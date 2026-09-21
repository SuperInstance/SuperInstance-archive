"""
Static file serving optimizations for ActiveLog.
Implements efficient static file serving with proper caching headers and compression.
"""
import os
import mimetypes
import hashlib
from typing import Dict, List, Any, Optional, AsyncIterator
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import asyncio
import logging
from datetime import datetime, timedelta
import aiofiles
import aiofiles.os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CachePolicy:
    """Cache policy configuration for different file types."""
    max_age: int  # seconds
    immutable: bool = False
    private: bool = False
    no_cache: bool = False
    must_revalidate: bool = False
    stale_while_revalidate: int = 0
    stale_if_error: int = 0


class OptimizedStaticFiles(StaticFiles):
    """Enhanced static files handler with optimizations."""
    
    def __init__(
        self,
        directory: str,
        packages: Optional[List[str]] = None,
        html: bool = False,
        check_dir: bool = True,
        cache_policies: Optional[Dict[str, CachePolicy]] = None,
        enable_compression_negotiation: bool = True,
        enable_range_requests: bool = True
    ):
        super().__init__(
            directory=directory,
            packages=packages,
            html=html,
            check_dir=check_dir
        )
        
        self.cache_policies = cache_policies or self._default_cache_policies()
        self.enable_compression_negotiation = enable_compression_negotiation
        self.enable_range_requests = enable_range_requests
        self._etag_cache = {}
    
    def _default_cache_policies(self) -> Dict[str, CachePolicy]:
        """Default cache policies for different file types."""
        return {
            # Long-lived assets (with versioning)
            '.js': CachePolicy(max_age=31536000, immutable=True),  # 1 year
            '.css': CachePolicy(max_age=31536000, immutable=True),
            '.woff': CachePolicy(max_age=31536000, immutable=True),
            '.woff2': CachePolicy(max_age=31536000, immutable=True),
            '.ttf': CachePolicy(max_age=31536000, immutable=True),
            '.otf': CachePolicy(max_age=31536000, immutable=True),
            
            # Images - medium cache
            '.jpg': CachePolicy(max_age=2592000),  # 30 days
            '.jpeg': CachePolicy(max_age=2592000),
            '.png': CachePolicy(max_age=2592000),
            '.gif': CachePolicy(max_age=2592000),
            '.webp': CachePolicy(max_age=2592000),
            '.svg': CachePolicy(max_age=2592000),
            '.ico': CachePolicy(max_age=2592000),
            
            # Documents - shorter cache
            '.pdf': CachePolicy(max_age=86400),  # 1 day
            '.doc': CachePolicy(max_age=86400),
            '.docx': CachePolicy(max_age=86400),
            '.xls': CachePolicy(max_age=86400),
            '.xlsx': CachePolicy(max_age=86400),
            
            # HTML and dynamic content - no cache or very short
            '.html': CachePolicy(max_age=0, no_cache=True, must_revalidate=True),
            '.htm': CachePolicy(max_age=0, no_cache=True, must_revalidate=True),
            
            # Default policy
            'default': CachePolicy(max_age=3600)  # 1 hour
        }
    
    async def get_response(self, path: str, scope: Dict[str, Any]) -> Response:
        """Get optimized static file response."""
        try:
            # Get full file path
            full_path, stat_result = await self._get_file_info(path)
            
            if stat_result is None:
                raise HTTPException(status_code=404, detail="File not found")
            
            request = Request(scope)
            
            # Check if-modified-since header
            if_modified_since = request.headers.get('if-modified-since')
            if if_modified_since:
                try:
                    if_modified_dt = datetime.strptime(
                        if_modified_since, '%a, %d %b %Y %H:%M:%S %Z'
                    )
                    file_modified = datetime.fromtimestamp(stat_result.st_mtime)
                    
                    if file_modified <= if_modified_dt:
                        return Response(status_code=304)
                except ValueError:
                    pass
            
            # Generate and check ETag
            etag = await self._get_etag(full_path, stat_result)
            if_none_match = request.headers.get('if-none-match')
            
            if if_none_match == etag:
                return Response(status_code=304)
            
            # Handle range requests
            if self.enable_range_requests:
                range_header = request.headers.get('range')
                if range_header:
                    return await self._handle_range_request(
                        full_path, stat_result, range_header, etag
                    )
            
            # Check for pre-compressed files
            compressed_file = None
            if self.enable_compression_negotiation:
                compressed_file = await self._find_compressed_version(
                    full_path, request.headers.get('accept-encoding', '')
                )
            
            # Create response
            if compressed_file:
                response = await self._create_compressed_response(
                    compressed_file, stat_result, etag
                )
            else:
                response = await self._create_regular_response(
                    full_path, stat_result, etag
                )
            
            # Add cache headers
            self._add_cache_headers(response, full_path)
            
            return response
            
        except Exception as e:
            logger.error(f"Error serving static file {path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _get_file_info(self, path: str) -> tuple[Path, Any]:
        """Get file path and stat information."""
        full_path = Path(self.directory) / path.lstrip('/')
        
        try:
            stat_result = await aiofiles.os.stat(full_path)
            return full_path, stat_result
        except FileNotFoundError:
            return full_path, None
    
    async def _get_etag(self, file_path: Path, stat_result: Any) -> str:
        """Generate ETag for file."""
        cache_key = f"{file_path}:{stat_result.st_mtime}:{stat_result.st_size}"
        
        if cache_key in self._etag_cache:
            return self._etag_cache[cache_key]
        
        # Use file mtime and size for ETag
        etag_data = f"{stat_result.st_mtime}-{stat_result.st_size}"
        etag = f'"{hashlib.md5(etag_data.encode()).hexdigest()}"'
        
        self._etag_cache[cache_key] = etag
        return etag
    
    async def _find_compressed_version(
        self,
        file_path: Path,
        accept_encoding: str
    ) -> Optional[tuple[Path, str]]:
        """Find pre-compressed version of file."""
        encodings = [enc.strip().lower() for enc in accept_encoding.split(',')]
        
        # Check for brotli first (better compression)
        if 'br' in encodings:
            br_file = file_path.with_suffix(file_path.suffix + '.br')
            if await aiofiles.os.path.exists(br_file):
                return br_file, 'br'
        
        # Check for gzip
        if 'gzip' in encodings:
            gz_file = file_path.with_suffix(file_path.suffix + '.gz')
            if await aiofiles.os.path.exists(gz_file):
                return gz_file, 'gzip'
        
        return None
    
    async def _create_compressed_response(
        self,
        compressed_info: tuple[Path, str],
        original_stat: Any,
        etag: str
    ) -> Response:
        """Create response for pre-compressed file."""
        compressed_path, encoding = compressed_info
        
        content_type = mimetypes.guess_type(str(compressed_path.with_suffix('')))[0]
        content_type = content_type or 'application/octet-stream'
        
        headers = {
            'content-encoding': encoding,
            'vary': 'Accept-Encoding',
            'content-type': content_type,
            'etag': etag,
            'last-modified': datetime.fromtimestamp(
                original_stat.st_mtime
            ).strftime('%a, %d %b %Y %H:%M:%S GMT')
        }
        
        return FileResponse(
            path=compressed_path,
            headers=headers
        )
    
    async def _create_regular_response(
        self,
        file_path: Path,
        stat_result: Any,
        etag: str
    ) -> Response:
        """Create regular file response."""
        content_type = mimetypes.guess_type(str(file_path))[0]
        content_type = content_type or 'application/octet-stream'
        
        headers = {
            'content-type': content_type,
            'etag': etag,
            'last-modified': datetime.fromtimestamp(
                stat_result.st_mtime
            ).strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'content-length': str(stat_result.st_size)
        }
        
        return FileResponse(
            path=file_path,
            headers=headers
        )
    
    async def _handle_range_request(
        self,
        file_path: Path,
        stat_result: Any,
        range_header: str,
        etag: str
    ) -> Response:
        """Handle HTTP range requests for partial content."""
        file_size = stat_result.st_size
        
        # Parse range header
        try:
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else file_size - 1
            
            # Validate range
            if start >= file_size or end >= file_size or start > end:
                return Response(
                    status_code=416,
                    headers={'content-range': f'bytes */{file_size}'}
                )
            
            content_length = end - start + 1
            
            async def file_stream():
                async with aiofiles.open(file_path, 'rb') as f:
                    await f.seek(start)
                    remaining = content_length
                    
                    while remaining > 0:
                        chunk_size = min(8192, remaining)
                        chunk = await f.read(chunk_size)
                        
                        if not chunk:
                            break
                        
                        remaining -= len(chunk)
                        yield chunk
            
            content_type = mimetypes.guess_type(str(file_path))[0]
            content_type = content_type or 'application/octet-stream'
            
            headers = {
                'content-type': content_type,
                'content-length': str(content_length),
                'content-range': f'bytes {start}-{end}/{file_size}',
                'accept-ranges': 'bytes',
                'etag': etag,
                'last-modified': datetime.fromtimestamp(
                    stat_result.st_mtime
                ).strftime('%a, %d %b %Y %H:%M:%S GMT')
            }
            
            return StreamingResponse(
                file_stream(),
                status_code=206,
                headers=headers
            )
            
        except (ValueError, IndexError):
            # Invalid range header, return full file
            return await self._create_regular_response(file_path, stat_result, etag)
    
    def _add_cache_headers(self, response: Response, file_path: Path):
        """Add cache control headers based on file type."""
        file_ext = file_path.suffix.lower()
        
        # Get cache policy for file type
        cache_policy = self.cache_policies.get(
            file_ext, 
            self.cache_policies['default']
        )
        
        # Build cache-control header
        cache_parts = []
        
        if cache_policy.private:
            cache_parts.append('private')
        else:
            cache_parts.append('public')
        
        if cache_policy.no_cache:
            cache_parts.append('no-cache')
        
        if cache_policy.must_revalidate:
            cache_parts.append('must-revalidate')
        
        if cache_policy.immutable:
            cache_parts.append('immutable')
        
        cache_parts.append(f'max-age={cache_policy.max_age}')
        
        if cache_policy.stale_while_revalidate:
            cache_parts.append(f'stale-while-revalidate={cache_policy.stale_while_revalidate}')
        
        if cache_policy.stale_if_error:
            cache_parts.append(f'stale-if-error={cache_policy.stale_if_error}')
        
        response.headers['cache-control'] = ', '.join(cache_parts)
        
        # Add expires header for legacy clients
        if not cache_policy.no_cache:
            expires = datetime.utcnow() + timedelta(seconds=cache_policy.max_age)
            response.headers['expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')


class AdvancedFileServer:
    """Advanced file server with additional optimizations."""
    
    def __init__(
        self,
        static_dir: str,
        asset_manifest: Optional[Dict[str, Any]] = None,
        cdn_url: Optional[str] = None
    ):
        self.static_dir = Path(static_dir)
        self.asset_manifest = asset_manifest or {}
        self.cdn_url = cdn_url
        self._mime_cache = {}
    
    async def serve_file(
        self,
        request: Request,
        file_path: str,
        download: bool = False
    ) -> Response:
        """Serve a file with advanced optimizations."""
        try:
            # Resolve file path
            resolved_path = await self._resolve_file_path(file_path)
            
            if not resolved_path or not await aiofiles.os.path.exists(resolved_path):
                raise HTTPException(status_code=404, detail="File not found")
            
            # Security check - ensure file is within static directory
            if not self._is_safe_path(resolved_path):
                raise HTTPException(status_code=403, detail="Access denied")
            
            stat_result = await aiofiles.os.stat(resolved_path)
            
            # Check conditional headers
            if await self._check_not_modified(request, resolved_path, stat_result):
                return Response(status_code=304)
            
            # Handle range requests for large files
            range_header = request.headers.get('range')
            if range_header and stat_result.st_size > 1024 * 1024:  # > 1MB
                return await self._serve_range(
                    resolved_path, stat_result, range_header, download
                )
            
            # Regular file response
            return await self._serve_complete_file(
                resolved_path, stat_result, download
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error serving file {file_path}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    async def _resolve_file_path(self, file_path: str) -> Optional[Path]:
        """Resolve file path, checking for versioned assets."""
        # Clean the path
        clean_path = file_path.lstrip('/')
        
        # Check if we have a versioned asset
        if self.asset_manifest and 'assets' in self.asset_manifest:
            for original_path, asset_info in self.asset_manifest['assets'].items():
                if original_path == clean_path:
                    # Return versioned path if available
                    versioned_path = asset_info.get('versioned_path', original_path)
                    return self.static_dir / versioned_path
                elif asset_info.get('versioned_path') == clean_path:
                    # Direct access to versioned file
                    return self.static_dir / clean_path
        
        # Standard path resolution
        return self.static_dir / clean_path
    
    def _is_safe_path(self, file_path: Path) -> bool:
        """Check if file path is safe (within static directory)."""
        try:
            file_path.resolve().relative_to(self.static_dir.resolve())
            return True
        except ValueError:
            return False
    
    async def _check_not_modified(
        self,
        request: Request,
        file_path: Path,
        stat_result: Any
    ) -> bool:
        """Check if file has not been modified."""
        # Check If-Modified-Since
        if_modified_since = request.headers.get('if-modified-since')
        if if_modified_since:
            try:
                if_modified_dt = datetime.strptime(
                    if_modified_since, '%a, %d %b %Y %H:%M:%S %Z'
                )
                file_modified = datetime.fromtimestamp(stat_result.st_mtime)
                
                if file_modified <= if_modified_dt:
                    return True
            except ValueError:
                pass
        
        # Check ETag
        if_none_match = request.headers.get('if-none-match')
        if if_none_match:
            current_etag = self._generate_etag(file_path, stat_result)
            if if_none_match == current_etag:
                return True
        
        return False
    
    def _generate_etag(self, file_path: Path, stat_result: Any) -> str:
        """Generate ETag for file."""
        etag_data = f"{file_path.name}:{stat_result.st_mtime}:{stat_result.st_size}"
        return f'"{hashlib.md5(etag_data.encode()).hexdigest()}"'
    
    async def _serve_range(
        self,
        file_path: Path,
        stat_result: Any,
        range_header: str,
        download: bool
    ) -> Response:
        """Serve partial content for range request."""
        file_size = stat_result.st_size
        
        try:
            # Parse range
            range_spec = range_header.replace('bytes=', '')
            start_str, end_str = range_spec.split('-', 1)
            
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            
            # Validate range
            if start >= file_size or end >= file_size or start > end:
                return Response(
                    status_code=416,
                    headers={'content-range': f'bytes */{file_size}'}
                )
            
            content_length = end - start + 1
            
            async def range_generator():
                async with aiofiles.open(file_path, 'rb') as f:
                    await f.seek(start)
                    bytes_remaining = content_length
                    
                    while bytes_remaining > 0:
                        chunk_size = min(64 * 1024, bytes_remaining)  # 64KB chunks
                        chunk = await f.read(chunk_size)
                        
                        if not chunk:
                            break
                        
                        bytes_remaining -= len(chunk)
                        yield chunk
            
            # Prepare headers
            headers = self._prepare_file_headers(file_path, stat_result, download)
            headers.update({
                'content-length': str(content_length),
                'content-range': f'bytes {start}-{end}/{file_size}',
                'accept-ranges': 'bytes'
            })
            
            return StreamingResponse(
                range_generator(),
                status_code=206,
                headers=headers
            )
            
        except (ValueError, IndexError):
            # Invalid range, serve complete file
            return await self._serve_complete_file(file_path, stat_result, download)
    
    async def _serve_complete_file(
        self,
        file_path: Path,
        stat_result: Any,
        download: bool
    ) -> FileResponse:
        """Serve complete file."""
        headers = self._prepare_file_headers(file_path, stat_result, download)
        
        return FileResponse(
            path=file_path,
            headers=headers,
            filename=file_path.name if download else None
        )
    
    def _prepare_file_headers(
        self,
        file_path: Path,
        stat_result: Any,
        download: bool
    ) -> Dict[str, str]:
        """Prepare HTTP headers for file response."""
        # Get content type
        content_type = self._get_content_type(file_path)
        
        headers = {
            'content-type': content_type,
            'content-length': str(stat_result.st_size),
            'last-modified': datetime.fromtimestamp(
                stat_result.st_mtime
            ).strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'etag': self._generate_etag(file_path, stat_result),
            'accept-ranges': 'bytes'
        }
        
        # Set content disposition for downloads
        if download:
            headers['content-disposition'] = f'attachment; filename="{file_path.name}"'
        
        # Add security headers
        headers.update({
            'x-content-type-options': 'nosniff',
            'x-frame-options': 'DENY' if not content_type.startswith('image/') else 'SAMEORIGIN'
        })
        
        return headers
    
    def _get_content_type(self, file_path: Path) -> str:
        """Get content type with caching."""
        suffix = file_path.suffix.lower()
        
        if suffix in self._mime_cache:
            return self._mime_cache[suffix]
        
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = 'application/octet-stream'
        
        self._mime_cache[suffix] = content_type
        return content_type


def setup_static_files(
    app: FastAPI,
    static_dir: str,
    mount_path: str = "/static",
    cache_policies: Optional[Dict[str, CachePolicy]] = None
):
    """Setup optimized static file serving."""
    static_files = OptimizedStaticFiles(
        directory=static_dir,
        cache_policies=cache_policies
    )
    
    app.mount(mount_path, static_files, name="static")
    
    logger.info(f"Static files mounted at {mount_path} from {static_dir}")
    
    return static_files