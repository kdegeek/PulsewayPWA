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
    echo "  CLI access: docker-compose exec pulseway-backend python app/cli_tool.py --help"
else
    echo "❌ Failed to start Pulseway Backend"
    echo "📋 Check logs: docker-compose logs"
    exit 1
fi
