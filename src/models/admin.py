"""
Admin and dashboard models for user authentication and configuration management.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User roles for dashboard access control."""
    SYSTEM_ADMIN = "system_admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class DashboardUser(BaseModel):
    """User model for dashboard access."""
    user_id: str = Field(..., description="Unique user identifier")
    username: str
    email: str
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DashboardSettings(BaseModel):
    """Dashboard-specific settings and preferences."""
    theme: str = Field(default="light", description="UI theme preference")
    notifications_enabled: bool = Field(default=True)
    audit_log_retention_days: int = Field(default=90, ge=30, le=365)
    show_advanced_settings: bool = Field(default=False)


class ConfigChangeLog(BaseModel):
    """Detailed log entry for configuration changes via dashboard."""
    log_id: str = Field(..., description="Unique log entry identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = Field(..., description="User who made the change")
    username: str
    action: str = Field(..., description="Type of configuration change")
    config_section: str = Field(..., description="Section of config modified")
    changes: Dict[str, Any] = Field(default_factory=dict)
    previous_values: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DashboardAccessRequest(BaseModel):
    """Request model for dashboard access authentication."""
    username: str
    # TODO: Add password/token authentication in full implementation
    

class DashboardAccessResponse(BaseModel):
    """Response model for dashboard access."""
    user: DashboardUser
    permissions: Dict[str, bool]
    dashboard_settings: DashboardSettings
