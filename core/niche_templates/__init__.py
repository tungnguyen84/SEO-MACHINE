"""
Explicit Niche Templates Registry
Hosts pre-configured, declarative niche templates for preset site initialization and testing.
Isolated from generic core reasoning engines.
"""
from typing import Dict, Optional
from core.niche_builder.schema import NicheSpec
from core.niche_templates.air_purifiers import get_air_purifier_template
from core.niche_templates.dog_crates import get_dog_crate_template
from core.niche_templates.dehumidifiers import get_dehumidifier_template

NICHE_TEMPLATES: Dict[str, NicheSpec] = {
    "air_purifiers": get_air_purifier_template(),
    "dog_crates": get_dog_crate_template(),
    "home_dehumidifiers": get_dehumidifier_template(),
}

def get_template_by_id(niche_id: str) -> Optional[NicheSpec]:
    """Retrieve pre-configured template by niche ID."""
    return NICHE_TEMPLATES.get(niche_id)
