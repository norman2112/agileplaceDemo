"""
Headless Business Logic Agent for programmatic access.
Enables BL integration without web interface dependencies.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.models.incident import (
    Incident, IncidentResolutionResponse, IncidentCategory,
    IncidentPriority, IncidentStatus
)
from src.models.config import AutoResolutionConfig
from src.models.insight import (
    InsightsRequest, InsightsResponse, ServiceArea,
    InsightFeedback, AnomalyThresholdConfig
)
from src.models.report import (
    ReportRequest,
    ReportResponse,
    ReportType,
    TimeRange,
    ReportChatRequest,
    ReportChatResponse
)
from src.services.auto_resolution_service import AutoResolutionService
from src.services.insights_service import InsightsService
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService
from src.services.recommendation_service import RecommendationService
from src.services.reporting_service import ReportingService

logger = logging.getLogger(__name__)


class BusinessLogicAgent:
    """
    Headless agent providing programmatic access to business logic.
    No UI or web server dependencies required.
    """
    
    def __init__(
        self,
        config: Optional[AutoResolutionConfig] = None,
        enable_audit: bool = True,
        enable_notifications: bool = True
    ):
        self.config = config or AutoResolutionConfig()
        self.audit_service = AuditService() if enable_audit else None
        self.notification_service = NotificationService(self.audit_service) if enable_notifications and self.audit_service else None
        
        self.auto_resolution = AutoResolutionService(
            config=self.config,
            audit_service=self.audit_service,
            notification_service=self.notification_service
        )
        self.insights = InsightsService()
        self.recommendations = RecommendationService(self.audit_service) if self.audit_service else None
        self.reporting = ReportingService(self.audit_service) if self.audit_service else None
        
        logger.info("BusinessLogicAgent initialized")
    
    async def resolve_incident(
        self,
        incident: Incident,
        force: bool = False
    ) -> IncidentResolutionResponse:
        """
        Resolve an incident using auto-resolution logic.
        
        Args:
            incident: Incident object to resolve
            force: Force resolution even if confidence is below threshold
        
        Returns:
            IncidentResolutionResponse with resolution details
        """
        if force:
            original_score = incident.confidence_score
            incident.confidence_score = 1.0
            logger.info(f"Force-resolving incident {incident.incident_id}")
        
        response = await self.auto_resolution.resolve_incident(incident)
        
        if force:
            incident.confidence_score = original_score
        
        return response
    
    async def check_can_resolve(
        self,
        incident: Incident
    ) -> tuple[bool, str]:
        """
        Check if an incident can be auto-resolved.
        
        Args:
            incident: Incident to check
        
        Returns:
            Tuple of (can_resolve: bool, reason: str)
        """
        return await self.auto_resolution.can_auto_resolve(incident)
    
    async def generate_insights(
        self,
        service_areas: Optional[List[ServiceArea]] = None,
        time_period_days: int = 30,
        include_trends: bool = True,
        include_anomalies: bool = True,
        include_predictions: bool = True
    ) -> InsightsResponse:
        """
        Generate insights for specified service areas.
        
        Args:
            service_areas: List of service areas to analyze (None = all)
            time_period_days: Number of days to analyze
            include_trends: Include trend analysis
            include_anomalies: Include anomaly detection
            include_predictions: Include predictions
        
        Returns:
            InsightsResponse with analysis results
        """
        request = InsightsRequest(
            service_areas=service_areas,
            time_period_days=time_period_days,
            include_trends=include_trends,
            include_anomalies=include_anomalies,
            include_predictions=include_predictions
        )
        return await self.insights.generate_insights(request)
    
    async def submit_insight_feedback(
        self,
        feedback: InsightFeedback
    ) -> InsightFeedback:
        """
        Submit feedback on generated insights.
        
        Args:
            feedback: Feedback object
        
        Returns:
            Updated feedback object
        """
        return await self.insights.submit_feedback(feedback)
    
    async def configure_anomaly_threshold(
        self,
        config: AnomalyThresholdConfig
    ) -> AnomalyThresholdConfig:
        """
        Configure anomaly detection thresholds.
        
        Args:
            config: Threshold configuration
        
        Returns:
            Updated configuration
        """
        return await self.insights.configure_threshold(config)
    
    async def get_anomaly_thresholds(
        self,
        service_area: Optional[ServiceArea] = None
    ) -> List[AnomalyThresholdConfig]:
        """
        Get anomaly detection thresholds.
        
        Args:
            service_area: Filter by service area (None = all)
        
        Returns:
            List of threshold configurations
        """
        return await self.insights.get_thresholds(service_area)
    
    async def generate_recommendations(
        self,
        incident: Incident,
        max_recommendations: int = 5,
        min_success_rate: float = 0.5
    ) -> Optional[Any]:
        """
        Generate recommendations for an incident.
        
        Args:
            incident: Incident to generate recommendations for
            max_recommendations: Maximum number of recommendations
            min_success_rate: Minimum success rate filter
        
        Returns:
            RecommendationResponse or None if service unavailable
        """
        if not self.recommendations:
            logger.warning("Recommendations service not available (audit disabled)")
            return None
        return await self.recommendations.get_recommendations(
            incident=incident,
            max_recommendations=max_recommendations,
            min_success_rate=min_success_rate
        )
    
    async def generate_report(
        self,
        request: ReportRequest
    ) -> Optional[ReportResponse]:
        """
        Generate operational reports.
        
        Args:
            request: Report request with parameters
        
        Returns:
            ReportResponse or None if service unavailable
        """
        if not self.reporting:
            logger.warning("Reporting service not available (audit disabled)")
            return None
        return await self.reporting.generate_report(request)
    
    async def handle_chat_report_request(
        self,
        chat_request: ReportChatRequest
    ) -> ReportChatResponse:
        """
        Generate reports in response to InsightBot chat prompts.
        
        Args:
            chat_request: Normalized chat payload with optional overrides
        
        Returns:
            Structured chat response with shareable assets
        """
        if not self.reporting:
            raise ValueError("Reporting service not available (audit disabled)")
        
        report_type = chat_request.report_type or self._infer_report_type(chat_request.message)
        time_range = chat_request.time_range or self._infer_time_range(chat_request.message)
        
        report_request = ReportRequest(
            report_type=report_type,
            time_range=time_range,
            start_date=chat_request.start_date,
            end_date=chat_request.end_date,
            comparison_period_days=chat_request.comparison_period_days,
            category_filter=chat_request.metadata.get("category"),
            priority_filter=chat_request.metadata.get("priority")
        )
        
        report = await self.reporting.generate_report(report_request)
        if not report:
            raise ValueError("Unable to generate report for chat request")
        
        reply = (
            f"Generated {report.report_type.value.replace('_', ' ')} covering {report.time_range.value.replace('_', ' ')}. "
            f"Share this link with stakeholders: {report.shareable_link}."
        )
        
        return ReportChatResponse(
            reply=reply,
            report=report,
            shareable_link=report.shareable_link or "",
            export_payload=report.export_payload or {}
        )
    
    async def bulk_resolve_incidents(
        self,
        incidents: List[Incident]
    ) -> List[IncidentResolutionResponse]:
        """
        Resolve multiple incidents in batch.
        
        Args:
            incidents: List of incidents to resolve
        
        Returns:
            List of resolution responses
        """
        responses = []
        for incident in incidents:
            response = await self.resolve_incident(incident)
            responses.append(response)
        return responses
    
    def set_global_enabled(self, enabled: bool):
        """
        Set global auto-resolution enabled state (kill switch).
        
        Args:
            enabled: Enable or disable auto-resolution globally
        """
        self.config.global_enabled = enabled
        logger.info(f"Global auto-resolution: {'enabled' if enabled else 'disabled'}")
    
    def enable_category(self, category: IncidentCategory, enabled: bool = True):
        """
        Enable or disable auto-resolution for a specific category.
        
        Args:
            category: Incident category
            enabled: Enable or disable
        """
        from src.models.config import CategoryConfig
        if category not in self.config.category_configs:
            self.config.category_configs[category] = CategoryConfig(
                category=category,
                auto_resolution_enabled=enabled
            )
        else:
            self.config.category_configs[category].auto_resolution_enabled = enabled
        logger.info(f"Auto-resolution for {category.value}: {'enabled' if enabled else 'disabled'}")
    
    def set_confidence_threshold(
        self,
        category: IncidentCategory,
        threshold: float
    ):
        """
        Set confidence threshold for a category.
        
        Args:
            category: Incident category
            threshold: Confidence threshold (0.0 to 1.0)
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        from src.models.config import CategoryConfig
        if category not in self.config.category_configs:
            self.config.category_configs[category] = CategoryConfig(
                category=category,
                confidence_threshold=threshold
            )
        else:
            self.config.category_configs[category].confidence_threshold = threshold
        logger.info(f"Confidence threshold for {category.value}: {threshold:.2%}")
    
    def _infer_report_type(self, message: str) -> ReportType:
        """Map chat utterances to supported report types."""
        normalized = message.lower()
        if "trend" in normalized or "compare" in normalized:
            return ReportType.INCIDENT_TRENDS
        if "performance" in normalized or "latency" in normalized:
            return ReportType.PERFORMANCE_METRICS
        if "recommendation" in normalized or "adoption" in normalized:
            return ReportType.RECOMMENDATION_EFFECTIVENESS
        return ReportType.RESOLUTION_SUMMARY
    
    def _infer_time_range(self, message: str) -> TimeRange:
        """Infer a time window based on common chat phrases."""
        normalized = message.lower()
        if "24" in normalized or "day" in normalized:
            return TimeRange.LAST_24_HOURS
        if "30" in normalized or "month" in normalized:
            return TimeRange.LAST_30_DAYS
        if "90" in normalized or "quarter" in normalized:
            return TimeRange.LAST_90_DAYS
        return TimeRange.LAST_7_DAYS
    
    async def get_audit_log(
        self,
        incident_id: Optional[str] = None
    ) -> List[Any]:
        """
        Retrieve audit logs for an incident.
        
        Args:
            incident_id: Incident ID to get logs for
        
        Returns:
            List of audit log entries
        """
        if not self.audit_service:
            logger.warning("Audit service not available")
            return []
        if incident_id:
            return await self.audit_service.get_incident_audit_trail(incident_id)
        return []


def create_agent(
    config: Optional[AutoResolutionConfig] = None,
    enable_audit: bool = True,
    enable_notifications: bool = True
) -> BusinessLogicAgent:
    """
    Factory function to create a BusinessLogicAgent instance.
    
    Args:
        config: Auto-resolution configuration
        enable_audit: Enable audit logging
        enable_notifications: Enable notifications
    
    Returns:
        Configured BusinessLogicAgent instance
    """
    return BusinessLogicAgent(
        config=config,
        enable_audit=enable_audit,
        enable_notifications=enable_notifications
    )
