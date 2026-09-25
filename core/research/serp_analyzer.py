"""
SERP Research, Snapshot Storage, and Opportunity Scoring Engine.
Analyzes real SERP competitor landscapes, identifies content/data gaps,
and evaluates evidence readiness without fabricating search metrics.
"""
import json
import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from core.database import get_connection


class CompetitorType(str, Enum):
    MANUFACTURER = "MANUFACTURER"       # OEM subaru.com, toyota.com, iceco.com
    RETAILER = "RETAILER"               # amazon.com, rei.com, homedepot.com
    FORUM = "FORUM"                     # subaruoutback.org, rav4world.com, bronco6g.com
    REDDIT = "REDDIT"                   # reddit.com/r/carcamping
    YOUTUBE = "YOUTUBE"                 # youtube.com
    EDITORIAL = "EDITORIAL"             # caranddriver.com, motortrend.com, outdoorgearlab.com
    AFFILIATE = "AFFILIATE"             # thin niche affiliate blogs
    DATABASE = "DATABASE"               # edmunds.com specs, cars.com
    OTHER = "OTHER"


class EvidenceReadiness(str, Enum):
    READY = "READY"                     # Required vehicle and gear specs verified
    PARTIAL = "PARTIAL"                 # Vehicle verified, specific gear or electrical pending
    RESEARCH_REQUIRED = "RESEARCH_REQUIRED" # Key clearance or amperage data missing
    BLOCKED = "BLOCKED"                 # No credible OEM or manufacturer source available


class VolumeProvenance(str, Enum):
    REAL = "REAL"                       # From direct Google Keyword Planner API or paid data provider
    ESTIMATED = "ESTIMATED"             # Modelled from impression share / striking distance
    HEURISTIC = "HEURISTIC"             # Heuristic rule-based index
    UNKNOWN = "UNKNOWN"                 # Explicitly unmeasured (prevents false claims)


