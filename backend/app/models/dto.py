# backend/app/models/dto.py
from pydantic import BaseModel
from typing import Optional, List, TYPE_CHECKING, Dict, Any # Added Any
from datetime import datetime

# Forward reference for type hinting Device in from_entity
# Ensure Device is imported for type hint in from_entity, it's done under TYPE_CHECKING
if TYPE_CHECKING:
    from .database import Device # Assuming Device is in .database
    from .database import Notification as NotificationModel # For TYPE_CHECKING
    from .database import DeviceAsset as DeviceAssetModel # For TYPE_CHECKING

class DeviceFilters(BaseModel):
    organization: Optional[str] = None
    site: Optional[str] = None
    group: Optional[str] = None
    online_only: Optional[bool] = None
    offline_only: Optional[bool] = None
    has_alerts: Optional[bool] = None
    computer_type: Optional[str] = None
    limit: int = 100
    offset: int = 0

class DeviceDTO(BaseModel):
    identifier: str
    name: str
    description: Optional[str] = None
    computer_type: Optional[str] = None
    is_online: bool
    is_agent_installed: bool
    group_name: Optional[str] = None
    site_name: Optional[str] = None
    organization_name: Optional[str] = None
    critical_notifications: int
    elevated_notifications: int
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    last_seen_online: Optional[datetime] = None
    antivirus_enabled: Optional[str] = None # Field from DeviceSummary
    firewall_enabled: Optional[bool] = None # Field from DeviceSummary

    class Config:
        from_attributes = True # Replaces orm_mode = True in Pydantic v2

    @classmethod
    def from_entity(cls, device: 'Device') -> 'DeviceDTO':
        return cls(
            identifier=device.identifier,
            name=device.name,
            description=device.description,
            computer_type=device.computer_type,
            is_online=device.is_online,
            is_agent_installed=device.is_agent_installed,
            group_name=device.group_name,
            site_name=device.site_name,
            organization_name=device.organization_name,
            critical_notifications=device.critical_notifications,
            elevated_notifications=device.elevated_notifications,
            cpu_usage=device.cpu_usage,
            memory_usage=device.memory_usage,
            last_seen_online=device.last_seen_online,
            # Ensure these fields exist on the Device model or handle potential AttributeError
            antivirus_enabled=getattr(device, 'antivirus_enabled', None),
            firewall_enabled=getattr(device, 'firewall_enabled', None)
        )

class DeviceStatsDTO(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    devices_with_agent: int
    devices_without_agent: int
    critical_alerts: int
    elevated_alerts: int
    devices_by_organization: Dict[str, int]
    devices_by_site: Dict[str, int]
    devices_by_type: Dict[str, int]

class DeviceDetailDTO(BaseModel):
    identifier: str
    name: str
    description: Optional[str] = None
    computer_type: Optional[str] = None
    is_online: bool
    is_agent_installed: bool
    group_name: Optional[str] = None
    site_name: Optional[str] = None
    organization_name: Optional[str] = None
    critical_notifications: int
    elevated_notifications: int
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    last_seen_online: Optional[datetime] = None
    antivirus_enabled: Optional[str] = None
    firewall_enabled: Optional[bool] = None
    # Fields specific to DeviceDetail
    in_maintenance: bool
    external_ip_address: Optional[str] = None
    local_ip_addresses: Optional[List[Dict[str, Any]]] = None # Adjusted type hint
    uptime: Optional[str] = None
    client_version: Optional[str] = None
    memory_total: Optional[int] = None # Changed from float to int based on typical data
    antivirus_up_to_date: Optional[str] = None
    uac_enabled: Optional[bool] = None
    normal_notifications: int
    low_notifications: int
    event_logs: Optional[Dict[str, Any]] = None # Adjusted type hint
    updates: Optional[Dict[str, Any]] = None # Adjusted type hint

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, device: 'Device') -> 'DeviceDetailDTO': # Ensure Device is imported for type hint
        # This method will map all fields from the Device SQLAlchemy model
        # to the DTO. For fields not directly on Device, they might come from
        # related models or might need to be set to None/default if not applicable.
        return cls(
            identifier=device.identifier,
            name=device.name,
            description=device.description,
            computer_type=device.computer_type,
            is_online=device.is_online,
            is_agent_installed=device.is_agent_installed,
            group_name=device.group_name,
            site_name=device.site_name,
            organization_name=device.organization_name,
            critical_notifications=device.critical_notifications,
            elevated_notifications=device.elevated_notifications,
            cpu_usage=device.cpu_usage,
            memory_usage=device.memory_usage,
            last_seen_online=device.last_seen_online,
            antivirus_enabled=getattr(device, 'antivirus_enabled', None),
            firewall_enabled=getattr(device, 'firewall_enabled', None),
            in_maintenance=device.in_maintenance,
            external_ip_address=device.external_ip_address,
            local_ip_addresses=device.local_ip_addresses,
            uptime=device.uptime,
            client_version=device.client_version,
            memory_total=device.memory_total,
            antivirus_up_to_date=getattr(device, 'antivirus_up_to_date', None),
            uac_enabled=getattr(device, 'uac_enabled', None),
            normal_notifications=device.normal_notifications,
            low_notifications=device.low_notifications,
            event_logs=device.event_logs,
            updates=device.updates
        )

class NotificationDTO(BaseModel):
    id: str # Corrected to str based on model
    message: str
    datetime: Optional[datetime] = None
    priority: str
    read: bool
    device_identifier: str # Added from model

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, notification: 'NotificationModel') -> 'NotificationDTO':
        return cls(
            id=notification.id,
            message=notification.message,
            datetime=notification.datetime,
            priority=notification.priority,
            read=notification.read,
            device_identifier=notification.device_identifier
        )

class DeviceAssetDTO(BaseModel):
    device_identifier: str
    tags: Optional[List[str]] = None
    asset_info: Optional[Dict[str, Any]] = None
    public_ip_address: Optional[str] = None
    ip_addresses: Optional[List[Dict[str, Any]]] = None
    disks: Optional[List[Dict[str, Any]]] = None
    installed_software: Optional[List[Dict[str, Any]]] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_entity(cls, asset: 'DeviceAssetModel') -> 'DeviceAssetDTO':
        return cls(
            device_identifier=asset.device_identifier,
            tags=asset.tags,
            asset_info=asset.asset_info,
            public_ip_address=asset.public_ip_address,
            ip_addresses=asset.ip_addresses,
            disks=asset.disks,
            installed_software=asset.installed_software,
            updated_at=asset.updated_at
        )
