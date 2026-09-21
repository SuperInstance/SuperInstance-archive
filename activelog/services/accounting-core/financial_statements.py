#!/usr/bin/env python3
"""
Financial Statements Generator
Generates Income Statement, Balance Sheet, Cash Flow Statement, and financial ratios
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class FinancialStatementGenerator:
    """
    Comprehensive financial statement generator following GAAP principles
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
        
        # Account type mappings for financial statements
        self.statement_mappings = {
            'balance_sheet': {
                'assets': ['asset'],
                'liabilities': ['liability'],
                'equity': ['equity']
            },
            'income_statement': {
                'revenues': ['revenue'],
                'expenses': ['expense']
            },
            'cash_flow': {
                'operating': ['asset', 'liability', 'revenue', 'expense'],
                'investing': ['fixed_asset'],
                'financing': ['equity', 'long_term_liability']
            }
        }
    
    async def initialize(self):
        """Initialize the financial statement generator"""
        try:
            logger.info("Financial statement generator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize financial statement generator: {e}")
            raise
    
    async def generate_income_statement(
        self, 
        start_date: str, 
        end_date: str, 
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Income Statement (P&L)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build entity filter
            entity_filter = "AND coa.entity_id = ?" if entity_id else ""
            entity_params = [entity_id] if entity_id else []
            
            # Get revenue accounts
            cursor.execute(f'''
                SELECT 
                    coa.id, coa.account_code, coa.account_name, coa.account_subtype,
                    SUM(gl.credit_amount - gl.debit_amount) as balance
                FROM chart_of_accounts coa
                JOIN general_ledger gl ON coa.id = gl.account_id
                WHERE coa.account_type = 'revenue' 
                  AND coa.is_active = TRUE
                  AND gl.transaction_date BETWEEN ? AND ?
                  {entity_filter}
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_subtype
                HAVING ABS(balance) > 0.01
                ORDER BY coa.account_code
            ''', [start_date, end_date] + entity_params)
            
            revenues = []
            total_revenue = Decimal('0')
            
            for row in cursor.fetchall():
                balance = Decimal(str(row[4]))
                revenues.append({
                    'account_id': row[0],
                    'account_code': row[1],
                    'account_name': row[2],
                    'account_subtype': row[3],
                    'amount': balance
                })
                total_revenue += balance
            
            # Get expense accounts
            cursor.execute(f'''
                SELECT 
                    coa.id, coa.account_code, coa.account_name, coa.account_subtype,
                    SUM(gl.debit_amount - gl.credit_amount) as balance
                FROM chart_of_accounts coa
                JOIN general_ledger gl ON coa.id = gl.account_id
                WHERE coa.account_type = 'expense' 
                  AND coa.is_active = TRUE
                  AND gl.transaction_date BETWEEN ? AND ?
                  {entity_filter}
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_subtype
                HAVING ABS(balance) > 0.01
                ORDER BY coa.account_code
            ''', [start_date, end_date] + entity_params)
            
            expenses = []
            total_expenses = Decimal('0')
            
            for row in cursor.fetchall():
                balance = Decimal(str(row[4]))
                expenses.append({
                    'account_id': row[0],
                    'account_code': row[1],
                    'account_name': row[2],
                    'account_subtype': row[3],
                    'amount': balance
                })
                total_expenses += balance
            
            # Calculate net income
            net_income = total_revenue - total_expenses
            
            # Categorize expenses
            operating_expenses = [e for e in expenses if e['account_subtype'] == 'operating_expense']
            non_operating_expenses = [e for e in expenses if e['account_subtype'] == 'non_operating_expense']
            
            total_operating_expenses = sum(e['amount'] for e in operating_expenses)
            total_non_operating_expenses = sum(e['amount'] for e in non_operating_expenses)
            
            # Calculate key metrics
            gross_profit = total_revenue  # Simplified - would subtract COGS
            operating_income = total_revenue - total_operating_expenses
            
            conn.close()
            
            income_statement = {
                'statement_type': 'Income Statement',
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'entity_id': entity_id,
                'revenues': {
                    'operating_revenue': [r for r in revenues if r['account_subtype'] == 'operating_revenue'],
                    'non_operating_revenue': [r for r in revenues if r['account_subtype'] == 'non_operating_revenue'],
                    'total_revenue': total_revenue
                },
                'expenses': {
                    'operating_expenses': operating_expenses,
                    'non_operating_expenses': non_operating_expenses,
                    'total_operating_expenses': total_operating_expenses,
                    'total_non_operating_expenses': total_non_operating_expenses,
                    'total_expenses': total_expenses
                },
                'calculations': {
                    'gross_profit': gross_profit,
                    'operating_income': operating_income,
                    'net_income': net_income
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'income_statement': income_statement
            }
            
        except Exception as e:
            logger.error(f"Error generating income statement: {e}")
            return {
                'success': False,
                'error': f"Income statement error: {str(e)}"
            }
    
    async def generate_balance_sheet(
        self, 
        as_of_date: str, 
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Balance Sheet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            entity_filter = "AND coa.entity_id = ?" if entity_id else ""
            entity_params = [entity_id] if entity_id else []
            
            # Get asset accounts
            cursor.execute(f'''
                SELECT 
                    coa.id, coa.account_code, coa.account_name, coa.account_subtype,
                    SUM(gl.debit_amount - gl.credit_amount) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id AND gl.transaction_date <= ?
                WHERE coa.account_type = 'asset' 
                  AND coa.is_active = TRUE
                  {entity_filter}
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_subtype
                HAVING ABS(balance) > 0.01
                ORDER BY coa.account_code
            ''', [as_of_date] + entity_params)
            
            assets = []
            total_assets = Decimal('0')
            
            for row in cursor.fetchall():
                balance = Decimal(str(row[4] if row[4] else 0))
                assets.append({
                    'account_id': row[0],
                    'account_code': row[1],
                    'account_name': row[2],
                    'account_subtype': row[3],
                    'amount': balance
                })
                total_assets += balance
            
            # Get liability accounts
            cursor.execute(f'''
                SELECT 
                    coa.id, coa.account_code, coa.account_name, coa.account_subtype,
                    SUM(gl.credit_amount - gl.debit_amount) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id AND gl.transaction_date <= ?
                WHERE coa.account_type = 'liability' 
                  AND coa.is_active = TRUE
                  {entity_filter}
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_subtype
                HAVING ABS(balance) > 0.01
                ORDER BY coa.account_code
            ''', [as_of_date] + entity_params)
            
            liabilities = []
            total_liabilities = Decimal('0')
            
            for row in cursor.fetchall():
                balance = Decimal(str(row[4] if row[4] else 0))
                liabilities.append({
                    'account_id': row[0],
                    'account_code': row[1],
                    'account_name': row[2],
                    'account_subtype': row[3],
                    'amount': balance
                })
                total_liabilities += balance
            
            # Get equity accounts
            cursor.execute(f'''
                SELECT 
                    coa.id, coa.account_code, coa.account_name, coa.account_subtype,
                    SUM(gl.credit_amount - gl.debit_amount) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id AND gl.transaction_date <= ?
                WHERE coa.account_type = 'equity' 
                  AND coa.is_active = TRUE
                  {entity_filter}
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_subtype
                HAVING ABS(balance) > 0.01
                ORDER BY coa.account_code
            ''', [as_of_date] + entity_params)
            
            equity = []
            total_equity = Decimal('0')
            
            for row in cursor.fetchall():
                balance = Decimal(str(row[4] if row[4] else 0))
                equity.append({
                    'account_id': row[0],
                    'account_code': row[1],
                    'account_name': row[2],
                    'account_subtype': row[3],
                    'amount': balance
                })
                total_equity += balance
            
            # Categorize assets and liabilities
            current_assets = [a for a in assets if a['account_subtype'] == 'current_asset']
            fixed_assets = [a for a in assets if a['account_subtype'] == 'fixed_asset']
            
            current_liabilities = [l for l in liabilities if l['account_subtype'] == 'current_liability']
            long_term_liabilities = [l for l in liabilities if l['account_subtype'] == 'long_term_liability']
            
            total_current_assets = sum(a['amount'] for a in current_assets)
            total_fixed_assets = sum(a['amount'] for a in fixed_assets)
            total_current_liabilities = sum(l['amount'] for l in current_liabilities)
            total_long_term_liabilities = sum(l['amount'] for l in long_term_liabilities)
            
            # Calculate totals and check balance
            total_liabilities_equity = total_liabilities + total_equity
            is_balanced = abs(total_assets - total_liabilities_equity) <= self.precision
            
            conn.close()
            
            balance_sheet = {
                'statement_type': 'Balance Sheet',
                'as_of_date': as_of_date,
                'entity_id': entity_id,
                'assets': {
                    'current_assets': current_assets,
                    'fixed_assets': fixed_assets,
                    'total_current_assets': total_current_assets,
                    'total_fixed_assets': total_fixed_assets,
                    'total_assets': total_assets
                },
                'liabilities': {
                    'current_liabilities': current_liabilities,
                    'long_term_liabilities': long_term_liabilities,
                    'total_current_liabilities': total_current_liabilities,
                    'total_long_term_liabilities': total_long_term_liabilities,
                    'total_liabilities': total_liabilities
                },
                'equity': {
                    'equity_accounts': equity,
                    'total_equity': total_equity
                },
                'balance_check': {
                    'total_liabilities_equity': total_liabilities_equity,
                    'is_balanced': is_balanced,
                    'difference': total_assets - total_liabilities_equity
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'balance_sheet': balance_sheet
            }
            
        except Exception as e:
            logger.error(f"Error generating balance sheet: {e}")
            return {
                'success': False,
                'error': f"Balance sheet error: {str(e)}"
            }
    
    async def generate_cash_flow_statement(
        self, 
        start_date: str, 
        end_date: str, 
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate Cash Flow Statement (simplified indirect method)"""
        try:
            # Get net income from income statement
            income_result = await self.generate_income_statement(start_date, end_date, entity_id)
            if not income_result['success']:
                return income_result
            
            net_income = income_result['income_statement']['calculations']['net_income']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            entity_filter = "AND coa.entity_id = ?" if entity_id else ""
            entity_params = [entity_id] if entity_id else []
            
            # Get cash account changes
            cursor.execute(f'''
                SELECT 
                    SUM(gl.debit_amount - gl.credit_amount) as net_change
                FROM chart_of_accounts coa
                JOIN general_ledger gl ON coa.id = gl.account_id
                WHERE coa.account_code LIKE '10%' 
                  AND coa.account_name LIKE '%Cash%'
                  AND gl.transaction_date BETWEEN ? AND ?
                  {entity_filter}
            ''', [start_date, end_date] + entity_params)
            
            cash_change_row = cursor.fetchone()
            net_cash_change = Decimal(str(cash_change_row[0] if cash_change_row[0] else 0))
            
            # Simplified cash flow calculations
            # In a real implementation, this would be much more detailed
            
            # Operating activities (simplified)
            depreciation_expense = Decimal('0')  # Would calculate actual depreciation
            changes_in_working_capital = Decimal('0')  # Would calculate AR, AP, inventory changes
            
            operating_cash_flow = net_income + depreciation_expense + changes_in_working_capital
            
            # Investing activities (simplified)
            capital_expenditures = Decimal('0')  # Would calculate fixed asset purchases
            investing_cash_flow = -capital_expenditures
            
            # Financing activities (simplified)
            debt_changes = Decimal('0')  # Would calculate debt issuance/repayment
            equity_changes = Decimal('0')  # Would calculate equity transactions
            financing_cash_flow = debt_changes + equity_changes
            
            conn.close()
            
            cash_flow_statement = {
                'statement_type': 'Cash Flow Statement',
                'method': 'Indirect',
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'entity_id': entity_id,
                'operating_activities': {
                    'net_income': net_income,
                    'adjustments': {
                        'depreciation_expense': depreciation_expense,
                        'changes_in_working_capital': changes_in_working_capital
                    },
                    'net_cash_from_operations': operating_cash_flow
                },
                'investing_activities': {
                    'capital_expenditures': capital_expenditures,
                    'net_cash_from_investing': investing_cash_flow
                },
                'financing_activities': {
                    'debt_changes': debt_changes,
                    'equity_changes': equity_changes,
                    'net_cash_from_financing': financing_cash_flow
                },
                'summary': {
                    'net_change_in_cash': operating_cash_flow + investing_cash_flow + financing_cash_flow,
                    'actual_cash_change': net_cash_change
                },
                'generated_at': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'cash_flow_statement': cash_flow_statement
            }
            
        except Exception as e:
            logger.error(f"Error generating cash flow statement: {e}")
            return {
                'success': False,
                'error': f"Cash flow statement error: {str(e)}"
            }
    
    async def calculate_financial_ratios(
        self, 
        as_of_date: str, 
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate key financial ratios"""
        try:
            # Get balance sheet for ratios
            balance_sheet_result = await self.generate_balance_sheet(as_of_date, entity_id)
            if not balance_sheet_result['success']:
                return balance_sheet_result
            
            balance_sheet = balance_sheet_result['balance_sheet']
            
            # Get income statement for the year
            year_start = f"{as_of_date[:4]}-01-01"
            income_result = await self.generate_income_statement(year_start, as_of_date, entity_id)
            if not income_result['success']:
                return income_result
            
            income_statement = income_result['income_statement']
            
            # Extract key figures
            total_assets = balance_sheet['assets']['total_assets']
            current_assets = balance_sheet['assets']['total_current_assets']
            current_liabilities = balance_sheet['liabilities']['total_current_liabilities']
            total_liabilities = balance_sheet['liabilities']['total_liabilities']
            total_equity = balance_sheet['equity']['total_equity']
            
            net_income = income_statement['calculations']['net_income']
            total_revenue = income_statement['revenues']['total_revenue']
            
            # Calculate ratios
            ratios = {
                'liquidity_ratios': {
                    'current_ratio': current_assets / current_liabilities if current_liabilities > 0 else Decimal('0'),
                    'quick_ratio': current_assets / current_liabilities if current_liabilities > 0 else Decimal('0')  # Simplified
                },
                'leverage_ratios': {
                    'debt_to_equity': total_liabilities / total_equity if total_equity > 0 else Decimal('0'),
                    'debt_to_assets': total_liabilities / total_assets if total_assets > 0 else Decimal('0')
                },
                'profitability_ratios': {
                    'net_profit_margin': net_income / total_revenue if total_revenue > 0 else Decimal('0'),
                    'return_on_assets': net_income / total_assets if total_assets > 0 else Decimal('0'),
                    'return_on_equity': net_income / total_equity if total_equity > 0 else Decimal('0')
                },
                'efficiency_ratios': {
                    'asset_turnover': total_revenue / total_assets if total_assets > 0 else Decimal('0')
                }
            }
            
            return {
                'success': True,
                'financial_ratios': ratios,
                'as_of_date': as_of_date,
                'calculation_period': f"{year_start} to {as_of_date}"
            }
            
        except Exception as e:
            logger.error(f"Error calculating financial ratios: {e}")
            return {
                'success': False,
                'error': f"Financial ratios error: {str(e)}"
            }

# Global instance
statement_generator = FinancialStatementGenerator()