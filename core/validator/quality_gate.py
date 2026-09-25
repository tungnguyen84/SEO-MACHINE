"""
Quality Gate
Master evaluator that scores drafts, enforces SEO/Affiliate compliance, and grants publishing clearance.
"""
from typing import Dict, Any, List, Set, Optional
from .claim_validator import ClaimValidator

class QualityGate:
    """Pre-publish quality assurance engine."""

    MIN_PASS_SCORE = 80.0

    @classmethod
    def audit_content(
        cls,
        title: str,
        content: str,
        allowed_numbers: Optional[Set[float]] = None
    ) -> Dict[str, Any]:
        score = 100.0
        reasons = []
        is_passed = True

        # 1. Scan Forbidden Fake-Test Claims
        forbidden_violations = ClaimValidator.scan_forbidden_claims(content)
        if forbidden_violations:
            penalty = len(forbidden_violations) * 35.0
            score -= penalty
            is_passed = False
            for v in forbidden_violations:
                reasons.append(f"CRITICAL: Found forbidden claim '{v['matched']}' in context: \"{v['context']}\"")

        # 2. Factual Number Integrity Check
        if allowed_numbers:
            metric_check = ClaimValidator.verify_factual_numbers(content, allowed_numbers)
            if metric_check["unsupported_metrics"]:
                penalty = min(30.0, len(metric_check["unsupported_metrics"]) * 10.0)
                score -= penalty
                reasons.append(f"WARNING: Found {len(metric_check['unsupported_metrics'])} unverified numerical claims: {metric_check['unsupported_metrics']}")

        # 3. Answer-First Evaluation (Direct conclusion in first 200 words)
        words = content.split()
        first_200_words = " ".join(words[:200]).lower()
        has_quick_verdict = any(k in first_200_words for k in ["quick answer", "verdict", "bottom line", "key takeaway", "summary", "tóm tắt"])
        if not has_quick_verdict:
            score -= 10.0
            reasons.append("RECOMMENDATION: Article lacks an explicit 'Quick Answer / Bottom Line' in the first 200 words.")

        # 4. Affiliate Disclosure Check
        has_disclosure = any(k in content.lower() for k in ["affiliate disclosure", "commissions", "as an amazon associate", "earns from qualifying purchases", "hoa hồng"])
        if not has_disclosure:
            score -= 20.0
            is_passed = False
            reasons.append("CRITICAL: Missing mandatory Amazon Affiliate Disclosure statement.")

        # 5. Technical Specification / Table check
        has_table = "|" in content and "---" in content
        if not has_table:
            score -= 15.0
            reasons.append("WARNING: Missing structured markdown comparison or specification table.")

        final_score = max(0.0, min(100.0, score))
        if final_score < cls.MIN_PASS_SCORE:
            is_passed = False

        return {
            "is_passed": is_passed,
            "quality_score": round(final_score, 1),
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
        has_schema: bool = True
    ) -> Dict[str, Any]:
        """
        Comprehensive multi-dimensional quality gate:
        - source_coverage, source_authority, data_confidence
        - unique_data (deterministic calculation output)
        - factual_consistency & affiliate_compliance
        Word count is explicitly NOT a primary quality signal.
        """
        base_audit = cls.audit_content(title, content, allowed_numbers)
        word_count = len(content.split())

        # Evaluate individual signals
        signals = {
            "source_coverage": round(source_coverage, 2),
            "source_authority": round(source_authority, 2),
            "data_confidence": round(data_confidence, 2),
            "unique_data": has_unique_calculated_data,
            "cannibalization_risk": round(cannibalization_risk, 2),
            "schema_quality": has_schema,
            "factual_consistency": 1.0 if base_audit["forbidden_claims_count"] == 0 and not any("unverified" in r for r in base_audit["reasons"]) else 0.2,
            "affiliate_compliance": not any("Missing mandatory Amazon Affiliate Disclosure" in r for r in base_audit["reasons"]),
            "word_count": word_count
        }

        # Calculate final indexability readiness score
        # Even with high word count, unsupported claims or fake testing claims will destroy the score
        if not signals["factual_consistency"] or not signals["affiliate_compliance"] or base_audit["forbidden_claims_count"] > 0:
            is_passed = False
            index_verdict = "REJECTED_UNGROUNDED"
            final_score = min(45.0, base_audit["quality_score"])
        elif cannibalization_risk >= 0.70:
            is_passed = False
            index_verdict = "REJECTED_CANNIBALIZATION_RISK"
            final_score = 50.0
        else:
            bonus = 10.0 if has_unique_calculated_data else 0.0
            bonus += 5.0 if has_schema else 0.0
            final_score = min(100.0, base_audit["quality_score"] * 0.85 + bonus)
            is_passed = final_score >= cls.MIN_PASS_SCORE
            index_verdict = "INDEX_ELIGIBLE" if is_passed else "NEEDS_REVISION"

        return {
            "is_passed": is_passed,
            "index_verdict": index_verdict,
            "final_score": round(final_score, 1),
            "signals": signals,
            "reasons": base_audit["reasons"]
        }
