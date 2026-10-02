"""scripts/build_docs_site.py 单测：Markdown 子集渲染 + 生成物新鲜度 + 纯前端约束。"""

from __future__ import annotations

import sys
import re
import shutil
import subprocess
from pathlib import Path

import pytest

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
    assert 'id="page-tester"' in content
    for marker in ('id="t-base"', 'id="t-check-key"', 'id="t-probe"', 'id="t-transport"', 'id="t-body"', 'id="t-send"'):
        assert marker in content
    # 左侧目录：分点 TOC + 当前页高亮所需的标记
    assert 'class="nav-page"' in content
    assert content.count('class="toc-link') > 50
    assert "nav-page.active" in content


@pytest.mark.skipif(shutil.which("node") is None, reason="node 不可用，跳过 JS 逻辑校验")
def test_tester_javascript_logic(tmp_path):
    """把测试台的 JS 抽出来做语法检查 + 纯函数单测（parseSSE / classifyProbe / 请求体构造）。"""
    frag = (REPO / "docs/site/content/tester.html").read_text(encoding="utf-8")
    script = re.search(r"<script>(.*?)</script>", frag, re.S).group(1)
    js = tmp_path / "tester.js"
    js.write_text(script, encoding="utf-8")
    syntax = subprocess.run([shutil.which("node"), "--check", str(js)], capture_output=True, text=True)
    assert syntax.returncode == 0, syntax.stderr
    probe = (
        "const assert=require('assert');"
        "const T=require(process.env.TESTER_JS);"
        "assert.deepStrictEqual(T.parseSSE('data: {\"a\":1}\\n\\ndata: bad\\n'),[{a:1},{raw:'bad'}]);"
        "assert.strictEqual(T.classifyProbe(200,{results:[{engine:'yandex'}]},'yandex').state,'ok');"
        "assert.strictEqual(T.classifyProbe(200,{results:[{engine:'bing'}],failed_engines:['brave']},'brave').state,'fallback');"
        "assert.strictEqual(T.classifyProbe(200,{results:[],failed_engines:['x']},'x').state,'err');"
        "assert.strictEqual(T.classifyProbe(429,{},'x').state,'err');"
        "assert.strictEqual(T.buildMcpCall('q',2).params.arguments.max_results,2);"
        "console.log('ok');"
    )
    env = {"TESTER_JS": str(js), "PATH": "/usr/bin:/bin"}
    run = subprocess.run([shutil.which("node"), "-e", probe], capture_output=True, text=True, env=env)
    assert run.returncode == 0, run.stdout + run.stderr
