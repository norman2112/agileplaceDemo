import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
import time
import random

from src.models.insight import (
    TrendAnalysis, AnomalyDetection, Prediction, MetricSummary,
    InsightFeedback, AnomalyThresholdConfig, InsightsRequest, InsightsResponse,
    ServiceArea, TrendDirection, AnomalyType, InsightType, FeedbackType
)

logger = logging.getLogger(__name__)


class InsightsService:
    
    def __init__(self):
        self._feedback_store: List[InsightFeedback] = []
        self._threshold_configs: Dict[str, AnomalyThresholdConfig] = {}
        self._initialize_default_thresholds()
    
    def _initialize_default_thresholds(self):
        default_thresholds = [
            AnomalyThresholdConfig(
                service_area=ServiceArea.NETWORK,
                metric_name="response_time_ms",
                threshold_value=500.0,
                threshold_type="absolute"
            ),
            AnomalyThresholdConfig(
                service_area=ServiceArea.DATABASE,
                metric_name="query_time_ms",
                threshold_value=1000.0,
                threshold_type="absolute"
            ),
            AnomalyThresholdConfig(
                service_area=ServiceArea.APPLICATION,
                metric_name="error_rate",
                threshold_value=5.0,
                threshold_type="percentage"
            )
        ]
        for config in default_thresholds:
            key = f"{config.service_area.value}:{config.metric_name}"
            self._threshold_configs[key] = config
    
    async def generate_insights(self, request: InsightsRequest) -> InsightsResponse:
        start_time = time.time()
        logger.info(f"Generating insights for {request.time_period_days} days")
        
        service_areas = request.service_areas or list(ServiceArea)
        
        trends = []
        anomalies = []
        predictions = []
        
        if request.include_trends:
            trends = await self._analyze_trends(service_areas, request.time_period_days)
        
        if request.include_anomalies:
            anomalies = await self._detect_anomalies(service_areas)
        
        if request.include_predictions:
            predictions = await self._generate_predictions(service_areas)
        
        summary = await self._generate_summary(service_areas, request.time_period_days, trends, anomalies)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Generated insights in {processing_time_ms}ms")
        
        return InsightsResponse(
            trends=trends,
            anomalies=anomalies,
            predictions=predictions,
            summary=summary,
            processing_time_ms=processing_time_ms
        )
    
    async def _analyze_trends(
        self,
        service_areas: List[ServiceArea],
        time_period_days: int
    ) -> List[TrendAnalysis]:
        trends = []
        
        for area in service_areas:
            metrics = self._get_metrics_for_area(area)
            
            for metric_name in metrics:
                data_points = self._generate_mock_time_series(time_period_days)
                direction, change_pct = self._calculate_trend(data_points)
                
                trend = TrendAnalysis(
                    analysis_id=str(uuid4()),
                    service_area=area,
                    metric_name=metric_name,
                    direction=direction,
                    change_percentage=change_pct,
                    confidence_score=self._calculate_confidence(data_points),
                    time_period_days=time_period_days,
                    data_points=data_points,
                    summary=self._generate_trend_summary(area, metric_name, direction, change_pct)
                )
                trends.append(trend)
        
        return trends
    
    async def _detect_anomalies(self, service_areas: List[ServiceArea]) -> List[AnomalyDetection]:
        anomalies = []
        
        for area in service_areas:
            metrics = self._get_metrics_for_area(area)
            
            for metric_name in metrics:
                key = f"{area.value}:{metric_name}"
                config = self._threshold_configs.get(key)
                
                if not config or not config.enabled:
                    continue
                
                actual_value = self._get_current_metric_value(area, metric_name)
                
                if actual_value > config.threshold_value * 1.2:
                    anomaly_type = AnomalyType.SPIKE
                    deviation = ((actual_value - config.threshold_value) / config.threshold_value) * 100
                    severity = min(deviation / 100, 1.0)
                    
                    anomaly = AnomalyDetection(
                        anomaly_id=str(uuid4()),
                        service_area=area,
                        metric_name=metric_name,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        threshold_value=config.threshold_value,
                        actual_value=actual_value,
                        deviation_percentage=deviation,
                        explanation=self._generate_anomaly_explanation(area, metric_name, anomaly_type, deviation),
                        recommended_actions=self._get_anomaly_actions(area, metric_name, anomaly_type)
                    )
                    anomalies.append(anomaly)
        
        return anomalies
    
    async def _generate_predictions(self, service_areas: List[ServiceArea]) -> List[Prediction]:
        predictions = []
        
        for area in service_areas:
            metrics = self._get_metrics_for_area(area)
            
            for metric_name in metrics[:2]:
                historical_data = self._generate_mock_time_series(30)
                predicted_value = self._forecast_value(historical_data)
                confidence_interval = predicted_value * 0.15
                
                prediction = Prediction(
                    prediction_id=str(uuid4()),
                    service_area=area,
                    metric_name=metric_name,
                    predicted_value=predicted_value,
                    confidence_interval_low=predicted_value - confidence_interval,
                    confidence_interval_high=predicted_value + confidence_interval,
                    confidence_score=0.75 + random.random() * 0.2,
                    forecast_horizon_days=7,
                    summary=self._generate_prediction_summary(area, metric_name, predicted_value),
                    factors=self._identify_prediction_factors(area, metric_name)
                )
                predictions.append(prediction)
        
        return predictions
    
    async def _generate_summary(
        self,
        service_areas: List[ServiceArea],
        time_period_days: int,
        trends: List[TrendAnalysis],
        anomalies: List[AnomalyDetection]
    ) -> MetricSummary:
        
        key_metrics = {}
        for area in service_areas:
            key_metrics[area.value] = {
                "incident_count": random.randint(10, 50),
                "avg_resolution_time": random.randint(15, 120),
                "success_rate": round(0.85 + random.random() * 0.1, 2)
            }
        
        insights = []
        if trends:
            increasing_trends = [t for t in trends if t.direction == TrendDirection.INCREASING]
            if increasing_trends:
                insights.append(f"{len(increasing_trends)} metrics showing upward trends")
        
        if anomalies:
            critical_anomalies = [a for a in anomalies if a.severity > 0.7]
            if critical_anomalies:
                insights.append(f"{len(critical_anomalies)} critical anomalies detected")
        
        action_items = []
        for anomaly in anomalies[:3]:
            action_items.extend(anomaly.recommended_actions)
        
        summary_text = self._generate_executive_summary(key_metrics, insights, action_items)
        
        return MetricSummary(
            summary_id=str(uuid4()),
            service_area=service_areas[0] if service_areas else ServiceArea.APPLICATION,
            time_period_days=time_period_days,
            key_metrics=key_metrics,
            insights=insights,
            action_items=action_items[:5],
            summary_text=summary_text
        )
    
    async def submit_feedback(self, feedback: InsightFeedback) -> InsightFeedback:
        logger.info(f"Received feedback for insight {feedback.insight_id}")
        self._feedback_store.append(feedback)
        await self._update_ai_model(feedback)
        return feedback
    
    async def configure_threshold(self, config: AnomalyThresholdConfig) -> AnomalyThresholdConfig:
        key = f"{config.service_area.value}:{config.metric_name}"
        self._threshold_configs[key] = config
        logger.info(f"Updated threshold for {key}: {config.threshold_value}")
        return config
    
    async def get_thresholds(self, service_area: Optional[ServiceArea] = None) -> List[AnomalyThresholdConfig]:
        if service_area:
            return [c for c in self._threshold_configs.values() if c.service_area == service_area]
        return list(self._threshold_configs.values())
    
    async def _update_ai_model(self, feedback: InsightFeedback):
        logger.info(f"Updating AI model with feedback: {feedback.feedback_type.value}")
    
    def _get_metrics_for_area(self, area: ServiceArea) -> List[str]:
        metrics_map = {
            ServiceArea.NETWORK: ["response_time_ms", "packet_loss_rate", "bandwidth_utilization"],
            ServiceArea.DATABASE: ["query_time_ms", "connection_count", "cache_hit_rate"],
            ServiceArea.APPLICATION: ["error_rate", "request_count", "cpu_usage"],
            ServiceArea.SECURITY: ["failed_auth_attempts", "vulnerability_count", "threat_level"],
            ServiceArea.INFRASTRUCTURE: ["disk_usage", "memory_usage", "uptime_percentage"],
            ServiceArea.USER_ACCESS: ["active_users", "session_duration", "access_denied_count"]
        }
        return metrics_map.get(area, [])
    
    def _generate_mock_time_series(self, days: int) -> List[Dict[str, Any]]:
        base_value = random.uniform(50, 100)
        trend = random.uniform(-2, 2)
        
        data_points = []
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=days - i)
            value = base_value + (trend * i) + random.uniform(-10, 10)
            data_points.append({
                "date": date.isoformat(),
                "value": max(0, round(value, 2))
            })
        
        return data_points
    
    def _calculate_trend(self, data_points: List[Dict[str, Any]]) -> tuple[TrendDirection, float]:
        if len(data_points) < 2:
            return TrendDirection.STABLE, 0.0
        
        first_value = data_points[0]["value"]
        last_value = data_points[-1]["value"]
        
        change_pct = ((last_value - first_value) / first_value) * 100 if first_value > 0 else 0
        
        if abs(change_pct) < 5:
            return TrendDirection.STABLE, change_pct
        elif change_pct > 0:
            return TrendDirection.INCREASING, change_pct
        else:
            return TrendDirection.DECREASING, change_pct
    
    def _calculate_confidence(self, data_points: List[Dict[str, Any]]) -> float:
        return 0.8 + random.random() * 0.15
    
    def _get_current_metric_value(self, area: ServiceArea, metric_name: str) -> float:
        return random.uniform(100, 1500)
    
    def _forecast_value(self, historical_data: List[Dict[str, Any]]) -> float:
        if not historical_data:
            return 0.0
        recent_values = [d["value"] for d in historical_data[-7:]]
        return sum(recent_values) / len(recent_values) * (1 + random.uniform(-0.1, 0.2))
    
    def _generate_trend_summary(
        self,
        area: ServiceArea,
        metric: str,
        direction: TrendDirection,
        change_pct: float
    ) -> str:
        return f"{area.value.replace('_', ' ').title()} {metric.replace('_', ' ')} is {direction.value} by {abs(change_pct):.1f}% over the period."
    
    def _generate_anomaly_explanation(
        self,
        area: ServiceArea,
        metric: str,
        anomaly_type: AnomalyType,
        deviation: float
    ) -> str:
        return f"Detected {anomaly_type.value} in {area.value} {metric}: {deviation:.1f}% above expected threshold."
    
    def _get_anomaly_actions(
        self,
        area: ServiceArea,
        metric: str,
        anomaly_type: AnomalyType
    ) -> List[str]:
        return [
            f"Investigate {area.value} {metric} root cause",
            "Review recent configuration changes",
            "Check system logs for errors",
            "Consider scaling resources if needed"
        ]
    
    def _generate_prediction_summary(
        self,
        area: ServiceArea,
        metric: str,
        predicted_value: float
    ) -> str:
        return f"Predicted {area.value} {metric} for next 7 days: {predicted_value:.2f}"
    
    def _identify_prediction_factors(self, area: ServiceArea, metric: str) -> List[str]:
        return [
            "Historical trend patterns",
            "Seasonal variations",
            "Recent incident frequency",
            "System load patterns"
        ]
    
    def _generate_executive_summary(
        self,
        key_metrics: Dict[str, Any],
        insights: List[str],
        action_items: List[str]
    ) -> str:
        summary_parts = [
            "Executive Summary:",
            f"Analyzed {len(key_metrics)} service areas.",
            " ".join(insights) if insights else "Overall system performance is stable.",
            f"Recommended {len(action_items)} priority actions." if action_items else "No critical actions required."
        ]
        return " ".join(summary_parts)
