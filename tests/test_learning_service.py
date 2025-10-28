"""
Tests for the Learning Service - continuous AI improvement functionality.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.learning import (
    ResolutionFeedback, FeedbackType, CategoryPerformanceMetrics,
    ModelRetrainingRequest, EmergingPatternSuggestion
)
from src.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from src.services.learning_service import LearningService
from src.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Create audit service for testing."""
    return AuditService()


@pytest.fixture
def learning_service(audit_service):
    """Create learning service for testing."""
    return LearningService(audit_service=audit_service)


@pytest.fixture
def sample_feedback():
    """Create sample feedback for testing."""
    return ResolutionFeedback(
        feedback_id=str(uuid4()),
        incident_id="INC-001",
        feedback_type=FeedbackType.RESOLUTION_SUCCESS,
        original_category="network",
        original_confidence=0.92,
        resolution_successful=True,
        submitted_by="user@example.com",
        submitted_at=datetime.utcnow()
    )


@pytest.fixture
def sample_incident():
    """Create sample incident for testing."""
    return Incident(
        incident_id="INC-001",
        title="Network connectivity issue",
        description="Cannot connect to server",
        category=IncidentCategory.NETWORK,
        priority=IncidentPriority.HIGH,
        confidence_score=0.92,
        created_by="user@example.com"
    )


class TestFeedbackSubmission:
    """Test feedback submission and storage."""
    
    @pytest.mark.asyncio
    async def test_submit_feedback_success(self, learning_service, sample_feedback):
        """Test successful feedback submission."""
        result = await learning_service.submit_feedback(sample_feedback)
        
        assert result.feedback_id == sample_feedback.feedback_id
        assert result.incident_id == sample_feedback.incident_id
        assert result.feedback_type == FeedbackType.RESOLUTION_SUCCESS
        
        # Verify feedback is stored
        incident_feedback = await learning_service.get_feedback_by_incident("INC-001")
        assert len(incident_feedback) == 1
        assert incident_feedback[0].feedback_id == sample_feedback.feedback_id
    
    @pytest.mark.asyncio
    async def test_submit_classification_error_feedback(self, learning_service):
        """Test submitting feedback for misclassification."""
        feedback = ResolutionFeedback(
            feedback_id=str(uuid4()),
            incident_id="INC-002",
            feedback_type=FeedbackType.INCORRECT_CLASSIFICATION,
            original_category="network",
            correct_category="database",
            original_confidence=0.75,
            resolution_successful=False,
            submitted_by="admin@example.com",
            submitted_at=datetime.utcnow()
        )
        
        result = await learning_service.submit_feedback(feedback)
        
        assert result.correct_category == "database"
        assert result.feedback_type == FeedbackType.INCORRECT_CLASSIFICATION
    
    @pytest.mark.asyncio
    async def test_get_feedback_by_incident(self, learning_service):
        """Test retrieving feedback for specific incident."""
        # Submit multiple feedback entries
        for i in range(3):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id="INC-003",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="application",
                original_confidence=0.88,
                resolution_successful=True,
                submitted_by=f"user{i}@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        # Retrieve feedback
        feedback_list = await learning_service.get_feedback_by_incident("INC-003")
        assert len(feedback_list) == 3


