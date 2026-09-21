"""
Dispute Resolution System
Handle transaction disputes and resolution process
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"

class DisputeResolver:
    def __init__(self):
        self.disputes = {}
    
    async def create_dispute(self, dispute_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dispute"""
        
        dispute_id = f"DISPUTE_{uuid.uuid4().hex[:8].upper()}"
        
        dispute = {
            "id": dispute_id,
            "transaction_id": dispute_data["transaction_id"],
            "complainant_id": dispute_data["complainant_id"],
            "respondent_id": dispute_data["respondent_id"],
            "dispute_reason": dispute_data["reason"],
            "description": dispute_data["description"],
            "status": DisputeStatus.OPEN.value,
            "created_at": datetime.now().isoformat(),
            "evidence": dispute_data.get("evidence", []),
            "resolution": None
        }
        
        self.disputes[dispute_id] = dispute
        
        logger.info(f"Created dispute {dispute_id}")
        return dispute
    
    async def get_dispute(self, dispute_id: str) -> Optional[Dict[str, Any]]:
        """Get dispute by ID"""
        
        return self.disputes.get(dispute_id)

# Global instance
dispute_resolver = DisputeResolver()