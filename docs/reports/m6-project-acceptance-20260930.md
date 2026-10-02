# utf8-search 结项验收总表（2026-09-30；2026-10-01 修正需求 4 与结论计数；2026-10-02 需求 3 改判达标、3-9 结案）

> 对照最初 **8 条需求**逐条给出：需求 → 实现位置 → 验收证据 → 当前状态。
> 状态三档：**达标** / **有明确限制**（写清限制、对外表现、是否已告知调用方）/ **未做**。
> 本表只做汇总，不改代码；所有证据都在仓库内（`docs/reports/` 报告 + `checklist.md` 条号）。

## 0. 一句话结论

**8 条需求：7 条达标、1 条「有明确限制」、0 条未做**。唯一的限制是
**中文新闻时效**（免费中文新鲜源不可得 → 用 `freshness_unverified` 降级信号如实告知）。

> **3-9 结案（2026-10-02，用户裁决）**：「配置正确后能正常运行、能接收结果」已经由
> `scripts/clients_sim.py` 按**每个客户端自己的配置格式**做仿真验证（线上 **45/45 通过**，含 REST 与
> Streamable HTTP 两种走法），客户端界面里「粘贴配置 + 点保存」属机械操作、不构成测试项。
> 因此 3-9 **不再作为人工验收项**，需求 3 由「有明确限制」改为**达标**。

> **需求 4 的两次改判（2026-10-01）**：T3 曾因「同一 commit 单次采样只有 16–17/20」把 2-9 从达标改判为「有明确限制」；
> 此后 T5/T6/T7 修掉 Q1/Q6/Q16 的稳定缺陷并补起对拍/召回证据，**T8 按登记口径线上复验 19/19/19（中位 19、最低 19）⇒ 需求 4 恢复「达标」**；
> 仍保留 Q2 未达标的说明与「主题相关性闸门」立项。
>
> **T12 线上复核（2026-10-02）**：合并 T10+T11（`ff5a4ae`）并部署 `3a521d3e6f9d` 后，登记口径线上 3 轮 = **19/19/19（中位 19、最低 19）** ⇒ 需求 4 **保持「达标」**；**Q2 按出口条款结案为已知上游限制**（无料降级 / 有料换位收益已对拍验证），立项关闭。
>
> **最终状态快照（2026-10-02 收尾）**：线上镜像 **`3a521d3e6f9d`**（回滚锚点 `pre-t12-20261002` = `dc7b5f4257ff`）；**8 条需求 = 7 达标 / 1 有明确限制 / 0 未做**（限制 = 中文新闻时效 `freshness_unverified`）；**2-9 按登记口径线上 3 轮 = 19/19/19（中位 19、最低 19）**；**人工项：无**（3-9 已于 2026-10-02 按自动化仿真结案，操作单保留作参考： `docs/reports/manual-acceptance-checklist-20260928.md`）；最终镜像 6h 长稳已跑满（§2.2，可用率 100%）。

> **历史（T3 口径修正，保留披露）**：2026-10-01 之前的 19/20、20/20、「Q16 由 2/5→4/5」均为**单次抽样**结果，不作为稳定事实；
> 单次采样的摆动区间实测为 16–17/20（见 `m2-9-sampling-variance-20261001.md`），这也是后来引入「≥3 次取中位数」登记口径的原因。

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
| 状态 | ✅ **达标** |
| 验收补充（2026-10-02） | **按客户端仿真 45/45**：`scripts/clients_sim.py` 用每个客户端自己的配置格式（Claude/Cursor 的 JSON、Codex 的 TOML、Cherry Studio 图形界面字段、Dify/n8n 的 HTTP 请求）生成配置 → 解析回来 → 按该客户端的连接方式真连一次，覆盖本表上方列出的每一行客户端（含 REST 与 Streamable HTTP），冷查询全部通过 —— 见 `docs/reports/20261002-clients-sim.md` |
| 限制与告知 | 残留：客户端界面里「粘贴配置 + 点保存」这一步无法自动化（属机械操作）。**用户裁决（2026-10-02）**：该项不作为验收项 —— 「配置正确后能正常运行、能接收结果」即达成 |
| 备注 | §2 表格里的每一行客户端（Claude Desktop / Codex / Cursor / Cherry Studio / Dify / n8n / 自研 Agent / 已有 Tavily 代码）都由 `scripts/clients_sim.py` 按各自配置格式跑过一遍（45/45）；它们最终只走三条通道（MCP stdio / Streamable HTTP / REST），协议面由自检 24/24 覆盖 |

