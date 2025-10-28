"""
FastAPI endpoints for auto-resolution system.
"""
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from src.models.incident import (
    Incident, IncidentResolutionRequest, IncidentResolutionResponse
)
from src.models.audit import AuditLogEntry, AuditQuery
from src.models.config import AutoResolutionConfig, ConfigUpdateRequest, CategoryConfig
from src.models.recommendation import (
    ResolutionRecommendation, RecommendationRequest, RecommendationResponse,
    FeedbackRequest, RecommendationFeedback
)
from src.models.classification import (
    ClassificationRequest, ClassificationResult, ClassificationOverride,
    ClassificationStats, ClassificationFeedback
)
from src.services.auto_resolution_service import AutoResolutionService
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService
from src.services.config_service import ConfigService
from src.services.recommendation_service import RecommendationService
from src.services.classification_service import ClassificationService

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
_recommendation_service = RecommendationService(audit_service=_audit_service)
_classification_service = ClassificationService(audit_service=_audit_service)


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


async def get_recommendation_service() -> RecommendationService:
    return _recommendation_service


async def get_classification_service() -> ClassificationService:
    return _classification_service


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


# Resolution Recommendation Endpoints
@app.post(
    "/api/v1/incidents/{incident_id}/recommendations",
    response_model=RecommendationResponse,
    tags=["Recommendations"],
    status_code=status.HTTP_200_OK
)
async def get_recommendations_for_incident(
    incident_id: str,
    incident: Incident,
    request: Optional[RecommendationRequest] = None,
    service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Get resolution recommendations for a classified incident.
    
    Requirements:
    - Returns suggestions within 10 seconds
    - Provides step-by-step resolution instructions
    - Ranks suggestions by historical success rate
    - Target: Suggest at least one resolution for 75% of classified incidents
    
    Returns ranked list of resolution recommendations based on historical data.
    """
    if incident.incident_id != incident_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incident ID in path does not match incident data"
        )
    
    max_recommendations = request.max_recommendations if request else 5
    min_success_rate = request.min_success_rate if request else 0.5
    
    response = await service.get_recommendations(
        incident=incident,
        max_recommendations=max_recommendations,
        min_success_rate=min_success_rate
    )
    
    return response


@app.post(
    "/api/v1/recommendations/feedback",
    response_model=RecommendationFeedback,
    tags=["Recommendations"],
    status_code=status.HTTP_201_CREATED
)
async def submit_recommendation_feedback(
    feedback: FeedbackRequest,
    service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Submit feedback on recommendation effectiveness.
    
    Engineers can provide feedback on:
    - Whether the recommendation was helpful
    - Whether it was applied
    - Whether it successfully resolved the incident
    - How long resolution took
    - Additional comments
    
    This feedback is used to improve future recommendations and update success rates.
    """
    result = await service.submit_feedback(feedback)
    return result


@app.get(
    "/api/v1/recommendations/{recommendation_id}/stats",
    response_model=dict,
    tags=["Recommendations"]
)
async def get_recommendation_stats(
    recommendation_id: str,
    service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Get aggregated statistics for a specific recommendation.
    
    Returns:
    - Total feedback count
    - Times applied
    - Success rate
    - Average rating
    """
    stats = await service.get_feedback_stats(recommendation_id)
    return stats


@app.get(
    "/api/v1/incidents/{incident_id}/feedback",
    response_model=List[RecommendationFeedback],
    tags=["Recommendations"]
)
async def get_incident_feedback(
    incident_id: str,
    service: RecommendationService = Depends(get_recommendation_service)
):
    """
    Get all feedback for recommendations related to a specific incident.
    
    Useful for tracking which recommendations were tried and their outcomes.
    """
    feedback_list = await service.get_feedback_for_incident(incident_id)
    return feedback_list


# Classification Endpoints
@app.post(
    "/api/v1/incidents/classify",
    response_model=ClassificationResult,
    tags=["Classification"],
    status_code=status.HTTP_200_OK
)
async def classify_incident(
    request: ClassificationRequest,
    service: ClassificationService = Depends(get_classification_service)
):
    """
    Classify an incident into a predefined category.
    
    Requirements:
    - Correctly classify at least 80% of incoming incidents
    - Classification within 5 seconds of ticket creation
    - Display confidence score alongside category
    - Support for 20+ predefined incident categories
    
    Returns classification result with category, confidence score, and alternatives.
    """
    result = await service.classify_incident(request)
    return result


@app.post(
    "/api/v1/incidents/{incident_id}/classify-override",
    response_model=ClassificationOverride,
    tags=["Classification"],
    status_code=status.HTTP_200_OK
)
async def override_classification(
    incident_id: str,
    original_category: str,
    original_confidence: float,
    override_category: str,
    override_reason: str,
    overridden_by: str,
    service: ClassificationService = Depends(get_classification_service)
):
    """
    Manually override automatic incident classification.
    
    This endpoint supports the manual override requirement, allowing
    support staff to correct misclassifications and improve the model.
    
    Args:
        incident_id: Incident identifier
        original_category: Original automatic classification
        original_confidence: Original confidence score
        override_category: Manual override category
        override_reason: Reason for override
        overridden_by: User performing the override
    """
    from src.models.incident import IncidentCategory
    
    try:
        original_cat = IncidentCategory(original_category)
        override_cat = IncidentCategory(override_category)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {str(e)}"
        )
    
    result = await service.override_classification(
        incident_id=incident_id,
        original_category=original_cat,
        original_confidence=original_confidence,
        override_category=override_cat,
        override_reason=override_reason,
        overridden_by=overridden_by
    )
    
    return result


@app.get(
    "/api/v1/classification/stats",
    response_model=ClassificationStats,
    tags=["Classification"]
)
async def get_classification_stats(
    service: ClassificationService = Depends(get_classification_service)
):
    """
    Get classification engine performance statistics.
    
    Returns metrics including:
    - Total classifications performed
    - Accuracy rate (target: 80%)
    - Average confidence score
    - Average processing time (target: < 5 seconds)
    - Override rate
    - Category distribution
    """
    stats = await service.get_stats()
    return stats


@app.get(
    "/api/v1/incidents/{incident_id}/classification-overrides",
    response_model=List[ClassificationOverride],
    tags=["Classification"]
)
async def get_classification_overrides(
    incident_id: str,
    service: ClassificationService = Depends(get_classification_service)
):
    """
    Get all classification overrides for a specific incident.
    
    Useful for tracking manual corrections and classification history.
    """
    overrides = await service.get_overrides(incident_id=incident_id)
    return overrides


@app.post(
    "/api/v1/classification/feedback",
    response_model=ClassificationFeedback,
    tags=["Classification"],
    status_code=status.HTTP_201_CREATED
)
async def submit_classification_feedback(
    incident_id: str,
    classification_id: str,
    was_correct: bool,
    expected_category: Optional[str] = None,
    feedback_type: str = "correct",
    comments: Optional[str] = None,
    submitted_by: str = "user",
    service: ClassificationService = Depends(get_classification_service)
):
    """
    Submit feedback on classification accuracy.
    
    This feedback is used to monitor and improve the classification engine's
    accuracy over time, helping to meet the 80% accuracy requirement.
    
    Args:
        incident_id: Incident identifier
        classification_id: Classification result identifier
        was_correct: Whether the classification was correct
        expected_category: What the category should have been (if incorrect)
        feedback_type: Type of feedback (correct, incorrect, partially_correct)
        comments: Additional comments
        submitted_by: User submitting feedback
    """
    from src.models.incident import IncidentCategory
    
    expected_cat = None
    if expected_category:
        try:
            expected_cat = IncidentCategory(expected_category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid expected category: {expected_category}"
            )
    
    feedback = await service.submit_feedback(
        incident_id=incident_id,
        classification_id=classification_id,
        was_correct=was_correct,
        expected_category=expected_cat,
        feedback_type=feedback_type,
        comments=comments,
        submitted_by=submitted_by
    )
    
    return feedback


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
