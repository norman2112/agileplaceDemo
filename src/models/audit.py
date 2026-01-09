"""
Audit trail models for tracking all auto-resolution actions.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Audit action types."""
    AUTO_RESOLUTION_ATTEMPTED = "auto_resolution_attempted"
    AUTO_RESOLUTION_SUCCESS = "auto_resolution_success"
    AUTO_RESOLUTION_FAILED = "auto_resolution_failed"
    AUTO_RESOLUTION_SKIPPED = "auto_resolution_skipped"
    NOTIFICATION_SENT = "notification_sent"
    KILL_SWITCH_ACTIVATED = "kill_switch_activated"
    KILL_SWITCH_DEACTIVATED = "kill_switch_deactivated"
    CONFIG_UPDATED = "config_updated"
    RECOMMENDATION_REQUESTED = "recommendation_requested"
    RECOMMENDATIONS_GENERATED = "recommendations_generated"
    RECOMMENDATION_FEEDBACK = "recommendation_feedback"
    PATTERN_ANALYSIS_STARTED = "pattern_analysis_started"
    PATTERN_MATCH_FOUND = "pattern_match_found"
    PATTERN_AUTO_RESPONSE_TRIGGERED = "pattern_auto_response_triggered"


class AuditLogEntry(BaseModel):
    """Detailed audit log entry for incident actions."""
    audit_id: str = Field(..., description="Unique audit entry identifier")
    incident_id: str = Field(..., description="Related incident ID")
    action: AuditAction
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = Field(default="system", description="System or user performing action")
    confidence_score: Optional[float] = Field(None, description="Confidence score at time of action")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional action details")
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AuditQuery(BaseModel):
    """Query parameters for audit log retrieval."""
    incident_id: Optional[str] = None
    action: Optional[AuditAction] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
