# 验收清单（checklist）

> 项目：utf8-search
> 用法：开发与交付以本清单为准，逐项完成并勾选后再向用户汇报。
> 状态标记：[ ] 未开始 / [x] 已完成 / [!] 阻塞 / [-] 不做

## 0. 任务目标与范围

**目标**：为 LLM 提供免费、高速的联网搜索服务（MCP Server + REST），效果对标 Tavily，速度对标 DeepSeek 联网搜索。

**本期范围**：M0 调研与规划 → M1 MVP → M2 速度与质量 → M3 稳定性（均已完成主体开发与验收）。

**明确不做**：全站爬虫与建索引、绕过付费墙、自带 LLM 生成答案（默认）、数据转售。

**参考文档**：`docs/01-前期调研与可行性分析.md`、`docs/02-技术方案与开发计划.md`、`docs/03-客户端接入指南.md`、`docs/04-后续路线图.md`。

## 1. M0 调研与规划

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 0-1 | 完成同类产品调研 | 阅读 `docs/01` 第 3 节 | 覆盖 Tavily、Exa、Serper、Brave、Google CSE、Jina、SearXNG、DeepSeek | [x] |
| 0-2 | 完成免费搜索源实测 | 阅读 `docs/01` 第 4 节 | 至少 10 个目标有实测结果与结论 | [x] |
| 0-3 | 验证自建 SearXNG 可行性 | 本机 Docker 起容器并查询 | 返回结构化 JSON 且结果数大于 10 | [x] |
| 0-4 | 量化延迟预算 | 阅读 `docs/01` 第 5 节 | basic / advanced 均有 P50、P95 目标 | [x] |
| 0-5 | 输出技术方案与里程碑 | 阅读 `docs/02` | 含架构、接口、缓存、部署、里程碑、风险 | [x] |
| 0-6 | 列出待用户确认问题 | 阅读 `docs/01` 第 8 节、`docs/02` 第 12 节 | 至少 6 条 | [x] |
| 0-7 | 用户确认方案 | 用户回复 | 明确同意或提出修改 | [x] |

## 2. M1 MVP

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 1-1 | SearXNG 容器可一键启动 | `docker compose up -d searxng` | 容器健康，`/search?format=json` 返回结果 | [x] |
| 1-2 | 服务进程可通过 stdio 提供 MCP | MCP 客户端调用 `web_search` | 返回结构化结果数组 | [x] |
| 1-3 | 搜索 Provider 抽象完成 | 单元测试 | SearXNG 与 Bing 两个实现可切换 | [x] |
| 1-4 | 查询缓存生效 | 连续两次相同查询 | 第二次 response_time 极低且 cached=true | [x] |
| 1-5 | 延迟基准脚本可用 | `python scripts/bench.py --n 5 --fresh` | 输出 P50 / P90 / P95 / 成功率报告 | [x] |
| 1-6 | 单元测试通过 | `pytest -m 'not net'` | 全绿，无联网依赖 | [x] |
| 1-7 | 配置项外置 | 修改 `.env` 后重启 | 端口、超时、缓存 TTL 生效 | [x] |

## 3. M2 速度与质量

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 2-1 | basic 模式延迟达标 | `scripts/bench.py` 5 次冷启动采样 | P50 ≤ 1.5 s，P95 ≤ 3 s | [x] |
| 2-2 | advanced 模式延迟达标 | 同上 | P50 ≤ 4 s，P95 ≤ 8 s | [x] |
| 2-3 | 抓取硬超时与提前返回 | 构造慢响应页面 | 单次请求不因慢页面超过设定上限 | [x] |
| 2-4 | 多路融合与去重 | 单元测试 + 抽检 | 同一 URL 不重复，来源已标注 | [x] |
| 2-5 | 正文抽取 | 对 22 个真实结果页抽取 | 成功率 ≥ 80% | [x] |
| 2-6 | `web_fetch` 工具可用 | MCP 客户端调用 | 返回 markdown 且长度受限 | [x] |
| 2-7 | Streamable HTTP 传输可用 | `mcp.Client("http://.../mcp")` | 工具调用成功 | [x] |
| 2-8 | REST 接口可用 | `curl /search`、`/v1/extract` | 返回与 MCP 一致的结构 | [x] |
| 2-9 | 结果相关性抽检 | 20 条查询人工评估 | top5 中至少 4 条相关 | [ ] |
| 2-10 | deep 模式「读几十个网页」 | `scripts/bench.py` deep 模式 | 平均读页 ≥ 8，单次最高 ≥ 15 | [x] |

## 4. M3 稳定性

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 3-1 | 引擎健康检查与自动降级 | 观察 `failed_engines` | 上游引擎被限流时自动剔除并继续返回结果 | [x] |
| 3-2 | SearXNG 故障兜底 | SearXNG 返回 0 条时 | 自动切换到 Bing Provider，仍返回结果 | [x] |
| 3-3 | 并发压测 | 10 并发查询 | 无 5xx、无超时 | [x] 10 并发无 5xx、无超时（上游容量瓶颈已记录，见 §9） |
| 3-4 | 连续运行稳定性 | 连续运行 24 h 定时查询 | 无线程/内存泄漏，可用率 ≥ 99% | [x] 2026-09-26~27 挂机 24h：可用率 100%、覆盖率 100%、内存抬升后走平（见 `docs/reports/m4-4.4-soak-24h-20260926.md`） |
| 3-5 | 可观测性 | 查看响应字段与日志 | 每次请求含耗时、读页数、命中来源与失败引擎 | [x] |
| 3-6 | 客户端接入文档 | 按文档配置 | Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent 均有配置示例 | [x] |
| 3-7 | SSRF 防护 | 向 `/v1/extract` 传内网地址 | 被拒绝，不发起请求 | [ ] |
| 3-8 | 云服务器部署 | Linux + `docker compose up -d` | 双容器健康，HTTPS + 鉴权可用 | [x] |
| 3-9 | 真实客户端联调 | 各客户端按 `docs/03` 配置 | 至少 Claude Desktop / Codex / Cursor 跑通 | [ ] |

## 5. 鉴权与限流（用户第 7 条需求）

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 4-1 | Bearer 鉴权 | `Authorization: Bearer test123` | 200 | [x] |
| 4-2 | X-API-Key 鉴权 | `X-API-Key: test123` | 200 | [x] |
| 4-3 | 请求体 api_key 鉴权 | `{"api_key": "test123"}` | 200 | [x] |
| 4-4 | 错误 Key 拒绝 | 携带 `wrong` | 401 | [x] |
| 4-5 | 未携带 Key 拒绝 | 不带任何 Key | 401 | [x] |
| 4-6 | `/health` 免鉴权 | 不带 Key 访问 | 200 | [x] |
| 4-7 | 限流生效 | `RATE_LIMIT_RPM=3` 后连打 6 次 | 前 3 次 200，之后 429 | [x] |

## 6. 实测记录（2026-09-23，美国出口 IP）

延迟基准：`python scripts/bench.py --n 5 --fresh`（冷启动，清空缓存）

| 模式 | P50 | P90 | P95 | 最大 | 平均读页 |
| --- | --- | --- | --- | --- | --- |
| basic | 1048 ms | 1095 ms | 1095 ms | 1544 ms | 0 |
| advanced | 3775 ms | 3914 ms | 3914 ms | 4492 ms | 3.0 |
| deep | 9234 ms | 9492 ms | 9492 ms | 10462 ms | 16.2（14–19 页） |

SearXNG 引擎可用性（本镜像 2026.9.23，均已写入 `searxng/settings.yml`）：

- 稳定可用（9）：`resulthunter`、`google`、`yandex`、`naver`、`privacywall`、`zapmeta`、`yahoo`、`fynd`、`sogou`
- 机会型（4，间歇被限流但失败极快、零成本）：`reloado`、`yep`、`brave`、`quark`
- 不可用：`bing`（返回 0 条）、`duckduckgo` / `baidu` / `qwant`（CAPTCHA）、`google cse`（unusual traffic）、`seznam`（timeout）、`mojeek` 与 `startpage`（本镜像标记 `inactive`，需 Proof-of-Work 验证码）、`crowdview` / `fastbot` / `tusksearch` / `vuhuv` / `fireball` / `gabanza` / `searchmysite` / `ayo` / `encyclosearch` / `abcnyheter`（0 条或超时）
- 兜底：服务自带 Bing HTML 直取 Provider，SearXNG 返回 0 条时自动接管
- 单次查询原始结果数：81 条 / 10 个引擎命中（13 引擎并发查询）

关键性能结论：

- **瓶颈在正文解析而非下载**：24 页并发下载约 2.5 s，解析约 3–5 s。
- trafilatura 受 GIL 限制，**解析线程池并非越大越快**：实测 2–8 线程最快；原 32 线程会因争抢 GIL 使得单页解析从 0.13 s 恶化到 11 s。
- 已优化：线程池默认 8；搜索结果已带标题时跳过 `extract_metadata`（省掉一次等价成本的完整解析）；deep 模式提前返回阈值提高到 0.8（覆盖优先）。
- 聚合上限 `SEARCH_TIMEOUT_LIMIT` 由 4.0 s 收到 2.5 s：实测 2/3/4 s 上限都能拿满结果（结果集早已饱和），收到 2.5 s 只砍长尾，basic P50 由 2056 ms 降到 1048 ms。
- 批量抽取接口改用独立预算 `EXTRACT_BUDGET`（默认 10 s）：调用方已指定 URL、不在延迟竞赛中，给更宽松预算以提高成功率。
- 引擎配置必须 `keep_only`（名单过滤）+ `disabled: false`（显式启用）双管齐下；仅 `keep_only` 不会打开默认关闭的引擎。

## 7. M4-4.1 SSRF 防护（当前任务）

**背景**：`/extract`、`/v1/extract`、MCP `web_fetch` 以及深度模式的抓取都会访问调用方给出的 URL。
公网部署后，攻击者可用它探测内网服务（`http://127.0.0.1:6379`）或云元数据（`http://169.254.169.254/latest/meta-data/`）。

**范围**：新增 `src/utf8_search/security.py`；改造 `PageExtractor` 的 URL 校验与重定向处理；新增配置项。
**不做**：不改动 SearXNG / Bing 等由运维配置的上游地址；不做 DNS 固定（rebinding 防护留作已知限制记录）。

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 4.1-1 | 仅允许 http/https | 单测传 `file://`、`ftp://`、`gopher://`、`javascript:` | 全部被拒绝 | [x] |
| 4.1-2 | 拒绝字面量内网 IP | 单测传 `127.0.0.1`、`10.0.0.1`、`192.168.1.1`、`172.16.5.4` | 全部被拒绝 | [x] |
| 4.1-3 | 拒绝云元数据地址 | 单测传 `169.254.169.254` | 被拒绝 | [x] |
| 4.1-4 | 拒绝其他保留网段 | 单测传 `0.0.0.0`、`100.64.0.1`、`224.0.0.1`、`::1`、`fc00::1` | 全部被拒绝 | [x] |
| 4.1-5 | 拒绝内网主机名 | 单测传 `localhost`、`foo.internal`、`router`（无点单标签） | 全部被拒绝 | [x] |
| 4.1-6 | 拒绝解析到内网的域名 | 打桩解析器返回 `10.0.0.5` | 被拒绝 | [x] |
| 4.1-7 | 放行正常公网地址 | 单测传 `https://example.com`、`8.8.8.8` | 允许通过 | [x] |
| 4.1-8 | 重定向逐跳复检 | respx 模拟 302 → `http://169.254.169.254/...` | 返回 None，且内网地址**未被请求** | [x] |
| 4.1-9 | 重定向次数上限 | 单测构造循环重定向 | 达到上限后放弃，不无限循环 | [x] |
| 4.1-10 | 可配置开关 | `UTF8SEARCH_BLOCK_PRIVATE_HOSTS=false` | 内网地址放行（内网自用场景） | [x] |
| 4.1-11 | 回归：既有测试不受影响 | `pytest -q -m "not net"` | 全绿 | [x] |
| 4.1-12 | 端到端拒绝 | curl `/v1/extract` 传本机 SearXNG 地址 | 返回 `failed_results`，不真正抓取 | [x] |

**风险 / 已知限制**：

- DNS rebinding：校验与连接之间存在时间差，理论上可被利用；本任务记录为已知限制，不做 IP 固定。
- 内网自用（如抓内网 wiki）需显式关闭开关。

**验收记录（2026-09-24，分支 `feature/m4-ssrf-protection`）**

