## Summary

Add InsightBot notification flow so team members receive request alerts scoped to their work and preferences.

## Changes

- Added request and notification models covering priorities, channels, preferences, and feedback signals.
- Implemented `InsightBotService` to score request relevance, honor user thresholds, and learn from feedback history.
- Extended `NotificationService` with InsightBot delivery support and a reusable generic dispatch helper.
- Wired InsightBot capabilities into `BusinessLogicAgent` for programmatic access to notifications, preferences, and feedback.

## Testing

Not run (not requested).
