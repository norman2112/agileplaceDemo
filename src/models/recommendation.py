"""
Resolution recommendation data models.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FeedbackRating(str, Enum):
    """Feedback rating for recommendations."""
    VERY_HELPFUL = "very_helpful"
    HELPFUL = "helpful"
    SOMEWHAT_HELPFUL = "somewhat_helpful"
    NOT_HELPFUL = "not_helpful"


class RecommendationStatus(str, Enum):
    """Status of a recommendation."""
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    APPLIED = "applied"


class ResolutionRecommendation(BaseModel):
    """Individual resolution recommendation with historical data."""
    recommendation_id: str = Field(..., description="Unique recommendation identifier")
    incident_id: str = Field(..., description="Related incident ID")
    title: str = Field(..., min_length=1, max_length=200, description="Brief recommendation title")
    description: str = Field(..., description="Detailed description of the recommended resolution")
    steps: List[str] = Field(..., min_items=1, description="Step-by-step resolution instructions")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Historical success rate (0-1)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="ML confidence in this recommendation")
    times_suggested: int = Field(default=0, ge=0, description="Number of times suggested")
    times_applied: int = Field(default=0, ge=0, description="Number of times successfully applied")
    estimated_resolution_time: Optional[int] = Field(None, description="Estimated resolution time in minutes")
    related_incidents: List[str] = Field(default_factory=list, description="IDs of similar resolved incidents")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    status: RecommendationStatus = Field(default=RecommendationStatus.SUGGESTED)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RecommendationFeedback(BaseModel):
    """Feedback on a resolution recommendation."""
    feedback_id: str = Field(..., description="Unique feedback identifier")
    recommendation_id: str
    incident_id: str
    engineer_id: str = Field(..., description="ID of the engineer providing feedback")
    rating: FeedbackRating
    was_applied: bool = Field(..., description="Whether the recommendation was actually applied")
    was_successful: bool = Field(default=False, description="Whether application led to resolution")
    resolution_time_minutes: Optional[int] = Field(None, description="Actual time to resolve in minutes")
    comments: Optional[str] = Field(None, max_length=1000, description="Additional feedback comments")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class RecommendationRequest(BaseModel):
    """Request model for getting recommendations."""
    incident_id: str
    max_recommendations: int = Field(default=5, ge=1, le=10, description="Maximum number of recommendations to return")
    min_success_rate: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum historical success rate")


class RecommendationResponse(BaseModel):
    """Response model with recommendations for an incident."""
    incident_id: str
    recommendations: List[ResolutionRecommendation] = Field(default_factory=list)
    total_found: int = Field(..., description="Total recommendations found")
    processing_time_ms: int = Field(..., description="Time taken to generate recommendations in milliseconds")
    message: str = Field(default="Recommendations generated successfully")
    
    @property
    def coverage_met(self) -> bool:
        """Check if the 75% coverage requirement is met (at least one recommendation)."""
        return len(self.recommendations) > 0


class FeedbackRequest(BaseModel):
    """Request model for submitting recommendation feedback."""
    recommendation_id: str
    incident_id: str
    engineer_id: str
    rating: FeedbackRating
    was_applied: bool
    was_successful: bool = False
    resolution_time_minutes: Optional[int] = None
    comments: Optional[str] = Field(None, max_length=1000)
