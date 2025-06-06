# Pulseway PWA Dashboard - Complete Project Structure

A self-hosted Progressive Web App (PWA) dashboard for Pulseway monitoring with real-time updates, dark glassmorphism UI, and comprehensive device management.

## 🏗️ Project Structure

```
pulseway-dashboard/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app with PWA integration
│   ├── database.py                # SQLAlchemy database configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py            # SQLAlchemy models
│   ├── pulseway/
│   │   ├── __init__.py
│   │   └── client.py              # Pulseway API client
│   ├── services/
│   │   ├── __init__.py
│   │   └── data_sync.py           # Data synchronization service
│   ├── api/
│   │   ├── __init__.py
│   │   ├── devices.py             # Device management endpoints
│   │   ├── scripts.py             # Script execution endpoints
│   │   ├── notifications.py       # Notification management
│   │   └── organizations.py       # Organization/Site/Group endpoints
│   └── static/                    # PWA frontend files
│       ├── index.html             # Main dashboard (glassmorphism UI)
│       ├── devices.html           # Device management page
│       ├── scripts.html           # Script execution page
│       ├── notifications.html     # Notifications page
│       ├── settings.html          # Settings page
│       ├── manifest.json          # PWA manifest
│       ├── sw.js                  # Service worker
│       └── icons/                 # PWA icons
│           ├── icon-72.png
│           ├── icon-96.png
│           ├── icon-128.png
│           ├── icon-144.png
│           ├── icon-152.png
│           ├── icon-192.png
│           ├── icon-384.png
│           └── icon-512.png
├── cli.py                         # Command-line interface
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Docker container configuration
├── docker-compose.yml            # Docker Compose setup
├── .env.example                   # Environment variables template
└── README.md                      # Setup and usage instructions
```

## 🚀 Quick Start

### Method 1: Docker Compose (Recommended)

1. **Clone and Configure**
   ```bash
   git clone https://github.com/yourusername/pulseway-dashboard.git
   cd pulseway-dashboard
   cp .env.example .env
   ```

2. **Edit Environment Variables**
   ```bash
   # .env
   PULSEWAY_TOKEN_ID=your_token_id_here
   PULSEWAY_TOKEN_SECRET=your_token_secret_here
   PULSEWAY_BASE_URL=https://api.pulseway.com/v3/
   DATABASE_URL=sqlite:///./pulseway.db
   SYNC_INTERVAL_SECONDS=300
   UPDATE_INTERVAL_SECONDS=30
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access Dashboard**
   - Web Interface: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Method 2: Manual Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   export PULSEWAY_TOKEN_ID="your_token_id"
   export PULSEWAY_TOKEN_SECRET="your_token_secret"
   ```

3. **Initialize Database**
   ```bash
   python -c "from app.database import engine, Base; from app.models.database import *; Base.metadata.create_all(bind=engine)"
   ```

4. **Sync Initial Data**
   ```bash
   python cli.py sync now
   ```

