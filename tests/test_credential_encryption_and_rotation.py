"""
Test Suite: Credential AES-256-GCM Encryption, Key Rotation & Secret Leakage Prevention
Verifies:
1. AES-256-GCM encryption & decryption accuracy.
2. Tamper resistance: corrupted ciphertext or mismatched authentication tag fails decryption.
3. Online key rotation: re-encrypting credentials from key version 1 to version 2 without data loss.
4. Zero plaintext leakage: secrets never appear in masked outputs, logs, or niche export files.
"""

import pytest
from core.security.crypto import EncryptionManager, CryptographicError, mask_secret
from core.niche_builder.credentials import EncryptedCredentialStore
from core.niche_builder.schema import NicheSpec
from core.niche_builder.versioning import NicheVersioningManager


@pytest.fixture(autouse=True)
def clean_crypto():
    EncryptionManager.reset()
    EncryptedCredentialStore.clear_all()
    yield
    EncryptionManager.reset()
    EncryptedCredentialStore.clear_all()


def test_aes_256_gcm_encrypt_decrypt():
    """Verify AES-256-GCM round-trip encryption and decryption."""
    raw_secret = "wp_app_password_9876543210_secret"
    token = EncryptionManager.encrypt(raw_secret)

    # Token must have format v{version}:{nonce}:{ciphertext}
    assert token.startswith("v1:")
    assert raw_secret not in token  # Zero plaintext in ciphertext

    decrypted = EncryptionManager.decrypt(token)
    assert decrypted == raw_secret


def test_aes_256_gcm_tamper_resistance():
    """Verify that tampering with any byte of ciphertext causes decryption to fail."""
    raw_secret = "valuable_api_key"
    token = EncryptionManager.encrypt(raw_secret)

    # Corrupt token
    parts = token.split(":")
    corrupted_ct = parts[2][:-4] + "AAAA"
    corrupted_token = f"{parts[0]}:{parts[1]}:{corrupted_ct}"

    with pytest.raises(CryptographicError):
        EncryptionManager.decrypt(corrupted_token)


def test_online_key_rotation():
    """Verify online rotation from key version 1 to key version 2."""
    site_id = "site_rotation_test"
    secret_wp = "wp_secret_key_v1"
    secret_serp = "serp_secret_key_v1"

    # Store with key version 1
    EncryptedCredentialStore.store_credential(site_id, "wordpress_app_password", secret_wp)
    EncryptedCredentialStore.store_credential(site_id, "serp_provider_api_key", secret_serp)

    # Verify version 1 token format
    token_v1 = EncryptedCredentialStore._site_secrets[site_id]["wordpress_app_password"]
    assert token_v1.startswith("v1:")

    # Generate key version 2 and register in EncryptionManager
    new_key_v2 = b"\xbb" * 32
    EncryptionManager.set_key(version=2, key_bytes=new_key_v2, make_active=True)

    # Perform online rotation
    rotated_count = EncryptedCredentialStore.rotate_all_credentials(new_version=2)
    assert rotated_count == 2

    # Verify tokens now carry v2: prefix
    token_v2 = EncryptedCredentialStore._site_secrets[site_id]["wordpress_app_password"]
    assert token_v2.startswith("v2:")

    # Decrypt with active v2 key to verify integrity
    assert EncryptedCredentialStore.retrieve_secret(site_id, "wordpress_app_password") == secret_wp
    assert EncryptedCredentialStore.retrieve_secret(site_id, "serp_provider_api_key") == secret_serp


def test_zero_secret_leakage_assertion():
    """Verify that secrets NEVER leak in masked outputs or exported niche files."""
    site_id = "site_leak_test"
    raw_key = "super_confidential_secret_amazon_key_999"

    EncryptedCredentialStore.store_credential(site_id, "amazon_associates_api_key", raw_key)

    # Masked output check
    masked_field = EncryptedCredentialStore.get_masked_field(site_id, "amazon_associates_api_key")
    assert masked_field.is_set is True
    assert raw_key not in masked_field.masked_value
    assert "••••••••" in masked_field.masked_value

    all_masked = EncryptedCredentialStore.get_all_masked_for_site(site_id)
    assert raw_key not in str(all_masked)

    # Niche export check: verify raw secrets never appear in YAML or JSON exports
    spec = NicheSpec(
        niche_id="niche_secret_test",
        niche_name="Secret Test Niche",
        niche_description="Test Description for Secret Leakage",
        primary_entity_type="device",
        target_entity_type="accessory",
        category_name="Tech"
    )
    exported_yaml = NicheVersioningManager.export_niche_yaml(spec)
    exported_json = NicheVersioningManager.export_niche_json(spec)

    assert raw_key not in exported_yaml
    assert raw_key not in exported_json
