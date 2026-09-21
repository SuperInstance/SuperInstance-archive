"""
Adaptive Computer Vision Training System
Self-improving AI through continuous user feedback and voice commands
"""

import asyncio
import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import transforms, models
import speech_recognition as sr
import whisper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
from collections import defaultdict, deque
import pickle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Adaptive CV Training System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@dataclass
class TrainingSession:
    """Represents an active training session"""
    session_id: str
    user_id: str
    boat_id: Optional[str]
    start_time: datetime
    voice_commands: List[Dict]
    predictions: List[Dict]
    corrections: List[Dict]
    active_totes: Dict[str, str]  # tote_location -> species_name
    is_active: bool = True

@dataclass
class Prediction:
    """Real-time prediction with confidence"""
    timestamp: datetime
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    species: str
    confidence: float
    features: np.ndarray
    frame_id: str

@dataclass
class TrainingExample:
    """Training example with ground truth"""
    image_data: np.ndarray
    bbox: Tuple[int, int, int, int]
    species: str
    confidence_score: float
    user_id: str
    boat_id: Optional[str]
    timestamp: datetime

class VoiceCommandProcessor:
    """Processes voice commands to extract training instructions"""
    
    def __init__(self):
        self.whisper_model = whisper.load_model("base")
        self.species_keywords = {
            "king salmon": ["king", "chinook", "large salmon", "big salmon"],
            "coho salmon": ["coho", "silver", "silver salmon"],
            "pink salmon": ["pink", "humpy", "humpback"],
            "sockeye salmon": ["sockeye", "red", "red salmon"],
            "chum salmon": ["chum", "dog", "dog salmon"],
            "steelhead": ["steelhead", "steel head"],
            "halibut": ["halibut", "barn door"],
            "lingcod": ["lingcod", "ling cod"],
            "rockfish": ["rockfish", "rock fish", "red snapper"],
            "dungeness crab": ["dungeness", "crab"]
        }
        self.tote_keywords = ["tote", "box", "container", "bin", "cooler"]
        
    def process_audio(self, audio_data: bytes) -> Optional[Dict]:
        """Process audio to extract training commands"""
        try:
            # Convert audio to text using Whisper
            result = self.whisper_model.transcribe(audio_data)
            text = result["text"].lower()
            
            return self._parse_command(text)
            
        except Exception as e:
            logger.error(f"Voice processing error: {e}")
            return None
    
    def _parse_command(self, text: str) -> Optional[Dict]:
        """Parse text command for training instructions"""
        command_type = None
        species = None
        tote_location = None
        
        # Check for tote assignment commands
        if any(keyword in text for keyword in self.tote_keywords):
            command_type = "tote_assignment"
            
            # Extract species
            for species_name, keywords in self.species_keywords.items():
                if any(keyword in text for keyword in keywords):
                    species = species_name
                    break
            
            # Extract location (left, right, port, starboard, etc.)
            location_keywords = {
                "left": ["left", "port"],
                "right": ["right", "starboard"],
                "front": ["front", "bow", "forward"],
                "back": ["back", "stern", "aft"],
                "center": ["center", "middle"]
            }
            
            for location, keywords in location_keywords.items():
                if any(keyword in text for keyword in keywords):
                    tote_location = location
                    break
        
        # Check for correction commands
        elif "that's" in text or "this is" in text or "actually" in text:
            command_type = "correction"
            
            # Extract what it actually is
            for species_name, keywords in self.species_keywords.items():
                if any(keyword in text for keyword in keywords):
                    species = species_name
                    break
        
        # Check for training start/stop commands
        elif "start training" in text or "begin training" in text:
            command_type = "start_training"
        elif "stop training" in text or "end training" in text:
            command_type = "stop_training"
        
        if command_type:
            return {
                "type": command_type,
                "species": species,
                "tote_location": tote_location,
                "raw_text": text,
                "timestamp": datetime.now()
            }
        
        return None

