"""
Unit tests for resolution recommendation service.
"""
import pytest
from datetime import datetime
from src.models.incident import Incident, IncidentCategory, IncidentPriority
from src.models.recommendation import (
    FeedbackRequest, FeedbackRating, RecommendationStatus
)
from src.services.recommendation_service import RecommendationService
from src.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Create audit service fixture."""
    return AuditService()


@pytest.fixture
def recommendation_service(audit_service):
    """Create recommendation service fixture."""
    return RecommendationService(audit_service=audit_service)


@pytest.fixture
def network_incident():
    """Create a network category incident."""
    return Incident(
        incident_id="INC-REC-001",
        title="Network connectivity issues",
        description="Users reporting intermittent network disconnections",
        category=IncidentCategory.NETWORK,
        priority=IncidentPriority.HIGH,
        confidence_score=0.88,
        created_by="engineer001"
    )


@pytest.fixture
def database_incident():
    """Create a database category incident."""
    return Incident(
        incident_id="INC-REC-002",
        title="Database connection pool exhausted",
        description="Application cannot establish new database connections",
        category=IncidentCategory.DATABASE,
        priority=IncidentPriority.CRITICAL,
        confidence_score=0.93,
        created_by="engineer002"
    )


@pytest.fixture
def application_incident():
    """Create an application category incident."""
    return Incident(
        incident_id="INC-REC-003",
        title="Application memory leak",
        description="Application memory usage gradually increasing",
        category=IncidentCategory.APPLICATION,
        priority=IncidentPriority.MEDIUM,
        confidence_score=0.75,
        created_by="engineer003"
    )


@pytest.mark.asyncio
async def test_get_recommendations_returns_results(recommendation_service, network_incident):
    """Test that recommendations are returned for network incidents."""
    response = await recommendation_service.get_recommendations(
        incident=network_incident,
        max_recommendations=5,
        min_success_rate=0.5
    )
    
    assert response.incident_id == network_incident.incident_id
    assert response.total_found > 0
    assert len(response.recommendations) > 0
    assert response.processing_time_ms < 10000  # Must be under 10 seconds
    assert response.coverage_met is True  # At least one recommendation


@pytest.mark.asyncio
async def test_recommendations_ranked_by_success_rate(recommendation_service, database_incident):
    """Test that recommendations are ranked by success rate."""
    response = await recommendation_service.get_recommendations(
        incident=database_incident,
        max_recommendations=5,
        min_success_rate=0.0
    )
    
    recommendations = response.recommendations
    
    # Verify recommendations are sorted by success rate (descending)
    for i in range(len(recommendations) - 1):
        assert recommendations[i].success_rate >= recommendations[i + 1].success_rate


@pytest.mark.asyncio
async def test_recommendations_include_steps(recommendation_service, network_incident):
    """Test that recommendations include step-by-step instructions."""
    response = await recommendation_service.get_recommendations(
        incident=network_incident,
        max_recommendations=5,
        min_success_rate=0.5
    )
    
    for recommendation in response.recommendations:
        assert len(recommendation.steps) > 0  # Must have at least one step
        assert recommendation.title is not None
        assert recommendation.description is not None
        assert 0.0 <= recommendation.success_rate <= 1.0


@pytest.mark.asyncio
async def test_recommendations_meet_coverage_target(recommendation_service, audit_service):
    """
    Test that the system meets the 75% coverage target.
    
    In production, this would test against a large dataset of historical incidents.
    For this stub, we verify that at least one recommendation is returned for
    common incident categories.
    """
    test_incidents = [
        Incident(
            incident_id=f"INC-TEST-{i}",
            title=f"Test incident {i}",
            description="Test description",
            category=category,
            priority=IncidentPriority.MEDIUM,
            confidence_score=0.8,
            created_by="test-user"
        )
        for i, category in enumerate([
            IncidentCategory.NETWORK,
            IncidentCategory.DATABASE,
            IncidentCategory.APPLICATION,
        ])
    ]
    
    service = RecommendationService(audit_service=audit_service)
    
    incidents_with_recommendations = 0
    
    for incident in test_incidents:
        response = await service.get_recommendations(
            incident=incident,
            max_recommendations=5,
            min_success_rate=0.5
        )
        
        if response.coverage_met:
            incidents_with_recommendations += 1
    
    coverage_percentage = (incidents_with_recommendations / len(test_incidents)) * 100
    
    # Verify we meet the 75% target
    assert coverage_percentage >= 75.0, f"Coverage was {coverage_percentage}%, expected >= 75%"


@pytest.mark.asyncio
async def test_recommendation_performance_under_10_seconds(recommendation_service, network_incident):
    """Test that recommendations are returned within 10 seconds."""
    response = await recommendation_service.get_recommendations(
        incident=network_incident,
        max_recommendations=5,
        min_success_rate=0.5
    )
    
    # Verify processing time is under 10 seconds (10000ms)
    assert response.processing_time_ms < 10000


@pytest.mark.asyncio
async def test_submit_feedback(recommendation_service):
    """Test submitting feedback for a recommendation."""
    feedback_request = FeedbackRequest(
        recommendation_id="rec-001",
        incident_id="INC-REC-001",
        engineer_id="engineer123",
        rating=FeedbackRating.HELPFUL,
        was_applied=True,
        was_successful=True,
        resolution_time_minutes=15,
        comments="Recommendation worked perfectly"
    )
    
    feedback = await recommendation_service.submit_feedback(feedback_request)
    
    assert feedback.feedback_id is not None
    assert feedback.recommendation_id == "rec-001"
    assert feedback.incident_id == "INC-REC-001"
    assert feedback.engineer_id == "engineer123"
    assert feedback.rating == FeedbackRating.HELPFUL
    assert feedback.was_applied is True
    assert feedback.was_successful is True
    assert feedback.resolution_time_minutes == 15


@pytest.mark.asyncio
async def test_get_feedback_stats(recommendation_service):
    """Test retrieving aggregated feedback statistics."""
    recommendation_id = "rec-stats-001"
    
    # Submit multiple feedback entries
    feedback_requests = [
        FeedbackRequest(
            recommendation_id=recommendation_id,
            incident_id=f"INC-{i}",
            engineer_id=f"eng-{i}",
            rating=FeedbackRating.HELPFUL,
            was_applied=True,
            was_successful=True
        )
        for i in range(3)
    ]
    
    for req in feedback_requests:
        await recommendation_service.submit_feedback(req)
    
    # Get statistics
    stats = await recommendation_service.get_feedback_stats(recommendation_id)
    
    assert stats["recommendation_id"] == recommendation_id
    assert stats["total_feedback"] == 3
    assert stats["times_applied"] == 3
    assert stats["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_get_feedback_for_incident(recommendation_service):
    """Test retrieving all feedback for a specific incident."""
    incident_id = "INC-FEEDBACK-001"
    
    # Submit feedback for multiple recommendations on the same incident
    for i in range(2):
        feedback_request = FeedbackRequest(
            recommendation_id=f"rec-{i}",
            incident_id=incident_id,
            engineer_id="engineer456",
            rating=FeedbackRating.VERY_HELPFUL,
            was_applied=True,
            was_successful=True
        )
        await recommendation_service.submit_feedback(feedback_request)
    
    # Get all feedback for the incident
    feedback_list = await recommendation_service.get_feedback_for_incident(incident_id)
    
    assert len(feedback_list) == 2
    assert all(f.incident_id == incident_id for f in feedback_list)


@pytest.mark.asyncio
async def test_audit_trail_created_for_recommendations(
    recommendation_service,
    network_incident,
    audit_service
):
    """Test that audit trail is created for recommendation operations."""
    initial_audit_count = len(audit_service._audit_log)
    
    # Request recommendations
    await recommendation_service.get_recommendations(
        incident=network_incident,
        max_recommendations=5,
        min_success_rate=0.5
    )
    
    # Verify audit entries were created
    assert len(audit_service._audit_log) > initial_audit_count
    
    # Verify audit trail for the incident
    incident_audits = await audit_service.get_incident_audit_trail(network_incident.incident_id)
    assert len(incident_audits) > 0


@pytest.mark.asyncio
async def test_min_success_rate_filter(recommendation_service, database_incident):
    """Test that recommendations are filtered by minimum success rate."""
    # Get recommendations with high success rate threshold
    response_high_threshold = await recommendation_service.get_recommendations(
        incident=database_incident,
        max_recommendations=10,
        min_success_rate=0.9
    )
    
    # Get recommendations with low success rate threshold
    response_low_threshold = await recommendation_service.get_recommendations(
        incident=database_incident,
        max_recommendations=10,
        min_success_rate=0.5
    )
    
    # All recommendations should meet the threshold
    for rec in response_high_threshold.recommendations:
        assert rec.success_rate >= 0.9
    
    for rec in response_low_threshold.recommendations:
        assert rec.success_rate >= 0.5
    
    # Lower threshold should return more or equal recommendations
    assert len(response_low_threshold.recommendations) >= len(response_high_threshold.recommendations)


@pytest.mark.asyncio
async def test_max_recommendations_limit(recommendation_service, network_incident):
    """Test that the maximum recommendations limit is respected."""
    max_limit = 3
    
    response = await recommendation_service.get_recommendations(
        incident=network_incident,
        max_recommendations=max_limit,
        min_success_rate=0.0
    )
    
    # Should not return more than the limit
    assert len(response.recommendations) <= max_limit
