"""
Page Planner Clustering & Cannibalization Prevention Tests (Section 9)
Verifies that near-identical keywords do NOT spawn 5 separate spam articles.
Enforces deliberate intent clustering: CREATE, MERGE, UPDATE_EXISTING, NOINDEX, SKIP.
"""
import pytest
from core.planner.page_planner import PagePlanner

def test_page_planner_5_duplicate_keywords_cluster():
    """
    Test 5 near-identical keywords:
    - 'best fridge for Subaru Outback'
    - 'best Subaru Outback fridge'
    - 'Outback camping fridge'
    - 'fridge for Outback camping'
    - 'best 12v fridge Outback'
    Expected: Exactly 1 CREATE (Pillar), others MERGED or SKIPPED. Total new pages = 1.
    """
    keywords = [
        "best fridge for Subaru Outback",
        "best Subaru Outback fridge",
        "Outback camping fridge",
        "fridge for Outback camping",
        "best 12v fridge Outback"
    ]
    
    plan_decisions = PagePlanner.cluster_keywords(keywords)
    assert len(plan_decisions) == 5
    
    # 1. Count actions
    create_actions = [p for p in plan_decisions if p["action"] == "CREATE"]
    merge_actions = [p for p in plan_decisions if p["action"] == "MERGE"]
    skip_actions = [p for p in plan_decisions if p["action"] == "SKIP"]
    
    # Exactly ONE article must be created
    assert len(create_actions) == 1, f"Expected exactly 1 CREATE, got {len(create_actions)}"
    assert create_actions[0]["keyword"] == "best fridge for Subaru Outback"
    
    # The remaining 4 must be merged or skipped
    non_create_count = len(merge_actions) + len(skip_actions)
    assert non_create_count == 4, f"All 4 near-duplicate keywords must be MERGED or SKIPPED to stop cannibalization. Got {non_create_count}"
    
    # All share the same primary cluster
    cluster_id = create_actions[0]["cluster_id"]
    for p in plan_decisions:
        assert p["cluster_id"] == cluster_id

def test_page_planner_detects_existing_page_for_update():
    """
    When a keyword targets a topic where an existing page already ranks,
    the planner must recommend UPDATE_EXISTING, never creating a duplicate competing page.
    """
    existing_pages = ["2025 Subaru Outback Camping Fridge Guide"]
    new_candidate_keywords = ["camping fridge subaru outback 2025"]
    
    plan = PagePlanner.cluster_keywords(new_candidate_keywords, existing_planned_keywords=existing_pages)
    assert len(plan) == 1
    assert plan[0]["action"] == "UPDATE_EXISTING"
    assert "2025 Subaru Outback Camping Fridge Guide" in plan[0]["target_page"]
    assert "Update existing page" in plan[0]["reason"]
