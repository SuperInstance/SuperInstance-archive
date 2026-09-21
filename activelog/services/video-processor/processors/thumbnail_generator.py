"""
Thumbnail Generator - Creates video thumbnails and preview videos
"""

import cv2
import numpy as np
import logging
import os
import asyncio
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import subprocess

from ..core.config import settings
from ..core.database import DatabaseManager

logger = logging.getLogger('video_processor.thumbnails')

class ThumbnailGenerator:
    """Generates thumbnails and preview videos from source videos"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.temp_path = settings.TEMP_PATH
        self.output_path = settings.OUTPUT_PATH
        
        # Thumbnail settings
        self.thumbnail_sizes = settings.THUMBNAIL_SIZES
        self.thumbnail_quality = settings.THUMBNAIL_QUALITY
        self.preview_duration = settings.PREVIEW_DURATION_SECONDS
        self.preview_fps = settings.PREVIEW_FPS
        
        logger.info("Thumbnail generator initialized")
    
    async def generate_all_thumbnails(self, job_id: str, video_path: str) -> Dict[str, List[str]]:
        """Generate all types of thumbnails for a video"""
        
        results = {
            'poster_thumbnails': [],
            'timeline_thumbnails': [],
            'preview_videos': []
        }
        
        try:
            logger.info(f"Starting thumbnail generation for job {job_id}")
            
            # Create output directories
            thumb_dir = os.path.join(self.output_path, f"thumbnails_{job_id}")
            os.makedirs(thumb_dir, exist_ok=True)
            
            # Generate poster thumbnails (single frame from video)
            poster_paths = await self.generate_poster_thumbnails(job_id, video_path, thumb_dir)
            results['poster_thumbnails'] = poster_paths
            
            # Generate timeline thumbnails (multiple frames for scrubbing)
            timeline_paths = await self.generate_timeline_thumbnails(job_id, video_path, thumb_dir)
            results['timeline_thumbnails'] = timeline_paths
            
            # Generate preview videos (short clips)
            preview_paths = await self.generate_preview_videos(job_id, video_path, thumb_dir)
            results['preview_videos'] = preview_paths
            
            logger.info(f"Thumbnail generation completed for job {job_id}")
            return results
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed for job {job_id}: {e}")
            raise
    
    async def generate_poster_thumbnails(self, job_id: str, video_path: str, output_dir: str) -> List[str]:
        """Generate poster thumbnails at different sizes"""
        
        poster_paths = []
        
        try:
            # Open video capture
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            # Extract frame from middle of video for poster
            middle_frame = total_frames // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)
            
            ret, frame = cap.read()
            if not ret:
                # Fallback to first frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    raise ValueError("Cannot read any frame from video")
            
            cap.release()
            
            timestamp = middle_frame / fps if fps > 0 else 0
            
            # Generate thumbnails at different sizes
            for width, height in self.thumbnail_sizes:
                resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                
                # Save thumbnail
                filename = f"poster_{width}x{height}.jpg"
                file_path = os.path.join(output_dir, filename)
                
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.thumbnail_quality]
                success = cv2.imwrite(file_path, resized_frame, encode_params)
                
                if success:
                    poster_paths.append(file_path)
                    
                    # Save to database
                    await self.db_manager.execute_scalar("""
                        INSERT INTO video_thumbnails 
                        (job_id, thumbnail_type, timestamp_seconds, width, height, file_path, quality, file_size)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING thumbnail_id
                    """, job_id, "poster", timestamp, width, height, file_path, 
                        self.thumbnail_quality, os.path.getsize(file_path))
            
            logger.info(f"Generated {len(poster_paths)} poster thumbnails for job {job_id}")
            return poster_paths
            
        except Exception as e:
            logger.error(f"Error generating poster thumbnails: {e}")
            raise
    
    async def generate_timeline_thumbnails(self, job_id: str, video_path: str, 
                                          output_dir: str, count: int = 20) -> List[str]:
        """Generate timeline thumbnails for video scrubbing interface"""
        
        timeline_paths = []
        
        try:
            # Open video capture
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            # Calculate frame intervals for timeline
            frame_interval = max(1, total_frames // count)
            
            # Use smallest thumbnail size for timeline
            thumb_width, thumb_height = min(self.thumbnail_sizes, key=lambda x: x[0] * x[1])
            
            timeline_dir = os.path.join(output_dir, "timeline")
            os.makedirs(timeline_dir, exist_ok=True)
            
            for i in range(count):
                frame_number = min(i * frame_interval, total_frames - 1)
                timestamp = frame_number / fps if fps > 0 else 0
                
                # Set frame position
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                
                ret, frame = cap.read()
                if not ret:
                    continue
                
                # Resize frame
                resized_frame = cv2.resize(frame, (thumb_width, thumb_height), 
                                         interpolation=cv2.INTER_AREA)
                
                # Save timeline thumbnail
                filename = f"timeline_{i:03d}_{timestamp:.2f}s.jpg"
                file_path = os.path.join(timeline_dir, filename)
                
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.thumbnail_quality]
                success = cv2.imwrite(file_path, resized_frame, encode_params)
                
                if success:
                    timeline_paths.append(file_path)
                    
                    # Save to database
                    await self.db_manager.execute_scalar("""
                        INSERT INTO video_thumbnails 
                        (job_id, thumbnail_type, timestamp_seconds, width, height, file_path, quality, file_size)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING thumbnail_id
                    """, job_id, "timeline", timestamp, thumb_width, thumb_height, 
                        file_path, self.thumbnail_quality, os.path.getsize(file_path))
                
                # Yield control periodically
                if i % 5 == 0:
                    await asyncio.sleep(0.01)
            
            cap.release()
            
            logger.info(f"Generated {len(timeline_paths)} timeline thumbnails for job {job_id}")
            return timeline_paths
            
        except Exception as e:
            logger.error(f"Error generating timeline thumbnails: {e}")
            raise
    
    async def generate_preview_videos(self, job_id: str, video_path: str, 
                                     output_dir: str) -> List[str]:
        """Generate short preview videos"""
        
        preview_paths = []
        
        try:
            # Get video properties
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            if duration <= self.preview_duration:
                # Video is shorter than preview duration, create a copy
                preview_path = await self._create_short_preview(job_id, video_path, output_dir, duration)
                if preview_path:
                    preview_paths.append(preview_path)
            else:
                # Create multiple preview segments
                preview_segments = [
                    ("beginning", 0),
                    ("middle", duration / 2 - self.preview_duration / 2),
                    ("end", duration - self.preview_duration)
                ]
                
                for segment_name, start_time in preview_segments:
                    if start_time < 0:
                        start_time = 0
                    
                    preview_path = await self._create_preview_segment(
                        job_id, video_path, output_dir, segment_name, start_time
                    )
                    
                    if preview_path:
                        preview_paths.append(preview_path)
            
            logger.info(f"Generated {len(preview_paths)} preview videos for job {job_id}")
            return preview_paths
            
        except Exception as e:
            logger.error(f"Error generating preview videos: {e}")
            raise
    
    async def _create_preview_segment(self, job_id: str, video_path: str, output_dir: str,
                                     segment_name: str, start_time: float) -> Optional[str]:
        """Create a preview segment using FFmpeg"""
        
        try:
            preview_dir = os.path.join(output_dir, "previews")
            os.makedirs(preview_dir, exist_ok=True)
            
            output_filename = f"preview_{segment_name}_{self.preview_duration}s.mp4"
            output_path = os.path.join(preview_dir, output_filename)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(self.preview_duration),
                '-c:v', settings.VIDEO_CODEC,
                '-c:a', settings.AUDIO_CODEC,
                '-crf', str(settings.CRF_VALUE),
                '-preset', settings.PRESET,
                '-r', str(self.preview_fps),
                '-movflags', 'faststart',
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Run FFmpeg
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Save to database
                file_size = os.path.getsize(output_path)
                
                await self.db_manager.execute_scalar("""
                    INSERT INTO video_thumbnails 
                    (job_id, thumbnail_type, timestamp_seconds, width, height, file_path, file_size)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING thumbnail_id
                """, job_id, "preview", start_time, 0, 0, output_path, file_size)
                
                logger.debug(f"Created preview segment: {output_path}")
                return output_path
            else:
                logger.error(f"FFmpeg failed for preview creation: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating preview segment: {e}")
            return None
    
    async def _create_short_preview(self, job_id: str, video_path: str, output_dir: str,
                                   duration: float) -> Optional[str]:
        """Create a preview for videos shorter than preview duration"""
        
        try:
            preview_dir = os.path.join(output_dir, "previews")
            os.makedirs(preview_dir, exist_ok=True)
            
            output_filename = f"preview_full_{duration:.1f}s.mp4"
            output_path = os.path.join(preview_dir, output_filename)
            
            # Build FFmpeg command for re-encoding with lower quality
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-c:v', settings.VIDEO_CODEC,
                '-c:a', settings.AUDIO_CODEC,
                '-crf', str(settings.CRF_VALUE + 5),  # Slightly lower quality
                '-preset', 'fast',
                '-r', str(self.preview_fps),
                '-movflags', 'faststart',
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Run FFmpeg
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Save to database
                file_size = os.path.getsize(output_path)
                
                await self.db_manager.execute_scalar("""
                    INSERT INTO video_thumbnails 
                    (job_id, thumbnail_type, timestamp_seconds, width, height, file_path, file_size)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING thumbnail_id
                """, job_id, "preview", 0.0, 0, 0, output_path, file_size)
                
                logger.debug(f"Created short preview: {output_path}")
                return output_path
            else:
                logger.error(f"FFmpeg failed for short preview: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating short preview: {e}")
            return None
    
    async def generate_gif_preview(self, job_id: str, video_path: str, output_dir: str,
                                  start_time: float = 0, duration: float = 5,
                                  width: int = 320, fps: int = 10) -> Optional[str]:
        """Generate an animated GIF preview"""
        
        try:
            gif_dir = os.path.join(output_dir, "gifs")
            os.makedirs(gif_dir, exist_ok=True)
            
            output_filename = f"preview_{start_time:.1f}s_{duration}s.gif"
            output_path = os.path.join(gif_dir, output_filename)
            
            # Build FFmpeg command for GIF creation
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f'fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse',
                '-loop', '0',
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Run FFmpeg
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.debug(f"Created GIF preview: {output_path}")
                return output_path
            else:
                logger.error(f"FFmpeg failed for GIF creation: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating GIF preview: {e}")
            return None
    
    async def create_thumbnail_sprite(self, job_id: str, timeline_paths: List[str],
                                     output_dir: str) -> Optional[str]:
        """Create a sprite sheet of timeline thumbnails for efficient loading"""
        
        try:
            if not timeline_paths:
                return None
            
            # Load first thumbnail to get dimensions
            first_thumb = cv2.imread(timeline_paths[0])
            if first_thumb is None:
                return None
            
            thumb_height, thumb_width = first_thumb.shape[:2]
            
            # Calculate sprite sheet dimensions
            thumbs_per_row = 10
            num_rows = (len(timeline_paths) + thumbs_per_row - 1) // thumbs_per_row
            
            sprite_width = thumb_width * thumbs_per_row
            sprite_height = thumb_height * num_rows
            
            # Create sprite sheet
            sprite = np.zeros((sprite_height, sprite_width, 3), dtype=np.uint8)
            
            # Place thumbnails in sprite
            for i, thumb_path in enumerate(timeline_paths):
                thumb = cv2.imread(thumb_path)
                if thumb is None:
                    continue
                
                # Resize if necessary
                if thumb.shape[:2] != (thumb_height, thumb_width):
                    thumb = cv2.resize(thumb, (thumb_width, thumb_height))
                
                # Calculate position in sprite
                row = i // thumbs_per_row
                col = i % thumbs_per_row
                
                y_start = row * thumb_height
                y_end = y_start + thumb_height
                x_start = col * thumb_width
                x_end = x_start + thumb_width
                
                sprite[y_start:y_end, x_start:x_end] = thumb
            
            # Save sprite sheet
            sprite_filename = f"timeline_sprite.jpg"
            sprite_path = os.path.join(output_dir, sprite_filename)
            
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.thumbnail_quality]
            success = cv2.imwrite(sprite_path, sprite, encode_params)
            
            if success:
                # Create metadata for sprite sheet
                sprite_metadata = {
                    'sprite_path': sprite_path,
                    'thumb_width': thumb_width,
                    'thumb_height': thumb_height,
                    'thumbs_per_row': thumbs_per_row,
                    'total_thumbs': len(timeline_paths),
                    'sprite_width': sprite_width,
                    'sprite_height': sprite_height
                }
                
                # Save metadata to JSON file
                import json
                metadata_path = os.path.join(output_dir, "sprite_metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(sprite_metadata, f, indent=2)
                
                logger.info(f"Created thumbnail sprite: {sprite_path}")
                return sprite_path
            
        except Exception as e:
            logger.error(f"Error creating thumbnail sprite: {e}")
            return None
    
    async def generate_video_poster_from_keyframes(self, job_id: str, output_path: str,
                                                  grid_size: Tuple[int, int] = (3, 3)) -> Optional[str]:
        """Generate a poster image from video keyframes"""
        
        try:
            # Get keyframes for the job
            keyframes = await self.db_manager.get_job_keyframes(job_id)
            
            if not keyframes:
                logger.warning(f"No keyframes found for job {job_id}")
                return None
            
            # Select evenly distributed keyframes
            max_keyframes = grid_size[0] * grid_size[1]
            if len(keyframes) > max_keyframes:
                indices = np.linspace(0, len(keyframes) - 1, max_keyframes, dtype=int)
                selected_keyframes = [keyframes[i] for i in indices]
            else:
                selected_keyframes = keyframes
            
            # Load keyframe images
            images = []
            target_width, target_height = 213, 120  # 16:9 aspect ratio
            
            for keyframe in selected_keyframes:
                thumbnail_path = keyframe.get('thumbnail_path') or keyframe.get('file_path')
                if thumbnail_path and os.path.exists(thumbnail_path):
                    img = cv2.imread(thumbnail_path)
                    if img is not None:
                        # Resize to standard size
                        img = cv2.resize(img, (target_width, target_height))
                        images.append(img)
            
            if not images:
                logger.warning(f"No valid keyframe images found for job {job_id}")
                return None
            
            # Create poster grid
            rows = []
            for row in range(grid_size[1]):
                row_images = []
                for col in range(grid_size[0]):
                    idx = row * grid_size[0] + col
                    if idx < len(images):
                        row_images.append(images[idx])
                    else:
                        # Create blank image
                        blank = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                        row_images.append(blank)
                
                # Concatenate horizontally
                row_img = np.hstack(row_images)
                rows.append(row_img)
            
            # Concatenate vertically
            poster = np.vstack(rows)
            
            # Add border and title if needed
            poster = cv2.copyMakeBorder(poster, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[0, 0, 0])
            
            # Save poster
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 95]
            success = cv2.imwrite(output_path, poster, encode_params)
            
            if success:
                logger.info(f"Created video poster from keyframes: {output_path}")
                return output_path
            
        except Exception as e:
            logger.error(f"Error generating video poster from keyframes: {e}")
            return None
    
    async def cleanup_thumbnails(self, job_id: str):
        """Clean up thumbnail files for a job"""
        
        try:
            # Get all thumbnails for the job
            thumbnails = await self.db_manager.execute_query("""
                SELECT file_path FROM video_thumbnails WHERE job_id = $1
            """, job_id)
            
            # Delete files
            deleted_count = 0
            for thumbnail in thumbnails:
                file_path = thumbnail['file_path']
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete thumbnail file {file_path}: {e}")
            
            # Remove from database
            await self.db_manager.execute_command("""
                DELETE FROM video_thumbnails WHERE job_id = $1
            """, job_id)
            
            logger.info(f"Cleaned up {deleted_count} thumbnail files for job {job_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up thumbnails: {e}")
            raise