"""
Unit tests for File Sync Service
Tests file synchronization, conflict resolution, and version management
"""

import pytest
import asyncio
import uuid
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import hashlib
import json

# Import file sync components
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

from file_sync.main import FileSyncService
from file_sync.models import FileMetadata, SyncEvent, ConflictResolution
from file_sync.sync_engine import SyncEngine
from file_sync.conflict_resolver import ConflictResolver


class TestFileMetadata:
    """Test file metadata model"""
    
    def test_file_metadata_creation(self, sample_file):
        """Test file metadata creation"""
        metadata = FileMetadata(**sample_file)
        
        assert metadata.id == sample_file['id']
        assert metadata.name == sample_file['name']
        assert metadata.size == sample_file['size']
        assert metadata.checksum == sample_file['checksum']
    
    def test_file_metadata_hash_calculation(self, temp_dir):
        """Test file hash calculation"""
        # Create test file
        test_file = os.path.join(temp_dir, "test_file.txt")
        test_content = "This is test content for hash calculation"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        metadata = FileMetadata.from_file(test_file)
        
        # Verify hash is calculated correctly
        expected_hash = hashlib.sha256(test_content.encode()).hexdigest()
        assert metadata.checksum == expected_hash
        assert metadata.size == len(test_content)
    
    def test_file_metadata_comparison(self):
        """Test file metadata comparison"""
        file1 = {
            'id': str(uuid.uuid4()),
            'name': 'test.txt',
            'checksum': 'abc123',
            'modified_at': datetime.utcnow()
        }
        
        file2 = file1.copy()
        file3 = file1.copy()
        file3['checksum'] = 'def456'  # Different checksum
        
        metadata1 = FileMetadata(**file1)
        metadata2 = FileMetadata(**file2)
        metadata3 = FileMetadata(**file3)
        
        assert metadata1.is_identical(metadata2)
        assert not metadata1.is_identical(metadata3)
    
    def test_file_metadata_conflict_detection(self):
        """Test conflict detection between file versions"""
        base_time = datetime.utcnow()
        
        file_local = {
            'id': str(uuid.uuid4()),
            'name': 'test.txt',
            'checksum': 'local_checksum',
            'modified_at': base_time + timedelta(seconds=10)
        }
        
        file_remote = {
            'id': file_local['id'],
            'name': 'test.txt',
            'checksum': 'remote_checksum',
            'modified_at': base_time + timedelta(seconds=20)
        }
        
        local_metadata = FileMetadata(**file_local)
        remote_metadata = FileMetadata(**file_remote)
        
        # Should detect conflict due to different checksums
        assert local_metadata.has_conflict_with(remote_metadata)


