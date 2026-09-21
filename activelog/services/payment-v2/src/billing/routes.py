from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import uuid

from ..database import get_db
from .bulk_manager import BulkBillingManager

router = APIRouter()

@router.post("/organization/setup")
async def setup_organization_billing(
    organization_id: uuid.UUID,
    billing_period: str = "monthly",
    credit_limit: float = 10000.0,
    auto_billing_enabled: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Set up organization billing cycle"""
    manager = BulkBillingManager(db)
    
    try:
        result = await manager.create_organization_billing_cycle(
            organization_id=organization_id,
            billing_period=billing_period,
            credit_limit=credit_limit,
            auto_billing_enabled=auto_billing_enabled
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/usage-breakdown/{organization_id}")
async def get_usage_breakdown(
    organization_id: uuid.UUID,
    days_back: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed usage breakdown for organization"""
    manager = BulkBillingManager(db)
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        breakdown = await manager.get_organization_usage_breakdown(
            organization_id, start_date, end_date
        )
        return breakdown
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecasts/{organization_id}")
async def get_billing_forecasts(
    organization_id: uuid.UUID,
    months_ahead: int = 3,
    db: AsyncSession = Depends(get_db)
):
    """Get billing forecasts for organization"""
    manager = BulkBillingManager(db)
    
    try:
        forecasts = await manager.get_billing_forecasts(
            organization_id, months_ahead
        )
        return forecasts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))