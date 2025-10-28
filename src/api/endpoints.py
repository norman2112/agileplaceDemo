"""
FastAPI endpoints for auto-resolution system.
"""
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from src.models.incident import (
    Incident, IncidentResolutionRequest, IncidentResolutionResponse
)
from src.models.audit import AuditLogEntry, AuditQuery
from src.models.config import AutoResolutionConfig, ConfigUpdateRequest, CategoryConfig
from src.models.learning import (
    ResolutionFeedback, LearningMetrics, CategoryPerformanceMetrics,
    TrainingDataset, ModelRetrainingRequest, ModelRetrainingResult,
    EmergingPatternSuggestion, MonthlyPerformanceReport
)
from src.services.auto_resolution_service import AutoResolutionService
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService
from src.services.config_service import ConfigService
from src.services.learning_service import LearningService
from src.services.reporting_service import ReportingService

# Initialize FastAPI app
app = FastAPI(
    title="Incident Auto-Resolution System",
    description="Automatically resolves high-confidence incidents with comprehensive auditing",
    version="1.0.0"
)

# Initialize services (singleton pattern)
# In production, use dependency injection with proper lifecycle management
_audit_service = AuditService()
_notification_service = NotificationService(audit_service=_audit_service)
_config_service = ConfigService(
    audit_service=_audit_service,
    notification_service=_notification_service
)
_learning_service = LearningService(audit_service=_audit_service)
_reporting_service = ReportingService(
    learning_service=_learning_service,
    audit_service=_audit_service
)


# Dependency to get services
async def get_audit_service() -> AuditService:
    return _audit_service


async def get_notification_service() -> NotificationService:
    return _notification_service


async def get_config_service() -> ConfigService:
    return _config_service


async def get_auto_resolution_service() -> AutoResolutionService:
    config = await _config_service.get_config()
    return AutoResolutionService(
        config=config,
        audit_service=_audit_service,
        notification_service=_notification_service
    )


async def get_learning_service() -> LearningService:
    return _learning_service


async def get_reporting_service() -> ReportingService:
    return _reporting_service


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "auto-resolution-system",
        "version": "1.0.0"
    }


# Incident Resolution Endpoints
@app.post(
    "/api/v1/incidents/{incident_id}/auto-resolve",
    response_model=IncidentResolutionResponse,
    tags=["Incidents"],
    status_code=status.HTTP_200_OK
)
async def auto_resolve_incident(
    incident_id: str,
    incident: Incident,
    service: AutoResolutionService = Depends(get_auto_resolution_service)
):
    """
    Attempt to auto-resolve an incident.
    
    Requirements:
    - Incident must have confidence score ≥ 90% (or configured threshold)
    - Auto-resolution must be enabled globally and for the incident category
    - Incident must not already be resolved
    
    Returns detailed resolution response with all executed steps.
    """
    if incident.incident_id != incident_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident ID in path does not match incident data"
        )
    
    result = await service.resolve_incident(incident)
    
    if not result.success:
        # Return 200 with success=false rather than error status
        # since the operation completed successfully, just chose not to resolve
        return result
    
    return result


@app.post(
    "/api/v1/incidents/batch-resolve",
    response_model=List[IncidentResolutionResponse],
    tags=["Incidents"]
)
async def batch_auto_resolve(
    incidents: List[Incident],
    service: AutoResolutionService = Depends(get_auto_resolution_service)
):
    """
    Batch auto-resolve multiple incidents.
    
    Useful for processing a queue of incidents awaiting auto-resolution.
    """
    results = []
    
    for incident in incidents:
        result = await service.resolve_incident(incident)
        results.append(result)
    
    return results


