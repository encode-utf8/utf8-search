# T12：T10+T11 合并上线 + 线上复验 + Q2 结案（2026-10-02）

> 范围：①合并 `fix/topic-relevance-gate-20261001`（f0c852f）→ main；②部署（回滚锚点 `dc7b5f4257ff`）；
> ③线上复验（含新字段 REST/MCP 双验）；④Q2 按出口结案 + 遗留登记。约束：未动闸门参数、`.env`、人工项 3-9。

## 0. 结论摘要

| 项 | 结果 |
| --- | --- |
| 合并 | `ff5a4ae`（`--no-ff`）；离线 **364 passed / 4 deselected**（与预期一致）；已推送 main |
| 部署 | 新镜像 **`3a521d3e6f9d`**；**停机 8.3s**；回滚锚点 `pre-t12-20261002` = `dc7b5f4257ff`；searxng/caddy 未动 |
| 线上 2-9（登记口径 3 轮） | **19/19/19 → 中位 19、最低 19（≥18）✅**；Q2 = 1/0/1 且 3/3 轮降级 |
| 新字段验证 | **REST 与 MCP 各一次**：无料查询均返回 `degraded=true` + `degraded_reason="no_relevant_results"` ✅ |
| 其它复验 | selfcheck **24/24**、鉴权 401/200、`/metrics` 无 error/rejected、巡检 `[OK] exit=0` |
| Q2 结案 | 登记为**已知上游限制**；「主题相关性闸门」立项**关闭**；新遗留「registry 判据扩展」已入 `docs/04` §8 第 16 条 |

## 1. 合并与部署

| 步骤 | 结果 |
| --- | --- |
| 合并 | `git merge --no-ff fix/topic-relevance-gate-20261001` → **ff5a4ae**（无冲突） |
| 离线套件 | **364 passed / 4 deselected** |
| 推送 / 工作区 | `push c5eb1ac..ff5a4ae main`；工作区在 main（cron 跟随） |
| 回滚锚点 | `pre-t12-20261002` = **`dc7b5f4257ff`**（部署前镜像） |
| 备份 | `docker-compose.yml` / `.env` → `/var/backups/utf8-search/deploy-backups-20261001/t12-pre-deploy-*`（env 600） |
| 构建 / 上线 | build **54.2s**；`up -d --no-deps utf8-search` **停机 8.3s** → 新镜像 **`3a521d3e6f9d`** |

## 2. 线上复验

### 2.1 协议与鉴权

* `mcp_selfcheck.py --base-url http://127.0.0.1:8000`：**24/24 全通过（exit 0）**；
* 鉴权：无 Key → **401**、对 Key → **200**；
* `/metrics`：`requests_total{result="ok"}` 正常推进、**无 `result="error"`、无 `rejected_total`**；
* 巡检：`ops_check.py` → `[OK] health=200 error=0.0 rejected=0`，**exit=0**。

### 2.2 新字段（`no_relevant_results`）线上双通道验证

用无料查询「最近一周 AI 行业动态」+ 尾空格绕缓存：

```
REST : degraded=True  | reason=no_relevant_results | n=5
MCP  : isError=False  | degraded=True              | reason=no_relevant_results
```

两通道一致，且返回的是"现有能给的 5 条"（npm `nocache`/StackOverflow 等）+ 明确的降级信号，
没有硬凑、也没有丢字段（Tavily 标准字段语义未动）。

### 2.3 2-9（登记口径：HTTP、绕缓存、单并发、轮间 65s、3 轮取中位）

> run1 首次采集因**我自己的 REST/MCP 验证**先打了同样的尾空格，导致 1 条缓存命中；
> 已用 5 空格后缀**重跑一轮冷查询（run1b，cached=0）**，下表用 run1b/run2/run3。

| 轮次 | 窗口 | 相关数 ≥4 的查询 | 平均相关 | <4 的查询 | 降级条目 |
| --- | --- | --- | --- | --- | --- |
| run1b（冷） | 00:57:32 → 00:57:47 | **19/20 = 95%** | 4.60 | Q2(1) | 仅 Q2 |
| run2 | 00:54:44 → 00:54:59 | **19/20 = 95%** | 4.60 | Q2(0) | 仅 Q2 |
| run3 | 00:56:04 → 00:56:20 | **19/20 = 95%** | 4.60 | Q2(1) | 仅 Q2 |

