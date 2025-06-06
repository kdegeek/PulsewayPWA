# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .database import engine, SessionLocal
from .models.database import Base
from .services.data_sync import DataSyncService
from .api import devices, scripts, monitoring
from .pulseway.client import PulsewayClient
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("Starting Pulseway Backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize Pulseway client
    token_id = os.getenv("PULSEWAY_TOKEN_ID")
    token_secret = os.getenv("PULSEWAY_TOKEN_SECRET")

    if not token_id or not token_secret:
        logger.warning("PULSEWAY_TOKEN_ID or PULSEWAY_TOKEN_SECRET not set. Client may not function correctly.")
        # Provide empty strings if None, assuming client might handle this or fail gracefully
        # Or, raise an error here if they are absolutely mandatory for startup
        token_id = token_id or ""
        token_secret = token_secret or ""

    pulseway_client = PulsewayClient(
        base_url=os.getenv("PULSEWAY_BASE_URL", "https://api.pulseway.com/v3/"),
        token_id=token_id,
        token_secret=token_secret
    )
    
    # Initialize data sync service
    data_sync = DataSyncService(pulseway_client)
    
    # Schedule periodic data refresh (every 10 minutes)
    scheduler.add_job(
        data_sync.sync_all_data,
        IntervalTrigger(minutes=10),
        id="data_sync",
        name="Sync Pulseway Data",
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    
    # Initial data sync
    try:
        await data_sync.sync_all_data()
        logger.info("Initial data sync completed")
    except Exception as e:
        logger.error(f"Initial data sync failed: {e}")
    
    # Store services in app state
    app.state.pulseway_client = pulseway_client
    app.state.data_sync = data_sync
    
    yield
    
    # Shutdown
    logger.info("Shutting down Pulseway Backend...")
    scheduler.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Pulseway Backend API",
    description="Robust backend for interfacing with Pulseway instances",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for future PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(devices.router, prefix="/api/devices", tags=["devices"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["monitoring"])

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Pulseway Backend API is running",
        "version": "1.0.0"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    try:
        # Check database connection
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "scheduler": "running" if scheduler.running else "stopped"
    }

@app.post("/api/sync")
async def trigger_sync():
    """Manually trigger data synchronization"""
    try:
        await app.state.data_sync.sync_all_data()
        return {"status": "success", "message": "Data synchronization completed"}
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get Pulseway client
def get_pulseway_client() -> PulsewayClient:
    return app.state.pulseway_client