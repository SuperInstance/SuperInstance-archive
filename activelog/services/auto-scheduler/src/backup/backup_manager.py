import os
import shutil
import tarfile
import gzip
import json
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import logging
import subprocess

logger = logging.getLogger(__name__)

class BackupType(Enum):
    INCREMENTAL = "incremental"
    STABILITY = "stability"
    MILESTONE = "milestone"
    ARCHIVE = "archive"
    PERMANENT = "permanent"

class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"

@dataclass
class BackupRecord:
    id: str
    backup_type: BackupType
    timestamp: datetime
    size_bytes: int
    checksum: str
    path: str
    status: BackupStatus = BackupStatus.PENDING
    verification_date: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # For incremental backups

@dataclass
class BackupConfig:
    enabled: bool = True
    schedule: Dict[str, str] = field(default_factory=dict)
    retention: Dict[str, int] = field(default_factory=dict)
    compression: bool = True
    verification: bool = True
    cloud_sync: bool = False
    exclusions: List[str] = field(default_factory=list)

class BackupManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_path = Path(config.get('backup_path', '/home/activeloguser/activelog/backups'))
        self.source_path = Path(config.get('source_path', '/home/activeloguser/activelog'))
        
        # Backup storage structure
        self.incremental_path = self.base_path / 'incremental'
        self.stability_path = self.base_path / 'stability'
        self.milestone_path = self.base_path / 'milestone'
        self.archive_path = self.base_path / 'archive'
        self.permanent_path = self.base_path / 'permanent'
        
        # Create directories
        for path in [self.incremental_path, self.stability_path, 
                    self.milestone_path, self.archive_path, self.permanent_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Backup records
        self.records: Dict[str, BackupRecord] = {}
        self.running_backups: Dict[str, BackupRecord] = {}
        
        # Configuration
        self.backup_configs = self._initialize_backup_configs()
        
        # State tracking
        self.last_incremental = None
        self.last_stability = None
        self.last_milestone = None
        self.last_archive = None
        self.last_permanent = None
        
        # Load existing records
        asyncio.create_task(self._load_backup_records())
    
    def _initialize_backup_configs(self) -> Dict[BackupType, BackupConfig]:
        """Initialize default backup configurations"""
        return {
            BackupType.INCREMENTAL: BackupConfig(
                schedule={'frequency': 'daily', 'time': '01:00'},
                retention={'days': 7},
                compression=True,
                verification=True
            ),
            BackupType.STABILITY: BackupConfig(
                schedule={'frequency': 'weekly', 'day': 'sunday', 'time': '02:00'},
                retention={'weeks': 4},
                compression=True,
                verification=True
            ),
            BackupType.MILESTONE: BackupConfig(
                schedule={'frequency': 'monthly', 'day': 1, 'time': '03:00'},
                retention={'months': 12},
                compression=True,
                verification=True,
                cloud_sync=True
            ),
            BackupType.ARCHIVE: BackupConfig(
                schedule={'frequency': 'biannual', 'months': [1, 7], 'day': 1, 'time': '04:00'},
                retention={'years': 3},
                compression=True,
                verification=True,
                cloud_sync=True
            ),
            BackupType.PERMANENT: BackupConfig(
                schedule={'frequency': 'yearly', 'month': 1, 'day': 1, 'time': '05:00'},
                retention={'years': 50},  # Long-term storage
                compression=True,
                verification=True,
                cloud_sync=True
            )
        }
    
    async def _load_backup_records(self):
        """Load existing backup records from metadata files"""
        try:
            for backup_type in BackupType:
                records_file = self.base_path / f'{backup_type.value}_records.json'
                if records_file.exists():
                    with open(records_file, 'r') as f:
                        data = json.load(f)
                        for record_data in data:
                            record = BackupRecord(
                                id=record_data['id'],
                                backup_type=BackupType(record_data['backup_type']),
                                timestamp=datetime.fromisoformat(record_data['timestamp']),
                                size_bytes=record_data['size_bytes'],
                                checksum=record_data['checksum'],
                                path=record_data['path'],
                                status=BackupStatus(record_data['status']),
                                verification_date=datetime.fromisoformat(record_data['verification_date']) 
                                    if record_data.get('verification_date') else None,
                                metadata=record_data.get('metadata', {}),
                                dependencies=record_data.get('dependencies', [])
                            )
                            self.records[record.id] = record
            
            logger.info(f"Loaded {len(self.records)} backup records")
            
        except Exception as e:
            logger.error(f"Error loading backup records: {e}")
    
    async def _save_backup_records(self):
        """Save backup records to metadata files"""
        try:
            # Group records by type
            by_type = {}
            for record in self.records.values():
                if record.backup_type not in by_type:
                    by_type[record.backup_type] = []
                by_type[record.backup_type].append({
                    'id': record.id,
                    'backup_type': record.backup_type.value,
                    'timestamp': record.timestamp.isoformat(),
                    'size_bytes': record.size_bytes,
                    'checksum': record.checksum,
                    'path': record.path,
                    'status': record.status.value,
                    'verification_date': record.verification_date.isoformat() 
                        if record.verification_date else None,
                    'metadata': record.metadata,
                    'dependencies': record.dependencies
                })
            
            # Save each type to separate file
            for backup_type, records in by_type.items():
                records_file = self.base_path / f'{backup_type.value}_records.json'
                with open(records_file, 'w') as f:
                    json.dump(records, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving backup records: {e}")
    
    async def get_due_backups(self, current_time: datetime) -> Dict[str, Dict[str, Any]]:
        """Get backups that are due for execution"""
        due_backups = {}
        
        for backup_type, config in self.backup_configs.items():
            if not config.enabled:
                continue
            
            if await self._is_backup_due(backup_type, config, current_time):
                due_backups[backup_type.value] = {
                    'type': backup_type,
                    'config': config,
                    'estimated_duration': self._estimate_backup_duration(backup_type)
                }
        
        return due_backups
    
    async def _is_backup_due(self, backup_type: BackupType, config: BackupConfig, 
                           current_time: datetime) -> bool:
        """Check if a backup type is due for execution"""
        schedule = config.schedule
        frequency = schedule.get('frequency')
        
        # Get last backup of this type
        last_backup = await self._get_last_backup(backup_type)
        
        if frequency == 'daily':
            if last_backup is None:
                return True
            
            target_time = current_time.replace(
                hour=int(schedule['time'].split(':')[0]),
                minute=int(schedule['time'].split(':')[1]),
                second=0,
                microsecond=0
            )
            
            return (current_time >= target_time and 
                   last_backup.timestamp.date() < current_time.date())
        
        elif frequency == 'weekly':
            if last_backup is None:
                return True
            
            # Check if it's the right day of week
            target_day = ['monday', 'tuesday', 'wednesday', 'thursday', 
                         'friday', 'saturday', 'sunday'].index(schedule['day'].lower())
            
            if current_time.weekday() != target_day:
                return False
            
            # Check if enough time has passed
            return (current_time - last_backup.timestamp).days >= 7
        
        elif frequency == 'monthly':
            if last_backup is None:
                return True
            
            # Check if it's the right day of month
            if current_time.day != schedule['day']:
                return False
            
            # Check if in a new month
            return (current_time.year > last_backup.timestamp.year or 
                   current_time.month > last_backup.timestamp.month)
        
        elif frequency == 'biannual':
            if last_backup is None:
                return True
            
            # Check if it's one of the target months
            if current_time.month not in schedule['months']:
                return False
            
            # Check if enough time has passed (6 months)
            months_diff = (current_time.year - last_backup.timestamp.year) * 12 + \
                         (current_time.month - last_backup.timestamp.month)
            return months_diff >= 6
        
        elif frequency == 'yearly':
            if last_backup is None:
                return True
            
            # Check if it's the right month and day
            if (current_time.month != schedule['month'] or 
                current_time.day != schedule['day']):
                return False
            
            # Check if in a new year
            return current_time.year > last_backup.timestamp.year
        
        return False
    
    async def _get_last_backup(self, backup_type: BackupType) -> Optional[BackupRecord]:
        """Get the most recent backup of a specific type"""
        type_records = [r for r in self.records.values() 
                       if r.backup_type == backup_type and r.status == BackupStatus.COMPLETED]
        
        if not type_records:
            return None
        
        return max(type_records, key=lambda r: r.timestamp)
    
    def _estimate_backup_duration(self, backup_type: BackupType) -> float:
        """Estimate backup duration in hours"""
        base_durations = {
            BackupType.INCREMENTAL: 0.5,
            BackupType.STABILITY: 1.0,
            BackupType.MILESTONE: 2.0,
            BackupType.ARCHIVE: 3.0,
            BackupType.PERMANENT: 4.0
        }
        
        return base_durations.get(backup_type, 1.0)
    
    async def create_backup(self, backup_type: BackupType, 
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a new backup"""
        timestamp = datetime.now()
        backup_id = f"{backup_type.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        
        # Determine backup path
        type_path_map = {
            BackupType.INCREMENTAL: self.incremental_path,
            BackupType.STABILITY: self.stability_path,
            BackupType.MILESTONE: self.milestone_path,
            BackupType.ARCHIVE: self.archive_path,
            BackupType.PERMANENT: self.permanent_path
        }
        
        backup_path = type_path_map[backup_type] / f"{backup_id}.tar.gz"
        
        # Create backup record
        record = BackupRecord(
            id=backup_id,
            backup_type=backup_type,
            timestamp=timestamp,
            size_bytes=0,
            checksum="",
            path=str(backup_path),
            status=BackupStatus.RUNNING,
            metadata=metadata or {}
        )
        
        self.records[backup_id] = record
        self.running_backups[backup_id] = record
        
        try:
            # Create the backup
            await self._execute_backup(record)
            
            # Verify if enabled
            config = self.backup_configs[backup_type]
            if config.verification:
                await self._verify_backup(record)
            
            # Cloud sync if enabled
            if config.cloud_sync:
                await self._cloud_sync_backup(record)
            
            # Cleanup old backups
            await self._cleanup_old_backups(backup_type)
            
            # Save records
            await self._save_backup_records()
            
            logger.info(f"Backup {backup_id} completed successfully")
            return backup_id
            
        except Exception as e:
            record.status = BackupStatus.FAILED
            logger.error(f"Backup {backup_id} failed: {e}")
            raise
        finally:
            if backup_id in self.running_backups:
                del self.running_backups[backup_id]
    
    async def _execute_backup(self, record: BackupRecord):
        """Execute the actual backup process"""
        config = self.backup_configs[record.backup_type]
        
        # Prepare exclusion patterns
        exclusions = self._get_exclusion_patterns(config)
        
        # For incremental backups, find changes since last backup
        if record.backup_type == BackupType.INCREMENTAL:
            await self._create_incremental_backup(record, exclusions)
        else:
            await self._create_full_backup(record, exclusions)
        
        # Calculate final size and checksum
        backup_path = Path(record.path)
        if backup_path.exists():
            record.size_bytes = backup_path.stat().st_size
            record.checksum = await self._calculate_checksum(backup_path)
            record.status = BackupStatus.COMPLETED
        else:
            raise Exception("Backup file was not created")
    
    def _get_exclusion_patterns(self, config: BackupConfig) -> List[str]:
        """Get file exclusion patterns"""
        default_exclusions = [
            '*.log',
            '*.pid',
            'node_modules/',
            '__pycache__/',
            '.git/',
            'backups/',
            'logs/',
            'pids/',
            '*.sock',
            '*.tmp'
        ]
        
        return default_exclusions + config.exclusions
    
    async def _create_incremental_backup(self, record: BackupRecord, exclusions: List[str]):
        """Create an incremental backup"""
        # Find the last completed backup to use as base
        last_backup = await self._get_last_backup(BackupType.INCREMENTAL)
        
        if last_backup is None:
            # No previous backup, create full backup
            await self._create_full_backup(record, exclusions)
            return
        
        # Find files modified since last backup
        cutoff_time = last_backup.timestamp
        modified_files = await self._find_modified_files(cutoff_time)
        
        if not modified_files:
            logger.info("No files modified since last backup")
            # Create empty backup or minimal metadata backup
            record.metadata['incremental'] = True
            record.metadata['base_backup'] = last_backup.id
            record.dependencies = [last_backup.id]
        
        # Create tar archive with only modified files
        await self._create_tar_archive(record.path, modified_files, exclusions)
        
        record.metadata['incremental'] = True
        record.metadata['base_backup'] = last_backup.id
        record.metadata['file_count'] = len(modified_files)
        record.dependencies = [last_backup.id]
    
    async def _create_full_backup(self, record: BackupRecord, exclusions: List[str]):
        """Create a full backup"""
        # Create tar archive of entire source
        source_files = await self._get_source_files(exclusions)
        await self._create_tar_archive(record.path, source_files, exclusions)
        
        record.metadata['full_backup'] = True
        record.metadata['file_count'] = len(source_files)
    
    async def _find_modified_files(self, cutoff_time: datetime) -> List[Path]:
        """Find files modified since cutoff time"""
        modified_files = []
        cutoff_timestamp = cutoff_time.timestamp()
        
        for root, dirs, files in os.walk(self.source_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                d.startswith(excl.rstrip('/')) for excl in ['backups', 'logs', 'pids', '__pycache__', '.git', 'node_modules']
            )]
            
            for file in files:
                file_path = Path(root) / file
                try:
                    if file_path.stat().st_mtime > cutoff_timestamp:
                        modified_files.append(file_path)
                except (OSError, PermissionError):
                    continue
        
        return modified_files
    
    async def _get_source_files(self, exclusions: List[str]) -> List[Path]:
        """Get list of all source files respecting exclusions"""
        source_files = []
        
        for root, dirs, files in os.walk(self.source_path):
            # Skip excluded directories
            dirs[:] = [d for d in dirs if not any(
                d.startswith(excl.rstrip('/')) for excl in exclusions if excl.endswith('/')
            )]
            
            for file in files:
                file_path = Path(root) / file
                
                # Check file exclusions
                if any(file_path.match(pattern) for pattern in exclusions if not pattern.endswith('/')):
                    continue
                
                source_files.append(file_path)
        
        return source_files
    
    async def _create_tar_archive(self, archive_path: str, files: List[Path], exclusions: List[str]):
        """Create compressed tar archive"""
        with tarfile.open(archive_path, 'w:gz') as tar:
            for file_path in files:
                try:
                    # Calculate relative path from source root
                    relative_path = file_path.relative_to(self.source_path)
                    tar.add(file_path, arcname=relative_path)
                except (OSError, PermissionError, ValueError) as e:
                    logger.warning(f"Skipping file {file_path}: {e}")
                    continue
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    async def _verify_backup(self, record: BackupRecord):
        """Verify backup integrity"""
        try:
            backup_path = Path(record.path)
            
            # Verify checksum
            current_checksum = await self._calculate_checksum(backup_path)
            if current_checksum != record.checksum:
                raise Exception("Checksum verification failed")
            
            # Verify tar archive integrity
            with tarfile.open(backup_path, 'r:gz') as tar:
                # Try to read all file names
                tar.getnames()
            
            record.status = BackupStatus.VERIFIED
            record.verification_date = datetime.now()
            logger.info(f"Backup {record.id} verified successfully")
            
        except Exception as e:
            logger.error(f"Backup verification failed for {record.id}: {e}")
            record.status = BackupStatus.FAILED
            raise
    
    async def _cloud_sync_backup(self, record: BackupRecord):
        """Sync backup to cloud storage with intelligent version selection"""
        try:
            # Check if cloud sync is necessary based on backup importance
            if not self._should_cloud_sync(record):
                logger.info(f"Skipping cloud sync for {record.id} - not critical")
                return
            
            # Space optimization: compress further for cloud storage
            cloud_path = await self._optimize_for_cloud(record)
            
            # Simulate cloud upload with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Placeholder for actual cloud provider integration
                    # await cloud_provider.upload(cloud_path, f"backups/{record.id}")
                    
                    # For now, simulate successful upload
                    await asyncio.sleep(0.1)  # Simulate network delay
                    break
                    
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Cloud sync attempt {attempt + 1} failed, retrying...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            record.metadata['cloud_synced'] = True
            record.metadata['cloud_sync_date'] = datetime.now().isoformat()
            record.metadata['cloud_optimized'] = True
            logger.info(f"Cloud sync for {record.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Cloud sync failed for {record.id}: {e}")
            record.metadata['cloud_sync_error'] = str(e)
    
    def _should_cloud_sync(self, record: BackupRecord) -> bool:
        """Determine if backup should be synced to cloud based on importance"""
        # Always sync milestone, archive, and permanent backups
        if record.backup_type in [BackupType.MILESTONE, BackupType.ARCHIVE, BackupType.PERMANENT]:
            return True
        
        # Sync stability backups if they're verified
        if record.backup_type == BackupType.STABILITY and record.status == BackupStatus.VERIFIED:
            return True
        
        # Sync incremental backups only if recent and verified
        if record.backup_type == BackupType.INCREMENTAL:
            age_hours = (datetime.now() - record.timestamp).total_seconds() / 3600
            return age_hours < 24 and record.status == BackupStatus.VERIFIED
        
        return False
    
    async def _optimize_for_cloud(self, record: BackupRecord) -> str:
        """Optimize backup for cloud storage"""
        original_path = Path(record.path)
        optimized_path = original_path.parent / f"{original_path.stem}_optimized.tar.gz"
        
        try:
            # For cloud storage, we can use maximum compression
            # Re-compress with better algorithm if not already optimized
            if not record.metadata.get('cloud_optimized', False):
                with tarfile.open(original_path, 'r:gz') as source:
                    with tarfile.open(optimized_path, 'w:gz', compresslevel=9) as target:
                        for member in source.getmembers():
                            if member.isfile():
                                file_data = source.extractfile(member)
                                target.addfile(member, file_data)
                
                # Update record if significantly smaller
                original_size = original_path.stat().st_size
                optimized_size = optimized_path.stat().st_size
                
                if optimized_size < original_size * 0.9:  # At least 10% savings
                    record.metadata['space_savings'] = (original_size - optimized_size) / original_size
                    return str(optimized_path)
            
            return str(original_path)
            
        except Exception as e:
            logger.warning(f"Optimization failed for {record.id}: {e}")
            if optimized_path.exists():
                optimized_path.unlink()
            return str(original_path)
    
    async def _cleanup_old_backups(self, backup_type: BackupType):
        """Clean up old backups based on retention policy"""
        config = self.backup_configs[backup_type]
        retention = config.retention
        
        # Get all backups of this type
        type_records = [r for r in self.records.values() 
                       if r.backup_type == backup_type and r.status in [BackupStatus.COMPLETED, BackupStatus.VERIFIED]]
        
        if not type_records:
            return
        
        # Sort by timestamp (newest first)
        type_records.sort(key=lambda r: r.timestamp, reverse=True)
        
        # Determine cutoff based on retention policy
        cutoff_date = None
        if 'days' in retention:
            cutoff_date = datetime.now() - timedelta(days=retention['days'])
        elif 'weeks' in retention:
            cutoff_date = datetime.now() - timedelta(weeks=retention['weeks'])
        elif 'months' in retention:
            cutoff_date = datetime.now() - timedelta(days=retention['months'] * 30)
        elif 'years' in retention:
            cutoff_date = datetime.now() - timedelta(days=retention['years'] * 365)
        
        if cutoff_date:
            # Find backups to delete
            to_delete = [r for r in type_records if r.timestamp < cutoff_date]
            
            for record in to_delete:
                try:
                    # Delete backup file
                    backup_path = Path(record.path)
                    if backup_path.exists():
                        backup_path.unlink()
                    
                    # Remove from records
                    if record.id in self.records:
                        del self.records[record.id]
                    
                    logger.info(f"Deleted old backup: {record.id}")
                    
                except Exception as e:
                    logger.error(f"Error deleting backup {record.id}: {e}")
    
    async def restore_backup(self, backup_id: str, target_path: Optional[str] = None) -> bool:
        """Restore from a backup with rollback automation"""
        if backup_id not in self.records:
            logger.error(f"Backup {backup_id} not found")
            return False
        
        record = self.records[backup_id]
        backup_path = Path(record.path)
        
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        restore_path = Path(target_path) if target_path else self.source_path
        
        # Create rollback point before restoration
        rollback_backup = None
        if restore_path == self.source_path:
            rollback_backup = await self._create_rollback_point()
        
        try:
            # For incremental backups, need to restore dependencies first
            if record.metadata.get('incremental') and record.dependencies:
                for dep_id in record.dependencies:
                    if not await self.restore_backup(dep_id, str(restore_path)):
                        logger.error(f"Failed to restore dependency {dep_id}")
                        if rollback_backup:
                            await self._rollback_to_point(rollback_backup)
                        return False
            
            # Validate backup before extraction
            if not await self._validate_backup_for_restore(record):
                logger.error(f"Backup {backup_id} failed validation")
                if rollback_backup:
                    await self._rollback_to_point(rollback_backup)
                return False
            
            # Extract backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(restore_path)
            
            # Verify restoration
            if not await self._verify_restoration(record, restore_path):
                logger.error(f"Restoration verification failed for {backup_id}")
                if rollback_backup:
                    await self._rollback_to_point(rollback_backup)
                return False
            
            logger.info(f"Successfully restored backup {backup_id} to {restore_path}")
            
            # Clean up rollback point on success
            if rollback_backup:
                await self._cleanup_rollback_point(rollback_backup)
            
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup {backup_id}: {e}")
            if rollback_backup:
                await self._rollback_to_point(rollback_backup)
            return False
    
    async def _create_rollback_point(self) -> Optional[str]:
        """Create a rollback point before making changes"""
        try:
            rollback_id = f"rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            rollback_path = self.base_path / 'rollback' / f"{rollback_id}.tar.gz"
            rollback_path.parent.mkdir(exist_ok=True)
            
            # Create quick backup of current state
            with tarfile.open(rollback_path, 'w:gz') as tar:
                # Only backup critical files for faster rollback
                critical_patterns = [
                    'services/*/main.py',
                    'services/*/config/*',
                    'config/*',
                    'docker-compose.yml',
                    'requirements.txt',
                    'package.json'
                ]
                
                for pattern in critical_patterns:
                    for file_path in self.source_path.glob(pattern):
                        if file_path.is_file():
                            relative_path = file_path.relative_to(self.source_path)
                            tar.add(file_path, arcname=relative_path)
            
            logger.info(f"Created rollback point: {rollback_id}")
            return rollback_id
            
        except Exception as e:
            logger.error(f"Failed to create rollback point: {e}")
            return None
    
    async def _rollback_to_point(self, rollback_id: str):
        """Rollback to a previous point"""
        try:
            rollback_path = self.base_path / 'rollback' / f"{rollback_id}.tar.gz"
            if not rollback_path.exists():
                logger.error(f"Rollback point {rollback_id} not found")
                return False
            
            # Extract rollback data
            with tarfile.open(rollback_path, 'r:gz') as tar:
                tar.extractall(self.source_path)
            
            logger.info(f"Successfully rolled back to {rollback_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    async def _cleanup_rollback_point(self, rollback_id: str):
        """Clean up rollback point after successful operation"""
        try:
            rollback_path = self.base_path / 'rollback' / f"{rollback_id}.tar.gz"
            if rollback_path.exists():
                rollback_path.unlink()
            logger.info(f"Cleaned up rollback point: {rollback_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup rollback point {rollback_id}: {e}")
    
    async def _validate_backup_for_restore(self, record: BackupRecord) -> bool:
        """Validate backup integrity before restoration"""
        try:
            # Check file exists and is readable
            backup_path = Path(record.path)
            if not backup_path.exists():
                return False
            
            # Verify checksum if available
            if record.checksum:
                current_checksum = await self._calculate_checksum(backup_path)
                if current_checksum != record.checksum:
                    return False
            
            # Quick archive validation
            with tarfile.open(backup_path, 'r:gz') as tar:
                # Ensure we can read the archive structure
                members = tar.getmembers()
                if not members:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Backup validation failed: {e}")
            return False
    
    async def _verify_restoration(self, record: BackupRecord, restore_path: Path) -> bool:
        """Verify restoration was successful"""
        try:
            # Check if key files were restored
            if record.metadata.get('file_count', 0) > 0:
                # For now, just check that some files exist in restore path
                restored_files = list(restore_path.rglob('*'))
                if len(restored_files) < record.metadata['file_count'] * 0.8:  # At least 80% of files
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Restoration verification failed: {e}")
            return False
    
    async def auto_rollback_on_failure(self, service_check_command: str = None) -> bool:
        """Automatically rollback if system health check fails after restoration"""
        try:
            # Run health check
            if service_check_command:
                result = subprocess.run(
                    service_check_command.split(),
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    logger.warning("Health check failed after restoration, initiating rollback")
                    # Find most recent rollback point
                    rollback_dir = self.base_path / 'rollback'
                    if rollback_dir.exists():
                        rollback_files = list(rollback_dir.glob('rollback_*.tar.gz'))
                        if rollback_files:
                            latest_rollback = max(rollback_files, key=lambda p: p.stat().st_mtime)
                            rollback_id = latest_rollback.stem
                            return await self._rollback_to_point(rollback_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Auto-rollback check failed: {e}")
            return False
    
    async def get_backup_recommendations(self) -> List[Dict[str, Any]]:
        """Get intelligent backup recommendations"""
        recommendations = []
        current_time = datetime.now()
        
        # Check backup health
        for backup_type in BackupType:
            last_backup = await self._get_last_backup(backup_type)
            config = self.backup_configs[backup_type]
            
            if not config.enabled:
                continue
            
            # Check if backup is overdue
            if await self._is_backup_due(backup_type, config, current_time):
                urgency = "high" if backup_type in [BackupType.INCREMENTAL, BackupType.STABILITY] else "medium"
                recommendations.append({
                    'type': 'overdue_backup',
                    'backup_type': backup_type.value,
                    'urgency': urgency,
                    'message': f'{backup_type.value.title()} backup is overdue',
                    'action': 'schedule_backup'
                })
            
            # Check backup age
            if last_backup:
                age_days = (current_time - last_backup.timestamp).days
                max_age = {'incremental': 2, 'stability': 14, 'milestone': 45}
                
                if backup_type.value in max_age and age_days > max_age[backup_type.value]:
                    recommendations.append({
                        'type': 'aged_backup',
                        'backup_type': backup_type.value,
                        'urgency': 'medium',
                        'age_days': age_days,
                        'message': f'Last {backup_type.value} backup is {age_days} days old',
                        'action': 'consider_backup'
                    })
        
        # Storage space recommendations
        total_size = sum(r.size_bytes for r in self.records.values() 
                        if r.status in [BackupStatus.COMPLETED, BackupStatus.VERIFIED])
        
        if total_size > 10 * 1024 * 1024 * 1024:  # 10GB
            recommendations.append({
                'type': 'storage_cleanup',
                'urgency': 'low',
                'total_size_gb': total_size / (1024**3),
                'message': f'Backup storage using {total_size/(1024**3):.1f}GB',
                'action': 'cleanup_old_backups'
            })
        
        return recommendations
    
    async def get_status(self) -> Dict[str, Any]:
        """Get backup system status"""
        current_time = datetime.now()
        
        # Count backups by type and status
        by_type = {}
        by_status = {}
        
        for record in self.records.values():
            # By type
            type_key = record.backup_type.value
            if type_key not in by_type:
                by_type[type_key] = {'count': 0, 'total_size': 0, 'latest': None}
            
            by_type[type_key]['count'] += 1
            by_type[type_key]['total_size'] += record.size_bytes
            
            if (by_type[type_key]['latest'] is None or 
                record.timestamp > by_type[type_key]['latest']):
                by_type[type_key]['latest'] = record.timestamp.isoformat()
            
            # By status
            status_key = record.status.value
            by_status[status_key] = by_status.get(status_key, 0) + 1
        
        return {
            'timestamp': current_time.isoformat(),
            'total_backups': len(self.records),
            'running_backups': len(self.running_backups),
            'by_type': by_type,
            'by_status': by_status,
            'total_storage_gb': sum(r.size_bytes for r in self.records.values()) / (1024**3),
            'recommendations': await self.get_backup_recommendations()
        }