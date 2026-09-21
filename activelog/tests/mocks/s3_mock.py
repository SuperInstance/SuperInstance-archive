"""
Mock S3 service for testing
Provides in-memory storage that simulates AWS S3 operations
"""

import json
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, BinaryIO
from unittest.mock import AsyncMock
import tempfile
import os
from pathlib import Path


class MockS3Client:
    """Mock S3 client that simulates AWS S3 operations"""
    
    def __init__(self):
        self.buckets: Dict[str, Dict[str, Any]] = {}
        self.objects: Dict[str, Dict[str, Any]] = {}  # bucket/key -> object data
        self.call_log = []
        self._setup_default_bucket()
    
    def _setup_default_bucket(self):
        """Setup default bucket for testing"""
        self.buckets["activelog-files"] = {
            "name": "activelog-files",
            "creation_date": datetime.now(timezone.utc),
            "region": "us-east-1"
        }
    
    def log_call(self, operation: str, **kwargs):
        """Log API calls for testing verification"""
        self.call_log.append({
            "operation": operation,
            "timestamp": datetime.now(timezone.utc),
            **kwargs
        })
    
    async def create_bucket(self, bucket: str, **kwargs):
        """Mock bucket creation"""
        self.log_call("create_bucket", bucket=bucket)
        
        if bucket in self.buckets:
            raise MockS3Error("BucketAlreadyExists", f"Bucket {bucket} already exists")
        
        self.buckets[bucket] = {
            "name": bucket,
            "creation_date": datetime.now(timezone.utc),
            "region": kwargs.get("CreateBucketConfiguration", {}).get("LocationConstraint", "us-east-1")
        }
        
        return {"Location": f"/{bucket}"}
    
    async def delete_bucket(self, bucket: str):
        """Mock bucket deletion"""
        self.log_call("delete_bucket", bucket=bucket)
        
        if bucket not in self.buckets:
            raise MockS3Error("NoSuchBucket", f"Bucket {bucket} does not exist")
        
        # Check if bucket is empty
        bucket_objects = [key for key in self.objects.keys() if key.startswith(f"{bucket}/")]
        if bucket_objects:
            raise MockS3Error("BucketNotEmpty", f"Bucket {bucket} is not empty")
        
        del self.buckets[bucket]
    
    async def list_buckets(self):
        """Mock bucket listing"""
        self.log_call("list_buckets")
        
        return {
            "Buckets": [
                {
                    "Name": bucket_data["name"],
                    "CreationDate": bucket_data["creation_date"]
                }
                for bucket_data in self.buckets.values()
            ],
            "Owner": {
                "DisplayName": "mock-user",
                "ID": "mock-user-id"
            }
        }
    
    async def put_object(self, bucket: str, key: str, body: bytes, **kwargs):
        """Mock object upload"""
        self.log_call("put_object", bucket=bucket, key=key, size=len(body))
        
        if bucket not in self.buckets:
            raise MockS3Error("NoSuchBucket", f"Bucket {bucket} does not exist")
        
        # Calculate ETag (MD5 hash)
        etag = hashlib.md5(body).hexdigest()
        
        object_key = f"{bucket}/{key}"
        self.objects[object_key] = {
            "bucket": bucket,
            "key": key,
            "body": body,
            "etag": etag,
            "size": len(body),
            "last_modified": datetime.now(timezone.utc),
            "content_type": kwargs.get("ContentType", "binary/octet-stream"),
            "metadata": kwargs.get("Metadata", {}),
            "storage_class": kwargs.get("StorageClass", "STANDARD")
        }
        
        return {
            "ETag": f'"{etag}"',
            "VersionId": f"mock-version-{hash(object_key)}"
        }
    
    async def get_object(self, bucket: str, key: str, **kwargs):
        """Mock object download"""
        self.log_call("get_object", bucket=bucket, key=key)
        
        object_key = f"{bucket}/{key}"
        if object_key not in self.objects:
            raise MockS3Error("NoSuchKey", f"Key {key} does not exist in bucket {bucket}")
        
        obj = self.objects[object_key]
        
        # Handle range requests
        body = obj["body"]
        if "Range" in kwargs:
            range_header = kwargs["Range"]
            # Simple range parsing (bytes=start-end)
            if range_header.startswith("bytes="):
                range_part = range_header[6:]
                if "-" in range_part:
                    start, end = range_part.split("-", 1)
                    start = int(start) if start else 0
                    end = int(end) if end else len(body) - 1
                    body = body[start:end + 1]
        
        return {
            "Body": body,
            "ContentLength": len(body),
            "ContentType": obj["content_type"],
            "ETag": f'"{obj["etag"]}"',
            "LastModified": obj["last_modified"],
            "Metadata": obj["metadata"],
            "StorageClass": obj["storage_class"]
        }
    
    async def delete_object(self, bucket: str, key: str):
        """Mock object deletion"""
        self.log_call("delete_object", bucket=bucket, key=key)
        
        object_key = f"{bucket}/{key}"
        if object_key in self.objects:
            del self.objects[object_key]
        
        return {
            "DeleteMarker": False,
            "VersionId": f"mock-version-{hash(object_key)}"
        }
    
    async def list_objects_v2(self, bucket: str, prefix: str = "", max_keys: int = 1000, **kwargs):
        """Mock object listing"""
        self.log_call("list_objects_v2", bucket=bucket, prefix=prefix)
        
        if bucket not in self.buckets:
            raise MockS3Error("NoSuchBucket", f"Bucket {bucket} does not exist")
        
        # Filter objects by bucket and prefix
        matching_objects = []
        for object_key, obj in self.objects.items():
            if (obj["bucket"] == bucket and 
                obj["key"].startswith(prefix) and 
                len(matching_objects) < max_keys):
                matching_objects.append({
                    "Key": obj["key"],
                    "Size": obj["size"],
                    "ETag": f'"{obj["etag"]}"',
                    "LastModified": obj["last_modified"],
                    "StorageClass": obj["storage_class"]
                })
        
        return {
            "Contents": matching_objects,
            "KeyCount": len(matching_objects),
            "IsTruncated": False,
            "Name": bucket,
            "Prefix": prefix,
            "MaxKeys": max_keys
        }
    
    async def head_object(self, bucket: str, key: str):
        """Mock object metadata retrieval"""
        self.log_call("head_object", bucket=bucket, key=key)
        
        object_key = f"{bucket}/{key}"
        if object_key not in self.objects:
            raise MockS3Error("NoSuchKey", f"Key {key} does not exist in bucket {bucket}")
        
        obj = self.objects[object_key]
        
        return {
            "ContentLength": obj["size"],
            "ContentType": obj["content_type"],
            "ETag": f'"{obj["etag"]}"',
            "LastModified": obj["last_modified"],
            "Metadata": obj["metadata"],
            "StorageClass": obj["storage_class"]
        }
    
    async def copy_object(self, copy_source: Dict[str, str], bucket: str, key: str, **kwargs):
        """Mock object copying"""
        source_bucket = copy_source["Bucket"]
        source_key = copy_source["Key"]
        
        self.log_call("copy_object", 
                     source_bucket=source_bucket, source_key=source_key,
                     dest_bucket=bucket, dest_key=key)
        
        source_object_key = f"{source_bucket}/{source_key}"
        if source_object_key not in self.objects:
            raise MockS3Error("NoSuchKey", f"Source key {source_key} does not exist")
        
        source_obj = self.objects[source_object_key]
        
        # Copy the object
        return await self.put_object(
            bucket=bucket,
            key=key,
            body=source_obj["body"],
            ContentType=source_obj["content_type"],
            Metadata=source_obj["metadata"],
            **kwargs
        )
    
    async def generate_presigned_url(self, operation: str, params: Dict[str, str], 
                                   expires_in: int = 3600):
        """Mock presigned URL generation"""
        self.log_call("generate_presigned_url", operation=operation, params=params)
        
        bucket = params.get("Bucket", "")
        key = params.get("Key", "")
        
        # Generate a mock presigned URL
        base_url = f"https://{bucket}.s3.amazonaws.com/{key}"
        mock_signature = hashlib.md5(f"{operation}{bucket}{key}{expires_in}".encode()).hexdigest()[:16]
        
        return f"{base_url}?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Signature={mock_signature}&X-Amz-Expires={expires_in}"


