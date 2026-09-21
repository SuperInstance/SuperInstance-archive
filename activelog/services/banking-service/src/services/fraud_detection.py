import uuid
import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from ..core.config import settings
import logging
import hashlib
from geopy.distance import geodesic

logger = logging.getLogger(__name__)

class FraudRiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FraudAlertType(Enum):
    VELOCITY = "velocity"
    AMOUNT = "amount"
    LOCATION = "location"
    PATTERN = "pattern"
    DEVICE = "device"
    BEHAVIORAL = "behavioral"
    MERCHANT = "merchant"

class ActionType(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    CHALLENGE = "challenge"
    MANUAL_REVIEW = "manual_review"

@dataclass
class FraudAlert:
    alert_id: str
    customer_id: str
    account_id: str
    transaction_id: str
    alert_type: FraudAlertType
    risk_score: float
    risk_level: FraudRiskLevel
    description: str
    triggered_rules: List[str]
    transaction_data: Dict
    device_data: Optional[Dict]
    location_data: Optional[Dict]
    created_at: datetime
    action_taken: ActionType
    reviewed_by: Optional[str]
    resolved_at: Optional[datetime]
    false_positive: Optional[bool]

@dataclass
class CustomerBehaviorProfile:
    customer_id: str
    typical_transaction_amount: float
    typical_transaction_times: List[int]  # Hours of day
    typical_locations: List[Dict]  # Lat/lon coordinates
    typical_merchants: List[str]
    typical_transaction_frequency: float  # Transactions per day
    spending_categories: Dict[str, float]
    device_fingerprints: List[str]
    last_updated: datetime

@dataclass
class DeviceFingerprint:
    device_id: str
    customer_id: str
    user_agent: str
    screen_resolution: str
    timezone: str
    language: str
    ip_address: str
    first_seen: datetime
    last_seen: datetime
    trusted: bool
    risk_score: float

class FraudDetectionService:
    def __init__(self):
        self.alerts = {}
        self.customer_profiles = {}
        self.device_fingerprints = {}
        self.blacklisted_devices = set()
        self.blacklisted_ips = set()
        self.fraud_rules = self._initialize_fraud_rules()
        self.monitoring_active = False
        self.ml_model = self._initialize_ml_model()
        
    async def start_monitoring(self):
        """Start fraud monitoring background tasks"""
        self.monitoring_active = True
        asyncio.create_task(self._continuous_monitoring())
        logger.info("Fraud detection monitoring started")
    
    async def stop_monitoring(self):
        """Stop fraud monitoring"""
        self.monitoring_active = False
        logger.info("Fraud detection monitoring stopped")
    
    async def analyze_transaction(self, transaction_data: Dict) -> Dict:
        """Analyze transaction for fraud indicators"""
        try:
            customer_id = transaction_data.get('customer_id')
            account_id = transaction_data.get('account_id')
            amount = float(transaction_data.get('amount', 0))
            
            # Get or create customer behavior profile
            profile = await self._get_or_create_customer_profile(customer_id)
            
            # Initialize fraud score
            fraud_score = 0.0
            triggered_rules = []
            alerts = []
            
            # Run fraud detection rules
            for rule in self.fraud_rules:
                rule_result = await self._evaluate_fraud_rule(rule, transaction_data, profile)
                if rule_result['triggered']:
                    fraud_score += rule_result['score']
                    triggered_rules.append(rule['rule_id'])
                    alerts.append({
                        'rule_id': rule['rule_id'],
                        'rule_name': rule['name'],
                        'score': rule_result['score'],
                        'description': rule_result.get('description', rule['description'])
                    })
            
            # ML model prediction
            ml_score = await self._get_ml_fraud_score(transaction_data, profile)
            fraud_score += ml_score
            
            # Normalize score to 0-100
            fraud_score = min(100, fraud_score)
            
            # Determine risk level and action
            risk_level, action = self._determine_risk_and_action(fraud_score)
            
            # Create fraud alert if necessary
            alert_id = None
            if risk_level in [FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL] or action != ActionType.ALLOW:
                alert_id = await self._create_fraud_alert(
                    customer_id, account_id, transaction_data.get('transaction_id'),
                    fraud_score, risk_level, triggered_rules, transaction_data, action
                )
            
            # Update customer profile
            await self._update_customer_profile(customer_id, transaction_data)
            
            result = {
                'success': True,
                'fraud_score': fraud_score,
                'risk_level': risk_level.value,
                'action': action.value,
                'triggered_rules': len(triggered_rules),
                'alert_id': alert_id,
                'alerts': alerts,
                'ml_score': ml_score,
                'recommendation': self._get_recommendation(action, fraud_score)
            }
            
            logger.info(f"Fraud analysis completed for transaction {transaction_data.get('transaction_id', 'N/A')}: Score={fraud_score}, Action={action.value}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error in fraud analysis: {e}")
            return {
                'success': False,
                'error': str(e),
                'fraud_score': 0.0,
                'risk_level': 'unknown',
                'action': 'manual_review'
            }
    
    async def register_device(self, customer_id: str, device_data: Dict) -> Dict:
        """Register and analyze device fingerprint"""
        try:
            device_id = self._generate_device_fingerprint(device_data)
            
            # Check if device is blacklisted
            if device_id in self.blacklisted_devices:
                return {
                    'success': False,
                    'device_id': device_id,
                    'status': 'blacklisted',
                    'action': 'block'
                }
            
            # Check if IP is blacklisted
            ip_address = device_data.get('ip_address', '')
            if ip_address in self.blacklisted_ips:
                return {
                    'success': False,
                    'device_id': device_id,
                    'status': 'ip_blacklisted',
                    'action': 'block'
                }
            
            # Get or create device fingerprint
            if device_id in self.device_fingerprints:
                fingerprint = self.device_fingerprints[device_id]
                fingerprint.last_seen = datetime.now()
                
                # Check for device takeover
                if fingerprint.customer_id != customer_id:
                    fingerprint.risk_score += 50
                    return {
                        'success': True,
                        'device_id': device_id,
                        'status': 'suspicious',
                        'risk_score': fingerprint.risk_score,
                        'action': 'challenge',
                        'reason': 'Device associated with different customer'
                    }
            else:
                # New device
                risk_score = await self._calculate_device_risk(device_data, customer_id)
                
                fingerprint = DeviceFingerprint(
                    device_id=device_id,
                    customer_id=customer_id,
                    user_agent=device_data.get('user_agent', ''),
                    screen_resolution=device_data.get('screen_resolution', ''),
                    timezone=device_data.get('timezone', ''),
                    language=device_data.get('language', ''),
                    ip_address=ip_address,
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                    trusted=risk_score < 30,
                    risk_score=risk_score
                )
                
                self.device_fingerprints[device_id] = fingerprint
            
            action = 'allow' if fingerprint.trusted else 'challenge' if fingerprint.risk_score < 70 else 'manual_review'
            
            return {
                'success': True,
                'device_id': device_id,
                'status': 'registered',
                'risk_score': fingerprint.risk_score,
                'trusted': fingerprint.trusted,
                'action': action
            }
        
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_fraud_alerts(self, customer_id: str = None, 
                             start_date: datetime = None,
                             end_date: datetime = None) -> List[Dict]:
        """Get fraud alerts"""
        try:
            alerts = []
            
            for alert in self.alerts.values():
                if customer_id and alert.customer_id != customer_id:
                    continue
                
                if start_date and alert.created_at < start_date:
                    continue
                
                if end_date and alert.created_at > end_date:
                    continue
                
                alerts.append({
                    'alert_id': alert.alert_id,
                    'customer_id': alert.customer_id,
                    'account_id': alert.account_id,
                    'transaction_id': alert.transaction_id,
                    'alert_type': alert.alert_type.value,
                    'risk_score': alert.risk_score,
                    'risk_level': alert.risk_level.value,
                    'description': alert.description,
                    'triggered_rules': alert.triggered_rules,
                    'action_taken': alert.action_taken.value,
                    'created_at': alert.created_at.isoformat(),
                    'resolved': alert.resolved_at is not None,
                    'false_positive': alert.false_positive
                })
            
            return sorted(alerts, key=lambda x: x['created_at'], reverse=True)
        
        except Exception as e:
            logger.error(f"Error getting fraud alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str, resolution: Dict) -> Dict:
        """Resolve a fraud alert"""
        try:
            if alert_id not in self.alerts:
                return {'success': False, 'error': 'Alert not found'}
            
            alert = self.alerts[alert_id]
            
            alert.resolved_at = datetime.now()
            alert.reviewed_by = resolution.get('reviewed_by')
            alert.false_positive = resolution.get('false_positive', False)
            
            # Update ML model with feedback
            if alert.false_positive:
                await self._update_ml_model_feedback(alert, negative=True)
            else:
                await self._update_ml_model_feedback(alert, negative=False)
            
            # Update device trust if applicable
            if resolution.get('trust_device') and alert.device_data:
                device_id = alert.device_data.get('device_id')
                if device_id in self.device_fingerprints:
                    self.device_fingerprints[device_id].trusted = True
                    self.device_fingerprints[device_id].risk_score = max(0, self.device_fingerprints[device_id].risk_score - 20)
            
            return {
                'success': True,
                'alert_id': alert_id,
                'resolution': {
                    'resolved_at': alert.resolved_at.isoformat(),
                    'reviewed_by': alert.reviewed_by,
                    'false_positive': alert.false_positive
                }
            }
        
        except Exception as e:
            logger.error(f"Error resolving alert: {e}")
            return {'success': False, 'error': str(e)}
    
    def _initialize_fraud_rules(self) -> List[Dict]:
        """Initialize fraud detection rules"""
        return [
            {
                'rule_id': 'VELOCITY_CHECK',
                'name': 'Transaction Velocity',
                'description': 'Multiple transactions in short time',
                'max_score': 40,
                'condition': self._check_velocity
            },
            {
                'rule_id': 'AMOUNT_ANOMALY',
                'name': 'Amount Anomaly',
                'description': 'Transaction amount unusual for customer',
                'max_score': 30,
                'condition': self._check_amount_anomaly
            },
            {
                'rule_id': 'LOCATION_ANOMALY',
                'name': 'Location Anomaly',
                'description': 'Transaction from unusual location',
                'max_score': 35,
                'condition': self._check_location_anomaly
            },
            {
                'rule_id': 'TIME_ANOMALY',
                'name': 'Time Pattern Anomaly',
                'description': 'Transaction at unusual time',
                'max_score': 20,
                'condition': self._check_time_anomaly
            },
            {
                'rule_id': 'MERCHANT_RISK',
                'name': 'High-Risk Merchant',
                'description': 'Transaction with high-risk merchant',
                'max_score': 25,
                'condition': self._check_merchant_risk
            },
            {
                'rule_id': 'DEVICE_RISK',
                'name': 'Device Risk',
                'description': 'Transaction from risky device',
                'max_score': 30,
                'condition': self._check_device_risk
            }
        ]
    
    async def _evaluate_fraud_rule(self, rule: Dict, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Evaluate a specific fraud rule"""
        try:
            result = await rule['condition'](transaction_data, profile)
            
            if result['triggered']:
                score = min(rule['max_score'], result.get('score', rule['max_score']))
                return {
                    'triggered': True,
                    'score': score,
                    'description': result.get('description', rule['description'])
                }
            
            return {'triggered': False, 'score': 0}
        
        except Exception as e:
            logger.error(f"Error evaluating fraud rule {rule['rule_id']}: {e}")
            return {'triggered': False, 'score': 0}
    
    async def _check_velocity(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Check transaction velocity"""
        customer_id = transaction_data.get('customer_id')
        current_time = datetime.now()
        
        # Count transactions in last 5 minutes
        recent_transactions = 1  # Mock - would count actual recent transactions
        
        threshold = settings.FRAUD_VELOCITY_THRESHOLD
        
        if recent_transactions > threshold:
            return {
                'triggered': True,
                'score': min(40, recent_transactions * 8),
                'description': f'{recent_transactions} transactions in 5 minutes (threshold: {threshold})'
            }
        
        return {'triggered': False}
    
    async def _check_amount_anomaly(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Check for amount anomalies"""
        amount = float(transaction_data.get('amount', 0))
        
        # Check against customer's typical amount
        if profile.typical_transaction_amount > 0:
            ratio = amount / profile.typical_transaction_amount
            
            if ratio > 10:  # 10x typical amount
                return {
                    'triggered': True,
                    'score': min(30, ratio * 2),
                    'description': f'Amount ${amount} is {ratio:.1f}x typical amount'
                }
        
        # Check against absolute threshold
        if amount > settings.FRAUD_AMOUNT_THRESHOLD:
            return {
                'triggered': True,
                'score': min(30, amount / 1000),
                'description': f'Large transaction amount: ${amount}'
            }
        
        return {'triggered': False}
    
    async def _check_location_anomaly(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Check for location anomalies"""
        transaction_location = transaction_data.get('location')
        
        if not transaction_location or not profile.typical_locations:
            return {'triggered': False}
        
        tx_lat = transaction_location.get('latitude')
        tx_lon = transaction_location.get('longitude')
        
        if not tx_lat or not tx_lon:
            return {'triggered': False}
        
        # Check distance from typical locations
        min_distance = float('inf')
        
        for typical_loc in profile.typical_locations:
            distance = geodesic(
                (tx_lat, tx_lon),
                (typical_loc['latitude'], typical_loc['longitude'])
            ).kilometers
            
            min_distance = min(min_distance, distance)
        
        if min_distance > settings.UNUSUAL_LOCATION_RADIUS_KM:
            score = min(35, min_distance / 10)
            return {
                'triggered': True,
                'score': score,
                'description': f'Transaction {min_distance:.1f}km from typical locations'
            }
        
        return {'triggered': False}
    
    async def _check_time_anomaly(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Check for time pattern anomalies"""
        transaction_time = datetime.now().hour
        
        if not profile.typical_transaction_times:
            return {'triggered': False}
        
        # Check if transaction time is far from typical times
        min_time_diff = min(abs(transaction_time - typical_time) for typical_time in profile.typical_transaction_times)
        
        if min_time_diff > 6:  # More than 6 hours from typical time
            return {
                'triggered': True,
                'score': min(20, min_time_diff * 2),
                'description': f'Transaction at unusual time: {transaction_time:02d}:00'
            }
        
        return {'triggered': False}
    
    async def _check_merchant_risk(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Check merchant risk factors"""
        merchant = transaction_data.get('merchant', {})
        merchant_category = merchant.get('category', '')
        
        # High-risk merchant categories
        high_risk_categories = ['gambling', 'adult_entertainment', 'cryptocurrency', 'money_transfer']
        
        if merchant_category.lower() in high_risk_categories:
            return {
                'triggered': True,
                'score': 25,
                'description': f'High-risk merchant category: {merchant_category}'
            }
        
        return {'triggered': False}
    
    async def _check_device_risk(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> Dict:
        """Check device risk factors"""
        device_data = transaction_data.get('device', {})
        device_id = device_data.get('device_id')
        
        if not device_id:
            return {
                'triggered': True,
                'score': 15,
                'description': 'No device information provided'
            }
        
        if device_id in self.device_fingerprints:
            fingerprint = self.device_fingerprints[device_id]
            
            if fingerprint.risk_score > 50:
                return {
                    'triggered': True,
                    'score': min(30, fingerprint.risk_score / 2),
                    'description': f'High-risk device (score: {fingerprint.risk_score})'
                }
        
        return {'triggered': False}
    
    def _determine_risk_and_action(self, fraud_score: float) -> Tuple[FraudRiskLevel, ActionType]:
        """Determine risk level and recommended action"""
        if fraud_score >= 80:
            return FraudRiskLevel.CRITICAL, ActionType.BLOCK
        elif fraud_score >= 60:
            return FraudRiskLevel.HIGH, ActionType.MANUAL_REVIEW
        elif fraud_score >= 40:
            return FraudRiskLevel.MEDIUM, ActionType.CHALLENGE
        elif fraud_score >= 20:
            return FraudRiskLevel.LOW, ActionType.ALLOW
        else:
            return FraudRiskLevel.LOW, ActionType.ALLOW
    
    async def _create_fraud_alert(self, customer_id: str, account_id: str, transaction_id: str,
                                 fraud_score: float, risk_level: FraudRiskLevel,
                                 triggered_rules: List[str], transaction_data: Dict,
                                 action: ActionType) -> str:
        """Create a fraud alert"""
        alert_id = str(uuid.uuid4())
        
        # Determine primary alert type
        alert_type = FraudAlertType.PATTERN
        if 'VELOCITY_CHECK' in triggered_rules:
            alert_type = FraudAlertType.VELOCITY
        elif 'AMOUNT_ANOMALY' in triggered_rules:
            alert_type = FraudAlertType.AMOUNT
        elif 'LOCATION_ANOMALY' in triggered_rules:
            alert_type = FraudAlertType.LOCATION
        elif 'DEVICE_RISK' in triggered_rules:
            alert_type = FraudAlertType.DEVICE
        
        alert = FraudAlert(
            alert_id=alert_id,
            customer_id=customer_id,
            account_id=account_id,
            transaction_id=transaction_id,
            alert_type=alert_type,
            risk_score=fraud_score,
            risk_level=risk_level,
            description=f"Fraud alert triggered with score {fraud_score}",
            triggered_rules=triggered_rules,
            transaction_data=transaction_data,
            device_data=transaction_data.get('device'),
            location_data=transaction_data.get('location'),
            created_at=datetime.now(),
            action_taken=action,
            reviewed_by=None,
            resolved_at=None,
            false_positive=None
        )
        
        self.alerts[alert_id] = alert
        
        logger.warning(f"Fraud alert created: {alert_id} for customer {customer_id} with score {fraud_score}")
        
        return alert_id
    
    def _generate_device_fingerprint(self, device_data: Dict) -> str:
        """Generate device fingerprint hash"""
        fingerprint_data = f"{device_data.get('user_agent', '')}{device_data.get('screen_resolution', '')}{device_data.get('timezone', '')}{device_data.get('language', '')}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    async def _calculate_device_risk(self, device_data: Dict, customer_id: str) -> float:
        """Calculate risk score for new device"""
        risk_score = 0.0
        
        # Check if IP is from high-risk country
        ip_address = device_data.get('ip_address', '')
        if self._is_high_risk_ip(ip_address):
            risk_score += 30
        
        # Check if device characteristics are suspicious
        user_agent = device_data.get('user_agent', '')
        if not user_agent or len(user_agent) < 50:
            risk_score += 20
        
        # Check timezone consistency
        timezone = device_data.get('timezone', '')
        if not timezone:
            risk_score += 15
        
        # New device penalty
        risk_score += 10
        
        return min(100, risk_score)
    
    def _is_high_risk_ip(self, ip_address: str) -> bool:
        """Check if IP address is from high-risk location"""
        # Mock implementation - would use actual IP geolocation service
        high_risk_ips = ['192.168.1.100']  # Mock high-risk IPs
        return ip_address in high_risk_ips
    
    async def _get_or_create_customer_profile(self, customer_id: str) -> CustomerBehaviorProfile:
        """Get or create customer behavior profile"""
        if customer_id not in self.customer_profiles:
            # Create new profile with defaults
            profile = CustomerBehaviorProfile(
                customer_id=customer_id,
                typical_transaction_amount=100.0,
                typical_transaction_times=[9, 12, 15, 18],  # Common transaction hours
                typical_locations=[],
                typical_merchants=[],
                typical_transaction_frequency=2.0,
                spending_categories={},
                device_fingerprints=[],
                last_updated=datetime.now()
            )
            
            self.customer_profiles[customer_id] = profile
        
        return self.customer_profiles[customer_id]
    
    async def _update_customer_profile(self, customer_id: str, transaction_data: Dict):
        """Update customer behavior profile"""
        profile = self.customer_profiles[customer_id]
        
        amount = float(transaction_data.get('amount', 0))
        transaction_time = datetime.now().hour
        
        # Update typical transaction amount (moving average)
        if profile.typical_transaction_amount > 0:
            profile.typical_transaction_amount = (profile.typical_transaction_amount * 0.9) + (amount * 0.1)
        else:
            profile.typical_transaction_amount = amount
        
        # Update typical transaction times
        if transaction_time not in profile.typical_transaction_times:
            profile.typical_transaction_times.append(transaction_time)
            profile.typical_transaction_times = profile.typical_transaction_times[-10:]  # Keep last 10
        
        # Update location if provided
        location = transaction_data.get('location')
        if location and location.get('latitude') and location.get('longitude'):
            profile.typical_locations.append(location)
            profile.typical_locations = profile.typical_locations[-5:]  # Keep last 5
        
        # Update merchant if provided
        merchant = transaction_data.get('merchant', {}).get('name')
        if merchant and merchant not in profile.typical_merchants:
            profile.typical_merchants.append(merchant)
            profile.typical_merchants = profile.typical_merchants[-20:]  # Keep last 20
        
        profile.last_updated = datetime.now()
    
    def _initialize_ml_model(self):
        """Initialize ML model for fraud detection"""
        # Mock ML model - in production would use actual trained model
        return {
            'model_type': 'random_forest',
            'version': '1.0',
            'last_trained': datetime.now()
        }
    
    async def _get_ml_fraud_score(self, transaction_data: Dict, profile: CustomerBehaviorProfile) -> float:
        """Get fraud score from ML model"""
        # Mock ML prediction - would use actual model
        import random
        base_score = random.uniform(0, 20)
        
        # Adjust based on transaction characteristics
        amount = float(transaction_data.get('amount', 0))
        if amount > 1000:
            base_score += random.uniform(0, 10)
        
        return base_score
    
    async def _update_ml_model_feedback(self, alert: FraudAlert, negative: bool):
        """Update ML model with feedback"""
        # Mock implementation - would retrain model with feedback
        logger.info(f"ML model feedback: Alert {alert.alert_id} marked as {'false positive' if negative else 'true positive'}")
    
    def _get_recommendation(self, action: ActionType, fraud_score: float) -> str:
        """Get recommendation based on action and score"""
        if action == ActionType.BLOCK:
            return f"Block transaction due to high fraud risk (score: {fraud_score})"
        elif action == ActionType.CHALLENGE:
            return f"Challenge customer with additional authentication (score: {fraud_score})"
        elif action == ActionType.MANUAL_REVIEW:
            return f"Flag for manual review by fraud team (score: {fraud_score})"
        else:
            return f"Allow transaction - low fraud risk (score: {fraud_score})"
    
    async def _continuous_monitoring(self):
        """Continuous background monitoring for fraud patterns"""
        while self.monitoring_active:
            try:
                # Check for account takeover patterns
                await self._check_account_takeover_patterns()
                
                # Update ML model if needed
                await self._check_model_updates()
                
                # Clean old data
                await self._cleanup_old_data()
                
                await asyncio.sleep(300)  # Run every 5 minutes
            
            except Exception as e:
                logger.error(f"Error in continuous fraud monitoring: {e}")
                await asyncio.sleep(300)
    
    async def _check_account_takeover_patterns(self):
        """Check for account takeover patterns"""
        # Look for suspicious device/location combinations
        for customer_id, profile in self.customer_profiles.items():
            # Mock analysis - would implement actual pattern detection
            pass
    
    async def _check_model_updates(self):
        """Check if ML model needs updating"""
        # Mock implementation - would check if model needs retraining
        pass
    
    async def _cleanup_old_data(self):
        """Clean up old fraud data"""
        cutoff_date = datetime.now() - timedelta(days=90)
        
        # Remove old alerts
        old_alerts = [
            alert_id for alert_id, alert in self.alerts.items()
            if alert.created_at < cutoff_date and alert.resolved_at is not None
        ]
        
        for alert_id in old_alerts:
            del self.alerts[alert_id]
        
        logger.info(f"Cleaned up {len(old_alerts)} old fraud alerts")