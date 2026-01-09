## Summary

Implements automatic notification system for incident resolution to keep end users informed when their incidents are resolved by the AI system.

- Added `NotificationService` enhancements supporting email and in-app notification channels
- Created notification models with resolution summary, reopen capability, and quality rating support
- Added API endpoints for users to rate resolutions and reopen incidents if issues persist
- Added new audit actions (`RESOLUTION_RATED`, `INCIDENT_REOPENED`) for tracking user feedback

## Acceptance Criteria

- [x] Notifications sent within 2 minutes of resolution (implemented via immediate async notification)
- [x] Includes summary of what was fixed (resolution_summary field with step descriptions)
- [x] Provides option to reopen if issue persists (reopen_link and `/api/v1/incidents/{id}/reopen` endpoint)
- [x] Supports email and in-app notifications (NotificationChannel enum with both options)
- [x] Allows users to rate the resolution quality (`/api/v1/incidents/{id}/rate` endpoint with ResolutionRating options)

## Test Plan

- [ ] Verify notification is sent when an incident is auto-resolved
- [ ] Confirm email and in-app notification channels are triggered
- [ ] Test reopen incident endpoint returns incident with OPEN status
- [ ] Test rating endpoint accepts valid ratings and stores feedback
- [ ] Verify audit trail captures resolution ratings and incident reopens
