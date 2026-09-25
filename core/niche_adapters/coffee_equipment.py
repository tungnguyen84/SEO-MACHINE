"""
Coffee Equipment & Specialty Espresso Knowledge Adapter
Second production niche validating multi-niche architecture without core modifications.
"""
from typing import List, Dict, Any, Set, Optional
from core.niche_adapters.base_adapter import (
    NicheAdapter, Capability, RiskProfile, SourceType,
    ProvenanceClass, PageType, IntentType, FreshnessPolicyType,
    AttributeDefinition, CompatibilityRule, CalculationDefinition, PageBlueprint
)
from core.niche_adapters.registry import NicheRegistry
from core.engine.calculation import CalculationRegistry
from core.engine.compatibility import CompatibilityRuleEngine, CompatibilityStatus


def calculate_coffee_brew_ratio(
    dose_grams: float,
    ratio: float = 2.0,
    brew_method: str = "espresso"
) -> Dict[str, Any]:
    """Calculates target liquid yield in grams and extraction window based on brew ratio."""
    if dose_grams <= 0 or ratio <= 0:
        return {"error": "Dose and ratio must be greater than zero."}

    yield_grams = dose_grams * ratio
    if brew_method.lower() == "espresso":
        time_target = "25 - 32 seconds"
        grind_spec = "Fine espresso grind"
    elif brew_method.lower() == "pourover":
        time_target = "3:00 - 3:45 minutes"
        grind_spec = "Medium-coarse grind"
    else:
        time_target = "4:00 minutes"
        grind_spec = "Coarse immersion grind"

    return {
        "dose_grams": dose_grams,
        "ratio": ratio,
        "brew_method": brew_method,
        "target_yield_grams": round(yield_grams, 1),
        "target_extraction_time": time_target,
        "recommended_grind_profile": grind_spec,
        "display_str": f"{dose_grams}g dose at 1:{ratio} ratio -> {round(yield_grams, 1)}g liquid yield ({time_target})"
    }


