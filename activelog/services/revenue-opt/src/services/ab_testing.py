import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from scipy import stats
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging
import uuid

logger = logging.getLogger(__name__)

class TestStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

@dataclass
class ABTestResult:
    variant_a_conversion: float
    variant_b_conversion: float
    confidence_level: float
    p_value: float
    is_significant: bool
    winner: Optional[str]
    lift: float
    sample_size_a: int
    sample_size_b: int

class ABTestingService:
    def __init__(self):
        self.active_tests = {}
        self.test_history = []
        self.min_sample_size = settings.AB_TEST_MIN_SAMPLE_SIZE
        self.significance_level = settings.AB_TEST_SIGNIFICANCE_LEVEL
    
    async def create_pricing_test(self, 
                                 test_name: str,
                                 control_price: float,
                                 variant_price: float,
                                 target_metric: str = "conversion_rate",
                                 duration_days: int = 30,
                                 traffic_split: float = 0.5) -> Dict:
        """Create a new A/B test for pricing optimization"""
        test_id = str(uuid.uuid4())
        
        test_config = {
            'test_id': test_id,
            'test_name': test_name,
            'test_type': 'pricing',
            'status': TestStatus.DRAFT.value,
            'created_at': datetime.now().isoformat(),
            'start_date': None,
            'end_date': None,
            'duration_days': duration_days,
            'traffic_split': traffic_split,
            'target_metric': target_metric,
            'variants': {
                'control': {
                    'price': control_price,
                    'traffic_percentage': traffic_split,
                    'conversions': 0,
                    'impressions': 0,
                    'revenue': 0.0
                },
                'variant': {
                    'price': variant_price,
                    'traffic_percentage': 1 - traffic_split,
                    'conversions': 0,
                    'impressions': 0,
                    'revenue': 0.0
                }
            },
            'hypothesis': f"Changing price from ${control_price} to ${variant_price} will improve {target_metric}",
            'success_criteria': {
                'min_sample_size': self.min_sample_size,
                'significance_level': self.significance_level,
                'minimum_detectable_effect': 0.05  # 5% minimum improvement
            }
        }
        
        self.active_tests[test_id] = test_config
        
        logger.info(f"Created pricing A/B test: {test_name} (ID: {test_id})")
        
        return {
            'success': True,
            'test_id': test_id,
            'test_config': test_config
        }
    
    async def start_test(self, test_id: str) -> Dict:
        """Start an A/B test"""
        if test_id not in self.active_tests:
            return {'success': False, 'error': 'Test not found'}
        
        test = self.active_tests[test_id]
        
        if test['status'] != TestStatus.DRAFT.value:
            return {'success': False, 'error': 'Test is not in draft status'}
        
        # Start the test
        test['status'] = TestStatus.RUNNING.value
        test['start_date'] = datetime.now().isoformat()
        test['end_date'] = (datetime.now() + timedelta(days=test['duration_days'])).isoformat()
        
        logger.info(f"Started A/B test: {test['test_name']} (ID: {test_id})")
        
        return {
            'success': True,
            'test_id': test_id,
            'start_date': test['start_date'],
            'end_date': test['end_date']
        }
    
    async def assign_variant(self, test_id: str, user_id: str) -> Dict:
        """Assign a user to a test variant"""
        if test_id not in self.active_tests:
            return {'success': False, 'error': 'Test not found'}
        
        test = self.active_tests[test_id]
        
        if test['status'] != TestStatus.RUNNING.value:
            return {'success': False, 'error': 'Test is not running'}
        
        # Use consistent hashing to assign variant
        hash_value = hash(f"{test_id}_{user_id}") % 100
        traffic_split_percentage = test['traffic_split'] * 100
        
        if hash_value < traffic_split_percentage:
            variant = 'control'
        else:
            variant = 'variant'
        
        # Get variant details
        variant_data = test['variants'][variant]
        
        return {
            'success': True,
            'variant': variant,
            'price': variant_data['price'],
            'user_id': user_id,
            'test_id': test_id
        }
    
    async def record_impression(self, test_id: str, variant: str, user_id: str) -> Dict:
        """Record an impression for a test variant"""
        if test_id not in self.active_tests:
            return {'success': False, 'error': 'Test not found'}
        
        test = self.active_tests[test_id]
        
        if variant not in test['variants']:
            return {'success': False, 'error': 'Invalid variant'}
        
        # Record impression
        test['variants'][variant]['impressions'] += 1
        
        return {
            'success': True,
            'test_id': test_id,
            'variant': variant,
            'total_impressions': test['variants'][variant]['impressions']
        }
    
    async def record_conversion(self, test_id: str, variant: str, user_id: str, revenue: float = 0.0) -> Dict:
        """Record a conversion for a test variant"""
        if test_id not in self.active_tests:
            return {'success': False, 'error': 'Test not found'}
        
        test = self.active_tests[test_id]
        
        if variant not in test['variants']:
            return {'success': False, 'error': 'Invalid variant'}
        
        # Record conversion
        test['variants'][variant]['conversions'] += 1
        test['variants'][variant]['revenue'] += revenue
        
        # Check if test should be auto-stopped
        should_stop, reason = await self._should_auto_stop_test(test_id)
        if should_stop:
            await self.stop_test(test_id, reason)
        
        return {
            'success': True,
            'test_id': test_id,
            'variant': variant,
            'total_conversions': test['variants'][variant]['conversions'],
            'total_revenue': test['variants'][variant]['revenue']
        }
    
    async def get_test_results(self, test_id: str) -> Dict:
        """Get current results for an A/B test"""
        if test_id not in self.active_tests:
            return {'success': False, 'error': 'Test not found'}
        
        test = self.active_tests[test_id]
        
        # Calculate basic metrics
        control = test['variants']['control']
        variant = test['variants']['variant']
        
        control_rate = control['conversions'] / max(control['impressions'], 1)
        variant_rate = variant['conversions'] / max(variant['impressions'], 1)
        
        # Perform statistical analysis
        statistical_result = await self._perform_statistical_analysis(
            control['conversions'], control['impressions'],
            variant['conversions'], variant['impressions']
        )
        
        # Calculate revenue metrics
        control_revenue_per_visitor = control['revenue'] / max(control['impressions'], 1)
        variant_revenue_per_visitor = variant['revenue'] / max(variant['impressions'], 1)
        
        # Determine test status and recommendations
        recommendations = await self._generate_test_recommendations(test_id, statistical_result)
        
        return {
            'success': True,
            'test_id': test_id,
            'test_name': test['test_name'],
            'status': test['status'],
            'duration_days': test['duration_days'],
            'start_date': test['start_date'],
            'end_date': test['end_date'],
            'results': {
                'control': {
                    'impressions': control['impressions'],
                    'conversions': control['conversions'],
                    'conversion_rate': control_rate,
                    'revenue': control['revenue'],
                    'revenue_per_visitor': control_revenue_per_visitor,
                    'price': control['price']
                },
                'variant': {
                    'impressions': variant['impressions'],
                    'conversions': variant['conversions'],
                    'conversion_rate': variant_rate,
                    'revenue': variant['revenue'],
                    'revenue_per_visitor': variant_revenue_per_visitor,
                    'price': variant['price']
                },
                'statistical_analysis': statistical_result.__dict__,
                'recommendations': recommendations
            }
        }
    
    async def stop_test(self, test_id: str, reason: str = "Manual stop") -> Dict:
        """Stop a running A/B test"""
        if test_id not in self.active_tests:
            return {'success': False, 'error': 'Test not found'}
        
        test = self.active_tests[test_id]
        
        if test['status'] != TestStatus.RUNNING.value:
            return {'success': False, 'error': 'Test is not running'}
        
        # Stop the test
        test['status'] = TestStatus.COMPLETED.value
        test['stopped_at'] = datetime.now().isoformat()
        test['stop_reason'] = reason
        
        # Move to history
        self.test_history.append(test.copy())
        
        # Generate final report
        final_results = await self.get_test_results(test_id)
        
        logger.info(f"Stopped A/B test: {test['test_name']} (ID: {test_id}), Reason: {reason}")
        
        return {
            'success': True,
            'test_id': test_id,
            'stop_reason': reason,
            'final_results': final_results
        }
    
    async def get_active_tests(self) -> List[Dict]:
        """Get all active A/B tests"""
        active_tests = []
        
        for test_id, test in self.active_tests.items():
            if test['status'] == TestStatus.RUNNING.value:
                test_summary = await self.get_test_results(test_id)
                active_tests.append(test_summary)
        
        return active_tests
    
    async def _perform_statistical_analysis(self, 
                                          control_conversions: int,
                                          control_impressions: int,
                                          variant_conversions: int,
                                          variant_impressions: int) -> ABTestResult:
        """Perform statistical analysis on A/B test results"""
        
        if control_impressions == 0 or variant_impressions == 0:
            return ABTestResult(
                variant_a_conversion=0.0,
                variant_b_conversion=0.0,
                confidence_level=0.0,
                p_value=1.0,
                is_significant=False,
                winner=None,
                lift=0.0,
                sample_size_a=control_impressions,
                sample_size_b=variant_impressions
            )
        
        # Calculate conversion rates
        control_rate = control_conversions / control_impressions
        variant_rate = variant_conversions / variant_impressions
        
        # Perform two-proportion z-test
        p1 = control_rate
        p2 = variant_rate
        n1 = control_impressions
        n2 = variant_impressions
        
        # Pooled proportion
        p_pool = (control_conversions + variant_conversions) / (control_impressions + variant_impressions)
        
        # Standard error
        se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        
        # Z-score
        if se > 0:
            z_score = (p2 - p1) / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        else:
            z_score = 0
            p_value = 1.0
        
        # Determine significance
        is_significant = p_value < self.significance_level
        confidence_level = (1 - p_value) * 100
        
        # Calculate lift
        if control_rate > 0:
            lift = ((variant_rate - control_rate) / control_rate) * 100
        else:
            lift = 0.0
        
        # Determine winner
        winner = None
        if is_significant:
            if variant_rate > control_rate:
                winner = "variant"
            elif control_rate > variant_rate:
                winner = "control"
        
        return ABTestResult(
            variant_a_conversion=control_rate,
            variant_b_conversion=variant_rate,
            confidence_level=confidence_level,
            p_value=p_value,
            is_significant=is_significant,
            winner=winner,
            lift=lift,
            sample_size_a=control_impressions,
            sample_size_b=variant_impressions
        )
    
    async def _should_auto_stop_test(self, test_id: str) -> Tuple[bool, str]:
        """Check if test should be automatically stopped"""
        test = self.active_tests[test_id]
        
        # Check if test duration is exceeded
        if test['end_date']:
            end_date = datetime.fromisoformat(test['end_date'])
            if datetime.now() > end_date:
                return True, "Test duration exceeded"
        
        # Check for statistical significance with enough sample size
        control = test['variants']['control']
        variant = test['variants']['variant']
        
        if (control['impressions'] >= self.min_sample_size and 
            variant['impressions'] >= self.min_sample_size):
            
            statistical_result = await self._perform_statistical_analysis(
                control['conversions'], control['impressions'],
                variant['conversions'], variant['impressions']
            )
            
            # Stop if highly significant (p < 0.01) and good sample size
            if statistical_result.is_significant and statistical_result.p_value < 0.01:
                return True, f"Statistical significance reached (p={statistical_result.p_value:.4f})"
        
        return False, ""
    
    async def _generate_test_recommendations(self, test_id: str, statistical_result: ABTestResult) -> List[str]:
        """Generate recommendations based on test results"""
        test = self.active_tests[test_id]
        recommendations = []
        
        control = test['variants']['control']
        variant = test['variants']['variant']
        
        # Sample size recommendations
        if control['impressions'] < self.min_sample_size or variant['impressions'] < self.min_sample_size:
            recommendations.append(f"Continue test - need minimum {self.min_sample_size} samples per variant")
        
        # Statistical significance recommendations
        if statistical_result.is_significant:
            if statistical_result.winner == "variant":
                price_change = variant['price'] - control['price']
                recommendations.append(f"Winner: Variant (${variant['price']}) - {statistical_result.lift:.1f}% improvement")
                recommendations.append(f"Implement price change of ${price_change:+.2f}")
            elif statistical_result.winner == "control":
                recommendations.append(f"Winner: Control (${control['price']}) - keep current pricing")
        else:
            if statistical_result.p_value > 0.5:
                recommendations.append("No significant difference detected - consider larger sample size")
            else:
                recommendations.append(f"Test trending but not significant (p={statistical_result.p_value:.3f})")
        
        # Revenue impact recommendations
        control_rpm = control['revenue'] / max(control['impressions'], 1) * 1000
        variant_rpm = variant['revenue'] / max(variant['impressions'], 1) * 1000
        
        if variant_rpm > control_rpm * 1.05:
            recommendations.append(f"Variant shows {((variant_rpm/control_rpm-1)*100):.1f}% higher revenue per visitor")
        
        return recommendations