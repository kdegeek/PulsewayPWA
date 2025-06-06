# setup.py
#!/usr/bin/env python3
"""
Pulseway Backend Setup Script
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Check if required tools are installed"""
    requirements = ['docker', 'docker-compose', 'python3']
    missing = []
    
    for req in requirements:
        if not shutil.which(req):
            missing.append(req)
    
    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        print("Please install these tools before continuing.")
        return False
    
    print("✅ All required tools are available")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs', 'backups']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def setup_environment():
    """Setup environment configuration"""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env file with your Pulseway credentials")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file already exists")
    
    return True

def build_docker_image():
    """Build the Docker image"""
    print("🔨 Building Docker image...")
    
    try:
        subprocess.run(['docker-compose', 'build'], check=True)
        print("✅ Docker image built successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to build Docker image")
        return False

def setup_database():
    """Initialize the database"""
    print("🗄️  Setting up database...")
    
    try:
        # Create database tables by importing the models
        sys.path.insert(0, 'app')
        from app.database import engine
        from app.models.database import Base
        
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
        return True
    except Exception as e:
        print(f"❌ Failed to setup database: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Pulseway Backend Setup")
    print("=" * 40)
    
    if not check_requirements():
        sys.exit(1)
    
    create_directories()
    
    if not setup_environment():
        sys.exit(1)
    
    if not setup_database():
        print("⚠️  Database setup failed, but continuing...")
    
    if not build_docker_image():
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your Pulseway API credentials")
    print("2. Run: docker-compose up -d")
    print("3. Check status: docker-compose logs -f")
    print("4. Access API docs: http://localhost:8000/docs")

if __name__ == '__main__':
    main()

# scripts/start.sh
#!/bin/bash

# Pulseway Backend Startup Script

set -e

echo "🚀 Starting Pulseway Backend..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Create directories if they don't exist
mkdir -p data logs backups

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Start the services
echo "🐳 Starting Docker containers..."
docker-compose up -d

# Wait for the service to be healthy
echo "⏳ Waiting for service to be ready..."
sleep 10

# Check if service is running
if docker-compose ps | grep -q "Up"; then
    echo "✅ Pulseway Backend is running!"
    echo "📊 API Documentation: http://localhost:8000/docs"
    echo "🏥 Health Check: http://localhost:8000/api/health"
    echo ""
    echo "📋 Useful commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop service: docker-compose down"
    echo "  Restart: docker-compose restart"
    echo "  CLI access: docker-compose exec pulseway-backend python cli.py --help"
else
    echo "❌ Failed to start Pulseway Backend"
    echo "📋 Check logs: docker-compose logs"
    exit 1
fi

# scripts/backup.sh
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

# scripts/restore.sh
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

# app/config.py
"""
Configuration settings for Pulseway Backend
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Pulseway API Configuration
    pulseway_token_id: str
    pulseway_token_secret: str
    pulseway_base_url: str = "https://api.pulseway.com/v3/"
    
    # Database Configuration
    database_url: str = "sqlite:///./data/pulseway.db"
    
    # Application Configuration
    log_level: str = "INFO"
    debug: bool = False
    
    # Sync Configuration
    sync_interval_minutes: int = 10
    min_request_interval: float = 0.1
    
    # API Configuration
    api_title: str = "Pulseway Backend API"
    api_description: str = "Robust backend for interfacing with Pulseway instances"
    api_version: str = "1.0.0"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# app/logging_config.py
"""
Logging configuration for Pulseway Backend
"""

import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging(log_level: str = "INFO"):
    """Setup application logging"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "pulseway_backend.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "pulseway_errors.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    logger.addHandler(error_handler)
    
    return logger