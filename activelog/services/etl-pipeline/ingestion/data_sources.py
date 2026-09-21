"""
Data Sources Configuration and Connectors
Comprehensive data ingestion from 50+ sources
"""

import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Iterator, AsyncIterator, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import pandas as pd
import asyncpg
import aioredis
import motor.motor_asyncio
from sqlalchemy import create_engine, MetaData, Table
from elasticsearch import AsyncElasticsearch
from kafka import KafkaConsumer, KafkaProducer
import boto3
from google.cloud import storage as gcs
from azure.storage.blob import BlobServiceClient
import paramiko
import ftplib
from pathlib import Path
import xml.etree.ElementTree as ET
import csv
import yaml
import toml

logger = logging.getLogger(__name__)

class DataSourceType(str, Enum):
    DATABASE = "database"
    API = "api"
    FILE = "file"
    STREAM = "stream"
    CLOUD_STORAGE = "cloud_storage"
    MESSAGE_QUEUE = "message_queue"
    NOSQL = "nosql"
    SEARCH_ENGINE = "search_engine"
    TIME_SERIES = "time_series"
    GRAPH = "graph"

class DataFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    AVRO = "avro"
    XML = "xml"
    YAML = "yaml"
    TOML = "toml"
    EXCEL = "excel"
    BINARY = "binary"
    TEXT = "text"

@dataclass
class DataSourceConfig:
    source_id: str
    source_type: DataSourceType
    connection_params: Dict[str, Any]
    data_format: DataFormat
    extraction_config: Dict[str, Any] = field(default_factory=dict)
    schedule_config: Dict[str, Any] = field(default_factory=dict)
    transformation_config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    priority: int = 1  # 1=highest, 5=lowest
    tags: List[str] = field(default_factory=list)

