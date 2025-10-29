from datetime import datetime, time
from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ExternalSystem(str, Enum):
    JIRA = "jira"
    SERVICENOW = "servicenow"


class DeliveryFormat(str, Enum):
    EMAIL = "email"
    DASHBOARD = "dashboard"
    BOTH = "both"


class SeverityBreakdown(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0


class CriticalIncidentHighlight(BaseModel):
    incident_id: str
    title: str
    severity: str
    system: str
    created_at: datetime
    reason: str


class DailySummaryConfig(BaseModel):
    user_id: str
    enabled: bool = True
    delivery_time: time = Field(default=time(9, 0))
    delivery_format: DeliveryFormat = DeliveryFormat.EMAIL
    systems: List[ExternalSystem] = Field(default_factory=lambda: [ExternalSystem.JIRA, ExternalSystem.SERVICENOW])
    include_trend_analysis: bool = True
    critical_incidents_only: bool = False
    email_recipients: List[str] = Field(default_factory=list)


class DailySummaryReport(BaseModel):
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime
    period_end: datetime
    total_incidents: int
    severity_breakdown: SeverityBreakdown
    trend_analysis: Optional[str] = None
    critical_incidents: List[CriticalIncidentHighlight] = Field(default_factory=list)
    systems_included: List[ExternalSystem]
    summary_text: str
