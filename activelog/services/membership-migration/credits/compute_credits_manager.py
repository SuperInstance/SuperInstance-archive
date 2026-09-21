#!/usr/bin/env python3
"""
Compute Credits Manager for ActiveLog Migration Service
Preserves and manages compute credits during membership transfers
"""

import logging
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import decimal

logger = logging.getLogger(__name__)


class CreditType(Enum):
    """Types of compute credits"""
    AI_PROCESSING = "ai_processing"
    DATA_ANALYSIS = "data_analysis"
    STORAGE = "storage"
    API_CALLS = "api_calls"
    PREMIUM_FEATURES = "premium_features"
    COLLABORATION = "collaboration"
    EXPORT_CREDITS = "export_credits"
    INTEGRATION_CALLS = "integration_calls"


class CreditStatus(Enum):
    """Credit status states"""
    ACTIVE = "active"
    RESERVED = "reserved"
    EXPIRED = "expired"
    TRANSFERRED = "transferred"
    REFUNDED = "refunded"
    PENDING_TRANSFER = "pending_transfer"


class TransferMethod(Enum):
    """Credit transfer methods"""
    DIRECT_TRANSFER = "direct_transfer"
    PROPORTIONAL_ALLOCATION = "proportional_allocation"
    FEATURE_MAPPING = "feature_mapping"
    VALUE_CONVERSION = "value_conversion"


@dataclass
class CreditBalance:
    """Credit balance data structure"""
    user_id: str
    app_id: str
    credit_type: CreditType
    balance: decimal.Decimal
    reserved_balance: decimal.Decimal
    total_earned: decimal.Decimal
    total_spent: decimal.Decimal
    last_activity: datetime
    expiry_date: Optional[datetime]
    auto_top_up_enabled: bool
    auto_top_up_threshold: decimal.Decimal
    auto_top_up_amount: decimal.Decimal


@dataclass
class CreditTransaction:
    """Credit transaction record"""
    transaction_id: str
    user_id: str
    app_id: str
    credit_type: CreditType
    amount: decimal.Decimal
    transaction_type: str  # earn, spend, transfer, refund, expire
    description: str
    reference_id: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass
class CreditPreservationPlan:
    """Plan for preserving credits during transfer"""
    user_id: str
    source_app: str
    target_app: str
    preservation_method: TransferMethod
    credit_mappings: Dict[str, Any]
    estimated_preserved_value: decimal.Decimal
    estimated_loss_percentage: float
    preservation_steps: List[str]
    risk_factors: List[str]
    created_at: datetime


