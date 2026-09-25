"""
Niche Adapter Registry
Central catalog for discovering, registering, and activating niche adapters.
"""
from typing import Dict, List, Optional
from core.niche_adapters.base_adapter import NicheAdapter

class NicheRegistry:
    """Singleton/class-level registry of active and configured niche adapters."""
    _adapters: Dict[str, NicheAdapter] = {}
    _active_niche_id: Optional[str] = None

    @classmethod
    def register(cls, adapter: NicheAdapter, make_active: bool = False):
        """Registers a niche adapter and its compatibility rules."""
        cls._adapters[adapter.niche_id] = adapter
        if make_active or cls._active_niche_id is None:
            cls._active_niche_id = adapter.niche_id

        # Auto-register adapter's compatibility rules into CompatibilityRuleEngine
        try:
            from core.engine.compatibility import CompatibilityRuleEngine
            for rule in getattr(adapter, "compatibility_rules", []):
                CompatibilityRuleEngine.register_rule(rule)
        except Exception:
            pass

    @classmethod
    def _ensure_loaded(cls):
        if not cls._adapters:
            try:
                import core.niche_adapters.vehicle_camping
            except Exception:
                pass

    @classmethod
    def get(cls, niche_id: str) -> Optional[NicheAdapter]:
        """Retrieves an adapter by niche_id."""
        cls._ensure_loaded()
        return cls._adapters.get(niche_id)

    @classmethod
    def list_all(cls) -> List[NicheAdapter]:
        """Lists all registered adapters."""
        cls._ensure_loaded()
        return list(cls._adapters.values())

    get_all = list_all

    @classmethod
    def get_active(cls) -> Optional[NicheAdapter]:
        """Retrieves currently active adapter."""
        cls._ensure_loaded()
        if cls._active_niche_id:
            return cls._adapters.get(cls._active_niche_id)
        if cls._adapters:
            return next(iter(cls._adapters.values()))
        return None

    @classmethod
    def set_active(cls, niche_id: str):
        """Sets the active adapter."""
        if niche_id not in cls._adapters:
            raise KeyError(f"Niche adapter '{niche_id}' is not registered.")
        cls._active_niche_id = niche_id

    @classmethod
    def clear(cls):
        """Resets registry (mainly for testing)."""
        cls._adapters.clear()
        cls._active_niche_id = None
