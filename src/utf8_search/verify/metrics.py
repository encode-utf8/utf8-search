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
from datetime import datetime
from pathlib import Path

# 内存「持续增长」的判定门槛：相对增长与绝对增长必须**同时**超过才算，
# 避免 RSS 的日常抖动（GC、缓存填充）被误判为泄漏。
MEMORY_GROWTH_RATIO = 0.20
MEMORY_GROWTH_FLOOR_BYTES = 50 * 1024 * 1024

# 长稳可用率门槛（docs/04 第 4.4 节：≥ 99%）
MIN_AVAILABILITY = 0.99

# 长稳「疑似休眠」判定：单次采样耗时超过 interval 的这个倍数，说明进程被挂起过
# （机器休眠 / cgroup 冻结 / 断网重试），这个耗时不是服务的真实延迟，必须排除出分位统计。
SOAK_SUSPECT_LATENCY_FACTOR = 3.0

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


def is_suspect_latency(
    latency_ms: float, interval_s: float | None, factor: float = SOAK_SUSPECT_LATENCY_FACTOR
) -> bool:
    """单次采样耗时是否异常（疑似进程休眠 / 被挂起）。

    本机 24h 首轮出现过 `latency_ms=6280716`（≈104 分钟，远超 300s 采样间隔）的假样本：
    请求本身早就返回了，是进程被系统挂起后 `perf_counter` 才继续走。这种样本算进 P50/P95
    会把分位彻底带偏，因此标记为 suspect 并排除出分位；它仍是「有结果」的采样，
    所以照常计入可用率与 RSS 序列。

    `interval_s` 缺失或非法时不做判定（返回 False），以免旧数据被误标。
    """
    if not interval_s or interval_s <= 0:
        return False
    return float(latency_ms) > factor * float(interval_s) * 1000.0


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
    empty: int = 0,
    errors: int | None = None,
    min_availability: float = MIN_AVAILABILITY,
    growth_ratio: float = MEMORY_GROWTH_RATIO,
    growth_floor_bytes: float = MEMORY_GROWTH_FLOOR_BYTES,
) -> tuple[bool, list[str], dict[str, float]]:
    """长稳判定，返回 (是否通过, 结论列表, 明细)。

    通过标准（docs/04 第 4.4 节）：
    1. **有结果可用率** = 有结果的样本数 / 总样本数 ≥ 99%；
    2. 内存无持续增长：比较有效 RSS 序列「头 25%」与「尾 25%」的中位数，
       相对增长 > 20% 且绝对增长 > 50MB 才判为增长。

    口径（4.2 挂机首轮暴露的「假绿」问题）：采样「没抛异常」不等于「搜到了东西」。
    本机曾连续 115 个样本返回 0 结果（约 10.7h 全空），旧口径仍算出 100% 可用率。
    因此这里把三类样本分开计数、分别展示：

    - `succeeded`：请求成功且**有结果** —— 唯一计入可用率分子的样本；
    - `empty`：请求成功但**0 结果**（上游全挂 / 风控时的典型表现）；
    - `errors`：请求抛异常（超时、连接失败、5xx 等）。

    结论里同时给出「含空结果可用率」= (succeeded + empty) / total 作为参考，
    **判定只用「有结果可用率」**。

    `rss_series` 应由调用方剔除预热样本后传入（单位：字节）。
    """
    if errors is None:
        errors = max(0, total - succeeded - empty)

    details: dict[str, float] = {
        "availability": 0.0,
        "availability_including_empty": 0.0,
        "empty": float(empty),
        "errors": float(errors),
        "rss_samples": float(len(rss_series)),
    }
    if total <= 0:
        return False, ["没有产生任何采样，无法判定"], details

    notes: list[str] = []
    passed = True
    availability = succeeded / total
    availability_including_empty = (succeeded + empty) / total
    details["availability"] = availability
    details["availability_including_empty"] = availability_including_empty
    if availability < min_availability:
        passed = False
        notes.append(f"有结果可用率 {availability:.2%} 低于门槛 {min_availability:.0%}")
    else:
        notes.append(f"有结果可用率 {availability:.2%} 达标（≥ {min_availability:.0%}）")
    notes.append(
        f"含空结果可用率 {availability_including_empty:.2%}（仅作参考：空结果不计成功）"
    )
    notes.append(f"失败明细：空结果 {empty} 个、异常 {errors} 个")

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


