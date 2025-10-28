"""
Resolution recommendation service - generates resolution suggestions based on historical data.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4
import time

from src.models.incident import Incident, IncidentCategory
from src.models.recommendation import (
    ResolutionRecommendation,
    RecommendationResponse,
    RecommendationFeedback,
    FeedbackRequest,
    RecommendationStatus
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Service responsible for generating resolution recommendations based on historical data.
    
    Requirements:
    - Suggest at least one resolution for 75% of classified incidents
    - Return suggestions within 10 seconds
    - Provide step-by-step resolution instructions
    - Rank suggestions by historical success rate
    - Collect feedback on recommendation effectiveness
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        # In production, this would connect to:
        # - Historical incident database
        # - ML model service for similarity matching
        # - Recommendation training pipeline
        self._feedback_store: List[RecommendationFeedback] = []
        
    async def get_recommendations(
        self,
        incident: Incident,
        max_recommendations: int = 5,
        min_success_rate: float = 0.5
    ) -> RecommendationResponse:
        """
        Generate resolution recommendations for an incident.
        
        Args:
            incident: The incident requiring resolution
            max_recommendations: Maximum number of recommendations to return
            min_success_rate: Minimum historical success rate threshold
            
        Returns:
            RecommendationResponse with ranked recommendations
        """
        start_time = time.time()
        logger.info(f"Generating recommendations for incident {incident.incident_id}")
        
        try:
            # Audit: Recommendation request
            await self.audit_service.log_recommendation_request(
                incident_id=incident.incident_id,
                category=incident.category.value
            )
            
            # Fetch recommendations from historical data
            recommendations = await self._fetch_recommendations(
                incident=incident,
                max_recommendations=max_recommendations,
                min_success_rate=min_success_rate
            )
            
            # Rank by success rate (already done in fetch, but explicit for clarity)
            recommendations.sort(key=lambda r: r.success_rate, reverse=True)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Ensure we meet the 10-second requirement
            if processing_time_ms > 10000:
                logger.warning(
                    f"Recommendation generation took {processing_time_ms}ms, "
                    "exceeding 10-second requirement"
                )
            
            response = RecommendationResponse(
                incident_id=incident.incident_id,
                recommendations=recommendations,
                total_found=len(recommendations),
                processing_time_ms=processing_time_ms
            )
            
            # Audit: Recommendations generated
            await self.audit_service.log_recommendations_generated(
                incident_id=incident.incident_id,
                count=len(recommendations),
                processing_time_ms=processing_time_ms
            )
            
            logger.info(
                f"Generated {len(recommendations)} recommendations for incident "
                f"{incident.incident_id} in {processing_time_ms}ms"
            )
            
            return response
            
        except Exception as e:
            error_message = f"Failed to generate recommendations: {str(e)}"
            logger.error(
                f"Error generating recommendations for incident {incident.incident_id}: {error_message}",
                exc_info=True
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return RecommendationResponse(
                incident_id=incident.incident_id,
                recommendations=[],
                total_found=0,
                processing_time_ms=processing_time_ms,
                message=error_message
            )
    
    async def submit_feedback(self, feedback_request: FeedbackRequest) -> RecommendationFeedback:
        """
        Submit feedback on a recommendation's effectiveness.
        
        Args:
            feedback_request: The feedback details
            
        Returns:
            Created feedback record
        """
        logger.info(
            f"Received feedback for recommendation {feedback_request.recommendation_id} "
            f"from engineer {feedback_request.engineer_id}"
        )
        
        feedback = RecommendationFeedback(
            feedback_id=str(uuid4()),
            recommendation_id=feedback_request.recommendation_id,
            incident_id=feedback_request.incident_id,
            engineer_id=feedback_request.engineer_id,
            rating=feedback_request.rating,
            was_applied=feedback_request.was_applied,
            was_successful=feedback_request.was_successful,
            resolution_time_minutes=feedback_request.resolution_time_minutes,
            comments=feedback_request.comments
        )
        
        # Store feedback (in production, this would be persisted to a database)
        self._feedback_store.append(feedback)
        
        # Audit: Feedback submitted
        await self.audit_service.log_recommendation_feedback(
            feedback_id=feedback.feedback_id,
            recommendation_id=feedback.recommendation_id,
            incident_id=feedback.incident_id,
            rating=feedback.rating.value,
            was_successful=feedback.was_successful
        )
        
        # Update recommendation statistics (stub)
        await self._update_recommendation_stats(
            recommendation_id=feedback_request.recommendation_id,
            was_applied=feedback_request.was_applied,
            was_successful=feedback_request.was_successful
        )
        
        logger.info(f"Feedback {feedback.feedback_id} stored successfully")
        
        return feedback
    
    async def get_feedback_for_incident(self, incident_id: str) -> List[RecommendationFeedback]:
        """Get all feedback for recommendations of a specific incident."""
        return [f for f in self._feedback_store if f.incident_id == incident_id]
    
    async def get_feedback_stats(self, recommendation_id: str) -> dict:
        """
        Get aggregated feedback statistics for a recommendation.
        
        Returns:
            Dictionary with feedback metrics
        """
        feedback_list = [
            f for f in self._feedback_store 
            if f.recommendation_id == recommendation_id
        ]
        
        if not feedback_list:
            return {
                "recommendation_id": recommendation_id,
                "total_feedback": 0,
                "times_applied": 0,
                "success_rate": 0.0,
                "average_rating": None
            }
        
        times_applied = sum(1 for f in feedback_list if f.was_applied)
        successful_applications = sum(1 for f in feedback_list if f.was_successful)
        
        rating_values = {
            "very_helpful": 4,
            "helpful": 3,
            "somewhat_helpful": 2,
            "not_helpful": 1
        }
        
        ratings = [rating_values[f.rating.value] for f in feedback_list]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        return {
            "recommendation_id": recommendation_id,
            "total_feedback": len(feedback_list),
            "times_applied": times_applied,
            "success_rate": successful_applications / times_applied if times_applied > 0 else 0.0,
            "average_rating": avg_rating
        }
    
    async def _fetch_recommendations(
        self,
        incident: Incident,
        max_recommendations: int,
        min_success_rate: float
    ) -> List[ResolutionRecommendation]:
        """
        Fetch recommendations from historical data.
        
        In production, this would:
        - Query historical incident database
        - Use ML models to find similar incidents
        - Retrieve successful resolution patterns
        - Calculate success rates from feedback data
        """
        # Stub implementation: Return category-based recommendations
        recommendations = self._get_category_recommendations(incident.category)
        
        # Filter by success rate
        filtered = [r for r in recommendations if r.success_rate >= min_success_rate]
        
        # Sort by success rate and confidence
        filtered.sort(key=lambda r: (r.success_rate, r.confidence_score), reverse=True)
        
        # Limit to max_recommendations
        return filtered[:max_recommendations]
    
    def _get_category_recommendations(self, category: IncidentCategory) -> List[ResolutionRecommendation]:
        """
        Get predefined recommendations for a category.
        
        This is a stub - in production, this would query a recommendation database
        populated by ML models analyzing historical incident data.
        """
        # Stub data for different incident categories
        recommendations_map = {
            IncidentCategory.NETWORK: [
                ResolutionRecommendation(
                    recommendation_id=str(uuid4()),
                    incident_id="placeholder",
                    title="Network Interface Restart",
                    description="Restart the affected network interface to clear transient connection issues",
                    steps=[
                        "Identify the affected network interface",
                        "Check current interface status with 'ip addr show'",
                        "Bring interface down: 'sudo ifdown <interface>'",
                        "Wait 5 seconds",
                        "Bring interface up: 'sudo ifup <interface>'",
                        "Verify connectivity with ping test"
                    ],
                    success_rate=0.87,
                    confidence_score=0.92,
                    times_suggested=145,
                    times_applied=98,
                    estimated_resolution_time=5,
                    tags=["network", "interface", "restart"]
                ),
                ResolutionRecommendation(
                    recommendation_id=str(uuid4()),
                    incident_id="placeholder",
                    title="DNS Cache Flush",
                    description="Clear DNS cache to resolve name resolution issues",
                    steps=[
                        "Check current DNS configuration in /etc/resolv.conf",
                        "Flush local DNS cache: 'sudo systemd-resolve --flush-caches'",
                        "Verify DNS resolution with 'nslookup google.com'",
                        "If issue persists, restart systemd-resolved service"
                    ],
                    success_rate=0.79,
                    confidence_score=0.85,
                    times_suggested=112,
                    times_applied=74,
                    estimated_resolution_time=3,
                    tags=["network", "dns", "cache"]
                )
            ],
            IncidentCategory.DATABASE: [
                ResolutionRecommendation(
                    recommendation_id=str(uuid4()),
                    incident_id="placeholder",
                    title="Connection Pool Reset",
                    description="Reset database connection pool to clear stale connections",
                    steps=[
                        "Check current connection pool status",
                        "Identify stale or idle connections",
                        "Execute connection pool reset command",
                        "Verify new connections are established",
                        "Monitor connection pool metrics for 5 minutes"
                    ],
                    success_rate=0.91,
                    confidence_score=0.94,
                    times_suggested=203,
                    times_applied=165,
                    estimated_resolution_time=8,
                    tags=["database", "connection-pool", "reset"]
                ),
                ResolutionRecommendation(
                    recommendation_id=str(uuid4()),
                    incident_id="placeholder",
                    title="Query Cache Clear",
                    description="Clear query cache to resolve stale data issues",
                    steps=[
                        "Connect to database with admin credentials",
                        "Check cache size: 'SHOW STATUS LIKE \"Qcache%\"'",
                        "Flush query cache: 'FLUSH QUERY CACHE'",
                        "Verify cache is cleared",
                        "Monitor query performance"
                    ],
                    success_rate=0.82,
                    confidence_score=0.88,
                    times_suggested=89,
                    times_applied=61,
                    estimated_resolution_time=4,
                    tags=["database", "cache", "performance"]
                )
            ],
            IncidentCategory.APPLICATION: [
                ResolutionRecommendation(
                    recommendation_id=str(uuid4()),
                    incident_id="placeholder",
                    title="Application Service Restart",
                    description="Gracefully restart application service to clear memory leaks or deadlocks",
                    steps=[
                        "Check application logs for errors",
                        "Notify users of brief service interruption",
                        "Gracefully stop application: 'systemctl stop <service>'",
                        "Verify process has stopped completely",
                        "Start application: 'systemctl start <service>'",
                        "Verify service is running and healthy",
                        "Check logs for successful startup"
                    ],
                    success_rate=0.85,
                    confidence_score=0.89,
                    times_suggested=178,
                    times_applied=132,
                    estimated_resolution_time=10,
                    tags=["application", "restart", "service"]
                )
            ]
        }
        
        return recommendations_map.get(category, [])
    
    async def _update_recommendation_stats(
        self,
        recommendation_id: str,
        was_applied: bool,
        was_successful: bool
    ):
        """
        Update recommendation statistics based on feedback.
        
        In production, this would update the recommendation database
        and potentially trigger retraining of ML models.
        """
        # Stub implementation
        logger.info(
            f"Updating stats for recommendation {recommendation_id}: "
            f"applied={was_applied}, successful={was_successful}"
        )
        # In production: Update database, trigger analytics, etc.
        pass
