"""
Freshness Policy and Attribute Expiration Engine.
Replaces global blanket expiration (e.g. 90 days) with attribute-specific
and source-specific freshness lifecycles.
"""
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class FreshnessPolicy(str, Enum):
    """
    Defines how rapidly an attribute or data point decays.
    """
    STATIC = "STATIC"               # Fixed OEM dimensions, structural volume, model ratings, fuse limits.
                                    # Never decays solely by passage of days. Revalidated only if source hash or model-year changes.
    SEMI_DYNAMIC = "SEMI_DYNAMIC"   # Manufacturer product specs, weight, exterior dimensions, rated wattage.
                                    # Periodic verification (e.g., 180 - 365 days).
    DYNAMIC = "DYNAMIC"             # Merchant offers, prices, coupons, stock availability.
                                    # High-frequency verification (e.g., 1 - 7 days).
    SEARCH_DATA = "SEARCH_DATA"     # SERP snapshots, competitor positioning, SERP features.
                                    # Research cycle verification (e.g., 30 days).
    PERFORMANCE_DATA = "PERFORMANCE_DATA" # GSC impressions, clicks, average position.
                                          # Daily sync (1 day).


class AttributeDefinition(BaseModel):
    """
    Defines the specification and freshness lifecycle of an entity attribute.
    """
    attr_key: str
    display_name: str
    data_type: str = "numeric"  # numeric, text, boolean, json
    default_unit: Optional[str] = None
    freshness_policy: FreshnessPolicy = FreshnessPolicy.SEMI_DYNAMIC
    refresh_interval_days: int = 180
    invalidate_on_source_change: bool = True
    description: Optional[str] = None


# Authoritative Attribute Dictionary with Universal Core Freshness Policies
# (Domain-specific attributes are registered dynamically via Niche Adapters)
ATTRIBUTE_REGISTRY: Dict[str, AttributeDefinition] = {
    # -------------------------------------------------------------
    # 1. CORE DIMENSIONAL & PHYSICAL ATTRIBUTES
    # -------------------------------------------------------------
    "dimensions_height_inches": AttributeDefinition(
        attr_key="dimensions_height_inches",
        display_name="Exterior Height",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Maximum overall height."
    ),
    "dimensions_length_inches": AttributeDefinition(
        attr_key="dimensions_length_inches",
        display_name="Exterior Length",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Maximum overall length."
    ),
    "dimensions_width_inches": AttributeDefinition(
        attr_key="dimensions_width_inches",
        display_name="Exterior Width",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Maximum overall width."
    ),
    "weight_lbs": AttributeDefinition(
        attr_key="weight_lbs",
        display_name="Unit Weight",
        data_type="numeric",
        default_unit="lbs",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Gross net weight of unit."
    ),

    # -------------------------------------------------------------
    # 3. DYNAMIC COMMERCE / OFFER DATA
    # (Refresh frequent: 1 - 7 days)
    # -------------------------------------------------------------
    "current_price": AttributeDefinition(
        attr_key="current_price",
        display_name="Merchant Current Price",
        data_type="numeric",
        default_unit="USD",
        freshness_policy=FreshnessPolicy.DYNAMIC,
        refresh_interval_days=3,
        invalidate_on_source_change=True,
        description="Real-time retail price at merchant."
    ),
    "in_stock": AttributeDefinition(
        attr_key="in_stock",
        display_name="Inventory In Stock",
        data_type="boolean",
        freshness_policy=FreshnessPolicy.DYNAMIC,
        refresh_interval_days=1,
        invalidate_on_source_change=True,
        description="Live stock status."
    ),

    # -------------------------------------------------------------
    # 4. SEARCH DATA
    # (Refresh research cycle: 30 days)
    # -------------------------------------------------------------
    "serp_snapshot": AttributeDefinition(
        attr_key="serp_snapshot",
        display_name="SERP Competitor Composition",
        data_type="json",
        freshness_policy=FreshnessPolicy.SEARCH_DATA,
        refresh_interval_days=30,
        invalidate_on_source_change=False,
        description="Snapshot of top 10 search results and features."
    ),

    # -------------------------------------------------------------
    # 5. PERFORMANCE DATA
    # (Daily sync: 1 day)
    # -------------------------------------------------------------
    "gsc_metrics": AttributeDefinition(
        attr_key="gsc_metrics",
        display_name="Search Console Daily Telemetry",
        data_type="json",
        freshness_policy=FreshnessPolicy.PERFORMANCE_DATA,
        refresh_interval_days=1,
        invalidate_on_source_change=False,
        description="Impressions, clicks, CTR, and position from GSC."
    ),
}


