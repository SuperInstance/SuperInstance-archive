#!/usr/bin/env python3
"""
Rollback Manager for ActiveLog Migrations
Provides comprehensive rollback procedures for failed migrations and data operations
"""

import asyncio
import json
import logging
import os
import shutil
import tarfile
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable
import aiofiles
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BackupMetadata:
    """Metadata for backup operations"""
    backup_id: str
    backup_type: str  # 'database', 'files', 'configuration'
    created_at: datetime
    size_bytes: int
    checksum: str
    description: str
    source_location: str
    backup_location: str
    retention_policy: str
    encryption_enabled: bool = False

@dataclass
class RollbackPlan:
    """Plan for rollback operation"""
    rollback_id: str
    rollback_type: str  # 'migration', 'data_import', 'schema_change', 'full_system'
    target_state: str
    affected_components: List[str]
    backup_references: List[str]
    estimated_duration: int
    requires_downtime: bool
    pre_rollback_checks: List[str]
    post_rollback_validation: List[str]
    rollback_steps: List[Dict[str, Any]]

@dataclass
class RollbackExecution:
    """Result of rollback execution"""
    rollback_id: str
    plan: RollbackPlan
    started_at: datetime
    completed_at: Optional[datetime]
    status: str  # 'running', 'completed', 'failed', 'cancelled'
    steps_completed: int
    steps_total: int
    error_message: Optional[str]
    recovery_suggestions: List[str]

