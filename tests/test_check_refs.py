"""scripts/check_refs.py 的单测：有界提取 + 已清理引用标记 + 仓库自检。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import check_refs  # noqa: E402

RP = "docs/" + "reports/"


def ref(name: str) -> str:
    """测试里拼出示例路径，避免测试文件本身被 check_refs 误判为引用不存在的文件。"""
    return RP + name


def test_extract_tokens_is_bounded_and_keeps_patterns():
    text = ("证据见 `" + ref("m29-t12-20261002-run{1..3}-{brief.md,scores.csv}") + "`，"
            "以及 " + ref("20261002-clients-sim.md") + "；data/foo.json 只统计。")
    tokens = check_refs.extract_tokens(text)
    assert ref("m29-t12-20261002-run{1..3}-{brief.md,scores.csv}") in tokens
    assert ref("20261002-clients-sim.md") in tokens
    assert len(tokens) < 10  # 不做花括号展开


def test_token_status_existing_cleaned_missing_and_docs_number():
    exists = {ref("a.md"), "docs/" + "04-路线图.md"}
    cleaned = {ref("gone.md")}
    ok, _ = check_refs.token_status(ref("a.md"), REPO, exists, cleaned)
    assert ok == "ok"
    status, _ = check_refs.token_status(ref("gone.md"), REPO, exists, cleaned)
    assert status == "cleaned-ok"
    status, _ = check_refs.token_status(ref("never.md"), REPO, exists, cleaned)
    assert status == "missing"
    # docs/00 是文档集占位编号；docs/04 需真实存在
    assert check_refs.token_status("docs/00", REPO, exists, cleaned)[0] == "ok"
    assert check_refs.token_status("docs/04", REPO, exists, cleaned)[0] == "ok"


def test_cleaned_ref_requires_policy_marker(tmp_path):
    cleaned = {ref("gone.md")}
    names = {"gone.md": ref("gone.md")}
    target = tmp_path / "doc.md"
    target.write_text("# t\n\n见 `" + ref("gone.md") + "`。\n", encoding="utf-8")
    problems = check_refs.check_file("doc.md", tmp_path, set(), cleaned, names)
    assert problems and "缺少标记" in problems[0]["reason"]

    target.write_text("# t\n<!-- refs-policy: cleaned-2026-10-02 -->\n\n见 `" + ref("gone.md") + "`。\n",
                      encoding="utf-8")
    assert check_refs.check_file("doc.md", tmp_path, set(), cleaned, names) == []


def test_repo_has_no_dangling_refs():
    """仓库自检：所有非忽略文件的路径引用都可核实（由 CI/本地 pytest 守住）。"""
    result = check_refs.run(REPO)
    assert result["violations"] == []
    assert result["scanned_files"] > 100
    assert result["cleaned_registry"] > 100
