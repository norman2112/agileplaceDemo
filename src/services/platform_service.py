"""
Platform service for handling legacy device platforms (Samsung Bada refactoring).
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from src.models.platform import (
    DevicePlatform, PlatformType, PlatformStatus,
    PlatformIncidentMapping, PlatformMigrationRequest, PlatformMigrationResponse
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class PlatformService:
    """
    Service for managing platform-specific incident handling.
    
    Handles:
    - Legacy platform support (Samsung Bada, deprecated platforms)
    - Platform-specific incident mappings
    - Migration from discontinued platforms
    - Platform lifecycle management
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        # In production, this would use a persistent data store
        self._platforms: Dict[str, DevicePlatform] = {}
        self._mappings: Dict[str, PlatformIncidentMapping] = {}
        
        # Initialize with Bada as legacy platform
        self._initialize_legacy_platforms()
    
    def _initialize_legacy_platforms(self):
        """Initialize known legacy platforms including Samsung Bada."""
        bada_platform = DevicePlatform(
            platform_id="platform_bada_20",
            platform_type=PlatformType.BADA,
            platform_version="2.0",
            status=PlatformStatus.DISCONTINUED,
            support_end_date=datetime(2013, 12, 31),
            metadata={
                "vendor": "Samsung",
                "successor": "Tizen",
                "discontinuation_reason": "Platform discontinued in favor of Tizen"
            }
        )
        self._platforms[bada_platform.platform_id] = bada_platform
        
        logger.info("Initialized legacy platform support: Samsung Bada")
    
    async def register_platform(self, platform: DevicePlatform) -> DevicePlatform:
        """
        Register a new device platform.
        
        Args:
            platform: Platform configuration to register
            
        Returns:
            Registered platform
        """
        self._platforms[platform.platform_id] = platform
        
        logger.info(
            f"Registered platform: {platform.platform_type.value} "
            f"(status: {platform.status.value})"
        )
        
        return platform
    
    async def get_platform(self, platform_id: str) -> Optional[DevicePlatform]:
        """Get platform by ID."""
        return self._platforms.get(platform_id)
    
    async def list_platforms(
        self,
        platform_type: Optional[PlatformType] = None,
        status: Optional[PlatformStatus] = None
    ) -> List[DevicePlatform]:
        """
        List platforms with optional filters.
        
        Args:
            platform_type: Filter by platform type
            status: Filter by platform status
            
        Returns:
            List of matching platforms
        """
        platforms = list(self._platforms.values())
        
        if platform_type:
            platforms = [p for p in platforms if p.platform_type == platform_type]
        
        if status:
            platforms = [p for p in platforms if p.status == status]
        
        return platforms
    
    async def map_incident_to_platform(
        self,
        incident_id: str,
        platform_id: str,
        device_info: Optional[Dict[str, Any]] = None,
        platform_specific_details: Optional[Dict[str, Any]] = None
    ) -> PlatformIncidentMapping:
        """
        Create a mapping between an incident and a platform.
        
        Args:
            incident_id: Incident identifier
            platform_id: Platform identifier
            device_info: Additional device information
            platform_specific_details: Platform-specific context
            
        Returns:
            Created mapping
        """
        mapping = PlatformIncidentMapping(
            mapping_id=str(uuid4()),
            incident_id=incident_id,
            platform_id=platform_id,
            device_info=device_info or {},
            platform_specific_details=platform_specific_details or {}
        )
        
        self._mappings[mapping.mapping_id] = mapping
        
        logger.info(
            f"Mapped incident {incident_id} to platform {platform_id}"
        )
        
        return mapping
    
    async def get_incident_platform(
        self,
        incident_id: str
    ) -> Optional[DevicePlatform]:
        """Get the platform associated with an incident."""
        for mapping in self._mappings.values():
            if mapping.incident_id == incident_id:
                return await self.get_platform(mapping.platform_id)
        
        return None
    
    async def migrate_legacy_platform(
        self,
        request: PlatformMigrationRequest
    ) -> PlatformMigrationResponse:
        """
        Migrate incidents from legacy platform to modern platform.
        
        Used for Bada -> Tizen migrations or other platform transitions.
        
        Args:
            request: Migration request with source/target platforms
            
        Returns:
            Migration response with results
        """
        migration_id = str(uuid4())
        migrated_count = 0
        failed_count = 0
        details = {
            "source": request.source_platform.value,
            "target": request.target_platform.value,
            "dry_run": request.dry_run
        }
        
        logger.info(
            f"Starting platform migration: {request.source_platform.value} -> "
            f"{request.target_platform.value} (dry_run={request.dry_run})"
        )
        
        # Stub implementation - in production, would perform actual migration
        for incident_id in request.incident_ids:
            try:
                # Find existing mapping
                mapping = None
                for m in self._mappings.values():
                    if m.incident_id == incident_id:
                        mapping = m
                        break
                
                if mapping and not request.dry_run:
                    # Update platform in mapping (simplified)
                    # In production, would handle full migration logic
                    migrated_count += 1
                elif mapping:
                    # Dry run - just count
                    migrated_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to migrate incident {incident_id}: {e}")
                failed_count += 1
        
        response = PlatformMigrationResponse(
            migration_id=migration_id,
            success=failed_count == 0,
            migrated_count=migrated_count,
            failed_count=failed_count,
            details=details
        )
        
        logger.info(
            f"Migration complete: {migrated_count} migrated, {failed_count} failed"
        )
        
        return response
    
    async def deprecate_platform(
        self,
        platform_id: str,
        actor: str
    ) -> DevicePlatform:
        """
        Mark a platform as deprecated.
        
        Args:
            platform_id: Platform to deprecate
            actor: User performing the action
            
        Returns:
            Updated platform
        """
        platform = self._platforms.get(platform_id)
        if not platform:
            raise ValueError(f"Platform {platform_id} not found")
        
        platform.status = PlatformStatus.DEPRECATED
        
        logger.info(
            f"Platform {platform_id} deprecated by {actor}"
        )
        
        return platform
    
    async def get_legacy_platforms(self) -> List[DevicePlatform]:
        """Get all legacy/discontinued platforms."""
        return await self.list_platforms(
            status=PlatformStatus.DISCONTINUED
        ) + await self.list_platforms(
            status=PlatformStatus.LEGACY
        )
