"""
Unit tests for Cache Service
Tests Redis caching, session management, and distributed locks
"""

import pytest
import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import asyncio

# Import cache service components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

from cache.redis_client import RedisClient, cache_result
from cache.session_cache import SessionCache, PermissionCache
from cache.metadata_cache import MetadataCache, SearchCache, AnalyticsCache
from cache.invalidation import CacheInvalidationManager, InvalidationType, InvalidationRule
from cache.api_cache import APIResponseCache
from cache.distributed_locks import DistributedLock, LockType, SyncCoordinator


class TestRedisClient:
    """Test Redis client functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.redis_client.redis') as mock_redis:
            self.mock_redis_instance = MagicMock()
            mock_redis.Redis.return_value = self.mock_redis_instance
            mock_redis.ConnectionPool.return_value = MagicMock()
            
            self.redis_client = RedisClient()
    
    def test_redis_client_initialization(self):
        """Test Redis client initialization"""
        assert self.redis_client.host == 'localhost'
        assert self.redis_client.port == 6379
        assert self.redis_client.db == 0
        assert isinstance(self.redis_client.prefixes, dict)
        assert isinstance(self.redis_client.default_ttl, dict)
    
    def test_health_check_success(self):
        """Test Redis health check success"""
        self.mock_redis_instance.ping.return_value = True
        
        result = self.redis_client.health_check()
        
        assert result is True
        self.mock_redis_instance.ping.assert_called_once()
    
    def test_health_check_failure(self):
        """Test Redis health check failure"""
        self.mock_redis_instance.ping.side_effect = Exception("Connection failed")
        
        result = self.redis_client.health_check()
        
        assert result is False
    
    def test_make_key(self):
        """Test cache key generation"""
        key = self.redis_client._make_key('session', 'user123')
        
        assert key == 'session:user123'
    
    def test_serialize_deserialize_dict(self):
        """Test serialization and deserialization of dict"""
        data = {'key': 'value', 'number': 42}
        
        serialized = self.redis_client._serialize(data)
        deserialized = self.redis_client._deserialize(serialized)
        
        assert deserialized == data
    
    def test_serialize_deserialize_string(self):
        """Test serialization and deserialization of string"""
        data = "test string"
        
        serialized = self.redis_client._serialize(data)
        deserialized = self.redis_client._deserialize(serialized)
        
        assert deserialized == data
    
    def test_get_set_operations(self):
        """Test basic get/set operations"""
        self.mock_redis_instance.setex.return_value = True
        self.mock_redis_instance.get.return_value = json.dumps({'test': 'data'})
        
        # Test set
        result = self.redis_client.set('test', 'key1', {'test': 'data'}, 300)
        assert result is True
        
        # Test get
        result = self.redis_client.get('test', 'key1')
        assert result == {'test': 'data'}
    
    def test_delete_operation(self):
        """Test delete operation"""
        self.mock_redis_instance.delete.return_value = 1
        
        result = self.redis_client.delete('test', 'key1')
        
        assert result is True
        self.mock_redis_instance.delete.assert_called_once()
    
    def test_exists_operation(self):
        """Test exists operation"""
        self.mock_redis_instance.exists.return_value = 1
        
        result = self.redis_client.exists('test', 'key1')
        
        assert result is True
    
    def test_mget_mset_operations(self):
        """Test bulk get/set operations"""
        # Test mset
        self.mock_redis_instance.mset.return_value = True
        
        data = {'key1': 'value1', 'key2': 'value2'}
        result = self.redis_client.mset('test', data, 300)
        
        assert result is True
        
        # Test mget
        self.mock_redis_instance.mget.return_value = [
            json.dumps('value1'),
            json.dumps('value2')
        ]
        
        result = self.redis_client.mget('test', ['key1', 'key2'])
        
        assert result == {'key1': 'value1', 'key2': 'value2'}
    
    def test_hash_operations(self):
        """Test Redis hash operations"""
        # Test hset
        self.mock_redis_instance.hset.return_value = 1
        
        result = self.redis_client.hset('test', 'hash1', 'field1', 'value1', 300)
        assert result is True
        
        # Test hget
        self.mock_redis_instance.hget.return_value = json.dumps('value1')
        
        result = self.redis_client.hget('test', 'hash1', 'field1')
        assert result == 'value1'
        
        # Test hgetall
        self.mock_redis_instance.hgetall.return_value = {
            'field1': json.dumps('value1'),
            'field2': json.dumps('value2')
        }
        
        result = self.redis_client.hgetall('test', 'hash1')
        assert result == {'field1': 'value1', 'field2': 'value2'}
    
    def test_list_operations(self):
        """Test Redis list operations"""
        # Test lpush
        self.mock_redis_instance.lpush.return_value = 2
        
        result = self.redis_client.lpush('test', 'list1', 'item1', 'item2')
        assert result == 2
        
        # Test lrange
        self.mock_redis_instance.lrange.return_value = [
            json.dumps('item2'),
            json.dumps('item1')
        ]
        
        result = self.redis_client.lrange('test', 'list1')
        assert result == ['item2', 'item1']
    
    def test_set_operations(self):
        """Test Redis set operations"""
        # Test sadd
        self.mock_redis_instance.sadd.return_value = 2
        
        result = self.redis_client.sadd('test', 'set1', 'member1', 'member2')
        assert result == 2
        
        # Test smembers
        self.mock_redis_instance.smembers.return_value = {
            json.dumps('member1'),
            json.dumps('member2')
        }
        
        result = self.redis_client.smembers('test', 'set1')
        assert result == {'member1', 'member2'}


class TestSessionCache:
    """Test session cache functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.session_cache.get_redis_client') as mock_get_redis:
            self.mock_redis = MagicMock()
            mock_get_redis.return_value = self.mock_redis
            
            self.session_cache = SessionCache(self.mock_redis)
    
    def test_create_session(self, sample_user):
        """Test session creation"""
        self.mock_redis.set.return_value = True
        self.mock_redis.sadd.return_value = 1
        
        permissions = ['read', 'write']
        device_info = {'platform': 'web', 'browser': 'chrome'}
        
        tokens = self.session_cache.create_session(
            user_id=sample_user['id'],
            user_data=sample_user,
            permissions=permissions,
            device_info=device_info
        )
        
        assert 'session_id' in tokens
        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        assert self.mock_redis.set.call_count >= 3  # Session, token mapping, refresh token
    
    def test_get_session_valid(self, sample_user):
        """Test getting valid session"""
        session_id = str(uuid.uuid4())
        access_token = str(uuid.uuid4())
        
        # Mock token data
        self.mock_redis.get.side_effect = [
            {'session_id': session_id, 'user_id': sample_user['id']},  # Token mapping
            {  # Session data
                'session_id': session_id,
                'user_id': sample_user['id'],
                'access_token': access_token,
                'is_active': True,
                'permissions': ['read', 'write']
            }
        ]
        
        session = self.session_cache.get_session(access_token)
        
        assert session is not None
        assert session['user_id'] == sample_user['id']
        assert session['is_active'] is True
    
    def test_get_session_invalid_token(self):
        """Test getting session with invalid token"""
        self.mock_redis.get.return_value = None
        
        session = self.session_cache.get_session('invalid_token')
        
        assert session is None
    
    def test_refresh_session(self, sample_user):
        """Test session refresh"""
        session_id = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        
        self.mock_redis.get.side_effect = [
            {'session_id': session_id, 'user_id': sample_user['id']},  # Refresh token data
            {  # Session data
                'session_id': session_id,
                'user_id': sample_user['id'],
                'refresh_token': refresh_token,
                'is_active': True
            }
        ]
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = True
        
        new_tokens = self.session_cache.refresh_session(refresh_token)
        
        assert new_tokens is not None
        assert 'access_token' in new_tokens
        assert new_tokens['session_id'] == session_id
    
    def test_invalidate_session(self, sample_user):
        """Test session invalidation"""
        session_id = str(uuid.uuid4())
        access_token = str(uuid.uuid4())
        
        self.mock_redis.get.return_value = {
            'session_id': session_id,
            'user_id': sample_user['id'],
            'access_token': access_token,
            'is_active': True
        }
        self.mock_redis.set.return_value = True
        self.mock_redis.delete.return_value = True
        self.mock_redis.srem.return_value = 1
        
        result = self.session_cache.invalidate_session(session_id)
        
        assert result is True
        self.mock_redis.set.assert_called()  # Session marked as inactive
        self.mock_redis.delete.assert_called()  # Token mappings removed
    
    def test_cache_user_permissions(self, sample_user):
        """Test caching user permissions"""
        self.mock_redis.set.return_value = True
        
        permissions = ['read', 'write', 'admin']
        result = self.session_cache.cache_user_permissions(sample_user['id'], permissions)
        
        assert result is True
        self.mock_redis.set.assert_called_once()
    
    def test_get_cached_user_permissions(self, sample_user):
        """Test getting cached user permissions"""
        permissions = ['read', 'write', 'admin']
        self.mock_redis.get.return_value = {
            'permissions': permissions,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        result = self.session_cache.get_cached_user_permissions(sample_user['id'])
        
        assert result == permissions
    
    def test_check_permission(self, sample_user):
        """Test permission checking"""
        permissions = ['read', 'write']
        self.mock_redis.get.return_value = {
            'permissions': permissions,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        assert self.session_cache.check_permission(sample_user['id'], 'read') is True
        assert self.session_cache.check_permission(sample_user['id'], 'write') is True
        assert self.session_cache.check_permission(sample_user['id'], 'admin') is False


class TestMetadataCache:
    """Test metadata cache functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.metadata_cache.get_redis_client') as mock_get_redis:
            self.mock_redis = MagicMock()
            mock_get_redis.return_value = self.mock_redis
            
            self.metadata_cache = MetadataCache(self.mock_redis)
    
    def test_cache_file_metadata(self, sample_file):
        """Test caching file metadata"""
        self.mock_redis.set.return_value = True
        
        result = self.metadata_cache.cache_file_metadata(sample_file['id'], sample_file)
        
        assert result is True
        self.mock_redis.set.assert_called()
    
    def test_get_file_metadata(self, sample_file):
        """Test getting cached file metadata"""
        self.mock_redis.get.return_value = sample_file
        
        result = self.metadata_cache.get_file_metadata(sample_file['id'])
        
        assert result == sample_file
    
    def test_cache_file_tags(self, sample_file):
        """Test caching file tags"""
        tags = [
            {'name': 'important', 'color': '#ff0000'},
            {'name': 'work', 'color': '#0000ff'}
        ]
        
        self.mock_redis.set.return_value = True
        self.mock_redis.sadd.return_value = 1
        
        result = self.metadata_cache.cache_file_tags(sample_file['id'], tags)
        
        assert result is True
        self.mock_redis.set.assert_called()
        self.mock_redis.sadd.assert_called()
    
    def test_get_files_by_tag(self):
        """Test getting files by tag"""
        file_ids = {'file1', 'file2', 'file3'}
        self.mock_redis.smembers.return_value = file_ids
        
        result = self.metadata_cache.get_files_by_tag('important')
        
        assert set(result) == file_ids
    
    def test_add_file_to_user_index(self, sample_file):
        """Test adding file to user index"""
        self.mock_redis.client.zadd.return_value = 1
        self.mock_redis.hset.return_value = True
        
        file_data = {
            'file_id': sample_file['id'],
            'name': sample_file['name'],
            'modified_at': sample_file['modified_at'].isoformat()
        }
        
        result = self.metadata_cache.add_file_to_user_index(
            sample_file['user_id'],
            sample_file['id'],
            file_data
        )
        
        assert result is True
    
    def test_get_user_files(self, sample_file):
        """Test getting user files"""
        file_ids = [sample_file['id']]
        file_data = {sample_file['id']: sample_file}
        
        self.mock_redis.client.zrevrange.return_value = file_ids
        self.mock_redis.hgetall.return_value = file_data
        
        result = self.metadata_cache.get_user_files(sample_file['user_id'], limit=10)
        
        assert len(result) == 1
        assert result[0] == sample_file
    
    def test_remove_file_from_cache(self, sample_file):
        """Test removing file from cache"""
        self.mock_redis.get.return_value = sample_file
        self.mock_redis.delete.return_value = True
        self.mock_redis.client.zrem.return_value = 1
        self.mock_redis.hdel.return_value = 1
        
        result = self.metadata_cache.remove_file_from_cache(sample_file['id'])
        
        assert result is True
        assert self.mock_redis.delete.call_count >= 4  # Multiple cache entries


class TestSearchCache:
    """Test search cache functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.metadata_cache.get_redis_client') as mock_get_redis:
            self.mock_redis = MagicMock()
            mock_get_redis.return_value = self.mock_redis
            
            self.search_cache = SearchCache(self.mock_redis)
    
    def test_generate_query_hash(self):
        """Test query hash generation"""
        query = "machine learning algorithms"
        filters = {'file_type': 'document'}
        user_id = str(uuid.uuid4())
        
        hash1 = self.search_cache.generate_query_hash(query, filters, user_id)
        hash2 = self.search_cache.generate_query_hash(query, filters, user_id)
        hash3 = self.search_cache.generate_query_hash(query, {}, user_id)
        
        assert hash1 == hash2  # Same inputs should produce same hash
        assert hash1 != hash3  # Different inputs should produce different hash
        assert len(hash1) == 16  # Expected hash length
    
    def test_cache_search_results(self):
        """Test caching search results"""
        self.mock_redis.set.return_value = True
        
        query_hash = 'test_hash_123'
        results = [{'file_id': 'file1', 'name': 'test.pdf'}]
        search_params = {'query': 'test', 'limit': 10}
        
        result = self.search_cache.cache_search_results(query_hash, results, search_params)
        
        assert result is True
        self.mock_redis.set.assert_called_once()
    
    def test_get_cached_search_results(self):
        """Test getting cached search results"""
        cached_data = {
            'results': [{'file_id': 'file1', 'name': 'test.pdf'}],
            'search_params': {'query': 'test'},
            'result_count': 1,
            'cached_at': datetime.utcnow().isoformat()
        }
        self.mock_redis.get.return_value = cached_data
        
        result = self.search_cache.get_cached_search_results('test_hash_123')
        
        assert result == cached_data
    
    def test_track_popular_search(self):
        """Test tracking popular searches"""
        self.mock_redis.client.zincrby.return_value = 1
        
        result = self.search_cache.track_popular_search('machine learning', 'user123')
        
        assert result is True
        assert self.mock_redis.client.zincrby.call_count == 2  # Global and user-specific
    
    def test_get_popular_searches(self):
        """Test getting popular searches"""
        popular_searches = [('machine learning', 10.0), ('python', 8.0), ('AI', 6.0)]
        self.mock_redis.client.zrevrange.return_value = popular_searches
        
        result = self.search_cache.get_popular_searches(limit=3)
        
        assert len(result) == 3
        assert result[0] == ('machine learning', 10.0)


class TestCacheInvalidationManager:
    """Test cache invalidation functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.invalidation.get_redis_client') as mock_get_redis:
            self.mock_redis = MagicMock()
            mock_get_redis.return_value = self.mock_redis
            
            self.invalidation_manager = CacheInvalidationManager(self.mock_redis)
    
    def test_register_rule(self):
        """Test registering invalidation rule"""
        rule = InvalidationRule(
            cache_type='test_cache',
            invalidation_type=InvalidationType.IMMEDIATE,
            dependencies=['dep1', 'dep2']
        )
        
        self.invalidation_manager.register_rule('test_event', rule)
        
        assert 'test_event' in self.invalidation_manager.invalidation_rules
        assert len(self.invalidation_manager.invalidation_rules['test_event']) == 1
    
    def test_immediate_invalidation(self, sample_file):
        """Test immediate cache invalidation"""
        self.mock_redis.delete.return_value = True
        self.mock_redis.delete_pattern.return_value = 5
        self.mock_redis.clear_prefix.return_value = 10
        
        rule = InvalidationRule(
            cache_type='metadata',
            invalidation_type=InvalidationType.IMMEDIATE,
            dependencies=['search_results']
        )
        
        context = {
            'file_id': sample_file['id'],
            'user_id': sample_file['user_id']
        }
        
        self.invalidation_manager._execute_invalidation_rule(rule, context)
        
        assert self.mock_redis.delete.call_count >= 4  # Multiple cache entries
        assert self.invalidation_manager.stats['immediate_invalidations'] == 1
    
    def test_lazy_invalidation(self, sample_file):
        """Test lazy cache invalidation"""
        self.mock_redis.set.return_value = True
        
        rule = InvalidationRule(
            cache_type='metadata',
            invalidation_type=InvalidationType.LAZY,
            ttl_override=300
        )
        
        context = {'file_id': sample_file['id']}
        
        self.invalidation_manager._execute_invalidation_rule(rule, context)
        
        assert len(self.invalidation_manager.invalidation_queue) == 1
        assert self.invalidation_manager.stats['lazy_invalidations'] == 1
    
    def test_process_lazy_invalidation_queue(self):
        """Test processing lazy invalidation queue"""
        # Add item to queue
        rule = InvalidationRule(
            cache_type='metadata',
            invalidation_type=InvalidationType.LAZY
        )
        
        self.invalidation_manager.invalidation_queue.append({
            'rule': rule,
            'context': {'file_id': 'test_file'},
            'queued_at': datetime.utcnow().isoformat()
        })
        
        self.mock_redis.delete.return_value = True
        
        processed = self.invalidation_manager.process_lazy_invalidation_queue()
        
        assert processed == 1
        assert len(self.invalidation_manager.invalidation_queue) == 0
    
    def test_invalidate_by_pattern(self):
        """Test pattern-based invalidation"""
        self.mock_redis.delete_pattern.return_value = 5
        
        result = self.invalidation_manager.invalidate_by_pattern('metadata', 'user123:*')
        
        assert result == 5
        self.mock_redis.delete_pattern.assert_called_once()


class TestDistributedLock:
    """Test distributed lock functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.distributed_locks.get_redis_client') as mock_get_redis:
            self.mock_redis = MagicMock()
            mock_get_redis.return_value = self.mock_redis
            
            self.lock = DistributedLock(self.mock_redis)
    
    def test_lock_key_generation(self):
        """Test lock key generation"""
        key = self.lock._make_lock_key('test_resource')
        assert key == 'lock:test_resource'
    
    def test_owner_id_generation(self):
        """Test owner ID generation"""
        owner_id = self.lock._make_owner_id('client123')
        
        assert 'client123' in owner_id
        assert self.lock.instance_id in owner_id
    
    def test_acquire_lock_success(self):
        """Test successful lock acquisition"""
        self.mock_redis.client.eval.return_value = 1  # Lock acquired
        
        lock_id = self.lock.acquire('test_resource', timeout=30, blocking=False)
        
        assert lock_id is not None
        assert self.lock.stats['locks_acquired'] == 1
        self.mock_redis.client.eval.assert_called_once()
    
    def test_acquire_lock_failure(self):
        """Test failed lock acquisition"""
        self.mock_redis.client.eval.return_value = 0  # Lock not acquired
        
        lock_id = self.lock.acquire('test_resource', timeout=30, blocking=False)
        
        assert lock_id is None
        assert self.lock.stats['lock_conflicts'] == 1
    
    def test_release_lock_success(self):
        """Test successful lock release"""
        self.mock_redis.client.eval.return_value = 1  # Lock released
        
        result = self.lock.release('test_resource', 'test_lock_id')
        
        assert result is True
        assert self.lock.stats['locks_released'] == 1
    
    def test_release_lock_failure(self):
        """Test failed lock release"""
        self.mock_redis.client.eval.return_value = 0  # Lock not released
        
        result = self.lock.release('test_resource', 'wrong_lock_id')
        
        assert result is False
    
    def test_extend_lock(self):
        """Test lock extension"""
        self.mock_redis.client.eval.return_value = 1  # Lock extended
        
        result = self.lock.extend('test_resource', 'test_lock_id', 30)
        
        assert result is True
    
    def test_is_locked(self):
        """Test checking if resource is locked"""
        self.mock_redis.exists.return_value = True
        
        result = self.lock.is_locked('test_resource')
        
        assert result is True
    
    def test_force_release(self):
        """Test force releasing a lock"""
        self.mock_redis.client.delete.return_value = 1
        
        result = self.lock.force_release('test_resource')
        
        assert result is True
    
    def test_lock_context_manager(self):
        """Test lock context manager"""
        self.mock_redis.client.eval.side_effect = [1, 1]  # Acquire and release
        
        with self.lock.lock('test_resource') as lock_id:
            assert lock_id is not None
        
        assert self.lock.stats['locks_acquired'] == 1
        assert self.lock.stats['locks_released'] == 1


class TestSyncCoordinator:
    """Test sync coordinator functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        with patch('cache.distributed_locks.DistributedLock') as mock_lock_class:
            self.mock_lock = MagicMock()
            mock_lock_class.return_value = self.mock_lock
            
            self.coordinator = SyncCoordinator(self.mock_lock)
    
    def test_sync_file_operation(self, sample_file):
        """Test file sync coordination"""
        self.mock_lock.lock.return_value.__enter__ = Mock(return_value='test_lock_id')
        self.mock_lock.lock.return_value.__exit__ = Mock(return_value=None)
        
        with self.coordinator.sync_file(
            sample_file['id'],
            'file_upload',
            sample_file['user_id']
        ) as lock_id:
            assert lock_id == 'test_lock_id'
        
        self.mock_lock.lock.assert_called_once()
    
    def test_sync_user_files(self, sample_user):
        """Test user files sync coordination"""
        self.mock_lock.lock.return_value.__enter__ = Mock(return_value='test_lock_id')
        self.mock_lock.lock.return_value.__exit__ = Mock(return_value=None)
        
        with self.coordinator.sync_user_files(
            sample_user['id'],
            'batch_sync'
        ) as lock_id:
            assert lock_id == 'test_lock_id'
        
        self.mock_lock.lock.assert_called_once()
    
    def test_resolve_conflict(self, sample_file, sample_user):
        """Test conflict resolution coordination"""
        self.mock_lock.lock.return_value.__enter__ = Mock(return_value='test_lock_id')
        self.mock_lock.lock.return_value.__exit__ = Mock(return_value=None)
        
        conflict_data = {
            'type': 'version_conflict',
            'local_version': 1,
            'remote_version': 2
        }
        
        with self.coordinator.resolve_conflict(
            sample_file['id'],
            sample_user['id'],
            conflict_data
        ) as lock_id:
            assert lock_id == 'test_lock_id'


@pytest.mark.unit
class TestCacheServiceIntegration:
    """Integration tests for cache service components"""
    
    def test_complete_session_flow(self, sample_user):
        """Test complete session management flow"""
        with patch('cache.session_cache.get_redis_client') as mock_get_redis:
            mock_redis = MagicMock()
            mock_get_redis.return_value = mock_redis
            mock_redis.set.return_value = True
            mock_redis.sadd.return_value = 1
            mock_redis.get.side_effect = [
                {'session_id': 'sess123', 'user_id': sample_user['id']},
                {
                    'session_id': 'sess123',
                    'user_id': sample_user['id'],
                    'is_active': True,
                    'permissions': ['read', 'write']
                }
            ]
            
            session_cache = SessionCache(mock_redis)
            
            # Create session
            tokens = session_cache.create_session(
                sample_user['id'],
                sample_user,
                ['read', 'write']
            )
            
            assert 'access_token' in tokens
            
            # Get session
            session = session_cache.get_session(tokens['access_token'])
            assert session['user_id'] == sample_user['id']
    
    def test_cache_invalidation_flow(self, sample_file):
        """Test cache invalidation flow"""
        with patch('cache.invalidation.get_redis_client') as mock_get_redis:
            mock_redis = MagicMock()
            mock_get_redis.return_value = mock_redis
            mock_redis.delete.return_value = True
            mock_redis.clear_prefix.return_value = 5
            
            manager = CacheInvalidationManager(mock_redis)
            
            # Register rule
            rule = InvalidationRule(
                cache_type='metadata',
                invalidation_type=InvalidationType.IMMEDIATE,
                dependencies=['search_results']
            )
            manager.register_rule('file_update', rule)
            
            # Trigger invalidation
            manager.invalidate('file_update', {
                'file_id': sample_file['id'],
                'user_id': sample_file['user_id']
            })
            
            assert manager.stats['immediate_invalidations'] == 1
    
    def test_distributed_locking_flow(self):
        """Test distributed locking flow"""
        with patch('cache.distributed_locks.get_redis_client') as mock_get_redis:
            mock_redis = MagicMock()
            mock_get_redis.return_value = mock_redis
            mock_redis.client.eval.side_effect = [1, 1]  # Acquire and release
            
            lock = DistributedLock(mock_redis)
            
            # Acquire lock
            lock_id = lock.acquire('test_resource', blocking=False)
            assert lock_id is not None
            
            # Release lock
            result = lock.release('test_resource', lock_id)
            assert result is True
            
            assert lock.stats['locks_acquired'] == 1
            assert lock.stats['locks_released'] == 1