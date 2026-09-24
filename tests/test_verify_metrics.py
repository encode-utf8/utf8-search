"""验收判定逻辑的单元测试（对应验收项 4.4-11）。

这些函数决定了压测 / 长稳 / 相关性抽检的「通过 / 不通过」，
因此必须离线可测，避免验收结论依赖人工读数字。
"""

from __future__ import annotations

import os

import pytest

from utf8_search.verify.metrics import (
    evaluate_engine_health_ab,
    evaluate_load_test,
    evaluate_relevance,
    evaluate_soak,
    format_bytes,
    percentile,
    read_rss_bytes,
    summarize_latencies,
)


# ---------------------------------------------------------------- 分位与汇总
def test_percentile_empty_returns_zero() -> None:
    """空序列返回 0，不应抛异常。"""
    assert percentile([], 95) == 0.0


def test_percentile_p50_is_median() -> None:
    """P50 取中位数（与 scripts/bench.py 口径一致）。"""
    assert percentile([1.0, 2.0, 3.0, 4.0], 50) == 2.5
    assert percentile([5.0], 50) == 5.0


def test_percentile_high_tail_uses_nearest_rank() -> None:
    """P90 / P95 使用最近秩法（ceil），小样本夹取到有效下标而不是退化成最小值。"""
    values = [float(i) for i in range(1, 11)]  # 1..10
    assert percentile(values, 90) == 9.0
    assert percentile(values, 95) == 10.0
    assert percentile([1.0], 95) == 1.0
    assert percentile([1.0, 2.0], 95) == 2.0
    # 30 个样本的 P95 应落在第 29 个（ceil(28.5)=29）
    assert percentile([float(i) for i in range(1, 31)], 95) == 29.0


def test_summarize_latencies() -> None:
    """汇总应包含 count / p50 / p90 / p95 / max / mean。"""
    stats = summarize_latencies([100.0, 200.0, 300.0, 400.0])
    assert stats["count"] == 4
    assert stats["p50"] == 250.0
    assert stats["max"] == 400.0
    assert stats["mean"] == 250.0
    assert summarize_latencies([])["count"] == 0


# ---------------------------------------------------------------- 压测判定
def test_load_test_passes_without_5xx_or_timeout() -> None:
    """无 5xx、无超时即通过。"""
    passed, notes = evaluate_load_test(
        total=50, succeeded=50, server_errors=0, timeouts=0, transport_errors=0
    )
    assert passed is True
    assert "无 5xx、无超时" in notes[0]


def test_load_test_fails_on_5xx() -> None:
    passed, notes = evaluate_load_test(
        total=50, succeeded=48, server_errors=2, timeouts=0, transport_errors=0
    )
    assert passed is False
    assert any("5xx" in note for note in notes)


def test_load_test_fails_on_timeout_and_transport_error() -> None:
    passed, notes = evaluate_load_test(
        total=50, succeeded=45, server_errors=0, timeouts=3, transport_errors=2
    )
    assert passed is False
    assert any("超时" in note for note in notes)
    assert any("传输" in note for note in notes)


def test_load_test_4xx_does_not_fail_but_warns() -> None:
    """4xx（例如 429 限流）不算失败，但必须提示，避免误读为故障。"""
    passed, notes = evaluate_load_test(
        total=50, succeeded=40, server_errors=0, timeouts=0, transport_errors=0, client_errors=10
    )
    assert passed is True
    assert any("4xx" in note for note in notes)


def test_load_test_without_requests_fails() -> None:
    passed, _ = evaluate_load_test(total=0, succeeded=0, server_errors=0, timeouts=0, transport_errors=0)
    assert passed is False


# ---------------------------------------------------------------- 长稳判定
def test_soak_passes_with_high_availability_and_stable_memory() -> None:
    """可用率达标 + 内存平稳 -> 通过。"""
    rss = [100 * 1024 * 1024 + (i % 5) * 1024 * 1024 for i in range(40)]
    passed, notes, details = evaluate_soak(total=100, succeeded=100, rss_series=rss)
    assert passed is True
    assert details["availability"] == 1.0
    assert any("内存平稳" in note for note in notes)


