"""
Fish Species Identifier
Advanced AI-powered fish identification system for marine navigation and fishing applications
"""

import asyncio
import cv2
import numpy as np
import tensorflow as tf
from PIL import Image, ImageDraw, ImageFont
import io
import json
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import base64
import requests
import sqlite3
import pickle
import math
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FishHabitat(Enum):
    FRESHWATER = "freshwater"
    SALTWATER = "saltwater"
    BRACKISH = "brackish"
    DEEP_SEA = "deep_sea"
    REEF = "reef"
    PELAGIC = "pelagic"
    BOTTOM = "bottom"

class FishSize(Enum):
    SMALL = "small"      # < 12 inches
    MEDIUM = "medium"    # 12-24 inches
    LARGE = "large"      # 24-48 inches
    XLARGE = "xlarge"    # > 48 inches

class FishingMethod(Enum):
    TROLLING = "trolling"
    BOTTOM_FISHING = "bottom_fishing"
    CASTING = "casting"
    FLY_FISHING = "fly_fishing"
    JIGGING = "jigging"
    NET_FISHING = "net_fishing"

@dataclass
class FishSpecies:
    species_id: str
    common_name: str
    scientific_name: str
    family: str
    habitat: FishHabitat
    typical_size: FishSize
    min_length_cm: float
    max_length_cm: float
    min_weight_kg: float
    max_weight_kg: float
    description: str
    identification_features: List[str] = field(default_factory=list)
    fishing_methods: List[FishingMethod] = field(default_factory=list)
    best_baits: List[str] = field(default_factory=list)
    seasonal_patterns: Dict[str, str] = field(default_factory=dict)
    conservation_status: str = "Unknown"
    edible: bool = True
    regulations: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FishIdentification:
    species: FishSpecies
    confidence: float
    bounding_box: Tuple[int, int, int, int]  # x, y, width, height
    key_features: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class IdentificationResult:
    image_path: Optional[str] = None
    identifications: List[FishIdentification] = field(default_factory=list)
    processing_time: float = 0.0
    location: Optional[Tuple[float, float]] = None
    water_temperature: Optional[float] = None
    depth: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

