# docs/reports/ —— 报告索引（稳定入口）

> **报告类链接统一走本索引**：站点/文档只深链 `docs/00`–`docs/05`、`checklist.md` 这类稳定文件；
> 具体报告用「本文件 + 文件名」引用，不要在站点里硬编码单个报告的相对路径。

## 0. 链接策略与清理政策

- **稳定深链白名单**：`docs/00`–`docs/05`、仓库根 `README.md`、`checklist.md`、本文件（以及 `searxng/settings.yml`、`docker-compose.yml`、`Caddyfile` 等配置）。
- **报告类**：一律经由本索引引用。2026-10-02 做过一次仓库瘦身（口径 = 只留**开发结果验证 / 方案设计 / 反馈 / 日志**），
  删除了 204 个测试与实验的过程明细（2-9 逐轮采样、候选池与对拍原始 JSON、引擎探针与环境 AB 原始数据、部署过程回显、被后续报告取代的中间件）。
  细节见 [`20261002-repo-cleanup.md`](20261002-repo-cleanup.md)。
- **历史正文里的旧文件名（2026-10-03 加固）**：已删文件的机器可读清单在
  [`cleaned-files-20261002.txt`](cleaned-files-20261002.txt)（204 项）；凡是引用这些路径/文件名的非忽略文件，
  必须在文首带标记 `<!-- refs-policy: cleaned-2026-10-02 -->`（配一条可见的「引用提示」）。
  需要原始文件时从 git 历史取回：`git log --diff-filter=D -- docs/reports/<文件名>` 或 `git show <commit>:docs/reports/<文件名>`。
- **引用校验（防复发）**：`.venv/bin/python scripts/check_refs.py` 扫描全部**非 gitignore 文件**——
  Markdown 链接必须能解析；`docs/reports/...` 与带扩展名的仓库内路径必须是现存文件，或命中已清理清单**且带上述标记**；
  违规 exit 1。`tests/test_check_refs.py::test_repo_has_no_dangling_refs` 把「0 违规」固化为离线套件的一部分。
  约定：**引用已清理文件前先确认是否必须保留原件**；新增报告一律引用现存文件。
- **`data/` 路径规则**：报告里出现的 `data/...` 是当时的**工作副本路径**（`data/` 不入 git ⇒ 默认不可用；引用只统计、不判错）；
  只有本索引收录的 `docs/reports/` 文件才是留档证据——**验收证据一律归档到本目录**，不允许只在 `data/` 留唯一副本；
  命名 `\<里程碑\>-\<主题\>-\<日期\>.md`（日期 `YYYYMMDD`）。
- **不可恢复的例外（已知 5 个）**：2026-10-02 服务器 `data/` 清理删掉了 T19 的原始件
  `selfcheck-t19.md`、`soak-t19-1h.{csv,json,meta.json,out.log}` —— 无 git 历史、只能重跑复现；
  相关报告已就地标注，数字以 `20261002-t19-merge-deploy.md` 为准。

## 1. 索引

### 结项与验收（9）

| 文件 | 标题 |
| --- | --- |
| `env-selfcheck-linux-20260925.md` | M4-4.3 客户端联调自检报告 |
| `m4-4.2-deploy-20260925.md` | M4-4.2 云服务器部署验收报告 |
| `m4-4.2-deploy-selfcheck-20260925.md` | M4-4.3 客户端联调自检报告 |
| `m4-4.3-client-selfcheck-20260924.md` | M4-4.3 客户端联调自检报告 |
| `m4-4.4-soak-24h-20260926.md` | M4-4.4 24h 长稳验收报告（2026-09-26 → 09-27） |
| `m4-4.4-soak-coverage-floor-20260926.md` | M4-4.4 长稳覆盖率下限（B 补丁）验收：SIGSTOP 受控挂起复现 |
| `m5-5.3-verification-20260924.md` | M5-5.3 中文源强化与查询质量 —— 验收报告（2026-09-24） |
| `m6-project-acceptance-20260930.md` | utf8-search 结项验收总表（2026-09-30；2026-10-01 修正需求 4 与结论计数；2026-10-02 需求 3 改判达标、3-9 结案） |
| `manual-acceptance-checklist-20260928.md` | 人工验收操作单（2-9 相关性抽检 / 3-9 真实客户端联调） |

### 部署 / 合并 / 上线（8）

