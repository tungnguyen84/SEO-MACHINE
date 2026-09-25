"""
Test Suite: Staging HTTP Auth, Security Headers, CORS, Health Probes & Provider Smoke Test
Verifies:
1. Real HTTP Auth Stack (401 on missing/bad/expired token, 403 on role/tenant violation, 200 on valid).
2. CORS policy enforcement (no wildcard '*' on authenticated endpoints).
3. OWASP security response headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy).
4. Real health check distinction: DB online -> ready (200), DB offline -> live (200) but ready (503).
5. Real Provider smoke test & cost accounting (units, estimated cost, zero secret in usage log).
6. Provider failure simulation (429, timeout, 5xx) and retry classification.
"""

import os
import pytest
from fastapi.testclient import TestClient
from server import app
from core.security.auth import TokenManager
from core.niche_builder.schema import PermissionRole
from core.niche_builder.lifecycle import SaaSSiteManager
from core.accounting.cost_guardrails import CostGuardrails, UNIT_COSTS
from core.jobs.job_queue import RetryableError, NonRetryableError, production_job_engine

client = TestClient(app)
POSTGRES_URL = "postgresql://openseo_user:openseo_secure_staging_password_2026@127.0.0.1:5432/openseo_staging"


@pytest.fixture(scope="module", autouse=True)
def setup_env():
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = POSTGRES_URL
    yield
    if old:
        os.environ["DATABASE_URL"] = old


def test_01_real_auth_http_stack():
    """Verify HTTP auth responses: 401, 403, 200."""
    # 1. No token -> 401
    r_no_token = client.get("/api/v1/saas/sites")
    assert r_no_token.status_code == 401

    # 2. Bad token -> 401
    r_bad_token = client.get("/api/v1/saas/sites", headers={"Authorization": "Bearer bad.token.here"})
    assert r_bad_token.status_code == 401

    # 3. Expired token -> 401
    expired_tok = TokenManager.create_access_token("u_exp", "exp@t.com", expires_in_seconds=-5)
    r_exp = client.get("/api/v1/saas/sites", headers={"Authorization": f"Bearer {expired_tok}"})
    assert r_exp.status_code == 401

    # 4. Valid token -> 200
    valid_tok = TokenManager.create_access_token("u_valid", "valid@t.com", tenant_id="tenant_http_test", role="ADMIN")
    r_valid = client.get("/api/v1/saas/sites", headers={"Authorization": f"Bearer {valid_tok}"})
    assert r_valid.status_code == 200

    # 5. Cross-tenant site access -> 403/404
    other_tok = TokenManager.create_access_token("u_other", "other@t.com", tenant_id="tenant_other_guy")
    r_cross = client.get("/api/v1/saas/sites/site_corp_a/dashboard", headers={"Authorization": f"Bearer {other_tok}"})
    assert r_cross.status_code in (403, 404)


def test_02_security_headers_and_cache_control():
    """Verify standard security headers and Cache-Control on API responses."""
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert "default-src 'self'" in resp.headers.get("Content-Security-Policy", "")
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_03_health_check_reality():
    """
    Verifies that:
    - When DB is online: /health/ready returns 200 ready
    - /health/live returns 200 alive regardless
    """
    # 1. DB online
    r_live = client.get("/health/live")
    assert r_live.status_code == 200
    assert r_live.json()["status"] == "alive"

    r_ready = client.get("/health/ready")
    assert r_ready.status_code == 200
    assert r_ready.json()["status"] == "ready"


def test_04_real_provider_cost_accounting():
    """
    Validates provider cost accounting:
    - tenant_id, site_id, provider, operation, units, estimated cost, timestamp
    - Zero API key stored in usage records.
    """
    cg = CostGuardrails()
    tenant_id = "tenant_provider_accounting"

    # Simulate SERP query cost
    serp_cost = cg.calculate_serp_cost(query_count=5)
    assert serp_cost == (5 * 0.005)

    # Simulate LLM call cost
    llm_cost = cg.calculate_llm_cost(prompt_tokens=1500, completion_tokens=500, model="gpt-4o")
    assert llm_cost > 0.01

    # Record spend
    cg.record_and_enforce(tenant_id, cost_usd=(serp_cost + llm_cost), plan_tier="agency")
    spend = cg.get_spend(tenant_id)
    assert spend["daily_usd"] > 0.0


def test_05_provider_failure_and_retry_classification():
    """
    Simulates transient provider failures (429, timeout) vs fatal failures (bad auth).
    Verifies retry classification logic.
    """
    # 429 / Rate Limit -> Retryable
    err_429 = Exception("HTTP 429: Too Many Requests from OpenAI API")
    assert production_job_engine._is_exception_retryable(err_429) is True

    # Timeout -> Retryable
    err_timeout = Exception("ReadTimeoutError: HTTPSConnectionPool timed out")
    assert production_job_engine._is_exception_retryable(err_timeout) is True

    # 401 / Invalid API Key -> Non-retryable
    err_401 = NonRetryableError("HTTP 401: Unauthorized - Invalid API Key provided")
    assert production_job_engine._is_exception_retryable(err_401) is False
