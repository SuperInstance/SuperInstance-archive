"""
Privacy Budget Management System
Manage and enforce privacy budgets for differential privacy mechanisms
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from enum import Enum
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
import json
import math
from abc import ABC, abstractmethod
import numpy as np

class BudgetType(Enum):
    EPSILON_DELTA = "epsilon_delta"
    ZERO_CONCENTRATED = "zero_concentrated"
    RENYI = "renyi"
    GDP = "gdp"  # Gaussian Differential Privacy

class BudgetScope(Enum):
    GLOBAL = "global"
    USER = "user"
    DATASET = "dataset"
    QUERY_TYPE = "query_type"
    TIME_PERIOD = "time_period"

class PrivacyMechanism(Enum):
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    SPARSE_VECTOR = "sparse_vector"
    ABOVE_THRESHOLD = "above_threshold"
    REPORT_NOISY_MAX = "report_noisy_max"

class BudgetStatus(Enum):
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    CONSUMED = "consumed"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"

class AllocationStrategy(Enum):
    UNIFORM = "uniform"
    PROPORTIONAL = "proportional"
    ADAPTIVE = "adaptive"
    PRIORITY_BASED = "priority_based"
    TIME_DECAYING = "time_decaying"

@dataclass
class PrivacyBudget:
    """Privacy budget allocation with differential privacy parameters"""
    budget_id: str
    epsilon: float  # Privacy parameter
    delta: Optional[float]  # Failure probability (for (ε,δ)-DP)
    scope: BudgetScope
    scope_identifier: str  # User ID, dataset name, etc.
    allocated_at: datetime
    expires_at: Optional[datetime]
    initial_amount: float
    remaining_amount: float
    status: BudgetStatus
    metadata: Dict[str, Any]

@dataclass
class BudgetConsumption:
    """Record of privacy budget consumption"""
    consumption_id: str
    budget_id: str
    consumed_epsilon: float
    consumed_delta: Optional[float]
    mechanism_used: PrivacyMechanism
    query_type: str
    consumed_at: datetime
    consumed_by: str  # User or system identifier
    query_metadata: Dict[str, Any]

@dataclass
class BudgetAllocation:
    """Allocation of privacy budget across different scopes"""
    allocation_id: str
    parent_budget_id: Optional[str]
    allocated_budgets: List[str]  # Budget IDs
    allocation_strategy: AllocationStrategy
    allocation_ratios: Dict[str, float]
    created_at: datetime
    valid_until: Optional[datetime]

@dataclass
class PrivacyAccountingRecord:
    """Record for privacy accounting and composition"""
    record_id: str
    mechanism: PrivacyMechanism
    epsilon_used: float
    delta_used: Optional[float]
    sensitivity: float
    noise_parameter: float
    timestamp: datetime
    query_info: Dict[str, Any]

@dataclass
class BudgetAlert:
    """Alert for privacy budget threshold violations"""
    alert_id: str
    budget_id: str
    alert_type: str  # "threshold_exceeded", "budget_exhausted", "suspicious_usage"
    threshold: float
    current_usage: float
    triggered_at: datetime
    severity: str  # "low", "medium", "high", "critical"
    message: str

class PrivacyComposer(ABC):
    """Abstract base for privacy composition"""
    
    @abstractmethod
    async def compose(self, records: List[PrivacyAccountingRecord]) -> Tuple[float, float]:
        """Compose privacy parameters from multiple mechanisms"""
        pass
    
    @abstractmethod
    async def get_remaining_budget(self, initial_epsilon: float, consumed_records: List[PrivacyAccountingRecord]) -> float:
        """Calculate remaining privacy budget"""
        pass

class BasicComposer(PrivacyComposer):
    """Basic composition using simple addition (worst-case)"""
    
    async def compose(self, records: List[PrivacyAccountingRecord]) -> Tuple[float, float]:
        """Simple additive composition"""
        total_epsilon = sum(record.epsilon_used for record in records)
        total_delta = sum(record.delta_used or 0 for record in records)
        return total_epsilon, total_delta
    
    async def get_remaining_budget(self, initial_epsilon: float, consumed_records: List[PrivacyAccountingRecord]) -> float:
        """Calculate remaining budget using basic composition"""
        consumed_epsilon, _ = await self.compose(consumed_records)
        return max(0, initial_epsilon - consumed_epsilon)

class AdvancedComposer(PrivacyComposer):
    """Advanced composition using optimal composition theorems"""
    
    async def compose(self, records: List[PrivacyAccountingRecord]) -> Tuple[float, float]:
        """Advanced composition using optimal bounds"""
        if not records:
            return 0.0, 0.0
        
        # Group by mechanism type for better composition
        mechanism_groups = {}
        for record in records:
            if record.mechanism not in mechanism_groups:
                mechanism_groups[record.mechanism] = []
            mechanism_groups[record.mechanism].append(record)
        
        total_epsilon = 0.0
        total_delta = 0.0
        
        for mechanism, group_records in mechanism_groups.items():
            if mechanism in [PrivacyMechanism.LAPLACE, PrivacyMechanism.EXPONENTIAL]:
                # Pure ε-DP mechanisms use basic composition
                group_epsilon = sum(r.epsilon_used for r in group_records)
                total_epsilon += group_epsilon
            else:
                # (ε,δ)-DP mechanisms can use advanced composition
                group_epsilon = sum(r.epsilon_used for r in group_records)
                group_delta = sum(r.delta_used or 0 for r in group_records)
                
                # Apply advanced composition formula (simplified)
                k = len(group_records)
                if k > 1 and group_delta > 0:
                    # Advanced composition: ε' = ε√(2k ln(1/δ')) + kε(e^ε - 1)
                    advanced_epsilon = group_epsilon * math.sqrt(2 * k * math.log(1/max(group_delta, 1e-10))) + \
                                     k * group_epsilon * (math.exp(group_epsilon) - 1)
                    total_epsilon += min(advanced_epsilon, group_epsilon * k)  # Take better of two
                else:
                    total_epsilon += group_epsilon
                
                total_delta += group_delta
        
        return total_epsilon, total_delta
    
    async def get_remaining_budget(self, initial_epsilon: float, consumed_records: List[PrivacyAccountingRecord]) -> float:
        """Calculate remaining budget using advanced composition"""
        consumed_epsilon, _ = await self.compose(consumed_records)
        return max(0, initial_epsilon - consumed_epsilon)

class PrivacyBudgetManager:
    """Main privacy budget management system"""
    
    def __init__(self, composer: Optional[PrivacyComposer] = None):
        self.composer = composer or AdvancedComposer()
        self.budgets: Dict[str, PrivacyBudget] = {}
        self.consumptions: List[BudgetConsumption] = []
        self.allocations: Dict[str, BudgetAllocation] = {}
        self.accounting_records: Dict[str, List[PrivacyAccountingRecord]] = {}
        self.alerts: List[BudgetAlert] = []
        self.alert_thresholds: Dict[str, float] = {
            "warning": 0.8,  # 80% of budget consumed
            "critical": 0.95  # 95% of budget consumed
        }
    
    async def create_budget(
        self,
        epsilon: float,
        delta: Optional[float],
        scope: BudgetScope,
        scope_identifier: str,
        validity_period: Optional[timedelta] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PrivacyBudget:
        """Create a new privacy budget"""
        budget_id = f"budget_{secrets.token_hex(8)}"
        
        expires_at = None
        if validity_period:
            expires_at = datetime.now() + validity_period
        
        budget = PrivacyBudget(
            budget_id=budget_id,
            epsilon=epsilon,
            delta=delta,
            scope=scope,
            scope_identifier=scope_identifier,
            allocated_at=datetime.now(),
            expires_at=expires_at,
            initial_amount=epsilon,
            remaining_amount=epsilon,
            status=BudgetStatus.AVAILABLE,
            metadata=metadata or {}
        )
        
        self.budgets[budget_id] = budget
        self.accounting_records[budget_id] = []
        return budget
    
    async def allocate_budget(
        self,
        parent_budget_id: str,
        allocations: Dict[str, float],  # scope_identifier -> allocation_ratio
        strategy: AllocationStrategy = AllocationStrategy.PROPORTIONAL,
        validity_period: Optional[timedelta] = None
    ) -> BudgetAllocation:
        """Allocate budget across multiple scopes"""
        if parent_budget_id not in self.budgets:
            raise ValueError(f"Parent budget {parent_budget_id} not found")
        
        parent_budget = self.budgets[parent_budget_id]
        
        if parent_budget.status != BudgetStatus.AVAILABLE:
            raise ValueError(f"Parent budget is not available: {parent_budget.status}")
        
        # Validate allocation ratios
        total_ratio = sum(allocations.values())
        if abs(total_ratio - 1.0) > 1e-6:
            raise ValueError(f"Allocation ratios must sum to 1.0, got {total_ratio}")
        
        # Create sub-budgets
        allocated_budget_ids = []
        
        for scope_id, ratio in allocations.items():
            allocated_epsilon = parent_budget.remaining_amount * ratio
            allocated_delta = parent_budget.delta * ratio if parent_budget.delta else None
            
            sub_budget = await self.create_budget(
                epsilon=allocated_epsilon,
                delta=allocated_delta,
                scope=parent_budget.scope,
                scope_identifier=scope_id,
                validity_period=validity_period,
                metadata={
                    "parent_budget": parent_budget_id,
                    "allocation_ratio": ratio
                }
            )
            
            allocated_budget_ids.append(sub_budget.budget_id)
        
        # Update parent budget status
        parent_budget.status = BudgetStatus.ALLOCATED
        parent_budget.remaining_amount = 0  # All allocated to children
        
        # Create allocation record
        allocation_id = f"alloc_{secrets.token_hex(8)}"
        valid_until = datetime.now() + validity_period if validity_period else None
        
        allocation = BudgetAllocation(
            allocation_id=allocation_id,
            parent_budget_id=parent_budget_id,
            allocated_budgets=allocated_budget_ids,
            allocation_strategy=strategy,
            allocation_ratios=allocations,
            created_at=datetime.now(),
            valid_until=valid_until
        )
        
        self.allocations[allocation_id] = allocation
        return allocation
    
    async def consume_budget(
        self,
        budget_id: str,
        epsilon_consumption: float,
        delta_consumption: Optional[float],
        mechanism: PrivacyMechanism,
        query_type: str,
        consumer_id: str,
        query_metadata: Optional[Dict[str, Any]] = None
    ) -> BudgetConsumption:
        """Consume privacy budget for a query"""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        # Check budget availability
        if budget.status not in [BudgetStatus.AVAILABLE, BudgetStatus.ALLOCATED]:
            raise ValueError(f"Budget is not available for consumption: {budget.status}")
        
        # Check expiration
        if budget.expires_at and datetime.now() > budget.expires_at:
            budget.status = BudgetStatus.EXPIRED
            raise ValueError("Budget has expired")
        
        # Check sufficient budget
        if epsilon_consumption > budget.remaining_amount:
            raise ValueError(f"Insufficient budget: requested {epsilon_consumption}, available {budget.remaining_amount}")
        
        # Create consumption record
        consumption_id = f"cons_{secrets.token_hex(8)}"
        consumption = BudgetConsumption(
            consumption_id=consumption_id,
            budget_id=budget_id,
            consumed_epsilon=epsilon_consumption,
            consumed_delta=delta_consumption,
            mechanism_used=mechanism,
            query_type=query_type,
            consumed_at=datetime.now(),
            consumed_by=consumer_id,
            query_metadata=query_metadata or {}
        )
        
        # Create accounting record
        accounting_record = PrivacyAccountingRecord(
            record_id=f"acc_{secrets.token_hex(8)}",
            mechanism=mechanism,
            epsilon_used=epsilon_consumption,
            delta_used=delta_consumption,
            sensitivity=query_metadata.get("sensitivity", 1.0) if query_metadata else 1.0,
            noise_parameter=query_metadata.get("noise_parameter", 1.0) if query_metadata else 1.0,
            timestamp=datetime.now(),
            query_info=query_metadata or {}
        )
        
        # Update budget
        budget.remaining_amount -= epsilon_consumption
        self.consumptions.append(consumption)
        self.accounting_records[budget_id].append(accounting_record)
        
        # Update budget status
        if budget.remaining_amount <= 0:
            budget.status = BudgetStatus.EXHAUSTED
        elif budget.remaining_amount < budget.initial_amount * 0.1:  # Less than 10% remaining
            budget.status = BudgetStatus.CONSUMED
        
        # Check for alerts
        await self._check_budget_alerts(budget_id)
        
        return consumption
    
    async def _check_budget_alerts(self, budget_id: str):
        """Check if budget consumption triggers any alerts"""
        budget = self.budgets[budget_id]
        usage_ratio = (budget.initial_amount - budget.remaining_amount) / budget.initial_amount
        
        # Check warning threshold
        if usage_ratio >= self.alert_thresholds["warning"] and usage_ratio < self.alert_thresholds["critical"]:
            alert = BudgetAlert(
                alert_id=f"alert_{secrets.token_hex(8)}",
                budget_id=budget_id,
                alert_type="threshold_exceeded",
                threshold=self.alert_thresholds["warning"],
                current_usage=usage_ratio,
                triggered_at=datetime.now(),
                severity="medium",
                message=f"Budget {budget_id} has exceeded {self.alert_thresholds['warning']*100:.0f}% usage threshold"
            )
            self.alerts.append(alert)
        
        # Check critical threshold
        elif usage_ratio >= self.alert_thresholds["critical"]:
            alert = BudgetAlert(
                alert_id=f"alert_{secrets.token_hex(8)}",
                budget_id=budget_id,
                alert_type="budget_exhausted",
                threshold=self.alert_thresholds["critical"],
                current_usage=usage_ratio,
                triggered_at=datetime.now(),
                severity="critical",
                message=f"Budget {budget_id} is critically low ({usage_ratio*100:.1f}% consumed)"
            )
            self.alerts.append(alert)
    
    async def get_budget_status(self, budget_id: str) -> Dict[str, Any]:
        """Get comprehensive status of a privacy budget"""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        consumption_records = [c for c in self.consumptions if c.budget_id == budget_id]
        accounting_records = self.accounting_records.get(budget_id, [])
        
        # Calculate composed privacy parameters
        composed_epsilon, composed_delta = await self.composer.compose(accounting_records)
        
        # Calculate usage statistics
        total_queries = len(consumption_records)
        usage_ratio = (budget.initial_amount - budget.remaining_amount) / budget.initial_amount
        
        # Get recent consumption pattern
        recent_consumptions = [
            c for c in consumption_records 
            if (datetime.now() - c.consumed_at).days <= 7
        ]
        
        return {
            "budget_id": budget_id,
            "status": budget.status.value,
            "initial_epsilon": budget.initial_amount,
            "remaining_epsilon": budget.remaining_amount,
            "consumed_epsilon": budget.initial_amount - budget.remaining_amount,
            "usage_percentage": usage_ratio * 100,
            "composed_epsilon": composed_epsilon,
            "composed_delta": composed_delta,
            "total_queries": total_queries,
            "recent_queries_7d": len(recent_consumptions),
            "expires_at": budget.expires_at.isoformat() if budget.expires_at else None,
            "scope": budget.scope.value,
            "scope_identifier": budget.scope_identifier,
            "created_at": budget.allocated_at.isoformat()
        }
    
    async def estimate_budget_requirement(
        self,
        mechanism: PrivacyMechanism,
        sensitivity: float,
        target_epsilon: float,
        num_queries: int
    ) -> Dict[str, Any]:
        """Estimate budget requirements for a series of queries"""
        # Calculate noise parameter needed
        if mechanism == PrivacyMechanism.LAPLACE:
            noise_scale = sensitivity / target_epsilon
            individual_epsilon = target_epsilon
        elif mechanism == PrivacyMechanism.GAUSSIAN:
            # Gaussian mechanism for (ε,δ)-DP
            sigma = sensitivity * math.sqrt(2 * math.log(1.25 / 0.00001)) / target_epsilon
            noise_scale = sigma
            individual_epsilon = target_epsilon
        else:
            # Default estimation
            noise_scale = sensitivity / target_epsilon
            individual_epsilon = target_epsilon
        
        # Estimate total budget needed
        if mechanism in [PrivacyMechanism.LAPLACE, PrivacyMechanism.EXPONENTIAL]:
            # Pure ε-DP: basic composition
            total_epsilon = individual_epsilon * num_queries
            total_delta = 0.0
        else:
            # (ε,δ)-DP: can use advanced composition
            if num_queries > 1:
                # Advanced composition estimate
                delta = 0.00001  # Small δ
                advanced_epsilon = individual_epsilon * math.sqrt(2 * num_queries * math.log(1/delta)) + \
                                 num_queries * individual_epsilon * (math.exp(individual_epsilon) - 1)
                total_epsilon = min(advanced_epsilon, individual_epsilon * num_queries)
                total_delta = delta * num_queries
            else:
                total_epsilon = individual_epsilon
                total_delta = 0.00001
        
        return {
            "mechanism": mechanism.value,
            "target_epsilon": target_epsilon,
            "sensitivity": sensitivity,
            "num_queries": num_queries,
            "noise_scale": noise_scale,
            "individual_query_epsilon": individual_epsilon,
            "total_epsilon_needed": total_epsilon,
            "total_delta_needed": total_delta,
            "composition_type": "advanced" if mechanism not in [PrivacyMechanism.LAPLACE, PrivacyMechanism.EXPONENTIAL] else "basic"
        }
    
    async def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide privacy budget overview"""
        total_budgets = len(self.budgets)
        active_budgets = len([b for b in self.budgets.values() if b.status == BudgetStatus.AVAILABLE])
        exhausted_budgets = len([b for b in self.budgets.values() if b.status == BudgetStatus.EXHAUSTED])
        
        total_allocations = len(self.allocations)
        total_consumptions = len(self.consumptions)
        
        # Calculate total privacy spent
        total_epsilon_spent = sum(c.consumed_epsilon for c in self.consumptions)
        total_delta_spent = sum(c.consumed_delta or 0 for c in self.consumptions)
        
        # Recent activity
        recent_consumptions = [
            c for c in self.consumptions 
            if (datetime.now() - c.consumed_at).hours <= 24
        ]
        
        # Active alerts
        recent_alerts = [
            a for a in self.alerts 
            if (datetime.now() - a.triggered_at).hours <= 24
        ]
        
        return {
            "total_budgets": total_budgets,
            "active_budgets": active_budgets,
            "exhausted_budgets": exhausted_budgets,
            "total_allocations": total_allocations,
            "total_consumptions": total_consumptions,
            "total_epsilon_spent": total_epsilon_spent,
            "total_delta_spent": total_delta_spent,
            "consumption_last_24h": len(recent_consumptions),
            "active_alerts": len(recent_alerts),
            "budget_utilization": {
                "high_usage": len([b for b in self.budgets.values() if (b.initial_amount - b.remaining_amount) / b.initial_amount > 0.8]),
                "medium_usage": len([b for b in self.budgets.values() if 0.3 < (b.initial_amount - b.remaining_amount) / b.initial_amount <= 0.8]),
                "low_usage": len([b for b in self.budgets.values() if (b.initial_amount - b.remaining_amount) / b.initial_amount <= 0.3])
            }
        }

