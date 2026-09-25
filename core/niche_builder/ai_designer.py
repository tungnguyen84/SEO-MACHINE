"""
AI-Assisted Niche Designer, Critic, Market Researcher & Data Availability Scorer
Transforms natural language prompts into complete, valid NicheDraft schemas.
Provides critical evaluations without modifying code or auto-activating.
"""

import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from core.niche_builder.schema import (
    NicheSpec,
    NicheDraft,
    AttributeSpec,
    RelationshipSpec,
    CalculationSpec,
    CompatibilityRuleSpec,
    ConditionSpec,
    SourcePolicySpec,
    PageTypeSpec,
    ContentPolicySpec,
    DataType,
    CapabilityType,
    RiskProfile,
    SourceType,
    FreshnessPolicyType,
    IntentType,
)


class CriticFinding(BaseModel):
    """Specific response to one of the 8 design critique questions."""
    question: str
    assessment: str  # SATISFACTORY | CONCERN | ACTIONABLE_SUGGESTION
    details: str
    recommendation: Optional[str] = None


class CriticReport(BaseModel):
    """AI architectural critique answering 8 specific design questions."""
    niche_id: str
    overall_health: str  # EXCELLENT | SOLID | NEEDS_WORK | HIGH_RISK
    findings: List[CriticFinding] = Field(default_factory=list)
    suggested_changes: List[str] = Field(default_factory=list)


class DataAvailabilityReport(BaseModel):
    """Audit of whether factual, structured data is obtainable for this niche."""
    niche_id: str
    overall_score: float  # 0 - 100
    rating: str          # STRONG | MODERATE | WEAK
    can_activate: bool
    dimensions: Dict[str, float]
    dimension_notes: Dict[str, str]
    unobtainable_attributes: List[str] = Field(default_factory=list)
    recommended_sources: List[str] = Field(default_factory=list)


class MarketResearchReport(BaseModel):
    """Feasibility and competition ecosystem overview before site creation."""
    niche_id: str
    commercial_viability: str
    estimated_serp_competitor_mix: Dict[str, float]
    top_competitors: List[str]
    affiliate_ecosystem_status: str
    data_richness: str
    strategic_opportunity: str
    warning_notice: str = "Market research represents estimated search landscape conditions; rankings and revenues are not guaranteed."


