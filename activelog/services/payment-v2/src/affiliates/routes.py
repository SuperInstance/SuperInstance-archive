from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
import uuid

from ..database import get_db
from .manager import AffiliateManager
from .schemas import (
    CreateAffiliateProgramRequest, ProcessReferralRequest,
    ProcessCommissionRequest, BatchCommissionRequest
)

router = APIRouter()

@router.post("/program")
async def create_affiliate_program(
    request: CreateAffiliateProgramRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create affiliate program for user"""
    manager = AffiliateManager(db)
    
    try:
        result = await manager.create_affiliate_program(
            user_id=request.user_id,
            commission_rate=Decimal(str(request.commission_rate)),
            tier_level=request.tier_level
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/referral")
async def process_referral(
    request: ProcessReferralRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process new user referral"""
    manager = AffiliateManager(db)
    
    try:
        result = await manager.process_referral(
            affiliate_code=request.affiliate_code,
            new_user_id=request.new_user_id
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/commission")
async def process_commission(
    request: ProcessCommissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process commission for affiliate"""
    manager = AffiliateManager(db)
    
    try:
        result = await manager.process_commission(
            affiliate_id=request.affiliate_id,
            referred_user_id=request.referred_user_id,
            transaction_id=request.transaction_id,
            original_amount=Decimal(str(request.original_amount))
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/commission/batch")
async def process_batch_commissions(
    request: BatchCommissionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process multiple commissions in batch"""
    manager = AffiliateManager(db)
    
    try:
        transactions = [tx.dict() for tx in request.transactions]
        result = await manager.process_batch_commissions(transactions)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{affiliate_id}")
async def get_affiliate_stats(
    affiliate_id: uuid.UUID,
    period_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get affiliate statistics"""
    manager = AffiliateManager(db)
    
    try:
        stats = await manager.get_affiliate_stats(
            affiliate_id=affiliate_id,
            period_days=period_days
        )
        
        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/leaderboard")
async def get_affiliate_leaderboard(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get affiliate leaderboard"""
    manager = AffiliateManager(db)
    
    try:
        leaderboard = await manager.get_leaderboard(limit=limit)
        return {"leaderboard": leaderboard, "total_affiliates": len(leaderboard)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/commission/calculate")
async def calculate_commission(
    affiliate_id: uuid.UUID,
    transaction_amount: float,
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Calculate commission for a transaction"""
    manager = AffiliateManager(db)
    
    try:
        calculation = await manager.calculate_commission(
            affiliate_id=affiliate_id,
            transaction_amount=Decimal(str(transaction_amount)),
            transaction_id=transaction_id
        )
        
        return calculation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tiers")
async def get_tier_info():
    """Get affiliate tier information"""
    return {
        "tiers": [
            {
                "level": 1,
                "name": "Bronze",
                "commission_multiplier": 1.0,
                "requirements": {
                    "lifetime_earnings": 0,
                    "referrals": 0
                },
                "benefits": ["Base commission rate", "Monthly reports"]
            },
            {
                "level": 2,
                "name": "Silver",
                "commission_multiplier": 1.2,
                "requirements": {
                    "lifetime_earnings": 1000,
                    "referrals": 10
                },
                "benefits": ["20% bonus on commissions", "Priority support", "Advanced analytics"]
            },
            {
                "level": 3,
                "name": "Gold",
                "commission_multiplier": 1.5,
                "requirements": {
                    "lifetime_earnings": 5000,
                    "referrals": 25
                },
                "benefits": ["50% bonus on commissions", "Custom promotional materials", "Dedicated account manager"]
            },
            {
                "level": 4,
                "name": "Platinum",
                "commission_multiplier": 2.0,
                "requirements": {
                    "lifetime_earnings": 15000,
                    "referrals": 50
                },
                "benefits": ["100% bonus on commissions", "Early access to features", "Co-marketing opportunities"]
            },
            {
                "level": 5,
                "name": "Diamond",
                "commission_multiplier": 2.5,
                "requirements": {
                    "lifetime_earnings": 50000,
                    "referrals": 100
                },
                "benefits": ["150% bonus on commissions", "Revenue sharing", "Strategic partnership opportunities"]
            }
        ],
        "bonus_structure": {
            "welcome_bonus": 100,  # credits for new referrals
            "referral_bonus": 50,  # credits for successful referral
            "tier_upgrade_bonus": "500 credits × tier level"
        }
    }

@router.get("/performance/{affiliate_id}")
async def get_performance_metrics(
    affiliate_id: uuid.UUID,
    months_back: int = 12,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed performance metrics for affiliate"""
    # This would implement detailed performance analytics
    # Including conversion rates, top-performing referrals, etc.
    
    return {
        "affiliate_id": str(affiliate_id),
        "message": "Performance metrics endpoint - would include detailed analytics",
        "metrics": {
            "conversion_rate": 15.5,  # percentage
            "average_commission_per_referral": 125.50,
            "top_converting_channels": ["organic", "social", "email"],
            "monthly_performance": "Array of monthly data would be here"
        }
    }