"""
Tests for Real Source Ingestion, Priority Hierarchy, Staleness, and Page Planner Gates
Priority 3, 4, & 5 Verification
"""
import pytest
from core.database import init_db, get_connection
from core.entities.entity_manager import EntityManager
from core.sources.ingestion import SourceIngestionEngine, SourcePriority
from core.planner.page_planner import PagePlanner

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_real_source_failure_stops_evidence_creation():
    """
    Test that a failed source fetch (e.g. HTTP 403 or network error)
    immediately halts the pipeline and refuses to create fake or partial evidence.
    """
    entity_id = "test_subaru_fail_case"
    EntityManager.create_or_update_entity(
        entity_id=entity_id,
        entity_type="vehicle",
        brand="Subaru",
        model="Outback Failed Fetch"
    )

    failed_fetch_result = {
        "success": False,
        "url": "https://www.subaru.com/403-forbidden-specs",
        "http_status": 403,
        "content": None,
        "error": "HTTP 403 Forbidden"
    }

    ingest_result = SourceIngestionEngine.ingest_structured_source(
        entity_id=entity_id,
        url=failed_fetch_result["url"],
        source_type="oem_manual",
        document_title="Subaru Restricted Spec Sheet",
        raw_attributes={"cargo_length_inches": "75.0 in"},
        fetch_result=failed_fetch_result
    )

    assert ingest_result["success"] is False
    assert ingest_result["status"] == "FETCH_FAILED"

    # Verify that NO evidence claim was inserted into the database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM evidence_claims WHERE entity_id = ?", (entity_id,))
    count = cursor.fetchone()[0]
    conn.close()
    assert count == 0

def test_source_content_hash_marks_stale_evidence():
    """
    Test that when an existing source document changes content hash,
    prior evidence claims are marked as STALE for revalidation.
    """
    entity_id = "test_stale_detection_entity"
    # Clean previous test state
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evidence_claims WHERE entity_id = ?", (entity_id,))
    cursor.execute("DELETE FROM sources WHERE entity_id = ?", (entity_id,))
    conn.commit()
    conn.close()

    EntityManager.create_or_update_entity(
        entity_id=entity_id,
        entity_type="portable_fridge",
        brand="ICECO",
        model="VL45 Spec Check"
    )

    url = "https://icecofreezer.com/products/vl45-specs"

    # First Ingestion
    fetch_1 = {
        "success": True,
        "url": url,
        "http_status": 200,
        "content_hash": "hash_version_1_original"
    }
    res_1 = SourceIngestionEngine.ingest_structured_source(
        entity_id=entity_id,
        url=url,
        source_type="product_manufacturer",
        document_title="VL45 Original Specs",
        raw_attributes={"volume_liters": 45.0},
        fetch_result=fetch_1
    )
    assert res_1["success"] is True

    # Verify claim is VERIFIED
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM evidence_claims WHERE entity_id = ?", (entity_id,))
    status_1 = cursor.fetchone()[0]
    conn.close()
    assert status_1 == "VERIFIED"

    # Second Ingestion with CHANGED content hash
    fetch_2 = {
        "success": True,
        "url": url,
        "http_status": 200,
        "content_hash": "hash_version_2_updated_by_manufacturer"
    }
    res_2 = SourceIngestionEngine.ingest_structured_source(
        entity_id=entity_id,
        url=url,
        source_type="product_manufacturer",
        document_title="VL45 Revised Specs",
        raw_attributes={"volume_liters": 45.0},
        fetch_result=fetch_2
    )
    assert res_2["success"] is True
    assert res_2["is_stale_detected"] is True

    # Verify that the older source claims were updated to STALE
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM evidence_claims WHERE source_id = ?", (res_1["source_id"],))
    older_claim_status = cursor.fetchone()[0]
    conn.close()
    assert older_claim_status == "STALE"

def test_source_priority_community_cannot_override_oem():
    """
    Test that community forum evidence (priority 6) cannot override OEM data (priority 1).
    """
    entity_id = "test_subaru_priority"
    EntityManager.create_or_update_entity(
        entity_id=entity_id,
        entity_type="vehicle",
        brand="Subaru",
        model="Outback 2025"
    )

    # 1. Ingest OEM Source (Priority 1)
    SourceIngestionEngine.ingest_structured_source(
        entity_id=entity_id,
        url="https://subaru.com/oem-specs",
        source_type="oem_manufacturer",
        document_title="Subaru Official OEM Manual",
        raw_attributes={"cargo_length_inches": 75.0}
    )

    from core.database import get_entity_attributes
    attrs_oem = get_entity_attributes(entity_id)
    assert attrs_oem["cargo_length_inches"]["num"] == 75.0

    # 2. Ingest Forum Post with conflicting / informal measurement (Priority 6)
    SourceIngestionEngine.ingest_structured_source(
        entity_id=entity_id,
        url="https://subaruoutback.org/threads/cargo-space.123",
        source_type="community_forum",
        document_title="Subaru Outback Forum User Post",
        raw_attributes={"cargo_length_inches": 71.0}  # User claim
    )

    # OEM spec MUST remain intact at 75.0!
    attrs_after = get_entity_attributes(entity_id)
    assert attrs_after["cargo_length_inches"]["num"] == 75.0

def test_page_planner_research_required_when_evidence_missing():
    """
    Test that PagePlanner returns RESEARCH_REQUIRED if target entities lack
    verified evidence in the database.
    """
    entity_id = "test_empty_unresearched_gear"
    EntityManager.create_or_update_entity(
        entity_id=entity_id,
        entity_type="camping_gear",
        brand="UnknownGear",
        model="Tent123"
    )

    # Target entity has 0 evidence claims
    decision = PagePlanner.evaluate_page_decision(
        keyword="best camping tent unknowngear tent123 review",
        target_entity_ids=[entity_id],
        min_evidence_count=1
    )

    assert decision["action"] == "RESEARCH_REQUIRED"
    assert "Required evidence count not met" in decision["reason"]
    assert entity_id in decision["missing_evidence_entities"]
