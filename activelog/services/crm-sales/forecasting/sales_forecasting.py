"""
Sales Forecasting System
Predictive sales analytics, forecasting models, and revenue projections
"""

import sqlite3
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
import statistics
import math
from collections import defaultdict


class ForecastModel(Enum):
    """Forecasting model types"""
    LINEAR_TREND = "linear_trend"
    SEASONAL = "seasonal"
    WEIGHTED_PIPELINE = "weighted_pipeline"
    HISTORICAL_AVERAGE = "historical_average"
    REGRESSION = "regression"
    PIPELINE_VELOCITY = "pipeline_velocity"


class ForecastPeriod(Enum):
    """Forecast time periods"""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"


class ConfidenceLevel(Enum):
    """Forecast confidence levels"""
    LOW = 0.68  # 68% confidence (1 sigma)
    MEDIUM = 0.90  # 90% confidence
    HIGH = 0.95  # 95% confidence (2 sigma)


@dataclass
class ForecastResult:
    """Forecast result data structure"""
    forecast_id: str
    model_type: ForecastModel
    period: str
    forecast_value: float
    confidence_level: float
    lower_bound: float
    upper_bound: float
    accuracy_score: Optional[float]
    generated_at: datetime


class SalesForecastingSystem:
    """Sales forecasting and predictive analytics system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def generate_forecast(self, model_type: str, forecast_periods: int = 4,
                         period_type: str = "monthly", user_id: Optional[str] = None,
                         territory_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate sales forecast using specified model"""
        
        forecast_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get historical data
            historical_data = self._get_historical_data(
                cursor, period_type, user_id, territory_id
            )
            
            if len(historical_data) < 3:
                return {
                    'forecast_id': forecast_id,
                    'error': 'Insufficient historical data for forecasting',
                    'min_periods_required': 3
                }
            
            # Generate forecast based on model type
            if model_type == ForecastModel.LINEAR_TREND.value:
                forecast_results = self._linear_trend_forecast(
                    historical_data, forecast_periods
                )
            elif model_type == ForecastModel.SEASONAL.value:
                forecast_results = self._seasonal_forecast(
                    historical_data, forecast_periods, period_type
                )
            elif model_type == ForecastModel.WEIGHTED_PIPELINE.value:
                forecast_results = self._weighted_pipeline_forecast(
                    cursor, forecast_periods, user_id, territory_id
                )
            elif model_type == ForecastModel.HISTORICAL_AVERAGE.value:
                forecast_results = self._historical_average_forecast(
                    historical_data, forecast_periods
                )
            elif model_type == ForecastModel.PIPELINE_VELOCITY.value:
                forecast_results = self._pipeline_velocity_forecast(
                    cursor, forecast_periods, user_id, territory_id
                )
            else:
                forecast_results = self._linear_trend_forecast(
                    historical_data, forecast_periods
                )
            
            # Save forecast to database
            self._save_forecast_results(cursor, forecast_id, model_type, forecast_results, {
                'user_id': user_id,
                'territory_id': territory_id,
                'period_type': period_type
            })
            
            conn.commit()
            
            return {
                'forecast_id': forecast_id,
                'model_type': model_type,
                'period_type': period_type,
                'forecast_periods': forecast_periods,
                'historical_periods': len(historical_data),
                'forecasts': forecast_results,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_pipeline_forecast(self, confidence_level: float = 0.90) -> Dict[str, Any]:
        """Get forecast based on current pipeline"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current pipeline by stage
            cursor.execute("""
                SELECT 
                    ps.name as stage_name,
                    ps.probability,
                    COUNT(o.opportunity_id) as opportunity_count,
                    SUM(o.value) as total_value,
                    AVG(o.value) as avg_value,
                    AVG(JULIANDAY('now') - JULIANDAY(o.created_at)) as avg_age_days
                FROM opportunities o
                JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
                WHERE o.status = 'open'
                GROUP BY ps.stage_id, ps.name, ps.probability
                ORDER BY ps.stage_order
            """)
            
            pipeline_stages = cursor.fetchall()
            
            # Calculate weighted pipeline value
            total_weighted_value = 0
            stage_forecasts = []
            
            for stage in pipeline_stages:
                weighted_value = stage['total_value'] * (stage['probability'] / 100)
                total_weighted_value += weighted_value
                
                # Calculate confidence intervals based on stage probability
                stage_confidence = stage['probability'] / 100 * confidence_level
                lower_bound = weighted_value * (1 - (1 - stage_confidence) / 2)
                upper_bound = weighted_value * (1 + (1 - stage_confidence) / 2)
                
                stage_forecasts.append({
                    'stage_name': stage['stage_name'],
                    'opportunity_count': stage['opportunity_count'],
                    'total_value': stage['total_value'],
                    'probability': stage['probability'],
                    'weighted_value': weighted_value,
                    'confidence_level': stage_confidence * 100,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'avg_age_days': stage['avg_age_days']
                })
            
            # Get historical conversion rates for better accuracy
            conversion_rates = self._get_historical_conversion_rates(cursor)
            adjusted_forecast = total_weighted_value
            
            if conversion_rates:
                avg_conversion_rate = statistics.mean(conversion_rates.values())
                adjusted_forecast = total_weighted_value * avg_conversion_rate
            
            return {
                'total_pipeline_value': sum(stage['total_value'] for stage in pipeline_stages),
                'weighted_pipeline_value': total_weighted_value,
                'adjusted_forecast': adjusted_forecast,
                'confidence_level': confidence_level * 100,
                'stage_forecasts': stage_forecasts,
                'conversion_rates': conversion_rates,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_revenue_projection(self, projection_months: int = 12,
                             scenarios: List[str] = None) -> Dict[str, Any]:
        """Generate revenue projections with multiple scenarios"""
        
        if scenarios is None:
            scenarios = ['conservative', 'realistic', 'optimistic']
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get historical monthly revenue
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', o.updated_at) as month,
                    SUM(o.value) as revenue
                FROM opportunities o
                WHERE o.status = 'won' 
                AND o.updated_at >= DATE('now', '-24 months')
                GROUP BY strftime('%Y-%m', o.updated_at)
                ORDER BY month
            """)
            
            historical_revenue = []
            for result in cursor.fetchall():
                historical_revenue.append({
                    'month': result['month'],
                    'revenue': result['revenue']
                })
            
            if len(historical_revenue) < 6:
                return {
                    'error': 'Insufficient historical data for revenue projection',
                    'min_months_required': 6
                }
            
            # Calculate scenario multipliers
            scenario_multipliers = {
                'conservative': 0.8,
                'realistic': 1.0,
                'optimistic': 1.3
            }
            
            # Generate base projection using linear trend
            revenue_values = [r['revenue'] for r in historical_revenue[-12:]]
            base_trend = self._calculate_trend(revenue_values)
            
            projections = {}
            
            for scenario in scenarios:
                multiplier = scenario_multipliers.get(scenario, 1.0)
                scenario_projections = []
                
                for month in range(1, projection_months + 1):
                    # Calculate projected revenue with trend and seasonality
                    base_projection = revenue_values[-1] + (base_trend * month)
                    
                    # Apply seasonality if we have enough data
                    if len(historical_revenue) >= 12:
                        seasonal_factor = self._calculate_seasonal_factor(
                            historical_revenue, month
                        )
                        base_projection *= seasonal_factor
                    
                    # Apply scenario multiplier
                    projected_revenue = base_projection * multiplier
                    
                    # Calculate confidence intervals
                    std_dev = statistics.stdev(revenue_values) if len(revenue_values) > 1 else 0
                    lower_bound = projected_revenue - (1.96 * std_dev)  # 95% CI
                    upper_bound = projected_revenue + (1.96 * std_dev)
                    
                    scenario_projections.append({
                        'month': month,
                        'projected_revenue': max(0, projected_revenue),
                        'lower_bound': max(0, lower_bound),
                        'upper_bound': upper_bound
                    })
                
                projections[scenario] = {
                    'total_projected_revenue': sum(p['projected_revenue'] for p in scenario_projections),
                    'monthly_projections': scenario_projections
                }
            
            return {
                'projection_months': projection_months,
                'historical_months': len(historical_revenue),
                'base_trend': base_trend,
                'scenarios': projections,
                'historical_revenue': historical_revenue[-6:],  # Last 6 months
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def analyze_forecast_accuracy(self, forecast_id: str) -> Dict[str, Any]:
        """Analyze the accuracy of a previous forecast"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get forecast details
            cursor.execute("""
                SELECT * FROM sales_forecasts 
                WHERE forecast_id = ?
            """, [forecast_id])
            
            forecast = cursor.fetchone()
            if not forecast:
                raise ValueError("Forecast not found")
            
            forecast_data = json.loads(forecast['forecast_data'])
            forecast_date = datetime.fromisoformat(forecast['created_at'])
            
            # Get actual results for comparison
            actual_results = self._get_actual_results_for_forecast(
                cursor, forecast_date, forecast_data
            )
            
            if not actual_results:
                return {
                    'forecast_id': forecast_id,
                    'status': 'insufficient_actual_data',
                    'message': 'Not enough actual data available for accuracy analysis'
                }
            
            # Calculate accuracy metrics
            accuracy_metrics = self._calculate_accuracy_metrics(
                forecast_data['forecasts'], actual_results
            )
            
            # Update forecast record with accuracy
            cursor.execute("""
                UPDATE sales_forecasts 
                SET accuracy_score = ?, updated_at = ?
                WHERE forecast_id = ?
            """, [
                accuracy_metrics['mean_absolute_percentage_error'],
                datetime.utcnow().isoformat(),
                forecast_id
            ])
            
            conn.commit()
            
            return {
                'forecast_id': forecast_id,
                'forecast_model': forecast['model_type'],
                'forecast_date': forecast['created_at'],
                'accuracy_metrics': accuracy_metrics,
                'forecast_vs_actual': self._compare_forecast_vs_actual(
                    forecast_data['forecasts'], actual_results
                )
            }
    
    def get_forecast_comparison(self, models: List[str] = None,
                              period_type: str = "monthly") -> Dict[str, Any]:
        """Compare different forecasting models"""
        
        if models is None:
            models = [
                ForecastModel.LINEAR_TREND.value,
                ForecastModel.SEASONAL.value,
                ForecastModel.WEIGHTED_PIPELINE.value,
                ForecastModel.HISTORICAL_AVERAGE.value
            ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            historical_data = self._get_historical_data(cursor, period_type)
            
            if len(historical_data) < 6:
                return {
                    'error': 'Insufficient data for model comparison',
                    'min_periods_required': 6
                }
            
            # Use 80% of data for training, 20% for testing
            train_size = int(len(historical_data) * 0.8)
            train_data = historical_data[:train_size]
            test_data = historical_data[train_size:]
            
            model_comparisons = []
            
            for model in models:
                try:
                    # Generate forecast using training data
                    if model == ForecastModel.LINEAR_TREND.value:
                        forecasts = self._linear_trend_forecast(train_data, len(test_data))
                    elif model == ForecastModel.SEASONAL.value:
                        forecasts = self._seasonal_forecast(train_data, len(test_data), period_type)
                    elif model == ForecastModel.HISTORICAL_AVERAGE.value:
                        forecasts = self._historical_average_forecast(train_data, len(test_data))
                    else:
                        continue  # Skip models that need current pipeline data
                    
                    # Calculate accuracy against test data
                    actual_values = [period['value'] for period in test_data]
                    forecast_values = [f['forecast_value'] for f in forecasts]
                    
                    accuracy_metrics = self._calculate_accuracy_metrics_simple(
                        forecast_values, actual_values
                    )
                    
                    model_comparisons.append({
                        'model': model,
                        'accuracy_metrics': accuracy_metrics,
                        'test_periods': len(test_data),
                        'avg_forecast_value': statistics.mean(forecast_values),
                        'avg_actual_value': statistics.mean(actual_values)
                    })
                    
                except Exception as e:
                    model_comparisons.append({
                        'model': model,
                        'error': str(e)
                    })
            
            # Rank models by accuracy (lower MAPE is better)
            valid_models = [m for m in model_comparisons if 'error' not in m]
            valid_models.sort(key=lambda x: x['accuracy_metrics']['mape'])
            
            return {
                'comparison_method': f'{train_size}/{len(test_data)} train/test split',
                'period_type': period_type,
                'model_rankings': valid_models,
                'best_model': valid_models[0]['model'] if valid_models else None,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_sales_forecast_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive sales forecast dashboard"""
        
        # Generate multiple forecasts
        pipeline_forecast = self.get_pipeline_forecast()
        revenue_projection = self.get_revenue_projection(6)
        
        # Get recent forecasts
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM sales_forecasts 
                ORDER BY created_at DESC 
                LIMIT 5
            """)
            
            recent_forecasts = []
            for result in cursor.fetchall():
                forecast_data = json.loads(result['forecast_data'])
                recent_forecasts.append({
                    'forecast_id': result['forecast_id'],
                    'model_type': result['model_type'],
                    'created_at': result['created_at'],
                    'accuracy_score': result['accuracy_score'],
                    'total_forecast_value': sum(
                        f.get('forecast_value', 0) for f in forecast_data.get('forecasts', [])
                    )
                })
        
        return {
            'pipeline_forecast': pipeline_forecast,
            'revenue_projection': revenue_projection,
            'recent_forecasts': recent_forecasts,
            'dashboard_generated_at': datetime.utcnow().isoformat()
        }
    
    def _get_historical_data(self, cursor, period_type: str, user_id: Optional[str] = None,
                           territory_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get historical sales data for forecasting"""
        
        # Determine date format and lookback period
        if period_type == "weekly":
            date_format = "%Y-%W"
            lookback_months = 12
        elif period_type == "quarterly":
            date_format = "%Y-%m"  # We'll group by quarters manually
            lookback_months = 24
        else:  # monthly
            date_format = "%Y-%m"
            lookback_months = 18
        
        # Build query
        query = f"""
            SELECT 
                strftime('{date_format}', o.updated_at) as period,
                SUM(o.value) as value,
                COUNT(o.opportunity_id) as deal_count,
                AVG(o.value) as avg_deal_size
            FROM opportunities o
        """
        
        where_conditions = ["o.status = 'won'", f"o.updated_at >= DATE('now', '-{lookback_months} months')"]
        params = []
        
        if user_id:
            where_conditions.append("o.assigned_to = ?")
            params.append(user_id)
            
        if territory_id:
            query += " JOIN contacts c ON o.contact_id = c.contact_id"
            where_conditions.append("c.territory_id = ?")
            params.append(territory_id)
        
        query += f" WHERE {' AND '.join(where_conditions)}"
        query += f" GROUP BY strftime('{date_format}', o.updated_at)"
        query += " ORDER BY period"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        historical_data = []
        for result in results:
            historical_data.append({
                'period': result['period'],
                'value': result['value'],
                'deal_count': result['deal_count'],
                'avg_deal_size': result['avg_deal_size']
            })
        
        return historical_data
    
    def _linear_trend_forecast(self, historical_data: List[Dict[str, Any]], 
                             forecast_periods: int) -> List[Dict[str, Any]]:
        """Generate linear trend forecast"""
        
        values = [period['value'] for period in historical_data]
        n = len(values)
        
        # Calculate linear trend using least squares
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        intercept = y_mean - slope * x_mean
        
        # Generate forecasts
        forecasts = []
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        for period in range(forecast_periods):
            x_forecast = n + period
            forecast_value = intercept + slope * x_forecast
            
            # Calculate confidence intervals (95%)
            lower_bound = forecast_value - (1.96 * std_dev)
            upper_bound = forecast_value + (1.96 * std_dev)
            
            forecasts.append({
                'period': period + 1,
                'forecast_value': max(0, forecast_value),
                'lower_bound': max(0, lower_bound),
                'upper_bound': upper_bound,
                'confidence_level': 95
            })
        
        return forecasts
    
    def _seasonal_forecast(self, historical_data: List[Dict[str, Any]], 
                          forecast_periods: int, period_type: str) -> List[Dict[str, Any]]:
        """Generate seasonal forecast"""
        
        values = [period['value'] for period in historical_data]
        
        # Determine seasonality cycle
        if period_type == "monthly":
            cycle_length = 12
        elif period_type == "quarterly":
            cycle_length = 4
        else:
            cycle_length = 52  # weekly
        
        # Calculate seasonal indices if we have enough data
        if len(values) < cycle_length:
            # Fall back to linear trend if not enough data for seasonality
            return self._linear_trend_forecast(historical_data, forecast_periods)
        
        # Calculate trend
        trend = self._calculate_trend(values)
        
        # Calculate seasonal indices
        seasonal_indices = self._calculate_seasonal_indices(values, cycle_length)
        
        # Generate forecasts
        forecasts = []
        last_value = values[-1]
        
        for period in range(forecast_periods):
            # Apply trend
            trended_value = last_value + (trend * (period + 1))
            
            # Apply seasonality
            seasonal_index = seasonal_indices[period % len(seasonal_indices)]
            forecast_value = trended_value * seasonal_index
            
            # Calculate confidence intervals
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            lower_bound = forecast_value - (1.96 * std_dev)
            upper_bound = forecast_value + (1.96 * std_dev)
            
            forecasts.append({
                'period': period + 1,
                'forecast_value': max(0, forecast_value),
                'lower_bound': max(0, lower_bound),
                'upper_bound': upper_bound,
                'confidence_level': 95,
                'seasonal_index': seasonal_index
            })
        
        return forecasts
    
    def _weighted_pipeline_forecast(self, cursor, forecast_periods: int,
                                  user_id: Optional[str] = None,
                                  territory_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate weighted pipeline forecast"""
        
        # Get current pipeline
        query = """
            SELECT 
                SUM(o.value * ps.probability / 100) as weighted_value,
                COUNT(o.opportunity_id) as opportunity_count
            FROM opportunities o
            JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
            WHERE o.status = 'open'
        """
        
        params = []
        
        if user_id:
            query += " AND o.assigned_to = ?"
            params.append(user_id)
            
        if territory_id:
            query += " AND o.contact_id IN (SELECT contact_id FROM contacts WHERE territory_id = ?)"
            params.append(territory_id)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        weighted_pipeline = result['weighted_value'] or 0
        
        # Get average sales cycle
        cycle_query = """
            SELECT AVG(JULIANDAY(updated_at) - JULIANDAY(created_at)) as avg_cycle_days
            FROM opportunities
            WHERE status = 'won'
        """
        
        cursor.execute(cycle_query)
        cycle_result = cursor.fetchone()
        avg_cycle_days = cycle_result['avg_cycle_days'] or 30
        
        # Distribute pipeline over forecast periods based on sales cycle
        forecasts = []
        
        # Simple distribution: assume pipeline converts over average sales cycle
        months_to_convert = max(1, avg_cycle_days / 30)  # Convert days to months
        
        for period in range(forecast_periods):
            # Decay factor based on time and conversion probability
            decay_factor = math.exp(-period / months_to_convert)
            period_forecast = weighted_pipeline * decay_factor / forecast_periods
            
            forecasts.append({
                'period': period + 1,
                'forecast_value': period_forecast,
                'lower_bound': period_forecast * 0.7,
                'upper_bound': period_forecast * 1.3,
                'confidence_level': 80
            })
        
        return forecasts
    
    def _historical_average_forecast(self, historical_data: List[Dict[str, Any]], 
                                   forecast_periods: int) -> List[Dict[str, Any]]:
        """Generate historical average forecast"""
        
        values = [period['value'] for period in historical_data]
        
        # Use different averaging methods
        recent_avg = statistics.mean(values[-6:]) if len(values) >= 6 else statistics.mean(values)
        overall_avg = statistics.mean(values)
        
        # Weight recent data more heavily
        weighted_avg = (recent_avg * 0.7) + (overall_avg * 0.3)
        
        forecasts = []
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        for period in range(forecast_periods):
            forecasts.append({
                'period': period + 1,
                'forecast_value': weighted_avg,
                'lower_bound': max(0, weighted_avg - (1.96 * std_dev)),
                'upper_bound': weighted_avg + (1.96 * std_dev),
                'confidence_level': 95
            })
        
        return forecasts
    
    def _pipeline_velocity_forecast(self, cursor, forecast_periods: int,
                                  user_id: Optional[str] = None,
                                  territory_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate pipeline velocity-based forecast"""
        
        # Calculate sales velocity: (Number of deals × Average deal size × Win rate) / Sales cycle length
        velocity_query = """
            SELECT 
                COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_deals,
                COUNT(o.opportunity_id) as total_deals,
                AVG(CASE WHEN o.status = 'won' THEN o.value END) as avg_deal_size,
                AVG(CASE WHEN o.status = 'won' 
                    THEN JULIANDAY(o.updated_at) - JULIANDAY(o.created_at)
                END) as avg_cycle_days
            FROM opportunities o
            WHERE o.created_at >= DATE('now', '-6 months')
        """
        
        params = []
        
        if user_id:
            velocity_query += " AND o.assigned_to = ?"
            params.append(user_id)
            
        if territory_id:
            velocity_query += " AND o.contact_id IN (SELECT contact_id FROM contacts WHERE territory_id = ?)"
            params.append(territory_id)
        
        cursor.execute(velocity_query, params)
        result = cursor.fetchone()
        
        won_deals = result['won_deals'] or 0
        total_deals = result['total_deals'] or 1
        avg_deal_size = result['avg_deal_size'] or 0
        avg_cycle_days = result['avg_cycle_days'] or 30
        
        win_rate = won_deals / total_deals if total_deals > 0 else 0
        velocity = (won_deals * avg_deal_size * win_rate) / max(avg_cycle_days, 1)
        
        # Project velocity forward
        forecasts = []
        monthly_velocity = velocity * 30  # Convert daily velocity to monthly
        
        for period in range(forecast_periods):
            forecast_value = monthly_velocity
            
            # Add some variance based on historical performance
            variance = forecast_value * 0.2  # 20% variance
            
            forecasts.append({
                'period': period + 1,
                'forecast_value': forecast_value,
                'lower_bound': max(0, forecast_value - variance),
                'upper_bound': forecast_value + variance,
                'confidence_level': 85,
                'velocity_components': {
                    'deals_per_month': won_deals / 6,  # Assuming 6 months of data
                    'avg_deal_size': avg_deal_size,
                    'win_rate': win_rate,
                    'avg_cycle_days': avg_cycle_days
                }
            })
        
        return forecasts
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate linear trend from values"""
        
        if len(values) < 2:
            return 0
        
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0
    
    def _calculate_seasonal_indices(self, values: List[float], cycle_length: int) -> List[float]:
        """Calculate seasonal indices"""
        
        # Group values by season
        seasonal_sums = defaultdict(list)
        
        for i, value in enumerate(values):
            season = i % cycle_length
            seasonal_sums[season].append(value)
        
        # Calculate seasonal indices
        overall_mean = statistics.mean(values)
        seasonal_indices = []
        
        for season in range(cycle_length):
            if seasonal_sums[season]:
                seasonal_mean = statistics.mean(seasonal_sums[season])
                index = seasonal_mean / overall_mean if overall_mean > 0 else 1
            else:
                index = 1
            
            seasonal_indices.append(index)
        
        return seasonal_indices
    
    def _calculate_seasonal_factor(self, historical_data: List[Dict[str, Any]], month: int) -> float:
        """Calculate seasonal adjustment factor for a given month"""
        
        # Simple seasonality calculation
        month_values = []
        all_values = []
        
        for period in historical_data:
            all_values.append(period['value'])
            # Extract month from period string (assuming YYYY-MM format)
            try:
                period_month = int(period['period'].split('-')[1])
                if period_month == ((month - 1) % 12) + 1:
                    month_values.append(period['value'])
            except:
                continue
        
        if month_values and all_values:
            month_avg = statistics.mean(month_values)
            overall_avg = statistics.mean(all_values)
            return month_avg / overall_avg if overall_avg > 0 else 1
        
        return 1  # No seasonal adjustment if insufficient data
    
    def _get_historical_conversion_rates(self, cursor) -> Dict[str, float]:
        """Get historical conversion rates by stage"""
        
        cursor.execute("""
            SELECT 
                ps.name,
                COUNT(CASE WHEN o.status = 'won' THEN 1 END) as won_count,
                COUNT(o.opportunity_id) as total_count
            FROM opportunities o
            JOIN pipeline_stages ps ON o.stage_id = ps.stage_id
            WHERE o.created_at >= DATE('now', '-12 months')
            GROUP BY ps.stage_id, ps.name
        """)
        
        conversion_rates = {}
        for result in cursor.fetchall():
            if result['total_count'] > 0:
                conversion_rates[result['name']] = result['won_count'] / result['total_count']
        
        return conversion_rates
    
    def _save_forecast_results(self, cursor, forecast_id: str, model_type: str,
                             forecast_results: List[Dict[str, Any]], metadata: Dict[str, Any]):
        """Save forecast results to database"""
        
        cursor.execute("""
            INSERT INTO sales_forecasts (
                forecast_id, model_type, forecast_data, metadata,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            forecast_id,
            model_type,
            json.dumps({
                'forecasts': forecast_results,
                'total_forecast_value': sum(f.get('forecast_value', 0) for f in forecast_results)
            }),
            json.dumps(metadata),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ])
    
    def _get_actual_results_for_forecast(self, cursor, forecast_date: datetime,
                                       forecast_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get actual results for comparison with forecast"""
        
        # This is a simplified implementation
        # In practice, you'd need more sophisticated logic to map forecast periods to actual results
        
        end_date = forecast_date + timedelta(days=len(forecast_data.get('forecasts', [])) * 30)
        
        cursor.execute("""
            SELECT 
                strftime('%Y-%m', updated_at) as period,
                SUM(value) as actual_value
            FROM opportunities
            WHERE status = 'won' 
            AND updated_at BETWEEN ? AND ?
            GROUP BY strftime('%Y-%m', updated_at)
            ORDER BY period
        """, [forecast_date.isoformat(), end_date.isoformat()])
        
        return [{'period': r['period'], 'actual_value': r['actual_value']} 
                for r in cursor.fetchall()]
    
    def _calculate_accuracy_metrics(self, forecasts: List[Dict[str, Any]], 
                                  actual_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate forecast accuracy metrics"""
        
        if len(forecasts) != len(actual_results):
            return {'error': 'Mismatched forecast and actual data lengths'}
        
        forecast_values = [f['forecast_value'] for f in forecasts]
        actual_values = [a['actual_value'] for a in actual_results]
        
        return self._calculate_accuracy_metrics_simple(forecast_values, actual_values)
    
    def _calculate_accuracy_metrics_simple(self, forecast_values: List[float], 
                                         actual_values: List[float]) -> Dict[str, Any]:
        """Calculate accuracy metrics for two value lists"""
        
        if len(forecast_values) != len(actual_values) or len(forecast_values) == 0:
            return {'error': 'Invalid data for accuracy calculation'}
        
        # Mean Absolute Error (MAE)
        mae = statistics.mean(abs(f - a) for f, a in zip(forecast_values, actual_values))
        
        # Mean Squared Error (MSE)
        mse = statistics.mean((f - a) ** 2 for f, a in zip(forecast_values, actual_values))
        
        # Root Mean Squared Error (RMSE)
        rmse = math.sqrt(mse)
        
        # Mean Absolute Percentage Error (MAPE)
        mape_values = []
        for f, a in zip(forecast_values, actual_values):
            if a != 0:
                mape_values.append(abs((a - f) / a) * 100)
        
        mape = statistics.mean(mape_values) if mape_values else 0
        
        return {
            'mean_absolute_error': mae,
            'mean_squared_error': mse,
            'root_mean_squared_error': rmse,
            'mean_absolute_percentage_error': mape,
            'data_points': len(forecast_values)
        }
    
    def _compare_forecast_vs_actual(self, forecasts: List[Dict[str, Any]], 
                                  actual_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compare forecast vs actual values"""
        
        comparisons = []
        
        min_length = min(len(forecasts), len(actual_results))
        
        for i in range(min_length):
            forecast_value = forecasts[i]['forecast_value']
            actual_value = actual_results[i]['actual_value']
            
            comparisons.append({
                'period': i + 1,
                'forecast_value': forecast_value,
                'actual_value': actual_value,
                'difference': actual_value - forecast_value,
                'percentage_difference': ((actual_value - forecast_value) / forecast_value * 100) 
                                       if forecast_value != 0 else 0
            })
        
        return comparisons