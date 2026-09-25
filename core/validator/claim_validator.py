"""
Claim Validator
Inspects markdown content against ground-truth database facts and flags prohibited claims.
"""
import re
from typing import List, Dict, Any, Set

class ClaimValidator:
    """Detects hallucinations and illegal test claims."""

    FORBIDDEN_TEST_PATTERNS = [
        r"\b(?:we\s+tested|our\s+test|our\s+tests|hands-on\s+test|in\s+our\s+lab|laboratory\s+testing)\b",
        r"\b(?:we\s+spent\s+\d+\s+hours\s+testing|we\s+drove|we\s+bought\s+this\s+unit)\b",
        r"\b(?:after\s+testing\s+for\s+\d+|our\s+in-depth\s+field\s+test)\b",
        r"\b(?:chúng\s+tôi\s+đã\s+test|chúng\s+tôi\s+đã\s+thử\s+nghiệm|trải\s+nghiệm\s+thực\s+tế\s+của\s+chúng\s+tôi)\b"
    ]

    @classmethod
    def scan_forbidden_claims(cls, content: str) -> List[Dict[str, str]]:
        """
        Flags any unverified first-person testing assertions.
        """
        violations = []
        if not content:
            return violations

        for pat in cls.FORBIDDEN_TEST_PATTERNS:
            for match in re.finditer(pat, content, re.IGNORECASE):
                snippet_start = max(0, match.start() - 40)
                snippet_end = min(len(content), match.end() + 40)
                violations.append({
                    "type": "FORBIDDEN_EXPERIENCE_CLAIM",
                    "matched": match.group(0),
                    "context": content[snippet_start:snippet_end].replace("\n", " ").strip(),
                    "reason": "Rule 10 Violation: Do not claim hands-on laboratory testing without verifiable lab logs."
                })
        return violations

    @classmethod
    def verify_factual_numbers(cls, content: str, allowed_numbers: Set[float]) -> Dict[str, Any]:
        """
        Extracts key technical quantities (Wh, W, lbs, inches) and checks if they exist in the allowed fact set.
        """
        if not content:
            return {"unsupported_metrics": [], "valid_metrics_count": 0}

        # Find numbers with electrical/physical units
        found_metrics = re.findall(r"([\d\.]+)\s*(?:wh|watt|watts|w|lbs|lb|kg|inches|in|\"|cu\s*ft)\b", content, re.IGNORECASE)
        unsupported = []
        valid_count = 0

        for num_str in found_metrics:
            try:
                val = float(num_str)
                # Allow standard margin of 0.1 for rounding
                matched = any(abs(val - allowed) < 0.5 for allowed in allowed_numbers)
                if matched:
                    valid_count += 1
                else:
                    # Ignore common small integers like 1, 2, 3, 5, 10, 12, 24, 100, 110, 120, 240 (voltages, port counts)
                    if val not in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 24.0, 100.0, 110.0, 120.0, 220.0, 240.0]:
                        unsupported.append(val)
            except ValueError:
                pass

        return {
            "unsupported_metrics": list(set(unsupported)),
            "valid_metrics_count": valid_count
        }
