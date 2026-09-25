"""
Production AES-256-GCM Cryptographic Subsystem
Enforces authenticated symmetric encryption for all site credentials and API tokens.
Supports multi-version key rotation, nonce randomization, and zero plaintext exposure in logs/tracebacks.
"""

import os
import base64
import secrets
from typing import Dict, Optional, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CryptographicError(Exception):
    """Base exception for encryption and decryption failures."""
    pass


class KeyRotationError(CryptographicError):
    """Raised when key rotation encounters missing or mismatched keys."""
    pass


class EncryptionManager:
    """
    Industrial-grade AES-256-GCM encryption manager.
    - Uses 256-bit symmetric keys.
    - Uses unique 96-bit (12 bytes) CSPRNG nonce per encryption operation.
    - Incorporates key version prefix (e.g. 'v1:nonce:ciphertext') to enable seamless key rotation.
    - Refuses to start in production without an explicitly supplied strong key.
    """

    _DEFAULT_DEV_KEY = b"\xaa" * 32  # 32 bytes fallback strictly for local dev/testing
    _key_ring: Dict[int, bytes] = {}
    _active_version: int = 1

    @classmethod
    def _initialize_keys(cls):
        """Initializes keys from environment or test fallback."""
        if cls._key_ring:
            return

        env = os.getenv("APP_ENV") or os.getenv("ENV") or "development"
        env_key_b64 = os.getenv("OPENSEO_ENCRYPTION_KEY")

        if env.lower() == "production":
            if not env_key_b64 or len(env_key_b64.strip()) < 32:
                raise RuntimeError(
                    "CRITICAL PRODUCTION ERROR: OPENSEO_ENCRYPTION_KEY is required and must be "
                    "at least 32 bytes (256-bit) base64 or hex encoded in production mode."
                )

        if env_key_b64:
            try:
                # Try base64 decode first
                key_bytes = base64.b64decode(env_key_b64)
                if len(key_bytes) != 32:
                    # Try hex
                    key_bytes = bytes.fromhex(env_key_b64)
            except Exception:
                key_bytes = env_key_b64.encode("utf-8")[:32].ljust(32, b"\0")
            cls._key_ring[1] = key_bytes
        else:
            cls._key_ring[1] = cls._DEFAULT_DEV_KEY

        cls._active_version = 1

    @classmethod
    def set_key(cls, version: int, key_bytes: bytes, make_active: bool = True):
        """Sets a key for a given version in the key ring (for rotation/testing)."""
        if len(key_bytes) != 32:
            raise ValueError("AES-256-GCM key must be exactly 32 bytes (256 bits).")
        cls._key_ring[version] = key_bytes
        if make_active:
            cls._active_version = version

    @classmethod
    def get_active_version(cls) -> int:
        cls._initialize_keys()
        return cls._active_version

    @classmethod
    def encrypt(cls, plaintext: str, associated_data: Optional[bytes] = None) -> str:
        """
        Encrypts plaintext using AES-256-GCM with the active key.
        Output format: v{version}:{b64_nonce}:{b64_ciphertext}
        """
        if plaintext is None:
            raise ValueError("Plaintext cannot be None")
        if not plaintext:
            return ""

        cls._initialize_keys()
        key = cls._key_ring.get(cls._active_version)
        if not key:
            raise CryptographicError(f"Active encryption key version {cls._active_version} not found.")

        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)  # 96-bit standard GCM nonce
        data_bytes = plaintext.encode("utf-8")
        
        try:
            ciphertext = aesgcm.encrypt(nonce, data_bytes, associated_data)
        except Exception as e:
            raise CryptographicError(f"Encryption failed: {str(e)}")

        nonce_b64 = base64.b64encode(nonce).decode("ascii")
        ct_b64 = base64.b64encode(ciphertext).decode("ascii")
        return f"v{cls._active_version}:{nonce_b64}:{ct_b64}"

    @classmethod
    def decrypt(cls, token: str, associated_data: Optional[bytes] = None) -> str:
        """
        Decrypts an AES-256-GCM formatted token.
        Inspects version tag and looks up corresponding key in the keyring.
        """
        if not token:
            return ""

        cls._initialize_keys()
        parts = token.split(":")
        if len(parts) != 3 or not parts[0].startswith("v"):
            raise CryptographicError("Malformed encryption token. Expected 'v{version}:{nonce}:{ciphertext}'")

        try:
            version = int(parts[0][1:])
            nonce = base64.b64decode(parts[1])
            ciphertext = base64.b64decode(parts[2])
        except Exception as e:
            raise CryptographicError(f"Invalid token encoding: {str(e)}")

        key = cls._key_ring.get(version)
        if not key:
            raise KeyRotationError(f"Decryption key version {version} not available in key ring.")

        aesgcm = AESGCM(key)
        try:
            decrypted = aesgcm.decrypt(nonce, ciphertext, associated_data)
            return decrypted.decode("utf-8")
        except Exception as e:
            raise CryptographicError(f"Decryption authentication failed (ciphertext tampered or wrong key): {str(e)}")

    @classmethod
    def rotate_token(cls, token: str, target_version: Optional[int] = None) -> str:
        """
        Decrypts a token using its original key version and re-encrypts it with target/active key version.
        """
        if not token:
            return ""
        target_v = target_version if target_version is not None else cls._active_version
        plaintext = cls.decrypt(token)
        orig_active = cls._active_version
        try:
            cls._active_version = target_v
            new_token = cls.encrypt(plaintext)
            return new_token
        finally:
            cls._active_version = orig_active

    @classmethod
    def reset(cls):
        """Resets the key ring (used in testing)."""
        cls._key_ring.clear()
        cls._active_version = 1


def mask_secret(secret: Optional[str]) -> str:
    """Safely masks a secret string for UI or log presentation."""
    if not secret:
        return ""
    if len(secret) <= 8:
        return "••••••••"
    return f"{secret[:3]}••••••••{secret[-4:]}"
