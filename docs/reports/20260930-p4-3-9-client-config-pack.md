# 3-9 客户端「复制即用」配置包（2026-09-30）

> 目的：把 3-9（真实 GUI 客户端人工联调）的成本压到「复制 → 点一次」。
> 配套操作单：`docs/reports/manual-acceptance-checklist-20260928.md`（回填「跑通 ✅ / 失败备注」）。
> 本文件**不改任何代码/配置**，只是素材集合。

## 0. 公共信息（先看这一段）

**服务地址**

| 场景 | URL | 说明 |
| --- | --- | --- |
| 本机（服务器上直连） | `http://127.0.0.1:8000` | 只绑回环，不走 Caddy |
| 公网（走 Caddy + TLS） | `https://203.0.113.10.sslip.io` | 真证书（Let's Encrypt，2026-12-24 到期） |

**三种 Key 传法**（任选其一，`<KEY>` 取自服务器 `.env` 的 `UTF8SEARCH_API_KEYS`）

```bash
# ① Bearer（推荐，MCP 与 REST 通用）
Authorization: Bearer <KEY>
# ② 自定义头
X-API-Key: <KEY>
# ③ 请求体字段（仅 REST /search 支持；MCP 的 http 传输用前两种）
{"query": "...", "api_key": "<KEY>", "max_results": 5}
```

**MCP 两种接法**

| 接法 | 端点/命令 | Host 要求 |
| --- | --- | --- |
| Streamable HTTP | `https://203.0.113.10.sslip.io/mcp`（或 `http://127.0.0.1:8000/mcp`） | 公网**必须**带白名单 Host（`203.0.113.10:*` / `203.0.113.10.sslip.io`），否则 **421**；本机 127.0.0.1 不受限 |
| stdio | 命令 `utf8-search`、参数 `stdio`（需在本机装好该包） | 无（进程内通信，不需要 Host/Key） |

**degraded / degraded_reason 怎么读**（所有客户端都一样，**这不是错误**）

| 值 | 含义 | 调用方该怎么做 |
| --- | --- | --- |
| `degraded=false` | 正常 | 直接用 |
| `degraded=true` + `freshness_unverified` | 查询带了 `days`/`time_range`，但**拿不到足够「可信日期」结果**（中文新闻常见） | 结果可用，但**不要声称"这是最近 N 天的最新消息"**；可换数据源或放宽时间要求 |
| `upstream_overloaded` | 上游过载但仍有部分结果 | 结果可用，提示"可能不完整" |
| `fallback_low_relevance` | 兜底源结果**全部**未过相关性闸门 → 只返回少量/零结果 | 建议换查询词，不要当成"没搜到" |
| `spec_unverified` | 候选不足，只能保留**规格不完全匹配**的结果（如机型/版本号不符） | 涉及型号/版本时请人工核对 |

## 1. 通用「最小验证」脚本（REST，一条命令）

```bash
KEY=<你的 Key>
curl -sS -X POST https://203.0.113.10.sslip.io/v1/search \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"query":"美国 关税 最新政策","max_results":3,"search_depth":"basic","days":1}' \
  | python3 -m json.tool | head -40
```

**预期看到**：`query` / `results[]`（每项含 `title` `url` `content` `score` `published_date` `engine`）、
`response_time` / `request_id` / `engines_used` / `failed_engines`、以及 `degraded` 与 `degraded_reason`
（上面那条中文时效查询**预期** `degraded=true` + `freshness_unverified`，这是**如实告知**而不是故障）。

**MCP 最小验证**：调用工具 `web_search`，参数 `{"query":"美国 关税 最新政策","max_results":3,"topic":"news","time_range":"day"}`，
返回的 dict **与 REST 同字段**（含 `degraded` / `degraded_reason`）。

## 2. 七个客户端（复制即用）

### 2.1 Claude Desktop

