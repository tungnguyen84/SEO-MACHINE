"""
Niche Data Model & Architecture Validator
Performs comprehensive structural, mathematical, relational, and source checks before site activation.
Strictly blocks activation if any ERROR is detected.
"""

from enum import Enum
from typing import List, Dict, Any, Set, Optional
from pydantic import BaseModel, Field

from core.niche_builder.schema import (
    NicheSpec,
    DataType,
    CapabilityType,
    SourceType,
    RiskProfile,
)
from core.niche_builder.safe_formula import SafeFormulaEngine


class IssueSeverity(str, Enum):
    ERROR = "ERROR"      # Blocks activation
    WARNING = "WARNING"  # Flagged to user, does not block
    INFO = "INFO"        # Best practice suggestion


class ValidationIssue(BaseModel):
    """Specific finding during niche validation."""
    code: str = ""
    severity: IssueSeverity
    category: str
    target: str
    message: str
    recommendation: Optional[str] = None


class ValidationReport(BaseModel):
    """Comprehensive health audit of a declarative niche specification."""
    niche_id: str
    is_valid: bool
    errors_count: int
    warnings_count: int
    info_count: int
    issues: List[ValidationIssue] = Field(default_factory=list)

    @property
    def can_activate(self) -> bool:
        return self.errors_count == 0

    @property
    def critical_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.ERROR]


