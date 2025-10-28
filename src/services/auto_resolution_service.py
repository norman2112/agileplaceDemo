"""
Auto-resolution service - handles automatic incident resolution for high-confidence cases.
"""
import logging
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from src.models.incident import (
    Incident, IncidentStatus, ResolutionStep, IncidentResolutionResponse
)
from src.models.config import AutoResolutionConfig
from src.services.audit_service import AuditService
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class AutoResolutionService:
    """
    Service responsible for automatically resolving incidents with high confidence scores.
    
    Implements the following safety requirements:
    - Only auto-resolves incidents with ≥90% confidence (configurable)
    - Logs all actions in detail
    - Notifies incident creators
    - Respects category-based configuration
    - Honors emergency kill switch
    """
    
    def __init__(
        self,
        config: AutoResolutionConfig,
        audit_service: AuditService,
        notification_service: NotificationService
    ):
        self.config = config
        self.audit_service = audit_service
        self.notification_service = notification_service
        
    async def can_auto_resolve(self, incident: Incident) -> tuple[bool, str]:
        """
        Determine if an incident can be auto-resolved.
        
        Returns:
            tuple: (can_resolve: bool, reason: str)
        """
        # Check emergency kill switch
        if not self.config.global_enabled:
            return False, "Auto-resolution is globally disabled (kill switch active)"
        
        # Check if already resolved
        if incident.status in [IncidentStatus.AUTO_RESOLVED, IncidentStatus.MANUALLY_RESOLVED, IncidentStatus.CLOSED]:
            return False, f"Incident already in status: {incident.status}"
        
        # Check category-specific settings
        if not self.config.is_enabled_for_category(incident.category):
            return False, f"Auto-resolution disabled for category: {incident.category}"
        
        # Check confidence threshold
        threshold = self.config.get_confidence_threshold(incident.category)
        if incident.confidence_score < threshold:
            return False, f"Confidence score {incident.confidence_score:.2%} below threshold {threshold:.2%}"
        
        return True, "All checks passed"
    
    async def resolve_incident(self, incident: Incident) -> IncidentResolutionResponse:
        """
        Attempt to auto-resolve an incident.
        
        Args:
            incident: The incident to resolve
            
        Returns:
            IncidentResolutionResponse with resolution details
        """
        logger.info(f"Starting auto-resolution for incident {incident.incident_id}")
        
        # Audit: Resolution attempted
        await self.audit_service.log_auto_resolution_attempt(
            incident_id=incident.incident_id,
            confidence_score=incident.confidence_score
        )
        
        # Check if resolution is allowed
        can_resolve, reason = await self.can_auto_resolve(incident)
        
        if not can_resolve:
            logger.warning(f"Cannot auto-resolve incident {incident.incident_id}: {reason}")
            await self.audit_service.log_auto_resolution_skipped(
                incident_id=incident.incident_id,
                reason=reason,
                confidence_score=incident.confidence_score
            )
            return IncidentResolutionResponse(
                incident_id=incident.incident_id,
                success=False,
                message=f"Auto-resolution skipped: {reason}",
                resolution_steps=[]
            )
        
        # Execute resolution steps
        try:
            resolution_steps = await self._execute_resolution_steps(incident)
            
            # Update incident status
            incident.status = IncidentStatus.AUTO_RESOLVED
            incident.auto_resolved = True
            incident.resolved_at = datetime.utcnow()
            incident.resolution_steps = resolution_steps
            incident.updated_at = datetime.utcnow()
            
            # Audit: Resolution success
            await self.audit_service.log_auto_resolution_success(
                incident_id=incident.incident_id,
                confidence_score=incident.confidence_score,
                resolution_steps=[step.dict() for step in resolution_steps]
            )
            
            # Send notification to incident creator
            await self.notification_service.notify_auto_resolution(
                incident=incident,
                resolution_steps=resolution_steps
            )
            
            logger.info(f"Successfully auto-resolved incident {incident.incident_id}")
            
            return IncidentResolutionResponse(
                incident_id=incident.incident_id,
                success=True,
                message="Incident successfully auto-resolved",
                resolution_steps=resolution_steps,
                resolved_at=incident.resolved_at
            )
            
        except Exception as e:
            error_message = f"Failed to auto-resolve incident: {str(e)}"
            logger.error(f"Error resolving incident {incident.incident_id}: {error_message}", exc_info=True)
            
            # Audit: Resolution failed
            await self.audit_service.log_auto_resolution_failed(
                incident_id=incident.incident_id,
                confidence_score=incident.confidence_score,
                error_message=error_message
            )
            
            return IncidentResolutionResponse(
                incident_id=incident.incident_id,
                success=False,
                message=error_message,
                resolution_steps=[]
            )
    
    async def _execute_resolution_steps(self, incident: Incident) -> List[ResolutionStep]:
        """
        Execute the actual resolution steps for an incident.
        
        This is a placeholder that would integrate with actual resolution systems.
        In production, this would:
        - Call remediation APIs
        - Execute scripts
        - Update external systems
        - Perform health checks
        """
        resolution_steps = []
        
        # Example resolution steps based on category
        steps_config = self._get_resolution_steps_for_category(incident.category)
        
        for step_config in steps_config:
            step = ResolutionStep(
                step_id=str(uuid4()),
                description=step_config["description"],
                action=step_config["action"]
            )
            
            try:
                # Execute the step (placeholder for actual implementation)
                await self._execute_step(step, incident)
                step.executed_at = datetime.utcnow()
                step.success = True
                logger.info(f"Executed step {step.step_id}: {step.description}")
                
            except Exception as e:
                step.executed_at = datetime.utcnow()
                step.success = False
                step.error_message = str(e)
                logger.error(f"Failed to execute step {step.step_id}: {str(e)}")
                # In production, you might want to rollback previous steps
                
            resolution_steps.append(step)
        
        return resolution_steps
    
    def _get_resolution_steps_for_category(self, category) -> List[dict]:
        """Get resolution steps configuration for a given incident category."""
        # This would typically come from a configuration database or service
        steps_map = {
            "network": [
                {"description": "Check network connectivity", "action": "ping_check"},
                {"description": "Restart network service", "action": "service_restart"},
                {"description": "Verify resolution", "action": "health_check"}
            ],
            "database": [
                {"description": "Check database connections", "action": "connection_check"},
                {"description": "Clear connection pool", "action": "pool_clear"},
                {"description": "Verify database health", "action": "health_check"}
            ],
            "application": [
                {"description": "Check application logs", "action": "log_check"},
                {"description": "Restart application service", "action": "service_restart"},
                {"description": "Verify application health", "action": "health_check"}
            ],
            "ios_upgrade": [
                {"description": "Check iOS version compatibility", "action": "ios_version_check"},
                {"description": "Verify app bundle and provisioning profiles", "action": "bundle_verification"},
                {"description": "Clear derived data and build cache", "action": "cache_clear"},
                {"description": "Validate API compatibility with iOS version", "action": "api_compatibility_check"},
                {"description": "Run automated iOS build test", "action": "build_test"}
            ]
        }
        
        return steps_map.get(category.value, [
            {"description": "Generic health check", "action": "health_check"}
        ])
    
    async def _execute_step(self, step: ResolutionStep, incident: Incident):
        """
        Execute a single resolution step.
        
        This is where the actual remediation logic would be implemented.
        In production, this would integrate with:
        - Ansible/Chef/Puppet for configuration management
        - Kubernetes/Docker APIs for container orchestration
        - Cloud provider APIs (AWS, Azure, GCP)
        - Custom remediation scripts
        """
        # Placeholder implementation
        logger.info(f"Executing action '{step.action}' for incident {incident.incident_id}")
        # In production: call actual remediation APIs/scripts here
        pass
