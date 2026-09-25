"""
Anti-Hallucination Tests (Section 6)
Tests strict factual boundary enforcement and prohibition of fake testing claims:
- CASE A: AI hallucinating a dimension not in structured data -> UNSUPPORTED, QualityGate REJECT
- CASE B: AI writing 'we tested', 'our tests', 'hands-on tested' -> QualityGate REJECT
- CASE C: Conflicting authoritative source values -> DATA_CONFLICT / REVIEW (no arbitrary choice)
- CASE D: Source retrieval failure -> SOURCE_FAILED (no fallback mock/fake product)
"""
import pytest
from core.validator.claim_validator import ClaimValidator
from core.validator.quality_gate import QualityGate
from connectors.amazon import AmazonConnector

def test_case_a_unsupported_dimension_rejected():
    """CASE A: Content contains numerical dimensions not in verified database facts."""
    # Verified ground truth: ICECO VL45 height is 18.5 in, power is 45W
    allowed_numbers = {18.5, 45.0, 49.6, 27.2, 16.3}
    
    # Hallucinated text inventing 29.5 inches height and 125W draw
    hallucinated_content = """
    # ICECO VL45 Review
    The ICECO VL45 measures 29.5 inches in height and draws 125W continuous power.
    Affiliate disclosure: We earn commissions from qualifying purchases.
    | Metric | Spec |
    |---|---|
    | Height | 29.5 in |
    """
    
    # 1. ClaimValidator must flag 29.5 and 125.0 as unsupported
    metric_check = ClaimValidator.verify_factual_numbers(hallucinated_content, allowed_numbers)
    assert len(metric_check["unsupported_metrics"]) > 0, "ClaimValidator must detect unsupported numerical specs"
    assert 29.5 in metric_check["unsupported_metrics"] or 125.0 in metric_check["unsupported_metrics"]
    
    # 2. QualityGate must penalize and reject content with unverified metrics
    audit = QualityGate.audit_content("ICECO Review", hallucinated_content, allowed_numbers)
    assert any("unverified numerical claims" in r for r in audit["reasons"])
    assert audit["quality_score"] < 100.0

def test_case_b_forbidden_test_claims_rejected():
    """CASE B: Content uses first-person fake testing claims without lab proof."""
    forbidden_content = """
    # 2025 Subaru Outback Cargo Test
    We tested the Outback in our lab for 30 hours and our in-depth field test proved it fits all coolers.
    Affiliate disclosure: We earn from qualifying purchases.
    Quick Answer: The Outback fits standard 12V fridges.
    | Dimension | Size |
    |---|---|
    | Height | 31.8 in |
    """
    
    # 1. ClaimValidator scans and flags forbidden strings
    violations = ClaimValidator.scan_forbidden_claims(forbidden_content)
    assert len(violations) >= 2, "ClaimValidator must catch 'we tested' and 'field test'"
    
    # 2. QualityGate must immediately REJECT content
    audit = QualityGate.audit_content("Outback Test", forbidden_content, {31.8})
    assert audit["is_passed"] is False, "QualityGate must REJECT content with fake testing claims"
    assert audit["status_badge"] == "REJECTED"
    assert audit["forbidden_claims_count"] >= 2

def test_case_c_conflicting_sources_flagged():
    """CASE C: Two authoritative sources report conflicting values."""
    # Source A reports battery is 1056Wh, Source B reports 850Wh (20% variance)
    source_a_capacity = 1056.0
    source_b_capacity = 850.0
    
    conflict_result = ClaimValidator.check_source_conflict(source_a_capacity, source_b_capacity, tolerance=0.05)
    assert conflict_result["has_conflict"] is True, "Must detect discrepancy above 5%"
    assert conflict_result["status"] == "DATA_CONFLICT"
    assert conflict_result["action"] == "REVIEW"
    assert "Discrepancy detected" in conflict_result["reason"]

def test_case_d_source_retrieval_failure_no_fake_injection():
    """CASE D: Source lookup failure returns None/Error without injecting mock/fake products."""
    connector = AmazonConnector()
    # Query non-existent bogus ASIN
    res = connector.get_product_details("B000000000_NONEXISTENT")
    assert res is None, "Failed product lookup must return None, NOT a mock/fake product"
