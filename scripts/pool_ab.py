"""M6 阶段 2a：候选池上限 A/B/C 受控实验（**不增加上游调用**）。

做法（关键：避免上游漂移）：
1. 每条查询**只发一次**上游请求，索取 `--max-pool`（默认 40）条原始候选；
2. 在**同一批候选**上分别按 `--pools 24,32,40` 切片并各自跑一遍排序与质量过滤
   （复用 `SearchPipeline._rank_hits`，与 `scripts/rank_ab.py` 同一套受控方法）；
3. 比较：查询词覆盖率、独立站点数、**多留的候选是否真的进入 top5**、以及排序耗时。

同时产出**可直接打分的明细表**（与 `scripts/relevance.py` 的 `--score-file` 兼容）：
   data/measure/pool24-scores.csv / pool40-scores.csv

用法：
    python scripts/pool_ab.py --max-pool 40 --pools 24,32,40 --out data/measure/pool-ab-2026-09-28.json
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.core.upstream_gate import UpstreamOverloaded  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.rank.diversity import query_coverage, registrable_domain  # noqa: E402
from utf8_search.rank.fusion import normalize_url  # noqa: E402

from relevance import QUERIES as RELEVANCE_QUERIES  # noqa: E402

MAX_RESULTS = 5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="候选池上限 A/B/C 受控实验（M6 阶段 2a）")
    parser.add_argument("--max-pool", type=int, default=40, help="上游索取的最大候选数（只发一次请求）")
    parser.add_argument("--pools", default="24,32,40", help="要比较的候选池大小，逗号分隔")
    parser.add_argument("--out", default="", help="JSON 输出路径")
    parser.add_argument("--score-dir", default="data/measure", help="人工打分模板输出目录")
    parser.add_argument("--score-prefix", default="pool", help="打分模板文件名前缀（默认 pool → pool24-scores.csv）")
    parser.add_argument(
        "--detail-out",
        default="",
        help="可读对照明细 md 输出路径（默认 docs/reports/m6-pool-ab-detail-<日期>.md）",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> int:
    pools = [int(x) for x in args.pools.split(",") if x.strip()]
    settings = Settings().model_copy(
        update={"rank_candidate_pool": args.max_pool, "news_candidate_pool": args.max_pool}
    )
    pipeline = await SearchPipeline.create(settings)
    queries = [q for _, q in RELEVANCE_QUERIES]

    per_query: list[dict[str, object]] = []
    try:
        for index, query in enumerate(queries, start=1):
            request = SearchRequest(query=query, max_results=MAX_RESULTS, depth="basic")
            try:
                hits, _engines, _failed, _degraded = await pipeline._collect_hits(request)
            except UpstreamOverloaded as exc:
                print(f"[{index:>2}/{len(queries)}] 失败：overloaded:{exc.reason}  {query}")
                continue

            raw = getattr(
                next((p for p in pipeline.providers if p.name == "searxng"), None),
                "raw_result_count",
                None,
            )
            entry: dict[str, object] = {"query": query, "raw_candidates": raw, "pools": {}}
            base_urls_local = {
                normalize_url(hit.url) for hit in hits[: pools[0]]
            }
            for pool in pools:
                subset = hits[:pool]
                started = time.perf_counter()
                merged = await pipeline._rank_hits(list(subset), request)
                rank_ms = (time.perf_counter() - started) * 1000
                top = merged[:MAX_RESULTS]
                coverage = (
                    sum(query_coverage(query, item) for item in top) / len(top) if top else None
                )
                hosts = {registrable_domain(item.url) for item in top}
                hosts.discard("")
                # 「多留的候选」= 超出基准池才拿到的候选；看它们有没有真的进 top5
                extra_urls = {normalize_url(hit.url) for hit in subset} - base_urls_local
                new_in_top5 = sum(1 for item in top if normalize_url(item.url) in extra_urls)
                entry["pools"][str(pool)] = {  # type: ignore[index]
                    "candidates": len(subset),
                    "extra_candidates": len(extra_urls),
                    "new_in_top5": new_in_top5,
                    "coverage_mean": None if coverage is None else round(coverage, 4),
                    "distinct_hosts": len(hosts),
                    "rank_ms": round(rank_ms, 2),
                    "top": [
                        {
                            "title": item.title,
                            "url": item.url,
                            "domain": registrable_domain(item.url),
                            "content": item.content or "",
                            "published_date": item.published_date or "",
                        }
                        for item in top
                    ],
                }
            per_query.append(entry)
            by_pool = entry["pools"]  # type: ignore[assignment]
            print(
                f"[{index:>2}/{len(queries)}] 原始 {raw} 条｜"
                + " ｜".join(
                    f"池{p}: 覆盖 {by_pool[str(p)]['coverage_mean']:.2f}"
                    f" 站点 {by_pool[str(p)]['distinct_hosts']}"
                    f" 新进top5 {by_pool[str(p)]['new_in_top5']}"
                    for p in pools
                )
            )
    finally:
        await pipeline.close()

    # ---------------- 汇总 ----------------
    summary: dict[str, object] = {"pools": pools, "queries": len(per_query), "by_pool": {}}
    base_pool = pools[0]
    base_text = {entry["query"]: entry["pools"][str(base_pool)]["top"] for entry in per_query}  # type: ignore[index]
    for pool in pools:
        cov = [
            float(entry["pools"][str(pool)]["coverage_mean"])  # type: ignore[index]
            for entry in per_query
            if entry["pools"][str(pool)]["coverage_mean"] is not None  # type: ignore[index]
        ]
        hosts = [float(entry["pools"][str(pool)]["distinct_hosts"]) for entry in per_query]  # type: ignore[index]
        rank_ms = [float(entry["pools"][str(pool)]["rank_ms"]) for entry in per_query]  # type: ignore[index]
        # 「多留的候选是否真的进 top5」：每条查询里，来自「超出基准池的候选」的新 top5 条数
        new_in_top5 = [int(entry["pools"][str(pool)]["new_in_top5"]) for entry in per_query]  # type: ignore[index]
        extra_candidates = [int(entry["pools"][str(pool)]["extra_candidates"]) for entry in per_query]  # type: ignore[index]
        # 与基准池相比 top5 的内容变化条数（换了哪些结果）
        churn = [
            sum(
                1
                for item in entry["pools"][str(pool)]["top"]  # type: ignore[index]
                if normalize_url(item["url"])
                not in {normalize_url(x["url"]) for x in base_text[entry["query"]]}
            )
            for entry in per_query
        ]
        summary["by_pool"][str(pool)] = {  # type: ignore[index]
            "coverage_mean": round(statistics.fmean(cov), 4) if cov else None,
            "coverage_min": round(min(cov), 4) if cov else None,
            "distinct_hosts_mean": round(statistics.fmean(hosts), 3) if hosts else None,
            "rank_ms_p50": round(statistics.median(rank_ms), 2) if rank_ms else None,
            "extra_candidates_total": sum(extra_candidates),
            "new_in_top5_total": sum(new_in_top5),
            "new_in_top5_ratio": round(
                sum(new_in_top5) / (len(per_query) * MAX_RESULTS) * 100, 2
            )
            if per_query
            else None,
            "queries_with_new_in_top5_pct": round(
                sum(1 for n in new_in_top5 if n > 0) / (len(per_query) or 1) * 100, 1
            ),
            "top5_changed_mean": round(statistics.fmean(churn), 2) if churn else None,
        }

    print("\n== 汇总（同一批候选内切片，无上游漂移）==")
    for pool in pools:
        row = summary["by_pool"][str(pool)]  # type: ignore[index]
        print(
            f"池 {pool:>3}: 覆盖均值 {row['coverage_mean']}（最低 {row['coverage_min']}） "
            f"独立站点均值 {row['distinct_hosts_mean']} 排序P50 {row['rank_ms_p50']}ms "
            f"｜ 多留候选 {row['extra_candidates_total']} 条，进 top5 {row['new_in_top5_total']} 条"
            f"（占 top5 槽位 {row['new_in_top5_ratio']}%，"
            f"{row['queries_with_new_in_top5_pct']}% 的查询至少进 1 条）"
            f"｜ top5 相对池{base_pool} 变化 {row['top5_changed_mean']} 条/查询"
        )

    out = Path(args.out) if args.out else Path("data/measure") / f"pool-ab-{datetime.now():%Y%m%d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"summary": summary, "queries": per_query}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n明细已写入 {out.resolve()}")

    # ---------------- 人工打分模板（与 relevance.py --score-file 兼容） ----------------
    score_dir = Path(args.score_dir)
    score_dir.mkdir(parents=True, exist_ok=True)
    templates: dict[int, Path] = {}
    for pool in (pools[0], pools[-1]):
        path = score_dir / f"{args.score_prefix}{pool}-scores.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "scores", "note"])
            for idx, entry in enumerate(per_query, start=1):
                writer.writerow([idx, "", f"[pool{pool}] {entry['query']}"])
        templates[pool] = path
        print(f"打分模板（pool={pool}）: {path.resolve()}")

    write_detail(per_query, summary, pools, args, templates)
    return 0


def _cell(text: object, limit: int = 90) -> str:
    """Markdown 表格单元格：压成单行、截断、转义竖线。"""
    flat = " ".join(str(text or "").split())
    flat = flat[:limit] + ("…" if len(flat) > limit else "")
    return flat.replace("|", "\\|")


def write_detail(
    per_query: list[dict[str, object]],
    summary: dict[str, object],
    pools: list[int],
    args: argparse.Namespace,
    templates: dict[int, Path],
) -> Path:
    """写可读对照明细（池 24 与池 40 并列），供人工打分。"""
    low, high = pools[0], pools[-1]
    out = (
        Path(args.detail_out)
        if args.detail_out
        else Path("docs/reports") / f"m6-pool-ab-detail-{datetime.now():%Y%m%d}.md"
    )
    lines: list[str] = [
        f"# 候选池 {low} vs {high} 对照明细（人工打分用）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "- **数据来源**：**同一批候选切片而来** —— 每条查询只发**一次**上游请求（索取 "
        f"{args.max_pool} 条），再在本地取前 {low} / {high} 条分别排序。",
        "- ⚠️ **不可与重新采集的结果混用**：本文件里的两列来自同一次采集；另跑一次脚本会得到不同的候选集。",
        f"- 打分模板：`{templates[low].name}`（先填这份）、`{templates[high].name}`（仅在必要时对照）",
        f"- 打分规则：scores 的 5 位依次对应排名 1-5，**非零即为相关**；门槛 20 条里 ≥18 条满足「相关 ≥4」。",
        "",
        "## 怎么用（交付说明）",
        "",
        f"1. **先只填 `{templates[low].name}`**（池 {low} = 当前默认）——这份用于**关闭 2-9**"
        "（与 `docs/reports/m2-9-relevance-20260928.md` 是同一批 20 条查询，但采集批次不同，二者选一即可，别混填）。",
        f"2. **只有**当池 {low} 那份打出 **< 18/20**（未达 90% 门槛）时，才需要再填 `{templates[high].name}` 做对照，"
        f"看「把候选池从 {low} 放大到 {high}」能不能救回来。",
        "3. 判定命令（不联网）：`.venv/bin/python scripts/relevance.py --score-file <填好的 csv>`",
        "",
        "## 汇总",
        "",
        f"| 指标 | 池 {low} | 池 {high} |",
        "| --- | --- | --- |",
    ]
    by_pool = summary.get("by_pool") or {}
    for label, key in (
        ("覆盖率均值", "coverage_mean"),
        ("覆盖率最低", "coverage_min"),
        ("独立站点均值", "distinct_hosts_mean"),
        ("排序耗时 P50", "rank_ms_p50"),
        ("多留候选进 top5（条）", "new_in_top5_total"),
        ("进 top5 占槽位", "new_in_top5_ratio"),
        ("至少进 1 条的查询占比", "queries_with_new_in_top5_pct"),
        ("top5 变化（条/查询）", "top5_changed_mean"),
    ):
        row_low = by_pool.get(str(low), {})
        row_high = by_pool.get(str(high), {})
        lines.append(f"| {label} | {row_low.get(key, '-')} | {row_high.get(key, '-')} |")
    lines.append("")

    for idx, entry in enumerate(per_query, start=1):
        lines.append(f"## {idx}. {entry['query']}")
        lines.append("")
        for pool in (low, high):
            pool_top = entry["pools"][str(pool)]["top"]  # type: ignore[index]
            lines.append(f"**池 {pool}**（候选 {entry['pools'][str(pool)]['candidates']} 条，"  # type: ignore[index]
                         f"覆盖 {entry['pools'][str(pool)]['coverage_mean']}，"  # type: ignore[index]
                         f"独立站点 {entry['pools'][str(pool)]['distinct_hosts']}，"  # type: ignore[index]
                         f"新进 top5 {entry['pools'][str(pool)]['new_in_top5']} 条）")
            lines.append("")
            lines.append("| 排名 | 标题 | 域名 | 摘要 | URL |")
            lines.append("| --- | --- | --- | --- | --- |")
            for rank, item in enumerate(pool_top, start=1):
                lines.append(
                    f"| {rank} | {_cell(item.get('title'))} | {_cell(item.get('domain'), 40)} | "
                    f"{_cell(item.get('content'))} | {_cell(item.get('url'), 80)} |"
                )
            lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"对照明细 md: {out.resolve()}")
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