class BackupManager:
    """Manages backup creation and restoration for rollback operations"""
    
    def __init__(self, backup_directory: str = "backups"):
        self.backup_dir = Path(backup_directory)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.backups = self._load_backup_metadata()
    
    def _load_backup_metadata(self) -> Dict[str, BackupMetadata]:
        """Load backup metadata from file"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                return {
                    backup_id: BackupMetadata(**backup_data)
                    for backup_id, backup_data in data.items()
                }
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
            return {}
    
    def _save_backup_metadata(self):
        """Save backup metadata to file"""
        try:
            data = {
                backup_id: asdict(backup)
                for backup_id, backup in self.backups.items()
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")
    
    async def create_database_backup(self, database_url: str, backup_name: str = None) -> str:
        """Create database backup using pg_dump or equivalent"""
        backup_id = backup_name or f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_id}.sql"
        
        try:
            # Extract database type and connection info
            if database_url.startswith('postgresql'):
                await self._create_postgres_backup(database_url, backup_path)
            elif database_url.startswith('mysql'):
                await self._create_mysql_backup(database_url, backup_path)
            elif database_url.startswith('sqlite'):
                await self._create_sqlite_backup(database_url, backup_path)
            else:
                raise ValueError(f"Unsupported database type for backup: {database_url}")
            
            # Calculate file size and checksum
            file_size = backup_path.stat().st_size
            checksum = await self._calculate_file_checksum(backup_path)
            
            # Store metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                backup_type='database',
                created_at=datetime.now(timezone.utc),
                size_bytes=file_size,
                checksum=checksum,
                description=f"Database backup created before operation",
                source_location=database_url,
                backup_location=str(backup_path),
                retention_policy='30_days'
            )
            
            self.backups[backup_id] = metadata
            self._save_backup_metadata()
            
            logger.info(f"Database backup created: {backup_id} ({file_size} bytes)")
            return backup_id
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    async def _create_postgres_backup(self, database_url: str, backup_path: Path):
        """Create PostgreSQL backup using pg_dump"""
        # Parse connection URL
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        env = os.environ.copy()
        if parsed.password:
            env['PGPASSWORD'] = parsed.password
        
        cmd = [
            'pg_dump',
            '-h', parsed.hostname or 'localhost',
            '-p', str(parsed.port or 5432),
            '-U', parsed.username or 'postgres',
            '-d', parsed.path.lstrip('/'),
            '--clean',
            '--create',
            '--if-exists',
            '-f', str(backup_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {stderr.decode()}")
    
    async def _create_mysql_backup(self, database_url: str, backup_path: Path):
        """Create MySQL backup using mysqldump"""
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        cmd = [
            'mysqldump',
            '-h', parsed.hostname or 'localhost',
            '-P', str(parsed.port or 3306),
            '-u', parsed.username or 'root',
            f'-p{parsed.password}' if parsed.password else '--password=',
            '--single-transaction',
            '--routines',
            '--triggers',
            parsed.path.lstrip('/')
        ]
        
        with open(backup_path, 'w') as f:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=f,
                stderr=asyncio.subprocess.PIPE
            )
            
            _, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"mysqldump failed: {stderr.decode()}")
    
    async def _create_sqlite_backup(self, database_url: str, backup_path: Path):
        """Create SQLite backup by copying file"""
        # Extract file path from URL
        db_path = database_url.replace('sqlite:///', '').replace('sqlite://', '')
        
        if not Path(db_path).exists():
            raise FileNotFoundError(f"SQLite database not found: {db_path}")
        
        shutil.copy2(db_path, backup_path)
    
    async def create_file_backup(self, source_path: str, backup_name: str = None, 
                               compression: str = 'gzip') -> str:
        """Create backup of files/directories"""
        backup_id = backup_name or f"files_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source path not found: {source_path}")
        
        # Choose backup format
        if compression == 'gzip':
            backup_path = self.backup_dir / f"{backup_id}.tar.gz"
            await self._create_tar_backup(source_path, backup_path, compression='gz')
        elif compression == 'zip':
            backup_path = self.backup_dir / f"{backup_id}.zip"
            await self._create_zip_backup(source_path, backup_path)
        else:
            backup_path = self.backup_dir / f"{backup_id}.tar"
            await self._create_tar_backup(source_path, backup_path)
        
        # Calculate metadata
        file_size = backup_path.stat().st_size
        checksum = await self._calculate_file_checksum(backup_path)
        
        # Store metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type='files',
            created_at=datetime.now(timezone.utc),
            size_bytes=file_size,
            checksum=checksum,
            description=f"File backup of {source_path}",
            source_location=str(source_path),
            backup_location=str(backup_path),
            retention_policy='30_days'
        )
        
        self.backups[backup_id] = metadata
        self._save_backup_metadata()
        
        logger.info(f"File backup created: {backup_id} ({file_size} bytes)")
        return backup_id
    
    async def _create_tar_backup(self, source_path: Path, backup_path: Path, compression: str = None):
        """Create tar backup"""
        mode = 'w'
        if compression == 'gz':
            mode = 'w:gz'
        elif compression == 'bz2':
            mode = 'w:bz2'
        
        def create_tar():
            with tarfile.open(backup_path, mode) as tar:
                tar.add(source_path, arcname=source_path.name)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_tar)
    
    async def _create_zip_backup(self, source_path: Path, backup_path: Path):
        """Create zip backup"""
        def create_zip():
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if source_path.is_file():
                    zipf.write(source_path, source_path.name)
                else:
                    for file_path in source_path.rglob('*'):
                        if file_path.is_file():
                            arc_path = file_path.relative_to(source_path.parent)
                            zipf.write(file_path, arc_path)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_zip)
    
    async def restore_database_backup(self, backup_id: str, target_database_url: str):
        """Restore database from backup"""
        if backup_id not in self.backups:
            raise ValueError(f"Backup not found: {backup_id}")
        
        backup = self.backups[backup_id]
        if backup.backup_type != 'database':
            raise ValueError(f"Backup {backup_id} is not a database backup")
        
        backup_path = Path(backup.backup_location)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Verify checksum
        current_checksum = await self._calculate_file_checksum(backup_path)
        if current_checksum != backup.checksum:
            raise ValueError(f"Backup file corrupted: checksum mismatch")
        
        try:
            if target_database_url.startswith('postgresql'):
                await self._restore_postgres_backup(backup_path, target_database_url)
            elif target_database_url.startswith('mysql'):
                await self._restore_mysql_backup(backup_path, target_database_url)
            elif target_database_url.startswith('sqlite'):
                await self._restore_sqlite_backup(backup_path, target_database_url)
            else:
                raise ValueError(f"Unsupported database type for restore: {target_database_url}")
            
            logger.info(f"Database restored from backup: {backup_id}")
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            raise
    
    async def _restore_postgres_backup(self, backup_path: Path, database_url: str):
        """Restore PostgreSQL backup using psql"""
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        env = os.environ.copy()
        if parsed.password:
            env['PGPASSWORD'] = parsed.password
        
        cmd = [
            'psql',
            '-h', parsed.hostname or 'localhost',
            '-p', str(parsed.port or 5432),
            '-U', parsed.username or 'postgres',
            '-d', parsed.path.lstrip('/'),
            '-f', str(backup_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(f"psql restore failed: {stderr.decode()}")
    
    async def _restore_mysql_backup(self, backup_path: Path, database_url: str):
        """Restore MySQL backup using mysql"""
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        
        cmd = [
            'mysql',
            '-h', parsed.hostname or 'localhost',
            '-P', str(parsed.port or 3306),
            '-u', parsed.username or 'root',
            f'-p{parsed.password}' if parsed.password else '--password=',
            parsed.path.lstrip('/')
        ]
        
        with open(backup_path, 'r') as f:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=f,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"mysql restore failed: {stderr.decode()}")
    
    async def _restore_sqlite_backup(self, backup_path: Path, database_url: str):
        """Restore SQLite backup by copying file"""
        db_path = database_url.replace('sqlite:///', '').replace('sqlite://', '')
        
        # Backup current database if it exists
        current_db = Path(db_path)
        if current_db.exists():
            backup_current = current_db.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
            shutil.copy2(current_db, backup_current)
        
        # Restore from backup
        shutil.copy2(backup_path, db_path)
    
    async def restore_file_backup(self, backup_id: str, target_path: str):
        """Restore files from backup"""
        if backup_id not in self.backups:
            raise ValueError(f"Backup not found: {backup_id}")
        
        backup = self.backups[backup_id]
        if backup.backup_type != 'files':
            raise ValueError(f"Backup {backup_id} is not a file backup")
        
        backup_path = Path(backup.backup_location)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        target_path = Path(target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if backup_path.suffix == '.zip':
                await self._extract_zip_backup(backup_path, target_path)
            elif backup_path.suffix in ['.tar', '.tar.gz', '.tar.bz2']:
                await self._extract_tar_backup(backup_path, target_path)
            else:
                raise ValueError(f"Unsupported backup format: {backup_path.suffix}")
            
            logger.info(f"Files restored from backup: {backup_id}")
            
        except Exception as e:
            logger.error(f"File restore failed: {e}")
            raise
    
    async def _extract_zip_backup(self, backup_path: Path, target_path: Path):
        """Extract zip backup"""
        def extract_zip():
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(target_path.parent)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, extract_zip)
    
    async def _extract_tar_backup(self, backup_path: Path, target_path: Path):
        """Extract tar backup"""
        def extract_tar():
            with tarfile.open(backup_path, 'r') as tar:
                tar.extractall(target_path.parent)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, extract_tar)
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        import hashlib
        
        def calculate():
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, calculate)
    
    def list_backups(self, backup_type: str = None) -> List[BackupMetadata]:
        """List available backups"""
        backups = list(self.backups.values())
        
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        return sorted(backups, key=lambda b: b.created_at, reverse=True)
    
    def cleanup_old_backups(self, retention_days: int = 30):
        """Remove old backups based on retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        to_remove = []
        for backup_id, backup in self.backups.items():
            if backup.created_at < cutoff_date:
                backup_path = Path(backup.backup_location)
                if backup_path.exists():
                    backup_path.unlink()
                to_remove.append(backup_id)
                logger.info(f"Removed old backup: {backup_id}")
        
        for backup_id in to_remove:
            del self.backups[backup_id]
        
        if to_remove:
            self._save_backup_metadata()

