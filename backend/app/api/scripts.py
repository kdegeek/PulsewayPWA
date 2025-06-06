# app/api/scripts.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..database import SessionLocal
from ..models.database import Script, Device
from ..pulseway.client import PulsewayClient, PulsewayNotFoundError, PulsewayAPIError, PulsewayClientError # Import specific exceptions
from ..exceptions import ExternalAPIError # Base for some Pulseway errors
from pydantic import BaseModel
from datetime import datetime
from ..security import get_current_active_api_key

router = APIRouter(dependencies=[Depends(get_current_active_api_key)])

# Pydantic models for API requests/responses
class ScriptSummary(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category_name: Optional[str]
    platforms: Optional[List[str]]
    created_by: Optional[str]
    is_built_in: bool
    
    class Config:
        from_attributes = True

class ScriptDetail(ScriptSummary):
    category_id: Optional[int]
    input_variables: Optional[List[Dict]]
    output_variables: Optional[List[Dict]]
    script_items: Optional[List[Dict]]
    
    class Config:
        from_attributes = True

class ScriptExecution(BaseModel):
    device_identifier: str
    variables: Optional[List[Dict[str, Any]]] = None
    webhook_url: Optional[str] = None

class ScriptExecutionResponse(BaseModel):
    execution_id: str
    status: str
    message: str

class ScriptExecutionDetail(BaseModel):
    id: str
    start_time: datetime
    duration_in_seconds: Optional[float]
    state: str
    end_time: Optional[datetime]
    output: Optional[str]
    exit_code: Optional[str]
    variable_outputs: Optional[List[Dict]]

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get Pulseway client
def get_pulseway_client(request: Request) -> PulsewayClient:
    return request.app.state.pulseway_client

@router.get("/", response_model=List[ScriptSummary], summary="List all scripts", description="Retrieve a list of all available scripts, with optional filtering.", response_description="A list of scripts.")
async def get_scripts(
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None, description="Filter by platform (Windows, Linux, Mac OS)"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    built_in_only: Optional[bool] = Query(None, description="Show only built-in scripts"),
    custom_only: Optional[bool] = Query(None, description="Show only custom scripts"),
    search: Optional[str] = Query(None, description="Search in script name or description"),
    limit: int = Query(100, le=500, description="Maximum number of scripts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get list of scripts with optional filtering"""
    
    query = db.query(Script)
    
    # Apply filters
    if platform:
        # Filter by platform in JSON array
        # The method to query JSON varies by database.
        # For PostgreSQL, using has_key for string elements in a JSON array is common.
        # For SQLite, a LIKE query on the text representation is a common fallback.
        if db.bind.dialect.name == "sqlite":
            # Using LIKE for SQLite. Ensure platform string is quoted inside the JSON array.
            # e.g., searching for "Windows" in '["Windows", "Linux"]'
            # This is somewhat fragile but a common workaround for SQLite JSON arrays.
            query = query.filter(Script.platforms.astext.like(f'%"{platform}"%'))
        else:
            # For PostgreSQL and potentially other DBs with good JSON support
            # This checks if the platform string is an element in the JSON array.
            query = query.filter(Script.platforms.has_key(platform))
            # An alternative for some backends might be func.json_contains(Script.platforms, f'"{platform}"')
            # or specific array functions. has_key is generally for presence of a key or an element.

    if category:
        query = query.filter(Script.category_name.ilike(f"%{category}%"))
    
    if built_in_only is not None:
        query = query.filter(Script.is_built_in == built_in_only)
    
    if custom_only is not None:
        query = query.filter(Script.is_built_in == (not custom_only))
    
    if search:
        query = query.filter(
            (Script.name.ilike(f"%{search}%")) |
            (Script.description.ilike(f"%{search}%"))
        )
    
    scripts = query.offset(offset).limit(limit).all()
    return scripts

@router.get("/{script_id}", response_model=ScriptDetail, summary="Get script details", description="Retrieve detailed information about a specific script by its ID.", response_description="Detailed information about the script.")
async def get_script(
    script_id: str, 
    db: Session = Depends(get_db),
    pulseway_client: PulsewayClient = Depends(get_pulseway_client)
):
    """Get detailed information about a specific script"""
    
    # First check local database
    script = db.query(Script).filter(Script.id == script_id).first()
    
    if not script:
        # Try to get from Pulseway API
        try:
            response = pulseway_client.get_script(script_id)
            script_data = response.get('Data', {})
            
            if script_data:
                # Create a ScriptDetail response from API data
                return ScriptDetail(
                    id=script_data['Id'],
                    name=script_data['Name'],
                    description=script_data.get('Description'),
                    category_id=script_data.get('CategoryId'),
                    category_name=script_data.get('CategoryName'),
                    platforms=script_data.get('Platforms'),
                    created_by=script_data.get('CreatedBy'),
                    is_built_in=script_data.get('IsBuiltIn', False),
                    input_variables=script_data.get('InputVariables'),
                    output_variables=script_data.get('OutputVariables'),
                    script_items=script_data.get('ScriptItems')
                )
            # If script_data is empty from Pulseway, it means not found.
            raise HTTPException(status_code=404, detail="Script not found via Pulseway (no data).")
        except PulsewayNotFoundError as e:
            # Log this event if desired, then re-raise as HTTPException
            # logger.info(f"Script {script_id} not found via Pulseway client: {e.detail}")
            raise HTTPException(status_code=e.status_code, detail=e.detail) from e
        except PulsewayAPIError as e: # Catch other API errors from client
            # logger.error(f"Pulseway API error fetching script {script_id}: {e.detail}", exc_info=True)
            raise HTTPException(status_code=e.status_code, detail=f"Pulseway API error: {e.detail}") from e
        except PulsewayClientError as e: # Catch other client errors (network, etc.)
             # logger.error(f"Pulseway client error fetching script {script_id}: {e.detail}", exc_info=True)
             raise HTTPException(status_code=e.status_code, detail=f"Pulseway client error: {e.detail}") from e
        except Exception as e: # Catch any other unexpected error during Pulseway fetch
             # logger.error(f"Unexpected error fetching script {script_id} from Pulseway: {str(e)}", exc_info=True)
             raise HTTPException(status_code=500, detail=f"An unexpected error occurred while fetching from Pulseway: {str(e)}") from e
    
    # If script was found locally, it's returned here.
    # If not found locally, and Pulseway calls above didn't return or raised HTTPException,
    # this means it wasn't found anywhere.
# Removed redundant `if not script` branch as it is unreachable.

    return script

@router.post("/{script_id}/execute", response_model=ScriptExecutionResponse, summary="Execute script", description="Execute a script on a specific device.", response_description="Status of the script execution request.")
async def execute_script(
    script_id: str,
    execution_request: ScriptExecution,
    db: Session = Depends(get_db),
    pulseway_client: PulsewayClient = Depends(get_pulseway_client)
):
    """Execute a script on a specific device"""
    
    # Verify script exists
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Verify device exists and is online
    device = db.query(Device).filter(Device.identifier == execution_request.device_identifier).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if not device.is_online:
        raise HTTPException(status_code=400, detail="Device is offline")
    
    try:
        # Execute script via Pulseway API
        response = pulseway_client.run_script(
            script_id=script_id,
            device_id=execution_request.device_identifier,
            variables=execution_request.variables,
            webhook_url=execution_request.webhook_url
        )
        
        execution_data = response.get('Data', {})
        execution_id = execution_data.get('ExecutionId')
        
        if execution_id:
            return ScriptExecutionResponse(
                execution_id=execution_id,
                status="success",
                message="Script execution started successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start script execution (no execution ID returned by Pulseway)")
            
    except PulsewayClientError as e:
        # logger.error(f"Pulseway client error during script execution for {script_id} on {execution_request.device_identifier}: {e.detail}", exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e: # Catch any other unexpected error
        # logger.error(f"Unexpected error during script execution for {script_id} on {execution_request.device_identifier}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Script execution failed unexpectedly: {str(e)}")

@router.get("/{script_id}/executions/{device_id}", summary="Get script executions for a device", description="Retrieve execution history for a script on a specific device.", response_description="List of script executions.")
async def get_script_executions(
    script_id: str,
    device_id: str,
    pulseway_client: PulsewayClient = Depends(get_pulseway_client),
    limit: int = Query(20, le=100, description="Maximum number of executions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """Get execution history for a script on a specific device"""
    
    try:
        response = pulseway_client.get_script_executions(
            script_id=script_id,
            device_id=device_id,
            top=limit,
            skip=offset
        )
        
        executions_data = response.get('Data', [])
        
        return {
            "script_id": script_id,
            "device_id": device_id,
            "executions": executions_data,
            "total_count": response.get('Meta', {}).get('TotalCount', len(executions_data))
        }
        
    except PulsewayClientError as e:
        # logger.error(f"Pulseway client error getting executions for script {script_id} on {device_id}: {e.detail}", exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e:
        # logger.error(f"Unexpected error getting executions for script {script_id} on {device_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get script executions unexpectedly: {str(e)}")

@router.get("/{script_id}/executions/{device_id}/{execution_id}", response_model=ScriptExecutionDetail, summary="Get script execution details", description="Retrieve detailed information about a specific script execution.", response_description="Detailed information about the script execution.")
async def get_script_execution_details(
    script_id: str,
    device_id: str,
    execution_id: str,
    pulseway_client: PulsewayClient = Depends(get_pulseway_client)
):
    """Get detailed information about a specific script execution"""
    
    try:
        response = pulseway_client.get_script_execution_details(
            script_id=script_id,
            device_id=device_id,
            execution_id=execution_id
        )
        
        execution_data = response.get('Data', {})
        
        if not execution_data:
            raise HTTPException(status_code=404, detail="Script execution not found")
        
        # Parse timestamps
        start_time = None
        end_time = None
        
        if execution_data.get('StartTime'):
            try:
                start_time = datetime.fromisoformat(execution_data['StartTime'].replace('Z', '+00:00'))
            except ValueError: # Log parsing error if needed
                # logger.warning(f"Could not parse StartTime for script execution {execution_id}: {execution_data.get('StartTime')}")
                pass
        
        if execution_data.get('EndTime'):
            try:
                end_time = datetime.fromisoformat(execution_data['EndTime'].replace('Z', '+00:00'))
            except ValueError: # Log parsing error if needed
                # logger.warning(f"Could not parse EndTime for script execution {execution_id}: {execution_data.get('EndTime')}")
                pass
        
        return ScriptExecutionDetail(
            id=execution_data['Id'],
            start_time=start_time,
            duration_in_seconds=execution_data.get('DurationInSeconds'),
            state=execution_data['State'],
            end_time=end_time,
            output=execution_data.get('Output'),
            exit_code=execution_data.get('ExitCode'),
            variable_outputs=execution_data.get('VariableOutputs')
        )
    except PulsewayNotFoundError as e:
        # logger.info(f"Script execution details not found for script {script_id}, device {device_id}, exec {execution_id}: {e.detail}")
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except PulsewayClientError as e: # Other Pulseway errors
        # logger.error(f"Pulseway client error getting execution details for script {script_id}, device {device_id}, exec {execution_id}: {e.detail}", exc_info=True)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    except Exception as e: # Catch any other unexpected error
        # logger.error(f"Unexpected error getting execution details for script {script_id}, device {device_id}, exec {execution_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get script execution details unexpectedly: {str(e)}")

@router.get("/categories/list", summary="List script categories", description="Retrieve a list of all script categories.", response_description="A list of script categories.")
async def get_script_categories(db: Session = Depends(get_db)):
    """Get list of script categories"""
    
    categories = db.query(Script.category_name).distinct().filter(
        Script.category_name.isnot(None)
    ).all()
    
    return {"categories": [cat[0] for cat in categories if cat[0]]}

@router.get("/platforms/list", summary="List script platforms", description="Retrieve a list of supported script platforms.", response_description="A list of script platforms.")
async def get_script_platforms(db: Session = Depends(get_db)):
    """Get list of supported platforms"""
    
    # This is a bit complex due to JSON storage, so we'll return common platforms
    return {
        "platforms": ["Windows", "Linux", "Mac OS"]
    }

@router.post("/bulk-execute", summary="Bulk execute script", description="Execute a script on multiple devices simultaneously.", response_description="Results of the bulk script execution.")
async def bulk_execute_script(
    script_id: str = Body(...),
    device_identifiers: List[str] = Body(...),
    variables: Optional[List[Dict[str, Any]]] = Body(None),
    webhook_url: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    pulseway_client: PulsewayClient = Depends(get_pulseway_client)
):
    """Execute a script on multiple devices"""
    
    # Verify script exists
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    
    # Verify devices exist and are online
    devices = db.query(Device).filter(Device.identifier.in_(device_identifiers)).all()
    found_device_ids = {device.identifier for device in devices}
    missing_devices = set(device_identifiers) - found_device_ids
    
    if missing_devices:
        raise HTTPException(
            status_code=404, 
            detail=f"Devices not found: {', '.join(missing_devices)}"
        )
    
    offline_devices = [device.identifier for device in devices if not device.is_online]
    if offline_devices:
        raise HTTPException(
            status_code=400,
            detail=f"Some devices are offline: {', '.join(offline_devices)}"
        )
    
    # Execute script on each device
    execution_results = []
    failed_executions = []
    
    for device_id in device_identifiers:
        try:
            response = pulseway_client.run_script(
                script_id=script_id,
                device_id=device_id,
                variables=variables,
                webhook_url=webhook_url
            )
            
            execution_data = response.get('Data', {})
            execution_id = execution_data.get('ExecutionId')
            
            if execution_id:
                execution_results.append({
                    "device_id": device_id,
                    "execution_id": execution_id,
                    "status": "success"
                })
            else:
                failed_executions.append({
                    "device_id": device_id,
                    "error": "No execution ID returned"
                })
        except PulsewayClientError as e: # Catch specific errors from client
            # logger.warning(f"Pulseway client error during bulk execution for device {device_id}, script {script_id}: {e.detail}")
            failed_executions.append({
                "device_id": device_id,
                "error": e.detail, # Provide the error detail from the custom exception
                "status_code": e.status_code
            })
        except Exception as e: # Catch any other unexpected error for this specific device
            # logger.error(f"Unexpected error during bulk execution for device {device_id}, script {script_id}: {str(e)}", exc_info=True)
            failed_executions.append({
                "device_id": device_id,
                "error": f"Unexpected error: {str(e)}"
            })
    
    return {
        "script_id": script_id,
        "successful_executions": execution_results,
        "failed_executions": failed_executions,
        "total_requested": len(device_identifiers),
        "total_successful": len(execution_results),
        "total_failed": len(failed_executions)
    }

@router.get("/search/{search_term}", summary="Search scripts", description="Search for scripts by name or description.", response_description="A list of scripts matching the search term.")
async def search_scripts(
    search_term: str,
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100, description="Maximum number of scripts to return")
):
    """Search scripts by name or description"""
    
    scripts = db.query(Script).filter(
        (Script.name.ilike(f"%{search_term}%")) |
        (Script.description.ilike(f"%{search_term}%"))
    ).limit(limit).all()
    
    return scripts