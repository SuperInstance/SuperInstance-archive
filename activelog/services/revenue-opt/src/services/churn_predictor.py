import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from ..models.customer import Customer
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class ChurnPredictor:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = [
            'days_since_last_login',
            'total_logins',
            'avg_session_duration',
            'total_revenue',
            'days_since_last_purchase',
            'support_tickets',
            'feature_usage_score',
            'account_age_days'
        ]
    
    async def predict_churn_probability(self, customer_id: str) -> float:
        """Predict churn probability for a specific customer"""
        try:
            customer_data = await self._get_customer_features(customer_id)
            if not customer_data:
                return 0.0
            
            features = self._prepare_features(customer_data)
            if not self.is_trained:
                await self._train_model()
            
            probability = self.model.predict_proba([features])[0][1]
            return float(probability)
        
        except Exception as e:
            logger.error(f"Error predicting churn for customer {customer_id}: {e}")
            return 0.0
    
    async def identify_at_risk_customers(self, threshold: Optional[float] = None) -> List[Dict]:
        """Identify customers at risk of churning"""
        if threshold is None:
            threshold = settings.CHURN_MODEL_THRESHOLD
        
        at_risk_customers = []
        
        # Get all active customers
        customers = await self._get_all_active_customers()
        
        for customer in customers:
            churn_prob = await self.predict_churn_probability(customer['id'])
            
            if churn_prob >= threshold:
                risk_factors = await self._analyze_risk_factors(customer['id'])
                
                at_risk_customers.append({
                    'customer_id': customer['id'],
                    'churn_probability': churn_prob,
                    'risk_level': self._get_risk_level(churn_prob),
                    'risk_factors': risk_factors,
                    'recommended_actions': await self._get_retention_recommendations(customer['id'], risk_factors)
                })
        
        # Sort by churn probability (highest risk first)
        at_risk_customers.sort(key=lambda x: x['churn_probability'], reverse=True)
        return at_risk_customers
    
    async def execute_retention_campaign(self, customer_id: str, campaign_type: str) -> Dict:
        """Execute automated retention campaign"""
        campaigns = {
            'discount_offer': await self._send_discount_offer(customer_id),
            'feature_tutorial': await self._send_feature_tutorial(customer_id),
            'personal_outreach': await self._schedule_personal_outreach(customer_id),
            'loyalty_reward': await self._send_loyalty_reward(customer_id),
            'usage_report': await self._send_usage_report(customer_id)
        }
        
        if campaign_type in campaigns:
            result = await campaigns[campaign_type]
            
            # Log campaign execution
            await self._log_retention_campaign(customer_id, campaign_type, result)
            
            return result
        
        return {'success': False, 'error': 'Unknown campaign type'}
    
    async def _get_customer_features(self, customer_id: str) -> Optional[Dict]:
        """Get customer features for churn prediction"""
        try:
            # This would connect to your actual database
            # Mock implementation for now
            return {
                'customer_id': customer_id,
                'days_since_last_login': 5,
                'total_logins': 45,
                'avg_session_duration': 25.5,
                'total_revenue': 299.99,
                'days_since_last_purchase': 30,
                'support_tickets': 2,
                'feature_usage_score': 0.65,
                'account_age_days': 120
            }
        except Exception as e:
            logger.error(f"Error getting customer features: {e}")
            return None
    
    def _prepare_features(self, customer_data: Dict) -> List[float]:
        """Prepare features for model prediction"""
        features = []
        for column in self.feature_columns:
            features.append(customer_data.get(column, 0))
        return features
    
    async def _train_model(self):
        """Train the churn prediction model"""
        try:
            # Generate synthetic training data for demo
            # In production, this would use historical customer data
            training_data = await self._generate_training_data()
            
            X = training_data[self.feature_columns]
            y = training_data['churned']
            
            X_scaled = self.scaler.fit_transform(X)
            self.model.fit(X_scaled, y)
            self.is_trained = True
            
            logger.info("Churn prediction model trained successfully")
            
        except Exception as e:
            logger.error(f"Error training churn model: {e}")
    
    async def _generate_training_data(self) -> pd.DataFrame:
        """Generate synthetic training data"""
        np.random.seed(42)
        n_samples = 1000
        
        data = {
            'days_since_last_login': np.random.exponential(5, n_samples),
            'total_logins': np.random.poisson(30, n_samples),
            'avg_session_duration': np.random.normal(20, 10, n_samples),
            'total_revenue': np.random.lognormal(5, 1, n_samples),
            'days_since_last_purchase': np.random.exponential(20, n_samples),
            'support_tickets': np.random.poisson(1, n_samples),
            'feature_usage_score': np.random.beta(2, 2, n_samples),
            'account_age_days': np.random.normal(180, 90, n_samples)
        }
        
        df = pd.DataFrame(data)
        
        # Create churn labels based on features
        churn_prob = (
            0.3 * (df['days_since_last_login'] > 10) +
            0.2 * (df['total_logins'] < 10) +
            0.2 * (df['days_since_last_purchase'] > 60) +
            0.1 * (df['support_tickets'] > 3) +
            0.2 * (df['feature_usage_score'] < 0.3)
        )
        
        df['churned'] = np.random.binomial(1, churn_prob)
        
        return df
    
    async def _analyze_risk_factors(self, customer_id: str) -> List[str]:
        """Analyze specific risk factors for a customer"""
        customer_data = await self._get_customer_features(customer_id)
        if not customer_data:
            return []
        
        risk_factors = []
        
        if customer_data['days_since_last_login'] > 7:
            risk_factors.append("Infrequent logins")
        
        if customer_data['days_since_last_purchase'] > 60:
            risk_factors.append("Long time since last purchase")
        
        if customer_data['feature_usage_score'] < 0.3:
            risk_factors.append("Low feature engagement")
        
        if customer_data['support_tickets'] > 3:
            risk_factors.append("High support ticket volume")
        
        if customer_data['avg_session_duration'] < 5:
            risk_factors.append("Short session duration")
        
        return risk_factors
    
    def _get_risk_level(self, churn_probability: float) -> str:
        """Determine risk level based on churn probability"""
        if churn_probability >= 0.8:
            return "Critical"
        elif churn_probability >= 0.6:
            return "High"
        elif churn_probability >= 0.4:
            return "Medium"
        else:
            return "Low"
    
    async def _get_retention_recommendations(self, customer_id: str, risk_factors: List[str]) -> List[str]:
        """Get retention recommendations based on risk factors"""
        recommendations = []
        
        if "Infrequent logins" in risk_factors:
            recommendations.append("Send re-engagement email with feature highlights")
        
        if "Long time since last purchase" in risk_factors:
            recommendations.append("Offer personalized discount or promotion")
        
        if "Low feature engagement" in risk_factors:
            recommendations.append("Provide guided tutorial or onboarding")
        
        if "High support ticket volume" in risk_factors:
            recommendations.append("Schedule personal check-in call")
        
        if "Short session duration" in risk_factors:
            recommendations.append("Recommend relevant features based on usage pattern")
        
        # Default recommendations
        if not recommendations:
            recommendations.extend([
                "Send satisfaction survey",
                "Offer loyalty reward",
                "Schedule product demo"
            ])
        
        return recommendations
    
    async def _get_all_active_customers(self) -> List[Dict]:
        """Get all active customers"""
        # Mock implementation
        return [
            {'id': f'customer_{i}', 'status': 'active'}
            for i in range(1, 101)
        ]
    
    async def _send_discount_offer(self, customer_id: str) -> Dict:
        """Send discount offer to customer"""
        # Mock implementation
        logger.info(f"Sending 20% discount offer to customer {customer_id}")
        return {
            'success': True,
            'campaign_type': 'discount_offer',
            'message': 'Sent 20% discount offer',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _send_feature_tutorial(self, customer_id: str) -> Dict:
        """Send feature tutorial to customer"""
        logger.info(f"Sending feature tutorial to customer {customer_id}")
        return {
            'success': True,
            'campaign_type': 'feature_tutorial',
            'message': 'Sent personalized feature tutorial',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _schedule_personal_outreach(self, customer_id: str) -> Dict:
        """Schedule personal outreach call"""
        logger.info(f"Scheduling personal outreach for customer {customer_id}")
        return {
            'success': True,
            'campaign_type': 'personal_outreach',
            'message': 'Scheduled personal check-in call',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _send_loyalty_reward(self, customer_id: str) -> Dict:
        """Send loyalty reward to customer"""
        logger.info(f"Sending loyalty reward to customer {customer_id}")
        return {
            'success': True,
            'campaign_type': 'loyalty_reward',
            'message': 'Sent loyalty points and exclusive access',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _send_usage_report(self, customer_id: str) -> Dict:
        """Send personalized usage report"""
        logger.info(f"Sending usage report to customer {customer_id}")
        return {
            'success': True,
            'campaign_type': 'usage_report',
            'message': 'Sent personalized usage insights report',
            'timestamp': datetime.now().isoformat()
        }
    
    async def _log_retention_campaign(self, customer_id: str, campaign_type: str, result: Dict):
        """Log retention campaign execution"""
        logger.info(f"Retention campaign logged - Customer: {customer_id}, Type: {campaign_type}, Success: {result.get('success', False)}")