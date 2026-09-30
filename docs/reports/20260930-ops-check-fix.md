# P6 修复：P2×P3 交叉缺陷（加密备份被巡检误报）+ 分卷保留策略（2026-09-30）

> 分支 `chore/ops-hardening-20260930`（**未合并 main**）。**只做 P6**：未重启容器、未改 `.env`、未动闸门参数、未改 `src/`。

## 1. 缺陷与修复

**缺陷（已实测确认）**：P3 之后备份产物默认是 `utf8-search-backup-*.tar.gz.enc`，
而 `ops_check.py::check_backup` 只 glob `utf8-search-backup-*.tar.gz` ⇒ 加密备份上线后
**每 5 分钟误报「未找到任何备份产物」**（288 次/天），cron 次次非零退出 —— 告警通道会被噪声淹没，
真正的告警（证书 <30 天 / 服务不可达）反而被埋掉。

**修复（`scripts/ops_check.py`）**：

```python
BACKUP_ARTIFACT_GLOBS = ("utf8-search-backup-*.tar.gz", "utf8-search-backup-*.tar.gz.enc")
BACKUP_PAIR_TOLERANCE_SEC = 3600     # SHA256SUMS 与产物必须同目录且同龄（≤1h）
```

判据写清楚为三条：① 产物后缀**两种都认**（明文 `.tar.gz` 与 P3 起的加密 `.tar.gz.enc`）；
② `SHA256SUMS` 必须与产物**同目录**；③ 两者 **mtime 相差 ≤ 1 小时**（避免"刚更新的校验和 + 很旧的包"
被误判成新鲜），新鲜度取 pair 里较新的 mtime。

## 2. 单测（新增 `tests/test_ops_check_backup.py`，5 条）

| 用例 | 断言 |
| --- | --- |
| **`test_encrypted_only_directory_is_not_reported_missing`**（本次回归点） | 目录里**只有 `.tar.gz.enc`** 时 `check_backup` 返回 `[]` |
| `test_plaintext_artifact_still_accepted` | 旧明文 `.tar.gz` 仍被认（兼容性不丢） |
| `test_expired_artifact_alerts` | mtime 72h 前 → 告警（含"小时"字样） |
| `test_missing_artifact_alerts` | 空目录 / 只有 SHA256SUMS → 「未找到」告警 |
| `test_new_sums_with_old_artifact_not_counted_as_fresh` | 只刷新 SHA256SUMS 不算新鲜（必须同龄） |

`pytest -q tests/test_ops_check_backup.py` → **5 passed**。

## 3. 遗留明文包的处置

处置对象：`/root/deploy-backups-20260930/utf8-search-backup-2026-09-30.tar.gz`（P2 时生成，**内含明文 API Key**）。

| 时间（2026-09-30） | 动作 | 结果 |
| --- | --- | --- |
| 18:56 | 用 P3 口令文件（`/root/.utf8-search-backup.pass`）把该明文包**重新加密**为同目录 `….tar.gz.enc`（600） | 产出 1,473,808 B 的 `.enc` |
| 18:56 | `openssl enc -d …` 解密并与原明文包 `cmp` | **逐字节一致** ⇒ 加密包完整覆盖原内容 |
| 18:56 | 重算 `SHA256SUMS`（记密文哈希）并 `touch -r` 对齐 mtime | `e1713e48…83e  utf8-search-backup-2026-09-30.tar.gz.enc` |
| 18:56 | 明文包移出备份目录到 `/tmp/withdrawn-plaintext-20260930/`，随后 **`shred -u` 覆写删除** | 目录已空，备份目录内只剩 `.enc` + SHA256SUMS |

**结论**：该目录现在**只有加密产物**，明文包已销毁；口令文件 `600`，与备份分开保管（见 docs/05 §14.5）。

## 4. 分卷保留策略（`backup.sh`）

新增 `BACKUP_KEEP_DAYS`（默认 **30**）：每次运行**先打印将删除的清单**，再删除 `OUT_DIR` 下超过保留期的
`utf8-search-backup-*` 与 `SHA256SUMS`（同目录、按 mtime）。cron 已带上该参数：

```
30 3 * * * cd /root/utf8-search && BACKUP_PASSPHRASE_FILE=/root/.utf8-search-backup.pass \
            BACKUP_SKIP_CACHE=1 BACKUP_KEEP_DAYS=30 bash scripts/backup.sh \
            /root/deploy-backups-$(date +%Y%m%d) $(date +%Y%m%d) >> data/backup.cron.log 2>&1
```

**实测（/tmp 演练目录，造一个 40 天前的旧包）**：

```
== 保留策略：BACKUP_KEEP_DAYS=30（清理 /tmp/keep-drill-… 下的旧产物）==
将删除以下超过 30 天的文件：
2026-08-21 18:57  /tmp/keep-drill-…/utf8-search-backup-2026-08-01.tar.gz.enc
（已删除；如需保留请提高 BACKUP_KEEP_DAYS）
```

## 5. 验收（两次真实场景 + 真实退出码）

| 场景 | 命令 | 输出 | 退出码 |
| --- | --- | --- | --- |
| **① 目录里只有 `.enc`**（默认 glob 指向真实备份目录，也单独指过一次） | `.venv/bin/python scripts/ops_check.py --no-probe-search` | `[OK] health=200 error=0.0 rejected=0 … 通知=log-only` | **exit=0** ✅ |
| **② 产物过期**（/tmp 造 72h 前的 `.enc` + SHA256SUMS） | `… --backup-glob /tmp/expired-backup-…` | `[ALERT] … ⚠️ 最近一次备份已 72.0 小时（> 48h）：/tmp/expired-backup-…` | **exit=1** ✅ |

（注：第一次量退出码时用了管道 `\| tail`，量到的其实是 `tail` 的退出码；上表是**不经管道**直接量的真实退出码。）

## 6. 证据

| 内容 | 路径 |
| --- | --- |
| 修复后的巡检脚本 | `scripts/ops_check.py`（`BACKUP_ARTIFACT_GLOBS` / `BACKUP_PAIR_TOLERANCE_SEC`） |
| 回归单测 | `tests/test_ops_check_backup.py`（5 passed） |
| 处置后的备份目录 | `/root/deploy-backups-20260930/`（只剩 `.tar.gz.enc` + `SHA256SUMS`） |
| 保留策略实测 | `/tmp/keep-drill-<时间戳>/`（旧包已删，新包保留） |
| cron | `crontab -l`（备份行已带 `BACKUP_KEEP_DAYS=30`） |
| 退出码证据 | `/tmp/p6-a.log`（OK）、`/tmp/p6-b.log`（ALERT） |
