"""
Real-time Fish Detection and Learning Pipeline
Continuously processes video feed and learns from user feedback
"""

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
import threading
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import logging
from collections import deque
import json

logger = logging.getLogger(__name__)

@dataclass
class DetectionResult:
    """Fish detection result with tracking info"""
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    confidence: float
    species_prediction: str
    species_confidence: float
    track_id: Optional[int] = None
    features: Optional[np.ndarray] = None

class FishTracker:
    """Simple fish tracking for learning continuity"""
    
    def __init__(self, max_tracks: int = 50):
        self.tracks = {}
        self.next_id = 0
        self.max_tracks = max_tracks
        self.track_timeout = 30  # frames
        
    def update_tracks(self, detections: List[DetectionResult]) -> List[DetectionResult]:
        """Update tracks with new detections"""
        # Simple centroid tracking
        current_centroids = []
        for det in detections:
            x, y, w, h = det.bbox
            centroid = (x + w//2, y + h//2)
            current_centroids.append(centroid)
        
        # Match to existing tracks
        matched_detections = []
        
        for i, detection in enumerate(detections):
            best_track_id = None
            min_distance = float('inf')
            
            current_centroid = current_centroids[i]
            
            for track_id, track_info in self.tracks.items():
                if track_info['timeout'] > 0:
                    last_centroid = track_info['centroid']
                    distance = np.sqrt(
                        (current_centroid[0] - last_centroid[0])**2 + 
                        (current_centroid[1] - last_centroid[1])**2
                    )
                    
                    if distance < min_distance and distance < 100:  # threshold
                        min_distance = distance
                        best_track_id = track_id
            
            if best_track_id is not None:
                # Update existing track
                self.tracks[best_track_id]['centroid'] = current_centroid
                self.tracks[best_track_id]['timeout'] = self.track_timeout
                detection.track_id = best_track_id
            else:
                # Create new track
                if len(self.tracks) < self.max_tracks:
                    new_id = self.next_id
                    self.next_id += 1
                    self.tracks[new_id] = {
                        'centroid': current_centroid,
                        'timeout': self.track_timeout,
                        'species_votes': {},
                        'confidence_history': deque(maxlen=10)
                    }
                    detection.track_id = new_id
            
            matched_detections.append(detection)
        
        # Decrease timeout for all tracks
        expired_tracks = []
        for track_id in self.tracks:
            self.tracks[track_id]['timeout'] -= 1
            if self.tracks[track_id]['timeout'] <= 0:
                expired_tracks.append(track_id)
        
        # Remove expired tracks
        for track_id in expired_tracks:
            del self.tracks[track_id]
        
        return matched_detections
    
    def update_species_vote(self, track_id: int, species: str, confidence: float):
        """Update species prediction for a track"""
        if track_id in self.tracks:
            votes = self.tracks[track_id]['species_votes']
            if species not in votes:
                votes[species] = []
            votes[species].append(confidence)
            
            # Keep only recent votes
            if len(votes[species]) > 5:
                votes[species] = votes[species][-5:]
    
    def get_track_consensus(self, track_id: int) -> Tuple[str, float]:
        """Get consensus species prediction for a track"""
        if track_id not in self.tracks:
            return "unknown", 0.0
        
        votes = self.tracks[track_id]['species_votes']
        if not votes:
            return "unknown", 0.0
        
        # Calculate weighted average for each species
        species_scores = {}
        for species, confidences in votes.items():
            species_scores[species] = np.mean(confidences)
        
        best_species = max(species_scores, key=species_scores.get)
        return best_species, species_scores[best_species]

class RealTimeFishDetector:
    """Real-time fish detection with continuous learning"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load YOLOv5 or similar for fish detection
        self.detection_model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
        self.detection_model.to(self.device)
        
        # Load species classification model (from main system)
        self.species_model = None  # Will be loaded from adaptive system
        
        # Preprocessing transforms
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                               std=[0.229, 0.224, 0.225])
        ])
        
        # Fish tracker
        self.tracker = FishTracker()
        
        # Processing parameters
        self.min_confidence = 0.3
        self.target_fps = 30
        
        # Callbacks for learning system
        self.on_detection: Optional[Callable] = None
        self.on_track_update: Optional[Callable] = None
        
    def set_species_model(self, model):
        """Set species classification model from adaptive system"""
        self.species_model = model
        
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[DetectionResult]]:
        """Process single frame and return annotated frame with detections"""
        
        # Run fish detection
        results = self.detection_model(frame)
        detections = []
        
        # Filter for fish-like objects
        fish_classes = ['fish']  # Extend based on model classes
        
        for *box, conf, cls in results.xyxy[0].cpu().numpy():
            if conf > self.min_confidence:
                x1, y1, x2, y2 = map(int, box)
                w, h = x2 - x1, y2 - y1
                
                # Extract fish region for species classification
                fish_region = frame[y1:y2, x1:x2]
                
                # Predict species if model is available
                species_pred, species_conf = self._predict_species(fish_region)
                
                detection = DetectionResult(
                    bbox=(x1, y1, w, h),
                    confidence=conf,
                    species_prediction=species_pred,
                    species_confidence=species_conf
                )
                
                detections.append(detection)
        
        # Update tracking
        tracked_detections = self.tracker.update_tracks(detections)
        
        # Update species votes for tracks
        for detection in tracked_detections:
            if detection.track_id is not None:
                self.tracker.update_species_vote(
                    detection.track_id, 
                    detection.species_prediction, 
                    detection.species_confidence
                )
        
        # Get consensus predictions for stable tracks
        final_detections = []
        for detection in tracked_detections:
            if detection.track_id is not None:
                consensus_species, consensus_conf = self.tracker.get_track_consensus(detection.track_id)
                
                # Update detection with consensus
                if consensus_conf > detection.species_confidence:
                    detection.species_prediction = consensus_species
                    detection.species_confidence = consensus_conf
            
            final_detections.append(detection)
        
        # Create annotated frame
        annotated_frame = self._annotate_frame(frame.copy(), final_detections)
        
        # Trigger callbacks for learning system
        if self.on_detection:
            asyncio.create_task(self.on_detection(final_detections))
        
        return annotated_frame, final_detections
    
    def _predict_species(self, fish_region: np.ndarray) -> Tuple[str, float]:
        """Predict fish species from cropped region"""
        if self.species_model is None or fish_region.size == 0:
            return "unknown", 0.0
        
        try:
            # Preprocess fish region
            input_tensor = self.transform(fish_region).unsqueeze(0).to(self.device)
            
            # Get prediction
            with torch.no_grad():
                logits, features = self.species_model(input_tensor)
                probabilities = F.softmax(logits, dim=1)
                
                # Get top prediction
                top_prob, top_class = torch.max(probabilities, 1)
                
                # Convert class index to species name (would need mapping)
                species_names = ["king_salmon", "coho_salmon", "pink_salmon", 
                               "sockeye_salmon", "chum_salmon", "steelhead", 
                               "halibut", "lingcod", "rockfish", "dungeness_crab"]
                
                if top_class.item() < len(species_names):
                    species = species_names[top_class.item()]
                else:
                    species = "unknown"
                
                return species, top_prob.item()
                
        except Exception as e:
            logger.error(f"Species prediction error: {e}")
            return "unknown", 0.0
    
    def _annotate_frame(self, frame: np.ndarray, detections: List[DetectionResult]) -> np.ndarray:
        """Annotate frame with detection boxes and predictions"""
        
        for detection in detections:
            x, y, w, h = detection.bbox
            
            # Choose color based on confidence
            if detection.species_confidence > 0.8:
                color = (0, 255, 0)  # Green - high confidence
            elif detection.species_confidence > 0.5:
                color = (0, 255, 255)  # Yellow - medium confidence
            else:
                color = (0, 0, 255)  # Red - low confidence
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw species prediction
            label = f"{detection.species_prediction} ({detection.species_confidence:.2f})"
            if detection.track_id is not None:
                label = f"ID:{detection.track_id} " + label
            
            # Background for text
            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x, y - label_h - 10), (x + label_w, y), color, -1)
            
            # Text
            cv2.putText(frame, label, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame

class CameraManager:
    """Manages camera input and frame processing"""
    
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None
        self.is_running = False
        self.frame_callback: Optional[Callable] = None
        self.processing_thread = None
        
    def start(self) -> bool:
        """Start camera capture"""
        self.cap = cv2.VideoCapture(self.camera_index)
        
        if not self.cap.isOpened():
            logger.error(f"Failed to open camera {self.camera_index}")
            return False
        
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.start()
        
        logger.info("Camera started successfully")
        return True
    
    def stop(self):
        """Stop camera capture"""
        self.is_running = False
        
        if self.processing_thread:
            self.processing_thread.join()
        
        if self.cap:
            self.cap.release()
        
        logger.info("Camera stopped")
    
    def set_frame_callback(self, callback: Callable[[np.ndarray], None]):
        """Set callback for processed frames"""
        self.frame_callback = callback
    
    def _processing_loop(self):
        """Main camera processing loop"""
        frame_time = 1.0 / 30  # Target 30 FPS
        
        while self.is_running:
            start_time = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                continue
            
            # Trigger frame callback
            if self.frame_callback:
                try:
                    self.frame_callback(frame)
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")
            
            # Maintain frame rate
            elapsed = time.time() - start_time
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)

class AdaptiveLearningPipeline:
    """Complete pipeline for adaptive computer vision learning"""
    
    def __init__(self, adaptive_system):
        self.adaptive_system = adaptive_system
        self.detector = RealTimeFishDetector()
        self.camera_manager = CameraManager()
        
        # Connect components
        self.detector.set_species_model(adaptive_system.model)
        self.detector.on_detection = self._on_detection_callback
        self.camera_manager.set_frame_callback(self._on_frame_callback)
        
        # Current session
        self.current_session_id: Optional[str] = None
        
        # Frame processing
        self.latest_frame: Optional[np.ndarray] = None
        self.processing_active = True
        
    async def start_session(self, session_id: str):
        """Start adaptive learning session"""
        self.current_session_id = session_id
        
        # Start camera
        if not self.camera_manager.start():
            raise RuntimeError("Failed to start camera")
        
        logger.info(f"Started adaptive learning pipeline for session {session_id}")
    
    def stop_session(self):
        """Stop current session"""
        self.camera_manager.stop()
        self.current_session_id = None
        
        logger.info("Stopped adaptive learning pipeline")
    
    def _on_frame_callback(self, frame: np.ndarray):
        """Process incoming camera frames"""
        if not self.processing_active or self.current_session_id is None:
            return
        
        try:
            # Process frame through detector
            annotated_frame, detections = self.detector.process_frame(frame)
            
            # Store latest frame and detections
            self.latest_frame = annotated_frame
            
            # Convert detections for adaptive system
            predictions = []
            for detection in detections:
                prediction_data = {
                    "bbox": {
                        "x": detection.bbox[0],
                        "y": detection.bbox[1], 
                        "w": detection.bbox[2],
                        "h": detection.bbox[3]
                    },
                    "species": detection.species_prediction,
                    "confidence": detection.species_confidence,
                    "track_id": detection.track_id
                }
                predictions.append(prediction_data)
            
            # Send to adaptive system asynchronously
            if predictions:
                asyncio.create_task(
                    self.adaptive_system.process_frame_predictions(
                        self.current_session_id, frame, 
                        [self._convert_to_prediction(p, frame.shape) for p in predictions]
                    )
                )
                
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
    
    def _convert_to_prediction(self, pred_data: Dict, frame_shape: Tuple) -> 'Prediction':
        """Convert prediction data to Prediction object"""
        from main import Prediction
        from datetime import datetime
        
        return Prediction(
            timestamp=datetime.now(),
            bbox=(pred_data["bbox"]["x"], pred_data["bbox"]["y"],
                  pred_data["bbox"]["w"], pred_data["bbox"]["h"]),
            species=pred_data["species"],
            confidence=pred_data["confidence"],
            features=np.array([]),  # Would be extracted by model
            frame_id=str(time.time())
        )
    
    async def _on_detection_callback(self, detections: List[DetectionResult]):
        """Handle detections for learning"""
        if self.current_session_id is None:
            return
        
        # Log detections for analysis
        logger.debug(f"Detected {len(detections)} fish in frame")
        
        # Could implement additional logic here for:
        # - Quality assessment of detections
        # - Confidence-based filtering
        # - Temporal consistency checks
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """Get latest processed frame"""
        return self.latest_frame

if __name__ == "__main__":
    # Test the real-time pipeline
    import asyncio
    from main import AdaptiveCVTrainingSystem
    
    async def test_pipeline():
        # Create adaptive system
        cv_system = AdaptiveCVTrainingSystem()
        
        # Create pipeline
        pipeline = AdaptiveLearningPipeline(cv_system)
        
        # Start session
        session_id = await cv_system.start_training_session("test_user", "test_boat")
        await pipeline.start_session(session_id)
        
        # Run for 30 seconds
        await asyncio.sleep(30)
        
        # Stop
        pipeline.stop_session()
    
    # Run test
    asyncio.run(test_pipeline())