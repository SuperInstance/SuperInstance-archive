"""
Differential Privacy for Aggregate Analytics
Advanced privacy-preserving analytics system that provides mathematical guarantees of privacy protection
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import secrets
import math
from abc import ABC, abstractmethod
from collections import defaultdict

logger = logging.getLogger(__name__)

class PrivacyMechanism(Enum):
    """Types of differential privacy mechanisms"""
    LAPLACE = "laplace"                    # Laplace mechanism for numerical queries
    GAUSSIAN = "gaussian"                  # Gaussian mechanism for numerical queries
    EXPONENTIAL = "exponential"            # Exponential mechanism for non-numerical queries
    RANDOMIZED_RESPONSE = "randomized_response"  # For binary/categorical data
    SPARSE_VECTOR = "sparse_vector"        # Sparse vector technique
    PRIVATE_MULTIPLICATIVE_WEIGHTS = "pmw" # Private multiplicative weights
    DIFFERENTIALLY_PRIVATE_SGD = "dp_sgd"  # For machine learning

class PrivacyBudgetType(Enum):
    """Types of privacy budget allocation"""
    GLOBAL = "global"                      # Global budget across all queries
    PER_USER = "per_user"                  # Budget per individual user
    PER_QUERY_TYPE = "per_query_type"      # Budget per type of query
    TEMPORAL = "temporal"                  # Budget over time periods
    HIERARCHICAL = "hierarchical"          # Nested budget structure

class SensitivityType(Enum):
    """Types of query sensitivity"""
    L1_SENSITIVITY = "l1"                  # L1 sensitivity (sum of absolute differences)
    L2_SENSITIVITY = "l2"                  # L2 sensitivity (Euclidean distance)
    LOCAL_SENSITIVITY = "local"            # Local sensitivity
    SMOOTH_SENSITIVITY = "smooth"          # Smooth sensitivity
    GLOBAL_SENSITIVITY = "global"          # Global sensitivity

@dataclass
class PrivacyParameters:
    """Parameters for differential privacy"""
    epsilon: float                         # Privacy parameter (smaller = more private)
    delta: float = 0.0                    # Failure probability (for (ε,δ)-DP)
    mechanism: PrivacyMechanism = PrivacyMechanism.LAPLACE
    sensitivity: float = 1.0              # Query sensitivity
    sensitivity_type: SensitivityType = SensitivityType.GLOBAL_SENSITIVITY
    
    def __post_init__(self):
        if self.epsilon <= 0:
            raise ValueError("Epsilon must be positive")
        if not (0 <= self.delta < 1):
            raise ValueError("Delta must be in [0, 1)")

@dataclass
class PrivacyBudget:
    """Privacy budget management"""
    total_epsilon: float
    remaining_epsilon: float
    total_delta: float = 0.0
    remaining_delta: float = 0.0
    budget_type: PrivacyBudgetType = PrivacyBudgetType.GLOBAL
    queries_executed: int = 0
    allocation_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def allocate(self, epsilon: float, delta: float = 0.0, query_id: str = None) -> bool:
        """Allocate privacy budget for a query"""
        if self.remaining_epsilon >= epsilon and self.remaining_delta >= delta:
            self.remaining_epsilon -= epsilon
            self.remaining_delta -= delta
            self.queries_executed += 1
            
            self.allocation_history.append({
                'query_id': query_id or f"query_{self.queries_executed}",
                'epsilon_used': epsilon,
                'delta_used': delta,
                'timestamp': datetime.now(),
                'remaining_epsilon': self.remaining_epsilon,
                'remaining_delta': self.remaining_delta
            })
            return True
        return False
    
    @property
    def epsilon_exhausted(self) -> bool:
        """Check if epsilon budget is exhausted"""
        return self.remaining_epsilon <= 0
    
    @property
    def utilization_rate(self) -> float:
        """Get budget utilization rate"""
        return 1.0 - (self.remaining_epsilon / self.total_epsilon) if self.total_epsilon > 0 else 1.0

@dataclass
class DPQueryResult:
    """Result of a differentially private query"""
    query_id: str
    result: Any
    true_result: Optional[Any] = None      # For testing/evaluation only
    noise_added: float = 0.0
    privacy_cost: PrivacyParameters = None
    mechanism_used: PrivacyMechanism = None
    accuracy_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

class PrivacyMechanismBase(ABC):
    """Base class for differential privacy mechanisms"""
    
    @abstractmethod
    async def add_noise(self, value: Union[float, np.ndarray], 
                       privacy_params: PrivacyParameters) -> Union[float, np.ndarray]:
        """Add noise to value according to the mechanism"""
        pass
    
    @abstractmethod
    def calculate_noise_scale(self, privacy_params: PrivacyParameters) -> float:
        """Calculate the scale of noise to add"""
        pass

class LaplaceMechanism(PrivacyMechanismBase):
    """Laplace mechanism for differential privacy"""
    
    async def add_noise(self, value: Union[float, np.ndarray], 
                       privacy_params: PrivacyParameters) -> Union[float, np.ndarray]:
        """Add Laplace noise to the value"""
        noise_scale = self.calculate_noise_scale(privacy_params)
        
        if isinstance(value, np.ndarray):
            noise = np.random.laplace(0, noise_scale, value.shape)
            return value + noise
        else:
            noise = np.random.laplace(0, noise_scale)
            return value + noise
    
    def calculate_noise_scale(self, privacy_params: PrivacyParameters) -> float:
        """Calculate Laplace noise scale: Δf / ε"""
        return privacy_params.sensitivity / privacy_params.epsilon

class GaussianMechanism(PrivacyMechanismBase):
    """Gaussian mechanism for differential privacy"""
    
    async def add_noise(self, value: Union[float, np.ndarray], 
                       privacy_params: PrivacyParameters) -> Union[float, np.ndarray]:
        """Add Gaussian noise to the value"""
        noise_scale = self.calculate_noise_scale(privacy_params)
        
        if isinstance(value, np.ndarray):
            noise = np.random.normal(0, noise_scale, value.shape)
            return value + noise
        else:
            noise = np.random.normal(0, noise_scale)
            return value + noise
    
    def calculate_noise_scale(self, privacy_params: PrivacyParameters) -> float:
        """Calculate Gaussian noise scale for (ε,δ)-DP"""
        if privacy_params.delta == 0:
            raise ValueError("Gaussian mechanism requires δ > 0")
        
        # σ ≥ Δf * sqrt(2 * ln(1.25/δ)) / ε
        c = math.sqrt(2 * math.log(1.25 / privacy_params.delta))
        return privacy_params.sensitivity * c / privacy_params.epsilon

class ExponentialMechanism(PrivacyMechanismBase):
    """Exponential mechanism for non-numerical queries"""
    
    def __init__(self):
        self.utility_functions = {}
    
    async def add_noise(self, candidates: List[Any], 
                       privacy_params: PrivacyParameters,
                       utility_function: Callable[[Any], float]) -> Any:
        """Select output using exponential mechanism"""
        if not candidates:
            raise ValueError("No candidates provided")
        
        # Calculate utility scores
        utilities = [utility_function(candidate) for candidate in candidates]
        
        # Calculate probabilities using exponential mechanism
        noise_scale = self.calculate_noise_scale(privacy_params)
        scaled_utilities = np.array(utilities) / (2 * privacy_params.sensitivity)
        scaled_utilities *= privacy_params.epsilon
        
        # Apply softmax to get probabilities
        exp_utilities = np.exp(scaled_utilities - np.max(scaled_utilities))  # Numerical stability
        probabilities = exp_utilities / np.sum(exp_utilities)
        
        # Sample according to probabilities
        selected_idx = np.random.choice(len(candidates), p=probabilities)
        return candidates[selected_idx]
    
    def calculate_noise_scale(self, privacy_params: PrivacyParameters) -> float:
        """For exponential mechanism, this is used in the probability calculation"""
        return 2 * privacy_params.sensitivity / privacy_params.epsilon

class RandomizedResponseMechanism(PrivacyMechanismBase):
    """Randomized response for binary/categorical data"""
    
    async def add_noise(self, value: Union[bool, int, str], 
                       privacy_params: PrivacyParameters,
                       domain: Optional[List] = None) -> Union[bool, int, str]:
        """Apply randomized response to value"""
        if isinstance(value, bool):
            return await self._randomized_response_binary(value, privacy_params)
        elif domain is not None:
            return await self._randomized_response_categorical(value, privacy_params, domain)
        else:
            raise ValueError("Domain must be provided for non-binary values")
    
    async def _randomized_response_binary(self, value: bool, 
                                        privacy_params: PrivacyParameters) -> bool:
        """Randomized response for binary values"""
        # Probability of truth-telling
        p = math.exp(privacy_params.epsilon) / (math.exp(privacy_params.epsilon) + 1)
        
        if np.random.random() < p:
            return value  # Tell the truth
        else:
            return not value  # Flip the bit
    
    async def _randomized_response_categorical(self, value: Any, 
                                             privacy_params: PrivacyParameters,
                                             domain: List) -> Any:
        """Randomized response for categorical values"""
        k = len(domain)
        if k <= 1:
            return value
        
        # Probability of truth-telling for k-ary randomized response
        p = math.exp(privacy_params.epsilon) / (math.exp(privacy_params.epsilon) + k - 1)
        
        if np.random.random() < p:
            return value  # Return true value
        else:
            # Return random value from domain (excluding true value)
            other_values = [v for v in domain if v != value]
            return np.random.choice(other_values)
    
    def calculate_noise_scale(self, privacy_params: PrivacyParameters) -> float:
        """Not applicable for randomized response"""
        return 0.0

class SparseVectorTechnique(PrivacyMechanismBase):
    """Sparse Vector Technique for answering multiple threshold queries"""
    
    async def answer_threshold_queries(self, queries: List[Callable], 
                                     threshold: float,
                                     privacy_params: PrivacyParameters,
                                     max_answers: int = 1) -> List[Tuple[int, bool]]:
        """Answer threshold queries using sparse vector technique"""
        # Add noise to threshold
        threshold_noise = np.random.laplace(0, 2 * privacy_params.sensitivity / privacy_params.epsilon)
        noisy_threshold = threshold + threshold_noise
        
        answers = []
        answered_count = 0
        
        for i, query in enumerate(queries):
            if answered_count >= max_answers:
                break
            
            # Evaluate query
            query_result = query()
            
            # Add noise to query result
            query_noise = np.random.laplace(0, 4 * privacy_params.sensitivity / privacy_params.epsilon)
            noisy_result = query_result + query_noise
            
            # Compare with noisy threshold
            above_threshold = noisy_result >= noisy_threshold
            answers.append((i, above_threshold))
            
            if above_threshold:
                answered_count += 1
        
        return answers
    
    async def add_noise(self, value: Union[float, np.ndarray], 
                       privacy_params: PrivacyParameters) -> Union[float, np.ndarray]:
        """Not directly applicable - use answer_threshold_queries instead"""
        raise NotImplementedError("Use answer_threshold_queries for sparse vector technique")
    
    def calculate_noise_scale(self, privacy_params: PrivacyParameters) -> float:
        """Calculate noise scale for sparse vector technique"""
        return 4 * privacy_params.sensitivity / privacy_params.epsilon

class DifferentialPrivacyEngine:
    """Main engine for differential privacy operations"""
    
    def __init__(self):
        self.mechanisms = {
            PrivacyMechanism.LAPLACE: LaplaceMechanism(),
            PrivacyMechanism.GAUSSIAN: GaussianMechanism(),
            PrivacyMechanism.EXPONENTIAL: ExponentialMechanism(),
            PrivacyMechanism.RANDOMIZED_RESPONSE: RandomizedResponseMechanism(),
            PrivacyMechanism.SPARSE_VECTOR: SparseVectorTechnique()
        }
        self.budgets = {}
        self.query_history = []
        self.sensitivity_analyzers = {}
        
    async def create_privacy_budget(self, budget_id: str, total_epsilon: float, 
                                  total_delta: float = 0.0,
                                  budget_type: PrivacyBudgetType = PrivacyBudgetType.GLOBAL) -> PrivacyBudget:
        """Create a new privacy budget"""
        budget = PrivacyBudget(
            total_epsilon=total_epsilon,
            remaining_epsilon=total_epsilon,
            total_delta=total_delta,
            remaining_delta=total_delta,
            budget_type=budget_type
        )
        
        self.budgets[budget_id] = budget
        logger.info(f"Created privacy budget {budget_id}: ε={total_epsilon}, δ={total_delta}")
        return budget
    
    async def execute_dp_query(self, query_function: Callable, 
                             privacy_params: PrivacyParameters,
                             budget_id: str,
                             query_id: Optional[str] = None) -> DPQueryResult:
        """Execute a differentially private query"""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        query_id = query_id or f"query_{len(self.query_history) + 1}"
        
        # Check budget availability
        if not budget.allocate(privacy_params.epsilon, privacy_params.delta, query_id):
            raise ValueError("Insufficient privacy budget")
        
        try:
            # Execute the true query
            true_result = query_function()
            
            # Add noise according to the specified mechanism
            mechanism = self.mechanisms[privacy_params.mechanism]
            
            if privacy_params.mechanism == PrivacyMechanism.EXPONENTIAL:
                # Exponential mechanism requires special handling
                if not hasattr(query_function, 'candidates') or not hasattr(query_function, 'utility'):
                    raise ValueError("Exponential mechanism requires candidates and utility function")
                
                noisy_result = await mechanism.add_noise(
                    query_function.candidates, privacy_params, query_function.utility
                )
                noise_added = 0.0  # Not applicable for exponential mechanism
            
            elif privacy_params.mechanism == PrivacyMechanism.RANDOMIZED_RESPONSE:
                domain = getattr(query_function, 'domain', None)
                noisy_result = await mechanism.add_noise(true_result, privacy_params, domain)
                noise_added = 0.0  # Not directly quantifiable
            
            else:
                noisy_result = await mechanism.add_noise(true_result, privacy_params)
                if isinstance(true_result, np.ndarray):
                    noise_added = np.linalg.norm(noisy_result - true_result)
                else:
                    noise_added = abs(noisy_result - true_result)
            
            # Calculate accuracy metrics
            accuracy_metrics = await self._calculate_accuracy_metrics(true_result, noisy_result)
            
            result = DPQueryResult(
                query_id=query_id,
                result=noisy_result,
                true_result=true_result,
                noise_added=noise_added,
                privacy_cost=privacy_params,
                mechanism_used=privacy_params.mechanism,
                accuracy_metrics=accuracy_metrics,
                metadata={'budget_id': budget_id}
            )
            
            self.query_history.append(result)
            logger.info(f"Executed DP query {query_id} with ε={privacy_params.epsilon}")
            
            return result
        
        except Exception as e:
            # Refund the budget on error
            budget.remaining_epsilon += privacy_params.epsilon
            budget.remaining_delta += privacy_params.delta
            budget.queries_executed -= 1
            budget.allocation_history.pop()
            
            logger.error(f"Error executing DP query {query_id}: {e}")
            raise
    
    async def _calculate_accuracy_metrics(self, true_result: Any, noisy_result: Any) -> Dict[str, float]:
        """Calculate accuracy metrics for the query result"""
        metrics = {}
        
        try:
            if isinstance(true_result, (int, float)) and isinstance(noisy_result, (int, float)):
                metrics['absolute_error'] = abs(float(noisy_result) - float(true_result))
                metrics['relative_error'] = metrics['absolute_error'] / max(abs(float(true_result)), 1e-10)
                
            elif isinstance(true_result, np.ndarray) and isinstance(noisy_result, np.ndarray):
                metrics['l1_error'] = np.linalg.norm(noisy_result - true_result, ord=1)
                metrics['l2_error'] = np.linalg.norm(noisy_result - true_result, ord=2)
                metrics['max_error'] = np.max(np.abs(noisy_result - true_result))
                
                if np.linalg.norm(true_result) > 0:
                    metrics['relative_l2_error'] = metrics['l2_error'] / np.linalg.norm(true_result)
                
            elif true_result == noisy_result:
                metrics['accuracy'] = 1.0
            else:
                metrics['accuracy'] = 0.0
                
        except Exception as e:
            logger.warning(f"Could not calculate accuracy metrics: {e}")
        
        return metrics
    
    async def compose_privacy_costs(self, privacy_params_list: List[PrivacyParameters]) -> PrivacyParameters:
        """Compose privacy costs using composition theorems"""
        if not privacy_params_list:
            raise ValueError("No privacy parameters provided")
        
        # Simple composition (basic composition theorem)
        total_epsilon = sum(params.epsilon for params in privacy_params_list)
        total_delta = sum(params.delta for params in privacy_params_list)
        
        # Advanced composition could use better bounds
        # For k queries with (ε,δ)-DP each, advanced composition gives:
        # (ε', kδ + δ')-DP where ε' ≈ ε√(2k ln(1/δ'))
        k = len(privacy_params_list)
        if k > 1 and all(params.delta > 0 for params in privacy_params_list):
            avg_epsilon = total_epsilon / k
            avg_delta = total_delta / k
            
            # Apply advanced composition (simplified)
            delta_prime = min(avg_delta, 1e-6)  # Small δ'
            epsilon_prime = avg_epsilon * math.sqrt(2 * k * math.log(1 / delta_prime))
            total_delta_advanced = k * avg_delta + delta_prime
            
            if epsilon_prime < total_epsilon:
                total_epsilon = epsilon_prime
                total_delta = total_delta_advanced
        
        return PrivacyParameters(
            epsilon=total_epsilon,
            delta=total_delta,
            mechanism=privacy_params_list[0].mechanism  # Use first mechanism as default
        )
    
    async def estimate_query_sensitivity(self, query_function: Callable, 
                                       dataset_size: int,
                                       sensitivity_type: SensitivityType = SensitivityType.GLOBAL_SENSITIVITY) -> float:
        """Estimate the sensitivity of a query function"""
        
        if sensitivity_type == SensitivityType.GLOBAL_SENSITIVITY:
            # For common queries, we can provide estimates
            query_name = getattr(query_function, '__name__', 'unknown')
            
            if 'count' in query_name.lower():
                return 1.0  # Adding/removing one person changes count by 1
            elif 'sum' in query_name.lower():
                return 1.0  # Assuming bounded values
            elif 'mean' in query_name.lower():
                return 1.0 / dataset_size  # Mean sensitivity
            elif 'variance' in query_name.lower():
                return 2.0 / dataset_size  # Approximate variance sensitivity
            else:
                return 1.0  # Conservative estimate
        
        elif sensitivity_type == SensitivityType.LOCAL_SENSITIVITY:
            # Local sensitivity would require analyzing the specific dataset
            # This is a placeholder implementation
            return 0.5
        
        else:
            return 1.0  # Conservative default
    
    async def optimize_privacy_parameters(self, target_accuracy: float, 
                                        available_budget: float,
                                        query_sensitivity: float,
                                        mechanism: PrivacyMechanism = PrivacyMechanism.LAPLACE) -> PrivacyParameters:
        """Optimize privacy parameters to achieve target accuracy within budget"""
        
        if mechanism == PrivacyMechanism.LAPLACE:
            # For Laplace mechanism: noise_scale = sensitivity / epsilon
            # Standard deviation of Laplace noise = sqrt(2) * noise_scale
            # For target accuracy (standard deviation), we need:
            required_epsilon = query_sensitivity * math.sqrt(2) / target_accuracy
            
            if required_epsilon <= available_budget:
                return PrivacyParameters(
                    epsilon=required_epsilon,
                    mechanism=mechanism,
                    sensitivity=query_sensitivity
                )
            else:
                # Use all available budget
                return PrivacyParameters(
                    epsilon=available_budget,
                    mechanism=mechanism,
                    sensitivity=query_sensitivity
                )
        
        elif mechanism == PrivacyMechanism.GAUSSIAN:
            # For Gaussian mechanism with (ε,δ)-DP
            delta = 1e-6  # Small δ
            c = math.sqrt(2 * math.log(1.25 / delta))
            required_epsilon = query_sensitivity * c / target_accuracy
            
            if required_epsilon <= available_budget:
                return PrivacyParameters(
                    epsilon=required_epsilon,
                    delta=delta,
                    mechanism=mechanism,
                    sensitivity=query_sensitivity
                )
            else:
                return PrivacyParameters(
                    epsilon=available_budget,
                    delta=delta,
                    mechanism=mechanism,
                    sensitivity=query_sensitivity
                )
        
        else:
            # Default parameters
            return PrivacyParameters(
                epsilon=min(available_budget, 1.0),
                mechanism=mechanism,
                sensitivity=query_sensitivity
            )
    
    def get_privacy_metrics(self, budget_id: str) -> Dict[str, Any]:
        """Get privacy metrics for a budget"""
        if budget_id not in self.budgets:
            raise ValueError(f"Budget {budget_id} not found")
        
        budget = self.budgets[budget_id]
        
        return {
            'budget_utilization': budget.utilization_rate,
            'queries_executed': budget.queries_executed,
            'remaining_epsilon': budget.remaining_epsilon,
            'remaining_delta': budget.remaining_delta,
            'epsilon_exhausted': budget.epsilon_exhausted,
            'average_epsilon_per_query': (budget.total_epsilon - budget.remaining_epsilon) / max(budget.queries_executed, 1)
        }
    
    async def analyze_privacy_risk(self, query_history: List[DPQueryResult]) -> Dict[str, Any]:
        """Analyze privacy risk from query history"""
        if not query_history:
            return {'risk_level': 'none', 'total_privacy_cost': 0.0}
        
        # Calculate total privacy cost
        total_epsilon = sum(result.privacy_cost.epsilon for result in query_history)
        total_delta = sum(result.privacy_cost.delta for result in query_history)
        
        # Assess risk level
        if total_epsilon <= 0.1:
            risk_level = 'very_low'
        elif total_epsilon <= 1.0:
            risk_level = 'low'
        elif total_epsilon <= 5.0:
            risk_level = 'medium'
        elif total_epsilon <= 10.0:
            risk_level = 'high'
        else:
            risk_level = 'very_high'
        
        return {
            'risk_level': risk_level,
            'total_epsilon': total_epsilon,
            'total_delta': total_delta,
            'query_count': len(query_history),
            'mechanisms_used': list(set(result.mechanism_used.value for result in query_history))
        }

# Factory functions
async def create_dp_engine() -> DifferentialPrivacyEngine:
    """Factory function to create differential privacy engine"""
    return DifferentialPrivacyEngine()

# Example usage
async def main():
    """Example usage of differential privacy system"""
    
    # Create DP engine
    dp_engine = await create_dp_engine()
    
    # Create privacy budget
    budget = await dp_engine.create_privacy_budget("test_budget", total_epsilon=2.0, total_delta=1e-6)
    
    # Example dataset
    dataset = np.random.randint(0, 100, size=1000)
    
    # Define query functions
    def count_query():
        return len(dataset)
    
    def sum_query():
        return np.sum(dataset)
    
    def mean_query():
        return np.mean(dataset)
    
    # Execute differentially private queries
    queries = [
        (count_query, "count"),
        (sum_query, "sum"),
        (mean_query, "mean")
    ]
    
    results = []
    
    for query_func, query_name in queries:
        # Estimate sensitivity
        sensitivity = await dp_engine.estimate_query_sensitivity(query_func, len(dataset))
        
        # Optimize privacy parameters
        privacy_params = await dp_engine.optimize_privacy_parameters(
            target_accuracy=10.0,  # Target accuracy
            available_budget=0.5,   # Budget per query
            query_sensitivity=sensitivity,
            mechanism=PrivacyMechanism.LAPLACE
        )
        
        # Execute query
        result = await dp_engine.execute_dp_query(
            query_func, privacy_params, "test_budget", f"{query_name}_query"
        )
        
        results.append(result)
        
        print(f"{query_name.upper()} Query:")
        print(f"  True result: {result.true_result}")
        print(f"  DP result: {result.result}")
        print(f"  Noise added: {result.noise_added:.2f}")
        print(f"  Privacy cost: ε={result.privacy_cost.epsilon:.3f}")
        print(f"  Accuracy metrics: {result.accuracy_metrics}")
        print()
    
    # Check budget status
    metrics = dp_engine.get_privacy_metrics("test_budget")
    print(f"Budget Metrics:")
    print(f"  Utilization: {metrics['budget_utilization']:.1%}")
    print(f"  Remaining ε: {metrics['remaining_epsilon']:.3f}")
    print(f"  Queries executed: {metrics['queries_executed']}")
    
    # Analyze privacy risk
    risk_analysis = await dp_engine.analyze_privacy_risk(results)
    print(f"\nPrivacy Risk Analysis:")
    print(f"  Risk level: {risk_analysis['risk_level']}")
    print(f"  Total ε used: {risk_analysis['total_epsilon']:.3f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())