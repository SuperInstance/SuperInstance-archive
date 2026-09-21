"""
Affiliate Program Implementation
Manages referrals and commission distribution
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
import secrets
import string

from ...models.database import (
    User, AffiliateProgram, Transaction, TransactionType, TransactionStatus
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class AffiliateManager:
    """Manages affiliate program and referral rewards"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        self.commission_rate = settings.compute_credits.affiliate_commission_rate
        self.signup_bonus_cc = settings.compute_credits.free_tier_credits
        
    def _generate_affiliate_code(self, username: str) -> str:
        """Generate unique affiliate code for user"""
        # Create base code from username
        base = username.upper()[:4]
        
        # Add random suffix
        suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        
        code = f"{base}{suffix}"
        
        # Ensure uniqueness
        existing = self.db.query(User).filter(User.affiliate_code == code).first()
        if existing:
            # Add more randomness if collision
            extra = ''.join(secrets.choice(string.digits) for _ in range(2))
            code = f"{code}{extra}"
        
        return code
    
    async def create_affiliate_account(self, user_id: str) -> str:
        """Create affiliate account for user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.affiliate_code:
            return user.affiliate_code
        
        # Generate unique affiliate code
        affiliate_code = self._generate_affiliate_code(user.username)
        
        # Update user record
        user.affiliate_code = affiliate_code
        user.referral_count = 0
        user.total_affiliate_earnings_cc = Decimal("0")
        
        self.db.commit()
        
        logger.info(f"Created affiliate account for user {user_id} with code {affiliate_code}")
        return affiliate_code
    
    async def process_referral(
        self,
        referrer_code: str,
        new_user_id: str
    ) -> Optional[AffiliateProgram]:
        """Process a new user referral"""
        
        # Find referrer by affiliate code
        referrer = self.db.query(User).filter(User.affiliate_code == referrer_code).first()
        if not referrer:
            logger.warning(f"Invalid affiliate code: {referrer_code}")
            return None
        
        # Verify new user exists
        new_user = self.db.query(User).filter(User.id == new_user_id).first()
        if not new_user:
            raise ValueError(f"New user {new_user_id} not found")
        
        # Check if referral already exists
        existing_referral = (
            self.db.query(AffiliateProgram)
            .filter(
                and_(
                    AffiliateProgram.referrer_id == referrer.id,
                    AffiliateProgram.referee_id == new_user_id
                )
            )
            .first()
        )
        
        if existing_referral:
            logger.warning(f"Referral already exists between {referrer.id} and {new_user_id}")
            return existing_referral
        
        # Create affiliate program record
        affiliate_program = AffiliateProgram(
            referrer_id=referrer.id,
            referee_id=new_user_id,
            commission_rate=self.commission_rate,
            total_commission_cc=Decimal("0"),
            is_active=True
        )
        
        # Award signup bonus to referrer (immediate reward)
        signup_commission = self.signup_bonus_cc * self.commission_rate
        
        try:
            # Award commission to referrer
            await self.cc_system.add_credits(
                referrer.id,
                signup_commission,
                TransactionType.AFFILIATE_COMMISSION,
                f"Referral signup bonus for {new_user.username}",
                metadata={
                    "affiliate_code": referrer_code,
                    "referee_id": new_user_id,
                    "referee_username": new_user.username,
                    "commission_type": "signup_bonus"
                }
            )
            
            # Update affiliate program record
            affiliate_program.total_commission_cc += signup_commission
            affiliate_program.last_transaction_at = datetime.utcnow()
            
            # Update referrer stats
            referrer.referral_count += 1
            referrer.total_affiliate_earnings_cc += signup_commission
            
            self.db.add(affiliate_program)
            self.db.commit()
            
            logger.info(
                f"Processed referral: {referrer.username} referred {new_user.username}, "
                f"earned {signup_commission} CC"
            )
            
            return affiliate_program
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process referral: {str(e)}")
            raise
    
    async def award_purchase_commission(
        self,
        referee_id: str,
        purchase_amount_cc: Decimal,
        description: str = "Purchase commission"
    ) -> List[Transaction]:
        """Award commission to referrer when referee makes purchase"""
        
        # Find active affiliate relationships for this referee
        affiliate_programs = (
            self.db.query(AffiliateProgram)
            .filter(
                and_(
                    AffiliateProgram.referee_id == referee_id,
                    AffiliateProgram.is_active == True
                )
            )
            .all()
        )
        
        transactions = []
        
        for program in affiliate_programs:
            try:
                # Calculate commission
                commission_amount = purchase_amount_cc * program.commission_rate
                
                # Award commission to referrer
                transaction = await self.cc_system.add_credits(
                    program.referrer_id,
                    commission_amount,
                    TransactionType.AFFILIATE_COMMISSION,
                    f"Commission from {description}",
                    metadata={
                        "referee_id": referee_id,
                        "purchase_amount_cc": str(purchase_amount_cc),
                        "commission_rate": str(program.commission_rate),
                        "commission_type": "purchase"
                    }
                )
                
                # Update program stats
                program.total_commission_cc += commission_amount
                program.last_transaction_at = datetime.utcnow()
                
                # Update referrer stats
                referrer = self.db.query(User).filter(User.id == program.referrer_id).first()
                if referrer:
                    referrer.total_affiliate_earnings_cc += commission_amount
                
                transactions.append(transaction)
                
                logger.info(
                    f"Awarded {commission_amount} CC commission to {program.referrer_id} "
                    f"for purchase by {referee_id}"
                )
                
            except Exception as e:
                logger.error(f"Failed to award commission for program {program.id}: {str(e)}")
                continue
        
        self.db.commit()
        return transactions
    
    async def get_affiliate_stats(self, user_id: str) -> Dict:
        """Get affiliate statistics for user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get affiliate programs where user is referrer
        referrals = (
            self.db.query(AffiliateProgram)
            .filter(AffiliateProgram.referrer_id == user_id)
            .all()
        )
        
        # Get transaction history for affiliate commissions
        commission_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.AFFILIATE_COMMISSION,
                    Transaction.status == TransactionStatus.COMPLETED
                )
            )
            .order_by(desc(Transaction.created_at))
            .limit(50)
            .all()
        )
        
        # Calculate monthly statistics
        this_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_commissions = (
            self.db.query(func.sum(Transaction.amount_cc))
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.AFFILIATE_COMMISSION,
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= this_month_start
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Get referee details
        referee_stats = []
        for program in referrals:
            referee = self.db.query(User).filter(User.id == program.referee_id).first()
            if referee:
                referee_stats.append({
                    "referee_id": program.referee_id,
                    "referee_username": referee.username,
                    "joined_date": program.created_at.isoformat(),
                    "total_commission_earned": float(program.total_commission_cc),
                    "last_transaction": program.last_transaction_at.isoformat() if program.last_transaction_at else None,
                    "is_active": program.is_active
                })
        
        return {
            "user_id": user_id,
            "affiliate_code": user.affiliate_code,
            "total_referrals": user.referral_count,
            "total_earnings_cc": float(user.total_affiliate_earnings_cc),
            "monthly_earnings_cc": float(monthly_commissions),
            "commission_rate": float(self.commission_rate * 100),  # As percentage
            "referee_details": referee_stats,
            "recent_transactions": [
                {
                    "date": tx.created_at.isoformat(),
                    "amount_cc": float(tx.amount_cc),
                    "description": tx.description,
                    "metadata": tx.metadata
                }
                for tx in commission_transactions
            ]
        }
    
    async def get_referral_link(self, user_id: str, base_url: str = "https://activelog.com") -> str:
        """Generate referral link for user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if not user.affiliate_code:
            user.affiliate_code = await self.create_affiliate_account(user_id)
        
        return f"{base_url}/signup?ref={user.affiliate_code}"
    
    async def deactivate_affiliate_program(self, referrer_id: str, referee_id: str) -> bool:
        """Deactivate affiliate program relationship"""
        
        program = (
            self.db.query(AffiliateProgram)
            .filter(
                and_(
                    AffiliateProgram.referrer_id == referrer_id,
                    AffiliateProgram.referee_id == referee_id
                )
            )
            .first()
        )
        
        if not program:
            return False
        
        program.is_active = False
        self.db.commit()
        
        logger.info(f"Deactivated affiliate program between {referrer_id} and {referee_id}")
        return True
    
    async def get_top_affiliates(self, limit: int = 10) -> List[Dict]:
        """Get top performing affiliates"""
        
        top_affiliates = (
            self.db.query(User)
            .filter(User.affiliate_code.isnot(None))
            .order_by(desc(User.total_affiliate_earnings_cc))
            .limit(limit)
            .all()
        )
        
        result = []
        for user in top_affiliates:
            # Get recent activity
            recent_activity = (
                self.db.query(func.count(AffiliateProgram.id))
                .filter(
                    and_(
                        AffiliateProgram.referrer_id == user.id,
                        AffiliateProgram.created_at >= datetime.utcnow() - timedelta(days=30)
                    )
                )
                .scalar() or 0
            )
            
            result.append({
                "user_id": user.id,
                "username": user.username,
                "affiliate_code": user.affiliate_code,
                "total_referrals": user.referral_count,
                "total_earnings_cc": float(user.total_affiliate_earnings_cc),
                "recent_referrals_30d": recent_activity
            })
        
        return result
    
    async def calculate_affiliate_projections(
        self,
        user_id: str,
        projected_referrals_per_month: int = 10,
        avg_referee_spending_cc: Decimal = Decimal("100")
    ) -> Dict:
        """Calculate affiliate earnings projections"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Signup bonus per referral
        signup_commission_per_referral = self.signup_bonus_cc * self.commission_rate
        
        # Ongoing commission per referral
        ongoing_commission_per_referral = avg_referee_spending_cc * self.commission_rate
        
        # Monthly projections
        monthly_signup_commissions = signup_commission_per_referral * projected_referrals_per_month
        monthly_ongoing_commissions = ongoing_commission_per_referral * user.referral_count  # From existing referrals
        monthly_total = monthly_signup_commissions + monthly_ongoing_commissions
        
        return {
            "user_id": user_id,
            "current_referrals": user.referral_count,
            "commission_rate_percentage": float(self.commission_rate * 100),
            "projections": {
                "referrals_per_month": projected_referrals_per_month,
                "avg_referee_spending_cc": float(avg_referee_spending_cc),
                "signup_commission_per_referral": float(signup_commission_per_referral),
                "ongoing_commission_per_referral": float(ongoing_commission_per_referral),
                "monthly_signup_commissions": float(monthly_signup_commissions),
                "monthly_ongoing_commissions": float(monthly_ongoing_commissions),
                "total_monthly_earnings": float(monthly_total),
                "annual_projection": float(monthly_total * 12)
            }
        }