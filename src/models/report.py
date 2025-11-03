"""
Report data models for analytics and reporting.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Types of reports available."""
    RESOLUTION_SUMMARY = "resolution_summary"
    INCIDENT_TRENDS = "incident_trends"
    PERFORMANCE_METRICS = "performance_metrics"
    RECOMMENDATION_EFFECTIVENESS = "recommendation_effectiveness"
    CONFIGURATION_HISTORY = "configuration_history"
    USAGE_REPORT = "usage_report"


class TimeRange(str, Enum):
    """Time range options for reports."""
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    CUSTOM = "custom"


class ResolutionSummary(BaseModel):
    """Summary statistics for incident resolutions."""
    total_incidents: int = Field(default=0, ge=0)
    auto_resolved: int = Field(default=0, ge=0)
    manually_resolved: int = Field(default=0, ge=0)
    failed_attempts: int = Field(default=0, ge=0)
    auto_resolution_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    average_resolution_time_minutes: Optional[float] = None


class IncidentTrends(BaseModel):
    """Incident trends over time."""
    time_period: TimeRange
    incidents_by_category: Dict[str, int] = Field(default_factory=dict)
    incidents_by_priority: Dict[str, int] = Field(default_factory=dict)
    daily_incident_counts: List[Dict[str, Any]] = Field(default_factory=list)
    trend_direction: str = Field(default="stable")  # "increasing", "decreasing", "stable"


class PerformanceMetrics(BaseModel):
    """System performance metrics."""
    total_requests: int = Field(default=0, ge=0)
    successful_operations: int = Field(default=0, ge=0)
    failed_operations: int = Field(default=0, ge=0)
    average_response_time_ms: float = Field(default=0.0, ge=0.0)
    kill_switch_activations: int = Field(default=0, ge=0)
    uptime_percentage: float = Field(default=100.0, ge=0.0, le=100.0)


class RecommendationEffectiveness(BaseModel):
    """Effectiveness metrics for recommendations."""
    total_recommendations: int = Field(default=0, ge=0)
    recommendations_applied: int = Field(default=0, ge=0)
    successful_resolutions: int = Field(default=0, ge=0)
    average_success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    coverage_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Percentage of incidents with recommendations")


class ReportRequest(BaseModel):
    """Request parameters for generating a report."""
    report_type: ReportType
    time_range: TimeRange = TimeRange.LAST_7_DAYS
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_filter: Optional[str] = None
    priority_filter: Optional[str] = None
    department_filter: Optional[str] = None


class ReportResponse(BaseModel):
    """Response containing report data."""
    report_id: str = Field(..., description="Unique report identifier")
    report_type: ReportType
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    time_range: TimeRange
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Report data (varies by type)
    resolution_summary: Optional[ResolutionSummary] = None
    incident_trends: Optional[IncidentTrends] = None
    performance_metrics: Optional[PerformanceMetrics] = None
    recommendation_effectiveness: Optional[RecommendationEffectiveness] = None
    login_frequency: Optional[Dict[str, int]] = None
    feature_usage_statistics: Optional[Dict[str, Any]] = None
    
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
