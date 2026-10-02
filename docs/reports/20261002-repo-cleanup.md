# 仓库清理：docs/reports 与 data/ 瘦身（2026-10-02）

> 分支 `chore/repo-cleanup-20261002`；口径 = **只留开发结果验证 / 方案设计 / 反馈 / 日志**，测试与实验的过程明细一律清掉。

## 0. 一句话结论

`docs/reports` **284 → 80**（删 **205** 个、-3.50 MB）；`data/` **40 → 1**（删 **39** 个、-3.85 MB）。`src/`、`scripts/`、`tests/`、`checklist.md` 正文、`.env` / `settings.yml` / 闸门参数、线上容器 **零改动**。

## 1. 保留口径

| 类别 | 留什么 | 例子 |
| --- | --- | --- |
| 结项与验收 | 结项总表、人工验收操作单、阶段验收 | `m6-project-acceptance-20260930.md` |
| 部署 / 合并 / 上线 | 每次上线与合并的收尾报告 | `20261002-t19-merge-deploy.md` |
| 决策与结案 | 评估结论、可行性结论（含失败结案） | `20261002-tls-renewal-assessment.md` |
| 方案设计 | 规划 / 路线 / 计划书 | `20261001-topic-relevance-gate-plan.md` |
| 功能实现 | 每条功能或加固一份实现报告 | `20261002-registry-form-t15.md` |
| 运维交付 | 手册、备份、巡检、客户端仿真 | `m6-ops-hardening-20260930.md` |
| 日志 | 长稳与压测 csv/json | `soak-*.{csv,json}` |
| 被引用 | `src/` `scripts/` `tests/` `docs/00-05` `checklist.md` `docker-compose.yml` 直接引用的 | `tavily-search-response-example-20260928.json`（测试 fixture） |

## 2. 删除口径（测试 / 实验 / 过程明细）

- **2-9 逐轮采样明细**：`m29-*`（brief / scores / judge / meta / gate）
- **2-9 早期单轮报告与打分**：`m2-9-*-{brief,scores,judge}`、`m2-9-pool24-*`、`m2-9-agent-preliminary-*`
- **候选池 / 对拍 / 诊断原始 JSON**：`t*-pool-*`、`t*-paired-*`、`t*-rule-stats-*`、`t5-q6-q16-{diagnosis,after-fix}`
- **引擎与环境的探针 / AB 扫描原始数据**：`engine-*-probe*`、`engine-*-fanout*`、`engine-swap-sweep-*`、`engine-swap-applist-compare-*`、`engine-list-env-*`（compare / decompose / gate / hygiene）、`env-wiring-*`、`hygiene-*-swap.json`
- **部署过程原始回显**：`redeploy-{health,public-health,metrics,public-metrics,loadtest,gate-burst429,hygiene}-*`
- **被后续报告取代的中间件**：`m5-5.3-{relevance-after,relevance-legacy,rank-ab-same-candidates,hygiene-*}`
- **结论报告已覆盖的原始数据**：`zh-rss-pool-benefit-20261002.json`、`zh-rss-pool-benefit-20261002-detail.md`
- **`data/`**：M4/M5/M6 期测量产物（bench / news-check / rank-ab / rel53 / relevance / loadtest / soak-24h 系列）与运行时缓存（`cache.db*`、`soak-cache.db`）

## 3. 引用完整性

清理前后对全部保留文档做了 Markdown 链接扫描：仅 `m5-6-query-expansion-plan-20260928.md` → `m6-query-expansion-pool-ab-20260928.md` 一处会断 ⇒ **已恢复该文件**，复扫 **0 处断链**。
说明：`checklist.md §8` 与部分历史报告正文里写的"证据"路径仍指向已删的过程明细 —— 它们仍在 git 历史中（`git log --diff-filter=D -- <path>` 可取回），历史正文未改。

## 4. data/ 说明

`data/` 被 `.gitignore` 整体忽略（0 个受版本控制文件）⇒ 删除**不可由 git 恢复**；已逐项确认删除的都是测量产物与运行时缓存（缓存会按 `CACHE_QUERY_TTL` 自动重建），与运行/使用无关。
唯一保留 `data/searxng-default.yml` = Stock SearXNG 默认配置基线（便于与 `searxng/settings.yml` 做差异对照）；如认为无用可再删。

## 5. 服务器 `data/` 同步清理（同一口径）

对 `root@43.106.104.49:/root/utf8-search/data/` 按同一口径清理（脚本**先打印清单再删**，并逐条校验目标路径必须落在 `/root/utf8-search/data/` 内）：

| 项 | 清理前 | 清理后 |
| --- | --- | --- |
| 文件数 | 158 | **9** |
| 占用 | 19 MB | 16 MB |

