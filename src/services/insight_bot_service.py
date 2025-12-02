import logging
from collections import defaultdict
from datetime import date
from typing import Dict, List, Tuple

from src.models.insightbot import (
    RequestPayload,
    TeamMemberContext,
    NotificationPreference,
    NotificationPreferenceUpdate,
    NotificationResult,
    FeedbackPayload,
    FeedbackResponse,
    RequestPriority,
)


logger = logging.getLogger(__name__)


class InsightBotService:
    def __init__(self):
        self._preferences: Dict[str, NotificationPreference] = {}
        self._feedback_bias: Dict[str, float] = defaultdict(float)
        self._notification_counts: Dict[Tuple[str, date], int] = defaultdict(int)
        self._last_counter_reset = date.today()
        self._priority_rank = {
            RequestPriority.LOW: 0,
            RequestPriority.MEDIUM: 1,
            RequestPriority.HIGH: 2,
            RequestPriority.CRITICAL: 3,
        }

    async def evaluate_notifications(
        self,
        request: RequestPayload,
        team_members: List[TeamMemberContext]
    ) -> List[NotificationResult]:
        self._reset_counts_if_needed()
        results: List[NotificationResult] = []

        for member in team_members:
            preference = self._preferences.get(member.user_id) or self._create_default_preference(member.user_id)

            if self._priority_rank[request.priority] < self._priority_rank[preference.min_priority]:
                continue

            if request.category and request.category.lower() in self._to_lower_set(preference.muted_categories):
                continue

            if self._contains_muted_tag(request.tags, preference.muted_tags):
                continue

            base_score, reason = self._compute_relevance_score(request, member, preference)
            adjusted_score = self._apply_feedback_bias(base_score, member.user_id, preference)

            if adjusted_score < preference.relevance_threshold:
                continue

            if not self._can_notify(member.user_id, preference):
                continue

            channel = preference.preferred_channels[0] if preference.preferred_channels else "in_app"
            results.append(NotificationResult(
                user_id=member.user_id,
                request_id=request.request_id,
                summary=request.summary,
                priority=request.priority,
                channel=channel,
                relevance_score=round(adjusted_score, 3),
                reason=reason
            ))

        return results

    async def update_preferences(
        self,
        user_id: str,
        update: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        existing = self._preferences.get(user_id) or self._create_default_preference(user_id)
        data = existing.dict()
        data.update({k: v for k, v in update.dict(exclude_unset=True).items() if v is not None})
        preference = NotificationPreference(**data)
        self._preferences[user_id] = preference
        return preference

    async def get_preferences(self, user_id: str) -> NotificationPreference:
        return self._preferences.get(user_id) or self._create_default_preference(user_id)

    async def record_feedback(self, feedback: FeedbackPayload) -> FeedbackResponse:
        preference = self._preferences.get(feedback.user_id) or self._create_default_preference(feedback.user_id)
        adjustment = 0.05 if feedback.was_relevant else -0.05

        if not preference.learning_enabled:
            adjustment = 0.0

        new_bias = self._feedback_bias[feedback.user_id] + adjustment
        new_bias = max(-0.25, min(0.25, new_bias))
        self._feedback_bias[feedback.user_id] = new_bias

        logger.info(
            "InsightBot feedback recorded",
            extra={
                "user_id": feedback.user_id,
                "request_id": feedback.request_id,
                "adjustment": adjustment,
                "bias": new_bias,
            }
        )

        return FeedbackResponse(
            user_id=feedback.user_id,
            request_id=feedback.request_id,
            adjustment_applied=adjustment,
            total_bias=round(new_bias, 3)
        )

    def _compute_relevance_score(
        self,
        request: RequestPayload,
        member: TeamMemberContext,
        preference: NotificationPreference
    ) -> Tuple[float, str]:
        score = 0.0
        reasons = []

        tag_match_score, tag_reason = self._score_tags(request.tags, member.focus_tags, preference)
        if tag_match_score:
            score += tag_match_score
            reasons.append(tag_reason)

        keyword_score, keyword_reason = self._score_keywords(request, preference)
        if keyword_score:
            score += keyword_score
            reasons.append(keyword_reason)

        role_score, role_reason = self._score_roles(request, member)
        if role_score:
            score += role_score
            reasons.append(role_reason)

        priority_bonus = 0.15 * (self._priority_rank[request.priority] / 3)
        score += priority_bonus
        reasons.append(f"priority weight {request.priority.value}")

        focus_bonus = 0.1 if self._priority_rank[request.priority] >= self._priority_rank[member.current_priority_focus] else 0.0
        if focus_bonus:
            score += focus_bonus
            reasons.append("matches current focus")

        score = max(0.0, min(1.0, score))
        reason_text = "; ".join(reasons) if reasons else "baseline relevance"
        return score, reason_text

    def _score_tags(
        self,
        request_tags: List[str],
        focus_tags: List[str],
        preference: NotificationPreference
    ) -> Tuple[float, str]:
        if not request_tags:
            return 0.0, ""

        request_set = self._to_lower_set(request_tags)
        focus_set = self._to_lower_set(focus_tags)
        tracked_set = self._to_lower_set(preference.tracked_tags)

        overlap = request_set & (focus_set | tracked_set)
        if not overlap:
            return 0.0, ""

        overlap_ratio = len(overlap) / max(1, len(request_set))
        score = min(0.45, overlap_ratio * 0.45)
        reason = f"tags match {', '.join(sorted(overlap))}"
        return score, reason

    def _score_keywords(
        self,
        request: RequestPayload,
        preference: NotificationPreference
    ) -> Tuple[float, str]:
        if not preference.keywords:
            return 0.0, ""

        tokens = self._tokenize_request(request)
        keyword_hits = [kw for kw in preference.keywords if kw.lower() in tokens]
        if not keyword_hits:
            return 0.0, ""

        score = min(0.2, 0.05 * len(keyword_hits))
        reason = f"keywords {', '.join(keyword_hits)}"
        return score, reason

    def _score_roles(
        self,
        request: RequestPayload,
        member: TeamMemberContext
    ) -> Tuple[float, str]:
        if not member.roles:
            return 0.0, ""

        tokens = self._tokenize_request(request)
        role_hits = [role for role in member.roles if role.lower() in tokens]
        if not role_hits:
            return 0.0, ""

        score = min(0.2, 0.05 * len(role_hits))
        reason = f"role context {', '.join(role_hits)}"
        return score, reason

    def _apply_feedback_bias(
        self,
        base_score: float,
        user_id: str,
        preference: NotificationPreference
    ) -> float:
        bias = self._feedback_bias.get(user_id, 0.0)
        adjusted = base_score + bias
        if not preference.learning_enabled:
            adjusted = base_score
        return max(0.0, min(1.0, adjusted))

    def _can_notify(self, user_id: str, preference: NotificationPreference) -> bool:
        today = date.today()
        key = (user_id, today)
        count = self._notification_counts[key]
        if count >= preference.max_daily_notifications:
            return False
        self._notification_counts[key] = count + 1
        return True

    def _reset_counts_if_needed(self):
        today = date.today()
        if today != self._last_counter_reset:
            self._notification_counts.clear()
            self._last_counter_reset = today

    @staticmethod
    def _create_default_preference(user_id: str) -> NotificationPreference:
        return NotificationPreference(user_id=user_id)

    @staticmethod
    def _tokenize_request(request: RequestPayload) -> List[str]:
        text = f"{request.summary} {request.details} {' '.join(request.tags)}"
        clean = text.replace("/", " ").replace("-", " ")
        return [token.strip().lower() for token in clean.split() if token]

    @staticmethod
    def _to_lower_set(values: List[str]) -> set:
        return {value.lower() for value in values}

    def _contains_muted_tag(self, tags: List[str], muted_tags: List[str]) -> bool:
        if not muted_tags:
            return False
        tag_set = self._to_lower_set(tags)
        muted_set = self._to_lower_set(muted_tags)
        return bool(tag_set & muted_set)
