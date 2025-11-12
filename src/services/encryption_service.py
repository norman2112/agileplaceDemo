import os
from cryptography.fernet import Fernet
from typing import Optional

class EncryptionService:
    def __init__(self):
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = Fernet.generate_key()
            os.environ['ENCRYPTION_KEY'] = key.decode()
        else:
            key = key.encode()
        self._cipher = Fernet(key)
    
    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        if plaintext is None or plaintext == "":
            return plaintext
        encrypted_bytes = self._cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        if ciphertext is None or ciphertext == "":
            return ciphertext
        try:
            decrypted_bytes = self._cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception:
            return ciphertext

_encryption_service = EncryptionService()

def encrypt_pii(value: Optional[str]) -> Optional[str]:
    return _encryption_service.encrypt(value)

def decrypt_pii(value: Optional[str]) -> Optional[str]:
    return _encryption_service.decrypt(value)
