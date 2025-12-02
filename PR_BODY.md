## Summary

Enable InsightBot chat prompts to generate analytics reports with visualization payloads, date-range controls, comparison metadata, and share-ready artifacts.

## Changes

- **API**: Adds `/api/v1/insightbot/chat/report` endpoint that relays chat prompts to the business logic agent.
- **Agent**: Adds natural-language inference for report type/time range and returns shareable chat responses.
- **Reporting**: Enriches reports with visualization specs, comparison windows, and export/share payloads for stakeholders.

## Testing

- pytest tests/test_reporting_service.py *(fails: pytest not installed in container)*
