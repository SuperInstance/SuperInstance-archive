"""
Platform Data Import Tools for ActiveLog
Comprehensive import utilities for Google Photos, Dropbox, iCloud, and other platforms.
"""

import os
import json
import asyncio
import aiohttp
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from urllib.parse import urlencode, urlparse
import tempfile
import shutil
import zipfile
import time
from PIL import Image
from PIL.ExifTags import TAGS
import requests


@dataclass
class ImportedFile:
    """Represents an imported file with metadata."""
    original_path: str
    filename: str
    size: int
    mime_type: str
    checksum: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    metadata: Dict[str, Any]
    source_platform: str
    source_id: str
    import_status: str = 'pending'
    local_path: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ImportProgress:
    """Tracks import progress."""
    total_files: int
    processed_files: int
    successful_imports: int
    failed_imports: int
    bytes_processed: int
    start_time: datetime
    current_file: Optional[str] = None


class PlatformImporter:
    """Base class for platform importers."""
    
    def __init__(self, output_dir: str, api_credentials: Dict[str, str]):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.credentials = api_credentials
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Import configuration
        self.config = {
            'batch_size': 100,
            'concurrent_downloads': 5,
            'retry_attempts': 3,
            'timeout_seconds': 300,
            'supported_types': ['image', 'video', 'document', 'audio'],
            'max_file_size': 5 * 1024 * 1024 * 1024,  # 5GB
            'preserve_timestamps': True,
            'extract_metadata': True
        }
        
        self.session = None
        self.import_stats = ImportProgress(
            total_files=0,
            processed_files=0,
            successful_imports=0,
            failed_imports=0,
            bytes_processed=0,
            start_time=datetime.now()
        )
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def import_data(self) -> ImportProgress:
        """Main import method - to be overridden by subclasses."""
        raise NotImplementedError
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _extract_metadata(self, file_path: str, mime_type: str) -> Dict[str, Any]:
        """Extract metadata from file."""
        metadata = {}
        
        try:
            if mime_type.startswith('image/'):
                metadata.update(self._extract_image_metadata(file_path))
            elif mime_type.startswith('video/'):
                metadata.update(self._extract_video_metadata(file_path))
        except Exception as e:
            self.logger.warning(f"Failed to extract metadata from {file_path}: {e}")
        
        return metadata
    
    def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract EXIF and other metadata from images."""
        metadata = {}
        
        try:
            with Image.open(file_path) as image:
                metadata['image'] = {
                    'width': image.width,
                    'height': image.height,
                    'format': image.format,
                    'mode': image.mode
                }
                
                # Extract EXIF data
                if hasattr(image, '_getexif') and image._getexif():
                    exif_data = {}
                    for tag_id, value in image._getexif().items():
                        tag = TAGS.get(tag_id, tag_id)
                        if isinstance(value, str) and len(value) < 1000:  # Avoid huge strings
                            exif_data[tag] = value
                        elif isinstance(value, (int, float)):
                            exif_data[tag] = value
                    
                    metadata['exif'] = exif_data
        except Exception as e:
            self.logger.debug(f"Could not extract image metadata: {e}")
        
        return metadata
    
    def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from video files."""
        metadata = {}
        
        try:
            # This would typically use ffmpeg or similar
            # For now, just get basic file info
            stat = os.stat(file_path)
            metadata['video'] = {
                'size_bytes': stat.st_size,
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
        except Exception as e:
            self.logger.debug(f"Could not extract video metadata: {e}")
        
        return metadata
    
    async def _download_file(self, url: str, destination: str, headers: Dict[str, str] = None) -> bool:
        """Download file from URL."""
        try:
            async with self.session.get(url, headers=headers or {}) as response:
                if response.status == 200:
                    with open(destination, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    return True
                else:
                    self.logger.error(f"Download failed with status {response.status}: {url}")
                    return False
        except Exception as e:
            self.logger.error(f"Download error for {url}: {e}")
            return False
    
    def _save_import_manifest(self, files: List[ImportedFile]):
        """Save import manifest for tracking."""
        manifest_path = self.output_dir / "import_manifest.json"
        
        manifest_data = {
            'import_date': datetime.now().isoformat(),
            'platform': self.__class__.__name__,
            'total_files': len(files),
            'successful_imports': sum(1 for f in files if f.import_status == 'success'),
            'failed_imports': sum(1 for f in files if f.import_status == 'failed'),
            'statistics': asdict(self.import_stats),
            'files': [asdict(f) for f in files]
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f, indent=2, default=str)
        
        self.logger.info(f"Import manifest saved to {manifest_path}")


class GooglePhotosImporter(PlatformImporter):
    """Importer for Google Photos using Google Photos API."""
    
    def __init__(self, output_dir: str, api_credentials: Dict[str, str]):
        super().__init__(output_dir, api_credentials)
        self.api_base = "https://photoslibrary.googleapis.com/v1"
    
    async def import_data(self) -> ImportProgress:
        """Import photos from Google Photos."""
        self.logger.info("Starting Google Photos import...")
        
        # Get access token
        access_token = await self._get_access_token()
        if not access_token:
            self.logger.error("Failed to get access token")
            return self.import_stats
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Get media items
        media_items = await self._get_all_media_items(headers)
        self.import_stats.total_files = len(media_items)
        
        # Download media items
        imported_files = []
        semaphore = asyncio.Semaphore(self.config['concurrent_downloads'])
        
        tasks = [
            self._download_media_item(item, headers, semaphore)
            for item in media_items
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, ImportedFile):
                imported_files.append(result)
                if result.import_status == 'success':
                    self.import_stats.successful_imports += 1
                else:
                    self.import_stats.failed_imports += 1
            self.import_stats.processed_files += 1
        
        # Save manifest
        self._save_import_manifest(imported_files)
        
        self.logger.info(f"Google Photos import completed: {self.import_stats.successful_imports}/{self.import_stats.total_files} files")
        return self.import_stats
    
    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for Google Photos API."""
        # This would typically use OAuth2 flow
        # For demo purposes, assume token is provided in credentials
        return self.credentials.get('access_token')
    
    async def _get_all_media_items(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Retrieve all media items from Google Photos."""
        media_items = []
        page_token = None
        
        while True:
            params = {'pageSize': 100}
            if page_token:
                params['pageToken'] = page_token
            
            async with self.session.get(f"{self.api_base}/mediaItems", headers=headers, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to get media items: {response.status}")
                    break
                
                data = await response.json()
                media_items.extend(data.get('mediaItems', []))
                
                page_token = data.get('nextPageToken')
                if not page_token:
                    break
        
        return media_items
    
    async def _download_media_item(self, item: Dict[str, Any], headers: Dict[str, str], semaphore: asyncio.Semaphore) -> ImportedFile:
        """Download a single media item."""
        async with semaphore:
            imported_file = ImportedFile(
                original_path=item.get('productUrl', ''),
                filename=item.get('filename', 'unknown'),
                size=0,
                mime_type=item.get('mimeType', ''),
                checksum='',
                created_date=datetime.fromisoformat(item.get('mediaMetadata', {}).get('creationTime', '').rstrip('Z')),
                modified_date=None,
                metadata={},
                source_platform='Google Photos',
                source_id=item.get('id', ''),
                import_status='pending'
            )
            
            try:
                # Construct download URL
                base_url = item.get('baseUrl')
                if not base_url:
                    raise ValueError("No base URL available")
                
                download_url = f"{base_url}=d"  # Add download parameter
                
                # Download file
                local_filename = f"google_photos_{item['id']}_{item.get('filename', 'file')}"
                local_path = self.output_dir / local_filename
                
                success = await self._download_file(download_url, str(local_path), headers)
                
                if success:
                    # Update file info
                    stat = os.stat(local_path)
                    imported_file.size = stat.st_size
                    imported_file.local_path = str(local_path)
                    imported_file.checksum = self._calculate_checksum(str(local_path))
                    
                    if self.config['extract_metadata']:
                        imported_file.metadata = self._extract_metadata(str(local_path), imported_file.mime_type)
                    
                    imported_file.import_status = 'success'
                    self.import_stats.bytes_processed += imported_file.size
                else:
                    imported_file.import_status = 'failed'
                    imported_file.error_message = 'Download failed'
            
            except Exception as e:
                imported_file.import_status = 'failed'
                imported_file.error_message = str(e)
                self.logger.error(f"Failed to download {item.get('filename', 'unknown')}: {e}")
            
            return imported_file


class DropboxImporter(PlatformImporter):
    """Importer for Dropbox using Dropbox API."""
    
    def __init__(self, output_dir: str, api_credentials: Dict[str, str]):
        super().__init__(output_dir, api_credentials)
        self.api_base = "https://api.dropboxapi.com/2"
        self.content_api_base = "https://content.dropboxapi.com/2"
    
    async def import_data(self) -> ImportProgress:
        """Import files from Dropbox."""
        self.logger.info("Starting Dropbox import...")
        
        access_token = self.credentials.get('access_token')
        if not access_token:
            self.logger.error("Dropbox access token required")
            return self.import_stats
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Get all files
        files = await self._list_all_files(headers)
        self.import_stats.total_files = len(files)
        
        # Download files
        imported_files = []
        semaphore = asyncio.Semaphore(self.config['concurrent_downloads'])
        
        tasks = [
            self._download_dropbox_file(file_info, headers, semaphore)
            for file_info in files
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, ImportedFile):
                imported_files.append(result)
                if result.import_status == 'success':
                    self.import_stats.successful_imports += 1
                else:
                    self.import_stats.failed_imports += 1
            self.import_stats.processed_files += 1
        
        # Save manifest
        self._save_import_manifest(imported_files)
        
        self.logger.info(f"Dropbox import completed: {self.import_stats.successful_imports}/{self.import_stats.total_files} files")
        return self.import_stats
    
    async def _list_all_files(self, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """List all files in Dropbox account."""
        files = []
        cursor = None
        
        while True:
            if cursor:
                # Continue listing
                payload = {'cursor': cursor}
                endpoint = '/files/list_folder/continue'
            else:
                # Start listing
                payload = {
                    'path': '',
                    'recursive': True,
                    'include_media_info': True,
                    'include_deleted': False
                }
                endpoint = '/files/list_folder'
            
            async with self.session.post(f"{self.api_base}{endpoint}", headers=headers, json=payload) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to list files: {response.status}")
                    break
                
                data = await response.json()
                
                # Filter for files (not folders)
                file_entries = [entry for entry in data.get('entries', []) if entry.get('.tag') == 'file']
                files.extend(file_entries)
                
                if data.get('has_more'):
                    cursor = data.get('cursor')
                else:
                    break
        
        return files
    
    async def _download_dropbox_file(self, file_info: Dict[str, Any], headers: Dict[str, str], semaphore: asyncio.Semaphore) -> ImportedFile:
        """Download a single file from Dropbox."""
        async with semaphore:
            imported_file = ImportedFile(
                original_path=file_info.get('path_display', ''),
                filename=file_info.get('name', ''),
                size=file_info.get('size', 0),
                mime_type=mimetypes.guess_type(file_info.get('name', ''))[0] or 'application/octet-stream',
                checksum=file_info.get('content_hash', ''),
                created_date=None,
                modified_date=datetime.fromisoformat(file_info.get('client_modified', '').rstrip('Z')),
                metadata={},
                source_platform='Dropbox',
                source_id=file_info.get('id', ''),
                import_status='pending'
            )
            
            try:
                # Download file
                download_headers = {
                    'Authorization': headers['Authorization'],
                    'Dropbox-API-Arg': json.dumps({'path': file_info['path_display']})
                }
                
                local_filename = f"dropbox_{file_info['name']}"
                local_path = self.output_dir / local_filename
                
                async with self.session.post(f"{self.content_api_base}/files/download", headers=download_headers) as response:
                    if response.status == 200:
                        with open(local_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        imported_file.local_path = str(local_path)
                        imported_file.checksum = self._calculate_checksum(str(local_path))
                        
                        if self.config['extract_metadata']:
                            imported_file.metadata = self._extract_metadata(str(local_path), imported_file.mime_type)
                        
                        imported_file.import_status = 'success'
                        self.import_stats.bytes_processed += imported_file.size
                    else:
                        imported_file.import_status = 'failed'
                        imported_file.error_message = f'Download failed with status {response.status}'
            
            except Exception as e:
                imported_file.import_status = 'failed'
                imported_file.error_message = str(e)
                self.logger.error(f"Failed to download {file_info.get('name', 'unknown')}: {e}")
            
            return imported_file


class iCloudImporter(PlatformImporter):
    """Importer for iCloud (limited API access - uses export files)."""
    
    def __init__(self, output_dir: str, api_credentials: Dict[str, str]):
        super().__init__(output_dir, api_credentials)
        # iCloud doesn't have a public API, so this importer works with exported archives
    
    async def import_data(self, archive_path: str = None) -> ImportProgress:
        """Import from iCloud export archive."""
        self.logger.info("Starting iCloud import from archive...")
        
        if not archive_path:
            archive_path = self.credentials.get('archive_path')
        
        if not archive_path or not os.path.exists(archive_path):
            self.logger.error("iCloud archive path required and must exist")
            return self.import_stats
        
        # Extract and process archive
        imported_files = await self._process_icloud_archive(archive_path)
        
        self.import_stats.total_files = len(imported_files)
        self.import_stats.successful_imports = sum(1 for f in imported_files if f.import_status == 'success')
        self.import_stats.failed_imports = sum(1 for f in imported_files if f.import_status == 'failed')
        self.import_stats.processed_files = len(imported_files)
        
        # Save manifest
        self._save_import_manifest(imported_files)
        
        self.logger.info(f"iCloud import completed: {self.import_stats.successful_imports}/{self.import_stats.total_files} files")
        return self.import_stats
    
    async def _process_icloud_archive(self, archive_path: str) -> List[ImportedFile]:
        """Process iCloud export archive (ZIP file)."""
        imported_files = []
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as archive:
                file_list = archive.namelist()
                
                for file_path in file_list:
                    if file_path.endswith('/'):  # Skip directories
                        continue
                    
                    imported_file = ImportedFile(
                        original_path=file_path,
                        filename=os.path.basename(file_path),
                        size=0,
                        mime_type=mimetypes.guess_type(file_path)[0] or 'application/octet-stream',
                        checksum='',
                        created_date=None,
                        modified_date=None,
                        metadata={},
                        source_platform='iCloud',
                        source_id=file_path,
                        import_status='pending'
                    )
                    
                    try:
                        # Extract file
                        local_filename = f"icloud_{os.path.basename(file_path)}"
                        local_path = self.output_dir / local_filename
                        
                        with archive.open(file_path) as source:
                            with open(local_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                        
                        # Update file info
                        stat = os.stat(local_path)
                        imported_file.size = stat.st_size
                        imported_file.local_path = str(local_path)
                        imported_file.checksum = self._calculate_checksum(str(local_path))
                        imported_file.modified_date = datetime.fromtimestamp(stat.st_mtime)
                        
                        if self.config['extract_metadata']:
                            imported_file.metadata = self._extract_metadata(str(local_path), imported_file.mime_type)
                        
                        imported_file.import_status = 'success'
                        self.import_stats.bytes_processed += imported_file.size
                    
                    except Exception as e:
                        imported_file.import_status = 'failed'
                        imported_file.error_message = str(e)
                        self.logger.error(f"Failed to extract {file_path}: {e}")
                    
                    imported_files.append(imported_file)
        
        except Exception as e:
            self.logger.error(f"Failed to process archive {archive_path}: {e}")
        
        return imported_files


class GenericCloudImporter(PlatformImporter):
    """Generic importer for cloud storage services with WebDAV/HTTP APIs."""
    
    def __init__(self, output_dir: str, api_credentials: Dict[str, str]):
        super().__init__(output_dir, api_credentials)
        self.api_base = api_credentials.get('api_base', '')
    
    async def import_data(self) -> ImportProgress:
        """Import from generic cloud storage."""
        self.logger.info("Starting generic cloud import...")
        
        # Implementation would depend on specific API
        # This is a template for other cloud services
        
        return self.import_stats


async def run_platform_import(platform: str, output_dir: str, credentials: Dict[str, str], **kwargs) -> ImportProgress:
    """Run import for specified platform."""
    
    importers = {
        'google_photos': GooglePhotosImporter,
        'dropbox': DropboxImporter,
        'icloud': iCloudImporter,
        'generic': GenericCloudImporter
    }
    
    if platform not in importers:
        raise ValueError(f"Unsupported platform: {platform}")
    
    importer_class = importers[platform]
    
    async with importer_class(output_dir, credentials) as importer:
        progress = await importer.import_data(**kwargs)
        return progress


async def batch_import_multiple_platforms(import_configs: List[Dict[str, Any]]) -> Dict[str, ImportProgress]:
    """Import from multiple platforms concurrently."""
    
    results = {}
    tasks = []
    
    for config in import_configs:
        platform = config['platform']
        output_dir = config['output_dir']
        credentials = config['credentials']
        kwargs = config.get('kwargs', {})
        
        task = run_platform_import(platform, output_dir, credentials, **kwargs)
        tasks.append((platform, task))
    
    # Run imports concurrently
    for platform, task in tasks:
        try:
            progress = await task
            results[platform] = progress
        except Exception as e:
            logging.error(f"Import failed for {platform}: {e}")
            results[platform] = None
    
    return results


def create_import_report(results: Dict[str, ImportProgress]) -> str:
    """Generate import report."""
    
    report_lines = [
        "=" * 80,
        "PLATFORM DATA IMPORT REPORT",
        "=" * 80,
        f"Import Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]
    
    total_files = 0
    total_successful = 0
    total_failed = 0
    total_bytes = 0
    
    for platform, progress in results.items():
        if progress:
            report_lines.extend([
                f"PLATFORM: {platform.upper()}",
                f"  Total Files: {progress.total_files}",
                f"  Successful: {progress.successful_imports}",
                f"  Failed: {progress.failed_imports}",
                f"  Bytes Processed: {progress.bytes_processed:,}",
                f"  Duration: {datetime.now() - progress.start_time}",
                ""
            ])
            
            total_files += progress.total_files
            total_successful += progress.successful_imports
            total_failed += progress.failed_imports
            total_bytes += progress.bytes_processed
        else:
            report_lines.extend([
                f"PLATFORM: {platform.upper()}",
                "  Status: FAILED",
                ""
            ])
    
    report_lines.extend([
        "SUMMARY:",
        f"  Total Files: {total_files}",
        f"  Total Successful: {total_successful}",
        f"  Total Failed: {total_failed}",
        f"  Success Rate: {(total_successful / total_files * 100) if total_files > 0 else 0:.1f}%",
        f"  Total Data: {total_bytes / (1024**3):.2f} GB",
        "",
        "=" * 80
    ])
    
    return "\\n".join(report_lines)


def main():
    """Demo of platform importers."""
    
    async def demo():
        print("🔄 ActiveLog Platform Import Demo")
        print("=" * 50)
        
        # Demo configurations (would use real credentials in production)
        import_configs = [
            {
                'platform': 'google_photos',
                'output_dir': '/tmp/activelog_imports/google_photos',
                'credentials': {
                    'access_token': 'demo_token_google_photos'
                }
            },
            {
                'platform': 'dropbox',
                'output_dir': '/tmp/activelog_imports/dropbox',
                'credentials': {
                    'access_token': 'demo_token_dropbox'
                }
            },
            {
                'platform': 'icloud',
                'output_dir': '/tmp/activelog_imports/icloud',
                'credentials': {
                    'archive_path': '/tmp/demo_icloud_export.zip'
                }
            }
        ]
        
        print("Starting multi-platform import...")
        
        # Create demo archive for iCloud
        demo_archive_path = '/tmp/demo_icloud_export.zip'
        with zipfile.ZipFile(demo_archive_path, 'w') as zf:
            # Create demo files in the archive
            zf.writestr('Photos/IMG_001.jpg', b'fake_jpeg_data')
            zf.writestr('Photos/IMG_002.png', b'fake_png_data')
            zf.writestr('Documents/document.pdf', b'fake_pdf_data')
        
        # Run imports (will fail without real credentials, but shows structure)
        try:
            results = await batch_import_multiple_platforms(import_configs)
            
            # Generate report
            report = create_import_report(results)
            print(report)
            
            # Save report
            report_path = Path('/tmp/activelog_imports/import_report.txt')
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                f.write(report)
            
            print(f"\\nReport saved to: {report_path}")
            
        except Exception as e:
            print(f"Demo failed (expected with demo credentials): {e}")
        
        # Cleanup
        if os.path.exists(demo_archive_path):
            os.unlink(demo_archive_path)
        
        print("\\n✅ Platform import demo completed!")
    
    asyncio.run(demo())


if __name__ == "__main__":
    main()