| 文件 | 标题 |
| --- | --- |
| `20261001-t4-merge-deploy-backfill.md` | T4：合并两条分支 → 开窗口部署 → 回填长稳（2026-10-01） |
| `20261001-t8-merge-deploy.md` | T8：T5/T6/T7 合并上线 + 线上复验 + 总表需求 4 复核（2026-10-01） |
| `20261002-acceptance-leftovers-t13.md` | T13：总表 §2 遗留清单对齐 + 最终镜像 6h 长稳启动（2026-10-02） |
| `20261002-t12-merge-deploy-q2-closeout.md` | T12：T10+T11 合并上线 + 线上复验 + Q2 结案（2026-10-02） |
| `20261002-t19-merge-deploy.md` | T19：四分支合并上线 + 线上复验 + 结项快照（2026-10-02） |
| `m6-redeploy-20260929.md` | 现网应用镜像重部署（对齐 main：M5 闸门 + /metrics）（2026-09-29） |
| `redeploy-news-20260929.md` | 时效性验收报告（验收项 5.2-7） |
| `redeploy-selfcheck-20260929.md` | M4-4.3 客户端联调自检报告 |

### 决策 / 结案 / 评估（8）

| 文件 | 标题 |
| --- | --- |
| `20260930-p7-ranking-followups.md` | P7：P1 两处欠账（幂等 + 召回证据）（2026-09-30） |
| `20261002-gate-adaptive-assessment.md` | 「闸门上限对上游健康度自适应」评估（遗留 #2）：先盘点坏日样本 |
| `20261002-tls-renewal-assessment.md` | TLS 续期评估（遗留 #5）：结论 ① —— 续期已自动化且 80/443 有保障，降为「运维常识项」 |
| `20261002-zh-rss-pool-benefit.md` | 中文新鲜源增强评估：「报刊 RSS 当最新新闻池」的收益上限（T17，失败结案） |
| `m2-9-sampling-policy-20261001.md` | 2-9 采样口径登记 + 结项总表诚实修正（2026-10-01） |
| `m2-9-sampling-variance-20261001.md` | 2-9 采样波动实测（只测不判） |
| `m6-news-freshness-decision-20260930.md` | news 时效：日期可信度分组、门槛新口径、时效降级信号（2026-09-30） |
| `m6-zh-fresh-source-20260930.md` | 2-9 结案结论 + 中文新鲜源可行性（2026-09-30） |

### 方案设计 / 规划（3）

| 文件 | 标题 |
| --- | --- |
| `20261001-topic-relevance-gate-plan.md` | 「主题相关性闸门」立项方案（治 Q2：最近一周 AI 行业动态） |
| `m5-6-query-expansion-plan-20260928.md` | M5-6 查询改写 / 多查询扩展 —— 可行性分析与实施方案（2026-09-28） |
| `m6-env-wiring-plan-20260930.md` | 容器 env 接线方案（只写方案，不改 compose / 不改 .env）（2026-09-30） |

### 运维交付（11）

| 文件 | 标题 |
| --- | --- |
| `20260930-ops-check-fix.md` | P6 修复：P2×P3 交叉缺陷（加密备份被巡检误报）+ 分卷保留策略（2026-09-30） |
| `20260930-ops-check-plus.md` | P2 巡检增强 + 坏日样本积累（2026-09-30） |
| `20260930-p3-backup-encryption.md` | P3 备份机密治理：对称加密 + 口令保管 + 解密恢复演练（2026-09-30） |
| `20260930-p4-3-9-client-config-pack.md` | 3-9 客户端「复制即用」配置包（2026-09-30） |
| `20261001-backup-retention-fix.md` | P8 修复：backup.sh 保留策略只扫单层目录（旧备份永远清不掉）（2026-10-01） |
| `20261001-backup-retention-hardening.md` | P9 加固：保留策略的排除名单 + 永不删光（2026-10-01） |
| `20261002-clients-sim.md` | 各客户端仿真联调报告 |
| `20261002-mcp-stdio-linux-path-docs.md` | MCP stdio 接入：补 Linux/macOS 路径 + 澄清 `Auth: Unsupported`（2026-10-02） |
| `20261002-repo-cleanup.md` | 仓库清理：docs/reports 与 data/ 瘦身（2026-10-02） |
| `m6-ops-hardening-20260930.md` | 运维交付收尾：自愈 + 日志轮转 + 巡检告警 + 备份恢复 + 手册（2026-09-30） |
| `recall-ab-usage-20261001.md` | `scripts/recall_ab.py` 使用说明（受控回放） |

### 兼容性与客户端（3）

| 文件 | 标题 |
| --- | --- |
| `m6-tavily-compat-20260928.md` | M6 Tavily 兼容性逐字段核对与补齐（2026-09-28，含同日收口：校验错误码 422 → 400） |
| `tavily-official-search-20260928.md` | Tavily 官方 `/search` 字段清单（留档，2026-09-28 抓取） |
| `tavily-search-response-example-20260928.json` | 数据 / 日志（csv / json） |

### 功能实现与加固（23）

