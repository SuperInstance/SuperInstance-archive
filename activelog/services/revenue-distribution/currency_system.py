"""
Multi-Currency Support System
Handle multiple currencies with real-time exchange rates
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import logging
from decimal import Decimal, ROUND_HALF_UP
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class CurrencyManager:
    def __init__(self):
        # Mock exchange rates (in production, use real API)
        self.exchange_rates = {
            "USD": {"EUR": 0.85, "GBP": 0.73, "JPY": 110.0, "CAD": 1.25, "AUD": 1.35},
            "EUR": {"USD": 1.18, "GBP": 0.86, "JPY": 129.0, "CAD": 1.47, "AUD": 1.59},
            "GBP": {"USD": 1.37, "EUR": 1.16, "JPY": 150.0, "CAD": 1.71, "AUD": 1.85}
        }
    
    async def get_exchange_rates(self, base_currency: str = "USD") -> Dict[str, Any]:
        """Get current exchange rates for base currency"""
        
        rates = self.exchange_rates.get(base_currency, {})
        
        return {
            "base_currency": base_currency,
            "rates": rates,
            "last_updated": datetime.now().isoformat(),
            "provider": "mock_provider"
        }
    
    async def convert_amount(self, amount: Decimal, from_currency: str, 
                           to_currency: str) -> Dict[str, Any]:
        """Convert amount between currencies"""
        
        if from_currency == to_currency:
            return {
                "original_amount": float(amount),
                "converted_amount": float(amount),
                "from_currency": from_currency,
                "to_currency": to_currency,
                "exchange_rate": 1.0
            }
        
        # Get exchange rate
        rates = self.exchange_rates.get(from_currency, {})
        exchange_rate = rates.get(to_currency, 1.0)
        
        converted_amount = (amount * Decimal(str(exchange_rate))).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return {
            "original_amount": float(amount),
            "converted_amount": float(converted_amount),
            "from_currency": from_currency,
            "to_currency": to_currency,
            "exchange_rate": exchange_rate,
            "converted_at": datetime.now().isoformat()
        }

# Global instance
currency_manager = CurrencyManager()