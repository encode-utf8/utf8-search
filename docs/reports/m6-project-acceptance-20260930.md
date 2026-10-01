# utf8-search 结项验收总表（2026-09-30，2026-10-01 修正需求 4 与结论计数）

> 对照最初 **8 条需求**逐条给出：需求 → 实现位置 → 验收证据 → 当前状态。
> 状态三档：**达标** / **有明确限制**（写清限制、对外表现、是否已告知调用方）/ **未做**。
> 本表只做汇总，不改代码；所有证据都在仓库内（`docs/reports/` 报告 + `checklist.md` 条号）。

## 0. 一句话结论

**8 条需求：5 条达标、3 条「有明确限制」、0 条未做**。三条限制分别是
**中文新闻时效**（免费中文新鲜源不可得 → 用 `freshness_unverified` 降级信号如实告知）、
**召回质量 2-9**（按 2026-10-01 登记的采样口径实测**中位数 16/20 = 80% < 90%**，稳定缺陷 Q6/Q16，见需求 4）与
**真实客户端人工联调 3-9**（自动化通道已 24/24，人工回填待用户本人完成）。

> **修正说明（2026-10-01）**：需求 4 原先按**单次采样**判为「2-9 = 19/20 = 95% 达标」；同一 commit 的 5 次采样显示
> 单次采样自身就有 **16–17/20** 的摆动（`docs/reports/m2-9-sampling-variance-20261001.md`），
> 因此改按登记的「≥3 次取中位数」口径**改判为「有明确限制」**。**19/20、20/20、以及「Q16 由 2/5→4/5」均为单次抽样结果，不作为稳定事实。**

## 1. 逐条验收

### 需求 1 —— 高速 + 免费（免费不限量、单请求快、高并发不雪崩）

| 项 | 内容 |
| --- | --- |
| 实现位置 | `src/utf8_search/core/upstream_gate.py`（并发闸门）、`core/pipeline.py`（兜底/降级）、`providers/searxng.py`（多引擎 + 健康度）、`cache/store.py`（多级缓存）、`rank/*`（本地排序与过滤） |
| 验收证据 | checklist §15（M5 闸门全轮）、§17/§18（引擎集合与候选池）、报告 `m5-concurrency-gate-20260927.md`（契约分层：**@≤5 100% 成功 / 0 降级 / P95 ≤5.2s**；**@10 ≥95% / P95 ≤6.5s**；@30 秒级 429、容量陈述）；`docs/01` 的冷启动基线（basic P50 **1048ms**、advanced 3775ms、deep 9234ms） |
| 状态 | ✅ **达标** |
| 备注 | 全部上游均为免费源（SearXNG 聚合 + 本地抽取），无任何付费 Key；坏日容量上限已如实记录（`docs/04` §8） |

### 需求 2 —— 本机 + 云部署（同一套代码两处都能跑）

| 项 | 内容 |
| --- | --- |
| 实现位置 | `docker-compose.yml`（三容器：SearXNG / 应用 / Caddy）、`searxng/settings.yml` + `settings.local.yml`（云端直连 vs 本机代理，单测强制两份仅 proxies 不同）、`docs/05-服务器部署手册.md` |
| 验收证据 | `m4-4.2-deploy-20260925.md`（阿里云 `43.106.104.49`：三容器 healthy、Let's Encrypt 真证书、Host 白名单 421、鉴权/限流、`data/` 持久化、全通道自检 **24/24**）；checklist §14；本轮环境实测：`https://43.106.104.49.sslip.io/health` 200（证书至 **2026-12-24**） |
| 状态 | ✅ **达标** |
| 备注 | 本机模式要求走 `settings.local.yml`（代理），云端必须用默认 `settings.yml`；两者一致性由 `tests/test_searxng_settings.py` 强制 |

### 需求 3 —— 客户端支持（MCP stdio / Streamable HTTP / Tavily REST 全覆盖）

