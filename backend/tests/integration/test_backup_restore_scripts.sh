#!/bin/bash

# Integration test for backup.sh and restore.sh scripts

# Exit on error, print commands
set -e
# set -x # Uncomment for verbose debugging

echo "🚀 Starting backup/restore script tests..."

# --- 1. Setup Phase ---
echo "🔧 Setting up test environment..."

# Define unique names using RANDOM for some level of isolation
# However, Docker volume names might not accept all characters from RANDOM if it's too large.
# Let's use a timestamp and a short random suffix for better compatibility.
RAND_SUFFIX=$(head /dev/urandom | tr -dc a-z0-9 | head -c 5)
TS=$(date +%s)

TEST_DOCKER_VOLUME_NAME="test_pulseway_vol_${TS}_${RAND_SUFFIX}"
TEST_BACKUP_DIR="./test_backups_dir_${TS}_${RAND_SUFFIX}"
TEMP_SCRIPT_DIR=$(mktemp -d) # Temporary directory for modified scripts

# Create dummy .env file
DUMMY_ENV_FILE=".env"
ORIGINAL_ENV_CONTENT="TEST_VAR_BACKUP=\"original_value\""
echo "$ORIGINAL_ENV_CONTENT" > "$DUMMY_ENV_FILE"
echo "    Created dummy .env file."

# Create the test Docker volume
echo "    Creating Docker volume: $TEST_DOCKER_VOLUME_NAME"
docker volume create "$TEST_DOCKER_VOLUME_NAME"

# Populate the test Docker volume with dummy data
DUMMY_VOLUME_DATA_CONTENT="Initial data in volume"
DUMMY_VOLUME_FILE_NAME="dummy_data.txt"
echo "    Populating Docker volume '$TEST_DOCKER_VOLUME_NAME' with '$DUMMY_VOLUME_FILE_NAME'..."
docker run --rm \
    -v "${TEST_DOCKER_VOLUME_NAME}:/data_to_populate" \
    alpine sh -c "echo \"$DUMMY_VOLUME_DATA_CONTENT\" > /data_to_populate/$DUMMY_VOLUME_FILE_NAME"

# Create a minimal docker-compose.yml
DUMMY_COMPOSE_FILE="docker-compose.yml"
cat <<EOL > "$DUMMY_COMPOSE_FILE"
version: '3.8'
services:
  dummy_service_for_test:
    image: alpine
    command: sleep infinity
    volumes:
      - "${TEST_DOCKER_VOLUME_NAME}:/data" # Ensure volume is listed so 'docker-compose down' might interact if needed by scripts
EOL
echo "    Created dummy docker-compose.yml."

# Ensure main scripts are executable (though they should be in git)
chmod +x ../../scripts/backup.sh
chmod +x ../../scripts/restore.sh

# Copy scripts to temp location and modify them
cp ../../scripts/backup.sh "${TEMP_SCRIPT_DIR}/backup.sh"
cp ../../scripts/restore.sh "${TEMP_SCRIPT_DIR}/restore.sh"

# Modify DOCKER_VOLUME_NAME lines in the *copied* scripts
# For backup.sh:
# Replace DOCKER_VOLUME_NAME="${PROJECT_NAME}_pulseway_data" and its fallback logic
# We'll replace the line after PROJECT_NAME is defined, and the fallback assignment.
# This is a bit brittle if the script changes significantly. A more robust way is for scripts to accept env vars.
sed -i.bak -e "/PROJECT_NAME=\$(basename \"\$(pwd)\")/a DOCKER_VOLUME_NAME=\"${TEST_DOCKER_VOLUME_NAME}\" # Overridden by test" \
            -e "/DOCKER_VOLUME_NAME=\"\${PROJECT_NAME}_pulseway_data\"/d" \
            -e "/echo \"❌ Docker volume.*not found. Attempting with generic 'pulseway_data'.\"/ { N; d; }" \
            -e "/DOCKER_VOLUME_NAME=\"pulseway_data\" # Fallback/d" \
            "${TEMP_SCRIPT_DIR}/backup.sh"

# For restore.sh:
sed -i.bak -e "/PROJECT_NAME=\$(basename \"\$(pwd)\")/a DOCKER_VOLUME_NAME=\"${TEST_DOCKER_VOLUME_NAME}\" # Overridden by test" \
            -e "/DOCKER_VOLUME_NAME=\"\${PROJECT_NAME}_pulseway_data\"/d" \
            -e "/echo \"    Volume.*not found by that name. Will attempt to restore to 'pulseway_data'.\"/ { N; d; }" \
            -e "/DOCKER_VOLUME_NAME=\"pulseway_data\"/d" \
            "${TEMP_SCRIPT_DIR}/restore.sh"

echo "    Copied and modified scripts to use test volume name."
echo "🔧 Setup complete."
echo ""

# --- 2. Backup Test Phase ---
echo "🧪 Testing backup.sh..."
mkdir -p "$TEST_BACKUP_DIR" # Ensure backup dir exists for the script

# Temporarily modify BACKUP_DIR in the copied backup.sh
sed -i.bak2 -e "s|BACKUP_DIR=\"./backups\"|BACKUP_DIR=\"${TEST_BACKUP_DIR}\"|g" "${TEMP_SCRIPT_DIR}/backup.sh"

# Run the modified backup script
"${TEMP_SCRIPT_DIR}/backup.sh"

# Check if a backup .tar.gz file was created
BACKUP_FILE_PATH=$(ls -1 "${TEST_BACKUP_DIR}"/pulseway_backup_*.tar.gz | head -n 1)
if [ -z "$BACKUP_FILE_PATH" ]; then
    echo "❌ Backup file not found in $TEST_BACKUP_DIR!"
    exit 1