def evaluate_filter_basket_fit(basket: Dict[str, Any], machine: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates whether a filter basket fits a machine's grouphead diameter."""
    b_attrs = ctx.get("subject_attrs", {})
    m_attrs = ctx.get("target_attrs", {})

    b_size = b_attrs.get("basket_diameter_mm", {}).get("num")
    m_size = m_attrs.get("grouphead_diameter_mm", {}).get("num") or m_attrs.get("basket_size_mm", {}).get("num")

    if b_size is None or m_size is None:
        return {
            "verdict": "RESEARCH_REQUIRED",
            "compatibility_status": CompatibilityStatus.UNKNOWN.value,
            "confidence": 0.0,
            "fit_detail": f"Missing grouphead or basket diameter specs for {basket.get('brand')} or {machine.get('brand')}.",
            "data_box_html": "<div class='openseo-compat-unknown'>Fit Unknown: Missing diameter measurements.</div>"
        }

    diff = abs(b_size - m_size)
    if diff == 0:
        status = CompatibilityStatus.PASS.value
        verdict = "PASS"
        detail = (
            f"The {basket['brand']} {basket['model']} ({b_size}mm) fits the {machine['brand']} {machine['model']}'s "
            f"{m_size}mm commercial grouphead with exact portafilter clearance."
        )
    elif diff <= 0.5:
        status = CompatibilityStatus.PASS_WITH_CONDITIONS.value
        verdict = "PASS_WITH_CONDITIONS"
        detail = (
            f"Tolerances within 0.5mm ({b_size}mm basket vs {m_size}mm grouphead). Fits with compatible commercial gasket."
        )
    else:
        status = CompatibilityStatus.FAIL.value
        verdict = "FAIL"
        detail = (
            f"Incompatible diameter: {basket['brand']} {basket['model']} is {b_size}mm, whereas "
            f"{machine['brand']} {machine['model']} requires {m_size}mm portafilter baskets."
        )

    html = f"""
    <div class="openseo-coffee-compat" style="border: 2px solid #0284c7; border-radius: 8px; padding: 16px; margin: 16px 0; background: #f0f9ff;">
        <div style="font-weight: 700; color: #0369a1; font-size: 1.1rem; margin-bottom: 8px;">
            ☕ Grouphead Compatibility: {basket['brand']} {basket['model']} → {machine['brand']} {machine['model']}
        </div>
        <p style="margin: 4px 0; color: #1e293b;"><strong>Verdict:</strong> {status} ({verdict})</p>
        <p style="margin: 4px 0; color: #1e293b;"><strong>Diameter Match:</strong> {b_size}mm vs {m_size}mm</p>
        <p style="margin: 4px 0; color: #334155;">{detail}</p>
    </div>
    """

    return {
        "verdict": verdict,
        "compatibility_status": status,
        "confidence": 1.0,
        "reason": detail,
        "fit_detail": detail,
        "data_box_html": html.strip()
    }


class CoffeeEquipmentAdapter(NicheAdapter):
    """Adapter for Specialty Coffee, Espresso Machines, Grinders, and Brewing Mechanics."""

    @property
    def niche_id(self) -> str:
        return "coffee_equipment"

    @property
    def name(self) -> str:
        return "Specialty Coffee & Espresso Equipment"

    @property
    def capabilities(self) -> List[Capability]:
        return [
            Capability.COMPARISON,
            Capability.PRODUCT_DATABASE,
            Capability.TECHNICAL_SPECS,
            Capability.CALCULATION,
            Capability.COMPATIBILITY,
            Capability.AFFILIATE_COMMERCE
        ]

    @property
    def risk_profile(self) -> RiskProfile:
        return RiskProfile.LOW

    @property
    def entity_types(self) -> List[str]:
        return ["coffee_machine", "grinder", "filter_basket", "coffee_bean", "brewing_method"]

    @property
    def attribute_definitions(self) -> Dict[str, List[AttributeDefinition]]:
        return {
            "coffee_machine": [
                AttributeDefinition(key="grouphead_diameter_mm", display_name="Grouphead Size", data_type="numeric", unit_type="mm", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="machine_pressure_bar", display_name="Pump Pressure", data_type="numeric", unit_type="bar", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="boiler_type", display_name="Boiler System", data_type="text", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="pid_temperature_control", display_name="PID Temp Control", data_type="boolean", required=False, criticality="IMPORTANT", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="weight_kg", display_name="Machine Weight", data_type="numeric", unit_type="kg", required=False, criticality="NORMAL", freshness_policy=FreshnessPolicyType.SEMI_DYNAMIC)
            ],
            "grinder": [
                AttributeDefinition(key="grinder_burr_size_mm", display_name="Burr Diameter", data_type="numeric", unit_type="mm", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="burr_type", display_name="Burr Geometry", data_type="text", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="grind_range", display_name="Grind Range Capability", data_type="text", required=True, criticality="IMPORTANT", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="motor_rpm", display_name="Motor RPM", data_type="numeric", unit_type="rpm", required=False, criticality="NORMAL", freshness_policy=FreshnessPolicyType.STATIC)
            ],
            "filter_basket": [
                AttributeDefinition(key="basket_diameter_mm", display_name="Basket Diameter", data_type="numeric", unit_type="mm", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="basket_capacity_grams", display_name="Dose Capacity", data_type="numeric", unit_type="g", required=True, criticality="IMPORTANT", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="ridge_type", display_name="Basket Ridge", data_type="text", required=False, criticality="NORMAL", freshness_policy=FreshnessPolicyType.STATIC)
            ]
        }

    @property
    def intent_taxonomy(self) -> Dict[str, List[str]]:
        return {
            "COMPATIBILITY_GUIDE": ["fit in", "fits in", "compatibility", "compatible with", "portafilter size", "basket fit"],
            "ENGINEERING_RUNTIME": ["brew ratio", "extraction time", "pressure bar", "flow rate"],
            "VS_COMPARISON": [" vs ", " versus ", " compare ", " comparison "],
            "ROUNDUP_BEST_FOR": ["best grinder for", "top espresso machine", "best 58mm basket"]
        }

    @property
    def page_blueprints(self) -> List[PageBlueprint]:
        return [
            PageBlueprint(
                page_type=PageType.COMPATIBILITY,
                title_pattern="{subject} and {target} Portafilter Compatibility",
                required_sections=["Grouphead Specifications", "Basket Diameter Fit", "Extraction Dynamics", "Recommended Portafilters"],
                primary_intent=IntentType.COMPATIBILITY
            ),
            PageBlueprint(
                page_type=PageType.COMPARISON,
                title_pattern="{subject} vs {target}: Burr Size & Grind Uniformity",
                required_sections=["Burr Geometry Comparison", "RPM & Heat Dissipation", "Espresso vs Pourover Grind", "Buying Verdict"],
                primary_intent=IntentType.COMPARISON
            )
        ]

    def get_cluster_differentiators(self) -> Set[str]:
        return {
            "58mm", "54mm", "51mm", "e61", "conical", "flat",
            "grinder", "machine", "espresso", "pourover", "basket", "portafilter",
            "breville", "gaggia", "rancilio", "eureka", "fellow", "baratza"
        }

    def get_domain_stop_words(self) -> Set[str]:
        return {"guide", "setup", "review", "reviews", "best", "top", "for", "in", "with"}

    def get_semantic_synonyms(self) -> Dict[str, str]:
        return {
            "portafilter": "basket",
            "maker": "machine"
        }

    def get_lead_summary(self, primary_entity: Dict[str, Any], model: str, keyword: str) -> str:
        brand = primary_entity.get("brand", "Manufacturer")
        return f"When calibrating the **{brand} {model}** for espresso extraction, precise basket dimensions, pump pressure, and burr geometries are critical."

    def get_known_competitors(self) -> Dict[str, str]:
        return {
            "home-barista.com": "FORUM",
            "coffeeforums.co.uk": "FORUM",
            "reddit.com/r/espresso": "REDDIT",
            "breville.com": "MANUFACTURER",
            "gaggia.com": "MANUFACTURER",
            "ranciliogroup.com": "MANUFACTURER",
            "wholelattelove.com": "RETAILER",
            "seattlecoffeegear.com": "RETAILER",
            "jameshoffmann.co.uk": "EDITORIAL",
            "wirecutter.com": "EDITORIAL"
        }


# Register Coffee calculations and compatibility rules
CalculationRegistry.register(CalculationDefinition(
    calculation_id="coffee_brew_ratio",
    adapter_id="coffee_equipment",
    name="Espresso & Filter Brew Ratio Calculator",
    required_inputs=["dose_grams"],
    optional_inputs=["ratio", "brew_method"],
    formula_version="v1.0-coffee",
    executor=calculate_coffee_brew_ratio,
    output_schema={"target_yield_grams": "float", "target_extraction_time": "str"}
))

CompatibilityRuleEngine.register_rule(CompatibilityRule(
    rule_id="coffee_filter_basket_fit",
    name="Filter Basket to Grouphead Diameter Fit",
    subject_type="filter_basket",
    target_type="coffee_machine",
    evaluator=evaluate_filter_basket_fit
))

# Register adapter in NicheRegistry
_coffee_adapter = CoffeeEquipmentAdapter()
NicheRegistry.register(_coffee_adapter)
