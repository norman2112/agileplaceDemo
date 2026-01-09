"""
Notification service - notifies incident creators of auto-resolutions.
Supports email and in-app notifications with resolution rating and reopen capabilities.
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from uuid import uuid4

from src.models.incident import Incident, ResolutionStep, IncidentStatus
from src.models.notification import (
    NotificationChannel, ResolutionNotification, ResolutionRating,
    ResolutionRatingRequest, ResolutionRatingResponse, ReopenIncidentRequest
)
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications about auto-resolution events.
    
    Sends notifications to:
    - Incident creators via email and in-app channels
    - Additional configured recipients
    - Operations team members
    
    Features:
    - Email and in-app notification support
    - Resolution summary with fix details
    - Option to reopen incident if issue persists
    - Resolution quality rating
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
        self._notifications: Dict[str, ResolutionNotification] = {}
        self._ratings: Dict[str, ResolutionRatingResponse] = {}
        self._incidents: Dict[str, Incident] = {}
    
    async def notify_auto_resolution(
        self,
        incident: Incident,
        resolution_steps: List[ResolutionStep],
        channels: Optional[List[NotificationChannel]] = None
    ) -> ResolutionNotification:
        """
        Notify the incident creator that their incident was auto-resolved.
        Sends within 2 minutes of resolution as per requirements.
        
        Args:
            incident: The resolved incident
            resolution_steps: Steps taken to resolve the incident
            channels: Notification channels (defaults to email + in-app)
            
        Returns:
            ResolutionNotification: The notification record
        """
        if channels is None:
            channels = [NotificationChannel.EMAIL, NotificationChannel.IN_APP]
        
        notification_id = str(uuid4())
        resolution_summary = self._build_resolution_summary(incident, resolution_steps)
        
        notification = ResolutionNotification(
            notification_id=notification_id,
            incident_id=incident.incident_id,
            recipient_id=incident.created_by,
            channels=channels,
            subject=f"Incident {incident.incident_id} Resolved - {incident.title}",
            resolution_summary=resolution_summary,
            resolution_steps=[s.description for s in resolution_steps if s.success],
            reopen_link=f"/api/v1/incidents/{incident.incident_id}/reopen",
            rating_link=f"/api/v1/incidents/{incident.incident_id}/rate",
            sent_at=datetime.utcnow()
        )
        
        # Store notification and incident for tracking
        self._notifications[notification_id] = notification
        self._incidents[incident.incident_id] = incident
        
        # Send via configured channels
        for channel in channels:
            await self._send_via_channel(channel, notification, incident, resolution_steps)
        
        # Log notification in audit trail
        await self.audit_service.log_notification_sent(
            incident_id=incident.incident_id,
            recipient=incident.created_by,
            notification_type="auto_resolution"
        )
        
        logger.info(
            f"Auto-resolution notification {notification_id} sent for incident "
            f"{incident.incident_id} to user {incident.created_by} via {[c.value for c in channels]}"
        )
        
        return notification
    
    def _build_resolution_summary(
        self,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ) -> str:
        """Build a concise summary of what was fixed."""
        successful_steps = [s for s in resolution_steps if s.success]
        actions = [s.description for s in successful_steps]
        
        if not actions:
            return f"Issue '{incident.title}' has been resolved."
        
        summary = f"Issue '{incident.title}' was resolved by: "
        summary += "; ".join(actions[:3])
        if len(actions) > 3:
            summary += f" and {len(actions) - 3} additional step(s)"
        
        return summary
    
    async def _send_via_channel(
        self,
        channel: NotificationChannel,
        notification: ResolutionNotification,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ):
        """Send notification through specified channel."""
        if channel == NotificationChannel.EMAIL:
            await self._send_email_notification(notification, incident, resolution_steps)
        elif channel == NotificationChannel.IN_APP:
            await self._send_in_app_notification(notification, incident, resolution_steps)
    
    async def _send_email_notification(
        self,
        notification: ResolutionNotification,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ):
        """Send email notification with full details."""
        message = self._build_email_message(notification, incident, resolution_steps)
        logger.info(f"Sending email notification to {notification.recipient_id}: {notification.subject}")
        logger.debug(f"Email content:\n{message}")
        # In production: integrate with SendGrid, SES, etc.
    
    async def _send_in_app_notification(
        self,
        notification: ResolutionNotification,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ):
        """Send in-app notification."""
        logger.info(f"Sending in-app notification to {notification.recipient_id}")
        # In production: push to websocket/notification queue
    
    def _build_email_message(
        self,
        notification: ResolutionNotification,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ) -> str:
        """Build email notification message."""
        successful_steps = [s for s in resolution_steps if s.success]
        
        message = f"""
