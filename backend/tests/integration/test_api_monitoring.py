import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# FastAPI app instance
from backend.app.main import app
# SQLAlchemy Base for table metadata
from backend.app.models.database import Base, Device, Notification, Organization, Site, Group, DeviceAsset
# Module to monkeypatch for database redirection
import backend.app.database as app_db

TEST_API_KEY = "your-secret-key-here"
BASE_API_PATH = "/api/monitoring"

@pytest.fixture(scope="function")
def client_with_test_db():
    TEST_DATABASE_URL = "sqlite:///:memory:"
    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    original_engine = app_db.engine
    original_session_local = app_db.SessionLocal
    app_db.engine = test_engine
    app_db.SessionLocal = TestSessionLocal

    Base.metadata.create_all(bind=test_engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=test_engine)

    app_db.engine = original_engine
    app_db.SessionLocal = original_session_local

# Helper functions to create test data
def _create_test_organization(db: Session, **kwargs):
    data = {"name": f"Org-{datetime.now().timestamp()}"}
    data.update(kwargs)
    org = Organization(**data)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

def _create_test_site(db: Session, org_id: int, **kwargs):
    data = {"name": f"Site-{datetime.now().timestamp()}", "parent_id": org_id, "parent_name": "SomeOrg"}
    data.update(kwargs)
    site = Site(**data)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site

def _create_test_group(db: Session, site_id: int, org_id: int, **kwargs):
    data = {
        "name": f"Group-{datetime.now().timestamp()}",
        "parent_site_id": site_id,
        "parent_site_name": "SomeSite",
        "parent_organization_id": org_id,
        "parent_organization_name": "SomeOrg"
    }
    data.update(kwargs)
    group = Group(**data)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

def _create_test_device(db: Session, **kwargs):
    data = {
        "identifier": f"dev-id-{datetime.now().timestamp()}-{kwargs.get('name', 'test')}",
        "name": "Test Device",
        "organization_name": "Default Org",
        "site_name": "Default Site",
        "group_name": "Default Group",
        "is_online": True,
        "last_seen_online": datetime.now(timezone.utc)
    }
    data.update(kwargs)
    device = Device(**data)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

def _create_test_notification(db: Session, device_id: str = None, **kwargs):
    data = {
        "message": "Test Notification",
        "datetime": datetime.now(timezone.utc),
        "priority": "normal",
        "read": False,
        "device_identifier": device_id
    }
    data.update(kwargs)
    notification = Notification(**data)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification

# --- Test Cases ---

# GET /monitoring/dashboard
def test_get_dashboard_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/dashboard", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total_devices"] == 0
    assert data["online_devices"] == 0
    assert data["offline_devices"] == 0
    assert data["critical_alerts"] == 0
    assert data["unread_notifications"] == 0
    assert data["devices_in_maintenance"] == 0
    assert "last_sync_time" in data # Can be None or a string

def test_get_dashboard_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    dev1 = _create_test_device(db, identifier="dash_d1", is_online=True, critical_notifications=1, in_maintenance=True)
    dev2 = _create_test_device(db, identifier="dash_d2", is_online=False)
    _create_test_notification(db, device_id=dev1.identifier, read=False, priority="critical")
    _create_test_notification(db, device_id=dev2.identifier, read=True, priority="normal")
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/dashboard", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total_devices"] == 2
    assert data["online_devices"] == 1
    assert data["offline_devices"] == 1
    assert data["critical_alerts"] == 1 # Based on device.critical_notifications field
    assert data["unread_notifications"] == 1
    assert data["devices_in_maintenance"] == 1

# GET /monitoring/alerts
def test_get_alerts_summary_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/alerts", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total_alerts"] == 0
    assert data["critical_alerts_count"] == 0
    assert data["elevated_alerts_count"] == 0
    assert data["devices_with_critical_alerts"] == 0

def test_get_alerts_summary_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_device(db, identifier="alert_d1", critical_notifications=2, elevated_notifications=1, has_alerts=True, alert_severity="critical")
    _create_test_device(db, identifier="alert_d2", elevated_notifications=3, has_alerts=True, alert_severity="elevated")
    _create_test_device(db, identifier="alert_d3", normal_notifications=5) # No critical/elevated device alerts
    # Create actual notifications for total_alerts count
    _create_test_notification(db, priority="critical", device_identifier="alert_d1")
    _create_test_notification(db, priority="elevated", device_identifier="alert_d2")
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/alerts", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total_alerts"] == 2 # Counts actual Notification records
    assert data["critical_alerts_count"] == 2 # Counts device.critical_notifications
    assert data["elevated_alerts_count"] == 4 # Counts device.elevated_notifications (1+3)
    assert data["devices_with_critical_alerts"] == 1 # Counts devices where alert_severity is critical

# GET /monitoring/health
def test_get_system_health_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/health", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total_devices"] == 0
    assert data["healthy_devices"] == 0
    # ... assert other fields are 0 or empty lists

def test_get_system_health_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_device(db, identifier="health_d1", is_online=True, critical_notifications=0, elevated_notifications=0, firewall_enabled=True, antivirus_up_to_date="Yes") # Healthy
    _create_test_device(db, identifier="health_d2", is_online=True, critical_notifications=1) # Warning/Critical
    _create_test_device(db, identifier="health_d3", is_online=False) # Offline
    _create_test_device(db, identifier="health_d4", in_maintenance=True) # Maintenance
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/health", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total_devices"] == 4
    assert data["healthy_devices"] >= 1 # Depends on exact logic in service
    assert data["offline_devices"] == 1
    assert data["maintenance_mode_devices"] == 1
    assert len(data["devices_with_issues"]) >= 1

# GET /monitoring/activity/recent
def test_get_recent_activity_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/activity/recent", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["activities"]) == 0

