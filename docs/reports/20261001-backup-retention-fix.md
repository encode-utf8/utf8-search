# P8 修复：backup.sh 保留策略只扫单层目录（旧备份永远清不掉）（2026-10-01）

> 分支 `chore/ops-hardening-20260930`（**未合并 main**）。**只改 `scripts/backup.sh` 的保留段 + cron 文本**；
> 未改 `src/`、未重启容器、未改 `.env`、未动闸门参数。

## 1. 缺陷

cron 每天传一个**新目录**（`/root/deploy-backups-<YYYYMMDD>`），而旧实现只扫 `OUT_DIR` **单层**
（当天的目录）⇒ **历史目录永远不会被清理**，备份会无限堆积直到吃满磁盘 —— 而"保留 30 天"的语义形同虚设。

## 2. 修复（`scripts/backup.sh`）

保留段改为扫 `BACKUP_ROOT`（默认 `/root`）下的 `deploy-backups-*`：

```bash
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"; BACKUP_ROOT="${BACKUP_ROOT:-/root}"
# ① 删掉这些目录里超过保留期的产物（utf8-search-backup-*）与 SHA256SUMS
# ② 整目录 mtime 也超期的：连目录一起删（rm -rf）
# ③ 最后清掉遗留的空目录（rmdir）
# 全部先打印清单，再执行删除
```

cron 文本同步更新（显式带上 `BACKUP_ROOT=/root`）：

```
30 3 * * * cd /root/utf8-search && BACKUP_ROOT=/root BACKUP_PASSPHRASE_FILE=/root/.utf8-search-backup.pass \
            BACKUP_SKIP_CACHE=1 BACKUP_KEEP_DAYS=30 bash scripts/backup.sh \
            /root/deploy-backups-$(date +%Y%m%d) $(date +%Y%m%d) >> data/backup.cron.log 2>&1
```

**与巡检的衔接**：`ops_check.py` 的 `--backup-glob` 默认仍是 `/root/deploy-backups-*`（本次未改），
所以清理逻辑与巡检口径一致；实测清理后巡检 **`[OK]` exit=0**（仍能命中当天目录里的 `.enc` + 同龄 `SHA256SUMS`）。

## 3. 验证（/tmp 造 3 个日期目录 + 1 个 40 天旧产物）

演练根目录 `/tmp/p8-drill-<随机>`（路径记在 `/tmp/p8-root.txt`）：

| 目录 | mtime | 内容 |
| --- | --- | --- |
| `deploy-backups-20260929` | **40 天前** | `.tar.gz.enc` + `SHA256SUMS`（**旧产物**） |
| `deploy-backups-20260930` | 2 天前 | `.tar.gz.enc` + `SHA256SUMS`（应保留） |
| `deploy-backups-20261001` | 1 小时前 | 当天目录（跑备份写入新包，应保留） |

**BEFORE**（`find -maxdepth 2`，节选）：
```
2026-08-22 17:05  …/deploy-backups-20260929/SHA256SUMS
2026-08-22 17:05  …/deploy-backups-20260929/utf8-search-backup-2026-09-30.tar.gz.enc
2026-09-29 17:05  …/deploy-backups-20260930/…（保留）
2026-10-01 16:05  …/deploy-backups-20261001/…（保留）
```

**执行**（`BACKUP_ROOT=/tmp/p8-drill-… BACKUP_KEEP_DAYS=30 … bash scripts/backup.sh <当天目录> 2026-10-01`）输出：
```
== 保留策略：BACKUP_KEEP_DAYS=30，扫描 /tmp/p8-drill-…/deploy-backups-* ==
将删除以下超过 30 天的条目（先打印，后删除）：
2026-08-22 17:05  …/deploy-backups-20260929/SHA256SUMS
2026-08-22 17:05  …/deploy-backups-20260929/utf8-search-backup-2026-09-30.tar.gz.enc
（以下为整目录，连同内容一起删除）
2026-08-22 17:05  …/deploy-backups-20260929
（已删除；如需保留更久请提高 BACKUP_KEEP_DAYS）
```

**AFTER**：`deploy-backups-20260929`（含内容）**整个消失**；`deploy-backups-20260930` 与
`deploy-backups-20261001` 完整保留，且当天目录里新增了 `utf8-search-backup-2026-10-01.tar.gz.enc`（加密包）。

## 4. 证据

| 内容 | 路径 |
| --- | --- |
| 修复后的保留段 | `scripts/backup.sh`（第 5 节） |
| cron 文本（含 `BACKUP_ROOT`） | `crontab -l` |
| 演练根目录 / before-after | `/tmp/p8-drill-<随机>`（路径：`/tmp/p8-root.txt`） |
| 巡检仍命中 | `/tmp/p8-ops.log`（`[OK] … exit=0`） |
