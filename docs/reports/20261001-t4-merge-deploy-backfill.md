# T4：合并两条分支 → 开窗口部署 → 回填长稳（2026-10-01）

> 本轮 = ①合并 `chore/ops-hardening-20260930`（64b83eb）+ `chore/p1-ranking-20260930`（2c2294f）进 main；
> ②服务器工作区切到 main（cron 跟随工作区）；③回填两个 6h + 一个 24h 长稳；
> ④开窗口部署 P1/P5/P7（回滚锚点 `fe0252b06803`）；⑤线上复验（selfcheck / 2-9 新口径 / 鉴权 / metrics /
> 巡检 / 自愈演练 / 1h 回看）。**未动 3-9、闸门参数与 `.env`。**

## 1. 合并（两次 `--no-ff`，各复跑离线套件）

| 步骤 | 结果 |
| --- | --- |
| 起点 | main = `3fa89fc`（与 origin/main 同步） |
| merge ① `origin/chore/ops-hardening-20260930`（64b83eb） | 无冲突 → **e687d7e**；离线 **326 passed / 4 deselected** |
| merge ② `origin/chore/p1-ranking-20260930`（2c2294f） | **唯一冲突 = checklist.md §8 工作记录**（两侧各自追加）→ 按**并集**解决（10 条完整保留、按任务号/时间排序，无内容取舍）；其余自动合并 → **84feca5** |
| 合并态复跑 | **330 passed / 4 deselected**（与空跑验证一致） |
| 推送 | `push 3fa89fc..84feca5 main` |

## 2. 服务器工作区切 main + P9 nit

- 工作区已 `checkout main` 并 `pull --ff-only`（随后的回填提交 `9a7c370` 也在 main 上）。
  **cron 跟随工作区**：切换后 `scripts/ops_check.py` / `scripts/backup.sh` 均为 main 版本（P2/P3/P6/P8/P9 生效）。
- **P9 nit（清空目录那段 find 也带 `BACKUP_EXCLUDE`）**：核查后**已由 64b83eb 满足**（`EMPTY_DIRS=find … "${EXCLUDE_ARGS[@]}" -empty`），无需再改；用真脚本在 `/tmp` 复验：
  `deploy-backups-20260929`（排除名单、空、超期）**保留**；`deploy-backups-20260901`（空、超期、未排除）与
  `20260915`（含超期产物）**删除**；新产物 `…/deploy-backups-20261001/utf8-search-backup-20261001.tar.gz.enc` 正常生成。

## 3. 长稳回填（`--summarize`，证据 CSV/JSON 已入库 `docs/reports/`）

| 长稳 | 窗口 | 采样 | 可用率 | 延迟 | 内存 | 429 |
| --- | --- | --- | --- | --- | --- | --- |
| 跨镜像 6h（`soak-6h-envwiring`） | 09-30 11:14:33 → 17:14:34（6.00h） | 71 计入 | **100%** | P50 2362 / P95 2584 / max 2740ms | **不可比**（12:00 rebuild 后 PID 失效、仅 7 个 RSS 采样） | 无 |
| 干净 6h（`soak-6h-freshness`） | 09-30 12:15:14 → 18:05:14（5.83h） | 71 计入 | **100%** | P50 1256 / P95 2550 / max 2586ms | 末次 127.7MB（采样不足、趋势未判定） | 无 |
| 24h 稳定期（`soak-24h-closeout`） | 09-30 17:17:27 → 10-01 17:17:27（24.00h） | **287 计入** | **100%** | P50 1331 / P95 2569 / max 2619 / mean 1612ms | 中位 111.7 → 103.9MB（**-7.0%**），min 99.2 / 峰值 113.6MB | 无 |

