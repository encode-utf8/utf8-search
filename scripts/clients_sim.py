"""各客户端仿真联调：按 docs/03 §2 表格里的每一行客户端，各造一份「该客户端真实存储格式」的配置并真的连一次。

与 scripts/mcp_selfcheck.py 的分工
--------------------------------
- `mcp_selfcheck.py` 按**通道**做协议级自检（stdio / Streamable HTTP / REST / 限流），回答「服务端本身对不对」；
- 本脚本按**客户端**做仿真，回答「照 docs/03 抄一份配置给某个客户端，能不能用」：
  先用各客户端**自己的配置格式**生成配置文本（Claude/Cursor 的 JSON、Codex 的 TOML、
  Cherry Studio 的图形界面字段、Dify/n8n 的 HTTP 请求），再把配置**解析回来**、按该客户端的连接方式连一次。

覆盖（对应 docs/03 §2 表格的每一行）
----------------------------------
Claude Desktop(stdio) / Codex(stdio) / Cursor(stdio、HTTP) / Cherry Studio(stdio、HTTP) /
Dify(REST) / n8n(REST) / 自研 Agent(MCP HTTP、REST) / 已有 Tavily 代码(REST，换 base_url)

不覆盖的部分（如实说明）：客户端界面里「把配置粘进去」的动作本身无法自动化；但配置文本与连接方式
已被本脚本验证，粘贴只剩机械操作。

用法
----
    python scripts/clients_sim.py --base-url http://127.0.0.1:8000 --api-key <Key>
    python scripts/clients_sim.py --base-url http://127.0.0.1:8000 --api-key <Key> --out docs/reports/<日期>-clients-sim.md
    python scripts/clients_sim.py --only Cursor        # 只跑名字里含 Cursor 的客户端
    python scripts/clients_sim.py --no-search          # 只握手不真搜（省上游配额）

退出码：0 = 全部通过（跳过项不计）；1 = 有失败项。
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_QUERY = "2026年 新能源汽车 补贴政策"
SEARXNG_URL = "http://127.0.0.1:8888"
CN_TZ = timezone(timedelta(hours=8))

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


# ---------------------------------------------------------------- 结果记录
@dataclass
class Check:
    """一条仿真结果。"""

    client: str
    step: str
    status: str
    detail: str
    seconds: float = 0.0


@dataclass
class Recorder:
    """收集所有客户端的检查结果（与 mcp_selfcheck 的报告口径保持一致：PASS/FAIL/SKIP）。"""

    checks: list[Check] = field(default_factory=list)

    def add(self, client: str, step: str, ok: bool, detail: str, seconds: float = 0.0, skip: bool = False) -> None:
        status = SKIP if skip else (PASS if ok else FAIL)
        self.checks.append(Check(client, step, status, detail, seconds))

    def fail(self, client: str, step: str, exc: BaseException, seconds: float = 0.0) -> None:
        self.add(client, step, False, f"{type(exc).__name__}: {exc}", seconds)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if c.status == FAIL]

    @property
    def executed(self) -> list[Check]:
        return [c for c in self.checks if c.status != SKIP]

    def client_names(self) -> list[str]:
        """按出现顺序去重的客户端名。"""
        names: list[str] = []
        for c in self.checks:
            if c.client not in names:
                names.append(c.client)
        return names

# ---------------------------------------------------------------- 通用小工具
def _stdio_argv() -> list[str]:
    """本仓库 venv 里的入口（Linux 是 bin/，Windows 是 Scripts\\*.exe）。"""
    win = REPO_ROOT / ".venv" / "Scripts" / "utf8-search.exe"
    nix = REPO_ROOT / ".venv" / "bin" / "utf8-search"
    if os.name == "nt" and win.exists():
        return [str(win)]
    if nix.exists():
        return [str(nix)]
    return [sys.executable, "-m", "utf8_search"]


def _stdio_env_block() -> dict[str, str]:
    """stdio 客户端配置里那份 env（与 docs/03 §3.1 一致）。"""
    return {
        "UTF8SEARCH_SEARXNG_URL": SEARXNG_URL,
        "UTF8SEARCH_TRUST_ENV": "false",
        "UTF8SEARCH_LOG_LEVEL": "WARNING",
    }


def _child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {**os.environ, "UTF8SEARCH_LOG_LEVEL": "WARNING"}
    env.update(extra or {})
    return env


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    """兼容 snake_case / camelCase 两种属性写法（MCP SDK 版本间有过改动）。"""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
        if isinstance(obj, dict) and name in obj:
            return obj[name]
    return default


def _payload(result: Any) -> dict[str, Any]:
    """把工具调用结果转成 dict：优先结构化内容，其次解析文本块里的 JSON。"""
    structured = _get(result, "structured_content", "structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in _get(result, "content", default=[]) or []:
        text = getattr(block, "text", None)
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            continue
    return {}


def _search_problems(payload: dict[str, Any], *, tavily: bool = False) -> list[str]:
    """搜索响应的基本契约检查，返回问题列表（空 = 通过）。"""
    problems: list[str] = []
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        problems.append("results 为空")
    else:
        for idx, item in enumerate(results[:3], 1):
            if not item.get("url"):
                problems.append(f"第 {idx} 条缺 url")
            if not item.get("title"):
                problems.append(f"第 {idx} 条缺 title")
    if not isinstance(payload.get("response_time"), (int, float)):
        problems.append("response_time 不是数字")
    if tavily:
        for name in ("query", "request_id", "auto_parameters", "usage"):
            if name not in payload:
                problems.append(f"缺 Tavily 字段 {name}")
    return problems


def _summarize(payload: dict[str, Any], limit: int = 3) -> str:
    """给报告用的一句话摘要；顺带标出缓存状态（复测口径要求绕缓存，冷查询才有说服力）。"""
    results = payload.get("results") or []
    cached = payload.get("cached")
    tag = "（缓存命中）" if cached is True else ("（冷查询）" if cached is False else "")
    head = "；".join(
        f"[{item.get('engine')}] {(item.get('title') or '')[:28]}" for item in results[:limit]
    )
    return f"{tag}{len(results)} 条结果（{payload.get('response_time')}s）{head}"

# ---------------------------------------------------------------- 各客户端的配置形态 + 解析
def render_claude_json(argv: list[str]) -> str:
    """Claude Desktop 的 claude_desktop_config.json（Cursor 的 mcp.json 结构相同）。"""
    cfg = {
        "mcpServers": {
            "utf8-search": {"command": argv[0], "args": argv[1:], "env": _stdio_env_block()}
        }
    }
    return json.dumps(cfg, ensure_ascii=False, indent=2)


def render_cursor_json(argv: list[str]) -> str:
    """Cursor 的 .cursor/mcp.json（docs §3.3 的示例只给 UTF8SEARCH_TRUST_ENV）。"""
    cfg = {
        "mcpServers": {
            "utf8-search": {
                "command": argv[0],
                "args": argv[1:],
                "env": {"UTF8SEARCH_TRUST_ENV": "false"},
            }
        }
    }
    return json.dumps(cfg, ensure_ascii=False, indent=2)


def parse_json_mcp(text: str) -> tuple[list[str], dict[str, str]]:
    """解析 JSON 形态的 stdio 客户端配置 → (argv, env)。"""
    entry = json.loads(text)["mcpServers"]["utf8-search"]
    if "url" in entry:
        raise ValueError("这是 HTTP 形态的配置（含 url），不能当 stdio 用")
    return [entry["command"], *list(entry.get("args") or [])], dict(entry.get("env") or {})


def render_cherry_stdio_fields(argv: list[str]) -> dict[str, str]:
    """Cherry Studio「设置 → MCP 服务器 → 添加」里逐字段填的内容（stdio）。"""
    return {
        "名称": "utf8-search",
        "类型": "stdio",
        "命令": argv[0],
        "参数": " ".join(argv[1:]),
        "环境变量": "UTF8SEARCH_TRUST_ENV=false",
    }


def parse_cherry_stdio_fields(fields: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """图形界面字段 → (argv, env)；参数按空格拆分，环境变量按 K=V 解析。"""
    argv = [fields["命令"]]
    if fields.get("参数", "").strip():
        argv.extend(fields["参数"].split())
    env: dict[str, str] = {}
    for chunk in fields.get("环境变量", "").split(","):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            env[key.strip()] = value.strip()
    return argv, env


def render_codex_toml(argv: list[str]) -> str:
    """Codex 的 ~/.codex/config.toml（docs/03 §3.2 的模板，按当前平台给路径）。"""
    env_lines = "\n".join(f'{k} = "{v}"' for k, v in _stdio_env_block().items())
    return (
        "[mcp_servers.utf8-search]\n"
        'type = "stdio"\n'
        f"command = '{argv[0]}'\n"
        "startup_timeout_sec = 60\n"
        "\n"
        "[mcp_servers.utf8-search.env]\n"
        f"{env_lines}\n"
    )


_RE_TOML_SECTION = re.compile(r"^\[mcp_servers\.utf8-search(?:\.(?P<sub>[^\]]+))?\]\s*$")


def parse_codex_toml(text: str) -> tuple[list[str], dict[str, str], str]:
    """解析 Codex 的 TOML 配置 → (argv, env, 用的解析器名)。

    Python 3.11+ 有 tomllib、3.10 上本仓库依赖了 tomli；两者都没有时退回正则——
    只解析 `[mcp_servers.utf8-search]` 这两段，够用且不引入新依赖。
    """
    parser = None
    how = "正则兜底"
    try:
        import tomllib as parser  # type: ignore[no-redef]
        how = "tomllib"
    except ModuleNotFoundError:
        try:
            import tomli as parser  # type: ignore[no-redef]
            how = "tomli"
        except ModuleNotFoundError:
            parser = None

    if parser is not None:
        data = parser.loads(text)
        entry = data["mcp_servers"]["utf8-search"]
        argv = [entry["command"], *list(entry.get("args") or [])]
        return argv, dict(entry.get("env") or {}), how

    # 正则兜底：只认 docs 里那两段结构化写法
    argv: list[str] = []
    env: dict[str, str] = {}
    section: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("["):
            match = _RE_TOML_SECTION.match(line)
            # "" 表示 `[mcp_servers.utf8-search]` 那一段（没有子表名），None 表示还没进段
            section = (match.group("sub") or "") if match else "__other__"
            continue
        if section is None or section == "__other__" or not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        value = value.strip().strip('"').strip("'")
        if section == "" and key == "command":
            argv = [value]
        elif section == "env":
            env[key] = value
    if not argv:
        raise ValueError("正则兜底没解析出 command（配置写法超出兜底范围）")
    return argv, env, how


def load_codex_entry(path: Path) -> tuple[list[str], dict[str, str], str]:
    """读真实存在的 Codex 配置；文件里没有 utf8-search 条目时抛 KeyError 由调用方记 SKIP。"""
    text = path.read_text(encoding="utf-8")
    return parse_codex_toml(text)


def render_cursor_http_json(base_url: str, api_key: str) -> str:
    """Cursor 的 Streamable HTTP 写法：mcp.json 里给 url + headers。"""
    cfg = {
        "mcpServers": {
            "utf8-search": {"url": f"{base_url.rstrip('/')}/mcp", "headers": {"X-API-Key": api_key}}
        }
    }
    return json.dumps(cfg, ensure_ascii=False, indent=2)


def parse_http_json(text: str) -> tuple[str, dict[str, str]]:
    entry = json.loads(text)["mcpServers"]["utf8-search"]
    if "url" not in entry:
        raise ValueError("这份配置没有 url，不是 HTTP 形态")
    return entry["url"], dict(entry.get("headers") or {})


def render_cherry_http_fields(base_url: str, api_key: str) -> dict[str, str]:
    """Cherry Studio 选「可流式传输的 HTTP」时填的字段。"""
    return {
        "名称": "utf8-search",
        "类型": "可流式传输的 HTTP",
        "URL": f"{base_url.rstrip('/')}/mcp",
        "请求头": f"X-API-Key: {api_key}",
    }


def parse_cherry_http_fields(fields: dict[str, str]) -> tuple[str, dict[str, str]]:
    headers: dict[str, str] = {}
    for chunk in fields.get("请求头", "").splitlines():
        if ":" in chunk:
            key, value = chunk.split(":", 1)
            headers[key.strip()] = value.strip()
    return fields["URL"], headers

# ---------------------------------------------------------------- stdio 执行器
async def run_stdio(
    rec: Recorder,
    client: str,
    argv: list[str],
    env: dict[str, str],
    *,
    query: str,
    max_results: int,
    do_search: bool,
    note: str = "",
) -> None:
    """按 stdio 客户端的方式起子进程，跑握手 / 工具发现 /（可选）一次真实搜索。"""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    entry = Path(argv[0])
    exists = entry.exists() if entry.is_absolute() else True
    detail = " ".join(str(a) for a in argv) + (f"（{note}）" if note else "")
    rec.add(client, "配置解析 → command", bool(exists), detail if exists else f"找不到可执行文件 {argv[0]}")
    if not exists:
        return

    params = StdioServerParameters(command=argv[0], args=argv[1:], env=_child_env(env), cwd=str(REPO_ROOT))
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            started = time.perf_counter()
            try:
                init = await asyncio.wait_for(session.initialize(), timeout=60)
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "initialize", exc, time.perf_counter() - started)
                return
            info = _get(init, "server_info", "serverInfo", default=None)
            name = getattr(info, "name", "?") if info else "?"
            rec.add(
                client,
                "initialize",
                name == "utf8-search",
                f"{name} {getattr(info, 'version', '?') if info else ''}".strip(),
                time.perf_counter() - started,
            )

            started = time.perf_counter()
            try:
                listed = await asyncio.wait_for(session.list_tools(), timeout=30)
                tools = [t.name for t in (_get(listed, "tools", default=[]) or [])]
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "tools/list", exc, time.perf_counter() - started)
                tools = []
            rec.add(
                client,
                "tools/list",
                {"web_search", "web_fetch"} <= set(tools),
                f"工具 {','.join(tools) or '（空）'}",
                time.perf_counter() - started,
            )

            if not do_search or not tools:
                return
            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool("web_search", {"query": query, "max_results": max_results}), timeout=120
                )
                payload = _payload(result)
                problems = _search_problems(payload)
                if _get(result, "is_error", "isError", default=False):
                    problems = problems or ["isError=True"]
                rec.add(
                    client,
                    "call web_search",
                    not problems,
                    _summarize(payload) if not problems else "；".join(problems),
                    time.perf_counter() - started,
                )
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "call web_search", exc, time.perf_counter() - started)


# ---------------------------------------------------------------- Streamable HTTP 执行器
async def run_http_mcp(
    rec: Recorder,
    client: str,
    url: str,
    headers: dict[str, str],
    *,
    query: str,
    max_results: int,
    do_search: bool,
    note: str = "",
) -> None:
    """按「MCP Streamable HTTP 客户端」的方式连 /mcp（Cursor / Cherry Studio / 自研 Agent 都走这条路）。"""
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    from mcp.shared._httpx_utils import create_mcp_http_client

    has_key = any(k.lower() in {"x-api-key", "authorization"} for k in headers)
    rec.add(
        client,
        "配置解析 → url+headers",
        has_key,
        f"{url}｜{' '.join(headers)}" + (f"（{note}）" if note else ""),
    )
    if not has_key:
        return

    http_client = create_mcp_http_client(headers=headers)
    async with streamable_http_client(url, http_client=http_client) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            started = time.perf_counter()
            try:
                init = await asyncio.wait_for(session.initialize(), timeout=60)
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "initialize", exc, time.perf_counter() - started)
                return
            info = _get(init, "server_info", "serverInfo", default=None)
            rec.add(
                client,
                "initialize",
                getattr(info, "name", None) == "utf8-search",
                f"{getattr(info, 'name', '?')}",
                time.perf_counter() - started,
            )

            started = time.perf_counter()
            try:
                listed = await asyncio.wait_for(session.list_tools(), timeout=30)
                tools = [t.name for t in (_get(listed, "tools", default=[]) or [])]
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "tools/list", exc, time.perf_counter() - started)
                tools = []
            rec.add(
                client,
                "tools/list",
                {"web_search", "web_fetch"} <= set(tools),
                f"工具 {','.join(tools) or '（空）'}",
                time.perf_counter() - started,
            )

            if not do_search or not tools:
                return
            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    session.call_tool("web_search", {"query": query, "max_results": max_results}), timeout=120
                )
                payload = _payload(result)
                problems = _search_problems(payload)
                rec.add(
                    client,
                    "call web_search",
                    not problems,
                    _summarize(payload) if not problems else "；".join(problems),
                    time.perf_counter() - started,
                )
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "call web_search", exc, time.perf_counter() - started)

# ---------------------------------------------------------------- REST 执行器
async def run_rest(
    rec: Recorder,
    client: str,
    base_url: str,
    api_key: str,
    *,
    header_style: str,
    body_key: bool,
    query: str,
    max_results: int,
    do_search: bool,
    tavily: bool = False,
    positive_control: bool = True,
    note: str = "",
) -> None:
    """按 REST 客户端的方式打 /v1/search（Dify 用 Bearer、n8n 用 X-API-Key、自研 Agent 可用 body 传 Key）。"""
    import httpx

    base = base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if header_style == "bearer":
        headers["Authorization"] = f"Bearer {api_key}"
    elif header_style == "x-api-key":
        headers["X-API-Key"] = api_key
    body: dict[str, Any] = {"query": query, "max_results": max_results, "search_depth": "basic"}
    if body_key:
        body["api_key"] = api_key

    rec.add(
        client,
        "配置解析 → 请求方式",
        True,
        f"POST {base}/v1/search｜{header_style or 'body api_key'}" + (f"（{note}）" if note else ""),
    )

    async with httpx.AsyncClient(base_url=base, timeout=120.0, trust_env=False) as http:
        # 证伪：不带 Key 必须 401（否则等于没鉴权）
        if positive_control:
            started = time.perf_counter()
            try:
                response = await http.post("/v1/search", json={"query": query, "max_results": 1})
                rec.add(
                    client,
                    "无 Key 应 401",
                    response.status_code == 401,
                    f"HTTP {response.status_code}",
                    time.perf_counter() - started,
                )
            except Exception as exc:  # noqa: BLE001
                rec.fail(client, "无 Key 应 401", exc, time.perf_counter() - started)

        if not do_search:
            return
        started = time.perf_counter()
        try:
            response = await http.post("/v1/search", json=body, headers=headers)
            if response.status_code != 200:
                rec.add(
                    client,
                    "call /v1/search",
                    False,
                    f"HTTP {response.status_code}：{response.text[:150]}",
                    time.perf_counter() - started,
                )
                return
            payload = response.json()
            problems = _search_problems(payload, tavily=tavily)
            rec.add(
                client,
                "call /v1/search",
                not problems,
                _summarize(payload) if not problems else "；".join(problems),
                time.perf_counter() - started,
            )
        except Exception as exc:  # noqa: BLE001
            rec.fail(client, "call /v1/search", exc, time.perf_counter() - started)


async def run_rest_extract(rec: Recorder, client: str, base_url: str, api_key: str, fetch_url: str) -> None:
    """Tavily 迁移场景额外验一下 /v1/extract（Dify/n8n 的「读正文」工具会用到）。"""
    import httpx

    async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=120.0, trust_env=False) as http:
        started = time.perf_counter()
        try:
            response = await http.post(
                "/v1/extract", json={"urls": [fetch_url], "api_key": api_key, "format": "markdown"}
            )
            if response.status_code != 200:
                rec.add(
                    client,
                    "call /v1/extract",
                    False,
                    f"HTTP {response.status_code}：{response.text[:150]}",
                    time.perf_counter() - started,
                )
                return
            payload = response.json()
            results = payload.get("results") or []
            first = (results[0].get("raw_content") or "") if results else ""
            rec.add(
                client,
                "call /v1/extract",
                bool(results) and bool(first),
                f"{len(results)} 条，首条正文 {len(first)} 字符",
                time.perf_counter() - started,
            )
        except Exception as exc:  # noqa: BLE001
            rec.fail(client, "call /v1/extract", exc, time.perf_counter() - started)

# ---------------------------------------------------------------- 报告
def render_report(rec: Recorder, args: argparse.Namespace) -> str:
    now = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M:%S %z")
    lines: list[str] = [
        "# 各客户端仿真联调报告",
        "",
        f"- 生成时间：{now}",
        f"- 目标服务：`{args.base_url}`（MCP `/mcp` + REST `/v1/search`、`/v1/extract`）",
        f"- 查询：`{args.query}`，max_results={args.max_results}"
        + ("；本轮 `--no-search`，只做握手与工具发现" if args.no_search else "")
        + (
            "；`--unique`：每个客户端尾部空格不同，均为冷查询"
            if args.unique
            else "；相同查询会命中服务端 600s 缓存（细节列里标「缓存命中」）"
        ),
        f"- 共执行 {len(rec.executed)} 项检查：通过 {len(rec.executed) - len(rec.failed)}，失败 {len(rec.failed)}",
        "",
        "## 1. 逐客户端结果",
        "",
    ]
    for client in rec.client_names():
        lines.append(f"### {client}")
        lines.append("")
        lines.append("| 步骤 | 结果 | 耗时 | 细节 |")
        lines.append("| --- | --- | --- | --- |")
        for c in [x for x in rec.checks if x.client == client]:
            lines.append(f"| {c.step} | {c.status} | {c.seconds:.2f}s | {c.detail.replace('|', '/')} |")
        lines.append("")
    lines += ["## 2. 结论", ""]
    if rec.failed:
        lines.append(f"**有 {len(rec.failed)} 项失败**：")
        lines.append("")
        for c in rec.failed:
            lines.append(f"- {c.client} / {c.step}：{c.detail}")
    else:
        lines.append("**全部通过**（`SKIP` 表示该项按条件跳过，不计入失败）。")
    lines += [
        "",
        "## 3. 覆盖与边界",
        "",
        "- 覆盖 docs/03 §2 表格里的每一行客户端：stdio 走 MCP SDK 起子进程，HTTP 走 Streamable HTTP 客户端，",
        "  REST 走原生 HTTP（与 Dify / n8n / 自研 Agent 的实际调用方式一致）。",
        "- **不覆盖**：客户端界面里「把配置粘进去 / 点保存」这个动作本身（无法自动化）；",
        "  但配置文本与连接方式已在上面逐项验证，粘贴只剩机械操作。",
        "- `/mcp` 的鉴权只认 `Authorization` 或 `X-API-Key` 头（服务端 `mcp_auth_middleware`），",
        "  **不支持 URL 里带 Key**：HTTP 传输的客户端必须能自定义请求头。",
        "",
        "## 4. 复现命令",
        "",
        "```bash",
        f".venv/bin/python scripts/clients_sim.py --base-url {args.base_url} --api-key <Key> --unique --out <报告路径>",
        "```",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- 主流程
def _selected(name: str, only: list[str]) -> bool:
    return not only or any(token.lower() in name.lower() for token in only)


async def run(args: argparse.Namespace) -> int:
    rec = Recorder()
    argv = list(args.stdio_command) if args.stdio_command else _stdio_argv()
    only = [x.strip() for x in (args.only or "").split(",") if x.strip()]
    base_url = args.base_url.rstrip("/")
    fetch_url = args.fetch_url

    # 服务端有 600s 查询缓存：`--unique` 时给每个客户端一条「尾部空格数不同」的查询，
    # 保证每条都是冷查询（尾空格不改变分词结果，是本项目既有的绕缓存手法）。
    counter = itertools.count(1)

    def next_query() -> str:
        return args.query if not args.unique else args.query + " " * next(counter)

    print(f"各客户端仿真联调｜目标 {base_url}｜stdio 入口 {' '.join(argv)}")
    print(
        f"查询：{args.query}｜max_results={args.max_results}｜真搜：{'否' if args.no_search else '是'}"
        f"｜绕缓存：{'是（每个客户端一条冷查询）' if args.unique else '否'}"
    )

    # ---- Claude Desktop（stdio，claude_desktop_config.json）
    if _selected("Claude Desktop", only):
        print("- Claude Desktop（stdio，claude_desktop_config.json）")
        try:
            parsed_argv, env = parse_json_mcp(render_claude_json(argv))
        except Exception as exc:  # noqa: BLE001
            rec.fail("Claude Desktop", "配置解析", exc)
        else:
            await run_stdio(rec, "Claude Desktop", parsed_argv, env, query=next_query(),
                            max_results=args.max_results, do_search=not args.no_search)

    # ---- Cursor（stdio，.cursor/mcp.json）
    if _selected("Cursor (stdio)", only):
        print("- Cursor（stdio，.cursor/mcp.json）")
        try:
            parsed_argv, env = parse_json_mcp(render_cursor_json(argv))
        except Exception as exc:  # noqa: BLE001
            rec.fail("Cursor (stdio)", "配置解析", exc)
        else:
            await run_stdio(rec, "Cursor (stdio)", parsed_argv, env, query=next_query(),
                            max_results=args.max_results, do_search=not args.no_search)

    # ---- Codex（stdio，~/.codex/config.toml）
    if _selected("Codex", only):
        print("- Codex（stdio，config.toml）")
        try:
            parsed_argv, env, how = parse_codex_toml(render_codex_toml(argv))
        except Exception as exc:  # noqa: BLE001
            rec.fail("Codex", "配置解析", exc)
        else:
            await run_stdio(rec, "Codex", parsed_argv, env, query=next_query(),
                            max_results=args.max_results, do_search=not args.no_search,
                            note=f"docs 模板，解析器 {how}")
        real = Path(os.path.expanduser(args.codex_config))
        if real.exists():
            try:
                parsed_argv, env, how = load_codex_entry(real)
            except KeyError:
                rec.add("Codex（真实配置）", "读取 config.toml", True,
                        f"{real} 里没有 `[mcp_servers.utf8-search]` 条目（该机器未配置）", skip=True)
            except Exception as exc:  # noqa: BLE001
                rec.fail("Codex（真实配置）", "读取 config.toml", exc)
            else:
                await run_stdio(rec, "Codex（真实配置）", parsed_argv, env, query=next_query(),
                                max_results=args.max_results, do_search=not args.no_search,
                                note=f"{real}，解析器 {how}")
        else:
            rec.add("Codex（真实配置）", "读取 config.toml", True, f"{real} 不存在", skip=True)

    # ---- Cherry Studio（stdio，图形界面字段）
    if _selected("Cherry Studio (stdio)", only):
        print("- Cherry Studio（stdio，图形界面字段）")
        try:
            parsed_argv, env = parse_cherry_stdio_fields(render_cherry_stdio_fields(argv))
        except Exception as exc:  # noqa: BLE001
            rec.fail("Cherry Studio (stdio)", "配置解析", exc)
        else:
            await run_stdio(rec, "Cherry Studio (stdio)", parsed_argv, env, query=next_query(),
                            max_results=args.max_results, do_search=not args.no_search)

    # ---- Cursor（Streamable HTTP）
    if _selected("Cursor (HTTP)", only):
        print("- Cursor（Streamable HTTP，mcp.json 的 url+headers）")
        try:
            url, headers = parse_http_json(render_cursor_http_json(base_url, args.api_key))
        except Exception as exc:  # noqa: BLE001
            rec.fail("Cursor (HTTP)", "配置解析", exc)
        else:
            await run_http_mcp(rec, "Cursor (HTTP)", url, headers, query=next_query(),
                               max_results=args.max_results, do_search=not args.no_search)

    # ---- Cherry Studio（Streamable HTTP，图形界面字段）
    if _selected("Cherry Studio (HTTP)", only):
        print("- Cherry Studio（Streamable HTTP，图形界面字段）")
        try:
            url, headers = parse_cherry_http_fields(render_cherry_http_fields(base_url, args.api_key))
        except Exception as exc:  # noqa: BLE001
            rec.fail("Cherry Studio (HTTP)", "配置解析", exc)
        else:
            await run_http_mcp(rec, "Cherry Studio (HTTP)", url, headers, query=next_query(),
                               max_results=args.max_results, do_search=not args.no_search)

    # ---- 自研 Agent（MCP HTTP，官方 Python SDK）
    if _selected("自研 Agent (MCP)", only):
        print("- 自研 Agent（MCP Streamable HTTP，官方 SDK）")
        await run_http_mcp(rec, "自研 Agent (MCP)", f"{base_url}/mcp", {"X-API-Key": args.api_key},
                           query=next_query(), max_results=args.max_results, do_search=not args.no_search,
                           note="等价 MCP SDK / 自研客户端")

    # ---- Dify（REST，自定义工具 + OpenAPI：Authorization: Bearer）
    if _selected("Dify", only):
        print("- Dify（REST，自定义工具 + OpenAPI）")
        await run_rest(rec, "Dify", base_url, args.api_key, header_style="bearer", body_key=False,
                       query=next_query(), max_results=args.max_results, do_search=not args.no_search)

    # ---- n8n（REST，HTTP Request 节点：X-API-Key）
    if _selected("n8n", only):
        print("- n8n（REST，HTTP Request 节点）")
        await run_rest(rec, "n8n", base_url, args.api_key, header_style="x-api-key", body_key=False,
                       query=next_query(), max_results=args.max_results, do_search=not args.no_search)

    # ---- 自研 Agent（REST，body 传 Key）
    if _selected("自研 Agent (REST)", only):
        print("- 自研 Agent（REST，body 传 Key）")
        await run_rest(rec, "自研 Agent (REST)", base_url, args.api_key, header_style="", body_key=True,
                       query=next_query(), max_results=args.max_results, do_search=not args.no_search,
                       note="api_key 放在请求体里（Tavily 兼容写法）")

    # ---- 已有 Tavily 代码（换 base_url）
    if _selected("已有 Tavily 代码", only):
        print("- 已有 Tavily 代码（只换 base_url）")
        await run_rest(rec, "已有 Tavily 代码", base_url, args.api_key, header_style="bearer", body_key=False,
                       query=next_query(), max_results=args.max_results, do_search=not args.no_search,
                       tavily=True, note="Tavily 字段断言 + /v1/extract")
        if not args.no_search:
            await run_rest_extract(rec, "已有 Tavily 代码", base_url, args.api_key, fetch_url)

    report = render_report(rec, args)
    failed = rec.failed
    print(f"\n共执行 {len(rec.executed)} 项检查：通过 {len(rec.executed) - len(failed)}，失败 {len(failed)}")
    for c in failed:
        print(f"  FAIL  {c.client} / {c.step}：{c.detail}")
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8", newline="\n")
        print(f"报告已写入：{out_path}")
    else:
        print("\n" + report)
    return 1 if failed else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        prog="clients_sim.py",
        description="各客户端仿真联调：按每个客户端自己的配置格式生成配置、解析回来、再连一次。",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"服务地址（默认 {DEFAULT_BASE_URL}）")
    parser.add_argument("--api-key", required=True, help="访问 Key（服务端开着鉴权时必须给）")
    parser.add_argument("--stdio-command", nargs="*", default=None,
                        help="stdio 客户端用的启动命令（默认取本仓库 .venv 里的 utf8-search）")
    parser.add_argument("--codex-config", default="~/.codex/config.toml",
                        help="Codex 的真实配置文件（默认 ~/.codex/config.toml，不存在则跳过）")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="搜索查询")
    parser.add_argument("--max-results", type=int, default=3, help="每次搜索取几条（默认 3）")
    parser.add_argument("--fetch-url", default="https://example.com", help="extract 自检用 URL")
    parser.add_argument("--only", default="", help="只跑名字里含这些词的客户端（逗号分隔）")
    parser.add_argument("--no-search", action="store_true", help="只做握手与工具发现，不真搜（省上游配额）")
    parser.add_argument("--unique", action="store_true",
                        help="每个客户端用一条「尾部空格不同」的查询绕开服务端缓存，保证都是冷查询")
    parser.add_argument("--out", default=None, help="报告输出路径（Markdown）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    args = parse_args(argv)
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
