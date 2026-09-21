#!/usr/bin/env python3
"""
Collections Automation System
Automated collections processes and debtor management
"""

import json
import sqlite3
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class CollectionStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"
    WRITTEN_OFF = "written_off"
    LEGAL_ACTION = "legal_action"

class CollectionAction(str, Enum):
    EMAIL_NOTICE = "email_notice"
    PHONE_CALL = "phone_call"
    FORMAL_LETTER = "formal_letter"
    LEGAL_NOTICE = "legal_notice"
    ACCOUNT_SUSPENSION = "account_suspension"
    COLLECTION_AGENCY = "collection_agency"

class CollectionsAutomationSystem:
    """Collections automation and debtor management system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        
        # Collection escalation rules
        self.escalation_rules = [
            {'days_overdue': 30, 'action': CollectionAction.EMAIL_NOTICE, 'severity': 1},
            {'days_overdue': 45, 'action': CollectionAction.PHONE_CALL, 'severity': 2},
            {'days_overdue': 60, 'action': CollectionAction.FORMAL_LETTER, 'severity': 3},
            {'days_overdue': 90, 'action': CollectionAction.LEGAL_NOTICE, 'severity': 4},
            {'days_overdue': 120, 'action': CollectionAction.ACCOUNT_SUSPENSION, 'severity': 5},
            {'days_overdue': 180, 'action': CollectionAction.COLLECTION_AGENCY, 'severity': 6}
        ]
    
    async def initialize(self):
        """Initialize collections automation system"""
        try:
            await self._setup_collections_tables()
            await self._setup_default_workflows()
            logger.info("Collections automation system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize collections automation system: {e}")
            raise
    
    async def _setup_collections_tables(self):
        """Setup collections tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_cases (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                invoice_id TEXT,
                case_number TEXT UNIQUE NOT NULL,
                total_debt DECIMAL NOT NULL,
                remaining_debt DECIMAL NOT NULL,
                days_overdue INTEGER NOT NULL,
                priority_level INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                assigned_collector TEXT,
                created_date DATE NOT NULL,
                last_action_date DATE,
                next_action_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_actions (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_date DATE NOT NULL,
                description TEXT,
                outcome TEXT,
                follow_up_date DATE,
                collector_id TEXT,
                cost DECIMAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES collection_cases (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS collection_workflows (
                id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                trigger_conditions TEXT NOT NULL,
                action_sequence TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS debtor_profiles (
                id TEXT PRIMARY KEY,
                customer_id TEXT UNIQUE NOT NULL,
                risk_score INTEGER DEFAULT 50,
                payment_history TEXT,
                communication_preferences TEXT,
                payment_capacity DECIMAL,
                last_payment_date DATE,
                total_outstanding DECIMAL DEFAULT 0,
                collection_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def _setup_default_workflows(self):
        """Setup default collection workflows"""
        default_workflows = [
            {
                'workflow_name': 'Standard Collections',
                'trigger_conditions': {'days_overdue': 30, 'min_amount': 100},
                'action_sequence': [
                    {'action': 'email_notice', 'delay_days': 0},
                    {'action': 'phone_call', 'delay_days': 15},
                    {'action': 'formal_letter', 'delay_days': 15},
                    {'action': 'legal_notice', 'delay_days': 30}
                ]
            },
            {
                'workflow_name': 'High-Value Collections',
                'trigger_conditions': {'days_overdue': 15, 'min_amount': 5000},
                'action_sequence': [
                    {'action': 'phone_call', 'delay_days': 0},
                    {'action': 'formal_letter', 'delay_days': 7},
                    {'action': 'legal_notice', 'delay_days': 14},
                    {'action': 'collection_agency', 'delay_days': 30}
                ]
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for workflow in default_workflows:
            workflow_id = f"CWF_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT OR IGNORE INTO collection_workflows (
                    id, workflow_name, trigger_conditions, action_sequence
                ) VALUES (?, ?, ?, ?)
            ''', (
                workflow_id, workflow['workflow_name'],
                json.dumps(workflow['trigger_conditions']),
                json.dumps(workflow['action_sequence'])
            ))
        
        conn.commit()
        conn.close()
    
    async def create_collection_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create collection case"""
        try:
            case_id = f"CASE_{uuid.uuid4().hex[:8].upper()}"
            case_number = await self._generate_case_number()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Calculate days overdue if not provided
            days_overdue = case_data.get('days_overdue', 0)
            if case_data.get('invoice_id'):
                cursor.execute('SELECT due_date FROM invoices WHERE id = ?', (case_data['invoice_id'],))
                invoice_row = cursor.fetchone()
                if invoice_row and invoice_row[0]:
                    due_date = datetime.strptime(invoice_row[0], '%Y-%m-%d').date()
                    days_overdue = (date.today() - due_date).days
            
            cursor.execute('''
                INSERT INTO collection_cases (
                    id, customer_id, invoice_id, case_number, total_debt,
                    remaining_debt, days_overdue, priority_level, assigned_collector,
                    created_date, next_action_date, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                case_id, case_data['customer_id'], case_data.get('invoice_id'),
                case_number, case_data['total_debt'], case_data['total_debt'],
                days_overdue, case_data.get('priority_level', 1),
                case_data.get('assigned_collector'), date.today().isoformat(),
                date.today().isoformat(), json.dumps(case_data)
            ))
            
            # Create or update debtor profile
            await self._update_debtor_profile(cursor, case_data['customer_id'], case_data['total_debt'])
            
            conn.commit()
            conn.close()
            
            # Trigger automatic workflow
            await self._trigger_collection_workflow(case_id)
            
            return {
                'success': True,
                'case_id': case_id,
                'case_number': case_number,
                'days_overdue': days_overdue
            }
            
        except Exception as e:
            logger.error(f"Error creating collection case: {e}")
            return {
                'success': False,
                'error': f"Case creation error: {str(e)}"
            }
    
    async def _generate_case_number(self) -> str:
        """Generate unique case number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM collection_cases")
        count = cursor.fetchone()[0] + 1
        conn.close()
        return f"COLL-{date.today().strftime('%Y%m')}-{count:04d}"
    
    async def _update_debtor_profile(self, cursor, customer_id: str, additional_debt: float):
        """Update debtor profile"""
        cursor.execute('SELECT id, total_outstanding FROM debtor_profiles WHERE customer_id = ?', (customer_id,))
        profile = cursor.fetchone()
        
        if profile:
            new_outstanding = float(profile[1]) + additional_debt
            cursor.execute('''
                UPDATE debtor_profiles 
                SET total_outstanding = ?, updated_at = CURRENT_TIMESTAMP
                WHERE customer_id = ?
            ''', (new_outstanding, customer_id))
        else:
            profile_id = f"PROF_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO debtor_profiles (
                    id, customer_id, total_outstanding, payment_history
                ) VALUES (?, ?, ?, ?)
            ''', (profile_id, customer_id, additional_debt, json.dumps([])))
    
    async def _trigger_collection_workflow(self, case_id: str):
        """Trigger appropriate collection workflow"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get case details
        cursor.execute('''
            SELECT total_debt, days_overdue FROM collection_cases WHERE id = ?
        ''', (case_id,))
        
        case_row = cursor.fetchone()
        if not case_row:
            conn.close()
            return
        
        total_debt, days_overdue = case_row
        
        # Find matching workflow
        cursor.execute('''
            SELECT id, action_sequence FROM collection_workflows
            WHERE is_active = TRUE
        ''')
        
        for workflow_row in cursor.fetchall():
            workflow_id, action_sequence = workflow_row
            actions = json.loads(action_sequence)
            
            # Schedule first action
            if actions:
                first_action = actions[0]
                await self._schedule_collection_action(case_id, first_action['action'], 0)
                break
        
        conn.close()
    
    async def _schedule_collection_action(self, case_id: str, action_type: str, delay_days: int):
        """Schedule collection action"""
        action_date = date.today() + timedelta(days=delay_days)
        
        # In a real implementation, this would integrate with a task scheduler
        logger.info(f"Scheduled {action_type} for case {case_id} on {action_date}")
    
    async def record_collection_action(self, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record collection action taken"""
        try:
            action_id = f"ACT_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO collection_actions (
                    id, case_id, action_type, action_date, description,
                    outcome, follow_up_date, collector_id, cost
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                action_id, action_data['case_id'], action_data['action_type'],
                action_data.get('action_date', date.today().isoformat()),
                action_data.get('description'), action_data.get('outcome'),
                action_data.get('follow_up_date'), action_data.get('collector_id'),
                action_data.get('cost', 0)
            ))
            
            # Update case
            cursor.execute('''
                UPDATE collection_cases 
                SET last_action_date = ?, next_action_date = ?
                WHERE id = ?
            ''', (
                date.today().isoformat(), action_data.get('follow_up_date'),
                action_data['case_id']
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'action_id': action_id,
                'case_id': action_data['case_id']
            }
            
        except Exception as e:
            logger.error(f"Error recording collection action: {e}")
            return {'success': False, 'error': f"Action recording error: {str(e)}"}
    
    async def get_collection_queue(self, collector_id: Optional[str] = None) -> Dict[str, Any]:
        """Get collection action queue"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT cc.id, cc.case_number, cc.customer_id, cc.total_debt,
                       cc.remaining_debt, cc.days_overdue, cc.priority_level,
                       cc.next_action_date, cc.assigned_collector
                FROM collection_cases cc
                WHERE cc.status = 'active' AND cc.next_action_date <= ?
            '''
            
            params = [date.today().isoformat()]
            
            if collector_id:
                base_query += " AND cc.assigned_collector = ?"
                params.append(collector_id)
            
            base_query += " ORDER BY cc.priority_level DESC, cc.days_overdue DESC"
            cursor.execute(base_query, params)
            
            queue_items = []
            for row in cursor.fetchall():
                # Get recommended action
                recommended_action = self._get_recommended_action(row[5])  # days_overdue
                
                queue_items.append({
                    'case_id': row[0],
                    'case_number': row[1],
                    'customer_id': row[2],
                    'total_debt': Decimal(str(row[3])),
                    'remaining_debt': Decimal(str(row[4])),
                    'days_overdue': row[5],
                    'priority_level': row[6],
                    'next_action_date': row[7],
                    'assigned_collector': row[8],
                    'recommended_action': recommended_action
                })
            
            conn.close()
            
            return {
                'success': True,
                'queue_items': queue_items,
                'count': len(queue_items)
            }
            
        except Exception as e:
            logger.error(f"Error getting collection queue: {e}")
            return {'success': False, 'error': f"Queue error: {str(e)}"}
    
    def _get_recommended_action(self, days_overdue: int) -> str:
        """Get recommended action based on days overdue"""
        for rule in reversed(self.escalation_rules):
            if days_overdue >= rule['days_overdue']:
                return rule['action'].value
        return CollectionAction.EMAIL_NOTICE.value
    
    async def generate_collections_report(self, report_type: str = 'summary') -> Dict[str, Any]:
        """Generate collections performance report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if report_type == 'summary':
                # Overall summary
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_cases,
                        SUM(total_debt) as total_debt,
                        SUM(remaining_debt) as remaining_debt,
                        AVG(days_overdue) as avg_days_overdue
                    FROM collection_cases 
                    WHERE status = 'active'
                ''')
                
                summary_row = cursor.fetchone()
                
                # Status breakdown
                cursor.execute('''
                    SELECT status, COUNT(*), SUM(remaining_debt)
                    FROM collection_cases
                    GROUP BY status
                ''')
                
                status_breakdown = {}
                for row in cursor.fetchall():
                    status_breakdown[row[0]] = {
                        'count': row[1],
                        'total_debt': Decimal(str(row[2] or 0))
                    }
                
                # Recent actions
                cursor.execute('''
                    SELECT action_type, COUNT(*), AVG(cost)
                    FROM collection_actions
                    WHERE action_date >= ?
                    GROUP BY action_type
                ''', ((date.today() - timedelta(days=30)).isoformat(),))
                
                recent_actions = {}
                for row in cursor.fetchall():
                    recent_actions[row[0]] = {
                        'count': row[1],
                        'avg_cost': Decimal(str(row[2] or 0))
                    }
                
                conn.close()
                
                return {
                    'success': True,
                    'report_type': report_type,
                    'total_cases': summary_row[0] or 0,
                    'total_debt': Decimal(str(summary_row[1] or 0)),
                    'remaining_debt': Decimal(str(summary_row[2] or 0)),
                    'avg_days_overdue': round(summary_row[3] or 0, 1),
                    'status_breakdown': status_breakdown,
                    'recent_actions': recent_actions
                }
            
        except Exception as e:
            logger.error(f"Error generating collections report: {e}")
            return {'success': False, 'error': f"Report error: {str(e)}"}

# Global instance
collections_system = CollectionsAutomationSystem()