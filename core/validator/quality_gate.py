"""
Quality Gate 2.0
Master evaluator with hard blockers separation.
Priority 6 Implementation:
Never lets high average score mask critical integrity or compliance failures.
"""
from typing import Dict, Any, List, Set, Optional
from .claim_validator import ClaimValidator

class QualityGate:
    """Pre-publish quality assurance engine with hard blocking rules."""

    MIN_PASS_SCORE = 80.0

    @classmethod
    def audit_content(
        cls,
        title: str,
        content: str,
        allowed_numbers: Optional[Set[float]] = None,
        has_primary_evidence: bool = True,
        is_compatibility_valid: bool = True,
        has_calculation_provenance: bool = True,
        has_unresolved_conflict: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates content, computes quality score, and extracts hard blockers.
        If any hard blocker exists, final decision is REJECT regardless of score.
        """
        score = 100.0
        reasons: List[str] = []
        hard_blockers: List[str] = []

        # 1. Hard Blocker: Scan Forbidden Fake-Test Claims (Rule 10)
        forbidden_violations = ClaimValidator.scan_forbidden_claims(content)
        if forbidden_violations:
            for v in forbidden_violations:
                msg = f"Rule 10 Violation: Forbidden testing claim '{v['matched']}' detected."
                hard_blockers.append(msg)
                reasons.append(msg)
            score -= len(forbidden_violations) * 40.0

        # 2. Hard Blocker: Factual Number Integrity Check
        if allowed_numbers:
            metric_check = ClaimValidator.verify_factual_numbers(content, allowed_numbers)
            unsupported = metric_check.get("unsupported_metrics", [])
            if unsupported:
                msg = f"Critical Unsupported Facts: {len(unsupported)} unverified numerical claims ({unsupported})."
                hard_blockers.append(msg)
                reasons.append(msg)
                score -= min(40.0, len(unsupported) * 15.0)

        # 3. Hard Blocker: Primary Evidence Availability
        if not has_primary_evidence:
            msg = "Missing Primary Evidence: Primary entity lacks verified ground-truth documentation."
            hard_blockers.append(msg)
            reasons.append(msg)
            score -= 30.0

        # 4. Hard Blocker: Compatibility Validation
        if not is_compatibility_valid:
            msg = "Invalid Compatibility Result: Dimensional conflict or unverified fitment assertion."
            hard_blockers.append(msg)
            reasons.append(msg)
            score -= 25.0

        # 5. Hard Blocker: Affiliate Disclosure Check (FTC)
        has_disclosure = any(k in content.lower() for k in [
            "affiliate disclosure", "commissions", "as an amazon associate",
            "earns from qualifying purchases", "hoa hồng", "affiliate partner"
        ])
        if not has_disclosure:
            msg = "Affiliate Compliance Failure: Missing mandatory affiliate disclosure statement."
            hard_blockers.append(msg)
            reasons.append(msg)
            score -= 25.0

        # 6. Hard Blocker: Data Conflict Unresolved
        if has_unresolved_conflict:
            msg = "Unresolved Data Conflict: Discrepancy between authoritative sources exceeds tolerance."
            hard_blockers.append(msg)
            reasons.append(msg)
            score -= 25.0

        # 7. Hard Blocker: Calculation Provenance
        if not has_calculation_provenance:
            msg = "Missing Calculation Provenance: Physical/electrical formulas lack input parameters or versioning."
            hard_blockers.append(msg)
            reasons.append(msg)
            score -= 20.0

        # 8. Score Factor: Answer-First Structure (first 200 words)
        words = content.split()
        first_200_words = " ".join(words[:200]).lower()
        has_quick_verdict = any(k in first_200_words for k in ["quick answer", "verdict", "bottom line", "key takeaway", "summary", "tóm tắt", "executive summary"])
        if not has_quick_verdict:
            score -= 10.0
            reasons.append("RECOMMENDATION: Article lacks an explicit 'Quick Answer / Bottom Line' in the first 200 words.")

        # 9. Score Factor: Structured Comparison / Table
        has_table = "|" in content and "---" in content
        if not has_table:
            score -= 15.0
            reasons.append("WARNING: Missing structured markdown comparison or specification table.")

        final_score = max(0.0, min(100.0, score))

        # Decision Logic: Hard Blockers override Score!
        if hard_blockers:
            final_decision = "REJECT"
            is_passed = False
        elif final_score >= cls.MIN_PASS_SCORE:
            final_decision = "INDEX"
            is_passed = True
        elif final_score >= 65.0:
            final_decision = "REVIEW"
            is_passed = False
        else:
            final_decision = "NOINDEX"
            is_passed = False

        return {
            "is_passed": is_passed,
            "final_decision": final_decision,  # INDEX, NOINDEX, REVIEW, REJECT
            "quality_score": round(final_score, 1),
            "hard_blockers": hard_blockers,
            "forbidden_claims_count": len(forbidden_violations),
            "reasons": reasons,
            "status_badge": "PASS" if is_passed else "REJECTED"
        }

    @classmethod
    def evaluate_multi_dimensional(
        cls,
        title: str,
        content: str,
        allowed_numbers: Optional[Set[float]] = None,
        source_coverage: float = 1.0,
        source_authority: float = 0.90,
        data_confidence: float = 1.0,
        has_unique_calculated_data: bool = False,
        cannibalization_risk: float = 0.0,
        has_schema: bool = True,
        has_primary_evidence: bool = True,
        is_compatibility_valid: bool = True,
        has_calculation_provenance: bool = True,
        has_unresolved_conflict: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates multi-signal criteria while strictly enforcing hard blockers.
        """
        base_audit = cls.audit_content(
            title=title,
            content=content,
            allowed_numbers=allowed_numbers,
            has_primary_evidence=has_primary_evidence,
            is_compatibility_valid=is_compatibility_valid,
            has_calculation_provenance=has_calculation_provenance,
            has_unresolved_conflict=has_unresolved_conflict
        )

        word_count = len(content.split())
        signals = {
            "source_coverage": round(source_coverage, 2),
            "source_authority": round(source_authority, 2),
            "data_confidence": round(data_confidence, 2),
            "unique_data": has_unique_calculated_data,
            "cannibalization_risk": round(cannibalization_risk, 2),
            "schema_quality": has_schema,
            "factual_consistency": 1.0 if not base_audit["hard_blockers"] else 0.0,
            "affiliate_compliance": not any("Affiliate Compliance Failure" in hb for hb in base_audit["hard_blockers"]),
            "word_count": word_count
        }

        # Hard blockers take absolute precedence
        if base_audit["hard_blockers"]:
            final_decision = "REJECT"
            is_passed = False
            final_score = min(45.0, base_audit["quality_score"])
        elif cannibalization_risk >= 0.70:
            final_decision = "NOINDEX"
            is_passed = False
            final_score = 50.0
            base_audit["reasons"].append(f"Cannibalization risk too high ({cannibalization_risk}). Recommend MERGE or UPDATE.")
        else:
            bonus = 10.0 if has_unique_calculated_data else 0.0
            bonus += 5.0 if has_schema else 0.0
            final_score = min(100.0, base_audit["quality_score"] * 0.85 + bonus)
            is_passed = final_score >= cls.MIN_PASS_SCORE
            final_decision = "INDEX" if is_passed else ("REVIEW" if final_score >= 65.0 else "NOINDEX")

        return {
            "is_passed": is_passed,
            "final_decision": final_decision,
            "index_verdict": "INDEX_ELIGIBLE" if is_passed else ("REJECTED_UNGROUNDED" if base_audit["hard_blockers"] else final_decision),
            "final_score": round(final_score, 1),
            "hard_blockers": base_audit["hard_blockers"],
            "signals": signals,
            "reasons": base_audit["reasons"]
        }
