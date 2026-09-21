import asyncio
import logging
import json
import math
import numpy as np
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from enum import Enum
from dataclasses import dataclass
import uuid
import secrets
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class PrivacyTechnique(Enum):
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    K_ANONYMITY = "k_anonymity"
    L_DIVERSITY = "l_diversity"
    T_CLOSENESS = "t_closeness"
    SYNTHETIC_DATA = "synthetic_data"
    FEDERATED_LEARNING = "federated_learning"
    SECURE_AGGREGATION = "secure_aggregation"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"

class NoiseType(Enum):
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"

class AggregationType(Enum):
    COUNT = "count"
    SUM = "sum"
    MEAN = "mean"
    MEDIAN = "median"
    MIN = "min"
    MAX = "max"
    VARIANCE = "variance"
    HISTOGRAM = "histogram"
    QUANTILE = "quantile"

class AnalyticsQuery(Enum):
    STATISTICAL_SUMMARY = "statistical_summary"
    FREQUENCY_ANALYSIS = "frequency_analysis"
    CORRELATION_ANALYSIS = "correlation_analysis"
    TREND_ANALYSIS = "trend_analysis"
    COHORT_ANALYSIS = "cohort_analysis"
    SEGMENTATION_ANALYSIS = "segmentation_analysis"

@dataclass
class PrivacyBudget:
    total_epsilon: float
    consumed_epsilon: float
    remaining_epsilon: float
    delta: float
    time_window: timedelta
    reset_time: datetime
    queries_count: int
    max_queries: int

@dataclass
class AnalyticsRequest:
    request_id: str
    requester_id: str
    query_type: AnalyticsQuery
    dataset_id: str
    fields: List[str]
    filters: Dict[str, Any]
    aggregation_type: AggregationType
    privacy_technique: PrivacyTechnique
    privacy_parameters: Dict[str, Any]
    epsilon: Optional[float]
    delta: Optional[float]
    min_group_size: int
    created_date: datetime
    approved: bool
    executed: bool
    result_id: Optional[str]

@dataclass
class AnalyticsResult:
    result_id: str
    request_id: str
    query_type: AnalyticsQuery
    result_data: Dict[str, Any]
    privacy_technique_used: PrivacyTechnique
    epsilon_consumed: float
    delta_consumed: float
    noise_added: bool
    uncertainty_bounds: Optional[Dict[str, float]]
    data_points_analyzed: int
    suppressed_values: int
    execution_time: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class KAnonymityGroup:
    group_id: str
    quasi_identifiers: Dict[str, Any]
    group_size: int
    sensitive_values: List[Any]
    diversity_count: int
    closeness_score: float

@dataclass
class SyntheticDataModel:
    model_id: str
    dataset_id: str
    model_type: str  # GAN, VAE, etc.
    privacy_epsilon: float
    model_parameters: Dict[str, Any]
    training_date: datetime
    synthetic_samples_generated: int
    utility_metrics: Dict[str, float]
    privacy_metrics: Dict[str, float]

