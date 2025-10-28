"""
Unit tests for platform service (Samsung Bada refactoring).
"""
import pytest
from datetime import datetime
from src.models.platform import (
    DevicePlatform, PlatformType, PlatformStatus,
    PlatformMigrationRequest, PlatformMigrationResponse
)
from src.services.platform_service import PlatformService
from src.services.audit_service import AuditService


@pytest.fixture
def audit_service():
    """Create audit service fixture."""
    return AuditService()


@pytest.fixture
def platform_service(audit_service):
    """Create platform service fixture."""
    return PlatformService(audit_service=audit_service)


@pytest.mark.asyncio
async def test_bada_platform_initialized(platform_service):
    """Test that Samsung Bada platform is initialized on service creation."""
    platforms = await platform_service.list_platforms()
    
    bada_platforms = [p for p in platforms if p.platform_type == PlatformType.BADA]
    assert len(bada_platforms) > 0
    
    bada = bada_platforms[0]
    assert bada.status == PlatformStatus.DISCONTINUED
    assert bada.platform_version == "2.0"


@pytest.mark.asyncio
async def test_register_new_platform(platform_service):
    """Test registering a new platform."""
    new_platform = DevicePlatform(
        platform_id="platform_tizen_30",
        platform_type=PlatformType.TIZEN,
        platform_version="3.0",
        status=PlatformStatus.ACTIVE,
        metadata={"vendor": "Samsung"}
    )
    
    registered = await platform_service.register_platform(new_platform)
    
    assert registered.platform_id == "platform_tizen_30"
    assert registered.platform_type == PlatformType.TIZEN
    assert registered.status == PlatformStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_platform_by_id(platform_service):
    """Test retrieving a platform by ID."""
    platform = await platform_service.get_platform("platform_bada_20")
    
    assert platform is not None
    assert platform.platform_type == PlatformType.BADA


@pytest.mark.asyncio
async def test_list_platforms_by_type(platform_service):
    """Test filtering platforms by type."""
    # Register additional platform for testing
    tizen_platform = DevicePlatform(
        platform_id="platform_tizen_40",
        platform_type=PlatformType.TIZEN,
        platform_version="4.0",
        status=PlatformStatus.ACTIVE
    )
    await platform_service.register_platform(tizen_platform)
    
    tizen_platforms = await platform_service.list_platforms(
        platform_type=PlatformType.TIZEN
    )
    
    assert len(tizen_platforms) > 0
    assert all(p.platform_type == PlatformType.TIZEN for p in tizen_platforms)


@pytest.mark.asyncio
async def test_list_platforms_by_status(platform_service):
    """Test filtering platforms by status."""
    discontinued = await platform_service.list_platforms(
        status=PlatformStatus.DISCONTINUED
    )
    
    assert len(discontinued) > 0
    assert all(p.status == PlatformStatus.DISCONTINUED for p in discontinued)


@pytest.mark.asyncio
async def test_get_legacy_platforms(platform_service):
    """Test retrieving all legacy platforms."""
    legacy_platforms = await platform_service.get_legacy_platforms()
    
    # Should include at least Bada
    assert len(legacy_platforms) > 0
    assert any(p.platform_type == PlatformType.BADA for p in legacy_platforms)


@pytest.mark.asyncio
async def test_map_incident_to_platform(platform_service):
    """Test mapping an incident to a platform."""
    mapping = await platform_service.map_incident_to_platform(
        incident_id="INC-12345",
        platform_id="platform_bada_20",
        device_info={"model": "Samsung Wave S8500"},
        platform_specific_details={"os_build": "BADA-2.0.1"}
    )
    
    assert mapping.incident_id == "INC-12345"
    assert mapping.platform_id == "platform_bada_20"
    assert "model" in mapping.device_info


@pytest.mark.asyncio
async def test_get_incident_platform(platform_service):
    """Test retrieving platform for an incident."""
    # First create a mapping
    await platform_service.map_incident_to_platform(
        incident_id="INC-99999",
        platform_id="platform_bada_20"
    )
    
    platform = await platform_service.get_incident_platform("INC-99999")
    
    assert platform is not None
    assert platform.platform_type == PlatformType.BADA


@pytest.mark.asyncio
async def test_migrate_legacy_platform_dry_run(platform_service):
    """Test platform migration in dry-run mode."""
    migration_request = PlatformMigrationRequest(
        source_platform=PlatformType.BADA,
        target_platform=PlatformType.TIZEN,
        incident_ids=["INC-1", "INC-2", "INC-3"],
        dry_run=True
    )
    
    response = await platform_service.migrate_legacy_platform(migration_request)
    
    assert response.migration_id is not None
    assert response.details["dry_run"] is True


@pytest.mark.asyncio
async def test_migrate_legacy_platform(platform_service):
    """Test actual platform migration."""
    # Setup: Create mappings for Bada incidents
    for i in range(1, 4):
        await platform_service.map_incident_to_platform(
            incident_id=f"INC-MIGRATE-{i}",
            platform_id="platform_bada_20"
        )
    
    migration_request = PlatformMigrationRequest(
        source_platform=PlatformType.BADA,
        target_platform=PlatformType.TIZEN,
        incident_ids=[f"INC-MIGRATE-{i}" for i in range(1, 4)],
        dry_run=False
    )
    
    response = await platform_service.migrate_legacy_platform(migration_request)
    
    assert response.migrated_count >= 0
    assert response.details["source"] == "bada"
    assert response.details["target"] == "tizen"


@pytest.mark.asyncio
async def test_deprecate_platform(platform_service):
    """Test marking a platform as deprecated."""
    # First register an active platform
    new_platform = DevicePlatform(
        platform_id="platform_test_deprecated",
        platform_type=PlatformType.ANDROID,
        platform_version="4.0",
        status=PlatformStatus.ACTIVE
    )
    await platform_service.register_platform(new_platform)
    
    # Now deprecate it
    deprecated = await platform_service.deprecate_platform(
        platform_id="platform_test_deprecated",
        actor="admin"
    )
    
    assert deprecated.status == PlatformStatus.DEPRECATED


@pytest.mark.asyncio
async def test_deprecate_nonexistent_platform(platform_service):
    """Test that deprecating a non-existent platform raises error."""
    with pytest.raises(ValueError, match="not found"):
        await platform_service.deprecate_platform(
            platform_id="platform_does_not_exist",
            actor="admin"
        )


@pytest.mark.asyncio
async def test_platform_metadata(platform_service):
    """Test that platform metadata is properly stored."""
    platform = await platform_service.get_platform("platform_bada_20")
    
    assert platform is not None
    assert "vendor" in platform.metadata
    assert platform.metadata["vendor"] == "Samsung"
    assert "successor" in platform.metadata
    assert platform.metadata["successor"] == "Tizen"
