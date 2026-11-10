#!/bin/sh
# ==============================================================================
# PAKAR - Automated Backup Script for PostgreSQL and Upload Storage
# Creates a custom-format pg_dump and a compressed tar of uploaded documents.
# Prunes backups older than RETENTION_DAYS (default 7 days).
# Usage: sudo sh deploy/backup.sh
# Can be run via cron: 0 3 * * * /opt/pakar/deploy/backup.sh >> /var/log/pakar-backup.log 2>&1
# ==============================================================================

set -eu

BACKUP_DIR=${BACKUP_DIR:-/srv/pakar-backups}
RETENTION_DAYS=${RETENTION_DAYS:-7}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

cd "$PROJECT_DIR"

if [ ! -f deploy/.env ]; then
  printf '%s\n' "deploy/.env not found. Please ensure deploy/.env exists before running backup." >&2
  exit 1
fi

printf '[%s] Starting PAKAR backup...\n' "$(date -Iseconds)"

# 1. PostgreSQL custom-format binary backup
DB_DUMP_FILE="${BACKUP_DIR}/pakar-db-${TIMESTAMP}.dump"
printf '[%s] Dumping PostgreSQL database to %s...\n' "$(date -Iseconds)" "$DB_DUMP_FILE"

sh deploy/pakar.sh exec -T database sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl --file=/tmp/pakar-db-backup.dump'

sh deploy/pakar.sh cp database:/tmp/pakar-db-backup.dump "$DB_DUMP_FILE"
sh deploy/pakar.sh exec -T database rm -f /tmp/pakar-db-backup.dump

# 2. Uploads and simulation volume backup
UPLOADS_TAR_FILE="${BACKUP_DIR}/pakar-data-${TIMESTAMP}.tar.gz"
printf '[%s] Archiving backend data volume to %s...\n' "$(date -Iseconds)" "$UPLOADS_TAR_FILE"

VOLUME_PATH=$(docker volume inspect pakar_vps_backend_data --format '{{ .Mountpoint }}' 2>/dev/null || true)
if [ -n "$VOLUME_PATH" ] && [ -d "$VOLUME_PATH" ]; then
  tar -czf "$UPLOADS_TAR_FILE" -C "$VOLUME_PATH" .
else
  # Fallback: copy from container directly if volume mountpoint is not directly accessible
  sh deploy/pakar.sh cp backend:/app/data/uploads "${BACKUP_DIR}/uploads_temp"
  tar -czf "$UPLOADS_TAR_FILE" -C "${BACKUP_DIR}/uploads_temp" .
  rm -rf "${BACKUP_DIR}/uploads_temp"
fi

# 3. Clean up backups older than RETENTION_DAYS
printf '[%s] Pruning backups older than %s days...\n' "$(date -Iseconds)" "$RETENTION_DAYS"
find "$BACKUP_DIR" -type f \( -name "pakar-db-*.dump" -o -name "pakar-data-*.tar.gz" \) -mtime "+$RETENTION_DAYS" -delete

printf '[%s] Backup completed successfully. Current backups in %s:\n' "$(date -Iseconds)" "$BACKUP_DIR"
ls -lh "$BACKUP_DIR"

