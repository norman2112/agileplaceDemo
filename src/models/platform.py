"""
Platform data models for legacy device support (Samsung Bada refactoring).
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PlatformType(str, Enum):
    """Supported platform types."""
    BADA = "bada"
    TIZEN = "tizen"
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"
    UNKNOWN = "unknown"


class PlatformStatus(str, Enum):
    """Platform lifecycle status."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISCONTINUED = "discontinued"
    LEGACY = "legacy"


class DevicePlatform(BaseModel):
    """Device platform information model."""
    platform_id: str = Field(..., description="Unique platform identifier")
    platform_type: PlatformType
    platform_version: Optional[str] = None
    status: PlatformStatus = PlatformStatus.ACTIVE
    support_end_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlatformIncidentMapping(BaseModel):
    """Maps incidents to specific platform configurations."""
    mapping_id: str
    incident_id: str
    platform_id: str
    device_info: Dict[str, Any] = Field(default_factory=dict)
    platform_specific_details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PlatformMigrationRequest(BaseModel):
    """Request to migrate incidents from legacy platform."""
    source_platform: PlatformType
    target_platform: PlatformType
    incident_ids: List[str] = Field(default_factory=list)
    preserve_history: bool = True
    dry_run: bool = False


class PlatformMigrationResponse(BaseModel):
    """Response for platform migration operation."""
    migration_id: str
    success: bool
    migrated_count: int
    failed_count: int
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