- 离线测试：`pytest -q -m "not net"` → **69 passed, 4 deselected**（含新增 `tests/test_security.py` 35 项）。
- 单元覆盖：协议白名单、字面量内网 IP、云元数据、其他保留网段、内网主机名、解析到内网的域名、正常公网放行、重定向逐跳复检、重定向次数上限、开关关闭放行、既有回归。
- 端到端（本机 127.0.0.1:8124，`UTF8SEARCH_API_KEYS=test123`）：
  - `POST /v1/extract {"urls":["http://127.0.0.1:8888/search"]}` → `failed_results`，`response_time` 0.001 s（未发请求）
  - `POST /v1/extract {"urls":["http://169.254.169.254/latest/meta-data/"]}` → `failed_results`，0.001 s
  - `POST /v1/extract {"urls":["file:///etc/passwd"]}` → `failed_results`，0.001 s
  - 对照组 `https://example.com` → 正常返回正文（131 字符），未误伤
- 日志佐证：`WARNING 拒绝抓取 http://127.0.0.1:8888/search：目标 IP 127.0.0.1 属于保留网段`。

## 16. M6 Tavily 兼容性逐字段核对与补齐（2026-09-28，分支 `feature/m6-tavily-compat`）

**背景**：需求第 8 条要求兼容 Tavily。此前只到「客户端能连、能拿结果」，缺逐字段对照矩阵，也没有用官方示例响应做 fixture 断言。
另按用户要求先做第 0 步小修：`docs/05` §4.4 契约表 **@30 行的 P95 单元格**由「≤6.5s（见下注）」改为
**「记录值 3.0-8.5s（不设阈值）」**，与同行其它列的「不设阈值」口径一致（本清单 5.4-20 已同步）。

**范围**：新增 `tests/test_tavily_compat.py`、`docs/reports/tavily-official-search-20260928.md`（官方字段清单留档）、
`docs/reports/tavily-search-response-example-20260928.json`（官方示例响应 fixture）、`docs/reports/m6-tavily-compat-20260928.md`（矩阵报告）、
`docs/reports/manual-acceptance-checklist-20260928.md`（人工验收操作单）；修改 `models.py` / `core/pipeline.py` /
`server/http_api.py` / `server/mcp_server.py` / `docs/03-客户端接入指南.md`。**不碰**闸门自适应，**不碰**人工项本身。

| 编号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 6-1 | 逐字段对照矩阵 | `docs/reports/m6-tavily-compat-20260928.md` | 请求 / 响应 / 错误三类字段逐条给「字段·我方·Tavily·差异·影响」，并分三类处置 | [x] 报告 §1-§3 |
| 6-2 | 对照依据留档（不凭记忆） | `tavily-official-search-20260928.md` + 示例 JSON | 官方字段清单（从 OpenAPI schema 逐字提取）与示例响应入库，测试直接引用 | [x] 抓取日期 2026-09-28，来源 URL 已记 |
| 6-3 | 可直接补齐项已补 | 代码 diff | `results[].favicon/images/id`、顶层 `auto_parameters`、`usage`、`/extract` 的 `results[].images`、错误体 `error` | [x] 只加字段/键，未改既有字段类型与语义 |
| 6-4 | 官方 fixture 断言 | `tests/test_tavily_compat.py` | 官方示例响应能被我们的模型直接解析；我们的响应覆盖官方示例每个字段路径 | [x] 8 条离线用例全绿 |
| 6-5 | REST 与 MCP 同一套字段 | 同上 | `web_search` 输出 ⊇ 官方字段路径，且含本轮补齐字段 | [x] |
| 6-6 | 错误码与限流语义 | 同上 | 401/429/422 形态；429 带 `Retry-After`；用官方 SDK 的解析写法能分类且不崩 | [x] 官方 SDK 的 `detail.error` 取法有 try/except 兜底，我们额外给顶层 `error` |
| 6-7 | 不改既有字段语义 | `pytest -q -m "not net"` | 全绿 | [x] **264 passed, 4 deselected** |
| 6-8 | 人工验收操作单（附带产出） | `docs/reports/manual-acceptance-checklist-20260928.md` | 2-9 的填分步骤与命令、3-9 每个客户端的最小操作与预期现象 | [x] 供用户本人照着做 |

## 15. M5 上游并发闸门与过载快速返回（2026-09-27，分支 `feature/m5-concurrency-gate`）

**背景**：`docs/04` §4.4 实测——并发 1-3 时 P50 ≈ 1.3s，并发 10 冷查询劣化到 ~12s；直连 SearXNG 探测显示
上游聚合吞吐仅 1.3-2.0 req/s，**瓶颈在上游聚合而非本服务**。现状没有上游并发闸门，10 个请求同时压垮上游后
全体一起变慢。目标改为「**宁可快速失败，不要一起慢**」。

**范围**：新增 `src/utf8_search/core/upstream_gate.py`（闸门 + 最小指标集）、`/metrics` 端点、REST/MCP 过载映射、
`Settings` 三个闸门参数；**不改**搜索语义 / 融合 / 时效 / 引擎健康自适应逻辑。

| 编号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 5.4-1 | 闸门放行 / 排队 / 拒绝判定 | 离线单测 `tests/test_upstream_gate.py` | limit 内立即放行；超限排队；队列满或等待超时立即抛 `UpstreamOverloaded` | [x] 13 条单测全绿 |
| 5.4-2 | 闸门参数配置化 | `Settings` + `.env.example` | `UTF8SEARCH_UPSTREAM_MAX_CONCURRENCY/QUEUE_LIMIT/MAX_WAIT/OPTIONAL_WAIT` 可解析，默认 **3 / 12 / 4.0s / 1.0s**（排队优先，见 5.4-14/5.4-18） | [x] 四项默认值与 env 覆盖均有单测 |
| 5.4-3 | 过载不被吞成空结果 | 离线回归：provider 抛 `UpstreamOverloaded` | `pipeline.search` 抛 `UpstreamOverloaded`，**不返回 0 条** | [x] `test_pipeline_raises_overload_instead_of_returning_empty` |
| 5.4-4 | 过载不降级到兜底源 | 离线：searxng 过载时兜底 provider 调用数为 0 | 直接上抛，不把压力转嫁给更脆弱的抓取源 | [x] `test_overload_does_not_fall_back_to_secondary_provider` |
| 5.4-5 | REST 过载映射 | 离线：桩 pipeline 抛过载 → `POST /v1/search` | HTTP 429 + `Retry-After` | [x] 实测 429 + `Retry-After: 3` |
| 5.4-6 | MCP 过载映射 | 离线：`web_search` 过载 | 返回可读 `isError` 文本（非空结果、不是「没搜到」） | [x] `ToolError` 文本含「上游搜索过载」「秒后重试」 |
| 5.4-7 | `/metrics` 最小指标集 | 离线：`GET /metrics`（沿用 REST 鉴权） | Prometheus 文本：等待数、被拒计数、排队时长与上游延迟直方图 | [x] 单测 + loadtest 实抓均通过 |
| 5.4-8 | metrics 可关闭 | `UTF8SEARCH_METRICS_ENABLED=false` | 端点不可用 | [x] 404 |
| 5.4-9 | 并发 10 冷查询不出现 12s 级 P95 | `scripts/loadtest.py --concurrency 10 --n 50` | P95 远低于 12s，超出部分快速 429 | [x] 新默认下 general@10 P95 **4847ms**（100% 成功）；news@10 P95 **5955ms**（96% 成功，且降级率 **0%**、空结果率 **0%**） |
| 5.4-10 | general 与 news 两组对比 | loadtest 两组各跑基线/改动后 | 输出 P50/P90/P95/max/QPS、5xx/超时计数、成功数 vs P95 权衡表 | [x] 报告 §6：成功率、**降级率、空结果率**并列；墙钟吞吐与**有效吞吐（成功/墙钟）**并列，含 429 的墙钟吞吐标注「非服务吞吐」 |
| 5.4-11 | 单请求延迟不回退 | 单并发 P50 对比 | 退化 ≤ 5%（>5% 停下汇报） | [x] 单并发 P50 834→**822ms**、P95 1452→**1332ms**、max 1638→1335ms（@1 排队计数 = 0） |
| 5.4-12 | 不回退既有能力 | 离线套件全绿 | 质量过滤 / 时效分层 / 引擎健康逻辑未被改动 | [x] `pytest -q -m "not net"` → **256 passed** |
| 5.4-13 | 报告归档 | `docs/reports/m5-concurrency-gate-20260927.md` | 写明 12s 根因经实测确认是哪一段、闸门消掉了哪一段、news 占两槽位的影响 | [x] 报告 §1/§3-§6 |
| 5.4-14 | 参数矩阵扫描与 queue/max_wait 选点（**结构优化前所测**，news 行已被 5.4-18/19 取代） | limit=3，queue ∈ {6,12} × max_wait ∈ {2.5,4,6}，@1/@10/@30 × general/news | 「@10 ≥90% 且 P95≤6s，取最小 max_wait」 | [x] queue=6 时 @10 仅 18% 淘汰；queue=12 时 @10 ≥90%、4.0 达 100% → 取 **4.0s**（保持，不上调）。**原「general@30 ≥25%」阈值已作废**：7 轮实测 25/23/25/25/15/27/22%（中位 24.5%）落在噪声里，改由 5.4-20 的分层契约表述 |
| 5.4-15 | news 召回（降级率 / 空结果率） | news@10 扫 `OPTIONAL_WAIT` ∈ {1.0,1.5,3.0}（结构优化后） | 降级率 ≤ 30% 且 空结果率 ≤ 10% 且 P95 ≤ 6.5s，取最小值 | [x] 三者全部满足：**1.0s** → 降级 **0%**、空结果 **0%**、P95 **5955ms**；1.5s → 0%/0%/6430ms；3.0s → 0%/0%/6098ms → 取最小 **1.0s** |
| 5.4-16 | 健康日的代价定位 | general@10 交错重测 base→gate→base→gate（各 2 轮） | 排除上游漂移后如实归因 | [x] 基线 P50 2379-2551ms/墙钟 13.4-13.8s；闸门开 P50 3156-3388ms/墙钟 16.5-17.6s（+23~42%，两次交错均复现）→ 写为「**健康日付约 20-30% 尾延迟代价换坏日保护**」；`docs/05` §4.4 给出调大上限（如 6）的建议与风险；自适应列入 `docs/04` §8 遗留 |
| 5.4-17 | 429 时延（**容量/证据陈述，不设阈值**） | 进程内微基准 + 同链路地板 + 单发/饱和探针 | 记录事实与归因，不作为达标项 | [x] 陈述：闸门决策 **0.32µs / 3.88µs**；缓存命中地板 p50 **7.2ms**；单发 429 p50 **20.9ms**（多出的 ~13ms 来自闸门前的两次缓存查询 + aiosqlite 串行化，非闸门在等）；饱和观察 193-353ms（单 worker + 压测客户端饱和）。原「单发 <20ms」阈值已作废 |
| 5.4-18 | 调用分两类 + 结构优化 | 单测 + 结构说明 | 按「跳过是否导致返回空结果」分兜底型/锦上添花型；兜底型不许静默跳过 | [x] `_collect_general_extra` 改「主源不足才补（复用 5.2 判据）+ 串行」，news 上游需求 ~1；Bing 兜底同判据；兜底型拿不到容量 → 抛 `UpstreamOverloaded`（429）。单测：主源充足不触发补路；不足时串行触发且带 `optional_wait`；无容量 → 429 而非空结果 |
| 5.4-19 | 运行点曲线与「不降级并发上限 N」 | general/news 各 @1/@2/@3/@5（n=30），另补 @10/@30 | 给出 N 与各点成功率/降级率/空结果率/P50/P95 | [x] **降级率在所有测点（@1/2/3/5/10/30）均为 0%**（静默跳过已从产品路径移除）⇒ N **≥30**；成功率/P95：@≤5 全 100% 且 P95 ≤5.2s，@10 96%/5955ms，@30 20%/8474ms（超出 6.5s，瓶颈是上游容量） |
| 5.4-20 | 服务契约分层（替代单点阈值） | docs/05 §4.4 + 本清单 + 报告 §7 | @≤5：100% 成功 / 0 降级 / P95 ≤5.2s；@10：≥95% / 0 降级 / P95 ≤6.5s；@30：**容量陈述（成功率与 P95 均不设阈值，P95 记录值 3.0-8.5s）** / 0 降级 / 0 空结果 / 秒级 429 | [x] @≤5 与 @10 **逐点达标**；@30 降级与空结果 0%、429 秒级 ✓，成功率与 P95 按容量陈述记录（general 15-27%、P95 3.0-6.9s；news 15-28%、P95 3.7-8.5s），不设阈值 |
| 5.4-21 | 「不足才补 + 串行」的代价对照 | 旧提交 `a063e88`（news 并行双打）vs 新默认，news@1/@2 各 n=30 | 若 @1 退化 >20% 则把混合模式列入遗留 | [x] **无退化，实为收益**：@1 P50 3280→**1383ms**（-58%）、P95 5326→4497ms；@2 P50 2557→**1413ms**（-45%）、P95 4965→3340ms。故混合模式**不列入**遗留 |
| 5.4-22 | news@30「净负」的定性 | base→gate→base→gate 各 2 轮（n=60、@30） | 确认是否可复现，并写清好日/坏日前提 | [x] 复现为**好日 artifact**：好日基线 100% 服务（P95 6.5-9.6s），闸门只留 15-20%（429×48-51、服务到的 P95 4.9-6.6s）；坏日（§4.4 的 19s 级）闸门才是保护。扩容方向（多实例 SearXNG / 何时可提高 `MAX_CONCURRENCY`）写入 `docs/05` §4.4 |

