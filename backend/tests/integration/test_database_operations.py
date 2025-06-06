import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone

# Assuming Device, Organization, Site, Group, Base are in backend.app.models.database
# Adjust imports based on actual project structure
from backend.app.models.database import Base, Device, Organization, Site, Group, Notification, DeviceAsset
# Using database.py for Base and engine setup logic is also an option, but for tests,
# it's often clearer to define a separate test engine and session.
# from backend.app.database import Base # If Base is exposed there

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} # Needed for SQLite
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Pytest fixture to set up a test database session.
    Creates all tables before each test and drops them afterwards.
    """
    # Ensure all tables are created
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables to ensure a clean state for the next test
        Base.metadata.drop_all(bind=engine)

# --- Device Model Tests ---

def test_create_and_read_device(db_session: Session):
    """Test creating a new device and reading it back."""
    initial_device_data = {
        "identifier": "test_device_001",
        "name": "Integration Test Device",
        "description": "A device for integration testing",
        "computer_type": "Server",
        "is_online": True,
        "is_agent_installed": True,
        "organization_name": "Test Org A",
        "site_name": "Test Site A",
        "group_name": "Test Group A",
        "external_ip_address": "192.0.2.1",
        "client_version": "1.0.0",
        "cpu_usage": 50.5,
        "memory_usage": 60.2,
        "memory_total": 16384,
        "last_seen_online": datetime.now(timezone.utc)
    }
    new_device = Device(**initial_device_data)

    db_session.add(new_device)
    db_session.commit()
    db_session.refresh(new_device)

    retrieved_device = db_session.query(Device).filter(Device.identifier == "test_device_001").first()

    assert retrieved_device is not None
    assert retrieved_device.identifier == initial_device_data["identifier"]
    assert retrieved_device.name == initial_device_data["name"]
    assert retrieved_device.description == initial_device_data["description"]
    assert retrieved_device.computer_type == initial_device_data["computer_type"]
    assert retrieved_device.is_online == initial_device_data["is_online"]
    assert retrieved_device.is_agent_installed == initial_device_data["is_agent_installed"]
    assert retrieved_device.organization_name == initial_device_data["organization_name"]
    assert retrieved_device.site_name == initial_device_data["site_name"]
    assert retrieved_device.group_name == initial_device_data["group_name"]
    assert retrieved_device.external_ip_address == initial_device_data["external_ip_address"]
    assert retrieved_device.client_version == initial_device_data["client_version"]
    assert retrieved_device.cpu_usage == initial_device_data["cpu_usage"]
    assert retrieved_device.memory_usage == initial_device_data["memory_usage"]
    assert retrieved_device.memory_total == initial_device_data["memory_total"]
    assert retrieved_device.last_seen_online.replace(microsecond=0) == initial_device_data["last_seen_online"].replace(microsecond=0) # Compare without microseconds for safety with DB precision
    assert retrieved_device.created_at is not None
    assert retrieved_device.updated_at is not None

def test_update_device(db_session: Session):
    """Test updating an existing device's attributes."""
    # First, create a device to update
    device_to_update_data = {
        "identifier": "update_device_002",
        "name": "Device Before Update",
        "organization_name": "Old Org",
        "cpu_usage": 30.0
    }
    device = Device(**device_to_update_data)
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    # Retrieve the device
    retrieved_device = db_session.query(Device).filter(Device.identifier == "update_device_002").first()
    assert retrieved_device is not None

    # Modify attributes
    retrieved_device.name = "Device After Update"
    retrieved_device.organization_name = "New Org"
    retrieved_device.is_online = True
    retrieved_device.cpu_usage = 75.5
    original_updated_at = retrieved_device.updated_at # Keep track for comparison

    db_session.commit()
    db_session.refresh(retrieved_device)

    # Query again and assert updates
    updated_device = db_session.query(Device).filter(Device.identifier == "update_device_002").first()
    assert updated_device is not None
    assert updated_device.name == "Device After Update"
    assert updated_device.organization_name == "New Org"
    assert updated_device.is_online is True
    assert updated_device.cpu_usage == 75.5
    # Check if updated_at was actually updated (may depend on onupdate=func.now() behavior and if other fields changed)
    if original_updated_at:
         assert updated_device.updated_at > original_updated_at
    else:
        assert updated_device.updated_at is not None


