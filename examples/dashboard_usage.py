"""
Example usage of the Admin Configuration Dashboard.

This script demonstrates how to interact with the dashboard endpoints
for managing the AI Resolution Assistant configuration.

NOTE: This is a stub for demonstration purposes.
In production, this would be integrated with a web UI (React, Vue, etc.).
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.dashboard_service import DashboardService
from src.services.config_service import ConfigService
from src.services.audit_service import AuditService
from src.models.admin import UserRole, DashboardSettings


async def main():
    """Demonstrate dashboard functionality."""
    
    # Initialize services
    audit_service = AuditService()
    config_service = ConfigService(
        audit_service=audit_service,
        notification_service=None
    )
    dashboard_service = DashboardService(
        config_service=config_service,
        audit_service=audit_service
    )
    
    print("=" * 60)
    print("Admin Configuration Dashboard - Usage Example")
    print("=" * 60)
    
    # Step 1: Authenticate admin user
    print("\n1. Authenticating admin user...")
    auth_response = await dashboard_service.authenticate_user("admin")
    if auth_response:
        print(f"   ✓ User: {auth_response.user.username}")
        print(f"   ✓ Role: {auth_response.user.role.value}")
        print(f"   ✓ Permissions: {list(auth_response.permissions.keys())}")
        admin_id = auth_response.user.user_id
    else:
        print("   ✗ Authentication failed")
        return
    
    # Step 2: View current configuration
    print("\n2. Viewing current AI system configuration...")
    config = await dashboard_service.get_dashboard_config(admin_id)
    print(f"   ✓ Global AI System Enabled: {config.global_enabled}")
    print(f"   ✓ Default Confidence Threshold: {config.default_confidence_threshold}")
    print(f"   ✓ Max Concurrent Resolutions: {config.max_concurrent_resolutions}")
    print(f"   ✓ Configured Categories: {len(config.category_configs)}")
    
    # Step 3: Create a new operator user
    print("\n3. Creating a new operator user...")
    try:
        new_user = await dashboard_service.create_user(
            admin_user_id=admin_id,
            username="operator_alice",
            email="alice@example.com",
            role=UserRole.OPERATOR
        )
        print(f"   ✓ Created user: {new_user.username}")
        print(f"   ✓ Role: {new_user.role.value}")
        print(f"   ✓ User ID: {new_user.user_id}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Step 4: Update dashboard settings
    print("\n4. Updating dashboard settings...")
    new_settings = DashboardSettings(
        theme="dark",
        notifications_enabled=True,
        audit_log_retention_days=60,
        show_advanced_settings=True
    )
    updated_settings = await dashboard_service.update_dashboard_settings(
        admin_id, 
        new_settings
    )
    print(f"   ✓ Theme: {updated_settings.theme}")
    print(f"   ✓ Notifications: {updated_settings.notifications_enabled}")
    print(f"   ✓ Audit retention: {updated_settings.audit_log_retention_days} days")
    
    # Step 5: View configuration change logs
    print("\n5. Viewing configuration change logs...")
    logs = await dashboard_service.get_config_change_logs(admin_id, limit=10)
    if logs:
        print(f"   ✓ Found {len(logs)} configuration changes")
        for log in logs[:3]:
            print(f"     - {log.timestamp}: {log.action} by {log.username}")
    else:
        print("   ℹ No configuration changes logged yet")
    
    # Step 6: List all users
    print("\n6. Listing all dashboard users...")
    users = await dashboard_service.get_all_users(admin_id)
    print(f"   ✓ Total users: {len(users)}")
    for user in users:
        print(f"     - {user.username} ({user.role.value})")
    
    print("\n" + "=" * 60)
    print("Dashboard demonstration complete!")
    print("=" * 60)
    
    # Display next steps
    print("\nNext Steps for Full Implementation:")
    print("  • Implement proper authentication (JWT tokens, OAuth)")
    print("  • Add database persistence (PostgreSQL, MongoDB)")
    print("  • Build web UI with React/Vue")
    print("  • Add real-time WebSocket notifications")
    print("  • Implement category-specific configuration updates")
    print("  • Add audit log export functionality")


if __name__ == "__main__":
    asyncio.run(main())