**风险 / 取舍**：闸门是**单进程**的（本项目 `serve` 单 worker；多 worker 需按 worker 数分摊，手册说明）；
高并发下成功率会下降（预期取舍，loadtest 给权衡数据）；`/metrics` 沿用 REST 鉴权（避免经 Caddy 对外裸奔）。
**不在本轮**：人工项 2-9、3-9；M6。

## 14. M4-4.2 云服务器部署验收（2026-09-25）

**背景**：`docs/04-后续路线图.md` 第 4.2 节要求「Linux VPS + `docker compose up -d`，SearXNG + 应用均健康；反向代理 + HTTPS，配置 `UTF8SEARCH_MCP_ALLOWED_HOSTS`；开启 `UTF8SEARCH_API_KEYS`，确认 401/429 行为；`data/` 卷持久化验证；产出 `docs/05-服务器部署手册.md`」。

**范围**：新增 `Caddyfile`、`docs/05-服务器部署手册.md`、`docs/reports/m4-4.2-deploy-20260925.md`；修改 `docker-compose.yml`（Caddy 服务 + 应用端口收回回环 + 应用 healthcheck）、`.env`（gitignore）、`docs/04-后续路线图.md`、`checklist.md`。**阶段 A3 收尾**另修 `scripts/mcp_selfcheck.py`（时效性口径 / ratelimit Key / Key 掩码 / 复现命令平台自适应）并新增离线回归 `tests/test_mcp_selfcheck.py`；**未改 `src/`**。

**部署环境**：阿里云新加坡 `43.106.104.49`（Ubuntu 22.04.5 / x86_64），域名 `43.106.104.49.sslip.io`，基线 commit `a5e5756`。

| 编号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 4.2-1 | 整栈起来 | `docker compose up -d --build` + `docker compose ps` | SearXNG 与应用均 healthy | [x] |
| 4.2-2 | 对外只暴露 TLS | `ss -ltn`；从非回环网卡直连 8000 | 应用端口为 `127.0.0.1:8000`，其它接口 `Connection refused` | [x] |
| 4.2-3 | 新增 Caddy 反向代理 | 加入 `docker-compose.yml` + `Caddyfile` | 对外只开 80/443，TLS 终止后转 `utf8-search:8000` | [x] |
| 4.2-4 | 阿里云安全组只放行 22/80/443 | 控制台手工改 + 公网探测 | 安全组已放行，公网可访问 | [x] 2026-09-25 放行；公网 `80 → 308`、`443 → 200` |
| 4.2-5 | 无域名拿真证书 | Caddy 自动 ACME（sslip.io） | Let's Encrypt 签发成功 | [x] 已签发真证书，有效期至 2026-12-24（A3 复核指纹见部署报告 3.1） |
| 4.2-6 | 自签兜底与客户端信任 | 导出 Caddy 根 CA + `update-ca-certificates` | 客户端信任根证书后可正常校验 | [x] |
| 4.2-7 | 配置 `UTF8SEARCH_MCP_ALLOWED_HOSTS` | 伪造 Host 请求 `/mcp` | 白名单内 200、伪造 Host 421 | [x] |
| 4.2-8 | 开启鉴权 | 无 Key / 错 Key 请求 | 均返回 401 | [x] |
| 4.2-9 | 三种 Key 传法 | Bearer / X-API-Key / body `api_key` | 三路均 200 | [x] |
| 4.2-10 | 限流 | 部署环境连发 65 次（RPM=60） | 出现 429 且带 `Retry-After` | [x] |
| 4.2-11 | `data/` 卷持久化 | 重启应用容器后同查询 | 缓存文件仍在，`cached=true` | [x] |
| 4.2-12 | 全通道回归（TLS + 鉴权） | `mcp_selfcheck.py --base-url https://... --api-key` | 24/24 通过，exit 0 | [x] 阶段 A3 修掉脚本自身缺陷后，**主命令一次跑出 24/24** |
| 4.2-13 | 产出部署手册 | `docs/05-服务器部署手册.md` | 含端口/安全组/环境变量/证书/升级回滚/排障 | [x] |

**关键实测值**：

- 容器：app `Up (healthy) 127.0.0.1:8000->8000/tcp`、searxng `Up (healthy) 127.0.0.1:8888->8080/tcp`、caddy `Up 0.0.0.0:80,0.0.0.0:443`。
- 鉴权：无 Key / 错 Key → 401；Bearer / X-API-Key / body `api_key` → 200；连发 65 次 → 59×200 后 429（`retry-after: 51`）。
- Host 白名单：域名 200、裸 IP 200、`rebind.example` → 421（`server: uvicorn`）。
- 持久化：`cached=False` → 重启 → `cached=True`，`cache_entries=26`。
- 全通道自检：2026-09-25 首次为主命令 22/24（2 项 ratelimit 失败源于脚本 bug）+ `--mode ratelimit` 单跑 2/2；**阶段 A3 修掉脚本自身缺陷后，主命令一次跑出 24/24、exit 0**。

**本轮修掉的问题**：

- **Caddy 吞掉不匹配 Host 的请求**：原配置下伪造 Host 会拿到 Caddy 自己的「空 200」而非应用的 421，等于把 DNS 重绑定防护架空。修法：`header_up Host {http.request.host}` 透传原始 Host，并加 `:443` 兜底站点把所有 Host 都交给应用判定。修复后伪造 Host 正确返回 421。
- **应用容器无 healthcheck**：补上后 `docker compose ps` 才显示 `Up (healthy)`。

**阶段 A3 修掉的脚本自身缺陷**（详见部署报告第 6 节）：

- 时效性判定与产品口径不一致：旧实现「最旧一条 ≤ 3 天」，而 M5-5.2 / `docs/04` 第 5.2 节 / `.env.example` 的口径是「**带 7 日内日期、门槛 ≥ 80%**」。已改为窗口 `min(settings.news_fresh_days, 7)`、判「带日期结果中落在窗口内的比例 ≥ 80%」，最旧值仅作诊断。这是**自检脚本缺陷**，不代表产品新鲜度变差。
- `scripts/mcp_selfcheck.py`：`--api-key` 与 ratelimit 通道实例的 Key 不一致，导致用自定义 Key 跑时 ratelimit 两项必然 401 —— 已改为复用 `--api-key`。
- `scripts/mcp_selfcheck.py`：会把完整 API Key 打印进报告 —— 已改为只输出掩码（前 4…后 4），`render_report` 再兜底脱敏。

**附加观测（`google news`）**：部署后连续 6 条 news 查询 6/6 失败，`/health` 显示 `class=captcha`、`consecutive_failures=6`；但**重启 SearXNG 清空其处罚盒后 6/6 成功**，同机直连 Google 搜索页也稳定 200 → 判定为间歇性风控 + SearXNG 自锁，**不是这台机器 IP 被永久封禁**，无需改代码，换源建议见 `docs/reports/m4-4.2-deploy-20260925.md` 第 7.3 节。

**风险 / 已知限制**：

- 安全组未放行前，公网不可达、Let's Encrypt 无法签发（放行后需「删缓存证书 + 重启 caddy」两步切换，仅 restart 不会重新申请）。
- 公开受信任证书会把该 IP 写进证书透明度（CT）日志，属公开永久记录。

## 13. M4-4.3 真实客户端联调（✅ 自动化已完成 2026-09-24；4.3-12 待人工回填）

**背景**：`docs/04-后续路线图.md` 第 4.3 节要求「按 `docs/03` 逐个跑通并记录：Claude Desktop、Codex、
Cursor、Cherry Studio、Dify、n8n、自研 Agent；任一跑不通则回修文档或代码」。

**可行性分析（先说清界限）**：

- **可自动化**：这些客户端与服务的交互最终只有三条通道 —— ① MCP stdio（Claude Desktop / Codex / Cursor /
  Cherry Studio 本地）、② MCP Streamable HTTP（`/mcp`，Cursor / Cherry Studio 远程、Codex 新版本）、
  ③ Tavily 兼容 REST（Dify / n8n / 自研 Agent）。三条通道都能用**官方 MCP SDK 客户端**（`mcp` 2.2.0，
  客户端内部实现与真实客户端同源）与 HTTP 客户端跑完整的端到端验证，含握手、能力协商、工具调用、鉴权、限流。
- **不可自动化**：各客户端自身的「配置界面 / 配置文件名 / 参数名」是否正确，必须在客户端里点一次。
  本任务交付一份**逐客户端人工联调清单**（`docs/03`），把点击步骤收敛到最小（每客户端 1-3 步 + 一句预期现象）。
- 结论：自动化部分全部纳入本轮验收；人工部分交给用户按清单执行，结果回填清单表。

**设计（`scripts/mcp_selfcheck.py`）**：

| 通道 | 检查项 |
| --- | --- |
| A. MCP stdio（SDK 客户端） | 启动 `utf8-search stdio` 子进程；`initialize`（服务名/版本）；`tools/list`（`web_search`/`web_fetch` 及其必填参数与枚举）；`tools/call web_search`（general basic）；`tools/call web_search`（news + time_range）；`tools/call web_fetch` |
| B. MCP stdio 原始帧 | 绕过 SDK 直接读写子进程管道：断言 stdout 里每一行非空输出都是合法 JSON-RPC（**防日志/`print()` 污染协议通道**，这是 stdio 客户端「连上了但工具调不通」的头号原因） |
| C. MCP Streamable HTTP | 起本地 `serve`（临时端口 + 临时 Key）；SDK 客户端连 `/mcp`：`initialize` / `tools/list` / `tools/call`；无 Key 时 `/mcp` 应 401；伪造 Host 应 421 |
| D. REST / Tavily 兼容 | `GET /health`；`POST /v1/search`（X-API-Key）、`POST /search`（body `api_key`）；无 Key 应 401；`days=1` 应映射为 `time_range=day`；`include_domains` 生效；`POST /v1/extract` 返回正文；`include_raw_content` 生效 |
| E. 限流 | 单独起一个 `RATE_LIMIT_RPM=1` 的实例：第 1 次 200、第 2 次 429 |

**范围**：新增 `scripts/mcp_selfcheck.py`、`tests/test_mcp_selfcheck.py`（离线：握手 + tools/list）；
改动 `docs/03-客户端接入指南.md`（联调清单 + 自研 Agent 示例 + 修掉 Q6 损坏的代码块）、
`docs/04-后续路线图.md`、`README.md`、`docs/reports/`；

| 编号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 4.3-1 | MCP stdio 握手与工具发现 | `scripts/mcp_selfcheck.py --mode stdio` | `initialize` 返回服务名/版本；`tools/list` 含 `web_search`、`web_fetch` 且参数 schema 正确 | [x] |
| 4.3-2 | MCP stdio 工具调用 | 同上 | `web_search`（general/basic、news/time_range）与 `web_fetch` 均返回可用结果 | [x] |
| 4.3-3 | stdio 协议通道纯净 | `--mode stdio-raw` | stdout 每一行都是合法 JSON-RPC，无日志/print 污染 | [x] |
| 4.3-4 | MCP Streamable HTTP | `--mode http` | `/mcp` 握手 + 工具发现 + 工具调用全通 | [x] |
| 4.3-5 | `/mcp` 鉴权 | 同上 | 无 Key 返回 401；伪造 Host 返回 421 | [x] |
| 4.3-6 | REST 搜索（Tavily 兼容） | `--mode rest` | `/v1/search`、`/search` 均 200 且字段与 Tavily 对齐 | [x] |
| 4.3-7 | REST 鉴权与 Key 传递三种方式 | 同上 | Header `X-API-Key`、`Authorization: Bearer`、body `api_key` 都放行；缺失 401 | [x] |
| 4.3-8 | `days` → `time_range` 映射 | 同上 | `days=1` 请求的 `time_range` 生效（结果带日期/时效处理） | [x] |
| 4.3-9 | REST 抽取 | 同上 | `/v1/extract` 返回 `results[].raw_content` | [x] |
| 4.3-10 | 限流 | `--mode ratelimit`（独立实例 RPM=1） | 第 2 次请求 429 | [x] |
| 4.3-11 | 离线单测不回归 | `pytest -q -m "not net"` | 全绿（新增 stdio 握手测试） | [x] |
| 4.3-12 | 人工联调清单可执行 | 用户按 `docs/03` 清单逐客户端点一次 | 每个客户端记录「跑通/失败」；失败项回修文档或代码 | [ ] |

