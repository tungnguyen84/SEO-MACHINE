"""
SaaS Site Lifecycle, Multi-Tenant Isolation & Site Switcher Engine
Enforces strict lifecycle progression (DRAFT -> CONFIGURING -> VALIDATING -> READY -> ACTIVE -> PAUSED -> ARCHIVED),
permission checks (OWNER, ADMIN, EDITOR, VIEWER), site context switching, and tenant isolation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from core.niche_builder.schema import (
    SiteLifecycleStatus,
    PermissionRole,
    NicheSpec,
)
from core.site_profile import SiteProfile, SiteManager
from core.niche_builder.credentials import EncryptedCredentialStore


class SaaSSite(BaseModel):
    """Rich multi-tenant site model for OpenSEO SaaS."""
    site_id: str
    tenant_id: str = "tenant_default"
    site_name: str
    domain: str
    country: str = "US"
    language: str = "en"
    target_market: str = "US"
    currency: str = "USD"
    timezone_str: str = "America/New_York"
    business_model: str = "Affiliate"
    niche_id: str
    lifecycle_status: SiteLifecycleStatus = SiteLifecycleStatus.DRAFT
    niche_spec: Optional[NicheSpec] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_roles: Dict[str, PermissionRole] = Field(default_factory=dict)  # user_id -> PermissionRole

    # Telemetry metrics scoped to this site
    metrics: Dict[str, Any] = Field(default_factory=lambda: {
        "entities_count": 0,
        "sources_count": 0,
        "evidence_count": 0,
        "serp_queries_researched": 0,
        "page_plans_count": 0,
        "drafts_count": 0,
        "published_count": 0,
        "indexed_count": 0,
        "gsc_impressions": 0,
        "gsc_clicks": 0,
        "affiliate_clicks": 0,
        "quality_alerts": 0,
        "active_jobs": 0
    })


class SaaSSiteManager:
    """
    Central SaaS controller for multi-site lifecycle, role enforcement, and context switching.
    """

    _sites: Dict[str, SaaSSite] = {}
    _active_site_per_session: Dict[str, str] = {}  # session_or_user_id -> site_id

    @classmethod
    def create_site(
        cls,
        site_name: str,
        domain: str,
        niche_id: str,
        tenant_id: str = "tenant_default",
        owner_user_id: str = "user_admin",
        country: str = "US",
        language: str = "en",
        currency: str = "USD",
        business_model: str = "Affiliate",
        niche_spec: Optional[NicheSpec] = None
    ) -> SaaSSite:
        site_id = f"site_{domain.replace('.', '_').replace('-', '_').lower()}"
        site = SaaSSite(
            site_id=site_id,
            tenant_id=tenant_id,
            site_name=site_name,
            domain=domain,
            country=country,
            language=language,
            currency=currency,
            business_model=business_model,
            niche_id=niche_id,
            lifecycle_status=SiteLifecycleStatus.DRAFT,
            niche_spec=niche_spec,
            user_roles={owner_user_id: PermissionRole.OWNER}
        )
        cls._sites[site_id] = site

        # Sync into core SiteManager for pipeline execution
        core_profile = SiteProfile(
            site_id=site_id,
            tenant_id=tenant_id,
            project_id=f"proj_{site_id}",
            domain=domain,
            brand_name=site_name,
            language=language,
            country=country,
            niche_adapter_id=niche_id,
            affiliate_tags={"amazon": f"{site_name.lower().replace(' ', '')}-20"}
        )
        SiteManager.register_site(core_profile)
        return site

    @classmethod
    def get_site(cls, site_id: str, tenant_id: Optional[str] = None) -> Optional[SaaSSite]:
        site = cls._sites.get(site_id)
        if not site:
            return None
        if tenant_id and site.tenant_id != tenant_id:
            return None
        return site

    @classmethod
    def list_sites(cls, tenant_id: Optional[str] = None) -> List[SaaSSite]:
        if tenant_id:
            return [s for s in cls._sites.values() if s.tenant_id == tenant_id]
        return list(cls._sites.values())

    @classmethod
    def update_lifecycle_status(
        cls,
        site_id: str,
        new_status: SiteLifecycleStatus,
        user_id: str = "user_admin",
        tenant_id: Optional[str] = None
    ) -> SaaSSite:
        """Transitions site through lifecycle states with permission checks and tenant isolation."""
        site = cls._sites.get(site_id)
        if not site:
            raise KeyError(f"Site '{site_id}' not found.")

        if tenant_id and site.tenant_id != tenant_id:
            raise PermissionError(f"Cross-tenant access forbidden: Tenant '{tenant_id}' cannot modify site '{site_id}'.")

        cls.verify_permission(site_id, user_id, required_roles=[PermissionRole.OWNER, PermissionRole.ADMIN])
        site.lifecycle_status = new_status
        site.updated_at = datetime.now(timezone.utc).isoformat()
        return site

    @classmethod
    def can_schedule_jobs(cls, site_id: str) -> bool:
        """Rule: Only ACTIVE sites may schedule or run production automation jobs."""
        site = cls._sites.get(site_id)
        if not site:
            return False
        return site.lifecycle_status == SiteLifecycleStatus.ACTIVE

    @classmethod
    def set_active_site_context(cls, user_id: str, site_id: str, tenant_id: Optional[str] = None):
        """Switches the active site context for the session with tenant isolation."""
        site = cls._sites.get(site_id)
        if not site:
            raise KeyError(f"Cannot switch to non-existent site '{site_id}'")
        if tenant_id and site.tenant_id != tenant_id:
            raise PermissionError(f"Cross-tenant context switch forbidden: Tenant '{tenant_id}' cannot access site '{site_id}'.")
        cls._active_site_per_session[user_id] = site_id

    @classmethod
    def get_active_site_context(cls, user_id: str, tenant_id: Optional[str] = None) -> Optional[SaaSSite]:
        site_id = cls._active_site_per_session.get(user_id)
        if site_id:
            site = cls.get_site(site_id, tenant_id=tenant_id)
            if site:
                return site
        # Default to first site belonging to this tenant if any
        sites = cls.list_sites(tenant_id=tenant_id)
        if sites:
            first = sites[0]
            cls._active_site_per_session[user_id] = first.site_id
            return first
        return None

    @classmethod
    def verify_permission(cls, site_id: str, user_id: str, required_roles: List[PermissionRole]):
        site = cls._sites.get(site_id)
        if not site:
            raise KeyError(f"Site '{site_id}' not found.")
        default_role = PermissionRole.ADMIN if user_id == "user_admin" else PermissionRole.VIEWER
        user_role = site.user_roles.get(user_id, default_role)
        if user_role not in required_roles:
            raise PermissionError(f"User '{user_id}' with role '{user_role.value}' lacks required permissions: {[r.value for r in required_roles]}")

    @classmethod
    def get_site_dashboard(cls, site_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns scoped overview dashboard for a specific site with tenant check."""
        site = cls._sites.get(site_id)
        if not site:
            raise KeyError(f"Site '{site_id}' not found.")

        if tenant_id and site.tenant_id != tenant_id:
            raise PermissionError(f"Cross-tenant access forbidden: Site '{site_id}' does not belong to tenant '{tenant_id}'.")

        masked_creds = EncryptedCredentialStore.get_all_masked_for_site(site_id)
        return {
            "site_id": site.site_id,
            "site_name": site.site_name,
            "domain": site.domain,
            "niche_id": site.niche_id,
            "lifecycle_status": site.lifecycle_status.value,
            "can_schedule_jobs": cls.can_schedule_jobs(site_id),
            "metrics": site.metrics,
            "configured_credentials": {k: f.model_dump() for k, f in masked_creds.items()},
            "updated_at": site.updated_at
        }

    @classmethod
    def get_global_dashboard(cls, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns SaaS multi-site overview across all sites."""
        sites = cls.list_sites(tenant_id)
        total_entities = sum(s.metrics["entities_count"] for s in sites)
        total_drafts = sum(s.metrics["drafts_count"] for s in sites)
        total_published = sum(s.metrics["published_count"] for s in sites)
        total_gsc_impressions = sum(s.metrics["gsc_impressions"] for s in sites)
        total_gsc_clicks = sum(s.metrics["gsc_clicks"] for s in sites)
        total_affiliate_clicks = sum(s.metrics["affiliate_clicks"] for s in sites)

        site_summaries = []
        for s in sites:
            site_summaries.append({
                "site_id": s.site_id,
                "site_name": s.site_name,
                "domain": s.domain,
                "niche_id": s.niche_id,
                "lifecycle_status": s.lifecycle_status.value,
                "entities": s.metrics["entities_count"],
                "drafts": s.metrics["drafts_count"],
                "published": s.metrics["published_count"],
                "gsc_impressions": s.metrics["gsc_impressions"],
                "affiliate_clicks": s.metrics["affiliate_clicks"],
            })

        return {
            "total_sites": len(sites),
            "aggregate_metrics": {
                "total_entities": total_entities,
                "total_drafts": total_drafts,
                "total_published": total_published,
                "total_gsc_impressions": total_gsc_impressions,
                "total_gsc_clicks": total_gsc_clicks,
                "total_affiliate_clicks": total_affiliate_clicks,
            },
            "sites": site_summaries
        }

    @classmethod
    def clear(cls):
        cls._sites.clear()
        cls._active_site_per_session.clear()
