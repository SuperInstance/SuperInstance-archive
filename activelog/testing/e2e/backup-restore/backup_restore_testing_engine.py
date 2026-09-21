#!/usr/bin/env python3
"""
Backup and Restore Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive backup and restore testing including
database backups, file system backups, configuration backups, disaster recovery,
point-in-time recovery, and backup integrity verification.
"""

import asyncio
import json
import time
import shutil
import subprocess
import hashlib
import gzip
import tarfile
import os
import tempfile
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import psutil

try:
    import psycopg2
    import pymongo
    import redis
except ImportError:
    print("Database drivers optional: pip install psycopg2 pymongo redis")

class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    TRANSACTION_LOG = "transaction_log"
    SNAPSHOT = "snapshot"

class BackupTarget(Enum):
    DATABASE = "database"
    FILESYSTEM = "filesystem"
    CONFIGURATION = "configuration"
    APPLICATION_DATA = "application_data"
    USER_DATA = "user_data"
    LOGS = "logs"
    MEDIA = "media"

class DatabaseType(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    REDIS = "redis"

class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CORRUPTED = "corrupted"
    EXPIRED = "expired"

class RestoreType(Enum):
    FULL_RESTORE = "full_restore"
    POINT_IN_TIME = "point_in_time"
    PARTIAL_RESTORE = "partial_restore"
    TABLE_RESTORE = "table_restore"
    FILE_RESTORE = "file_restore"

class TestSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class BackupConfiguration:
    name: str
    backup_type: BackupType
    target_type: BackupTarget
    source_path: str
    destination_path: str
    compression: bool = True
    encryption: bool = False
    retention_days: int = 30
    schedule: Optional[str] = None
    max_backup_size: Optional[int] = None  # in bytes
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DatabaseBackupConfig:
    db_type: DatabaseType
    connection_params: Dict[str, Any]
    backup_config: BackupConfiguration
    tables: Optional[List[str]] = None
    schema_only: bool = False
    data_only: bool = False

@dataclass
class BackupResult:
    backup_id: str
    config_name: str
    status: BackupStatus
    backup_path: str
    file_size: int = 0
    compressed_size: int = 0
    file_count: int = 0
    checksum: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RestoreResult:
    restore_id: str
    backup_id: str
    status: BackupStatus
    restore_path: str
    restored_items: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: float = 0.0
    verification_passed: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BackupTestCase:
    id: str
    name: str
    description: str
    backup_config: BackupConfiguration
    test_data_setup: Optional[callable] = None
    expected_status: BackupStatus = BackupStatus.COMPLETED
    verify_integrity: bool = True
    test_restore: bool = True
    severity: TestSeverity = TestSeverity.MEDIUM

@dataclass
class BackupRestoreTestResult:
    test_case_id: str
    test_name: str
    status: str
    backup_result: Optional[BackupResult] = None
    restore_result: Optional[RestoreResult] = None
    integrity_check_passed: bool = False
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class FileSystemBackupEngine:
    def __init__(self, base_backup_dir: str):
        self.base_backup_dir = Path(base_backup_dir)
        self.base_backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self, config: BackupConfiguration) -> BackupResult:
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(config.name) % 10000}"
        start_time = datetime.now()
        
        backup_result = BackupResult(
            backup_id=backup_id,
            config_name=config.name,
            status=BackupStatus.RUNNING,
            backup_path="",
            start_time=start_time
        )
        
        try:
            source_path = Path(config.source_path)
            backup_dir = self.base_backup_dir / backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            if config.backup_type == BackupType.FULL:
                backup_path = await self._create_full_backup(source_path, backup_dir, config)
            elif config.backup_type == BackupType.INCREMENTAL:
                backup_path = await self._create_incremental_backup(source_path, backup_dir, config)
            else:
                backup_path = await self._create_full_backup(source_path, backup_dir, config)
            
            backup_result.backup_path = str(backup_path)
            
            if backup_path.exists():
                backup_result.file_size = self._get_directory_size(source_path)
                backup_result.compressed_size = self._get_directory_size(backup_path)
                backup_result.file_count = len(list(source_path.rglob("*"))) if source_path.is_dir() else 1
                backup_result.checksum = await self._calculate_checksum(backup_path)
                backup_result.status = BackupStatus.COMPLETED
            else:
                backup_result.status = BackupStatus.FAILED
                backup_result.error_message = "Backup file not created"
                
        except Exception as e:
            backup_result.status = BackupStatus.FAILED
            backup_result.error_message = str(e)
            logging.error(f"Backup failed: {e}")
        
        finally:
            backup_result.end_time = datetime.now()
            backup_result.duration = (backup_result.end_time - start_time).total_seconds()
        
        return backup_result

    async def _create_full_backup(self, source_path: Path, backup_dir: Path, config: BackupConfiguration) -> Path:
        if config.compression:
            backup_file = backup_dir / f"{config.name}_full.tar.gz"
            
            def create_archive():
                with tarfile.open(backup_file, 'w:gz') as tar:
                    for item in source_path.rglob("*"):
                        if self._should_include_file(item, config):
                            try:
                                arcname = item.relative_to(source_path)
                                tar.add(item, arcname=arcname)
                            except (OSError, ValueError) as e:
                                logging.warning(f"Skipping {item}: {e}")
                                continue
            
            await asyncio.get_event_loop().run_in_executor(None, create_archive)
        else:
            backup_file = backup_dir / f"{config.name}_full"
            backup_file.mkdir(exist_ok=True)
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: shutil.copytree(source_path, backup_file, dirs_exist_ok=True)
            )
        
        return backup_file

    async def _create_incremental_backup(self, source_path: Path, backup_dir: Path, config: BackupConfiguration) -> Path:
        last_backup_time = datetime.now() - timedelta(days=1)
        
        backup_file = backup_dir / f"{config.name}_incremental.tar.gz"
        
        def create_incremental():
            with tarfile.open(backup_file, 'w:gz') as tar:
                for item in source_path.rglob("*"):
                    if (self._should_include_file(item, config) and 
                        item.stat().st_mtime > last_backup_time.timestamp()):
                        try:
                            arcname = item.relative_to(source_path)
                            tar.add(item, arcname=arcname)
                        except (OSError, ValueError) as e:
                            logging.warning(f"Skipping {item}: {e}")
                            continue
        
        await asyncio.get_event_loop().run_in_executor(None, create_incremental)
        return backup_file

    def _should_include_file(self, file_path: Path, config: BackupConfiguration) -> bool:
        file_str = str(file_path)
        
        if config.exclude_patterns:
            for pattern in config.exclude_patterns:
                if pattern in file_str:
                    return False
        
        if config.include_patterns:
            for pattern in config.include_patterns:
                if pattern in file_str:
                    return True
            return False
        
        return True

    def _get_directory_size(self, path: Path) -> int:
        if path.is_file():
            return path.stat().st_size
        
        total_size = 0
        for item in path.rglob("*"):
            try:
                if item.is_file():
                    total_size += item.stat().st_size
            except (OSError, FileNotFoundError):
                continue
        return total_size

    async def _calculate_checksum(self, path: Path) -> str:
        def calculate():
            hasher = hashlib.sha256()
            if path.is_file():
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
            else:
                for item in sorted(path.rglob("*")):
                    if item.is_file():
                        try:
                            with open(item, 'rb') as f:
                                for chunk in iter(lambda: f.read(4096), b""):
                                    hasher.update(chunk)
                        except (OSError, IOError):
                            continue
            return hasher.hexdigest()
        
        return await asyncio.get_event_loop().run_in_executor(None, calculate)

    async def restore_backup(self, backup_result: BackupResult, restore_path: str) -> RestoreResult:
        restore_id = f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        restore_result = RestoreResult(
            restore_id=restore_id,
            backup_id=backup_result.backup_id,
            status=BackupStatus.RUNNING,
            restore_path=restore_path,
            start_time=start_time
        )
        
        try:
            backup_path = Path(backup_result.backup_path)
            restore_target = Path(restore_path)
            restore_target.mkdir(parents=True, exist_ok=True)
            
            if backup_path.suffix == '.gz':
                await self._extract_compressed_backup(backup_path, restore_target)
            else:
                await self._restore_directory_backup(backup_path, restore_target)
            
            restore_result.restored_items = [str(item) for item in restore_target.rglob("*") if item.is_file()]
            restore_result.status = BackupStatus.COMPLETED
            restore_result.verification_passed = await self._verify_restore(backup_result, restore_result)
            
        except Exception as e:
            restore_result.status = BackupStatus.FAILED
            restore_result.error_message = str(e)
            logging.error(f"Restore failed: {e}")
        
        finally:
            restore_result.end_time = datetime.now()
            restore_result.duration = (restore_result.end_time - start_time).total_seconds()
        
        return restore_result

    async def _extract_compressed_backup(self, backup_path: Path, restore_path: Path):
        def extract():
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(path=restore_path)
        
        await asyncio.get_event_loop().run_in_executor(None, extract)

    async def _restore_directory_backup(self, backup_path: Path, restore_path: Path):
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: shutil.copytree(backup_path, restore_path, dirs_exist_ok=True)
        )

    async def _verify_restore(self, backup_result: BackupResult, restore_result: RestoreResult) -> bool:
        try:
            restored_checksum = await self._calculate_checksum(Path(restore_result.restore_path))
            return restored_checksum == backup_result.checksum
        except Exception as e:
            logging.error(f"Restore verification failed: {e}")
            return False