| 项 | 内容 |
| --- | --- |
| 实现位置 | `src/utf8_search/server/mcp_server.py`（工具 `web_search` / `web_fetch`）、`server/http_api.py`（`/search`、`/v1/search`、`/extract`、`/v1/extract`、`/mcp`）、`docs/03-客户端接入指南.md` |
| 验收证据 | `scripts/mcp_selfcheck.py` **24/24**（stdio SDK / stdio 原始帧 / Streamable HTTP：401·421·initialize·tools/list·调用 / REST：三种鉴权位置、`days`→`time_range`、`include_domains`、`/v1/extract`、advanced+raw_content / 限流：RPM=1 第 2 次 429+Retry-After）——见 `redeploy-selfcheck-20260929.md`；`docs/03` §7.1 逐客户端「该期待什么/不该期待什么」 |
| 状态 | ⚠️ **有明确限制** |
| 限制与告知 | 限制：**真实客户端 GUI 的人工联调（3-9）未完成**（自动化只覆盖协议层）。对外表现：无（不影响运行）。已告知：`docs/reports/manual-acceptance-checklist-20260928.md` 给出每个客户端的最小操作与预期现象，checklist 3-9 行标注「待用户本人完成」 |
| 备注 | 其余 7 个客户端类（Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent）走的是同一套协议，自检 24/24 已覆盖协议面 |

### 需求 4 —— 多页深读 + 召回质量（"一次读几十个网页、效果接近 Tavily"）

| 项 | 内容 |
| --- | --- |
| 实现位置 | `core/pipeline.py`（深度模式预算、正文抓取）、`extract/extractor.py`（trafilatura + Jina 兜底）、`rank/fusion.py`（RRF 融合）、`rank/diversity.py`（质量与多样性）、`rank/spec_tokens.py`（规格 token，2026-09-30 新增） |
| 验收证据 | deep 模式平均读页 **16.2**（单次 14-19，`docs/01`）；**2-9 相关性抽检（按 2026-10-01 登记的采样口径）**：固定 commit 5 次采样 = **16–17/20，中位 16/20 = 80%**，**未达 90% 门槛**（门槛仍是 90%；判据改为「≥3 次取中位数 ≥18/20」，属**采样方式修正、不是放宽门槛**），见 `m2-9-sampling-variance-20261001.md`；**先前 19/20（2026-09-30）与 20/20（P1 轮）均为单次抽样，不作为稳定事实**；方法=agent 初评+校准集+盲评；**卫生度**：覆盖率 0.773 / 独立站点 4.75 / 同站冗余 0 / 聚合页 0 / 空内容 2（`relevance-hardening-20260930/hygiene-after.json`） |
| 状态 | ⚠️ **有明确限制**（2-9 未达 90%，已定位 Q6/Q16 稳定缺陷） |
| 备注 | 限制：**2-9 中位数 16/20 < 90%**；稳定缺陷 = **Q6**（Python 3.13，5 轮恒 3/5：V2EX 会员页/brew formula 等纯导航/元数据页）与 **Q16**（iPhone 17 Pro，5 轮恒 3/5：wirefly Pro Max 机型不符 + Pinterest 图片站）；**Q1 的降档（4→2）与「brave/google/privacywall/resulthunter/yep 多引擎同时失败」同现**（5 轮里 3 轮）= 上游可用性限制。对外表现：无（2-9 是内部质量指标，不改 API 字段与降级信号）。已告知：本表 + checklist 2-9 行 + `m2-9-sampling-variance-20261001.md`。另有历史记录（保留）：口径澄清「含实质内容的首页/栏目页算相关」；Q16 混杂型号回收页修复**已部署**（镜像 `fe0252b06803`，线上复验绕缓存：`iPhone 17 Pro 价格 参数` 前 3 条为 redsea/Apple 官方/Spigen，无回收列表页、无 iPhone 8 参数页；自检 24/24、鉴权 401 与 `/metrics` 正常）——但该修复**未把 Q16 在 5 次采样中拉过 ≥4 线** |

### 需求 5 —— 时效性 + 中文优先

