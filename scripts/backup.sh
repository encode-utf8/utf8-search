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
#   bash scripts/backup.sh [输出目录]        # 默认 /root/deploy-backups-<日期>
#   bash scripts/backup.sh /root/backups 2026-09-30
#
# 说明：
#   * `data/` 里的 cache.db 体积最大（当前 ~12MB），是**可重建**的；为控制体积可改用
#     `BACKUP_SKIP_CACHE=1 bash scripts/backup.sh`（跳过 *.db/*.db-wal/*.db-shm）。
#   * 备份目录权限设为 700（.env 在里面，属机密）；校验和写入 SHA256SUMS。
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATE="${2:-$(date +%Y%m%d-%H%M)}"
OUT_DIR="${1:-/root/deploy-backups-$DATE}"
STAGE="$(mktemp -d)"
ARCHIVE="$OUT_DIR/utf8-search-backup-$DATE.tar.gz"

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

# 4) 打包 + 校验和
mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"
tar -czf "$ARCHIVE" -C "$STAGE" utf8-search
( cd "$OUT_DIR" && sha256sum "$(basename "$ARCHIVE")" > SHA256SUMS )
rm -rf "$STAGE"

echo "== 完成 =="
ls -lh "$ARCHIVE" "$OUT_DIR/SHA256SUMS"
echo "校验和: $(cat "$OUT_DIR/SHA256SUMS")"
echo "提示：.env 属机密，本目录已设为 700；如需异地保存请先加密（如 age/gpg）。"
