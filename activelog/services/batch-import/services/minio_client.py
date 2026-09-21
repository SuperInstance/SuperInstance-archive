"""
MinIO client service for file storage
"""

import asyncio
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote

from minio import Minio
from minio.error import S3Error

from ..core.config import settings
from ..core.logging import logger


class MinIOClient:
    """Handles MinIO object storage operations"""
    
    def __init__(self):
        self.client: Optional[Minio] = None
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.initialized = False
        
        # Upload statistics
        self.stats = {
            "files_uploaded": 0,
            "bytes_uploaded": 0,
            "upload_errors": 0,
            "thumbnails_uploaded": 0,
            "start_time": datetime.now()
        }
    
    async def initialize(self):
        """Initialize MinIO client and ensure bucket exists"""
        try:
            # Create MinIO client
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
                region=settings.MINIO_REGION
            )
            
            # Test connection by checking if bucket exists
            await self._ensure_bucket_exists()
            
            self.initialized = True
            logger.info("MinIO client initialized", 
                       endpoint=settings.MINIO_ENDPOINT,
                       bucket=self.bucket_name)
            
        except Exception as e:
            logger.error("Failed to initialize MinIO client", error=str(e))
            raise
    
    async def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if it doesn't"""
        def check_and_create_bucket():
            try:
                # Check if bucket exists
                if not self.client.bucket_exists(self.bucket_name):
                    # Create bucket
                    self.client.make_bucket(self.bucket_name, location=settings.MINIO_REGION)
                    logger.info("Created MinIO bucket", bucket=self.bucket_name)
                else:
                    logger.debug("MinIO bucket already exists", bucket=self.bucket_name)
                    
            except S3Error as e:
                logger.error("MinIO bucket operation failed", 
                           bucket=self.bucket_name, 
                           error=str(e))
                raise
        
        await asyncio.get_event_loop().run_in_executor(None, check_and_create_bucket)
    
    async def upload_file(self, file_path: Path, object_name: str, 
                         metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to MinIO"""
        if not self.initialized:
            logger.error("MinIO client not initialized")
            return False
        
        try:
            # Prepare metadata
            file_metadata = {
                "uploaded_at": datetime.now().isoformat(),
                "original_filename": file_path.name,
                "file_size": str(file_path.stat().st_size)
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # Upload file
            def upload_sync():
                try:
                    with open(file_path, 'rb') as file_data:
                        self.client.put_object(
                            bucket_name=self.bucket_name,
                            object_name=object_name,
                            data=file_data,
                            length=file_path.stat().st_size,
                            metadata=file_metadata
                        )
                    return True
                except Exception as e:
                    logger.error("Error in sync upload", error=str(e))
                    return False
            
            success = await asyncio.get_event_loop().run_in_executor(None, upload_sync)
            
            if success:
                self.stats["files_uploaded"] += 1
                self.stats["bytes_uploaded"] += file_path.stat().st_size
                
                logger.debug("File uploaded to MinIO", 
                           file=str(file_path),
                           object=object_name,
                           bucket=self.bucket_name)
                return True
            else:
                self.stats["upload_errors"] += 1
                return False
                
        except Exception as e:
            logger.error("Error uploading file to MinIO", 
                        file=str(file_path),
                        object=object_name,
                        error=str(e))
            self.stats["upload_errors"] += 1
            return False
    
    async def upload_thumbnails(self, thumbnail_paths: List[str], 
                               base_object_name: str) -> List[Dict[str, Any]]:
        """Upload thumbnails to MinIO"""
        results = []
        
        for i, thumb_path in enumerate(thumbnail_paths):
            try:
                thumb_file = Path(thumb_path)
                if not thumb_file.exists():
                    results.append({
                        "success": False,
                        "path": thumb_path,
                        "error": "Thumbnail file not found"
                    })
                    continue
                
                # Generate thumbnail object name
                thumb_object = f"thumbnails/{base_object_name}_{i}_{thumb_file.name}"
                
                # Upload thumbnail
                success = await self.upload_file(
                    thumb_file, 
                    thumb_object,
                    metadata={
                        "thumbnail_index": str(i),
                        "parent_object": base_object_name
                    }
                )
                
                if success:
                    self.stats["thumbnails_uploaded"] += 1
                    results.append({
                        "success": True,
                        "path": thumb_path,
                        "object_name": thumb_object,
                        "url": self._get_object_url(thumb_object)
                    })
                else:
                    results.append({
                        "success": False,
                        "path": thumb_path,
                        "error": "Upload failed"
                    })
                    
            except Exception as e:
                logger.error("Error uploading thumbnail", 
                           path=thumb_path, 
                           error=str(e))
                results.append({
                    "success": False,
                    "path": thumb_path,
                    "error": str(e)
                })
        
        return results
    
    async def download_file(self, object_name: str, local_path: str) -> bool:
        """Download a file from MinIO"""
        if not self.initialized:
            logger.error("MinIO client not initialized")
            return False
        
        try:
            def download_sync():
                try:
                    self.client.fget_object(
                        bucket_name=self.bucket_name,
                        object_name=object_name,
                        file_path=local_path
                    )
                    return True
                except Exception as e:
                    logger.error("Error in sync download", error=str(e))
                    return False
            
            success = await asyncio.get_event_loop().run_in_executor(None, download_sync)
            
            if success:
                logger.debug("File downloaded from MinIO", 
                           object=object_name,
                           local_path=local_path)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Error downloading file from MinIO", 
                        object=object_name,
                        local_path=local_path,
                        error=str(e))
            return False
    
    async def delete_file(self, object_name: str) -> bool:
        """Delete a file from MinIO"""
        if not self.initialized:
            logger.error("MinIO client not initialized")
            return False
        
        try:
            def delete_sync():
                try:
                    self.client.remove_object(
                        bucket_name=self.bucket_name,
                        object_name=object_name
                    )
                    return True
                except Exception as e:
                    logger.error("Error in sync delete", error=str(e))
                    return False
            
            success = await asyncio.get_event_loop().run_in_executor(None, delete_sync)
            
            if success:
                logger.debug("File deleted from MinIO", 
                           object=object_name)
                return True
            else:
                return False
                
        except Exception as e:
            logger.error("Error deleting file from MinIO", 
                        object=object_name,
                        error=str(e))
            return False
    
    async def list_objects(self, prefix: str = "", limit: int = 1000) -> List[Dict[str, Any]]:
        """List objects in MinIO bucket"""
        if not self.initialized:
            logger.error("MinIO client not initialized")
            return []
        
        try:
            def list_sync():
                try:
                    objects = []
                    for obj in self.client.list_objects(
                        bucket_name=self.bucket_name,
                        prefix=prefix,
                        recursive=True
                    ):
                        objects.append({
                            "object_name": obj.object_name,
                            "size": obj.size,
                            "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                            "etag": obj.etag
                        })
                        
                        if len(objects) >= limit:
                            break
                    
                    return objects
                except Exception as e:
                    logger.error("Error in sync list", error=str(e))
                    return []
            
            objects = await asyncio.get_event_loop().run_in_executor(None, list_sync)
            return objects
            
        except Exception as e:
            logger.error("Error listing objects from MinIO", 
                        prefix=prefix,
                        error=str(e))
            return []
    
    async def get_object_info(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an object"""
        if not self.initialized:
            logger.error("MinIO client not initialized")
            return None
        
        try:
            def get_info_sync():
                try:
                    stat = self.client.stat_object(
                        bucket_name=self.bucket_name,
                        object_name=object_name
                    )
                    
                    return {
                        "object_name": stat.object_name,
                        "size": stat.size,
                        "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
                        "etag": stat.etag,
                        "content_type": stat.content_type,
                        "metadata": stat.metadata
                    }
                except Exception as e:
                    logger.error("Error in sync get_info", error=str(e))
                    return None
            
            info = await asyncio.get_event_loop().run_in_executor(None, get_info_sync)
            return info
            
        except Exception as e:
            logger.error("Error getting object info from MinIO", 
                        object=object_name,
                        error=str(e))
            return None
    
    def _get_object_url(self, object_name: str, expires_hours: int = 24) -> str:
        """Get a presigned URL for an object"""
        try:
            if not self.initialized:
                return ""
            
            # Generate presigned URL
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=timedelta(hours=expires_hours)
            )
            
            return url
            
        except Exception as e:
            logger.error("Error generating object URL", 
                        object=object_name,
                        error=str(e))
            return ""
    
    async def get_presigned_url(self, object_name: str, expires_hours: int = 24) -> str:
        """Get a presigned URL for downloading an object"""
        def get_url_sync():
            return self._get_object_url(object_name, expires_hours)
        
        url = await asyncio.get_event_loop().run_in_executor(None, get_url_sync)
        return url
    
    async def check_connection(self) -> bool:
        """Check if MinIO connection is working"""
        try:
            def check_sync():
                try:
                    # Try to list buckets as a connection test
                    buckets = self.client.list_buckets()
                    return True
                except Exception:
                    return False
            
            connected = await asyncio.get_event_loop().run_in_executor(None, check_sync)
            return connected
            
        except Exception as e:
            logger.error("Error checking MinIO connection", error=str(e))
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get MinIO client statistics"""
        stats = self.stats.copy()
        stats["initialized"] = self.initialized
        stats["bucket_name"] = self.bucket_name
        stats["endpoint"] = settings.MINIO_ENDPOINT
        
        uptime = (datetime.now() - stats["start_time"]).total_seconds()
        stats["uptime_seconds"] = uptime
        
        if stats["files_uploaded"] > 0:
            stats["avg_bytes_per_file"] = stats["bytes_uploaded"] / stats["files_uploaded"]
        else:
            stats["avg_bytes_per_file"] = 0
        
        return stats