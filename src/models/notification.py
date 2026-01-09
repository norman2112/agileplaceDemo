"""
Notification models for incident resolution notifications.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    EMAIL = "email"
    IN_APP = "in_app"


class ResolutionRating(str, Enum):
    """Resolution quality rating options."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


class ResolutionNotification(BaseModel):
    """Resolution notification sent to user."""
    notification_id: str = Field(..., description="Unique notification identifier")
    incident_id: str = Field(..., description="Related incident ID")
    recipient_id: str = Field(..., description="User ID of recipient")
    channels: List[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.EMAIL, NotificationChannel.IN_APP]
    )
    subject: str
    resolution_summary: str = Field(..., description="Summary of what was fixed")
    resolution_steps: List[str] = Field(default_factory=list)
    reopen_link: str = Field(..., description="Link/token to reopen the incident")
    rating_link: str = Field(..., description="Link/token to rate the resolution")
    sent_at: datetime = Field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ReopenIncidentRequest(BaseModel):
    """Request to reopen a resolved incident."""
    incident_id: str
    user_id: str
    reason: str = Field(..., min_length=1, max_length=1000)


class ResolutionRatingRequest(BaseModel):
    """Request to rate a resolution."""
    incident_id: str
    user_id: str
    rating: ResolutionRating
    feedback: Optional[str] = Field(None, max_length=2000)


class ResolutionRatingResponse(BaseModel):
    """Response after submitting a resolution rating."""
    incident_id: str
    rating: ResolutionRating
    feedback: Optional[str] = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = "Thank you for your feedback"