class PrivacyPreservingAnalytics:
    def __init__(self):
        self.privacy_budgets: Dict[str, PrivacyBudget] = {}
        self.analytics_requests: Dict[str, AnalyticsRequest] = {}
        self.analytics_results: Dict[str, AnalyticsResult] = {}
        self.k_anonymity_groups: Dict[str, List[KAnonymityGroup]] = {}
        self.synthetic_models: Dict[str, SyntheticDataModel] = {}
        self.query_history: Dict[str, List[str]] = defaultdict(list)
        self.noise_calibration: Dict[str, Dict] = {}
        logger.info("Privacy-Preserving Analytics Manager initialized")

    async def initialize(self):
        await self._initialize_privacy_budgets()
        await self._initialize_noise_calibration()
        await self._initialize_synthetic_data_models()
        logger.info("Privacy-Preserving Analytics Manager initialization completed")

    async def _initialize_privacy_budgets(self):
        # Default privacy budgets for different data types
        default_budgets = {
            "personal_data": {"epsilon": 1.0, "delta": 1e-5, "max_queries": 100},
            "health_data": {"epsilon": 0.5, "delta": 1e-6, "max_queries": 50},
            "financial_data": {"epsilon": 0.3, "delta": 1e-7, "max_queries": 30},
            "sensitive_data": {"epsilon": 0.1, "delta": 1e-8, "max_queries": 10},
            "public_data": {"epsilon": 5.0, "delta": 1e-3, "max_queries": 1000}
        }
        
        for data_type, budget_params in default_budgets.items():
            budget_id = f"budget_{data_type}"
            budget = PrivacyBudget(
                total_epsilon=budget_params["epsilon"],
                consumed_epsilon=0.0,
                remaining_epsilon=budget_params["epsilon"],
                delta=budget_params["delta"],
                time_window=timedelta(days=30),  # Monthly reset
                reset_time=datetime.now() + timedelta(days=30),
                queries_count=0,
                max_queries=budget_params["max_queries"]
            )
            self.privacy_budgets[budget_id] = budget
        
        logger.info(f"Initialized {len(default_budgets)} privacy budgets")

    async def _initialize_noise_calibration(self):
        # Calibrate noise parameters for different query types and sensitivities
        self.noise_calibration = {
            AggregationType.COUNT.value: {
                "sensitivity": 1,
                "noise_multiplier": 1.0,
                "min_threshold": 5
            },
            AggregationType.SUM.value: {
                "sensitivity": 1,  # Depends on data range
                "noise_multiplier": 1.0,
                "min_threshold": 0
            },
            AggregationType.MEAN.value: {
                "sensitivity": 2,  # Bounded by data range
                "noise_multiplier": 1.2,
                "min_threshold": 0
            },
            AggregationType.MEDIAN.value: {
                "sensitivity": 1,  # Depends on data range
                "noise_multiplier": 1.5,
                "min_threshold": 0
            },
            AggregationType.HISTOGRAM.value: {
                "sensitivity": 1,
                "noise_multiplier": 0.8,
                "min_threshold": 3
            }
        }
        logger.info("Initialized noise calibration parameters")

    async def _initialize_synthetic_data_models(self):
        # Initialize synthetic data generation capabilities
        self.synthetic_model_templates = {
            "demographic": {
                "model_type": "tabular_gan",
                "features": ["age", "gender", "location", "occupation"],
                "privacy_epsilon": 1.0,
                "utility_threshold": 0.8
            },
            "transactional": {
                "model_type": "sequence_gan",
                "features": ["amount", "category", "timestamp", "merchant"],
                "privacy_epsilon": 0.5,
                "utility_threshold": 0.7
            },
            "behavioral": {
                "model_type": "lstm_vae",
                "features": ["action", "timestamp", "duration", "context"],
                "privacy_epsilon": 0.3,
                "utility_threshold": 0.6
            }
        }
        logger.info("Initialized synthetic data model templates")

    async def submit_analytics_request(
        self,
        requester_id: str,
        query_type: AnalyticsQuery,
        dataset_id: str,
        fields: List[str],
        aggregation_type: AggregationType,
        privacy_technique: PrivacyTechnique,
        **kwargs
    ) -> str:
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        
        # Extract privacy parameters
        privacy_parameters = kwargs.get("privacy_parameters", {})
        epsilon = kwargs.get("epsilon", 1.0)
        delta = kwargs.get("delta", 1e-5)
        min_group_size = kwargs.get("min_group_size", 5)
        
        # Create analytics request
        request = AnalyticsRequest(
            request_id=request_id,
            requester_id=requester_id,
            query_type=query_type,
            dataset_id=dataset_id,
            fields=fields,
            filters=kwargs.get("filters", {}),
            aggregation_type=aggregation_type,
            privacy_technique=privacy_technique,
            privacy_parameters=privacy_parameters,
            epsilon=epsilon,
            delta=delta,
            min_group_size=min_group_size,
            created_date=datetime.now(),
            approved=False,
            executed=False,
            result_id=None
        )
        
        self.analytics_requests[request_id] = request
        
        # Auto-approve for demonstration (in production, this would require approval workflow)
        await self._approve_request(request_id)
        
        logger.info(f"Submitted analytics request {request_id} for {query_type.value}")
        return request_id

    async def _approve_request(self, request_id: str) -> bool:
        if request_id not in self.analytics_requests:
            return False
        
        request = self.analytics_requests[request_id]
        
        # Check privacy budget availability
        budget_available = await self._check_privacy_budget(
            request.dataset_id, request.epsilon or 1.0
        )
        
        if not budget_available:
            logger.warning(f"Privacy budget exceeded for request {request_id}")
            return False
        
        # Approve request
        request.approved = True
        logger.info(f"Approved analytics request {request_id}")
        return True

    async def _check_privacy_budget(self, dataset_id: str, requested_epsilon: float) -> bool:
        # Determine appropriate budget based on dataset type
        budget_key = await self._get_budget_key(dataset_id)
        
        if budget_key not in self.privacy_budgets:
            return False
        
        budget = self.privacy_budgets[budget_key]
        
        # Check if budget allows this query
        return (budget.remaining_epsilon >= requested_epsilon and
                budget.queries_count < budget.max_queries)

    async def _get_budget_key(self, dataset_id: str) -> str:
        # Simple mapping - in production, this would query dataset metadata
        if "health" in dataset_id.lower():
            return "budget_health_data"
        elif "financial" in dataset_id.lower():
            return "budget_financial_data"
        elif "sensitive" in dataset_id.lower():
            return "budget_sensitive_data"
        else:
            return "budget_personal_data"

    async def execute_analytics_request(self, request_id: str) -> Optional[str]:
        if request_id not in self.analytics_requests:
            return None
        
        request = self.analytics_requests[request_id]
        
        if not request.approved or request.executed:
            return None
        
        try:
            # Route to appropriate analytics method
            if request.privacy_technique == PrivacyTechnique.DIFFERENTIAL_PRIVACY:
                result = await self._execute_differential_privacy_query(request)
            elif request.privacy_technique == PrivacyTechnique.K_ANONYMITY:
                result = await self._execute_k_anonymity_query(request)
            elif request.privacy_technique == PrivacyTechnique.SYNTHETIC_DATA:
                result = await self._execute_synthetic_data_query(request)
            elif request.privacy_technique == PrivacyTechnique.SECURE_AGGREGATION:
                result = await self._execute_secure_aggregation_query(request)
            else:
                logger.error(f"Unsupported privacy technique: {request.privacy_technique}")
                return None
            
            if result:
                # Update privacy budget
                await self._update_privacy_budget(
                    request.dataset_id, request.epsilon or 1.0
                )
                
                # Mark request as executed
                request.executed = True
                request.result_id = result.result_id
                
                # Store result
                self.analytics_results[result.result_id] = result
                
                logger.info(f"Executed analytics request {request_id}")
                return result.result_id
            
        except Exception as e:
            logger.error(f"Failed to execute analytics request {request_id}: {e}")
        
        return None

    async def _execute_differential_privacy_query(self, request: AnalyticsRequest) -> AnalyticsResult:
        # Simulate data retrieval (in production, this would query actual data)
        raw_data = await self._simulate_data_retrieval(request)
        
        # Apply differential privacy
        if request.aggregation_type == AggregationType.COUNT:
            result_value = await self._dp_count(raw_data, request.epsilon or 1.0)
        elif request.aggregation_type == AggregationType.SUM:
            result_value = await self._dp_sum(raw_data, request.epsilon or 1.0, request.privacy_parameters)
        elif request.aggregation_type == AggregationType.MEAN:
            result_value = await self._dp_mean(raw_data, request.epsilon or 1.0, request.privacy_parameters)
        elif request.aggregation_type == AggregationType.HISTOGRAM:
            result_value = await self._dp_histogram(raw_data, request.epsilon or 1.0, request.privacy_parameters)
        else:
            raise ValueError(f"Unsupported aggregation type: {request.aggregation_type}")
        
        # Calculate uncertainty bounds
        uncertainty_bounds = await self._calculate_uncertainty_bounds(
            result_value, request.epsilon or 1.0, request.aggregation_type
        )
        
        result_id = f"result_{uuid.uuid4().hex[:8]}"
        return AnalyticsResult(
            result_id=result_id,
            request_id=request.request_id,
            query_type=request.query_type,
            result_data={"value": result_value, "type": request.aggregation_type.value},
            privacy_technique_used=PrivacyTechnique.DIFFERENTIAL_PRIVACY,
            epsilon_consumed=request.epsilon or 1.0,
            delta_consumed=request.delta or 1e-5,
            noise_added=True,
            uncertainty_bounds=uncertainty_bounds,
            data_points_analyzed=len(raw_data),
            suppressed_values=0,
            execution_time=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            metadata={
                "noise_type": "laplace",
                "sensitivity": self._get_sensitivity(request.aggregation_type),
                "fields_analyzed": request.fields
            }
        )

    async def _simulate_data_retrieval(self, request: AnalyticsRequest) -> List[Dict[str, Any]]:
        # Simulate realistic data based on request
        data_size = np.random.randint(100, 10000)
        
        if "demographic" in request.dataset_id:
            return [
                {
                    "age": np.random.randint(18, 80),
                    "income": np.random.normal(50000, 15000),
                    "location": np.random.choice(["urban", "suburban", "rural"]),
                    "education": np.random.choice(["high_school", "college", "graduate"])
                }
                for _ in range(data_size)
            ]
        elif "transaction" in request.dataset_id:
            return [
                {
                    "amount": np.random.exponential(50),
                    "category": np.random.choice(["food", "transport", "entertainment", "utilities"]),
                    "timestamp": datetime.now() - timedelta(days=np.random.randint(1, 365)),
                    "user_id": f"user_{np.random.randint(1, 1000)}"
                }
                for _ in range(data_size)
            ]
        else:
            # Generic numerical data
            return [
                {"value": np.random.normal(100, 25)} for _ in range(data_size)
            ]

    async def _dp_count(self, data: List[Dict], epsilon: float) -> float:
        # True count
        true_count = len(data)
        
        # Add Laplace noise
        sensitivity = 1  # Adding/removing one record changes count by at most 1
        noise_scale = sensitivity / epsilon
        noise = np.random.laplace(0, noise_scale)
        
        noisy_count = max(0, true_count + noise)  # Ensure non-negative
        return round(noisy_count)

    async def _dp_sum(self, data: List[Dict], epsilon: float, params: Dict) -> float:
        field = params.get("field", "value")
        clipping_bound = params.get("clipping_bound", 1000)
        
        # Extract values and clip them
        values = []
        for record in data:
            if field in record:
                # Clip values to bound sensitivity
                clipped_value = max(-clipping_bound, min(clipping_bound, record[field]))
                values.append(clipped_value)
        
        true_sum = sum(values)
        
        # Sensitivity is the clipping bound
        sensitivity = clipping_bound
        noise_scale = sensitivity / epsilon
        noise = np.random.laplace(0, noise_scale)
        
        return true_sum + noise

    async def _dp_mean(self, data: List[Dict], epsilon: float, params: Dict) -> float:
        field = params.get("field", "value")
        clipping_bound = params.get("clipping_bound", 1000)
        
        # Use composition: split epsilon between count and sum
        epsilon_count = epsilon / 2
        epsilon_sum = epsilon / 2
        
        # Get noisy count and sum
        noisy_count = await self._dp_count(data, epsilon_count)
        noisy_sum = await self._dp_sum(data, epsilon_sum, params)
        
        if noisy_count == 0:
            return 0.0
        
        return noisy_sum / noisy_count

    async def _dp_histogram(self, data: List[Dict], epsilon: float, params: Dict) -> Dict[str, float]:
        field = params.get("field", "category")
        bins = params.get("bins", None)
        
        # Count occurrences
        counter = Counter()
        for record in data:
            if field in record:
                counter[record[field]] += 1
        
        # Add noise to each bin
        sensitivity = 1  # Adding/removing one record changes one bin by at most 1
        noise_scale = sensitivity / epsilon
        
        noisy_histogram = {}
        for bin_name, count in counter.items():
            noise = np.random.laplace(0, noise_scale)
            noisy_count = max(0, count + noise)  # Ensure non-negative
            noisy_histogram[bin_name] = round(noisy_count)
        
        return noisy_histogram

    async def _execute_k_anonymity_query(self, request: AnalyticsRequest) -> AnalyticsResult:
        # Simulate k-anonymity processing
        raw_data = await self._simulate_data_retrieval(request)
        k = request.privacy_parameters.get("k", 5)
        
        # Create k-anonymous groups
        groups = await self._create_k_anonymous_groups(
            raw_data, request.fields, k
        )
        
        # Apply aggregation to groups
        if request.aggregation_type == AggregationType.COUNT:
            result_data = {"total_groups": len(groups), "min_group_size": k}
        elif request.aggregation_type == AggregationType.MEAN:
            field = request.privacy_parameters.get("target_field", "value")
            group_means = []
            for group in groups:
                if group.group_size >= k:
                    # Calculate mean for this group (simplified)
                    group_means.append(np.random.normal(100, 25))  # Simulated
            result_data = {"group_means": group_means, "total_groups": len(groups)}
        else:
            result_data = {"error": "Unsupported aggregation for k-anonymity"}
        
        # Calculate suppressed values
        total_records = len(raw_data)
        records_in_groups = sum(g.group_size for g in groups if g.group_size >= k)
        suppressed_values = total_records - records_in_groups
        
        result_id = f"result_{uuid.uuid4().hex[:8]}"
        return AnalyticsResult(
            result_id=result_id,
            request_id=request.request_id,
            query_type=request.query_type,
            result_data=result_data,
            privacy_technique_used=PrivacyTechnique.K_ANONYMITY,
            epsilon_consumed=0.0,  # K-anonymity doesn't use differential privacy
            delta_consumed=0.0,
            noise_added=False,
            uncertainty_bounds=None,
            data_points_analyzed=records_in_groups,
            suppressed_values=suppressed_values,
            execution_time=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            metadata={
                "k_value": k,
                "total_groups": len(groups),
                "quasi_identifiers": request.fields
            }
        )

    async def _create_k_anonymous_groups(
        self,
        data: List[Dict],
        quasi_identifiers: List[str],
        k: int
    ) -> List[KAnonymityGroup]:
        # Group records by quasi-identifier values
        groups_dict = defaultdict(list)
        
        for record in data:
            # Create key from quasi-identifiers
            key_parts = []
            for qi in quasi_identifiers:
                if qi in record:
                    # Generalize values for k-anonymity
                    generalized_value = await self._generalize_value(qi, record[qi])
                    key_parts.append(str(generalized_value))
            
            key = "|".join(key_parts)
            groups_dict[key].append(record)
        
        # Create KAnonymityGroup objects
        groups = []
        for key, records in groups_dict.items():
            if len(records) >= k:
                group_id = f"group_{uuid.uuid4().hex[:8]}"
                
                # Parse key back to quasi-identifier values
                key_parts = key.split("|")
                qi_values = dict(zip(quasi_identifiers, key_parts))
                
                # Extract sensitive values (non-QI attributes)
                sensitive_values = []
                for record in records:
                    for attr, value in record.items():
                        if attr not in quasi_identifiers:
                            sensitive_values.append(value)
                
                group = KAnonymityGroup(
                    group_id=group_id,
                    quasi_identifiers=qi_values,
                    group_size=len(records),
                    sensitive_values=sensitive_values,
                    diversity_count=len(set(sensitive_values)),
                    closeness_score=0.0  # Simplified
                )
                
                groups.append(group)
        
        return groups

    async def _generalize_value(self, attribute: str, value: Any) -> Any:
        # Simple generalization rules
        if attribute == "age" and isinstance(value, (int, float)):
            # Age ranges
            if value < 25:
                return "18-24"
            elif value < 35:
                return "25-34"
            elif value < 45:
                return "35-44"
            elif value < 55:
                return "45-54"
            elif value < 65:
                return "55-64"
            else:
                return "65+"
        elif attribute == "income" and isinstance(value, (int, float)):
            # Income ranges
            if value < 30000:
                return "low"
            elif value < 70000:
                return "medium"
            else:
                return "high"
        elif attribute == "location":
            # Keep as is for simplicity
            return value
        else:
            return str(value)

    async def _execute_synthetic_data_query(self, request: AnalyticsRequest) -> AnalyticsResult:
        # Generate synthetic data and perform query
        model_type = request.privacy_parameters.get("model_type", "tabular")
        sample_size = request.privacy_parameters.get("sample_size", 1000)
        
        # Generate synthetic dataset
        synthetic_data = await self._generate_synthetic_data(
            request.dataset_id, model_type, sample_size, request.epsilon or 1.0
        )
        
        # Perform aggregation on synthetic data
        if request.aggregation_type == AggregationType.COUNT:
            result_value = len(synthetic_data)
        elif request.aggregation_type == AggregationType.MEAN:
            field = request.privacy_parameters.get("field", "value")
            values = [record.get(field, 0) for record in synthetic_data]
            result_value = np.mean(values) if values else 0
        elif request.aggregation_type == AggregationType.HISTOGRAM:
            field = request.privacy_parameters.get("field", "category")
            counter = Counter(record.get(field) for record in synthetic_data)
            result_value = dict(counter)
        else:
            result_value = {"error": "Unsupported aggregation for synthetic data"}
        
        result_id = f"result_{uuid.uuid4().hex[:8]}"
        return AnalyticsResult(
            result_id=result_id,
            request_id=request.request_id,
            query_type=request.query_type,
            result_data={"value": result_value, "synthetic": True},
            privacy_technique_used=PrivacyTechnique.SYNTHETIC_DATA,
            epsilon_consumed=request.epsilon or 1.0,
            delta_consumed=request.delta or 1e-5,
            noise_added=True,
            uncertainty_bounds=None,
            data_points_analyzed=sample_size,
            suppressed_values=0,
            execution_time=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            metadata={
                "model_type": model_type,
                "synthetic_samples": sample_size,
                "privacy_epsilon": request.epsilon or 1.0
            }
        )

    async def _generate_synthetic_data(
        self,
        dataset_id: str,
        model_type: str,
        sample_size: int,
        epsilon: float
    ) -> List[Dict[str, Any]]:
        # Simplified synthetic data generation
        if "demographic" in dataset_id:
            return [
                {
                    "age": max(18, np.random.normal(40, 15)),
                    "income": max(0, np.random.normal(55000, 20000)),
                    "education": np.random.choice(["high_school", "college", "graduate"]),
                    "location": np.random.choice(["urban", "suburban", "rural"])
                }
                for _ in range(sample_size)
            ]
        elif "transaction" in dataset_id:
            return [
                {
                    "amount": max(0, np.random.exponential(75)),
                    "category": np.random.choice(["food", "transport", "entertainment", "utilities"]),
                    "merchant_type": np.random.choice(["online", "retail", "restaurant", "gas_station"])
                }
                for _ in range(sample_size)
            ]
        else:
            return [
                {"value": np.random.normal(100, 30)} for _ in range(sample_size)
            ]

    async def _execute_secure_aggregation_query(self, request: AnalyticsRequest) -> AnalyticsResult:
        # Simulate secure aggregation (e.g., federated learning scenario)
        num_parties = request.privacy_parameters.get("num_parties", 3)
        
        # Simulate each party computing local aggregates
        local_results = []
        for party_id in range(num_parties):
            # Simulate local data for each party
            local_data = await self._simulate_data_retrieval(request)
            
            if request.aggregation_type == AggregationType.COUNT:
                local_result = len(local_data)
            elif request.aggregation_type == AggregationType.SUM:
                field = request.privacy_parameters.get("field", "value")
                local_result = sum(record.get(field, 0) for record in local_data)
            elif request.aggregation_type == AggregationType.MEAN:
                field = request.privacy_parameters.get("field", "value")
                values = [record.get(field, 0) for record in local_data]
                local_result = np.mean(values) if values else 0
            else:
                local_result = 0
            
            local_results.append(local_result)
        
        # Aggregate results from all parties
        if request.aggregation_type == AggregationType.COUNT:
            final_result = sum(local_results)
        elif request.aggregation_type == AggregationType.SUM:
            final_result = sum(local_results)
        elif request.aggregation_type == AggregationType.MEAN:
            # Weighted average (simplified)
            final_result = np.mean(local_results)
        else:
            final_result = 0
        
        result_id = f"result_{uuid.uuid4().hex[:8]}"
        return AnalyticsResult(
            result_id=result_id,
            request_id=request.request_id,
            query_type=request.query_type,
            result_data={"value": final_result, "parties": num_parties},
            privacy_technique_used=PrivacyTechnique.SECURE_AGGREGATION,
            epsilon_consumed=0.0,  # Secure aggregation doesn't use DP budget
            delta_consumed=0.0,
            noise_added=False,
            uncertainty_bounds=None,
            data_points_analyzed=sum(local_results) if request.aggregation_type == AggregationType.COUNT else 0,
            suppressed_values=0,
            execution_time=datetime.now(),
            expires_at=datetime.now() + timedelta(days=30),
            metadata={
                "num_parties": num_parties,
                "local_results": local_results,
                "aggregation_type": request.aggregation_type.value
            }
        )

    def _get_sensitivity(self, aggregation_type: AggregationType) -> float:
        calibration = self.noise_calibration.get(aggregation_type.value, {})
        return calibration.get("sensitivity", 1.0)

    async def _calculate_uncertainty_bounds(
        self,
        result_value: Any,
        epsilon: float,
        aggregation_type: AggregationType
    ) -> Dict[str, float]:
        if not isinstance(result_value, (int, float)):
            return {}
        
        # Calculate confidence intervals based on noise distribution
        sensitivity = self._get_sensitivity(aggregation_type)
        noise_scale = sensitivity / epsilon
        
        # For Laplace noise, 95% confidence interval
        confidence_95 = 1.96 * noise_scale
        
        return {
            "lower_bound_95": result_value - confidence_95,
            "upper_bound_95": result_value + confidence_95,
            "noise_scale": noise_scale,
            "confidence_level": 0.95
        }

    async def _update_privacy_budget(self, dataset_id: str, epsilon_consumed: float):
        budget_key = await self._get_budget_key(dataset_id)
        
        if budget_key in self.privacy_budgets:
            budget = self.privacy_budgets[budget_key]
            budget.consumed_epsilon += epsilon_consumed
            budget.remaining_epsilon = max(0, budget.total_epsilon - budget.consumed_epsilon)
            budget.queries_count += 1
            
            # Check if budget needs reset
            if datetime.now() > budget.reset_time:
                await self._reset_privacy_budget(budget_key)

    async def _reset_privacy_budget(self, budget_key: str):
        if budget_key in self.privacy_budgets:
            budget = self.privacy_budgets[budget_key]
            budget.consumed_epsilon = 0.0
            budget.remaining_epsilon = budget.total_epsilon
            budget.queries_count = 0
            budget.reset_time = datetime.now() + budget.time_window
            
            logger.info(f"Reset privacy budget: {budget_key}")

    async def get_analytics_result(self, result_id: str) -> Optional[AnalyticsResult]:
        result = self.analytics_results.get(result_id)
        
        # Check if result has expired
        if result and result.expires_at and datetime.now() > result.expires_at:
            logger.info(f"Analytics result {result_id} has expired")
            del self.analytics_results[result_id]
            return None
        
        return result

    async def get_privacy_budget_status(self, dataset_id: str) -> Dict[str, Any]:
        budget_key = await self._get_budget_key(dataset_id)
        
        if budget_key not in self.privacy_budgets:
            return {"error": "Budget not found"}
        
        budget = self.privacy_budgets[budget_key]
        
        return {
            "budget_key": budget_key,
            "total_epsilon": budget.total_epsilon,
            "consumed_epsilon": budget.consumed_epsilon,
            "remaining_epsilon": budget.remaining_epsilon,
            "delta": budget.delta,
            "queries_count": budget.queries_count,
            "max_queries": budget.max_queries,
            "reset_time": budget.reset_time.isoformat(),
            "utilization_percentage": (budget.consumed_epsilon / budget.total_epsilon) * 100
        }

    async def get_analytics_statistics(self) -> Dict[str, Any]:
        total_requests = len(self.analytics_requests)
        executed_requests = len([r for r in self.analytics_requests.values() if r.executed])
        
        # Technique usage
        technique_usage = Counter(
            r.privacy_technique.value for r in self.analytics_requests.values()
        )
        
        # Query type usage
        query_type_usage = Counter(
            r.query_type.value for r in self.analytics_requests.values()
        )
        
        # Privacy budget utilization
        budget_utilization = {}
        for budget_key, budget in self.privacy_budgets.items():
            budget_utilization[budget_key] = {
                "utilization_percentage": (budget.consumed_epsilon / budget.total_epsilon) * 100,
                "queries_used": budget.queries_count,
                "queries_remaining": budget.max_queries - budget.queries_count
            }
        
        return {
            "total_requests": total_requests,
            "executed_requests": executed_requests,
            "success_rate": (executed_requests / total_requests) * 100 if total_requests > 0 else 0,
            "technique_usage": dict(technique_usage),
            "query_type_usage": dict(query_type_usage),
            "budget_utilization": budget_utilization,
            "total_results": len(self.analytics_results),
            "active_budgets": len(self.privacy_budgets)
        }

    async def cleanup_expired_results(self) -> int:
        expired_count = 0
        current_time = datetime.now()
        
        expired_results = []
        for result_id, result in self.analytics_results.items():
            if result.expires_at and result.expires_at < current_time:
                expired_results.append(result_id)
        
        for result_id in expired_results:
            del self.analytics_results[result_id]
            expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired analytics results")
        return expired_count

    async def export_analytics_data(self) -> Dict[str, Any]:
        export_data = {
            "export_date": datetime.now().isoformat(),
            "statistics": await self.get_analytics_statistics(),
            "privacy_budgets": {},
            "request_summary": {},
            "technique_performance": {}
        }
        
        # Export privacy budgets (without sensitive details)
        for budget_key, budget in self.privacy_budgets.items():
            export_data["privacy_budgets"][budget_key] = {
                "total_epsilon": budget.total_epsilon,
                "consumed_epsilon": budget.consumed_epsilon,
                "queries_count": budget.queries_count,
                "max_queries": budget.max_queries,
                "utilization_percentage": (budget.consumed_epsilon / budget.total_epsilon) * 100
            }
        
        # Export request summaries (without sensitive data)
        for request_id, request in self.analytics_requests.items():
            export_data["request_summary"][request_id] = {
                "query_type": request.query_type.value,
                "privacy_technique": request.privacy_technique.value,
                "aggregation_type": request.aggregation_type.value,
                "executed": request.executed,
                "created_date": request.created_date.isoformat()
            }
        
        # Calculate technique performance
        for technique in PrivacyTechnique:
            technique_requests = [
                r for r in self.analytics_requests.values()
                if r.privacy_technique == technique and r.executed
            ]
            
            if technique_requests:
                export_data["technique_performance"][technique.value] = {
                    "total_requests": len(technique_requests),
                    "avg_epsilon_consumption": np.mean([r.epsilon or 0 for r in technique_requests]),
                    "success_rate": len([r for r in technique_requests if r.result_id]) / len(technique_requests) * 100
                }
        
        logger.info(f"Exported privacy-preserving analytics data")
        return export_data