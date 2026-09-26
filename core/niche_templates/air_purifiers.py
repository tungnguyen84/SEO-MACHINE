"""
Explicit Template: Air Purifiers & Filtration Systems
Declarative reference template for testing and preset site creation.
"""
from core.niche_builder.schema import (
    NicheSpec,
    AttributeSpec,
    RelationshipSpec,
    CalculationSpec,
    CompatibilityRuleSpec,
    ConditionSpec,
    SourcePolicySpec,
    PageTypeSpec,
    DataType,
    CapabilityType,
    RiskProfile,
    SourceType,
    IntentType,
)

def get_air_purifier_template() -> NicheSpec:
    return NicheSpec(
        niche_id="air_purifiers",
        niche_name="Home Air Purifiers & Filtration Systems",
        niche_description="US residential air purifier authority focusing on CADR, room size matching, filter replacement compatibility, and continuous running costs.",
        version="1.0.0",
        risk_profile=RiskProfile.LOW,
        capabilities=[
            CapabilityType.COMPATIBILITY,
            CapabilityType.CALCULATION,
            CapabilityType.COMPARISON,
            CapabilityType.PRODUCT_DATABASE,
            CapabilityType.TECHNICAL_SPECS,
            CapabilityType.AFFILIATE_COMMERCE
        ],
        entity_types=["AirPurifier", "Filter", "Room", "Pollutant"],
        attributes={
            "AirPurifier": [
                AttributeSpec(key="cadr_smoke_cfm", display_name="Smoke CADR", data_type=DataType.INTEGER, unit="cfm", required=True, critical=True, preferred_source_type=SourceType.CERTIFICATION),
                AttributeSpec(key="cadr_dust_cfm", display_name="Dust CADR", data_type=DataType.INTEGER, unit="cfm", required=True, critical=True, preferred_source_type=SourceType.CERTIFICATION),
                AttributeSpec(key="cadr_pollen_cfm", display_name="Pollen CADR", data_type=DataType.INTEGER, unit="cfm", required=True, critical=True, preferred_source_type=SourceType.CERTIFICATION),
                AttributeSpec(key="recommended_room_sqft", display_name="Recommended Room Area", data_type=DataType.INTEGER, unit="sqft", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="power_consumption_watts", display_name="Rated Power Draw (Max)", data_type=DataType.POWER, unit="W", required=True, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="noise_level_min_db", display_name="Minimum Noise Level", data_type=DataType.FLOAT, unit="dB", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="noise_level_max_db", display_name="Maximum Noise Level", data_type=DataType.FLOAT, unit="dB", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="filter_slot_diameter_mm", display_name="Filter Slot Diameter", data_type=DataType.DIMENSION, unit="mm", required=False, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="oem_filter_replacement_cost_usd", display_name="OEM Filter Replacement Cost", data_type=DataType.MONEY, unit="USD", required=False, critical=False, preferred_source_type=SourceType.RETAILER),
            ],
            "Filter": [
                AttributeSpec(key="filter_type", display_name="Filtration Standard", data_type=DataType.STRING, unit="", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="lifespan_months", display_name="Expected Filter Lifespan", data_type=DataType.INTEGER, unit="months", required=True, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="filter_diameter_mm", display_name="Filter Outer Diameter", data_type=DataType.DIMENSION, unit="mm", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="replacement_price_usd", display_name="Filter Replacement Price", data_type=DataType.MONEY, unit="USD", required=True, critical=False, preferred_source_type=SourceType.RETAILER),
            ],
            "Room": [
                AttributeSpec(key="area_sqft", display_name="Room Floor Area", data_type=DataType.INTEGER, unit="sqft", required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION),
                AttributeSpec(key="ceiling_height_ft", display_name="Ceiling Height", data_type=DataType.FLOAT, unit="ft", required=False, critical=False, preferred_source_type=SourceType.DOCUMENTATION),
            ],
            "Pollutant": [
                AttributeSpec(key="particle_size_microns", display_name="Target Particle Size", data_type=DataType.FLOAT, unit="microns", required=True, critical=True, preferred_source_type=SourceType.GOVERNMENT),
            ]
        },
        relationships=[
            RelationshipSpec(source_entity="AirPurifier", relationship="uses", target_entity="Filter", description="Air purifier requires compatible filter model."),
            RelationshipSpec(source_entity="AirPurifier", relationship="suitable_for", target_entity="Room", description="Calculated area suitability based on CADR 2/3 rule."),
            RelationshipSpec(source_entity="Filter", relationship="captures", target_entity="Pollutant", description="HEPA filtration effectiveness against specific particle sizes.")
        ],
        calculations=[
            CalculationSpec(
                id="air_purifier_room_suitability",
                name="AHAM CADR 2/3 Room Area Match",
                formula="cadr_smoke_cfm * 1.5",
                output_unit="sqft",
                output_description="Maximum recommended room floor area under AHAM 4.8 air changes per hour standard.",
                required_variables=["cadr_smoke_cfm"],
                provenance_type="OFFICIAL_STANDARD",
                source_ids=["AHAM AC-1-2020"],
                confidence=0.95,
                assumptions=["Standard ceiling height 8 ft, 4.8 ACH standard"]
            ),
            CalculationSpec(
                id="annual_electricity_cost",
                name="Annual Electrical Operating Cost",
                formula="(power_consumption_watts / 1000.0) * hours_per_day * 365.0 * electricity_rate_kwh",
                output_unit="USD",
                output_description="Estimated annual continuous electrical utility cost.",
                required_variables=["power_consumption_watts", "hours_per_day", "electricity_rate_kwh"],
                provenance_type="DERIVED",
                source_ids=[],
                confidence=0.90,
                assumptions=["Continuous operation at specified hours per day"]
            ),
            CalculationSpec(
                id="annual_filter_cost",
                name="Annual Filter Replacement Budget",
                formula="(12.0 / lifespan_months) * replacement_price_usd",
                output_unit="USD",
                output_description="Estimated annual consumables budget based on replacement frequency.",
                required_variables=["lifespan_months", "replacement_price_usd"],
                provenance_type="DERIVED",
                source_ids=[],
                confidence=0.90,
                assumptions=["Filter replacement at manufacturer recommended interval"]
            )
        ],
        compatibility_rules=[
            CompatibilityRuleSpec(
                rule_id="purifier_filter_fit",
                name="Filter Slot Physical Compatibility",
                subject_type="Filter",
                target_type="AirPurifier",
                conditions=[
                    ConditionSpec(
                        subject_attribute="filter_diameter_mm",
                        operator="==",
                        target_attribute="filter_slot_diameter_mm",
                        tolerance=2.0
                    )
                ],
                pass_verdict="PASS",
                pass_status="EXACT_FIT",
                fail_verdict="FAIL",
                fail_status="DOES_NOT_FIT",
                explanation_pass="Filter dimensions fit inside air purifier enclosure.",
                explanation_fail="Filter diameter does not match air purifier slot.",
                provenance_type="MANUFACTURER",
                confidence=0.95
            )
        ],
        source_policies=[
            SourcePolicySpec(source_type=SourceType.CERTIFICATION, priority=1, allowed_for_critical_facts=True, freshness_interval_days=730),
            SourcePolicySpec(source_type=SourceType.MANUFACTURER, priority=2, allowed_for_critical_facts=True, freshness_interval_days=365),
            SourcePolicySpec(source_type=SourceType.RETAILER, priority=4, allowed_for_critical_facts=False, freshness_interval_days=7)
        ],
        page_types=[
            PageTypeSpec(page_type_id="compatibility", name="Filter Replacement Fitment Guide", primary_intent=IntentType.COMPATIBILITY, required_entities=["AirPurifier", "Filter"], required_attributes=["cadr_smoke_cfm", "filter_diameter_mm"]),
            PageTypeSpec(page_type_id="comparison", name="Room Sizing & CADR Comparison", primary_intent=IntentType.COMPARISON, required_entities=["AirPurifier", "Room"], required_attributes=["cadr_smoke_cfm", "recommended_room_sqft"]),
            PageTypeSpec(page_type_id="calculator", name="Annual Running Cost Calculator", primary_intent=IntentType.UTILITY, required_entities=["AirPurifier", "Filter"], required_attributes=["power_consumption_watts", "replacement_price_usd"])
        ],
        intent_taxonomy={
            "COMPATIBILITY_GUIDE": ["replacement filter for", "fits in", "compatible with", "filter size for"],
            "ENGINEERING_RUNTIME": ["cadr for room", "how much electricity does", "air changes per hour", "running cost"],
            "VS_COMPARISON": [" vs ", " versus ", " compare "]
        },
        cluster_differentiators=["hepa", "cadr", "filter", "cost", "smoke", "allergies", "room"]
    )
