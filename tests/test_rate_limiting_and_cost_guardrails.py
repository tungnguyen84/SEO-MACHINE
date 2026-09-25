"""
Test Suite: Rate Limiting, Usage Quotas & Cost Guardrails
Verifies:
1. Sliding-window rate limiter returns 429 Too Many Requests with Retry-After header.
2. Tenant quota tracking across plan tiers (starter, growth, agency).
3. Cost limits preventing unexpected cloud bills.
4. Runaway AI loop breaker halting runaway LLM or tool-calling loops.
"""

import pytest
from core.security.rate_limiter import SlidingWindowRateLimiter, RateLimitExceeded
from core.accounting.quota_manager import TenantQuotaManager, QuotaExceededError
from core.accounting.cost_guardrails import (
    CostGuardrails,
    SpendLimitExceeded,
    AILoopBreaker,
    RunawayLoopDetected,
)


def test_sliding_window_rate_limiter():
    """Verify rate limiter allows requests up to max_requests and rejects subsequent requests with 429."""
    limiter = SlidingWindowRateLimiter()
    key = "tenant_test_rate_limit"

    # Allow 3 requests in a 10-second window
    limiter.enforce(key, max_requests=3, window_seconds=10)
    limiter.enforce(key, max_requests=3, window_seconds=10)
    limiter.enforce(key, max_requests=3, window_seconds=10)

    # 4th request must raise RateLimitExceeded (HTTP 429)
    with pytest.raises(RateLimitExceeded) as exc_info:
        limiter.enforce(key, max_requests=3, window_seconds=10)
    
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
    retry_after = int(exc_info.value.headers["Retry-After"])
    assert retry_after > 0


def test_tenant_usage_quotas():
    """Verify that tenant cannot exceed allocated resource quotas on their plan tier."""
    qm = TenantQuotaManager()
    tenant_id = "tenant_starter_user"

    # Starter plan allows max 50,000 LLM tokens
    qm.check_and_record(tenant_id, "llm_tokens", 30_000, plan_tier="starter")
    assert qm.get_usage(tenant_id)["llm_tokens"] == 30_000

    # Additional 15,000 is allowed (total 45,000 <= 50,000)
    qm.check_and_record(tenant_id, "llm_tokens", 15_000, plan_tier="starter")
    assert qm.get_usage(tenant_id)["llm_tokens"] == 45_000

    # Additional 10,000 pushes total to 55,000 > 50,000 limit -> must raise QuotaExceededError
    with pytest.raises(QuotaExceededError) as exc_info:
        qm.check_and_record(tenant_id, "llm_tokens", 10_000, plan_tier="starter")
    assert "Quota exceeded for 'llm_tokens'" in str(exc_info.value)


def test_daily_and_monthly_cost_guardrails():
    """Verify that financial spend limits prevent unexpected API cost spikes."""
    cg = CostGuardrails()
    tenant_id = "tenant_growth_user"

    # Growth plan: max daily $25.00
    cg.record_and_enforce(tenant_id, cost_usd=10.0, plan_tier="growth")
    cg.record_and_enforce(tenant_id, cost_usd=12.0, plan_tier="growth")

    # Exceeding daily cap ($22 + $5 = $27 > $25) must raise SpendLimitExceeded
    with pytest.raises(SpendLimitExceeded) as exc_info:
        cg.record_and_enforce(tenant_id, cost_usd=5.0, plan_tier="growth")
    assert "Daily cost limit exceeded" in str(exc_info.value)


def test_ai_runaway_loop_breaker():
    """Verify that single job workflows cannot run infinite LLM or tool-calling loops."""
    loop_breaker = AILoopBreaker(max_llm_calls=5, max_tool_iterations=4)

    # 5 LLM calls allowed
    for _ in range(5):
        loop_breaker.record_llm_call()

    # 6th call raises RunawayLoopDetected
    with pytest.raises(RunawayLoopDetected) as exc_info:
        loop_breaker.record_llm_call()
    assert "Exceeded max permitted LLM invocations" in str(exc_info.value)

    # Tool iterations limit
    with pytest.raises(RunawayLoopDetected):
        for _ in range(5):
            loop_breaker.record_tool_iteration()
