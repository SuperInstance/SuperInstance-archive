#!/usr/bin/env python3
"""
ActiveLog Camera Device Agent
Handles intelligent camera capture, local processing, and batch upload
"""

import asyncio
import cv2
import json
import logging
import os
import sys
import time
import threading
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import deque
import sqlite3
from dataclasses import dataclass, asdict

import numpy as np
import requests
from PIL import Image, ImageEnhance, ExifTags
from queue import Queue, Empty

# Add potential virtual environment paths
possible_venv_paths = [
    Path.home() / "activelog-venv" / "lib" / "python3.11" / "site-packages",
    Path("/opt/activelog") / "venv" / "lib" / "python3.11" / "site-packages"
]

for venv_path in possible_venv_paths:
    if venv_path.exists():
        sys.path.insert(0, str(venv_path))
        break

@dataclass
class CameraFrame:
    """Represents a captured camera frame with metadata"""
    timestamp: float
    frame_id: str
    width: int
    height: int
    channels: int
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    metadata: Optional[Dict] = None
    processed: bool = False
    uploaded: bool = False
    file_size: int = 0
    quality_score: float = 0.0
    motion_detected: bool = False
    faces_detected: int = 0
    objects_detected: List[str] = None

    def __post_init__(self):
        if self.objects_detected is None:
            self.objects_detected = []

@dataclass
class CameraConfig:
    """Camera configuration parameters"""
    device_id: int = 0
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 30
    format: str = "MJPG"
    auto_exposure: bool = True
    brightness: float = 0.5
    contrast: float = 0.5
    saturation: float = 0.5
    enable_auto_focus: bool = True
    enable_stabilization: bool = True


class MotionDetector:
    """Intelligent motion detection with noise filtering"""
    
    def __init__(self, sensitivity: float = 0.1, min_area: int = 500):
        self.sensitivity = sensitivity
        self.min_area = min_area
        self.background_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True, varThreshold=50
        )
        self.previous_frame = None
        self.motion_history = deque(maxlen=10)

    def detect_motion(self, frame: np.ndarray) -> Tuple[bool, float, List[Tuple[int, int, int, int]]]:
        """
        Detect motion in frame and return motion areas
        Returns: (motion_detected, motion_percentage, bounding_boxes)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        # Background subtraction method
        fg_mask = self.background_subtractor.apply(frame)
        
        # Morphological operations to clean up the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_areas = []
        total_motion_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_area:
                x, y, w, h = cv2.boundingRect(contour)
                motion_areas.append((x, y, w, h))
                total_motion_area += area
        
        frame_area = frame.shape[0] * frame.shape[1]
        motion_percentage = total_motion_area / frame_area
        motion_detected = motion_percentage > self.sensitivity
        
        # Update motion history
        self.motion_history.append(motion_detected)
        
        # Smooth motion detection (require motion in multiple consecutive frames)
        stable_motion = sum(self.motion_history) >= 3
        
        return stable_motion, motion_percentage, motion_areas


class QualityAnalyzer:
    """Analyzes image quality and applies intelligent filtering"""
    
    def __init__(self):
        self.blur_threshold = 100.0
        self.brightness_range = (30, 225)
        self.contrast_threshold = 20.0

    def analyze_quality(self, frame: np.ndarray) -> Dict:
        """Analyze image quality metrics"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Blur detection using Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # Brightness analysis
        brightness = np.mean(gray)
        
        # Contrast analysis
        contrast = gray.std()
        
        # Noise analysis
        noise_score = self._estimate_noise(gray)
        
        # Overall quality score (0-1)
        quality_score = self._calculate_quality_score(
            blur_score, brightness, contrast, noise_score
        )
        
        return {
            "blur_score": blur_score,
            "brightness": brightness,
            "contrast": contrast,
            "noise_score": noise_score,
            "quality_score": quality_score,
            "is_acceptable": quality_score > 0.5
        }

    def _estimate_noise(self, gray_frame: np.ndarray) -> float:
        """Estimate noise level in the image"""
        # Use high-pass filter to estimate noise
        kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
        filtered = cv2.filter2D(gray_frame, -1, kernel)
        return np.mean(np.abs(filtered))

    def _calculate_quality_score(self, blur: float, brightness: float, 
                                contrast: float, noise: float) -> float:
        """Calculate overall quality score"""
        # Normalize each metric (simplified scoring)
        blur_norm = min(1.0, blur / self.blur_threshold)
        brightness_norm = 1.0 if self.brightness_range[0] <= brightness <= self.brightness_range[1] else 0.5
        contrast_norm = min(1.0, contrast / self.contrast_threshold)
        noise_norm = max(0.0, 1.0 - (noise / 50.0))  # Lower noise is better
        
        # Weighted average
        weights = [0.3, 0.2, 0.3, 0.2]  # blur, brightness, contrast, noise
        return np.average([blur_norm, brightness_norm, contrast_norm, noise_norm], weights=weights)


