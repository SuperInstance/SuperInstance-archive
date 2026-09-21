#!/usr/bin/env python3
"""
Database Schema and Management for Auto-Scheduler Service
Handles database initialization, migrations, and configuration storage
"""

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    backup_path: str = ""

class DatabaseManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        db_config = config.get('database', {})
        
        # Parse database URL (assuming SQLite for now)
        self.db_url = db_config.get('url', 'sqlite:///home/activeloguser/activelog/services/auto-scheduler/data/auto_scheduler.db')
        self.db_path = Path(self.db_url.replace('sqlite:///', ''))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.pool_size = db_config.get('pool_size', 5)
        self.max_overflow = db_config.get('max_overflow', 10)
        
        # Schema version for migrations
        self.current_schema_version = 3
        
    async def initialize(self):
        """Initialize database with all required schemas"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute('PRAGMA foreign_keys = ON')
            conn.execute('PRAGMA journal_mode = WAL')
            conn.execute('PRAGMA synchronous = NORMAL')
            
            cursor = conn.cursor()
            
            # Create version tracking table first
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            ''')
            
            # Check current version
            cursor.execute('SELECT MAX(version) FROM schema_version')
            result = cursor.fetchone()
            current_version = result[0] if result[0] is not None else 0
            
            # Apply migrations if needed
            if current_version < self.current_schema_version:
                await self._run_migrations(conn, current_version)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Database initialized successfully with schema version {self.current_schema_version}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    async def _run_migrations(self, conn: sqlite3.Connection, from_version: int):
        """Run database migrations"""
        cursor = conn.cursor()
        
        migrations = [
            (1, self._migration_v1, "Initial schema creation"),
            (2, self._migration_v2, "Add configuration tables"),
            (3, self._migration_v3, "Add performance optimization indexes")
        ]
        
        for version, migration_func, description in migrations:
            if from_version < version:
                logger.info(f"Applying migration v{version}: {description}")
                migration_func(cursor)
                
                cursor.execute('''
                    INSERT INTO schema_version (version, description)
                    VALUES (?, ?)
                ''', (version, description))
        
        conn.commit()
    
    def _migration_v1(self, cursor: sqlite3.Cursor):
        """Initial schema creation"""
        
        # Bots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                daily_limit_hours REAL NOT NULL DEFAULT 5.0,
                used_hours_today REAL NOT NULL DEFAULT 0.0,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_task_id TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                capabilities TEXT NOT NULL DEFAULT '[]',
                performance_score REAL NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 3,
                estimated_duration REAL NOT NULL,
                deadline TIMESTAMP,
                dependencies TEXT NOT NULL DEFAULT '[]',
                resource_requirements TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                bot_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            )
        ''')
        
        # Task dependencies junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT NOT NULL,
                depends_on_task_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_id, depends_on_task_id),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # Backup records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_records (
                id TEXT PRIMARY KEY,
                backup_type TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                checksum TEXT,
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                verification_date TIMESTAMP,
                metadata TEXT NOT NULL DEFAULT '{}',
                dependencies TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Progress entries table (already exists but ensure consistency)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS progress_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                component TEXT NOT NULL,
                metric TEXT NOT NULL,
                value TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                avg_task_completion_time REAL,
                task_success_rate REAL,
                bot_efficiency_score REAL,
                system_utilization REAL,
                backup_success_rate REAL,
                storage_growth_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Cost metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cost_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                total_bot_hours REAL,
                cost_per_hour REAL,
                total_cost REAL,
                cost_by_task_type TEXT DEFAULT '{}',
                efficiency_savings REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Reports table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Maintenance windows table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS maintenance_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week INTEGER NOT NULL CHECK (day_of_week >= 0 AND day_of_week <= 6),
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Resource reservations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resource_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_type TEXT NOT NULL,
                amount TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                task_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
    
    def _migration_v2(self, cursor: sqlite3.Cursor):
        """Add configuration tables"""
        
        # System configuration table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bot configuration history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_id TEXT NOT NULL,
                config_key TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots(id)
            )
        ''')
        
        # Task execution logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                log_level TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # System alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                is_acknowledged BOOLEAN NOT NULL DEFAULT 0,
                acknowledged_at TIMESTAMP,
                acknowledged_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        ''')
        
        # Backup verification results
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_id TEXT NOT NULL,
                verification_type TEXT NOT NULL,
                result TEXT NOT NULL,
                details TEXT,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (backup_id) REFERENCES backup_records(id)
            )
        ''')
    
    def _migration_v3(self, cursor: sqlite3.Cursor):
        """Add performance optimization indexes"""
        
        # Indexes for tasks table
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_bot_id ON tasks(bot_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_deadline ON tasks(deadline)')
        
        # Indexes for bots table
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bots_is_active ON bots(is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_bots_current_task ON bots(current_task_id)')
        
        # Indexes for progress entries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_timestamp ON progress_entries(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_component ON progress_entries(component)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_metric ON progress_entries(metric)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_comp_metric ON progress_entries(component, metric)')
        
        # Indexes for backup records
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backup_type ON backup_records(backup_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backup_status ON backup_records(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backup_timestamp ON backup_records(timestamp)')
        
        # Indexes for performance metrics
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_perf_timestamp ON performance_metrics(timestamp)')
        
        # Indexes for cost metrics
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_metrics(timestamp)')
        
        # Indexes for reports
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_timestamp ON reports(timestamp)')
        
        # Indexes for system alerts
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON system_alerts(is_acknowledged)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_severity ON system_alerts(severity)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_component ON system_alerts(component)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON system_alerts(created_at)')
    
    async def backup_database(self, backup_path: Optional[str] = None) -> str:
        """Create a backup of the database"""
        if not backup_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = str(self.db_path.parent / f"backup_{timestamp}.db")
        
        try:
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(backup_path)
            
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            logger.info(f"Database backed up to {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            raise
    
    async def restore_database(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            if not Path(backup_path).exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create a safety backup first
            safety_backup = await self.backup_database(
                str(self.db_path.parent / f"safety_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            )
            
            # Restore from backup
            backup_conn = sqlite3.connect(backup_path)
            restore_conn = sqlite3.connect(str(self.db_path))
            
            backup_conn.backup(restore_conn)
            
            backup_conn.close()
            restore_conn.close()
            
            logger.info(f"Database restored from {backup_path}")
            logger.info(f"Safety backup created at {safety_backup}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {e}")
            return False
    
    async def optimize_database(self):
        """Run database optimization and maintenance"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Update table statistics
            cursor.execute('ANALYZE')
            
            # Vacuum to reclaim space
            cursor.execute('VACUUM')
            
            # Rebuild indexes
            cursor.execute('REINDEX')
            
            conn.close()
            
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing database: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health info"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            stats = {
                'timestamp': datetime.now().isoformat(),
                'file_size_mb': self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0,
                'tables': {},
                'indexes': [],
                'schema_version': None
            }
            
            # Get schema version
            cursor.execute('SELECT MAX(version) FROM schema_version')
            result = cursor.fetchone()
            stats['schema_version'] = result[0] if result else 0
            
            # Get table statistics
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                if table_name.startswith('sqlite_'):
                    continue
                
                cursor.execute(f'SELECT COUNT(*) FROM `{table_name}`')
                row_count = cursor.fetchone()[0]
                
                stats['tables'][table_name] = {
                    'row_count': row_count
                }
            
            # Get index information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            indexes = cursor.fetchall()
            stats['indexes'] = [idx[0] for idx in indexes]
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}
    
    async def cleanup_old_data(self, retention_days: int = 90):
        """Clean up old data based on retention policies"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Clean up old progress entries
            cursor.execute('''
                DELETE FROM progress_entries 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            progress_deleted = cursor.rowcount
            
            # Clean up old reports
            cursor.execute('''
                DELETE FROM reports 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            reports_deleted = cursor.rowcount
            
            # Clean up old performance metrics
            cursor.execute('''
                DELETE FROM performance_metrics 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            perf_deleted = cursor.rowcount
            
            # Clean up old task execution logs
            cursor.execute('''
                DELETE FROM task_execution_logs 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            logs_deleted = cursor.rowcount
            
            # Clean up resolved system alerts older than retention period
            cursor.execute('''
                DELETE FROM system_alerts 
                WHERE resolved_at < ? AND resolved_at IS NOT NULL
            ''', (cutoff_date.isoformat(),))
            alerts_deleted = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            total_deleted = progress_deleted + reports_deleted + perf_deleted + logs_deleted + alerts_deleted
            
            logger.info(f"Cleaned up {total_deleted} old records (progress: {progress_deleted}, "
                       f"reports: {reports_deleted}, performance: {perf_deleted}, "
                       f"logs: {logs_deleted}, alerts: {alerts_deleted})")
            
            return total_deleted
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
            return 0
    
    async def get_connection(self) -> sqlite3.Connection:
        """Get a database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('PRAGMA foreign_keys = ON')
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    
    async def execute_query(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute a query and return results"""
        conn = await self.get_connection()
        try:
            cursor = conn.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            conn.close()
            raise e
    
    async def execute_non_query(self, query: str, params: Tuple = ()) -> int:
        """Execute a non-query statement and return affected rows"""
        conn = await self.get_connection()
        try:
            cursor = conn.execute(query, params)
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            return affected_rows
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e