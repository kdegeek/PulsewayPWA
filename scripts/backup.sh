#!/bin/bash

# Pulseway Backend Backup Script

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="pulseway_backup_${TIMESTAMP}.tar.gz"
PROJECT_NAME=$(basename "$(pwd)") # Infer project name from current directory
DOCKER_VOLUME_NAME="${PROJECT_NAME}_pulseway_data" # Default Docker Compose volume naming

echo "💾 Creating backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create a temporary staging directory for backup contents
TEMP_BACKUP_STAGING_DIR=$(mktemp -d)
if [ ! -d "$TEMP_BACKUP_STAGING_DIR" ]; then
    echo "❌ Failed to create temporary staging directory."
    exit 1
fi

# Ensure cleanup of temp directory on script exit
trap 'rm -rf "$TEMP_BACKUP_STAGING_DIR"' EXIT

echo "    Staging .env file..."
if [ -f ".env" ]; then
    cp .env "${TEMP_BACKUP_STAGING_DIR}/.env"
else
    echo "⚠️  .env file not found. It will not be included in the backup."
fi

echo "    Staging database volume '${DOCKER_VOLUME_NAME}'..."
# Create a 'data' subdirectory in staging for DB content
mkdir -p "${TEMP_BACKUP_STAGING_DIR}/data"

# Verify the Docker volume exists
if ! docker volume inspect "${DOCKER_VOLUME_NAME}" > /dev/null 2>&1; then
    echo "❌ Docker volume '${DOCKER_VOLUME_NAME}' not found. Attempting with generic 'pulseway_data'."
    DOCKER_VOLUME_NAME="pulseway_data" # Fallback for non-project-scoped or manually named volume
    if ! docker volume inspect "${DOCKER_VOLUME_NAME}" > /dev/null 2>&1; then
        echo "❌ Docker volume '${DOCKER_VOLUME_NAME}' also not found. Database backup will be empty."
        # Proceed to create an archive without DB data if user wants partial backup
    fi
fi

if docker volume inspect "${DOCKER_VOLUME_NAME}" > /dev/null 2>&1; then
    # Backup Docker volume content into the staging/data directory using a tar pipe
    # This preserves permissions and handles various file types better than cp.
    # The target directory inside the container for tar extraction must exist.
    docker run --rm \
        -v "${DOCKER_VOLUME_NAME}:/volume_data:ro" \
        -v "${TEMP_BACKUP_STAGING_DIR}/data:/target_in_container" \
        alpine \
        sh -c "cd /volume_data && tar -cf - . | (cd /target_in_container && tar -xf -)"
    echo "    Database volume staged."
else
    echo "⚠️  Skipping database volume backup as volume was not found."
fi

# Create final backup archive from the staging directory
echo "    Creating final backup archive: ${BACKUP_DIR}/${BACKUP_FILE}"
tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" -C "${TEMP_BACKUP_STAGING_DIR}" . # Backup .env and data/

# Cleanup of temp directory is handled by trap

echo "✅ Backup created: ${BACKUP_DIR}/${BACKUP_FILE}"

# Keep only last 10 backups
echo "🧹 Cleaning up old backups..."
cd "$BACKUP_DIR"
ls -t pulseway_backup_*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm
cd - > /dev/null # Go back to previous directory silently

echo "✅ Backup process completed."
