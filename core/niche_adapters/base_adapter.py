"""
Generic Niche Adapter Contract & Capability Framework
Defines the base interface for domain adapters in OpenSEO Multi-Niche Data Authority SaaS.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Set
from pydantic import BaseModel, Field, ConfigDict


class Capability(str, Enum):
    """Platform capabilities that a niche may utilize."""
    COMPATIBILITY = "COMPATIBILITY"
    CALCULATION = "CALCULATION"
    COMPARISON = "COMPARISON"
    PRODUCT_DATABASE = "PRODUCT_DATABASE"
    LOCATION = "LOCATION"
    TEMPORAL_DATA = "TEMPORAL_DATA"
    TECHNICAL_SPECS = "TECHNICAL_SPECS"
    USER_GENERATED_EVIDENCE = "USER_GENERATED_EVIDENCE"
    AFFILIATE_COMMERCE = "AFFILIATE_COMMERCE"


class RiskProfile(str, Enum):
    """Safety and strictness level for quality gates."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SourceType(str, Enum):
    """Standard, niche-independent source authority classifications."""
    OFFICIAL = "OFFICIAL"
    MANUFACTURER = "MANUFACTURER"
    DOCUMENTATION = "DOCUMENTATION"
    GOVERNMENT = "GOVERNMENT"
    CERTIFICATION = "CERTIFICATION"
    RETAILER = "RETAILER"
    EDITORIAL = "EDITORIAL"
    COMMUNITY = "COMMUNITY"
    FORUM = "FORUM"
    SOCIAL = "SOCIAL"
    OTHER = "OTHER"


class ProvenanceClass(str, Enum):
    """Standard ground-truth provenance classes."""
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    INDEPENDENT_MEASURED = "INDEPENDENT_MEASURED"
    OWNER_REPORTED = "OWNER_REPORTED"
    CALCULATED = "CALCULATED"
    MODELLED = "MODELLED"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class PageType(str, Enum):
    """Universal page archetypes for content generation and architecture."""
    ENTITY_HUB = "ENTITY_HUB"
    COMPARISON = "COMPARISON"
    COMPATIBILITY = "COMPATIBILITY"
    PROBLEM_SOLUTION = "PROBLEM_SOLUTION"
    DATA_GUIDE = "DATA_GUIDE"
    COMPLETE_SETUP = "COMPLETE_SETUP"
    CALCULATOR = "CALCULATOR"
    COMMERCIAL_GUIDE = "COMMERCIAL_GUIDE"
    CUSTOM = "CUSTOM"


class IntentType(str, Enum):
    """Search intent taxonomy."""
    DISCOVERY = "DISCOVERY"
    INFORMATIONAL = "INFORMATIONAL"
    PROBLEM_SOLUTION = "PROBLEM_SOLUTION"
    COMPATIBILITY = "COMPATIBILITY"
    COMMERCIAL_INVESTIGATION = "COMMERCIAL_INVESTIGATION"
    COMPARISON = "COMPARISON"
    TRANSACTIONAL = "TRANSACTIONAL"
    SETUP = "SETUP"
    UTILITY = "UTILITY"


class FreshnessPolicyType(str, Enum):
    """Freshness decay velocity."""
    STATIC = "STATIC"
    SEMI_DYNAMIC = "SEMI_DYNAMIC"
    DYNAMIC = "DYNAMIC"
    SEARCH_DATA = "SEARCH_DATA"
    PERFORMANCE_DATA = "PERFORMANCE_DATA"


class AttributeDefinition(BaseModel):
    """Metadata schema defining an attribute in a domain."""
    key: str
    display_name: str
    data_type: str = "numeric"  # numeric, text, boolean, json
    unit_type: Optional[str] = None
    required: bool = False
    criticality: str = "NORMAL"  # CRITICAL, IMPORTANT, NORMAL
    validation_rule: Optional[str] = None
    freshness_policy: FreshnessPolicyType = FreshnessPolicyType.SEMI_DYNAMIC
    refresh_interval_days: int = 180
    source_priority: int = 3
    description: Optional[str] = None


class RelationshipDefinition(BaseModel):
    """Specification of entity relationship within a niche."""
    rel_type: str
    source_entity_type: str
    target_entity_type: str
    description: Optional[str] = None


class CalculationDefinition(BaseModel):
    """Formal schema for mathematical or physical domain calculations."""
    calculation_id: str
    adapter_id: str
    name: str
    required_inputs: List[str]
    optional_inputs: List[str] = Field(default_factory=list)
    formula_version: str = "1.0"
    executor: Optional[Callable[..., Dict[str, Any]]] = None
    output_schema: Dict[str, str] = Field(default_factory=dict)
    uncertainty_rules: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CompatibilityRule(BaseModel):
    """Generic rule definition evaluated by CompatibilityEngine."""
    rule_id: str
    name: str
    subject_type: str
    target_type: str
    evaluator: Optional[Callable[[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]]], Dict[str, Any]]] = None
    explanation_template: str = "{subject} compatibility with {target}: {status}"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PageBlueprint(BaseModel):
    """Template for generating a page plan."""
    page_type: PageType
    title_pattern: str
    required_sections: List[str]
    primary_intent: IntentType
    schema_type: str = "Article"


