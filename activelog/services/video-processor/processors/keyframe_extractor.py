"""
Keyframe Extractor - Extracts significant frames from videos using OpenCV
"""

import cv2
import numpy as np
import logging
import os
from typing import List, Dict, Tuple, Optional, AsyncGenerator
import asyncio
from datetime import datetime
import hashlib

from ..core.config import settings
from ..core.database import DatabaseManager

logger = logging.getLogger('video_processor.keyframes')

class KeyframeExtractor:
    """Extracts keyframes from videos using various algorithms"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.temp_path = settings.TEMP_PATH
        
        # Keyframe extraction parameters
        self.interval_seconds = settings.KEYFRAME_INTERVAL_SECONDS
        self.max_keyframes = settings.MAX_KEYFRAMES_PER_VIDEO
        self.quality = settings.KEYFRAME_QUALITY
        self.target_size = settings.KEYFRAME_SIZE
        
        logger.info("Keyframe extractor initialized")
    
    async def extract_keyframes(self, job_id: str, video_path: str, 
                               method: str = "interval") -> List[Dict]:
        """
        Extract keyframes from video using specified method
        
        Args:
            job_id: Processing job ID
            video_path: Path to video file
            method: Extraction method ('interval', 'difference', 'optical_flow', 'histogram')
        """
        
        keyframes = []
        
        try:
            logger.info(f"Starting keyframe extraction for job {job_id} using method: {method}")
            
            # Create job-specific output directory
            output_dir = os.path.join(self.temp_path, f"keyframes_{job_id}")
            os.makedirs(output_dir, exist_ok=True)
            
            # Open video capture
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open video file: {video_path}")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"Video properties: {total_frames} frames, {fps} FPS, {duration:.2f}s duration")
            
            # Extract keyframes based on method
            if method == "interval":
                keyframes = await self._extract_interval_keyframes(
                    cap, job_id, output_dir, fps, total_frames
                )
            elif method == "difference":
                keyframes = await self._extract_difference_keyframes(
                    cap, job_id, output_dir, fps, total_frames
                )
            elif method == "optical_flow":
                keyframes = await self._extract_optical_flow_keyframes(
                    cap, job_id, output_dir, fps, total_frames
                )
            elif method == "histogram":
                keyframes = await self._extract_histogram_keyframes(
                    cap, job_id, output_dir, fps, total_frames
                )
            else:
                raise ValueError(f"Unknown keyframe extraction method: {method}")
            
            cap.release()
            
            # Save keyframes to database
            for keyframe_data in keyframes:
                await self.db_manager.save_keyframe(
                    job_id=job_id,
                    timestamp=keyframe_data['timestamp'],
                    frame_number=keyframe_data['frame_number'],
                    file_path=keyframe_data['file_path'],
                    thumbnail_path=keyframe_data.get('thumbnail_path'),
                    width=keyframe_data.get('width'),
                    height=keyframe_data.get('height'),
                    confidence=keyframe_data.get('confidence'),
                    features=keyframe_data.get('features')
                )
            
            logger.info(f"Extracted {len(keyframes)} keyframes for job {job_id}")
            return keyframes
            
        except Exception as e:
            logger.error(f"Keyframe extraction failed for job {job_id}: {e}")
            raise
    
    async def _extract_interval_keyframes(self, cap: cv2.VideoCapture, job_id: str,
                                         output_dir: str, fps: float, 
                                         total_frames: int) -> List[Dict]:
        """Extract keyframes at regular intervals"""
        
        keyframes = []
        frame_interval = max(1, int(fps * self.interval_seconds))
        
        frame_number = 0
        while frame_number < total_frames and len(keyframes) < self.max_keyframes:
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_number / fps
            
            # Save keyframe
            keyframe_data = await self._save_keyframe_image(
                frame, frame_number, timestamp, job_id, output_dir
            )
            
            if keyframe_data:
                keyframes.append(keyframe_data)
            
            frame_number += frame_interval
            
            # Yield control periodically
            if len(keyframes) % 10 == 0:
                await asyncio.sleep(0.01)
        
        return keyframes
    
    async def _extract_difference_keyframes(self, cap: cv2.VideoCapture, job_id: str,
                                           output_dir: str, fps: float,
                                           total_frames: int) -> List[Dict]:
        """Extract keyframes based on frame difference threshold"""
        
        keyframes = []
        prev_frame = None
        frame_number = 0
        difference_threshold = 0.3  # Adjustable threshold
        
        while frame_number < total_frames and len(keyframes) < self.max_keyframes:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_number / fps
            
            # Convert to grayscale for comparison
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_frame is not None:
                # Calculate frame difference
                diff = cv2.absdiff(prev_frame, gray_frame)
                diff_score = np.mean(diff) / 255.0
                
                # Save keyframe if difference is significant
                if diff_score > difference_threshold:
                    keyframe_data = await self._save_keyframe_image(
                        frame, frame_number, timestamp, job_id, output_dir,
                        confidence=diff_score
                    )
                    
                    if keyframe_data:
                        keyframes.append(keyframe_data)
            else:
                # Always save first frame
                keyframe_data = await self._save_keyframe_image(
                    frame, frame_number, timestamp, job_id, output_dir,
                    confidence=1.0
                )
                
                if keyframe_data:
                    keyframes.append(keyframe_data)
            
            prev_frame = gray_frame.copy()
            frame_number += 1
            
            # Yield control periodically
            if frame_number % 30 == 0:
                await asyncio.sleep(0.01)
        
        return keyframes
    
    async def _extract_optical_flow_keyframes(self, cap: cv2.VideoCapture, job_id: str,
                                             output_dir: str, fps: float,
                                             total_frames: int) -> List[Dict]:
        """Extract keyframes based on optical flow analysis"""
        
        keyframes = []
        prev_gray = None
        frame_number = 0
        motion_threshold = 5.0  # Motion magnitude threshold
        
        # Parameters for Lucas-Kanade optical flow
        lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        while frame_number < total_frames and len(keyframes) < self.max_keyframes:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_number / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if prev_gray is not None:
                # Detect corners for tracking
                corners = cv2.goodFeaturesToTrack(
                    prev_gray, maxCorners=100, qualityLevel=0.01, minDistance=10
                )
                
                if corners is not None:
                    # Calculate optical flow
                    next_corners, status, error = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, corners, None, **lk_params
                    )
                    
                    # Calculate motion magnitude
                    good_corners = corners[status == 1]
                    good_next_corners = next_corners[status == 1]
                    
                    if len(good_corners) > 0:
                        motion_vectors = good_next_corners - good_corners
                        motion_magnitude = np.mean(np.sqrt(
                            motion_vectors[:, 0]**2 + motion_vectors[:, 1]**2
                        ))
                        
                        # Save keyframe if significant motion detected
                        if motion_magnitude > motion_threshold:
                            keyframe_data = await self._save_keyframe_image(
                                frame, frame_number, timestamp, job_id, output_dir,
                                confidence=min(motion_magnitude / 20.0, 1.0)
                            )
                            
                            if keyframe_data:
                                keyframes.append(keyframe_data)
            else:
                # Always save first frame
                keyframe_data = await self._save_keyframe_image(
                    frame, frame_number, timestamp, job_id, output_dir,
                    confidence=1.0
                )
                
                if keyframe_data:
                    keyframes.append(keyframe_data)
            
            prev_gray = gray.copy()
            frame_number += 1
            
            # Yield control periodically
            if frame_number % 30 == 0:
                await asyncio.sleep(0.01)
        
        return keyframes
    
    async def _extract_histogram_keyframes(self, cap: cv2.VideoCapture, job_id: str,
                                          output_dir: str, fps: float,
                                          total_frames: int) -> List[Dict]:
        """Extract keyframes based on histogram comparison"""
        
        keyframes = []
        prev_hist = None
        frame_number = 0
        hist_threshold = 0.7  # Histogram correlation threshold
        
        while frame_number < total_frames and len(keyframes) < self.max_keyframes:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_number / fps
            
            # Calculate histogram
            hist = cv2.calcHist([frame], [0, 1, 2], None, [50, 50, 50], [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            if prev_hist is not None:
                # Calculate histogram correlation
                correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                
                # Save keyframe if histogram difference is significant
                if correlation < hist_threshold:
                    keyframe_data = await self._save_keyframe_image(
                        frame, frame_number, timestamp, job_id, output_dir,
                        confidence=1.0 - correlation
                    )
                    
                    if keyframe_data:
                        keyframes.append(keyframe_data)
            else:
                # Always save first frame
                keyframe_data = await self._save_keyframe_image(
                    frame, frame_number, timestamp, job_id, output_dir,
                    confidence=1.0
                )
                
                if keyframe_data:
                    keyframes.append(keyframe_data)
            
            prev_hist = hist.copy()
            frame_number += 1
            
            # Yield control periodically
            if frame_number % 30 == 0:
                await asyncio.sleep(0.01)
        
        return keyframes
    
    async def _save_keyframe_image(self, frame: np.ndarray, frame_number: int,
                                  timestamp: float, job_id: str, output_dir: str,
                                  confidence: float = None) -> Optional[Dict]:
        """Save keyframe image to disk and create thumbnail"""
        
        try:
            # Resize frame if necessary
            height, width = frame.shape[:2]
            if width > self.target_size[0] or height > self.target_size[1]:
                # Calculate scaling to maintain aspect ratio
                scale = min(self.target_size[0] / width, self.target_size[1] / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                height, width = new_height, new_width
            
            # Generate filename
            timestamp_str = f"{timestamp:.3f}".replace('.', '_')
            filename = f"keyframe_{frame_number:06d}_{timestamp_str}.jpg"
            file_path = os.path.join(output_dir, filename)
            
            # Save keyframe
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.quality]
            success = cv2.imwrite(file_path, frame, encode_params)
            
            if not success:
                logger.error(f"Failed to save keyframe: {file_path}")
                return None
            
            # Create thumbnail (smaller version)
            thumbnail_size = (160, 90)  # 16:9 aspect ratio thumbnail
            thumbnail = cv2.resize(frame, thumbnail_size, interpolation=cv2.INTER_AREA)
            thumbnail_filename = f"thumb_{frame_number:06d}_{timestamp_str}.jpg"
            thumbnail_path = os.path.join(output_dir, thumbnail_filename)
            cv2.imwrite(thumbnail_path, thumbnail, encode_params)
            
            # Extract visual features
            features = await self._extract_visual_features(frame)
            
            return {
                'frame_number': frame_number,
                'timestamp': timestamp,
                'file_path': file_path,
                'thumbnail_path': thumbnail_path,
                'width': width,
                'height': height,
                'confidence': confidence,
                'features': features
            }
            
        except Exception as e:
            logger.error(f"Error saving keyframe: {e}")
            return None
    
    async def _extract_visual_features(self, frame: np.ndarray) -> Dict:
        """Extract basic visual features from frame"""
        
        try:
            features = {}
            
            # Color statistics
            mean_color = np.mean(frame, axis=(0, 1))
            features['mean_color'] = [float(c) for c in mean_color]
            
            # Brightness
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            features['brightness'] = float(np.mean(gray))
            
            # Contrast (standard deviation of pixel intensities)
            features['contrast'] = float(np.std(gray))
            
            # Edge density
            edges = cv2.Canny(gray, 50, 150)
            features['edge_density'] = float(np.sum(edges > 0) / edges.size)
            
            # Dominant colors (simple clustering)
            features['dominant_colors'] = await self._get_dominant_colors(frame)
            
            # Image hash for similarity detection
            features['image_hash'] = self._calculate_image_hash(gray)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting visual features: {e}")
            return {}
    
    async def _get_dominant_colors(self, frame: np.ndarray, num_colors: int = 5) -> List[List[int]]:
        """Extract dominant colors using k-means clustering"""
        
        try:
            # Reshape frame for clustering
            data = frame.reshape((-1, 3))
            data = np.float32(data)
            
            # Apply k-means clustering
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = cv2.kmeans(data, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # Convert centers to integers
            centers = np.uint8(centers)
            
            # Sort by frequency
            unique, counts = np.unique(labels, return_counts=True)
            sorted_indices = np.argsort(-counts)
            
            dominant_colors = []
            for idx in sorted_indices:
                color = centers[idx]
                dominant_colors.append([int(c) for c in color])
            
            return dominant_colors
            
        except Exception as e:
            logger.error(f"Error extracting dominant colors: {e}")
            return []
    
    def _calculate_image_hash(self, gray_frame: np.ndarray) -> str:
        """Calculate perceptual hash of image for similarity detection"""
        
        try:
            # Resize to 8x8 for hash calculation
            resized = cv2.resize(gray_frame, (8, 8), interpolation=cv2.INTER_AREA)
            
            # Calculate average
            avg = np.mean(resized)
            
            # Create binary string
            binary_str = ''
            for pixel in resized.flatten():
                binary_str += '1' if pixel > avg else '0'
            
            # Convert to hexadecimal
            hash_value = hex(int(binary_str, 2))[2:]
            
            return hash_value
            
        except Exception as e:
            logger.error(f"Error calculating image hash: {e}")
            return ""
    
    async def find_similar_keyframes(self, job_id: str, similarity_threshold: float = 0.8) -> List[Dict]:
        """Find and group similar keyframes within a video"""
        
        try:
            # Get all keyframes for the job
            keyframes = await self.db_manager.get_job_keyframes(job_id)
            
            similar_groups = []
            processed_keyframes = set()
            
            for i, keyframe in enumerate(keyframes):
                if keyframe['keyframe_id'] in processed_keyframes:
                    continue
                
                similar_group = [keyframe]
                processed_keyframes.add(keyframe['keyframe_id'])
                
                # Compare with remaining keyframes
                for j, other_keyframe in enumerate(keyframes[i+1:], i+1):
                    if other_keyframe['keyframe_id'] in processed_keyframes:
                        continue
                    
                    # Compare features for similarity
                    similarity = await self._calculate_keyframe_similarity(keyframe, other_keyframe)
                    
                    if similarity > similarity_threshold:
                        similar_group.append(other_keyframe)
                        processed_keyframes.add(other_keyframe['keyframe_id'])
                
                if len(similar_group) > 1:
                    similar_groups.append({
                        'group_id': len(similar_groups),
                        'keyframes': similar_group,
                        'count': len(similar_group)
                    })
            
            logger.info(f"Found {len(similar_groups)} groups of similar keyframes for job {job_id}")
            return similar_groups
            
        except Exception as e:
            logger.error(f"Error finding similar keyframes: {e}")
            return []
    
    async def _calculate_keyframe_similarity(self, keyframe1: Dict, keyframe2: Dict) -> float:
        """Calculate similarity between two keyframes based on their features"""
        
        try:
            features1 = keyframe1.get('features', {})
            features2 = keyframe2.get('features', {})
            
            if not features1 or not features2:
                return 0.0
            
            similarities = []
            
            # Compare image hashes (if available)
            hash1 = features1.get('image_hash')
            hash2 = features2.get('image_hash')
            if hash1 and hash2:
                # Hamming distance for hash comparison
                if len(hash1) == len(hash2):
                    hamming_distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
                    hash_similarity = 1.0 - (hamming_distance / len(hash1))
                    similarities.append(hash_similarity)
            
            # Compare dominant colors
            colors1 = features1.get('dominant_colors', [])
            colors2 = features2.get('dominant_colors', [])
            if colors1 and colors2:
                color_similarity = self._compare_color_palettes(colors1, colors2)
                similarities.append(color_similarity)
            
            # Compare brightness and contrast
            if 'brightness' in features1 and 'brightness' in features2:
                brightness_diff = abs(features1['brightness'] - features2['brightness']) / 255.0
                brightness_similarity = 1.0 - brightness_diff
                similarities.append(brightness_similarity)
            
            if 'contrast' in features1 and 'contrast' in features2:
                contrast_diff = abs(features1['contrast'] - features2['contrast']) / 255.0
                contrast_similarity = 1.0 - min(contrast_diff, 1.0)
                similarities.append(contrast_similarity)
            
            # Return average similarity
            return np.mean(similarities) if similarities else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating keyframe similarity: {e}")
            return 0.0
    
    def _compare_color_palettes(self, colors1: List[List[int]], colors2: List[List[int]]) -> float:
        """Compare two color palettes for similarity"""
        
        try:
            if not colors1 or not colors2:
                return 0.0
            
            # Calculate distances between all color pairs
            similarities = []
            
            for color1 in colors1[:3]:  # Compare top 3 colors
                best_match = 0.0
                for color2 in colors2[:3]:
                    # Calculate Euclidean distance in RGB space
                    distance = np.sqrt(sum((c1 - c2) ** 2 for c1, c2 in zip(color1, color2)))
                    # Convert to similarity (max distance in RGB is ~442)
                    similarity = 1.0 - (distance / 442.0)
                    best_match = max(best_match, similarity)
                similarities.append(best_match)
            
            return np.mean(similarities) if similarities else 0.0
            
        except Exception as e:
            logger.error(f"Error comparing color palettes: {e}")
            return 0.0
    
    async def create_keyframe_montage(self, job_id: str, output_path: str,
                                     grid_size: Tuple[int, int] = (5, 4)) -> str:
        """Create a montage of keyframes for quick video overview"""
        
        try:
            # Get keyframes for the job
            keyframes = await self.db_manager.get_job_keyframes(job_id)
            
            if not keyframes:
                raise ValueError(f"No keyframes found for job {job_id}")
            
            # Limit number of keyframes to grid size
            max_keyframes = grid_size[0] * grid_size[1]
            if len(keyframes) > max_keyframes:
                # Select evenly distributed keyframes
                indices = np.linspace(0, len(keyframes) - 1, max_keyframes, dtype=int)
                keyframes = [keyframes[i] for i in indices]
            
            # Load keyframe images
            images = []
            target_width, target_height = 160, 90  # Thumbnail size
            
            for keyframe in keyframes:
                if os.path.exists(keyframe['thumbnail_path']):
                    img = cv2.imread(keyframe['thumbnail_path'])
                    if img is not None:
                        # Resize to standard thumbnail size
                        img = cv2.resize(img, (target_width, target_height))
                        images.append(img)
            
            if not images:
                raise ValueError("No valid keyframe images found")
            
            # Create montage
            rows = []
            for row in range(grid_size[1]):
                row_images = []
                for col in range(grid_size[0]):
                    idx = row * grid_size[0] + col
                    if idx < len(images):
                        row_images.append(images[idx])
                    else:
                        # Create blank image if we don't have enough keyframes
                        blank = np.zeros((target_height, target_width, 3), dtype=np.uint8)
                        row_images.append(blank)
                
                # Concatenate horizontally
                row_img = np.hstack(row_images)
                rows.append(row_img)
            
            # Concatenate vertically
            montage = np.vstack(rows)
            
            # Save montage
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            cv2.imwrite(output_path, montage)
            
            logger.info(f"Created keyframe montage for job {job_id}: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating keyframe montage: {e}")
            raise