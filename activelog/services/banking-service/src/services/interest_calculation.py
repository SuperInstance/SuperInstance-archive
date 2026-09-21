import asyncio
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List
from dataclasses import dataclass
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

@dataclass
class InterestCalculation:
    account_id: str
    balance: Decimal
    interest_rate: Decimal
    daily_interest: Decimal
    calculation_date: datetime
    compounding_frequency: str

class InterestCalculationService:
    def __init__(self):
        self.calculation_active = False
        self.interest_history = {}
        
    async def start_daily_calculation(self):
        """Start daily interest calculation"""
        self.calculation_active = True
        asyncio.create_task(self._daily_calculation_loop())
        logger.info("Daily interest calculation started")
    
    async def stop_calculation(self):
        """Stop interest calculation"""
        self.calculation_active = False
        logger.info("Interest calculation stopped")
    
    async def calculate_daily_interest(self, account_data: Dict) -> Dict:
        """Calculate daily interest for an account"""
        try:
            account_id = account_data['account_id']
            balance = Decimal(str(account_data['balance']))
            annual_rate = Decimal(str(account_data['interest_rate']))
            account_type = account_data['account_type']
            
            # Daily interest rate
            daily_rate = annual_rate / Decimal('365')
            
            # Calculate daily interest
            daily_interest = (balance * daily_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Store calculation
            calculation = InterestCalculation(
                account_id=account_id,
                balance=balance,
                interest_rate=annual_rate,
                daily_interest=daily_interest,
                calculation_date=datetime.now(),
                compounding_frequency='daily'
            )
            
            if account_id not in self.interest_history:
                self.interest_history[account_id] = []
            
            self.interest_history[account_id].append(calculation)
            
            return {
                'success': True,
                'account_id': account_id,
                'daily_interest': float(daily_interest),
                'annual_rate': float(annual_rate),
                'balance': float(balance)
            }
        
        except Exception as e:
            logger.error(f"Error calculating interest: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _daily_calculation_loop(self):
        """Daily interest calculation loop"""
        while self.calculation_active:
            try:
                # Wait until next calculation time (daily at midnight)
                now = datetime.now()
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                sleep_seconds = (tomorrow - now).total_seconds()
                
                await asyncio.sleep(sleep_seconds)
                
                # Perform daily calculations for all eligible accounts
                await self._perform_daily_calculations()
                
            except Exception as e:
                logger.error(f"Error in daily calculation loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def _perform_daily_calculations(self):
        """Perform daily interest calculations for all accounts"""
        logger.info("Starting daily interest calculations")
        # This would integrate with the virtual accounts service
        # to get all eligible accounts and calculate interest