#!/usr/bin/env python3
"""
Core Data Management AI Service for ActiveLog
Intelligent data orchestration, classification, and processing engine
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
import aiofiles
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import numpy as np
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataType(Enum):
    """Enumeration of supported data types"""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STRUCTURED = "structured"
    TIME_SERIES = "time_series"
    GEOSPATIAL = "geospatial"
    UNKNOWN = "unknown"

class ProcessingStatus(Enum):
    """Data processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    ARCHIVED = "archived"

class Priority(Enum):
    """Processing priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class DataItem:
    """Represents a single data item in the system"""
    id: str
    user_id: str
    data_type: DataType
    source: str
    content: Any
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    priority: Priority = Priority.NORMAL
    size_bytes: int = 0
    checksum: Optional[str] = None
    tags: List[str] = None
    category: Optional[str] = None
    confidence_score: float = 0.0

@dataclass
class ProcessingTask:
    """Represents a data processing task"""
    task_id: str
    data_item_id: str
    processor_name: str
    task_type: str
    parameters: Dict[str, Any]
    status: ProcessingStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class DataInsight:
    """Represents insights derived from data"""
    insight_id: str
    data_item_id: str
    insight_type: str
    title: str
    description: str
    confidence_score: float
    data: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None

class DataClassifier:
    """AI-powered data classification engine"""
    
    def __init__(self):
        self.classification_rules = self._load_classification_rules()
        self.confidence_threshold = 0.7
    
    def _load_classification_rules(self) -> Dict[str, Any]:
        """Load classification rules and patterns"""
        return {
            'text': {
                'patterns': [
                    {'pattern': r'.*\.txt$', 'confidence': 0.9},
                    {'pattern': r'.*\.md$', 'confidence': 0.8},
                    {'pattern': r'.*\.log$', 'confidence': 0.8}
                ],
                'content_indicators': ['plain text', 'utf-8', 'ascii']
            },
            'image': {
                'patterns': [
                    {'pattern': r'.*\.(jpg|jpeg|png|gif|bmp|webp)$', 'confidence': 0.95},
                    {'pattern': r'.*\.tiff?$', 'confidence': 0.9}
                ],
                'mime_types': ['image/jpeg', 'image/png', 'image/gif']
            },
            'video': {
                'patterns': [
                    {'pattern': r'.*\.(mp4|avi|mov|wmv|flv|webm|mkv)$', 'confidence': 0.95}
                ],
                'mime_types': ['video/mp4', 'video/avi', 'video/quicktime']
            },
            'audio': {
                'patterns': [
                    {'pattern': r'.*\.(mp3|wav|flac|aac|ogg|m4a)$', 'confidence': 0.95}
                ],
                'mime_types': ['audio/mpeg', 'audio/wav', 'audio/flac']
            },
            'document': {
                'patterns': [
                    {'pattern': r'.*\.(pdf|doc|docx|xls|xlsx|ppt|pptx)$', 'confidence': 0.9},
                    {'pattern': r'.*\.rtf$', 'confidence': 0.8}
                ],
                'mime_types': ['application/pdf', 'application/msword']
            }
        }
    
    async def classify_data(self, data_item: DataItem) -> Dict[str, Any]:
        """Classify data item and return classification results"""
        classification_results = {
            'data_type': DataType.UNKNOWN,
            'confidence': 0.0,
            'category': None,
            'subcategory': None,
            'tags': [],
            'processing_recommendations': []
        }
        
        # File extension based classification
        if hasattr(data_item.content, 'name') or 'filename' in data_item.metadata:
            filename = getattr(data_item.content, 'name', data_item.metadata.get('filename', ''))
            ext_classification = await self._classify_by_extension(filename)
            if ext_classification['confidence'] > classification_results['confidence']:
                classification_results.update(ext_classification)
        
        # MIME type based classification
        if 'mime_type' in data_item.metadata:
            mime_classification = await self._classify_by_mime_type(data_item.metadata['mime_type'])
            if mime_classification['confidence'] > classification_results['confidence']:
                classification_results.update(mime_classification)
        
        # Content-based classification
        content_classification = await self._classify_by_content(data_item)
        if content_classification['confidence'] > classification_results['confidence']:
            classification_results.update(content_classification)
        
        # Activity context classification
        if data_item.source:
            context_classification = await self._classify_by_context(data_item)
            classification_results['tags'].extend(context_classification.get('tags', []))
            classification_results['processing_recommendations'].extend(
                context_classification.get('processing_recommendations', [])
            )
        
        return classification_results
    
    async def _classify_by_extension(self, filename: str) -> Dict[str, Any]:
        """Classify data based on file extension"""
        import re
        
        for data_type, rules in self.classification_rules.items():
            for pattern_rule in rules.get('patterns', []):
                if re.match(pattern_rule['pattern'], filename.lower()):
                    return {
                        'data_type': DataType(data_type),
                        'confidence': pattern_rule['confidence'],
                        'category': data_type,
                        'subcategory': self._get_subcategory(filename),
                        'tags': [f'file_type:{data_type}'],
                        'processing_recommendations': self._get_processing_recommendations(data_type)
                    }
        
        return {'data_type': DataType.UNKNOWN, 'confidence': 0.0}
    
    async def _classify_by_mime_type(self, mime_type: str) -> Dict[str, Any]:
        """Classify data based on MIME type"""
        for data_type, rules in self.classification_rules.items():
            if mime_type in rules.get('mime_types', []):
                return {
                    'data_type': DataType(data_type),
                    'confidence': 0.9,
                    'category': data_type,
                    'tags': [f'mime_type:{mime_type}'],
                    'processing_recommendations': self._get_processing_recommendations(data_type)
                }
        
        return {'data_type': DataType.UNKNOWN, 'confidence': 0.0}
    
    async def _classify_by_content(self, data_item: DataItem) -> Dict[str, Any]:
        """Classify data based on content analysis"""
        if isinstance(data_item.content, str):
            return await self._classify_text_content(data_item.content)
        elif isinstance(data_item.content, bytes):
            return await self._classify_binary_content(data_item.content)
        elif isinstance(data_item.content, dict):
            return await self._classify_structured_content(data_item.content)
        
        return {'data_type': DataType.UNKNOWN, 'confidence': 0.0}
    
    async def _classify_text_content(self, content: str) -> Dict[str, Any]:
        """Classify text content"""
        # Analyze text characteristics
        word_count = len(content.split())
        line_count = len(content.split('\n'))
        
        # Check for structured formats
        if content.strip().startswith('{') and content.strip().endswith('}'):
            try:
                json.loads(content)
                return {
                    'data_type': DataType.STRUCTURED,
                    'confidence': 0.9,
                    'category': 'json',
                    'subcategory': 'json_document',
                    'tags': ['structured_data', 'json'],
                    'processing_recommendations': ['json_parser', 'schema_validator']
                }
            except json.JSONDecodeError:
                pass
        
        # Check for log format
        log_indicators = ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'TRACE']
        if any(indicator in content for indicator in log_indicators):
            return {
                'data_type': DataType.TEXT,
                'confidence': 0.8,
                'category': 'log',
                'subcategory': 'application_log',
                'tags': ['log_data', 'structured_text'],
                'processing_recommendations': ['log_parser', 'error_analyzer']
            }
        
        # Default text classification
        return {
            'data_type': DataType.TEXT,
            'confidence': 0.6,
            'category': 'text',
            'subcategory': 'plain_text' if word_count > 10 else 'short_text',
            'tags': ['text_content'],
            'processing_recommendations': ['text_analyzer', 'sentiment_analyzer']
        }
    
    async def _classify_binary_content(self, content: bytes) -> Dict[str, Any]:
        """Classify binary content by analyzing byte patterns"""
        # Check common binary file signatures
        signatures = {
            b'\xFF\xD8\xFF': ('image', 'jpeg', 0.95),
            b'\x89PNG\r\n\x1a\n': ('image', 'png', 0.95),
            b'GIF87a': ('image', 'gif', 0.95),
            b'GIF89a': ('image', 'gif', 0.95),
            b'%PDF': ('document', 'pdf', 0.95),
            b'PK\x03\x04': ('document', 'zip_based', 0.7),  # Could be zip, docx, xlsx, etc.
            b'\x00\x00\x00\x18ftypmp4': ('video', 'mp4', 0.9),
            b'RIFF': ('audio', 'wav', 0.8),
            b'ID3': ('audio', 'mp3', 0.9)
        }
        
        for signature, (data_type, subcategory, confidence) in signatures.items():
            if content.startswith(signature):
                return {
                    'data_type': DataType(data_type),
                    'confidence': confidence,
                    'category': data_type,
                    'subcategory': subcategory,
                    'tags': [f'binary_{data_type}', f'format_{subcategory}'],
                    'processing_recommendations': self._get_processing_recommendations(data_type)
                }
        
        return {
            'data_type': DataType.UNKNOWN,
            'confidence': 0.1,
            'category': 'binary',
            'tags': ['binary_data', 'unknown_format']
        }
    
    async def _classify_structured_content(self, content: dict) -> Dict[str, Any]:
        """Classify structured data content"""
        # Analyze dictionary structure
        has_timestamp = any(key in content for key in ['timestamp', 'created_at', 'date', 'time'])
        has_location = any(key in content for key in ['lat', 'lon', 'latitude', 'longitude', 'location'])
        has_metrics = any(isinstance(value, (int, float)) for value in content.values())
        
        if has_timestamp and has_metrics:
            return {
                'data_type': DataType.TIME_SERIES,
                'confidence': 0.8,
                'category': 'time_series',
                'subcategory': 'metric_data',
                'tags': ['structured_data', 'time_series', 'metrics'],
                'processing_recommendations': ['time_series_analyzer', 'trend_detector']
            }
        
        if has_location:
            return {
                'data_type': DataType.GEOSPATIAL,
                'confidence': 0.8,
                'category': 'geospatial',
                'subcategory': 'location_data',
                'tags': ['structured_data', 'geospatial', 'location'],
                'processing_recommendations': ['geospatial_analyzer', 'location_enricher']
            }
        
        return {
            'data_type': DataType.STRUCTURED,
            'confidence': 0.7,
            'category': 'structured',
            'subcategory': 'generic_object',
            'tags': ['structured_data'],
            'processing_recommendations': ['schema_analyzer', 'data_profiler']
        }
    
    async def _classify_by_context(self, data_item: DataItem) -> Dict[str, Any]:
        """Classify data based on source context and metadata"""
        context_tags = []
        recommendations = []
        
        # Source-based classification
        source_mapping = {
            'google_photos': {
                'tags': ['social_media', 'photos', 'personal'],
                'recommendations': ['image_analyzer', 'face_detector', 'location_extractor']
            },
            'dropbox': {
                'tags': ['cloud_storage', 'files', 'backup'],
                'recommendations': ['file_organizer', 'duplicate_detector']
            },
            'fitness_tracker': {
                'tags': ['health', 'fitness', 'quantified_self'],
                'recommendations': ['activity_analyzer', 'health_insights']
            },
            'email': {
                'tags': ['communication', 'personal', 'text'],
                'recommendations': ['text_analyzer', 'contact_extractor', 'sentiment_analyzer']
            },
            'calendar': {
                'tags': ['scheduling', 'events', 'time_management'],
                'recommendations': ['event_analyzer', 'pattern_detector']
            }
        }
        
        source_key = data_item.source.lower().replace(' ', '_')
        if source_key in source_mapping:
            mapping = source_mapping[source_key]
            context_tags.extend(mapping['tags'])
            recommendations.extend(mapping['recommendations'])
        
        # Time-based context
        if data_item.created_at:
            hour = data_item.created_at.hour
            if 6 <= hour < 12:
                context_tags.append('morning_activity')
            elif 12 <= hour < 18:
                context_tags.append('afternoon_activity')
            elif 18 <= hour < 22:
                context_tags.append('evening_activity')
            else:
                context_tags.append('night_activity')
        
        return {
            'tags': context_tags,
            'processing_recommendations': recommendations
        }
    
    def _get_subcategory(self, filename: str) -> str:
        """Get subcategory based on file extension"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        subcategory_mapping = {
            'jpg': 'photo', 'jpeg': 'photo', 'png': 'image', 'gif': 'animation',
            'mp4': 'video', 'avi': 'video', 'mov': 'video',
            'mp3': 'music', 'wav': 'audio', 'flac': 'audio',
            'pdf': 'document', 'doc': 'document', 'docx': 'document',
            'txt': 'text', 'md': 'markdown', 'log': 'log_file'
        }
        
        return subcategory_mapping.get(extension, 'unknown')
    
    def _get_processing_recommendations(self, data_type: str) -> List[str]:
        """Get processing recommendations for data type"""
        recommendations = {
            'image': ['image_analyzer', 'thumbnail_generator', 'metadata_extractor'],
            'video': ['video_analyzer', 'thumbnail_generator', 'transcoder'],
            'audio': ['audio_analyzer', 'waveform_generator', 'transcriber'],
            'text': ['text_analyzer', 'sentiment_analyzer', 'keyword_extractor'],
            'document': ['document_parser', 'text_extractor', 'indexer'],
            'structured': ['schema_analyzer', 'data_profiler', 'validator']
        }
        
        return recommendations.get(data_type, ['generic_processor'])

