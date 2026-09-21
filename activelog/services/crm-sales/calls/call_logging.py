"""
Call Logging System
Comprehensive call tracking, logging, and analytics
"""

import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import uuid
from urllib.parse import urlparse


class CallType(Enum):
    """Call types"""
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    MISSED = "missed"
    VOICEMAIL = "voicemail"


class CallDisposition(Enum):
    """Call disposition/outcome"""
    CONNECTED = "connected"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    LEFT_MESSAGE = "left_message"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"
    CALLBACK_REQUESTED = "callback_requested"
    APPOINTMENT_SET = "appointment_set"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class CallSentiment(Enum):
    """Call sentiment analysis"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


@dataclass
class CallRecord:
    """Call record data structure"""
    call_id: str
    contact_id: str
    user_id: str
    phone_number: str
    call_type: CallType
    duration_seconds: int
    call_disposition: CallDisposition
    sentiment: Optional[CallSentiment]
    notes: str
    recording_url: Optional[str]
    transcription: Optional[str]
    created_at: datetime
    

class CallLoggingSystem:
    """Call logging and analytics system"""
    
    def __init__(self, db_path: str = "data/crm_sales.db"):
        self.db_path = db_path
        
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
        
    def log_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Log a new call"""
        
        call_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert call record
            cursor.execute("""
                INSERT INTO call_logs (
                    call_id, contact_id, user_id, phone_number, call_type,
                    duration_seconds, call_disposition, sentiment, notes,
                    recording_url, transcription, scheduled_at, started_at,
                    ended_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                call_id,
                call_data.get('contact_id'),
                call_data['user_id'],
                call_data['phone_number'],
                call_data['call_type'],
                call_data.get('duration_seconds', 0),
                call_data.get('call_disposition'),
                call_data.get('sentiment'),
                call_data.get('notes', ''),
                call_data.get('recording_url'),
                call_data.get('transcription'),
                call_data.get('scheduled_at'),
                call_data.get('started_at'),
                call_data.get('ended_at'),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            # Create activity record
            if call_data.get('contact_id'):
                self._create_activity(cursor, {
                    'contact_id': call_data['contact_id'],
                    'activity_type': 'call',
                    'description': f"{call_data['call_type'].title()} call - {call_data.get('call_disposition', 'N/A')}",
                    'metadata': {
                        'call_id': call_id,
                        'duration_seconds': call_data.get('duration_seconds', 0),
                        'phone_number': call_data['phone_number']
                    },
                    'user_id': call_data['user_id']
                })
            
            # Auto-create follow-up task if needed
            if call_data.get('call_disposition') == CallDisposition.CALLBACK_REQUESTED.value:
                self._create_callback_task(cursor, call_id, call_data)
            elif call_data.get('call_disposition') == CallDisposition.APPOINTMENT_SET.value:
                self._create_appointment_task(cursor, call_id, call_data)
            
            conn.commit()
            
            # Update contact last contact date
            if call_data.get('contact_id'):
                self._update_contact_last_contact(call_data['contact_id'])
            
            return {
                'call_id': call_id,
                'status': 'logged',
                'created_at': datetime.utcnow().isoformat()
            }
    
    def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get call record by ID"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT cl.*, c.first_name, c.last_name, c.company
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.contact_id
                WHERE cl.call_id = ?
            """, [call_id])
            
            result = cursor.fetchone()
            if result:
                return {
                    'call_id': result['call_id'],
                    'contact_id': result['contact_id'],
                    'contact_name': f"{result['first_name'] or ''} {result['last_name'] or ''}".strip(),
                    'company': result['company'],
                    'user_id': result['user_id'],
                    'phone_number': result['phone_number'],
                    'call_type': result['call_type'],
                    'duration_seconds': result['duration_seconds'],
                    'call_disposition': result['call_disposition'],
                    'sentiment': result['sentiment'],
                    'notes': result['notes'],
                    'recording_url': result['recording_url'],
                    'transcription': result['transcription'],
                    'scheduled_at': result['scheduled_at'],
                    'started_at': result['started_at'],
                    'ended_at': result['ended_at'],
                    'created_at': result['created_at']
                }
            return None
    
    def list_calls(self, contact_id: Optional[str] = None, user_id: Optional[str] = None,
                   call_type: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List call records with filters"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build query
            query = """
                SELECT cl.*, c.first_name, c.last_name, c.company
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.contact_id
                WHERE 1=1
            """
            params = []
            
            if contact_id:
                query += " AND cl.contact_id = ?"
                params.append(contact_id)
            if user_id:
                query += " AND cl.user_id = ?"
                params.append(user_id)
            if call_type:
                query += " AND cl.call_type = ?"
                params.append(call_type)
                
            query += " ORDER BY cl.created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            calls = []
            for result in results:
                calls.append({
                    'call_id': result['call_id'],
                    'contact_id': result['contact_id'],
                    'contact_name': f"{result['first_name'] or ''} {result['last_name'] or ''}".strip(),
                    'company': result['company'],
                    'user_id': result['user_id'],
                    'phone_number': result['phone_number'],
                    'call_type': result['call_type'],
                    'duration_seconds': result['duration_seconds'],
                    'call_disposition': result['call_disposition'],
                    'sentiment': result['sentiment'],
                    'notes': result['notes'][:100] + '...' if result['notes'] and len(result['notes']) > 100 else result['notes'],
                    'created_at': result['created_at']
                })
                
            return calls
    
    def update_call(self, call_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update call record"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query
            set_clauses = []
            params = []
            
            updatable_fields = [
                'call_disposition', 'sentiment', 'notes', 'recording_url', 
                'transcription', 'duration_seconds', 'ended_at'
            ]
            
            for field in updatable_fields:
                if field in updates:
                    set_clauses.append(f"{field} = ?")
                    params.append(updates[field])
            
            if not set_clauses:
                raise ValueError("No valid fields to update")
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(call_id)
            
            query = f"UPDATE call_logs SET {', '.join(set_clauses)} WHERE call_id = ?"
            cursor.execute(query, params)
            
            if cursor.rowcount == 0:
                raise ValueError("Call not found")
            
            conn.commit()
            
            return {
                'call_id': call_id,
                'status': 'updated',
                'updated_at': datetime.utcnow().isoformat()
            }
    
    def schedule_call(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a future call"""
        
        call_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert scheduled call
            cursor.execute("""
                INSERT INTO call_logs (
                    call_id, contact_id, user_id, phone_number, call_type,
                    call_disposition, notes, scheduled_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                call_id,
                call_data.get('contact_id'),
                call_data['user_id'],
                call_data['phone_number'],
                CallType.OUTBOUND.value,
                'scheduled',
                call_data.get('notes', ''),
                call_data['scheduled_at'],
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            # Create task
            task_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, title, description, due_date, priority,
                    assigned_to, contact_id, task_type, status,
                    metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                task_id,
                f"Call {call_data.get('contact_name', 'contact')}",
                f"Scheduled call - {call_data.get('notes', '')}",
                call_data['scheduled_at'],
                'medium',
                call_data['user_id'],
                call_data.get('contact_id'),
                'call',
                'pending',
                json.dumps({'call_id': call_id, 'phone_number': call_data['phone_number']}),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ])
            
            conn.commit()
            
            return {
                'call_id': call_id,
                'task_id': task_id,
                'status': 'scheduled',
                'scheduled_at': call_data['scheduled_at']
            }
    
    def get_call_analytics(self, user_id: Optional[str] = None, 
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """Get call analytics and metrics"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build date filter
            date_filter = ""
            params = []
            
            if start_date and end_date:
                date_filter = "AND cl.created_at BETWEEN ? AND ?"
                params.extend([start_date, end_date])
            elif start_date:
                date_filter = "AND cl.created_at >= ?"
                params.append(start_date)
            elif end_date:
                date_filter = "AND cl.created_at <= ?"
                params.append(end_date)
            
            # Build user filter
            user_filter = ""
            if user_id:
                user_filter = "AND cl.user_id = ?"
                params.append(user_id)
            
            # Basic call statistics
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(CASE WHEN call_type = 'outbound' THEN 1 END) as outbound_calls,
                    COUNT(CASE WHEN call_type = 'inbound' THEN 1 END) as inbound_calls,
                    COUNT(CASE WHEN call_type = 'missed' THEN 1 END) as missed_calls,
                    AVG(duration_seconds) as avg_duration,
                    SUM(duration_seconds) as total_duration,
                    COUNT(CASE WHEN call_disposition = 'connected' THEN 1 END) as connected_calls,
                    COUNT(CASE WHEN call_disposition = 'appointment_set' THEN 1 END) as appointments_set
                FROM call_logs cl
                WHERE 1=1 {date_filter} {user_filter}
            """, params)
            
            basic_stats = cursor.fetchone()
            
            # Call disposition breakdown
            cursor.execute(f"""
                SELECT call_disposition, COUNT(*) as count
                FROM call_logs cl
                WHERE call_disposition IS NOT NULL {date_filter} {user_filter}
                GROUP BY call_disposition
                ORDER BY count DESC
            """, params)
            
            disposition_breakdown = []
            for result in cursor.fetchall():
                disposition_breakdown.append({
                    'disposition': result['call_disposition'],
                    'count': result['count']
                })
            
            # Daily call volume
            cursor.execute(f"""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as call_count,
                    AVG(duration_seconds) as avg_duration
                FROM call_logs cl
                WHERE 1=1 {date_filter} {user_filter}
                GROUP BY DATE(created_at)
                ORDER BY date DESC
                LIMIT 30
            """, params)
            
            daily_volume = []
            for result in cursor.fetchall():
                daily_volume.append({
                    'date': result['date'],
                    'call_count': result['call_count'],
                    'avg_duration': result['avg_duration']
                })
            
            # Performance metrics
            total_calls = basic_stats['total_calls'] or 0
            connected_calls = basic_stats['connected_calls'] or 0
            connection_rate = (connected_calls / total_calls * 100) if total_calls > 0 else 0
            
            # Sentiment analysis
            cursor.execute(f"""
                SELECT sentiment, COUNT(*) as count
                FROM call_logs cl
                WHERE sentiment IS NOT NULL {date_filter} {user_filter}
                GROUP BY sentiment
            """, params)
            
            sentiment_breakdown = []
            for result in cursor.fetchall():
                sentiment_breakdown.append({
                    'sentiment': result['sentiment'],
                    'count': result['count']
                })
            
            return {
                'basic_stats': {
                    'total_calls': basic_stats['total_calls'] or 0,
                    'outbound_calls': basic_stats['outbound_calls'] or 0,
                    'inbound_calls': basic_stats['inbound_calls'] or 0,
                    'missed_calls': basic_stats['missed_calls'] or 0,
                    'avg_duration_seconds': basic_stats['avg_duration'] or 0,
                    'total_duration_seconds': basic_stats['total_duration'] or 0,
                    'connected_calls': basic_stats['connected_calls'] or 0,
                    'appointments_set': basic_stats['appointments_set'] or 0,
                    'connection_rate': connection_rate
                },
                'disposition_breakdown': disposition_breakdown,
                'sentiment_breakdown': sentiment_breakdown,
                'daily_volume': daily_volume,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_call_queue(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get scheduled calls queue"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT cl.*, c.first_name, c.last_name, c.company
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.contact_id
                WHERE cl.call_disposition = 'scheduled' 
                AND cl.scheduled_at IS NOT NULL
            """
            params = []
            
            if user_id:
                query += " AND cl.user_id = ?"
                params.append(user_id)
                
            query += " ORDER BY cl.scheduled_at ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            queue = []
            for result in results:
                queue.append({
                    'call_id': result['call_id'],
                    'contact_id': result['contact_id'],
                    'contact_name': f"{result['first_name'] or ''} {result['last_name'] or ''}".strip(),
                    'company': result['company'],
                    'phone_number': result['phone_number'],
                    'scheduled_at': result['scheduled_at'],
                    'notes': result['notes']
                })
                
            return queue
    
    def get_overdue_calls(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get overdue scheduled calls"""
        
        now = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT cl.*, c.first_name, c.last_name, c.company
                FROM call_logs cl
                LEFT JOIN contacts c ON cl.contact_id = c.contact_id
                WHERE cl.call_disposition = 'scheduled' 
                AND cl.scheduled_at < ?
            """
            params = [now]
            
            if user_id:
                query += " AND cl.user_id = ?"
                params.append(user_id)
                
            query += " ORDER BY cl.scheduled_at ASC"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            overdue = []
            for result in results:
                overdue.append({
                    'call_id': result['call_id'],
                    'contact_id': result['contact_id'],
                    'contact_name': f"{result['first_name'] or ''} {result['last_name'] or ''}".strip(),
                    'company': result['company'],
                    'phone_number': result['phone_number'],
                    'scheduled_at': result['scheduled_at'],
                    'notes': result['notes']
                })
                
            return overdue
    
    def import_call_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk import call records"""
        
        imported_count = 0
        errors = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for i, record in enumerate(records):
                try:
                    # Validate required fields
                    required_fields = ['user_id', 'phone_number', 'call_type']
                    for field in required_fields:
                        if field not in record:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # Import the record
                    self.log_call(record)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append({
                        'row': i + 1,
                        'error': str(e),
                        'record': record
                    })
        
        return {
            'imported_count': imported_count,
            'error_count': len(errors),
            'errors': errors
        }
    
    def analyze_call_performance(self, user_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Analyze individual user call performance"""
        
        start_date = (datetime.utcnow() - timedelta(days=period_days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get performance metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_calls,
                    COUNT(CASE WHEN call_disposition = 'connected' THEN 1 END) as connected_calls,
                    COUNT(CASE WHEN call_disposition = 'appointment_set' THEN 1 END) as appointments_set,
                    AVG(duration_seconds) as avg_duration,
                    COUNT(CASE WHEN call_type = 'outbound' THEN 1 END) as outbound_calls
                FROM call_logs
                WHERE user_id = ? AND created_at >= ?
            """, [user_id, start_date])
            
            metrics = cursor.fetchone()
            
            # Calculate rates
            total_calls = metrics['total_calls'] or 0
            connected_calls = metrics['connected_calls'] or 0
            appointments_set = metrics['appointments_set'] or 0
            outbound_calls = metrics['outbound_calls'] or 0
            
            connection_rate = (connected_calls / total_calls * 100) if total_calls > 0 else 0
            appointment_rate = (appointments_set / connected_calls * 100) if connected_calls > 0 else 0
            activity_score = min(100, (total_calls / period_days) * 10)  # Simplified scoring
            
            # Get daily breakdown
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as daily_calls,
                    COUNT(CASE WHEN call_disposition = 'connected' THEN 1 END) as daily_connected
                FROM call_logs
                WHERE user_id = ? AND created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date
            """, [user_id, start_date])
            
            daily_breakdown = []
            for result in cursor.fetchall():
                daily_breakdown.append({
                    'date': result['date'],
                    'calls': result['daily_calls'],
                    'connected': result['daily_connected']
                })
            
            return {
                'user_id': user_id,
                'period_days': period_days,
                'metrics': {
                    'total_calls': total_calls,
                    'connected_calls': connected_calls,
                    'appointments_set': appointments_set,
                    'outbound_calls': outbound_calls,
                    'avg_duration_seconds': metrics['avg_duration'] or 0,
                    'connection_rate': connection_rate,
                    'appointment_rate': appointment_rate,
                    'activity_score': activity_score
                },
                'daily_breakdown': daily_breakdown,
                'generated_at': datetime.utcnow().isoformat()
            }
    
    def get_call_transcription(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get call transcription and analysis"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT transcription, sentiment, notes
                FROM call_logs
                WHERE call_id = ?
            """, [call_id])
            
            result = cursor.fetchone()
            if result and result['transcription']:
                return {
                    'call_id': call_id,
                    'transcription': result['transcription'],
                    'sentiment': result['sentiment'],
                    'notes': result['notes'],
                    'word_count': len(result['transcription'].split()) if result['transcription'] else 0
                }
            return None
    
    def _create_activity(self, cursor, activity_data: Dict[str, Any]):
        """Create activity record"""
        
        activity_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO activities (
                activity_id, contact_id, activity_type, description,
                metadata, user_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            activity_id,
            activity_data['contact_id'],
            activity_data['activity_type'],
            activity_data['description'],
            json.dumps(activity_data.get('metadata', {})),
            activity_data.get('user_id'),
            datetime.utcnow().isoformat()
        ])
    
    def _create_callback_task(self, cursor, call_id: str, call_data: Dict[str, Any]):
        """Create callback task"""
        
        task_id = str(uuid.uuid4())
        
        # Schedule callback for next business day
        callback_date = (datetime.utcnow() + timedelta(days=1)).isoformat()
        
        cursor.execute("""
            INSERT INTO tasks (
                task_id, title, description, due_date, priority,
                assigned_to, contact_id, task_type, status,
                metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            task_id,
            "Callback requested",
            f"Follow up call requested - {call_data.get('notes', '')}",
            callback_date,
            'high',
            call_data['user_id'],
            call_data.get('contact_id'),
            'call',
            'pending',
            json.dumps({
                'original_call_id': call_id,
                'phone_number': call_data['phone_number'],
                'callback_requested': True
            }),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ])
    
    def _create_appointment_task(self, cursor, call_id: str, call_data: Dict[str, Any]):
        """Create appointment task"""
        
        task_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO tasks (
                task_id, title, description, due_date, priority,
                assigned_to, contact_id, task_type, status,
                metadata, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            task_id,
            "Appointment set",
            f"Meeting scheduled - {call_data.get('notes', '')}",
            call_data.get('scheduled_at', (datetime.utcnow() + timedelta(days=3)).isoformat()),
            'high',
            call_data['user_id'],
            call_data.get('contact_id'),
            'meeting',
            'pending',
            json.dumps({
                'original_call_id': call_id,
                'appointment_set': True
            }),
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ])
    
    def _update_contact_last_contact(self, contact_id: str):
        """Update contact's last contact date"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE contacts 
                SET last_contact_date = ?, updated_at = ?
                WHERE contact_id = ?
            """, [
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                contact_id
            ])
            
            conn.commit()