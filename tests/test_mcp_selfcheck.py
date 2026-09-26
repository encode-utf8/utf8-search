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
import os
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


def test_mask_api_key_keeps_only_head_and_tail() -> None:
    """掩码只保留前 4 + 后 4；短板/空 Key 一律整体打码。"""
    assert mcp_selfcheck.mask_api_key("utf8_abcdefghijklmnop") == "utf8…mnop"
    assert mcp_selfcheck.mask_api_key("short") == "*****"
    assert mcp_selfcheck.mask_api_key("") == "(未提供)"


def test_render_report_never_leaks_full_api_key() -> None:
    """报告任何位置都不得出现完整 API Key（归档/分享即泄露）。"""
    secret = "utf8_abcdefghijklmnopqrstuvwxyz0123456789"
    rec = mcp_selfcheck.Recorder()
    rec.add("rest", "demo-ok", True, "一切正常", 0.1)
    args = mcp_selfcheck.parse_args(["--api-key", secret])
    masked = mcp_selfcheck.mask_api_key(secret)

    # 场景 1：调用方按约定传入掩码 —— 报告里只应有掩码形态
    report = mcp_selfcheck.render_report(
        rec, args, ["rest"], [f"http://127.0.0.1:1（临时实例，API Key={masked}，RPM=1）"]
    )
    assert secret not in report
    assert masked in report

    # 场景 2：调用方忘了掩码 —— render_report 必须兜底把明文替换掉
    report_raw = mcp_selfcheck.render_report(
        rec, args, ["rest"], [f"http://127.0.0.1:1（临时实例，API Key={secret}，RPM=1）"]
    )
    assert secret not in report_raw
    assert masked in report_raw


def test_render_report_reproduce_command_is_platform_adaptive() -> None:
    """复现命令不得硬编码 Windows 路径：本机解释器与代码块语言按平台给出。"""
    rec = mcp_selfcheck.Recorder()
    args = mcp_selfcheck.parse_args(["--mode", "rest"])
    report = mcp_selfcheck.render_report(rec, args, ["rest"], [])

    assert "scripts/mcp_selfcheck.py" in report
    if os.name == "nt":
        assert "```powershell" in report
    else:
        assert "```bash" in report
        assert "\\Scripts\\python.exe" not in report


def test_news_freshness_all_within_window_passes() -> None:
    """全部落在窗口内 → 覆盖率 100%，判定通过，结论给出比例/窗口/最旧天数。"""
    passed, detail = mcp_selfcheck.evaluate_news_freshness([0.5, 1.0, 2.5, 6.9], window_days=7.0)

    assert passed is True
    assert "100%" in detail
    assert "7 天窗口" in detail
    assert "最旧" in detail


def test_news_freshness_one_of_five_over_window_still_passes() -> None:
    """5 条里 1 条超窗 → 覆盖率 4/5 = 80% ≥ 门槛，仍判通过（这正是旧口径误杀的场景）。"""
    passed, detail = mcp_selfcheck.evaluate_news_freshness(
        [0.4, 1.2, 2.0, 5.1, 8.3], window_days=7.0
    )

    assert passed is True
    assert "80%" in detail


def test_news_freshness_two_of_five_over_window_fails() -> None:
    """5 条里 2 条超窗 → 覆盖率 3/5 = 60% < 80%，判定不通过。"""
    passed, detail = mcp_selfcheck.evaluate_news_freshness(
        [0.4, 1.2, 5.0, 9.0, 11.5], window_days=7.0
    )

    assert passed is False
    assert "60%" in detail


def test_news_fresh_window_caps_at_seven_days() -> None:
    """窗口取 min(配置, 7)：部署可更严，但不能放宽到 7 天以上。"""
    assert mcp_selfcheck.news_fresh_window_days(7) == 7.0
    assert mcp_selfcheck.news_fresh_window_days(3) == 3.0
    assert mcp_selfcheck.news_fresh_window_days(30) == 7.0


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
