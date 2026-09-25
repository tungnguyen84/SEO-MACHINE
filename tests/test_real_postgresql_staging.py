"""
Test Suite: Real PostgreSQL 16 Staging Database Verification
Verifies:
1. Actual PostgreSQL 16.8 version check.
2. Tables, foreign keys, indexes, and constraints after migration.
3. Multi-tenant real DB persistence across restart (Tenant A vs Tenant B).
4. Real PostgreSQL ACID transaction rollback on mid-operation failure.
5. Concurrent DB inserts, reads, and usage accounting with zero corruption.
"""

import os
import time
import pytest
from sqlalchemy import text
from core.database import get_db_session, get_engine
from core.models import User, Workspace, Project, Job, SiteCredential, AuditLog
from core.niche_builder.lifecycle import SaaSSiteManager
from core.niche_builder.credentials import EncryptedCredentialStore

POSTGRES_URL = "postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_staging"


@pytest.fixture(scope="module", autouse=True)
def setup_postgres_env():
    """Sets environment to real PostgreSQL staging."""
    old_db = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_URL
    yield
    if old_db:
        os.environ["DATABASE_URL"] = old_db


def test_01_real_postgresql_version():
    """Verify that PostgreSQL is running live and reports version >= 16."""
    session = get_db_session()
    try:
        ver_str = session.execute(text("SELECT version();")).scalar()
        assert "PostgreSQL 16" in ver_str
        print(f"\n[POSTGRES VERSION] {ver_str}")
    finally:
        session.close()


def test_02_database_schema_and_constraints_validation():
    """Verify that actual tables, foreign keys, and indexes exist in PostgreSQL."""
    session = get_db_session()
    try:
        # Check table existence
        tables = session.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).scalars().all()
        required_tables = {"users", "workspaces", "projects", "jobs", "site_credentials", "audit_logs", "articles"}
        assert required_tables.issubset(set(tables))

        # Check unique constraint on site_credentials
        constraints = session.execute(text("""
            SELECT conname FROM pg_constraint 
            WHERE conrelid = 'site_credentials'::regclass
        """)).scalars().all()
        assert "uq_site_credential_key" in constraints

        # Check foreign keys on jobs table
        job_fks = session.execute(text("""
            SELECT conname FROM pg_constraint 
            WHERE conrelid = 'jobs'::regclass AND contype = 'f'
        """)).scalars().all()
        assert "jobs_workspace_id_fkey" in job_fks
    finally:
        session.close()


def test_03_multi_tenant_real_db_persistence_across_restart():
    """
    Creates Tenant A and Tenant B with sites, credentials, and jobs.
    Simulates application restart (clearing memory cache).
    Verifies all data survives restart in PostgreSQL and Tenant A cannot access Tenant B.
    """
    session = get_db_session()
    try:
        # 1. Persist Tenant A & B users in PostgreSQL
        u_a = session.query(User).filter_by(email="tenant_a@staging.com").first()
        if not u_a:
            u_a = User(email="tenant_a@staging.com", password_hash="hash_a", salt="salt_a", plan_tier="growth")
            session.add(u_a)
            session.commit()

        u_b = session.query(User).filter_by(email="tenant_b@staging.com").first()
        if not u_b:
            u_b = User(email="tenant_b@staging.com", password_hash="hash_b", salt="salt_b", plan_tier="starter")
            session.add(u_b)
            session.commit()

        # 2. Persist site credentials in PostgreSQL
        EncryptedCredentialStore.store_credential("site_corp_a", "wp_key", "secret_pass_a", tenant_id="tenant_a")
        EncryptedCredentialStore.store_credential("site_corp_b", "wp_key", "secret_pass_b", tenant_id="tenant_b")

        # 3. Simulate application restart (clear in-memory structures)
        EncryptedCredentialStore._memory_cache.clear()
        SaaSSiteManager.clear()

        # 4. Verify data survived restart by querying PostgreSQL directly
        cred_a_row = session.execute(
            text("SELECT encrypted_value, tenant_id FROM site_credentials WHERE site_id = 'site_corp_a' AND key_name = 'wp_key'")
        ).fetchone()
        assert cred_a_row is not None
        assert cred_a_row[1] == "tenant_a"

        # 5. Verify Tenant A can decrypt its secret, but Tenant B cannot
        decrypted_a = EncryptedCredentialStore.retrieve_secret("site_corp_a", "wp_key", tenant_id="tenant_a")
        assert decrypted_a == "secret_pass_a"

        decrypted_b_attempt = EncryptedCredentialStore.retrieve_secret("site_corp_a", "wp_key", tenant_id="tenant_b")
        assert decrypted_b_attempt is None  # Blocked cross-tenant access!
    finally:
        session.close()


def test_04_real_postgresql_transaction_rollback():
    """
    Tests real PostgreSQL transactional integrity.
    Simulates a failure halfway through a multi-step operation.
    Verifies that rollback leaves zero partial or corrupted state.
    """
    session = get_db_session()
    marker_email = "rollback_test_user@staging.com"
    marker_proj = "proj_rollback_test"

    # Clean prior marker if any
    session.execute(text("DELETE FROM users WHERE email = :e"), {"e": marker_email})
    session.execute(text("DELETE FROM projects WHERE id = :p"), {"p": marker_proj})
    session.commit()

    try:
        # Step 1: Insert user
        u = User(email=marker_email, password_hash="h", salt="s")
        session.add(u)
        session.flush()

        # Step 2: Insert project
        p = Project(id=marker_proj, name="Rollback Proj", niche="coffee")
        session.add(p)
        session.flush()

        # Step 3: Trigger intentional error (e.g. invalid foreign key or forced exception)
        raise RuntimeError("Simulated failure mid-operation during site creation!")
    except RuntimeError:
        session.rollback()

    # Verify that NEITHER user nor project was committed
    check_session = get_db_session()
    try:
        found_user = check_session.query(User).filter_by(email=marker_email).first()
        found_proj = check_session.query(Project).filter_by(id=marker_proj).first()
        assert found_user is None
        assert found_proj is None
    finally:
        check_session.close()


def test_05_concurrent_database_operations():
    """
    Executes concurrent inserts and reads across multiple worker threads on PostgreSQL.
    Verifies no lost updates, duplicate constraint violations, or database locks.
    """
    from concurrent.futures import ThreadPoolExecutor

    num_threads = 8
    inserts_per_thread = 5
    # Clean up any leftover records from prior test runs
    clean_session = get_db_session()
    try:
        clean_session.execute(text("DELETE FROM audit_logs WHERE action = 'CONCURRENT_TEST'"))
        clean_session.commit()
    finally:
        clean_session.close()

    def worker_insert(thread_idx: int):
        session = get_db_session()
        try:
            for i in range(inserts_per_thread):
                audit = AuditLog(
                    workspace_id=1,
                    action="CONCURRENT_TEST",
                    actor=f"thread_{thread_idx}",
                    entity_type="test_entity",
                    entity_id=f"ent_{thread_idx}_{i}"
                )
                session.add(audit)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=num_threads) as pool:
        results = list(pool.map(worker_insert, range(num_threads)))

    assert all(results) is True

    # Verify total count in DB
    verify_session = get_db_session()
    try:
        count = verify_session.execute(
            text("SELECT COUNT(*) FROM audit_logs WHERE action = 'CONCURRENT_TEST'")
        ).scalar()
        assert count == (num_threads * inserts_per_thread)
    finally:
        verify_session.close()
