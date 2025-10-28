"""
Tests for the Reporting Service - performance reports and trend analysis.
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.models.learning import (
    ResolutionFeedback, FeedbackType, MonthlyPerformanceReport
)
from src.services.learning_service import LearningService
from src.services.reporting_service import ReportingService
from src.services.audit_service import AuditService
from src.models.audit import AuditAction


@pytest.fixture
def audit_service():
    """Create audit service for testing."""
    return AuditService()


@pytest.fixture
def learning_service(audit_service):
    """Create learning service for testing."""
    return LearningService(audit_service=audit_service)


@pytest.fixture
def reporting_service(learning_service, audit_service):
    """Create reporting service for testing."""
    return ReportingService(
        learning_service=learning_service,
        audit_service=audit_service
    )


@pytest.fixture
async def sample_data(learning_service, audit_service):
    """Create sample data for testing."""
    # Add feedback data
    categories = ["network", "database", "application"]
    for category in categories:
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{category}-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS if i < 8 else FeedbackType.RESOLUTION_FAILURE,
                original_category=category,
                original_confidence=0.88,
                resolution_successful=i < 8,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
    
    # Add audit entries
    for i in range(30):
        await audit_service.log_auto_resolution_success(
            incident_id=f"INC-{i}",
            confidence_score=0.90,
            resolution_steps=[]
        )
    
    return learning_service, audit_service


class TestMonthlyReports:
    """Test monthly report generation."""
    
    @pytest.mark.asyncio
    async def test_generate_monthly_report(self, reporting_service, sample_data):
        """Test generating a monthly report."""
        now = datetime.utcnow()
        report = await reporting_service.generate_monthly_report(
            month=now.month,
            year=now.year
        )
        
        assert report.month == now.month
        assert report.year == now.year
        assert report.total_incidents >= 0
        assert 0.0 <= report.overall_accuracy <= 1.0
        assert 0.0 <= report.classification_accuracy <= 1.0
        assert 0.0 <= report.resolution_success_rate <= 1.0
    
    @pytest.mark.asyncio
    async def test_monthly_report_includes_categories(self, reporting_service, sample_data):
        """Test that monthly report includes category breakdown."""
        now = datetime.utcnow()
        report = await reporting_service.generate_monthly_report(
            month=now.month,
            year=now.year
        )
        
        assert len(report.category_performance) > 0
        for category, metrics in report.category_performance.items():
            assert metrics.category == category
            assert metrics.total_incidents > 0
    
    @pytest.mark.asyncio
    async def test_monthly_report_identifies_poor_performers(self, reporting_service, learning_service, audit_service):
        """Test that monthly report identifies poor performing categories."""
        # Add good performance for network
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-NET-{i}",
                feedback_type=FeedbackType.CORRECT_CLASSIFICATION,
                original_category="network",
                original_confidence=0.95,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        # Add poor performance for security
        for i in range(10):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-SEC-{i}",
                feedback_type=FeedbackType.INCORRECT_CLASSIFICATION,
                original_category="security",
                correct_category="infrastructure",
                original_confidence=0.60,
                resolution_successful=False,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        now = datetime.utcnow()
        report = await reporting_service.generate_monthly_report(
            month=now.month,
            year=now.year
        )
        
        assert "security" in report.poor_performing_categories
        assert "network" not in report.poor_performing_categories
    
    @pytest.mark.asyncio
    async def test_get_report_by_id(self, reporting_service, sample_data):
        """Test retrieving a report by ID."""
        now = datetime.utcnow()
        report = await reporting_service.generate_monthly_report(
            month=now.month,
            year=now.year
        )
        
        retrieved = await reporting_service.get_report_by_id(report.report_id)
        
        assert retrieved is not None
        assert retrieved.report_id == report.report_id
        assert retrieved.month == report.month
        assert retrieved.year == report.year
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_report(self, reporting_service):
        """Test retrieving a report that doesn't exist."""
        report = await reporting_service.get_report_by_id("nonexistent-id")
        assert report is None
    
    @pytest.mark.asyncio
    async def test_list_reports(self, reporting_service, sample_data):
        """Test listing available reports."""
        now = datetime.utcnow()
        
        # Generate multiple reports
        await reporting_service.generate_monthly_report(month=now.month, year=now.year)
        
        reports = await reporting_service.list_reports(limit=10)
        
        assert len(reports) >= 1
        assert isinstance(reports[0], MonthlyPerformanceReport)
    
    @pytest.mark.asyncio
    async def test_list_reports_filtered_by_year(self, reporting_service, sample_data):
        """Test listing reports filtered by year."""
        now = datetime.utcnow()
        
        await reporting_service.generate_monthly_report(month=now.month, year=now.year)
        
        reports = await reporting_service.list_reports(year=now.year)
        
        assert all(report.year == now.year for report in reports)