fi
echo "    ✅ Backup file created: $BACKUP_FILE_PATH"

# Extract and verify backup content
TEMP_EXTRACTED_BACKUP_DIR=$(mktemp -d)
echo "    Extracting backup to $TEMP_EXTRACTED_BACKUP_DIR for verification..."
tar -xzf "$BACKUP_FILE_PATH" -C "$TEMP_EXTRACTED_BACKUP_DIR"

# Verify .env file
if [ ! -f "${TEMP_EXTRACTED_BACKUP_DIR}/.env" ]; then
    echo "❌ .env file not found in backup!"
    exit 1
fi
EXTRACTED_ENV_CONTENT=$(cat "${TEMP_EXTRACTED_BACKUP_DIR}/.env")
if [ "$EXTRACTED_ENV_CONTENT" != "$ORIGINAL_ENV_CONTENT" ]; then
    echo "❌ .env content mismatch in backup!"
    echo "Expected: $ORIGINAL_ENV_CONTENT"
    echo "Got: $EXTRACTED_ENV_CONTENT"
    exit 1
fi
echo "    ✅ .env file content verified."

# Verify dummy_data.txt in volume backup
VOLUME_BACKUP_FILE_PATH="${TEMP_EXTRACTED_BACKUP_DIR}/data/${DUMMY_VOLUME_FILE_NAME}"
if [ ! -f "$VOLUME_BACKUP_FILE_PATH" ]; then
    echo "❌ $DUMMY_VOLUME_FILE_NAME not found in backup's data directory!"
    exit 1
fi
EXTRACTED_VOLUME_DATA_CONTENT=$(cat "$VOLUME_BACKUP_FILE_PATH")
if [ "$EXTRACTED_VOLUME_DATA_CONTENT" != "$DUMMY_VOLUME_DATA_CONTENT" ]; then
    echo "❌ $DUMMY_VOLUME_FILE_NAME content mismatch in backup!"
    echo "Expected: $DUMMY_VOLUME_DATA_CONTENT"
    echo "Got: $EXTRACTED_VOLUME_DATA_CONTENT"
    exit 1
fi
echo "    ✅ Docker volume data content verified."

rm -rf "$TEMP_EXTRACTED_BACKUP_DIR"
echo "🧪 Backup test complete."
echo ""

# --- 3. Pre-Restore Modification Phase ---
echo "✏️ Modifying data before restore..."
MODIFIED_ENV_CONTENT="TEST_VAR_BACKUP=\"changed_value_for_restore_test\""
echo "$MODIFIED_ENV_CONTENT" > "$DUMMY_ENV_FILE"
echo "    Modified live .env file."

MODIFIED_VOLUME_DATA_CONTENT="Modified data in volume for restore test"
echo "    Modifying data in Docker volume '$TEST_DOCKER_VOLUME_NAME'..."
docker run --rm \
    -v "${TEST_DOCKER_VOLUME_NAME}:/data_to_modify" \
    alpine sh -c "echo \"$MODIFIED_VOLUME_DATA_CONTENT\" > /data_to_modify/$DUMMY_VOLUME_FILE_NAME"
echo "✏️ Data modification complete."
echo ""

# --- 4. Restore Test Phase ---
echo "🔄 Testing restore.sh..."

# Run the modified restore script, piping 'y' for confirmation
echo 'y' | "${TEMP_SCRIPT_DIR}/restore.sh" "$BACKUP_FILE_PATH"

# Verify .env file restoration
RESTORED_ENV_CONTENT=$(cat "$DUMMY_ENV_FILE")
if [ "$RESTORED_ENV_CONTENT" != "$ORIGINAL_ENV_CONTENT" ]; then
    echo "❌ .env file not restored correctly!"
    echo "Expected: $ORIGINAL_ENV_CONTENT"
    echo "Got: $RESTORED_ENV_CONTENT"
    exit 1
fi
echo "    ✅ .env file restored correctly."

# Verify Docker volume data restoration
RESTORED_VOLUME_DATA_CONTENT=$(docker run --rm -v "${TEST_DOCKER_VOLUME_NAME}:/data_to_check" alpine cat "/data_to_check/${DUMMY_VOLUME_FILE_NAME}")
if [ "$RESTORED_VOLUME_DATA_CONTENT" != "$DUMMY_VOLUME_DATA_CONTENT" ]; then
    echo "❌ Docker volume data not restored correctly!"
    echo "Expected: $DUMMY_VOLUME_DATA_CONTENT"
    echo "Got: $RESTORED_VOLUME_DATA_CONTENT"
    exit 1
fi
echo "    ✅ Docker volume data restored correctly."
echo "🔄 Restore test complete."
echo ""

# --- 5. Cleanup Phase ---
echo "🧹 Cleaning up test environment..."

rm -rf "$TEST_BACKUP_DIR"
echo "    Removed test backup directory: $TEST_BACKUP_DIR"

echo "    Removing Docker volume: $TEST_DOCKER_VOLUME_NAME"
docker volume rm "$TEST_DOCKER_VOLUME_NAME" || echo "    Warning: Failed to remove volume $TEST_DOCKER_VOLUME_NAME. It might have already been removed or is in use."

rm -f "$DUMMY_ENV_FILE"
echo "    Removed dummy .env file."

rm -f "$DUMMY_COMPOSE_FILE"
echo "    Removed dummy docker-compose.yml."

rm -rf "$TEMP_SCRIPT_DIR"
echo "    Removed temporary script directory."

echo "🧹 Cleanup complete."
echo ""

echo "✅ Backup/restore script tests completed successfully!"

# set +x
set +e
