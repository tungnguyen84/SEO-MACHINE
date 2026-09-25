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
        source_coverage: float = 0.92,
        source_authority: float = 0.95,
        data_confidence: float = 0.92,
        has_unique_calculated_data: bool = False,
        cannibalization_risk: float = 0.0,
        intent_match_score: float = 0.95,
        serp_differentiation_score: float = 0.88,
        is_stale_evidence: bool = False,
        non_critical_unsupported_count: int = 0,
        affiliate_link_count: Optional[int] = None,
        has_schema: bool = True,
        has_primary_evidence: bool = True,
        is_compatibility_valid: bool = True,
        has_calculation_provenance: bool = True,
        has_unresolved_conflict: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates multi-signal criteria with calibrated realistic scoring.
        Quality score 100/100 is strictly reserved for theoretical perfection.
        Provides transparent 9-point explainability breakdown.
        Hard blockers strictly force REJECT decision regardless of score.
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

        words = content.split()
        word_count = len(words)

        # 1. Source Coverage (0-100)
        cov_100 = round(max(0.0, min(100.0, source_coverage * 100.0 if source_coverage <= 1.0 else source_coverage)), 1)

        # 2. Source Authority (0-100)
        auth_100 = round(max(0.0, min(100.0, source_authority * 100.0 if source_authority <= 1.0 else source_authority)), 1)

        # 3. Data Confidence (0-100)
        conf_100 = round(max(0.0, min(100.0, data_confidence * 100.0 if data_confidence <= 1.0 else data_confidence)), 1)

        # 4. Unique Utility (0-100)
        # AI filler penalty: 4,000 words without unique data/utility drops to 35
        has_table = "|" in content and "---" in content
        if word_count > 3000 and not has_unique_calculated_data:
            util_100 = 35.0
        elif has_unique_calculated_data and has_table:
            util_100 = 88.0
        elif has_unique_calculated_data or has_table:
            util_100 = 75.0
        else:
            util_100 = 45.0

        # 5. Intent Match (0-100)
        intent_100 = round(max(0.0, min(100.0, intent_match_score * 100.0 if intent_match_score <= 1.0 else intent_match_score)), 1)

        # 6. SERP Differentiation (0-100)
        # Cannibalization drops differentiation sharply
        if cannibalization_risk >= 0.70:
            diff_100 = 25.0
        elif cannibalization_risk >= 0.40:
            diff_100 = 55.0
        else:
            diff_100 = round(max(0.0, min(100.0, serp_differentiation_score * 100.0 if serp_differentiation_score <= 1.0 else serp_differentiation_score)), 1)

        # 7. Factual Consistency (0-100)
        if base_audit["hard_blockers"]:
            fact_100 = 0.0
        elif non_critical_unsupported_count > 0:
            fact_100 = max(50.0, 85.0 - (non_critical_unsupported_count * 15.0))
        else:
            fact_100 = 96.0  # realistic high, 100 is theoretical perfection

        # 8. Affiliate Compliance (0-100)
        # Count affiliate markdown links or [Available Here]
        num_aff_links = affiliate_link_count
        if num_aff_links is None:
            num_aff_links = content.count("[http") + content.count("Available Here") + content.count("buy_button")
        
        has_ftc = not any("Affiliate Compliance Failure" in hb for hb in base_audit["hard_blockers"])
        if not has_ftc:
            aff_100 = 0.0
        elif word_count > 0 and (num_aff_links / (word_count / 100.0)) > 2.5:
            # Over-commercial affiliate link stuffing: > 2.5 links per 100 words
            aff_100 = 50.0
        elif word_count > 0 and (num_aff_links / (word_count / 100.0)) > 1.5:
            aff_100 = 70.0
        else:
            aff_100 = 95.0

        # 9. Freshness (0-100)
        fresh_100 = 40.0 if is_stale_evidence else 90.0

        # Weighted Composite Score Calculation
        # Weights sum to 1.0
        weights = {
            "source_coverage": 0.12,
            "source_authority": 0.12,
            "data_confidence": 0.12,
            "unique_utility": 0.14,
            "intent_match": 0.12,
            "serp_differentiation": 0.12,
            "factual_consistency": 0.16,
            "freshness": 0.10
        }
        composite = (
            cov_100 * weights["source_coverage"] +
            auth_100 * weights["source_authority"] +
            conf_100 * weights["data_confidence"] +
            util_100 * weights["unique_utility"] +
            intent_100 * weights["intent_match"] +
            diff_100 * weights["serp_differentiation"] +
            fact_100 * weights["factual_consistency"] +
            fresh_100 * weights["freshness"]
        )

        # Commercial Stuffing Penalty
        if aff_100 <= 50.0:
            composite -= 15.0
        elif aff_100 <= 70.0:
            composite -= 8.0

        # Low coverage penalty
        if cov_100 < 80.0:
            composite -= (80.0 - cov_100) * 0.40

        # Non-critical claim penalty
        if non_critical_unsupported_count > 0:
            composite -= (non_critical_unsupported_count * 8.0)

        # Schema bonus
        if has_schema:
            composite += 2.0

        composite = max(0.0, min(94.5, composite))

        breakdown = {
            "Source Coverage": cov_100,
            "Source Authority": auth_100,
            "Data Confidence": conf_100,
            "Unique Utility": util_100,
            "Intent Match": intent_100,
            "SERP Differentiation": diff_100,
            "Factual Consistency": fact_100,
            "Affiliate Compliance": aff_100,
            "Freshness": fresh_100
        }

        # Deductions and Explainability notes
        reasons = list(base_audit["reasons"])
        if cov_100 < 90.0:
            reasons.append(f"Deduction ({cov_100}/100 Source Coverage): Incomplete technical specification coverage.")
        if aff_100 < 75.0:
            reasons.append(f"Deduction ({aff_100}/100 Affiliate Compliance): High affiliate link density or missing disclosures.")
        if util_100 < 60.0:
            reasons.append(f"Deduction ({util_100}/100 Unique Utility): Lengthy content lacks unique engineering calculations or tables.")
        if diff_100 < 60.0:
            reasons.append(f"Deduction ({diff_100}/100 SERP Differentiation): High overlap/cannibalization with existing topical URLs.")
        if is_stale_evidence:
            reasons.append("Deduction (40/100 Freshness): Associated source evidence has been marked STALE by hash change.")
        if intent_100 < 65.0:
            reasons.append(f"Deduction ({intent_100}/100 Intent Match): Article focus diverges from target search query intent.")

        # Hard Blockers override Score!
        if base_audit["hard_blockers"]:
            final_decision = "REJECT"
            is_passed = False
            final_score = min(45.0, composite)
        elif cannibalization_risk >= 0.70:
            final_decision = "NOINDEX"
            is_passed = False
            final_score = min(55.0, composite)
        elif is_stale_evidence or util_100 < 40.0:
            final_decision = "NOINDEX" if util_100 < 40.0 else "REVIEW"
            is_passed = False
            final_score = min(64.0 if util_100 < 40.0 else 72.0, composite)
        elif intent_100 < 65.0:
            final_decision = "REVIEW"
            is_passed = False
            final_score = min(74.0, composite)
        elif composite >= cls.MIN_PASS_SCORE:
            final_decision = "INDEX"
            is_passed = True
            final_score = composite
        elif composite >= 65.0:
            final_decision = "REVIEW"
            is_passed = False
            final_score = composite
        else:
            final_decision = "NOINDEX"
            is_passed = False
            final_score = composite

        signals = {
            "source_coverage": round(cov_100 / 100.0, 2),
            "source_authority": round(auth_100 / 100.0, 2),
            "data_confidence": round(conf_100 / 100.0, 2),
            "unique_data": has_unique_calculated_data,
            "cannibalization_risk": round(cannibalization_risk, 2),
            "schema_quality": has_schema,
            "factual_consistency": round(fact_100 / 100.0, 2),
            "affiliate_compliance": round(aff_100 / 100.0, 2),
            "word_count": word_count
        }

        return {
            "is_passed": is_passed,
            "final_decision": final_decision,
            "index_verdict": "INDEX_ELIGIBLE" if is_passed else ("REJECTED_UNGROUNDED" if base_audit["hard_blockers"] else final_decision),
            "final_score": round(final_score, 1),
            "score_breakdown": breakdown,
            "hard_blockers": base_audit["hard_blockers"],
            "signals": signals,
            "reasons": reasons
        }
