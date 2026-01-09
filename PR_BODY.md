## Summary

- Added AI-powered incident detection and classification service that monitors multiple data sources (server logs, application logs, network metrics, system metrics, security alerts)
- Implemented anomaly detection with 95% confidence threshold and <5% false positive rate target
- Added automatic incident classification by severity (Critical, High, Medium, Low) and type (performance, security, availability, etc.)
- Extended Incident model with new fields for incident type, source, detection confidence, and auto-detection flag
- Added REST API endpoints for single and batch incident detection

## Test plan

- [ ] Verify `POST /api/v1/incidents/detect` endpoint accepts data and returns detected incidents
- [ ] Verify `POST /api/v1/incidents/detect/batch` endpoint processes multiple sources
- [ ] Verify `GET /api/v1/incidents/sources` returns list of monitored sources
- [ ] Confirm incidents are classified with correct priority based on severity signals
- [ ] Confirm incidents are classified with correct type based on anomaly indicators
- [ ] Verify detection confidence meets 95% threshold before creating incidents