class AdaptiveFishClassifier(nn.Module):
    """Adaptive fish classification model that can learn continuously"""
    
    def __init__(self, num_base_classes: int = 50, embedding_dim: int = 512):
        super().__init__()
        
        # Use pre-trained ResNet as backbone
        self.backbone = models.resnet50(pretrained=True)
        self.backbone.fc = nn.Linear(self.backbone.fc.in_features, embedding_dim)
        
        # Adaptive classification head
        self.classifier = nn.Linear(embedding_dim, num_base_classes)
        
        # Species-specific adapters (learned per user/boat)
        self.species_adapters = nn.ModuleDict()
        
        # Feature memory for few-shot learning
        self.feature_memory = {}
        self.species_prototypes = {}
        
    def forward(self, x, species_adapter=None):
        # Extract features
        features = self.backbone(x)
        
        # Apply species-specific adapter if available
        if species_adapter and species_adapter in self.species_adapters:
            adapted_features = self.species_adapters[species_adapter](features)
        else:
            adapted_features = features
        
        # Classification
        logits = self.classifier(adapted_features)
        
        return logits, features
    
    def add_species_adapter(self, species_name: str, user_id: str):
        """Add a new species adapter for personalized learning"""
        adapter_key = f"{user_id}_{species_name}"
        if adapter_key not in self.species_adapters:
            self.species_adapters[adapter_key] = nn.Sequential(
                nn.Linear(512, 256),
                nn.ReLU(),
                nn.Linear(256, 512)
            )
    
    def update_prototype(self, species: str, features: torch.Tensor):
        """Update species prototype for few-shot learning"""
        if species not in self.species_prototypes:
            self.species_prototypes[species] = features.mean(dim=0)
        else:
            # Moving average update
            alpha = 0.1
            self.species_prototypes[species] = (
                (1 - alpha) * self.species_prototypes[species] + 
                alpha * features.mean(dim=0)
            )

class TrainingDataManager:
    """Manages training data collection and storage"""
    
    def __init__(self, db_path: str = "adaptive_training.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize SQLite database for training data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                boat_id TEXT,
                start_time DATETIME,
                end_time DATETIME,
                total_predictions INTEGER,
                total_corrections INTEGER,
                accuracy_improvement REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_examples (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp DATETIME,
                species TEXT,
                bbox_x INTEGER,
                bbox_y INTEGER,
                bbox_w INTEGER,
                bbox_h INTEGER,
                confidence REAL,
                user_id TEXT,
                boat_id TEXT,
                image_path TEXT,
                features BLOB
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_commands (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                timestamp DATETIME,
                command_type TEXT,
                species TEXT,
                tote_location TEXT,
                raw_text TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_performance (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                boat_id TEXT,
                species TEXT,
                precision_score REAL,
                recall_score REAL,
                f1_score REAL,
                updated_at DATETIME
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_training_example(self, example: TrainingExample, session_id: str, image_path: str):
        """Save a training example to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO training_examples (
                id, session_id, timestamp, species, bbox_x, bbox_y, bbox_w, bbox_h,
                confidence, user_id, boat_id, image_path, features
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            session_id,
            example.timestamp,
            example.species,
            example.bbox[0], example.bbox[1], example.bbox[2], example.bbox[3],
            example.confidence_score,
            example.user_id,
            example.boat_id,
            image_path,
            pickle.dumps(example.image_data)
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_training_data(self, user_id: str, species: Optional[str] = None) -> List[Dict]:
        """Retrieve training data for a specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM training_examples WHERE user_id = ?"
        params = [user_id]
        
        if species:
            query += " AND species = ?"
            params.append(species)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(zip([col[0] for col in cursor.description], row)) for row in results]

class AdaptiveCVTrainingSystem:
    """Main system for adaptive computer vision training"""
    
    def __init__(self):
        self.voice_processor = VoiceCommandProcessor()
        self.model = AdaptiveFishClassifier()
        self.data_manager = TrainingDataManager()
        
        # Active training sessions
        self.active_sessions: Dict[str, TrainingSession] = {}
        
        # Real-time prediction queue
        self.prediction_queue = deque(maxlen=1000)
        
        # WebSocket connections
        self.connections: List[WebSocket] = []
        
        # Training thread
        self.training_thread = None
        self.training_active = False
        
    async def start_training_session(self, user_id: str, boat_id: Optional[str] = None) -> str:
        """Start a new adaptive training session"""
        session_id = str(uuid.uuid4())
        
        session = TrainingSession(
            session_id=session_id,
            user_id=user_id,
            boat_id=boat_id,
            start_time=datetime.now(),
            voice_commands=[],
            predictions=[],
            corrections=[],
            active_totes={}
        )
        
        self.active_sessions[session_id] = session
        
        logger.info(f"Started training session {session_id} for user {user_id}")
        return session_id
    
    async def process_voice_command(self, session_id: str, audio_data: bytes):
        """Process voice command for training"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        command = self.voice_processor.process_audio(audio_data)
        
        if command:
            session.voice_commands.append(command)
            
            if command["type"] == "tote_assignment":
                # Update active tote mappings
                if command["tote_location"] and command["species"]:
                    session.active_totes[command["tote_location"]] = command["species"]
                    
                    # Add species adapter if needed
                    self.model.add_species_adapter(command["species"], session.user_id)
                    
                    logger.info(f"Tote assignment: {command['tote_location']} -> {command['species']}")
            
            elif command["type"] == "correction":
                # Handle correction - use latest prediction
                if session.predictions and command["species"]:
                    latest_prediction = session.predictions[-1]
                    correction = {
                        "prediction_id": latest_prediction.get("id"),
                        "correct_species": command["species"],
                        "timestamp": datetime.now()
                    }
                    session.corrections.append(correction)
                    
                    logger.info(f"Correction: {latest_prediction.get('species')} -> {command['species']}")
            
            # Broadcast command to connected clients
            await self.broadcast_update({
                "type": "voice_command",
                "session_id": session_id,
                "command": command
            })
    
    async def process_frame_predictions(self, session_id: str, frame: np.ndarray, 
                                     predictions: List[Prediction]):
        """Process real-time predictions and create training examples"""
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        
        for prediction in predictions:
            # Store prediction
            pred_data = {
                "id": str(uuid.uuid4()),
                "timestamp": prediction.timestamp,
                "bbox": prediction.bbox,
                "species": prediction.species,
                "confidence": prediction.confidence,
                "frame_id": prediction.frame_id
            }
            session.predictions.append(pred_data)
            
            # Check if fish is moving toward a tote (ground truth labeling)
            tote_location = self._detect_fish_destination(prediction.bbox, frame)
            
            if tote_location and tote_location in session.active_totes:
                # Create training example with ground truth
                ground_truth_species = session.active_totes[tote_location]
                
                # Extract fish region from frame
                x, y, w, h = prediction.bbox
                fish_region = frame[y:y+h, x:x+w]
                
                training_example = TrainingExample(
                    image_data=fish_region,
                    bbox=prediction.bbox,
                    species=ground_truth_species,
                    confidence_score=1.0,  # Ground truth confidence
                    user_id=session.user_id,
                    boat_id=session.boat_id,
                    timestamp=prediction.timestamp
                )
                
                # Save training example
                image_path = f"training_images/{session_id}_{pred_data['id']}.jpg"
                cv2.imwrite(image_path, fish_region)
                self.data_manager.save_training_example(training_example, session_id, image_path)
                
                # Update model with new example
                await self._update_model_online(training_example, session.user_id)
                
                logger.info(f"Created training example: {prediction.species} -> {ground_truth_species}")
    
    def _detect_fish_destination(self, bbox: Tuple[int, int, int, int], 
                               frame: np.ndarray) -> Optional[str]:
        """Detect which tote the fish is heading toward"""
        # Simple heuristic: check if fish is in certain regions of frame
        x, y, w, h = bbox
        center_x = x + w // 2
        center_y = y + h // 2
        
        frame_height, frame_width = frame.shape[:2]
        
        # Define tote regions (these would be configurable)
        if center_x < frame_width * 0.3:
            return "left"
        elif center_x > frame_width * 0.7:
            return "right"
        elif center_y < frame_height * 0.3:
            return "front"
        elif center_y > frame_height * 0.7:
            return "back"
        else:
            return "center"
    
    async def _update_model_online(self, example: TrainingExample, user_id: str):
        """Update model with new training example"""
        try:
            # Convert to tensor
            transform = transforms.Compose([
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                   std=[0.229, 0.224, 0.225])
            ])
            
            input_tensor = transform(example.image_data).unsqueeze(0)
            
            # Get current prediction
            with torch.no_grad():
                logits, features = self.model(input_tensor)
            
            # Update species prototype
            self.model.update_prototype(example.species, features)
            
            # TODO: Implement online learning update
            # This could use techniques like:
            # - Few-shot learning with prototypical networks
            # - Meta-learning for quick adaptation
            # - Continual learning to avoid catastrophic forgetting
            
        except Exception as e:
            logger.error(f"Error updating model online: {e}")
    
    async def broadcast_update(self, message: Dict):
        """Broadcast update to all connected WebSocket clients"""
        if self.connections:
            disconnected = []
            for connection in self.connections:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected clients
            for conn in disconnected:
                self.connections.remove(conn)
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a training session"""
        if session_id not in self.active_sessions:
            return {}
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "start_time": session.start_time,
            "total_predictions": len(session.predictions),
            "total_corrections": len(session.corrections),
            "active_totes": session.active_totes,
            "voice_commands": len(session.voice_commands)
        }

# Global system instance
cv_system = AdaptiveCVTrainingSystem()

# API Models
class StartSessionRequest(BaseModel):
    user_id: str
    boat_id: Optional[str] = None

class ProcessFrameRequest(BaseModel):
    session_id: str
    frame_data: str  # base64 encoded frame
    predictions: List[Dict]

# API Endpoints
@app.post("/api/start-session")
async def start_session(request: StartSessionRequest):
    """Start a new adaptive training session"""
    session_id = await cv_system.start_training_session(
        request.user_id, 
        request.boat_id
    )
    return {"session_id": session_id}

@app.get("/api/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Get training session statistics"""
    stats = cv_system.get_session_stats(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats

@app.post("/api/session/{session_id}/frame")
async def process_frame(session_id: str, request: ProcessFrameRequest):
    """Process frame with predictions for training"""
    # Decode frame data
    import base64
    frame_bytes = base64.b64decode(request.frame_data)
    nparr = np.frombuffer(frame_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Convert predictions
    predictions = []
    for pred_data in request.predictions:
        prediction = Prediction(
            timestamp=datetime.now(),
            bbox=(pred_data["bbox"]["x"], pred_data["bbox"]["y"], 
                  pred_data["bbox"]["w"], pred_data["bbox"]["h"]),
            species=pred_data["species"],
            confidence=pred_data["confidence"],
            features=np.array([]),  # Would be extracted by model
            frame_id=str(uuid.uuid4())
        )
        predictions.append(prediction)
    
    await cv_system.process_frame_predictions(session_id, frame, predictions)
    return {"status": "processed"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    cv_system.connections.append(websocket)
    
    try:
        while True:
            # Handle incoming messages (voice commands, etc.)
            data = await websocket.receive_bytes()
            
            # Process as voice command
            await cv_system.process_voice_command(session_id, data)
            
    except WebSocketDisconnect:
        cv_system.connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    
    # Create necessary directories
    Path("training_images").mkdir(exist_ok=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8100)