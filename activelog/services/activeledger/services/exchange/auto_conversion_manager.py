"""
Automatic Currency Conversion Manager for International Users
Handles smart CC conversion, preferred currencies, and localized pricing
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.database import (
    User, AutoConversionRule, CurrencyConversionTransaction, Transaction,
    TransactionType, TransactionStatus
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem
from .currency_converter import CurrencyConverter

logger = logging.getLogger(__name__)

class AutoConversionManager:
    """Manages automatic currency conversion for international users"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        self.currency_converter = CurrencyConverter()
        
        # Conversion thresholds
        self.min_conversion_amount_usd = Decimal("1.00")  # Minimum $1 USD equivalent
        self.max_daily_conversion_usd = Decimal("10000.00")  # Maximum $10,000 USD per day
        self.conversion_buffer_percentage = Decimal("0.05")  # 5% buffer for rate fluctuations
        
        # Auto-conversion triggers
        self.low_balance_threshold_percentage = Decimal("0.20")  # Convert when CC < 20% of preferred balance
        self.preferred_balance_days = 7  # Maintain balance for 7 days of average usage
    
    async def setup_auto_conversion(
        self,
        user_id: str,
        preferred_currency: str,
        auto_convert_enabled: bool = True,
        preferred_balance_cc: Optional[Decimal] = None,
        max_daily_conversion_amount: Optional[Decimal] = None,
        conversion_threshold_percentage: Optional[Decimal] = None
    ) -> AutoConversionRule:
        """Set up automatic conversion rules for a user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate currency
        supported_currencies = await self.currency_converter.get_supported_currencies()
        if preferred_currency not in supported_currencies:
            raise ValueError(f"Unsupported currency: {preferred_currency}")
        
        # Get or create auto conversion rule
        rule = (
            self.db.query(AutoConversionRule)
            .filter(AutoConversionRule.user_id == user_id)
            .first()
        )
        
        if not rule:
            rule = AutoConversionRule(user_id=user_id)
            self.db.add(rule)
        
        # Update rule settings
        rule.preferred_currency = preferred_currency
        rule.auto_convert_enabled = auto_convert_enabled
        rule.preferred_balance_cc = preferred_balance_cc or await self._calculate_preferred_balance(user_id)
        rule.max_daily_conversion_amount = max_daily_conversion_amount or self.max_daily_conversion_usd
        rule.conversion_threshold_percentage = conversion_threshold_percentage or self.low_balance_threshold_percentage
        rule.updated_at = datetime.utcnow()
        
        # Update user's preferred currency
        user.preferred_currency = preferred_currency
        
        self.db.commit()
        
        logger.info(f"Set up auto conversion for user {user_id}: {preferred_currency}, enabled: {auto_convert_enabled}")
        return rule
    
    async def _calculate_preferred_balance(self, user_id: str) -> Decimal:
        """Calculate preferred CC balance based on user's usage patterns"""
        
        # Get user's average daily usage over last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_transactions = (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type.in_([TransactionType.DEBIT, TransactionType.PAYMENT]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .all()
        )
        
        if not recent_transactions:
            # Default preferred balance for new users
            return Decimal("1000")  # $10 USD equivalent
        
        # Calculate average daily spending
        total_spent = sum(abs(tx.amount_cc) for tx in recent_transactions)
        days_of_data = min(30, (datetime.utcnow() - recent_transactions[-1].created_at).days + 1)
        average_daily_spend = total_spent / days_of_data
        
        # Preferred balance = average daily spend * buffer days
        preferred_balance = average_daily_spend * self.preferred_balance_days
        
        # Ensure minimum balance
        return max(preferred_balance, Decimal("500"))  # Minimum $5 USD equivalent
    
    async def check_and_convert(self, user_id: str) -> Optional[CurrencyConversionTransaction]:
        """Check if user needs automatic conversion and execute if needed"""
        
        rule = (
            self.db.query(AutoConversionRule)
            .filter(AutoConversionRule.user_id == user_id)
            .first()
        )
        
        if not rule or not rule.auto_convert_enabled:
            return None
        
        # Get current CC balance
        current_balance = await self.cc_system.get_user_balance(user_id)
        
        # Check if balance is below threshold
        threshold_balance = rule.preferred_balance_cc * rule.conversion_threshold_percentage
        
        if current_balance > threshold_balance:
            return None
        
        # Calculate conversion amount needed
        conversion_needed_cc = rule.preferred_balance_cc - current_balance
        
        # Add buffer for rate fluctuations
        conversion_amount_cc = conversion_needed_cc * (Decimal("1") + self.conversion_buffer_percentage)
        
        # Check daily conversion limits
        if not await self._check_daily_limits(user_id, conversion_amount_cc, rule):
            logger.warning(f"Daily conversion limit reached for user {user_id}")
            return None
        
        # Perform conversion
        return await self._execute_auto_conversion(user_id, conversion_amount_cc, rule)
    
    async def _check_daily_limits(
        self,
        user_id: str,
        conversion_amount_cc: Decimal,
        rule: AutoConversionRule
    ) -> bool:
        """Check if conversion is within daily limits"""
        
        # Get today's conversions
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        today_conversions = (
            self.db.query(
                func.sum(CurrencyConversionTransaction.source_amount)
            )
            .filter(
                and_(
                    CurrencyConversionTransaction.user_id == user_id,
                    CurrencyConversionTransaction.created_at >= today_start,
                    CurrencyConversionTransaction.status == TransactionStatus.COMPLETED
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Convert CC to USD for limit checking
        conversion_amount_usd = conversion_amount_cc * settings.compute_credits.cc_to_usd_rate
        
        # Check limits
        if conversion_amount_usd < self.min_conversion_amount_usd:
            return False
        
        if today_conversions + conversion_amount_usd > rule.max_daily_conversion_amount:
            return False
        
        return True
    
    async def _execute_auto_conversion(
        self,
        user_id: str,
        conversion_amount_cc: Decimal,
        rule: AutoConversionRule
    ) -> CurrencyConversionTransaction:
        """Execute automatic currency conversion"""
        
        # Convert CC amount to source currency
        conversion_amount_usd = conversion_amount_cc * settings.compute_credits.cc_to_usd_rate
        
        source_amount = await self.currency_converter.convert(
            conversion_amount_usd,
            "USD",
            rule.preferred_currency,
            include_fee=False,
            db=self.db
        )
        
        # Create conversion transaction record
        conversion_tx = CurrencyConversionTransaction(
            user_id=user_id,
            source_currency=rule.preferred_currency,
            source_amount=source_amount,
            target_currency="CC",
            target_amount=conversion_amount_cc,
            exchange_rate=await self.currency_converter.get_exchange_rate(
                rule.preferred_currency, "USD", self.db
            ),
            conversion_fee=await self.currency_converter.calculate_conversion_fee(
                source_amount, rule.preferred_currency, "USD"
            ),
            status=TransactionStatus.PENDING,
            is_automatic=True,
            triggered_by="low_balance"
        )
        
        try:
            # In a real implementation, this would:
            # 1. Charge the user's payment method in their preferred currency
            # 2. Handle payment processing
            # 3. Add CC credits on successful payment
            
            # For this implementation, we'll simulate successful payment
            # In production, integrate with payment gateways here
            
            # Add CC credits to user account
            await self.cc_system.add_credits(
                user_id,
                conversion_amount_cc,
                TransactionType.CURRENCY_CONVERSION,
                f"Auto-conversion: {source_amount} {rule.preferred_currency} → {conversion_amount_cc} CC",
                metadata={
                    "conversion_id": str(conversion_tx.id),
                    "source_currency": rule.preferred_currency,
                    "source_amount": str(source_amount),
                    "exchange_rate": str(conversion_tx.exchange_rate),
                    "conversion_fee": str(conversion_tx.conversion_fee),
                    "trigger": "automatic_low_balance"
                }
            )
            
            # Update conversion transaction
            conversion_tx.status = TransactionStatus.COMPLETED
            conversion_tx.completed_at = datetime.utcnow()
            
            self.db.add(conversion_tx)
            self.db.commit()
            
            logger.info(
                f"Auto-converted for user {user_id}: {source_amount} {rule.preferred_currency} "
                f"→ {conversion_amount_cc} CC"
            )
            
            return conversion_tx
            
        except Exception as e:
            # Mark conversion as failed
            conversion_tx.status = TransactionStatus.FAILED
            conversion_tx.error_message = str(e)
            
            self.db.add(conversion_tx)
            self.db.commit()
            
            logger.error(f"Auto-conversion failed for user {user_id}: {str(e)}")
            raise
    
    async def manual_conversion(
        self,
        user_id: str,
        source_amount: Decimal,
        source_currency: str,
        target_currency: str = "CC"
    ) -> CurrencyConversionTransaction:
        """Perform manual currency conversion"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Validate currencies
        supported_currencies = await self.currency_converter.get_supported_currencies()
        if source_currency not in supported_currencies and source_currency != "CC":
            raise ValueError(f"Unsupported source currency: {source_currency}")
        
        if target_currency not in supported_currencies and target_currency != "CC":
            raise ValueError(f"Unsupported target currency: {target_currency}")
        
        # Calculate conversion
        if source_currency == "CC" and target_currency != "CC":
            # CC to fiat currency
            target_amount = await self.cc_system.convert_from_cc(source_amount, target_currency, user_id)
            exchange_rate = await self.currency_converter.get_exchange_rate("USD", target_currency, self.db)
        elif source_currency != "CC" and target_currency == "CC":
            # Fiat currency to CC
            target_amount = await self.cc_system.convert_to_cc(source_amount, source_currency, user_id)
            exchange_rate = await self.currency_converter.get_exchange_rate(source_currency, "USD", self.db)
        else:
            # Fiat to fiat
            target_amount = await self.currency_converter.convert(
                source_amount, source_currency, target_currency, include_fee=True, db=self.db
            )
            exchange_rate = await self.currency_converter.get_exchange_rate(
                source_currency, target_currency, self.db
            )
        
        # Calculate conversion fee
        conversion_fee = await self.currency_converter.calculate_conversion_fee(
            source_amount, source_currency, target_currency
        )
        
        # Create conversion transaction
        conversion_tx = CurrencyConversionTransaction(
            user_id=user_id,
            source_currency=source_currency,
            source_amount=source_amount,
            target_currency=target_currency,
            target_amount=target_amount,
            exchange_rate=exchange_rate,
            conversion_fee=conversion_fee,
            status=TransactionStatus.COMPLETED,
            is_automatic=False,
            triggered_by="manual"
        )
        
        # Process the actual conversion
        if source_currency == "CC":
            # Deduct CC credits
            await self.cc_system.deduct_credits(
                user_id,
                source_amount,
                TransactionType.CURRENCY_CONVERSION,
                f"Manual conversion: {source_amount} CC → {target_amount} {target_currency}",
                metadata={
                    "conversion_id": str(conversion_tx.id),
                    "target_currency": target_currency,
                    "target_amount": str(target_amount)
                }
            )
        elif target_currency == "CC":
            # Add CC credits
            await self.cc_system.add_credits(
                user_id,
                target_amount,
                TransactionType.CURRENCY_CONVERSION,
                f"Manual conversion: {source_amount} {source_currency} → {target_amount} CC",
                metadata={
                    "conversion_id": str(conversion_tx.id),
                    "source_currency": source_currency,
                    "source_amount": str(source_amount)
                }
            )
        
        conversion_tx.completed_at = datetime.utcnow()
        
        self.db.add(conversion_tx)
        self.db.commit()
        
        logger.info(
            f"Manual conversion for user {user_id}: {source_amount} {source_currency} "
            f"→ {target_amount} {target_currency}"
        )
        
        return conversion_tx
    
    async def get_conversion_preview(
        self,
        source_amount: Decimal,
        source_currency: str,
        target_currency: str
    ) -> Dict:
        """Get preview of conversion without executing it"""
        
        # Get current exchange rate
        if source_currency == "CC":
            exchange_rate = Decimal("1") / settings.compute_credits.cc_to_usd_rate
            if target_currency != "USD":
                usd_to_target = await self.currency_converter.get_exchange_rate("USD", target_currency, self.db)
                exchange_rate *= usd_to_target
        elif target_currency == "CC":
            exchange_rate = settings.compute_credits.cc_to_usd_rate
            if source_currency != "USD":
                source_to_usd = await self.currency_converter.get_exchange_rate(source_currency, "USD", self.db)
                exchange_rate /= source_to_usd
        else:
            exchange_rate = await self.currency_converter.get_exchange_rate(
                source_currency, target_currency, self.db
            )
        
        # Calculate amounts
        gross_target_amount = source_amount * exchange_rate
        conversion_fee = await self.currency_converter.calculate_conversion_fee(
            source_amount, source_currency, target_currency
        )
        net_target_amount = gross_target_amount - conversion_fee
        
        return {
            "source_currency": source_currency,
            "target_currency": target_currency,
            "source_amount": float(source_amount),
            "exchange_rate": float(exchange_rate),
            "gross_target_amount": float(gross_target_amount),
            "conversion_fee": float(conversion_fee),
            "net_target_amount": float(net_target_amount),
            "fee_percentage": float(self.currency_converter.exchange_fee_rate * 100),
            "estimated_at": datetime.utcnow().isoformat()
        }
    
    async def get_user_conversion_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """Get user's currency conversion history"""
        
        conversions = (
            self.db.query(CurrencyConversionTransaction)
            .filter(CurrencyConversionTransaction.user_id == user_id)
            .order_by(desc(CurrencyConversionTransaction.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        return [
            {
                "conversion_id": conversion.id,
                "source_currency": conversion.source_currency,
                "source_amount": float(conversion.source_amount),
                "target_currency": conversion.target_currency,
                "target_amount": float(conversion.target_amount),
                "exchange_rate": float(conversion.exchange_rate),
                "conversion_fee": float(conversion.conversion_fee),
                "status": conversion.status.value,
                "is_automatic": conversion.is_automatic,
                "triggered_by": conversion.triggered_by,
                "created_at": conversion.created_at.isoformat(),
                "completed_at": conversion.completed_at.isoformat() if conversion.completed_at else None,
                "error_message": conversion.error_message
            }
            for conversion in conversions
        ]
    
    async def get_localized_pricing(
        self,
        user_id: str,
        base_price_cc: Decimal
    ) -> Dict:
        """Get pricing in user's preferred currency with localization"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        preferred_currency = user.preferred_currency or "USD"
        
        # Convert CC to preferred currency
        price_in_preferred = await self.cc_system.convert_from_cc(
            base_price_cc, preferred_currency, user_id
        )
        
        # Get current exchange rate for transparency
        exchange_rate = await self.currency_converter.get_exchange_rate(
            "USD", preferred_currency, self.db
        )
        
        # Get currency formatting info
        currency_info = await self._get_currency_formatting(preferred_currency)
        
        return {
            "base_price_cc": float(base_price_cc),
            "base_price_usd": float(base_price_cc * settings.compute_credits.cc_to_usd_rate),
            "localized_price": float(price_in_preferred),
            "currency": preferred_currency,
            "exchange_rate": float(exchange_rate),
            "formatting": currency_info,
            "formatted_price": self._format_currency_amount(price_in_preferred, currency_info),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    def _get_currency_formatting(self, currency_code: str) -> Dict:
        """Get currency formatting information"""
        
        formatting_rules = {
            "USD": {"symbol": "$", "decimal_places": 2, "symbol_before": True},
            "EUR": {"symbol": "€", "decimal_places": 2, "symbol_before": False},
            "GBP": {"symbol": "£", "decimal_places": 2, "symbol_before": True},
            "JPY": {"symbol": "¥", "decimal_places": 0, "symbol_before": True},
            "CNY": {"symbol": "¥", "decimal_places": 2, "symbol_before": True},
            "INR": {"symbol": "₹", "decimal_places": 2, "symbol_before": True},
            "BRL": {"symbol": "R$", "decimal_places": 2, "symbol_before": True},
            "CAD": {"symbol": "C$", "decimal_places": 2, "symbol_before": True},
            "AUD": {"symbol": "A$", "decimal_places": 2, "symbol_before": True},
            "CHF": {"symbol": "CHF", "decimal_places": 2, "symbol_before": False},
        }
        
        return formatting_rules.get(currency_code, {
            "symbol": currency_code,
            "decimal_places": 2,
            "symbol_before": True
        })
    
    def _format_currency_amount(self, amount: Decimal, formatting: Dict) -> str:
        """Format currency amount according to locale rules"""
        
        # Round to appropriate decimal places
        decimal_places = formatting.get("decimal_places", 2)
        if decimal_places == 0:
            formatted_amount = str(int(amount.quantize(Decimal("1"))))
        else:
            quantizer = Decimal("0." + "0" * decimal_places)
            formatted_amount = str(amount.quantize(quantizer, rounding=ROUND_HALF_UP))
        
        # Add thousand separators
        parts = formatted_amount.split(".")
        parts[0] = "{:,}".format(int(parts[0]))
        formatted_amount = ".".join(parts)
        
        # Add currency symbol
        symbol = formatting.get("symbol", "")
        symbol_before = formatting.get("symbol_before", True)
        
        if symbol_before:
            return f"{symbol}{formatted_amount}"
        else:
            return f"{formatted_amount} {symbol}"
    
    async def process_scheduled_conversions(self) -> Dict[str, int]:
        """Process automatic conversions for all eligible users (scheduled job)"""
        
        # Find users with auto-conversion enabled
        auto_conversion_users = (
            self.db.query(AutoConversionRule)
            .filter(AutoConversionRule.auto_convert_enabled == True)
            .all()
        )
        
        results = {"checked": 0, "converted": 0, "failed": 0}
        
        for rule in auto_conversion_users:
            try:
                results["checked"] += 1
                
                conversion = await self.check_and_convert(rule.user_id)
                if conversion:
                    results["converted"] += 1
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to process auto-conversion for user {rule.user_id}: {str(e)}")
                results["failed"] += 1
        
        logger.info(f"Processed scheduled conversions: {results}")
        return results