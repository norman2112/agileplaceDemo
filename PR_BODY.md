## Summary

Implemented daily incident summary functionality for InsightBot to enable managers to receive automated summaries of incidents across systems.

## Changes

### New Models (`src/models/daily_summary.py`)
- `DailySummaryConfig`: User configuration for delivery time, format, and systems
- `DailySummaryReport`: Report structure with incident counts, severity breakdown, and critical highlights
- `SeverityBreakdown`: Breakdown of incidents by severity level
- `CriticalIncidentHighlight`: Details for critical incidents requiring attention
- Support for Jira and ServiceNow as external systems

### New Service (`src/services/daily_summary_service.py`)
- `DailySummaryService`: Core service for generating daily summaries
- `ExternalSystemConnector`: Integration layer for Jira and ServiceNow
- Configurable delivery time and format (email/dashboard)
- Trend analysis of incident patterns
- Critical incident identification and highlighting

### API Endpoints (`src/api/endpoints.py`)
- `POST /api/v1/daily-summary/configure`: Configure summary settings for a user
- `GET /api/v1/daily-summary/config/{user_id}`: Retrieve user configuration
- `POST /api/v1/daily-summary/generate/{user_id}`: Generate summary on-demand

## Acceptance Criteria Met

✅ InsightBot connects to incident management systems (Jira, ServiceNow)  
✅ Daily summaries include incident count, severity breakdown, and trend analysis  
✅ Users can customize delivery time and format (email, dashboard)  
✅ Summaries highlight critical incidents requiring attention
