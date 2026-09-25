"""
GSC Feedback & Daily Metric History Tests
Priority 8 Verification
"""
import pytest
from core.database import init_db
from core.feedback.opportunity_detector import OpportunityDetector
from core.feedback.gsc_client import GSCClient

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_gsc_striking_distance_opportunity_optimizes_existing_page():
    """
    Page A: position 18, impressions 4800, clicks 120, query: '45l fridge outback'.
    Must recommend OPTIMIZE_EXISTING_PAGE and refuse to spawn cannibalizing article.
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

    assert analysis["opportunity_detected"] is True
    assert analysis["action"] == "OPTIMIZE_EXISTING_PAGE"
    assert analysis["priority"] == "HIGH"
    assert analysis["create_new_article"] is False
    assert any("Striking Distance" in r for r in analysis["recommendations"])

def test_gsc_daily_history_not_overwritten():
    """
    Test that daily historical records are preserved over time.
    Ingesting metrics for 2026-09-02 must NOT overwrite 2026-09-01.
    """
    page_url = "https://myoverlandblog.com/subaru-outback-fridge"
    query = "subaru outback 12v fridge"

    # Ingest Day 1
    GSCClient.record_daily_metric(
        page_url=page_url,
        query=query,
        impressions=500,
        clicks=15,
        ctr=3.0,
        position=14.2,
        recorded_date="2026-09-01"
    )

    # Ingest Day 2
    GSCClient.record_daily_metric(
        page_url=page_url,
        query=query,
        impressions=750,
        clicks=25,
        ctr=3.33,
        position=13.8,
        recorded_date="2026-09-02"
    )

    # Ingest Day 3
    GSCClient.record_daily_metric(
        page_url=page_url,
        query=query,
        impressions=1100,
        clicks=42,
        ctr=3.82,
        position=12.5,
        recorded_date="2026-09-03"
    )

    # Verify both dates exist independently in history
    dates = GSCClient.get_distinct_historical_dates(page_url, query)
    assert len(dates) == 3
    assert "2026-09-01" in dates
    assert "2026-09-02" in dates
    assert "2026-09-03" in dates

    # Verify window aggregation
    agg = GSCClient.get_aggregated_metrics(page_url=page_url, query=query, days=90)
    assert agg["total_impressions"] == 500 + 750 + 1100  # 2350
    assert agg["total_clicks"] == 15 + 25 + 42  # 82
    assert agg["days_recorded"] == 3
    assert agg["provenance"] == "REAL"