# Configuration Endpoints
@app.get(
    "/api/v1/config",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def get_configuration(
    service: ConfigService = Depends(get_config_service)
):
    """Get current auto-resolution configuration."""
    return await service.get_config()


@app.put(
    "/api/v1/config",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def update_configuration(
    update_request: ConfigUpdateRequest,
    actor: str = "api-user",
    service: ConfigService = Depends(get_config_service)
):
    """
    Update auto-resolution configuration.
    
    Can update:
    - Global enable/disable (kill switch)
    - Default confidence threshold
    - Category-specific settings
    """
    return await service.update_config(update_request, actor=actor)


@app.post(
    "/api/v1/config/kill-switch/activate",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def activate_kill_switch(
    actor: str,
    reason: str = "Emergency activation",
    service: ConfigService = Depends(get_config_service)
):
    """
    EMERGENCY: Activate kill switch to immediately disable all auto-resolutions.
    
    Use this endpoint when:
    - Auto-resolution is causing issues
    - Manual intervention is required
    - System behavior is unexpected
    
    All pending auto-resolutions will be blocked until the kill switch is deactivated.
    """
    return await service.activate_kill_switch(actor=actor, reason=reason)


@app.post(
    "/api/v1/config/kill-switch/deactivate",
    response_model=AutoResolutionConfig,
    tags=["Configuration"]
)
async def deactivate_kill_switch(
    actor: str,
    service: ConfigService = Depends(get_config_service)
):
    """
    Deactivate kill switch to re-enable auto-resolutions.
    
    Only use after verifying that issues causing the kill switch activation
    have been resolved.
    """
    return await service.deactivate_kill_switch(actor=actor)


@app.get(
    "/api/v1/config/category/{category}",
    response_model=CategoryConfig,
    tags=["Configuration"]
)
async def get_category_config(
    category: str,
    service: ConfigService = Depends(get_config_service)
):
    """Get configuration for a specific incident category."""
    from src.models.incident import IncidentCategory
    
    try:
        cat = IncidentCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {category}"
        )
    
    return await service.get_category_config(cat)


# Audit Log Endpoints
@app.get(
    "/api/v1/audit",
    response_model=List[AuditLogEntry],
    tags=["Audit"]
)
async def query_audit_log(
    incident_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    service: AuditService = Depends(get_audit_service)
):
    """
    Query audit log with filters.
    
    Supports filtering by:
    - Incident ID
    - Action type
    - Date range
    
    Returns paginated results.
    """
    from src.models.audit import AuditAction
    
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type: {action}"
            )
    
    query = AuditQuery(
        incident_id=incident_id,
        action=action_enum,
        limit=limit,
        offset=offset
    )
    
    return await service.query_audit_log(query)


@app.get(
    "/api/v1/audit/incident/{incident_id}",
    response_model=List[AuditLogEntry],
    tags=["Audit"]
)
async def get_incident_audit_trail(
    incident_id: str,
    service: AuditService = Depends(get_audit_service)
):
    """
    Get complete audit trail for a specific incident.
    
    Returns all audit log entries related to the incident,
    including resolution attempts, notifications, and configuration changes.
    """
    return await service.get_incident_audit_trail(incident_id)


# Learning and Feedback Endpoints
@app.post(
    "/api/v1/learning/feedback",
    response_model=ResolutionFeedback,
    tags=["Learning"],
    status_code=status.HTTP_201_CREATED
)
async def submit_resolution_feedback(
    feedback: ResolutionFeedback,
    service: LearningService = Depends(get_learning_service)
):
    """
    Submit feedback from manual resolution to improve AI recommendations.
    
    This is a critical component of the continuous learning system.
    Feedback is used to:
    - Identify classification errors
    - Learn from successful manual resolutions
    - Improve confidence scoring
    - Retrain models with real-world data
    
    Feedback types:
    - resolution_success: Auto-resolution worked correctly
    - resolution_failure: Auto-resolution failed (false positive)
    - incorrect_classification: AI misclassified the incident
    - correct_classification: AI classified correctly
    - manual_override: Human chose to resolve manually despite AI recommendation
    """
    return await service.submit_feedback(feedback)


@app.get(
    "/api/v1/learning/feedback/incident/{incident_id}",
    response_model=List[ResolutionFeedback],
    tags=["Learning"]
)
async def get_incident_feedback(
    incident_id: str,
    service: LearningService = Depends(get_learning_service)
):
    """Get all feedback submitted for a specific incident."""
    return await service.get_feedback_by_incident(incident_id)


@app.get(
    "/api/v1/learning/metrics/category/{category}",
    response_model=CategoryPerformanceMetrics,
    tags=["Learning"]
)
async def get_category_metrics(
    category: str,
    lookback_days: int = 30,
    service: LearningService = Depends(get_learning_service)
):
    """
    Get performance metrics for a specific incident category.
    
    Metrics include:
    - Auto-resolution success rate
    - Classification accuracy
    - Average confidence scores
    - False positive/negative rates
    
    Use this to identify categories that need attention or retraining.
    """
    from datetime import datetime, timedelta
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=lookback_days)
    
    return await service.calculate_category_metrics(category, start_date, end_date)


