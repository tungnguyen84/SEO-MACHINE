"""
Quality Gate Multi-Dimensional & Hard Blockers Tests
Priority 6 Verification
"""
import pytest
from core.validator.quality_gate import QualityGate

def test_quality_hard_blocker_overrides_score():
    """
    Test that even if an article has an otherwise high score (e.g. 95%),
    any hard blocker (e.g. Rule 10 fake testing claim or unverified facts)
    immediately forces final_decision = 'REJECT'.
    """
    well_written_article = """
    # 2025 Subaru Outback Setup Guide
    
    Executive summary: The ICECO VL45 fits with 13.3 inches vertical clearance.
    
    Affiliate disclosure: We earn commissions from qualifying purchases as an Amazon Associate.
    
    | Vehicle Cargo Height | Fridge Height | Vertical Clearance | 12V Power Draw |
    |---|---|---|---|
    | 31.8 in | 18.5 in | 13.3 in | 45.0W |
    
    We tested this unit in our lab for 75 hours across Colorado trails.
    """
    
    allowed_numbers = {31.8, 18.5, 13.3, 45.0}

    eval_res = QualityGate.audit_content(
        title="Subaru Outback Setup Guide",
        content=well_written_article,
        allowed_numbers=allowed_numbers
    )

    assert len(eval_res["hard_blockers"]) >= 1
    assert any("Rule 10" in hb for hb in eval_res["hard_blockers"])
    assert eval_res["final_decision"] == "REJECT"
    assert eval_res["is_passed"] is False

def test_quality_gate_4000_word_spam_rejected():
    """A 4,000-word article filled with AI filler and unsupported/fake claims must be REJECTED."""
    filler = "This is a detailed analysis of battery life and overland refrigerator performance across multiple environments. "
    spam_body = filler * 250  # ~4,000 words
    
    bloated_article = f"""
    # The Ultimate 4000 Word Guide to Camping
    We tested this unit in our lab for 50 hours and drove across the country.
    The fridge draws 999.0W power in our tests.
    {spam_body}
    """
    
    allowed_numbers = {45.0, 18.5}
    
    eval_res = QualityGate.evaluate_multi_dimensional(
        title="4000 Word Camping Guide",
        content=bloated_article,
        allowed_numbers=allowed_numbers,
        source_coverage=0.3,
        has_unique_calculated_data=False
    )
    
    assert eval_res["is_passed"] is False
    assert eval_res["final_decision"] == "REJECT"
    assert len(eval_res["hard_blockers"]) >= 1
    assert eval_res["signals"]["word_count"] > 3500

def test_quality_gate_800_word_grounded_article_passes():
    """An 800-word concise article with verified evidence, calculated data, and disclosure PASSES."""
    chunk = "The 12V portable compressor operates efficiently on the rear auxiliary port of the Outback. "
    body = chunk * 50  # ~750 words
    
    grounded_article = f"""
    # 2025 Subaru Outback & ICECO VL45 Compatibility Guide
    
    Quick Answer: The ICECO VL45 fits upright in the 2025 Subaru Outback cargo compartment with 13.3 inches of vertical clearance.
    
    Affiliate disclosure: We earn commissions from qualifying purchases as an Amazon Associate.
    
    | Vehicle Cargo Height | Fridge Height | Vertical Clearance | 12V Power Draw |
    |---|---|---|---|
    | 31.8 in | 18.5 in | 13.3 in | 45.0W |
    
    {body}
    """
    
    allowed_numbers = {31.8, 18.5, 13.3, 45.0}
    
    eval_res = QualityGate.evaluate_multi_dimensional(
        title="Subaru Outback & ICECO VL45 Compatibility Guide",
        content=grounded_article,
        allowed_numbers=allowed_numbers,
        source_coverage=1.0,
        source_authority=0.95,
        data_confidence=1.0,
        has_unique_calculated_data=True,
        has_schema=True
    )
    
    assert eval_res["is_passed"] is True
    assert eval_res["final_decision"] == "INDEX"
    assert len(eval_res["hard_blockers"]) == 0
    assert eval_res["final_score"] >= 80.0
    assert eval_res["signals"]["unique_data"] is True
    assert eval_res["signals"]["word_count"] < 1200