class TestSyncEngine:
    """Test sync engine functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.sync_engine = SyncEngine()
    
    @patch('file_sync.sync_engine.storage_client')
    @patch('file_sync.sync_engine.database')
    async def test_sync_file_upload_new(self, mock_db, mock_storage):
        """Test syncing new file upload"""
        file_data = {
            'id': str(uuid.uuid4()),
            'name': 'new_file.txt',
            'path': '/user/documents/new_file.txt',
            'content': b'New file content',
            'user_id': str(uuid.uuid4())
        }
        
        # Mock database responses
        mock_db.get_file_metadata.return_value = None  # File doesn't exist
        mock_db.create_file_metadata.return_value = file_data
        mock_storage.upload_file.return_value = {'success': True, 'url': 'https://storage/file'}
        
        result = await self.sync_engine.sync_file_upload(file_data)
        
        assert result['success'] is True
        assert result['action'] == 'created'
        mock_storage.upload_file.assert_called_once()
        mock_db.create_file_metadata.assert_called_once()
    
    @patch('file_sync.sync_engine.storage_client')
    @patch('file_sync.sync_engine.database')
    async def test_sync_file_update_existing(self, mock_db, mock_storage):
        """Test syncing file update"""
        file_id = str(uuid.uuid4())
        existing_file = {
            'id': file_id,
            'name': 'existing_file.txt',
            'checksum': 'old_checksum',
            'version': 1
        }
        
        updated_file = {
            'id': file_id,
            'name': 'existing_file.txt',
            'content': b'Updated content',
            'checksum': 'new_checksum',
            'user_id': str(uuid.uuid4())
        }
        
        mock_db.get_file_metadata.return_value = existing_file
        mock_db.update_file_metadata.return_value = updated_file
        mock_storage.upload_file.return_value = {'success': True}
        
        result = await self.sync_engine.sync_file_upload(updated_file)
        
        assert result['success'] is True
        assert result['action'] == 'updated'
        mock_db.update_file_metadata.assert_called_once()
    
    @patch('file_sync.sync_engine.storage_client')
    @patch('file_sync.sync_engine.database')
    async def test_sync_file_conflict_detection(self, mock_db, mock_storage):
        """Test conflict detection during sync"""
        file_id = str(uuid.uuid4())
        base_time = datetime.utcnow()
        
        # Server version (newer timestamp)
        server_file = {
            'id': file_id,
            'name': 'conflict_file.txt',
            'checksum': 'server_checksum',
            'modified_at': base_time + timedelta(minutes=10),
            'version': 2
        }
        
        # Client version (older timestamp, different content)
        client_file = {
            'id': file_id,
            'name': 'conflict_file.txt',
            'checksum': 'client_checksum',
            'modified_at': base_time + timedelta(minutes=5),
            'content': b'Client content'
        }
        
        mock_db.get_file_metadata.return_value = server_file
        
        result = await self.sync_engine.sync_file_upload(client_file)
        
        assert result['success'] is False
        assert result['conflict'] is True
        assert 'conflict_id' in result
    
    @patch('file_sync.sync_engine.database')
    async def test_sync_file_download(self, mock_db):
        """Test file download sync"""
        file_id = str(uuid.uuid4())
        file_data = {
            'id': file_id,
            'name': 'download_file.txt',
            'storage_url': 'https://storage/file',
            'checksum': 'file_checksum'
        }
        
        mock_db.get_file_metadata.return_value = file_data
        
        with patch('file_sync.sync_engine.storage_client.download_file') as mock_download:
            mock_download.return_value = b'File content'
            
            result = await self.sync_engine.sync_file_download(file_id, '/local/path')
            
            assert result['success'] is True
            assert result['file_path'] == '/local/path'
            mock_download.assert_called_once()
    
    @patch('file_sync.sync_engine.database')
    async def test_get_sync_changes(self, mock_db):
        """Test getting sync changes since timestamp"""
        since_timestamp = datetime.utcnow() - timedelta(hours=1)
        
        mock_changes = [
            {
                'id': str(uuid.uuid4()),
                'action': 'created',
                'file_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow()
            },
            {
                'id': str(uuid.uuid4()),
                'action': 'updated',
                'file_id': str(uuid.uuid4()),
                'timestamp': datetime.utcnow()
            }
        ]
        
        mock_db.get_sync_events.return_value = mock_changes
        
        changes = await self.sync_engine.get_sync_changes(since_timestamp)
        
        assert len(changes) == 2
        assert all('action' in change for change in changes)
        mock_db.get_sync_events.assert_called_once_with(since_timestamp)
    
    async def test_calculate_sync_priority(self):
        """Test sync priority calculation"""
        # High priority: Recently modified, frequently accessed
        high_priority_file = {
            'modified_at': datetime.utcnow() - timedelta(minutes=5),
            'access_count': 100,
            'file_type': 'document',
            'size': 1024 * 1024  # 1MB
        }
        
        # Low priority: Old, rarely accessed
        low_priority_file = {
            'modified_at': datetime.utcnow() - timedelta(days=30),
            'access_count': 1,
            'file_type': 'archive',
            'size': 100 * 1024 * 1024  # 100MB
        }
        
        high_priority = self.sync_engine.calculate_sync_priority(high_priority_file)
        low_priority = self.sync_engine.calculate_sync_priority(low_priority_file)
        
        assert high_priority > low_priority
    
    async def test_bandwidth_throttling(self):
        """Test bandwidth throttling functionality"""
        # Test with bandwidth limit
        self.sync_engine.set_bandwidth_limit(1024 * 1024)  # 1 MB/s
        
        start_time = datetime.utcnow()
        
        # Simulate large file transfer
        await self.sync_engine.throttle_transfer(10 * 1024 * 1024)  # 10 MB
        
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Should take at least 10 seconds with 1MB/s limit
        assert duration >= 9  # Allow some margin


class TestConflictResolver:
    """Test conflict resolution functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.conflict_resolver = ConflictResolver()
    
    def test_detect_conflict_different_content(self):
        """Test conflict detection with different content"""
        local_file = {
            'id': str(uuid.uuid4()),
            'checksum': 'local_checksum',
            'modified_at': datetime.utcnow() - timedelta(minutes=5)
        }
        
        remote_file = {
            'id': local_file['id'],
            'checksum': 'remote_checksum',
            'modified_at': datetime.utcnow()
        }
        
        conflict = self.conflict_resolver.detect_conflict(local_file, remote_file)
        
        assert conflict is not None
        assert conflict['type'] == 'content_conflict'
        assert conflict['local_file'] == local_file
        assert conflict['remote_file'] == remote_file
    
    def test_detect_conflict_same_content(self):
        """Test no conflict with same content"""
        file_data = {
            'id': str(uuid.uuid4()),
            'checksum': 'same_checksum',
            'modified_at': datetime.utcnow()
        }
        
        local_file = file_data.copy()
        remote_file = file_data.copy()
        
        conflict = self.conflict_resolver.detect_conflict(local_file, remote_file)
        
        assert conflict is None
    
    async def test_resolve_conflict_keep_local(self):
        """Test resolving conflict by keeping local version"""
        conflict = {
            'id': str(uuid.uuid4()),
            'type': 'content_conflict',
            'local_file': {'id': str(uuid.uuid4()), 'content': 'local_content'},
            'remote_file': {'id': str(uuid.uuid4()), 'content': 'remote_content'}
        }
        
        resolution = ConflictResolution.KEEP_LOCAL
        
        with patch.object(self.conflict_resolver, 'database') as mock_db:
            mock_db.resolve_conflict.return_value = True
            
            result = await self.conflict_resolver.resolve_conflict(conflict, resolution)
            
            assert result['success'] is True
            assert result['resolution'] == 'keep_local'
            assert result['final_content'] == 'local_content'
    
    async def test_resolve_conflict_keep_remote(self):
        """Test resolving conflict by keeping remote version"""
        conflict = {
            'id': str(uuid.uuid4()),
            'type': 'content_conflict',
            'local_file': {'id': str(uuid.uuid4()), 'content': 'local_content'},
            'remote_file': {'id': str(uuid.uuid4()), 'content': 'remote_content'}
        }
        
        resolution = ConflictResolution.KEEP_REMOTE
        
        with patch.object(self.conflict_resolver, 'database') as mock_db:
            mock_db.resolve_conflict.return_value = True
            
            result = await self.conflict_resolver.resolve_conflict(conflict, resolution)
            
            assert result['success'] is True
            assert result['resolution'] == 'keep_remote'
            assert result['final_content'] == 'remote_content'
    
    async def test_resolve_conflict_merge(self):
        """Test resolving conflict by merging versions"""
        conflict = {
            'id': str(uuid.uuid4()),
            'type': 'content_conflict',
            'local_file': {
                'id': str(uuid.uuid4()),
                'content': 'Line 1\nLocal Line 2\nLine 3'
            },
            'remote_file': {
                'id': str(uuid.uuid4()),
                'content': 'Line 1\nRemote Line 2\nLine 3'
            }
        }
        
        resolution = ConflictResolution.MERGE
        
        with patch.object(self.conflict_resolver, 'database') as mock_db:
            mock_db.resolve_conflict.return_value = True
            
            result = await self.conflict_resolver.resolve_conflict(conflict, resolution)
            
            assert result['success'] is True
            assert result['resolution'] == 'merge'
            assert 'merged_content' in result
    
    async def test_auto_resolve_conflict_newer_wins(self):
        """Test automatic conflict resolution based on timestamp"""
        newer_time = datetime.utcnow()
        older_time = newer_time - timedelta(minutes=10)
        
        conflict = {
            'type': 'content_conflict',
            'local_file': {
                'modified_at': older_time,
                'content': 'older_content'
            },
            'remote_file': {
                'modified_at': newer_time,
                'content': 'newer_content'
            }
        }
        
        with patch.object(self.conflict_resolver, 'database') as mock_db:
            mock_db.resolve_conflict.return_value = True
            
            result = await self.conflict_resolver.auto_resolve_conflict(conflict)
            
            assert result['success'] is True
            assert result['resolution'] == 'keep_remote'  # Remote is newer
    
    def test_create_conflict_backup(self):
        """Test creating backup of conflicted file"""
        file_data = {
            'id': str(uuid.uuid4()),
            'name': 'document.txt',
            'content': 'conflicted_content',
            'user_id': str(uuid.uuid4())
        }
        
        backup = self.conflict_resolver.create_conflict_backup(file_data)
        
        assert backup['name'].endswith('_conflict')
        assert backup['content'] == file_data['content']
        assert backup['original_file_id'] == file_data['id']
        assert 'backup_timestamp' in backup


