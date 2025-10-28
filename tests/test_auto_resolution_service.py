"""
Unit tests for auto-resolution service.
"""
import pytest
from datetime import datetime
from src.models.incident import Incident, IncidentCategory, IncidentPriority, IncidentStatus
from src.models.config import AutoResolutionConfig, CategoryConfig
from src.services.auto_resolution_service import AutoResolutionService
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
def config():
    """Create default configuration fixture."""
    return AutoResolutionConfig(
        global_enabled=True,
        default_confidence_threshold=0.90
    )


@pytest.fixture
def auto_resolution_service(config, audit_service, notification_service):
    """Create auto-resolution service fixture."""
    return AutoResolutionService(
        config=config,
        audit_service=audit_service,
        notification_service=notification_service
    )


@pytest.fixture
def high_confidence_incident():
    """Create a high-confidence incident."""
    return Incident(
        incident_id="INC-001",
        title="Database connection pool exhausted",
        description="Application cannot connect to database",
        category=IncidentCategory.DATABASE,
        priority=IncidentPriority.HIGH,
        confidence_score=0.95,
        created_by="user123"
    )


@pytest.fixture
def low_confidence_incident():
    """Create a low-confidence incident."""
    return Incident(
        incident_id="INC-002",
        title="Unknown error",
        description="Something went wrong",
        category=IncidentCategory.APPLICATION,
        priority=IncidentPriority.MEDIUM,
        confidence_score=0.65,
        created_by="user456"
    )


@pytest.mark.asyncio
async def test_can_auto_resolve_high_confidence(auto_resolution_service, high_confidence_incident):
    """Test that high-confidence incidents can be auto-resolved."""
    can_resolve, reason = await auto_resolution_service.can_auto_resolve(high_confidence_incident)
    
    assert can_resolve is True
    assert "All checks passed" in reason


@pytest.mark.asyncio
async def test_cannot_auto_resolve_low_confidence(auto_resolution_service, low_confidence_incident):
    """Test that low-confidence incidents cannot be auto-resolved."""
    can_resolve, reason = await auto_resolution_service.can_auto_resolve(low_confidence_incident)
    
    assert can_resolve is False
    assert "below threshold" in reason


@pytest.mark.asyncio
async def test_cannot_auto_resolve_when_kill_switch_active(
    auto_resolution_service,
    high_confidence_incident
):
    """Test that no incidents can be auto-resolved when kill switch is active."""
    # Disable auto-resolution
    auto_resolution_service.config.global_enabled = False
    
    can_resolve, reason = await auto_resolution_service.can_auto_resolve(high_confidence_incident)
    
    assert can_resolve is False
    assert "kill switch" in reason.lower()


@pytest.mark.asyncio
async def test_cannot_auto_resolve_already_resolved(auto_resolution_service, high_confidence_incident):
    """Test that already resolved incidents cannot be auto-resolved again."""
    high_confidence_incident.status = IncidentStatus.AUTO_RESOLVED
    
    can_resolve, reason = await auto_resolution_service.can_auto_resolve(high_confidence_incident)
    
    assert can_resolve is False
    assert "already" in reason.lower()


@pytest.mark.asyncio
async def test_successful_auto_resolution(auto_resolution_service, high_confidence_incident):
    """Test successful auto-resolution of high-confidence incident."""
    result = await auto_resolution_service.resolve_incident(high_confidence_incident)
    
    assert result.success is True
    assert result.incident_id == high_confidence_incident.incident_id
    assert len(result.resolution_steps) > 0
    assert result.resolved_at is not None
    
    # Verify incident was updated
    assert high_confidence_incident.status == IncidentStatus.AUTO_RESOLVED
    assert high_confidence_incident.auto_resolved is True


@pytest.mark.asyncio
async def test_skipped_auto_resolution(auto_resolution_service, low_confidence_incident):
    """Test that low-confidence incidents are skipped with proper response."""
    result = await auto_resolution_service.resolve_incident(low_confidence_incident)
    
    assert result.success is False
    assert "skipped" in result.message.lower()
    assert len(result.resolution_steps) == 0
    
    # Verify incident was not modified
    assert low_confidence_incident.status == IncidentStatus.OPEN
    assert low_confidence_incident.auto_resolved is False


@pytest.mark.asyncio
async def test_category_specific_threshold(
    config,
    audit_service,
    notification_service
):
    """Test that category-specific thresholds are respected."""
    # Set custom threshold for database category
    config.category_configs[IncidentCategory.DATABASE] = CategoryConfig(
        category=IncidentCategory.DATABASE,
        auto_resolution_enabled=True,
        confidence_threshold=0.95  # Higher threshold
    )
    
    service = AutoResolutionService(
        config=config,
        audit_service=audit_service,
        notification_service=notification_service
    )
    
    incident = Incident(
        incident_id="INC-003",
        title="Database issue",
        description="Test",
        category=IncidentCategory.DATABASE,
        priority=IncidentPriority.HIGH,
        confidence_score=0.92,  # Above global threshold but below category threshold
        created_by="user789"
    )
    
    can_resolve, reason = await service.can_auto_resolve(incident)
    
    assert can_resolve is False
    assert "below threshold" in reason


@pytest.mark.asyncio
async def test_audit_trail_created(auto_resolution_service, high_confidence_incident, audit_service):
    """Test that audit trail is created during resolution."""
    initial_audit_count = len(audit_service._audit_log)
    
    await auto_resolution_service.resolve_incident(high_confidence_incident)
    
    # Should have created multiple audit entries
    assert len(audit_service._audit_log) > initial_audit_count
    
    # Verify audit entries exist for this incident
    incident_audits = await audit_service.get_incident_audit_trail(high_confidence_incident.incident_id)
    assert len(incident_audits) > 0
