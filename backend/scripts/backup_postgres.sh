#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL 未配置，无法备份 PostgreSQL" >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

STAMP="$(date '+%Y%m%d_%H%M%S')"
TARGET="${BACKUP_DIR%/}/betweenus_${STAMP}.sql.gz"

pg_dump "$DATABASE_URL" | gzip > "$TARGET"

echo "PostgreSQL 备份完成: $TARGET"
