"""
Unit tests for the Granular Freshness Model.
Verifies that STATIC OEM vehicle dimensions never decay purely by age,
while DYNAMIC prices decay rapidly, and source hash changes trigger invalidation.
"""
from datetime import datetime, timedelta, timezone
from core.entities.freshness import FreshnessEngine, FreshnessPolicy, AttributeDefinition


def test_static_vehicle_dimension_does_not_decay_by_age():
    """
    OEM vehicle dimensions (e.g. cargo floor length, hatch sill opening)
    must NOT decay simply because 91 or 180 days have passed.
    """
    now = datetime.now(timezone.utc)
    old_verified_at = (now - timedelta(days=120)).isoformat()

    is_stale, reason, policy = FreshnessEngine.evaluate_staleness(
        attr_key="cargo_dimensions_length_inches",
        last_verified_at=old_verified_at,
        source_hash_changed=False,
        model_year_changed=False,
        now=now
    )
    assert policy == FreshnessPolicy.STATIC
    assert is_stale is False
    assert "remains authoritative" in reason


def test_static_vehicle_dimension_invalidates_on_source_change():
    """
    If the underlying source document content hash changes,
    even STATIC attributes must immediately revalidate.
    """
    now = datetime.now(timezone.utc)
    recent_verified_at = (now - timedelta(days=5)).isoformat()

    is_stale, reason, policy = FreshnessEngine.evaluate_staleness(
        attr_key="rear_hatch_height_inches",
        last_verified_at=recent_verified_at,
        source_hash_changed=True,
        model_year_changed=False,
        now=now
    )
    assert policy == FreshnessPolicy.STATIC
    assert is_stale is True
    assert "content hash changed" in reason


def test_dynamic_merchant_price_decays_quickly():
    """
    DYNAMIC commercial attributes (prices, deals) must decay within days.
    """
    now = datetime.now(timezone.utc)
    five_days_ago = (now - timedelta(days=5)).isoformat()

    is_stale, reason, policy = FreshnessEngine.evaluate_staleness(
        attr_key="current_price",
        last_verified_at=five_days_ago,
        now=now
    )
    assert policy == FreshnessPolicy.DYNAMIC
    assert is_stale is True
    assert "exceeding DYNAMIC threshold" in reason


def test_semi_dynamic_product_specs():
    """
    SEMI_DYNAMIC manufacturer appliance specs remain fresh within 180 days,
    but decay after 200 days.
    """
    now = datetime.now(timezone.utc)
    fresh_date = (now - timedelta(days=60)).isoformat()
    old_date = (now - timedelta(days=210)).isoformat()

    is_stale_1, _, policy_1 = FreshnessEngine.evaluate_staleness("dimensions_height_inches", last_verified_at=fresh_date, now=now)
    is_stale_2, _, policy_2 = FreshnessEngine.evaluate_staleness("dimensions_height_inches", last_verified_at=old_date, now=now)

    assert policy_1 == FreshnessPolicy.SEMI_DYNAMIC
    assert is_stale_1 is False
    assert is_stale_2 is True


def test_evaluate_evidence_claims_batch_freshness():
    """
    Batch evaluation of evidence claims properly differentiates static vs dynamic.
    """
    claims = [
        {"claim_type": "cargo_dimensions_length_inches", "verified_at": "2025-01-01T00:00:00Z", "source_hash_changed": False},
        {"claim_type": "dimensions_height_inches", "verified_at": "2026-08-01T00:00:00Z", "source_hash_changed": False},
        {"claim_type": "current_price", "verified_at": "2026-09-01T00:00:00Z", "source_hash_changed": False}
    ]
    audit = FreshnessEngine.evaluate_evidence_claims_freshness(claims)
    assert audit["breakdown"]["static_specs"] == 1
    assert audit["breakdown"]["semi_dynamic_specs"] == 1
    assert audit["breakdown"]["dynamic_offers"] == 1
    # current_price from Sept 1 (24+ days ago) is stale
    assert audit["stale_count"] >= 1
