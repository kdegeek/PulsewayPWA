# app/services/data_sync.py
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
import logging
from ..database import SessionLocal
from ..models.database import (
    Organization, Site, Group, Device, DeviceAsset, 
    Notification, Script, Task, Workflow
)
from ..pulseway.client import PulsewayClient

logger = logging.getLogger(__name__)

class DataSyncService:
    """Service for synchronizing Pulseway data with local database"""
    
    def __init__(self, pulseway_client: PulsewayClient):
        self.client = pulseway_client
        self.db_session = SessionLocal
    
    async def sync_all_data(self):
        """Sync all data from Pulseway API"""
        logger.info("Starting full data synchronization...")
        
        try:
            # Sync in order of dependencies
            await self.sync_organizations()
            await self.sync_sites()
            await self.sync_groups()
            await self.sync_devices()
            await self.sync_device_assets()
            await self.sync_notifications()
            await self.sync_scripts()
            await self.sync_tasks()
            await self.sync_workflows()
            
            logger.info("Data synchronization completed successfully")
        except Exception as e:
            logger.error(f"Data synchronization failed: {e}")
            raise
    
    async def sync_organizations(self):
        """Sync organizations"""
        logger.info("Syncing organizations...")
        
        db = self.db_session()
        try:
            all_organizations_data = []
            skip = 0
            top = 100

            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_organizations, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_organizations_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_organizations_data) > 10000:  # Adjust limit as needed
                    logger.warning("Too many organizations, stopping pagination")
                    break

            local_orgs = db.query(Organization).all()
            local_orgs_map = {org.id: org for org in local_orgs}

            created_count = 0
            updated_count = 0

            for org_data in all_organizations_data:
                org_id = org_data['Id']
                record_to_update = local_orgs_map.get(org_id)

                if record_to_update:
                    # Update existing organization
                    updated = False
                    if record_to_update.name != org_data['Name']:
                        record_to_update.name = org_data['Name']
                        updated = True
                    if record_to_update.has_custom_fields != org_data.get('HasCustomFields', False):
                        record_to_update.has_custom_fields = org_data.get('HasCustomFields', False)
                        updated = True
                    if record_to_update.psa_mapping_id != org_data.get('PsaMappingId'):
                        record_to_update.psa_mapping_id = org_data.get('PsaMappingId')
                        updated = True
                    if record_to_update.psa_mapping_type != org_data.get('PsaMappingType'):
                        record_to_update.psa_mapping_type = org_data.get('PsaMappingType')
                        updated = True

                    if updated:
                        record_to_update.updated_at = datetime.now(timezone.utc) # Or rely on DB onupdate
                        updated_count += 1
                else:
                    # Create new organization
                    organization = Organization(
                        id=org_id,
                        name=org_data['Name'],
                        has_custom_fields=org_data.get('HasCustomFields', False),
                        psa_mapping_id=org_data.get('PsaMappingId'),
                        psa_mapping_type=org_data.get('PsaMappingType')
                        # created_at and updated_at will be set by the DB default/onupdate
                    )
                    db.add(organization)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced organizations. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync organizations: {e}")
            raise
        finally:
            db.close()
    
    async def sync_sites(self):
        """Sync sites"""
        logger.info("Syncing sites...")
        
        db = self.db_session()
        try:
            all_sites_data = []
            skip = 0
            top = 100

            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_sites, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_sites_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_sites_data) > 10000: # Adjust limit as needed
                    logger.warning("Too many sites, stopping pagination")
                    break

            local_sites = db.query(Site).all()
            local_sites_map = {site.id: site for site in local_sites}

            created_count = 0
            updated_count = 0

            for site_data in all_sites_data:
                site_id = site_data['Id']
                record_to_update = local_sites_map.get(site_id)

                if record_to_update:
                    updated = False
                    if record_to_update.name != site_data['Name']:
                        record_to_update.name = site_data['Name']
                        updated = True
                    if record_to_update.parent_id != site_data.get('ParentId'):
                        record_to_update.parent_id = site_data.get('ParentId')
                        updated = True
                    if record_to_update.parent_name != site_data.get('ParentName'):
                        record_to_update.parent_name = site_data.get('ParentName')
                        updated = True
                    if record_to_update.has_custom_fields != site_data.get('HasCustomFields', False):
                        record_to_update.has_custom_fields = site_data.get('HasCustomFields', False)
                        updated = True
                    if record_to_update.psa_mapping_id != site_data.get('PsaMappingId'):
                        record_to_update.psa_mapping_id = site_data.get('PsaMappingId')
                        updated = True
                    if record_to_update.psa_integration_type != site_data.get('PsaIntegrationType'):
                        record_to_update.psa_integration_type = site_data.get('PsaIntegrationType')
                        updated = True
                    if record_to_update.contact_info != site_data.get('ContactInformation'):
                        record_to_update.contact_info = site_data.get('ContactInformation')
                        updated = True

                    if updated:
                        record_to_update.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                else:
                    site = Site(
                        id=site_id,
                        name=site_data['Name'],
                        parent_id=site_data.get('ParentId'),
                        parent_name=site_data.get('ParentName'),
                        has_custom_fields=site_data.get('HasCustomFields', False),
                        psa_mapping_id=site_data.get('PsaMappingId'),
                        psa_integration_type=site_data.get('PsaIntegrationType'),
                        contact_info=site_data.get('ContactInformation')
                    )
                    db.add(site)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced sites. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync sites: {e}")
            raise
        finally:
            db.close()
    
    async def sync_groups(self):
        """Sync groups"""
        logger.info("Syncing groups...")
        
        db = self.db_session()
        try:
            all_groups_data = []
            skip = 0
            top = 100

            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_groups, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_groups_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_groups_data) > 10000: # Adjust limit as needed
                    logger.warning("Too many groups, stopping pagination")
                    break

            local_groups = db.query(Group).all()
            local_groups_map = {group.id: group for group in local_groups}

            created_count = 0
            updated_count = 0

            for group_data in all_groups_data:
                group_id = group_data['Id']
                record_to_update = local_groups_map.get(group_id)

                if record_to_update:
                    updated = False
                    if record_to_update.name != group_data['Name']:
                        record_to_update.name = group_data['Name']
                        updated = True
                    if record_to_update.parent_site_id != group_data.get('ParentSiteId'):
                        record_to_update.parent_site_id = group_data.get('ParentSiteId')
                        updated = True
                    if record_to_update.parent_site_name != group_data.get('ParentSiteName'):
                        record_to_update.parent_site_name = group_data.get('ParentSiteName')
                        updated = True
                    if record_to_update.parent_organization_id != group_data.get('ParentOrganizationId'):
                        record_to_update.parent_organization_id = group_data.get('ParentOrganizationId')
                        updated = True
                    if record_to_update.parent_organization_name != group_data.get('ParentOrganizationName'):
                        record_to_update.parent_organization_name = group_data.get('ParentOrganizationName')
                        updated = True
                    if record_to_update.notes != group_data.get('Notes'):
                        record_to_update.notes = group_data.get('Notes')
                        updated = True
                    if record_to_update.has_custom_fields != group_data.get('HasCustomFields', False):
                        record_to_update.has_custom_fields = group_data.get('HasCustomFields', False)
                        updated = True
                    if record_to_update.psa_mapping_id != group_data.get('PsaMappingId'):
                        record_to_update.psa_mapping_id = group_data.get('PsaMappingId')
                        updated = True
                    if record_to_update.psa_mapping_type != group_data.get('PsaMappingType'):
                        record_to_update.psa_mapping_type = group_data.get('PsaMappingType')
                        updated = True

                    if updated:
                        record_to_update.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                else:
                    group = Group(
                        id=group_id,
                        name=group_data['Name'],
                        parent_site_id=group_data.get('ParentSiteId'),
                        parent_site_name=group_data.get('ParentSiteName'),
                        parent_organization_id=group_data.get('ParentOrganizationId'),
                        parent_organization_name=group_data.get('ParentOrganizationName'),
                        notes=group_data.get('Notes'),
                        has_custom_fields=group_data.get('HasCustomFields', False),
                        psa_mapping_id=group_data.get('PsaMappingId'),
                        psa_mapping_type=group_data.get('PsaMappingType')
                    )
                    db.add(group)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced groups. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync groups: {e}")
            raise
        finally:
            db.close()
    
    async def sync_devices(self):
        """Sync devices"""
        logger.info("Syncing devices...")
        
        db = self.db_session()
        try:
            # Get all devices from API (paginated)
            all_devices = []
            skip = 0
            top = 100
            
            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_devices, top, skip
                )
                
                devices_data = response.get('Data', [])
                if not devices_data:
                    break
                
                all_devices.extend(devices_data)
                skip += top
                
                # Safety check
                if len(all_devices) > 10000:  # Adjust limit as needed
                    logger.warning("Too many devices, stopping pagination")
                    break
            
            local_devices = db.query(Device).all()
            local_devices_map = {dev.identifier: dev for dev in local_devices}

            created_count = 0
            updated_count = 0

            for device_data in all_devices:
                device_identifier = device_data['Identifier']
                record_to_update = local_devices_map.get(device_identifier)

                # Get detailed device info - this is needed for both create and update
                try:
                    device_details_response = await asyncio.get_event_loop().run_in_executor(
                        None, self.client.get_device, device_identifier
                    )
                    detailed_data = device_details_response.get('Data', {})
                except Exception as e:
                    logger.warning(f"Failed to get details for device {device_identifier}: {e}")
                    detailed_data = {}

                # Parse last seen online
                last_seen = None
                if detailed_data.get('LastSeenOnline'):
                    try:
                        last_seen = datetime.fromisoformat(detailed_data['LastSeenOnline'].replace('Z', '+00:00'))
                    except ValueError:
                        pass # Keep last_seen as None if parsing fails

                if record_to_update:
                    updated = False
                    if record_to_update.name != device_data['Name']:
                        record_to_update.name = device_data['Name']
                        updated = True
                    # Comparing all relevant fields from detailed_data and device_data
                    if record_to_update.description != detailed_data.get('Description'):
                        record_to_update.description = detailed_data.get('Description')
                        updated = True
                    if record_to_update.computer_type != detailed_data.get('ComputerType'):
                        record_to_update.computer_type = detailed_data.get('ComputerType')
                        updated = True
                    if record_to_update.is_online != detailed_data.get('IsOnline', False):
                        record_to_update.is_online = detailed_data.get('IsOnline', False)
                        updated = True
                    if record_to_update.is_agent_installed != device_data.get('IsAgentInstalled', False): # From summary
                        record_to_update.is_agent_installed = device_data.get('IsAgentInstalled', False)
                        updated = True
                    if record_to_update.is_mdm_enrolled != device_data.get('IsMdmEnrolled', False): # From summary
                        record_to_update.is_mdm_enrolled = device_data.get('IsMdmEnrolled', False)
                        updated = True
                    if record_to_update.in_maintenance != detailed_data.get('InMaintenance', False):
                        record_to_update.in_maintenance = detailed_data.get('InMaintenance', False)
                        updated = True
                    if record_to_update.external_ip_address != detailed_data.get('ExternalIpAddress'):
                        record_to_update.external_ip_address = detailed_data.get('ExternalIpAddress')
                        updated = True
                    if record_to_update.local_ip_addresses != detailed_data.get('LocalIpAddresses'): # This could be a list/JSON
                        record_to_update.local_ip_addresses = detailed_data.get('LocalIpAddresses')
                        updated = True
                    if record_to_update.uptime != detailed_data.get('Uptime'):
                        record_to_update.uptime = detailed_data.get('Uptime')
                        updated = True
                    if record_to_update.client_version != detailed_data.get('ClientVersion'):
                        record_to_update.client_version = detailed_data.get('ClientVersion')
                        updated = True
                    if record_to_update.cpu_usage != detailed_data.get('CpuUsage'):
                        record_to_update.cpu_usage = detailed_data.get('CpuUsage')
                        updated = True
                    if record_to_update.memory_usage != detailed_data.get('MemoryUsage'):
                        record_to_update.memory_usage = detailed_data.get('MemoryUsage')
                        updated = True
                    if record_to_update.memory_total != detailed_data.get('MemoryTotal'):
                        record_to_update.memory_total = detailed_data.get('MemoryTotal')
                        updated = True
                    # ... (continue for all other fields including notifications, group, site, org info, last_seen_online)
                    if record_to_update.firewall_enabled != detailed_data.get('FirewallEnabled'):
                        record_to_update.firewall_enabled = detailed_data.get('FirewallEnabled')
                        updated = True
                    if record_to_update.antivirus_enabled != detailed_data.get('AntivirusEnabled'):
                        record_to_update.antivirus_enabled = detailed_data.get('AntivirusEnabled')
                        updated = True
                    if record_to_update.antivirus_up_to_date != detailed_data.get('AntivirusUpToDate'):
                        record_to_update.antivirus_up_to_date = detailed_data.get('AntivirusUpToDate')
                        updated = True
                    if record_to_update.uac_enabled != detailed_data.get('UacEnabled'):
                        record_to_update.uac_enabled = detailed_data.get('UacEnabled')
                        updated = True
                    if record_to_update.critical_notifications != detailed_data.get('CriticalNotifications', 0):
                        record_to_update.critical_notifications = detailed_data.get('CriticalNotifications', 0)
                        updated = True
                    if record_to_update.elevated_notifications != detailed_data.get('ElevatedNotifications', 0):
                        record_to_update.elevated_notifications = detailed_data.get('ElevatedNotifications', 0)
                        updated = True
                    if record_to_update.normal_notifications != detailed_data.get('NormalNotifications', 0):
                        record_to_update.normal_notifications = detailed_data.get('NormalNotifications', 0)
                        updated = True
                    if record_to_update.low_notifications != detailed_data.get('LowNotifications', 0):
                        record_to_update.low_notifications = detailed_data.get('LowNotifications', 0)
                        updated = True
                    if record_to_update.event_logs != detailed_data.get('EventLogs'): # JSON
                        record_to_update.event_logs = detailed_data.get('EventLogs')
                        updated = True
                    if record_to_update.updates != detailed_data.get('Updates'): # JSON
                        record_to_update.updates = detailed_data.get('Updates')
                        updated = True
                    if record_to_update.group_id != device_data.get('GroupId'): # From summary
                        record_to_update.group_id = device_data.get('GroupId')
                        updated = True
                    if record_to_update.group_name != device_data.get('GroupName'): # From summary
                        record_to_update.group_name = device_data.get('GroupName')
                        updated = True
                    if record_to_update.site_id != device_data.get('SiteId'): # From summary
                        record_to_update.site_id = device_data.get('SiteId')
                        updated = True
                    if record_to_update.site_name != device_data.get('SiteName'): # From summary
                        record_to_update.site_name = device_data.get('SiteName')
                        updated = True
                    if record_to_update.organization_id != device_data.get('OrganizationId'): # From summary
                        record_to_update.organization_id = device_data.get('OrganizationId')
                        updated = True
                    if record_to_update.organization_name != device_data.get('OrganizationName'): # From summary
                        record_to_update.organization_name = device_data.get('OrganizationName')
                        updated = True
                    if record_to_update.last_seen_online != last_seen:
                        record_to_update.last_seen_online = last_seen
                        updated = True

                    if updated:
                        record_to_update.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                else:
                    device = Device(
                        identifier=device_identifier,
                        name=device_data['Name'], # From summary
                        description=detailed_data.get('Description'),
                        computer_type=detailed_data.get('ComputerType'),
                        is_online=detailed_data.get('IsOnline', False),
                        is_agent_installed=device_data.get('IsAgentInstalled', False), # From summary
                        is_mdm_enrolled=device_data.get('IsMdmEnrolled', False), # From summary
                        in_maintenance=detailed_data.get('InMaintenance', False),
                        external_ip_address=detailed_data.get('ExternalIpAddress'),
                        local_ip_addresses=detailed_data.get('LocalIpAddresses'),
                        uptime=detailed_data.get('Uptime'),
                        client_version=detailed_data.get('ClientVersion'),
                        cpu_usage=detailed_data.get('CpuUsage'),
                        memory_usage=detailed_data.get('MemoryUsage'),
                        memory_total=detailed_data.get('MemoryTotal'),
                        firewall_enabled=detailed_data.get('FirewallEnabled'),
                        antivirus_enabled=detailed_data.get('AntivirusEnabled'),
                        antivirus_up_to_date=detailed_data.get('AntivirusUpToDate'),
                        uac_enabled=detailed_data.get('UacEnabled'),
                        critical_notifications=detailed_data.get('CriticalNotifications', 0),
                        elevated_notifications=detailed_data.get('ElevatedNotifications', 0),
                        normal_notifications=detailed_data.get('NormalNotifications', 0),
                        low_notifications=detailed_data.get('LowNotifications', 0),
                        event_logs=detailed_data.get('EventLogs'),
                        updates=detailed_data.get('Updates'),
                        group_id=device_data.get('GroupId'), # From summary
                        group_name=device_data.get('GroupName'), # From summary
                        site_id=device_data.get('SiteId'), # From summary
                        site_name=device_data.get('SiteName'), # From summary
                        organization_id=device_data.get('OrganizationId'), # From summary
                        organization_name=device_data.get('OrganizationName'), # From summary
                        last_seen_online=last_seen
                    )
                    db.add(device)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced devices. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync devices: {e}")
            raise
        finally:
            db.close()
    
    async def sync_device_assets(self):
        """Sync device assets"""
        logger.info("Syncing device assets...")
        
        db = self.db_session()
        try:
            all_assets_data = []
            skip = 0
            top = 100

            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_assets, top, skip
                )
                
                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_assets_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_assets_data) > 20000:
                    logger.warning("Too many assets, stopping pagination")
                    break

            local_assets = db.query(DeviceAsset).all()
            # The primary key for DeviceAsset is its own 'id', but it's uniquely linked to a device by 'device_identifier'.
            # For upserting based on API data, we should use the device_identifier from the API.
            local_assets_map = {asset.device_identifier: asset for asset in local_assets}

            created_count = 0
            updated_count = 0

            for asset_data in all_assets_data:
                # 'Identifier' from /assets endpoint is the device_identifier
                device_identifier = asset_data.get('Identifier')
                if not device_identifier:
                    logger.warning(f"Asset data missing Identifier (device_identifier): {asset_data}")
                    continue

                record_to_update = local_assets_map.get(device_identifier)

                if record_to_update:
                    updated = False
                    if record_to_update.tags != asset_data.get('Tags'):
                        record_to_update.tags = asset_data.get('Tags')
                        updated = True
                    if record_to_update.asset_info != asset_data.get('AssetInfo'): # This is likely a JSON field
                        record_to_update.asset_info = asset_data.get('AssetInfo')
                        updated = True
                    if record_to_update.public_ip_address != asset_data.get('PublicIpAddress'):
                        record_to_update.public_ip_address = asset_data.get('PublicIpAddress')
                        updated = True
                    if record_to_update.ip_addresses != asset_data.get('IpAddresses'): # JSON field
                        record_to_update.ip_addresses = asset_data.get('IpAddresses')
                        updated = True
                    if record_to_update.disks != asset_data.get('Disks'): # JSON field
                        record_to_update.disks = asset_data.get('Disks')
                        updated = True
                    if record_to_update.installed_software != asset_data.get('InstalledSoftware'): # JSON field
                        record_to_update.installed_software = asset_data.get('InstalledSoftware')
                        updated = True

                    if updated:
                        record_to_update.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                else:
                    device_asset = DeviceAsset(
                        device_identifier=device_identifier,
                        tags=asset_data.get('Tags'),
                        asset_info=asset_data.get('AssetInfo'),
                        public_ip_address=asset_data.get('PublicIpAddress'),
                        ip_addresses=asset_data.get('IpAddresses'),
                        disks=asset_data.get('Disks'),
                        installed_software=asset_data.get('InstalledSoftware')
                    )
                    db.add(device_asset)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced device assets. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync device assets: {e}")
            raise
        finally:
            db.close()
    
    async def sync_notifications(self):
        """Sync notifications"""
        logger.info("Syncing notifications...")
        
        db = self.db_session()
        try:
            all_notifications_data = []
            skip = 0
            top = 100 # Using a smaller page size for notifications
            
            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_notifications, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_notifications_data.extend(current_batch)
                skip += top

                # Safety check - notifications can be numerous
                if len(all_notifications_data) > 50000:
                    logger.warning("Too many notifications, stopping pagination")
                    break
            
            local_notifications = db.query(Notification).all()
            local_notifications_map = {notif.id: notif for notif in local_notifications}

            created_count = 0
            updated_count = 0

            for notif_data in all_notifications_data:
                notif_id = notif_data['Id']
                record_to_update = local_notifications_map.get(notif_id)

                # Parse datetime - needed for both create and update comparison
                notification_datetime = None
                api_datetime_val = notif_data.get('DateTime')
                if api_datetime_val:
                    try:
                        if isinstance(api_datetime_val, str):
                            notification_datetime = datetime.fromisoformat(api_datetime_val.replace('Z', '+00:00'))
                        else: # Assuming Unix timestamp if not string
                            notification_datetime = datetime.fromtimestamp(api_datetime_val, tz=timezone.utc)
                    except (ValueError, OSError):
                        logger.warning(f"Could not parse datetime for notification {notif_id}: {api_datetime_val}")
                        pass # Keep notification_datetime as None

                if record_to_update:
                    updated = False
                    if record_to_update.message != notif_data['Message']:
                        record_to_update.message = notif_data['Message']
                        updated = True

                    # Ensure datetimes are comparable (e.g. both are timezone-aware or naive)
                    # If record_to_update.datetime can be None or have different tz, adjust comparison
                    if record_to_update.datetime != notification_datetime:
                        record_to_update.datetime = notification_datetime
                        updated = True

                    api_priority = notif_data.get('Priority', 'Normal')
                    if record_to_update.priority != api_priority:
                        record_to_update.priority = api_priority
                        updated = True

                    # 'read' status is managed internally, not from API typically, so skip comparing/updating it
                    # unless API provides it. Current logic defaults to False on create.

                    if updated:
                        # Assuming Notification model has an onupdate for updated_at
                        # If not, add: record_to_update.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                else:
                    notification = Notification(
                        id=notif_id,
                        message=notif_data['Message'],
                        datetime=notification_datetime,
                        priority=notif_data.get('Priority', 'Normal'),
                        read=False  # Default to unread for new notifications
                    )
                    db.add(notification)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced notifications. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync notifications: {e}")
            raise
        finally:
            db.close()
    
    async def sync_scripts(self):
        """Sync scripts"""
        logger.info("Syncing scripts...")
        
        db = self.db_session()
        try:
            all_scripts_data = []
            skip = 0
            top = 100

            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_scripts, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_scripts_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_scripts_data) > 10000: # Adjust limit as needed
                    logger.warning("Too many scripts, stopping pagination")
                    break

            local_scripts = db.query(Script).all()
            local_scripts_map = {script.id: script for script in local_scripts}

            created_count = 0
            updated_count = 0

            for script_data in all_scripts_data:
                script_id = script_data['Id']
                record_to_update = local_scripts_map.get(script_id)

                if record_to_update:
                    updated = False
                    if record_to_update.name != script_data['Name']:
                        record_to_update.name = script_data['Name']
                        updated = True
                    if record_to_update.description != script_data.get('Description'):
                        record_to_update.description = script_data.get('Description')
                        updated = True
                    if record_to_update.category_id != script_data.get('CategoryId'):
                        record_to_update.category_id = script_data.get('CategoryId')
                        updated = True
                    if record_to_update.category_name != script_data.get('CategoryName'):
                        record_to_update.category_name = script_data.get('CategoryName')
                        updated = True
                    if record_to_update.platforms != script_data.get('Platforms'): # This could be a JSON/List
                        record_to_update.platforms = script_data.get('Platforms')
                        updated = True
                    if record_to_update.created_by != script_data.get('CreatedBy'):
                        record_to_update.created_by = script_data.get('CreatedBy')
                        updated = True
                    if record_to_update.is_built_in != script_data.get('IsBuiltIn', False):
                        record_to_update.is_built_in = script_data.get('IsBuiltIn', False)
                        updated = True

                    if updated:
                        record_to_update.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                else:
                    script = Script(
                        id=script_id,
                        name=script_data['Name'],
                        description=script_data.get('Description'),
                        category_id=script_data.get('CategoryId'),
                        category_name=script_data.get('CategoryName'),
                        platforms=script_data.get('Platforms'),
                        created_by=script_data.get('CreatedBy'),
                        is_built_in=script_data.get('IsBuiltIn', False)
                    )
                    db.add(script)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced scripts. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync scripts: {e}")
            raise
        finally:
            db.close()
    
    async def sync_tasks(self):
        """Sync tasks"""
        logger.info("Syncing tasks...")
        
        db = self.db_session()
        try:
            all_tasks_data = []
            skip = 0
            top = 100
            
            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_tasks, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_tasks_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_tasks_data) > 10000: # Adjust limit as needed
                    logger.warning("Too many tasks, stopping pagination")
                    break
            
            local_tasks = db.query(Task).all()
            local_tasks_map = {task.id: task for task in local_tasks}

            created_count = 0
            updated_count = 0

            for task_data in all_tasks_data:
                task_id = task_data['Id']
                record_to_update = local_tasks_map.get(task_id)

                # Parse task_updated_at from API
                api_task_updated_at = None
                if task_data.get('UpdatedAt'):
                    try:
                        api_task_updated_at = datetime.fromisoformat(task_data['UpdatedAt'].replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Could not parse UpdatedAt for task {task_id}: {task_data.get('UpdatedAt')}")
                        pass # Keep api_task_updated_at as None

                if record_to_update:
                    updated = False
                    if record_to_update.name != task_data['Name']:
                        record_to_update.name = task_data['Name']
                        updated = True
                    if record_to_update.description != task_data.get('Description'):
                        record_to_update.description = task_data.get('Description')
                        updated = True
                    if record_to_update.is_enabled != task_data.get('IsEnabled', True):
                        record_to_update.is_enabled = task_data.get('IsEnabled', True)
                        updated = True
                    if record_to_update.scope_id != task_data.get('ScopeId'):
                        record_to_update.scope_id = task_data.get('ScopeId')
                        updated = True
                    if record_to_update.scope_name != task_data.get('ScopeName'):
                        record_to_update.scope_name = task_data.get('ScopeName')
                        updated = True
                    if record_to_update.is_scheduled != task_data.get('IsScheduled', False):
                        record_to_update.is_scheduled = task_data.get('IsScheduled', False)
                        updated = True
                    if record_to_update.total_scripts != task_data.get('TotalScripts', 0):
                        record_to_update.total_scripts = task_data.get('TotalScripts', 0)
                        updated = True
                    if record_to_update.is_built_in != task_data.get('IsBuiltIn', False):
                        record_to_update.is_built_in = task_data.get('IsBuiltIn', False)
                        updated = True
                    if record_to_update.continue_on_error != task_data.get('ContinueOnError', False):
                        record_to_update.continue_on_error = task_data.get('ContinueOnError', False)
                        updated = True
                    if record_to_update.execution_state != task_data.get('ExecutionState', 'Idle'):
                        record_to_update.execution_state = task_data.get('ExecutionState', 'Idle')
                        updated = True
                    if record_to_update.task_updated_at != api_task_updated_at:
                        record_to_update.task_updated_at = api_task_updated_at
                        updated = True

                    if updated:
                        # The model itself might have an onupdate for a general 'updated_at' field.
                        # Here we're explicitly setting task_updated_at from the API.
                        # If there's a separate DB-managed 'updated_at', it should auto-update.
                        updated_count += 1
                else:
                    task = Task(
                        id=task_id,
                        name=task_data['Name'],
                        description=task_data.get('Description'),
                        is_enabled=task_data.get('IsEnabled', True),
                        scope_id=task_data.get('ScopeId'),
                        scope_name=task_data.get('ScopeName'),
                        is_scheduled=task_data.get('IsScheduled', False),
                        total_scripts=task_data.get('TotalScripts', 0),
                        is_built_in=task_data.get('IsBuiltIn', False),
                        continue_on_error=task_data.get('ContinueOnError', False),
                        execution_state=task_data.get('ExecutionState', 'Idle'),
                        task_updated_at=api_task_updated_at
                    )
                    db.add(task)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced tasks. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync tasks: {e}")
            raise
        finally:
            db.close()
    
    async def sync_workflows(self):
        """Sync workflows"""
        logger.info("Syncing workflows...")
        
        db = self.db_session()
        try:
            all_workflows_data = []
            skip = 0
            top = 100
            
            while True:
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.client.get_workflows, top, skip
                )

                current_batch = response.get('Data', [])
                if not current_batch:
                    break

                all_workflows_data.extend(current_batch)
                skip += top

                # Safety check
                if len(all_workflows_data) > 10000: # Adjust limit as needed
                    logger.warning("Too many workflows, stopping pagination")
                    break
            
            local_workflows = db.query(Workflow).all()
            local_workflows_map = {wf.id: wf for wf in local_workflows}

            created_count = 0
            updated_count = 0

            for workflow_data in all_workflows_data:
                workflow_id = workflow_data['Id']
                record_to_update = local_workflows_map.get(workflow_id)

                # Parse workflow_updated_at from API
                api_workflow_updated_at = None
                if workflow_data.get('UpdatedAt'):
                    try:
                        api_workflow_updated_at = datetime.fromisoformat(workflow_data['UpdatedAt'].replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Could not parse UpdatedAt for workflow {workflow_id}: {workflow_data.get('UpdatedAt')}")
                        pass

                if record_to_update:
                    updated = False
                    if record_to_update.name != workflow_data['Name']:
                        record_to_update.name = workflow_data['Name']
                        updated = True
                    if record_to_update.description != workflow_data.get('Description'):
                        record_to_update.description = workflow_data.get('Description')
                        updated = True
                    if record_to_update.is_enabled != workflow_data.get('IsEnabled', True):
                        record_to_update.is_enabled = workflow_data.get('IsEnabled', True)
                        updated = True
                    if record_to_update.trigger_type != workflow_data.get('TriggerType'):
                        record_to_update.trigger_type = workflow_data.get('TriggerType')
                        updated = True
                    if record_to_update.trigger_sub_type != workflow_data.get('TriggerSubType'):
                        record_to_update.trigger_sub_type = workflow_data.get('TriggerSubType')
                        updated = True
                    if record_to_update.context_type != workflow_data.get('ContextType'):
                        record_to_update.context_type = workflow_data.get('ContextType')
                        updated = True
                    if record_to_update.context_item_id != workflow_data.get('ContextItemId'):
                        record_to_update.context_item_id = workflow_data.get('ContextItemId')
                        updated = True
                    if record_to_update.workflow_updated_at != api_workflow_updated_at:
                        record_to_update.workflow_updated_at = api_workflow_updated_at
                        updated = True

                    if updated:
                        # If there's a separate DB-managed 'updated_at', it should auto-update.
                        updated_count += 1
                else:
                    workflow = Workflow(
                        id=workflow_id,
                        name=workflow_data['Name'],
                        description=workflow_data.get('Description'),
                        is_enabled=workflow_data.get('IsEnabled', True),
                        trigger_type=workflow_data.get('TriggerType'),
                        trigger_sub_type=workflow_data.get('TriggerSubType'),
                        context_type=workflow_data.get('ContextType'),
                        context_item_id=workflow_data.get('ContextItemId'),
                        workflow_updated_at=api_workflow_updated_at
                    )
                    db.add(workflow)
                    created_count += 1
            
            db.commit()
            logger.info(f"Synced workflows. Created: {created_count}, Updated: {updated_count}.")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync workflows: {e}")
            raise
        finally:
            db.close()