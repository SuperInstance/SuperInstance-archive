import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class CardType(Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    PREPAID = "prepaid"

class CardStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    EXPIRED = "expired"
    LOST_STOLEN = "lost_stolen"

@dataclass
class IssuedCard:
    card_id: str
    account_id: str
    card_number: str
    cvv: str
    expiry_date: datetime
    card_type: CardType
    status: CardStatus
    daily_limit: Decimal
    monthly_limit: Decimal
    issued_at: datetime
    last_used: Optional[datetime]

class CardIssuingService:
    def __init__(self):
        self.cards = {}
        
    async def issue_card(self, card_request: Dict) -> Dict:
        """Issue a new payment card"""
        try:
            card_id = str(uuid.uuid4())
            
            # Generate card number
            card_number = self._generate_card_number()
            cvv = self._generate_cvv()
            expiry_date = datetime.now() + timedelta(days=365 * settings.CARD_EXPIRY_YEARS)
            
            card = IssuedCard(
                card_id=card_id,
                account_id=card_request['account_id'],
                card_number=card_number,
                cvv=cvv,
                expiry_date=expiry_date,
                card_type=CardType(card_request.get('card_type', 'debit')),
                status=CardStatus.ACTIVE,
                daily_limit=Decimal(str(card_request.get('daily_limit', settings.DAILY_CARD_LIMIT))),
                monthly_limit=Decimal(str(card_request.get('monthly_limit', settings.DAILY_CARD_LIMIT * 30))),
                issued_at=datetime.now(),
                last_used=None
            )
            
            self.cards[card_id] = card
            
            return {
                'success': True,
                'card_id': card_id,
                'card_number': f"****-****-****-{card_number[-4:]}",
                'expiry_date': expiry_date.strftime('%m/%y'),
                'card_type': card.card_type.value,
                'status': card.status.value
            }
        
        except Exception as e:
            logger.error(f"Error issuing card: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_card_number(self) -> str:
        """Generate card number with BIN"""
        bin_range = settings.CARD_BIN_RANGE
        suffix = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        return bin_range + suffix
    
    def _generate_cvv(self) -> str:
        """Generate CVV"""
        return ''.join([str(random.randint(0, 9)) for _ in range(settings.CARD_CVV_LENGTH)])