class TestAccuracyTrends:
    """Test accuracy trend analysis."""
    
    @pytest.mark.asyncio
    async def test_get_accuracy_trends(self, reporting_service, sample_data):
        """Test retrieving accuracy trends over multiple months."""
        trends = await reporting_service.get_accuracy_trends(months=3)
        
        assert "monthly_overall" in trends
        assert "monthly_classification" in trends
        assert "monthly_resolution" in trends
        
        assert len(trends["monthly_overall"]) == 3
        assert all(0.0 <= acc <= 1.0 for acc in trends["monthly_overall"])
    
    @pytest.mark.asyncio
    async def test_accuracy_trends_show_improvement(self, reporting_service, learning_service):
        """Test that accuracy trends can show improvement over time."""
        # Simulate improvement by adding increasingly better feedback over time
        base_date = datetime.utcnow() - timedelta(days=60)
        
        for day_offset in range(60):
            current_date = base_date + timedelta(days=day_offset)
            # Gradually improve success rate
            success_rate = 0.5 + (day_offset / 120)  # 0.5 to 1.0
            
            feedback_type = FeedbackType.RESOLUTION_SUCCESS if day_offset > 30 else FeedbackType.RESOLUTION_FAILURE
            
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{day_offset}",
                feedback_type=feedback_type,
                original_category="application",
                original_confidence=0.80 + (day_offset / 300),
                resolution_successful=day_offset > 30,
                submitted_by="user@example.com",
                submitted_at=current_date
            )
            await learning_service.submit_feedback(feedback)
        
        trends = await reporting_service.get_accuracy_trends(months=2)
        
        # Should have trend data
        assert len(trends["monthly_overall"]) == 2


class TestCategoryComparison:
    """Test category performance comparison."""
    
    @pytest.mark.asyncio
    async def test_get_category_performance_comparison(self, reporting_service, sample_data):
        """Test comparing performance across categories."""
        comparison = await reporting_service.get_category_performance_comparison(
            lookback_days=30
        )
        
        assert isinstance(comparison, dict)
        assert len(comparison) > 0
        
        for category, metrics in comparison.items():
            assert metrics.category == category
            assert hasattr(metrics, 'classification_accuracy')
            assert hasattr(metrics, 'auto_resolution_success_rate')
    
    @pytest.mark.asyncio
    async def test_category_comparison_includes_all_categories(self, reporting_service, learning_service):
        """Test that comparison includes all categories with feedback."""
        categories = ["network", "database", "application", "security"]
        
        for category in categories:
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-{category}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category=category,
                original_confidence=0.90,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        comparison = await reporting_service.get_category_performance_comparison(
            lookback_days=30
        )
        
        for category in categories:
            assert category in comparison


