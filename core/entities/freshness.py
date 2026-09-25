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
    STATIC = "STATIC"               # Vehicle OEM dimensions, cargo volume, hatch height, roof ratings, 12V fuse limits.
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


# Authoritative Attribute Dictionary with Tailored Freshness Policies
ATTRIBUTE_REGISTRY: Dict[str, AttributeDefinition] = {
    # -------------------------------------------------------------
    # 1. STATIC / MODEL-YEAR VEHICLE ATTRIBUTES
    # (Do NOT expire by time alone. Valid for vehicle model lifecycle)
    # -------------------------------------------------------------
    "cargo_dimensions_length_inches": AttributeDefinition(
        attr_key="cargo_dimensions_length_inches",
        display_name="Cargo Floor Length (Seats Folded)",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Length from rear hatch to front seats folded flat."
    ),
    "cargo_dimensions_width_inches": AttributeDefinition(
        attr_key="cargo_dimensions_width_inches",
        display_name="Cargo Width (Max)",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Widest cargo floor dimension."
    ),
    "cargo_dimensions_height_inches": AttributeDefinition(
        attr_key="cargo_dimensions_height_inches",
        display_name="Interior Cargo Height",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Vertical cargo clearance from floor to headliner."
    ),
    "rear_hatch_height_inches": AttributeDefinition(
        attr_key="rear_hatch_height_inches",
        display_name="Rear Hatch Opening Height",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Vertical opening clearance at the rear tailgate sill."
    ),
    "rear_hatch_width_inches": AttributeDefinition(
        attr_key="rear_hatch_width_inches",
        display_name="Rear Hatch Opening Width",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Narrowest horizontal clearance of the tailgate opening."
    ),
    "wheel_well_width_inches": AttributeDefinition(
        attr_key="wheel_well_width_inches",
        display_name="Width Between Wheel Arches",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Minimum floor width between interior wheel arches."
    ),
    "cargo_volume_cu_ft": AttributeDefinition(
        attr_key="cargo_volume_cu_ft",
        display_name="Cargo Volume Behind Row 1",
        data_type="numeric",
        default_unit="cu ft",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Total rear volume per EPA / SAE measurement."
    ),
    "roof_rail_weight_limit_dynamic_lbs": AttributeDefinition(
        attr_key="roof_rail_weight_limit_dynamic_lbs",
        display_name="Dynamic Roof Rail Load Limit",
        data_type="numeric",
        default_unit="lbs",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Maximum permissible roof weight while vehicle is in motion."
    ),
    "roof_rail_weight_limit_static_lbs": AttributeDefinition(
        attr_key="roof_rail_weight_limit_static_lbs",
        display_name="Static Roof Rail Load Limit",
        data_type="numeric",
        default_unit="lbs",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Maximum rooftop tent / occupant weight when parked."
    ),
    "auxiliary_socket_max_amps": AttributeDefinition(
        attr_key="auxiliary_socket_max_amps",
        display_name="12V Rear Cargo Socket Fuse Limit",
        data_type="numeric",
        default_unit="A",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Maximum continuous current draw from OEM rear 12V DC outlet."
    ),
    "ground_clearance_inches": AttributeDefinition(
        attr_key="ground_clearance_inches",
        display_name="OEM Ground Clearance",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.STATIC,
        refresh_interval_days=730,
        invalidate_on_source_change=True,
        description="Lowest chassis/diff clearance to ground."
    ),

    # -------------------------------------------------------------
    # 2. SEMI-DYNAMIC APPLIANCE / PRODUCT SPECS
    # (Verified periodically: 180 - 365 days)
    # -------------------------------------------------------------
    "dimensions_height_inches": AttributeDefinition(
        attr_key="dimensions_height_inches",
        display_name="Exterior Height (with handles/feet)",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Maximum overall height of appliance."
    ),
    "dimensions_length_inches": AttributeDefinition(
        attr_key="dimensions_length_inches",
        display_name="Exterior Length",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Maximum exterior length."
    ),
    "dimensions_width_inches": AttributeDefinition(
        attr_key="dimensions_width_inches",
        display_name="Exterior Width",
        data_type="numeric",
        default_unit="in",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Maximum exterior width."
    ),
    "power_draw_watts": AttributeDefinition(
        attr_key="power_draw_watts",
        display_name="Compressor Rated Power",
        data_type="numeric",
        default_unit="W",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=180,
        invalidate_on_source_change=True,
        description="Nominal continuous power consumption while compressor runs."
    ),
    "rated_capacity_liters": AttributeDefinition(
        attr_key="rated_capacity_liters",
        display_name="Internal Storage Volume",
        data_type="numeric",
        default_unit="L",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=365,
        invalidate_on_source_change=True,
        description="Usable internal cooler volume in liters."
    ),
    "usable_capacity_wh": AttributeDefinition(
        attr_key="usable_capacity_wh",
        display_name="Battery Storage Capacity",
        data_type="numeric",
        default_unit="Wh",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=365,
        invalidate_on_source_change=True,
        description="Rated energy storage in Watt-hours."
    ),
    "compressor_cutout_voltage": AttributeDefinition(
        attr_key="compressor_cutout_voltage",
        display_name="Low Voltage Cutoff Level",
        data_type="numeric",
        default_unit="V",
        freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
        refresh_interval_days=365,
        invalidate_on_source_change=True,
        description="High/Medium/Low battery protection cutoff voltage."
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
    def get_attribute_definition(cls, attr_key: str) -> AttributeDefinition:
        """Retrieves known attribute definition or returns a default semi-dynamic one."""
        return ATTRIBUTE_REGISTRY.get(
            attr_key,
            AttributeDefinition(
                attr_key=attr_key,
                display_name=attr_key.replace("_", " ").title(),
                freshness_policy=FreshnessPolicy.SEMI_DYNAMIC,
                refresh_interval_days=180,
                invalidate_on_source_change=True
            )
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
            return True, f"Vehicle model-year generation updated for static spec '{attr_key}'.", policy

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

