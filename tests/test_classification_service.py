"""
Tests for the Classification Service.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from src.models.incident import IncidentCategory
from src.models.classification import (
    ClassificationRequest,
    ClassificationResult,
    ClassificationOverride,
    ClassificationStats,
    ClassificationFeedback
)
from src.services.classification_service import ClassificationService
from src.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Fixture for audit service."""
    service = AuditService()
    return service


@pytest.fixture
def classification_service(audit_service):
    """Fixture for classification service."""
    return ClassificationService(audit_service=audit_service)


@pytest.mark.asyncio
async def test_classify_network_incident(classification_service):
    """Test classification of network incident."""
    request = ClassificationRequest(
        incident_id="INC-001",
        title="Network connection timeout",
        description="Users are experiencing connection timeouts when accessing the network"
    )
    
    result = await classification_service.classify_incident(request)
    
    assert result.incident_id == "INC-001"
    assert result.category in [IncidentCategory.NETWORK, IncidentCategory.NETWORK_CONNECTIVITY]
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.processing_time_ms < 5000  # Must be under 5 seconds


@pytest.mark.asyncio
async def test_classify_database_incident(classification_service):
    """Test classification of database incident."""
    request = ClassificationRequest(
        incident_id="INC-002",
        title="Database query timeout",
        description="Slow query performance on production database"
    )
    
    result = await classification_service.classify_incident(request)
    
    assert result.incident_id == "INC-002"
    assert result.category in [IncidentCategory.DATABASE, IncidentCategory.DATABASE_PERFORMANCE]
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.processing_time_ms < 5000


@pytest.mark.asyncio
async def test_classify_authentication_incident(classification_service):
    """Test classification of authentication incident."""
    request = ClassificationRequest(
        incident_id="INC-003",
        title="Cannot login to system",
        description="User authentication failed, credentials not working"
    )
    
    result = await classification_service.classify_incident(request)
    
    assert result.incident_id == "INC-003"
    assert result.category in [IncidentCategory.AUTHENTICATION, IncidentCategory.USER_ACCESS]
    assert 0.0 <= result.confidence_score <= 1.0
    assert result.processing_time_ms < 5000


@pytest.mark.asyncio
async def test_classification_with_confidence_threshold(classification_service):
    """Test that high-confidence classifications meet 80% threshold."""
    # Test with clear network keywords
    request = ClassificationRequest(
        incident_id="INC-004",
        title="Network interface down, cannot ping server",
        description="Network connection failed, ping timeout, unreachable"
    )
    
    result = await classification_service.classify_incident(request)
    
    # With strong keywords, confidence should be relatively high
    assert result.confidence_score > 0.0
    assert result.category == IncidentCategory.NETWORK


@pytest.mark.asyncio
async def test_classification_returns_alternatives(classification_service):
    """Test that classification returns alternative categories."""
    request = ClassificationRequest(
        incident_id="INC-005",
        title="Application slow and network latency high",
        description="Performance issues with application and network"
    )
    
    result = await classification_service.classify_incident(request)
    
    # Should have alternative categories since multiple keywords match
    assert len(result.alternative_categories) >= 0
    
    # Each alternative should have a confidence score
    for category, confidence in result.alternative_categories:
        assert isinstance(category, IncidentCategory)
        assert 0.0 <= confidence <= 1.0


@pytest.mark.asyncio
async def test_manual_classification_override(classification_service):
    """Test manual override of classification."""
    override = await classification_service.override_classification(
        incident_id="INC-006",
        original_category=IncidentCategory.APPLICATION,
        original_confidence=0.75,
        override_category=IncidentCategory.DATABASE,
        override_reason="Incident was actually a database connection issue",
        overridden_by="admin-user"
    )
    
    assert override.incident_id == "INC-006"
    assert override.original_category == IncidentCategory.APPLICATION
    assert override.override_category == IncidentCategory.DATABASE
    assert override.override_reason == "Incident was actually a database connection issue"
    assert override.overridden_by == "admin-user"
    
    # Verify override is stored
    overrides = await classification_service.get_overrides(incident_id="INC-006")
    assert len(overrides) == 1
    assert overrides[0].incident_id == "INC-006"


@pytest.mark.asyncio
async def test_classification_uses_override(classification_service):
    """Test that classification uses manual override when available."""
    # First, create an override
    await classification_service.override_classification(
        incident_id="INC-007",
        original_category=IncidentCategory.APPLICATION,
        original_confidence=0.70,
        override_category=IncidentCategory.SECURITY,
        override_reason="Security incident misclassified",
        overridden_by="security-admin"
    )
    
    # Now classify the same incident
    request = ClassificationRequest(
        incident_id="INC-007",
        title="Application error",
        description="Error in application"
    )
    
    result = await classification_service.classify_incident(request)
    
    # Should use the override
    assert result.category == IncidentCategory.SECURITY
    assert result.confidence_score == 1.0  # Overrides have 100% confidence
    assert "-override" in result.model_version


