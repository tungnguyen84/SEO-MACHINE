"""
No-Code Niche Builder & SaaS Site Automation Subsystem
Enables end-to-end site creation, AI-assisted niche modeling, declarative formula parsing,
no-code compatibility evaluation, validation, sandboxing, and multi-tenant management.
"""

from .schema import (
    DataType,
    AttributeSpec,
    RelationshipSpec,
    CalculationSpec,
    CompatibilityRuleSpec,
    SourcePolicySpec,
    PageTypeSpec,
    ContentPolicySpec,
    NicheSpec,
    NicheDraft,
    SiteLifecycleStatus,
    PermissionRole,
    NicheVersionSpec,
)
from .safe_formula import SafeFormulaEngine
from .rule_evaluator import DeclarativeRuleEvaluator
from .validator import NicheValidator, ValidationReport, ValidationIssue, IssueSeverity
from .ai_designer import AINicheDesigner, AINicheCritic, MarketResearchEstimator, DataAvailabilityScore
from .sandbox import NicheSandbox, SandboxReport
from .versioning import NicheVersioningManager
from .credentials import EncryptedCredentialStore
from .lifecycle import SaaSSiteManager

__all__ = [
    "DataType",
    "AttributeSpec",
    "RelationshipSpec",
    "CalculationSpec",
    "CompatibilityRuleSpec",
    "SourcePolicySpec",
    "PageTypeSpec",
    "ContentPolicySpec",
    "NicheSpec",
    "NicheDraft",
    "SiteLifecycleStatus",
    "PermissionRole",
    "NicheVersionSpec",
    "SafeFormulaEngine",
    "DeclarativeRuleEvaluator",
    "NicheValidator",
    "ValidationReport",
    "ValidationIssue",
    "IssueSeverity",
    "AINicheDesigner",
    "AINicheCritic",
    "MarketResearchEstimator",
    "DataAvailabilityScore",
    "NicheSandbox",
    "SandboxReport",
    "NicheVersioningManager",
    "EncryptedCredentialStore",
    "SaaSSiteManager",
]
