#!/usr/bin/env python3
"""
Audit Trail System
Comprehensive transaction logging, user activity monitoring, and compliance tracking
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import uuid
import hashlib

logger = logging.getLogger(__name__)

class AuditTrailSystem:
    """Comprehensive audit trail and compliance system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        
    async def initialize(self):
        """Initialize audit trail system"""
        try:
            await self._setup_audit_tables()
            logger.info("Audit trail system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize audit trail system: {e}")
            raise
    
    async def _setup_audit_tables(self):
        """Setup audit-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                login_time TIMESTAMP NOT NULL,
                logout_time TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                session_duration INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # System events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                affected_records TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def log_transaction(
        self, 
        table_name: str, 
        record_id: str, 
        action: str,
        user_id: str,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log transaction to audit trail"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            audit_id = f"AUDIT_{uuid.uuid4().hex[:8].upper()}"
            
            cursor.execute('''
                INSERT INTO audit_trail (
                    id, table_name, record_id, action, old_values, new_values,
                    user_id, ip_address, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                audit_id, table_name, record_id, action,
                json.dumps(old_values) if old_values else None,
                json.dumps(new_values) if new_values else None,
                user_id, ip_address, json.dumps({
                    'audit_id': audit_id,
                    'timestamp': datetime.now().isoformat(),
                    'action_details': f"{action} on {table_name}"
                })
            ))
            
            conn.commit()
            conn.close()
            
            return audit_id
            
        except Exception as e:
            logger.error(f"Error logging transaction: {e}")
            return ""
    
    async def get_audit_trail(
        self, 
        record_id: Optional[str] = None,
        table_name: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get audit trail records"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_conditions = []
            params = []
            
            if record_id:
                where_conditions.append("record_id = ?")
                params.append(record_id)
            
            if table_name:
                where_conditions.append("table_name = ?")
                params.append(table_name)
            
            if user_id:
                where_conditions.append("user_id = ?")
                params.append(user_id)
            
            if start_date:
                where_conditions.append("timestamp >= ?")
                params.append(start_date)
            
            if end_date:
                where_conditions.append("timestamp <= ?")
                params.append(end_date)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            cursor.execute(f'''
                SELECT 
                    id, table_name, record_id, action, old_values, new_values,
                    user_id, timestamp, ip_address
                FROM audit_trail
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            ''', params + [limit])
            
            audit_records = []
            for row in cursor.fetchall():
                audit_records.append({
                    'id': row[0],
                    'table_name': row[1],
                    'record_id': row[2],
                    'action': row[3],
                    'old_values': json.loads(row[4]) if row[4] else None,
                    'new_values': json.loads(row[5]) if row[5] else None,
                    'user_id': row[6],
                    'timestamp': row[7],
                    'ip_address': row[8]
                })
            
            conn.close()
            
            return {
                'success': True,
                'audit_records': audit_records,
                'record_count': len(audit_records)
            }
            
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return {
                'success': False,
                'error': f"Audit trail error: {str(e)}"
            }
    
    async def get_activity_log(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get user activity log"""
        try:
            if start_date is None:
                start_date = (date.today() - timedelta(days=30)).isoformat()
            if end_date is None:
                end_date = date.today().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_conditions = ["timestamp BETWEEN ? AND ?"]
            params = [start_date, end_date]
            
            if user_id:
                where_conditions.append("user_id = ?")
                params.append(user_id)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get activity summary
            cursor.execute(f'''
                SELECT 
                    user_id,
                    COUNT(*) as activity_count,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity,
                    COUNT(DISTINCT table_name) as tables_accessed
                FROM audit_trail
                WHERE {where_clause}
                GROUP BY user_id
                ORDER BY activity_count DESC
                LIMIT ?
            ''', params + [limit])
            
            activity_summary = []
            for row in cursor.fetchall():
                activity_summary.append({
                    'user_id': row[0],
                    'activity_count': row[1],
                    'first_activity': row[2],
                    'last_activity': row[3],
                    'tables_accessed': row[4]
                })
            
            # Get recent activities
            cursor.execute(f'''
                SELECT 
                    user_id, table_name, action, timestamp, record_id
                FROM audit_trail
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ?
            ''', params + [50])
            
            recent_activities = []
            for row in cursor.fetchall():
                recent_activities.append({
                    'user_id': row[0],
                    'table_name': row[1],
                    'action': row[2],
                    'timestamp': row[3],
                    'record_id': row[4]
                })
            
            conn.close()
            
            return {
                'success': True,
                'period': {'start_date': start_date, 'end_date': end_date},
                'activity_summary': activity_summary,
                'recent_activities': recent_activities
            }
            
        except Exception as e:
            logger.error(f"Error getting activity log: {e}")
            return {
                'success': False,
                'error': f"Activity log error: {str(e)}"
            }

# Global instance
audit_system = AuditTrailSystem()