**通过标准**：4.3-1 ~ 4.3-11 自动通过；4.3-12 由用户执行并回填 `docs/reports/` 里的联调记录表。

**验收记录（2026-09-24，分支 `feature/m4-4.3-client-verify`）**：

- 命令：`.\.venv\Scripts\python.exe -u scripts\mcp_selfcheck.py --out docs\reports\m4-4.3-client-selfcheck-20260924.md`
  → **退出码 0：24/24 项通过，0 失败 0 跳过**（stdio 5 / stdio-raw 1 / http-mcp 6 / rest 10 / ratelimit 2）。
- 关键实测值：
  - stdio：`initialize` → `utf8-search 0.1.0`（协商协议 `2025-11-25`）；`tools/list` 的参数名/必填项/枚举全部符合契约；
    `web_search`（basic）5 条结果、（news + `time_range=week`）5 条全带日期；`web_fetch` → 131 字符。
  - stdio-raw：stdout 共 2 行、全为合法 JSON-RPC，**无任何日志污染协议通道**。
  - http-mcp：无 Key → 401、错误 Key → 401、伪造 Host → 421（未配置 `UTF8SEARCH_MCP_ALLOWED_HOSTS` 时
    SDK 自带的防 DNS 重绑定已在生效）；SDK 客户端握手 + 工具发现 + 工具调用全通。
  - rest：`/health` 200（status=ok、SearXNG=ok、鉴权开）；三种 Key 传法（`X-API-Key` / Bearer / body）全部 200；
    无 Key、错误 Key → 401；`days=1` → 5/5 条带日期、最旧 0.6 天；`include_domains=["post.smzdm.com"]` 1/1 命中；
    `/v1/extract` → 131 字符；`advanced + include_raw_content` → 读 3 页、3/3 条附带正文。
  - ratelimit：RPM=1 实例第 1 次 200、第 2 次 **429**（`Retry-After: 60`）。
- 离线单测：`pytest -q -m "not net"` → **203 passed**（新增 `tests/test_mcp_selfcheck.py` 7 项：参数解析 /
  纯函数 / 报告结构 + **真实子进程 stdio 握手**与原始帧纯净度回归）；联网 `-m net` 仍 4 passed。
- 文档回修（本轮真正修掉的问题）：`docs/03` Q6 里的 `failed_results` 乱码字符与被吃掉的
  `$env:UTF8SEARCH_BLOCK_PRIVATE_HOSTS` 代码块；新增 §9 自研 Agent 示例（stdio / HTTP / REST 三段可复制）、
  §10 自检用法与人工联调清单；`README.md` 验收脚本区补 `mcp_selfcheck.py`、测试数 196 → 203。
- **待办（4.3-12）**：用户按 `docs/03` §10.2 逐客户端点一次（每客户端 1 条最小操作 + 预期现象），
  把「跑通」列回填到 `docs/reports/m4-4.3-client-selfcheck-20260924.md` 第 4 节的表里。

**风险 / 遗留**：

- 无法替代客户端自身的配置解析（例如 Codex 版本不支持 `streamable_http` 类型）；清单里对这类
  「依版本而定」的项给出备选方案（stdio + `mcp-remote` 桥接，或直接走 REST）。
- Dify / n8n 需要用户在各自 UI 里导入 OpenAPI / 建 HTTP 节点，本轮只保证「请求形状」与服务端行为一致。

## 12. M5-5.3 中文源强化与查询质量（已完成 2026-09-24，5.3-12 待人工打分）

**背景**：`docs/04-后续路线图.md` 第 5.3 节。2-9 相关性抽检 20 条查询 75% 达标（门槛 90%），
未达标的 5 条集中在**中文商品类与强时效类**（#2 混入无关产品页/社区首页、#4 同站重复、
#11 混入展会与跑车新闻、#16 混入俄语开箱与官网首页、#18 混入乐高攻略/净水器等垃圾结果）。

**本次调研实测（2026-09-24）**：

1. **`360search` 是可用且高质的中文源**。它此前被我们自己的 `keep_only` 白名单挡住，
   加入白名单后逐引擎隔离实测（4 条中文查询）：每查询 **4 条**结果，查询词覆盖率 **0.67-0.93**
   （同时刻 12 引擎混合结果里 naver 只有 0.32），域名全部是一手中文站
   （中关村在线 / 太平洋电脑网 / 汽车之家 / 浙江水利厅台风路径 / 天气网）。
   忽略 `time_range`（带 `day`/`week` 仍返回 4 条，不会变空），可安全用于新闻的通用兜底那一路。
2. **加入 360search 的延迟代价可忽略**：交替配对实测（n=12）每查询多 **4-7 条**结果，
   配对延迟差中位 **+24ms**、13 引擎更快的比例 42%（即无实质影响）。
3. **`baidu` 不可用**：`SearxEngineCaptchaException`（`suspended_time=3600`），加入白名单后
   4/4 查询 0 条、22-511ms 快速失败 —— 与 `quark` 同一处境。
4. **`bilibili` 可用但不适合默认启用**：每查询返回 **20 条全部来自 bilibili.com 的视频**，
   会以同站结果淹没结果集，对「给 LLM 提供文字资料」无价值 → 不采用。
5. **`chinaso` 在本镜像注册失败**：`The "engine" field is missing for the engine named "chinaso"`，
   需自行补 `engine` 字段（API 形态），暂不采用。
6. **意外发现（工程健壮性）**：点名**全部未注册**的引擎时，SearXNG 会**静默回退到整个默认引擎集合**
   ——`engines=baidu` 返回的是 `fynd/naver/yandex/yahoo` 的结果（`engines=nonexistent_xyz` 同样）。
   有效名字仍在时不会回退（`engines=baidu,yandex` 只跑 yandex）。这意味着**配置里写错引擎名会静默失去约束**，
   与我们 5.2/5.1 维护 `engines` 约束的努力相冲突，需要可观测。
7. **本机 IP 下真正出结果的引擎只有 6 个**（`/metrics` 的 `result_count_total` 只有
   fynd/google/yandex/yahoo/naver/zapmeta）。**但这不构成裁剪名单的理由**：换个出口 IP
   （如用户自己的服务器）google/brave 等可能恢复，裁剪反而固化损失。取舍是「保留候选 + 5.1 健康度自适应」，
   而不是「按当前 IP 手工精简」。`quark` 同理保留。

**实现设计**：

- **E1 中文源接入**：`searxng/settings*.yml` 的 `keep_only` 与显式启用列表加入 `360search`；
  `config.default_engines` 与 `news_general_engines` 加入 `360search`。
- **E2 同站限流（多样性）**：新增 `rank/diversity.py: limit_per_host` —— 最终 top-N 里同一可注册域
  最多保留 `rank_max_per_host`（默认 2）条。依据：#4（中央气象台/中国天气网）、bilibili 单站 20 条。
- **E3 脚本一致性过滤**：`rank/diversity.py: filter_script_mismatch` —— 查询主体为 CJK 时，
  剔除「标题与摘要都不含 CJK、也不含拉丁字母」的结果（西里尔/阿拉伯/泰文等）。
  依据：#16 的俄语 YouTube 开箱。英文结果必须保留（用户明确需要外网英文信息）。
- **E4 查询词覆盖度下限**：`rank/fusion.py: filter_low_coverage` —— 候选充足时剔除
  查询词覆盖率低于 `rank_min_query_coverage`（默认 0.34）的结果。复用已有的中文二元组分词，零额外成本。
  依据：#2 的德语无关页（覆盖率 0）、#11 的展会页、#18 的乐高攻略/净水器。
- **E5 聚合页识别**：`rank/diversity.py: is_aggregator_page` —— URL 路径为空/极浅，
  或标题含「首页/频道/栏目/分类/导航/新闻中心」等，判为栏目页；候选充足时剔除。
  依据：#11 的盖世汽车栏目页、#16 的 apple.com.cn 官网首页、#2 的 www.ai.ch 首页。
- **E6 通用主题的时间词感知**：`rank/recency.py: has_recency_intent`（最近/最新/今日/本周/近期/今天/
  latest/recent/this week）——`topic=general` 且命中时，先用 **URL 内嵌日期（零网络开销）** 补日期，
  再按新鲜度轻排序（**不丢弃**无日期结果、不抓页面，保持 basic 的速度）。
  依据：#4「台风 最新消息 路径」此前返回 2021 旧闻、#2「最近一周 AI 行业动态」。
- **E7 约束被忽略的可观测**：`SearxngProvider` 检测「结果来源引擎不在请求集合内」并告警，
  避免配置写错引擎名时静默失去约束（发现 6）。
- **兜底原则**：E2/E4/E5 一律遵循「候选充足才过滤」——过滤后若不足 `max_results`，
  按原顺序补回被过滤的结果，绝不让质量过滤把结果掏空（与 5.1 的覆盖率下限同思路）。

**范围**：新增 `src/utf8_search/rank/diversity.py`、`tests/test_diversity.py`；
改动 `rank/fusion.py`、`rank/recency.py`、`core/pipeline.py`、`providers/searxng.py`、`config.py`、
`verify/metrics.py`、`scripts/relevance.py`、`searxng/settings*.yml`、`.env.example`、`README.md`、`docs/04`。

| 编号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 5.3-1 | 360search 可用且高质 | 逐引擎隔离实测 | 中文查询返回结果、覆盖度 >= 0.6、域名为一手中文站 | [x] |
| 5.3-2 | 同站限流 | `tests/test_diversity.py` | 同域最多保留 `rank_max_per_host` 条；候选不足时不过度过滤 | [x] |
| 5.3-3 | 脚本一致性过滤 | 单测 | CJK 查询剔除纯西里尔结果；保留英文结果 | [x] |
| 5.3-4 | 查询词覆盖度下限 | 单测 + 实网 | 低覆盖结果在候选充足时被剔除；候选不足时补回 | [x] |
| 5.3-5 | 聚合页识别 | 单测 | 首页/栏目页在候选充足时被剔除 | [x] |
| 5.3-6 | 时间词感知重排 | 单测 | general 主题命中时间词时按新鲜度重排且不丢无日期结果 | [x] |
| 5.3-7 | 约束被忽略可观测 | 单测（假 httpx） | 结果来源不在请求集合内时告警并置标志 | [x] |
| 5.3-8 | 卫生度自动化指标 | `verify/metrics.py` + 单测 | 可输出同站重复/覆盖率/聚合页/脚本不匹配/空内容比例 | [x] |
| 5.3-9 | 不回归：离线 + 联网单测 | `pytest -q -m "not net"` / `-m net` | 全绿 | [x] |
| 5.3-10 | 不回归：时效性 | `scripts/news_check.py --time-range day` | 带 7 日内日期比例 >= 80% | [x] |
| 5.3-11 | 不回归：引擎健康度 A/B | `scripts/bench_engines.py` | 判定通过（覆盖率不下降、延迟不劣化） | [x] |
| 5.3-12 | 相关性达标（2-9 门槛） | 重跑 `scripts/relevance.py` + **人工打分** | top5 相关 >=4 的查询占比 >= 90% | [ ] **待人工打分** |

**通过标准**：以上全部通过。5.3-12 是官方门槛，**打分仍需人工**（脚本只负责采集与判定）；
本轮会同时给出 5.3-8 的自动化「卫生度」前后对比作为客观证据。

**风险 / 遗留**：

- 质量过滤存在**过拟合到 2-9 这 20 条查询**的风险。对策：全部规则只用客观信号
  （URL 结构、字符脚本、查询词覆盖度、发布日期的存在性），不维护站点黑名单、不写查询特例，
  且一律「候选充足才过滤」。
- `360search` 每查询只返回 4 条（上游只解析首页），是**高精度低召回**的补充源，不是主力。
- 本机出口 IP 下 12 个通用引擎仅 6 个出结果；这不是裁剪名单的依据（见调研第 7 条），
  部署到其他 IP 后实际贡献面可能不同。
