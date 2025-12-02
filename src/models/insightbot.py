from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RequestPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestPayload(BaseModel):
    request_id: str
    summary: str = Field(..., min_length=1, max_length=500)
    details: str = Field(..., min_length=1)
    priority: RequestPriority = RequestPriority.MEDIUM
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    updated_by: Optional[str] = None
    request_type: Optional[str] = None


class TeamMemberContext(BaseModel):
    user_id: str
    roles: List[str] = Field(default_factory=list)
    focus_tags: List[str] = Field(default_factory=list)
    current_priority_focus: RequestPriority = RequestPriority.MEDIUM
    active_request_ids: List[str] = Field(default_factory=list)


class NotificationPreference(BaseModel):
    user_id: str
    min_priority: RequestPriority = RequestPriority.MEDIUM
    relevance_threshold: float = Field(default=0.4, ge=0.0, le=1.0)
    preferred_channels: List[str] = Field(default_factory=lambda: ["in_app"])
    tracked_tags: List[str] = Field(default_factory=list)
    muted_tags: List[str] = Field(default_factory=list)
    muted_categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    max_daily_notifications: int = Field(default=25, ge=1, le=1000)
    learning_enabled: bool = True


class NotificationPreferenceUpdate(BaseModel):
    min_priority: Optional[RequestPriority] = None
    relevance_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    preferred_channels: Optional[List[str]] = None
    tracked_tags: Optional[List[str]] = None
    muted_tags: Optional[List[str]] = None
    muted_categories: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    max_daily_notifications: Optional[int] = Field(None, ge=1, le=1000)
    learning_enabled: Optional[bool] = None


class NotificationResult(BaseModel):
    user_id: str
    request_id: str
    summary: str
    priority: RequestPriority
    channel: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reason: str


class FeedbackPayload(BaseModel):
    user_id: str
    request_id: str
    was_relevant: bool
    comments: Optional[str] = Field(default=None, max_length=500)


class FeedbackResponse(BaseModel):
    user_id: str
    request_id: str
    adjustment_applied: float
    total_bias: float


class InsightBotNotificationRequest(BaseModel):
    request: RequestPayload
    team_members: List[TeamMemberContext]
