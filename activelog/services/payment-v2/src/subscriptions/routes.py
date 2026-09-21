from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..database import get_db

router = APIRouter()

@router.post("/create")
async def create_subscription(
    user_id: uuid.UUID,
    plan_name: str,
    credits_per_cycle: float,
    cycle_amount: float,
    billing_cycle: str = "monthly",
    db: AsyncSession = Depends(get_db)
):
    """Create credit-based subscription"""
    return {
        "subscription_id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "plan_name": plan_name,
        "credits_per_cycle": credits_per_cycle,
        "cycle_amount": cycle_amount,
        "billing_cycle": billing_cycle,
        "status": "active"
    }

@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get subscription details"""
    return {
        "subscription_id": str(subscription_id),
        "status": "active",
        "next_billing_date": "2024-09-24T00:00:00Z",
        "credits_allocated_this_cycle": 1000,
        "credits_used_this_cycle": 750
    }