5. **Start Application**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🐳 Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 pulseway && chown -R pulseway:pulseway /app
USER pulseway

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  pulseway-dashboard:
    build: .
    container_name: pulseway-dashboard
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - PULSEWAY_TOKEN_ID=${PULSEWAY_TOKEN_ID}
      - PULSEWAY_TOKEN_SECRET=${PULSEWAY_TOKEN_SECRET}
      - PULSEWAY_BASE_URL=${PULSEWAY_BASE_URL:-https://api.pulseway.com/v3/}
      - DATABASE_URL=sqlite:///./data/pulseway.db
      - SYNC_INTERVAL_SECONDS=${SYNC_INTERVAL_SECONDS:-300}
      - UPDATE_INTERVAL_SECONDS=${UPDATE_INTERVAL_SECONDS:-30}
    volumes:
      - pulseway_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.pulseway.rule=Host(`pulseway.yourdomain.com`)"
      - "traefik.http.routers.pulseway.tls=true"
      - "traefik.http.routers.pulseway.tls.certresolver=letsencrypt"

volumes:
  pulseway_data:
    driver: local
```

## 📱 PWA Features

### Core Features
- **Offline Support**: Cached data and offline functionality via service worker
- **Push Notifications**: Real-time critical alerts and system notifications
- **App-like Experience**: Install as native app on desktop and mobile
- **Dark Glassmorphism UI**: Modern frosted glass design with neon accents
- **Real-time Updates**: WebSocket connections for live data updates
- **Responsive Design**: Optimized for desktop-first, mobile-compatible

### Browser Support
- Chrome/Chromium 88+
- Firefox 85+
- Safari 14+
- Edge 88+

### Installation
1. Open dashboard in supported browser
2. Look for "Install" button in address bar
3. Click to install as PWA
4. Access from desktop/home screen like native app

## 🔧 CLI Usage

The included CLI tool provides powerful command-line management:

```bash
# View all devices
python cli.py devices list --format table

# Filter devices by organization
python cli.py devices list --organization "Main Office" --online-only

# Get device details
python cli.py devices info 11111111-2222-3333-4444-555555555555

# Show device statistics
python cli.py devices stats

# List available scripts
python cli.py scripts list --platform Windows

# Execute script on device
python cli.py scripts execute script-id device-id --variables '{"param1": "value1"}'

# Monitor dashboard
python cli.py monitoring dashboard

# View recent alerts
python cli.py monitoring alerts --priority critical --limit 10

# Trigger data sync
python cli.py sync now

# Check sync status
python cli.py sync status
```

## 🔄 API Endpoints

### Real-time Data
- `GET /api/health` - System health check
- `POST /api/sync/trigger` - Manual data synchronization
- `WS /ws` - WebSocket for real-time updates

### Device Management
- `GET /api/devices/` - List devices with filtering
- `GET /api/devices/stats` - Device statistics
- `GET /api/devices/{id}` - Device details
- `POST /api/devices/{id}/refresh` - Refresh device data
- `GET /api/devices/{id}/notifications` - Device notifications
- `GET /api/devices/{id}/assets` - Device asset information

### Script Execution
- `GET /api/scripts/` - List scripts
- `GET /api/scripts/{id}` - Script details
- `POST /api/scripts/{id}/execute` - Execute script
- `POST /api/scripts/bulk-execute` - Execute on multiple devices
- `GET /api/scripts/{id}/executions/{device_id}` - Execution history

### Notifications
- `GET /api/notifications/` - List notifications
- `POST /api/notifications/push` - Send push notification
- `DELETE /api/notifications/{id}` - Delete notification

## 🏗️ Architecture

### Backend Stack
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: Database ORM with SQLite default
- **WebSockets**: Real-time communication
- **Background Tasks**: Periodic data synchronization
- **Pydantic**: Data validation and serialization

### Frontend Stack
- **Progressive Web App**: Native app experience
- **Vanilla JavaScript**: No framework dependencies
- **CSS Grid/Flexbox**: Responsive layouts
- **CSS Custom Properties**: Theming and glassmorphism
- **Service Worker**: Offline functionality and caching
- **Web Push API**: Browser notifications

### Data Flow
1. **Periodic Sync**: Background task syncs with Pulseway API
2. **Real-time Updates**: WebSocket broadcasts changes to clients
3. **Offline Support**: Service worker caches data and provides offline access
4. **Push Notifications**: Critical alerts trigger browser notifications

## 🔐 Security Considerations

### Authentication
- Configure CORS appropriately for production
- Use environment variables for sensitive data
- Consider adding authentication middleware

### Network Security
- Use HTTPS in production
- Configure firewall rules appropriately
- Consider VPN access for external exposure

### Data Privacy
- Local SQLite database keeps data on-premise
- No data transmitted to third parties
- Configurable data retention policies

## 📊 Monitoring & Observability

### Health Monitoring
- Built-in health check endpoint
- Docker health checks
- WebSocket connection monitoring

### Logging
- Structured logging with Python logging module
- Configurable log levels
- Error tracking and alerting

### Metrics
- Connection count tracking
- API response time monitoring
- Background task status

## 🔧 Customization

### Theming
Modify CSS custom properties in static files:
```css
:root {
    --primary-glow: #00f5ff;    /* Cyan */
    --secondary-glow: #ff00ff;  /* Magenta */
    --success-glow: #00ff88;    /* Green */
    --warning-glow: #ff8800;    /* Orange */
    --error-glow: #ff0055;      /* Red */
}
```

### Configuration
Environment variables control behavior:
- `SYNC_INTERVAL_SECONDS`: How often to sync with Pulseway API
- `UPDATE_INTERVAL_SECONDS`: Real-time update frequency
- `DATABASE_URL`: Database connection string

### Extensions
- Add custom API endpoints in `app/api/`
- Extend database models in `app/models/`
- Add new PWA pages in `app/static/`

## 📈 Performance Optimization

### Backend
- Database connection pooling
- Efficient query design with SQLAlchemy
- Background task optimization
- Response caching where appropriate

### Frontend
- Service worker caching strategy
- Lazy loading for large datasets
- Efficient DOM updates
- Image optimization

### Network
- GZip compression enabled
- Static file caching headers
- WebSocket connection reuse

## 🐛 Troubleshooting

### Common Issues

1. **Pulseway API Connection Failed**
   - Verify `PULSEWAY_TOKEN_ID` and `PULSEWAY_TOKEN_SECRET`
   - Check network connectivity
   - Validate API endpoint URL

2. **Database Issues**
   - Ensure write permissions for SQLite file
   - Check disk space availability
   - Verify database URL format

3. **PWA Installation Issues**
   - Ensure HTTPS in production
   - Verify manifest.json is accessible
   - Check browser PWA support

4. **WebSocket Connection Problems**
   - Check firewall settings
   - Verify proxy configuration
   - Monitor browser console for errors

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

- GitHub Issues: Report bugs and feature requests
- Documentation: Check README and inline comments
- CLI Help: `python cli.py --help`