- **保留（9）**：`cache.db` / `cache.db-shm` / `cache.db-wal`（`./data:/app/data` 绑定挂载，运行中的容器在用）、`ops-check.log` / `ops-check.cron.log` / `ops-check-state.json` / `ops-metrics-snapshot.csv` / `backup.cron.log`（5 分钟巡检与每日备份 cron 正在写；其中 `ops-metrics-snapshot.csv` 是**闸门自适应立项的在采数据源**）、`caddy-local-root.crt`（客户端信任本地 CA 用）。
- **删除**：`data/measure/**`（14 个子目录的测量证据）、`data/plan/**`、全部 `soak-*`（历史长稳明细；结论已入 `docs/reports/soak-*`）、`selfcheck-t19.md`、`recall-ab.json`、`final-s2-ow1.0-n10.json`。
- **删后自检**：三容器 `healthy`（app / caddy / searxng），`http://127.0.0.1:8000/health` = **200**；磁盘 15G/59G（27%）不变。
- ⚠️ 与本地同理：服务器 `data/` 不在 git 中 ⇒ 删除**同样不可由 git 恢复**；`soak-t19-1h.*` 与 `selfcheck-t19.md`（T19 上线复验证据）已随本轮删除，其数字保留在 `docs/reports/20261002-t19-merge-deploy.md`。Caddy 证书在命名卷 `caddy_data` 中，**未触碰**。

## 6. 保留清单（80 个）

- `20260930-ops-check-fix.md`
- `20260930-ops-check-plus.md`
- `20260930-p1-ranking-form-downrank.md`
- `20260930-p3-backup-encryption.md`
- `20260930-p4-3-9-client-config-pack.md`
- `20260930-p7-ranking-followups.md`
- `20261001-backup-retention-fix.md`
- `20261001-backup-retention-hardening.md`
- `20261001-t4-merge-deploy-backfill.md`
- `20261001-t5-q6-q16-fix.md`
- `20261001-t6-paired-and-margin.md`
- `20261001-t7-q1-forms.md`
- `20261001-t8-merge-deploy.md`
- `20261001-topic-relevance-gate-plan.md`
- `20261002-acceptance-leftovers-t13.md`
- `20261002-clients-sim.md`
- `20261002-gate-adaptive-assessment.md`
- `20261002-mcp-stdio-linux-path-docs.md`
- `20261002-registry-form-t15.md`
- `20261002-t12-merge-deploy-q2-closeout.md`
- `20261002-t19-merge-deploy.md`
- `20261002-tls-renewal-assessment.md`
- `20261002-topic-relevance-gate-t10.md`
- `20261002-topic-relevance-gate-t11.md`
- `20261002-zh-rss-pool-benefit.md`
- `README.md`
- `env-selfcheck-linux-20260925.md`
- `m2-9-relevance-20260928.md`
- `m2-9-sampling-policy-20261001.md`
- `m2-9-sampling-variance-20261001.md`
- `m4-4.2-deploy-20260925.md`
- `m4-4.2-deploy-selfcheck-20260925.md`
- `m4-4.3-client-selfcheck-20260924.md`
- `m4-4.4-soak-24h-20260926.md`
- `m4-4.4-soak-coverage-floor-20260926.md`
- `m5-5.1-bench-engines-20260924.md`
- `m5-5.2-news-timeliness-20260924.md`
- `m5-5.3-news-timeliness-ab-20260924.md`
- `m5-5.3-verification-20260924.md`
- `m5-6-query-expansion-plan-20260928.md`
- `m5-concurrency-gate-20260927.md`
- `m6-engine-inventory-20260928.md`
- `m6-engine-selection-20260928.md`
- `m6-engine-swap-20260929.md`
- `m6-env-engines-20260930.md`
- `m6-env-wiring-applied-20260930.md`
- `m6-env-wiring-plan-20260930.md`
- `m6-news-freshness-20260930.md`
- `m6-news-freshness-decision-20260930.md`
- `m6-news-sina-20260930.md`
- `m6-ops-hardening-20260930.md`
- `m6-project-acceptance-20260930.md`
- `m6-query-expansion-measurement-20260928.md`
- `m6-query-expansion-pool-ab-20260928.md`
- `m6-redeploy-20260929.md`
- `m6-relevance-hardening-20260930.md`
- `m6-tavily-compat-20260928.md`
- `m6-zh-fresh-source-20260930.md`
- `manual-acceptance-checklist-20260928.md`
- `recall-ab-usage-20261001.md`
- `redeploy-news-20260929.md`
- `redeploy-selfcheck-20260929.md`
- `redeploy-soak-6h-20260929.csv`
- `redeploy-soak-6h-20260929.json`
- `soak-24h-closeout.csv`
- `soak-24h-closeout.json`
- `soak-6h-envwiring.csv`
- `soak-6h-envwiring.json`
- `soak-6h-freshness.csv`
- `soak-6h-freshness.json`
- `soak-final-image-6h.csv`
- `soak-final-image-6h.json`
- `soak-t12-1h.csv`
- `soak-t12-1h.json`
- `soak-t4-1h.csv`
- `soak-t4-1h.json`
- `soak-t8-1h.csv`
- `soak-t8-1h.json`
- `tavily-official-search-20260928.md`
- `tavily-search-response-example-20260928.json`
