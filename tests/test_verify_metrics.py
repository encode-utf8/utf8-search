"""验收判定逻辑的单元测试（对应验收项 4.4-11）。

这些函数决定了压测 / 长稳 / 相关性抽检的「通过 / 不通过」，
因此必须离线可测，避免验收结论依赖人工读数字。
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timedelta

import pytest

from utf8_search.verify.metrics import (
    evaluate_engine_health_ab,
    evaluate_load_test,
    evaluate_relevance,
    evaluate_soak,
    format_bytes,
    is_suspect_latency,
    load_soak_rows,
    percentile,
    process_alive,
    read_rss_bytes,
    summarize_latencies,
    summarize_soak_rows,
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


# ---------------------------------------------------------------- 长稳明细 CSV 解析与复算
SOAK_HEADER = "index,timestamp,elapsed_s,warmup,ok,latency_ms,results,pages_read,cached,rss_bytes,query,error"


def _synthetic_rows(
    *, count: int = 12, warmup: int = 2, failures: int = 0, rss_growth: bool = False
) -> list[dict[str, object]]:
    """构造长稳样本：默认 12 个采样、其中 2 个预热、全部成功、内存平稳。"""
    base = datetime(2026, 9, 24, 0, 0, 0)
    rows: list[dict[str, object]] = []
    for index in range(1, count + 1):
        ok = index <= count - failures
        rows.append(
            {
                "index": index,
                "timestamp": (base + timedelta(minutes=5 * (index - 1))).strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_s": 300.0 * (index - 1),
                "warmup": index <= warmup,
                "ok": ok,
                "latency_ms": 1200.0,
                "results": 5 if ok else 0,
                "pages_read": 0,
                "cached": False,
                "rss_bytes": float((100 + (10 * index if rss_growth else index)) * 1024 * 1024),
                "query": "q",
                "error": "" if ok else "TimeoutError: 上游超时",
            }
        )
    return rows


def test_load_soak_rows_parses_types_and_skips_broken_lines(tmp_path) -> None:
    """CSV 解析：类型归一，并丢弃「缺时间戳 / 缺延迟」的坏行（挂机被强杀时会出现）。"""
    csv_path = tmp_path / "soak.csv"
    csv_path.write_text(
        "\n".join(
            [
                SOAK_HEADER,
                "1,2026-09-24 22:00:00,0.1,True,True,1200.5,5,0,False,104857600,q1,",
                "2,2026-09-24 22:05:00,300.2,False,false,60.0,0,0,false,105906176,q2,TimeoutError: 超时",
                "3,2026-09-24 22:10:00,600.3,False,True,,0,0,False,,q3,",
                ",,,,,,,,,,,",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = load_soak_rows(csv_path)

    assert len(rows) == 2
    assert rows[0]["ok"] is True and rows[0]["warmup"] is True
    assert rows[0]["latency_ms"] == pytest.approx(1200.5)
    assert rows[0]["rss_bytes"] == pytest.approx(104857600.0)
    assert rows[1]["ok"] is False and rows[1]["warmup"] is False
    assert str(rows[1]["error"]).startswith("TimeoutError")


def test_load_soak_rows_missing_file_returns_empty(tmp_path) -> None:
    """文件不存在时返回空列表（首次挂机、路径写错都不应抛异常）。"""
    assert load_soak_rows(tmp_path / "nope.csv") == []


def test_summarize_soak_rows_passes_and_reports_window() -> None:
    """样本充足且内存平稳 -> 通过，并给出覆盖窗口（24h 长稳按首末时间戳算）。"""
    summary = summarize_soak_rows(_synthetic_rows())

    assert summary["passed"] is True
    assert summary["samples"] == 10
    assert summary["warmup_rows"] == 2
    assert summary["availability"] == 1.0
    assert summary["failed"] == 0
    # 10 个计入统计的样本，间隔 5 分钟 -> 覆盖 45 分钟
    assert summary["window_hours"] == pytest.approx(45 / 60)
    assert summary["first_timestamp"] == "2026-09-24 00:10:00"
    assert summary["last_timestamp"] == "2026-09-24 00:55:00"
    assert summary["latency"]["count"] == 10


def test_summarize_soak_rows_coverage_window_includes_warmup() -> None:
    """覆盖窗口按 CSV 全部行（含预热）算，计入统计的窗口另给；原字段语义不变。"""
    summary = summarize_soak_rows(_synthetic_rows())  # 12 行，其中 2 个预热

    # 全部行 00:00 -> 00:55 = 55 分钟（覆盖 ≥ 24h 的口径看这个）
    assert summary["coverage_window_hours"] == pytest.approx(55 / 60)
    assert summary["coverage_first_timestamp"] == "2026-09-24 00:00:00"
    assert summary["coverage_last_timestamp"] == "2026-09-24 00:55:00"
    # 计入统计行 00:10 -> 00:55 = 45 分钟（原字段 window_* 语义保持）
    assert summary["window_hours"] == pytest.approx(45 / 60)
    assert summary["coverage_window_hours"] > summary["window_hours"]


def test_summarize_soak_rows_coverage_window_tolerates_bad_timestamps() -> None:
    """坏时间戳不参与覆盖窗口首末取值（与计入统计窗口同样容错，不崩）。"""
    rows = _synthetic_rows(count=10, warmup=0)
    rows[0]["timestamp"] = "not-a-date"

    summary = summarize_soak_rows(rows)

    assert summary["coverage_first_timestamp"] == "2026-09-24 00:05:00"
    assert summary["coverage_last_timestamp"] == "2026-09-24 00:45:00"
    assert summary["coverage_window_hours"] == pytest.approx(40 / 60)


def test_summarize_soak_rows_fails_on_low_availability() -> None:
    """失败样本拉低可用率 -> 不通过，并保留失败明细供定位。"""
    summary = summarize_soak_rows(_synthetic_rows(failures=2))

    assert summary["passed"] is False
    assert summary["failed"] == 2
    assert summary["availability"] == pytest.approx(0.8)
    assert len(summary["failures"]) == 2
    assert any("可用率" in note for note in summary["notes"])


def test_summarize_soak_rows_fails_on_memory_growth() -> None:
    """内存尾部中位数持续升高 -> 不通过。"""
    summary = summarize_soak_rows(_synthetic_rows(rss_growth=True))
    assert summary["passed"] is False
    assert any("内存持续增长" in note for note in summary["notes"])


def test_summarize_soak_rows_tolerates_bad_timestamps() -> None:
    """时间戳解析不了时窗口记 0，但统计与判定照常进行（不能因此崩掉）。"""
    rows = _synthetic_rows(count=10, warmup=0)
    rows[0]["timestamp"] = "not-a-date"
    rows[-1]["timestamp"] = ""

    summary = summarize_soak_rows(rows)

    assert summary["samples"] == 10
    assert summary["window_hours"] == 0.0
    assert summary["passed"] is True


def test_summarize_soak_rows_without_samples_fails() -> None:
    summary = summarize_soak_rows([])
    assert summary["passed"] is False
    assert summary["samples"] == 0
    assert summary["notes"]


# ------------------------------------------------ 长稳口径修正（4.2 挂机首轮四缺陷）
def _soak_row(**overrides: object) -> dict[str, object]:
    """构造一条长稳样本（默认：有结果、延迟正常、非 suspect、非 skip）。"""
    row: dict[str, object] = {
        "index": 1,
        "timestamp": "2026-09-25 00:00:00",
        "elapsed_s": 0.0,
        "warmup": False,
        "ok": True,
        "latency_ms": 1000.0,
        "results": 5,
        "pages_read": 0,
        "cached": False,
        "rss_bytes": 100 * 1024 * 1024.0,
        "query": "q",
        "error": "",
        "suspect": False,
        "skipped": False,
    }
    row.update(overrides)
    return row


def test_is_suspect_latency_thresholds() -> None:
    """单次耗时 > 3×间隔 才算疑似休眠；间隔缺失/非法时不做判定。"""
    assert is_suspect_latency(20_000.0, 300) is False  # 20s < 900s
    assert is_suspect_latency(1_000_000.0, 300) is True  # 1000s > 900s
    assert is_suspect_latency(6_280_716.0, 300) is True  # 本机那条 ≈104 分钟的假样本
    assert is_suspect_latency(6_280_716.0, None) is False
    assert is_suspect_latency(6_280_716.0, 0) is False


def test_soak_empty_results_do_not_count_as_success() -> None:
    """B1 假绿：连续 100 个 0 结果样本不能算 100% 可用（旧口径就是这么错的）。"""
    rows = [_soak_row(index=i, ok=True, results=0) for i in range(1, 101)]
    summary = summarize_soak_rows(rows)

    assert summary["succeeded"] == 0
    assert summary["empty"] == 100
    assert summary["errors"] == 0
    assert summary["availability"] == 0.0
    assert summary["availability_including_empty"] == 1.0  # 「没抛异常」只作参考
    assert summary["passed"] is False


def test_soak_counts_empty_and_errors_separately() -> None:
    """B1：空结果与异常分开计数，并在结论里分别显示。"""
    rows = (
        [_soak_row(index=i) for i in range(1, 9)]
        + [_soak_row(index=9, ok=True, results=0)]
        + [_soak_row(index=10, ok=False, results=0, error="TimeoutError: 上游超时")]
    )
    summary = summarize_soak_rows(rows)

    assert (summary["succeeded"], summary["empty"], summary["errors"]) == (8, 1, 1)
    assert summary["availability"] == pytest.approx(0.8)
    assert summary["availability_including_empty"] == pytest.approx(0.9)
    notes = "；".join(summary["notes"])
    assert "空结果 1 个" in notes
    assert "异常 1 个" in notes


def test_soak_suspect_kept_out_of_percentiles_but_in_availability_and_rss() -> None:
    """B3：休眠假样本排除出 P50/P95，但仍计入可用率与 RSS 序列。"""
    normal = [_soak_row(index=i, latency_ms=1000.0 + i) for i in range(1, 10)]
    sleeping = _soak_row(index=10, latency_ms=6_280_716.0, rss_bytes=140 * 1024 * 1024.0, suspect=True)
    summary = summarize_soak_rows(normal + [sleeping], interval_s=300)

    assert summary["suspect"] == 1
    assert summary["latency"]["count"] == 9
    assert summary["latency"]["max"] == pytest.approx(1009.0)  # 104 分钟的假样本没进分位
    assert summary["succeeded"] == 10  # 仍是有结果的采样
    assert summary["availability"] == 1.0
    assert summary["rss"]["samples"] == 10  # 仍留在 RSS 序列
    assert any("疑似休眠样本 1 个" in note for note in summary["notes"])


def test_soak_suspect_recomputed_for_legacy_rows() -> None:
    """旧格式 CSV 没有 suspect 列：给了 interval_s 就按延迟回算。"""
    rows = [_soak_row(index=i) for i in range(1, 5)]
    legacy = _soak_row(index=5, latency_ms=6_280_716.0)
    legacy.pop("suspect")
    summary = summarize_soak_rows(rows + [legacy], interval_s=300)

    assert summary["suspect"] == 1
    assert summary["latency"]["count"] == 4


def test_soak_skipped_slots_visible_and_excluded_from_availability() -> None:
    """B2：休眠后没跑的槽位记 SKIP，可见、计入覆盖，但不静默算作连续覆盖。"""
    rows = [_soak_row(index=i) for i in range(1, 7)]
    rows += [
        _soak_row(
            index=6 + i,
            skipped=True,
            ok=False,
            results=0,
            latency_ms="",
            rss_bytes=None,
            error="SKIPPED: 落后 4 个采样周期（>2×间隔），按规则不补跑",
        )
        for i in range(1, 5)
    ]
    summary = summarize_soak_rows(rows)

    assert summary["samples"] == 10
    assert summary["skipped"] == 4
    assert summary["succeeded"] == 6
    assert summary["availability"] == 1.0  # SKIP 不进可用率分母
    assert summary["coverage_ratio"] == pytest.approx(0.6)
    assert any("跳过 4 个采样槽位" in note for note in summary["notes"])


def test_soak_fails_when_coverage_below_floor() -> None:
    """B1 补丁：覆盖率是硬门槛 —— 「跳过 40% 槽位 + 其余全成功」不得再判通过。

    SKIP 不进可用率分母，所以可用率会显示 100%、`window_hours` 按首末时间戳看也没缩水；
    只有把覆盖率（20/... 实际打到的槽位占比）也当门槛，才能挡住这类假绿。
    """
    rows = [_soak_row(index=i) for i in range(1, 13)]  # 12 个真实成功样本
    rows += [
        _soak_row(
            index=12 + i,
            skipped=True,
            ok=False,
            results=0,
            latency_ms="",
            rss_bytes=None,
            error="SKIPPED: 落后 4 个采样周期（>2×间隔），按规则不补跑",
        )
        for i in range(1, 9)  # 8 个 SKIP -> 覆盖率 12/20 = 60% < 95%
    ]
    summary = summarize_soak_rows(rows)

    assert summary["samples"] == 20
    assert summary["skipped"] == 8
    assert summary["availability"] == 1.0  # 可用率仍是 100%（SKIP 不进分母）
    assert summary["coverage_ratio"] == pytest.approx(0.6)
    assert summary["passed"] is False  # 但覆盖率 60% < 95% -> 不通过
    assert any("采样覆盖率 60.0% 低于下限 95%" in note for note in summary["notes"])


def test_soak_fails_when_availability_below_floor_even_if_coverage_ok() -> None:
    """覆盖率达标（100%）但可用率不达标 -> 仍不通过：两个门槛是「与」关系。"""
    rows = [_soak_row(index=i) for i in range(1, 9)]
    rows += [
        _soak_row(index=9, ok=False, results=0, error="TimeoutError: 上游超时"),
        _soak_row(index=10, ok=False, results=0, error="TimeoutError: 上游超时"),
    ]
    summary = summarize_soak_rows(rows)

    assert summary["coverage_ratio"] == pytest.approx(1.0)
    assert summary["availability"] == pytest.approx(0.8)
    assert summary["passed"] is False
    assert any("可用率" in note for note in summary["notes"])


def test_soak_legacy_12_column_csv_parses(tmp_path) -> None:
    """旧格式（12 列）CSV 仍能解析：缺列时 suspect=None、skipped=False。"""
    path = tmp_path / "legacy.csv"
    path.write_text(
        SOAK_HEADER
        + "\n"
        + "1,2026-09-24 22:00:00,0.1,False,True,1200.5,5,0,False,104857600,q1,\n"
        # 未跳过却没有延迟 = 挂机被强杀时写坏的半截行，仍应丢弃
        + "2,2026-09-24 22:05:00,300.2,False,True,,0,0,False,105906176,q2,\n",
        encoding="utf-8",
    )
    rows = load_soak_rows(path)

    assert len(rows) == 1
    assert rows[0]["suspect"] is None
    assert rows[0]["skipped"] is False
    summary = summarize_soak_rows(rows, interval_s=300)
    assert summary["samples"] == 1
    assert summary["succeeded"] == 1


def test_evaluate_soak_and_summarize_share_the_same_availability() -> None:
    """B4：两条路径（在线判定与事后复算）的可用率口径必须完全一致。"""
    rows = (
        [_soak_row(index=i) for i in range(1, 10)]  # 9 有结果
        + [_soak_row(index=10, ok=True, results=0)]  # 1 空结果
        + [_soak_row(index=11, ok=False, results=0, error="ConnectError: 拒绝")]  # 1 异常
    )
    summary = summarize_soak_rows(rows)

    passed, _notes, details = evaluate_soak(
        total=summary["samples"] - summary["skipped"],
        succeeded=summary["succeeded"],
        empty=summary["empty"],
        errors=summary["errors"],
        rss_series=[float(row["rss_bytes"]) for row in rows],
    )

    assert details["availability"] == pytest.approx(summary["availability"])
    assert details["availability_including_empty"] == pytest.approx(summary["availability_including_empty"])
    assert details["empty"] == summary["empty"]
    assert details["errors"] == summary["errors"]
    assert passed == summary["passed"]


def test_evaluate_soak_empty_only_fails_but_reports_reference_rate() -> None:
    """evaluate_soak 自身也必须把「空结果」排除出成功（口径与汇总一致）。"""
    passed, _notes, details = evaluate_soak(
        total=100, succeeded=0, empty=100, rss_series=[1.0] * 10
    )
    assert passed is False
    assert details["availability"] == 0.0
    assert details["availability_including_empty"] == 1.0


# ---------------------------------------------------------------- 进程存活检测
def test_process_alive_detects_current_process() -> None:
    """当前进程必须判为存活（--status 的存活判定依赖它）。"""
    assert process_alive(os.getpid()) is True


def test_process_alive_false_for_invalid_pid() -> None:
    assert process_alive(0) is False
    assert process_alive(-1) is False
    assert process_alive(999_999_999) is False


def test_process_alive_false_after_child_exits() -> None:
    """子进程退出后必须判为「已退出」，否则挂机死了也会显示存活。"""
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    assert process_alive(child.pid) is False


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
