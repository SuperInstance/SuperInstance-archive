"""
Thumbnail generation service for images and videos
"""

import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..core.config import settings
from ..core.logging import logger


class ThumbnailGenerator:
    """Generates thumbnails for images and videos"""
    
    def __init__(self):
        self.thumbnail_sizes = settings.THUMBNAIL_SIZES
        self.thumbnail_quality = settings.THUMBNAIL_QUALITY
        self.video_thumbnail_time = settings.VIDEO_THUMBNAIL_TIME
        
    async def generate_thumbnails(self, file_path: Path, mime_type: str) -> Dict[str, List[str]]:
        """Generate thumbnails for supported file types"""
        try:
            thumbnails = {"paths": [], "sizes": []}
            
            if mime_type and mime_type.startswith('image/'):
                thumbnail_paths = await self._generate_image_thumbnails(file_path)
                thumbnails["paths"] = thumbnail_paths
                thumbnails["type"] = "image"
            elif mime_type and mime_type.startswith('video/'):
                thumbnail_paths = await self._generate_video_thumbnails(file_path)
                thumbnails["paths"] = thumbnail_paths
                thumbnails["type"] = "video"
            else:
                # Check by extension if mime type is not available
                extension = file_path.suffix.lower()
                if extension in settings.SUPPORTED_IMAGE_FORMATS:
                    thumbnail_paths = await self._generate_image_thumbnails(file_path)
                    thumbnails["paths"] = thumbnail_paths
                    thumbnails["type"] = "image"
                elif extension in settings.SUPPORTED_VIDEO_FORMATS:
                    thumbnail_paths = await self._generate_video_thumbnails(file_path)
                    thumbnails["paths"] = thumbnail_paths
                    thumbnails["type"] = "video"
            
            if thumbnails["paths"]:
                thumbnails["sizes"] = [f"{size[0]}x{size[1]}" for size in self.thumbnail_sizes]
                thumbnails["generated_at"] = datetime.now().isoformat()
                
            return thumbnails
            
        except Exception as e:
            logger.error("Error generating thumbnails", 
                        file=str(file_path), 
                        error=str(e))
            return {"error": str(e), "paths": [], "sizes": []}
    
    async def _generate_image_thumbnails(self, file_path: Path) -> List[str]:
        """Generate thumbnails for image files using Pillow"""
        thumbnail_paths = []
        
        def generate_sync():
            try:
                from PIL import Image, ImageOps
                
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary (handles transparency)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        # Create white background for transparent images
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    elif img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Apply auto-rotation based on EXIF
                    img = ImageOps.exif_transpose(img)
                    
                    # Generate thumbnails for each size
                    for size in self.thumbnail_sizes:
                        # Create thumbnail
                        thumb_img = img.copy()
                        thumb_img.thumbnail(size, Image.Resampling.LANCZOS)
                        
                        # Create thumbnail filename
                        thumb_filename = f"{file_path.stem}_{size[0]}x{size[1]}.jpg"
                        
                        # Save to temporary file
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                            thumb_img.save(
                                temp_file.name,
                                'JPEG',
                                quality=self.thumbnail_quality,
                                optimize=True
                            )
                            thumbnail_paths.append(temp_file.name)
                            
                        logger.debug("Generated image thumbnail", 
                                   original=str(file_path),
                                   thumbnail=thumb_filename,
                                   size=f"{size[0]}x{size[1]}")
                        
            except ImportError:
                raise Exception("Pillow (PIL) not available for image thumbnail generation")
            except Exception as e:
                raise Exception(f"Failed to generate image thumbnails: {str(e)}")
        
        await asyncio.get_event_loop().run_in_executor(None, generate_sync)
        return thumbnail_paths
    
    async def _generate_video_thumbnails(self, file_path: Path) -> List[str]:
        """Generate thumbnails for video files using ffmpeg"""
        thumbnail_paths = []
        
        def generate_sync():
            try:
                import ffmpeg
                
                # Get video info first
                probe = ffmpeg.probe(str(file_path))
                video_streams = [s for s in probe['streams'] if s['codec_type'] == 'video']
                
                if not video_streams:
                    raise Exception("No video streams found in file")
                
                video_stream = video_streams[0]
                duration = float(probe['format'].get('duration', 0))
                
                # Calculate thumbnail extraction time (avoid end of video)
                extract_time = min(self.video_thumbnail_time, duration * 0.1) if duration > 0 else self.video_thumbnail_time
                
                # Generate thumbnails for each size
                for size in self.thumbnail_sizes:
                    # Create temporary output file
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                        temp_path = temp_file.name
                    
                    try:
                        # Extract frame at specified time and resize
                        (
                            ffmpeg
                            .input(str(file_path), ss=extract_time)
                            .filter('scale', size[0], size[1], force_original_aspect_ratio='decrease')
                            .filter('pad', size[0], size[1], '(ow-iw)/2', '(oh-ih)/2', color='black')
                            .output(temp_path, vframes=1, format='image2', loglevel='error')
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                        
                        # Verify thumbnail was created
                        if Path(temp_path).exists() and Path(temp_path).stat().st_size > 0:
                            thumbnail_paths.append(temp_path)
                            
                            logger.debug("Generated video thumbnail", 
                                       original=str(file_path),
                                       size=f"{size[0]}x{size[1]}",
                                       time=extract_time)
                        else:
                            logger.warning("Video thumbnail generation failed - empty file", 
                                         file=str(file_path),
                                         size=f"{size[0]}x{size[1]}")
                            
                    except ffmpeg.Error as e:
                        error_msg = e.stderr.decode() if e.stderr else str(e)
                        logger.warning("FFmpeg error generating video thumbnail", 
                                     file=str(file_path),
                                     size=f"{size[0]}x{size[1]}",
                                     error=error_msg)
                        # Clean up failed temp file
                        if Path(temp_path).exists():
                            Path(temp_path).unlink()
                            
            except ImportError:
                raise Exception("ffmpeg-python not available for video thumbnail generation")
            except Exception as e:
                raise Exception(f"Failed to generate video thumbnails: {str(e)}")
        
        await asyncio.get_event_loop().run_in_executor(None, generate_sync)
        return thumbnail_paths
    
    async def cleanup_thumbnails(self, thumbnail_paths: List[str]):
        """Clean up temporary thumbnail files"""
        for thumb_path in thumbnail_paths:
            try:
                path = Path(thumb_path)
                if path.exists():
                    path.unlink()
                    logger.debug("Cleaned up thumbnail", path=thumb_path)
            except Exception as e:
                logger.warning("Failed to cleanup thumbnail", 
                             path=thumb_path, 
                             error=str(e))
    
    async def get_thumbnail_info(self, thumbnail_paths: List[str]) -> List[Dict]:
        """Get information about generated thumbnails"""
        thumbnail_info = []
        
        for thumb_path in thumbnail_paths:
            try:
                path = Path(thumb_path)
                if path.exists():
                    stat = path.stat()
                    
                    # Extract size from filename if possible
                    size_info = None
                    if '_' in path.stem:
                        size_part = path.stem.split('_')[-1]
                        if 'x' in size_part:
                            try:
                                width, height = size_part.split('x')
                                size_info = {"width": int(width), "height": int(height)}
                            except:
                                pass
                    
                    info = {
                        "path": str(path),
                        "filename": path.name,
                        "size_bytes": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                    }
                    
                    if size_info:
                        info.update(size_info)
                    
                    thumbnail_info.append(info)
                    
            except Exception as e:
                logger.warning("Error getting thumbnail info", 
                             path=thumb_path, 
                             error=str(e))
        
        return thumbnail_info
    
    def validate_requirements(self) -> Dict[str, bool]:
        """Validate that required libraries are available"""
        requirements = {
            "pillow": False,
            "ffmpeg": False
        }
        
        try:
            import PIL
            requirements["pillow"] = True
        except ImportError:
            pass
        
        try:
            import ffmpeg
            requirements["ffmpeg"] = True
        except ImportError:
            pass
        
        return requirements