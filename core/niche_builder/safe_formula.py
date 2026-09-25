"""
Safe Mathematical Formula Engine
Parses and evaluates declarative arithmetic formulas using an AST visitor.
Strictly rejects arbitrary code execution, raw eval(), attribute lookups, and unsafe calls.
"""

import ast
import math
from typing import Dict, Any, Set, List, Union, Tuple, Optional


class UnsafeFormulaError(ValueError):
    """Raised when a formula violates AST safety restrictions."""
    pass


class SafeFormulaEngine:
    """
    Evaluates mathematical expressions safely by walking the Python AST.
    Guarantees no access to builtins, imports, filesystem, or OS operations.
    """

    ALLOWED_BINARY_OPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b if b != 0 else float("inf"),
        ast.FloorDiv: lambda a, b: a // b if b != 0 else float("inf"),
        ast.Mod: lambda a, b: a % b if b != 0 else 0,
        ast.Pow: lambda a, b: a ** b if abs(b) <= 100 else float("inf"),
    }

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
    def extract_variables(cls, formula_str: str) -> Set[str]:
        """Extracts variable names from a formula expression string."""
        try:
            tree = ast.parse(formula_str.strip(), mode="eval")
        except SyntaxError as e:
            raise UnsafeFormulaError(f"Syntax error in formula '{formula_str}': {e}")

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
        Strictly prevents code injection or unsafe operations.
        """
        try:
            tree = ast.parse(formula_str.strip(), mode="eval")
        except SyntaxError as e:
            raise UnsafeFormulaError(f"Syntax error in formula: {e}")

        return cls._eval_node(tree.body, context)

    @classmethod
    def _eval_node(cls, node: ast.AST, context: Dict[str, Union[int, float]]) -> float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise UnsafeFormulaError(f"Literal constants must be numeric, got {type(node.value).__name__}")

        elif isinstance(node, ast.Name):
            if node.id in context:
                val = context[node.id]
                if isinstance(val, (int, float)):
                    return float(val)
                try:
                    return float(str(val))
                except (ValueError, TypeError):
                    raise UnsafeFormulaError(f"Variable '{node.id}' value '{val}' is not a valid number.")
            raise UnsafeFormulaError(f"Undefined variable in formula: '{node.id}'")

        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_BINARY_OPS:
                raise UnsafeFormulaError(f"Disallowed binary operator '{op_type.__name__}'")
            left_val = cls._eval_node(node.left, context)
            right_val = cls._eval_node(node.right, context)
            return float(cls.ALLOWED_BINARY_OPS[op_type](left_val, right_val))

        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in cls.ALLOWED_UNARY_OPS:
                raise UnsafeFormulaError(f"Disallowed unary operator '{op_type.__name__}'")
            operand_val = cls._eval_node(node.operand, context)
            return float(cls.ALLOWED_UNARY_OPS[op_type](operand_val))

        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise UnsafeFormulaError("Only direct named functions from whitelist are permitted.")
            func_name = node.func.id
            if func_name not in cls.ALLOWED_FUNCTIONS:
                raise UnsafeFormulaError(f"Function '{func_name}' is not in the safe mathematical whitelist.")

            args = [cls._eval_node(arg, context) for arg in node.args]
            fn = cls.ALLOWED_FUNCTIONS[func_name]
            try:
                res = fn(*args)
                return float(res)
            except Exception as e:
                raise UnsafeFormulaError(f"Error executing function '{func_name}': {e}")

        else:
            raise UnsafeFormulaError(f"Disallowed AST expression element: '{type(node).__name__}'")


# Type alias helper
Tuple_Validation = tuple[bool, Set[str], Optional[str]]
