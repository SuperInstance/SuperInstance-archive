"""
Cost Tracker
Tracks API costs and enforces budget limits
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class CostEntry:
    """Single cost entry"""
    timestamp: datetime
    model: str
    cost: float
    input_tokens: int
    output_tokens: int
    task_description: Optional[str] = None


class CostTracker:
    """
    Tracks costs across models and enforces budget limits
    """

    def __init__(self, daily_limit: float = 5.0, monthly_limit: float = 150.0):
        """
        Initialize cost tracker

        Args:
            daily_limit: Daily budget limit in USD
            monthly_limit: Monthly budget limit in USD
        """
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit

        self.costs: List[CostEntry] = []
        self.cache_savings = 0.0
        self.local_model_count = 0  # Track free local model usage

    def record_cost(
        self,
        model: str,
        cost: float,
        input_tokens: int,
        output_tokens: int,
        task_description: Optional[str] = None
    ):
        """
        Record a cost entry

        Args:
            model: Model name
            cost: Cost in USD
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            task_description: Optional task description
        """
        entry = CostEntry(
            timestamp=datetime.now(),
            model=model,
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            task_description=task_description
        )

        self.costs.append(entry)

        # Track local model usage separately
        if cost == 0:
            self.local_model_count += 1

    def record_cache_savings(self, savings: float):
        """Record cost savings from caching"""
        self.cache_savings += savings

    def get_total_cost(self) -> float:
        """Get total session cost"""
        return sum(entry.cost for entry in self.costs)

    def get_today_cost(self) -> float:
        """Get today's total cost"""
        today = datetime.now().date()
        return sum(
            entry.cost for entry in self.costs
            if entry.timestamp.date() == today
        )

    def get_month_cost(self) -> float:
        """Get this month's total cost"""
        now = datetime.now()
        return sum(
            entry.cost for entry in self.costs
            if entry.timestamp.year == now.year and entry.timestamp.month == now.month
        )

    def get_remaining_daily_budget(self) -> float:
        """Get remaining daily budget"""
        return max(0, self.daily_limit - self.get_today_cost())

    def get_remaining_monthly_budget(self) -> float:
        """Get remaining monthly budget"""
        return max(0, self.monthly_limit - self.get_month_cost())

    def is_near_limit(self, threshold: float = 0.8) -> bool:
        """
        Check if near budget limit

        Args:
            threshold: Warning threshold (0-1)

        Returns:
            True if over threshold
        """
        daily_usage = self.get_today_cost() / self.daily_limit if self.daily_limit > 0 else 0
        return daily_usage >= threshold

    def is_over_budget(self) -> bool:
        """Check if over budget"""
        return self.get_today_cost() >= self.daily_limit

    def get_breakdown(self) -> Dict:
        """
        Get cost breakdown

        Returns:
            Dict with cost details
        """
        # Costs by model
        by_model = {}
        for entry in self.costs:
            by_model[entry.model] = by_model.get(entry.model, 0) + entry.cost

        # Token counts
        total_input_tokens = sum(entry.input_tokens for entry in self.costs)
        total_output_tokens = sum(entry.output_tokens for entry in self.costs)

        # Calculate theoretical cost without local models
        theoretical_cost_without_local = self.get_total_cost() + (self.local_model_count * 0.002)  # Assume $0.002 per local task if using cloud

        return {
            'total': self.get_total_cost(),
            'today': self.get_today_cost(),
            'month': self.get_month_cost(),
            'remaining': self.get_remaining_daily_budget(),
            'remaining_monthly': self.get_remaining_monthly_budget(),
            'by_model': by_model,
            'cache_savings': self.cache_savings,
            'local_model_count': self.local_model_count,
            'local_model_savings': theoretical_cost_without_local - self.get_total_cost(),
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'avg_cost_per_task': self.get_total_cost() / len(self.costs) if self.costs else 0
        }

    def get_cost_summary(self) -> str:
        """
        Get human-readable cost summary

        Returns:
            Formatted string
        """
        breakdown = self.get_breakdown()

        summary = f"""
Cost Summary:
  Session Total: ${breakdown['total']:.4f}
  Today's Total: ${breakdown['today']:.2f} / ${self.daily_limit:.2f}
  Remaining: ${breakdown['remaining']:.2f}

  Tokens Used: {breakdown['total_input_tokens']:,} in / {breakdown['total_output_tokens']:,} out
  Tasks Completed: {len(self.costs)}
  Local Tasks (FREE): {self.local_model_count}

  Savings from Local: ${breakdown['local_model_savings']:.2f}
  Savings from Cache: ${self.cache_savings:.2f}
        """

        return summary.strip()

    def set_daily_limit(self, limit: float):
        """Set daily budget limit"""
        self.daily_limit = limit

    def set_monthly_limit(self, limit: float):
        """Set monthly budget limit"""
        self.monthly_limit = limit

    def export_costs(self, filepath: str):
        """
        Export costs to CSV

        Args:
            filepath: Output file path
        """
        import csv

        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Model', 'Cost', 'Input Tokens', 'Output Tokens', 'Task'])

            for entry in self.costs:
                writer.writerow([
                    entry.timestamp.isoformat(),
                    entry.model,
                    f"{entry.cost:.6f}",
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.task_description or ''
                ])

    def get_cost_over_time(self, days: int = 7) -> List[Tuple[datetime, float]]:
        """
        Get cost over time for visualization

        Args:
            days: Number of days to look back

        Returns:
            List of (date, cost) tuples
        """
        cutoff = datetime.now() - timedelta(days=days)
        filtered = [entry for entry in self.costs if entry.timestamp >= cutoff]

        # Group by day
        daily_costs = {}
        for entry in filtered:
            day = entry.timestamp.date()
            daily_costs[day] = daily_costs.get(day, 0) + entry.cost

        # Convert to sorted list
        return sorted(daily_costs.items())