class TestCategoryMetrics:
    """Test category performance metrics calculation."""
    
    @pytest.mark.asyncio
    async def test_calculate_category_metrics_no_data(self, learning_service):
        """Test metrics calculation with no feedback data."""
        metrics = await learning_service.calculate_category_metrics("network")
        
        assert metrics.category == "network"
        assert metrics.total_incidents == 0
        assert metrics.classification_accuracy == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_category_metrics_with_data(self, learning_service):
        """Test metrics calculation with feedback data."""
        # Submit feedback for network category
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS if i < 8 else FeedbackType.RESOLUTION_FAILURE,
                original_category="network",
                original_confidence=0.90,
                resolution_successful=i < 8,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        metrics = await learning_service.calculate_category_metrics("network")
        
        assert metrics.category == "network"
        assert metrics.total_incidents == 10
        assert metrics.auto_resolved_count == 8
        assert metrics.auto_resolution_success_rate == 0.8
        assert metrics.false_positive_count == 2
    
    @pytest.mark.asyncio
    async def test_calculate_category_metrics_with_date_filter(self, learning_service):
        """Test metrics calculation with date filtering."""
        # Submit old feedback
        old_feedback = ResolutionFeedback(
            feedback_id=str(uuid4()),
            incident_id="INC-OLD",
            feedback_type=FeedbackType.RESOLUTION_SUCCESS,
            original_category="database",
            original_confidence=0.85,
            resolution_successful=True,
            submitted_by="user@example.com",
            submitted_at=datetime.utcnow() - timedelta(days=60)
        )
        await learning_service.submit_feedback(old_feedback)
        
        # Submit recent feedback
        recent_feedback = ResolutionFeedback(
            feedback_id=str(uuid4()),
            incident_id="INC-RECENT",
            feedback_type=FeedbackType.RESOLUTION_SUCCESS,
            original_category="database",
            original_confidence=0.90,
            resolution_successful=True,
            submitted_by="user@example.com",
            submitted_at=datetime.utcnow()
        )
        await learning_service.submit_feedback(recent_feedback)
        
        # Calculate metrics for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        metrics = await learning_service.calculate_category_metrics("database", start_date, end_date)
        
        assert metrics.total_incidents == 1  # Only recent feedback


class TestOverallMetrics:
    """Test overall learning system metrics."""
    
    @pytest.mark.asyncio
    async def test_calculate_overall_metrics(self, learning_service):
        """Test overall metrics calculation."""
        # Submit feedback for multiple categories
        categories = ["network", "database", "application"]
        for category in categories:
            for i in range(5):
                feedback = ResolutionFeedback(
                    feedback_id=str(uuid4()),
                    incident_id=f"INC-{category}-{i}",
                    feedback_type=FeedbackType.CORRECT_CLASSIFICATION,
                    original_category=category,
                    original_confidence=0.88,
                    resolution_successful=True,
                    submitted_by="user@example.com",
                    submitted_at=datetime.utcnow()
                )
                await learning_service.submit_feedback(feedback)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        metrics = await learning_service.calculate_overall_metrics(start_date, end_date)
        
        assert metrics.total_feedback_count == 15
        assert len(metrics.category_metrics) == 3
        assert metrics.classification_accuracy > 0.0
    
    @pytest.mark.asyncio
    async def test_identify_poor_performing_categories(self, learning_service):
        """Test identification of poor performing categories."""
        # Submit good feedback for network
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-NET-{i}",
                feedback_type=FeedbackType.CORRECT_CLASSIFICATION,
                original_category="network",
                original_confidence=0.90,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        # Submit poor feedback for database (mostly incorrect)
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-DB-{i}",
                feedback_type=FeedbackType.INCORRECT_CLASSIFICATION,
                original_category="database",
                correct_category="infrastructure",
                original_confidence=0.65,
                resolution_successful=False,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        metrics = await learning_service.calculate_overall_metrics(start_date, end_date)
        
        assert "database" in metrics.poor_performing_categories


