from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter()

@router.get("/rates/{region}")
async def get_tax_rates(region: str, db: AsyncSession = Depends(get_db)):
    """Get tax rates for region"""
    tax_rates = {
        "US": {"sales_tax": 0.08, "type": "sales_tax"},
        "GB": {"vat": 0.20, "type": "VAT"},
        "DE": {"vat": 0.19, "type": "VAT"},
        "CA": {"gst": 0.05, "type": "GST"}
    }
    
    return tax_rates.get(region.upper(), {"error": "Region not found"})

@router.post("/calculate")
async def calculate_tax(
    amount: float,
    region: str,
    tax_type: str = "auto",
    db: AsyncSession = Depends(get_db)
):
    """Calculate tax for amount and region"""
    # Mock tax calculation
    tax_rate = 0.08 if region.upper() == "US" else 0.20
    tax_amount = amount * tax_rate
    
    return {
        "subtotal": amount,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": amount + tax_amount,
        "region": region
    }