class FreshnessEngine:
    """
    Evaluates attribute freshness based on fine-grained lifecycle policies.
    """

    @classmethod
    def register_attribute_definition(cls, defn: AttributeDefinition):
        ATTRIBUTE_REGISTRY[defn.attr_key] = defn

    @classmethod
    def register_attribute_definitions(cls, defns: List[AttributeDefinition]):
        for d in defns:
            ATTRIBUTE_REGISTRY[d.attr_key] = d

    @classmethod
    def get_attribute_definition(cls, attr_key: str) -> AttributeDefinition:
        """Retrieves known attribute definition, checks registered adapters, or returns a default semi-dynamic one."""
        if attr_key in ATTRIBUTE_REGISTRY:
            return ATTRIBUTE_REGISTRY[attr_key]

        # Check registered adapters dynamically
        try:
            from core.niche_adapters.registry import NicheRegistry
            for adapter in NicheRegistry.get_all():
                raw_defs = getattr(adapter, "attribute_definitions", [])
                if isinstance(raw_defs, dict):
                    all_defs = [item for sublist in raw_defs.values() for item in sublist]
                else:
                    all_defs = raw_defs
                for defn in all_defs:
                    key = getattr(defn, "attr_key", None) or getattr(defn, "key", None)
                    if key == attr_key:
                        fp = getattr(defn, "freshness_policy", None)
                        policy = FreshnessPolicy.STATIC if "STATIC" in str(fp) else FreshnessPolicy.SEMI_DYNAMIC
                        unit = getattr(defn, "default_unit", None) or getattr(defn, "unit_type", None)
                        conv = AttributeDefinition(
                            attr_key=key,
                            display_name=getattr(defn, "display_name", key.replace("_", " ").title()),
                            data_type=getattr(defn, "data_type", "numeric"),
                            default_unit=unit,
                            freshness_policy=policy,
                            refresh_interval_days=getattr(defn, "refresh_interval_days", 730 if policy == FreshnessPolicy.STATIC else 180),
                            invalidate_on_source_change=getattr(defn, "invalidate_on_source_change", True)
                        )
                        ATTRIBUTE_REGISTRY[attr_key] = conv
                        return conv
        except Exception:
            pass

        return AttributeDefinition(
            attr_key=attr_key,
            display_name=attr_key.replace("_", " ").title(),
            freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
            refresh_interval_days=180,
            invalidate_on_source_change=True
        )

    @classmethod
    def evaluate_staleness(
        cls,
        attr_key: str,
        last_verified_at: Optional[str] = None,
        source_hash_changed: bool = False,
        model_year_changed: bool = False,
        now: Optional[datetime] = None
    ) -> Tuple[bool, str, FreshnessPolicy]:
        """
        Determines if an attribute value is stale based on its specific FreshnessPolicy.

        Returns:
            Tuple[is_stale (bool), reason (str), policy (FreshnessPolicy)]
        """
        defn = cls.get_attribute_definition(attr_key)
        policy = defn.freshness_policy

        # Rule 1: Immediate invalidation on source hash change or model year update
        if defn.invalidate_on_source_change and source_hash_changed:
            return True, f"Source document content hash changed for '{attr_key}'.", policy

        if model_year_changed and policy == FreshnessPolicy.STATIC:
            return True, f"Model-year generation updated for static spec '{attr_key}'.", policy

        # Rule 2: STATIC attributes DO NOT expire by time alone if source is unmodified
        if policy == FreshnessPolicy.STATIC:
            return False, f"Static model-year spec '{attr_key}' remains authoritative (unmodified source).", policy

        # Rule 3: Time-based decay for SEMI_DYNAMIC, DYNAMIC, SEARCH_DATA, PERFORMANCE_DATA
        if not last_verified_at:
            return True, f"Attribute '{attr_key}' has never been verified (no timestamp).", policy

        try:
            # Parse ISO timestamp
            ts_str = last_verified_at.replace("Z", "+00:00")
            verified_dt = datetime.fromisoformat(ts_str)
            if verified_dt.tzinfo is None:
                verified_dt = verified_dt.replace(tzinfo=timezone.utc)
            
            curr_time = now or datetime.now(timezone.utc)
            age_days = (curr_time - verified_dt).total_seconds() / 86400.0

            if age_days > defn.refresh_interval_days:
                return (
                    True,
                    f"Attribute '{attr_key}' aged {age_days:.1f} days, exceeding {policy.value} threshold of {defn.refresh_interval_days} days.",
                    policy
                )
            else:
                return (
                    False,
                    f"Attribute '{attr_key}' is fresh ({age_days:.1f} days / {defn.refresh_interval_days} allowed).",
                    policy
                )
        except Exception as e:
            # On parse error, fall back safely
            return False, f"Timestamp parsing failed ({e}); default to fresh if source valid.", policy

    @classmethod
    def evaluate_evidence_claims_freshness(
        cls,
        evidence_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Audits a collection of evidence claims used in an article or calculation.
        Flags stale items according to their respective attribute policy.
        """
        stale_items = []
        fresh_items = []
        static_count = 0
        semi_count = 0
        dynamic_count = 0

        for item in evidence_list:
            attr_key = item.get("claim_type") or item.get("attr_key") or "general_spec"
            last_verified = item.get("verified_at") or item.get("retrieved_at")
            source_changed = item.get("source_hash_changed", False)
            model_changed = item.get("model_year_changed", False)

            is_stale, reason, policy = cls.evaluate_staleness(
                attr_key=attr_key,
                last_verified_at=last_verified,
                source_hash_changed=source_changed,
                model_year_changed=model_changed
            )

            if policy == FreshnessPolicy.STATIC:
                static_count += 1
            elif policy == FreshnessPolicy.DYNAMIC:
                dynamic_count += 1
            else:
                semi_count += 1

            record = {
                "attr_key": attr_key,
                "policy": policy.value,
                "is_stale": is_stale,
                "reason": reason
            }
            if is_stale:
                stale_items.append(record)
            else:
                fresh_items.append(record)

        overall_is_stale = len(stale_items) > 0
        return {
            "overall_is_stale": overall_is_stale,
            "stale_count": len(stale_items),
            "fresh_count": len(fresh_items),
            "breakdown": {
                "static_specs": static_count,
                "semi_dynamic_specs": semi_count,
                "dynamic_offers": dynamic_count
            },
            "stale_details": stale_items
        }

    @classmethod
    def seed_attribute_definitions(cls) -> int:
        """Populates the database attribute_definitions table with registered attributes."""
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        count = 0
        for defn in ATTRIBUTE_REGISTRY.values():
            cursor.execute("""
            INSERT INTO attribute_definitions (
                attr_key, display_name, data_type, default_unit, description,
                freshness_policy, refresh_interval_days, invalidate_on_source_change
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(attr_key) DO UPDATE SET
                display_name = excluded.display_name,
                data_type = excluded.data_type,
                default_unit = excluded.default_unit,
                description = excluded.description,
                freshness_policy = excluded.freshness_policy,
                refresh_interval_days = excluded.refresh_interval_days,
                invalidate_on_source_change = excluded.invalidate_on_source_change
            """, (
                defn.attr_key, defn.display_name, defn.data_type, defn.default_unit,
                defn.description, defn.freshness_policy.value, defn.refresh_interval_days,
                1 if defn.invalidate_on_source_change else 0
            ))
            count += 1
        conn.commit()
        conn.close()
        return count

