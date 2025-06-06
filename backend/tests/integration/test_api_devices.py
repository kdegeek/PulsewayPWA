import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# FastAPI app instance
from backend.app.main import app
# SQLAlchemy Base for table metadata
from backend.app.models.database import Base
# Module to monkeypatch for database redirection
import backend.app.database as app_db
# Device model for potentially creating test data in more advanced tests later
from backend.app.models.database import Device, Notification, DeviceAsset
from datetime import datetime, timezone
from unittest.mock import patch # For mocking PulsewayClient

# Use the fallback API key from main.py if no specific test key is set via env
TEST_API_KEY = "your-secret-key-here"

# Helper function to create a device in the test DB
def _create_device_in_db(db_session, **kwargs):
    default_data = {
        "identifier": f"test-dev-{datetime.now().timestamp()}", # Ensure unique ID
        "name": "Test Device",
        "organization_name": "Test Org",
        "site_name": "Test Site",
        "group_name": "Test Group",
        "last_seen_online": datetime.now(timezone.utc)
    }
    default_data.update(kwargs)
    device = Device(**default_data)
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)
    return device

@pytest.fixture(scope="function")
def client_with_test_db():
    """
    Pytest fixture to provide a TestClient with an isolated in-memory SQLite database.
    It monkeypatches the application's database engine and session factory.
    """
    TEST_DATABASE_URL = "sqlite:///:memory:"

    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # --- Monkeypatch the application's database dependencies ---
    original_engine = app_db.engine
    original_session_local = app_db.SessionLocal

    app_db.engine = test_engine
    app_db.SessionLocal = TestSessionLocal
    # --- End Monkeypatch ---

    # Create all tables in the test database.
    # The app's lifespan manager (in main.py) calls Base.metadata.create_all(bind=engine).
    # Since app_db.engine is now test_engine, this should use the in-memory DB.
    # If issues arise, explicit creation here can be done:
    # Base.metadata.create_all(bind=test_engine)

    # Yield the TestClient. The app's lifespan (including table creation)
    # will be triggered when the client initializes the app.
    with TestClient(app) as c:
        yield c

    # Drop all tables from the test database after the test.
    # This is crucial for test isolation if Base.metadata.create_all was called.
    Base.metadata.drop_all(bind=test_engine) # Ensure cleanup

    # --- Restore original database dependencies ---
    app_db.engine = original_engine
    app_db.SessionLocal = original_session_local
    # --- End Restore ---

# --- API Tests for /api/devices ---

def test_get_devices_empty(client_with_test_db: TestClient):
    """
    Test GET /api/devices when no devices are in the database.
    Expects a 200 OK and an empty list of devices.
    """
    response = client_with_test_db.get("/api/devices", headers={"X-API-Key": TEST_API_KEY})

    assert response.status_code == 200
    api_response = response.json()
    # Based on backend/app/api/devices.py, the response for no devices should be:
    # {"devices": [], "total": 0, "page": 1, "page_size": 100, "total_pages": 0}
    # or similar if default pagination is applied.
    # Let's check the actual response structure from the service for an empty case.
    # Assuming default pagination (page=1, page_size=100) from DeviceFilters model.
    assert api_response == {
        "devices": [],
        "total": 0,
        "page": 1,
        "page_size": 100, # Default page_size from DeviceFilters
        "total_pages": 0   # Calculated as ceil(total / page_size)
    }

def test_get_devices_requires_api_key(client_with_test_db: TestClient):
    """
    Test GET /api/devices without providing an API key.
    Expects a 401 Unauthorized error.
    """
    response = client_with_test_db.get("/api/devices") # No X-API-Key header

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}

