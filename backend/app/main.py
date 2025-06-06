# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware # Added
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
from contextlib import asynccontextmanager
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .database import engine, SessionLocal
from .models.database import Base
from .services.data_sync import DataSyncService
from .api import devices, scripts, monitoring
from .pulseway.client import PulsewayClient
import os
import structlog
import sentry_sdk # Added Sentry

from .logging_config import setup_logging
# Import custom exceptions and the base AppException
from .exceptions import AppException, DatabaseError, ExternalAPIError, AuthenticationError, NotFoundError, BusinessLogicError # Added

# Initialize Sentry SDK
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # Adjust in production!
        traces_sample_rate=1.0,
        # Consider adding environment, release version for better Sentry event filtering
        # environment=os.getenv("ENVIRONMENT", "development"),
        # release="pulseway-backend@1.0.0" # Replace with dynamic version
    )
    # Use logger for this message
    # Potential issue: logger might not be configured yet if setup_logging is called after this.
    # However, structlog.get_logger() can be called before configure, messages will be buffered.
    # For now, let's assume basic logging (like print to stdout) might happen or it's buffered.
    # A better pattern is to configure logging (stdlib part) then Sentry then structlog processors.
    # Given current structure, will use a temp logger or print if logger is not yet useful.
    # Safest is to move Sentry init after basic logging is up.
    # Let's assume logger is available for now from structlog's global config.
    structlog.get_logger("sentry_init").info(f"Sentry initialized with DSN starting: {SENTRY_DSN[:20]}...")
else:
    # Same assumption for logger here.
    structlog.get_logger("sentry_init").warning("Sentry DSN not found, Sentry will not be initialized.")


# Configure structlog
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
logger = structlog.get_logger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler()

# API Key Verification
async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    expected_api_key = os.getenv("API_KEY")
    if expected_api_key is None:
        expected_api_key = "your-secret-key-here"  # Fallback as per original snippet

    if x_api_key != expected_api_key:
        logger.warning("Failed API key verification attempt.") # Example of a log, API is similar
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("Starting Pulseway Backend...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize Pulseway client
    pulseway_client = PulsewayClient(
        base_url=os.getenv("PULSEWAY_BASE_URL", "https://api.pulseway.com/v3/"),
        token_id=os.getenv("PULSEWAY_TOKEN_ID"),
        token_secret=os.getenv("PULSEWAY_TOKEN_SECRET")
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
        logger.error("Initial data sync failed", error=str(e)) # structlog encourages key-value pairs
    
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
    version="1.0.0-alpha.1",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)]
)

# Custom Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    # Manually capture the exception with Sentry, if Sentry is initialized
    if SENTRY_DSN: # Only attempt to capture if Sentry was initialized
        sentry_sdk.capture_exception(exc)

    logger.error(
        "Application error occurred",
        type=type(exc).__name__,
        detail=exc.detail,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method,
        exc_info=True # Include stack trace if appropriate, or remove for production verbosity control
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# If you need more specific handling for certain AppException subtypes, you can add them here.
# For example, if DatabaseError needed a very different response structure:
# @app.exception_handler(DatabaseError)
# async def database_exception_handler(request: Request, exc: DatabaseError):
#     logger.error("Database error", detail=exc.detail, path=request.url.path, method=request.method, exc_info=True)
#     return JSONResponse(status_code=exc.status_code, content={"error_type": "database", "message": exc.detail})
# Otherwise, the AppException handler above will catch DatabaseError and other children.


# Request Tracing Middleware
@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())

    # Bind request_id to structlog context for this request
    structlog.contextvars.bind_contextvars(request_id=request_id)

    # Initial log with request details (optional, but good for tracing start)
    logger.debug("Request received", method=request.method, path=request.url.path, client_host=request.client.host if request.client else "unknown")

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        # Log after response is generated (optional, but good for tracing end)
        logger.debug("Request finished", method=request.method, path=request.url.path, status_code=response.status_code)
    except Exception as e:
        # Log any exception that occurs during request processing
        logger.error("Request failed during processing", exc_info=True, method=request.method, path=request.url.path)
        # Important: Re-raise the exception so FastAPI can handle it
        raise e
    finally:
        # Clear context variables for the next request to prevent leakage
        structlog.contextvars.clear_contextvars()

    return response

# Add CORS middleware for future PWA
# This should typically come after tracing middleware if you want tracing on CORS preflight requests too
app.add_middleware(
    CORSMiddleware,
    # TODO: Restrict allow_origins for production environments.
    allow_origins=["https://yourdomain.com", "http://localhost:3000"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(scripts.router, prefix="/api/v1/scripts", tags=["scripts"])
app.include_router(monitoring.router, prefix="/api/v1/monitoring", tags=["monitoring"])

@app.get("/")
async def root():
    """Health check endpoint"""
    logger.debug("Root health check requested") # Example of debug log
    return {
        "status": "healthy",
        "message": "Pulseway Backend API is running",
        "version": "1.0.0-alpha.1"
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    logger.info("Detailed health check requested")
    db_status = "unknown"
    try:
        # Check database connection
        db = SessionLocal()
        # For SQLAlchemy 2.0, use text() if you're executing a literal SQL string
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = "unhealthy" # Corrected from f"unhealthy"
        logger.error("Database health check failed", error=str(e), exc_info=True) # Add exc_info for stacktrace
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "scheduler": "running" if scheduler.running else "stopped"
    }

@app.post("/api/sync")
async def trigger_sync():
    """Manually trigger data synchronization"""
    logger.info("Manual data synchronization triggered")
    try:
        await app.state.data_sync.sync_all_data()
        return {"status": "success", "message": "Data synchronization completed"}
    # Let the global AppException handler catch errors from data_sync service
    except AppException as e:
        # Logged by the global handler already. Re-raise if you want FastAPI's default handling for some reason,
        # or trust the global handler to return the JSONResponse.
        # For this setup, we trust the global handler.
        raise e
    except Exception as e: # Catch any other unexpected non-AppException
        logger.error("Unexpected error during manual sync", error=str(e), exc_info=True)
        # Convert to a generic HTTPException or let a generic AppExc handler (if any for Exception) handle it
        raise HTTPException(status_code=500, detail="An unexpected server error occurred during sync.")

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