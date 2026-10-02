# T19：四分支合并上线 + 线上复验 + 结项快照（2026-10-02）

> 本轮按用户拍板执行：**T15 → T16 → T17 → T18 依序 `--no-ff` 合并进 main**（每条合完即跑离线套件），
> 随后**只重建 app 容器**（searxng / caddy 不动）把 T15 的 rank 层修复上线，做线上复验与结项快照。
> 约束遵守：**未改 `.env` / `settings.yml` / 闸门参数默认值**；未用 `git worktree`
> （本机 `.venv` 是 editable 安装、指向主仓库 `src/`，复测一律在主仓库切分支跑）。

## 0. 结论摘要

| 项 | 结果 | 性质 |
| --- | --- | --- |
| 合并 | 4 条分支按序 `--no-ff` 合并（`bb34b19` / `5deb65b` / `079699d` / `6db27a6`）；checklist §8 冲突按并集解决 | 实测 |
| 离线套件 | 每条合并后均 **380 passed / 4 deselected** | 实测 |
| 部署 | 回滚锚点 `pre-t19-20261002` = `3a521d3e6f9d`；build **60.3s**；`up -d` 命令 3.9s；**停机 6.55s**；新镜像 **`258749c7a318`** | 实测 |
| 配置面 | `.env` / `docker-compose.yml` 部署前后 **sha256 完全一致**；searxng / caddy 未动 | 实测 |
| 自检/鉴权 | `mcp_selfcheck.py` **24/24（exit 0）**；鉴权 **401 / 401 / 200** | 实测 |
| 指标/巡检 | `/metrics`：`result="error"`=0、`rejected_total`=0、`requests_total{ok}` 正常推进；`ops_check.py` **[OK] exit 0** | 实测 |
| 2-9（登记口径 3 轮） | **19/19/19（中位 19、最低 19 ≥18）**；平均相关 4.80 / 4.60 / 4.55；0 缓存命中 | 实测（agent 初评 + 校准集 + 盲评） |
| Q6 专项 | **5/5/5**（`docker.aityp.com` 镜像页三轮零出现 —— T15 修复上线生效） | 实测 |
| 1h 回看 | 可用率 **100%**（11 计入）；P50 **1353ms** / P95 2598ms；窗口内 **429 = 0**（闸门与 RPM 均未触发）；RSS 未采样（如实记录，见 §4.3） | 实测 |
| 遗留 | 仅两项「等触发」：①闸门上限自适应（等坏日样本）②证书续期核对（2026-11-24 前后只读核对一次） | 实测/文档 |

## 1. 合并（每条合完即跑离线套件）

| 顺序 | 分支 | 源提交 | 合并提交 | 合并后离线套件 | 冲突 |
| --- | --- | --- | --- | --- | --- |
| 1 | `fix/registry-form-20261002`（T15） | `96132c3` | **`bb34b19`** | 380 passed / 4 deselected | 无 |
| 2 | `fix/gate-adaptive-assessment-20261002`（T16） | `03d938b` | **`5deb65b`** | 380 passed / 4 deselected | `checklist.md` §8（并集） |
| 3 | `feat/zh-rss-pool-eval-20261002`（T17） | `5219708` | **`079699d`** | 380 passed / 4 deselected | `checklist.md` §8（并集） |
| 4 | `docs/tls-renewal-20261002`（T18） | `2584702` | **`6db27a6`** | 380 passed / 4 deselected | `checklist.md` §8（并集） |

* 合并前 `main` = `7fe8b80`（与 `origin/main` 一致）；
* checklist §8 的三次冲突都是「双方各自在文件末尾追加工作记录」：删除冲突标记、**两侧记录都保留**（T15 → T16 → T17 → TLS 四条按序并列），无内容取舍；
* 离线套件数字与预期一致（T15 自带 5 条新单测：375 → 380）。

## 2. 文档回落与复测规范落档

* **T16 报告数字回填**：`docs/reports/20261002-gate-adaptive-assessment.md` 的
  「375 passed / 4 deselected（本分支基于 main，未含 T15 的 5 条新单测）」改为
  **380 passed / 4 deselected**（T15 合入后的合并态实测；T16 自身纯文档、不改单测）；
