import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import uuid

# FastAPI app instance
from backend.app.main import app
# SQLAlchemy Base for table metadata
from backend.app.models.database import Base, Device, Script
# Module to monkeypatch for database redirection
import backend.app.database as app_db
# Pulseway client exceptions
from backend.app.pulseway.client import PulsewayAPIError, PulsewayNotFoundError

TEST_API_KEY = "your-secret-key-here"
BASE_API_PATH = "/api/scripts"

@pytest.fixture(scope="function")
def client_with_test_db():
    TEST_DATABASE_URL = "sqlite:///:memory:"
    test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    original_engine = app_db.engine
    original_session_local = app_db.SessionLocal
    app_db.engine = test_engine
    app_db.SessionLocal = TestSessionLocal

    # Explicitly create tables for the test session
    Base.metadata.create_all(bind=test_engine)

    # Mock app.state.pulseway_client before TestClient is initialized
    # This ensures the dependency get_pulseway_client in main.py gets the mock
    mock_pw_client = MagicMock()

    # Store original app.state if it exists, to restore later
    original_app_state_pulseway_client = getattr(app.state, 'pulseway_client', None)
    app.state.pulseway_client = mock_pw_client

    with TestClient(app) as c:
        yield c # TestClient now uses the app with the mocked pulseway_client in its state

    Base.metadata.drop_all(bind=test_engine) # Clean up tables

    # Restore original app.state.pulseway_client
    if original_app_state_pulseway_client:
        app.state.pulseway_client = original_app_state_pulseway_client
    else:
        delattr(app.state, 'pulseway_client') # If it wasn't there before

    app_db.engine = original_engine
    app_db.SessionLocal = original_session_local

# Helper functions
def _create_test_device(db: Session, **kwargs):
    data = {
        "identifier": f"dev-id-{uuid.uuid4()}",
        "name": "Test Device",
        "is_online": True,
        "last_seen_online": datetime.now(timezone.utc)
    }
    data.update(kwargs)
    device = Device(**data)
    db.add(device)
    db.commit()
    db.refresh(device)
    return device

def _create_test_script(db: Session, **kwargs):
    data = {
        "id": f"script-id-{uuid.uuid4()}",
        "name": "Test Script",
        "description": "A test script",
        "platforms": ["windows", "linux"],
        "category_name": "Utility"
    }
    data.update(kwargs)
    script = Script(**data)
    db.add(script)
    db.commit()
    db.refresh(script)
    return script

# --- Test Cases ---

