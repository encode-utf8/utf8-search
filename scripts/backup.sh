#!/usr/bin/env bash
# utf8-search 备份脚本（2026-09-30）
#
# 打包「必须备份」的项到一个带日期与校验和的 tar.gz：
#   .env                     —— 机密（含 API Key / 站点白名单），备份必须落到受控目录
#   docker-compose.yml       —— 部署编排（含 env_file 接线与日志轮转）
#   searxng/settings.yml(+local) —— 引擎集合与出网策略
#   searxng/ settings 快照    —— 历史配置便于回滚对比（若存在 .bak-*）
#   data/                    —— 运行时数据：SQLite 缓存 + 测量产物 + 长稳 CSV/JSON + ops 巡检日志
#   Caddyfile                —— 反代与 TLS 配置
#
# 用法：
#   BACKUP_PASSPHRASE='<口令>' bash scripts/backup.sh [输出目录] [日期]     # 加密（默认，推荐）
#   BACKUP_PASSPHRASE_FILE=/root/.backup.pass bash scripts/backup.sh        # 从 600 权限文件读口令（cron 用）
#   bash scripts/backup.sh --allow-plaintext [输出目录] [日期]              # 显式放弃加密（不推荐）
#
# 说明：
#   * **默认加密**：tar.gz 用 AES-256-CBC(+pbkdf2) 加密成 `*.tar.gz.enc`，SHA256SUMS 记的是**密文**的校验和；
#     口令只从环境变量 `BACKUP_PASSPHRASE`（或 `BACKUP_PASSPHRASE_FILE`）读，**缺口令时直接拒绝执行**
#     （除非显式 `--allow-plaintext`）。BACKUP-INFO.txt 里**不会**出现口令。
#   * `data/` 里的 cache.db 体积最大（当前 ~12MB），是**可重建**的；为控制体积可改用
#     `BACKUP_SKIP_CACHE=1 bash scripts/backup.sh`（跳过 *.db/*.db-wal/*.db-shm）。
#   * 备份目录权限设为 700（.env 在里面，属机密）；校验和写入 SHA256SUMS。
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOW_PLAINTEXT=0
if [ "${1:-}" = "--allow-plaintext" ]; then
  ALLOW_PLAINTEXT=1
  shift
fi
DATE="${2:-$(date +%Y%m%d-%H%M)}"
OUT_DIR="${1:-/root/deploy-backups-$DATE}"
STAGE="$(mktemp -d)"
ARCHIVE="$OUT_DIR/utf8-search-backup-$DATE.tar.gz"
ENCRYPTED_ARCHIVE="$ARCHIVE.enc"

# 口令来源：环境变量优先，其次 600 权限的口令文件；两者都没有 → 拒绝执行（除非显式放开）
PASSPHRASE="${BACKUP_PASSPHRASE:-}"
if [ -z "$PASSPHRASE" ] && [ -n "${BACKUP_PASSPHRASE_FILE:-}" ] && [ -r "${BACKUP_PASSPHRASE_FILE}" ]; then
  PASSPHRASE="$(tr -d '\r\n' < "${BACKUP_PASSPHRASE_FILE}")"
fi
if [ -z "$PASSPHRASE" ] && [ "$ALLOW_PLAINTEXT" != "1" ]; then
  echo "❌ 未提供备份口令（.env 含明文 API Key，默认必须加密）。" >&2
  echo "   请用 BACKUP_PASSPHRASE='<口令>' 或 BACKUP_PASSPHRASE_FILE=<600 权限文件> 重跑；" >&2
  echo "   确实要明文备份请显式加 --allow-plaintext（不推荐）。" >&2
  rm -rf "$STAGE"
  exit 2
fi

echo "== utf8-search 备份 =="
echo "仓库: $REPO"
echo "输出: $ARCHIVE"

mkdir -p "$STAGE/utf8-search"
cd "$REPO"

# 1) 配置类
for item in .env docker-compose.yml Caddyfile searxng/settings.yml searxng/settings.local.yml; do
  if [ -e "$item" ]; then
    mkdir -p "$STAGE/utf8-search/$(dirname "$item")"
    cp -a "$item" "$STAGE/utf8-search/$item"
    echo "  + $item"
  fi
done

# 2) data/（可选跳过 SQLite 缓存）
mkdir -p "$STAGE/utf8-search/data"
if [ "${BACKUP_SKIP_CACHE:-0}" = "1" ]; then
  rsync -a --exclude '*.db' --exclude '*.db-wal' --exclude '*.db-shm' data/ "$STAGE/utf8-search/data/"
  echo "  + data/（已跳过 SQLite 缓存）"
else
  rsync -a data/ "$STAGE/utf8-search/data/"
  echo "  + data/（含 SQLite 缓存）"
fi

# 3) 记录来源信息，便于恢复时核对
cat > "$STAGE/utf8-search/BACKUP-INFO.txt" <<INFO
date: $(date -Is)
host: $(hostname)
repo: $REPO
git_head: $(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)
git_branch: $(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)
images:
$(docker images --format '  {{.Repository}}:{{.Tag}} {{.ID}}' | grep -E 'utf8-search|searxng|caddy' || true)
INFO

# 4) 打包（+ 默认加密）与校验和
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"
tar -czf "$ARCHIVE" -C "$STAGE" utf8-search
if [ "$ALLOW_PLAINTEXT" = "1" ]; then
  FINAL_ARTIFACT="$ARCHIVE"
  echo "⚠️ 已按 --allow-plaintext 生成**明文**备份（内含 .env 的明文 Key，务必只留受控目录）"
else
  # 对称加密：AES-256-CBC + pbkdf2（200k 迭代）；口令只经 env 传递，不落盘、不进日志
  if ! printf '%s' "$PASSPHRASE" | openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
        -pass stdin -in "$ARCHIVE" -out "$ENCRYPTED_ARCHIVE"; then
    echo "❌ 加密失败（openssl）。" >&2
    rm -rf "$STAGE" "$ARCHIVE"
    exit 3
  fi
  rm -f "$ARCHIVE"                     # 明文 tar.gz 不留在备份目录
  FINAL_ARTIFACT="$ENCRYPTED_ARCHIVE"
  chmod 600 "$FINAL_ARTIFACT"
fi
( cd "$OUT_DIR" && sha256sum "$(basename "$FINAL_ARTIFACT")" > SHA256SUMS )
rm -rf "$STAGE"

echo "== 完成 =="
ls -lh "$FINAL_ARTIFACT" "$OUT_DIR/SHA256SUMS"
echo "校验和: $(cat "$OUT_DIR/SHA256SUMS")"
if [ "$ALLOW_PLAINTEXT" = "1" ]; then
  echo "提示：.env 属机密，本目录已设为 700；建议改用默认的加密模式。"
else
  echo "提示：解密 = openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_PASSPHRASE \\"
  echo "                           -in <*.tar.gz.enc> -out <restore.tar.gz> && sha256sum -c SHA256SUMS"
  echo "      口令务必与备份分开保管（口令文件不进备份、不写日志）。"
fi
