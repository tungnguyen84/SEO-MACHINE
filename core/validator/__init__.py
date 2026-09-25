"""
OpenSEO Truth & Quality Gate Validator Module
Enforces factual accuracy, eliminates AI hallucination, and prevents fake testing claims.
"""
from .claim_validator import ClaimValidator
from .quality_gate import QualityGate

__all__ = ["ClaimValidator", "QualityGate"]
