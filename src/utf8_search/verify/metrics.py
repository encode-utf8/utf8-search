"""验收指标计算：延迟分位、压测 / 长稳 / 相关性判定、内存采样。

把这些「纯计算 + 判定」逻辑抽成独立模块（而不是散落在脚本里），
是为了让验收标准本身可被单元测试覆盖；脚本只负责 IO 与命令行解析。

分位口径：P50 取中位数，其余用最近秩法（nearest-rank，`index = ceil(n*p/100)-1`）。
注意这比 `scripts/bench.py` 的「下取整」口径保守一档（n=50 时相差 1 个序位），
bench.py 的下取整在极小样本下会把 P95 退化成最小值，不宜沿用。
"""

from __future__ import annotations

import os
import statistics
from pathlib import Path

# 内存「持续增长」的判定门槛：相对增长与绝对增长必须**同时**超过才算，
# 避免 RSS 的日常抖动（GC、缓存填充）被误判为泄漏。
MEMORY_GROWTH_RATIO = 0.20
MEMORY_GROWTH_FLOOR_BYTES = 50 * 1024 * 1024

# 长稳可用率门槛（docs/04 第 4.4 节：≥ 99%）
MIN_AVAILABILITY = 0.99

# 相关性抽检门槛（docs/04 第 4.4 节：top5 中 ≥ 4 条相关）
RELEVANCE_PER_QUERY_MIN = 4
RELEVANCE_MIN_PASS_RATIO = 0.9


