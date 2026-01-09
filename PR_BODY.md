## Summary

- Added pattern detection service to automatically identify recurring incident patterns based on error messages, system components, and historical data
- Implements analysis within 30-second timeout with confidence scoring
- Triggers automated responses for high-confidence pattern matches (≥70-90% depending on pattern type)
- Includes comprehensive audit logging for all pattern analysis activities

## Changes

- **New `src/models/pattern.py`**: Data models for patterns, matches, and analysis requests/responses
- **New `src/services/pattern_detection_service.py`**: Core service implementing pattern detection with 8 pre-configured common incident patterns
- **Updated `src/models/audit.py`**: Added audit action types for pattern detection events
- **Updated `src/services/audit_service.py`**: Added helper methods for pattern-related audit logging
- **Updated `src/api/endpoints.py`**: Added REST API endpoints for pattern analysis and management

## API Endpoints

- `POST /api/v1/patterns/analyze` - Analyze an incident for matching patterns
- `GET /api/v1/patterns` - List all registered patterns
- `GET /api/v1/patterns/{pattern_id}` - Get a specific pattern
- `POST /api/v1/patterns` - Register a new pattern
- `GET /api/v1/patterns/statistics/summary` - Get pattern detection statistics

## Test Plan

- [x] Pattern detection service imports successfully
- [x] Pattern analysis completes within 30-second timeout
- [x] Confidence scores calculated correctly
- [x] High-confidence matches trigger automated responses
- [x] Audit trail created for pattern matches
- [x] All existing tests pass (37 tests)