def create_privacy_budget_manager(composer: Optional[PrivacyComposer] = None) -> PrivacyBudgetManager:
    """Factory function to create privacy budget manager"""
    return PrivacyBudgetManager(composer)

# Example usage
async def example_usage():
    """Example of using privacy budget management"""
    
    # Create budget manager
    budget_manager = create_privacy_budget_manager()
    
    # Create global privacy budget
    global_budget = await budget_manager.create_budget(
        epsilon=10.0,
        delta=0.00001,
        scope=BudgetScope.GLOBAL,
        scope_identifier="main_database",
        validity_period=timedelta(days=30),
        metadata={"purpose": "analytics", "data_source": "user_behavior"}
    )
    
    print(f"Created global budget: {global_budget.budget_id}")
    print(f"  Epsilon: {global_budget.epsilon}")
    print(f"  Delta: {global_budget.delta}")
    print(f"  Expires: {global_budget.expires_at.strftime('%Y-%m-%d') if global_budget.expires_at else 'Never'}")
    
    # Allocate budget across different query types
    allocations = {
        "count_queries": 0.4,
        "sum_queries": 0.3,
        "avg_queries": 0.2,
        "histogram_queries": 0.1
    }
    
    allocation = await budget_manager.allocate_budget(
        parent_budget_id=global_budget.budget_id,
        allocations=allocations,
        strategy=AllocationStrategy.PROPORTIONAL,
        validity_period=timedelta(days=30)
    )
    
    print(f"\nAllocated budget across {len(allocation.allocated_budgets)} sub-budgets:")
    for i, (query_type, ratio) in enumerate(allocations.items()):
        sub_budget_id = allocation.allocated_budgets[i]
        sub_budget = budget_manager.budgets[sub_budget_id]
        print(f"  {query_type}: {sub_budget.epsilon:.2f} epsilon ({ratio*100:.0f}%)")
    
    # Estimate budget requirement for a series of queries
    estimate = await budget_manager.estimate_budget_requirement(
        mechanism=PrivacyMechanism.LAPLACE,
        sensitivity=1.0,
        target_epsilon=0.1,
        num_queries=50
    )
    
    print(f"\nBudget estimation for 50 Laplace queries:")
    print(f"  Target epsilon per query: {estimate['target_epsilon']}")
    print(f"  Total epsilon needed: {estimate['total_epsilon_needed']:.2f}")
    print(f"  Noise scale: {estimate['noise_scale']:.3f}")
    
    # Consume budget for queries
    count_budget_id = allocation.allocated_budgets[0]  # count_queries budget
    
    for i in range(5):
        consumption = await budget_manager.consume_budget(
            budget_id=count_budget_id,
            epsilon_consumption=0.2,
            delta_consumption=None,
            mechanism=PrivacyMechanism.LAPLACE,
            query_type="count",
            consumer_id=f"analyst_{i+1}",
            query_metadata={
                "sensitivity": 1.0,
                "noise_parameter": 5.0,
                "query": f"SELECT COUNT(*) FROM table WHERE condition_{i+1}"
            }
        )
        
        print(f"  Query {i+1}: consumed {consumption.consumed_epsilon} epsilon")
    
    # Get budget status
    status = await budget_manager.get_budget_status(count_budget_id)
    print(f"\nCount queries budget status:")
    print(f"  Usage: {status['usage_percentage']:.1f}%")
    print(f"  Remaining: {status['remaining_epsilon']:.2f} epsilon")
    print(f"  Total queries: {status['total_queries']}")
    
    # Get system overview
    overview = await budget_manager.get_system_overview()
    print(f"\nSystem Overview:")
    print(f"  Total budgets: {overview['total_budgets']}")
    print(f"  Active budgets: {overview['active_budgets']}")
    print(f"  Total epsilon spent: {overview['total_epsilon_spent']:.2f}")
    print(f"  Recent consumptions (24h): {overview['consumption_last_24h']}")
    print(f"  Active alerts: {overview['active_alerts']}")
    
    print(f"\nBudget utilization:")
    for level, count in overview['budget_utilization'].items():
        print(f"  {level}: {count} budgets")

if __name__ == "__main__":
    asyncio.run(example_usage())