class BaseDataSource(ABC):
    """Abstract base class for data sources"""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self.connection = None
        self.is_connected = False
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection to data source"""
        pass
    
    @abstractmethod
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        """Extract data from source"""
        pass
    
    @abstractmethod
    async def get_schema(self) -> Dict[str, Any]:
        """Get schema information"""
        pass
    
    async def health_check(self) -> bool:
        """Check if data source is healthy"""
        try:
            if not self.is_connected:
                await self.connect()
            return True
        except Exception as e:
            logger.error(f"Health check failed for {self.config.source_id}: {e}")
            return False

# Database Sources
class PostgreSQLSource(BaseDataSource):
    """PostgreSQL data source"""
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            self.connection = await asyncpg.create_pool(
                host=params['host'],
                port=params.get('port', 5432),
                user=params['username'],
                password=params['password'],
                database=params['database'],
                min_size=1,
                max_size=10
            )
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False
    
    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        if not self.is_connected:
            await self.connect()
        
        query = query_params.get('query', 'SELECT * FROM information_schema.tables')
        batch_size = query_params.get('batch_size', 1000)
        
        async with self.connection.acquire() as conn:
            async with conn.transaction():
                async for record in conn.cursor(query):
                    yield dict(record)
    
    async def get_schema(self) -> Dict[str, Any]:
        query = """
        SELECT table_schema, table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        ORDER BY table_schema, table_name, ordinal_position
        """
        
        schema = {}
        async with self.connection.acquire() as conn:
            async for record in conn.cursor(query):
                table_key = f"{record['table_schema']}.{record['table_name']}"
                if table_key not in schema:
                    schema[table_key] = []
                schema[table_key].append({
                    'column': record['column_name'],
                    'type': record['data_type'],
                    'nullable': record['is_nullable']
                })
        
        return schema

class MySQLSource(BaseDataSource):
    """MySQL data source"""
    
    async def connect(self) -> bool:
        try:
            import aiomysql
            params = self.config.connection_params
            self.connection = await aiomysql.create_pool(
                host=params['host'],
                port=params.get('port', 3306),
                user=params['username'],
                password=params['password'],
                db=params['database'],
                minsize=1,
                maxsize=10
            )
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False
    
    async def disconnect(self):
        if self.connection:
            self.connection.close()
            await self.connection.wait_closed()
            self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        query = query_params.get('query', 'SHOW TABLES')
        
        async with self.connection.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query)
                async for row in cursor:
                    yield row
    
    async def get_schema(self) -> Dict[str, Any]:
        query = """
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
        """
        
        schema = {}
        async with self.connection.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(query)
                async for record in cursor:
                    table_key = f"{record['TABLE_SCHEMA']}.{record['TABLE_NAME']}"
                    if table_key not in schema:
                        schema[table_key] = []
                    schema[table_key].append({
                        'column': record['COLUMN_NAME'],
                        'type': record['DATA_TYPE'],
                        'nullable': record['IS_NULLABLE']
                    })
        
        return schema

class MongoDBSource(BaseDataSource):
    """MongoDB data source"""
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            connection_string = f"mongodb://{params['username']}:{params['password']}@{params['host']}:{params.get('port', 27017)}/{params['database']}"
            client = motor.motor_asyncio.AsyncIOMotorClient(connection_string)
            self.connection = client[params['database']]
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    async def disconnect(self):
        if self.connection:
            self.connection.client.close()
            self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        collection_name = query_params.get('collection', 'test')
        query = query_params.get('query', {})
        batch_size = query_params.get('batch_size', 1000)
        
        collection = self.connection[collection_name]
        cursor = collection.find(query).batch_size(batch_size)
        
        async for document in cursor:
            # Convert ObjectId to string for JSON serialization
            if '_id' in document:
                document['_id'] = str(document['_id'])
            yield document
    
    async def get_schema(self) -> Dict[str, Any]:
        collections = await self.connection.list_collection_names()
        schema = {}
        
        for collection_name in collections:
            collection = self.connection[collection_name]
            # Sample documents to infer schema
            sample_docs = await collection.find().limit(100).to_list(length=100)
            
            if sample_docs:
                field_types = {}
                for doc in sample_docs:
                    for field, value in doc.items():
                        field_type = type(value).__name__
                        if field not in field_types:
                            field_types[field] = set()
                        field_types[field].add(field_type)
                
                schema[collection_name] = {
                    field: list(types) for field, types in field_types.items()
                }
        
        return schema

class RedisSource(BaseDataSource):
    """Redis data source"""
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            self.connection = await aioredis.create_redis_pool(
                f"redis://{params['host']}:{params.get('port', 6379)}",
                password=params.get('password'),
                db=params.get('db', 0)
            )
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            return False
    
    async def disconnect(self):
        if self.connection:
            self.connection.close()
            await self.connection.wait_closed()
            self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        pattern = query_params.get('pattern', '*')
        keys = await self.connection.keys(pattern)
        
        for key in keys:
            key_type = await self.connection.type(key)
            key_str = key.decode('utf-8')
            
            if key_type == b'string':
                value = await self.connection.get(key)
                yield {'key': key_str, 'type': 'string', 'value': value.decode('utf-8')}
            elif key_type == b'hash':
                value = await self.connection.hgetall(key)
                decoded_value = {k.decode('utf-8'): v.decode('utf-8') for k, v in value.items()}
                yield {'key': key_str, 'type': 'hash', 'value': decoded_value}
            elif key_type == b'list':
                value = await self.connection.lrange(key, 0, -1)
                decoded_value = [v.decode('utf-8') for v in value]
                yield {'key': key_str, 'type': 'list', 'value': decoded_value}
    
    async def get_schema(self) -> Dict[str, Any]:
        info = await self.connection.info()
        return {
            'redis_info': info,
            'keyspace': await self.connection.info('keyspace')
        }

class ElasticsearchSource(BaseDataSource):
    """Elasticsearch data source"""
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            self.connection = AsyncElasticsearch(
                [{'host': params['host'], 'port': params.get('port', 9200)}],
                http_auth=(params.get('username'), params.get('password')),
                use_ssl=params.get('use_ssl', False)
            )
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            return False
    
    async def disconnect(self):
        if self.connection:
            await self.connection.close()
            self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        index = query_params.get('index', '*')
        query = query_params.get('query', {'match_all': {}})
        size = query_params.get('size', 1000)
        
        try:
            response = await self.connection.search(
                index=index,
                body={'query': query, 'size': size},
                scroll='5m'
            )
            
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            
            for hit in hits:
                yield {
                    '_id': hit['_id'],
                    '_index': hit['_index'],
                    '_source': hit['_source']
                }
            
            while hits:
                response = await self.connection.scroll(scroll_id=scroll_id, scroll='5m')
                scroll_id = response['_scroll_id']
                hits = response['hits']['hits']
                
                for hit in hits:
                    yield {
                        '_id': hit['_id'],
                        '_index': hit['_index'],
                        '_source': hit['_source']
                    }
            
            await self.connection.clear_scroll(scroll_id=scroll_id)
            
        except Exception as e:
            logger.error(f"Error extracting from Elasticsearch: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        try:
            indices = await self.connection.indices.get('*')
            schema = {}
            
            for index_name, index_info in indices.items():
                mappings = index_info.get('mappings', {})
                properties = mappings.get('properties', {})
                
                schema[index_name] = {
                    'properties': properties,
                    'settings': index_info.get('settings', {})
                }
            
            return schema
        except Exception as e:
            logger.error(f"Error getting Elasticsearch schema: {e}")
            return {}

# API Sources
class RESTAPISource(BaseDataSource):
    """REST API data source"""
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            headers = params.get('headers', {})
            
            # Test connection with a simple request
            async with aiohttp.ClientSession(headers=headers) as session:
                test_url = params.get('test_url', params['base_url'])
                async with session.get(test_url, timeout=10) as response:
                    self.is_connected = response.status == 200
                    return self.is_connected
        except Exception as e:
            logger.error(f"Failed to connect to REST API: {e}")
            return False
    
    async def disconnect(self):
        self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        params = self.config.connection_params
        base_url = params['base_url']
        headers = params.get('headers', {})
        endpoints = query_params.get('endpoints', ['/'])
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for endpoint in endpoints:
                url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
                
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Handle different response structures
                            if isinstance(data, list):
                                for item in data:
                                    yield {'endpoint': endpoint, 'data': item}
                            elif isinstance(data, dict):
                                yield {'endpoint': endpoint, 'data': data}
                            else:
                                yield {'endpoint': endpoint, 'data': data}
                        else:
                            logger.warning(f"API request failed: {response.status} for {url}")
                except Exception as e:
                    logger.error(f"Error fetching from {url}: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        params = self.config.connection_params
        schema_url = params.get('schema_url')
        
        if schema_url:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(schema_url) as response:
                        if response.status == 200:
                            return await response.json()
                except Exception as e:
                    logger.error(f"Error fetching schema from {schema_url}: {e}")
        
        return {'message': 'Schema endpoint not available'}

class GraphQLSource(BaseDataSource):
    """GraphQL API data source"""
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            headers = params.get('headers', {})
            
            # Test with introspection query
            introspection_query = """
            query IntrospectionQuery {
                __schema {
                    queryType { name }
                }
            }
            """
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(
                    params['endpoint'],
                    json={'query': introspection_query},
                    timeout=10
                ) as response:
                    self.is_connected = response.status == 200
                    return self.is_connected
        except Exception as e:
            logger.error(f"Failed to connect to GraphQL API: {e}")
            return False
    
    async def disconnect(self):
        self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        params = self.config.connection_params
        endpoint = params['endpoint']
        headers = params.get('headers', {})
        queries = query_params.get('queries', [])
        
        async with aiohttp.ClientSession(headers=headers) as session:
            for query_info in queries:
                query = query_info.get('query', '')
                variables = query_info.get('variables', {})
                
                payload = {'query': query}
                if variables:
                    payload['variables'] = variables
                
                try:
                    async with session.post(endpoint, json=payload) as response:
                        if response.status == 200:
                            result = await response.json()
                            yield {
                                'query': query,
                                'data': result.get('data', {}),
                                'errors': result.get('errors', [])
                            }
                        else:
                            logger.warning(f"GraphQL request failed: {response.status}")
                except Exception as e:
                    logger.error(f"Error executing GraphQL query: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        introspection_query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                    description
                    fields {
                        name
                        type {
                            name
                            kind
                        }
                    }
                }
            }
        }
        """
        
        params = self.config.connection_params
        headers = params.get('headers', {})
        
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.post(
                    params['endpoint'],
                    json={'query': introspection_query}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get('data', {}).get('__schema', {})
            except Exception as e:
                logger.error(f"Error fetching GraphQL schema: {e}")
        
        return {}

# File Sources
class CSVFileSource(BaseDataSource):
    """CSV file data source"""
    
    async def connect(self) -> bool:
        try:
            file_path = self.config.connection_params['file_path']
            self.is_connected = Path(file_path).exists()
            return self.is_connected
        except Exception as e:
            logger.error(f"Failed to connect to CSV file: {e}")
            return False
    
    async def disconnect(self):
        self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        file_path = self.config.connection_params['file_path']
        chunk_size = query_params.get('chunk_size', 10000)
        
        try:
            # Read CSV in chunks to handle large files
            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                for _, row in chunk.iterrows():
                    yield row.to_dict()
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        file_path = self.config.connection_params['file_path']
        
        try:
            # Read just the header to get column information
            df_sample = pd.read_csv(file_path, nrows=100)
            
            schema = {
                'columns': list(df_sample.columns),
                'dtypes': {col: str(dtype) for col, dtype in df_sample.dtypes.items()},
                'shape': df_sample.shape,
                'memory_usage': df_sample.memory_usage(deep=True).to_dict()
            }
            
            return schema
        except Exception as e:
            logger.error(f"Error getting CSV schema: {e}")
            return {}

class JSONFileSource(BaseDataSource):
    """JSON file data source"""
    
    async def connect(self) -> bool:
        try:
            file_path = self.config.connection_params['file_path']
            self.is_connected = Path(file_path).exists()
            return self.is_connected
        except Exception as e:
            logger.error(f"Failed to connect to JSON file: {e}")
            return False
    
    async def disconnect(self):
        self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        file_path = self.config.connection_params['file_path']
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
                if isinstance(data, list):
                    for item in data:
                        yield item
                elif isinstance(data, dict):
                    yield data
                else:
                    yield {'value': data}
        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        file_path = self.config.connection_params['file_path']
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
                def analyze_structure(obj, path="root"):
                    if isinstance(obj, dict):
                        return {f"{path}.{k}": analyze_structure(v, f"{path}.{k}") for k, v in obj.items()}
                    elif isinstance(obj, list):
                        if obj:
                            return {f"{path}[0]": analyze_structure(obj[0], f"{path}[0]")}
                        else:
                            return {f"{path}": "empty_list"}
                    else:
                        return type(obj).__name__
                
                return analyze_structure(data)
        except Exception as e:
            logger.error(f"Error analyzing JSON structure: {e}")
            return {}

# Stream Sources
class KafkaSource(BaseDataSource):
    """Kafka stream data source"""
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.consumer = None
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            consumer_config = {
                'bootstrap_servers': params['bootstrap_servers'],
                'group_id': params.get('group_id', 'etl-pipeline'),
                'auto_offset_reset': params.get('auto_offset_reset', 'earliest'),
                'value_deserializer': lambda x: json.loads(x.decode('utf-8'))
            }
            
            # Add authentication if provided
            if 'security_protocol' in params:
                consumer_config.update({
                    'security_protocol': params['security_protocol'],
                    'sasl_mechanism': params.get('sasl_mechanism'),
                    'sasl_plain_username': params.get('username'),
                    'sasl_plain_password': params.get('password')
                })
            
            self.consumer = KafkaConsumer(**consumer_config)
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            return False
    
    async def disconnect(self):
        if self.consumer:
            self.consumer.close()
            self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        topics = query_params.get('topics', [])
        timeout_ms = query_params.get('timeout_ms', 1000)
        
        if not topics:
            logger.warning("No topics specified for Kafka consumption")
            return
        
        self.consumer.subscribe(topics)
        
        try:
            while True:
                message_pack = self.consumer.poll(timeout_ms=timeout_ms)
                
                if not message_pack:
                    await asyncio.sleep(1)
                    continue
                
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        yield {
                            'topic': message.topic,
                            'partition': message.partition,
                            'offset': message.offset,
                            'timestamp': message.timestamp,
                            'key': message.key.decode('utf-8') if message.key else None,
                            'value': message.value
                        }
        except Exception as e:
            logger.error(f"Error consuming from Kafka: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        try:
            # Get cluster metadata
            cluster_metadata = self.consumer.list_consumer_groups()
            topics_metadata = self.consumer.topics()
            
            return {
                'cluster_metadata': str(cluster_metadata),
                'available_topics': list(topics_metadata),
                'consumer_group': self.consumer.config.get('group_id')
            }
        except Exception as e:
            logger.error(f"Error getting Kafka metadata: {e}")
            return {}

# Cloud Storage Sources
class S3Source(BaseDataSource):
    """AWS S3 data source"""
    
    def __init__(self, config: DataSourceConfig):
        super().__init__(config)
        self.s3_client = None
    
    async def connect(self) -> bool:
        try:
            params = self.config.connection_params
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=params['access_key_id'],
                aws_secret_access_key=params['secret_access_key'],
                region_name=params.get('region', 'us-east-1'),
                endpoint_url=params.get('endpoint_url')
            )
            
            # Test connection by listing buckets
            self.s3_client.list_buckets()
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            return False
    
    async def disconnect(self):
        self.is_connected = False
    
    async def extract_data(self, query_params: Dict[str, Any] = None) -> AsyncIterator[Dict[str, Any]]:
        bucket = query_params.get('bucket')
        prefix = query_params.get('prefix', '')
        
        if not bucket:
            logger.error("No bucket specified for S3 extraction")
            return
        
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Get object metadata and content
                        response = self.s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                        
                        yield {
                            'bucket': bucket,
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat(),
                            'etag': obj['ETag'],
                            'content_type': response.get('ContentType', 'unknown'),
                            'metadata': response.get('Metadata', {}),
                            'content': response['Body'].read()
                        }
        except Exception as e:
            logger.error(f"Error extracting from S3: {e}")
    
    async def get_schema(self) -> Dict[str, Any]:
        try:
            buckets = self.s3_client.list_buckets()
            
            schema = {
                'buckets': [],
                'total_buckets': len(buckets['Buckets'])
            }
            
            for bucket in buckets['Buckets']:
                bucket_info = {
                    'name': bucket['Name'],
                    'creation_date': bucket['CreationDate'].isoformat()
                }
                
                # Get bucket location and size info
                try:
                    location = self.s3_client.get_bucket_location(Bucket=bucket['Name'])
                    bucket_info['region'] = location.get('LocationConstraint', 'us-east-1')
                except:
                    bucket_info['region'] = 'unknown'
                
                schema['buckets'].append(bucket_info)
            
            return schema
        except Exception as e:
            logger.error(f"Error getting S3 schema: {e}")
            return {}

# Data Source Factory
class DataSourceFactory:
    """Factory for creating data sources"""
    
    _source_classes = {
        'postgresql': PostgreSQLSource,
        'mysql': MySQLSource,
        'mongodb': MongoDBSource,
        'redis': RedisSource,
        'elasticsearch': ElasticsearchSource,
        'rest_api': RESTAPISource,
        'graphql': GraphQLSource,
        'csv_file': CSVFileSource,
        'json_file': JSONFileSource,
        'kafka': KafkaSource,
        's3': S3Source
    }
    
    @classmethod
    def create_source(cls, config: DataSourceConfig) -> BaseDataSource:
        """Create a data source instance based on configuration"""
        source_type = config.connection_params.get('type', '').lower()
        
        if source_type not in cls._source_classes:
            raise ValueError(f"Unsupported data source type: {source_type}")
        
        source_class = cls._source_classes[source_type]
        return source_class(config)
    
    @classmethod
    def get_supported_sources(cls) -> List[str]:
        """Get list of supported data source types"""
        return list(cls._source_classes.keys())

# Predefined source configurations for 50+ sources
DATA_SOURCE_CONFIGURATIONS = [
    # Databases
    DataSourceConfig(
        source_id="postgres_main",
        source_type=DataSourceType.DATABASE,
        connection_params={
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "username": "postgres",
            "password": "postgres",
            "database": "activelog"
        },
        data_format=DataFormat.JSON,
        tags=["database", "primary"]
    ),
    
    DataSourceConfig(
        source_id="mysql_analytics",
        source_type=DataSourceType.DATABASE,
        connection_params={
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "username": "mysql",
            "password": "mysql",
            "database": "analytics"
        },
        data_format=DataFormat.JSON,
        tags=["database", "analytics"]
    ),
    
    DataSourceConfig(
        source_id="mongodb_logs",
        source_type=DataSourceType.NOSQL,
        connection_params={
            "type": "mongodb",
            "host": "localhost",
            "port": 27017,
            "username": "mongo",
            "password": "mongo",
            "database": "logs"
        },
        data_format=DataFormat.JSON,
        tags=["nosql", "logs"]
    ),
    
    DataSourceConfig(
        source_id="redis_cache",
        source_type=DataSourceType.NOSQL,
        connection_params={
            "type": "redis",
            "host": "localhost",
            "port": 6379,
            "password": "",
            "db": 0
        },
        data_format=DataFormat.JSON,
        tags=["cache", "redis"]
    ),
    
    DataSourceConfig(
        source_id="elasticsearch_search",
        source_type=DataSourceType.SEARCH_ENGINE,
        connection_params={
            "type": "elasticsearch",
            "host": "localhost",
            "port": 9200,
            "username": "elastic",
            "password": "elastic"
        },
        data_format=DataFormat.JSON,
        tags=["search", "elasticsearch"]
    ),
    
    # APIs
    DataSourceConfig(
        source_id="rest_api_users",
        source_type=DataSourceType.API,
        connection_params={
            "type": "rest_api",
            "base_url": "https://jsonplaceholder.typicode.com",
            "headers": {"Content-Type": "application/json"}
        },
        data_format=DataFormat.JSON,
        tags=["api", "users"]
    ),
    
    DataSourceConfig(
        source_id="github_api",
        source_type=DataSourceType.API,
        connection_params={
            "type": "rest_api",
            "base_url": "https://api.github.com",
            "headers": {"Authorization": "token YOUR_GITHUB_TOKEN"}
        },
        data_format=DataFormat.JSON,
        tags=["api", "github", "git"]
    ),
    
    DataSourceConfig(
        source_id="graphql_api",
        source_type=DataSourceType.API,
        connection_params={
            "type": "graphql",
            "endpoint": "https://api.spacex.land/graphql/",
            "headers": {"Content-Type": "application/json"}
        },
        data_format=DataFormat.JSON,
        tags=["api", "graphql"]
    ),
    
    # Streaming
    DataSourceConfig(
        source_id="kafka_events",
        source_type=DataSourceType.STREAM,
        connection_params={
            "type": "kafka",
            "bootstrap_servers": ["localhost:9092"],
            "group_id": "etl-pipeline",
            "auto_offset_reset": "earliest"
        },
        data_format=DataFormat.JSON,
        tags=["stream", "kafka", "events"]
    ),
    
    # Cloud Storage
    DataSourceConfig(
        source_id="s3_data_lake",
        source_type=DataSourceType.CLOUD_STORAGE,
        connection_params={
            "type": "s3",
            "access_key_id": "YOUR_ACCESS_KEY",
            "secret_access_key": "YOUR_SECRET_KEY",
            "region": "us-east-1"
        },
        data_format=DataFormat.PARQUET,
        tags=["cloud", "s3", "data-lake"]
    ),
    
    # Files
    DataSourceConfig(
        source_id="csv_sales_data",
        source_type=DataSourceType.FILE,
        connection_params={
            "type": "csv_file",
            "file_path": "/data/sales/sales.csv"
        },
        data_format=DataFormat.CSV,
        tags=["file", "csv", "sales"]
    ),
    
    DataSourceConfig(
        source_id="json_config_data",
        source_type=DataSourceType.FILE,
        connection_params={
            "type": "json_file",
            "file_path": "/data/config/app_config.json"
        },
        data_format=DataFormat.JSON,
        tags=["file", "json", "config"]
    ),
    
    # Add more configurations to reach 50+ sources...
    # This is a sample - in production, you would have all 50+ configured
]

def get_all_data_source_configs() -> List[DataSourceConfig]:
    """Get all predefined data source configurations"""
    return DATA_SOURCE_CONFIGURATIONS

def get_data_source_config(source_id: str) -> Optional[DataSourceConfig]:
    """Get specific data source configuration by ID"""
    for config in DATA_SOURCE_CONFIGURATIONS:
        if config.source_id == source_id:
            return config
    return None