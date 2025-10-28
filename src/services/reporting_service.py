"""
Reporting service - generates monthly reports and accuracy trend analysis.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import uuid4
from collections import defaultdict

from src.models.learning import (
    MonthlyPerformanceReport, CategoryPerformanceMetrics,
    EmergingPatternSuggestion, LearningMetrics
)
from src.services.learning_service import LearningService
from src.services.audit_service import AuditService
from src.models.audit import AuditAction

logger = logging.getLogger(__name__)


class ReportingService:
    """
    Service for generating performance reports and trend analysis.
    
    Responsibilities:
    - Generate monthly performance reports
    - Track accuracy trends over time
    - Identify performance improvements or degradations
    - Provide insights for decision-making
    """
    
    def __init__(self, learning_service: LearningService, audit_service: AuditService):
        self.learning_service = learning_service
        self.audit_service = audit_service
        # In production, store reports in a database
        self._report_store: List[MonthlyPerformanceReport] = []
    
    async def generate_monthly_report(
        self,
        month: int,
        year: int
    ) -> MonthlyPerformanceReport:
        """
        Generate comprehensive monthly performance report.
        
        The report includes:
        - Overall accuracy metrics
        - Category-specific performance
        - Accuracy trends throughout the month
        - Poor performing categories
        - Emerging patterns
        - Model retraining activities
        
        Args:
            month: Month (1-12)
            year: Year (e.g., 2024)
            
        Returns:
            Detailed monthly performance report
        """
        report_id = str(uuid4())
        
        logger.info(f"Generating monthly report for {year}-{month:02d}")
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        end_date = end_date - timedelta(seconds=1)  # Last second of the month
        
        # Get overall metrics for the period
        metrics = await self.learning_service.calculate_overall_metrics(start_date, end_date)
        
        # Query audit logs to get incident counts
        audit_entries = await self.audit_service.query_audit_log(
            query=type('AuditQuery', (), {
                'incident_id': None,
                'action': None,
                'start_date': start_date,
                'end_date': end_date,
                'limit': 10000,
                'offset': 0
            })()
        )
        
        # Count incidents by resolution type
        total_incidents = len(set(entry.incident_id for entry in audit_entries if entry.incident_id != "SYSTEM"))
        
        auto_resolved_incidents = len([
            entry for entry in audit_entries
            if entry.action == AuditAction.AUTO_RESOLUTION_SUCCESS
        ])
        
        manual_resolutions = total_incidents - auto_resolved_incidents
        
        # Calculate daily accuracy trend
        accuracy_trend = await self._calculate_daily_accuracy_trend(start_date, end_date)
        
        # Detect emerging patterns
        emerging_patterns = await self.learning_service.detect_emerging_patterns(
            min_frequency=3,
            min_confidence=0.65,
            lookback_days=30
        )
        
        # Get model retraining count
        training_history = await self.learning_service.get_training_history()
        model_retraining_count = len([
            t for t in training_history
            if start_date <= t.training_started_at <= end_date
        ])
        
        report = MonthlyPerformanceReport(
            report_id=report_id,
            month=month,
            year=year,
            total_incidents=total_incidents,
            auto_resolved_incidents=auto_resolved_incidents,
            manual_resolutions=manual_resolutions,
            overall_accuracy=metrics.overall_accuracy,
            classification_accuracy=metrics.classification_accuracy,
            resolution_success_rate=metrics.resolution_success_rate,
            category_performance=metrics.category_metrics,
            accuracy_trend=accuracy_trend,
            poor_performing_categories=metrics.poor_performing_categories,
            emerging_patterns=emerging_patterns,
            feedback_received_count=metrics.total_feedback_count,
            model_retraining_count=model_retraining_count,
            generated_at=datetime.utcnow()
        )
        
        self._report_store.append(report)
        
        logger.info(
            f"Monthly report generated: {report_id} "
            f"(accuracy: {report.overall_accuracy:.2%}, incidents: {total_incidents})"
        )
        
        return report
    
    async def _calculate_daily_accuracy_trend(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[float]:
        """
        Calculate daily accuracy values for trend analysis.
        
        Returns list of accuracy percentages, one per day in the period.
        """
        daily_accuracies = []
        current_date = start_date
        
        while current_date < end_date:
            next_date = current_date + timedelta(days=1)
            
            # Calculate metrics for this day
            try:
                day_metrics = await self.learning_service.calculate_overall_metrics(
                    current_date,
                    next_date
                )
                daily_accuracies.append(day_metrics.overall_accuracy)
            except Exception as e:
                logger.warning(f"Could not calculate metrics for {current_date.date()}: {e}")
                daily_accuracies.append(0.0)
            
            current_date = next_date
        
        return daily_accuracies
    
    async def get_accuracy_trends(
        self,
        months: int = 6
    ) -> Dict[str, List[float]]:
        """
        Get accuracy trends over multiple months.
        
        Args:
            months: Number of months to analyze (default: 6)
            
        Returns:
            Dictionary with trend data:
            - monthly_overall: Overall accuracy by month
            - monthly_classification: Classification accuracy by month
            - monthly_resolution: Resolution success rate by month
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        monthly_overall = []
        monthly_classification = []
        monthly_resolution = []
        
        # Calculate metrics for each month
        for i in range(months):
            month_start = end_date - timedelta(days=(months - i) * 30)
            month_end = month_start + timedelta(days=30)
            
            try:
                metrics = await self.learning_service.calculate_overall_metrics(
                    month_start,
                    month_end
                )
                
                monthly_overall.append(metrics.overall_accuracy)
                monthly_classification.append(metrics.classification_accuracy)
                monthly_resolution.append(metrics.resolution_success_rate)
            except Exception as e:
                logger.warning(f"Could not calculate metrics for month {i+1}: {e}")
                monthly_overall.append(0.0)
                monthly_classification.append(0.0)
                monthly_resolution.append(0.0)
        
        return {
            "monthly_overall": monthly_overall,
            "monthly_classification": monthly_classification,
            "monthly_resolution": monthly_resolution
        }
    
    async def get_category_performance_comparison(
        self,
        lookback_days: int = 90
    ) -> Dict[str, CategoryPerformanceMetrics]:
        """
        Get comparative performance metrics for all categories.
        
        Useful for identifying which categories need attention.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get all unique categories from feedback
        all_categories = set()
        for feedback in self.learning_service._feedback_store:
            all_categories.add(feedback.original_category)
            if feedback.correct_category:
                all_categories.add(feedback.correct_category)
        
        category_comparison = {}
        
        for category in all_categories:
            metrics = await self.learning_service.calculate_category_metrics(
                category,
                start_date,
                end_date
            )
            category_comparison[category] = metrics
        
        return category_comparison
    
    async def get_performance_summary(self) -> Dict[str, any]:
        """
        Get high-level performance summary.
        
        Returns quick stats for dashboards and monitoring.
        """
        # Get data for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        metrics = await self.learning_service.calculate_overall_metrics(start_date, end_date)
        
        # Get model info
        current_model = self.learning_service.get_current_model_version()
        training_history = await self.learning_service.get_training_history(limit=1)
        last_training = training_history[0] if training_history else None
        
        # Count recent feedback
        recent_feedback = [
            f for f in self.learning_service._feedback_store
            if f.submitted_at >= start_date
        ]
        
        return {
            "current_model_version": current_model,
            "last_training_date": last_training.training_completed_at if last_training else None,
            "overall_accuracy_30d": metrics.overall_accuracy,
            "classification_accuracy_30d": metrics.classification_accuracy,
            "resolution_success_rate_30d": metrics.resolution_success_rate,
            "total_feedback_30d": len(recent_feedback),
            "poor_performing_categories": metrics.poor_performing_categories,
            "categories_tracked": len(metrics.category_metrics),
            "generated_at": datetime.utcnow()
        }
    
    async def get_report_by_id(self, report_id: str) -> Optional[MonthlyPerformanceReport]:
        """Retrieve a specific report by ID."""
        for report in self._report_store:
            if report.report_id == report_id:
                return report
        return None
    
    async def list_reports(
        self,
        limit: int = 12,
        year: Optional[int] = None
    ) -> List[MonthlyPerformanceReport]:
        """
        List available reports.
        
        Args:
            limit: Maximum number of reports to return
            year: Filter by specific year
            
        Returns:
            List of reports, most recent first
        """
        reports = self._report_store
        
        if year:
            reports = [r for r in reports if r.year == year]
        
        # Sort by date (newest first)
        reports = sorted(
            reports,
            key=lambda r: (r.year, r.month),
            reverse=True
        )
        
        return reports[:limit]
    
    async def identify_improvement_opportunities(self) -> Dict[str, any]:
        """
        Analyze data to identify opportunities for improvement.
        
        Returns actionable insights such as:
        - Categories that need more training data
        - Categories with declining accuracy
        - Emerging patterns that should become categories
        - Confidence threshold adjustments needed
        """
        opportunities = {
            "low_data_categories": [],
            "declining_accuracy_categories": [],
            "high_priority_patterns": [],
            "threshold_adjustments": []
        }
        
        # Get recent performance
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        category_comparison = await self.get_category_performance_comparison(lookback_days=90)
        
        for category, metrics in category_comparison.items():
            # Identify categories with insufficient data
            if metrics.total_incidents < 20:
                opportunities["low_data_categories"].append({
                    "category": category,
                    "incident_count": metrics.total_incidents,
                    "recommendation": "Collect more training data"
                })
            
            # Identify categories with poor performance
            if metrics.classification_accuracy < 0.7 and metrics.total_incidents >= 10:
                opportunities["declining_accuracy_categories"].append({
                    "category": category,
                    "accuracy": metrics.classification_accuracy,
                    "total_incidents": metrics.total_incidents,
                    "recommendation": "Review and retrain model for this category"
                })
            
            # Suggest threshold adjustments
            if metrics.false_positive_count > metrics.total_incidents * 0.1:
                opportunities["threshold_adjustments"].append({
                    "category": category,
                    "current_threshold": 0.90,  # Would get from config
                    "suggested_threshold": 0.95,
                    "reason": f"High false positive rate ({metrics.false_positive_count} of {metrics.total_incidents})"
                })
        
        # Get emerging patterns
        patterns = await self.learning_service.detect_emerging_patterns(
            min_frequency=5,
            min_confidence=0.75,
            lookback_days=60
        )
        
        for pattern in patterns:
            if pattern.confidence >= 0.80:
                opportunities["high_priority_patterns"].append({
                    "suggested_category": pattern.suggested_category_name,
                    "frequency": pattern.pattern_frequency,
                    "confidence": pattern.confidence,
                    "recommendation": "Consider adding as new incident category"
                })
        
        logger.info(
            f"Identified {len(opportunities['low_data_categories'])} low-data categories, "
            f"{len(opportunities['declining_accuracy_categories'])} declining categories, "
            f"{len(opportunities['high_priority_patterns'])} high-priority patterns"
        )
        
        return opportunities
