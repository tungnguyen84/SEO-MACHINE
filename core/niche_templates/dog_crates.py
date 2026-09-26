"""
Explicit Template: Dog Crates, Travel Kennels & Vehicle Fitment
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

def get_dog_crate_template() -> NicheSpec:
    return NicheSpec(
        niche_id="dog_crates",
        niche_name="Dog Crates, Travel Kennels & Vehicle Fitment",
        niche_description="Independent canine travel authority comparing crate dimensions against dog breed sizing and vehicle cargo spaces.",
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
        entity_types=["DogCrate", "DogBreed", "VehicleCargoArea"],
        attributes={
            "DogCrate": [
                AttributeSpec(key="internal_length_inches", display_name="Internal Floor Length", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="internal_width_inches", display_name="Internal Floor Width", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="internal_height_inches", display_name="Internal Height", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="external_height_inches", display_name="Exterior Height", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="crate_weight_lbs", display_name="Tare Crate Weight", data_type=DataType.FLOAT, unit="lbs", required=False, critical=False, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="max_dog_weight_lbs", display_name="Max Dog Weight Rating", data_type=DataType.FLOAT, unit="lbs", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
            ],
            "DogBreed": [
                AttributeSpec(key="avg_length_snout_to_tail_inches", display_name="Average Body Length", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION),
                AttributeSpec(key="avg_withers_height_inches", display_name="Average Standing Height", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION),
                AttributeSpec(key="avg_adult_weight_lbs", display_name="Average Adult Weight", data_type=DataType.FLOAT, unit="lbs", required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION),
            ],
            "VehicleCargoArea": [
                AttributeSpec(key="cargo_opening_height_inches", display_name="Cargo Opening Height", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
                AttributeSpec(key="cargo_floor_depth_inches", display_name="Cargo Floor Depth", data_type=DataType.DIMENSION, unit="in", required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER),
            ]
        },
        relationships=[
            RelationshipSpec(source_entity="DogCrate", relationship="suitable_for", target_entity="DogBreed", description="Evaluates whether crate provides adequate turnaround space for breed."),
            RelationshipSpec(source_entity="DogCrate", relationship="fits_inside", target_entity="VehicleCargoArea", description="Evaluates physical enclosure clearance into vehicle trunk.")
        ],
        calculations=[
            CalculationSpec(
                id="dog_crate_min_length_needed",
                name="AKC Crate Minimum Length Rule",
                formula="avg_length_snout_to_tail_inches + 4.0",
                output_unit="in",
                output_description="AKC recommended minimum crate floor length (dog body length plus 4 inches).",
                required_variables=["avg_length_snout_to_tail_inches"],
                provenance_type="OFFICIAL_STANDARD",
                source_ids=["AKC Crate Guidelines"],
                confidence=0.95,
                assumptions=["4 inch clearance for normal turning comfort"]
            ),
            CalculationSpec(
                id="dog_crate_min_height_needed",
                name="AKC Crate Minimum Height Rule",
                formula="avg_withers_height_inches + 3.0",
                output_unit="in",
                output_description="AKC recommended minimum crate standing height (dog withers height plus 3 inches).",
                required_variables=["avg_withers_height_inches"],
                provenance_type="OFFICIAL_STANDARD",
                source_ids=["AKC Crate Guidelines"],
                confidence=0.95,
                assumptions=["3 inch standing clearance above head"]
            )
        ],
        compatibility_rules=[
            CompatibilityRuleSpec(
                rule_id="crate_dog_size_suitability",
                name="Dog Crate to Breed Sizing Fit",
                subject_type="DogCrate",
                target_type="DogBreed",
                conditions=[
                    ConditionSpec(
                        subject_attribute="internal_length_inches",
                        operator=">=",
                        target_attribute="avg_length_snout_to_tail_inches",
                        tolerance=-4.0  # internal length >= dog length + 4
                    ),
                    ConditionSpec(
                        subject_attribute="max_dog_weight_lbs",
                        operator=">=",
                        target_attribute="avg_adult_weight_lbs",
                        tolerance=0.0
                    )
                ],
                pass_verdict="PASS",
                pass_status="EXACT_FIT",
                fail_verdict="FAIL",
                fail_status="TOO_SMALL",
                explanation_pass="Crate allows adult dog to comfortably stand up, turn around, and lie down.",
                explanation_fail="Crate does not provide required ergonomic turnaround space or exceeds weight rating.",
                provenance_type="OFFICIAL_STANDARD",
                confidence=0.95
            )
        ],
        source_policies=[
            SourcePolicySpec(source_type=SourceType.MANUFACTURER, priority=1, allowed_for_critical_facts=True, freshness_interval_days=730),
            SourcePolicySpec(source_type=SourceType.DOCUMENTATION, priority=2, allowed_for_critical_facts=True, freshness_interval_days=730),
            SourcePolicySpec(source_type=SourceType.RETAILER, priority=4, allowed_for_critical_facts=False, freshness_interval_days=7)
        ],
        page_types=[
            PageTypeSpec(page_type_id="compatibility", name="Dog Breed Crate Size Guide", primary_intent=IntentType.COMPATIBILITY, required_entities=["DogCrate", "DogBreed"], required_attributes=["internal_length_inches", "avg_length_snout_to_tail_inches"]),
            PageTypeSpec(page_type_id="comparison", name="Crate Comparison by Dog Weight", primary_intent=IntentType.COMPARISON, required_entities=["DogCrate"], required_attributes=["max_dog_weight_lbs", "internal_length_inches"])
        ],
        intent_taxonomy={
            "COMPATIBILITY_GUIDE": ["crate size for", "what size crate for", "fits in car", "kennel size for"],
            "VS_COMPARISON": [" vs ", " versus ", " compare "]
        },
        cluster_differentiators=["breed", "crate", "size", "weight", "kennel", "inches"]
    )
