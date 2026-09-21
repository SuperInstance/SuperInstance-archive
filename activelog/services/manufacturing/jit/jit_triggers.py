#!/usr/bin/env python3
"""
ActiveLog Manufacturing Suite - Just-In-Time Manufacturing Triggers

Intelligent system for demand forecasting, inventory optimization, and
automated production triggering based on real-time consumption patterns.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import aiohttp
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')


class TriggerType(Enum):
    REORDER_POINT = "reorder_point"
    DEMAND_SPIKE = "demand_spike"
    INVENTORY_LOW = "inventory_low"
    LEAD_TIME_VARIANCE = "lead_time_variance"
    SEASONAL_ADJUSTMENT = "seasonal_adjustment"
    SUPPLIER_DISRUPTION = "supplier_disruption"
    QUALITY_ISSUE = "quality_issue"
    CAPACITY_CONSTRAINT = "capacity_constraint"


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProductionMethod(Enum):
    MAKE_TO_STOCK = "make_to_stock"
    MAKE_TO_ORDER = "make_to_order"
    ASSEMBLE_TO_ORDER = "assemble_to_order"
    ENGINEER_TO_ORDER = "engineer_to_order"


class InventoryStrategy(Enum):
    JIT = "just_in_time"
    KANBAN = "kanban"
    LEAN_BUFFER = "lean_buffer"
    SAFETY_STOCK = "safety_stock"


@dataclass
class Component:
    component_id: str
    name: str
    category: str
    unit_cost: float
    lead_time_days: int
    supplier_id: str
    min_order_quantity: int
    inventory_strategy: InventoryStrategy
    critical_component: bool
    shelf_life_days: Optional[int] = None
    storage_requirements: Optional[Dict[str, str]] = None


@dataclass
class InventoryRecord:
    record_id: str
    component_id: str
    timestamp: datetime
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    location: str
    batch_number: Optional[str] = None
    expiry_date: Optional[datetime] = None


@dataclass
class DemandForecast:
    component_id: str
    forecast_date: datetime
    forecast_period_days: int
    predicted_demand: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    seasonality_factor: float
    trend_factor: float
    model_accuracy: float


@dataclass
class ProductionTrigger:
    trigger_id: str
    component_id: str
    trigger_type: TriggerType
    priority: Priority
    quantity_needed: int
    required_by_date: datetime
    estimated_cost: float
    supplier_id: str
    production_method: ProductionMethod
    created_at: datetime
    executed: bool = False
    execution_date: Optional[datetime] = None


@dataclass
class OptimizationResult:
    component_id: str
    optimal_order_quantity: int
    optimal_reorder_point: int
    expected_annual_cost: float
    service_level: float
    stockout_probability: float
    holding_cost: float
    ordering_cost: float


class DemandForecaster:
    """Advanced demand forecasting using machine learning"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
    
    async def generate_forecast(self, component_id: str, 
                              forecast_days: int = 30) -> DemandForecast:
        """Generate demand forecast for component"""
        # Get historical demand data
        historical_data = await self._get_historical_demand(component_id)
        
        if len(historical_data) < 30:
            # Insufficient data, use simple average
            return await self._simple_forecast(component_id, forecast_days)
        
        # Prepare features
        features, target = await self._prepare_features(historical_data)
        
        # Train or load model
        model = await self._get_or_train_model(component_id, features, target)
        
        # Generate forecast
        forecast_features = await self._generate_forecast_features(
            component_id, forecast_days
        )
        
        predicted_demand = model.predict(forecast_features)[0]
        
        # Calculate confidence intervals
        confidence_lower, confidence_upper = await self._calculate_confidence_intervals(
            model, forecast_features, predicted_demand
        )
        
        # Calculate seasonality and trend factors
        seasonality_factor = await self._calculate_seasonality_factor(component_id)
        trend_factor = await self._calculate_trend_factor(historical_data)
        
        # Model accuracy
        accuracy = self._calculate_model_accuracy(component_id)
        
        return DemandForecast(
            component_id=component_id,
            forecast_date=datetime.now(),
            forecast_period_days=forecast_days,
            predicted_demand=max(0, predicted_demand),
            confidence_interval_lower=max(0, confidence_lower),
            confidence_interval_upper=max(0, confidence_upper),
            seasonality_factor=seasonality_factor,
            trend_factor=trend_factor,
            model_accuracy=accuracy
        )
    
    async def _get_historical_demand(self, component_id: str) -> pd.DataFrame:
        """Get historical demand data"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT 
            demand_date,
            quantity,
            order_id,
            customer_type,
            seasonal_indicator
        FROM demand_history 
        WHERE component_id = ? 
        AND demand_date >= date('now', '-365 days')
        ORDER BY demand_date
        """
        
        df = pd.read_sql_query(query, conn, params=(component_id,))
        conn.close()
        
        if not df.empty:
            df['demand_date'] = pd.to_datetime(df['demand_date'])
            df = df.set_index('demand_date')
        
        return df
    
    async def _prepare_features(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for machine learning model"""
        # Time-based features
        data['day_of_week'] = data.index.dayofweek
        data['day_of_month'] = data.index.day
        data['month'] = data.index.month
        data['quarter'] = data.index.quarter
        data['is_weekend'] = (data.index.dayofweek >= 5).astype(int)
        
        # Lag features
        for lag in [1, 7, 14, 30]:
            data[f'demand_lag_{lag}'] = data['quantity'].shift(lag)
        
        # Rolling statistics
        for window in [7, 14, 30]:
            data[f'demand_mean_{window}d'] = data['quantity'].rolling(window).mean()
            data[f'demand_std_{window}d'] = data['quantity'].rolling(window).std()
        
        # Trend features
        data['demand_trend'] = data['quantity'].rolling(30).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0
        )
        
        # Economic indicators (simulated)
        data['economic_indicator'] = np.random.normal(1.0, 0.1, len(data))
        
        # Customer type encoding
        customer_type_encoded = pd.get_dummies(data['customer_type'], prefix='customer')
        data = pd.concat([data, customer_type_encoded], axis=1)
        
        # Remove rows with NaN values
        data = data.dropna()
        
        # Select feature columns
        feature_columns = [col for col in data.columns 
                         if col not in ['quantity', 'order_id', 'customer_type', 'seasonal_indicator']]
        
        features = data[feature_columns].values
        target = data['quantity'].values
        
        return features, target
    
    async def _get_or_train_model(self, component_id: str, 
                                 features: np.ndarray, target: np.ndarray):
        """Get existing model or train new one"""
        if component_id in self.models:
            return self.models[component_id]
        
        # Split data for training
        X_train, X_test, y_train, y_test = train_test_split(
            features, target, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Try multiple models and select best
        models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boost': GradientBoostingRegressor(n_estimators=100, random_state=42)
        }
        
        best_model = None
        best_score = float('inf')
        
        for name, model in models.items():
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            
            if mae < best_score:
                best_score = mae
                best_model = model
        
        # Store model and scaler
        self.models[component_id] = best_model
        self.scalers[component_id] = scaler
        
        # Store feature importance for random forest
        if hasattr(best_model, 'feature_importances_'):
            self.feature_importance[component_id] = best_model.feature_importances_
        
        return best_model
    
    async def _generate_forecast_features(self, component_id: str, 
                                        forecast_days: int) -> np.ndarray:
        """Generate features for forecasting"""
        # Get recent data for lag features
        recent_data = await self._get_historical_demand(component_id)
        
        if recent_data.empty:
            # Default features if no historical data
            forecast_date = datetime.now() + timedelta(days=forecast_days)
            features = np.array([[
                forecast_date.weekday(),
                forecast_date.day,
                forecast_date.month,
                forecast_date.quarter,
                1 if forecast_date.weekday() >= 5 else 0,
                0, 0, 0, 0,  # lag features
                0, 0, 0, 0, 0, 0,  # rolling stats
                0,  # trend
                1.0,  # economic indicator
                1, 0, 0  # customer type dummies (assuming 3 types)
            ]])
        else:
            # Calculate features based on recent data
            forecast_date = datetime.now() + timedelta(days=forecast_days)
            
            # Time features
            time_features = [
                forecast_date.weekday(),
                forecast_date.day,
                forecast_date.month,
                forecast_date.quarter,
                1 if forecast_date.weekday() >= 5 else 0
            ]
            
            # Lag features from recent data
            recent_quantities = recent_data['quantity'].values
            lag_features = [
                recent_quantities[-1] if len(recent_quantities) >= 1 else 0,
                recent_quantities[-7] if len(recent_quantities) >= 7 else 0,
                recent_quantities[-14] if len(recent_quantities) >= 14 else 0,
                recent_quantities[-30] if len(recent_quantities) >= 30 else 0
            ]
            
            # Rolling statistics
            rolling_features = [
                np.mean(recent_quantities[-7:]) if len(recent_quantities) >= 7 else 0,
                np.std(recent_quantities[-7:]) if len(recent_quantities) >= 7 else 0,
                np.mean(recent_quantities[-14:]) if len(recent_quantities) >= 14 else 0,
                np.std(recent_quantities[-14:]) if len(recent_quantities) >= 14 else 0,
                np.mean(recent_quantities[-30:]) if len(recent_quantities) >= 30 else 0,
                np.std(recent_quantities[-30:]) if len(recent_quantities) >= 30 else 0
            ]
            
            # Trend
            if len(recent_quantities) >= 30:
                trend = np.polyfit(range(30), recent_quantities[-30:], 1)[0]
            else:
                trend = 0
            
            # Other features
            other_features = [
                trend,
                1.0,  # economic indicator
                1, 0, 0  # customer type dummies
            ]
            
            features = np.array([time_features + lag_features + rolling_features + other_features])
        
        # Scale features if scaler exists
        if component_id in self.scalers:
            features = self.scalers[component_id].transform(features)
        
        return features
    
    async def _calculate_confidence_intervals(self, model, features: np.ndarray, 
                                           prediction: float) -> Tuple[float, float]:
        """Calculate prediction confidence intervals"""
        # For simplicity, use standard deviation of residuals
        # In production, use more sophisticated methods like quantile regression
        
        # Estimate prediction uncertainty (simplified)
        uncertainty = prediction * 0.2  # 20% uncertainty
        
        confidence_lower = prediction - 1.96 * uncertainty  # 95% CI
        confidence_upper = prediction + 1.96 * uncertainty
        
        return confidence_lower, confidence_upper
    
    async def _calculate_seasonality_factor(self, component_id: str) -> float:
        """Calculate seasonality factor for component"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT AVG(quantity) as avg_demand, 
               strftime('%m', demand_date) as month
        FROM demand_history 
        WHERE component_id = ? 
        AND demand_date >= date('now', '-365 days')
        GROUP BY strftime('%m', demand_date)
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (component_id,))
        monthly_data = cursor.fetchall()
        conn.close()
        
        if not monthly_data:
            return 1.0
        
        # Calculate coefficient of variation for seasonality
        monthly_demands = [row[0] for row in monthly_data]
        cv = np.std(monthly_demands) / np.mean(monthly_demands) if np.mean(monthly_demands) > 0 else 0
        
        # Convert to seasonality factor (higher CV = more seasonal)
        return min(2.0, 1.0 + cv)
    
    async def _calculate_trend_factor(self, data: pd.DataFrame) -> float:
        """Calculate trend factor from historical data"""
        if data.empty or len(data) < 30:
            return 1.0
        
        # Calculate trend using linear regression
        x = np.arange(len(data))
        y = data['quantity'].values
        
        try:
            slope, intercept = np.polyfit(x, y, 1)
            # Normalize trend factor
            avg_demand = np.mean(y)
            trend_factor = 1.0 + (slope * 30) / avg_demand if avg_demand > 0 else 1.0
            return max(0.5, min(2.0, trend_factor))
        except:
            return 1.0
    
    def _calculate_model_accuracy(self, component_id: str) -> float:
        """Calculate model accuracy score"""
        if component_id not in self.models:
            return 0.5  # Default accuracy if no model
        
        # In production, this would use validation data
        # For now, return a simulated accuracy based on historical performance
        return np.random.uniform(0.7, 0.95)
    
    async def _simple_forecast(self, component_id: str, forecast_days: int) -> DemandForecast:
        """Simple forecast for components with insufficient data"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
        SELECT AVG(quantity) as avg_demand
        FROM demand_history 
        WHERE component_id = ? 
        AND demand_date >= date('now', '-90 days')
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (component_id,))
        result = cursor.fetchone()
        conn.close()
        
        avg_demand = result[0] if result and result[0] else 10.0
        
        return DemandForecast(
            component_id=component_id,
            forecast_date=datetime.now(),
            forecast_period_days=forecast_days,
            predicted_demand=avg_demand,
            confidence_interval_lower=avg_demand * 0.7,
            confidence_interval_upper=avg_demand * 1.3,
            seasonality_factor=1.0,
            trend_factor=1.0,
            model_accuracy=0.5
        )


class InventoryOptimizer:
    """Inventory optimization using economic order quantity and safety stock calculations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def optimize_inventory_parameters(self, component_id: str) -> OptimizationResult:
        """Optimize inventory parameters for component"""
        # Get component data
        component = await self._get_component_data(component_id)
        
        # Get demand statistics
        demand_stats = await self._get_demand_statistics(component_id)
        
        # Get cost parameters
        cost_params = await self._get_cost_parameters(component_id)
        
        # Calculate optimal order quantity (EOQ)
        eoq = await self._calculate_eoq(demand_stats, cost_params)
        
        # Calculate safety stock and reorder point
        safety_stock = await self._calculate_safety_stock(
            component_id, demand_stats, component.lead_time_days
        )
        
        reorder_point = int(
            demand_stats['daily_average'] * component.lead_time_days + safety_stock
        )
        
        # Calculate expected costs
        annual_cost = await self._calculate_total_annual_cost(
            eoq, reorder_point, demand_stats, cost_params
        )
        
        # Calculate service level and stockout probability
        service_level, stockout_prob = await self._calculate_service_metrics(
            safety_stock, demand_stats
        )
        
        return OptimizationResult(
            component_id=component_id,
            optimal_order_quantity=int(eoq),
            optimal_reorder_point=reorder_point,
            expected_annual_cost=annual_cost,
            service_level=service_level,
            stockout_probability=stockout_prob,
            holding_cost=cost_params['holding_cost_rate'] * component.unit_cost * eoq / 2,
            ordering_cost=cost_params['ordering_cost'] * demand_stats['annual_demand'] / eoq
        )
    
    async def _get_component_data(self, component_id: str) -> Component:
        """Get component data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM components WHERE component_id = ?", (component_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            # Return default component if not found
            return Component(
                component_id=component_id,
                name="Unknown Component",
                category="general",
                unit_cost=10.0,
                lead_time_days=14,
                supplier_id="default",
                min_order_quantity=1,
                inventory_strategy=InventoryStrategy.JIT,
                critical_component=False
            )
        
        return Component(
            component_id=row[0],
            name=row[1],
            category=row[2],
            unit_cost=row[3],
            lead_time_days=row[4],
            supplier_id=row[5],
            min_order_quantity=row[6],
            inventory_strategy=InventoryStrategy(row[7]),
            critical_component=bool(row[8]),
            shelf_life_days=row[9],
            storage_requirements=json.loads(row[10]) if row[10] else None
        )
    
    async def _get_demand_statistics(self, component_id: str) -> Dict[str, float]:
        """Get demand statistics for component"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(quantity) as avg_daily,
                STDDEV(quantity) as std_daily,
                SUM(quantity) as total_demand,
                COUNT(*) as demand_days
            FROM demand_history 
            WHERE component_id = ? 
            AND demand_date >= date('now', '-365 days')
        """, (component_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return {
                'daily_average': 5.0,
                'daily_std': 2.0,
                'annual_demand': 1825.0,  # 5 * 365
                'coefficient_of_variation': 0.4
            }
        
        avg_daily, std_daily, total_demand, demand_days = result
        
        return {
            'daily_average': avg_daily,
            'daily_std': std_daily or avg_daily * 0.3,
            'annual_demand': total_demand * 365.0 / demand_days if demand_days > 0 else total_demand or 0,
            'coefficient_of_variation': (std_daily / avg_daily) if avg_daily > 0 else 0.3
        }
    
    async def _get_cost_parameters(self, component_id: str) -> Dict[str, float]:
        """Get cost parameters for optimization"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ordering_cost, holding_cost_rate, stockout_cost_rate
            FROM cost_parameters 
            WHERE component_id = ?
        """, (component_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'ordering_cost': result[0],
                'holding_cost_rate': result[1],
                'stockout_cost_rate': result[2]
            }
        else:
            # Default cost parameters
            return {
                'ordering_cost': 50.0,  # Cost per order
                'holding_cost_rate': 0.25,  # 25% of item value per year
                'stockout_cost_rate': 100.0  # Cost per stockout occurrence
            }
    
    async def _calculate_eoq(self, demand_stats: Dict[str, float], 
                           cost_params: Dict[str, float]) -> float:
        """Calculate Economic Order Quantity"""
        annual_demand = demand_stats['annual_demand']
        ordering_cost = cost_params['ordering_cost']
        holding_cost = cost_params['holding_cost_rate']
        
        if holding_cost <= 0 or annual_demand <= 0:
            return 100.0  # Default quantity
        
        eoq = np.sqrt(2 * annual_demand * ordering_cost / holding_cost)
        return max(1.0, eoq)
    
    async def _calculate_safety_stock(self, component_id: str, 
                                    demand_stats: Dict[str, float],
                                    lead_time_days: int) -> float:
        """Calculate safety stock based on demand variability and lead time"""
        # Get lead time variability
        lead_time_std = await self._get_lead_time_std(component_id)
        
        daily_std = demand_stats['daily_std']
        daily_avg = demand_stats['daily_average']
        
        # Service level (99% = z=2.33, 95% = z=1.64)
        service_level_z = 1.96  # 97.5% service level
        
        # Safety stock formula considering both demand and lead time uncertainty
        demand_uncertainty = daily_std * np.sqrt(lead_time_days)
        lead_time_uncertainty = daily_avg * lead_time_std if lead_time_std > 0 else 0
        
        safety_stock = service_level_z * np.sqrt(
            demand_uncertainty**2 + lead_time_uncertainty**2
        )
        
        return max(0.0, safety_stock)
    
    async def _get_lead_time_std(self, component_id: str) -> float:
        """Get lead time standard deviation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT STDDEV(actual_lead_time)
            FROM delivery_history 
            WHERE component_id = ? 
            AND delivery_date >= date('now', '-180 days')
        """, (component_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 2.0  # Default 2-day std deviation
    
    async def _calculate_total_annual_cost(self, eoq: float, reorder_point: int,
                                         demand_stats: Dict[str, float],
                                         cost_params: Dict[str, float]) -> float:
        """Calculate total annual inventory cost"""
        annual_demand = demand_stats['annual_demand']
        ordering_cost = cost_params['ordering_cost']
        holding_cost_rate = cost_params['holding_cost_rate']
        
        # Ordering cost
        annual_ordering_cost = (annual_demand / eoq) * ordering_cost
        
        # Holding cost
        annual_holding_cost = (eoq / 2) * holding_cost_rate
        
        # Safety stock holding cost
        safety_stock = reorder_point - demand_stats['daily_average'] * 14  # Assuming 14-day lead time
        safety_stock_cost = max(0, safety_stock) * holding_cost_rate
        
        return annual_ordering_cost + annual_holding_cost + safety_stock_cost
    
    async def _calculate_service_metrics(self, safety_stock: float,
                                       demand_stats: Dict[str, float]) -> Tuple[float, float]:
        """Calculate service level and stockout probability"""
        # Simplified calculation
        cv = demand_stats['coefficient_of_variation']
        
        # Higher safety stock = better service level
        service_level = 0.95 + 0.04 * min(1.0, safety_stock / (demand_stats['daily_average'] * 7))
        stockout_prob = 1.0 - service_level
        
        return min(0.99, service_level), max(0.01, stockout_prob)


class TriggerEngine:
    """Engine for generating and managing JIT production triggers"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.forecaster = DemandForecaster(db_path)
        self.optimizer = InventoryOptimizer(db_path)
    
    async def generate_triggers(self) -> List[ProductionTrigger]:
        """Generate all production triggers based on current conditions"""
        triggers = []
        
        # Get all active components
        components = await self._get_active_components()
        
        for component in components:
            component_triggers = await self._check_component_triggers(component)
            triggers.extend(component_triggers)
        
        # Sort by priority and required date
        triggers.sort(key=lambda x: (x.priority.value, x.required_by_date))
        
        return triggers
    
    async def _get_active_components(self) -> List[Component]:
        """Get all active components"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM components WHERE is_active = 1")
        rows = cursor.fetchall()
        conn.close()
        
        components = []
        for row in rows:
            components.append(Component(
                component_id=row[0],
                name=row[1],
                category=row[2],
                unit_cost=row[3],
                lead_time_days=row[4],
                supplier_id=row[5],
                min_order_quantity=row[6],
                inventory_strategy=InventoryStrategy(row[7]),
                critical_component=bool(row[8]),
                shelf_life_days=row[9],
                storage_requirements=json.loads(row[10]) if row[10] else None
            ))
        
        return components
    
    async def _check_component_triggers(self, component: Component) -> List[ProductionTrigger]:
        """Check all trigger conditions for a component"""
        triggers = []
        
        # Get current inventory
        current_inventory = await self._get_current_inventory(component.component_id)
        
        # Get optimization parameters
        optimization = await self.optimizer.optimize_inventory_parameters(component.component_id)
        
        # Get demand forecast
        forecast = await self.forecaster.generate_forecast(component.component_id)
        
        # Check reorder point trigger
        reorder_trigger = await self._check_reorder_point(
            component, current_inventory, optimization
        )
        if reorder_trigger:
            triggers.append(reorder_trigger)
        
        # Check demand spike trigger
        spike_trigger = await self._check_demand_spike(
            component, current_inventory, forecast
        )
        if spike_trigger:
            triggers.append(spike_trigger)
        
        # Check inventory low trigger
        low_inventory_trigger = await self._check_low_inventory(
            component, current_inventory, forecast
        )
        if low_inventory_trigger:
            triggers.append(low_inventory_trigger)
        
        # Check lead time variance trigger
        lead_time_trigger = await self._check_lead_time_variance(
            component, current_inventory
        )
        if lead_time_trigger:
            triggers.append(lead_time_trigger)
        
        # Check supplier disruption trigger
        disruption_trigger = await self._check_supplier_disruption(
            component, current_inventory
        )
        if disruption_trigger:
            triggers.append(disruption_trigger)
        
        return triggers
    
    async def _get_current_inventory(self, component_id: str) -> int:
        """Get current available inventory for component"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(quantity_available)
            FROM inventory_records 
            WHERE component_id = ? 
            AND (expiry_date IS NULL OR expiry_date > date('now'))
        """, (component_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else 0
    
    async def _check_reorder_point(self, component: Component, 
                                 current_inventory: int,
                                 optimization: OptimizationResult) -> Optional[ProductionTrigger]:
        """Check if inventory has hit reorder point"""
        if current_inventory <= optimization.optimal_reorder_point:
            required_date = datetime.now() + timedelta(days=component.lead_time_days)
            
            return ProductionTrigger(
                trigger_id=f"reorder_{component.component_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                component_id=component.component_id,
                trigger_type=TriggerType.REORDER_POINT,
                priority=Priority.HIGH if component.critical_component else Priority.MEDIUM,
                quantity_needed=optimization.optimal_order_quantity,
                required_by_date=required_date,
                estimated_cost=optimization.optimal_order_quantity * component.unit_cost,
                supplier_id=component.supplier_id,
                production_method=ProductionMethod.MAKE_TO_STOCK,
                created_at=datetime.now()
            )
        
        return None
    
    async def _check_demand_spike(self, component: Component,
                                current_inventory: int,
                                forecast: DemandForecast) -> Optional[ProductionTrigger]:
        """Check for demand spike requiring additional inventory"""
        # Compare forecast to recent average
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT AVG(quantity)
            FROM demand_history 
            WHERE component_id = ? 
            AND demand_date >= date('now', '-30 days')
        """, (component.component_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        recent_avg = result[0] if result and result[0] else forecast.predicted_demand
        
        # Check if forecast is significantly higher than recent average
        spike_threshold = recent_avg * 1.5  # 50% increase threshold
        
        if forecast.predicted_demand > spike_threshold:
            required_quantity = int(forecast.predicted_demand - current_inventory)
            
            if required_quantity > 0:
                return ProductionTrigger(
                    trigger_id=f"spike_{component.component_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    component_id=component.component_id,
                    trigger_type=TriggerType.DEMAND_SPIKE,
                    priority=Priority.HIGH,
                    quantity_needed=required_quantity,
                    required_by_date=datetime.now() + timedelta(days=forecast.forecast_period_days),
                    estimated_cost=required_quantity * component.unit_cost,
                    supplier_id=component.supplier_id,
                    production_method=ProductionMethod.MAKE_TO_ORDER,
                    created_at=datetime.now()
                )
        
        return None
    
    async def _check_low_inventory(self, component: Component,
                                 current_inventory: int,
                                 forecast: DemandForecast) -> Optional[ProductionTrigger]:
        """Check for critically low inventory"""
        # Calculate minimum safety stock
        min_safety_days = 3 if component.critical_component else 1
        min_safety_stock = forecast.predicted_demand / 30 * min_safety_days
        
        if current_inventory < min_safety_stock:
            return ProductionTrigger(
                trigger_id=f"low_{component.component_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                component_id=component.component_id,
                trigger_type=TriggerType.INVENTORY_LOW,
                priority=Priority.CRITICAL if component.critical_component else Priority.HIGH,
                quantity_needed=int(min_safety_stock * 2),  # Double safety stock
                required_by_date=datetime.now() + timedelta(days=min_safety_days),
                estimated_cost=int(min_safety_stock * 2) * component.unit_cost,
                supplier_id=component.supplier_id,
                production_method=ProductionMethod.MAKE_TO_STOCK,
                created_at=datetime.now()
            )
        
        return None
    
    async def _check_lead_time_variance(self, component: Component,
                                      current_inventory: int) -> Optional[ProductionTrigger]:
        """Check for lead time variance requiring buffer adjustment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent lead time performance
        cursor.execute("""
            SELECT AVG(actual_lead_time), STDDEV(actual_lead_time)
            FROM delivery_history 
            WHERE component_id = ? 
            AND delivery_date >= date('now', '-90 days')
        """, (component.component_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            return None
        
        avg_lead_time, std_lead_time = result
        
        # Check if lead time variance is high
        cv = (std_lead_time / avg_lead_time) if avg_lead_time > 0 else 0
        
        if cv > 0.5:  # High variance threshold
            # Calculate additional buffer needed
            buffer_days = int(std_lead_time * 2)  # 2 standard deviations
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(quantity)
                FROM demand_history 
                WHERE component_id = ? 
                AND demand_date >= date('now', '-30 days')
            """, (component.component_id,))
            
            avg_daily_demand = cursor.fetchone()[0] or 1.0
            conn.close()
            
            buffer_quantity = int(avg_daily_demand * buffer_days)
            
            return ProductionTrigger(
                trigger_id=f"leadtime_{component.component_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                component_id=component.component_id,
                trigger_type=TriggerType.LEAD_TIME_VARIANCE,
                priority=Priority.MEDIUM,
                quantity_needed=buffer_quantity,
                required_by_date=datetime.now() + timedelta(days=component.lead_time_days + buffer_days),
                estimated_cost=buffer_quantity * component.unit_cost,
                supplier_id=component.supplier_id,
                production_method=ProductionMethod.MAKE_TO_STOCK,
                created_at=datetime.now()
            )
        
        return None
    
    async def _check_supplier_disruption(self, component: Component,
                                       current_inventory: int) -> Optional[ProductionTrigger]:
        """Check for supplier disruption risks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check supplier risk level
        cursor.execute("""
            SELECT risk_level, last_delivery_date
            FROM supplier_status 
            WHERE supplier_id = ?
        """, (component.supplier_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        risk_level, last_delivery = result
        
        # Check if high risk or no recent deliveries
        if risk_level in ['high', 'critical'] or (
            last_delivery and 
            (datetime.now() - datetime.fromisoformat(last_delivery)).days > 30
        ):
            # Recommend building extra inventory
            safety_multiplier = 3 if risk_level == 'critical' else 2
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT AVG(quantity) * ?
                FROM demand_history 
                WHERE component_id = ? 
                AND demand_date >= date('now', '-30 days')
            """, (safety_multiplier * 30, component.component_id))  # 30-90 day supply
            
            safety_quantity = cursor.fetchone()[0] or component.min_order_quantity * safety_multiplier
            conn.close()
            
            return ProductionTrigger(
                trigger_id=f"disruption_{component.component_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                component_id=component.component_id,
                trigger_type=TriggerType.SUPPLIER_DISRUPTION,
                priority=Priority.HIGH,
                quantity_needed=int(safety_quantity),
                required_by_date=datetime.now() + timedelta(days=component.lead_time_days),
                estimated_cost=int(safety_quantity) * component.unit_cost,
                supplier_id=component.supplier_id,
                production_method=ProductionMethod.MAKE_TO_STOCK,
                created_at=datetime.now()
            )
        
        return None


