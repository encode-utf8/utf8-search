# T8：T5/T6/T7 合并上线 + 线上复验 + 总表需求 4 复核（2026-10-01）

> 范围：①合并 `fix/q6-q16-20261001`（6c79170）→ main；②服务器工作区切 main（cron 跟随）；
> ③开窗口部署（回滚锚点 `5694bdc297e2`）；④线上复验（selfcheck / 2-9 登记口径 3 轮 / 鉴权 / metrics /
> 巡检 / 1h 回看）；⑤总表需求 4 复核。约束：未动闸门参数、`.env`、`settings.yml`、人工项 3-9。

## 0. 结论摘要

| 项 | 结果 |
| --- | --- |
| 合并 | `fix/q6-q16-20261001` → main **3f8b0c4**（`--no-ff`，无冲突）；离线 **350 passed / 4 deselected**（与预期一致） |
| 部署 | 新镜像 **`dc7b5f4257ff`**；**停机 7.5s**；回滚锚点 `pre-t8-20261001` = `5694bdc297e2`；searxng/caddy 未动 |
| 线上 2-9（登记口径） | **19/19/19 → 中位 19/20 = 95%、三轮最低 19（≥18）✅** |
| 其它复验 | selfcheck **24/24**、鉴权 401/401/200、`/metrics` 无 error、巡检 `[OK] exit=0` |
| 总表需求 4 | 状态 **✅ 达标（按 2026-10-01 登记的采样口径）**；Q2 说明保留并指向「主题相关性闸门」；§0 计数同步为 **6/2/0** |

## 1. 合并与工作区

| 步骤 | 结果 |
| --- | --- |
| 合并 | `git merge --no-ff fix/q6-q16-20261001` → **3f8b0c4**（无冲突；checklist 追加无重叠） |
| 离线套件 | **350 passed / 4 deselected**（预期一致） |
| 推送 | `ccadc21..3f8b0c4 main` |
| 工作区 | 切到 main 并 `pull --ff-only`（cron 跟随工作区，脚本即最新） |

## 2. 部署窗口

| 项 | 值 |
| --- | --- |
| 回滚锚点 | `docker tag … pre-t8-20261001` = **`5694bdc297e2`**（部署前镜像） |
| 备份 | `docker-compose.yml` / `.env` → `/root/deploy-backups-20261001/t8-pre-deploy-{compose,env}-20261001-2058.*`（env 600） |
| 构建 | `docker compose build utf8-search` **53.2s** → 新镜像 **`dc7b5f4257ff`** |
| 上线 | `docker compose up -d --no-deps utf8-search`：recreate 2.7s；**`/health` 200 恢复 7.5s** |
| 未动 | searxng / caddy 未重启；端口矩阵不变 |

## 3. 线上复验

### 3.1 协议与鉴权

- `scripts/mcp_selfcheck.py --base-url http://127.0.0.1:8000`：**24/24 全通过（exit 0）**；
- 鉴权：无 Key → **401**、错 Key → **401**、对 Key → **200**；
- `/metrics`：`requests_total{result="ok"}` 正常推进、**无 `result="error"`、无 `rejected_total` 序列**；
- 巡检：`scripts/ops_check.py` → `[OK] health=200 error=0.0 rejected=0`，**exit=0**。

### 3.2 2-9（登记口径：线上 HTTP、绕缓存、单并发、轮间 65s、3 轮取中位）

三轮均 `cached=0/20`、`ok=20/20`（尾加 2/3/4 个空格保证冷查询）：

| 轮次 | 窗口 | 相关数 ≥4 的查询 | 平均相关 | <4 的查询 |
| --- | --- | --- | --- | --- |
| run1 | 21:01:15 → 21:01:32 | **19/20 = 95%** | 4.50 | Q2(0) |
| run2 | 21:02:37 → 21:02:55 | **19/20 = 95%** | 4.55 | Q2(1) |
| run3 | 21:04:00 → 21:04:19 | **19/20 = 95%** | 4.55 | Q2(1) |

**中位 19/20、三轮最低 19 ≥18 ⇒ 达标（按登记口径）**；Q1 三轮 5/5/5（T7 的三类形态修复在线上生效），
Q6/Q16 稳定在 4–5（V2EX/brew/Pinterest/Pro Max 均未再进 top5）。
**唯一未达标仍是 Q2**：三轮 top5 分别是 `nocache`（npm/SO/GitHub/Yarn）、DuckDuckGo（知乎/Reddit）、
Stack Overflow 缓存问答 —— 上游候选池漂移 + 主题匹配类，已立项「主题相关性闸门」。