class TestModelRetraining:
    """Test model retraining functionality."""
    
    @pytest.mark.asyncio
    async def test_prepare_training_dataset(self, learning_service, sample_incident):
        """Test training dataset preparation."""
        # Add some feedback
        for i in range(5):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="network",
                original_confidence=0.90,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        # Add incident to store
        learning_service._incident_store.append(sample_incident)
        
        dataset = await learning_service.prepare_training_dataset(
            name="Test Dataset",
            description="Dataset for testing"
        )
        
        assert dataset.name == "Test Dataset"
        assert dataset.feedback_count == 5
        assert "network" in dataset.categories_included
    
    @pytest.mark.asyncio
    async def test_retrain_model_success(self, learning_service):
        """Test successful model retraining."""
        # Submit sufficient feedback
        for i in range(15):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="application",
                original_confidence=0.88,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        request = ModelRetrainingRequest(
            requested_by="admin@example.com"
        )
        
        result = await learning_service.retrain_model(request)
        
        assert result.status == "success"
        assert result.training_samples_count >= 10
        assert result.validation_accuracy > 0.0
        assert result.model_version != "1.0.0"
    
    @pytest.mark.asyncio
    async def test_retrain_model_insufficient_data(self, learning_service):
        """Test retraining failure with insufficient data."""
        # Submit only a few feedback entries
        for i in range(3):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="security",
                original_confidence=0.90,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        request = ModelRetrainingRequest(
            requested_by="admin@example.com"
        )
        
        result = await learning_service.retrain_model(request)
        
        assert result.status == "failed"
        assert "Insufficient training samples" in result.error_message
    
    @pytest.mark.asyncio
    async def test_get_training_history(self, learning_service):
        """Test retrieving training history."""
        # Perform some training
        for i in range(15):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="network",
                original_confidence=0.90,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        request = ModelRetrainingRequest(requested_by="admin@example.com")
        await learning_service.retrain_model(request)
        
        history = await learning_service.get_training_history(limit=5)
        
        assert len(history) >= 1
        assert history[0].status == "success"


class TestEmergingPatterns:
    """Test emerging pattern detection."""
    
    @pytest.mark.asyncio
    async def test_detect_emerging_patterns_no_patterns(self, learning_service):
        """Test pattern detection with no clear patterns."""
        patterns = await learning_service.detect_emerging_patterns()
        assert isinstance(patterns, list)
    
    @pytest.mark.asyncio
    async def test_detect_emerging_patterns_with_pattern(self, learning_service):
        """Test pattern detection with clear emerging pattern."""
        # Submit feedback with common keywords
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-SSL-{i}",
                feedback_type=FeedbackType.MANUAL_OVERRIDE,
                original_category="security",
                original_confidence=0.65,
                resolution_successful=True,
                feedback_notes="SSL certificate expired and needs renewal",
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        patterns = await learning_service.detect_emerging_patterns(
            min_frequency=5,
            min_confidence=0.5
        )
        
        # Should detect pattern related to SSL/certificate
        assert len(patterns) > 0
        # Pattern should have reasonable confidence
        for pattern in patterns:
            assert pattern.confidence >= 0.5
            assert pattern.pattern_frequency >= 5
    
    @pytest.mark.asyncio
    async def test_pattern_suggestion_details(self, learning_service):
        """Test that pattern suggestions contain useful details."""
        # Submit feedback with specific pattern
        for i in range(8):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-API-{i}",
                feedback_type=FeedbackType.MANUAL_OVERRIDE,
                original_category="application",
                original_confidence=0.70,
                resolution_successful=True,
                feedback_notes="API timeout error requires configuration adjustment",
                human_resolution_steps=[
                    {"description": "Increase timeout value", "action": "config_update"},
                    {"description": "Restart API service", "action": "service_restart"}
                ],
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        patterns = await learning_service.detect_emerging_patterns(
            min_frequency=5,
            min_confidence=0.5
        )
        
        if patterns:
            pattern = patterns[0]
            assert pattern.suggested_category_name is not None
            assert pattern.suggested_category_description is not None
            assert len(pattern.incident_sample_ids) > 0
            assert pattern.status == "pending_review"


class TestModelVersion:
    """Test model version tracking."""
    
    def test_get_current_model_version(self, learning_service):
        """Test retrieving current model version."""
        version = learning_service.get_current_model_version()
        assert version == "1.0.0"
    
    @pytest.mark.asyncio
    async def test_model_version_updates_after_training(self, learning_service):
        """Test that model version increments after successful training."""
        # Submit sufficient feedback
        for i in range(15):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="network",
                original_confidence=0.90,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        initial_version = learning_service.get_current_model_version()
        
        request = ModelRetrainingRequest(requested_by="admin@example.com")
        result = await learning_service.retrain_model(request)
        
        if result.status == "success":
            new_version = learning_service.get_current_model_version()
            assert new_version != initial_version
            assert result.model_version == new_version
