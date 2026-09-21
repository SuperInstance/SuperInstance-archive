"""
CCC to USD Reporting System
Track and report cryptocurrency conversions for tax purposes
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime, date
from decimal import Decimal
import uuid
import logging
import json
import sqlite3

logger = logging.getLogger(__name__)

class CCCConversion(BaseModel):
    id: str
    entity_id: str
    
    # Conversion details
    ccc_amount: Decimal
    usd_amount: Decimal
    exchange_rate: Decimal
    conversion_date: date
    
    # Tax implications
    cost_basis: Decimal  # What we paid for the CCC
    capital_gain_loss: Decimal  # Gain or loss on conversion
    
    # Metadata
    transaction_id: Optional[str] = None
    conversion_method: str = "automatic"
    
    created_at: datetime

class CCCReporter:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
    
    async def generate_ccc_tax_report(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Generate CCC to USD tax report"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all CCC transactions for the year
        cursor.execute('''
            SELECT ccc_amount, amount, transaction_date
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND ccc_amount IS NOT NULL
            ORDER BY transaction_date
        ''', (entity_id, str(tax_year)))
        
        results = cursor.fetchall()
        conn.close()
        
        total_ccc_received = Decimal('0')
        total_usd_value = Decimal('0')
        transactions = []
        
        for result in results:
            ccc_amount = Decimal(str(result[0]))
            usd_amount = Decimal(str(result[1]))
            transaction_date = result[2]
            
            total_ccc_received += ccc_amount
            total_usd_value += usd_amount
            
            transactions.append({
                "date": transaction_date,
                "ccc_amount": float(ccc_amount),
                "usd_value": float(usd_amount),
                "exchange_rate": float(usd_amount / ccc_amount) if ccc_amount > 0 else 0
            })
        
        return {
            "entity_id": entity_id,
            "tax_year": tax_year,
            "summary": {
                "total_ccc_received": float(total_ccc_received),
                "total_usd_value": float(total_usd_value),
                "transaction_count": len(transactions),
                "average_exchange_rate": float(total_usd_value / total_ccc_received) if total_ccc_received > 0 else 0
            },
            "transactions": transactions,
            "generated_at": datetime.now().isoformat()
        }
    
    async def record_ccc_conversion(self, conversion_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record CCC to USD conversion"""
        
        conversion_id = f"CCC_{uuid.uuid4().hex[:8].upper()}"
        
        ccc_amount = Decimal(str(conversion_data["ccc_amount"]))
        usd_amount = Decimal(str(conversion_data["usd_amount"]))
        exchange_rate = usd_amount / ccc_amount if ccc_amount > 0 else Decimal('0')
        
        # Calculate capital gain/loss (simplified)
        cost_basis = Decimal(str(conversion_data.get("cost_basis", usd_amount)))
        capital_gain_loss = usd_amount - cost_basis
        
        conversion = CCCConversion(
            id=conversion_id,
            entity_id=conversion_data["entity_id"],
            ccc_amount=ccc_amount,
            usd_amount=usd_amount,
            exchange_rate=exchange_rate,
            conversion_date=datetime.strptime(conversion_data["conversion_date"], "%Y-%m-%d").date(),
            cost_basis=cost_basis,
            capital_gain_loss=capital_gain_loss,
            transaction_id=conversion_data.get("transaction_id"),
            conversion_method=conversion_data.get("conversion_method", "automatic"),
            created_at=datetime.now()
        )
        
        return {
            "conversion_id": conversion_id,
            "ccc_amount": float(ccc_amount),
            "usd_amount": float(usd_amount),
            "exchange_rate": float(exchange_rate),
            "capital_gain_loss": float(capital_gain_loss),
            "recorded_at": datetime.now().isoformat()
        }

# Global instance
ccc_reporter = CCCReporter()