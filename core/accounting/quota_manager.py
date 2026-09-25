"""
Production SaaS Usage Quota & Resource Accounting Subsystem
Tracks LLM tokens, SERP queries, managed sites, and drafts per tenant.
Enforces hard tier ceilings to eliminate infrastructure cost overruns.
"""

import threading
from typing import Dict, Any, Optional
from pydantic import BaseModel


class QuotaExceededError(Exception):
    """Raised when tenant exhausts allocated resource quota."""
    def __init__(self, resource: str, limit: int, current: int, plan: str):
        super().__init__(
            f"Quota exceeded for '{resource}'. Current: {current}, Limit: {limit} on '{plan}' plan."
        )
        self.resource = resource
        self.limit = limit
        self.current = current
        self.plan = plan


class TierPlanLimits(BaseModel):
    max_sites: int
    max_monthly_llm_tokens: int
    max_monthly_serp_queries: int
    max_daily_spend_usd: float
    max_monthly_spend_usd: float


TIER_LIMITS: Dict[str, TierPlanLimits] = {
    "starter": TierPlanLimits(
        max_sites=1,
        max_monthly_llm_tokens=50_000,
        max_monthly_serp_queries=50,
        max_daily_spend_usd=5.0,
        max_monthly_spend_usd=50.0,
    ),
    "growth": TierPlanLimits(
        max_sites=10,
        max_monthly_llm_tokens=500_000,
        max_monthly_serp_queries=500,
        max_daily_spend_usd=25.0,
        max_monthly_spend_usd=250.0,
    ),
    "agency": TierPlanLimits(
        max_sites=100,
        max_monthly_llm_tokens=5_000_000,
        max_monthly_serp_queries=5_000,
        max_daily_spend_usd=100.0,
        max_monthly_spend_usd=1_000.0,
    ),
}


class TenantQuotaManager:
    """Thread-safe tenant quota enforcement."""

    def __init__(self):
        self._lock = threading.Lock()
        # tenant_id -> {resource_name -> current_usage}
        self._usage: Dict[str, Dict[str, int]] = {}

    def get_limits(self, plan_tier: str) -> TierPlanLimits:
        return TIER_LIMITS.get(plan_tier.lower(), TIER_LIMITS["starter"])

    def record_usage(self, tenant_id: str, resource: str, amount: int):
        with self._lock:
            tenant_record = self._usage.setdefault(tenant_id, {
                "llm_tokens": 0,
                "serp_queries": 0,
                "sites": 0,
                "drafts": 0,
            })
            tenant_record[resource] = tenant_record.get(resource, 0) + amount

    def check_and_record(self, tenant_id: str, resource: str, amount: int, plan_tier: str = "starter"):
        """Checks if usage exceeds tier quota; raises QuotaExceededError if so, otherwise records usage."""
        limits = self.get_limits(plan_tier)
        limit_val = None
        if resource == "llm_tokens":
            limit_val = limits.max_monthly_llm_tokens
        elif resource == "serp_queries":
            limit_val = limits.max_monthly_serp_queries
        elif resource == "sites":
            limit_val = limits.max_sites

        with self._lock:
            tenant_record = self._usage.setdefault(tenant_id, {
                "llm_tokens": 0,
                "serp_queries": 0,
                "sites": 0,
                "drafts": 0,
            })
            current = tenant_record.get(resource, 0)
            if limit_val is not None and (current + amount) > limit_val:
                raise QuotaExceededError(resource, limit_val, current, plan_tier)

            tenant_record[resource] = current + amount

    def get_usage(self, tenant_id: str) -> Dict[str, int]:
        with self._lock:
            return dict(self._usage.get(tenant_id, {
                "llm_tokens": 0,
                "serp_queries": 0,
                "sites": 0,
                "drafts": 0,
            }))

    def reset(self, tenant_id: Optional[str] = None):
        with self._lock:
            if tenant_id:
                self._usage.pop(tenant_id, None)
            else:
                self._usage.clear()


quota_manager = TenantQuotaManager()
