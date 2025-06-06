# Pulseway Backend API

A robust Python backend for interfacing with Pulseway instances, featuring device management, script execution, monitoring, and automated data synchronization.

## 🌟 Features

- **Device Management**: Comprehensive device monitoring and management
- **Script Execution**: Execute scripts on devices with variable support
- **Real-time Monitoring**: Dark-mode friendly monitoring dashboard
- **Automated Sync**: Background data synchronization every 10 minutes
- **Multi-location Support**: Organization, site, and group categorization
- **RESTful API**: FastAPI-based API with automatic documentation
- **CLI Tool**: Rich command-line interface for operations
- **Docker Ready**: Full containerization support
- **SQLite Caching**: Local data caching for improved performance

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PWA Frontend  │───▶│  FastAPI Backend │───▶│  Pulseway API   │
│   (Future)      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  SQLite Cache   │
                       │                 │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Pulseway API credentials

### 1. Clone and Setup

```bash
git clone <repository-url>
cd pulseway-backend
chmod +x scripts/*.sh
python setup.py
```

### 2. Configure Environment

Copy the example environment file and configure your Pulseway credentials:

```bash
cp .env.example .env
```

Edit `.env` with your Pulseway API credentials:

```env
PULSEWAY_TOKEN_ID=your_token_id_here
PULSEWAY_TOKEN_SECRET=your_token_secret_here
PULSEWAY_BASE_URL=https://api.pulseway.com/v3/
```

### 3. Start the Service

```bash
# Using the startup script
./scripts/start.sh

# Or manually with Docker Compose
docker-compose up -d
```

### 4. Verify Installation

```bash
# Check service health
curl http://localhost:8000/api/health

# View API documentation
open http://localhost:8000/docs
```

## 📱 CLI Usage

The CLI tool provides a rich command-line interface for managing your Pulseway infrastructure:

### Device Management

```bash
# List all devices
docker-compose exec pulseway-backend python cli.py devices list

# Filter devices by organization
docker-compose exec pulseway-backend python cli.py devices list --organization "Acme Corp"

# Show only offline devices
docker-compose exec pulseway-backend python cli.py devices list --offline-only

# Get detailed device information
docker-compose exec pulseway-backend python cli.py devices info <device-id>

# Show device statistics
docker-compose exec pulseway-backend python cli.py devices stats
```

### Script Management

```bash
# List available scripts
docker-compose exec pulseway-backend python cli.py scripts list

# Filter scripts by platform
docker-compose exec pulseway-backend python cli.py scripts list --platform Windows

# Execute a script on a device
docker-compose exec pulseway-backend python cli.py scripts execute <script-id> <device-id>

# Execute with variables
docker-compose exec pulseway-backend python cli.py scripts execute <script-id> <device-id> \
  --variables '{"variable1": "value1", "variable2": "value2"}'
```

### Monitoring

```bash
# Show monitoring dashboard
docker-compose exec pulseway-backend python cli.py monitoring dashboard

# View recent alerts
docker-compose exec pulseway-backend python cli.py monitoring alerts

# Filter critical alerts only
docker-compose exec pulseway-backend python cli.py monitoring alerts --priority critical
```

### Data Synchronization

```bash
# Trigger immediate sync
docker-compose exec pulseway-backend python cli.py sync now

# Check sync status
docker-compose exec pulseway-backend python cli.py sync status
```

## 🔌 API Endpoints

### Device Endpoints

- `GET /api/devices/` - List devices with filtering
- `GET /api/devices/stats` - Device statistics
- `GET /api/devices/{device_id}` - Device details
- `GET /api/devices/{device_id}/notifications` - Device notifications
- `GET /api/devices/{device_id}/assets` - Device assets
- `POST /api/devices/{device_id}/refresh` - Refresh device data
- `GET /api/devices/search/{term}` - Search devices

### Script Endpoints

- `GET /api/scripts/` - List scripts
- `GET /api/scripts/{script_id}` - Script details
- `POST /api/scripts/{script_id}/execute` - Execute script
- `GET /api/scripts/{script_id}/executions/{device_id}` - Execution history
- `POST /api/scripts/bulk-execute` - Execute on multiple devices

### Monitoring Endpoints

