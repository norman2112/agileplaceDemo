"""
Configuration models for auto-resolution system.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator
from src.models.incident import IncidentCategory


class CategoryConfig(BaseModel):
    """Configuration for a specific incident category."""
    category: IncidentCategory
    auto_resolution_enabled: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    max_retry_attempts: int = Field(default=3, ge=0, le=10)
    notification_required: bool = Field(default=True)
    
    @validator('confidence_threshold')
    def validate_threshold(cls, v):
        """Ensure threshold is reasonable (at least 0.5 for safety)."""
        if v < 0.5:
            raise ValueError('Confidence threshold should be at least 0.5 for safety')
        return v


class AutoResolutionConfig(BaseModel):
    """Global auto-resolution configuration."""
    global_enabled: bool = Field(default=True, description="Emergency kill switch - disables all auto-resolutions")
    default_confidence_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    category_configs: Dict[IncidentCategory, CategoryConfig] = Field(default_factory=dict)
    max_concurrent_resolutions: int = Field(default=10, ge=1, le=100)
    notification_recipients: List[str] = Field(default_factory=list, description="Additional notification recipients")
    
    def is_enabled_for_category(self, category: IncidentCategory) -> bool:
        """Check if auto-resolution is enabled for a specific category."""
        if not self.global_enabled:
            return False
        
        if category in self.category_configs:
            return self.category_configs[category].auto_resolution_enabled
        
        return True  # Default to enabled if no specific config exists
    
    def get_confidence_threshold(self, category: IncidentCategory) -> float:
        """Get confidence threshold for a specific category."""
        if category in self.category_configs:
            return self.category_configs[category].confidence_threshold
        
        return self.default_confidence_threshold


class ConfigUpdateRequest(BaseModel):
    """Request to update auto-resolution configuration."""
    global_enabled: Optional[bool] = None
    default_confidence_threshold: Optional[float] = Field(None, ge=0.5, le=1.0)
    category_config: Optional[CategoryConfig] = None