class ComputeCreditsManager:
    """Manages compute credits preservation and transfer"""
    
    def __init__(self, config):
        self.config = config
        self.credit_balances = {}
        self.transaction_history = {}
        self.preservation_plans = {}
        
        # Credit conversion rates between apps
        self.conversion_rates = {
            ('activelog-core', 'studylog'): {
                CreditType.AI_PROCESSING: 0.95,
                CreditType.DATA_ANALYSIS: 1.0,
                CreditType.STORAGE: 1.0,
                CreditType.API_CALLS: 0.9,
                CreditType.PREMIUM_FEATURES: 0.8
            },
            ('activelog-core', 'businesslog'): {
                CreditType.AI_PROCESSING: 1.0,
                CreditType.DATA_ANALYSIS: 1.1,
                CreditType.STORAGE: 1.0,
                CreditType.API_CALLS: 1.0,
                CreditType.COLLABORATION: 1.2
            },
            ('studylog', 'businesslog'): {
                CreditType.AI_PROCESSING: 1.05,
                CreditType.DATA_ANALYSIS: 1.15,
                CreditType.COLLABORATION: 1.3,
                CreditType.API_CALLS: 1.1
            },
            ('makerlog', 'businesslog'): {
                CreditType.AI_PROCESSING: 0.9,
                CreditType.DATA_ANALYSIS: 1.2,
                CreditType.COLLABORATION: 1.4,
                CreditType.PREMIUM_FEATURES: 1.1
            },
            ('dmlog', 'activelog-core'): {
                CreditType.AI_PROCESSING: 0.8,
                CreditType.DATA_ANALYSIS: 0.9,
                CreditType.STORAGE: 1.0,
                CreditType.API_CALLS: 0.85
            }
        }
        
        # App-specific credit features
        self.app_credit_features = {
            'activelog-core': {
                CreditType.AI_PROCESSING: 'AI-powered search and categorization',
                CreditType.DATA_ANALYSIS: 'Advanced analytics and insights',
                CreditType.STORAGE: 'Cloud storage for entries and media',
                CreditType.API_CALLS: 'External API integrations',
                CreditType.EXPORT_CREDITS: 'Data export in various formats'
            },
            'studylog': {
                CreditType.AI_PROCESSING: 'Study pattern analysis and recommendations',
                CreditType.DATA_ANALYSIS: 'Learning progress analytics',
                CreditType.COLLABORATION: 'Study group features',
                CreditType.PREMIUM_FEATURES: 'Advanced study tools'
            },
            'businesslog': {
                CreditType.AI_PROCESSING: 'Business intelligence and insights',
                CreditType.DATA_ANALYSIS: 'Advanced business reporting',
                CreditType.COLLABORATION: 'Team collaboration features',
                CreditType.INTEGRATION_CALLS: 'Business tool integrations',
                CreditType.PREMIUM_FEATURES: 'Enterprise features'
            },
            'makerlog': {
                CreditType.AI_PROCESSING: 'Project recommendation engine',
                CreditType.DATA_ANALYSIS: 'Progress and milestone analytics',
                CreditType.COLLABORATION: 'Community features',
                CreditType.PREMIUM_FEATURES: 'Advanced project tools'
            },
            'dmlog': {
                CreditType.AI_PROCESSING: 'Campaign and NPC generation',
                CreditType.DATA_ANALYSIS: 'Game statistics and analytics',
                CreditType.STORAGE: 'Campaign data and media storage',
                CreditType.PREMIUM_FEATURES: 'Advanced DM tools'
            }
        }
        
        logger.info("ComputeCreditsManager initialized")
    
    def preserve_credits(self, user_id: str, source_app: str, target_app: str) -> Dict[str, Any]:
        """Preserve compute credits during app migration"""
        try:
            # Get current credit balances for source app
            source_balances = self._get_credit_balances(user_id, source_app)
            
            if not source_balances:
                return {
                    'success': True,
                    'message': 'No credits to preserve',
                    'preserved_credits': {},
                    'preservation_plan_id': None
                }
            
            # Create preservation plan
            preservation_plan = self._create_preservation_plan(user_id, source_app, target_app, source_balances)
            
            # Execute credit preservation
            preservation_result = self._execute_credit_preservation(preservation_plan)
            
            # Store preservation plan
            plan_id = f"cpp_{uuid.uuid4().hex[:8]}"
            self.preservation_plans[plan_id] = preservation_plan
            
            # Record transactions
            self._record_preservation_transactions(preservation_plan, preservation_result)
            
            logger.info(f"Credits preserved for user {user_id}: {source_app} -> {target_app}")
            
            return {
                'success': True,
                'preservation_plan_id': plan_id,
                'source_app': source_app,
                'target_app': target_app,
                'preserved_credits': preservation_result['preserved_credits'],
                'total_value_preserved': float(preservation_result['total_value_preserved']),
                'preservation_efficiency': preservation_result['preservation_efficiency'],
                'conversion_summary': preservation_result['conversion_summary'],
                'next_steps': [
                    'Credits have been transferred to your target application',
                    'Auto-renewal settings have been migrated',
                    'Check your new app for updated credit balances'
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to preserve credits: {e}")
            return {
                'success': False,
                'error': str(e),
                'preserved_credits': {}
            }
    
    def get_credits_balance(self, user_id: str, app_id: str = None) -> Dict[str, Any]:
        """Get user's compute credits balance across apps or for specific app"""
        try:
            if app_id:
                # Get balance for specific app
                balances = self._get_credit_balances(user_id, app_id)
                return {
                    'user_id': user_id,
                    'app_id': app_id,
                    'balances': balances,
                    'summary': self._calculate_balance_summary(balances)
                }
            else:
                # Get balance across all apps
                all_balances = {}
                total_summary = {
                    'total_active_balance': decimal.Decimal('0'),
                    'total_reserved_balance': decimal.Decimal('0'),
                    'total_value_usd': decimal.Decimal('0'),
                    'active_apps': []
                }
                
                for app in ['activelog-core', 'studylog', 'businesslog', 'makerlog', 'dmlog']:
                    app_balances = self._get_credit_balances(user_id, app)
                    if app_balances:
                        all_balances[app] = app_balances
                        app_summary = self._calculate_balance_summary(app_balances)
                        total_summary['total_active_balance'] += app_summary['total_active_balance']
                        total_summary['total_reserved_balance'] += app_summary['total_reserved_balance']
                        total_summary['total_value_usd'] += app_summary['total_value_usd']
                        total_summary['active_apps'].append(app)
                
                return {
                    'user_id': user_id,
                    'all_apps_balances': all_balances,
                    'summary': {
                        'total_active_balance': float(total_summary['total_active_balance']),
                        'total_reserved_balance': float(total_summary['total_reserved_balance']),
                        'total_value_usd': float(total_summary['total_value_usd']),
                        'active_apps': total_summary['active_apps'],
                        'last_updated': datetime.utcnow().isoformat()
                    },
                    'recommendations': self._get_credit_optimization_recommendations(user_id, all_balances)
                }
                
        except Exception as e:
            logger.error(f"Failed to get credits balance: {e}")
            return {'error': str(e)}
    
    def _get_credit_balances(self, user_id: str, app_id: str) -> Dict[str, Any]:
        """Get credit balances for user in specific app"""
        # Simulate getting balances from database
        if app_id == 'activelog-core':
            return {
                CreditType.AI_PROCESSING.value: {
                    'balance': 250.75,
                    'reserved': 25.0,
                    'last_activity': (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    'expiry_date': (datetime.utcnow() + timedelta(days=365)).isoformat()
                },
                CreditType.DATA_ANALYSIS.value: {
                    'balance': 180.50,
                    'reserved': 15.0,
                    'last_activity': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    'expiry_date': (datetime.utcnow() + timedelta(days=365)).isoformat()
                },
                CreditType.STORAGE.value: {
                    'balance': 500.0,
                    'reserved': 50.0,
                    'last_activity': (datetime.utcnow() - timedelta(hours=6)).isoformat(),
                    'expiry_date': None  # No expiry for storage credits
                },
                CreditType.API_CALLS.value: {
                    'balance': 95.25,
                    'reserved': 10.0,
                    'last_activity': (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                    'expiry_date': (datetime.utcnow() + timedelta(days=90)).isoformat()
                }
            }
        elif app_id == 'studylog':
            return {
                CreditType.AI_PROCESSING.value: {
                    'balance': 120.0,
                    'reserved': 12.0,
                    'last_activity': (datetime.utcnow() - timedelta(days=3)).isoformat(),
                    'expiry_date': (datetime.utcnow() + timedelta(days=365)).isoformat()
                },
                CreditType.COLLABORATION.value: {
                    'balance': 75.5,
                    'reserved': 5.0,
                    'last_activity': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    'expiry_date': (datetime.utcnow() + timedelta(days=180)).isoformat()
                }
            }
        else:
            return {}
    
    def _create_preservation_plan(self, user_id: str, source_app: str, target_app: str, 
                                source_balances: Dict[str, Any]) -> CreditPreservationPlan:
        """Create a plan for preserving credits"""
        
        # Determine preservation method
        preservation_method = self._determine_preservation_method(source_app, target_app)
        
        # Create credit mappings
        credit_mappings = self._create_credit_mappings(source_app, target_app, source_balances)
        
        # Calculate estimated preserved value
        estimated_value, loss_percentage = self._calculate_preservation_value(source_balances, credit_mappings)
        
        # Identify preservation steps
        steps = self._get_preservation_steps(preservation_method, credit_mappings)
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(source_app, target_app, source_balances)
        
        return CreditPreservationPlan(
            user_id=user_id,
            source_app=source_app,
            target_app=target_app,
            preservation_method=preservation_method,
            credit_mappings=credit_mappings,
            estimated_preserved_value=estimated_value,
            estimated_loss_percentage=loss_percentage,
            preservation_steps=steps,
            risk_factors=risk_factors,
            created_at=datetime.utcnow()
        )
    
    def _determine_preservation_method(self, source_app: str, target_app: str) -> TransferMethod:
        """Determine the best preservation method for the app combination"""
        conversion_key = (source_app, target_app)
        
        if conversion_key in self.conversion_rates:
            return TransferMethod.DIRECT_TRANSFER
        elif self._apps_have_similar_features(source_app, target_app):
            return TransferMethod.FEATURE_MAPPING
        else:
            return TransferMethod.VALUE_CONVERSION
    
    def _create_credit_mappings(self, source_app: str, target_app: str, 
                              source_balances: Dict[str, Any]) -> Dict[str, Any]:
        """Create mappings for credit conversion"""
        mappings = {}
        conversion_key = (source_app, target_app)
        
        if conversion_key in self.conversion_rates:
            conversion_rates = self.conversion_rates[conversion_key]
            
            for credit_type_str, balance_info in source_balances.items():
                credit_type = CreditType(credit_type_str)
                
                if credit_type in conversion_rates:
                    mappings[credit_type_str] = {
                        'target_credit_type': credit_type_str,
                        'conversion_rate': conversion_rates[credit_type],
                        'source_balance': balance_info['balance'],
                        'target_balance': balance_info['balance'] * conversion_rates[credit_type],
                        'method': 'direct_conversion'
                    }
                else:
                    # Use value conversion for unmapped credits
                    usd_value = self._calculate_credit_usd_value(credit_type, balance_info['balance'])
                    target_credits = self._convert_usd_to_target_credits(target_app, usd_value)
                    
                    mappings[credit_type_str] = {
                        'target_credit_type': 'ai_processing',  # Default fallback
                        'conversion_rate': target_credits / balance_info['balance'],
                        'source_balance': balance_info['balance'],
                        'target_balance': target_credits,
                        'method': 'value_conversion',
                        'usd_value': usd_value
                    }
        else:
            # Feature-based mapping for unsupported combinations
            for credit_type_str, balance_info in source_balances.items():
                mapped_type = self._map_credit_type_by_features(credit_type_str, source_app, target_app)
                conversion_rate = self._estimate_conversion_rate(credit_type_str, mapped_type, source_app, target_app)
                
                mappings[credit_type_str] = {
                    'target_credit_type': mapped_type,
                    'conversion_rate': conversion_rate,
                    'source_balance': balance_info['balance'],
                    'target_balance': balance_info['balance'] * conversion_rate,
                    'method': 'feature_mapping'
                }
        
        return mappings
    
    def _execute_credit_preservation(self, plan: CreditPreservationPlan) -> Dict[str, Any]:
        """Execute the credit preservation plan"""
        preserved_credits = {}
        total_preserved_value = decimal.Decimal('0')
        conversion_details = []
        
        for source_type, mapping in plan.credit_mappings.items():
            # Calculate preserved amount
            preserved_amount = decimal.Decimal(str(mapping['target_balance']))
            target_type = mapping['target_credit_type']
            
            # Store preserved credits
            if target_type not in preserved_credits:
                preserved_credits[target_type] = decimal.Decimal('0')
            
            preserved_credits[target_type] += preserved_amount
            total_preserved_value += self._calculate_credit_usd_value(
                CreditType(target_type), preserved_amount
            )
            
            conversion_details.append({
                'source_type': source_type,
                'target_type': target_type,
                'source_amount': mapping['source_balance'],
                'preserved_amount': float(preserved_amount),
                'conversion_rate': mapping['conversion_rate'],
                'method': mapping['method']
            })
        
        # Calculate preservation efficiency
        original_value = sum(
            self._calculate_credit_usd_value(CreditType(ct), decimal.Decimal(str(mapping['source_balance'])))
            for ct, mapping in plan.credit_mappings.items()
        )
        preservation_efficiency = float(total_preserved_value / original_value * 100) if original_value > 0 else 0
        
        return {
            'preserved_credits': {ct: float(amount) for ct, amount in preserved_credits.items()},
            'total_value_preserved': total_preserved_value,
            'preservation_efficiency': preservation_efficiency,
            'conversion_summary': conversion_details
        }
    
    def _record_preservation_transactions(self, plan: CreditPreservationPlan, result: Dict[str, Any]):
        """Record preservation transactions for audit trail"""
        for conversion in result['conversion_summary']:
            # Record debit from source app
            debit_transaction = CreditTransaction(
                transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
                user_id=plan.user_id,
                app_id=plan.source_app,
                credit_type=CreditType(conversion['source_type']),
                amount=-decimal.Decimal(str(conversion['source_amount'])),
                transaction_type='transfer_out',
                description=f"Credit transfer to {plan.target_app}",
                reference_id=None,
                created_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
                metadata={
                    'preservation_plan_id': id(plan),
                    'target_app': plan.target_app,
                    'conversion_rate': conversion['conversion_rate']
                }
            )
            
            # Record credit to target app
            credit_transaction = CreditTransaction(
                transaction_id=f"txn_{uuid.uuid4().hex[:8]}",
                user_id=plan.user_id,
                app_id=plan.target_app,
                credit_type=CreditType(conversion['target_type']),
                amount=decimal.Decimal(str(conversion['preserved_amount'])),
                transaction_type='transfer_in',
                description=f"Credit transfer from {plan.source_app}",
                reference_id=None,
                created_at=datetime.utcnow(),
                processed_at=datetime.utcnow(),
                metadata={
                    'preservation_plan_id': id(plan),
                    'source_app': plan.source_app,
                    'conversion_rate': conversion['conversion_rate']
                }
            )
            
            # Store transactions
            if plan.user_id not in self.transaction_history:
                self.transaction_history[plan.user_id] = []
            
            self.transaction_history[plan.user_id].extend([
                asdict(debit_transaction),
                asdict(credit_transaction)
            ])
    
    def _calculate_balance_summary(self, balances: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics for credit balances"""
        total_active = decimal.Decimal('0')
        total_reserved = decimal.Decimal('0')
        total_value = decimal.Decimal('0')
        expiring_soon = []
        
        for credit_type_str, balance_info in balances.items():
            credit_type = CreditType(credit_type_str)
            active_balance = decimal.Decimal(str(balance_info['balance']))
            reserved_balance = decimal.Decimal(str(balance_info['reserved']))
            
            total_active += active_balance
            total_reserved += reserved_balance
            
            # Calculate USD value
            usd_value = self._calculate_credit_usd_value(credit_type, active_balance + reserved_balance)
            total_value += usd_value
            
            # Check for credits expiring within 30 days
            if balance_info.get('expiry_date'):
                expiry_date = datetime.fromisoformat(balance_info['expiry_date'].replace('Z', '+00:00'))
                if expiry_date <= datetime.utcnow() + timedelta(days=30):
                    expiring_soon.append({
                        'credit_type': credit_type_str,
                        'balance': float(active_balance),
                        'expiry_date': balance_info['expiry_date']
                    })
        
        return {
            'total_active_balance': float(total_active),
            'total_reserved_balance': float(total_reserved),
            'total_balance': float(total_active + total_reserved),
            'total_value_usd': float(total_value),
            'expiring_soon': expiring_soon,
            'credit_types_count': len(balances)
        }
    
    def _calculate_credit_usd_value(self, credit_type: CreditType, amount: decimal.Decimal) -> decimal.Decimal:
        """Calculate USD value of credits"""
        # Simulated USD values per credit type
        usd_rates = {
            CreditType.AI_PROCESSING: decimal.Decimal('0.10'),
            CreditType.DATA_ANALYSIS: decimal.Decimal('0.08'),
            CreditType.STORAGE: decimal.Decimal('0.02'),
            CreditType.API_CALLS: decimal.Decimal('0.15'),
            CreditType.PREMIUM_FEATURES: decimal.Decimal('0.12'),
            CreditType.COLLABORATION: decimal.Decimal('0.06'),
            CreditType.EXPORT_CREDITS: decimal.Decimal('0.20'),
            CreditType.INTEGRATION_CALLS: decimal.Decimal('0.18')
        }
        
        return amount * usd_rates.get(credit_type, decimal.Decimal('0.05'))
    
    def _convert_usd_to_target_credits(self, target_app: str, usd_value: decimal.Decimal) -> float:
        """Convert USD value to target app credits"""
        # Simplified conversion - would use actual app pricing in production
        return float(usd_value * 10)  # $1 = 10 credits
    
    def _apps_have_similar_features(self, source_app: str, target_app: str) -> bool:
        """Check if apps have similar feature sets"""
        if source_app not in self.app_credit_features or target_app not in self.app_credit_features:
            return False
        
        source_features = set(self.app_credit_features[source_app].keys())
        target_features = set(self.app_credit_features[target_app].keys())
        
        overlap = len(source_features.intersection(target_features))
        total = len(source_features.union(target_features))
        
        return (overlap / total) > 0.5 if total > 0 else False
    
    def _map_credit_type_by_features(self, credit_type: str, source_app: str, target_app: str) -> str:
        """Map credit type based on feature similarity"""
        if target_app in self.app_credit_features and credit_type in [ct.value for ct in self.app_credit_features[target_app].keys()]:
            return credit_type
        
        # Default mapping logic
        if credit_type in ['ai_processing', 'data_analysis']:
            return 'ai_processing'
        elif credit_type in ['collaboration', 'premium_features']:
            return 'premium_features'
        else:
            return 'ai_processing'  # Safe default
    
    def _estimate_conversion_rate(self, source_type: str, target_type: str, 
                                source_app: str, target_app: str) -> float:
        """Estimate conversion rate for unmapped credit types"""
        # Base rate depends on feature similarity
        base_rate = 0.8 if source_type == target_type else 0.7
        
        # App-specific adjustments
        if target_app == 'businesslog':
            base_rate *= 1.1  # Business apps typically have higher credit values
        elif target_app == 'studylog':
            base_rate *= 0.9  # Student discounts apply
        
        return base_rate
    
    def _calculate_preservation_value(self, source_balances: Dict[str, Any], 
                                    mappings: Dict[str, Any]) -> Tuple[decimal.Decimal, float]:
        """Calculate total preservation value and loss percentage"""
        original_value = decimal.Decimal('0')
        preserved_value = decimal.Decimal('0')
        
        for credit_type_str, balance_info in source_balances.items():
            credit_type = CreditType(credit_type_str)
            balance = decimal.Decimal(str(balance_info['balance']))
            
            original_value += self._calculate_credit_usd_value(credit_type, balance)
            
            if credit_type_str in mappings:
                mapping = mappings[credit_type_str]
                target_credit_type = CreditType(mapping['target_credit_type'])
                target_balance = decimal.Decimal(str(mapping['target_balance']))
                
                preserved_value += self._calculate_credit_usd_value(target_credit_type, target_balance)
        
        loss_percentage = float((1 - (preserved_value / original_value)) * 100) if original_value > 0 else 0
        
        return preserved_value, loss_percentage
    
    def _get_preservation_steps(self, method: TransferMethod, mappings: Dict[str, Any]) -> List[str]:
        """Get preservation steps based on method"""
        steps = [
            "Validate source credit balances",
            "Calculate optimal conversion rates",
            "Reserve credits during transfer",
            "Execute credit conversion",
            "Verify target credit balances",
            "Update user preferences and settings"
        ]
        
        if method == TransferMethod.VALUE_CONVERSION:
            steps.insert(2, "Convert credits to USD value")
            steps.insert(3, "Calculate equivalent target credits")
        elif method == TransferMethod.FEATURE_MAPPING:
            steps.insert(2, "Map credits based on feature compatibility")
        
        return steps
    
    def _identify_risk_factors(self, source_app: str, target_app: str, 
                             source_balances: Dict[str, Any]) -> List[str]:
        """Identify risk factors for credit preservation"""
        risks = []
        
        # Check for expiring credits
        for credit_type_str, balance_info in source_balances.items():
            if balance_info.get('expiry_date'):
                expiry_date = datetime.fromisoformat(balance_info['expiry_date'].replace('Z', '+00:00'))
                if expiry_date <= datetime.utcnow() + timedelta(days=60):
                    risks.append(f"{credit_type_str} credits expire within 60 days")
        
        # Check for unsupported conversions
        conversion_key = (source_app, target_app)
        if conversion_key not in self.conversion_rates:
            risks.append("Direct conversion rates not available - using estimated rates")
        
        # Check for feature compatibility
        if not self._apps_have_similar_features(source_app, target_app):
            risks.append("Limited feature overlap may result in credit value reduction")
        
        return risks
    
    def _get_credit_optimization_recommendations(self, user_id: str, 
                                               all_balances: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get recommendations for credit optimization"""
        recommendations = []
        
        # Check for scattered credits across apps
        if len(all_balances) > 2:
            recommendations.append({
                'type': 'consolidation',
                'title': 'Consider consolidating credits',
                'description': 'You have credits across multiple apps. Consider transferring to your primary app.',
                'potential_benefit': 'Simplified management and better utilization'
            })
        
        # Check for expiring credits
        for app_id, balances in all_balances.items():
            for credit_type_str, balance_info in balances.items():
                if balance_info.get('expiry_date'):
                    expiry_date = datetime.fromisoformat(balance_info['expiry_date'].replace('Z', '+00:00'))
                    if expiry_date <= datetime.utcnow() + timedelta(days=30):
                        recommendations.append({
                            'type': 'urgent',
                            'title': f'Credits expiring soon in {app_id}',
                            'description': f'{credit_type_str} credits expire on {balance_info["expiry_date"]}',
                            'potential_benefit': 'Avoid losing unused credits'
                        })
        
        # Check for auto-top-up optimization
        total_usage = sum(
            sum(balance_info.get('balance', 0) for balance_info in balances.values())
            for balances in all_balances.values()
        )
        
        if total_usage > 500:  # High usage threshold
            recommendations.append({
                'type': 'optimization',
                'title': 'Enable auto-top-up for consistent usage',
                'description': 'Your high usage pattern suggests auto-top-up would prevent interruptions',
                'potential_benefit': 'Uninterrupted service and bulk purchase discounts'
            })
        
        return recommendations