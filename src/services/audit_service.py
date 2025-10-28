"""
Audit service - comprehensive logging of all auto-resolution actions.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from src.models.audit import AuditLogEntry, AuditAction, AuditQuery

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging all auto-resolution actions in detail.
    
    Provides a complete audit trail for:
    - Auto-resolution attempts
    - Success/failure outcomes
    - Configuration changes
    - Kill switch activations
    - Notifications sent
    """
    
    def __init__(self):
        # In production, this would use a persistent data store
        # (e.g., PostgreSQL, MongoDB, Elasticsearch)
        self._audit_log: List[AuditLogEntry] = []
    
    async def log_entry(
        self,
        incident_id: str,
        action: AuditAction,
        confidence_score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        actor: str = "system"
    ) -> AuditLogEntry:
        """
        Create a detailed audit log entry.
        
        Args:
            incident_id: Related incident identifier
            action: Type of action performed
            confidence_score: Confidence score at time of action
            details: Additional contextual information
            success: Whether the action succeeded
            error_message: Error details if action failed
            actor: System or user performing the action
            
        Returns:
            Created AuditLogEntry
        """
        entry = AuditLogEntry(
            audit_id=str(uuid4()),
            incident_id=incident_id,
            action=action,
            timestamp=datetime.utcnow(),
            actor=actor,
            confidence_score=confidence_score,
            details=details or {},
            success=success,
            error_message=error_message
        )
        
        self._audit_log.append(entry)
        
        logger.info(
            f"Audit log created: {action.value} for incident {incident_id} "
            f"(success={success}, confidence={confidence_score})"
        )
        
        return entry
    
    async def log_auto_resolution_attempt(
        self,
        incident_id: str,
        confidence_score: float
    ) -> AuditLogEntry:
        """Log that an auto-resolution was attempted."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.AUTO_RESOLUTION_ATTEMPTED,
            confidence_score=confidence_score,
            details={"message": "Auto-resolution process initiated"}
        )
    
    async def log_auto_resolution_success(
        self,
        incident_id: str,
        confidence_score: float,
        resolution_steps: List[Dict[str, Any]]
    ) -> AuditLogEntry:
        """Log successful auto-resolution."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.AUTO_RESOLUTION_SUCCESS,
            confidence_score=confidence_score,
            details={
                "message": "Incident auto-resolved successfully",
                "resolution_steps": resolution_steps,
                "step_count": len(resolution_steps)
            },
            success=True
        )
    
    async def log_auto_resolution_failed(
        self,
        incident_id: str,
        confidence_score: float,
        error_message: str
    ) -> AuditLogEntry:
        """Log failed auto-resolution attempt."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.AUTO_RESOLUTION_FAILED,
            confidence_score=confidence_score,
            details={"message": "Auto-resolution failed"},
            success=False,
            error_message=error_message
        )
    
    async def log_auto_resolution_skipped(
        self,
        incident_id: str,
        reason: str,
        confidence_score: float
    ) -> AuditLogEntry:
        """Log that auto-resolution was skipped."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.AUTO_RESOLUTION_SKIPPED,
            confidence_score=confidence_score,
            details={
                "message": "Auto-resolution skipped",
                "reason": reason
            },
            success=True
        )
    
    async def log_notification_sent(
        self,
        incident_id: str,
        recipient: str,
        notification_type: str
    ) -> AuditLogEntry:
        """Log that a notification was sent."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.NOTIFICATION_SENT,
            details={
                "recipient": recipient,
                "notification_type": notification_type
            }
        )
    
    async def log_kill_switch_activation(
        self,
        actor: str,
        reason: Optional[str] = None
    ) -> AuditLogEntry:
        """Log emergency kill switch activation."""
        return await self.log_entry(
            incident_id="SYSTEM",
            action=AuditAction.KILL_SWITCH_ACTIVATED,
            actor=actor,
            details={
                "message": "Emergency kill switch activated - all auto-resolutions disabled",
                "reason": reason or "Not specified"
            }
        )
    
    async def log_kill_switch_deactivation(
        self,
        actor: str
    ) -> AuditLogEntry:
        """Log emergency kill switch deactivation."""
        return await self.log_entry(
            incident_id="SYSTEM",
            action=AuditAction.KILL_SWITCH_DEACTIVATED,
            actor=actor,
            details={
                "message": "Emergency kill switch deactivated - auto-resolutions re-enabled"
            }
        )
    
    async def log_config_update(
        self,
        actor: str,
        config_changes: Dict[str, Any]
    ) -> AuditLogEntry:
        """Log configuration updates."""
        return await self.log_entry(
            incident_id="SYSTEM",
            action=AuditAction.CONFIG_UPDATED,
            actor=actor,
            details={
                "message": "Auto-resolution configuration updated",
                "changes": config_changes
            }
        )
    
    async def query_audit_log(self, query: AuditQuery) -> List[AuditLogEntry]:
        """
        Query audit log entries with filters.
        
        Args:
            query: Query parameters for filtering
            
        Returns:
            List of matching audit log entries
        """
        results = self._audit_log
        
        # Filter by incident_id
        if query.incident_id:
            results = [e for e in results if e.incident_id == query.incident_id]
        
        # Filter by action type
        if query.action:
            results = [e for e in results if e.action == query.action]
        
        # Filter by date range
        if query.start_date:
            results = [e for e in results if e.timestamp >= query.start_date]
        
        if query.end_date:
            results = [e for e in results if e.timestamp <= query.end_date]
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        start_idx = query.offset
        end_idx = start_idx + query.limit
        
        return results[start_idx:end_idx]
    
    async def get_incident_audit_trail(self, incident_id: str) -> List[AuditLogEntry]:
        """Get complete audit trail for a specific incident."""
        query = AuditQuery(incident_id=incident_id, limit=1000)
        return await self.query_audit_log(query)
    
    async def log_recommendation_request(
        self,
        incident_id: str,
        category: str
    ) -> AuditLogEntry:
        """Log that recommendations were requested for an incident."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.RECOMMENDATION_REQUESTED,
            details={
                "message": "Resolution recommendations requested",
                "category": category
            }
        )
    
    async def log_recommendations_generated(
        self,
        incident_id: str,
        count: int,
        processing_time_ms: int
    ) -> AuditLogEntry:
        """Log that recommendations were successfully generated."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.RECOMMENDATIONS_GENERATED,
            details={
                "message": "Resolution recommendations generated",
                "count": count,
                "processing_time_ms": processing_time_ms
            },
            success=True
        )
    
    async def log_recommendation_feedback(
        self,
        feedback_id: str,
        recommendation_id: str,
        incident_id: str,
        rating: str,
        was_successful: bool
    ) -> AuditLogEntry:
        """Log feedback submitted for a recommendation."""
        return await self.log_entry(
            incident_id=incident_id,
            action=AuditAction.RECOMMENDATION_FEEDBACK,
            details={
                "message": "Recommendation feedback submitted",
                "feedback_id": feedback_id,
                "recommendation_id": recommendation_id,
                "rating": rating,
                "was_successful": was_successful
            }
        )
