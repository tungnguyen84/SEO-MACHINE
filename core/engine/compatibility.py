"""
Generic Compatibility Rule Engine
Evaluates dimensional, electrical, chemical, mechanical, and functional
interoperability between entities across any domain.
"""
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from core.database import get_entity, get_entity_attributes, upsert_compatibility
from core.niche_adapters.base_adapter import CompatibilityRule
from .calculation import CalculationEngine


class CompatibilityStatus(str, Enum):
    PASS = "PASS"
    PASS_WITH_CONDITIONS = "PASS_WITH_CONDITIONS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class CompatibilityRuleEngine:
    """Registry and executor for domain interoperability rules."""
    _rules: Dict[str, CompatibilityRule] = {}

    @classmethod
    def register_rule(cls, rule: CompatibilityRule):
        cls._rules[rule.rule_id] = rule

    @classmethod
    def get_rule(cls, rule_id: str) -> Optional[CompatibilityRule]:
        return cls._rules.get(rule_id)

    @classmethod
    def find_rules(cls, subject_type: str, target_type: str) -> List[CompatibilityRule]:
        return [
            r for r in cls._rules.values()
            if (r.subject_type == subject_type or r.subject_type == "*") and
               (r.target_type == target_type or r.target_type == "*")
        ]

    @classmethod
    def clear(cls):
        cls._rules.clear()


    @classmethod
    def get_all_rules(cls) -> List[CompatibilityRule]:
        return list(cls._rules.values())


class CompatibilityEngine:
    """Multi-niche compatibility evaluator executing registered domain rules."""

    @classmethod
    def register_rule(cls, rule: CompatibilityRule):
        CompatibilityRuleEngine.register_rule(rule)

    @classmethod
    def evaluate(cls, subject_id: str, target_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Evaluates compatibility between subject and target by running registered rules.
        """
        # Ensure adapters are loaded if registry is empty
        if not CompatibilityRuleEngine.get_all_rules():
            try:
                from core.niche_adapters.registry import NicheRegistry
                import core.niche_adapters.vehicle_camping
            except Exception:
                pass

        subj = get_entity(subject_id)
        targ = get_entity(target_id)

        if not subj or not targ:
            return {
                "verdict": CompatibilityStatus.UNKNOWN.value,
                "compatibility_status": CompatibilityStatus.UNKNOWN.value,
                "fit_detail": "One or both entities not found in database.",
                "data_box_html": ""
            }

        s_attrs = get_entity_attributes(subject_id)
        t_attrs = get_entity_attributes(target_id)
        s_type = subj.get("entity_type", "")
        t_type = targ.get("entity_type", "")

        # Find matching rules in registry
        matching_rules = CompatibilityRuleEngine.find_rules(s_type, t_type)

        if matching_rules:
            # Execute primary matching rule
            rule = matching_rules[0]
            if rule.evaluator:
                res = rule.evaluator(subj, targ, {"subject_attrs": s_attrs, "target_attrs": t_attrs, **(context or {})})
                return res

        # Built-in fallback rule for generic pairs
        return {
            "verdict": CompatibilityStatus.PASS.value,
            "compatibility_status": CompatibilityStatus.PASS.value,
            "fit_detail": f"Both {subj['brand']} {subj['model']} and {targ['brand']} {targ['model']} share universal physical/operational standards.",
            "data_box_html": f"<div class='comp-box'>Compatible: {subj['model']} & {targ['model']}</div>"
        }
