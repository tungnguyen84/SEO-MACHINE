"""
Workshop Tools & Battery Platform Knowledge Adapter
Third production niche validating multi-niche architecture without core modifications.
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


def calculate_tool_cuts_per_charge(
    voltage_v: float,
    amp_hours_ah: float,
    cut_energy_wh: float = 3.5
) -> Dict[str, Any]:
    """Calculates estimated standard 2x4 lumber cuts per charge."""
    if voltage_v <= 0 or amp_hours_ah <= 0 or cut_energy_wh <= 0:
        return {"error": "Voltage, amp hours, and cut energy must be positive numbers."}

    total_wh = voltage_v * amp_hours_ah
    estimated_cuts = int(total_wh / cut_energy_wh)

    return {
        "total_pack_energy_wh": round(total_wh, 1),
        "energy_per_cut_wh": cut_energy_wh,
        "estimated_cuts_count": estimated_cuts,
        "display_str": f"{voltage_v}V {amp_hours_ah}Ah pack ({round(total_wh, 1)}Wh) -> ~{estimated_cuts} standard crosscuts"
    }


def evaluate_tool_battery_fit(battery: Dict[str, Any], tool: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates whether a battery pack locks into and powers a cordless power tool."""
    b_attrs = ctx.get("subject_attrs", {})
    t_attrs = ctx.get("target_attrs", {})

    b_platform = (b_attrs.get("battery_system", {}).get("text") or b_attrs.get("platform_name", {}).get("text") or "").strip().lower()
    t_platform = (t_attrs.get("battery_system", {}).get("text") or "").strip().lower()

    b_volt = b_attrs.get("voltage_v", {}).get("num")
    t_volt = t_attrs.get("voltage_v", {}).get("num")

    if not b_platform or not t_platform:
        return {
            "verdict": "RESEARCH_REQUIRED",
            "compatibility_status": CompatibilityStatus.UNKNOWN.value,
            "confidence": 0.0,
            "fit_detail": f"Missing battery platform documentation for {battery.get('brand')} or {tool.get('brand')}.",
            "data_box_html": "<div class='openseo-compat-unknown'>Battery Platform Unknown: Missing system spec.</div>"
        }

    # Brand & platform match
    is_flexvolt_compatible = "flexvolt" in b_platform and ("20v" in t_platform or "dewalt 20v" in t_platform)
    is_exact_platform = b_platform == t_platform

    if is_exact_platform or is_flexvolt_compatible:
        status = CompatibilityStatus.PASS.value
        verdict = "PASS"
        detail = (
            f"The {battery['brand']} {battery['model']} ({b_platform.upper()}) fits and operates "
            f"the {tool['brand']} {tool['model']} seamlessly via native slide-on platform mount."
        )
    elif battery.get("brand", "").lower() != tool.get("brand", "").lower():
        status = CompatibilityStatus.FAIL.value
        verdict = "FAIL"
        detail = (
            f"Cross-brand platform mismatch: {battery['brand']} ({b_platform}) cannot natively power "
            f"{tool['brand']} ({t_platform}) tools due to proprietary rail terminal geometry."
        )
    else:
        status = CompatibilityStatus.FAIL.value
        verdict = "FAIL"
        detail = (
            f"Voltage/Platform mismatch: {battery['brand']} {b_platform} ({b_volt}V) does not fit {t_platform} ({t_volt}V)."
        )

    html = f"""
    <div class="openseo-tool-compat" style="border: 2px solid #ea580c; border-radius: 8px; padding: 16px; margin: 16px 0; background: #fff7ed;">
        <div style="font-weight: 700; color: #c2410c; font-size: 1.1rem; margin-bottom: 8px;">
            🛠 Cordless Platform Fit: {battery['brand']} {battery['model']} → {tool['brand']} {tool['model']}
        </div>
        <p style="margin: 4px 0; color: #1e293b;"><strong>Compatibility Status:</strong> {status} ({verdict})</p>
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


class WorkshopToolsAdapter(NicheAdapter):
    """Adapter for Power Tools, Cordless Battery Platforms, and Job Site Accessories."""

    @property
    def niche_id(self) -> str:
        return "workshop_tools"

    @property
    def name(self) -> str:
        return "Workshop Power Tools & Battery Platforms"

    @property
    def capabilities(self) -> List[Capability]:
        return [
            Capability.COMPATIBILITY,
            Capability.CALCULATION,
            Capability.PRODUCT_DATABASE,
            Capability.TECHNICAL_SPECS,
            Capability.AFFILIATE_COMMERCE
        ]

    @property
    def risk_profile(self) -> RiskProfile:
        return RiskProfile.MEDIUM

    @property
    def entity_types(self) -> List[str]:
        return ["power_tool", "battery_platform", "accessory", "material", "job_type"]

    @property
    def attribute_definitions(self) -> Dict[str, List[AttributeDefinition]]:
        return {
            "power_tool": [
                AttributeDefinition(key="voltage_v", display_name="Operating Voltage", data_type="numeric", unit_type="V", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="battery_system", display_name="Battery Platform", data_type="text", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="brushless", display_name="Brushless Motor", data_type="boolean", required=True, criticality="IMPORTANT", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="max_rpm", display_name="No-Load Speed", data_type="numeric", unit_type="rpm", required=False, criticality="NORMAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="weight_lbs", display_name="Bare Tool Weight", data_type="numeric", unit_type="lbs", required=False, criticality="NORMAL", freshness_policy=FreshnessPolicyType.SEMI_DYNAMIC)
            ],
            "battery_platform": [
                AttributeDefinition(key="voltage_v", display_name="Nominal Voltage", data_type="numeric", unit_type="V", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="platform_name", display_name="Platform Name", data_type="text", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.STATIC),
                AttributeDefinition(key="amp_hours_ah", display_name="Pack Capacity", data_type="numeric", unit_type="Ah", required=True, criticality="CRITICAL", freshness_policy=FreshnessPolicyType.SEMI_DYNAMIC),
                AttributeDefinition(key="cell_type", display_name="Cell Chemistry", data_type="text", required=False, criticality="NORMAL", freshness_policy=FreshnessPolicyType.STATIC)
            ]
        }

    @property
    def intent_taxonomy(self) -> Dict[str, List[str]]:
        return {
            "COMPATIBILITY_GUIDE": ["will battery fit", "compatible battery", "battery fit", "tool compatibility", "battery cross platform"],
            "ENGINEERING_RUNTIME": ["cuts per charge", "battery runtime", "torque in lbs", "rpm"],
            "VS_COMPARISON": [" vs ", " versus ", " compare ", " comparison "],
            "ROUNDUP_BEST_FOR": ["best cordless drill", "best impact driver for", "top 18v tool"]
        }

    def get_cluster_differentiators(self) -> Set[str]:
        return {
            "dewalt", "milwaukee", "makita", "bosch", "ryobi", "ridgid",
            "20v", "18v", "m18", "m12", "flexvolt", "drill", "impact", "saw", "battery"
        }

    def get_domain_stop_words(self) -> Set[str]:
        return {"guide", "setup", "review", "reviews", "best", "top", "for", "in", "with"}

    def get_lead_summary(self, primary_entity: Dict[str, Any], model: str, keyword: str) -> str:
        brand = primary_entity.get("brand", "Manufacturer")
        return f"When assessing the **{brand} {model}** for heavy job site construction, cordless battery platform compatibility and motor efficiency are paramount."

    def get_known_competitors(self) -> Dict[str, str]:
        return {
            "toolguyd.com": "EDITORIAL",
            "protoolreviews.com": "EDITORIAL",
            "garagejournal.com": "FORUM",
            "reddit.com/r/tools": "REDDIT",
            "homedepot.com": "RETAILER",
            "lowes.com": "RETAILER",
            "dewalt.com": "MANUFACTURER",
            "milwaukeetool.com": "MANUFACTURER",
            "makitatools.com": "MANUFACTURER"
        }


# Register Workshop calculations and compatibility rules
CalculationRegistry.register(CalculationDefinition(
    calculation_id="workshop_battery_cuts",
    adapter_id="workshop_tools",
    name="Cordless Tool Cuts Per Charge Estimator",
    required_inputs=["voltage_v", "amp_hours_ah"],
    optional_inputs=["cut_energy_wh"],
    formula_version="v1.0-tools",
    executor=calculate_tool_cuts_per_charge,
    output_schema={"estimated_cuts_count": "int", "total_pack_energy_wh": "float"}
))

CompatibilityRuleEngine.register_rule(CompatibilityRule(
    rule_id="workshop_battery_fit",
    name="Cordless Battery to Tool Platform Fit",
    subject_type="battery_platform",
    target_type="power_tool",
    evaluator=evaluate_tool_battery_fit
))

# Register adapter in NicheRegistry
_workshop_adapter = WorkshopToolsAdapter()
NicheRegistry.register(_workshop_adapter)
