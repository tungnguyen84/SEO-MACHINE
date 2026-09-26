"""
Explicit Template: Home Dehumidifiers & Moisture Control
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

def get_dehumidifier_template() -> NicheSpec:
    return NicheSpec(
        niche_id="home_dehumidifiers",
        niche_name="Home Dehumidifiers & Moisture Control",
        niche_description="US residential dehumidifier authority matching room dimensions, humidity levels, cold basement conditions, drainage mechanisms, and annual energy costs.",
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
        entity_types=["Dehumidifier", "Room", "Basement"],
        attributes={
            "Dehumidifier": [
                AttributeSpec(key="capacity_pints_day", display_name="DOE Removal Capacity", data_type=DataType.FLOAT, unit="", required=True, critical=True, preferred_source_type=SourceType.CERTIFICATION),
                AttributeSpec(key="recommended_room_sqft", display_name="Recommended Room Area", data_type=DataType.DIMENSION, unit="sqft", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="power_consumption_watts", display_name="Rated Power Draw", data_type=DataType.POWER, unit="W", required=True, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="energy_factor_l_kwh", display_name="Integrated Energy Factor (IEF)", data_type=DataType.FLOAT, unit="", required=True, critical=True, preferred_source_type=SourceType.CERTIFICATION),
                AttributeSpec(key="energy_star_certified", display_name="Energy Star Status", data_type=DataType.BOOLEAN, unit="", required=True, critical=False, preferred_source_type=SourceType.CERTIFICATION),
                AttributeSpec(key="drainage_method", display_name="Drainage & Continuous Drain Options", data_type=DataType.STRING, unit="", required=True, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="has_internal_pump", display_name="Internal Condensate Pump", data_type=DataType.BOOLEAN, unit="", required=True, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="water_tank_capacity_pints", display_name="Water Tank Capacity", data_type=DataType.FLOAT, unit="", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="min_operating_temp_f", display_name="Operating Temperature Range", data_type=DataType.FLOAT, unit="", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="auto_defrost", display_name="Auto Defrost for Basements", data_type=DataType.BOOLEAN, unit="", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="noise_level_db", display_name="Operating Noise Level", data_type=DataType.FLOAT, unit="", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="washable_filter", display_name="Washable Air Filter Included", data_type=DataType.BOOLEAN, unit="", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="retail_price_usd", display_name="Retail Price", data_type=DataType.MONEY, unit="USD", required=False, critical=False, preferred_source_type=SourceType.RETAILER),
            ],
            "Room": [
                AttributeSpec(key="area_sqft", display_name="Room Floor Area", data_type=DataType.DIMENSION, unit="sqft", required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION),
                AttributeSpec(key="humidity_level", display_name="Dampness & Relative Humidity Level", data_type=DataType.STRING, unit="", required=True, critical=False, preferred_source_type=SourceType.DOCUMENTATION),
                AttributeSpec(key="ceiling_height_ft", display_name="Ceiling Height", data_type=DataType.FLOAT, unit="", required=False, critical=False, preferred_source_type=SourceType.DOCUMENTATION),
            ],
            "Basement": [
                AttributeSpec(key="temperature_f", display_name="Typical Ambient Temperature", data_type=DataType.FLOAT, unit="", required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION),
                AttributeSpec(key="has_floor_drain", display_name="Floor Drain Available", data_type=DataType.BOOLEAN, unit="", required=True, critical=False, preferred_source_type=SourceType.DOCUMENTATION),
            ]
        },
        relationships=[
            RelationshipSpec(source_entity="Dehumidifier", relationship="suitable_for", target_entity="Room", description="Calculated dehumidification capacity matches room square footage and humidity level."),
            RelationshipSpec(source_entity="Dehumidifier", relationship="operates_in", target_entity="Basement", description="Dehumidifier low-temperature defrost and pump support cold basement operation.")
        ],
        calculations=[
            CalculationSpec(
                id="annual_electricity_cost",
                name="Annual Electrical Operating Cost",
                formula="(power_consumption_watts / 1000.0) * hours_per_day * 365.0 * electricity_rate_kwh",
                output_unit="USD",
                output_description="Estimated annual continuous electrical utility cost based on wattage, usage hours, and kWh electricity tariff.",
                required_variables=["power_consumption_watts", "hours_per_day", "electricity_rate_kwh"],
                provenance_type="DERIVED",
                source_ids=[],
                confidence=0.85,
                assumptions=["Operating hours per day and regional electricity rate baseline"]
            ),
            CalculationSpec(
                id="dehumidifier_room_suitability",
                name="Recommended Coverage Capacity Match",
                formula="capacity_pints_day * 50.0",
                output_unit="sqft",
                output_description="AHAM standard estimated maximum coverage area based on pints per 24 hours.",
                required_variables=["capacity_pints_day"],
                provenance_type="MODEL_PROPOSED",
                source_ids=[],
                confidence=0.75,
                assumptions=["Heuristic sizing multiplier based on standard ceiling heights"]
            )
        ],
        compatibility_rules=[
            CompatibilityRuleSpec(
                rule_id="dehumidifier_room_sizing_suitability",
                name="Room Sizing & Moisture Capacity Suitability",
                subject_type="Dehumidifier",
                target_type="Room",
                conditions=[
                    ConditionSpec(
                        subject_attribute="recommended_room_sqft",
                        operator=">=",
                        target_attribute="area_sqft",
                        tolerance=0.0
                    )
                ],
                pass_verdict="PASS",
                pass_status="SUITABLE_SIZE",
                fail_verdict="FAIL",
                fail_status="UNDERTANKED_OR_UNDERPOWERED",
                explanation_pass="Dehumidifier capacity is appropriately sized to maintain 45-50% relative humidity in this room.",
                explanation_fail="Room area exceeds dehumidifier rated capacity; risk of continuous non-stop compressor cycling.",
                provenance_type="MODEL_PROPOSED",
                confidence=0.80
            )
        ],
        source_policies=[
            SourcePolicySpec(source_type=SourceType.CERTIFICATION, priority=1, allowed_for_critical_facts=True, freshness_interval_days=730),
            SourcePolicySpec(source_type=SourceType.MANUFACTURER, priority=2, allowed_for_critical_facts=True, freshness_interval_days=365),
            SourcePolicySpec(source_type=SourceType.DOCUMENTATION, priority=3, allowed_for_critical_facts=True, freshness_interval_days=365),
            SourcePolicySpec(source_type=SourceType.RETAILER, priority=4, allowed_for_critical_facts=False, freshness_interval_days=7)
        ],
        page_types=[
            PageTypeSpec(page_type_id="suitability", name="Room Sizing & Moisture Capacity Guide", primary_intent=IntentType.COMPATIBILITY, required_entities=["Dehumidifier", "Room"], required_attributes=["recommended_room_sqft", "capacity_pints_day"]),
            PageTypeSpec(page_type_id="calculator", name="Annual Running Cost & Electricity Calculator", primary_intent=IntentType.UTILITY, required_entities=["Dehumidifier"], required_attributes=["power_consumption_watts"]),
            PageTypeSpec(page_type_id="comparison", name="Basement Dehumidifiers with Pump Comparison", primary_intent=IntentType.COMPARISON, required_entities=["Dehumidifier", "Basement"], required_attributes=["capacity_pints_day", "min_operating_temp_f"]),
            PageTypeSpec(page_type_id="hub", name="Home Humidity & Dehumidifier Sizing Hub", primary_intent=IntentType.INFORMATIONAL, required_entities=["Dehumidifier", "Room", "Basement"], required_attributes=["capacity_pints_day", "recommended_room_sqft"]),
            PageTypeSpec(page_type_id="troubleshooting", name="Cold Basement & Frost Problem Solutions", primary_intent=IntentType.INFORMATIONAL, required_entities=["Dehumidifier", "Basement"], required_attributes=["min_operating_temp_f", "auto_defrost"])
        ],
        intent_taxonomy={
            "SIZING_SUITABILITY": ["what size dehumidifier for", "dehumidifier for sq ft", "pints needed for", "sizing chart"],
            "BASEMENT_DRAINAGE": ["basement dehumidifier with pump", "continuous drain", "cold basement", "auto defrost"],
            "RUNNING_COST": ["how much electricity does a dehumidifier use", "running cost per month", "energy star dehumidifier"],
            "VS_COMPARISON": [" vs ", " versus ", " compare "]
        },
        cluster_differentiators=["pints", "basement", "pump", "sqft", "energy star", "continuous drain", "cost", "humidity", "noise"]
    )