def test_soak_fails_on_low_availability() -> None:
    rss = [100 * 1024 * 1024 for _ in range(40)]
    passed, notes, details = evaluate_soak(total=100, succeeded=95, rss_series=rss)
    assert passed is False
    assert details["availability"] == pytest.approx(0.95)
    assert any("可用率" in note for note in notes)


def test_soak_fails_on_memory_growth() -> None:
    """内存尾部中位数同时超过相对与绝对门槛 -> 判定为持续增长。"""
    rss = [100 * 1024 * 1024 for _ in range(20)] + [300 * 1024 * 1024 for _ in range(20)]
    passed, notes, details = evaluate_soak(total=100, succeeded=100, rss_series=rss)
    assert passed is False
    assert details["rss_growth_bytes"] > 50 * 1024 * 1024
    assert any("内存持续增长" in note for note in notes)


def test_soak_ignores_small_absolute_growth() -> None:
    """相对增长很大但绝对值很小（如 5MB -> 10MB）不应误报为泄漏。"""
    rss = [5 * 1024 * 1024 for _ in range(20)] + [10 * 1024 * 1024 for _ in range(20)]
    passed, _, _ = evaluate_soak(total=100, succeeded=100, rss_series=rss)
    assert passed is True


def test_soak_with_few_rss_samples_skips_memory_verdict() -> None:
    """RSS 采样不足时不做内存判定，但可用率仍要判。"""
    passed, notes, _ = evaluate_soak(total=10, succeeded=10, rss_series=[1.0, 2.0])
    assert passed is True
    assert any("采样不足" in note for note in notes)


def test_soak_without_samples_fails() -> None:
    passed, notes, _ = evaluate_soak(total=0, succeeded=0, rss_series=[])
    assert passed is False
    assert notes


# ---------------------------------------------------------------- 相关性判定
def test_relevance_passes_when_most_queries_are_good() -> None:
    scores = {f"q{i}": [1, 1, 1, 1, 0] for i in range(20)}
    passed, notes, details = evaluate_relevance(scores)
    assert passed is True
    assert details["pass_ratio"] == 1.0
    assert details["avg_relevant"] == 4.0


def test_relevance_fails_when_below_threshold() -> None:
    """只有一半查询达标（50% < 90%）-> 不通过，并列出不达标查询。"""
    scores = {f"q{i}": ([1, 1, 1, 1, 1] if i < 10 else [1, 1, 0, 0, 0]) for i in range(20)}
    passed, notes, details = evaluate_relevance(scores)
    assert passed is False
    assert len(details["failed_queries"]) == 10
    assert any("未达标查询" in note for note in notes)


def test_relevance_empty_scores_fails() -> None:
    passed, notes, _ = evaluate_relevance({})
    assert passed is False
    assert notes


# ---------------------------------------------------------------- 内存采样与格式化
def test_read_rss_bytes_for_current_process() -> None:
    """当前进程的 RSS 应能读到（Windows 走 psapi，Linux 走 /proc）。"""
    value = read_rss_bytes(os.getpid())
    if value is None:
        pytest.skip("当前平台不支持读取 RSS")
    assert value > 1024 * 1024


def test_read_rss_bytes_invalid_pid_returns_none() -> None:
    """非法 PID 返回 None，调用方必须能容忍缺失。"""
    assert read_rss_bytes(0) is None
    assert read_rss_bytes(-1) is None
    assert read_rss_bytes(999_999_999) is None


def test_format_bytes() -> None:
    assert format_bytes(None) == "n/a"
    assert format_bytes(0) == "0B"
    assert format_bytes(1024) == "1.0KB"
    assert format_bytes(1536 * 1024) == "1.5MB"

# ---------------------------------------------------------------- 引擎健康度 A/B 判定
def test_engine_health_ab_passes_when_coverage_and_latency_hold() -> None:
    static = {"count": 16, "results_median": 48.0, "p50": 1000.0, "p95": 1300.0, "failures": 80.0, "empty": 0.0}
    adaptive = {"count": 16, "results_median": 48.0, "p50": 900.0, "p95": 1050.0, "failures": 0.0, "empty": 0.0}
    passed, notes, details = evaluate_engine_health_ab(static=static, adaptive=adaptive)
    assert passed
    assert details["count"] == 16
    assert any("覆盖率不下降" in note for note in notes)