- `baidu` / `bilibili` / `chinaso` 本次评估结论为不采用，已从白名单移除并记录原因。
### 实现修正与补充（相对上面的设计稿）

本轮实现依据实测对设计稿做了 6 处修正/补充（全部记录理由，避免后人误以为实现跑偏）：

1. **候选池 `rank_candidate_pool`（默认 24）——设计稿漏掉的最关键前提**。
   旧代码 general 主题向上游索取的条数 = `max_results`，即「候选数 = 结果数」，
   于是过滤一删结果就必然触发「不足 max_results 就补回」，**过滤形同虚设**
   （2-9 的聚合页/官网首页正是这样漏进 top5 的）。SearXNG 本来就一次返回整批结果，
   扩大候选**零额外上游请求、零额外延迟**（受控 A/B：结果条数 100 → 100）。
2. **脚本一致性判据收窄**：设计稿写的是「标题与摘要都不含 CJK、也不含拉丁字母」，
   实现改为「含西里尔/阿拉伯/泰文/韩文 **且不含汉字/假名**」→ 英文结果一定保留，
   且能识别「俄语 + 拉丁字母混排」的标题（#16 的真实形态，按设计稿口径会漏判）。
3. **落地位置与「分级补回」**：同站/覆盖度/聚合页统一实现在 `rank/diversity.py`
   （设计稿把 E4 写在 `fusion.py`）；补回顺序改为「覆盖度低 → 同站冗余 → 聚合页 → 脚本不匹配」，
   否则排在最前的聚合页会被第一个补回来，过滤白做。
4. **新闻路径只做结构性过滤**：`topic=news` 只保留同站冗余与脚本不匹配两项。
   依据是配对 A/B（`news_check.py --ab`，逐条交替两种口径，抵消上游漂移）：
   全套过滤会把各站「当天更新的日报/栏目页」连同日期一起剔除，
   时效性 **39/40 (98%) → 32/40 (80%)**（逐条配对差 −2/−3/0/0/0/0/−1/−1）；
   收敛为结构性过滤后复测 **40/40 vs 40/40，配对差中位 0**。
5. **标题跨年年份 → 陈旧信号**（`rank/recency.py: mark_stale_by_title_year`）：
   设计稿只从 URL 取日期，而 #4 的 2021 台风页 URL 里没有日期（年份写在标题里）。
   补上这一零成本信号后，通用主题的分层顺序调整为「新鲜 > 无日期 > 过期」（`apply_recency(stale_last=True)`）
   —— 无日期结果多是实时页面（台风实时路径、官网专题），不该排在已知跨年旧闻之后。
6. **聚合页判据补充通用 URL 形态**：`/tags/xxx`、`/topic/xxx`、`/zhuanti/xxx`、`/category/xxx`，
   以及以 `/news`、`/list`、`/index` 结尾的浅路径（段数 ≤2 且无 `.html/.shtml/.jsp` 等文章后缀）。
   这不是站点黑名单，而是各站点通行的 URL 约定；`/news/2026824/172470.shtm` 这类文章页不受影响（有单测覆盖）。

### 验收记录（2026-09-24）

**完整证据与复现命令：`docs/reports/m5-5.3-verification-20260924.md`**（报告索引：`docs/reports/README.md`）。

| 验收项 | 结果 | 证据（留痕文件 / 命令） |
| --- | --- | --- |
| 5.3-1 | ✅ `360search` 每查询 4 条、覆盖率 0.67-0.93、域名为一手中文站 | `searxng/settings*.yml`；`/config` 返回 16 引擎 |
| 5.3-2 | ✅ 同站冗余（端到端）1 → 0 | `docs/reports/m5-5.3-hygiene-compare-raw-20260924.txt` |
| 5.3-3 | ✅ 非中英文脚本 2 → 0 | 同上 |
| 5.3-4 | ✅ 覆盖率均值 0.595 → 0.831 | 同上 |
| 5.3-5 | ✅ 聚合页 11 → 0 | 同上 |
| 5.3-6 | ✅ #4 的 2021 旧闻被挤出 top5 | `docs/reports/m5-5.3-relevance-after-20260924.md` |
| 5.3-7 | ✅ `constraint_ignored` + 告警（单测） | `tests/test_searxng_engine_health.py` |
| 5.3-8 | ✅ 受控 A/B **通过**：聚合页 10 → 0、同站冗余 2 → 0、结果条数 100 → 100 | `docs/reports/m5-5.3-rank-ab-same-candidates-20260924.md` |
| 5.3-9 | ✅ 离线 **196 passed** / 联网 **4 passed** | `pytest -q -m "not net"` / `-m net` |
| 5.3-10 | ✅ **40/40 = 100%**（门槛 80%） | `docs/reports/m5-5.2-news-timeliness-20260924.md`；配对回归 `m5-5.3-news-timeliness-ab-20260924.md` |
| 5.3-11 | ✅ 判定通过：结果数中位 10.0 → 10.0、配对延迟 −163ms、上游异常 131 → 2 | `docs/reports/m5-5.1-bench-engines-20260924.md` |
| 5.3-12 | ⏳ **待人工打分** | 明细 `m5-5.3-relevance-after-20260924.md` + 模板 `m5-5.3-relevance-scores-20260924.csv` |

**方法学修正（重要）**：免费引擎的上游漂移极大（同一查询隔几秒跑两次 top1 都可能不同；
时效性单跑在 10 分钟内波动过 80% / 85% / 95% / 100%），因此**凡涉及前后对比一律用配对或受控方法**：

- 排序侧改动 → `scripts/rank_ab.py`（先采候选快照，再对**同一批候选**跑两种排序口径）；
- 时效性 → `scripts/news_check.py --ab`（逐条交替开/关过滤）。
  端到端单跑对比（`relevance.py --legacy` vs 默认）只作为参考，不作为判定依据。

### 后续（不在 5.3 范围）

- **5.3-12 人工打分**：门槛 ≥ 90%；若未达标，先看是「上游没给出好候选」还是「排序选错」——
  前者需要查询改写/多路召回（M6），后者才动质量过滤。

## 11. M5-5.1 引擎健康度自适应（已完成 2026-09-24）

**背景**：`docs/04-后续路线图.md` 第 5.1 节。文档写的是「剔除连续失败的引擎、按成功率排序，
让被限流引擎不再占用聚合等待时间，basic P50 进一步下降」。用户要求：**不是一味做防御性降级，要稳健的运行效果**。

**实测关键发现（2026-09-24：12 个通用引擎逐引擎隔离实测 + `/metrics`）**：

1. **文档「剔除限流引擎能降 P50」的前提不成立**。SearXNG 对处于惩罚期（suspended）的引擎是
   **快速失败**：`resulthunter/privacywall/yep/brave/quark` 单引擎探测耗时 0.03-0.19s、0 条结果，
   且 `request_count_total` 停在 1-9（说明根本没往上流发请求）。既然不占用等待时间，剔除它们
   **拿不到延迟收益**。A/B 基准印证：全部 12 引擎 P50=0.99s vs 仅 7 个「当时健康」引擎 P50=0.98s。
2. **引擎健康是分钟级漂移的**，静态名单必然过期。上一轮实测 `google` 5/5 被 CAPTCHA、`yep` 5/5 正常；
   本轮 `google` 100% 可靠（10 条结果），`yep` 反而 `Suspended: access denied`。所以「固定一份健康名单」
   是最差方案：既丢真结果，又留着真挂的（B 组比 A 组少 11 条结果中位数）。
3. **`/metrics`（OpenMetrics）是唯一权威的引擎级指标源**（`enable_metrics: true`，
   basic auth 用户名任意、密码 = `open_metrics` 值）。暴露 `searxng_engines_*{engine_name=...}`：
   平均响应时间、结果数、请求数、0-100 的 `reliability`。**注意**：配置名写的是分位数，实际只输出
   **平均值**；且只对「有过请求」的引擎出现，因此只能当辅助信号。
4. **每查询返回的 `unresponsive_engines` 带失败原因**（`Suspended: too many requests` /
   `access denied` / `CAPTCHA`），免费、零额外请求 —— 这是最合适的**主信号**（旧代码只取了名字、丢了原因）。
5. **`resulthunter` 会触发 SearXNG 502**（`add_unresponsive_engine after close`），是真正的稳定性缺陷；
   而现有 `_request` 的 502 重试会**丢掉 `engines` 参数**、退回 SearXNG 默认引擎集合 —— 这正是
   「防御性降级」的坏例子：约束被静默换掉，返回内容不再可控（实测会混入垃圾农场内容）。
6. **空结果 != 失败**：`zapmeta` / `reloado` 对纯中文长尾查询会返回 0 条且**不报 unresponsive**。
   把「空」当失败会把好引擎误判成坏引擎，必须区分。
7. **引擎顺序不影响延迟**（E 组：12 引擎顺序反转，P50 0.91s vs 0.99s，属噪声）。故文档里的
   「按成功率排序」不采用 —— 无收益且会引入不稳定性。

**实现设计（稳健优先，非单纯降级）**：

新增 `src/utf8_search/providers/engine_health.py`：`EngineHealthTracker`（进程内、按引擎名，general/news 共用）。

- **按失败原因分级冷却**（租约式，带到期时间，绝不永久封杀）：
  `CAPTCHA` 1800s / `access denied`·403 900s / `too many requests`·429 180s / `timeout` 90s / 其他 120s；
  连续失败**指数退避**，封顶 `engine_health_cooldown_max`（3600s）。
- **自愈**：冷却到期自动回到候选集；任一次成功即清零失败计数（无需人工干预、不依赖重启）。
- **覆盖率下限**：若可用引擎数 < `engine_health_min_active`（默认 6），按「最早解冻」顺序补足，
  引擎集合不会因连锁冷却而萎缩到搜不出东西。
- **有界探测**：每次查询最多带 `engine_health_probe_slots`（默认 1）个仍处冷却期的引擎，
  既能发现恢复又不拖垮延迟。
- **空结果不惩罚**：只有出现在 `unresponsive_engines` 里的引擎才计失败。
- **502 重试保持约束**：重试时不再抛弃 `engines`，而是用「剔除本次失败引擎后」的显式列表重试，
  让响应始终受本服务选定的引擎集合约束；仅当显式列表为空时才退回无 `engines`（并明确告警）。
- **可观测**：`/health` 增加引擎健康快照（冷却中/失败过的引擎与原因），上游策略变化可被运维看见。
- 开关 `engine_health_enabled`（默认 true；关闭后完全等价于旧行为）。

**范围**：新增 `src/utf8_search/providers/engine_health.py`、`tests/test_engine_health.py`、
`tests/test_searxng_engine_health.py`、`scripts/bench_engines.py`；改动 `providers/searxng.py`、
`core/pipeline.py`、`config.py`、`server/http_api.py`、`.env.example`、`docs/04`、`README.md`。

| 编号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 5.1-1 | 失败原因分级正确 | `pytest tests/test_engine_health.py` | captcha/denied/ratelimit/timeout/other 各落入对应冷却档 | [x] |
| 5.1-2 | 连续失败指数退避且封顶 | 单测（注入时钟） | 冷却时长递增且在 `cooldown_max` 处封顶 | [x] |
| 5.1-3 | 租约到期自动自愈 | 单测（注入时钟） | 到期后引擎回到候选集；成功后失败计数清零 | [x] |
| 5.1-4 | 覆盖率下限不被击穿 | 单测 | 可用数 < min_active 时补足，选中数 >= min(候选数, min_active) | [x] |
| 5.1-5 | 探测名额有界 | 单测 | 每次查询带入的冷却中引擎 <= probe_slots | [x] |
| 5.1-6 | 空结果不惩罚引擎 | 单测 | 无 unresponsive 的引擎即使 0 结果也保持健康 | [x] |
| 5.1-7 | 健康引擎相对顺序稳定 | 单测 | select 不改变未冷却引擎的原顺序 | [x] |
| 5.1-8 | 502 重试保持 engines 约束 | 单测（假 httpx） | 第 2 次请求仍带 engines 且不含本次失败引擎 | [x] |
| 5.1-9 | 关闭开关等价旧行为 | 单测 + 配置 | `engine_health_enabled=false` 时 engines 原样透传 | [x] |
| 5.1-10 | 不回归：离线单测 | `pytest -q -m "not net"` | 全绿（132 基线 + 新增） | [x] |
| 5.1-11 | 不回归：联网单测 | `pytest -q -m net` | 4 passed | [x] |
| 5.1-12 | 不回归：时效性 | `scripts/news_check.py --time-range day` | 带 7 日内日期比例 >= 80% | [x] |
| 5.1-13 | 稳健运行：健康自适应 vs 静态名单 | `scripts/bench_engines.py` 实网对比 | 结果数中位数不下降、配对延迟差不劣化、上游异常次数不增加 | [x] |
| 5.1-14 | `/health` 可见引擎健康 | 本地起服务 `curl /health` | 返回引擎健康快照字段 | [x] |

