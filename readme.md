# Incident Auto-Resolution System

A production-ready system for automatically resolving high-confidence IT incidents with comprehensive audit trails, notifications, and emergency controls.

## Overview

This system automatically executes resolution steps for routine incidents with high confidence scores (≥90% by default), enabling IT Operations teams to handle incidents more efficiently while maintaining full visibility and control.

## Features

### Core Capabilities
- ✅ **Confidence-Based Resolution**: Only auto-resolves incidents with ≥90% confidence score (configurable)
- ✅ **Comprehensive Audit Trail**: Every action is logged in detail for compliance and debugging
- ✅ **Automatic Notifications**: Incident creators are notified immediately upon auto-resolution
- ✅ **Category-Based Configuration**: Configure auto-resolution settings per incident category
- ✅ **Emergency Kill Switch**: Instantly disable all auto-resolutions with a single API call

### Safety & Control
- Configurable confidence thresholds per incident category
- Multiple retry attempts for failed resolutions
- Detailed logging of all resolution steps
- Rollback capability (ready for implementation)
- Rate limiting with max concurrent resolutions

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agileplaceDemo

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
```

### Running the Application

```bash
# Start the API server
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_auto_resolution_service.py
```

## Architecture

```
src/
├── models/              # Data models (Pydantic)
│   ├── incident.py      # Incident, resolution step models
│   ├── audit.py         # Audit log models
│   └── config.py        # Configuration models
├── services/            # Business logic
│   ├── auto_resolution_service.py  # Core auto-resolution logic
│   ├── audit_service.py            # Audit logging
│   ├── notification_service.py     # Notifications
│   └── config_service.py           # Configuration management
└── api/                 # FastAPI endpoints
    └── endpoints.py     # REST API definitions
```

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Incident Resolution
- `POST /api/v1/incidents/{incident_id}/auto-resolve` - Auto-resolve a single incident
- `POST /api/v1/incidents/batch-resolve` - Batch auto-resolve multiple incidents

### Configuration
- `GET /api/v1/config` - Get current configuration
- `PUT /api/v1/config` - Update configuration
- `GET /api/v1/config/category/{category}` - Get category-specific config

### Emergency Controls
- `POST /api/v1/config/kill-switch/activate` - **EMERGENCY**: Disable all auto-resolutions
- `POST /api/v1/config/kill-switch/deactivate` - Re-enable auto-resolutions

### Audit Logs
- `GET /api/v1/audit` - Query audit logs with filters
- `GET /api/v1/audit/incident/{incident_id}` - Get complete audit trail for incident

## Usage Examples

### Auto-Resolve an Incident

```python
import httpx

incident_data = {
    "incident_id": "INC-12345",
    "title": "Database connection pool exhausted",
    "description": "Application cannot connect to database",
    "category": "database",
    "priority": "high",
    "confidence_score": 0.95,
    "created_by": "user123"
}

response = httpx.post(
    "http://localhost:8000/api/v1/incidents/INC-12345/auto-resolve",
    json=incident_data
)

result = response.json()
print(f"Success: {result['success']}")
print(f"Message: {result['message']}")
```

### Activate Emergency Kill Switch

```python
response = httpx.post(
    "http://localhost:8000/api/v1/config/kill-switch/activate",
    params={
        "actor": "ops-admin",
        "reason": "High number of failed resolutions detected"
    }
)

config = response.json()
print(f"Auto-resolution enabled: {config['global_enabled']}")  # False
```

### Query Audit Logs

```python
response = httpx.get(
    "http://localhost:8000/api/v1/audit/incident/INC-12345"
)

audit_trail = response.json()
for entry in audit_trail:
    print(f"{entry['timestamp']} - {entry['action']}: {entry['details']}")
```

## Configuration

### Global Settings

```python
# Default confidence threshold (90%)
default_confidence_threshold = 0.90

# Emergency kill switch (enabled by default)
global_enabled = True

