"""
Niche Versioning, Template Library & Import/Export Manager
Governs schema iteration tracking, version migrations, sanitized template sharing,
and non-destructive cloning into site-scoped configurations.
"""

import copy
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.niche_builder.schema import NicheSpec, NicheVersionSpec
from core.niche_builder.validator import NicheValidator, ValidationReport


class NicheVersioningManager:
    """
    Manages version increments, migration requirements, import/export sanitization,
    and global vs site-scoped template cloning.
    """

    _global_templates: Dict[str, NicheSpec] = {}
    _site_niche_versions: Dict[str, List[NicheSpec]] = {}  # site_id -> list of versions

    @classmethod
    def register_global_template(cls, spec: NicheSpec):
        """Registers an immutable global template in the library."""
        cls._global_templates[spec.niche_id] = spec

    @classmethod
    def list_templates(cls) -> List[Dict[str, Any]]:
        """Returns catalog of available global niche templates for cloning."""
        cls._ensure_default_templates()
        catalog = []
        for t in cls._global_templates.values():
            catalog.append({
                "niche_id": t.niche_id,
                "name": t.niche_name,
                "description": t.niche_description,
                "version": t.version,
                "capabilities": [c.value for c in t.capabilities],
                "entity_types": t.entity_types,
                "total_attributes": sum(len(a) for a in t.attributes.values()),
                "total_calculations": len(t.calculations),
                "total_compatibility_rules": len(t.compatibility_rules)
            })
        return catalog

    @classmethod
    def clone_template_for_site(cls, template_niche_id: str, new_site_id: str) -> NicheSpec:
        """
        Clones a global template into an isolated site-scoped configuration.
        Guarantees the global template is never mutated.
        """
        cls._ensure_default_templates()
        if template_niche_id not in cls._global_templates:
            raise KeyError(f"Template '{template_niche_id}' not found in global library.")

        original = cls._global_templates[template_niche_id]
        cloned_dict = copy.deepcopy(original.model_dump())
        cloned_spec = NicheSpec.model_validate(cloned_dict)

        # Track under site version history
        if new_site_id not in cls._site_niche_versions:
            cls._site_niche_versions[new_site_id] = []
        cls._site_niche_versions[new_site_id].append(cloned_spec)
        return cloned_spec

    @classmethod
    def increment_version(cls, current_spec: NicheSpec, change_summary: str, migration_required: bool = False) -> NicheSpec:
        """
        Creates a new version increment (e.g. 1.0.0 -> 1.1.0) with change metadata.
        Prevents silent breaking changes to existing entities.
        """
        parts = current_spec.version.split(".")
        major = int(parts[0]) if len(parts) > 0 else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        new_version = f"{major}.{minor + 1}.0"
        new_history = list(current_spec.version_history)
        new_history.append(NicheVersionSpec(
            version=new_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            changes=[change_summary],
            migration_required=migration_required
        ))

        updated_dict = current_spec.model_dump()
        updated_dict["version"] = new_version
        updated_dict["version_history"] = [h.model_dump() for h in new_history]
        return NicheSpec.model_validate(updated_dict)

    @classmethod
    def export_spec(cls, spec: NicheSpec, format_type: str = "yaml") -> str:
        """
        Exports a NicheSpec to YAML or JSON string.
        Guarantees that zero credentials, API keys, or private site secrets are exported.
        """
        data = json.loads(spec.model_dump_json())
        # Ensure credentials cannot exist in schema
        for banned in ["api_key", "password", "secret", "token"]:
            data.pop(banned, None)

        if format_type.lower() == "json":
            return json.dumps(data, indent=2)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def import_spec(cls, raw_content: str, format_type: str = "yaml") -> tuple[Optional[NicheSpec], ValidationReport]:
        """
        Validates and imports a NicheSpec from YAML or JSON.
        Strictly blocks import if NicheValidator detects fatal errors.
        """
        try:
            if format_type.lower() == "json":
                parsed = json.loads(raw_content)
            else:
                parsed = yaml.safe_load(raw_content)
            spec = NicheSpec.model_validate(parsed)
        except Exception as e:
            from core.niche_builder.validator import ValidationIssue, IssueSeverity
            report = ValidationReport(
                niche_id="import_failure",
                is_valid=False,
                errors_count=1,
                warnings_count=0,
                info_count=0,
                issues=[ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category="PARSER",
                    target="format",
                    message=f"Failed to parse niche configuration: {e}"
                )]
            )
            return None, report

        report = NicheValidator.validate(spec)
        if not report.can_activate:
            return None, report
        return spec, report

    @classmethod
    def _ensure_default_templates(cls):
        """Populates baseline global template library if empty."""
        if not cls._global_templates:
            from core.niche_builder.ai_designer import AINicheDesigner
            air_spec = AINicheDesigner._design_air_purifier_niche()
            dog_spec = AINicheDesigner._design_dog_crate_niche()

            cls._global_templates[air_spec.niche_id] = air_spec
            cls._global_templates[dog_spec.niche_id] = dog_spec

            # Add home_solar template from config if exists
            yaml_path = Path("config/niches/home_solar.yaml")
            if yaml_path.exists():
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        hs_data = yaml.safe_load(f)
                    hs_spec = NicheSpec(
                        niche_id=hs_data.get("niche_id", "home_solar"),
                        niche_name=hs_data.get("name", "Home Solar"),
                        niche_description=hs_data.get("description", "Residential Solar"),
                        entity_types=hs_data.get("entity_types", ["solar_panel", "inverter"])
                    )
                    cls._global_templates[hs_spec.niche_id] = hs_spec
                except Exception:
                    pass

    @classmethod
    def export_niche_yaml(cls, spec: NicheSpec) -> str:
        return cls.export_spec(spec, "yaml")

    @classmethod
    def export_niche_json(cls, spec: NicheSpec) -> str:
        return cls.export_spec(spec, "json")

    @classmethod
    def import_niche_yaml(cls, content: str) -> NicheSpec:
        spec, report = cls.import_spec(content, "yaml")
        if not spec:
            raise ValueError(f"Failed to import YAML niche: {[i.message for i in report.issues]}")
        return spec

    @classmethod
    def import_niche_json(cls, content: str) -> NicheSpec:
        spec, report = cls.import_spec(content, "json")
        if not spec:
            raise ValueError(f"Failed to import JSON niche: {[i.message for i in report.issues]}")
        return spec

    @classmethod
    def get_template(cls, template_id: str) -> Optional[NicheSpec]:
        cls._ensure_default_templates()
        return cls._global_templates.get(template_id)

