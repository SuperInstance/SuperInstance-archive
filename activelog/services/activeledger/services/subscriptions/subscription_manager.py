"""
Subscription Management System
Handles free tier, paid tier, pro tier, and enterprise billing
"""

from decimal import Decimal
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import logging

from ...models.database import (
    User, Subscription, Transaction, SubscriptionTier, SubscriptionStatus,
    TransactionType, TransactionStatus
)
from ...config.settings import settings, SUBSCRIPTION_TIERS
from ..credits.cc_system import ComputeCreditSystem
from ..analytics.usage_tracker import UsageTracker

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Manages user subscriptions and billing"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        self.usage_tracker = UsageTracker(db)
    
    async def create_subscription(
        self,
        user_id: str,
        tier: SubscriptionTier,
        custom_pricing: Optional[Dict] = None
    ) -> Subscription:
        """Create or upgrade user subscription"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get tier configuration
        tier_config = SUBSCRIPTION_TIERS.get(tier.value)
        if not tier_config:
            raise ValueError(f"Invalid subscription tier: {tier}")
        
        # Calculate billing dates
        now = datetime.utcnow()
        billing_end = now + timedelta(days=30)  # Monthly billing
        next_billing = billing_end
        
        # Determine cost
        monthly_cost = tier_config["monthly_cost_cc"]
        if custom_pricing and tier == SubscriptionTier.ENTERPRISE:
            monthly_cost = Decimal(str(custom_pricing.get("monthly_cost_cc", monthly_cost)))
        
        # Cancel existing subscription if any
        await self._cancel_existing_subscription(user_id)
        
        # Create new subscription
        subscription = Subscription(
            user_id=user_id,
            tier=tier,
            status=SubscriptionStatus.ACTIVE,
            monthly_cost_cc=monthly_cost,
            billing_cycle_start=now,
            billing_cycle_end=billing_end,
            next_billing_date=next_billing,
            custom_pricing=custom_pricing
        )
        
        # Update user subscription info
        user.subscription_tier = tier
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.subscription_expires_at = billing_end
        
        self.db.add(subscription)
        self.db.commit()
        
        # Process initial payment for paid tiers
        if monthly_cost > 0:
            await self._process_subscription_payment(subscription.id)
        
        logger.info(f"Created {tier.value} subscription for user {user_id}")
        return subscription
    
    async def _cancel_existing_subscription(self, user_id: str):
        """Cancel user's existing active subscription"""
        
        active_subscription = (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
            .first()
        )
        
        if active_subscription:
            active_subscription.status = SubscriptionStatus.CANCELLED
            active_subscription.cancelled_at = datetime.utcnow()
    
    async def _process_subscription_payment(self, subscription_id: str) -> bool:
        """Process subscription payment"""
        
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        # Check user balance
        user_balance = await self.cc_system.get_user_balance(subscription.user_id)
        
        if user_balance < subscription.monthly_cost_cc:
            # Insufficient balance - mark subscription as inactive
            subscription.status = SubscriptionStatus.INACTIVE
            self.db.commit()
            
            logger.warning(f"Insufficient balance for subscription {subscription_id}")
            return False
        
        # Deduct payment from user balance
        await self.cc_system.deduct_credits(
            subscription.user_id,
            subscription.monthly_cost_cc,
            TransactionType.DEBIT,
            f"Subscription payment - {subscription.tier.value}",
            metadata={
                "subscription_id": subscription_id,
                "billing_period": f"{subscription.billing_cycle_start} to {subscription.billing_cycle_end}"
            }
        )
        
        # Update billing cycle
        subscription.billing_cycle_start = subscription.billing_cycle_end
        subscription.billing_cycle_end = subscription.billing_cycle_start + timedelta(days=30)
        subscription.next_billing_date = subscription.billing_cycle_end
        
        self.db.commit()
        
        logger.info(f"Processed payment for subscription {subscription_id}")
        return True
    
    async def upgrade_subscription(
        self,
        user_id: str,
        new_tier: SubscriptionTier,
        custom_pricing: Optional[Dict] = None
    ) -> Subscription:
        """Upgrade user to higher tier with prorated billing"""
        
        current_subscription = await self.get_active_subscription(user_id)
        if not current_subscription:
            return await self.create_subscription(user_id, new_tier, custom_pricing)
        
        # Calculate prorated refund for current tier
        days_remaining = (current_subscription.billing_cycle_end - datetime.utcnow()).days
        if days_remaining > 0:
            daily_rate = current_subscription.monthly_cost_cc / 30
            refund_amount = daily_rate * days_remaining
            
            # Refund prorated amount
            await self.cc_system.add_credits(
                user_id,
                refund_amount,
                TransactionType.REFUND,
                f"Prorated refund for upgrade from {current_subscription.tier.value}",
                metadata={"days_remaining": days_remaining, "upgrade_to": new_tier.value}
            )
        
        # Create new subscription
        return await self.create_subscription(user_id, new_tier, custom_pricing)
    
    async def downgrade_subscription(
        self,
        user_id: str,
        new_tier: SubscriptionTier
    ) -> Subscription:
        """Downgrade subscription at end of current billing cycle"""
        
        current_subscription = await self.get_active_subscription(user_id)
        if not current_subscription:
            return await self.create_subscription(user_id, new_tier)
        
        # Schedule downgrade at end of billing cycle
        current_subscription.status = SubscriptionStatus.CANCELLED
        current_subscription.cancelled_at = datetime.utcnow()
        
        # Create new subscription starting at end of current cycle
        new_tier_config = SUBSCRIPTION_TIERS.get(new_tier.value)
        
        new_subscription = Subscription(
            user_id=user_id,
            tier=new_tier,
            status=SubscriptionStatus.ACTIVE,
            monthly_cost_cc=new_tier_config["monthly_cost_cc"],
            billing_cycle_start=current_subscription.billing_cycle_end,
            billing_cycle_end=current_subscription.billing_cycle_end + timedelta(days=30),
            next_billing_date=current_subscription.billing_cycle_end + timedelta(days=30)
        )
        
        self.db.add(new_subscription)
        self.db.commit()
        
        logger.info(f"Scheduled downgrade for user {user_id} from {current_subscription.tier.value} to {new_tier.value}")
        return new_subscription
    
    async def cancel_subscription(self, user_id: str) -> bool:
        """Cancel user subscription"""
        
        subscription = await self.get_active_subscription(user_id)
        if not subscription:
            return False
        
        # Cancel subscription
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.utcnow()
        
        # Update user record
        user = self.db.query(User).filter(User.id == user_id).first()
        user.subscription_tier = SubscriptionTier.FREE
        user.subscription_status = SubscriptionStatus.CANCELLED
        
        self.db.commit()
        
        logger.info(f"Cancelled subscription for user {user_id}")
        return True
    
    async def get_active_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription"""
        
        return (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == SubscriptionStatus.ACTIVE
                )
            )
            .first()
        )
    
    async def check_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """Check user's usage against subscription limits"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        subscription = await self.get_active_subscription(user_id)
        tier = subscription.tier if subscription else SubscriptionTier.FREE
        tier_config = SUBSCRIPTION_TIERS.get(tier.value)
        
        # Get current usage
        usage = await self.usage_tracker.get_current_usage(user_id)
        
        # Check limits
        limits = tier_config["limits"]
        usage_status = {
            "tier": tier.value,
            "storage": {
                "used_gb": usage["storage_gb"],
                "limit_gb": tier_config["storage_gb"],
                "percentage": (usage["storage_gb"] / tier_config["storage_gb"]) * 100 if tier_config["storage_gb"] > 0 else 0
            },
            "compute": {
                "used_hours": usage["compute_hours"],
                "limit_hours": tier_config["compute_hours"],
                "percentage": (usage["compute_hours"] / tier_config["compute_hours"]) * 100 if tier_config["compute_hours"] > 0 else 0
            },
            "api_calls": {
                "used": usage["api_calls"],
                "limit": limits["api_calls_per_month"],
                "percentage": (usage["api_calls"] / limits["api_calls_per_month"]) * 100 if limits["api_calls_per_month"] > 0 else 0
            },
            "bandwidth": {
                "used_gb": usage["bandwidth_gb"],
                "limit_gb": limits["bandwidth_gb_per_month"],
                "percentage": (usage["bandwidth_gb"] / limits["bandwidth_gb_per_month"]) * 100 if limits["bandwidth_gb_per_month"] > 0 else 0
            }
        }
        
        # Check for overages
        overages = []
        if usage["storage_gb"] > tier_config["storage_gb"]:
            overages.append("storage")
        if usage["compute_hours"] > tier_config["compute_hours"]:
            overages.append("compute")
        if limits["api_calls_per_month"] > 0 and usage["api_calls"] > limits["api_calls_per_month"]:
            overages.append("api_calls")
        if limits["bandwidth_gb_per_month"] > 0 and usage["bandwidth_gb"] > limits["bandwidth_gb_per_month"]:
            overages.append("bandwidth")
        
        usage_status["overages"] = overages
        usage_status["within_limits"] = len(overages) == 0
        
        return usage_status
    
    async def process_monthly_billing(self) -> Dict[str, int]:
        """Process monthly billing for all active subscriptions"""
        
        # Get all active subscriptions due for billing
        due_subscriptions = (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.next_billing_date <= datetime.utcnow(),
                    Subscription.monthly_cost_cc > 0
                )
            )
            .all()
        )
        
        results = {"processed": 0, "failed": 0, "cancelled": 0}
        
        for subscription in due_subscriptions:
            try:
                success = await self._process_subscription_payment(subscription.id)
                if success:
                    results["processed"] += 1
                else:
                    # Cancel subscription due to insufficient funds
                    await self.cancel_subscription(subscription.user_id)
                    results["cancelled"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process billing for subscription {subscription.id}: {str(e)}")
                results["failed"] += 1
        
        logger.info(f"Monthly billing processed: {results}")
        return results
    
    async def get_subscription_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get subscription analytics for user"""
        
        subscription = await self.get_active_subscription(user_id)
        if not subscription:
            return {"error": "No active subscription"}
        
        # Get billing history
        billing_history = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.subscription_id == subscription.id,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
            .order_by(desc(Transaction.created_at))
            .limit(12)  # Last 12 months
            .all()
        )
        
        # Calculate costs and savings
        tier_config = SUBSCRIPTION_TIERS.get(subscription.tier.value)
        usage = await self.usage_tracker.get_current_usage(user_id)
        
        # Calculate cost per usage unit
        cost_per_gb_storage = subscription.monthly_cost_cc / tier_config["storage_gb"] if tier_config["storage_gb"] > 0 else 0
        cost_per_compute_hour = subscription.monthly_cost_cc / tier_config["compute_hours"] if tier_config["compute_hours"] > 0 else 0
        
        analytics = {
            "subscription": {
                "tier": subscription.tier.value,
                "monthly_cost_cc": float(subscription.monthly_cost_cc),
                "status": subscription.status.value,
                "next_billing": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
                "days_until_renewal": (subscription.next_billing_date - datetime.utcnow()).days if subscription.next_billing_date else None
            },
            "usage_efficiency": {
                "storage_utilization": (usage["storage_gb"] / tier_config["storage_gb"]) * 100 if tier_config["storage_gb"] > 0 else 0,
                "compute_utilization": (usage["compute_hours"] / tier_config["compute_hours"]) * 100 if tier_config["compute_hours"] > 0 else 0,
                "cost_per_gb_used": float(cost_per_gb_storage),
                "cost_per_hour_used": float(cost_per_compute_hour)
            },
            "billing_history": [
                {
                    "date": tx.created_at.isoformat(),
                    "amount_cc": float(tx.amount_cc),
                    "description": tx.description
                }
                for tx in billing_history
            ],
            "potential_savings": await self._calculate_potential_savings(user_id, usage, tier_config)
        }
        
        return analytics
    
    async def _calculate_potential_savings(self, user_id: str, usage: Dict, current_tier_config: Dict) -> Dict[str, Any]:
        """Calculate potential savings by switching tiers"""
        
        savings = {}
        
        for tier_name, tier_config in SUBSCRIPTION_TIERS.items():
            if tier_name == current_tier_config.get("name"):
                continue
            
            # Check if tier can handle current usage
            can_handle = (
                usage["storage_gb"] <= tier_config["storage_gb"] and
                usage["compute_hours"] <= tier_config["compute_hours"]
            )
            
            if can_handle:
                monthly_savings = current_tier_config["monthly_cost_cc"] - tier_config["monthly_cost_cc"]
                annual_savings = monthly_savings * 12
                
                savings[tier_name] = {
                    "monthly_savings_cc": float(monthly_savings),
                    "annual_savings_cc": float(annual_savings),
                    "can_downgrade": monthly_savings > 0
                }
        
        return savings