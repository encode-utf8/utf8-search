"""长稳（soak）测试：按固定间隔查询，逐行记录成功率与进程 RSS。

对应验收项 3-4（详见 `docs/04-后续路线图.md` 第 4.4 节）。

默认在**本进程内**构造流水线（不额外起服务），这样采样到的 RSS 就是服务本体的内存，
而不是「客户端进程 + 服务进程」两份开销；也可以配合 `--http-url` 打已运行的服务。

用法：
    python scripts/soak.py --duration-hours 24 --interval 300     # 正式挂机
    python scripts/soak.py --duration-hours 0.1 --interval 60     # 快速自检
    python scripts/soak.py --http-url http://127.0.0.1:8000 --api-key test123 --rss-pid 1234

     # 挂机期间/之后随时可用（不启动采样）：
    python scripts/soak.py --status --out data/soak-24h.csv        # 存活 / 心跳 / 进度 / 当前结论
    python scripts/soak.py --summarize --out data/soak-24h.csv --json data/soak-24h.json

挂机健壮性（首轮 24h 挂机被外部终止后补的）：
- 每次采样刷新 `--meta`（PID / 启动时间 / 心跳 / 已写样本数）与 `--json` 汇总，
  进程被强杀也能从已有样本复算结论，不再依赖「正常退出」；
- 中断后用同一 `--out` 重启即可**续跑**：序号接着编，历史样本保留并一起参与判定，
  只有本次进程的前 `--warmup` 个样本算预热；
- 判定标准不变：覆盖 ≥ 24h（按 CSV 首末时间戳）、可用率 ≥ 99%、内存无持续增长
  （逻辑见 `utf8_search.verify.metrics.summarize_soak_rows` / `evaluate_soak`）。
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from utf8_search.config import Settings  # noqa: E402
from utf8_search.core.pipeline import SearchPipeline  # noqa: E402
from utf8_search.models import SearchRequest  # noqa: E402
from utf8_search.verify.metrics import (  # noqa: E402
    SOAK_TIMESTAMP_FORMAT,
    format_bytes,
    is_suspect_latency,
    load_soak_rows,
    process_alive,
    read_rss_bytes,
    summarize_soak_rows,
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
    # 下面两列是 4.2 挂机失败后新增的（旧 CSV 没有这两列，解析时按默认值处理）：
    # suspect = 单次采样耗时 > 3×间隔（进程被挂起过），skipped = 该槽位没跑（休眠后不补跑）
    "suspect",
    "skipped",
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
    parser.add_argument("--json", dest="json_out", default="", help="把汇总结果写入该 JSON 文件（每次采样刷新）")
    parser.add_argument(
        "--meta",
        default="",
        help="挂机元数据（PID / 启动时间 / 心跳）路径；默认取 --out 同名的 .meta.json",
    )
    parser.add_argument("--status", action="store_true", help="只打印挂机状态（存活 / 心跳 / 进度 / 当前结论），不采样")
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="只从 --out 的明细 CSV 复算结论（挂机进程已退出 / 被强杀时用），不采样",
    )
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


def _meta_path(args: argparse.Namespace) -> Path:
    """挂机元数据路径：默认与明细 CSV 同名（`data/soak-24h.csv` -> `data/soak-24h.meta.json`）。"""
    return Path(args.meta) if args.meta else Path(args.out).with_suffix(".meta.json")


def _write_json(path: str | Path, payload: dict[str, object]) -> None:
    """原子写 JSON（先写 .tmp 再替换），避免读方拿到半截文件。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def _heartbeat_age(text: str) -> float | None:
    """心跳距现在的秒数；无法解析返回 None。"""
    try:
        stamp = datetime.strptime(text, SOAK_TIMESTAMP_FORMAT)
    except ValueError:
        return None
    return max(0.0, (datetime.now() - stamp).total_seconds())


def _skip_row(*, index: int, timestamp: datetime, elapsed: float, missed: int) -> dict[str, object]:
    """构造一条「没跑」的 SKIP 行。

    进程被挂起（机器休眠 / cgroup 冻结）后落后超过 2 个周期时，补跑没有意义
    ——首轮挂机出现过「47 个样本在 11 秒内补完、其中 39 个命中缓存」的失真数据。
    这类空档必须逐条落进 CSV，否则汇总会把它们静默当成连续覆盖。
    """
    return {
        "index": index,
        "timestamp": timestamp.strftime(SOAK_TIMESTAMP_FORMAT),
        "elapsed_s": round(elapsed, 3),
        "warmup": False,
        "ok": False,
        "latency_ms": "",
        "results": 0,
        "pages_read": 0,
        "cached": False,
        "rss_bytes": None,
        "query": "",
        "error": f"SKIPPED: 落后 {missed} 个采样周期（>2×间隔），按规则不补跑",
        "suspect": False,
        "skipped": True,
    }