class DatabaseBackupEngine:
    def __init__(self, base_backup_dir: str):
        self.base_backup_dir = Path(base_backup_dir)
        self.base_backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_database_backup(self, db_config: DatabaseBackupConfig) -> BackupResult:
        backup_id = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(db_config.backup_config.name) % 10000}"
        start_time = datetime.now()
        
        backup_result = BackupResult(
            backup_id=backup_id,
            config_name=db_config.backup_config.name,
            status=BackupStatus.RUNNING,
            backup_path="",
            start_time=start_time
        )
        
        try:
            backup_path = self.base_backup_dir / f"{backup_id}.sql"
            
            if db_config.db_type == DatabaseType.POSTGRESQL:
                await self._backup_postgresql(db_config, backup_path)
            elif db_config.db_type == DatabaseType.MYSQL:
                await self._backup_mysql(db_config, backup_path)
            elif db_config.db_type == DatabaseType.SQLITE:
                await self._backup_sqlite(db_config, backup_path)
            elif db_config.db_type == DatabaseType.MONGODB:
                await self._backup_mongodb(db_config, backup_path)
            else:
                raise ValueError(f"Unsupported database type: {db_config.db_type}")
            
            backup_result.backup_path = str(backup_path)
            
            if backup_path.exists():
                backup_result.file_size = backup_path.stat().st_size
                backup_result.compressed_size = backup_result.file_size
                backup_result.checksum = await self._calculate_file_checksum(backup_path)
                backup_result.status = BackupStatus.COMPLETED
            else:
                backup_result.status = BackupStatus.FAILED
                backup_result.error_message = "Backup file not created"
                
        except Exception as e:
            backup_result.status = BackupStatus.FAILED
            backup_result.error_message = str(e)
            logging.error(f"Database backup failed: {e}")
        
        finally:
            backup_result.end_time = datetime.now()
            backup_result.duration = (backup_result.end_time - start_time).total_seconds()
        
        return backup_result

    async def _backup_postgresql(self, db_config: DatabaseBackupConfig, backup_path: Path):
        conn_params = db_config.connection_params
        
        cmd = [
            'pg_dump',
            f"--host={conn_params.get('host', 'localhost')}",
            f"--port={conn_params.get('port', 5432)}",
            f"--username={conn_params.get('user', 'postgres')}",
            f"--dbname={conn_params.get('database')}",
            '--no-password',
            f"--file={backup_path}"
        ]
        
        if db_config.schema_only:
            cmd.append('--schema-only')
        elif db_config.data_only:
            cmd.append('--data-only')
        
        if db_config.tables:
            for table in db_config.tables:
                cmd.extend(['--table', table])
        
        env = os.environ.copy()
        env['PGPASSWORD'] = conn_params.get('password', '')
        
        process = await asyncio.create_subprocess_exec(
            *cmd, env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"pg_dump failed: {stderr.decode()}")

    async def _backup_mysql(self, db_config: DatabaseBackupConfig, backup_path: Path):
        conn_params = db_config.connection_params
        
        cmd = [
            'mysqldump',
            f"--host={conn_params.get('host', 'localhost')}",
            f"--port={conn_params.get('port', 3306)}",
            f"--user={conn_params.get('user', 'root')}",
            f"--password={conn_params.get('password', '')}",
            '--single-transaction',
            '--routines',
            '--triggers'
        ]
        
        if db_config.schema_only:
            cmd.append('--no-data')
        elif db_config.data_only:
            cmd.append('--no-create-info')
        
        cmd.append(conn_params.get('database'))
        
        if db_config.tables:
            cmd.extend(db_config.tables)
        
        with open(backup_path, 'w') as f:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=f, stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"mysqldump failed: {stderr.decode()}")

    async def _backup_sqlite(self, db_config: DatabaseBackupConfig, backup_path: Path):
        conn_params = db_config.connection_params
        db_path = conn_params.get('database')
        
        def backup_sqlite():
            source_conn = sqlite3.connect(db_path)
            backup_conn = sqlite3.connect(str(backup_path))
            
            source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
        
        await asyncio.get_event_loop().run_in_executor(None, backup_sqlite)

    async def _backup_mongodb(self, db_config: DatabaseBackupConfig, backup_path: Path):
        conn_params = db_config.connection_params
        
        cmd = [
            'mongodump',
            '--host', f"{conn_params.get('host', 'localhost')}:{conn_params.get('port', 27017)}",
            '--db', conn_params.get('database'),
            '--out', str(backup_path.parent / f"{backup_path.stem}_mongo")
        ]
        
        if conn_params.get('username'):
            cmd.extend(['--username', conn_params['username']])
            cmd.extend(['--password', conn_params.get('password', '')])
        
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"mongodump failed: {stderr.decode()}")

    async def _calculate_file_checksum(self, file_path: Path) -> str:
        def calculate():
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        
        return await asyncio.get_event_loop().run_in_executor(None, calculate)

