"""
Safe Mathematical Formula Engine
Parses and evaluates declarative arithmetic formulas using an AST visitor.
Strictly rejects arbitrary code execution, raw eval(), attribute lookups, unsafe calls,
and resource-exhaustion / DoS attacks (massive ASTs, giant exponents, memory bombs).
"""

import ast
import math
from typing import Dict, Any, Set, List, Union, Tuple, Optional


class UnsafeFormulaError(ValueError):
    """Raised when a formula violates AST safety or resource restrictions."""
    pass


class SafeFormulaEngine:
    """
    Evaluates mathematical expressions safely by walking the Python AST.
    Guarantees:
    - Zero access to builtins, imports, filesystem, or OS operations.
    - Input length capped at 1000 characters to prevent ReDoS / memory abuse.
    - AST complexity capped at 50 nodes to prevent deeply nested stack-overflow attacks.
    - Exponents capped at abs(b) <= 20 to prevent computational DoS (e.g. 2**1000000).
    - Numeric values constrained within [-1e12, 1e12] and strictly finite (no NaN / Inf).
    - Division by zero raises UnsafeFormulaError cleanly.
    """

    MAX_EXPRESSION_LENGTH = 1000
    MAX_AST_NODES = 50
    MAX_EXPONENT = 20
    MAX_MAGNITUDE = 1e12

    @classmethod
    def _safe_div(cls, a: float, b: float) -> float:
        if b == 0:
            raise UnsafeFormulaError("Division by zero in formula.")
        return a / b

    @classmethod
    def _safe_floordiv(cls, a: float, b: float) -> float:
        if b == 0:
            raise UnsafeFormulaError("Division by zero in formula.")
        return a // b

    @classmethod
    def _safe_mod(cls, a: float, b: float) -> float:
        if b == 0:
            raise UnsafeFormulaError("Division by zero in formula.")
        return a % b

    @classmethod
    def _safe_pow(cls, a: float, b: float) -> float:
        if abs(b) > cls.MAX_EXPONENT:
            raise UnsafeFormulaError(
                f"Exponent {b} exceeds safety limit of {cls.MAX_EXPONENT} (DoS prevention)."
            )
        try:
            res = a ** b
            if math.isinf(res) or math.isnan(res):
                raise UnsafeFormulaError("Exponentiation resulted in non-finite value.")
            return res
        except OverflowError:
            raise UnsafeFormulaError("Exponentiation calculation overflow.")

    ALLOWED_UNARY_OPS = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
    }

    ALLOWED_FUNCTIONS = {
        "min": min,
        "max": max,
        "round": round,
        "abs": abs,
        "sqrt": math.sqrt,
        "ceil": math.ceil,
        "floor": math.floor,
        "log": math.log,
        "exp": math.exp,
    }

    @classmethod
    def _get_binary_ops(cls):
        return {
            ast.Add: lambda a, b: a + b,
            ast.Sub: lambda a, b: a - b,
            ast.Mult: lambda a, b: a * b,
            ast.Div: cls._safe_div,
            ast.FloorDiv: cls._safe_floordiv,
            ast.Mod: cls._safe_mod,
            ast.Pow: cls._safe_pow,
        }

    @classmethod
    def _parse_and_validate_ast(cls, formula_str: str) -> ast.Expression:
        if not formula_str or not isinstance(formula_str, str):
            raise UnsafeFormulaError("Formula expression cannot be empty.")

        clean_str = formula_str.strip()
        if len(clean_str) > cls.MAX_EXPRESSION_LENGTH:
            raise UnsafeFormulaError(
                f"Formula length ({len(clean_str)}) exceeds maximum allowed limit of {cls.MAX_EXPRESSION_LENGTH} characters."
            )

        try:
            tree = ast.parse(clean_str, mode="eval")
        except SyntaxError as e:
            raise UnsafeFormulaError(f"Syntax error in formula '{formula_str}': {e}")

        # AST Complexity validation (prevent deeply nested expressions / AST bombs)
        node_count = sum(1 for _ in ast.walk(tree))
        if node_count > cls.MAX_AST_NODES:
            raise UnsafeFormulaError(
                f"Formula complexity ({node_count} AST nodes) exceeds maximum limit of {cls.MAX_AST_NODES} nodes."
            )

        return tree

    @classmethod
    def extract_variables(cls, formula_str: str) -> Set[str]:
        """Extracts variable names from a formula expression string with AST safety checks."""
        tree = cls._parse_and_validate_ast(formula_str)

        variables: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in cls.ALLOWED_FUNCTIONS:
                    variables.add(node.id)
            elif isinstance(node, (ast.Attribute, ast.Subscript, ast.Lambda, ast.Import, ast.ImportFrom)):
                raise UnsafeFormulaError(f"Disallowed AST construct '{type(node).__name__}' in formula.")
        return variables

    @classmethod
    def validate_formula(cls, formula_str: str) -> Tuple[bool, Set[str], Optional[str]]:
        """
        Validates formula syntax and safety without executing it.
        Returns (is_valid, extracted_variables, error_message).
        """
        try:
            vars_found = cls.extract_variables(formula_str)
            return True, vars_found, None
        except Exception as e:
            return False, set(), str(e)

    @classmethod
    def evaluate(cls, formula_str: str, context: Dict[str, Union[int, float]]) -> float:
        """
        Evaluates a formula with a numerical context dictionary.
        Strictly prevents code injection, DoS, and non-finite outputs.
        """
        tree = cls._parse_and_validate_ast(formula_str)
        result = cls._eval_node(tree.body, context)

        if math.isnan(result) or math.isinf(result):
            raise UnsafeFormulaError("Formula evaluation resulted in non-finite value (NaN or Inf).")

        if abs(result) > cls.MAX_MAGNITUDE:
            raise UnsafeFormulaError(
                f"Formula result {result} exceeds maximum allowed magnitude of {cls.MAX_MAGNITUDE}."
            )

        return float(result)

    @classmethod
    def _eval_node(cls, node: ast.AST, context: Dict[str, Union[int, float]]) -> float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                val = float(node.value)
                if abs(val) > cls.MAX_MAGNITUDE:
                    raise UnsafeFormulaError(f"Constant value exceeds magnitude limit: {val}")
                return val
            raise UnsafeFormulaError(f"Literal constants must be numeric, got {type(node.value).__name__}")

        elif isinstance(node, ast.Name):
            if node.id in context:
                val = context[node.id]
                if isinstance(val, (int, float)):
                    num_val = float(val)
                else:
                    try:
                        num_val = float(str(val))
                    except (ValueError, TypeError):
                        raise UnsafeFormulaError(f"Variable '{node.id}' value '{val}' is not a valid number.")

                if abs(num_val) > cls.MAX_MAGNITUDE:
                    raise UnsafeFormulaError(f"Variable '{node.id}' value exceeds magnitude limit: {num_val}")
                return num_val
            raise UnsafeFormulaError(f"Undefined variable in formula: '{node.id}'")

        elif isinstance(node, ast.BinOp):
            bin_ops = cls._get_binary_ops()
            op_type = type(node.op)
            if op_type not in bin_ops:
                raise UnsafeFormulaError(f"Disallowed binary operator '{op_type.__name__}'")
            left_val = cls._eval_node(node.left, context)
            right_val = cls._eval_node(node.right, context)
            res = float(bin_ops[op_type](left_val, right_val))
            if abs(res) > cls.MAX_MAGNITUDE:
                raise UnsafeFormulaError("Intermediate calculation exceeds magnitude limit.")
            return res

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_UNARY_OPS:
                raise UnsafeFormulaError(f"Disallowed unary operator '{op_type.__name__}'")
            operand_val = cls._eval_node(node.operand, context)
            res = float(cls.ALLOWED_UNARY_OPS[op_type](operand_val))
            return res

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise UnsafeFormulaError("Only direct named functions from whitelist are permitted.")
            func_name = node.func.id
            if func_name not in cls.ALLOWED_FUNCTIONS:
                raise UnsafeFormulaError(f"Function '{func_name}' is not in the safe mathematical whitelist.")

            args = [cls._eval_node(arg, context) for arg in node.args]
            fn = cls.ALLOWED_FUNCTIONS[func_name]
            try:
                res = float(fn(*args))
                if math.isnan(res) or math.isinf(res) or abs(res) > cls.MAX_MAGNITUDE:
                    raise UnsafeFormulaError(f"Function '{func_name}' returned out-of-bounds or non-finite result.")
                return res
            except Exception as e:
                raise UnsafeFormulaError(f"Error executing function '{func_name}': {e}")

        else:
            raise UnsafeFormulaError(f"Disallowed AST expression element: '{type(node).__name__}'")
