#!/usr/bin/env python3
"""
ActiveLog.ai Edge Offline Sync Queue

Manages offline operation with intelligent data queuing and synchronization.
Handles network outages, prioritizes critical data, and implements retry logic.
"""

import asyncio
import json
import logging
import sqlite3
import time
import hashlib
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import requests
import queue
from contextlib import contextmanager

class SyncPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class SyncStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SyncItem:
    """Data item for synchronization"""
    id: str
    operation_type: str  # 'create', 'update', 'delete', 'upload'
    endpoint: str
    data: Dict[str, Any]
    priority: SyncPriority
    created_at: str
    scheduled_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    status: SyncStatus = SyncStatus.PENDING
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    content_hash: Optional[str] = None
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}
        if self.scheduled_at is None:
            self.scheduled_at = self.created_at

class OfflineSyncQueue:
    """SQLite-based offline sync queue"""
    
    def __init__(self, db_path: str = "/tmp/activelog_sync_queue.db"):
        self.db_path = db_path
        self.init_database()
        self.logger = logging.getLogger(__name__)
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_queue (
                id TEXT PRIMARY KEY,
                operation_type TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                data TEXT NOT NULL,
                priority INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                scheduled_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                file_path TEXT,
                content_hash TEXT,
                dependencies TEXT,
                metadata TEXT
            )
        ''')
        
        # File cache table for large data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_cache (
                hash TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                size INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL
            )
        ''')
        
        # Sync statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_stats (
                date TEXT PRIMARY KEY,
                items_queued INTEGER DEFAULT 0,
                items_synced INTEGER DEFAULT 0,
                items_failed INTEGER DEFAULT 0,
                bytes_synced INTEGER DEFAULT 0,
                sync_duration_seconds REAL DEFAULT 0
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status_priority ON sync_queue(status, priority DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scheduled_at ON sync_queue(scheduled_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_operation_type ON sync_queue(operation_type)')
        
        conn.commit()
        conn.close()
    
    def add_item(self, item: SyncItem) -> str:
        """Add item to sync queue"""
        if not item.id:
            item.id = self._generate_id(item)
        
        # Store large data in file cache if needed
        if item.file_path and os.path.exists(item.file_path):
            item.content_hash = self._calculate_file_hash(item.file_path)
            self._store_in_file_cache(item.file_path, item.content_hash)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO sync_queue 
            (id, operation_type, endpoint, data, priority, created_at, scheduled_at,
             retry_count, max_retries, status, error_message, file_path, content_hash,
             dependencies, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.id, item.operation_type, item.endpoint, json.dumps(item.data),
            item.priority.value, item.created_at, item.scheduled_at,
            item.retry_count, item.max_retries, item.status.value,
            item.error_message, item.file_path, item.content_hash,
            json.dumps(item.dependencies), json.dumps(item.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.debug(f"Added sync item: {item.id} ({item.operation_type})")
        return item.id
    
    def get_pending_items(self, limit: int = 100) -> List[SyncItem]:
        """Get pending sync items ordered by priority"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM sync_queue 
            WHERE status = 'pending' AND scheduled_at <= ?
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        ''', (datetime.now().isoformat(), limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        items = []
        for row in rows:
            items.append(self._row_to_sync_item(row))
        
        return items
    
    def update_item_status(self, item_id: str, status: SyncStatus, error_message: str = None):
        """Update sync item status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sync_queue 
            SET status = ?, error_message = ?
            WHERE id = ?
        ''', (status.value, error_message, item_id))
        
        conn.commit()
        conn.close()
    
    def increment_retry_count(self, item_id: str) -> int:
        """Increment retry count and return new count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE sync_queue 
            SET retry_count = retry_count + 1,
                scheduled_at = ?
            WHERE id = ?
        ''', (self._calculate_retry_delay(item_id), item_id))
        
        cursor.execute('SELECT retry_count FROM sync_queue WHERE id = ?', (item_id,))
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        return result[0] if result else 0
    
    def remove_item(self, item_id: str):
        """Remove item from queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sync_queue WHERE id = ?', (item_id,))
        
        conn.commit()
        conn.close()
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN priority = 4 THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN priority = 3 THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN priority = 2 THEN 1 ELSE 0 END) as normal,
                SUM(CASE WHEN priority = 1 THEN 1 ELSE 0 END) as low
            FROM sync_queue
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            'total': result[0] or 0,
            'pending': result[1] or 0,
            'completed': result[2] or 0,
            'failed': result[3] or 0,
            'priority_breakdown': {
                'critical': result[4] or 0,
                'high': result[5] or 0,
                'normal': result[6] or 0,
                'low': result[7] or 0
            }
        }
    
    def cleanup_completed_items(self, max_age_hours: int = 24) -> int:
        """Clean up old completed/failed items"""
        cutoff_time = (datetime.now() - timedelta(hours=max_age_hours)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM sync_queue 
            WHERE status IN ('completed', 'failed') 
            AND created_at < ?
        ''', (cutoff_time,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def _generate_id(self, item: SyncItem) -> str:
        """Generate unique ID for sync item"""
        content = f"{item.operation_type}-{item.endpoint}-{json.dumps(item.data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _store_in_file_cache(self, file_path: str, content_hash: str):
        """Store file in cache table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        file_size = os.path.getsize(file_path)
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO file_cache 
            (hash, file_path, size, created_at, accessed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (content_hash, file_path, file_size, now, now))
        
        conn.commit()
        conn.close()
    
    def _calculate_retry_delay(self, item_id: str) -> str:
        """Calculate exponential backoff delay"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT retry_count FROM sync_queue WHERE id = ?', (item_id,))
        result = cursor.fetchone()
        conn.close()
        
        retry_count = result[0] if result else 0
        
        # Exponential backoff: 1min, 2min, 4min, 8min, etc.
        delay_minutes = 2 ** retry_count
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        return scheduled_time.isoformat()
    
    def _row_to_sync_item(self, row) -> SyncItem:
        """Convert database row to SyncItem"""
        return SyncItem(
            id=row[0],
            operation_type=row[1],
            endpoint=row[2],
            data=json.loads(row[3]),
            priority=SyncPriority(row[4]),
            created_at=row[5],
            scheduled_at=row[6],
            retry_count=row[7],
            max_retries=row[8],
            status=SyncStatus(row[9]),
            error_message=row[10],
            file_path=row[11],
            content_hash=row[12],
            dependencies=json.loads(row[13]) if row[13] else [],
            metadata=json.loads(row[14]) if row[14] else {}
        )

class NetworkChecker:
    """Network connectivity checker"""
    
    def __init__(self, check_hosts: List[str] = None):
        self.check_hosts = check_hosts or [
            'google.com',
            'cloudflare.com',
            '8.8.8.8'
        ]
        self.logger = logging.getLogger(__name__)
        self._last_check = None
        self._last_result = False
        self._check_interval = 30  # seconds
    
    def is_online(self) -> bool:
        """Check if network connection is available"""
        now = time.time()
        
        # Use cached result if recent
        if (self._last_check and 
            now - self._last_check < self._check_interval):
            return self._last_result
        
        # Test connectivity
        for host in self.check_hosts:
            try:
                response = requests.get(f'http://{host}', timeout=5)
                if response.status_code == 200:
                    self._last_check = now
                    self._last_result = True
                    return True
            except:
                continue
        
        self._last_check = now
        self._last_result = False
        return False
    
    def wait_for_connection(self, timeout: int = 300) -> bool:
        """Wait for network connection with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_online():
                return True
            time.sleep(10)
        
        return False

class SyncManager:
    """Main synchronization manager"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.queue = OfflineSyncQueue(self.config.get('queue_db_path', '/tmp/activelog_sync_queue.db'))
        self.network_checker = NetworkChecker(self.config.get('check_hosts'))
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, self.config.get('log_level', 'INFO')),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Sync configuration
        self.api_base_url = self.config.get('api_base_url', 'https://api.activelog.ai')
        self.api_key = self.config.get('api_key', '')
        self.sync_interval = self.config.get('sync_interval', 60)
        self.batch_size = self.config.get('batch_size', 50)
        self.max_concurrent = self.config.get('max_concurrent', 5)
        
        # State
        self.running = False
        self.sync_in_progress = False
        self._sync_semaphore = asyncio.Semaphore(self.max_concurrent)
    
    async def start(self):
        """Start the sync manager"""
        self.running = True
        self.logger.info("Starting Offline Sync Manager...")
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._sync_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._stats_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        finally:
            self.running = False
            self.logger.info("Sync manager stopped")
    
    async def _sync_loop(self):
        """Main synchronization loop"""
        while self.running:
            try:
                if self.network_checker.is_online():
                    await self._process_sync_queue()
                else:
                    self.logger.debug("No network connection - skipping sync")
                
            except Exception as e:
                self.logger.error(f"Sync loop error: {e}")
            
            await asyncio.sleep(self.sync_interval)
    
    async def _process_sync_queue(self):
        """Process pending sync items"""
        if self.sync_in_progress:
            return
        
        self.sync_in_progress = True
        
        try:
            pending_items = self.queue.get_pending_items(self.batch_size)
            
            if not pending_items:
                return
            
            self.logger.info(f"Processing {len(pending_items)} sync items")
            
            # Group items by dependencies
            dependency_groups = self._group_by_dependencies(pending_items)
            
            # Process groups sequentially, items within groups concurrently
            for group in dependency_groups:
                tasks = []
                for item in group:
                    task = asyncio.create_task(self._sync_item(item))
                    tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            self.sync_in_progress = False
    
    async def _sync_item(self, item: SyncItem):
        """Sync individual item"""
        async with self._sync_semaphore:
            try:
                self.queue.update_item_status(item.id, SyncStatus.IN_PROGRESS)
                
                # Prepare request
                url = f"{self.api_base_url}{item.endpoint}"
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                # Handle different operation types
                if item.operation_type == 'create':
                    response = requests.post(url, json=item.data, headers=headers, timeout=30)
                elif item.operation_type == 'update':
                    response = requests.put(url, json=item.data, headers=headers, timeout=30)
                elif item.operation_type == 'delete':
                    response = requests.delete(url, headers=headers, timeout=30)
                elif item.operation_type == 'upload' and item.file_path:
                    response = await self._upload_file(url, item, headers)
                else:
                    raise ValueError(f"Unknown operation type: {item.operation_type}")
                
                # Check response
                if response.status_code in [200, 201, 204]:
                    self.queue.update_item_status(item.id, SyncStatus.COMPLETED)
                    self.logger.debug(f"Successfully synced item: {item.id}")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            except Exception as e:
                await self._handle_sync_error(item, str(e))
    
    async def _upload_file(self, url: str, item: SyncItem, headers: Dict[str, str]):
        """Handle file upload with resumable support"""
        if not item.file_path or not os.path.exists(item.file_path):
            raise FileNotFoundError(f"File not found: {item.file_path}")
        
        file_size = os.path.getsize(item.file_path)
        
        # For large files, implement chunked upload
        if file_size > 10 * 1024 * 1024:  # 10MB
            return await self._chunked_upload(url, item, headers)
        else:
            # Simple upload for small files
            with open(item.file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(url, files=files, headers=headers, timeout=60)
                return response
    
    async def _chunked_upload(self, url: str, item: SyncItem, headers: Dict[str, str]):
        """Implement chunked/resumable file upload"""
        chunk_size = 1024 * 1024  # 1MB chunks
        file_size = os.path.getsize(item.file_path)
        
        with open(item.file_path, 'rb') as f:
            for chunk_start in range(0, file_size, chunk_size):
                chunk_end = min(chunk_start + chunk_size - 1, file_size - 1)
                
                # Prepare chunk headers
                chunk_headers = headers.copy()
                chunk_headers['Content-Range'] = f'bytes {chunk_start}-{chunk_end}/{file_size}'
                
                # Read chunk
                f.seek(chunk_start)
                chunk_data = f.read(chunk_size)
                
                # Upload chunk
                response = requests.post(
                    f"{url}/chunk",
                    data=chunk_data,
                    headers=chunk_headers,
                    timeout=60
                )
                
                if response.status_code not in [200, 201, 206]:
                    raise Exception(f"Chunk upload failed: {response.status_code}")
        
        # Finalize upload
        return requests.post(f"{url}/finalize", headers=headers, timeout=30)
    
    async def _handle_sync_error(self, item: SyncItem, error_message: str):
        """Handle sync error with retry logic"""
        self.logger.warning(f"Sync failed for item {item.id}: {error_message}")
        
        retry_count = self.queue.increment_retry_count(item.id)
        
        if retry_count >= item.max_retries:
            self.queue.update_item_status(item.id, SyncStatus.FAILED, error_message)
            self.logger.error(f"Item {item.id} failed permanently after {retry_count} retries")
        else:
            self.queue.update_item_status(item.id, SyncStatus.PENDING, error_message)
            self.logger.info(f"Item {item.id} scheduled for retry ({retry_count}/{item.max_retries})")
    
    def _group_by_dependencies(self, items: List[SyncItem]) -> List[List[SyncItem]]:
        """Group items by dependencies for ordered processing"""
        # Simple implementation - can be enhanced with topological sorting
        groups = []
        remaining_items = items.copy()
        
        while remaining_items:
            # Find items with no unresolved dependencies
            current_group = []
            completed_ids = set()
            
            for item in remaining_items[:]:
                if not item.dependencies or all(dep in completed_ids for dep in item.dependencies):
                    current_group.append(item)
                    remaining_items.remove(item)
                    completed_ids.add(item.id)
            
            if current_group:
                groups.append(current_group)
            else:
                # Break circular dependencies by processing remaining items
                groups.append(remaining_items)
                break
        
        return groups
    
    async def _cleanup_loop(self):
        """Cleanup old completed items"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                deleted = self.queue.cleanup_completed_items(
                    self.config.get('cleanup_age_hours', 24)
                )
                
                if deleted > 0:
                    self.logger.info(f"Cleaned up {deleted} old sync items")
                
            except Exception as e:
                self.logger.error(f"Cleanup failed: {e}")
    
    async def _stats_loop(self):
        """Record sync statistics"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Record stats every hour
                
                stats = self.queue.get_queue_stats()
                self.logger.info(f"Sync queue stats: {stats}")
                
            except Exception as e:
                self.logger.error(f"Stats recording failed: {e}")
    
    def add_sync_item(self, operation_type: str, endpoint: str, data: Dict[str, Any], 
                     priority: SyncPriority = SyncPriority.NORMAL, 
                     file_path: str = None, dependencies: List[str] = None) -> str:
        """Add item to sync queue"""
        item = SyncItem(
            id="",  # Will be generated
            operation_type=operation_type,
            endpoint=endpoint,
            data=data,
            priority=priority,
            created_at=datetime.now().isoformat(),
            file_path=file_path,
            dependencies=dependencies or []
        )
        
        return self.queue.add_item(item)
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Get current sync statistics"""
        queue_stats = self.queue.get_queue_stats()
        
        return {
            'queue_stats': queue_stats,
            'network_online': self.network_checker.is_online(),
            'sync_in_progress': self.sync_in_progress,
            'last_sync': datetime.now().isoformat()
        }

class OfflineSyncAPI:
    """API wrapper for offline-capable operations"""
    
    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
        self.logger = logging.getLogger(__name__)
    
    def create_log_entry(self, log_data: Dict[str, Any], priority: SyncPriority = SyncPriority.NORMAL) -> str:
        """Create log entry (offline-capable)"""
        return self.sync_manager.add_sync_item(
            operation_type='create',
            endpoint='/api/logs',
            data=log_data,
            priority=priority
        )
    
    def update_log_entry(self, log_id: str, log_data: Dict[str, Any], priority: SyncPriority = SyncPriority.NORMAL) -> str:
        """Update log entry (offline-capable)"""
        return self.sync_manager.add_sync_item(
            operation_type='update',
            endpoint=f'/api/logs/{log_id}',
            data=log_data,
            priority=priority
        )
    
    def upload_file(self, file_path: str, metadata: Dict[str, Any] = None, priority: SyncPriority = SyncPriority.HIGH) -> str:
        """Upload file (offline-capable)"""
        return self.sync_manager.add_sync_item(
            operation_type='upload',
            endpoint='/api/files',
            data=metadata or {},
            priority=priority,
            file_path=file_path
        )
    
    def sync_device_metrics(self, metrics_data: Dict[str, Any]) -> str:
        """Sync device metrics (offline-capable)"""
        return self.sync_manager.add_sync_item(
            operation_type='create',
            endpoint='/api/metrics',
            data=metrics_data,
            priority=SyncPriority.LOW
        )
    
    def report_critical_event(self, event_data: Dict[str, Any]) -> str:
        """Report critical event (high priority)"""
        return self.sync_manager.add_sync_item(
            operation_type='create',
            endpoint='/api/events',
            data=event_data,
            priority=SyncPriority.CRITICAL
        )

async def main():
    """Main entry point for testing"""
    config = {
        'api_base_url': 'https://api.activelog.ai',
        'api_key': 'test-key',
        'sync_interval': 30,
        'log_level': 'INFO'
    }
    
    sync_manager = SyncManager(config)
    
    # Add some test items
    api = OfflineSyncAPI(sync_manager)
    
    api.create_log_entry({
        'message': 'Test log entry',
        'level': 'info',
        'timestamp': datetime.now().isoformat()
    })
    
    api.report_critical_event({
        'event_type': 'system_error',
        'description': 'Critical system error occurred',
        'timestamp': datetime.now().isoformat()
    })
    
    # Start sync manager
    await sync_manager.start()

if __name__ == '__main__':
    asyncio.run(main())