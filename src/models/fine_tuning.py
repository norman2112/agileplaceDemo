"""
Fine-tuning models for Small Language Models.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class FineTuningStatus(str, Enum):
    """Status of fine-tuning job."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModelType(str, Enum):
    """Supported small language model types."""
    GPT2 = "gpt2"
    DISTILGPT2 = "distilgpt2"
    BLOOM_560M = "bloom-560m"
    OPT_125M = "opt-125m"
    PYTHIA_160M = "pythia-160m"


class FineTuningConfig(BaseModel):
    """Configuration for fine-tuning job."""
    model_type: ModelType
    learning_rate: float = Field(default=5e-5, ge=1e-6, le=1e-3)
    batch_size: int = Field(default=8, ge=1, le=128)
    num_epochs: int = Field(default=3, ge=1, le=100)
    max_seq_length: int = Field(default=512, ge=128, le=2048)
    warmup_steps: int = Field(default=500, ge=0)
    weight_decay: float = Field(default=0.01, ge=0.0, le=1.0)
    gradient_accumulation_steps: int = Field(default=1, ge=1, le=32)
    validation_split: float = Field(default=0.1, ge=0.0, le=0.5)


class FineTuningJob(BaseModel):
    """Fine-tuning job."""
    job_id: str
    model_type: ModelType
    config: FineTuningConfig
    status: FineTuningStatus = FineTuningStatus.PENDING
    training_data_path: str
    output_model_path: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    error_message: Optional[str] = None


class FineTuningRequest(BaseModel):
    """Request to create fine-tuning job."""
    model_type: ModelType
    training_data_path: str
    config: Optional[FineTuningConfig] = None
    use_case: Optional[str] = None


class FineTuningMetrics(BaseModel):
    """Training metrics for fine-tuning job."""
    job_id: str
    epoch: int
    train_loss: float
    eval_loss: Optional[float] = None
    learning_rate: float
    timestamp: datetime
