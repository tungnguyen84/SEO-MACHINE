"""
Production Financial Cost Guardrails & AI Runaway Loop Breaker
Monitors real-time API expense per tenant and cuts off runaway loops before large bills accrue.
"""

import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from core.accounting.quota_manager import TIER_LIMITS


class SpendLimitExceeded(Exception):
    """Raised when tenant exceeds daily or monthly monetary budget."""
    pass


class RunawayLoopDetected(Exception):
    """Raised when an AI workflow exceeds safe iteration / invocation thresholds."""
    pass


# Default pricing per unit in USD
UNIT_COSTS = {
    "gpt-4o-prompt-1k": 0.005,
    "gpt-4o-completion-1k": 0.015,
    "claude-3-5-sonnet-prompt-1k": 0.003,
    "claude-3-5-sonnet-completion-1k": 0.015,
    "serp-query": 0.005,
}


class CostGuardrails:
    """Thread-safe financial expense tracker per tenant."""

    def __init__(self):
        self._lock = threading.Lock()
        # tenant_id -> {"daily_usd": float, "monthly_usd": float, "last_reset_day": int}
        self._spend: Dict[str, Dict[str, float]] = {}

    def calculate_llm_cost(self, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4o") -> float:
        prompt_rate = UNIT_COSTS.get(f"{model}-prompt-1k", 0.005) / 1000.0
        completion_rate = UNIT_COSTS.get(f"{model}-completion-1k", 0.015) / 1000.0
        return (prompt_tokens * prompt_rate) + (completion_tokens * completion_rate)

    def calculate_serp_cost(self, query_count: int = 1) -> float:
        return query_count * UNIT_COSTS.get("serp-query", 0.005)

    def record_and_enforce(self, tenant_id: str, cost_usd: float, plan_tier: str = "starter"):
        """Records expense and raises SpendLimitExceeded if cap is breached."""
        limits = TIER_LIMITS.get(plan_tier.lower(), TIER_LIMITS["starter"])
        today_int = datetime.now(timezone.utc).timetuple().tm_yday

        with self._lock:
            record = self._spend.setdefault(tenant_id, {
                "daily_usd": 0.0,
                "monthly_usd": 0.0,
                "last_day": today_int,
            })

            # Daily rollover
            if record.get("last_day") != today_int:
                record["daily_usd"] = 0.0
                record["last_day"] = today_int

            new_daily = record["daily_usd"] + cost_usd
            new_monthly = record["monthly_usd"] + cost_usd

            if new_daily > limits.max_daily_spend_usd:
                raise SpendLimitExceeded(
                    f"Daily cost limit exceeded for tenant '{tenant_id}': "
                    f"${new_daily:.3f} > ${limits.max_daily_spend_usd:.2f} limit."
                )

            if new_monthly > limits.max_monthly_spend_usd:
                raise SpendLimitExceeded(
                    f"Monthly cost limit exceeded for tenant '{tenant_id}': "
                    f"${new_monthly:.3f} > ${limits.max_monthly_spend_usd:.2f} limit."
                )

            record["daily_usd"] = new_daily
            record["monthly_usd"] = new_monthly

    def get_spend(self, tenant_id: str) -> Dict[str, float]:
        with self._lock:
            data = self._spend.get(tenant_id, {"daily_usd": 0.0, "monthly_usd": 0.0})
            return {"daily_usd": data["daily_usd"], "monthly_usd": data["monthly_usd"]}

    def reset(self, tenant_id: Optional[str] = None):
        with self._lock:
            if tenant_id:
                self._spend.pop(tenant_id, None)
            else:
                self._spend.clear()


class AILoopBreaker:
    """
    Guards against runaway LLM or tool-calling loops within a single task execution.
    Default ceilings: max 10 LLM invocations, max 8 tool iterations.
    """
    def __init__(self, max_llm_calls: int = 10, max_tool_iterations: int = 8):
        self.max_llm_calls = max_llm_calls
        self.max_tool_iterations = max_tool_iterations
        self._llm_calls: int = 0
        self._tool_iterations: int = 0

    def record_llm_call(self):
        self._llm_calls += 1
        if self._llm_calls > self.max_llm_calls:
            raise RunawayLoopDetected(
                f"Runaway AI detected: Exceeded max permitted LLM invocations ({self.max_llm_calls}) in single job."
            )

    def record_tool_iteration(self):
        self._tool_iterations += 1
        if self._tool_iterations > self.max_tool_iterations:
            raise RunawayLoopDetected(
                f"Runaway AI detected: Exceeded max permitted tool iterations ({self.max_tool_iterations}) in single job."
            )


cost_guardrails = CostGuardrails()
