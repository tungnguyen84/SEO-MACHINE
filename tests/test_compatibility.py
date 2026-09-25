"""
Deterministic Compatibility Engine Tests (Section 7)
Proves that compatibility results come from deterministic dimensional & electrical calculations,
NOT from LLM hallucination.
"""
import pytest
from core.engine.compatibility import CompatibilityEngine
from core.database import get_entity, get_entity_attributes, upsert_entity_attribute

def test_compatibility_deterministic_pass():
    """Test 2025 Subaru Outback + ICECO VL45: Dimensions fit within cargo space."""
    res = CompatibilityEngine.evaluate("car_subaru_outback_2025", "prod_iceco_vl45")
    
    assert res["verdict"] == "PASS", f"Expected PASS, got {res.get('verdict')}"
    assert res["compatibility_status"] == "EXACT_FIT"
    assert res["confidence"] == 1.0
    assert res["max_clearance_inches"] == 13.3, f"Expected 13.3 in clearance, got {res.get('max_clearance_inches')}"
    assert "cargo opening" in res["reason"]
    assert len(res["evidence_references"]) >= 2

def test_compatibility_dimension_expansion_fails():
    """
    Test changing product dimension to be larger than vehicle cargo height.
    Vehicle height = 31.8 in.
    Setting fridge height = 36.0 in (> 31.8 in).
    Result must deterministically flip from PASS -> FAIL.
    """
    # 1. Update fridge height in DB to 36.0 in (too tall for Outback cargo hatch)
    upsert_entity_attribute(
        entity_id="prod_iceco_vl45",
        attr_key="height_inches",
        attr_value_num=36.0,
        attr_value_text="36.0 in",
        unit="in"
    )
    
    try:
        res = CompatibilityEngine.evaluate("car_subaru_outback_2025", "prod_iceco_vl45")
        assert res["verdict"] == "FAIL", f"Expected FAIL when height exceeds cargo opening, got {res.get('verdict')}"
        assert res["compatibility_status"] == "DOES_NOT_FIT"
        assert res["max_clearance_inches"] < 0, "Clearance must be negative"
    finally:
        # Restore ground-truth height = 18.5 in
        upsert_entity_attribute(
            entity_id="prod_iceco_vl45",
            attr_key="height_inches",
            attr_value_num=18.5,
            attr_value_text="18.5 in",
            unit="in"
        )
        
    # Verify restored state passes again
    restored_res = CompatibilityEngine.evaluate("car_subaru_outback_2025", "prod_iceco_vl45")
    assert restored_res["verdict"] == "PASS"
