"""
Pattern detection models for incident analysis.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """Types of incident patterns."""
    ERROR_MESSAGE = "error_message"
    SYSTEM_COMPONENT = "system_component"
    TIME_BASED = "time_based"
    FREQUENCY = "frequency"
    CASCADING = "cascading"


class IncidentPattern(BaseModel):
    """Represents a known incident pattern."""
    pattern_id: str = Field(..., description="Unique pattern identifier")
    name: str = Field(..., description="Human-readable pattern name")
    pattern_type: PatternType
    keywords: List[str] = Field(default_factory=list, description="Keywords to match in error messages")
    components: List[str] = Field(default_factory=list, description="System components associated with pattern")
    category: Optional[str] = None
    auto_response_enabled: bool = Field(default=True)
    min_confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    occurrence_count: int = Field(default=0, description="Number of times this pattern has been matched")


class PatternMatch(BaseModel):
    """Result of pattern matching analysis."""
    pattern_id: str
    pattern_name: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    matched_keywords: List[str] = Field(default_factory=list)
    matched_components: List[str] = Field(default_factory=list)
    analysis_time_ms: int = Field(..., description="Time taken for analysis in milliseconds")
    should_auto_respond: bool = Field(default=False)


class PatternAnalysisRequest(BaseModel):
    """Request for incident pattern analysis."""
    incident_id: str
    title: str
    description: str
    error_message: Optional[str] = None
    component: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class PatternAnalysisResponse(BaseModel):
    """Response from pattern analysis."""
    incident_id: str
    matches: List[PatternMatch] = Field(default_factory=list)
    best_match: Optional[PatternMatch] = None
    analysis_completed_at: datetime = Field(default_factory=datetime.utcnow)
    total_analysis_time_ms: int
    auto_response_triggered: bool = Field(default=False)
