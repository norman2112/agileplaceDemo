"""
Classification data models for the Incident Classification Engine.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator

from src.models.incident import IncidentCategory


class ClassificationRequest(BaseModel):
    """Request model for incident classification."""
    incident_id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., min_length=1, max_length=500)
    description: str
    metadata: Optional[dict] = Field(default=None, description="Additional context for classification")


class ClassificationResult(BaseModel):
    """Result of incident classification."""
    incident_id: str
    category: IncidentCategory
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Classification confidence (0-1)")
    alternative_categories: List[tuple[IncidentCategory, float]] = Field(
        default_factory=list,
        description="Alternative categories with confidence scores"
    )
    processing_time_ms: int = Field(..., description="Time taken to classify in milliseconds")
    model_version: str = Field(default="1.0.0", description="Version of classification model used")
    classified_at: datetime = Field(default_factory=datetime.utcnow)
    
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


class ClassificationOverride(BaseModel):
    """Manual override of automatic classification."""
    incident_id: str
    original_category: IncidentCategory
    original_confidence: float
    override_category: IncidentCategory
    override_reason: str = Field(..., min_length=1, description="Reason for manual override")
    overridden_by: str = Field(..., description="User ID who performed the override")
    overridden_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ClassificationStats(BaseModel):
    """Statistics for classification engine performance."""
    total_classifications: int = 0
    successful_classifications: int = 0
    accuracy_rate: float = Field(0.0, ge=0.0, le=1.0)
    average_confidence: float = Field(0.0, ge=0.0, le=1.0)
    average_processing_time_ms: float = 0.0
    overrides_count: int = 0
    override_rate: float = Field(0.0, ge=0.0, le=1.0)
    category_distribution: dict = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ClassificationFeedback(BaseModel):
    """Feedback on classification accuracy for model improvement."""
    feedback_id: str
    incident_id: str
    classification_id: str
    was_correct: bool
    expected_category: Optional[IncidentCategory] = None
    feedback_type: str = Field(..., description="Type: 'correct', 'incorrect', 'partially_correct'")
    comments: Optional[str] = None
    submitted_by: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
