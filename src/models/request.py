from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RequestPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequestType(str, Enum):
    FEATURE = "feature"
    DEFECT = "defect"
    TASK = "task"
    INCIDENT = "incident"
    SERVICE = "service"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    SMS = "sms"
    IN_APP = "in_app"


class WorkRequest(BaseModel):
    request_id: str
    summary: str
    description: str
    priority: RequestPriority = RequestPriority.MEDIUM
    request_type: RequestType = RequestType.TASK
    tags: List[str] = Field(default_factory=list)
    service_area: Optional[str] = None
    requested_by: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, str] = Field(default_factory=dict)


class NotificationPreference(BaseModel):
    user_id: str
    channels: List[NotificationChannel] = Field(
        default_factory=lambda: [NotificationChannel.EMAIL]
    )
    priority_threshold: RequestPriority = RequestPriority.MEDIUM
    tag_weights: Dict[str, float] = Field(default_factory=dict)
    service_area_focus: List[str] = Field(default_factory=list)
    mute_until: Optional[datetime] = None


class NotificationFeedback(BaseModel):
    user_id: str
    request_id: str
    relevant: bool
    tags: List[str] = Field(default_factory=list)
    priority: RequestPriority = RequestPriority.MEDIUM
    comments: Optional[str] = None

