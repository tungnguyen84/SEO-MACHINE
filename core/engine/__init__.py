"""
OpenSEO Engineering & Physics Calculation Engine
Calculates real-world battery runtimes, inverter efficiencies, thermal de-rating,
dimensional clearance, and cross-domain entity interoperability.
"""
from .calculation import CalculationEngine, CalculationRegistry
from .compatibility import CompatibilityEngine, CompatibilityRuleEngine

__all__ = ["CalculationEngine", "CalculationRegistry", "CompatibilityEngine", "CompatibilityRuleEngine"]