* **总表 §2 遗留清零**：
  * **#4 中文新鲜源** → ✅ **已结案（T17 失败结论）**：固定池回放 3 轮，**有改善查询 = 0 条**、
    中文 news 时效 **28.2% → 36.6%（+8.5pp < 10pp）** ⇒ 两条硬性停用判据同时触发，不新增 provider/开关，
    维持「已知限制 + `freshness_unverified`」；
  * **#9 registry 判据** → ✅ **已闭环（T15，本轮部署上线）**：路径 + 标题形态判据，固定池对拍 Q6
    的 `docker.aityp.com/image/...` mirror 页被剔除；线上 Q6 三轮 **5/5/5**。
* **复测规范**（本轮新增，防再次踩 worktree 坑）：
  * `docs/04` §5.3 受控回放清单新增 **⑧ 复测环境**：editable venv 指向主仓库 `src/`，
    复测必须主仓库切分支并记 commit；**不要用 `git worktree`**；
  * `docs/05` §14.9 新增「复测环境」小节（含 cron 跟随工作区分支的提醒）。

## 3. 部署（实测）

```text
回滚锚点 tag : utf8-search-utf8-search:pre-t19-20261002 = 3a521d3e6f9d（= 部署前 latest）
build        : docker compose build utf8-search → real 1m0.346s
recreate     : docker compose up -d --no-deps utf8-search → real 0m3.939s
停机实测     : 6.55s（0.2s 探针：最后一次 200 → 首次恢复 200；期间 27 个非 200 采样）
新镜像       : 258749c7a318（容器 StartedAt 2026-10-02T11:43:18Z；6s 内 healthy）
searxng/caddy: 未重启（容器 uptime 保持 2d / 3d）
```

| 面 | 部署前 sha256 | 部署后 sha256 | 结论 |
| --- | --- | --- | --- |
| `.env` | `314a2064…e6195947` | `314a2064…e6195947` | 未变 |
| `docker-compose.yml` | `8367e248…4ac3b9736d` | `8367e248…4ac3b9736d` | 未变 |

## 4. 线上复验

### 4.1 协议 / 鉴权 / 指标 / 巡检

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| `mcp_selfcheck.py` | **24/24 通过、exit 0** | `data/selfcheck-t19.md` |
| 鉴权 | 无 Key **401** / 错 Key **401** / 对 Key **200** | 本轮实测（3 条请求） |
| `/metrics` | `upstream_requests_total{result="ok"}=67`（推进中）、`error`=0、`rejected_total`=0 | 本轮实测 |
| `ops_check.py` | `[OK] health=200 error=0.0 rejected=0 冷却引擎=[brave, resulthunter, privacywall, yep, google, google news]`，**exit 0** | `data/ops-check.log` |

> 如实记录一次调用姿势错误：首次跑自检**没带 `--api-key`**，脚本用了默认 Key `selfcheck-key` ⇒ 8 项 401 失败
> （共 21 项、通过 13）。换成 `.env` 里的真实 Key 复跑后 **24/24 全通过**。这不是服务缺陷。
>
> `google` / `google news` 在 cooling 列表中属**既有基线**（CAPTCHA 处罚盒，非本轮引入；
> 见 `m6-env-engines-20260930.md` 附录与 T17 报告）。

### 4.2 2-9（登记口径：HTTP、绕缓存、单并发、轮间 65s、3 轮取中位）

**方法**：`POST /v1/search`（已部署服务）、单并发、每条查询尾随 5/6/7 个空格绕缓存（三轮 `cached` 全部为 `False`）、
轮间 65s；判分 = **agent 初评（盲评：只看标题/域名/摘要，不看来源标签；三档 明显相关/勉强相关 → 1、不相关 → 0）**。
校准集：本轮出现的**历史 ❌ 形态**（东方财富行情页、Wheeler School 校方政策页、淘宝数码网首页）**全部判 0**；
历史 ❌ 形态（`docker.aityp.com` 镜像页、V2EX 会员页、brew formula 页）**三轮零出现**。

| 轮次 | 窗口 | 相关 ≥4 的查询 | 平均相关 | <4 的查询 | 降级 |
| --- | --- | --- | --- | --- | --- |
| run1 | 19:44:29 → 19:45:10 | **19/20 = 95%** | 4.80 | Q2（3/5） | 无 |
| run2 | 19:45:54 → 19:46:35 | **19/20 = 95%** | 4.60 | Q2（0/5） | Q2 `no_relevant_results` |
| run3 | 19:47:17 → 19:47:58 | **19/20 = 95%** | 4.55 | Q2（0/5） | Q2 `no_relevant_results` |

