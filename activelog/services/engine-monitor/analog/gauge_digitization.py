"""
Analog Gauge Digitization System
Computer vision and signal processing for digitizing analog marine gauges
"""

import asyncio
import logging
import cv2
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import json

logger = logging.getLogger(__name__)


class GaugeType(Enum):
    """Types of analog gauges"""
    CIRCULAR = "circular"
    LINEAR = "linear"
    DIGITAL_SEGMENT = "digital_segment"
    NEEDLE_POINTER = "needle_pointer"
    BAR_GRAPH = "bar_graph"


class CalibrationMethod(Enum):
    """Gauge calibration methods"""
    MANUAL_POINTS = "manual_points"
    AUTO_DETECTION = "auto_detection"
    TEMPLATE_MATCHING = "template_matching"
    EDGE_DETECTION = "edge_detection"


@dataclass
class GaugeCalibration:
    """Calibration data for analog gauge"""
    gauge_id: str
    gauge_type: GaugeType
    
    # Physical parameters
    center_x: int = 0
    center_y: int = 0
    radius: int = 100
    start_angle: float = -135.0  # degrees
    end_angle: float = 135.0  # degrees
    
    # Value mapping
    min_value: float = 0.0
    max_value: float = 100.0
    units: str = ""
    precision: int = 1
    
    # Visual recognition
    needle_color_hsv_min: Tuple[int, int, int] = (0, 50, 50)
    needle_color_hsv_max: Tuple[int, int, int] = (10, 255, 255)
    roi_x: int = 0
    roi_y: int = 0
    roi_width: int = 200
    roi_height: int = 200
    
    # Calibration points for accuracy
    calibration_points: List[Dict[str, float]] = field(default_factory=list)
    
    # Processing parameters
    blur_kernel_size: int = 5
    canny_threshold1: int = 50
    canny_threshold2: int = 150
    hough_threshold: int = 20
    min_line_length: int = 20
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gauge_id': self.gauge_id,
            'gauge_type': self.gauge_type.value,
            'center_x': self.center_x,
            'center_y': self.center_y,
            'radius': self.radius,
            'start_angle': self.start_angle,
            'end_angle': self.end_angle,
            'min_value': self.min_value,
            'max_value': self.max_value,
            'units': self.units,
            'precision': self.precision,
            'roi': [self.roi_x, self.roi_y, self.roi_width, self.roi_height],
            'calibration_points': self.calibration_points,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class GaugeReading:
    """Reading from analog gauge"""
    gauge_id: str
    value: float
    confidence: float
    raw_angle: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    image_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gauge_id': self.gauge_id,
            'value': self.value,
            'confidence': self.confidence,
            'raw_angle': self.raw_angle,
            'timestamp': self.timestamp.isoformat(),
            'image_path': self.image_path
        }