# 结果「卫生度」判定门槛（M5-5.3）。质量过滤的目标是**减少可疑结果**，
# 因此容差给得很小：可疑项不允许变多，查询词覆盖率不允许实质下降。
HYGIENE_COVERAGE_TOLERANCE = 0.05


def summarize_result_hygiene(
    items: list[dict[str, object]],
    query: str,
    *,
    max_per_host: int = 2,
    empty_content_chars: int = 40,
) -> dict[str, float]:
    """统计一轮结果的「卫生度」指标（M5-5.3，客观、可自动化）。

    `items` 每项至少包含 `title` / `url` / `content` 三个键。
    返回的指标直接对应 2-9 抽检暴露的几类问题：
    同站重复、聚合页（首页/栏目页）、非中文/非英文脚本、查询词覆盖度、空内容。
    """
    from ..models import SearchResult
    from ..rank.diversity import (
        has_script_mismatch,
        is_aggregator_page,
        query_coverage,
        registrable_domain,
    )
    from ..rank.fusion import tokenize

    results = [
        SearchResult(
            title=str(item.get("title") or ""),
            url=str(item.get("url") or ""),
            content=str(item.get("content") or ""),
        )
        for item in items
    ]
    total = len(results)
    if total == 0:
        return {
            "total": 0.0, "distinct_hosts": 0.0, "same_host_excess": 0.0,
            "aggregator": 0.0, "script_mismatch": 0.0, "empty_content": 0.0,
            "coverage_mean": 0.0, "coverage_min": 0.0, "low_coverage": 0.0,
        }

    per_host: dict[str, int] = {}
    for result in results:
        host = registrable_domain(result.url)
        if host:
            per_host[host] = per_host.get(host, 0) + 1
    same_host_excess = sum(max(0, count - max_per_host) for count in per_host.values())

    coverages = [query_coverage(query, result) for result in results]
    wanted = set(tokenize(query or ""))

    return {
        "total": float(total),
        "distinct_hosts": float(len(per_host)),
        "same_host_excess": float(same_host_excess),
        "aggregator": float(sum(1 for r in results if is_aggregator_page(r))),
        "script_mismatch": float(
            sum(1 for r in results if has_script_mismatch(query, r.title))
        ),
        "empty_content": float(
            sum(1 for r in results if len((r.content or "").strip()) < empty_content_chars)
        ),
        "coverage_mean": statistics.fmean(coverages),
        "coverage_min": min(coverages),
        "low_coverage": float(sum(1 for c in coverages if c < 0.34)),
        "_has_query_tokens": 1.0 if wanted else 0.0,
    }


def evaluate_hygiene_delta(
    *, before: dict[str, float], after: dict[str, float]
) -> tuple[bool, list[str], dict[str, object]]:
    """对比改动前后的卫生度（M5-5.3），返回 (是否通过, 结论, 明细)。

    通过标准（三项都要满足）：
    1. 同站冗余不增加；
    2. 聚合页 / 非中文脚本结果不增加；
    3. 查询词覆盖率不实质下降（容差 `HYGIENE_COVERAGE_TOLERANCE`）。
    """
    if before.get("total", 0) <= 0 or after.get("total", 0) <= 0:
        return False, ["没有结果样本，无法比较卫生度"], {"before": dict(before), "after": dict(after)}

    notes: list[str] = []
    passed = True
    for key, label in (("same_host_excess", "同站冗余"), ("aggregator", "聚合页"), ("script_mismatch", "非中英文脚本")):
        old, new = float(before.get(key, 0.0)), float(after.get(key, 0.0))
        if new > old:
            passed = False
            notes.append(f"{label}增加：{old:.0f} -> {new:.0f}")
        else:
            notes.append(f"{label}不增加：{old:.0f} -> {new:.0f}")

    old_cov, new_cov = float(before.get("coverage_mean", 0.0)), float(after.get("coverage_mean", 0.0))
    if new_cov < old_cov - HYGIENE_COVERAGE_TOLERANCE:
        passed = False
        notes.append(f"查询词覆盖率下降：{old_cov:.3f} -> {new_cov:.3f}")
    else:
        notes.append(f"查询词覆盖率不下降：{old_cov:.3f} -> {new_cov:.3f}")

    return passed, notes, {"before": dict(before), "after": dict(after)}


