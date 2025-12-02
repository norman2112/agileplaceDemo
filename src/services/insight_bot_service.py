import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from src.models.request import (
    WorkRequest,
    NotificationPreference,
    NotificationFeedback,
    RequestPriority,
)
from src.services.notification_service import NotificationService


logger = logging.getLogger(__name__)


class InsightBotService:
    """Delivers InsightBot notifications for relevant work requests."""

    _PRIORITY_BASELINES: Dict[RequestPriority, float] = {
        RequestPriority.LOW: 0.15,
        RequestPriority.MEDIUM: 0.35,
        RequestPriority.HIGH: 0.6,
        RequestPriority.CRITICAL: 0.8,
    }

    def __init__(self, notification_service: Optional[NotificationService] = None):
        self.notification_service = notification_service
        self._preferences: Dict[str, NotificationPreference] = {}
        self._interest_vectors: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._feedback_history: List[NotificationFeedback] = []

    async def process_request_update(
        self,
        request: WorkRequest,
        candidate_user_ids: List[str],
    ) -> List[Dict[str, str]]:
        notifications: List[Dict[str, str]] = []

        for user_id in candidate_user_ids:
            preference = self._get_or_create_preference(user_id)

            if self._is_muted(preference):
                continue

            relevance_score = self._calculate_relevance(user_id, request, preference)
            threshold = self._PRIORITY_BASELINES[preference.priority_threshold]

            if relevance_score < threshold:
                continue

            channels = [channel.value for channel in preference.channels]
            notification = {
                "user_id": user_id,
                "request_id": request.request_id,
                "summary": request.summary,
                "priority": request.priority.value,
                "score": f"{relevance_score:.2f}",
                "channels": channels,
            }
            notifications.append(notification)

            if self.notification_service:
                await self.notification_service.notify_request_relevance(
                    recipient=user_id,
                    request=request,
                    score=relevance_score,
                    channels=channels,
                )

        logger.info(
            "InsightBot generated %s notifications for request %s",
            len(notifications),
            request.request_id,
        )

        return notifications

    async def register_preferences(
        self,
        preference: NotificationPreference,
    ) -> NotificationPreference:
        self._preferences[preference.user_id] = preference
        return preference

    def get_preferences(self, user_id: str) -> NotificationPreference:
        return self._get_or_create_preference(user_id)

    async def record_feedback(
        self,
        feedback: NotificationFeedback,
    ) -> NotificationFeedback:
        self._feedback_history.append(feedback)

        preference = self._get_or_create_preference(feedback.user_id)
        self._adjust_threshold(preference, feedback.relevant)
        self._reinforce_tags(feedback)

        logger.info(
            "Captured InsightBot feedback for %s on request %s (relevant=%s)",
            feedback.user_id,
            feedback.request_id,
            feedback.relevant,
        )

        return feedback

    def _get_or_create_preference(self, user_id: str) -> NotificationPreference:
        if user_id not in self._preferences:
            self._preferences[user_id] = NotificationPreference(user_id=user_id)
        return self._preferences[user_id]

    def _calculate_relevance(
        self,
        user_id: str,
        request: WorkRequest,
        preference: NotificationPreference,
    ) -> float:
        score = self._PRIORITY_BASELINES[request.priority]

        if request.service_area and request.service_area in preference.service_area_focus:
            score += 0.2

        for tag in request.tags:
            score += preference.tag_weights.get(tag, 0.05)
            score += self._interest_vectors[user_id].get(tag, 0.0)

        return self._clamp(score)

    def _reinforce_tags(self, feedback: NotificationFeedback):
        interest_vector = self._interest_vectors[feedback.user_id]
        delta = 0.15 if feedback.relevant else -0.1

        for tag in feedback.tags:
            interest_vector[tag] = self._clamp(interest_vector.get(tag, 0.05) + delta)

    def _adjust_threshold(self, preference: NotificationPreference, relevant: bool):
        order = [
            RequestPriority.LOW,
            RequestPriority.MEDIUM,
            RequestPriority.HIGH,
            RequestPriority.CRITICAL,
        ]
        index = order.index(preference.priority_threshold)

        if relevant and index > 0:
            preference.priority_threshold = order[index - 1]
        elif not relevant and index < len(order) - 1:
            preference.priority_threshold = order[index + 1]

    def _is_muted(self, preference: NotificationPreference) -> bool:
        if not preference.mute_until:
            return False
        return preference.mute_until > datetime.utcnow()

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

