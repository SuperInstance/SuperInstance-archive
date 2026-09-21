"""
Cloud provider integration for data export uploads
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import aiohttp

# Google Drive
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# Dropbox
try:
    import dropbox
    from dropbox.exceptions import ApiError, AuthError
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

# AWS S3
try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class UploadResult:
    """Result of file upload to cloud provider"""
    success: bool
    provider: str
    file_id: Optional[str] = None
    path: Optional[str] = None
    share_url: Optional[str] = None
    size: Optional[int] = None
    error: Optional[str] = None
    upload_time_seconds: Optional[float] = None

class CloudProvider(ABC):
    """Abstract base class for cloud providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.initialized = False
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the cloud provider"""
        pass
    
    @abstractmethod
    async def upload_file(self, local_path: str, remote_path: str, 
                         user_id: str, **kwargs) -> UploadResult:
        """Upload file to cloud provider"""
        pass
    
    @abstractmethod
    async def create_folder(self, folder_path: str, user_id: str) -> bool:
        """Create folder in cloud provider"""
        pass
    
    @abstractmethod
    async def get_share_link(self, file_id: str, user_id: str) -> Optional[str]:
        """Get shareable link for uploaded file"""
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from cloud provider"""
        pass
    
    @abstractmethod
    def get_storage_info(self, user_id: str) -> Dict[str, Any]:
        """Get storage information"""
        pass