**MCP（stdio，推荐）** —— `claude_desktop_config.json`：
```json
{"mcpServers": {"utf8-search": {"command": "utf8-search", "args": ["stdio"]}}}
```
**MCP（Streamable HTTP）**：
```json
{"mcpServers": {"utf8-search": {"type": "http", "url": "https://203.0.113.10.sslip.io/mcp",
  "headers": {"Authorization": "Bearer <KEY>"}}}}
```
**REST**：就是 §1 的 curl（Claude Desktop 本身不直连 REST，配置仅用于对照排查）。
**验证**：让 Claude 调 `web_search` 搜「MCP protocol specification 2026」→ 看到 5 条结果 + `degraded=false`。
**常见坑**：stdio 报 `command not found` → 用绝对路径（`.venv/bin/utf8-search`）。

### 2.2 Codex（CLI/IDE 的 MCP 配置）

**MCP（stdio）**：`~/.codex/config.toml`
```toml
[mcp_servers.utf8-search]
command = "utf8-search"
args = ["stdio"]
```
**MCP（HTTP）**：
```toml
[mcp_servers.utf8-search]
url = "https://203.0.113.10.sslip.io/mcp"
bearer_token_env_var = "UTF8SEARCH_KEY"     # 或 http_headers = { Authorization = "Bearer <KEY>" }
```
**REST**：同 §1（Codex 可用 shell 工具直接 curl）。
**验证**：让它跑 §1 的 curl，并把 `degraded` 读出来解释一遍（同时验证 Key 与字段理解）。

### 2.3 Cursor

**MCP（stdio）**：`.cursor/mcp.json`（或全局 `~/.cursor/mcp.json`）
```json
{"mcpServers": {"utf8-search": {"command": "utf8-search", "args": ["stdio"]}}}
```
**MCP（HTTP）**：
```json
{"mcpServers": {"utf8-search": {"url": "https://203.0.113.10.sslip.io/mcp",
  "headers": {"Authorization": "Bearer <KEY>"}}}}
```
**REST**：Cursor 里用 HTTP 请求文件/终端跑 §1。
**验证**：在 Chat 里问「用 utf8-search 搜 Python 3.13 新特性，列出前 3 条 url」→ 期望 3 条 3.13 相关页面。

### 2.4 Cherry Studio

**MCP**：设置 → MCP 服务器 → 添加 → 类型选「Streamable HTTP」→ URL `https://203.0.113.10.sslip.io/mcp`，
自定义 Header 加 `Authorization: Bearer <KEY>`（或 `X-API-Key: <KEY>`）。
**REST**：设置 → 模型服务 → 添加「OpenAI 兼容」自定义服务，Base URL 填 `https://203.0.113.10.sslip.io`
（该客户端需支持自定义工具/函数调用时才算打通 REST；不支持的版本只用 MCP 即可）。
**验证**：在对话里启用该工具，问「搜索 iPhone 17 Pro 价格 参数」→ 顶部应出现工具调用，结果 5 条。
**常见坑**：Cherry Studio 的 HTTP 传输对 `Host` 敏感 —— 若报 **421**，检查 URL 是否写成了 IP（应用白名单按 Host 精确匹配）。

### 2.5 Dify

**REST（推荐）**：工作流/Agent 里加「HTTP 请求」节点：

| 项 | 值 |
| --- | --- |
| Method / URL | `POST` `https://203.0.113.10.sslip.io/v1/search` |
| Headers | `Authorization: Bearer <KEY>`、`Content-Type: application/json` |
| Body | `{"query":"{{用户输入}}","max_results":5,"search_depth":"basic"}` |

**MCP**：Dify 原生支持 MCP（自 1.6+）→ 添加 MCP Server，URL 同上 `/mcp`，Header 同上。
**验证**：跑一次工作流，检查输出节点里能取到 `results[0].url` 与 `degraded`。
**常见坑**：Body 必须显式 `Content-Type: application/json`，否则 400（我们已把校验错误对齐 Tavily 的 400）。