SOAK_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _as_bool(value: object) -> bool:
    """把 CSV 里的布尔列解析成 bool（容忍 True/true/1/yes）。"""
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def _as_float(value: object) -> float | None:
    """把 CSV 单元格解析成 float；空值或脏值返回 None。"""
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_timestamp(value: object) -> datetime | None:
    """解析长稳样本的时间戳（格式与 scripts/soak.py 写入的一致）。"""
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, SOAK_TIMESTAMP_FORMAT)
    except ValueError:
        return None


def load_soak_rows(path: str | Path) -> list[dict[str, object]]:
    """读取长稳明细 CSV 并做类型归一。

    刻意做成容错的：挂机进程被强杀时最后一行可能是半截的，直接 `csv.DictReader`
    会给出一堆字符串与空值；这里丢弃「没有时间戳或没有延迟」的行，保证**用已有样本
    也能复算结论**（这正是 24h 首轮挂机失败后暴露出来的需求）。

    兼容性：新增的 `suspect` / `skipped` 两列按「有则解析、无则给默认值」处理，
    因此**旧格式（12 列）的 CSV 仍然能解析**，只是 suspect 记为未知（None），
    汇总时若提供 `interval_s` 会按采样间隔回算。

    `skipped=True` 的行表示「该采样槽位没跑」（进程休眠后落后超过 2 个周期），
    这类行没有延迟但必须保留，否则汇总会把它静默当成连续覆盖。
    """
    import csv

    file = Path(path)
    rows: list[dict[str, object]] = []
    if not file.exists():
        return rows

    with file.open(encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            timestamp = (raw.get("timestamp") or "").strip()
            latency = _as_float(raw.get("latency_ms"))
            skipped = _as_bool(raw.get("skipped"))
            if not timestamp or (latency is None and not skipped):
                continue
            raw_suspect = raw.get("suspect")
            rows.append(
                {
                    "index": int(_as_float(raw.get("index")) or 0),
                    "timestamp": timestamp,
                    "elapsed_s": _as_float(raw.get("elapsed_s")) or 0.0,
                    "warmup": _as_bool(raw.get("warmup")),
                    "ok": _as_bool(raw.get("ok")),
                    "latency_ms": latency if latency is not None else 0.0,
                    "results": int(_as_float(raw.get("results")) or 0),
                    "pages_read": int(_as_float(raw.get("pages_read")) or 0),
                    "cached": _as_bool(raw.get("cached")),
                    "rss_bytes": _as_float(raw.get("rss_bytes")),
                    "query": str(raw.get("query") or ""),
                    "error": str(raw.get("error") or ""),
                    # 旧格式没有这两列：suspect 记为 None（未知），skipped 记为 False
                    "suspect": None if raw_suspect is None else _as_bool(raw_suspect),
                    "skipped": skipped,
                }
            )
    return rows


def summarize_soak_rows(
    rows: list[dict[str, object]],
    *,
    interval_s: float | None = None,
    min_availability: float = MIN_AVAILABILITY,
    growth_ratio: float = MEMORY_GROWTH_RATIO,
    growth_floor_bytes: float = MEMORY_GROWTH_FLOOR_BYTES,
) -> dict[str, object]:
    """汇总长稳样本并给出判定（在线采样与事后复算共用这一条路径）。

    判定沿用 `evaluate_soak`（**有结果**可用率 ≥ 99% + 内存头尾中位数无持续增长），
    另外给出两类额外信息：

    - **覆盖窗口**：24h 长稳允许中断后续跑，因此「时长」按 CSV 首末时间戳计算，
      而不是单个进程的 `elapsed_s`（后者重启后会归零）；
    - **样本归类**：有结果 / 空结果 / 异常 / 跳过 / 疑似休眠（suspect）分别计数。
      「跳过」是进程休眠后**没有跑**的采样槽位（见 `scripts/soak.py` 的 SKIP 逻辑）：
      它们不计入可用率分母，但必须在结论里可见，否则会被静默当成连续覆盖。

    `interval_s` 用于在旧格式 CSV（没有 `suspect` 列）上回算疑似休眠样本；不传则
    只认 CSV 里写明的 suspects。
    """
    measured = [row for row in rows if not row.get("warmup")]
    skipped = [row for row in measured if row.get("skipped")]
    sampled = [row for row in measured if not row.get("skipped")]  # 真正打到服务的样本
    succeeded = [row for row in sampled if row.get("ok") and int(row.get("results") or 0) > 0]
    empty = [row for row in sampled if row.get("ok") and int(row.get("results") or 0) == 0]
    errors = [row for row in sampled if not row.get("ok")]
    # RSS 序列沿用「所有实际采样点」，suspect 样本照常保留（内存不会因为进程被挂起而失真）
    rss_series = [float(row["rss_bytes"]) for row in measured if row.get("rss_bytes")]
    suspects = [row for row in succeeded if _row_is_suspect(row, interval_s)]
    # 延迟分位只用「有结果且非疑似休眠」的样本：休眠期间那条 104 分钟的假样本必须排除
    latencies = [
        float(row["latency_ms"])
        for row in succeeded
        if row.get("latency_ms") is not None and not _row_is_suspect(row, interval_s)
    ]

    passed, notes, details = evaluate_soak(
        total=len(sampled),
        succeeded=len(succeeded),
        empty=len(empty),
        errors=len(errors),
        rss_series=rss_series,
        min_availability=min_availability,
        growth_ratio=growth_ratio,
        growth_floor_bytes=growth_floor_bytes,
    )

    coverage_ratio = (len(sampled) / len(measured)) if measured else 0.0
    if skipped:
        notes.append(
            f"跳过 {len(skipped)} 个采样槽位（进程休眠后落后 > 2 个周期，不补跑）："
            f"实际覆盖 {len(sampled)}/{len(measured)}（{coverage_ratio:.1%}），这些槽位不计入可用率"
        )
    if suspects:
        notes.append(
            f"疑似休眠样本 {len(suspects)} 个（单次耗时 > {SOAK_SUSPECT_LATENCY_FACTOR:.0f}×采样间隔）："
            "已排除出延迟分位，仍计入可用率与 RSS"
        )

    first = _parse_timestamp(measured[0]["timestamp"]) if measured else None
    last = _parse_timestamp(measured[-1]["timestamp"]) if measured else None
    window_seconds = max(0.0, (last - first).total_seconds()) if (first and last) else 0.0

    return {
        "samples": len(measured),
        "warmup_rows": len(rows) - len(measured),
        "succeeded": len(succeeded),
        "empty": len(empty),
        "errors": len(errors),
        "skipped": len(skipped),
        "suspect": len(suspects),
        "failed": len(errors),
        "availability": float(details.get("availability", 0.0)),
        "availability_including_empty": float(details.get("availability_including_empty", 0.0)),
        "coverage_ratio": coverage_ratio,
        "latency": summarize_latencies(latencies),
        "rss": {
            "samples": len(rss_series),
            "min": min(rss_series) if rss_series else None,
            "last": rss_series[-1] if rss_series else None,
            "max": max(rss_series) if rss_series else None,
            "head_median": details.get("rss_head_bytes"),
            "tail_median": details.get("rss_tail_bytes"),
            "growth_ratio": details.get("rss_growth_ratio"),
        },
        "window_seconds": window_seconds,
        "window_hours": window_seconds / 3600.0,
        "first_timestamp": measured[0]["timestamp"] if measured else None,
        "last_timestamp": measured[-1]["timestamp"] if measured else None,
        "passed": passed,
        "notes": notes,
        "failures": errors,
        "empty_rows": empty,
        "skipped_rows": skipped,
    }


def _row_is_suspect(row: dict[str, object], interval_s: float | None) -> bool:
    """样本是否疑似进程休眠。

    优先用 CSV 里写明的 `suspect` 列（采样当时算的，最准）；旧格式没有该列时，
    用 `interval_s` 按 `latency_ms` 回算。
    """
    flag = row.get("suspect")
    if flag is not None:
        return bool(flag)
    latency = row.get("latency_ms")
    if latency is None:
        return False
    return is_suspect_latency(float(latency), interval_s)


def process_alive(pid: int) -> bool:
    """进程是否仍在运行（长稳挂机的存活检查）。

    用标准库实现，不引入 psutil：
    - Windows：`OpenProcess` + `GetExitCodeProcess == STILL_ACTIVE(259)`；
    - Linux：`/proc/<pid>` 是否存在；
    - 其他：`os.kill(pid, 0)`。

    注意 PID 会被系统复用，因此判定存活只作为「粗判」；脚本里同时要求心跳新鲜，
    两者一起看才能确认挂机真的在跑。
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        return _process_alive_windows(pid)
    if Path(f"/proc/{pid}").exists():
        return True
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _process_alive_windows(pid: int) -> bool:
    """Windows 下的存活检测（ctypes 直调 kernel32）。"""
    import ctypes
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    still_active = 259
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except OSError:
        return False

    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


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
