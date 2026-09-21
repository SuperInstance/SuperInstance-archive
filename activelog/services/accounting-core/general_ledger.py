#!/usr/bin/env python3
"""
General Ledger System
Handles posting from journal entries, balance calculations, trial balance generation,
and period-end closing procedures
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
import calendar

logger = logging.getLogger(__name__)

class PeriodStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PERMANENTLY_CLOSED = "permanently_closed"

class ClosingType(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    INTERIM = "interim"

class GeneralLedgerSystem:
    """
    Comprehensive general ledger system with posting, balance calculations, and reporting
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
        
        # Account normal balances for proper balance calculation
        self.normal_balances = {
            'asset': 'debit',
            'expense': 'debit',
            'liability': 'credit',
            'equity': 'credit',
            'revenue': 'credit'
        }
        
        # Closing account mappings
        self.closing_accounts = {
            'revenue_summary': 'Revenue Summary',
            'expense_summary': 'Expense Summary',
            'income_summary': 'Income Summary',
            'retained_earnings': 'Retained Earnings'
        }
    
    async def initialize(self):
        """Initialize the general ledger system"""
        try:
            await self._setup_period_tables()
            logger.info("General ledger system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize general ledger system: {e}")
            raise
    
    async def _setup_period_tables(self):
        """Setup period-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Period closing records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS period_closings (
                id TEXT PRIMARY KEY,
                period_id TEXT NOT NULL,
                closing_type TEXT NOT NULL,
                closing_date DATE NOT NULL,
                closed_by TEXT NOT NULL,
                revenue_closed DECIMAL DEFAULT 0,
                expense_closed DECIMAL DEFAULT 0,
                net_income DECIMAL DEFAULT 0,
                closing_entries TEXT, -- JSON array of closing journal entry IDs
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (period_id) REFERENCES financial_periods (id)
            )
        ''')
        
        # Trial balance snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trial_balance_snapshots (
                id TEXT PRIMARY KEY,
                snapshot_date DATE NOT NULL,
                period_id TEXT,
                total_debits DECIMAL NOT NULL,
                total_credits DECIMAL NOT NULL,
                is_balanced BOOLEAN NOT NULL,
                account_count INTEGER NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trial_balance_data TEXT NOT NULL -- JSON of trial balance
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def post_journal_entry(self, journal_entry_id: str) -> Dict[str, Any]:
        """
        Post journal entry to general ledger (called after journal entry is posted)
        
        Args:
            journal_entry_id: Journal entry ID that was posted
            
        Returns:
            Posting confirmation
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verify journal entry was posted
            cursor.execute('''
                SELECT status, entry_number FROM journal_entries WHERE id = ?
            ''', (journal_entry_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Journal entry {journal_entry_id} not found"
                }
            
            status, entry_number = row
            if status != 'posted':
                return {
                    'success': False,
                    'error': f"Journal entry {entry_number} is not posted (status: {status})"
                }
            
            # Verify all lines were recorded in general ledger
            cursor.execute('''
                SELECT COUNT(*) FROM general_ledger WHERE journal_entry_id = ?
            ''', (journal_entry_id,))
            
            gl_line_count = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM journal_entry_lines WHERE journal_entry_id = ?
            ''', (journal_entry_id,))
            
            je_line_count = cursor.fetchone()[0]
            
            conn.close()
            
            if gl_line_count != je_line_count:
                return {
                    'success': False,
                    'error': f"Mismatch in posted lines: {gl_line_count} in GL vs {je_line_count} in JE"
                }
            
            logger.info(f"Journal entry {entry_number} successfully posted to general ledger")
            
            return {
                'success': True,
                'journal_entry_id': journal_entry_id,
                'entry_number': entry_number,
                'lines_posted': gl_line_count
            }
            
        except Exception as e:
            logger.error(f"Error confirming journal entry posting: {e}")
            return {
                'success': False,
                'error': f"GL posting confirmation error: {str(e)}"
            }
    
    async def get_account_ledger(
        self, 
        account_id: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_beginning_balance: bool = True
    ) -> Dict[str, Any]:
        """
        Get account ledger with transactions and running balances
        
        Args:
            account_id: Account to get ledger for
            start_date: Start date filter
            end_date: End date filter
            include_beginning_balance: Include beginning balance calculation
            
        Returns:
            Account ledger data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get account information
            cursor.execute('''
                SELECT account_code, account_name, account_type, current_balance
                FROM chart_of_accounts WHERE id = ?
            ''', (account_id,))
            
            account_row = cursor.fetchone()
            if not account_row:
                return {
                    'success': False,
                    'error': f"Account {account_id} not found"
                }
            
            account_code, account_name, account_type, current_balance = account_row
            
            # Build query filters
            date_conditions = []
            params = [account_id]
            
            if start_date:
                date_conditions.append("gl.transaction_date >= ?")
                params.append(start_date)
            
            if end_date:
                date_conditions.append("gl.transaction_date <= ?")
                params.append(end_date)
            
            date_filter = ""
            if date_conditions:
                date_filter = "AND " + " AND ".join(date_conditions)
            
            # Calculate beginning balance if requested
            beginning_balance = Decimal('0')
            if include_beginning_balance and start_date:
                cursor.execute(f'''
                    SELECT SUM(
                        CASE 
                            WHEN ? IN ('asset', 'expense') THEN gl.debit_amount - gl.credit_amount
                            ELSE gl.credit_amount - gl.debit_amount
                        END
                    ) as balance
                    FROM general_ledger gl
                    WHERE gl.account_id = ? AND gl.transaction_date < ?
                ''', (account_type, account_id, start_date))
                
                balance_row = cursor.fetchone()
                beginning_balance = Decimal(str(balance_row[0] if balance_row[0] else 0))
            
            # Get ledger transactions
            cursor.execute(f'''
                SELECT 
                    gl.id, gl.transaction_date, gl.description, gl.debit_amount, gl.credit_amount,
                    gl.running_balance, gl.reference, je.entry_number, je.id as journal_entry_id,
                    gl.created_at
                FROM general_ledger gl
                JOIN journal_entries je ON gl.journal_entry_id = je.id
                WHERE gl.account_id = ? {date_filter}
                ORDER BY gl.transaction_date, gl.created_at
            ''', params)
            
            transactions = []
            running_balance = beginning_balance
            
            for row in cursor.fetchall():
                gl_id, txn_date, description, debit_amt, credit_amt = row[:5]
                stored_balance, reference, entry_number, je_id, created_at = row[5:]
                
                debit_amount = Decimal(str(debit_amt))
                credit_amount = Decimal(str(credit_amt))
                
                # Recalculate running balance for consistency
                if account_type in ['asset', 'expense']:
                    running_balance += debit_amount - credit_amount
                else:
                    running_balance += credit_amount - debit_amount
                
                transactions.append({
                    'id': gl_id,
                    'transaction_date': txn_date,
                    'description': description,
                    'debit_amount': debit_amount,
                    'credit_amount': credit_amount,
                    'running_balance': running_balance,
                    'stored_balance': Decimal(str(stored_balance)),
                    'reference': reference,
                    'entry_number': entry_number,
                    'journal_entry_id': je_id,
                    'created_at': created_at
                })
            
            # Calculate summary statistics
            total_debits = sum(t['debit_amount'] for t in transactions)
            total_credits = sum(t['credit_amount'] for t in transactions)
            ending_balance = running_balance
            
            conn.close()
            
            return {
                'success': True,
                'account': {
                    'id': account_id,
                    'account_code': account_code,
                    'account_name': account_name,
                    'account_type': account_type,
                    'normal_balance': self.normal_balances.get(account_type, 'debit')
                },
                'period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'beginning_balance': beginning_balance,
                    'ending_balance': ending_balance,
                    'current_system_balance': Decimal(str(current_balance))
                },
                'transactions': transactions,
                'summary': {
                    'transaction_count': len(transactions),
                    'total_debits': total_debits,
                    'total_credits': total_credits,
                    'net_change': total_debits - total_credits if account_type in ['asset', 'expense'] else total_credits - total_debits
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting account ledger: {e}")
            return {
                'success': False,
                'error': f"Account ledger error: {str(e)}"
            }
    
    async def generate_trial_balance(
        self, 
        as_of_date: Optional[str] = None,
        save_snapshot: bool = False,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate trial balance report
        
        Args:
            as_of_date: Date for trial balance (None for current)
            save_snapshot: Whether to save trial balance snapshot
            created_by: User generating the trial balance
            
        Returns:
            Trial balance report
        """
        try:
            if as_of_date is None:
                as_of_date = date.today().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all active accounts with balances
            date_filter = ""
            params = []
            if as_of_date:
                date_filter = "AND gl.transaction_date <= ?"
                params.append(as_of_date)
            
            query = f'''
                SELECT 
                    coa.id, coa.account_code, coa.account_name, coa.account_type,
                    coa.account_subtype,
                    COALESCE(SUM(gl.debit_amount), 0) as total_debits,
                    COALESCE(SUM(gl.credit_amount), 0) as total_credits,
                    COALESCE(SUM(
                        CASE 
                            WHEN coa.account_type IN ('asset', 'expense') 
                            THEN gl.debit_amount - gl.credit_amount
                            ELSE gl.credit_amount - gl.debit_amount
                        END
                    ), 0) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id {date_filter}
                WHERE coa.is_active = TRUE
                GROUP BY coa.id, coa.account_code, coa.account_name, coa.account_type, coa.account_subtype
                HAVING ABS(balance) > 0.01 OR total_debits > 0 OR total_credits > 0
                ORDER BY coa.account_code
            '''
            
            cursor.execute(query, params)
            
            accounts = []
            total_debit_balances = Decimal('0')
            total_credit_balances = Decimal('0')
            
            # Process each account
            for row in cursor.fetchall():
                account_id, account_code, account_name, account_type = row[:4]
                account_subtype, total_debits, total_credits, balance = row[4:]
                
                balance_decimal = Decimal(str(balance)).quantize(self.precision)
                
                # Determine if balance shows as debit or credit on trial balance
                normal_balance_side = self.normal_balances.get(account_type, 'debit')
                
                if balance_decimal > 0:
                    if normal_balance_side == 'debit':
                        debit_balance = balance_decimal
                        credit_balance = Decimal('0')
                        total_debit_balances += balance_decimal
                    else:
                        debit_balance = Decimal('0')
                        credit_balance = balance_decimal
                        total_credit_balances += balance_decimal
                elif balance_decimal < 0:
                    # Negative balance - shows on opposite side
                    abs_balance = abs(balance_decimal)
                    if normal_balance_side == 'debit':
                        debit_balance = Decimal('0')
                        credit_balance = abs_balance
                        total_credit_balances += abs_balance
                    else:
                        debit_balance = abs_balance
                        credit_balance = Decimal('0')
                        total_debit_balances += abs_balance
                else:
                    # Zero balance
                    debit_balance = Decimal('0')
                    credit_balance = Decimal('0')
                
                # Only include accounts with non-zero balances
                if debit_balance != Decimal('0') or credit_balance != Decimal('0'):
                    accounts.append({
                        'id': account_id,
                        'account_code': account_code,
                        'account_name': account_name,
                        'account_type': account_type,
                        'account_subtype': account_subtype,
                        'debit_balance': debit_balance,
                        'credit_balance': credit_balance,
                        'total_debits_period': Decimal(str(total_debits)),
                        'total_credits_period': Decimal(str(total_credits)),
                        'normal_balance_side': normal_balance_side
                    })
            
            # Check if trial balance balances
            difference = abs(total_debit_balances - total_credit_balances)
            is_balanced = difference <= self.precision
            
            trial_balance = {
                'as_of_date': as_of_date,
                'accounts': accounts,
                'totals': {
                    'total_debit_balances': total_debit_balances,
                    'total_credit_balances': total_credit_balances,
                    'difference': total_debit_balances - total_credit_balances,
                    'is_balanced': is_balanced
                },
                'summary': {
                    'account_count': len(accounts),
                    'accounts_with_debit_balances': len([a for a in accounts if a['debit_balance'] > 0]),
                    'accounts_with_credit_balances': len([a for a in accounts if a['credit_balance'] > 0])
                },
                'generated_at': datetime.now().isoformat()
            }
            
            # Save snapshot if requested
            if save_snapshot and created_by:
                await self._save_trial_balance_snapshot(cursor, trial_balance, created_by)
                conn.commit()
            
            conn.close()
            
            if not is_balanced:
                logger.warning(f"Trial balance out of balance by {difference}")
            else:
                logger.info(f"Trial balance generated successfully - {len(accounts)} accounts")
            
            return {
                'success': True,
                'trial_balance': trial_balance
            }
            
        except Exception as e:
            logger.error(f"Error generating trial balance: {e}")
            return {
                'success': False,
                'error': f"Trial balance error: {str(e)}"
            }
    
    async def _save_trial_balance_snapshot(
        self, 
        cursor, 
        trial_balance: Dict[str, Any], 
        created_by: str
    ):
        """Save trial balance snapshot"""
        snapshot_id = f"TB_{uuid.uuid4().hex[:8].upper()}"
        
        cursor.execute('''
            INSERT INTO trial_balance_snapshots (
                id, snapshot_date, total_debits, total_credits, is_balanced,
                account_count, created_by, trial_balance_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot_id, trial_balance['as_of_date'],
            float(trial_balance['totals']['total_debit_balances']),
            float(trial_balance['totals']['total_credit_balances']),
            trial_balance['totals']['is_balanced'],
            trial_balance['summary']['account_count'],
            created_by, json.dumps(trial_balance)
        ))
    
    async def close_period(
        self, 
        period_id: str, 
        closing_type: ClosingType,
        closed_by: str,
        auto_create_closing_entries: bool = True
    ) -> Dict[str, Any]:
        """
        Close accounting period with optional automatic closing entries
        
        Args:
            period_id: Financial period to close
            closing_type: Type of closing (monthly, quarterly, annually)
            closed_by: User performing the closing
            auto_create_closing_entries: Whether to auto-create closing entries
            
        Returns:
            Period closing result
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get period information
            cursor.execute('''
                SELECT period_name, start_date, end_date, is_closed
                FROM financial_periods WHERE id = ?
            ''', (period_id,))
            
            period_row = cursor.fetchone()
            if not period_row:
                return {
                    'success': False,
                    'error': f"Financial period {period_id} not found"
                }
            
            period_name, start_date, end_date, is_closed = period_row
            
            if is_closed:
                return {
                    'success': False,
                    'error': f"Period {period_name} is already closed"
                }
            
            closing_entries = []
            
            if auto_create_closing_entries:
                # Generate closing entries
                closing_result = await self._create_closing_entries(
                    cursor, period_id, start_date, end_date, closed_by
                )
                if not closing_result['success']:
                    conn.close()
                    return closing_result
                
                closing_entries = closing_result['closing_entries']
            
            # Calculate closing summary
            cursor.execute(f'''
                SELECT 
                    SUM(CASE WHEN coa.account_type = 'revenue' 
                        THEN gl.credit_amount - gl.debit_amount ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN coa.account_type = 'expense' 
                        THEN gl.debit_amount - gl.credit_amount ELSE 0 END) as total_expenses
                FROM general_ledger gl
                JOIN chart_of_accounts coa ON gl.account_id = coa.id
                WHERE gl.transaction_date BETWEEN ? AND ?
            ''', (start_date, end_date))
            
            summary_row = cursor.fetchone()
            total_revenue = Decimal(str(summary_row[0] if summary_row[0] else 0))
            total_expenses = Decimal(str(summary_row[1] if summary_row[1] else 0))
            net_income = total_revenue - total_expenses
            
            # Create period closing record
            closing_id = f"PC_{uuid.uuid4().hex[:8].upper()}"
            
            cursor.execute('''
                INSERT INTO period_closings (
                    id, period_id, closing_type, closing_date, closed_by,
                    revenue_closed, expense_closed, net_income, closing_entries,
                    status, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                closing_id, period_id, closing_type.value, end_date, closed_by,
                float(total_revenue), float(total_expenses), float(net_income),
                json.dumps([e['entry_id'] for e in closing_entries]),
                'completed', json.dumps({
                    'closing_id': closing_id,
                    'period_name': period_name,
                    'closing_summary': {
                        'total_revenue': float(total_revenue),
                        'total_expenses': float(total_expenses),
                        'net_income': float(net_income)
                    },
                    'closing_entries_created': len(closing_entries)
                })
            ))
            
            # Mark period as closed
            cursor.execute('''
                UPDATE financial_periods
                SET is_closed = TRUE, closed_by = ?, closed_date = ?
                WHERE id = ?
            ''', (closed_by, datetime.now().isoformat(), period_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Closed period {period_name} with net income of {net_income}")
            
            return {
                'success': True,
                'closing_id': closing_id,
                'period_id': period_id,
                'period_name': period_name,
                'closing_type': closing_type.value,
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'net_income': net_income,
                'closing_entries': closing_entries,
                'closed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error closing period: {e}")
            return {
                'success': False,
                'error': f"Period closing error: {str(e)}"
            }
    
    async def _create_closing_entries(
        self, 
        cursor, 
        period_id: str, 
        start_date: str, 
        end_date: str,
        closed_by: str
    ) -> Dict[str, Any]:
        """Create automatic closing journal entries"""
        try:
            from journal_entries import journal_system
            
            closing_entries = []
            
            # Get revenue accounts with balances
            cursor.execute('''
                SELECT coa.id, coa.account_name,
                       SUM(gl.credit_amount - gl.debit_amount) as revenue_balance
                FROM chart_of_accounts coa
                JOIN general_ledger gl ON coa.id = gl.account_id
                WHERE coa.account_type = 'revenue' 
                  AND coa.is_active = TRUE
                  AND gl.transaction_date BETWEEN ? AND ?
                GROUP BY coa.id, coa.account_name
                HAVING ABS(revenue_balance) > 0.01
            ''', (start_date, end_date))
            
            revenue_accounts = cursor.fetchall()
            
            # Get expense accounts with balances
            cursor.execute('''
                SELECT coa.id, coa.account_name,
                       SUM(gl.debit_amount - gl.credit_amount) as expense_balance
                FROM chart_of_accounts coa
                JOIN general_ledger gl ON coa.id = gl.account_id
                WHERE coa.account_type = 'expense' 
                  AND coa.is_active = TRUE
                  AND gl.transaction_date BETWEEN ? AND ?
                GROUP BY coa.id, coa.account_name
                HAVING ABS(expense_balance) > 0.01
            ''', (start_date, end_date))
            
            expense_accounts = cursor.fetchall()
            
            # Find or create Income Summary account
            income_summary_id = await self._get_or_create_closing_account(
                cursor, 'income_summary', 'equity'
            )
            
            # Find or create Retained Earnings account
            retained_earnings_id = await self._get_or_create_closing_account(
                cursor, 'retained_earnings', 'equity'
            )
            
            # 1. Close Revenue Accounts to Income Summary
            if revenue_accounts:
                revenue_lines = []
                total_revenue = Decimal('0')
                
                for account_id, account_name, revenue_balance in revenue_accounts:
                    balance = Decimal(str(revenue_balance))
                    total_revenue += balance
                    
                    # Debit revenue account (close it)
                    revenue_lines.append({
                        'account_id': account_id,
                        'description': f"Close {account_name} to Income Summary",
                        'debit_amount': float(balance),
                        'credit_amount': 0
                    })
                
                # Credit Income Summary
                revenue_lines.append({
                    'account_id': income_summary_id,
                    'description': "Close Revenue Accounts",
                    'debit_amount': 0,
                    'credit_amount': float(total_revenue)
                })
                
                # Create revenue closing entry
                revenue_entry = {
                    'id': f"CE_REV_{uuid.uuid4().hex[:8].upper()}",
                    'transaction_date': end_date,
                    'description': f"Close Revenue Accounts - Period Ending {end_date}",
                    'lines': revenue_lines,
                    'entry_type': 'closing',
                    'created_by': closed_by
                }
                
                result = await journal_system.create_entry(revenue_entry)
                if result['success']:
                    # Auto-approve and post
                    await journal_system.approve_entry(result['journal_entry_id'], closed_by)
                    await journal_system.post_entry(result['journal_entry_id'], closed_by)
                    closing_entries.append({
                        'type': 'revenue_closing',
                        'entry_id': result['journal_entry_id'],
                        'total_amount': total_revenue
                    })
            
            # 2. Close Expense Accounts to Income Summary
            if expense_accounts:
                expense_lines = []
                total_expenses = Decimal('0')
                
                for account_id, account_name, expense_balance in expense_accounts:
                    balance = Decimal(str(expense_balance))
                    total_expenses += balance
                    
                    # Credit expense account (close it)
                    expense_lines.append({
                        'account_id': account_id,
                        'description': f"Close {account_name} to Income Summary",
                        'debit_amount': 0,
                        'credit_amount': float(balance)
                    })
                
                # Debit Income Summary
                expense_lines.append({
                    'account_id': income_summary_id,
                    'description': "Close Expense Accounts",
                    'debit_amount': float(total_expenses),
                    'credit_amount': 0
                })
                
                # Create expense closing entry
                expense_entry = {
                    'id': f"CE_EXP_{uuid.uuid4().hex[:8].upper()}",
                    'transaction_date': end_date,
                    'description': f"Close Expense Accounts - Period Ending {end_date}",
                    'lines': expense_lines,
                    'entry_type': 'closing',
                    'created_by': closed_by
                }
                
                result = await journal_system.create_entry(expense_entry)
                if result['success']:
                    # Auto-approve and post
                    await journal_system.approve_entry(result['journal_entry_id'], closed_by)
                    await journal_system.post_entry(result['journal_entry_id'], closed_by)
                    closing_entries.append({
                        'type': 'expense_closing',
                        'entry_id': result['journal_entry_id'],
                        'total_amount': total_expenses
                    })
            
            # 3. Close Income Summary to Retained Earnings
            total_revenue = sum(Decimal(str(r[2])) for r in revenue_accounts)
            total_expenses = sum(Decimal(str(e[2])) for e in expense_accounts)
            net_income = total_revenue - total_expenses
            
            if abs(net_income) > self.precision:
                income_summary_lines = []
                
                if net_income > 0:
                    # Profit - Debit Income Summary, Credit Retained Earnings
                    income_summary_lines.extend([
                        {
                            'account_id': income_summary_id,
                            'description': "Close Net Income to Retained Earnings",
                            'debit_amount': float(net_income),
                            'credit_amount': 0
                        },
                        {
                            'account_id': retained_earnings_id,
                            'description': "Net Income for Period",
                            'debit_amount': 0,
                            'credit_amount': float(net_income)
                        }
                    ])
                else:
                    # Loss - Credit Income Summary, Debit Retained Earnings
                    net_loss = abs(net_income)
                    income_summary_lines.extend([
                        {
                            'account_id': income_summary_id,
                            'description': "Close Net Loss to Retained Earnings",
                            'debit_amount': 0,
                            'credit_amount': float(net_loss)
                        },
                        {
                            'account_id': retained_earnings_id,
                            'description': "Net Loss for Period",
                            'debit_amount': float(net_loss),
                            'credit_amount': 0
                        }
                    ])
                
                # Create income summary closing entry
                income_entry = {
                    'id': f"CE_INC_{uuid.uuid4().hex[:8].upper()}",
                    'transaction_date': end_date,
                    'description': f"Close Income Summary - Period Ending {end_date}",
                    'lines': income_summary_lines,
                    'entry_type': 'closing',
                    'created_by': closed_by
                }
                
                result = await journal_system.create_entry(income_entry)
                if result['success']:
                    # Auto-approve and post
                    await journal_system.approve_entry(result['journal_entry_id'], closed_by)
                    await journal_system.post_entry(result['journal_entry_id'], closed_by)
                    closing_entries.append({
                        'type': 'income_summary_closing',
                        'entry_id': result['journal_entry_id'],
                        'net_income': net_income
                    })
            
            return {
                'success': True,
                'closing_entries': closing_entries
            }
            
        except Exception as e:
            logger.error(f"Error creating closing entries: {e}")
            return {
                'success': False,
                'error': f"Closing entries error: {str(e)}"
            }
    
    async def _get_or_create_closing_account(
        self, 
        cursor, 
        account_key: str, 
        account_type: str
    ) -> str:
        """Get or create closing account (Income Summary, Retained Earnings, etc.)"""
        
        account_name = self.closing_accounts[account_key]
        
        # Try to find existing account
        cursor.execute('''
            SELECT id FROM chart_of_accounts 
            WHERE account_name = ? AND account_type = ? AND is_active = TRUE
        ''', (account_name, account_type))
        
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Create new closing account
        from chart_of_accounts import coa_manager
        
        account_code_ranges = {
            'income_summary': '3500',
            'retained_earnings': '3100'
        }
        
        account_data = {
            'id': f"ACC_{uuid.uuid4().hex[:8].upper()}",
            'account_code': account_code_ranges.get(account_key, '3999'),
            'account_name': account_name,
            'account_type': account_type,
            'account_subtype': 'retained_earnings' if 'retained' in account_key else 'owners_equity',
            'description': f"System-created {account_name} account for period closing"
        }
        
        result = await coa_manager.create_account(account_data)
        if result['success']:
            return account_data['id']
        else:
            raise Exception(f"Failed to create closing account {account_name}")

# Global instance
ledger_system = GeneralLedgerSystem()