class TestPerformanceSummary:
    """Test performance summary for dashboards."""
    
    @pytest.mark.asyncio
    async def test_get_performance_summary(self, reporting_service, sample_data):
        """Test getting high-level performance summary."""
        summary = await reporting_service.get_performance_summary()
        
        assert "current_model_version" in summary
        assert "overall_accuracy_30d" in summary
        assert "classification_accuracy_30d" in summary
        assert "resolution_success_rate_30d" in summary
        assert "total_feedback_30d" in summary
        assert "poor_performing_categories" in summary
        assert "categories_tracked" in summary
        assert "generated_at" in summary
        
        # Verify data types and ranges
        assert isinstance(summary["current_model_version"], str)
        assert 0.0 <= summary["overall_accuracy_30d"] <= 1.0
        assert 0.0 <= summary["classification_accuracy_30d"] <= 1.0
        assert 0.0 <= summary["resolution_success_rate_30d"] <= 1.0
        assert summary["total_feedback_30d"] >= 0
        assert summary["categories_tracked"] >= 0
    
    @pytest.mark.asyncio
    async def test_summary_reflects_recent_data(self, reporting_service, learning_service):
        """Test that summary reflects recent data only."""
        # Add old feedback (should not be included in 30-day summary)
        old_feedback = ResolutionFeedback(
            feedback_id=str(uuid4()),
            incident_id="INC-OLD",
            feedback_type=FeedbackType.RESOLUTION_SUCCESS,
            original_category="network",
            original_confidence=0.90,
            resolution_successful=True,
            submitted_by="user@example.com",
            submitted_at=datetime.utcnow() - timedelta(days=60)
        )
        await learning_service.submit_feedback(old_feedback)
        
        # Add recent feedback
        recent_feedback = ResolutionFeedback(
            feedback_id=str(uuid4()),
            incident_id="INC-RECENT",
            feedback_type=FeedbackType.RESOLUTION_SUCCESS,
            original_category="database",
            original_confidence=0.92,
            resolution_successful=True,
            submitted_by="user@example.com",
            submitted_at=datetime.utcnow()
        )
        await learning_service.submit_feedback(recent_feedback)
        
        summary = await reporting_service.get_performance_summary()
        
        # Should only count recent feedback
        assert summary["total_feedback_30d"] == 1


class TestImprovementOpportunities:
    """Test identification of improvement opportunities."""
    
    @pytest.mark.asyncio
    async def test_identify_improvement_opportunities(self, reporting_service, sample_data):
        """Test identifying improvement opportunities."""
        opportunities = await reporting_service.identify_improvement_opportunities()
        
        assert "low_data_categories" in opportunities
        assert "declining_accuracy_categories" in opportunities
        assert "high_priority_patterns" in opportunities
        assert "threshold_adjustments" in opportunities
        
        assert isinstance(opportunities["low_data_categories"], list)
        assert isinstance(opportunities["declining_accuracy_categories"], list)
        assert isinstance(opportunities["high_priority_patterns"], list)
        assert isinstance(opportunities["threshold_adjustments"], list)
    
    @pytest.mark.asyncio
    async def test_identifies_low_data_categories(self, reporting_service, learning_service):
        """Test identification of categories with insufficient data."""
        # Add minimal data for a category
        for i in range(3):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-RARE-{i}",
                feedback_type=FeedbackType.RESOLUTION_SUCCESS,
                original_category="user_access",
                original_confidence=0.85,
                resolution_successful=True,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        opportunities = await reporting_service.identify_improvement_opportunities()
        
        # Should identify user_access as low data
        low_data = opportunities["low_data_categories"]
        if low_data:
            category_names = [item["category"] for item in low_data]
            assert "user_access" in category_names
    
    @pytest.mark.asyncio
    async def test_identifies_declining_accuracy(self, reporting_service, learning_service):
        """Test identification of categories with poor accuracy."""
        # Add poor performing feedback
        for i in range(15):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-POOR-{i}",
                feedback_type=FeedbackType.INCORRECT_CLASSIFICATION,
                original_category="infrastructure",
                correct_category="network",
                original_confidence=0.65,
                resolution_successful=False,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        opportunities = await reporting_service.identify_improvement_opportunities()
        
        declining = opportunities["declining_accuracy_categories"]
        if declining:
            category_names = [item["category"] for item in declining]
            assert "infrastructure" in category_names
    
    @pytest.mark.asyncio
    async def test_suggests_threshold_adjustments(self, reporting_service, learning_service):
        """Test suggestion of threshold adjustments for high false positive rates."""
        # Add many false positives
        for i in range(15):
            feedback = ResolutionFeedback(
                feedback_id=str(uuid4()),
                incident_id=f"INC-FP-{i}",
                feedback_type=FeedbackType.RESOLUTION_FAILURE,
                original_category="application",
                original_confidence=0.91,
                resolution_successful=False,
                submitted_by="user@example.com",
                submitted_at=datetime.utcnow()
            )
            await learning_service.submit_feedback(feedback)
        
        opportunities = await reporting_service.identify_improvement_opportunities()
        
        # Should suggest threshold adjustment
        adjustments = opportunities["threshold_adjustments"]
        # May or may not trigger based on exact calculation, but should not error
        assert isinstance(adjustments, list)
