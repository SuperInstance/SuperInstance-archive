"""
Image and media optimization service for mobile clients

Provides efficient image processing with mobile-specific optimizations:
- Automatic format selection (WebP, AVIF, HEIC support)
- Dynamic quality adjustment based on connection
- Progressive loading and thumbnails
- Battery-aware processing
- Bandwidth optimization
"""

import asyncio
import io
import hashlib
import logging
from enum import Enum
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path

import aiofiles
from PIL import Image, ImageOps, ExifTags
from PIL.Image import Resampling
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import psutil

from ..config import settings
from ..protobuf.generated.mobile_pb import (
    MediaRequest, MediaResponse, MediaFormat, Quality, 
    OptimizationHints, MediaMetadata, ProcessingStats,
    ConnectionType, BatteryInfo, PerformanceTier
)

logger = logging.getLogger(__name__)

class ImageFormat(Enum):
    """Supported image formats for mobile optimization"""
    WEBP = "webp"
    JPEG = "jpeg"
    PNG = "png"
    AVIF = "avif"
    HEIC = "heic"

@dataclass
class OptimizationResult:
    """Result of image optimization"""
    content: bytes
    format: str
    width: int
    height: int
    quality: int
    file_size: int
    compression_ratio: float
    processing_time_ms: int
    optimization_applied: str
    cache_key: str