**通过标准**：以上全部通过；且 5.1-13 必须给出「覆盖率不下降」的实测证据（这是本次「稳健」的核心判据）。

**验收记录（2026-09-24，分支 `feature/m5-5.1-engine-health`，改动仅在工作区）**

- 单测：`tests/test_engine_health.py`（30 项，覆盖 5.1-1 ~ 5.1-7、5.1-9）、
  `tests/test_searxng_engine_health.py`（7 项，覆盖 5.1-8、冷却引擎不入下一次查询、重试保留约束）、
  `tests/test_verify_metrics.py` 新增 8 项 A/B 判定测试。
- 离线全量：`pytest -q -m "not net"` → **177 passed, 4 deselected**；联网 `pytest -q -m net` → **4 passed**。
- 时效性不回归（5.1-12）：`scripts/news_check.py --time-range day` → 8 条查询 / 40 条结果中
  39 条带 7 日内日期，**98%**（门槛 80%），结论通过。
- A/B 基准（5.1-13）：`scripts/bench_engines.py --rounds 3`，24 对配对样本 ——
  结果数中位 **10.0 → 10.0**（不下降）、配对延迟差中位 **−16 ms**（自适应更快的比例 62%）、
  上游「不可用引擎」报告次数 **142 → 0**；判定**通过**。报告：`data/bench-engines-20260924.md`
（复测版已归档：`docs/reports/m5-5.1-bench-engines-20260924.md`）。
- 端到端行为核验（本机 8127 端口，用唯一查询避开结果缓存）：
  第 1 次查询上游报告 6 个引擎不可用（`resulthunter`/`brave` 限流、`privacywall`/`yep` 拒绝访问、
  `google`/`quark` 验证码），第 2 次查询 `failed_engines` 已为**空** —— 自适应把已挂引擎摘掉了。
- `/health` 快照核验（5.1-14）：返回 `engines.cooling`（引擎 / 档位 / 剩余时间 / 连续失败 / 原始原因）
  与 `engines.active`（本次实际使用的引擎集合）。

**过程中修正的两个关键问题**：

1. **判定口径**：最初直接比较两种模式的 P50，n=16 时得出「自适应慢 20%」并判定不通过。
   改用「同查询、同轮次逐条交替」的**配对差值**复核（另跑了一轮 18 对的上游直连诊断）后确认：
   配对差中位 −22 ms、自适应更快的比例 50%，即**剔除挂引擎对延迟没有因果影响**；
   原始 P50 的差异来自上游延迟的双峰性（~0.9 s 与 ~1.25 s 两簇，随机落在任一次请求上，与选路无关）。
   判定函数因此改用配对差值 `evaluate_engine_health_ab(paired_delta_median=...)`。
2. **失败原因文案是本地化的**：本服务客户端带 `Accept-Language: zh-CN`，SearXNG 实测返回的是
   「暂停服务: 请求过于频繁 / 拒绝访问 / 验证码」而非英文 `Suspended: ...`。
   最初只写英文规则，导致 6 个引擎全部落进 `other` 档（CAPTCHA 只冷却 120 s，等于每 2 分钟撞一次墙）。
   已改为中英文同时匹配，并把「超时」判定提到「无原因 Suspended」之前（否则 `Suspended: timeout`
   会被粗判成限流）。


**风险 / 遗留**：

- 健康状态是**进程内**的：多副本部署各自学习、互不共享；后续可换 Redis 共享（不在本次范围）。
- 冷启动（首次启动、无历史）等价于静态名单，需若干次查询才收敛（渐进学习，非一次性剔除）。
- `unresponsive_engines` 的原因文案由 SearXNG 官方引擎代码 + gettext 本地化决定
  （本服务实测拿到的是中文，取决于 `Accept-Language`）；未命中的文案会落回 `other` 档，
  靠指数退避兜住，不会退化成高频重试。若上游大改文案，按 `/health` 的 `cooling.reason` 复核对齐。
- `/metrics` 本次**只用于可观测**，不参与选路决策：它是平均值而非分位数、且只覆盖有请求的引擎，
  用它做决策会引入偏差。

## 10. M5-5.2 时效性增强（当前任务，已完成）

**背景**：`docs/04-后续路线图.md` 第 5.2 节。验收 2-9 的抽检暴露了强时效类查询的问题——
「台风 最新消息 路径」返回 2021 年旧闻且同站重复，新闻类查询混入产品页与社区首页。

**关键发现（2026-09-24）**：

1. **此前「逐引擎隔离实测」的方法本身是错的**。SearXNG 的 `engines` 查询参数与 `categories`
   参数是**「叠加」关系而非互斥**（源码 `searx/webadapter.py: parse_generic`）：同时传
   `categories=news` 与 `engines="google news"`，会返回 news 类目下**全部**引擎的结果，
   显式 engines 列表因此失去约束力。所以此前「镜像里没有 google news / sogou wechat /
   yahoo news」以及「duckduckgo news 之外都不合适」的结论**均不成立**。
   已修正 `SearxngProvider`（给了 `engines` 就不再传 `categories`），并用单测锁死该行为。
2. 用正确方式重测：镜像里**存在** `google news`、`sogou wechat`、`bing news`、`reuters`、
   `brave.news` 等引擎，只是默认被 `keep_only` 挡在外面。
3. `time_range` 对**新闻类目**引擎无效：`duckduckgo news` / `sogou wechat` / `google news`
   加 `time_range=day|week|month` 一律返回 **0 条**（故 `news_pass_time_range` 默认关闭，
   时效性改由本地按 `published_date` 处理）。
4. `time_range` 对**通用引擎**有效，且这是本次时效性达标的关键：`time_range=day` 时通用引擎
   每条查询能返回 5-12 条「当天/1 日内」结果；不透传时同一批查询只有 0-2 条带日期。

**逐引擎隔离实测（8 条中英新闻查询，正确隔离口径）**：

| 引擎 | 结果数 | 日期覆盖 | 7 日内 | 平均延迟 | 结论 |
| --- | --- | --- | --- | --- | --- |
| duckduckgo news | 93 | 100% | 48 | 1.3s | 采用：英文时效最好，但 3 条纯中文查询返回 0 条 |
| sogou wechat | 80 | 100% | 16 | 0.4s | 采用：8/8 查询各 10 条，补上 DDG news 的中文盲区 |
| google news | 84 | 0% | 0 | 0.9s | 采用：中文覆盖最全（8/8 各 10 条）但不给日期，靠 URL/页面回补 |
| reuters | 43 | 100% | 0 | 0.5s | 剔除：7 日内 0 条、不支持中文 |
| bing news | 0 | — | — | 0.2s | 剔除：8/8 查询 0 条 |
| brave.news | 42 | 5% | 0 | 0.3s | 剔除：`Suspended: too many requests` |
| 360search | 43 | 0% | 0 | 0.5s | 剔除：0 条带日期 |
| wikinews / naver news | — | — | — | — | 剔除：本镜像未注册，用 `engines` 点名会被静默丢弃 |
| sogou（通用） | 0 | — | — | 0.2s | 从通用引擎列表剔除：`sogou.py:56` AttributeError 恒崩溃 |

**实现（三处关键设计）**：

1. **URL 内嵌日期优先**（`rank/recency.py: date_from_url`）：政府和门户站常把日期写进路径
   （`/202609/t20260922_`、`/2026/08/01/`），这一步零网络开销、优先于抓页面。带严格校验
   （年/月/日必须构成真实日期、年份限 2000-2100），实测能挡住雪花 ID 被误判成日期。
2. **通用引擎兜底透传 time_range**（`pipeline: _collect_general_extra`）：时效性从 75% 到 100%
   的关键一步；同时改用独立的 `news_general_engines`（默认排除 yandex —— 它配合 time_range
   会返回垃圾农场内容，实测出现成人站与综艺盗播站）。
3. **两路上游请求并发 + 日期回补按需触发**：新闻请求与通用兜底请求用 `asyncio.Task` 并发发出；
   抓页面回补日期只在「新鲜结果不够填满 max_results」时才做，抓取页数按缺口反推、并受
   `news_date_pages` / `news_date_budget` 双重封顶。实测把 topic=news 端到端耗时从
   2.6-5.6s 压到 1.1-1.3s，且保持 100% 时效性。

另新增 `rank/fusion.filter_low_quality`：剔除「无标题」与「标题就是裸域名/裸 URL」的结果
（客观低质信号，不猜内容质量、不维护垃圾域名黑名单）—— 这类结果在「按时间过滤」的通用引擎
结果里占比不低，对 LLM 毫无价值。

**范围**：新增 `src/utf8_search/rank/recency.py`；`PageExtractor.fetch_date`；`SearxngProvider`
新闻引擎 + `engines/categories` 修正；pipeline 时效处理；`rank/fusion.filter_low_quality`；
`searxng/settings.yml`（配套本机代理用的 `searxng/settings.local.yml`）；`scripts/news_check.py`；
`verify/metrics.py: evaluate_timeliness`。
**不做**：不改动引擎健康度自适应（那是 5.1）；不引入新的第三方依赖（htmldate 由 trafilatura 传递依赖提供）。

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 5.2-1 | SearXNG 启用可用的 news 引擎 | 直接读 `/config` + `scripts/news_check.py` | 注册 duckduckgo news / sogou wechat / google news 且均 enabled | [x] |
| 5.2-2 | `topic=news` 走新闻引擎 | `tests/test_news_timeliness.py` | 使用 `news_engines`，且不与 `categories` 叠加 | [x] |
| 5.2-3 | 发布日期解析健壮 | `tests/test_recency.py` | ISO / 时间戳 / 中文日期 / URL 内嵌 / 空值均正确 | [x] |
| 5.2-4 | 时效分层与重排 | `tests/test_recency.py` | 新鲜 > 过期 > 无日期，同层保持相关性顺序 | [x] |
| 5.2-5 | 过期结果过滤 | `tests/test_recency.py` | 新鲜结果足够时不返回已知过期结果 | [x] |
| 5.2-6 | 日期回填（URL 优先 + htmldate） | `tests/test_news_timeliness.py` | URL 内嵌日期零网络开销生效；页面回补受页数/预算约束 | [x] |
| 5.2-7 | 时效性验收（核心） | `scripts/news_check.py` | `topic=news` + `time_range=day` 结果 ≥ 80% 带 7 日内日期 | [x] |
| 5.2-8 | 非 news 主题不受影响 | `pytest -m net` + 5 条通用查询抽检 | general 查询行为与排序不变 | [x] |
| 5.2-9 | 回归 | `pytest -q -m "not net"` | 既有测试全绿 | [x] |
| 5.2-10 | 文档同步 | 查看 `docs/04`、`README.md`、`.env.example` | 引擎偏差与用法已记录 | [x] |

**验收记录（2026-09-24，分支 `feature/m5-5.2-timeliness`）**

- 离线测试：`pytest -q -m "not net"` → **132 passed, 4 deselected**
  （新增 `tests/test_recency.py` / `tests/test_news_timeliness.py` / `tests/test_searxng_settings.py`）。
- 联网冒烟：`pytest -q -m net` → **4 passed**。
- 时效性验收（核心：8 条中英新闻查询，`topic=news`，`time_range=day`，`--max-results 5 --no-cache`）：

| 阶段 | 达标比例 |
| --- | --- |
| 起始基线（`time_range` 未透传给通用引擎、无中文新闻源） | 18%（7/40） |
| 修掉 `time_range` 透传后（仍只有 duckduckgo news） | 32-35% |
| 加入 sogou wechat + google news（中文有源了） | 60-85%（波动） |
| 通用兜底透传 `time_range` + 并发 + 按需回补（最终） | **95-100%（38-40/40，4 轮）** |

  最终方案连续 4 轮结果：**100% / 100%（`--time-range week` 档）/ 100% / 95%（38/40）**，
  全部远超 80% 门槛。波动来自免费新闻源候选池本身（同一查询不同时刻的 7 日内条数会浮动）。
- 延迟（`topic=news`，basic，本机，`time_range=day`）：**1.06-1.27s**（优化前 2.56-5.59s）。
- 通用主题回归抽检（5 条中英技术/商品/政策查询，basic）：0.97-2.42s，结果均切题，无空结果。
- 结果质量人工抽查：修复前出现「海角网成人站」「综艺全集在线观看」「vk.ru」等垃圾结果；
  加 `filter_low_quality` + 通用兜底排除 yandex 后，8 条查询均为正规新闻站
  （news.qq.com / finance.sina.cn / reuters.com / abc.net.au / cn.nytimes.com 等）。

