## Summary

Introduced InsightBot notification pipeline so team members can receive intelligent request alerts tailored to their work.

## Changes

- Created InsightBot data models covering request payloads, team context, notification preferences, and feedback wiring
- Added InsightBot service with relevance scoring, preference controls, learning loop, and notification budgeting
- Extended FastAPI endpoints with InsightBot notification, preference, and feedback routes

## Key Features

- Content + tag analysis to match requests with relevant teammates
- Notifications always include request summary, priority, channel, and rationale
- User-configurable thresholds, delivery channels, and tag/keyword preferences
- Lightweight learning loop that boosts or suppresses future alerts based on explicit feedback

## Usage Example

```python
from src.models.insightbot import (
    InsightBotNotificationRequest,
    RequestPayload,
    TeamMemberContext,
    RequestPriority,
)
from src.services.insight_bot_service import InsightBotService

service = InsightBotService()
request = RequestPayload(
    request_id="REQ-42",
    summary="Database latency spike",
    details="Checkout API slowed after schema change",
    priority=RequestPriority.HIGH,
    tags=["database", "performance"],
)
team = [TeamMemberContext(user_id="alice", roles=["dba"], focus_tags=["database"])]
notifications = await service.evaluate_notifications(request, team)
```

## Technical Details

- Relevance scoring blends tag overlap, keyword matches, user focus, and priority weighting
- Per-user preferences stored in-memory with merge-on-update semantics
- Feedback adjusts personal bias within ±0.25 to refine alert thresholds without retraining models
- Daily notification budgets guard against noisy floods while still honoring high-priority work
