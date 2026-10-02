"""各客户端仿真脚本的离线测试（2026-10-02）。

覆盖 `scripts/clients_sim.py` 里**不需要联网**的部分：

- 各客户端配置格式的「生成 → 解析」往返：Claude Desktop / Cursor 的 JSON、
  Codex 的 TOML（含 Python 3.10 上无 `tomllib` 时的正则兜底）、Cherry Studio 的图形界面字段；
- 解析失败路径（把 HTTP 形态配置当 stdio 用、配置里没有 url）；
- 报告用的结果判定（`_search_problems`）与 `Recorder` 的统计口径。

刻意不发起任何真实连接，因此不需要网络，默认随 `-m "not net"` 一起跑。
"""

from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import clients_sim  # noqa: E402 - 需要先把 scripts/ 加进 sys.path

LINUX_ENTRY = "/root/utf8-search/.venv/bin/utf8-search"


def test_claude_json_roundtrip() -> None:
    """Claude Desktop 的 claude_desktop_config.json：command/args/env 必须原样往返。"""
    argv, env = clients_sim.parse_json_mcp(clients_sim.render_claude_json([LINUX_ENTRY]))
    assert argv == [LINUX_ENTRY]
    assert env["UTF8SEARCH_SEARXNG_URL"] == clients_sim.SEARXNG_URL
    assert env["UTF8SEARCH_TRUST_ENV"] == "false"


def test_cursor_stdin_json_roundtrip() -> None:
    """Cursor 的 mcp.json（docs §3.3 只给 TRUST_ENV）也要能解析成同一份启动参数。"""
    argv, env = clients_sim.parse_json_mcp(clients_sim.render_cursor_json([LINUX_ENTRY]))
    assert argv == [LINUX_ENTRY]
    assert env == {"UTF8SEARCH_TRUST_ENV": "false"}


def test_json_config_rejects_http_shape() -> None:
    """把 HTTP 形态的配置（含 url）当 stdio 用必须报错，而不是静默起一个错命令。"""
    text = clients_sim.render_cursor_http_json("http://127.0.0.1:8000", "k1")
    with pytest.raises(ValueError):
        clients_sim.parse_json_mcp(text)


def test_codex_toml_roundtrip() -> None:
    """Codex 的 config.toml：TOML 生成后要能解析回 command 与 env。"""
    argv, env, how = clients_sim.parse_codex_toml(clients_sim.render_codex_toml([LINUX_ENTRY]))
    assert argv == [LINUX_ENTRY]
    assert env["UTF8SEARCH_LOG_LEVEL"] == "WARNING"
    assert how in {"tomllib", "tomli"}


def test_codex_toml_regex_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Python 3.10 上既没有 tomllib 也可能没有 tomli：正则兜底必须仍能解析 docs 的写法。"""
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):  # noqa: ANN401 - 测试替身
        if name in {"tomllib", "tomli"}:
            raise ModuleNotFoundError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    argv, env, how = clients_sim.parse_codex_toml(clients_sim.render_codex_toml([LINUX_ENTRY]))
    assert argv == [LINUX_ENTRY]
    assert env["UTF8SEARCH_SEARXNG_URL"] == clients_sim.SEARXNG_URL
    assert how == "正则兜底"


def test_codex_toml_real_entry_shape() -> None:
    """真实 config.toml 的写法（单引号字符串 + 额外小节）也要能解析。"""
    text = (
        "[mcp_servers]\n\n"
        "[mcp_servers.utf8-search]\n"
        'type = "stdio"\n'
        f"command = '{LINUX_ENTRY}'\n"
        "startup_timeout_sec = 60\n\n"
        "[mcp_servers.utf8-search.env]\n"
        'UTF8SEARCH_SEARXNG_URL = "http://127.0.0.1:8888"\n'
        'UTF8SEARCH_TRUST_ENV = "false"\n'
    )
    argv, env, _ = clients_sim.parse_codex_toml(text)
    assert argv == [LINUX_ENTRY]
    assert env["UTF8SEARCH_TRUST_ENV"] == "false"


def test_cherry_fields_roundtrip() -> None:
    """Cherry Studio 的图形界面字段：命令/参数/环境变量按界面语义拆开。"""
    fields = clients_sim.render_cherry_stdio_fields(["/usr/bin/python", "-m", "utf8_search"])
    argv, env = clients_sim.parse_cherry_stdio_fields(fields)
    assert argv == ["/usr/bin/python", "-m", "utf8_search"]
    assert env == {"UTF8SEARCH_TRUST_ENV": "false"}


def test_http_config_roundtrip() -> None:
    """HTTP 形态：Cursor 的 url+headers 与 Cherry 的界面字段要解析出同样的目标与请求头。"""
    url, headers = clients_sim.parse_http_json(
        clients_sim.render_cursor_http_json("http://127.0.0.1:8000/", "k1")
    )
    assert url == "http://127.0.0.1:8000/mcp"
    assert headers == {"X-API-Key": "k1"}

    url2, headers2 = clients_sim.parse_cherry_http_fields(
        clients_sim.render_cherry_http_fields("http://127.0.0.1:8000", "k1")
    )
    assert (url2, headers2) == (url, headers)


def test_search_problems_flags_empty_and_missing_fields() -> None:
    """报告判定：空结果、缺 url/title、response_time 非数字都要被抓出来。"""
    assert clients_sim._search_problems({"results": [{"url": "u", "title": "t"}], "response_time": 1.0}) == []
    problems = clients_sim._search_problems({"results": [], "response_time": "1.0"})
    assert "results 为空" in problems and "response_time 不是数字" in problems
    assert "第 1 条缺 url" in clients_sim._search_problems(
        {"results": [{"title": "t"}], "response_time": 1.0}
    )


def test_search_problems_tavily_fields() -> None:
    """Tavily 迁移场景要额外断言顶层兼容字段存在。"""
    payload = {"results": [{"url": "u", "title": "t"}], "response_time": 1.0}
    problems = clients_sim._search_problems(payload, tavily=True)
    assert "缺 Tavily 字段 request_id" in problems
    payload.update({"query": "q", "request_id": "r", "auto_parameters": {}, "usage": {"credits": 0}})
    assert clients_sim._search_problems(payload, tavily=True) == []


def test_recorder_counts_and_order() -> None:
    """Recorder 的统计口径：SKIP 不计入失败，客户端顺序按首次出现。"""
    rec = clients_sim.Recorder()
    rec.add("A", "s1", True, "ok", 0.1)
    rec.add("B", "s1", False, "bad", 0.2)
    rec.add("C", "s1", True, "跳过", skip=True)
    assert [c.client for c in rec.failed] == ["B"]
    assert len(rec.executed) == 2
    assert rec.client_names() == ["A", "B", "C"]
