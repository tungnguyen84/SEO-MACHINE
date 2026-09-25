"""
Unit tests for SERP snapshot analysis, opportunity scoring,
and template diversity checking.
"""
from core.research.serp_analyzer import SerpAnalyzer, CompetitorType, EvidenceReadiness, VolumeProvenance
from core.publisher.first_5_pipeline import TemplateSimilarityAuditor, EditorialQualityAuditor


def test_serp_competitor_classification():
    """Verifies that forums, reddit, manufacturers, and retailers are accurately categorized."""
    assert SerpAnalyzer.classify_competitor("https://subaruoutback.org/thread/1", "subaruoutback.org", "Title") == CompetitorType.FORUM
    assert SerpAnalyzer.classify_competitor("https://reddit.com/r/subaru", "reddit.com", "Title") == CompetitorType.REDDIT
    assert SerpAnalyzer.classify_competitor("https://subaru.com/specs", "subaru.com", "Title") == CompetitorType.MANUFACTURER
    assert SerpAnalyzer.classify_competitor("https://amazon.com/dp/123", "amazon.com", "Listing") == CompetitorType.RETAILER
    assert SerpAnalyzer.classify_competitor("https://caranddriver.com/review", "caranddriver.com", "Review") == CompetitorType.EDITORIAL


def test_serp_opportunity_score_breakdown():
    """
    Opportunity score is explainable, strictly calibrated, and does not promise guaranteed rankings.
    """
    score, breakdown = SerpAnalyzer.calculate_serp_opportunity_score(
        intent_gap=90.0,
        weak_result_presence=85.0,
        forum_dependency=95.0,
        exact_answer_gap=90.0,
        data_gap=85.0,
        compatibility_gap=90.0,
        authority_barrier=20.0,
        content_freshness_gap=70.0,
        unique_utility_potential=95.0,
        commercial_intent=90.0
    )
    assert 85.0 <= score <= 96.0
    assert "data_gap" in breakdown
    assert "forum_dependency" in breakdown
    assert breakdown["final_opportunity_score"] == score


def test_serp_snapshot_persistence():
    """Verifies saving and retrieving a snapshot with gap analysis."""
    query = "test outback camping query"
    top_results = [{"rank": 1, "domain": "subaruoutback.org", "title": "Test Forum", "url": "https://test.com"}]
    gap = {"has_exact_answer": False, "openseo_unique_data": "75.0 in length"}
    score = 82.5
    breakdown = {"data_gap": 80.0, "final_opportunity_score": 82.5}

    snap_id = SerpAnalyzer.save_serp_snapshot(
        query=query,
        top_results=top_results,
        serp_gap=gap,
        opportunity_score=score,
        opportunity_breakdown=breakdown,
        evidence_readiness=EvidenceReadiness.READY,
        volume_label=VolumeProvenance.ESTIMATED,
        estimated_volume=500
    )
    assert snap_id > 0

    retrieved = SerpAnalyzer.get_latest_snapshot(query)
    assert retrieved is not None
    assert retrieved["query"] == query
    assert retrieved["opportunity_score"] == 82.5
    assert retrieved["evidence_readiness"] == "READY"
    assert retrieved["volume_label"] == "ESTIMATED"


def test_template_similarity_auditor():
    """
    Verifies that distinct articles pass the diversity audit,
    while templated Mad-Libs clones are rejected.
    """
    text_diverse_1 = "The Subaru Outback rear cargo area provides seventy-five inches of flat length when seats are folded."
    text_diverse_2 = "Electrical power stations using lithium iron phosphate batteries supply twelve-volt compressor cooling without vehicle alternator drain."

    # Distinct articles
    sim_diverse = TemplateSimilarityAuditor.calculate_jaccard_similarity(text_diverse_1, text_diverse_2)
    assert sim_diverse < 0.20

    # Templated clones
    text_clone_1 = "The best fridge for Subaru Outback is the ICECO VL45 because it has great clearance and runs on 12V power."
    text_clone_2 = "The best fridge for Subaru Forester is the ICECO VL45 because it has great clearance and runs on 12V power."
    sim_clone = TemplateSimilarityAuditor.calculate_jaccard_similarity(text_clone_1, text_clone_2)
    assert sim_clone > 0.70
