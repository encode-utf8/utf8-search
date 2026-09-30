# 人工验收操作单（2-9 相关性抽检 / 3-9 真实客户端联调）

> 这两项**必须由本人操作**（需要人工判断相关性 / 需要真实客户端界面），本文件把它们拆成
> 「照着做即可」的步骤。做完把结论填回 `checklist.md` 对应行即可，无需改代码。
>
> 前置（服务器上，沙箱外执行）：服务已起、SearXNG 可用。
>
> ```bash
> cd /root/utf8-search
> curl -sS http://127.0.0.1:8888/healthz -o /dev/null -w 'searxng=%{http_code}\n'   # 期望 200
> curl -sS http://127.0.0.1:8000/health                                          # 期望 searxng=ok
> ```

---

## 一、2-9 相关性抽检（20 条中英查询，人工打分）

**通过标准**：每条查询看 top5，**相关数 ≥ 4 的查询占比 ≥ 90%**（即 20 条里最多 2 条不达标）。
这是需求第 2/5 条的验收项，也是 `docs/04` §5.3 的输入。

### 第 1 步：生成待打分的明细表（约 1-2 分钟，会联网）

```bash
cd /root/utf8-search
.venv/bin/python scripts/relevance.py --depth basic --out data/acceptance/relevance-<今天的日期>.md
```

产物有两个（脚本会打印绝对路径）：

- 明细报告 `data/acceptance/relevance-<日期>.md`：20 条查询、每条 top5 的标题/URL/摘要；
- 打分模板 CSV（同目录）：表头 `id,scores,note`，`scores` 是 **5 个 0/1**，第 1 位对应排名第 1 的结果。

> 想重跑一批候选：加 `--no-cache`；只想换 SearXNG 地址：`--searxng http://127.0.0.1:8888`。

### 第 2 步：人工填分（唯一需要判断的一步）

打开打分模板 CSV，对每条查询的 top5 逐个判断「这条是否切题、可引用」：

```
1,1 1 1 1 0,中文购物类第 5 条是导购聚合页
2,1 1 0 1 1,
...
```

- 规则：**只填 0/1**（1=相关）；`note` 可选，写不达标的原因；
- 不要改 `id` 列（脚本按 id 对回查询）。

### 第 3 步：复算判定（不联网，秒级）

```bash
.venv/bin/python scripts/relevance.py --score-file data/acceptance/relevance-scores-<日期>.csv
```

输出逐条 `[通过]/[不通过]` 与总计，最后给 **通过 / 不通过** 与未达标查询清单。

### 第 4 步：回填

- `checklist.md` 第 2-9 行：把结果写上（例如「top5 相关数 ≥4 的查询占比 19/20 = 95% → 通过」）；
- 若未达标：把未达标查询与原因抄进 `checklist.md` 的「遗留与风险事项」，再决定是否开新任务修。
- 明细表建议留在 `data/acceptance/`（gitignore），结论进 `checklist.md` 即可。

---

## 二、3-9 真实客户端联调（逐客户端点一次）

**通过标准**：至少 Claude Desktop / Codex / Cursor 跑通（其余尽力）；跑不通就回修文档或代码。
自动化只能覆盖协议层（`scripts/mcp_selfcheck.py` 24 项），**各客户端自己的配置界面与文件名必须点一次**。

### 第 0 步：先跑自动化自检（确认服务侧没问题）

```bash
cd /root/utf8-search
.venv/bin/python -u scripts/mcp_selfcheck.py --out data/acceptance/selfcheck-<日期>.md
```

退出码 0 且「共执行 24 项检查：通过 24，失败 0」→ 服务侧没问题，剩下是客户端配置问题。

### 第 1 步：逐个客户端按表操作

