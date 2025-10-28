"""
Configuration service - manages auto-resolution configuration and kill switch.
"""
import logging
from typing import Optional

from src.models.config import AutoResolutionConfig, ConfigUpdateRequest, CategoryConfig
from src.models.incident import IncidentCategory
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Service for managing auto-resolution configuration.
    
    Features:
    - Emergency kill switch (global disable)
    - Category-specific configuration
    - Confidence threshold management
    - Configuration auditing
    """
    
    def __init__(
        self,
        audit_service: AuditService,
        notification_service: Optional[NotificationService] = None
    ):
        self.audit_service = audit_service
        self.notification_service = notification_service
        
        # Initialize with default configuration
        self._config = AutoResolutionConfig(
            global_enabled=True,
            default_confidence_threshold=0.90,
            category_configs=self._initialize_default_category_configs()
        )
    
    def _initialize_default_category_configs(self) -> dict:
        """Initialize default configurations for each incident category."""
        default_configs = {}
        
        for category in IncidentCategory:
            default_configs[category] = CategoryConfig(
                category=category,
                auto_resolution_enabled=True,
                confidence_threshold=0.90,
                max_retry_attempts=3,
                notification_required=True
            )
        
        return default_configs
    
    async def get_config(self) -> AutoResolutionConfig:
        """Get current auto-resolution configuration."""
        return self._config
    
    async def update_config(
        self,
        update_request: ConfigUpdateRequest,
        actor: str = "system"
    ) -> AutoResolutionConfig:
        """
        Update auto-resolution configuration.
        
        Args:
            update_request: Configuration update request
            actor: User or system making the change
            
        Returns:
            Updated configuration
        """
        changes = {}
        
        # Update global kill switch
        if update_request.global_enabled is not None:
            old_value = self._config.global_enabled
            self._config.global_enabled = update_request.global_enabled
            changes["global_enabled"] = {
                "old": old_value,
                "new": update_request.global_enabled
            }
            
            # Log kill switch changes
            if not update_request.global_enabled and old_value:
                await self.audit_service.log_kill_switch_activation(
                    actor=actor,
                    reason="Set via configuration update"
                )
                if self.notification_service:
                    await self.notification_service.notify_kill_switch_activated(
                        activated_by=actor,
                        reason="Configuration update"
                    )
            elif update_request.global_enabled and not old_value:
                await self.audit_service.log_kill_switch_deactivation(actor=actor)
        
        # Update default confidence threshold
        if update_request.default_confidence_threshold is not None:
            old_value = self._config.default_confidence_threshold
            self._config.default_confidence_threshold = update_request.default_confidence_threshold
            changes["default_confidence_threshold"] = {
                "old": old_value,
                "new": update_request.default_confidence_threshold
            }
        
        # Update category-specific configuration
        if update_request.category_config is not None:
            category = update_request.category_config.category
            old_config = self._config.category_configs.get(category)
            self._config.category_configs[category] = update_request.category_config
            changes[f"category_config.{category.value}"] = {
                "old": old_config.dict() if old_config else None,
                "new": update_request.category_config.dict()
            }
        
        # Log configuration changes
        if changes:
            await self.audit_service.log_config_update(
                actor=actor,
                config_changes=changes
            )
            logger.info(f"Configuration updated by {actor}: {changes}")
        
        return self._config
    
    async def activate_kill_switch(
        self,
        actor: str,
        reason: str = "Emergency activation"
    ) -> AutoResolutionConfig:
        """
        Activate emergency kill switch - disables all auto-resolutions immediately.
        
        Args:
            actor: User activating the kill switch
            reason: Reason for activation
            
        Returns:
            Updated configuration
        """
        logger.warning(f"Kill switch activated by {actor}: {reason}")
        
        self._config.global_enabled = False
        
        # Audit the kill switch activation
        await self.audit_service.log_kill_switch_activation(
            actor=actor,
            reason=reason
        )
        
        # Send urgent notifications
        if self.notification_service:
            await self.notification_service.notify_kill_switch_activated(
                activated_by=actor,
                reason=reason
            )
        
        return self._config
    
    async def deactivate_kill_switch(
        self,
        actor: str
    ) -> AutoResolutionConfig:
        """
        Deactivate emergency kill switch - re-enables auto-resolutions.
        
        Args:
            actor: User deactivating the kill switch
            
        Returns:
            Updated configuration
        """
        logger.info(f"Kill switch deactivated by {actor}")
        
        self._config.global_enabled = True
        
        # Audit the deactivation
        await self.audit_service.log_kill_switch_deactivation(actor=actor)
        
        return self._config
    
    async def get_category_config(
        self,
        category: IncidentCategory
    ) -> CategoryConfig:
        """Get configuration for a specific incident category."""
        return self._config.category_configs.get(
            category,
            CategoryConfig(category=category)
        )
    
    async def is_auto_resolution_enabled(
        self,
        category: Optional[IncidentCategory] = None
    ) -> bool:
        """
        Check if auto-resolution is enabled.
        
        Args:
            category: Optional category to check. If None, checks global setting.
            
        Returns:
            True if auto-resolution is enabled
        """
        if category:
            return self._config.is_enabled_for_category(category)
        
        return self._config.global_enabled
