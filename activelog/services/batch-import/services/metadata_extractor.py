"""
Metadata extraction service for different file types
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json

from ..core.logging import logger


class MetadataExtractor:
    """Extracts metadata from various file types"""
    
    def __init__(self):
        self.extractors = {
            'image': self._extract_image_metadata,
            'video': self._extract_video_metadata,
            'audio': self._extract_audio_metadata,
            'document': self._extract_document_metadata
        }
        
    async def extract_metadata(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """Extract metadata based on file type"""
        try:
            # Basic metadata
            stat = file_path.stat()
            metadata = {
                "filename": file_path.name,
                "file_size": stat.st_size,
                "mime_type": mime_type,
                "file_extension": file_path.suffix.lower(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extracted_at": datetime.now().isoformat()
            }
            
            # Type-specific metadata
            file_type = self._get_file_type(mime_type, file_path.suffix)
            if file_type in self.extractors:
                type_metadata = await self.extractors[file_type](file_path)
                metadata.update(type_metadata)
            
            return metadata
            
        except Exception as e:
            logger.error("Error extracting metadata", 
                        file=str(file_path), 
                        error=str(e))
            return {"error": str(e)}
    
    def _get_file_type(self, mime_type: str, extension: str) -> str:
        """Determine file type category"""
        if mime_type:
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('video/'):
                return 'video'
            elif mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('application/pdf') or \
                 mime_type.startswith('application/msword') or \
                 mime_type.startswith('application/vnd.'):
                return 'document'
        
        # Fallback to extension
        image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.heic'}
        video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
        audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'}
        doc_exts = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt'}
        
        ext = extension.lower()
        if ext in image_exts:
            return 'image'
        elif ext in video_exts:
            return 'video'
        elif ext in audio_exts:
            return 'audio'
        elif ext in doc_exts:
            return 'document'
        
        return 'unknown'
    
    async def _extract_image_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract EXIF and image metadata"""
        metadata = {"type": "image"}
        
        def extract_sync():
            try:
                from PIL import Image
                from PIL.ExifTags import TAGS, GPSTAGS
                
                with Image.open(file_path) as img:
                    # Basic image info
                    metadata.update({
                        "width": img.width,
                        "height": img.height,
                        "mode": img.mode,
                        "format": img.format,
                        "has_transparency": img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                    })
                    
                    # Extract EXIF data
                    exif_data = img.getexif()
                    if exif_data:
                        exif = {}
                        for tag_id, value in exif_data.items():
                            tag = TAGS.get(tag_id, tag_id)
                            
                            # Handle GPS data separately
                            if tag == 'GPSInfo':
                                gps_data = {}
                                for gps_tag_id, gps_value in value.items():
                                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                                    gps_data[gps_tag] = gps_value
                                exif['GPS'] = gps_data
                            else:
                                # Convert bytes to string if needed
                                if isinstance(value, bytes):
                                    try:
                                        value = value.decode('utf-8')
                                    except:
                                        value = str(value)
                                exif[tag] = value
                        
                        metadata["exif"] = exif
                        
                        # Extract common fields
                        if 'DateTime' in exif:
                            metadata["date_taken"] = exif['DateTime']
                        if 'Make' in exif:
                            metadata["camera_make"] = exif['Make']
                        if 'Model' in exif:
                            metadata["camera_model"] = exif['Model']
                        if 'Software' in exif:
                            metadata["software"] = exif['Software']
                    
                    # Color profile information
                    if hasattr(img, 'info') and 'icc_profile' in img.info:
                        metadata["has_color_profile"] = True
                        
            except ImportError:
                metadata["error"] = "PIL (Pillow) not available for image metadata extraction"
            except Exception as e:
                metadata["error"] = f"Failed to extract image metadata: {str(e)}"
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _extract_video_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract video metadata using ffprobe"""
        metadata = {"type": "video"}
        
        def extract_sync():
            try:
                import ffmpeg
                
                # Use ffprobe to get video metadata
                probe = ffmpeg.probe(str(file_path))
                
                # General format info
                format_info = probe.get('format', {})
                metadata.update({
                    "duration": float(format_info.get('duration', 0)),
                    "size": int(format_info.get('size', 0)),
                    "bit_rate": int(format_info.get('bit_rate', 0)),
                    "format_name": format_info.get('format_name', ''),
                    "format_long_name": format_info.get('format_long_name', '')
                })
                
                # Stream information
                streams = probe.get('streams', [])
                video_streams = [s for s in streams if s.get('codec_type') == 'video']
                audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
                
                if video_streams:
                    video_stream = video_streams[0]
                    metadata.update({
                        "width": video_stream.get('width'),
                        "height": video_stream.get('height'),
                        "codec_name": video_stream.get('codec_name'),
                        "codec_long_name": video_stream.get('codec_long_name'),
                        "frame_rate": video_stream.get('r_frame_rate'),
                        "avg_frame_rate": video_stream.get('avg_frame_rate'),
                        "pixel_format": video_stream.get('pix_fmt')
                    })
                
                if audio_streams:
                    audio_stream = audio_streams[0]
                    metadata["audio"] = {
                        "codec_name": audio_stream.get('codec_name'),
                        "codec_long_name": audio_stream.get('codec_long_name'),
                        "sample_rate": audio_stream.get('sample_rate'),
                        "channels": audio_stream.get('channels'),
                        "channel_layout": audio_stream.get('channel_layout')
                    }
                
                # Tags (metadata)
                if 'tags' in format_info:
                    metadata["tags"] = format_info['tags']
                    
            except ImportError:
                metadata["error"] = "ffmpeg-python not available for video metadata extraction"
            except Exception as e:
                metadata["error"] = f"Failed to extract video metadata: {str(e)}"
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _extract_audio_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract audio metadata using mutagen"""
        metadata = {"type": "audio"}
        
        def extract_sync():
            try:
                from mutagen import File
                
                audio_file = File(file_path)
                if audio_file is None:
                    metadata["error"] = "Could not read audio file"
                    return
                
                # Basic audio info
                if hasattr(audio_file, 'info'):
                    info = audio_file.info
                    metadata.update({
                        "length": getattr(info, 'length', 0),
                        "bitrate": getattr(info, 'bitrate', 0),
                        "sample_rate": getattr(info, 'sample_rate', 0),
                        "channels": getattr(info, 'channels', 0),
                        "bitrate_mode": getattr(info, 'bitrate_mode', None)
                    })
                
                # Tags (ID3, etc.)
                if audio_file.tags:
                    tags = {}
                    for key, value in audio_file.tags.items():
                        # Handle list values
                        if isinstance(value, list):
                            if len(value) == 1:
                                tags[key] = str(value[0])
                            else:
                                tags[key] = [str(v) for v in value]
                        else:
                            tags[key] = str(value)
                    
                    metadata["tags"] = tags
                    
                    # Common tag mappings
                    common_tags = {
                        'TIT2': 'title',
                        'TPE1': 'artist', 
                        'TALB': 'album',
                        'TDRC': 'year',
                        'TCON': 'genre',
                        'TRCK': 'track_number'
                    }
                    
                    for tag_key, readable_key in common_tags.items():
                        if tag_key in tags:
                            metadata[readable_key] = tags[tag_key]
                
            except ImportError:
                metadata["error"] = "mutagen not available for audio metadata extraction"
            except Exception as e:
                metadata["error"] = f"Failed to extract audio metadata: {str(e)}"
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata
    
    async def _extract_document_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract document metadata"""
        metadata = {"type": "document"}
        
        def extract_sync():
            try:
                extension = file_path.suffix.lower()
                
                if extension == '.pdf':
                    # PDF metadata
                    try:
                        from PyPDF2 import PdfReader
                        
                        with open(file_path, 'rb') as f:
                            reader = PdfReader(f)
                            metadata.update({
                                "pages": len(reader.pages),
                                "encrypted": reader.is_encrypted
                            })
                            
                            # Document info
                            if reader.metadata:
                                doc_info = {}
                                for key, value in reader.metadata.items():
                                    clean_key = key.replace('/', '').lower()
                                    if isinstance(value, str):
                                        doc_info[clean_key] = value
                                metadata["document_info"] = doc_info
                                
                    except ImportError:
                        metadata["error"] = "PyPDF2 not available for PDF metadata extraction"
                        
                elif extension in ['.docx', '.xlsx', '.pptx']:
                    # Office documents
                    try:
                        from zipfile import ZipFile
                        import xml.etree.ElementTree as ET
                        
                        with ZipFile(file_path, 'r') as zip_file:
                            # Try to read core properties
                            try:
                                core_props = zip_file.read('docProps/core.xml')
                                root = ET.fromstring(core_props)
                                
                                props = {}
                                namespaces = {
                                    'cp': 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties',
                                    'dc': 'http://purl.org/dc/elements/1.1/',
                                    'dcterms': 'http://purl.org/dc/terms/'
                                }
                                
                                for elem in root:
                                    tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                                    if elem.text:
                                        props[tag_name] = elem.text
                                
                                metadata["document_properties"] = props
                                
                            except:
                                pass
                                
                    except Exception as e:
                        metadata["error"] = f"Failed to extract Office document metadata: {str(e)}"
                        
                elif extension == '.txt':
                    # Text file - basic info
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read(1024)  # Read first 1KB
                            metadata.update({
                                "encoding": "utf-8",
                                "line_count": content.count('\n') + 1,
                                "char_count": len(content),
                                "preview": content[:200] if content else ""
                            })
                    except Exception as e:
                        metadata["error"] = f"Failed to extract text file metadata: {str(e)}"
                        
            except Exception as e:
                metadata["error"] = f"Failed to extract document metadata: {str(e)}"
        
        await asyncio.get_event_loop().run_in_executor(None, extract_sync)
        return metadata