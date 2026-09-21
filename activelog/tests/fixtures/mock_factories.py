"""
Mock factories for creating test doubles and stubs
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from faker import Faker
import asyncio

fake = Faker()


class MockFactories:
    """Factory for creating various mock objects and test doubles"""
    
    @staticmethod
    def create_mock_database_session():
        """Create mock database session"""
        
        mock_session = MagicMock()
        
        # Mock common database operations
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Mock query results
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_result.fetchone = MagicMock(return_value=None)
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        # Mock context manager
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        return mock_session
    
    @staticmethod
    def create_mock_redis_client():
        """Create mock Redis client"""
        
        mock_redis = MagicMock()
        
        # In-memory store for testing
        store = {}
        
        def mock_get(key):
            return store.get(key)
        
        def mock_set(key, value, ex=None):
            store[key] = value
            return True
        
        def mock_delete(*keys):
            deleted = 0
            for key in keys:
                if key in store:
                    del store[key]
                    deleted += 1
            return deleted
        
        def mock_exists(key):
            return key in store
        
        def mock_keys(pattern="*"):
            if pattern == "*":
                return list(store.keys())
            # Simple pattern matching
            import re
            regex = pattern.replace("*", ".*")
            return [k for k in store.keys() if re.match(regex, k)]
        
        mock_redis.get = mock_get
        mock_redis.set = mock_set
        mock_redis.delete = mock_delete
        mock_redis.exists = mock_exists
        mock_redis.keys = mock_keys
        mock_redis.ping = MagicMock(return_value=True)
        
        # Hash operations
        hash_store = {}
        
        def mock_hget(name, key):
            return hash_store.get(name, {}).get(key)
        
        def mock_hset(name, key, value):
            if name not in hash_store:
                hash_store[name] = {}
            hash_store[name][key] = value
            return True
        
        def mock_hgetall(name):
            return hash_store.get(name, {})
        
        mock_redis.hget = mock_hget
        mock_redis.hset = mock_hset
        mock_redis.hgetall = mock_hgetall
        
        # Set operations
        set_store = {}
        
        def mock_sadd(name, *values):
            if name not in set_store:
                set_store[name] = set()
            set_store[name].update(values)
            return len(values)
        
        def mock_smembers(name):
            return set_store.get(name, set())
        
        mock_redis.sadd = mock_sadd
        mock_redis.smembers = mock_smembers
        
        return mock_redis
    
    @staticmethod
    def create_mock_s3_client():
        """Create mock AWS S3 client"""
        
        mock_s3 = MagicMock()
        
        # Mock file store
        file_store = {}
        
        def mock_upload_fileobj(fileobj, bucket, key, **kwargs):
            file_store[f"{bucket}/{key}"] = {
                'content': fileobj.read() if hasattr(fileobj, 'read') else str(fileobj),
                'metadata': kwargs.get('Metadata', {}),
                'uploaded_at': datetime.utcnow()
            }
            return None
        
        def mock_download_fileobj(bucket, key, fileobj, **kwargs):
            file_key = f"{bucket}/{key}"
            if file_key in file_store:
                content = file_store[file_key]['content']
                if hasattr(fileobj, 'write'):
                    fileobj.write(content if isinstance(content, bytes) else content.encode())
                return None
            else:
                from botocore.exceptions import ClientError
                raise ClientError(
                    error_response={'Error': {'Code': 'NoSuchKey'}},
                    operation_name='GetObject'
                )
        
        def mock_head_object(Bucket, Key):
            file_key = f"{Bucket}/{Key}"
            if file_key in file_store:
                file_data = file_store[file_key]
                content = file_data['content']
                return {
                    'ContentLength': len(content) if isinstance(content, (str, bytes)) else 0,
                    'LastModified': file_data['uploaded_at'],
                    'ETag': f'"{hash(content) % 10000000000:010d}"',
                    'Metadata': file_data['metadata']
                }
            else:
                from botocore.exceptions import ClientError
                raise ClientError(
                    error_response={'Error': {'Code': 'NoSuchKey'}},
                    operation_name='HeadObject'
                )
        
        def mock_list_objects_v2(Bucket, Prefix="", **kwargs):
            matching_files = []
            for file_key, file_data in file_store.items():
                if file_key.startswith(f"{Bucket}/{Prefix}"):
                    key = file_key[len(f"{Bucket}/"):]
                    content = file_data['content']
                    matching_files.append({
                        'Key': key,
                        'Size': len(content) if isinstance(content, (str, bytes)) else 0,
                        'LastModified': file_data['uploaded_at'],
                        'ETag': f'"{hash(content) % 10000000000:010d}"'
                    })
            
            return {
                'Contents': matching_files,
                'IsTruncated': False,
                'KeyCount': len(matching_files)
            }
        
        def mock_delete_object(Bucket, Key):
            file_key = f"{Bucket}/{Key}"
            if file_key in file_store:
                del file_store[file_key]
            return {}
        
        mock_s3.upload_fileobj = mock_upload_fileobj
        mock_s3.download_fileobj = mock_download_fileobj
        mock_s3.head_object = mock_head_object
        mock_s3.list_objects_v2 = mock_list_objects_v2
        mock_s3.delete_object = mock_delete_object
        
        return mock_s3
    
    @staticmethod
    def create_mock_openai_client():
        """Create mock OpenAI client"""
        
        mock_openai = MagicMock()
        
        # Mock chat completions
        def mock_chat_create(**kwargs):
            messages = kwargs.get('messages', [])
            model = kwargs.get('model', 'gpt-3.5-turbo')
            
            # Generate realistic response based on last message
            last_message = messages[-1] if messages else {'content': ''}
            prompt_length = len(last_message.get('content', ''))
            
            response_content = fake.text(max_nb_chars=min(prompt_length * 2, 500))
            
            return {
                'id': f'chatcmpl-{fake.bothify("?????????#######")}',
                'object': 'chat.completion',
                'created': int(datetime.utcnow().timestamp()),
                'model': model,
                'choices': [{
                    'index': 0,
                    'message': {
                        'role': 'assistant',
                        'content': response_content
                    },
                    'finish_reason': 'stop'
                }],
                'usage': {
                    'prompt_tokens': max(1, prompt_length // 4),
                    'completion_tokens': max(1, len(response_content) // 4),
                    'total_tokens': max(2, (prompt_length + len(response_content)) // 4)
                }
            }
        
        mock_openai.chat.completions.create = mock_chat_create
        
        # Mock embeddings
        def mock_embeddings_create(**kwargs):
            input_text = kwargs.get('input', '')
            model = kwargs.get('model', 'text-embedding-ada-002')
            
            # Generate random embedding vector
            dimension = 1536 if 'ada-002' in model else 512
            embedding = [random.gauss(0, 0.1) for _ in range(dimension)]
            
            # Normalize to unit vector
            import math
            norm = math.sqrt(sum(x*x for x in embedding))
            if norm > 0:
                embedding = [x/norm for x in embedding]
            
            return {
                'object': 'list',
                'data': [{
                    'object': 'embedding',
                    'index': 0,
                    'embedding': embedding
                }],
                'model': model,
                'usage': {
                    'prompt_tokens': max(1, len(str(input_text)) // 4),
                    'total_tokens': max(1, len(str(input_text)) // 4)
                }
            }
        
        mock_openai.embeddings.create = mock_embeddings_create
        
        return mock_openai
    
    @staticmethod
    def create_mock_elasticsearch_client():
        """Create mock Elasticsearch client"""
        
        mock_es = MagicMock()
        
        # Mock document store
        doc_store = {}
        
        def mock_index(index, id=None, body=None, **kwargs):
            doc_id = id or str(uuid.uuid4())
            doc_store[f"{index}/{doc_id}"] = {
                'source': body,
                'indexed_at': datetime.utcnow()
            }
            return {
                '_index': index,
                '_id': doc_id,
                '_version': 1,
                'result': 'created'
            }
        
        def mock_get(index, id):
            doc_key = f"{index}/{id}"
            if doc_key in doc_store:
                doc_data = doc_store[doc_key]
                return {
                    '_index': index,
                    '_id': id,
                    '_version': 1,
                    'found': True,
                    '_source': doc_data['source']
                }
            else:
                from elasticsearch.exceptions import NotFoundError
                raise NotFoundError(404, 'not_found', {'found': False})
        
        def mock_search(index=None, body=None, **kwargs):
            # Simple search simulation
            query = body.get('query', {}) if body else {}
            size = body.get('size', 10) if body else 10
            
            # Find matching documents
            matching_docs = []
            for doc_key, doc_data in doc_store.items():
                doc_index, doc_id = doc_key.split('/', 1)
                if index is None or doc_index == index:
                    # Simple text matching
                    source = str(doc_data['source'])
                    if not query or any(term.lower() in source.lower() for term in query.get('match', {}).values()):
                        matching_docs.append({
                            '_index': doc_index,
                            '_id': doc_id,
                            '_score': random.uniform(0.1, 1.0),
                            '_source': doc_data['source']
                        })
            
            # Sort by score and limit results
            matching_docs.sort(key=lambda x: x['_score'], reverse=True)
            matching_docs = matching_docs[:size]
            
            return {
                'took': random.randint(1, 100),
                'timed_out': False,
                'hits': {
                    'total': {'value': len(matching_docs), 'relation': 'eq'},
                    'max_score': matching_docs[0]['_score'] if matching_docs else 0,
                    'hits': matching_docs
                }
            }
        
        def mock_delete(index, id):
            doc_key = f"{index}/{id}"
            if doc_key in doc_store:
                del doc_store[doc_key]
                return {'result': 'deleted'}
            else:
                return {'result': 'not_found'}
        
        mock_es.index = mock_index
        mock_es.get = mock_get
        mock_es.search = mock_search
        mock_es.delete = mock_delete
        
        return mock_es
    
    @staticmethod
    def create_mock_file_system():
        """Create mock file system operations"""
        
        mock_fs = MagicMock()
        
        # Mock file store
        fs_store = {}
        
        def mock_exists(path):
            return path in fs_store
        
        def mock_read_file(path, mode='r'):
            if path in fs_store:
                content = fs_store[path]['content']
                if 'b' in mode:
                    return content.encode() if isinstance(content, str) else content
                return content
            else:
                raise FileNotFoundError(f"File not found: {path}")
        
        def mock_write_file(path, content, mode='w'):
            if 'b' in mode and isinstance(content, str):
                content = content.encode()
            elif 'b' not in mode and isinstance(content, bytes):
                content = content.decode()
            
            fs_store[path] = {
                'content': content,
                'created_at': datetime.utcnow(),
                'size': len(content)
            }
            return len(content)
        
        def mock_delete_file(path):
            if path in fs_store:
                del fs_store[path]
                return True
            return False
        
        def mock_list_files(directory):
            return [path for path in fs_store.keys() if path.startswith(directory)]
        
        def mock_get_file_stats(path):
            if path in fs_store:
                file_data = fs_store[path]
                return {
                    'size': file_data['size'],
                    'created': file_data['created_at'],
                    'modified': file_data['created_at']
                }
            else:
                raise FileNotFoundError(f"File not found: {path}")
        
        mock_fs.exists = mock_exists
        mock_fs.read_file = mock_read_file
        mock_fs.write_file = mock_write_file
        mock_fs.delete_file = mock_delete_file
        mock_fs.list_files = mock_list_files
        mock_fs.get_file_stats = mock_get_file_stats
        
        return mock_fs
    
    @staticmethod
    def create_mock_http_client():
        """Create mock HTTP client"""
        
        mock_client = MagicMock()
        
        # Mock response store
        response_store = {}
        
        def setup_response(url, method='GET', status=200, json_data=None, text=None, headers=None):
            """Helper to set up mock responses"""
            response_store[f"{method.upper()}:{url}"] = {
                'status': status,
                'json': json_data,
                'text': text or (str(json_data) if json_data else ''),
                'headers': headers or {}
            }
        
        def mock_request(method, url, **kwargs):
            key = f"{method.upper()}:{url}"
            if key in response_store:
                response_data = response_store[key]
                
                mock_response = MagicMock()
                mock_response.status_code = response_data['status']
                mock_response.json = MagicMock(return_value=response_data['json'])
                mock_response.text = response_data['text']
                mock_response.headers = response_data['headers']
                mock_response.ok = 200 <= response_data['status'] < 400
                
                return mock_response
            else:
                # Default response
                mock_response = MagicMock()
                mock_response.status_code = 404
                mock_response.json = MagicMock(return_value={'error': 'Not found'})
                mock_response.text = 'Not found'
                mock_response.ok = False
                
                return mock_response
        
        mock_client.request = mock_request
        mock_client.get = lambda url, **kwargs: mock_request('GET', url, **kwargs)
        mock_client.post = lambda url, **kwargs: mock_request('POST', url, **kwargs)
        mock_client.put = lambda url, **kwargs: mock_request('PUT', url, **kwargs)
        mock_client.delete = lambda url, **kwargs: mock_request('DELETE', url, **kwargs)
        mock_client.setup_response = setup_response
        
        return mock_client
    
    @staticmethod
    def create_mock_email_service():
        """Create mock email service"""
        
        mock_email = MagicMock()
        
        # Email store for testing
        sent_emails = []
        
        def mock_send_email(to, subject, body, from_addr=None, **kwargs):
            email_data = {
                'id': str(uuid.uuid4()),
                'to': to if isinstance(to, list) else [to],
                'subject': subject,
                'body': body,
                'from': from_addr or 'noreply@example.com',
                'sent_at': datetime.utcnow(),
                'status': 'sent',
                **kwargs
            }
            sent_emails.append(email_data)
            return email_data['id']
        
        def mock_get_sent_emails():
            return sent_emails.copy()
        
        def mock_clear_sent_emails():
            sent_emails.clear()
        
        mock_email.send_email = mock_send_email
        mock_email.get_sent_emails = mock_get_sent_emails
        mock_email.clear_sent_emails = mock_clear_sent_emails
        
        return mock_email
    
    @staticmethod
    def create_mock_queue_service():
        """Create mock message queue service"""
        
        mock_queue = MagicMock()
        
        # Queue storage
        queues = {}
        
        def mock_publish(queue_name, message, **kwargs):
            if queue_name not in queues:
                queues[queue_name] = []
            
            message_data = {
                'id': str(uuid.uuid4()),
                'body': message,
                'published_at': datetime.utcnow(),
                'metadata': kwargs
            }
            queues[queue_name].append(message_data)
            return message_data['id']
        
        def mock_consume(queue_name, timeout=30):
            if queue_name in queues and queues[queue_name]:
                return queues[queue_name].pop(0)
            return None
        
        def mock_get_queue_size(queue_name):
            return len(queues.get(queue_name, []))
        
        def mock_purge_queue(queue_name):
            if queue_name in queues:
                count = len(queues[queue_name])
                queues[queue_name] = []
                return count
            return 0
        
        mock_queue.publish = mock_publish
        mock_queue.consume = mock_consume
        mock_queue.get_queue_size = mock_get_queue_size
        mock_queue.purge_queue = mock_purge_queue
        
        return mock_queue
    
    @staticmethod
    def create_mock_websocket():
        """Create mock WebSocket connection"""
        
        mock_ws = MagicMock()
        
        # Message buffers
        sent_messages = []
        received_messages = []
        
        def mock_send(message):
            sent_messages.append({
                'message': message,
                'sent_at': datetime.utcnow()
            })
        
        def mock_receive():
            if received_messages:
                return received_messages.pop(0)['message']
            return None
        
        def mock_close():
            mock_ws.closed = True
        
        def mock_add_received_message(message):
            """Helper to simulate receiving messages"""
            received_messages.append({
                'message': message,
                'received_at': datetime.utcnow()
            })
        
        mock_ws.send = mock_send
        mock_ws.receive = mock_receive
        mock_ws.close = mock_close
        mock_ws.closed = False
        mock_ws.sent_messages = sent_messages
        mock_ws.add_received_message = mock_add_received_message
        
        return mock_ws
    
    @staticmethod
    def create_mock_cache_service():
        """Create mock cache service"""
        
        mock_cache = MagicMock()
        
        # Cache storage with TTL
        cache_store = {}
        
        def mock_get(key):
            if key in cache_store:
                item = cache_store[key]
                if item['expires_at'] > datetime.utcnow():
                    return item['value']
                else:
                    del cache_store[key]
            return None
        
        def mock_set(key, value, ttl=3600):
            cache_store[key] = {
                'value': value,
                'set_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(seconds=ttl)
            }
        
        def mock_delete(key):
            if key in cache_store:
                del cache_store[key]
                return True
            return False
        
        def mock_exists(key):
            if key in cache_store:
                item = cache_store[key]
                if item['expires_at'] > datetime.utcnow():
                    return True
                else:
                    del cache_store[key]
            return False
        
        def mock_clear():
            cache_store.clear()
        
        def mock_get_stats():
            active_items = sum(1 for item in cache_store.values() 
                             if item['expires_at'] > datetime.utcnow())
            return {
                'active_keys': active_items,
                'total_keys_ever': len(cache_store),
                'hit_rate': random.uniform(0.7, 0.9),
                'memory_usage_mb': active_items * 0.1  # Rough estimate
            }
        
        mock_cache.get = mock_get
        mock_cache.set = mock_set
        mock_cache.delete = mock_delete
        mock_cache.exists = mock_exists
        mock_cache.clear = mock_clear
        mock_cache.get_stats = mock_get_stats
        
        return mock_cache
    
    @staticmethod
    def create_mock_service_collection():
        """Create collection of commonly used mock services"""
        
        return {
            'database': MockFactories.create_mock_database_session(),
            'redis': MockFactories.create_mock_redis_client(),
            's3': MockFactories.create_mock_s3_client(),
            'openai': MockFactories.create_mock_openai_client(),
            'elasticsearch': MockFactories.create_mock_elasticsearch_client(),
            'file_system': MockFactories.create_mock_file_system(),
            'http_client': MockFactories.create_mock_http_client(),
            'email': MockFactories.create_mock_email_service(),
            'queue': MockFactories.create_mock_queue_service(),
            'websocket': MockFactories.create_mock_websocket(),
            'cache': MockFactories.create_mock_cache_service()
        }
    
    @staticmethod
    def patch_all_services():
        """Create a context manager that patches all common services"""
        
        patches = [
            patch('sqlalchemy.create_engine'),
            patch('redis.Redis'),
            patch('boto3.client'),
            patch('openai.OpenAI'),
            patch('elasticsearch.Elasticsearch')
        ]
        
        class ServicePatchManager:
            def __init__(self, patches):
                self.patches = patches
                self.mocks = {}
            
            def __enter__(self):
                mock_services = MockFactories.create_mock_service_collection()
                
                for i, p in enumerate(self.patches):
                    mock = p.__enter__()
                    service_name = list(mock_services.keys())[i]
                    mock.return_value = mock_services[service_name]
                    self.mocks[service_name] = mock_services[service_name]
                
                return self.mocks
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                for p in reversed(self.patches):
                    p.__exit__(exc_type, exc_val, exc_tb)
        
        return ServicePatchManager(patches)