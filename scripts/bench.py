"""延迟基准脚本：对每个深度模式跑 N 次真实查询，输出 P50 / P90 / P95 与命中情况。

用法（需先启动 SearXNG）：
    python scripts/bench.py --n 10 --modes basic,advanced,deep
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

# 中英混合的测试查询（覆盖中文时效性与外网英文信息）
QUERIES = [
    "2026年 人工智能 政策",
    "最近一周 AI 领域重要新闻",
    "OpenAI API 定价",
    "Python 3.13 新特性",
    "国产大模型 排行榜 2026",
    "GPT-6 上下文窗口",
    "新能源汽车 销量 最新",
    "MCP protocol latest specification",
]


async def run_mode(pipeline: SearchPipeline, mode: str, count: int) -> dict[str, object]:
    """对指定深度模式执行 count 次查询并统计耗时。"""
    latencies: list[float] = []
    pages: list[int] = []
    cached = 0
    failures = 0

    for index in range(count):
        query = QUERIES[index % len(QUERIES)]
        request = SearchRequest(query=query, max_results=5, depth=mode)  # type: ignore[arg-type]
        started = time.perf_counter()
        try:
            response = await pipeline.search(request)
        except Exception as exc:
            failures += 1
            print(f"    查询失败: {query} -> {exc}")
            continue
        latencies.append((time.perf_counter() - started) * 1000)
        pages.append(response.pages_read)
        cached += 1 if response.cached else 0
        print(
            f"    [{index + 1}/{count}] {query[:24]:<26} {latencies[-1]:7.0f} ms  "
            f"结果 {len(response.results):>2} 条  读页 {response.pages_read:>2}  "
            f"引擎 {','.join(response.engines_used) or '-'}"
            + ("  (缓存)" if response.cached else "")
        )

    if not latencies:
        return {"mode": mode, "count": 0, "failures": failures}

    latencies.sort()
    return {
        "mode": mode,
        "count": len(latencies),
        "failures": failures,
        "p50": statistics.median(latencies),
        "p90": latencies[int(len(latencies) * 0.9) - 1],
        "p95": latencies[int(len(latencies) * 0.95) - 1] if len(latencies) > 3 else latencies[-1],
        "max": latencies[-1],
        "avg_pages": statistics.mean(pages) if pages else 0,
        "cached": cached,
    }


async def wait_for_searxng(provider, url: str, *, timeout: float = 90.0) -> bool:
    """等待 SearXNG 就绪：容器刚启动时首次查询需要加载引擎，过早请求会拿到 502。"""
    started = time.perf_counter()
    while time.perf_counter() - started < timeout:
        if await provider.health():
            elapsed = time.perf_counter() - started
            print(f"SearXNG ({url}) 就绪，用时 {elapsed:.1f}s")
            return True
        await asyncio.sleep(3)
    print(f"SearXNG ({url}) 在 {timeout:.0f}s 内未就绪")
    return False


async def main() -> None:
    parser = argparse.ArgumentParser(description="utf8-search 延迟基准")
    parser.add_argument("--n", type=int, default=5, help="每个模式的采样次数")
    parser.add_argument("--modes", default="basic,advanced,deep", help="逗号分隔的深度模式")
    parser.add_argument("--searxng", default="", help="覆盖 SearXNG 地址")
    parser.add_argument("--fresh", action="store_true", help="跑之前清空缓存，测量冷启动真实延迟")
    args = parser.parse_args()

    settings = Settings()
    if args.searxng:
        settings = settings.model_copy(update={"searxng_url": args.searxng})

    if args.fresh:
        for suffix in ("", "-wal", "-shm"):
            path = Path(settings.cache_path + suffix)
            if path.exists():
                path.unlink()
        print("缓存已清空（冷启动测量）")

    pipeline = await SearchPipeline.create(settings)
    try:
        searxng = pipeline.providers[0]
        searxng_ok = await wait_for_searxng(searxng, settings.searxng_url, timeout=90)
        if not searxng_ok:
            print("提示：请先执行 docker compose up -d searxng（容器启动后首次查询需要加载引擎，通常需 20-60 秒）")
            return

        summaries = []
        for mode in [m.strip() for m in args.modes.split(",") if m.strip()]:
            print(f"\n== 模式 {mode} ==")
            summaries.append(await run_mode(pipeline, mode, args.n))

        print("\n== 汇总 ==")
        print(f"{'模式':<10}{'采样':>5}{'失败':>6}{'P50':>9}{'P90':>9}{'P95':>9}{'最大':>9}{'平均读页':>9}{'缓存命中':>9}")
        for item in summaries:
            if not item.get("count"):
                print(f"{item['mode']:<10}   0  （无有效样本）")
                continue
            print(
                f"{item['mode']:<10}{item['count']:>5}{item['failures']:>6}"
                f"{item['p50']:>8.0f}ms{item['p90']:>8.0f}ms{item['p95']:>8.0f}ms{item['max']:>8.0f}ms"
                f"{item['avg_pages']:>9.1f}{item['cached']:>9}"
            )
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())