「无 429」的两层证据：① 三个窗口的 `--summarize` 均无失败/跳过；② 重建**前**（app 容器自 09-30 17:16 起）
`/metrics` 累计 = `requests_total{result="ok"} 329`、**无 `result="error"`、无 `rejected_total` 序列、
`upstream_acquire_seconds` 计数 0（无排队）** —— 覆盖整个 24h 窗口（闸门与 RPM 都没触发）。
回填落点：checklist §22-7 / §24-2 / §27-6 + 总表 §2.1。

## 4. 部署窗口（约 7.6s 不可用）

| 项 | 值 |
| --- | --- |
| 回滚锚点 | `docker tag utf8-search-utf8-search:latest utf8-search-utf8-search:pre-p1ranking-20261001` = **`fe0252b06803`**（旧镜像） |
| 备份 | `docker-compose.yml`、`.env` → `/var/backups/utf8-search/deploy-backups-20261001/t4-pre-deploy-{compose,env}-20261001-1749.*`（env 600） |
| 构建 | `docker compose build utf8-search` **52.8s** → 新镜像 **`5694bdc297e2`** |
| 上线 | `docker compose up -d --no-deps utf8-search`：recreate 命令 3.3s；**`/health` 200 恢复耗时 7.6s** |
| 未动 | searxng / caddy（未重启）；端口矩阵不变（app 仅 127.0.0.1:8000） |

## 5. 线上复验

### 5.1 协议与鉴权

- `scripts/mcp_selfcheck.py --base-url http://127.0.0.1:8000`：**24 项全通过（24/24，exit 0）**，
  含 stdio / streamable-http / REST / 401 / 421 / 429+Retry-After。
- 鉴权抽查：无 Key → **401**、错 Key → **401**、对 Key → **200**。
- `/metrics`：`requests_total{result="ok"}` 正常推进、**无 `result="error"`、无 `rejected_total` 序列**。
- 巡检：`scripts/ops_check.py` → `[OK] health=200 error=0.0 rejected=0`，**exit=0**
  （同时证明 P6 修复在现网成立：加密备份 `.enc` 不再被误报"未找到产物"）。

### 5.2 2-9（线上路径，按 2026-10-01 登记口径：3 次取中位数）

三次**冷查询**（HTTP `/v1/search`，查询尾加 2/3/4 个空格绕缓存；单并发；每轮之间等 65s 避开 `RPM=60`；
`cached=0/20`、`degraded=0/20`、`ok=20/20`）：

| 轮次 | 采集窗口 | 相关数 ≥4 的查询 | 平均相关 | <4 的查询 |
| --- | --- | --- | --- | --- |
| run1 | 17:53:54 → 17:54:10 | **16/20 = 80%** | 4.30 | Q1(2)、Q2(1)、Q6(3)、Q16(3) |
| run2 | 17:55:15 → 17:55:32 | **16/20 = 80%** | 4.25 | Q1(2)、Q2(0)、Q6(3)、Q16(3) |
| run3 | 17:56:37 → 17:56:52 | **16/20 = 80%** | 4.30 | Q1(2)、Q2(1)、Q6(3)、Q16(3) |

**中位数 = 16/20 = 80%**（门槛 90%，**未达**）；三轮未达标集合一致 —— 与 T2 的稳定缺陷结论吻合：
**Q6**（V2EX 会员页 / brew formula）与 **Q16**（wirefly Pro Max 机型不符 + Pinterest）恒为 3/5，
**Q1**（2/5，本轮 3 轮都在）与 **Q2**（0-1/5，含短剧垃圾站）为上游漂移面。
⚠️ 过程中的一次口径外事件：首轮**未做 RPM 间隔**时，第 61+ 次请求触发**RPM 限流 429**（与闸门无关）——
之后改为每轮间隔 65s，三轮全部正常；该 429 不计入闸门 rejected。

### 5.3 自愈演练（含一处对旧假设的纠正）

