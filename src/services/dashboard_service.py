"""
Dashboard service - manages admin dashboard access, user roles, and configuration UI.
"""
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.models.admin import (
    DashboardUser, UserRole, DashboardSettings, 
    ConfigChangeLog, DashboardAccessResponse
)
from src.models.config import AutoResolutionConfig, CategoryConfig
from src.services.config_service import ConfigService
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class DashboardService:
    """
    Service for managing the admin configuration dashboard.
    
    Features:
    - User authentication and role-based access control
    - Configuration change logging with user attribution
    - Dashboard settings management
    - Audit trail for all configuration changes
    """
    
    def __init__(
        self,
        config_service: ConfigService,
        audit_service: AuditService
    ):
        self.config_service = config_service
        self.audit_service = audit_service
        
        # In-memory user store (TODO: Replace with database in production)
        self._users: Dict[str, DashboardUser] = {}
        self._settings: Dict[str, DashboardSettings] = {}
        self._config_change_logs: List[ConfigChangeLog] = []
        
        # Initialize default admin user for testing
        self._initialize_default_users()
    
    def _initialize_default_users(self):
        """Initialize default users for development/testing."""
        default_admin = DashboardUser(
            user_id="admin-001",
            username="admin",
            email="admin@example.com",
            role=UserRole.SYSTEM_ADMIN,
            is_active=True
        )
        self._users[default_admin.user_id] = default_admin
    
    async def authenticate_user(self, username: str) -> Optional[DashboardAccessResponse]:
        """
        Authenticate user and return dashboard access info.
        
        TODO: Implement proper authentication with password/token validation.
        """
        # Simple username lookup for now
        user = next((u for u in self._users.values() if u.username == username), None)
        
        if not user or not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        
        # Get or create dashboard settings
        if user.user_id not in self._settings:
            self._settings[user.user_id] = DashboardSettings()
        
        # Determine permissions based on role
        permissions = self._get_role_permissions(user.role)
        
        return DashboardAccessResponse(
            user=user,
            permissions=permissions,
            dashboard_settings=self._settings[user.user_id]
        )
    
    def _get_role_permissions(self, role: UserRole) -> Dict[str, bool]:
        """Get permissions for a specific role."""
        base_permissions = {
            "view_config": False,
            "edit_config": False,
            "view_audit_log": False,
            "manage_users": False,
            "activate_kill_switch": False
        }
        
        if role == UserRole.VIEWER:
            base_permissions["view_config"] = True
            base_permissions["view_audit_log"] = True
        elif role == UserRole.OPERATOR:
            base_permissions["view_config"] = True
            base_permissions["edit_config"] = True
            base_permissions["view_audit_log"] = True
            base_permissions["activate_kill_switch"] = True
        elif role == UserRole.SYSTEM_ADMIN:
            # Admin has all permissions
            base_permissions = {k: True for k in base_permissions}
        
        return base_permissions
    
    async def get_dashboard_config(self, user_id: str) -> AutoResolutionConfig:
        """
        Get configuration for dashboard display.
        Validates user permissions before returning.
        """
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        permissions = self._get_role_permissions(user.role)
        if not permissions.get("view_config"):
            raise PermissionError(f"User {user.username} lacks permission to view configuration")
        
        return await self.config_service.get_config()
    
    async def update_dashboard_config(
        self,
        user_id: str,
        config_updates: Dict[str, Any]
    ) -> AutoResolutionConfig:
        """
        Update configuration via dashboard with user attribution and logging.
        """
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        permissions = self._get_role_permissions(user.role)
        if not permissions.get("edit_config"):
            raise PermissionError(f"User {user.username} lacks permission to edit configuration")
        
        # Get current config for tracking changes
        current_config = await self.config_service.get_config()
        previous_values = {}
        
        # Track what's being changed
        for key, value in config_updates.items():
            if hasattr(current_config, key):
                previous_values[key] = getattr(current_config, key)
        
        # Log the configuration change
        change_log = ConfigChangeLog(
            log_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user.user_id,
            username=user.username,
            action="config_update",
            config_section="auto_resolution",
            changes=config_updates,
            previous_values=previous_values
        )
        self._config_change_logs.append(change_log)
        
        logger.info(
            f"Configuration update by {user.username} (user_id: {user.user_id}): "
            f"{config_updates}"
        )
        
        # TODO: Apply updates via config_service
        # This is a stub - full implementation would parse and apply updates
        
        return current_config
    
    async def get_config_change_logs(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[ConfigChangeLog]:
        """
        Get configuration change logs for dashboard display.
        """
        user = self._users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        permissions = self._get_role_permissions(user.role)
        if not permissions.get("view_audit_log"):
            raise PermissionError(f"User {user.username} lacks permission to view audit logs")
        
        # Return most recent logs
        return sorted(
            self._config_change_logs,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]
    
    async def update_dashboard_settings(
        self,
        user_id: str,
        settings: DashboardSettings
    ) -> DashboardSettings:
        """Update user-specific dashboard settings."""
        if user_id not in self._users:
            raise ValueError(f"User {user_id} not found")
        
        self._settings[user_id] = settings
        logger.info(f"Dashboard settings updated for user {user_id}")
        
        return settings
    
    async def create_user(
        self,
        admin_user_id: str,
        username: str,
        email: str,
        role: UserRole
    ) -> DashboardUser:
        """
        Create a new dashboard user.
        Only system admins can create users.
        """
        admin = self._users.get(admin_user_id)
        if not admin or admin.role != UserRole.SYSTEM_ADMIN:
            raise PermissionError("Only system administrators can create users")
        
        # Check if username already exists
        if any(u.username == username for u in self._users.values()):
            raise ValueError(f"Username {username} already exists")
        
        new_user = DashboardUser(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            role=role,
            is_active=True
        )
        
        self._users[new_user.user_id] = new_user
        logger.info(f"User created: {username} with role {role.value} by {admin.username}")
        
        return new_user
    
    async def get_all_users(self, admin_user_id: str) -> List[DashboardUser]:
        """
        Get all dashboard users.
        Only system admins can list users.
        """
        admin = self._users.get(admin_user_id)
        if not admin or admin.role != UserRole.SYSTEM_ADMIN:
            raise PermissionError("Only system administrators can list users")
        
        return list(self._users.values())
