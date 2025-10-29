from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class WidgetType(str, Enum):
    CHART = "chart"
    TABLE = "table"
    METRIC = "metric"
    GAUGE = "gauge"
    TIMELINE = "timeline"
    CUSTOM = "custom"


class WidgetStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class WidgetTemplate(BaseModel):
    template_id: str
    name: str
    description: str
    widget_type: WidgetType
    default_config: Dict[str, Any] = Field(default_factory=dict)
    schema: Dict[str, Any] = Field(default_factory=dict)


class Widget(BaseModel):
    widget_id: str
    name: str
    description: Optional[str] = None
    widget_type: WidgetType
    template_id: Optional[str] = None
    creator_id: str
    service_area: str
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, int]] = Field(default_factory=dict)
    status: WidgetStatus = WidgetStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WidgetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    widget_type: WidgetType
    template_id: Optional[str] = None
    service_area: str
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, int]] = None


class WidgetApprovalRequest(BaseModel):
    widget_id: str
    approved: bool
    reviewer_id: str
    comments: Optional[str] = None


class WidgetValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
