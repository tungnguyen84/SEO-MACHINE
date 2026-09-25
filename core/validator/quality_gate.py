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