| # | 客户端 | 最小操作 | 预期现象 | 跑通 |
| --- | --- | --- | --- | --- |
| 1 | **Claude Desktop** | 按 `docs/03` §3.1 写 `claude_desktop_config.json` → **完全退出**再启动 → 新对话问「今天有什么 AI 新闻」 | 工具列表出现 `web_search` / `web_fetch`；回答能引用 URL | ☐ |
| 2 | **Codex** | 按 §3.2 写 `~/.codex/config.toml` → 重启 → 让它联网查一条最新消息 | 会话里出现 `utf8-search` 的工具调用与结果 | ☐ |
| 3 | **Cursor** | 按 §3.3 在 MCP 设置里加 stdio 或 Streamable HTTP（`https://43.106.104.49.sslip.io/mcp`，带 Key） | 设置页显示工具已连接；对话里能搜到实时结果 | ☐ |
| 4 | Cherry Studio | 按 §3.4 添加 MCP 服务器（stdio 或 HTTP） | 工具列表出现两个工具，调用返回结果 | ☐ |
| 5 | Dify | 按 §6.1 建自定义工具（OpenAPI 导入 `https://43.106.104.49.sslip.io`） | 工具测试返回 `results[]`；工作流里可引用 | ☐ |
| 6 | n8n | 按 §6.2 用 HTTP Request 节点 POST `/v1/search` | 返回 JSON 且 `results` 非空 | ☐ |
| 7 | 自研 Agent | 按 §9 三选一（stdio / Streamable HTTP / REST） | 能拿到结构化结果 | ☐ |

**HTTP 客户端的 Key 传法**（三选一，任一可用）：`Authorization: Bearer <key>`、`X-API-Key: <key>`、
请求体 `{"api_key": "<key>"}`。Key 在服务器 `.env` 的 `UTF8SEARCH_API_KEYS`。

**常见失败与对应**（详见 `docs/03` §8 与 `docs/05` §8）：

- `/mcp` 一律 421 → Host 不在 `UTF8SEARCH_MCP_ALLOWED_HOSTS` 白名单；
- 所有请求 401 → 客户端没带 Key，或 Key 与 `.env` 不一致；
- 大量 429 → 触发限流（`UTF8SEARCH_RATE_LIMIT_RPM`），等待 `Retry-After` 后重试；
- 工具调用超时 → 上游搜索慢，可先用 `search_depth=basic` 验证通路。

### 第 2 步：回填

- `checklist.md` 第 3-9 行改成 `[x]` 或写清哪几个客户端跑通、哪几个失败；
- 失败项：把客户端、现象、原始报错抄进「遗留与风险事项」，并回修 `docs/03` 或代码。

---

## 附：本次（2026-09-28）已自动完成、无需人工的部分

- Tavily 兼容逐字段核对与补齐：见 [`m6-tavily-compat-20260928.md`](m6-tavily-compat-20260928.md)；
- 协议/鉴权/限流全通道自检：`scripts/mcp_selfcheck.py`（24 项，可随时重跑）。

---

## 复测操作规范：容器 HTTP 路径**必须绕缓存**（2026-09-30 补充）

应用缓存 `UTF8SEARCH_CACHE_QUERY_TTL=600`（10 分钟）。用 HTTP 路径复测门槛（news 时效、2-9 等）时：

1. **同一查询直接打第二次会命中缓存**，拿到的是十几分钟前的快照 —— 实测同一时刻同一个查询：
   原样 `台风 最新消息 路径` → **28%**，加尾空格（绕缓存）→ **56%**；
2. 规范做法（任选其一）：
   - 给查询加**唯一后缀**（尾空格、`#2026-09-30T12xx` 等），保证 cache key 不同；
   - 或等 TTL 过期（≥10 分钟）再测；
   - 或在脚本路径用 `scripts/news_check.py --no-cache`（进程内、天然不读应用缓存）；
3. **报告里必须注明"是否绕缓存"**；基于缓存快照得到的数字一律视为无效样本
   （例：`m6-news-freshness-20260930.md` 里容器路径 52% 的 3 轮回放已标为无效）。
4. 顺带提醒：`/metrics` 的计数器在**容器重建后归零**，跨重建比较计数时要注明起点。
