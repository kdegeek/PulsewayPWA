# app/api/scripts.py
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..database import SessionLocal
from ..models.database import Script, Device
from ..pulseway.client import PulsewayClient
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

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

@router.get("/", response_model=List[ScriptSummary])
async def get_scripts(
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None, description="Filter by platform (Windows, Linux, Mac OS)"),
    category: Optional[str] = Query(None, description="Filter by category name"),
    built_in_only: Optional[bool] = Query(None, description="Show only built-in scripts"),
    custom_only: Optional[bool] = Query(None, description="Show only custom scripts"),
    search: Optional[str] = Query(None, description="Search in script name or description"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
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

@router.get("/{script_id}", response_model=ScriptDetail)
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
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Script not found: {str(e)}")
    
    return script

@router.post("/{script_id}/execute", response_model=ScriptExecutionResponse)
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
            raise HTTPException(status_code=500, detail="Failed to start script execution")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Script execution failed: {str(e)}")

@router.get("/{script_id}/executions/{device_id}")
async def get_script_executions(
    script_id: str,
    device_id: str,
    pulseway_client: PulsewayClient = Depends(get_pulseway_client),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0)
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get script executions: {str(e)}")

@router.get("/{script_id}/executions/{device_id}/{execution_id}", response_model=ScriptExecutionDetail)
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
            except ValueError:
                pass
        
        if execution_data.get('EndTime'):
            try:
                end_time = datetime.fromisoformat(execution_data['EndTime'].replace('Z', '+00:00'))
            except ValueError:
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get script execution details: {str(e)}")

@router.get("/categories/list")
async def get_script_categories(db: Session = Depends(get_db)):
    """Get list of script categories"""
    
    categories = db.query(Script.category_name).distinct().filter(
        Script.category_name.isnot(None)
    ).all()
    
    return {"categories": [cat[0] for cat in categories if cat[0]]}

@router.get("/platforms/list")
async def get_script_platforms(db: Session = Depends(get_db)):
    """Get list of supported platforms"""
    
    # This is a bit complex due to JSON storage, so we'll return common platforms
    return {
        "platforms": ["Windows", "Linux", "Mac OS"]
    }

@router.post("/bulk-execute")
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
                
        except Exception as e:
            failed_executions.append({
                "device_id": device_id,
                "error": str(e)
            })
    
    return {
        "script_id": script_id,
        "successful_executions": execution_results,
        "failed_executions": failed_executions,
        "total_requested": len(device_identifiers),
        "total_successful": len(execution_results),
        "total_failed": len(failed_executions)
    }

@router.get("/search/{search_term}")
async def search_scripts(
    search_term: str,
    db: Session = Depends(get_db),
    limit: int = Query(20, le=100)
):
    """Search scripts by name or description"""
    
    scripts = db.query(Script).filter(
        (Script.name.ilike(f"%{search_term}%")) |
        (Script.description.ilike(f"%{search_term}%"))
    ).limit(limit).all()
    
    return scripts