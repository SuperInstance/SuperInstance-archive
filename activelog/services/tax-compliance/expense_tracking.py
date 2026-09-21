"""
Business Expense Tracking System
Track and categorize business expenses for tax deductions
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import logging
import json
import sqlite3

logger = logging.getLogger(__name__)

class ExpenseTracker:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db"
    
    async def get_business_expenses(self, entity_id: str, year: int, 
                                  category: str = None) -> Dict[str, Any]:
        """Get business expenses for entity"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT expense_category, SUM(amount), COUNT(*)
            FROM tax_transactions
            WHERE entity_id = ?
            AND strftime('%Y', transaction_date) = ?
            AND transaction_type = 'expense'
            AND deductible = TRUE
        '''
        params = [entity_id, str(year)]
        
        if category:
            query += " AND expense_category = ?"
            params.append(category)
        
        query += " GROUP BY expense_category"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        expenses_by_category = {}
        total_expenses = Decimal('0')
        
        for result in results:
            category_name = result[0] if result[0] else "uncategorized"
            amount = Decimal(str(result[1]))
            count = result[2]
            
            expenses_by_category[category_name] = {
                "amount": float(amount),
                "transaction_count": count
            }
            total_expenses += amount
        
        return {
            "entity_id": entity_id,
            "year": year,
            "total_expenses": float(total_expenses),
            "expenses_by_category": expenses_by_category,
            "category_count": len(expenses_by_category)
        }
    
    async def get_expense_summary(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Get expense summary by category"""
        
        return await self.get_business_expenses(entity_id, tax_year)

# Global instance
expense_tracker = ExpenseTracker()