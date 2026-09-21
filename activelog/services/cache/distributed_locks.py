"""
Distributed Locks for Sync Operations
Implements Redis-based distributed locking for coordinating sync operations
"""

import time
import uuid
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Union
from contextlib import contextmanager, asynccontextmanager
from enum import Enum
from dataclasses import dataclass
from .redis_client import get_redis_client, RedisClient

logger = logging.getLogger(__name__)


class LockType(Enum):
    """Types of distributed locks"""
    EXCLUSIVE = "exclusive"
    SHARED = "shared"
    REENTRANT = "reentrant"
    FAIR = "fair"
    PRIORITY = "priority"


@dataclass
class LockInfo:
    """Information about a lock"""
    lock_id: str
    lock_type: LockType
    owner_id: str
    resource: str
    acquired_at: datetime
    expires_at: datetime
    metadata: Dict[str, Any]


class DistributedLock:
    """Redis-based distributed lock implementation"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis = redis_client or get_redis_client()
        self.instance_id = str(uuid.uuid4())
        
        # Lock configuration
        self.default_timeout = 30  # seconds
        self.default_blocking_timeout = 10  # seconds
        self.heartbeat_interval = 5  # seconds
        self.cleanup_interval = 60  # seconds
        
        # Statistics
        self.stats = {
            'locks_acquired': 0,
            'locks_released': 0,
            'lock_timeouts': 0,
            'lock_conflicts': 0,
            'heartbeats_sent': 0
        }
    
    def _make_lock_key(self, resource: str) -> str:
        """Create Redis key for lock"""
        return f"lock:{resource}"
    
    def _make_owner_id(self, client_id: str = None) -> str:
        """Create unique owner ID"""
        if client_id:
            return f"{self.instance_id}:{client_id}"
        return f"{self.instance_id}:{uuid.uuid4()}"
    
    def _serialize_lock_data(self, lock_info: LockInfo) -> str:
        """Serialize lock information"""
        return self.redis._serialize({
            'lock_id': lock_info.lock_id,
            'lock_type': lock_info.lock_type.value,
            'owner_id': lock_info.owner_id,
            'resource': lock_info.resource,
            'acquired_at': lock_info.acquired_at.isoformat(),
            'expires_at': lock_info.expires_at.isoformat(),
            'metadata': lock_info.metadata
        })
    
    def _deserialize_lock_data(self, data: str) -> Optional[LockInfo]:
        """Deserialize lock information"""
        try:
            lock_data = self.redis._deserialize(data)
            if not lock_data:
                return None
            
            return LockInfo(
                lock_id=lock_data['lock_id'],
                lock_type=LockType(lock_data['lock_type']),
                owner_id=lock_data['owner_id'],
                resource=lock_data['resource'],
                acquired_at=datetime.fromisoformat(lock_data['acquired_at']),
                expires_at=datetime.fromisoformat(lock_data['expires_at']),
                metadata=lock_data.get('metadata', {})
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to deserialize lock data: {e}")
            return None
    
    def acquire(self, resource: str, timeout: int = None, blocking: bool = True,
               blocking_timeout: int = None, client_id: str = None,
               lock_type: LockType = LockType.EXCLUSIVE, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Acquire a distributed lock"""
        
        timeout = timeout or self.default_timeout
        blocking_timeout = blocking_timeout or self.default_blocking_timeout
        metadata = metadata or {}
        
        lock_key = self._make_lock_key(resource)
        owner_id = self._make_owner_id(client_id)
        lock_id = str(uuid.uuid4())
        
        acquired_at = datetime.utcnow()
        expires_at = acquired_at + timedelta(seconds=timeout)
        
        lock_info = LockInfo(
            lock_id=lock_id,
            lock_type=lock_type,
            owner_id=owner_id,
            resource=resource,
            acquired_at=acquired_at,
            expires_at=expires_at,
            metadata=metadata
        )
        
        start_time = time.time()
        
        while True:
            # Try to acquire lock
            if self._try_acquire_lock(lock_key, lock_info):
                self.stats['locks_acquired'] += 1
                logger.debug(f"Acquired lock {lock_id} for resource {resource}")
                return lock_id
            
            # Check if we should continue trying
            if not blocking:
                self.stats['lock_conflicts'] += 1
                return None
            
            elapsed_time = time.time() - start_time
            if elapsed_time >= blocking_timeout:
                self.stats['lock_timeouts'] += 1
                logger.warning(f"Lock acquisition timeout for resource {resource}")
                return None
            
            # Wait before retrying
            time.sleep(0.1)
    
    def _try_acquire_lock(self, lock_key: str, lock_info: LockInfo) -> bool:
        """Try to acquire lock atomically"""
        
        # Use Lua script for atomic lock acquisition
        lua_script = """
        local lock_key = KEYS[1]
        local lock_data = ARGV[1]
        local lock_type = ARGV[2]
        local expires_at = ARGV[3]
        
        -- Check if lock exists
        local existing_lock = redis.call('GET', lock_key)
        
        if existing_lock == false then
            -- No existing lock, acquire it
            redis.call('SET', lock_key, lock_data)
            redis.call('EXPIREAT', lock_key, expires_at)
            return 1
        else
            -- Lock exists, check if it's expired or compatible
            local lock_info = cjson.decode(existing_lock)
            local current_time = tonumber(ARGV[4])
            local existing_expires = tonumber(lock_info.expires_at)
            
            if current_time > existing_expires then
                -- Lock is expired, acquire it
                redis.call('SET', lock_key, lock_data)
                redis.call('EXPIREAT', lock_key, expires_at)
                return 1
            elseif lock_type == 'shared' and lock_info.lock_type == 'shared' then
                -- Both are shared locks, allow acquisition
                redis.call('SET', lock_key, lock_data)
                redis.call('EXPIREAT', lock_key, expires_at)
                return 1
            else
                -- Cannot acquire lock
                return 0
            end
        end
        """
        
        try:
            lock_data = self._serialize_lock_data(lock_info)
            expires_timestamp = int(lock_info.expires_at.timestamp())
            current_timestamp = int(time.time())
            
            result = self.redis.client.eval(
                lua_script, 
                1, 
                lock_key,
                lock_data,
                lock_info.lock_type.value,
                expires_timestamp,
                current_timestamp
            )
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to acquire lock: {e}")
            return False
    
    def release(self, resource: str, lock_id: str) -> bool:
        """Release a distributed lock"""
        
        lock_key = self._make_lock_key(resource)
        
        # Use Lua script for atomic lock release
        lua_script = """
        local lock_key = KEYS[1]
        local expected_lock_id = ARGV[1]
        
        local existing_lock = redis.call('GET', lock_key)
        
        if existing_lock == false then
            return 0  -- Lock doesn't exist
        end
        
        local lock_info = cjson.decode(existing_lock)
        
        if lock_info.lock_id == expected_lock_id then
            redis.call('DEL', lock_key)
            return 1  -- Successfully released
        else
            return 0  -- Lock ID mismatch
        end
        """
        
        try:
            result = self.redis.client.eval(lua_script, 1, lock_key, lock_id)
            
            if result:
                self.stats['locks_released'] += 1
                logger.debug(f"Released lock {lock_id} for resource {resource}")
                return True
            else:
                logger.warning(f"Failed to release lock {lock_id} for resource {resource}")
                return False
                
        except Exception as e:
            logger.error(f"Error releasing lock {lock_id}: {e}")
            return False
    
    def extend(self, resource: str, lock_id: str, additional_time: int) -> bool:
        """Extend lock timeout"""
        
        lock_key = self._make_lock_key(resource)
        
        lua_script = """
        local lock_key = KEYS[1]
        local expected_lock_id = ARGV[1]
        local additional_seconds = tonumber(ARGV[2])
        
        local existing_lock = redis.call('GET', lock_key)
        
        if existing_lock == false then
            return 0  -- Lock doesn't exist
        end
        
        local lock_info = cjson.decode(existing_lock)
        
        if lock_info.lock_id == expected_lock_id then
            local current_expiry = redis.call('TTL', lock_key)
            if current_expiry > 0 then
                redis.call('EXPIRE', lock_key, current_expiry + additional_seconds)
                return 1
            else
                return 0  -- Lock already expired
            end
        else
            return 0  -- Lock ID mismatch
        end
        """
        
        try:
            result = self.redis.client.eval(lua_script, 1, lock_key, lock_id, additional_time)
            return bool(result)
        except Exception as e:
            logger.error(f"Error extending lock {lock_id}: {e}")
            return False
    
    def is_locked(self, resource: str) -> bool:
        """Check if resource is locked"""
        lock_key = self._make_lock_key(resource)
        return self.redis.exists('lock', resource)
    
    def get_lock_info(self, resource: str) -> Optional[LockInfo]:
        """Get information about current lock"""
        lock_key = self._make_lock_key(resource)
        lock_data = self.redis.client.get(lock_key)
        
        if lock_data:
            return self._deserialize_lock_data(lock_data)
        return None
    
    def force_release(self, resource: str) -> bool:
        """Force release a lock (admin operation)"""
        lock_key = self._make_lock_key(resource)
        return bool(self.redis.client.delete(lock_key))
    
    def cleanup_expired_locks(self) -> int:
        """Clean up expired locks"""
        pattern = f"{self.redis.prefixes['lock']}*"
        lock_keys = self.redis.client.keys(pattern)
        
        cleaned_count = 0
        current_time = datetime.utcnow()
        
        for lock_key in lock_keys:
            try:
                lock_data = self.redis.client.get(lock_key)
                if lock_data:
                    lock_info = self._deserialize_lock_data(lock_data)
                    if lock_info and current_time > lock_info.expires_at:
                        self.redis.client.delete(lock_key)
                        cleaned_count += 1
            except Exception as e:
                logger.error(f"Error cleaning up lock {lock_key}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired locks")
        
        return cleaned_count
    
    def get_all_locks(self) -> List[LockInfo]:
        """Get information about all current locks"""
        pattern = f"{self.redis.prefixes['lock']}*"
        lock_keys = self.redis.client.keys(pattern)
        
        locks = []
        for lock_key in lock_keys:
            try:
                lock_data = self.redis.client.get(lock_key)
                if lock_data:
                    lock_info = self._deserialize_lock_data(lock_data)
                    if lock_info:
                        locks.append(lock_info)
            except Exception as e:
                logger.error(f"Error getting lock info for {lock_key}: {e}")
        
        return locks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get lock statistics"""
        all_locks = self.get_all_locks()
        
        return {
            **self.stats,
            'active_locks': len(all_locks),
            'lock_types': {
                lock_type.value: len([l for l in all_locks if l.lock_type == lock_type])
                for lock_type in LockType
            }
        }
    
    @contextmanager
    def lock(self, resource: str, timeout: int = None, blocking: bool = True,
            blocking_timeout: int = None, client_id: str = None,
            lock_type: LockType = LockType.EXCLUSIVE, metadata: Dict[str, Any] = None):
        """Context manager for acquiring and releasing locks"""
        
        lock_id = self.acquire(
            resource=resource,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            client_id=client_id,
            lock_type=lock_type,
            metadata=metadata
        )
        
        if lock_id is None:
            raise LockAcquisitionError(f"Failed to acquire lock for resource: {resource}")
        
        try:
            yield lock_id
        finally:
            self.release(resource, lock_id)


class AsyncDistributedLock:
    """Async version of distributed lock"""
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.sync_lock = DistributedLock(redis_client)
    
    async def acquire(self, resource: str, timeout: int = None, blocking: bool = True,
                     blocking_timeout: int = None, client_id: str = None,
                     lock_type: LockType = LockType.EXCLUSIVE, metadata: Dict[str, Any] = None) -> Optional[str]:
        """Async acquire lock"""
        
        timeout = timeout or self.sync_lock.default_timeout
        blocking_timeout = blocking_timeout or self.sync_lock.default_blocking_timeout
        
        start_time = time.time()
        
        while True:
            # Try to acquire lock
            lock_id = self.sync_lock.acquire(
                resource=resource,
                timeout=timeout,
                blocking=False,
                client_id=client_id,
                lock_type=lock_type,
                metadata=metadata
            )
            
            if lock_id:
                return lock_id
            
            if not blocking:
                return None
            
            elapsed_time = time.time() - start_time
            if elapsed_time >= blocking_timeout:
                return None
            
            # Async wait before retrying
            await asyncio.sleep(0.1)
    
    async def release(self, resource: str, lock_id: str) -> bool:
        """Async release lock"""
        return self.sync_lock.release(resource, lock_id)
    
    async def extend(self, resource: str, lock_id: str, additional_time: int) -> bool:
        """Async extend lock"""
        return self.sync_lock.extend(resource, lock_id, additional_time)
    
    @asynccontextmanager
    async def lock(self, resource: str, timeout: int = None, blocking: bool = True,
                  blocking_timeout: int = None, client_id: str = None,
                  lock_type: LockType = LockType.EXCLUSIVE, metadata: Dict[str, Any] = None):
        """Async context manager for locks"""
        
        lock_id = await self.acquire(
            resource=resource,
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            client_id=client_id,
            lock_type=lock_type,
            metadata=metadata
        )
        
        if lock_id is None:
            raise LockAcquisitionError(f"Failed to acquire lock for resource: {resource}")
        
        try:
            yield lock_id
        finally:
            await self.release(resource, lock_id)


class SyncCoordinator:
    """Coordinates file synchronization operations using distributed locks"""
    
    def __init__(self, lock_manager: DistributedLock = None):
        self.lock_manager = lock_manager or DistributedLock()
        
        # Sync operation types
        self.sync_operations = {
            'file_upload': {'timeout': 300, 'lock_type': LockType.EXCLUSIVE},
            'file_download': {'timeout': 180, 'lock_type': LockType.SHARED},
            'file_delete': {'timeout': 60, 'lock_type': LockType.EXCLUSIVE},
            'metadata_update': {'timeout': 30, 'lock_type': LockType.EXCLUSIVE},
            'conflict_resolution': {'timeout': 600, 'lock_type': LockType.EXCLUSIVE},
            'batch_sync': {'timeout': 1800, 'lock_type': LockType.EXCLUSIVE}
        }
    
    def sync_file(self, file_id: str, operation: str, user_id: str,
                 metadata: Dict[str, Any] = None) -> str:
        """Coordinate file synchronization operation"""
        
        if operation not in self.sync_operations:
            raise ValueError(f"Unknown sync operation: {operation}")
        
        config = self.sync_operations[operation]
        resource = f"file:{file_id}"
        
        sync_metadata = {
            'operation': operation,
            'user_id': user_id,
            'started_at': datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        with self.lock_manager.lock(
            resource=resource,
            timeout=config['timeout'],
            lock_type=config['lock_type'],
            client_id=user_id,
            metadata=sync_metadata
        ) as lock_id:
            logger.info(f"Started {operation} for file {file_id} (lock: {lock_id})")
            return lock_id
    
    def sync_user_files(self, user_id: str, operation: str = 'batch_sync',
                       metadata: Dict[str, Any] = None) -> str:
        """Coordinate user-level synchronization"""
        
        resource = f"user:{user_id}"
        config = self.sync_operations.get(operation, self.sync_operations['batch_sync'])
        
        sync_metadata = {
            'operation': operation,
            'user_id': user_id,
            'started_at': datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        with self.lock_manager.lock(
            resource=resource,
            timeout=config['timeout'],
            lock_type=config['lock_type'],
            client_id=user_id,
            metadata=sync_metadata
        ) as lock_id:
            logger.info(f"Started {operation} for user {user_id} (lock: {lock_id})")
            return lock_id
    
    def resolve_conflict(self, file_id: str, user_id: str, 
                        conflict_data: Dict[str, Any]) -> str:
        """Coordinate conflict resolution"""
        
        resource = f"conflict:{file_id}"
        
        conflict_metadata = {
            'operation': 'conflict_resolution',
            'user_id': user_id,
            'conflict_type': conflict_data.get('type'),
            'started_at': datetime.utcnow().isoformat(),
            'conflict_data': conflict_data
        }
        
        with self.lock_manager.lock(
            resource=resource,
            timeout=600,  # 10 minutes for conflict resolution
            lock_type=LockType.EXCLUSIVE,
            client_id=user_id,
            metadata=conflict_metadata
        ) as lock_id:
            logger.info(f"Started conflict resolution for file {file_id} (lock: {lock_id})")
            return lock_id
    
    def get_active_sync_operations(self, user_id: str = None) -> List[LockInfo]:
        """Get active synchronization operations"""
        all_locks = self.lock_manager.get_all_locks()
        
        sync_locks = []
        for lock in all_locks:
            # Filter by user if specified
            if user_id and lock.metadata.get('user_id') != user_id:
                continue
            
            # Only include sync-related locks
            if 'operation' in lock.metadata:
                sync_locks.append(lock)
        
        return sync_locks


class LockAcquisitionError(Exception):
    """Exception raised when lock acquisition fails"""
    pass


class LockTimeoutError(Exception):
    """Exception raised when lock operation times out"""
    pass


# Global instances
distributed_lock = None
async_distributed_lock = None
sync_coordinator = None


def get_distributed_lock() -> DistributedLock:
    """Get global distributed lock instance"""
    global distributed_lock
    if distributed_lock is None:
        distributed_lock = DistributedLock()
    return distributed_lock


def get_async_distributed_lock() -> AsyncDistributedLock:
    """Get global async distributed lock instance"""
    global async_distributed_lock
    if async_distributed_lock is None:
        async_distributed_lock = AsyncDistributedLock()
    return async_distributed_lock


def get_sync_coordinator() -> SyncCoordinator:
    """Get global sync coordinator instance"""
    global sync_coordinator
    if sync_coordinator is None:
        sync_coordinator = SyncCoordinator()
    return sync_coordinator


# Convenience functions
def acquire_sync_lock(file_id: str, operation: str, user_id: str, 
                     metadata: Dict[str, Any] = None) -> str:
    """Convenience function to acquire sync lock"""
    coordinator = get_sync_coordinator()
    return coordinator.sync_file(file_id, operation, user_id, metadata)


def release_sync_lock(resource: str, lock_id: str) -> bool:
    """Convenience function to release sync lock"""
    lock_manager = get_distributed_lock()
    return lock_manager.release(resource, lock_id)