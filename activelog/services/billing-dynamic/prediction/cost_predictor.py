"""
Cost Prediction Engine
ML-powered cost forecasting and optimization recommendations
"""

import asyncio
import json
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import redis
import pickle
from collections import defaultdict, deque
from decimal import Decimal
import math

class PredictionModel(Enum):
    LINEAR_REGRESSION = "linear_regression"
    POLYNOMIAL_REGRESSION = "polynomial_regression"
    SEASONAL_ARIMA = "seasonal_arima"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"

class TimeHorizon(Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

@dataclass
class CostPrediction:
    """Cost prediction result"""
    user_id: str
    session_id: str
    prediction_type: str
    time_horizon: TimeHorizon
    
    # Prediction results
    predicted_cost: Decimal
    confidence_interval: Tuple[Decimal, Decimal]
    confidence_score: float
    
    # Contributing factors
    usage_patterns: Dict[str, float] = field(default_factory=dict)
    seasonal_factors: Dict[str, float] = field(default_factory=dict)
    trend_factors: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    model_used: PredictionModel = PredictionModel.LINEAR_REGRESSION
    prediction_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    historical_data_points: int = 0
    
@dataclass
class OptimizationRecommendation:
    """Cost optimization recommendation"""
    recommendation_id: str
    user_id: str
    session_id: str
    
    # Recommendation details
    optimization_type: str
    description: str
    potential_savings: Decimal
    confidence_score: float
    
    # Implementation details
    action_required: str
    estimated_effort: str
    time_to_implement: str
    
    # Impact analysis
    cost_impact: Decimal
    performance_impact: str
    risk_level: str
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: str = "medium"

class CostPredictionEngine:
    """
    Advanced cost prediction engine using machine learning
    to forecast costs and provide optimization recommendations
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Prediction models
        self.models: Dict[str, Any] = {}
        self.model_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Historical data
        self.cost_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.usage_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Prediction cache
        self.prediction_cache: Dict[str, CostPrediction] = {}
        self.recommendation_cache: Dict[str, List[OptimizationRecommendation]] = {}
        
        # Engine state
        self.prediction_engine_running = False
        
        # Performance metrics
        self.metrics = {
            "predictions_made": 0,
            "recommendations_generated": 0,
            "model_accuracy": 0.0,
            "cache_hit_rate": 0.0,
            "average_prediction_time": 0.0
        }
        
        # Configuration
        self.update_interval = 3600  # 1 hour
        self.cache_ttl = 1800  # 30 minutes

    async def forecast_costs(self, forecast_request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cost forecast based on historical data and usage patterns"""
        try:
            user_id = forecast_request["user_id"]
            time_horizon = TimeHorizon(forecast_request.get("time_horizon", "monthly"))
            session_id = forecast_request.get("session_id", "all")
            
            # Check cache first
            cache_key = f"{user_id}_{session_id}_{time_horizon.value}"
            if cache_key in self.prediction_cache:
                cached_prediction = self.prediction_cache[cache_key]
                if (datetime.now(timezone.utc) - cached_prediction.prediction_date).seconds < self.cache_ttl:
                    self.metrics["cache_hit_rate"] = self.metrics.get("cache_hit_rate", 0) * 0.9 + 0.1
                    return self._format_prediction_response(cached_prediction)
            
            start_time = datetime.now()
            
            # Gather historical data
            historical_data = await self._gather_historical_data(user_id, session_id, time_horizon)
            
            if not historical_data or len(historical_data["cost_data"]) < 3:
                # Insufficient data - use simple extrapolation
                prediction = await self._simple_cost_extrapolation(user_id, session_id, time_horizon, historical_data)
            else:
                # Use ML model for prediction
                prediction = await self._ml_cost_prediction(user_id, session_id, time_horizon, historical_data)
            
            # Cache prediction
            self.prediction_cache[cache_key] = prediction
            
            # Update metrics
            prediction_time = (datetime.now() - start_time).total_seconds()
            self.metrics["average_prediction_time"] = (
                self.metrics["average_prediction_time"] * 0.9 + prediction_time * 0.1
            )
            self.metrics["predictions_made"] += 1
            
            return self._format_prediction_response(prediction)
            
        except Exception as e:
            self.logger.error(f"Cost forecasting failed: {e}")
            return {"error": str(e)}

    async def get_monthly_prediction(self, user_id: str) -> Dict[str, Any]:
        """Get monthly cost prediction for user"""
        try:
            forecast_request = {
                "user_id": user_id,
                "time_horizon": "monthly",
                "session_id": "all"
            }
            
            return await self.forecast_costs(forecast_request)
            
        except Exception as e:
            self.logger.error(f"Monthly prediction failed for user {user_id}: {e}")
            return {"error": str(e)}

    async def optimize_costs(self, optimization_request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate cost optimization recommendations"""
        try:
            user_id = optimization_request["user_id"]
            session_id = optimization_request.get("session_id", "all")
            
            # Check cache
            cache_key = f"opt_{user_id}_{session_id}"
            if cache_key in self.recommendation_cache:
                cached_recommendations = self.recommendation_cache[cache_key]
                if cached_recommendations and (datetime.now(timezone.utc) - cached_recommendations[0].created_at).seconds < self.cache_ttl:
                    return self._format_optimization_response(cached_recommendations)
            
            # Generate recommendations
            recommendations = await self._generate_optimization_recommendations(
                user_id, session_id, optimization_request
            )
            
            # Cache recommendations
            self.recommendation_cache[cache_key] = recommendations
            
            # Update metrics
            self.metrics["recommendations_generated"] += len(recommendations)
            
            return self._format_optimization_response(recommendations)
            
        except Exception as e:
            self.logger.error(f"Cost optimization failed: {e}")
            return {"error": str(e)}

    async def _gather_historical_data(
        self,
        user_id: str,
        session_id: str,
        time_horizon: TimeHorizon
    ) -> Dict[str, Any]:
        """Gather historical cost and usage data"""
        try:
            historical_data = {
                "cost_data": [],
                "usage_data": [],
                "time_points": [],
                "metadata": {}
            }
            
            # Determine lookback period
            lookback_days = {
                TimeHorizon.HOURLY: 7,
                TimeHorizon.DAILY: 30,
                TimeHorizon.WEEKLY: 90,
                TimeHorizon.MONTHLY: 365,
                TimeHorizon.QUARTERLY: 730
            }.get(time_horizon, 30)
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
            
            # Gather data from Redis
            if self.redis_client:
                # Get billing data
                await self._gather_billing_data(user_id, session_id, cutoff_date, historical_data)
                
                # Get usage data
                await self._gather_usage_data(user_id, session_id, cutoff_date, historical_data)
            
            # Gather data from memory
            await self._gather_memory_data(user_id, session_id, cutoff_date, historical_data)
            
            # Process and clean data
            historical_data = await self._process_historical_data(historical_data, time_horizon)
            
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Failed to gather historical data: {e}")
            return {"cost_data": [], "usage_data": [], "time_points": []}

    async def _gather_billing_data(
        self,
        user_id: str,
        session_id: str,
        cutoff_date: datetime,
        historical_data: Dict[str, Any]
    ):
        """Gather billing data from Redis"""
        try:
            # Get archived billing sessions
            if session_id == "all":
                # Get all user sessions
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
            else:
                session_ids = [session_id]
            
            for sid in session_ids:
                archive_key = f"billing_archive:{user_id}:{sid}"
                
                if await self.redis_client.exists(archive_key):
                    archive_data = await self.redis_client.hgetall(archive_key)
                    
                    if archive_data and "stopped_at" in archive_data:
                        stopped_at = datetime.fromisoformat(archive_data["stopped_at"])
                        
                        if stopped_at >= cutoff_date:
                            cost = float(archive_data.get("total_cost", 0))
                            usage = json.loads(archive_data.get("resource_usage", "{}"))
                            
                            historical_data["cost_data"].append(cost)
                            historical_data["usage_data"].append(usage)
                            historical_data["time_points"].append(stopped_at.timestamp())
            
        except Exception as e:
            self.logger.error(f"Failed to gather billing data from Redis: {e}")

    async def _gather_usage_data(
        self,
        user_id: str,
        session_id: str,
        cutoff_date: datetime,
        historical_data: Dict[str, Any]
    ):
        """Gather usage data from Redis"""
        try:
            if session_id == "all":
                # Get all user sessions
                user_sessions_key = f"user_sessions:{user_id}"
                session_ids = await self.redis_client.smembers(user_sessions_key)
            else:
                session_ids = [session_id]
            
            for sid in session_ids:
                usage_key = f"usage_snapshots:{sid}"
                
                # Get usage snapshots since cutoff date
                cutoff_timestamp = cutoff_date.timestamp()
                snapshots = await self.redis_client.zrangebyscore(
                    usage_key, cutoff_timestamp, "+inf", withscores=True
                )
                
                for snapshot_data, timestamp in snapshots:
                    try:
                        snapshot = json.loads(snapshot_data)
                        metrics = json.loads(snapshot.get("metrics", "{}"))
                        
                        # Extract usage metrics
                        usage = {}
                        for resource_type, metric_data in metrics.items():
                            usage[f"{resource_type}_value"] = metric_data.get("value", 0)
                        
                        historical_data["usage_data"].append(usage)
                        historical_data["time_points"].append(timestamp)
                        
                    except json.JSONDecodeError:
                        continue
            
        except Exception as e:
            self.logger.error(f"Failed to gather usage data from Redis: {e}")

    async def _gather_memory_data(
        self,
        user_id: str,
        session_id: str,
        cutoff_date: datetime,
        historical_data: Dict[str, Any]
    ):
        """Gather data from in-memory storage"""
        try:
            # Gather from cost history
            cost_key = f"{user_id}_{session_id}"
            if cost_key in self.cost_history:
                for cost_point in self.cost_history[cost_key]:
                    if hasattr(cost_point, 'timestamp') and cost_point.timestamp >= cutoff_date:
                        historical_data["cost_data"].append(float(cost_point.cost))
                        historical_data["time_points"].append(cost_point.timestamp.timestamp())
            
            # Gather from usage history
            usage_key = f"{user_id}_{session_id}"
            if usage_key in self.usage_history:
                for usage_point in self.usage_history[usage_key]:
                    if hasattr(usage_point, 'timestamp') and usage_point.timestamp >= cutoff_date:
                        historical_data["usage_data"].append(usage_point.usage_data)
                        historical_data["time_points"].append(usage_point.timestamp.timestamp())
        
        except Exception as e:
            self.logger.error(f"Failed to gather memory data: {e}")

    async def _process_historical_data(
        self,
        historical_data: Dict[str, Any],
        time_horizon: TimeHorizon
    ) -> Dict[str, Any]:
        """Process and clean historical data"""
        try:
            # Remove duplicates and sort by time
            combined_data = list(zip(
                historical_data["time_points"],
                historical_data["cost_data"],
                historical_data["usage_data"] if historical_data["usage_data"] else [{}] * len(historical_data["cost_data"])
            ))
            
            # Sort by timestamp
            combined_data.sort(key=lambda x: x[0])
            
            # Remove duplicates (same timestamp)
            unique_data = []
            last_timestamp = None
            
            for timestamp, cost, usage in combined_data:
                if last_timestamp is None or timestamp != last_timestamp:
                    unique_data.append((timestamp, cost, usage))
                    last_timestamp = timestamp
            
            if not unique_data:
                return historical_data
            
            # Aggregate by time horizon
            aggregated_data = await self._aggregate_by_time_horizon(unique_data, time_horizon)
            
            # Update historical data
            historical_data["time_points"] = [point[0] for point in aggregated_data]
            historical_data["cost_data"] = [point[1] for point in aggregated_data]
            historical_data["usage_data"] = [point[2] for point in aggregated_data]
            
            # Add metadata
            historical_data["metadata"] = {
                "data_points": len(aggregated_data),
                "time_range_days": (historical_data["time_points"][-1] - historical_data["time_points"][0]) / 86400 if len(historical_data["time_points"]) > 1 else 0,
                "avg_cost": sum(historical_data["cost_data"]) / len(historical_data["cost_data"]) if historical_data["cost_data"] else 0,
                "total_cost": sum(historical_data["cost_data"]) if historical_data["cost_data"] else 0
            }
            
            return historical_data
            
        except Exception as e:
            self.logger.error(f"Failed to process historical data: {e}")
            return historical_data

    async def _aggregate_by_time_horizon(
        self,
        data: List[Tuple[float, float, Dict[str, Any]]],
        time_horizon: TimeHorizon
    ) -> List[Tuple[float, float, Dict[str, Any]]]:
        """Aggregate data points by time horizon"""
        try:
            if not data:
                return []
            
            # Define aggregation intervals in seconds
            intervals = {
                TimeHorizon.HOURLY: 3600,
                TimeHorizon.DAILY: 86400,
                TimeHorizon.WEEKLY: 604800,
                TimeHorizon.MONTHLY: 2592000,
                TimeHorizon.QUARTERLY: 7776000
            }
            
            interval = intervals.get(time_horizon, 86400)
            
            # Group data by intervals
            grouped_data = defaultdict(list)
            
            for timestamp, cost, usage in data:
                # Calculate interval bucket
                bucket = int(timestamp // interval) * interval
                grouped_data[bucket].append((timestamp, cost, usage))
            
            # Aggregate each bucket
            aggregated = []
            for bucket_time in sorted(grouped_data.keys()):
                bucket_data = grouped_data[bucket_time]
                
                # Aggregate costs (sum)
                total_cost = sum(point[1] for point in bucket_data)
                
                # Aggregate usage (average)
                usage_aggregated = {}
                if bucket_data:
                    usage_keys = set()
                    for _, _, usage in bucket_data:
                        if usage:
                            usage_keys.update(usage.keys())
                    
                    for key in usage_keys:
                        values = [usage.get(key, 0) for _, _, usage in bucket_data if usage]
                        if values:
                            usage_aggregated[key] = sum(values) / len(values)
                
                aggregated.append((bucket_time, total_cost, usage_aggregated))
            
            return aggregated
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate data by time horizon: {e}")
            return data

    async def _simple_cost_extrapolation(
        self,
        user_id: str,
        session_id: str,
        time_horizon: TimeHorizon,
        historical_data: Dict[str, Any]
    ) -> CostPrediction:
        """Simple cost extrapolation when insufficient data"""
        try:
            cost_data = historical_data.get("cost_data", [])
            
            if not cost_data:
                # No historical data - use baseline estimate
                predicted_cost = Decimal("10.00")  # Default monthly estimate
                confidence_score = 0.1
            elif len(cost_data) == 1:
                # Single data point - use as baseline
                predicted_cost = Decimal(str(cost_data[0]))
                confidence_score = 0.3
            else:
                # Multiple data points - use average with trend
                avg_cost = sum(cost_data) / len(cost_data)
                
                # Simple trend calculation
                if len(cost_data) >= 2:
                    trend = (cost_data[-1] - cost_data[0]) / (len(cost_data) - 1)
                    predicted_cost = Decimal(str(avg_cost + trend))
                else:
                    predicted_cost = Decimal(str(avg_cost))
                
                confidence_score = min(0.6, len(cost_data) / 10.0)
            
            # Adjust for time horizon
            horizon_multipliers = {
                TimeHorizon.HOURLY: 1/24/30,  # Hourly from monthly
                TimeHorizon.DAILY: 1/30,       # Daily from monthly
                TimeHorizon.WEEKLY: 1/4.33,    # Weekly from monthly
                TimeHorizon.MONTHLY: 1.0,      # Monthly baseline
                TimeHorizon.QUARTERLY: 3.0     # Quarterly from monthly
            }
            
            multiplier = horizon_multipliers.get(time_horizon, 1.0)
            predicted_cost *= Decimal(str(multiplier))
            
            # Calculate confidence interval
            margin = predicted_cost * Decimal("0.5")  # ±50% margin
            confidence_interval = (
                max(Decimal("0"), predicted_cost - margin),
                predicted_cost + margin
            )
            
            return CostPrediction(
                user_id=user_id,
                session_id=session_id,
                prediction_type="simple_extrapolation",
                time_horizon=time_horizon,
                predicted_cost=predicted_cost,
                confidence_interval=confidence_interval,
                confidence_score=confidence_score,
                model_used=PredictionModel.LINEAR_REGRESSION,
                historical_data_points=len(cost_data)
            )
            
        except Exception as e:
            self.logger.error(f"Simple cost extrapolation failed: {e}")
            # Return safe default
            return CostPrediction(
                user_id=user_id,
                session_id=session_id,
                prediction_type="default",
                time_horizon=time_horizon,
                predicted_cost=Decimal("10.00"),
                confidence_interval=(Decimal("5.00"), Decimal("20.00")),
                confidence_score=0.1,
                historical_data_points=0
            )

    async def _ml_cost_prediction(
        self,
        user_id: str,
        session_id: str,
        time_horizon: TimeHorizon,
        historical_data: Dict[str, Any]
    ) -> CostPrediction:
        """ML-based cost prediction"""
        try:
            cost_data = historical_data["cost_data"]
            time_points = historical_data["time_points"]
            usage_data = historical_data["usage_data"]
            
            # Prepare features
            features = await self._prepare_ml_features(cost_data, time_points, usage_data, time_horizon)
            
            # Choose and apply model
            model_type = await self._select_best_model(user_id, session_id, time_horizon)
            predicted_cost, confidence_interval, confidence_score = await self._apply_ml_model(
                features, cost_data, model_type
            )
            
            # Analyze contributing factors
            usage_patterns = await self._analyze_usage_patterns(usage_data)
            seasonal_factors = await self._analyze_seasonal_factors(time_points, cost_data)
            trend_factors = await self._analyze_trend_factors(time_points, cost_data)
            
            return CostPrediction(
                user_id=user_id,
                session_id=session_id,
                prediction_type="ml_prediction",
                time_horizon=time_horizon,
                predicted_cost=Decimal(str(predicted_cost)),
                confidence_interval=(Decimal(str(confidence_interval[0])), Decimal(str(confidence_interval[1]))),
                confidence_score=confidence_score,
                usage_patterns=usage_patterns,
                seasonal_factors=seasonal_factors,
                trend_factors=trend_factors,
                model_used=model_type,
                historical_data_points=len(cost_data)
            )
            
        except Exception as e:
            self.logger.error(f"ML cost prediction failed: {e}")
            # Fallback to simple extrapolation
            return await self._simple_cost_extrapolation(user_id, session_id, time_horizon, historical_data)

    async def _prepare_ml_features(
        self,
        cost_data: List[float],
        time_points: List[float],
        usage_data: List[Dict[str, Any]],
        time_horizon: TimeHorizon
    ) -> np.ndarray:
        """Prepare features for ML model"""
        try:
            features = []
            
            for i, (cost, timestamp) in enumerate(zip(cost_data, time_points)):
                feature_vector = []
                
                # Time-based features
                dt = datetime.fromtimestamp(timestamp, timezone.utc)
                feature_vector.extend([
                    dt.hour,
                    dt.weekday(),
                    dt.day,
                    dt.month,
                    dt.year - 2020,  # Normalize year
                    math.sin(2 * math.pi * dt.hour / 24),  # Cyclical hour
                    math.cos(2 * math.pi * dt.hour / 24),
                    math.sin(2 * math.pi * dt.weekday() / 7),  # Cyclical weekday
                    math.cos(2 * math.pi * dt.weekday() / 7)
                ])
                
                # Historical cost features
                if i > 0:
                    feature_vector.extend([
                        cost_data[i-1],  # Previous cost
                        cost - cost_data[i-1] if i > 0 else 0,  # Cost change
                        sum(cost_data[max(0, i-3):i]) / min(i, 3) if i > 0 else cost  # Moving average
                    ])
                else:
                    feature_vector.extend([cost, 0, cost])
                
                # Usage-based features
                if i < len(usage_data) and usage_data[i]:
                    usage = usage_data[i]
                    feature_vector.extend([
                        usage.get("cpu_value", 0),
                        usage.get("memory_value", 0),
                        usage.get("storage_value", 0),
                        usage.get("network_value", 0),
                        usage.get("requests_value", 0)
                    ])
                else:
                    feature_vector.extend([0, 0, 0, 0, 0])
                
                features.append(feature_vector)
            
            return np.array(features) if features else np.array([[0] * 20])
            
        except Exception as e:
            self.logger.error(f"Feature preparation failed: {e}")
            return np.array([[0] * 20])

    async def _select_best_model(
        self,
        user_id: str,
        session_id: str,
        time_horizon: TimeHorizon
    ) -> PredictionModel:
        """Select best performing model for user/session"""
        try:
            model_key = f"{user_id}_{session_id}_{time_horizon.value}"
            
            if model_key in self.model_performance:
                performance = self.model_performance[model_key]
                best_model = max(performance.items(), key=lambda x: x[1])[0]
                return PredictionModel(best_model)
            
            # Default model for new users
            return PredictionModel.LINEAR_REGRESSION
            
        except Exception as e:
            self.logger.error(f"Model selection failed: {e}")
            return PredictionModel.LINEAR_REGRESSION

    async def _apply_ml_model(
        self,
        features: np.ndarray,
        cost_data: List[float],
        model_type: PredictionModel
    ) -> Tuple[float, Tuple[float, float], float]:
        """Apply selected ML model"""
        try:
            if model_type == PredictionModel.LINEAR_REGRESSION:
                return await self._linear_regression_prediction(features, cost_data)
            elif model_type == PredictionModel.POLYNOMIAL_REGRESSION:
                return await self._polynomial_regression_prediction(features, cost_data)
            elif model_type == PredictionModel.ENSEMBLE:
                return await self._ensemble_prediction(features, cost_data)
            else:
                # Fallback to linear regression
                return await self._linear_regression_prediction(features, cost_data)
            
        except Exception as e:
            self.logger.error(f"ML model application failed: {e}")
            # Return safe default
            avg_cost = sum(cost_data) / len(cost_data) if cost_data else 10.0
            return avg_cost, (avg_cost * 0.5, avg_cost * 1.5), 0.5

    async def _linear_regression_prediction(
        self,
        features: np.ndarray,
        cost_data: List[float]
    ) -> Tuple[float, Tuple[float, float], float]:
        """Simple linear regression prediction"""
        try:
            if len(cost_data) < 2:
                avg_cost = cost_data[0] if cost_data else 10.0
                return avg_cost, (avg_cost * 0.8, avg_cost * 1.2), 0.5
            
            # Simple time-series linear regression
            x = np.arange(len(cost_data)).reshape(-1, 1)
            y = np.array(cost_data)
            
            # Calculate slope and intercept
            x_mean = np.mean(x)
            y_mean = np.mean(y)
            
            numerator = np.sum((x.flatten() - x_mean) * (y - y_mean))
            denominator = np.sum((x.flatten() - x_mean) ** 2)
            
            if denominator == 0:
                predicted_cost = y_mean
            else:
                slope = numerator / denominator
                intercept = y_mean - slope * x_mean
                predicted_cost = slope * len(cost_data) + intercept
            
            # Calculate confidence interval based on residuals
            residuals = y - (slope * x.flatten() + intercept) if denominator != 0 else y - y_mean
            mse = np.mean(residuals ** 2)
            std_error = math.sqrt(mse)
            
            confidence_interval = (
                max(0, predicted_cost - 1.96 * std_error),
                predicted_cost + 1.96 * std_error
            )
            
            # Calculate confidence score based on R²
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - y_mean) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            confidence_score = max(0, min(1, r_squared))
            
            return predicted_cost, confidence_interval, confidence_score
            
        except Exception as e:
            self.logger.error(f"Linear regression prediction failed: {e}")
            avg_cost = sum(cost_data) / len(cost_data) if cost_data else 10.0
            return avg_cost, (avg_cost * 0.8, avg_cost * 1.2), 0.5

    async def _polynomial_regression_prediction(
        self,
        features: np.ndarray,
        cost_data: List[float]
    ) -> Tuple[float, Tuple[float, float], float]:
        """Polynomial regression prediction"""
        try:
            # For simplicity, use quadratic polynomial
            if len(cost_data) < 3:
                return await self._linear_regression_prediction(features, cost_data)
            
            x = np.arange(len(cost_data))
            y = np.array(cost_data)
            
            # Fit quadratic polynomial
            coeffs = np.polyfit(x, y, min(2, len(cost_data) - 1))
            
            # Predict next point
            next_x = len(cost_data)
            predicted_cost = np.polyval(coeffs, next_x)
            
            # Calculate prediction variance
            y_pred = np.polyval(coeffs, x)
            residuals = y - y_pred
            mse = np.mean(residuals ** 2)
            std_error = math.sqrt(mse)
            
            confidence_interval = (
                max(0, predicted_cost - 1.96 * std_error),
                predicted_cost + 1.96 * std_error
            )
            
            # R² calculation
            ss_res = np.sum(residuals ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            confidence_score = max(0, min(1, r_squared))
            
            return float(predicted_cost), confidence_interval, confidence_score
            
        except Exception as e:
            self.logger.error(f"Polynomial regression prediction failed: {e}")
            return await self._linear_regression_prediction(features, cost_data)

    async def _ensemble_prediction(
        self,
        features: np.ndarray,
        cost_data: List[float]
    ) -> Tuple[float, Tuple[float, float], float]:
        """Ensemble prediction combining multiple models"""
        try:
            # Get predictions from multiple models
            linear_pred = await self._linear_regression_prediction(features, cost_data)
            poly_pred = await self._polynomial_regression_prediction(features, cost_data)
            
            # Simple average ensemble
            predicted_cost = (linear_pred[0] + poly_pred[0]) / 2
            
            # Combined confidence interval
            lower = (linear_pred[1][0] + poly_pred[1][0]) / 2
            upper = (linear_pred[1][1] + poly_pred[1][1]) / 2
            confidence_interval = (lower, upper)
            
            # Average confidence score
            confidence_score = (linear_pred[2] + poly_pred[2]) / 2
            
            return predicted_cost, confidence_interval, confidence_score
            
        except Exception as e:
            self.logger.error(f"Ensemble prediction failed: {e}")
            return await self._linear_regression_prediction(features, cost_data)

    async def _analyze_usage_patterns(self, usage_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Analyze usage patterns for prediction insights"""
        try:
            if not usage_data:
                return {}
            
            patterns = {}
            
            # Calculate average usage for each resource type
            resource_totals = defaultdict(list)
            
            for usage in usage_data:
                if usage:
                    for key, value in usage.items():
                        if isinstance(value, (int, float)):
                            resource_totals[key].append(value)
            
            # Calculate averages and trends
            for resource, values in resource_totals.items():
                if values:
                    patterns[f"{resource}_avg"] = sum(values) / len(values)
                    patterns[f"{resource}_max"] = max(values)
                    patterns[f"{resource}_min"] = min(values)
                    patterns[f"{resource}_trend"] = (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Usage pattern analysis failed: {e}")
            return {}

    async def _analyze_seasonal_factors(
        self,
        time_points: List[float],
        cost_data: List[float]
    ) -> Dict[str, float]:
        """Analyze seasonal factors in cost data"""
        try:
            if len(time_points) < 7:  # Need at least a week of data
                return {}
            
            seasonal_factors = {}
            
            # Group costs by hour of day
            hourly_costs = defaultdict(list)
            daily_costs = defaultdict(list)
            
            for timestamp, cost in zip(time_points, cost_data):
                dt = datetime.fromtimestamp(timestamp, timezone.utc)
                hourly_costs[dt.hour].append(cost)
                daily_costs[dt.weekday()].append(cost)
            
            # Calculate hourly patterns
            if len(hourly_costs) > 1:
                avg_cost = sum(cost_data) / len(cost_data)
                for hour, costs in hourly_costs.items():
                    hour_avg = sum(costs) / len(costs)
                    seasonal_factors[f"hour_{hour}_factor"] = hour_avg / avg_cost if avg_cost > 0 else 1
            
            # Calculate daily patterns
            if len(daily_costs) > 1:
                avg_cost = sum(cost_data) / len(cost_data)
                for day, costs in daily_costs.items():
                    day_avg = sum(costs) / len(costs)
                    seasonal_factors[f"day_{day}_factor"] = day_avg / avg_cost if avg_cost > 0 else 1
            
            return seasonal_factors
            
        except Exception as e:
            self.logger.error(f"Seasonal factor analysis failed: {e}")
            return {}

    async def _analyze_trend_factors(
        self,
        time_points: List[float],
        cost_data: List[float]
    ) -> Dict[str, float]:
        """Analyze trend factors in cost data"""
        try:
            if len(cost_data) < 2:
                return {}
            
            trend_factors = {}
            
            # Overall trend
            total_change = cost_data[-1] - cost_data[0]
            time_span = time_points[-1] - time_points[0]
            
            if time_span > 0:
                trend_factors["cost_per_hour"] = total_change / (time_span / 3600)
                trend_factors["percentage_change"] = (total_change / cost_data[0] * 100) if cost_data[0] > 0 else 0
            
            # Recent trend (last 25% of data)
            recent_start = len(cost_data) * 3 // 4
            if recent_start < len(cost_data) - 1:
                recent_change = cost_data[-1] - cost_data[recent_start]
                recent_time_span = time_points[-1] - time_points[recent_start]
                
                if recent_time_span > 0:
                    trend_factors["recent_cost_per_hour"] = recent_change / (recent_time_span / 3600)
            
            # Volatility
            if len(cost_data) > 1:
                cost_changes = [abs(cost_data[i] - cost_data[i-1]) for i in range(1, len(cost_data))]
                trend_factors["volatility"] = sum(cost_changes) / len(cost_changes) if cost_changes else 0
            
            return trend_factors
            
        except Exception as e:
            self.logger.error(f"Trend factor analysis failed: {e}")
            return {}

    async def _generate_optimization_recommendations(
        self,
        user_id: str,
        session_id: str,
        request_data: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate cost optimization recommendations"""
        try:
            recommendations = []
            
            # Analyze current usage patterns
            current_usage = await self._analyze_current_usage(user_id, session_id)
            
            # Generate recommendations based on usage patterns
            recommendations.extend(await self._generate_usage_recommendations(user_id, session_id, current_usage))
            
            # Generate scheduling recommendations
            recommendations.extend(await self._generate_scheduling_recommendations(user_id, session_id, current_usage))
            
            # Generate scaling recommendations
            recommendations.extend(await self._generate_scaling_recommendations(user_id, session_id, current_usage))
            
            # Generate tier recommendations
            recommendations.extend(await self._generate_tier_recommendations(user_id, session_id, current_usage))
            
            # Sort by potential savings
            recommendations.sort(key=lambda x: float(x.potential_savings), reverse=True)
            
            return recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate optimization recommendations: {e}")
            return []

    async def _analyze_current_usage(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Analyze current usage patterns for optimization"""
        try:
            # Get recent usage data
            usage_analysis = {
                "cpu_utilization": 50.0,  # Placeholder - would get from actual monitoring
                "memory_utilization": 60.0,
                "peak_hours": [9, 10, 11, 14, 15, 16],
                "low_hours": [0, 1, 2, 3, 4, 5, 22, 23],
                "weekly_pattern": {"weekdays": 0.8, "weekends": 0.3},
                "current_tier": "standard",
                "unused_features": ["gpu", "premium_storage"],
                "efficiency_score": 0.65
            }
            
            return usage_analysis
            
        except Exception as e:
            self.logger.error(f"Current usage analysis failed: {e}")
            return {}

    async def _generate_usage_recommendations(
        self,
        user_id: str,
        session_id: str,
        usage_analysis: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate usage-based recommendations"""
        recommendations = []
        
        try:
            # Low utilization recommendation
            if usage_analysis.get("cpu_utilization", 0) < 30:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"usage_cpu_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    session_id=session_id,
                    optimization_type="resource_optimization",
                    description="Reduce CPU allocation due to low utilization",
                    potential_savings=Decimal("15.00"),
                    confidence_score=0.85,
                    action_required="Scale down CPU allocation by 25%",
                    estimated_effort="Low",
                    time_to_implement="5 minutes",
                    cost_impact=Decimal("15.00"),
                    performance_impact="Minimal - usage is well below capacity",
                    risk_level="Low",
                    priority="High"
                ))
            
            # Unused features recommendation
            unused_features = usage_analysis.get("unused_features", [])
            if unused_features:
                savings_per_feature = 8.0
                total_savings = len(unused_features) * savings_per_feature
                
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"usage_features_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    session_id=session_id,
                    optimization_type="feature_optimization",
                    description=f"Disable unused features: {', '.join(unused_features)}",
                    potential_savings=Decimal(str(total_savings)),
                    confidence_score=0.95,
                    action_required="Disable unused premium features",
                    estimated_effort="Low",
                    time_to_implement="2 minutes",
                    cost_impact=Decimal(str(total_savings)),
                    performance_impact="None - features are not being used",
                    risk_level="Very Low",
                    priority="High"
                ))
            
        except Exception as e:
            self.logger.error(f"Usage recommendations generation failed: {e}")
        
        return recommendations

    async def _generate_scheduling_recommendations(
        self,
        user_id: str,
        session_id: str,
        usage_analysis: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate scheduling-based recommendations"""
        recommendations = []
        
        try:
            peak_hours = usage_analysis.get("peak_hours", [])
            low_hours = usage_analysis.get("low_hours", [])
            
            if peak_hours and low_hours:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"schedule_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    session_id=session_id,
                    optimization_type="scheduling_optimization",
                    description="Implement scheduled scaling to reduce costs during low-usage hours",
                    potential_savings=Decimal("25.00"),
                    confidence_score=0.75,
                    action_required="Configure auto-scaling schedule",
                    estimated_effort="Medium",
                    time_to_implement="15 minutes",
                    cost_impact=Decimal("25.00"),
                    performance_impact="Potential slight delay during scale-up periods",
                    risk_level="Low",
                    priority="Medium"
                ))
            
        except Exception as e:
            self.logger.error(f"Scheduling recommendations generation failed: {e}")
        
        return recommendations

    async def _generate_scaling_recommendations(
        self,
        user_id: str,
        session_id: str,
        usage_analysis: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate scaling-based recommendations"""
        recommendations = []
        
        try:
            efficiency_score = usage_analysis.get("efficiency_score", 1.0)
            
            if efficiency_score < 0.7:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"scaling_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    session_id=session_id,
                    optimization_type="scaling_optimization",
                    description="Implement dynamic scaling to improve resource efficiency",
                    potential_savings=Decimal("18.00"),
                    confidence_score=0.70,
                    action_required="Enable automatic scaling policies",
                    estimated_effort="Medium",
                    time_to_implement="10 minutes",
                    cost_impact=Decimal("18.00"),
                    performance_impact="Improved - better resource utilization",
                    risk_level="Medium",
                    priority="Medium"
                ))
        
        except Exception as e:
            self.logger.error(f"Scaling recommendations generation failed: {e}")
        
        return recommendations

    async def _generate_tier_recommendations(
        self,
        user_id: str,
        session_id: str,
        usage_analysis: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """Generate tier-based recommendations"""
        recommendations = []
        
        try:
            current_tier = usage_analysis.get("current_tier", "standard")
            
            if current_tier == "premium" and usage_analysis.get("cpu_utilization", 0) < 40:
                recommendations.append(OptimizationRecommendation(
                    recommendation_id=f"tier_{user_id}_{int(datetime.now().timestamp())}",
                    user_id=user_id,
                    session_id=session_id,
                    optimization_type="tier_optimization",
                    description="Downgrade to Standard tier based on usage patterns",
                    potential_savings=Decimal("35.00"),
                    confidence_score=0.80,
                    action_required="Switch to Standard pricing tier",
                    estimated_effort="Low",
                    time_to_implement="1 minute",
                    cost_impact=Decimal("35.00"),
                    performance_impact="Minimal for current usage levels",
                    risk_level="Low",
                    priority="High"
                ))
        
        except Exception as e:
            self.logger.error(f"Tier recommendations generation failed: {e}")
        
        return recommendations

    def _format_prediction_response(self, prediction: CostPrediction) -> Dict[str, Any]:
        """Format prediction response"""
        return {
            "prediction": {
                "predicted_cost": float(prediction.predicted_cost),
                "confidence_interval": {
                    "lower": float(prediction.confidence_interval[0]),
                    "upper": float(prediction.confidence_interval[1])
                },
                "confidence_score": prediction.confidence_score,
                "time_horizon": prediction.time_horizon.value,
                "model_used": prediction.model_used.value,
                "historical_data_points": prediction.historical_data_points
            },
            "analysis": {
                "usage_patterns": prediction.usage_patterns,
                "seasonal_factors": prediction.seasonal_factors,
                "trend_factors": prediction.trend_factors
            },
            "metadata": {
                "prediction_date": prediction.prediction_date.isoformat(),
                "prediction_type": prediction.prediction_type
            }
        }

    def _format_optimization_response(self, recommendations: List[OptimizationRecommendation]) -> Dict[str, Any]:
        """Format optimization response"""
        total_savings = sum(float(rec.potential_savings) for rec in recommendations)
        
        return {
            "recommendations": [
                {
                    "recommendation_id": rec.recommendation_id,
                    "optimization_type": rec.optimization_type,
                    "description": rec.description,
                    "potential_savings": float(rec.potential_savings),
                    "confidence_score": rec.confidence_score,
                    "action_required": rec.action_required,
                    "estimated_effort": rec.estimated_effort,
                    "time_to_implement": rec.time_to_implement,
                    "cost_impact": float(rec.cost_impact),
                    "performance_impact": rec.performance_impact,
                    "risk_level": rec.risk_level,
                    "priority": rec.priority
                }
                for rec in recommendations
            ],
            "summary": {
                "total_recommendations": len(recommendations),
                "total_potential_savings": total_savings,
                "high_priority_count": sum(1 for rec in recommendations if rec.priority == "High"),
                "low_risk_count": sum(1 for rec in recommendations if rec.risk_level in ["Low", "Very Low"])
            }
        }

    async def start_prediction_updates(self):
        """Start background prediction updates"""
        if self.prediction_engine_running:
            return
        
        self.prediction_engine_running = True
        self.logger.info("Starting cost prediction engine")
        
        try:
            while self.prediction_engine_running:
                # Update model performance metrics
                await self._update_model_performance()
                
                # Clear old cache entries
                await self._cleanup_cache()
                
                # Store predictions in Redis
                if self.redis_client:
                    await self._store_predictions_in_redis()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Cost prediction engine cancelled")
        except Exception as e:
            self.logger.error(f"Cost prediction engine error: {e}")
        finally:
            self.prediction_engine_running = False

    async def _update_model_performance(self):
        """Update model performance metrics"""
        try:
            # This would compare actual costs vs predicted costs
            # and update model performance scores
            self.logger.debug("Updating model performance metrics")
            
        except Exception as e:
            self.logger.error(f"Model performance update failed: {e}")

    async def _cleanup_cache(self):
        """Clean up old cache entries"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Clean prediction cache
            expired_keys = []
            for key, prediction in self.prediction_cache.items():
                if (current_time - prediction.prediction_date).seconds > self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.prediction_cache[key]
            
            # Clean recommendation cache
            expired_rec_keys = []
            for key, recommendations in self.recommendation_cache.items():
                if recommendations and (current_time - recommendations[0].created_at).seconds > self.cache_ttl:
                    expired_rec_keys.append(key)
            
            for key in expired_rec_keys:
                del self.recommendation_cache[key]
            
            if expired_keys or expired_rec_keys:
                self.logger.debug(f"Cleaned {len(expired_keys)} prediction and {len(expired_rec_keys)} recommendation cache entries")
            
        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {e}")

    async def _store_predictions_in_redis(self):
        """Store predictions in Redis for persistence"""
        try:
            if not self.redis_client:
                return
            
            for key, prediction in self.prediction_cache.items():
                prediction_key = f"cost_prediction:{key}"
                
                prediction_data = {
                    "predicted_cost": float(prediction.predicted_cost),
                    "confidence_score": prediction.confidence_score,
                    "time_horizon": prediction.time_horizon.value,
                    "prediction_date": prediction.prediction_date.isoformat(),
                    "model_used": prediction.model_used.value
                }
                
                await self.redis_client.hset(prediction_key, mapping=prediction_data)
                await self.redis_client.expire(prediction_key, self.cache_ttl)
            
        except Exception as e:
            self.logger.error(f"Failed to store predictions in Redis: {e}")

    async def update_models(self) -> Dict[str, Any]:
        """Update prediction models with latest data"""
        try:
            updated_models = 0
            
            # This would retrain models with latest data
            # For now, just simulate model updates
            
            for model_type in PredictionModel:
                # Simulate model training/updating
                self.logger.info(f"Updating {model_type.value} model")
                updated_models += 1
            
            return {
                "updated_models": updated_models,
                "update_time": datetime.now(timezone.utc).isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            self.logger.error(f"Model update failed: {e}")
            return {"error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get cost prediction engine status"""
        return {
            "prediction_engine_running": self.prediction_engine_running,
            "cached_predictions": len(self.prediction_cache),
            "cached_recommendations": len(self.recommendation_cache),
            "metrics": self.metrics,
            "available_models": [model.value for model in PredictionModel],
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown cost prediction engine"""
        try:
            self.logger.info("Shutting down cost prediction engine...")
            
            # Stop prediction engine
            self.prediction_engine_running = False
            
            # Store final predictions
            if self.redis_client:
                await self._store_predictions_in_redis()
            
            self.logger.info("Cost prediction engine shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during cost prediction engine shutdown: {e}")