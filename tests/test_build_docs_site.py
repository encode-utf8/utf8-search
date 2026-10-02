"""scripts/build_docs_site.py 单测：Markdown 子集渲染 + 生成物新鲜度 + 纯前端约束。"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_docs_site as bds  # noqa: E402


def test_markdown_subset_rendering():
    md = ("# 标题\n\n## 小节\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\n"
          "- 一\n  - 二\n\n`code` **bold** [x](https://example.com)\n")
    out, heads = bds.md_to_html(md, "p", {}, REPO)
    assert "<h2" in out and "<table>" in out and "<ul>" in out and "<li>" in out
    assert "<code>code</code>" in out and "<strong>bold</strong>" in out
    assert "| --- |" not in out  # 表格分隔行不能泄漏到正文
    assert heads and heads[0][0].startswith("page-p--")


def test_table_escaped_pipe_and_inline_code():
    md = "| 检查 | 期望 |\n| --- | --- |\n| `ss -ltn \\| grep :443` | 监听 |\n"
    out, _ = bds.md_to_html(md, "p", {}, REPO)
    assert "<code>ss -ltn | grep :443</code>" in out


def test_repo_link_becomes_nonlink_ref(tmp_path):
    md = "见 [r](../gone.md)，以及 [hook](https://example.com)。\n"
    out, _ = bds.md_to_html(md, "p", {}, tmp_path)
    assert 'class="repo-ref"' in out
    assert 'href="https://example.com"' in out


def test_generated_site_is_fresh_and_offline():
    """提交的 docs/site/index.html 必须与生成器一致，且不加载任何外部资源。"""
    content = bds.build_site()
    assert bds.OUT_PATH.read_text(encoding="utf-8") == content
    assert "<script src=" not in content
    assert '<link rel="stylesheet"' not in content
    assert "url(http" not in content
    assert "const INDEX = [" in content
    assert 'id="page-clients"' in content and 'id="page-deploy"' in content
    # 左侧目录：分点 TOC + 当前页高亮所需的标记
    assert 'class="nav-page"' in content
    assert content.count('class="toc-link') > 50
    assert "nav-page.active" in content