class MobileMediaOptimizer:
    """Mobile-optimized media processing service"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=settings.MEDIA_WORKER_THREADS)
        self.format_priority = self._get_format_priority()
        self.quality_presets = self._get_quality_presets()
        self.cache = {}
        
    def _get_format_priority(self) -> Dict[str, List[ImageFormat]]:
        """Get format priority by platform"""
        return {
            'ios': [ImageFormat.HEIC, ImageFormat.WEBP, ImageFormat.JPEG],
            'android': [ImageFormat.WEBP, ImageFormat.AVIF, ImageFormat.JPEG],
            'web': [ImageFormat.WEBP, ImageFormat.AVIF, ImageFormat.JPEG],
            'default': [ImageFormat.WEBP, ImageFormat.JPEG]
        }
    
    def _get_quality_presets(self) -> Dict[Quality, Dict[str, Any]]:
        """Quality presets for different scenarios"""
        return {
            Quality.QUALITY_LOW: {
                'jpeg_quality': 60,
                'webp_quality': 65,
                'max_dimension': 800,
                'progressive': False
            },
            Quality.QUALITY_MEDIUM: {
                'jpeg_quality': 75,
                'webp_quality': 80,
                'max_dimension': 1200,
                'progressive': True
            },
            Quality.QUALITY_HIGH: {
                'jpeg_quality': 90,
                'webp_quality': 90,
                'max_dimension': 2048,
                'progressive': True
            },
            Quality.QUALITY_ADAPTIVE: {
                'jpeg_quality': 75,
                'webp_quality': 80,
                'max_dimension': 1200,
                'progressive': True
            }
        }
    
    async def optimize_image(self, 
                           file_path: str,
                           request: MediaRequest) -> OptimizationResult:
        """
        Optimize image based on mobile requirements
        
        Args:
            file_path: Path to source image
            request: Optimization request with format and quality preferences
            
        Returns:
            OptimizationResult with optimized image data
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(file_path, request)
        
        # Check cache first
        if cache_key in self.cache:
            logger.info(f"Cache hit for {cache_key}")
            return self.cache[cache_key]
        
        try:
            # Process image in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._process_image_sync,
                file_path,
                request,
                cache_key,
                start_time
            )
            
            # Cache result
            self.cache[cache_key] = result
            
            # Log optimization metrics
            logger.info(
                f"Optimized {file_path}: "
                f"{result.file_size} bytes, "
                f"{result.compression_ratio:.2f}x compression, "
                f"{result.processing_time_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to optimize image {file_path}: {e}")
            raise
    
    def _process_image_sync(self,
                          file_path: str,
                          request: MediaRequest,
                          cache_key: str,
                          start_time: float) -> OptimizationResult:
        """Synchronous image processing (runs in thread pool)"""
        
        with Image.open(file_path) as img:
            original_size = Path(file_path).stat().st_size
            
            # Handle EXIF orientation
            img = ImageOps.exif_transpose(img)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                # For formats that don't support transparency, composite on white
                if request.format.type in [MediaFormat.Type.FORMAT_JPEG]:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode == 'P':
                    img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Determine optimal dimensions
            target_width, target_height = self._calculate_target_dimensions(
                img.size, request
            )
            
            # Resize if needed
            if (target_width, target_height) != img.size:
                img = img.resize(
                    (target_width, target_height),
                    Resampling.LANCZOS
                )
            
            # Determine optimal format and quality
            format_type, quality_settings = self._determine_optimal_settings(request)
            
            # Save optimized image
            output_buffer = io.BytesIO()
            optimization_applied = []
            
            if format_type == ImageFormat.WEBP:
                img.save(
                    output_buffer,
                    format='WEBP',
                    quality=quality_settings['webp_quality'],
                    method=6,  # Best compression
                    optimize=True
                )
                optimization_applied.append("WebP compression")
            elif format_type == ImageFormat.JPEG:
                img.save(
                    output_buffer,
                    format='JPEG',
                    quality=quality_settings['jpeg_quality'],
                    optimize=True,
                    progressive=quality_settings.get('progressive', True)
                )
                optimization_applied.append("JPEG compression")
            else:
                # Fallback to JPEG
                img.save(
                    output_buffer,
                    format='JPEG',
                    quality=quality_settings['jpeg_quality'],
                    optimize=True
                )
                optimization_applied.append("JPEG fallback")
            
            # Get result data
            optimized_content = output_buffer.getvalue()
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return OptimizationResult(
                content=optimized_content,
                format=format_type.value,
                width=target_width,
                height=target_height,
                quality=quality_settings.get('jpeg_quality', quality_settings.get('webp_quality', 75)),
                file_size=len(optimized_content),
                compression_ratio=original_size / len(optimized_content) if optimized_content else 1.0,
                processing_time_ms=processing_time_ms,
                optimization_applied=", ".join(optimization_applied),
                cache_key=cache_key
            )
    
    def _calculate_target_dimensions(self,
                                   original_size: Tuple[int, int],
                                   request: MediaRequest) -> Tuple[int, int]:
        """Calculate optimal dimensions based on request parameters"""
        
        original_width, original_height = original_size
        
        # Get max dimensions from format or request
        max_width = request.format.max_width or 1920
        max_height = request.format.max_height or 1920
        
        # Adjust based on optimization hints
        if request.hints:
            if request.hints.is_thumbnail:
                max_width = min(max_width, 300)
                max_height = min(max_height, 300)
            elif request.hints.is_preview:
                max_width = min(max_width, 800)
                max_height = min(max_height, 800)
            
            # Connection-based adjustments
            if request.hints.connection:
                if request.hints.connection.type in [
                    ConnectionType.Type.CELLULAR_2G,
                    ConnectionType.Type.CELLULAR_3G
                ]:
                    max_width = min(max_width, 600)
                    max_height = min(max_height, 600)
                elif request.hints.connection.is_metered:
                    max_width = min(max_width, 1000)
                    max_height = min(max_height, 1000)
        
        # Calculate maintaining aspect ratio
        if original_width <= max_width and original_height <= max_height:
            return original_width, original_height
        
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        ratio = min(width_ratio, height_ratio)
        
        return (
            int(original_width * ratio),
            int(original_height * ratio)
        )
    
    def _determine_optimal_settings(self,
                                  request: MediaRequest) -> Tuple[ImageFormat, Dict[str, Any]]:
        """Determine optimal format and quality settings"""
        
        # Start with requested format if specified
        if request.format.type != MediaFormat.Type.FORMAT_UNKNOWN:
            format_map = {
                MediaFormat.Type.FORMAT_WEBP: ImageFormat.WEBP,
                MediaFormat.Type.FORMAT_JPEG: ImageFormat.JPEG,
                MediaFormat.Type.FORMAT_PNG: ImageFormat.PNG,
                MediaFormat.Type.FORMAT_AVIF: ImageFormat.AVIF,
                MediaFormat.Type.FORMAT_HEIC: ImageFormat.HEIC,
            }
            target_format = format_map.get(request.format.type, ImageFormat.JPEG)
        else:
            # Auto-select based on hints
            target_format = self._auto_select_format(request)
        
        # Get quality settings
        quality_level = request.quality if request.quality != Quality.QUALITY_UNKNOWN else Quality.QUALITY_ADAPTIVE
        
        if quality_level == Quality.QUALITY_ADAPTIVE:
            quality_level = self._adaptive_quality_selection(request)
        
        quality_settings = self.quality_presets[quality_level].copy()
        
        # Apply custom quality if specified
        if request.format.quality > 0:
            quality_settings['jpeg_quality'] = request.format.quality
            quality_settings['webp_quality'] = request.format.quality
        
        return target_format, quality_settings
    
    def _auto_select_format(self, request: MediaRequest) -> ImageFormat:
        """Automatically select best format based on device and connection"""
        
        # Default to WebP for best compression
        if not request.hints or not hasattr(request.hints, 'connection'):
            return ImageFormat.WEBP
        
        # Prefer more efficient formats on slower connections
        if request.hints.connection:
            if request.hints.connection.type in [
                ConnectionType.Type.CELLULAR_2G,
                ConnectionType.Type.CELLULAR_3G
            ]:
                return ImageFormat.WEBP  # Better compression
            elif request.hints.connection.is_metered:
                return ImageFormat.WEBP
        
        return ImageFormat.WEBP
    
    def _adaptive_quality_selection(self, request: MediaRequest) -> Quality:
        """Adaptively select quality based on device conditions"""
        
        if not request.hints:
            return Quality.QUALITY_MEDIUM
        
        # Low quality for thumbnails or slow connections
        if request.hints.is_thumbnail:
            return Quality.QUALITY_LOW
        
        # Connection-based quality
        if request.hints.connection:
            if request.hints.connection.type in [
                ConnectionType.Type.CELLULAR_2G,
                ConnectionType.Type.CELLULAR_3G
            ]:
                return Quality.QUALITY_LOW
            elif request.hints.connection.is_metered:
                return Quality.QUALITY_MEDIUM
            elif request.hints.connection.speed_mbps > 10:
                return Quality.QUALITY_HIGH
        
        # Battery-based adjustments
        if request.hints.battery:
            if request.hints.battery.low_power_mode:
                return Quality.QUALITY_LOW
            elif request.hints.battery.level < 20:
                return Quality.QUALITY_MEDIUM
        
        # Prefer speed or quality hints
        if request.hints.prefer_speed:
            return Quality.QUALITY_LOW
        elif request.hints.prefer_quality:
            return Quality.QUALITY_HIGH
        
        return Quality.QUALITY_MEDIUM
    
    def _generate_cache_key(self, file_path: str, request: MediaRequest) -> str:
        """Generate cache key for optimization request"""
        
        # Include file path, modification time, and request parameters
        file_stat = Path(file_path).stat()
        
        key_data = f"{file_path}:{file_stat.st_mtime}:{file_stat.st_size}:"
        key_data += f"{request.format.type}:{request.format.max_width}:{request.format.max_height}:"
        key_data += f"{request.format.quality}:{request.quality}"
        
        if request.hints:
            key_data += f":{request.hints.is_thumbnail}:{request.hints.is_preview}"
            if request.hints.connection:
                key_data += f":{request.hints.connection.type}:{request.hints.connection.is_metered}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def create_thumbnail(self,
                             file_path: str,
                             size: Tuple[int, int] = (300, 300)) -> bytes:
        """Create thumbnail for file preview"""
        
        # Create thumbnail request
        format_info = MediaFormat()
        format_info.type = MediaFormat.Type.FORMAT_WEBP
        format_info.max_width = size[0]
        format_info.max_height = size[1]
        format_info.quality = 75
        
        hints = OptimizationHints()
        hints.is_thumbnail = True
        hints.prefer_speed = True
        
        request = MediaRequest()
        request.file_id = file_path
        request.format.CopyFrom(format_info)
        request.quality = Quality.QUALITY_LOW
        request.hints.CopyFrom(hints)
        
        result = await self.optimize_image(file_path, request)
        return result.content
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics"""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'cache_entries': len(self.cache),
            'thread_pool_size': self.executor._threads if hasattr(self.executor, '_threads') else 0
        }
    
    def clear_cache(self, max_age_seconds: int = 3600):
        """Clear old cache entries"""
        # Simple cache clearing - in production, implement LRU or time-based eviction
        if len(self.cache) > 1000:  # Max cache entries
            # Clear half the cache (simple approach)
            keys_to_remove = list(self.cache.keys())[:len(self.cache)//2]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Cleared {len(keys_to_remove)} cache entries")

# Global optimizer instance
media_optimizer = MobileMediaOptimizer()

async def optimize_media_for_mobile(file_path: str, request: MediaRequest) -> MediaResponse:
    """
    Main entry point for media optimization
    
    Args:
        file_path: Path to source media file
        request: MediaRequest with optimization parameters
        
    Returns:
        MediaResponse with optimized media
    """
    try:
        result = await media_optimizer.optimize_image(file_path, request)
        
        # Create response
        response = MediaResponse()
        response.content = result.content
        response.content_type = f"image/{result.format}"
        response.content_length = result.file_size
        response.cache_key = result.cache_key
        response.cache_ttl = 3600  # 1 hour cache
        
        # Set metadata
        metadata = MediaMetadata()
        metadata.width = result.width
        metadata.height = result.height
        metadata.format = result.format
        metadata.quality = result.quality
        metadata.file_size = result.file_size
        metadata.compression_ratio = result.compression_ratio
        
        # Set processing stats
        stats = ProcessingStats()
        stats.processing_time_ms = result.processing_time_ms
        stats.optimization_applied = result.optimization_applied
        stats.bytes_saved = Path(file_path).stat().st_size - result.file_size
        
        metadata.stats.CopyFrom(stats)
        response.metadata.CopyFrom(metadata)
        
        return response
        
    except Exception as e:
        logger.error(f"Media optimization failed: {e}")
        raise

async def get_optimization_stats() -> Dict[str, Any]:
    """Get media optimization service statistics"""
    return {
        'memory_usage': media_optimizer.get_memory_usage(),
        'supported_formats': [f.value for f in ImageFormat],
        'quality_levels': list(media_optimizer.quality_presets.keys()),
        'cache_size': len(media_optimizer.cache)
    }