| 项 | 内容 |
| --- | --- |
| 实现位置 | `providers/searxng.py`（按引擎白名单透传 `time_range`）、`core/pipeline.py`（新鲜度触发判据、Bing 让位、`freshness_unverified` 降级信号、日期回补）、`rank/recency.py`（本地时效排序 + 日期回补）、`scripts/searxng_dates.py`（日期可信度判据） |
| 验收证据 | **英文组**：`topic=news` + `time_range=day` 的 7 日内比例 **87-100%（达标，门槛 80%）**；**中文组**：52-68%（已知限制）；报告 `m6-news-freshness-decision-20260930.md`、`m6-zh-fresh-source-20260930.md`（免费中文新鲜源不可得的结论） |
| 状态 | ⚠️ **有明确限制** |
| 限制与告知 | 限制：**中文新闻拿不到足够"日期可信"的新鲜结果**（`chinaso news` 索引旧、`tiger news` 常 0 条、`google news` 长期 CAPTCHA 且不给日期、`sogou wechat` 在当前出口失效、`sina` 无日期、`bilibili` 是视频站）；免费且按查询可用的中文新鲜源经探测**不可得**。对外表现：响应里 **`degraded=true` + `degraded_reason="freshness_unverified"`**（REST 与 MCP 同一套字段，Tavily 标准字段不动）。已告知：`docs/03` §7.1 + `docs/04` §8 第 12/14 条 + 本表 |
| 备注 | 附带成果：**日期可信度抽检**（`engine_probe.py dates`）识别出 `yandex` 是"仅索引日期"源（2017 年旧文被标成当天），避免门槛被假绿骗过 |

### 需求 6 —— Docker（一键起）

| 项 | 内容 |
| --- | --- |
| 实现位置 | `docker-compose.yml`（三服务 + `env_file: .env` 全量注入 + 12 条显式覆盖/中性化）、`Dockerfile` |
| 验收证据 | checklist §19/§22（镜像重建、env 接线生效证明：容器 env 与 `.env` **逐键 65/65 一致、0 缺失**；端口矩阵 app 仅 `127.0.0.1:8000`、对外仅 80/443）；`m6-env-wiring-applied-20260930.md` §3；镜像回滚锚点：`pre-relevance-hardening-20260930` / `pre-datetrust-20260930` / `pre-m5-20260929` |
| 状态 | ✅ **达标** |
| 备注 | 现在改 `.env` 必须 `docker compose up -d --no-deps utf8-search`（env_file 变更需重建容器，restart 不够） |

### 需求 7 —— 鉴权 + 限流

| 项 | 内容 |
| --- | --- |
| 实现位置 | `auth.py`（Bearer / `X-API-Key` / body `api_key` 三种位置、滑动窗口限流）、`server/http_api.py`（`_authorize`） |
| 验收证据 | 自检 24/24 中的鉴权与限流项；本轮线上实测：无/错 Key → **401**（`/v1/search`、`/v1/extract`、`/metrics`），**RPM=60 时第 61 次 → 429 + `Retry-After: 59`**；Caddy 层 HTTPS + Host 白名单 421 |
| 状态 | ✅ **达标** |
| 备注 | `/metrics` 沿用同一套 REST 鉴权（不裸奔） |

### 需求 8 —— Tavily 兼容

| 项 | 内容 |
| --- | --- |
| 实现位置 | `server/http_api.py`（`/search`、`/v1/search`、`/extract`、错误体）、`models.py`（Tavily 字段：`answer`/`images`/`favicon`/`usage`/`auto_parameters`）、`server/mcp_server.py`（同一套字段） |
| 验收证据 | `m6-tavily-compat-20260928.md`（**逐字段矩阵**：请求/响应/错误三类，依据官方 OpenAPI schema + 官方 SDK 源码 + 官方示例响应，均已入库 `tavily-official-search-20260928.md` 等）；`tests/test_tavily_compat.py`（用官方示例响应做 fixture、官方 SDK 异常类型断言 **400 → BadRequestError**、401/429 语义不变、429 带 `Retry-After`）；`docs/03` §7.1「该期待什么 / 不该期待什么」 |
| 状态 | ✅ **达标** |
| 备注 | **有意保留的差异**（已在 `docs/03` §7.1 逐条告知）：`answer` 恒 null、图片字段恒空、`score` 量纲不同、`results[].id` 格式不同、`usage.credits` 恒 0、未实现的请求参数「接受但忽略」、`detail` 仍是字符串/列表 |

## 2. 遗留清单（按优先级）