@pytest.mark.asyncio
class TestFileSyncService:
    """Test main file sync service"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.sync_service = FileSyncService()
    
    @patch('file_sync.main.SyncEngine')
    async def test_start_sync_session(self, mock_sync_engine):
        """Test starting sync session"""
        user_id = str(uuid.uuid4())
        device_id = str(uuid.uuid4())
        
        mock_sync_engine.return_value.start_session.return_value = {
            'session_id': str(uuid.uuid4()),
            'status': 'active'
        }
        
        result = await self.sync_service.start_sync_session(user_id, device_id)
        
        assert result['success'] is True
        assert 'session_id' in result
    
    @patch('file_sync.main.SyncEngine')
    async def test_stop_sync_session(self, mock_sync_engine):
        """Test stopping sync session"""
        session_id = str(uuid.uuid4())
        
        mock_sync_engine.return_value.stop_session.return_value = True
        
        result = await self.sync_service.stop_sync_session(session_id)
        
        assert result['success'] is True
    
    @patch('file_sync.main.SyncEngine')
    async def test_get_sync_status(self, mock_sync_engine):
        """Test getting sync status"""
        user_id = str(uuid.uuid4())
        
        mock_status = {
            'synced_files': 150,
            'pending_files': 5,
            'failed_files': 2,
            'last_sync': datetime.utcnow().isoformat(),
            'conflicts': 1
        }
        
        mock_sync_engine.return_value.get_sync_status.return_value = mock_status
        
        status = await self.sync_service.get_sync_status(user_id)
        
        assert status['synced_files'] == 150
        assert status['pending_files'] == 5
        assert status['conflicts'] == 1
    
    @patch('file_sync.main.ConflictResolver')
    async def test_resolve_sync_conflict(self, mock_resolver):
        """Test resolving sync conflict"""
        conflict_id = str(uuid.uuid4())
        resolution = 'keep_local'
        
        mock_resolver.return_value.resolve_conflict.return_value = {
            'success': True,
            'resolution': resolution
        }
        
        result = await self.sync_service.resolve_conflict(conflict_id, resolution)
        
        assert result['success'] is True
        assert result['resolution'] == resolution
    
    async def test_file_change_detection(self):
        """Test file change detection"""
        with patch('file_sync.main.file_watcher') as mock_watcher:
            mock_watcher.start.return_value = None
            
            await self.sync_service.start_file_watching('/test/path')
            
            mock_watcher.start.assert_called_once()
    
    async def test_sync_queue_management(self):
        """Test sync queue management"""
        # Add files to sync queue
        files_to_sync = [
            {'id': str(uuid.uuid4()), 'priority': 1},
            {'id': str(uuid.uuid4()), 'priority': 5},
            {'id': str(uuid.uuid4()), 'priority': 3}
        ]
        
        for file_data in files_to_sync:
            await self.sync_service.add_to_sync_queue(file_data)
        
        # Get next file to sync (should be highest priority first)
        next_file = await self.sync_service.get_next_sync_file()
        
        assert next_file['priority'] == 5  # Highest priority first
    
    async def test_sync_performance_monitoring(self):
        """Test sync performance monitoring"""
        # Mock sync operation
        with patch.object(self.sync_service, 'sync_engine') as mock_engine:
            mock_engine.sync_file_upload.return_value = {
                'success': True,
                'duration': 1.5,
                'bytes_transferred': 1024 * 1024
            }
            
            result = await self.sync_service.sync_file_with_monitoring({
                'id': str(uuid.uuid4()),
                'size': 1024 * 1024
            })
            
            assert result['success'] is True
            assert 'performance_metrics' in result
            assert result['performance_metrics']['duration'] == 1.5


@pytest.mark.integration
class TestFileSyncIntegration:
    """Integration tests for file sync service"""
    
    @patch('file_sync.main.storage_client')
    @patch('file_sync.main.database')
    async def test_complete_sync_workflow(self, mock_db, mock_storage):
        """Test complete file sync workflow"""
        sync_service = FileSyncService()
        user_id = str(uuid.uuid4())
        
        # 1. Start sync session
        session_result = await sync_service.start_sync_session(user_id, 'device_1')
        assert session_result['success'] is True
        
        # 2. Upload new file
        file_data = {
            'name': 'test_document.pdf',
            'content': b'PDF content here',
            'user_id': user_id
        }
        
        mock_db.get_file_metadata.return_value = None
        mock_storage.upload_file.return_value = {'success': True}
        mock_db.create_file_metadata.return_value = file_data
        
        upload_result = await sync_service.upload_file(file_data)
        assert upload_result['success'] is True
        
        # 3. Check sync status
        mock_db.get_sync_status.return_value = {
            'synced_files': 1,
            'pending_files': 0
        }
        
        status = await sync_service.get_sync_status(user_id)
        assert status['synced_files'] == 1
    
    async def test_conflict_resolution_workflow(self):
        """Test conflict resolution workflow"""
        conflict_resolver = ConflictResolver()
        
        # Create conflict scenario
        conflict = {
            'id': str(uuid.uuid4()),
            'type': 'content_conflict',
            'local_file': {
                'content': 'Local changes',
                'modified_at': datetime.utcnow() - timedelta(minutes=5)
            },
            'remote_file': {
                'content': 'Remote changes',
                'modified_at': datetime.utcnow()
            }
        }
        
        with patch.object(conflict_resolver, 'database') as mock_db:
            mock_db.resolve_conflict.return_value = True
            
            # Test different resolution strategies
            resolutions = [
                ConflictResolution.KEEP_LOCAL,
                ConflictResolution.KEEP_REMOTE,
                ConflictResolution.MERGE
            ]
            
            for resolution in resolutions:
                result = await conflict_resolver.resolve_conflict(conflict, resolution)
                assert result['success'] is True


@pytest.mark.performance
class TestFileSyncPerformance:
    """Performance tests for file sync service"""
    
    async def test_large_file_sync_performance(self, performance_monitor):
        """Test performance with large files"""
        sync_engine = SyncEngine()
        
        # Simulate 100MB file
        large_file_data = {
            'id': str(uuid.uuid4()),
            'size': 100 * 1024 * 1024,
            'content': b'0' * (100 * 1024 * 1024)
        }
        
        performance_monitor.start()
        
        with patch('file_sync.sync_engine.storage_client') as mock_storage:
            mock_storage.upload_file.return_value = {'success': True}
            
            result = await sync_engine.sync_file_upload(large_file_data)
        
        duration = performance_monitor.stop('large_file_sync')
        
        assert result['success'] is True
        assert duration < 30  # Should complete within 30 seconds
    
    async def test_concurrent_sync_performance(self):
        """Test performance with concurrent sync operations"""
        sync_engine = SyncEngine()
        
        # Create multiple files to sync concurrently
        files = []
        for i in range(10):
            files.append({
                'id': str(uuid.uuid4()),
                'name': f'file_{i}.txt',
                'content': f'Content for file {i}' * 1000
            })
        
        with patch('file_sync.sync_engine.storage_client') as mock_storage:
            mock_storage.upload_file.return_value = {'success': True}
            
            # Start concurrent sync operations
            tasks = []
            for file_data in files:
                task = asyncio.create_task(sync_engine.sync_file_upload(file_data))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
        
        # All operations should succeed
        assert all(result['success'] for result in results)
        assert len(results) == 10