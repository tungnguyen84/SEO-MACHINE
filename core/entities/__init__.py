"""
OpenSEO Core Entities Module
Standardized Data Model for Products, Vehicles, and Gear
"""
from .models import Entity, EntityAttribute, EntityType
from .normalizer import UnitNormalizer
from .entity_manager import EntityManager

__all__ = ["Entity", "EntityAttribute", "EntityType", "UnitNormalizer", "EntityManager"]