**中位 19/20、三轮最低 19（≥18）✅**；**Q6（Python 3.13 新特性）三轮 = 5/5/5 ✅**
（`docker.aityp.com` 镜像页零出现，T15 修复在线上生效）。

逐条口径：唯一未达标仍是 **Q2「最近一周 AI 行业动态」** —— run1 池内有 3 条切题（知乎周报/周刊/ai-bot），
run2/run3 上游池漂移到 `nocache` 工具页（0 条切题）但**如实降级 `no_relevant_results`**；
与 T12 结案一致：**属已知上游限制，不硬凑**。

对照 T12 基线（也是 19/19/19、唯一未达标 Q2）：**未新增不达标查询**，且 **Q6 由 T12 的 4/4/5（中位 4）
提升到 5/5/5** —— 这正是 T15 registry 形态修复在本轮上线的效果（其它查询的中位数无下降）。
因三轮最低 19 ≥18，**未触发**「用固定池对拍证明因果」的备用条款。

### 4.3 1h 回看

**实测（跑满后回填）**：

* 命令：`scripts/soak.py --duration-hours 1 --interval 300 --unique --http-url http://127.0.0.1:8000`
  （PID **595374**，2026-10-02 **19:49:00 → 20:49:02**，打已部署服务）；
* `--summarize`：覆盖 **1.00h**、采样 13 行 = 2 预热 + **11 计入**、**可用率 100%**
  （0 空结果 / 0 异常 / 0 跳过、采样覆盖率 100%），延迟 **P50 1353ms / P95 2598ms / max 2598ms / mean 1546ms**；
* **无 429**：窗口内 app 容器日志 `429` 计数 = **0**（**闸门与 RPM 都没触发**，日志是区分手段）；
  `/metrics` 自 19:43 重建累计 `upstream_requests_total{result="ok"}=91`、**无 `result="error"`、无 `rejected_total`**；
* **RSS**：本轮 soak **未带 `--rss-pid`** ⇒ **1h RSS 趋势未判定（如实记录）**；
  容器当前单点内存 `docker stats` = **92.4MB**（20:52 采集，供后续对照）。

## 5. 结项快照（总表 §0 + checklist 顶部）

* 线上镜像 **`258749c7a318`**（回滚锚点 `pre-t19-20261002` = `3a521d3e6f9d`）；
* 8 条需求 = **7 达标 / 1 有明确限制 / 0 未做**（限制 = 中文新闻时效 `freshness_unverified`）；
* 2-9 按登记口径线上 3 轮 = **19/19/19（中位 19、最低 19）**，Q6 5/5/5；
* **人工项：无**；
* 剩余遗留 = 两项「等触发」：①闸门上限自适应（坏日样本继续采集，只登记不动代码）②证书续期核对
  （2026-11-24 前后只读核对一次；已降为运维常识项）。

## 6. 实测 / 文档 / 推断区分

| 内容 | 性质 |
| --- | --- |
| 合并提交/套件数字/停机时长/镜像 ID/哈希对比/selfcheck/鉴权/metrics/ops_check/2-9 三轮/Q6 | **本轮实测** |
| 回滚锚点回滚步骤、证书续期 ARI 排程 | 文档/上轮实测（T18 报告） |
| 「google 系冷却会自动恢复」「闸门自适应需要更多坏日样本」 | 推断（有历史证据支撑，非本轮结论的前提） |

## 7. 产物

* 本报告；2-9 三轮明细/模板/判定：`m29-t19-20261002-run{1..3}-{brief.md,meta.json,scores.csv,scores-judge.md}`；
* 自检报告 `data/selfcheck-t19.md`（运行产物，不入库）；1h 长稳 `data/soak-t19-1h.{csv,json,meta.json}`；
* `checklist.md` §8 工作记录 + 顶部最终状态快照；总表 §0/§2 已同步。
* 约束：未改 `.env` / `settings.yml` / 闸门参数默认值；未用 worktree；searxng / caddy 未重启。