class SerpAnalyzer:
    """
    Performs SERP snapshot ingestion, competitor categorization,
    gap discovery, and deterministic opportunity scoring.
    """

    @classmethod
    def classify_competitor(cls, url: str, domain: str, title: str) -> CompetitorType:
        """Classifies a SERP result based on domain and page patterns."""
        dom = domain.lower()
        t = title.lower()

        if any(f in dom for f in ["subaruoutback.org", "rav4world.com", "bronco6g.com", "crvownersclub.com", "expeditionportal.com", "overlandbound.com", "tacomaworld.com"]):
            return CompetitorType.FORUM
        if "reddit.com" in dom:
            return CompetitorType.REDDIT
        if "youtube.com" in dom or "youtu.be" in dom:
            return CompetitorType.YOUTUBE
        if any(m in dom for m in ["subaru.com", "toyota.com", "ford.com", "honda.com", "icecofreezer.com", "dometic.com", "bougerv.com", "ecoflow.com", "jackery.com"]):
            return CompetitorType.MANUFACTURER
        if any(r in dom for r in ["amazon.com", "rei.com", "walmart.com", "target.com", "homedepot.com", "basspro.com"]):
            return CompetitorType.RETAILER
        if any(e in dom for e in ["caranddriver.com", "motortrend.com", "outdoorgearlab.com", "gearjunkie.com", "wirecutter.com", "nytimes.com/wirecutter"]):
            return CompetitorType.EDITORIAL
        if any(d in dom for d in ["edmunds.com", "cars.com", "kbb.com"]):
            return CompetitorType.DATABASE
        if any(a in dom for a in ["campersrule.com", "overlandoutfitters.com", "carcampguide.com", "gearadviser.com"]):
            return CompetitorType.AFFILIATE
        return CompetitorType.OTHER

    @classmethod
    def calculate_serp_opportunity_score(
        cls,
        intent_gap: float,                  # 0 - 100: extent to which SERP fails user core intent
        weak_result_presence: float,        # 0 - 100: presence of thin pages, old threads
        forum_dependency: float,            # 0 - 100: presence of Reddit/Forums in top 5
        exact_answer_gap: float,            # 0 - 100: lack of concise, direct dimension answer
        data_gap: float,                    # 0 - 100: lack of exact engineering/capacity numbers
        compatibility_gap: float,           # 0 - 100: lack of clear Pass/Fail fitment verdict
        authority_barrier: float,           # 0 - 100: presence of dominant DR 90+ publishers (deduction)
        content_freshness_gap: float,       # 0 - 100: age of ranking articles (>3 years old)
        unique_utility_potential: float,    # 0 - 100: opportunity to render a fitment card / calculator
        commercial_intent: float            # 0 - 100: commercial or practical buyer value
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculates an explainable SERP Opportunity Score (0 - 100).
        High score indicates a high-probability search gap where structured data can win.
        """
        weights = {
            "intent_gap": 0.12,
            "weak_result_presence": 0.10,
            "forum_dependency": 0.12,
            "exact_answer_gap": 0.12,
            "data_gap": 0.14,
            "compatibility_gap": 0.14,
            "authority_barrier_inverse": 0.08,
            "content_freshness_gap": 0.06,
            "unique_utility_potential": 0.12
        }

        # Inverse authority barrier: if authority barrier is high (80), inverse is low (20)
        auth_inverse = max(0.0, 100.0 - authority_barrier)

        raw_score = (
            intent_gap * weights["intent_gap"] +
            weak_result_presence * weights["weak_result_presence"] +
            forum_dependency * weights["forum_dependency"] +
            exact_answer_gap * weights["exact_answer_gap"] +
            data_gap * weights["data_gap"] +
            compatibility_gap * weights["compatibility_gap"] +
            auth_inverse * weights["authority_barrier_inverse"] +
            content_freshness_gap * weights["content_freshness_gap"] +
            unique_utility_potential * weights["unique_utility_potential"]
        )

        # Commercial multiplier adjustment (subtle, 0.90 to 1.05)
        multiplier = 0.90 + (commercial_intent / 100.0) * 0.15
        final_score = round(min(96.0, max(10.0, raw_score * multiplier)), 1)

        breakdown = {
            "intent_gap": round(intent_gap, 1),
            "weak_result_presence": round(weak_result_presence, 1),
            "forum_dependency": round(forum_dependency, 1),
            "exact_answer_gap": round(exact_answer_gap, 1),
            "data_gap": round(data_gap, 1),
            "compatibility_gap": round(compatibility_gap, 1),
            "authority_barrier": round(authority_barrier, 1),
            "content_freshness_gap": round(content_freshness_gap, 1),
            "unique_utility_potential": round(unique_utility_potential, 1),
            "commercial_intent": round(commercial_intent, 1),
            "final_opportunity_score": final_score
        }
        return final_score, breakdown

    @classmethod
    def save_serp_snapshot(
        cls,
        query: str,
        top_results: List[Dict[str, Any]],
        serp_gap: Dict[str, Any],
        opportunity_score: float,
        opportunity_breakdown: Dict[str, Any],
        evidence_readiness: EvidenceReadiness,
        market: str = "US",
        language: str = "en",
        device: str = "desktop",
        volume_label: VolumeProvenance = VolumeProvenance.ESTIMATED,
        estimated_volume: int = 0
    ) -> int:
        """Persists a complete SERP snapshot into the database."""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO serp_snapshots (
            query, market, language, device, volume_label, estimated_volume,
            top_results_json, serp_gap_json, opportunity_score,
            opportunity_breakdown_json, evidence_readiness, retrieved_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            query, market, language, device, volume_label.value, estimated_volume,
            json.dumps(top_results), json.dumps(serp_gap), opportunity_score,
            json.dumps(opportunity_breakdown), evidence_readiness.value
        ))
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return snapshot_id

    @classmethod
    def get_latest_snapshot(cls, query: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent snapshot for a query."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM serp_snapshots WHERE query = ? ORDER BY id DESC LIMIT 1", (query,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["top_results"] = json.loads(d["top_results_json"])
        d["serp_gap"] = json.loads(d["serp_gap_json"]) if d.get("serp_gap_json") else {}
        d["opportunity_breakdown"] = json.loads(d["opportunity_breakdown_json"]) if d.get("opportunity_breakdown_json") else {}
        return d
