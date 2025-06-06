# app/main.py - Enhanced main file with PWA support
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import asyncio
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
import os
from pathlib import Path

from .database import engine, SessionLocal
from .models.database import Base
from .pulseway.client import PulsewayClient
from .services.data_sync import DataSyncService
from .api import devices, scripts, notifications, organizations

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Pulseway Dashboard API",
    description="Self-hosted Pulseway monitoring dashboard",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, List[str]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = []
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict, event_type: Optional[str] = None):
        """Broadcast message to all connected clients or filtered by subscription"""
        disconnected = []
        for connection in self.active_connections:
            try:
                # Check if client is subscribed to this event type
                if event_type and event_type not in self.subscriptions.get(connection, []):
                    continue
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def subscribe(self, websocket: WebSocket, event_types: List[str]):
        """Subscribe client to specific event types"""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].extend(event_types)
        else:
            self.subscriptions[websocket] = event_types

manager = ConnectionManager()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Pulseway Dashboard...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize Pulseway client
    token_id = os.getenv("PULSEWAY_TOKEN_ID")
    token_secret = os.getenv("PULSEWAY_TOKEN_SECRET")
    base_url = os.getenv("PULSEWAY_BASE_URL", "https://api.pulseway.com/v3/")
    
    if token_id and token_secret:
        pulseway_client = PulsewayClient(base_url, token_id, token_secret)
        app.state.pulseway_client = pulseway_client
        
        # Test connection
        if pulseway_client.health_check():
            logger.info("✅ Pulseway API connection successful")
            
            # Start background sync
            asyncio.create_task(background_sync_task())
        else:
            logger.error("❌ Pulseway API connection failed")
    else:
        logger.warning("⚠️ Pulseway credentials not provided")

    # Start real-time update task
    asyncio.create_task(real_time_updates_task())

# Background sync task
async def background_sync_task():
    """Periodic data synchronization with Pulseway API"""
    sync_interval = int(os.getenv("SYNC_INTERVAL_SECONDS", "300"))  # 5 minutes default
    
    while True:
        try:
            if hasattr(app.state, 'pulseway_client'):
                logger.info("🔄 Starting background sync...")
                sync_service = DataSyncService(app.state.pulseway_client)
                await sync_service.sync_all_data()
                
                # Broadcast update to connected clients
                await manager.broadcast({
                    "type": "DATA_SYNC_COMPLETE",
                    "timestamp": datetime.now().isoformat(),
                    "message": "Data synchronization completed"
                }, "sync")
                
                logger.info("✅ Background sync completed")
            
        except Exception as e:
            logger.error(f"❌ Background sync failed: {e}")
            await manager.broadcast({
                "type": "SYNC_ERROR",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }, "sync")
        
        await asyncio.sleep(sync_interval)

