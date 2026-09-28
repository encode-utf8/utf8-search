"""相关性抽检：跑 20 条中英查询，输出 top5 明细表，供人工打分。

对应验收项 2-9（详见 `docs/04-后续路线图.md` 第 4.4 节）：
覆盖 新闻 / 技术 / 政策 / 商品 四类，中英混合。

两步用法：
    # 1) 采集：生成明细报告 + 打分模板
    python scripts/relevance.py --depth basic --out data/relevance-2026-09-24.md
    # 2) 打分：把模板 CSV 的 scores 列填成 5 个 0/1（1=相关）后判定
    python scripts/relevance.py --score-file data/relevance-2026-09-24-scores.csv

判定标准：top5 中相关数 ≥ 4 的查询占比 ≥ 90%（逻辑见 `utf8_search.verify.metrics.evaluate_relevance`）。
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.verify.metrics import (  # noqa: E402
    evaluate_hygiene_delta,
    evaluate_relevance,
    summarize_result_hygiene,
)

# 20 条抽检查询：id 即下表顺序（打分模板的 id 列与此一致）
QUERIES: list[tuple[str, str]] = [
    ("新闻", "2026年9月 国内外重大新闻"),
    ("新闻", "最近一周 AI 行业动态"),
    ("新闻", "latest news semiconductor export controls"),
    ("新闻", "台风 最新消息 路径"),
    ("新闻", "美国 关税 最新政策"),
    ("技术", "Python 3.13 新特性"),
    ("技术", "MCP protocol specification 2026"),
    ("技术", "FastAPI 与 Django 性能对比"),
    ("技术", "how does HTTP/3 QUIC work"),
    ("技术", "Rust async runtime tokio 原理"),
    ("政策", "2026年 新能源汽车 补贴政策"),
    ("政策", "数据出境安全评估办法 最新"),
    ("政策", "EU AI Act compliance requirements"),
    ("政策", "个人所得税 专项附加扣除 标准"),
    ("政策", "children privacy law COPPA update"),
    ("商品", "iPhone 17 Pro 价格 参数"),
    ("商品", "best noise cancelling headphones 2026 review"),
    ("商品", "扫地机器人 推荐 性价比"),
    ("商品", "RTX 5090 benchmark 价格"),
    ("商品", "国产显卡 摩尔线程 最新型号"),
]

# 判定门槛（与 docs/04 第 4.4 节的「top5 中 ≥ 4 条相关」对应）
PER_QUERY_MIN = 4
MIN_PASS_RATIO = 0.9


def _configure_stdout() -> None:
    """Windows 控制台默认非 UTF-8，中文输出会抛异常，这里统一兜底。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="utf8-search 相关性抽检（验收项 2-9）")
    parser.add_argument("--depth", default="basic", choices=["basic", "advanced", "deep"], help="搜索深度")
    parser.add_argument("--max-results", type=int, default=5, help="每条查询取前 N 条（默认 5）")
    parser.add_argument("--out", default="", help="明细 Markdown 输出路径（默认 data/relevance-<日期>.md）")
    parser.add_argument("--score-file", default="", help="已打分的 CSV（id,scores,note）；给了就只做判定，不再联网")
    parser.add_argument("--searxng", default="", help="覆盖 SearXNG 地址")
    parser.add_argument("--no-cache", action="store_true", help="采集时禁用缓存，避免复用到旧结果")
    parser.add_argument("--hygiene-out", default="", help="把「卫生度」汇总写成 JSON，便于改动前后对比")
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="按 5.3 之前的排序口径采集（关闭同站限流/聚合页/脚本/覆盖度过滤与时效意图），用于前后对比",
    )
    parser.add_argument("--no-cn-source", action="store_true", help="排除 360search，用于隔离中文源本身的贡献")
    parser.add_argument(
        "--compare-hygiene",
        nargs=2,
        default=None,
        metavar=("BEFORE", "AFTER"),
        help="对比两份卫生度 JSON（M5-5.3 验收）：同站冗余/聚合页/脚本不匹配不增加、覆盖率不下降",
    )
    return parser.parse_args()


def _domain(url: str) -> str:
    from urllib.parse import urlsplit

    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def _snippet(text: str, limit: int = 100) -> str:
    """把正文压成单行短摘要，方便人工在表格里判断相关性。"""
    flat = " ".join((text or "").split())
    return flat[:limit] + ("…" if len(flat) > limit else "")


def _escape(text: str) -> str:
    """Markdown 表格里竖线会破坏列结构，统一转义。"""
    return (text or "").replace("|", "\\|")


async def collect(args: argparse.Namespace) -> list[dict[str, object]]:
    """跑完 20 条查询，收集 top-N 明细。"""
    settings = Settings()
    if args.searxng:
        settings = settings.model_copy(update={"searxng_url": args.searxng})
    if args.no_cache:
        settings = settings.model_copy(update={"cache_enabled": False})
    if args.legacy:
        # 关闭 5.3 引入的排序侧改动，得到「改动前」口径用于 A/B；360search 用 --no-cn-source 单独隔离
        settings = settings.model_copy(
            update={
                "rank_max_per_host": 0,
                "rank_min_query_coverage": 0.0,
                "rank_drop_aggregator_pages": False,
                "rank_drop_script_mismatch": False,
                "general_recency_intent": False,
                # 候选池也要退回旧行为：旧代码的 want 就是 max_results（等于 5），
                # 否则「候选池」本身成了变量，测不出排序改动带来的差异
                "rank_candidate_pool": 1,
            }
        )
    if args.no_cn_source:
        settings = settings.model_copy(
            update={
                "default_engines": ",".join(
                    e for e in settings.engine_list if e != "360search"
                ),
                "news_general_engines": ",".join(
                    e for e in settings.news_general_engine_list if e != "360search"
                ),
            }
        )

    pipeline = await SearchPipeline.create(settings)
    collected: list[dict[str, object]] = []
    try:
        for index, (category, query) in enumerate(QUERIES, start=1):
            try:
                response = await pipeline.search(
                    SearchRequest(query=query, max_results=args.max_results, depth=args.depth)
                )
                items = [
                    {
                        "rank": rank,
                        "title": result.title or "(无标题)",
                        "url": result.url,
                        "domain": _domain(result.url),
                        "chars": len(result.content or ""),
                        "snippet": _snippet(result.content or ""),
                        "published_date": result.published_date or "",
                        "score": result.score,
                        # 卫生度统计（覆盖率 / 空内容）要读完整摘要：snippet 已截断到 100 字，
                        # 用它算覆盖率会把「正文里出现查询词」的结果误判成低覆盖。
                        # 键名固定为 "content"，与 verify.metrics.summarize_result_hygiene 对齐。
                        "content": result.content or "",
                    }
                    for rank, result in enumerate(response.results, start=1)
                ]
                # 卫生度指标（M5-5.3）：客观、可自动化，用于对比改动前后的结果质量
                hygiene = summarize_result_hygiene(items, query)
                collected.append(
                    {
                        "id": index,
                        "category": category,
                        "query": query,
                        "items": items,
                        "engines": response.engines_used,
                        "failed_engines": response.failed_engines,
                        "hygiene": hygiene,
                        "error": "",
                    }
                )
                print(
                    f"[{index:>2}/20] {category} {query} -> {len(items)} 条  "
                    f"覆盖 {hygiene['coverage_mean']:.2f}  同站冗余 {hygiene['same_host_excess']:.0f}  "
                    f"聚合页 {hygiene['aggregator']:.0f}  脚本不匹配 {hygiene['script_mismatch']:.0f}  "
                    f"空内容 {hygiene['empty_content']:.0f}"
                )
            except Exception as exc:  # noqa: BLE001 - 单条查询失败不应中断整轮抽检
                collected.append(
                    {
                        "id": index,
                        "category": category,
                        "query": query,
                        "items": [],
                        "engines": [],
                        "failed_engines": [],
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                print(f"[{index:>2}/20] {category} {query} -> 失败: {exc}")
    finally:
        await pipeline.close()
    return collected


def write_report(collected: list[dict[str, object]], args: argparse.Namespace, out: Path) -> Path:
    """把明细写成 Markdown，并生成人工打分模板 CSV。"""
    min_pass_queries = math.ceil(len(QUERIES) * MIN_PASS_RATIO)  # 20 × 90% → 18
    cache_state = (
        "已禁用缓存（`--no-cache`），全部为本次实时采集"
        if args.no_cache
        else "启用缓存（未传 `--no-cache`），可能复用到历史结果"
    )
    lines: list[str] = [
        "# 相关性抽检报告（验收项 2-9）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 深度模式：{args.depth}，每条取前 {args.max_results} 条",
        "- 查询构成：20 条中英混合，覆盖 新闻 / 技术 / 政策 / 商品 各 5 条",
        f"- **采集缓存状态**：{cache_state}",
        "",
        "## 打分规则（先读这三条）",
        "",
        f"1. **门槛**：20 条查询里，满足「top5 中相关条数 ≥ {PER_QUERY_MIN}」的查询数要 **≥ "
        f"{min_pass_queries} 条**（即 ≥ {MIN_PASS_RATIO:.0%}）。",
        f"2. **scores 的 {args.max_results} 位依次对应排名 1-{args.max_results}**"
        "（第 1 位 = 排名第 1 的结果），逐位填 0/1。",
        "3. **非零数字一律视为「相关」**（填 1 最规范；填 2 或其它非零值同样按相关计）。",
        "",
        f"- 判定命令：`python scripts/relevance.py --score-file {out.with_name(out.stem + '-scores.csv').name}`",
        f"- 通过标准（脚本口径）：top5 中相关数 ≥ {PER_QUERY_MIN} 的查询占比 ≥ {MIN_PASS_RATIO:.0%}",
        f"- 速览版（不带正文字数/发布时间/URL）：`{out.with_name(out.stem + '-brief.md').name}`",
        "",
    ]

    for entry in collected:
        lines.append(f"## {entry['id']}. [{entry['category']}] {entry['query']}")
        lines.append("")
        if entry["error"]:
            lines.append(f"> 查询失败：{entry['error']}")
            lines.append("")
            continue
        if not entry["items"]:
            lines.append("> 无结果")
            lines.append("")
            continue
        lines.append(f"引擎：{', '.join(entry['engines']) or '-'}；失败引擎：{', '.join(entry['failed_engines']) or '-'}")
        hygiene = entry.get("hygiene") or {}
        if hygiene:
            lines.append(
                f"卫生度：覆盖 {hygiene['coverage_mean']:.2f}（最低 {hygiene['coverage_min']:.2f}）"
                f" · 同站冗余 {hygiene['same_host_excess']:.0f} · 聚合页 {hygiene['aggregator']:.0f}"
                f" · 脚本不匹配 {hygiene['script_mismatch']:.0f} · 空内容 {hygiene['empty_content']:.0f}"
                f" · 独立站点 {hygiene['distinct_hosts']:.0f}"
            )
        lines.append("")
        lines.append("| 排名 | 标题 | 域名 | 正文字数 | 发布时间 | 内容开头 | URL |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for item in entry["items"]:
            lines.append(
                f"| {item['rank']} | {_escape(str(item['title']))} | {_escape(str(item['domain']))} | "
                f"{item['chars']} | {item['published_date'] or '-'} | {_escape(str(item['snippet']))} | "
                f"{_escape(str(item['url']))} |"
            )
        lines.append("")

    summary = _aggregate_hygiene(collected)
    lines.extend(_hygiene_section(summary))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    template = out.with_name(out.stem + "-scores.csv")
    with template.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "scores", "note"])
        for entry in collected:
            writer.writerow([entry["id"], "", ""])
    print(f"\n明细报告: {out.resolve()}")
    print(f"打分模板: {template.resolve()}")
    write_brief(collected, args, out)
    print("提示：scores 填 5 个 0/1（第 1 位对应排名第 1 的结果），填好后用 --score-file 判定")
    return out


def write_brief(collected: list[dict[str, object]], args: argparse.Namespace, out: Path) -> Path:
    """写「速览版」明细：每条查询 5 行，「打勾位 | 标题 | 域名 | 摘要 80 字」，便于快速打分。

    刻意去掉正文字数 / 发布时间 / URL 等干扰列；标题与摘要仍与明细报告同源（同一批采集结果）。
    """
    lines: list[str] = [
        "# 相关性抽检速览版（验收项 2-9，配合同名 `-scores.csv` 使用）",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 深度模式：{args.depth}；每条查询 5 行，第一列是「打勾位」（= 排名，填到 scores 的对应位）",
        "- 打分：**非零即为相关**；门槛 20 条里 ≥18 条满足「相关 ≥4」",
        "",
    ]
    for entry in collected:
        lines.append(f"## {entry['id']}. [{entry['category']}] {entry['query']}")
        lines.append("")
        if entry["error"]:
            lines.append(f"> 查询失败：{entry['error']}")
            lines.append("")
            continue
        if not entry["items"]:
            lines.append("> 无结果")
            lines.append("")
            continue
        lines.append("| 打勾位 | 标题 | 域名 | 摘要 |")
        lines.append("| --- | --- | --- | --- |")
        for item in entry["items"]:
            snippet = _escape(_snippet(str(item.get("content") or item.get("snippet") or ""), limit=80))
            lines.append(
                f"| {item['rank']} | {_escape(str(item['title']))} | "
                f"{_escape(str(item['domain']))} | {snippet} |"
            )
        lines.append("")
    brief = out.with_name(out.stem + "-brief.md")
    brief.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"速览版: {brief.resolve()}")
    return brief


