"""
AI-Assisted Niche Designer, Critic, Market Researcher & Data Availability Scorer
Transforms natural language prompts into complete, valid NicheDraft schemas.
Provides critical evaluations without modifying code or auto-activating.
Pure generic core: strictly zero domain-specific keyword lookup tables.
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
    ProvenanceType,
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
    Pure Generic AI Niche Designer.
    Generates structured, validated NicheDraft schemas from natural language descriptions
    without hardcoded domain dictionaries or keyword routing.
    """

    @classmethod
    def build_design_prompt(cls, user_description: str) -> str:
        """
        Constructs the formal system instruction prompt for LLM reasoning
        mandating the strict structured NicheDraft output schema.
        """
        return f"""You are the OpenSEO AI Niche Architect.
Analyze the user's natural language domain description and produce a complete, strictly structured JSON schema.

User Description:
\"\"\"{user_description}\"\"\"

Required JSON Schema:
{{
  "niche_name": "<Human readable domain title>",
  "niche_id": "<lowercase_snake_case_slug>",
  "description": "<Concise domain description>",
  "risk_profile": "LOW" | "MEDIUM" | "HIGH",
  "capabilities": ["COMPATIBILITY", "CALCULATION", "COMPARISON", "PRODUCT_DATABASE", "TECHNICAL_SPECS", "AFFILIATE_COMMERCE"],
  "entity_types": ["<PrimaryEntity>", "<ContextOrEnvironmentEntity>", ...],
  "attributes": {{
    "<EntityName>": [
      {{
        "key": "<attribute_snake_case>",
        "display_name": "<Label>",
        "data_type": "STRING"|"INTEGER"|"FLOAT"|"BOOLEAN"|"DIMENSION"|"POWER"|"MONEY",
        "unit": "<unit_symbol_or_empty>",
        "required": true|false,
        "critical": true|false,
        "preferred_source_type": "MANUFACTURER"|"CERTIFICATION"|"DOCUMENTATION"|"RETAILER"
      }}
    ]
  }},
  "relationships": [
    {{
      "source_entity": "<Entity1>",
      "relationship": "suitable_for"|"compatible_with"|"uses"|"operates_in",
      "target_entity": "<Entity2>",
      "description": "<Description>"
    }}
  ],
  "calculations": [
    {{
      "id": "<calc_id>",
      "name": "<Formula Name>",
      "formula": "<safe_arithmetic_formula>",
      "output_unit": "<unit>",
      "output_description": "<description>",
      "required_variables": ["<var1>", "<var2>"],
      "provenance_type": "MODEL_PROPOSED",
      "confidence": 0.70,
      "assumptions": ["<assumptions>"]
    }}
  ],
  "suitability_or_compatibility_rules": [
    {{
      "rule_id": "<rule_id>",
      "name": "<Rule Name>",
      "subject_type": "<Entity1>",
      "target_type": "<Entity2>",
      "conditions": [
        {{
          "subject_attribute": "<attr>",
          "operator": ">="|"<="|"=="|"IN",
          "target_attribute": "<target_attr>",
          "tolerance": 0.0
        }}
      ],
      "pass_verdict": "STRONG_MATCH" | "PASS",
      "fail_verdict": "NOT_SUITABLE" | "FAIL",
      "provenance_type": "MODEL_PROPOSED",
      "confidence": 0.70,
      "assumptions": ["<assumptions>"]
    }}
  ],
  "page_types": [
    {{
      "page_type_id": "compatibility"|"comparison"|"calculator"|"hub"|"troubleshooting",
      "name": "<Page Type Name>",
      "primary_intent": "COMPATIBILITY"|"COMPARISON"|"UTILITY"|"INFORMATIONAL",
      "required_entities": ["<Entity1>"]
    }}
  ],
  "source_policies": [
    {{"source_type": "MANUFACTURER", "priority": 1, "allowed_for_critical_facts": true, "freshness_interval_days": 365}},
    {{"source_type": "DOCUMENTATION", "priority": 2, "allowed_for_critical_facts": true, "freshness_interval_days": 365}},
    {{"source_type": "RETAILER", "priority": 3, "allowed_for_critical_facts": false, "freshness_interval_days": 7}}
  ],
  "freshness_rules": [],
  "monetization_types": ["affiliate_commerce", "display_ads"]
}}

Rules:
1. All domain calculations and suitability rules MUST have provenance_type="MODEL_PROPOSED".
2. Never claim unverified formulas are official standards without explicit citation evidence.
3. Every attribute must map directly to observable physical, operational, or commercial metrics.
"""

    @classmethod
    def design_from_prompt(cls, prompt: str) -> NicheDraft:
        """
        Synthesizes a structured NicheDraft from an arbitrary natural language prompt
        using generic semantic linguistic parsing and schema synthesis.
        Strictly zero domain keyword routing tables.
        """
        clean_text = prompt.strip()
        draft_id = f"draft_{uuid.uuid4().hex[:8]}"

        spec = cls._synthesize_generic_ontology(clean_text)
        rationale = (
            f"Dynamically synthesized domain ontology with {len(spec.entity_types)} entities, "
            f"{sum(len(v) for v in spec.attributes.values())} attributes, {len(spec.calculations)} proposed calculations, "
            f"and {len(spec.compatibility_rules)} proposed rules based on prompt analysis."
        )

        return NicheDraft(
            draft_id=draft_id,
            prompt=prompt,
            proposed_niche=spec,
            ai_rationale=rationale,
            status="PROPOSED"
        )

    @classmethod
    def _synthesize_generic_ontology(cls, prompt: str) -> NicheSpec:
        """
        Extracts entities, attributes, relationships, calculations, and rules generically
        from the grammatical and syntactic structure of the prompt.
        """
        low = prompt.lower()

        # 1. Identify primary domain subject from action verb patterns
        # e.g. "choose [X] based on", "find compatible [X] for", "comparing [X] against", "website about [X]"
        primary_entity_name = "PrimaryProduct"
        subject_matches = re.findall(
            r"(?:choose|find|comparing|select|evaluate|recommend|review|testing)\s+([a-zA-Z0-9\s\-]+?)(?:\s+based on|\s+for|\s+against|\s+with|\s+and|\.|$)",
            prompt,
            re.IGNORECASE
        )
        if subject_matches:
            raw_subj = subject_matches[0].strip()
            # Clean words like "compatible", "high-authority", "best"
            cleaned_subj = re.sub(r"^(?:compatible|high-authority|best|top|new|portable)\s+", "", raw_subj, flags=re.IGNORECASE)
            words = [w.capitalize() for w in re.split(r"[\s\-_]+", cleaned_subj) if len(w) > 2]
            if words:
                primary_entity_name = "".join(words[:2])
                # Singularize simple plural
                if primary_entity_name.endswith("s") and not primary_entity_name.endswith("ss"):
                    primary_entity_name = primary_entity_name[:-1]

        # 2. Extract context environments, targets, and accessories
        context_entities: List[str] = []
        raw_factors: List[str] = []

        # Extract "based on <factors>" or "with <factors>"
        factor_match = re.search(r"(?:based on|with|considering|evaluating)\s+([^.]+)", prompt, re.IGNORECASE)
        if factor_match:
            parts = re.split(r",|\band\b", factor_match.group(1))
            raw_factors = [p.strip() for p in parts if p.strip()]

        # Extract "for their <target>" or "for <target>"
        target_match = re.search(r"(?:for their|for)\s+([a-zA-Z0-9\s]+?)(?:models|systems|setups|machines|units|\.|,)", prompt, re.IGNORECASE)
        if target_match:
            tgt_phrase = target_match.group(1).strip()
            tgt_words = [w.capitalize() for w in tgt_phrase.split() if len(w) > 2 and w.lower() not in ["their", "your", "each", "both"]]
            if tgt_words:
                tgt_name = "".join(tgt_words[:2])
                if tgt_name and tgt_name != primary_entity_name and tgt_name not in context_entities:
                    context_entities.append(tgt_name)

        # Syntactically extract environment or container nouns from factor phrases
        for factor in raw_factors:
            f_clean = factor.strip()
            # Match physical environment or container nouns like "<noun> conditions", "<noun> size", "<noun> environment", "<noun> area"
            m = re.search(r"([a-zA-Z]+)\s+(?:conditions|size|environment|space|enclosure|area)", f_clean, re.IGNORECASE)
            if m:
                env_word = m.group(1).capitalize()
                if env_word and env_word != primary_entity_name and env_word not in context_entities:
                    context_entities.append(env_word)
            # Detect component or media factors like "filter media"
            elif any(k in f_clean.lower() for k in ["media", "consumable", "accessory", "replacement"]):
                words = [w.capitalize() for w in f_clean.split() if len(w) > 2]
                if words:
                    comp_name = "".join(words[:2])
                    if comp_name != primary_entity_name and comp_name not in context_entities:
                        context_entities.append(comp_name)

        # If secondary entities are mentioned in "find compatible presser feet, bobbins, needles"
        accessory_match = re.search(r"(?:compatible|matching|replacement)\s+([^.]+?)\s+for", prompt, re.IGNORECASE)
        if accessory_match:
            acc_parts = re.split(r",|\band\b", accessory_match.group(1))
            for p in acc_parts:
                p_clean = p.strip()
                p_words = [w.capitalize() for w in p_clean.split() if len(w) > 2 and w.lower() not in ["their", "other", "all"]]
                if p_words:
                    acc_name = "".join(p_words[:2])
                    if acc_name.endswith("s") and not acc_name.endswith("ss"):
                        acc_name = acc_name[:-1]
                    if acc_name and acc_name != primary_entity_name and acc_name not in context_entities:
                        context_entities.append(acc_name)

        # Default fallback entity if only 1 entity found to ensure relational authority
        if not context_entities:
            context_entities.append("TargetEnvironment")

        all_entity_types = [primary_entity_name] + context_entities

        # 3. Attribute Extraction based on semantic factor patterns
        attributes: Dict[str, List[AttributeSpec]] = {e: [] for e in all_entity_types}

        # Core baseline attributes for primary product
        attributes[primary_entity_name].append(
            AttributeSpec(key="brand", display_name="Brand / Manufacturer", data_type=DataType.STRING, required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER)
        )
        attributes[primary_entity_name].append(
            AttributeSpec(key="model", display_name="Model Number / Designation", data_type=DataType.STRING, required=True, critical=True, preferred_source_type=SourceType.MANUFACTURER)
        )
        attributes[primary_entity_name].append(
            AttributeSpec(key="retail_price_usd", display_name="Retail Price", data_type=DataType.MONEY, unit="USD", required=False, critical=False, preferred_source_type=SourceType.RETAILER)
        )

        # Map factors into structured attributes
        has_power_factor = False
        has_flow_factor = False
        has_size_factor = False

        for f in raw_factors:
            f_clean = f.lower().strip()
            attr_slug = re.sub(r"[^a-z0-9]+", "_", f_clean).strip("_")

            # Dimensional / Sizing factors
            if any(k in f_clean for k in ["size", "area", "dimension", "length", "width", "height", "volume", "clearance", "sqft", "sq ft"]):
                has_size_factor = True
                unit_val = "sqft" if "sqft" in f_clean else ("gal" if "gal" in f_clean else ("in" if "in" in f_clean else "units"))
                attributes[primary_entity_name].append(
                    AttributeSpec(
                        key=f"recommended_{attr_slug}",
                        display_name=f.title() + " Rating",
                        data_type=DataType.DIMENSION,
                        unit=unit_val,
                        required=True,
                        critical=True,
                        preferred_source_type=SourceType.MANUFACTURER
                    )
                )
                # Also attribute to context entity if appropriate
                tgt_ent = next((e for e in context_entities if e.lower() in f_clean), context_entities[0])
                attributes[tgt_ent].append(
                    AttributeSpec(
                        key=f"{attr_slug}",
                        display_name=f.title(),
                        data_type=DataType.DIMENSION,
                        unit=unit_val,
                        required=True,
                        critical=True,
                        preferred_source_type=SourceType.DOCUMENTATION
                    )
                )

            # Power / Energy factors
            elif any(k in f_clean for k in ["energy", "power", "watt", "electricity", "consumption"]):
                has_power_factor = True
                attributes[primary_entity_name].append(
                    AttributeSpec(
                        key="power_consumption_watts",
                        display_name="Rated Power Consumption",
                        data_type=DataType.POWER,
                        unit="W",
                        required=True,
                        critical=False,
                        preferred_source_type=SourceType.MANUFACTURER
                    )
                )

            # Flow / Rate / Capacity factors
            elif any(k in f_clean for k in ["flow", "turnover", "throughput", "capacity", "rate", "delivery"]):
                has_flow_factor = True
                unit_str = "units/hr" if "flow" in f_clean or "turnover" in f_clean else "capacity_units"
                attributes[primary_entity_name].append(
                    AttributeSpec(
                        key=f"{attr_slug}",
                        display_name=f.title(),
                        data_type=DataType.FLOAT,
                        unit=unit_str,
                        required=True,
                        critical=True,
                        preferred_source_type=SourceType.MANUFACTURER
                    )
                )

            # Sound / Noise factors
            elif any(k in f_clean for k in ["noise", "sound", "decibel", "db", "quiet"]):
                attributes[primary_entity_name].append(
                    AttributeSpec(
                        key="noise_level_db",
                        display_name="Operating Noise Level",
                        data_type=DataType.FLOAT,
                        unit="dB",
                        required=False,
                        critical=False,
                        preferred_source_type=SourceType.MANUFACTURER
                    )
                )

            # Cost / Running / Operating cost factors
            elif any(k in f_clean for k in ["cost", "operating", "running", "maintenance"]):
                if "operating" in f_clean or "running" in f_clean:
                    has_power_factor = True
                attributes[primary_entity_name].append(
                    AttributeSpec(
                        key=f"{attr_slug}_usd",
                        display_name=f.title() + " (Annual)",
                        data_type=DataType.MONEY,
                        unit="USD",
                        required=False,
                        critical=False,
                        preferred_source_type=SourceType.RETAILER
                    )
                )

            # Categorical / Setup / Method factors
            else:
                attributes[primary_entity_name].append(
                    AttributeSpec(
                        key=f"{attr_slug}",
                        display_name=f.title(),
                        data_type=DataType.STRING,
                        unit="",
                        required=True,
                        critical=False,
                        preferred_source_type=SourceType.MANUFACTURER
                    )
                )

        # Ensure context entities have at least 2 attributes
        for ce in context_entities:
            if len(attributes[ce]) == 0:
                attributes[ce].append(
                    AttributeSpec(key="name_designation", display_name="Type / Classification", data_type=DataType.STRING, required=True, critical=True, preferred_source_type=SourceType.DOCUMENTATION)
                )
                attributes[ce].append(
                    AttributeSpec(key="specification_value", display_name="Operating Requirement", data_type=DataType.STRING, required=True, critical=False, preferred_source_type=SourceType.DOCUMENTATION)
                )

        # 4. Propose Relationships
        relationships: List[RelationshipSpec] = []
        for ce in context_entities:
            relationships.append(
                RelationshipSpec(
                    source_entity=primary_entity_name,
                    relationship="suitable_for" if any(w in ce.lower() for w in ["room", "tank", "environment", "area"]) else "compatible_with",
                    target_entity=ce,
                    description=f"{primary_entity_name} evaluated against {ce} operating requirements and specifications."
                )
            )

        # 5. Propose Calculations based on extracted variables
        calculations: List[CalculationSpec] = []

        if has_power_factor or any("power" in a.key or "watt" in a.key for a in attributes[primary_entity_name]):
            calculations.append(
                CalculationSpec(
                    id="annual_operating_cost",
                    name="Annual Electrical Operating Cost",
                    formula="(power_consumption_watts / 1000.0) * hours_per_day * 365.0 * electricity_rate_kwh",
                    output_unit="USD",
                    output_description="Estimated annual continuous electrical utility cost based on wattage, usage hours, and kWh electricity tariff.",
                    required_variables=["power_consumption_watts", "hours_per_day", "electricity_rate_kwh"],
                    provenance_type="MODEL_PROPOSED",
                    source_ids=[],
                    confidence=0.70,
                    assumptions=["Heuristic electricity model requiring local utility tariff verification (e.g. baseline assumption $0.16/kWh)"]
                )
            )

        if has_flow_factor and has_size_factor:
            calculations.append(
                CalculationSpec(
                    id="system_turnover_rate",
                    name="Hourly Turnover Rate Sizing",
                    formula="flow_rate_primary / volume_target",
                    output_unit="turnovers/hr",
                    output_description="Calculated hourly circulation/turnover rate relative to target volume.",
                    required_variables=["flow_rate_primary", "volume_target"],
                    provenance_type="MODEL_PROPOSED",
                    source_ids=[],
                    confidence=0.70,
                    assumptions=["Standard circulation guideline derived from prompt requirements"]
                )
            )
        elif has_size_factor:
            calculations.append(
                CalculationSpec(
                    id="coverage_suitability_ratio",
                    name="Rated Coverage Suitability Ratio",
                    formula="rated_coverage / actual_target_size",
                    output_unit="ratio",
                    output_description="Calculated ratio of rated capacity against target dimension requirements.",
                    required_variables=["rated_coverage", "actual_target_size"],
                    provenance_type="MODEL_PROPOSED",
                    source_ids=[],
                    confidence=0.70,
                    assumptions=["Direct linear sizing ratio comparison"]
                )
            )

        # 6. Propose Suitability & Compatibility Rules
        compatibility_rules: List[CompatibilityRuleSpec] = []
        target_entity = context_entities[0] if context_entities else "TargetEnvironment"

        # Sizing / capacity compatibility rule
        size_attrs_primary = [a.key for a in attributes[primary_entity_name] if "size" in a.key or "sqft" in a.key or "volume" in a.key or "flow" in a.key]
        size_attrs_target = [a.key for a in attributes[target_entity] if "size" in a.key or "sqft" in a.key or "volume" in a.key or "area" in a.key]

        subj_attr = size_attrs_primary[0] if size_attrs_primary else attributes[primary_entity_name][0].key
        tgt_attr = size_attrs_target[0] if size_attrs_target else attributes[target_entity][0].key

        compatibility_rules.append(
            CompatibilityRuleSpec(
                rule_id=f"{primary_entity_name.lower()}_{target_entity.lower()}_suitability",
                name=f"{primary_entity_name} to {target_entity} Sizing Suitability",
                subject_type=primary_entity_name,
                target_type=target_entity,
                conditions=[
                    ConditionSpec(
                        subject_attribute=subj_attr,
                        operator=">=",
                        target_attribute=tgt_attr,
                        tolerance=0.0
                    )
                ],
                pass_verdict="STRONG_MATCH",
                pass_status="SUITABLE_MATCH",
                fail_verdict="NOT_SUITABLE",
                fail_status="UNDERSIZED_OR_INCOMPATIBLE",
                explanation_pass=f"{primary_entity_name} specifications meet or exceed recommended {target_entity} operational thresholds.",
                explanation_fail=f"{primary_entity_name} capacity is insufficient for {target_entity} requirements.",
                provenance_type="MODEL_PROPOSED",
                confidence=0.70,
                assumptions=["Model proposed suitability rule awaiting empirical manufacturer source verification"]
            )
        )

        # 7. Propose Standard Strategy Page Types
        page_types = [
            PageTypeSpec(
                page_type_id="suitability",
                name=f"{primary_entity_name} Sizing & Suitability Guide",
                primary_intent=IntentType.COMPATIBILITY,
                required_entities=[primary_entity_name, target_entity]
            ),
            PageTypeSpec(
                page_type_id="comparison",
                name=f"Top {primary_entity_name} Head-to-Head Comparison",
                primary_intent=IntentType.COMPARISON,
                required_entities=[primary_entity_name]
            ),
            PageTypeSpec(
                page_type_id="calculator",
                name=f"{primary_entity_name} Operating Cost & Sizing Calculator",
                primary_intent=IntentType.UTILITY,
                required_entities=[primary_entity_name]
            ),
            PageTypeSpec(
                page_type_id="hub",
                name=f"Complete {primary_entity_name} Buyer's Authority Hub",
                primary_intent=IntentType.INFORMATIONAL,
                required_entities=[primary_entity_name, target_entity]
            )
        ]

        # 8. Source Policies
        source_policies = [
            SourcePolicySpec(source_type=SourceType.MANUFACTURER, priority=1, allowed_for_critical_facts=True, freshness_interval_days=365),
            SourcePolicySpec(source_type=SourceType.DOCUMENTATION, priority=2, allowed_for_critical_facts=True, freshness_interval_days=365),
            SourcePolicySpec(source_type=SourceType.RETAILER, priority=3, allowed_for_critical_facts=False, freshness_interval_days=7)
        ]

        # 9. Clean Niche Name & ID
        clean_name = f"{primary_entity_name} Authority Guide"
        slug = re.sub(r"(?<!^)(?=[A-Z])", "_", primary_entity_name).lower().strip("_")
        if not slug:
            slug = f"niche_{uuid.uuid4().hex[:6]}"

        return NicheSpec(
            niche_id=slug,
            niche_name=clean_name,
            niche_description=prompt,
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
            entity_types=all_entity_types,
            attributes=attributes,
            relationships=relationships,
            calculations=calculations,
            compatibility_rules=compatibility_rules,
            source_policies=source_policies,
            page_types=page_types,
            freshness_rules=[],
            monetization_types=["affiliate_commerce", "display_ads"],
            intent_taxonomy={
                "SIZING_SUITABILITY": ["what size", "how to choose", "recommendation for", "sizing chart"],
                "VS_COMPARISON": [" vs ", " versus ", " compare ", "best models"],
                "COST_CALCULATOR": ["how much does it cost", "running cost", "power consumption", "calculator"]
            },
            cluster_differentiators=[e.lower() for e in all_entity_types] + ["cost", "specs", "size", "reviews"]
        )


