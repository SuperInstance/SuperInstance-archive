import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class CheckStatus(Enum):
    DEPOSITED = "deposited"
    IN_CLEARING = "in_clearing"
    CLEARED = "cleared"
    RETURNED = "returned"
    HOLD = "hold"

@dataclass
class CheckDeposit:
    check_id: str
    account_id: str
    amount: Decimal
    check_number: str
    routing_number: str
    account_number: str
    memo: str
    deposited_at: datetime
    status: CheckStatus
    hold_until: Optional[datetime]
    image_front: str
    image_back: str

class CheckProcessingService:
    def __init__(self):
        self.checks = {}
        
    async def deposit_check(self, deposit_data: Dict) -> Dict:
        """Process check deposit"""
        try:
            check_id = str(uuid.uuid4())
            amount = Decimal(str(deposit_data['amount']))
            
            # Apply hold period
            hold_until = datetime.now() + timedelta(days=settings.CHECK_HOLD_DAYS)
            
            check = CheckDeposit(
                check_id=check_id,
                account_id=deposit_data['account_id'],
                amount=amount,
                check_number=deposit_data.get('check_number', ''),
                routing_number=deposit_data.get('routing_number', ''),
                account_number=deposit_data.get('account_number', ''),
                memo=deposit_data.get('memo', ''),
                deposited_at=datetime.now(),
                status=CheckStatus.HOLD,
                hold_until=hold_until,
                image_front=deposit_data.get('image_front', ''),
                image_back=deposit_data.get('image_back', '')
            )
            
            self.checks[check_id] = check
            
            return {
                'success': True,
                'check_id': check_id,
                'status': check.status.value,
                'hold_until': hold_until.isoformat(),
                'amount': float(amount)
            }
        
        except Exception as e:
            logger.error(f"Error processing check deposit: {e}")
            return {'success': False, 'error': str(e)}