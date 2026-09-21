#!/usr/bin/env python3
"""
Multi-Currency Support System
Exchange rate management, foreign currency transactions, and revaluation
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
import uuid

logger = logging.getLogger(__name__)

class CurrencySystem:
    """Multi-currency support system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.0001')  # 4 decimal places for exchange rates
        
        # Common currencies
        self.default_currencies = [
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
            {'code': 'CAD', 'name': 'Canadian Dollar', 'symbol': 'C$'},
            {'code': 'JPY', 'name': 'Japanese Yen', 'symbol': '¥'},
            {'code': 'CCC', 'name': 'Compound Currency Credits', 'symbol': '₵'}
        ]
    
    async def initialize(self):
        """Initialize currency system"""
        try:
            await self._setup_currency_tables()
            await self._setup_default_currencies()
            logger.info("Currency system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize currency system: {e}")
            raise
    
    async def _setup_currency_tables(self):
        """Setup currency-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Currencies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS currencies (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                decimal_places INTEGER DEFAULT 2,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Exchange rates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id TEXT PRIMARY KEY,
                from_currency TEXT NOT NULL,
                to_currency TEXT NOT NULL,
                rate DECIMAL NOT NULL,
                rate_date DATE NOT NULL,
                source TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (from_currency) REFERENCES currencies (code),
                FOREIGN KEY (to_currency) REFERENCES currencies (code)
            )
        ''')
        
        # Currency revaluations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS currency_revaluations (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                revaluation_date DATE NOT NULL,
                original_amount DECIMAL NOT NULL,
                revalued_amount DECIMAL NOT NULL,
                gain_loss DECIMAL NOT NULL,
                exchange_rate DECIMAL NOT NULL,
                journal_entry_id TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id),
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _setup_default_currencies(self):
        """Setup default currencies"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for currency in self.default_currencies:
            cursor.execute('''
                INSERT OR IGNORE INTO currencies (code, name, symbol)
                VALUES (?, ?, ?)
            ''', (currency['code'], currency['name'], currency['symbol']))
        
        conn.commit()
        conn.close()
    
    async def create_exchange_rate(self, rate_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update exchange rate"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            rate_id = f"XR_{uuid.uuid4().hex[:8].upper()}"
            
            # Deactivate existing rates for same currency pair and date
            cursor.execute('''
                UPDATE exchange_rates 
                SET is_active = FALSE
                WHERE from_currency = ? AND to_currency = ? AND rate_date = ?
            ''', (
                rate_data['from_currency'], 
                rate_data['to_currency'], 
                rate_data['rate_date']
            ))
            
            cursor.execute('''
                INSERT INTO exchange_rates (
                    id, from_currency, to_currency, rate, rate_date, source, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                rate_id, rate_data['from_currency'], rate_data['to_currency'],
                float(Decimal(str(rate_data['rate']))), rate_data['rate_date'],
                rate_data.get('source', 'MANUAL'), json.dumps(rate_data)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'rate_id': rate_id,
                'from_currency': rate_data['from_currency'],
                'to_currency': rate_data['to_currency'],
                'rate': Decimal(str(rate_data['rate']))
            }
            
        except Exception as e:
            logger.error(f"Error creating exchange rate: {e}")
            return {
                'success': False,
                'error': f"Exchange rate error: {str(e)}"
            }
    
    async def get_exchange_rate(
        self, 
        from_currency: str, 
        to_currency: str, 
        rate_date: Optional[str] = None
    ) -> Optional[Decimal]:
        """Get exchange rate for currency pair"""
        try:
            if from_currency == to_currency:
                return Decimal('1.0000')
            
            if rate_date is None:
                rate_date = date.today().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Try direct rate first
            cursor.execute('''
                SELECT rate FROM exchange_rates
                WHERE from_currency = ? AND to_currency = ? AND rate_date <= ?
                AND is_active = TRUE
                ORDER BY rate_date DESC
                LIMIT 1
            ''', (from_currency, to_currency, rate_date))
            
            rate_row = cursor.fetchone()
            if rate_row:
                conn.close()
                return Decimal(str(rate_row[0]))
            
            # Try inverse rate
            cursor.execute('''
                SELECT rate FROM exchange_rates
                WHERE from_currency = ? AND to_currency = ? AND rate_date <= ?
                AND is_active = TRUE
                ORDER BY rate_date DESC
                LIMIT 1
            ''', (to_currency, from_currency, rate_date))
            
            inverse_rate_row = cursor.fetchone()
            if inverse_rate_row:
                conn.close()
                return Decimal('1') / Decimal(str(inverse_rate_row[0]))
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            return None
    
    async def convert_currency(
        self, 
        amount: Decimal, 
        from_currency: str, 
        to_currency: str,
        rate_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert amount from one currency to another"""
        try:
            if from_currency == to_currency:
                return {
                    'success': True,
                    'original_amount': amount,
                    'converted_amount': amount,
                    'exchange_rate': Decimal('1.0000'),
                    'from_currency': from_currency,
                    'to_currency': to_currency
                }
            
            exchange_rate = await self.get_exchange_rate(from_currency, to_currency, rate_date)
            
            if exchange_rate is None:
                return {
                    'success': False,
                    'error': f"No exchange rate found for {from_currency} to {to_currency}"
                }
            
            converted_amount = amount * exchange_rate
            
            return {
                'success': True,
                'original_amount': amount,
                'converted_amount': converted_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'exchange_rate': exchange_rate,
                'from_currency': from_currency,
                'to_currency': to_currency,
                'rate_date': rate_date or date.today().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error converting currency: {e}")
            return {
                'success': False,
                'error': f"Currency conversion error: {str(e)}"
            }
    
    async def revalue_foreign_balances(
        self, 
        revaluation_date: Optional[str] = None,
        created_by: str = 'SYSTEM'
    ) -> Dict[str, Any]:
        """Revalue foreign currency balances at current rates"""
        try:
            if revaluation_date is None:
                revaluation_date = date.today().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get foreign currency accounts with balances
            cursor.execute('''
                SELECT DISTINCT coa.id, coa.account_name, coa.account_currency
                FROM chart_of_accounts coa
                WHERE coa.account_currency IS NOT NULL AND coa.account_currency != 'USD'
                AND coa.is_active = TRUE
            ''')
            
            revaluations = []
            total_gain_loss = Decimal('0')
            
            for row in cursor.fetchall():
                account_id, account_name, account_currency = row
                
                # Get current balance in foreign currency
                from bookkeeping_engine import double_entry_system
                balance_result = await double_entry_system.calculate_account_balance(
                    account_id, datetime.strptime(revaluation_date, '%Y-%m-%d').date()
                )
                
                original_amount = balance_result.get('balance', Decimal('0'))
                
                if abs(original_amount) > Decimal('0.01'):  # Only revalue significant balances
                    # Get current exchange rate
                    exchange_rate = await self.get_exchange_rate(
                        account_currency, 'USD', revaluation_date
                    )
                    
                    if exchange_rate:
                        revalued_amount = original_amount * exchange_rate
                        gain_loss = revalued_amount - original_amount
                        
                        # Record revaluation
                        revaluation_id = f"REV_{uuid.uuid4().hex[:8].upper()}"
                        
                        cursor.execute('''
                            INSERT INTO currency_revaluations (
                                id, account_id, revaluation_date, original_amount,
                                revalued_amount, gain_loss, exchange_rate, created_by, data
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            revaluation_id, account_id, revaluation_date,
                            float(original_amount), float(revalued_amount),
                            float(gain_loss), float(exchange_rate), created_by,
                            json.dumps({
                                'account_name': account_name,
                                'currency': account_currency
                            })
                        ))
                        
                        revaluations.append({
                            'account_id': account_id,
                            'account_name': account_name,
                            'original_amount': original_amount,
                            'revalued_amount': revalued_amount,
                            'gain_loss': gain_loss,
                            'currency': account_currency,
                            'exchange_rate': exchange_rate
                        })
                        
                        total_gain_loss += gain_loss
            
            # Create journal entry for net revaluation if significant
            journal_entry_id = None
            if abs(total_gain_loss) > Decimal('0.01'):
                journal_entry_id = await self._create_revaluation_journal_entry(
                    cursor, total_gain_loss, revaluation_date, created_by
                )
                
                # Update revaluation records with journal entry reference
                if journal_entry_id:
                    cursor.execute(
                        "UPDATE currency_revaluations SET journal_entry_id = ? WHERE created_by = ? AND revaluation_date = ?",
                        (journal_entry_id, created_by, revaluation_date)
                    )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'revaluation_date': revaluation_date,
                'revaluations': revaluations,
                'total_gain_loss': total_gain_loss,
                'journal_entry_id': journal_entry_id,
                'accounts_processed': len(revaluations)
            }
            
        except Exception as e:
            logger.error(f"Error revaluing foreign balances: {e}")
            return {
                'success': False,
                'error': f"Currency revaluation error: {str(e)}"
            }
    
    async def _create_revaluation_journal_entry(
        self, 
        cursor, 
        total_gain_loss: Decimal, 
        revaluation_date: str,
        created_by: str
    ) -> Optional[str]:
        """Create journal entry for currency revaluation"""
        try:
            from journal_entries import journal_system
            
            # Get unrealized gain/loss account (or create it)
            cursor.execute(
                "SELECT id FROM chart_of_accounts WHERE account_name LIKE '%Unrealized%Currency%' AND is_active = TRUE LIMIT 1"
            )
            
            gain_loss_account = cursor.fetchone()
            if not gain_loss_account:
                # Would create the account here in a real implementation
                return None
            
            gain_loss_account_id = gain_loss_account[0]
            
            # For simplification, we'll post to a general account
            # In reality, each foreign currency account would be adjusted individually
            
            if total_gain_loss > 0:  # Net gain
                lines = [
                    {
                        'account_id': gain_loss_account_id,
                        'description': 'Foreign Currency Revaluation - Unrealized Gain',
                        'debit_amount': 0,
                        'credit_amount': float(total_gain_loss)
                    }
                ]
            else:  # Net loss
                lines = [
                    {
                        'account_id': gain_loss_account_id,
                        'description': 'Foreign Currency Revaluation - Unrealized Loss',
                        'debit_amount': float(abs(total_gain_loss)),
                        'credit_amount': 0
                    }
                ]
            
            journal_entry_data = {
                'id': f"JE_{uuid.uuid4().hex[:8].upper()}",
                'transaction_date': revaluation_date,
                'description': f"Currency Revaluation - {revaluation_date}",
                'reference': 'CURRENCY_REVALUATION',
                'lines': lines,
                'created_by': created_by
            }
            
            result = await journal_system.create_entry(journal_entry_data)
            if result['success']:
                # Auto-approve and post
                await journal_system.approve_entry(result['journal_entry_id'], created_by)
                await journal_system.post_entry(result['journal_entry_id'], created_by)
                return result['journal_entry_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating revaluation journal entry: {e}")
            return None

# Global instance
currency_system = CurrencySystem()