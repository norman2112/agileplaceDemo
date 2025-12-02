"""
Notification service - notifies incident creators of auto-resolutions.
"""
import logging
from typing import List
from datetime import datetime

from src.models.incident import Incident, ResolutionStep
from src.models.request import WorkRequest
from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for sending notifications about auto-resolution events.
    
    Sends notifications to:
    - Incident creators
    - Additional configured recipients
    - Operations team members
    """
    
    def __init__(self, audit_service: AuditService):
        self.audit_service = audit_service
    
    async def notify_auto_resolution(
        self,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ) -> bool:
        """
        Notify the incident creator that their incident was auto-resolved.
        
        Args:
            incident: The resolved incident
            resolution_steps: Steps taken to resolve the incident
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Build notification message
            message = self._build_notification_message(incident, resolution_steps)
            
            # Send notification (placeholder for actual implementation)
            # In production, this would integrate with:
            # - Email service (SendGrid, SES, etc.)
            # - Slack/Teams
            # - SMS (Twilio)
            # - PagerDuty
            # - Custom notification systems
            
            await self._send_notification(
                recipient=incident.created_by,
                subject=f"Incident {incident.incident_id} Auto-Resolved",
                message=message,
                incident=incident
            )
            
            # Log notification in audit trail
            await self.audit_service.log_notification_sent(
                incident_id=incident.incident_id,
                recipient=incident.created_by,
                notification_type="auto_resolution"
            )
            
            logger.info(
                f"Auto-resolution notification sent for incident {incident.incident_id} "
                f"to user {incident.created_by}"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to send notification for incident {incident.incident_id}: {str(e)}",
                exc_info=True
            )
            return False

    async def notify_request_relevance(
        self,
        recipient: str,
        request: WorkRequest,
        score: float,
        channels: List[str]
    ) -> bool:
        """
        Notify a user that InsightBot identified a relevant work request.
        """
        subject = f"InsightBot alert: {request.summary} ({request.priority.value.upper()})"
        channel_list = ", ".join(channels) if channels else "email"
        tags = ", ".join(request.tags) if request.tags else "none"

        message = f"""
InsightBot detected a request that may need your attention.

Summary: {request.summary}
Priority: {request.priority.value.title()}
Request Type: {request.request_type.value.title()}
Channels: {channel_list}
Relevance Score: {score:.2f}
Tags: {tags}

Details:
{request.description}
""".strip()

        try:
            await self._send_generic_notification(recipient, subject, message)

            if self.audit_service:
                await self.audit_service.log_notification_sent(
                    incident_id=request.request_id,
                    recipient=recipient,
                    notification_type="insightbot_request"
                )

            return True

        except Exception as exc:
            logger.error(
                "Failed to send InsightBot notification for request %s: %s",
                request.request_id,
                str(exc),
                exc_info=True
            )
            return False
    
    def _build_notification_message(
        self,
        incident: Incident,
        resolution_steps: List[ResolutionStep]
    ) -> str:
        """Build a detailed notification message."""
        successful_steps = [s for s in resolution_steps if s.success]
        failed_steps = [s for s in resolution_steps if not s.success]
        
        message = f"""
Incident Auto-Resolution Notification
=====================================

Your incident has been automatically resolved by the system.

Incident Details:
- ID: {incident.incident_id}
- Title: {incident.title}
- Category: {incident.category.value}
- Priority: {incident.priority.value}
- Confidence Score: {incident.confidence_score:.2%}
- Resolved At: {incident.resolved_at.isoformat() if incident.resolved_at else 'N/A'}

Resolution Summary:
- Total Steps: {len(resolution_steps)}
- Successful: {len(successful_steps)}
- Failed: {len(failed_steps)}

Resolution Steps Taken:
"""
        
        for i, step in enumerate(resolution_steps, 1):
            status = "✓ SUCCESS" if step.success else "✗ FAILED"
            message += f"\n{i}. [{status}] {step.description}"
            if step.error_message:
                message += f"\n   Error: {step.error_message}"
        
        message += """

If you believe this resolution is incorrect or incomplete, please:
1. Review the incident in the incident management system
2. Re-open the incident if necessary
3. Contact the operations team for manual intervention

This is an automated message. For questions, please contact your IT Operations team.
"""
        
        return message
    
    async def _send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        incident: Incident
    ):
        """
        Send notification through configured channels.
        
        This is a placeholder for actual notification implementation.
        In production, implement integration with your notification systems.
        """
        await self._send_generic_notification(recipient, subject, message)

    async def _send_generic_notification(
        self,
        recipient: str,
        subject: str,
        message: str
    ):
        logger.info(f"Sending notification to {recipient}: {subject}")

        # Placeholder implementations:
        # Email service, chat integrations, SMS, etc.

        # For now, just log it
        logger.debug(f"Notification content:\n{message}")
    
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
