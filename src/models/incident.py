"""
Incident data models for the auto-resolution system.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class IncidentStatus(str, Enum):
    """Incident status enumeration."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    AUTO_RESOLVED = "auto_resolved"
    MANUALLY_RESOLVED = "manually_resolved"
    CLOSED = "closed"


class IncidentCategory(str, Enum):
    """Incident category types."""
    NETWORK = "network"
    DATABASE = "database"
    APPLICATION = "application"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    USER_ACCESS = "user_access"
    IOS_UPGRADE = "ios_upgrade"


class IncidentType(str, Enum):
    """Incident type classification."""
    PERFORMANCE = "performance"
    SECURITY = "security"
    AVAILABILITY = "availability"
    CONFIGURATION = "configuration"
    CAPACITY = "capacity"
    CONNECTIVITY = "connectivity"


class IncidentSource(str, Enum):
    """Data source where incident was detected."""
    SERVER_LOGS = "server_logs"
    APPLICATION_LOGS = "application_logs"
    NETWORK_METRICS = "network_metrics"
    SYSTEM_METRICS = "system_metrics"
    SECURITY_ALERTS = "security_alerts"
    CUSTOM_ALERTS = "custom_alerts"


class IncidentPriority(str, Enum):
    """Incident priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionStep(BaseModel):
    """Individual resolution step."""
    step_id: str
    description: str
    action: str
    executed_at: Optional[datetime] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None


class Incident(BaseModel):
    """Core incident model."""
    incident_id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    category: IncidentCategory
    priority: IncidentPriority
    status: IncidentStatus = IncidentStatus.OPEN
    incident_type: Optional[IncidentType] = Field(None, description="Type of incident (performance, security, etc.)")
    source: Optional[IncidentSource] = Field(None, description="Data source where incident was detected")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="ML confidence score for auto-resolution (0-1)")
    detection_confidence: float = Field(0.0, ge=0.0, le=1.0, description="ML confidence in anomaly detection")
    classification_confidence: float = Field(0.0, ge=0.0, le=1.0, description="ML confidence in classification")
    auto_detected: bool = Field(default=False, description="Whether incident was auto-detected")
    created_by: str = Field(..., description="User ID of incident creator")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    detected_at: Optional[datetime] = Field(None, description="When incident was detected by AI")
    resolved_at: Optional[datetime] = None
    resolution_steps: List[ResolutionStep] = Field(default_factory=list)
    auto_resolved: bool = Field(default=False)
    tags: List[str] = Field(default_factory=list)

    @validator('confidence_score')
    def validate_confidence_score(cls, v):
        """Ensure confidence score is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence score must be between 0.0 and 1.0')
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class IncidentResolutionRequest(BaseModel):
    """Request model for incident resolution."""
    incident_id: str
    force: bool = Field(default=False, description="Force resolution even if confidence is below threshold")


class IncidentResolutionResponse(BaseModel):
    """Response model for incident resolution."""
    incident_id: str
    success: bool
    message: str
    resolution_steps: List[ResolutionStep]
    resolved_at: Optional[datetime] = None
