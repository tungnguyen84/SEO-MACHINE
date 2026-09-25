"""
Tests for Database Migration & Schema Compatibility (PostgreSQL + SQLite)
Priority 1 Verification
"""
import pytest
from alembic.config import Config
from alembic import command
from core.database import (
    init_db, create_project, get_project, get_connection
)
from core.entities.entity_manager import EntityManager
from core.planner.page_planner import PagePlanner

def test_postgresql_migration_ddl_generation():
    """
    Test that Alembic can compile the entire 001_initial migration into
    valid PostgreSQL DDL without errors.
    """
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", "postgresql://user:pass@localhost:5432/openseo")
    
    # Offline upgrade generates PostgreSQL DDL
    try:
        command.upgrade(cfg, "001_initial", sql=True)
        success = True
    except Exception as e:
        success = False
        pytest.fail(f"PostgreSQL migration compilation failed: {e}")
    assert success is True

def test_sqlite_migration_upgrade_and_data_roundtrip():
    """
    Test that database starts, creates project, entity, source, evidence, page_plan,
    and reads back all models successfully.
    """
    init_db()

    # 1. Project
    proj = create_project(
        project_id="test_proj_us_camping",
        name="US Vehicle Camping Pilot",
        niche="vehicle_camping",
        target_country="US",
        config={"pilot": True, "currency": "USD"}
    )
    assert proj["id"] == "test_proj_us_camping"
    fetched_proj = get_project("test_proj_us_camping")
    assert fetched_proj is not None
    assert fetched_proj["niche"] == "vehicle_camping"
    assert fetched_proj["config"]["pilot"] is True

    # 2. Entity
    EntityManager.create_or_update_entity(
        entity_id="test_car_subaru",
        entity_type="vehicle",
        brand="Subaru",
        model="Outback 2025"
    )
    ent = EntityManager.get_entity("test_car_subaru")
    assert ent is not None
    assert ent["brand"] == "Subaru"

    # 3. Source & Evidence
    source_id = EntityManager.register_manual_source(
        entity_id="test_car_subaru",
        url="https://www.subaru.com/vehicles/outback/specs.html",
        document_title="2025 Subaru Outback Specifications"
    )
    assert source_id > 0

    EntityManager.add_evidence_claim(
        entity_id="test_car_subaru",
        source_id=source_id,
        attribute_key="cargo_length_inches",
        extracted_value="75.0 in",
        raw_quote="Maximum cargo length with seats folded: 75.0 inches.",
        page_number=14
    )

    claims = EntityManager.get_evidence_claims("test_car_subaru")
    assert len(claims) >= 1
    assert claims[0]["extracted_value"] == "75.0 in"

    # 4. Page Plan
    plan_id = PagePlanner.create_page_plan(
        target_keyword="subaru outback 2025 camping fridge setup",
        intent_type="commercial",
        target_entity_ids=["test_car_subaru"],
        factual_brief={"priority": "high", "niche": "vehicle_camping"}
    )
    assert plan_id > 0

    # Read back plan
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM page_plans WHERE id = ?", (plan_id,))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row["target_keyword"] == "subaru outback 2025 camping fridge setup"