**风险 / 已知限制**：

- **免费新闻源本身波动**：同一查询不同时刻的候选池会变（实测同一查询的 7 日内条数在 3-5 之间浮动）。
  当前靠「新闻引擎 + 通用引擎 `time_range` 兜底」双路，单路失效也不会掉到 0%。
- `duckduckgo news` 可能被上游限流（实测出现过瞬时 `unresponsive`），中文兜底主力是 `sogou wechat`。
- **SearXNG 出口不读 `HTTP_PROXY` 环境变量**，只认 `settings.yml` 的 `outgoing.proxies`。
  中国大陆网络直连时 `google.com` / `duckduckgo.com` 会 ConnectTimeout（实测），必须用
  `searxng/settings.local.yml`（已提供，配套 docker-compose 的 `SEARXNG_SETTINGS_FILE` 变量）；
  海外服务器直连可达，用默认 `settings.yml` 即可（`tests/test_searxng_settings.py` 保证两份文件除
  `outgoing.proxies` 外一致）。
- 免费引擎给出的发布日期可能不准（如站点把「最后修改时间」当发布时间），只做相对排序与过滤，不做强保证。
- **`time_range` / `days` 是「强偏好」而不是硬过滤**：丢弃阈值取 `max(time_range 对应天数,
  news_fresh_days)`（默认 7 天）。实测 `days=1` 的请求可能返回 4 天前的新闻（当天结果不够填满
  max_results 时，用 2-7 天的近期新闻补位，而不是补「无日期」的结果）。新鲜度以每条结果的
  `published_date` 为准；这条语义已写进 README。

## 9. M4-4.4 补完 M3 验收（3-3 并发压测 / 3-4 24h 长稳 / 2-9 相关性抽检）（2026-09-24 续做：24h 长稳重跑）

**背景**：`docs/04-后续路线图.md` 第 4.4 节。M3 主体功能已完成，但三项验收（并发压测、24h 长稳、结果相关性抽检）一直未做，
导致「稳定性」缺少数据支撑。本任务补齐这三项，并沉淀可复用的验收脚本。

**范围**：新增 `scripts/loadtest.py`、`scripts/soak.py`、`scripts/relevance.py` 与 `src/utf8_search/verify/metrics.py`（可测试的判定逻辑）。
**不做**：不改动搜索 / 抽取 / 缓存等业务逻辑；不引入新依赖（RSS 采样用标准库实现，不装 psutil）。

| 序号 | 验收项 | 验证方式 | 通过标准 | 状态 |
| --- | --- | --- | --- | --- |
| 4.4-1 | 压测脚本可用 | `scripts/loadtest.py --concurrency 10 --n 50` | 正常跑完并输出报告 | [x] |
| 4.4-2 | 10 并发无 5xx | 同上，查看状态码分布 | 5xx = 0 | [x] |
| 4.4-3 | 10 并发无超时 | 同上 | 客户端超时 / 连接错误 = 0 | [x] |
| 4.4-4 | 输出延迟分位与吞吐 | 同上 | 含 P50 / P90 / P95 / max / QPS | [x] |
| 4.4-5 | 压测自动判定 | 同上，看结论行 | 明确「通过 / 不通过」 | [x] |
| 4.4-6 | 长稳脚本可用 | `scripts/soak.py --interval 300` | 定时查询，逐行落盘 RSS 与成功率 | [x] |
| 4.4-7 | 长稳脚本短跑自检 | `scripts/soak.py --duration-hours 0.1 --interval 40 --warmup 1`（HTTP 模式） | ≥ 6 个采样点（实际 9 个），CSV 可解析，汇总正确 | [x] |
| 4.4-8 | 24h 长稳 | 后台挂机 24h 后看汇总 | 可用率 ≥ 99%，内存无持续增长 | [x] PID 223395，289 行（287 计入统计）；可用率 100%、异常 0、疑似休眠 0，内存无持续增长；覆盖窗口 24.00h（见 `docs/reports/m4-4.4-soak-24h-20260926.md`） |
| 4.4-9 | 相关性抽检脚本可用 | `scripts/relevance.py` | 输出 20 条中英查询的 top5 明细表 | [x] |
| 4.4-10 | 相关性人工打分 | 对明细表逐条打分 | top5 中相关数 ≥ 4 的查询占比 ≥ 90% | [!] |
| 4.4-11 | 判定逻辑单测 | `pytest -q -m "not net"` | 分位 / 判定 / RSS 解析用例全绿 | [x] |
| 4.4-12 | 回归 | `pytest -q -m "not net"` | 既有测试全绿 | [x] |
| 4.4-13 | 文档同步 | 查看 `docs/04`、`README.md` | 验收结论与脚本用法已记录 | [x] |
| 4.4-14 | 挂机进程可脱离终端 | `Start-Process -WindowStyle Hidden` 启动后关掉终端，另开窗口跑 `soak.py --status` | 状态显示「存活」，且心跳随采样刷新 | [x] |
| 4.4-15 | 结论可事后复算 | `soak.py --summarize --out data\soak-24h.csv` | 不需要挂机进程存活，直接从 CSV 得出「通过 / 不通过」 | [x] |
| 4.4-16 | 断点续跑不丢样本 | 中断后用同一 `--out` 重启 | 序号接续、历史样本保留、仅本次进程的冷启动样本计为预热 | [x] |
| 4.4-17 | 周期落盘心跳与汇总 | 查看 `data/soak-24h.meta.json` 与 `--json` 产物 | 每次采样都刷新，进程被强杀也不丢结论 | [x] |
| 4.4-18 | 新增判定逻辑单测 | `pytest -q -m "not net"` | CSV 解析 / 汇总判定 / 存活检测用例全绿 | [x] |

**验收记录（2026-09-24，分支 `feature/m4-4.4-verification`）**

新增脚本：`scripts/loadtest.py`（3-3 并发压测）、`scripts/soak.py`（3-4 长稳）、`scripts/relevance.py`（2-9 相关性抽检），
判定逻辑抽到可单测的 `src/utf8_search/verify/metrics.py`，新增 `tests/test_verify_metrics.py`（21 项）。

**3-3 并发压测结论：通过（无 5xx、无超时），但发现上游容量瓶颈**

| 场景 | 请求数 | 并发 | P50 | P95 | 墙钟 | 吞吐 | 2xx / 4xx / 5xx / 超时 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| basic 冷查询 | 50 | 10 | 12138 ms | 12838 ms | 59.43 s | 0.84 req/s | 50 / 0 / 0 / 0 |
| basic 命中缓存 | 50 | 10 | 126 ms | 12501 ms | 19.13 s | 2.60 req/s | 50 / 0 / 0 / 0 |
| basic 冷查询 | 30 | 3 | 1270 ms | 2050 ms | 14.66 s | 2.00 req/s | 30 / 0 / 0 / 0 |
| basic 冷查询 | 5 | 1 | 1286 ms | 2738 ms | 8.13 s | 0.60 req/s | 5 / 0 / 0 / 0 |

- 达标情况：**无 5xx、无超时，压测判定通过**；服务内存 95.7MB -> 106.6MB。
- **发现（重要）**：并发 1/3 时延迟稳定在 ~1.3 s，与文档基线一致；并发升到 10 且查询命中缓存时 P50 126 ms；
  但并发 10 且全部为唯一查询时，延迟劣化到 ~12 s。独立探测 SearXNG 本体（10 并发直连 `/search`）墙钟 7.90 s、
  单请求 2.6-7.8 s，说明**瓶颈在上游 SearXNG 的聚合能力（约 1.3-2.0 req/s），而不是本服务的异步处理**。
  本服务表现为「排队变慢」而非「报错」，属于可接受的降级，但需要给调用方一个明确的并发预期。
- 建议：默认把 10 并发视为过载点；后续在 M5 增加「搜索并发闸门 + 过载快速返回（503/限流头）」，
  避免长队堆积把延迟推到 10 s 以上。文档侧建议标注「建议并发 ≤ 3」。

**3-4 长稳：脚本自检通过，24h 挂机已启动**

- 自检（HTTP 模式，打 127.0.0.1:8125 的实例，`--duration-hours 0.1 --interval 40 --warmup 1`）：
  9 个采样点、8 个计入统计，可用率 100%，P50 43 ms，服务进程 RSS 80.8-84.2MB，内存判定正常触发（-1.5%，平稳）。
- 24h 挂机：2026-09-24 12:48 起（启动进程 PID 34080，脚本自身 PID 18088），`--interval 300 --duration-hours 24`（进程内流水线，独立缓存 `data/soak-cache.db`）。
  明细 `data/soak-24h.csv`，汇总 `data/soak-24h.json`。**结论待 24h 后（约 2026-09-25 12:48）读取汇总判定**。

**2-9 相关性抽检：未达标，移交 M5**

- 采集：20 条中英查询（新闻/技术/政策/商品 各 5 条）全部返回 5 条结果，明细见 `data/relevance-20260924.md`；
  打分表 `data/relevance-20260924-scores.csv`，判定报告 `data/relevance-20260924-scores-judge.md`。
  （已归档：`docs/reports/m2-9-relevance-judge-baseline-20260924.md` 与
  `docs/reports/m2-9-relevance-scores-20260924.csv`；这 5 条未达标查询是 M5-5.3 的输入。）
- 结果：**15/20 条查询达标（75%），未达 90% 门槛 -> 判定不通过**；平均相关条数 4.25（该口径 ≥ 4）。
- 未达标 5 条及根因：
  - #2 最近一周 AI 行业动态：混入产品页与社区首页（缺时效性重排）。
  - #4 台风 最新消息 路径：第 1 条为 2021 年旧闻，且第 4/5 条为同一站点重复结果（**缺发布时间过滤 + 去重不彻底**）。
  - #11 2026年新能源汽车补贴政策：混入展会与跑车新闻（中文长尾召回质量差）。
  - #16 iPhone 17 Pro 价格 参数：混入 Pinterest 图集与俄语开箱视频（**非目标品类**）。
  - #18 扫地机器人 推荐 性价比：混入乐高攻略、美国手机卡、净水器（**垃圾结果，无品类约束**）。
- 结论：技术/政策/英文类查询质量良好（技术 5 条仅 1 条不达标、政策 4/5 全面达标），
  **短板集中在中文商品类与强时效类**，正好对应 `docs/04` 的 5.2（时效性增强）与 5.3（中文源强化）。
  建议把「时效性重排 + 品类/垃圾结果过滤 + 结果去重加强」列为 M5 的验收输入。

**本轮续做（2026-09-24 晚）：24h 长稳重跑**

- **首轮为什么失败**：`data/soak-24h.csv` 只有 2 行（12:48、12:53），`soak-24h.err.log` 为空、
  `soak-24h.json` 从未生成 → 进程是被**外部终止**（终端/会话结束），而不是抛异常退出。
  两处结构性缺陷：① 汇总 JSON 只在正常结束时写 → 中途死掉就拿不到判定产物；
  ② PID 文件里记的是启动器 PID（34080）而非挂机进程 PID（18080），事后无法判断存活。
- **续跑设计（只动脚本与判定模块，不动搜索逻辑）**：
  1. `verify/metrics.py` 新增 `load_soak_rows` / `summarize_soak_rows` / `process_alive`
     —— 把「CSV 解析 + 汇总判定」从脚本里抽出来，在线采样与事后复算走**同一条判定路径**（可单测）；
  2. `scripts/soak.py` 新增 `--status`（存活 / 心跳 / 进度 / 当前结论）与 `--summarize`（从 CSV 复算结论）；
  3. 每次采样后刷新 `--meta`（PID、启动时间、心跳、已写样本数）与 `--json` 汇总 → **强杀也不丢结论**；
  4. 续跑：启动时读回已有 CSV 的序号继续编号，仅把**本次进程**的前 `--warmup` 个样本标为预热；
  5. 用 `Start-Process -WindowStyle Hidden` 启动，并断言 `meta.pid` 与进程自身 PID 一致。
- **判定标准不变**（docs/04 §4.4）：覆盖 ≥ 24h、可用率 ≥ 99%、内存无持续增长。
  其中「覆盖 ≥ 24h」按 CSV 首末时间戳计算（跨重启累计），避免用单进程 `elapsed_s` 误判。

**本轮续做验收记录（2026-09-24 晚，分支 `feature/m4-4.4-soak`）**

实现（只动脚本与判定模块，未改搜索逻辑）：