class BackupRestoreTestingEngine:
    def __init__(self, test_data_dir: str = "test_data", backup_dir: str = "test_backups", results_dir: str = "backup_results"):
        self.test_data_dir = Path(test_data_dir)
        self.backup_dir = Path(backup_dir)
        self.results_dir = Path(results_dir)
        
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.fs_backup_engine = FileSystemBackupEngine(str(self.backup_dir / "filesystem"))
        self.db_backup_engine = DatabaseBackupEngine(str(self.backup_dir / "database"))
        
        self.test_cases = self._create_test_cases()

    def _create_test_cases(self) -> List[BackupTestCase]:
        test_cases = []
        
        small_files_config = BackupConfiguration(
            name="small_files_backup",
            backup_type=BackupType.FULL,
            target_type=BackupTarget.APPLICATION_DATA,
            source_path=str(self.test_data_dir / "small_files"),
            destination_path=str(self.backup_dir / "small_files"),
            compression=True,
            retention_days=7
        )
        
        large_files_config = BackupConfiguration(
            name="large_files_backup",
            backup_type=BackupType.FULL,
            target_type=BackupTarget.USER_DATA,
            source_path=str(self.test_data_dir / "large_files"),
            destination_path=str(self.backup_dir / "large_files"),
            compression=True,
            retention_days=30
        )
        
        incremental_config = BackupConfiguration(
            name="incremental_backup",
            backup_type=BackupType.INCREMENTAL,
            target_type=BackupTarget.APPLICATION_DATA,
            source_path=str(self.test_data_dir / "incremental_test"),
            destination_path=str(self.backup_dir / "incremental"),
            compression=True,
            retention_days=7
        )
        
        config_backup_config = BackupConfiguration(
            name="config_backup",
            backup_type=BackupType.FULL,
            target_type=BackupTarget.CONFIGURATION,
            source_path=str(self.test_data_dir / "config"),
            destination_path=str(self.backup_dir / "config"),
            compression=False,
            retention_days=90,
            include_patterns=[".conf", ".json", ".yaml", ".xml"]
        )
        
        test_cases.extend([
            BackupTestCase(
                id="small_files_test",
                name="Small Files Backup Test",
                description="Test backup of small configuration and data files",
                backup_config=small_files_config,
                test_data_setup=self._setup_small_files_test_data,
                severity=TestSeverity.MEDIUM
            ),
            BackupTestCase(
                id="large_files_test",
                name="Large Files Backup Test", 
                description="Test backup of large media and data files",
                backup_config=large_files_config,
                test_data_setup=self._setup_large_files_test_data,
                severity=TestSeverity.HIGH
            ),
            BackupTestCase(
                id="incremental_backup_test",
                name="Incremental Backup Test",
                description="Test incremental backup functionality",
                backup_config=incremental_config,
                test_data_setup=self._setup_incremental_test_data,
                severity=TestSeverity.HIGH
            ),
            BackupTestCase(
                id="config_backup_test",
                name="Configuration Backup Test",
                description="Test backup of application configuration files",
                backup_config=config_backup_config,
                test_data_setup=self._setup_config_test_data,
                severity=TestSeverity.CRITICAL
            )
        ])
        
        return test_cases

    def _setup_small_files_test_data(self):
        test_dir = self.test_data_dir / "small_files"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(100):
            file_path = test_dir / f"test_file_{i:03d}.txt"
            with open(file_path, 'w') as f:
                f.write(f"Test content for file {i}\n" * 10)
        
        (test_dir / "subdir").mkdir(exist_ok=True)
        for i in range(20):
            file_path = test_dir / "subdir" / f"sub_file_{i:02d}.json"
            with open(file_path, 'w') as f:
                json.dump({"id": i, "data": f"test data {i}"}, f)

    def _setup_large_files_test_data(self):
        test_dir = self.test_data_dir / "large_files"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(5):
            file_path = test_dir / f"large_file_{i}.dat"
            with open(file_path, 'wb') as f:
                data = b"0" * (10 * 1024 * 1024)  # 10MB file
                f.write(data)

    def _setup_incremental_test_data(self):
        test_dir = self.test_data_dir / "incremental_test"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        for i in range(50):
            file_path = test_dir / f"incremental_file_{i:02d}.txt"
            with open(file_path, 'w') as f:
                f.write(f"Initial content for file {i}\n" * 5)

    def _setup_config_test_data(self):
        test_dir = self.test_data_dir / "config"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        configs = {
            "app.conf": "[database]\nhost=localhost\nport=5432\n",
            "settings.json": json.dumps({"debug": True, "port": 8080}),
            "config.yaml": "database:\n  host: localhost\n  port: 5432\n",
            "service.xml": "<?xml version='1.0'?><config><port>8080</port></config>"
        }
        
        for filename, content in configs.items():
            with open(test_dir / filename, 'w') as f:
                f.write(content)

    async def run_backup_restore_test(self, test_case: BackupTestCase) -> BackupRestoreTestResult:
        start_time = time.time()
        
        result = BackupRestoreTestResult(
            test_case_id=test_case.id,
            test_name=test_case.name,
            status="pending"
        )
        
        try:
            if test_case.test_data_setup:
                test_case.test_data_setup()
            
            backup_start = time.time()
            backup_result = await self.fs_backup_engine.create_backup(test_case.backup_config)
            backup_time = time.time() - backup_start
            
            result.backup_result = backup_result
            result.performance_metrics["backup_time"] = backup_time
            
            if backup_result.status == BackupStatus.COMPLETED:
                if test_case.verify_integrity:
                    integrity_check_start = time.time()
                    result.integrity_check_passed = await self._verify_backup_integrity(backup_result)
                    integrity_check_time = time.time() - integrity_check_start
                    result.performance_metrics["integrity_check_time"] = integrity_check_time
                    
                    if not result.integrity_check_passed:
                        result.issues_found.append("Backup integrity verification failed")
                
                if test_case.test_restore:
                    restore_path = self.test_data_dir / "restore_test" / test_case.id
                    restore_path.mkdir(parents=True, exist_ok=True)
                    
                    restore_start = time.time()
                    restore_result = await self.fs_backup_engine.restore_backup(
                        backup_result, str(restore_path)
                    )
                    restore_time = time.time() - restore_start
                    
                    result.restore_result = restore_result
                    result.performance_metrics["restore_time"] = restore_time
                    
                    if restore_result.status != BackupStatus.COMPLETED:
                        result.issues_found.append(f"Restore failed: {restore_result.error_message}")
                    
                    if not restore_result.verification_passed:
                        result.issues_found.append("Restore verification failed")
                
                if backup_result.status == test_case.expected_status and not result.issues_found:
                    result.status = "passed"
                else:
                    result.status = "failed"
            else:
                result.status = "failed"
                result.issues_found.append(f"Backup failed: {backup_result.error_message}")
                
        except Exception as e:
            result.status = "failed"
            result.issues_found.append(f"Test execution error: {str(e)}")
            logging.error(f"Backup/restore test failed: {e}")
        
        finally:
            result.execution_time = time.time() - start_time
        
        return result

    async def _verify_backup_integrity(self, backup_result: BackupResult) -> bool:
        try:
            backup_path = Path(backup_result.backup_path)
            
            if not backup_path.exists():
                return False
            
            if backup_path.suffix == '.gz':
                try:
                    with tarfile.open(backup_path, 'r:gz') as tar:
                        members = tar.getmembers()
                        if not members:
                            return False
                        
                        for member in members[:5]:
                            if member.isfile():
                                try:
                                    tar.extractfile(member).read(1024)
                                except Exception:
                                    return False
                except tarfile.TarError:
                    return False
            
            current_checksum = await self.fs_backup_engine._calculate_checksum(backup_path)
            return current_checksum == backup_result.checksum
            
        except Exception as e:
            logging.error(f"Integrity verification error: {e}")
            return False

    async def run_backup_test_suite(self, test_case_ids: List[str] = None) -> Dict[str, Any]:
        test_cases_to_run = self.test_cases
        if test_case_ids:
            test_cases_to_run = [tc for tc in self.test_cases if tc.id in test_case_ids]
        
        results = []
        
        for test_case in test_cases_to_run:
            print(f"Running backup test: {test_case.name}")
            result = await self.run_backup_restore_test(test_case)
            results.append(result)
            
            await asyncio.sleep(1)
        
        return {
            "results": results,
            "summary": self._generate_test_summary(results)
        }

    def _generate_test_summary(self, results: List[BackupRestoreTestResult]) -> Dict[str, Any]:
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == "passed"])
        failed_tests = len([r for r in results if r.status == "failed"])
        
        total_backup_time = sum(r.performance_metrics.get("backup_time", 0) for r in results)
        total_restore_time = sum(r.performance_metrics.get("restore_time", 0) for r in results)
        
        avg_backup_time = total_backup_time / total_tests if total_tests > 0 else 0
        avg_restore_time = total_restore_time / total_tests if total_tests > 0 else 0
        
        total_backup_size = sum(
            r.backup_result.compressed_size for r in results 
            if r.backup_result and r.backup_result.compressed_size
        )
        
        all_issues = []
        for result in results:
            all_issues.extend(result.issues_found)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "total_backup_time": total_backup_time,
            "total_restore_time": total_restore_time,
            "average_backup_time": avg_backup_time,
            "average_restore_time": avg_restore_time,
            "total_backup_size_mb": total_backup_size / (1024 * 1024),
            "unique_issues": list(set(all_issues)),
            "total_issues": len(all_issues),
            "integrity_checks_passed": len([
                r for r in results 
                if r.integrity_check_passed
            ])
        }

    def generate_backup_report(self, test_results: Dict[str, Any], output_path: str):
        results = test_results["results"]
        summary = test_results["summary"]
        
        report = {
            "test_summary": {
                "total_tests": summary["total_tests"],
                "passed_tests": summary["passed_tests"],
                "failed_tests": summary["failed_tests"],
                "pass_rate": summary["pass_rate"],
                "timestamp": datetime.now().isoformat()
            },
            "performance_metrics": {
                "total_backup_time": summary["total_backup_time"],
                "total_restore_time": summary["total_restore_time"],
                "average_backup_time": summary["average_backup_time"],
                "average_restore_time": summary["average_restore_time"],
                "total_backup_size_mb": summary["total_backup_size_mb"]
            },
            "reliability_metrics": {
                "integrity_checks_passed": summary["integrity_checks_passed"],
                "unique_issues": summary["unique_issues"],
                "total_issues": summary["total_issues"]
            },
            "detailed_results": []
        }
        
        for result in results:
            test_data = {
                "test_case_id": result.test_case_id,
                "test_name": result.test_name,
                "status": result.status,
                "execution_time": result.execution_time,
                "integrity_check_passed": result.integrity_check_passed,
                "performance_metrics": result.performance_metrics,
                "issues_found": result.issues_found,
                "backup_result": {
                    "backup_id": result.backup_result.backup_id if result.backup_result else None,
                    "status": result.backup_result.status.value if result.backup_result else None,
                    "file_size_mb": (result.backup_result.file_size / (1024 * 1024)) if result.backup_result else 0,
                    "compressed_size_mb": (result.backup_result.compressed_size / (1024 * 1024)) if result.backup_result else 0,
                    "compression_ratio": (
                        (1 - result.backup_result.compressed_size / result.backup_result.file_size) * 100
                        if result.backup_result and result.backup_result.file_size > 0
                        else 0
                    ),
                    "duration": result.backup_result.duration if result.backup_result else 0,
                    "checksum": result.backup_result.checksum if result.backup_result else None
                } if result.backup_result else None,
                "restore_result": {
                    "restore_id": result.restore_result.restore_id if result.restore_result else None,
                    "status": result.restore_result.status.value if result.restore_result else None,
                    "restored_items_count": len(result.restore_result.restored_items) if result.restore_result else 0,
                    "duration": result.restore_result.duration if result.restore_result else 0,
                    "verification_passed": result.restore_result.verification_passed if result.restore_result else False
                } if result.restore_result else None
            }
            
            report["detailed_results"].append(test_data)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        html_report_path = output_path.replace('.json', '.html')
        self.generate_html_report(report, html_report_path)

    def generate_html_report(self, report_data: Dict[str, Any], output_path: str):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Backup & Restore Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #17a2b8; color: white; border-radius: 6px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .performance-section {{ background: #e8f4fd; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .reliability-section {{ background: #f0f8e8; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .test-results {{ margin-bottom: 30px; }}
                .test-item {{ background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .test-item.failed {{ border-left-color: #dc3545; }}
                .test-item.pending {{ border-left-color: #ffc107; }}
                .test-details {{ margin-top: 15px; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
                .detail-section {{ background: white; padding: 10px; border-radius: 4px; }}
                .backup-result {{ background: #e8f5e8; padding: 10px; border-radius: 4px; }}
                .backup-result.failed {{ background: #f8d7da; }}
                .restore-result {{ background: #e3f2fd; padding: 10px; border-radius: 4px; }}
                .restore-result.failed {{ background: #f8d7da; }}
                .performance-metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
                .metric {{ background: white; padding: 8px; border-radius: 4px; text-align: center; }}
                .issues-list {{ list-style-type: none; padding: 0; }}
                .issue-item {{ background: #f8d7da; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #dc3545; }}
                .compression-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 5px 0; }}
                .compression-fill {{ height: 100%; background: #28a745; }}
                .status-badge {{ padding: 4px 8px; border-radius: 12px; color: white; font-weight: bold; }}
                .status-passed {{ background: #28a745; }}
                .status-failed {{ background: #dc3545; }}
                .status-pending {{ background: #ffc107; color: #212529; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💾 Backup & Restore Test Report</h1>
                    <p>Comprehensive Backup and Recovery Testing Results</p>
                    <p>Generated on {report_data['test_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Tests</h3>
                        <div class="value">{report_data['test_summary']['total_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Passed Tests</h3>
                        <div class="value" style="color: #28a745;">{report_data['test_summary']['passed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Failed Tests</h3>
                        <div class="value" style="color: #dc3545;">{report_data['test_summary']['failed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Pass Rate</h3>
                        <div class="value" style="color: {'#28a745' if report_data['test_summary']['pass_rate'] >= 80 else '#dc3545'}">{report_data['test_summary']['pass_rate']:.1f}%</div>
                    </div>
                </div>
                
                <div class="performance-section">
                    <h3>⚡ Performance Metrics</h3>
                    <div class="performance-metrics">
                        <div class="metric">
                            <strong>Total Backup Time</strong><br>
                            {report_data['performance_metrics']['total_backup_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Total Restore Time</strong><br>
                            {report_data['performance_metrics']['total_restore_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Avg Backup Time</strong><br>
                            {report_data['performance_metrics']['average_backup_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Avg Restore Time</strong><br>
                            {report_data['performance_metrics']['average_restore_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Total Backup Size</strong><br>
                            {report_data['performance_metrics']['total_backup_size_mb']:.2f} MB
                        </div>
                    </div>
                </div>
                
                <div class="reliability-section">
                    <h3>🔒 Reliability Metrics</h3>
                    <p><strong>Integrity Checks Passed:</strong> {report_data['reliability_metrics']['integrity_checks_passed']}</p>
                    <p><strong>Total Issues Found:</strong> {report_data['reliability_metrics']['total_issues']}</p>
        """
        
        if report_data['reliability_metrics']['unique_issues']:
            html_content += "<h4>Issues Summary:</h4><ul class='issues-list'>"
            for issue in report_data['reliability_metrics']['unique_issues']:
                html_content += f"<li class='issue-item'>{issue}</li>"
            html_content += "</ul>"
        
        html_content += """
                </div>
                
                <div class="test-results">
                    <h3>📊 Detailed Test Results</h3>
        """
        
        for test in report_data['detailed_results']:
            status_class = test['status']
            html_content += f"""
                    <div class="test-item {status_class}">
                        <h4>{test['test_name']} ({test['test_case_id']}) <span class="status-badge status-{status_class}">{test['status'].upper()}</span></h4>
                        <p><strong>Execution Time:</strong> {test['execution_time']:.2f}s | <strong>Integrity Check:</strong> {'✅ PASSED' if test['integrity_check_passed'] else '❌ FAILED'}</p>
                        
                        <div class="test-details">
            """
            
            if test['backup_result']:
                backup = test['backup_result']
                backup_class = 'failed' if backup['status'] != 'completed' else ''
                compression_percent = backup['compression_ratio']
                
                html_content += f"""
                            <div class="detail-section">
                                <h5>Backup Result</h5>
                                <div class="backup-result {backup_class}">
                                    <strong>Backup ID:</strong> {backup['backup_id'] or 'N/A'}<br>
                                    <strong>Status:</strong> {backup['status'] or 'N/A'}<br>
                                    <strong>Original Size:</strong> {backup['file_size_mb']:.2f} MB<br>
                                    <strong>Compressed Size:</strong> {backup['compressed_size_mb']:.2f} MB<br>
                                    <strong>Compression:</strong> {compression_percent:.1f}%
                                    <div class="compression-bar">
                                        <div class="compression-fill" style="width: {compression_percent}%;"></div>
                                    </div>
                                    <strong>Duration:</strong> {backup['duration']:.2f}s<br>
                                    <strong>Checksum:</strong> {backup['checksum'][:16] + '...' if backup['checksum'] else 'N/A'}
                                </div>
                            </div>
                """
            
            if test['restore_result']:
                restore = test['restore_result']
                restore_class = 'failed' if restore['status'] != 'completed' else ''
                
                html_content += f"""
                            <div class="detail-section">
                                <h5>Restore Result</h5>
                                <div class="restore-result {restore_class}">
                                    <strong>Restore ID:</strong> {restore['restore_id'] or 'N/A'}<br>
                                    <strong>Status:</strong> {restore['status'] or 'N/A'}<br>
                                    <strong>Items Restored:</strong> {restore['restored_items_count']}<br>
                                    <strong>Duration:</strong> {restore['duration']:.2f}s<br>
                                    <strong>Verification:</strong> {'✅ PASSED' if restore['verification_passed'] else '❌ FAILED'}
                                </div>
                            </div>
                """
            
            html_content += f"""
                            <div class="detail-section">
                                <h5>Performance Metrics</h5>
                                <div class="performance-metrics">
            """
            
            for metric, value in test['performance_metrics'].items():
                html_content += f"""
                                    <div class="metric">
                                        <strong>{metric.replace('_', ' ').title()}</strong><br>
                                        {value:.2f}s
                                    </div>
                """
            
            html_content += "</div></div>"
            
            if test['issues_found']:
                html_content += """
                            <div class="detail-section">
                                <h5>Issues Found</h5>
                                <ul class="issues-list">
                """
                for issue in test['issues_found']:
                    html_content += f"<li class='issue-item'>{issue}</li>"
                html_content += "</ul></div>"
            
            html_content += "</div></div>"
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

    async def run_comprehensive_backup_test(self) -> Dict[str, Any]:
        print("Starting comprehensive backup and restore testing...")
        
        test_results = await self.run_backup_test_suite()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"backup_restore_report_{timestamp}.json"
        
        self.generate_backup_report(test_results, str(report_path))
        
        return {
            "test_results": test_results,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html'),
            "summary": test_results["summary"]
        }

async def main():
    engine = BackupRestoreTestingEngine()
    
    print("Running comprehensive backup and restore tests...")
    results = await engine.run_comprehensive_backup_test()
    
    print(f"Backup/restore testing completed!")
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed tests: {results['summary']['passed_tests']}")
    print(f"Failed tests: {results['summary']['failed_tests']}")
    print(f"Pass rate: {results['summary']['pass_rate']:.1f}%")
    print(f"Total backup time: {results['summary']['total_backup_time']:.2f}s")
    print(f"Total restore time: {results['summary']['total_restore_time']:.2f}s")
    print(f"Total backup size: {results['summary']['total_backup_size_mb']:.2f} MB")
    print(f"Integrity checks passed: {results['summary']['integrity_checks_passed']}")
    print(f"Issues found: {results['summary']['total_issues']}")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())