"""
Whisper Plugin for ActiveLog AI Orchestrator
Provides audio transcription, metadata extraction, and searchable transcript storage
"""
import os
import json
import asyncio
import logging
import hashlib
import tempfile
from typing import Dict, List, Any, Optional, Union, BinaryIO
from datetime import datetime, timedelta
import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
import aiofiles
import mutagen
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from mutagen.flac import FLAC
import openai

# Configure logging
logger = logging.getLogger(__name__)

class WhisperPlugin:
    """Whisper plugin for audio transcription and analysis"""
    
    def __init__(self):
        self.name = "whisper"
        self.version = "1.0.0"
        
        # OpenAI configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.whisper_model = os.getenv("WHISPER_MODEL", "whisper-1")
        self.openai_timeout = int(os.getenv("OPENAI_TIMEOUT", "60"))
        
        # Audio processing configuration
        self.supported_formats = [
            'mp3', 'mp4', 'm4a', 'wav', 'flac', 'ogg', 'webm'
        ]
        self.max_file_size = int(os.getenv("WHISPER_MAX_FILE_SIZE", "25000000"))  # 25MB default
        
        # Transcription options
        self.default_language = os.getenv("WHISPER_DEFAULT_LANGUAGE", "auto")
        self.response_format = os.getenv("WHISPER_RESPONSE_FORMAT", "verbose_json")
        self.timestamp_granularities = ["word", "segment"]
        
        # Elasticsearch configuration
        self.es_host = os.getenv("ELASTICSEARCH_HOST", "localhost")
        self.es_port = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
        self.es_index = os.getenv("WHISPER_ES_INDEX", "audio_transcripts")
        self.es_username = os.getenv("ELASTICSEARCH_USERNAME")
        self.es_password = os.getenv("ELASTICSEARCH_PASSWORD")
        
        # Caching configuration
        self.enable_caching = os.getenv("WHISPER_ENABLE_CACHING", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("WHISPER_CACHE_TTL", "86400"))  # 24 hours
        
        # Rate limiting
        self.rate_limit_rpm = int(os.getenv("WHISPER_RATE_LIMIT_RPM", "50"))
        self.rate_limit_per_minute = {}
        
        # Internal state
        self.redis_client = None
        self.es_client = None
        self.openai_client = None
        
        self.stats = {
            "transcriptions_processed": 0,
            "audio_files_analyzed": 0,
            "transcripts_stored": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0,
            "total_audio_duration": 0.0,
            "total_file_size": 0
        }
    
    async def initialize(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the Whisper plugin"""
        self.redis_client = redis_client
        
        # Initialize OpenAI client
        if self.openai_api_key:
            self.openai_client = openai.AsyncOpenAI(
                api_key=self.openai_api_key,
                timeout=self.openai_timeout
            )
            logger.info("OpenAI Whisper client initialized")
        else:
            logger.warning("OpenAI API key not provided. Whisper plugin will not function.")
        
        # Initialize Elasticsearch client
        await self._init_elasticsearch()
        
        # Create ES index if it doesn't exist
        if self.es_client:
            await self._ensure_index_exists()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.es_client:
            await self.es_client.close()
    
    async def _init_elasticsearch(self):
        """Initialize Elasticsearch client"""
        try:
            es_config = {
                "hosts": [f"http://{self.es_host}:{self.es_port}"],
                "timeout": 30,
                "max_retries": 3,
                "retry_on_timeout": True
            }
            
            # Add authentication if provided
            if self.es_username and self.es_password:
                es_config["http_auth"] = (self.es_username, self.es_password)
            
            self.es_client = AsyncElasticsearch(**es_config)
            
            # Test connection
            await self.es_client.ping()
            logger.info("Elasticsearch client initialized successfully")
            
        except Exception as e:
            logger.warning(f"Elasticsearch initialization failed: {e}")
            self.es_client = None
    
    async def _ensure_index_exists(self):
        """Create Elasticsearch index for transcripts if it doesn't exist"""
        if not self.es_client:
            return
        
        try:
            index_exists = await self.es_client.indices.exists(index=self.es_index)
            
            if not index_exists:
                # Define index mapping for transcripts
                mapping = {
                    "mappings": {
                        "properties": {
                            "file_name": {"type": "keyword"},
                            "file_hash": {"type": "keyword"},
                            "file_size": {"type": "long"},
                            "duration": {"type": "float"},
                            "format": {"type": "keyword"},
                            "language": {"type": "keyword"},
                            "transcript_text": {
                                "type": "text",
                                "analyzer": "standard",
                                "search_analyzer": "standard"
                            },
                            "segments": {
                                "type": "nested",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "start": {"type": "float"},
                                    "end": {"type": "float"},
                                    "text": {"type": "text"},
                                    "no_speech_prob": {"type": "float"},
                                    "avg_logprob": {"type": "float"},
                                    "compression_ratio": {"type": "float"},
                                    "words": {
                                        "type": "nested",
                                        "properties": {
                                            "word": {"type": "text"},
                                            "start": {"type": "float"},
                                            "end": {"type": "float"},
                                            "probability": {"type": "float"}
                                        }
                                    }
                                }
                            },
                            "metadata": {
                                "properties": {
                                    "title": {"type": "text"},
                                    "artist": {"type": "keyword"},
                                    "album": {"type": "keyword"},
                                    "date": {"type": "keyword"},
                                    "genre": {"type": "keyword"},
                                    "bitrate": {"type": "integer"},
                                    "sample_rate": {"type": "integer"},
                                    "channels": {"type": "integer"}
                                }
                            },
                            "created_at": {"type": "date"},
                            "updated_at": {"type": "date"}
                        }
                    },
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "analysis": {
                            "analyzer": {
                                "transcript_analyzer": {
                                    "type": "standard",
                                    "stopwords": "_english_"
                                }
                            }
                        }
                    }
                }
                
                await self.es_client.indices.create(
                    index=self.es_index,
                    body=mapping
                )
                logger.info(f"Created Elasticsearch index: {self.es_index}")
                
        except Exception as e:
            logger.error(f"Failed to create Elasticsearch index: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Whisper plugin is healthy"""
        health_status = {
            "status": "healthy" if self.openai_api_key else "unhealthy",
            "openai_configured": bool(self.openai_api_key),
            "elasticsearch_connected": False,
            "supported_formats": self.supported_formats,
            "max_file_size_mb": self.max_file_size / 1024 / 1024
        }
        
        # Check Elasticsearch connection
        if self.es_client:
            try:
                await self.es_client.ping()
                health_status["elasticsearch_connected"] = True
            except Exception as e:
                health_status["elasticsearch_error"] = str(e)
        
        # Overall status
        if not health_status["openai_configured"]:
            health_status["status"] = "unhealthy"
            health_status["error"] = "OpenAI API key not configured"
        
        return health_status
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": [
                "audio_transcription",
                "metadata_extraction",
                "elasticsearch_storage",
                "multiple_formats",
                "timestamp_alignment",
                "searchable_transcripts"
            ],
            "stats": self.stats.copy(),
            "config": {
                "whisper_model": self.whisper_model,
                "supported_formats": self.supported_formats,
                "max_file_size_mb": self.max_file_size / 1024 / 1024,
                "elasticsearch_index": self.es_index,
                "caching_enabled": self.enable_caching,
                "default_language": self.default_language
            }
        }
    
    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operations"""
        key_data = f"{operation}:{json.dumps(kwargs, sort_keys=True)}"
        return f"whisper:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available"""
        if not self.enable_caching or not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                self.stats["cache_hits"] += 1
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        
        self.stats["cache_misses"] += 1
        return None
    
    async def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache response"""
        if not self.enable_caching or not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(response, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    async def _check_rate_limit(self, identifier: str = "global") -> bool:
        """Check rate limiting"""
        current_time = datetime.utcnow()
        minute_key = current_time.strftime("%Y-%m-%d-%H-%M")
        
        if identifier not in self.rate_limit_per_minute:
            self.rate_limit_per_minute[identifier] = {}
        
        # Clean old entries
        for key in list(self.rate_limit_per_minute[identifier].keys()):
            if key != minute_key:
                del self.rate_limit_per_minute[identifier][key]
        
        current_count = self.rate_limit_per_minute[identifier].get(minute_key, 0)
        if current_count >= self.rate_limit_rpm:
            return False
        
        self.rate_limit_per_minute[identifier][minute_key] = current_count + 1
        return True
    
    def _extract_audio_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from audio file"""
        try:
            audio_file = mutagen.File(file_path)
            
            if audio_file is None:
                return {}
            
            metadata = {
                "duration": getattr(audio_file.info, 'length', 0),
                "bitrate": getattr(audio_file.info, 'bitrate', 0),
                "sample_rate": getattr(audio_file.info, 'sample_rate', 0),
                "channels": getattr(audio_file.info, 'channels', 0)
            }
            
            # Extract common tags
            if audio_file.tags:
                tag_mapping = {
                    'TIT2': 'title',  # MP3
                    'TPE1': 'artist',  # MP3
                    'TALB': 'album',   # MP3
                    'TDRC': 'date',    # MP3
                    'TCON': 'genre',   # MP3
                    '©nam': 'title',   # MP4
                    '©ART': 'artist',  # MP4
                    '©alb': 'album',   # MP4
                    '©day': 'date',    # MP4
                    '©gen': 'genre',   # MP4
                    'TITLE': 'title', # FLAC/OGG
                    'ARTIST': 'artist', # FLAC/OGG
                    'ALBUM': 'album',   # FLAC/OGG
                    'DATE': 'date',     # FLAC/OGG
                    'GENRE': 'genre'    # FLAC/OGG
                }
                
                for tag_key, meta_key in tag_mapping.items():
                    if tag_key in audio_file.tags:
                        value = audio_file.tags[tag_key]
                        if isinstance(value, list) and value:
                            metadata[meta_key] = str(value[0])
                        elif value:
                            metadata[meta_key] = str(value)
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {}
    
    def _validate_audio_file(self, file_path: str, file_size: int) -> Dict[str, Any]:
        """Validate audio file format and size"""
        # Check file size
        if file_size > self.max_file_size:
            raise ValueError(f"File size {file_size} exceeds maximum {self.max_file_size} bytes")
        
        # Check file extension
        file_extension = os.path.splitext(file_path)[1][1:].lower()
        if file_extension not in self.supported_formats:
            raise ValueError(f"Unsupported format: {file_extension}")
        
        # Try to read audio file
        try:
            audio_file = mutagen.File(file_path)
            if audio_file is None:
                raise ValueError("Invalid or corrupted audio file")
            
            duration = getattr(audio_file.info, 'length', 0)
            return {
                "format": file_extension,
                "duration": duration,
                "valid": True
            }
            
        except Exception as e:
            raise ValueError(f"Audio file validation failed: {e}")
    
    async def transcribe_audio(
        self,
        audio_file: Union[str, BinaryIO],
        file_name: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        response_format: Optional[str] = None,
        timestamp_granularities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Transcribe audio file using OpenAI Whisper"""
        
        if not self.openai_client:
            raise Exception("OpenAI client not configured")
        
        if not await self._check_rate_limit("transcribe"):
            raise Exception("Rate limit exceeded for transcription")
        
        temp_file_path = None
        file_hash = None
        file_size = 0
        
        try:
            # Handle file input
            if isinstance(audio_file, str):
                # File path provided
                temp_file_path = audio_file
                file_size = os.path.getsize(audio_file)
                
                # Calculate file hash for caching
                with open(audio_file, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
            else:
                # File-like object provided
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                    temp_file_path = temp_file.name
                    
                    # Read and write file data
                    file_data = audio_file.read()
                    temp_file.write(file_data)
                    file_size = len(file_data)
                    
                    # Calculate file hash
                    file_hash = hashlib.sha256(file_data).hexdigest()
            
            if not file_name:
                file_name = os.path.basename(temp_file_path)
            
            # Validate audio file
            validation_info = self._validate_audio_file(temp_file_path, file_size)
            
            # Check cache
            cache_params = {
                "file_hash": file_hash,
                "language": language or self.default_language,
                "response_format": response_format or self.response_format
            }
            cache_key = self._generate_cache_key("transcribe", **cache_params)
            cached_response = await self._get_cached_response(cache_key)
            
            if cached_response:
                return cached_response
            
            # Extract metadata
            metadata = self._extract_audio_metadata(temp_file_path)
            
            # Prepare transcription parameters
            transcribe_params = {
                "model": self.whisper_model,
                "response_format": response_format or self.response_format,
            }
            
            if language and language != "auto":
                transcribe_params["language"] = language
            
            if prompt:
                transcribe_params["prompt"] = prompt
            
            if timestamp_granularities:
                transcribe_params["timestamp_granularities"] = timestamp_granularities
            
            # Perform transcription
            with open(temp_file_path, 'rb') as audio_file_obj:
                transcription = await self.openai_client.audio.transcriptions.create(
                    file=audio_file_obj,
                    **transcribe_params
                )
            
            # Process transcription result
            result = {
                "file_name": file_name,
                "file_hash": file_hash,
                "file_size": file_size,
                "format": validation_info["format"],
                "duration": validation_info["duration"],
                "language": getattr(transcription, 'language', language or 'unknown'),
                "text": transcription.text,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Add detailed segments if available
            if hasattr(transcription, 'segments') and transcription.segments:
                result["segments"] = []
                for segment in transcription.segments:
                    segment_data = {
                        "id": segment.get('id'),
                        "start": segment.get('start'),
                        "end": segment.get('end'),
                        "text": segment.get('text'),
                        "no_speech_prob": segment.get('no_speech_prob'),
                        "avg_logprob": segment.get('avg_logprob'),
                        "compression_ratio": segment.get('compression_ratio')
                    }
                    
                    # Add word-level timestamps if available
                    if 'words' in segment:
                        segment_data["words"] = [
                            {
                                "word": word.get('word'),
                                "start": word.get('start'),
                                "end": word.get('end'),
                                "probability": word.get('probability')
                            }
                            for word in segment['words']
                        ]
                    
                    result["segments"].append(segment_data)
            
            # Store in Elasticsearch
            if self.es_client:
                await self._store_transcript(result)
            
            # Cache the result
            await self._cache_response(cache_key, result)
            
            # Update statistics
            self.stats["transcriptions_processed"] += 1
            self.stats["audio_files_analyzed"] += 1
            self.stats["total_audio_duration"] += validation_info["duration"]
            self.stats["total_file_size"] += file_size
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            self.stats["errors"] += 1
            raise Exception(f"Audio transcription failed: {e}")
            
        finally:
            # Clean up temporary file if we created it
            if temp_file_path and isinstance(audio_file, (BinaryIO, io.IOBase)):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass
    
    async def _store_transcript(self, transcript_data: Dict[str, Any]):
        """Store transcript in Elasticsearch"""
        try:
            # Prepare document for indexing
            doc = {
                "file_name": transcript_data["file_name"],
                "file_hash": transcript_data["file_hash"],
                "file_size": transcript_data["file_size"],
                "duration": transcript_data["duration"],
                "format": transcript_data["format"],
                "language": transcript_data["language"],
                "transcript_text": transcript_data["text"],
                "metadata": transcript_data["metadata"],
                "created_at": transcript_data["created_at"],
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Add segments if available
            if "segments" in transcript_data:
                doc["segments"] = transcript_data["segments"]
            
            # Index the document
            await self.es_client.index(
                index=self.es_index,
                id=transcript_data["file_hash"],
                body=doc
            )
            
            self.stats["transcripts_stored"] += 1
            logger.info(f"Stored transcript for {transcript_data['file_name']} in Elasticsearch")
            
        except Exception as e:
            logger.error(f"Failed to store transcript in Elasticsearch: {e}")
    
    async def search_transcripts(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search transcripts in Elasticsearch"""
        
        if not self.es_client:
            raise Exception("Elasticsearch not configured")
        
        try:
            # Build search query
            search_body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": [
                                        "transcript_text^2",
                                        "segments.text",
                                        "file_name",
                                        "metadata.title",
                                        "metadata.artist"
                                    ],
                                    "type": "best_fields"
                                }
                            }
                        ]
                    }
                },
                "highlight": {
                    "fields": {
                        "transcript_text": {},
                        "segments.text": {}
                    }
                },
                "from": offset,
                "size": limit,
                "sort": [
                    {"_score": {"order": "desc"}},
                    {"created_at": {"order": "desc"}}
                ]
            }
            
            # Add filters if provided
            if filters:
                filter_clauses = []
                
                if "language" in filters:
                    filter_clauses.append({"term": {"language": filters["language"]}})
                
                if "format" in filters:
                    filter_clauses.append({"term": {"format": filters["format"]}})
                
                if "duration_min" in filters:
                    filter_clauses.append({"range": {"duration": {"gte": filters["duration_min"]}}})
                
                if "duration_max" in filters:
                    filter_clauses.append({"range": {"duration": {"lte": filters["duration_max"]}}})
                
                if "date_from" in filters:
                    filter_clauses.append({"range": {"created_at": {"gte": filters["date_from"]}}})
                
                if "date_to" in filters:
                    filter_clauses.append({"range": {"created_at": {"lte": filters["date_to"]}}})
                
                if filter_clauses:
                    search_body["query"]["bool"]["filter"] = filter_clauses
            
            # Execute search
            response = await self.es_client.search(
                index=self.es_index,
                body=search_body
            )
            
            # Process results
            results = []
            for hit in response['hits']['hits']:
                result = {
                    "id": hit['_id'],
                    "score": hit['_score'],
                    "file_name": hit['_source']['file_name'],
                    "duration": hit['_source']['duration'],
                    "language": hit['_source']['language'],
                    "format": hit['_source']['format'],
                    "transcript_text": hit['_source']['transcript_text'][:500],  # Truncate for preview
                    "metadata": hit['_source'].get('metadata', {}),
                    "created_at": hit['_source']['created_at']
                }
                
                # Add highlights if available
                if 'highlight' in hit:
                    result["highlights"] = hit['highlight']
                
                results.append(result)
            
            return {
                "query": query,
                "total": response['hits']['total']['value'],
                "results": results,
                "limit": limit,
                "offset": offset,
                "search_time_ms": response['took']
            }
            
        except Exception as e:
            logger.error(f"Transcript search failed: {e}")
            raise Exception(f"Search failed: {e}")
    
    async def get_transcript(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get specific transcript by file hash"""
        
        if not self.es_client:
            raise Exception("Elasticsearch not configured")
        
        try:
            response = await self.es_client.get(
                index=self.es_index,
                id=file_hash
            )
            
            return response['_source']
            
        except Exception as e:
            if "not_found" in str(e).lower():
                return None
            logger.error(f"Failed to get transcript: {e}")
            raise Exception(f"Failed to get transcript: {e}")
    
    async def delete_transcript(self, file_hash: str) -> bool:
        """Delete transcript from Elasticsearch"""
        
        if not self.es_client:
            raise Exception("Elasticsearch not configured")
        
        try:
            await self.es_client.delete(
                index=self.es_index,
                id=file_hash
            )
            
            return True
            
        except Exception as e:
            if "not_found" in str(e).lower():
                return False
            logger.error(f"Failed to delete transcript: {e}")
            raise Exception(f"Failed to delete transcript: {e}")


def create_plugin():
    """Factory function to create Whisper plugin instance"""
    return WhisperPlugin()