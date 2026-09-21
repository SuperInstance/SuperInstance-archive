import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class MonitoringStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    UNDER_REVIEW = "under_review"

@dataclass
class TransactionMonitor:
    monitor_id: str
    customer_id: str
    account_id: str
    rule_name: str
    threshold: float
    time_window_hours: int
    current_amount: float
    transaction_count: int
    status: MonitoringStatus
    created_at: datetime
    last_triggered: Optional[datetime]

class TransactionMonitoringService:
    def __init__(self):
        self.monitors = {}
        self.transaction_cache = {}
        self.monitoring_active = False
        
    async def start_monitoring(self):
        """Start transaction monitoring"""
        self.monitoring_active = True
        asyncio.create_task(self._continuous_monitoring())
        logger.info("Transaction monitoring started")
    
    async def stop_monitoring(self):
        """Stop transaction monitoring"""
        self.monitoring_active = False
        logger.info("Transaction monitoring stopped")
    
    async def monitor_transaction(self, transaction_data: Dict) -> Dict:
        """Monitor a transaction against all rules"""
        try:
            customer_id = transaction_data.get('customer_id')
            account_id = transaction_data.get('account_id')
            amount = float(transaction_data.get('amount', 0))
            
            # Store transaction for pattern analysis
            await self._store_transaction(transaction_data)
            
            # Check BSA reporting thresholds
            bsa_alerts = await self._check_bsa_thresholds(transaction_data)
            
            # Check velocity limits
            velocity_alerts = await self._check_velocity_limits(transaction_data)
            
            # Check daily/monthly limits
            limit_alerts = await self._check_transaction_limits(transaction_data)
            
            all_alerts = bsa_alerts + velocity_alerts + limit_alerts
            
            return {
                'success': True,
                'alerts_triggered': len(all_alerts),
                'alerts': all_alerts,
                'monitoring_status': 'active'
            }
        
        except Exception as e:
            logger.error(f"Error in transaction monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _store_transaction(self, transaction_data: Dict):
        """Store transaction for monitoring"""
        customer_id = transaction_data.get('customer_id')
        
        if customer_id not in self.transaction_cache:
            self.transaction_cache[customer_id] = []
        
        self.transaction_cache[customer_id].append({
            'timestamp': datetime.now(),
            'amount': float(transaction_data.get('amount', 0)),
            'type': transaction_data.get('transaction_type', ''),
            'account_id': transaction_data.get('account_id', '')
        })
        
        # Keep only last 24 hours of transactions
        cutoff = datetime.now() - timedelta(hours=24)
        self.transaction_cache[customer_id] = [
            tx for tx in self.transaction_cache[customer_id]
            if tx['timestamp'] > cutoff
        ]
    
    async def _check_bsa_thresholds(self, transaction_data: Dict) -> List[Dict]:
        """Check Bank Secrecy Act reporting thresholds"""
        alerts = []
        amount = float(transaction_data.get('amount', 0))
        
        if amount >= settings.BSA_REPORTING_THRESHOLD:
            alerts.append({
                'alert_type': 'bsa_threshold',
                'description': f'Transaction amount ${amount:,.2f} exceeds BSA reporting threshold',
                'amount': amount,
                'threshold': settings.BSA_REPORTING_THRESHOLD,
                'action_required': 'file_ctr'
            })
        
        return alerts
    
    async def _check_velocity_limits(self, transaction_data: Dict) -> List[Dict]:
        """Check transaction velocity limits"""
        alerts = []
        customer_id = transaction_data.get('customer_id')
        current_amount = float(transaction_data.get('amount', 0))
        
        if customer_id in self.transaction_cache:
            # Check transactions in last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_transactions = [
                tx for tx in self.transaction_cache[customer_id]
                if tx['timestamp'] > one_hour_ago
            ]
            
            if len(recent_transactions) > 5:  # More than 5 transactions per hour
                alerts.append({
                    'alert_type': 'velocity_limit',
                    'description': f'{len(recent_transactions)} transactions in past hour',
                    'transaction_count': len(recent_transactions),
                    'threshold': 5,
                    'action_required': 'review_pattern'
                })
        
        return alerts
    
    async def _check_transaction_limits(self, transaction_data: Dict) -> List[Dict]:
        """Check daily and monthly transaction limits"""
        alerts = []
        customer_id = transaction_data.get('customer_id')
        amount = float(transaction_data.get('amount', 0))
        
        if customer_id in self.transaction_cache:
            # Check daily limits
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            daily_transactions = [
                tx for tx in self.transaction_cache[customer_id]
                if tx['timestamp'] > today
            ]
            
            daily_total = sum(tx['amount'] for tx in daily_transactions)
            
            if daily_total > settings.DAILY_WIRE_LIMIT:
                alerts.append({
                    'alert_type': 'daily_limit',
                    'description': f'Daily transaction total ${daily_total:,.2f} exceeds limit',
                    'daily_total': daily_total,
                    'limit': settings.DAILY_WIRE_LIMIT,
                    'action_required': 'limit_enforcement'
                })
        
        return alerts
    
    async def _continuous_monitoring(self):
        """Background monitoring task"""
        while self.monitoring_active:
            try:
                await self._cleanup_old_data()
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Error in continuous monitoring: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_old_data(self):
        """Clean up old transaction data"""
        cutoff = datetime.now() - timedelta(hours=24)
        
        for customer_id in list(self.transaction_cache.keys()):
            self.transaction_cache[customer_id] = [
                tx for tx in self.transaction_cache[customer_id]
                if tx['timestamp'] > cutoff
            ]
            
            if not self.transaction_cache[customer_id]:
                del self.transaction_cache[customer_id]