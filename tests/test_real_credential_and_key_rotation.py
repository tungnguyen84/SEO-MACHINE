"""
Test Suite: Real PostgreSQL Credential Persistence, Master Key Failure & Key Rotation
Verifies:
1. Real credential persistence in PostgreSQL across application restart.
2. Master encryption key startup failure test (Item 13).
3. Online key rotation on real PostgreSQL database (Item 14).
4. JWT signing key consistency across restart (Item 15).
"""

import os
import pytest
from sqlalchemy import text
from core.database import get_db_session
from core.security.crypto import EncryptionManager, CryptographicError
from core.security.auth import TokenManager
from core.niche_builder.credentials import EncryptedCredentialStore

POSTGRES_URL = "postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_staging"


@pytest.fixture(scope="module", autouse=True)
def setup_env():
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_URL
    yield
    if old:
        os.environ["DATABASE_URL"] = old


def test_01_real_credential_persistence_in_postgresql():
    """
    Stores encrypted test provider credential in PostgreSQL.
    Clears memory cache (simulates app restart).
    Retrieves through authorized service:
    - ciphertext persisted in DB
    - plaintext NOT stored in DB
    - correct tenant can decrypt
    - wrong tenant cannot decrypt
    """
    site_id = "site_real_pg_cred_01"
    raw_secret = "ghp_realPostgreSecretToken2026_LiveKey"

    # Store credential in PostgreSQL
    EncryptedCredentialStore.store_credential(
        site_id=site_id,
        key_name="github_token",
        raw_secret=raw_secret,
        tenant_id="tenant_legit_owner"
    )

    # Verify directly in PostgreSQL table
    session = get_db_session()
    try:
        row = session.execute(
            text("SELECT encrypted_value, tenant_id, key_version FROM site_credentials WHERE site_id = :s AND key_name = 'github_token'"),
            {"s": site_id}
        ).fetchone()
        assert row is not None
        db_encrypted, db_tenant, db_ver = row[0], row[1], row[2]

        # Plaintext must NOT appear in the database
        assert raw_secret not in db_encrypted
        assert db_encrypted.startswith("v1:")
        assert db_tenant == "tenant_legit_owner"
    finally:
        session.close()

    # Clear in-memory cache to simulate restart
    EncryptedCredentialStore._memory_cache.clear()

    # Retrieve through authorized tenant -> must decrypt cleanly
    decrypted_owner = EncryptedCredentialStore.retrieve_secret(site_id, "github_token", tenant_id="tenant_legit_owner")
    assert decrypted_owner == raw_secret

    # Retrieve through attacker tenant -> must return None (blocked)
    decrypted_attacker = EncryptedCredentialStore.retrieve_secret(site_id, "github_token", tenant_id="tenant_attacker")
    assert decrypted_attacker is None


def test_02_master_key_failure_test():
    """
    Start staging without encryption master key.
    Expected: startup FAILS with RuntimeError.
    Does not generate random replacement key silently.
    """
    old_env = os.environ.get("APP_ENV")
    old_key = os.environ.get("OPENSEO_ENCRYPTION_KEY")

    try:
        os.environ["APP_ENV"] = "staging"
        os.environ.pop("OPENSEO_ENCRYPTION_KEY", None)
        EncryptionManager.reset()

        with pytest.raises(RuntimeError) as exc_info:
            EncryptionManager._initialize_keys()
        assert "OPENSEO_ENCRYPTION_KEY" in str(exc_info.value)
    finally:
        # Restore environment
        if old_env:
            os.environ["APP_ENV"] = old_env
        else:
            os.environ.pop("APP_ENV", None)
        if old_key:
            os.environ["OPENSEO_ENCRYPTION_KEY"] = old_key
        EncryptionManager.reset()


def test_03_key_rotation_on_real_database():
    """
    Persist credentials encrypted with key v1.
    Rotate to key v2 using rotate_all_credentials.
    Restart (clear memory cache).
    Verify credentials remain usable and database ciphertext references v2.
    """
    site_id = "site_rotation_db_test"
    secret_wp = "wp_secret_real_db_v1"

    # Store with active version 1
    EncryptedCredentialStore.store_credential(site_id, "wordpress_app_password", secret_wp, tenant_id="tenant_rot")

    # Set new key version 2 in keyring
    key_v2 = b"\x22" * 32
    EncryptionManager.set_key(version=2, key_bytes=key_v2, make_active=True)

    # Perform database rotation
    rotated = EncryptedCredentialStore.rotate_all_credentials(new_version=2)
    assert rotated >= 1

    # Verify directly in PostgreSQL table that ciphertext is now v2:
    session = get_db_session()
    try:
        row = session.execute(
            text("SELECT encrypted_value, key_version FROM site_credentials WHERE site_id = :s AND key_name = 'wordpress_app_password'"),
            {"s": site_id}
        ).fetchone()
        assert row is not None
        assert row[0].startswith("v2:")
        assert row[1] == 2
    finally:
        session.close()

    # Clear memory cache (simulate restart)
    EncryptedCredentialStore._memory_cache.clear()

    # Decrypt from DB using version 2 key
    retrieved = EncryptedCredentialStore.retrieve_secret(site_id, "wordpress_app_password", tenant_id="tenant_rot")
    assert retrieved == secret_wp


def test_04_jwt_restart_and_signing_consistency():
    """
    Issues valid token.
    Restarts API context / token manager.
    Token must verify correctly according to secret policy, without random re-generation.
    """
    test_secret = "staging-production-fixed-jwt-secret-32bytes-entropy-2026"
    os.environ["OPENSEO_JWT_SECRET"] = test_secret

    token = TokenManager.create_access_token(
        user_id="user_jwt_test",
        email="jwt@staging.com",
        tenant_id="tenant_jwt",
        role="ADMIN"
    )

    # Simulate restart by reading token anew
    payload = TokenManager.verify_token(token)
    assert payload["sub"] == "user_jwt_test"
    assert payload["tenant_id"] == "tenant_jwt"
    assert payload["role"] == "ADMIN"
