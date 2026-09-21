"""
Batch Processor Service - Handles file processing in chunks
"""

import asyncio
import hashlib
import logging
import mimetypes
import shutil
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from core.config import settings
from .minio_service import MinIOService

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result of processing a file"""
    file_path: str
    success: bool
    error_message: Optional[str] = None
    file_hash: Optional[str] = None
    file_size: int = 0
    mime_type: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    thumbnails: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    duplicate_of: Optional[str] = None

@dataclass
class BatchResult:
    """Result of processing a batch of files"""
    batch_id: str
    files_processed: int
    files_succeeded: int
    files_failed: int
    processing_time: float
    results: List[ProcessingResult]
    timestamp: datetime = field(default_factory=datetime.now)

class BatchProcessor:
    """Processes batches of files with chunked reading and metadata extraction"""
    
    def __init__(self, report_service=None):
        self.report_service = report_service
        self.minio_service = MinIOService()
        
        # Processing state
        self.active_batches: Dict[str, asyncio.Task] = {}
        self.processed_hashes: Set[str] = set()
        self.hash_to_file: Dict[str, str] = {}
        
        # Statistics
        self.stats = {
            "batches_processed": 0,
            "files_processed": 0,
            "files_succeeded": 0,
            "files_failed": 0,
            "duplicates_found": 0,
            "total_size_processed": 0,
            "start_time": datetime.now(),
            "last_batch": None
        }
        
        # Ensure processing directories exist
        Path(settings.PROCESSING_PATH).mkdir(parents=True, exist_ok=True)
        Path(settings.COMPLETED_PATH).mkdir(parents=True, exist_ok=True)
        Path(settings.FAILED_PATH).mkdir(parents=True, exist_ok=True)
        
        logger.info("Batch processor initialized")
    
    async def process_batch(self, file_paths: List[str]) -> BatchResult:
        """Process a batch of files"""
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_batches)}"
        start_time = datetime.now()
        
        logger.info(f"Starting batch {batch_id} with {len(file_paths)} files")
        
        # Limit concurrent batches
        while len(self.active_batches) >= settings.MAX_CONCURRENT_JOBS:
            await asyncio.sleep(1)
        
        # Create processing task
        task = asyncio.create_task(self._process_batch_internal(batch_id, file_paths))
        self.active_batches[batch_id] = task
        
        try:
            result = await task
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            
            # Update statistics
            self.stats["batches_processed"] += 1
            self.stats["files_processed"] += result.files_processed
            self.stats["files_succeeded"] += result.files_succeeded
            self.stats["files_failed"] += result.files_failed
            self.stats["last_batch"] = datetime.now()
            
            logger.info(f"Completed batch {batch_id}: {result.files_succeeded}/{result.files_processed} succeeded")
            
            # Generate report if service available
            if self.report_service:
                await self.report_service.create_batch_report(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing batch {batch_id}: {e}")
            raise
        finally:
            # Cleanup
            if batch_id in self.active_batches:
                del self.active_batches[batch_id]
    
    async def _process_batch_internal(self, batch_id: str, file_paths: List[str]) -> BatchResult:
        """Internal batch processing implementation"""
        results = []
        
        # Process files concurrently with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(settings.WORKER_THREADS)
        
        async def process_single_file(file_path: str) -> ProcessingResult:
            async with semaphore:
                return await self._process_single_file(file_path)
        
        # Create tasks for all files
        tasks = [process_single_file(fp) for fp in file_paths]
        
        # Wait for all files to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and create proper results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing file {file_paths[i]}: {result}")
                processed_results.append(ProcessingResult(
                    file_path=file_paths[i],
                    success=False,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
        
        # Calculate batch statistics
        files_succeeded = sum(1 for r in processed_results if r.success)
        files_failed = len(processed_results) - files_succeeded
        
        return BatchResult(
            batch_id=batch_id,
            files_processed=len(processed_results),
            files_succeeded=files_succeeded,
            files_failed=files_failed,
            processing_time=0.0,  # Will be set by caller
            results=processed_results
        )
    
    async def _process_single_file(self, file_path: str) -> ProcessingResult:
        """Process a single file with chunked reading"""
        start_time = datetime.now()
        result = ProcessingResult(file_path=file_path, success=False)
        
        try:
            path = Path(file_path)
            
            # Validate file exists
            if not path.exists():
                result.error_message = "File does not exist"
                return result
            
            # Get file info
            stat = path.stat()
            result.file_size = stat.st_size
            result.mime_type = mimetypes.guess_type(str(path))[0]
            
            # Skip empty files
            if result.file_size == 0:
                result.error_message = "File is empty"
                return result
            
            # Skip files that are too large
            if result.file_size > settings.MAX_FILE_SIZE:
                result.error_message = f"File too large: {result.file_size} bytes"
                return result
            
            # Calculate file hash with chunked reading
            file_hash = await self._calculate_file_hash(path)
            result.file_hash = file_hash
            
            # Check for duplicates
            if file_hash in self.processed_hashes:
                result.duplicate_of = self.hash_to_file.get(file_hash)
                self.stats["duplicates_found"] += 1
                
                if settings.DUPLICATE_ACTION == "skip":
                    result.error_message = f"Duplicate file (hash: {file_hash[:16]}...)"
                    return result
            
            # Move file to processing directory
            processing_path = Path(settings.PROCESSING_PATH) / path.name
            shutil.move(str(path), str(processing_path))
            
            try:
                # Extract metadata based on file type
                metadata = await self._extract_metadata(processing_path)
                result.metadata = metadata
                
                # Generate thumbnails if applicable
                thumbnails = await self._generate_thumbnails(processing_path)
                result.thumbnails = thumbnails
                
                # Upload to MinIO with organization
                upload_result = await self.minio_service.upload_file(
                    str(processing_path), 
                    metadata
                )
                
                if upload_result["success"]:
                    result.metadata["minio_object"] = upload_result["object_name"]
                    result.metadata["minio_url"] = upload_result["url"]
                    
                    # Upload thumbnails if any
                    if thumbnails:
                        thumb_results = await self.minio_service.upload_thumbnails(
                            thumbnails, 
                            upload_result["object_name"]
                        )
                        result.metadata["thumbnail_objects"] = [
                            r["object_name"] for r in thumb_results if r["success"]
                        ]
                
                # Move to completed directory
                completed_path = Path(settings.COMPLETED_PATH) / path.name
                shutil.move(str(processing_path), str(completed_path))
                
                # Track processed file
                self.processed_hashes.add(file_hash)
                self.hash_to_file[file_hash] = str(completed_path)
                self.stats["total_size_processed"] += result.file_size
                
                result.success = True
                logger.debug(f"Successfully processed: {path.name}")
                
            except Exception as e:
                logger.error(f"Error processing file {path.name}: {e}")
                
                # Move to failed directory
                failed_path = Path(settings.FAILED_PATH) / path.name
                if processing_path.exists():
                    shutil.move(str(processing_path), str(failed_path))
                
                result.error_message = str(e)
                result.success = False
        
        except Exception as e:
            logger.error(f"Error in file processing pipeline for {file_path}: {e}")
            result.error_message = str(e)
            result.success = False
        
        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
        
        return result
    
    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate file hash using chunked reading"""
        hasher = hashlib.new(settings.HASH_ALGORITHM)
        
        def read_chunks():
            with open(file_path, 'rb') as f:
                while chunk := f.read(settings.CHUNK_SIZE):
                    hasher.update(chunk)
        
        # Run in thread pool to avoid blocking
        await asyncio.get_event_loop().run_in_executor(None, read_chunks)
        
        return hasher.hexdigest()
    
    async def _extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from file based on type"""
        metadata = {
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "file_type": file_path.suffix.lower()
        }
        
        try:
            # Determine file type and extract appropriate metadata
            file_ext = file_path.suffix.lower()
            
            if file_ext in settings.SUPPORTED_IMAGE_FORMATS:
                metadata.update(await self._extract_image_metadata(file_path))
            elif file_ext in settings.SUPPORTED_VIDEO_FORMATS:
                metadata.update(await self._extract_video_metadata(file_path))
            elif file_ext in settings.SUPPORTED_AUDIO_FORMATS:
                metadata.update(await self._extract_audio_metadata(file_path))
            elif file_ext in settings.SUPPORTED_DOCUMENT_FORMATS:
                metadata.update(await self._extract_document_metadata(file_path))
            
        except Exception as e:
            logger.warning(f"Failed to extract metadata from {file_path}: {e}")
            metadata["metadata_error"] = str(e)
        
        return metadata
    
    async def _extract_image_metadata(self, file_path: Path) -> Dict:
        """Extract EXIF and other metadata from images"""
        metadata = {}
        
        def extract_sync():
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS
                
                with Image.open(file_path) as img:
                    metadata["dimensions"] = f"{img.width}x{img.height}"
                    metadata["mode"] = img.mode
                    metadata["format"] = img.format
                    
                    # Extract EXIF data
                    exif_data = img.getexif()
                    if exif_data:
                        exif = {}
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if isinstance(value, (str, int, float)):
                                exif[tag] = value
                        metadata["exif"] = exif
                        
            except Exception as e:
                logger.debug(f"Could not extract image metadata: {e}")
                metadata["extraction_error"] = str(e)
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _extract_video_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from video files"""
        metadata = {}
        
        def extract_sync():
            try:
                # Basic file info - would use ffprobe in production
                metadata["type"] = "video"
                metadata["container"] = file_path.suffix.lower()
            except Exception as e:
                logger.debug(f"Could not extract video metadata: {e}")
                metadata["extraction_error"] = str(e)
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _extract_audio_metadata(self, file_path: Path) -> Dict:
        """Extract ID3 and other metadata from audio files"""
        metadata = {}
        
        def extract_sync():
            try:
                from mutagen import File
                
                audio_file = File(file_path)
                if audio_file:
                    metadata["type"] = "audio"
                    metadata["length"] = getattr(audio_file.info, 'length', 0)
                    metadata["bitrate"] = getattr(audio_file.info, 'bitrate', 0)
                    
                    # Extract tags
                    if audio_file.tags:
                        tags = {}
                        for key, value in audio_file.tags.items():
                            if isinstance(value, list) and len(value) > 0:
                                tags[key] = str(value[0])
                            else:
                                tags[key] = str(value)
                        metadata["tags"] = tags
                        
            except Exception as e:
                logger.debug(f"Could not extract audio metadata: {e}")
                metadata["extraction_error"] = str(e)
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _extract_document_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from document files"""
        metadata = {"type": "document"}
        
        def extract_sync():
            try:
                if file_path.suffix.lower() == '.pdf':
                    from PyPDF2 import PdfReader
                    
                    with open(file_path, 'rb') as f:
                        reader = PdfReader(f)
                        metadata["pages"] = len(reader.pages)
                        
                        if reader.metadata:
                            doc_info = {}
                            for key, value in reader.metadata.items():
                                if isinstance(value, str):
                                    doc_info[key.replace('/', '')] = value
                            metadata["document_info"] = doc_info
                            
            except Exception as e:
                logger.debug(f"Could not extract document metadata: {e}")
                metadata["extraction_error"] = str(e)
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _generate_thumbnails(self, file_path: Path) -> List[str]:
        """Generate thumbnails for supported file types"""
        thumbnails = []
        
        try:
            file_ext = file_path.suffix.lower()
            
            if file_ext in settings.SUPPORTED_IMAGE_FORMATS:
                thumbnails = await self._generate_image_thumbnails(file_path)
            elif file_ext in settings.SUPPORTED_VIDEO_FORMATS:
                thumbnails = await self._generate_video_thumbnails(file_path)
                
        except Exception as e:
            logger.warning(f"Failed to generate thumbnails for {file_path}: {e}")
        
        return thumbnails
    
    async def _generate_image_thumbnails(self, file_path: Path) -> List[str]:
        """Generate thumbnails for images"""
        thumbnails = []
        
        def generate_sync():
            try:
                from PIL import Image
                
                # Create thumbnails directory for this file
                thumb_dir = Path(settings.THUMBNAILS_PATH) / file_path.stem
                thumb_dir.mkdir(parents=True, exist_ok=True)
                
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    for size in settings.THUMBNAIL_SIZES:
                        thumb_copy = img.copy()
                        thumb_copy.thumbnail(size, Image.Resampling.LANCZOS)
                        
                        thumb_filename = f"{file_path.stem}_{size[0]}x{size[1]}.jpg"
                        thumb_path = thumb_dir / thumb_filename
                        
                        thumb_copy.save(
                            thumb_path,
                            "JPEG",
                            quality=settings.THUMBNAIL_QUALITY,
                            optimize=True
                        )
                        
                        thumbnails.append(str(thumb_path))
                        
            except Exception as e:
                logger.error(f"Error generating image thumbnails: {e}")
                raise
        
        await asyncio.get_event_loop().run_in_executor(None, generate_sync)
        return thumbnails
    
    async def _generate_video_thumbnails(self, file_path: Path) -> List[str]:
        """Generate thumbnails for videos using ffmpeg"""
        thumbnails = []
        
        def generate_sync():
            try:
                # Create thumbnails directory for this file
                thumb_dir = Path(settings.THUMBNAILS_PATH) / file_path.stem
                thumb_dir.mkdir(parents=True, exist_ok=True)
                
                # For now, just create a placeholder
                # In production, would use ffmpeg to extract frames
                thumb_filename = f"{file_path.stem}_video_thumb.jpg"
                thumb_path = thumb_dir / thumb_filename
                
                # Create a simple placeholder image
                from PIL import Image, ImageDraw
                
                img = Image.new('RGB', (300, 200), color='gray')
                draw = ImageDraw.Draw(img)
                draw.text((50, 90), "VIDEO", fill='white')
                
                img.save(thumb_path, "JPEG", quality=settings.THUMBNAIL_QUALITY)
                thumbnails.append(str(thumb_path))
                
            except Exception as e:
                logger.error(f"Error generating video thumbnails: {e}")
                raise
        
        await asyncio.get_event_loop().run_in_executor(None, generate_sync)
        return thumbnails
    
    def get_stats(self) -> Dict:
        """Get processing statistics"""
        stats = self.stats.copy()
        stats.update({
            "active_batches": len(self.active_batches),
            "processed_hashes_count": len(self.processed_hashes),
            "uptime_seconds": (datetime.now() - stats["start_time"]).total_seconds()
        })
        return stats
    
    def get_active_batches(self) -> List[str]:
        """Get list of currently active batch IDs"""
        return list(self.active_batches.keys())