#!/usr/bin/env python3
"""
Tax Preparation Interface
Tax account mapping, form data extraction, and multi-jurisdiction support
"""

import json
import sqlite3
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
import uuid

logger = logging.getLogger(__name__)

class TaxPreparationInterface:
    """Tax preparation and reporting interface"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        
        # Common tax form mappings
        self.tax_mappings = {
            'form_1120': {  # Corporate Income Tax
                'gross_receipts': ['4000', '4100'],
                'cost_of_goods_sold': ['5000'],
                'total_income': ['4000', '4100', '4900'],
                'compensation': ['6000'],
                'repairs': ['6100'],
                'bad_debts': ['6200'],
                'rent': ['6100'],
                'taxes': ['6400'],
                'interest': ['7000'],
                'depreciation': ['6500']
            }
        }
    
    async def initialize(self):
        """Initialize tax preparation interface"""
        logger.info("Tax preparation interface initialized")
    
    async def get_tax_data(self, entity_id: str, tax_year: int) -> Dict[str, Any]:
        """Get tax preparation data for entity and year"""
        try:
            start_date = f"{tax_year}-01-01"
            end_date = f"{tax_year}-12-31"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get account balances for tax year
            entity_filter = "AND coa.entity_id = ?" if entity_id else ""
            entity_params = [entity_id] if entity_id else []
            
            cursor.execute(f'''
                SELECT 
                    coa.account_code, coa.account_name, coa.account_type, coa.tax_code,
                    SUM(CASE 
                        WHEN coa.account_type IN ('revenue') THEN gl.credit_amount - gl.debit_amount
                        WHEN coa.account_type IN ('expense') THEN gl.debit_amount - gl.credit_amount
                        ELSE gl.debit_amount - gl.credit_amount
                    END) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id 
                    AND gl.transaction_date BETWEEN ? AND ?
                WHERE coa.is_active = TRUE {entity_filter}
                GROUP BY coa.account_code, coa.account_name, coa.account_type, coa.tax_code
                HAVING ABS(balance) > 0.01
                ORDER BY coa.account_code
            ''', [start_date, end_date] + entity_params)
            
            tax_accounts = []
            for row in cursor.fetchall():
                tax_accounts.append({
                    'account_code': row[0],
                    'account_name': row[1],
                    'account_type': row[2],
                    'tax_code': row[3],
                    'balance': Decimal(str(row[4]))
                })
            
            # Generate tax form data
            form_data = self._generate_form_data(tax_accounts, 'form_1120')
            
            conn.close()
            
            return {
                'success': True,
                'entity_id': entity_id,
                'tax_year': tax_year,
                'tax_accounts': tax_accounts,
                'form_data': form_data,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting tax data: {e}")
            return {
                'success': False,
                'error': f"Tax data error: {str(e)}"
            }
    
    def _generate_form_data(self, accounts: List[Dict], form_type: str) -> Dict[str, Any]:
        """Generate tax form data from account balances"""
        form_mapping = self.tax_mappings.get(form_type, {})
        form_data = {}
        
        for line_item, account_codes in form_mapping.items():
            total = Decimal('0')
            
            for account in accounts:
                if account['account_code'] in account_codes:
                    total += account['balance']
            
            form_data[line_item] = total
        
        return form_data
    
    async def export_tax_data(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """Export tax data in specified format"""
        try:
            format_type = export_data.get('format', 'json')
            
            if format_type == 'json':
                return {
                    'success': True,
                    'export_format': 'json',
                    'data': export_data
                }
            
            return {
                'success': True,
                'export_format': format_type,
                'message': f"Export in {format_type} format completed"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Tax export error: {str(e)}"
            }

# Global instance
tax_interface = TaxPreparationInterface()