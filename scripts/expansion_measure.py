"""M6 阶段 1：查询扩展埋点测量（**零额外上游调用**）。

对每条查询只跑**现有的那一次**上游调用（复用 `SearchPipeline._collect_hits` 的内部实现，
不新增任何请求），记录：

- 主源候选数 / 目标候选池；
- 查询词覆盖率（**分母固定为用户原始查询词**）；
- 最终结果的独立站点数；
- 是否命中「候选不足」判据（占位口径：候选数 < 目标候选池）。

用途：为「扩展触发阈值」的**选点**提供分布（分位数 + 直方图 + 各候选阈值的预计触发率）。

用法：
    python scripts/expansion_measure.py --out data/measure/expansion-samples-2026-09-28.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.core.upstream_gate import UpstreamOverloaded  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.rank.diversity import query_coverage, registrable_domain  # noqa: E402
from utf8_search.verify.expansion import expansion_needed  # noqa: E402

from relevance import QUERIES as RELEVANCE_QUERIES  # noqa: E402 - 复用 2-9 的 20 条抽检查询

# 中文长尾补充集：刻意选「具体、低频、地方/品类/标准」类查询，用于看候选是否更容易不足
LONGTAIL_QUERIES: list[str] = [
    "四川省 2026年 数字经济 扶持 政策 申报 条件",
    "2026年 跨境电商 出口 退税 流程",
    "国产 数据库 达梦 迁移 实践 案例",
    "折叠屏 手机 铰链 寿命 测试 数据",
    "固态电池 量产 时间表 车企",
    "老旧小区 加装电梯 补贴 申请 流程",
    "宠物 处方粮 国标 执行 标准",
    "空气源热泵 补贴 小区 改造 案例",
    "工业软件 CAE 国产替代 落地 案例",
    "光伏 组件 回收 政策 试点 名单",
    "医疗器械 二类 注册 资料 清单",
    "茶叶 农残 检测 标准 2026",
    "小语种 翻译 大模型 评测 结果",
    "储能 电站 消防 验收 规范",
    "新能源汽车 换电 标准 统一 进展",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M6 阶段 1：查询扩展埋点测量（零额外上游调用）")
    parser.add_argument("--out", default="", help="样本 JSON 输出路径（默认 data/measure/expansion-samples-<日期>.json）")
    parser.add_argument("--depth", default="basic", help="搜索深度（默认 basic）")
    parser.add_argument("--max-results", type=int, default=5, help="每条查询取前 N 条（默认 5）")
    parser.add_argument("--limit", type=int, default=0, help="只跑前 N 条查询（0=全部；用于小样本试跑）")
    parser.add_argument("--searxng", default="", help="覆盖 SearXNG 地址")
    return parser.parse_args()


def _quantiles(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)

    def pick(p: float) -> float:
        index = max(0, min(len(ordered) - 1, round(p * (len(ordered) - 1))))
        return round(ordered[index], 3)

    return {
        "min": pick(0.0),
        "p25": pick(0.25),
        "p50": pick(0.5),
        "p75": pick(0.75),
        "p90": pick(0.9),
        "max": pick(1.0),
        "mean": round(statistics.fmean(ordered), 3),
    }


def _histogram(values: list[int], edges: list[int]) -> dict[str, int]:
    """朴素直方图：`[0,edges[0])`、`[edges[i],edges[i+1])`、`[edges[-1],+∞)`。"""
    buckets: dict[str, int] = {}
    for value in values:
        label = f">={edges[-1]}"
        for index, edge in enumerate(edges):
            if value < edge:
                label = f"<{edge}" if index == 0 else f"[{edges[index - 1]},{edge})"
                break
        buckets[label] = buckets.get(label, 0) + 1
    return buckets


async def _measure_one(pipeline: SearchPipeline, query: str, depth: str, max_results: int) -> dict[str, object]:
    """跑一次**现有的**上游调用并采集埋点数值（不新增任何请求）。"""
    request = SearchRequest(query=query, max_results=max_results, depth=depth)  # type: ignore[arg-type]
    target = pipeline._candidate_target(request)
    try:
        hits, engines, failed, degraded = await pipeline._collect_hits(request)
    except UpstreamOverloaded as exc:
        return {"query": query, "error": f"overloaded:{exc.reason}", "target": target}
    merged = await pipeline._rank_hits(hits, request)
    results = merged[:max_results]
    raw_candidates: int | None = None
    for provider in pipeline.providers:
        if provider.name == "searxng":
            raw_candidates = getattr(provider, "raw_result_count", None)
            break
    coverage = (
        sum(query_coverage(query, item) for item in results) / len(results) if results else None
    )
    hosts = {registrable_domain(item.url) for item in results}
    hosts.discard("")
    reason = expansion_needed(len(hits), target, coverage)
    return {
        "query": query,
        "target": target,
        "candidates": len(hits),
        "raw_candidates": raw_candidates,
        "results": len(results),
        "coverage_mean": None if coverage is None else round(coverage, 4),
        "distinct_hosts": len(hosts),
        "reason": reason,
        "engines_used": engines,
        "failed_engines": failed,
        "degraded": degraded,
    }


def _sweep(samples: list[dict[str, object]]) -> dict[str, dict[str, int]]:
    """各种候选阈值下的预计触发率（用样本回算，不另外发请求）。"""
    ok = [s for s in samples if "candidates" in s]
    total = len(ok) or 1
    candidate_edges = [6, 8, 12, 16, 24]
    coverage_edges = [0.4, 0.5, 0.6]
    out: dict[str, dict[str, int]] = {"candidates_lt": {}, "coverage_lt": {}, "either": {}}
    for edge in candidate_edges:
        n = sum(1 for s in ok if int(s["candidates"]) < edge)  # type: ignore[arg-type]
        out["candidates_lt"][f"<{edge}"] = round(n / total * 100, 1)
    for edge in coverage_edges:
        n = sum(
            1
            for s in ok
            if s["coverage_mean"] is not None and float(s["coverage_mean"]) < edge  # type: ignore[arg-type]
        )
        out["coverage_lt"][f"<{edge}"] = round(n / total * 100, 1)
    for c_edge in candidate_edges:
        row: dict[str, int] = {}
        for v_edge in coverage_edges:
            n = sum(
                1
                for s in ok
                if int(s["candidates"]) < c_edge  # type: ignore[arg-type]
                or (s["coverage_mean"] is not None and float(s["coverage_mean"]) < v_edge)  # type: ignore[arg-type]
            )
            row[f"cov<{v_edge}"] = round(n / total * 100, 1)
        out["either"][f"cand<{c_edge}"] = row  # type: ignore[assignment]
    return out


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    if args.searxng:
        settings = settings.model_copy(update={"searxng_url": args.searxng})
    pipeline = await SearchPipeline.create(settings)

    labelled: list[tuple[str, str]] = [("relevance", q) for _, q in RELEVANCE_QUERIES]
    labelled += [("longtail-zh", q) for q in LONGTAIL_QUERIES]
    if args.limit:
        labelled = labelled[: args.limit]

    samples: list[dict[str, object]] = []
    try:
        for index, (group, query) in enumerate(labelled, start=1):
            sample = await _measure_one(pipeline, query, args.depth, args.max_results)
            sample["group"] = group
            samples.append(sample)
            if "error" in sample:
                print(f"[{index:>2}/{len(labelled)}] {group:<11} 失败：{sample['error']}  {query}")
            else:
                print(
                    f"[{index:>2}/{len(labelled)}] {group:<11} 候选 {sample['candidates']:>2}/{sample['target']:<2}"
                    f"（原始 {sample['raw_candidates']}）"
                    f" 覆盖 {float(sample['coverage_mean'] or 0):.2f} 独立站点 {sample['distinct_hosts']}"
                    f" {'→ 候选不足:' + str(sample['reason']) if sample['reason'] else '→ 充足'}  {query}"
                )
    finally:
        await pipeline.close()

    ok = [s for s in samples if "candidates" in s]
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "depth": args.depth,
        "max_results": args.max_results,
        "queries": len(samples),
        "measured": len(ok),
        "failed": len(samples) - len(ok),
        "candidates": _quantiles([float(s["candidates"]) for s in ok]),  # type: ignore[arg-type]
        "raw_candidates": _quantiles(
            [float(s["raw_candidates"]) for s in ok if s.get("raw_candidates") is not None]  # type: ignore[arg-type]
        ),
        "targets": _quantiles([float(s["target"]) for s in ok]),  # type: ignore[arg-type]
        "coverage_mean": _quantiles([float(s["coverage_mean"]) for s in ok if s["coverage_mean"] is not None]),  # type: ignore[arg-type]
        "distinct_hosts": _quantiles([float(s["distinct_hosts"]) for s in ok]),  # type: ignore[arg-type]
        "hist_candidates": _histogram([int(s["candidates"]) for s in ok], [6, 12, 16, 24, 32]),  # type: ignore[arg-type]
        "hist_raw_candidates": _histogram(
            [int(s["raw_candidates"]) for s in ok if s.get("raw_candidates") is not None], [12, 24, 32, 48, 64]  # type: ignore[arg-type]
        ),
        "hist_coverage": _histogram([int(float(s["coverage_mean"]) * 10) for s in ok if s["coverage_mean"] is not None], [4, 6, 8, 9]),
        "hist_hosts": _histogram([int(s["distinct_hosts"]) for s in ok], [2, 3, 4, 5]),  # type: ignore[arg-type]
        "placeholder_trigger": {
            "criterion": "candidates < target（5.2 原始「不足」口径）",
            "count": sum(1 for s in ok if s["reason"]),
            "rate": round(sum(1 for s in ok if s["reason"]) / (len(ok) or 1) * 100, 1),
        },
        "sweep": _sweep(samples),
    }

    print("\n== 分布（分位数）==")
    for key in ("raw_candidates", "candidates", "targets", "coverage_mean", "distinct_hosts"):
        print(f"{key:<15} {summary[key]}")  # type: ignore[index]
    print("\n== 直方图 ==")
    print("原始返回条数  ", summary["hist_raw_candidates"])
    print("候选数(截断后)", summary["hist_candidates"])
    print("覆盖率(×10)   ", summary["hist_coverage"])
    print("独立站点数    ", summary["hist_hosts"])
    print("\n== 预计触发率（占位口径：候选 < 目标）==")
    print(json.dumps(summary["placeholder_trigger"], ensure_ascii=False))
    print("\n== 阈值扫描（回算，百分比）==")
    print(json.dumps(summary["sweep"], ensure_ascii=False))

    out = Path(args.out) if args.out else Path("data/measure") / f"expansion-samples-{datetime.now():%Y%m%d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "samples": samples}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n样本已写入 {out.resolve()}")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
