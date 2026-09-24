"""长稳（soak）测试：按固定间隔查询，逐行记录成功率与进程 RSS。

对应验收项 3-4（详见 `docs/04-后续路线图.md` 第 4.4 节）。

默认在**本进程内**构造流水线（不额外起服务），这样采样到的 RSS 就是服务本体的内存，
而不是「客户端进程 + 服务进程」两份开销；也可以配合 `--http-url` 打已运行的服务。

用法：
    python scripts/soak.py --duration-hours 24 --interval 300     # 正式挂机
    python scripts/soak.py --duration-hours 0.1 --interval 60     # 快速自检
    python scripts/soak.py --http-url http://127.0.0.1:8000 --api-key test123 --rss-pid 1234

判定标准：可用率 ≥ 99% 且内存无持续增长（逻辑见 `utf8_search.verify.metrics.evaluate_soak`）。
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.verify.metrics import (  # noqa: E402
    evaluate_soak,
    format_bytes,
    read_rss_bytes,
    summarize_latencies,
)

# 中英混合查询池：轮换使用且**不加随机后缀**，让缓存发挥兜底作用，
# 既贴近真实用法，也避免 24 小时持续猛打免费上游引擎。
QUERIES = [
    "2026年 人工智能 政策",
    "最近一周 AI 领域重要新闻",
    "Python 3.13 新特性",
    "MCP protocol latest specification",
    "国产大模型 排行榜 2026",
    "新能源汽车 销量 最新",
    "OpenAI API 定价",
    "best noise cancelling headphones 2026",
]

COLUMNS = [
    "index",
    "timestamp",
    "elapsed_s",
    "warmup",
    "ok",
    "latency_ms",
    "results",
    "pages_read",
    "cached",
    "rss_bytes",
    "query",
    "error",
]


def _configure_stdout() -> None:
    """Windows 控制台默认非 UTF-8，中文输出会抛异常，这里统一兜底。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="utf8-search 长稳测试（验收项 3-4）")
    parser.add_argument("--duration-hours", type=float, default=24.0, help="挂机时长（小时），可用小数做短跑自检")
    parser.add_argument("--interval", type=float, default=300.0, help="查询间隔（秒）")
    parser.add_argument("--mode", default="basic", help="深度模式（basic / advanced / deep）")
    parser.add_argument("--max-results", type=int, default=5, help="每次查询返回结果数")
    parser.add_argument("--max-samples", type=int, default=0, help="最多采样多少次（0 表示不限）")
    parser.add_argument("--warmup", type=int, default=2, help="预热采样数（记录但不计入统计）")
    parser.add_argument("--out", default="data/soak.csv", help="采样明细 CSV 路径（追加写入）")
    parser.add_argument("--http-url", default="", help="改为压已运行的服务（默认在本进程内跑流水线）")
    parser.add_argument("--api-key", default="", help="配合 --http-url 使用的 API Key")
    parser.add_argument("--rss-pid", type=int, default=0, help="配合 --http-url：采样该进程的内存")
    parser.add_argument("--searxng", default="", help="覆盖 SearXNG 地址")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP 模式下单请求超时（秒）")
    parser.add_argument("--unique", action="store_true", help="给查询加随机后缀，强制不回缓存（更狠，但会持续打上游）")
    parser.add_argument("--json", dest="json_out", default="", help="把汇总结果写入该 JSON 文件")
    return parser.parse_args()