# Real-time updates task
async def real_time_updates_task():
    """Send periodic updates to connected clients"""
    update_interval = int(os.getenv("UPDATE_INTERVAL_SECONDS", "30"))  # 30 seconds default
    
    while True:
        try:
            if len(manager.active_connections) > 0:
                # Get fresh stats
                db = SessionLocal()
                try:
                    from .models.database import Device, Notification
                    
                    total_devices = db.query(Device).count()
                    online_devices = db.query(Device).filter(Device.is_online == True).count()
                    critical_alerts = db.query(Device).filter(Device.critical_notifications > 0).count()
                    
                    # Get recent notifications
                    recent_notifications = db.query(Notification).order_by(
                        Notification.datetime.desc()
                    ).limit(5).all()
                    
                    update_data = {
                        "type": "STATS_UPDATE",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "total_devices": total_devices,
                            "online_devices": online_devices,
                            "offline_devices": total_devices - online_devices,
                            "critical_alerts": critical_alerts,
                            "recent_notifications": [
                                {
                                    "id": n.id,
                                    "message": n.message,
                                    "priority": n.priority,
                                    "datetime": n.datetime.isoformat() if n.datetime else None
                                } for n in recent_notifications
                            ]
                        }
                    }
                    
                    await manager.broadcast(update_data, "stats")
                    
                finally:
                    db.close()
        
        except Exception as e:
            logger.error(f"Real-time update failed: {e}")
        
        await asyncio.sleep(update_interval)

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle subscription requests
            if message.get("type") == "SUBSCRIBE":
                event_types = message.get("events", [])
                await manager.subscribe(websocket, event_types)
                await manager.send_personal_message({
                    "type": "SUBSCRIPTION_CONFIRMED",
                    "events": event_types
                }, websocket)
            
            # Handle ping/pong for connection health
            elif message.get("type") == "PING":
                await manager.send_personal_message({
                    "type": "PONG",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Push notification endpoint
@app.post("/api/notifications/push")
async def send_push_notification(
    title: str,
    body: str,
    priority: str = "normal",
    device_id: Optional[str] = None,
    url: Optional[str] = None
):
    """Send push notification to all connected clients"""
    
    notification_data = {
        "type": "PUSH_NOTIFICATION",
        "timestamp": datetime.now().isoformat(),
        "notification": {
            "title": title,
            "body": body,
            "priority": priority,
            "device_id": device_id,
            "url": url,
            "tag": f"alert-{datetime.now().timestamp()}"
        }
    }
    
    await manager.broadcast(notification_data, "notifications")
    
    return {"status": "sent", "message": "Push notification broadcast to all clients"}

# Manual sync trigger
@app.post("/api/sync/trigger")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Manually trigger data synchronization"""
    
    if not hasattr(app.state, 'pulseway_client'):
        raise HTTPException(status_code=503, detail="Pulseway client not configured")
    
    async def sync_task():
        try:
            sync_service = DataSyncService(app.state.pulseway_client)
            await sync_service.sync_all_data()
            
            await manager.broadcast({
                "type": "MANUAL_SYNC_COMPLETE",
                "timestamp": datetime.now().isoformat()
            }, "sync")
            
        except Exception as e:
            await manager.broadcast({
                "type": "SYNC_ERROR",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }, "sync")
    
    background_tasks.add_task(sync_task)
    return {"status": "triggered", "message": "Data synchronization started"}

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "active_connections": len(manager.active_connections),
        "pulseway_configured": hasattr(app.state, 'pulseway_client')
    }
    
    # Test Pulseway connection if configured
    if hasattr(app.state, 'pulseway_client'):
        health_status["pulseway_status"] = app.state.pulseway_client.health_check()
    
    return health_status

# Include API routers
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(organizations.router, prefix="/api/organizations", tags=["organizations"])

# Serve PWA static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# PWA routes
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve main dashboard page"""
    return FileResponse(static_dir / "index.html")

@app.get("/devices", response_class=HTMLResponse)
async def serve_devices():
    """Serve devices page"""
    return FileResponse(static_dir / "devices.html")

@app.get("/scripts", response_class=HTMLResponse)
async def serve_scripts():
    """Serve scripts page"""
    return FileResponse(static_dir / "scripts.html")

@app.get("/notifications", response_class=HTMLResponse)
async def serve_notifications():
    """Serve notifications page"""
    return FileResponse(static_dir / "notifications.html")

@app.get("/settings", response_class=HTMLResponse)
async def serve_settings():
    """Serve settings page"""
    return FileResponse(static_dir / "settings.html")

# PWA manifest and service worker
@app.get("/manifest.json")
async def serve_manifest():
    """Serve PWA manifest"""
    return FileResponse(static_dir / "manifest.json")

@app.get("/sw.js")
async def serve_service_worker():
    """Serve service worker"""
    return FileResponse(static_dir / "sw.js")

# PWA icons
@app.get("/icon-{size}.png")
async def serve_icon(size: str):
    """Serve PWA icons"""
    return FileResponse(static_dir / f"icon-{size}.png")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)