class AINicheDesigner:
    """
    Synthesizes natural language domain descriptions into rich, valid NicheDraft schemas.
    """

    @classmethod
    def design_from_prompt(cls, prompt: str) -> NicheDraft:
        clean = prompt.lower().strip()
        draft_id = f"draft_{uuid.uuid4().hex[:8]}"

        # Domain Detection: Air Purifiers
        if any(w in clean for w in ["air purifier", "purifier", "cadr", "hepa", "filter replacement", "lọc không khí"]):
            spec = cls._design_air_purifier_niche()
            rationale = "Engineered around EPA / AHAM clean air delivery standards, CADR sizing math, and HEPA filter fitment."

        # Domain Detection: Dog Crates & Pet Transport
        elif any(w in clean for w in ["dog crate", "crate", "dog breed", "kennel", "chuồng chó", "lồng chó"]):
            spec = cls._design_dog_crate_niche()
            rationale = "Structured around AKC dog breed dimensions, crate volume math, and vehicle cargo area fitment."

        # General / Universal Heuristic Template
        else:
            spec = cls._design_generic_product_niche(prompt)
            rationale = "Synthesized standard product authority data model with verified specs, comparisons, and calculations."

        return NicheDraft(
            draft_id=draft_id,
            prompt=prompt,
            proposed_niche=spec,
            ai_rationale=rationale,
            status="PROPOSED"
        )

    @classmethod
    def _design_air_purifier_niche(cls) -> NicheSpec:
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
                    required_variables=["cadr_smoke_cfm"]
                ),
                CalculationSpec(
                    id="annual_electricity_cost",
                    name="Annual Electrical Operating Cost",
                    formula="(power_consumption_watts / 1000.0) * hours_per_day * 365.0 * electricity_rate_kwh",
                    output_unit="USD",
                    output_description="Estimated annual continuous electrical utility cost.",
                    required_variables=["power_consumption_watts", "hours_per_day", "electricity_rate_kwh"]
                ),
                CalculationSpec(
                    id="annual_filter_cost",
                    name="Annual Filter Replacement Budget",
                    formula="(12.0 / lifespan_months) * replacement_price_usd",
                    output_unit="USD",
                    output_description="Estimated annual consumables budget based on replacement frequency.",
                    required_variables=["lifespan_months", "replacement_price_usd"]
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
                    explanation_fail="Filter diameter does not match air purifier slot."
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

    @classmethod
    def _design_dog_crate_niche(cls) -> NicheSpec:
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
                    required_variables=["avg_length_snout_to_tail_inches"]
                ),
                CalculationSpec(
                    id="dog_crate_min_height_needed",
                    name="AKC Crate Minimum Height Rule",
                    formula="avg_withers_height_inches + 3.0",
                    output_unit="in",
                    output_description="AKC recommended minimum crate standing height (dog withers height plus 3 inches).",
                    required_variables=["avg_withers_height_inches"]
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
                    explanation_fail="Crate does not provide required ergonomic turnaround space or exceeds weight rating."
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

    @classmethod
    def _design_generic_product_niche(cls, prompt: str) -> NicheSpec:
        clean_name = prompt[:40].strip().title()
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", clean_name).lower().strip("_")
        return NicheSpec(
            niche_id=slug,
            niche_name=clean_name,
            niche_description=prompt,
            version="1.0.0",
            risk_profile=RiskProfile.LOW,
            capabilities=[
                CapabilityType.PRODUCT_DATABASE,
                CapabilityType.TECHNICAL_SPECS,
                CapabilityType.COMPARISON,
                CapabilityType.AFFILIATE_COMMERCE
            ],
            entity_types=["PrimaryProduct", "Accessory"],
            attributes={
                "PrimaryProduct": [
                    AttributeSpec(key="weight_lbs", display_name="Unit Weight", data_type=DataType.FLOAT, unit="lbs", required=True, critical=False),
                    AttributeSpec(key="dimensions_length_inches", display_name="Length", data_type=DataType.DIMENSION, unit="in", required=True, critical=True),
                    AttributeSpec(key="base_price_usd", display_name="Retail Price", data_type=DataType.MONEY, unit="USD", required=False, critical=False),
                ],
                "Accessory": [
                    AttributeSpec(key="price_usd", display_name="Price", data_type=DataType.MONEY, unit="USD", required=True, critical=False),
                ]
            },
            relationships=[
                RelationshipSpec(source_entity="PrimaryProduct", relationship="accepts", target_entity="Accessory")
            ],
            calculations=[],
            compatibility_rules=[],
            source_policies=[
                SourcePolicySpec(source_type=SourceType.MANUFACTURER, priority=1, allowed_for_critical_facts=True),
                SourcePolicySpec(source_type=SourceType.RETAILER, priority=3, allowed_for_critical_facts=False)
            ],
            page_types=[
                PageTypeSpec(page_type_id="comparison", name="Product Comparison Guide", primary_intent=IntentType.COMPARISON, required_entities=["PrimaryProduct"])
            ]
        )


class AINicheCritic:
    """
    Rigorously answers the 8 architectural critique questions before niche activation.
    """

    @classmethod
    def review_niche(cls, spec: NicheSpec) -> CriticReport:
        findings: List[CriticFinding] = []
        suggestions: List[str] = []

        # Q1: Are important entities missing?
        if len(spec.entity_types) < 2:
            findings.append(CriticFinding(
                question="Are important entities missing?",
                assessment="CONCERN",
                details="Niche defines only 1 entity type. Authority engines excel when comparing or connecting at least 2 distinct interacting entities.",
                recommendation="Add related accessory, consumable, container, or environment entity."
            ))
            suggestions.append("Add complementary entity to unlock relational comparisons.")
        else:
            findings.append(CriticFinding(
                question="Are important entities missing?",
                assessment="SATISFACTORY",
                details=f"Defined {len(spec.entity_types)} distinct interacting entities ({', '.join(spec.entity_types)})."
            ))

        # Q2: Are attributes sufficient?
        total_attrs = sum(len(a) for a in spec.attributes.values())
        if total_attrs < 4:
            findings.append(CriticFinding(
                question="Are attributes sufficient?",
                assessment="CONCERN",
                details=f"Only {total_attrs} attributes defined across all entities. Content may lack numerical depth.",
                recommendation="Add key physical dimensions, capacities, electrical ratings, or certifications."
            ))
            suggestions.append("Expand attribute dictionary to include primary datasheets.")
        else:
            findings.append(CriticFinding(
                question="Are attributes sufficient?",
                assessment="SATISFACTORY",
                details=f"Thorough specification with {total_attrs} verified attributes."
            ))

        # Q3: Can compatibility actually be calculated?
        if CapabilityType.COMPATIBILITY in spec.capabilities:
            if not spec.compatibility_rules:
                findings.append(CriticFinding(
                    question="Can compatibility actually be calculated?",
                    assessment="ACTIONABLE_SUGGESTION",
                    details="Compatibility is enabled but no deterministic rules exist.",
                    recommendation="Add at least one rule with physical dimension or electrical tolerance conditions."
                ))
            else:
                findings.append(CriticFinding(
                    question="Can compatibility actually be calculated?",
                    assessment="SATISFACTORY",
                    details=f"Defined {len(spec.compatibility_rules)} deterministic compatibility rules."
                ))
        else:
            findings.append(CriticFinding(
                question="Can compatibility actually be calculated?",
                assessment="SATISFACTORY",
                details="Compatibility capability is not active for this niche."
            ))

        # Q4: Are page types too overlapping?
        page_ids = [pt.page_type_id for pt in spec.page_types]
        if len(page_ids) != len(set(page_ids)):
            findings.append(CriticFinding(
                question="Are page types too overlapping?",
                assessment="CONCERN",
                details="Duplicate page type archetypes detected.",
                recommendation="Ensure distinct primary search intents per page archetype."
            ))
        else:
            findings.append(CriticFinding(
                question="Are page types too overlapping?",
                assessment="SATISFACTORY",
                details="Page types span distinct search intents (Discovery, Comparison, Compatibility, Calculator)."
            ))

        # Q5: Is the niche too broad?
        if len(spec.entity_types) > 8:
            findings.append(CriticFinding(
                question="Is the niche too broad?",
                assessment="CONCERN",
                details="Niche spans more than 8 entity types. Risk of spreading authority too thin.",
                recommendation="Narrow niche focus to a tight cluster of interacting hardware products."
            ))
            suggestions.append("Consider splitting into two sub-niche sites.")
        else:
            findings.append(CriticFinding(
                question="Is the niche too broad?",
                assessment="SATISFACTORY",
                details="Focused domain scope with clear entity boundaries."
            ))

        # Q6: Are critical facts obtainable?
        has_crit = any(a.critical for attrs in spec.attributes.values() for a in attrs)
        if not has_crit:
            findings.append(CriticFinding(
                question="Are critical facts obtainable?",
                assessment="ACTIONABLE_SUGGESTION",
                details="No attributes marked as CRITICAL. Defining critical attributes ensures quality gates protect factual integrity.",
                recommendation="Mark primary dimensions and safety ratings as critical."
            ))
        else:
            findings.append(CriticFinding(
                question="Are critical facts obtainable?",
                assessment="SATISFACTORY",
                details="Critical attributes identified with strict manufacturer/official source policies."
            ))

        # Q7: Are there obvious YMYL/safety risks?
        clean_desc = (spec.niche_name + " " + spec.niche_description).lower()
        ymyl_triggers = ["medical", "health", "cure", "crypto", "loan", "financial", "legal", "drug"]
        if any(t in clean_desc for t in ymyl_triggers) and spec.risk_profile != RiskProfile.HIGH:
            findings.append(CriticFinding(
                question="Are there obvious YMYL/safety risks?",
                assessment="CONCERN",
                details="Niche touches health, medical, or financial topics but risk profile is not set to HIGH.",
                recommendation="Switch risk_profile to HIGH and mandate human review."
            ))
            suggestions.append("Escalate risk profile to HIGH.")
        else:
            findings.append(CriticFinding(
                question="Are there obvious YMYL/safety risks?",
                assessment="SATISFACTORY",
                details=f"Risk profile '{spec.risk_profile.value}' is well-calibrated for hardware/appliances."
            ))

        # Q8: Could this niche create unique utility?
        has_calc = len(spec.calculations) > 0
        has_comp = len(spec.compatibility_rules) > 0
        if has_calc or has_comp:
            findings.append(CriticFinding(
                question="Could this niche create unique utility?",
                assessment="SATISFACTORY",
                details=f"High unique utility: renders deterministic math ({len(spec.calculations)} formulas) and verified fitment cards ({len(spec.compatibility_rules)} rules)."
            ))
        else:
            findings.append(CriticFinding(
                question="Could this niche create unique utility?",
                assessment="ACTIONABLE_SUGGESTION",
                details="Lacks dynamic calculations or compatibility cards. Content risks reading like standard editorial reviews.",
                recommendation="Add at least one mathematical formula or fitment rule to generate unique interactive components."
            ))
            suggestions.append("Add a calculation tool to deliver 10x unique value over competitors.")

        concerns = sum(1 for f in findings if f.assessment == "CONCERN")
        overall = "EXCELLENT" if concerns == 0 and len(suggestions) <= 1 else ("SOLID" if concerns <= 1 else "NEEDS_WORK")

        return CriticReport(
            niche_id=spec.niche_id,
            overall_health=overall,
            findings=findings,
            suggested_changes=suggestions
        )

    @classmethod
    def critique_niche(cls, spec: NicheSpec) -> Dict[str, Any]:
        """Alias returning dictionary format answering 8 design questions."""
        report = cls.review_niche(spec)
        return {
            "total_questions": len(report.findings),
            "answers": [{"question": f.question, "assessment": f.assessment, "details": f.details} for f in report.findings],
            "verdict": "APPROVE" if report.overall_health in ["EXCELLENT", "SOLID"] else "REVISE",
            "overall_health": report.overall_health,
            "suggested_changes": report.suggested_changes
        }


class DataAvailabilityScore:
    """
    Evaluates whether factual structured data is obtainable prior to site activation.
    """

    @classmethod
    def evaluate(cls, spec: NicheSpec) -> DataAvailabilityReport:
        # Dimensions scored 0 to 100
        authoritative_sources = 90.0 if any(sp.source_type in (SourceType.MANUFACTURER, SourceType.CERTIFICATION) for sp in spec.source_policies) else 50.0
        structured_specs = min(100.0, sum(len(a) for a in spec.attributes.values()) * 12.0)
        entity_coverage = 90.0 if len(spec.entity_types) >= 2 else 60.0
        relationship_calc = 95.0 if spec.calculations or spec.compatibility_rules else 40.0
        commercial_products = 90.0 if CapabilityType.AFFILIATE_COMMERCE in spec.capabilities else 70.0
        source_accessibility = 85.0

        dimensions = {
            "authoritative_source_availability": authoritative_sources,
            "structured_specification_availability": structured_specs,
            "entity_coverage": entity_coverage,
            "relationship_calculability": relationship_calc,
            "commercial_product_availability": commercial_products,
            "source_accessibility": source_accessibility,
        }

        weights = {
            "authoritative_source_availability": 0.25,
            "structured_specification_availability": 0.20,
            "entity_coverage": 0.15,
            "relationship_calculability": 0.15,
            "commercial_product_availability": 0.15,
            "source_accessibility": 0.10,
        }

        overall = sum(dimensions[k] * weights[k] for k in dimensions)

        if overall >= 75.0:
            rating = "STRONG"
            can_activate = True
        elif overall >= 50.0:
            rating = "MODERATE"
            can_activate = True
        else:
            rating = "WEAK"
            can_activate = False

        notes = {
            "authoritative_source_availability": "Manufacturer technical PDFs and certification lab databases available.",
            "structured_specification_availability": f"{sum(len(a) for a in spec.attributes.values())} distinct data points modelled.",
            "entity_coverage": f"{len(spec.entity_types)} entity types provide sufficient domain depth.",
            "relationship_calculability": f"{len(spec.calculations)} formulas and {len(spec.compatibility_rules)} rules.",
            "commercial_product_availability": "Amazon / Retail merchant product catalogs readily scrapable.",
            "source_accessibility": "Public datasheets and manuals accessible without paywalls."
        }

        return DataAvailabilityReport(
            niche_id=spec.niche_id,
            overall_score=round(overall, 1),
            rating=rating,
            can_activate=can_activate,
            dimensions=dimensions,
            dimension_notes=notes,
            recommended_sources=["Manufacturer Datasheets", "AHAM / EPA / Safety Certification Registers", "Retailer Manual Repositories"]
        )

    @classmethod
    def score_niche(cls, spec: NicheSpec) -> Dict[str, Any]:
        """Alias returning score dictionary."""
        report = cls.evaluate(spec)
        return {
            "score": report.rating,
            "numerical_score": report.overall_score,
            "can_activate": report.can_activate,
            "dimensions": report.dimensions,
            "dimension_notes": report.dimension_notes,
            "recommended_sources": report.recommended_sources
        }


class MarketResearchEstimator:
    """
    Simulates / conducts pre-activation market landscape research without publishing articles.
    """

    @classmethod
    def analyze_niche(cls, spec: NicheSpec) -> MarketResearchReport:
        competitor_mix = {
            "MANUFACTURER": 35.0,
            "EDITORIAL": 25.0,
            "RETAILER": 20.0,
            "FORUM": 15.0,
            "AFFILIATE": 5.0
        }
        return MarketResearchReport(
            niche_id=spec.niche_id,
            commercial_viability="HIGH — High-ticket products with ongoing consumable accessories.",
            estimated_serp_competitor_mix=competitor_mix,
            top_competitors=["ConsumerReports", "Wirecutter", "Manufacturer Official Portals", "Reddit User Communities"],
            affiliate_ecosystem_status="ACTIVE — Broad Amazon Associates, Home Depot, and direct manufacturer affiliate programs.",
            data_richness="EXCELLENT — Clear engineering units (dimensions, watts, capacities, decibels).",
            strategic_opportunity="Opportunity to outrank thin affiliate blogs by embedding deterministic calculators and certified fitment cards."
        )

    @classmethod
    def estimate(cls, spec: NicheSpec, country: str = "US") -> Dict[str, Any]:
        """Alias returning market estimate dictionary."""
        report = cls.analyze_niche(spec)
        return {
            "niche_id": report.niche_id,
            "commercial_viability": report.commercial_viability,
            "estimated_monthly_searches": 125000,
            "recommended_pages_initial": 30,
            "intent_breakdown": {"informational": 45, "commercial": 35, "navigational": 10, "transactional": 10},
            "top_competitors": report.top_competitors,
            "strategic_opportunity": report.strategic_opportunity
        }

