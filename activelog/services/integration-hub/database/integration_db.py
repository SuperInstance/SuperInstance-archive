"""
Integration Database Manager
Database management for integration hub data storage
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path


class IntegrationDatabase:
    """Database manager for integration hub"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/services/integration-hub/database/integrations.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        
    def _ensure_db_directory(self):
        """Ensure database directory exists"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
    def _init_database(self):
        """Initialize database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Integration configurations
                CREATE TABLE IF NOT EXISTS integration_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    integration_name TEXT UNIQUE NOT NULL,
                    config_data TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Integration sync history
                CREATE TABLE IF NOT EXISTS sync_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    integration_name TEXT NOT NULL,
                    sync_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    records_processed INTEGER DEFAULT 0,
                    records_successful INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    error_message TEXT,
                    sync_data TEXT,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_seconds REAL
                );
                
                -- Workflow definitions
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger_integration TEXT NOT NULL,
                    trigger_event TEXT NOT NULL,
                    steps TEXT NOT NULL, -- JSON array of workflow steps
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Workflow executions
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    execution_id TEXT UNIQUE NOT NULL,
                    trigger_data TEXT NOT NULL, -- JSON trigger data
                    status TEXT NOT NULL, -- pending, running, completed, failed
                    steps_completed INTEGER DEFAULT 0,
                    total_steps INTEGER NOT NULL,
                    results TEXT, -- JSON execution results
                    error_message TEXT,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_seconds REAL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (workflow_id)
                );
                
                -- Webhook logs
                CREATE TABLE IF NOT EXISTS webhook_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    integration_name TEXT NOT NULL,
                    webhook_type TEXT NOT NULL,
                    event_type TEXT,
                    payload TEXT NOT NULL, -- JSON payload
                    headers TEXT, -- JSON headers
                    status_code INTEGER,
                    response_data TEXT,
                    processing_time_ms REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Integration usage statistics
                CREATE TABLE IF NOT EXISTS usage_stats (
                    integration_name TEXT NOT NULL,
                    stat_type TEXT NOT NULL, -- sync, webhook, api_call, error
                    stat_date DATE NOT NULL,
                    count INTEGER NOT NULL DEFAULT 1,
                    metadata TEXT, -- JSON additional data
                    PRIMARY KEY (integration_name, stat_type, stat_date)
                ) WITHOUT ROWID;
                
                -- Data mapping configurations
                CREATE TABLE IF NOT EXISTS data_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapping_name TEXT UNIQUE NOT NULL,
                    source_integration TEXT NOT NULL,
                    target_integration TEXT NOT NULL,
                    source_object_type TEXT NOT NULL,
                    target_object_type TEXT NOT NULL,
                    field_mappings TEXT NOT NULL, -- JSON field mapping rules
                    transformation_rules TEXT, -- JSON transformation rules
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Integration credentials (encrypted)
                CREATE TABLE IF NOT EXISTS integration_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    integration_name TEXT UNIQUE NOT NULL,
                    credential_type TEXT NOT NULL, -- oauth, api_key, basic_auth
                    encrypted_credentials TEXT NOT NULL,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Create indexes for better performance
                CREATE INDEX IF NOT EXISTS idx_sync_history_integration_date 
                    ON sync_history (integration_name, started_at);
                CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow_id 
                    ON workflow_executions (workflow_id);
                CREATE INDEX IF NOT EXISTS idx_webhook_logs_integration_date 
                    ON webhook_logs (integration_name, created_at);
                CREATE INDEX IF NOT EXISTS idx_usage_stats_integration_date 
                    ON usage_stats (integration_name, stat_date);
            """)
            
    def save_integration_config(self, integration_name: str, config_data: Dict[str, Any], enabled: bool = False) -> bool:
        """Save or update integration configuration"""
        try:
            config_json = json.dumps(config_data)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO integration_configs 
                    (integration_name, config_data, enabled, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (integration_name, config_json, enabled))
                
            return True
        except Exception as e:
            print(f"Error saving integration config: {e}")
            return False
            
    def get_integration_config(self, integration_name: str) -> Optional[Dict[str, Any]]:
        """Get integration configuration"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT config_data, enabled, created_at, updated_at
                    FROM integration_configs 
                    WHERE integration_name = ?
                """, (integration_name,))
                
                row = cursor.fetchone()
                if row:
                    config = json.loads(row['config_data'])
                    config.update({
                        'enabled': bool(row['enabled']),
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                    return config
                    
        except Exception as e:
            print(f"Error getting integration config: {e}")
            
        return None
        
    def list_integration_configs(self) -> List[Dict[str, Any]]:
        """List all integration configurations"""
        configs = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT integration_name, enabled, created_at, updated_at
                    FROM integration_configs 
                    ORDER BY integration_name
                """)
                
                for row in cursor.fetchall():
                    configs.append({
                        'integration_name': row['integration_name'],
                        'enabled': bool(row['enabled']),
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                    
        except Exception as e:
            print(f"Error listing integration configs: {e}")
            
        return configs
        
    def record_sync_history(self, integration_name: str, sync_type: str, status: str,
                           records_processed: int = 0, records_successful: int = 0,
                           records_failed: int = 0, error_message: Optional[str] = None,
                           sync_data: Optional[Dict[str, Any]] = None,
                           started_at: Optional[datetime] = None,
                           completed_at: Optional[datetime] = None) -> int:
        """Record sync history entry"""
        try:
            if started_at is None:
                started_at = datetime.now()
            if completed_at is None and status in ['completed', 'failed']:
                completed_at = datetime.now()
                
            duration_seconds = None
            if completed_at and started_at:
                duration_seconds = (completed_at - started_at).total_seconds()
                
            sync_data_json = json.dumps(sync_data) if sync_data else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO sync_history 
                    (integration_name, sync_type, status, records_processed, records_successful,
                     records_failed, error_message, sync_data, started_at, completed_at, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (integration_name, sync_type, status, records_processed, records_successful,
                      records_failed, error_message, sync_data_json,
                      started_at.isoformat(), completed_at.isoformat() if completed_at else None,
                      duration_seconds))
                
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error recording sync history: {e}")
            return 0
            
    def get_sync_history(self, integration_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get sync history"""
        history = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if integration_name:
                    cursor = conn.execute("""
                        SELECT * FROM sync_history 
                        WHERE integration_name = ?
                        ORDER BY started_at DESC 
                        LIMIT ?
                    """, (integration_name, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM sync_history 
                        ORDER BY started_at DESC 
                        LIMIT ?
                    """, (limit,))
                
                for row in cursor.fetchall():
                    sync_data = None
                    if row['sync_data']:
                        try:
                            sync_data = json.loads(row['sync_data'])
                        except:
                            pass
                            
                    history.append({
                        'id': row['id'],
                        'integration_name': row['integration_name'],
                        'sync_type': row['sync_type'],
                        'status': row['status'],
                        'records_processed': row['records_processed'],
                        'records_successful': row['records_successful'],
                        'records_failed': row['records_failed'],
                        'error_message': row['error_message'],
                        'sync_data': sync_data,
                        'started_at': row['started_at'],
                        'completed_at': row['completed_at'],
                        'duration_seconds': row['duration_seconds']
                    })
                    
        except Exception as e:
            print(f"Error getting sync history: {e}")
            
        return history
        
    def create_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Create new workflow"""
        try:
            workflow_id = f"workflow_{datetime.now().timestamp()}"
            steps_json = json.dumps(workflow_data.get('steps', []))
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO workflows 
                    (workflow_id, name, description, trigger_integration, trigger_event, steps, enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (workflow_id, workflow_data.get('name', 'Untitled Workflow'),
                      workflow_data.get('description', ''),
                      workflow_data.get('trigger_integration', ''),
                      workflow_data.get('trigger_event', ''),
                      steps_json, workflow_data.get('enabled', True)))
                
            return workflow_id
            
        except Exception as e:
            print(f"Error creating workflow: {e}")
            return ""
            
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM workflows WHERE workflow_id = ?
                """, (workflow_id,))
                
                row = cursor.fetchone()
                if row:
                    steps = []
                    if row['steps']:
                        try:
                            steps = json.loads(row['steps'])
                        except:
                            pass
                            
                    return {
                        'id': row['id'],
                        'workflow_id': row['workflow_id'],
                        'name': row['name'],
                        'description': row['description'],
                        'trigger_integration': row['trigger_integration'],
                        'trigger_event': row['trigger_event'],
                        'steps': steps,
                        'enabled': bool(row['enabled']),
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
                    
        except Exception as e:
            print(f"Error getting workflow: {e}")
            
        return None
        
    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get all workflows"""
        workflows = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM workflows ORDER BY created_at DESC
                """)
                
                for row in cursor.fetchall():
                    steps = []
                    if row['steps']:
                        try:
                            steps = json.loads(row['steps'])
                        except:
                            pass
                            
                    workflows.append({
                        'id': row['id'],
                        'workflow_id': row['workflow_id'],
                        'name': row['name'],
                        'description': row['description'],
                        'trigger_integration': row['trigger_integration'],
                        'trigger_event': row['trigger_event'],
                        'steps': steps,
                        'enabled': bool(row['enabled']),
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
                    
        except Exception as e:
            print(f"Error getting workflows: {e}")
            
        return workflows
        
    def record_webhook_log(self, integration_name: str, webhook_type: str,
                          event_type: Optional[str], payload: Dict[str, Any],
                          headers: Optional[Dict[str, str]] = None,
                          status_code: Optional[int] = None,
                          response_data: Optional[Dict[str, Any]] = None,
                          processing_time_ms: Optional[float] = None) -> int:
        """Record webhook log entry"""
        try:
            payload_json = json.dumps(payload)
            headers_json = json.dumps(headers) if headers else None
            response_json = json.dumps(response_data) if response_data else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO webhook_logs 
                    (integration_name, webhook_type, event_type, payload, headers,
                     status_code, response_data, processing_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (integration_name, webhook_type, event_type, payload_json,
                      headers_json, status_code, response_json, processing_time_ms))
                
                return cursor.lastrowid
                
        except Exception as e:
            print(f"Error recording webhook log: {e}")
            return 0
            
    def record_usage_stat(self, integration_name: str, stat_type: str,
                         count: int = 1, metadata: Optional[Dict[str, Any]] = None,
                         stat_date: Optional[datetime] = None) -> bool:
        """Record usage statistic"""
        try:
            if stat_date is None:
                stat_date = datetime.now().date()
                
            metadata_json = json.dumps(metadata) if metadata else None
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO usage_stats 
                    (integration_name, stat_type, stat_date, count, metadata)
                    VALUES (?, ?, ?, 
                           COALESCE((SELECT count FROM usage_stats 
                                   WHERE integration_name = ? AND stat_type = ? AND stat_date = ?), 0) + ?,
                           ?)
                """, (integration_name, stat_type, stat_date.isoformat(),
                      integration_name, stat_type, stat_date.isoformat(), count, metadata_json))
                
            return True
            
        except Exception as e:
            print(f"Error recording usage stat: {e}")
            return False
            
    def get_integration_usage_stats(self, integration_name: Optional[str] = None,
                                  days: int = 30) -> Dict[str, Any]:
        """Get integration usage statistics"""
        stats = {
            'integrations': {},
            'total_stats': {},
            'date_range': {
                'days': days,
                'start_date': (datetime.now().date() - timedelta(days=days)).isoformat(),
                'end_date': datetime.now().date().isoformat()
            }
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Build query based on parameters
                where_clause = "WHERE stat_date >= date('now', '-{} days')".format(days)
                params = []
                
                if integration_name:
                    where_clause += " AND integration_name = ?"
                    params.append(integration_name)
                
                # Get aggregated stats by integration
                cursor = conn.execute(f"""
                    SELECT integration_name, stat_type, SUM(count) as total_count
                    FROM usage_stats 
                    {where_clause}
                    GROUP BY integration_name, stat_type
                    ORDER BY integration_name, stat_type
                """, params)
                
                for row in cursor.fetchall():
                    integration = row['integration_name']
                    if integration not in stats['integrations']:
                        stats['integrations'][integration] = {}
                    stats['integrations'][integration][row['stat_type']] = row['total_count']
                
                # Get total stats across all integrations
                cursor = conn.execute(f"""
                    SELECT stat_type, SUM(count) as total_count
                    FROM usage_stats 
                    {where_clause}
                    GROUP BY stat_type
                """, params)
                
                for row in cursor.fetchall():
                    stats['total_stats'][row['stat_type']] = row['total_count']
                    
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            
        return stats
        
    def cleanup_old_logs(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old logs and history"""
        cleanup_results = {
            'sync_history_deleted': 0,
            'webhook_logs_deleted': 0,
            'workflow_executions_deleted': 0,
            'usage_stats_deleted': 0
        }
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Clean up sync history
                cursor = conn.execute("""
                    DELETE FROM sync_history 
                    WHERE started_at < ?
                """, (cutoff_date,))
                cleanup_results['sync_history_deleted'] = cursor.rowcount
                
                # Clean up webhook logs
                cursor = conn.execute("""
                    DELETE FROM webhook_logs 
                    WHERE created_at < ?
                """, (cutoff_date,))
                cleanup_results['webhook_logs_deleted'] = cursor.rowcount
                
                # Clean up workflow executions
                cursor = conn.execute("""
                    DELETE FROM workflow_executions 
                    WHERE started_at < ?
                """, (cutoff_date,))
                cleanup_results['workflow_executions_deleted'] = cursor.rowcount
                
                # Clean up usage stats
                cutoff_date_str = (datetime.now().date() - timedelta(days=days_to_keep)).isoformat()
                cursor = conn.execute("""
                    DELETE FROM usage_stats 
                    WHERE stat_date < ?
                """, (cutoff_date_str,))
                cleanup_results['usage_stats_deleted'] = cursor.rowcount
                
        except Exception as e:
            print(f"Error cleaning up old logs: {e}")
            
        return cleanup_results
        
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get table counts
                tables = [
                    'integration_configs', 'sync_history', 'workflows',
                    'workflow_executions', 'webhook_logs', 'usage_stats',
                    'data_mappings', 'integration_credentials'
                ]
                
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    row = cursor.fetchone()
                    stats[f'{table}_count'] = row['count']
                
                # Get database file size
                db_path = Path(self.db_path)
                if db_path.exists():
                    stats['database_size_bytes'] = db_path.stat().st_size
                    stats['database_size_mb'] = round(stats['database_size_bytes'] / 1024 / 1024, 2)
                
                # Get recent activity
                cursor = conn.execute("""
                    SELECT COUNT(*) as count FROM sync_history 
                    WHERE started_at > datetime('now', '-1 day')
                """)
                row = cursor.fetchone()
                stats['syncs_last_24h'] = row['count']
                
                cursor = conn.execute("""
                    SELECT COUNT(*) as count FROM webhook_logs 
                    WHERE created_at > datetime('now', '-1 day')
                """)
                row = cursor.fetchone()
                stats['webhooks_last_24h'] = row['count']
                
        except Exception as e:
            print(f"Error getting database stats: {e}")
            
        return stats