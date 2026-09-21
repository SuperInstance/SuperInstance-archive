"""
ActiveLog Manufacturing Suite - Just-in-Time Manufacturing Triggers

AI-driven production triggers, demand forecasting, inventory optimization,
and automated manufacturing scheduling for lean production.
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
    DEMAND_SPIKE = "demand_spike"
    INVENTORY_LOW = "inventory_low"
    SEASONAL_FORECAST = "seasonal_forecast"
    SUPPLIER_DELAY = "supplier_delay"
    QUALITY_ISSUE = "quality_issue"
    CAPACITY_AVAILABLE = "capacity_available"
    CUSTOMER_PRIORITY = "customer_priority"
    COST_OPTIMIZATION = "cost_optimization"


class TriggerPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ProductionStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class DemandPattern(Enum):
    STABLE = "stable"
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SEASONAL = "seasonal"
    VOLATILE = "volatile"
    CYCLIC = "cyclic"


@dataclass
class Product:
    product_id: str
    name: str
    category: str
    unit_cost: float
    setup_time: int  # minutes
    cycle_time: int  # minutes per unit
    minimum_batch_size: int
    maximum_batch_size: int
    shelf_life_days: Optional[int]
    storage_requirements: Dict[str, Any]
    components: List[str]


@dataclass
class InventoryLevel:
    product_id: str
    current_stock: int
    reserved_stock: int
    available_stock: int
    safety_stock: int
    reorder_point: int
    maximum_stock: int
    last_updated: datetime
    location: str


@dataclass
class DemandForecast:
    product_id: str
    forecast_date: datetime
    forecast_horizon_days: int
    predicted_demand: int
    confidence_interval: Tuple[float, float]
    model_accuracy: float
    demand_pattern: DemandPattern
    seasonality_factor: float
    trend_factor: float


@dataclass
class ProductionTrigger:
    trigger_id: str
    trigger_type: TriggerType
    product_id: str
    priority: TriggerPriority
    created_at: datetime
    trigger_reason: str
    recommended_quantity: int
    target_completion: datetime
    cost_impact: float
    risk_factors: List[str]
    automation_confidence: float


@dataclass
class ProductionOrder:
    order_id: str
    product_id: str
    quantity: int
    priority: TriggerPriority
    created_at: datetime
    scheduled_start: datetime
    estimated_completion: datetime
    actual_start: Optional[datetime]
    actual_completion: Optional[datetime]
    status: ProductionStatus
    trigger_id: str
    assigned_line: Optional[str]
    cost_estimate: float


@dataclass
class ManufacturingCapacity:
    line_id: str
    line_name: str
    is_available: bool
    current_utilization: float
    hourly_capacity: int
    setup_time_minutes: int
    changeover_cost: float
    maintenance_schedule: List[datetime]
    qualified_products: List[str]


class DemandForecaster:
    """AI-powered demand forecasting engine"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.models = {}
        self.scalers = {}
        self.feature_columns = [
            'historical_avg', 'trend', 'seasonality', 'day_of_week',
            'month', 'quarter', 'is_holiday', 'price_factor',
            'promotion_factor', 'market_sentiment'
        ]
    
    async def train_demand_model(self, product_id: str, retrain: bool = False):
        """Train demand forecasting model for specific product"""
        if product_id in self.models and not retrain:
            return
        
        # Get historical demand data
        historical_data = await self._get_historical_demand(product_id)
        
        if len(historical_data) < 30:  # Need minimum data for training
            print(f"Insufficient data for {product_id}, using default model")
            return
        
        # Prepare features
        features, targets = self._prepare_features(historical_data, product_id)
        
        if len(features) < 10:
            return
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, targets, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train ensemble model
        model = GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        predictions = model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, predictions)
        mse = mean_squared_error(y_test, predictions)
        
        # Store model and scaler
        self.models[product_id] = {
            'model': model,
            'mae': mae,
            'mse': mse,
            'accuracy': 1 - (mae / np.mean(y_test)) if np.mean(y_test) > 0 else 0
        }
        self.scalers[product_id] = scaler
        
        print(f"Trained model for {product_id}: MAE={mae:.2f}, Accuracy={self.models[product_id]['accuracy']:.2%}")
    
    async def _get_historical_demand(self, product_id: str) -> pd.DataFrame:
        """Get historical demand data for product"""
        conn = sqlite3.connect(self.db_path)
        
        # Get demand history
        query = """
            SELECT date, demand_quantity, price, promotion_active, market_events
            FROM demand_history 
            WHERE product_id = ? 
            AND date >= date('now', '-730 days')
            ORDER BY date
        """
        
        df = pd.read_sql_query(query, conn, params=[product_id])
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        return df
    
    def _prepare_features(self, data: pd.DataFrame, product_id: str) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for demand forecasting"""
        if data.empty:
            return np.array([]), np.array([])
        
        features_list = []
        targets = []
        
        # Calculate rolling statistics
        data['historical_avg'] = data['demand_quantity'].rolling(window=7, min_periods=1).mean()
        data['trend'] = data['demand_quantity'].rolling(window=14, min_periods=1).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0
        )
        
        # Add time-based features
        data['day_of_week'] = data.index.dayofweek
        data['month'] = data.index.month
        data['quarter'] = data.index.quarter
        data['is_holiday'] = self._identify_holidays(data.index)
        
        # Seasonality calculation
        data['seasonality'] = self._calculate_seasonality(data['demand_quantity'])
        
        # Price and promotion factors
        data['price_factor'] = (data['price'] / data['price'].median()) if 'price' in data.columns else 1.0
        data['promotion_factor'] = data['promotion_active'].astype(float) if 'promotion_active' in data.columns else 0.0
        
        # Market sentiment (simplified)
        data['market_sentiment'] = self._calculate_market_sentiment(data)
        
        # Create feature matrix
        for i in range(7, len(data)):  # Start from index 7 to have enough lookback
            feature_row = [
                data['historical_avg'].iloc[i],
                data['trend'].iloc[i],
                data['seasonality'].iloc[i],
                data['day_of_week'].iloc[i],
                data['month'].iloc[i],
                data['quarter'].iloc[i],
                data['is_holiday'].iloc[i],
                data['price_factor'].iloc[i],
                data['promotion_factor'].iloc[i],
                data['market_sentiment'].iloc[i]
            ]
            
            features_list.append(feature_row)
            targets.append(data['demand_quantity'].iloc[i])
        
        return np.array(features_list), np.array(targets)
    
    def _identify_holidays(self, dates) -> np.ndarray:
        """Identify holidays in date range (simplified)"""
        # Simplified holiday detection
        holidays = []
        for date in dates:
            # Check for major holidays (simplified)
            if (date.month == 12 and date.day == 25) or \
               (date.month == 1 and date.day == 1) or \
               (date.month == 7 and date.day == 4):
                holidays.append(1.0)
            else:
                holidays.append(0.0)
        return np.array(holidays)
    
    def _calculate_seasonality(self, demand_series) -> pd.Series:
        """Calculate seasonality factor"""
        if len(demand_series) < 365:
            return pd.Series([1.0] * len(demand_series), index=demand_series.index)
        
        # Simple seasonal decomposition
        seasonal_avg = demand_series.groupby(demand_series.index.dayofyear).mean()
        overall_avg = demand_series.mean()
        
        seasonality = demand_series.index.map(
            lambda x: seasonal_avg.get(x.dayofyear, overall_avg) / overall_avg
        )
        
        return pd.Series(seasonality, index=demand_series.index)
    
    def _calculate_market_sentiment(self, data: pd.DataFrame) -> pd.Series:
        """Calculate market sentiment factor"""
        # Simplified sentiment based on demand volatility and external events
        sentiment = []
        
        for i, row in data.iterrows():
            base_sentiment = 1.0
            
            # Adjust based on market events
            if 'market_events' in data.columns and pd.notna(row['market_events']):
                if 'positive' in str(row['market_events']).lower():
                    base_sentiment += 0.1
                elif 'negative' in str(row['market_events']).lower():
                    base_sentiment -= 0.1
            
            sentiment.append(base_sentiment)
        
        return pd.Series(sentiment, index=data.index)
    
    async def forecast_demand(self, product_id: str, horizon_days: int = 30) -> DemandForecast:
        """Generate demand forecast for specified horizon"""
        # Ensure model is trained
        await self.train_demand_model(product_id)
        
        if product_id not in self.models:
            # Return default forecast if no model available
            return self._create_default_forecast(product_id, horizon_days)
        
        model_info = self.models[product_id]
        model = model_info['model']
        scaler = self.scalers[product_id]
        
        # Get recent data for forecasting
        recent_data = await self._get_recent_data_for_forecast(product_id)
        
        if recent_data.empty:
            return self._create_default_forecast(product_id, horizon_days)
        
        # Generate features for forecast period
        forecast_features = self._generate_forecast_features(recent_data, horizon_days)
        
        if len(forecast_features) == 0:
            return self._create_default_forecast(product_id, horizon_days)
        
        # Make predictions
        forecast_features_scaled = scaler.transform([forecast_features])
        predicted_demand = max(0, int(model.predict(forecast_features_scaled)[0]))
        
        # Calculate confidence interval
        prediction_std = np.sqrt(model_info['mse'])
        confidence_lower = max(0, predicted_demand - 1.96 * prediction_std)
        confidence_upper = predicted_demand + 1.96 * prediction_std
        
        # Determine demand pattern
        demand_pattern = self._analyze_demand_pattern(recent_data['demand_quantity'])
        
        return DemandForecast(
            product_id=product_id,
            forecast_date=datetime.now(),
            forecast_horizon_days=horizon_days,
            predicted_demand=predicted_demand,
            confidence_interval=(confidence_lower, confidence_upper),
            model_accuracy=model_info['accuracy'],
            demand_pattern=demand_pattern,
            seasonality_factor=self._get_current_seasonality_factor(product_id),
            trend_factor=self._get_current_trend_factor(product_id)
        )
    
    async def _get_recent_data_for_forecast(self, product_id: str) -> pd.DataFrame:
        """Get recent data needed for forecasting"""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT date, demand_quantity, price, promotion_active
            FROM demand_history 
            WHERE product_id = ? 
            AND date >= date('now', '-30 days')
            ORDER BY date DESC LIMIT 30
        """
        
        df = pd.read_sql_query(query, conn, params=[product_id])
        conn.close()
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        return df
    
    def _generate_forecast_features(self, recent_data: pd.DataFrame, horizon_days: int) -> List[float]:
        """Generate features for forecasting"""
        if recent_data.empty:
            return []
        
        # Calculate recent statistics
        recent_avg = recent_data['demand_quantity'].mean()
        recent_trend = np.polyfit(range(len(recent_data)), recent_data['demand_quantity'], 1)[0] if len(recent_data) > 1 else 0
        
        # Project forward
        target_date = datetime.now() + timedelta(days=horizon_days)
        
        features = [
            recent_avg,  # historical_avg
            recent_trend,  # trend
            1.0,  # seasonality (simplified)
            target_date.weekday(),  # day_of_week
            target_date.month,  # month
            (target_date.month - 1) // 3 + 1,  # quarter
            0.0,  # is_holiday (simplified)
            1.0,  # price_factor (default)
            0.0,  # promotion_factor (default)
            1.0   # market_sentiment (default)
        ]
        
        return features
    
    def _analyze_demand_pattern(self, demand_series: pd.Series) -> DemandPattern:
        """Analyze demand pattern from historical data"""
        if len(demand_series) < 7:
            return DemandPattern.STABLE
        
        # Calculate trend
        x = np.arange(len(demand_series))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, demand_series)
        
        # Calculate volatility
        cv = demand_series.std() / demand_series.mean() if demand_series.mean() > 0 else 0
        
        # Determine pattern
        if abs(slope) < 0.1 and cv < 0.2:
            return DemandPattern.STABLE
        elif slope > 0.5:
            return DemandPattern.TRENDING_UP
        elif slope < -0.5:
            return DemandPattern.TRENDING_DOWN
        elif cv > 0.5:
            return DemandPattern.VOLATILE
        else:
            return DemandPattern.STABLE
    
    def _get_current_seasonality_factor(self, product_id: str) -> float:
        """Get current seasonality factor"""
        # Simplified seasonality calculation
        current_month = datetime.now().month
        
        # Default seasonal factors by month
        seasonal_factors = {
            1: 0.9, 2: 0.8, 3: 0.9, 4: 1.0, 5: 1.1, 6: 1.2,
            7: 1.1, 8: 1.0, 9: 1.1, 10: 1.2, 11: 1.3, 12: 1.4
        }
        
        return seasonal_factors.get(current_month, 1.0)
    
    def _get_current_trend_factor(self, product_id: str) -> float:
        """Get current trend factor"""
        # Simplified trend calculation
        return 1.0  # Placeholder
    
    def _create_default_forecast(self, product_id: str, horizon_days: int) -> DemandForecast:
        """Create default forecast when no model is available"""
        return DemandForecast(
            product_id=product_id,
            forecast_date=datetime.now(),
            forecast_horizon_days=horizon_days,
            predicted_demand=10,  # Default demand
            confidence_interval=(5.0, 15.0),
            model_accuracy=0.5,  # Low accuracy for default
            demand_pattern=DemandPattern.STABLE,
            seasonality_factor=1.0,
            trend_factor=1.0
        )


