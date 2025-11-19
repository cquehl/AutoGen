"""
Suntory v3 - Cost Tracking
Track and limit LLM API costs
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from .persistence import get_db_manager
from .telemetry import get_logger

logger = get_logger(__name__)


# Approximate pricing (USD per 1K tokens) - Update regularly!
MODEL_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},

    # Anthropic
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet-20240229": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},

    # Google
    "gemini-pro": {"input": 0.00025, "output": 0.0005},
    "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
    "gemini-ultra": {"input": 0.0125, "output": 0.0375},
}


@dataclass
class CostMetrics:
    """Cost metrics for a request"""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    timestamp: datetime


class CostTracker:
    """
    Track LLM API costs and enforce budgets.

    Features:
    - Per-session cost tracking
    - Daily/monthly budget limits
    - Cost estimation before request
    - Cost breakdown by model
    """

    def __init__(self):
        self.session_costs: list[CostMetrics] = []
        self.daily_limit: Optional[float] = None
        self.monthly_limit: Optional[float] = None

        # Set reasonable defaults ($10/day, $100/month)
        self.set_daily_limit(10.0)
        self.set_monthly_limit(100.0)

    def set_daily_limit(self, limit_usd: float):
        """Set daily spending limit"""
        self.daily_limit = limit_usd
        logger.info(f"Daily cost limit set to ${limit_usd:.2f}")

    def set_monthly_limit(self, limit_usd: float):
        """Set monthly spending limit"""
        self.monthly_limit = limit_usd
        logger.info(f"Monthly cost limit set to ${limit_usd:.2f}")

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Estimate cost for a request.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Estimated output tokens

        Returns:
            Estimated cost in USD
        """
        # Get pricing for model (default to GPT-4 if unknown)
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gpt-4"])

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        return input_cost + output_cost

    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> CostMetrics:
        """
        Record actual usage.

        Args:
            model: Model used
            input_tokens: Actual input tokens
            output_tokens: Actual output tokens

        Returns:
            Cost metrics
        """
        total_tokens = input_tokens + output_tokens
        estimated_cost = self.estimate_cost(model, input_tokens, output_tokens)

        metrics = CostMetrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            timestamp=datetime.now()
        )

        self.session_costs.append(metrics)

        logger.info(
            "Cost recorded",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=f"${estimated_cost:.4f}"
        )

        return metrics

    def get_session_total(self) -> float:
        """Get total cost for current session"""
        return sum(m.estimated_cost for m in self.session_costs)

    def get_daily_total(self) -> float:
        """Get total cost for today"""
        today = datetime.now().date()
        return sum(
            m.estimated_cost
            for m in self.session_costs
            if m.timestamp.date() == today
        )

    def check_budget(self, estimated_cost: float) -> tuple[bool, str]:
        """
        Check if request would exceed budget.

        Args:
            estimated_cost: Estimated cost of request

        Returns:
            Tuple of (allowed, message)
        """
        # Check daily limit
        if self.daily_limit:
            daily_total = self.get_daily_total()
            if daily_total + estimated_cost > self.daily_limit:
                return False, (
                    f"Request would exceed daily budget limit. "
                    f"Used: ${daily_total:.2f}, Limit: ${self.daily_limit:.2f}, "
                    f"Request: ${estimated_cost:.4f}"
                )

        # Check monthly limit (simplified - just checks session)
        # In production, query database for actual monthly total
        if self.monthly_limit:
            session_total = self.get_session_total()
            if session_total + estimated_cost > self.monthly_limit:
                return False, (
                    f"Request would exceed budget limit. "
                    f"Session total: ${session_total:.2f}, "
                    f"Limit: ${self.monthly_limit:.2f}"
                )

        return True, ""

    def get_summary(self) -> str:
        """Get cost summary for session"""
        if not self.session_costs:
            return "No API usage in this session yet."

        total_cost = self.get_session_total()
        total_tokens = sum(m.total_tokens for m in self.session_costs)
        request_count = len(self.session_costs)

        # Breakdown by model
        model_breakdown: Dict[str, float] = {}
        for metrics in self.session_costs:
            model_breakdown[metrics.model] = (
                model_breakdown.get(metrics.model, 0) + metrics.estimated_cost
            )

        lines = [
            f"**Session Cost Summary**",
            f"",
            f"Total Requests: {request_count}",
            f"Total Tokens: {total_tokens:,}",
            f"Total Cost: ${total_cost:.4f}",
            f""
        ]

        if model_breakdown:
            lines.append("**Breakdown by Model:**")
            for model, cost in sorted(
                model_breakdown.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                lines.append(f"  • {model}: ${cost:.4f} ({percentage:.1f}%)")

        if self.daily_limit:
            daily_total = self.get_daily_total()
            daily_remaining = self.daily_limit - daily_total
            lines.append(f"")
            lines.append(f"Daily Budget: ${self.daily_limit:.2f}")
            lines.append(f"Daily Remaining: ${daily_remaining:.2f}")

        return "\n".join(lines)

    def format_cost_display(self, metrics: CostMetrics) -> str:
        """Format cost for display after request"""
        return (
            f"💰 Cost: ${metrics.estimated_cost:.4f} "
            f"({metrics.total_tokens:,} tokens)"
        )


# Singleton instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create cost tracker singleton"""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


def reset_cost_tracker():
    """Reset cost tracker (useful for testing)"""
    global _cost_tracker
    _cost_tracker = None
