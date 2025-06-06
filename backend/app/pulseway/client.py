# app/pulseway/client.py
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)

class PulsewayClient:
    """Pulseway REST API Client"""
    
    def __init__(self, base_url: str, token_id: str, token_secret: str):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(token_id, token_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
    
    def _rate_limit(self):
        """Simple rate limiting"""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling"""
        self._rate_limit()
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            raise
        except ValueError as e:
            logger.error(f"JSON decode failed: {e}")
            raise
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request"""
        return self._make_request('POST', endpoint, json=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request"""
        return self._make_request('PUT', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request"""
        return self._make_request('DELETE', endpoint)
    
    # Device Methods
    def get_devices(self, top: int = 100, skip: int = 0, filters: Optional[str] = None) -> Dict[str, Any]:
        """Get all devices"""
        params = {'$top': top, '$skip': skip}
        if filters:
            params['$filter'] = filters
        return self.get('devices', params=params)
    
    def get_device(self, device_id: str) -> Dict[str, Any]:
        """Get specific device details"""
        return self.get(f'devices/{device_id}')
    
    def get_device_notifications(self, device_id: str, top: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get device notifications"""
        params = {'$top': top, '$skip': skip}
        return self.get(f'devices/{device_id}/notifications', params=params)
    
    def get_device_assets(self, device_id: str) -> Dict[str, Any]:
        """Get device assets"""
        return self.get(f'assets/{device_id}')
    
    def get_device_custom_fields(self, device_id: str) -> Dict[str, Any]:
        """Get device custom fields"""
        return self.get(f'devices/{device_id}/customfields')
    
    def get_antivirus_status(self, device_id: str) -> Dict[str, Any]:
        """Get device antivirus status"""
        return self.get(f'devices/{device_id}/antivirus')
    
    # Asset Methods
    def get_assets(self, top: int = 100, skip: int = 0, filters: Optional[str] = None) -> Dict[str, Any]:
        """Get all assets"""
        params = {'$top': top, '$skip': skip}
        if filters:
            params['$filter'] = filters
        return self.get('assets', params=params)
    
    # Organization Methods
    def get_organizations(self, top: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get all organizations"""
        params = {'$top': top, '$skip': skip}
        return self.get('organizations', params=params)
    
    def get_organization(self, org_id: str) -> Dict[str, Any]:
        """Get specific organization"""
        return self.get(f'organizations/{org_id}')
    
    # Site Methods
    def get_sites(self, top: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get all sites"""
        params = {'$top': top, '$skip': skip}
        return self.get('sites', params=params)
    
    def get_site(self, site_id: str) -> Dict[str, Any]:
        """Get specific site"""
        return self.get(f'sites/{site_id}')
    
    # Group Methods
    def get_groups(self, top: int = 100, skip: int = 0) -> Dict[str, Any]:
        """Get all groups"""
        params = {'$top': top, '$skip': skip}
        return self.get('groups', params=params)
    
    def get_group(self, group_id: str) -> Dict[str, Any]:
        """Get specific group"""
        return self.get(f'groups/{group_id}')
    
    # Script Methods
    def get_scripts(self, top: int = 100, skip: int = 0, filters: Optional[str] = None) -> Dict[str, Any]:
        """Get all scripts"""
        params = {'$top': top, '$skip': skip}
        if filters:
            params['$filter'] = filters
        return self.get('automation/scripts', params=params)
    
    def get_script(self, script_id: str) -> Dict[str, Any]:
        """Get specific script"""
        return self.get(f'automation/scripts/{script_id}')
    
    def run_script(self, script_id: str, device_id: str, variables: Optional[List[Dict]] = None, 
                   webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Run script on device"""
        data = {'DeviceIdentifier': device_id}
        if variables:
            data['Variables'] = variables
        if webhook_url:
            data['WebhookUrl'] = webhook_url
        return self.post(f'automation/scripts/{script_id}/run', data=data)
    
    def get_script_executions(self, script_id: str, device_id: str, top: int = 50, skip: int = 0) -> Dict[str, Any]:
        """Get script execution history"""
        params = {'$top': top, '$skip': skip}
        return self.get(f'automation/scripts/{script_id}/device/{device_id}/executions', params=params)
    
    def get_script_execution_details(self, script_id: str, device_id: str, execution_id: str) -> Dict[str, Any]:
        """Get script execution details"""
        return self.get(f'automation/scripts/{script_id}/device/{device_id}/executions/{execution_id}')
    
    # Task Methods
    def get_tasks(self, top: int = 100, skip: int = 0, filters: Optional[str] = None) -> Dict[str, Any]:
        """Get all tasks"""
        params = {'$top': top, '$skip': skip}
        if filters:
            params['$filter'] = filters
        return self.get('automation/tasks', params=params)
    
    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get specific task"""
        return self.get(f'automation/tasks/{task_id}')
    
    def run_task(self, task_id: str, device_ids: Optional[List[str]] = None, 
                 webhook_url: Optional[str] = None) -> Dict[str, Any]:
        """Run task on devices"""
        data = {}
        if device_ids:
            data['DeviceIdentifiers'] = device_ids
        if webhook_url:
            data['WebhookUrl'] = webhook_url
        return self.post(f'automation/tasks/{task_id}/run', data=data)
    
    # Workflow Methods
    def get_workflows(self, top: int = 100, skip: int = 0, filters: Optional[str] = None) -> Dict[str, Any]:
        """Get all workflows"""
        params = {'$top': top, '$skip': skip}
        if filters:
            params['$filter'] = filters
        return self.get('automation/workflows', params=params)
    
    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Get specific workflow"""
        return self.get(f'automation/workflows/{workflow_id}')
    
    def run_workflow(self, workflow_id: str, device_ids: Optional[List[str]] = None,
                     webhook_url: Optional[str] = None, variable_overrides: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Run workflow"""
        data = {}
        if device_ids:
            data['DeviceIdentifiers'] = device_ids
        if webhook_url:
            data['WebhookUrl'] = webhook_url
        if variable_overrides:
            data['ConstantVariableOverrides'] = variable_overrides
        return self.post(f'automation/workflows/{workflow_id}/run', data=data)
    
    # Notification Methods
    def get_notifications(self, top: int = 100, skip: int = 0, filters: Optional[str] = None) -> Dict[str, Any]:
        """Get all notifications"""
        params = {'$top': top, '$skip': skip}
        if filters:
            params['$filter'] = filters
        return self.get('notifications', params=params)
    
    def get_notification(self, notification_id: str) -> Dict[str, Any]:
        """Get specific notification"""
        return self.get(f'notifications/{notification_id}')
    
    def create_notification(self, instance_id: str, title: str, message: Optional[str] = None,
                          priority: str = "Normal") -> Dict[str, Any]:
        """Create notification"""
        data = {
            'InstanceId': instance_id,
            'Title': title,
            'Priority': priority
        }
        if message:
            data['Message'] = message
        return self.post('notifications', data=data)
    
    def delete_notification(self, notification_id: str) -> Dict[str, Any]:
        """Delete notification"""
        return self.delete(f'notifications/{notification_id}')
    
    # Environment Methods
    def get_environment(self) -> Dict[str, Any]:
        """Get environment information"""
        return self.get('environment')
    
    # Health check
    def health_check(self) -> bool:
        """Check if API is accessible"""
        try:
            response = self.get_environment()
            return response.get('Meta', {}).get('ResponseCode') == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False