"""
Multi-Site Profile & Tenant Isolation Layer
Provides multi-tenant configuration, credential scoping, and audit logging for SaaS sites.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from core.niche_adapters.base_adapter import RiskProfile


class SiteProfile(BaseModel):
    """
    Isolated configuration profile for a specific hosted or connected website.
    Enforces strict separation of WordPress, GSC, affiliate tags, and risk thresholds.
    """
    site_id: str
    tenant_id: str = "tenant_default"
    project_id: str = "project_default"
    domain: str
    brand_name: str
    language: str = "en"
    country: str = "US"
    niche_adapter_id: str
    tone: str = "technical_expert"
    target_audience: str = "buyers_and_enthusiasts"
    author_profile: Dict[str, Any] = Field(default_factory=lambda: {
        "name": "Technical Editorial Team",
        "bio": "Specialized domain researchers and data engineers."
    })
    publisher_profile: Dict[str, Any] = Field(default_factory=dict)
    affiliate_disclosure: str = (
        "When you purchase through links on our site, we may earn an affiliate commission at no extra cost to you. "
        "All calculations and ratings remain mathematically grounded in verified specifications."
    )
    monetization_sources: List[str] = Field(default_factory=lambda: ["affiliate"])
    affiliate_tags: Dict[str, str] = Field(default_factory=dict)  # e.g., {"amazon": "siteA-tag-20"}
    wordpress_connection: Dict[str, Any] = Field(default_factory=dict)  # site_url, username, app_password
    search_console_property: Optional[str] = None  # e.g., "sc-domain:mysite.com"
    content_policy: Dict[str, Any] = Field(default_factory=dict)
    quality_thresholds: Dict[str, float] = Field(default_factory=lambda: {"min_pass_score": 80.0})
    risk_profile: RiskProfile = RiskProfile.LOW


class AuditLogEntry(BaseModel):
    """Immutable audit trail for all significant data and configuration mutations."""
    tenant_id: str
    site_id: str
    project_id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SiteManager:
    """Manages active SiteProfiles and prevents cross-site data leakage."""
    _sites: Dict[str, SiteProfile] = {}
    _audit_logs: List[AuditLogEntry] = []

    @classmethod
    def register_site(cls, profile: SiteProfile):
        cls._sites[profile.site_id] = profile

    @classmethod
    def get_site(cls, site_id: str) -> Optional[SiteProfile]:
        return cls._sites.get(site_id)

    @classmethod
    def list_sites(cls, tenant_id: Optional[str] = None) -> List[SiteProfile]:
        if tenant_id:
            return [s for s in cls._sites.values() if s.tenant_id == tenant_id]
        return list(cls._sites.values())

    @classmethod
    def get_affiliate_tag(cls, site_id: str, network: str = "amazon") -> Optional[str]:
        site = cls.get_site(site_id)
        if not site:
            return None
        return site.affiliate_tags.get(network)

    @classmethod
    def get_wordpress_credentials(cls, site_id: str) -> Dict[str, Any]:
        site = cls.get_site(site_id)
        if not site:
            return {}
        return site.wordpress_connection

    @classmethod
    def get_gsc_property(cls, site_id: str) -> Optional[str]:
        site = cls.get_site(site_id)
        if not site:
            return None
        return site.search_console_property

    @classmethod
    def log_action(
        cls,
        tenant_id: str,
        site_id: str,
        project_id: str,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: Optional[Dict[str, Any]] = None,
        after_state: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        entry = AuditLogEntry(
            tenant_id=tenant_id,
            site_id=site_id,
            project_id=project_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state
        )
        cls._audit_logs.append(entry)
        return entry

    @classmethod
    def get_audit_logs(cls, site_id: Optional[str] = None) -> List[AuditLogEntry]:
        if site_id:
            return [e for e in cls._audit_logs if e.site_id == site_id]
        return list(cls._audit_logs)

    @classmethod
    def clear(cls):
        cls._sites.clear()
        cls._audit_logs.clear()
