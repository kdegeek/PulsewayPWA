import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, MagicMock, AsyncMock

# FastAPI app instance
from backend.app.main import app
# SQLAlchemy Base for table metadata
from backend.app.models.database import Base
# Module to monkeypatch for database redirection
import backend.app.database as app_db
# Custom exceptions for testing error handling
from backend.app.exceptions import AppException, ExternalAPIError

TEST_API_KEY = "your-secret-key-here"

@pytest.fixture(scope="function")
def client_with_test_db():
    TEST_DATABASE_URL = "sqlite:///:memory:"
    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    original_engine = app_db.engine
    original_session_local = app_db.SessionLocal
    app_db.engine = test_engine
    app_db.SessionLocal = TestSessionLocal

    # Mock app.state components that might be initialized in lifespan
    # and rely on external services or complex setup not needed for all main endpoint tests.
    # data_sync service is particularly relevant for /api/sync.
    mock_pw_client = MagicMock()
    mock_data_sync_service = MagicMock()
    # Make sync_all_data an AsyncMock if the original is an async def
    mock_data_sync_service.sync_all_data = AsyncMock()


    original_app_state_pulseway_client = getattr(app.state, 'pulseway_client', None)
    original_app_state_data_sync = getattr(app.state, 'data_sync', None)

    app.state.pulseway_client = mock_pw_client
    app.state.data_sync = mock_data_sync_service

    # Tables are created by the app's lifespan manager using the patched engine
    # Base.metadata.create_all(bind=test_engine) # Can be explicit if needed

    with TestClient(app) as c:
        yield c # TestClient now uses the app with mocked state components

    Base.metadata.drop_all(bind=test_engine)

    # Restore original app.state components
    if original_app_state_pulseway_client:
        app.state.pulseway_client = original_app_state_pulseway_client
    elif hasattr(app.state, 'pulseway_client'): # Ensure it's removed if added by this fixture only
        delattr(app.state, 'pulseway_client')

    if original_app_state_data_sync:
        app.state.data_sync = original_app_state_data_sync
    elif hasattr(app.state, 'data_sync'): # Ensure it's removed if added by this fixture only
        delattr(app.state, 'data_sync')

    app_db.engine = original_engine
    app_db.SessionLocal = original_session_local

# --- Test Cases for Main App Endpoints ---

# GET / (Root Health Check)
def test_get_root_health_check_with_api_key(client_with_test_db: TestClient):
    response = client_with_test_db.get("/", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    expected_response = {
        "status": "healthy",
        "message": "Pulseway Backend API is running",
        "version": "1.0.0-alpha.1"  # Assuming this is the version in main.py
    }
    assert response.json() == expected_response

def test_get_root_health_check_no_api_key(client_with_test_db: TestClient):
    response = client_with_test_db.get("/")
    assert response.status_code == 401 # Due to global dependency
    assert response.json() == {"detail": "Invalid or missing API key"}

# GET /api/health (Detailed Health Check)
def test_get_api_health_detailed(client_with_test_db: TestClient):
    response = client_with_test_db.get("/api/health", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy" # Should be healthy as DB is working
    assert data["database"] == "healthy"
    assert data["scheduler"] == "running" # TestClient runs lifespan, so scheduler should be running

# POST /api/sync (Manual Data Synchronization Trigger)
def test_post_api_sync_success(client_with_test_db: TestClient):
    # app.state.data_sync.sync_all_data is already an AsyncMock from the fixture setup
    # We can configure its return value if needed, but by default, it does nothing and returns None.
    # The endpoint doesn't check the return value of sync_all_data, just that it doesn't error.

    response = client_with_test_db.post("/api/sync", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Data synchronization completed"}
    app.state.data_sync.sync_all_data.assert_awaited_once() # Verify the mocked async method was called

def test_post_api_sync_app_exception(client_with_test_db: TestClient):
    # Configure the mock to raise a specific AppException
    app.state.data_sync.sync_all_data.side_effect = ExternalAPIError("Pulseway API is down for sync")

    response = client_with_test_db.post("/api/sync", headers={"X-API-Key": TEST_API_KEY})
    # ExternalAPIError has a default status_code of 502
    assert response.status_code == 502
    assert response.json() == {"detail": "Pulseway API is down for sync"}
    app.state.data_sync.sync_all_data.assert_awaited_once()

def test_post_api_sync_generic_exception(client_with_test_db: TestClient):
    # Configure the mock to raise a generic Exception
    app.state.data_sync.sync_all_data.side_effect = Exception("A very unexpected error occurred")

    response = client_with_test_db.post("/api/sync", headers={"X-API-Key": TEST_API_KEY})
    # The custom exception handler for generic Exception in main.py converts it to HTTPException(500)
    assert response.status_code == 500
    assert response.json() == {"detail": "An unexpected server error occurred during sync."}
    app.state.data_sync.sync_all_data.assert_awaited_once()
