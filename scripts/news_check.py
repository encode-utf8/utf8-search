"""时效性验收：`topic=news` 结果中带近期发布日期的比例（验收项 5.2-7）。

对应 `docs/04-后续路线图.md` 第 5.2 节：
`topic=news` + `time_range=day` 返回结果中 ≥ 80% 带 7 日内日期。

用法：
    python scripts/news_check.py                          # 默认 8 条中英新闻查询，time_range=day
    python scripts/news_check.py --time-range week --max-results 5
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.rank.recency import timing_stats  # noqa: E402
from utf8_search.verify.metrics import evaluate_timeliness  # noqa: E402

# 新闻类查询（含 2-9 抽检中暴露问题的「台风路径」，用于回归）
QUERIES = [
    "2026年9月 国内外重大新闻",
    "最近一周 AI 行业动态",
    "台风 最新消息 路径",
    "美国 关税 最新政策",
    "latest news semiconductor export controls",
    "OpenAI latest news",
    "2026年 新能源汽车 补贴政策",
    "EU AI Act latest developments",
]

# 验收口径固定为 7 日（docs/04 第 5.2 节）
FRESH_DAYS = 7


def _configure_stdout() -> None:
    """Windows 控制台默认非 UTF-8，中文输出会抛异常，这里统一兜底。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="utf8-search 时效性验收（验收项 5.2-7）")
    parser.add_argument("--time-range", default="day", choices=["day", "week", "month", "year", ""], help="传给 SearXNG 的时间范围")
    parser.add_argument("--max-results", type=int, default=5, help="每条查询返回的结果数")
    parser.add_argument("--depth", default="basic", choices=["basic", "advanced", "deep"], help="搜索深度")
    parser.add_argument("--searxng", default="", help="覆盖 SearXNG 地址")
    parser.add_argument("--out", default="", help="Markdown 报告输出路径")
    parser.add_argument("--no-cache", action="store_true", help="禁用缓存，保证测的是实时结果")
    parser.add_argument(
        "--ab",
        action="store_true",
        help="配对 A/B：每条查询交替跑「开/关 5.3 质量过滤」两种口径，抵消上游漂移（M5-5.3 回归用）",
    )
    parser.add_argument("--rounds", type=int, default=1, help="--ab 模式下每条查询跑几轮（默认 1）")
    return parser.parse_args()


# 「改动前」口径：关掉 5.3 引入的质量过滤（与 scripts/relevance.py --legacy 一致）
LEGACY_OVERRIDES = {
    "rank_max_per_host": 0,
    "rank_min_query_coverage": 0.0,
    "rank_drop_aggregator_pages": False,
    "rank_drop_script_mismatch": False,
    "general_recency_intent": False,
}


