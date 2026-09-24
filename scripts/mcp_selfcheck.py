"""客户端联调自检（M4-4.3）：把「逐个真实客户端手点」里可自动化的部分固化成一个脚本。

背景：Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent 与服务交互，
最终只走三条通道 ——

1. **MCP stdio**：本地客户端启动 `utf8-search stdio` 子进程，通过 stdin/stdout 走 MCP 协议；
2. **MCP Streamable HTTP**：连 `http://<host>:<port>/mcp`；
3. **Tavily 兼容 REST**：`/v1/search`、`/v1/extract`。

本脚本用**官方 MCP SDK 客户端**（`mcp` 包，与真实客户端同源实现）与普通 HTTP 客户端，
把这三条通道端到端跑一遍：握手、能力协商、工具发现、工具调用、鉴权、限流、参数兼容。

无法自动化的部分（各客户端自己的配置界面/文件名）由 `docs/03-客户端接入指南.md` 的
**人工联调清单**覆盖，本脚本生成的报告里也带一份待回填的表。

用法：
    python scripts/mcp_selfcheck.py                       # 全部通道（自动起本地 HTTP 服务）
    python scripts/mcp_selfcheck.py --mode stdio,stdio-raw # 只测 stdio
    python scripts/mcp_selfcheck.py --base-url http://127.0.0.1:8000   # 复用已启动的服务
    python scripts/mcp_selfcheck.py --out docs/reports/m4-4.3-client-selfcheck-20260924.md

退出码：0 = 全部通过；1 = 有失败项。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

# 自检用的临时 Key：只在本机 127.0.0.1 上生效，跑到一半就随进程一起消失
SELFCHECK_KEY = "selfcheck-key"
# 各通道的默认查询：中文查询最能覆盖我们的引擎名单与质量过滤
DEFAULT_QUERY = "2026年 新能源汽车 补贴政策"
DEFAULT_NEWS_QUERY = "最近一周 AI 行业动态"
# 抽取自检用的页面：内容短、稳定、无需登录（实测 131 字符）
EXTRACT_URL = "https://example.com"

ALL_CHANNELS = ("stdio", "stdio-raw", "http-mcp", "rest", "ratelimit")


@dataclass
class Check:
    """一条自检结果。"""

    channel: str
    name: str
    passed: bool
    detail: str = ""
    elapsed: float = 0.0
    skipped: bool = False


class Recorder:
    """收集并实时打印自检结果。"""

    def __init__(self) -> None:
        self.checks: list[Check] = []

    def add(
        self,
        channel: str,
        name: str,
        passed: bool,
        detail: str = "",
        elapsed: float = 0.0,
        skipped: bool = False,
    ) -> Check:
        mark = "SKIP" if skipped else ("PASS" if passed else "FAIL")
        check = Check(channel, name, passed, detail, elapsed, skipped)
        self.checks.append(check)
        print(f"  [{mark}] {channel:<10} {name:<34} {detail}  ({elapsed:.2f}s)", flush=True)
        return check

    def fail(self, channel: str, name: str, exc: BaseException, elapsed: float = 0.0) -> Check:
        return self.add(channel, name, False, f"{type(exc).__name__}: {exc}", elapsed)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.passed and not c.skipped]

    @property
    def executed(self) -> list[Check]:
        return [c for c in self.checks if not c.skipped]


def _free_port() -> int:
    """取一个当前空闲的本机端口（避免与用户已启动的服务撞车）。"""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _child_env(**overrides: str) -> dict[str, str]:
    """子进程环境：继承当前环境，叠加自检需要的覆盖项。"""
    env = {**os.environ, "UTF8SEARCH_LOG_LEVEL": "WARNING"}
    env.update(overrides)
    return env


def _import_httpx():
    """只依赖项目已有的 httpx（REST 通道用）。"""
    import httpx

    return httpx


class LocalServer:
    """起一个本地 `utf8-search serve` 实例（独立端口 / Key / 限流配置），退出时清理。

    用真实 HTTP 服务而不是 FastAPI TestClient：客户端的实际路径就是「TCP + HTTP」，
    TestClient 会绕过 ASGI 服务器的传输层（Host 校验、SSE、分块等），测不出真实问题。
    """

    def __init__(self, *, api_keys: str = SELFCHECK_KEY, rate_limit_rpm: int = 0, note: str = "") -> None:
        self.port = _free_port()
        self.api_keys = api_keys
        self.rate_limit_rpm = rate_limit_rpm
        self.note = note
        self.process: asyncio.subprocess.Process | None = None
        self.log_lines: list[str] = []

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def __aenter__(self) -> "LocalServer":
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    async def start(self) -> None:
        env = _child_env(
            UTF8SEARCH_API_KEYS=self.api_keys,
            UTF8SEARCH_RATE_LIMIT_RPM=str(self.rate_limit_rpm),
            UTF8SEARCH_LOG_LEVEL="WARNING",
        )
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "utf8_search",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            cwd=str(REPO_ROOT),
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        if not await self._wait_ready(timeout=60.0):
            await self.stop()
            raise RuntimeError(
                f"本地 serve 实例未在 60s 内就绪（port={self.port}）"
                + (f"；stderr: {' / '.join(self.log_lines[-3:])}" if self.log_lines else "")
            )

    async def _wait_ready(self, *, timeout: float) -> bool:
        """轮询 /health，直到服务可用（冷启动要预热流水线）。"""
        httpx = _import_httpx()
        deadline = time.monotonic() + timeout
        async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
            while time.monotonic() < deadline:
                if self.process is not None and self.process.returncode is not None:
                    await self._drain_stderr()
                    return False
                try:
                    response = await client.get(f"{self.base_url}/health")
                    if response.status_code == 200:
                        return True
                except Exception:  # noqa: BLE001 - 未就绪时连接被拒是正常的
                    pass
                await asyncio.sleep(0.4)
        return False

    async def _drain_stderr(self) -> None:
        """把子进程 stderr 里的报错收进来（服务起动失败时用来定位）。"""
        if self.process is None or self.process.stderr is None:
            return
        try:
            raw = await asyncio.wait_for(self.process.stderr.read(), timeout=1.0)
        except (asyncio.TimeoutError, TimeoutError):
            return
        if raw:
            self.log_lines.extend(raw.decode("utf-8", "replace").splitlines()[-20:])

    async def stop(self) -> None:
        if self.process is None:
            return
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=8.0)
            except (asyncio.TimeoutError, TimeoutError):
                self.process.kill()
                await self.process.wait()
        await self._drain_stderr()


# ---------------------------------------------------------------- MCP 断言工具
def _get(obj: Any, *names: str, default: Any = None) -> Any:
    """兼容 SDK 不同版本的字段命名（snake_case / camelCase）。"""
    for name in names:
        value = getattr(obj, name, None)
        if value is not None:
            return value
    return default


def _tool_payload(result: Any) -> dict[str, Any]:
    """把工具调用结果转成 dict：优先结构化内容，其次解析文本块里的 JSON。"""
    structured = _get(result, "structured_content", "structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in _get(result, "content", default=[]) or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _tool_error(result: Any) -> str | None:
    """工具返回 is_error=True 时，把文本内容拼成一句错误说明。"""
    if not _get(result, "is_error", "isError", default=False):
        return None
    texts = [getattr(block, "text", "") for block in _get(result, "content", default=[]) or []]
    return "工具返回错误：" + (" / ".join(text for text in texts if text) or "(无详情)")


def _schema_enums(node: Any) -> set[str]:
    """递归收集 JSON Schema 里出现的所有 enum 值（兼容 anyOf/oneOf 包装）。"""
    found: set[str] = set()
    if isinstance(node, dict):
        for value in node.get("enum", []) or []:
            found.add(str(value))
        for value in node.values():
            found |= _schema_enums(value)
    elif isinstance(node, list):
        for value in node:
            found |= _schema_enums(value)
    return found


# web_search / web_fetch 对客户端暴露的参数契约：少一个参数，某个客户端就可能调不通
EXPECTED_TOOLS: dict[str, dict[str, Any]] = {
    "web_search": {
        "required": {"query"},
        "properties": {
            "query",
            "max_results",
            "search_depth",
            "topic",
            "time_range",
            "include_domains",
            "exclude_domains",
            "include_raw_content",
        },
        "enums": {"basic", "advanced", "deep", "general", "news", "day", "week", "month", "year"},
    },
    "web_fetch": {
        "required": {"urls"},
        "properties": {"urls", "format", "max_chars"},
        "enums": {"markdown", "text"},
    },
}


def _verify_tool_schemas(rec: Recorder, channel: str, tools: list[Any], elapsed: float) -> None:
    """校验两个工具是否都暴露，且参数名/必填项/枚举与契约一致。"""
    by_name = {getattr(tool, "name", ""): tool for tool in tools}
    names = ",".join(sorted(by_name))
    missing = set(EXPECTED_TOOLS) - set(by_name)
    if missing:
        rec.add(channel, "tools/list", False, f"缺少工具 {sorted(missing)}；实际有 {names}", elapsed)
        return

    problems: list[str] = []
    for name, spec in EXPECTED_TOOLS.items():
        tool = by_name[name]
        schema = _get(tool, "input_schema", "inputSchema", default={}) or {}
        properties = set((schema.get("properties") or {}).keys())
        required = set(schema.get("required") or [])
        if not properties >= spec["properties"]:
            problems.append(f"{name} 缺参数 {sorted(spec['properties'] - properties)}")
        if not required >= spec["required"]:
            problems.append(f"{name} 缺必填项 {sorted(spec['required'] - required)}")
        enums = _schema_enums(schema)
        if not enums >= spec["enums"]:
            problems.append(f"{name} 枚举缺 {sorted(spec['enums'] - enums)}")
    if problems:
        rec.add(channel, "tools/list", False, "；".join(problems), elapsed)
    else:
        rec.add(channel, "tools/list", True, f"工具 {names}（参数/必填/枚举均符合契约）", elapsed)


def _verify_search_payload(rec: Recorder, channel: str, name: str, payload: dict[str, Any], elapsed: float) -> None:
    """校验一次搜索返回的结构（MCP 工具与 REST 共用同一套字段）。"""
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        rec.add(channel, name, False, f"结果为空：{json.dumps(payload, ensure_ascii=False)[:160]}", elapsed)
        return
    missing = [key for key in ("query", "results", "response_time", "request_id") if key not in payload]
    if missing:
        rec.add(channel, name, False, f"响应缺字段 {missing}", elapsed)
        return
    first = results[0]
    if not first.get("url") or not first.get("title"):
        rec.add(channel, name, False, f"首条结果缺 url/title：{first}", elapsed)
        return
    dated = sum(1 for item in results if item.get("published_date"))
    detail = f"{len(results)} 条结果（{dated} 条带日期），首条 {str(first.get('title'))[:26]}"
    rec.add(channel, name, True, detail, elapsed)


# ---------------------------------------------------------------- 通道 A：MCP stdio（SDK 客户端）
async def check_stdio(rec: Recorder, *, general_query: str, news_query: str, fetch_url: str) -> None:
    """用官方 MCP SDK 的 stdio 客户端跑完整握手 + 工具调用（等价于本地桌面客户端）。"""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "utf8_search", "stdio"],
        env=_child_env(),
        cwd=str(REPO_ROOT),
    )

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            started = time.perf_counter()
            try:
                init = await asyncio.wait_for(session.initialize(), timeout=60)
            except Exception as exc:  # noqa: BLE001 - 握手失败后面都做不了
                rec.fail("stdio", "initialize", exc, time.perf_counter() - started)
                return
            info = _get(init, "server_info", "serverInfo", default=None)
            name = getattr(info, "name", "?") if info else "?"
            version = getattr(info, "version", "?") if info else "?"
            protocol = _get(init, "protocol_version", "protocolVersion", default="?")
            rec.add(
                "stdio",
                "initialize",
                name == "utf8-search",
                f"{name} {version}，协议 {protocol}",
                time.perf_counter() - started,
            )

            started = time.perf_counter()
            try:
                listed = await asyncio.wait_for(session.list_tools(), timeout=30)
                tools = list(_get(listed, "tools", default=[]) or [])
            except Exception as exc:  # noqa: BLE001
                rec.fail("stdio", "tools/list", exc, time.perf_counter() - started)
                tools = []
            if tools:
                _verify_tool_schemas(rec, "stdio", tools, time.perf_counter() - started)

            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool("web_search", {"query": general_query, "max_results": 5}),
                    timeout=90,
                )
                error = _tool_error(result)
                if error:
                    rec.add("stdio", "call web_search(basic)", False, error, time.perf_counter() - started)
                else:
                    _verify_search_payload(
                        rec, "stdio", "call web_search(basic)", _tool_payload(result), time.perf_counter() - started
                    )
            except Exception as exc:  # noqa: BLE001
                rec.fail("stdio", "call web_search(basic)", exc, time.perf_counter() - started)

            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool(
                        "web_search",
                        {"query": news_query, "topic": "news", "time_range": "week", "max_results": 5},
                    ),
                    timeout=90,
                )
                error = _tool_error(result)
                if error:
                    rec.add("stdio", "call web_search(news)", False, error, time.perf_counter() - started)
                else:
                    _verify_search_payload(
                        rec, "stdio", "call web_search(news)", _tool_payload(result), time.perf_counter() - started
                    )
            except Exception as exc:  # noqa: BLE001
                rec.fail("stdio", "call web_search(news)", exc, time.perf_counter() - started)

            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool("web_fetch", {"urls": [fetch_url], "max_chars": 2000}), timeout=90
                )
                error = _tool_error(result)
                payload = _tool_payload(result)
                if error:
                    rec.add("stdio", "call web_fetch", False, error, time.perf_counter() - started)
                elif payload.get("results"):
                    chars = int(payload["results"][0].get("chars") or 0)
                    rec.add(
                        "stdio", "call web_fetch", chars > 0, f"{fetch_url} 抽取 {chars} 字符", time.perf_counter() - started
                    )
                else:
                    rec.add(
                        "stdio",
                        "call web_fetch",
                        False,
                        f"未返回正文：{json.dumps(payload, ensure_ascii=False)[:160]}",
                        time.perf_counter() - started,
                    )
            except Exception as exc:  # noqa: BLE001
                rec.fail("stdio", "call web_fetch", exc, time.perf_counter() - started)


# ---------------------------------------------------------------- 通道 B：stdio 原始帧（协议纯净度）
async def check_stdio_raw(rec: Recorder, *, timeout: float = 45.0) -> None:
    """绕过 SDK 直接读写子进程管道：stdout 必须只有合法 JSON-RPC。

    这是 stdio 客户端「进程起来了、工具却调不通」的头号原因：服务端任何一行 print()
    或第三方库写到 stdout 的日志都会破坏协议帧。SDK 客户端遇到这种帧会直接报解析错误，
    所以这里显式断言每一行。
    """
    from mcp import types

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "utf8_search",
        "stdio",
        cwd=str(REPO_ROOT),
        env=_child_env(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    lines: list[str] = []
    started = time.perf_counter()
    try:
        assert process.stdin is not None and process.stdout is not None

        async def send(payload: dict[str, Any]) -> None:
            process.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
            await process.stdin.drain()

        async def read_until(request_id: int, *, deadline: float) -> dict[str, Any]:
            """读到指定 id 的响应为止；途中的每一行都必须能解析成 JSON-RPC。"""
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"等待 id={request_id} 的响应超时")
                raw = await asyncio.wait_for(process.stdout.readline(), timeout=remaining)
                if not raw:
                    raise RuntimeError("服务端 stdout 提前关闭")
                text = raw.decode("utf-8", "replace").strip()
                if not text:
                    continue
                lines.append(text)
                payload = json.loads(text)  # 解析失败即抛异常 → 被记为该检查失败
                if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
                    raise RuntimeError(f"stdout 出现非 JSON-RPC 输出：{text[:120]}")
                if payload.get("id") == request_id:
                    return payload

        deadline = time.monotonic() + timeout
        await send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": types.LATEST_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "utf8-search-selfcheck", "version": "0.1"},
                },
            }
        )
        init = await read_until(1, deadline=deadline)
        server_name = ((init.get("result") or {}).get("serverInfo") or {}).get("name")
        await send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listed = await read_until(2, deadline=deadline)
        tool_names = sorted(tool.get("name", "") for tool in ((listed.get("result") or {}).get("tools") or []))

        problems = []
        if server_name != "utf8-search":
            problems.append(f"serverInfo.name={server_name}")
        if tool_names != ["web_fetch", "web_search"]:
            problems.append(f"tools={tool_names}")
        bad = [text for text in lines if "jsonrpc" not in text]
        if bad:
            problems.append(f"stdout 混入非协议输出 {bad[:2]}")
        detail = f"stdout {len(lines)} 行全为合法 JSON-RPC，工具 {tool_names}"
        rec.add("stdio-raw", "handshake", not problems, "；".join(problems) or detail, time.perf_counter() - started)
    except Exception as exc:  # noqa: BLE001
        rec.fail("stdio-raw", "handshake", exc, time.perf_counter() - started)
    finally:
        if process.stdin is not None:
            process.stdin.close()
        if process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except (asyncio.TimeoutError, TimeoutError):
                process.kill()
                await process.wait()


# ---------------------------------------------------------------- 通道 C：MCP Streamable HTTP
async def _mcp_http_session(rec: Recorder, *, base_url: str, api_key: str, general_query: str) -> None:
    """用官方 SDK 的 Streamable HTTP 客户端连 /mcp，跑握手 + 工具发现 + 工具调用。"""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    client = create_mcp_http_client(headers={"X-API-Key": api_key})
    url = f"{base_url}/mcp"
    async with streamable_http_client(url, http_client=client) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            started = time.perf_counter()
            try:
                init = await asyncio.wait_for(session.initialize(), timeout=60)
            except Exception as exc:  # noqa: BLE001
                rec.fail("http-mcp", "initialize", exc, time.perf_counter() - started)
                return
            info = _get(init, "server_info", "serverInfo", default=None)
            name = getattr(info, "name", "?") if info else "?"
            rec.add(
                "http-mcp",
                "initialize",
                name == "utf8-search",
                f"{name}，协议 {_get(init, 'protocol_version', 'protocolVersion', default='?')}",
                time.perf_counter() - started,
            )

            started = time.perf_counter()
            try:
                listed = await asyncio.wait_for(session.list_tools(), timeout=30)
                tools = list(_get(listed, "tools", default=[]) or [])
            except Exception as exc:  # noqa: BLE001
                rec.fail("http-mcp", "tools/list", exc, time.perf_counter() - started)
                tools = []
            if tools:
                _verify_tool_schemas(rec, "http-mcp", tools, time.perf_counter() - started)

            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool("web_search", {"query": general_query, "max_results": 3}), timeout=90
                )
                error = _tool_error(result)
                if error:
                    rec.add("http-mcp", "call web_search", False, error, time.perf_counter() - started)
                else:
                    _verify_search_payload(
                        rec, "http-mcp", "call web_search", _tool_payload(result), time.perf_counter() - started
                    )
            except Exception as exc:  # noqa: BLE001
                rec.fail("http-mcp", "call web_search", exc, time.perf_counter() - started)


class _Stopwatch:
    """给单条检查计时（报告里要展示每一项的耗时）。"""

    def __enter__(self) -> "_Stopwatch":
        self.started = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> bool:
        self.elapsed = self.lap()
        return False

    def lap(self) -> float:
        """从进入计时点到现在的秒数（block 内、block 后都可调用）。"""
        return time.perf_counter() - self.started


# ---------------------------------------------------------------- 通道 C：MCP Streamable HTTP（鉴权 / 防重绑定）
# 用一个最小的 initialize 请求做「证伪」：无 Key 应 401、伪造 Host 应 421。
# 请求体在这里只起「非空 JSON-RPC」的作用：这两种情况在协议解析之前就被拦掉了。
_MCP_INIT_BODY: dict[str, Any] = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2026-07-28",
        "capabilities": {},
        "clientInfo": {"name": "utf8-search-selfcheck", "version": "0.1"},
    },
}
_MCP_HEADERS = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}


async def check_http_mcp(
    rec: Recorder, *, base_url: str, api_key: str, general_query: str, timeout: float = 90.0
) -> None:
    """通道 C：先证伪（鉴权 + Host 白名单），再用官方 SDK 客户端跑通全流程。"""
    httpx = _import_httpx()

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0, trust_env=False) as client:
        cases: list[tuple[str, dict[str, str], int]] = [
            ("无 Key 应 401", {}, 401),
            ("错误 Key 应 401", {"X-API-Key": "definitely-wrong-key"}, 401),
            ("伪造 Host 应 421", {"X-API-Key": api_key, "Host": "rebind.example"}, 421),
        ]
        for name, extra, expected in cases:
            with _Stopwatch() as sw:
                try:
                    response = await client.post("/mcp", json=_MCP_INIT_BODY, headers={**_MCP_HEADERS, **extra})
                    text = response.text.strip().replace("\n", " ")[:100]
                except Exception as exc:  # noqa: BLE001
                    rec.fail("http-mcp", name, exc, sw.lap())
                    continue
                rec.add(
                    "http-mcp",
                    name,
                    response.status_code == expected,
                    f"HTTP {response.status_code}（期望 {expected}）{text}",
                    sw.lap(),
                )

    # 正常路径：SDK 客户端的握手 / 工具发现 / 工具调用
    try:
        await _mcp_http_session(rec, base_url=base_url, api_key=api_key, general_query=general_query)
    except Exception as exc:  # noqa: BLE001 - 连接层异常（SDK 内部抛错）在这里兜住
        rec.fail("http-mcp", "SDK 会话", exc)


# ---------------------------------------------------------------- 通道 D：REST / Tavily 兼容
def _host_matches(url: str, domain: str) -> bool:
    """URL 的主机是否属于给定域名（含子域）。"""
    from urllib.parse import urlsplit

    host = (urlsplit(url).hostname or "").lower()
    domain = domain.lower().lstrip(".")
    return host == domain or host.endswith("." + domain)


def _domain_of(url: str) -> str:
    """取结果域名（复用服务端实现，保证自检与服务端的过滤口径一致）。"""
    from utf8_search.rank.fusion import domain_of

    return domain_of(url)


def _age_days(published: str | None) -> float | None:
    """发布日期距今天数；复用服务端同一套解析逻辑，避免自检与实现脱节。"""
    from utf8_search.rank.recency import age_days

    return age_days(published)


def _expect_status(expected: int) -> Callable[[int, dict[str, Any]], tuple[bool, str]]:
    """构造一个「只看状态码」的判定函数。"""

    def verdict(status: int, payload: dict[str, Any]) -> tuple[bool, str]:
        detail = f"HTTP {status}"
        if status != expected:
            detail += f"（期望 {expected}）：{json.dumps(payload, ensure_ascii=False)[:120]}"
        return status == expected, detail

    return verdict


async def check_rest(
    rec: Recorder,
    *,
    base_url: str,
    api_key: str,
    general_query: str,
    news_query: str,
    fetch_url: str,
    timeout: float = 120.0,
) -> None:
    """通道 D：Tavily 兼容 REST —— 鉴权三种传法、参数映射、域名过滤、抽取、正文附带。"""
    httpx = _import_httpx()

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, trust_env=False) as client:

        async def probe(
            name: str,
            *,
            path: str,
            body: dict[str, Any],
            headers: dict[str, str],
            verdict: Callable[[int, dict[str, Any]], tuple[bool, str]] | None = None,
        ) -> None:
            """发一次搜索请求：默认校验结果结构，给了 verdict 就按 verdict 判定。"""
            with _Stopwatch() as sw:
                try:
                    response = await client.post(path, json=body, headers=headers)
                    payload = response.json() if response.content else {}
                except Exception as exc:  # noqa: BLE001
                    rec.fail("rest", name, exc, sw.lap())
                    return
                if not isinstance(payload, dict):
                    payload = {"raw": payload}
                if verdict is not None:
                    ok, detail = verdict(response.status_code, payload)
                    rec.add("rest", name, ok, detail, sw.lap())
                elif response.status_code != 200:
                    rec.add(
                        "rest",
                        name,
                        False,
                        f"HTTP {response.status_code}：{json.dumps(payload, ensure_ascii=False)[:140]}",
                        sw.lap(),
                    )
                else:
                    _verify_search_payload(rec, "rest", name, payload, sw.lap())

        # 1) /health：顺便探测目标服务是否启用了鉴权（--base-url 复用外部实例时要按实际情况放宽断言）
        with _Stopwatch() as sw:
            try:
                response = await client.get("/health")
                payload = response.json() if response.status_code == 200 else {}
            except Exception as exc:  # noqa: BLE001 - 服务不可达，后面的检查都做不了
                rec.fail("rest", "GET /health", exc, sw.lap())
                return
            auth_on = bool(payload.get("auth_enabled"))
            alive = response.status_code == 200 and payload.get("status") in {"ok", "degraded"}
            rec.add(
                "rest",
                "GET /health",
                alive,
                f"HTTP {response.status_code}，status={payload.get('status')}，"
                f"SearXNG={payload.get('searxng')}，鉴权={'开' if auth_on else '关'}",
                sw.lap(),
            )
        key_headers = {"X-API-Key": api_key} if auth_on else {}

        # 2) 鉴权三种传法都必须放行（Tavily 生态三种都在用）
        if auth_on:
            await probe(
                "POST /v1/search（X-API-Key）",
                path="/v1/search",
                body={"query": general_query, "max_results": 3},
                headers={"X-API-Key": api_key},
            )
            await probe(
                "POST /v1/search（Bearer）",
                path="/v1/search",
                body={"query": general_query, "max_results": 3},
                headers={"Authorization": f"Bearer {api_key}"},
            )
            await probe(
                "POST /search（body.api_key）",
                path="/search",
                body={"query": general_query, "max_results": 3, "api_key": api_key},
                headers={},
            )
        else:
            for name in ("POST /v1/search（X-API-Key）", "POST /v1/search（Bearer）", "POST /search（body.api_key）"):
                rec.add("rest", name, True, "目标服务未启用鉴权，跳过", 0.0, skipped=True)

        # 3) 缺失 / 错误 Key 必须被拒
        if auth_on:
            await probe(
                "无 Key 应 401",
                path="/v1/search",
                body={"query": general_query, "max_results": 3},
                headers={},
                verdict=_expect_status(401),
            )
            await probe(
                "错误 Key 应 401",
                path="/v1/search",
                body={"query": general_query, "max_results": 3},
                headers={"X-API-Key": "definitely-wrong-key"},
                verdict=_expect_status(401),
            )
        else:
            for name in ("无 Key 应 401", "错误 Key 应 401"):
                rec.add("rest", name, True, "目标服务未启用鉴权（UTF8SEARCH_API_KEYS 为空），跳过", 0.0, skipped=True)

        # 4) Tavily 的 days -> 内部 time_range 映射：看可观测结果（带日期结果的新鲜度）
        with _Stopwatch() as sw:
            try:
                response = await client.post(
                    "/v1/search",
                    json={"query": news_query, "topic": "news", "days": 1, "max_results": 5},
                    headers=key_headers,
                )
                payload = response.json() if response.status_code == 200 else {}
                results = payload.get("results") or []
            except Exception as exc:  # noqa: BLE001
                rec.fail("rest", "days=1 → time_range=day", exc, sw.lap())
            else:
                ages = [age for age in (_age_days(item.get("published_date")) for item in results) if age is not None]
                if response.status_code != 200:
                    rec.add(
                        "rest",
                        "days=1 → time_range=day",
                        False,
                        f"HTTP {response.status_code}：{json.dumps(payload, ensure_ascii=False)[:140]}",
                        sw.lap(),
                    )
                elif not results:
                    rec.add("rest", "days=1 → time_range=day", False, "结果为空", sw.lap())
                elif not ages:
                    rec.add(
                        "rest",
                        "days=1 → time_range=day",
                        True,
                        f"已受理并返回 {len(results)} 条；上游未给日期，时效性无法量化"
                        "（映射逻辑由 tests/test_api.py::test_days_maps_to_time_range 覆盖）",
                        sw.lap(),
                        skipped=True,
                    )
                else:
                    worst = max(ages)
                    rec.add(
                        "rest",
                        "days=1 → time_range=day",
                        worst <= 3.0,
                        f"{len(ages)}/{len(results)} 条带日期，最旧 {worst:.1f} 天",
                        sw.lap(),
                    )

        # 5) include_domains 必须真的生效（越界结果说明过滤被绕过）
        async def check_include_domains() -> None:
            """用「基准搜索里确实有结果的域名」当白名单：固定域名可能恰好无结果，测不出过滤。"""
            with _Stopwatch() as sw:
                try:
                    baseline = await client.post(
                        "/v1/search", json={"query": general_query, "max_results": 5}, headers=key_headers
                    )
                    base_payload = baseline.json() if baseline.status_code == 200 else {}
                    base_results = base_payload.get("results") or []
                    if not base_results:
                        rec.add(
                            "rest",
                            "include_domains 生效",
                            True,
                            "基准搜索无结果，取不到白名单域名（不计失败）",
                            sw.lap(),
                            skipped=True,
                        )
                        return
                    domain = _domain_of(str(base_results[0].get("url") or ""))
                    response = await client.post(
                        "/v1/search",
                        json={"query": general_query, "max_results": 5, "include_domains": [domain]},
                        headers=key_headers,
                    )
                    payload = response.json() if response.status_code == 200 else {}
                except Exception as exc:  # noqa: BLE001
                    rec.fail("rest", "include_domains 生效", exc, sw.lap())
                    return
                results = payload.get("results") or []
                if response.status_code != 200:
                    rec.add("rest", "include_domains 生效", False, f"HTTP {response.status_code}", sw.lap())
                elif not results:
                    rec.add(
                        "rest",
                        "include_domains 生效",
                        False,
                        f"白名单 {domain} 过滤后无结果，但基准搜索里有该域名结果",
                        sw.lap(),
                    )
                else:
                    outside = [
                        item.get("url") for item in results if not _host_matches(str(item.get("url") or ""), domain)
                    ]
                    rec.add(
                        "rest",
                        "include_domains 生效",
                        not outside,
                        f"白名单 {domain}：{len(results)} 条结果全部命中"
                        if not outside
                        else f"越界结果 {outside[:2]}",
                        sw.lap(),
                    )

        await check_include_domains()

        # 6) /v1/extract：正文抽取（Tavily /extract 兼容）
        with _Stopwatch() as sw:
            try:
                response = await client.post(
                    "/v1/extract",
                    json={"urls": [fetch_url], "max_chars": 2000},
                    headers=key_headers,
                )
                payload = response.json() if response.status_code == 200 else {}
                items = payload.get("results") or []
            except Exception as exc:  # noqa: BLE001
                rec.fail("rest", "POST /v1/extract", exc, sw.lap())
            else:
                chars = int(items[0].get("chars") or 0) if items else 0
                body = str(items[0].get("raw_content") or "") if items else ""
                ok = response.status_code == 200 and chars > 0 and bool(body.strip())
                rec.add(
                    "rest",
                    "POST /v1/extract",
                    ok,
                    f"HTTP {response.status_code}，{fetch_url} → {chars} 字符"
                    if items
                    else f"HTTP {response.status_code}，无结果：{json.dumps(payload, ensure_ascii=False)[:140]}",
                    sw.lap(),
                )

        # 7) advanced + include_raw_content：正文只在深度模式附带（basic 不带，省 token）
        with _Stopwatch() as sw:
            try:
                response = await client.post(
                    "/v1/search",
                    json={
                        "query": general_query,
                        "max_results": 3,
                        "search_depth": "advanced",
                        "include_raw_content": True,
                    },
                    headers=key_headers,
                )
                payload = response.json() if response.status_code == 200 else {}
                results = payload.get("results") or []
            except Exception as exc:  # noqa: BLE001
                rec.fail("rest", "advanced + include_raw_content", exc, sw.lap())
            else:
                pages = int(payload.get("pages_read") or 0)
                with_body = [item for item in results if str(item.get("raw_content") or "").strip()]
                ok = response.status_code == 200 and pages > 0 and bool(with_body)
                rec.add(
                    "rest",
                    "advanced + include_raw_content",
                    ok,
                    f"HTTP {response.status_code}，读取 {pages} 页，{len(with_body)}/{len(results)} 条附带正文",
                    sw.lap(),
                )


# ---------------------------------------------------------------- 通道 E：限流
async def check_ratelimit(
    rec: Recorder, *, base_url: str, api_key: str, query: str, timeout: float = 90.0
) -> None:
    """通道 E：RPM=1 的实例连发两次 —— 第 1 次放行，第 2 次必须 429。"""
    httpx = _import_httpx()

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, trust_env=False) as client:
        headers = {"X-API-Key": api_key}
        body = {"query": query, "max_results": 3}

        with _Stopwatch() as sw:
            try:
                first = await client.post("/v1/search", json=body, headers=headers)
            except Exception as exc:  # noqa: BLE001
                rec.fail("ratelimit", "第 1 次请求放行", exc, sw.lap())
                return
            rec.add("ratelimit", "第 1 次请求放行", first.status_code == 200, f"HTTP {first.status_code}", sw.lap())

        with _Stopwatch() as sw:
            try:
                second = await client.post("/v1/search", json=body, headers=headers)
            except Exception as exc:  # noqa: BLE001
                rec.fail("ratelimit", "第 2 次请求被限流", exc, sw.lap())
                return
            retry_after = second.headers.get("retry-after")
            rec.add(
                "ratelimit",
                "第 2 次请求被限流",
                second.status_code == 429 and retry_after is not None,
                f"HTTP {second.status_code}，Retry-After={retry_after}",
                sw.lap(),
            )


# ---------------------------------------------------------------- 报告
MANUAL_CLIENTS: tuple[tuple[str, str], ...] = (
    ("Claude Desktop", "MCP stdio（claude_desktop_config.json）"),
    ("Codex", "MCP stdio（config.toml）；新版可用 Streamable HTTP"),
    ("Cursor", "MCP stdio 或 Streamable HTTP（/mcp）"),
    ("Cherry Studio", "MCP stdio 或 Streamable HTTP（/mcp）"),
    ("Dify", "Tavily 兼容 REST（自定义工具 / OpenAPI）"),
    ("n8n", "Tavily 兼容 REST（HTTP Request 节点）"),
    ("自研 Agent", "MCP stdio / Streamable HTTP / REST 任选"),
)


def render_report(rec: Recorder, args: argparse.Namespace, modes: list[str], servers: list[str]) -> str:
    """生成 Markdown 报告（含「人工联调清单」待回填表）。"""
    executed = rec.executed
    failed = rec.failed
    skipped = [check for check in rec.checks if check.skipped]
    now = datetime.now().astimezone()

    lines: list[str] = []
    lines.append("# M4-4.3 客户端联调自检报告")
    lines.append("")
    lines.append(f"- 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S %z')}")
    lines.append(f"- 运行环境：Python {sys.version.split()[0]} / {platform.platform()}")
    lines.append(f"- 仓库：`{REPO_ROOT}`")
    lines.append(f"- 覆盖通道：{', '.join(modes)}")
    lines.append(f"- 服务实例：{'；'.join(servers) if servers else '（本次未启动 HTTP 实例）'}")
    lines.append(f"- 查询：`{args.query}`；新闻查询：`{args.news_query}`；抽取 URL：`{args.fetch_url}`")
    verdict = "全部通过" if not failed else f"{len(failed)} 项失败"
    lines.append(f"- 结论：**{verdict}**（执行 {len(executed)} 项，跳过 {len(skipped)} 项）")

    lines.append("")
    lines.append("## 1. 汇总")
    lines.append("")
    lines.append("| 通道 | 执行 | 通过 | 失败 | 跳过 | 耗时合计 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for channel in [name for name in ALL_CHANNELS if any(check.channel == name for check in rec.checks)]:
        rows = [check for check in rec.checks if check.channel == channel]
        ok = sum(1 for check in rows if check.passed and not check.skipped)
        bad = sum(1 for check in rows if not check.passed and not check.skipped)
        skip = sum(1 for check in rows if check.skipped)
        total = sum(check.elapsed for check in rows if not check.skipped)
        lines.append(f"| {channel} | {ok + bad} | {ok} | {bad} | {skip} | {total:.1f}s |")

    lines.append("")
    lines.append("## 2. 明细")
    lines.append("")
    lines.append("| # | 通道 | 检查项 | 结果 | 耗时 | 说明 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for index, check in enumerate(rec.checks, 1):
        mark = "跳过" if check.skipped else ("通过" if check.passed else "**失败**")
        detail = check.detail.replace("|", "\\|")
        lines.append(f"| {index} | {check.channel} | {check.name} | {mark} | {check.elapsed:.2f}s | {detail} |")

    lines.append("")
    lines.append("## 3. 失败详情")
    lines.append("")
    if failed:
        for check in failed:
            lines.append(f"- `{check.channel}` / {check.name}：{check.detail}")
    else:
        lines.append("无。")

    lines.append("")
    lines.append("## 4. 人工联调清单（待回填）")
    lines.append("")
    lines.append("自动化只能覆盖协议、参数、鉴权、限流；**各客户端自身的配置界面与文件名**必须在客户端里点一次。")
    lines.append("步骤见 `docs/03-客户端接入指南.md`；跑通后在「跑通」列填 ✅，失败写进备注并回修文档或代码。")
    lines.append("")
    lines.append("| 客户端 | 接入方式 | 跑通 | 备注 |")
    lines.append("| --- | --- | --- | --- |")
    for client, channel in MANUAL_CLIENTS:
        lines.append(f"| {client} | {channel} | ☐ | |")

    lines.append("")
    lines.append("## 5. 复现命令")
    lines.append("")
    lines.append("```powershell")
    out = args.out or "data\\selfcheck43.md"
    lines.append(f".\\.venv\\Scripts\\python.exe -u scripts\\mcp_selfcheck.py --mode {args.mode} --out {out}")
    lines.append("# 复用已启动的服务（跳过临时实例）：")
    lines.append(
        ".\\.venv\\Scripts\\python.exe -u scripts\\mcp_selfcheck.py --mode rest,http"
        " --base-url http://127.0.0.1:8000 --api-key <你的 Key>"
    )
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- 入口
def resolve_modes(raw: str) -> list[str]:
    """把 --mode 解析成通道列表（支持别名与 all）。"""
    aliases = {
        "all": "all",
        "stdio": "stdio",
        "stdio-raw": "stdio-raw",
        "stdio_raw": "stdio-raw",
        "http": "http-mcp",
        "http-mcp": "http-mcp",
        "http_mcp": "http-mcp",
        "rest": "rest",
        "ratelimit": "ratelimit",
        "rate-limit": "ratelimit",
    }
    modes: list[str] = []
    for token in raw.split(","):
        key = token.strip().lower()
        if not key:
            continue
        if key not in aliases:
            raise SystemExit(f"未知通道 {token.strip()!r}；可选：all, {', '.join(ALL_CHANNELS)}")
        value = aliases[key]
        if value == "all":
            modes = list(ALL_CHANNELS)
        elif value not in modes:
            modes.append(value)
    return modes or list(ALL_CHANNELS)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="mcp_selfcheck.py",
        description="utf8-search 客户端联调自检（M4-4.3）：把 stdio / Streamable HTTP / REST 三条通道端到端跑一遍。",
        epilog=f"--mode 可选：all, {', '.join(ALL_CHANNELS)}；http 是 http-mcp 的别名。",
    )
    parser.add_argument("--mode", default="all", help="逗号分隔的通道；all 表示全部（默认）")
    parser.add_argument(
        "--base-url",
        default=None,
        help="复用已启动的 HTTP 服务（http-mcp / rest 通道用），跳过自动启动临时实例",
    )
    parser.add_argument("--api-key", default=SELFCHECK_KEY, help=f"访问 Key；默认 {SELFCHECK_KEY}")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="通用查询")
    parser.add_argument("--news-query", default=DEFAULT_NEWS_QUERY, help="新闻 / 时效查询")
    parser.add_argument("--fetch-url", default=EXTRACT_URL, help="抽取自检用 URL")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP 请求超时（秒）")
    parser.add_argument("--out", default=None, help="报告输出路径（Markdown）；不填则只打印到终端")
    return parser.parse_args(argv)


async def _run_http_channels(
    rec: Recorder, modes: list[str], *, base_url: str, api_key: str, args: argparse.Namespace
) -> None:
    """跑 http-mcp / rest 两个通道（共用同一个 HTTP 服务实例）。"""
    if "http-mcp" in modes:
        print("- 通道 C：MCP Streamable HTTP（/mcp）")
        await check_http_mcp(
            rec, base_url=base_url, api_key=api_key, general_query=args.query, timeout=args.timeout
        )
    if "rest" in modes:
        print("- 通道 D：REST / Tavily 兼容")
        await check_rest(
            rec,
            base_url=base_url,
            api_key=api_key,
            general_query=args.query,
            news_query=args.news_query,
            fetch_url=args.fetch_url,
            timeout=args.timeout,
        )


async def run(args: argparse.Namespace) -> int:
    """按通道顺序跑自检，返回退出码（0 = 无失败项）。"""
    modes = resolve_modes(args.mode)
    rec = Recorder()
    servers: list[str] = []
    print(f"utf8-search 客户端自检（M4-4.3）｜通道：{', '.join(modes)}")

    if "stdio" in modes:
        print("- 通道 A：MCP stdio（SDK 客户端）")
        try:
            await check_stdio(
                rec, general_query=args.query, news_query=args.news_query, fetch_url=args.fetch_url
            )
        except Exception as exc:  # noqa: BLE001 - 子进程/传输层异常在这里兜住
            rec.fail("stdio", "通道", exc)

    if "stdio-raw" in modes:
        print("- 通道 B：stdio 原始帧（协议纯净度）")
        await check_stdio_raw(rec, timeout=45.0)

    if {"http-mcp", "rest"} & set(modes):
        if args.base_url:
            base_url = args.base_url.rstrip("/")
            print(f"- 通道 C/D：复用已启动的服务 {base_url}")
            servers.append(f"{base_url}（复用外部实例）")
            await _run_http_channels(rec, modes, base_url=base_url, api_key=args.api_key, args=args)
        else:
            print("- 通道 C/D：启动临时 HTTP 实例")
            server = LocalServer(api_keys=args.api_key, note="http-mcp/rest 自检实例")
            try:
                await server.start()
            except Exception as exc:  # noqa: BLE001 - 起不来就逐个通道记失败
                for channel in ("http-mcp", "rest"):
                    if channel in modes:
                        rec.fail(channel, "启动临时实例", exc)
            else:
                servers.append(f"{server.base_url}（临时实例，API Key={args.api_key}，不限流）")
                await _run_http_channels(rec, modes, base_url=server.base_url, api_key=args.api_key, args=args)
            finally:
                await server.stop()

    if "ratelimit" in modes:
        print("- 通道 E：限流（独立实例 RPM=1）")
        server = LocalServer(rate_limit_rpm=1, note="限流自检实例")
        try:
            await server.start()
        except Exception as exc:  # noqa: BLE001
            rec.fail("ratelimit", "启动临时实例", exc)
        else:
            servers.append(f"{server.base_url}（临时实例，API Key={args.api_key}，RPM=1）")
            await check_ratelimit(
                rec, base_url=server.base_url, api_key=args.api_key, query=args.query, timeout=args.timeout
            )
        finally:
            await server.stop()

    report = render_report(rec, args, modes, servers)
    failed = rec.failed
    print(f"\n共执行 {len(rec.executed)} 项检查：通过 {len(rec.executed) - len(failed)}，失败 {len(failed)}")
    for check in failed:
        print(f"  FAIL  {check.channel} / {check.name}：{check.detail}")
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8", newline="\n")
        print(f"报告已写入：{out_path}")
    else:
        print("\n" + report)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    args = parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())