- `GET /api/monitoring/dashboard` - Dashboard summary
- `GET /api/monitoring/alerts` - Alert summary
- `GET /api/monitoring/health` - System health
- `GET /api/monitoring/activity/recent` - Recent activity
- `GET /api/monitoring/locations/organizations` - Organization stats
- `GET /api/monitoring/performance` - Performance metrics

## 🎨 PWA Frontend Preparation

The API is designed with a future PWA frontend in mind:

- **Dark Mode Ready**: All monitoring endpoints return data optimized for dark themes
- **Real-time Updates**: WebSocket support ready for implementation
- **Mobile Friendly**: Compact data structures for mobile devices
- **Colorful Visualizations**: Rich data for charts and dashboards
- **Responsive Design**: API supports various screen sizes and orientations

### Recommended Frontend Stack

```typescript
// Suggested PWA tech stack
- Framework: React/Vue.js with TypeScript
- State Management: Zustand/Pinia
- UI Components: Tailwind CSS + Headless UI
- Charts: Chart.js or D3.js
- PWA: Workbox for service workers
- Real-time: Socket.io client
```

## 🔧 Development Setup

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd pulseway-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup development environment
cp .env.example .env.dev
# Edit .env.dev with your credentials

# Run development server
uvicorn app.main:app --reload --env-file .env.dev
```

### Docker Development

```bash
# Use development compose file
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Access container for debugging
docker-compose exec pulseway-backend bash
```

### Testing

```bash
# Run tests (when implemented)
pytest

# Code formatting
black app/
flake8 app/

# Type checking
mypy app/
```

## 📊 Monitoring and Maintenance

### Health Monitoring

```bash
# Check application health
curl http://localhost:8000/api/health

# View logs
docker-compose logs -f

# Monitor resource usage
docker stats pulseway-backend
```

### Backup and Restore

```bash
# Create backup
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh backups/pulseway_backup_20240101_120000.tar.gz
```

### Performance Tuning

- **Database**: SQLite is optimized for read-heavy workloads
- **Sync Interval**: Adjust `SYNC_INTERVAL_MINUTES` based on your needs
- **Rate Limiting**: Configure `MIN_REQUEST_INTERVAL` for API rate limits
- **Memory**: Monitor memory usage for large device counts

## 🔐 Security Considerations

- **API Keys**: Store Pulseway credentials securely
- **Network**: Use HTTPS in production
- **Access Control**: Implement authentication for production use
- **Backup Encryption**: Encrypt backups containing sensitive data
- **Container Security**: Regular security updates for base images

## 🐛 Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check environment variables
docker-compose config

# Verify credentials
docker-compose exec pulseway-backend python cli.py sync status
```

**Sync failures:**
```bash
# Check logs for API errors
docker-compose logs pulseway-backend | grep ERROR

# Test API connectivity
docker-compose exec pulseway-backend python -c "
from app.pulseway.client import PulsewayClient
from app.config import settings
client = PulsewayClient(settings.pulseway_base_url, settings.pulseway_token_id, settings.pulseway_token_secret)
print('Health check:', client.health_check())
"
```

**Database issues:**
```bash
# Reset database
docker-compose down
docker volume rm pulseway-backend_pulseway_data
docker-compose up -d
```

### Log Locations

- **Application Logs**: `logs/pulseway_backend.log`
- **Error Logs**: `logs/pulseway_errors.log`
- **Docker Logs**: `docker-compose logs`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Create an issue with detailed information
4. Include relevant log snippets and configuration

## 🗺️ Roadmap

### Phase 1: Core Backend ✅
- [x] FastAPI application structure
- [x] Pulseway API client
- [x] SQLite database with models
- [x] Automated data synchronization
- [x] Device management endpoints
- [x] Script execution endpoints
- [x] Monitoring endpoints
- [x] CLI tool
- [x] Docker containerization

### Phase 2: PWA Frontend (Next)
- [ ] React-based PWA
- [ ] Dark mode dashboard
- [ ] Real-time updates via WebSocket
- [ ] Mobile-responsive design
- [ ] Offline functionality
- [ ] Push notifications

### Phase 3: Advanced Features
- [ ] User authentication and authorization
- [ ] Custom alerting rules
- [ ] Report generation
- [ ] Integration with external systems
- [ ] Advanced analytics and trends
- [ ] Multi-tenant support

---

**Built with ❤️ for the Pulseway community**