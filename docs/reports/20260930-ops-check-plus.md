# P2 巡检增强 + 坏日样本积累（2026-09-30）

> 分支 `chore/ops-hardening-20260930`（**未合并 main**）。**只做 P2**：未重启任何容器、未改 `.env`、
> 未动闸门参数、未改 `src/`。新增能力全在 `scripts/ops_check.py`（+ 一条 backup.sh 的 cron）。

## 1. 三个新巡检项

| 巡检项 | 判据 | 告警样例 |
| --- | --- | --- |
| **① 证书剩余天数**（遗留 #5 的"无法提前发现"面） | 连 `--cert-host:--cert-port`（默认 `203.0.113.10.sslip.io:443`）读回证书，`notAfter - now < --cert-min-days`（默认 **30 天**）即告警 | `证书剩余 1.0 天（< 30 天，到期 2026-10-01T09:40:16+00:00）：127.0.0.1:8443` |
| **② 最近备份新鲜度** | 在 `--backup-glob`（默认 `/var/backups/utf8-search/deploy-backups-*`）里找**最新的 tar.gz + SHA256SUMS**，年龄 > `--backup-max-hours`（默认 **48h**）或找不到即告警 | `未找到任何备份产物（/tmp/empty-backups：需要 tar.gz + SHA256SUMS）` |
| **③ 坏日样本快照** | 每轮把 `/metrics` 的 `result="error"`、`rejected_total{queue_full}`、`rejected_total{timeout}`、`requests_ok` 与**探针搜索结果条数**追加一行到 `data/ops-metrics-snapshot.csv` | 见 §3 的 CSV 尾部样例 |

实现要点：证书检查用 `ssl` + `cryptography`（本地已有依赖）解析 `notAfter`，**不做链校验**（内网自签也能读）；
探针搜索默认开启（每轮一条唯一查询，用于"结果条数"这一列），`--no-probe-search` 可关；
新增 `--cert-skip` 便于离线环境跳过。所有项都写进 `data/ops-check.log` 的结构化 JSON。

## 2. 验收：正常 exit=0 + 三种人为异常各 exit=1

| 场景 | 命令 | 结果 |
| --- | --- | --- |
| **正常** | `.venv/bin/python scripts/ops_check.py` | `[OK] health=200 error=0.0 rejected=0 …`，**exit=0** |
| **① 服务不可达（改错端口）** | `--base-url http://127.0.0.1:9 --no-probe-search` | `[ALERT] /health 不可达：Connection refused`，**exit=1** |
| **② 备份缺失（指向空目录）** | `--backup-glob /tmp/empty-backups` | `[ALERT] 未找到任何备份产物（…需要 tar.gz + SHA256SUMS）`，**exit=1** |
| **③ 过期证书探针** | 用 `openssl req -days 1` 生成自签证书 + `openssl s_server -accept 8443`，再跑 `--cert-host 127.0.0.1 --cert-port 8443` | `[ALERT] 证书剩余 1.0 天（< 30 天，到期 2026-10-01…）`，**exit=1** |

三次 ALERT 的 JSON 行都在 `data/ops-check.log`（`"level": "ALERT"`）；过期证书探针用的是**1 天有效期的自签证书**，
跑在 8443 上、用完即停（`pkill -f "s_server -accept 8443"`），**没有触碰现网证书**。

## 3. 坏日样本 CSV

`data/ops-metrics-snapshot.csv`（表头 `ts,health_status,upstream_error,rejected_queue_full,rejected_timeout,requests_ok,probe_results`）：

```
2026-09-30T09:40:05+00:00  200  0.0  0.0  0.0  14.0  5
2026-09-30T09:40:09+00:00  200  0.0  0.0  0.0  15.0  5
2026-09-30T09:40:18+00:00  200  0.0  0.0  0.0  17.0  5
2026-09-30T09:40:21+00:00  200  0.0  0.0  0.0  18.0  5
```

（`rejected_*` 全 0、`probe_results` 全 5 —— 当前是"好日"样本。**坏日样本**会在上游限流/过载时自然出现，
这批数据就是"闸门上限自适应"立项的输入；本轮**只采集、不调参**。）

## 4. backup.sh 每日 cron（已装）

```
30 3 * * * cd /opt/utf8-search && BACKUP_SKIP_CACHE=1 bash scripts/backup.sh \
            /var/backups/utf8-search/deploy-backups-$(date +\%Y\%m\%d) $(date +\%Y\%m\%d) >> /opt/utf8-search/data/backup.cron.log 2>&1
```

`crontab -l` 已确认两条任务都在（巡检每 5 分钟 + 备份每天 03:30）；`cron` 服务 `active`。
今天已按同路径生成一份产物：`/var/backups/utf8-search/deploy-backups-20260930/utf8-search-backup-20260930.tar.gz`（1.5MB）+ `SHA256SUMS`，
这就是新巡检项②的"新鲜备份"来源（同时验证了 `backup.sh` 可被 cron 直接调用）。

## 5. 与遗留清单的对应

* 总表遗留 #5「证书 2026-12-24 续期依赖 80/443 长期放行」→ 现在**每天 12×N 次巡检都能提前发现**（<30 天即告警）。
* 总表遗留 #2「闸门上限自适应（坏日样本不足）」→ 本轮起**每 5 分钟落一行指标快照**，为立项积累数据。
* 备份新鲜度巡检 → 配合新增的每日备份 cron，把「备份存在但过期」也纳入告警。

## 6. 证据

| 内容 | 路径 |
| --- | --- |
| 巡检脚本（含三个新项） | `scripts/ops_check.py` |
| 巡检日志（含 3 类 ALERT 样本） | `data/ops-check.log` |
| 坏日样本快照 | `data/ops-metrics-snapshot.csv` |
| cron 配置 | `crontab -l`（巡检 `*/5`，备份 `30 3 * * *`） |
| 备份产物 | `/var/backups/utf8-search/deploy-backups-20260930/{utf8-search-backup-20260930.tar.gz,SHA256SUMS}` |
| 过期证书探针（用完即停） | `/tmp/short.crt`、`/tmp/short.key`、`openssl s_server -accept 8443`（已停） |