> 口径外事件记录：三轮之间按要求各等 65s 避开 `RPM=60`，全程未触发限流 429；闸门 `rejected_total` 也始终为空。

### 3.3 1h 回看（cooling / rejected / 延迟）

部署后启动 1h 观测长稳（`soak.py --duration-hours 1 --interval 300 --unique --http-url http://127.0.0.1:8000`，
PID **416230**，21:05:04 起，预计 22:05:04 结束；首采样 OK/1188ms/5 条/RSS 135MB）。
结果见 §4（跑满后回填）。

## 4. 1h 回看结果（跑满后回填）

`--summarize`（21:05:05 → 22:05:05，覆盖 1.00h，**11 个计入样本**（13 行含 2 预热））：

| 指标 | 值 |
| --- | --- |
| 可用率 | **100%**（空结果 / 异常 / 跳过 = 0 / 0 / 0） |
| 延迟 | **P50 819ms / P95 1241ms / max 1241ms / mean 875ms** |
| 内存（容器 RSS） | 129.0MB（最低）/ 129.5MB（末次 = 峰值）；中位 129.0 → 129.3MB（+0.3%） |
| `/metrics` 终值 | `requests_total{result="ok"} 91`；**无 `result="error"`、无 `rejected_total` 序列** |
| `/health` cooling 终值 | 4 个（resulthunter timeout、brave rate_limit、google captcha、privacywall denied）；窗口内 4–6 波动，服务不受影响 |

窗口内 12 个 5 分钟快照（`requests_ok` 69→91 单调推进，error/rejected 序列始终 0，cooling 4–6）：

```
21:11 samples=2  lat=2340ms requests_ok=69 cooling=5
21:16 samples=3  lat=774ms  requests_ok=71 cooling=6
21:21 samples=4  lat=786ms  requests_ok=73 cooling=6
21:26 samples=5  lat=879ms  requests_ok=75 cooling=6
21:31 samples=6  lat=1241ms requests_ok=77 cooling=4
21:36 samples=7  lat=909ms  requests_ok=79 cooling=5
21:41 samples=8  lat=1159ms requests_ok=81 cooling=5
21:46 samples=9  lat=819ms  requests_ok=83 cooling=4
21:51 samples=10 lat=736ms  requests_ok=85 cooling=5
21:56 samples=11 lat=850ms  requests_ok=87 cooling=5
22:01 samples=12 lat=740ms  requests_ok=89 cooling=5
22:06 samples=13 lat=726ms  requests_ok=91 cooling=4（finished）
```

⇒ 新镜像（T5/T6/T7 全部上线）**无 429（闸门/RPM 都没有）、无 error、可用率 100%**，
延迟处于基线水平（P95 1.24s，优于 24h 基线 2.57s）；cooling 波动来自免费引擎的 rate limit / CAPTCHA，属常态。

## 5. 总表需求 4 复核（`docs/reports/m6-project-acceptance-20260930.md`）

* 状态：`⚠️ 有明确限制（2-9 未达 90%）` → **`✅ 达标（按 2026-10-01 登记的采样口径）`**（触发条件：中位 ≥18 且三轮最低 ≥18，实测 19/19/19）；
* 验收证据：替换为**线上 3 轮**数字（19/19/19、中位 19），并挂上 T5/T6/T7 的对拍与召回证据；
* 备注：保留 **Q2 未达标**说明（上游候选漂移 + 主题匹配类）并指向 **「主题相关性闸门」立项**；保留 Q16 修复/部署等历史记录；
* §0 一句话结论：**6 条达标 / 2 条有明确限制 / 0 条未做**（限制 = 中文新闻时效、3-9 人工联调）；
* `checklist.md` 顶部结论同步为 6/2/0，并注明需求 4 恢复达标的依据。

## 6. 回滚方式

```bash
docker tag utf8-search-utf8-search:pre-t8-20261001 utf8-search-utf8-search:latest
docker compose up -d --no-deps utf8-search   # 上次实测 7.5s 恢复
```

## 7. 产物

| 内容 | 路径 |
| --- | --- |
| 线上 2-9 明细与打分 | `docs/reports/m29-t8-20261001-run{1..3}-{brief.md,scores.csv,meta.json}` |
| 1h 长稳证据 | `data/soak-t8-1h.{csv,json,meta.json}` + `docs/reports/soak-t8-1h.{csv,json}`（入库） |
| 总表 / checklist | `docs/reports/m6-project-acceptance-20260930.md` 需求 4 + §0；`checklist.md` 顶部指针 + §8 |
