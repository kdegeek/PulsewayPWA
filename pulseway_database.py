# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - SQLite for simplicity and portability
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pulseway.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# app/models/database.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    has_custom_fields = Column(Boolean, default=False)
    psa_mapping_id = Column(Integer, nullable=True)
    psa_mapping_type = Column(String, nullable=True)
    
    # Relationships
    sites = relationship("Site", back_populates="organization")
    devices = relationship("Device", back_populates="organization")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Site(Base):
    __tablename__ = "sites"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_id = Column(Integer, ForeignKey("organizations.id"))
    parent_name = Column(String)
    has_custom_fields = Column(Boolean, default=False)
    psa_mapping_id = Column(Integer, nullable=True)
    psa_integration_type = Column(String, nullable=True)
    contact_info = Column(JSON, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="sites")
    groups = relationship("Group", back_populates="site")
    devices = relationship("Device", back_populates="site")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    parent_site_id = Column(Integer, ForeignKey("sites.id"))
    parent_site_name = Column(String)
    parent_organization_id = Column(Integer)
    parent_organization_name = Column(String)
    notes = Column(Text, nullable=True)
    has_custom_fields = Column(Boolean, default=False)
    psa_mapping_id = Column(Integer, nullable=True)
    psa_mapping_type = Column(String, nullable=True)
    
    # Relationships
    site = relationship("Site", back_populates="groups")
    devices = relationship("Device", back_populates="group")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Device(Base):
    __tablename__ = "devices"
    
    identifier = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    computer_type = Column(String, nullable=True)
    is_online = Column(Boolean, default=False)
    is_agent_installed = Column(Boolean, default=False)
    is_mdm_enrolled = Column(Boolean, default=False)
    in_maintenance = Column(Boolean, default=False)
    
    # Network information
    external_ip_address = Column(String, nullable=True)
    local_ip_addresses = Column(JSON, nullable=True)
    
    # System information
    uptime = Column(String, nullable=True)
    client_version = Column(String, nullable=True)
    cpu_usage = Column(Float, nullable=True)
    memory_usage = Column(Float, nullable=True)
    memory_total = Column(Integer, nullable=True)
    
    # Security status
    firewall_enabled = Column(Boolean, nullable=True)
    antivirus_enabled = Column(String, nullable=True)
    antivirus_up_to_date = Column(String, nullable=True)
    uac_enabled = Column(Boolean, nullable=True)
    
    # Notifications count
    critical_notifications = Column(Integer, default=0)
    elevated_notifications = Column(Integer, default=0)
    normal_notifications = Column(Integer, default=0)
    low_notifications = Column(Integer, default=0)
    
    # Event logs
    event_logs = Column(JSON, nullable=True)
    
    # Updates
    updates = Column(JSON, nullable=True)
    
    # Relationships
    group_id = Column(Integer, ForeignKey("groups.id"))
    group_name = Column(String)
    site_id = Column(Integer, ForeignKey("sites.id"))
    site_name = Column(String)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    organization_name = Column(String)
    
    group = relationship("Group", back_populates="devices")
    site = relationship("Site", back_populates="devices")
    organization = relationship("Organization", back_populates="devices")
    
    notifications = relationship("Notification", back_populates="device")
    asset_info = relationship("DeviceAsset", back_populates="device", uselist=False)
    
    # Timestamps
    last_seen_online = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class DeviceAsset(Base):
    __tablename__ = "device_assets"
    
    id = Column(Integer, primary_key=True, index=True)
    device_identifier = Column(String, ForeignKey("devices.identifier"))
    
    # Asset information
    tags = Column(JSON, nullable=True)
    asset_info = Column(JSON, nullable=True)  # System, BIOS, OS info
    public_ip_address = Column(String, nullable=True)
    ip_addresses = Column(JSON, nullable=True)
    disks = Column(JSON, nullable=True)
    installed_software = Column(JSON, nullable=True)
    
    # Relationships
    device = relationship("Device", back_populates="asset_info")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    message = Column(Text)
    datetime = Column(DateTime(timezone=True))
    priority = Column(String, index=True)
    read = Column(Boolean, default=False)
    
    # Device relationship
    device_identifier = Column(String, ForeignKey("devices.identifier"), nullable=True)
    device = relationship("Device", back_populates="notifications")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Script(Base):
    __tablename__ = "scripts"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, nullable=True)
    category_name = Column(String, nullable=True)
    platforms = Column(JSON, nullable=True)
    created_by = Column(String, nullable=True)
    is_built_in = Column(Boolean, default=False)
    
    # Script details
    input_variables = Column(JSON, nullable=True)
    output_variables = Column(JSON, nullable=True)
    script_items = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    scope_id = Column(Integer, nullable=True)
    scope_name = Column(String, nullable=True)
    is_scheduled = Column(Boolean, default=False)
    total_scripts = Column(Integer, default=0)
    is_built_in = Column(Boolean, default=False)
    continue_on_error = Column(Boolean, default=False)
    execution_state = Column(String, default="Idle")
    
    # Timestamps
    task_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    trigger_type = Column(String, nullable=True)
    trigger_sub_type = Column(String, nullable=True)
    context_type = Column(String, nullable=True)
    context_item_id = Column(String, nullable=True)
    
    # Timestamps
    workflow_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())