"""
Automated Invoicing System
Generate and manage invoices automatically
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class InvoiceGenerator:
    def __init__(self):
        self.invoices = {}
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invoice"""
        
        invoice_id = f"INV_{uuid.uuid4().hex[:8].upper()}"
        
        invoice = {
            "id": invoice_id,
            "recipient_id": invoice_data["recipient_id"],
            "amount": invoice_data["amount"],
            "currency": invoice_data.get("currency", "USD"),
            "description": invoice_data["description"],
            "status": InvoiceStatus.DRAFT.value,
            "created_at": datetime.now().isoformat(),
            "due_date": invoice_data.get("due_date"),
            "line_items": invoice_data.get("line_items", [])
        }
        
        self.invoices[invoice_id] = invoice
        
        logger.info(f"Created invoice {invoice_id}")
        return invoice
    
    async def get_user_invoices(self, user_id: str, status: str = None) -> List[Dict[str, Any]]:
        """Get invoices for a user"""
        
        user_invoices = [
            inv for inv in self.invoices.values() 
            if inv["recipient_id"] == user_id
        ]
        
        if status:
            user_invoices = [inv for inv in user_invoices if inv["status"] == status]
        
        return user_invoices

# Global instance
invoice_generator = InvoiceGenerator()