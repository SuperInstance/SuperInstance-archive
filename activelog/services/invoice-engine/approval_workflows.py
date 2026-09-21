#!/usr/bin/env python3
"""
Invoice Approval Workflows System
Multi-step approval processes for invoice authorization
"""

import json
import sqlite3
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

class ApprovalWorkflowSystem:
    """Invoice approval workflow management system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
    
    async def initialize(self):
        """Initialize approval workflow system"""
        try:
            await self._setup_approval_tables()
            await self._create_default_workflows()
            logger.info("Approval workflow system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize approval workflow system: {e}")
            raise
    
    async def _setup_approval_tables(self):
        """Setup approval workflow tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_workflows (
                id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                workflow_steps TEXT NOT NULL,
                conditions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_approvals (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                current_step INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                submitted_by TEXT NOT NULL,
                submitted_date DATE NOT NULL,
                completed_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (workflow_id) REFERENCES approval_workflows (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_actions (
                id TEXT PRIMARY KEY,
                approval_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                approver_id TEXT NOT NULL,
                action TEXT NOT NULL,
                comments TEXT,
                action_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (approval_id) REFERENCES invoice_approvals (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _create_default_workflows(self):
        """Create default approval workflows"""
        default_workflows = [
            {
                'workflow_name': 'Simple Approval',
                'description': 'Single-step approval process',
                'workflow_steps': [
                    {'step': 1, 'role': 'manager', 'required': True}
                ],
                'conditions': {'amount_threshold': 1000}
            },
            {
                'workflow_name': 'Two-Step Approval',
                'description': 'Manager and director approval',
                'workflow_steps': [
                    {'step': 1, 'role': 'manager', 'required': True},
                    {'step': 2, 'role': 'director', 'required': True}
                ],
                'conditions': {'amount_threshold': 5000}
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for workflow in default_workflows:
            workflow_id = f"WF_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT OR IGNORE INTO approval_workflows (
                    id, workflow_name, description, workflow_steps, conditions
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                workflow_id, workflow['workflow_name'], workflow['description'],
                json.dumps(workflow['workflow_steps']), json.dumps(workflow['conditions'])
            ))
        
        conn.commit()
        conn.close()
    
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom approval workflow"""
        try:
            workflow_id = f"WF_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO approval_workflows (
                    id, workflow_name, description, workflow_steps, conditions, data
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                workflow_id, workflow_data['workflow_name'],
                workflow_data.get('description'), json.dumps(workflow_data['workflow_steps']),
                json.dumps(workflow_data.get('conditions', {})), json.dumps(workflow_data)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'workflow_id': workflow_id,
                'workflow_name': workflow_data['workflow_name']
            }
            
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            return {
                'success': False,
                'error': f"Workflow creation error: {str(e)}"
            }
    
    async def submit_for_approval(self, invoice_id: str, submitted_by: str = 'USER') -> Dict[str, Any]:
        """Submit invoice for approval"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get invoice details for workflow selection
            cursor.execute('SELECT total_amount FROM invoices WHERE id = ?', (invoice_id,))
            invoice_row = cursor.fetchone()
            if not invoice_row:
                conn.close()
                return {'success': False, 'error': 'Invoice not found'}
            
            total_amount = float(invoice_row[0])
            
            # Select appropriate workflow
            workflow_id = await self._select_workflow(cursor, total_amount)
            if not workflow_id:
                conn.close()
                return {'success': False, 'error': 'No suitable workflow found'}
            
            # Create approval record
            approval_id = f"APP_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO invoice_approvals (
                    id, invoice_id, workflow_id, submitted_by, submitted_date
                ) VALUES (?, ?, ?, ?, ?)
            ''', (approval_id, invoice_id, workflow_id, submitted_by, date.today().isoformat()))
            
            # Update invoice status
            cursor.execute('''
                UPDATE invoices SET status = 'pending_approval' WHERE id = ?
            ''', (invoice_id,))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'approval_id': approval_id,
                'workflow_id': workflow_id,
                'status': ApprovalStatus.PENDING.value
            }
            
        except Exception as e:
            logger.error(f"Error submitting for approval: {e}")
            return {'success': False, 'error': f"Submission error: {str(e)}"}
    
    async def _select_workflow(self, cursor, amount: float) -> Optional[str]:
        """Select appropriate workflow based on conditions"""
        cursor.execute('''
            SELECT id, conditions FROM approval_workflows
            WHERE is_active = TRUE ORDER BY id
        ''')
        
        for row in cursor.fetchall():
            workflow_id = row[0]
            conditions = json.loads(row[1] or '{}')
            
            threshold = conditions.get('amount_threshold', 0)
            if amount >= threshold:
                return workflow_id
        
        return None
    
    async def approve_invoice(self, approval_id: str, approval_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process approval action"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get approval details
            cursor.execute('''
                SELECT invoice_id, workflow_id, current_step, status
                FROM invoice_approvals WHERE id = ?
            ''', (approval_id,))
            
            approval_row = cursor.fetchone()
            if not approval_row:
                conn.close()
                return {'success': False, 'error': 'Approval not found'}
            
            invoice_id, workflow_id, current_step, status = approval_row
            
            if status != ApprovalStatus.PENDING.value:
                conn.close()
                return {'success': False, 'error': f'Approval already {status}'}
            
            action = approval_data['action']  # 'approve', 'reject', 'request_changes'
            approver_id = approval_data['approver_id']
            comments = approval_data.get('comments', '')
            
            # Record action
            action_id = f"ACT_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO approval_actions (
                    id, approval_id, step_number, approver_id, action, comments, action_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (action_id, approval_id, current_step, approver_id, action, 
                  comments, date.today().isoformat()))
            
            if action == 'reject':
                # Reject the invoice
                cursor.execute('''
                    UPDATE invoice_approvals SET status = ?, completed_date = ? WHERE id = ?
                ''', (ApprovalStatus.REJECTED.value, date.today().isoformat(), approval_id))
                
                cursor.execute('''
                    UPDATE invoices SET status = 'rejected' WHERE id = ?
                ''', (invoice_id,))
                
                final_status = ApprovalStatus.REJECTED.value
                
            elif action == 'approve':
                # Check if more steps needed
                cursor.execute('''
                    SELECT workflow_steps FROM approval_workflows WHERE id = ?
                ''', (workflow_id,))
                
                workflow_steps = json.loads(cursor.fetchone()[0])
                total_steps = len(workflow_steps)
                
                if current_step >= total_steps:
                    # Final approval
                    cursor.execute('''
                        UPDATE invoice_approvals SET status = ?, completed_date = ? WHERE id = ?
                    ''', (ApprovalStatus.APPROVED.value, date.today().isoformat(), approval_id))
                    
                    cursor.execute('''
                        UPDATE invoices SET status = 'approved' WHERE id = ?
                    ''', (invoice_id,))
                    
                    final_status = ApprovalStatus.APPROVED.value
                else:
                    # Move to next step
                    next_step = current_step + 1
                    cursor.execute('''
                        UPDATE invoice_approvals SET current_step = ? WHERE id = ?
                    ''', (next_step, approval_id))
                    
                    final_status = ApprovalStatus.PENDING.value
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'approval_id': approval_id,
                'action': action,
                'status': final_status
            }
            
        except Exception as e:
            logger.error(f"Error processing approval: {e}")
            return {'success': False, 'error': f"Approval error: {str(e)}"}
    
    async def list_pending_approvals(self, approver_id: Optional[str] = None) -> Dict[str, Any]:
        """List pending approvals"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT ia.id, ia.invoice_id, ia.workflow_id, ia.current_step,
                       ia.submitted_by, ia.submitted_date, i.total_amount, i.invoice_number
                FROM invoice_approvals ia
                JOIN invoices i ON ia.invoice_id = i.id
                WHERE ia.status = 'pending'
            '''
            
            params = []
            # In a real implementation, would filter by approver role/permissions
            
            base_query += " ORDER BY ia.submitted_date ASC"
            cursor.execute(base_query, params)
            
            pending_approvals = []
            for row in cursor.fetchall():
                pending_approvals.append({
                    'approval_id': row[0],
                    'invoice_id': row[1],
                    'workflow_id': row[2],
                    'current_step': row[3],
                    'submitted_by': row[4],
                    'submitted_date': row[5],
                    'invoice_amount': row[6],
                    'invoice_number': row[7]
                })
            
            conn.close()
            
            return {
                'success': True,
                'pending_approvals': pending_approvals,
                'count': len(pending_approvals)
            }
            
        except Exception as e:
            logger.error(f"Error listing pending approvals: {e}")
            return {'success': False, 'error': f"List error: {str(e)}"}

# Global instance
approval_system = ApprovalWorkflowSystem()