def test_engine_health_ab_fails_on_coverage_drop() -> None:
    """覆盖率下降必须判不通过 —— 这正是用户拒绝的「一味防御性降级」。"""
    static = {"count": 16, "results_median": 48.0, "p50": 1000.0, "p95": 1300.0, "failures": 80.0, "empty": 0.0}
    adaptive = {"count": 16, "results_median": 30.0, "p50": 800.0, "p95": 900.0, "failures": 0.0, "empty": 2.0}
    passed, notes, _ = evaluate_engine_health_ab(static=static, adaptive=adaptive)
    assert not passed
    assert any("覆盖率下降" in note for note in notes)


def test_engine_health_ab_allows_small_coverage_jitter() -> None:
    static = {"count": 16, "results_median": 48.0, "p50": 1000.0, "p95": 1300.0, "failures": 80.0, "empty": 0.0}
    adaptive = {"count": 16, "results_median": 46.0, "p50": 1000.0, "p95": 1200.0, "failures": 80.0, "empty": 0.0}
    passed, _, _ = evaluate_engine_health_ab(static=static, adaptive=adaptive)
    assert passed


def test_engine_health_ab_fails_on_latency_regression() -> None:
    static = {"count": 16, "results_median": 48.0, "p50": 1000.0, "p95": 1300.0, "failures": 80.0, "empty": 0.0}
    adaptive = {"count": 16, "results_median": 48.0, "p50": 1400.0, "p95": 1600.0, "failures": 0.0, "empty": 0.0}
    passed, notes, _ = evaluate_engine_health_ab(static=static, adaptive=adaptive)
    assert not passed
    assert any("延迟劣化" in note for note in notes)


def test_engine_health_ab_fails_when_upstream_errors_increase() -> None:
    static = {"count": 16, "results_median": 48.0, "p50": 1000.0, "p95": 1300.0, "failures": 10.0, "empty": 0.0}
    adaptive = {"count": 16, "results_median": 48.0, "p50": 1000.0, "p95": 1300.0, "failures": 12.0, "empty": 0.0}
    passed, notes, _ = evaluate_engine_health_ab(static=static, adaptive=adaptive)
    assert not passed
    assert any("异常引擎次数增加" in note for note in notes)


def test_engine_health_ab_requires_samples() -> None:
    passed, notes, _ = evaluate_engine_health_ab(
        static={"count": 0}, adaptive={"count": 0, "results_median": 0.0}
    )
    assert not passed
    assert "没有足够的样本" in notes[0]


def test_engine_health_ab_paired_delta_overrides_noisy_p50() -> None:
    """上游延迟双峰时，原始 P50 差异可能纯属抽样噪声；配对差值才是选路的因果影响。"""
    static = {"count": 32, "results_median": 10.0, "p50": 995.0, "p95": 1327.0, "failures": 97.0, "empty": 0.0}
    adaptive = {"count": 32, "results_median": 10.0, "p50": 1199.0, "p95": 1271.0, "failures": 3.0, "empty": 0.0}
    passed, notes, _ = evaluate_engine_health_ab(
        static=static, adaptive=adaptive, paired_delta_median=-22.0
    )
    assert passed
    assert any("配对判定" in note for note in notes)


def test_engine_health_ab_paired_delta_fails_when_really_slower() -> None:
    static = {"count": 32, "results_median": 10.0, "p50": 1000.0, "p95": 1300.0, "failures": 97.0, "empty": 0.0}
    adaptive = {"count": 32, "results_median": 10.0, "p50": 1300.0, "p95": 1500.0, "failures": 3.0, "empty": 0.0}
    passed, notes, _ = evaluate_engine_health_ab(
        static=static, adaptive=adaptive, paired_delta_median=300.0
    )
    assert not passed
    assert any("延迟劣化" in note and "配对" in note for note in notes)
