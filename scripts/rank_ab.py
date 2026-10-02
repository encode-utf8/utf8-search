"""受控 A/B：用**同一批候选**复核 M5-5.3 的排序改动（候选池 → 融合 → 重排 → 质量过滤 → 时效分层）。

为什么需要它：免费引擎每次请求返回的候选集差异很大（同一查询隔几秒跑两次，top1 都可能不同），
直接对比「改动前 / 改动后」的两次联网采集，测到的主要是上游漂移而不是排序改动的效果。
本脚本把两件事分开：

1. `--snapshot-out`：联网采集一次候选（按新口径的候选池索取），落盘成快照；
2. `--snapshot-in`：拿**同一份快照**分别按「改动前口径」和「改动后口径」排序，输出对比报告。

判定用 `utf8_search.verify.metrics.evaluate_hygiene_delta`：同站冗余 / 聚合页 / 非中英文脚本不增加，
查询词覆盖率不下降（容差 5%）。

用法：
    python scripts/rank_ab.py --snapshot-out data/rank-ab-candidates.json
    python scripts/rank_ab.py --snapshot-in data/rank-ab-candidates.json --out docs/reports/<日期>-rank-ab.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from relevance import QUERIES  # noqa: E402  （共用同一份 20 条抽检查询）

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.providers.base import SearchHit  # noqa: E402
from utf8_search.rank.diversity import is_aggregator_page, query_coverage  # noqa: E402
from utf8_search.verify.metrics import (  # noqa: E402
    evaluate_hygiene_delta,
    summarize_result_hygiene,
)

# 改动前的排序口径（与 scripts/relevance.py --legacy 保持一致）
LEGACY_OVERRIDES = {
    "rank_max_per_host": 0,
    "rank_min_query_coverage": 0.0,
    "rank_drop_aggregator_pages": False,
    "rank_drop_script_mismatch": False,
    "general_recency_intent": False,
    "rank_candidate_pool": 1,
}


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="M5-5.3 排序改动受控 A/B（同一候选集）")
    parser.add_argument("--snapshot-out", default="", help="采集候选快照并写入该路径")
    parser.add_argument("--snapshot-in", default="", help="读取候选快照做离线 A/B")
    parser.add_argument("--out", default="", help="A/B 报告输出路径（Markdown）")
    parser.add_argument("--max-results", type=int, default=5, help="每条查询取前 N 条（默认 5）")
    parser.add_argument("--searxng", default="", help="覆盖 SearXNG 地址")
    return parser.parse_args()


async def collect_snapshot(args: argparse.Namespace) -> dict[str, object]:
    """联网采集一次候选快照（每查询一批原始命中）。"""
    settings = Settings()
    if args.searxng:
        settings = settings.model_copy(update={"searxng_url": args.searxng})
    # 快照必须现采：命中旧缓存会让「候选集」混入历史状态，A/B 就说不清了
    settings = settings.model_copy(update={"cache_enabled": False})
    pipeline = await SearchPipeline.create(settings)
    entries: list[dict[str, object]] = []
    try:
        for index, (category, query) in enumerate(QUERIES, start=1):
            request = SearchRequest(query=query, max_results=args.max_results, depth="basic")
            # 第 4 个返回值是 M5 并发保护的 degraded 标记（本脚本只关心候选集，忽略即可）
            hits, engines_used, failed, _degraded = await pipeline._collect_hits(request)
            entries.append(
                {
                    "id": index,
                    "category": category,
                    "query": query,
                    "hits": [hit.to_dict() for hit in hits],
                    "engines_used": engines_used,
                    "failed_engines": failed,
                }
            )
            print(
                f"[{index}/{len(QUERIES)}] {category} {query} -> 候选 {len(hits)} 条"
                f"（引擎 {', '.join(engines_used) or '-'}）",
                flush=True,
            )
    finally:
        await pipeline.close()
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "candidate_pool": settings.rank_candidate_pool,
        "entries": entries,
    }


def _items(results: list) -> list[dict[str, object]]:
    return [
        {
            "rank": rank,
            "title": result.title or "(无标题)",
            "url": result.url,
            "content": result.content or "",
        }
        for rank, result in enumerate(results, start=1)
    ]


async def compare(args: argparse.Namespace) -> int:
    snapshot = json.loads(Path(args.snapshot_in).read_text(encoding="utf-8"))
    base = Settings()
    if args.searxng:
        base = base.model_copy(update={"searxng_url": args.searxng})
    base = base.model_copy(update={"cache_enabled": False})
    legacy_settings = base.model_copy(update=LEGACY_OVERRIDES)

    legacy_pipeline = await SearchPipeline.create(legacy_settings)
    new_pipeline = await SearchPipeline.create(base)

    rows: list[dict[str, object]] = []
    before_all: list[dict[str, float]] = []
    after_all: list[dict[str, float]] = []
    try:
        for entry in snapshot["entries"]:
            query = entry["query"]
            hits = [SearchHit(**item) for item in entry["hits"]]
            request = SearchRequest(query=query, max_results=args.max_results, depth="basic")
            # 同一批候选，两种口径各排一次
            legacy_top = (await legacy_pipeline._rank_hits(list(hits), request))[: args.max_results]
            new_top = (await new_pipeline._rank_hits(list(hits), request))[: args.max_results]
            before = summarize_result_hygiene(_items(legacy_top), query)
            after = summarize_result_hygiene(_items(new_top), query)
            before_all.append(before)
            after_all.append(after)
            rows.append(
                {
                    "id": entry["id"],
                    "category": entry["category"],
                    "query": query,
                    "candidates": len(hits),
                    "before": before,
                    "after": after,
                    "before_results": legacy_top,
                    "after_results": new_top,
                }
            )
            print(
                f"[{entry['id']:>2}/{len(snapshot['entries'])}] {query}\n"
                f"      改动前 覆盖 {before['coverage_mean']:.2f} 同站冗余 {before['same_host_excess']:.0f}"
                f" 聚合页 {before['aggregator']:.0f} 脚本 {before['script_mismatch']:.0f}\n"
                f"      改动后 覆盖 {after['coverage_mean']:.2f} 同站冗余 {after['same_host_excess']:.0f}"
                f" 聚合页 {after['aggregator']:.0f} 脚本 {after['script_mismatch']:.0f}",
                flush=True,
            )
    finally:
        await legacy_pipeline.close()
        await new_pipeline.close()

    before_sum = _aggregate(before_all)
    after_sum = _aggregate(after_all)
    passed, notes, _details = evaluate_hygiene_delta(before=before_sum, after=after_sum)

    report = _render(snapshot, rows, before_sum, after_sum, passed, notes)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(report, encoding="utf-8", newline="\n")
        print(f"\nA/B 报告: {target.resolve()}")
    else:
        print(report)
    print("\n== 卫生度汇总（同一候选集，N=%d 条查询） ==" % len(rows))
    for key, label in (
        ("total", "结果条数"),
        ("coverage_mean", "查询词覆盖率均值"),
        ("same_host_excess", "同站冗余"),
        ("aggregator", "聚合页"),
        ("script_mismatch", "非中英文脚本"),
        ("distinct_hosts_mean", "独立站点数均值"),
    ):
        print(f"  {label:<14} {before_sum.get(key, 0):8.3f} -> {after_sum.get(key, 0):8.3f}")
    print(f"结论：{'通过' if passed else '不通过'}")
    for note in notes:
        print(f"  - {note}")
    return 0 if passed else 1


def _aggregate(summaries: list[dict[str, float]]) -> dict[str, float]:
    if not summaries:
        return {}
    keys = [k for k in summaries[0] if k != "_has_query_tokens"]
    out: dict[str, float] = {key: sum(s.get(key, 0.0) for s in summaries) for key in keys}
    out["coverage_mean"] = out["coverage_mean"] / len(summaries)
    out["coverage_min"] = min(s.get("coverage_min", 0.0) for s in summaries)
    out["distinct_hosts_mean"] = out["distinct_hosts"] / len(summaries)
    return out


def _cell(text: str, limit: int = 56) -> str:
    flat = " ".join((text or "").split()).replace("|", "\\|")
    return flat[:limit] + ("…" if len(flat) > limit else "")


def _render(snapshot, rows, before_sum, after_sum, passed, notes) -> str:
    lines = [
        "# M5-5.3 排序改动受控 A/B（同一候选集）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 候选快照采集时间：{snapshot.get('generated_at', '-')}，"
        f"每查询索取 {snapshot.get('candidate_pool', '-')} 条候选",
        "- 说明：两次排序吃的是**同一批候选**，因此差异只来自 5.3 的排序侧改动，不含上游漂移",
        f"- 每条查询取前 {len(rows[0]['after_results']) if rows else 0} 条做卫生度统计",
        "",
        "## 汇总（全部查询合计）",
        "",
        "| 指标 | 改动前 | 改动后 |",
        "| --- | --- | --- |",
        f"| 结果条数 | {before_sum.get('total', 0):.0f} | {after_sum.get('total', 0):.0f} |",
        f"| 查询词覆盖率均值 | {before_sum.get('coverage_mean', 0):.3f} | {after_sum.get('coverage_mean', 0):.3f} |",
        f"| 同站冗余 | {before_sum.get('same_host_excess', 0):.0f} | {after_sum.get('same_host_excess', 0):.0f} |",
        f"| 聚合页 | {before_sum.get('aggregator', 0):.0f} | {after_sum.get('aggregator', 0):.0f} |",
        f"| 非中英文脚本 | {before_sum.get('script_mismatch', 0):.0f} | {after_sum.get('script_mismatch', 0):.0f} |",
        f"| 独立站点数均值 | {before_sum.get('distinct_hosts_mean', 0):.2f} | {after_sum.get('distinct_hosts_mean', 0):.2f} |",
        "",
        f"**判定：{'通过' if passed else '不通过'}**",
        "",
        *[f"- {note}" for note in notes],
        "",
    ]
    for row in rows:
        lines.append(f"## {row['id']}. [{row['category']}] {row['query']}")
        lines.append("")
        lines.append(f"候选 {row['candidates']} 条 · 改动前 top-N → 改动后 top-N")
        lines.append("")
        lines.append("| # | 改动前 | 改动后 |")
        lines.append("| --- | --- | --- |")
        for index in range(max(len(row["before_results"]), len(row["after_results"]))):
            old = row["before_results"][index].title if index < len(row["before_results"]) else "-"
            new = row["after_results"][index].title if index < len(row["after_results"]) else "-"
            lines.append(f"| {index + 1} | {_cell(old)} | {_cell(new)} |")
        lines.append("")
        lines.append("改动后明细：")
        lines.append("")
        lines.append("| # | 标题 | 覆盖率 | 聚合页 | URL |")
        lines.append("| --- | --- | --- | --- | --- |")
        for rank, result in enumerate(row["after_results"], start=1):
            coverage = query_coverage(row["query"], result)
            flag = "是" if is_aggregator_page(result) else "-"
            lines.append(
                f"| {rank} | {_cell(result.title)} | {coverage:.2f} | {flag} | {result.url} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    _configure_stdout()
    args = parse_args()
    if args.snapshot_out:
        snapshot = asyncio.run(collect_snapshot(args))
        target = Path(args.snapshot_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n"
        )
        print(f"候选快照: {target.resolve()}")
        if not args.snapshot_in:
            return 0
    if not args.snapshot_in:
        print("需要 --snapshot-out 或 --snapshot-in")
        return 2
    return asyncio.run(compare(args))


if __name__ == "__main__":
    raise SystemExit(main())