### 需求 4 —— 多页深读 + 召回质量（"一次读几十个网页、效果接近 Tavily"）

| 项 | 内容 |
| --- | --- |
| 实现位置 | `core/pipeline.py`（深度模式预算、正文抓取）、`extract/extractor.py`（trafilatura + Jina 兜底）、`rank/fusion.py`（RRF 融合）、`rank/diversity.py`（质量与多样性）、`rank/spec_tokens.py`（规格 token，2026-09-30 新增） |
| 验收证据 | deep 模式平均读页 **16.2**（单次 14-19，`docs/01`）；**2-9 相关性抽检（2026-10-01 登记口径；线上 HTTP 路径、绕缓存、单并发、轮间 65s、3 轮取中位）**：**19/19/19 → 中位 19/20 = 95%、三轮最低 19（≥18）**，见 `20261001-t8-merge-deploy.md` 与 `m29-t8-20261001-run{1..3}-*`；固定候选对拍与召回证据见 `20261001-t6-paired-and-margin.md`、`20261001-t7-q1-forms.md`（rule① 20/20 返回条数 5→5）；**卫生度**：覆盖率 0.773 / 独立站点 4.75 / 同站冗余 0 / 聚合页 0 / 空内容 2 |
| 状态 | ✅ **达标（按 2026-10-01 登记的采样口径）** |
| 备注 | **登记口径达标**：中位 19/20 ≥18、三轮最低 19 ≥18（T8 线上复验，镜像 `dc7b5f4257ff`）。**保留说明**：唯一未达标查询仍是 **Q2（最近一周 AI 行业动态）** —— 上游候选池漂移 + 主题匹配类问题（短剧垃圾站、`nocache`/DuckDuckGo 等无关主题），已立项 **「主题相关性闸门」**（见 `20261001-t6-paired-and-margin.md` §2③）；本轮修掉的稳定缺陷：Q6（V2EX 会员页 / brew 包索引页）、Q16（Pro Max 机型 + 图片素材板）、Q1（电视节目单 / 院校迎新 / 开运日历）→ 分别 4/5+、4/5+、5/5。历史记录（保留）：Q1#3/Q1#5/Q2#2 三条承重项裁决、`is_aggregator_page` 口径对齐、Q16 混杂型号回收页修复与部署。**Q2 结案（2026-10-02 T12）**：Q2 属**已知上游限制** —— 无料时如实降级 `no_relevant_results`（线上 REST 与 MCP 各验证一次），有料时的换位收益已在受控对拍中验证（T11）；「主题相关性闸门」立项**已关闭**。**新遗留**：registry 判据从域名白名单扩展为路径/标题形态（治 `docker.aityp.com` 这类 mirror 页，Q6）—— 见 `docs/04` §8 第 16 条 |

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
| 1 | ~~3-9 真实客户端人工联调~~ | ✅ **已闭环（2026-10-02 用户裁决：按自动化仿真结案）** | `docs/reports/20261002-clients-sim.md`：对线上 **45/45** 通过（每个客户端用各自配置格式跑通，含 REST 与 Streamable HTTP）；界面粘贴属机械操作、无测试价值 |
| 2 | **闸门上限对上游健康度自适应**（坏日样本不足，本轮不做） | 需更多坏日数据 | `docs/04` §8；`m5-concurrency-gate-20260927.md` |
| 3 | ~~排序层对"含实质内容的首页/栏目页"轻微降权~~ | ✅ **已闭环（P1，2026-09-30；P7 补幂等）**：`COLUMN_PAGE_SCORE_MULTIPLIER = 0.95` + `apply_form_penalty()`（与过滤层共用 `looks_like_column` 判据；P7 起只用于排序 key、重复调用幂等，不改对外 `score` 语义） | `20260930-p1-ranking-form-downrank.md`、`20260930-p7-ranking-followups.md` |
| 4 | **中文新鲜源不可得**（结论）+ 「报刊 RSS 当最新新闻池」可选低价值增强 | 结论 + 可选实现 | `m6-zh-fresh-source-20260930.md` §3.4 |
| 5 | ~~证书续期依赖 80/443 长期放行~~ | ✅ **已结案（2026-10-02 评估）→ 降为运维常识项**：Caddy 自动续期已实测排程（ARI 窗口 **2026-11-23 → 11-25 UTC**，约到期前 30 天；全量日志 `certificate renewed` 0 次 = 首次续期尚未发生）；安全组 22/80/443 保持长期放行，`ops_check` 到期前 30 天起报 ALERT（告警分支实测 `--cert-min-days 100` → **exit=1**）；仅留 2026-11-24 前后一次只读核对 | `20261002-tls-renewal-assessment.md`；`m4-4.2-deploy-20260925.md`；`docs/05` §5.4 |
| 6 | 长稳最终结论回填 | ✅ **已闭环（T8 回填，2026-10-01）**：跨镜像 6h = 73 行/71 计入、可用率 **100%**、P50 2362ms/P95 2584ms（**内存不可比**：12:00 rebuild 后容器 PID 失效）；干净 6h = 71 计入、可用率 **100%**、P50 1256ms/P95 2550ms；24h 稳定期 = 287 计入/100%/P50 1331ms；结论已回填 checklist §22/§24/§27 与本文 §2.1 | checklist §22/§24/§27；`docs/reports/soak-6h-{envwiring,freshness}.{csv,json}` |
| 7 | ~~Q16 混杂型号页修复待部署~~ | ✅ **已闭环**：镜像 `fe0252b06803`（回滚锚点 `pre-closeout-20260930` = `40f87e4a5f9d`），复验见需求 4 备注 | `m6-zh-fresh-source-20260930.md` §2/§4 |
| 8 | ~~2-9 召回质量未达 90%~~ | ✅ **已闭环（T8 达标 / T12 结案，2026-10-02）**：需求 4 按 2026-10-01 登记的采样口径线上 3 轮 **19/19/19（中位 19、最低 19）** ⇒ 达标；**Q2 属已知上游限制** —— 无料时返回 `degraded_reason="no_relevant_results"`（线上 REST 与 MCP 均已验），有料时的换位收益经受控对拍验证；该立项已关闭 | checklist 2-9 行；`20261002-t12-merge-deploy-q2-closeout.md` |
| 9 | **registry 判据从域名白名单扩展为路径/标题形态**（治 `docker.aityp.com` 这类 mirror 页 → Q6） | 需下一轮质量项 | `docs/04` §8 第 16 条；`20261002-topic-relevance-gate-t11.md` §3.3 |

