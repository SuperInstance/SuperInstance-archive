#!/usr/bin/env python3
"""
Bulk Invoicing System
Batch processing for large-scale invoice generation
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class BatchStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class BulkInvoicingSystem:
    """Bulk invoice processing system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
    
    async def initialize(self):
        """Initialize bulk invoicing system"""
        try:
            await self._setup_bulk_tables()
            logger.info("Bulk invoicing system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize bulk invoicing system: {e}")
            raise
    
    async def _setup_bulk_tables(self):
        """Setup bulk processing tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bulk_batches (
                id TEXT PRIMARY KEY,
                batch_name TEXT NOT NULL,
                total_records INTEGER NOT NULL,
                processed_records INTEGER DEFAULT 0,
                successful_records INTEGER DEFAULT 0,
                failed_records INTEGER DEFAULT 0,
                status TEXT DEFAULT 'queued',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bulk_items (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                invoice_data TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                invoice_id TEXT,
                error_message TEXT,
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES bulk_batches (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def process_bulk_invoices(self, bulk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process bulk invoice generation"""
        try:
            batch_id = f"BULK_{uuid.uuid4().hex[:8].upper()}"
            invoice_list = bulk_data['invoices']
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create batch record
            cursor.execute('''
                INSERT INTO bulk_batches (
                    id, batch_name, total_records, created_by, data
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                batch_id, bulk_data.get('batch_name', f'Batch {date.today()}'),
                len(invoice_list), bulk_data.get('created_by', 'SYSTEM'),
                json.dumps(bulk_data)
            ))
            
            # Insert individual items
            for invoice_data in invoice_list:
                item_id = f"ITEM_{uuid.uuid4().hex[:8].upper()}"
                cursor.execute('''
                    INSERT INTO bulk_items (id, batch_id, invoice_data)
                    VALUES (?, ?, ?)
                ''', (item_id, batch_id, json.dumps(invoice_data)))
            
            conn.commit()
            conn.close()
            
            # Process in background
            asyncio.create_task(self._process_batch(batch_id))
            
            return {
                'success': True,
                'batch_id': batch_id,
                'total_records': len(invoice_list),
                'status': BatchStatus.QUEUED.value
            }
            
        except Exception as e:
            logger.error(f"Error processing bulk invoices: {e}")
            return {
                'success': False,
                'error': f"Bulk processing error: {str(e)}"
            }
    
    async def _process_batch(self, batch_id: str):
        """Process individual batch"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Update batch status
            cursor.execute('''
                UPDATE bulk_batches 
                SET status = ?, started_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (BatchStatus.PROCESSING.value, batch_id))
            conn.commit()
            
            # Get batch items
            cursor.execute('''
                SELECT id, invoice_data FROM bulk_items
                WHERE batch_id = ? AND status = 'pending'
            ''', (batch_id,))
            
            items = cursor.fetchall()
            successful = 0
            failed = 0
            
            from invoice_templates import template_system
            
            for item_id, invoice_data_json in items:
                try:
                    invoice_data = json.loads(invoice_data_json)
                    
                    # Generate invoice
                    result = await template_system.generate_invoice(invoice_data)
                    
                    if result['success']:
                        # Update item as successful
                        cursor.execute('''
                            UPDATE bulk_items 
                            SET status = 'completed', invoice_id = ?, processed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (result['invoice_id'], item_id))
                        successful += 1
                    else:
                        # Update item as failed
                        cursor.execute('''
                            UPDATE bulk_items 
                            SET status = 'failed', error_message = ?, processed_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (result.get('error', 'Unknown error'), item_id))
                        failed += 1
                        
                except Exception as e:
                    cursor.execute('''
                        UPDATE bulk_items 
                        SET status = 'failed', error_message = ?, processed_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (str(e), item_id))
                    failed += 1
                
                # Update batch progress
                cursor.execute('''
                    UPDATE bulk_batches 
                    SET processed_records = processed_records + 1,
                        successful_records = ?, failed_records = ?
                    WHERE id = ?
                ''', (successful, failed, batch_id))
                conn.commit()
            
            # Final batch status
            total_processed = successful + failed
            if failed == 0:
                final_status = BatchStatus.COMPLETED.value
            elif successful == 0:
                final_status = BatchStatus.FAILED.value
            else:
                final_status = BatchStatus.PARTIAL.value
            
            cursor.execute('''
                UPDATE bulk_batches 
                SET status = ?, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (final_status, batch_id))
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}")
            cursor.execute('''
                UPDATE bulk_batches SET status = ? WHERE id = ?
            ''', (BatchStatus.FAILED.value, batch_id))
            conn.commit()
        finally:
            conn.close()
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """Get bulk batch processing status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT batch_name, total_records, processed_records,
                       successful_records, failed_records, status,
                       started_at, completed_at, created_by
                FROM bulk_batches WHERE id = ?
            ''', (batch_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return {'success': False, 'error': 'Batch not found'}
            
            # Get sample errors if any
            cursor.execute('''
                SELECT error_message FROM bulk_items
                WHERE batch_id = ? AND status = 'failed' AND error_message IS NOT NULL
                LIMIT 5
            ''', (batch_id,))
            
            sample_errors = [r[0] for r in cursor.fetchall()]
            
            conn.close()
            
            progress_percentage = (row[2] / row[1] * 100) if row[1] > 0 else 0
            
            return {
                'success': True,
                'batch_id': batch_id,
                'batch_name': row[0],
                'total_records': row[1],
                'processed_records': row[2],
                'successful_records': row[3],
                'failed_records': row[4],
                'status': row[5],
                'progress_percentage': round(progress_percentage, 2),
                'started_at': row[6],
                'completed_at': row[7],
                'created_by': row[8],
                'sample_errors': sample_errors
            }
            
        except Exception as e:
            logger.error(f"Error getting batch status: {e}")
            return {'success': False, 'error': f"Status error: {str(e)}"}

# Global instance
bulk_system = BulkInvoicingSystem()