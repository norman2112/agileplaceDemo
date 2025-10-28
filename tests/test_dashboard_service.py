"""
Tests for the dashboard service.
"""
import pytest
from src.services.dashboard_service import DashboardService
from src.services.config_service import ConfigService
from src.services.audit_service import AuditService
from src.models.admin import UserRole, DashboardSettings


@pytest.fixture
def audit_service():
    """Create an audit service instance for testing."""
    return AuditService()


@pytest.fixture
def config_service(audit_service):
    """Create a config service instance for testing."""
    return ConfigService(audit_service=audit_service)


@pytest.fixture
def dashboard_service(config_service, audit_service):
    """Create a dashboard service instance for testing."""
    return DashboardService(
        config_service=config_service,
        audit_service=audit_service
    )


@pytest.mark.asyncio
async def test_authenticate_default_admin(dashboard_service):
    """Test that default admin user can authenticate."""
    response = await dashboard_service.authenticate_user("admin")
    
    assert response is not None
    assert response.user.username == "admin"
    assert response.user.role == UserRole.SYSTEM_ADMIN
    assert response.user.is_active is True
    
    # Admin should have all permissions
    assert response.permissions["view_config"] is True
    assert response.permissions["edit_config"] is True
    assert response.permissions["manage_users"] is True


@pytest.mark.asyncio
async def test_authenticate_nonexistent_user(dashboard_service):
    """Test that non-existent users cannot authenticate."""
    response = await dashboard_service.authenticate_user("nonexistent")
    
    assert response is None


@pytest.mark.asyncio
async def test_role_permissions():
    """Test that different roles have correct permissions."""
    service = DashboardService(
        config_service=None,  # Not needed for permission test
        audit_service=None
    )
    
    # Viewer permissions
    viewer_perms = service._get_role_permissions(UserRole.VIEWER)
    assert viewer_perms["view_config"] is True
    assert viewer_perms["edit_config"] is False
    assert viewer_perms["manage_users"] is False
    
    # Operator permissions
    operator_perms = service._get_role_permissions(UserRole.OPERATOR)
    assert operator_perms["view_config"] is True
    assert operator_perms["edit_config"] is True
    assert operator_perms["activate_kill_switch"] is True
    assert operator_perms["manage_users"] is False
    
    # Admin permissions
    admin_perms = service._get_role_permissions(UserRole.SYSTEM_ADMIN)
    assert all(admin_perms.values())  # All should be True


@pytest.mark.asyncio
async def test_get_dashboard_config_with_permission(dashboard_service):
    """Test that users with proper permissions can view config."""
    # Authenticate admin user
    auth_response = await dashboard_service.authenticate_user("admin")
    user_id = auth_response.user.user_id
    
    # Should be able to get config
    config = await dashboard_service.get_dashboard_config(user_id)
    
    assert config is not None
    assert hasattr(config, "global_enabled")


@pytest.mark.asyncio
async def test_create_user_as_admin(dashboard_service):
    """Test that admin can create new users."""
    # Get admin user ID
    auth_response = await dashboard_service.authenticate_user("admin")
    admin_id = auth_response.user.user_id
    
    # Create new operator user
    new_user = await dashboard_service.create_user(
        admin_user_id=admin_id,
        username="operator1",
        email="operator1@example.com",
        role=UserRole.OPERATOR
    )
    
    assert new_user.username == "operator1"
    assert new_user.role == UserRole.OPERATOR
    assert new_user.is_active is True


@pytest.mark.asyncio
async def test_create_user_duplicate_username(dashboard_service):
    """Test that duplicate usernames are rejected."""
    auth_response = await dashboard_service.authenticate_user("admin")
    admin_id = auth_response.user.user_id
    
    # Try to create user with existing username
    with pytest.raises(ValueError, match="already exists"):
        await dashboard_service.create_user(
            admin_user_id=admin_id,
            username="admin",  # Already exists
            email="another@example.com",
            role=UserRole.VIEWER
        )


@pytest.mark.asyncio
async def test_update_dashboard_settings(dashboard_service):
    """Test updating user dashboard settings."""
    auth_response = await dashboard_service.authenticate_user("admin")
    user_id = auth_response.user.user_id
    
    new_settings = DashboardSettings(
        theme="dark",
        notifications_enabled=False,
        show_advanced_settings=True
    )
    
    updated = await dashboard_service.update_dashboard_settings(user_id, new_settings)
    
    assert updated.theme == "dark"
    assert updated.notifications_enabled is False
    assert updated.show_advanced_settings is True


@pytest.mark.asyncio
async def test_get_config_change_logs_empty(dashboard_service):
    """Test getting config change logs when none exist."""
    auth_response = await dashboard_service.authenticate_user("admin")
    user_id = auth_response.user.user_id
    
    logs = await dashboard_service.get_config_change_logs(user_id)
    
    assert isinstance(logs, list)
    assert len(logs) == 0  # No changes made yet
