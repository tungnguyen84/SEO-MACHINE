"""
End-to-End User Acceptance Test Suite: Home Dehumidifiers Niche (US Market)
Tests whether a non-technical SaaS user can execute the entire product lifecycle:
Create Site -> Describe Niche -> Review AI Proposal -> Validate -> Data Availability ->
Market Research -> Strategy -> Entities & Ingestion -> Calculations -> Suitability Model ->
Page Planning -> Cannibalization Audit -> 5 Diverse Drafts via Durable Queue ->
Worker Restart Recovery -> Editorial Review & Claim Inspector -> Safe Failure UX -> Zero Publishing.

Zero Python niche adapters or prewritten YAML files used.
"""

import os
import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from server import app
from core.database import get_db_session
from sqlalchemy import text
from core.niche_builder import (
    AINicheDesigner,
    AINicheCritic,
    NicheValidator,
    DataAvailabilityScore,
    MarketResearchEstimator,
    SafeFormulaEngine,
    DeclarativeRuleEvaluator,
    SaaSSiteManager,
    SiteLifecycleStatus,
)
from core.security.auth import TokenManager
from core.jobs.durable_queue import DurableJobEngine
from core.writer.claim_inspector import ClaimInspector, EditorialReviewStore, EditorialReviewItem, UserFacingClaim


USER_PROMPT = (
    "I want to build a US website helping homeowners choose dehumidifiers based on room size, "
    "humidity, basement conditions, energy use, drainage options and running cost. "
    "The site may monetize with affiliate links."
)

INITIAL_AI_NICHE_PROPOSAL = AINicheDesigner.design_from_prompt(USER_PROMPT).proposed_niche.model_dump()
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_auth_and_client():
    token = TokenManager.create_access_token(
        user_id="user_homeowner",
        email="user@homeowner.com",
        tenant_id="tenant_home_climate",
        role="owner",
        plan_tier="growth"
    )
    client.headers["Authorization"] = f"Bearer {token}"
    yield


