# app/api/monitoring.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from ..database import SessionLocal
from ..models.database import Device, Notification, Organization, Site, Group
from pydantic import BaseModel
from ..security import get_current_active_api_key

router = APIRouter(dependencies=[Depends(get_current_active_api_key)])

# Pydantic models for monitoring responses
class DashboardSummary(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    critical_alerts: int
    elevated_alerts: int
    total_notifications: int
    unread_notifications: int
    devices_with_agents: int
    last_updated: datetime

class AlertSummary(BaseModel):
    critical_count: int
    elevated_count: int
    normal_count: int
    low_count: int
    total_count: int
    devices_with_critical: int
    devices_with_elevated: int

class SystemHealth(BaseModel):
    healthy_devices: int
    warning_devices: int
    critical_devices: int
    offline_devices: int
    maintenance_devices: int
    antivirus_status: Dict[str, int]
    firewall_status: Dict[str, int]

class RecentActivity(BaseModel):
    id: int
    message: str
    priority: str
    datetime: datetime
    device_name: Optional[str]
    device_identifier: Optional[str]

class LocationStats(BaseModel):
    name: str
    total_devices: int
    online_devices: int
    offline_devices: int
    critical_alerts: int
    elevated_alerts: int

class PerformanceMetrics(BaseModel):
    avg_cpu_usage: Optional[float]
    avg_memory_usage: Optional[float]
    high_cpu_devices: int
    high_memory_devices: int
    low_disk_space_devices: int

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """Get main dashboard summary statistics"""
    
    # Basic device counts
    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.is_online == True).count()
    offline_devices = total_devices - online_devices
    devices_with_agents = db.query(Device).filter(Device.is_agent_installed == True).count()
    
    # Alert counts
    critical_alerts = db.query(func.sum(Device.critical_notifications)).scalar() or 0
    elevated_alerts = db.query(func.sum(Device.elevated_notifications)).scalar() or 0
    
    # Notification counts
    total_notifications = db.query(Notification).count()
    unread_notifications = db.query(Notification).filter(Notification.read == False).count()
    
    # Get last update time (most recent device update)
    last_device_update = db.query(func.max(Device.updated_at)).scalar()
    
    return DashboardSummary(
        total_devices=total_devices,
        online_devices=online_devices,
        offline_devices=offline_devices,
        critical_alerts=critical_alerts,
        elevated_alerts=elevated_alerts,
        total_notifications=total_notifications,
        unread_notifications=unread_notifications,
        devices_with_agents=devices_with_agents,
        last_updated=last_device_update or datetime.now()
    )

@router.get("/alerts", response_model=AlertSummary)
async def get_alert_summary(db: Session = Depends(get_db)):
    """Get summary of all alerts across the system"""
    
    # Total notification counts
    critical_count = db.query(func.sum(Device.critical_notifications)).scalar() or 0
    elevated_count = db.query(func.sum(Device.elevated_notifications)).scalar() or 0
    normal_count = db.query(func.sum(Device.normal_notifications)).scalar() or 0
    low_count = db.query(func.sum(Device.low_notifications)).scalar() or 0
    
    # Device counts with alerts
    devices_with_critical = db.query(Device).filter(Device.critical_notifications > 0).count()
    devices_with_elevated = db.query(Device).filter(Device.elevated_notifications > 0).count()
    
    return AlertSummary(
        critical_count=critical_count,
        elevated_count=elevated_count,
        normal_count=normal_count,
        low_count=low_count,
        total_count=critical_count + elevated_count + normal_count + low_count,
        devices_with_critical=devices_with_critical,
        devices_with_elevated=devices_with_elevated
    )

@router.get("/health", response_model=SystemHealth)
async def get_system_health(db: Session = Depends(get_db)):
    """Get overall system health metrics"""
    
    # Device health categories
    healthy_devices = db.query(Device).filter(
        and_(
            Device.is_online == True,
            Device.critical_notifications == 0,
            Device.elevated_notifications == 0,
            Device.in_maintenance == False
        )
    ).count()
    
    warning_devices = db.query(Device).filter(
        and_(
            Device.is_online == True,
            Device.elevated_notifications > 0,
            Device.critical_notifications == 0
        )
    ).count()
    
    critical_devices = db.query(Device).filter(
        Device.critical_notifications > 0
    ).count()
    
    offline_devices = db.query(Device).filter(Device.is_online == False).count()
    maintenance_devices = db.query(Device).filter(Device.in_maintenance == True).count()
    
    # Antivirus status
    av_enabled = db.query(Device).filter(Device.antivirus_enabled == "enabled").count()
    av_disabled = db.query(Device).filter(Device.antivirus_enabled == "disabled").count()
    av_unknown = db.query(Device).filter(
        or_(Device.antivirus_enabled.is_(None), Device.antivirus_enabled == "unknown")
    ).count()
    
    # Firewall status
    fw_enabled = db.query(Device).filter(Device.firewall_enabled == True).count()
    fw_disabled = db.query(Device).filter(Device.firewall_enabled == False).count()
    fw_unknown = db.query(Device).filter(Device.firewall_enabled.is_(None)).count()
    
    return SystemHealth(
        healthy_devices=healthy_devices,
        warning_devices=warning_devices,
        critical_devices=critical_devices,
        offline_devices=offline_devices,
        maintenance_devices=maintenance_devices,
        antivirus_status={
            "enabled": av_enabled,
            "disabled": av_disabled,
            "unknown": av_unknown
        },
        firewall_status={
            "enabled": fw_enabled,
            "disabled": fw_disabled,
            "unknown": fw_unknown
        }
    )

