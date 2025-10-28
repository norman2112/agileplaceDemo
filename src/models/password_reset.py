from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="User's registered email address")

class PasswordResetToken(BaseModel):
    token: str = Field(..., description="Unique reset token identifier")
    user_id: str = Field(..., description="ID of the user requesting reset")
    expires_at: datetime = Field(..., description="Expiration time of the token")

    def is_valid(self) -> bool:
        """Check if the token is still valid based on current time"""
        return datetime.utcnow() < self.expires_at

    @classmethod
    def create(cls, user_id: str, validity_hours: int = 24):
        """Create a new password reset token with a validity period."""
        return cls(
            token="generate_unique_token()",
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=validity_hours)
        )