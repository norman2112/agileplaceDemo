"""
Android-specific issue models for tracking mobile platform incidents.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class AndroidSeverity(str, Enum):
    """Android issue severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AndroidIssueType(str, Enum):
    """Types of Android-specific issues."""
    CRASH = "crash"
    ANR = "anr"  # Application Not Responding
    PERFORMANCE = "performance"
    UI_RENDERING = "ui_rendering"
    NETWORK = "network"
    STORAGE = "storage"
    BATTERY_DRAIN = "battery_drain"
    MEMORY_LEAK = "memory_leak"


class DeviceInfo(BaseModel):
    """Android device information."""
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    android_version: Optional[str] = None
    api_level: Optional[int] = None
    screen_density: Optional[str] = None
    screen_resolution: Optional[str] = None


class AndroidIssue(BaseModel):
    """Android-specific issue model."""
    issue_id: str = Field(..., description="Unique Android issue identifier")
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    issue_type: AndroidIssueType
    severity: AndroidSeverity
    stack_trace: Optional[str] = None
    device_info: Optional[DeviceInfo] = None
    app_version: Optional[str] = None
    affected_users_count: int = Field(default=0, ge=0)
    occurrence_count: int = Field(default=1, ge=1)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_resolved: bool = Field(default=False)
    resolved_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, str] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AndroidIssueCreateRequest(BaseModel):
    """Request model for creating a new Android issue."""
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    issue_type: AndroidIssueType
    severity: AndroidSeverity
    stack_trace: Optional[str] = None
    device_info: Optional[DeviceInfo] = None
    app_version: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class AndroidIssueUpdateRequest(BaseModel):
    """Request model for updating an Android issue."""
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[AndroidSeverity] = None
    is_resolved: Optional[bool] = None
    tags: Optional[List[str]] = None


class AndroidIssueResponse(BaseModel):
    """Response model for Android issue operations."""
    issue_id: str
    success: bool
    message: str
