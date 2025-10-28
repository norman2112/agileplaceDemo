from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ServiceArea(str, Enum):
    NETWORK = "network"
    DATABASE = "database"
    APPLICATION = "application"
    SECURITY = "security"
    INFRASTRUCTURE = "infrastructure"
    USER_ACCESS = "user_access"


class TrendDirection(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"


class AnomalyType(str, Enum):
    SPIKE = "spike"
    DROP = "drop"
    UNUSUAL_PATTERN = "unusual_pattern"
    OUTLIER = "outlier"


class InsightType(str, Enum):
    TREND = "trend"
    ANOMALY = "anomaly"
    PREDICTION = "prediction"
    SUMMARY = "summary"


class FeedbackType(str, Enum):
    ACCURATE = "accurate"
    PARTIALLY_ACCURATE = "partially_accurate"
    INACCURATE = "inaccurate"


class TrendAnalysis(BaseModel):
    analysis_id: str = Field(..., description="Unique analysis identifier")
    service_area: ServiceArea
    metric_name: str = Field(..., description="Name of the metric being analyzed")
    direction: TrendDirection
    change_percentage: float = Field(..., description="Percentage change over period")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    time_period_days: int = Field(..., ge=1)
    data_points: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str = Field(..., description="Natural language summary of trend")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AnomalyDetection(BaseModel):
    anomaly_id: str = Field(..., description="Unique anomaly identifier")
    service_area: ServiceArea
    metric_name: str
    anomaly_type: AnomalyType
    severity: float = Field(..., ge=0.0, le=1.0, description="Anomaly severity score")
    threshold_value: float = Field(..., description="Configured threshold")
    actual_value: float = Field(..., description="Actual detected value")
    deviation_percentage: float = Field(..., description="Deviation from expected")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    explanation: str = Field(..., description="Natural language explanation")
    recommended_actions: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class Prediction(BaseModel):
    prediction_id: str = Field(..., description="Unique prediction identifier")
    service_area: ServiceArea
    metric_name: str
    predicted_value: float
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    forecast_horizon_days: int = Field(..., ge=1)
    prediction_date: datetime = Field(default_factory=datetime.utcnow)
    summary: str = Field(..., description="Natural language summary of prediction")
    factors: List[str] = Field(default_factory=list, description="Key factors influencing prediction")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class MetricSummary(BaseModel):
    summary_id: str = Field(..., description="Unique summary identifier")
    service_area: ServiceArea
    time_period_days: int
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    insights: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    summary_text: str = Field(..., description="Natural language summary")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class InsightFeedback(BaseModel):
    feedback_id: str = Field(..., description="Unique feedback identifier")
    insight_id: str = Field(..., description="ID of insight being reviewed")
    insight_type: InsightType
    user_id: str
    feedback_type: FeedbackType
    accuracy_rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AnomalyThresholdConfig(BaseModel):
    service_area: ServiceArea
    metric_name: str
    threshold_value: float
    threshold_type: str = Field(..., description="Type of threshold (e.g., 'absolute', 'percentage')")
    enabled: bool = Field(default=True)


class InsightsRequest(BaseModel):
    service_areas: Optional[List[ServiceArea]] = None
    time_period_days: int = Field(default=30, ge=1, le=365)
    include_trends: bool = Field(default=True)
    include_anomalies: bool = Field(default=True)
    include_predictions: bool = Field(default=True)


class InsightsResponse(BaseModel):
    trends: List[TrendAnalysis] = Field(default_factory=list)
    anomalies: List[AnomalyDetection] = Field(default_factory=list)
    predictions: List[Prediction] = Field(default_factory=list)
    summary: Optional[MetricSummary] = None
    processing_time_ms: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
