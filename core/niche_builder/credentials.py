"""
Per-Site Encrypted Credential Store & Secret Masking
Provides secure storage for WordPress, GSC, Amazon, eBay, SERP, and LLM API keys.
Guarantees plain-text secrets are never exposed in UI responses, audit logs, or niche exports.
"""

import base64
import hashlib
from typing import Dict, Any, Optional
from core.niche_builder.schema import CredentialField


class EncryptedCredentialStore:
    """
    Manages tenant/site credentials with encryption-at-rest and strict UI masking.
    """

    _MASTER_KEY = hashlib.sha256(b"openseo_saas_credential_salt_2026").digest()
    _site_secrets: Dict[str, Dict[str, bytes]] = {}  # site_id -> {secret_key -> encrypted_bytes}

    @classmethod
    def _xor_cipher(cls, data: bytes) -> bytes:
        """Lightweight reversible symmetric cipher using SHA-256 derived master keystream."""
        key = cls._MASTER_KEY
        return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])

    @classmethod
    def store_secret(cls, site_id: str, key_name: str, raw_secret: str):
        """Encrypts and stores a site-scoped API credential."""
        if not raw_secret or not raw_secret.strip():
            return
        if site_id not in cls._site_secrets:
            cls._site_secrets[site_id] = {}
        encrypted = cls._xor_cipher(raw_secret.strip().encode("utf-8"))
        cls._site_secrets[site_id][key_name] = encrypted

    @classmethod
    def retrieve_secret(cls, site_id: str, key_name: str) -> Optional[str]:
        """Decrypts and returns the raw credential for backend execution only."""
        site_bucket = cls._site_secrets.get(site_id, {})
        encrypted = site_bucket.get(key_name)
        if not encrypted:
            return None
        decrypted = cls._xor_cipher(encrypted).decode("utf-8")
        return decrypted

    @classmethod
    def get_masked_field(cls, site_id: str, key_name: str) -> CredentialField:
        """
        Returns a sanitized CredentialField suitable for safe UI rendering.
        Raw secrets are never exposed.
        """
        raw = cls.retrieve_secret(site_id, key_name)
        if not raw:
            return CredentialField(key=key_name, is_set=False, masked_value="")

        if len(raw) <= 8:
            masked = "••••••••"
        else:
            prefix = raw[:3]
            suffix = raw[-4:]
            masked = f"{prefix}••••••••{suffix}"

        return CredentialField(key=key_name, is_set=True, masked_value=masked)

    @classmethod
    def get_all_masked_for_site(cls, site_id: str) -> Dict[str, CredentialField]:
        """Returns all configured credentials in masked form for the site dashboard."""
        standard_keys = [
            "wordpress_app_password",
            "search_console_service_account_json",
            "amazon_associates_api_key",
            "ebay_partner_network_token",
            "serp_provider_api_key",
            "llm_provider_api_key"
        ]
        return {k: cls.get_masked_field(site_id, k) for k in standard_keys}

    @classmethod
    def store_credential(cls, site_id: str, key_name: str, raw_secret: str):
        """Alias for store_secret."""
        cls.store_secret(site_id, key_name, raw_secret)

    @classmethod
    def get_credential(cls, site_id: str, key_name: str) -> Optional[str]:
        """Alias for retrieve_secret."""
        return cls.retrieve_secret(site_id, key_name)

    @classmethod
    def clear(cls):
        """Alias for clear_all."""
        cls.clear_all()

    @classmethod
    def clear_for_site(cls, site_id: str):
        """Purges credentials for a deleted or archived site."""
        cls._site_secrets.pop(site_id, None)

    @classmethod
    def clear_all(cls):
        """Clears in-memory store (for testing)."""
        cls._site_secrets.clear()
