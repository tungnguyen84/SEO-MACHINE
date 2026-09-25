"""
Tests for Grounded Writer 2.0, Structured Fact Registry, and Claim Traceability
Priority 2 Verification
"""
import pytest
from core.database import init_db
from core.entities.entity_manager import EntityManager
from core.writer.grounded_context import GroundedContentContext, StructuredFact
from core.writer.grounded_writer import GroundedWriter, ClaimTracer

@pytest.fixture(autouse=True)
def setup_db():
    init_db()

def test_grounded_writer_only_receives_allowed_facts():
    """
    Test that GroundedContentContext only encapsulates authorized facts and calculations.
    """
    EntityManager.create_or_update_entity(
        entity_id="test_car_2025",
        entity_type="vehicle",
        brand="Subaru",
        model="Outback Wilderness"
    )
    src_id = EntityManager.register_manual_source(
        entity_id="test_car_2025",
        url="https://www.subaru.com/specs",
        document_title="Subaru Manual"
    )
    EntityManager.add_verified_attribute(
        entity_id="test_car_2025",
        attr_key="cargo_length_inches",
        raw_value="75.0 in",
        source_id=src_id,
        evidence_quote="75.0 inches length"
    )

    page_plan = {"target_keyword": "subaru outback wilderness camping", "intent_type": "commercial"}
    ctx = GroundedContentContext.build(
        page_plan=page_plan,
        primary_entity_id="test_car_2025",
        calculations=[{"calculation_type": "battery_runtime", "output": {"runtime_hours": 32.5}}]
    )

    assert "test_car_2025.cargo_length_inches" in ctx.facts
    assert ctx.facts["test_car_2025.cargo_length_inches"].value == 75.0
    assert 75.0 in ctx.get_allowed_numbers()
    assert 32.5 in ctx.get_allowed_numbers()
    # Unverified numbers are NOT in allowed set
    assert 99.9 not in ctx.get_allowed_numbers()

def test_claim_to_fact_traceability():
    """
    Test that GroundedWriter generates content where factual metrics are traced
    to verified facts, and unsupported numbers are flagged.
    """
    facts = {
        "car.cargo_length": StructuredFact(
            fact_id="car.cargo_length",
            entity_id="test_car",
            attribute_key="cargo_length_inches",
            value=75.0,
            unit="inches",
            confidence=0.98,
            evidence_ids=[101],
            source_type="oem_manual",
            source_urls=["https://subaru.com/manual.pdf"]
        )
    }

    ctx = GroundedContentContext(
        page_plan={"target_keyword": "subaru outback specs"},
        primary_entity={"brand": "Subaru", "model": "Outback"},
        facts=facts,
        calculations=[{"calculation_type": "runtime", "output": {"hours": 48.0}}],
        allowed_claims=["Only verified numbers permitted"],
        prohibited_claims=["No fake tests"]
    )

    # 1. Valid Grounded Content
    valid_content = "The vehicle offers 75.0 inches cargo length and delivers 48.0 hours runtime."
    trace = ClaimTracer.trace_and_validate(valid_content, ctx)
    assert trace["verified_claims_count"] >= 2
    assert len(trace["unsupported_claims"]) == 0
    assert len(trace["forbidden_claims"]) == 0

    # 2. Content with Hallucinated / Unsupported Number
    fake_content = "The vehicle has 75.0 inches cargo space with 899.0 watts solar power."
    trace_fake = ClaimTracer.trace_and_validate(fake_content, ctx)
    assert len(trace_fake["unsupported_claims"]) >= 1
    assert any("899.0" in c["claim_text"] for c in trace_fake["unsupported_claims"])

    # 3. Content with Forbidden Hands-on Testing Claim (Rule 10)
    forbidden_content = "After we tested in our lab for 40 hours, the cargo measured 75.0 inches."
    trace_forbidden = ClaimTracer.trace_and_validate(forbidden_content, ctx)
    assert len(trace_forbidden["forbidden_claims"]) >= 1
    assert trace_forbidden["forbidden_claims"][0]["validation_status"] == "FORBIDDEN"

def test_unknown_attribute_not_hallucinated():
    """
    Test that an unknown specification remains UNKNOWN and is not invented.
    """
    EntityManager.create_or_update_entity(
        entity_id="test_fridge_unknown",
        entity_type="portable_fridge",
        brand="BrandX",
        model="Cooler90"
    )
    # Register an unknown attribute explicitly
    EntityManager.add_verified_attribute(
        entity_id="test_fridge_unknown",
        attr_key="compressor_db_noise",
        raw_value="UNKNOWN"
    )

    ctx = GroundedContentContext.build(
        page_plan={"target_keyword": "brandx cooler90 noise"},
        primary_entity_id="test_fridge_unknown"
    )

    fact = ctx.facts.get("test_fridge_unknown.compressor_db_noise")
    assert fact is not None
    assert str(fact.value).upper() == "UNKNOWN"

    article = GroundedWriter.write_article(ctx)
    # Check that writer displays UNKNOWN or does not invent a fake dB value like 35 dB
    assert "35 db" not in article["content"].lower()
    assert "UNKNOWN" in article["content"] or "Unknown" in article["content"]
