"""
OpenSEO Niche Adapters Module
Domain-specific knowledge bases, ontologies, and entity seeders.
"""
from .base_adapter import (
    NicheAdapter, BaseNicheAdapter, Capability, RiskProfile,
    SourceType, ProvenanceClass, PageType, IntentType,
    AttributeDefinition, CompatibilityRule, CalculationDefinition, PageBlueprint
)
from .registry import NicheRegistry

__all__ = [
    "NicheAdapter", "BaseNicheAdapter", "Capability", "RiskProfile",
    "SourceType", "ProvenanceClass", "PageType", "IntentType",
    "AttributeDefinition", "CompatibilityRule", "CalculationDefinition", "PageBlueprint",
    "NicheRegistry"
]
