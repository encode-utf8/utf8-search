"""并发压测：向运行中的服务发起 N 个请求，统计状态码分布与延迟分位。

对应验收项 3-3（详见 `docs/04-后续路线图.md` 第 4.4 节）。走真实 HTTP 链路，
因此一次性覆盖「鉴权 + 限流 + 缓存 + 搜索流水线」的全链路。

用法（先在另一个终端起服务）：
    $env:UTF8SEARCH_API_KEYS="test123"
    $env:UTF8SEARCH_RATE_LIMIT_RPM="0"     # 压测期间关掉限流，否则会拿到 429
    utf8-search serve --host 127.0.0.1 --port 8000

    python scripts/loadtest.py --concurrency 10 --n 50 --api-key test123

判定标准：无 5xx、无超时即通过（逻辑见 `utf8_search.verify.metrics.evaluate_load_test`）。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import httpx  # noqa: E402

from utf8_search.verify.metrics import (  # noqa: E402
    evaluate_load_test,
    format_bytes,
    read_rss_bytes,
    summarize_latencies,
)

# 中英混合查询池；默认每个请求加随机后缀，避免命中缓存导致压不到真实抓取链路
QUERIES = [
    "2026年 人工智能 政策",
    "最近一周 AI 领域重要新闻",
    "OpenAI API 定价",
    "Python 3.13 新特性",
    "国产大模型 排行榜 2026",
    "新能源汽车 销量 最新",
    "MCP protocol latest specification",
    "best noise cancelling headphones 2026",
]


def _configure_stdout() -> None:
    """Windows 控制台默认非 UTF-8，中文输出会抛异常，这里统一兜底。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="utf8-search 并发压测（验收项 3-3）")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="服务基础地址")
    parser.add_argument("--api-key", default="", help="API Key（服务开启鉴权时必填）")
    parser.add_argument("--concurrency", type=int, default=10, help="并发数")
    parser.add_argument("--n", type=int, default=50, help="总请求数")
    parser.add_argument("--mode", default="basic", help="深度模式；多个用逗号分隔并按请求轮换，如 basic,advanced")
    parser.add_argument("--max-results", type=int, default=5, help="每次查询返回的结果数")
    parser.add_argument("--timeout", type=float, default=60.0, help="单个请求的超时（秒）")
    parser.add_argument("--warmup", type=int, default=2, help="预热请求数（不计入统计）")
    parser.add_argument(
        "--reuse-cache",
        action="store_true",
        help="复用缓存（不加随机后缀）。默认不复用，以便压到真实抓取链路",
    )
    parser.add_argument("--rss-pid", type=int, default=0, help="服务进程 PID，用于记录压测前后内存")
    parser.add_argument("--trust-env", action="store_true", help="遵循系统代理环境变量（默认直连，避免本机代理干扰）")
    parser.add_argument("--json", dest="json_out", default="", help="把每次请求的原始结果写入该 JSON 文件")
    parser.add_argument("--verbose", action="store_true", help="逐条打印请求结果")
    return parser.parse_args()


async def _one_request(
    client: httpx.AsyncClient,
    *,
    search_url: str,
    headers: dict[str, str],
    query: str,
    mode: str,
    max_results: int,
) -> dict[str, object]:
    """发一个搜索请求，返回状态码与耗时（异常也被归一化成结果，不向上抛）。"""
    payload = {"query": query, "search_depth": mode, "max_results": max_results}
    started = time.perf_counter()
    try:
        response = await client.post(search_url, headers=headers, json=payload)
        return {
            "query": query,
            "mode": mode,
            "status": response.status_code,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "error": None,
            "detail": "",
        }
    except httpx.TimeoutException as exc:
        return {
            "query": query,
            "mode": mode,
            "status": None,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "error": "timeout",
            "detail": str(exc),
        }
    except Exception as exc:  # noqa: BLE001 - 连接被拒 / 协议错误等统一归为传输错误
        return {
            "query": query,
            "mode": mode,
            "status": None,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "error": "transport",
            "detail": str(exc),
        }