@router.get("/activity/recent", response_model=List[RecentActivity])
async def get_recent_activity(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    priority_filter: Optional[str] = Query(None, description="Filter by priority (critical, elevated, normal, low)")
):
    """Get recent system activity and notifications"""
    
    query = db.query(Notification).join(
        Device, Notification.device_identifier == Device.identifier, isouter=True
    )
    
    if priority_filter:
        query = query.filter(Notification.priority.ilike(priority_filter))
    
    notifications = query.order_by(desc(Notification.datetime)).limit(limit).all()
    
    activity = []
    for notif in notifications:
        device_name = None
        if notif.device:
            device_name = notif.device.name
        
        activity.append(RecentActivity(
            id=notif.id,
            message=notif.message,
            priority=notif.priority,
            datetime=notif.datetime,
            device_name=device_name,
            device_identifier=notif.device_identifier
        ))
    
    return activity

@router.get("/locations/organizations", response_model=List[LocationStats])
async def get_organization_stats(db: Session = Depends(get_db)):
    """Get statistics by organization"""
    
    stats = []
    
    organizations = db.query(Organization).all()
    
    for org in organizations:
        devices = db.query(Device).filter(Device.organization_id == org.id).all()
        
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.is_online)
        offline_devices = total_devices - online_devices
        critical_alerts = sum(d.critical_notifications or 0 for d in devices)
        elevated_alerts = sum(d.elevated_notifications or 0 for d in devices)
        
        stats.append(LocationStats(
            name=org.name,
            total_devices=total_devices,
            online_devices=online_devices,
            offline_devices=offline_devices,
            critical_alerts=critical_alerts,
            elevated_alerts=elevated_alerts
        ))
    
    return sorted(stats, key=lambda x: x.total_devices, reverse=True)

@router.get("/locations/sites", response_model=List[LocationStats])
async def get_site_stats(db: Session = Depends(get_db)):
    """Get statistics by site"""
    
    stats = []
    
    sites = db.query(Site).all()
    
    for site in sites:
        devices = db.query(Device).filter(Device.site_id == site.id).all()
        
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.is_online)
        offline_devices = total_devices - online_devices
        critical_alerts = sum(d.critical_notifications or 0 for d in devices)
        elevated_alerts = sum(d.elevated_notifications or 0 for d in devices)
        
        stats.append(LocationStats(
            name=site.name,
            total_devices=total_devices,
            online_devices=online_devices,
            offline_devices=offline_devices,
            critical_alerts=critical_alerts,
            elevated_alerts=elevated_alerts
        ))
    
    return sorted(stats, key=lambda x: x.total_devices, reverse=True)

@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(db: Session = Depends(get_db)):
    """Get system performance metrics"""
    
    # Average CPU and memory usage (only for online devices with data)
    online_devices = db.query(Device).filter(
        and_(Device.is_online == True, Device.cpu_usage.isnot(None))
    ).all()
    
    avg_cpu = None
    avg_memory = None
    high_cpu_devices = 0
    high_memory_devices = 0
    
    if online_devices:
        cpu_values = [d.cpu_usage for d in online_devices if d.cpu_usage is not None]
        memory_values = [d.memory_usage for d in online_devices if d.memory_usage is not None]
        
        if cpu_values:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            high_cpu_devices = sum(1 for cpu in cpu_values if cpu > 80)
        
        if memory_values:
            avg_memory = sum(memory_values) / len(memory_values)
            high_memory_devices = sum(1 for mem in memory_values if mem > 85)
    
    # Count devices with potential disk space issues (would need asset data)
    low_disk_space_devices = 0  # Placeholder - would need to check asset data
    
    return PerformanceMetrics(
        avg_cpu_usage=avg_cpu,
        avg_memory_usage=avg_memory,
        high_cpu_devices=high_cpu_devices,
        high_memory_devices=high_memory_devices,
        low_disk_space_devices=low_disk_space_devices
    )

@router.get("/trends/hourly")
async def get_hourly_trends(
    db: Session = Depends(get_db),
    hours: int = Query(24, le=168, description="Number of hours to look back")
):
    """Get hourly trends for devices and alerts"""
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # This is a simplified version - in a real implementation you'd want
    # to store historical data or use time-series data
    
    # For now, return current snapshot with timestamps
    hourly_data = []
    for i in range(hours):
        hour_time = start_time + timedelta(hours=i)
        
        # In a real implementation, you'd query historical data for each hour
        # For now, we'll return current values with different timestamps
        snapshot = {
            "timestamp": hour_time.isoformat(),
            "online_devices": db.query(Device).filter(Device.is_online == True).count(),
            "offline_devices": db.query(Device).filter(Device.is_online == False).count(),
            "critical_alerts": db.query(func.sum(Device.critical_notifications)).scalar() or 0,
            "elevated_alerts": db.query(func.sum(Device.elevated_notifications)).scalar() or 0
        }
        hourly_data.append(snapshot)
    
    return {"trends": hourly_data}

@router.get("/notifications/unread")
async def get_unread_notifications(
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    priority_filter: Optional[str] = Query(None)
):
    """Get unread notifications"""
    
    query = db.query(Notification).filter(Notification.read == False)
    
    if priority_filter:
        query = query.filter(Notification.priority.ilike(priority_filter))
    
    notifications = query.order_by(desc(Notification.datetime)).limit(limit).all()
    
    return notifications

@router.post("/notifications/{notification_id}/mark-read")
async def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    """Mark a notification as read"""
    
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.read = True
    db.commit()
    
    return {"status": "success", "message": "Notification marked as read"}

@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(db: Session = Depends(get_db)):
    """Mark all notifications as read"""
    
    updated_count = db.query(Notification).filter(Notification.read == False).update(
        {Notification.read: True}
    )
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Marked {updated_count} notifications as read"
    }