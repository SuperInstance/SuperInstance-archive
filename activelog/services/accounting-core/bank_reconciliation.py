#!/usr/bin/env python3
"""
Bank Reconciliation System
Bank statement import, transaction matching, and reconciliation automation
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
import uuid
import csv
import io

logger = logging.getLogger(__name__)

class BankReconciliationSystem:
    """Comprehensive bank reconciliation system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
        
        # Matching algorithm weights
        self.matching_weights = {
            'exact_amount': 40,
            'date_proximity': 20,
            'reference_match': 25,
            'description_similarity': 15
        }
    
    async def initialize(self):
        """Initialize bank reconciliation system"""
        try:
            await self._setup_reconciliation_tables()
            logger.info("Bank reconciliation system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize bank reconciliation system: {e}")
            raise
    
    async def _setup_reconciliation_tables(self):
        """Setup reconciliation-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Bank accounts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id TEXT PRIMARY KEY,
                bank_name TEXT NOT NULL,
                account_name TEXT NOT NULL,
                account_number TEXT NOT NULL,
                account_type TEXT NOT NULL,
                routing_number TEXT,
                account_id TEXT NOT NULL,
                current_balance DECIMAL DEFAULT 0,
                last_reconciled_date DATE,
                last_reconciled_balance DECIMAL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id)
            )
        ''')
        
        # Bank transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_transactions (
                id TEXT PRIMARY KEY,
                bank_account_id TEXT NOT NULL,
                transaction_date DATE NOT NULL,
                description TEXT NOT NULL,
                amount DECIMAL NOT NULL,
                type TEXT NOT NULL,
                check_number TEXT,
                reference TEXT,
                is_reconciled BOOLEAN DEFAULT FALSE,
                reconciled_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (bank_account_id) REFERENCES bank_accounts (id)
            )
        ''')
        
        # Transaction matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transaction_matches (
                id TEXT PRIMARY KEY,
                bank_transaction_id TEXT NOT NULL,
                gl_transaction_id TEXT,
                journal_entry_id TEXT,
                match_confidence DECIMAL NOT NULL,
                match_reason TEXT,
                matched_by TEXT NOT NULL,
                is_manual BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (bank_transaction_id) REFERENCES bank_transactions (id),
                FOREIGN KEY (gl_transaction_id) REFERENCES general_ledger (id),
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
            )
        ''')
        
        # Bank reconciliations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_reconciliations (
                id TEXT PRIMARY KEY,
                bank_account_id TEXT NOT NULL,
                statement_date DATE NOT NULL,
                ending_balance DECIMAL NOT NULL,
                book_balance DECIMAL NOT NULL,
                reconciled_balance DECIMAL NOT NULL,
                outstanding_deposits DECIMAL DEFAULT 0,
                outstanding_checks DECIMAL DEFAULT 0,
                is_balanced BOOLEAN DEFAULT FALSE,
                reconciled_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (bank_account_id) REFERENCES bank_accounts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def import_bank_statement(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import bank statement data"""
        try:
            bank_account_id = import_data['bank_account_id']
            statement_data = import_data['statement_data']
            format_type = import_data.get('format', 'csv')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            imported_count = 0
            duplicate_count = 0
            
            if format_type == 'csv':
                transactions = self._parse_csv_statement(statement_data)
            else:
                transactions = statement_data.get('transactions', [])
            
            for txn in transactions:
                # Check for duplicates
                cursor.execute('''
                    SELECT id FROM bank_transactions 
                    WHERE bank_account_id = ? AND transaction_date = ? 
                      AND amount = ? AND description = ?
                ''', (
                    bank_account_id, txn['date'], 
                    float(Decimal(str(txn['amount']))),
                    txn['description']
                ))
                
                if cursor.fetchone():
                    duplicate_count += 1
                    continue
                
                # Insert new transaction
                txn_id = f"BTXN_{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute('''
                    INSERT INTO bank_transactions (
                        id, bank_account_id, transaction_date, description, amount,
                        type, check_number, reference, data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    txn_id, bank_account_id, txn['date'], txn['description'],
                    float(Decimal(str(txn['amount']))), txn.get('type', 'DEBIT'),
                    txn.get('check_number'), txn.get('reference'),
                    json.dumps(txn)
                ))
                
                imported_count += 1
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'imported_transactions': imported_count,
                'duplicate_transactions': duplicate_count,
                'bank_account_id': bank_account_id
            }
            
        except Exception as e:
            logger.error(f"Error importing bank statement: {e}")
            return {
                'success': False,
                'error': f"Bank statement import error: {str(e)}"
            }
    
    def _parse_csv_statement(self, csv_data: str) -> List[Dict[str, Any]]:
        """Parse CSV bank statement data"""
        transactions = []
        
        try:
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                # Common CSV formats mapping
                transaction = {
                    'date': row.get('Date') or row.get('Transaction Date'),
                    'description': row.get('Description') or row.get('Memo'),
                    'amount': Decimal(str(row.get('Amount') or row.get('Debit') or row.get('Credit') or 0)),
                    'type': 'DEBIT' if float(row.get('Amount', 0)) < 0 else 'CREDIT',
                    'check_number': row.get('Check Number'),
                    'reference': row.get('Reference') or row.get('Transaction ID')
                }
                
                transactions.append(transaction)
        
        except Exception as e:
            logger.error(f"Error parsing CSV statement: {e}")
            
        return transactions
    
    async def get_reconciliation_data(self, bank_account_id: str, statement_date: str) -> Dict[str, Any]:
        """Get data for bank reconciliation"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get bank account details
            cursor.execute('''
                SELECT ba.bank_name, ba.account_name, ba.account_number, ba.current_balance, ba.account_id
                FROM bank_accounts ba
                WHERE ba.id = ?
            ''', (bank_account_id,))
            
            account_row = cursor.fetchone()
            if not account_row:
                return {'success': False, 'error': 'Bank account not found'}
            
            bank_name, account_name, account_number, current_balance = account_row[:4]
            gl_account_id = account_row[4]
            
            # Get unreconciled bank transactions
            cursor.execute('''
                SELECT id, transaction_date, description, amount, type, check_number, reference
                FROM bank_transactions
                WHERE bank_account_id = ? AND transaction_date <= ? AND is_reconciled = FALSE
                ORDER BY transaction_date
            ''', (bank_account_id, statement_date))
            
            bank_transactions = []
            for row in cursor.fetchall():
                bank_transactions.append({
                    'id': row[0],
                    'date': row[1],
                    'description': row[2],
                    'amount': Decimal(str(row[3])),
                    'type': row[4],
                    'check_number': row[5],
                    'reference': row[6]
                })
            
            # Get unreconciled GL transactions
            cursor.execute('''
                SELECT gl.id, gl.transaction_date, gl.description, gl.debit_amount, gl.credit_amount,
                       je.entry_number, je.reference
                FROM general_ledger gl
                JOIN journal_entries je ON gl.journal_entry_id = je.id
                WHERE gl.account_id = ? AND gl.transaction_date <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM transaction_matches tm 
                      WHERE tm.gl_transaction_id = gl.id OR tm.journal_entry_id = je.id
                  )
                ORDER BY gl.transaction_date
            ''', (gl_account_id, statement_date))
            
            gl_transactions = []
            for row in cursor.fetchall():
                net_amount = Decimal(str(row[3])) - Decimal(str(row[4]))
                gl_transactions.append({
                    'id': row[0],
                    'date': row[1],
                    'description': row[2],
                    'amount': net_amount,
                    'entry_number': row[5],
                    'reference': row[6]
                })
            
            # Attempt automatic matching
            suggested_matches = await self._suggest_matches(bank_transactions, gl_transactions)
            
            conn.close()
            
            return {
                'success': True,
                'bank_account': {
                    'id': bank_account_id,
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'current_balance': Decimal(str(current_balance))
                },
                'statement_date': statement_date,
                'bank_transactions': bank_transactions,
                'gl_transactions': gl_transactions,
                'suggested_matches': suggested_matches
            }
            
        except Exception as e:
            logger.error(f"Error getting reconciliation data: {e}")
            return {
                'success': False,
                'error': f"Reconciliation data error: {str(e)}"
            }
    
    async def _suggest_matches(self, bank_txns: List[Dict], gl_txns: List[Dict]) -> List[Dict[str, Any]]:
        """Suggest transaction matches using various criteria"""
        suggestions = []
        
        for bank_txn in bank_txns:
            best_match = None
            best_score = 0
            
            for gl_txn in gl_txns:
                score = self._calculate_match_score(bank_txn, gl_txn)
                
                if score > best_score and score >= 60:  # Minimum confidence threshold
                    best_score = score
                    best_match = gl_txn
            
            if best_match:
                suggestions.append({
                    'bank_transaction_id': bank_txn['id'],
                    'gl_transaction_id': best_match['id'],
                    'confidence': best_score,
                    'match_reasons': self._get_match_reasons(bank_txn, best_match)
                })
        
        return suggestions
    
    def _calculate_match_score(self, bank_txn: Dict, gl_txn: Dict) -> float:
        """Calculate match score between bank and GL transactions"""
        score = 0
        
        # Exact amount match
        if abs(bank_txn['amount'] - gl_txn['amount']) <= self.precision:
            score += self.matching_weights['exact_amount']
        
        # Date proximity (within 3 days)
        bank_date = datetime.strptime(bank_txn['date'], '%Y-%m-%d').date()
        gl_date = datetime.strptime(gl_txn['date'], '%Y-%m-%d').date()
        date_diff = abs((bank_date - gl_date).days)
        
        if date_diff == 0:
            score += self.matching_weights['date_proximity']
        elif date_diff <= 3:
            score += self.matching_weights['date_proximity'] * (1 - date_diff / 3)
        
        # Reference/check number match
        bank_ref = (bank_txn.get('check_number') or bank_txn.get('reference') or '').lower()
        gl_ref = (gl_txn.get('reference') or '').lower()
        
        if bank_ref and gl_ref and (bank_ref in gl_ref or gl_ref in bank_ref):
            score += self.matching_weights['reference_match']
        
        # Description similarity (simple keyword matching)
        bank_desc = bank_txn['description'].lower()
        gl_desc = gl_txn['description'].lower()
        
        # Extract keywords (ignore common words)
        common_words = {'the', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        
        bank_words = set(word for word in bank_desc.split() if len(word) > 2 and word not in common_words)
        gl_words = set(word for word in gl_desc.split() if len(word) > 2 and word not in common_words)
        
        if bank_words and gl_words:
            intersection = len(bank_words.intersection(gl_words))
            union = len(bank_words.union(gl_words))
            similarity = intersection / union if union > 0 else 0
            score += self.matching_weights['description_similarity'] * similarity
        
        return score
    
    def _get_match_reasons(self, bank_txn: Dict, gl_txn: Dict) -> List[str]:
        """Get list of reasons why transactions match"""
        reasons = []
        
        if abs(bank_txn['amount'] - gl_txn['amount']) <= self.precision:
            reasons.append("Exact amount match")
        
        bank_date = datetime.strptime(bank_txn['date'], '%Y-%m-%d').date()
        gl_date = datetime.strptime(gl_txn['date'], '%Y-%m-%d').date()
        date_diff = abs((bank_date - gl_date).days)
        
        if date_diff == 0:
            reasons.append("Same date")
        elif date_diff <= 3:
            reasons.append(f"Date within {date_diff} days")
        
        return reasons
    
    async def reconcile_transactions(self, bank_account_id: str, reconciliation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reconcile bank transactions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            matches = reconciliation_data.get('matches', [])
            statement_date = reconciliation_data['statement_date']
            ending_balance = Decimal(str(reconciliation_data['ending_balance']))
            
            reconciliation_id = f"REC_{uuid.uuid4().hex[:8].upper()}"
            matched_count = 0
            
            # Process matches
            for match in matches:
                match_id = f"MATCH_{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute('''
                    INSERT INTO transaction_matches (
                        id, bank_transaction_id, gl_transaction_id, journal_entry_id,
                        match_confidence, match_reason, matched_by, is_manual
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    match_id, match['bank_transaction_id'], 
                    match.get('gl_transaction_id'), match.get('journal_entry_id'),
                    match.get('confidence', 100), match.get('reason', 'Manual match'),
                    reconciliation_data.get('reconciled_by', 'USER'), match.get('is_manual', True)
                ))
                
                # Mark bank transaction as reconciled
                cursor.execute('''
                    UPDATE bank_transactions 
                    SET is_reconciled = TRUE, reconciled_date = ?
                    WHERE id = ?
                ''', (statement_date, match['bank_transaction_id']))
                
                matched_count += 1
            
            # Calculate reconciliation summary
            # Get book balance
            cursor.execute('''
                SELECT account_id FROM bank_accounts WHERE id = ?
            ''', (bank_account_id,))
            gl_account_id = cursor.fetchone()[0]
            
            from bookkeeping_engine import double_entry_system
            balance_result = await double_entry_system.calculate_account_balance(
                gl_account_id, datetime.strptime(statement_date, '%Y-%m-%d').date()
            )
            
            book_balance = balance_result.get('balance', Decimal('0'))
            
            # Calculate outstanding items
            cursor.execute('''
                SELECT SUM(amount) FROM bank_transactions 
                WHERE bank_account_id = ? AND is_reconciled = FALSE AND amount > 0
            ''', (bank_account_id,))
            outstanding_deposits = Decimal(str(cursor.fetchone()[0] or 0))
            
            cursor.execute('''
                SELECT SUM(ABS(amount)) FROM bank_transactions 
                WHERE bank_account_id = ? AND is_reconciled = FALSE AND amount < 0
            ''', (bank_account_id,))
            outstanding_checks = Decimal(str(cursor.fetchone()[0] or 0))
            
            reconciled_balance = book_balance + outstanding_deposits - outstanding_checks
            is_balanced = abs(reconciled_balance - ending_balance) <= self.precision
            
            # Create reconciliation record
            cursor.execute('''
                INSERT INTO bank_reconciliations (
                    id, bank_account_id, statement_date, ending_balance, book_balance,
                    reconciled_balance, outstanding_deposits, outstanding_checks,
                    is_balanced, reconciled_by, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reconciliation_id, bank_account_id, statement_date,
                float(ending_balance), float(book_balance), float(reconciled_balance),
                float(outstanding_deposits), float(outstanding_checks),
                is_balanced, reconciliation_data.get('reconciled_by', 'USER'),
                json.dumps(reconciliation_data)
            ))
            
            # Update bank account
            cursor.execute('''
                UPDATE bank_accounts 
                SET last_reconciled_date = ?, last_reconciled_balance = ?
                WHERE id = ?
            ''', (statement_date, float(ending_balance), bank_account_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'reconciliation_id': reconciliation_id,
                'matched_transactions': matched_count,
                'ending_balance': ending_balance,
                'book_balance': book_balance,
                'reconciled_balance': reconciled_balance,
                'outstanding_deposits': outstanding_deposits,
                'outstanding_checks': outstanding_checks,
                'is_balanced': is_balanced,
                'difference': reconciled_balance - ending_balance
            }
            
        except Exception as e:
            logger.error(f"Error reconciling transactions: {e}")
            return {
                'success': False,
                'error': f"Reconciliation error: {str(e)}"
            }

# Global instance
reconciliation_system = BankReconciliationSystem()