async def run(args: argparse.Namespace) -> int:
    search_url = args.url.rstrip("/") + "/v1/search"
    headers = {"content-type": "application/json"}
    if args.api_key:
        headers["x-api-key"] = args.api_key
    modes = [m.strip() for m in args.mode.split(",") if m.strip()] or ["basic"]

    # 每个请求加一个本次运行独有的后缀，保证不命中共用缓存
    run_id = f"{int(time.time()) % 100000}-{args.n}"

    limits = httpx.Limits(max_connections=args.concurrency + 4, max_keepalive_connections=args.concurrency + 4)
    rss_before = read_rss_bytes(args.rss_pid) if args.rss_pid else None

    print(f"目标: {search_url}")
    print(f"请求: {args.n} 个，并发 {args.concurrency}，模式 {','.join(modes)}，超时 {args.timeout:.0f}s")
    print(f"缓存: {'复用' if args.reuse_cache else '不复用（每请求唯一查询）'}")

    async with httpx.AsyncClient(limits=limits, timeout=args.timeout, trust_env=args.trust_env) as client:
        for index in range(args.warmup):
            query = QUERIES[index % len(QUERIES)] + f" #{run_id}-warm{index}"
            result = await _one_request(
                client,
                search_url=search_url,
                headers=headers,
                query=query,
                mode=modes[index % len(modes)],
                max_results=args.max_results,
            )
            status = result["status"] if result["status"] is not None else result["error"]
            print(f"预热 {index + 1}/{args.warmup}: {status} {result['latency_ms']:.0f}ms")

        semaphore = asyncio.Semaphore(args.concurrency)

        async def task(index: int) -> dict[str, object]:
            async with semaphore:
                query = QUERIES[index % len(QUERIES)]
                if not args.reuse_cache:
                    query = f"{query} #{run_id}-{index}"
                return await _one_request(
                    client,
                    search_url=search_url,
                    headers=headers,
                    query=query,
                    mode=modes[index % len(modes)],
                    max_results=args.max_results,
                )

        started = time.perf_counter()
        results = await asyncio.gather(*(task(index) for index in range(args.n)))
        wall = time.perf_counter() - started

    rss_after = read_rss_bytes(args.rss_pid) if args.rss_pid else None

    if args.verbose:
        for item in results:
            status = item["status"] if item["status"] is not None else item["error"]
            print(f"  {status} {item['latency_ms']:7.0f}ms  {str(item['query'])[:40]}")

    succeeded = [r for r in results if r["status"] and 200 <= r["status"] < 300]
    server_errors = [r for r in results if r["status"] and r["status"] >= 500]
    client_errors = [r for r in results if r["status"] and 400 <= r["status"] < 500]
    rate_limited = [r for r in client_errors if r["status"] == 429]
    timeouts = [r for r in results if r["error"] == "timeout"]
    transport_errors = [r for r in results if r["error"] == "transport"]

    stats = summarize_latencies([float(r["latency_ms"]) for r in succeeded])
    passed, notes = evaluate_load_test(
        total=len(results),
        succeeded=len(succeeded),
        server_errors=len(server_errors),
        timeouts=len(timeouts),
        transport_errors=len(transport_errors),
        client_errors=len(client_errors),
    )

    print("\n== 压测结果 ==")
    print(f"请求总数      : {len(results)}（并发 {args.concurrency}）")
    print(f"成功 2xx      : {len(succeeded)}")
    print(f"客户端 4xx    : {len(client_errors)}（其中 429 限流 {len(rate_limited)}）")
    print(f"服务端 5xx    : {len(server_errors)}")
    print(f"请求超时      : {len(timeouts)}")
    print(f"连接/传输错误 : {len(transport_errors)}")
    print(f"墙钟耗时      : {wall:.2f}s（吞吐 {len(results) / wall:.1f} req/s）")
    if stats["count"]:
        print(
            f"延迟（成功）  : P50 {stats['p50']:.0f}ms  P90 {stats['p90']:.0f}ms  "
            f"P95 {stats['p95']:.0f}ms  max {stats['max']:.0f}ms  mean {stats['mean']:.0f}ms"
        )
    if rss_before is not None and rss_after is not None:
        print(f"服务内存      : {format_bytes(rss_before)} -> {format_bytes(rss_after)}（{format_bytes(rss_after - rss_before)}）")

    if timeouts:
        for item in timeouts[:5]:
            print(f"  超时详情: {item['query']} -> {item['detail']}")
    if transport_errors:
        for item in transport_errors[:5]:
            print(f"  传输错误: {item['query']} -> {item['detail']}")

    print("\n结论：" + ("通过" if passed else "不通过") + " — " + "；".join(notes))

    if args.json_out:
        payload = {
            "target": search_url,
            "concurrency": args.concurrency,
            "n": args.n,
            "mode": args.mode,
            "wall_seconds": wall,
            "rss_before": rss_before,
            "rss_after": rss_after,
            "summary": {
                "succeeded": len(succeeded),
                "client_errors": len(client_errors),
                "rate_limited": len(rate_limited),
                "server_errors": len(server_errors),
                "timeouts": len(timeouts),
                "transport_errors": len(transport_errors),
                **stats,
            },
            "passed": passed,
            "notes": notes,
            "results": results,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"原始结果已写入 {args.json_out}")

    return 0 if passed else 1


def main() -> int:
    _configure_stdout()
    args = parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n已中断")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())