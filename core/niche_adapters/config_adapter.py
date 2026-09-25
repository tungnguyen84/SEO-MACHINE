"""
Config-Driven Niche Adapter & Creation Wizard
Allows simple niches to be instantiated purely from YAML, JSON, or database configuration.
"""
from typing import Dict, Any, List, Set, Optional
import yaml
import json
from pathlib import Path
from core.niche_adapters.base_adapter import (
    NicheAdapter, Capability, RiskProfile, SourceType,
    ProvenanceClass, PageType, IntentType, FreshnessPolicyType,
    AttributeDefinition, CompatibilityRule, CalculationDefinition, PageBlueprint
)
from core.niche_adapters.registry import NicheRegistry


class ConfigDrivenNicheAdapter(NicheAdapter):
    """Dynamically configured niche adapter loaded from declarative YAML/JSON schemas."""

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._niche_id = config.get("niche_id", "custom_niche")
        self._name = config.get("name", "Custom Niche")
        self._capabilities = [Capability(c) for c in config.get("capabilities", ["PRODUCT_DATABASE", "TECHNICAL_SPECS"])]
        self._risk_profile = RiskProfile(config.get("risk_profile", "LOW"))
        self._entity_types = config.get("entity_types", [])

        # Parse attribute definitions
        self._attribute_definitions: Dict[str, List[AttributeDefinition]] = {}
        for ent_type, attr_list in config.get("attributes", {}).items():
            self._attribute_definitions[ent_type] = []
            for item in attr_list:
                policy = FreshnessPolicyType(item.get("freshness_policy", "SEMI_DYNAMIC"))
                self._attribute_definitions[ent_type].append(
                    AttributeDefinition(
                        key=item["key"],
                        display_name=item.get("display_name", item["key"]),
                        data_type=item.get("data_type", "numeric"),
                        unit_type=item.get("unit_type"),
                        required=item.get("required", False),
                        criticality=item.get("criticality", "NORMAL"),
                        freshness_policy=policy
                    )
                )

        self._intent_taxonomy = config.get("intent_taxonomy", {})
        self._stop_words = set(config.get("domain_stop_words", []))
        self._cluster_differentiators = set(config.get("cluster_differentiators", []))
        self._known_competitors = config.get("known_competitors", {})

    @property
    def niche_id(self) -> str:
        return self._niche_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def capabilities(self) -> List[Capability]:
        return self._capabilities

    @property
    def risk_profile(self) -> RiskProfile:
        return self._risk_profile

    @property
    def entity_types(self) -> List[str]:
        return self._entity_types

    @property
    def attribute_definitions(self) -> Dict[str, List[AttributeDefinition]]:
        return self._attribute_definitions

    @property
    def intent_taxonomy(self) -> Dict[str, List[str]]:
        return self._intent_taxonomy

    def get_domain_stop_words(self) -> Set[str]:
        return self._stop_words

    def get_cluster_differentiators(self) -> Set[str]:
        return self._cluster_differentiators

    def get_known_competitors(self) -> Dict[str, str]:
        return self._known_competitors

    @classmethod
    def from_yaml_file(cls, file_path: str) -> "ConfigDrivenNicheAdapter":
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(data)

    @classmethod
    def from_json_file(cls, file_path: str) -> "ConfigDrivenNicheAdapter":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)


class NicheCreationWizard:
    """Guided programmatic workflow for creating and registering new niches without core code changes."""

    @staticmethod
    def create_niche_template(
        niche_id: str,
        name: str,
        capabilities: List[str],
        entity_types: List[str],
        risk_profile: str = "LOW"
    ) -> Dict[str, Any]:
        """Generates a canonical declarative niche dictionary."""
        return {
            "niche_id": niche_id,
            "name": name,
            "capabilities": capabilities,
            "risk_profile": risk_profile,
            "entity_types": entity_types,
            "attributes": {et: [] for et in entity_types},
            "intent_taxonomy": {},
            "domain_stop_words": ["guide", "review", "best", "setup"],
            "cluster_differentiators": [],
            "known_competitors": {}
        }

    @staticmethod
    def save_to_yaml(config: Dict[str, Any], output_path: str) -> str:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        return output_path
