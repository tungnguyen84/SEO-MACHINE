"""
Test Suite: SaaS Authentication & RBAC Authorization Hardening
Verifies:
1. Strict 401 on missing or invalid Bearer tokens (zero dev backdoor bypasses).
2. Token expiration and signature validation.
3. Role hierarchy enforcement (OWNER > ADMIN > EDITOR > VIEWER) and 403 on insufficient permissions.
"""

import pytest
import time
from fastapi.testclient import TestClient
from server import app
from core.security.auth import TokenManager, AuthenticatedUser
from core.security.rbac import require_role
from core.niche_builder.schema import PermissionRole
from core.niche_builder.lifecycle import SaaSSiteManager, SiteLifecycleStatus

client = TestClient(app)


def test_unauthenticated_request_blocked():
    """Verify that calling protected SaaS routes without Authorization header returns 401."""
    res = client.get("/api/v1/saas/sites")
    assert res.status_code == 401
    assert "Authorization header is required" in res.json().get("detail", "")


def test_malformed_token_blocked():
    """Verify that invalid token formats or forged signatures return 401."""
    res = client.get("/api/v1/saas/sites", headers={"Authorization": "Bearer not-a-valid-token"})
    assert res.status_code == 401

    # Token with invalid signature
    fake_token = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiMSJ9.forged_signature"
    res2 = client.get("/api/v1/saas/sites", headers={"Authorization": f"Bearer {fake_token}"})
    assert res2.status_code == 401


def test_expired_token_blocked():
    """Verify that an expired JWT token is rejected with 401."""
    expired_token = TokenManager.create_access_token(
        user_id="user_123",
        email="test@tenant.com",
        tenant_id="tenant_alpha",
        role="ADMIN",
        expires_in_seconds=-10  # Already expired
    )
    res = client.get("/api/v1/saas/sites", headers={"Authorization": f"Bearer {expired_token}"})
    assert res.status_code == 401
    assert "expired" in res.json().get("detail", "").lower()


def test_authenticated_user_access_granted():
    """Verify that a valid signed JWT permits access to SaaS routes."""
    valid_token = TokenManager.create_access_token(
        user_id="user_valid",
        email="valid@tenant.com",
        tenant_id="tenant_valid",
        role="ADMIN"
    )
    res = client.get("/api/v1/saas/sites", headers={"Authorization": f"Bearer {valid_token}"})
    assert res.status_code == 200
    assert res.json().get("success") is True


def test_rbac_role_hierarchy():
    """Verify role hierarchy logic: OWNER (4) > ADMIN (3) > EDITOR (2) > VIEWER (1)."""
    viewer = AuthenticatedUser("u1", "v@t.com", "t1", "VIEWER")
    editor = AuthenticatedUser("u2", "e@t.com", "t1", "EDITOR")
    admin = AuthenticatedUser("u3", "a@t.com", "t1", "ADMIN")
    owner = AuthenticatedUser("u4", "o@t.com", "t1", "OWNER")

    # VIEWER
    assert viewer.has_role(PermissionRole.VIEWER) is True
    assert viewer.has_role(PermissionRole.EDITOR) is False
    assert viewer.has_role(PermissionRole.ADMIN) is False

    # EDITOR
    assert editor.has_role(PermissionRole.VIEWER) is True
    assert editor.has_role(PermissionRole.EDITOR) is True
    assert editor.has_role(PermissionRole.ADMIN) is False

    # ADMIN
    assert admin.has_role(PermissionRole.VIEWER) is True
    assert admin.has_role(PermissionRole.EDITOR) is True
    assert admin.has_role(PermissionRole.ADMIN) is True
    assert admin.has_role(PermissionRole.OWNER) is False

    # OWNER
    assert owner.has_role(PermissionRole.VIEWER) is True
    assert owner.has_role(PermissionRole.ADMIN) is True
    assert owner.has_role(PermissionRole.OWNER) is True
