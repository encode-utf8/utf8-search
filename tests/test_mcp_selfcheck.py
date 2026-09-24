"""MCP 自检脚本的离线测试（M4-4.3）。

覆盖 `scripts/mcp_selfcheck.py` 里**不需要联网**的部分：

- `resolve_modes` / `parse_args` 的参数解析（别名、默认值）；
- `_host_matches` / `_expect_status` / `render_report` 这些纯函数；
- **真实 MCP stdio 握手**：拉起 `python -m utf8_search stdio` 子进程，走官方 SDK 做
  `initialize` + `tools/list`，并用脚本里的契约校验工具的参数 schema；
- **stdio 协议通道纯净度**：绕过 SDK 直接读写管道，断言 stdout 每一行都是合法 JSON-RPC
  （这是「进程起来了但工具调不通」的头号原因，必须有离线回归）。

刻意不触发任何搜索/抽取，因此不需要网络，默认随 `-m "not net"` 一起跑。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import mcp_selfcheck  # noqa: E402 - 需要先把 scripts/ 加进 sys.path


def test_resolve_modes_supports_aliases() -> None:
    """`--mode` 要接受别名与 all，并保持通道顺序、去重。"""
    assert mcp_selfcheck.resolve_modes("all") == list(mcp_selfcheck.ALL_CHANNELS)
    assert mcp_selfcheck.resolve_modes("http") == ["http-mcp"]
    assert mcp_selfcheck.resolve_modes("http-mcp,http") == ["http-mcp"]
    assert mcp_selfcheck.resolve_modes("rest,stdio") == ["rest", "stdio"]
    # 空串退化为「全部通道」，避免误传导致什么都没跑
    assert mcp_selfcheck.resolve_modes(" , ") == list(mcp_selfcheck.ALL_CHANNELS)
    with pytest.raises(SystemExit):
        mcp_selfcheck.resolve_modes("nonexistent")


def test_parse_args_defaults() -> None:
    """默认参数：全通道、自检 Key、内置查询。"""
    args = mcp_selfcheck.parse_args([])
    assert args.mode == "all"
    assert args.api_key == mcp_selfcheck.SELFCHECK_KEY
    assert args.query == mcp_selfcheck.DEFAULT_QUERY
    assert args.base_url is None
    assert args.out is None


def test_host_matches_includes_subdomains() -> None:
    """域名白名单匹配要覆盖子域，但不能被相似后缀骗过。"""
    assert mcp_selfcheck._host_matches("https://www.gov.cn/a/b", "gov.cn")
    assert mcp_selfcheck._host_matches("https://news.sina.com.cn/x", "sina.com.cn")
    assert not mcp_selfcheck._host_matches("https://fakegov.cn/x", "gov.cn")
    assert not mcp_selfcheck._host_matches("", "gov.cn")


def test_expect_status_verdict() -> None:
    """状态码判定函数：命中即通过，否则带上响应片段便于定位。"""
    verdict = mcp_selfcheck._expect_status(401)
    assert verdict(401, {})[0] is True
    ok, detail = verdict(200, {"error": "nope"})
    assert ok is False and "401" in detail


def test_render_report_lists_failures_and_manual_checklist() -> None:
    """报告要能反映失败项，并带上待回填的人工联调清单。"""
    rec = mcp_selfcheck.Recorder()
    rec.add("rest", "demo-ok", True, "一切正常", 0.1)
    rec.add("stdio", "demo-bad", False, "握手失败", 0.2)
    args = mcp_selfcheck.parse_args(["--mode", "rest", "--out", "data/x.md"])
    report = mcp_selfcheck.render_report(rec, args, ["rest"], ["http://127.0.0.1:1（临时实例）"])

    assert "1 项失败" in report
    assert "demo-bad" in report
    assert "| rest | 1 | 1 | 0 | 0 |" in report
    for client, _ in mcp_selfcheck.MANUAL_CLIENTS:
        assert client in report


async def test_stdio_handshake_and_tools() -> None:
    """真实子进程上的 MCP stdio 握手与工具发现（无搜索调用，离线可跑）。"""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    rec = mcp_selfcheck.Recorder()
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "utf8_search", "stdio"],
        env=mcp_selfcheck._child_env(),
        cwd=str(mcp_selfcheck.REPO_ROOT),
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init = await asyncio.wait_for(session.initialize(), timeout=60)
            info = mcp_selfcheck._get(init, "server_info", "serverInfo", default=None)
            assert getattr(info, "name", None) == "utf8-search"
            assert getattr(info, "version", None)
            # instructions 会展示在支持该字段的客户端里，丢了会少掉「什么时候该搜」的提示
            assert mcp_selfcheck._get(init, "instructions")

            listed = await asyncio.wait_for(session.list_tools(), timeout=30)
            tools = list(mcp_selfcheck._get(listed, "tools", default=[]) or [])

    assert {tool.name for tool in tools} >= set(mcp_selfcheck.EXPECTED_TOOLS)
    mcp_selfcheck._verify_tool_schemas(rec, "stdio", tools, 0.0)
    assert not rec.failed, [check.detail for check in rec.failed]


async def test_stdio_raw_channel_is_jsonrpc_only() -> None:
    """stdio 的 stdout 必须只有 JSON-RPC：任何 print/日志污染都会让客户端解析失败。"""
    rec = mcp_selfcheck.Recorder()
    await mcp_selfcheck.check_stdio_raw(rec, timeout=60.0)
    assert not rec.failed, [check.detail for check in rec.failed]