# 运维交付收尾：自愈 + 日志轮转 + 巡检告警 + 备份恢复 + 手册（2026-09-30）

> 分支 `chore/ops-hardening-20260930`（**未合并 main**）。**未改 `src/`、未动闸门参数、未碰人工项 3-9**；
> 涉及**中断现网**的动作（自愈演练 / 让日志轮转生效的 recreate）本轮**未执行**，原因与命令见 §2/§7。

## 0. 摘要

| 项 | 结果 |
| --- | --- |
| A 合并 | `chore/closeout-20260930`（1ea46a4）→ main **3fa89fc** 并推送；复跑 **321 passed / 4 deselected**；`diff --stat` = **2 files, +16/-4** |
| B 自愈与日志轮转 | `restart: unless-stopped` **三个服务本来已有**（复核确认）；**新增** 三个服务的 `logging: json-file + max-size 10m + max-file 3`；`docker compose config` 解析通过。⚠️ **生效需 recreate，本轮暂缓**（24h 稳定期长稳正在跑，见 §7） |
| C 巡检告警 | 新增 `scripts/ops_check.py`（/health + /metrics + 磁盘/data 阈值 → `data/ops-check.log`，异常退出码 1，通知通道留 webhook 接口）；**已装 cron（每 5 分钟）**；正常与故障各留了一次日志样本 |
| D 备份与恢复 | 新增 `scripts/backup.sh`（打包 .env/compose/Caddyfile/searxng 配置/data → tar.gz + SHA256SUMS，目录 700）；**真做了一次恢复演练**（/tmp 临时环境：校验和 OK、关键文件可读、`docker compose config` 解析通过、`.env` 键集合一致） |
| E 手册 | `docs/05` 新增 §14「运维交付」（重建/回滚锚点/env recreate/CAPTCHA 重启/绕缓存/磁盘观察点/**不要多 worker** 警告） |

## 1. A) 合并

```
3fa89fc merge: 结项收尾（总表更新 + 长稳回填 + Q16 修复上线 + 24h 稳定期长稳）
push 2cfa599..3fa89fc main；合并后复跑 321 passed, 4 deselected
diff --stat 2cfa599..main = 2 files changed, 16 insertions(+), 4 deletions(-)
```

## 2. B) 容器自愈与日志轮转

### 2.1 自愈（复核 + 说明）

`restart: unless-stopped` 在 `docker-compose.yml` 的 **searxng / utf8-search / caddy 三个服务上本来就已经存在**
（第 6/32/84 行），本轮只做复核与文档化，**不需要改动**。理由：服务器重启或进程崩溃后容器自动拉起，
不需要人工介入；`unless-stopped` 的语义是"除非你手动 stop，否则总是拉起"。

### 2.2 日志轮转（新增）

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"     # 单容器最多 30MB
```

三个服务统一加上。**当前占用**：容器日志合计仅 ~2.9MB（`docker system df`：Containers 2.15MB），
所以加轮转是**防患**——坏日时 SearXNG 的引擎 WARNING 会快速增长（`unresponsive` 每次请求都可能写）。
校验：`docker compose config` 三段 `logging` 均已生效（见执行输出）。

### 2.3 自愈演练（**待用户确认窗口，本轮未做**）

```bash
# 需你在场同意后执行；预计中断 10-20 秒（healthcheck interval 30s + start_period 20s）
time docker kill utf8-search-app          # 观察 docker ps 是否自动拉起
docker inspect -f '{{.State.Status}} {{.RestartCount}}' utf8-search-app
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health
```

注意两点：① 24h 稳定期长稳正在跑（§7），演练会打断它的 RSS 采样；② 演练窗口建议避开压测/验收。

## 3. C) 巡检与告警

### 3.1 脚本

`scripts/ops_check.py`：

* `/health`（带 Key）→ 服务不可达 / `searxng` 状态 / `engines.cooling` 快照；
* `/metrics`（带 Key）→ `upstream_requests_total{result="error"}` 非 0 报警；`rejected_total` 与**上次快照比增量** > 200 报警；
* 磁盘：根分区 > 85% 或 `data/` > 5GiB 报警；
* 结构化 JSON 日志 → `data/ops-check.log`；**异常退出码 1**（cron 可据此接监控）；
* **通知通道留接口**：`OPS_ALERT_WEBHOOK` + `OPS_ALERT_TOKEN`，未配置时只记日志（当前就是这种状态）。

### 3.2 cron（已安装）

```
*/5 * * * * cd /opt/utf8-search && /opt/utf8-search/.venv/bin/python scripts/ops_check.py \
            >> /opt/utf8-search/data/ops-check.cron.log 2>&1
```

`cron` 服务状态 `active`（PID 706）。每小时 12 次巡检，日志落在 `data/`（已被备份脚本覆盖）。

### 3.3 证据：正常 + 人为触发

```
$ .venv/bin/python scripts/ops_check.py
[OK] health=200 error=0.0 rejected=0 冷却引擎=['brave','privacywall','yep','google','google news'] 通知=log-only
exit=0

