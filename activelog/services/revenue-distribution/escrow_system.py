"""
Escrow System for Transactions
Secure escrow accounts for holding funds during transactions
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class EscrowStatus(str, Enum):
    CREATED = "created"
    FUNDED = "funded"
    RELEASED = "released"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

class EscrowManager:
    def __init__(self):
        self.escrow_accounts = {}
    
    async def create_escrow_account(self, escrow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new escrow account"""
        
        escrow_id = f"ESCROW_{uuid.uuid4().hex[:8].upper()}"
        
        escrow = {
            "id": escrow_id,
            "payer_id": escrow_data["payer_id"],
            "recipient_id": escrow_data["recipient_id"],
            "amount": Decimal(str(escrow_data["amount"])),
            "currency": escrow_data.get("currency", "USD"),
            "status": EscrowStatus.CREATED.value,
            "created_at": datetime.now().isoformat(),
            "conditions": escrow_data.get("conditions", []),
            "auto_release_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        self.escrow_accounts[escrow_id] = escrow
        
        logger.info(f"Created escrow account {escrow_id}")
        return escrow
    
    async def release_escrow_funds(self, escrow_id: str) -> Dict[str, Any]:
        """Release funds from escrow"""
        
        if escrow_id not in self.escrow_accounts:
            raise ValueError("Escrow account not found")
        
        escrow = self.escrow_accounts[escrow_id]
        escrow["status"] = EscrowStatus.RELEASED.value
        escrow["released_at"] = datetime.now().isoformat()
        
        logger.info(f"Released escrow funds {escrow_id}")
        return escrow

# Global instance
escrow_manager = EscrowManager()