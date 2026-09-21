#!/usr/bin/env python3
"""
Budget vs Actual Reporting System
Budget creation, variance analysis, and forecasting
"""

import json
import sqlite3
import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
import uuid

logger = logging.getLogger(__name__)

class BudgetReportingSystem:
    """Comprehensive budget vs actual reporting system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
    
    async def initialize(self):
        """Initialize budget reporting system"""
        logger.info("Budget reporting system initialized")
    
    async def create_budget(self, budget_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create budget entry"""
        try:
            budget_id = f"BUD_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO budgets (
                    id, budget_name, account_id, period_id, budgeted_amount,
                    currency, created_at, updated_at, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                budget_id, budget_data['budget_name'], budget_data['account_id'],
                budget_data['period_id'], float(Decimal(str(budget_data['budgeted_amount']))),
                budget_data.get('currency', 'USD'), datetime.now().isoformat(),
                datetime.now().isoformat(), json.dumps(budget_data)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'budget_id': budget_id,
                'budget_name': budget_data['budget_name'],
                'budgeted_amount': Decimal(str(budget_data['budgeted_amount']))
            }
            
        except Exception as e:
            logger.error(f"Error creating budget: {e}")
            return {
                'success': False,
                'error': f"Budget creation error: {str(e)}"
            }
    
    async def generate_budget_vs_actual_report(
        self, 
        period_id: str, 
        account_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate budget vs actual report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get period information
            cursor.execute('''
                SELECT period_name, start_date, end_date
                FROM financial_periods WHERE id = ?
            ''', (period_id,))
            
            period_row = cursor.fetchone()
            if not period_row:
                return {'success': False, 'error': 'Period not found'}
            
            period_name, start_date, end_date = period_row
            
            # Build account type filter
            account_filter = "AND coa.account_type = ?" if account_type else ""
            account_params = [account_type] if account_type else []
            
            # Get budget vs actual data
            cursor.execute(f'''
                SELECT 
                    b.account_id, coa.account_code, coa.account_name, coa.account_type,
                    b.budgeted_amount,
                    COALESCE(actual.actual_amount, 0) as actual_amount
                FROM budgets b
                JOIN chart_of_accounts coa ON b.account_id = coa.id
                LEFT JOIN (
                    SELECT 
                        gl.account_id,
                        SUM(CASE 
                            WHEN coa.account_type IN ('revenue') THEN gl.credit_amount - gl.debit_amount
                            WHEN coa.account_type IN ('expense') THEN gl.debit_amount - gl.credit_amount
                            ELSE gl.debit_amount - gl.credit_amount
                        END) as actual_amount
                    FROM general_ledger gl
                    JOIN chart_of_accounts coa ON gl.account_id = coa.id
                    WHERE gl.transaction_date BETWEEN ? AND ?
                    GROUP BY gl.account_id
                ) actual ON b.account_id = actual.account_id
                WHERE b.period_id = ? {account_filter}
                ORDER BY coa.account_code
            ''', [start_date, end_date, period_id] + account_params)
            
            budget_items = []
            total_budgeted = Decimal('0')
            total_actual = Decimal('0')
            total_variance = Decimal('0')
            
            for row in cursor.fetchall():
                account_id, account_code, account_name, account_type_val = row[:4]
                budgeted_amount = Decimal(str(row[4]))
                actual_amount = Decimal(str(row[5]))
                
                variance_amount = actual_amount - budgeted_amount
                variance_percentage = (variance_amount / budgeted_amount * 100) if budgeted_amount != 0 else Decimal('0')
                
                budget_items.append({
                    'account_id': account_id,
                    'account_code': account_code,
                    'account_name': account_name,
                    'account_type': account_type_val,
                    'budgeted_amount': budgeted_amount,
                    'actual_amount': actual_amount,
                    'variance_amount': variance_amount,
                    'variance_percentage': variance_percentage,
                    'favorable_variance': variance_amount > 0 if account_type_val == 'revenue' else variance_amount < 0
                })
                
                total_budgeted += budgeted_amount
                total_actual += actual_amount
                total_variance += variance_amount
            
            # Calculate summary by account type
            type_summary = {}
            for item in budget_items:
                acc_type = item['account_type']
                if acc_type not in type_summary:
                    type_summary[acc_type] = {
                        'budgeted': Decimal('0'),
                        'actual': Decimal('0'),
                        'variance': Decimal('0'),
                        'count': 0
                    }
                
                type_summary[acc_type]['budgeted'] += item['budgeted_amount']
                type_summary[acc_type]['actual'] += item['actual_amount']
                type_summary[acc_type]['variance'] += item['variance_amount']
                type_summary[acc_type]['count'] += 1
            
            conn.close()
            
            return {
                'success': True,
                'period': {
                    'id': period_id,
                    'name': period_name,
                    'start_date': start_date,
                    'end_date': end_date
                },
                'budget_items': budget_items,
                'totals': {
                    'total_budgeted': total_budgeted,
                    'total_actual': total_actual,
                    'total_variance': total_variance,
                    'overall_variance_percentage': (total_variance / total_budgeted * 100) if total_budgeted != 0 else Decimal('0')
                },
                'type_summary': type_summary,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating budget vs actual report: {e}")
            return {
                'success': False,
                'error': f"Budget vs actual error: {str(e)}"
            }
    
    async def generate_variance_analysis(
        self, 
        period_id: str, 
        threshold: float = 0.1
    ) -> Dict[str, Any]:
        """Generate variance analysis for significant variances"""
        try:
            # Get budget vs actual report first
            report_result = await self.generate_budget_vs_actual_report(period_id)
            if not report_result['success']:
                return report_result
            
            budget_items = report_result['budget_items']
            threshold_decimal = Decimal(str(threshold))
            
            # Identify significant variances
            significant_variances = []
            favorable_variances = []
            unfavorable_variances = []
            
            for item in budget_items:
                variance_pct = abs(item['variance_percentage'])
                
                if variance_pct >= (threshold_decimal * 100):  # Convert to percentage
                    variance_info = {
                        'account_code': item['account_code'],
                        'account_name': item['account_name'],
                        'account_type': item['account_type'],
                        'budgeted_amount': item['budgeted_amount'],
                        'actual_amount': item['actual_amount'],
                        'variance_amount': item['variance_amount'],
                        'variance_percentage': item['variance_percentage'],
                        'is_favorable': item['favorable_variance']
                    }
                    
                    significant_variances.append(variance_info)
                    
                    if item['favorable_variance']:
                        favorable_variances.append(variance_info)
                    else:
                        unfavorable_variances.append(variance_info)
            
            # Sort by variance percentage (largest first)
            significant_variances.sort(key=lambda x: abs(x['variance_percentage']), reverse=True)
            
            return {
                'success': True,
                'variance_analysis': {
                    'threshold_percentage': threshold * 100,
                    'significant_variances': significant_variances,
                    'favorable_variances': favorable_variances,
                    'unfavorable_variances': unfavorable_variances,
                    'summary': {
                        'total_significant_variances': len(significant_variances),
                        'favorable_count': len(favorable_variances),
                        'unfavorable_count': len(unfavorable_variances),
                        'largest_favorable': max(favorable_variances, key=lambda x: x['variance_percentage']) if favorable_variances else None,
                        'largest_unfavorable': min(unfavorable_variances, key=lambda x: x['variance_percentage']) if unfavorable_variances else None
                    }
                },
                'period_info': report_result['period'],
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating variance analysis: {e}")
            return {
                'success': False,
                'error': f"Variance analysis error: {str(e)}"
            }

# Global instance
budget_system = BudgetReportingSystem()