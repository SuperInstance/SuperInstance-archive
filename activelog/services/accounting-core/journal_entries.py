#!/usr/bin/env python3
"""
Journal Entry System
Handles journal entry creation, validation, approval workflow, and batch processing
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
import hashlib

logger = logging.getLogger(__name__)

class JournalEntryStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"
    REJECTED = "rejected"

class EntryType(str, Enum):
    STANDARD = "standard"
    ADJUSTING = "adjusting"
    CLOSING = "closing"
    CORRECTING = "correcting"
    RECURRING = "recurring"
    REVERSING = "reversing"

class ApprovalLevel(str, Enum):
    NONE = "none"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    CONTROLLER = "controller"
    CFO = "cfo"

class JournalEntrySystem:
    """
    Comprehensive journal entry management system with approval workflows
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        
        # Approval thresholds (in USD)
        self.approval_thresholds = {
            ApprovalLevel.NONE: Decimal('1000'),
            ApprovalLevel.SUPERVISOR: Decimal('10000'),
            ApprovalLevel.MANAGER: Decimal('50000'),
            ApprovalLevel.CONTROLLER: Decimal('250000'),
            ApprovalLevel.CFO: Decimal('1000000')
        }
        
        # Recurring entry templates
        self.recurring_templates = {}
    
    async def initialize(self):
        """Initialize the journal entry system"""
        try:
            await self._setup_recurring_entry_tables()
            await self._load_recurring_templates()
            logger.info("Journal entry system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize journal entry system: {e}")
            raise
    
    async def _setup_recurring_entry_tables(self):
        """Setup recurring journal entry tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Recurring journal entry templates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_journal_templates (
                id TEXT PRIMARY KEY,
                template_name TEXT NOT NULL,
                description TEXT,
                entry_type TEXT DEFAULT 'recurring',
                frequency TEXT NOT NULL, -- monthly, quarterly, annually
                next_run_date DATE NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                template_data TEXT NOT NULL
            )
        ''')
        
        # Journal entry approvals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entry_approvals (
                id TEXT PRIMARY KEY,
                journal_entry_id TEXT NOT NULL,
                approver_id TEXT NOT NULL,
                approval_level TEXT NOT NULL,
                status TEXT DEFAULT 'pending', -- pending, approved, rejected
                comments TEXT,
                approved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
            )
        ''')
        
        # Journal entry batches
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entry_batches (
                id TEXT PRIMARY KEY,
                batch_name TEXT NOT NULL,
                batch_type TEXT DEFAULT 'standard',
                total_entries INTEGER DEFAULT 0,
                total_amount DECIMAL DEFAULT 0,
                status TEXT DEFAULT 'draft',
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                posted_at TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _load_recurring_templates(self):
        """Load recurring journal entry templates"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, template_name, template_data
            FROM recurring_journal_templates 
            WHERE is_active = TRUE
        ''')
        
        for row in cursor.fetchall():
            template_id, template_name, template_data = row
            self.recurring_templates[template_id] = {
                'name': template_name,
                'data': json.loads(template_data)
            }
        
        conn.close()
    
    async def create_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new journal entry
        
        Args:
            entry_data: Journal entry information including lines
            
        Returns:
            Entry creation result
        """
        try:
            # Import bookkeeping engine for validation
            from bookkeeping_engine import double_entry_system
            
            # Validate journal entry
            validation = await double_entry_system.validate_entry(entry_data.get('lines', []))
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors']
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate entry number if not provided
            entry_number = entry_data.get('entry_number', self._generate_entry_number())
            
            # Determine approval requirements
            total_amount = validation['total_debits']
            required_approval = self._determine_approval_level(total_amount)
            initial_status = JournalEntryStatus.PENDING_APPROVAL if required_approval != ApprovalLevel.NONE else JournalEntryStatus.APPROVED
            
            # Create journal entry record
            journal_entry = {
                'id': entry_data['id'],
                'entry_number': entry_number,
                'transaction_date': entry_data['transaction_date'],
                'description': entry_data['description'],
                'reference': entry_data.get('reference'),
                'lines': entry_data['lines'],
                'total_debits': validation['total_debits'],
                'total_credits': validation['total_credits'],
                'status': initial_status.value,
                'entry_type': entry_data.get('entry_type', EntryType.STANDARD.value),
                'created_by': entry_data['created_by'],
                'approved_by': None,
                'posted_by': None,
                'source_document': entry_data.get('source_document'),
                'batch_id': entry_data.get('batch_id'),
                'entity_id': entry_data.get('entity_id'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Insert journal entry
            cursor.execute('''
                INSERT INTO journal_entries (
                    id, entry_number, transaction_date, description, reference,
                    total_debits, total_credits, status, created_by, approved_by,
                    posted_by, source_document, batch_id, entity_id,
                    created_at, updated_at, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                journal_entry['id'], journal_entry['entry_number'],
                journal_entry['transaction_date'], journal_entry['description'],
                journal_entry['reference'], float(journal_entry['total_debits']),
                float(journal_entry['total_credits']), journal_entry['status'],
                journal_entry['created_by'], journal_entry['approved_by'],
                journal_entry['posted_by'], journal_entry['source_document'],
                journal_entry['batch_id'], journal_entry['entity_id'],
                journal_entry['created_at'], journal_entry['updated_at'],
                json.dumps(journal_entry)
            ))
            
            # Create approval record if needed
            if required_approval != ApprovalLevel.NONE:
                await self._create_approval_record(cursor, journal_entry['id'], required_approval)
            
            # Insert journal entry lines (not posted to GL yet)
            for i, line in enumerate(entry_data['lines']):
                line_id = f"JL_{uuid.uuid4().hex[:8].upper()}"
                
                cursor.execute('''
                    INSERT INTO journal_entry_lines (
                        id, journal_entry_id, account_id, line_number,
                        description, debit_amount, credit_amount,
                        currency, exchange_rate, reference, data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    line_id, journal_entry['id'], line['account_id'], i + 1,
                    line.get('description', ''), float(Decimal(str(line.get('debit_amount', 0)))),
                    float(Decimal(str(line.get('credit_amount', 0)))),
                    line.get('currency', 'USD'), line.get('exchange_rate', 1.0),
                    line.get('reference', ''), json.dumps(line)
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Created journal entry: {entry_number}")
            
            return {
                'success': True,
                'journal_entry_id': journal_entry['id'],
                'entry_number': entry_number,
                'status': initial_status.value,
                'total_debits': validation['total_debits'],
                'total_credits': validation['total_credits'],
                'requires_approval': required_approval != ApprovalLevel.NONE,
                'approval_level': required_approval.value
            }
            
        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return {
                'success': False,
                'errors': [f"Entry creation error: {str(e)}"]
            }
    
    def _generate_entry_number(self) -> str:
        """Generate unique journal entry number"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"JE{date_str}{random_str}"
    
    def _determine_approval_level(self, amount: Decimal) -> ApprovalLevel:
        """Determine required approval level based on amount"""
        if amount >= self.approval_thresholds[ApprovalLevel.CFO]:
            return ApprovalLevel.CFO
        elif amount >= self.approval_thresholds[ApprovalLevel.CONTROLLER]:
            return ApprovalLevel.CONTROLLER
        elif amount >= self.approval_thresholds[ApprovalLevel.MANAGER]:
            return ApprovalLevel.MANAGER
        elif amount >= self.approval_thresholds[ApprovalLevel.SUPERVISOR]:
            return ApprovalLevel.SUPERVISOR
        else:
            return ApprovalLevel.NONE
    
    async def _create_approval_record(
        self, 
        cursor, 
        journal_entry_id: str, 
        approval_level: ApprovalLevel
    ):
        """Create approval record for journal entry"""
        approval_id = f"APP_{uuid.uuid4().hex[:8].upper()}"
        
        cursor.execute('''
            INSERT INTO journal_entry_approvals (
                id, journal_entry_id, approver_id, approval_level,
                status, created_at, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            approval_id, journal_entry_id, 'PENDING_ASSIGNMENT',
            approval_level.value, 'pending', datetime.now().isoformat(),
            json.dumps({
                'approval_id': approval_id,
                'created_at': datetime.now().isoformat()
            })
        ))
    
    async def get_entries(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        entry_type: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get journal entries with filtering
        
        Args:
            start_date: Filter entries from this date
            end_date: Filter entries to this date
            status: Filter by status
            entry_type: Filter by entry type
            created_by: Filter by creator
            limit: Maximum number of entries to return
            
        Returns:
            Filtered journal entries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build query with filters
            where_conditions = []
            params = []
            
            if start_date:
                where_conditions.append("transaction_date >= ?")
                params.append(start_date)
            
            if end_date:
                where_conditions.append("transaction_date <= ?")
                params.append(end_date)
            
            if status:
                where_conditions.append("status = ?")
                params.append(status)
            
            if entry_type:
                where_conditions.append("JSON_EXTRACT(data, '$.entry_type') = ?")
                params.append(entry_type)
            
            if created_by:
                where_conditions.append("created_by = ?")
                params.append(created_by)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            # Get entries
            query = f'''
                SELECT 
                    id, entry_number, transaction_date, description, reference,
                    total_debits, total_credits, status, created_by, approved_by,
                    posted_by, source_document, batch_id, created_at, updated_at
                FROM journal_entries
                {where_clause}
                ORDER BY transaction_date DESC, created_at DESC
                LIMIT ?
            '''
            
            params.append(limit)
            cursor.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                entry = {
                    'id': row[0],
                    'entry_number': row[1],
                    'transaction_date': row[2],
                    'description': row[3],
                    'reference': row[4],
                    'total_debits': Decimal(str(row[5])),
                    'total_credits': Decimal(str(row[6])),
                    'status': row[7],
                    'created_by': row[8],
                    'approved_by': row[9],
                    'posted_by': row[10],
                    'source_document': row[11],
                    'batch_id': row[12],
                    'created_at': row[13],
                    'updated_at': row[14]
                }
                
                # Get entry lines
                cursor.execute('''
                    SELECT 
                        jel.account_id, jel.description, jel.debit_amount, jel.credit_amount,
                        coa.account_code, coa.account_name
                    FROM journal_entry_lines jel
                    JOIN chart_of_accounts coa ON jel.account_id = coa.id
                    WHERE jel.journal_entry_id = ?
                    ORDER BY jel.line_number
                ''', (entry['id'],))
                
                lines = []
                for line_row in cursor.fetchall():
                    lines.append({
                        'account_id': line_row[0],
                        'description': line_row[1],
                        'debit_amount': Decimal(str(line_row[2])),
                        'credit_amount': Decimal(str(line_row[3])),
                        'account_code': line_row[4],
                        'account_name': line_row[5]
                    })
                
                entry['lines'] = lines
                entries.append(entry)
            
            conn.close()
            
            return {
                'success': True,
                'entries': entries,
                'count': len(entries),
                'filters_applied': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'status': status,
                    'entry_type': entry_type,
                    'created_by': created_by
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting journal entries: {e}")
            return {
                'success': False,
                'error': f"Get entries error: {str(e)}"
            }
    
    async def get_entry_details(self, entry_id: str) -> Dict[str, Any]:
        """Get detailed journal entry information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get entry details
            cursor.execute('''
                SELECT 
                    id, entry_number, transaction_date, description, reference,
                    total_debits, total_credits, status, created_by, approved_by,
                    posted_by, source_document, batch_id, entity_id,
                    created_at, updated_at, data
                FROM journal_entries WHERE id = ?
            ''', (entry_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Journal entry {entry_id} not found"
                }
            
            entry = {
                'id': row[0],
                'entry_number': row[1],
                'transaction_date': row[2],
                'description': row[3],
                'reference': row[4],
                'total_debits': Decimal(str(row[5])),
                'total_credits': Decimal(str(row[6])),
                'status': row[7],
                'created_by': row[8],
                'approved_by': row[9],
                'posted_by': row[10],
                'source_document': row[11],
                'batch_id': row[12],
                'entity_id': row[13],
                'created_at': row[14],
                'updated_at': row[15]
            }
            
            # Get entry lines with account details
            cursor.execute('''
                SELECT 
                    jel.id, jel.account_id, jel.line_number, jel.description,
                    jel.debit_amount, jel.credit_amount, jel.currency, jel.exchange_rate,
                    coa.account_code, coa.account_name, coa.account_type
                FROM journal_entry_lines jel
                JOIN chart_of_accounts coa ON jel.account_id = coa.id
                WHERE jel.journal_entry_id = ?
                ORDER BY jel.line_number
            ''', (entry_id,))
            
            lines = []
            for line_row in cursor.fetchall():
                lines.append({
                    'id': line_row[0],
                    'account_id': line_row[1],
                    'line_number': line_row[2],
                    'description': line_row[3],
                    'debit_amount': Decimal(str(line_row[4])),
                    'credit_amount': Decimal(str(line_row[5])),
                    'currency': line_row[6],
                    'exchange_rate': Decimal(str(line_row[7])),
                    'account_code': line_row[8],
                    'account_name': line_row[9],
                    'account_type': line_row[10]
                })
            
            entry['lines'] = lines
            
            # Get approval history
            cursor.execute('''
                SELECT 
                    approver_id, approval_level, status, comments, approved_at, created_at
                FROM journal_entry_approvals
                WHERE journal_entry_id = ?
                ORDER BY created_at
            ''', (entry_id,))
            
            approvals = []
            for approval_row in cursor.fetchall():
                approvals.append({
                    'approver_id': approval_row[0],
                    'approval_level': approval_row[1],
                    'status': approval_row[2],
                    'comments': approval_row[3],
                    'approved_at': approval_row[4],
                    'created_at': approval_row[5]
                })
            
            entry['approvals'] = approvals
            
            conn.close()
            
            return {
                'success': True,
                'entry': entry
            }
            
        except Exception as e:
            logger.error(f"Error getting journal entry details: {e}")
            return {
                'success': False,
                'error': f"Entry details error: {str(e)}"
            }
    
    async def approve_entry(
        self, 
        entry_id: str, 
        approver_id: str, 
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve journal entry"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check entry exists and is pending approval
            cursor.execute(
                "SELECT status FROM journal_entries WHERE id = ?", 
                (entry_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Journal entry {entry_id} not found"
                }
            
            if row[0] != JournalEntryStatus.PENDING_APPROVAL.value:
                return {
                    'success': False,
                    'error': f"Entry is not pending approval (current status: {row[0]})"
                }
            
            # Update approval record
            cursor.execute('''
                UPDATE journal_entry_approvals
                SET approver_id = ?, status = 'approved', comments = ?, 
                    approved_at = ?
                WHERE journal_entry_id = ? AND status = 'pending'
            ''', (approver_id, comments, datetime.now().isoformat(), entry_id))
            
            # Update journal entry status
            cursor.execute('''
                UPDATE journal_entries
                SET status = ?, approved_by = ?, updated_at = ?
                WHERE id = ?
            ''', (
                JournalEntryStatus.APPROVED.value, approver_id, 
                datetime.now().isoformat(), entry_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Approved journal entry {entry_id} by {approver_id}")
            
            return {
                'success': True,
                'journal_entry_id': entry_id,
                'status': JournalEntryStatus.APPROVED.value,
                'approved_by': approver_id,
                'approved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error approving journal entry: {e}")
            return {
                'success': False,
                'error': f"Approval error: {str(e)}"
            }
    
    async def post_entry(self, entry_id: str, posted_by: str) -> Dict[str, Any]:
        """Post approved journal entry to general ledger"""
        try:
            # Import bookkeeping engine
            from bookkeeping_engine import double_entry_system
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get entry details
            cursor.execute('''
                SELECT transaction_date, status, data
                FROM journal_entries WHERE id = ?
            ''', (entry_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'success': False,
                    'error': f"Journal entry {entry_id} not found"
                }
            
            transaction_date_str, status, entry_data_json = row
            entry_data = json.loads(entry_data_json)
            
            if status != JournalEntryStatus.APPROVED.value:
                return {
                    'success': False,
                    'error': f"Entry must be approved before posting (current status: {status})"
                }
            
            # Get entry lines
            cursor.execute('''
                SELECT account_id, description, debit_amount, credit_amount, currency, exchange_rate
                FROM journal_entry_lines
                WHERE journal_entry_id = ?
                ORDER BY line_number
            ''', (entry_id,))
            
            lines = []
            for line_row in cursor.fetchall():
                lines.append({
                    'account_id': line_row[0],
                    'description': line_row[1],
                    'debit_amount': line_row[2],
                    'credit_amount': line_row[3],
                    'currency': line_row[4],
                    'exchange_rate': line_row[5]
                })
            
            conn.close()
            
            # Post to general ledger via bookkeeping engine
            transaction_date = datetime.strptime(transaction_date_str, "%Y-%m-%d").date()
            
            posting_result = await double_entry_system.record_transaction(
                entry_id, lines, transaction_date, posted_by
            )
            
            if not posting_result['success']:
                return posting_result
            
            # Update journal entry status
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE journal_entries
                SET status = ?, posted_by = ?, updated_at = ?
                WHERE id = ?
            ''', (
                JournalEntryStatus.POSTED.value, posted_by,
                datetime.now().isoformat(), entry_id
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Posted journal entry {entry_id} to general ledger")
            
            return {
                'success': True,
                'journal_entry_id': entry_id,
                'status': JournalEntryStatus.POSTED.value,
                'posted_by': posted_by,
                'posted_at': datetime.now().isoformat(),
                'balance_updates': posting_result['balance_updates']
            }
            
        except Exception as e:
            logger.error(f"Error posting journal entry: {e}")
            return {
                'success': False,
                'error': f"Posting error: {str(e)}"
            }
    
    async def reverse_entry(
        self, 
        entry_id: str, 
        reversal_reason: str, 
        reversed_by: str,
        reversal_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Create reversing journal entry"""
        try:
            if reversal_date is None:
                reversal_date = date.today()
            
            # Get original entry
            entry_details = await self.get_entry_details(entry_id)
            if not entry_details['success']:
                return entry_details
            
            original_entry = entry_details['entry']
            
            # Create reversing entry lines (swap debits and credits)
            reversing_lines = []
            for line in original_entry['lines']:
                reversing_lines.append({
                    'account_id': line['account_id'],
                    'description': f"REVERSAL: {line['description']}",
                    'debit_amount': float(line['credit_amount']),
                    'credit_amount': float(line['debit_amount']),
                    'currency': line['currency'],
                    'exchange_rate': float(line['exchange_rate'])
                })
            
            # Create reversing journal entry
            reversal_entry_data = {
                'id': f"REV_{uuid.uuid4().hex[:8].upper()}",
                'transaction_date': reversal_date.isoformat(),
                'description': f"REVERSAL of {original_entry['entry_number']}: {reversal_reason}",
                'reference': f"REV-{original_entry['entry_number']}",
                'lines': reversing_lines,
                'entry_type': EntryType.REVERSING.value,
                'created_by': reversed_by,
                'source_document': f"Reversal of {entry_id}"
            }
            
            # Create the reversing entry
            reversal_result = await self.create_entry(reversal_entry_data)
            
            if reversal_result['success']:
                # Auto-approve and post if original was posted
                if original_entry['status'] == JournalEntryStatus.POSTED.value:
                    await self.approve_entry(
                        reversal_result['journal_entry_id'],
                        reversed_by,
                        f"Auto-approved reversal entry"
                    )
                    await self.post_entry(reversal_result['journal_entry_id'], reversed_by)
                
                # Update original entry status
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE journal_entries
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                ''', (JournalEntryStatus.REVERSED.value, datetime.now().isoformat(), entry_id))
                
                conn.commit()
                conn.close()
            
            return reversal_result
            
        except Exception as e:
            logger.error(f"Error reversing journal entry: {e}")
            return {
                'success': False,
                'error': f"Reversal error: {str(e)}"
            }
    
    async def create_batch(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create batch of journal entries"""
        try:
            batch_id = f"BATCH_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create batch record
            cursor.execute('''
                INSERT INTO journal_entry_batches (
                    id, batch_name, batch_type, total_entries, total_amount,
                    status, created_by, created_at, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                batch_id, batch_data['batch_name'], batch_data.get('batch_type', 'standard'),
                0, 0, 'draft', batch_data['created_by'], datetime.now().isoformat(),
                json.dumps(batch_data)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'batch_id': batch_id,
                'batch_name': batch_data['batch_name'],
                'status': 'draft'
            }
            
        except Exception as e:
            logger.error(f"Error creating journal entry batch: {e}")
            return {
                'success': False,
                'error': f"Batch creation error: {str(e)}"
            }
    
    async def process_recurring_entries(self, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """Process recurring journal entries"""
        try:
            if as_of_date is None:
                as_of_date = date.today()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get due recurring templates
            cursor.execute('''
                SELECT id, template_name, template_data, frequency
                FROM recurring_journal_templates
                WHERE next_run_date <= ? AND is_active = TRUE
            ''', (as_of_date.isoformat(),))
            
            processed_entries = []
            
            for row in cursor.fetchall():
                template_id, template_name, template_data, frequency = row
                template = json.loads(template_data)
                
                # Create journal entry from template
                entry_data = {
                    'id': f"REC_{uuid.uuid4().hex[:8].upper()}",
                    'transaction_date': as_of_date.isoformat(),
                    'description': f"Recurring: {template_name} - {as_of_date}",
                    'lines': template['lines'],
                    'entry_type': EntryType.RECURRING.value,
                    'created_by': 'SYSTEM_RECURRING'
                }
                
                result = await self.create_entry(entry_data)
                if result['success']:
                    processed_entries.append(result)
                    
                    # Update next run date
                    next_run_date = self._calculate_next_run_date(as_of_date, frequency)
                    cursor.execute('''
                        UPDATE recurring_journal_templates
                        SET next_run_date = ?, updated_at = ?
                        WHERE id = ?
                    ''', (next_run_date.isoformat(), datetime.now().isoformat(), template_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'processed_count': len(processed_entries),
                'entries': processed_entries,
                'as_of_date': as_of_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing recurring entries: {e}")
            return {
                'success': False,
                'error': f"Recurring entries error: {str(e)}"
            }
    
    def _calculate_next_run_date(self, current_date: date, frequency: str) -> date:
        """Calculate next run date for recurring entry"""
        if frequency == 'monthly':
            # Next month, same day
            if current_date.month == 12:
                return current_date.replace(year=current_date.year + 1, month=1)
            else:
                return current_date.replace(month=current_date.month + 1)
        elif frequency == 'quarterly':
            return current_date + timedelta(days=90)
        elif frequency == 'annually':
            return current_date.replace(year=current_date.year + 1)
        else:
            # Default to monthly
            return current_date + timedelta(days=30)

# Global instance
journal_system = JournalEntrySystem()