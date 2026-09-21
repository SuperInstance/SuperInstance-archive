"""
MinIO object storage service for video files
"""
import asyncio
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, BinaryIO
from urllib.parse import urlparse
from pathlib import Path

from minio import Minio
from minio.error import S3Error
import aiofiles
import structlog

from config.settings import settings

logger = structlog.get_logger()


class StorageService:
    """
    MinIO-based storage service for video files and assets
    """
    
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.buckets = {
            "videos": settings.minio_bucket_videos,
            "thumbnails": settings.minio_bucket_thumbnails,
            "processed": settings.minio_bucket_processed
        }
        
    async def initialize(self) -> None:
        """Initialize storage service and create buckets"""
        try:
            # Create buckets if they don't exist
            for bucket_name in self.buckets.values():
                if not self.client.bucket_exists(bucket_name):
                    self.client.make_bucket(bucket_name)
                    logger.info("Created bucket", bucket=bucket_name)
                    
            logger.info("Storage service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize storage service", error=str(e))
            raise

    async def upload_file(
        self, 
        file_path: str, 
        object_name: str, 
        bucket_type: str = "videos",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file to MinIO
        
        Args:
            file_path: Local path to file
            object_name: Name to store in MinIO
            bucket_type: Type of bucket (videos, thumbnails, processed)
            metadata: Optional metadata to attach
            
        Returns:
            Upload result with URL and metadata
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path)
            
            # Get file info
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            # Prepare metadata
            upload_metadata = {
                "upload-timestamp": datetime.utcnow().isoformat(),
                "file-hash": file_hash,
                "file-size": str(file_size),
                **(metadata or {})
            }
            
            # Upload file
            result = self.client.fput_object(
                bucket_name,
                object_name,
                file_path,
                metadata=upload_metadata
            )
            
            # Get object URL
            object_url = self.client.presigned_get_object(
                bucket_name, 
                object_name,
                expires=timedelta(days=7)
            )
            
            logger.info("File uploaded successfully", 
                       bucket=bucket_name, 
                       object_name=object_name,
                       file_size=file_size)
            
            return {
                "bucket": bucket_name,
                "object_name": object_name,
                "url": object_url,
                "size": file_size,
                "hash": file_hash,
                "etag": result.etag,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            logger.error("Failed to upload file", 
                        file_path=file_path,
                        object_name=object_name,
                        error=str(e))
            raise

    async def upload_stream(
        self,
        data_stream: BinaryIO,
        object_name: str,
        length: int,
        bucket_type: str = "videos",
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload data from stream to MinIO
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            # Prepare metadata
            upload_metadata = {
                "upload-timestamp": datetime.utcnow().isoformat(),
                "content-type": content_type,
                **(metadata or {})
            }
            
            # Upload stream
            result = self.client.put_object(
                bucket_name,
                object_name,
                data_stream,
                length,
                content_type=content_type,
                metadata=upload_metadata
            )
            
            # Get object URL
            object_url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(days=7)
            )
            
            logger.info("Stream uploaded successfully",
                       bucket=bucket_name,
                       object_name=object_name,
                       size=length)
            
            return {
                "bucket": bucket_name,
                "object_name": object_name,
                "url": object_url,
                "size": length,
                "etag": result.etag,
                "metadata": upload_metadata
            }
            
        except Exception as e:
            logger.error("Failed to upload stream",
                        object_name=object_name,
                        error=str(e))
            raise

    async def download_file(
        self,
        object_name: str,
        file_path: str,
        bucket_type: str = "videos"
    ) -> Dict[str, Any]:
        """
        Download a file from MinIO
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            # Download file
            self.client.fget_object(bucket_name, object_name, file_path)
            
            # Get file info
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            
            # Get object metadata
            object_stat = self.client.stat_object(bucket_name, object_name)
            
            logger.info("File downloaded successfully",
                       bucket=bucket_name,
                       object_name=object_name,
                       file_path=file_path,
                       size=file_size)
            
            return {
                "file_path": file_path,
                "size": file_size,
                "metadata": object_stat.metadata,
                "last_modified": object_stat.last_modified
            }
            
        except Exception as e:
            logger.error("Failed to download file",
                        object_name=object_name,
                        file_path=file_path,
                        error=str(e))
            raise

    async def get_object_info(
        self,
        object_name: str,
        bucket_type: str = "videos"
    ) -> Dict[str, Any]:
        """
        Get information about an object
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            # Get object stats
            object_stat = self.client.stat_object(bucket_name, object_name)
            
            return {
                "bucket": bucket_name,
                "object_name": object_name,
                "size": object_stat.size,
                "etag": object_stat.etag,
                "last_modified": object_stat.last_modified,
                "content_type": object_stat.content_type,
                "metadata": object_stat.metadata
            }
            
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise
        except Exception as e:
            logger.error("Failed to get object info",
                        object_name=object_name,
                        error=str(e))
            raise

    async def delete_object(
        self,
        object_name: str,
        bucket_type: str = "videos"
    ) -> bool:
        """
        Delete an object from storage
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            self.client.remove_object(bucket_name, object_name)
            
            logger.info("Object deleted successfully",
                       bucket=bucket_name,
                       object_name=object_name)
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete object",
                        object_name=object_name,
                        error=str(e))
            return False

    async def list_objects(
        self,
        prefix: str = "",
        bucket_type: str = "videos",
        recursive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List objects in a bucket
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            objects = []
            for obj in self.client.list_objects(bucket_name, prefix=prefix, recursive=recursive):
                objects.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified,
                    "is_dir": obj.is_dir
                })
                
            return objects
            
        except Exception as e:
            logger.error("Failed to list objects",
                        prefix=prefix,
                        error=str(e))
            raise

    async def get_presigned_url(
        self,
        object_name: str,
        bucket_type: str = "videos",
        expires: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> str:
        """
        Get a presigned URL for object access
        """
        try:
            bucket_name = self.buckets[bucket_type]
            
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket_name,
                    object_name,
                    expires=expires
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket_name,
                    object_name,
                    expires=expires
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return url
            
        except Exception as e:
            logger.error("Failed to generate presigned URL",
                        object_name=object_name,
                        method=method,
                        error=str(e))
            raise

    async def copy_object(
        self,
        source_object: str,
        dest_object: str,
        source_bucket_type: str = "videos",
        dest_bucket_type: str = "processed"
    ) -> Dict[str, Any]:
        """
        Copy an object from one location to another
        """
        try:
            source_bucket = self.buckets[source_bucket_type]
            dest_bucket = self.buckets[dest_bucket_type]
            
            # Copy object
            result = self.client.copy_object(
                dest_bucket,
                dest_object,
                f"{source_bucket}/{source_object}"
            )
            
            logger.info("Object copied successfully",
                       source_bucket=source_bucket,
                       source_object=source_object,
                       dest_bucket=dest_bucket,
                       dest_object=dest_object)
            
            return {
                "source_bucket": source_bucket,
                "source_object": source_object,
                "dest_bucket": dest_bucket,
                "dest_object": dest_object,
                "etag": result.etag
            }
            
        except Exception as e:
            logger.error("Failed to copy object",
                        source_object=source_object,
                        dest_object=dest_object,
                        error=str(e))
            raise

    async def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file
        """
        hash_sha256 = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                hash_sha256.update(chunk)
                
        return hash_sha256.hexdigest()

    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up temporary files older than specified age
        """
        try:
            deleted_count = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            # List temp files in processed bucket
            temp_objects = await self.list_objects(
                prefix="temp/",
                bucket_type="processed"
            )
            
            for obj in temp_objects:
                if obj["last_modified"] < cutoff_time:
                    await self.delete_object(obj["name"], "processed")
                    deleted_count += 1
                    
            logger.info("Temporary files cleaned up",
                       deleted_count=deleted_count)
            
            return deleted_count
            
        except Exception as e:
            logger.error("Failed to cleanup temp files", error=str(e))
            return 0


# Global storage service instance
storage_service = StorageService()