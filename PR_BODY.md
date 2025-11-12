## Summary

Implemented encryption and decryption mechanisms for Personally Identifiable Information (PII) fields to ensure data security and compliance with privacy regulations.

## Changes

- Added `cryptography` library to project dependencies
- Created `EncryptionService` utility for encrypting and decrypting PII data using Fernet symmetric encryption
- Updated `UserProfile` model to automatically encrypt PII fields (name, email, phone_number, address) on input and decrypt on serialization
- Encryption key managed via environment variable `ENCRYPTION_KEY` with automatic generation fallback

## Technical Details

- Uses Fernet symmetric encryption from the `cryptography` library
- PII fields are encrypted when data enters the system and decrypted when accessed
- Graceful handling of null/empty values
- Environment-based key management for security

## Testing Notes

Ensure `ENCRYPTION_KEY` environment variable is set in production environments for consistent encryption/decryption across deployments.