class InventoryOptimizer:
    """Inventory optimization and reorder point calculation"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.service_level = 0.95  # 95% service level
    
    async def calculate_optimal_inventory_levels(self, product_id: str) -> Dict[str, int]:
        """Calculate optimal inventory levels for product"""
        # Get demand forecast
        forecaster = DemandForecaster(self.db_path)
        forecast = await forecaster.forecast_demand(product_id, 30)
        
        # Get historical demand statistics
        demand_stats = await self._get_demand_statistics(product_id)
        
        # Get lead time information
        lead_time_info = await self._get_lead_time_info(product_id)
        
        # Calculate safety stock
        safety_stock = self._calculate_safety_stock(
            demand_stats['avg_demand'],
            demand_stats['demand_std'],
            lead_time_info['avg_lead_time'],
            lead_time_info['lead_time_std']
        )
        
        # Calculate reorder point
        reorder_point = int(
            forecast.predicted_demand * (lead_time_info['avg_lead_time'] / 30) + safety_stock
        )
        
        # Calculate maximum stock level
        max_stock = self._calculate_max_stock(forecast, safety_stock)
        
        return {
            'safety_stock': safety_stock,
            'reorder_point': reorder_point,
            'maximum_stock': max_stock,
            'economic_order_quantity': self._calculate_eoq(product_id, forecast.predicted_demand)
        }
    
    async def _get_demand_statistics(self, product_id: str) -> Dict[str, float]:
        """Get demand statistics for product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(demand_quantity) as avg_demand,
                STDEV(demand_quantity) as demand_std,
                COUNT(*) as data_points
            FROM demand_history 
            WHERE product_id = ? 
            AND date >= date('now', '-90 days')
        """, (product_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'avg_demand': result[0] if result[0] else 10,
            'demand_std': result[1] if result[1] else 3,
            'data_points': result[2] if result[2] else 0
        }
    
    async def _get_lead_time_info(self, product_id: str) -> Dict[str, float]:
        """Get lead time information for product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get lead time from supplier data
        cursor.execute("""
            SELECT 
                AVG(lead_time_days) as avg_lead_time,
                STDEV(lead_time_days) as lead_time_std
            FROM supplier_lead_times 
            WHERE product_id = ?
        """, (product_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'avg_lead_time': result[0] if result[0] else 7,  # Default 7 days
            'lead_time_std': result[1] if result[1] else 2   # Default 2 days std
        }
    
    def _calculate_safety_stock(self, avg_demand: float, demand_std: float,
                              avg_lead_time: float, lead_time_std: float) -> int:
        """Calculate safety stock using statistical method"""
        # Z-score for 95% service level
        z_score = 1.645
        
        # Safety stock formula considering demand and lead time variability
        demand_component = (avg_lead_time * demand_std) ** 2
        lead_time_component = (avg_demand * lead_time_std) ** 2
        
        safety_stock = z_score * np.sqrt(demand_component + lead_time_component)
        
        return max(1, int(safety_stock))
    
    def _calculate_max_stock(self, forecast: DemandForecast, safety_stock: int) -> int:
        """Calculate maximum stock level"""
        # Maximum stock = forecast demand + safety stock + buffer
        buffer_factor = 1.2  # 20% buffer
        max_stock = (forecast.predicted_demand + safety_stock) * buffer_factor
        
        return int(max_stock)
    
    def _calculate_eoq(self, product_id: str, annual_demand: int) -> int:
        """Calculate Economic Order Quantity"""
        # Simplified EOQ calculation
        # EOQ = sqrt((2 * D * S) / H)
        # D = annual demand, S = setup cost, H = holding cost
        
        setup_cost = 100  # Default setup cost
        holding_cost_rate = 0.2  # 20% of item cost
        unit_cost = 10  # Default unit cost
        
        if annual_demand <= 0:
            return 100  # Default batch size
        
        eoq = np.sqrt((2 * annual_demand * setup_cost) / (holding_cost_rate * unit_cost))
        
        return max(10, int(eoq))


class ProductionTriggerEngine:
    """Engine for generating and managing production triggers"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.forecaster = DemandForecaster(db_path)
        self.inventory_optimizer = InventoryOptimizer(db_path)
    
    async def analyze_production_needs(self) -> List[ProductionTrigger]:
        """Analyze all products and generate production triggers"""
        triggers = []
        
        # Get all active products
        products = await self._get_active_products()
        
        for product in products:
            product_triggers = await self._analyze_product_triggers(product)
            triggers.extend(product_triggers)
        
        # Sort triggers by priority and urgency
        triggers.sort(key=lambda t: (t.priority.value, t.target_completion))
        
        return triggers
    
    async def _get_active_products(self) -> List[Product]:
        """Get all active products"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT product_id, name, category, unit_cost, setup_time, cycle_time,
                   minimum_batch_size, maximum_batch_size, shelf_life_days
            FROM products WHERE is_active = 1
        """)
        
        products = []
        for row in cursor.fetchall():
            product = Product(
                product_id=row[0],
                name=row[1],
                category=row[2],
                unit_cost=row[3],
                setup_time=row[4],
                cycle_time=row[5],
                minimum_batch_size=row[6],
                maximum_batch_size=row[7],
                shelf_life_days=row[8],
                storage_requirements={},
                components=[]
            )
            products.append(product)
        
        conn.close()
        return products
    
    async def _analyze_product_triggers(self, product: Product) -> List[ProductionTrigger]:
        """Analyze triggers for a specific product"""
        triggers = []
        
        # Get current inventory
        inventory = await self._get_current_inventory(product.product_id)
        
        # Get demand forecast
        forecast = await self.forecaster.forecast_demand(product.product_id)
        
        # Get optimal inventory levels
        optimal_levels = await self.inventory_optimizer.calculate_optimal_inventory_levels(product.product_id)
        
        # Check for various trigger conditions
        
        # 1. Low inventory trigger
        if inventory.available_stock <= optimal_levels['reorder_point']:
            triggers.append(await self._create_inventory_trigger(product, inventory, optimal_levels))
        
        # 2. Demand spike trigger
        recent_demand = await self._get_recent_demand_spike(product.product_id)
        if recent_demand > forecast.predicted_demand * 1.5:  # 50% above forecast
            triggers.append(await self._create_demand_spike_trigger(product, recent_demand, forecast))
        
        # 3. Seasonal forecast trigger
        if forecast.seasonality_factor > 1.2:  # High seasonal demand
            triggers.append(await self._create_seasonal_trigger(product, forecast))
        
        # 4. Supplier delay trigger
        supplier_delays = await self._check_supplier_delays(product.product_id)
        if supplier_delays:
            triggers.append(await self._create_supplier_delay_trigger(product, supplier_delays))
        
        # 5. Capacity optimization trigger
        available_capacity = await self._check_available_capacity()
        if available_capacity and inventory.available_stock < optimal_levels['maximum_stock']:
            triggers.append(await self._create_capacity_trigger(product, available_capacity))
        
        return triggers
    
    async def _get_current_inventory(self, product_id: str) -> InventoryLevel:
        """Get current inventory level for product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_stock, reserved_stock, safety_stock, reorder_point, 
                   maximum_stock, last_updated, location
            FROM inventory_levels 
            WHERE product_id = ?
        """, (product_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return InventoryLevel(
                product_id=product_id,
                current_stock=row[0],
                reserved_stock=row[1],
                available_stock=row[0] - row[1],
                safety_stock=row[2],
                reorder_point=row[3],
                maximum_stock=row[4],
                last_updated=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                location=row[6]
            )
        else:
            # Return default inventory if not found
            return InventoryLevel(
                product_id=product_id,
                current_stock=0,
                reserved_stock=0,
                available_stock=0,
                safety_stock=10,
                reorder_point=20,
                maximum_stock=100,
                last_updated=datetime.now(),
                location="main_warehouse"
            )
    
    async def _get_recent_demand_spike(self, product_id: str) -> int:
        """Check for recent demand spikes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SUM(demand_quantity) 
            FROM demand_history 
            WHERE product_id = ? 
            AND date >= date('now', '-7 days')
        """, (product_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result[0] else 0
    
    async def _check_supplier_delays(self, product_id: str) -> List[Dict[str, Any]]:
        """Check for supplier delays affecting the product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT supplier_id, expected_delay_days, impact_severity
            FROM supplier_delays 
            WHERE product_id = ? 
            AND is_active = 1
        """, (product_id,))
        
        delays = []
        for row in cursor.fetchall():
            delays.append({
                'supplier_id': row[0],
                'delay_days': row[1],
                'severity': row[2]
            })
        
        conn.close()
        return delays
    
    async def _check_available_capacity(self) -> Optional[ManufacturingCapacity]:
        """Check for available manufacturing capacity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT line_id, line_name, current_utilization, hourly_capacity,
                   setup_time_minutes, changeover_cost
            FROM manufacturing_lines 
            WHERE is_available = 1 
            AND current_utilization < 0.8
            ORDER BY current_utilization ASC LIMIT 1
        """, )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ManufacturingCapacity(
                line_id=row[0],
                line_name=row[1],
                is_available=True,
                current_utilization=row[2],
                hourly_capacity=row[3],
                setup_time_minutes=row[4],
                changeover_cost=row[5],
                maintenance_schedule=[],
                qualified_products=[]
            )
        
        return None
    
    async def _create_inventory_trigger(self, product: Product, inventory: InventoryLevel,
                                      optimal_levels: Dict[str, int]) -> ProductionTrigger:
        """Create inventory-based production trigger"""
        shortage = optimal_levels['reorder_point'] - inventory.available_stock
        recommended_quantity = max(shortage, optimal_levels['economic_order_quantity'])
        
        # Calculate urgency based on current stock level
        if inventory.available_stock <= inventory.safety_stock:
            priority = TriggerPriority.CRITICAL
            target_days = 1
        elif inventory.available_stock <= inventory.reorder_point * 0.5:
            priority = TriggerPriority.HIGH
            target_days = 3
        else:
            priority = TriggerPriority.MEDIUM
            target_days = 7
        
        return ProductionTrigger(
            trigger_id=f"inv_{product.product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trigger_type=TriggerType.INVENTORY_LOW,
            product_id=product.product_id,
            priority=priority,
            created_at=datetime.now(),
            trigger_reason=f"Inventory below reorder point: {inventory.available_stock} < {inventory.reorder_point}",
            recommended_quantity=recommended_quantity,
            target_completion=datetime.now() + timedelta(days=target_days),
            cost_impact=recommended_quantity * product.unit_cost,
            risk_factors=["stockout_risk", "customer_impact"] if priority == TriggerPriority.CRITICAL else ["inventory_risk"],
            automation_confidence=0.9
        )
    
    async def _create_demand_spike_trigger(self, product: Product, recent_demand: int,
                                         forecast: DemandForecast) -> ProductionTrigger:
        """Create demand spike trigger"""
        spike_magnitude = recent_demand - forecast.predicted_demand
        recommended_quantity = int(spike_magnitude * 1.5)  # 50% buffer
        
        return ProductionTrigger(
            trigger_id=f"spike_{product.product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trigger_type=TriggerType.DEMAND_SPIKE,
            product_id=product.product_id,
            priority=TriggerPriority.HIGH,
            created_at=datetime.now(),
            trigger_reason=f"Demand spike detected: {recent_demand} vs forecast {forecast.predicted_demand}",
            recommended_quantity=recommended_quantity,
            target_completion=datetime.now() + timedelta(days=2),
            cost_impact=recommended_quantity * product.unit_cost,
            risk_factors=["demand_volatility", "market_uncertainty"],
            automation_confidence=0.8
        )
    
    async def _create_seasonal_trigger(self, product: Product, forecast: DemandForecast) -> ProductionTrigger:
        """Create seasonal forecast trigger"""
        seasonal_increase = int(forecast.predicted_demand * (forecast.seasonality_factor - 1))
        
        return ProductionTrigger(
            trigger_id=f"season_{product.product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trigger_type=TriggerType.SEASONAL_FORECAST,
            product_id=product.product_id,
            priority=TriggerPriority.MEDIUM,
            created_at=datetime.now(),
            trigger_reason=f"Seasonal demand increase predicted: {forecast.seasonality_factor:.1%} above baseline",
            recommended_quantity=seasonal_increase,
            target_completion=datetime.now() + timedelta(days=14),
            cost_impact=seasonal_increase * product.unit_cost,
            risk_factors=["seasonal_risk", "forecast_uncertainty"],
            automation_confidence=0.7
        )
    
    async def _create_supplier_delay_trigger(self, product: Product, delays: List[Dict[str, Any]]) -> ProductionTrigger:
        """Create supplier delay trigger"""
        max_delay = max(delay['delay_days'] for delay in delays)
        recommended_quantity = product.minimum_batch_size * 2  # Double minimum batch
        
        return ProductionTrigger(
            trigger_id=f"delay_{product.product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trigger_type=TriggerType.SUPPLIER_DELAY,
            product_id=product.product_id,
            priority=TriggerPriority.HIGH,
            created_at=datetime.now(),
            trigger_reason=f"Supplier delays detected: up to {max_delay} days",
            recommended_quantity=recommended_quantity,
            target_completion=datetime.now() + timedelta(days=1),
            cost_impact=recommended_quantity * product.unit_cost,
            risk_factors=["supply_chain_risk", "delivery_delays"],
            automation_confidence=0.85
        )
    
    async def _create_capacity_trigger(self, product: Product, capacity: ManufacturingCapacity) -> ProductionTrigger:
        """Create capacity optimization trigger"""
        # Calculate optimal batch size based on available capacity
        available_hours = (1.0 - capacity.current_utilization) * 8  # 8-hour shift
        available_minutes = available_hours * 60 - capacity.setup_time_minutes
        
        if available_minutes > 0:
            potential_quantity = int(available_minutes / product.cycle_time)
            recommended_quantity = min(potential_quantity, product.maximum_batch_size)
        else:
            recommended_quantity = product.minimum_batch_size
        
        return ProductionTrigger(
            trigger_id=f"capacity_{product.product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            trigger_type=TriggerType.CAPACITY_AVAILABLE,
            product_id=product.product_id,
            priority=TriggerPriority.LOW,
            created_at=datetime.now(),
            trigger_reason=f"Available capacity on {capacity.line_name}: {(1-capacity.current_utilization):.1%}",
            recommended_quantity=recommended_quantity,
            target_completion=datetime.now() + timedelta(days=5),
            cost_impact=recommended_quantity * product.unit_cost,
            risk_factors=["capacity_underutilization"],
            automation_confidence=0.6
        )


class JITManufacturingTriggers:
    """Main JIT manufacturing trigger system"""
    
    def __init__(self, db_path: str = "jit_manufacturing.db"):
        self.db_path = db_path
        self.trigger_engine = ProductionTriggerEngine(db_path)
        self.forecaster = DemandForecaster(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize JIT manufacturing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                unit_cost REAL,
                setup_time INTEGER,
                cycle_time INTEGER,
                minimum_batch_size INTEGER,
                maximum_batch_size INTEGER,
                shelf_life_days INTEGER,
                is_active BOOLEAN,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Inventory levels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_levels (
                product_id TEXT PRIMARY KEY,
                current_stock INTEGER,
                reserved_stock INTEGER,
                safety_stock INTEGER,
                reorder_point INTEGER,
                maximum_stock INTEGER,
                last_updated TIMESTAMP,
                location TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Demand history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS demand_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                date DATE,
                demand_quantity INTEGER,
                price REAL,
                promotion_active BOOLEAN,
                market_events TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Production triggers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_triggers (
                trigger_id TEXT PRIMARY KEY,
                trigger_type TEXT,
                product_id TEXT,
                priority TEXT,
                created_at TIMESTAMP,
                trigger_reason TEXT,
                recommended_quantity INTEGER,
                target_completion TIMESTAMP,
                cost_impact REAL,
                risk_factors TEXT,
                automation_confidence REAL,
                status TEXT,
                approved_by TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Production orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS production_orders (
                order_id TEXT PRIMARY KEY,
                product_id TEXT,
                quantity INTEGER,
                priority TEXT,
                created_at TIMESTAMP,
                scheduled_start TIMESTAMP,
                estimated_completion TIMESTAMP,
                actual_start TIMESTAMP,
                actual_completion TIMESTAMP,
                status TEXT,
                trigger_id TEXT,
                assigned_line TEXT,
                cost_estimate REAL,
                FOREIGN KEY (product_id) REFERENCES products (product_id),
                FOREIGN KEY (trigger_id) REFERENCES production_triggers (trigger_id)
            )
        """)
        
        # Manufacturing lines table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manufacturing_lines (
                line_id TEXT PRIMARY KEY,
                line_name TEXT,
                is_available BOOLEAN,
                current_utilization REAL,
                hourly_capacity INTEGER,
                setup_time_minutes INTEGER,
                changeover_cost REAL,
                maintenance_schedule TEXT
            )
        """)
        
        # Supplier information table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_lead_times (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                supplier_id TEXT,
                lead_time_days INTEGER,
                recorded_date TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        # Supplier delays table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_delays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                supplier_id TEXT,
                expected_delay_days INTEGER,
                impact_severity TEXT,
                is_active BOOLEAN,
                reported_date TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def run_trigger_analysis(self) -> Dict[str, Any]:
        """Run complete trigger analysis cycle"""
        start_time = datetime.now()
        
        # Generate production triggers
        triggers = await self.trigger_engine.analyze_production_needs()
        
        # Store triggers in database
        stored_triggers = []
        for trigger in triggers:
            await self._store_trigger(trigger)
            stored_triggers.append(trigger)
        
        # Generate automatic production orders for high-confidence triggers
        auto_orders = []
        for trigger in triggers:
            if trigger.automation_confidence >= 0.8 and trigger.priority in [TriggerPriority.CRITICAL, TriggerPriority.HIGH]:
                order = await self._create_production_order(trigger)
                if order:
                    auto_orders.append(order)
        
        # Calculate analysis metrics
        analysis_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'analysis_timestamp': start_time,
            'analysis_duration_seconds': analysis_time,
            'total_triggers': len(triggers),
            'critical_triggers': len([t for t in triggers if t.priority == TriggerPriority.CRITICAL]),
            'high_priority_triggers': len([t for t in triggers if t.priority == TriggerPriority.HIGH]),
            'auto_generated_orders': len(auto_orders),
            'total_recommended_cost': sum(t.cost_impact for t in triggers),
            'triggers_by_type': self._categorize_triggers_by_type(triggers),
            'next_critical_deadline': self._get_next_critical_deadline(triggers)
        }
    
    async def _store_trigger(self, trigger: ProductionTrigger):
        """Store production trigger in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO production_triggers 
            (trigger_id, trigger_type, product_id, priority, created_at, trigger_reason,
             recommended_quantity, target_completion, cost_impact, risk_factors,
             automation_confidence, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trigger.trigger_id, trigger.trigger_type.value, trigger.product_id,
            trigger.priority.value, trigger.created_at, trigger.trigger_reason,
            trigger.recommended_quantity, trigger.target_completion, trigger.cost_impact,
            json.dumps(trigger.risk_factors), trigger.automation_confidence, 'pending'
        ))
        
        conn.commit()
        conn.close()
    
    async def _create_production_order(self, trigger: ProductionTrigger) -> Optional[ProductionOrder]:
        """Create production order from trigger"""
        # Check if manufacturing capacity is available
        capacity = await self.trigger_engine._check_available_capacity()
        if not capacity:
            return None
        
        order = ProductionOrder(
            order_id=f"order_{trigger.product_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            product_id=trigger.product_id,
            quantity=trigger.recommended_quantity,
            priority=trigger.priority,
            created_at=datetime.now(),
            scheduled_start=datetime.now() + timedelta(hours=2),  # 2-hour lead time
            estimated_completion=trigger.target_completion,
            actual_start=None,
            actual_completion=None,
            status=ProductionStatus.SCHEDULED,
            trigger_id=trigger.trigger_id,
            assigned_line=capacity.line_id,
            cost_estimate=trigger.cost_impact
        )
        
        # Store order in database
        await self._store_production_order(order)
        
        return order
    
    async def _store_production_order(self, order: ProductionOrder):
        """Store production order in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO production_orders 
            (order_id, product_id, quantity, priority, created_at, scheduled_start,
             estimated_completion, status, trigger_id, assigned_line, cost_estimate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order.order_id, order.product_id, order.quantity, order.priority.value,
            order.created_at, order.scheduled_start, order.estimated_completion,
            order.status.value, order.trigger_id, order.assigned_line, order.cost_estimate
        ))
        
        conn.commit()
        conn.close()
    
    def _categorize_triggers_by_type(self, triggers: List[ProductionTrigger]) -> Dict[str, int]:
        """Categorize triggers by type"""
        categories = {}
        for trigger in triggers:
            trigger_type = trigger.trigger_type.value
            categories[trigger_type] = categories.get(trigger_type, 0) + 1
        return categories
    
    def _get_next_critical_deadline(self, triggers: List[ProductionTrigger]) -> Optional[datetime]:
        """Get next critical deadline"""
        critical_triggers = [t for t in triggers if t.priority == TriggerPriority.CRITICAL]
        if critical_triggers:
            return min(t.target_completion for t in critical_triggers)
        return None
    
    async def get_trigger_dashboard(self) -> Dict[str, Any]:
        """Get trigger dashboard with current status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active triggers
        cursor.execute("""
            SELECT trigger_type, priority, COUNT(*) as count
            FROM production_triggers 
            WHERE status = 'pending'
            GROUP BY trigger_type, priority
        """)
        
        active_triggers = cursor.fetchall()
        
        # Get recent orders
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM production_orders 
            WHERE created_at > date('now', '-7 days')
            GROUP BY status
        """)
        
        recent_orders = cursor.fetchall()
        
        # Get capacity utilization
        cursor.execute("""
            SELECT AVG(current_utilization) as avg_utilization
            FROM manufacturing_lines 
            WHERE is_available = 1
        """)
        
        capacity_result = cursor.fetchone()
        conn.close()
        
        return {
            'dashboard_timestamp': datetime.now(),
            'active_triggers': [
                {'type': row[0], 'priority': row[1], 'count': row[2]}
                for row in active_triggers
            ],
            'recent_orders': [
                {'status': row[0], 'count': row[1]}
                for row in recent_orders
            ],
            'average_capacity_utilization': capacity_result[0] if capacity_result[0] else 0.0,
            'system_status': 'operational'
        }


async def main():
    """Example usage of JIT Manufacturing Triggers"""
    jit_system = JITManufacturingTriggers()
    
    # Add sample data (normally this would come from existing systems)
    conn = sqlite3.connect(jit_system.db_path)
    cursor = conn.cursor()
    
    # Add sample product
    cursor.execute("""
        INSERT OR REPLACE INTO products 
        (product_id, name, category, unit_cost, setup_time, cycle_time,
         minimum_batch_size, maximum_batch_size, shelf_life_days, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("PROD001", "Widget A", "Electronics", 25.50, 30, 5, 50, 500, 365, True))
    
    # Add sample inventory
    cursor.execute("""
        INSERT OR REPLACE INTO inventory_levels 
        (product_id, current_stock, reserved_stock, safety_stock, reorder_point,
         maximum_stock, last_updated, location)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("PROD001", 15, 5, 20, 50, 200, datetime.now(), "main_warehouse"))
    
    # Add sample manufacturing line
    cursor.execute("""
        INSERT OR REPLACE INTO manufacturing_lines 
        (line_id, line_name, is_available, current_utilization, hourly_capacity,
         setup_time_minutes, changeover_cost)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("LINE001", "Assembly Line 1", True, 0.6, 12, 30, 500.0))
    
    # Add sample demand history
    for i in range(30):
        date = datetime.now() - timedelta(days=i)
        demand = np.random.poisson(15)  # Average demand of 15 units
        cursor.execute("""
            INSERT OR REPLACE INTO demand_history 
            (product_id, date, demand_quantity, price, promotion_active)
            VALUES (?, ?, ?, ?, ?)
        """, ("PROD001", date.date(), demand, 30.0, False))
    
    conn.commit()
    conn.close()
    
    print("Running JIT Manufacturing Trigger Analysis...")
    
    # Run trigger analysis
    results = await jit_system.run_trigger_analysis()
    
    print(f"\nAnalysis Results:")
    print(f"Analysis Duration: {results['analysis_duration_seconds']:.2f} seconds")
    print(f"Total Triggers: {results['total_triggers']}")
    print(f"Critical Triggers: {results['critical_triggers']}")
    print(f"High Priority Triggers: {results['high_priority_triggers']}")
    print(f"Auto-Generated Orders: {results['auto_generated_orders']}")
    print(f"Total Recommended Cost: ${results['total_recommended_cost']:,.2f}")
    
    print(f"\nTriggers by Type:")
    for trigger_type, count in results['triggers_by_type'].items():
        print(f"  {trigger_type.replace('_', ' ').title()}: {count}")
    
    if results['next_critical_deadline']:
        print(f"\nNext Critical Deadline: {results['next_critical_deadline']}")
    
    # Get dashboard
    dashboard = await jit_system.get_trigger_dashboard()
    print(f"\nDashboard Status:")
    print(f"Average Capacity Utilization: {dashboard['average_capacity_utilization']:.1%}")
    print(f"System Status: {dashboard['system_status']}")


if __name__ == "__main__":
    asyncio.run(main())