from pydantic import BaseModel, field_validator, field_serializer
from typing import Optional
from ..services.encryption_service import encrypt_pii, decrypt_pii

class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    
    @field_validator('name', 'email', 'phone_number', 'address', mode='before')
    @classmethod
    def encrypt_pii_fields(cls, v):
        return encrypt_pii(v)
    
    @field_serializer('name', 'email', 'phone_number', 'address')
    def decrypt_pii_fields(self, value: Optional[str]) -> Optional[str]:
        return decrypt_pii(value)