"""
Fine-tuning service for Small Language Models.
"""
import logging
from typing import List, Optional
from datetime import datetime
import uuid

from src.models.fine_tuning import (
    FineTuningJob, FineTuningRequest, FineTuningConfig,
    FineTuningStatus, FineTuningMetrics, ModelType
)

logger = logging.getLogger(__name__)


class FineTuningService:
    """
    Service for managing SLM fine-tuning operations.
    
    Features:
    - Job creation and management
    - Training orchestration
    - Metrics tracking
    - Model deployment
    """
    
    def __init__(self):
        self._jobs = {}
        self._metrics = {}
    
    async def create_job(
        self,
        request: FineTuningRequest,
        user_id: str
    ) -> FineTuningJob:
        """
        Create a new fine-tuning job.
        
        Args:
            request: Fine-tuning job request
            user_id: User creating the job
            
        Returns:
            Created fine-tuning job
        """
        job_id = str(uuid.uuid4())
        
        config = request.config or FineTuningConfig(model_type=request.model_type)
        
        job = FineTuningJob(
            job_id=job_id,
            model_type=request.model_type,
            config=config,
            status=FineTuningStatus.PENDING,
            training_data_path=request.training_data_path,
            created_at=datetime.utcnow(),
            created_by=user_id
        )
        
        self._jobs[job_id] = job
        logger.info(f"Created fine-tuning job {job_id} for user {user_id}")
        
        return job
    
    async def get_job(self, job_id: str) -> Optional[FineTuningJob]:
        """Get fine-tuning job by ID."""
        return self._jobs.get(job_id)
    
    async def list_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[FineTuningStatus] = None
    ) -> List[FineTuningJob]:
        """
        List fine-tuning jobs with optional filtering.
        
        Args:
            user_id: Filter by user
            status: Filter by status
            
        Returns:
            List of fine-tuning jobs
        """
        jobs = list(self._jobs.values())
        
        if user_id:
            jobs = [j for j in jobs if j.created_by == user_id]
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)
    
    async def start_job(self, job_id: str) -> FineTuningJob:
        """
        Start a fine-tuning job.
        
        Args:
            job_id: Job ID to start
            
        Returns:
            Updated job
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status != FineTuningStatus.PENDING:
            raise ValueError(f"Job {job_id} cannot be started in status {job.status}")
        
        job.status = FineTuningStatus.RUNNING
        job.started_at = datetime.utcnow()
        
        logger.info(f"Started fine-tuning job {job_id}")
        
        return job
    
    async def update_job_metrics(
        self,
        job_id: str,
        metrics: FineTuningMetrics
    ) -> FineTuningJob:
        """
        Update job training metrics.
        
        Args:
            job_id: Job ID
            metrics: Training metrics
            
        Returns:
            Updated job
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.metrics = {
            "epoch": metrics.epoch,
            "train_loss": metrics.train_loss,
            "eval_loss": metrics.eval_loss or 0.0,
            "learning_rate": metrics.learning_rate
        }
        
        if job_id not in self._metrics:
            self._metrics[job_id] = []
        self._metrics[job_id].append(metrics)
        
        return job
    
    async def complete_job(
        self,
        job_id: str,
        output_model_path: str
    ) -> FineTuningJob:
        """
        Mark job as completed.
        
        Args:
            job_id: Job ID
            output_model_path: Path to fine-tuned model
            
        Returns:
            Updated job
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = FineTuningStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.output_model_path = output_model_path
        
        logger.info(f"Completed fine-tuning job {job_id}")
        
        return job
    
    async def fail_job(
        self,
        job_id: str,
        error_message: str
    ) -> FineTuningJob:
        """
        Mark job as failed.
        
        Args:
            job_id: Job ID
            error_message: Error description
            
        Returns:
            Updated job
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        job.status = FineTuningStatus.FAILED
        job.completed_at = datetime.utcnow()
        job.error_message = error_message
        
        logger.error(f"Fine-tuning job {job_id} failed: {error_message}")
        
        return job
    
    async def cancel_job(self, job_id: str) -> FineTuningJob:
        """
        Cancel a running job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Updated job
        """
        job = self._jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        if job.status not in [FineTuningStatus.PENDING, FineTuningStatus.RUNNING]:
            raise ValueError(f"Job {job_id} cannot be cancelled in status {job.status}")
        
        job.status = FineTuningStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        
        logger.info(f"Cancelled fine-tuning job {job_id}")
        
        return job
    
    async def get_job_metrics(self, job_id: str) -> List[FineTuningMetrics]:
        """
        Get training metrics for a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of metrics
        """
        return self._metrics.get(job_id, [])
