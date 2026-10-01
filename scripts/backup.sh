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
#   * 分卷保留：`BACKUP_KEEP_DAYS`（默认 30）——每次运行会**先打印将删除的旧产物清单**，
#     再删除超过保留期的 `utf8-search-backup-*` 与 `SHA256SUMS`（同一目录内按 mtime 判断）。
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

# 5) 分卷保留策略：默认保留 30 天（BACKUP_KEEP_DAYS），**先打印再删除**
#
# 2026-10-01 修正：cron 每天传一个**新目录**（`/root/deploy-backups-<YYYYMMDD>`），
# 而旧实现只扫 `OUT_DIR` 单层 ⇒ **永远清不掉历史目录**（旧备份会无限堆积，磁盘慢慢被吃满）。
# 现在改成：扫 `BACKUP_ROOT`（默认 `/root`）下的 `deploy-backups-*` 目录，按 mtime 清理 ——
#   ① 删掉其中超过保留期的产物（`.tar.gz[.enc]`）与 `SHA256SUMS`；
#   ② 整目录也已超过保留期的，连目录一起删；③ 最后清掉遗留的空目录。
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
BACKUP_ROOT="${BACKUP_ROOT:-/root}"
# 排除名单（2026-10-01 P9）：**人工回滚备份**不能按"超期"删掉。
# 默认排除 `deploy-backups-20260929`（实测该目录装的是 .env 备份 / compose 快照 / 压测证据，属人工资产），
# 可用空格分隔的 glob 追加，例如：BACKUP_EXCLUDE="deploy-backups-20260929 deploy-backups-manual-*"
BACKUP_EXCLUDE="${BACKUP_EXCLUDE:-deploy-backups-20260929}"
if [ "$KEEP_DAYS" -gt 0 ] 2>/dev/null; then
  echo "== 保留策略：BACKUP_KEEP_DAYS=$KEEP_DAYS，扫描 $BACKUP_ROOT/deploy-backups-*（排除：${BACKUP_EXCLUDE:-无}）=="
  # 排除名单 → find 的 -not -path 条件
  EXCLUDE_ARGS=()
  for pattern in $BACKUP_EXCLUDE; do
    EXCLUDE_ARGS+=(-not -path "$BACKUP_ROOT/$pattern" -not -path "$BACKUP_ROOT/$pattern/*")
  done
  # 「永不删光」保险：先算出**最新一份产物**所在目录，它一定不删（连同它的 SHA256SUMS）
  NEWEST_ARTIFACT="$(find "$BACKUP_ROOT" -maxdepth 2 -type f -name 'utf8-search-backup-*' \
        -path "$BACKUP_ROOT/deploy-backups-*/*" -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | awk '{print $2}')"
  NEWEST_DIR="${NEWEST_ARTIFACT%/*}"
  if [ -n "$NEWEST_ARTIFACT" ]; then
    echo "（保险）最新产物不会被删：$NEWEST_ARTIFACT"
  fi
  STALE_FILES="$(find "$BACKUP_ROOT" -maxdepth 2 -type f \
        \( -name 'utf8-search-backup-*' -o -name 'SHA256SUMS' \) \
        -path "$BACKUP_ROOT/deploy-backups-*/*" "${EXCLUDE_ARGS[@]}" -mtime +"$KEEP_DAYS" \
        -printf '%TY-%Tm-%Td %TH:%TM  %p\n' 2>/dev/null | sort)"
  if [ -n "$NEWEST_ARTIFACT" ] && [ -n "$STALE_FILES" ]; then
    STALE_FILES="$(echo "$STALE_FILES" | grep -v -F "$NEWEST_ARTIFACT" | grep -v -F "$NEWEST_DIR/SHA256SUMS" || true)"
  fi
  STALE_DIRS="$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'deploy-backups-*' \
        "${EXCLUDE_ARGS[@]}" -mtime +"$KEEP_DAYS" -printf '%TY-%Tm-%Td %TH:%TM  %p\n' 2>/dev/null | sort)"
  if [ -n "$NEWEST_DIR" ] && [ -n "$STALE_DIRS" ]; then
    STALE_DIRS="$(echo "$STALE_DIRS" | grep -v -F "$NEWEST_DIR" || true)"
  fi
  if [ -n "$STALE_FILES" ] || [ -n "$STALE_DIRS" ]; then
    echo "将删除以下超过 $KEEP_DAYS 天的条目（先打印，后删除）："
    [ -n "$STALE_FILES" ] && echo "$STALE_FILES"
    if [ -n "$STALE_DIRS" ]; then
      echo "（以下为整目录，连同内容一起删除）"
      echo "$STALE_DIRS"
    fi
    if [ -n "$STALE_FILES" ]; then
      echo "$STALE_FILES" | awk '{print $3}' | while IFS= read -r victim; do
        [ -n "$victim" ] && [ -f "$victim" ] && rm -f -- "$victim"
      done
    fi
    if [ -n "$STALE_DIRS" ]; then
      echo "$STALE_DIRS" | awk '{print $3}' | while IFS= read -r victim; do
        [ -n "$victim" ] && [ -d "$victim" ] && rm -rf -- "$victim"
      done
    fi
    # 清掉被删空的 deploy-backups-* 目录（打印后再删）
    EMPTY_DIRS="$(find "$BACKUP_ROOT" -maxdepth 1 -type d -name 'deploy-backups-*' \
          "${EXCLUDE_ARGS[@]}" -empty 2>/dev/null)"
    if [ -n "$EMPTY_DIRS" ]; then
      echo "$EMPTY_DIRS" | sed 's/^/（空目录，一并删除）/'
      echo "$EMPTY_DIRS" | while IFS= read -r victim; do
        [ -n "$victim" ] && rmdir -- "$victim" 2>/dev/null || true
      done
    fi
    echo "（已删除；如需保留更久请提高 BACKUP_KEEP_DAYS）"
  else
    echo "没有超过 $KEEP_DAYS 天的旧条目，无需清理。"
  fi
else
  echo "== 保留策略：BACKUP_KEEP_DAYS=$KEEP_DAYS（<=0，跳过清理）=="
fi
