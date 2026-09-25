"""
Test Suite: SaaS IDOR Defense & Multi-Tenant Isolation
Simulates adversarial cross-tenant attacks (Insecure Direct Object Reference).
Verifies that Tenant B can NEVER view, mutate, or access Tenant A's sites, credentials, or session contexts.
"""

import pytest
from fastapi.testclient import TestClient
from server import app
from core.security.auth import TokenManager
from core.niche_builder.lifecycle import SaaSSiteManager
from core.niche_builder.credentials import EncryptedCredentialStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    SaaSSiteManager.clear()
    EncryptedCredentialStore.clear_all()
    yield
    SaaSSiteManager.clear()
    EncryptedCredentialStore.clear_all()


def test_cross_tenant_idor_dashboard_blocked():
    """Tenant A creates a site; Tenant B attempts to fetch its dashboard."""
    token_a = TokenManager.create_access_token("user_a", "a@corp.com", tenant_id="tenant_a", role="ADMIN")
    token_b = TokenManager.create_access_token("user_b", "b@corp.com", tenant_id="tenant_b", role="ADMIN")

    # Tenant A creates site
    res_create = client.post(
        "/api/v1/saas/sites/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "site_name": "Tenant A Secret Site",
            "domain": "secret-a.com",
            "niche_option": "custom",
            "business_model": "Affiliate"
        }
    )
    assert res_create.status_code == 200
    site_id = res_create.json()["site"]["site_id"]

    # Tenant A can access its own dashboard
    res_a = client.get(f"/api/v1/saas/sites/{site_id}/dashboard", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    assert res_a.json()["dashboard"]["site_id"] == site_id

    # Tenant B tries to access Tenant A's site dashboard (IDOR Attack)
    res_b = client.get(f"/api/v1/saas/sites/{site_id}/dashboard", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code in (403, 404)
    # Ensure no internal site details leaked in error body
    assert "Tenant A Secret Site" not in res_b.text


def test_cross_tenant_idor_credentials_blocked():
    """Tenant A stores a credential; Tenant B attempts to read or mutate it."""
    token_a = TokenManager.create_access_token("user_a", "a@corp.com", tenant_id="tenant_a", role="ADMIN")
    token_b = TokenManager.create_access_token("user_b", "b@corp.com", tenant_id="tenant_b", role="ADMIN")

    res_create = client.post(
        "/api/v1/saas/sites/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"site_name": "Site Creds A", "domain": "creds-a.com", "niche_option": "custom"}
    )
    site_id = res_create.json()["site"]["site_id"]

    # Tenant A stores credential
    res_store = client.post(
        f"/api/v1/saas/sites/{site_id}/credentials",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"key": "wordpress_app_password", "value": "super-secret-wp-pass-1234"}
    )
    assert res_store.status_code == 200

    # Tenant B attempts to read credentials of Site A
    res_read_b = client.get(f"/api/v1/saas/sites/{site_id}/credentials", headers={"Authorization": f"Bearer {token_b}"})
    assert res_read_b.status_code in (403, 404)

    # Tenant B attempts to overwrite Site A's credential
    res_mutate_b = client.post(
        f"/api/v1/saas/sites/{site_id}/credentials",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"key": "wordpress_app_password", "value": "hacked-password"}
    )
    assert res_mutate_b.status_code in (403, 404)

    # Verify original credential was NOT tampered with
    raw_secret = EncryptedCredentialStore.retrieve_secret(site_id, "wordpress_app_password")
    assert raw_secret == "super-secret-wp-pass-1234"


def test_cross_tenant_idor_lifecycle_update_blocked():
    """Tenant B attempts to alter the lifecycle status of Tenant A's site."""
    token_a = TokenManager.create_access_token("user_a", "a@corp.com", tenant_id="tenant_a", role="ADMIN")
    token_b = TokenManager.create_access_token("user_b", "b@corp.com", tenant_id="tenant_b", role="ADMIN")

    res_create = client.post(
        "/api/v1/saas/sites/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"site_name": "Lifecycle Site", "domain": "lifecycle-a.com", "niche_option": "custom"}
    )
    site_id = res_create.json()["site"]["site_id"]

    # Tenant B tries to pause Tenant A's site
    res_lifecycle = client.post(
        f"/api/v1/saas/sites/{site_id}/lifecycle",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"status": "PAUSED"}
    )
    assert res_lifecycle.status_code in (403, 404)

    # Verify site remains in DRAFT
    site = SaaSSiteManager.get_site(site_id, tenant_id="tenant_a")
    assert site.lifecycle_status.value == "DRAFT"


def test_cross_tenant_context_switch_blocked():
    """Tenant B attempts to switch session active context to Tenant A's site."""
    token_a = TokenManager.create_access_token("user_a", "a@corp.com", tenant_id="tenant_a", role="ADMIN")
    token_b = TokenManager.create_access_token("user_b", "b@corp.com", tenant_id="tenant_b", role="ADMIN")

    res_create = client.post(
        "/api/v1/saas/sites/create",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"site_name": "Context Site", "domain": "context-a.com", "niche_option": "custom"}
    )
    site_id = res_create.json()["site"]["site_id"]

    # Tenant B attempts context switch to site_id
    res_switch = client.post(
        "/api/v1/saas/context/switch",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"site_id": site_id}
    )
    assert res_switch.status_code in (403, 404)