# GET /scripts/
def test_get_scripts_empty(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["scripts"] == []
    assert data["total"] == 0

def test_get_scripts_with_data_and_filters(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_script(db, name="Windows Utility", platforms=["windows"], category_name="Utility", is_built_in=True)
    _create_test_script(db, name="Linux Monitoring", platforms=["linux"], category_name="Monitoring", is_built_in=False)
    _create_test_script(db, name="Cross-Platform Script", platforms=["windows", "macos"], category_name="Utility")
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/?platform=windows&category=Utility&built_in_only=false&custom_only=false&search=script", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1 # Should find "Cross-Platform Script" and potentially "Windows Utility"
    assert any(s["name"] == "Cross-Platform Script" for s in data["scripts"])

    response_custom = client_with_test_db.get(f"{BASE_API_PATH}/?custom_only=true", headers={"X-API-Key": TEST_API_KEY})
    data_custom = response_custom.json()
    assert all(not s.get("is_built_in", False) for s in data_custom["scripts"])
    assert any(s["name"] == "Linux Monitoring" for s in data_custom["scripts"])


# GET /scripts/{script_id}
def test_get_script_by_id_local_db(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    script = _create_test_script(db, id="local_script_1", name="Local Script")
    db.close()
    response = client_with_test_db.get(f"{BASE_API_PATH}/{script.id}", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == script.id
    assert data["name"] == script.name

@patch.object(app.state, 'pulseway_client', new_callable=MagicMock) # Patch the client on app.state
def test_get_script_by_id_pulseway_api(mock_pw_client_on_state, client_with_test_db: TestClient):
    script_id = "pulseway_script_1"
    mock_pw_client_on_state.get_script.return_value = {"id": script_id, "name": "Pulseway API Script", "description": "Fetched from API"}

    response = client_with_test_db.get(f"{BASE_API_PATH}/{script_id}", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == script_id
    assert data["name"] == "Pulseway API Script"
    mock_pw_client_on_state.get_script.assert_called_once_with(script_id)

@patch.object(app.state, 'pulseway_client', new_callable=MagicMock)
def test_get_script_by_id_not_found_anywhere(mock_pw_client_on_state, client_with_test_db: TestClient):
    script_id = "ghost_script"
    mock_pw_client_on_state.get_script.side_effect = PulsewayNotFoundError("Script not found in Pulseway")

    response = client_with_test_db.get(f"{BASE_API_PATH}/{script_id}", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

# POST /scripts/{script_id}/execute
@patch.object(app.state, 'pulseway_client', new_callable=MagicMock)
def test_execute_script_success(mock_pw_client_on_state, client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    script = _create_test_script(db, id="exec_script_1")
    device = _create_test_device(db, identifier="exec_dev_1", is_online=True)
    db.close()

    mock_pw_client_on_state.run_script.return_value = {"success": True, "executionId": "exec123"}
    payload = {"device_ids": [device.identifier], "parameters": {"param1": "value1"}}
    response = client_with_test_db.post(f"{BASE_API_PATH}/{script.id}/execute", json=payload, headers={"X-API-Key": TEST_API_KEY})

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Script execution initiated successfully."
    # This endpoint returns a summary now.
    assert len(data["results"]) == 1
    assert data["results"][0]["device_id"] == device.identifier
    assert data["results"][0]["status"] == "success"
    mock_pw_client_on_state.run_script.assert_called_once_with(script.id, device.identifier, payload["parameters"])

def test_execute_script_device_offline(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    script = _create_test_script(db, id="exec_script_offline")
    device = _create_test_device(db, identifier="exec_dev_offline", is_online=False)
    db.close()
    payload = {"device_ids": [device.identifier]}
    response = client_with_test_db.post(f"{BASE_API_PATH}/{script.id}/execute", json=payload, headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200 # The overall request is 200, but individual device fails
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["status"] == "error"
    assert "offline" in data["results"][0]["error"]


# GET /scripts/{script_id}/executions/{device_id}
@patch.object(app.state, 'pulseway_client', new_callable=MagicMock)
def test_get_script_executions(mock_pw_client_on_state, client_with_test_db: TestClient):
    script_id = "s1"
    device_id = "d1"
    mock_executions = [{"id": "exec1", "status": "Completed"}, {"id": "exec2", "status": "Running"}]
    mock_pw_client_on_state.get_script_executions.return_value = mock_executions

    response = client_with_test_db.get(f"{BASE_API_PATH}/{script_id}/executions/{device_id}?limit=5&offset=0", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json() == mock_executions
    mock_pw_client_on_state.get_script_executions.assert_called_once_with(script_id, device_id, limit=5, offset=0)

# GET /scripts/{script_id}/executions/{device_id}/{execution_id}
@patch.object(app.state, 'pulseway_client', new_callable=MagicMock)
def test_get_script_execution_details(mock_pw_client_on_state, client_with_test_db: TestClient):
    s_id, d_id, e_id = "s1", "d1", "e1"
    mock_details = {"id": e_id, "status": "Completed", "output": "All good."}
    mock_pw_client_on_state.get_script_execution_details.return_value = mock_details

    response = client_with_test_db.get(f"{BASE_API_PATH}/{s_id}/executions/{d_id}/{e_id}", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    assert response.json() == mock_details
    mock_pw_client_on_state.get_script_execution_details.assert_called_once_with(s_id, d_id, e_id)

# GET /scripts/categories/list
def test_get_script_categories(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_script(db, category_name="Cat A")
    _create_test_script(db, category_name="Cat B")
    _create_test_script(db, category_name="Cat A") # Duplicate
    _create_test_script(db, category_name=None) # No category
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/categories/list", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "Cat A" in data
    assert "Cat B" in data
    assert len(data) == 2 # Unique categories

# GET /scripts/platforms/list
def test_get_script_platforms(client_with_test_db: TestClient):
    response = client_with_test_db.get(f"{BASE_API_PATH}/platforms/list", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    # Based on the current implementation in api/scripts.py
    expected_platforms = ["windows", "linux", "macos", "esxi"]
    assert response.json() == expected_platforms

# POST /scripts/bulk-execute
@patch.object(app.state, 'pulseway_client', new_callable=MagicMock)
def test_bulk_execute_script(mock_pw_client_on_state, client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    script = _create_test_script(db, id="bulk_script_1")
    dev1 = _create_test_device(db, identifier="bulk_dev_1", is_online=True) # Success
    dev2 = _create_test_device(db, identifier="bulk_dev_2", is_online=False) # Offline
    dev3_id = "bulk_dev_non_existent" # Non-existent
    db.close()

    # Mock Pulseway client run_script
    # For dev1 (success):
    mock_pw_client_on_state.run_script.side_effect = lambda s_id, d_id, params: \
        {"success": True, "executionId": f"exec_{d_id}"} if d_id == dev1.identifier else PulsewayAPIError("Simulated API error for other devices")

    payload = {
        "script_id": script.id,
        "device_ids": [dev1.identifier, dev2.identifier, dev3_id],
        "parameters": {"timeout": 30}
    }
    response = client_with_test_db.post(f"{BASE_API_PATH}/bulk-execute", json=payload, headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200 # Endpoint itself succeeds
    data = response.json()

    assert len(data["successful_executions"]) == 1
    assert data["successful_executions"][0]["device_id"] == dev1.identifier
    assert data["successful_executions"][0]["status"] == "success"

    assert len(data["failed_executions"]) == 2
    failed_dev_ids = [item["device_id"] for item in data["failed_executions"]]
    assert dev2.identifier in failed_dev_ids
    assert dev3_id in failed_dev_ids

    # Check error messages
    for item in data["failed_executions"]:
        if item["device_id"] == dev2.identifier:
            assert "offline" in item["error"]
        elif item["device_id"] == dev3_id:
            assert "not found" in item["error"]

    mock_pw_client_on_state.run_script.assert_called_once_with(script.id, dev1.identifier, payload["parameters"])


# GET /scripts/search/{search_term}
def test_search_scripts_by_term(client_with_test_db: TestClient):
    db = app_db.SessionLocal()
    _create_test_script(db, name="Cleanup Script", description="Removes temporary files")
    _create_test_script(db, name="User Management", description="Manage user accounts")
    db.close()

    response = client_with_test_db.get(f"{BASE_API_PATH}/search/cleanup", headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Cleanup Script"

    response_desc = client_with_test_db.get(f"{BASE_API_PATH}/search/accounts", headers={"X-API-Key": TEST_API_KEY})
    assert response_desc.status_code == 200
    data_desc = response_desc.json()
    assert len(data_desc) == 1
    assert data_desc[0]["name"] == "User Management"

    response_none = client_with_test_db.get(f"{BASE_API_PATH}/search/nonexistentterm", headers={"X-API-Key": TEST_API_KEY})
    assert response_none.status_code == 200
    assert response_none.json() == []
