"""
Base Interface for Niche Knowledge Adapters
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseNicheAdapter(ABC):
    """Abstract class for domain knowledge injection and entity seeding."""

    @abstractmethod
    def get_niche_name(self) -> str:
        """Returns the human-readable name of the niche."""
        pass

    @abstractmethod
    def seed_default_entities(self) -> int:
        """Populates the database with verified core entities and specifications."""
        pass

    @abstractmethod
    def get_required_specs(self, entity_type: str) -> List[str]:
        """Returns the list of mandatory technical specifications required for authority rating."""
        pass
