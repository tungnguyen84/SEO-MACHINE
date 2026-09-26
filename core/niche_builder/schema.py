"""
Declarative Niche Configuration & SaaS Site Schemas
Complete Pydantic models for no-code niche modeling, draft review,
attribute building, relationships, safe calculations, rules, policies, and site lifecycle.
"""

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict

from core.niche_adapters.base_adapter import (
    RiskProfile,
    SourceType,
    ProvenanceClass,
    PageType,
    IntentType,
    FreshnessPolicyType,
)


class DataType(str, Enum):
    """Supported attribute data types in No-Code Niche Builder."""
    STRING = "STRING"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    ENUM = "ENUM"
    DATE = "DATE"
    URL = "URL"
    MONEY = "MONEY"
    DIMENSION = "DIMENSION"
    POWER = "POWER"
    ENERGY = "ENERGY"
    PERCENTAGE = "PERCENTAGE"


class CapabilityType(str, Enum):
    """Platform capabilities user can toggle for a niche."""
    COMPATIBILITY = "COMPATIBILITY"
    CALCULATION = "CALCULATION"
    COMPARISON = "COMPARISON"
    PRODUCT_DATABASE = "PRODUCT_DATABASE"
    TECHNICAL_SPECS = "TECHNICAL_SPECS"
    AFFILIATE_COMMERCE = "AFFILIATE_COMMERCE"
    TEMPORAL_DATA = "TEMPORAL_DATA"
    LOCATION_DATA = "LOCATION_DATA"


class SiteLifecycleStatus(str, Enum):
    """Strict lifecycle progression for SaaS sites."""
    DRAFT = "DRAFT"
    CONFIGURING = "CONFIGURING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class PermissionRole(str, Enum):
    """SaaS user access control roles."""
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class AttributeSpec(BaseModel):
    """Specification of an entity attribute created via No-Code UI."""
    key: str
    display_name: str
    data_type: DataType = DataType.FLOAT
    unit: Optional[str] = None
    required: bool = False
    critical: bool = False
    freshness_policy: FreshnessPolicyType = FreshnessPolicyType.SEMI_DYNAMIC
    preferred_source_type: SourceType = SourceType.MANUFACTURER
    validation_rule: Optional[str] = None
    description: Optional[str] = None


class RelationshipSpec(BaseModel):
    """Directional or bidirectional semantic link between two entity types."""
    source_entity: str
    relationship: str  # e.g., "uses", "suitable_for", "accepts", "mounts_to"
    target_entity: str
    description: Optional[str] = None
    bidirectional: bool = False


class ConditionSpec(BaseModel):
    """Atomic condition for visual compatibility evaluation."""
    subject_attribute: str
    operator: str  # ==, !=, >, >=, <, <=, IN, RANGE, CONTAINS
    target_attribute: Optional[str] = None
    constant_value: Optional[Any] = None
    tolerance: float = 0.0


class ProvenanceType(str, Enum):
    """Allowed provenance classes for calculations and rules."""
    OFFICIAL_STANDARD = "OFFICIAL_STANDARD"
    MANUFACTURER = "MANUFACTURER"
    INDEPENDENT = "INDEPENDENT"
    DERIVED = "DERIVED"
    USER_DEFINED = "USER_DEFINED"
    MODEL_PROPOSED = "MODEL_PROPOSED"


class CompatibilityRuleSpec(BaseModel):
    """Visual no-code compatibility rule specification."""
    rule_id: str
    name: str
    subject_type: str
    target_type: str
    conditions: List[ConditionSpec] = Field(default_factory=list)
    condition_logic: str = "AND"  # AND | OR
    pass_verdict: str = "PASS"
    pass_status: str = "EXACT_FIT"
    fail_verdict: str = "FAIL"
    fail_status: str = "DOES_NOT_FIT"
    explanation_pass: str = "Verified compatible fitment."
    explanation_fail: str = "Physical or operational specifications do not match."
    provenance_type: str = "MODEL_PROPOSED"
    source_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.70
    assumptions: List[str] = Field(default_factory=list)


class CalculationSpec(BaseModel):
    """Declarative safe formula calculation definition."""
    id: str
    name: str
    formula: str
    output_unit: str = ""
    output_description: str = ""
    required_variables: List[str] = Field(default_factory=list)
    display_template: Optional[str] = None
    provenance_type: str = "MODEL_PROPOSED"
    source_ids: List[str] = Field(default_factory=list)
    confidence: float = 0.70
    assumptions: List[str] = Field(default_factory=list)
    version: str = "1.0.0"


