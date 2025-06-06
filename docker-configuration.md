# Docker Configuration Files

## Dockerfile
```dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 pulseway && \
    chown -R pulseway:pulseway /app && \
    mkdir -p /app/data && \
    chown -R pulseway:pulseway /app/data

# Switch to non-root user
USER pulseway

# Create data directory for SQLite database
VOLUME ["/app/data"]

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

## docker-compose.yml
```yaml
version: '3.8'

services:
  pulseway-dashboard:
    build: .
    container_name: pulseway-dashboard
    restart: unless-stopped
    ports:
      - "${PORT:-8000}:8000"
    environment:
      - PULSEWAY_TOKEN_ID=${PULSEWAY_TOKEN_ID}
      - PULSEWAY_TOKEN_SECRET=${PULSEWAY_TOKEN_SECRET}
      - PULSEWAY_BASE_URL=${PULSEWAY_BASE_URL:-https://api.pulseway.com/v3/}
      - DATABASE_URL=sqlite:///./data/pulseway.db
      - SYNC_INTERVAL_SECONDS=${SYNC_INTERVAL_SECONDS:-300}
      - UPDATE_INTERVAL_SECONDS=${UPDATE_INTERVAL_SECONDS:-30}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - pulseway_data:/app/data
      - pulseway_logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    labels:
      # Traefik labels for reverse proxy (optional)
      - "traefik.enable=true"
      - "traefik.http.routers.pulseway.rule=Host(`${DOMAIN:-pulseway.localhost}`)"
      - "traefik.http.routers.pulseway.tls=true"
      - "traefik.http.routers.pulseway.tls.certresolver=letsencrypt"
      - "traefik.http.services.pulseway.loadbalancer.server.port=8000"
      # Docker metadata
      - "org.label-schema.name=Pulseway Dashboard"
      - "org.label-schema.description=Self-hosted Pulseway monitoring dashboard"
      - "org.label-schema.version=1.0.0"
      - "org.label-schema.schema-version=1.0"

volumes:
  pulseway_data:
    driver: local
  pulseway_logs:
    driver: local

networks:
  default:
    name: pulseway-network
```

## docker-compose.dev.yml (Development Override)
```yaml
version: '3.8'

services:
  pulseway-dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/app
      - pulseway_data:/app/data
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
      - RELOAD=true
    ports:
      - "8000:8000"
      - "8001:8001"  # Debug port
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

## Dockerfile.dev (Development Version)
```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies including development tools
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-dev.txt

# Create user
RUN useradd -m -u 1000 pulseway
USER pulseway

EXPOSE 8000 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

## .dockerignore
```
# Git
.git
.gitignore

# Documentation
README.md
docs/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local
.env.*.local
.venv
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite
*.sqlite3

# Node modules (if any)
node_modules/

# Temporary files
tmp/
temp/
.tmp/

# Test coverage
htmlcov/
.coverage
.pytest_cache/

# Deployment
docker-compose.override.yml
```

## scripts/docker-build.sh
```bash
#!/bin/bash

# Docker build script for Pulseway Dashboard

set -e

# Configuration
IMAGE_NAME="pulseway-dashboard"
VERSION=${1:-"latest"}
PLATFORM=${2:-"linux/amd64,linux/arm64"}

echo "🐳 Building Pulseway Dashboard Docker image..."
echo "Image: ${IMAGE_NAME}:${VERSION}"
echo "Platform: ${PLATFORM}"

# Build multi-platform image
docker buildx build \
    --platform "${PLATFORM}" \
    --tag "${IMAGE_NAME}:${VERSION}" \
    --tag "${IMAGE_NAME}:latest" \
    --push \
    .

echo "✅ Docker image built successfully!"
echo "📦 Image: ${IMAGE_NAME}:${VERSION}"

# Show image info
docker images "${IMAGE_NAME}" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
```

## scripts/docker-run.sh
```bash
#!/bin/bash

# Docker run script for Pulseway Dashboard

set -e

# Load environment variables
if [ -f .env ]; then
    source .env
fi

# Configuration
CONTAINER_NAME="pulseway-dashboard"
IMAGE_NAME="pulseway-dashboard:latest"
PORT=${PORT:-8000}

echo "🚀 Starting Pulseway Dashboard container..."

# Stop existing container if running
if [ "$(docker ps -q -f name=${CONTAINER_NAME})" ]; then
    echo "⏹️  Stopping existing container..."
    docker stop ${CONTAINER_NAME}
fi

# Remove existing container if exists
if [ "$(docker ps -aq -f name=${CONTAINER_NAME})" ]; then
    echo "🗑️  Removing existing container..."
    docker rm ${CONTAINER_NAME}
fi

# Run new container
docker run -d \
    --name ${CONTAINER_NAME} \
    --restart unless-stopped \
    -p ${PORT}:8000 \
    -e PULSEWAY_TOKEN_ID="${PULSEWAY_TOKEN_ID}" \
    -e PULSEWAY_TOKEN_SECRET="${PULSEWAY_TOKEN_SECRET}" \
    -e PULSEWAY_BASE_URL="${PULSEWAY_BASE_URL:-https://api.pulseway.com/v3/}" \
    -e SYNC_INTERVAL_SECONDS="${SYNC_INTERVAL_SECONDS:-300}" \
    -e UPDATE_INTERVAL_SECONDS="${UPDATE_INTERVAL_SECONDS:-30}" \
    -v pulseway_data:/app/data \
    -v pulseway_logs:/app/logs \
    ${IMAGE_NAME}

echo "✅ Container started successfully!"
echo "🌐 Dashboard: http://localhost:${PORT}"
echo "📊 API Docs: http://localhost:${PORT}/docs"

# Show container status
docker ps --filter name=${CONTAINER_NAME} --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Show logs
echo ""
echo "📋 Container logs (last 20 lines):"
docker logs --tail 20 ${CONTAINER_NAME}
```

## scripts/backup.sh
```bash
#!/bin/bash

# Backup script for Pulseway Dashboard data

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CONTAINER_NAME="pulseway-dashboard"

echo "💾 Creating backup of Pulseway Dashboard data..."

# Create backup directory
mkdir -p ${BACKUP_DIR}

# Backup database
echo "📦 Backing up database..."
docker exec ${CONTAINER_NAME} cp /app/data/pulseway.db /tmp/pulseway_backup.db
docker cp ${CONTAINER_NAME}:/tmp/pulseway_backup.db ${BACKUP_DIR}/pulseway_${TIMESTAMP}.db

# Backup configuration (if exists)
if [ -f .env ]; then
    echo "⚙️  Backing up configuration..."
    cp .env ${BACKUP_DIR}/env_${TIMESTAMP}.backup
fi

# Create compressed archive
echo "🗜️  Creating compressed archive..."
tar -czf ${BACKUP_DIR}/pulseway_full_backup_${TIMESTAMP}.tar.gz \
    ${BACKUP_DIR}/pulseway_${TIMESTAMP}.db \
    ${BACKUP_DIR}/env_${TIMESTAMP}.backup 2>/dev/null || \
tar -czf ${BACKUP_DIR}/pulseway_full_backup_${TIMESTAMP}.tar.gz \
    ${BACKUP_DIR}/pulseway_${TIMESTAMP}.db

# Cleanup individual files
rm -f ${BACKUP_DIR}/pulseway_${TIMESTAMP}.db
rm -f ${BACKUP_DIR}/env_${TIMESTAMP}.backup 2>/dev/null || true

echo "✅ Backup completed!"
echo "📁 Backup file: ${BACKUP_DIR}/pulseway_full_backup_${TIMESTAMP}.tar.gz"

# List recent backups
echo ""
echo "📋 Recent backups:"
ls -lah ${BACKUP_DIR}/ | grep pulseway_full_backup | tail -5
```

## scripts/restore.sh
```bash
#!/bin/bash

# Restore script for Pulseway Dashboard data

set -e

BACKUP_FILE=$1
CONTAINER_NAME="pulseway-dashboard"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -la ./backups/ | grep pulseway_full_backup || echo "No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "🔄 Restoring Pulseway Dashboard from backup..."
echo "📁 Backup file: $BACKUP_FILE"

# Stop container
echo "⏹️  Stopping container..."
docker stop ${CONTAINER_NAME} 2>/dev/null || true

# Extract backup
echo "📦 Extracting backup..."
TEMP_DIR=$(mktemp -d)
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Find database file
DB_FILE=$(find "$TEMP_DIR" -name "pulseway_*.db" | head -1)
if [ -z "$DB_FILE" ]; then
    echo "❌ Database file not found in backup"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Restore database
echo "💾 Restoring database..."
docker volume create pulseway_data 2>/dev/null || true
docker run --rm -v pulseway_data:/data -v "$(dirname "$DB_FILE"):/backup" alpine cp /backup/$(basename "$DB_FILE") /data/pulseway.db

# Cleanup
rm -rf "$TEMP_DIR"

# Start container
echo "🚀 Starting container..."
docker start ${CONTAINER_NAME}

echo "✅ Restore completed successfully!"
echo "🌐 Dashboard: http://localhost:8000"
```

## Makefile
```makefile
.PHONY: help build run stop logs clean backup restore dev test lint

# Default target
help:
	@echo "Pulseway Dashboard - Available Commands:"
	@echo ""
	@echo "  build     - Build Docker image"
	@echo "  run       - Run container"
	@echo "  dev       - Run in development mode"
	@echo "  stop      - Stop container"
	@echo "  restart   - Restart container"
	@echo "  logs      - Show container logs"
	@echo "  shell     - Open shell in container"
	@echo "  backup    - Create data backup"
	@echo "  restore   - Restore from backup"
	@echo "  clean     - Clean up containers and images"
	@echo "  test      - Run tests"
	@echo "  lint      - Run code linting"
	@echo ""

# Build Docker image
build:
	@echo "🐳 Building Docker image..."
	docker-compose build

# Run container
run:
	@echo "🚀 Starting Pulseway Dashboard..."
	docker-compose up -d
	@echo "✅ Dashboard available at http://localhost:8000"

# Development mode
dev:
	@echo "🔧 Starting in development mode..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Stop container
stop:
	@echo "⏹️  Stopping containers..."
	docker-compose down

# Restart container
restart: stop run

# Show logs
logs:
	docker-compose logs -f --tail=100

# Open shell in container
shell:
	docker-compose exec pulseway-dashboard /bin/bash

# Create backup
backup:
	@./scripts/backup.sh

# Restore from backup
restore:
	@echo "Available backups:"
	@ls -la ./backups/ | grep pulseway_full_backup || echo "No backups found"
	@echo ""
	@echo "Usage: make restore BACKUP=<backup_file>"
	@if [ -n "$(BACKUP)" ]; then ./scripts/restore.sh $(BACKUP); fi

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleanup completed"

# Run tests
test:
	@echo "🧪 Running tests..."
	docker-compose exec pulseway-dashboard python -m pytest tests/ -v

# Run linting
lint:
	@echo "🔍 Running code linting..."
	docker-compose exec pulseway-dashboard python -m flake8 app/
	docker-compose exec pulseway-dashboard python -m black --check app/
	docker-compose exec pulseway-dashboard python -m isort --check-only app/

# Install development dependencies
install-dev:
	pip install -r requirements-dev.txt

# Format code
format:
	@echo "✨ Formatting code..."
	black app/
	isort app/

# Security scan
security:
	@echo "🔒 Running security scan..."
	docker-compose exec pulseway-dashboard python -m bandit -r app/

# Update dependencies
update-deps:
	@echo "📦 Updating dependencies..."
	pip-compile requirements.in
	pip-compile requirements-dev.in
```
