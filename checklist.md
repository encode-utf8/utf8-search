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
| 3-3 | 并发压测 | 10 并发查询 | 无 5xx、无超时 | [ ] |
| 3-4 | 连续运行稳定性 | 连续运行 24 h 定时查询 | 无线程/内存泄漏，可用率 ≥ 99% | [ ] |
| 3-5 | 可观测性 | 查看响应字段与日志 | 每次请求含耗时、读页数、命中来源与失败引擎 | [x] |
| 3-6 | 客户端接入文档 | 按文档配置 | Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent 均有配置示例 | [x] |
| 3-7 | SSRF 防护 | 向 `/v1/extract` 传内网地址 | 被拒绝，不发起请求 | [ ] |
| 3-8 | 云服务器部署 | Linux + `docker compose up -d` | 双容器健康，HTTPS + 鉴权可用 | [ ] |
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

## 11. M5-5.1 引擎健康度自适应（当前任务）

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
  上游「不可用引擎」报告次数 **142 → 0**；判定**通过**。报告：`data/bench-engines-20260924.md`。
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

## 9. M4-4.4 补完 M3 验收（3-3 并发压测 / 3-4 24h 长稳 / 2-9 相关性抽检）（当前任务）

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
| 4.4-8 | 24h 长稳 | 后台挂机 24h 后看汇总 | 可用率 ≥ 99%，内存无持续增长 | [ ] |
| 4.4-9 | 相关性抽检脚本可用 | `scripts/relevance.py` | 输出 20 条中英查询的 top5 明细表 | [x] |
| 4.4-10 | 相关性人工打分 | 对明细表逐条打分 | top5 中相关数 ≥ 4 的查询占比 ≥ 90% | [!] |
| 4.4-11 | 判定逻辑单测 | `pytest -q -m "not net"` | 分位 / 判定 / RSS 解析用例全绿 | [x] |
| 4.4-12 | 回归 | `pytest -q -m "not net"` | 既有测试全绿 | [x] |
| 4.4-13 | 文档同步 | 查看 `docs/04`、`README.md` | 验收结论与脚本用法已记录 | [x] |

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

**风险 / 已知限制**：

- 压测与长稳都依赖本机代理出网；开发期代理曾失效导致大面积超时，需在结论中区分「服务问题」与「网络抖动」。
- 10 并发会真打 SearXNG 与上游引擎，可能触发上游限流，导致个别请求变慢；判定只看 5xx / 超时，不看延迟绝对值。
- 24h 长稳需要机器与代理连续可用，若中途网络中断会体现为可用率下降，需人工判断剔除。

## 8. 遗留与风险事项

- **本机网络波动**：开发期间出现系统代理（`127.0.0.1:7897`）失效导致外网抓取大面积超时的情况，此时改用直连（`UTF8SEARCH_TRUST_ENV=false`）即可恢复。部署到服务器时无此问题。
- 反爬风险：免费引擎会被上游限流，需持续跟踪引擎可用性并按需调整 `keep_only` 名单。
- 未完成项：2-9（相关性人工抽检）、3-3（10 并发压测）、3-4（24 h 长稳）、3-8（云服务器部署）、3-9（真实客户端联调）；3-7（SSRF 防护）已由 M4-4.1 完成。——**详细执行计划见 `docs/04-后续路线图.md`**。
- 合规：仅限抓取公开页面并遵守 robots.txt 与限速要求。
- 待清理：调研期临时容器已删除；`%TEMP%\searxng-spike` 目录受本机策略限制未能删除，其中仅含一份测试用 settings.yml。