### 2.6 n8n

**REST（HTTP Request 节点）**：
```
Method: POST
URL: https://203.0.113.10.sslip.io/v1/search
Authentication: Header Auth  (Name: Authorization, Value: Bearer <KEY>)
Body Content Type: JSON
Body: {"query":"{{ $json.query }}","max_results":5,"search_depth":"basic"}
```
**MCP**：n8n 有社区 MCP 节点时同上配置 `/mcp` + Header；没有则只用 REST。
**验证**：手动执行一次，确认输出 JSON 里有 `results` 与 `degraded`；再把 `degraded=true` 的分支接一个 IF 节点（示例：`freshness_unverified` → 提示"时效未验证"）。
**常见坑**：n8n 默认会带自己的 `User-Agent`/`Host`，公网访问必须用域名（`203.0.113.10.sslip.io`）而不是裸 IP。

### 2.7 自研 Agent（Python，两种接法各 20 行）

```python
# ① REST（最短路径）
import httpx
r = httpx.post("https://203.0.113.10.sslip.io/v1/search",
               headers={"Authorization": "Bearer <KEY>"},
               json={"query": "台风 最新消息 路径", "max_results": 5, "topic": "news", "days": 1},
               timeout=30.0)
data = r.json()
print(r.status_code, [x["url"] for x in data["results"]])
if data.get("degraded"):
    print("降级原因:", data["degraded_reason"])     # 常见：freshness_unverified

# ② MCP（官方 SDK，stdio 与 HTTP 同源写法）
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async with stdio_client(StdioServerParameters(command="utf8-search", args=["stdio"])) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        out = await session.call_tool("web_search", {"query": "MCP protocol specification 2026", "max_results": 3})
        print(out.content[0].text[:200])
```
**验证**：① 打印的 url 数量=5；② MCP 返回的文本里能找到 `degraded` 字段。

## 3. 故障对照表（421 / 401 / 429 三类）

| 现象 | 状态码 | 响应特征 | 原因与处理 |
| --- | --- | --- | --- |
| `Invalid Host header` | **421** | body 无 `error` 字段 | 公网请求的 `Host` 不在白名单。**改用 `https://203.0.113.10.sslip.io` 或把客户端 Host 加进 `UTF8SEARCH_MCP_ALLOWED_HOSTS`** |
| `无效的 API Key：请在 Authorization: Bearer <key>、X-API-Key 或请求体 api_key 中提供` | **401** | 带 `detail` + `error` | Key 没传/传错。核对三种传法（§0），注意别把 `Bearer` 漏掉 |
| `请求过于频繁，请 N 秒后重试。` | **429** | **`Retry-After`=整分钟级（如 59）** | **应用限流（RPM=60，按 Key 统计）**。降速，或给不同客户端分配不同 Key |
| `上游搜索过载（queue_full／timeout／no_capacity）：已返回明确失败而不是挂到超时，请 N 秒后重试。` | **429** | `Retry-After` 通常 **1-6 秒**（等于闸门 `max_wait` 量级） | **上游闸门过载**（limit=3 / queue=12 / max_wait=4.0s）：说明上游被压住，**等几秒重试即可**；这是"宁可快速失败，不要一起慢"的预期行为 |
| `degraded=true` + 任意 reason | **200** | 正常结果 + 标记 | **不是故障**，见 §0 的 degraded 表 |

**一眼区分两种 429**：看 body 文案（「请求过于频繁」=RPM；「上游搜索过载」=闸门）+ 看 `Retry-After` 量级（几十秒 vs 几秒）。

## 4. 回填方式（给用户的 3 步）

1. 打开 `docs/reports/manual-acceptance-checklist-20260928.md` 的客户端表格；
2. 按本文件对应小节复制配置 → 跑「最小验证」→ 把「跑通 ✅ / 失败备注」填上；
3. 若失败，按 §3 对照表定位（421/401/429 三类最常见），把现象与状态码填进备注列。
