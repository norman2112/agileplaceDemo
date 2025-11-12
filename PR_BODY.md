## Summary

Created headless Business Logic Agent for programmatic BL integration without web interface dependencies.

## Changes

- **Added** `src/bl_agent.py`: Non-UI agent providing programmatic access to core business logic services
  - Wraps auto-resolution, insights, recommendations, and reporting services
  - Enables direct Python API usage without FastAPI/web server
  - Factory function `create_agent()` for easy instantiation
  - Configurable audit and notification support

## Key Features

- **Incident Resolution**: Direct programmatic incident resolution and status checking
- **Insights Generation**: Generate analytics and insights without web endpoints
- **Recommendations**: Get resolution recommendations programmatically
- **Reporting**: Generate operational reports via code
- **Configuration Management**: Control thresholds, categories, and kill switch
- **Audit Trail**: Optional audit logging for all operations

## Usage Example

```python
from src.bl_agent import create_agent
from src.models.incident import Incident, IncidentCategory, IncidentPriority

# Create agent instance
agent = create_agent()

# Resolve an incident
incident = Incident(
    incident_id="INC-001",
    title="Service Down",
    description="API not responding",
    category=IncidentCategory.APPLICATION,
    priority=IncidentPriority.HIGH,
    confidence_score=0.95,
    created_by="user_123"
)

response = await agent.resolve_incident(incident)
```

## Technical Details

- No FastAPI or uvicorn dependencies required
- Async/await support maintained
- All existing service integrations preserved
- Backward compatible with existing codebase
