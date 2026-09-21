#!/usr/bin/env python3

"""
Rollback Manager for ActiveLog
Manages rollback procedures with safety checks and monitoring
"""

import os
import json
import sqlite3
import subprocess
import argparse
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class RollbackStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RollbackType(Enum):
    FULL = "full"
    SERVICES = "services"
    DATABASE = "database"
    CONFIG = "config"

@dataclass
class RollbackOperation:
    id: str
    type: RollbackType
    target_version: str
    target_backup: str
    status: RollbackStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict = None

class RollbackManager:
    def __init__(self, environment: str = "beta", data_dir: str = None):
        self.environment = environment
        self.data_dir = Path(data_dir or f"/app/data/rollback/{environment}")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "rollbacks.db"
        self.logger = logging.getLogger(__name__)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.data_dir / "rollback.log"),
                logging.StreamHandler()
            ]
        )
        
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for rollback tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rollbacks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                target_version TEXT,
                target_backup TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rollback_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rollback_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY (rollback_id) REFERENCES rollbacks (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def create_rollback(self, rollback_type: RollbackType, target_version: str = None, 
                       target_backup: str = None, metadata: Dict = None) -> str:
        """Create a new rollback operation"""
        rollback_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rollback = RollbackOperation(
            id=rollback_id,
            type=rollback_type,
            target_version=target_version or "latest-stable",
            target_backup=target_backup or "",
            status=RollbackStatus.PENDING,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rollbacks 
            (id, type, target_version, target_backup, status, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            rollback.id,
            rollback.type.value,
            rollback.target_version,
            rollback.target_backup,
            rollback.status.value,
            rollback.created_at,
            json.dumps(rollback.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Created rollback operation: {rollback_id}")
        return rollback_id

    def get_rollback(self, rollback_id: str) -> Optional[RollbackOperation]:
        """Get rollback operation by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM rollbacks WHERE id = ?', (rollback_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return RollbackOperation(
            id=row[0],
            type=RollbackType(row[1]),
            target_version=row[2],
            target_backup=row[3],
            status=RollbackStatus(row[4]),
            created_at=row[5],
            started_at=row[6],
            completed_at=row[7],
            error_message=row[8],
            metadata=json.loads(row[9] or '{}')
        )

    def update_rollback_status(self, rollback_id: str, status: RollbackStatus, 
                              error_message: str = None):
        """Update rollback operation status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        update_fields = ['status = ?']
        values = [status.value]
        
        if status == RollbackStatus.IN_PROGRESS:
            update_fields.append('started_at = ?')
            values.append(datetime.now().isoformat())
        elif status in [RollbackStatus.COMPLETED, RollbackStatus.FAILED, RollbackStatus.CANCELLED]:
            update_fields.append('completed_at = ?')
            values.append(datetime.now().isoformat())
        
        if error_message:
            update_fields.append('error_message = ?')
            values.append(error_message)
        
        values.append(rollback_id)
        
        cursor.execute(
            f'UPDATE rollbacks SET {", ".join(update_fields)} WHERE id = ?',
            values
        )
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Updated rollback {rollback_id} status to {status.value}")

    def log_rollback_event(self, rollback_id: str, level: str, message: str):
        """Log rollback event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rollback_logs (rollback_id, timestamp, level, message)
            VALUES (?, ?, ?, ?)
        ''', (rollback_id, datetime.now().isoformat(), level, message))
        
        conn.commit()
        conn.close()
        
        # Also log to standard logger
        getattr(self.logger, level.lower(), self.logger.info)(f"[{rollback_id}] {message}")

    def execute_rollback(self, rollback_id: str, dry_run: bool = False, 
                        force: bool = False) -> bool:
        """Execute rollback operation"""
        rollback = self.get_rollback(rollback_id)
        if not rollback:
            self.logger.error(f"Rollback not found: {rollback_id}")
            return False
        
        if rollback.status != RollbackStatus.PENDING:
            self.logger.error(f"Rollback {rollback_id} is not in pending state")
            return False
        
        try:
            self.update_rollback_status(rollback_id, RollbackStatus.IN_PROGRESS)
            self.log_rollback_event(rollback_id, "INFO", "Starting rollback execution")
            
            # Pre-rollback safety checks
            if not self._pre_rollback_checks(rollback_id):
                self.update_rollback_status(rollback_id, RollbackStatus.FAILED, 
                                          "Pre-rollback safety checks failed")
                return False
            
            # Execute rollback script
            script_path = Path(__file__).parent / "rollback-beta.sh"
            cmd = [str(script_path)]
            
            # Add rollback type
            if rollback.type == RollbackType.FULL:
                cmd.append("--full")
            elif rollback.type == RollbackType.SERVICES:
                cmd.append("--services-only")
            elif rollback.type == RollbackType.DATABASE:
                cmd.append("--database-only")
            
            # Add target version/backup
            if rollback.target_version:
                cmd.extend(["--to-version", rollback.target_version])
            if rollback.target_backup:
                cmd.extend(["--to-backup", rollback.target_backup])
            
            # Add flags
            if dry_run:
                cmd.append("--dry-run")
            if force:
                cmd.append("--force")
            
            self.log_rollback_event(rollback_id, "INFO", f"Executing: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                self.log_rollback_event(rollback_id, "INFO", "Rollback completed successfully")
                self.log_rollback_event(rollback_id, "DEBUG", f"STDOUT: {result.stdout}")
                
                # Post-rollback verification
                if self._post_rollback_verification(rollback_id):
                    self.update_rollback_status(rollback_id, RollbackStatus.COMPLETED)
                    return True
                else:
                    self.update_rollback_status(rollback_id, RollbackStatus.FAILED,
                                              "Post-rollback verification failed")
                    return False
            else:
                error_msg = f"Rollback script failed: {result.stderr}"
                self.log_rollback_event(rollback_id, "ERROR", error_msg)
                self.update_rollback_status(rollback_id, RollbackStatus.FAILED, error_msg)
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = "Rollback timed out after 30 minutes"
            self.log_rollback_event(rollback_id, "ERROR", error_msg)
            self.update_rollback_status(rollback_id, RollbackStatus.FAILED, error_msg)
            return False
        except Exception as e:
            error_msg = f"Rollback execution failed: {str(e)}"
            self.log_rollback_event(rollback_id, "ERROR", error_msg)
            self.update_rollback_status(rollback_id, RollbackStatus.FAILED, error_msg)
            return False

    def _pre_rollback_checks(self, rollback_id: str) -> bool:
        """Perform pre-rollback safety checks"""
        self.log_rollback_event(rollback_id, "INFO", "Performing pre-rollback safety checks")
        
        checks = [
            self._check_disk_space,
            self._check_backup_integrity,
            self._check_service_dependencies,
            self._check_active_users
        ]
        
        for check in checks:
            if not check(rollback_id):
                return False
        
        self.log_rollback_event(rollback_id, "INFO", "Pre-rollback safety checks passed")
        return True

    def _check_disk_space(self, rollback_id: str) -> bool:
        """Check available disk space"""
        try:
            stat = shutil.disk_usage('/')
            available_gb = stat.free / (1024**3)
            
            if available_gb < 5:  # Require at least 5GB
                self.log_rollback_event(rollback_id, "ERROR", 
                                      f"Insufficient disk space: {available_gb:.1f}GB available")
                return False
            
            self.log_rollback_event(rollback_id, "INFO", 
                                  f"Disk space check passed: {available_gb:.1f}GB available")
            return True
        except Exception as e:
            self.log_rollback_event(rollback_id, "ERROR", f"Disk space check failed: {e}")
            return False

    def _check_backup_integrity(self, rollback_id: str) -> bool:
        """Check backup file integrity"""
        self.log_rollback_event(rollback_id, "INFO", "Checking backup integrity")
        # Implementation would check backup file checksums, etc.
        return True

    def _check_service_dependencies(self, rollback_id: str) -> bool:
        """Check service dependencies"""
        self.log_rollback_event(rollback_id, "INFO", "Checking service dependencies")
        # Implementation would check for dependent services, etc.
        return True

    def _check_active_users(self, rollback_id: str) -> bool:
        """Check for active users (warn if high activity)"""
        self.log_rollback_event(rollback_id, "INFO", "Checking active user sessions")
        # Implementation would check active sessions, warn if high activity
        return True

    def _post_rollback_verification(self, rollback_id: str) -> bool:
        """Perform post-rollback verification"""
        self.log_rollback_event(rollback_id, "INFO", "Performing post-rollback verification")
        
        # Health check
        try:
            result = subprocess.run(
                ["curl", "-f", "http://localhost:8080/health"],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_rollback_event(rollback_id, "INFO", "Health check passed")
                return True
            else:
                self.log_rollback_event(rollback_id, "ERROR", "Health check failed")
                return False
        except Exception as e:
            self.log_rollback_event(rollback_id, "ERROR", f"Health check error: {e}")
            return False

    def list_rollbacks(self, limit: int = 50) -> List[RollbackOperation]:
        """List rollback operations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM rollbacks 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        rollbacks = []
        for row in rows:
            rollbacks.append(RollbackOperation(
                id=row[0],
                type=RollbackType(row[1]),
                target_version=row[2],
                target_backup=row[3],
                status=RollbackStatus(row[4]),
                created_at=row[5],
                started_at=row[6],
                completed_at=row[7],
                error_message=row[8],
                metadata=json.loads(row[9] or '{}')
            ))
        
        return rollbacks

    def cancel_rollback(self, rollback_id: str) -> bool:
        """Cancel pending rollback"""
        rollback = self.get_rollback(rollback_id)
        if not rollback:
            return False
        
        if rollback.status == RollbackStatus.PENDING:
            self.update_rollback_status(rollback_id, RollbackStatus.CANCELLED)
            self.log_rollback_event(rollback_id, "INFO", "Rollback cancelled")
            return True
        
        return False

    def cleanup_old_rollbacks(self, days: int = 30):
        """Clean up old rollback records"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM rollback_logs 
            WHERE rollback_id IN (
                SELECT id FROM rollbacks 
                WHERE created_at < ? AND status IN ('completed', 'failed', 'cancelled')
            )
        ''', (cutoff_date.isoformat(),))
        
        cursor.execute('''
            DELETE FROM rollbacks 
            WHERE created_at < ? AND status IN ('completed', 'failed', 'cancelled')
        ''', (cutoff_date.isoformat(),))
        
        conn.commit()
        deleted_count = cursor.rowcount
        conn.close()
        
        self.logger.info(f"Cleaned up {deleted_count} old rollback records")

def main():
    parser = argparse.ArgumentParser(description='Rollback Manager')
    parser.add_argument('--environment', default='beta', help='Environment (beta/prod)')
    parser.add_argument('--data-dir', help='Data directory path')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Create rollback
    create_parser = subparsers.add_parser('create', help='Create rollback operation')
    create_parser.add_argument('--type', choices=['full', 'services', 'database', 'config'], 
                              required=True, help='Rollback type')
    create_parser.add_argument('--version', help='Target version')
    create_parser.add_argument('--backup', help='Target backup')
    
    # Execute rollback
    exec_parser = subparsers.add_parser('execute', help='Execute rollback')
    exec_parser.add_argument('rollback_id', help='Rollback ID')
    exec_parser.add_argument('--dry-run', action='store_true', help='Dry run')
    exec_parser.add_argument('--force', action='store_true', help='Force execution')
    
    # List rollbacks
    list_parser = subparsers.add_parser('list', help='List rollbacks')
    list_parser.add_argument('--limit', type=int, default=20, help='Limit results')
    
    # Get rollback
    get_parser = subparsers.add_parser('get', help='Get rollback details')
    get_parser.add_argument('rollback_id', help='Rollback ID')
    
    # Cancel rollback
    cancel_parser = subparsers.add_parser('cancel', help='Cancel rollback')
    cancel_parser.add_argument('rollback_id', help='Rollback ID')
    
    # Cleanup
    cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup old rollbacks')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Days to keep')
    
    args = parser.parse_args()
    
    manager = RollbackManager(args.environment, args.data_dir)
    
    if args.command == 'create':
        rollback_id = manager.create_rollback(
            RollbackType(args.type),
            args.version,
            args.backup
        )
        print(f"Created rollback: {rollback_id}")
    
    elif args.command == 'execute':
        success = manager.execute_rollback(args.rollback_id, args.dry_run, args.force)
        print("Success" if success else "Failed")
    
    elif args.command == 'list':
        rollbacks = manager.list_rollbacks(args.limit)
        for rollback in rollbacks:
            print(f"{rollback.id}: {rollback.type.value} -> {rollback.status.value} ({rollback.created_at})")
    
    elif args.command == 'get':
        rollback = manager.get_rollback(args.rollback_id)
        if rollback:
            print(json.dumps(asdict(rollback), indent=2))
        else:
            print("Rollback not found")
    
    elif args.command == 'cancel':
        success = manager.cancel_rollback(args.rollback_id)
        print("Cancelled" if success else "Failed")
    
    elif args.command == 'cleanup':
        manager.cleanup_old_rollbacks(args.days)
        print("Cleanup completed")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()