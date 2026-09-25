"""
Per-Site Encrypted Credential Store & Secret Masking
Provides secure storage for WordPress, GSC, Amazon, eBay, SERP, and LLM API keys
using production-grade AES-256-GCM authenticated encryption.
Guarantees plain-text secrets are never exposed in UI responses, audit logs, or niche exports.
Supports online key rotation across all stored credentials.
"""

from typing import Dict, Any, Optional
from core.niche_builder.schema import CredentialField
from core.security.crypto import EncryptionManager, mask_secret


class EncryptedCredentialStore:
    """
    Manages tenant/site credentials with AES-256-GCM encryption-at-rest and strict UI masking.
    All stored tokens carry version markers (e.g. 'v1:...', 'v2:...') allowing seamless key rotation.
    """

    # site_id -> {credential_key -> encrypted_token_str}
    _site_secrets: Dict[str, Dict[str, str]] = {}

    @classmethod
    def store_secret(cls, site_id: str, key_name: str, raw_secret: str):
        """Encrypts and stores a site-scoped API credential using AES-256-GCM."""
        if not raw_secret or not raw_secret.strip():
            return
        if site_id not in cls._site_secrets:
            cls._site_secrets[site_id] = {}

        # Encrypt with AES-256-GCM
        encrypted_token = EncryptionManager.encrypt(raw_secret.strip())
        cls._site_secrets[site_id][key_name] = encrypted_token

    @classmethod
    def retrieve_secret(cls, site_id: str, key_name: str) -> Optional[str]:
        """Decrypts and returns the raw credential for backend execution only."""
        site_bucket = cls._site_secrets.get(site_id, {})
        encrypted_token = site_bucket.get(key_name)
        if not encrypted_token:
            return None

        # Decrypt via AES-256-GCM (auto-selects key based on token version)
        return EncryptionManager.decrypt(encrypted_token)

    @classmethod
    def get_masked_field(cls, site_id: str, key_name: str) -> CredentialField:
        """
        Returns a sanitized CredentialField suitable for safe UI rendering.
        Raw secrets are never exposed.
        """
        raw = cls.retrieve_secret(site_id, key_name)
        if not raw:
            return CredentialField(key=key_name, is_set=False, masked_value="")

        masked = mask_secret(raw)
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
    def rotate_all_credentials(cls, new_version: int) -> int:
        """
        Rotates all stored credentials across all sites to the new key version.
        Returns the count of credentials re-encrypted.
        """
        rotated_count = 0
        for site_id, creds in cls._site_secrets.items():
            for key_name, token in list(creds.items()):
                new_token = EncryptionManager.rotate_token(token, target_version=new_version)
                creds[key_name] = new_token
                rotated_count += 1
        return rotated_count

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