@app.get(
    "/api/v1/learning/metrics/overall",
    response_model=LearningMetrics,
    tags=["Learning"]
)
async def get_overall_metrics(
    lookback_days: int = 30,
    service: LearningService = Depends(get_learning_service)
):
    """
    Get overall learning system metrics.
    
    Provides comprehensive view of AI performance across all categories,
    including poor performers and overall accuracy trends.
    """
    from datetime import datetime, timedelta
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=lookback_days)
    
    return await service.calculate_overall_metrics(start_date, end_date)


@app.post(
    "/api/v1/learning/patterns/detect",
    response_model=List[EmergingPatternSuggestion],
    tags=["Learning"]
)
async def detect_emerging_patterns(
    min_frequency: int = 5,
    min_confidence: float = 0.7,
    lookback_days: int = 30,
    service: LearningService = Depends(get_learning_service)
):
    """
    Detect emerging incident patterns that might warrant new categories.
    
    This endpoint analyzes recent incidents to identify:
    - Common keywords and themes
    - Similar resolution patterns
    - Incidents that don't fit well into existing categories
    - Recurring issues across multiple incidents
    
    Parameters:
    - min_frequency: Minimum number of incidents to consider a pattern (default: 5)
    - min_confidence: Minimum confidence for pattern detection (default: 0.7)
    - lookback_days: How many days to analyze (default: 30)
    
    Returns suggestions for new incident categories based on detected patterns.
    """
    return await service.detect_emerging_patterns(min_frequency, min_confidence, lookback_days)


@app.post(
    "/api/v1/learning/dataset/prepare",
    response_model=TrainingDataset,
    tags=["Learning"]
)
async def prepare_training_dataset(
    name: str,
    description: Optional[str] = None,
    lookback_days: int = 90,
    categories: Optional[List[str]] = None,
    service: LearningService = Depends(get_learning_service)
):
    """
    Prepare a dataset for model retraining.
    
    Aggregates incidents and feedback into a structured training dataset.
    This is the first step before retraining the AI model.
    """
    from datetime import datetime, timedelta
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=lookback_days)
    
    return await service.prepare_training_dataset(
        name=name,
        description=description,
        start_date=start_date,
        end_date=end_date,
        categories=categories
    )


@app.post(
    "/api/v1/learning/model/retrain",
    response_model=ModelRetrainingResult,
    tags=["Learning"],
    status_code=status.HTTP_202_ACCEPTED
)
async def retrain_model(
    request: ModelRetrainingRequest,
    service: LearningService = Depends(get_learning_service)
):
    """
    Retrain the AI model with new data.
    
    This is a critical operation for continuous improvement:
    - Uses feedback from manual resolutions
    - Incorporates new incident patterns
    - Improves classification and confidence scoring
    - Validates model performance before deployment
    
    The system will:
    1. Load training data (from dataset or all available feedback)
    2. Retrain classification and confidence models
    3. Validate performance on held-out data
    4. Deploy new model version if improvement is significant
    5. Rollback if performance degrades
    
    Parameters:
    - dataset_id: Use specific dataset (optional, uses all data if not provided)
    - include_feedback_since: Include feedback from this date forward
    - categories_to_train: Specific categories to retrain (optional, all if not provided)
    - min_confidence_threshold: Minimum confidence for training samples (default: 0.7)
    - requested_by: User requesting retraining
    
    Returns immediate acknowledgment; actual training may take several minutes.
    """
    return await service.retrain_model(request)


