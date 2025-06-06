#!/bin/bash

# Pulseway Backend Backup Script

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="pulseway_backup_${TIMESTAMP}.tar.gz"

echo "💾 Creating backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create backup archive
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    --exclude='logs/*' \
    --exclude='backups/*' \
    --exclude='.git/*' \
    --exclude='__pycache__/*' \
    --exclude='*.pyc' \
    data/ .env

echo "✅ Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"

# Keep only last 10 backups
cd "$BACKUP_DIR"
ls -t pulseway_backup_*.tar.gz | tail -n +11 | xargs -r rm

echo "🧹 Old backups cleaned up"