class AnalogGaugeDigitizer:
    """Main class for analog gauge digitization"""
    
    def __init__(self):
        self.gauges: Dict[str, GaugeCalibration] = {}
        self.camera_devices: Dict[str, cv2.VideoCapture] = {}
        self.reading_callbacks: List = []
        self.is_running = False
        
        # Processing parameters
        self.reading_interval = 0.5  # seconds
        self.confidence_threshold = 0.7
        self.max_reading_history = 1000
        
        # Reading history
        self.reading_history: Dict[str, List[GaugeReading]] = {}
        
        logger.info("AnalogGaugeDigitizer initialized")
    
    def add_gauge(self, calibration: GaugeCalibration) -> bool:
        """Add a new gauge for monitoring"""
        try:
            self.gauges[calibration.gauge_id] = calibration
            self.reading_history[calibration.gauge_id] = []
            
            logger.info(f"Added gauge {calibration.gauge_id} ({calibration.gauge_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add gauge {calibration.gauge_id}: {e}")
            return False
    
    def remove_gauge(self, gauge_id: str) -> bool:
        """Remove a gauge from monitoring"""
        try:
            if gauge_id in self.gauges:
                del self.gauges[gauge_id]
                del self.reading_history[gauge_id]
                logger.info(f"Removed gauge {gauge_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove gauge {gauge_id}: {e}")
            return False
    
    def add_camera_device(self, device_id: str, camera_index: int = 0) -> bool:
        """Add camera device for gauge monitoring"""
        try:
            cap = cv2.VideoCapture(camera_index)
            if cap.isOpened():
                self.camera_devices[device_id] = cap
                logger.info(f"Added camera device {device_id} (index {camera_index})")
                return True
            else:
                logger.error(f"Failed to open camera {camera_index}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to add camera device: {e}")
            return False
    
    async def start_monitoring(self):
        """Start gauge monitoring"""
        self.is_running = True
        
        # Start monitoring tasks for each gauge
        for gauge_id in self.gauges.keys():
            asyncio.create_task(self._monitor_gauge(gauge_id))
        
        logger.info("Started analog gauge monitoring")
    
    async def stop_monitoring(self):
        """Stop gauge monitoring"""
        self.is_running = False
        
        # Close camera devices
        for cap in self.camera_devices.values():
            cap.release()
        
        logger.info("Stopped analog gauge monitoring")
    
    async def _monitor_gauge(self, gauge_id: str):
        """Monitor a specific gauge"""
        while self.is_running:
            try:
                reading = await self.read_gauge(gauge_id)
                if reading and reading.confidence >= self.confidence_threshold:
                    # Store reading
                    self._store_reading(reading)
                    
                    # Notify callbacks
                    for callback in self.reading_callbacks:
                        try:
                            await callback(reading)
                        except Exception as e:
                            logger.error(f"Error in reading callback: {e}")
                
                await asyncio.sleep(self.reading_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring gauge {gauge_id}: {e}")
                await asyncio.sleep(1)
    
    def _store_reading(self, reading: GaugeReading):
        """Store gauge reading in history"""
        if reading.gauge_id not in self.reading_history:
            self.reading_history[reading.gauge_id] = []
        
        history = self.reading_history[reading.gauge_id]
        history.append(reading)
        
        # Limit history size
        if len(history) > self.max_reading_history:
            history.pop(0)
    
    async def read_gauge(self, gauge_id: str, image: Optional[np.ndarray] = None) -> Optional[GaugeReading]:
        """Read value from analog gauge"""
        try:
            calibration = self.gauges.get(gauge_id)
            if not calibration:
                logger.error(f"No calibration found for gauge {gauge_id}")
                return None
            
            # Get image from camera or use provided image
            if image is None:
                image = await self._capture_image(gauge_id)
                if image is None:
                    return None
            
            # Process image based on gauge type
            if calibration.gauge_type == GaugeType.CIRCULAR:
                return await self._read_circular_gauge(calibration, image)
            elif calibration.gauge_type == GaugeType.LINEAR:
                return await self._read_linear_gauge(calibration, image)
            elif calibration.gauge_type == GaugeType.NEEDLE_POINTER:
                return await self._read_needle_gauge(calibration, image)
            else:
                logger.error(f"Unsupported gauge type: {calibration.gauge_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error reading gauge {gauge_id}: {e}")
            return None
    
    async def _capture_image(self, gauge_id: str) -> Optional[np.ndarray]:
        """Capture image for gauge reading"""
        try:
            # For demo, create a synthetic gauge image
            return self._create_demo_gauge_image(gauge_id)
            
        except Exception as e:
            logger.error(f"Error capturing image for gauge {gauge_id}: {e}")
            return None
    
    def _create_demo_gauge_image(self, gauge_id: str) -> np.ndarray:
        """Create demo gauge image for testing"""
        # Create a synthetic circular gauge
        img = np.ones((400, 400, 3), dtype=np.uint8) * 240
        
        center = (200, 200)
        radius = 150
        
        # Draw gauge outline
        cv2.circle(img, center, radius, (0, 0, 0), 3)
        cv2.circle(img, center, radius-20, (0, 0, 0), 2)
        
        # Draw tick marks
        for i in range(0, 360, 30):
            angle_rad = math.radians(i)
            x1 = int(center[0] + (radius-15) * math.cos(angle_rad))
            y1 = int(center[1] + (radius-15) * math.sin(angle_rad))
            x2 = int(center[0] + (radius-5) * math.cos(angle_rad))
            y2 = int(center[1] + (radius-5) * math.sin(angle_rad))
            cv2.line(img, (x1, y1), (x2, y2), (0, 0, 0), 2)
        
        # Draw needle at current demo position
        import time
        needle_angle = (time.time() % 10) * 36 - 135  # Simulate moving needle
        needle_rad = math.radians(needle_angle)
        needle_x = int(center[0] + (radius-30) * math.cos(needle_rad))
        needle_y = int(center[1] + (radius-30) * math.sin(needle_rad))
        
        cv2.line(img, center, (needle_x, needle_y), (0, 0, 255), 4)
        cv2.circle(img, center, 8, (0, 0, 255), -1)
        
        return img
    
    async def _read_circular_gauge(self, calibration: GaugeCalibration, image: np.ndarray) -> Optional[GaugeReading]:
        """Read circular gauge using computer vision"""
        try:
            # Extract ROI
            roi = image[calibration.roi_y:calibration.roi_y + calibration.roi_height,
                       calibration.roi_x:calibration.roi_x + calibration.roi_width]
            
            # Convert to HSV for color detection
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            
            # Create mask for needle color
            mask = cv2.inRange(hsv, calibration.needle_color_hsv_min, calibration.needle_color_hsv_max)
            
            # Apply morphological operations to clean up mask
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return GaugeReading(calibration.gauge_id, 0.0, 0.0)
            
            # Find the longest contour (likely the needle)
            longest_contour = max(contours, key=cv2.contourArea)
            
            # Fit line to contour
            if len(longest_contour) >= 10:
                [vx, vy, x, y] = cv2.fitLine(longest_contour, cv2.DIST_L2, 0, 0.01, 0.01)
                
                # Calculate needle angle
                needle_angle = math.degrees(math.atan2(vy, vx))
                
                # Normalize angle to gauge range
                angle_range = calibration.end_angle - calibration.start_angle
                normalized_angle = (needle_angle - calibration.start_angle) / angle_range
                
                # Map to value range
                value_range = calibration.max_value - calibration.min_value
                gauge_value = calibration.min_value + (normalized_angle * value_range)
                
                # Apply precision
                gauge_value = round(gauge_value, calibration.precision)
                
                # Calculate confidence based on contour quality
                confidence = min(1.0, cv2.contourArea(longest_contour) / 1000.0)
                
                return GaugeReading(
                    gauge_id=calibration.gauge_id,
                    value=gauge_value,
                    confidence=confidence,
                    raw_angle=needle_angle
                )
            
            return GaugeReading(calibration.gauge_id, 0.0, 0.0)
            
        except Exception as e:
            logger.error(f"Error reading circular gauge: {e}")
            return None
    
    async def _read_linear_gauge(self, calibration: GaugeCalibration, image: np.ndarray) -> Optional[GaugeReading]:
        """Read linear gauge using computer vision"""
        try:
            # Extract ROI
            roi = image[calibration.roi_y:calibration.roi_y + calibration.roi_height,
                       calibration.roi_x:calibration.roi_x + calibration.roi_width]
            
            # Convert to grayscale
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (calibration.blur_kernel_size, calibration.blur_kernel_size), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, calibration.canny_threshold1, calibration.canny_threshold2)
            
            # Find lines using Hough transform
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 
                                  calibration.hough_threshold,
                                  minLineLength=calibration.min_line_length)
            
            if lines is not None and len(lines) > 0:
                # Process the most prominent line as the gauge indicator
                line = lines[0][0]
                
                # Calculate position along the linear gauge
                if calibration.roi_width > calibration.roi_height:  # Horizontal gauge
                    position = (line[0] + line[2]) / 2  # Average x position
                    relative_position = position / calibration.roi_width
                else:  # Vertical gauge
                    position = (line[1] + line[3]) / 2  # Average y position
                    relative_position = 1.0 - (position / calibration.roi_height)  # Invert for bottom-to-top
                
                # Map to value range
                value_range = calibration.max_value - calibration.min_value
                gauge_value = calibration.min_value + (relative_position * value_range)
                gauge_value = round(gauge_value, calibration.precision)
                
                confidence = 0.8  # Fixed confidence for linear gauges
                
                return GaugeReading(
                    gauge_id=calibration.gauge_id,
                    value=gauge_value,
                    confidence=confidence
                )
            
            return GaugeReading(calibration.gauge_id, 0.0, 0.0)
            
        except Exception as e:
            logger.error(f"Error reading linear gauge: {e}")
            return None
    
    async def _read_needle_gauge(self, calibration: GaugeCalibration, image: np.ndarray) -> Optional[GaugeReading]:
        """Read needle-type gauge with advanced detection"""
        try:
            # Use Hough line detection for needle
            roi = image[calibration.roi_y:calibration.roi_y + calibration.roi_height,
                       calibration.roi_x:calibration.roi_x + calibration.roi_width]
            
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                # Find the line closest to center that could be the needle
                center_x = calibration.roi_width // 2
                center_y = calibration.roi_height // 2
                
                best_line = None
                min_distance = float('inf')
                
                for line in lines:
                    rho, theta = line[0]
                    a = np.cos(theta)
                    b = np.sin(theta)
                    x0 = a * rho
                    y0 = b * rho
                    
                    # Calculate distance from center
                    distance = abs(x0 - center_x) + abs(y0 - center_y)
                    
                    if distance < min_distance:
                        min_distance = distance
                        best_line = (rho, theta)
                
                if best_line:
                    _, theta = best_line
                    needle_angle = math.degrees(theta) - 90  # Adjust for vertical reference
                    
                    # Map angle to gauge value
                    angle_range = calibration.end_angle - calibration.start_angle
                    normalized_angle = (needle_angle - calibration.start_angle) / angle_range
                    
                    value_range = calibration.max_value - calibration.min_value
                    gauge_value = calibration.min_value + (normalized_angle * value_range)
                    gauge_value = round(gauge_value, calibration.precision)
                    
                    return GaugeReading(
                        gauge_id=calibration.gauge_id,
                        value=gauge_value,
                        confidence=0.75,
                        raw_angle=needle_angle
                    )
            
            return GaugeReading(calibration.gauge_id, 0.0, 0.0)
            
        except Exception as e:
            logger.error(f"Error reading needle gauge: {e}")
            return None
    
    def calibrate_gauge(self, gauge_id: str, method: CalibrationMethod, 
                       reference_points: List[Dict[str, float]]) -> bool:
        """Calibrate gauge using reference points"""
        try:
            if gauge_id not in self.gauges:
                logger.error(f"Gauge {gauge_id} not found")
                return False
            
            calibration = self.gauges[gauge_id]
            calibration.calibration_points = reference_points
            
            # Update calibration based on reference points
            if len(reference_points) >= 2:
                # Use linear interpolation to improve accuracy
                points = sorted(reference_points, key=lambda x: x['actual_value'])
                calibration.min_value = points[0]['actual_value']
                calibration.max_value = points[-1]['actual_value']
                
                logger.info(f"Calibrated gauge {gauge_id} with {len(reference_points)} points")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error calibrating gauge {gauge_id}: {e}")
            return False
    
    def get_gauge_readings(self, gauge_id: Optional[str] = None, 
                          limit: int = 100) -> List[GaugeReading]:
        """Get recent gauge readings"""
        if gauge_id:
            history = self.reading_history.get(gauge_id, [])
            return history[-limit:]
        else:
            all_readings = []
            for readings in self.reading_history.values():
                all_readings.extend(readings[-limit:])
            return sorted(all_readings, key=lambda x: x.timestamp)[-limit:]
    
    def get_gauge_statistics(self, gauge_id: str) -> Dict[str, Any]:
        """Get statistics for a gauge"""
        try:
            readings = self.reading_history.get(gauge_id, [])
            if not readings:
                return {}
            
            values = [r.value for r in readings[-100:]]  # Last 100 readings
            confidences = [r.confidence for r in readings[-100:]]
            
            return {
                'gauge_id': gauge_id,
                'total_readings': len(readings),
                'recent_readings': len(values),
                'min_value': min(values) if values else 0,
                'max_value': max(values) if values else 0,
                'avg_value': sum(values) / len(values) if values else 0,
                'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
                'last_reading': readings[-1].to_dict() if readings else None
            }
            
        except Exception as e:
            logger.error(f"Error getting gauge statistics for {gauge_id}: {e}")
            return {}
    
    def subscribe_to_readings(self, callback):
        """Subscribe to gauge reading updates"""
        self.reading_callbacks.append(callback)
        logger.info(f"Added reading subscriber: {callback.__name__}")
    
    def save_calibration(self, gauge_id: str, file_path: str) -> bool:
        """Save gauge calibration to file"""
        try:
            if gauge_id not in self.gauges:
                return False
            
            calibration_data = self.gauges[gauge_id].to_dict()
            
            with open(file_path, 'w') as f:
                json.dump(calibration_data, f, indent=2)
            
            logger.info(f"Saved calibration for gauge {gauge_id} to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving calibration: {e}")
            return False
    
    def load_calibration(self, file_path: str) -> bool:
        """Load gauge calibration from file"""
        try:
            with open(file_path, 'r') as f:
                calibration_data = json.load(f)
            
            calibration = GaugeCalibration(
                gauge_id=calibration_data['gauge_id'],
                gauge_type=GaugeType(calibration_data['gauge_type']),
                center_x=calibration_data['center_x'],
                center_y=calibration_data['center_y'],
                radius=calibration_data['radius'],
                start_angle=calibration_data['start_angle'],
                end_angle=calibration_data['end_angle'],
                min_value=calibration_data['min_value'],
                max_value=calibration_data['max_value'],
                units=calibration_data['units'],
                precision=calibration_data['precision'],
                roi_x=calibration_data['roi'][0],
                roi_y=calibration_data['roi'][1],
                roi_width=calibration_data['roi'][2],
                roi_height=calibration_data['roi'][3]
            )
            
            self.add_gauge(calibration)
            
            logger.info(f"Loaded calibration for gauge {calibration.gauge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading calibration: {e}")
            return False