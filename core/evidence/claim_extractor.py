"""
Claim Extractor
Extracts factual claims and quantitative specifications from manufacturer datasheets and manuals.
"""
import re
from typing import List, Dict, Any, Optional
from core.entities.normalizer import UnitNormalizer

class ClaimExtractor:
    """Parses text documents and user manuals into verified claims."""

    SPEC_PATTERNS = {
        "battery_capacity_wh": [
            r"(?:battery\s+capacity|capacity|energy)[\s:]*([\d,\.]+\s*(?:wh|kwh|mah))",
            r"([\d,\.]+\s*(?:wh|kwh))\s+(?:lithium|lifepo4|lfp|battery)"
        ],
        "inverter_continuous_watts": [
            r"(?:ac\s+output|continuous\s+output|rated\s+power)[\s:]*([\d,\.]+\s*(?:w|kw))\b",
            r"([\d,\.]+\s*w)\s+(?:pure\s+sine\s+wave|continuous)"
        ],
        "inverter_surge_watts": [
            r"(?:surge|peak|x-boost|max\s+surge)[\s:]*([\d,\.]+\s*(?:w|kw))\b",
            r"([\d,\.]+\s*w)\s+surge"
        ],
        "weight_lbs": [
            r"(?:weight|net\s+weight)[\s:]*([\d,\.]+\s*(?:lbs|lb|kg))\b",
            r"([\d,\.]+\s*(?:lbs|kg))\s*(?:\/|\()\s*[\d,\.]+\s*(?:lbs|kg)"
        ],
        "volume_liters": [
            r"(?:capacity|volume|storage\s+volume)[\s:]*([\d,\.]+\s*(?:l|liters|quarts|qt))\b"
        ],
        "dimensions_inches": [
            r"(?:dimensions|size|external\s+dimensions)[\s:]*([\d\.]+\s*(?:x|×|\*)\s*[\d\.]+\s*(?:x|×|\*)\s*[\d\.]+\s*(?:in|inches|mm|cm))"
        ]
    }

    @classmethod
    def extract_claims_from_text(cls, text: str, page_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scans raw text block and extracts structured claims with exact quote evidence.
        """
        claims = []
        if not text:
            return claims

        lines = text.split("\n")

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) < 5:
                continue

            for attr_key, patterns in cls.SPEC_PATTERNS.items():
                for pat in patterns:
                    match = re.search(pat, line_str, re.IGNORECASE)
                    if match:
                        raw_matched_val = match.group(1)
                        num_val, text_val, unit = UnitNormalizer.normalize_attribute(attr_key, raw_matched_val)

                        claims.append({
                            "attribute_key": attr_key,
                            "raw_matched_value": raw_matched_val,
                            "normalized_text": text_val,
                            "normalized_num": num_val,
                            "unit": unit,
                            "raw_quote": line_str[:300],
                            "page_number": page_number,
                            "confidence_score": 0.95
                        })
                        break

        return claims