def percentile(values: list[float], p: float) -> float:
    """分位数（最近秩法）。空序列返回 0，小样本自动夹取到有效下标。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if p == 50:
        return statistics.median(ordered)
    import math

    index = math.ceil(len(ordered) * p / 100) - 1
    index = max(0, min(len(ordered) - 1, index))
    return ordered[index]


def summarize_latencies(values: list[float]) -> dict[str, float]:
    """延迟汇总：P50 / P90 / P95 / 最大 / 均值。"""
    if not values:
        return {"count": 0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "count": len(values),
        "p50": percentile(values, 50),
        "p90": percentile(values, 90),
        "p95": percentile(values, 95),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def evaluate_load_test(
    *,
    total: int,
    succeeded: int,
    server_errors: int,
    timeouts: int,
    transport_errors: int,
    client_errors: int = 0,
) -> tuple[bool, list[str]]:
    """压测判定，返回 (是否通过, 结论列表)。

    通过标准（docs/04 第 4.4 节）：无 5xx、无超时。
    4xx（含 429 限流）不算失败，但会在结论里提示，避免把「限流」误读成「故障」。
    """
    if total <= 0:
        return False, ["没有产生任何请求，无法判定"]
    if succeeded <= 0:
        return False, ["全部请求失败"]

    notes: list[str] = []
    passed = True
    if server_errors:
        passed = False
        notes.append(f"出现 {server_errors} 次 5xx（服务端错误）")
    if timeouts:
        passed = False
        notes.append(f"出现 {timeouts} 次请求超时")
    if transport_errors:
        passed = False
        notes.append(f"出现 {transport_errors} 次连接 / 传输错误")
    if client_errors:
        notes.append(f"出现 {client_errors} 次 4xx（多为限流，不计入失败）")
    if passed:
        notes.insert(0, f"{succeeded}/{total} 请求成功，无 5xx、无超时")
    return passed, notes


def _split_head_tail(values: list[float], fraction: float = 0.25) -> tuple[list[float], list[float]]:
    """把序列切成「头 fraction」与「尾 fraction」，用于比较前后段的中位数。"""
    size = max(1, int(len(values) * fraction))
    return values[:size], values[-size:]


def evaluate_soak(
    *,
    total: int,
    succeeded: int,
    rss_series: list[float],
    min_availability: float = MIN_AVAILABILITY,
    growth_ratio: float = MEMORY_GROWTH_RATIO,
    growth_floor_bytes: float = MEMORY_GROWTH_FLOOR_BYTES,
) -> tuple[bool, list[str], dict[str, float]]:
    """长稳判定，返回 (是否通过, 结论列表, 明细)。

    通过标准（docs/04 第 4.4 节）：
    1. 可用率 = 成功次数 / 总次数 ≥ 99%；
    2. 内存无持续增长：比较有效 RSS 序列「头 25%」与「尾 25%」的中位数，
       相对增长 > 20% 且绝对增长 > 50MB 才判为增长。

    `rss_series` 应由调用方剔除预热样本后传入（单位：字节）。
    """
    details: dict[str, float] = {"availability": 0.0, "rss_samples": float(len(rss_series))}
    if total <= 0:
        return False, ["没有产生任何采样，无法判定"], details

    notes: list[str] = []
    passed = True
    availability = succeeded / total
    details["availability"] = availability
    if availability < min_availability:
        passed = False
        notes.append(f"可用率 {availability:.2%} 低于门槛 {min_availability:.0%}")
    else:
        notes.append(f"可用率 {availability:.2%} 达标（≥ {min_availability:.0%}）")

    if len(rss_series) >= 8:
        head, tail = _split_head_tail(rss_series)
        head_median = statistics.median(head)
        tail_median = statistics.median(tail)
        growth = tail_median - head_median
        ratio = growth / head_median if head_median else 0.0
        details.update(
            rss_head_bytes=head_median,
            rss_tail_bytes=tail_median,
            rss_growth_bytes=growth,
            rss_growth_ratio=ratio,
        )
        if growth > growth_floor_bytes and ratio > growth_ratio:
            passed = False
            notes.append(
                f"内存持续增长：中位数 {head_median / 1048576:.1f}MB -> {tail_median / 1048576:.1f}MB"
                f"（+{ratio:.1%}）"
            )
        else:
            notes.append(
                f"内存平稳：中位数 {head_median / 1048576:.1f}MB -> {tail_median / 1048576:.1f}MB"
                f"（{ratio:+.1%}）"
            )
    else:
        notes.append(f"RSS 采样不足（{len(rss_series)} 个），内存趋势未判定")

    return passed, notes, details


def evaluate_relevance(
    scores: dict[str, list[int]],
    *,
    per_query_min: int = RELEVANCE_PER_QUERY_MIN,
    min_pass_ratio: float = RELEVANCE_MIN_PASS_RATIO,
) -> tuple[bool, list[str], dict[str, object]]:
    """相关性抽检判定，返回 (是否通过, 结论列表, 明细)。

    `scores`：{查询: [top1, top2, ...]}，元素为 0/1（或 0-2 分），≥ 1 视为相关。
    通过标准：top5 中相关数 ≥ 4 的查询占比 ≥ 90%。
    """
    if not scores:
        return False, ["没有打分数据，无法判定"], {"queries": 0}

    relevant_counts = {query: sum(1 for value in values if value >= 1) for query, values in scores.items()}
    passed_queries = [query for query, count in relevant_counts.items() if count >= per_query_min]
    failed_queries = [query for query in scores if query not in passed_queries]
    ratio = len(passed_queries) / len(scores)

    details: dict[str, object] = {
        "queries": len(scores),
        "passed_queries": len(passed_queries),
        "pass_ratio": ratio,
        "avg_relevant": statistics.fmean(relevant_counts.values()),
        "failed_queries": failed_queries,
    }
    notes = [
        f"{len(passed_queries)}/{len(scores)} 条查询的 top5 相关数 ≥ {per_query_min}（{ratio:.0%}）",
        f"平均相关条数 {details['avg_relevant']:.2f}",
    ]
    passed = ratio >= min_pass_ratio
    if not passed:
        notes.append(f"未达 {min_pass_ratio:.0%} 门槛，需复核引擎质量或查询用词")
    if failed_queries:
        notes.append("未达标查询：" + "、".join(failed_queries))
    return passed, notes, details


NEWS_FRESH_RATIO_MIN = 0.8


def evaluate_timeliness(
    *, total: int, fresh: int, min_ratio: float = NEWS_FRESH_RATIO_MIN
) -> tuple[bool, list[str], dict[str, float]]:
    """时效性验收判定（M5-5.2），返回 (是否通过, 结论列表, 明细)。

    通过标准（docs/04 第 5.2 节）：`topic=news` + `time_range=day` 返回的结果中，
    带 7 日内发布日期的比例 ≥ 80%。
    """
    if total <= 0:
        return False, ["没有返回任何结果，无法判定"], {"ratio": 0.0, "total": 0.0, "fresh": 0.0}
    ratio = fresh / total
    details = {"ratio": ratio, "total": float(total), "fresh": float(fresh)}
    passed = ratio >= min_ratio
    notes = [f"{fresh}/{total} 条结果带 7 日内日期（{ratio:.0%}，门槛 {min_ratio:.0%}）"]
    if not passed:
        notes.append("时效性未达标，需检查新闻引擎可用性，或调大日期回补预算 / 页数")
    return passed, notes, details


# 引擎健康度自适应 A/B 判定门槛（M5-5.1 验收 5.1-13）。
# 用户明确要求「稳健的运行效果」而不是一味降级，因此覆盖率是硬指标：
# 允许抽样抖动带来的微小差异，但不允许实质下降。
ENGINE_HEALTH_COVERAGE_TOLERANCE = 0.05
ENGINE_HEALTH_LATENCY_TOLERANCE = 0.10


def evaluate_engine_health_ab(
    *,
    static: dict[str, float],
    adaptive: dict[str, float],
    paired_delta_median: float | None = None,
    coverage_tolerance: float = ENGINE_HEALTH_COVERAGE_TOLERANCE,
    latency_tolerance: float = ENGINE_HEALTH_LATENCY_TOLERANCE,
) -> tuple[bool, list[str], dict[str, object]]:
    """引擎健康度自适应 vs 静态引擎名单的 A/B 判定（M5-5.1），返回 (是否通过, 结论, 明细)。

    通过标准（三条同时满足）：
    1. 结果数中位数不下降（允许 coverage_tolerance 的抽样抖动）——覆盖率是硬指标；
    2. 端到端延迟不劣化；
    3. 上游「不可用引擎」次数不增加（自适应应减少对已挂引擎的无谓请求）。

    延迟为什么用**配对差值**判定：上游端到端延迟是双峰的（实测 ~0.9s 与 ~1.25s 两簇，
    差异来自引擎返回时机，与选路无关），小样本下直接比 P50 等于抛硬币
    （2026-09-24 实测：n=16 时 P50 差 20%，而配对差值中位仅 -22ms、自适应更快的比例 50%）。
    因此基准逐条交替两种模式、按同一 (查询, 轮次) 配对求差；`paired_delta_median`
    就是「自适应 - 静态」的配对差值中位数。未提供时退回直接比较 P50。

    `static` / `adaptive` 为 `scripts/bench_engines.py: summarize()` 的输出：
    `{count, results_median, p50, p95, mean, failures, empty}`。
    """
    if static.get("count", 0) <= 0 or adaptive.get("count", 0) <= 0:
        return False, ["没有足够的样本，无法判定"], {"static": dict(static), "adaptive": dict(adaptive)}

    notes: list[str] = []
    passed = True

    static_median = float(static.get("results_median", 0.0))
    adaptive_median = float(adaptive.get("results_median", 0.0))
    coverage_floor = static_median * (1.0 - coverage_tolerance)
    if adaptive_median < coverage_floor:
        passed = False
        notes.append(
            f"覆盖率下降：结果数中位数 {static_median:.1f} -> {adaptive_median:.1f}（下限 {coverage_floor:.1f}）"
        )
    else:
        notes.append(f"覆盖率不下降：结果数中位数 {static_median:.1f} -> {adaptive_median:.1f}")

    static_p50 = float(static.get("p50", 0.0))
    adaptive_p50 = float(adaptive.get("p50", 0.0))
    latency_ceiling = static_p50 * (1.0 + latency_tolerance)
    if paired_delta_median is not None:
        # 配对判定：本服务的选路对延迟的因果影响。
        # 注意参照量是「差值上限」= 静态 P50 的 latency_tolerance 倍，不是延迟上限本身。
        delta_ceiling = static_p50 * latency_tolerance
        if paired_delta_median > delta_ceiling:
            passed = False
            notes.append(
                f"延迟劣化：配对差值中位 {paired_delta_median:+.0f}ms，超过静态 P50 的 "
                f"{latency_tolerance:.0%}（上限 {delta_ceiling:.0f}ms）"
            )
        else:
            notes.append(
                f"延迟不劣化（配对判定）：配对差值中位 {paired_delta_median:+.0f}ms"
                f"（上限 {delta_ceiling:.0f}ms）；原始 P50 {static_p50:.0f}ms -> {adaptive_p50:.0f}ms 仅作参考"
            )
    elif adaptive_p50 > latency_ceiling:
        passed = False
        notes.append(f"延迟劣化：P50 {static_p50:.0f}ms -> {adaptive_p50:.0f}ms（上限 {latency_ceiling:.0f}ms）")
    else:
        notes.append(f"延迟不劣化：P50 {static_p50:.0f}ms -> {adaptive_p50:.0f}ms")

    static_failures = float(static.get("failures", 0.0))
    adaptive_failures = float(adaptive.get("failures", 0.0))
    if adaptive_failures > static_failures:
        passed = False
        notes.append(f"上游异常引擎次数增加：{static_failures:.0f} -> {adaptive_failures:.0f}")
    else:
        notes.append(f"上游异常引擎次数不增加：{static_failures:.0f} -> {adaptive_failures:.0f}")

    details: dict[str, object] = {
        "count": adaptive.get("count", 0),
        "static": dict(static),
        "adaptive": dict(adaptive),
    }
    return passed, notes, details


def read_rss_bytes(pid: int) -> int | None:
    """读取进程常驻内存 RSS（字节），失败返回 None。

    - Linux：/proc/<pid>/status 的 VmRSS
    - Windows：psapi.GetProcessMemoryInfo 的 WorkingSetSize（等价任务管理器「内存」）
    采用标准库实现，避免为一个指标引入 psutil 依赖。
    """
    if pid <= 0:
        return None

    status = Path(f"/proc/{pid}/status")
    if status.exists():
        try:
            for line in status.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
        return None

    if os.name == "nt":
        return _read_rss_windows(pid)
    return None


def _read_rss_windows(pid: int) -> int | None:
    """Windows 下的 RSS 读取（ctypes 直调 psapi）。"""
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    process_query_limited_information = 0x1000
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
    except OSError:
        return None

    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return None
    try:
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return None
        return int(counters.WorkingSetSize)
    except OSError:
        return None
    finally:
        kernel32.CloseHandle(handle)


def format_bytes(size: float | None) -> str:
    """人类可读的字节数，用于报告输出。"""
    if size is None:
        return "n/a"
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size) < 1024 or unit == "GB":
            return f"{size:.1f}{unit}" if unit != "B" else f"{size:.0f}B"
        size /= 1024
    return f"{size:.1f}GB"