"""
Request and response compression optimizations for ActiveLog.
Implements gzip, brotli, and zstd compression with intelligent content handling.
"""
import gzip
import brotli
import zstandard as zstd
import mimetypes
from typing import Dict, List, Any, Optional, Union, Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import asyncio
import io
import json
import logging
from dataclasses import dataclass
from enum import Enum
import time

logger = logging.getLogger(__name__)


class CompressionType(Enum):
    """Supported compression types."""
    GZIP = "gzip"
    BROTLI = "br"
    ZSTD = "zstd"
    NONE = "none"


@dataclass
class CompressionConfig:
    """Configuration for compression settings."""
    min_size: int = 1024  # Minimum response size to compress (bytes)
    compression_level: Dict[CompressionType, int] = None
    compressible_types: List[str] = None
    excluded_paths: List[str] = None
    max_compression_ratio: float = 0.8  # Don't compress if ratio > this
    enable_streaming: bool = True
    
    def __post_init__(self):
        if self.compression_level is None:
            self.compression_level = {
                CompressionType.GZIP: 6,
                CompressionType.BROTLI: 4,
                CompressionType.ZSTD: 3
            }
        
        if self.compressible_types is None:
            self.compressible_types = [
                'application/json',
                'application/javascript',
                'application/xml',
                'text/html',
                'text/css',
                'text/plain',
                'text/xml',
                'text/csv',
                'application/pdf',  # Can benefit from compression
                'image/svg+xml'
            ]
        
        if self.excluded_paths is None:
            self.excluded_paths = [
                '/health',
                '/metrics',
                '/websocket'
            ]