def test_get_recent_activity_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    dev = _create_test_device(db, identifier="act_dev1")
    _create_test_notification(db, device_identifier=dev.identifier, message="Msg1", priority="high", datetime=datetime.now(timezone.utc) - timedelta(minutes=5))
    _create_test_notification(db, message="Msg2 Global", priority="normal", datetime=datetime.now(timezone.utc) - timedelta(minutes=10))
    _create_test_notification(db, device_identifier=dev.identifier, message="Msg3", priority="high", datetime=datetime.now(timezone.utc) - timedelta(minutes=1))
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/activity/recent?limit=2&priority_filter=high", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2 # Total high priority notifications
    assert len(data["activities"]) == 2
    assert data["activities"][0]["message"] == "Msg3" # Most recent high priority
    assert data["activities"][1]["message"] == "Msg1"

# GET /monitoring/locations/organizations & /sites
def test_get_location_organizations_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/locations/organizations", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json() == []

def test_get_location_organizations_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    org1 = _create_test_organization(db, name="Org Alpha")
    _create_test_device(db, identifier="loc_d1", organization_id=org1.id, organization_name=org1.name, is_online=True)
    _create_test_device(db, identifier="loc_d2", organization_id=org1.id, organization_name=org1.name, is_online=False, critical_notifications=1)
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/locations/organizations", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Org Alpha"
    assert data[0]["total_devices"] == 2
    assert data[0]["online_devices"] == 1
    assert data[0]["offline_devices"] == 1
    assert data[0]["alerts_count"] == 1

# (Similar tests for /locations/sites would follow)

# GET /monitoring/performance
def test_get_performance_metrics_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/performance", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["average_cpu_usage"] == 0
    assert data["average_memory_usage"] == 0
    assert data["total_online_devices_with_data"] == 0
    assert len(data["top_cpu_usage_devices"]) == 0
    assert len(data["top_memory_usage_devices"]) == 0
    assert data["low_disk_space_devices"] == 0 # Placeholder

def test_get_performance_metrics_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_device(db, identifier="perf_d1", is_online=True, cpu_usage=50.0, memory_usage=60.0)
    _create_test_device(db, identifier="perf_d2", is_online=True, cpu_usage=30.0, memory_usage=40.0)
    _create_test_device(db, identifier="perf_d3", is_online=False, cpu_usage=90.0, memory_usage=90.0) # Offline, ignored
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/performance", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["average_cpu_usage"] == 40.0 # (50+30)/2
    assert data["average_memory_usage"] == 50.0 # (60+40)/2
    assert data["total_online_devices_with_data"] == 2
    assert len(data["top_cpu_usage_devices"]) == 2
    assert data["top_cpu_usage_devices"][0]["name"] == "perf_d1" # Higher CPU
    assert data["top_memory_usage_devices"][0]["name"] == "perf_d1" # Higher Memory

# GET /monitoring/trends/hourly
def test_get_trends_hourly(client_with_test_db: TestClient):
    # This endpoint's logic depends on current data and time. Basic structure check.
    response = client_with_test_db.get(f"{BASE_API_PATH}/trends/hourly?hours=3", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert "labels" in data
    assert "online_devices" in data
    assert "offline_devices" in data
    assert "new_alerts" in data
    assert len(data["labels"]) == 3
    assert len(data["online_devices"]) == 3

# GET /monitoring/notifications/unread
def test_get_unread_notifications_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/notifications/unread", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["notifications"]) == 0

def test_get_unread_notifications_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_notification(db, read=False, priority="high", message="Unread High")
    _create_test_notification(db, read=False, priority="normal", message="Unread Normal")
    _create_test_notification(db, read=True, priority="high", message="Read High")
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/notifications/unread?limit=1&priority_filter=high", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1 # Total unread high-priority
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["message"] == "Unread High"

# POST /monitoring/notifications/{notification_id}/mark-read
def test_mark_notification_read(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    notif = _create_test_notification(db, read=False)
    notif_id = notif.id
    db.close()

    response = client_with_test_db.post(f"{BASE_API_PATH}/notifications/{notif_id}/mark-read", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json()["message"] == "Notification marked as read"

    db = app_db.SessionLocal()
    updated_notif = db.query(Notification).filter(Notification.id == notif_id).first()
    assert updated_notif.read is True
    db.close()

def test_mark_notification_read_not_found(client_with_test_db: TestClient):
    response = client_with_test_db.post(f"{BASE_API_PATH}/notifications/99999/mark-read", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404
    assert "Notification not found" in response.json()["detail"]

# POST /monitoring/notifications/mark-all-read
def test_mark_all_notifications_read(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_notification(db, read=False, message="Unread1")
    _create_test_notification(db, read=False, message="Unread2")
    _create_test_notification(db, read=True, message="AlreadyRead")
    db.close()

    response = client_with_test_db.post(f"{BASE_API_PATH}/notifications/mark-all-read", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    db = app_db.SessionLocal()
    unread_count = db.query(Notification).filter(Notification.read == False).count()
    assert unread_count == 0
    db.close()

# Placeholder for /locations/sites, similar to organizations
def test_get_location_sites_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/locations/sites", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json() == []

def test_get_location_sites_with_data(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    org1 = _create_test_organization(db, name="OrgForSiteTest")
    site1 = _create_test_site(db, org_id=org1.id, name="Site Gamma")
    _create_test_device(db, identifier="loc_s1", site_id=site1.id, site_name=site1.name, organization_id=org1.id, organization_name=org1.name, is_online=True, critical_notifications=1)
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/locations/sites", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Site Gamma"
    assert data[0]["total_devices"] == 1
    assert data[0]["online_devices"] == 1
    assert data[0]["alerts_count"] == 1