## 2.1 结项稳定期 24h 长稳（结项后的长期证据）

| 项 | 内容 |
| --- | --- |
| 目标 | 在**最终镜像**（`fe0252b06803`）上跑 24h，作为结项后的长期可用性/内存证据 |
| 启动 | **2026-09-30 17:17:26**，`setsid nohup` 后台；PID **227695**（以 `data/soak-24h-closeout.meta.json` 的 `pid` 为准），预计 **2026-10-01 17:17** 结束 |
| 口径 | `--interval 300 --unique --http-url http://127.0.0.1:8000`（打已部署服务、每轮唯一查询避开缓存；RSS 采样新容器 PID） |
| 首个采样 | 17:17:27 OK，1152ms，结果 5 条，**RSS 110.7MB** |
| 结果 | ✅ **已跑满（2026-09-30 17:17:27 → 2026-10-01 17:17:27，24.00h）**：`--summarize` = 289 行 = 2 预热 + **287 计入**、覆盖 **100.0%**、**可用率 100%**、0 空结果/异常/跳过；延迟 **P50 1331ms / P95 2569ms / max 2619ms / mean 1612ms**；**内存平稳**（最低 99.2MB、末次 99.2MB、峰值 113.6MB；中位数 111.7 → 103.9MB，**-7.0%**）；期间**无 429**：app 容器自 09-30 17:16 起累计 `/metrics` = `requests_total{result="ok"} 329`、**无 `result="error"`、无 `rejected_total` 序列、`upstream_acquire_seconds` 无排队**（重建前快照，覆盖整个 24h 窗口） |
| 说明 | 该 24h 跑在 **P1/P7 上线前的镜像 `fe0252b06803`** 上；2026-10-01 的部署已换新镜像，新镜像另有 1h 回看（见 T4 报告） |
| 证据 | `data/soak-24h-closeout.{csv,json,meta.json,out.log}`；**已随代码留痕**：`docs/reports/soak-24h-closeout.{csv,json}`（另两个 6h 的 CSV/JSON 同目录） |
## 2.2 最终镜像长稳（6h，2026-10-02 启动）

