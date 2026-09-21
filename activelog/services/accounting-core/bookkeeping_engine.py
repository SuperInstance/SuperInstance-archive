#!/usr/bin/env python3
"""
Double-Entry Bookkeeping Engine
Handles double-entry validation, transaction recording, and account balance calculations
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class TransactionType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"

class ValidationRule(str, Enum):
    DEBITS_EQUAL_CREDITS = "debits_equal_credits"
    VALID_ACCOUNTS = "valid_accounts"
    NON_ZERO_AMOUNTS = "non_zero_amounts"
    BALANCED_ENTRY = "balanced_entry"
    ACCOUNT_TYPE_RULES = "account_type_rules"

class DoubleEntryBookkeepingEngine:
    """
    Core double-entry bookkeeping engine following GAAP principles
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')  # 2 decimal places for currency
        self.validation_rules = {
            ValidationRule.DEBITS_EQUAL_CREDITS: self._validate_debits_credits_equal,
            ValidationRule.VALID_ACCOUNTS: self._validate_accounts_exist,
            ValidationRule.NON_ZERO_AMOUNTS: self._validate_non_zero_amounts,
            ValidationRule.BALANCED_ENTRY: self._validate_balanced_entry,
            ValidationRule.ACCOUNT_TYPE_RULES: self._validate_account_type_rules
        }
        
    async def initialize(self):
        """Initialize the bookkeeping engine"""
        try:
            await self._setup_validation_cache()
            logger.info("Double-entry bookkeeping engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize bookkeeping engine: {e}")
            raise
    
    async def _setup_validation_cache(self):
        """Setup cached account data for faster validation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Cache account types and normal balances
        cursor.execute("""
            SELECT id, account_code, account_type, account_subtype, is_active
            FROM chart_of_accounts
            WHERE is_active = TRUE
        """)
        
        self.account_cache = {}
        self.normal_balances = {
            'asset': 'debit',
            'expense': 'debit',
            'liability': 'credit',
            'equity': 'credit',
            'revenue': 'credit'
        }
        
        for row in cursor.fetchall():
            self.account_cache[row[0]] = {
                'account_code': row[1],
                'account_type': row[2],
                'account_subtype': row[3],
                'is_active': row[4]
            }
        
        conn.close()
    
    async def validate_entry(self, journal_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Comprehensive validation of journal entry lines
        
        Args:
            journal_lines: List of journal entry lines with debit/credit amounts
            
        Returns:
            Validation result with errors and totals
        """
        try:
            validation_result = {
                'valid': False,
                'errors': [],
                'warnings': [],
                'total_debits': Decimal('0'),
                'total_credits': Decimal('0'),
                'line_validations': []
            }
            
            # Run all validation rules
            for rule, validator in self.validation_rules.items():
                rule_result = await validator(journal_lines)
                
                if not rule_result['valid']:
                    validation_result['errors'].extend(rule_result.get('errors', []))
                
                validation_result['warnings'].extend(rule_result.get('warnings', []))
                
                # Update totals from the balanced entry validation
                if rule == ValidationRule.DEBITS_EQUAL_CREDITS:
                    validation_result['total_debits'] = rule_result.get('total_debits', Decimal('0'))
                    validation_result['total_credits'] = rule_result.get('total_credits', Decimal('0'))
            
            # Validate individual lines
            for i, line in enumerate(journal_lines):
                line_validation = await self._validate_line(line, i + 1)
                validation_result['line_validations'].append(line_validation)
                
                if not line_validation['valid']:
                    validation_result['errors'].extend(line_validation['errors'])
            
            # Overall validation
            validation_result['valid'] = len(validation_result['errors']) == 0
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating journal entry: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'total_debits': Decimal('0'),
                'total_credits': Decimal('0'),
                'line_validations': []
            }
    
    async def _validate_debits_credits_equal(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that total debits equal total credits"""
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        for line in lines:
            debit_amount = Decimal(str(line.get('debit_amount', 0)))
            credit_amount = Decimal(str(line.get('credit_amount', 0)))
            
            total_debits += debit_amount
            total_credits += credit_amount
        
        # Round to prevent floating point precision issues
        total_debits = total_debits.quantize(self.precision, rounding=ROUND_HALF_UP)
        total_credits = total_credits.quantize(self.precision, rounding=ROUND_HALF_UP)
        
        valid = total_debits == total_credits
        errors = []
        
        if not valid:
            difference = abs(total_debits - total_credits)
            errors.append(
                f"Debits ({total_debits}) do not equal credits ({total_credits}). "
                f"Difference: {difference}"
            )
        
        return {
            'valid': valid,
            'errors': errors,
            'total_debits': total_debits,
            'total_credits': total_credits
        }
    
    async def _validate_accounts_exist(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that all referenced accounts exist and are active"""
        errors = []
        
        for i, line in enumerate(lines):
            account_id = line.get('account_id')
            
            if not account_id:
                errors.append(f"Line {i + 1}: Account ID is required")
                continue
            
            if account_id not in self.account_cache:
                errors.append(f"Line {i + 1}: Account {account_id} does not exist or is inactive")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _validate_non_zero_amounts(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that each line has either a debit or credit (but not both)"""
        errors = []
        warnings = []
        
        for i, line in enumerate(lines):
            debit_amount = Decimal(str(line.get('debit_amount', 0)))
            credit_amount = Decimal(str(line.get('credit_amount', 0)))
            
            if debit_amount == 0 and credit_amount == 0:
                errors.append(f"Line {i + 1}: Must have either a debit or credit amount")
            elif debit_amount > 0 and credit_amount > 0:
                errors.append(f"Line {i + 1}: Cannot have both debit and credit amounts")
            elif debit_amount < 0 or credit_amount < 0:
                errors.append(f"Line {i + 1}: Amounts cannot be negative")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    async def _validate_balanced_entry(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate that the entry is balanced according to accounting equation"""
        asset_changes = Decimal('0')
        liability_changes = Decimal('0')
        equity_changes = Decimal('0')
        
        for line in lines:
            account_id = line.get('account_id')
            if account_id not in self.account_cache:
                continue
                
            account_type = self.account_cache[account_id]['account_type']
            debit_amount = Decimal(str(line.get('debit_amount', 0)))
            credit_amount = Decimal(str(line.get('credit_amount', 0)))
            
            # Calculate net effect on each account type
            if account_type == 'asset':
                asset_changes += debit_amount - credit_amount
            elif account_type == 'liability':
                liability_changes += credit_amount - debit_amount
            elif account_type in ['equity', 'revenue']:
                equity_changes += credit_amount - debit_amount
            elif account_type == 'expense':
                # Expenses reduce equity
                equity_changes -= debit_amount - credit_amount
        
        # Assets = Liabilities + Equity (accounting equation)
        # Changes should balance: Asset changes = Liability changes + Equity changes
        expected_balance = liability_changes + equity_changes
        
        if abs(asset_changes - expected_balance) > self.precision:
            return {
                'valid': False,
                'errors': [
                    f"Entry does not maintain accounting equation balance. "
                    f"Asset changes: {asset_changes}, Liability + Equity changes: {expected_balance}"
                ]
            }
        
        return {'valid': True, 'errors': []}
    
    async def _validate_account_type_rules(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate account type specific rules"""
        warnings = []
        
        for i, line in enumerate(lines):
            account_id = line.get('account_id')
            if account_id not in self.account_cache:
                continue
            
            account_type = self.account_cache[account_id]['account_type']
            normal_balance = self.normal_balances.get(account_type)
            
            debit_amount = Decimal(str(line.get('debit_amount', 0)))
            credit_amount = Decimal(str(line.get('credit_amount', 0)))
            
            # Check if transaction goes against normal balance
            if normal_balance == 'debit' and credit_amount > debit_amount:
                warnings.append(
                    f"Line {i + 1}: Credit to {account_type} account "
                    f"(normal balance is debit) - verify this is correct"
                )
            elif normal_balance == 'credit' and debit_amount > credit_amount:
                warnings.append(
                    f"Line {i + 1}: Debit to {account_type} account "
                    f"(normal balance is credit) - verify this is correct"
                )
        
        return {
            'valid': True,
            'errors': [],
            'warnings': warnings
        }
    
    async def _validate_line(self, line: Dict[str, Any], line_number: int) -> Dict[str, Any]:
        """Validate individual journal entry line"""
        errors = []
        
        # Required fields
        required_fields = ['account_id', 'description']
        for field in required_fields:
            if not line.get(field):
                errors.append(f"Line {line_number}: {field} is required")
        
        # Amount precision
        debit_amount = line.get('debit_amount', 0)
        credit_amount = line.get('credit_amount', 0)
        
        try:
            debit_decimal = Decimal(str(debit_amount)).quantize(self.precision)
            credit_decimal = Decimal(str(credit_amount)).quantize(self.precision)
            
            if debit_decimal != Decimal(str(debit_amount)):
                errors.append(f"Line {line_number}: Debit amount has too many decimal places")
            if credit_decimal != Decimal(str(credit_amount)):
                errors.append(f"Line {line_number}: Credit amount has too many decimal places")
                
        except Exception as e:
            errors.append(f"Line {line_number}: Invalid amount format - {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def record_transaction(
        self, 
        journal_entry_id: str, 
        lines: List[Dict[str, Any]],
        transaction_date: date,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Record validated transaction and update account balances
        
        Args:
            journal_entry_id: Unique journal entry ID
            lines: List of journal entry lines
            transaction_date: Date of transaction
            user_id: User recording the transaction
            
        Returns:
            Recording result with balance updates
        """
        try:
            # Validate entry first
            validation = await self.validate_entry(lines)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'journal_entry_id': journal_entry_id
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Begin transaction
            cursor.execute("BEGIN TRANSACTION")
            
            balance_updates = []
            
            try:
                # Record each line and update balances
                for i, line in enumerate(lines):
                    line_id = f"JL_{uuid.uuid4().hex[:8].upper()}"
                    account_id = line['account_id']
                    debit_amount = Decimal(str(line.get('debit_amount', 0)))
                    credit_amount = Decimal(str(line.get('credit_amount', 0)))
                    
                    # Insert journal entry line
                    cursor.execute('''
                        INSERT INTO journal_entry_lines (
                            id, journal_entry_id, account_id, line_number,
                            description, debit_amount, credit_amount,
                            currency, exchange_rate, reference, data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        line_id, journal_entry_id, account_id, i + 1,
                        line.get('description', ''), float(debit_amount), float(credit_amount),
                        line.get('currency', 'USD'), line.get('exchange_rate', 1.0),
                        line.get('reference', ''), json.dumps(line)
                    ))
                    
                    # Update account balance
                    balance_update = await self._update_account_balance(
                        cursor, account_id, debit_amount, credit_amount
                    )
                    balance_updates.append(balance_update)
                    
                    # Record in general ledger
                    await self._record_general_ledger_entry(
                        cursor, account_id, journal_entry_id, line_id,
                        transaction_date, line.get('description', ''),
                        debit_amount, credit_amount, balance_update['new_balance']
                    )
                
                # Commit transaction
                cursor.execute("COMMIT")
                
                # Log successful recording
                await self._log_transaction_recording(
                    journal_entry_id, validation['total_debits'], 
                    validation['total_credits'], user_id
                )
                
                return {
                    'success': True,
                    'journal_entry_id': journal_entry_id,
                    'total_debits': validation['total_debits'],
                    'total_credits': validation['total_credits'],
                    'balance_updates': balance_updates,
                    'lines_recorded': len(lines)
                }
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                raise e
                
        except Exception as e:
            logger.error(f"Error recording transaction: {e}")
            return {
                'success': False,
                'errors': [f"Recording error: {str(e)}"],
                'journal_entry_id': journal_entry_id
            }
        finally:
            conn.close()
    
    async def _update_account_balance(
        self, 
        cursor, 
        account_id: str, 
        debit_amount: Decimal, 
        credit_amount: Decimal
    ) -> Dict[str, Any]:
        """Update account balance based on debit/credit amounts"""
        
        # Get current balance
        cursor.execute('''
            SELECT current_balance, debit_balance, credit_balance, account_type
            FROM chart_of_accounts WHERE id = ?
        ''', (account_id,))
        
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Account {account_id} not found")
        
        current_balance = Decimal(str(row[0]))
        debit_balance = Decimal(str(row[1]))
        credit_balance = Decimal(str(row[2]))
        account_type = row[3]
        
        # Update running totals
        new_debit_balance = debit_balance + debit_amount
        new_credit_balance = credit_balance + credit_amount
        
        # Calculate new current balance based on account type
        normal_balance = self.normal_balances.get(account_type, 'debit')
        
        if normal_balance == 'debit':
            new_current_balance = new_debit_balance - new_credit_balance
        else:
            new_current_balance = new_credit_balance - new_debit_balance
        
        # Update database
        cursor.execute('''
            UPDATE chart_of_accounts 
            SET current_balance = ?, debit_balance = ?, credit_balance = ?, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (float(new_current_balance), float(new_debit_balance), 
              float(new_credit_balance), account_id))
        
        return {
            'account_id': account_id,
            'old_balance': current_balance,
            'new_balance': new_current_balance,
            'debit_amount': debit_amount,
            'credit_amount': credit_amount,
            'new_debit_balance': new_debit_balance,
            'new_credit_balance': new_credit_balance
        }
    
    async def _record_general_ledger_entry(
        self, 
        cursor, 
        account_id: str, 
        journal_entry_id: str, 
        line_id: str,
        transaction_date: date, 
        description: str, 
        debit_amount: Decimal,
        credit_amount: Decimal, 
        running_balance: Decimal
    ):
        """Record entry in general ledger"""
        
        gl_id = f"GL_{uuid.uuid4().hex[:8].upper()}"
        
        cursor.execute('''
            INSERT INTO general_ledger (
                id, account_id, journal_entry_id, journal_line_id,
                transaction_date, description, debit_amount, credit_amount,
                running_balance, currency, exchange_rate, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            gl_id, account_id, journal_entry_id, line_id,
            transaction_date.isoformat(), description,
            float(debit_amount), float(credit_amount), float(running_balance),
            'USD', 1.0, json.dumps({
                'recorded_at': datetime.now().isoformat(),
                'gl_id': gl_id
            })
        ))
    
    async def _log_transaction_recording(
        self, 
        journal_entry_id: str, 
        total_debits: Decimal, 
        total_credits: Decimal, 
        user_id: str
    ):
        """Log transaction recording for audit trail"""
        logger.info(
            f"Transaction recorded - Entry: {journal_entry_id}, "
            f"Debits: {total_debits}, Credits: {total_credits}, "
            f"User: {user_id}"
        )
    
    async def calculate_account_balance(
        self, 
        account_id: str, 
        as_of_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Calculate account balance as of specific date
        
        Args:
            account_id: Account to calculate balance for
            as_of_date: Date to calculate balance as of (None for current)
            
        Returns:
            Account balance information
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
            
            if as_of_date is None:
                # Return current balance
                calculated_balance = Decimal(str(current_balance))
            else:
                # Calculate balance as of specific date
                cursor.execute('''
                    SELECT SUM(debit_amount - credit_amount) as net_change
                    FROM general_ledger
                    WHERE account_id = ? AND transaction_date <= ?
                ''', (account_id, as_of_date.isoformat()))
                
                net_change_row = cursor.fetchone()
                net_change = Decimal(str(net_change_row[0] if net_change_row[0] else 0))
                
                # Adjust for account type
                normal_balance = self.normal_balances.get(account_type, 'debit')
                if normal_balance == 'credit':
                    calculated_balance = -net_change
                else:
                    calculated_balance = net_change
            
            # Get transaction count
            date_filter = f"AND transaction_date <= '{as_of_date.isoformat()}'" if as_of_date else ""
            cursor.execute(f'''
                SELECT COUNT(*) FROM general_ledger 
                WHERE account_id = ? {date_filter}
            ''', (account_id,))
            transaction_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': True,
                'account_id': account_id,
                'account_code': account_code,
                'account_name': account_name,
                'account_type': account_type,
                'balance': calculated_balance,
                'as_of_date': as_of_date.isoformat() if as_of_date else None,
                'transaction_count': transaction_count,
                'normal_balance': self.normal_balances.get(account_type, 'debit'),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating account balance: {e}")
            return {
                'success': False,
                'error': f"Balance calculation error: {str(e)}"
            }
    
    async def verify_books_balance(self, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Verify that books are in balance (Assets = Liabilities + Equity)
        
        Args:
            as_of_date: Date to verify balance as of
            
        Returns:
            Balance verification results
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            date_filter = ""
            params = []
            if as_of_date:
                date_filter = "AND gl.transaction_date <= ?"
                params.append(as_of_date.isoformat())
            
            # Calculate balances by account type
            cursor.execute(f'''
                SELECT 
                    coa.account_type,
                    SUM(
                        CASE 
                            WHEN coa.account_type IN ('asset', 'expense') THEN gl.debit_amount - gl.credit_amount
                            ELSE gl.credit_amount - gl.debit_amount
                        END
                    ) as balance
                FROM chart_of_accounts coa
                LEFT JOIN general_ledger gl ON coa.id = gl.account_id {date_filter}
                WHERE coa.is_active = TRUE
                GROUP BY coa.account_type
            ''', params)
            
            balances = {}
            for row in cursor.fetchall():
                balances[row[0]] = Decimal(str(row[1] if row[1] else 0))
            
            # Calculate totals
            assets = balances.get('asset', Decimal('0'))
            liabilities = balances.get('liability', Decimal('0'))
            equity = balances.get('equity', Decimal('0'))
            revenue = balances.get('revenue', Decimal('0'))
            expenses = balances.get('expense', Decimal('0'))
            
            # Net income (Revenue - Expenses) is part of equity
            net_income = revenue - expenses
            total_equity = equity + net_income
            
            # Verify accounting equation: Assets = Liabilities + Equity
            difference = assets - (liabilities + total_equity)
            is_balanced = abs(difference) <= self.precision
            
            conn.close()
            
            return {
                'success': True,
                'is_balanced': is_balanced,
                'as_of_date': as_of_date.isoformat() if as_of_date else None,
                'assets': assets,
                'liabilities': liabilities,
                'equity': equity,
                'revenue': revenue,
                'expenses': expenses,
                'net_income': net_income,
                'total_equity': total_equity,
                'difference': difference,
                'accounting_equation_check': {
                    'left_side': assets,
                    'right_side': liabilities + total_equity,
                    'difference': difference,
                    'tolerance': self.precision
                },
                'verified_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error verifying books balance: {e}")
            return {
                'success': False,
                'error': f"Balance verification error: {str(e)}"
            }

# Global instance
double_entry_system = DoubleEntryBookkeepingEngine()