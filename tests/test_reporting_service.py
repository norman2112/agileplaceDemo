"""
Tests for the reporting service.
"""
import pytest
from datetime import datetime, timedelta

from src.services.reporting_service import ReportingService
from src.services.audit_service import AuditService
from src.models.report import (
    ReportRequest, ReportType, TimeRange,
    ResolutionSummary, IncidentTrends, PerformanceMetrics,
    RecommendationEffectiveness
)


@pytest.fixture
def audit_service():
    """Create audit service instance for testing."""
    return AuditService()


@pytest.fixture
def reporting_service(audit_service):
    """Create reporting service instance for testing."""
    return ReportingService(audit_service=audit_service)


class TestReportingService:
    """Test suite for ReportingService."""
    
    @pytest.mark.asyncio
    async def test_generate_resolution_summary_report(self, reporting_service):
        """Test generating resolution summary report."""
        request = ReportRequest(
            report_type=ReportType.RESOLUTION_SUMMARY,
            time_range=TimeRange.LAST_7_DAYS
        )
        
        report = await reporting_service.generate_report(request)
        
        assert report.report_id is not None
        assert report.report_type == ReportType.RESOLUTION_SUMMARY
        assert report.resolution_summary is not None
        assert isinstance(report.resolution_summary, ResolutionSummary)
        assert report.start_date is not None
        assert report.end_date is not None
    
    @pytest.mark.asyncio
    async def test_generate_incident_trends_report(self, reporting_service):
        """Test generating incident trends report."""
        request = ReportRequest(
            report_type=ReportType.INCIDENT_TRENDS,
            time_range=TimeRange.LAST_30_DAYS
        )
        
        report = await reporting_service.generate_report(request)
        
        assert report.report_id is not None
        assert report.report_type == ReportType.INCIDENT_TRENDS
        assert report.incident_trends is not None
        assert isinstance(report.incident_trends, IncidentTrends)
        assert report.incident_trends.time_period == TimeRange.LAST_30_DAYS
    
    @pytest.mark.asyncio
    async def test_generate_performance_metrics_report(self, reporting_service):
        """Test generating performance metrics report."""
        request = ReportRequest(
            report_type=ReportType.PERFORMANCE_METRICS,
            time_range=TimeRange.LAST_24_HOURS
        )
        
        report = await reporting_service.generate_report(request)
        
        assert report.report_id is not None
        assert report.report_type == ReportType.PERFORMANCE_METRICS
        assert report.performance_metrics is not None
        assert isinstance(report.performance_metrics, PerformanceMetrics)
    
    @pytest.mark.asyncio
    async def test_generate_recommendation_effectiveness_report(self, reporting_service):
        """Test generating recommendation effectiveness report."""
        request = ReportRequest(
            report_type=ReportType.RECOMMENDATION_EFFECTIVENESS,
            time_range=TimeRange.LAST_7_DAYS
        )
        
        report = await reporting_service.generate_report(request)
        
        assert report.report_id is not None
        assert report.report_type == ReportType.RECOMMENDATION_EFFECTIVENESS
        assert report.recommendation_effectiveness is not None
        assert isinstance(report.recommendation_effectiveness, RecommendationEffectiveness)
    
    @pytest.mark.asyncio
    async def test_custom_date_range(self, reporting_service):
        """Test report generation with custom date range."""
        start_date = datetime.utcnow() - timedelta(days=14)
        end_date = datetime.utcnow()
        
        request = ReportRequest(
            report_type=ReportType.RESOLUTION_SUMMARY,
            time_range=TimeRange.CUSTOM,
            start_date=start_date,
            end_date=end_date
        )
        
        report = await reporting_service.generate_report(request)
        
        assert report.start_date == start_date
        assert report.end_date == end_date
    
    @pytest.mark.asyncio
    async def test_custom_date_range_missing_dates(self, reporting_service):
        """Test that custom date range without dates raises error."""
        request = ReportRequest(
            report_type=ReportType.RESOLUTION_SUMMARY,
            time_range=TimeRange.CUSTOM
        )
        
        with pytest.raises(ValueError, match="Custom time range requires"):
            await reporting_service.generate_report(request)
    
    @pytest.mark.asyncio
    async def test_get_quick_stats(self, reporting_service):
        """Test getting quick statistics."""
        stats = await reporting_service.get_quick_stats()
        
        assert isinstance(stats, dict)
        assert "total_incidents_today" in stats
        assert "auto_resolved_today" in stats
        assert "active_incidents" in stats
        assert "system_status" in stats
        assert "kill_switch_active" in stats
    
    @pytest.mark.asyncio
    async def test_report_with_category_filter(self, reporting_service):
        """Test report generation with category filter."""
        request = ReportRequest(
            report_type=ReportType.RESOLUTION_SUMMARY,
            time_range=TimeRange.LAST_7_DAYS,
            category_filter="network"
        )
        
        report = await reporting_service.generate_report(request)
        
        assert report.metadata["category_filter"] == "network"
    
    @pytest.mark.asyncio
    async def test_date_range_calculation_last_24_hours(self, reporting_service):
        """Test date range calculation for last 24 hours."""
        start, end = reporting_service._calculate_date_range(
            TimeRange.LAST_24_HOURS, None, None
        )
        
        time_diff = (end - start).total_seconds()
        assert abs(time_diff - 86400) < 60  # Within 1 minute of 24 hours
    
    @pytest.mark.asyncio
    async def test_date_range_calculation_last_7_days(self, reporting_service):
        """Test date range calculation for last 7 days."""
        start, end = reporting_service._calculate_date_range(
            TimeRange.LAST_7_DAYS, None, None
        )
        
        time_diff = (end - start).total_seconds()
        expected = 7 * 86400  # 7 days in seconds
        assert abs(time_diff - expected) < 60  # Within 1 minute
