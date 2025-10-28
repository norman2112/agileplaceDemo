"""
BMC data models for integration with BMC systems.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class BMCRecordStatus(str, Enum):
    """BMC record status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    RESOLVED = "resolved"
    CLOSED = "closed"


class BMCRecord(BaseModel):
    """
    Core BMC record model.
    
    Represents a record from BMC systems that can be processed
    by the auto-resolution system.
    """
    record_id: str = Field(..., description="Unique BMC record identifier")
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    status: BMCRecordStatus = BMCRecordStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict, description="Additional BMC metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BMCRecordRequest(BaseModel):
    """Request model for creating/updating BMC records."""
    title: str = Field(..., min_length=1)
    description: str
    metadata: Optional[dict] = None


class BMCRecordResponse(BaseModel):
    """Response model for BMC record operations."""
    record_id: str
    success: bool
    message: str
    record: Optional[BMCRecord] = None