@app.get(
    "/api/v1/learning/model/version",
    tags=["Learning"]
)
async def get_model_version(
    service: LearningService = Depends(get_learning_service)
):
    """Get current AI model version and training history."""
    version = service.get_current_model_version()
    training_history = await service.get_training_history(limit=5)
    
    return {
        "current_version": version,
        "recent_training": training_history
    }


# Reporting Endpoints
@app.post(
    "/api/v1/reports/monthly/generate",
    response_model=MonthlyPerformanceReport,
    tags=["Reports"]
)
async def generate_monthly_report(
    month: int,
    year: int,
    service: ReportingService = Depends(get_reporting_service)
):
    """
    Generate comprehensive monthly performance report.
    
    The report includes:
    - Overall accuracy metrics
    - Category-specific performance
    - Daily accuracy trends
    - Poor performing categories
    - Emerging patterns
    - Model retraining activities
    
    This fulfills the requirement for "monthly reports showing classification
    and resolution accuracy trends."
    """
    if not 1 <= month <= 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Month must be between 1 and 12"
        )
    
    if year < 2020 or year > datetime.now().year + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid year"
        )
    
    return await service.generate_monthly_report(month, year)


@app.get(
    "/api/v1/reports/monthly/{report_id}",
    response_model=MonthlyPerformanceReport,
    tags=["Reports"]
)
async def get_monthly_report(
    report_id: str,
    service: ReportingService = Depends(get_reporting_service)
):
    """Retrieve a specific monthly report by ID."""
    report = await service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found: {report_id}"
        )
    return report


@app.get(
    "/api/v1/reports/monthly/list",
    response_model=List[MonthlyPerformanceReport],
    tags=["Reports"]
)
async def list_monthly_reports(
    limit: int = 12,
    year: Optional[int] = None,
    service: ReportingService = Depends(get_reporting_service)
):
    """List available monthly reports, most recent first."""
    return await service.list_reports(limit=limit, year=year)


@app.get(
    "/api/v1/reports/trends",
    tags=["Reports"]
)
async def get_accuracy_trends(
    months: int = 6,
    service: ReportingService = Depends(get_reporting_service)
):
    """
    Get accuracy trends over multiple months.
    
    Returns:
    - monthly_overall: Overall accuracy by month
    - monthly_classification: Classification accuracy by month
    - monthly_resolution: Resolution success rate by month
    
    Useful for visualizing performance improvements over time.
    """
    return await service.get_accuracy_trends(months=months)


@app.get(
    "/api/v1/reports/category-comparison",
    response_model=Dict[str, CategoryPerformanceMetrics],
    tags=["Reports"]
)
async def get_category_performance_comparison(
    lookback_days: int = 90,
    service: ReportingService = Depends(get_reporting_service)
):
    """
    Get comparative performance metrics for all categories.
    
    This helps identify which categories need attention or retraining.
    Categories with poor performance (<70% accuracy) will be flagged.
    """
    return await service.get_category_performance_comparison(lookback_days=lookback_days)


@app.get(
    "/api/v1/reports/summary",
    tags=["Reports"]
)
async def get_performance_summary(
    service: ReportingService = Depends(get_reporting_service)
):
    """
    Get high-level performance summary for dashboards.
    
    Returns quick stats including:
    - Current model version
    - Recent accuracy metrics
    - Poor performing categories
    - Number of categories tracked
    """
    return await service.get_performance_summary()


@app.get(
    "/api/v1/reports/improvement-opportunities",
    tags=["Reports"]
)
async def get_improvement_opportunities(
    service: ReportingService = Depends(get_reporting_service)
):
    """
    Identify opportunities for AI system improvement.
    
    Returns actionable insights:
    - Categories that need more training data
    - Categories with declining accuracy
    - Emerging patterns that should become categories
    - Confidence threshold adjustments needed
    
    Use this to prioritize improvement efforts.
    """
    return await service.identify_improvement_opportunities()


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )
