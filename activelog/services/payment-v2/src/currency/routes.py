from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter()

@router.get("/rates")
async def get_exchange_rates(db: AsyncSession = Depends(get_db)):
    """Get current exchange rates"""
    return {
        "base_currency": "USD", 
        "rates": {
            "EUR": 0.85,
            "GBP": 0.73,
            "JPY": 149.50,
            "CAD": 1.35,
            "AUD": 1.52
        },
        "updated": "2024-08-24T12:00:00Z"
    }

@router.post("/convert")
async def convert_currency(
    from_currency: str,
    to_currency: str,
    amount: float,
    db: AsyncSession = Depends(get_db)
):
    """Convert between currencies"""
    return {
        "from_currency": from_currency,
        "to_currency": to_currency,
        "original_amount": amount,
        "converted_amount": amount * 0.85,  # Mock conversion
        "exchange_rate": 0.85
    }