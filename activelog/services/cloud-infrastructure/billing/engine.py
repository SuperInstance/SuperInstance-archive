"""
Per-Minute Billing Engine
Real-time billing system with minute-level precision for cloud infrastructure
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
import json
from dataclasses import asdict
import uuid

from core.models import (
    User, EC2Instance, BillingRecord, InstanceType, BillingStatus,
    UserTier, current_timestamp, generate_id, calculate_cost
)

class BillingEngine:
    """Core billing engine for per-minute resource billing"""
    
    def __init__(self, config: Dict[str, Any], database_manager):
        self.config = config
        self.db = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Billing configuration
        self.pricing = config['billing']['pricing']
        self.currency = config['billing']['currency']
        self.billing_precision = config['billing']['billing_precision']
        
        # Billing cycle management
        self.billing_active = False
        self.billing_task = None
        
    async def start_billing_engine(self):
        """Start the billing engine"""
        if self.billing_active:
            return
            
        self.billing_active = True
        self.billing_task = asyncio.create_task(self._billing_loop())
        self.logger.info("Billing engine started")
    
    async def stop_billing_engine(self):
        """Stop the billing engine"""
        self.billing_active = False
        if self.billing_task:
            self.billing_task.cancel()
            try:
                await self.billing_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Billing engine stopped")
    
    async def _billing_loop(self):
        """Main billing loop - runs every minute"""
        while self.billing_active:
            try:
                await self._process_billing_cycle()
                await asyncio.sleep(60)  # Run every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Billing cycle error: {e}")
                await asyncio.sleep(60)
    
    async def _process_billing_cycle(self):
        """Process one billing cycle for all running instances"""
        try:
            # Get all billable instances
            running_instances = await self.db.get_instances_by_state("running")
            
            billing_tasks = []
            for instance in running_instances:
                task = self._bill_instance_minute(instance)
                billing_tasks.append(task)
            
            if billing_tasks:
                await asyncio.gather(*billing_tasks, return_exceptions=True)
                
            self.logger.debug(f"Processed billing for {len(running_instances)} instances")
            
        except Exception as e:
            self.logger.error(f"Error in billing cycle: {e}")
    
    async def _bill_instance_minute(self, instance: EC2Instance):
        """Bill a single instance for one minute of usage"""
        try:
            current_time = current_timestamp()
            
            # Calculate billing window
            if instance.last_billed_at:
                start_time = instance.last_billed_at
            else:
                start_time = instance.created_at
            
            end_time = current_time
            duration_minutes = max(1, int((end_time - start_time).total_seconds() / 60))
            
            if duration_minutes < 1:
                return  # No billable time
            
            # Get pricing for instance type
            cost_per_minute = self._get_instance_cost_per_minute(instance.instance_type)
            total_cost = Decimal(str(cost_per_minute * duration_minutes)).quantize(
                Decimal('0.0001'), rounding=ROUND_HALF_UP
            )
            
            # Create billing record
            billing_record = BillingRecord(
                record_id=generate_id("bill"),
                user_id=instance.user_id,
                instance_id=instance.instance_id,
                instance_type=instance.instance_type,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                cost_per_minute=cost_per_minute,
                total_cost=float(total_cost),
                billing_tags=instance.tags.copy()
            )
            
            # Save billing record
            await self.db.create_billing_record(billing_record)
            
            # Update instance billing timestamp
            instance.last_billed_at = current_time
            instance.total_runtime_minutes += duration_minutes
            await self.db.update_instance(instance)
            
            # Update user's current spend
            await self._update_user_spend(instance.user_id, float(total_cost))
            
            self.logger.debug(
                f"Billed instance {instance.instance_id}: "
                f"{duration_minutes}min × ${cost_per_minute} = ${total_cost}"
            )
            
        except Exception as e:
            self.logger.error(f"Error billing instance {instance.instance_id}: {e}")
    
    def _get_instance_cost_per_minute(self, instance_type: InstanceType) -> float:
        """Get per-minute cost for instance type"""
        base_cost = self.pricing['compute'].get(instance_type.value, 0.0)
        
        # Apply any modifiers (e.g., game night pricing)
        # This could be expanded with time-based pricing, user tier discounts, etc.
        
        return base_cost
    
    async def _update_user_spend(self, user_id: str, additional_cost: float):
        """Update user's current spend and check budget"""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return
            
            user.current_spend += additional_cost
            await self.db.update_user(user)
            
            # Check budget limits
            if user.monthly_budget and user.current_spend > user.monthly_budget:
                await self._handle_budget_exceeded(user)
                
        except Exception as e:
            self.logger.error(f"Error updating user spend for {user_id}: {e}")
    
    async def _handle_budget_exceeded(self, user: User):
        """Handle user exceeding budget"""
        try:
            self.logger.warning(f"User {user.user_id} exceeded budget: ${user.current_spend}/${user.monthly_budget}")
            
            # For now, just log. In production, you might:
            # - Send notification
            # - Suspend non-critical instances
            # - Change billing status
            # - Apply spending limits
            
            # Example: Set billing status to overdue
            if user.billing_status == BillingStatus.ACTIVE:
                user.billing_status = BillingStatus.OVERDUE
                await self.db.update_user(user)
                
        except Exception as e:
            self.logger.error(f"Error handling budget exceeded for user {user.user_id}: {e}")
    
    async def get_user_usage(self, user_id: str, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get detailed usage and billing information for a user"""
        try:
            # Default to current month if no dates provided
            if not start_date:
                now = current_timestamp()
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if not end_date:
                end_date = current_timestamp()
            
            # Get billing records for the period
            billing_records = await self.db.get_billing_records(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Calculate totals and breakdowns
            total_cost = sum(record.total_cost for record in billing_records)
            total_minutes = sum(record.duration_minutes for record in billing_records)
            
            # Breakdown by instance type
            instance_breakdown = {}
            for record in billing_records:
                inst_type = record.instance_type.value
                if inst_type not in instance_breakdown:
                    instance_breakdown[inst_type] = {
                        'total_cost': 0.0,
                        'total_minutes': 0,
                        'instance_count': set()
                    }
                
                instance_breakdown[inst_type]['total_cost'] += record.total_cost
                instance_breakdown[inst_type]['total_minutes'] += record.duration_minutes
                instance_breakdown[inst_type]['instance_count'].add(record.instance_id)
            
            # Convert sets to counts
            for breakdown in instance_breakdown.values():
                breakdown['unique_instances'] = len(breakdown['instance_count'])
                del breakdown['instance_count']
            
            # Daily breakdown
            daily_breakdown = {}
            for record in billing_records:
                day_key = record.start_time.strftime('%Y-%m-%d')
                if day_key not in daily_breakdown:
                    daily_breakdown[day_key] = {'cost': 0.0, 'minutes': 0}
                
                daily_breakdown[day_key]['cost'] += record.total_cost
                daily_breakdown[day_key]['minutes'] += record.duration_minutes
            
            # Get user info for budget comparison
            user = await self.db.get_user(user_id)
            
            return {
                'user_id': user_id,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': {
                    'total_cost': round(total_cost, 4),
                    'total_minutes': total_minutes,
                    'total_hours': round(total_minutes / 60, 2),
                    'average_cost_per_hour': round(total_cost / (total_minutes / 60), 4) if total_minutes > 0 else 0,
                    'monthly_budget': user.monthly_budget if user else None,
                    'budget_utilization': round((total_cost / user.monthly_budget) * 100, 1) if user and user.monthly_budget else None
                },
                'breakdown': {
                    'by_instance_type': instance_breakdown,
                    'by_day': daily_breakdown
                },
                'recent_records': [
                    {
                        'record_id': record.record_id,
                        'instance_id': record.instance_id,
                        'instance_type': record.instance_type.value,
                        'start_time': record.start_time.isoformat(),
                        'end_time': record.end_time.isoformat(),
                        'duration_minutes': record.duration_minutes,
                        'cost': record.total_cost
                    }
                    for record in billing_records[-10:]  # Last 10 records
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user usage for {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def calculate_projected_cost(self, user_id: str, 
                                     projection_days: int = 30) -> Dict[str, Any]:
        """Calculate projected costs based on current usage patterns"""
        try:
            # Get recent usage (last 7 days for pattern analysis)
            end_date = current_timestamp()
            start_date = end_date - timedelta(days=7)
            
            recent_usage = await self.get_user_usage(user_id, start_date, end_date)
            
            if 'error' in recent_usage:
                return recent_usage
            
            # Calculate daily average
            total_cost_7days = recent_usage['summary']['total_cost']
            daily_average = total_cost_7days / 7
            
            # Project forward
            projected_cost = daily_average * projection_days
            
            # Get current month costs for comparison
            now = current_timestamp()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            current_month_usage = await self.get_user_usage(user_id, month_start, now)
            
            current_month_cost = current_month_usage['summary']['total_cost']
            
            return {
                'user_id': user_id,
                'projection_days': projection_days,
                'daily_average_cost': round(daily_average, 4),
                'projected_cost': round(projected_cost, 2),
                'current_month_cost': round(current_month_cost, 2),
                'analysis_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'breakdown': recent_usage['breakdown']['by_instance_type'],
                'recommendations': self._generate_cost_recommendations(
                    daily_average, projected_cost, recent_usage['breakdown']
                ),
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating projected cost for {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    def _generate_cost_recommendations(self, daily_average: float, 
                                     projected_cost: float, 
                                     breakdown: Dict[str, Any]) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []
        
        # High cost warning
        if daily_average > 10:  # $10/day threshold
            recommendations.append(
                f"High daily cost detected (${daily_average:.2f}/day). "
                "Consider optimizing instance types or usage patterns."
            )
        
        # Instance type recommendations
        instance_breakdown = breakdown.get('by_instance_type', {})
        for inst_type, data in instance_breakdown.items():
            if data['total_cost'] > projected_cost * 0.5:  # >50% of total cost
                recommendations.append(
                    f"Instance type {inst_type} represents {data['total_cost']/projected_cost*100:.1f}% "
                    f"of projected costs. Consider rightsizing or scheduled shutdowns."
                )
        
        # Usage pattern recommendations
        if projected_cost > 100:  # $100/month threshold
            recommendations.append(
                "Consider using spot instances or reserved capacity for predictable workloads."
            )
        
        return recommendations
    
    async def generate_invoice(self, user_id: str, billing_period_start: datetime,
                             billing_period_end: datetime) -> Dict[str, Any]:
        """Generate detailed invoice for a billing period"""
        try:
            # Get user information
            user = await self.db.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Get usage data
            usage_data = await self.get_user_usage(user_id, billing_period_start, billing_period_end)
            
            if 'error' in usage_data:
                return usage_data
            
            # Generate invoice
            invoice = {
                'invoice_id': generate_id("inv"),
                'user_id': user_id,
                'user_email': user.email,
                'user_tier': user.tier.value,
                'billing_period': {
                    'start_date': billing_period_start.isoformat(),
                    'end_date': billing_period_end.isoformat()
                },
                'generated_at': current_timestamp().isoformat(),
                'currency': self.currency,
                'summary': usage_data['summary'],
                'line_items': [],
                'subtotal': 0.0,
                'taxes': 0.0,
                'total': 0.0
            }
            
            # Create line items by instance type
            for inst_type, breakdown in usage_data['breakdown']['by_instance_type'].items():
                line_item = {
                    'description': f"{inst_type} instance usage",
                    'quantity': breakdown['total_minutes'],
                    'unit': 'minutes',
                    'rate': self._get_instance_cost_per_minute(InstanceType(inst_type)),
                    'amount': breakdown['total_cost']
                }
                invoice['line_items'].append(line_item)
                invoice['subtotal'] += breakdown['total_cost']
            
            # Apply discounts if applicable
            discounts = await self._calculate_discounts(user, invoice['subtotal'])
            if discounts:
                invoice['discounts'] = discounts
                for discount in discounts:
                    invoice['subtotal'] -= discount['amount']
            
            # Calculate taxes (simplified - 0% for demo)
            invoice['taxes'] = 0.0
            invoice['total'] = invoice['subtotal'] + invoice['taxes']
            
            # Save invoice record
            await self.db.create_invoice(invoice)
            
            return invoice
            
        except Exception as e:
            self.logger.error(f"Error generating invoice for {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def _calculate_discounts(self, user: User, subtotal: float) -> List[Dict[str, Any]]:
        """Calculate applicable discounts"""
        discounts = []
        
        # Volume discounts based on monthly usage
        volume_discounts = self.config['billing']['volume_discounts']
        
        # Get current month usage minutes
        now = current_timestamp()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage_data = await self.get_user_usage(user.user_id, month_start, now)
        total_minutes = usage_data['summary']['total_minutes']
        
        # Apply volume discounts
        for tier_name, tier_config in volume_discounts.items():
            if total_minutes >= tier_config['threshold_minutes']:
                discount_amount = subtotal * (tier_config['discount_percent'] / 100)
                discounts.append({
                    'type': 'volume_discount',
                    'description': f"{tier_config['discount_percent']}% volume discount ({tier_name})",
                    'amount': discount_amount
                })
                break  # Apply only the highest applicable discount
        
        # Tier-based discounts
        tier_discounts = {
            UserTier.PREMIUM: 0.05,  # 5% discount
            UserTier.ENTERPRISE: 0.10  # 10% discount
        }
        
        if user.tier in tier_discounts:
            discount_amount = subtotal * tier_discounts[user.tier]
            discounts.append({
                'type': 'tier_discount',
                'description': f"{tier_discounts[user.tier]*100}% {user.tier.value} tier discount",
                'amount': discount_amount
            })
        
        return discounts
    
    async def get_billing_metrics(self) -> Dict[str, Any]:
        """Get billing system metrics"""
        try:
            # Get current period stats
            now = current_timestamp()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Total revenue this month
            all_records = await self.db.get_all_billing_records(month_start, now)
            total_revenue = sum(record.total_cost for record in all_records)
            total_minutes_billed = sum(record.duration_minutes for record in all_records)
            
            # Active users with billing
            active_users = len(set(record.user_id for record in all_records))
            
            # Average revenue per user
            arpu = total_revenue / active_users if active_users > 0 else 0
            
            # Top users by spend
            user_spend = {}
            for record in all_records:
                if record.user_id not in user_spend:
                    user_spend[record.user_id] = 0
                user_spend[record.user_id] += record.total_cost
            
            top_users = sorted(user_spend.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'billing_engine_status': 'active' if self.billing_active else 'inactive',
                'current_month_revenue': round(total_revenue, 2),
                'total_minutes_billed': total_minutes_billed,
                'active_billing_users': active_users,
                'average_revenue_per_user': round(arpu, 2),
                'top_users_by_spend': [
                    {'user_id': user_id, 'spend': round(spend, 2)}
                    for user_id, spend in top_users
                ],
                'billing_records_processed': len(all_records),
                'timestamp': now.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting billing metrics: {e}")
            return {
                'billing_engine_status': 'error',
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for billing engine"""
        try:
            # Check billing loop status
            billing_healthy = self.billing_active and (
                self.billing_task and not self.billing_task.done()
            )
            
            # Check database connectivity
            try:
                test_user = await self.db.get_user("health_check_test")
                db_healthy = True
            except:
                db_healthy = False
            
            # Get recent billing activity
            now = current_timestamp()
            hour_ago = now - timedelta(hours=1)
            recent_records = await self.db.get_all_billing_records(hour_ago, now)
            
            return {
                'service': 'billing_engine',
                'healthy': billing_healthy and db_healthy,
                'billing_loop_active': billing_healthy,
                'database_connected': db_healthy,
                'recent_billing_records': len(recent_records),
                'last_billing_cycle': now.isoformat(),
                'timestamp': now.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Billing engine health check failed: {e}")
            return {
                'service': 'billing_engine',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }