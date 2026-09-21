"""
MinIO Service - Handles file organization and storage in MinIO
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import MaxRetryError
import mimetypes

from core.config import settings

logger = logging.getLogger(__name__)

class MinIOService:
    """Handles file uploads and organization in MinIO object storage"""
    
    def __init__(self):
        self.client = None
        self.bucket_name = settings.MINIO_BUCKET
        self.connected = False
        
        # Statistics
        self.stats = {
            "files_uploaded": 0,
            "upload_failures": 0,
            "total_size_uploaded": 0,
            "connection_attempts": 0,
            "last_upload": None,
            "service_start": datetime.now()
        }
        
        # Initialize connection
        asyncio.create_task(self._initialize_connection())
        
        logger.info("MinIO service initialized")
    
    async def _initialize_connection(self):
        """Initialize MinIO connection"""
        try:
            self.stats["connection_attempts"] += 1
            
            # Create MinIO client
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            
            # Test connection by checking if bucket exists
            await self._run_sync(self._ensure_bucket_exists)
            
            self.connected = True
            logger.info(f"Connected to MinIO at {settings.MINIO_ENDPOINT}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")
            self.connected = False
            
            # Retry connection after delay
            await asyncio.sleep(30)
            asyncio.create_task(self._initialize_connection())
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.debug(f"Bucket exists: {self.bucket_name}")
                
        except S3Error as e:
            logger.error(f"Error with bucket operations: {e}")
            raise
    
    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous MinIO operations in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)
    
    async def upload_file(self, file_path: str, metadata: Optional[Dict] = None) -> Dict:
        """Upload a file to MinIO with proper organization"""
        if not self.connected:
            raise Exception("MinIO client not connected")
        
        try:
            file_path_obj = Path(file_path)
            
            # Generate object name with organization structure
            object_name = self._generate_object_name(file_path_obj, metadata)
            
            # Prepare metadata for MinIO
            minio_metadata = self._prepare_metadata(file_path_obj, metadata)
            
            # Get content type
            content_type = mimetypes.guess_type(str(file_path_obj))[0] or 'application/octet-stream'
            
            # Upload file
            upload_result = await self._run_sync(
                self._upload_file_sync,
                file_path_obj,
                object_name,
                content_type,
                minio_metadata
            )
            
            # Update statistics
            self.stats["files_uploaded"] += 1
            self.stats["total_size_uploaded"] += file_path_obj.stat().st_size
            self.stats["last_upload"] = datetime.now()
            
            logger.info(f"Uploaded {file_path_obj.name} to {object_name}")
            
            return {
                "success": True,
                "object_name": object_name,
                "bucket": self.bucket_name,
                "size": file_path_obj.stat().st_size,
                "content_type": content_type,
                "url": f"{'https' if settings.MINIO_SECURE else 'http'}://{settings.MINIO_ENDPOINT}/{self.bucket_name}/{object_name}"
            }
            
        except Exception as e:
            self.stats["upload_failures"] += 1
            logger.error(f"Failed to upload {file_path}: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "object_name": None
            }
    
    def _upload_file_sync(self, file_path: Path, object_name: str, content_type: str, metadata: Dict):
        """Synchronous file upload"""
        try:
            with open(file_path, 'rb') as file_data:
                # Get file size
                file_size = file_path.stat().st_size
                
                # Upload file
                result = self.client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_name,
                    data=file_data,
                    length=file_size,
                    content_type=content_type,
                    metadata=metadata
                )
                
                return result
                
        except Exception as e:
            logger.error(f"Sync upload failed for {file_path}: {e}")
            raise
    
    def _generate_object_name(self, file_path: Path, metadata: Optional[Dict] = None) -> str:
        """Generate organized object name based on file type and metadata"""
        
        # Extract date information for organization
        date_taken = None
        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        
        # Try to get date from metadata
        if metadata and isinstance(metadata, dict):
            # Check for EXIF date from images
            exif_data = metadata.get('exif', {})
            if isinstance(exif_data, dict):
                for date_field in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                    if date_field in exif_data:
                        try:
                            date_taken = datetime.strptime(exif_data[date_field], '%Y:%m:%d %H:%M:%S')
                            break
                        except ValueError:
                            continue
            
            # Check for video/audio metadata dates
            if not date_taken and 'creation_time' in metadata:
                try:
                    date_taken = datetime.fromisoformat(metadata['creation_time'])
                except (ValueError, TypeError):
                    pass
        
        # Use date taken or file modification time
        organize_date = date_taken or file_mtime
        
        # Determine file category
        file_ext = file_path.suffix.lower()
        
        if file_ext in settings.SUPPORTED_IMAGE_FORMATS:
            category = "images"
        elif file_ext in settings.SUPPORTED_VIDEO_FORMATS:
            category = "videos"
        elif file_ext in settings.SUPPORTED_AUDIO_FORMATS:
            category = "audio"
        elif file_ext in settings.SUPPORTED_DOCUMENT_FORMATS:
            category = "documents"
        else:
            category = "other"
        
        # Generate organized path: category/year/month/filename
        year = organize_date.strftime('%Y')
        month = organize_date.strftime('%m')
        
        # Add hash prefix to avoid naming conflicts
        if metadata and metadata.get('file_hash'):
            hash_prefix = metadata['file_hash'][:8]
            filename = f"{hash_prefix}_{file_path.name}"
        else:
            filename = file_path.name
        
        object_name = f"{category}/{year}/{month}/{filename}"
        
        return object_name
    
    def _prepare_metadata(self, file_path: Path, metadata: Optional[Dict] = None) -> Dict:
        """Prepare metadata for MinIO storage"""
        minio_metadata = {
            "original-filename": file_path.name,
            "upload-timestamp": datetime.now().isoformat(),
            "file-size": str(file_path.stat().st_size),
            "file-extension": file_path.suffix.lower()
        }
        
        if metadata:
            # Add file hash if available
            if metadata.get('file_hash'):
                minio_metadata["file-hash"] = metadata['file_hash']
            
            # Add basic file info
            if metadata.get('mime_type'):
                minio_metadata["mime-type"] = metadata['mime_type']
            
            # Add image metadata
            if metadata.get('dimensions'):
                minio_metadata["image-dimensions"] = metadata['dimensions']
            
            # Add processing info
            if metadata.get('processing_time'):
                minio_metadata["processing-time"] = str(metadata['processing_time'])
            
            # Add thumbnail info
            if metadata.get('thumbnails'):
                minio_metadata["thumbnails-generated"] = str(len(metadata['thumbnails']))
            
            # Add EXIF data summary for images
            exif_data = metadata.get('exif', {})
            if isinstance(exif_data, dict):
                # Add key EXIF fields
                for field in ['Make', 'Model', 'DateTime', 'GPS']:
                    if field in exif_data:
                        minio_metadata[f"exif-{field.lower()}"] = str(exif_data[field])[:100]  # Limit length
        
        return minio_metadata
    
    async def upload_thumbnails(self, thumbnail_paths: List[str], original_object_name: str) -> List[Dict]:
        """Upload thumbnails for a file"""
        if not self.connected:
            raise Exception("MinIO client not connected")
        
        results = []
        
        for thumb_path in thumbnail_paths:
            try:
                thumb_path_obj = Path(thumb_path)
                
                # Generate thumbnail object name
                thumb_object_name = self._generate_thumbnail_object_name(original_object_name, thumb_path_obj)
                
                # Prepare thumbnail metadata
                thumb_metadata = {
                    "original-object": original_object_name,
                    "thumbnail-type": self._extract_thumbnail_type(thumb_path_obj),
                    "upload-timestamp": datetime.now().isoformat()
                }
                
                # Upload thumbnail
                content_type = mimetypes.guess_type(str(thumb_path_obj))[0] or 'image/jpeg'
                
                upload_result = await self._run_sync(
                    self._upload_file_sync,
                    thumb_path_obj,
                    thumb_object_name,
                    content_type,
                    thumb_metadata
                )
                
                results.append({
                    "success": True,
                    "thumbnail_path": str(thumb_path_obj),
                    "object_name": thumb_object_name,
                    "size": thumb_path_obj.stat().st_size
                })
                
                logger.debug(f"Uploaded thumbnail: {thumb_object_name}")
                
            except Exception as e:
                logger.error(f"Failed to upload thumbnail {thumb_path}: {e}")
                results.append({
                    "success": False,
                    "thumbnail_path": str(thumb_path),
                    "error": str(e)
                })
        
        return results
    
    def _generate_thumbnail_object_name(self, original_object_name: str, thumb_path: Path) -> str:
        """Generate object name for thumbnail"""
        # Extract thumbnail size from filename (e.g., filename_150x150.jpg)
        thumb_name = thumb_path.name
        
        # Get directory structure from original
        original_parts = original_object_name.split('/')
        if len(original_parts) >= 3:  # category/year/month/filename
            category, year, month = original_parts[:3]
            
            # Create thumbnails subdirectory
            thumb_object_name = f"{category}/{year}/{month}/thumbnails/{thumb_name}"
        else:
            # Fallback
            thumb_object_name = f"thumbnails/{thumb_name}"
        
        return thumb_object_name
    
    def _extract_thumbnail_type(self, thumb_path: Path) -> str:
        """Extract thumbnail type/size from filename"""
        thumb_name = thumb_path.stem
        
        # Look for size pattern (e.g., filename_150x150)
        if '_' in thumb_name:
            parts = thumb_name.split('_')
            last_part = parts[-1]
            if 'x' in last_part and last_part.replace('x', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '') == '':
                return last_part
        
        return "thumbnail"
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from MinIO"""
        if not self.connected:
            raise Exception("MinIO client not connected")
        
        try:
            await self._run_sync(self.client.remove_object, self.bucket_name, object_name)
            logger.info(f"Deleted object: {object_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete {object_name}: {e}")
            return False
    
    async def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict]:
        """List files in MinIO bucket with optional prefix filter"""
        if not self.connected:
            raise Exception("MinIO client not connected")
        
        try:
            def list_sync():
                objects = []
                for obj in self.client.list_objects(self.bucket_name, prefix=prefix):
                    objects.append({
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                        "etag": obj.etag,
                        "content_type": obj.content_type
                    })
                    
                    if len(objects) >= limit:
                        break
                
                return objects
            
            return await self._run_sync(list_sync)
            
        except Exception as e:
            logger.error(f"Failed to list files with prefix '{prefix}': {e}")
            return []
    
    async def get_file_info(self, object_name: str) -> Optional[Dict]:
        """Get information about a file in MinIO"""
        if not self.connected:
            return None
        
        try:
            def get_info_sync():
                try:
                    stat = self.client.stat_object(self.bucket_name, object_name)
                    return {
                        "object_name": stat.object_name,
                        "size": stat.size,
                        "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                        "etag": stat.etag,
                        "content_type": stat.content_type,
                        "metadata": stat.metadata or {}
                    }
                except S3Error:
                    return None
            
            return await self._run_sync(get_info_sync)
            
        except Exception as e:
            logger.error(f"Failed to get file info for {object_name}: {e}")
            return None
    
    async def generate_presigned_url(self, object_name: str, expires_hours: int = 24) -> Optional[str]:
        """Generate a presigned URL for file access"""
        if not self.connected:
            return None
        
        try:
            from datetime import timedelta
            
            def generate_url_sync():
                return self.client.presigned_get_object(
                    self.bucket_name,
                    object_name,
                    expires=timedelta(hours=expires_hours)
                )
            
            url = await self._run_sync(generate_url_sync)
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get MinIO service statistics"""
        stats = self.stats.copy()
        stats.update({
            "connected": self.connected,
            "bucket_name": self.bucket_name,
            "endpoint": settings.MINIO_ENDPOINT,
            "uptime_seconds": (datetime.now() - stats["service_start"]).total_seconds()
        })
        return stats
    
    async def health_check(self) -> Dict:
        """Perform MinIO health check"""
        health_data = {
            "connected": self.connected,
            "bucket_accessible": False,
            "can_upload": False,
            "error": None
        }
        
        if not self.connected:
            health_data["error"] = "Not connected to MinIO"
            return health_data
        
        try:
            # Check bucket access
            await self._run_sync(self.client.bucket_exists, self.bucket_name)
            health_data["bucket_accessible"] = True
            
            # Test upload capability with a small test object
            test_object = "health-check-test.txt"
            test_content = b"health check"
            
            await self._run_sync(
                self.client.put_object,
                self.bucket_name,
                test_object,
                io.BytesIO(test_content),
                len(test_content)
            )
            
            # Clean up test object
            await self._run_sync(self.client.remove_object, self.bucket_name, test_object)
            
            health_data["can_upload"] = True
            
        except Exception as e:
            health_data["error"] = str(e)
            logger.warning(f"MinIO health check failed: {e}")
        
        return health_data