def test_delete_device(db_session: Session):
    """Test deleting a device."""
    # Create a device to delete
    device_to_delete_data = {"identifier": "delete_device_003", "name": "To Be Deleted"}
    device = Device(**device_to_delete_data)
    db_session.add(device)
    db_session.commit()
    db_session.refresh(device)

    # Retrieve to ensure it exists
    retrieved_device = db_session.query(Device).filter(Device.identifier == "delete_device_003").first()
    assert retrieved_device is not None

    # Delete the device
    db_session.delete(retrieved_device)
    db_session.commit()

    # Attempt to query again
    deleted_device = db_session.query(Device).filter(Device.identifier == "delete_device_003").first()
    assert deleted_device is None

def test_device_identifier_unique_constraint(db_session: Session):
    """Test that the identifier field has a unique constraint."""
    device1_data = {"identifier": "unique_id_001", "name": "Device 1"}
    device1 = Device(**device1_data)
    db_session.add(device1)
    db_session.commit()

    device2_data = {"identifier": "unique_id_001", "name": "Device 2 with same ID"}
    device2 = Device(**device2_data)
    db_session.add(device2)

    with pytest.raises(IntegrityError): # SQLAlchemy raises IntegrityError for unique constraint violations
        db_session.commit()

# Placeholder for simple relationship tests - can be expanded later.
# For now, we'll focus on Device model's direct fields.
# If Device had a mandatory, simple FK relationship that's easy to mock or create,
# we could add it here. For example, if 'organization_id' was non-nullable and
# we had an Organization model:
#
# def test_device_with_organization_relationship(db_session: Session):
#     # Create a dummy organization
#     test_org = Organization(name="Test Org For Device Relation")
#     db_session.add(test_org)
#     db_session.commit()
#     db_session.refresh(test_org)
#
#     device_with_org_data = {
#         "identifier": "device_with_org_001",
#         "name": "Device Linked to Org",
#         "organization_id": test_org.id, # Assuming direct ID assignment
#         "organization_name": test_org.name # And also storing name
#     }
#     new_device = Device(**device_with_org_data)
#     db_session.add(new_device)
#     db_session.commit()
#     db_session.refresh(new_device)
#
#     retrieved_device = db_session.query(Device).filter(Device.identifier == "device_with_org_001").first()
#     assert retrieved_device is not None
#     assert retrieved_device.organization_id == test_org.id
#     assert retrieved_device.organization.id == test_org.id # If relationship is set up for back-population
#     assert retrieved_device.organization.name == "Test Org For Device Relation"

# Add more tests for other constraints or specific field behaviors if necessary.
# For example, testing default values, nullable fields, etc.
# For now, the CRUD operations cover the primary requirements.


# --- Notification Model Tests ---

def test_create_read_notification(db_session: Session):
    """Test creating a Notification and reading it back, including device relationship."""
    # 1. Create a parent Device
    parent_device = Device(identifier="dev_for_notif_001", name="Device with Notifications")
    db_session.add(parent_device)
    db_session.commit()
    db_session.refresh(parent_device)

    # 2. Create Notification
    notification_data = {
        "message": "Critical alert: CPU temperature high!",
        "datetime": datetime.now(timezone.utc),
        "priority": "critical",
        "read": False,
        "device_identifier": parent_device.identifier
    }
    new_notification = Notification(**notification_data)
    db_session.add(new_notification)
    db_session.commit()
    db_session.refresh(new_notification)

    # 3. Query Notification back
    retrieved_notification = db_session.query(Notification).filter(Notification.id == new_notification.id).first()
    assert retrieved_notification is not None
    assert retrieved_notification.message == notification_data["message"]
    assert retrieved_notification.priority == notification_data["priority"]
    assert retrieved_notification.device_identifier == parent_device.identifier
    assert retrieved_notification.created_at is not None

    # 4. Check relationship from Device side
    db_session.refresh(parent_device) # Refresh to load the relationship
    assert len(parent_device.notifications) == 1
    assert parent_device.notifications[0].id == new_notification.id
    assert parent_device.notifications[0].message == notification_data["message"]

