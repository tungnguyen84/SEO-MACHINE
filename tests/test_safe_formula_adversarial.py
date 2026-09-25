"""
Test Suite: Safe Mathematical Formula Adversarial Defense
Exhaustively attacks SafeFormulaEngine with DoS payloads, memory bombs, AST tree exhaustion,
giant exponents, division-by-zero, and arbitrary code injection.
"""

import pytest
from core.niche_builder.safe_formula import SafeFormulaEngine, UnsafeFormulaError


def test_adversarial_expression_length_limit():
    """Verify that formula strings exceeding 1000 characters are rejected prior to AST evaluation."""
    huge_formula = " + ".join(["1"] * 600)  # > 1200 characters
    assert len(huge_formula) > 1000

    with pytest.raises(UnsafeFormulaError) as exc_info:
        SafeFormulaEngine.evaluate(huge_formula, {})
    assert "exceeds maximum allowed limit" in str(exc_info.value)


def test_adversarial_ast_node_count_limit():
    """Verify that deeply nested formulas or excessive operators (> 50 nodes) are rejected."""
    # 30 additions creates > 60 AST nodes
    nested_expr = " + ".join([f"var_{i}" for i in range(30)])
    context = {f"var_{i}": 1.0 for i in range(30)}

    with pytest.raises(UnsafeFormulaError) as exc_info:
        SafeFormulaEngine.evaluate(nested_expr, context)
    assert "AST nodes" in str(exc_info.value) or "exceeds maximum limit" in str(exc_info.value)


def test_adversarial_giant_exponent_dos():
    """Verify that exponents > 20 are rejected to prevent computational CPU exhaustion."""
    # Attempting 2 ** 1000000 or 2 ** 50
    with pytest.raises(UnsafeFormulaError) as exc_info:
        SafeFormulaEngine.evaluate("2 ** 25", {})
    assert "safety limit" in str(exc_info.value) or "DoS prevention" in str(exc_info.value)

    with pytest.raises(UnsafeFormulaError) as exc_info2:
        SafeFormulaEngine.evaluate("base ** exp", {"base": 2, "exp": 100})
    assert "safety limit" in str(exc_info2.value)


def test_adversarial_magnitude_limit():
    """Verify that numbers or results exceeding 1e12 are rejected."""
    with pytest.raises(UnsafeFormulaError) as exc_info:
        SafeFormulaEngine.evaluate("100000000000000 + 5", {})
    assert "magnitude" in str(exc_info.value).lower()

    with pytest.raises(UnsafeFormulaError) as exc_info2:
        SafeFormulaEngine.evaluate("a * b", {"a": 1e8, "b": 1e6})
    assert "magnitude" in str(exc_info2.value).lower()


def test_adversarial_division_by_zero():
    """Verify that division by zero raises UnsafeFormulaError cleanly without crashing."""
    with pytest.raises(UnsafeFormulaError) as exc_info:
        SafeFormulaEngine.evaluate("100 / 0", {})
    assert "Division by zero" in str(exc_info.value)

    with pytest.raises(UnsafeFormulaError) as exc_info2:
        SafeFormulaEngine.evaluate("100 // 0", {})
    assert "Division by zero" in str(exc_info2.value)

    with pytest.raises(UnsafeFormulaError) as exc_info3:
        SafeFormulaEngine.evaluate("100 % 0", {})
    assert "Division by zero" in str(exc_info3.value)


def test_adversarial_code_injection_payloads():
    """Verify that malicious Python code injection is categorically blocked."""
    payloads = [
        "__import__('os').system('dir')",
        "eval('2 + 2')",
        "open('test.txt', 'w')",
        "().__class__.__bases__[0].__subclasses__()",
        "lambda x: x + 1",
        "math.sin(1)",  # Attribute lookup disallowed
        "a[0] + 1",      # Subscript disallowed
        "exec('x = 1')",
    ]

    for p in payloads:
        with pytest.raises(UnsafeFormulaError):
            SafeFormulaEngine.evaluate(p, {"a": [1, 2, 3]})


def test_valid_safe_formulas_remain_functional():
    """Verify that legitimate domain mathematical formulas calculate accurately."""
    res1 = SafeFormulaEngine.evaluate("min(10, 20) + max(5, 2)", {})
    assert res1 == 15.0

    res2 = SafeFormulaEngine.evaluate("round(sqrt(16) * 2.5)", {})
    assert res2 == 10.0

    res3 = SafeFormulaEngine.evaluate("(cargo_vol * 0.8) - safety_margin", {"cargo_vol": 35.5, "safety_margin": 2.5})
    assert abs(res3 - 25.9) < 0.001
