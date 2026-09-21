#!/usr/bin/env python3
"""
Credit Note Management System
Credit note creation, application, and refund processing
"""

import json
import sqlite3
import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class CreditNoteStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    APPLIED = "applied"
    CANCELLED = "cancelled"

class CreditNoteSystem:
    """Credit note management system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.precision = Decimal('0.01')
    
    async def initialize(self):
        """Initialize credit note system"""
        try:
            await self._setup_credit_tables()
            logger.info("Credit note system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize credit note system: {e}")
            raise
    
    async def _setup_credit_tables(self):
        """Setup credit note tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credit_notes (
                id TEXT PRIMARY KEY,
                credit_number TEXT UNIQUE NOT NULL,
                original_invoice_id TEXT,
                customer_id TEXT NOT NULL,
                credit_date DATE NOT NULL,
                amount DECIMAL NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                items TEXT NOT NULL,
                applied_amount DECIMAL DEFAULT 0,
                remaining_amount DECIMAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credit_applications (
                id TEXT PRIMARY KEY,
                credit_note_id TEXT NOT NULL,
                applied_to_invoice_id TEXT,
                applied_amount DECIMAL NOT NULL,
                application_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (credit_note_id) REFERENCES credit_notes (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_credit_note(self, credit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create credit note"""
        try:
            credit_id = f"CN_{uuid.uuid4().hex[:8].upper()}"
            credit_number = await self._generate_credit_number()
            
            amount = Decimal(str(credit_data['amount']))
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO credit_notes (
                    id, credit_number, original_invoice_id, customer_id,
                    credit_date, amount, reason, items, remaining_amount, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                credit_id, credit_number, credit_data.get('original_invoice_id'),
                credit_data['customer_id'], credit_data.get('credit_date', date.today().isoformat()),
                float(amount), credit_data['reason'], json.dumps(credit_data.get('items', [])),
                float(amount), json.dumps(credit_data)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'credit_id': credit_id,
                'credit_number': credit_number,
                'amount': amount
            }
            
        except Exception as e:
            logger.error(f"Error creating credit note: {e}")
            return {
                'success': False,
                'error': f"Credit note creation error: {str(e)}"
            }
    
    async def _generate_credit_number(self) -> str:
        """Generate unique credit number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM credit_notes")
        count = cursor.fetchone()[0] + 1
        conn.close()
        return f"CN-{date.today().strftime('%Y%m')}-{count:04d}"
    
    async def apply_credit_note(self, credit_id: str, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply credit note to invoice"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get credit note details
            cursor.execute('''
                SELECT remaining_amount, customer_id FROM credit_notes WHERE id = ?
            ''', (credit_id,))
            
            credit_row = cursor.fetchone()
            if not credit_row:
                conn.close()
                return {'success': False, 'error': 'Credit note not found'}
            
            remaining_amount = Decimal(str(credit_row[0]))
            credit_customer_id = credit_row[1]
            
            invoice_id = application_data['invoice_id']
            apply_amount = min(Decimal(str(application_data.get('amount', remaining_amount))), remaining_amount)
            
            # Apply credit to invoice
            from partial_payments import payment_tracking_system
            result = await payment_tracking_system.apply_customer_credit(
                credit_customer_id, invoice_id, apply_amount
            )
            
            if result['success']:
                # Record application
                app_id = f"CAPP_{uuid.uuid4().hex[:8].upper()}"
                cursor.execute('''
                    INSERT INTO credit_applications (
                        id, credit_note_id, applied_to_invoice_id, applied_amount, application_date
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (app_id, credit_id, invoice_id, float(apply_amount), date.today().isoformat()))
                
                # Update credit note
                new_remaining = remaining_amount - apply_amount
                new_applied = Decimal(str(cursor.execute('SELECT applied_amount FROM credit_notes WHERE id = ?', (credit_id,)).fetchone()[0])) + apply_amount
                new_status = 'applied' if new_remaining <= Decimal('0.01') else 'issued'
                
                cursor.execute('''
                    UPDATE credit_notes 
                    SET applied_amount = ?, remaining_amount = ?, status = ?
                    WHERE id = ?
                ''', (float(new_applied), float(new_remaining), new_status, credit_id))
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'credit_id': credit_id,
                    'application_id': app_id,
                    'applied_amount': apply_amount,
                    'remaining_amount': new_remaining
                }
            else:
                conn.close()
                return result
                
        except Exception as e:
            logger.error(f"Error applying credit note: {e}")
            return {'success': False, 'error': f"Credit application error: {str(e)}"}
    
    async def list_credit_notes(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List credit notes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT id, credit_number, customer_id, credit_date, amount,
                       reason, status, applied_amount, remaining_amount
                FROM credit_notes WHERE 1=1
            '''
            
            params = []
            if filters:
                if filters.get('customer_id'):
                    base_query += " AND customer_id = ?"
                    params.append(filters['customer_id'])
                if filters.get('status'):
                    base_query += " AND status = ?"
                    params.append(filters['status'])
            
            base_query += " ORDER BY created_at DESC"
            cursor.execute(base_query, params)
            
            credit_notes = []
            for row in cursor.fetchall():
                credit_notes.append({
                    'id': row[0], 'credit_number': row[1], 'customer_id': row[2],
                    'credit_date': row[3], 'amount': Decimal(str(row[4])),
                    'reason': row[5], 'status': row[6],
                    'applied_amount': Decimal(str(row[7])), 'remaining_amount': Decimal(str(row[8]))
                })
            
            conn.close()
            return {'success': True, 'credit_notes': credit_notes, 'count': len(credit_notes)}
            
        except Exception as e:
            logger.error(f"Error listing credit notes: {e}")
            return {'success': False, 'error': f"List error: {str(e)}"}

# Global instance
credit_system = CreditNoteSystem()