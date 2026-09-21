#!/usr/bin/env python3
"""
Accounts Payable System
Handles vendor bill management, payment scheduling, aging analysis, and vendor management
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

class BillStatus(str, Enum):
    DRAFT = "draft"
    OUTSTANDING = "outstanding"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"

class VendorPaymentSystem:
    """
    Comprehensive accounts payable management system
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
        
        # Aging buckets (days)
        self.aging_buckets = [
            (0, 30, "Current"),
            (31, 60, "31-60 days"),
            (61, 90, "61-90 days"),
            (91, 120, "91-120 days"),
            (121, float('inf'), "Over 120 days")
        ]
    
    async def initialize(self):
        """Initialize the accounts payable system"""
        try:
            await self._setup_ap_tables()
            logger.info("Accounts payable system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AP system: {e}")
            raise
    
    async def _setup_ap_tables(self):
        """Setup AP-specific tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Vendor information table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendors (
                id TEXT PRIMARY KEY,
                vendor_code TEXT UNIQUE NOT NULL,
                vendor_name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                address TEXT,
                payment_terms INTEGER DEFAULT 30,
                tax_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # AP payments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ap_payments (
                id TEXT PRIMARY KEY,
                vendor_id TEXT NOT NULL,
                bill_id TEXT,
                payment_date DATE NOT NULL,
                payment_amount DECIMAL NOT NULL,
                payment_method TEXT NOT NULL,
                check_number TEXT,
                reference_number TEXT,
                journal_entry_id TEXT,
                notes TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (vendor_id) REFERENCES vendors (id),
                FOREIGN KEY (bill_id) REFERENCES accounts_payable (id),
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_bill(self, bill_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create vendor bill"""
        try:
            bill_id = f"BILL_{uuid.uuid4().hex[:8].upper()}"
            bill_number = self._generate_bill_number()
            
            # Calculate due date
            bill_date = datetime.strptime(bill_data['bill_date'], "%Y-%m-%d").date()
            payment_terms = bill_data.get('payment_terms', 30)
            due_date = bill_date + timedelta(days=payment_terms)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert bill
            cursor.execute('''
                INSERT INTO accounts_payable (
                    id, vendor_id, bill_number, bill_date, due_date,
                    total_amount, amount_paid, amount_due, currency, status,
                    created_at, updated_at, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                bill_id, bill_data['vendor_id'], bill_number,
                bill_data['bill_date'], due_date.isoformat(),
                float(Decimal(str(bill_data['total_amount']))),
                0, float(Decimal(str(bill_data['total_amount']))),
                bill_data.get('currency', 'USD'), BillStatus.OUTSTANDING.value,
                datetime.now().isoformat(), datetime.now().isoformat(),
                json.dumps({**bill_data, 'id': bill_id, 'bill_number': bill_number})
            ))
            
            # Create journal entry for bill
            await self._create_bill_journal_entry(cursor, bill_id, bill_data)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'bill_id': bill_id,
                'bill_number': bill_number,
                'total_amount': Decimal(str(bill_data['total_amount'])),
                'due_date': due_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating bill: {e}")
            return {
                'success': False,
                'error': f"Bill creation error: {str(e)}"
            }
    
    def _generate_bill_number(self) -> str:
        """Generate unique bill number"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"BILL{date_str}{random_str}"
    
    async def _create_bill_journal_entry(self, cursor, bill_id: str, bill_data: Dict[str, Any]):
        """Create journal entry for bill"""
        from journal_entries import journal_system
        
        # Get AP account (assuming code 2000)
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '2000' AND is_active = TRUE")
        ap_account_row = cursor.fetchone()
        if not ap_account_row:
            raise Exception("Accounts Payable account not found")
        ap_account_id = ap_account_row[0]
        
        # Get expense account (assuming code 6000 for general expenses)
        expense_account_id = bill_data.get('expense_account_id')
        if not expense_account_id:
            cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '6000' AND is_active = TRUE")
            expense_account_row = cursor.fetchone()
            if not expense_account_row:
                raise Exception("Expense account not found")
            expense_account_id = expense_account_row[0]
        
        total_amount = Decimal(str(bill_data['total_amount']))
        
        journal_entry_data = {
            'id': f"JE_{uuid.uuid4().hex[:8].upper()}",
            'transaction_date': bill_data['bill_date'],
            'description': f"Vendor Bill - {bill_data.get('description', 'Vendor Bill')}",
            'reference': bill_id,
            'lines': [
                {
                    'account_id': expense_account_id,
                    'description': 'Vendor Bill - Expense',
                    'debit_amount': float(total_amount),
                    'credit_amount': 0
                },
                {
                    'account_id': ap_account_id,
                    'description': 'Vendor Bill - Accounts Payable',
                    'debit_amount': 0,
                    'credit_amount': float(total_amount)
                }
            ],
            'created_by': 'AP_SYSTEM'
        }
        
        result = await journal_system.create_entry(journal_entry_data)
        if result['success']:
            await journal_system.approve_entry(result['journal_entry_id'], 'AP_SYSTEM')
            await journal_system.post_entry(result['journal_entry_id'], 'AP_SYSTEM')
            
            cursor.execute(
                "UPDATE accounts_payable SET journal_entry_id = ? WHERE id = ?",
                (result['journal_entry_id'], bill_id)
            )
    
    async def record_payment(self, bill_id: str, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record vendor payment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get bill details
            cursor.execute(
                "SELECT vendor_id, total_amount, amount_paid, amount_due FROM accounts_payable WHERE id = ?",
                (bill_id,)
            )
            bill_row = cursor.fetchone()
            if not bill_row:
                return {'success': False, 'error': f"Bill {bill_id} not found"}
            
            vendor_id, total_amount, amount_paid, amount_due = bill_row
            payment_amount = Decimal(str(payment_data['payment_amount']))
            
            if payment_amount > Decimal(str(amount_due)):
                return {'success': False, 'error': "Payment amount exceeds amount due"}
            
            # Record payment
            payment_id = f"VPAY_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO ap_payments (
                    id, vendor_id, bill_id, payment_date, payment_amount,
                    payment_method, check_number, reference_number, notes, created_by, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_id, vendor_id, bill_id, payment_data['payment_date'],
                float(payment_amount), payment_data.get('payment_method', 'check'),
                payment_data.get('check_number'), payment_data.get('reference_number'),
                payment_data.get('notes'), payment_data.get('created_by', 'AP_SYSTEM'),
                json.dumps(payment_data)
            ))
            
            # Update bill
            new_amount_paid = Decimal(str(amount_paid)) + payment_amount
            new_amount_due = Decimal(str(total_amount)) - new_amount_paid
            
            new_status = BillStatus.PAID.value if new_amount_due <= Decimal('0.01') else BillStatus.PARTIAL.value
            
            cursor.execute('''
                UPDATE accounts_payable 
                SET amount_paid = ?, amount_due = ?, status = ?, updated_at = ?
                WHERE id = ?
            ''', (
                float(new_amount_paid), float(new_amount_due), new_status,
                datetime.now().isoformat(), bill_id
            ))
            
            # Create payment journal entry
            await self._create_payment_journal_entry(cursor, payment_id, payment_data, payment_amount)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_amount': payment_amount,
                'new_balance': new_amount_due,
                'bill_status': new_status
            }
            
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            return {
                'success': False,
                'error': f"Payment recording error: {str(e)}"
            }
    
    async def _create_payment_journal_entry(self, cursor, payment_id: str, payment_data: Dict[str, Any], payment_amount: Decimal):
        """Create journal entry for payment"""
        from journal_entries import journal_system
        
        # Get cash account
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '1000' AND is_active = TRUE")
        cash_account_row = cursor.fetchone()
        if not cash_account_row:
            raise Exception("Cash account not found")
        cash_account_id = cash_account_row[0]
        
        # Get AP account
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '2000' AND is_active = TRUE")
        ap_account_row = cursor.fetchone()
        if not ap_account_row:
            raise Exception("Accounts Payable account not found")
        ap_account_id = ap_account_row[0]
        
        journal_entry_data = {
            'id': f"JE_{uuid.uuid4().hex[:8].upper()}",
            'transaction_date': payment_data['payment_date'],
            'description': f"Vendor Payment - {payment_data.get('payment_method', 'Check')}",
            'reference': payment_id,
            'lines': [
                {
                    'account_id': ap_account_id,
                    'description': 'Reduce Accounts Payable',
                    'debit_amount': float(payment_amount),
                    'credit_amount': 0
                },
                {
                    'account_id': cash_account_id,
                    'description': 'Vendor Payment Made',
                    'debit_amount': 0,
                    'credit_amount': float(payment_amount)
                }
            ],
            'created_by': 'AP_SYSTEM'
        }
        
        result = await journal_system.create_entry(journal_entry_data)
        if result['success']:
            await journal_system.approve_entry(result['journal_entry_id'], 'AP_SYSTEM')
            await journal_system.post_entry(result['journal_entry_id'], 'AP_SYSTEM')
    
    async def get_payables(self, vendor_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Get accounts payable"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_conditions = []
            params = []
            
            if vendor_id:
                where_conditions.append("ap.vendor_id = ?")
                params.append(vendor_id)
            
            if status:
                where_conditions.append("ap.status = ?")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            cursor.execute(f'''
                SELECT 
                    ap.id, ap.bill_number, ap.bill_date, ap.due_date,
                    ap.total_amount, ap.amount_paid, ap.amount_due, ap.status,
                    v.vendor_name, v.vendor_code
                FROM accounts_payable ap
                JOIN vendors v ON ap.vendor_id = v.id
                {where_clause}
                ORDER BY ap.due_date
            ''', params)
            
            payables = []
            for row in cursor.fetchall():
                payables.append({
                    'id': row[0],
                    'bill_number': row[1],
                    'bill_date': row[2],
                    'due_date': row[3],
                    'total_amount': Decimal(str(row[4])),
                    'amount_paid': Decimal(str(row[5])),
                    'amount_due': Decimal(str(row[6])),
                    'status': row[7],
                    'vendor_name': row[8],
                    'vendor_code': row[9],
                    'days_outstanding': (date.today() - datetime.strptime(row[2], "%Y-%m-%d").date()).days
                })
            
            conn.close()
            
            return {
                'success': True,
                'payables': payables,
                'total_outstanding': sum(p['amount_due'] for p in payables)
            }
            
        except Exception as e:
            logger.error(f"Error getting payables: {e}")
            return {
                'success': False,
                'error': f"Get payables error: {str(e)}"
            }
    
    async def generate_aging_report(self, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Generate aging report"""
        try:
            if as_of_date is None:
                as_of_date = date.today().isoformat()
            
            reference_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    ap.id, ap.bill_number, ap.bill_date, ap.due_date,
                    ap.amount_due, v.vendor_name, v.vendor_code
                FROM accounts_payable ap
                JOIN vendors v ON ap.vendor_id = v.id
                WHERE ap.amount_due > 0.01 AND ap.status != 'paid'
            ''')
            
            aging_data = {bucket[2]: [] for bucket in self.aging_buckets}
            aging_totals = {bucket[2]: Decimal('0') for bucket in self.aging_buckets}
            
            for row in cursor.fetchall():
                bill_id, bill_number, bill_date, due_date = row[:4]
                amount_due, vendor_name, vendor_code = row[4:]
                
                bill_date_obj = datetime.strptime(bill_date, "%Y-%m-%d").date()
                days_outstanding = (reference_date - bill_date_obj).days
                
                # Find appropriate aging bucket
                bucket_name = "Over 120 days"  # default
                for min_days, max_days, name in self.aging_buckets:
                    if min_days <= days_outstanding <= max_days:
                        bucket_name = name
                        break
                
                amount_decimal = Decimal(str(amount_due))
                aging_data[bucket_name].append({
                    'bill_id': bill_id,
                    'bill_number': bill_number,
                    'bill_date': bill_date,
                    'due_date': due_date,
                    'vendor_name': vendor_name,
                    'vendor_code': vendor_code,
                    'amount_due': amount_decimal,
                    'days_outstanding': days_outstanding
                })
                aging_totals[bucket_name] += amount_decimal
            
            total_outstanding = sum(aging_totals.values())
            
            conn.close()
            
            return {
                'success': True,
                'as_of_date': as_of_date,
                'aging_data': aging_data,
                'aging_totals': aging_totals,
                'total_outstanding': total_outstanding,
                'aging_percentages': {
                    bucket: (amount / total_outstanding * 100) if total_outstanding > 0 else Decimal('0')
                    for bucket, amount in aging_totals.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating aging report: {e}")
            return {
                'success': False,
                'error': f"Aging report error: {str(e)}"
            }

# Global instance
ap_system = VendorPaymentSystem()