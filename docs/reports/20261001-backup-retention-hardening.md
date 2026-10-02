# P9 加固：保留策略的排除名单 + 永不删光（2026-10-01）

> 分支 `chore/ops-hardening-20260930`（未合并 main）。只改 `scripts/backup.sh` 保留段 + cron 文本 + docs/05 §14.8。

## 1. 实际目录判定（`ls -d /var/backups/utf8-search/deploy-backups-*`）

| 目录 | 内容 | 判定 |
| --- | --- | --- |
| `/var/backups/utf8-search/deploy-backups-20260929` | `env.bak` / `env.20260930-pre-*.bak` / `compose-config-*.yml` / `app-*-before*.json` / `images-before.txt` / loadtest 与 selfcheck 证据 | **人工回滚备份**（**不是** backup.sh 产物）→ **必须排除** |
| `/var/backups/utf8-search/deploy-backups-20260930` | `utf8-search-backup-2026-09-30.tar.gz.enc` + `SHA256SUMS` | 自动备份（加密，P6 处置后） |
| `/var/backups/utf8-search/deploy-backups-20261001` | 03:30 cron 产物，当时工作区不在本分支 ⇒ **明文** `utf8-search-backup-20261001.tar.gz` | 自动备份；**已重加密并销毁明文**（见 §4） |

## 2. 加固内容

1. **`BACKUP_EXCLUDE`**（默认 `deploy-backups-20260929`）：排除名单里的目录/文件**永不参与清理**（`find -not -path`）。
2. **永不删光保险**：清理前先按 mtime 找出**最新产物**，把「它 + 它的 SHA256SUMS + 它所在目录」从删除列表中剔除；
   日志打印 `（保险）最新产物不会被删：<路径>`。
3. 清理范围仍是 `BACKUP_ROOT/deploy-backups-*`，按 mtime，**先打印再删**。
4. cron 文本同步：`BACKUP_ROOT=/root BACKUP_EXCLUDE='deploy-backups-20260929' BACKUP_PASSPHRASE_FILE=… BACKUP_KEEP_DAYS=30`。

## 3. 验收（/tmp 两场景）

**场景① 人工目录 + 3 个日期目录 + 全部超期**：人工 `deploy-backups-20260929`（40 天前）**保留**；
两个最老的自动目录被整目录删除；最新自动目录保留并写入当天新包。

```
BEFORE: 20260901(45d) 20260915(40d) 20260920(35d) 20260929(40d,人工)
将删除：20260901/* 与 20260915/* 与两目录本身
AFTER : 20260929(人工) 保留；20260920 保留（内有当天新包）；20260901/20260915 消失
```

**场景② 全部超期（新产物写到 BACKUP_ROOT 之外，只考保留逻辑）**：

```
（保险）最新产物不会被删：/tmp/p9b-root-…/deploy-backups-20260915/utf8-search-backup-20260915.tar.gz.enc
将删除：deploy-backups-20260901（含 SHA256SUMS 与 .enc）+ 目录本身
AFTER : 只剩 deploy-backups-20260915（产物 + SHA256SUMS 完整） ⇒ 最后一份不会被删
```

## 4. 附带处置：03:30 的明文自动备份

t 日 cron 产出的 `utf8-search-backup-20261001.tar.gz` 是**明文**（cron 跟随当时签出的分支，不在本分支上）。
处置：用口令文件重新加密为同目录 `.tar.gz.enc`（600）→ 解密 `cmp` **逐字节一致** → 重算 `SHA256SUMS`
→ `shred -u` 销毁明文包。该目录现在只剩加密产物。

## 5. 证据

| 内容 | 路径 |
| --- | --- |
| 场景① / ② 的 before/after | `/tmp/p9-drill-<随机>`（`/tmp/p9-root.txt`）、`/tmp/p9b-root-<随机>` |
| cron 文本 | `crontab -l`（含 `BACKUP_EXCLUDE`） |
| 重加密后的 10-01 备份目录 | `/var/backups/utf8-search/deploy-backups-20261001/`（仅 `.enc` + `SHA256SUMS`） |
| 手册 | `docs/05-服务器部署手册.md` §14.8 |