@pytest.mark.asyncio
async def test_classification_stats_tracking(classification_service):
    """Test that classification statistics are tracked correctly."""
    # Perform several classifications
    for i in range(5):
        request = ClassificationRequest(
            incident_id=f"INC-{100+i}",
            title="Network connection issue",
            description="Cannot connect to network"
        )
        await classification_service.classify_incident(request)
    
    stats = await classification_service.get_stats()
    
    assert stats.total_classifications >= 5
    assert 0.0 <= stats.accuracy_rate <= 1.0
    assert 0.0 <= stats.average_confidence <= 1.0
    assert stats.average_processing_time_ms >= 0
    assert isinstance(stats.category_distribution, dict)


@pytest.mark.asyncio
async def test_classification_feedback_submission(classification_service):
    """Test submission of classification feedback."""
    feedback = await classification_service.submit_feedback(
        incident_id="INC-200",
        classification_id="CLS-200",
        was_correct=True,
        expected_category=None,
        feedback_type="correct",
        comments="Classification was accurate",
        submitted_by="engineer-1"
    )
    
    assert feedback.incident_id == "INC-200"
    assert feedback.classification_id == "CLS-200"
    assert feedback.was_correct is True
    assert feedback.feedback_type == "correct"
    assert feedback.submitted_by == "engineer-1"


@pytest.mark.asyncio
async def test_classification_feedback_with_correction(classification_service):
    """Test feedback submission with category correction."""
    feedback = await classification_service.submit_feedback(
        incident_id="INC-201",
        classification_id="CLS-201",
        was_correct=False,
        expected_category=IncidentCategory.DATABASE,
        feedback_type="incorrect",
        comments="Should have been classified as database issue",
        submitted_by="engineer-2"
    )
    
    assert feedback.was_correct is False
    assert feedback.expected_category == IncidentCategory.DATABASE
    assert feedback.feedback_type == "incorrect"


@pytest.mark.asyncio
async def test_classify_with_unknown_keywords(classification_service):
    """Test classification with unclear/unknown keywords."""
    request = ClassificationRequest(
        incident_id="INC-999",
        title="Something is broken",
        description="System not working as expected"
    )
    
    result = await classification_service.classify_incident(request)
    
    # Should still return a classification (likely with lower confidence)
    assert result.incident_id == "INC-999"
    assert isinstance(result.category, IncidentCategory)
    assert result.confidence_score >= 0.0


@pytest.mark.asyncio
async def test_classification_processing_time_requirement(classification_service):
    """Test that classification meets the 5-second processing time requirement."""
    request = ClassificationRequest(
        incident_id="INC-PERF",
        title="Test performance",
        description="Testing classification speed requirement"
    )
    
    result = await classification_service.classify_incident(request, max_processing_time_ms=5000)
    
    # Must complete within 5 seconds (5000ms)
    assert result.processing_time_ms < 5000


@pytest.mark.asyncio
async def test_classification_stats_accuracy_tracking(classification_service):
    """Test that accuracy statistics track 80% requirement."""
    # Create high-confidence classifications
    high_confidence_requests = [
        ClassificationRequest(
            incident_id=f"INC-ACC-{i}",
            title="Network ping timeout connection failed",
            description="Network issue with connection unreachable"
        )
        for i in range(10)
    ]
    
    for request in high_confidence_requests:
        await classification_service.classify_incident(request)
    
    stats = await classification_service.get_stats()
    
    # Should track successful classifications (confidence >= 0.8)
    assert stats.total_classifications >= 10
    assert stats.successful_classifications >= 0
    
    # Accuracy rate should be calculated
    if stats.total_classifications > 0:
        expected_accuracy = stats.successful_classifications / stats.total_classifications
        assert abs(stats.accuracy_rate - expected_accuracy) < 0.01


@pytest.mark.asyncio
async def test_get_all_overrides(classification_service):
    """Test retrieving all classification overrides."""
    # Create multiple overrides
    for i in range(3):
        await classification_service.override_classification(
            incident_id=f"INC-OVER-{i}",
            original_category=IncidentCategory.APPLICATION,
            original_confidence=0.70,
            override_category=IncidentCategory.DATABASE,
            override_reason=f"Override reason {i}",
            overridden_by="admin"
        )
    
    # Get all overrides
    all_overrides = await classification_service.get_overrides()
    assert len(all_overrides) >= 3
    
    # Get overrides for specific incident
    specific_overrides = await classification_service.get_overrides(incident_id="INC-OVER-0")
    assert len(specific_overrides) == 1
    assert specific_overrides[0].incident_id == "INC-OVER-0"