def _meta_payload(
    args: argparse.Namespace, *, pid: int, started_at: str, samples: int, finished: bool
) -> dict[str, object]:
    """挂机元数据：每次采样刷新，用来回答「还在跑吗 / 跑到哪了」。"""
    return {
        "pid": pid,
        "started_at": started_at,
        "updated_at": datetime.now().strftime(SOAK_TIMESTAMP_FORMAT),
        "finished": finished,
        "planned_hours": args.duration_hours,
        "interval_s": args.interval,
        "mode": args.mode,
        "csv": str(Path(args.out).resolve()),
        "samples_written": samples,
        "http_url": args.http_url or "",
        "searxng": args.searxng or "",
    }


def _json_payload(
    args: argparse.Namespace, summary: dict[str, object], rows: list[dict[str, object]]
) -> dict[str, object]:
    """汇总 JSON：判定结论 + 汇总指标 + 逐条样本（供报告与事后复核）。"""
    return {
        "generated_at": datetime.now().strftime(SOAK_TIMESTAMP_FORMAT),
        "duration_hours": args.duration_hours,
        "interval": args.interval,
        "mode": args.mode,
        "samples": summary["samples"],
        "succeeded": summary["succeeded"],
        "empty": summary["empty"],
        "errors": summary["errors"],
        "skipped": summary["skipped"],
        "suspect": summary["suspect"],
        "availability": summary["availability"],
        "availability_including_empty": summary["availability_including_empty"],
        "coverage_ratio": summary["coverage_ratio"],
        "window_hours": summary["window_hours"],
        "latency": summary["latency"],
        "rss": summary["rss"],
        "passed": summary["passed"],
        "notes": summary["notes"],
        "rows": rows,
    }


def _print_summary(
    rows: list[dict[str, object]], args: argparse.Namespace
) -> tuple[bool, list[str], dict[str, object]]:
    """打印长稳结论（只统计非预热样本）。

    判定与汇总全部走 `utf8_search.verify.metrics.summarize_soak_rows`，
    因此「在线采样结束时的结论」与「事后 --summarize 复算的结论」必然一致。
    """
    summary = summarize_soak_rows(rows, interval_s=args.interval)
    latency = summary["latency"]  # type: ignore[assignment]
    rss = summary["rss"]  # type: ignore[assignment]

    print("\n== 长稳结果 ==")
    if summary["first_timestamp"]:
        print(
            f"采样区间    : {summary['first_timestamp']} -> {summary['last_timestamp']}"
            f"（覆盖 {float(summary['window_hours']):.2f} h）"
        )
    print(f"采样点数    : {summary['samples']}（预热 {summary['warmup_rows']} 个已剔除）")
    print(f"有结果      : {summary['succeeded']}（可用率分子，判定口径）")
    print(f"空结果 / 异常: {summary['empty']} / {summary['errors']}（分开计数，均不计成功）")
    print(
        f"跳过槽位    : {summary['skipped']} 个"
        f"（实际覆盖 {float(summary['coverage_ratio']):.1%}，SKIP 不计入可用率）"
    )
    print(
        f"可用率      : 有结果 {float(summary['availability']):.2%}（判定）"
        f" / 含空结果 {float(summary['availability_including_empty']):.2%}（参考）"
    )
    if summary["suspect"]:
        print(f"疑似休眠    : {summary['suspect']} 个（已排除出延迟分位，仍计入可用率与 RSS）")
    if latency["count"]:
        print(
            f"延迟        : P50 {latency['p50']:.0f}ms  P95 {latency['p95']:.0f}ms  "
            f"max {latency['max']:.0f}ms  mean {latency['mean']:.0f}ms"
        )
    if rss["samples"]:
        print(
            f"内存        : {format_bytes(rss['min'])}（最低） / "
            f"{format_bytes(rss['last'])}（末次） / {format_bytes(rss['max'])}（峰值）"
        )
    for row in summary["failures"][:10]:  # type: ignore[index]
        print(f"  失败样本 #{row['index']}: {row['error']}")
    for row in summary["empty_rows"][:5]:  # type: ignore[index]
        print(f"  空结果样本 #{row['index']}: {row['query']}（上游 0 条）")
    print("\n结论：" + ("通过" if summary["passed"] else "不通过 / 待定") + " — " + "；".join(summary["notes"]))  # type: ignore[arg-type]
    if not summary["samples"]:
        print("提示：没有任何有效采样，无法判定")
    print(f"明细 CSV: {Path(args.out).resolve()}")
    return bool(summary["passed"]), list(summary["notes"]), summary  # type: ignore[arg-type]


