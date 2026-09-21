"""
Scene Detector - Detects and segments video scenes using various algorithms
"""

import cv2
import numpy as np
import logging
import os
import asyncio
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime
from scipy import signal
from scipy.spatial.distance import pdist, squareform
import sklearn.cluster as cluster

from ..core.config import settings
from ..core.database import DatabaseManager

logger = logging.getLogger('video_processor.scenes')

class SceneDetector:
    """Detects scene boundaries and segments videos into meaningful scenes"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.temp_path = settings.TEMP_PATH
        
        # Scene detection parameters
        self.threshold = settings.SCENE_DETECTION_THRESHOLD
        self.min_scene_duration = settings.MIN_SCENE_DURATION_SECONDS
        self.max_scenes = settings.MAX_SCENES_PER_VIDEO
        
        logger.info("Scene detector initialized")
    
    async def detect_scenes(self, job_id: str, video_path: str, 
                           method: str = "histogram") -> List[Dict]:
        """
        Detect scenes in video using specified method
        
        Args:
            job_id: Processing job ID
            video_path: Path to video file
            method: Detection method ('histogram', 'optical_flow', 'content_aware', 'audio')
        """
        
        scenes = []
        
        try:
            logger.info(f"Starting scene detection for job {job_id} using method: {method}")
            
            # Open video capture
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"Video properties: {total_frames} frames, {fps} FPS, {duration:.2f}s duration")
            
            # Detect scene boundaries based on method
            if method == "histogram":
                scene_boundaries = await self._detect_histogram_scenes(cap, fps, total_frames)
            elif method == "optical_flow":
                scene_boundaries = await self._detect_optical_flow_scenes(cap, fps, total_frames)
            elif method == "content_aware":
                scene_boundaries = await self._detect_content_aware_scenes(cap, fps, total_frames)
            elif method == "audio":
                scene_boundaries = await self._detect_audio_scenes(video_path, fps, duration)
            elif method == "combined":
                scene_boundaries = await self._detect_combined_scenes(cap, video_path, fps, total_frames)
            else:
                raise ValueError(f"Unknown scene detection method: {method}")
            
            cap.release()
            
            # Convert boundaries to scene segments
            scenes = await self._create_scene_segments(job_id, scene_boundaries, fps, duration)
            
            # Save scenes to database
            for scene_data in scenes:
                scene_id = await self.db_manager.save_scene(
                    job_id=job_id,
                    start_time=scene_data['start_time'],
                    end_time=scene_data['end_time'],
                    confidence=scene_data.get('confidence'),
                    description=scene_data.get('description'),
                    dominant_colors=scene_data.get('dominant_colors'),
                    motion_intensity=scene_data.get('motion_intensity'),
                    audio_features=scene_data.get('audio_features')
                )
                scene_data['scene_id'] = scene_id
            
            logger.info(f"Detected {len(scenes)} scenes for job {job_id}")
            return scenes
            
        except Exception as e:
            logger.error(f"Scene detection failed for job {job_id}: {e}")
            raise
    
    async def _detect_histogram_scenes(self, cap: cv2.VideoCapture, fps: float,
                                      total_frames: int) -> List[Tuple[int, float]]:
        """Detect scene boundaries using histogram comparison"""
        
        boundaries = [(0, 1.0)]  # Start with first frame
        prev_hist = None
        frame_number = 0
        
        # Sample frames for analysis (to improve performance)
        sample_interval = max(1, int(fps / 4))  # 4 samples per second
        
        while frame_number < total_frames:
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate histogram for each color channel
            hist = []
            for i in range(3):  # BGR channels
                channel_hist = cv2.calcHist([frame], [i], None, [64], [0, 256])
                hist.extend(channel_hist.flatten())
            
            hist = np.array(hist)
            hist = hist / np.sum(hist)  # Normalize
            
            if prev_hist is not None:
                # Calculate histogram distance
                distance = np.sum(np.abs(hist - prev_hist))
                
                # Check if distance exceeds threshold
                if distance > self.threshold:
                    boundaries.append((frame_number, distance))
            
            prev_hist = hist.copy()
            frame_number += sample_interval
            
            # Yield control periodically
            if len(boundaries) % 20 == 0:
                await asyncio.sleep(0.01)
        
        return boundaries
    
    async def _detect_optical_flow_scenes(self, cap: cv2.VideoCapture, fps: float,
                                         total_frames: int) -> List[Tuple[int, float]]:
        """Detect scene boundaries using optical flow analysis"""
        
        boundaries = [(0, 1.0)]
        prev_gray = None
        frame_number = 0
        
        # Sample frames for analysis
        sample_interval = max(1, int(fps / 2))  # 2 samples per second
        
        # Parameters for Lucas-Kanade optical flow
        lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        while frame_number < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            if not ret:
                break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_gray is not None:
                # Detect corners for tracking
                corners = cv2.goodFeaturesToTrack(
                    prev_gray, maxCorners=200, qualityLevel=0.01, minDistance=7
                )
                
                if corners is not None and len(corners) > 10:
                    # Calculate optical flow
                    next_corners, status, error = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, corners, None, **lk_params
                    )
                    
                    # Calculate motion vectors
                    good_corners = corners[status == 1]
                    good_next_corners = next_corners[status == 1]
                    
                    if len(good_corners) > 10:
                        motion_vectors = good_next_corners - good_corners
                        motion_magnitudes = np.sqrt(
                            motion_vectors[:, 0]**2 + motion_vectors[:, 1]**2
                        )
                        
                        # Calculate scene change metric
                        avg_motion = np.mean(motion_magnitudes)
                        motion_variance = np.var(motion_magnitudes)
                        
                        # Combine metrics for scene boundary detection
                        scene_change_score = avg_motion + (motion_variance / 10.0)
                        
                        # Check if score exceeds threshold
                        if scene_change_score > self.threshold * 20:  # Adjusted threshold
                            boundaries.append((frame_number, scene_change_score / 20.0))
            
            prev_gray = gray.copy()
            frame_number += sample_interval
            
            # Yield control periodically
            if len(boundaries) % 15 == 0:
                await asyncio.sleep(0.01)
        
        return boundaries
    
    async def _detect_content_aware_scenes(self, cap: cv2.VideoCapture, fps: float,
                                          total_frames: int) -> List[Tuple[int, float]]:
        """Detect scene boundaries using content-aware analysis"""
        
        boundaries = [(0, 1.0)]
        frame_features = []
        frame_numbers = []
        
        # Sample frames for analysis
        sample_interval = max(1, int(fps))  # 1 sample per second
        frame_number = 0
        
        # Extract features from sampled frames
        while frame_number < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            if not ret:
                break
            
            # Extract multiple features
            features = await self._extract_content_features(frame)
            if features is not None:
                frame_features.append(features)
                frame_numbers.append(frame_number)
            
            frame_number += sample_interval
            
            # Yield control periodically
            if len(frame_features) % 10 == 0:
                await asyncio.sleep(0.01)
        
        if len(frame_features) < 3:
            return boundaries
        
        # Convert to numpy array
        feature_matrix = np.array(frame_features)
        
        # Normalize features
        feature_matrix = (feature_matrix - np.mean(feature_matrix, axis=0)) / (np.std(feature_matrix, axis=0) + 1e-8)
        
        # Calculate pairwise distances
        distances = pdist(feature_matrix, metric='euclidean')
        distance_matrix = squareform(distances)
        
        # Find scene boundaries using clustering or thresholding
        scene_boundaries = await self._find_content_boundaries(
            distance_matrix, frame_numbers, fps
        )
        
        boundaries.extend(scene_boundaries)
        
        return boundaries
    
    async def _extract_content_features(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Extract content features from a frame"""
        
        try:
            features = []
            
            # Color features
            mean_color = np.mean(frame, axis=(0, 1))
            features.extend(mean_color)
            
            # Brightness and contrast
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            features.append(np.mean(gray))
            features.append(np.std(gray))
            
            # Edge features
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            features.append(edge_density)
            
            # Texture features (using LBP-like approach)
            texture_features = await self._calculate_texture_features(gray)
            features.extend(texture_features)
            
            # Histogram features
            hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            hist = hist.flatten()
            hist = hist / (np.sum(hist) + 1e-8)  # Normalize
            features.extend(hist[:50])  # Use first 50 bins to keep feature vector manageable
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Error extracting content features: {e}")
            return None
    
    async def _calculate_texture_features(self, gray_frame: np.ndarray) -> List[float]:
        """Calculate texture features using gradient and statistical methods"""
        
        try:
            features = []
            
            # Gradient features
            grad_x = cv2.Sobel(gray_frame, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray_frame, cv2.CV_64F, 0, 1, ksize=3)
            
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            features.append(np.mean(gradient_magnitude))
            features.append(np.std(gradient_magnitude))
            
            # Local standard deviation (texture measure)
            kernel = np.ones((5, 5), np.float32) / 25
            local_mean = cv2.filter2D(gray_frame.astype(np.float32), -1, kernel)
            local_sq_mean = cv2.filter2D((gray_frame.astype(np.float32))**2, -1, kernel)
            local_variance = local_sq_mean - local_mean**2
            local_std = np.sqrt(np.maximum(local_variance, 0))
            
            features.append(np.mean(local_std))
            features.append(np.std(local_std))
            
            return features
            
        except Exception as e:
            logger.error(f"Error calculating texture features: {e}")
            return [0.0, 0.0, 0.0, 0.0]
    
    async def _find_content_boundaries(self, distance_matrix: np.ndarray,
                                      frame_numbers: List[int], fps: float) -> List[Tuple[int, float]]:
        """Find scene boundaries from content feature distance matrix"""
        
        boundaries = []
        
        try:
            # Calculate frame-to-frame distances
            frame_distances = []
            for i in range(1, len(distance_matrix)):
                frame_distances.append(distance_matrix[i-1, i])
            
            # Find peaks in distance function
            if len(frame_distances) > 5:
                # Use median + threshold to find significant changes
                median_distance = np.median(frame_distances)
                threshold = median_distance + self.threshold * np.std(frame_distances)
                
                for i, distance in enumerate(frame_distances):
                    if distance > threshold:
                        frame_idx = i + 1  # +1 because we started from index 1
                        if frame_idx < len(frame_numbers):
                            frame_number = frame_numbers[frame_idx]
                            confidence = min(distance / (threshold + 1e-8), 1.0)
                            boundaries.append((frame_number, confidence))
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Error finding content boundaries: {e}")
            return []
    
    async def _detect_audio_scenes(self, video_path: str, fps: float, 
                                  duration: float) -> List[Tuple[int, float]]:
        """Detect scene boundaries using audio analysis"""
        
        boundaries = [(0, 1.0)]
        
        try:
            # Extract audio features using FFmpeg
            audio_features = await self._extract_audio_features(video_path)
            
            if not audio_features:
                return boundaries
            
            # Analyze audio for scene changes
            scene_boundaries = await self._analyze_audio_for_scenes(audio_features, fps, duration)
            boundaries.extend(scene_boundaries)
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Error detecting audio scenes: {e}")
            return boundaries
    
    async def _extract_audio_features(self, video_path: str) -> Optional[Dict]:
        """Extract audio features from video"""
        
        try:
            # Use FFmpeg to extract audio analysis
            cmd = [
                'ffmpeg', '-i', video_path,
                '-af', 'silencedetect=noise=-30dB:duration=0.5',
                '-f', 'null', '-'
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            # Parse silence detection output
            silence_periods = []
            lines = stderr.decode().split('\n')
            
            for line in lines:
                if 'silence_start' in line:
                    try:
                        start_time = float(line.split('silence_start: ')[1].split()[0])
                        silence_periods.append({'start': start_time, 'type': 'silence_start'})
                    except (IndexError, ValueError):
                        continue
                elif 'silence_end' in line:
                    try:
                        end_time = float(line.split('silence_end: ')[1].split()[0])
                        if silence_periods and silence_periods[-1]['type'] == 'silence_start':
                            silence_periods[-1]['end'] = end_time
                            silence_periods[-1]['type'] = 'silence_period'
                    except (IndexError, ValueError):
                        continue
            
            return {'silence_periods': silence_periods}
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {e}")
            return None
    
    async def _analyze_audio_for_scenes(self, audio_features: Dict, fps: float,
                                       duration: float) -> List[Tuple[int, float]]:
        """Analyze audio features to find scene boundaries"""
        
        boundaries = []
        
        try:
            silence_periods = audio_features.get('silence_periods', [])
            
            for silence in silence_periods:
                if silence.get('type') == 'silence_period':
                    # Consider silence periods as potential scene boundaries
                    silence_duration = silence.get('end', 0) - silence.get('start', 0)
                    
                    if silence_duration > 1.0:  # At least 1 second of silence
                        # Use end of silence as scene boundary
                        boundary_time = silence.get('end', 0)
                        boundary_frame = int(boundary_time * fps)
                        confidence = min(silence_duration / 3.0, 1.0)  # Longer silence = higher confidence
                        
                        boundaries.append((boundary_frame, confidence))
            
            return boundaries
            
        except Exception as e:
            logger.error(f"Error analyzing audio for scenes: {e}")
            return []
    
    async def _detect_combined_scenes(self, cap: cv2.VideoCapture, video_path: str,
                                     fps: float, total_frames: int) -> List[Tuple[int, float]]:
        """Detect scenes using combined visual and audio analysis"""
        
        try:
            # Get visual boundaries
            visual_boundaries = await self._detect_histogram_scenes(cap, fps, total_frames)
            
            # Reset video capture
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            # Get content-aware boundaries
            content_boundaries = await self._detect_content_aware_scenes(cap, fps, total_frames)
            
            # Get audio boundaries
            duration = total_frames / fps if fps > 0 else 0
            audio_boundaries = await self._detect_audio_scenes(video_path, fps, duration)
            
            # Combine and weight boundaries
            all_boundaries = []
            
            # Add visual boundaries with weight
            for frame, confidence in visual_boundaries:
                all_boundaries.append((frame, confidence * 0.4, 'visual'))
            
            # Add content boundaries with weight
            for frame, confidence in content_boundaries:
                all_boundaries.append((frame, confidence * 0.4, 'content'))
            
            # Add audio boundaries with weight
            for frame, confidence in audio_boundaries:
                all_boundaries.append((frame, confidence * 0.2, 'audio'))
            
            # Merge nearby boundaries
            merged_boundaries = await self._merge_nearby_boundaries(all_boundaries, fps)
            
            return merged_boundaries
            
        except Exception as e:
            logger.error(f"Error in combined scene detection: {e}")
            return [(0, 1.0)]
    
    async def _merge_nearby_boundaries(self, boundaries: List[Tuple], 
                                      fps: float, merge_threshold: float = 2.0) -> List[Tuple[int, float]]:
        """Merge scene boundaries that are close together"""
        
        if not boundaries:
            return [(0, 1.0)]
        
        # Sort boundaries by frame number
        boundaries.sort(key=lambda x: x[0])
        
        merged = [(0, 1.0)]  # Always start with first frame
        
        for frame, confidence, source in boundaries[1:]:
            last_frame = merged[-1][0]
            time_diff = (frame - last_frame) / fps
            
            # If boundaries are close, merge them
            if time_diff < merge_threshold:
                # Update last boundary with higher confidence
                if confidence > merged[-1][1]:
                    merged[-1] = (frame, confidence)
            else:
                merged.append((frame, confidence))
        
        return merged
    
    async def _create_scene_segments(self, job_id: str, boundaries: List[Tuple[int, float]],
                                    fps: float, total_duration: float) -> List[Dict]:
        """Convert scene boundaries to scene segments"""
        
        scenes = []
        
        if not boundaries:
            return scenes
        
        # Sort boundaries by frame number
        boundaries.sort(key=lambda x: x[0])
        
        # Ensure we have a boundary at the end
        last_frame = int(total_duration * fps)
        if not boundaries or boundaries[-1][0] < last_frame - fps:  # If last boundary is not close to end
            boundaries.append((last_frame, 0.5))
        
        # Create scene segments
        for i in range(len(boundaries) - 1):
            start_frame, start_confidence = boundaries[i]
            end_frame, _ = boundaries[i + 1]
            
            start_time = start_frame / fps
            end_time = end_frame / fps
            duration = end_time - start_time
            
            # Skip very short scenes
            if duration < self.min_scene_duration:
                continue
            
            # Limit total number of scenes
            if len(scenes) >= self.max_scenes:
                break
            
            scene = {
                'scene_number': len(scenes) + 1,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'confidence': start_confidence,
                'start_frame': start_frame,
                'end_frame': end_frame
            }
            
            # Add scene analysis
            await self._analyze_scene_content(job_id, scene)
            
            scenes.append(scene)
        
        return scenes
    
    async def _analyze_scene_content(self, job_id: str, scene: Dict):
        """Analyze scene content and add metadata"""
        
        try:
            # This is a placeholder for scene content analysis
            # In a full implementation, you would:
            # 1. Extract representative frames from the scene
            # 2. Analyze dominant colors
            # 3. Estimate motion intensity
            # 4. Analyze audio characteristics
            # 5. Generate scene description
            
            # For now, add basic metadata
            scene['description'] = f"Scene {scene['scene_number']}: {scene['duration']:.1f}s"
            scene['dominant_colors'] = [[128, 128, 128]]  # Placeholder
            scene['motion_intensity'] = 0.5  # Placeholder
            scene['audio_features'] = {'has_speech': False, 'has_music': False}  # Placeholder
            
        except Exception as e:
            logger.error(f"Error analyzing scene content: {e}")
    
    async def generate_scene_preview(self, job_id: str, scene_id: str, 
                                    output_path: str) -> Optional[str]:
        """Generate a preview video for a specific scene"""
        
        try:
            # Get scene information
            scenes = await self.db_manager.execute_query("""
                SELECT * FROM video_scenes WHERE scene_id = $1
            """, scene_id)
            
            if not scenes:
                return None
            
            scene = scenes[0]
            
            # Get original video path from job
            job = await self.db_manager.get_job_details(job_id)
            if not job:
                return None
            
            video_path = job['file_path']
            
            # Create scene preview using FFmpeg
            start_time = scene['start_time_seconds']
            duration = scene['duration_seconds']
            
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', settings.VIDEO_CODEC,
                '-c:a', settings.AUDIO_CODEC,
                '-crf', str(settings.CRF_VALUE),
                '-preset', 'fast',
                '-movflags', 'faststart',
                '-y',
                output_path
            ]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(output_path):
                logger.debug(f"Created scene preview: {output_path}")
                return output_path
            else:
                logger.error(f"FFmpeg failed for scene preview: {stderr.decode()}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating scene preview: {e}")
            return None
    
    async def create_scene_timeline(self, job_id: str) -> Optional[Dict]:
        """Create a visual timeline of all scenes"""
        
        try:
            # Get all scenes for the job
            scenes = await self.db_manager.get_job_scenes(job_id)
            
            if not scenes:
                return None
            
            # Create timeline data
            timeline = {
                'job_id': job_id,
                'total_scenes': len(scenes),
                'total_duration': sum(scene['duration_seconds'] for scene in scenes),
                'scenes': []
            }
            
            for i, scene in enumerate(scenes):
                scene_info = {
                    'scene_id': scene['scene_id'],
                    'scene_number': i + 1,
                    'start_time': scene['start_time_seconds'],
                    'end_time': scene['end_time_seconds'],
                    'duration': scene['duration_seconds'],
                    'confidence': scene.get('confidence_score', 0.5),
                    'description': scene.get('description', f"Scene {i + 1}"),
                    'dominant_colors': scene.get('dominant_colors', []),
                    'motion_intensity': scene.get('motion_intensity', 0.5)
                }
                
                timeline['scenes'].append(scene_info)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Error creating scene timeline: {e}")
            return None