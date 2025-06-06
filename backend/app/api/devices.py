# app/api/devices.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from ..database import SessionLocal
from ..models.database import Device, DeviceAsset, Notification, Organization, Site, Group
from ..pulseway.client import PulsewayClient
from pydantic import BaseModel
from datetime import datetime
from ..security import get_current_active_api_key

router = APIRouter(dependencies=[Depends(get_current_active_api_key)])

# Pydantic models for API responses
class DeviceSummary(BaseModel):
    identifier: str
    name: str
    description: Optional[str]
    computer_type: Optional[str]
    is_online: bool
    is_agent_installed: bool
    group_name: Optional[str]
    site_name: Optional[str]
    organization_name: Optional[str]
    critical_notifications: int
    elevated_notifications: int
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    last_seen_online: Optional[datetime]
    antivirus_enabled: Optional[str]
    firewall_enabled: Optional[bool]
    
    class Config:
        from_attributes = True

class DeviceDetail(DeviceSummary):
    in_maintenance: bool
    external_ip_address: Optional[str]
    local_ip_addresses: Optional[List[Dict]]
    uptime: Optional[str]
    client_version: Optional[str]
    memory_total: Optional[int]
    antivirus_up_to_date: Optional[str]
    uac_enabled: Optional[bool]
    normal_notifications: int
    low_notifications: int
    event_logs: Optional[Dict]
    updates: Optional[Dict]
    
    class Config:
        from_attributes = True

class DeviceStats(BaseModel):
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

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get Pulseway client from app state
def get_pulseway_client(request: Request) -> PulsewayClient:
    # This will be injected from main.py
    return request.app.state.pulseway_client

@router.get("/", response_model=List[DeviceSummary])
async def get_devices(
    db: Session = Depends(get_db),
    organization: Optional[str] = Query(None, description="Filter by organization name"),
    site: Optional[str] = Query(None, description="Filter by site name"),
    group: Optional[str] = Query(None, description="Filter by group name"),
    online_only: Optional[bool] = Query(None, description="Show only online devices"),
    offline_only: Optional[bool] = Query(None, description="Show only offline devices"),
    has_alerts: Optional[bool] = Query(None, description="Show only devices with alerts"),
    computer_type: Optional[str] = Query(None, description="Filter by computer type"),
    limit: int = Query(100, le=500, description="Maximum number of devices to return"),
    offset: int = Query(0, ge=0, description="Number of devices to skip")
):
    """Get list of devices with optional filtering"""
    
    query = db.query(Device)
    
    # Apply filters
    if organization:
        query = query.filter(Device.organization_name.ilike(f"%{organization}%"))
    
    if site:
        query = query.filter(Device.site_name.ilike(f"%{site}%"))
    
    if group:
        query = query.filter(Device.group_name.ilike(f"%{group}%"))
    
    if online_only is not None:
        query = query.filter(Device.is_online == online_only)
    
    if offline_only is not None:
        query = query.filter(Device.is_online == (not offline_only))
    
    if has_alerts:
        query = query.filter(
            (Device.critical_notifications > 0) | 
            (Device.elevated_notifications > 0)
        )
    
    if computer_type:
        query = query.filter(Device.computer_type.ilike(f"%{computer_type}%"))
    
    # Apply pagination
    devices = query.offset(offset).limit(limit).all()
    
    return devices

@router.get("/stats", response_model=DeviceStats)
async def get_device_stats(db: Session = Depends(get_db)):
    """Get device statistics and counts"""
    
    # Basic counts
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.is_online == True).count()
    offline_devices = total_devices - online_devices
    devices_with_agent = db.query(Device).filter(Device.is_agent_installed == True).count()
    devices_without_agent = total_devices - devices_with_agent
    
    # Alert counts
    critical_alerts = db.query(Device).filter(Device.critical_notifications > 0).count()
    elevated_alerts = db.query(Device).filter(Device.elevated_notifications > 0).count()
    
    # Devices by organization
    org_stats = db.query(
        Device.organization_name, 
        db.func.count(Device.identifier)
    ).group_by(Device.organization_name).all()
    devices_by_organization = {org or "Unknown": count for org, count in org_stats}
    
    # Devices by site
    site_stats = db.query(
        Device.site_name, 
        db.func.count(Device.identifier)
    ).group_by(Device.site_name).all()
    devices_by_site = {site or "Unknown": count for site, count in site_stats}
    
    # Devices by type
    type_stats = db.query(
        Device.computer_type, 
        db.func.count(Device.identifier)
    ).group_by(Device.computer_type).all()
    devices_by_type = {comp_type or "Unknown": count for comp_type, count in type_stats}
    
    return DeviceStats(
        total_devices=total_devices,
        online_devices=online_devices,
        offline_devices=offline_devices,
        devices_with_agent=devices_with_agent,
        devices_without_agent=devices_without_agent,
        critical_alerts=critical_alerts,
        elevated_alerts=elevated_alerts,
        devices_by_organization=devices_by_organization,
        devices_by_site=devices_by_site,
        devices_by_type=devices_by_type
    )

@router.get("/{device_id}", response_model=DeviceDetail)
async def get_device(device_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific device"""
    
    device = db.query(Device).filter(Device.identifier == device_id).first()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device

@router.get("/{device_id}/notifications")
async def get_device_notifications(
    device_id: str, 
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """Get notifications for a specific device"""
    
    # Check if device exists
    device = db.query(Device).filter(Device.identifier == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    notifications = db.query(Notification).filter(
        Notification.device_identifier == device_id
    ).order_by(Notification.datetime.desc()).offset(offset).limit(limit).all()
    
    return notifications

@router.get("/{device_id}/assets")
async def get_device_assets(device_id: str, db: Session = Depends(get_db)):
    """Get asset information for a specific device"""
    
    # Check if device exists
    device = db.query(Device).filter(Device.identifier == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    assets = db.query(DeviceAsset).filter(
        DeviceAsset.device_identifier == device_id
    ).first()
    
    if not assets:
        raise HTTPException(status_code=404, detail="Assets not found for this device")
    
    return {
        "device_identifier": assets.device_identifier,
        "tags": assets.tags,
        "asset_info": assets.asset_info,
        "public_ip_address": assets.public_ip_address,
        "ip_addresses": assets.ip_addresses,
        "disks": assets.disks,
        "installed_software": assets.installed_software,
        "updated_at": assets.updated_at
    }

@router.post("/{device_id}/refresh")
async def refresh_device_data(
    device_id: str, 
    db: Session = Depends(get_db),
    pulseway_client: PulsewayClient = Depends(get_pulseway_client)
):
    """Refresh data for a specific device from Pulseway API"""
    
    try:
        # Get fresh device data from API
        device_response = pulseway_client.get_device(device_id)
        device_data = device_response.get('Data', {})
        
        if not device_data:
            raise HTTPException(status_code=404, detail="Device not found in Pulseway")
        
        # Update device in database
        device = db.query(Device).filter(Device.identifier == device_id).first()
        
        if device:
            # Update existing device
            device.name = device_data.get('Name', device.name)
            device.description = device_data.get('Description', device.description)
            device.is_online = device_data.get('IsOnline', device.is_online)
            device.uptime = device_data.get('Uptime', device.uptime)
            device.cpu_usage = device_data.get('CpuUsage', device.cpu_usage)
            device.memory_usage = device_data.get('MemoryUsage', device.memory_usage)
            device.critical_notifications = device_data.get('CriticalNotifications', device.critical_notifications)
            device.elevated_notifications = device_data.get('ElevatedNotifications', device.elevated_notifications)
            device.normal_notifications = device_data.get('NormalNotifications', device.normal_notifications)
            device.low_notifications = device_data.get('LowNotifications', device.low_notifications)
            device.updated_at = datetime.now()
            
            db.commit()
            
            return {"status": "success", "message": "Device data refreshed"}
        else:
            raise HTTPException(status_code=404, detail="Device not found in local database")
            
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to refresh device data: {str(e)}")

@router.get("/search/{search_term}")
async def search_devices(
    search_term: str,
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100)
):
    """Search devices by name, description, or IP address"""
    
    # Search in multiple fields
    devices = db.query(Device).filter(
        (Device.name.ilike(f"%{search_term}%")) |
        (Device.description.ilike(f"%{search_term}%")) |
        (Device.external_ip_address.ilike(f"%{search_term}%"))
    ).limit(limit).all()
    
    return devices

@router.get("/organization/{org_name}")
async def get_devices_by_organization(
    org_name: str,
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get all devices for a specific organization"""
    
    devices = db.query(Device).filter(
        Device.organization_name.ilike(f"%{org_name}%")
    ).offset(offset).limit(limit).all()
    
    return devices

@router.get("/site/{site_name}")
async def get_devices_by_site(
    site_name: str,
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get all devices for a specific site"""
    
    devices = db.query(Device).filter(
        Device.site_name.ilike(f"%{site_name}%")
    ).offset(offset).limit(limit).all()
    
    return devices

@router.get("/alerts/critical")
async def get_devices_with_critical_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200)
):
    """Get devices with critical alerts"""
    
    devices = db.query(Device).filter(
        Device.critical_notifications > 0
    ).order_by(Device.critical_notifications.desc()).limit(limit).all()
    
    return devices

@router.get("/alerts/elevated")
async def get_devices_with_elevated_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200)
):
    """Get devices with elevated alerts"""
    
    devices = db.query(Device).filter(
        Device.elevated_notifications > 0
    ).order_by(Device.elevated_notifications.desc()).limit(limit).all()
    
    return devices

@router.get("/status/offline")
async def get_offline_devices(
    db: Session = Depends(get_db),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get all offline devices"""
    
    devices = db.query(Device).filter(
        Device.is_online == False
    ).order_by(Device.last_seen_online.desc()).offset(offset).limit(limit).all()
    
    return devices