**中位 19/20、三轮最低 19（≥18）✅**；Q1 三轮 5/5/5；
逐条中位口径 19/20 = 95%（唯一未达标仍是 Q2 —— 已按 §3 结案）。

### 2.4 1h 回看（cooling / rejected / 延迟）

部署后启动 1h 观测长稳（`soak.py --duration-hours 1 --interval 300 --unique --http-url http://127.0.0.1:8000`，
PID **459054**，00:58:23 起，预计 01:58:23 结束；首采样 OK/1180ms/5 条）。
结果见 §3（跑满后回填）。

## 3. 1h 回看结果（跑满后回填）

`--summarize`（00:58:24 → 01:58:26，覆盖 1.00h，**11 个计入样本**（13 行含 2 预热））：

| 指标 | 值 |
| --- | --- |
| 可用率 | **100%**（空结果 / 异常 / 跳过 = 0 / 0 / 0） |
| 延迟 | **P50 1424ms / P95 2600ms / max 2600ms / mean 1750ms** |
| 内存（容器 RSS） | 119.1MB（最低）/ 120.2MB（末次 = 峰值）；中位 119.3 → 120.0MB（+0.6%） |
| `/metrics` 终值 | `requests_total{result="ok"} 111`；**无 `result="error"`、无 `rejected_total` 序列** |
| `/health` cooling 终值 | 4 个（resulthunter timeout、google captcha、brave rate_limit、privacywall denied）；窗口内 3–6 波动 |

窗口内 12 个 5 分钟快照（`requests_ok` 89→111 单调推进，error/rejected 序列始终 0）：

```
01:04 samples=2  lat=2546ms requests_ok=89 cooling=6
01:09 samples=3  lat=1407ms requests_ok=91 cooling=5
01:14 samples=4  lat=1199ms requests_ok=93 cooling=5
01:19 samples=5  lat=1360ms requests_ok=95 cooling=5
01:24 samples=6  lat=2550ms requests_ok=97 cooling=5
01:29 samples=7  lat=1424ms requests_ok=99 cooling=5
01:34 samples=8  lat=1131ms requests_ok=101 cooling=5
01:39 samples=9  lat=1516ms requests_ok=103 cooling=3
01:44 samples=10 lat=1001ms requests_ok=105 cooling=4
01:49 samples=11 lat=2508ms requests_ok=107 cooling=3
01:54 samples=12 lat=2600ms requests_ok=109 cooling=4
01:59 samples=13 lat=2556ms requests_ok=111 cooling=4（finished）
```

⇒ 新镜像（T10/T11 全部上线）**无 429、无 error、可用率 100%**，延迟处于基线水平（P95 2.6s，与 24h 基线 2.57s 同量级）；
cooling 波动来自免费引擎的 rate limit / CAPTCHA，属常态。

## 4. Q2 结案（按 T9 出口条款）

登记内容（三处同步）：

* `docs/reports/m6-project-acceptance-20260930.md` 需求 4 备注：**Q2 属已知上游限制** ——
  无料时如实降级 `no_relevant_results`（线上 REST + MCP 已验），有料时的换位收益已在**受控对拍**（`replay_pool.py`）中验证；
  **「主题相关性闸门」立项已关闭**；
* `checklist.md` 顶部结论 + 2-9 行：同步结案口径（6 达标 / 2 有明确限制 / 0 未做不变）；
* `docs/04` §8 第 16 条：记录 T9→T12 的完整链路（立项 → 实施 → 验收 → 结案）与**新遗留**。

**新遗留（已登记）**：registry 判据从「域名白名单」扩展为「**路径/标题形态**」
（`/formula|package|project|镜像下载/` + 版本号等），以覆盖 `docker.aityp.com` 这类 mirror 页 ——
这是 T11 线上 Q6 中位 5→4 的诱因（上游漂移引入；固定池对拍已证与规则零因果）。

## 5. 回滚与产物

* 回滚：`docker tag utf8-search-utf8-search:pre-t12-20261002 utf8-search-utf8-search:latest && docker compose up -d --no-deps utf8-search`（上次实测 8.3s 恢复）；
* 未动：闸门参数、`settings.yml`、`.env`、人工项 3-9；
* 证据：`docs/reports/m29-t12-20261002-{run1b,run2,run3}-{brief.md,gate.json,scores.csv,meta.json}`、`data/soak-t12-1h.{csv,json}`（入库 `docs/reports/`）。