class BatchUploader:
    """Handles intelligent batch uploading with compression and deduplication"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.upload_queue = Queue()
        self.batch_size = config.get("batch_size", 10)
        self.max_batch_age = config.get("max_batch_age", 300)  # 5 minutes
        self.compression_quality = config.get("compression_quality", 85)
        self.enable_deduplication = config.get("enable_deduplication", True)
        self.server_url = config.get("server_url", "https://api.activelog.ai")
        
        self.current_batch = []
        self.batch_start_time = time.time()
        self.upload_stats = {
            "total_uploads": 0,
            "failed_uploads": 0,
            "bytes_uploaded": 0,
            "deduplicated_files": 0
        }
        
        self.logger = logging.getLogger(__name__)

    async def queue_for_upload(self, frame: CameraFrame):
        """Queue a frame for batch upload"""
        # Add to current batch
        self.current_batch.append(frame)
        
        # Check if batch is ready for upload
        if (len(self.current_batch) >= self.batch_size or 
            time.time() - self.batch_start_time > self.max_batch_age):
            await self.upload_batch()

    async def upload_batch(self):
        """Upload the current batch of frames"""
        if not self.current_batch:
            return
        
        self.logger.info(f"Uploading batch of {len(self.current_batch)} frames")
        
        try:
            # Prepare batch data
            batch_data = await self.prepare_batch_data(self.current_batch)
            
            # Upload to server
            success = await self.send_batch_to_server(batch_data)
            
            if success:
                # Mark frames as uploaded
                for frame in self.current_batch:
                    frame.uploaded = True
                
                self.upload_stats["total_uploads"] += len(self.current_batch)
                self.logger.info(f"Successfully uploaded batch of {len(self.current_batch)} frames")
            else:
                self.upload_stats["failed_uploads"] += len(self.current_batch)
                self.logger.error(f"Failed to upload batch of {len(self.current_batch)} frames")
            
        except Exception as e:
            self.logger.error(f"Batch upload error: {e}")
            self.upload_stats["failed_uploads"] += len(self.current_batch)
        finally:
            # Reset batch
            self.current_batch = []
            self.batch_start_time = time.time()

    async def prepare_batch_data(self, frames: List[CameraFrame]) -> Dict:
        """Prepare batch data for upload with compression and deduplication"""
        batch_files = []
        deduplicated_count = 0
        seen_hashes = set()
        
        for frame in frames:
            if not frame.file_path or not os.path.exists(frame.file_path):
                continue
            
            # Calculate file hash for deduplication
            file_hash = None
            if self.enable_deduplication:
                file_hash = self._calculate_file_hash(frame.file_path)
                if file_hash in seen_hashes:
                    deduplicated_count += 1
                    continue
                seen_hashes.add(file_hash)
            
            # Compress image if needed
            compressed_path = await self._compress_image(frame.file_path)
            
            file_data = {
                "frame_id": frame.frame_id,
                "timestamp": frame.timestamp,
                "file_path": compressed_path,
                "file_hash": file_hash,
                "metadata": asdict(frame),
                "compressed": compressed_path != frame.file_path
            }
            batch_files.append(file_data)
        
        self.upload_stats["deduplicated_files"] += deduplicated_count
        
        return {
            "batch_id": f"batch_{int(time.time())}_{len(frames)}",
            "device_id": self.config.get("device_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "files": batch_files,
            "total_files": len(batch_files),
            "deduplicated_count": deduplicated_count
        }

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    async def _compress_image(self, image_path: str) -> str:
        """Compress image if it's above size threshold"""
        try:
            # Check file size
            file_size = os.path.getsize(image_path)
            max_size = self.config.get("max_file_size", 1024 * 1024)  # 1MB default
            
            if file_size <= max_size:
                return image_path  # No compression needed
            
            # Create compressed version
            compressed_path = image_path.replace('.jpg', '_compressed.jpg')
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save with compression
                img.save(compressed_path, 'JPEG', quality=self.compression_quality, optimize=True)
            
            # Check if compression was effective
            compressed_size = os.path.getsize(compressed_path)
            if compressed_size < file_size:
                return compressed_path
            else:
                # Remove compressed file if it's not smaller
                os.remove(compressed_path)
                return image_path
                
        except Exception as e:
            self.logger.error(f"Image compression failed: {e}")
            return image_path

    async def send_batch_to_server(self, batch_data: Dict) -> bool:
        """Send batch data to server"""
        try:
            # Prepare multipart upload
            files = []
            form_data = {
                "batch_metadata": json.dumps({
                    k: v for k, v in batch_data.items() if k != "files"
                })
            }
            
            # Add files to upload
            for i, file_data in enumerate(batch_data["files"]):
                file_path = file_data["file_path"]
                if os.path.exists(file_path):
                    files.append((
                        f"file_{i}",
                        (f"{file_data['frame_id']}.jpg", open(file_path, 'rb'), 'image/jpeg')
                    ))
                    form_data[f"metadata_{i}"] = json.dumps(file_data["metadata"])
            
            # Send HTTP request
            response = requests.post(
                f"{self.server_url}/api/camera/batch-upload",
                data=form_data,
                files=files,
                headers={"X-Device-ID": self.config.get("device_id", "unknown")},
                timeout=60
            )
            
            # Close file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()
            
            if response.status_code == 200:
                result = response.json()
                uploaded_bytes = sum(os.path.getsize(f["file_path"]) for f in batch_data["files"])
                self.upload_stats["bytes_uploaded"] += uploaded_bytes
                return True
            else:
                self.logger.error(f"Upload failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Upload request failed: {e}")
            return False

    def get_upload_stats(self) -> Dict:
        """Get upload statistics"""
        return self.upload_stats.copy()