def test_update_notification(db_session: Session):
    """Test updating an existing Notification."""
    parent_device = Device(identifier="dev_for_notif_update_001", name="Device for Notif Update")
    db_session.add(parent_device)
    db_session.commit()

    notification = Notification(
        message="Initial message",
        priority="normal",
        device_identifier=parent_device.identifier,
        datetime=datetime.now(timezone.utc)
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)

    retrieved_notification = db_session.query(Notification).filter(Notification.id == notification.id).first()
    assert retrieved_notification is not None

    retrieved_notification.message = "Updated message for notification"
    retrieved_notification.read = True
    retrieved_notification.priority = "high"
    db_session.commit()
    db_session.refresh(retrieved_notification)

    updated_notification = db_session.query(Notification).filter(Notification.id == notification.id).first()
    assert updated_notification.message == "Updated message for notification"
    assert updated_notification.read is True
    assert updated_notification.priority == "high"

def test_delete_notification(db_session: Session):
    """Test deleting a Notification without deleting the parent Device."""
    parent_device = Device(identifier="dev_for_notif_delete_001", name="Device for Notif Delete")
    db_session.add(parent_device)
    db_session.commit()

    notification = Notification(
        message="To be deleted",
        priority="low",
        device_identifier=parent_device.identifier,
        datetime=datetime.now(timezone.utc)
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    notification_id = notification.id

    db_session.delete(notification)
    db_session.commit()

    assert db_session.query(Notification).filter(Notification.id == notification_id).first() is None
    # Verify parent device still exists
    assert db_session.query(Device).filter(Device.identifier == parent_device.identifier).first() is not None


def test_delete_device_cascades_to_notifications(db_session: Session):
    """Test that deleting a Device also deletes its associated Notifications due to CASCADE."""
    parent_device = Device(identifier="dev_cascade_delete_notif_001", name="Device Cascade Notif")
    db_session.add(parent_device)
    db_session.commit()

    notif1 = Notification(device_identifier=parent_device.identifier, message="N1", datetime=datetime.now(timezone.utc))
    notif2 = Notification(device_identifier=parent_device.identifier, message="N2", datetime=datetime.now(timezone.utc))
    db_session.add_all([notif1, notif2])
    db_session.commit()
    notif1_id = notif1.id
    notif2_id = notif2.id
    device_id = parent_device.identifier

    db_session.delete(parent_device)
    db_session.commit()

    assert db_session.query(Device).filter(Device.identifier == device_id).first() is None
    assert db_session.query(Notification).filter(Notification.id == notif1_id).first() is None
    assert db_session.query(Notification).filter(Notification.id == notif2_id).first() is None


# --- DeviceAsset Model Tests ---

def test_create_read_device_asset(db_session: Session):
    """Test creating a DeviceAsset and reading it back, including device relationship."""
    parent_device = Device(identifier="dev_for_asset_001", name="Device with Asset")
    db_session.add(parent_device)
    db_session.commit()
    db_session.refresh(parent_device)

    asset_data = {
        "device_identifier": parent_device.identifier,
        "tags": ["server", "production"],
        "asset_info": {"os": "Linux", "kernel": "5.4.0"},
        "public_ip_address": "203.0.113.45",
    }
    new_asset = DeviceAsset(**asset_data)
    db_session.add(new_asset)
    db_session.commit()
    db_session.refresh(new_asset)

    retrieved_asset = db_session.query(DeviceAsset).filter(DeviceAsset.id == new_asset.id).first()
    assert retrieved_asset is not None
    assert retrieved_asset.device_identifier == parent_device.identifier
    assert retrieved_asset.tags == ["server", "production"]
    assert retrieved_asset.asset_info["os"] == "Linux"
    assert retrieved_asset.public_ip_address == "203.0.113.45"

    # Check relationship from Device side (asset_info is one-to-one)
    db_session.refresh(parent_device)
    assert parent_device.asset_info is not None
    assert parent_device.asset_info.id == new_asset.id
    assert parent_device.asset_info.tags == ["server", "production"]

def test_update_device_asset(db_session: Session):
    """Test updating an existing DeviceAsset."""
    parent_device = Device(identifier="dev_for_asset_update_001", name="Device for Asset Update")
    db_session.add(parent_device)
    db_session.commit()

    asset = DeviceAsset(
        device_identifier=parent_device.identifier,
        asset_info={"model": "PowerEdge R740"},
        tags=["initial_tag"]
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    retrieved_asset = db_session.query(DeviceAsset).filter(DeviceAsset.id == asset.id).first()
    assert retrieved_asset is not None

    retrieved_asset.asset_info = {"model": "PowerEdge R750", "cpu": "Intel Xeon Gold"}
    retrieved_asset.tags = ["updated_tag", "critical"]
    db_session.commit()
    db_session.refresh(retrieved_asset)

    updated_asset = db_session.query(DeviceAsset).filter(DeviceAsset.id == asset.id).first()
    assert updated_asset.asset_info["model"] == "PowerEdge R750"
    assert updated_asset.asset_info["cpu"] == "Intel Xeon Gold"
    assert updated_asset.tags == ["updated_tag", "critical"]

def test_delete_device_asset(db_session: Session):
    """Test deleting a DeviceAsset without deleting the parent Device."""
    parent_device = Device(identifier="dev_for_asset_delete_001", name="Device for Asset Delete")
    db_session.add(parent_device)
    db_session.commit()

    asset = DeviceAsset(device_identifier=parent_device.identifier, asset_info={"disk": "1TB SSD"})
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    asset_id = asset.id

    db_session.delete(asset)
    db_session.commit()

    assert db_session.query(DeviceAsset).filter(DeviceAsset.id == asset_id).first() is None
    assert db_session.query(Device).filter(Device.identifier == parent_device.identifier).first() is not None

def test_device_asset_multiple_for_one_device(db_session: Session):
    """
    Test behavior of creating multiple DeviceAsset entries for one Device.
    Given the current schema (no unique constraint on DeviceAsset.device_identifier)
    and `uselist=False` on Device.asset_info, this will test that multiple can be added,
    but the relationship on Device might only pick one.
    A true DB-level one-to-one would require a unique constraint on DeviceAsset.device_identifier.
    """
    parent_device = Device(identifier="dev_multi_asset_001", name="Device Multi Asset")
    db_session.add(parent_device)
    db_session.commit()

    asset1_data = {"device_identifier": parent_device.identifier, "asset_info": {"type": "Primary Asset"}}
    asset1 = DeviceAsset(**asset1_data)
    db_session.add(asset1)
    db_session.commit()

    # Attempt to create a second asset for the same device
    asset2_data = {"device_identifier": parent_device.identifier, "asset_info": {"type": "Secondary Asset"}}
    asset2 = DeviceAsset(**asset2_data)
    db_session.add(asset2)

    # This should NOT raise an IntegrityError with the current schema, as there's no unique constraint
    # on DeviceAsset.device_identifier. If there was, an IntegrityError would be expected here.
    db_session.commit()

    count = db_session.query(DeviceAsset).filter(DeviceAsset.device_identifier == parent_device.identifier).count()
    assert count == 2

    # Check what device.asset_info returns (uselist=False means it should be one item)
    db_session.refresh(parent_device)
    assert parent_device.asset_info is not None
    # Which one it picks might be database/ORM dependent without explicit ordering on the relationship
    assert parent_device.asset_info.asset_info["type"] in ["Primary Asset", "Secondary Asset"]


def test_delete_device_cascades_to_device_asset(db_session: Session):
    """Test that deleting a Device also deletes its associated DeviceAsset due to CASCADE."""
    parent_device = Device(identifier="dev_cascade_delete_asset_001", name="Device Cascade Asset")
    db_session.add(parent_device)
    db_session.commit()

    asset = DeviceAsset(device_identifier=parent_device.identifier, asset_info={"data": "some asset data"})
    db_session.add(asset)
    db_session.commit()
    asset_id = asset.id
    device_id = parent_device.identifier

    db_session.delete(parent_device)
    db_session.commit()

    assert db_session.query(Device).filter(Device.identifier == device_id).first() is None
    assert db_session.query(DeviceAsset).filter(DeviceAsset.id == asset_id).first() is None


# To run these tests (assuming pytest is installed):
# Navigate to the root directory of the project in the terminal
# Run: pytest backend/tests/integration/test_database_operations.py
