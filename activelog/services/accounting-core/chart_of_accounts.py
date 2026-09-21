#!/usr/bin/env python3
"""
Chart of Accounts Management System
Handles account creation, hierarchy management, and account standardization
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
import re

logger = logging.getLogger(__name__)

class AccountCodeStandard(str, Enum):
    """Standard account code ranges following GAAP"""
    ASSETS = "1000-1999"
    LIABILITIES = "2000-2999"
    EQUITY = "3000-3999"
    REVENUE = "4000-4999"
    EXPENSES = "5000-9999"

class AccountStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    PENDING_APPROVAL = "pending_approval"

class ChartOfAccountsManager:
    """
    Comprehensive chart of accounts management system
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.account_code_ranges = {
            'asset': (1000, 1999),
            'liability': (2000, 2999),
            'equity': (3000, 3999),
            'revenue': (4000, 4999),
            'expense': (5000, 9999)
        }
        
        # Standard account codes
        self.standard_accounts = {
            # Assets
            1000: {'name': 'Cash and Cash Equivalents', 'type': 'asset', 'subtype': 'current_asset'},
            1100: {'name': 'Accounts Receivable', 'type': 'asset', 'subtype': 'current_asset'},
            1200: {'name': 'Inventory', 'type': 'asset', 'subtype': 'current_asset'},
            1500: {'name': 'Fixed Assets', 'type': 'asset', 'subtype': 'fixed_asset'},
            1600: {'name': 'Accumulated Depreciation', 'type': 'asset', 'subtype': 'fixed_asset'},
            
            # Liabilities  
            2000: {'name': 'Accounts Payable', 'type': 'liability', 'subtype': 'current_liability'},
            2100: {'name': 'Accrued Expenses', 'type': 'liability', 'subtype': 'current_liability'},
            2500: {'name': 'Long-term Debt', 'type': 'liability', 'subtype': 'long_term_liability'},
            
            # Equity
            3000: {'name': 'Owner\'s Capital', 'type': 'equity', 'subtype': 'owners_equity'},
            3100: {'name': 'Retained Earnings', 'type': 'equity', 'subtype': 'retained_earnings'},
            3200: {'name': 'Drawing', 'type': 'equity', 'subtype': 'owners_equity'},
            
            # Revenue
            4000: {'name': 'Sales Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            4100: {'name': 'Service Revenue', 'type': 'revenue', 'subtype': 'operating_revenue'},
            4900: {'name': 'Other Revenue', 'type': 'revenue', 'subtype': 'non_operating_revenue'},
            
            # Expenses
            5000: {'name': 'Cost of Goods Sold', 'type': 'expense', 'subtype': 'operating_expense'},
            6000: {'name': 'Salaries and Wages', 'type': 'expense', 'subtype': 'operating_expense'},
            6100: {'name': 'Rent Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            6200: {'name': 'Utilities Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            6300: {'name': 'Office Supplies', 'type': 'expense', 'subtype': 'operating_expense'},
            6400: {'name': 'Insurance Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            6500: {'name': 'Depreciation Expense', 'type': 'expense', 'subtype': 'operating_expense'},
            7000: {'name': 'Interest Expense', 'type': 'expense', 'subtype': 'non_operating_expense'},
            8000: {'name': 'Income Tax Expense', 'type': 'expense', 'subtype': 'operating_expense'}
        }
    
    async def initialize(self):
        """Initialize the chart of accounts manager"""
        try:
            await self._setup_standard_accounts()
            logger.info("Chart of accounts manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize chart of accounts manager: {e}")
            raise
    
    async def _setup_standard_accounts(self):
        """Setup standard chart of accounts if none exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if any accounts exist
        cursor.execute("SELECT COUNT(*) FROM chart_of_accounts")
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Create standard accounts
            for code, account_info in self.standard_accounts.items():
                account_data = {
                    'id': f"ACC_{uuid.uuid4().hex[:8].upper()}",
                    'account_code': str(code),
                    'account_name': account_info['name'],
                    'account_type': account_info['type'],
                    'account_subtype': account_info['subtype'],
                    'is_active': True,
                    'requires_detail': False,
                    'cash_flow_type': self._determine_cash_flow_type(account_info['type']),
                    'current_balance': 0,
                    'debit_balance': 0,
                    'credit_balance': 0,
                    'parent_account_id': None,
                    'default_currency': 'USD',
                    'entity_id': None,
                    'description': f"Standard {account_info['name']} account",
                    'tax_code': None,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                cursor.execute('''
                    INSERT INTO chart_of_accounts (
                        id, account_code, account_name, account_type, account_subtype,
                        is_active, requires_detail, cash_flow_type, current_balance,
                        debit_balance, credit_balance, parent_account_id, default_currency,
                        entity_id, description, tax_code, created_at, updated_at, data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account_data['id'], account_data['account_code'], account_data['account_name'],
                    account_data['account_type'], account_data['account_subtype'],
                    account_data['is_active'], account_data['requires_detail'],
                    account_data['cash_flow_type'], account_data['current_balance'],
                    account_data['debit_balance'], account_data['credit_balance'],
                    account_data['parent_account_id'], account_data['default_currency'],
                    account_data['entity_id'], account_data['description'],
                    account_data['tax_code'], account_data['created_at'],
                    account_data['updated_at'], json.dumps(account_data)
                ))
            
            conn.commit()
            logger.info(f"Created {len(self.standard_accounts)} standard accounts")
        
        conn.close()
    
    def _determine_cash_flow_type(self, account_type: str) -> Optional[str]:
        """Determine cash flow statement type for account"""
        cash_flow_mapping = {
            'asset': 'operating',
            'liability': 'operating',
            'revenue': 'operating',
            'expense': 'operating',
            'equity': 'financing'
        }
        return cash_flow_mapping.get(account_type)
    
    async def create_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new account with validation
        
        Args:
            account_data: Account information
            
        Returns:
            Account creation result
        """
        try:
            # Validate account data
            validation = await self._validate_account_data(account_data)
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }
            
            # Validate account code
            code_validation = await self._validate_account_code(
                account_data['account_code'], 
                account_data['account_type']
            )
            if not code_validation['valid']:
                return {
                    'success': False,
                    'errors': code_validation['errors']
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for duplicate account code
            cursor.execute(
                "SELECT id FROM chart_of_accounts WHERE account_code = ?",
                (account_data['account_code'],)
            )
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'errors': [f"Account code {account_data['account_code']} already exists"]
                }
            
            # Validate parent account if specified
            if account_data.get('parent_account_id'):
                parent_validation = await self._validate_parent_account(
                    cursor, account_data['parent_account_id'], account_data['account_type']
                )
                if not parent_validation['valid']:
                    conn.close()
                    return {
                        'success': False,
                        'errors': parent_validation['errors']
                    }
            
            # Insert new account
            account_id = account_data['id']
            full_data = {
                **account_data,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'cash_flow_type': account_data.get('cash_flow_type') or self._determine_cash_flow_type(account_data['account_type']),
                'current_balance': Decimal('0'),
                'debit_balance': Decimal('0'),
                'credit_balance': Decimal('0')
            }
            
            cursor.execute('''
                INSERT INTO chart_of_accounts (
                    id, account_code, account_name, account_type, account_subtype,
                    is_active, requires_detail, cash_flow_type, current_balance,
                    debit_balance, credit_balance, parent_account_id, default_currency,
                    entity_id, description, tax_code, created_at, updated_at, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_id, full_data['account_code'], full_data['account_name'],
                full_data['account_type'], full_data['account_subtype'],
                full_data.get('is_active', True), full_data.get('requires_detail', False),
                full_data['cash_flow_type'], float(full_data['current_balance']),
                float(full_data['debit_balance']), float(full_data['credit_balance']),
                full_data.get('parent_account_id'), full_data.get('default_currency', 'USD'),
                full_data.get('entity_id'), full_data.get('description', ''),
                full_data.get('tax_code'), full_data['created_at'],
                full_data['updated_at'], json.dumps(full_data)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created account: {account_data['account_code']} - {account_data['account_name']}")
            
            return {
                'success': True,
                'account_id': account_id,
                'account_code': account_data['account_code'],
                'account_name': account_data['account_name'],
                'account_type': account_data['account_type']
            }
            
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return {
                'success': False,
                'errors': [f"Account creation error: {str(e)}"]
            }
    
    async def _validate_account_data(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate account data"""
        errors = []
        
        # Required fields
        required_fields = ['account_code', 'account_name', 'account_type', 'account_subtype']
        for field in required_fields:
            if not account_data.get(field):
                errors.append(f"{field} is required")
        
        # Account code format
        account_code = account_data.get('account_code', '')
        if account_code and not re.match(r'^[0-9]+$', account_code):
            errors.append("Account code must be numeric")
        
        # Account name length
        account_name = account_data.get('account_name', '')
        if len(account_name) < 3:
            errors.append("Account name must be at least 3 characters")
        if len(account_name) > 100:
            errors.append("Account name must be less than 100 characters")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def _validate_account_code(self, account_code: str, account_type: str) -> Dict[str, Any]:
        """Validate account code follows standard ranges"""
        try:
            code_num = int(account_code)
            min_code, max_code = self.account_code_ranges.get(account_type, (0, 0))
            
            if not (min_code <= code_num <= max_code):
                return {
                    'valid': False,
                    'errors': [
                        f"Account code {account_code} is not in valid range for {account_type} "
                        f"({min_code}-{max_code})"
                    ]
                }
            
            return {'valid': True, 'errors': []}
            
        except ValueError:
            return {
                'valid': False,
                'errors': ["Account code must be a valid number"]
            }
    
    async def _validate_parent_account(
        self, 
        cursor, 
        parent_account_id: str, 
        child_account_type: str
    ) -> Dict[str, Any]:
        """Validate parent account relationship"""
        cursor.execute(
            "SELECT account_type, requires_detail FROM chart_of_accounts WHERE id = ? AND is_active = TRUE",
            (parent_account_id,)
        )
        
        parent_row = cursor.fetchone()
        if not parent_row:
            return {
                'valid': False,
                'errors': ["Parent account not found or inactive"]
            }
        
        parent_type, requires_detail = parent_row
        
        # Parent must be same account type
        if parent_type != child_account_type:
            return {
                'valid': False,
                'errors': [
                    f"Parent account type ({parent_type}) must match child account type ({child_account_type})"
                ]
            }
        
        # Parent must allow sub-accounts
        if not requires_detail:
            return {
                'valid': False,
                'errors': ["Parent account does not allow sub-accounts"]
            }
        
        return {'valid': True, 'errors': []}
    
    async def get_chart_of_accounts(
        self, 
        account_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_balances: bool = True,
        entity_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get chart of accounts with optional filtering
        
        Args:
            account_type: Filter by account type
            is_active: Filter by active status
            include_balances: Include current balances
            entity_id: Filter by entity
            
        Returns:
            Chart of accounts data
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query with filters
            where_conditions = []
            params = []
            
            if account_type:
                where_conditions.append("account_type = ?")
                params.append(account_type)
            
            if is_active is not None:
                where_conditions.append("is_active = ?")
                params.append(is_active)
            
            if entity_id:
                where_conditions.append("entity_id = ?")
                params.append(entity_id)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            query = f'''
                SELECT 
                    id, account_code, account_name, account_type, account_subtype,
                    is_active, requires_detail, cash_flow_type, current_balance,
                    debit_balance, credit_balance, parent_account_id, default_currency,
                    entity_id, description, tax_code, created_at, updated_at
                FROM chart_of_accounts
                {where_clause}
                ORDER BY account_code
            '''
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            accounts = []
            account_hierarchy = {}
            
            for row in rows:
                account = {
                    'id': row[0],
                    'account_code': row[1],
                    'account_name': row[2],
                    'account_type': row[3],
                    'account_subtype': row[4],
                    'is_active': bool(row[5]),
                    'requires_detail': bool(row[6]),
                    'cash_flow_type': row[7],
                    'current_balance': Decimal(str(row[8])) if include_balances else None,
                    'debit_balance': Decimal(str(row[9])) if include_balances else None,
                    'credit_balance': Decimal(str(row[10])) if include_balances else None,
                    'parent_account_id': row[11],
                    'default_currency': row[12],
                    'entity_id': row[13],
                    'description': row[14],
                    'tax_code': row[15],
                    'created_at': row[16],
                    'updated_at': row[17],
                    'sub_accounts': []
                }
                
                accounts.append(account)
                account_hierarchy[account['id']] = account
            
            # Build hierarchy
            root_accounts = []
            for account in accounts:
                if account['parent_account_id']:
                    parent = account_hierarchy.get(account['parent_account_id'])
                    if parent:
                        parent['sub_accounts'].append(account)
                else:
                    root_accounts.append(account)
            
            # Calculate summary by account type
            summary = {}
            for account_type_name in ['asset', 'liability', 'equity', 'revenue', 'expense']:
                type_accounts = [a for a in accounts if a['account_type'] == account_type_name]
                total_balance = sum((a['current_balance'] or Decimal('0')) for a in type_accounts)
                
                summary[account_type_name] = {
                    'count': len(type_accounts),
                    'total_balance': total_balance,
                    'active_count': len([a for a in type_accounts if a['is_active']])
                }
            
            conn.close()
            
            return {
                'success': True,
                'accounts': root_accounts,
                'flat_accounts': accounts,
                'summary': summary,
                'total_accounts': len(accounts),
                'filters_applied': {
                    'account_type': account_type,
                    'is_active': is_active,
                    'entity_id': entity_id
                },
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting chart of accounts: {e}")
            return {
                'success': False,
                'error': f"Chart of accounts error: {str(e)}"
            }
    
    async def get_account_details(self, account_id: str) -> Dict[str, Any]:
        """Get detailed account information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get account details
            cursor.execute('''
                SELECT 
                    id, account_code, account_name, account_type, account_subtype,
                    is_active, requires_detail, cash_flow_type, current_balance,
                    debit_balance, credit_balance, parent_account_id, default_currency,
                    entity_id, description, tax_code, created_at, updated_at, data
                FROM chart_of_accounts WHERE id = ?
            ''', (account_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Account {account_id} not found"
                }
            
            account = {
                'id': row[0],
                'account_code': row[1],
                'account_name': row[2],
                'account_type': row[3],
                'account_subtype': row[4],
                'is_active': bool(row[5]),
                'requires_detail': bool(row[6]),
                'cash_flow_type': row[7],
                'current_balance': Decimal(str(row[8])),
                'debit_balance': Decimal(str(row[9])),
                'credit_balance': Decimal(str(row[10])),
                'parent_account_id': row[11],
                'default_currency': row[12],
                'entity_id': row[13],
                'description': row[14],
                'tax_code': row[15],
                'created_at': row[16],
                'updated_at': row[17]
            }
            
            # Get sub-accounts
            cursor.execute('''
                SELECT id, account_code, account_name, current_balance, is_active
                FROM chart_of_accounts 
                WHERE parent_account_id = ?
                ORDER BY account_code
            ''', (account_id,))
            
            sub_accounts = []
            for sub_row in cursor.fetchall():
                sub_accounts.append({
                    'id': sub_row[0],
                    'account_code': sub_row[1],
                    'account_name': sub_row[2],
                    'current_balance': Decimal(str(sub_row[3])),
                    'is_active': bool(sub_row[4])
                })
            
            account['sub_accounts'] = sub_accounts
            
            # Get parent account info
            if account['parent_account_id']:
                cursor.execute('''
                    SELECT account_code, account_name
                    FROM chart_of_accounts 
                    WHERE id = ?
                ''', (account['parent_account_id'],))
                
                parent_row = cursor.fetchone()
                if parent_row:
                    account['parent_account'] = {
                        'id': account['parent_account_id'],
                        'account_code': parent_row[0],
                        'account_name': parent_row[1]
                    }
            
            # Get recent transactions
            cursor.execute('''
                SELECT gl.transaction_date, gl.description, gl.debit_amount, gl.credit_amount,
                       je.entry_number
                FROM general_ledger gl
                JOIN journal_entries je ON gl.journal_entry_id = je.id
                WHERE gl.account_id = ?
                ORDER BY gl.transaction_date DESC, gl.created_at DESC
                LIMIT 10
            ''', (account_id,))
            
            recent_transactions = []
            for txn_row in cursor.fetchall():
                recent_transactions.append({
                    'transaction_date': txn_row[0],
                    'description': txn_row[1],
                    'debit_amount': Decimal(str(txn_row[2])),
                    'credit_amount': Decimal(str(txn_row[3])),
                    'entry_number': txn_row[4]
                })
            
            account['recent_transactions'] = recent_transactions
            
            # Calculate account statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as transaction_count,
                    MIN(transaction_date) as first_transaction,
                    MAX(transaction_date) as last_transaction
                FROM general_ledger
                WHERE account_id = ?
            ''', (account_id,))
            
            stats_row = cursor.fetchone()
            account['statistics'] = {
                'transaction_count': stats_row[0],
                'first_transaction': stats_row[1],
                'last_transaction': stats_row[2]
            }
            
            conn.close()
            
            return {
                'success': True,
                'account': account
            }
            
        except Exception as e:
            logger.error(f"Error getting account details: {e}")
            return {
                'success': False,
                'error': f"Account details error: {str(e)}"
            }
    
    async def update_account(self, account_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update account information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if account exists
            cursor.execute("SELECT data FROM chart_of_accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {
                    'success': False,
                    'error': f"Account {account_id} not found"
                }
            
            # Validate updates
            validation = await self._validate_account_updates(cursor, account_id, update_data)
            if not validation['valid']:
                conn.close()
                return {
                    'success': False,
                    'errors': validation['errors']
                }
            
            # Build update query
            update_fields = []
            params = []
            
            allowed_updates = [
                'account_name', 'description', 'is_active', 'requires_detail',
                'tax_code', 'default_currency'
            ]
            
            for field in allowed_updates:
                if field in update_data:
                    update_fields.append(f"{field} = ?")
                    params.append(update_data[field])
            
            if not update_fields:
                conn.close()
                return {
                    'success': False,
                    'error': "No valid fields to update"
                }
            
            # Add updated timestamp and data
            update_fields.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            
            # Execute update
            query = f"UPDATE chart_of_accounts SET {', '.join(update_fields)} WHERE id = ?"
            params.append(account_id)
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            logger.info(f"Updated account {account_id}")
            
            return {
                'success': True,
                'account_id': account_id,
                'updated_fields': list(update_data.keys())
            }
            
        except Exception as e:
            logger.error(f"Error updating account: {e}")
            return {
                'success': False,
                'error': f"Account update error: {str(e)}"
            }
    
    async def _validate_account_updates(
        self, 
        cursor, 
        account_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate account updates"""
        errors = []
        
        # Check if account has transactions before inactivating
        if 'is_active' in update_data and not update_data['is_active']:
            cursor.execute(
                "SELECT COUNT(*) FROM general_ledger WHERE account_id = ?",
                (account_id,)
            )
            transaction_count = cursor.fetchone()[0]
            
            if transaction_count > 0:
                errors.append(
                    f"Cannot inactivate account with {transaction_count} transactions. "
                    "Archive instead of inactivate."
                )
        
        # Validate account name length
        if 'account_name' in update_data:
            name = update_data['account_name']
            if len(name) < 3 or len(name) > 100:
                errors.append("Account name must be between 3 and 100 characters")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    async def archive_account(self, account_id: str, reason: str) -> Dict[str, Any]:
        """Archive account (soft delete)"""
        try:
            return await self.update_account(account_id, {
                'is_active': False,
                'description': f"ARCHIVED: {reason}. Original: {datetime.now().isoformat()}"
            })
        except Exception as e:
            logger.error(f"Error archiving account: {e}")
            return {
                'success': False,
                'error': f"Archive error: {str(e)}"
            }
    
    async def get_account_hierarchy(self, root_account_type: Optional[str] = None) -> Dict[str, Any]:
        """Get account hierarchy tree"""
        try:
            accounts_result = await self.get_chart_of_accounts(
                account_type=root_account_type, 
                is_active=True
            )
            
            if not accounts_result['success']:
                return accounts_result
            
            return {
                'success': True,
                'hierarchy': accounts_result['accounts'],
                'account_type_filter': root_account_type
            }
            
        except Exception as e:
            logger.error(f"Error getting account hierarchy: {e}")
            return {
                'success': False,
                'error': f"Hierarchy error: {str(e)}"
            }

# Global instance
coa_manager = ChartOfAccountsManager()