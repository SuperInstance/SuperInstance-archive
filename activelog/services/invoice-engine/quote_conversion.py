#!/usr/bin/env python3
"""
Quote to Invoice Conversion System
Quote management and seamless conversion to invoices
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CONVERTED = "converted"

class QuoteSystem:
    """Quote management and conversion system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.precision = Decimal('0.01')
    
    async def initialize(self):
        """Initialize quote system"""
        try:
            await self._setup_quote_tables()
            logger.info("Quote conversion system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize quote system: {e}")
            raise
    
    async def _setup_quote_tables(self):
        """Setup quote-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Quotes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id TEXT PRIMARY KEY,
                quote_number TEXT UNIQUE NOT NULL,
                customer_id TEXT NOT NULL,
                template_id TEXT,
                quote_date DATE NOT NULL,
                valid_until DATE NOT NULL,
                status TEXT DEFAULT 'draft',
                subtotal DECIMAL NOT NULL,
                tax_amount DECIMAL DEFAULT 0,
                discount_amount DECIMAL DEFAULT 0,
                total_amount DECIMAL NOT NULL,
                items TEXT NOT NULL,
                terms TEXT,
                notes TEXT,
                converted_invoice_id TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Quote interactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quote_interactions (
                id TEXT PRIMARY KEY,
                quote_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                interaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_agent TEXT,
                ip_address TEXT,
                details TEXT,
                FOREIGN KEY (quote_id) REFERENCES quotes (id)
            )
        ''')
        
        # Quote versions table (for revisions)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quote_versions (
                id TEXT PRIMARY KEY,
                quote_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                items TEXT NOT NULL,
                total_amount DECIMAL NOT NULL,
                changes_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                FOREIGN KEY (quote_id) REFERENCES quotes (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new quote"""
        try:
            quote_id = f"QTE_{uuid.uuid4().hex[:8].upper()}"
            quote_number = await self._generate_quote_number()
            
            # Calculate totals
            items = quote_data['items']
            subtotal = sum(Decimal(str(item.get('total', 0))) for item in items)
            tax_amount = Decimal(str(quote_data.get('tax_amount', 0)))
            discount_amount = Decimal(str(quote_data.get('discount_amount', 0)))
            total_amount = subtotal + tax_amount - discount_amount
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO quotes (
                    id, quote_number, customer_id, template_id, quote_date,
                    valid_until, subtotal, tax_amount, discount_amount,
                    total_amount, items, terms, notes, metadata, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                quote_id, quote_number, quote_data['customer_id'],
                quote_data.get('template_id'), quote_data.get('quote_date', date.today().isoformat()),
                quote_data['valid_until'], float(subtotal), float(tax_amount),
                float(discount_amount), float(total_amount), json.dumps(items),
                quote_data.get('terms'), quote_data.get('notes'),
                json.dumps(quote_data.get('metadata', {})), json.dumps(quote_data)
            ))
            
            # Create initial version
            await self._create_quote_version(cursor, quote_id, items, total_amount, 'Initial version')
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'quote_id': quote_id,
                'quote_number': quote_number,
                'total_amount': total_amount,
                'status': QuoteStatus.DRAFT.value
            }
            
        except Exception as e:
            logger.error(f"Error creating quote: {e}")
            return {
                'success': False,
                'error': f"Quote creation error: {str(e)}"
            }
    
    async def _generate_quote_number(self) -> str:
        """Generate unique quote number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM quotes")
        count = cursor.fetchone()[0] + 1
        
        conn.close()
        
        return f"QTE-{date.today().strftime('%Y%m')}-{count:04d}"
    
    async def _create_quote_version(
        self, cursor, quote_id: str, items: List[Dict], 
        total_amount: Decimal, changes_summary: str, created_by: str = 'SYSTEM'
    ):
        """Create quote version"""
        cursor.execute('''
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM quote_versions WHERE quote_id = ?
        ''', (quote_id,))
        version_number = cursor.fetchone()[0]
        
        cursor.execute('''
            INSERT INTO quote_versions (
                id, quote_id, version_number, items, total_amount,
                changes_summary, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"QVER_{uuid.uuid4().hex[:8].upper()}",
            quote_id, version_number, json.dumps(items),
            float(total_amount), changes_summary, created_by
        ))
    
    async def convert_to_invoice(self, quote_id: str, conversion_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert quote to invoice"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get quote details
            cursor.execute('''
                SELECT quote_number, customer_id, template_id, items, total_amount,
                       terms, notes, status, metadata
                FROM quotes WHERE id = ?
            ''', (quote_id,))
            
            quote_row = cursor.fetchone()
            if not quote_row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Quote not found'
                }
            
            quote_number, customer_id, template_id, items_json = quote_row[:4]
            total_amount, terms, notes, status, metadata_json = quote_row[4:]
            
            if status == QuoteStatus.CONVERTED.value:
                conn.close()
                return {
                    'success': False,
                    'error': 'Quote already converted'
                }
            
            if status == QuoteStatus.EXPIRED.value:
                conn.close()
                return {
                    'success': False,
                    'error': 'Quote has expired'
                }
            
            # Parse data
            items = json.loads(items_json)
            metadata = json.loads(metadata_json or '{}')
            
            # Create invoice using template system
            from invoice_templates import template_system
            
            invoice_data = {
                'customer_id': customer_id,
                'template_id': template_id,
                'items': items,
                'invoice_date': conversion_data.get('invoice_date', date.today().isoformat()) if conversion_data else date.today().isoformat(),
                'due_date': conversion_data.get('due_date') if conversion_data else None,
                'terms': terms,
                'notes': notes,
                'metadata': {
                    **metadata,
                    'converted_from_quote': quote_id,
                    'quote_number': quote_number,
                    'conversion_date': datetime.now().isoformat()
                }
            }
            
            invoice_result = await template_system.generate_invoice(invoice_data)
            
            if invoice_result['success']:
                invoice_id = invoice_result['invoice_id']
                
                # Update quote status
                cursor.execute('''
                    UPDATE quotes 
                    SET status = ?, converted_invoice_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (QuoteStatus.CONVERTED.value, invoice_id, quote_id))
                
                # Record interaction
                await self._record_interaction(cursor, quote_id, 'converted', {
                    'invoice_id': invoice_id,
                    'conversion_date': datetime.now().isoformat()
                })
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'quote_id': quote_id,
                    'invoice_id': invoice_id,
                    'quote_number': quote_number,
                    'invoice_number': invoice_result.get('invoice_number'),
                    'total_amount': total_amount
                }
            else:
                conn.close()
                return invoice_result
                
        except Exception as e:
            logger.error(f"Error converting quote to invoice: {e}")
            return {
                'success': False,
                'error': f"Conversion error: {str(e)}"
            }
    
    async def update_quote_status(self, quote_id: str, status: str, details: Optional[Dict] = None) -> Dict[str, Any]:
        """Update quote status"""
        try:
            if status not in [s.value for s in QuoteStatus]:
                return {
                    'success': False,
                    'error': f"Invalid status: {status}"
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE quotes 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, quote_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    'success': False,
                    'error': 'Quote not found'
                }
            
            # Record interaction
            await self._record_interaction(cursor, quote_id, f'status_changed_to_{status}', details or {})
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'quote_id': quote_id,
                'new_status': status
            }
            
        except Exception as e:
            logger.error(f"Error updating quote status: {e}")
            return {
                'success': False,
                'error': f"Status update error: {str(e)}"
            }
    
    async def _record_interaction(self, cursor, quote_id: str, interaction_type: str, details: Dict):
        """Record quote interaction"""
        cursor.execute('''
            INSERT INTO quote_interactions (
                id, quote_id, interaction_type, details
            ) VALUES (?, ?, ?, ?)
        ''', (
            f"QINT_{uuid.uuid4().hex[:8].upper()}",
            quote_id, interaction_type, json.dumps(details)
        ))
    
    async def revise_quote(self, quote_id: str, revision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create quote revision"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current quote
            cursor.execute('''
                SELECT status, items FROM quotes WHERE id = ?
            ''', (quote_id,))
            
            quote_row = cursor.fetchone()
            if not quote_row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Quote not found'
                }
            
            current_status, current_items_json = quote_row
            
            if current_status == QuoteStatus.CONVERTED.value:
                conn.close()
                return {
                    'success': False,
                    'error': 'Cannot revise converted quote'
                }
            
            # Update quote with new items
            new_items = revision_data['items']
            subtotal = sum(Decimal(str(item.get('total', 0))) for item in new_items)
            tax_amount = Decimal(str(revision_data.get('tax_amount', 0)))
            discount_amount = Decimal(str(revision_data.get('discount_amount', 0)))
            total_amount = subtotal + tax_amount - discount_amount
            
            cursor.execute('''
                UPDATE quotes 
                SET items = ?, subtotal = ?, tax_amount = ?, 
                    discount_amount = ?, total_amount = ?, 
                    valid_until = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                json.dumps(new_items), float(subtotal), float(tax_amount),
                float(discount_amount), float(total_amount),
                revision_data.get('valid_until'), quote_id
            ))
            
            # Create new version
            await self._create_quote_version(
                cursor, quote_id, new_items, total_amount,
                revision_data.get('changes_summary', 'Quote revised'),
                revision_data.get('revised_by', 'USER')
            )
            
            # Record interaction
            await self._record_interaction(cursor, quote_id, 'revised', {
                'changes_summary': revision_data.get('changes_summary'),
                'new_total': float(total_amount)
            })
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'quote_id': quote_id,
                'new_total_amount': total_amount,
                'revision_date': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error revising quote: {e}")
            return {
                'success': False,
                'error': f"Revision error: {str(e)}"
            }
    
    async def list_quotes(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List quotes with filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT id, quote_number, customer_id, quote_date, valid_until,
                       status, total_amount, converted_invoice_id, created_at
                FROM quotes
                WHERE 1=1
            '''
            
            params = []
            
            if filters:
                if filters.get('customer_id'):
                    base_query += " AND customer_id = ?"
                    params.append(filters['customer_id'])
                
                if filters.get('status'):
                    base_query += " AND status = ?"
                    params.append(filters['status'])
                
                if filters.get('date_from'):
                    base_query += " AND quote_date >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    base_query += " AND quote_date <= ?"
                    params.append(filters['date_to'])
            
            base_query += " ORDER BY created_at DESC"
            
            if filters and filters.get('limit'):
                base_query += " LIMIT ?"
                params.append(filters['limit'])
            
            cursor.execute(base_query, params)
            
            quotes = []
            for row in cursor.fetchall():
                quotes.append({
                    'id': row[0],
                    'quote_number': row[1],
                    'customer_id': row[2],
                    'quote_date': row[3],
                    'valid_until': row[4],
                    'status': row[5],
                    'total_amount': Decimal(str(row[6])),
                    'converted_invoice_id': row[7],
                    'created_at': row[8],
                    'is_expired': datetime.strptime(row[4], '%Y-%m-%d').date() < date.today()
                })
            
            conn.close()
            
            return {
                'success': True,
                'quotes': quotes,
                'count': len(quotes)
            }
            
        except Exception as e:
            logger.error(f"Error listing quotes: {e}")
            return {
                'success': False,
                'error': f"List error: {str(e)}"
            }
    
    async def expire_old_quotes(self) -> Dict[str, Any]:
        """Expire quotes that have passed their valid_until date"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = date.today().isoformat()
            
            cursor.execute('''
                UPDATE quotes 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE valid_until < ? AND status NOT IN (?, ?, ?)
            ''', (
                QuoteStatus.EXPIRED.value, today,
                QuoteStatus.CONVERTED.value, QuoteStatus.EXPIRED.value, QuoteStatus.DECLINED.value
            ))
            
            expired_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'expired_count': expired_count,
                'expiration_date': today
            }
            
        except Exception as e:
            logger.error(f"Error expiring quotes: {e}")
            return {
                'success': False,
                'error': f"Expiration error: {str(e)}"
            }
    
    async def get_quote_analytics(self) -> Dict[str, Any]:
        """Get quote analytics and conversion rates"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_quotes,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as converted_quotes,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as expired_quotes,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as declined_quotes,
                    AVG(total_amount) as avg_quote_value,
                    SUM(total_amount) as total_quote_value
                FROM quotes
            ''', (QuoteStatus.CONVERTED.value, QuoteStatus.EXPIRED.value, QuoteStatus.DECLINED.value))
            
            stats_row = cursor.fetchone()
            total_quotes = stats_row[0]
            converted_quotes = stats_row[1]
            expired_quotes = stats_row[2]
            declined_quotes = stats_row[3]
            avg_quote_value = Decimal(str(stats_row[4] or 0))
            total_quote_value = Decimal(str(stats_row[5] or 0))
            
            conversion_rate = (converted_quotes / total_quotes * 100) if total_quotes > 0 else 0
            
            # Monthly trends
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', quote_date) as month,
                    COUNT(*) as quote_count,
                    SUM(CASE WHEN status = ? THEN 1 ELSE 0 END) as conversions,
                    AVG(total_amount) as avg_value
                FROM quotes
                WHERE quote_date >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', quote_date)
                ORDER BY month
            ''', (QuoteStatus.CONVERTED.value,))
            
            monthly_trends = []
            for row in cursor.fetchall():
                monthly_trends.append({
                    'month': row[0],
                    'quote_count': row[1],
                    'conversions': row[2],
                    'conversion_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0,
                    'avg_value': Decimal(str(row[3] or 0))
                })
            
            conn.close()
            
            return {
                'success': True,
                'analytics': {
                    'total_quotes': total_quotes,
                    'converted_quotes': converted_quotes,
                    'expired_quotes': expired_quotes,
                    'declined_quotes': declined_quotes,
                    'conversion_rate': round(conversion_rate, 2),
                    'avg_quote_value': avg_quote_value,
                    'total_quote_value': total_quote_value,
                    'monthly_trends': monthly_trends
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting quote analytics: {e}")
            return {
                'success': False,
                'error': f"Analytics error: {str(e)}"
            }

# Global instance
quote_system = QuoteSystem()