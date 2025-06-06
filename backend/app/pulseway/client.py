# app/pulseway/client.py
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import time
import pybreaker # Added
# Import new base exceptions
from app.exceptions import ExternalAPIError, AuthenticationError, NotFoundError

logger = logging.getLogger(__name__) # structlog will find this logger

# Module-level circuit breaker for the Pulseway API
# Opens after 5 consecutive failures, resets after 60 seconds.
pulseway_api_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)

# Custom Exception Classes mapped to new hierarchy
class PulsewayClientError(ExternalAPIError): # Inherits from ExternalAPIError now
    """Base exception for Pulseway client errors. Typically network or non-HTTP errors."""
    def __init__(self, detail: str = "Pulseway client error.", status_code: int = 500):
        super().__init__(detail, status_code)

class PulsewayAPIError(ExternalAPIError): # Specific for API operational errors
    """General Pulseway API error (e.g., 400, 500 series from Pulseway)."""
    def __init__(self, detail: str = "Pulseway API error.", status_code: int = 500):
        super().__init__(detail, status_code)

class PulsewayAuthenticationError(AuthenticationError): # Inherits from our top-level AuthenticationError
    """Pulseway API Authentication Error (401)."""
    def __init__(self, detail: str = "Pulseway API authentication failed.", status_code: int = 401):
        super().__init__(detail, status_code)

class PulsewayPermissionError(AuthenticationError): # Could also be a more general ExternalAPIError with 403
    """Pulseway API Permission Error (403)."""
    def __init__(self, detail: str = "Pulseway API permission denied.", status_code: int = 403):
        super().__init__(detail, status_code) # Using AuthenticationError as base for 403 too

class PulsewayNotFoundError(NotFoundError): # Inherits from our top-level NotFoundError
    """Pulseway API Resource Not Found Error (404)."""
    def __init__(self, detail: str = "Pulseway API resource not found.", status_code: int = 404):
        super().__init__(detail, status_code)


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
    
    @pulseway_api_breaker # Decorate the method with the circuit breaker
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and circuit breaker"""
        try:
            self._rate_limit()

            url = f"{self.base_url}/{endpoint.lstrip('/')}"

            response = self.session.request(method, url, **kwargs)

            # Use status_code from the response for our custom exceptions
            # These specific errors (400,401,403,404) might not always be counted as "failures"
            # by the circuit breaker if we configure `expected_exception` on the breaker.
            # For now, they will be counted as failures if they are raised.
            if response.status_code == 400:
                logger.error(f"Pulseway API Bad Request (400): {method} {url} - Response: {response.text}")
                raise PulsewayAPIError(detail=f"Pulseway API Bad Request: {response.text}", status_code=400)
            elif response.status_code == 401:
                logger.error(f"Pulseway API Authentication Error (401): {method} {url} - Response: {response.text}")
                raise PulsewayAuthenticationError(detail=f"Pulseway API Authentication Error: {response.text}", status_code=401)
            elif response.status_code == 403:
                logger.error(f"Pulseway API Permission Error (403): {method} {url} - Response: {response.text}")
                raise PulsewayPermissionError(detail=f"Pulseway API Permission Error: {response.text}", status_code=403)
            elif response.status_code == 404:
                logger.error(f"Pulseway API Resource Not Found (404): {method} {url} - Response: {response.text}")
                raise PulsewayNotFoundError(detail=f"Pulseway API Resource Not Found: {response.text}", status_code=404)
            elif response.status_code >= 500:
                logger.error(f"Pulseway API Server Error ({response.status_code}): {method} {url} - Response: {response.text}")
                raise PulsewayAPIError(detail=f"Pulseway API Server Error ({response.status_code}): {response.text}", status_code=response.status_code)

            response.raise_for_status()  # For other 4xx errors or if non-error codes are not 2xx.

            # Check if response content is empty before trying to parse JSON
            if not response.content:
                logger.info(f"Empty response content for {method} {url}")
                return {} # Or appropriate default for empty response

            return response.json()

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during Pulseway request: {method} {url} - {e} - Response: {e.response.text if e.response else 'No response body'}")
            # Wrap HTTPError in PulsewayAPIError, preserving status code if available
            status_code = e.response.status_code if e.response is not None else 500
            # Only certain HTTP errors (like 5xx) should typically trip the circuit breaker for external API calls.
            # 4xx errors are often client errors or expected "not found/forbidden" type responses.
            # The current setup will count PulsewayAPIError (subclass of ExternalAPIError) as a failure.
            # If status_code < 500, this might not be ideal for a circuit breaker.
            # Consider adding `exclude` to CircuitBreaker or specific `expected_exception` for finer control.
            raise PulsewayAPIError(detail=f"HTTP error: {e} - {e.response.text if e.response else 'No response body'}", status_code=status_code) from e
        except requests.exceptions.RequestException as e: # Timeout, ConnectionError, etc. These are good candidates for CB failure.
            logger.error(f"Request failed during Pulseway request: {method} {url} - {e}")
            raise PulsewayClientError(detail=f"Request failed: {e}") from e
        except ValueError as e: # JSONDecodeError - API returned malformed JSON.
            logger.error(f"JSON decode failed for Pulseway response: {method} {url}: {e} - Response text: {response.text if 'response' in locals() else 'Response object not available'}")
            raise PulsewayAPIError(detail=f"JSON decode failed: {e}", status_code=500) from e
        # The pybreaker.CircuitBreakerError for an already open circuit will be raised by the decorator
        # before this method's try block is even entered. So, this internal except block for it
        # is only for other (less likely) scenarios where CircuitBreakerError might be raised inside.
        # The main handling for "circuit already open" needs to be in the calling methods (get, post, etc.).
        except pybreaker.CircuitBreakerError as e: # Should ideally not be hit if decorator handles "already open"
            logger.error(f"Unexpected CircuitBreakerError inside _make_request: {e}. Method: {method}, Endpoint: {endpoint}")
            raise PulsewayClientError(detail=f"Pulseway API circuit breaker issue: {e}", status_code=503) from e

    def _call_make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Helper to wrap calls to _make_request to handle CircuitBreakerError from the decorator."""
        try:
            return self._make_request(method, endpoint, **kwargs)
        except pybreaker.CircuitBreakerError as e:
            logger.error(f"Circuit breaker open for Pulseway API (prevented call): {e}. Method: {method}, Endpoint: {endpoint}")
            raise PulsewayClientError(detail=f"Pulseway API is temporarily unavailable (circuit breaker open): {e}", status_code=503) from e

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        return self._call_make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """POST request"""
        return self._call_make_request('POST', endpoint, json=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT request"""
        return self._call_make_request('PUT', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE request"""
        return self._call_make_request('DELETE', endpoint)
    
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