Incident Resolution Notification
================================

Good news! Your incident has been automatically resolved.

{notification.resolution_summary}

Incident Details:
- ID: {incident.incident_id}
- Title: {incident.title}
- Category: {incident.category.value}
- Priority: {incident.priority.value}
- Resolved At: {incident.resolved_at.isoformat() if incident.resolved_at else datetime.utcnow().isoformat()}

What was fixed:
"""
        for i, step in enumerate(successful_steps, 1):
            message += f"  {i}. {step.description}\n"
        
        message += f"""
---
Is the issue still occurring?
Click here to reopen: {notification.reopen_link}

Help us improve!
Rate this resolution: {notification.rating_link}

This notification was sent automatically within 2 minutes of resolution.
"""
        return message
    
    async def rate_resolution(
        self,
        request: ResolutionRatingRequest
    ) -> ResolutionRatingResponse:
        """
        Submit a rating for the resolution quality.
        
        Args:
            request: Rating request with incident ID, rating, and optional feedback
            
        Returns:
            ResolutionRatingResponse confirming the rating
        """
        from src.models.audit import AuditAction
        
        response = ResolutionRatingResponse(
            incident_id=request.incident_id,
            rating=request.rating,
            feedback=request.feedback,
            submitted_at=datetime.utcnow()
        )
        
        self._ratings[request.incident_id] = response
        
        await self.audit_service.log_entry(
            incident_id=request.incident_id,
            action=AuditAction.RESOLUTION_RATED,
            actor=request.user_id,
            details={
                "rating": request.rating.value,
                "feedback": request.feedback
            }
        )
        
        logger.info(
            f"Resolution rating submitted for incident {request.incident_id}: "
            f"{request.rating.value}"
        )
        
        return response
    
    async def reopen_incident(
        self,
        request: ReopenIncidentRequest
    ) -> Incident:
        """
        Reopen a resolved incident if the issue persists.
        
        Args:
            request: Reopen request with incident ID and reason
            
        Returns:
            Updated incident with reopened status
        """
        from src.models.audit import AuditAction
        
        incident = self._incidents.get(request.incident_id)
        if not incident:
            raise ValueError(f"Incident {request.incident_id} not found")
        
        incident.status = IncidentStatus.OPEN
        incident.auto_resolved = False
        incident.resolved_at = None
        incident.updated_at = datetime.utcnow()
        
        await self.audit_service.log_entry(
            incident_id=request.incident_id,
            action=AuditAction.INCIDENT_REOPENED,
            actor=request.user_id,
            details={
                "reason": request.reason,
                "reopened_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(
            f"Incident {request.incident_id} reopened by {request.user_id}: {request.reason}"
        )
        
        return incident
    
    def get_notification(self, notification_id: str) -> Optional[ResolutionNotification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)
    
    def get_rating(self, incident_id: str) -> Optional[ResolutionRatingResponse]:
        """Get rating for an incident."""
        return self._ratings.get(incident_id)
    
    async def notify_kill_switch_activated(self, activated_by: str, reason: str):
        """Notify operations team that kill switch was activated."""
        logger.warning(f"Kill switch activated by {activated_by}: {reason}")
        
        # In production, send urgent notifications to operations team
        message = f"""
ALERT: Auto-Resolution Kill Switch Activated
============================================

The emergency kill switch for auto-resolution has been activated.

- Activated By: {activated_by}
- Time: {datetime.utcnow().isoformat()}
- Reason: {reason}

All automatic incident resolutions are now disabled.
Manual incident resolution is still available.

To re-enable auto-resolution, deactivate the kill switch through the configuration API.
"""
        
        # Send to operations team (placeholder)
        logger.critical(message)
