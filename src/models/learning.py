"""
Learning and feedback models for continuous AI improvement.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FeedbackType(str, Enum):
    """Types of feedback for the learning system."""
    RESOLUTION_SUCCESS = "resolution_success"
    RESOLUTION_FAILURE = "resolution_failure"
    INCORRECT_CLASSIFICATION = "incorrect_classification"
    CORRECT_CLASSIFICATION = "correct_classification"
    MANUAL_OVERRIDE = "manual_override"


class ResolutionFeedback(BaseModel):
    """
    Feedback from manual resolutions to improve AI recommendations.
    """
    feedback_id: str = Field(..., description="Unique feedback identifier")
    incident_id: str = Field(..., description="Related incident ID")
    feedback_type: FeedbackType
    original_category: str = Field(..., description="AI-predicted category")
    correct_category: Optional[str] = Field(None, description="Human-corrected category")
    original_confidence: float = Field(..., ge=0.0, le=1.0)
    resolution_successful: bool = Field(..., description="Whether resolution worked")
    human_resolution_steps: Optional[List[Dict[str, Any]]] = Field(None, description="Steps taken by human")
    feedback_notes: Optional[str] = Field(None, description="Additional context from human resolver")
    submitted_by: str = Field(..., description="User who provided feedback")
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CategoryPerformanceMetrics(BaseModel):
    """
    Performance metrics for a specific incident category.
    """
    category: str
    total_incidents: int = 0
    auto_resolved_count: int = 0
    auto_resolution_success_rate: float = Field(0.0, ge=0.0, le=1.0)
    classification_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    average_confidence: float = Field(0.0, ge=0.0, le=1.0)
    false_positive_count: int = 0  # Auto-resolved but shouldn't have been
    false_negative_count: int = 0  # Could have been auto-resolved but wasn't
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LearningMetrics(BaseModel):
    """
    Overall learning system metrics and trends.
    """
    metrics_id: str
    period_start: datetime
    period_end: datetime
    total_feedback_count: int = 0
    overall_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    classification_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    resolution_success_rate: float = Field(0.0, ge=0.0, le=1.0)
    category_metrics: Dict[str, CategoryPerformanceMetrics] = Field(default_factory=dict)
    poor_performing_categories: List[str] = Field(default_factory=list, description="Categories with accuracy < 70%")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TrainingDataset(BaseModel):
    """
    Dataset prepared for model retraining.
    """
    dataset_id: str
    name: str
    description: Optional[str] = None
    incident_count: int
    feedback_count: int
    date_range_start: datetime
    date_range_end: datetime
    categories_included: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ModelRetrainingRequest(BaseModel):
    """
    Request to retrain the AI model with new data.
    """
    dataset_id: Optional[str] = Field(None, description="Use specific dataset, or all available data if None")
    include_feedback_since: Optional[datetime] = Field(None, description="Include feedback from this date forward")
    categories_to_train: Optional[List[str]] = Field(None, description="Specific categories to retrain, or all if None")
    min_confidence_threshold: float = Field(0.7, ge=0.5, le=1.0, description="Minimum confidence for training samples")
    requested_by: str = Field(..., description="User requesting retraining")


class ModelRetrainingResult(BaseModel):
    """
    Result of model retraining operation.
    """
    training_id: str
    status: str  # success, failed, in_progress
    model_version: str
    training_samples_count: int
    validation_accuracy: float = Field(..., ge=0.0, le=1.0)
    categories_trained: List[str]
    training_started_at: datetime
    training_completed_at: Optional[datetime] = None
    performance_improvement: Optional[Dict[str, float]] = Field(None, description="Category-wise improvement")
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class EmergingPatternSuggestion(BaseModel):
    """
    Suggestion for new incident category based on emerging patterns.
    """
    suggestion_id: str
    suggested_category_name: str
    suggested_category_description: str
    incident_sample_ids: List[str] = Field(..., description="Sample incidents matching this pattern")
    pattern_frequency: int = Field(..., description="How many incidents match this pattern")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in pattern detection")
    common_keywords: List[str] = Field(default_factory=list)
    common_resolution_steps: List[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field("pending_review", description="pending_review, approved, rejected")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MonthlyPerformanceReport(BaseModel):
    """
    Monthly report showing AI system performance trends.
    """
    report_id: str
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020)
    total_incidents: int
    auto_resolved_incidents: int
    manual_resolutions: int
    overall_accuracy: float = Field(..., ge=0.0, le=1.0)
    classification_accuracy: float = Field(..., ge=0.0, le=1.0)
    resolution_success_rate: float = Field(..., ge=0.0, le=1.0)
    category_performance: Dict[str, CategoryPerformanceMetrics]
    accuracy_trend: List[float] = Field(default_factory=list, description="Daily accuracy values")
    poor_performing_categories: List[str] = Field(default_factory=list)
    emerging_patterns: List[EmergingPatternSuggestion] = Field(default_factory=list)
    feedback_received_count: int = 0
    model_retraining_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