class CompressionStats:
    """Tracks compression performance statistics."""
    
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'compressed_requests': 0,
            'compression_ratio': 0.0,
            'avg_compression_time': 0.0,
            'by_type': {
                CompressionType.GZIP: {'count': 0, 'ratio': 0.0, 'time': 0.0},
                CompressionType.BROTLI: {'count': 0, 'ratio': 0.0, 'time': 0.0},
                CompressionType.ZSTD: {'count': 0, 'ratio': 0.0, 'time': 0.0}
            }
        }
    
    def record_compression(
        self,
        compression_type: CompressionType,
        original_size: int,
        compressed_size: int,
        compression_time: float
    ):
        """Record compression statistics."""
        self.stats['total_requests'] += 1
        
        if compression_type != CompressionType.NONE:
            self.stats['compressed_requests'] += 1
            
            # Calculate compression ratio
            ratio = compressed_size / original_size if original_size > 0 else 1.0
            
            # Update overall stats
            total_compressed = self.stats['compressed_requests']
            current_ratio = self.stats['compression_ratio']
            self.stats['compression_ratio'] = (
                (current_ratio * (total_compressed - 1) + ratio) / total_compressed
            )
            
            current_time = self.stats['avg_compression_time']
            self.stats['avg_compression_time'] = (
                (current_time * (total_compressed - 1) + compression_time) / total_compressed
            )
            
            # Update type-specific stats
            type_stats = self.stats['by_type'][compression_type]
            type_count = type_stats['count']
            type_stats['count'] += 1
            type_stats['ratio'] = (
                (type_stats['ratio'] * type_count + ratio) / (type_count + 1)
            )
            type_stats['time'] = (
                (type_stats['time'] * type_count + compression_time) / (type_count + 1)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current compression statistics."""
        return self.stats.copy()


class ContentCompressor:
    """Handles different compression algorithms."""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
        self._compressors = self._initialize_compressors()
    
    def _initialize_compressors(self) -> Dict[CompressionType, Callable]:
        """Initialize compression functions."""
        return {
            CompressionType.GZIP: self._compress_gzip,
            CompressionType.BROTLI: self._compress_brotli,
            CompressionType.ZSTD: self._compress_zstd
        }
    
    def _compress_gzip(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        level = self.config.compression_level[CompressionType.GZIP]
        return gzip.compress(data, compresslevel=level)
    
    def _compress_brotli(self, data: bytes) -> bytes:
        """Compress data using brotli."""
        level = self.config.compression_level[CompressionType.BROTLI]
        return brotli.compress(data, quality=level)
    
    def _compress_zstd(self, data: bytes) -> bytes:
        """Compress data using zstandard."""
        level = self.config.compression_level[CompressionType.ZSTD]
        compressor = zstd.ZstdCompressor(level=level)
        return compressor.compress(data)
    
    def compress(self, data: bytes, compression_type: CompressionType) -> bytes:
        """Compress data using specified algorithm."""
        if compression_type == CompressionType.NONE:
            return data
        
        compressor = self._compressors.get(compression_type)
        if not compressor:
            raise ValueError(f"Unsupported compression type: {compression_type}")
        
        return compressor(data)
    
    def choose_compression_type(self, accept_encoding: str) -> CompressionType:
        """Choose best compression type based on Accept-Encoding header."""
        # Parse Accept-Encoding header and choose best available
        encodings = [enc.strip().lower() for enc in accept_encoding.split(',')]
        
        # Priority order: brotli > zstd > gzip
        if 'br' in encodings:
            return CompressionType.BROTLI
        elif 'zstd' in encodings:
            return CompressionType.ZSTD
        elif 'gzip' in encodings:
            return CompressionType.GZIP
        
        return CompressionType.NONE
    
    def should_compress(
        self,
        content_type: Optional[str],
        content_length: int,
        path: str
    ) -> bool:
        """Determine if content should be compressed."""
        # Check minimum size
        if content_length < self.config.min_size:
            return False
        
        # Check excluded paths
        if any(path.startswith(excluded) for excluded in self.config.excluded_paths):
            return False
        
        # Check content type
        if content_type:
            # Remove charset and other parameters
            main_type = content_type.split(';')[0].strip().lower()
            return main_type in self.config.compressible_types
        
        return False


class StreamingCompressor:
    """Handles streaming compression for large responses."""
    
    def __init__(self, compression_type: CompressionType, level: int):
        self.compression_type = compression_type
        self.level = level
        self._compressor = self._create_compressor()
    
    def _create_compressor(self):
        """Create appropriate streaming compressor."""
        if self.compression_type == CompressionType.GZIP:
            return gzip.GzipFile(fileobj=io.BytesIO(), mode='wb', compresslevel=self.level)
        elif self.compression_type == CompressionType.BROTLI:
            return brotli.Compressor(quality=self.level)
        elif self.compression_type == CompressionType.ZSTD:
            return zstd.ZstdCompressor(level=self.level)
        else:
            raise ValueError(f"Streaming not supported for {self.compression_type}")
    
    def compress_chunk(self, chunk: bytes) -> bytes:
        """Compress a chunk of data."""
        if self.compression_type == CompressionType.GZIP:
            self._compressor.write(chunk)
            return self._compressor.fileobj.getvalue()
        elif self.compression_type == CompressionType.BROTLI:
            return self._compressor.compress(chunk)
        elif self.compression_type == CompressionType.ZSTD:
            return self._compressor.compress(chunk)
        
        return chunk
    
    def finalize(self) -> bytes:
        """Finalize compression and return remaining data."""
        if self.compression_type == CompressionType.GZIP:
            self._compressor.close()
            return self._compressor.fileobj.getvalue()
        elif self.compression_type == CompressionType.BROTLI:
            return self._compressor.finish()
        elif self.compression_type == CompressionType.ZSTD:
            return self._compressor.flush()
        
        return b''


class CompressionMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic response compression."""
    
    def __init__(
        self,
        app: FastAPI,
        config: CompressionConfig = None,
        stats_enabled: bool = True
    ):
        super().__init__(app)
        self.config = config or CompressionConfig()
        self.compressor = ContentCompressor(self.config)
        self.stats = CompressionStats() if stats_enabled else None
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process request and compress response if appropriate."""
        start_time = time.time()
        response = await call_next(request)
        
        # Skip compression for certain conditions
        if not self._should_compress_response(request, response):
            return response
        
        # Get compression type from Accept-Encoding
        accept_encoding = request.headers.get('accept-encoding', '')
        compression_type = self.compressor.choose_compression_type(accept_encoding)
        
        if compression_type == CompressionType.NONE:
            return response
        
        # Compress response
        compressed_response = await self._compress_response(
            response, compression_type, start_time
        )
        
        return compressed_response
    
    def _should_compress_response(self, request: Request, response: Response) -> bool:
        """Determine if response should be compressed."""
        # Check if already compressed
        if 'content-encoding' in response.headers:
            return False
        
        # Check content type and size
        content_type = response.headers.get('content-type')
        content_length = int(response.headers.get('content-length', 0))
        
        return self.compressor.should_compress(
            content_type,
            content_length,
            request.url.path
        )
    
    async def _compress_response(
        self,
        response: Response,
        compression_type: CompressionType,
        start_time: float
    ) -> Response:
        """Compress the response content."""
        try:
            # Handle different response types
            if isinstance(response, StreamingResponse):
                return await self._compress_streaming_response(
                    response, compression_type, start_time
                )
            else:
                return await self._compress_regular_response(
                    response, compression_type, start_time
                )
        
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return response  # Return original response on compression error
    
    async def _compress_regular_response(
        self,
        response: Response,
        compression_type: CompressionType,
        start_time: float
    ) -> Response:
        """Compress regular (non-streaming) response."""
        # Get response content
        if hasattr(response, 'body'):
            original_content = response.body
        else:
            original_content = b''
        
        original_size = len(original_content)
        
        # Compress content
        compression_start = time.time()
        compressed_content = self.compressor.compress(original_content, compression_type)
        compression_time = time.time() - compression_start
        
        compressed_size = len(compressed_content)
        
        # Check compression ratio
        if original_size > 0:
            ratio = compressed_size / original_size
            if ratio > self.config.max_compression_ratio:
                # Compression not effective, return original
                if self.stats:
                    self.stats.record_compression(
                        CompressionType.NONE, original_size, original_size, 0
                    )
                return response
        
        # Create compressed response
        compressed_response = Response(
            content=compressed_content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
        
        # Update headers
        compressed_response.headers['content-encoding'] = compression_type.value
        compressed_response.headers['content-length'] = str(compressed_size)
        compressed_response.headers['vary'] = 'Accept-Encoding'
        
        # Record stats
        if self.stats:
            self.stats.record_compression(
                compression_type, original_size, compressed_size, compression_time
            )
        
        logger.debug(
            f"Compressed response: {original_size} -> {compressed_size} bytes "
            f"({ratio:.2%}) using {compression_type.value} in {compression_time:.3f}s"
        )
        
        return compressed_response
    
    async def _compress_streaming_response(
        self,
        response: StreamingResponse,
        compression_type: CompressionType,
        start_time: float
    ) -> StreamingResponse:
        """Compress streaming response."""
        if not self.config.enable_streaming:
            return response
        
        level = self.config.compression_level[compression_type]
        streaming_compressor = StreamingCompressor(compression_type, level)
        
        async def compress_generator():
            """Generator that compresses chunks on the fly."""
            total_original = 0
            total_compressed = 0
            
            try:
                async for chunk in response.body_iterator:
                    if isinstance(chunk, str):
                        chunk = chunk.encode('utf-8')
                    
                    total_original += len(chunk)
                    compressed_chunk = streaming_compressor.compress_chunk(chunk)
                    total_compressed += len(compressed_chunk)
                    
                    if compressed_chunk:
                        yield compressed_chunk
                
                # Finalize compression
                final_chunk = streaming_compressor.finalize()
                if final_chunk:
                    total_compressed += len(final_chunk)
                    yield final_chunk
                
                # Record stats
                if self.stats:
                    compression_time = time.time() - start_time
                    self.stats.record_compression(
                        compression_type, total_original, total_compressed, compression_time
                    )
            
            except Exception as e:
                logger.error(f"Streaming compression error: {e}")
                # Try to yield remaining original content
                async for chunk in response.body_iterator:
                    yield chunk
        
        # Create compressed streaming response
        compressed_response = StreamingResponse(
            compress_generator(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
        
        # Update headers
        compressed_response.headers['content-encoding'] = compression_type.value
        compressed_response.headers['vary'] = 'Accept-Encoding'
        # Remove content-length for streaming
        compressed_response.headers.pop('content-length', None)
        
        return compressed_response
    
    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get compression statistics."""
        return self.stats.get_stats() if self.stats else None


class JSONCompressionHandler:
    """Specialized handler for JSON response compression."""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
        self.compressor = ContentCompressor(config)
    
    def compress_json_response(
        self,
        data: Any,
        accept_encoding: str,
        ensure_ascii: bool = False,
        separators: tuple = (',', ':')
    ) -> tuple[bytes, CompressionType]:
        """Compress JSON data optimally."""
        # Serialize with optimal settings
        json_str = json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            separators=separators,  # Compact format
            default=str
        )
        json_bytes = json_str.encode('utf-8')
        
        # Choose compression
        compression_type = self.compressor.choose_compression_type(accept_encoding)
        
        if compression_type == CompressionType.NONE:
            return json_bytes, compression_type
        
        # Check if worth compressing
        if len(json_bytes) < self.config.min_size:
            return json_bytes, CompressionType.NONE
        
        # Compress
        compressed_data = self.compressor.compress(json_bytes, compression_type)
        
        # Check compression ratio
        if len(json_bytes) > 0:
            ratio = len(compressed_data) / len(json_bytes)
            if ratio > self.config.max_compression_ratio:
                return json_bytes, CompressionType.NONE
        
        return compressed_data, compression_type


