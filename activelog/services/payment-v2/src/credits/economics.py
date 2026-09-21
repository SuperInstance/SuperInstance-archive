from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from ..database import (
    CreditPricing, ComputeCredit, CreditTransaction, 
    CreditTransactionType, User, Organization
)

class ComputeEconomics:
    """Handles compute credit pricing, consumption, and economic calculations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def get_credit_cost(
        self, 
        resource_type: str, 
        units: float, 
        tier: str = "standard", 
        region: str = "global"
    ) -> Decimal:
        """Calculate credit cost for compute resources"""
        
        # Get current pricing
        pricing_result = await self.db.execute(
            select(CreditPricing).where(
                and_(
                    CreditPricing.resource_type == resource_type,
                    CreditPricing.tier == tier,
                    CreditPricing.region == region,
                    CreditPricing.effective_from <= datetime.utcnow(),
                    CreditPricing.effective_to.is_(None) | (CreditPricing.effective_to > datetime.utcnow())
                )
            ).order_by(CreditPricing.effective_from.desc())
        )
        
        pricing = pricing_result.scalar_one_or_none()
        if not pricing:
            raise ValueError(f"No pricing found for {resource_type} in {tier} tier")
        
        total_credits = Decimal(str(units)) * pricing.credits_per_unit
        return total_credits
    
    async def consume_credits(
        self,
        user_id: uuid.UUID,
        resource_type: str,
        units: float,
        tier: str = "standard",
        region: str = "global",
        job_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Consume credits for compute usage"""
        
        # Calculate credit cost
        credits_needed = await self.get_credit_cost(resource_type, units, tier, region)
        
        # Get user's credit account
        credit_account = await self._get_or_create_credit_account(user_id)
        
        # Check sufficient balance (including reserved)
        available_balance = credit_account.balance - credit_account.reserved_balance
        if available_balance < credits_needed:
            return {
                "success": False,
                "error": "insufficient_credits",
                "required": float(credits_needed),
                "available": float(available_balance),
                "shortfall": float(credits_needed - available_balance)
            }
        
        # Record transaction
        transaction = CreditTransaction(
            user_id=user_id,
            organization_id=credit_account.organization_id,
            transaction_type=CreditTransactionType.USAGE,
            amount=-credits_needed,  # Negative for consumption
            balance_before=credit_account.balance,
            balance_after=credit_account.balance - credits_needed,
            description=f"Consumed {units} {resource_type} units ({tier} tier)",
            metadata={
                "resource_type": resource_type,
                "units": units,
                "tier": tier,
                "region": region,
                "job_id": job_id,
                **(metadata or {})
            },
            reference_id=job_id
        )
        
        self.db.add(transaction)
        
        # Update balance
        credit_account.balance -= credits_needed
        credit_account.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        # Check for auto-recharge if enabled
        await self._check_auto_recharge(credit_account)
        
        return {
            "success": True,
            "credits_consumed": float(credits_needed),
            "remaining_balance": float(credit_account.balance),
            "transaction_id": str(transaction.id)
        }
    
    async def reserve_credits(
        self,
        user_id: uuid.UUID,
        credits_amount: Decimal,
        job_id: str,
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """Reserve credits for a job (prevents over-consumption)"""
        
        credit_account = await self._get_or_create_credit_account(user_id)
        
        # Check if enough credits available for reservation
        available = credit_account.balance - credit_account.reserved_balance
        if available < credits_amount:
            return {
                "success": False,
                "error": "insufficient_credits_for_reservation"
            }
        
        # Update reserved balance
        credit_account.reserved_balance += credits_amount
        credit_account.updated_at = datetime.utcnow()
        
        # Record reservation transaction
        transaction = CreditTransaction(
            user_id=user_id,
            organization_id=credit_account.organization_id,
            transaction_type=CreditTransactionType.USAGE,
            amount=Decimal('0'),  # No actual consumption yet
            balance_before=credit_account.balance,
            balance_after=credit_account.balance,
            description=f"Reserved {credits_amount} credits for job {job_id}",
            metadata={
                "action": "reserve",
                "reserved_amount": float(credits_amount),
                "job_id": job_id,
                "duration_minutes": duration_minutes
            },
            reference_id=job_id
        )
        
        self.db.add(transaction)
        await self.db.commit()
        
        # TODO: Schedule reservation cleanup after duration
        
        return {
            "success": True,
            "reserved_amount": float(credits_amount),
            "reservation_id": str(transaction.id)
        }
    
    async def release_credits(
        self,
        user_id: uuid.UUID,
        credits_amount: Decimal,
        job_id: str
    ) -> Dict[str, Any]:
        """Release reserved credits back to available balance"""
        
        credit_account = await self._get_or_create_credit_account(user_id)
        
        # Reduce reserved balance
        release_amount = min(credits_amount, credit_account.reserved_balance)
        credit_account.reserved_balance -= release_amount
        credit_account.updated_at = datetime.utcnow()
        
        # Record release transaction
        transaction = CreditTransaction(
            user_id=user_id,
            organization_id=credit_account.organization_id,
            transaction_type=CreditTransactionType.USAGE,
            amount=Decimal('0'),
            balance_before=credit_account.balance,
            balance_after=credit_account.balance,
            description=f"Released {release_amount} reserved credits from job {job_id}",
            metadata={
                "action": "release",
                "released_amount": float(release_amount),
                "job_id": job_id
            },
            reference_id=job_id
        )
        
        self.db.add(transaction)
        await self.db.commit()
        
        return {
            "success": True,
            "released_amount": float(release_amount),
            "remaining_reserved": float(credit_account.reserved_balance)
        }
    
    async def purchase_credits(
        self,
        user_id: uuid.UUID,
        usd_amount: Decimal,
        payment_method_id: str,
        bonus_percentage: float = 0.0
    ) -> Dict[str, Any]:
        """Purchase credits with USD payment"""
        
        # Calculate credits based on current exchange rate (1 USD = 100 credits base rate)
        base_credits = usd_amount * 100
        bonus_credits = base_credits * Decimal(str(bonus_percentage))
        total_credits = base_credits + bonus_credits
        
        credit_account = await self._get_or_create_credit_account(user_id)
        
        # Record purchase transaction
        transaction = CreditTransaction(
            user_id=user_id,
            organization_id=credit_account.organization_id,
            transaction_type=CreditTransactionType.PURCHASE,
            amount=total_credits,
            balance_before=credit_account.balance,
            balance_after=credit_account.balance + total_credits,
            description=f"Purchased {total_credits} credits for ${usd_amount}",
            metadata={
                "usd_amount": float(usd_amount),
                "base_credits": float(base_credits),
                "bonus_credits": float(bonus_credits),
                "bonus_percentage": bonus_percentage,
                "payment_method_id": payment_method_id,
                "exchange_rate": 100  # credits per USD
            }
        )
        
        self.db.add(transaction)
        
        # Update balance
        credit_account.balance += total_credits
        credit_account.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        return {
            "success": True,
            "credits_purchased": float(total_credits),
            "usd_amount": float(usd_amount),
            "bonus_credits": float(bonus_credits),
            "new_balance": float(credit_account.balance),
            "transaction_id": str(transaction.id)
        }
    
    async def get_usage_analytics(
        self,
        user_id: Optional[uuid.UUID] = None,
        organization_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get compute usage analytics"""
        
        # Build query filters
        filters = [CreditTransaction.transaction_type == CreditTransactionType.USAGE]
        
        if user_id:
            filters.append(CreditTransaction.user_id == user_id)
        if organization_id:
            filters.append(CreditTransaction.organization_id == organization_id)
        if start_date:
            filters.append(CreditTransaction.created_at >= start_date)
        if end_date:
            filters.append(CreditTransaction.created_at <= end_date)
        
        # Get usage transactions
        usage_result = await self.db.execute(
            select(CreditTransaction).where(and_(*filters))
        )
        transactions = usage_result.scalars().all()
        
        # Analyze usage patterns
        resource_usage = {}
        tier_usage = {}
        daily_usage = {}
        total_consumed = Decimal('0')
        
        for tx in transactions:
            if tx.metadata:
                resource_type = tx.metadata.get('resource_type', 'unknown')
                tier = tx.metadata.get('tier', 'standard')
                units = tx.metadata.get('units', 0)
                
                # Resource type breakdown
                if resource_type not in resource_usage:
                    resource_usage[resource_type] = {
                        'credits': 0,
                        'units': 0,
                        'transactions': 0
                    }
                
                resource_usage[resource_type]['credits'] += abs(float(tx.amount))
                resource_usage[resource_type]['units'] += units
                resource_usage[resource_type]['transactions'] += 1
                
                # Tier usage
                if tier not in tier_usage:
                    tier_usage[tier] = 0
                tier_usage[tier] += abs(float(tx.amount))
                
                # Daily usage
                day = tx.created_at.date().isoformat()
                if day not in daily_usage:
                    daily_usage[day] = 0
                daily_usage[day] += abs(float(tx.amount))
                
                total_consumed += abs(tx.amount)
        
        return {
            "total_credits_consumed": float(total_consumed),
            "total_transactions": len(transactions),
            "resource_usage": resource_usage,
            "tier_usage": tier_usage,
            "daily_usage": daily_usage,
            "analysis_period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
    
    async def get_pricing_tiers(self) -> Dict[str, Any]:
        """Get current pricing tiers and rates"""
        
        pricing_result = await self.db.execute(
            select(CreditPricing).where(
                and_(
                    CreditPricing.effective_from <= datetime.utcnow(),
                    CreditPricing.effective_to.is_(None) | (CreditPricing.effective_to > datetime.utcnow())
                )
            ).order_by(CreditPricing.resource_type, CreditPricing.tier)
        )
        
        pricing_list = pricing_result.scalars().all()
        
        # Organize by resource type and tier
        pricing_structure = {}
        
        for pricing in pricing_list:
            if pricing.resource_type not in pricing_structure:
                pricing_structure[pricing.resource_type] = {}
            
            pricing_structure[pricing.resource_type][pricing.tier] = {
                "credits_per_unit": float(pricing.credits_per_unit),
                "unit_name": pricing.unit_name,
                "region": pricing.region,
                "effective_from": pricing.effective_from.isoformat()
            }
        
        return {
            "pricing_structure": pricing_structure,
            "base_exchange_rate": 100,  # credits per USD
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def _get_or_create_credit_account(self, user_id: uuid.UUID) -> ComputeCredit:
        """Get or create credit account for user"""
        
        result = await self.db.execute(
            select(ComputeCredit).where(ComputeCredit.owner_id == user_id)
        )
        
        account = result.scalar_one_or_none()
        
        if not account:
            # Get user's organization
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            account = ComputeCredit(
                owner_id=user_id,
                organization_id=user.organization_id if user else None,
                balance=Decimal('0'),
                reserved_balance=Decimal('0')
            )
            
            self.db.add(account)
            await self.db.flush()
        
        return account
    
    async def _check_auto_recharge(self, credit_account: ComputeCredit):
        """Check if auto-recharge should be triggered"""
        
        if not credit_account.auto_recharge_enabled:
            return
        
        available_balance = credit_account.balance - credit_account.reserved_balance
        
        if available_balance <= (credit_account.auto_recharge_threshold or Decimal('0')):
            # Trigger auto-recharge
            await self._trigger_auto_recharge(credit_account)
    
    async def _trigger_auto_recharge(self, credit_account: ComputeCredit):
        """Trigger automatic credit purchase"""
        
        # This would integrate with payment processing
        # For now, just log the intent
        recharge_amount = credit_account.auto_recharge_amount or Decimal('1000')
        
        # Create a pending auto-purchase record
        transaction = CreditTransaction(
            user_id=credit_account.owner_id,
            organization_id=credit_account.organization_id,
            transaction_type=CreditTransactionType.AUTO_PURCHASE,
            amount=recharge_amount,
            balance_before=credit_account.balance,
            balance_after=credit_account.balance,  # Will be updated when payment completes
            description=f"Auto-recharge triggered for {recharge_amount} credits",
            metadata={
                "auto_recharge": True,
                "threshold": float(credit_account.auto_recharge_threshold),
                "status": "pending_payment"
            }
        )
        
        self.db.add(transaction)
        await self.db.commit()
        
        # TODO: Trigger payment processing workflow