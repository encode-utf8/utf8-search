"""引擎健康度自适应 A/B 基准（验收项 5.1-13）。

对同一批中英查询，分别用「静态引擎名单」与「健康度自适应」跑同一套端到端流水线，
对比结果条数、端到端 P50/P95、上游异常引擎次数、空结果条数。

判定标准见 `utf8_search.verify.metrics.evaluate_engine_health_ab`：覆盖率不下降是硬指标
（用户要求「稳健的运行效果」，而不是一味降级）。

用法（需先启动 SearXNG）：
    python scripts/bench_engines.py --rounds 2 --out data/bench-engines-20260924.md
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.verify.metrics import evaluate_engine_health_ab, percentile  # noqa: E402

# 中英混合：中文为主（首要受众），同时覆盖外网英文信息
QUERIES = [
    "2026年 人工智能 政策",
    "台风 最新消息 路径",
    "扫地机器人 推荐 性价比",
    "2026年 新能源汽车 补贴政策",
    "MCP protocol specification 2026",
    "OpenAI latest news",
    "EU AI Act compliance requirements",
    "Rust async runtime tokio",
]

MODE_STATIC = "静态引擎名单"
MODE_ADAPTIVE = "健康度自适应"


async def build_pipeline(settings: Settings, *, adaptive: bool) -> SearchPipeline:
    """按模式构造流水线：关闭结果缓存，保证每次都真的打上游。"""
    return await SearchPipeline.create(
        settings.model_copy(update={"engine_health_enabled": adaptive, "cache_enabled": False})
    )


async def run_mode(
    pipeline: SearchPipeline, queries: list[str], *, warmup: bool, label: str
) -> list[dict[str, float]]:
    """跑一轮查询，返回每条的 {latency_ms, results, failed}。"""
    rows: list[dict[str, float]] = []
    total = len(queries) + (1 if warmup else 0)
    for index in range(total):
        warm = warmup and index == 0
        query = queries[(index - (1 if warmup else 0)) % len(queries)]
        request = SearchRequest(query=query, max_results=10, depth="basic")  # type: ignore[arg-type]
        started = time.perf_counter()
        try:
            response = await pipeline.search(request)
        except Exception as exc:  # noqa: BLE001 - 基准脚本要把失败也记进样本
            print(f"    [{label}] 查询失败: {query} -> {exc}")
            continue
        latency = (time.perf_counter() - started) * 1000
        if warm:
            print(f"    [{label}] 预热 {query[:22]:<24} {latency:7.0f} ms")
            continue
        rows.append(
            {
                "latency_ms": latency,
                "results": float(len(response.results)),
                "failed": float(len(response.failed_engines)),
            }
        )
        print(
            f"    [{label}] {query[:22]:<24} {latency:7.0f} ms  结果 {len(response.results):>2} 条  "
            f"异常引擎 {len(response.failed_engines):>2}"
        )
    return rows


def summarize(rows: list[dict[str, float]]) -> dict[str, float]:
    """把逐条样本汇总成判定用的指标。"""
    if not rows:
        return {"count": 0, "results_median": 0, "p50": 0, "p95": 0, "failures": 0, "empty": 0}
    latencies = sorted(row["latency_ms"] for row in rows)
    return {
        "count": len(rows),
        "results_median": statistics.median([row["results"] for row in rows]),
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
        "mean": statistics.fmean(latencies),
        "failures": sum(row["failed"] for row in rows),
        "empty": sum(1 for row in rows if row["results"] == 0),
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="引擎健康度自适应 A/B 基准（M5-5.1）")
    parser.add_argument("--rounds", type=int, default=2, help="每个模式跑几轮（每轮覆盖全部查询）")
    parser.add_argument("--max-results", type=int, default=10, help="每次查询要的结果条数")
    parser.add_argument("--out", type=str, default="", help="Markdown 报告输出路径")
    args = parser.parse_args()

    settings = Settings()
    print(f"SearXNG: {settings.searxng_url}  自适应开关: {settings.engine_health_enabled}")
    print(f"默认引擎: {settings.default_engines}")

    static_pipe = await build_pipeline(settings, adaptive=False)
    adaptive_pipe = await build_pipeline(settings, adaptive=True)
    static_rows: list[dict[str, float]] = []
    adaptive_rows: list[dict[str, float]] = []
    paired: list[float] = []
    try:
        for round_index in range(max(1, args.rounds)):
            print(f"\n===== 第 {round_index + 1}/{args.rounds} 轮 =====")
            # 逐条交替两种模式：既抵消上游健康度随时间漂移，也构成同一 (查询, 轮次) 的配对样本
            for query_index, query in enumerate(QUERIES):
                order = (
                    [(MODE_STATIC, static_pipe), (MODE_ADAPTIVE, adaptive_pipe)]
                    if query_index % 2 == 0
                    else [(MODE_ADAPTIVE, adaptive_pipe), (MODE_STATIC, static_pipe)]
                )
                latencies: dict[str, float] = {}
                for label, pipeline in order:
                    rows = await run_mode(
                        pipeline, [query], warmup=(round_index == 0 and query_index == 0), label=label
                    )
                    (static_rows if label == MODE_STATIC else adaptive_rows).extend(rows)
                    if rows:
                        latencies[label] = rows[0]["latency_ms"]
                if len(latencies) == 2:
                    paired.append(latencies[MODE_ADAPTIVE] - latencies[MODE_STATIC])
    finally:
        await static_pipe.close()
        await adaptive_pipe.close()

    static_summary = summarize(static_rows)
    adaptive_summary = summarize(adaptive_rows)
    paired_median = statistics.median(paired) if paired else None
    passed, notes, details = evaluate_engine_health_ab(
        static=static_summary,
        adaptive=adaptive_summary,
        paired_delta_median=paired_median,
    )
    if paired:
        details["paired"] = {
            "count": len(paired),
            "median_delta": paired_median,
            "mean_delta": statistics.fmean(paired),
            "adaptive_faster_ratio": sum(1 for delta in paired if delta < 0) / len(paired),
        }

    print("\n===== 汇总 =====")
    for label, summary in ((MODE_STATIC, static_summary), (MODE_ADAPTIVE, adaptive_summary)):
        print(
            f"{label:<12} n={summary['count']:>3}  结果数中位={summary['results_median']:.0f}  "
            f"P50={summary['p50']:.0f}ms  均值={summary.get('mean', 0):.0f}ms  P95={summary['p95']:.0f}ms  "
            f"异常引擎次数={summary['failures']:.0f}  空结果={summary['empty']:.0f}"
        )
    if paired:
        faster = sum(1 for delta in paired if delta < 0) / len(paired)
        print(
            f"配对样本 n={len(paired)}  差值中位={paired_median:+.0f}ms  "
            f"均值={statistics.fmean(paired):+.0f}ms  自适应更快的比例={faster:.0%}"
        )
    print("\n判定：" + ("通过" if passed else "不通过"))
    for note in notes:
        print("  - " + note)

    if args.out:
        report = render_report(settings, static_summary, adaptive_summary, details, notes, passed)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"\n报告已写入 {out_path}")
    return 0 if passed else 1


def render_report(
    settings: Settings,
    static_summary: dict[str, float],
    adaptive_summary: dict[str, float],
    details: dict[str, object],
    notes: list[str],
    passed: bool,
) -> str:
    """生成 Markdown 报告（便于直接贴进 checklist）。"""
    lines = [
        "# 引擎健康度自适应 A/B 基准（M5-5.1 验收 5.1-13）",
        "",
        f"- SearXNG：`{settings.searxng_url}`",
        f"- 查询数：{details.get('count', 0)} 条/模式（中英混合，逐条交替两种模式以抵消上游漂移）",
        f"- 配对样本：{details.get('paired', {}).get('count', 0)} 对"
        f"（差值中位 {details.get('paired', {}).get('median_delta', 0):+.0f} ms，"
        f"自适应更快的比例 {details.get('paired', {}).get('adaptive_faster_ratio', 0):.0%}）",
        f"- 候选引擎：`{settings.default_engines}`",
        "",
        "| 模式 | 样本 | 结果数中位 | P50 | P95 | 上游异常引擎次数 | 空结果条数 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        f"| {MODE_STATIC} | {static_summary['count']:.0f} | {static_summary['results_median']:.1f} | "
        f"{static_summary['p50']:.0f} ms | {static_summary['p95']:.0f} ms | {static_summary['failures']:.0f} | "
        f"{static_summary['empty']:.0f} |",
        f"| {MODE_ADAPTIVE} | {adaptive_summary['count']:.0f} | {adaptive_summary['results_median']:.1f} | "
        f"{adaptive_summary['p50']:.0f} ms | {adaptive_summary['p95']:.0f} ms | {adaptive_summary['failures']:.0f} | "
        f"{adaptive_summary['empty']:.0f} |",
        "",
        f"**判定：{'通过' if passed else '不通过'}**",
        "",
    ]
    lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))