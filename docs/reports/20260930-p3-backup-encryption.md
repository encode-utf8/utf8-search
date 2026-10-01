# P3 备份机密治理：对称加密 + 口令保管 + 解密恢复演练（2026-09-30）

> 分支 `chore/ops-hardening-20260930`（**未合并 main**）。**只改 `backup.sh` + docs/05 §14 + cron 口令来源**；
> 未改 `src/`、未重启容器、未改 `.env`、未动闸门参数。

## 1. 问题与做法

旧 `backup.sh` 产出的 tar.gz 内含 **`.env`（明文 API Key）**，目录虽 700，但**包一旦被复制即泄露**。

改造（`scripts/backup.sh`）：

| 项 | 行为 |
| --- | --- |
| **默认加密** | `tar.gz` → AES-256-CBC(+pbkdf2 200k 迭代) → `utf8-search-backup-<日期>.tar.gz.enc`（600 权限）；**明文 tar.gz 不留在备份目录** |
| **口令来源** | `BACKUP_PASSPHRASE` 环境变量，或 `BACKUP_PASSPHRASE_FILE`（600 权限文件，供 cron）；**两者都没有 → 拒绝执行，exit 2** |
| **显式放弃加密** | `--allow-plaintext` 才会产出明文（不推荐），并在输出里明确警告 |
| **校验和** | `SHA256SUMS` 记的是**密文**产物；校验/恢复流程不变 |
| **不留痕** | `BACKUP-INFO.txt` 只记日期/主机/git head/镜像 tag，**不含口令**；`strings` 也读不到 Key（见 §3） |

## 2. 服务器落地

```bash
openssl rand -base64 32 > /root/.utf8-search-backup.pass && chmod 600 /root/.utf8-search-backup.pass
# cron 已更新为使用口令文件：
30 3 * * * cd /root/utf8-search && BACKUP_PASSPHRASE_FILE=/root/.utf8-search-backup.pass \
            BACKUP_SKIP_CACHE=1 bash scripts/backup.sh /root/deploy-backups-$(date +%Y%m%d) $(date +%Y%m%d) \
            >> /root/utf8-search/data/backup.cron.log 2>&1
```

已用 `BACKUP_PASSPHRASE_FILE=… bash scripts/backup.sh /tmp/p3-drill <日期>` 模拟 cron 调用 → 加密成功。
**口令保管**：口令文件 `600`、**不在备份里、不进日志**，必须与备份**分开保存**（异机密钥库 / 密码管理器）；
口令丢失 = 备份不可恢复（无后门）。该要求已写入 `docs/05` §14.5。

## 3. 验收（全部在 /tmp，未触碰现网）

| 步骤 | 命令 | 结果 |
| --- | --- | --- |
| **拒绝无口令** | `bash scripts/backup.sh /tmp/p3-drill 2026-09-30` | `❌ 未提供备份口令（.env 含明文 API Key，默认必须加密）…`，**exit=2** |
| 加密备份 | `BACKUP_PASSPHRASE=… BACKUP_SKIP_CACHE=1 bash scripts/backup.sh /tmp/p3-drill 2026-09-30` | 产出 `utf8-search-backup-2026-09-30.tar.gz.enc`（728K、**600**）+ `SHA256SUMS` |
| **校验和（密文）** | `cd /tmp/p3-drill && sha256sum -c SHA256SUMS` | `…tar.gz.enc: OK` ✅ |
| 解密 | `openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass file:/tmp/p3-pass.txt -in …enc -out restore.tar.gz` | 成功 |
| 完整性 | `gzip -t restore.tar.gz` | OK ✅ |
| 解包 + compose 解析 | `tar -xzf … -C $RESTORE/env` → `docker compose config` | 解析通过 ✅ |
| `.env` 对照 | `diff <(cut -d= -f1 现网 .env) <(… 恢复副本 .env)` / `cmp -s` | **键集合一致 ✅、内容逐字节一致 ✅** |
| **密文不含明文 Key** | `strings …tar.gz.enc \| grep -c utf8_P3SFX…` | **0** ✅ |

脱敏输出样例（恢复副本）：

```
UTF8SEARCH_SEARXNG_URL=http://127.0.0.1:8888
UTF8SEARCH_API_KEYS=***REDACTED***
```

## 4. 回滚

`backup.sh` 是纯脚本：`git checkout <上一个 commit> -- scripts/backup.sh` 即回到明文模式；
已生成的 `.enc` 产物不受影响（仍可用上述解密命令恢复）。cron 若要回退，把
`BACKUP_PASSPHRASE_FILE=…` 前缀去掉并加 `--allow-plaintext` 即可（不推荐）。

## 5. 证据

| 内容 | 路径 |
| --- | --- |
| 脚本 | `scripts/backup.sh` |
| 加密产物 + 校验和 | `/tmp/p3-drill/utf8-search-backup-2026-09-30.tar.gz.enc`、`SHA256SUMS` |
| 解密恢复目录（临时） | `/tmp/p3-restore-<随机>`（路径记在 `/tmp/p3-restore-path.txt`） |
| 口令文件（600，未入备份） | `/root/.utf8-search-backup.pass` |
| 手册 | `docs/05-服务器部署手册.md` §14.5（口令保管 + 解密恢复步骤） |