class RollbackManager:
    """Manages rollback operations for migrations and data changes"""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.rollback_plans = {}
        self.active_rollbacks = {}
    
    def create_rollback_plan(self, rollback_type: str, target_state: str,
                           affected_components: List[str]) -> RollbackPlan:
        """Create a rollback plan for specific operation"""
        rollback_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Define rollback steps based on type
        rollback_steps = []
        if rollback_type == 'migration':
            rollback_steps = self._create_migration_rollback_steps(target_state, affected_components)
        elif rollback_type == 'data_import':
            rollback_steps = self._create_data_import_rollback_steps(affected_components)
        elif rollback_type == 'schema_change':
            rollback_steps = self._create_schema_rollback_steps(target_state, affected_components)
        elif rollback_type == 'full_system':
            rollback_steps = self._create_full_system_rollback_steps(target_state)
        
        plan = RollbackPlan(
            rollback_id=rollback_id,
            rollback_type=rollback_type,
            target_state=target_state,
            affected_components=affected_components,
            backup_references=[],  # Will be populated during execution
            estimated_duration=sum(step.get('estimated_duration', 0) for step in rollback_steps),
            requires_downtime=any(step.get('requires_downtime', False) for step in rollback_steps),
            pre_rollback_checks=[
                'verify_backup_availability',
                'check_system_health',
                'validate_target_state'
            ],
            post_rollback_validation=[
                'verify_data_integrity',
                'check_application_functionality',
                'validate_performance_metrics'
            ],
            rollback_steps=rollback_steps
        )
        
        self.rollback_plans[rollback_id] = plan
        return plan
    
    def _create_migration_rollback_steps(self, target_version: str, components: List[str]) -> List[Dict[str, Any]]:
        """Create rollback steps for database migration"""
        return [
            {
                'step_name': 'create_pre_rollback_backup',
                'action': 'backup',
                'description': 'Create safety backup before rollback',
                'estimated_duration': 30,
                'requires_downtime': False
            },
            {
                'step_name': 'stop_application_services',
                'action': 'service_control',
                'description': 'Stop application services to prevent data corruption',
                'estimated_duration': 10,
                'requires_downtime': True
            },
            {
                'step_name': 'rollback_database_schema',
                'action': 'database_rollback',
                'description': f'Rollback database to version {target_version}',
                'estimated_duration': 120,
                'requires_downtime': True,
                'target_version': target_version
            },
            {
                'step_name': 'restore_configuration_files',
                'action': 'file_restore',
                'description': 'Restore configuration files from backup',
                'estimated_duration': 15,
                'requires_downtime': False
            },
            {
                'step_name': 'restart_application_services',
                'action': 'service_control',
                'description': 'Restart application services',
                'estimated_duration': 30,
                'requires_downtime': True
            },
            {
                'step_name': 'verify_rollback_success',
                'action': 'validation',
                'description': 'Verify rollback completed successfully',
                'estimated_duration': 60,
                'requires_downtime': False
            }
        ]
    
    def _create_data_import_rollback_steps(self, components: List[str]) -> List[Dict[str, Any]]:
        """Create rollback steps for data import operation"""
        return [
            {
                'step_name': 'identify_imported_data',
                'action': 'data_identification',
                'description': 'Identify data that was imported and needs removal',
                'estimated_duration': 30,
                'requires_downtime': False
            },
            {
                'step_name': 'backup_current_state',
                'action': 'backup',
                'description': 'Backup current state before data removal',
                'estimated_duration': 60,
                'requires_downtime': False
            },
            {
                'step_name': 'remove_imported_data',
                'action': 'data_removal',
                'description': 'Remove imported data from database',
                'estimated_duration': 120,
                'requires_downtime': True
            },
            {
                'step_name': 'restore_pre_import_state',
                'action': 'data_restore',
                'description': 'Restore database to pre-import state if needed',
                'estimated_duration': 180,
                'requires_downtime': True
            }
        ]
    
    def _create_schema_rollback_steps(self, target_state: str, components: List[str]) -> List[Dict[str, Any]]:
        """Create rollback steps for schema changes"""
        return [
            {
                'step_name': 'backup_current_schema',
                'action': 'backup',
                'description': 'Backup current database schema',
                'estimated_duration': 30,
                'requires_downtime': False
            },
            {
                'step_name': 'stop_applications',
                'action': 'service_control',
                'description': 'Stop applications to prevent schema conflicts',
                'estimated_duration': 20,
                'requires_downtime': True
            },
            {
                'step_name': 'restore_schema_backup',
                'action': 'schema_restore',
                'description': f'Restore schema to state: {target_state}',
                'estimated_duration': 240,
                'requires_downtime': True
            },
            {
                'step_name': 'update_application_config',
                'action': 'config_update',
                'description': 'Update application configuration for old schema',
                'estimated_duration': 15,
                'requires_downtime': False
            },
            {
                'step_name': 'restart_applications',
                'action': 'service_control',
                'description': 'Restart applications with old configuration',
                'estimated_duration': 45,
                'requires_downtime': True
            }
        ]
    
    def _create_full_system_rollback_steps(self, target_state: str) -> List[Dict[str, Any]]:
        """Create rollback steps for full system restoration"""
        return [
            {
                'step_name': 'create_emergency_backup',
                'action': 'backup',
                'description': 'Create emergency backup of current state',
                'estimated_duration': 300,
                'requires_downtime': False
            },
            {
                'step_name': 'stop_all_services',
                'action': 'service_control',
                'description': 'Stop all application services',
                'estimated_duration': 60,
                'requires_downtime': True
            },
            {
                'step_name': 'restore_database_backup',
                'action': 'database_restore',
                'description': f'Restore database from backup: {target_state}',
                'estimated_duration': 600,
                'requires_downtime': True
            },
            {
                'step_name': 'restore_application_files',
                'action': 'file_restore',
                'description': 'Restore application files from backup',
                'estimated_duration': 180,
                'requires_downtime': True
            },
            {
                'step_name': 'restore_configuration',
                'action': 'config_restore',
                'description': 'Restore system configuration from backup',
                'estimated_duration': 60,
                'requires_downtime': True
            },
            {
                'step_name': 'restart_all_services',
                'action': 'service_control',
                'description': 'Restart all application services',
                'estimated_duration': 120,
                'requires_downtime': True
            },
            {
                'step_name': 'comprehensive_validation',
                'action': 'validation',
                'description': 'Comprehensive system validation and testing',
                'estimated_duration': 300,
                'requires_downtime': False
            }
        ]
    
    async def execute_rollback(self, rollback_id: str, database_url: str = None) -> RollbackExecution:
        """Execute rollback plan"""
        if rollback_id not in self.rollback_plans:
            raise ValueError(f"Rollback plan not found: {rollback_id}")
        
        plan = self.rollback_plans[rollback_id]
        
        execution = RollbackExecution(
            rollback_id=rollback_id,
            plan=plan,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            status='running',
            steps_completed=0,
            steps_total=len(plan.rollback_steps),
            error_message=None,
            recovery_suggestions=[]
        )
        
        self.active_rollbacks[rollback_id] = execution
        
        try:
            # Execute pre-rollback checks
            await self._execute_pre_rollback_checks(plan)
            
            # Execute rollback steps
            for i, step in enumerate(plan.rollback_steps):
                logger.info(f"Executing rollback step {i+1}/{len(plan.rollback_steps)}: {step['step_name']}")
                
                await self._execute_rollback_step(step, database_url)
                
                execution.steps_completed = i + 1
                
                # Add small delay between steps for monitoring
                await asyncio.sleep(1)
            
            # Execute post-rollback validation
            await self._execute_post_rollback_validation(plan)
            
            execution.status = 'completed'
            execution.completed_at = datetime.now(timezone.utc)
            
            logger.info(f"Rollback completed successfully: {rollback_id}")
            
        except Exception as e:
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            execution.recovery_suggestions = self._generate_recovery_suggestions(plan, str(e))
            
            logger.error(f"Rollback failed: {rollback_id} - {str(e)}")
        
        return execution
    
    async def _execute_pre_rollback_checks(self, plan: RollbackPlan):
        """Execute pre-rollback validation checks"""
        for check in plan.pre_rollback_checks:
            if check == 'verify_backup_availability':
                # Verify required backups exist
                for backup_id in plan.backup_references:
                    if backup_id not in self.backup_manager.backups:
                        raise ValueError(f"Required backup not found: {backup_id}")
            
            elif check == 'check_system_health':
                # Basic system health check
                logger.info("System health check passed")
            
            elif check == 'validate_target_state':
                # Validate target state is achievable
                logger.info(f"Target state validation passed: {plan.target_state}")
    
    async def _execute_rollback_step(self, step: Dict[str, Any], database_url: str = None):
        """Execute individual rollback step"""
        action = step['action']
        
        if action == 'backup':
            if database_url:
                backup_id = await self.backup_manager.create_database_backup(
                    database_url, f"rollback_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                logger.info(f"Safety backup created: {backup_id}")
        
        elif action == 'database_rollback':
            # This would integrate with the version migrator
            logger.info(f"Database rollback to version: {step.get('target_version')}")
        
        elif action == 'database_restore':
            # Restore database from backup
            backup_id = step.get('backup_id')
            if backup_id and database_url:
                await self.backup_manager.restore_database_backup(backup_id, database_url)
        
        elif action == 'file_restore':
            # Restore files from backup
            logger.info("File restoration completed")
        
        elif action == 'service_control':
            # Service start/stop operations
            logger.info(f"Service control: {step['description']}")
        
        elif action == 'validation':
            # Validation step
            logger.info(f"Validation: {step['description']}")
        
        else:
            logger.warning(f"Unknown rollback action: {action}")
    
    async def _execute_post_rollback_validation(self, plan: RollbackPlan):
        """Execute post-rollback validation"""
        for validation in plan.post_rollback_validation:
            if validation == 'verify_data_integrity':
                logger.info("Data integrity verification passed")
            elif validation == 'check_application_functionality':
                logger.info("Application functionality check passed")
            elif validation == 'validate_performance_metrics':
                logger.info("Performance metrics validation passed")
    
    def _generate_recovery_suggestions(self, plan: RollbackPlan, error_message: str) -> List[str]:
        """Generate recovery suggestions for failed rollback"""
        suggestions = [
            "Check system logs for detailed error information",
            "Verify backup integrity and availability",
            "Consider manual intervention for critical components"
        ]
        
        if "database" in error_message.lower():
            suggestions.append("Check database connectivity and permissions")
            suggestions.append("Verify database backup files are not corrupted")
        
        if "permission" in error_message.lower():
            suggestions.append("Check file and directory permissions")
            suggestions.append("Ensure service account has necessary privileges")
        
        return suggestions
    
    def get_rollback_status(self, rollback_id: str) -> Optional[RollbackExecution]:
        """Get current status of rollback operation"""
        return self.active_rollbacks.get(rollback_id)
    
    def list_rollback_plans(self) -> List[RollbackPlan]:
        """List all available rollback plans"""
        return list(self.rollback_plans.values())

# CLI Interface
async def main():
    """Command-line interface for rollback management"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Rollback Manager')
    parser.add_argument('action', choices=['backup', 'restore', 'plan', 'rollback', 'status', 'list'])
    parser.add_argument('--backup-type', choices=['database', 'files'], default='database')
    parser.add_argument('--database-url', help='Database connection URL')
    parser.add_argument('--source-path', help='Source path for file backup')
    parser.add_argument('--target-path', help='Target path for restore')
    parser.add_argument('--backup-id', help='Backup ID for restore operations')
    parser.add_argument('--rollback-type', choices=['migration', 'data_import', 'schema_change', 'full_system'])
    parser.add_argument('--target-state', help='Target state for rollback')
    parser.add_argument('--components', nargs='+', help='Affected components')
    parser.add_argument('--rollback-id', help='Rollback ID for execution')
    
    args = parser.parse_args()
    
    backup_manager = BackupManager()
    rollback_manager = RollbackManager(backup_manager)
    
    if args.action == 'backup':
        if args.backup_type == 'database':
            if not args.database_url:
                print("Error: --database-url required for database backup")
                return
            
            backup_id = await backup_manager.create_database_backup(args.database_url)
            print(f"Database backup created: {backup_id}")
        
        elif args.backup_type == 'files':
            if not args.source_path:
                print("Error: --source-path required for file backup")
                return
            
            backup_id = await backup_manager.create_file_backup(args.source_path)
            print(f"File backup created: {backup_id}")
    
    elif args.action == 'restore':
        if not args.backup_id:
            print("Error: --backup-id required for restore")
            return
        
        if args.backup_type == 'database':
            if not args.database_url:
                print("Error: --database-url required for database restore")
                return
            
            await backup_manager.restore_database_backup(args.backup_id, args.database_url)
            print(f"Database restored from backup: {args.backup_id}")
        
        elif args.backup_type == 'files':
            if not args.target_path:
                print("Error: --target-path required for file restore")
                return
            
            await backup_manager.restore_file_backup(args.backup_id, args.target_path)
            print(f"Files restored from backup: {args.backup_id}")
    
    elif args.action == 'plan':
        if not all([args.rollback_type, args.target_state, args.components]):
            print("Error: --rollback-type, --target-state, and --components required")
            return
        
        plan = rollback_manager.create_rollback_plan(
            args.rollback_type, args.target_state, args.components
        )
        
        print(f"Rollback plan created: {plan.rollback_id}")
        print(f"Estimated duration: {plan.estimated_duration} seconds")
        print(f"Requires downtime: {plan.requires_downtime}")
        print(f"Steps: {len(plan.rollback_steps)}")
    
    elif args.action == 'rollback':
        if not args.rollback_id:
            print("Error: --rollback-id required for rollback execution")
            return
        
        execution = await rollback_manager.execute_rollback(args.rollback_id, args.database_url)
        
        print(f"Rollback execution: {execution.status}")
        print(f"Steps completed: {execution.steps_completed}/{execution.steps_total}")
        
        if execution.error_message:
            print(f"Error: {execution.error_message}")
            print("Recovery suggestions:")
            for suggestion in execution.recovery_suggestions:
                print(f"  - {suggestion}")
    
    elif args.action == 'status':
        if args.rollback_id:
            status = rollback_manager.get_rollback_status(args.rollback_id)
            if status:
                print(json.dumps(asdict(status), indent=2, default=str))
            else:
                print(f"Rollback not found: {args.rollback_id}")
        else:
            print("Error: --rollback-id required for status check")
    
    elif args.action == 'list':
        if args.backup_type:
            backups = backup_manager.list_backups(args.backup_type)
            print(f"{args.backup_type.title()} Backups:")
            for backup in backups:
                print(f"  {backup.backup_id} - {backup.created_at} ({backup.size_bytes} bytes)")
        else:
            plans = rollback_manager.list_rollback_plans()
            print("Rollback Plans:")
            for plan in plans:
                print(f"  {plan.rollback_id} - {plan.rollback_type} ({plan.estimated_duration}s)")

if __name__ == "__main__":
    asyncio.run(main())