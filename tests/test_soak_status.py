"""`scripts/soak.py --status` 的离线测试。

重点覆盖「心跳超期」告警：只有**未收尾**（`finished=False`）才提示进程可能卡住/被杀；
挂机正常收尾（`finished=True`）时心跳天然停在最后一次采样，再报警就是误报。

刻意不启动任何采样，只造 meta.json + 明细 CSV，因此不需要网络，默认随 `-m "not net"` 一起跑。
"""

from __future__ import annotations

import csv
import json
import os
import sys
from argparse import Namespace
from datetime import datetime, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import soak  # noqa: E402 - 需要先把 scripts/ 加进 sys.path


def _write_case(
    tmp_path: Path, *, finished: bool, heartbeat_age_s: float, interval: float = 60.0
) -> Namespace:
    """造一份「已有 N 行样本 + 心跳在 X 秒前」的挂机产物，返回 --status 需要的 args。"""
    out = tmp_path / "soak.csv"
    base = datetime(2026, 9, 26, 0, 0, 0)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(soak.COLUMNS)
        for index in range(1, 6):
            writer.writerow(
                [
                    index,
                    (base + timedelta(minutes=5 * (index - 1))).strftime("%Y-%m-%d %H:%M:%S"),
                    (index - 1) * 300.0,
                    False,
                    True,
                    1000.0 + index,
                    5,
                    0,
                    False,
                    100 * 1024 * 1024.0,
                    "q",
                    "",
                    False,
                    False,
                ]
            )
    out.with_suffix(".meta.json").write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "started_at": "2026-09-26 00:00:00",
                "updated_at": (datetime.now() - timedelta(seconds=heartbeat_age_s)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "finished": finished,
                "planned_hours": 24.0,
                "interval_s": interval,
                "mode": "basic",
                "samples_written": 5,
            }
        ),
        encoding="utf-8",
    )
    return Namespace(meta="", out=str(out), interval=interval, json_out="")


def test_status_suppresses_heartbeat_warning_when_finished(tmp_path, capsys) -> None:
    """正常收尾（finished=True）：心跳停在最后一次采样是预期的，不得误报超期；
    同时「覆盖窗口」按 CSV 全部行打印，并另附「计入统计窗口」参考值。"""
    args = _write_case(tmp_path, finished=True, heartbeat_age_s=3600)

    assert soak._print_status(args) == 0

    printed = capsys.readouterr().out
    assert "finished=True" in printed
    assert "⚠ 心跳已超过 3 个采样周期" not in printed
    assert "覆盖窗口" in printed
    assert "0.33 h，按 CSV 全部行含预热" in printed
    assert "计入统计窗口" in printed


def test_status_warns_on_stale_heartbeat_when_not_finished(tmp_path, capsys) -> None:
    """未收尾（finished=False）心跳超期：仍要提示进程可能卡住/被杀。"""
    args = _write_case(tmp_path, finished=False, heartbeat_age_s=3600, interval=60.0)

    assert soak._print_status(args) == 0

    printed = capsys.readouterr().out
    assert "finished=False" in printed
    assert "⚠ 心跳已超过 3 个采样周期" in printed