| 动作 | 结果 |
| --- | --- |
| `docker kill utf8-search-app`（旧手册假设"自动拉起"） | ❌ **不会自动重启**：手动停止会**抑制** restart 策略；容器停在 `exited`（实测 26s 仍不恢复，`RestartCount` 不变）→ 已 `docker start` 恢复，**4.5s** 回到 healthy |
| 崩溃自愈（宿主侧 `kill -9 $(docker inspect -f '{{.State.Pid}}' …)`） | ✅ **4.3s 自动重启**（`RestartCount` 0→1），health 200 |

⇒ 结论写入 `docs/05` §14.3：**崩溃/重启自愈有效；`docker kill/stop` 属手动停止、不适用**；
容器内 `kill -9 1` 对 PID 1 无效（命名空间 init 收不到同命名空间信号），演练必须从宿主侧杀主进程。

### 5.4 1h 回看（cooling / rejected / 延迟）

部署后启动 1h 观测长稳：`scripts/soak.py --duration-hours 1 --interval 300 --unique --http-url http://127.0.0.1:8000`
（PID **377233**，17:59:41 起，预计 18:59:41 结束；首采样 OK / 1368ms / 5 条 / RSS 108.1MB）。
结果与 `/health` cooling、`/metrics` rejected 终值见 §6（跑满后回填）。

## 6. 1h 回看结果

`--summarize`（17:59:41 → 18:59:41，**11 个计入样本**（13 行含 2 预热）、覆盖 100%）：

| 指标 | 值 |
| --- | --- |
| 可用率 | **100%**（空结果 / 异常 / 跳过 = 0 / 0 / 0） |
| 延迟 | **P50 1369ms / P95 2588ms / max 2588ms / mean 1553ms** |
| 内存（容器 RSS） | 103.4MB（最低）/ 104.8MB（末次 = 峰值）；中位 103.5 → 104.8MB（+1.2%） |
| `/metrics` 终值 | `requests_total{result="ok"} 26`；**无 `result="error"`、无 `rejected_total` 序列** |
| `/health` cooling 终值 | 5 个（`resulthunter` timeout、`google` captcha、`brave` rate_limit、`privacywall` denied、`yep` denied）；窗口内波动 3–5 个，服务不受影响 |

窗口内 12 个 5 分钟快照（requests_ok 单调 4→26，error/rejected 序列始终 0，cooling 3–5）：

```
18:05 samples=2  lat=2559ms requests_ok=4  cooling=5
18:10 samples=3  lat=1316ms requests_ok=6  cooling=4
18:15 samples=4  lat=1135ms requests_ok=8  cooling=5
18:20 samples=5  lat=1196ms requests_ok=10 cooling=5
18:25 samples=6  lat=2588ms requests_ok=12 cooling=5
18:30 samples=7  lat=1550ms requests_ok=14 cooling=5
18:35 samples=8  lat=1390ms requests_ok=16 cooling=5
18:40 samples=9  lat=2588ms requests_ok=18 cooling=5
18:45 samples=10 lat=1369ms requests_ok=20 cooling=3
18:50 samples=11 lat=1136ms requests_ok=22 cooling=5
18:56 samples=12 lat=1303ms requests_ok=24 cooling=5
19:01 samples=13 lat=1513ms requests_ok=26 cooling=5（finished）
```

⇒ 1h 回看结论：新镜像（P1/P5/P7）上线后 **无 429（闸门/RPM 都没有）、无 error、可用率 100%**，
延迟维持基线水平（P95 2.59s，与 24h 的 2.57s 同量级）；cooling 波动来自免费引擎的 rate limit / CAPTCHA，
属常态（`resulthunter`/`brave`/`privacywall`/`yep`/`google`），不影响服务可用性。

## 7. 回滚方式

```bash
docker tag utf8-search-utf8-search:pre-p1ranking-20261001 utf8-search-utf8-search:latest  # 或直接改 compose 用 tag
docker compose up -d --no-deps utf8-search   # 上次实测 7.6s 恢复
```
> `.env` / `docker-compose.yml` 的改动前副本：`/var/backups/utf8-search/deploy-backups-20261001/t4-pre-deploy-{compose,env}-20261001-1749.*`。
