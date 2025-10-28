"""
FastAPI endpoints for auto-resolution system.
"""
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from src.models.incident import (
    Incident, IncidentResolutionRequest, IncidentResolutionResponse
)
from src.models.audit import AuditLogEntry, AuditQuery
from src.models.config import AutoResolutionConfig, ConfigUpdateRequest, CategoryConfig
from src.models.admin import (
    DashboardUser, DashboardAccessRequest, DashboardAccessResponse,
    DashboardSettings, ConfigChangeLog, UserRole
)
from src.services.auto_resolution_service import AutoResolutionService
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService
from src.services.config_service import ConfigService
from src.services.dashboard_service import DashboardService

# Initialize FastAPI app
app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

# Initialize services (singleton pattern)
# In production, use dependency injection with proper lifecycle management
_audit_service = AuditService()
_notification_service = NotificationService(audit_service=_audit_service)
_config_service = ConfigService(
    audit_service=_audit_service,
    notification_service=_notification_service
)
_dashboard_service = DashboardService(
    config_service=_config_service,
    audit_service=_audit_service
)


# Dependency to get services
async def get_audit_service() -> AuditService:
    return _audit_service


async def get_notification_service() -> NotificationService:
    return _notification_service


async def get_config_service() -> ConfigService:
    return _config_service


async def get_auto_resolution_service() -> AutoResolutionService:
    config = await _config_service.get_config()
    return AutoResolutionService(
        config=config,
        audit_service=_audit_service,
        notification_service=_notification_service
    )


async def get_dashboard_service() -> DashboardService:
    return _dashboard_service


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auto-resolution-system",
        "version": "1.0.0"
    }


# Incident Resolution Endpoints
@app.post(
    "/api/v1/incidents/{incident_id}/auto-resolve",
    response_model=IncidentResolutionResponse,
    tags=["Incidents"],
    status_code=status.HTTP_200_OK
)
async def auto_resolve_incident(
    incident_id: str,
    incident: Incident,
    service: AutoResolutionService = Depends(get_auto_resolution_service)
):
    """
    Attempt to auto-resolve an incident.
    
    Requirements:
    - Incident must have confidence score ≥ 90% (or configured threshold)
    - Auto-resolution must be enabled globally and for the incident category
    - Incident must not already be resolved
    
    Returns detailed resolution response with all executed steps.
    """
    if incident.incident_id != incident_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident ID in path does not match incident data"
        )
    
    result = await service.resolve_incident(incident)
    
    if not result.success:
        # Return 200 with success=false rather than error status
        # since the operation completed successfully, just chose not to resolve
        return result
    
    return result


@app.post(
    "/api/v1/incidents/batch-resolve",
    response_model=List[IncidentResolutionResponse],
    tags=["Incidents"]
)
async def batch_auto_resolve(
    incidents: List[Incident],
    service: AutoResolutionService = Depends(get_auto_resolution_service)
):
    """
    Batch auto-resolve multiple incidents.
    
    Useful for processing a queue of incidents awaiting auto-resolution.
    """
    results = []
    
    for incident in incidents:
        result = await service.resolve_incident(incident)
        results.append(result)
    
    return results


