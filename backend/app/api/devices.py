# app/api/devices.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session # removed joinedload, not used after refactor
from typing import List, Optional, Dict, Any
from ..database import SessionLocal
from ..models.database import Device, DeviceAsset, Notification, Organization, Site, Group # Keep other models
from ..pulseway.client import PulsewayClient
# BaseModel import removed as DeviceDetail is now a DTO
from datetime import datetime # Keep for DeviceDetail and other parts
from ..security import get_current_active_api_key
from ..models.dto import DeviceDTO, DeviceFilters, DeviceStatsDTO, DeviceDetailDTO, NotificationDTO, DeviceAssetDTO # Added NotificationDTO, DeviceAssetDTO
from ..services.device_service import DeviceService # Added

router = APIRouter(dependencies=[Depends(get_current_active_api_key)])

# Pydantic models for API responses
# DeviceSummary class removed
# DeviceDetail class removed (moved to dto.py)
# Removed DeviceStats class definition

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

# Dependency to get DeviceService
def get_device_service(db: Session = Depends(get_db), pulseway_client: PulsewayClient = Depends(get_pulseway_client)) -> DeviceService:
    return DeviceService(db=db, pulseway_client=pulseway_client)

@router.get("/", response_model=List[DeviceDTO])
async def get_devices(
    filters: DeviceFilters = Depends(),
    service: DeviceService = Depends(get_device_service)
):
    """Get list of devices with optional filtering"""
    devices_db = service.get_devices_with_filters(filters)
    return [DeviceDTO.from_entity(device) for device in devices_db]

@router.get("/stats", response_model=DeviceStatsDTO) # Updated response_model
async def get_device_stats(service: DeviceService = Depends(get_device_service)): # Inject service
    """Get device statistics and counts"""
    stats_data = service.get_device_statistics()
    return DeviceStatsDTO(**stats_data)

@router.get("/{device_id}", response_model=DeviceDetailDTO) # Updated response_model
async def get_device(
    device_id: str,
    service: DeviceService = Depends(get_device_service) # Inject service
):
    """Get detailed information about a specific device"""
    device_db = service.get_device_details(device_id)
    
    if not device_db:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return DeviceDetailDTO.from_entity(device_db)

@router.post("/{device_id}/refresh", response_model=Dict[str, str]) # Updated response_model
async def refresh_device_data(
    device_id: str,
    service: DeviceService = Depends(get_device_service) # Inject service
):
    """Refresh data for a specific device from Pulseway API"""
    
    result = service.refresh_single_device_data(device_id)
    
    if result["status"] == "error":
        # Determine appropriate status code based on message if needed
        # For now, using 404 for "not found" and 500 for others
        if "not found in Pulseway" in result["message"] or "not found in local database" in result["message"]:
            raise HTTPException(status_code=404, detail=result["message"])
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    
    return {"status": "success", "message": result["message"]} # Or simply return result

@router.get("/{device_id}/notifications", response_model=List[NotificationDTO])
async def get_device_notifications(
    device_id: str, 
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """Get notifications for a specific device"""
    try:
        notifications_db = service.get_notifications_for_device(device_id, limit, offset)
        return [NotificationDTO.from_entity(n) for n in notifications_db]
    except ValueError as e: # Catch specific error from service
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{device_id}/assets", response_model=DeviceAssetDTO)
async def get_device_assets(
    device_id: str, 
    service: DeviceService = Depends(get_device_service) # Inject service
):
    """Get asset information for a specific device"""
    try:
        asset_db = service.get_assets_for_device(device_id)
        return DeviceAssetDTO.from_entity(asset_db)
    except ValueError as e: # Catch specific error from service
         raise HTTPException(status_code=404, detail=str(e))

# The old refresh_device_data endpoint is replaced by the one above.

@router.get("/search/{search_term}", response_model=List[DeviceDTO])
async def search_devices(
    search_term: str,
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(20, le=100) # Keep Query for parameter validation if needed
):
    """Search devices by name, description, or IP address"""
    devices_db = service.search_devices_by_term(search_term=search_term, limit=limit)
    return [DeviceDTO.from_entity(device) for device in devices_db]

@router.get("/organization/{org_name}", response_model=List[DeviceDTO])
async def get_devices_by_organization(
    org_name: str,
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get all devices for a specific organization"""
    devices_db = service.get_devices_by_organization_name(org_name=org_name, limit=limit, offset=offset)
    return [DeviceDTO.from_entity(device) for device in devices_db]

@router.get("/site/{site_name}", response_model=List[DeviceDTO])
async def get_devices_by_site(
    site_name: str,
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get all devices for a specific site"""
    devices_db = service.get_devices_by_site_name(site_name=site_name, limit=limit, offset=offset)
    return [DeviceDTO.from_entity(device) for device in devices_db]

@router.get("/alerts/critical", response_model=List[DeviceDTO])
async def get_devices_with_critical_alerts(
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(50, le=200)
):
    """Get devices with critical alerts"""
    devices_db = service.get_devices_with_critical_alerts(limit=limit)
    return [DeviceDTO.from_entity(device) for device in devices_db]

@router.get("/alerts/elevated", response_model=List[DeviceDTO])
async def get_devices_with_elevated_alerts(
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(50, le=200)
):
    """Get devices with elevated alerts"""
    devices_db = service.get_devices_with_elevated_alerts(limit=limit)
    return [DeviceDTO.from_entity(device) for device in devices_db]

@router.get("/status/offline", response_model=List[DeviceDTO])
async def get_offline_devices( # Original name is fine as it's distinct in API
    service: DeviceService = Depends(get_device_service), # Inject service
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get all offline devices"""
    devices_db = service.get_offline_devices_list(limit=limit, offset=offset)
    return [DeviceDTO.from_entity(device) for device in devices_db]