$ .venv/bin/python scripts/ops_check.py --base-url http://127.0.0.1:9     # 人为把端口改错
[ALERT] health=None error=None rejected=None 冷却引擎=None 通知=log-only
  ⚠️ /health 不可达：[Errno 111] Connection refused
  ⚠️ /metrics 不可达：[Errno 111] Connection refused
exit=1
```

对应 `data/ops-check.log` 里的两行 JSON（`"level": "OK"` / `"level": "ALERT"`）已留档。

## 4. D) 备份清单与恢复演练

### 4.1 必须备份的项与机密等级

| 项 | 内容 | 机密性 |
| --- | --- | --- |
| `.env` | API Key、Host 白名单、全部运行参数 | **机密**（含明文 Key） |
| `docker-compose.yml` | 编排（env_file 接线、日志轮转、端口矩阵） | 普通 |
| `Caddyfile` | 反代、TLS、日志 | 普通 |
| `searxng/settings.yml` + `settings.local.yml` | 引擎集合与出网策略 | 普通 |
| `data/` | SQLite 缓存（可重建）、测量产物、长稳 CSV/JSON、巡检日志 | 内部（含查询样本） |

备份应落在**仓库外**的受控目录（默认 `/var/backups/utf8-search/deploy-backups-<日期>`，权限 700）；异地保存前先加密（age/gpg）。

### 4.2 `scripts/backup.sh`

```bash
BACKUP_SKIP_CACHE=1 bash scripts/backup.sh /tmp/backup-drill 2026-09-30   # 跳过可重建的 SQLite
```

产物：`utf8-search-backup-2026-09-30.tar.gz`（726KB，跳过缓存）+ `SHA256SUMS`；包内附 `BACKUP-INFO.txt`
（日期/主机/git head/镜像 tag），便于恢复时核对版本。

### 4.3 恢复演练（真做过，**在 /tmp 临时环境**）

| 步骤 | 结果 |
| --- | --- |
| 解包到 `mktemp -d /tmp/restore-drill-XXXX` | ✅ |
| `sha256sum -c SHA256SUMS` | ✅ `OK` |
| 关键文件存在且可读（`.env` / `docker-compose.yml` / `searxng/settings.yml`） | ✅ |
| 在恢复目录跑 `docker compose config` | ✅ **解析通过**（说明 compose 与 .env 自洽） |
| 比对 `.env` 键集合（现网 vs 恢复副本） | ✅ **完全一致** |

## 5. E) 手册（docs/05 §14）

新增一节，覆盖：重建与上线流程（实测 **53.5s**）、**回滚锚点**用法（含现有 5 个 tag 列表 + 当前镜像）、
「改 `.env` 必须 recreate 而不是 restart」、**CAPTCHA 卡住时 `restart searxng`**、
**复测必须绕缓存**（`CACHE_QUERY_TTL=600`，同刻 28% vs 56%）、磁盘与缓存增长观察点、
**⚠️ 不要启用多 worker**（闸门 limit 是进程内的，多 worker 会让全局并发变成 N×limit）。

## 6. 校验记录

| 校验 | 结果 |
| --- | --- |
| `docker compose config`（含新 logging） | ✅ 三个服务都解析出 `json-file/10m/3` |
| `crontab -l` | ✅ 巡检任务每 5 分钟 |
| `cron` 服务 | ✅ `active` |
| 巡检正常/故障样本 | ✅ exit 0 / exit 1 + ALERT 日志 |
| 备份校验和 + 恢复演练 | ✅ 见 §4.3 |

## 7. 待你确认的动作（本轮刻意未做）

1. **让日志轮转生效**：需要 `docker compose up -d --no-deps searxng utf8-search caddy`（三个容器 recreate，
   约 10-20 秒不可用）。**建议等 24h 稳定期长稳跑满（10-01 17:17）之后再执行**，否则长稳会跨镜像、RSS 采样再次失效。
2. **自愈演练**：`docker kill utf8-search-app`（同上，需你在场同意 + 选窗口）。
3. 两者也可合并成一次窗口：先 recreate 三个容器（日志轮转生效），再 kill 一次 app 观察自愈。

## 8. 证据

| 内容 | 路径 |
| --- | --- |
| 巡检脚本 / 备份脚本 | `scripts/ops_check.py`、`scripts/backup.sh` |
| 巡检日志（含 ALERT 样本） | `data/ops-check.log`、`data/ops-check.cron.log` |
| cron 配置 | `crontab -l`（每 5 分钟） |
| 备份产物与校验和 | `/tmp/backup-drill/utf8-search-backup-2026-09-30.tar.gz` + `SHA256SUMS` |
| 恢复演练目录 | `/tmp/restore-drill-<随机>`（`/tmp/restore-path.txt` 记录了路径） |
| 手册 | `docs/05-服务器部署手册.md` §14 |
