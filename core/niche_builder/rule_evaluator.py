"""
No-Code Visual Compatibility Rule Evaluator
Executes declarative fitment conditions using safe relational operators (==, !=, >, >=, <, <=, IN, RANGE, CONTAINS).
Zero raw Python code execution.
"""

from typing import Dict, Any, List, Optional, Union
from core.niche_builder.schema import CompatibilityRuleSpec, ConditionSpec


class DeclarativeRuleEvaluator:
    """
    Deterministically evaluates no-code compatibility rules between two entities.
    Handles numeric tolerances, physical ranges, discrete sets, and string containment.
    """
    MAX_CONDITIONS = 20
    MAX_STRING_LENGTH = 1000

    @classmethod
    def evaluate_rule(
        cls,
        rule: CompatibilityRuleSpec,
        subject: Dict[str, Any],
        target: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if len(rule.conditions) > cls.MAX_CONDITIONS:
            raise ValueError(
                f"Rule '{rule.name}' has {len(rule.conditions)} conditions, exceeding maximum of {cls.MAX_CONDITIONS}."
            )

        ctx = context or {}
        s_attrs = ctx.get("subject_attrs", {})
        t_attrs = ctx.get("target_attrs", {})

        condition_results: List[bool] = []
        condition_details: List[str] = []
        missing_attrs: List[str] = []

        for cond in rule.conditions:
            s_val = cls._get_attr_value(s_attrs, cond.subject_attribute)
            if s_val is None:
                missing_attrs.append(f"Subject '{subject.get('model', 'entity')}' missing '{cond.subject_attribute}'")
                continue

            if cond.target_attribute:
                t_val = cls._get_attr_value(t_attrs, cond.target_attribute)
                if t_val is None:
                    missing_attrs.append(f"Target '{target.get('model', 'entity')}' missing '{cond.target_attribute}'")
                    continue
            else:
                t_val = cond.constant_value

            passed, msg = cls._evaluate_condition(s_val, cond.operator, t_val, cond.tolerance)
            condition_results.append(passed)
            condition_details.append(f"[{'PASS' if passed else 'FAIL'}] {msg}")

        # If any mandatory attribute was missing
        if missing_attrs:
            detail = f"Missing verified engineering specifications: {'; '.join(missing_attrs)}."
            return {
                "verdict": "UNKNOWN",
                "compatibility_status": "UNKNOWN",
                "confidence": 0.0,
                "fit_detail": detail,
                "reason": detail,
                "data_box_html": f"<div class='openseo-compat-unknown'>{detail}</div>"
            }

        # Apply condition logic (AND / OR)
        if not condition_results:
            is_compatible = True
        elif rule.condition_logic.upper() == "OR":
            is_compatible = any(condition_results)
        else:
            is_compatible = all(condition_results)

        verdict = rule.pass_verdict if is_compatible else rule.fail_verdict
        status = rule.pass_status if is_compatible else rule.fail_status
        base_expl = rule.explanation_pass if is_compatible else rule.explanation_fail

        detail_str = f"{base_expl} Details: {' | '.join(condition_details)}"
        badge_color = "#047857" if verdict == "PASS" else ("#d97706" if verdict == "PASS_WITH_CONDITIONS" else "#dc2626")

        html = f"""
<div class="openseo-declarative-card" style="border: 2px solid {badge_color}; border-radius: 8px; padding: 16px; margin: 16px 0; background: {'#f0fdf4' if is_compatible else '#fef2f2'};">
    <div style="font-weight: 700; color: {'#065f46' if is_compatible else '#991b1b'}; font-size: 1.05rem; margin-bottom: 8px;">
        {'✔' if is_compatible else '✖'} {rule.name}: {subject.get('brand', '')} {subject.get('model', '')} + {target.get('brand', '')} {target.get('model', '')}
    </div>
    <div style="color: #1e293b; font-size: 0.95rem; margin-bottom: 8px;">{base_expl}</div>
    <ul style="margin: 0; padding-left: 20px; font-size: 0.88rem; color: #475569;">
        {''.join(f'<li>{d}</li>' for d in condition_details)}
    </ul>
    <div style="margin-top: 8px; font-weight: 600; color: {badge_color};">Verdict: {status} ({verdict})</div>
</div>
""".strip()

        return {
            "verdict": verdict,
            "compatibility_status": status,
            "confidence": 1.0,
            "fit_detail": detail_str,
            "reason": detail_str,
            "condition_results": condition_results,
            "data_box_html": html
        }

    @staticmethod
    def _get_attr_value(attrs: Dict[str, Any], key: str) -> Optional[Any]:
        if key in attrs:
            val_obj = attrs[key]
            if isinstance(val_obj, dict):
                return val_obj.get("num") if val_obj.get("num") is not None else val_obj.get("text")
            return val_obj
        return None

    @classmethod
    def _evaluate_condition(cls, val_s: Any, op: str, val_t: Any, tolerance: float = 0.0) -> tuple[bool, str]:
        op_clean = op.strip().upper()

        # Numeric comparisons
        is_s_num = isinstance(val_s, (int, float))
        is_t_num = isinstance(val_t, (int, float))

        try:
            if not is_s_num and str(val_s).replace(".", "", 1).isdigit():
                val_s = float(val_s)
                is_s_num = True
            if not is_t_num and str(val_t).replace(".", "", 1).isdigit():
                val_t = float(val_t)
                is_t_num = True
        except Exception:
            pass

        if op_clean in ("==", "EQ"):
            if is_s_num and is_t_num:
                delta = abs(float(val_s) - float(val_t))
                passed = delta <= tolerance
                return passed, f"Value {val_s} == {val_t} (delta {delta:.2f} <= tolerance {tolerance})"
            passed = str(val_s).strip().lower() == str(val_t).strip().lower()
            return passed, f"'{val_s}' == '{val_t}'"

        elif op_clean in ("!=", "NEQ"):
            if is_s_num and is_t_num:
                delta = abs(float(val_s) - float(val_t))
                passed = delta > tolerance
                return passed, f"Value {val_s} != {val_t} (delta {delta:.2f} > {tolerance})"
            passed = str(val_s).strip().lower() != str(val_t).strip().lower()
            return passed, f"'{val_s}' != '{val_t}'"

        elif op_clean in (">", "GT"):
            passed = float(val_s) > float(val_t)
            return passed, f"{val_s} > {val_t}"

        elif op_clean in (">=", "GTE"):
            passed = float(val_s) >= (float(val_t) - tolerance)
            return passed, f"{val_s} >= {val_t} (tolerance {tolerance})"

        elif op_clean in ("<", "LT"):
            passed = float(val_s) < float(val_t)
            return passed, f"{val_s} < {val_t}"

        elif op_clean in ("<=", "LTE"):
            passed = float(val_s) <= (float(val_t) + tolerance)
            return passed, f"{val_s} <= {val_t} (tolerance {tolerance})"

        elif op_clean == "IN":
            target_set = val_t if isinstance(val_t, (list, tuple, set)) else [item.strip() for item in str(val_t).split(",")]
            norm_s = str(val_s).strip().lower()
            norm_targets = [str(x).strip().lower() for x in target_set]
            passed = norm_s in norm_targets
            return passed, f"'{val_s}' IN [{', '.join(str(x) for x in target_set)}]"

        elif op_clean == "RANGE":
            # val_t expected as [min_val, max_val] or "min_val,max_val"
            if isinstance(val_t, (list, tuple)) and len(val_t) >= 2:
                min_v, max_v = float(val_t[0]), float(val_t[1])
            else:
                parts = [float(x.strip()) for x in str(val_t).split(",")]
                min_v, max_v = parts[0], parts[1]
            num_s = float(val_s)
            passed = (min_v - tolerance) <= num_s <= (max_v + tolerance)
            return passed, f"{min_v} <= {num_s} <= {max_v}"

        elif op_clean == "CONTAINS":
            passed = str(val_t).strip().lower() in str(val_s).strip().lower()
            return passed, f"'{val_s}' CONTAINS '{val_t}'"

        return False, f"Unsupported operator '{op}'"

    @classmethod
    def _eval_condition(cls, val_s: Any, op: str, val_t: Any = None, collection: Any = None, tolerance: Optional[float] = None) -> bool:
        """Helper for unit tests and direct evaluation."""
        target = collection if collection is not None else val_t
        tol = tolerance if tolerance is not None else 0.0
        passed, _ = cls._evaluate_condition(val_s, op, target, tol)
        return passed

