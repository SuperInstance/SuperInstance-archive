from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from ..database import get_db
from .economics import ComputeEconomics
from .schemas import (
    CreditConsumptionRequest, CreditPurchaseRequest, 
    CreditReservationRequest, UsageAnalyticsRequest
)

router = APIRouter()

@router.get("/balance/{user_id}")
async def get_credit_balance(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get user's credit balance"""
    economics = ComputeEconomics(db)
    
    try:
        account = await economics._get_or_create_credit_account(user_id)
        
        return {
            "user_id": str(user_id),
            "total_balance": float(account.balance),
            "reserved_balance": float(account.reserved_balance),
            "available_balance": float(account.balance - account.reserved_balance),
            "auto_recharge_enabled": account.auto_recharge_enabled,
            "auto_recharge_threshold": float(account.auto_recharge_threshold) if account.auto_recharge_threshold else None,
            "auto_recharge_amount": float(account.auto_recharge_amount) if account.auto_recharge_amount else None,
            "last_updated": account.updated_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/consume")
async def consume_credits(
    request: CreditConsumptionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Consume credits for compute usage"""
    economics = ComputeEconomics(db)
    
    try:
        result = await economics.consume_credits(
            user_id=request.user_id,
            resource_type=request.resource_type,
            units=request.units,
            tier=request.tier,
            region=request.region,
            job_id=request.job_id,
            metadata=request.metadata
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reserve")
async def reserve_credits(
    request: CreditReservationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reserve credits for a job"""
    economics = ComputeEconomics(db)
    
    try:
        result = await economics.reserve_credits(
            user_id=request.user_id,
            credits_amount=Decimal(str(request.credits_amount)),
            job_id=request.job_id,
            duration_minutes=request.duration_minutes
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/release")
async def release_credits(
    user_id: uuid.UUID,
    credits_amount: float,
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Release reserved credits"""
    economics = ComputeEconomics(db)
    
    try:
        result = await economics.release_credits(
            user_id=user_id,
            credits_amount=Decimal(str(credits_amount)),
            job_id=job_id
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/purchase")
async def purchase_credits(
    request: CreditPurchaseRequest,
    db: AsyncSession = Depends(get_db)
):
    """Purchase credits with USD payment"""
    economics = ComputeEconomics(db)
    
    try:
        result = await economics.purchase_credits(
            user_id=request.user_id,
            usd_amount=Decimal(str(request.usd_amount)),
            payment_method_id=request.payment_method_id,
            bonus_percentage=request.bonus_percentage
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-estimate")
async def estimate_cost(
    resource_type: str,
    units: float,
    tier: str = "standard",
    region: str = "global",
    db: AsyncSession = Depends(get_db)
):
    """Estimate credit cost for compute resources"""
    economics = ComputeEconomics(db)
    
    try:
        credits_needed = await economics.get_credit_cost(
            resource_type=resource_type,
            units=units,
            tier=tier,
            region=region
        )
        
        return {
            "resource_type": resource_type,
            "units": units,
            "tier": tier,
            "region": region,
            "credits_required": float(credits_needed),
            "usd_equivalent": float(credits_needed) / 100  # Assuming 100 credits = $1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics")
async def get_usage_analytics(
    user_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    days_back: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get compute usage analytics"""
    economics = ComputeEconomics(db)
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        analytics = await economics.get_usage_analytics(
            user_id=user_id,
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pricing")
async def get_pricing_tiers(db: AsyncSession = Depends(get_db)):
    """Get current pricing tiers and rates"""
    economics = ComputeEconomics(db)
    
    try:
        pricing = await economics.get_pricing_tiers()
        return pricing
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/auto-recharge/{user_id}")
async def configure_auto_recharge(
    user_id: uuid.UUID,
    enabled: bool,
    threshold: Optional[float] = None,
    amount: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """Configure auto-recharge settings"""
    economics = ComputeEconomics(db)
    
    try:
        account = await economics._get_or_create_credit_account(user_id)
        
        account.auto_recharge_enabled = enabled
        if threshold is not None:
            account.auto_recharge_threshold = Decimal(str(threshold))
        if amount is not None:
            account.auto_recharge_amount = Decimal(str(amount))
        account.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "success": True,
            "user_id": str(user_id),
            "auto_recharge_enabled": account.auto_recharge_enabled,
            "threshold": float(account.auto_recharge_threshold) if account.auto_recharge_threshold else None,
            "amount": float(account.auto_recharge_amount) if account.auto_recharge_amount else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))