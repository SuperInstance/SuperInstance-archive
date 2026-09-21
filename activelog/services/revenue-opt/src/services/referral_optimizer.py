import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import uuid
import logging

logger = logging.getLogger(__name__)

class ReferralStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    PAID = "paid"
    DECLINED = "declined"

class RewardType(Enum):
    CASH = "cash"
    CREDIT = "credit"
    DISCOUNT = "discount"
    FREE_MONTHS = "free_months"
    POINTS = "points"

@dataclass
class ReferralProgram:
    program_id: str
    name: str
    referrer_reward_type: RewardType
    referrer_reward_amount: float
    referee_reward_type: RewardType
    referee_reward_amount: float
    minimum_referee_spend: float
    expiry_days: int
    max_referrals_per_user: int
    is_active: bool

@dataclass
class ReferralMetrics:
    total_referrals: int
    successful_referrals: int
    conversion_rate: float
    average_referee_value: float
    total_rewards_paid: float
    roi: float
    viral_coefficient: float
    time_to_conversion: float

class ReferralOptimizer:
    def __init__(self):
        self.programs = {}
        self.referrals = {}
        self.user_referral_stats = {}
        self.default_reward = settings.DEFAULT_REFERRAL_REWARD
        self.commission_rate = settings.REFERRER_COMMISSION_RATE
    
    async def create_referral_program(self, program_config: Dict) -> Dict:
        """Create a new referral program"""
        try:
            program_id = str(uuid.uuid4())
            
            program = ReferralProgram(
                program_id=program_id,
                name=program_config['name'],
                referrer_reward_type=RewardType(program_config.get('referrer_reward_type', 'cash')),
                referrer_reward_amount=program_config.get('referrer_reward_amount', self.default_reward),
                referee_reward_type=RewardType(program_config.get('referee_reward_type', 'discount')),
                referee_reward_amount=program_config.get('referee_reward_amount', self.default_reward),
                minimum_referee_spend=program_config.get('minimum_referee_spend', 0.0),
                expiry_days=program_config.get('expiry_days', 90),
                max_referrals_per_user=program_config.get('max_referrals_per_user', 10),
                is_active=program_config.get('is_active', True)
            )
            
            self.programs[program_id] = program
            
            logger.info(f"Created referral program: {program.name} (ID: {program_id})")
            
            return {
                'success': True,
                'program_id': program_id,
                'program': program.__dict__
            }
        
        except Exception as e:
            logger.error(f"Error creating referral program: {e}")
            return {'success': False, 'error': str(e)}
    
    async def generate_referral_link(self, user_id: str, program_id: str) -> Dict:
        """Generate a unique referral link for a user"""
        try:
            if program_id not in self.programs:
                return {'success': False, 'error': 'Program not found'}
            
            program = self.programs[program_id]
            
            if not program.is_active:
                return {'success': False, 'error': 'Program is not active'}
            
            # Check user referral limits
            user_stats = self.user_referral_stats.get(user_id, {'total_referrals': 0})
            
            if user_stats['total_referrals'] >= program.max_referrals_per_user:
                return {'success': False, 'error': 'User has reached maximum referrals'}
            
            # Generate unique referral code
            referral_code = f"{user_id[:8]}_{program_id[:8]}_{str(uuid.uuid4())[:8]}"
            
            referral_link = f"https://yourapp.com/signup?ref={referral_code}"
            
            # Store referral link data
            referral_data = {
                'referral_code': referral_code,
                'referrer_id': user_id,
                'program_id': program_id,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=program.expiry_days)).isoformat(),
                'clicks': 0,
                'conversions': 0,
                'is_active': True
            }
            
            self.referrals[referral_code] = referral_data
            
            return {
                'success': True,
                'referral_code': referral_code,
                'referral_link': referral_link,
                'expires_at': referral_data['expires_at'],
                'referrer_reward': {
                    'type': program.referrer_reward_type.value,
                    'amount': program.referrer_reward_amount
                },
                'referee_reward': {
                    'type': program.referee_reward_type.value,
                    'amount': program.referee_reward_amount
                }
            }
        
        except Exception as e:
            logger.error(f"Error generating referral link: {e}")
            return {'success': False, 'error': str(e)}
    
    async def track_referral_click(self, referral_code: str) -> Dict:
        """Track a click on a referral link"""
        try:
            if referral_code not in self.referrals:
                return {'success': False, 'error': 'Invalid referral code'}
            
            referral = self.referrals[referral_code]
            
            # Check if referral is still active and not expired
            if not referral['is_active']:
                return {'success': False, 'error': 'Referral link is inactive'}
            
            expires_at = datetime.fromisoformat(referral['expires_at'])
            if datetime.now() > expires_at:
                return {'success': False, 'error': 'Referral link has expired'}
            
            # Track click
            referral['clicks'] += 1
            
            return {
                'success': True,
                'referral_code': referral_code,
                'total_clicks': referral['clicks'],
                'referrer_id': referral['referrer_id']
            }
        
        except Exception as e:
            logger.error(f"Error tracking referral click: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_referral_conversion(self, referral_code: str, referee_id: str, purchase_amount: float) -> Dict:
        """Process a successful referral conversion"""
        try:
            if referral_code not in self.referrals:
                return {'success': False, 'error': 'Invalid referral code'}
            
            referral = self.referrals[referral_code]
            program_id = referral['program_id']
            
            if program_id not in self.programs:
                return {'success': False, 'error': 'Program not found'}
            
            program = self.programs[program_id]
            
            # Check minimum spend requirement
            if purchase_amount < program.minimum_referee_spend:
                return {
                    'success': False,
                    'error': f'Purchase amount ${purchase_amount} below minimum ${program.minimum_referee_spend}'
                }
            
            # Create conversion record
            conversion_id = str(uuid.uuid4())
            conversion_data = {
                'conversion_id': conversion_id,
                'referral_code': referral_code,
                'referrer_id': referral['referrer_id'],
                'referee_id': referee_id,
                'program_id': program_id,
                'purchase_amount': purchase_amount,
                'status': ReferralStatus.PENDING.value,
                'created_at': datetime.now().isoformat(),
                'referrer_reward': {
                    'type': program.referrer_reward_type.value,
                    'amount': self._calculate_referrer_reward(program, purchase_amount)
                },
                'referee_reward': {
                    'type': program.referee_reward_type.value,
                    'amount': program.referee_reward_amount
                }
            }
            
            # Update referral stats
            referral['conversions'] += 1
            
            # Update user stats
            referrer_id = referral['referrer_id']
            if referrer_id not in self.user_referral_stats:
                self.user_referral_stats[referrer_id] = {'total_referrals': 0, 'successful_referrals': 0}
            
            self.user_referral_stats[referrer_id]['successful_referrals'] += 1
            
            # Process rewards
            reward_results = await self._process_rewards(conversion_data)
            
            logger.info(f"Processed referral conversion: {conversion_id}")
            
            return {
                'success': True,
                'conversion_id': conversion_id,
                'conversion_data': conversion_data,
                'reward_results': reward_results
            }
        
        except Exception as e:
            logger.error(f"Error processing referral conversion: {e}")
            return {'success': False, 'error': str(e)}
    
    async def calculate_program_metrics(self, program_id: str, time_period_days: int = 30) -> Dict:
        """Calculate comprehensive metrics for a referral program"""
        try:
            if program_id not in self.programs:
                return {'success': False, 'error': 'Program not found'}
            
            # Get program referrals for time period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=time_period_days)
            
            program_referrals = await self._get_program_referrals(program_id, start_date, end_date)
            
            # Calculate basic metrics
            total_referrals = len(program_referrals)
            successful_referrals = len([r for r in program_referrals if r['conversions'] > 0])
            conversion_rate = successful_referrals / max(total_referrals, 1)
            
            # Calculate financial metrics
            total_referee_value = sum(r.get('purchase_amount', 0) for r in program_referrals if r['conversions'] > 0)
            average_referee_value = total_referee_value / max(successful_referrals, 1)
            
            total_rewards_paid = await self._calculate_total_rewards_paid(program_id, start_date, end_date)
            roi = (total_referee_value - total_rewards_paid) / max(total_rewards_paid, 1) if total_rewards_paid > 0 else 0
            
            # Calculate viral coefficient
            viral_coefficient = await self._calculate_viral_coefficient(program_id)
            
            # Calculate average time to conversion
            avg_time_to_conversion = await self._calculate_avg_time_to_conversion(program_id)
            
            metrics = ReferralMetrics(
                total_referrals=total_referrals,
                successful_referrals=successful_referrals,
                conversion_rate=conversion_rate,
                average_referee_value=average_referee_value,
                total_rewards_paid=total_rewards_paid,
                roi=roi,
                viral_coefficient=viral_coefficient,
                time_to_conversion=avg_time_to_conversion
            )
            
            return {
                'success': True,
                'program_id': program_id,
                'time_period_days': time_period_days,
                'metrics': metrics.__dict__,
                'calculated_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error calculating program metrics: {e}")
            return {'success': False, 'error': str(e)}
    
    async def optimize_referral_rewards(self, program_id: str) -> Dict:
        """Optimize referral reward amounts based on performance data"""
        try:
            # Get historical performance data
            metrics = await self.calculate_program_metrics(program_id, 90)
            
            if not metrics['success']:
                return metrics
            
            current_metrics = metrics['metrics']
            program = self.programs[program_id]
            
            recommendations = []
            
            # Analyze conversion rate
            if current_metrics['conversion_rate'] < 0.05:  # Less than 5%
                recommendations.append({
                    'type': 'increase_referee_reward',
                    'current_amount': program.referee_reward_amount,
                    'suggested_amount': program.referee_reward_amount * 1.5,
                    'reason': 'Low conversion rate suggests referee reward is insufficient'
                })
            
            # Analyze ROI
            if current_metrics['roi'] > 3.0:  # Very high ROI
                recommendations.append({
                    'type': 'increase_referrer_reward',
                    'current_amount': program.referrer_reward_amount,
                    'suggested_amount': program.referrer_reward_amount * 1.2,
                    'reason': 'High ROI allows for increased referrer rewards to drive more referrals'
                })
            elif current_metrics['roi'] < 1.0:  # Negative or low ROI
                recommendations.append({
                    'type': 'decrease_rewards',
                    'reason': 'Low ROI suggests rewards are too high relative to customer value'
                })
            
            # Analyze viral coefficient
            if current_metrics['viral_coefficient'] < 0.1:
                recommendations.append({
                    'type': 'gamification',
                    'reason': 'Low viral coefficient suggests need for gamification or tiered rewards'
                })
            
            # Generate optimal reward structure
            optimal_structure = await self._calculate_optimal_reward_structure(program_id, current_metrics)
            
            return {
                'success': True,
                'program_id': program_id,
                'current_metrics': current_metrics,
                'recommendations': recommendations,
                'optimal_structure': optimal_structure
            }
        
        except Exception as e:
            logger.error(f"Error optimizing referral rewards: {e}")
            return {'success': False, 'error': str(e)}
    
    async def identify_top_referrers(self, program_id: str, limit: int = 10) -> List[Dict]:
        """Identify top-performing referrers for a program"""
        try:
            referrer_performance = {}
            
            # Get all referrals for program
            program_referrals = await self._get_program_referrals(program_id)
            
            for referral in program_referrals:
                referrer_id = referral['referrer_id']
                
                if referrer_id not in referrer_performance:
                    referrer_performance[referrer_id] = {
                        'referrer_id': referrer_id,
                        'total_referrals': 0,
                        'successful_referrals': 0,
                        'total_clicks': 0,
                        'total_revenue_generated': 0.0,
                        'conversion_rate': 0.0,
                        'average_deal_size': 0.0
                    }
                
                perf = referrer_performance[referrer_id]
                perf['total_referrals'] += 1
                perf['total_clicks'] += referral.get('clicks', 0)
                
                if referral['conversions'] > 0:
                    perf['successful_referrals'] += 1
                    perf['total_revenue_generated'] += referral.get('purchase_amount', 0)
            
            # Calculate derived metrics
            for referrer_id, perf in referrer_performance.items():
                if perf['total_referrals'] > 0:
                    perf['conversion_rate'] = perf['successful_referrals'] / perf['total_referrals']
                
                if perf['successful_referrals'] > 0:
                    perf['average_deal_size'] = perf['total_revenue_generated'] / perf['successful_referrals']
            
            # Sort by total revenue generated and limit results
            top_referrers = sorted(
                referrer_performance.values(),
                key=lambda x: x['total_revenue_generated'],
                reverse=True
            )[:limit]
            
            return top_referrers
        
        except Exception as e:
            logger.error(f"Error identifying top referrers: {e}")
            return []
    
    def _calculate_referrer_reward(self, program: ReferralProgram, purchase_amount: float) -> float:
        """Calculate referrer reward based on program rules"""
        if program.referrer_reward_type == RewardType.CASH:
            # Could be fixed amount or percentage of purchase
            if program.referrer_reward_amount <= 1.0:  # Assume percentage if <= 1
                return purchase_amount * program.referrer_reward_amount
            else:
                return program.referrer_reward_amount
        else:
            return program.referrer_reward_amount
    
    async def _process_rewards(self, conversion_data: Dict) -> Dict:
        """Process reward distribution for successful referral"""
        # Mock implementation - would integrate with payment/credit systems
        results = {
            'referrer_reward_processed': True,
            'referee_reward_processed': True,
            'referrer_reward_amount': conversion_data['referrer_reward']['amount'],
            'referee_reward_amount': conversion_data['referee_reward']['amount'],
            'processing_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Processed rewards for conversion {conversion_data['conversion_id']}")
        return results
    
    async def _get_program_referrals(self, program_id: str, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Get all referrals for a program within date range"""
        program_referrals = []
        
        for referral_code, referral in self.referrals.items():
            if referral['program_id'] == program_id:
                referral_date = datetime.fromisoformat(referral['created_at'])
                
                if start_date and referral_date < start_date:
                    continue
                if end_date and referral_date > end_date:
                    continue
                
                # Add mock purchase amount for successful conversions
                if referral['conversions'] > 0:
                    referral['purchase_amount'] = np.random.uniform(50, 500)
                
                program_referrals.append(referral)
        
        return program_referrals
    
    async def _calculate_total_rewards_paid(self, program_id: str, start_date: datetime, end_date: datetime) -> float:
        """Calculate total rewards paid for a program in time period"""
        # Mock implementation
        program_referrals = await self._get_program_referrals(program_id, start_date, end_date)
        successful_referrals = len([r for r in program_referrals if r['conversions'] > 0])
        
        program = self.programs[program_id]
        avg_reward_per_conversion = program.referrer_reward_amount + program.referee_reward_amount
        
        return successful_referrals * avg_reward_per_conversion
    
    async def _calculate_viral_coefficient(self, program_id: str) -> float:
        """Calculate viral coefficient (average referrals per customer)"""
        program_referrals = await self._get_program_referrals(program_id)
        
        if not program_referrals:
            return 0.0
        
        successful_referrals = len([r for r in program_referrals if r['conversions'] > 0])
        unique_referrers = len(set(r['referrer_id'] for r in program_referrals))
        
        return successful_referrals / max(unique_referrers, 1)
    
    async def _calculate_avg_time_to_conversion(self, program_id: str) -> float:
        """Calculate average time from referral creation to conversion"""
        # Mock implementation - would calculate actual conversion times
        return np.random.uniform(1, 30)  # 1-30 days average
    
    async def _calculate_optimal_reward_structure(self, program_id: str, current_metrics: Dict) -> Dict:
        """Calculate optimal reward structure based on performance"""
        current_roi = current_metrics['roi']
        current_conversion_rate = current_metrics['conversion_rate']
        
        # Simple optimization logic (in production, use more sophisticated models)
        optimal_referrer_reward = self.default_reward
        optimal_referee_reward = self.default_reward
        
        if current_roi > 2.0 and current_conversion_rate < 0.1:
            # High ROI but low conversion - increase referee reward
            optimal_referee_reward *= 1.3
        elif current_roi < 1.5 and current_conversion_rate > 0.1:
            # Low ROI but good conversion - decrease rewards
            optimal_referrer_reward *= 0.8
            optimal_referee_reward *= 0.8
        elif current_conversion_rate > 0.15:
            # Very good conversion rate - can increase referrer reward
            optimal_referrer_reward *= 1.2
        
        return {
            'optimal_referrer_reward': optimal_referrer_reward,
            'optimal_referee_reward': optimal_referee_reward,
            'expected_roi_improvement': 0.2,  # Mock improvement
            'expected_conversion_improvement': 0.05  # Mock improvement
        }