"""
GSC Feedback & Opportunity Detector Tests (Section 15)
Tests that striking-distance queries trigger optimization for EXISTING pages,
NOT spawning redundant keyword variation spam articles.
"""
import pytest
from core.feedback.opportunity_detector import OpportunityDetector

def test_gsc_striking_distance_opportunity_optimizes_existing_page():
    """
    Fixture from Section 15:
    Page A: position 18, impressions 4800, clicks 120, query: '45l fridge outback'.
    Expected:
    - Opportunity Detector identifies High-Impact Striking Distance.
    - Recommends OPTIMIZE_EXISTING_PAGE for Page A.
    - create_new_article is strictly False.
    """
    page_a_url = "https://myoverlandblog.com/subaru-outback-camping-guide"
    query = "45l fridge outback"
    impressions = 4800
    clicks = 120
    position = 18.0

    analysis = OpportunityDetector.analyze_query_performance(
        page_url=page_a_url,
        query=query,
        impressions=impressions,
        clicks=clicks,
        position=position
    )

    assert analysis["opportunity_detected"] is True, "Must detect striking distance opportunity"
    assert analysis["action"] == "OPTIMIZE_EXISTING_PAGE"
    assert analysis["priority"] == "HIGH"
    assert analysis["create_new_article"] is False, "Must NOT create a new keyword variation article"
    assert any("Striking Distance" in r for r in analysis["recommendations"])
    assert any("cannibalization" in r for r in analysis["recommendations"])
