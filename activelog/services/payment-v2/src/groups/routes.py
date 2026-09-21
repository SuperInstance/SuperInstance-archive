from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from ..database import get_db

router = APIRouter()

@router.post("/create-pool")
async def create_credit_pool(
    organization_id: uuid.UUID,
    name: str,
    initial_balance: float,
    db: AsyncSession = Depends(get_db)
):
    """Create a shared credit pool"""
    return {
        "message": "Credit pool created",
        "pool_id": str(uuid.uuid4()),
        "organization_id": str(organization_id),
        "name": name,
        "balance": initial_balance
    }

@router.post("/allocate")
async def allocate_credits(
    pool_id: uuid.UUID,
    user_id: uuid.UUID,
    amount: float,
    db: AsyncSession = Depends(get_db)
):
    """Allocate credits from pool to user"""
    return {
        "message": "Credits allocated",
        "pool_id": str(pool_id),
        "user_id": str(user_id),
        "allocated_amount": amount
    }