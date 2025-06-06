#!/bin/bash

# Pulseway Backend Restore Script

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file>"
    echo "Available backups:"
    ls -la backups/pulseway_backup_*.tar.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  This will overwrite existing data. Continue? (y/N)"
read -r confirm

if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "❌ Restore cancelled"
    exit 1
fi

echo "🔄 Stopping services..."
docker-compose down

echo "📦 Extracting backup..."
tar -xzf "$BACKUP_FILE"

echo "🚀 Starting services..."
docker-compose up -d

echo "✅ Restore completed!"