class GoogleDriveProvider(CloudProvider):
    """Google Drive integration"""
    
    def __init__(self):
        super().__init__("google_drive")
        self.service = None
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
    
    async def initialize(self) -> bool:
        """Initialize Google Drive client"""
        
        if not GOOGLE_AVAILABLE:
            logger.error("Google Drive libraries not available")
            return False
        
        try:
            # Check if we have credentials
            if not settings.cloud.google_credentials_file:
                logger.error("Google credentials file not configured")
                return False
            
            if not os.path.exists(settings.cloud.google_credentials_file):
                logger.error(f"Google credentials file not found: {settings.cloud.google_credentials_file}")
                return False
            
            # Load credentials
            creds = None
            
            # Try to load existing credentials
            token_file = settings.cloud.google_credentials_file.replace('.json', '_token.json')
            
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, self.scopes)
            
            # If there are no (valid) credentials available, authenticate
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        settings.cloud.google_credentials_file, self.scopes
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save the credentials for the next run
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=creds)
            self.initialized = True
            
            logger.info("Google Drive provider initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive: {e}")
            return False
    
    async def upload_file(self, local_path: str, remote_path: str,
                         user_id: str, **kwargs) -> UploadResult:
        """Upload file to Google Drive"""
        
        if not self.initialized:
            return UploadResult(success=False, provider=self.name, error="Provider not initialized")
        
        start_time = datetime.utcnow()
        
        try:
            # Prepare file metadata
            file_name = os.path.basename(remote_path)
            folder_path = os.path.dirname(remote_path)
            
            file_metadata = {
                'name': file_name,
                'description': f'ActiveLog export for user {user_id}'
            }
            
            # Create folder if needed
            if folder_path and folder_path != '.':
                folder_id = await self._ensure_folder_exists(folder_path)
                if folder_id:
                    file_metadata['parents'] = [folder_id]
            
            # Create media upload
            media = MediaFileUpload(local_path, resumable=True)
            
            # Upload file
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,size,webViewLink'
            ).execute()
            
            upload_time = (datetime.utcnow() - start_time).total_seconds()
            file_size = int(file.get('size', 0))
            
            logger.info(f"Uploaded {file_name} to Google Drive: {file['id']}")
            
            return UploadResult(
                success=True,
                provider=self.name,
                file_id=file['id'],
                path=remote_path,
                share_url=file.get('webViewLink'),
                size=file_size,
                upload_time_seconds=upload_time
            )
            
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            return UploadResult(
                success=False,
                provider=self.name,
                error=str(e)
            )
    
    async def _ensure_folder_exists(self, folder_path: str) -> Optional[str]:
        """Ensure folder exists and return folder ID"""
        
        try:
            # Split path into components
            path_parts = folder_path.strip('/').split('/')
            parent_id = 'root'
            
            for folder_name in path_parts:
                if not folder_name:
                    continue
                
                # Check if folder exists
                query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
                
                results = self.service.files().list(
                    q=query,
                    fields='files(id, name)'
                ).execute()
                
                folders = results.get('files', [])
                
                if folders:
                    # Folder exists
                    parent_id = folders[0]['id']
                else:
                    # Create folder
                    folder_metadata = {
                        'name': folder_name,
                        'parents': [parent_id],
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    
                    folder = self.service.files().create(
                        body=folder_metadata,
                        fields='id'
                    ).execute()
                    
                    parent_id = folder['id']
            
            return parent_id
            
        except Exception as e:
            logger.error(f"Failed to create folder {folder_path}: {e}")
            return None
    
    async def create_folder(self, folder_path: str, user_id: str) -> bool:
        """Create folder in Google Drive"""
        folder_id = await self._ensure_folder_exists(folder_path)
        return folder_id is not None
    
    async def get_share_link(self, file_id: str, user_id: str) -> Optional[str]:
        """Get shareable link for file"""
        
        try:
            # Make file publicly readable
            permission = {
                'role': 'reader',
                'type': 'anyone'
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            # Get file info with webViewLink
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file.get('webViewLink')
            
        except Exception as e:
            logger.error(f"Failed to get share link: {e}")
            return None
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from Google Drive"""
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    def get_storage_info(self, user_id: str) -> Dict[str, Any]:
        """Get Google Drive storage information"""
        
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            
            return {
                'provider': self.name,
                'total_bytes': int(quota.get('limit', 0)),
                'used_bytes': int(quota.get('usage', 0)),
                'available_bytes': int(quota.get('limit', 0)) - int(quota.get('usage', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {'provider': self.name, 'error': str(e)}

class DropboxProvider(CloudProvider):
    """Dropbox integration"""
    
    def __init__(self):
        super().__init__("dropbox")
        self.client = None
    
    async def initialize(self) -> bool:
        """Initialize Dropbox client"""
        
        if not DROPBOX_AVAILABLE:
            logger.error("Dropbox libraries not available")
            return False
        
        try:
            if not settings.cloud.dropbox_access_token:
                logger.error("Dropbox access token not configured")
                return False
            
            self.client = dropbox.Dropbox(settings.cloud.dropbox_access_token)
            
            # Test connection
            self.client.users_get_current_account()
            
            self.initialized = True
            logger.info("Dropbox provider initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Dropbox: {e}")
            return False
    
    async def upload_file(self, local_path: str, remote_path: str,
                         user_id: str, **kwargs) -> UploadResult:
        """Upload file to Dropbox"""
        
        if not self.initialized:
            return UploadResult(success=False, provider=self.name, error="Provider not initialized")
        
        start_time = datetime.utcnow()
        
        try:
            # Ensure remote path starts with /
            if not remote_path.startswith('/'):
                remote_path = '/' + remote_path
            
            file_size = os.path.getsize(local_path)
            
            # Use different upload methods based on file size
            if file_size <= 150 * 1024 * 1024:  # 150MB - use simple upload
                with open(local_path, 'rb') as f:
                    file_data = f.read()
                
                result = self.client.files_upload(
                    file_data,
                    remote_path,
                    mode=dropbox.files.WriteMode.overwrite,
                    autorename=True
                )
            else:
                # Use upload session for large files
                result = await self._upload_large_file(local_path, remote_path)
            
            upload_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Uploaded {os.path.basename(local_path)} to Dropbox: {result.id}")
            
            return UploadResult(
                success=True,
                provider=self.name,
                file_id=result.id,
                path=result.path_display,
                size=result.size,
                upload_time_seconds=upload_time
            )
            
        except Exception as e:
            logger.error(f"Dropbox upload failed: {e}")
            return UploadResult(
                success=False,
                provider=self.name,
                error=str(e)
            )
    
    async def _upload_large_file(self, local_path: str, remote_path: str):
        """Upload large file using upload session"""
        
        CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks
        
        with open(local_path, 'rb') as f:
            file_size = os.path.getsize(local_path)
            
            if file_size <= CHUNK_SIZE:
                return self.client.files_upload(
                    f.read(),
                    remote_path,
                    mode=dropbox.files.WriteMode.overwrite
                )
            
            # Start upload session
            session_start_result = self.client.files_upload_session_start(
                f.read(CHUNK_SIZE)
            )
            cursor = dropbox.files.UploadSessionCursor(
                session_id=session_start_result.session_id,
                offset=f.tell()
            )
            
            # Upload remaining chunks
            while f.tell() < file_size:
                if (file_size - f.tell()) <= CHUNK_SIZE:
                    # Final chunk
                    return self.client.files_upload_session_finish(
                        f.read(CHUNK_SIZE),
                        cursor,
                        dropbox.files.CommitInfo(path=remote_path)
                    )
                else:
                    # Continue session
                    self.client.files_upload_session_append_v2(
                        f.read(CHUNK_SIZE),
                        cursor
                    )
                    cursor.offset = f.tell()
    
    async def create_folder(self, folder_path: str, user_id: str) -> bool:
        """Create folder in Dropbox"""
        
        try:
            if not folder_path.startswith('/'):
                folder_path = '/' + folder_path
            
            self.client.files_create_folder_v2(folder_path)
            return True
        except dropbox.exceptions.ApiError as e:
            if e.error.is_path() and e.error.get_path().is_conflict():
                # Folder already exists
                return True
            logger.error(f"Failed to create folder {folder_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to create folder {folder_path}: {e}")
            return False
    
    async def get_share_link(self, file_id: str, user_id: str) -> Optional[str]:
        """Get shareable link for file"""
        
        try:
            # Create shared link
            link_result = self.client.sharing_create_shared_link_with_settings(
                file_id,
                settings=dropbox.sharing.SharedLinkSettings(
                    requested_visibility=dropbox.sharing.RequestedVisibility.public
                )
            )
            return link_result.url
        except Exception as e:
            logger.error(f"Failed to create share link: {e}")
            return None
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from Dropbox"""
        
        try:
            self.client.files_delete_v2(file_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False
    
    def get_storage_info(self, user_id: str) -> Dict[str, Any]:
        """Get Dropbox storage information"""
        
        try:
            space_usage = self.client.users_get_space_usage()
            
            return {
                'provider': self.name,
                'total_bytes': space_usage.allocation.get_individual().allocated,
                'used_bytes': space_usage.used,
                'available_bytes': space_usage.allocation.get_individual().allocated - space_usage.used
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {'provider': self.name, 'error': str(e)}

class AWSS3Provider(CloudProvider):
    """AWS S3 integration"""
    
    def __init__(self):
        super().__init__("aws_s3")
        self.s3_client = None
        self.bucket = settings.cloud.aws_bucket
    
    async def initialize(self) -> bool:
        """Initialize AWS S3 client"""
        
        if not AWS_AVAILABLE:
            logger.error("AWS libraries not available")
            return False
        
        try:
            if not all([settings.cloud.aws_access_key_id, 
                       settings.cloud.aws_secret_access_key, 
                       settings.cloud.aws_bucket]):
                logger.error("AWS credentials or bucket not configured")
                return False
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.cloud.aws_access_key_id,
                aws_secret_access_key=settings.cloud.aws_secret_access_key,
                region_name=settings.cloud.aws_region
            )
            
            # Test connection by checking bucket
            self.s3_client.head_bucket(Bucket=self.bucket)
            
            self.initialized = True
            logger.info("AWS S3 provider initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AWS S3: {e}")
            return False
    
    async def upload_file(self, local_path: str, remote_path: str,
                         user_id: str, **kwargs) -> UploadResult:
        """Upload file to AWS S3"""
        
        if not self.initialized:
            return UploadResult(success=False, provider=self.name, error="Provider not initialized")
        
        start_time = datetime.utcnow()
        
        try:
            # Add user prefix to path
            s3_key = f"exports/{user_id}/{remote_path}"
            
            # Upload file
            self.s3_client.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'user_id': user_id,
                        'upload_time': datetime.utcnow().isoformat()
                    }
                }
            )
            
            upload_time = (datetime.utcnow() - start_time).total_seconds()
            file_size = os.path.getsize(local_path)
            
            # Generate presigned URL for download
            share_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=3600 * 24 * 7  # 7 days
            )
            
            logger.info(f"Uploaded {os.path.basename(local_path)} to S3: {s3_key}")
            
            return UploadResult(
                success=True,
                provider=self.name,
                file_id=s3_key,
                path=s3_key,
                share_url=share_url,
                size=file_size,
                upload_time_seconds=upload_time
            )
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return UploadResult(
                success=False,
                provider=self.name,
                error=str(e)
            )
    
    async def create_folder(self, folder_path: str, user_id: str) -> bool:
        """Create folder in S3 (creates prefix)"""
        
        try:
            # S3 doesn't have real folders, but we can create a placeholder object
            s3_key = f"exports/{user_id}/{folder_path.rstrip('/')}/"
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=b'',
                ServerSideEncryption='AES256'
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to create S3 folder {folder_path}: {e}")
            return False
    
    async def get_share_link(self, file_id: str, user_id: str) -> Optional[str]:
        """Get presigned URL for S3 object"""
        
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_id},
                ExpiresIn=3600 * 24 * 7  # 7 days
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from S3"""
        
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_id)
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 object {file_id}: {e}")
            return False
    
    def get_storage_info(self, user_id: str) -> Dict[str, Any]:
        """Get S3 bucket information"""
        
        try:
            # Get bucket size (expensive operation - consider caching)
            total_size = 0
            user_prefix = f"exports/{user_id}/"
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket, Prefix=user_prefix):
                for obj in page.get('Contents', []):
                    total_size += obj['Size']
            
            return {
                'provider': self.name,
                'used_bytes': total_size,
                'bucket': self.bucket,
                'region': settings.cloud.aws_region
            }
        except Exception as e:
            logger.error(f"Failed to get S3 storage info: {e}")
            return {'provider': self.name, 'error': str(e)}

class CloudProviderManager:
    """Manage multiple cloud providers"""
    
    def __init__(self):
        self.providers: Dict[str, CloudProvider] = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize all configured cloud providers"""
        
        if self.initialized:
            return
        
        # Initialize Google Drive
        if settings.is_cloud_provider_configured("google_drive"):
            provider = GoogleDriveProvider()
            if await provider.initialize():
                self.providers["google_drive"] = provider
        
        # Initialize Dropbox
        if settings.is_cloud_provider_configured("dropbox"):
            provider = DropboxProvider()
            if await provider.initialize():
                self.providers["dropbox"] = provider
        
        # Initialize AWS S3
        if settings.is_cloud_provider_configured("aws_s3"):
            provider = AWSS3Provider()
            if await provider.initialize():
                self.providers["aws_s3"] = provider
        
        self.initialized = True
        logger.info(f"Initialized {len(self.providers)} cloud providers: {list(self.providers.keys())}")
    
    async def upload_file(self, provider: str, local_path: str, 
                         remote_path: str, user_id: str, **kwargs) -> UploadResult:
        """Upload file to specified cloud provider"""
        
        if provider not in self.providers:
            return UploadResult(
                success=False,
                provider=provider,
                error=f"Provider {provider} not available"
            )
        
        return await self.providers[provider].upload_file(
            local_path, remote_path, user_id, **kwargs
        )
    
    async def upload_to_all_providers(self, local_path: str, remote_path: str,
                                    user_id: str, **kwargs) -> Dict[str, UploadResult]:
        """Upload file to all configured providers"""
        
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                result = await provider.upload_file(local_path, remote_path, user_id, **kwargs)
                results[provider_name] = result
            except Exception as e:
                results[provider_name] = UploadResult(
                    success=False,
                    provider=provider_name,
                    error=str(e)
                )
        
        return results
    
    def get_available_providers(self) -> List[str]:
        """Get list of available cloud providers"""
        return list(self.providers.keys())
    
    def get_provider_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all providers"""
        
        info = {}
        
        for name, provider in self.providers.items():
            info[name] = {
                'name': provider.name,
                'initialized': provider.initialized,
                'available': True
            }
        
        # Add unavailable providers
        unavailable = []
        if not GOOGLE_AVAILABLE:
            unavailable.append('google_drive')
        if not DROPBOX_AVAILABLE:
            unavailable.append('dropbox')
        if not AWS_AVAILABLE:
            unavailable.append('aws_s3')
        
        for provider in unavailable:
            if provider not in info:
                info[provider] = {
                    'name': provider,
                    'initialized': False,
                    'available': False,
                    'error': 'Required libraries not installed'
                }
        
        return info
    
    async def cleanup(self):
        """Clean up cloud provider connections"""
        
        for provider in self.providers.values():
            try:
                if hasattr(provider, 'cleanup'):
                    await provider.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up provider {provider.name}: {e}")
        
        self.providers.clear()
        self.initialized = False