# Max concurrent auto-resolutions
max_concurrent_resolutions = 10
```

### Category-Specific Configuration

Each incident category can have custom settings:

```python
category_config = {
    "category": "database",
    "auto_resolution_enabled": True,
    "confidence_threshold": 0.95,  # Higher threshold for database
    "max_retry_attempts": 3,
    "notification_required": True
}
```

## Acceptance Criteria Status

| Requirement | Status | Implementation |
|------------|--------|----------------|
| System must only auto-resolve incidents with ≥90% confidence score | ✅ Complete | `AutoResolutionService.can_auto_resolve()` |
| All auto-resolution actions must be logged in detail | ✅ Complete | `AuditService` with comprehensive logging |
| System must notify incident creator of auto-resolution | ✅ Complete | `NotificationService.notify_auto_resolution()` |
| Auto-resolution must be configurable by incident category | ✅ Complete | `CategoryConfig` per incident type |
| Emergency kill switch to disable all auto-resolutions | ✅ Complete | `ConfigService.activate_kill_switch()` |

## Incident Categories

Supported incident categories:
- `network` - Network connectivity issues
- `database` - Database connection/performance issues
- `application` - Application errors and crashes
- `security` - Security-related incidents
- `infrastructure` - Infrastructure failures
- `user_access` - User authentication/authorization issues

## Safety Features

1. **Confidence Threshold**: Prevents low-confidence resolutions
2. **Kill Switch**: Immediate system-wide disable
3. **Audit Trail**: Complete history of all actions
4. **Notifications**: Real-time alerts for all resolutions
5. **Category Controls**: Fine-grained control per incident type
6. **Retry Logic**: Automatic retry for transient failures
7. **Error Handling**: Graceful degradation on failures

## Production Considerations

### Required Integrations

For production deployment, implement:

1. **Persistent Data Store**: Replace in-memory storage with PostgreSQL/MongoDB
2. **Message Queue**: Add Redis/RabbitMQ for async processing
3. **Notification Systems**: Integrate with email/Slack/PagerDuty
4. **Monitoring**: Add Prometheus metrics and Sentry error tracking
5. **Authentication**: Implement OAuth2/JWT for API security
6. **Rate Limiting**: Add request throttling
7. **Caching**: Implement Redis caching for config and audit queries

### Deployment

```bash
# Using Docker
docker build -t auto-resolution-system .
docker run -p 8000:8000 auto-resolution-system

# Using Gunicorn (production)
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test category
pytest -m unit
pytest -m integration

# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

## Monitoring & Observability

### Key Metrics to Track
- Auto-resolution success rate
- Average confidence scores
- Resolution time per category
- Kill switch activations
- Notification delivery rate
- API response times

### Audit Log Queries

The system provides comprehensive audit logs for:
- Resolution attempts and outcomes
- Configuration changes
- Kill switch activations
- Notification delivery
- System errors and failures

## Troubleshooting

### Common Issues

**Auto-resolution not triggering**
- Check if kill switch is active: `GET /api/v1/config`
- Verify confidence score meets threshold
- Check category-specific configuration

**Notifications not sending**
- Review audit logs for notification failures
- Check notification service configuration
- Verify recipient information is valid

**High failure rate**
- Review audit logs for error patterns
- Consider increasing confidence threshold
- Check resolution step implementations

## Security

- All configuration changes are audited
- Actor identification for all actions
- Kill switch for emergency situations
- Input validation on all API endpoints
- Error messages don't expose internal details

## Future Enhancements

- [ ] Machine learning model integration for confidence scoring
- [ ] Rollback automation for failed resolutions
- [ ] Advanced analytics and reporting dashboard
- [ ] Multi-tenant support
- [ ] Webhook support for external integrations
- [ ] Resolution playbook management UI

## Contributing

1. Follow existing code structure and patterns
2. Add tests for all new features
3. Update documentation
4. Ensure all tests pass before submitting
5. Follow Python PEP 8 style guidelines

## License

[Your License Here]

## Support

For issues and questions:
- Create an issue in the repository
- Contact the IT Operations team
- Review the audit logs for detailed error information