class FishDatabase:
    """Fish species database manager"""
    
    def __init__(self, db_path: str = "fish_species.db"):
        self.db_path = db_path
        self.species_data: Dict[str, FishSpecies] = {}
        self._initialize_database()
        self._load_species_data()
    
    def _initialize_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fish_species (
                species_id TEXT PRIMARY KEY,
                common_name TEXT NOT NULL,
                scientific_name TEXT NOT NULL,
                family TEXT,
                habitat TEXT,
                typical_size TEXT,
                min_length_cm REAL,
                max_length_cm REAL,
                min_weight_kg REAL,
                max_weight_kg REAL,
                description TEXT,
                identification_features TEXT,
                fishing_methods TEXT,
                best_baits TEXT,
                seasonal_patterns TEXT,
                conservation_status TEXT,
                edible BOOLEAN,
                regulations TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS identifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                species_id TEXT,
                confidence REAL,
                location_lat REAL,
                location_lon REAL,
                water_temp REAL,
                depth REAL,
                image_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (species_id) REFERENCES fish_species (species_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_species_data(self):
        """Load species data from database and populate with common species"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM fish_species')
        count = cursor.fetchone()[0]
        
        if count == 0:
            self._populate_default_species()
        
        # Load all species
        cursor.execute('SELECT * FROM fish_species')
        rows = cursor.fetchall()
        
        for row in rows:
            species = FishSpecies(
                species_id=row[0],
                common_name=row[1],
                scientific_name=row[2],
                family=row[3] or "",
                habitat=FishHabitat(row[4]) if row[4] else FishHabitat.SALTWATER,
                typical_size=FishSize(row[5]) if row[5] else FishSize.MEDIUM,
                min_length_cm=row[6] or 0,
                max_length_cm=row[7] or 100,
                min_weight_kg=row[8] or 0,
                max_weight_kg=row[9] or 10,
                description=row[10] or "",
                identification_features=json.loads(row[11]) if row[11] else [],
                fishing_methods=[FishingMethod(m) for m in json.loads(row[12])] if row[12] else [],
                best_baits=json.loads(row[13]) if row[13] else [],
                seasonal_patterns=json.loads(row[14]) if row[14] else {},
                conservation_status=row[15] or "Unknown",
                edible=bool(row[16]) if row[16] is not None else True,
                regulations=json.loads(row[17]) if row[17] else {}
            )
            self.species_data[species.species_id] = species
        
        conn.close()
        logger.info(f"Loaded {len(self.species_data)} fish species")
    
    def _populate_default_species(self):
        """Populate database with common fish species"""
        default_species = [
            # Saltwater species
            FishSpecies(
                species_id="largemouth_bass",
                common_name="Largemouth Bass",
                scientific_name="Micropterus salmoides",
                family="Centrarchidae",
                habitat=FishHabitat.FRESHWATER,
                typical_size=FishSize.MEDIUM,
                min_length_cm=20,
                max_length_cm=75,
                min_weight_kg=0.5,
                max_weight_kg=10,
                description="Popular game fish with large mouth extending past the eye",
                identification_features=["Large mouth", "Dark lateral stripe", "Spiny dorsal fin"],
                fishing_methods=[FishingMethod.CASTING, FishingMethod.TROLLING],
                best_baits=["Plastic worms", "Spinnerbaits", "Crankbaits"],
                conservation_status="Least Concern",
                edible=True
            ),
            FishSpecies(
                species_id="red_snapper",
                common_name="Red Snapper",
                scientific_name="Lutjanus campechanus",
                family="Lutjanidae",
                habitat=FishHabitat.SALTWATER,
                typical_size=FishSize.MEDIUM,
                min_length_cm=30,
                max_length_cm=100,
                min_weight_kg=1,
                max_weight_kg=15,
                description="Prized food fish with distinctive red coloration",
                identification_features=["Bright red coloration", "Triangular anal fin", "Red eyes"],
                fishing_methods=[FishingMethod.BOTTOM_FISHING],
                best_baits=["Cut bait", "Squid", "Live fish"],
                conservation_status="Vulnerable",
                edible=True,
                regulations={"min_size_cm": 40, "bag_limit": 2, "season": "June 1 - July 31"}
            ),
            FishSpecies(
                species_id="yellowfin_tuna",
                common_name="Yellowfin Tuna",
                scientific_name="Thunnus albacares",
                family="Scombridae",
                habitat=FishHabitat.PELAGIC,
                typical_size=FishSize.LARGE,
                min_length_cm=50,
                max_length_cm=200,
                min_weight_kg=5,
                max_weight_kg=200,
                description="Fast-swimming pelagic fish, highly prized for sashimi",
                identification_features=["Yellow fins", "Torpedo-shaped body", "Metallic blue back"],
                fishing_methods=[FishingMethod.TROLLING],
                best_baits=["Live bait", "Lures", "Flying fish"],
                conservation_status="Near Threatened",
                edible=True
            ),
            FishSpecies(
                species_id="mahi_mahi",
                common_name="Mahi Mahi",
                scientific_name="Coryphaena hippurus",
                family="Coryphaenidae",
                habitat=FishHabitat.PELAGIC,
                typical_size=FishSize.MEDIUM,
                min_length_cm=30,
                max_length_cm=150,
                min_weight_kg=2,
                max_weight_kg=30,
                description="Colorful dolphinfish with distinctive dorsal fin",
                identification_features=["Bright colors", "High dorsal fin", "Blunt forehead"],
                fishing_methods=[FishingMethod.TROLLING, FishingMethod.CASTING],
                best_baits=["Flying fish", "Squid", "Ballyhoo"],
                conservation_status="Least Concern",
                edible=True
            ),
            FishSpecies(
                species_id="grouper",
                common_name="Red Grouper",
                scientific_name="Epinephelus morio",
                family="Serranidae",
                habitat=FishHabitat.REEF,
                typical_size=FishSize.LARGE,
                min_length_cm=40,
                max_length_cm=120,
                min_weight_kg=3,
                max_weight_kg=25,
                description="Bottom-dwelling reef fish with large mouth",
                identification_features=["Large mouth", "Mottled coloration", "Robust body"],
                fishing_methods=[FishingMethod.BOTTOM_FISHING],
                best_baits=["Live fish", "Cut bait", "Squid"],
                conservation_status="Vulnerable",
                edible=True,
                regulations={"min_size_cm": 50, "bag_limit": 1}
            )
        ]
        
        # Save to database
        for species in default_species:
            self.add_species(species)
    
    def add_species(self, species: FishSpecies):
        """Add species to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO fish_species VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        ''', (
            species.species_id,
            species.common_name,
            species.scientific_name,
            species.family,
            species.habitat.value,
            species.typical_size.value,
            species.min_length_cm,
            species.max_length_cm,
            species.min_weight_kg,
            species.max_weight_kg,
            species.description,
            json.dumps(species.identification_features),
            json.dumps([m.value for m in species.fishing_methods]),
            json.dumps(species.best_baits),
            json.dumps(species.seasonal_patterns),
            species.conservation_status,
            species.edible,
            json.dumps(species.regulations)
        ))
        
        conn.commit()
        conn.close()
        
        self.species_data[species.species_id] = species
    
    def get_species(self, species_id: str) -> Optional[FishSpecies]:
        """Get species by ID"""
        return self.species_data.get(species_id)
    
    def search_species(self, query: str, habitat: Optional[FishHabitat] = None) -> List[FishSpecies]:
        """Search species by name or features"""
        results = []
        query_lower = query.lower()
        
        for species in self.species_data.values():
            if habitat and species.habitat != habitat:
                continue
            
            if (query_lower in species.common_name.lower() or 
                query_lower in species.scientific_name.lower() or
                query_lower in species.family.lower() or
                any(query_lower in feature.lower() for feature in species.identification_features)):
                results.append(species)
        
        return results
    
    def get_species_by_habitat(self, habitat: FishHabitat) -> List[FishSpecies]:
        """Get all species in a habitat"""
        return [species for species in self.species_data.values() 
                if species.habitat == habitat]
    
    def record_identification(self, identification: FishIdentification, 
                            location: Optional[Tuple[float, float]] = None,
                            water_temp: Optional[float] = None,
                            depth: Optional[float] = None,
                            image_path: Optional[str] = None):
        """Record identification in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        lat, lon = location if location else (None, None)
        
        cursor.execute('''
            INSERT INTO identifications (
                species_id, confidence, location_lat, location_lon, 
                water_temp, depth, image_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            identification.species.species_id,
            identification.confidence,
            lat, lon,
            water_temp,
            depth,
            image_path
        ))
        
        conn.commit()
        conn.close()

class FishClassificationModel:
    """Neural network model for fish classification"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self.model = None
        self.class_names = []
        self.input_size = (224, 224)
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        """Create a default CNN model for fish classification"""
        logger.info("Creating default fish classification model")
        
        # Use transfer learning with MobileNetV2
        base_model = tf.keras.applications.MobileNetV2(
            input_shape=(224, 224, 3),
            include_top=False,
            weights='imagenet'
        )
        base_model.trainable = False
        
        # Add classification head
        self.model = tf.keras.Sequential([
            base_model,
            tf.keras.layers.GlobalAveragePooling2D(),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(5, activation='softmax')  # 5 classes for demo
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Default class names
        self.class_names = [
            'largemouth_bass', 'red_snapper', 'yellowfin_tuna', 
            'mahi_mahi', 'grouper'
        ]
        
        logger.info(f"Created model with {len(self.class_names)} classes")
    
    def load_model(self, model_path: str):
        """Load trained model from file"""
        try:
            self.model = tf.keras.models.load_model(model_path)
            
            # Load class names if available
            class_names_path = model_path.replace('.h5', '_classes.json')
            if Path(class_names_path).exists():
                with open(class_names_path, 'r') as f:
                    self.class_names = json.load(f)
            
            logger.info(f"Loaded model from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self._create_default_model()
    
    def preprocess_image(self, image: Union[np.ndarray, Image.Image]) -> np.ndarray:
        """Preprocess image for model input"""
        if isinstance(image, Image.Image):
            image = np.array(image)
        
        # Resize to model input size
        image = cv2.resize(image, self.input_size)
        
        # Normalize pixel values
        image = image.astype(np.float32) / 255.0
        
        # Add batch dimension
        image = np.expand_dims(image, axis=0)
        
        return image
    
    def predict(self, image: Union[np.ndarray, Image.Image]) -> Tuple[str, float]:
        """Predict fish species from image"""
        if self.model is None:
            return "unknown", 0.0
        
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Make prediction
            predictions = self.model.predict(processed_image, verbose=0)
            
            # Get class with highest confidence
            class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][class_idx])
            
            if class_idx < len(self.class_names):
                species_id = self.class_names[class_idx]
            else:
                species_id = "unknown"
            
            return species_id, confidence
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return "unknown", 0.0

class FishDetector:
    """Fish detection and localization using computer vision"""
    
    def __init__(self):
        self.fish_cascade = None
        self.contour_detector = cv2.createBackgroundSubtractorMOG2()
        
        # Try to load OpenCV cascade classifier for fish detection
        # This would typically be a custom trained classifier
        cascade_path = "fish_cascade.xml"
        if Path(cascade_path).exists():
            self.fish_cascade = cv2.CascadeClassifier(cascade_path)
    
    def detect_fish(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect fish bounding boxes in image"""
        bounding_boxes = []
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Method 1: Cascade classifier (if available)
            if self.fish_cascade:
                fish_detections = self.fish_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
                )
                bounding_boxes.extend(fish_detections.tolist())
            
            # Method 2: Contour-based detection
            contour_boxes = self._detect_by_contours(image)
            bounding_boxes.extend(contour_boxes)
            
            # Method 3: Color-based detection
            color_boxes = self._detect_by_color(image)
            bounding_boxes.extend(color_boxes)
            
            # Remove duplicate/overlapping boxes
            bounding_boxes = self._remove_overlapping_boxes(bounding_boxes)
            
        except Exception as e:
            logger.error(f"Fish detection error: {e}")
        
        return bounding_boxes
    
    def _detect_by_contours(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect fish using contour analysis"""
        boxes = []
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Filter by area and aspect ratio
                area = cv2.contourArea(contour)
                if area < 500:  # Too small
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                
                # Fish typically have aspect ratios between 1.5 and 4
                if 1.2 <= aspect_ratio <= 5.0 and w > 50 and h > 30:
                    boxes.append((x, y, w, h))
        
        except Exception as e:
            logger.error(f"Contour detection error: {e}")
        
        return boxes
    
    def _detect_by_color(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect fish using color analysis"""
        boxes = []
        
        try:
            # Convert to HSV for better color filtering
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Define color ranges for common fish colors
            color_ranges = [
                # Silver/white fish
                ((0, 0, 150), (180, 50, 255)),
                # Blue fish
                ((100, 50, 50), (130, 255, 255)),
                # Yellow fish
                ((20, 100, 100), (30, 255, 255)),
                # Red fish
                ((0, 100, 100), (10, 255, 255)),
            ]
            
            combined_mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            
            for lower, upper in color_ranges:
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                combined_mask = cv2.bitwise_or(combined_mask, mask)
            
            # Morphological operations to clean up mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # Find contours in mask
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < 300:
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                if w > 40 and h > 30:
                    boxes.append((x, y, w, h))
        
        except Exception as e:
            logger.error(f"Color detection error: {e}")
        
        return boxes
    
    def _remove_overlapping_boxes(self, boxes: List[Tuple[int, int, int, int]], 
                                 overlap_threshold: float = 0.5) -> List[Tuple[int, int, int, int]]:
        """Remove overlapping bounding boxes using non-maximum suppression"""
        if not boxes:
            return boxes
        
        # Convert to format expected by OpenCV
        boxes_array = np.array(boxes)
        
        # Calculate areas
        areas = boxes_array[:, 2] * boxes_array[:, 3]
        
        # Sort by area (largest first)
        indices = np.argsort(areas)[::-1]
        
        keep = []
        while len(indices) > 0:
            # Keep the box with largest area
            current = indices[0]
            keep.append(current)
            
            if len(indices) == 1:
                break
            
            # Calculate IoU with remaining boxes
            current_box = boxes_array[current]
            remaining_boxes = boxes_array[indices[1:]]
            
            # Calculate intersection
            x1 = np.maximum(current_box[0], remaining_boxes[:, 0])
            y1 = np.maximum(current_box[1], remaining_boxes[:, 1])
            x2 = np.minimum(current_box[0] + current_box[2], 
                          remaining_boxes[:, 0] + remaining_boxes[:, 2])
            y2 = np.minimum(current_box[1] + current_box[3], 
                          remaining_boxes[:, 1] + remaining_boxes[:, 3])
            
            intersection = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
            
            # Calculate union
            union = areas[current] + areas[indices[1:]] - intersection
            
            # Calculate IoU
            iou = intersection / union
            
            # Keep boxes with IoU below threshold
            indices = indices[1:][iou < overlap_threshold]
        
        return [boxes[i] for i in keep]

class FishSpeciesIdentifier:
    """Main fish species identification system"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.database = FishDatabase()
        self.classifier = FishClassificationModel(model_path)
        self.detector = FishDetector()
        self.identification_history: List[IdentificationResult] = []
    
    async def identify_from_image(self, image: Union[np.ndarray, Image.Image, str],
                                location: Optional[Tuple[float, float]] = None,
                                water_temp: Optional[float] = None,
                                depth: Optional[float] = None) -> IdentificationResult:
        """Identify fish species from image"""
        start_time = time.time()
        
        try:
            # Load image if path provided
            if isinstance(image, str):
                image_path = image
                image = cv2.imread(image)
                if image is None:
                    raise ValueError(f"Could not load image from {image_path}")
            else:
                image_path = None
            
            # Convert PIL to numpy if needed
            if isinstance(image, Image.Image):
                image = np.array(image)
            
            # Detect fish in image
            bounding_boxes = self.detector.detect_fish(image)
            
            identifications = []
            
            # Identify each detected fish
            for bbox in bounding_boxes:
                x, y, w, h = bbox
                
                # Extract fish region
                fish_region = image[y:y+h, x:x+w]
                
                if fish_region.size == 0:
                    continue
                
                # Classify fish species
                species_id, confidence = self.classifier.predict(fish_region)
                
                # Get species information
                species = self.database.get_species(species_id)
                
                if species and confidence > 0.3:  # Minimum confidence threshold
                    identification = FishIdentification(
                        species=species,
                        confidence=confidence,
                        bounding_box=bbox,
                        key_features=self._extract_key_features(fish_region),
                        timestamp=datetime.now()
                    )
                    identifications.append(identification)
                    
                    # Record identification in database
                    self.database.record_identification(
                        identification, location, water_temp, depth, image_path
                    )
            
            processing_time = time.time() - start_time
            
            result = IdentificationResult(
                image_path=image_path,
                identifications=identifications,
                processing_time=processing_time,
                location=location,
                water_temperature=water_temp,
                depth=depth,
                timestamp=datetime.now()
            )
            
            self.identification_history.append(result)
            
            logger.info(f"Identified {len(identifications)} fish in {processing_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Fish identification error: {e}")
            return IdentificationResult()
    
    def _extract_key_features(self, fish_image: np.ndarray) -> List[str]:
        """Extract key visual features from fish image"""
        features = []
        
        try:
            # Color analysis
            hsv = cv2.cvtColor(fish_image, cv2.COLOR_BGR2HSV)
            
            # Dominant colors
            dominant_color = self._get_dominant_color(fish_image)
            if dominant_color:
                features.append(f"dominant_color_{dominant_color}")
            
            # Body shape analysis
            gray = cv2.cvtColor(fish_image, cv2.COLOR_BGR2GRAY)
            contours, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Aspect ratio
                x, y, w, h = cv2.boundingRect(largest_contour)
                aspect_ratio = w / h
                
                if aspect_ratio > 3:
                    features.append("elongated_body")
                elif aspect_ratio < 1.5:
                    features.append("deep_body")
                else:
                    features.append("moderate_body")
                
                # Fin detection (simplified)
                area = cv2.contourArea(largest_contour)
                hull = cv2.convexHull(largest_contour)
                hull_area = cv2.contourArea(hull)
                
                if area / hull_area < 0.8:  # Concave shape suggests fins
                    features.append("prominent_fins")
            
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
        
        return features
    
    def _get_dominant_color(self, image: np.ndarray) -> Optional[str]:
        """Get dominant color from image"""
        try:
            # Reshape image to list of pixels
            pixels = image.reshape(-1, 3)
            
            # Use k-means to find dominant colors
            from sklearn.cluster import KMeans
            
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Get the most frequent color
            colors = kmeans.cluster_centers_
            labels = kmeans.labels_
            
            # Count occurrences
            color_counts = np.bincount(labels)
            dominant_idx = np.argmax(color_counts)
            dominant_rgb = colors[dominant_idx]
            
            # Convert to color name
            return self._rgb_to_color_name(dominant_rgb)
            
        except ImportError:
            logger.warning("scikit-learn not available for color clustering")
        except Exception as e:
            logger.error(f"Dominant color extraction error: {e}")
        
        return None
    
    def _rgb_to_color_name(self, rgb: np.ndarray) -> str:
        """Convert RGB values to color name"""
        r, g, b = rgb
        
        # Simple color classification
        if r > 200 and g > 200 and b > 200:
            return "silver"
        elif r > g + 50 and r > b + 50:
            return "red"
        elif g > r + 30 and g > b + 30:
            return "green"
        elif b > r + 50 and b > g + 50:
            return "blue"
        elif r > 200 and g > 200 and b < 100:
            return "yellow"
        elif r < 100 and g < 100 and b < 100:
            return "dark"
        else:
            return "mixed"
    
    def create_identification_report(self, result: IdentificationResult) -> Dict[str, Any]:
        """Create detailed identification report"""
        report = {
            "timestamp": result.timestamp.isoformat(),
            "location": result.location,
            "environmental_conditions": {
                "water_temperature_c": result.water_temperature,
                "depth_m": result.depth
            },
            "processing_info": {
                "processing_time_seconds": result.processing_time,
                "num_detections": len(result.identifications)
            },
            "identifications": []
        }
        
        for identification in result.identifications:
            species = identification.species
            
            identification_data = {
                "species": {
                    "common_name": species.common_name,
                    "scientific_name": species.scientific_name,
                    "family": species.family
                },
                "confidence": identification.confidence,
                "bounding_box": identification.bounding_box,
                "key_features": identification.key_features,
                "species_info": {
                    "habitat": species.habitat.value,
                    "typical_size": species.typical_size.value,
                    "size_range_cm": [species.min_length_cm, species.max_length_cm],
                    "weight_range_kg": [species.min_weight_kg, species.max_weight_kg],
                    "conservation_status": species.conservation_status,
                    "edible": species.edible
                },
                "fishing_info": {
                    "best_methods": [method.value for method in species.fishing_methods],
                    "recommended_baits": species.best_baits,
                    "seasonal_patterns": species.seasonal_patterns
                },
                "regulations": species.regulations
            }
            
            report["identifications"].append(identification_data)
        
        return report
    
    def get_species_recommendations(self, location: Tuple[float, float],
                                  habitat: FishHabitat,
                                  season: str = None) -> List[FishSpecies]:
        """Get species recommendations for location and conditions"""
        # Get species for habitat
        candidates = self.database.get_species_by_habitat(habitat)
        
        # Filter by seasonal patterns if provided
        if season:
            seasonal_candidates = []
            for species in candidates:
                if season in species.seasonal_patterns:
                    seasonal_candidates.append(species)
            if seasonal_candidates:
                candidates = seasonal_candidates
        
        # Sort by some criteria (e.g., common in area)
        return candidates[:10]  # Return top 10
    
    def save_identification_image(self, image: np.ndarray, 
                                result: IdentificationResult,
                                output_path: str):
        """Save annotated identification image"""
        try:
            annotated_image = image.copy()
            
            # Draw bounding boxes and labels
            for identification in result.identifications:
                x, y, w, h = identification.bounding_box
                species = identification.species
                confidence = identification.confidence
                
                # Draw bounding box
                cv2.rectangle(annotated_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Draw label
                label = f"{species.common_name} ({confidence:.2f})"
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                
                # Background rectangle for text
                cv2.rectangle(annotated_image, (x, y - label_size[1] - 10), 
                             (x + label_size[0], y), (0, 255, 0), -1)
                
                # Text
                cv2.putText(annotated_image, label, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            # Save image
            cv2.imwrite(output_path, annotated_image)
            logger.info(f"Saved annotated image to {output_path}")
            
        except Exception as e:
            logger.error(f"Error saving identification image: {e}")

# Example usage and testing
async def example_usage():
    """Example of using the fish species identifier"""
    
    # Create identifier
    identifier = FishSpeciesIdentifier()
    
    # Simulate identification from image
    # In practice, this would be a real image file
    dummy_image = np.random.randint(0, 255, (400, 600, 3), dtype=np.uint8)
    
    # Identify fish with location and environmental data
    result = await identifier.identify_from_image(
        dummy_image,
        location=(25.7617, -80.1918),  # Miami coordinates
        water_temp=24.5,  # Celsius
        depth=15.0  # meters
    )
    
    # Print results
    print(f"Found {len(result.identifications)} fish:")
    for identification in result.identifications:
        species = identification.species
        print(f"- {species.common_name} ({species.scientific_name})")
        print(f"  Confidence: {identification.confidence:.2f}")
        print(f"  Features: {', '.join(identification.key_features)}")
        print(f"  Best baits: {', '.join(species.best_baits)}")
        print()
    
    # Create report
    report = identifier.create_identification_report(result)
    print("Full report:")
    print(json.dumps(report, indent=2))
    
    # Get species recommendations
    recommendations = identifier.get_species_recommendations(
        (25.7617, -80.1918), 
        FishHabitat.SALTWATER, 
        "summer"
    )
    
    print(f"\nRecommended species for this area:")
    for species in recommendations[:3]:
        print(f"- {species.common_name}: {species.description}")

if __name__ == "__main__":
    import time
    time.sleep = lambda x: None  # Disable sleep for testing
    asyncio.run(example_usage())