import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class LTVMetrics:
    customer_id: str
    ltv_prediction: float
    ltv_actual: Optional[float]
    months_active: int
    monthly_revenue: float
    churn_probability: float
    segment: str
    confidence_score: float

class LTVCalculator:
    def __init__(self):
        self.ltv_cache = {}
        self.segment_models = {
            'high_value': {'monthly_multiplier': 12, 'churn_discount': 0.85},
            'standard': {'monthly_multiplier': 8, 'churn_discount': 0.75},
            'low_value': {'monthly_multiplier': 6, 'churn_discount': 0.65}
        }
    
    async def calculate_customer_ltv(self, customer_id: str, method: str = "predictive") -> Dict:
        """Calculate Customer Lifetime Value using specified method"""
        try:
            customer_data = await self._get_customer_data(customer_id)
            if not customer_data:
                return {'success': False, 'error': 'Customer not found'}
            
            if method == "predictive":
                ltv_result = await self._calculate_predictive_ltv(customer_data)
            elif method == "historical":
                ltv_result = await self._calculate_historical_ltv(customer_data)
            elif method == "cohort":
                ltv_result = await self._calculate_cohort_ltv(customer_data)
            else:
                return {'success': False, 'error': 'Invalid calculation method'}
            
            # Store in cache
            self.ltv_cache[customer_id] = ltv_result
            
            return {
                'success': True,
                'customer_id': customer_id,
                'ltv_metrics': ltv_result.__dict__,
                'calculation_method': method,
                'calculated_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error calculating LTV for customer {customer_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def calculate_cohort_ltv(self, cohort_id: str) -> Dict:
        """Calculate average LTV for a customer cohort"""
        try:
            cohort_customers = await self._get_cohort_customers(cohort_id)
            
            ltv_values = []
            cohort_metrics = {
                'total_customers': len(cohort_customers),
                'active_customers': 0,
                'churned_customers': 0,
                'total_revenue': 0.0,
                'average_months_active': 0.0,
                'segments': {'high_value': 0, 'standard': 0, 'low_value': 0}
            }
            
            for customer in cohort_customers:
                customer_ltv = await self.calculate_customer_ltv(customer['id'], 'predictive')
                
                if customer_ltv['success']:
                    ltv_metrics = customer_ltv['ltv_metrics']
                    ltv_values.append(ltv_metrics['ltv_prediction'])
                    
                    # Update cohort metrics
                    cohort_metrics['total_revenue'] += ltv_metrics['monthly_revenue'] * ltv_metrics['months_active']
                    cohort_metrics['average_months_active'] += ltv_metrics['months_active']
                    cohort_metrics['segments'][ltv_metrics['segment']] += 1
                    
                    if customer['status'] == 'active':
                        cohort_metrics['active_customers'] += 1
                    else:
                        cohort_metrics['churned_customers'] += 1
            
            if ltv_values:
                cohort_metrics['average_months_active'] /= len(ltv_values)
                
                ltv_stats = {
                    'mean_ltv': np.mean(ltv_values),
                    'median_ltv': np.median(ltv_values),
                    'std_ltv': np.std(ltv_values),
                    'min_ltv': np.min(ltv_values),
                    'max_ltv': np.max(ltv_values),
                    'percentile_25': np.percentile(ltv_values, 25),
                    'percentile_75': np.percentile(ltv_values, 75)
                }
                
                return {
                    'success': True,
                    'cohort_id': cohort_id,
                    'ltv_statistics': ltv_stats,
                    'cohort_metrics': cohort_metrics,
                    'calculated_at': datetime.now().isoformat()
                }
            
            return {'success': False, 'error': 'No valid LTV calculations found'}
        
        except Exception as e:
            logger.error(f"Error calculating cohort LTV: {e}")
            return {'success': False, 'error': str(e)}
    
    async def identify_high_value_customers(self, threshold_percentile: int = 80) -> List[Dict]:
        """Identify customers with high predicted LTV"""
        try:
            all_customers = await self._get_all_customers()
            customer_ltvs = []
            
            for customer in all_customers:
                ltv_result = await self.calculate_customer_ltv(customer['id'], 'predictive')
                if ltv_result['success']:
                    customer_ltvs.append({
                        'customer_id': customer['id'],
                        'ltv': ltv_result['ltv_metrics']['ltv_prediction'],
                        'segment': ltv_result['ltv_metrics']['segment'],
                        'monthly_revenue': ltv_result['ltv_metrics']['monthly_revenue'],
                        'churn_probability': ltv_result['ltv_metrics']['churn_probability']
                    })
            
            if not customer_ltvs:
                return []
            
            # Calculate threshold
            ltv_values = [c['ltv'] for c in customer_ltvs]
            threshold = np.percentile(ltv_values, threshold_percentile)
            
            # Filter high-value customers
            high_value_customers = [
                customer for customer in customer_ltvs 
                if customer['ltv'] >= threshold
            ]
            
            # Sort by LTV descending
            high_value_customers.sort(key=lambda x: x['ltv'], reverse=True)
            
            return high_value_customers
        
        except Exception as e:
            logger.error(f"Error identifying high-value customers: {e}")
            return []
    
    async def generate_ltv_optimization_recommendations(self, customer_id: str) -> List[Dict]:
        """Generate recommendations to optimize customer LTV"""
        ltv_result = await self.calculate_customer_ltv(customer_id, 'predictive')
        
        if not ltv_result['success']:
            return []
        
        ltv_metrics = ltv_result['ltv_metrics']
        recommendations = []
        
        # Churn risk recommendations
        if ltv_metrics['churn_probability'] > 0.7:
            recommendations.append({
                'type': 'retention',
                'priority': 'high',
                'action': 'Immediate retention campaign',
                'description': 'Customer has high churn risk - implement retention strategy',
                'potential_impact': ltv_metrics['ltv_prediction'] * 0.8
            })
        
        # Upsell recommendations
        if ltv_metrics['segment'] == 'standard' and ltv_metrics['monthly_revenue'] > 20:
            recommendations.append({
                'type': 'upsell',
                'priority': 'medium',
                'action': 'Premium plan upgrade',
                'description': 'Customer shows potential for higher-tier plan',
                'potential_impact': ltv_metrics['ltv_prediction'] * 1.4
            })
        
        # Engagement recommendations
        if ltv_metrics['months_active'] > 6 and ltv_metrics['monthly_revenue'] < 15:
            recommendations.append({
                'type': 'engagement',
                'priority': 'medium',
                'action': 'Feature adoption campaign',
                'description': 'Long-term customer with low spend - increase feature usage',
                'potential_impact': ltv_metrics['ltv_prediction'] * 1.2
            })
        
        # Cross-sell recommendations
        if ltv_metrics['segment'] == 'high_value':
            recommendations.append({
                'type': 'cross_sell',
                'priority': 'low',
                'action': 'Additional services',
                'description': 'High-value customer ready for additional products',
                'potential_impact': ltv_metrics['ltv_prediction'] * 1.3
            })
        
        return recommendations
    
    async def _calculate_predictive_ltv(self, customer_data: Dict) -> LTVMetrics:
        """Calculate LTV using predictive modeling approach"""
        # Extract features
        monthly_revenue = customer_data.get('monthly_revenue', 0)
        months_active = customer_data.get('months_active', 1)
        churn_probability = customer_data.get('churn_probability', 0.5)
        
        # Determine customer segment
        segment = self._determine_customer_segment(customer_data)
        
        # Get segment parameters
        segment_params = self.segment_models[segment]
        
        # Calculate expected remaining lifetime
        expected_lifetime_months = segment_params['monthly_multiplier'] * (1 - churn_probability)
        
        # Apply churn discount
        churn_discount = segment_params['churn_discount']
        
        # Calculate predictive LTV
        base_ltv = monthly_revenue * expected_lifetime_months
        adjusted_ltv = base_ltv * churn_discount
        
        # Calculate confidence score based on data quality
        confidence_score = min(1.0, months_active / 12 * 0.8 + (1 - churn_probability) * 0.2)
        
        return LTVMetrics(
            customer_id=customer_data['customer_id'],
            ltv_prediction=adjusted_ltv,
            ltv_actual=None,
            months_active=months_active,
            monthly_revenue=monthly_revenue,
            churn_probability=churn_probability,
            segment=segment,
            confidence_score=confidence_score
        )
    
    async def _calculate_historical_ltv(self, customer_data: Dict) -> LTVMetrics:
        """Calculate LTV based on historical data"""
        total_revenue = customer_data.get('total_revenue', 0)
        months_active = customer_data.get('months_active', 1)
        monthly_revenue = total_revenue / max(months_active, 1)
        
        # For historical LTV, we use actual revenue
        ltv_actual = total_revenue
        
        # Predict future LTV if customer is still active
        if customer_data.get('status') == 'active':
            churn_probability = customer_data.get('churn_probability', 0.3)
            expected_future_months = 12 * (1 - churn_probability)
            future_revenue = monthly_revenue * expected_future_months
            ltv_prediction = ltv_actual + future_revenue
        else:
            ltv_prediction = ltv_actual
        
        segment = self._determine_customer_segment(customer_data)
        confidence_score = 1.0 if customer_data.get('status') == 'churned' else 0.8
        
        return LTVMetrics(
            customer_id=customer_data['customer_id'],
            ltv_prediction=ltv_prediction,
            ltv_actual=ltv_actual,
            months_active=months_active,
            monthly_revenue=monthly_revenue,
            churn_probability=customer_data.get('churn_probability', 0.3),
            segment=segment,
            confidence_score=confidence_score
        )
    
    async def _calculate_cohort_ltv(self, customer_data: Dict) -> LTVMetrics:
        """Calculate LTV based on cohort analysis"""
        cohort_id = customer_data.get('cohort_id', 'default')
        cohort_stats = await self._get_cohort_statistics(cohort_id)
        
        months_active = customer_data.get('months_active', 1)
        monthly_revenue = customer_data.get('monthly_revenue', 0)
        
        # Use cohort average for prediction if customer is new
        if months_active < 3:
            ltv_prediction = cohort_stats.get('average_ltv', monthly_revenue * 8)
        else:
            # Use customer-specific calculation
            personal_ltv = await self._calculate_predictive_ltv(customer_data)
            ltv_prediction = personal_ltv.ltv_prediction
        
        segment = self._determine_customer_segment(customer_data)
        churn_probability = cohort_stats.get('average_churn_rate', 0.4)
        
        return LTVMetrics(
            customer_id=customer_data['customer_id'],
            ltv_prediction=ltv_prediction,
            ltv_actual=customer_data.get('total_revenue'),
            months_active=months_active,
            monthly_revenue=monthly_revenue,
            churn_probability=churn_probability,
            segment=segment,
            confidence_score=0.7  # Cohort-based predictions are less certain
        )
    
    def _determine_customer_segment(self, customer_data: Dict) -> str:
        """Determine customer segment based on behavior and value"""
        monthly_revenue = customer_data.get('monthly_revenue', 0)
        usage_score = customer_data.get('usage_score', 0.5)
        engagement_score = customer_data.get('engagement_score', 0.5)
        
        # Calculate composite score
        value_score = (monthly_revenue / 50) * 0.4 + usage_score * 0.3 + engagement_score * 0.3
        
        if value_score >= 0.7:
            return 'high_value'
        elif value_score >= 0.4:
            return 'standard'
        else:
            return 'low_value'
    
    async def _get_customer_data(self, customer_id: str) -> Optional[Dict]:
        """Get comprehensive customer data for LTV calculation"""
        # Mock implementation - would connect to actual database
        return {
            'customer_id': customer_id,
            'monthly_revenue': np.random.uniform(10, 100),
            'total_revenue': np.random.uniform(50, 500),
            'months_active': np.random.randint(1, 24),
            'churn_probability': np.random.uniform(0.1, 0.8),
            'usage_score': np.random.uniform(0.3, 1.0),
            'engagement_score': np.random.uniform(0.2, 1.0),
            'status': np.random.choice(['active', 'churned'], p=[0.8, 0.2]),
            'cohort_id': f'cohort_{np.random.randint(1, 10)}'
        }
    
    async def _get_cohort_customers(self, cohort_id: str) -> List[Dict]:
        """Get all customers in a specific cohort"""
        # Mock implementation
        return [
            {'id': f'customer_{i}', 'cohort_id': cohort_id, 'status': 'active'}
            for i in range(1, 51)
        ]
    
    async def _get_all_customers(self) -> List[Dict]:
        """Get all customers for analysis"""
        # Mock implementation
        return [
            {'id': f'customer_{i}', 'status': 'active'}
            for i in range(1, 101)
        ]
    
    async def _get_cohort_statistics(self, cohort_id: str) -> Dict:
        """Get statistical data for a cohort"""
        # Mock implementation
        return {
            'average_ltv': np.random.uniform(200, 800),
            'average_churn_rate': np.random.uniform(0.2, 0.6),
            'average_monthly_revenue': np.random.uniform(20, 80),
            'customer_count': np.random.randint(10, 100)
        }