class CameraDatabase:
    """SQLite database for local frame metadata storage"""
    
    def __init__(self, db_path: str = "/var/lib/activelog/camera.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the camera database"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS frames (
                    frame_id TEXT PRIMARY KEY,
                    timestamp REAL,
                    width INTEGER,
                    height INTEGER,
                    channels INTEGER,
                    file_path TEXT,
                    thumbnail_path TEXT,
                    metadata TEXT,
                    processed BOOLEAN,
                    uploaded BOOLEAN,
                    file_size INTEGER,
                    quality_score REAL,
                    motion_detected BOOLEAN,
                    faces_detected INTEGER,
                    objects_detected TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON frames(timestamp)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_uploaded ON frames(uploaded)
            ''')

    def store_frame(self, frame: CameraFrame):
        """Store frame metadata in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO frames 
                (frame_id, timestamp, width, height, channels, file_path, 
                 thumbnail_path, metadata, processed, uploaded, file_size,
                 quality_score, motion_detected, faces_detected, objects_detected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                frame.frame_id, frame.timestamp, frame.width, frame.height,
                frame.channels, frame.file_path, frame.thumbnail_path,
                json.dumps(frame.metadata) if frame.metadata else None,
                frame.processed, frame.uploaded, frame.file_size,
                frame.quality_score, frame.motion_detected, frame.faces_detected,
                json.dumps(frame.objects_detected)
            ))

    def get_unuploaded_frames(self, limit: int = 100) -> List[CameraFrame]:
        """Get frames that haven't been uploaded yet"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT * FROM frames 
                WHERE uploaded = 0 AND file_path IS NOT NULL
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (limit,))
            
            frames = []
            for row in cursor.fetchall():
                frame = CameraFrame(
                    timestamp=row[1],
                    frame_id=row[0],
                    width=row[2],
                    height=row[3],
                    channels=row[4],
                    file_path=row[5],
                    thumbnail_path=row[6],
                    metadata=json.loads(row[7]) if row[7] else None,
                    processed=bool(row[8]),
                    uploaded=bool(row[9]),
                    file_size=row[10],
                    quality_score=row[11],
                    motion_detected=bool(row[12]),
                    faces_detected=row[13],
                    objects_detected=json.loads(row[14]) if row[14] else []
                )
                frames.append(frame)
            
            return frames

    def cleanup_old_frames(self, days: int = 30):
        """Clean up frames older than specified days"""
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get files to delete
            cursor = conn.execute('''
                SELECT file_path, thumbnail_path FROM frames 
                WHERE timestamp < ? AND uploaded = 1
            ''', (cutoff_time,))
            
            files_to_delete = cursor.fetchall()
            
            # Delete files
            for file_path, thumbnail_path in files_to_delete:
                for path in [file_path, thumbnail_path]:
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                        except:
                            pass
            
            # Delete database records
            conn.execute('DELETE FROM frames WHERE timestamp < ? AND uploaded = 1', (cutoff_time,))


class CameraAgent:
    """Main camera agent for intelligent capture and processing"""
    
    def __init__(self, config_path: str = "/etc/activelog/camera.conf"):
        self.config_path = config_path
        self.config = self.load_config()
        self.device_id = self.config.get("device", {}).get("id", "camera_device")
        self.running = False
        
        # Initialize logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.camera = None
        self.camera_config = CameraConfig()
        self.motion_detector = MotionDetector()
        self.quality_analyzer = QualityAnalyzer()
        self.batch_uploader = BatchUploader(self.config.get("upload", {}))
        self.database = CameraDatabase()
        
        # Capture settings
        self.capture_enabled = True
        self.motion_only_mode = self.config.get("capture", {}).get("motion_only", False)
        self.min_quality_threshold = self.config.get("capture", {}).get("min_quality", 0.3)
        self.capture_interval = self.config.get("capture", {}).get("interval", 1.0)
        
        # Storage paths
        self.data_dir = Path(self.config.get("storage", {}).get("data_dir", "/var/lib/activelog/camera"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "images").mkdir(exist_ok=True)
        (self.data_dir / "thumbnails").mkdir(exist_ok=True)
        
        self.logger.info(f"CameraAgent initialized for device {self.device_id}")

    def load_config(self) -> Dict:
        """Load configuration from file"""
        default_config = {
            "device": {"id": "camera_device"},
            "camera": {
                "device_id": 0,
                "resolution": [1920, 1080],
                "fps": 30,
                "format": "MJPG"
            },
            "capture": {
                "motion_only": False,
                "min_quality": 0.3,
                "interval": 1.0,
                "enable_thumbnails": True
            },
            "processing": {
                "enable_motion_detection": True,
                "enable_quality_analysis": True,
                "enable_face_detection": False,
                "enable_object_detection": False
            },
            "upload": {
                "batch_size": 10,
                "max_batch_age": 300,
                "compression_quality": 85,
                "enable_deduplication": True,
                "server_url": "https://api.activelog.ai"
            },
            "storage": {
                "data_dir": "/var/lib/activelog/camera",
                "max_storage_gb": 10,
                "cleanup_days": 30
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    self._merge_config(default_config, loaded_config)
            
            return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def _merge_config(self, default: Dict, loaded: Dict):
        """Recursively merge loaded config with defaults"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(default[key], dict) and isinstance(value, dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
            else:
                default[key] = value

    def setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.INFO
        log_file = "/var/log/activelog/camera.log"
        
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

    async def start(self):
        """Start the camera agent"""
        self.logger.info("Starting ActiveLog Camera Agent")
        self.running = True
        
        try:
            # Initialize camera
            await self.initialize_camera()
            
            # Start background tasks
            tasks = [
                asyncio.create_task(self.capture_loop()),
                asyncio.create_task(self.upload_loop()),
                asyncio.create_task(self.cleanup_loop()),
                asyncio.create_task(self.monitoring_loop())
            ]
            
            self.logger.info("Camera agent started successfully")
            
            # Wait for shutdown
            await self.wait_for_shutdown()
            
        except Exception as e:
            self.logger.error(f"Error starting camera agent: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop the camera agent"""
        self.logger.info("Stopping Camera Agent")
        self.running = False
        
        if self.camera:
            self.camera.release()
        
        cv2.destroyAllWindows()
        self.logger.info("Camera agent stopped")

    async def initialize_camera(self):
        """Initialize camera with optimal settings"""
        camera_config = self.config.get("camera", {})
        
        device_id = camera_config.get("device_id", 0)
        self.camera = cv2.VideoCapture(device_id)
        
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open camera device {device_id}")
        
        # Set camera properties
        resolution = camera_config.get("resolution", [1920, 1080])
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        self.camera.set(cv2.CAP_PROP_FPS, camera_config.get("fps", 30))
        
        # Set format if specified
        format_str = camera_config.get("format", "MJPG")
        if format_str == "MJPG":
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        
        # Verify settings
        actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))
        
        self.logger.info(f"Camera initialized: {actual_width}x{actual_height} @ {actual_fps}fps")

    async def capture_loop(self):
        """Main capture loop with intelligent processing"""
        last_capture_time = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check capture interval
                if current_time - last_capture_time < self.capture_interval:
                    await asyncio.sleep(0.1)
                    continue
                
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    self.logger.warning("Failed to capture frame")
                    await asyncio.sleep(1)
                    continue
                
                # Process frame
                should_save = await self.process_frame(frame, current_time)
                
                if should_save:
                    await self.save_frame(frame, current_time)
                    last_capture_time = current_time
                
                await asyncio.sleep(0.01)  # Small delay to prevent CPU overload
                
            except Exception as e:
                self.logger.error(f"Capture loop error: {e}")
                await asyncio.sleep(1)

    async def process_frame(self, frame: np.ndarray, timestamp: float) -> bool:
        """Process frame and determine if it should be saved"""
        processing_config = self.config.get("processing", {})
        
        # Motion detection
        motion_detected = False
        motion_areas = []
        
        if processing_config.get("enable_motion_detection", True):
            motion_detected, motion_percentage, motion_areas = self.motion_detector.detect_motion(frame)
            
            # Skip frame if motion-only mode and no motion detected
            if self.motion_only_mode and not motion_detected:
                return False
        
        # Quality analysis
        quality_info = {}
        if processing_config.get("enable_quality_analysis", True):
            quality_info = self.quality_analyzer.analyze_quality(frame)
            
            # Skip frame if quality is too low
            if quality_info.get("quality_score", 1.0) < self.min_quality_threshold:
                return False
        
        return True

    async def save_frame(self, frame: np.ndarray, timestamp: float):
        """Save frame to disk and database"""
        frame_id = f"frame_{int(timestamp * 1000)}_{hash(frame.tobytes()) % 10000}"
        
        # Create file paths
        image_filename = f"{frame_id}.jpg"
        image_path = self.data_dir / "images" / image_filename
        thumbnail_path = None
        
        try:
            # Save main image
            cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            
            # Create thumbnail if enabled
            if self.config.get("capture", {}).get("enable_thumbnails", True):
                thumbnail_filename = f"{frame_id}_thumb.jpg"
                thumbnail_path = self.data_dir / "thumbnails" / thumbnail_filename
                
                # Resize for thumbnail (maintain aspect ratio)
                height, width = frame.shape[:2]
                max_thumb_size = 200
                if width > height:
                    new_width = max_thumb_size
                    new_height = int(height * max_thumb_size / width)
                else:
                    new_height = max_thumb_size
                    new_width = int(width * max_thumb_size / height)
                
                thumbnail = cv2.resize(frame, (new_width, new_height))
                cv2.imwrite(str(thumbnail_path), thumbnail, [cv2.IMWRITE_JPEG_QUALITY, 80])
            
            # Get file size
            file_size = os.path.getsize(image_path)
            
            # Create frame object
            camera_frame = CameraFrame(
                timestamp=timestamp,
                frame_id=frame_id,
                width=frame.shape[1],
                height=frame.shape[0],
                channels=frame.shape[2],
                file_path=str(image_path),
                thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
                file_size=file_size,
                processed=True
            )
            
            # Store in database
            self.database.store_frame(camera_frame)
            
            # Queue for upload
            await self.batch_uploader.queue_for_upload(camera_frame)
            
            self.logger.debug(f"Saved frame {frame_id} ({file_size} bytes)")
            
        except Exception as e:
            self.logger.error(f"Failed to save frame: {e}")

    async def upload_loop(self):
        """Background upload processing loop"""
        while self.running:
            try:
                # Process any pending uploads
                unuploaded_frames = self.database.get_unuploaded_frames(50)
                
                for frame in unuploaded_frames:
                    if not self.running:
                        break
                    
                    await self.batch_uploader.queue_for_upload(frame)
                
                # Force upload any remaining batches
                if self.batch_uploader.current_batch:
                    await self.batch_uploader.upload_batch()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Upload loop error: {e}")
                await asyncio.sleep(30)

    async def cleanup_loop(self):
        """Background cleanup processing"""
        while self.running:
            try:
                # Clean up old frames
                cleanup_days = self.config.get("storage", {}).get("cleanup_days", 30)
                self.database.cleanup_old_frames(cleanup_days)
                
                # Check storage usage
                await self.check_storage_usage()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)

    async def check_storage_usage(self):
        """Check and manage storage usage"""
        max_storage_gb = self.config.get("storage", {}).get("max_storage_gb", 10)
        max_storage_bytes = max_storage_gb * 1024 * 1024 * 1024
        
        # Calculate current usage
        total_size = 0
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass
        
        # If over limit, clean up oldest files
        if total_size > max_storage_bytes:
            self.logger.warning(f"Storage usage {total_size / 1024**3:.2f}GB exceeds limit {max_storage_gb}GB")
            
            # Get oldest uploaded files
            with sqlite3.connect(self.database.db_path) as conn:
                cursor = conn.execute('''
                    SELECT file_path, thumbnail_path FROM frames 
                    WHERE uploaded = 1
                    ORDER BY timestamp ASC
                    LIMIT 100
                ''')
                
                files_to_delete = cursor.fetchall()
                bytes_freed = 0
                
                for file_path, thumbnail_path in files_to_delete:
                    for path in [file_path, thumbnail_path]:
                        if path and os.path.exists(path):
                            try:
                                file_size = os.path.getsize(path)
                                os.remove(path)
                                bytes_freed += file_size
                            except:
                                pass
                    
                    # Stop if we've freed enough space
                    if total_size - bytes_freed <= max_storage_bytes * 0.8:  # 80% of limit
                        break
                
                # Remove database records for deleted files
                conn.execute('''
                    DELETE FROM frames 
                    WHERE file_path IN ({})
                '''.format(','.join('?' * len(files_to_delete))), 
                [f[0] for f in files_to_delete])
                
                self.logger.info(f"Freed {bytes_freed / 1024**2:.2f}MB of storage")

    async def monitoring_loop(self):
        """Background monitoring and statistics"""
        while self.running:
            try:
                # Log statistics
                stats = await self.get_agent_stats()
                self.logger.info(f"Camera stats: {json.dumps(stats, indent=2)}")
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(300)

    async def get_agent_stats(self) -> Dict:
        """Get comprehensive agent statistics"""
        # Database stats
        with sqlite3.connect(self.database.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM frames')
            total_frames = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT COUNT(*) FROM frames WHERE uploaded = 1')
            uploaded_frames = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT SUM(file_size) FROM frames')
            total_size = cursor.fetchone()[0] or 0
        
        # Upload stats
        upload_stats = self.batch_uploader.get_upload_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.device_id,
            "total_frames_captured": total_frames,
            "frames_uploaded": uploaded_frames,
            "pending_upload": total_frames - uploaded_frames,
            "total_storage_bytes": total_size,
            "upload_stats": upload_stats,
            "camera_active": self.camera is not None and self.camera.isOpened(),
            "capture_enabled": self.capture_enabled
        }

    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        import signal
        
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        while self.running:
            await asyncio.sleep(1)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Camera Agent")
    parser.add_argument("--config", default="/etc/activelog/camera.conf",
                        help="Configuration file path")
    parser.add_argument("--device", type=int, default=0,
                        help="Camera device ID")
    parser.add_argument("--motion-only", action="store_true",
                        help="Only capture when motion is detected")
    
    args = parser.parse_args()
    
    # Create and run the agent
    agent = CameraAgent(args.config)
    
    # Override config with command line arguments
    if args.device != 0:
        agent.config["camera"]["device_id"] = args.device
    if args.motion_only:
        agent.motion_only_mode = True
    
    try:
        asyncio.run(agent.start())
    except KeyboardInterrupt:
        print("Camera agent stopped by user")
    except Exception as e:
        print(f"Camera agent error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()