class NicheValidator:
    """
    Validates a declarative NicheSpec across 11 core integrity dimensions.
    """

    VALID_UNITS_BY_DATATYPE = {
        DataType.POWER: {"W", "kW", "mW", "hp"},
        DataType.ENERGY: {"Wh", "kWh", "J", "BTU", "mAh", "Ah"},
        DataType.DIMENSION: {"in", "mm", "cm", "m", "ft", "sqft", "sqm", "cu_ft", "cu_in", "L"},
        DataType.MONEY: {"USD", "EUR", "GBP", "VND", "CAD", "AUD", "$", "€", "£"},
        DataType.PERCENTAGE: {"%", "pct"},
        DataType.BOOLEAN: {None, ""},
        DataType.DATE: {None, "", "ISO8601", "YYYY-MM-DD"},
        DataType.URL: {None, ""},
    }

    AUTHORITATIVE_SOURCES = {
        SourceType.MANUFACTURER,
        SourceType.CERTIFICATION,
        SourceType.GOVERNMENT,
        SourceType.DOCUMENTATION,
        SourceType.OFFICIAL,
    }

    @classmethod
    def validate(cls, spec: NicheSpec) -> ValidationReport:
        issues: List[ValidationIssue] = []

        cls._check_entities(spec, issues)
        cls._check_attributes(spec, issues)
        cls._check_relationships(spec, issues)
        cls._check_calculations(spec, issues)
        cls._check_compatibility_rules(spec, issues)
        cls._check_page_types(spec, issues)
        cls._check_sources(spec, issues)
        cls._check_capabilities(spec, issues)
        cls._check_risk_profile(spec, issues)

        errors = [i for i in issues if i.severity == IssueSeverity.ERROR]
        warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]
        info = [i for i in issues if i.severity == IssueSeverity.INFO]

        return ValidationReport(
            niche_id=spec.niche_id,
            is_valid=len(errors) == 0,
            errors_count=len(errors),
            warnings_count=len(warnings),
            info_count=len(info),
            issues=issues
        )

    @classmethod
    def _check_entities(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        if not spec.entity_types:
            issues.append(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category="ENTITY",
                target="entity_types",
                message="Niche defines no entity types.",
                recommendation="Add at least one primary entity type (e.g. Product)."
            ))
            return

        # Check for duplicate entity names
        seen = set()
        for et in spec.entity_types:
            clean = et.strip().lower()
            if clean in seen:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="ENTITY",
                    target=et,
                    message=f"Duplicate entity type '{et}' found.",
                    recommendation="Remove duplicate entity declaration."
                ))
            seen.add(clean)

        # Check orphan entities (no attributes AND no relationships)
        rel_entities = set()
        for r in spec.relationships:
            rel_entities.add(r.source_entity.lower())
            rel_entities.add(r.target_entity.lower())

        for et in spec.entity_types:
            has_attrs = len(spec.attributes.get(et, [])) > 0
            has_rel = et.lower() in rel_entities
            if not has_attrs and not has_rel:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="ENTITY",
                    target=et,
                    message=f"Orphan entity '{et}' has neither attributes nor relationships.",
                    recommendation=f"Define attributes or relationships for '{et}', or delete it."
                ))

    @classmethod
    def _check_attributes(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        all_attr_keys_per_entity: Dict[str, Set[str]] = {}

        for et, attrs in spec.attributes.items():
            if et not in spec.entity_types:
                issues.append(ValidationIssue(
                    code="ORPHAN_ATTRIBUTE_ENTITY",
                    severity=IssueSeverity.ERROR,
                    category="ATTRIBUTE",
                    target=et,
                    message=f"Attributes declared for undeclared entity '{et}'.",
                    recommendation=f"Add '{et}' to entity_types list."
                ))
            seen_keys = set()
            for a in attrs:
                if not a.key or not a.key.strip():
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category="ATTRIBUTE",
                        target=f"{et}.<empty>",
                        message="Attribute key cannot be empty.",
                        recommendation="Provide a machine-readable key (e.g., 'power_watts')."
                    ))
                    continue

                if a.key in seen_keys:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category="ATTRIBUTE",
                        target=f"{et}.{a.key}",
                        message=f"Duplicate attribute key '{a.key}' on entity '{et}'.",
                        recommendation="Attribute keys must be unique per entity."
                    ))
                seen_keys.add(a.key)

                # Validate Unit consistency with DataType
                if a.data_type in cls.VALID_UNITS_BY_DATATYPE:
                    allowed_units = cls.VALID_UNITS_BY_DATATYPE[a.data_type]
                    if a.unit and a.unit not in allowed_units:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            category="ATTRIBUTE",
                            target=f"{et}.{a.key}",
                            message=f"Unit '{a.unit}' may not match data type '{a.data_type.value}'.",
                            recommendation=f"Expected one of: {sorted(list(str(u) for u in allowed_units if u))}"
                        ))

                # Check critical attributes source authority
                if a.critical:
                    if a.preferred_source_type not in cls.AUTHORITATIVE_SOURCES:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            category="ATTRIBUTE",
                            target=f"{et}.{a.key}",
                            message=f"Critical attribute '{a.key}' has non-authoritative source type '{a.preferred_source_type.value}'.",
                            recommendation="Critical engineering attributes require MANUFACTURER, DOCUMENTATION, or CERTIFICATION."
                        ))

            all_attr_keys_per_entity[et] = seen_keys

    @classmethod
    def _check_relationships(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        known_ents = set(spec.entity_types)
        for r in spec.relationships:
            if r.source_entity not in known_ents:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="RELATIONSHIP",
                    target=f"{r.source_entity}->{r.target_entity}",
                    message=f"Relationship source entity '{r.source_entity}' is undefined.",
                    recommendation=f"Define '{r.source_entity}' in entity_types."
                ))
            if r.target_entity not in known_ents:
                issues.append(ValidationIssue(
                    code="RELATIONSHIP_TARGET_NOT_FOUND",
                    severity=IssueSeverity.ERROR,
                    category="RELATIONSHIP",
                    target=f"{r.source_entity}->{r.target_entity}",
                    message=f"Relationship target entity '{r.target_entity}' is undefined.",
                    recommendation=f"Define '{r.target_entity}' in entity_types."
                ))

            # Self-relationship check (circular)
            if r.source_entity == r.target_entity and not r.bidirectional:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category="RELATIONSHIP",
                    target=f"{r.source_entity}->{r.target_entity}",
                    message=f"Self-referencing relationship '{r.relationship}' on entity '{r.source_entity}'.",
                    recommendation="Ensure self-relationship is intended."
                ))

    @classmethod
    def _check_calculations(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        # Collect all defined attribute keys across all entities
        all_attrs = set()
        for attrs in spec.attributes.values():
            for a in attrs:
                all_attrs.add(a.key)

        calc_ids = set()
        for c in spec.calculations:
            if c.id in calc_ids:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="CALCULATION",
                    target=c.id,
                    message=f"Duplicate calculation ID '{c.id}'.",
                    recommendation="Calculation IDs must be unique."
                ))
            calc_ids.add(c.id)

            # Validate AST safety & syntax
            is_valid, extracted_vars, err_msg = SafeFormulaEngine.validate_formula(c.formula)
            if not is_valid:
                issues.append(ValidationIssue(
                    code="CALCULATION_UNSAFE",
                    severity=IssueSeverity.ERROR,
                    category="CALCULATION",
                    target=c.id,
                    message=f"Unsafe or invalid formula in calculation '{c.name}': {err_msg}",
                    recommendation="Ensure formula uses standard arithmetic and whitelisted functions."
                ))
            else:
                # Check if formula variables exist in attributes or declared required_variables
                for v in extracted_vars:
                    if v not in all_attrs and v not in c.required_variables:
                        issues.append(ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            category="CALCULATION",
                            target=c.id,
                            message=f"Variable '{v}' in calculation '{c.name}' is not in known attributes or required_variables.",
                            recommendation=f"Add '{v}' as an attribute or pass it as an explicit input."
                        ))

    @classmethod
    def _check_compatibility_rules(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        known_ents = set(spec.entity_types)
        rule_ids = set()

        for cr in spec.compatibility_rules:
            if cr.rule_id in rule_ids:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="COMPATIBILITY",
                    target=cr.rule_id,
                    message=f"Duplicate compatibility rule ID '{cr.rule_id}'.",
                    recommendation="Rule IDs must be unique."
                ))
            rule_ids.add(cr.rule_id)

            if cr.subject_type not in known_ents and cr.subject_type != "*":
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="COMPATIBILITY",
                    target=cr.rule_id,
                    message=f"Compatibility rule subject '{cr.subject_type}' is undefined.",
                    recommendation=f"Define '{cr.subject_type}' in entity_types."
                ))
            if cr.target_type not in known_ents and cr.target_type != "*":
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="COMPATIBILITY",
                    target=cr.rule_id,
                    message=f"Compatibility rule target '{cr.target_type}' is undefined.",
                    recommendation=f"Define '{cr.target_type}' in entity_types."
                ))

            if not cr.conditions:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="COMPATIBILITY",
                    target=cr.rule_id,
                    message=f"Compatibility rule '{cr.name}' has no conditions.",
                    recommendation="Add at least one evaluation condition."
                ))

    @classmethod
    def _check_page_types(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        known_ents = set(spec.entity_types)
        for pt in spec.page_types:
            for req_ent in pt.required_entities:
                if req_ent not in known_ents:
                    issues.append(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category="PAGE_TYPE",
                        target=pt.page_type_id,
                        message=f"Page type '{pt.name}' requires undefined entity '{req_ent}'.",
                        recommendation=f"Define '{req_ent}' in entity_types or update page type."
                    ))

            if pt.minimum_evidence_claims < 1:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category="PAGE_TYPE",
                    target=pt.page_type_id,
                    message=f"Page type '{pt.name}' requires 0 evidence claims.",
                    recommendation="Enforce at least 1 evidence claim to prevent ungrounded filler content."
                ))

    @classmethod
    def _check_sources(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        if not spec.source_policies:
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category="SOURCE_POLICY",
                target="source_policies",
                message="No explicit source priority policies configured.",
                recommendation="Configure source hierarchy (Manufacturer, Official, Retailer) to govern evidence authority."
            ))

    @classmethod
    def _check_capabilities(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        if CapabilityType.COMPATIBILITY in spec.capabilities and not spec.compatibility_rules:
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category="CAPABILITY",
                target="COMPATIBILITY",
                message="COMPATIBILITY capability enabled, but no compatibility rules defined.",
                recommendation="Define at least one compatibility rule or disable capability."
            ))

        if CapabilityType.CALCULATION in spec.capabilities and not spec.calculations:
            issues.append(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category="CAPABILITY",
                target="CALCULATION",
                message="CALCULATION capability enabled, but no calculations defined.",
                recommendation="Define at least one calculation formula or disable capability."
            ))

    @classmethod
    def _check_risk_profile(cls, spec: NicheSpec, issues: List[ValidationIssue]):
        if spec.risk_profile == RiskProfile.HIGH:
            if not spec.content_policy.human_review_required:
                issues.append(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="RISK_PROFILE",
                    target="human_review_required",
                    message="High-risk niches must mandate human review before publishing.",
                    recommendation="Set content_policy.human_review_required = True."
                ))
