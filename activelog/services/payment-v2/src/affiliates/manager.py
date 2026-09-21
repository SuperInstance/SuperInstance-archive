from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import secrets

from ..database import (
    AffiliateProgram, AffiliateCommission, User, CreditTransaction, 
    CreditTransactionType, ComputeCredit
)

class AffiliateManager:
    """Manages affiliate programs, referrals, and commission calculations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_affiliate_program(
        self, 
        user_id: uuid.UUID,
        commission_rate: Decimal = Decimal('0.1'),
        tier_level: int = 1
    ) -> Dict[str, Any]:
        """Create affiliate program for user"""
        
        # Check if user already has affiliate program
        existing = await self.db.execute(
            select(AffiliateProgram).where(AffiliateProgram.affiliate_id == user_id)
        )
        
        if existing.scalar_one_or_none():
            raise ValueError("User already has an affiliate program")
        
        # Generate unique affiliate code
        affiliate_code = await self._generate_affiliate_code(user_id)
        
        # Update user with affiliate code
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        user.affiliate_code = affiliate_code
        
        # Create affiliate program
        program = AffiliateProgram(
            affiliate_id=user_id,
            commission_rate=commission_rate,
            tier_level=tier_level
        )
        
        self.db.add(program)
        await self.db.commit()
        
        return {
            "success": True,
            "affiliate_id": str(user_id),
            "affiliate_code": affiliate_code,
            "commission_rate": float(commission_rate),
            "tier_level": tier_level
        }
    
    async def process_referral(
        self,
        affiliate_code: str,
        new_user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Process new user referral"""
        
        # Find affiliate by code
        affiliate_result = await self.db.execute(
            select(User).where(User.affiliate_code == affiliate_code)
        )
        affiliate = affiliate_result.scalar_one_or_none()
        
        if not affiliate:
            return {"success": False, "error": "Invalid affiliate code"}
        
        # Update new user with referrer
        new_user_result = await self.db.execute(
            select(User).where(User.id == new_user_id)
        )
        new_user = new_user_result.scalar_one_or_none()
        
        if not new_user:
            return {"success": False, "error": "New user not found"}
        
        if new_user.referrer_id:
            return {"success": False, "error": "User already has a referrer"}
        
        new_user.referrer_id = affiliate.id
        
        # Award welcome bonus to new user
        welcome_bonus = await self._award_welcome_bonus(new_user_id)
        
        # Award referral bonus to affiliate
        referral_bonus = await self._award_referral_bonus(affiliate.id, new_user_id)
        
        await self.db.commit()
        
        return {
            "success": True,
            "affiliate_id": str(affiliate.id),
            "new_user_id": str(new_user_id),
            "welcome_bonus": welcome_bonus,
            "referral_bonus": referral_bonus
        }
    
    async def calculate_commission(
        self,
        affiliate_id: uuid.UUID,
        transaction_amount: Decimal,
        transaction_id: str
    ) -> Dict[str, Any]:
        """Calculate commission for affiliate based on referred user transaction"""
        
        # Get affiliate program
        program_result = await self.db.execute(
            select(AffiliateProgram).where(
                and_(
                    AffiliateProgram.affiliate_id == affiliate_id,
                    AffiliateProgram.status == "active"
                )
            )
        )
        program = program_result.scalar_one_or_none()
        
        if not program:
            return {"success": False, "error": "No active affiliate program"}
        
        # Calculate commission with tier bonuses
        base_commission = transaction_amount * program.commission_rate
        tier_multiplier = self._get_tier_multiplier(program.tier_level)
        final_commission = base_commission * tier_multiplier
        
        return {
            "base_commission": float(base_commission),
            "tier_multiplier": float(tier_multiplier),
            "final_commission": float(final_commission),
            "commission_rate": float(program.commission_rate),
            "tier_level": program.tier_level
        }
    
    async def process_commission(
        self,
        affiliate_id: uuid.UUID,
        referred_user_id: uuid.UUID,
        transaction_id: str,
        original_amount: Decimal
    ) -> Dict[str, Any]:
        """Process and award commission to affiliate"""
        
        # Calculate commission
        commission_calc = await self.calculate_commission(
            affiliate_id, original_amount, transaction_id
        )
        
        if not commission_calc.get("success", True):
            return commission_calc
        
        commission_amount = Decimal(str(commission_calc["final_commission"]))
        
        # Create commission record
        commission = AffiliateCommission(
            affiliate_id=affiliate_id,
            referred_user_id=referred_user_id,
            transaction_id=uuid.UUID(transaction_id) if transaction_id else None,
            commission_amount=commission_amount,
            commission_rate=Decimal(str(commission_calc["commission_rate"])),
            original_amount=original_amount,
            status="pending"
        )
        
        self.db.add(commission)
        
        # Award commission credits to affiliate
        await self._award_commission_credits(affiliate_id, commission_amount, str(commission.id))
        
        # Update affiliate program lifetime earnings
        program_result = await self.db.execute(
            select(AffiliateProgram).where(AffiliateProgram.affiliate_id == affiliate_id)
        )
        program = program_result.scalar_one()
        program.lifetime_earnings += commission_amount
        
        # Check for tier upgrade
        await self._check_tier_upgrade(program)
        
        commission.status = "paid"
        await self.db.commit()
        
        return {
            "success": True,
            "commission_id": str(commission.id),
            "amount": float(commission_amount),
            "status": "paid"
        }
    
    async def get_affiliate_stats(
        self,
        affiliate_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive affiliate statistics"""
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)
        
        # Get affiliate program
        program_result = await self.db.execute(
            select(AffiliateProgram).where(AffiliateProgram.affiliate_id == affiliate_id)
        )
        program = program_result.scalar_one_or_none()
        
        if not program:
            return {"error": "Affiliate program not found"}
        
        # Get referral count
        referral_result = await self.db.execute(
            select(func.count(User.id)).where(User.referrer_id == affiliate_id)
        )
        total_referrals = referral_result.scalar()
        
        # Get recent referrals
        recent_referrals_result = await self.db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.referrer_id == affiliate_id,
                    User.created_at >= start_date
                )
            )
        )
        recent_referrals = recent_referrals_result.scalar()
        
        # Get commission stats
        commission_result = await self.db.execute(
            select(
                func.count(AffiliateCommission.id),
                func.sum(AffiliateCommission.commission_amount)
            ).where(AffiliateCommission.affiliate_id == affiliate_id)
        )
        
        commission_count, total_commissions = commission_result.one()
        total_commissions = total_commissions or Decimal('0')
        
        # Get recent commissions
        recent_commission_result = await self.db.execute(
            select(func.sum(AffiliateCommission.commission_amount)).where(
                and_(
                    AffiliateCommission.affiliate_id == affiliate_id,
                    AffiliateCommission.created_at >= start_date
                )
            )
        )
        recent_commissions = recent_commission_result.scalar() or Decimal('0')
        
        # Get top referrals by generated commissions
        top_referrals_result = await self.db.execute(
            select(
                AffiliateCommission.referred_user_id,
                func.sum(AffiliateCommission.commission_amount)
            ).where(AffiliateCommission.affiliate_id == affiliate_id)
            .group_by(AffiliateCommission.referred_user_id)
            .order_by(desc(func.sum(AffiliateCommission.commission_amount)))
            .limit(5)
        )
        top_referrals = top_referrals_result.all()
        
        return {
            "affiliate_id": str(affiliate_id),
            "program_status": program.status,
            "tier_level": program.tier_level,
            "commission_rate": float(program.commission_rate),
            "lifetime_earnings": float(program.lifetime_earnings),
            "total_referrals": total_referrals,
            "recent_referrals": recent_referrals,
            "total_commissions": float(total_commissions),
            "recent_commissions": float(recent_commissions),
            "commission_count": commission_count,
            "top_referrals": [
                {
                    "user_id": str(user_id),
                    "total_commissions": float(total)
                }
                for user_id, total in top_referrals
            ],
            "period_days": period_days,
            "next_tier_requirement": self._get_next_tier_requirement(program.tier_level),
            "payout_threshold": float(program.payout_threshold)
        }
    
    async def get_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get affiliate leaderboard"""
        
        result = await self.db.execute(
            select(
                AffiliateProgram.affiliate_id,
                AffiliateProgram.lifetime_earnings,
                AffiliateProgram.tier_level,
                func.count(User.id).label('referral_count')
            )
            .outerjoin(User, User.referrer_id == AffiliateProgram.affiliate_id)
            .where(AffiliateProgram.status == "active")
            .group_by(AffiliateProgram.affiliate_id, AffiliateProgram.lifetime_earnings, AffiliateProgram.tier_level)
            .order_by(desc(AffiliateProgram.lifetime_earnings))
            .limit(limit)
        )
        
        leaderboard = []
        for rank, (affiliate_id, earnings, tier, referrals) in enumerate(result.all(), 1):
            leaderboard.append({
                "rank": rank,
                "affiliate_id": str(affiliate_id),
                "lifetime_earnings": float(earnings),
                "tier_level": tier,
                "total_referrals": referrals
            })
        
        return leaderboard
    
    async def process_batch_commissions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process multiple commissions in batch"""
        
        results = []
        total_processed = 0
        total_failed = 0
        
        for tx_data in transactions:
            try:
                # Check if referred user transaction
                user_result = await self.db.execute(
                    select(User).where(User.id == tx_data["user_id"])
                )
                user = user_result.scalar_one_or_none()
                
                if user and user.referrer_id:
                    result = await self.process_commission(
                        affiliate_id=user.referrer_id,
                        referred_user_id=user.id,
                        transaction_id=tx_data["transaction_id"],
                        original_amount=Decimal(str(tx_data["amount"]))
                    )
                    
                    if result.get("success"):
                        total_processed += 1
                    else:
                        total_failed += 1
                    
                    results.append(result)
                
            except Exception as e:
                total_failed += 1
                results.append({
                    "success": False,
                    "error": str(e),
                    "transaction_id": tx_data.get("transaction_id")
                })
        
        return {
            "total_processed": total_processed,
            "total_failed": total_failed,
            "success_rate": total_processed / len(transactions) if transactions else 0,
            "results": results
        }
    
    async def _generate_affiliate_code(self, user_id: uuid.UUID) -> str:
        """Generate unique affiliate code"""
        
        # Create base from user ID and timestamp
        base = f"{user_id}{datetime.utcnow().timestamp()}"
        hash_object = hashlib.sha256(base.encode())
        hash_hex = hash_object.hexdigest()
        
        # Take first 8 characters and make uppercase
        code = hash_hex[:8].upper()
        
        # Ensure uniqueness
        existing = await self.db.execute(
            select(User).where(User.affiliate_code == code)
        )
        
        if existing.scalar_one_or_none():
            # If collision, add random suffix
            code += secrets.token_hex(2).upper()
        
        return code
    
    async def _award_welcome_bonus(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Award welcome bonus to new referred user"""
        
        welcome_bonus = Decimal('100')  # 100 credits welcome bonus
        
        # Get or create credit account
        from ..credits.economics import ComputeEconomics
        economics = ComputeEconomics(self.db)
        account = await economics._get_or_create_credit_account(user_id)
        
        # Create transaction
        transaction = CreditTransaction(
            user_id=user_id,
            organization_id=account.organization_id,
            transaction_type=CreditTransactionType.BONUS,
            amount=welcome_bonus,
            balance_before=account.balance,
            balance_after=account.balance + welcome_bonus,
            description="Welcome bonus for new user referral",
            metadata={"bonus_type": "welcome", "referral": True}
        )
        
        self.db.add(transaction)
        
        # Update balance
        account.balance += welcome_bonus
        account.updated_at = datetime.utcnow()
        
        return {
            "amount": float(welcome_bonus),
            "transaction_id": str(transaction.id)
        }
    
    async def _award_referral_bonus(self, affiliate_id: uuid.UUID, referred_user_id: uuid.UUID) -> Dict[str, Any]:
        """Award referral bonus to affiliate"""
        
        referral_bonus = Decimal('50')  # 50 credits for successful referral
        
        # Get or create credit account
        from ..credits.economics import ComputeEconomics
        economics = ComputeEconomics(self.db)
        account = await economics._get_or_create_credit_account(affiliate_id)
        
        # Create transaction
        transaction = CreditTransaction(
            user_id=affiliate_id,
            organization_id=account.organization_id,
            transaction_type=CreditTransactionType.AFFILIATE_COMMISSION,
            amount=referral_bonus,
            balance_before=account.balance,
            balance_after=account.balance + referral_bonus,
            description=f"Referral bonus for user {referred_user_id}",
            metadata={
                "bonus_type": "referral",
                "referred_user_id": str(referred_user_id)
            }
        )
        
        self.db.add(transaction)
        
        # Update balance
        account.balance += referral_bonus
        account.updated_at = datetime.utcnow()
        
        return {
            "amount": float(referral_bonus),
            "transaction_id": str(transaction.id)
        }
    
    async def _award_commission_credits(
        self, 
        affiliate_id: uuid.UUID, 
        commission_amount: Decimal,
        commission_id: str
    ):
        """Award commission credits to affiliate"""
        
        from ..credits.economics import ComputeEconomics
        economics = ComputeEconomics(self.db)
        account = await economics._get_or_create_credit_account(affiliate_id)
        
        # Create transaction
        transaction = CreditTransaction(
            user_id=affiliate_id,
            organization_id=account.organization_id,
            transaction_type=CreditTransactionType.AFFILIATE_COMMISSION,
            amount=commission_amount,
            balance_before=account.balance,
            balance_after=account.balance + commission_amount,
            description=f"Affiliate commission payment",
            metadata={
                "commission_id": commission_id,
                "commission_type": "referral_earning"
            }
        )
        
        self.db.add(transaction)
        
        # Update balance
        account.balance += commission_amount
        account.updated_at = datetime.utcnow()
    
    def _get_tier_multiplier(self, tier_level: int) -> Decimal:
        """Get commission multiplier based on tier level"""
        multipliers = {
            1: Decimal('1.0'),    # Bronze - 100%
            2: Decimal('1.2'),    # Silver - 120%
            3: Decimal('1.5'),    # Gold - 150%
            4: Decimal('2.0'),    # Platinum - 200%
            5: Decimal('2.5')     # Diamond - 250%
        }
        return multipliers.get(tier_level, Decimal('1.0'))
    
    def _get_next_tier_requirement(self, current_tier: int) -> Optional[Dict[str, Any]]:
        """Get requirements for next tier level"""
        requirements = {
            1: {"earnings": 1000, "referrals": 10, "tier_name": "Silver"},
            2: {"earnings": 5000, "referrals": 25, "tier_name": "Gold"},
            3: {"earnings": 15000, "referrals": 50, "tier_name": "Platinum"},
            4: {"earnings": 50000, "referrals": 100, "tier_name": "Diamond"},
            5: None  # Max tier
        }
        return requirements.get(current_tier)
    
    async def _check_tier_upgrade(self, program: AffiliateProgram):
        """Check if affiliate qualifies for tier upgrade"""
        
        # Get referral count
        referral_result = await self.db.execute(
            select(func.count(User.id)).where(User.referrer_id == program.affiliate_id)
        )
        referral_count = referral_result.scalar()
        
        # Check upgrade conditions
        next_tier_req = self._get_next_tier_requirement(program.tier_level)
        
        if next_tier_req and (
            program.lifetime_earnings >= next_tier_req["earnings"] and
            referral_count >= next_tier_req["referrals"]
        ):
            program.tier_level += 1
            # Award tier upgrade bonus
            bonus_credits = Decimal('500') * program.tier_level
            await self._award_commission_credits(
                program.affiliate_id, 
                bonus_credits, 
                f"tier_upgrade_{program.tier_level}"
            )