def _aggregate_hygiene(collected: list[dict[str, object]]) -> dict[str, float]:
    """把逐条查询的卫生度汇总成整体指标（对各查询取均值/求和）。"""
    entries = [entry["hygiene"] for entry in collected if entry.get("hygiene")]
    if not entries:
        return {}
    total = sum(float(e["total"]) for e in entries) or 1.0
    summary: dict[str, float] = {"queries": float(len(entries)), "total": total}
    for key in ("same_host_excess", "aggregator", "script_mismatch", "empty_content"):
        summary[key] = sum(float(e[key]) for e in entries)
    # 覆盖率按结果条数加权平均，避免「结果少的查询」被同等看待
    summary["coverage_mean"] = (
        sum(float(e["coverage_mean"]) * float(e["total"]) for e in entries) / total
    )
    summary["distinct_hosts_mean"] = statistics.fmean(float(e["distinct_hosts"]) for e in entries)
    return summary


def _hygiene_section(summary: dict[str, float]) -> list[str]:
    """生成 Markdown 的卫生度汇总小节。"""
    if not summary:
        return []
    lines = [
        "## 卫生度汇总（M5-5.3，客观指标）",
        "",
        "| 指标 | 值 | 含义 |",
        "| --- | --- | --- |",
        f"| 结果总数 | {summary['total']:.0f} | 20 条查询的 top-N 合计 |",
        f"| 查询词覆盖率（加权） | {summary['coverage_mean']:.3f} | 越高说明结果越贴题 |",
        f"| 同站冗余 | {summary['same_host_excess']:.0f} | 同一可注册域超出上限的条数 |",
        f"| 聚合页 | {summary['aggregator']:.0f} | 站点首页/栏目页这类「只是导航」的结果 |",
        f"| 非中英文脚本 | {summary['script_mismatch']:.0f} | 中文查询下混入的俄语/韩语等标题 |",
        f"| 空内容 | {summary['empty_content']:.0f} | 摘要不足 40 字、对 LLM 无价值 |",
        f"| 平均独立站点数 | {summary['distinct_hosts_mean']:.1f} | 来源分散度 |",
        "",
    ]
    return lines


def compare_hygiene(before_path: str, after_path: str) -> int:
    """对比两份卫生度 JSON（M5-5.3 验收 5.3-8）。"""
    before = json.loads(Path(before_path).read_text(encoding="utf-8"))
    after = json.loads(Path(after_path).read_text(encoding="utf-8"))
    passed, notes, details = evaluate_hygiene_delta(before=before, after=after)
    print("\n== 卫生度对比（改动前 -> 改动后） ==")
    keys = ["total", "coverage_mean", "same_host_excess", "aggregator", "script_mismatch", "empty_content"]
    for key in keys:
        print(f"  {key:<18} {float(before.get(key, 0)):>9.3f} -> {float(after.get(key, 0)):>9.3f}")
    print("\n结论：" + ("通过" if passed else "不通过"))
    for note in notes:
        print("  - " + note)
    return 0 if passed else 1


def judge(score_file: str) -> int:
    """读取人工打分并输出判定结论。"""
    path = Path(score_file)
    if not path.exists():
        print(f"打分文件不存在: {path}")
        return 2

    scores: dict[str, list[int]] = {}
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(row)

    for row in rows:
        raw_id = (row.get("id") or "").strip()
        raw_scores = (row.get("scores") or "").strip()
        if not raw_id or not raw_scores:
            continue
        try:
            index = int(raw_id)
        except ValueError:
            continue
        if index < 1 or index > len(QUERIES):
            print(f"忽略越界的 id: {raw_id}")
            continue
        values = [1 if char in "123456789" else 0 for char in raw_scores]
        label = f"{index}. [{QUERIES[index - 1][0]}] {QUERIES[index - 1][1]}"
        scores[label] = values

    if not scores:
        print("打分文件里没有有效数据（id 与 scores 均不能为空）")
        return 2

    passed, notes, details = evaluate_relevance(scores, per_query_min=PER_QUERY_MIN, min_pass_ratio=MIN_PASS_RATIO)

    print("\n== 逐条结果 ==")
    for label, values in scores.items():
        count = sum(1 for value in values if value >= 1)
        flag = "OK " if count >= PER_QUERY_MIN else "NG "
        print(f"{flag}{count}/{len(values)}  {label}")

    print("\n== 判定 ==")
    print(f"查询数        : {details['queries']}")
    print(f"达标查询数    : {details['passed_queries']}（门槛 top{len(next(iter(scores.values())))} 相关 ≥ {PER_QUERY_MIN}）")
    print(f"达标占比      : {details['pass_ratio']:.0%}（门槛 {MIN_PASS_RATIO:.0%}）")
    print(f"平均相关条数  : {details['avg_relevant']:.2f}")
    print("\n结论：" + ("通过" if passed else "不通过") + " — " + "；".join(notes))

    report = path.with_name(path.stem + "-judge.md")
    report.write_text(
        "\n".join(
            [
                "# 相关性抽检判定（验收项 2-9）",
                "",
                f"- 判定时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"- 打分文件：`{path.name}`",
                "",
                "## 逐条结果",
                "",
                "| 结论 | 相关数 | 查询 |",
                "| --- | --- | --- |",
                *[
                    f"| {'✅' if sum(1 for v in values if v >= 1) >= PER_QUERY_MIN else '❌'} "
                    f"| {sum(1 for v in values if v >= 1)}/{len(values)} | {label} |"
                    for label, values in scores.items()
                ],
                "",
                "## 判定",
                "",
                f"- 达标占比：{details['pass_ratio']:.0%}（门槛 {MIN_PASS_RATIO:.0%}）",
                f"- 平均相关条数：{details['avg_relevant']:.2f}",
                f"- 结论：**{'通过' if passed else '不通过'}** — {'；'.join(notes)}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"判定报告: {report.resolve()}")
    return 0 if passed else 1


def main() -> int:
    _configure_stdout()
    args = parse_args()
    if args.compare_hygiene:
        return compare_hygiene(*args.compare_hygiene)
    if args.score_file:
        return judge(args.score_file)

    out = Path(args.out) if args.out else Path(f"data/relevance-{datetime.now().strftime('%Y%m%d')}.md")
    collected = asyncio.run(collect(args))
    write_report(collected, args, out)
    if args.hygiene_out:
        summary = _aggregate_hygiene(collected)
        target = Path(args.hygiene_out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"卫生度汇总: {target.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