def _print_status(args: argparse.Namespace) -> int:
    """打印挂机状态：进程存活 / 心跳 / 进度 / 当前结论（随时可查，不影响挂机）。"""
    meta_path = _meta_path(args)
    csv_path = Path(args.out)
    print("== 长稳状态 ==")

    meta: dict[str, object] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"meta        : {meta_path.resolve()} 解析失败（{exc}）")
    else:
        print(f"meta        : 未找到 {meta_path.resolve()}")

    interval = float(meta.get("interval_s") or 0) or args.interval
    if meta:
        pid = int(meta.get("pid") or 0)
        heartbeat = str(meta.get("updated_at") or "")
        age = _heartbeat_age(heartbeat)
        print(f"进程 PID    : {pid}（{'存活' if process_alive(pid) else '已退出'}）")
        print(
            f"启动时间    : {meta.get('started_at')}（计划 {meta.get('planned_hours')} h，"
            f"每 {meta.get('interval_s')} s 一次，mode={meta.get('mode')}，finished={meta.get('finished')}）"
        )
        print(f"心跳        : {heartbeat}（{'n/a' if age is None else f'{age:.0f}s 前'}）")
        print(f"已写样本    : {meta.get('samples_written')}")
        if age is not None and age > 3 * interval:
            print(f"⚠ 心跳已超过 3 个采样周期（{3 * interval:.0f}s）：进程可能卡住或已被强杀")

    rows = load_soak_rows(csv_path)
    if not rows:
        print(f"明细        : {csv_path.resolve()} 不存在或无有效样本")
        return 2

    summary = summarize_soak_rows(rows, interval_s=interval)
    last = rows[-1]
    print(f"明细        : {csv_path.resolve()}（{len(rows)} 行）")
    if last.get("skipped"):
        last_state = "SKIP    "
    elif last.get("suspect"):
        last_state = "SUSPECT "
    else:
        last_state = "OK     " if last["ok"] else "FAIL   "
    print(
        f"最近采样    : #{last['index']} {last['timestamp']} {last_state}"
        f"{float(last['latency_ms']):.0f}ms 结果 {last['results']} 读页 {last['pages_read']} "
        f"RSS {format_bytes(last.get('rss_bytes'))}"
    )
    print(
        f"覆盖窗口    : {summary['first_timestamp']} -> {summary['last_timestamp']}"
        f"（{float(summary['window_hours']):.2f} h）"
    )
    print(
        f"累计可用率  : 有结果 {float(summary['availability']):.2%}"
        f"（{summary['succeeded']}/{summary['samples'] - summary['skipped']}）"
        f" / 含空结果 {float(summary['availability_including_empty']):.2%}"
    )
    print(
        f"样本分类    : 有结果 {summary['succeeded']} / 空结果 {summary['empty']}"
        f" / 异常 {summary['errors']} / 跳过 {summary['skipped']} / 疑似休眠 {summary['suspect']}"
    )
    print(
        f"当前结论    : {'通过' if summary['passed'] else '不通过 / 待定'} — "
        + "；".join(summary["notes"])  # type: ignore[arg-type]
    )
    if args.json_out:
        _write_json(args.json_out, _json_payload(args, summary, rows))
    return 0


