import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

class PaymentFailureReason(Enum):
    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    INVALID_CARD = "invalid_card"
    DECLINED_BY_BANK = "declined_by_bank"
    FRAUD_SUSPECTED = "fraud_suspected"
    PROCESSING_ERROR = "processing_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_FAILED = "authentication_failed"

class RecoveryStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    ABANDONED = "abandoned"
    MANUAL_INTERVENTION = "manual_intervention"

@dataclass
class PaymentFailure:
    failure_id: str
    customer_id: str
    amount: float
    currency: str
    failure_reason: PaymentFailureReason
    failure_timestamp: str
    subscription_id: Optional[str]
    invoice_id: Optional[str]
    payment_method_id: str
    retry_count: int
    recovery_status: RecoveryStatus
    next_retry_at: Optional[str]

@dataclass
class RecoveryStrategy:
    strategy_name: str
    trigger_conditions: Dict
    actions: List[Dict]
    success_rate: float
    average_recovery_time: float
    cost_per_recovery: float

class PaymentRecoveryService:
    def __init__(self):
        self.failed_payments = {}
        self.recovery_campaigns = {}
        self.recovery_strategies = self._initialize_recovery_strategies()
        self.max_retry_attempts = settings.PAYMENT_RETRY_ATTEMPTS
        self.retry_delay_hours = settings.PAYMENT_RETRY_DELAY_HOURS
        
    def _initialize_recovery_strategies(self) -> Dict[str, RecoveryStrategy]:
        """Initialize default recovery strategies"""
        strategies = {
            'immediate_retry': RecoveryStrategy(
                strategy_name='immediate_retry',
                trigger_conditions={'failure_reasons': ['network_error', 'processing_error']},
                actions=[
                    {'type': 'automatic_retry', 'delay_minutes': 5},
                    {'type': 'automatic_retry', 'delay_minutes': 30},
                    {'type': 'automatic_retry', 'delay_hours': 2}
                ],
                success_rate=0.65,
                average_recovery_time=2.5,
                cost_per_recovery=0.50
            ),
            'card_update_campaign': RecoveryStrategy(
                strategy_name='card_update_campaign',
                trigger_conditions={'failure_reasons': ['expired_card', 'invalid_card']},
                actions=[
                    {'type': 'send_email', 'template': 'card_update_request'},
                    {'type': 'send_sms', 'delay_hours': 24},
                    {'type': 'in_app_notification'},
                    {'type': 'phone_call', 'delay_days': 3}
                ],
                success_rate=0.45,
                average_recovery_time=48.0,
                cost_per_recovery=2.75
            ),
            'dunning_sequence': RecoveryStrategy(
                strategy_name='dunning_sequence',
                trigger_conditions={'failure_reasons': ['insufficient_funds', 'declined_by_bank']},
                actions=[
                    {'type': 'grace_period', 'days': 3},
                    {'type': 'send_email', 'template': 'payment_failure_notice'},
                    {'type': 'retry_payment', 'delay_days': 3},
                    {'type': 'send_email', 'template': 'account_suspension_warning', 'delay_days': 7},
                    {'type': 'retry_payment', 'delay_days': 10},
                    {'type': 'account_suspension', 'delay_days': 14}
                ],
                success_rate=0.35,
                average_recovery_time=168.0,
                cost_per_recovery=1.20
            ),
            'fraud_recovery': RecoveryStrategy(
                strategy_name='fraud_recovery',
                trigger_conditions={'failure_reasons': ['fraud_suspected', 'authentication_failed']},
                actions=[
                    {'type': 'send_email', 'template': 'fraud_alert_verification'},
                    {'type': 'require_manual_verification'},
                    {'type': 'phone_verification', 'delay_hours': 4},
                    {'type': 'alternative_payment_method'}
                ],
                success_rate=0.25,
                average_recovery_time=72.0,
                cost_per_recovery=8.50
            )
        }
        return strategies
    
    async def record_payment_failure(self, 
                                   customer_id: str,
                                   amount: float,
                                   failure_reason: str,
                                   payment_method_id: str,
                                   subscription_id: str = None,
                                   invoice_id: str = None) -> Dict:
        """Record a payment failure and initiate recovery process"""
        try:
            failure_id = str(uuid.uuid4())
            
            payment_failure = PaymentFailure(
                failure_id=failure_id,
                customer_id=customer_id,
                amount=amount,
                currency='USD',
                failure_reason=PaymentFailureReason(failure_reason),
                failure_timestamp=datetime.now().isoformat(),
                subscription_id=subscription_id,
                invoice_id=invoice_id,
                payment_method_id=payment_method_id,
                retry_count=0,
                recovery_status=RecoveryStatus.PENDING,
                next_retry_at=None
            )
            
            self.failed_payments[failure_id] = payment_failure
            
            # Determine and initiate recovery strategy
            recovery_strategy = await self._select_recovery_strategy(payment_failure)
            recovery_result = await self._initiate_recovery_campaign(payment_failure, recovery_strategy)
            
            logger.info(f"Recorded payment failure {failure_id} for customer {customer_id}, amount ${amount}")
            
            return {
                'success': True,
                'failure_id': failure_id,
                'recovery_strategy': recovery_strategy.strategy_name if recovery_strategy else None,
                'recovery_initiated': recovery_result['success'] if recovery_result else False
            }
        
        except Exception as e:
            logger.error(f"Error recording payment failure: {e}")
            return {'success': False, 'error': str(e)}
    
    async def retry_failed_payment(self, failure_id: str) -> Dict:
        """Manually or automatically retry a failed payment"""
        try:
            if failure_id not in self.failed_payments:
                return {'success': False, 'error': 'Payment failure not found'}
            
            payment_failure = self.failed_payments[failure_id]
            
            if payment_failure.retry_count >= self.max_retry_attempts:
                return {'success': False, 'error': 'Maximum retry attempts exceeded'}
            
            # Simulate payment retry
            retry_success = await self._attempt_payment_retry(payment_failure)
            
            payment_failure.retry_count += 1
            
            if retry_success:
                payment_failure.recovery_status = RecoveryStatus.SUCCESSFUL
                
                # Log successful recovery
                await self._log_successful_recovery(payment_failure)
                
                return {
                    'success': True,
                    'failure_id': failure_id,
                    'recovery_status': 'successful',
                    'retry_count': payment_failure.retry_count,
                    'amount_recovered': payment_failure.amount
                }
            else:
                # Schedule next retry if attempts remaining
                if payment_failure.retry_count < self.max_retry_attempts:
                    next_retry = datetime.now() + timedelta(hours=self.retry_delay_hours * payment_failure.retry_count)
                    payment_failure.next_retry_at = next_retry.isoformat()
                    payment_failure.recovery_status = RecoveryStatus.IN_PROGRESS
                else:
                    payment_failure.recovery_status = RecoveryStatus.FAILED
                
                return {
                    'success': False,
                    'failure_id': failure_id,
                    'recovery_status': payment_failure.recovery_status.value,
                    'retry_count': payment_failure.retry_count,
                    'next_retry_at': payment_failure.next_retry_at
                }
        
        except Exception as e:
            logger.error(f"Error retrying failed payment: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_recovery_analytics(self, time_period_days: int = 30) -> Dict:
        """Get comprehensive analytics on payment recovery performance"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)
            
            # Filter failures in time period
            period_failures = [
                failure for failure in self.failed_payments.values()
                if start_date <= datetime.fromisoformat(failure.failure_timestamp) <= end_date
            ]
            
            if not period_failures:
                return {
                    'success': True,
                    'message': 'No payment failures in specified period',
                    'analytics': {}
                }
            
            # Calculate basic metrics
            total_failures = len(period_failures)
            successful_recoveries = len([f for f in period_failures if f.recovery_status == RecoveryStatus.SUCCESSFUL])
            failed_recoveries = len([f for f in period_failures if f.recovery_status == RecoveryStatus.FAILED])
            pending_recoveries = len([f for f in period_failures if f.recovery_status in [RecoveryStatus.PENDING, RecoveryStatus.IN_PROGRESS]])
            
            # Calculate financial metrics
            total_failed_amount = sum(f.amount for f in period_failures)
            recovered_amount = sum(f.amount for f in period_failures if f.recovery_status == RecoveryStatus.SUCCESSFUL)
            at_risk_amount = sum(f.amount for f in period_failures if f.recovery_status in [RecoveryStatus.PENDING, RecoveryStatus.IN_PROGRESS])
            
            # Calculate rates
            recovery_rate = successful_recoveries / max(total_failures, 1)
            recovery_amount_rate = recovered_amount / max(total_failed_amount, 1)
            
            # Analyze failure reasons
            failure_reasons = {}
            for failure in period_failures:
                reason = failure.failure_reason.value
                if reason not in failure_reasons:
                    failure_reasons[reason] = {'count': 0, 'amount': 0, 'recovered': 0}
                
                failure_reasons[reason]['count'] += 1
                failure_reasons[reason]['amount'] += failure.amount
                
                if failure.recovery_status == RecoveryStatus.SUCCESSFUL:
                    failure_reasons[reason]['recovered'] += failure.amount
            
            # Calculate recovery rates by reason
            for reason, data in failure_reasons.items():
                data['recovery_rate'] = data['recovered'] / max(data['amount'], 1)
            
            # Strategy performance analysis
            strategy_performance = await self._analyze_strategy_performance(period_failures)
            
            return {
                'success': True,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': time_period_days
                },
                'overview': {
                    'total_failures': total_failures,
                    'successful_recoveries': successful_recoveries,
                    'failed_recoveries': failed_recoveries,
                    'pending_recoveries': pending_recoveries,
                    'recovery_rate': recovery_rate,
                    'total_failed_amount': total_failed_amount,
                    'recovered_amount': recovered_amount,
                    'at_risk_amount': at_risk_amount,
                    'recovery_amount_rate': recovery_amount_rate
                },
                'failure_reasons': failure_reasons,
                'strategy_performance': strategy_performance
            }
        
        except Exception as e:
            logger.error(f"Error getting recovery analytics: {e}")
            return {'success': False, 'error': str(e)}
    
    async def optimize_recovery_strategies(self) -> Dict:
        """Optimize recovery strategies based on historical performance"""
        try:
            all_failures = list(self.failed_payments.values())
            
            if not all_failures:
                return {'success': False, 'error': 'No historical data available'}
            
            optimization_recommendations = []
            
            # Analyze each strategy performance
            for strategy_name, strategy in self.recovery_strategies.items():
                strategy_failures = [
                    f for f in all_failures 
                    if f.failure_reason.value in strategy.trigger_conditions.get('failure_reasons', [])
                ]
                
                if strategy_failures:
                    actual_success_rate = len([f for f in strategy_failures if f.recovery_status == RecoveryStatus.SUCCESSFUL]) / len(strategy_failures)
                    
                    # Compare with expected success rate
                    performance_ratio = actual_success_rate / max(strategy.success_rate, 0.01)
                    
                    if performance_ratio < 0.8:  # Underperforming
                        optimization_recommendations.append({
                            'strategy': strategy_name,
                            'issue': 'underperforming',
                            'expected_success_rate': strategy.success_rate,
                            'actual_success_rate': actual_success_rate,
                            'recommendation': 'Review and optimize strategy actions',
                            'priority': 'high' if performance_ratio < 0.5 else 'medium'
                        })
                    elif performance_ratio > 1.2:  # Overperforming
                        optimization_recommendations.append({
                            'strategy': strategy_name,
                            'issue': 'overperforming',
                            'expected_success_rate': strategy.success_rate,
                            'actual_success_rate': actual_success_rate,
                            'recommendation': 'Consider expanding strategy or reducing costs',
                            'priority': 'low'
                        })
            
            # Identify optimal timing for retries
            timing_analysis = await self._analyze_optimal_retry_timing()
            
            # Generate new strategy recommendations
            new_strategies = await self._generate_new_strategy_recommendations(all_failures)
            
            return {
                'success': True,
                'current_strategies': len(self.recovery_strategies),
                'optimization_recommendations': optimization_recommendations,
                'timing_analysis': timing_analysis,
                'new_strategy_suggestions': new_strategies
            }
        
        except Exception as e:
            logger.error(f"Error optimizing recovery strategies: {e}")
            return {'success': False, 'error': str(e)}
    
    async def schedule_recovery_actions(self) -> Dict:
        """Schedule and execute pending recovery actions"""
        try:
            current_time = datetime.now()
            actions_executed = []
            
            for failure_id, payment_failure in self.failed_payments.items():
                if payment_failure.recovery_status != RecoveryStatus.IN_PROGRESS:
                    continue
                
                # Check if it's time for next retry
                if (payment_failure.next_retry_at and 
                    datetime.fromisoformat(payment_failure.next_retry_at) <= current_time):
                    
                    retry_result = await self.retry_failed_payment(failure_id)
                    actions_executed.append({
                        'failure_id': failure_id,
                        'action': 'automatic_retry',
                        'result': retry_result
                    })
            
            return {
                'success': True,
                'actions_executed': len(actions_executed),
                'details': actions_executed
            }
        
        except Exception as e:
            logger.error(f"Error scheduling recovery actions: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _select_recovery_strategy(self, payment_failure: PaymentFailure) -> Optional[RecoveryStrategy]:
        """Select the most appropriate recovery strategy for a payment failure"""
        failure_reason = payment_failure.failure_reason.value
        
        # Find strategies that match the failure reason
        matching_strategies = []
        
        for strategy in self.recovery_strategies.values():
            if failure_reason in strategy.trigger_conditions.get('failure_reasons', []):
                matching_strategies.append(strategy)
        
        if not matching_strategies:
            return None
        
        # Select strategy with highest success rate
        return max(matching_strategies, key=lambda s: s.success_rate)
    
    async def _initiate_recovery_campaign(self, payment_failure: PaymentFailure, strategy: RecoveryStrategy) -> Dict:
        """Initiate a recovery campaign based on the selected strategy"""
        if not strategy:
            return {'success': False, 'error': 'No strategy provided'}
        
        campaign_id = str(uuid.uuid4())
        
        campaign_data = {
            'campaign_id': campaign_id,
            'failure_id': payment_failure.failure_id,
            'strategy_name': strategy.strategy_name,
            'initiated_at': datetime.now().isoformat(),
            'actions': strategy.actions,
            'status': 'active'
        }
        
        self.recovery_campaigns[campaign_id] = campaign_data
        
        # Schedule first action
        if strategy.actions:
            first_action = strategy.actions[0]
            await self._execute_recovery_action(payment_failure, first_action)
        
        payment_failure.recovery_status = RecoveryStatus.IN_PROGRESS
        
        return {'success': True, 'campaign_id': campaign_id}
    
    async def _execute_recovery_action(self, payment_failure: PaymentFailure, action: Dict):
        """Execute a specific recovery action"""
        action_type = action.get('type')
        
        if action_type == 'automatic_retry':
            delay = action.get('delay_minutes', 0) + action.get('delay_hours', 0) * 60
            next_retry = datetime.now() + timedelta(minutes=delay)
            payment_failure.next_retry_at = next_retry.isoformat()
            
        elif action_type == 'send_email':
            template = action.get('template')
            await self._send_recovery_email(payment_failure.customer_id, template)
            
        elif action_type == 'send_sms':
            await self._send_recovery_sms(payment_failure.customer_id)
            
        elif action_type == 'phone_call':
            await self._schedule_recovery_call(payment_failure.customer_id)
            
        logger.info(f"Executed recovery action {action_type} for failure {payment_failure.failure_id}")
    
    async def _attempt_payment_retry(self, payment_failure: PaymentFailure) -> bool:
        """Simulate payment retry attempt"""
        # Mock implementation - would integrate with actual payment processor
        failure_reason = payment_failure.failure_reason
        
        # Different success rates based on failure reason
        success_rates = {
            PaymentFailureReason.NETWORK_ERROR: 0.8,
            PaymentFailureReason.PROCESSING_ERROR: 0.7,
            PaymentFailureReason.INSUFFICIENT_FUNDS: 0.3,
            PaymentFailureReason.EXPIRED_CARD: 0.1,
            PaymentFailureReason.INVALID_CARD: 0.1,
            PaymentFailureReason.DECLINED_BY_BANK: 0.2,
            PaymentFailureReason.FRAUD_SUSPECTED: 0.1,
            PaymentFailureReason.AUTHENTICATION_FAILED: 0.15
        }
        
        success_rate = success_rates.get(failure_reason, 0.3)
        return np.random.random() < success_rate
    
    async def _send_recovery_email(self, customer_id: str, template: str):
        """Send recovery email to customer"""
        logger.info(f"Sending recovery email (template: {template}) to customer {customer_id}")
        # Mock implementation - would integrate with email service
    
    async def _send_recovery_sms(self, customer_id: str):
        """Send recovery SMS to customer"""
        logger.info(f"Sending recovery SMS to customer {customer_id}")
        # Mock implementation - would integrate with SMS service
    
    async def _schedule_recovery_call(self, customer_id: str):
        """Schedule recovery call for customer"""
        logger.info(f"Scheduling recovery call for customer {customer_id}")
        # Mock implementation - would integrate with call scheduling system
    
    async def _log_successful_recovery(self, payment_failure: PaymentFailure):
        """Log successful payment recovery"""
        logger.info(f"Payment recovery successful - Failure ID: {payment_failure.failure_id}, Amount: ${payment_failure.amount}")
        
        # Update metrics and send notifications
        # Mock implementation
    
    async def _analyze_strategy_performance(self, failures: List[PaymentFailure]) -> Dict:
        """Analyze performance of recovery strategies"""
        strategy_stats = {}
        
        for strategy_name, strategy in self.recovery_strategies.items():
            relevant_failures = [
                f for f in failures
                if f.failure_reason.value in strategy.trigger_conditions.get('failure_reasons', [])
            ]
            
            if relevant_failures:
                successful = len([f for f in relevant_failures if f.recovery_status == RecoveryStatus.SUCCESSFUL])
                total = len(relevant_failures)
                
                strategy_stats[strategy_name] = {
                    'total_attempts': total,
                    'successful_recoveries': successful,
                    'success_rate': successful / max(total, 1),
                    'expected_success_rate': strategy.success_rate,
                    'performance_ratio': (successful / max(total, 1)) / max(strategy.success_rate, 0.01)
                }
        
        return strategy_stats
    
    async def _analyze_optimal_retry_timing(self) -> Dict:
        """Analyze optimal timing for payment retries"""
        # Mock analysis - would analyze actual timing data
        return {
            'optimal_first_retry_hours': 2,
            'optimal_second_retry_hours': 24,
            'optimal_third_retry_hours': 72,
            'best_day_of_week': 'Tuesday',
            'best_time_of_day': '10:00 AM'
        }
    
    async def _generate_new_strategy_recommendations(self, failures: List[PaymentFailure]) -> List[Dict]:
        """Generate recommendations for new recovery strategies"""
        recommendations = []
        
        # Analyze failure patterns
        failure_reason_counts = {}
        for failure in failures:
            reason = failure.failure_reason.value
            if reason not in failure_reason_counts:
                failure_reason_counts[reason] = 0
            failure_reason_counts[reason] += 1
        
        # Suggest new strategies for common failure types with low recovery rates
        for reason, count in failure_reason_counts.items():
            if count >= 10:  # Common failure type
                relevant_failures = [f for f in failures if f.failure_reason.value == reason]
                success_rate = len([f for f in relevant_failures if f.recovery_status == RecoveryStatus.SUCCESSFUL]) / len(relevant_failures)
                
                if success_rate < 0.3:  # Low recovery rate
                    recommendations.append({
                        'failure_reason': reason,
                        'current_success_rate': success_rate,
                        'suggested_strategy': f'Enhanced {reason} recovery strategy',
                        'recommended_actions': [
                            'Implement predictive retry timing',
                            'Add personalized recovery messaging',
                            'Introduce alternative payment methods'
                        ]
                    })
        
        return recommendations