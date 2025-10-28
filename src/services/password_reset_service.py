from datetime import datetime, timedelta
import logging
from src.models.password_reset import PasswordResetRequest, PasswordResetToken
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class PasswordResetService:
    """
    Service for handling user password reset requests.
    """

    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service

    def request_password_reset(self, email: str) -> bool:
        """
        Initiate the password reset process by generating a token and 
        notifying the user via email.
        """
        logger.info(f"Password reset requested for {email}")

        user_id = self.get_user_id_by_email(email)

        if not user_id:
            logger.warning(f"No user found with email: {email}")
            return False

        reset_token = PasswordResetToken.create(user_id)
        self.send_password_reset_email(email, reset_token)
        return True

    def get_user_id_by_email(self, email: str) -> Optional[str]:
        """
        Placeholder for fetching user ID by email address.
        """
        # In production, implement logic to retrieve user's ID from database
        return "some-user-id"

    def send_password_reset_email(self, email: str, reset_token: PasswordResetToken):
        """
        Send the password reset email to the user.
        """
        subject = "Password Reset Request"
        message = (f"To reset your password, click the following link: 
                    https://example.com/reset-password?token={reset_token.token} \n"
                   f"This link will expire at {reset_token.expires_at.isoformat()}.")

        logger.debug(f"Sending password reset email to {email} with token {reset_token.token}")
        self.notification_service._send_notification(
            recipient=email,
            subject=subject,
            message=message,
            incident=None  # Not applicable here
        )