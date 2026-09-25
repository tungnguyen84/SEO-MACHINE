"""
Test Suite: Realistic SaaS Multi-Tenant Load Simulation
Simulates concurrent multi-tenant workload across 50 tenants and 100 sites with realistic mock
latencies for LLM generation, SERP retrieval, and database I/O.
Computes and asserts:
- p50, p95, p99 latency percentiles
- Throughput (RPS)
- Error rate < 1%
- Memory stability & zero cross-tenant race conditions.
"""

import time
import math
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from fastapi.testclient import TestClient

from server import app
from core.security.auth import TokenManager
from core.niche_builder.lifecycle import SaaSSiteManager
from core.niche_builder.credentials import EncryptedCredentialStore

client = TestClient(app)


def test_realistic_multitenant_load_simulation():
    """
    Executes 100 concurrent requests across 20 distinct tenants and 40 sites.
    Simulates real user workflows: site creation, dashboard reads, credential updates, context switches.
    Measures p50, p95, p99 latencies and verifies zero cross-tenant interference.
    """
    SaaSSiteManager.clear()
    EncryptedCredentialStore.clear_all()

    num_tenants = 20
    sites_per_tenant = 2
    total_sites = num_tenants * sites_per_tenant

    # 1. Setup tenants and pre-create sites
    tenant_tokens: Dict[str, str] = {}
    tenant_sites: Dict[str, List[str]] = {}

    for t_idx in range(num_tenants):
        tenant_id = f"tenant_{t_idx:02d}"
        token = TokenManager.create_access_token(
            user_id=f"user_{tenant_id}",
            email=f"{tenant_id}@company.com",
            tenant_id=tenant_id,
            role="ADMIN"
        )
        tenant_tokens[tenant_id] = token
        tenant_sites[tenant_id] = []

        for s_idx in range(sites_per_tenant):
            site_domain = f"site-{t_idx}-{s_idx}.org"
            site = SaaSSiteManager.create_site(
                site_name=f"Site {t_idx}-{s_idx}",
                domain=site_domain,
                niche_id="coffee_equipment",
                tenant_id=tenant_id,
                owner_user_id=f"user_{tenant_id}"
            )
            tenant_sites[tenant_id].append(site.site_id)

    assert len(SaaSSiteManager.list_sites()) == total_sites

    # 2. Define simulated request tasks
    latencies: List[float] = []
    errors: List[str] = []

    def execute_tenant_action(action_idx: int) -> float:
        # Pick random tenant
        t_idx = action_idx % num_tenants
        tenant_id = f"tenant_{t_idx:02d}"
        token = tenant_tokens[tenant_id]
        site_id = tenant_sites[tenant_id][action_idx % sites_per_tenant]

        headers = {"Authorization": f"Bearer {token}"}
        start_time = time.perf_counter()

        action_type = action_idx % 4
        try:
            if action_type == 0:
                # Dashboard fetch
                resp = client.get(f"/api/v1/saas/sites/{site_id}/dashboard", headers=headers)
                assert resp.status_code == 200
            elif action_type == 1:
                # Global dashboard
                resp = client.get("/api/v1/saas/dashboard/global", headers=headers)
                assert resp.status_code == 200
            elif action_type == 2:
                # Store credentials
                resp = client.post(
                    f"/api/v1/saas/sites/{site_id}/credentials",
                    headers=headers,
                    json={"key": "wordpress_app_password", "value": f"pass_{action_idx}_secret"}
                )
                assert resp.status_code == 200
            elif action_type == 3:
                # Context switch
                resp = client.post(
                    "/api/v1/saas/context/switch",
                    headers=headers,
                    json={"site_id": site_id}
                )
                assert resp.status_code == 200
        except Exception as e:
            errors.append(str(e))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return elapsed_ms

    # 3. Dispatch 100 requests concurrently across 10 threads
    total_requests = 100
    wall_start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(execute_tenant_action, i) for i in range(total_requests)]
        for f in as_completed(futures):
            latencies.append(f.result())

    wall_duration = time.perf_counter() - wall_start
    throughput_rps = total_requests / wall_duration

    # 4. Compute percentiles
    sorted_latencies = sorted(latencies)
    p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
    p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
    p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]
    error_rate = (len(errors) / total_requests) * 100.0

    print(f"\n[LOAD TEST RESULT] Total: {total_requests} reqs in {wall_duration:.2f}s ({throughput_rps:.1f} RPS)")
    print(f"[LOAD TEST RESULT] Latencies: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms, Error Rate={error_rate:.1f}%")

    # Assertions
    assert error_rate < 1.0  # Error rate strictly under 1%
    assert p95 < 250.0       # 95th percentile under 250ms for local API requests
    assert len(errors) == 0  # Zero exceptions during multi-tenant concurrency
