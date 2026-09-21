"""
Intelligent Result Caching System
Minimizes redundant AI processing through smart caching with similarity matching
"""

import asyncio
import aioredis
import hashlib
import json
import lz4
import os
import pickle
import shutil
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.ai_operations import CacheEntry, AIOperationType, AIOperation
from ...config.settings import settings

logger = logging.getLogger(__name__)

class ResultCache:
    """Intelligent caching system with similarity matching and compression"""
    
    def __init__(self, db: Session):
        self.db = db
        self.redis_client = None
        self.cache_dir = "/tmp/ai_cache"
        self.settings = settings.cache
        
        # TTL settings by operation type
        self.ttl_hours = {
            AIOperationType.IMAGE_GENERATION: self.settings.image_cache_ttl_hours,
            AIOperationType.TEXT_GENERATION: self.settings.text_cache_ttl_hours,
            AIOperationType.VOICE_SYNTHESIS: self.settings.voice_cache_ttl_hours,
            AIOperationType.VIDEO_GENERATION: self.settings.video_cache_ttl_hours
        }
        
        # Similarity thresholds for fuzzy matching
        self.similarity_thresholds = {
            AIOperationType.IMAGE_GENERATION: 0.95,  # Very high for images
            AIOperationType.TEXT_GENERATION: 0.85,   # Lower for text (more flexible)
            AIOperationType.VOICE_SYNTHESIS: 0.90,   # High for voice
            AIOperationType.VIDEO_GENERATION: 0.95   # Very high for video
        }
        
        # Initialize storage
        os.makedirs(self.cache_dir, exist_ok=True)
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = await aioredis.from_url(
                self.settings.redis_url,
                encoding="utf-8",
                decode_responses=False  # We handle encoding manually for binary data
            )
            await self.redis_client.ping()
            logger.info("Redis cache connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed, using local cache only: {str(e)}")
            self.redis_client = None
    
    async def get_cached_result(
        self,
        input_hash: str,
        operation_type: AIOperationType,
        similarity_search: bool = True
    ) -> Optional[Dict[str, Any]]:
        """Get cached result with optional similarity matching"""
        
        # First try exact match
        cached_entry = await self._get_exact_match(input_hash, operation_type)
        if cached_entry:
            await self._update_cache_hit_stats(cached_entry)
            return await self._deserialize_cache_entry(cached_entry)
        
        # If no exact match and similarity search is enabled, try fuzzy matching
        if similarity_search and operation_type in [AIOperationType.TEXT_GENERATION]:
            similar_entry = await self._find_similar_cached_result(input_hash, operation_type)
            if similar_entry:
                await self._update_cache_hit_stats(similar_entry)
                return await self._deserialize_cache_entry(similar_entry)
        
        return None
    
    async def store_result(
        self,
        input_hash: str,
        operation_type: AIOperationType,
        output_data: Dict[str, Any],
        output_files: Dict[str, Any],
        original_cost_cc: Decimal
    ) -> bool:
        """Store result in cache with intelligent compression and file handling"""
        
        try:
            # Calculate expiration time
            ttl_hours = self.ttl_hours.get(operation_type, 72)  # Default 3 days
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            # Handle file storage
            stored_files = await self._store_output_files(output_files, input_hash)
            
            # Create cache entry
            cache_entry = CacheEntry(
                input_hash=input_hash,
                operation_type=operation_type,
                model_name=output_data.get("model", "unknown"),
                output_data=output_data,
                output_files=output_files,
                file_paths=stored_files,
                original_cost_cc=original_cost_cc,
                expires_at=expires_at
            )
            
            # Store in database
            self.db.add(cache_entry)
            self.db.commit()
            
            # Store in Redis for fast access
            if self.redis_client:
                await self._store_in_redis(cache_entry)
            
            # Clean up old cache entries if we're approaching size limits
            await self._cleanup_old_entries()
            
            logger.info(f"Cached result for {operation_type.value}: {input_hash[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store cache result: {str(e)}")
            return False
    
    async def _get_exact_match(self, input_hash: str, operation_type: AIOperationType) -> Optional[CacheEntry]:
        """Get exact cache match from database"""
        
        cache_entry = (
            self.db.query(CacheEntry)
            .filter(
                and_(
                    CacheEntry.input_hash == input_hash,
                    CacheEntry.operation_type == operation_type,
                    CacheEntry.expires_at > datetime.utcnow()
                )
            )
            .first()
        )
        
        return cache_entry
    
    async def _find_similar_cached_result(
        self,
        input_hash: str,
        operation_type: AIOperationType,
        limit: int = 10
    ) -> Optional[CacheEntry]:
        """Find similar cached results using fuzzy matching"""
        
        # Get recent cache entries of the same type
        recent_entries = (
            self.db.query(CacheEntry)
            .filter(
                and_(
                    CacheEntry.operation_type == operation_type,
                    CacheEntry.expires_at > datetime.utcnow()
                )
            )
            .order_by(desc(CacheEntry.last_accessed))
            .limit(limit)
            .all()
        )
        
        if not recent_entries:
            return None
        
        # Calculate similarity scores
        similarity_threshold = self.similarity_thresholds.get(operation_type, 0.85)
        best_match = None
        best_similarity = 0.0
        
        for entry in recent_entries:
            similarity = self._calculate_hash_similarity(input_hash, entry.input_hash)
            if similarity > similarity_threshold and similarity > best_similarity:
                best_similarity = similarity
                best_match = entry
        
        return best_match
    
    def _calculate_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate similarity between two hashes using Hamming distance"""
        
        if len(hash1) != len(hash2):
            return 0.0
        
        # Convert hex strings to binary
        try:
            bin1 = bin(int(hash1, 16))[2:].zfill(len(hash1) * 4)
            bin2 = bin(int(hash2, 16))[2:].zfill(len(hash2) * 4)
            
            # Calculate Hamming distance
            differences = sum(c1 != c2 for c1, c2 in zip(bin1, bin2))
            similarity = 1.0 - (differences / len(bin1))
            
            return similarity
        except:
            return 0.0
    
    async def _store_output_files(self, output_files: Dict, input_hash: str) -> Dict[str, str]:
        """Store output files locally and return paths"""
        
        stored_files = {}
        
        if not output_files:
            return stored_files
        
        # Create directory for this cache entry
        cache_entry_dir = os.path.join(self.cache_dir, input_hash[:8])
        os.makedirs(cache_entry_dir, exist_ok=True)
        
        for file_key, file_info in output_files.items():
            if isinstance(file_info, list):
                # Handle multiple files
                stored_file_list = []
                for i, file_data in enumerate(file_info):
                    stored_path = await self._store_single_file(file_data, cache_entry_dir, f"{file_key}_{i}")
                    if stored_path:
                        stored_file_list.append(stored_path)
                stored_files[file_key] = stored_file_list
            else:
                # Handle single file
                stored_path = await self._store_single_file(file_info, cache_entry_dir, file_key)
                if stored_path:
                    stored_files[file_key] = stored_path
        
        return stored_files
    
    async def _store_single_file(self, file_info: Dict, cache_dir: str, file_key: str) -> Optional[str]:
        """Store a single file to cache directory"""
        
        try:
            # Handle different file info formats
            source_path = None
            filename = None
            
            if isinstance(file_info, dict):
                source_path = file_info.get("local_path")
                filename = file_info.get("filename", f"{file_key}.bin")
            elif isinstance(file_info, str):
                source_path = file_info
                filename = os.path.basename(source_path) or f"{file_key}.bin"
            
            if not source_path or not os.path.exists(source_path):
                return None
            
            # Generate cache file path
            cache_file_path = os.path.join(cache_dir, filename)
            
            # Copy file to cache directory
            if self.settings.enable_cache_compression and filename.endswith(('.png', '.jpg', '.jpeg', '.wav', '.mp3')):
                # For binary files that don't compress well, just copy
                shutil.copy2(source_path, cache_file_path)
            else:
                # For other files, try compression
                await self._compress_and_store_file(source_path, cache_file_path)
            
            return cache_file_path
            
        except Exception as e:
            logger.error(f"Failed to store file {file_key}: {str(e)}")
            return None
    
    async def _compress_and_store_file(self, source_path: str, cache_path: str):
        """Compress and store file"""
        
        try:
            with open(source_path, 'rb') as source_file:
                data = source_file.read()
            
            # Try to compress
            if self.settings.enable_cache_compression:
                compressed_data = lz4.frame.compress(data)
                # Only use compressed version if it's significantly smaller
                if len(compressed_data) < len(data) * 0.8:
                    cache_path += ".lz4"
                    data = compressed_data
            
            with open(cache_path, 'wb') as cache_file:
                cache_file.write(data)
                
        except Exception as e:
            # Fallback to simple copy
            shutil.copy2(source_path, cache_path)
    
    async def _store_in_redis(self, cache_entry: CacheEntry):
        """Store cache entry metadata in Redis for fast lookup"""
        
        if not self.redis_client:
            return
        
        try:
            cache_key = f"ai_cache:{cache_entry.input_hash}"
            
            # Store metadata (not the actual files)
            cache_data = {
                "id": cache_entry.id,
                "operation_type": cache_entry.operation_type.value,
                "model_name": cache_entry.model_name,
                "output_data": json.dumps(cache_entry.output_data),
                "expires_at": cache_entry.expires_at.timestamp()
            }
            
            # Serialize and compress
            serialized_data = pickle.dumps(cache_data)
            if self.settings.enable_cache_compression:
                serialized_data = lz4.frame.compress(serialized_data)
            
            # Calculate TTL for Redis
            ttl_seconds = int((cache_entry.expires_at - datetime.utcnow()).total_seconds())
            
            await self.redis_client.setex(cache_key, ttl_seconds, serialized_data)
            
        except Exception as e:
            logger.warning(f"Failed to store in Redis: {str(e)}")
    
    async def _update_cache_hit_stats(self, cache_entry: CacheEntry):
        """Update cache hit statistics"""
        
        cache_entry.hit_count += 1
        cache_entry.last_accessed = datetime.utcnow()
        self.db.commit()
    
    async def _deserialize_cache_entry(self, cache_entry: CacheEntry) -> Dict[str, Any]:
        """Deserialize cache entry to return format"""
        
        result = {
            "output_data": cache_entry.output_data,
            "output_files": {},
            "original_cost_cc": cache_entry.original_cost_cc,
            "cached_at": cache_entry.created_at,
            "hit_count": cache_entry.hit_count
        }
        
        # Reconstruct file paths
        if cache_entry.file_paths:
            result["output_files"] = await self._reconstruct_file_paths(cache_entry.file_paths)
        
        return result
    
    async def _reconstruct_file_paths(self, stored_file_paths: Dict) -> Dict:
        """Reconstruct file paths from cache storage"""
        
        reconstructed = {}
        
        for file_key, file_paths in stored_file_paths.items():
            if isinstance(file_paths, list):
                # Handle multiple files
                file_list = []
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        file_info = {
                            "local_path": file_path,
                            "filename": os.path.basename(file_path),
                            "cached": True
                        }
                        # Decompress if necessary
                        if file_path.endswith(".lz4"):
                            decompressed_path = await self._decompress_file(file_path)
                            if decompressed_path:
                                file_info["local_path"] = decompressed_path
                        
                        file_list.append(file_info)
                
                reconstructed[file_key] = file_list
            else:
                # Handle single file
                if os.path.exists(file_paths):
                    file_info = {
                        "local_path": file_paths,
                        "filename": os.path.basename(file_paths),
                        "cached": True
                    }
                    
                    # Decompress if necessary
                    if file_paths.endswith(".lz4"):
                        decompressed_path = await self._decompress_file(file_paths)
                        if decompressed_path:
                            file_info["local_path"] = decompressed_path
                    
                    reconstructed[file_key] = file_info
        
        return reconstructed
    
    async def _decompress_file(self, compressed_path: str) -> Optional[str]:
        """Decompress a compressed cache file"""
        
        try:
            decompressed_path = compressed_path[:-4]  # Remove .lz4 extension
            
            # Check if decompressed version already exists
            if os.path.exists(decompressed_path):
                return decompressed_path
            
            # Decompress
            with open(compressed_path, 'rb') as compressed_file:
                compressed_data = compressed_file.read()
            
            decompressed_data = lz4.frame.decompress(compressed_data)
            
            with open(decompressed_path, 'wb') as decompressed_file:
                decompressed_file.write(decompressed_data)
            
            return decompressed_path
            
        except Exception as e:
            logger.error(f"Failed to decompress file {compressed_path}: {str(e)}")
            return None
    
    async def _cleanup_old_entries(self):
        """Clean up old cache entries to manage storage size"""
        
        try:
            # Check cache size
            cache_size_gb = await self._get_cache_size_gb()
            
            if cache_size_gb > self.settings.max_cache_size_gb:
                logger.info(f"Cache size ({cache_size_gb:.1f} GB) exceeds limit, cleaning up...")
                
                # Get expired entries
                expired_entries = (
                    self.db.query(CacheEntry)
                    .filter(CacheEntry.expires_at < datetime.utcnow())
                    .all()
                )
                
                # Delete expired entries
                for entry in expired_entries:
                    await self._delete_cache_entry(entry)
                
                # If still too big, delete least recently used entries
                cache_size_gb = await self._get_cache_size_gb()
                if cache_size_gb > self.settings.max_cache_size_gb:
                    lru_entries = (
                        self.db.query(CacheEntry)
                        .filter(CacheEntry.expires_at > datetime.utcnow())
                        .order_by(CacheEntry.last_accessed)
                        .limit(100)  # Delete up to 100 LRU entries
                        .all()
                    )
                    
                    for entry in lru_entries:
                        await self._delete_cache_entry(entry)
                        cache_size_gb = await self._get_cache_size_gb()
                        if cache_size_gb <= self.settings.max_cache_size_gb * 0.8:  # Leave some headroom
                            break
                
                logger.info(f"Cache cleanup completed, new size: {cache_size_gb:.1f} GB")
                
        except Exception as e:
            logger.error(f"Cache cleanup failed: {str(e)}")
    
    async def _get_cache_size_gb(self) -> float:
        """Calculate current cache size in GB"""
        
        total_size = 0
        
        for root, dirs, files in os.walk(self.cache_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass
        
        return total_size / (1024 * 1024 * 1024)  # Convert bytes to GB
    
    async def _delete_cache_entry(self, cache_entry: CacheEntry):
        """Delete a cache entry and its associated files"""
        
        try:
            # Delete files
            if cache_entry.file_paths:
                for file_paths in cache_entry.file_paths.values():
                    if isinstance(file_paths, list):
                        for file_path in file_paths:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    elif isinstance(file_paths, str) and os.path.exists(file_paths):
                        os.remove(file_paths)
            
            # Delete from Redis
            if self.redis_client:
                cache_key = f"ai_cache:{cache_entry.input_hash}"
                await self.redis_client.delete(cache_key)
            
            # Delete from database
            self.db.delete(cache_entry)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to delete cache entry {cache_entry.id}: {str(e)}")
    
    async def get_cache_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get cache performance statistics"""
        
        # Base query
        query = self.db.query(CacheEntry)
        
        # Filter by user if specified (would need to join with operations)
        if user_id:
            query = query.join(AIOperation, CacheEntry.operation_id == AIOperation.id)
            query = query.filter(AIOperation.user_id == user_id)
        
        # Calculate statistics
        total_entries = query.count()
        
        if total_entries == 0:
            return {"message": "No cache entries found"}
        
        # Hit statistics
        hit_stats = (
            query.with_entities(
                func.sum(CacheEntry.hit_count).label("total_hits"),
                func.avg(CacheEntry.hit_count).label("avg_hits"),
                func.sum(CacheEntry.original_cost_cc).label("total_original_cost")
            )
            .first()
        )
        
        # Statistics by operation type
        type_stats = (
            query.with_entities(
                CacheEntry.operation_type,
                func.count(CacheEntry.id).label("count"),
                func.sum(CacheEntry.hit_count).label("hits"),
                func.sum(CacheEntry.original_cost_cc).label("cost_saved")
            )
            .group_by(CacheEntry.operation_type)
            .all()
        )
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = (
            query.filter(CacheEntry.last_accessed >= week_ago)
            .count()
        )
        
        # Cache size
        cache_size_gb = await self._get_cache_size_gb()
        
        return {
            "overview": {
                "total_entries": total_entries,
                "total_hits": int(hit_stats.total_hits or 0),
                "average_hits_per_entry": float(hit_stats.avg_hits or 0),
                "total_cost_saved_cc": float(hit_stats.total_original_cost or 0),
                "cache_size_gb": cache_size_gb,
                "recent_activity_7d": recent_activity
            },
            "by_operation_type": [
                {
                    "operation_type": stat.operation_type.value,
                    "entries": stat.count,
                    "total_hits": stat.hits,
                    "cost_saved_cc": float(stat.cost_saved or 0)
                }
                for stat in type_stats
            ],
            "cache_efficiency": {
                "hit_rate": (hit_stats.total_hits / max(total_entries, 1)) if hit_stats.total_hits else 0,
                "storage_efficiency": f"{cache_size_gb / max(total_entries, 1):.3f} GB per entry"
            }
        }
    
    async def clear_expired_cache(self) -> Dict[str, int]:
        """Manually clear expired cache entries"""
        
        expired_entries = (
            self.db.query(CacheEntry)
            .filter(CacheEntry.expires_at < datetime.utcnow())
            .all()
        )
        
        deleted_count = 0
        freed_space_gb = 0
        
        for entry in expired_entries:
            # Calculate space that will be freed
            if entry.file_paths:
                for file_paths in entry.file_paths.values():
                    if isinstance(file_paths, list):
                        for file_path in file_paths:
                            if os.path.exists(file_path):
                                freed_space_gb += os.path.getsize(file_path) / (1024 * 1024 * 1024)
                    elif isinstance(file_paths, str) and os.path.exists(file_paths):
                        freed_space_gb += os.path.getsize(file_paths) / (1024 * 1024 * 1024)
            
            await self._delete_cache_entry(entry)
            deleted_count += 1
        
        return {
            "deleted_entries": deleted_count,
            "freed_space_gb": round(freed_space_gb, 2)
        }
    
    async def preload_similar_results(self, operation_type: AIOperationType, user_patterns: List[str]) -> int:
        """Preload cache with results similar to user patterns"""
        
        # This would be used to predict and cache likely future requests
        # For now, return a placeholder
        return 0
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()