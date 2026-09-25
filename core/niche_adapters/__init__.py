"""
OpenSEO Niche Adapters Module
Domain-specific knowledge bases, vehicle specs, and product seeders.
"""
from .base_adapter import BaseNicheAdapter
from .vehicle_camping import VehicleCampingAdapter

__all__ = ["BaseNicheAdapter", "VehicleCampingAdapter"]