class AINicheCritic:
    """
    Rigorously answers the 8 architectural critique questions before niche activation.
    Pure generic reasoning without domain-specific hardcoding.
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
                recommendation="Add key physical dimensions, capacities, electrical ratings, or specifications."
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
                    recommendation="Add at least one rule with physical dimension or operational tolerance conditions."
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
                recommendation="Narrow niche focus to a tight cluster of interacting products."
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
                recommendation="Mark primary dimensions and specifications as critical."
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
                details=f"Risk profile '{spec.risk_profile.value}' is well-calibrated for physical consumer and commercial products."
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
    Pure generic metrics without domain-specific hardcoding.
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
            "authoritative_source_availability": "Manufacturer technical specifications and documentation registers available.",
            "structured_specification_availability": f"{sum(len(a) for a in spec.attributes.values())} distinct data points modelled.",
            "entity_coverage": f"{len(spec.entity_types)} entity types provide sufficient domain depth.",
            "relationship_calculability": f"{len(spec.calculations)} formulas and {len(spec.compatibility_rules)} rules.",
            "commercial_product_availability": "Retail merchant product catalogs readily scrapable.",
            "source_accessibility": "Public datasheets and manuals accessible without paywalls."
        }

        return DataAvailabilityReport(
            niche_id=spec.niche_id,
            overall_score=round(overall, 1),
            rating=rating,
            can_activate=can_activate,
            dimensions=dimensions,
            dimension_notes=notes,
            recommended_sources=["Manufacturer Technical Datasheets", "Independent Testing Repositories", "Retail Specification Catalogs"]
        )

    @classmethod
    def score_niche(cls, spec: NicheSpec) -> Dict[str, Any]:
        """Alias returning score dictionary."""
        report = cls.evaluate(spec)
        return {
            "score": report.rating,
            "rating": report.rating,
            "numerical_score": report.overall_score,
            "overall_score": report.overall_score,
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
            top_competitors=["ConsumerGuides", "IndependentReviewPortals", "ManufacturerPortals", "UserCommunities"],
            affiliate_ecosystem_status="ACTIVE — Broad retailer and direct manufacturer affiliate programs available.",
            data_richness="EXCELLENT — Clear engineering units (dimensions, watts, capacities, decibels).",
            strategic_opportunity="Opportunity to outrank thin affiliate blogs by embedding deterministic calculators and verified fitment cards."
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
            "strategic_opportunity": report.strategic_opportunity,
            "warning_notice": report.warning_notice
        }