class JITManufacturingTriggers:
    """Main system for just-in-time manufacturing trigger management"""
    
    def __init__(self, db_path: str = "jit_triggers.db"):
        self.db_path = db_path
        self.trigger_engine = TriggerEngine(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize JIT triggers database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Components table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS components (
                component_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                unit_cost REAL,
                lead_time_days INTEGER,
                supplier_id TEXT,
                min_order_quantity INTEGER,
                inventory_strategy TEXT,
                critical_component BOOLEAN,
                shelf_life_days INTEGER,
                storage_requirements TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inventory records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_records (
                record_id TEXT PRIMARY KEY,
                component_id TEXT,
                timestamp TIMESTAMP,
                quantity_on_hand INTEGER,
                quantity_reserved INTEGER,
                quantity_available INTEGER,
                location TEXT,
                batch_number TEXT,
                expiry_date TIMESTAMP,
                FOREIGN KEY (component_id) REFERENCES components (component_id)
            )
        """)
        
        # Demand history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS demand_history (
                demand_id TEXT PRIMARY KEY,
                component_id TEXT,
                demand_date DATE,
                quantity INTEGER,
                order_id TEXT,
                customer_type TEXT,
                seasonal_indicator TEXT,
                FOREIGN KEY (component_id) REFERENCES components (component_id)
            )
        """)
        
        # Production triggers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_triggers (
                trigger_id TEXT PRIMARY KEY,
                component_id TEXT,
                trigger_type TEXT,
                priority TEXT,
                quantity_needed INTEGER,
                required_by_date TIMESTAMP,
                estimated_cost REAL,
                supplier_id TEXT,
                production_method TEXT,
                created_at TIMESTAMP,
                executed BOOLEAN DEFAULT 0,
                execution_date TIMESTAMP,
                FOREIGN KEY (component_id) REFERENCES components (component_id)
            )
        """)
        
        # Cost parameters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_parameters (
                component_id TEXT PRIMARY KEY,
                ordering_cost REAL,
                holding_cost_rate REAL,
                stockout_cost_rate REAL,
                FOREIGN KEY (component_id) REFERENCES components (component_id)
            )
        """)
        
        # Delivery history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_history (
                delivery_id TEXT PRIMARY KEY,
                component_id TEXT,
                delivery_date TIMESTAMP,
                actual_lead_time INTEGER,
                quantity_delivered INTEGER,
                FOREIGN KEY (component_id) REFERENCES components (component_id)
            )
        """)
        
        # Supplier status table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_status (
                supplier_id TEXT PRIMARY KEY,
                risk_level TEXT,
                last_delivery_date TIMESTAMP,
                performance_score REAL
            )
        """)
        
        # Demand forecasts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS demand_forecasts (
                forecast_id TEXT PRIMARY KEY,
                component_id TEXT,
                forecast_date TIMESTAMP,
                forecast_period_days INTEGER,
                predicted_demand REAL,
                confidence_interval_lower REAL,
                confidence_interval_upper REAL,
                seasonality_factor REAL,
                trend_factor REAL,
                model_accuracy REAL,
                FOREIGN KEY (component_id) REFERENCES components (component_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def run_trigger_cycle(self) -> Dict[str, Any]:
        """Run complete trigger generation and processing cycle"""
        start_time = datetime.now()
        
        # Generate all triggers
        triggers = await self.trigger_engine.generate_triggers()
        
        # Store triggers in database
        stored_triggers = 0
        for trigger in triggers:
            if await self._store_trigger(trigger):
                stored_triggers += 1
        
        # Process high-priority triggers
        processed_triggers = await self._process_critical_triggers()
        
        # Update forecasts
        updated_forecasts = await self._update_all_forecasts()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'cycle_start': start_time,
            'processing_time_seconds': processing_time,
            'triggers_generated': len(triggers),
            'triggers_stored': stored_triggers,
            'critical_triggers_processed': processed_triggers,
            'forecasts_updated': updated_forecasts,
            'trigger_breakdown': self._get_trigger_breakdown(triggers)
        }
    
    async def _store_trigger(self, trigger: ProductionTrigger) -> bool:
        """Store production trigger in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if similar trigger already exists
            cursor.execute("""
                SELECT COUNT(*) FROM production_triggers 
                WHERE component_id = ? AND trigger_type = ? 
                AND executed = 0 AND created_at > date('now', '-1 day')
            """, (trigger.component_id, trigger.trigger_type.value))
            
            if cursor.fetchone()[0] > 0:
                conn.close()
                return False  # Similar trigger already exists
            
            # Store new trigger
            cursor.execute("""
                INSERT INTO production_triggers 
                (trigger_id, component_id, trigger_type, priority, quantity_needed,
                 required_by_date, estimated_cost, supplier_id, production_method,
                 created_at, executed, execution_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trigger.trigger_id, trigger.component_id, trigger.trigger_type.value,
                trigger.priority.value, trigger.quantity_needed, trigger.required_by_date,
                trigger.estimated_cost, trigger.supplier_id, trigger.production_method.value,
                trigger.created_at, trigger.executed, trigger.execution_date
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error storing trigger: {e}")
            return False
    
    async def _process_critical_triggers(self) -> int:
        """Process critical priority triggers automatically"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get critical triggers
        cursor.execute("""
            SELECT * FROM production_triggers 
            WHERE priority = 'critical' AND executed = 0
            ORDER BY required_by_date
        """)
        
        triggers = cursor.fetchall()
        processed = 0
        
        for trigger_row in triggers:
            trigger_id = trigger_row[0]
            
            # Mark as executed (in production, this would trigger actual procurement)
            cursor.execute("""
                UPDATE production_triggers 
                SET executed = 1, execution_date = ?
                WHERE trigger_id = ?
            """, (datetime.now(), trigger_id))
            
            processed += 1
        
        conn.commit()
        conn.close()
        
        return processed
    
    async def _update_all_forecasts(self) -> int:
        """Update demand forecasts for all components"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT component_id FROM components WHERE is_active = 1")
        component_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        updated = 0
        
        for component_id in component_ids:
            try:
                forecast = await self.trigger_engine.forecaster.generate_forecast(component_id)
                await self._store_forecast(forecast)
                updated += 1
            except Exception as e:
                print(f"Error updating forecast for {component_id}: {e}")
        
        return updated
    
    async def _store_forecast(self, forecast: DemandForecast) -> bool:
        """Store demand forecast in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            forecast_id = f"forecast_{forecast.component_id}_{forecast.forecast_date.strftime('%Y%m%d_%H%M%S')}"
            
            cursor.execute("""
                INSERT INTO demand_forecasts 
                (forecast_id, component_id, forecast_date, forecast_period_days,
                 predicted_demand, confidence_interval_lower, confidence_interval_upper,
                 seasonality_factor, trend_factor, model_accuracy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                forecast_id, forecast.component_id, forecast.forecast_date,
                forecast.forecast_period_days, forecast.predicted_demand,
                forecast.confidence_interval_lower, forecast.confidence_interval_upper,
                forecast.seasonality_factor, forecast.trend_factor, forecast.model_accuracy
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error storing forecast: {e}")
            return False
    
    def _get_trigger_breakdown(self, triggers: List[ProductionTrigger]) -> Dict[str, int]:
        """Get breakdown of triggers by type and priority"""
        breakdown = {}
        
        # Count by type
        for trigger in triggers:
            trigger_type = trigger.trigger_type.value
            breakdown[f"type_{trigger_type}"] = breakdown.get(f"type_{trigger_type}", 0) + 1
        
        # Count by priority
        for trigger in triggers:
            priority = trigger.priority.value
            breakdown[f"priority_{priority}"] = breakdown.get(f"priority_{priority}", 0) + 1
        
        return breakdown
    
    async def get_trigger_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive trigger dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Active triggers
        cursor.execute("""
            SELECT trigger_type, priority, COUNT(*) as count
            FROM production_triggers 
            WHERE executed = 0
            GROUP BY trigger_type, priority
        """)
        active_triggers = cursor.fetchall()
        
        # Recent executions
        cursor.execute("""
            SELECT COUNT(*) as executed_today
            FROM production_triggers 
            WHERE executed = 1 AND date(execution_date) = date('now')
        """)
        executed_today = cursor.fetchone()[0]
        
        # Cost impact
        cursor.execute("""
            SELECT SUM(estimated_cost) as total_cost
            FROM production_triggers 
            WHERE executed = 0 AND priority IN ('critical', 'high')
        """)
        pending_cost = cursor.fetchone()[0] or 0
        
        # Component coverage
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT c.component_id) as total_components,
                COUNT(DISTINCT pt.component_id) as components_with_triggers
            FROM components c
            LEFT JOIN production_triggers pt ON c.component_id = pt.component_id AND pt.executed = 0
            WHERE c.is_active = 1
        """)
        coverage = cursor.fetchone()
        
        conn.close()
        
        return {
            'dashboard_date': datetime.now(),
            'active_triggers': [
                {
                    'type': row[0],
                    'priority': row[1],
                    'count': row[2]
                }
                for row in active_triggers
            ],
            'executed_today': executed_today,
            'pending_cost_estimate': pending_cost,
            'component_coverage': {
                'total_components': coverage[0],
                'components_with_triggers': coverage[1],
                'coverage_percentage': (coverage[1] / coverage[0] * 100) if coverage[0] > 0 else 0
            }
        }
    
    async def add_sample_data(self):
        """Add sample data for testing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sample components
        sample_components = [
            ('COMP001', 'Electronic Module A', 'electronics', 25.50, 14, 'SUPP001', 100, 'just_in_time', True, None, None),
            ('COMP002', 'Plastic Housing B', 'plastics', 8.75, 7, 'SUPP002', 500, 'kanban', False, 720, None),
            ('COMP003', 'Metal Bracket C', 'metals', 12.30, 21, 'SUPP003', 200, 'safety_stock', True, None, None)
        ]
        
        for comp in sample_components:
            cursor.execute("""
                INSERT OR REPLACE INTO components 
                (component_id, name, category, unit_cost, lead_time_days, supplier_id,
                 min_order_quantity, inventory_strategy, critical_component, shelf_life_days, storage_requirements)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, comp)
        
        # Sample inventory
        sample_inventory = [
            ('INV001', 'COMP001', datetime.now(), 150, 50, 100, 'WH-A01', 'BATCH001', None),
            ('INV002', 'COMP002', datetime.now(), 800, 200, 600, 'WH-B02', 'BATCH002', datetime.now() + timedelta(days=720)),
            ('INV003', 'COMP003', datetime.now(), 75, 25, 50, 'WH-C03', 'BATCH003', None)
        ]
        
        for inv in sample_inventory:
            cursor.execute("""
                INSERT OR REPLACE INTO inventory_records 
                (record_id, component_id, timestamp, quantity_on_hand, quantity_reserved, 
                 quantity_available, location, batch_number, expiry_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, inv)
        
        # Sample demand history
        base_date = datetime.now() - timedelta(days=90)
        for i in range(90):
            demand_date = base_date + timedelta(days=i)
            
            for comp_id in ['COMP001', 'COMP002', 'COMP003']:
                base_demand = {'COMP001': 15, 'COMP002': 45, 'COMP003': 8}[comp_id]
                daily_demand = max(0, int(np.random.normal(base_demand, base_demand * 0.3)))
                
                cursor.execute("""
                    INSERT OR REPLACE INTO demand_history 
                    (demand_id, component_id, demand_date, quantity, order_id, customer_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"DEM_{comp_id}_{demand_date.strftime('%Y%m%d')}",
                    comp_id, demand_date.date(), daily_demand,
                    f"ORD_{i:04d}", np.random.choice(['retail', 'wholesale', 'industrial'])
                ))
        
        # Sample supplier status
        sample_suppliers = [
            ('SUPP001', 'low', datetime.now() - timedelta(days=5), 0.92),
            ('SUPP002', 'medium', datetime.now() - timedelta(days=10), 0.85),
            ('SUPP003', 'high', datetime.now() - timedelta(days=35), 0.65)
        ]
        
        for supp in sample_suppliers:
            cursor.execute("""
                INSERT OR REPLACE INTO supplier_status 
                (supplier_id, risk_level, last_delivery_date, performance_score)
                VALUES (?, ?, ?, ?)
            """, supp)
        
        conn.commit()
        conn.close()


async def main():
    """Example usage of JIT Manufacturing Triggers"""
    jit_system = JITManufacturingTriggers()
    
    # Add sample data
    await jit_system.add_sample_data()
    print("Added sample data")
    
    # Run trigger cycle
    results = await jit_system.run_trigger_cycle()
    
    print(f"\nJIT Trigger Cycle Results:")
    print(f"Processing Time: {results['processing_time_seconds']:.2f} seconds")
    print(f"Triggers Generated: {results['triggers_generated']}")
    print(f"Critical Triggers Processed: {results['critical_triggers_processed']}")
    print(f"Forecasts Updated: {results['forecasts_updated']}")
    
    print(f"\nTrigger Breakdown:")
    for key, value in results['trigger_breakdown'].items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Get dashboard
    dashboard = await jit_system.get_trigger_dashboard()
    
    print(f"\nDashboard Summary:")
    print(f"Active Triggers: {len(dashboard['active_triggers'])}")
    print(f"Executed Today: {dashboard['executed_today']}")
    print(f"Pending Cost: ${dashboard['pending_cost_estimate']:,.2f}")
    print(f"Component Coverage: {dashboard['component_coverage']['coverage_percentage']:.1f}%")
    
    print(f"\nActive Triggers by Type:")
    for trigger in dashboard['active_triggers']:
        print(f"  {trigger['type']} ({trigger['priority']}): {trigger['count']}")


if __name__ == "__main__":
    asyncio.run(main())