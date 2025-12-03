"""
InsightBot data models for AI-driven solution suggestions.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models.incident import Incident


class SuggestionConfidenceLabel(str, Enum):
    """Readable label for confidence tiers."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SuggestionQuality(str, Enum):
    """Agent-provided quality signal for InsightBot suggestions."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class SolutionSuggestion(BaseModel):
    """Individual AI-generated solution suggestion."""
    suggestion_id: str = Field(..., description="Unique suggestion identifier")
    incident_id: str
    title: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., description="High-level overview of the proposed fix")
    steps: List[str] = Field(..., min_items=1, description="Step-by-step remediation plan")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model confidence (0-1)")
    confidence_label: SuggestionConfidenceLabel
    source_pattern_id: str = Field(..., description="Reference to the matched historical pattern")
    related_incidents: List[str] = Field(default_factory=list)
    estimated_resolution_time: Optional[int] = Field(
        None,
        description="Estimated minutes required to execute the solution"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SuggestionRequest(BaseModel):
    """Request for InsightBot solution suggestions."""
    incident: Incident
    max_suggestions: int = Field(default=3, ge=1, le=10)


class SuggestionResponse(BaseModel):
    """Response payload for InsightBot solution suggestions."""
    incident_id: str
    solutions: List[SolutionSuggestion] = Field(default_factory=list)
    total_solutions: int
    scanned_historical_records: int
    processing_time_ms: int


class SuggestionFeedbackRequest(BaseModel):
    """Feedback provided by agents on InsightBot suggestions."""
    suggestion_id: str
    pattern_id: str
    incident_id: str
    agent_id: str
    quality: SuggestionQuality
    was_helpful: bool = Field(default=True)
    was_applied: bool = Field(default=False)
    resolution_time_minutes: Optional[int] = Field(
        None,
        description="Actual minutes spent if suggestion was applied"
    )
    comments: Optional[str] = Field(None, max_length=1000)


class SuggestionFeedback(BaseModel):
    """Stored feedback record with learning metadata."""
    feedback_id: str = Field(..., description="Unique feedback identifier")
    suggestion_id: str
    pattern_id: str
    incident_id: str
    agent_id: str
    quality: SuggestionQuality
    was_helpful: bool
    was_applied: bool
    resolution_time_minutes: Optional[int] = None
    comments: Optional[str] = Field(None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
