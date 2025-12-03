## Summary

Deliver InsightBot starter experience so service desk agents receive AI-driven solution suggestions backed by historical incident data and continuous feedback loops.

## Changes

- Added InsightBot data models plus service that matches new incidents to historical resolution patterns, generates confidence-scored solutions, and stores agent feedback for learning.
- Wired InsightBot access into the BusinessLogicAgent to request suggestions and submit feedback alongside existing services.
- Exposed `/api/v1/insightbot/suggestions` and `/api/v1/insightbot/feedback` endpoints so agents can request solutions and rate their quality without additional setup.
