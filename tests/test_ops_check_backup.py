"""ops_check 备份判据的离线测试（2026-09-30 P6：P2×P3 交叉缺陷）。

缺陷回顾：P3 之后备份产物默认是 `*.tar.gz.enc`，而 `check_backup` 只 glob `*.tar.gz`
⇒ 加密备份上线后巡检每 5 分钟误报「未找到任何备份产物」（288 次/天，把告警通道淹掉）。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from ops_check import check_backup  # noqa: E402


def _make_backup(directory: Path, *, suffix: str, age_hours: float) -> None:
    """造一份「产物 + SHA256SUMS」同龄的备份对（age_hours 控制 mtime 年龄）。"""
    directory.mkdir(parents=True, exist_ok=True)
    artifact = directory / f"utf8-search-backup-20260930{suffix}"
    artifact.write_text("dummy", encoding="utf-8")
    sums = directory / "SHA256SUMS"
    sums.write_text("dummy  file\n", encoding="utf-8")
    stamp = time.time() - age_hours * 3600
    os.utime(artifact, (stamp, stamp))
    os.utime(sums, (stamp, stamp))


def test_encrypted_only_directory_is_not_reported_missing(tmp_path) -> None:
    """（本条就是回归用例）目录里只有 .enc 产物时，巡检不得报「未找到备份」。"""
    _make_backup(tmp_path, suffix=".tar.gz.enc", age_hours=1.0)
    problems, info = check_backup(str(tmp_path), max_age_hours=48.0)
    assert problems == []
    assert info["backup_artifact"].endswith(".tar.gz.enc")


def test_plaintext_artifact_still_accepted(tmp_path) -> None:
    """历史明文包（.tar.gz）仍然被认，避免回退兼容性丢失。"""
    _make_backup(tmp_path, suffix=".tar.gz", age_hours=2.0)
    problems, _info = check_backup(str(tmp_path), max_age_hours=48.0)
    assert problems == []


def test_expired_artifact_alerts(tmp_path) -> None:
    """产物过期（> max_age_hours）要告警。"""
    _make_backup(tmp_path, suffix=".tar.gz.enc", age_hours=72.0)
    problems, info = check_backup(str(tmp_path), max_age_hours=48.0)
    assert problems and "小时" in problems[0]
    assert info["backup_age_hours"] > 48


def test_missing_artifact_alerts(tmp_path) -> None:
    """空目录（或只剩 SHA256SUMS）要告警。"""
    (tmp_path / "SHA256SUMS").write_text("dummy\n", encoding="utf-8")
    problems, _info = check_backup(str(tmp_path), max_age_hours=48.0)
    assert problems and "未找到" in problems[0]


def test_new_sums_with_old_artifact_not_counted_as_fresh(tmp_path) -> None:
    """「新校验和 + 旧包」不算新鲜：两者必须同龄（≤1h）。"""
    _make_backup(tmp_path, suffix=".tar.gz.enc", age_hours=100.0)   # 包很旧
    sums = tmp_path / "SHA256SUMS"
    now = time.time()
    os.utime(sums, (now, now))                                      # 只把校验和刷新
    problems, _info = check_backup(str(tmp_path), max_age_hours=48.0)
    assert problems, "不同龄的 pair 不应被当成有效备份"
