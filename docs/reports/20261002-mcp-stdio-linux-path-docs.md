# MCP stdio 接入：补 Linux/macOS 路径 + 澄清 `Auth: Unsupported`（2026-10-02）

## 1. 起因

本机 Codex CLI 执行 `/mcp` 看到：

```
- utf8-search: unknown (2 tools)
  - Auth: Unsupported
  - Tools: web_fetch, web_search
```

要回答两件事：**这是故障还是预期？** **文档有没有把人坑了？**

## 2. 结论一：`Auth: Unsupported` / `unknown` 属预期，不是故障

- 服务端对**未带 Key** 的请求返回 **401**，且**不带 `WWW-Authenticate` 响应头**；MCP 客户端探测不到 OAuth 端点，
  于是标记 `Auth: Unsupported`、状态 `unknown`。
- **判断是否真正连上的依据 = 工具有没有列出来**：客户端列出 `web_fetch`、`web_search`，与服务端契约一致 ⇒ 链路正常。
- HTTP 传输的 Key 走静态 `Authorization: Bearer`（或 `X-API-Key`），不涉及 OAuth 发现。

## 3. 结论二：服务器上的 Codex 配置本来就是对的

`~/.codex/config.toml` 已使用 Linux 路径（**无需修改**）：

```toml
[mcp_servers.utf8-search]
type = "stdio"
command = '/opt/utf8-search/.venv/bin/utf8-search'
startup_timeout_sec = 60

[mcp_servers.utf8-search.env]
UTF8SEARCH_SEARXNG_URL = "http://127.0.0.1:8888"
UTF8SEARCH_TRUST_ENV = "false"
UTF8SEARCH_LOG_LEVEL = "WARNING"
```

早前那版写的是 Windows 路径（`~/utf8-search/.venv/Scripts/utf8-search.exe`），Linux 上不存在 ⇒ 客户端只能显示 `unknown (0 tools)`；
现在是 **2 tools**，说明这条已经修好。**这也正是本轮要写进文档的坑。**

## 4. 实测证据（服务器，2026-10-02）

```bash
cd /opt/utf8-search && .venv/bin/python scripts/mcp_selfcheck.py --mode stdio,stdio-raw
```

**6/6 通过**：

| 通道 | 检查 | 结果 |
| --- | --- | --- |
| stdio | initialize | `utf8-search 0.1.0`（2.63s） |
| stdio | tools/list | `web_fetch,web_search`（参数/必填/枚举符合契约） |
| stdio | call web_search(basic) | 5 条结果 |
| stdio | call web_search(news) | 5 条结果（5 条带日期） |
| stdio | call web_fetch | `https://example.com` 抽取 156 字符 |
| stdio-raw | handshake | stdout 2 行全为合法 JSON-RPC，工具 `['web_fetch','web_search']` |

另在本机（Windows）把同一枚 `initialize` 帧直喂 `.venv\Scripts\utf8-search.exe`，
stdout 返回含 `"serverInfo":{"name":"utf8-search","version":"0.1.0"}` —— 即文档里那条「一条命令自检 command」是实测可用的。

## 5. 真正要修的问题：文档只有 Windows 路径

`docs/03-客户端接入指南.md` 原文两处会误导 Linux / macOS 用户：

1. §1.2 只说「本机可执行文件位于 `.venv\Scripts\utf8-search.exe`」——没有 `bin/` 版本；
2. §3.2 Codex 的 `config.toml` 示例只给了 `C:\Users\...\.venv\Scripts\utf8-search.exe` 一条绝对路径。

照着抄到 Linux 的后果就是「客户端 `unknown (0 tools)` 且不报错细节」，排查成本高。

## 6. 改动（`docs/03-客户端接入指南.md`）

| # | 位置 | 改动 |
| --- | --- | --- |
| 1 | §1.2 | 可执行文件按平台分表（`Scripts\...exe` vs `bin/utf8-search`），并加 ⚠️ 说明「Linux/macOS 没有 `Scripts\`、没有 `.exe`，抄 Windows 路径会只显示 `unknown (0 tools)`」 |
| 2 | §3 开头 | `command` 规则补 Linux/macOS：同样用绝对路径，但不要带 `.exe`、不要用 `Scripts/` |
| 3 | §3.2 | Codex 配置拆成 **Windows** 与 **Linux/macOS** 两段（Linux 段给 `/opt/utf8-search/.venv/bin/utf8-search`） |
| 4 | §3.2 后 | 新增「写完先自检 `command`」：① 一条 `printf` + `initialize` 帧；② 仓库自带的 `scripts/mcp_selfcheck.py --mode stdio,stdio-raw`；并注明**改完需重启 Codex 会话** |
| 5 | §4 HTTP | 新增说明：未鉴权时 `Auth: Unsupported` / `unknown` 属预期（401 不带 `WWW-Authenticate`），**看工具有没有列出来**判断连通性 |
| 6 | §7.1 | 「另外两条边界」→「另外三条」，补一条同样的 Auth 预期，指向第 4 节 |

## 7. 影响面与回滚

- **纯文档**：未改 `src/`、`scripts/`、`docker-compose.yml`、`settings.yml`、`.env`，未重启容器、未动现网。
- 回滚：`git revert <commit>`（或切回上一版 `docs/03`）。
- 离线套件不受影响（本轮未跑，改动不涉及代码）。

## 8. 遗留

- **3-9 真实 GUI 客户端联调**仍是唯一人工项；本轮 §3.2 的自检命令可直接作为 Codex 一路的操作步骤。