# Configuration Endpoints
@app.get(
    "/api/v1/config",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def get_configuration(
    service: ConfigService = Depends(get_config_service)
):
    """Get current auto-resolution configuration."""
    return await service.get_config()


@app.put(
    "/api/v1/config",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def update_configuration(
    update_request: ConfigUpdateRequest,
    actor: str = "api-user",
    service: ConfigService = Depends(get_config_service)
):
    """
    Update auto-resolution configuration.
    
    Can update:
    - Global enable/disable (kill switch)
    - Default confidence threshold
    - Category-specific settings
    """
    return await service.update_config(update_request, actor=actor)


@app.post(
    "/api/v1/config/kill-switch/activate",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def activate_kill_switch(
    actor: str,
    reason: str = "Emergency activation",
    service: ConfigService = Depends(get_config_service)
):
    """
    EMERGENCY: Activate kill switch to immediately disable all auto-resolutions.
    
    Use this endpoint when:
    - Auto-resolution is causing issues
    - Manual intervention is required
    - System behavior is unexpected
    
    All pending auto-resolutions will be blocked until the kill switch is deactivated.
    """
    return await service.activate_kill_switch(actor=actor, reason=reason)


@app.post(
    "/api/v1/config/kill-switch/deactivate",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def deactivate_kill_switch(
    actor: str,
    service: ConfigService = Depends(get_config_service)
):
    """
    Deactivate kill switch to re-enable auto-resolutions.
    
    Only use after verifying that issues causing the kill switch activation
    have been resolved.
    """
    return await service.deactivate_kill_switch(actor=actor)


@app.get(
    "/api/v1/config/category/{category}",
    response_model=CategoryConfig,
    tags=["Configuration"]
)
async def get_category_config(
    category: str,
    service: ConfigService = Depends(get_config_service)
):
    """Get configuration for a specific incident category."""
    from src.models.incident import IncidentCategory
    
    try:
        cat = IncidentCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}"
        )
    
    return await service.get_category_config(cat)


# Audit Log Endpoints
@app.get(
    "/api/v1/audit",
    response_model=List[AuditLogEntry],
    tags=["Audit"]
)
async def query_audit_log(
    incident_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    service: AuditService = Depends(get_audit_service)
):
    """
    Query audit log with filters.
    
    Supports filtering by:
    - Incident ID
    - Action type
    - Date range
    
    Returns paginated results.
    """
    from src.models.audit import AuditAction
    
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type: {action}"
            )
    
    query = AuditQuery(
        incident_id=incident_id,
        action=action_enum,
        limit=limit,
        offset=offset
    )
    
    return await service.query_audit_log(query)


@app.get(
    "/api/v1/audit/incident/{incident_id}",
    response_model=List[AuditLogEntry],
    tags=["Audit"]
)
async def get_incident_audit_trail(
    incident_id: str,
    service: AuditService = Depends(get_audit_service)
):
    """
    Get complete audit trail for a specific incident.
    
    Returns all audit log entries related to the incident,
    including resolution attempts, notifications, and configuration changes.
    """
    return await service.get_incident_audit_trail(incident_id)


# Dashboard Endpoints
@app.post(
    "/api/v1/dashboard/auth",
    response_model=DashboardAccessResponse,
    tags=["Dashboard"]
)
async def authenticate_dashboard_user(
    request: DashboardAccessRequest,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Authenticate user for dashboard access.
    
    TODO: Implement proper authentication with password/token validation.
    Returns user info, permissions, and dashboard settings.
    """
    response = await service.authenticate_user(request.username)
    
    if not response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or inactive user"
        )
    
    return response


@app.get(
    "/api/v1/dashboard/config",
    response_model=AutoResolutionConfig,
    tags=["Dashboard"]
)
async def get_dashboard_config(
    user_id: str,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get configuration for dashboard display.
    Requires view_config permission.
    """
    try:
        return await service.get_dashboard_config(user_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.get(
    "/api/v1/dashboard/config-logs",
    response_model=List[ConfigChangeLog],
    tags=["Dashboard"]
)
async def get_config_change_logs(
    user_id: str,
    limit: int = 50,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get configuration change logs with user attribution.
    Shows who made what changes and when.
    Requires view_audit_log permission.
    """
    try:
        return await service.get_config_change_logs(user_id, limit)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@app.put(
    "/api/v1/dashboard/settings",
    response_model=DashboardSettings,
    tags=["Dashboard"]
)
async def update_dashboard_settings(
    user_id: str,
    settings: DashboardSettings,
    service: DashboardService = Depends(get_dashboard_service)
):
    """Update user-specific dashboard settings (theme, preferences, etc.)."""
    try:
        return await service.update_dashboard_settings(user_id, settings)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.post(
    "/api/v1/dashboard/users",
    response_model=DashboardUser,
    tags=["Dashboard"]
)
async def create_dashboard_user(
    admin_user_id: str,
    username: str,
    email: str,
    role: UserRole,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Create a new dashboard user.
    Only system administrators can create users.
    """
    try:
        return await service.create_user(admin_user_id, username, email, role)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get(
    "/api/v1/dashboard/users",
    response_model=List[DashboardUser],
    tags=["Dashboard"]
)
async def get_all_dashboard_users(
    admin_user_id: str,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get all dashboard users.
    Only system administrators can list users.
    """
    try:
        return await service.get_all_users(admin_user_id)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )
