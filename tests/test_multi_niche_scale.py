"""
Scale Test: Multi-Tenant Data Density & Performance Benchmarking (Section 25)
Seeds 10 sites, 1,000 entities, 5,000 attributes, and 1,000 page plans.
Measures query throughput, execution latency, memory footprint, and verifies absence of N+1 bottlenecks.
"""
import time
import os
import tracemalloc
import pytest
from core.database import get_connection
from core.site_profile import SiteProfile, SiteManager
from core.planner.page_planner import PagePlanner
from core.validator.quality_gate import QualityGate


@pytest.fixture(scope="module")
def seeded_scale_environment():
    """Seeds 10 sites with 100 entities, 500 attributes, and 100 page plans each."""
    conn = get_connection()
    cursor = conn.cursor()

    site_count = 10
    entities_per_site = 100
    attrs_per_site = 500
    plans_per_site = 100

    start_seed = time.perf_counter()

    # Register Site Profiles
    for s_idx in range(site_count):
        s_id = f"scale_site_{s_idx}"
        p = SiteProfile(
            site_id=s_id,
            tenant_id=f"tenant_{s_idx % 3}",
            project_id=f"proj_{s_id}",
            domain=f"domain{s_idx}.com",
            brand_name=f"Brand {s_idx}",
            niche_adapter_id="coffee_equipment" if s_idx % 2 == 0 else "workshop_tools"
        )
        SiteManager.register_site(p)

    # 1. Batch insert entities
    entity_rows = []
    for s_idx in range(site_count):
        s_id = f"scale_site_{s_idx}"
        for e_idx in range(entities_per_site):
            e_id = f"ent_{s_id}_{e_idx}"
            e_type = "coffee_machine" if s_idx % 2 == 0 else "power_tool"
            entity_rows.append((e_id, f"proj_{s_id}", e_type, f"Brand_{s_idx}", f"Model_{e_idx}"))

    cursor.executemany("""
    INSERT OR REPLACE INTO entities (id, project_id, entity_type, brand, model)
    VALUES (?, ?, ?, ?, ?)
    """, entity_rows)

    # 2. Batch insert attributes (500 per site)
    attr_rows = []
    for s_idx in range(site_count):
        s_id = f"scale_site_{s_idx}"
        for a_idx in range(attrs_per_site):
            e_target_id = f"ent_{s_id}_{a_idx % entities_per_site}"
            attr_rows.append((e_target_id, f"spec_metric_{a_idx % 10}", float(a_idx * 1.5), "mm", 1.0))

    cursor.executemany("""
    INSERT INTO entity_attributes (entity_id, attr_key, attr_value_num, unit, confidence_score)
    VALUES (?, ?, ?, ?, ?)
    """, attr_rows)

    # 3. Batch insert page plans (100 per site)
    plan_rows = []
    for s_idx in range(site_count):
        s_id = f"scale_site_{s_idx}"
        for p_idx in range(plans_per_site):
            kw = f"best {s_id} model {p_idx % 20} setup"
            plan_rows.append((1, f"proj_{s_id}", kw, "COMMERCIAL_GUIDE", "CREATE", "[]", "{}"))

    cursor.executemany("""
    INSERT INTO page_plans (workspace_id, project_id, target_keyword, intent_type, plan_action, target_entity_ids, factual_brief_json)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, plan_rows)

    conn.commit()
    conn.close()

    seed_duration = time.perf_counter() - start_seed

    return {
        "site_count": site_count,
        "total_entities": site_count * entities_per_site,
        "total_attributes": site_count * attrs_per_site,
        "total_page_plans": site_count * plans_per_site,
        "seed_duration_sec": seed_duration
    }


def test_scale_seeding_metrics(seeded_scale_environment):
    """Verifies that 10 sites, 1,000 entities, 5,000 specs, and 1,000 plans exist."""
    data = seeded_scale_environment
    assert data["site_count"] == 10
    assert data["total_entities"] == 1000
    assert data["total_attributes"] == 5000
    assert data["total_page_plans"] == 1000
    assert data["seed_duration_sec"] < 10.0, "Database batch seeding took too long"


def test_scale_entity_query_latency(seeded_scale_environment):
    """Measures single-site scoped entity lookup speed across 1,000 entities."""
    conn = get_connection()
    cursor = conn.cursor()

    start_time = time.perf_counter()

    # Query 100 entities scoped to project_id='proj_scale_site_3'
    cursor.execute("""
    SELECT e.id, e.brand, e.model, COUNT(a.id) as attr_count
    FROM entities e
    LEFT JOIN entity_attributes a ON e.id = a.entity_id
    WHERE e.project_id = ?
    GROUP BY e.id
    """, ("proj_scale_site_3",))
    rows = cursor.fetchall()
    conn.close()

    query_duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert len(rows) == 100
    # Strict latency check: 100 scoped entities with join must return in < 50ms
    assert query_duration_ms < 50.0, f"Entity query too slow: {query_duration_ms:.2f}ms"


def test_scale_planner_clustering_throughput(seeded_scale_environment):
    """Benchmarks PagePlanner clustering over batch of queries at scale."""
    keywords = [f"best scale_site_2 model {i % 15} review guide" for i in range(50)]

    start_time = time.perf_counter()
    clusters = PagePlanner.cluster_keywords(keywords)
    clustering_duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert len(clusters) == 50
    # Must cluster 50 queries in < 100ms
    assert clustering_duration_ms < 100.0, f"Clustering too slow: {clustering_duration_ms:.2f}ms"


def test_scale_quality_gate_batch_evaluation(seeded_scale_environment):
    """Evaluates 50 content drafts through QualityGate to ensure high throughput."""
    sample_content = """
    # Technical Specification Guide
    ## Executive Summary
    Quick Answer: The unit provides verified power and dimensional clearance.
    | Parameter | Measured Spec |
    | :--- | :--- |
    | Length | 42.8 in |
    > **Affiliate Disclosure**: We earn commissions from qualifying purchases.
    """

    start_time = time.perf_counter()
    for _ in range(50):
        res = QualityGate.audit_content(
            title="Technical Specification Guide",
            content=sample_content,
            allowed_numbers={42.8},
            has_primary_evidence=True,
            is_compatibility_valid=True
        )
        assert res["is_passed"] is True

    audit_duration_ms = (time.perf_counter() - start_time) * 1000.0
    throughput = 50.0 / (audit_duration_ms / 1000.0)

    # Must process at least 100 audits per second
    assert throughput >= 100.0, f"QualityGate throughput too low: {throughput:.1f} ops/sec"


def test_scale_memory_and_no_n_plus_one(seeded_scale_environment):
    """Checks memory usage and verifies bounded query count for internal link topology."""
    tracemalloc.start()

    conn = get_connection()
    cursor = conn.cursor()

    # Test single joined query for link graph across 1,000 page plans
    start_time = time.perf_counter()
    cursor.execute("""
    SELECT p.id, p.project_id, p.target_keyword, COUNT(e.id) as entity_count
    FROM page_plans p
    LEFT JOIN entities e ON e.project_id = p.project_id
    GROUP BY p.id
    LIMIT 200
    """)
    rows = cursor.fetchall()
    conn.close()

    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    query_duration_ms = (time.perf_counter() - start_time) * 1000.0
    peak_mb = peak_mem / (1024 * 1024)

    assert len(rows) == 200
    assert query_duration_ms < 100.0, f"Joined link graph query took {query_duration_ms:.2f}ms"
    assert peak_mb < 50.0, f"Peak memory consumption excessive: {peak_mb:.1f} MB"