class SourcePolicySpec(BaseModel):
    """Source authority hierarchy policy."""
    source_type: SourceType
    priority: int = 3  # 1 = Highest, 5 = Lowest
    allowed_for_critical_facts: bool = True
    freshness_interval_days: int = 180
    requires_secondary_verification: bool = False


class PageTypeSpec(BaseModel):
    """Strategy configuration for a specific page archetype."""
    page_type_id: str  # e.g., "entity_hub", "compatibility", "calculator"
    name: str
    primary_intent: IntentType = IntentType.INFORMATIONAL
    required_entities: List[str] = Field(default_factory=list)
    required_attributes: List[str] = Field(default_factory=list)
    minimum_evidence_claims: int = 1
    monetization_allowed: bool = True
    schema_type: str = "Article"
    indexability_requirements: str = "INDEX"


class ContentPolicySpec(BaseModel):
    """Per-site editorial and brand guidelines."""
    tone: str = "objective_engineering"
    audience: str = "buyers_and_enthusiasts"
    reading_level: str = "grade_10"
    answer_first: bool = True
    citation_style: str = "bracket_provenance"
    affiliate_disclosure: str = "Standard FTC disclosure."
    brand_voice: str = "authoritative_measured"
    forbidden_claims: List[str] = Field(default_factory=list)
    forbidden_phrases: List[str] = Field(default_factory=list)
    human_review_required: bool = False


class NicheVersionSpec(BaseModel):
    """Version metadata tracking schema iterations."""
    version: str = "1.0.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    changes: List[str] = Field(default_factory=list)
    migration_required: bool = False


class NicheSpec(BaseModel):
    """Complete declarative canonical schema for a domain niche."""
    niche_id: str
    niche_name: str
    niche_description: str
    version: str = "1.0.0"
    risk_profile: RiskProfile = RiskProfile.LOW
    capabilities: List[CapabilityType] = Field(default_factory=lambda: [
        CapabilityType.PRODUCT_DATABASE,
        CapabilityType.TECHNICAL_SPECS
    ])
    entity_types: List[str] = Field(default_factory=list)
    attributes: Dict[str, List[AttributeSpec]] = Field(default_factory=dict)
    relationships: List[RelationshipSpec] = Field(default_factory=list)
    calculations: List[CalculationSpec] = Field(default_factory=list)
    compatibility_rules: List[CompatibilityRuleSpec] = Field(default_factory=list)
    source_policies: List[SourcePolicySpec] = Field(default_factory=list)
    page_types: List[PageTypeSpec] = Field(default_factory=list)
    content_policy: ContentPolicySpec = Field(default_factory=ContentPolicySpec)
    intent_taxonomy: Dict[str, List[str]] = Field(default_factory=dict)
    domain_stop_words: List[str] = Field(default_factory=lambda: ["guide", "review", "best", "top", "for", "vs"])
    cluster_differentiators: List[str] = Field(default_factory=list)
    known_competitors: Dict[str, str] = Field(default_factory=dict)
    freshness_rules: List[Dict[str, Any]] = Field(default_factory=list)
    monetization_types: List[str] = Field(default_factory=lambda: ["affiliate_commerce", "display_ads"])
    version_history: List[NicheVersionSpec] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class NicheDraft(BaseModel):
    """AI-proposed niche draft awaiting human review and refinement."""
    draft_id: str
    prompt: str
    proposed_niche: NicheSpec
    ai_rationale: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "PROPOSED"  # PROPOSED | APPROVED | REJECTED


class CredentialField(BaseModel):
    """Masked credential representation for UI display."""
    key: str
    is_set: bool
    masked_value: str


class SiteCreationRequest(BaseModel):
    """Wizard request for Step 1 & 2."""
    site_name: str
    domain: str
    country: str = "US"
    language: str = "en"
    target_market: str = "US"
    currency: str = "USD"
    timezone_str: str = "America/New_York"
    business_model: str = "Affiliate"  # Affiliate | Display Ads | Lead Generation | Ecommerce | Mixed
    niche_option: str = "create_new"   # existing_template | create_new
    existing_niche_id: Optional[str] = None
    natural_language_prompt: Optional[str] = None
