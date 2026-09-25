"""
Config-Driven Niche Adapter & Creation Wizard
Allows simple niches to be instantiated purely from YAML, JSON, or database configuration.
"""
from typing import Dict, Any, List, Set, Optional
import yaml
import json
from pathlib import Path
from core.niche_adapters.base_adapter import (
    NicheAdapter, Capability, RiskProfile, SourceType,
    ProvenanceClass, PageType, IntentType, FreshnessPolicyType,
    AttributeDefinition, CompatibilityRule, CalculationDefinition, PageBlueprint
)
from core.niche_adapters.registry import NicheRegistry


class ConfigDrivenNicheAdapter(NicheAdapter):
    """Dynamically configured niche adapter loaded from declarative YAML/JSON schemas or NicheSpec."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._niche_id = config.get("niche_id", "custom_niche")
        self._name = config.get("name") or config.get("niche_name", "Custom Niche")
        caps = config.get("capabilities", ["PRODUCT_DATABASE", "TECHNICAL_SPECS"])
        self._capabilities = [Capability(c) for c in caps]
        self._risk_profile = RiskProfile(config.get("risk_profile", "LOW"))
        self._entity_types = config.get("entity_types", [])

        # Parse attribute definitions
        self._attribute_definitions: Dict[str, List[AttributeDefinition]] = {}
        for ent_type, attr_list in config.get("attributes", {}).items():
            self._attribute_definitions[ent_type] = []
            for item in attr_list:
                item_dict = item if isinstance(item, dict) else item.model_dump()
                policy_val = item_dict.get("freshness_policy", "SEMI_DYNAMIC")
                policy = FreshnessPolicyType(policy_val) if policy_val in FreshnessPolicyType.__members__ else FreshnessPolicyType.SEMI_DYNAMIC
                self._attribute_definitions[ent_type].append(
                    AttributeDefinition(
                        key=item_dict["key"],
                        display_name=item_dict.get("display_name", item_dict["key"]),
                        data_type=str(item_dict.get("data_type", "numeric")).lower(),
                        unit_type=item_dict.get("unit") or item_dict.get("unit_type"),
                        required=item_dict.get("required", False),
                        criticality="CRITICAL" if item_dict.get("critical", False) else item_dict.get("criticality", "NORMAL"),
                        freshness_policy=policy
                    )
                )

        self._intent_taxonomy = config.get("intent_taxonomy", {})
        self._stop_words = set(config.get("domain_stop_words", ["guide", "review", "best", "top", "for", "vs"]))
        self._cluster_differentiators = set(config.get("cluster_differentiators", []))
        self._known_competitors = config.get("known_competitors", {})

        # Parse calculations into executable CalculationDefinitions
        from core.niche_builder.safe_formula import SafeFormulaEngine
        from core.engine.calculation import CalculationRegistry
        self._calculations: List[CalculationDefinition] = []
        for c in config.get("calculations", []):
            c_dict = c if isinstance(c, dict) else c.model_dump()
            calc_id = c_dict["id"]
            formula_str = c_dict["formula"]
            output_unit = c_dict.get("output_unit", "")
            out_desc = c_dict.get("output_description", "")

            # Create safe AST formula executor
            def make_executor(f_str: str, u: str, d: str):
                def executor(**kwargs) -> Dict[str, Any]:
                    val = SafeFormulaEngine.evaluate(f_str, kwargs)
                    return {
                        "value": round(val, 2),
                        "unit": u,
                        "description": d,
                        "display_str": f"{round(val, 2)} {u}".strip()
                    }
                return executor

            calc_def = CalculationDefinition(
                calculation_id=calc_id,
                adapter_id=self._niche_id,
                name=c_dict.get("name", calc_id),
                required_inputs=c_dict.get("required_variables", []),
                formula_version="1.0",
                executor=make_executor(formula_str, output_unit, out_desc)
            )
            self._calculations.append(calc_def)
            CalculationRegistry.register_calculation(calc_def)

        # Parse compatibility rules into executable CompatibilityRules
        from core.niche_builder.rule_evaluator import DeclarativeRuleEvaluator
        from core.niche_builder.schema import CompatibilityRuleSpec
        from core.engine.compatibility import CompatibilityRuleEngine
        self._compatibility_rules: List[CompatibilityRule] = []
        for r in config.get("compatibility_rules", []):
            rule_spec = r if isinstance(r, CompatibilityRuleSpec) else CompatibilityRuleSpec.model_validate(r)
            
            def make_rule_evaluator(rs: CompatibilityRuleSpec):
                def evaluator(subj: Dict[str, Any], targ: Dict[str, Any], ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
                    return DeclarativeRuleEvaluator.evaluate_rule(rs, subj, targ, ctx)
                return evaluator

            comp_rule = CompatibilityRule(
                rule_id=rule_spec.rule_id,
                name=rule_spec.name,
                subject_type=rule_spec.subject_type,
                target_type=rule_spec.target_type,
                evaluator=make_rule_evaluator(rule_spec),
                explanation_template=f"{{subject}} and {{target}}: {rule_spec.name}"
            )
            self._compatibility_rules.append(comp_rule)
            CompatibilityRuleEngine.register_rule(comp_rule)

    @property
    def niche_id(self) -> str:
        return self._niche_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> List[Capability]:
        return self._capabilities

    @property
    def risk_profile(self) -> RiskProfile:
        return self._risk_profile

    @property
    def entity_types(self) -> List[str]:
        return self._entity_types

    @property
    def attribute_definitions(self) -> Dict[str, List[AttributeDefinition]]:
        return self._attribute_definitions

    @property
    def calculations(self) -> List[CalculationDefinition]:
        return self._calculations

    @property
    def compatibility_rules(self) -> List[CompatibilityRule]:
        return self._compatibility_rules

    @property
    def intent_taxonomy(self) -> Dict[str, List[str]]:
        return self._intent_taxonomy

    def get_domain_stop_words(self) -> Set[str]:
        return self._stop_words

    def get_cluster_differentiators(self) -> Set[str]:
        return self._cluster_differentiators

    def get_known_competitors(self) -> Dict[str, str]:
        return self._known_competitors

    def get_required_specs(self, entity_type: str) -> List[str]:
        specs = self.attribute_definitions.get(entity_type, [])
        return [s.key for s in specs if getattr(s, "required", False)]

    def should_cluster(self, fp1: Set[str], fp2: Set[str], jaccard: float) -> bool:
        diffs = self.get_cluster_differentiators()
        if diffs:
            has_diff1 = bool(fp1 & diffs)
            has_diff2 = bool(fp2 & diffs)
            if has_diff1 != has_diff2:
                return False
        return jaccard >= 0.60 or fp1 == fp2

    @classmethod
    def from_spec(cls, spec: Any) -> "ConfigDrivenNicheAdapter":
        spec_dict = spec.model_dump() if hasattr(spec, "model_dump") else spec
        return cls(spec_dict)

    @classmethod
    def from_yaml_file(cls, file_path: str) -> "ConfigDrivenNicheAdapter":
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> "ConfigDrivenNicheAdapter":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)


class NicheCreationWizard:
    """Guided programmatic workflow for creating and registering new niches without core code changes."""

    @staticmethod
    def create_niche_template(
        niche_id: str,
        name: str,
        capabilities: List[str],
        entity_types: List[str],
        risk_profile: str = "LOW"
    ) -> Dict[str, Any]:
        """Generates a canonical declarative niche dictionary."""
        return {
            "niche_id": niche_id,
            "name": name,
            "capabilities": capabilities,
            "risk_profile": risk_profile,
            "entity_types": entity_types,
            "attributes": {et: [] for et in entity_types},
            "intent_taxonomy": {},
            "domain_stop_words": ["guide", "review", "best", "setup"],
            "cluster_differentiators": [],
            "known_competitors": {}
        }

    @staticmethod
    def save_to_yaml(config: Dict[str, Any], output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return output_path
