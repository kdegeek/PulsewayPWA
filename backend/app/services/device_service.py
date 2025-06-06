# backend/app/services/device_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional # Added Optional
from ..models.dto import DeviceFilters # Corrected import
from ..models.database import Device, Notification, DeviceAsset # Added Notification, DeviceAsset
from ..pulseway.client import PulsewayClient
from datetime import datetime # Added datetime
# from datetime import datetime, timezone # if using timezone.utc

class DeviceService:
    def __init__(self, db: Session, pulseway_client: PulsewayClient):
        self.db = db
        self.client = pulseway_client

    def get_devices_with_filters(self, filters: DeviceFilters) -> List[Device]: # Updated type hint
        # Logic from backend/app/api/devices.py::get_devices will be moved here
        # For now, let's add a placeholder implementation

        query = self.db.query(Device)

        # Apply filters (to be implemented fully)
        if filters.organization:
            query = query.filter(Device.organization_name.ilike(f"%{filters.organization}%"))
        if filters.site:
            query = query.filter(Device.site_name.ilike(f"%{filters.site}%"))
        if filters.group:
            query = query.filter(Device.group_name.ilike(f"%{filters.group}%"))
        if filters.online_only is not None: # Changed from if filters.online_only:
            query = query.filter(Device.is_online == filters.online_only)
        if filters.offline_only is not None: # Changed from if filters.offline_only:
            query = query.filter(Device.is_online == (not filters.offline_only))
        if filters.has_alerts:
            query = query.filter(
                (Device.critical_notifications > 0) |
                (Device.elevated_notifications > 0)
            )
        if filters.computer_type:
            query = query.filter(Device.computer_type.ilike(f"%{filters.computer_type}%"))

        devices = query.offset(filters.offset).limit(filters.limit).all()

        return devices

    def get_device_statistics(self) -> Dict[str, Any]: # Or a specific DTO if we want to map here
        """Calculates device statistics."""

        # Basic counts
        total_devices = self.db.query(Device).count()
        online_devices = self.db.query(Device).filter(Device.is_online == True).count()
        offline_devices = total_devices - online_devices
        devices_with_agent = self.db.query(Device).filter(Device.is_agent_installed == True).count()
        devices_without_agent = total_devices - devices_with_agent

        # Alert counts
        critical_alerts = self.db.query(Device).filter(Device.critical_notifications > 0).count()
        elevated_alerts = self.db.query(Device).filter(Device.elevated_notifications > 0).count()

        # Devices by organization
        org_stats_query = self.db.query(
            Device.organization_name,
            self.db.func.count(Device.identifier)
        ).group_by(Device.organization_name).all()
        devices_by_organization = {org or "Unknown": count for org, count in org_stats_query}

        # Devices by site
        site_stats_query = self.db.query(
            Device.site_name,
            self.db.func.count(Device.identifier)
        ).group_by(Device.site_name).all()
        devices_by_site = {site or "Unknown": count for site, count in site_stats_query}

        # Devices by type
        type_stats_query = self.db.query(
            Device.computer_type,
            self.db.func.count(Device.identifier)
        ).group_by(Device.computer_type).all()
        devices_by_type = {comp_type or "Unknown": count for comp_type, count in type_stats_query}

        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": offline_devices,
            "devices_with_agent": devices_with_agent,
            "devices_without_agent": devices_without_agent,
            "critical_alerts": critical_alerts,
            "elevated_alerts": elevated_alerts,
            "devices_by_organization": devices_by_organization,
            "devices_by_site": devices_by_site,
            "devices_by_type": devices_by_type
        }

    def get_device_details(self, device_id: str) -> Optional[Device]:
        """Retrieves a specific device by its identifier."""
        device = self.db.query(Device).filter(Device.identifier == device_id).first()
        return device

    def refresh_single_device_data(self, device_id: str) -> Dict[str, Any]:
        """Refreshes data for a specific device from Pulseway API and updates the local DB."""
        try:
            device_response = self.client.get_device(device_id)
            device_data = device_response.get('Data', {})

            if not device_data:
                return {"status": "error", "message": f"Device with ID {device_id} not found in Pulseway"}

            device = self.db.query(Device).filter(Device.identifier == device_id).first()

            if device:
                # Update existing device (ensure all fields are covered)
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
                device.computer_type = device_data.get('ComputerType', device.computer_type)
                # is_agent_installed and is_mdm_enrolled usually come from summary, not detail.
                # If they are in detailed_data, use them, otherwise retain existing.
                # device.is_agent_installed = device_data.get('IsAgentInstalled', device.is_agent_installed)
                # device.is_mdm_enrolled = device_data.get('IsMdmEnrolled', device.is_mdm_enrolled)
                device.in_maintenance = device_data.get('InMaintenance', device.in_maintenance)
                device.external_ip_address = device_data.get('ExternalIpAddress', device.external_ip_address)
                device.local_ip_addresses = device_data.get('LocalIpAddresses', device.local_ip_addresses)
                device.client_version = device_data.get('ClientVersion', device.client_version)
                device.memory_total = device_data.get('MemoryTotal', device.memory_total)
                device.firewall_enabled = device_data.get('FirewallEnabled', device.firewall_enabled)
                device.antivirus_enabled = device_data.get('AntivirusEnabled', device.antivirus_enabled)
                device.antivirus_up_to_date = device_data.get('AntivirusUpToDate', device.antivirus_up_to_date)
                device.uac_enabled = device_data.get('UacEnabled', device.uac_enabled)
                device.event_logs = device_data.get('EventLogs', device.event_logs)
                device.updates = device_data.get('Updates', device.updates)

                api_last_seen = device_data.get('LastSeenOnline')
                if api_last_seen:
                    try:
                        device.last_seen_online = datetime.fromisoformat(api_last_seen.replace('Z', '+00:00'))
                    except ValueError:
                        pass # Keep old value or log

                device.updated_at = datetime.now() # Consider datetime.now(timezone.utc)

                self.db.commit()
                self.db.refresh(device)
                return {"status": "success", "message": "Device data refreshed"}
            else:
                return {"status": "error", "message": f"Device with ID {device_id} not found in local database"}

        except Exception as e:
            self.db.rollback()
            # Log e (e.g., logger.error(f"Failed to refresh device data for {device_id}: {e}"))
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

    def search_devices_by_term(self, search_term: str, limit: int = 20) -> List[Device]:
        """Searches devices by name, description, or IP address."""
        return self.db.query(Device).filter(
            (Device.name.ilike(f"%{search_term}%")) |
            (Device.description.ilike(f"%{search_term}%")) |
            (Device.external_ip_address.ilike(f"%{search_term}%"))
        ).limit(limit).all()

    def get_devices_by_organization_name(self, org_name: str, limit: int = 100, offset: int = 0) -> List[Device]:
        """Gets all devices for a specific organization."""
        return self.db.query(Device).filter(
            Device.organization_name.ilike(f"%{org_name}%")
        ).offset(offset).limit(limit).all()

    def get_devices_by_site_name(self, site_name: str, limit: int = 100, offset: int = 0) -> List[Device]:
        """Gets all devices for a specific site."""
        return self.db.query(Device).filter(
            Device.site_name.ilike(f"%{site_name}%")
        ).offset(offset).limit(limit).all()

    def get_devices_with_critical_alerts(self, limit: int = 50) -> List[Device]:
        """Gets devices with critical alerts."""
        return self.db.query(Device).filter(
            Device.critical_notifications > 0
        ).order_by(Device.critical_notifications.desc()).limit(limit).all()

    def get_devices_with_elevated_alerts(self, limit: int = 50) -> List[Device]:
        """Gets devices with elevated alerts."""
        return self.db.query(Device).filter(
            Device.elevated_notifications > 0
        ).order_by(Device.elevated_notifications.desc()).limit(limit).all()

    def get_offline_devices_list(self, limit: int = 100, offset: int = 0) -> List[Device]: # Renamed to avoid conflict if any
        """Gets all offline devices."""
        return self.db.query(Device).filter(
            Device.is_online == False
        ).order_by(Device.last_seen_online.desc()).offset(offset).limit(limit).all()

    def get_device_or_raise(self, device_id: str) -> Device:
        """Helper to get a device by ID or raise ValueError if not found."""
        # This replaces the direct HTTPException. API layer will convert ValueError.
        device = self.db.query(Device).filter(Device.identifier == device_id).first()
        if not device:
            raise ValueError(f"Device with ID {device_id} not found.")
        return device

    def get_notifications_for_device(self, device_id: str, limit: int, offset: int) -> List[Notification]:
        """Gets notifications for a specific device."""
        self.get_device_or_raise(device_id) # Check device existence

        return self.db.query(Notification).filter(
            Notification.device_identifier == device_id
        ).order_by(Notification.datetime.desc()).offset(offset).limit(limit).all()

    def get_assets_for_device(self, device_id: str) -> Optional[DeviceAsset]:
        """Gets asset information for a specific device."""
        self.get_device_or_raise(device_id) # Check device existence

        asset = self.db.query(DeviceAsset).filter(
            DeviceAsset.device_identifier == device_id
        ).first()
        if not asset:
            # Consistent error type for API layer to handle
            raise ValueError(f"Assets not found for device ID {device_id}.")
        return asset
