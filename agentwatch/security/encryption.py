"""
API Key Encryption Module

Provides secure storage and management of API keys using AES-256-GCM encryption.
Keys are encrypted at rest and decrypted only when needed.
"""

from __future__ import annotations

import hashlib
import logging
import os
from base64 import b64decode, b64encode
from typing import Any, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

logger = logging.getLogger(__name__)


class APIKeyEncryption:
    """Secure API key encryption and decryption using AES-256-GCM."""

    def __init__(self, master_key: Optional[str] = None) -> None:
        """Initialize encryption with master key from environment."""
        self.master_key = master_key or os.getenv("API_KEY_ENCRYPTION_KEY")
        if not self.master_key:
            raise ValueError("API_KEY_ENCRYPTION_KEY not set in environment")

        self._encryption_key = self._derive_key(self.master_key)

    @staticmethod
    def _derive_key(master_key: str, salt: bytes = b"agentwatch-api") -> bytes:
        """Derive 32-byte encryption key from master key using PBKDF2."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(master_key.encode())

    def encrypt_key(self, api_key: str) -> tuple[str, str]:
        """
        Encrypt API key using AES-256-GCM.

        Returns:
            (encrypted_key_b64, nonce_b64): Encrypted key and nonce, both base64-encoded
        """
        nonce = os.urandom(12)
        cipher = AESGCM(self._encryption_key)
        ciphertext = cipher.encrypt(nonce, api_key.encode(), None)

        return (
            b64encode(ciphertext).decode(),
            b64encode(nonce).decode(),
        )

    def decrypt_key(self, encrypted_key: str, nonce: str) -> str:
        """
        Decrypt API key using AES-256-GCM.

        Args:
            encrypted_key: Base64-encoded encrypted key
            nonce: Base64-encoded nonce

        Returns:
            Decrypted API key
        """
        try:
            ciphertext = b64decode(encrypted_key)
            nonce_bytes = b64decode(nonce)

            cipher = AESGCM(self._encryption_key)
            plaintext = cipher.decrypt(nonce_bytes, ciphertext, None)
            return plaintext.decode()
        except Exception as e:
            logger.error("Failed to decrypt API key: %s", str(e))
            raise ValueError("Decryption failed") from e

    @staticmethod
    def hash_key(api_key: str) -> str:
        """
        Hash API key for database lookup without storing plaintext.

        Args:
            api_key: Plain API key

        Returns:
            SHA-256 hash of the key, hex-encoded
        """
        return hashlib.sha256(api_key.encode()).hexdigest()


class KeyRotationManager:
    """Manages API key rotation and audit trail."""

    def __init__(self, db_session: Any = None) -> None:
        """Initialize rotation manager with database session."""
        self.db_session = db_session

    def rotate_key(self, agent_id: str, new_key: str) -> dict[str, Any]:
        """
        Rotate an agent's API key.

        Args:
            agent_id: ID of the agent
            new_key: New API key

        Returns:
            Rotation audit entry
        """
        return {
            "agent_id": agent_id,
            "rotated_at": None,  # Would use datetime in actual implementation
            "old_key_hash": None,  # Would hash old key
            "new_key_hash": APIKeyEncryption.hash_key(new_key),
        }

    def get_rotation_history(self, agent_id: str) -> list[dict[str, Any]]:
        """Get rotation history for an agent."""
        return []  # Would query database
