"""
Unit tests for configuration service and kill switch.
"""
import pytest
from src.models.config import AutoResolutionConfig, ConfigUpdateRequest, CategoryConfig
from src.models.incident import IncidentCategory
from src.services.config_service import ConfigService
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService


@pytest.fixture
def audit_service():
    """Create audit service fixture."""
    return AuditService()


@pytest.fixture
def notification_service(audit_service):
    """Create notification service fixture."""
    return NotificationService(audit_service=audit_service)


@pytest.fixture
def config_service(audit_service, notification_service):
    """Create config service fixture."""
    return ConfigService(
        audit_service=audit_service,
        notification_service=notification_service
    )


@pytest.mark.asyncio
async def test_default_configuration(config_service):
    """Test that default configuration is properly initialized."""
    config = await config_service.get_config()
    
    assert config.global_enabled is True
    assert config.default_confidence_threshold == 0.90
    assert len(config.category_configs) > 0


@pytest.mark.asyncio
async def test_kill_switch_activation(config_service):
    """Test emergency kill switch activation."""
    config = await config_service.activate_kill_switch(
        actor="admin",
        reason="Testing emergency shutdown"
    )
    
    assert config.global_enabled is False
    
    # Verify it's disabled for all categories
    for category in IncidentCategory:
        is_enabled = await config_service.is_auto_resolution_enabled(category)
        assert is_enabled is False


@pytest.mark.asyncio
async def test_kill_switch_deactivation(config_service):
    """Test kill switch deactivation."""
    # First activate
    await config_service.activate_kill_switch(actor="admin", reason="Test")
    
    # Then deactivate
    config = await config_service.deactivate_kill_switch(actor="admin")
    
    assert config.global_enabled is True


@pytest.mark.asyncio
async def test_update_global_threshold(config_service):
    """Test updating global confidence threshold."""
    update = ConfigUpdateRequest(default_confidence_threshold=0.95)
    
    config = await config_service.update_config(update, actor="admin")
    
    assert config.default_confidence_threshold == 0.95


@pytest.mark.asyncio
async def test_update_category_config(config_service):
    """Test updating category-specific configuration."""
    category_config = CategoryConfig(
        category=IncidentCategory.NETWORK,
        auto_resolution_enabled=False,
        confidence_threshold=0.88
    )
    
    update = ConfigUpdateRequest(category_config=category_config)
    config = await config_service.update_config(update, actor="admin")
    
    assert config.category_configs[IncidentCategory.NETWORK].confidence_threshold == 0.88
    assert config.category_configs[IncidentCategory.NETWORK].auto_resolution_enabled is False


@pytest.mark.asyncio
async def test_kill_switch_creates_audit_log(config_service, audit_service):
    """Test that kill switch activation creates audit log entries."""
    initial_count = len(audit_service._audit_log)
    
    await config_service.activate_kill_switch(actor="admin", reason="Test")
    
    assert len(audit_service._audit_log) > initial_count
    
    # Check that kill switch activation was logged
    system_audits = await audit_service.get_incident_audit_trail("SYSTEM")
    assert len(system_audits) > 0


@pytest.mark.asyncio
async def test_config_update_creates_audit_log(config_service, audit_service):
    """Test that configuration updates create audit log entries."""
    initial_count = len(audit_service._audit_log)
    
    update = ConfigUpdateRequest(default_confidence_threshold=0.92)
    await config_service.update_config(update, actor="admin")
    
    assert len(audit_service._audit_log) > initial_count