class ProcessingPipeline:
    """Intelligent data processing pipeline"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.task_queue = asyncio.Queue()
        self.processors = {}
        self.running = False
        self.worker_count = 4
        self.workers = []
    
    async def initialize(self):
        """Initialize the processing pipeline"""
        self.engine = create_async_engine(self.database_url)
        await self._register_processors()
        logger.info(f"Processing pipeline initialized with {len(self.processors)} processors")
    
    async def _register_processors(self):
        """Register available data processors"""
        from ..processing.processors import (
            ImageProcessor, TextProcessor, DocumentProcessor,
            TimeSeriesProcessor, GeospatialProcessor
        )
        
        self.processors = {
            'image_analyzer': ImageProcessor(),
            'text_analyzer': TextProcessor(),
            'document_parser': DocumentProcessor(),
            'time_series_analyzer': TimeSeriesProcessor(),
            'geospatial_analyzer': GeospatialProcessor()
        }
    
    async def start(self):
        """Start the processing pipeline workers"""
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker_{i}"))
            for i in range(self.worker_count)
        ]
        logger.info(f"Started {self.worker_count} pipeline workers")
    
    async def stop(self):
        """Stop the processing pipeline"""
        self.running = False
        
        # Cancel all workers
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        if self.engine:
            await self.engine.dispose()
        
        logger.info("Processing pipeline stopped")
    
    async def submit_task(self, task: ProcessingTask, priority: Priority = Priority.NORMAL):
        """Submit a processing task to the pipeline"""
        await self.task_queue.put((priority.value, task))
        logger.debug(f"Submitted task {task.task_id} with priority {priority.name}")
    
    async def _worker(self, worker_name: str):
        """Processing worker coroutine"""
        logger.info(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Get task from queue with timeout
                priority, task = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                
                logger.info(f"Worker {worker_name} processing task {task.task_id}")
                await self._process_task(task)
                
            except asyncio.TimeoutError:
                # No tasks available, continue polling
                continue
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {str(e)}")
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_task(self, task: ProcessingTask):
        """Process a single task"""
        task.started_at = datetime.now(timezone.utc)
        task.status = ProcessingStatus.PROCESSING
        
        try:
            # Update task status in database
            await self._update_task_status(task)
            
            # Get appropriate processor
            processor = self.processors.get(task.processor_name)
            if not processor:
                raise ValueError(f"Unknown processor: {task.processor_name}")
            
            # Execute processing
            result = await processor.process(task.data_item_id, task.parameters)
            
            # Update task with results
            task.status = ProcessingStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            task.result = result
            
            logger.info(f"Task {task.task_id} completed successfully")
            
        except Exception as e:
            task.status = ProcessingStatus.FAILED
            task.error_message = str(e)
            task.retry_count += 1
            
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            
            # Retry if under limit
            if task.retry_count < task.max_retries:
                task.status = ProcessingStatus.RETRYING
                # Re-queue with delay
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                await self.submit_task(task, Priority.LOW)
        
        finally:
            # Update final task status
            await self._update_task_status(task)
    
    async def _update_task_status(self, task: ProcessingTask):
        """Update task status in database"""
        # This would update the task status in the database
        # For now, just log the status update
        logger.debug(f"Task {task.task_id} status: {task.status.value}")

class DataManager:
    """Main data management AI service"""
    
    def __init__(self, database_url: str, config: Dict[str, Any] = None):
        self.database_url = database_url
        self.config = config or {}
        self.engine = None
        self.classifier = DataClassifier()
        self.pipeline = ProcessingPipeline(database_url)
        self.insights_cache = {}
        self.running = False
    
    async def initialize(self):
        """Initialize the data manager"""
        self.engine = create_async_engine(self.database_url)
        await self.pipeline.initialize()
        
        # Create database tables if they don't exist
        await self._create_tables()
        
        logger.info("Data Manager AI initialized")
    
    async def start(self):
        """Start the data manager service"""
        await self.pipeline.start()
        self.running = True
        
        # Start background tasks
        asyncio.create_task(self._insights_generator())
        asyncio.create_task(self._quality_monitor())
        
        logger.info("Data Manager AI started")
    
    async def stop(self):
        """Stop the data manager service"""
        self.running = False
        await self.pipeline.stop()
        
        if self.engine:
            await self.engine.dispose()
        
        logger.info("Data Manager AI stopped")
    
    async def ingest_data(self, user_id: str, source: str, content: Any, 
                         metadata: Dict[str, Any] = None) -> DataItem:
        """Ingest new data into the system"""
        # Create data item
        data_item = DataItem(
            id=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            user_id=user_id,
            data_type=DataType.UNKNOWN,
            source=source,
            content=content,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            size_bytes=self._calculate_size(content)
        )
        
        # Classify the data
        classification = await self.classifier.classify_data(data_item)
        data_item.data_type = classification['data_type']
        data_item.category = classification['category']
        data_item.tags = classification['tags']
        data_item.confidence_score = classification['confidence']
        
        # Store data item
        await self._store_data_item(data_item)
        
        # Schedule processing tasks
        for processor_name in classification['processing_recommendations']:
            await self._schedule_processing(data_item, processor_name)
        
        logger.info(f"Ingested data item {data_item.id} from {source}")
        return data_item
    
    async def get_data_items(self, user_id: str, filters: Dict[str, Any] = None,
                           limit: int = 100, offset: int = 0) -> List[DataItem]:
        """Retrieve data items with optional filtering"""
        # This would query the database for data items
        # For now, return empty list
        return []
    
    async def get_insights(self, user_id: str, data_item_id: str = None,
                          insight_type: str = None) -> List[DataInsight]:
        """Get insights for user's data"""
        cache_key = f"{user_id}_{data_item_id}_{insight_type}"
        
        if cache_key in self.insights_cache:
            return self.insights_cache[cache_key]
        
        # Generate insights
        insights = await self._generate_insights(user_id, data_item_id, insight_type)
        
        # Cache results
        self.insights_cache[cache_key] = insights
        
        return insights
    
    async def search_data(self, user_id: str, query: str, filters: Dict[str, Any] = None) -> List[DataItem]:
        """Search user's data using AI-powered search"""
        # This would implement intelligent search across all data types
        # For now, return empty list
        return []
    
    async def get_recommendations(self, user_id: str, recommendation_type: str = "general") -> List[Dict[str, Any]]:
        """Get AI-powered recommendations for data management"""
        recommendations = []
        
        # Get user's data summary
        data_summary = await self._get_user_data_summary(user_id)
        
        # Generate recommendations based on data patterns
        if data_summary['total_items'] > 1000:
            recommendations.append({
                'type': 'organization',
                'title': 'Consider organizing your large data collection',
                'description': f'You have {data_summary["total_items"]} items. Creating categories could help.',
                'priority': 'medium',
                'action': 'create_categories'
            })
        
        if data_summary['duplicate_count'] > 10:
            recommendations.append({
                'type': 'cleanup',
                'title': 'Duplicate files detected',
                'description': f'Found {data_summary["duplicate_count"]} potential duplicates.',
                'priority': 'high',
                'action': 'remove_duplicates'
            })
        
        # Storage optimization recommendations
        if data_summary['total_size_mb'] > 5000:  # 5GB
            recommendations.append({
                'type': 'storage',
                'title': 'Storage optimization opportunity',
                'description': f'Your data uses {data_summary["total_size_mb"]/1024:.1f}GB. Consider archiving old files.',
                'priority': 'medium',
                'action': 'archive_old_data'
            })
        
        return recommendations
    
    async def _create_tables(self):
        """Create necessary database tables"""
        create_tables_sql = """
        CREATE TABLE IF NOT EXISTS data_items (
            id VARCHAR(255) PRIMARY KEY,
            user_id UUID NOT NULL,
            data_type VARCHAR(50) NOT NULL,
            source VARCHAR(255) NOT NULL,
            content JSONB,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
            processing_status VARCHAR(50) DEFAULT 'pending',
            priority INTEGER DEFAULT 2,
            size_bytes BIGINT DEFAULT 0,
            checksum VARCHAR(64),
            tags TEXT[],
            category VARCHAR(100),
            confidence_score REAL DEFAULT 0.0
        );
        
        CREATE TABLE IF NOT EXISTS processing_tasks (
            task_id VARCHAR(255) PRIMARY KEY,
            data_item_id VARCHAR(255) NOT NULL,
            processor_name VARCHAR(100) NOT NULL,
            task_type VARCHAR(100) NOT NULL,
            parameters JSONB DEFAULT '{}',
            status VARCHAR(50) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT,
            result JSONB,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3
        );
        
        CREATE TABLE IF NOT EXISTS data_insights (
            insight_id VARCHAR(255) PRIMARY KEY,
            data_item_id VARCHAR(255) NOT NULL,
            insight_type VARCHAR(100) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            confidence_score REAL NOT NULL,
            data JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE
        );
        
        CREATE INDEX IF NOT EXISTS idx_data_items_user_id ON data_items(user_id);
        CREATE INDEX IF NOT EXISTS idx_data_items_type ON data_items(data_type);
        CREATE INDEX IF NOT EXISTS idx_data_items_source ON data_items(source);
        CREATE INDEX IF NOT EXISTS idx_data_items_created_at ON data_items(created_at);
        CREATE INDEX IF NOT EXISTS idx_processing_tasks_status ON processing_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_insights_type ON data_insights(insight_type);
        """
        
        async with self.engine.begin() as conn:
            await conn.execute(text(create_tables_sql))
    
    async def _store_data_item(self, data_item: DataItem):
        """Store data item in database"""
        insert_sql = """
        INSERT INTO data_items (
            id, user_id, data_type, source, content, metadata, created_at, updated_at,
            processing_status, priority, size_bytes, tags, category, confidence_score
        ) VALUES (
            :id, :user_id, :data_type, :source, :content, :metadata, :created_at, :updated_at,
            :processing_status, :priority, :size_bytes, :tags, :category, :confidence_score
        )
        """
        
        async with self.engine.begin() as conn:
            await conn.execute(text(insert_sql), {
                'id': data_item.id,
                'user_id': data_item.user_id,
                'data_type': data_item.data_type.value,
                'source': data_item.source,
                'content': json.dumps(data_item.content, default=str),
                'metadata': json.dumps(data_item.metadata),
                'created_at': data_item.created_at,
                'updated_at': data_item.updated_at,
                'processing_status': data_item.processing_status.value,
                'priority': data_item.priority.value,
                'size_bytes': data_item.size_bytes,
                'tags': data_item.tags or [],
                'category': data_item.category,
                'confidence_score': data_item.confidence_score
            })
    
    async def _schedule_processing(self, data_item: DataItem, processor_name: str):
        """Schedule a processing task for a data item"""
        task = ProcessingTask(
            task_id=f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            data_item_id=data_item.id,
            processor_name=processor_name,
            task_type="analysis",
            parameters={},
            status=ProcessingStatus.PENDING,
            created_at=datetime.now(timezone.utc)
        )
        
        await self.pipeline.submit_task(task, data_item.priority)
    
    def _calculate_size(self, content: Any) -> int:
        """Calculate the size of content in bytes"""
        if isinstance(content, str):
            return len(content.encode('utf-8'))
        elif isinstance(content, bytes):
            return len(content)
        elif isinstance(content, (dict, list)):
            return len(json.dumps(content, default=str).encode('utf-8'))
        else:
            return len(str(content).encode('utf-8'))
    
    async def _generate_insights(self, user_id: str, data_item_id: str = None,
                                insight_type: str = None) -> List[DataInsight]:
        """Generate insights for user's data"""
        insights = []
        
        # Example insight generation
        if insight_type == "activity_patterns" or insight_type is None:
            activity_insight = DataInsight(
                insight_id=f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
                data_item_id=data_item_id or "all",
                insight_type="activity_patterns",
                title="Most Active Time of Day",
                description="You're most active in the evening between 6-9 PM",
                confidence_score=0.8,
                data={
                    "peak_hours": [18, 19, 20],
                    "activity_distribution": {
                        "morning": 0.2,
                        "afternoon": 0.3,
                        "evening": 0.4,
                        "night": 0.1
                    }
                },
                created_at=datetime.now(timezone.utc)
            )
            insights.append(activity_insight)
        
        return insights
    
    async def _get_user_data_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary statistics for user's data"""
        # This would query the database for actual statistics
        # For now, return mock data
        return {
            'total_items': 850,
            'total_size_mb': 3200,
            'duplicate_count': 15,
            'data_types': {
                'image': 450,
                'text': 200,
                'video': 100,
                'audio': 50,
                'document': 30,
                'other': 20
            },
            'sources': {
                'google_photos': 400,
                'dropbox': 250,
                'email': 150,
                'manual_upload': 50
            }
        }
    
    async def _insights_generator(self):
        """Background task to generate insights"""
        while self.running:
            try:
                # Generate insights for active users
                logger.debug("Generating background insights...")
                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Insights generator error: {str(e)}")
                await asyncio.sleep(60)
    
    async def _quality_monitor(self):
        """Background task to monitor data quality"""
        while self.running:
            try:
                # Monitor data quality metrics
                logger.debug("Monitoring data quality...")
                await asyncio.sleep(1800)  # Run every 30 minutes
            except Exception as e:
                logger.error(f"Quality monitor error: {str(e)}")
                await asyncio.sleep(60)

