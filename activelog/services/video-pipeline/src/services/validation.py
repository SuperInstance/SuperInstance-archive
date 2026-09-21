"""
Video file validation and metadata extraction service
"""
import asyncio
import hashlib
import mimetypes
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

import cv2
import ffmpeg
from PIL import Image
import structlog

from config.settings import settings

logger = structlog.get_logger()


class VideoValidationService:
    """
    Service for validating video files and extracting basic metadata
    """
    
    def __init__(self):
        self.supported_formats = settings.supported_formats
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        
    async def validate_video_file(
        self,
        file_path: str,
        original_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive video file validation
        
        Args:
            file_path: Path to the video file
            original_filename: Original filename for additional validation
            
        Returns:
            Validation result with metadata and any issues found
        """
        validation_result = {
            "is_valid": False,
            "file_info": {},
            "video_metadata": {},
            "issues": [],
            "warnings": []
        }
        
        try:
            # Basic file checks
            if not os.path.exists(file_path):
                validation_result["issues"].append("File does not exist")
                return validation_result
                
            # File size check
            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                validation_result["issues"].append(
                    f"File size ({file_size / (1024*1024):.2f} MB) exceeds maximum allowed "
                    f"({settings.max_file_size_mb} MB)"
                )
                
            if file_size == 0:
                validation_result["issues"].append("File is empty")
                return validation_result
                
            # MIME type validation
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type or not mime_type.startswith('video/'):
                validation_result["warnings"].append(f"Unexpected MIME type: {mime_type}")
                
            # File extension validation
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            if file_extension not in self.supported_formats:
                validation_result["issues"].append(
                    f"Unsupported file format: {file_extension}. "
                    f"Supported formats: {', '.join(self.supported_formats)}"
                )
                
            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path)
            
            # Basic file info
            validation_result["file_info"] = {
                "path": file_path,
                "original_filename": original_filename or os.path.basename(file_path),
                "size": file_size,
                "mime_type": mime_type,
                "extension": file_extension,
                "hash": file_hash,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Video metadata extraction
            video_metadata = await self._extract_video_metadata(file_path)
            validation_result["video_metadata"] = video_metadata
            
            # Content validation
            content_issues = await self._validate_video_content(file_path, video_metadata)
            validation_result["issues"].extend(content_issues)
            
            # Corruption check
            corruption_check = await self._check_video_corruption(file_path)
            if not corruption_check["is_intact"]:
                validation_result["issues"].extend(corruption_check["issues"])
                
            # Security scan (basic)
            security_issues = await self._basic_security_scan(file_path)
            validation_result["issues"].extend(security_issues)
            
            # Determine if file is valid
            validation_result["is_valid"] = len(validation_result["issues"]) == 0
            
            logger.info("Video validation completed",
                       file_path=file_path,
                       is_valid=validation_result["is_valid"],
                       issues_count=len(validation_result["issues"]),
                       warnings_count=len(validation_result["warnings"]))
            
            return validation_result
            
        except Exception as e:
            logger.error("Video validation failed", 
                        file_path=file_path, 
                        error=str(e))
            validation_result["issues"].append(f"Validation error: {str(e)}")
            return validation_result

    async def _extract_video_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract comprehensive video metadata using ffmpeg"""
        try:
            # Use ffprobe to get detailed metadata
            probe = ffmpeg.probe(file_path)
            
            video_info = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            audio_info = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'audio'),
                None
            )
            
            metadata = {
                "format": probe.get('format', {}),
                "streams": probe.get('streams', []),
                "video": {},
                "audio": {}
            }
            
            if video_info:
                metadata["video"] = {
                    "codec": video_info.get('codec_name'),
                    "codec_long_name": video_info.get('codec_long_name'),
                    "width": int(video_info.get('width', 0)),
                    "height": int(video_info.get('height', 0)),
                    "fps": self._safe_eval_fraction(video_info.get('r_frame_rate', '0/1')),
                    "duration": float(video_info.get('duration', 0)),
                    "bit_rate": int(video_info.get('bit_rate', 0)),
                    "pixel_format": video_info.get('pix_fmt'),
                    "profile": video_info.get('profile'),
                    "level": video_info.get('level'),
                    "has_b_frames": video_info.get('has_b_frames', 0),
                    "color_space": video_info.get('color_space'),
                    "color_range": video_info.get('color_range')
                }
                
            if audio_info:
                metadata["audio"] = {
                    "codec": audio_info.get('codec_name'),
                    "codec_long_name": audio_info.get('codec_long_name'),
                    "sample_rate": int(audio_info.get('sample_rate', 0)),
                    "channels": int(audio_info.get('channels', 0)),
                    "channel_layout": audio_info.get('channel_layout'),
                    "duration": float(audio_info.get('duration', 0)),
                    "bit_rate": int(audio_info.get('bit_rate', 0)),
                    "bits_per_sample": int(audio_info.get('bits_per_sample', 0))
                }
                
            # Format information
            format_info = probe.get('format', {})
            metadata["format_info"] = {
                "format_name": format_info.get('format_name'),
                "format_long_name": format_info.get('format_long_name'),
                "duration": float(format_info.get('duration', 0)),
                "size": int(format_info.get('size', 0)),
                "bit_rate": int(format_info.get('bit_rate', 0)),
                "probe_score": int(format_info.get('probe_score', 0))
            }
            
            return metadata
            
        except Exception as e:
            logger.error("Failed to extract video metadata", 
                        file_path=file_path, 
                        error=str(e))
            return {}

    async def _validate_video_content(
        self, 
        file_path: str, 
        metadata: Dict[str, Any]
    ) -> List[str]:
        """Validate video content requirements"""
        issues = []
        
        try:
            video_info = metadata.get("video", {})
            audio_info = metadata.get("audio", {})
            format_info = metadata.get("format_info", {})
            
            # Duration check
            duration = format_info.get("duration", 0)
            if duration <= 0:
                issues.append("Video has no duration or invalid duration")
            elif duration > 14400:  # 4 hours
                issues.append("Video duration exceeds 4 hours maximum")
                
            # Resolution check
            width = video_info.get("width", 0)
            height = video_info.get("height", 0)
            
            if width <= 0 or height <= 0:
                issues.append("Invalid video resolution")
            elif width > 7680 or height > 4320:  # 8K max
                issues.append("Video resolution exceeds 8K maximum")
            elif width < 128 or height < 128:  # Minimum resolution
                issues.append("Video resolution below minimum 128x128")
                
            # Aspect ratio check
            if width > 0 and height > 0:
                aspect_ratio = width / height
                if aspect_ratio > 5 or aspect_ratio < 0.2:
                    issues.append(f"Unusual aspect ratio: {aspect_ratio:.2f}")
                    
            # Frame rate check
            fps = video_info.get("fps", 0)
            if fps <= 0:
                issues.append("Invalid or missing frame rate")
            elif fps > 120:
                issues.append("Frame rate exceeds 120 FPS")
                
            # Bitrate check
            bit_rate = format_info.get("bit_rate", 0)
            if bit_rate > 100_000_000:  # 100 Mbps
                issues.append("Bitrate exceeds reasonable maximum")
                
            # Codec validation
            video_codec = video_info.get("codec")
            if video_codec and video_codec not in ["h264", "h265", "vp8", "vp9", "av1"]:
                issues.append(f"Uncommon video codec: {video_codec}")
                
            # Audio validation
            if audio_info:
                audio_codec = audio_info.get("codec")
                sample_rate = audio_info.get("sample_rate", 0)
                
                if audio_codec and audio_codec not in ["aac", "mp3", "opus", "vorbis", "flac"]:
                    issues.append(f"Uncommon audio codec: {audio_codec}")
                    
                if sample_rate > 0 and (sample_rate < 8000 or sample_rate > 192000):
                    issues.append(f"Unusual audio sample rate: {sample_rate}")
                    
            return issues
            
        except Exception as e:
            logger.error("Content validation failed", 
                        file_path=file_path, 
                        error=str(e))
            return [f"Content validation error: {str(e)}"]

    async def _check_video_corruption(self, file_path: str) -> Dict[str, Any]:
        """Check for video file corruption"""
        result = {
            "is_intact": True,
            "issues": []
        }
        
        try:
            # Try to read the first and last few seconds
            cap = cv2.VideoCapture(file_path)
            
            if not cap.isOpened():
                result["is_intact"] = False
                result["issues"].append("Cannot open video file with OpenCV")
                return result
                
            # Check if we can read frames
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if total_frames <= 0 or fps <= 0:
                result["issues"].append("Invalid frame count or FPS")
                
            # Try to read first frame
            ret, frame = cap.read()
            if not ret or frame is None:
                result["is_intact"] = False
                result["issues"].append("Cannot read first frame")
                
            # Try to read a frame from the middle
            if total_frames > 10:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
                ret, frame = cap.read()
                if not ret or frame is None:
                    result["issues"].append("Cannot read middle frame")
                    
            # Try to read near the end
            if total_frames > 20:
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 10)
                ret, frame = cap.read()
                if not ret or frame is None:
                    result["issues"].append("Cannot read frame near end")
                    
            cap.release()
            
            # If we found issues, mark as not intact
            if result["issues"]:
                result["is_intact"] = False
                
            return result
            
        except Exception as e:
            logger.error("Corruption check failed", 
                        file_path=file_path, 
                        error=str(e))
            result["is_intact"] = False
            result["issues"].append(f"Corruption check error: {str(e)}")
            return result

    async def _basic_security_scan(self, file_path: str) -> List[str]:
        """Basic security scan for video files"""
        issues = []
        
        try:
            # Check file size vs metadata size
            actual_size = os.path.getsize(file_path)
            
            # Read first 1KB to check for suspicious patterns
            with open(file_path, 'rb') as f:
                header = f.read(1024)
                
            # Check for executable signatures
            exe_signatures = [
                b'MZ',  # Windows executable
                b'\x7fELF',  # Linux executable
                b'\xca\xfe\xba\xbe',  # Java class file
                b'PK\x03\x04',  # ZIP/JAR (could contain malware)
            ]
            
            for sig in exe_signatures:
                if header.startswith(sig):
                    issues.append(f"File contains suspicious executable signature")
                    break
                    
            # Check for extremely large files that might be zip bombs
            if actual_size > 5 * 1024 * 1024 * 1024:  # 5GB
                issues.append("File size is extremely large, possible zip bomb")
                
            return issues
            
        except Exception as e:
            logger.error("Security scan failed", 
                        file_path=file_path, 
                        error=str(e))
            return [f"Security scan error: {str(e)}"]

    async def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
                
        return hash_sha256.hexdigest()

    def _safe_eval_fraction(self, fraction_str: str) -> float:
        """Safely evaluate fraction strings like '30000/1001'"""
        try:
            if '/' in fraction_str:
                num, den = fraction_str.split('/')
                return float(num) / float(den) if float(den) != 0 else 0.0
            return float(fraction_str)
        except:
            return 0.0

    async def extract_thumbnail(
        self,
        video_path: str,
        timestamp: float = None,
        output_path: str = None
    ) -> Optional[str]:
        """
        Extract a thumbnail from video at specified timestamp
        """
        try:
            if timestamp is None:
                # Extract metadata to find middle timestamp
                metadata = await self._extract_video_metadata(video_path)
                duration = metadata.get("format_info", {}).get("duration", 0)
                timestamp = duration / 2 if duration > 0 else 5.0
                
            # Create temp file if output path not specified
            if output_path is None:
                temp_fd, output_path = tempfile.mkstemp(suffix='.jpg')
                os.close(temp_fd)
                
            # Extract thumbnail using ffmpeg
            (
                ffmpeg
                .input(video_path, ss=timestamp)
                .output(output_path, vframes=1, format='image2', vcodec='mjpeg')
                .overwrite_output()
                .run(quiet=True)
            )
            
            # Validate thumbnail was created
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            else:
                return None
                
        except Exception as e:
            logger.error("Thumbnail extraction failed",
                        video_path=video_path,
                        timestamp=timestamp,
                        error=str(e))
            return None

    async def get_video_info_summary(self, file_path: str) -> Dict[str, Any]:
        """
        Get a summary of video information for quick access
        """
        try:
            metadata = await self._extract_video_metadata(file_path)
            
            video_info = metadata.get("video", {})
            audio_info = metadata.get("audio", {})
            format_info = metadata.get("format_info", {})
            
            return {
                "duration": format_info.get("duration", 0),
                "width": video_info.get("width", 0),
                "height": video_info.get("height", 0),
                "fps": video_info.get("fps", 0),
                "video_codec": video_info.get("codec"),
                "audio_codec": audio_info.get("codec"),
                "file_size": format_info.get("size", 0),
                "bit_rate": format_info.get("bit_rate", 0),
                "has_audio": bool(audio_info),
                "has_video": bool(video_info)
            }
            
        except Exception as e:
            logger.error("Failed to get video info summary",
                        file_path=file_path,
                        error=str(e))
            return {}


# Global validation service instance
validation_service = VideoValidationService()