async def run_ab(args: argparse.Namespace) -> int:
    """配对 A/B：同一时刻交替跑两种口径，比较「7 日内日期条数」。

    单跑一次的时效性指标漂移很大（实测同一份代码 10 分钟内能跑出 95% / 85% / 80%），
    所以必须逐条配对才能判断「质量过滤有没有挤掉新鲜结果」。
    """
    base = Settings()
    if args.searxng:
        base = base.model_copy(update={"searxng_url": args.searxng})
    if args.no_cache:
        base = base.model_copy(update={"cache_enabled": False})

    pipelines = {
        "on": await SearchPipeline.create(base),
        "off": await SearchPipeline.create(base.model_copy(update=LEGACY_OVERRIDES)),
    }
    pairs: list[dict[str, object]] = []
    try:
        for index, query in enumerate(QUERIES, start=1):
            # 逐条交替：偶数轮先跑「开」，奇数轮先跑「关」，让漂移均摊到两侧
            order = ["on", "off"] if index % 2 == 1 else ["off", "on"]
            stats: dict[str, dict[str, float]] = {}
            for name in order:
                response = await pipelines[name].search(
                    SearchRequest(
                        query=query,
                        max_results=args.max_results,
                        depth=args.depth,
                        topic="news",
                        time_range=args.time_range or None,
                    )
                )
                stats[name] = timing_stats(response.results, fresh_days=FRESH_DAYS)
            pairs.append({"query": query, "on": stats["on"], "off": stats["off"]})
            print(
                f"[{index}/{len(QUERIES)}] {query[:24]:<26}"
                f" 开过滤 {stats['on']['fresh']:.0f}/{stats['on']['total']:.0f}"
                f"  关过滤 {stats['off']['fresh']:.0f}/{stats['off']['total']:.0f}"
                f"  配对差 {stats['on']['fresh'] - stats['off']['fresh']:+.0f}"
            )
    finally:
        for pipeline in pipelines.values():
            await pipeline.close()

    def _sum(key: str, mode: str) -> float:
        return sum(float(pair[mode].get(key, 0)) for pair in pairs)

    total_on, fresh_on = _sum("total", "on"), _sum("fresh", "on")
    total_off, fresh_off = _sum("total", "off"), _sum("fresh", "off")
    diffs = [float(pair["on"]["fresh"]) - float(pair["off"]["fresh"]) for pair in pairs]
    median_diff = statistics.median(diffs) if diffs else 0.0
    passed_off, notes_off, details_off = evaluate_timeliness(total=total_off, fresh=fresh_off)
    passed_on, notes_on, details_on = evaluate_timeliness(total=total_on, fresh=fresh_on)
    # 判定：① 开过滤后仍达标（5.2-7 的硬指标）；② 配对差中位数不劣于 -1 条（容差 2 条/8 查询）
    paired = median_diff >= -1
    passed = passed_on and paired and fresh_on >= fresh_off - 2

    print("\n== 时效性配对 A/B（开 / 关 5.3 质量过滤） ==")
    print(f"开过滤：{fresh_on:.0f}/{total_on:.0f} = {details_on['ratio']:.0%}")
    print(f"关过滤：{fresh_off:.0f}/{total_off:.0f} = {details_off['ratio']:.0%}")
    print(f"配对差（开-关）：中位 {median_diff:+.1f} 条/查询")
    print(f"结论：{'通过' if passed else '不通过'} — " + ("；".join(notes_on) if passed else f"关过滤口径 {'通过' if passed_off else '不通过'}；{'；'.join(notes_off)}"))

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 时效性配对 A/B（M5-5.3 回归，验收项 5.2-7 的回归保护）",
            "",
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 参数：topic=news，time_range={args.time_range or '未指定'}，depth={args.depth}，max_results={args.max_results}",
            "- 方法：逐条查询交替跑「开 / 关 5.3 质量过滤」两种口径，抵消上游漂移",
            "- 口径：结果带 7 日内发布日期算达标；判定要求开过滤后仍 ≥ 80%，且配对差不劣于 -1 条/查询",
            "",
            f"**结论：{'通过' if passed else '不通过'}** — 开过滤 {fresh_on:.0f}/{total_on:.0f} "
            f"({details_on['ratio']:.0%})，关过滤 {fresh_off:.0f}/{total_off:.0f} ({details_off['ratio']:.0%})，"
            f"配对差中位 {median_diff:+.1f} 条/查询",
            "",
            "| 查询 | 开过滤（7日内/总数） | 关过滤（7日内/总数） | 配对差 |",
            "| --- | --- | --- | --- |",
        ]
        for pair in pairs:
            lines.append(
                f"| {pair['query']} | {pair['on']['fresh']:.0f}/{pair['on']['total']:.0f} "
                f"| {pair['off']['fresh']:.0f}/{pair['off']['total']:.0f} "
                f"| {float(pair['on']['fresh']) - float(pair['off']['fresh']):+.0f} |"
            )
        lines.append("")
        out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"报告: {out.resolve()}")

    return 0 if passed else 1


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    if args.searxng:
        settings = settings.model_copy(update={"searxng_url": args.searxng})
    if args.no_cache:
        settings = settings.model_copy(update={"cache_enabled": False})

    pipeline = await SearchPipeline.create(settings)
    rows: list[dict[str, object]] = []
    try:
        for index, query in enumerate(QUERIES, start=1):
            try:
                response = await pipeline.search(
                    SearchRequest(
                        query=query,
                        max_results=args.max_results,
                        depth=args.depth,
                        topic="news",
                        time_range=args.time_range or None,
                    )
                )
                stats = timing_stats(response.results, fresh_days=FRESH_DAYS)
                rows.append({"query": query, "stats": stats, "results": response.results, "error": ""})
                print(
                    f"[{index}/{len(QUERIES)}] {query[:26]:<28} 结果 {stats['total']:>2}  "
                    f"7日内 {stats['fresh']:>2}  过期 {stats['stale']:>2}  无日期 {stats['undated']:>2}  "
                    f"({stats['fresh_ratio']:.0%})"
                )
            except Exception as exc:  # noqa: BLE001 - 单条失败不中断整轮验收
                rows.append({"query": query, "stats": {}, "results": [], "error": f"{type(exc).__name__}: {exc}"})
                print(f"[{index}/{len(QUERIES)}] {query[:26]:<28} 失败: {exc}")
    finally:
        await pipeline.close()

    total = sum(int(row["stats"].get("total", 0)) for row in rows)
    fresh = sum(int(row["stats"].get("fresh", 0)) for row in rows)
    passed, notes, details = evaluate_timeliness(total=total, fresh=fresh)

    print("\n== 时效性验收 ==")
    print(f"查询数        : {len(QUERIES)}（time_range={args.time_range or '未指定'}，topic=news）")
    print(f"结果总数      : {total}")
    print(f"7 日内日期    : {fresh}")
    print(f"达标比例      : {details['ratio']:.0%}（门槛 80%）")
    print("\n结论：" + ("通过" if passed else "不通过") + " — " + "；".join(notes))

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# 时效性验收报告（验收项 5.2-7）",
            "",
            f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 参数：topic=news，time_range={args.time_range or '未指定'}，depth={args.depth}，max_results={args.max_results}",
            f"- 口径：结果带 7 日内发布日期算达标，门槛 ≥ 80%",
            "",
            f"**结论：{'通过' if passed else '不通过'}** — {'；'.join(notes)}",
            "",
            "| 查询 | 结果 | 7 日内 | 过期 | 无日期 | 达标比例 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            stats = row["stats"]
            if not stats:
                lines.append(f"| {row['query']} | 失败 | - | - | - | {row['error']} |")
                continue
            lines.append(
                f"| {row['query']} | {stats['total']} | {stats['fresh']} | {stats['stale']} | "
                f"{stats['undated']} | {stats['fresh_ratio']:.0%} |"
            )
        lines.append("")
        for row in rows:
            if not row["results"]:
                continue
            lines.append(f"## {row['query']}")
            lines.append("")
            lines.append("| 排名 | 发布日期 | 标题 | 域名 |")
            lines.append("| --- | --- | --- | --- |")
            for rank, result in enumerate(row["results"], start=1):
                from urllib.parse import urlsplit

                domain = urlsplit(result.url).hostname or ""
                title = (result.title or "").replace("|", "\\|")[:80]
                lines.append(f"| {rank} | {result.published_date or '-'} | {title} | {domain} |")
            lines.append("")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"报告: {out.resolve()}")

    return 0 if passed else 1


def main() -> int:
    _configure_stdout()
    args = parse_args()
    if args.ab:
        return asyncio.run(run_ab(args))
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())