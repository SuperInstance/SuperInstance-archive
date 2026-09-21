import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class UpsellDetector:
    def __init__(self):
        self.model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = [
            'current_plan_value',
            'usage_percentage',
            'feature_adoption_score',
            'support_interactions',
            'days_on_current_plan',
            'payment_reliability_score',
            'engagement_score',
            'growth_trajectory'
        ]
        self.plan_matrix = {
            'basic': {'next_tier': 'pro', 'price': 9.99, 'features': ['basic_analytics', 'standard_support']},
            'pro': {'next_tier': 'enterprise', 'price': 29.99, 'features': ['advanced_analytics', 'priority_support', 'api_access']},
            'enterprise': {'next_tier': None, 'price': 99.99, 'features': ['custom_integrations', 'dedicated_support', 'white_label']}
        }
    
    async def identify_upsell_opportunities(self, customer_id: Optional[str] = None) -> List[Dict]:
        """Identify upsell opportunities for specific customer or all customers"""
        opportunities = []
        
        if customer_id:
            customers = [{'id': customer_id}]
        else:
            customers = await self._get_eligible_customers()
        
        for customer in customers:
            opportunity = await self._analyze_customer_upsell_potential(customer['id'])
            if opportunity and opportunity['confidence'] >= settings.UPSELL_CONFIDENCE_THRESHOLD:
                opportunities.append(opportunity)
        
        # Sort by confidence and potential revenue
        opportunities.sort(key=lambda x: (x['confidence'], x['potential_revenue']), reverse=True)
        return opportunities
    
    async def _analyze_customer_upsell_potential(self, customer_id: str) -> Optional[Dict]:
        """Analyze upsell potential for a specific customer"""
        try:
            customer_data = await self._get_customer_data(customer_id)
            if not customer_data:
                return None
            
            current_plan = customer_data['current_plan']
            if current_plan not in self.plan_matrix:
                return None
            
            next_tier = self.plan_matrix[current_plan]['next_tier']
            if not next_tier:
                return None  # Already on highest tier
            
            # Calculate upsell confidence
            features = self._prepare_features(customer_data)
            if not self.is_trained:
                await self._train_model()
            
            confidence = self.model.predict_proba([features])[0][1]
            
            if confidence < settings.UPSELL_CONFIDENCE_THRESHOLD:
                return None
            
            # Calculate potential revenue increase
            current_revenue = self.plan_matrix[current_plan]['price']
            potential_revenue = self.plan_matrix[next_tier]['price']
            revenue_increase = potential_revenue - current_revenue
            
            # Identify specific triggers
            triggers = await self._identify_upsell_triggers(customer_data)
            
            # Generate personalized recommendations
            recommendations = await self._generate_upsell_recommendations(customer_data, next_tier)
            
            return {
                'customer_id': customer_id,
                'current_plan': current_plan,
                'recommended_plan': next_tier,
                'confidence': float(confidence),
                'potential_revenue': revenue_increase,
                'triggers': triggers,
                'recommendations': recommendations,
                'best_approach': await self._determine_best_approach(customer_data, triggers),
                'timing_score': await self._calculate_timing_score(customer_data)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing upsell potential for customer {customer_id}: {e}")
            return None
    
    async def execute_upsell_campaign(self, customer_id: str, campaign_type: str) -> Dict:
        """Execute targeted upsell campaign"""
        campaigns = {
            'feature_showcase': await self._send_feature_showcase(customer_id),
            'usage_upgrade_notice': await self._send_usage_upgrade_notice(customer_id),
            'limited_time_offer': await self._send_limited_time_offer(customer_id),
            'roi_calculation': await self._send_roi_calculation(customer_id),
            'free_trial_upgrade': await self._offer_free_trial_upgrade(customer_id),
            'personal_demo': await self._schedule_personal_demo(customer_id)
        }
        
        if campaign_type in campaigns:
            result = await campaigns[campaign_type]
            await self._log_upsell_campaign(customer_id, campaign_type, result)
            return result
        
        return {'success': False, 'error': 'Unknown campaign type'}
    
    async def track_upsell_conversion(self, customer_id: str, from_plan: str, to_plan: str) -> Dict:
        """Track successful upsell conversion"""
        conversion_data = {
            'customer_id': customer_id,
            'from_plan': from_plan,
            'to_plan': to_plan,
            'conversion_date': datetime.now().isoformat(),
            'revenue_increase': self.plan_matrix[to_plan]['price'] - self.plan_matrix[from_plan]['price']
        }
        
        # Log conversion
        logger.info(f"Upsell conversion tracked: {conversion_data}")
        
        # Update customer success score
        await self._update_customer_success_score(customer_id, 'upsell_conversion')
        
        return {
            'success': True,
            'conversion_data': conversion_data,
            'next_actions': await self._get_post_upsell_actions(customer_id, to_plan)
        }
    
    async def _get_customer_data(self, customer_id: str) -> Optional[Dict]:
        """Get comprehensive customer data for upsell analysis"""
        # Mock implementation - in production would query actual database
        return {
            'customer_id': customer_id,
            'current_plan': 'basic',
            'current_plan_value': 9.99,
            'usage_percentage': 0.85,
            'feature_adoption_score': 0.7,
            'support_interactions': 3,
            'days_on_current_plan': 45,
            'payment_reliability_score': 0.95,
            'engagement_score': 0.8,
            'growth_trajectory': 0.15,
            'company_size': 50,
            'industry': 'technology',
            'monthly_active_users': 1250
        }
    
    def _prepare_features(self, customer_data: Dict) -> List[float]:
        """Prepare features for model prediction"""
        features = []
        for column in self.feature_columns:
            features.append(customer_data.get(column, 0))
        return features
    
    async def _train_model(self):
        """Train the upsell prediction model"""
        try:
            # Generate synthetic training data
            training_data = await self._generate_training_data()
            
            X = training_data[self.feature_columns]
            y = training_data['upsold']
            
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            logger.info("Upsell prediction model trained successfully")
            
        except Exception as e:
            logger.error(f"Error training upsell model: {e}")
    
    async def _generate_training_data(self) -> pd.DataFrame:
        """Generate synthetic training data for upsell prediction"""
        np.random.seed(42)
        n_samples = 1000
        
        data = {
            'current_plan_value': np.random.choice([9.99, 29.99], n_samples, p=[0.7, 0.3]),
            'usage_percentage': np.random.beta(3, 2, n_samples),
            'feature_adoption_score': np.random.beta(2, 3, n_samples),
            'support_interactions': np.random.poisson(2, n_samples),
            'days_on_current_plan': np.random.exponential(60, n_samples),
            'payment_reliability_score': np.random.beta(8, 2, n_samples),
            'engagement_score': np.random.beta(3, 2, n_samples),
            'growth_trajectory': np.random.normal(0.1, 0.2, n_samples)
        }
        
        df = pd.DataFrame(data)
        
        # Create upsell labels based on features
        upsell_prob = (
            0.3 * (df['usage_percentage'] > 0.8) +
            0.25 * (df['feature_adoption_score'] > 0.7) +
            0.2 * (df['engagement_score'] > 0.75) +
            0.15 * (df['payment_reliability_score'] > 0.9) +
            0.1 * (df['growth_trajectory'] > 0.15)
        )
        
        df['upsold'] = np.random.binomial(1, np.clip(upsell_prob, 0, 1))
        
        return df
    
    async def _identify_upsell_triggers(self, customer_data: Dict) -> List[str]:
        """Identify specific triggers that make customer ready for upsell"""
        triggers = []
        
        if customer_data['usage_percentage'] > 0.8:
            triggers.append("High usage - approaching plan limits")
        
        if customer_data['feature_adoption_score'] > 0.7:
            triggers.append("Strong feature adoption - ready for advanced features")
        
        if customer_data['growth_trajectory'] > 0.1:
            triggers.append("Growing business - scaling needs")
        
        if customer_data['engagement_score'] > 0.75:
            triggers.append("High engagement - power user behavior")
        
        if customer_data['days_on_current_plan'] > 60:
            triggers.append("Long tenure - established user ready for upgrade")
        
        if customer_data.get('company_size', 0) > 25:
            triggers.append("Company size suggests enterprise needs")
        
        return triggers
    
    async def _generate_upsell_recommendations(self, customer_data: Dict, target_plan: str) -> List[str]:
        """Generate personalized upsell recommendations"""
        recommendations = []
        
        current_plan = customer_data['current_plan']
        target_features = self.plan_matrix[target_plan]['features']
        
        if customer_data['usage_percentage'] > 0.8:
            recommendations.append(f"Upgrade to {target_plan} for increased usage limits")
        
        if 'advanced_analytics' in target_features:
            recommendations.append("Access advanced analytics and reporting features")
        
        if 'api_access' in target_features:
            recommendations.append("Integrate with your existing tools via API access")
        
        if 'priority_support' in target_features:
            recommendations.append("Get priority support and faster response times")
        
        if customer_data.get('company_size', 0) > 25:
            recommendations.append("Scale with team collaboration features")
        
        return recommendations
    
    async def _determine_best_approach(self, customer_data: Dict, triggers: List[str]) -> str:
        """Determine the best approach for upselling this customer"""
        if "High usage - approaching plan limits" in triggers:
            return "usage_based"
        elif "Strong feature adoption - ready for advanced features" in triggers:
            return "feature_based"
        elif "Growing business - scaling needs" in triggers:
            return "growth_based"
        elif customer_data['payment_reliability_score'] > 0.9:
            return "value_based"
        else:
            return "relationship_based"
    
    async def _calculate_timing_score(self, customer_data: Dict) -> float:
        """Calculate optimal timing score for upsell approach"""
        score = 0.0
        
        # Higher usage percentage = better timing
        score += customer_data['usage_percentage'] * 0.3
        
        # High engagement = good timing
        score += customer_data['engagement_score'] * 0.25
        
        # Payment reliability = readiness to pay
        score += customer_data['payment_reliability_score'] * 0.2
        
        # Feature adoption = understanding value
        score += customer_data['feature_adoption_score'] * 0.15
        
        # Growth trajectory = future needs
        if customer_data['growth_trajectory'] > 0:
            score += min(customer_data['growth_trajectory'], 0.5) * 0.1
        
        return min(score, 1.0)
    
    async def _get_eligible_customers(self) -> List[Dict]:
        """Get customers eligible for upsell analysis"""
        # Mock implementation
        return [{'id': f'customer_{i}'} for i in range(1, 51)]
    
    # Campaign execution methods
    async def _send_feature_showcase(self, customer_id: str) -> Dict:
        logger.info(f"Sending feature showcase to customer {customer_id}")
        return {'success': True, 'campaign_type': 'feature_showcase', 'timestamp': datetime.now().isoformat()}
    
    async def _send_usage_upgrade_notice(self, customer_id: str) -> Dict:
        logger.info(f"Sending usage upgrade notice to customer {customer_id}")
        return {'success': True, 'campaign_type': 'usage_upgrade_notice', 'timestamp': datetime.now().isoformat()}
    
    async def _send_limited_time_offer(self, customer_id: str) -> Dict:
        logger.info(f"Sending limited time offer to customer {customer_id}")
        return {'success': True, 'campaign_type': 'limited_time_offer', 'timestamp': datetime.now().isoformat()}
    
    async def _send_roi_calculation(self, customer_id: str) -> Dict:
        logger.info(f"Sending ROI calculation to customer {customer_id}")
        return {'success': True, 'campaign_type': 'roi_calculation', 'timestamp': datetime.now().isoformat()}
    
    async def _offer_free_trial_upgrade(self, customer_id: str) -> Dict:
        logger.info(f"Offering free trial upgrade to customer {customer_id}")
        return {'success': True, 'campaign_type': 'free_trial_upgrade', 'timestamp': datetime.now().isoformat()}
    
    async def _schedule_personal_demo(self, customer_id: str) -> Dict:
        logger.info(f"Scheduling personal demo for customer {customer_id}")
        return {'success': True, 'campaign_type': 'personal_demo', 'timestamp': datetime.now().isoformat()}
    
    async def _log_upsell_campaign(self, customer_id: str, campaign_type: str, result: Dict):
        """Log upsell campaign execution"""
        logger.info(f"Upsell campaign logged - Customer: {customer_id}, Type: {campaign_type}, Success: {result.get('success', False)}")
    
    async def _update_customer_success_score(self, customer_id: str, event: str):
        """Update customer success score after conversion"""
        logger.info(f"Updated customer success score for {customer_id} after {event}")
    
    async def _get_post_upsell_actions(self, customer_id: str, new_plan: str) -> List[str]:
        """Get recommended actions after successful upsell"""
        return [
            f"Send welcome email for {new_plan} features",
            "Schedule onboarding call",
            "Provide feature tutorial resources",
            "Monitor usage for next 30 days"
        ]