| 项 | 内容 |
| --- | --- |
| 目标 | 在**最终上线镜像 `3a521d3e6f9d`**（含 T10/T11：`no_relevant_results` 降级 + 新闻意图×内容页形态 + 内容农场补形态）上跑 6h，作为「已交付镜像」的长期可用性/延迟/内存证据 |
| 为什么必要 | 旧 6h/24h 长稳分别跑在 `fe0252b06803`（结项镜像）与 `c2205226f7fc` 等**更早镜像**上；T10/T11 改过 rank 层（每条候选新增形态判据），需要一份**对应最终镜像**的长稳证据，才能把「线上跑的就是长稳过的那个」说圆 |
| 启动 | **2026-10-02 02:15:19**，`setsid nohup` 后台；PID **478005**，预计 **08:15** 结束（`--duration-hours 6 --interval 300 --unique --http-url http://127.0.0.1:8000`） |
| 首个采样 | 02:15:20 OK，1216ms，5 条，RSS 126.0MB |
| 结果 | ✅ **已跑满（2026-10-02 02:15:20 → 08:15:20，6.00h）**：73 行 = 2 预热 + **71 计入**、覆盖 **100.0%**、**可用率 100%**、0 空结果/异常/跳过；延迟 **P50 1052ms / P95 2113ms / max 2588ms / mean 1102ms**；**内存平稳**（最低 102.2MB、末次 103.6MB、峰值 120.7MB；中位数 120.4 → 103.5MB，**-14.0%**） |
| 与 §2.1 旧镜像 24h 的差异 | **新镜像不劣于旧镜像**：P50 **1052ms vs 1331ms（-21%）**、P95 **2113ms vs 2569ms（-18%）**、max 2588ms vs 2619ms；可用率同为 **100%**；内存同为「抬升后走平/回落」形态（新镜像中位 -14.0%，旧镜像 -7.0%）。说明：两次长稳的查询集合与 `--unique` 口径一致，但上游引擎健康度会随日漂移 —— **差异只能读作「最终镜像不劣」**，不能归因于 T10/T11 代码变快 |
| 证据 | `data/soak-final-image-6h.{csv,json,meta.json,out.log}`（`data/` 不入库，回填时复制 CSV/JSON 到 `docs/reports/`） |


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
