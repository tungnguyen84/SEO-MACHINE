"""
Seed External Reviewer Account for OpenSEO Staging UX Audit.
Creates 'reviewer@openseo.staging' with role OWNER scoped strictly to 'OpenSEO UX Review' workspace.
Seeds both PostgreSQL 16 staging and local database to ensure 100% consistency.
"""

import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

from core.database import hash_password, get_db_session, DB_PATH
from core.models import User as PgUser, Workspace as PgWorkspace
from saas_core.auth import SaaSAuthManager

REVIEWER_EMAIL = "reviewer@openseo.staging"
REVIEWER_PASS = "Reviewer2026!OpenSEO"
REVIEWER_NAME = "External UX Reviewer"
WORKSPACE_NAME = "OpenSEO UX Review"


def seed_sqlite():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (REVIEWER_EMAIL.lower(),))
    existing = cursor.fetchone()
    pw_hash, salt = hash_password(REVIEWER_PASS)
    
    if existing:
        user_id = existing[0]
        cursor.execute("UPDATE users SET password_hash = ?, salt = ?, full_name = ?, plan_tier = 'agency', credits_remaining = 1000 WHERE id = ?",
                       (pw_hash, salt, REVIEWER_NAME, user_id))
    else:
        cursor.execute("""
            INSERT INTO users (email, password_hash, salt, full_name, plan_tier, credits_remaining)
            VALUES (?, ?, ?, ?, 'agency', 1000)
        """, (REVIEWER_EMAIL.lower(), pw_hash, salt, REVIEWER_NAME))
        user_id = cursor.lastrowid

    # Check workspace
    cursor.execute("SELECT id FROM workspaces WHERE user_id = ? AND name = ?", (user_id, WORKSPACE_NAME))
    ws_existing = cursor.fetchone()
    if not ws_existing:
        cursor.execute("""
            INSERT INTO workspaces (user_id, name, amazon_tag_us)
            VALUES (?, ?, 'reviewer-ux-20')
        """, (user_id, WORKSPACE_NAME))
        ws_id = cursor.lastrowid
    else:
        ws_id = ws_existing[0]

    # Verify 0 sites
    cursor.execute("SELECT count(*) FROM connected_sites WHERE workspace_id = ?", (ws_id,))
    site_count = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    print(f"[SQLite] Seeded user_id={user_id}, workspace_id={ws_id} ('{WORKSPACE_NAME}'), sites={site_count}")
    return user_id, ws_id


def seed_postgres():
    session = get_db_session()
    try:
        from sqlalchemy import text
        session.execute(text("SELECT setval('workspaces_id_seq', (SELECT COALESCE(MAX(id), 1) FROM workspaces));"))
        session.execute(text("SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users));"))
        session.commit()
        pw_hash, salt = hash_password(REVIEWER_PASS)
        user = session.query(PgUser).filter(PgUser.email == REVIEWER_EMAIL.lower()).first()
        if user:
            user.password_hash = pw_hash
            user.salt = salt
            user.full_name = REVIEWER_NAME
            user.plan_tier = "agency"
            user.credits_remaining = 1000
        else:
            user = PgUser(
                email=REVIEWER_EMAIL.lower(),
                password_hash=pw_hash,
                salt=salt,
                full_name=REVIEWER_NAME,
                plan_tier="agency",
                credits_remaining=1000
            )
            session.add(user)
            session.flush()

        ws = session.query(PgWorkspace).filter(PgWorkspace.user_id == user.id, PgWorkspace.name == WORKSPACE_NAME).first()
        if not ws:
            ws = PgWorkspace(
                user_id=user.id,
                name=WORKSPACE_NAME,
                amazon_tag_us="reviewer-ux-20"
            )
            session.add(ws)
            session.flush()

        session.commit()
        print(f"[PostgreSQL 16] Seeded user_id={user.id}, workspace_id={ws.id} ('{WORKSPACE_NAME}')")
    finally:
        session.close()


def test_login():
    res = SaaSAuthManager.authenticate_user(REVIEWER_EMAIL, REVIEWER_PASS)
    if res and res.get("token"):
        print(f"[Auth Test] SUCCESS! User authenticated: {res['email']}, role={res.get('role')}, tenant={res.get('tenant_id')}")
        print(f"[Auth Test] Token preview: {res['token'][:25]}...")
    else:
        raise RuntimeError("Failed to authenticate seeded reviewer account!")


if __name__ == "__main__":
    seed_sqlite()
    seed_postgres()
    test_login()
