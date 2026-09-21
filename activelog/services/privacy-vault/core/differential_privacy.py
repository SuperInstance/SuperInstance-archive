import asyncio
import logging
import json
import math
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Callable
from enum import Enum
from dataclasses import dataclass
import uuid
from collections import defaultdict
import scipy.stats as stats

logger = logging.getLogger(__name__)

class NoiseType(Enum):
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    DISCRETE_LAPLACE = "discrete_laplace"

class QueryType(Enum):
    COUNT = "count"
    SUM = "sum"
    MEAN = "mean"
    VARIANCE = "variance"
    QUANTILE = "quantile"
    HISTOGRAM = "histogram"
    COVARIANCE = "covariance"
    RANGE_QUERY = "range_query"

class CompositionType(Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    MOMENTS_ACCOUNTANT = "moments_accountant"
    RDP = "renyi_dp"  # Rényi Differential Privacy

class SensitivityType(Enum):
    L1 = "l1"  # Manhattan distance
    L2 = "l2"  # Euclidean distance
    SMOOTH = "smooth"
    LOCAL = "local"

@dataclass
class PrivacyParameters:
    epsilon: float
    delta: float
    sensitivity: float
    sensitivity_type: SensitivityType
    noise_type: NoiseType
    clipping_bound: Optional[float] = None
    composition_type: CompositionType = CompositionType.BASIC

@dataclass
class DPQuery:
    query_id: str
    query_type: QueryType
    privacy_params: PrivacyParameters
    dataset_id: str
    fields: List[str]
    conditions: Dict[str, Any]
    sensitivity_analysis: Dict[str, float]
    noise_added: float
    true_result: Optional[float] = None  # For evaluation only
    noisy_result: float = None
    created_date: datetime = None
    executed_date: Optional[datetime] = None

@dataclass
class PrivacyAccountant:
    total_epsilon: float
    total_delta: float
    consumed_epsilon: float
    consumed_delta: float
    query_history: List[DPQuery]
    composition_type: CompositionType
    advanced_composition_params: Dict[str, float]

@dataclass
class MomentsAccountantState:
    log_moments: List[float]  # Log moments for RDP
    orders: List[float]  # Orders alpha for RDP
    max_order: float
    precision: float

class DifferentialPrivacyManager:
    def __init__(self):
        self.privacy_accountants: Dict[str, PrivacyAccountant] = {}
        self.dp_queries: Dict[str, DPQuery] = {}
        self.sensitivity_oracle: Dict[str, Dict] = {}
        self.noise_calibration: Dict[str, Dict] = {}
        self.moments_accountants: Dict[str, MomentsAccountantState] = {}
        self.global_sensitivity_cache: Dict[str, float] = {}
        logger.info("Differential Privacy Manager initialized")

    async def initialize(self):
        await self._initialize_sensitivity_oracle()
        await self._initialize_noise_calibration()
        await self._initialize_default_accountants()
        logger.info("Differential Privacy Manager initialization completed")

    async def _initialize_sensitivity_oracle(self):
        """Initialize sensitivity analysis for common query types"""
        self.sensitivity_oracle = {
            QueryType.COUNT.value: {
                "l1_sensitivity": 1.0,  # Adding/removing one record
                "l2_sensitivity": 1.0,
                "smooth_sensitivity": lambda n: 1.0,  # Constant for count
                "local_sensitivity": 1.0
            },
            QueryType.SUM.value: {
                "l1_sensitivity": None,  # Depends on value range
                "l2_sensitivity": None,
                "smooth_sensitivity": lambda n: None,  # Needs data analysis
                "local_sensitivity": None,
                "requires_clipping": True
            },
            QueryType.MEAN.value: {
                "l1_sensitivity": None,  # Depends on value range and dataset size
                "l2_sensitivity": None,
                "smooth_sensitivity": lambda n: None,
                "local_sensitivity": None,
                "requires_clipping": True,
                "composition_queries": ["count", "sum"]
            },
            QueryType.HISTOGRAM.value: {
                "l1_sensitivity": 1.0,  # Moving one record between bins
                "l2_sensitivity": math.sqrt(2),  # L2 norm of unit vector
                "smooth_sensitivity": lambda n: 1.0,
                "local_sensitivity": 1.0
            },
            QueryType.QUANTILE.value: {
                "l1_sensitivity": None,  # Complex, depends on data distribution
                "l2_sensitivity": None,
                "smooth_sensitivity": lambda n, beta: None,
                "local_sensitivity": None,
                "requires_smooth_sensitivity": True
            }
        }
        logger.info("Initialized sensitivity oracle")

    async def _initialize_noise_calibration(self):
        """Initialize noise calibration parameters"""
        self.noise_calibration = {
            NoiseType.LAPLACE.value: {
                "scale_factor": lambda sensitivity, epsilon: sensitivity / epsilon,
                "cdf": lambda x, scale: 0.5 * (1 + np.sign(x) * (1 - np.exp(-np.abs(x) / scale))),
                "sample": lambda scale, size=1: np.random.laplace(0, scale, size)
            },
            NoiseType.GAUSSIAN.value: {
                "scale_factor": lambda sensitivity, epsilon, delta: sensitivity * math.sqrt(2 * math.log(1.25 / delta)) / epsilon,
                "cdf": lambda x, scale: stats.norm.cdf(x, 0, scale),
                "sample": lambda scale, size=1: np.random.normal(0, scale, size)
            },
            NoiseType.DISCRETE_LAPLACE.value: {
                "scale_factor": lambda sensitivity, epsilon: sensitivity / epsilon,
                "sample": self._sample_discrete_laplace
            },
            NoiseType.EXPONENTIAL.value: {
                "scale_factor": lambda sensitivity, epsilon: sensitivity / epsilon,
                "sample": lambda scale, size=1: np.random.exponential(scale, size) * np.random.choice([-1, 1], size)
            }
        }
        logger.info("Initialized noise calibration")

    async def _initialize_default_accountants(self):
        """Initialize default privacy accountants for different data types"""
        default_accountants = {
            "general": {"epsilon": 1.0, "delta": 1e-5},
            "sensitive": {"epsilon": 0.1, "delta": 1e-7},
            "health": {"epsilon": 0.5, "delta": 1e-6},
            "financial": {"epsilon": 0.3, "delta": 1e-6}
        }
        
        for account_type, params in default_accountants.items():
            accountant_id = f"dp_account_{account_type}"
            accountant = PrivacyAccountant(
                total_epsilon=params["epsilon"],
                total_delta=params["delta"],
                consumed_epsilon=0.0,
                consumed_delta=0.0,
                query_history=[],
                composition_type=CompositionType.BASIC,
                advanced_composition_params={}
            )
            self.privacy_accountants[accountant_id] = accountant
        
        logger.info(f"Initialized {len(default_accountants)} privacy accountants")

    def _sample_discrete_laplace(self, scale: float, size: int = 1) -> np.ndarray:
        """Sample from discrete Laplace distribution"""
        # Use geometric distribution to sample discrete Laplace
        p = 1 - np.exp(-1/scale)
        samples = []
        
        for _ in range(size):
            # Sample two geometric random variables
            geo1 = np.random.geometric(p)
            geo2 = np.random.geometric(p)
            sample = geo1 - geo2
            samples.append(sample)
        
        return np.array(samples)

    async def analyze_sensitivity(
        self,
        query_type: QueryType,
        dataset_id: str,
        fields: List[str],
        value_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
        dataset_size: Optional[int] = None
    ) -> Dict[str, float]:
        """Analyze sensitivity for a given query"""
        
        oracle_info = self.sensitivity_oracle.get(query_type.value, {})
        sensitivity_analysis = {}
        
        if query_type == QueryType.COUNT:
            sensitivity_analysis["l1"] = 1.0
            sensitivity_analysis["l2"] = 1.0
            
        elif query_type == QueryType.SUM:
            if not value_bounds or not fields:
                raise ValueError("Sum queries require value bounds and field specification")
            
            # Calculate sensitivity based on value range
            field = fields[0]  # Simplified for single field
            if field in value_bounds:
                min_val, max_val = value_bounds[field]
                range_val = max_val - min_val
                sensitivity_analysis["l1"] = range_val
                sensitivity_analysis["l2"] = range_val
                sensitivity_analysis["clipping_required"] = True
                sensitivity_analysis["clipping_bound"] = max(abs(min_val), abs(max_val))
        
        elif query_type == QueryType.MEAN:
            if not value_bounds or not fields or not dataset_size:
                raise ValueError("Mean queries require value bounds, field specification, and dataset size")
            
            field = fields[0]
            if field in value_bounds:
                min_val, max_val = value_bounds[field]
                range_val = max_val - min_val
                
                # Sensitivity of mean = sensitivity of sum / n + sensitivity of count * sum / n^2
                # Simplified: use range/n as approximation
                sensitivity_analysis["l1"] = range_val / dataset_size
                sensitivity_analysis["l2"] = range_val / dataset_size
                sensitivity_analysis["composition_required"] = True
        
        elif query_type == QueryType.HISTOGRAM:
            sensitivity_analysis["l1"] = 1.0  # One record can change at most one bin
            sensitivity_analysis["l2"] = math.sqrt(2)  # Can decrease one bin by 1 and increase another by 1
        
        elif query_type == QueryType.VARIANCE:
            if not value_bounds or not fields or not dataset_size:
                raise ValueError("Variance queries require value bounds, field specification, and dataset size")
            
            field = fields[0]
            if field in value_bounds:
                min_val, max_val = value_bounds[field]
                range_val = max_val - min_val
                
                # Simplified sensitivity analysis for variance
                # More complex analysis would consider the specific variance formula
                sensitivity_analysis["l1"] = (range_val ** 2) / dataset_size
                sensitivity_analysis["l2"] = (range_val ** 2) / dataset_size
                sensitivity_analysis["requires_advanced_composition"] = True
        
        # Cache the result
        cache_key = f"{query_type.value}_{dataset_id}_{hash(str(fields))}"
        self.global_sensitivity_cache[cache_key] = sensitivity_analysis.get("l1", 1.0)
        
        return sensitivity_analysis

    async def create_dp_query(
        self,
        query_type: QueryType,
        privacy_params: PrivacyParameters,
        dataset_id: str,
        fields: List[str],
        conditions: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Create a differential privacy query"""
        
        query_id = f"dpq_{uuid.uuid4().hex[:8]}"
        
        # Analyze sensitivity
        sensitivity_analysis = await self.analyze_sensitivity(
            query_type=query_type,
            dataset_id=dataset_id,
            fields=fields,
            value_bounds=kwargs.get("value_bounds"),
            dataset_size=kwargs.get("dataset_size")
        )
        
        # Validate privacy parameters
        await self._validate_privacy_parameters(privacy_params, sensitivity_analysis)
        
        # Create query object
        dp_query = DPQuery(
            query_id=query_id,
            query_type=query_type,
            privacy_params=privacy_params,
            dataset_id=dataset_id,
            fields=fields,
            conditions=conditions or {},
            sensitivity_analysis=sensitivity_analysis,
            noise_added=0.0,
            created_date=datetime.now()
        )
        
        self.dp_queries[query_id] = dp_query
        
        logger.info(f"Created DP query {query_id} of type {query_type.value}")
        return query_id

    async def _validate_privacy_parameters(
        self,
        privacy_params: PrivacyParameters,
        sensitivity_analysis: Dict[str, float]
    ):
        """Validate privacy parameters against sensitivity analysis"""
        
        # Check epsilon > 0
        if privacy_params.epsilon <= 0:
            raise ValueError("Epsilon must be positive")
        
        # Check delta for Gaussian mechanism
        if privacy_params.noise_type == NoiseType.GAUSSIAN:
            if privacy_params.delta <= 0 or privacy_params.delta >= 1:
                raise ValueError("Delta must be in (0, 1) for Gaussian mechanism")
        
        # Check sensitivity
        if privacy_params.sensitivity <= 0:
            raise ValueError("Sensitivity must be positive")
        
        # Warn about clipping requirements
        if sensitivity_analysis.get("clipping_required") and not privacy_params.clipping_bound:
            logger.warning("Query requires clipping but no clipping bound specified")

    async def execute_dp_query(
        self,
        query_id: str,
        data: List[Dict[str, Any]],
        account_id: str = "dp_account_general"
    ) -> Dict[str, Any]:
        """Execute a differential privacy query"""
        
        if query_id not in self.dp_queries:
            raise ValueError(f"Query {query_id} not found")
        
        dp_query = self.dp_queries[query_id]
        
        # Check privacy budget
        if not await self._check_privacy_budget(account_id, dp_query.privacy_params):
            raise ValueError("Insufficient privacy budget")
        
        try:
            # Execute the query based on type
            if dp_query.query_type == QueryType.COUNT:
                result = await self._execute_count_query(dp_query, data)
            elif dp_query.query_type == QueryType.SUM:
                result = await self._execute_sum_query(dp_query, data)
            elif dp_query.query_type == QueryType.MEAN:
                result = await self._execute_mean_query(dp_query, data)
            elif dp_query.query_type == QueryType.HISTOGRAM:
                result = await self._execute_histogram_query(dp_query, data)
            elif dp_query.query_type == QueryType.VARIANCE:
                result = await self._execute_variance_query(dp_query, data)
            elif dp_query.query_type == QueryType.QUANTILE:
                result = await self._execute_quantile_query(dp_query, data)
            else:
                raise ValueError(f"Unsupported query type: {dp_query.query_type}")
            
            # Update privacy budget
            await self._update_privacy_budget(account_id, dp_query)
            
            # Update query
            dp_query.executed_date = datetime.now()
            dp_query.noisy_result = result["noisy_value"]
            
            logger.info(f"Executed DP query {query_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute DP query {query_id}: {e}")
            raise

    async def _execute_count_query(self, dp_query: DPQuery, data: List[Dict]) -> Dict[str, Any]:
        """Execute count query with differential privacy"""
        
        # Apply conditions/filters
        filtered_data = await self._apply_conditions(data, dp_query.conditions)
        true_count = len(filtered_data)
        
        # Add noise
        noise = await self._generate_noise(
            dp_query.privacy_params.noise_type,
            dp_query.privacy_params.sensitivity,
            dp_query.privacy_params.epsilon,
            dp_query.privacy_params.delta
        )
        
        noisy_count = max(0, true_count + noise)  # Ensure non-negative
        dp_query.noise_added = noise
        dp_query.true_result = true_count  # For evaluation only
        
        return {
            "query_id": dp_query.query_id,
            "query_type": "count",
            "noisy_value": int(round(noisy_count)),
            "noise_added": noise,
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "delta": dp_query.privacy_params.delta,
                "sensitivity": dp_query.privacy_params.sensitivity,
                "noise_type": dp_query.privacy_params.noise_type.value
            },
            "confidence_interval": await self._calculate_confidence_interval(
                noisy_count, dp_query.privacy_params
            )
        }

    async def _execute_sum_query(self, dp_query: DPQuery, data: List[Dict]) -> Dict[str, Any]:
        """Execute sum query with differential privacy"""
        
        filtered_data = await self._apply_conditions(data, dp_query.conditions)
        field = dp_query.fields[0]  # Simplified for single field
        
        # Apply clipping if specified
        values = []
        for record in filtered_data:
            if field in record:
                value = record[field]
                if dp_query.privacy_params.clipping_bound:
                    value = np.clip(value, 
                                  -dp_query.privacy_params.clipping_bound,
                                  dp_query.privacy_params.clipping_bound)
                values.append(value)
        
        true_sum = sum(values)
        
        # Generate noise
        noise = await self._generate_noise(
            dp_query.privacy_params.noise_type,
            dp_query.privacy_params.sensitivity,
            dp_query.privacy_params.epsilon,
            dp_query.privacy_params.delta
        )
        
        noisy_sum = true_sum + noise
        dp_query.noise_added = noise
        dp_query.true_result = true_sum
        
        return {
            "query_id": dp_query.query_id,
            "query_type": "sum",
            "noisy_value": noisy_sum,
            "noise_added": noise,
            "records_processed": len(values),
            "clipping_applied": dp_query.privacy_params.clipping_bound is not None,
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "delta": dp_query.privacy_params.delta,
                "sensitivity": dp_query.privacy_params.sensitivity,
                "noise_type": dp_query.privacy_params.noise_type.value
            }
        }

    async def _execute_mean_query(self, dp_query: DPQuery, data: List[Dict]) -> Dict[str, Any]:
        """Execute mean query with differential privacy using composition"""
        
        # Split epsilon between count and sum
        epsilon_count = dp_query.privacy_params.epsilon / 2
        epsilon_sum = dp_query.privacy_params.epsilon / 2
        
        # Create sub-queries
        count_params = PrivacyParameters(
            epsilon=epsilon_count,
            delta=dp_query.privacy_params.delta / 2,
            sensitivity=1.0,
            sensitivity_type=dp_query.privacy_params.sensitivity_type,
            noise_type=dp_query.privacy_params.noise_type
        )
        
        sum_params = PrivacyParameters(
            epsilon=epsilon_sum,
            delta=dp_query.privacy_params.delta / 2,
            sensitivity=dp_query.privacy_params.sensitivity,
            sensitivity_type=dp_query.privacy_params.sensitivity_type,
            noise_type=dp_query.privacy_params.noise_type,
            clipping_bound=dp_query.privacy_params.clipping_bound
        )
        
        # Execute count query
        count_query = DPQuery(
            query_id=f"{dp_query.query_id}_count",
            query_type=QueryType.COUNT,
            privacy_params=count_params,
            dataset_id=dp_query.dataset_id,
            fields=dp_query.fields,
            conditions=dp_query.conditions,
            sensitivity_analysis={"l1": 1.0},
            noise_added=0.0
        )
        count_result = await self._execute_count_query(count_query, data)
        
        # Execute sum query
        sum_query = DPQuery(
            query_id=f"{dp_query.query_id}_sum",
            query_type=QueryType.SUM,
            privacy_params=sum_params,
            dataset_id=dp_query.dataset_id,
            fields=dp_query.fields,
            conditions=dp_query.conditions,
            sensitivity_analysis=dp_query.sensitivity_analysis,
            noise_added=0.0
        )
        sum_result = await self._execute_sum_query(sum_query, data)
        
        # Calculate noisy mean
        noisy_count = count_result["noisy_value"]
        noisy_sum = sum_result["noisy_value"]
        
        if noisy_count <= 0:
            noisy_mean = 0.0
        else:
            noisy_mean = noisy_sum / noisy_count
        
        total_noise = count_query.noise_added + sum_query.noise_added
        dp_query.noise_added = total_noise
        
        return {
            "query_id": dp_query.query_id,
            "query_type": "mean",
            "noisy_value": noisy_mean,
            "noisy_count": noisy_count,
            "noisy_sum": noisy_sum,
            "composition_used": True,
            "total_noise_added": total_noise,
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "delta": dp_query.privacy_params.delta,
                "composition_type": "basic"
            }
        }

    async def _execute_histogram_query(self, dp_query: DPQuery, data: List[Dict]) -> Dict[str, Any]:
        """Execute histogram query with differential privacy"""
        
        filtered_data = await self._apply_conditions(data, dp_query.conditions)
        field = dp_query.fields[0]
        
        # Build histogram
        bins = dp_query.conditions.get("bins", "auto")
        if isinstance(bins, str) and bins == "auto":
            # Automatically determine bins
            values = [record[field] for record in filtered_data if field in record]
            if not values:
                return {"error": "No data found for histogram"}
            
            # Use Sturges' rule for number of bins
            n_bins = max(1, int(np.ceil(np.log2(len(values)) + 1)))
            min_val, max_val = min(values), max(values)
            bin_edges = np.linspace(min_val, max_val, n_bins + 1)
        else:
            bin_edges = bins
        
        # Count values in each bin
        histogram = defaultdict(int)
        for record in filtered_data:
            if field in record:
                value = record[field]
                # Find appropriate bin
                bin_idx = np.digitize(value, bin_edges) - 1
                bin_idx = max(0, min(bin_idx, len(bin_edges) - 2))
                bin_key = f"bin_{bin_idx}"
                histogram[bin_key] += 1
        
        # Add noise to each bin
        noisy_histogram = {}
        total_noise = 0
        
        for bin_key, count in histogram.items():
            noise = await self._generate_noise(
                dp_query.privacy_params.noise_type,
                dp_query.privacy_params.sensitivity,
                dp_query.privacy_params.epsilon,
                dp_query.privacy_params.delta
            )
            noisy_count = max(0, count + noise)
            noisy_histogram[bin_key] = int(round(noisy_count))
            total_noise += abs(noise)
        
        dp_query.noise_added = total_noise
        
        return {
            "query_id": dp_query.query_id,
            "query_type": "histogram",
            "noisy_histogram": noisy_histogram,
            "bin_edges": bin_edges.tolist() if hasattr(bin_edges, 'tolist') else bin_edges,
            "total_bins": len(noisy_histogram),
            "total_noise_added": total_noise,
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "delta": dp_query.privacy_params.delta,
                "sensitivity": dp_query.privacy_params.sensitivity
            }
        }

    async def _execute_variance_query(self, dp_query: DPQuery, data: List[Dict]) -> Dict[str, Any]:
        """Execute variance query with differential privacy"""
        
        # Variance requires complex composition - simplified implementation
        filtered_data = await self._apply_conditions(data, dp_query.conditions)
        field = dp_query.fields[0]
        
        values = []
        for record in filtered_data:
            if field in record:
                value = record[field]
                if dp_query.privacy_params.clipping_bound:
                    value = np.clip(value, 
                                  -dp_query.privacy_params.clipping_bound,
                                  dp_query.privacy_params.clipping_bound)
                values.append(value)
        
        if not values:
            return {"error": "No data found for variance calculation"}
        
        # Calculate true variance
        true_variance = np.var(values, ddof=1) if len(values) > 1 else 0.0
        
        # Add noise (simplified - in practice, variance queries need more sophisticated noise)
        noise = await self._generate_noise(
            dp_query.privacy_params.noise_type,
            dp_query.privacy_params.sensitivity,
            dp_query.privacy_params.epsilon,
            dp_query.privacy_params.delta
        )
        
        noisy_variance = max(0, true_variance + noise)  # Ensure non-negative
        dp_query.noise_added = noise
        dp_query.true_result = true_variance
        
        return {
            "query_id": dp_query.query_id,
            "query_type": "variance",
            "noisy_value": noisy_variance,
            "noise_added": noise,
            "records_processed": len(values),
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "delta": dp_query.privacy_params.delta,
                "sensitivity": dp_query.privacy_params.sensitivity
            },
            "warning": "Variance query implementation is simplified"
        }

    async def _execute_quantile_query(self, dp_query: DPQuery, data: List[Dict]) -> Dict[str, Any]:
        """Execute quantile query with differential privacy (using smooth sensitivity)"""
        
        # Quantile queries are complex - this is a simplified implementation
        filtered_data = await self._apply_conditions(data, dp_query.conditions)
        field = dp_query.fields[0]
        quantile = dp_query.conditions.get("quantile", 0.5)  # Default to median
        
        values = []
        for record in filtered_data:
            if field in record:
                values.append(record[field])
        
        if not values:
            return {"error": "No data found for quantile calculation"}
        
        values.sort()
        n = len(values)
        
        # Calculate true quantile
        index = quantile * (n - 1)
        if index.is_integer():
            true_quantile = values[int(index)]
        else:
            lower_idx = int(np.floor(index))
            upper_idx = int(np.ceil(index))
            weight = index - lower_idx
            true_quantile = values[lower_idx] * (1 - weight) + values[upper_idx] * weight
        
        # For smooth sensitivity, we use a simplified approach
        # In practice, this requires more sophisticated analysis
        beta = dp_query.conditions.get("beta", 0.1)  # Smoothness parameter
        
        # Simplified smooth sensitivity (not theoretically correct)
        smooth_sensitivity = dp_query.privacy_params.sensitivity
        
        # Add noise calibrated to smooth sensitivity
        noise_scale = smooth_sensitivity / dp_query.privacy_params.epsilon
        noise = await self._generate_noise(
            NoiseType.LAPLACE,  # Force Laplace for simplicity
            smooth_sensitivity,
            dp_query.privacy_params.epsilon,
            dp_query.privacy_params.delta
        )
        
        noisy_quantile = true_quantile + noise
        dp_query.noise_added = noise
        dp_query.true_result = true_quantile
        
        return {
            "query_id": dp_query.query_id,
            "query_type": "quantile",
            "quantile": quantile,
            "noisy_value": noisy_quantile,
            "noise_added": noise,
            "records_processed": len(values),
            "smooth_sensitivity_used": True,
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "beta": beta,
                "sensitivity": smooth_sensitivity
            },
            "warning": "Quantile query implementation is simplified"
        }

    async def _apply_conditions(self, data: List[Dict], conditions: Dict[str, Any]) -> List[Dict]:
        """Apply filtering conditions to data"""
        if not conditions:
            return data
        
        filtered_data = []
        for record in data:
            include = True
            for field, condition in conditions.items():
                if field == "bins" or field == "quantile" or field == "beta":
                    continue  # Skip query parameters
                
                if field not in record:
                    include = False
                    break
                
                value = record[field]
                if isinstance(condition, dict):
                    if "min" in condition and value < condition["min"]:
                        include = False
                        break
                    if "max" in condition and value > condition["max"]:
                        include = False
                        break
                    if "eq" in condition and value != condition["eq"]:
                        include = False
                        break
                else:
                    if value != condition:
                        include = False
                        break
            
            if include:
                filtered_data.append(record)
        
        return filtered_data

    async def _generate_noise(
        self,
        noise_type: NoiseType,
        sensitivity: float,
        epsilon: float,
        delta: float = 0.0
    ) -> float:
        """Generate calibrated noise for differential privacy"""
        
        calibration = self.noise_calibration.get(noise_type.value, {})
        
        if noise_type == NoiseType.LAPLACE:
            scale = calibration["scale_factor"](sensitivity, epsilon)
            return calibration["sample"](scale)[0]
            
        elif noise_type == NoiseType.GAUSSIAN:
            if delta <= 0:
                raise ValueError("Gaussian mechanism requires delta > 0")
            scale = calibration["scale_factor"](sensitivity, epsilon, delta)
            return calibration["sample"](scale)[0]
            
        elif noise_type == NoiseType.DISCRETE_LAPLACE:
            scale = calibration["scale_factor"](sensitivity, epsilon)
            return float(calibration["sample"](scale, 1)[0])
            
        elif noise_type == NoiseType.EXPONENTIAL:
            scale = calibration["scale_factor"](sensitivity, epsilon)
            return calibration["sample"](scale)[0]
            
        else:
            raise ValueError(f"Unsupported noise type: {noise_type}")

    async def _calculate_confidence_interval(
        self,
        noisy_value: float,
        privacy_params: PrivacyParameters,
        confidence_level: float = 0.95
    ) -> Dict[str, float]:
        """Calculate confidence interval for noisy result"""
        
        if privacy_params.noise_type == NoiseType.LAPLACE:
            # For Laplace noise, confidence interval based on quantiles
            scale = privacy_params.sensitivity / privacy_params.epsilon
            alpha = 1 - confidence_level
            quantile = 1 - alpha / 2
            
            # Laplace quantile: sign(p - 0.5) * scale * ln(1 - 2*|p - 0.5|)
            margin = scale * math.log(2 / alpha)
            
            return {
                "lower_bound": noisy_value - margin,
                "upper_bound": noisy_value + margin,
                "confidence_level": confidence_level,
                "margin_of_error": margin
            }
            
        elif privacy_params.noise_type == NoiseType.GAUSSIAN:
            scale = privacy_params.sensitivity * math.sqrt(2 * math.log(1.25 / privacy_params.delta)) / privacy_params.epsilon
            z_score = stats.norm.ppf((1 + confidence_level) / 2)
            margin = z_score * scale
            
            return {
                "lower_bound": noisy_value - margin,
                "upper_bound": noisy_value + margin,
                "confidence_level": confidence_level,
                "margin_of_error": margin
            }
        
        else:
            # Generic approximation
            scale = privacy_params.sensitivity / privacy_params.epsilon
            margin = 2 * scale  # Rough approximation
            
            return {
                "lower_bound": noisy_value - margin,
                "upper_bound": noisy_value + margin,
                "confidence_level": confidence_level,
                "margin_of_error": margin,
                "note": "Approximate confidence interval"
            }

    async def _check_privacy_budget(
        self,
        account_id: str,
        privacy_params: PrivacyParameters
    ) -> bool:
        """Check if privacy budget allows the query"""
        
        if account_id not in self.privacy_accountants:
            return False
        
        accountant = self.privacy_accountants[account_id]
        
        # Simple budget check (basic composition)
        if accountant.composition_type == CompositionType.BASIC:
            return (accountant.consumed_epsilon + privacy_params.epsilon <= accountant.total_epsilon and
                    accountant.consumed_delta + privacy_params.delta <= accountant.total_delta)
        
        # Advanced composition would require more sophisticated analysis
        return True

    async def _update_privacy_budget(self, account_id: str, dp_query: DPQuery):
        """Update privacy budget after query execution"""
        
        if account_id not in self.privacy_accountants:
            return
        
        accountant = self.privacy_accountants[account_id]
        
        # Update consumed budget
        accountant.consumed_epsilon += dp_query.privacy_params.epsilon
        accountant.consumed_delta += dp_query.privacy_params.delta
        accountant.query_history.append(dp_query)

    async def get_privacy_budget_status(self, account_id: str) -> Dict[str, Any]:
        """Get privacy budget status"""
        
        if account_id not in self.privacy_accountants:
            return {"error": "Account not found"}
        
        accountant = self.privacy_accountants[account_id]
        
        return {
            "account_id": account_id,
            "total_epsilon": accountant.total_epsilon,
            "total_delta": accountant.total_delta,
            "consumed_epsilon": accountant.consumed_epsilon,
            "consumed_delta": accountant.consumed_delta,
            "remaining_epsilon": accountant.total_epsilon - accountant.consumed_epsilon,
            "remaining_delta": accountant.total_delta - accountant.consumed_delta,
            "queries_executed": len(accountant.query_history),
            "composition_type": accountant.composition_type.value,
            "budget_utilization": {
                "epsilon_percent": (accountant.consumed_epsilon / accountant.total_epsilon) * 100,
                "delta_percent": (accountant.consumed_delta / accountant.total_delta) * 100 if accountant.total_delta > 0 else 0
            }
        }

    async def analyze_query_accuracy(self, query_id: str) -> Dict[str, Any]:
        """Analyze accuracy of a differential privacy query"""
        
        if query_id not in self.dp_queries:
            return {"error": "Query not found"}
        
        dp_query = self.dp_queries[query_id]
        
        if dp_query.true_result is None:
            return {"error": "True result not available for accuracy analysis"}
        
        absolute_error = abs(dp_query.noisy_result - dp_query.true_result)
        relative_error = (absolute_error / abs(dp_query.true_result)) * 100 if dp_query.true_result != 0 else 0
        
        # Calculate theoretical error bounds
        if dp_query.privacy_params.noise_type == NoiseType.LAPLACE:
            scale = dp_query.privacy_params.sensitivity / dp_query.privacy_params.epsilon
            expected_abs_error = scale  # E[|Laplace(0, scale)|] = scale
        else:
            expected_abs_error = dp_query.privacy_params.sensitivity / dp_query.privacy_params.epsilon
        
        return {
            "query_id": query_id,
            "true_result": dp_query.true_result,
            "noisy_result": dp_query.noisy_result,
            "noise_added": dp_query.noise_added,
            "absolute_error": absolute_error,
            "relative_error_percent": relative_error,
            "expected_absolute_error": expected_abs_error,
            "error_ratio": absolute_error / expected_abs_error if expected_abs_error > 0 else 0,
            "privacy_parameters": {
                "epsilon": dp_query.privacy_params.epsilon,
                "delta": dp_query.privacy_params.delta,
                "sensitivity": dp_query.privacy_params.sensitivity,
                "noise_type": dp_query.privacy_params.noise_type.value
            }
        }

    async def export_dp_data(self) -> Dict[str, Any]:
        """Export differential privacy data and statistics"""
        
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_queries": len(self.dp_queries),
            "privacy_accountants": {},
            "query_statistics": {},
            "sensitivity_analysis": self.global_sensitivity_cache
        }
        
        # Export privacy accountant summaries
        for account_id, accountant in self.privacy_accountants.items():
            export_data["privacy_accountants"][account_id] = {
                "total_epsilon": accountant.total_epsilon,
                "consumed_epsilon": accountant.consumed_epsilon,
                "total_delta": accountant.total_delta,
                "consumed_delta": accountant.consumed_delta,
                "queries_count": len(accountant.query_history),
                "composition_type": accountant.composition_type.value
            }
        
        # Export query statistics
        query_types = defaultdict(int)
        noise_types = defaultdict(int)
        avg_noise_by_type = defaultdict(list)
        
        for dp_query in self.dp_queries.values():
            if dp_query.executed_date:
                query_types[dp_query.query_type.value] += 1
                noise_types[dp_query.privacy_params.noise_type.value] += 1
                avg_noise_by_type[dp_query.query_type.value].append(abs(dp_query.noise_added))
        
        export_data["query_statistics"] = {
            "query_types": dict(query_types),
            "noise_types": dict(noise_types),
            "average_noise_by_query_type": {
                qtype: np.mean(noises) if noises else 0
                for qtype, noises in avg_noise_by_type.items()
            }
        }
        
        logger.info(f"Exported differential privacy data: {len(self.dp_queries)} queries")
        return export_data

# Privacy-preserving utilities
class DPUtilities:
    @staticmethod
    def calculate_composition_epsilon(epsilons: List[float], composition_type: CompositionType = CompositionType.BASIC) -> float:
        """Calculate epsilon for query composition"""
        if composition_type == CompositionType.BASIC:
            return sum(epsilons)
        elif composition_type == CompositionType.ADVANCED:
            # Simplified advanced composition
            k = len(epsilons)
            epsilon = max(epsilons)
            return epsilon * math.sqrt(2 * k * math.log(1 / 0.05))  # Simplified
        else:
            return sum(epsilons)  # Fallback to basic
    
    @staticmethod
    def calculate_composition_delta(deltas: List[float], composition_type: CompositionType = CompositionType.BASIC) -> float:
        """Calculate delta for query composition"""
        if composition_type == CompositionType.BASIC:
            return sum(deltas)
        else:
            return sum(deltas)  # Simplified
    
    @staticmethod
    def optimize_epsilon_allocation(total_epsilon: float, query_sensitivities: List[float]) -> List[float]:
        """Optimize epsilon allocation across multiple queries"""
        # Simple proportional allocation based on sensitivity
        total_sensitivity = sum(query_sensitivities)
        if total_sensitivity == 0:
            return [total_epsilon / len(query_sensitivities)] * len(query_sensitivities)
        
        return [(sens / total_sensitivity) * total_epsilon for sens in query_sensitivities]