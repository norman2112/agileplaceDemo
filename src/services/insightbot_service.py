"""
InsightBot service - analyzes incidents and surfaces AI-driven solution suggestions.
"""
import logging
import time
from typing import Dict, List, Any, Tuple
from uuid import uuid4

from src.models.incident import Incident, IncidentCategory, IncidentPriority
from src.models.insightbot import (
    SolutionSuggestion,
    SuggestionRequest,
    SuggestionResponse,
    SuggestionFeedbackRequest,
    SuggestionFeedback,
    SuggestionConfidenceLabel,
)

logger = logging.getLogger(__name__)


class InsightBotService:
    """Service responsible for InsightBot solution suggestions and learning loop."""

    def __init__(self):
        self._historical_patterns: Dict[IncidentCategory, List[Dict[str, Any]]] = (
            self._seed_historical_patterns()
        )
        self._feedback_store: List[SuggestionFeedback] = []
        self._pattern_learning_state: Dict[str, Dict[str, float]] = {}

    async def suggest_solutions(
        self,
        incident: Incident,
        limit: int = 3,
    ) -> SuggestionResponse:
        """Generate InsightBot solution suggestions for a new incident."""
        start_time = time.time()
        logger.info("InsightBot generating solutions for incident %s", incident.incident_id)

        patterns = self._historical_patterns.get(incident.category, [])
        scored_patterns: List[Tuple[float, Dict[str, Any]]] = []

        for pattern in patterns:
            similarity = self._calculate_similarity(incident, pattern)
            confidence = self._calculate_confidence(incident, pattern, similarity)
            scored_patterns.append((confidence, pattern))

        scored_patterns.sort(key=lambda item: item[0], reverse=True)

        solutions: List[SolutionSuggestion] = []
        for confidence, pattern in scored_patterns[:limit]:
            solution = SolutionSuggestion(
                suggestion_id=str(uuid4()),
                incident_id=incident.incident_id,
                title=pattern["title"],
                summary=pattern["summary"],
                steps=pattern["steps"],
                confidence_score=round(confidence, 2),
                confidence_label=self._label_confidence(confidence),
                source_pattern_id=pattern["pattern_id"],
                related_incidents=pattern.get("related_incidents", []),
                estimated_resolution_time=pattern.get("estimated_resolution_time"),
            )
            solutions.append(solution)

        processing_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "InsightBot produced %d solutions for %s in %dms",
            len(solutions),
            incident.incident_id,
            processing_time_ms,
        )

        return SuggestionResponse(
            incident_id=incident.incident_id,
            solutions=solutions,
            total_solutions=len(solutions),
            scanned_historical_records=sum(
                len(entries) for entries in self._historical_patterns.values()
            ),
            processing_time_ms=processing_time_ms,
        )

    async def handle_request(self, request: SuggestionRequest) -> SuggestionResponse:
        """Public entry point that accepts a SuggestionRequest wrapper."""
        return await self.suggest_solutions(
            incident=request.incident,
            limit=request.max_suggestions,
        )

    async def record_feedback(
        self,
        feedback_request: SuggestionFeedbackRequest,
    ) -> SuggestionFeedback:
        """Store feedback from service desk agents and update learning weights."""
        logger.info(
            "InsightBot feedback received for suggestion %s",
            feedback_request.suggestion_id,
        )

        feedback = SuggestionFeedback(
            feedback_id=str(uuid4()),
            suggestion_id=feedback_request.suggestion_id,
            pattern_id=feedback_request.pattern_id,
            incident_id=feedback_request.incident_id,
            agent_id=feedback_request.agent_id,
            quality=feedback_request.quality,
            was_helpful=feedback_request.was_helpful,
            was_applied=feedback_request.was_applied,
            resolution_time_minutes=feedback_request.resolution_time_minutes,
            comments=feedback_request.comments,
        )

        self._feedback_store.append(feedback)
        self._update_learning_model(feedback)
        return feedback

    async def get_feedback_for_pattern(self, pattern_id: str) -> List[SuggestionFeedback]:
        """Retrieve feedback records for a specific solution pattern."""
        return [f for f in self._feedback_store if f.pattern_id == pattern_id]

    def _calculate_similarity(self, incident: Incident, pattern: Dict[str, Any]) -> float:
        """Lightweight similarity scoring between incoming incident and historical pattern."""
        score = 0.5 if incident.category == pattern["category"] else 0.0
        description = incident.description.lower()

        for keyword in pattern.get("keywords", []):
            if keyword in description:
                score += 0.1

        if incident.priority in pattern.get("high_success_priorities", []):
            score += 0.1

        return min(score, 1.0)

    def _calculate_confidence(
        self,
        incident: Incident,
        pattern: Dict[str, Any],
        similarity: float,
    ) -> float:
        """Blend similarity, historical success rate, and learning modifiers."""
        base_rate = pattern.get("success_rate", 0.6)
        learning_bonus = self._pattern_learning_state.get(pattern["pattern_id"], {}).get(
            "quality_modifier",
            0.0,
        )
        priority_multiplier = self._priority_multiplier(incident.priority)
        confidence = base_rate * priority_multiplier
        confidence += similarity * 0.2
        confidence += learning_bonus
        return max(0.05, min(confidence, 0.99))

    def _priority_multiplier(self, priority: IncidentPriority) -> float:
        """Favor higher priority incidents by boosting confidence emphasis."""
        mapping = {
            IncidentPriority.CRITICAL: 1.1,
            IncidentPriority.HIGH: 1.05,
            IncidentPriority.MEDIUM: 1.0,
            IncidentPriority.LOW: 0.95,
        }
        return mapping.get(priority, 1.0)

    def _label_confidence(self, confidence: float) -> SuggestionConfidenceLabel:
        """Translate numeric confidence into a human-friendly label."""
        if confidence >= 0.8:
            return SuggestionConfidenceLabel.HIGH
        if confidence >= 0.6:
            return SuggestionConfidenceLabel.MEDIUM
        return SuggestionConfidenceLabel.LOW

    def _seed_historical_patterns(self) -> Dict[IncidentCategory, List[Dict[str, Any]]]:
        """Static seed data representing historical successful resolutions."""
        return {
            IncidentCategory.NETWORK: [
                {
                    "pattern_id": "network_interface_reset",
                    "category": IncidentCategory.NETWORK,
                    "title": "Cycle unstable network interface",
                    "summary": "Restart the impacted interface and flush ARP cache to restore routing.",
                    "steps": [
                        "Identify degraded interface with 'ip -s link'.",
                        "Disable interface: 'ip link set dev <iface> down'.",
                        "Flush ARP cache: 'ip neigh flush dev <iface>'.",
                        "Re-enable interface: 'ip link set dev <iface> up'.",
                        "Validate connectivity and packet loss.",
                    ],
                    "success_rate": 0.88,
                    "estimated_resolution_time": 8,
                    "keywords": ["latency", "packet", "interface"],
                    "high_success_priorities": [
                        IncidentPriority.HIGH,
                        IncidentPriority.CRITICAL,
                    ],
                    "related_incidents": ["INC-2045", "INC-1980"],
                },
                {
                    "pattern_id": "dns_cache_flush",
                    "category": IncidentCategory.NETWORK,
                    "title": "Flush DNS cache on recursive resolvers",
                    "summary": "Clear resolver cache and revalidate upstream connectivity.",
                    "steps": [
                        "Check resolver status via 'systemctl status systemd-resolved'.",
                        "Flush cache: 'systemd-resolve --flush-caches'.",
                        "Restart resolver service if cache corruption suspected.",
                        "Validate recursive lookups for priority domains.",
                    ],
                    "success_rate": 0.76,
                    "estimated_resolution_time": 5,
                    "keywords": ["dns", "resolution", "lookup"],
                    "high_success_priorities": [IncidentPriority.MEDIUM, IncidentPriority.HIGH],
                    "related_incidents": ["INC-1732"],
                },
            ],
            IncidentCategory.DATABASE: [
                {
                    "pattern_id": "db_connection_pool_refresh",
                    "category": IncidentCategory.DATABASE,
                    "title": "Recycle saturated connection pools",
                    "summary": "Drain idle sessions and rebuild the pool to eliminate stale locks.",
                    "steps": [
                        "Review pool metrics from monitoring dashboard.",
                        "Disable new connections temporarily.",
                        "Terminate idle connections exceeding threshold.",
                        "Restart pool manager and re-enable traffic.",
                        "Monitor pool saturation for 10 minutes.",
                    ],
                    "success_rate": 0.9,
                    "estimated_resolution_time": 12,
                    "keywords": ["timeout", "pool", "connection", "lock"],
                    "high_success_priorities": [IncidentPriority.HIGH],
                    "related_incidents": ["INC-1500", "INC-1499"],
                }
            ],
            IncidentCategory.APPLICATION: [
                {
                    "pattern_id": "app_service_restart",
                    "category": IncidentCategory.APPLICATION,
                    "title": "Perform graceful application restart",
                    "summary": "Drain user traffic, cycle the service, and validate telemetry.",
                    "steps": [
                        "Notify stakeholders about restart plan.",
                        "Drain traffic by disabling load balancer node.",
                        "Restart application service via systemd.",
                        "Warm up caches and run smoke tests.",
                        "Re-enable node in load balancer and monitor errors.",
                    ],
                    "success_rate": 0.83,
                    "estimated_resolution_time": 15,
                    "keywords": ["error rate", "500", "crash"],
                    "high_success_priorities": [
                        IncidentPriority.MEDIUM,
                        IncidentPriority.HIGH,
                    ],
                    "related_incidents": ["INC-2101"],
                }
            ],
        }

    def _update_learning_model(self, feedback: SuggestionFeedback):
        """Adjust pattern weights based on agent feedback to simulate ML improvements."""
        state = self._pattern_learning_state.setdefault(
            feedback.pattern_id,
            {"quality_modifier": 0.0, "samples": 0},
        )

        delta_map = {
            "excellent": 0.05,
            "good": 0.03,
            "fair": 0.0,
            "poor": -0.04,
        }
        delta = delta_map[feedback.quality.value]
        if feedback.was_helpful:
            delta += 0.01
        if feedback.was_applied and feedback.was_helpful:
            delta += 0.02

        state["quality_modifier"] = max(-0.1, min(0.1, state["quality_modifier"] + delta))
        state["samples"] += 1
        logger.debug(
            "Updated learning state for %s -> %s",
            feedback.pattern_id,
            state,
        )
