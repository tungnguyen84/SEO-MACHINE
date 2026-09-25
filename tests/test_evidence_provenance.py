"""
Test Evidence Provenance Chain (Section 5)
Validates that every factual attribute can be traced back:
VALUE -> ENTITY ATTRIBUTE -> EVIDENCE CLAIM -> SOURCE -> URL -> RETRIEVED_AT -> CONFIDENCE
"""
import pytest
from core.entities.entity_manager import EntityManager
from core.database import get_connection

def test_evidence_provenance_subaru_outback_2025():
    """Verify complete evidence provenance chain for 2025 Subaru Outback cargo height."""
    entity = EntityManager.get_entity_full("car_subaru_outback_2025")
    assert entity is not None, "Entity car_subaru_outback_2025 must exist in database"
    
    # 1. VALUE & ENTITY ATTRIBUTE
    attrs = {a["attr_key"]: a for a in entity.get("attributes", [])}
    assert "cargo_height_inches" in attrs, "cargo_height_inches attribute must exist"
    attr = attrs["cargo_height_inches"]
    
    assert attr["attr_value_num"] == 31.8, "Attribute value must match ground truth 31.8 in"
    assert attr["confidence_score"] == 1.0, "Confidence score must be 1.0"
    source_id = attr["verified_by_source_id"]
    assert source_id is not None, "Provenance broken: verified_by_source_id is None"

    # 2. EVIDENCE CLAIM
    claims = entity.get("evidence_claims", [])
    matching_claims = [c for c in claims if c["attribute_key"] == "cargo_height_inches"]
    assert len(matching_claims) > 0, "Provenance broken: No evidence claim found for cargo_height_inches"
    claim = matching_claims[0]
    assert "31.8 in" in claim["raw_quote"], "Evidence quote must contain verified dimension"
    assert claim["status"] == "VERIFIED", "Evidence status must be VERIFIED"

    # 3. SOURCE, URL & RETRIEVED_AT
    sources = {s["id"]: s for s in entity.get("sources", [])}
    assert source_id in sources, f"Provenance broken: Source ID {source_id} not found in sources"
    src = sources[source_id]
    assert src["url"] is not None and "subaru.com" in src["url"], "Source URL must exist and point to authoritative domain"
    assert src["fetched_at"] is not None, "Source fetched_at timestamp must exist"
    assert "Subaru Outback" in src["document_title"], "Source document_title must specify vehicle manual"

def test_evidence_provenance_iceco_vl45():
    """Verify complete evidence provenance chain for ICECO VL45 portable fridge."""
    entity = EntityManager.get_entity_full("prod_iceco_vl45")
    assert entity is not None, "Entity prod_iceco_vl45 must exist in database"

    # 1. VALUE & ENTITY ATTRIBUTE
    attrs = {a["attr_key"]: a for a in entity.get("attributes", [])}
    assert "average_power_draw_watts" in attrs, "average_power_draw_watts attribute must exist"
    attr = attrs["average_power_draw_watts"]
    assert attr["attr_value_num"] == 45.0, "Power draw must be 45.0W"
    source_id = attr["verified_by_source_id"]
    assert source_id is not None, "Provenance broken: verified_by_source_id is None"

    # 2. EVIDENCE CLAIM
    claims = entity.get("evidence_claims", [])
    matching_claims = [c for c in claims if c["attribute_key"] == "average_power_draw_watts"]
    assert len(matching_claims) > 0, "Provenance broken: No evidence claim found for average_power_draw_watts"
    claim = matching_claims[0]
    assert "SECOP" in claim["raw_quote"] or "45W" in claim["raw_quote"], "Evidence quote must contain manufacturer spec"

    # 3. SOURCE & URL
    sources = {s["id"]: s for s in entity.get("sources", [])}
    assert source_id in sources, "Source ID must exist in sources table"
    src = sources[source_id]
    assert src["url"] is not None and "icecofreezer.com" in src["url"], "Source URL must link to official manufacturer"
    assert src["fetched_at"] is not None, "Provenance broken: missing retrieved_at timestamp"