class MockS3Error(Exception):
    """Mock S3 errors"""
    
    def __init__(self, error_code: str, message: str, status_code: int = 400):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        super().__init__(f"{error_code}: {message}")


class MockS3NoSuchKeyError(MockS3Error):
    """Mock NoSuchKey error"""
    
    def __init__(self, key: str, bucket: str):
        super().__init__("NoSuchKey", f"The specified key '{key}' does not exist in bucket '{bucket}'", 404)


class MockS3BucketNotFoundError(MockS3Error):
    """Mock NoSuchBucket error"""
    
    def __init__(self, bucket: str):
        super().__init__("NoSuchBucket", f"The specified bucket '{bucket}' does not exist", 404)


class MockS3AccessDeniedError(MockS3Error):
    """Mock AccessDenied error"""
    
    def __init__(self, message: str = "Access Denied"):
        super().__init__("AccessDenied", message, 403)


def create_mock_s3_client() -> MockS3Client:
    """Factory function to create mock S3 client"""
    return MockS3Client()


def mock_s3_successful():
    """Mock successful S3 operations"""
    return create_mock_s3_client()


def mock_s3_access_denied():
    """Mock S3 client that raises access denied errors"""
    async def access_denied_operation(*args, **kwargs):
        raise MockS3AccessDeniedError()
    
    client = create_mock_s3_client()
    # Override common operations to raise access denied
    client.put_object = access_denied_operation
    client.get_object = access_denied_operation
    client.delete_object = access_denied_operation
    return client


def mock_s3_network_error():
    """Mock S3 client that simulates network errors"""
    async def network_error_operation(*args, **kwargs):
        raise MockS3Error("NetworkError", "Network connection failed", 500)
    
    client = create_mock_s3_client()
    client.put_object = network_error_operation
    client.get_object = network_error_operation
    return client


# Helper functions for creating test data
def create_test_file_content(size_kb: int = 1) -> bytes:
    """Create test file content of specified size"""
    content = b"Test file content. " * (size_kb * 1024 // 18)
    return content[:size_kb * 1024]


def create_test_image_content() -> bytes:
    """Create minimal PNG image content for testing"""
    # Minimal PNG header and data
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'


def create_test_document_content() -> bytes:
    """Create test document content"""
    return b"""# Test Document

This is a test document for S3 mock testing.

## Features
- File upload
- File download 
- File management
- Metadata handling

The content is used to test various S3 operations in the ActiveLog system.
"""