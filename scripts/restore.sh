#!/bin/bash

# Pulseway Backend Restore Script

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file_path>"
    echo "Available backups:"
    ls -1 backups/pulseway_backup_*.tar.gz 2>/dev/null || echo "No backups found in ./backups/"
    exit 1
fi

BACKUP_FILE="$1"
PROJECT_NAME=$(basename "$(pwd)") # Infer project name
DOCKER_VOLUME_NAME="${PROJECT_NAME}_pulseway_data" # Default Docker Compose volume naming

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  This will overwrite existing application data and .env file (if present in backup). Continue? (y/N)"
read -r confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "❌ Restore cancelled by user."
    exit 1
fi

echo "🔄 Stopping services..."
# We don't use -v here because we want to restore into the existing volume (or a new one if it doesn't exist)
docker-compose down

# Create a temporary directory for extracting backup contents
TEMP_RESTORE_DIR=$(mktemp -d)
if [ ! -d "$TEMP_RESTORE_DIR" ]; then
    echo "❌ Failed to create temporary restore directory."
    exit 1
fi

# Ensure cleanup of temp directory on script exit
trap 'rm -rf "$TEMP_RESTORE_DIR"' EXIT

echo "📦 Extracting backup file '$BACKUP_FILE' to temporary location..."
tar -xzf "$BACKUP_FILE" -C "$TEMP_RESTORE_DIR"

if [ -f "${TEMP_RESTORE_DIR}/.env" ]; then
    echo "    Restoring .env file..."
    cp "${TEMP_RESTORE_DIR}/.env" ".env"
else
    echo "    No .env file found in backup. Skipping .env restore."
fi

if [ -d "${TEMP_RESTORE_DIR}/data" ]; then
    echo "    Restoring database volume '${DOCKER_VOLUME_NAME}'..."

    # Verify the Docker volume exists, or try generic name.
    # docker run -v volume_name:/path will create the volume if it doesn't exist.
    if ! docker volume inspect "${DOCKER_VOLUME_NAME}" > /dev/null 2>&1; then
        echo "    Volume '${DOCKER_VOLUME_NAME}' not found by that name. Will attempt to restore to 'pulseway_data'."
        DOCKER_VOLUME_NAME="pulseway_data"
    fi

    echo "    Using volume name '${DOCKER_VOLUME_NAME}' for restore."
    # Clear existing volume data and copy new data from backup.
    # Ensure the source directory /source_data ends with '/.' to copy contents correctly.
    # Ensure the target directory /volume_data exists (it should as it's a mount point).
    docker run --rm \
        -v "${DOCKER_VOLUME_NAME}:/volume_data" \
        -v "${TEMP_RESTORE_DIR}/data:/source_data:ro" \
        alpine \
        sh -c "rm -rf /volume_data/* /volume_data/..?* /volume_data/.[!.]* ; \
               if [ -d /source_data ] && [ \"\$(ls -A /source_data)\" ]; then \
                   cp -a /source_data/. /volume_data/ ; \
                   echo '    Database volume content restored.' ; \
               else \
                   echo '    No data found in backup/data to restore, volume might be empty.' ; \
               fi"
else
    echo "    No 'data' directory found in backup. Skipping database volume restore."
fi

# Cleanup of temp directory is handled by trap

echo "🚀 Starting services..."
docker-compose up -d

echo "✅ Restore completed!"
