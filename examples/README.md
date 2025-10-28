# Dashboard Usage Examples

This directory contains example scripts demonstrating how to use the Admin Configuration Dashboard.

## dashboard_usage.py

Demonstrates the core functionality of the dashboard service:

- User authentication and role-based access
- Viewing and managing configuration
- Creating new dashboard users
- Updating dashboard settings
- Accessing configuration change logs

### Running the Example

```bash
# From the workspace root
cd /workspace
python main.py &  # Start the API server

# In another terminal
PYTHONPATH=/workspace python3 examples/dashboard_usage.py
```

Or use the API directly via curl:

```bash
# Authenticate
curl -X POST http://localhost:8000/api/v1/dashboard/auth \
  -H "Content-Type: application/json" \
  -d '{"username": "admin"}'

# View configuration
curl "http://localhost:8000/api/v1/dashboard/config?user_id=admin-001"
```

### Interactive API Documentation

The easiest way to explore the dashboard endpoints is through the FastAPI auto-generated docs:

1. Start the server: `python main.py`
2. Navigate to: http://localhost:8000/docs
3. Find the "Dashboard" section in the API documentation
4. Try out the endpoints interactively

## Future Examples

Additional examples to be added:
- Web UI integration (React/Vue)
- Bulk configuration updates
- Audit log analysis
- Role management workflows
