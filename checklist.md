# 验收清单（checklist）

> 项目：utf8-search
> 用法：开发与交付以本清单为准，逐项完成并勾选后再向用户汇报。
> 状态标记：[ ] 未开始 / [x] 已完成 / [!] 阻塞 / [-] 不做

## 0. 任务目标与范围

**目标**：为 LLM 提供免费、高速的联网搜索服务（MCP Server + REST），效果对标 Tavily，速度对标 DeepSeek 联网搜索。

**本期范围**：M0 调研与规划 → M1 MVP → M2 速度与质量 → M3 稳定性（均已完成主体开发与验收）。

**明确不做**：全站爬虫与建索引、绕过付费墙、自带 LLM 生成答案（默认）、数据转售。

**参考文档**：`docs/01-前期调研与可行性分析.md`、`docs/02-技术方案与开发计划.md`、`docs/03-客户端接入指南.md`。

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

## 7. 遗留与风险事项

- **本机网络波动**：开发期间出现系统代理（`127.0.0.1:7897`）失效导致外网抓取大面积超时的情况，此时改用直连（`UTF8SEARCH_TRUST_ENV=false`）即可恢复。部署到服务器时无此问题。
- 反爬风险：免费引擎会被上游限流，需持续跟踪引擎可用性并按需调整 `keep_only` 名单。
- 未完成项：2-9（相关性人工抽检）、3-3（10 并发压测）、3-4（24 h 长稳）待下一阶段补。
- 合规：仅限抓取公开页面并遵守 robots.txt 与限速要求。
- 待清理：调研期临时容器已删除；`%TEMP%\searxng-spike` 目录受本机策略限制未能删除，其中仅含一份测试用 settings.yml。