| 文件 | 标题 |
| --- | --- |
| `20260930-p1-ranking-form-downrank.md` | P1 排序层形态降权 + P5 英文时新意图硬过滤（2026-09-30） |
| `20261001-t5-q6-q16-fix.md` | T5：Q6/Q16 稳定缺陷修复（诊断 → 改动 → 受控回放复测） |
| `20261001-t6-paired-and-margin.md` | T6：对拍证据 + 三条缺陷修复 + 把 90% 抬出压线（2026-10-01） |
| `20261001-t7-q1-forms.md` | T7：Q1 的受控对拍与召回证据 + 三类坏形态修复（2026-10-01） |
| `20261002-registry-form-t15.md` | T15：registry/包索引判据扩展为「路径+标题形态」（治 docker mirror 页） |
| `20261002-topic-relevance-gate-t10.md` | T10：AIHOT 误剔除修复 + 主题相关性降级信号（`no_relevant_results`） |
| `20261002-topic-relevance-gate-t11.md` | T11：新闻意图 × 内容页形态（T9 方案①）+ 内容农场漏网形态（C） |
| `README.md` | docs/reports/ —— 验收报告留痕 |
| `m2-9-relevance-20260928.md` | 相关性抽检报告（验收项 2-9） |
| `m5-5.1-bench-engines-20260924.md` | 引擎健康度自适应 A/B 基准（M5-5.1 验收 5.1-13） |
| `m5-5.2-news-timeliness-20260924.md` | 时效性验收报告（验收项 5.2-7） |
| `m5-5.3-news-timeliness-ab-20260924.md` | 时效性配对 A/B（M5-5.3 回归，验收项 5.2-7 的回归保护） |
| `m5-concurrency-gate-20260927.md` | M5 上游并发闸门 + 过载快速返回 验收报告（2026-09-27，2026-09-28 修订） |
| `m6-engine-inventory-20260928.md` | M6 引擎集合盘点（2026-09-28，只读实测） |
| `m6-engine-selection-20260928.md` | 引擎集合优化 阶段 1：现网复测 + 候选评估 + 替换方案（2026-09-28） |
| `m6-engine-swap-20260929.md` | M6 引擎集合优化 阶段 2：替换实施与验收（2026-09-29） |
| `m6-env-engines-20260930.md` | 引擎列表落地到产品路径（.env）与复验（2026-09-30） |
| `m6-env-wiring-applied-20260930.md` | 容器 env 接线实施（让 `.env` 真正对容器生效）（2026-09-30） |
| `m6-news-freshness-20260930.md` | news 时效收口：新鲜度判据 + Bing 让位 + 撤 sina + 探测加固（2026-09-30） |
| `m6-news-sina-20260930.md` | news 时效：sina 落地 + 按引擎 time_range 白名单（2026-09-30） |
| `m6-query-expansion-measurement-20260928.md` | M6 阶段 1：查询扩展埋点测量报告（2026-09-28） |
| `m6-query-expansion-pool-ab-20260928.md` | M6 阶段 2a：候选池上限实验报告（2026-09-28） |
| `m6-relevance-hardening-20260930.md` | 通用相关性加固：规格 token + 兜底闸门 + 聚合页口径对齐（2026-09-30） |

### 长稳与压测日志（16）

| 文件 | 标题 |
| --- | --- |
| `redeploy-soak-6h-20260929.csv` | 数据 / 日志（csv / json） |
| `redeploy-soak-6h-20260929.json` | 数据 / 日志（csv / json） |
| `soak-24h-closeout.csv` | 数据 / 日志（csv / json） |
| `soak-24h-closeout.json` | 数据 / 日志（csv / json） |
| `soak-6h-envwiring.csv` | 数据 / 日志（csv / json） |
| `soak-6h-envwiring.json` | 数据 / 日志（csv / json） |
| `soak-6h-freshness.csv` | 数据 / 日志（csv / json） |
| `soak-6h-freshness.json` | 数据 / 日志（csv / json） |
| `soak-final-image-6h.csv` | 数据 / 日志（csv / json） |
| `soak-final-image-6h.json` | 数据 / 日志（csv / json） |
| `soak-t12-1h.csv` | 数据 / 日志（csv / json） |
| `soak-t12-1h.json` | 数据 / 日志（csv / json） |
| `soak-t4-1h.csv` | 数据 / 日志（csv / json） |
| `soak-t4-1h.json` | 数据 / 日志（csv / json） |
| `soak-t8-1h.csv` | 数据 / 日志（csv / json） |
| `soak-t8-1h.json` | 数据 / 日志（csv / json） |

## 2. 人工项

协议、参数、鉴权、限流由 `scripts/mcp_selfcheck.py` 覆盖（最近一次 24/24 通过，见 `20260930-p4-3-9-client-config-pack.md`）；
真实客户端联调已按自动化仿真结案（见 `20261002-clients-sim.md`、`manual-acceptance-checklist-20260928.md`）。

## 3. 复现与打分

复现命令写在各自报告里；2-9 相关性打分的登记口径（固定 commit + 20 条查询 + `--no-cache` + 单并发 + ≥3 轮取中位、中位 ≥18/20）见 `m2-9-sampling-policy-20261001.md`，
打分脚本用法见 [`recall-ab-usage-20261001.md`](recall-ab-usage-20261001.md)。