class NicheAdapter(ABC):
    """
    Abstract Base Class for all domain-specific niche knowledge adapters.
    Injects ontology, calculation rules, compatibility heuristics, and quality checks.
    """

    @property
    @abstractmethod
    def niche_id(self) -> str:
        """Unique machine identifier (e.g., 'vehicle_camping', 'coffee_equipment')."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name (e.g. 'Coffee Equipment & Espresso Brewing')."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> List[Capability]:
        """List of platform capabilities enabled for this niche."""
        pass

    @property
    def risk_profile(self) -> RiskProfile:
        """Safety rating defining strictness of quality gates."""
        return RiskProfile.LOW

    @property
    @abstractmethod
    def entity_types(self) -> List[str]:
        """List of valid entity type identifiers in this niche."""
        pass

    @property
    @abstractmethod
    def attribute_definitions(self) -> Dict[str, List[AttributeDefinition]]:
        """Map of entity_type -> list of AttributeDefinition."""
        pass

    @property
    def relationship_types(self) -> List[RelationshipDefinition]:
        """List of supported relationship schemas between entities."""
        return []

    @property
    def source_priorities(self) -> Dict[SourceType, int]:
        """Prioritization of source types (1 = highest priority)."""
        return {
            SourceType.OFFICIAL: 1,
            SourceType.MANUFACTURER: 2,
            SourceType.DOCUMENTATION: 2,
            SourceType.GOVERNMENT: 2,
            SourceType.CERTIFICATION: 3,
            SourceType.RETAILER: 4,
            SourceType.EDITORIAL: 5,
            SourceType.COMMUNITY: 6,
            SourceType.FORUM: 6,
            SourceType.SOCIAL: 7,
            SourceType.OTHER: 8
        }

    @property
    def source_discovery_rules(self) -> Dict[str, Any]:
        """Rules for crawling and verifying sources (domains, TLDs, query patterns)."""
        return {}

    @property
    def compatibility_rules(self) -> List[CompatibilityRule]:
        """List of domain compatibility rules to register."""
        return []

    @property
    def calculation_definitions(self) -> List[CalculationDefinition]:
        """List of calculators to register with CalculationRegistry."""
        return []

    @property
    def page_blueprints(self) -> List[PageBlueprint]:
        """Page blueprints supported by PagePlanner for this niche."""
        return []

    @property
    def intent_taxonomy(self) -> Dict[str, List[str]]:
        """Domain-specific intent classification keywords."""
        return {}

    @property
    def quality_requirements(self) -> Dict[str, Any]:
        """Custom quality thresholds and forbidden claims."""
        return {
            "min_pass_score": 80.0,
            "forbidden_claims": [],
            "required_evidence_types": [SourceType.MANUFACTURER.value, SourceType.OFFICIAL.value]
        }

    @property
    def freshness_policies(self) -> Dict[str, FreshnessPolicyType]:
        """Map of attribute key -> FreshnessPolicyType."""
        return {}

    @property
    def schema_mapping(self) -> Dict[str, str]:
        """JSON-LD schema mapping per entity or page type."""
        return {}

    @property
    def monetization_types(self) -> List[str]:
        """Monetization mechanisms (e.g., 'affiliate', 'lead_gen', 'sponsorship')."""
        return ["affiliate"]

    # --- Domain Hooks ---

    def seed_default_entities(self) -> int:
        """Seeds canonical benchmark entities into database."""
        return 0

    def get_required_specs(self, entity_type: str) -> List[str]:
        """Returns mandatory technical spec keys for an entity type."""
        defs = self.attribute_definitions.get(entity_type, [])
        return [d.key for d in defs if d.required or d.criticality == "CRITICAL"]

    def normalize_entity_attributes(self, entity_type: str, raw_attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Performs domain-specific attribute normalization and conversion."""
        return raw_attrs

    def get_writer_system_prompt(self, page_plan: Dict[str, Any]) -> str:
        """Returns domain-tailored instructions for GroundedWriter."""
        return f"You are a technical editor for {self.name}. Ground all statements in verified database facts."

    def get_lead_summary(self, primary_entity: Dict[str, Any], model: str, keyword: str) -> str:
        """Generates executive summary lead sentence for GroundedWriter."""
        brand = primary_entity.get("brand", "Subject")
        return f"When evaluating the **{brand} {model}**, verified engineering specifications and dimensional compatibility are critical."

    def get_domain_stop_words(self) -> Set[str]:
        """Stop words specific to this domain during keyword clustering."""
        return set()

    def get_cluster_differentiators(self) -> Set[str]:
        """Key tokens that must NOT be collapsed during keyword clustering."""
        return set()

    def get_semantic_synonyms(self) -> Dict[str, str]:
        """Normalization dictionary for domain synonyms (e.g. {'espresso machine': 'machine'})."""
        return {}

    def get_known_competitors(self) -> Dict[str, str]:
        """Domain to competitor type mapping (e.g. {'specialtycoffee.com': 'EDITORIAL'})."""
        return {}

    # Backward compatibility with BaseNicheAdapter
    def get_niche_name(self) -> str:
        return self.name


# Alias for backward compatibility
BaseNicheAdapter = NicheAdapter
