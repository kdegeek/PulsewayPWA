# app/services/data_sync.py
import asyncio
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
            # Get all organizations from API
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_organizations
            )
            
            organizations_data = response.get('Data', [])
            
            # Clear existing organizations
            db.query(Organization).delete()
            
            # Insert updated organizations
            for org_data in organizations_data:
                organization = Organization(
                    id=org_data['Id'],
                    name=org_data['Name'],
                    has_custom_fields=org_data.get('HasCustomFields', False),
                    psa_mapping_id=org_data.get('PsaMappingId'),
                    psa_mapping_type=org_data.get('PsaMappingType')
                )
                db.add(organization)
            
            db.commit()
            logger.info(f"Synced {len(organizations_data)} organizations")
            
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_sites
            )
            
            sites_data = response.get('Data', [])
            
            # Clear existing sites
            db.query(Site).delete()
            
            # Insert updated sites
            for site_data in sites_data:
                site = Site(
                    id=site_data['Id'],
                    name=site_data['Name'],
                    parent_id=site_data.get('ParentId'),
                    parent_name=site_data.get('ParentName'),
                    has_custom_fields=site_data.get('HasCustomFields', False),
                    psa_mapping_id=site_data.get('PsaMappingId'),
                    psa_integration_type=site_data.get('PsaIntegrationType'),
                    contact_info=site_data.get('ContactInformation')
                )
                db.add(site)
            
            db.commit()
            logger.info(f"Synced {len(sites_data)} sites")
            
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_groups
            )
            
            groups_data = response.get('Data', [])
            
            # Clear existing groups
            db.query(Group).delete()
            
            # Insert updated groups
            for group_data in groups_data:
                group = Group(
                    id=group_data['Id'],
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
            
            db.commit()
            logger.info(f"Synced {len(groups_data)} groups")
            
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
            
            # Clear existing devices
            db.query(Device).delete()
            
            # Insert updated devices
            for device_data in all_devices:
                # Get detailed device info
                try:
                    device_details = await asyncio.get_event_loop().run_in_executor(
                        None, self.client.get_device, device_data['Identifier']
                    )
                    detailed_data = device_details.get('Data', {})
                except Exception as e:
                    logger.warning(f"Failed to get details for device {device_data['Identifier']}: {e}")
                    detailed_data = {}
                
                # Parse last seen online
                last_seen = None
                if detailed_data.get('LastSeenOnline'):
                    try:
                        last_seen = datetime.fromisoformat(detailed_data['LastSeenOnline'].replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                device = Device(
                    identifier=device_data['Identifier'],
                    name=device_data['Name'],
                    description=detailed_data.get('Description'),
                    computer_type=detailed_data.get('ComputerType'),
                    is_online=detailed_data.get('IsOnline', False),
                    is_agent_installed=device_data.get('IsAgentInstalled', False),
                    is_mdm_enrolled=device_data.get('IsMdmEnrolled', False),
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
                    group_id=device_data.get('GroupId'),
                    group_name=device_data.get('GroupName'),
                    site_id=device_data.get('SiteId'),
                    site_name=device_data.get('SiteName'),
                    organization_id=device_data.get('OrganizationId'),
                    organization_name=device_data.get('OrganizationName'),
                    last_seen_online=last_seen
                )
                db.add(device)
            
            db.commit()
            logger.info(f"Synced {len(all_devices)} devices")
            
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
            # Get all devices to sync their assets
            devices = db.query(Device).all()
            
            # Clear existing assets
            db.query(DeviceAsset).delete()
            
            asset_count = 0
            for device in devices:
                try:
                    response = await asyncio.get_event_loop().run_in_executor(
                        None, self.client.get_device_assets, device.identifier
                    )
                    
                    asset_data = response.get('Data', {})
                    
                    if asset_data:
                        device_asset = DeviceAsset(
                            device_identifier=device.identifier,
                            tags=asset_data.get('Tags'),
                            asset_info=asset_data.get('AssetInfo'),
                            public_ip_address=asset_data.get('PublicIpAddress'),
                            ip_addresses=asset_data.get('IpAddresses'),
                            disks=asset_data.get('Disks'),
                            installed_software=asset_data.get('InstalledSoftware')
                        )
                        db.add(device_asset)
                        asset_count += 1
                
                except Exception as e:
                    logger.warning(f"Failed to get assets for device {device.identifier}: {e}")
                    continue
            
            db.commit()
            logger.info(f"Synced {asset_count} device assets")
            
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_notifications, 500, 0  # Get more recent notifications
            )
            
            notifications_data = response.get('Data', [])
            
            # Clear existing notifications
            db.query(Notification).delete()
            
            # Insert updated notifications
            for notif_data in notifications_data:
                # Parse datetime
                notification_datetime = None
                if notif_data.get('DateTime'):
                    try:
                        if isinstance(notif_data['DateTime'], str):
                            notification_datetime = datetime.fromisoformat(notif_data['DateTime'].replace('Z', '+00:00'))
                        else:
                            # Handle Unix timestamp
                            notification_datetime = datetime.fromtimestamp(notif_data['DateTime'], tz=timezone.utc)
                    except (ValueError, OSError):
                        pass
                
                notification = Notification(
                    id=notif_data['Id'],
                    message=notif_data['Message'],
                    datetime=notification_datetime,
                    priority=notif_data.get('Priority', 'Normal'),
                    read=False  # Default to unread
                )
                db.add(notification)
            
            db.commit()
            logger.info(f"Synced {len(notifications_data)} notifications")
            
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_scripts
            )
            
            scripts_data = response.get('Data', [])
            
            # Clear existing scripts
            db.query(Script).delete()
            
            # Insert updated scripts
            for script_data in scripts_data:
                script = Script(
                    id=script_data['Id'],
                    name=script_data['Name'],
                    description=script_data.get('Description'),
                    category_id=script_data.get('CategoryId'),
                    category_name=script_data.get('CategoryName'),
                    platforms=script_data.get('Platforms'),
                    created_by=script_data.get('CreatedBy'),
                    is_built_in=script_data.get('IsBuiltIn', False)
                )
                db.add(script)
            
            db.commit()
            logger.info(f"Synced {len(scripts_data)} scripts")
            
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_tasks
            )
            
            tasks_data = response.get('Data', [])
            
            # Clear existing tasks
            db.query(Task).delete()
            
            # Insert updated tasks
            for task_data in tasks_data:
                # Parse updated_at
                updated_at = None
                if task_data.get('UpdatedAt'):
                    try:
                        updated_at = datetime.fromisoformat(task_data['UpdatedAt'].replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                task = Task(
                    id=task_data['Id'],
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
                    task_updated_at=updated_at
                )
                db.add(task)
            
            db.commit()
            logger.info(f"Synced {len(tasks_data)} tasks")
            
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
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_workflows
            )
            
            workflows_data = response.get('Data', [])
            
            # Clear existing workflows
            db.query(Workflow).delete()
            
            # Insert updated workflows
            for workflow_data in workflows_data:
                # Parse updated_at
                updated_at = None
                if workflow_data.get('UpdatedAt'):
                    try:
                        updated_at = datetime.fromisoformat(workflow_data['UpdatedAt'].replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                workflow = Workflow(
                    id=workflow_data['Id'],
                    name=workflow_data['Name'],
                    description=workflow_data.get('Description'),
                    is_enabled=workflow_data.get('IsEnabled', True),
                    trigger_type=workflow_data.get('TriggerType'),
                    trigger_sub_type=workflow_data.get('TriggerSubType'),
                    context_type=workflow_data.get('ContextType'),
                    context_item_id=workflow_data.get('ContextItemId'),
                    workflow_updated_at=updated_at
                )
                db.add(workflow)
            
            db.commit()
            logger.info(f"Synced {len(workflows_data)} workflows")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to sync workflows: {e}")
            raise
        finally:
            db.close()