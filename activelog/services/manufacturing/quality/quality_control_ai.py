"""
ActiveLog Manufacturing Suite - Quality Control AI

Computer vision-powered quality control system for defect detection,
statistical process control, and automated inspection.
"""

import asyncio
import cv2
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import json
import base64
from pathlib import Path
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image, ImageDraw
import io


class DefectType(Enum):
    SURFACE_DEFECT = "surface_defect"
    DIMENSIONAL_VARIANCE = "dimensional_variance"
    COLOR_DEVIATION = "color_deviation"
    ASSEMBLY_ERROR = "assembly_error"
    CONTAMINATION = "contamination"
    STRUCTURAL_DAMAGE = "structural_damage"
    MISSING_COMPONENT = "missing_component"


class SeverityLevel(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"


class InspectionStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    REWORK = "rework"
    PENDING = "pending"


@dataclass
class QualityStandard:
    standard_id: str
    name: str
    category: str
    specifications: Dict[str, Any]
    tolerance_limits: Dict[str, Tuple[float, float]]
    visual_criteria: List[str]
    measurement_requirements: List[str]


@dataclass
class DefectDetection:
    defect_id: str
    defect_type: DefectType
    severity: SeverityLevel
    location: Tuple[int, int, int, int]  # x, y, width, height
    confidence_score: float
    description: str
    suggested_action: str


@dataclass
class InspectionResult:
    inspection_id: str
    product_id: str
    batch_id: str
    station_id: str
    inspector_id: str
    timestamp: datetime
    status: InspectionStatus
    defects: List[DefectDetection]
    measurements: Dict[str, float]
    quality_score: float
    processing_time: float
    images: List[str]  # Image paths or base64


@dataclass
class QualityMetrics:
    total_inspected: int
    pass_rate: float
    defect_rate: float
    rework_rate: float
    critical_defects: int
    average_quality_score: float
    processing_efficiency: float


class ComputerVisionEngine:
    """AI engine for visual quality inspection"""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.defect_model = None
        self.classification_model = None
        self.segmentation_model = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize or load computer vision models"""
        try:
            self.defect_model = tf.keras.models.load_model(f"{self.model_path}/defect_detection.h5")
            self.classification_model = tf.keras.models.load_model(f"{self.model_path}/classification.h5")
        except:
            self._create_default_models()
    
    def _create_default_models(self):
        """Create default CNN models for quality inspection"""
        # Defect detection model (simplified YOLO-like architecture)
        self.defect_model = models.Sequential([
            layers.Conv2D(32, (3, 3), activation='relu', input_shape=(416, 416, 3)),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.Flatten(),
            layers.Dense(64, activation='relu'),
            layers.Dense(7, activation='sigmoid')  # 7 defect types
        ])
        
        # Classification model for pass/fail
        self.classification_model = models.Sequential([
            layers.Conv2D(32, (3, 3), activation='relu', input_shape=(224, 224, 3)),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.MaxPooling2D((2, 2)),
            layers.Conv2D(128, (3, 3), activation='relu'),
            layers.GlobalAveragePooling2D(),
            layers.Dense(128, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(3, activation='softmax')  # pass, fail, rework
        ])
        
        self.defect_model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        self.classification_model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
    
    async def analyze_image(self, image: np.ndarray, 
                          quality_standard: QualityStandard) -> List[DefectDetection]:
        """Analyze image for defects using computer vision"""
        if self.defect_model is None:
            return []
        
        # Preprocess image
        processed_image = self._preprocess_image(image)
        
        # Detect defects
        predictions = self.defect_model.predict(np.expand_dims(processed_image, axis=0))
        
        defects = []
        defect_types = list(DefectType)
        
        for i, confidence in enumerate(predictions[0]):
            if confidence > 0.5:  # Threshold for defect detection
                # Simulate defect location (in production, use object detection)
                location = self._simulate_defect_location(image.shape, i)
                
                severity = self._determine_severity(confidence, defect_types[i])
                
                defect = DefectDetection(
                    defect_id=f"defect_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}",
                    defect_type=defect_types[i],
                    severity=severity,
                    location=location,
                    confidence_score=float(confidence),
                    description=self._generate_defect_description(defect_types[i], confidence),
                    suggested_action=self._suggest_action(defect_types[i], severity)
                )
                
                defects.append(defect)
        
        return defects
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for model input"""
        # Resize to model input size
        resized = cv2.resize(image, (416, 416))
        
        # Normalize pixel values
        normalized = resized.astype(np.float32) / 255.0
        
        return normalized
    
    def _simulate_defect_location(self, image_shape: Tuple[int, int, int], 
                                defect_index: int) -> Tuple[int, int, int, int]:
        """Simulate defect bounding box location"""
        height, width = image_shape[:2]
        
        # Generate random but realistic defect locations
        x = np.random.randint(0, width - 100)
        y = np.random.randint(0, height - 100)
        w = np.random.randint(20, 100)
        h = np.random.randint(20, 100)
        
        return (x, y, w, h)
    
    def _determine_severity(self, confidence: float, defect_type: DefectType) -> SeverityLevel:
        """Determine defect severity based on confidence and type"""
        critical_defects = [DefectType.STRUCTURAL_DAMAGE, DefectType.MISSING_COMPONENT]
        
        if defect_type in critical_defects:
            return SeverityLevel.CRITICAL
        elif confidence > 0.9:
            return SeverityLevel.MAJOR
        elif confidence > 0.7:
            return SeverityLevel.MINOR
        else:
            return SeverityLevel.COSMETIC
    
    def _generate_defect_description(self, defect_type: DefectType, 
                                   confidence: float) -> str:
        """Generate human-readable defect description"""
        descriptions = {
            DefectType.SURFACE_DEFECT: f"Surface anomaly detected with {confidence:.1%} confidence",
            DefectType.DIMENSIONAL_VARIANCE: f"Dimensional deviation identified with {confidence:.1%} confidence",
            DefectType.COLOR_DEVIATION: f"Color variation from standard detected with {confidence:.1%} confidence",
            DefectType.ASSEMBLY_ERROR: f"Assembly misalignment detected with {confidence:.1%} confidence",
            DefectType.CONTAMINATION: f"Foreign material contamination found with {confidence:.1%} confidence",
            DefectType.STRUCTURAL_DAMAGE: f"Structural integrity issue identified with {confidence:.1%} confidence",
            DefectType.MISSING_COMPONENT: f"Missing component detected with {confidence:.1%} confidence"
        }
        
        return descriptions.get(defect_type, f"Defect detected with {confidence:.1%} confidence")
    
    def _suggest_action(self, defect_type: DefectType, severity: SeverityLevel) -> str:
        """Suggest corrective action based on defect type and severity"""
        if severity == SeverityLevel.CRITICAL:
            return "Immediate rejection and root cause analysis required"
        elif severity == SeverityLevel.MAJOR:
            if defect_type in [DefectType.ASSEMBLY_ERROR, DefectType.DIMENSIONAL_VARIANCE]:
                return "Rework recommended - check assembly procedures"
            else:
                return "Reject item and investigate process parameters"
        elif severity == SeverityLevel.MINOR:
            return "Rework possible - evaluate cost-benefit"
        else:
            return "Accept with documentation - monitor trend"


class DimensionalMeasurementEngine:
    """Engine for automated dimensional measurements"""
    
    def __init__(self):
        self.calibration_factor = 1.0  # pixels per mm
        self.reference_objects = {}
    
    async def measure_dimensions(self, image: np.ndarray, 
                               reference_size: Optional[float] = None) -> Dict[str, float]:
        """Perform automated dimensional measurements"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        measurements = {}
        
        if contours:
            # Find largest contour (assumed to be the main object)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Calculate bounding rectangle
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Convert pixel measurements to real units
            if reference_size:
                self.calibration_factor = reference_size / max(w, h)
            
            measurements = {
                'width_mm': w * self.calibration_factor,
                'height_mm': h * self.calibration_factor,
                'area_mm2': cv2.contourArea(largest_contour) * (self.calibration_factor ** 2),
                'perimeter_mm': cv2.arcLength(largest_contour, True) * self.calibration_factor,
                'aspect_ratio': w / h if h > 0 else 0,
                'bounding_box': (x, y, w, h)
            }
            
            # Calculate additional geometric properties
            if len(largest_contour) >= 5:
                ellipse = cv2.fitEllipse(largest_contour)
                measurements['major_axis_mm'] = max(ellipse[1]) * self.calibration_factor
                measurements['minor_axis_mm'] = min(ellipse[1]) * self.calibration_factor
        
        return measurements
    
    def check_dimensional_tolerance(self, measurements: Dict[str, float],
                                  specifications: Dict[str, Tuple[float, float]]) -> Dict[str, bool]:
        """Check if measurements are within tolerance"""
        results = {}
        
        for param, (min_val, max_val) in specifications.items():
            if param in measurements:
                value = measurements[param]
                results[param] = min_val <= value <= max_val
        
        return results


class StatisticalProcessControl:
    """Statistical process control for quality monitoring"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.control_limits = {}
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize SPC database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                batch_id TEXT,
                measurement_type TEXT,
                measurement_value REAL,
                timestamp TIMESTAMP,
                station_id TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS control_limits (
                measurement_type TEXT PRIMARY KEY,
                center_line REAL,
                upper_control_limit REAL,
                lower_control_limit REAL,
                upper_spec_limit REAL,
                lower_spec_limit REAL,
                last_updated TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def update_control_limits(self, measurement_type: str, data: List[float]):
        """Update statistical control limits"""
        if len(data) < 25:  # Minimum samples for reliable control limits
            return
        
        # Calculate control limits (3-sigma)
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        ucl = mean + 3 * std
        lcl = mean - 3 * std
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO control_limits 
            (measurement_type, center_line, upper_control_limit, lower_control_limit, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (measurement_type, mean, ucl, lcl, datetime.now()))
        
        conn.commit()
        conn.close()
        
        self.control_limits[measurement_type] = {
            'center_line': mean,
            'ucl': ucl,
            'lcl': lcl
        }
    
    async def detect_process_shifts(self, measurement_type: str, 
                                  recent_data: List[float]) -> List[str]:
        """Detect process shifts using control charts"""
        if measurement_type not in self.control_limits:
            return []
        
        limits = self.control_limits[measurement_type]
        alerts = []
        
        # Rule 1: Point beyond control limits
        for i, value in enumerate(recent_data):
            if value > limits['ucl'] or value < limits['lcl']:
                alerts.append(f"Point {i+1} beyond control limits: {value:.3f}")
        
        # Rule 2: 7 consecutive points on one side of center line
        if len(recent_data) >= 7:
            center = limits['center_line']
            above_center = [x > center for x in recent_data[-7:]]
            below_center = [x < center for x in recent_data[-7:]]
            
            if all(above_center):
                alerts.append("7 consecutive points above center line")
            elif all(below_center):
                alerts.append("7 consecutive points below center line")
        
        # Rule 3: 2 out of 3 consecutive points beyond 2-sigma
        if len(recent_data) >= 3:
            sigma = (limits['ucl'] - limits['center_line']) / 3
            two_sigma_upper = limits['center_line'] + 2 * sigma
            two_sigma_lower = limits['center_line'] - 2 * sigma
            
            for i in range(len(recent_data) - 2):
                window = recent_data[i:i+3]
                beyond_2sigma = sum(1 for x in window if x > two_sigma_upper or x < two_sigma_lower)
                if beyond_2sigma >= 2:
                    alerts.append(f"2 of 3 points beyond 2-sigma at position {i+1}")
        
        return alerts
    
    async def calculate_process_capability(self, measurement_type: str,
                                         spec_limits: Tuple[float, float]) -> Dict[str, float]:
        """Calculate process capability indices"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT measurement_value FROM quality_data 
            WHERE measurement_type = ? AND timestamp > date('now', '-30 days')
        """, (measurement_type,))
        
        data = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if len(data) < 30:
            return {}
        
        lsl, usl = spec_limits  # Lower and upper spec limits
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        # Process capability indices
        cp = (usl - lsl) / (6 * std) if std > 0 else 0
        cpk = min((usl - mean), (mean - lsl)) / (3 * std) if std > 0 else 0
        cpm = (usl - lsl) / (6 * np.sqrt(std**2 + (mean - (usl + lsl)/2)**2)) if std > 0 else 0
        
        return {
            'cp': cp,
            'cpk': cpk,
            'cpm': cpm,
            'mean': mean,
            'std': std,
            'samples': len(data)
        }


class QualityControlAI:
    """Main AI system for quality control and inspection"""
    
    def __init__(self, db_path: str = "quality_control.db", model_path: str = "models"):
        self.db_path = db_path
        self.model_path = model_path
        self.vision_engine = ComputerVisionEngine(model_path)
        self.measurement_engine = DimensionalMeasurementEngine()
        self.spc = StatisticalProcessControl(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize main quality control database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspections (
                inspection_id TEXT PRIMARY KEY,
                product_id TEXT,
                batch_id TEXT,
                station_id TEXT,
                inspector_id TEXT,
                timestamp TIMESTAMP,
                status TEXT,
                quality_score REAL,
                processing_time REAL,
                defect_count INTEGER,
                image_paths TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS defects (
                defect_id TEXT PRIMARY KEY,
                inspection_id TEXT,
                defect_type TEXT,
                severity TEXT,
                location TEXT,
                confidence_score REAL,
                description TEXT,
                suggested_action TEXT,
                FOREIGN KEY (inspection_id) REFERENCES inspections (inspection_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quality_standards (
                standard_id TEXT PRIMARY KEY,
                name TEXT,
                category TEXT,
                specifications TEXT,
                tolerance_limits TEXT,
                visual_criteria TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def perform_inspection(self, product_id: str, batch_id: str, 
                               station_id: str, inspector_id: str,
                               images: List[np.ndarray], 
                               quality_standard: QualityStandard) -> InspectionResult:
        """Perform comprehensive quality inspection"""
        start_time = datetime.now()
        inspection_id = f"insp_{start_time.strftime('%Y%m%d_%H%M%S')}_{product_id}"
        
        all_defects = []
        measurements = {}
        
        # Analyze each image
        for i, image in enumerate(images):
            # Computer vision analysis
            defects = await self.vision_engine.analyze_image(image, quality_standard)
            all_defects.extend(defects)
            
            # Dimensional measurements
            dims = await self.measurement_engine.measure_dimensions(image)
            measurements.update({f"image_{i}_{k}": v for k, v in dims.items()})
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(all_defects, measurements, quality_standard)
        
        # Determine inspection status
        status = self._determine_inspection_status(all_defects, quality_score)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create inspection result
        result = InspectionResult(
            inspection_id=inspection_id,
            product_id=product_id,
            batch_id=batch_id,
            station_id=station_id,
            inspector_id=inspector_id,
            timestamp=start_time,
            status=status,
            defects=all_defects,
            measurements=measurements,
            quality_score=quality_score,
            processing_time=processing_time,
            images=[f"image_{i}.jpg" for i in range(len(images))]
        )
        
        # Store results
        await self._store_inspection_result(result)
        
        # Update SPC data
        await self._update_spc_data(result)
        
        return result
    
    def _calculate_quality_score(self, defects: List[DefectDetection], 
                               measurements: Dict[str, float],
                               quality_standard: QualityStandard) -> float:
        """Calculate overall quality score"""
        base_score = 100.0
        
        # Deduct points for defects
        for defect in defects:
            if defect.severity == SeverityLevel.CRITICAL:
                base_score -= 30
            elif defect.severity == SeverityLevel.MAJOR:
                base_score -= 15
            elif defect.severity == SeverityLevel.MINOR:
                base_score -= 5
            else:  # COSMETIC
                base_score -= 1
        
        # Check dimensional tolerance
        tolerance_violations = 0
        for param, (min_val, max_val) in quality_standard.tolerance_limits.items():
            if param in measurements:
                value = measurements[param]
                if not (min_val <= value <= max_val):
                    tolerance_violations += 1
                    base_score -= 10
        
        return max(0.0, min(100.0, base_score))
    
    def _determine_inspection_status(self, defects: List[DefectDetection], 
                                   quality_score: float) -> InspectionStatus:
        """Determine inspection pass/fail status"""
        critical_defects = [d for d in defects if d.severity == SeverityLevel.CRITICAL]
        major_defects = [d for d in defects if d.severity == SeverityLevel.MAJOR]
        
        if critical_defects or quality_score < 70:
            return InspectionStatus.FAIL
        elif major_defects or quality_score < 85:
            return InspectionStatus.REWORK
        else:
            return InspectionStatus.PASS
    
    async def _store_inspection_result(self, result: InspectionResult):
        """Store inspection result in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store main inspection record
        cursor.execute("""
            INSERT INTO inspections 
            (inspection_id, product_id, batch_id, station_id, inspector_id, 
             timestamp, status, quality_score, processing_time, defect_count, image_paths)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.inspection_id, result.product_id, result.batch_id,
            result.station_id, result.inspector_id, result.timestamp,
            result.status.value, result.quality_score, result.processing_time,
            len(result.defects), json.dumps(result.images)
        ))
        
        # Store defects
        for defect in result.defects:
            cursor.execute("""
                INSERT INTO defects 
                (defect_id, inspection_id, defect_type, severity, location,
                 confidence_score, description, suggested_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                defect.defect_id, result.inspection_id, defect.defect_type.value,
                defect.severity.value, json.dumps(defect.location),
                defect.confidence_score, defect.description, defect.suggested_action
            ))
        
        conn.commit()
        conn.close()
    
    async def _update_spc_data(self, result: InspectionResult):
        """Update statistical process control data"""
        # Add quality score to SPC monitoring
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO quality_data 
            (product_id, batch_id, measurement_type, measurement_value, timestamp, station_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            result.product_id, result.batch_id, "quality_score",
            result.quality_score, result.timestamp, result.station_id
        ))
        
        # Add dimensional measurements
        for measurement, value in result.measurements.items():
            if isinstance(value, (int, float)):
                cursor.execute("""
                    INSERT INTO quality_data 
                    (product_id, batch_id, measurement_type, measurement_value, timestamp, station_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    result.product_id, result.batch_id, measurement,
                    value, result.timestamp, result.station_id
                ))
        
        conn.commit()
        conn.close()
    
    async def get_quality_metrics(self, time_period: int = 24) -> QualityMetrics:
        """Get quality metrics for specified time period (hours)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get inspection statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pass' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN status = 'fail' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'rework' THEN 1 ELSE 0 END) as rework,
                AVG(quality_score) as avg_score,
                AVG(processing_time) as avg_time
            FROM inspections 
            WHERE timestamp > datetime('now', '-{} hours')
        """.format(time_period))
        
        stats = cursor.fetchone()
        
        # Get critical defects count
        cursor.execute("""
            SELECT COUNT(*) FROM defects d
            JOIN inspections i ON d.inspection_id = i.inspection_id
            WHERE d.severity = 'critical' 
            AND i.timestamp > datetime('now', '-{} hours')
        """.format(time_period))
        
        critical_defects = cursor.fetchone()[0]
        conn.close()
        
        total = stats[0] if stats[0] else 1
        
        return QualityMetrics(
            total_inspected=total,
            pass_rate=stats[1] / total if stats[1] else 0.0,
            defect_rate=stats[2] / total if stats[2] else 0.0,
            rework_rate=stats[3] / total if stats[3] else 0.0,
            critical_defects=critical_defects,
            average_quality_score=stats[4] if stats[4] else 0.0,
            processing_efficiency=1.0 / stats[5] if stats[5] else 0.0
        )
    
    async def generate_quality_report(self, batch_id: str) -> Dict[str, Any]:
        """Generate comprehensive quality report for batch"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get batch statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_inspections,
                AVG(quality_score) as avg_quality_score,
                COUNT(CASE WHEN status = 'pass' THEN 1 END) as pass_count,
                COUNT(CASE WHEN status = 'fail' THEN 1 END) as fail_count,
                COUNT(CASE WHEN status = 'rework' THEN 1 END) as rework_count
            FROM inspections 
            WHERE batch_id = ?
        """, (batch_id,))
        
        batch_stats = cursor.fetchone()
        
        # Get defect breakdown
        cursor.execute("""
            SELECT d.defect_type, d.severity, COUNT(*) as count
            FROM defects d
            JOIN inspections i ON d.inspection_id = i.inspection_id
            WHERE i.batch_id = ?
            GROUP BY d.defect_type, d.severity
            ORDER BY count DESC
        """, (batch_id,))
        
        defect_breakdown = cursor.fetchall()
        conn.close()
        
        return {
            'batch_id': batch_id,
            'summary': {
                'total_inspections': batch_stats[0],
                'average_quality_score': batch_stats[1],
                'pass_rate': batch_stats[2] / batch_stats[0] if batch_stats[0] > 0 else 0,
                'fail_rate': batch_stats[3] / batch_stats[0] if batch_stats[0] > 0 else 0,
                'rework_rate': batch_stats[4] / batch_stats[0] if batch_stats[0] > 0 else 0
            },
            'defect_analysis': [
                {
                    'defect_type': row[0],
                    'severity': row[1],
                    'count': row[2]
                } for row in defect_breakdown
            ],
            'recommendations': self._generate_quality_recommendations(defect_breakdown),
            'generated_at': datetime.now().isoformat()
        }
    
    def _generate_quality_recommendations(self, defect_breakdown: List[Tuple]) -> List[str]:
        """Generate quality improvement recommendations"""
        recommendations = []
        
        if not defect_breakdown:
            return ["No significant quality issues detected"]
        
        # Analyze most common defects
        defect_counts = {}
        for defect_type, severity, count in defect_breakdown:
            defect_counts[defect_type] = defect_counts.get(defect_type, 0) + count
        
        most_common_defect = max(defect_counts.items(), key=lambda x: x[1])
        
        defect_recommendations = {
            'surface_defect': "Review surface finishing processes and tooling condition",
            'dimensional_variance': "Calibrate measurement equipment and review machining parameters",
            'color_deviation': "Check material batches and painting/coating processes",
            'assembly_error': "Review assembly procedures and operator training",
            'contamination': "Enhance cleaning protocols and environmental controls",
            'structural_damage': "Investigate handling procedures and packaging methods"
        }
        
        if most_common_defect[0] in defect_recommendations:
            recommendations.append(defect_recommendations[most_common_defect[0]])
        
        # Critical defects require immediate attention
        critical_defects = [row for row in defect_breakdown if row[1] == 'critical']
        if critical_defects:
            recommendations.append("Immediate process halt and root cause analysis required for critical defects")
        
        return recommendations


async def main():
    """Example usage of Quality Control AI"""
    qc_ai = QualityControlAI()
    
    # Example quality standard
    quality_standard = QualityStandard(
        standard_id="STD001",
        name="Electronic Component Standard",
        category="electronics",
        specifications={"surface_finish": "smooth", "color": "black"},
        tolerance_limits={
            "width_mm": (10.0, 12.0),
            "height_mm": (5.0, 7.0),
            "thickness_mm": (1.0, 2.0)
        },
        visual_criteria=["no_scratches", "uniform_color"],
        measurement_requirements=["dimensional_check", "surface_inspection"]
    )
    
    # Simulate inspection with dummy image
    dummy_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Perform inspection
    result = await qc_ai.perform_inspection(
        product_id="PROD001",
        batch_id="BATCH001",
        station_id="STATION01",
        inspector_id="AI_INSPECTOR",
        images=[dummy_image],
        quality_standard=quality_standard
    )
    
    print(f"Inspection ID: {result.inspection_id}")
    print(f"Status: {result.status.value}")
    print(f"Quality Score: {result.quality_score:.1f}")
    print(f"Defects Found: {len(result.defects)}")
    print(f"Processing Time: {result.processing_time:.2f}s")
    
    for defect in result.defects:
        print(f"  - {defect.defect_type.value}: {defect.description}")
    
    # Get quality metrics
    metrics = await qc_ai.get_quality_metrics(24)
    print(f"\n24-Hour Quality Metrics:")
    print(f"Total Inspected: {metrics.total_inspected}")
    print(f"Pass Rate: {metrics.pass_rate:.1%}")
    print(f"Average Quality Score: {metrics.average_quality_score:.1f}")


if __name__ == "__main__":
    asyncio.run(main())