def _summarize_from_csv(args: argparse.Namespace) -> int:
    """从已有明细 CSV 复算结论（挂机进程已退出 / 被强杀时用）。"""
    print("== 长稳结论复算（--summarize：不启动任何采样） ==")
    rows = load_soak_rows(args.out)
    if not rows:
        print(f"未找到有效样本：{Path(args.out).resolve()}")
        return 2
    passed, _notes, summary = _print_summary(rows, args)
    if args.json_out:
        _write_json(args.json_out, _json_payload(args, summary, rows))
        print(f"汇总 JSON: {args.json_out}")
    return 0 if passed else 1


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

    # 续跑：读回已有样本继续编号（历史样本保留，最终判定会把它们一起算上）
    existing = load_soak_rows(out)
    resume_from = max((int(row["index"]) for row in existing), default=0)
    need_header = not out.exists() or out.stat().st_size == 0

    pid = os.getpid()
    started_at = datetime.now().strftime(SOAK_TIMESTAMP_FORMAT)
    meta_path = _meta_path(args)
    print(f"本次进程 PID: {pid}；meta 写入 {meta_path.resolve()}")
    print(f"计划: 每 {args.interval:.0f}s 查询一次，共 {args.duration_hours:.2f} h，模式 {args.mode}")
    if existing:
        print(f"续跑: 已有 {len(existing)} 个样本，从 #{resume_from + 1} 继续（历史样本仍参与判定）")
    print(f"明细写入: {out.resolve()}\n")
    _write_json(meta_path, _meta_payload(args, pid=pid, started_at=started_at, samples=len(existing), finished=False))

    rows: list[dict[str, object]] = []
    started = time.perf_counter()
    started_wall = datetime.now()
    deadline = started + args.duration_hours * 3600
    finished = False

    def refresh_artifacts() -> None:
        """刷新 meta 心跳与汇总 JSON（含 SKIP 行），进程被强杀也不丢已有结论。"""
        all_rows = existing + rows
        _write_json(
            meta_path,
            _meta_payload(args, pid=pid, started_at=started_at, samples=len(all_rows), finished=False),
        )
        if args.json_out:
            _write_json(
                args.json_out,
                _json_payload(args, summarize_soak_rows(all_rows, interval_s=args.interval), all_rows),
            )

    try:
        with out.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            if need_header:
                writer.writerow(COLUMNS)

            index = resume_from
            proc_sample = 0
            # 本次进程内的采样槽位：第 k 个槽位的计划时刻 = started + k*interval
            slot = 0
            while time.perf_counter() < deadline:
                if args.max_samples and proc_sample >= args.max_samples:
                    break

                # 对齐到时间槽位。落后 1~2 个周期时立即补跑；落后超过 2 个周期说明进程被挂起过
                # （机器休眠 / cgroup 冻结），此时**不补跑**——把错过的槽位逐条记成 SKIP
                # 再快进到当前槽位，避免「47 个样本 11 秒内补完、39 个命中缓存」那种失真。
                lag = time.perf_counter() - (started + slot * args.interval)
                if lag < 0:
                    await asyncio.sleep(-lag)
                elif lag > 2 * args.interval:
                    missed = int(lag // args.interval)
                    for offset in range(missed):
                        index += 1
                        rows.append(
                            _skip_row(
                                index=index,
                                timestamp=started_wall + timedelta(seconds=(slot + offset) * args.interval),
                                elapsed=time.perf_counter() - started,
                                missed=missed,
                            )
                        )
                        writer.writerow([rows[-1].get(column, "") for column in COLUMNS])
                    slot += missed
                    handle.flush()
                    refresh_artifacts()
                    print(
                        f"[SKIP] 落后 {missed} 个采样周期（约 {lag / 60:.1f} 分钟）：按规则不补跑，"
                        f"已记 {missed} 条 SKIP 并快进到当前时间槽位"
                    )

                index += 1
                proc_sample += 1
                result = await probe.run(index)
                latency_ms = float(result["latency_ms"])
                row = {
                    "index": index,
                    "timestamp": datetime.now().strftime(SOAK_TIMESTAMP_FORMAT),
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "warmup": proc_sample <= args.warmup,
                    "rss_bytes": read_rss_bytes(rss_pid) if rss_pid else None,
                    # 单次耗时 > 3×采样间隔 => 进程被挂起过，这条延迟不是服务的真实表现
                    "suspect": is_suspect_latency(latency_ms, args.interval),
                    "skipped": False,
                    **result,
                }
                rows.append(row)
                slot += 1
                writer.writerow([row.get(column, "") for column in COLUMNS])
                # 逐行刷盘：24h 挂机中途被中断也能看到进度
                handle.flush()

                flag = "SUSP" if row["suspect"] else ("OK " if row["ok"] else "FAIL")
                print(
                    f"[{index:>4}] {row['timestamp']} {flag} {float(row['latency_ms']):6.0f}ms "
                    f"结果 {row['results']:>2} 读页 {row['pages_read']:>2} "
                    f"RSS {format_bytes(row['rss_bytes'])} {'' if row['ok'] else row['error']}"
                )

                # 每次采样刷新心跳与汇总：进程被强杀也不丢结论（首轮挂机就是这么丢的）
                refresh_artifacts()
            else:
                finished = True
    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n已中断，输出已有采样汇总")
    finally:
        if pipeline is not None:
            await pipeline.close()
        if client is not None:
            await client.aclose()

    all_rows = existing + rows
    passed, _notes, summary = _print_summary(all_rows, args)
    _write_json(
        meta_path, _meta_payload(args, pid=pid, started_at=started_at, samples=len(all_rows), finished=finished)
    )
    if args.json_out:
        _write_json(args.json_out, _json_payload(args, summary, all_rows))
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
        if args.status:
            return _print_status(args)
        if args.summarize:
            return _summarize_from_csv(args)
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        print("\n已中断")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