class Probe:
    """一次查询的执行器：统一封装「进程内流水线」与「HTTP 打服务」两种模式。"""

    def __init__(self, pipeline: SearchPipeline | None, client, args: argparse.Namespace) -> None:
        self.pipeline = pipeline
        self.client = client
        self.args = args
        self.run_id = f"{int(time.time()) % 100000}"

    async def run(self, index: int) -> dict[str, object]:
        query = QUERIES[index % len(QUERIES)]
        if self.args.unique:
            query = f"{query} #{self.run_id}-{index}"
        started = time.perf_counter()
        try:
            if self.pipeline is not None:
                response = await self.pipeline.search(
                    SearchRequest(query=query, max_results=self.args.max_results, depth=self.args.mode)  # type: ignore[arg-type]
                )
                results = len(response.results)
                pages = response.pages_read
                cached = response.cached
            else:
                response = await self.client.post(
                    self.args.http_url.rstrip("/") + "/v1/search",
                    headers={"content-type": "application/json", **({"x-api-key": self.args.api_key} if self.args.api_key else {})},
                    json={"query": query, "search_depth": self.args.mode, "max_results": self.args.max_results},
                )
                if response.status_code >= 400:
                    return {
                        "ok": False,
                        "latency_ms": (time.perf_counter() - started) * 1000,
                        "results": 0,
                        "pages_read": 0,
                        "cached": False,
                        "query": query,
                        "error": f"HTTP {response.status_code}",
                    }
                payload = response.json()
                results = len(payload.get("results") or [])
                pages = payload.get("pages_read") or 0
                cached = bool(payload.get("cached"))
            return {
                "ok": True,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "results": results,
                "pages_read": pages,
                "cached": cached,
                "query": query,
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001 - 长稳期间任何异常都记为一次失败，不中断挂机
            return {
                "ok": False,
                "latency_ms": (time.perf_counter() - started) * 1000,
                "results": 0,
                "pages_read": 0,
                "cached": False,
                "query": query,
                "error": f"{type(exc).__name__}: {exc}",
            }


def _print_summary(rows: list[dict[str, object]], args: argparse.Namespace) -> tuple[bool, list[str]]:
    """打印并返回长稳结论（只统计非预热样本）。"""
    measured = [row for row in rows if not row["warmup"]]
    succeeded = [row for row in measured if row["ok"]]
    rss_series = [float(row["rss_bytes"]) for row in measured if row.get("rss_bytes")]
    latencies = [float(row["latency_ms"]) for row in succeeded]
    stats = summarize_latencies(latencies)

    passed, notes, details = evaluate_soak(total=len(measured), succeeded=len(succeeded), rss_series=rss_series)

    print("\n== 长稳结果 ==")
    if measured:
        print(f"采样区间    : {measured[0]['timestamp']} -> {measured[-1]['timestamp']}（{float(measured[-1]['elapsed_s']) / 3600:.2f} h）")
    print(f"采样点数    : {len(measured)}（预热 {len(rows) - len(measured)} 个已剔除）")
    print(f"成功 / 失败 : {len(succeeded)} / {len(measured) - len(succeeded)}")
    print(f"可用率      : {details['availability']:.2%}")
    if stats["count"]:
        print(
            f"延迟        : P50 {stats['p50']:.0f}ms  P95 {stats['p95']:.0f}ms  "
            f"max {stats['max']:.0f}ms  mean {stats['mean']:.0f}ms"
        )
    if rss_series:
        print(
            f"内存        : {format_bytes(min(rss_series))}（最低） / "
            f"{format_bytes(rss_series[-1])}（末次） / {format_bytes(max(rss_series))}（峰值）"
        )
    failures = [row for row in measured if not row["ok"]]
    for row in failures[:10]:
        print(f"  失败样本 #{row['index']}: {row['error']}")
    print("\n结论：" + ("通过" if passed else "不通过 / 待定") + " — " + "；".join(notes))
    if not measured:
        print("提示：没有任何有效采样，无法判定")
    print(f"明细 CSV: {Path(args.out).resolve()}")
    return passed, notes


async def run(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    settings = Settings()
    if args.searxng:
        settings = settings.model_copy(update={"searxng_url": args.searxng})

    pipeline = None
    client = None
    if args.http_url:
        import httpx

        client = httpx.AsyncClient(timeout=args.timeout, trust_env=False)
        print(f"模式: HTTP（{args.http_url}），内存采样 PID={args.rss_pid or '未指定'}")
    else:
        pipeline = await SearchPipeline.create(settings)
        print(f"模式: 进程内流水线（SearXNG={settings.searxng_url}），内存采样 PID={os.getpid()}")

    probe = Probe(pipeline, client, args)
    rss_pid = args.rss_pid if args.http_url else os.getpid()
    if args.http_url and not args.rss_pid:
        rss_pid = 0

    print(f"计划: 每 {args.interval:.0f}s 查询一次，共 {args.duration_hours:.2f} h，模式 {args.mode}")
    print(f"明细写入: {out.resolve()}\n")

    rows: list[dict[str, object]] = []
    started = time.perf_counter()
    deadline = started + args.duration_hours * 3600
    new_file = not out.exists()

    try:
        with out.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if new_file:
                writer.writerow(COLUMNS)

            index = 0
            while time.perf_counter() < deadline:
                if args.max_samples and index >= args.max_samples:
                    break
                index += 1
                result = await probe.run(index)
                row = {
                    "index": index,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "warmup": index <= args.warmup,
                    "rss_bytes": read_rss_bytes(rss_pid) if rss_pid else None,
                    **result,
                }
                rows.append(row)
                writer.writerow([row.get(column, "") for column in COLUMNS])
                # 逐行刷盘：24h 挂机中途被中断也能看到进度
                handle.flush()

                flag = "OK " if row["ok"] else "FAIL"
                print(
                    f"[{index:>4}] {row['timestamp']} {flag} {float(row['latency_ms']):6.0f}ms "
                    f"结果 {row['results']:>2} 读页 {row['pages_read']:>2} "
                    f"RSS {format_bytes(row['rss_bytes'])} {'' if row['ok'] else row['error']}"
                )

                next_at = started + index * args.interval
                wait = next_at - time.perf_counter()
                if wait > 0:
                    await asyncio.sleep(wait)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n已中断，输出已有采样汇总")
    finally:
        if pipeline is not None:
            await pipeline.close()
        if client is not None:
            await client.aclose()

    passed, notes = _print_summary(rows, args)
    if args.json_out:
        import json

        measured = [row for row in rows if not row["warmup"]]
        payload = {
            "duration_hours": args.duration_hours,
            "interval": args.interval,
            "mode": args.mode,
            "samples": len(measured),
            "succeeded": sum(1 for row in measured if row["ok"]),
            "passed": passed,
            "notes": notes,
            "rows": rows,
        }
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"汇总 JSON: {args.json_out}")

    if not rows:
        return 2
    if len([row for row in rows if not row["warmup"]]) < 8:
        # 采样太少（多为短跑自检），不做内存趋势判定，返回 0 以免误报失败
        return 0
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