# Example of a test that adds data (can be expanded later)
def test_get_devices_with_data(client_with_test_db: TestClient):
    """
    Test GET /api/devices when there is data in the database.
    """
    # Get a database session to add data directly (using the patched SessionLocal)
    db = app_db.SessionLocal()
    try:
        device1_data = {
            "identifier": "test_dev_001", "name": "API Test Device 1",
            "organization_name": "Org API", "site_name": "Site API", "group_name": "Group API",
            "last_seen_online": datetime.now(timezone.utc)
        }
        device2_data = {
            "identifier": "test_dev_002", "name": "API Test Device 2",
            "organization_name": "Org API", "site_name": "Site API", "group_name": "Group API",
            "last_seen_online": datetime.now(timezone.utc)
        }
        db.add(Device(**device1_data))
        db.add(Device(**device2_data))
        db.commit()
    finally:
        db.close()

    response = client_with_test_db.get("/api/devices", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    api_response = response.json()

    assert api_response["total"] == 2
    assert len(api_response["devices"]) == 2
    assert api_response["devices"][0]["identifier"] in ["test_dev_001", "test_dev_002"]
    assert api_response["devices"][1]["identifier"] in ["test_dev_001", "test_dev_002"]
    assert api_response["devices"][0]["name"].startswith("API Test Device")
    assert api_response["page"] == 1
    assert api_response["page_size"] == 100 # Default
    assert api_response["total_pages"] == 1


# --- POST /api/devices/refresh/{device_id} ---

@patch('backend.app.main.app.state.pulseway_client.get_device')
def test_refresh_single_device_success(mock_pulseway_get_device, client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    device_in_db = _create_device_in_db(db, identifier="refresh_dev_001", name="Old Name", is_online=False)
    db.close()

    mock_pulseway_api_data = {
        'Data': {
            'Name': 'Updated Name from API',
            'IsOnline': True,
            'LastSeenOnline': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        }
    }
    mock_pulseway_get_device.return_value = mock_pulseway_api_data

    response = client_with_test_db.post(f"/api/devices/refresh/{device_in_db.identifier}", headers={"X-API-Key": TEST_API_KEY})

    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Device data refreshed successfully."}
    mock_pulseway_get_device.assert_called_once_with(device_in_db.identifier)

    db = app_db.SessionLocal()
    updated_device = db.query(Device).filter(Device.identifier == device_in_db.identifier).first()
    assert updated_device.name == "Updated Name from API"
    assert updated_device.is_online is True
    db.close()

def test_refresh_single_device_not_in_db(client_with_test_db: TestClient):
    response = client_with_test_db.post("/api/devices/refresh/non_existent_device", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404 # Based on DeviceService.get_device_or_raise
    assert "not found in local database" in response.json()["detail"]

@patch('backend.app.main.app.state.pulseway_client.get_device')
def test_refresh_single_device_not_in_pulseway(mock_pulseway_get_device, client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    device_in_db = _create_device_in_db(db, identifier="refresh_dev_002", name="Not in Pulseway")
    db.close()

    mock_pulseway_get_device.return_value = {'Data': {}} # Pulseway API indicates no data

    response = client_with_test_db.post(f"/api/devices/refresh/{device_in_db.identifier}", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404 # Or other appropriate error from service
    assert "not found in Pulseway or no data returned" in response.json()["detail"]


# --- GET /api/devices/stats ---

def test_get_device_stats_empty_db(client_with_test_db: TestClient):
    response = client_with_test_db.get("/api/devices/stats", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_devices"] == 0
    assert stats["online_devices"] == 0
    assert stats["offline_devices"] == 0
    assert stats["devices_by_organization"] == {}
    # ... other stats should be zero/empty

def test_get_device_stats_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="stat_dev_001", name="Online Server", is_online=True, organization_name="Org A", computer_type="Server", critical_notifications=1)
    _create_device_in_db(db, identifier="stat_dev_002", name="Offline Workstation", is_online=False, organization_name="Org B", computer_type="Workstation", agent_status="operational") # Assume agent_status exists
    _create_device_in_db(db, identifier="stat_dev_003", name="Online Server Org A", is_online=True, organization_name="Org A", computer_type="Server", elevated_notifications=2)
    db.close()

    response = client_with_test_db.get("/api/devices/stats", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    stats = response.json()
    assert stats["total_devices"] == 3
    assert stats["online_devices"] == 2
    assert stats["offline_devices"] == 1
    assert stats["devices_by_organization"]["Org A"] == 2
    assert stats["devices_by_organization"]["Org B"] == 1
    assert stats["devices_by_type"]["Server"] == 2
    assert stats["devices_by_type"]["Workstation"] == 1
    assert stats["critical_alerts"] == 1 # Assuming the field is critical_notifications
    assert stats["elevated_alerts"] == 2 # Assuming the field is elevated_notifications
    # assert stats["devices_with_agent"] == 1 # Depends on how agent_status is set/queried

# --- GET /api/devices/search ---

def test_search_devices(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="search_dev_001", name="Alpha Server", description="Main production server")
    _create_device_in_db(db, identifier="search_dev_002", name="Beta Workstation", external_ip_address="10.0.0.1")
    db.close()

    # Search by name
    response = client_with_test_db.get("/api/devices/search?term=Alpha", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["name"] == "Alpha Server"

    # Search by description (if service supports it)
    response = client_with_test_db.get("/api/devices/search?term=production", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["name"] == "Alpha Server"

    # Search by IP (if service supports it)
    response = client_with_test_db.get("/api/devices/search?term=10.0.0.1", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["name"] == "Beta Workstation"

    # No results
    response = client_with_test_db.get("/api/devices/search?term=OmegaXYZ", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["devices"]) == 0

# --- GET /api/devices/{device_id} ---

def test_get_device_by_id_found(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    device = _create_device_in_db(db, identifier="get_dev_001", name="Specific Device")
    db.close()

    response = client_with_test_db.get(f"/api/devices/{device.identifier}", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["identifier"] == device.identifier
    assert data["name"] == "Specific Device"

def test_get_device_by_id_not_found(client_with_test_db: TestClient):
    response = client_with_test_db.get("/api/devices/non_existent_id", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404
    assert response.json()["detail"] == "Device with ID non_existent_id not found."


# --- GET /api/devices/org/{org_name} & /site/{site_name} ---
def test_get_devices_by_org_name(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="org_dev_001", organization_name="OrgX")
    _create_device_in_db(db, identifier="org_dev_002", organization_name="OrgX")
    _create_device_in_db(db, identifier="org_dev_003", organization_name="OrgY")
    db.close()

    response = client_with_test_db.get("/api/devices/org/OrgX", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["devices"]) == 2
    assert all(d["organization_name"] == "OrgX" for d in data["devices"])

    response_empty = client_with_test_db.get("/api/devices/org/OrgZ", headers={"X-API-Key": TEST_API_KEY})
    assert response_empty.status_code == 200
    data_empty = response_empty.json()
    assert data_empty["total"] == 0

def test_get_devices_by_site_name(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="site_dev_001", site_name="SiteAlpha")
    db.close()

    response = client_with_test_db.get("/api/devices/site/SiteAlpha", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["site_name"] == "SiteAlpha"


# --- Alert & Offline Endpoints ---
def test_get_devices_critical_alerts(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="crit_alert_dev", has_alerts=True, alert_severity="critical")
    _create_device_in_db(db, identifier="no_crit_alert_dev", has_alerts=True, alert_severity="elevated")
    db.close()

    response = client_with_test_db.get("/api/devices/alerts/critical", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["identifier"] == "crit_alert_dev"

def test_get_devices_elevated_alerts(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="elev_alert_dev", has_alerts=True, alert_severity="elevated")
    db.close()
    response = client_with_test_db.get("/api/devices/alerts/elevated", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["identifier"] == "elev_alert_dev"

def test_get_offline_devices(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_device_in_db(db, identifier="offline_dev", is_online=False)
    _create_device_in_db(db, identifier="online_dev", is_online=True)
    db.close()
    response = client_with_test_db.get("/api/devices/offline", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["devices"][0]["identifier"] == "offline_dev"


# --- GET /api/devices/{device_id}/notifications ---
def test_get_device_notifications(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    device = _create_device_in_db(db, identifier="dev_with_notifs_01")
    notif1 = Notification(device_identifier=device.identifier, message="N1", datetime=datetime.now(timezone.utc), priority="high")
    notif2 = Notification(device_identifier=device.identifier, message="N2", datetime=datetime.now(timezone.utc), priority="low")
    db.add_all([notif1, notif2])
    db.commit()
    db.close()

    response = client_with_test_db.get(f"/api/devices/{device.identifier}/notifications", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["notifications"]) == 2
    assert data["notifications"][0]["message"] in ["N1", "N2"]

def test_get_device_notifications_no_device(client_with_test_db: TestClient):
    response = client_with_test_db.get("/api/devices/no_such_device/notifications", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404 # From get_device_or_raise

# --- GET /api/devices/{device_id}/asset ---
def test_get_device_asset(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    device = _create_device_in_db(db, identifier="dev_with_asset_01")
    asset = DeviceAsset(device_identifier=device.identifier, asset_info={"os": "Windows 11"}, tags=["test"])
    db.add(asset)
    db.commit()
    db.close()

    response = client_with_test_db.get(f"/api/devices/{device.identifier}/asset", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["device_identifier"] == device.identifier
    assert data["asset_info"]["os"] == "Windows 11"

def test_get_device_asset_no_asset(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    device = _create_device_in_db(db, identifier="dev_no_asset_01")
    db.close()
    response = client_with_test_db.get(f"/api/devices/{device.identifier}/asset", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404 # As DeviceService raises ValueError -> mapped to 404 by handler or default
    assert "Assets not found" in response.json()["detail"]

def test_get_device_asset_no_device(client_with_test_db: TestClient):
    response = client_with_test_db.get("/api/devices/no_such_device/asset", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404 # From get_device_or_raise