def create_optimized_json_response(
    data: Any,
    request: Request,
    config: CompressionConfig = None
) -> Response:
    """Create an optimized JSON response with compression."""
    config = config or CompressionConfig()
    handler = JSONCompressionHandler(config)
    
    accept_encoding = request.headers.get('accept-encoding', '')
    compressed_data, compression_type = handler.compress_json_response(
        data, accept_encoding
    )
    
    headers = {
        'content-type': 'application/json',
        'content-length': str(len(compressed_data))
    }
    
    if compression_type != CompressionType.NONE:
        headers['content-encoding'] = compression_type.value
        headers['vary'] = 'Accept-Encoding'
    
    return Response(
        content=compressed_data,
        headers=headers
    )


def add_compression_middleware(app: FastAPI, config: CompressionConfig = None):
    """Add compression middleware to FastAPI app."""
    config = config or CompressionConfig()
    middleware = CompressionMiddleware(app, config)
    app.add_middleware(CompressionMiddleware, config=config)
    return middleware


# Example usage for file downloads
class FileCompressionHandler:
    """Handles compression for file downloads."""
    
    def __init__(self, config: CompressionConfig):
        self.config = config
        self.compressor = ContentCompressor(config)
    
    async def compress_file_stream(
        self,
        file_stream,
        filename: str,
        accept_encoding: str
    ) -> tuple[AsyncIterable[bytes], CompressionType]:
        """Compress file stream for download."""
        # Determine if file should be compressed based on type
        content_type, _ = mimetypes.guess_type(filename)
        
        if not self.compressor.should_compress(content_type, float('inf'), ''):
            # Return original stream
            return file_stream, CompressionType.NONE
        
        compression_type = self.compressor.choose_compression_type(accept_encoding)
        if compression_type == CompressionType.NONE:
            return file_stream, CompressionType.NONE
        
        # Create streaming compressor
        level = self.config.compression_level[compression_type]
        streaming_compressor = StreamingCompressor(compression_type, level)
        
        async def compressed_stream():
            """Compressed file stream generator."""
            try:
                async for chunk in file_stream:
                    compressed_chunk = streaming_compressor.compress_chunk(chunk)
                    if compressed_chunk:
                        yield compressed_chunk
                
                # Finalize
                final_chunk = streaming_compressor.finalize()
                if final_chunk:
                    yield final_chunk
            
            except Exception as e:
                logger.error(f"File compression error: {e}")
                # Fall back to original stream
                async for chunk in file_stream:
                    yield chunk
        
        return compressed_stream(), compression_type