| # | 遗留项 | 性质 | 证据/出处 |
| --- | --- | --- | --- |
| 1 | **3-9 真实客户端人工联调** | 需用户本人完成 | `manual-acceptance-checklist-20260928.md`；checklist 3-9 行 |
| 2 | **闸门上限对上游健康度自适应**（坏日样本不足，本轮不做） | 需更多坏日数据 | `docs/04` §8；`m5-concurrency-gate-20260927.md` |
| 3 | **排序层对"含实质内容的首页/栏目页"轻微降权**（让独立文章更靠前） | 可选增强（本轮不实现） | `docs/04` §8 本轮新增条目 |
| 4 | **中文新鲜源不可得**（结论）+ 「报刊 RSS 当最新新闻池」可选低价值增强 | 结论 + 可选实现 | `m6-zh-fresh-source-20260930.md` §3.4 |
| 5 | **证书续期依赖 80/443 长期放行**（Let's Encrypt 至 2026-12-24 自动续期） | 运维约束 | `m4-4.2-deploy-20260925.md`；`docs/05` |
| 6 | 长稳最终结论回填 | **跨镜像 6h 已闭环**（只报可用率：71 个计入样本 **100%**、0 异常/空结果/跳过、覆盖率 100%、延迟 P50 2362ms/P95 2584ms；**内存不可比**：12:00 重建后 RSS 仅 7 个采样，原因已注明）；**干净 6h 仍差约 50 分钟**（18:05 收尾，当前 63 采样 100%） | checklist §22/§24/§27 |
| 7 | ~~Q16 混杂型号页修复待部署~~ | ✅ **已闭环**：镜像 `fe0252b06803`（回滚锚点 `pre-closeout-20260930` = `40f87e4a5f9d`），复验见需求 4 备注 | `m6-zh-fresh-source-20260930.md` §2/§4 |
| 8 | **2-9 召回质量未达 90%**（稳定缺陷 Q6/Q16；Q1 受「多引擎同时失败」影响） | 需质量项后续处理（本轮只登记口径与事实） | checklist 2-9 行；`m2-9-sampling-variance-20261001.md` |

## 2.1 结项稳定期 24h 长稳（结项后的长期证据）

| 项 | 内容 |
| --- | --- |
| 目标 | 在**最终镜像**（`fe0252b06803`）上跑 24h，作为结项后的长期可用性/内存证据 |
| 启动 | **2026-09-30 17:17:26**，`setsid nohup` 后台；PID **227695**（以 `data/soak-24h-closeout.meta.json` 的 `pid` 为准），预计 **2026-10-01 17:17** 结束 |
| 口径 | `--interval 300 --unique --http-url http://127.0.0.1:8000`（打已部署服务、每轮唯一查询避开缓存；RSS 采样新容器 PID） |
| 首个采样 | 17:17:27 OK，1152ms，结果 5 条，**RSS 110.7MB** |
| 结果 | ⏳ 跑满后 `scripts/soak.py --summarize --out data/soak-24h-closeout.csv --json data/soak-24h-closeout.json` 回填本行 |
| 证据 | `data/soak-24h-closeout.{csv,json,meta.json,out.log}`（`data/` 不入库，结项时复制 CSV/JSON 到 `docs/reports/`） |

## 3. 证据索引（本表引用的报告）

| 主题 | 报告 |
| --- | --- |
| 调研基线（性能/读页数） | `docs/01-前期调研与可行性分析.md` |
| 云部署 | `m4-4.2-deploy-20260925.md`、`docs/05-服务器部署手册.md` |
| 并发闸门与契约分层 | `m5-concurrency-gate-20260927.md` |
| 引擎集合（替换 + 日期可信度分组） | `m6-engine-selection-20260928.md`、`m6-engine-inventory-20260928.md` |
| 时效性（分语言口径 + 降级信号 + 中文源可行性） | `m6-news-freshness-20260930.md`、`m6-news-freshness-decision-20260930.md`、`m6-zh-fresh-source-20260930.md` |
| 环境接线与部署 | `m6-env-wiring-plan-20260930.md`、`m6-env-wiring-applied-20260930.md` |
| 相关性加固与 2-9 采样口径（中位 16/20，未达 90%） | `m6-relevance-hardening-20260930.md`、`m2-9-relevance-hardening-20260930-scores-judge.md`、`m2-9-sampling-variance-20261001.md` |
| Tavily 兼容 | `m6-tavily-compat-20260928.md`、`docs/03` §7.1 |
| 客户端人工操作单 | `manual-acceptance-checklist-20260928.md` |