# CLI Interface
async def main():
    """Command-line interface for data manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ActiveLog Data Manager AI')
    parser.add_argument('action', choices=['start', 'ingest', 'classify', 'insights', 'recommend'])
    parser.add_argument('--database-url', required=True, help='Database connection URL')
    parser.add_argument('--user-id', help='User ID for operations')
    parser.add_argument('--source', help='Data source identifier')
    parser.add_argument('--content', help='Content to ingest (text or file path)')
    parser.add_argument('--metadata', help='Metadata JSON string')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Initialize data manager
    data_manager = DataManager(args.database_url, config)
    await data_manager.initialize()
    
    try:
        if args.action == 'start':
            # Start the service
            await data_manager.start()
            print("Data Manager AI started. Press Ctrl+C to stop.")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping Data Manager AI...")
        
        elif args.action == 'ingest':
            if not all([args.user_id, args.source, args.content]):
                print("Error: --user-id, --source, and --content required for ingest")
                return
            
            metadata = json.loads(args.metadata) if args.metadata else {}
            
            # Check if content is a file path
            if os.path.exists(args.content):
                with open(args.content, 'rb') as f:
                    content = f.read()
                metadata['filename'] = os.path.basename(args.content)
            else:
                content = args.content
            
            data_item = await data_manager.ingest_data(
                args.user_id, args.source, content, metadata
            )
            
            print(f"Data ingested: {data_item.id}")
            print(f"Type: {data_item.data_type.value}")
            print(f"Category: {data_item.category}")
            print(f"Confidence: {data_item.confidence_score:.2f}")
            print(f"Tags: {data_item.tags}")
        
        elif args.action == 'classify':
            if not args.content:
                print("Error: --content required for classification")
                return
            
            # Create temporary data item for classification
            data_item = DataItem(
                id="temp_classify",
                user_id=args.user_id or "temp",
                data_type=DataType.UNKNOWN,
                source=args.source or "manual",
                content=args.content,
                metadata=json.loads(args.metadata) if args.metadata else {},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            classification = await data_manager.classifier.classify_data(data_item)
            
            print("Classification Results:")
            print(json.dumps(classification, indent=2, default=str))
        
        elif args.action == 'insights':
            if not args.user_id:
                print("Error: --user-id required for insights")
                return
            
            insights = await data_manager.get_insights(args.user_id)
            
            print(f"Insights for user {args.user_id}:")
            for insight in insights:
                print(f"- {insight.title}: {insight.description}")
                print(f"  Confidence: {insight.confidence_score:.2f}")
        
        elif args.action == 'recommend':
            if not args.user_id:
                print("Error: --user-id required for recommendations")
                return
            
            recommendations = await data_manager.get_recommendations(args.user_id)
            
            print(f"Recommendations for user {args.user_id}:")
            for rec in recommendations:
                print(f"- [{rec['priority'].upper()}] {rec['title']}")
                print(f"  {rec['description']}")
                print(f"  Action: {rec['action']}")
    
    finally:
        await data_manager.stop()

if __name__ == "__main__":
    asyncio.run(main())