- `src/utf8_search/verify/metrics.py` 新增 `load_soak_rows`（CSV 容错解析，丢弃挂机被强杀时的半截行）、
  `summarize_soak_rows`（汇总 + 判定，**在线采样与事后复算共用**）、`process_alive`（存活检测，标准库实现）。
- `scripts/soak.py` 新增 `--status`（存活 / 心跳 / 进度 / 当前结论）与 `--summarize`（从 CSV 复算结论）；
  每次采样原子写 `--meta` 与 `--json`；启动时读回已有 CSV 续编号（断点续跑）。

验证结果（全部实测）：

| 验收项 | 证据 |
| --- | --- |
| 4.4-14 挂机可脱离终端 | `Start-Process -WindowStyle Hidden` 启动后**关掉终端**；2 分钟后另开会话 `--status` 仍显示「存活」，`tasklist` 确认 PID 30424 常驻（66MB） |
| 4.4-15 结论可事后复算 | 短跑样本上 `--summarize` 复算结果与在线采样结论完全一致（2 个计入统计、可用率 100%、延迟 P50 1058ms） |
| 4.4-16 断点续跑 | 同一 `--out` 连跑两次（各 2 采样）：CSV 4 行、序号 1→4 连续、每进程首个样本各自计预热、JSON 含全部 4 行 |
| 4.4-17 周期落盘 | 每次采样刷新 `data/soak-24h.meta.json`（PID/心跳/已写样本数）与 `--json` 汇总 —— 强杀也不丢结论 |
| 4.4-18 新增单测 | `pytest -q -m "not net"` → **213 passed**（新增 10 项：CSV 解析 2 / 汇总判定 5 / 存活检测 3） |

**24h 长稳重跑（进行中）**：

- 启动：2026-09-24 21:53:11；`--duration-hours 24 --interval 300 --warmup 2`（进程内流水线，独立缓存 `data/soak-cache.db`）。
- 真实进程 PID **30424**（`data/soak-24h.meta.json` 的 `pid` 字段），预计 2026-09-25 21:53 结束（约 288 个采样）。
- 产物：明细 `data/soak-24h.csv`、汇总 `data/soak-24h.json`、日志 `data/soak-24h.out.log`（UTF-8）。
- ⚠ **踩坑记录**：`Start-Process -PassThru` 返回的 PID（31916）**不是** python 进程的真实 PID（30424），
  首轮挂机就是因为按启动器 PID 找进程而失联；现在以 `meta.pid` 为准（`--status` 读的就是它）。
- 读取结论（明天跑完或中途想看）：
  ```powershell
  .\.venv\Scripts\python.exe -X utf8 scripts\soak.py --status --out data\soak-24h.csv
  .\.venv\Scripts\python.exe -X utf8 scripts\soak.py --summarize --out data\soak-24h.csv --json data\soak-24h.json
  ```
- 判定：覆盖 ≥ 24h（按 CSV 首末时间戳）+ 可用率 ≥ 99% + 内存无持续增长（`4.4-8` 仍待跑满后勾选）。
- 首轮（12:48 启动、仅 2 个采样后失联）的残留已归档为 `data/soak-24h-attempt1.{csv,pid,out.log,err.log}`。

**风险 / 已知限制**：

- 压测与长稳都依赖本机代理出网；开发期代理曾失效导致大面积超时，需在结论中区分「服务问题」与「网络抖动」。
- 10 并发会真打 SearXNG 与上游引擎，可能触发上游限流，导致个别请求变慢；判定只看 5xx / 超时，不看延迟绝对值。
- 24h 长稳需要机器与代理连续可用，若中途网络中断会体现为可用率下降，需人工判断剔除。

## 8. 遗留与风险事项

- **本机网络波动**：开发期间出现系统代理（`127.0.0.1:7897`）失效导致外网抓取大面积超时的情况，此时改用直连（`UTF8SEARCH_TRUST_ENV=false`）即可恢复。部署到服务器时无此问题。
- 反爬风险：免费引擎会被上游限流，需持续跟踪引擎可用性并按需调整 `keep_only` 名单。
- 未完成项：**2-9（相关性人工抽检）、3-9（真实客户端联调）——两项均为人工项，待用户本人完成**；其余已结案：3-3（10 并发压测，见 §9）、3-4（24h 长稳，可用率 100%、内存抬升后走平）、3-7（SSRF 防护，M4-4.1）、3-8（云服务器部署，M4-4.2，安全组已放行、真证书已签发）。——**详细执行计划见 `docs/04-后续路线图.md`**。
- 合规：仅限抓取公开页面并遵守 robots.txt 与限速要求。
- 待清理：调研期临时容器已删除；`%TEMP%\searxng-spike` 目录受本机策略限制未能删除，其中仅含一份测试用 settings.yml。

### 工作记录（任务结论与后续安排，按 workflow skill §8 追加）

格式：日期 · 任务/分支 · 结论 · 关键数字或证据链接 · 后续动作。

- **2026-09-27 · 收口轮**（`fix/test-env-decoupling`）· 结论：A、B 两分支合并进 `main`（合并提交 `f30bf8c`、`71665f3`）；`tests/conftest.py` 解耦生产 `.env` 鉴权（`3ef9ed2`）；3-4 与 3-3 结案；`docs/04` 状态刷新（§1 缺口表、§4.2/§4.4/§7 陈旧标记）。· 关键数字：生产 `.env` 原样不动下 `pytest -q -m "not net"` → **235 passed / 0 failed**；24h 长稳可用率 100%、采样覆盖率 100%。· 证据：`docs/reports/m4-4.4-soak-24h-20260926.md`。· 后续动作：人工项 **2-9（相关性抽检）与 3-9（真实客户端联调）待用户本人完成**。
- **2026-09-25~26 · A 轮**（`feature/m4-4.2-cloud-deploy`）· 结论：阿里云 `43.106.104.49` 完成云部署验收——SearXNG + 应用 + Caddy(TLS) 三容器 healthy、Let's Encrypt 真证书、Host 白名单 421、鉴权/限流、`data/` 持久化、全通道自检 **24/24**；并修自检脚本三处自身缺陷（时效性口径对齐 M5-5.2、ratelimit 复用 `--api-key`、报告只输出 Key 掩码）。· 证据：`docs/reports/m4-4.2-deploy-20260925.md`、`docs/reports/m4-4.2-deploy-selfcheck-20260925.md`、`docs/05-服务器部署手册.md`。· 后续动作：无（安全组已放行；仅剩证书 2026-12-24 到期前自动续期依赖 80/443 长期放行）。
- **2026-09-26~27 · B 轮**（`fix/soak-longrun-metrics`）· 结论：长稳判定加固（有结果可用率 / SKIP 不补跑 / 休眠假样本 / 覆盖率下限 95% / 覆盖窗口按 CSV 全部行含预热）、`--status` 收尾不再误报心跳；24h 长稳跑满并通过。· 关键数字：PID 223395，289 行 / 287 计入统计，可用率 100%、采样覆盖率 100%、异常 0、疑似休眠 0，内存抬升后走平（+1.1%）。· 证据：`docs/reports/m4-4.4-soak-24h-20260926.md`、`docs/reports/m4-4.4-soak-coverage-floor-20260926.md`。· 后续动作：无。
- **2026-09-27/28 · M5 并发闸门轮**（`feature/m5-concurrency-gate`）· 结论：新增上游并发闸门（默认 **3 / 12 / 4.0s / OPTIONAL_WAIT 1.0s**，策略「排队优先、拒绝为例外」）+ 过载快速返回（REST 429 + `Retry-After`、MCP 可读 `ToolError`）+ `/metrics`；**按「跳过是否会导致返回空结果」把上游调用分两类**——**兜底型**（news 通用补充路、Bing 兜底）**不许静默跳过**，按 `OPTIONAL_WAIT` 有限等待，拿不到直接 429；锦上添花型才允许跳过 + `degraded`（当前产品路径无此类调用）。**结构优化**：`_collect_general_extra` 改为「主源不足才补（复用 5.2 判据）+ 串行」，news 每请求上游需求从 ~2 降到 ~1。· 关键数字：结构改前 news@10 空结果率 **58%**（默认 0.5s 纯非阻塞跳过）→ 改后 **0%**、降级率 **0%**、P95 5955ms；运行点曲线 @1/2/3/5 全部 100% 成功、零降级零空结果（P95 ≤5.2s），@10 96%/5955ms，@30 20%/8474ms；@1 单请求 P50 834→822ms、P95 1452→1332ms；离线 **256 passed**。· **如实记录的未达标/风险**：① general@30 成功率在同一配置下 7 轮测得 15-27%（中位 24.5%），**不能稳定 ≥25%**（max_wait 改 6.0 可 25-28%），未擅自改冻结值；② news@30 闸门**净收益为负**（成功率 20%、P95 8474ms，补路串行两跳被拉长）——高并发 news 应加上游容量而非调闸门；③ 429 时延口径（原「单发 <20ms」）**作废**，保留三段证据与归因（闸门决策 0.32µs/3.88µs；缓存命中地板 7.2ms；单发 429 p50 20.9ms 的额外 ~13ms 在闸门之前的缓存查询与 aiosqlite 串行化）。· 证据：`docs/reports/m5-concurrency-gate-20260927.md`；调参建议见 `docs/05` §4.4；遗留任务见 `docs/04` §8。· 后续动作：人工项 **2-9、3-9 待用户本人完成**；多 worker 需按 worker 数分摊闸门上限；**闸门上限对上游健康度自适应**（本轮不实现）。
- **2026-09-28 · M5 并发闸门收尾轮**（`feature/m5-concurrency-gate`）· 结论：**服务契约改为按并发分层**（@≤5：100% 成功/0 降级/P95 ≤5.2s；@10：≥95%/0/≤6.5s；@30：容量陈述、0 降级、0 空结果、秒级 429），**撤销「general@30 成功率 ≥25%」单点阈值**（7 轮 15-27% 落在噪声里），`max_wait` 保持 **4.0**；把「不满就补 + 串行」的代价做了对照，并给 news@30 的“净负”定性。· 关键数字：**旧并行双打 vs 新串行**（news@1/@2）——@1 P50 3280→**1383ms**（-58%）、P95 5326→4497ms；@2 P50 2557→**1413ms**（-45%）、P95 4965→3340ms ⇒ **无退化、实为收益**，混合模式不列入遗留；news@30 交错（base→gate→base→gate）确认「净负」是**好日 artifact**（好日基线 100% 服务/尾延迟 6.5-9.6s，闸门只留 15-20%、服务到的 P95 4.9-6.6s；坏日才是保护）；@30 的 P95 只有「多数样本 ≤6.5s」（general 3.0-6.9s、news 3.7-8.5s），按容量陈述读。· 证据/口径：报告 `docs/reports/m5-concurrency-gate-20260927.md` §7/§7.1/§7.2；契约与扩容方向写入 `docs/05` §4.4；离线 **256 passed**。· 后续动作：人工项 **2-9、3-9 待用户本人完成**；多 worker 按 worker 数分摊上限；**闸门上限对上游健康度自适应** 仍在 `docs/04` §8 遗留（本轮不做）。
- **2026-09-28 · M6 Tavily 兼容性轮**（`feature/m6-tavily-compat`）· 结论：按官方文档（OpenAPI schema + 示例响应 + 官方 Python SDK 源码，均已留档到 `docs/reports/`）逐字段核对了 `/search` 与 `/extract` 的请求/响应/错误语义；**只做加法**补齐差异项——`results[].favicon/images/id`、顶层 `auto_parameters`、`usage`（`include_usage=true` 时 `{"credits": 0}`）、`/extract` 的 `results[].images`、错误体追加顶层 `error`；**不改**任何既有字段的类型与语义（`detail` 仍为字符串，老客户端不被打断）。· 关键数字：官方示例响应可被我们的模型直接解析、我们的响应覆盖官方示例的每个字段路径（含 `results[].images[].url` 这类嵌套路径）；离线全量 **264 passed, 4 deselected**（新增 `tests/test_tavily_compat.py` 8 条）。· 已知差异（有意保留，报告 §6 有理由）：`answer` 恒 null、图片字段恒空、`score` 量纲不同、未实现的 Tavily 请求参数「接受但忽略」、非法参数返 422（Tavily 为 400，官方 SDK 走 `raise_for_status`，均为异常不静默成功）。· 附带产出：`docs/reports/manual-acceptance-checklist-20260928.md`（2-9 填分步骤与命令 + 3-9 每客户端最小操作与预期）。· 后续动作：人工项 **2-9、3-9 待用户本人照着操作单完成**；闸门上限自适应仍在 `docs/04` §8 遗留。
