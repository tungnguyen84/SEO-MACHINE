"""
Opportunity Detector & GSC Feedback Engine (Section 15)
Analyzes Google Search Console impressions, positions, and click metrics.
Directs improvements to EXISTING pages rather than spawning redundant keyword variation articles.
"""
from typing import Dict, Any, List, Optional

class OpportunityDetector:
    """
    Evaluates real or ingested GSC query/page performance.
    Detects Striking Distance opportunities (Positions 11-20 with high impressions).
    Enforces Rule: Optimize existing ranking URL; DO NOT cannibalize by creating new variation pages.
    """

    @classmethod
    def analyze_query_performance(
        cls,
        page_url: str,
        query: str,
        impressions: int,
        clicks: int,
        position: float
    ) -> Dict[str, Any]:
        ctr = (clicks / impressions * 100.0) if impressions > 0 else 0.0

        # Striking Distance: Ranked on page 2 (pos 11 to 25) with solid impressions (>1000)
        is_striking_distance = 11.0 <= position <= 25.0 and impressions >= 1000
        is_low_ctr_page_one = 1.0 <= position <= 10.0 and ctr < 3.0 and impressions >= 2000

        if is_striking_distance:
            action = "OPTIMIZE_EXISTING_PAGE"
            priority = "HIGH"
            recommendations = [
                f"Page is in Striking Distance (Position {round(position, 1)} with {impressions} impressions).",
                f"Add targeted section/H2 for query '{query}' to the existing page '{page_url}'.",
                "Inject verified technical specifications, comparison table, or compatibility card.",
                "DO NOT create a separate keyword article; doing so would trigger keyword cannibalization."
            ]
            create_new_article = False
        elif is_low_ctr_page_one:
            action = "OPTIMIZE_SNIPPET_CTR"
            priority = "MEDIUM"
            recommendations = [
                f"Ranking on Page 1 (Position {round(position, 1)}) but CTR is low ({round(ctr, 2)}%).",
                "Revise title tag and meta description to emphasize exact verified measurements.",
                "Verify FAQ or Product schema is present to qualify for rich snippets."
            ]
            create_new_article = False
        elif position > 25.0:
            action = "BUILD_TOPICAL_AUTHORITY"
            priority = "LOW"
            recommendations = [
                f"Position {round(position, 1)} is outside top 25.",
                "Strengthen internal link graph from high-authority pillar articles."
            ]
            create_new_article = False
        else:
            action = "MONITOR"
            priority = "LOW"
            recommendations = ["Performance is within healthy baseline."]
            create_new_article = False

        return {
            "page_url": page_url,
            "query": query,
            "impressions": impressions,
            "clicks": clicks,
            "position": position,
            "ctr_percent": round(ctr, 2),
            "opportunity_detected": is_striking_distance or is_low_ctr_page_one,
            "action": action,
            "priority": priority,
            "create_new_article": create_new_article,
            "recommendations": recommendations,
            "provenance": "REAL_GSC"
        }