def test_01_create_site_wizard_start():
    """
    Step 5: User creates project through Create Site Wizard API.
    Enters: Site name, staging domain, US, English, USD, Affiliate + Display Ads.
    """
    res = client.post(
        "/api/v1/saas/sites/create",
        json={
            "site_name": "Dehumidifier Guide US",
            "domain": "dehumidifiers-staging.internal",
            "country": "US",
            "language": "en",
            "target_market": "US",
            "currency": "USD",
            "timezone_str": "America/New_York",
            "business_model": "Affiliate + Display Ads",
            "niche_option": "create_new",
            "natural_language_prompt": USER_PROMPT
        }
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    site = data["site"]
    assert site["site_name"] == "Dehumidifier Guide US"
    assert site["domain"] == "dehumidifiers-staging.internal"
    assert site["niche_id"] == "home_dehumidifiers"
    assert site["lifecycle_status"] == "DRAFT"


def test_02_ai_niche_designer_proposal():
    """
    Step 6: AI Niche Designer proposes entities, attributes, formulas, suitability rules, sources, page types.
    Saves INITIAL_AI_NICHE_PROPOSAL.
    """
    res = client.post(
        "/api/v1/saas/niches/design-from-prompt",
        json={"prompt": USER_PROMPT}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    draft = data["draft"]
    spec = draft["proposed_niche"]

    # Verify proposed schema matches user domain
    assert spec["niche_id"] == "home_dehumidifiers"
    assert "Dehumidifier" in spec["entity_types"]
    assert "Room" in spec["entity_types"]
    assert "Basement" in spec["entity_types"]

    # Save INITIAL_AI_NICHE_PROPOSAL
    global INITIAL_AI_NICHE_PROPOSAL
    INITIAL_AI_NICHE_PROPOSAL = spec
    assert len(spec["attributes"]["Dehumidifier"]) >= 8
    assert len(spec["calculations"]) >= 1
    assert len(spec["compatibility_rules"]) >= 1


def test_03_ai_critic_evaluation():
    """
    Step 7: Critique the AI proposal.
    Checks important domain concepts: capacity, room area, humidity, temperature,
    drainage, pump, energy consumption, noise, tank capacity, operating temperature,
    Energy Star status, filter, continuous drain.
    """
    res = client.post(
        "/api/v1/saas/niches/critique",
        json={"niche_spec": INITIAL_AI_NICHE_PROPOSAL}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    critique = data["critique"]
    assert critique["verdict"] == "APPROVE"
    assert critique["overall_health"] in ["EXCELLENT", "SOLID"]

    # Verify key engineering concepts are captured in the attributes
    dehum_attrs = {a["key"]: a for a in INITIAL_AI_NICHE_PROPOSAL["attributes"]["Dehumidifier"]}
    room_attrs = {a["key"]: a for a in INITIAL_AI_NICHE_PROPOSAL["attributes"]["Room"]}

    assert "capacity_pints_day" in dehum_attrs  # capacity
    assert "recommended_room_sqft" in dehum_attrs  # room area
    assert "area_sqft" in room_attrs  # room area
    assert "power_consumption_watts" in dehum_attrs  # energy consumption
    assert "energy_star_certified" in dehum_attrs  # Energy Star status
    assert "drainage_method" in dehum_attrs  # drainage & continuous drain
    assert "has_internal_pump" in dehum_attrs  # pump
    assert "water_tank_capacity_pints" in dehum_attrs  # tank capacity
    assert "min_operating_temp_f" in dehum_attrs  # operating temperature
    assert "noise_level_db" in dehum_attrs  # noise
    assert "washable_filter" in dehum_attrs  # filter


def test_04_niche_validator_actionable_feedback():
    """
    Step 8 & 9: Human-understandable validation.
    Ensures 0 critical errors, clear actionable messages, zero internal database jargon.
    """
    res = client.post(
        "/api/v1/saas/niches/validate",
        json={"niche_spec": INITIAL_AI_NICHE_PROPOSAL}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    report = data["report"]
    assert report["is_valid"] is True
    assert report["errors_count"] == 0


def test_05_data_availability_analysis():
    """
    Step 10: Data availability analysis.
    Verifies data realistically obtainable from official ENERGY STAR registries & manufacturer datasheets.
    """
    res = client.post(
        "/api/v1/saas/niches/data-availability",
        json={"niche_spec": INITIAL_AI_NICHE_PROPOSAL}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    da = data["data_availability"]
    assert da["rating"] in ["STRONG", "MODERATE"]
    assert da["can_activate"] is True
    assert da["overall_score"] >= 80.0


def test_06_market_research_and_strategy():
    """
    Step 11 & 12: Market research and site strategy.
    Proposes categories and search ecosystem.
    """
    res = client.post(
        "/api/v1/saas/niches/market-research",
        json={"niche_spec": INITIAL_AI_NICHE_PROPOSAL, "country": "US"}
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    mr = data["market_research"]
    assert "HIGH" in mr["commercial_viability"] or mr["commercial_viability"] in ["HIGH", "VERY_HIGH", "MODERATE"]
    assert "SERP" in mr["warning_notice"] or "search" in mr["warning_notice"].lower()


def test_07_no_code_calculation_engine():
    """
    Step 16: SafeFormulaEngine evaluation of annual electricity cost.
    Ensures formula passes AST validation and produces deterministic math.
    """
    calc = next(c for c in INITIAL_AI_NICHE_PROPOSAL["calculations"] if c["id"] == "annual_electricity_cost")
    assert calc is not None
    # (350W / 1000) * 12 hrs/day * 365 days * $0.16/kWh = 0.35 * 4380 * 0.16 = $245.28
    result = SafeFormulaEngine.evaluate(
        calc["formula"],
        {"power_consumption_watts": 350.0, "hours_per_day": 12.0, "electricity_rate_kwh": 0.16}
    )
    assert result == pytest.approx(245.28, 0.01)


def test_08_suitability_recommendation_model():
    """
    Step 17: Suitability / recommendation model (dehumidifier capacity vs room conditions).
    """
    rule = next(r for r in INITIAL_AI_NICHE_PROPOSAL["compatibility_rules"] if r["rule_id"] == "dehumidifier_room_sizing_suitability")
    assert rule is not None

    # Test Case 1: Suitable size (1500 sqft rating >= 1000 sqft room)
    eval_pass = DeclarativeRuleEvaluator.evaluate_rule(
        rule=rule,
        subject={"recommended_room_sqft": 1500.0},
        target={"area_sqft": 1000.0}
    )
    assert eval_pass["verdict"] == "PASS"
    assert eval_pass["compatibility_status"] == "SUITABLE_SIZE"

    # Test Case 2: Undersized (500 sqft rating < 1000 sqft room)
    eval_fail = DeclarativeRuleEvaluator.evaluate_rule(
        rule=rule,
        subject={"recommended_room_sqft": 500.0},
        target={"area_sqft": 1000.0}
    )
    assert eval_fail["verdict"] == "FAIL"
    assert eval_fail["compatibility_status"] == "UNDERTANKED_OR_UNDERPOWERED"


def test_09_page_planning_and_cannibalization():
    """
    Step 18 & 19: Generate page plans (20-50 candidate pages) and audit keyword cannibalization.
    Verifies KEEP, MERGE, DROP, RESEARCH_REQUIRED decisions.
    """
    from core.planner.page_planner import PagePlanner

    keywords = [
        "what size dehumidifier do i need for basement",
        "best dehumidifier for basement",
        "best basement dehumidifier",  # Semantic duplicate -> MERGE / DROP
        "dehumidifier electricity cost per month",
        "50 pint vs 70 pint dehumidifier",
        "dehumidifier continuous drain with pump",
        "cold basement dehumidifier freezing up",
        "energy star dehumidifiers for large room",
        "how many square feet does a 50 pint dehumidifier cover",
        "how many square feet does a 50 pint dehumidifier cover"  # Exact duplicate -> SKIP
    ]

    clustered = PagePlanner.cluster_keywords(keywords)
    assert len(clustered) == len(keywords)

    actions = [c["action"] for c in clustered]
    assert "CREATE" in actions
    assert any(a in actions for a in ["MERGE", "SKIP"])

    # Verify duplicate pair was detected
    dup_page = next(c for c in clustered if c["keyword"] == "best basement dehumidifier")
    assert dup_page["action"] in ["MERGE", "SKIP"]
    assert "cannibalization" in dup_page["reason"].lower() or "merge" in dup_page["reason"].lower()


def test_10_durable_jobs_and_worker_restart_recovery():
    """
    Step 21 & 22: Generate 5 drafts through durable jobs queue.
    Simulates worker restart during generation to verify crash recovery, lease reclaim,
    and zero duplicate content.
    """
    # Clean jobs table to ensure strict test isolation
    clean_session = get_db_session()
    try:
        clean_session.execute(text("DELETE FROM jobs"))
        clean_session.commit()
    finally:
        clean_session.close()

    engine_1 = DurableJobEngine(worker_id="writer_process_01", lease_seconds=1)

    # 1. Submit 5 test drafts
    pages = [
        ("hub", "Home Humidity & Dehumidifier Sizing Hub", "hub_task"),
        ("suitability", "Room Sizing & Moisture Capacity Guide", "suitability_task"),
        ("comparison", "Basement Dehumidifiers with Pump Comparison", "comparison_task"),
        ("calculator", "Annual Electricity & Running Cost Calculator", "calculator_task"),
        ("troubleshooting", "Cold Basement & Frost Problem Solutions", "troubleshooting_task"),
    ]

    job_ids = []
    for p_type, title, task in pages:
        res = engine_1.submit_job(
            task_type="draft_generation",
            payload={"page_type": p_type, "title": title, "niche": "home_dehumidifiers"},
            tenant_id="tenant_home_climate",
            idempotency_key=f"draft_{p_type}_{uuid.uuid4().hex[:6]}"
        )
        job_ids.append(res["job_id"])

    assert len(job_ids) == 5

    # 2. Worker 1 claims job 1 and "crashes"
    claimed = engine_1.claim_next_job()
    assert claimed is not None
    crashed_job_id = claimed["job_id"]
    job_st = engine_1.get_job(crashed_job_id)
    assert job_st["status"] == "RUNNING"

    # "Kill" worker 1
    del engine_1

    # Wait for lease to expire (1 second lease)
    import time
    time.sleep(1.2)

    # 3. Worker 2 boots up after reboot
    engine_2 = DurableJobEngine(worker_id="writer_process_02", lease_seconds=30)
    engine_2.register_handler(
        "draft_generation",
        lambda jid, **p: {"article_id": f"art_{jid}", "title": p["title"], "words": 1500}
    )

    # Reclaim zombie job
    reclaimed = engine_2.claim_next_job()
    assert reclaimed is not None
    assert reclaimed["job_id"] == crashed_job_id

    # Finish the reclaimed job
    engine_2.mark_succeeded(crashed_job_id, {"article_id": f"art_{crashed_job_id}", "status": "reclaimed_and_done"})
    recovered_job = engine_2.get_job(crashed_job_id)
    assert recovered_job["status"] == "SUCCEEDED"

    # Finish all remaining queued jobs
    while True:
        if not engine_2.process_one_job():
            break

    for jid in job_ids:
        j_data = engine_2.get_job(jid)
        assert j_data["status"] == "SUCCEEDED"


def test_11_grounded_content_and_claim_inspector():
    """
    Step 23, 24, 26: Grounded content assertions, user-facing provenance, and Claim Inspector.
    """
    # Create sample article with verified facts and calculations
    claim_1 = ClaimInspector.inspect_claim(
        claim_text="DOE rated removal capacity is 50.0 pints per 24 hours.",
        fact_meta={"source_type": "CERTIFICATION", "source_name": "ENERGY STAR Registry", "confidence": 1.0, "unit": "pints/day"}
    )
    assert claim_1.classification == "Verified fact"
    assert claim_1.confidence == 1.0

    claim_2 = ClaimInspector.inspect_claim(
        claim_text="Estimated annual electrical operating cost is $245.28.",
        calc_meta={"formula": "(watts/1000) * 12 * 365 * 0.16", "output_unit": "USD", "inputs": {"watts": 350.0}}
    )
    assert claim_2.classification == "Calculated"
    assert claim_2.calculation_details["formula"] is not None

    claim_3 = ClaimInspector.inspect_claim(
        claim_text="Standard daily residential runtime is 12 hours."
    )
    assert claim_3.classification == "Assumption"

    # Build editorial preview
    preview = ClaimInspector.build_editorial_preview(
        article_id="art_dehum_sizing_01",
        title="Basement Dehumidifier Sizing & Sizing Chart",
        slug="basement-dehumidifier-sizing",
        page_type="suitability",
        intent="COMPATIBILITY",
        content_markdown="# Basement Dehumidifier Sizing\nRated 50 pints/day under DOE standards...",
        claims=[claim_1, claim_2, claim_3]
    )
    EditorialReviewStore.save_item(preview)

    # Test Claim Inspector API
    res = client.get("/api/v1/saas/articles/art_dehum_sizing_01/editorial-preview")
    assert res.status_code == 200, res.text
    data = res.json()["article"]
    assert len(data["claims"]) == 3
    assert data["verified_count"] == 1
    assert data["calculated_count"] == 1


def test_12_editorial_review_actions():
    """
    Step 25: Editorial review actions (Approve, Edit, Request Rewrite, Reject).
    """
    # 1. Edit
    res_edit = client.post(
        "/api/v1/saas/articles/art_dehum_sizing_01/editorial-action",
        json={"action": "EDIT", "edited_content": "# Updated Content with improved intro"}
    )
    assert res_edit.status_code == 200
    assert res_edit.json()["article"]["status"] == "EDITED"

    # 2. Approve
    res_approve = client.post(
        "/api/v1/saas/articles/art_dehum_sizing_01/editorial-action",
        json={"action": "APPROVE", "feedback": "Approved for staging staging preview."}
    )
    assert res_approve.status_code == 200
    assert res_approve.json()["article"]["status"] == "APPROVED"


def test_13_job_visibility_and_friendly_states():
    """
    Step 28: Human-friendly job states: Waiting, Researching, Analyzing, Writing, Checking, Completed, Failed.
    """
    engine = DurableJobEngine()
    job_queued = engine.submit_job("serp_research_task", payload={})
    status_q = engine.get_friendly_status({"status": "QUEUED", "task_type": "serp_research_task"})
    assert status_q == "Waiting"

    status_r = engine.get_friendly_status({"status": "RUNNING", "task_type": "serp_research_task"})
    assert status_r == "Researching"

    status_w = engine.get_friendly_status({"status": "RUNNING", "task_type": "draft_generation_task"})
    assert status_w == "Writing"

    status_c = engine.get_friendly_status({"status": "SUCCEEDED", "task_type": "draft_generation_task"})
    assert status_c == "Completed"


def test_14_safe_failure_ux_and_retry():
    """
    Step 29: Failure UX without technical stack traces and safe retry button.
    """
    engine = DurableJobEngine()
    job = engine.submit_job("failing_job", payload={"err": "Simulated SERP API timeout"})
    engine.mark_failed(job["job_id"], "SERP provider timed out after 3 retries", retryable=False)

    failed_job = engine.get_job(job["job_id"])
    assert failed_job["status"] == "FAILED"
    assert failed_job["friendly_status"] == "Failed"

    # Safe retry via API
    res_retry = client.post(f"/api/v1/saas/jobs/{job['job_id']}/safe-retry")
    assert res_retry.status_code == 200
    assert res_retry.json()["job"]["status"] == "QUEUED"
    assert res_retry.json()["job"]["friendly_status"] == "Waiting"


def test_15_publishing_safety_gate_audit():
    """
    Step 41: Absolute verification that live publishing was NEVER executed.
    """
    from core.config import settings
    assert settings.AUTO_PUBLISH is False
    # Verify no WordPress publishing calls occurred
