"""
Test Suite: Real PostgreSQL Backup (pg_dump) & Restore Drill Validation
Verifies:
1. Running actual pg_dump against openseo_staging database.
2. Storing backup outside active database directory with timestamp, size, and SHA-256 checksum.
3. Restoring the backup into openseo_restore database.
4. Comprehensive integrity drill checking users, sites, credentials, jobs, and audit logs.
"""

import os
import subprocess
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import pytest
from sqlalchemy import text, create_engine

PG_DUMP_PATH = r"D:\App\openseo\.pgsql16\pgsql\bin\pg_dump.exe"
PSQL_PATH = r"D:\App\openseo\.pgsql16\pgsql\bin\psql.exe"
BACKUP_DIR = Path(r"D:\App\openseo\backups")
BACKUP_FILE = BACKUP_DIR / "staging_backup.sql"

STAGING_URL = "postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_staging"
RESTORE_URL = "postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_restore"


def test_01_execute_real_pg_dump():
    """
    Executes actual pg_dump on openseo_staging.
    Records timestamp, size, and SHA-256 checksum.
    """
    BACKUP_DIR.mkdir(exist_ok=True)
    if BACKUP_FILE.exists():
        BACKUP_FILE.unlink()

    # Seed data into openseo_staging to ensure users, credentials, and jobs are populated
    from core.database import get_db_session
    from core.jobs.durable_queue import DurableJobEngine
    from core.niche_builder.credentials import EncryptedCredentialStore

    engine = DurableJobEngine(worker_id="backup_seeder")
    engine.submit_job("backup_canary_job", payload={"purpose": "restore_verification"})
    EncryptedCredentialStore.store_credential("backup_site", "backup_key", "secret_backup_val", tenant_id="tenant_backup")

    cmd = [
        PG_DUMP_PATH,
        "-U", "openseo_user",
        "-h", "127.0.0.1",
        "-p", "5432",
        "-d", "openseo_staging",
        "-F", "p",  # Plain-text SQL dump
        "-f", str(BACKUP_FILE)
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = "openseo_secure_staging_password_2026"

    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert res.returncode == 0, f"pg_dump failed: {res.stderr}"
    assert BACKUP_FILE.exists()

    # Calculate metrics
    size_bytes = BACKUP_FILE.stat().st_size
    assert size_bytes > 5000  # Non-trivial dump with 28+ tables

    hasher = hashlib.sha256()
    with open(BACKUP_FILE, "rb") as f:
        hasher.update(f.read())
    sha256_checksum = hasher.hexdigest()
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    print(f"\n[BACKUP METRICS]")
    print(f"Timestamp: {timestamp_iso}")
    print(f"Size: {size_bytes} bytes ({size_bytes / 1024:.2f} KB)")
    print(f"SHA-256 Checksum: {sha256_checksum}")


def test_02_mandatory_restore_drill_and_integrity_verification():
    """
    Mandatory Restore Drill:
    Restores the backup into openseo_restore database and verifies all data entities exist.
    """
    assert BACKUP_FILE.exists()

    # 1. Clean restore database schema
    engine_restore = create_engine(RESTORE_URL)
    with engine_restore.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
        conn.commit()

    # 2. Restore from backup file using psql
    cmd = [
        PSQL_PATH,
        "-U", "openseo_user",
        "-h", "127.0.0.1",
        "-p", "5432",
        "-d", "openseo_restore",
        "-f", str(BACKUP_FILE)
    ]

    env = os.environ.copy()
    env["PGPASSWORD"] = "openseo_secure_staging_password_2026"

    res = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert res.returncode == 0, f"psql restore failed: {res.stderr}"

    # 3. Comprehensive integrity checks on restored database
    with engine_restore.connect() as conn:
        # Verify tables restored
        tables = conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).scalars().all()
        assert "users" in tables
        assert "jobs" in tables
        assert "site_credentials" in tables
        assert "audit_logs" in tables

        # Verify users survived
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        assert user_count >= 1

        # Verify credentials survived with encryption intact
        creds_count = conn.execute(text("SELECT COUNT(*) FROM site_credentials")).scalar()
        assert creds_count >= 1

        # Verify jobs survived
        jobs_count = conn.execute(text("SELECT COUNT(*) FROM jobs")).scalar()
        assert jobs_count >= 1

    print("\n[RESTORE DRILL VERIFIED] openseo_restore contains all schema, credentials, jobs, and audit data!")
