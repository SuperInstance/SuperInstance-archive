"""
Currency Exchange Service for Multi-Currency Support
"""

import asyncio
import httpx
import redis
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session

from ...models.database import CurrencyExchangeRate
from ...config.settings import settings

logger = logging.getLogger(__name__)

class CurrencyConverter:
    """Currency conversion service with caching and rate management"""
    
    def __init__(self):
        self.redis_client = redis.from_url(settings.redis.url)
        self.cache_ttl = settings.currency_exchange.exchange_rate_cache_ttl
        self.api_key = settings.currency_exchange.exchange_rate_api_key
        self.supported_currencies = settings.currency_exchange.supported_currencies
        self.exchange_fee_rate = settings.currency_exchange.exchange_fee_rate
        
    async def get_exchange_rate(
        self,
        from_currency: str,
        to_currency: str,
        db: Optional[Session] = None
    ) -> Decimal:
        """Get exchange rate between two currencies"""
        
        if from_currency == to_currency:
            return Decimal("1.0")
        
        # Check cache first
        cache_key = f"exchange_rate:{from_currency}:{to_currency}"
        cached_rate = self.redis_client.get(cache_key)
        
        if cached_rate:
            try:
                return Decimal(cached_rate.decode())
            except:
                pass
        
        # Check database for recent rates
        if db:
            recent_rate = (
                db.query(CurrencyExchangeRate)
                .filter(
                    CurrencyExchangeRate.from_currency == from_currency,
                    CurrencyExchangeRate.to_currency == to_currency,
                    CurrencyExchangeRate.valid_until > datetime.utcnow()
                )
                .order_by(CurrencyExchangeRate.created_at.desc())
                .first()
            )
            
            if recent_rate:
                # Cache the rate
                self.redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    str(recent_rate.rate)
                )
                return recent_rate.rate
        
        # Fetch from external API
        try:
            rate = await self._fetch_rate_from_api(from_currency, to_currency)
            
            # Cache the rate
            self.redis_client.setex(cache_key, self.cache_ttl, str(rate))
            
            # Store in database if available
            if db:
                db_rate = CurrencyExchangeRate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=rate,
                    valid_until=datetime.utcnow() + timedelta(seconds=self.cache_ttl)
                )
                db.add(db_rate)
                db.commit()
            
            return rate
            
        except Exception as e:
            logger.error(f"Failed to fetch exchange rate {from_currency}->{to_currency}: {str(e)}")
            
            # Fallback to cached rate if available (even if expired)
            if cached_rate:
                return Decimal(cached_rate.decode())
            
            # Ultimate fallback - return 1.0 (no conversion)
            logger.warning(f"Using fallback rate of 1.0 for {from_currency}->{to_currency}")
            return Decimal("1.0")
    
    async def _fetch_rate_from_api(self, from_currency: str, to_currency: str) -> Decimal:
        """Fetch exchange rate from external API"""
        
        # Multiple API providers for redundancy
        providers = [
            self._fetch_from_currencyapi,
            self._fetch_from_exchangerate_api,
            self._fetch_from_fixer_io
        ]
        
        for provider in providers:
            try:
                rate = await provider(from_currency, to_currency)
                if rate:
                    return rate
            except Exception as e:
                logger.warning(f"Provider {provider.__name__} failed: {str(e)}")
                continue
        
        raise Exception("All exchange rate providers failed")
    
    async def _fetch_from_currencyapi(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Fetch from CurrencyAPI.com"""
        
        if not self.api_key:
            return None
        
        url = "https://api.currencyapi.com/v3/latest"
        params = {
            "apikey": self.api_key,
            "base_currency": from_currency,
            "currencies": to_currency
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "data" in data and to_currency in data["data"]:
                rate_data = data["data"][to_currency]
                return Decimal(str(rate_data["value"]))
        
        return None
    
    async def _fetch_from_exchangerate_api(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Fetch from ExchangeRate-API.com (free tier)"""
        
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if "rates" in data and to_currency in data["rates"]:
                return Decimal(str(data["rates"][to_currency]))
        
        return None
    
    async def _fetch_from_fixer_io(self, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Fetch from Fixer.io (backup)"""
        
        # Fixer.io requires API key for production
        url = f"https://api.fixer.io/latest?base={from_currency}&symbols={to_currency}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if "rates" in data and to_currency in data["rates"]:
                    return Decimal(str(data["rates"][to_currency]))
        
        return None
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        include_fee: bool = True,
        db: Optional[Session] = None
    ) -> Decimal:
        """Convert amount from one currency to another"""
        
        if from_currency == to_currency:
            return amount
        
        # Validate currencies
        if from_currency not in self.supported_currencies:
            raise ValueError(f"Unsupported source currency: {from_currency}")
        
        if to_currency not in self.supported_currencies:
            raise ValueError(f"Unsupported target currency: {to_currency}")
        
        # Get exchange rate
        rate = await self.get_exchange_rate(from_currency, to_currency, db)
        
        # Convert amount
        converted_amount = amount * rate
        
        # Apply exchange fee if requested
        if include_fee and self.exchange_fee_rate > 0:
            fee = converted_amount * self.exchange_fee_rate
            converted_amount -= fee
        
        # Round to appropriate precision
        converted_amount = converted_amount.quantize(
            Decimal("0.00000001"), 
            rounding=ROUND_HALF_UP
        )
        
        logger.info(
            f"Converted {amount} {from_currency} to {converted_amount} {to_currency} "
            f"(rate: {rate}, fee: {include_fee})"
        )
        
        return converted_amount
    
    async def get_supported_currencies(self) -> Dict[str, str]:
        """Get list of supported currencies with names"""
        
        currency_names = {
            "USD": "US Dollar",
            "EUR": "Euro",
            "GBP": "British Pound",
            "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar",
            "JPY": "Japanese Yen",
            "CNY": "Chinese Yuan",
            "INR": "Indian Rupee",
            "BRL": "Brazilian Real",
            "MXN": "Mexican Peso",
            "CHF": "Swiss Franc",
            "SGD": "Singapore Dollar",
            "HKD": "Hong Kong Dollar",
            "NZD": "New Zealand Dollar",
            "SEK": "Swedish Krona",
            "NOK": "Norwegian Krone",
            "DKK": "Danish Krone",
            "PLN": "Polish Zloty",
            "CZK": "Czech Koruna",
            "HUF": "Hungarian Forint"
        }
        
        return {
            code: currency_names.get(code, code)
            for code in self.supported_currencies
        }
    
    async def get_rate_history(
        self,
        from_currency: str,
        to_currency: str,
        days: int = 30,
        db: Optional[Session] = None
    ) -> List[Dict]:
        """Get historical exchange rates"""
        
        if not db:
            return []
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        rates = (
            db.query(CurrencyExchangeRate)
            .filter(
                CurrencyExchangeRate.from_currency == from_currency,
                CurrencyExchangeRate.to_currency == to_currency,
                CurrencyExchangeRate.created_at >= start_date
            )
            .order_by(CurrencyExchangeRate.created_at.desc())
            .all()
        )
        
        return [
            {
                "date": rate.created_at.isoformat(),
                "rate": float(rate.rate),
                "from_currency": rate.from_currency,
                "to_currency": rate.to_currency
            }
            for rate in rates
        ]
    
    async def update_all_rates(self, db: Session) -> int:
        """Update all currency rates (scheduled job)"""
        
        updated_count = 0
        base_currency = "USD"
        
        for currency in self.supported_currencies:
            if currency == base_currency:
                continue
            
            try:
                # Update both directions
                await self.get_exchange_rate(base_currency, currency, db)
                await self.get_exchange_rate(currency, base_currency, db)
                updated_count += 2
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to update rates for {currency}: {str(e)}")
        
        logger.info(f"Updated {updated_count} exchange rates")
        return updated_count
    
    async def calculate_conversion_fee(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str
    ) -> Decimal:
        """Calculate conversion fee for a transaction"""
        
        if from_currency == to_currency:
            return Decimal("0")
        
        # Get exchange rate
        rate = await self.get_exchange_rate(from_currency, to_currency)
        
        # Convert amount
        converted_amount = amount * rate
        
        # Calculate fee
        fee = converted_amount * self.exchange_fee_rate
        
        return fee.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)
    
    async def get_best_rate(
        self,
        from_currency: str,
        to_currency: str,
        amount: Decimal
    ) -> Dict:
        """Get best available rate with fee breakdown"""
        
        base_rate = await self.get_exchange_rate(from_currency, to_currency)
        converted_amount = amount * base_rate
        fee = await self.calculate_conversion_fee(amount, from_currency, to_currency)
        final_amount = converted_amount - fee
        
        return {
            "from_currency": from_currency,
            "to_currency": to_currency,
            "amount": float(amount),
            "exchange_rate": float(base_rate),
            "converted_amount": float(converted_amount),
            "conversion_fee": float(fee),
            "final_amount": float(final_amount),
            "fee_percentage": float(self.exchange_fee_rate * 100),
            "updated_at": datetime.utcnow().isoformat()
        }