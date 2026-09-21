"""
FishingLog Integration Module
Connects adaptive CV training with existing FishingLog Pro system
"""

import asyncio
import json
import logging
import sqlite3
import requests
import numpy as np
import cv2
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import base64
import threading
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class FishingLogIntegrationConfig:
    """Configuration for FishingLog integration"""
    fishinglog_api_url: str = "http://localhost:3000/api"
    cv_training_api_url: str = "http://localhost:8100/api"
    integration_enabled: bool = True
    auto_sync_interval: int = 30  # seconds
    image_quality_threshold: float = 0.7
    confidence_threshold: float = 0.6
    batch_size: int = 10

class FishingLogEntry:
    """FishingLog entry data structure"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.start_time = data.get('startTime')
        self.end_time = data.get('endTime')
        self.location = data.get('location', {})
        self.catches = data.get('catches', [])
        self.weather = data.get('weather', {})
        self.photos = data.get('photos', [])
        self.notes = data.get('notes', '')
        self.user_id = data.get('userId')
        self.boat_id = data.get('boatId')

class FishCatch:
    """Individual fish catch data"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.species = data.get('species')
        self.length = data.get('length')
        self.weight = data.get('weight')
        self.timestamp = data.get('timestamp')
        self.location = data.get('location', {})
        self.photo_path = data.get('photoPath')
        self.bait_used = data.get('baitUsed')
        self.depth = data.get('depth')
        self.kept = data.get('kept', False)
        self.released = data.get('released', True)

class CVPredictionResult:
    """Computer vision prediction result"""
    def __init__(self, data: Dict[str, Any]):
        self.species = data.get('species')
        self.confidence = data.get('confidence', 0.0)
        self.bbox = data.get('bbox', {})
        self.alternatives = data.get('alternatives', [])
        self.image_quality = data.get('image_quality', 1.0)
        self.timestamp = data.get('timestamp')

class FishingLogIntegrationService:
    """Service for integrating adaptive CV training with FishingLog"""
    
    def __init__(self, config: FishingLogIntegrationConfig):
        self.config = config
        self.db_path = "fishinglog_integration.db"
        
        # API connections
        self.fishinglog_session = requests.Session()
        self.cv_training_session = requests.Session()
        
        # Active sessions tracking
        self.active_sessions: Dict[str, str] = {}  # fishinglog_session_id -> cv_session_id
        
        # Sync queues
        self.prediction_queue = asyncio.Queue(maxsize=1000)
        self.correction_queue = asyncio.Queue(maxsize=1000)
        
        # Background tasks
        self.sync_task = None
        self.prediction_task = None
        self.is_running = False
        
        # Performance tracking
        self.integration_stats = {
            'total_predictions': 0,
            'successful_corrections': 0,
            'accuracy_improvements': 0,
            'last_sync': None
        }
        
        # Initialize database
        self.init_database()
    
    def init_database(self):
        """Initialize integration database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integration_sessions (
                fishinglog_session_id TEXT PRIMARY KEY,
                cv_session_id TEXT,
                user_id TEXT,
                boat_id TEXT,
                start_time DATETIME,
                end_time DATETIME,
                total_catches INTEGER,
                total_predictions INTEGER,
                accuracy_score REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prediction_corrections (
                id TEXT PRIMARY KEY,
                fishinglog_entry_id TEXT,
                cv_session_id TEXT,
                original_prediction TEXT,
                corrected_species TEXT,
                confidence_before REAL,
                confidence_after REAL,
                image_path TEXT,
                correction_source TEXT,
                timestamp DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_examples (
                id TEXT PRIMARY KEY,
                fishinglog_entry_id TEXT,
                image_path TEXT,
                species TEXT,
                confidence REAL,
                bbox_x INTEGER,
                bbox_y INTEGER,
                bbox_w INTEGER,
                bbox_h INTEGER,
                environmental_context TEXT,
                user_id TEXT,
                boat_id TEXT,
                timestamp DATETIME
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id TEXT PRIMARY KEY,
                sync_type TEXT,
                status TEXT,
                details TEXT,
                timestamp DATETIME
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def start_integration(self):
        """Start the integration service"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start background tasks
        self.sync_task = asyncio.create_task(self._sync_loop())
        self.prediction_task = asyncio.create_task(self._prediction_loop())
        
        logger.info("FishingLog integration service started")
    
    async def stop_integration(self):
        """Stop the integration service"""
        self.is_running = False
        
        if self.sync_task:
            self.sync_task.cancel()
        if self.prediction_task:
            self.prediction_task.cancel()
        
        logger.info("FishingLog integration service stopped")
    
    async def _sync_loop(self):
        """Main synchronization loop"""
        while self.is_running:
            try:
                await self._sync_fishing_sessions()
                await self._process_new_catches()
                await self._update_training_data()
                
                self.integration_stats['last_sync'] = datetime.now()
                
                # Log sync status
                await self._log_sync_event("periodic_sync", "success", "Regular sync completed")
                
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await self._log_sync_event("periodic_sync", "error", str(e))
            
            await asyncio.sleep(self.config.auto_sync_interval)
    
    async def _prediction_loop(self):
        """Process predictions from queue"""
        while self.is_running:
            try:
                # Process predictions
                prediction_data = await asyncio.wait_for(
                    self.prediction_queue.get(), timeout=5.0
                )
                
                await self._handle_prediction(prediction_data)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Prediction loop error: {e}")
    
    async def _sync_fishing_sessions(self):
        """Sync active fishing sessions with CV training"""
        try:
            # Get active FishingLog sessions
            response = await self._api_call(
                "GET", 
                f"{self.config.fishinglog_api_url}/sessions/active"
            )
            
            if response.status_code != 200:
                return
            
            active_sessions = response.json()
            
            for session_data in active_sessions:
                fishinglog_session_id = session_data['id']
                user_id = session_data['userId']
                boat_id = session_data.get('boatId')
                
                # Check if we have a corresponding CV session
                if fishinglog_session_id not in self.active_sessions:
                    # Start new CV training session
                    cv_session_id = await self._start_cv_session(user_id, boat_id)
                    if cv_session_id:
                        self.active_sessions[fishinglog_session_id] = cv_session_id
                        
                        # Save to database
                        await self._save_integration_session(
                            fishinglog_session_id, cv_session_id, user_id, boat_id
                        )
                        
                        logger.info(f"Started CV session {cv_session_id} for FishingLog session {fishinglog_session_id}")
                
        except Exception as e:
            logger.error(f"Error syncing fishing sessions: {e}")
    
    async def _process_new_catches(self):
        """Process new fish catches for training"""
        try:
            # Get recent catches since last sync
            last_sync = self.integration_stats.get('last_sync')
            if last_sync:
                since = last_sync.isoformat()
            else:
                since = (datetime.now() - timedelta(hours=1)).isoformat()
            
            response = await self._api_call(
                "GET",
                f"{self.config.fishinglog_api_url}/catches",
                params={'since': since, 'with_photos': 'true'}
            )
            
            if response.status_code != 200:
                return
            
            catches = response.json()
            
            for catch_data in catches:
                await self._process_catch_for_training(catch_data)
                
        except Exception as e:
            logger.error(f"Error processing new catches: {e}")
    
    async def _process_catch_for_training(self, catch_data: Dict[str, Any]):
        """Process individual catch for training data"""
        catch = FishCatch(catch_data)
        
        # Skip if no photo
        if not catch.photo_path:
            return
        
        # Get photo
        photo_response = await self._api_call(
            "GET",
            f"{self.config.fishinglog_api_url}/photos/{catch.photo_path}"
        )
        
        if photo_response.status_code != 200:
            return
        
        # Process image
        image_data = photo_response.content
        
        try:
            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Get CV session for this catch
            cv_session_id = await self._get_cv_session_for_catch(catch)
            
            if not cv_session_id:
                return
            
            # Make prediction
            prediction = await self._get_cv_prediction(image, cv_session_id)
            
            if not prediction:
                return
            
            # Check if prediction matches logged species
            if prediction.species != catch.species:
                # This is a correction opportunity
                await self._create_training_correction(
                    catch, prediction, image, cv_session_id
                )
            else:
                # This is positive training data
                await self._create_positive_training_example(
                    catch, prediction, image, cv_session_id
                )
            
            self.integration_stats['total_predictions'] += 1
            
        except Exception as e:
            logger.error(f"Error processing catch photo: {e}")
    
    async def _get_cv_session_for_catch(self, catch: FishCatch) -> Optional[str]:
        """Get CV session ID for a catch"""
        # In practice, would need to match based on timing and user
        # For now, return first active session
        if self.active_sessions:
            return list(self.active_sessions.values())[0]
        return None
    
    async def _get_cv_prediction(self, image: np.ndarray, cv_session_id: str) -> Optional[CVPredictionResult]:
        """Get CV prediction for image"""
        try:
            # Encode image
            _, buffer = cv2.imencode('.jpg', image)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Call CV API
            response = await self._api_call(
                "POST",
                f"{self.config.cv_training_api_url}/predict",
                json={
                    'session_id': cv_session_id,
                    'image_data': image_base64
                }
            )
            
            if response.status_code == 200:
                prediction_data = response.json()
                return CVPredictionResult(prediction_data)
            
        except Exception as e:
            logger.error(f"Error getting CV prediction: {e}")
        
        return None
    
    async def _create_training_correction(self, catch: FishCatch, 
                                        prediction: CVPredictionResult,
                                        image: np.ndarray, cv_session_id: str):
        """Create training correction from mismatched prediction"""
        
        # Send correction to CV training system
        correction_data = {
            'session_id': cv_session_id,
            'predicted_species': prediction.species,
            'correct_species': catch.species,
            'confidence': prediction.confidence,
            'image_data': self._encode_image(image),
            'correction_type': 'fishinglog_integration',
            'context': {
                'location': catch.location,
                'depth': catch.depth,
                'bait': catch.bait_used,
                'timestamp': catch.timestamp
            }
        }
        
        try:
            response = await self._api_call(
                "POST",
                f"{self.config.cv_training_api_url}/correction",
                json=correction_data
            )
            
            if response.status_code == 200:
                # Save correction to database
                await self._save_prediction_correction(
                    catch, prediction, cv_session_id, 'fishinglog_integration'
                )
                
                self.integration_stats['successful_corrections'] += 1
                logger.info(f"Created training correction: {prediction.species} -> {catch.species}")
            
        except Exception as e:
            logger.error(f"Error creating training correction: {e}")
    
    async def _create_positive_training_example(self, catch: FishCatch,
                                              prediction: CVPredictionResult,
                                              image: np.ndarray, cv_session_id: str):
        """Create positive training example from correct prediction"""
        
        training_data = {
            'session_id': cv_session_id,
            'species': catch.species,
            'confidence': prediction.confidence,
            'image_data': self._encode_image(image),
            'context': {
                'location': catch.location,
                'depth': catch.depth,
                'bait': catch.bait_used,
                'timestamp': catch.timestamp
            }
        }
        
        try:
            response = await self._api_call(
                "POST",
                f"{self.config.cv_training_api_url}/positive_example",
                json=training_data
            )
            
            if response.status_code == 200:
                # Save training example to database
                await self._save_training_example(catch, prediction, image, cv_session_id)
                
                logger.info(f"Created positive training example for {catch.species}")
            
        except Exception as e:
            logger.error(f"Error creating positive training example: {e}")
    
    async def _start_cv_session(self, user_id: str, boat_id: Optional[str]) -> Optional[str]:
        """Start new CV training session"""
        try:
            response = await self._api_call(
                "POST",
                f"{self.config.cv_training_api_url}/start-session",
                json={
                    'user_id': user_id,
                    'boat_id': boat_id
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('session_id')
            
        except Exception as e:
            logger.error(f"Error starting CV session: {e}")
        
        return None
    
    async def _update_training_data(self):
        """Update training data with latest corrections"""
        try:
            # Get recent corrections that need processing
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM prediction_corrections 
                WHERE timestamp > datetime('now', '-1 hour')
                ORDER BY timestamp DESC
            """)
            
            corrections = cursor.fetchall()
            conn.close()
            
            # Process corrections in batches
            for i in range(0, len(corrections), self.config.batch_size):
                batch = corrections[i:i + self.config.batch_size]
                await self._process_correction_batch(batch)
            
        except Exception as e:
            logger.error(f"Error updating training data: {e}")
    
    async def _process_correction_batch(self, corrections: List[Tuple]):
        """Process batch of corrections"""
        for correction_data in corrections:
            # Extract correction info
            correction_id = correction_data[0]
            cv_session_id = correction_data[2]
            
            # Could implement batch training updates here
            # For now, individual corrections are handled in real-time
            pass
    
    def _encode_image(self, image: np.ndarray) -> str:
        """Encode image to base64"""
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')
    
    async def _api_call(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make async API call"""
        loop = asyncio.get_event_loop()
        
        if method.upper() == 'GET':
            return await loop.run_in_executor(
                None, self.fishinglog_session.get, url, kwargs
            )
        elif method.upper() == 'POST':
            return await loop.run_in_executor(
                None, self.fishinglog_session.post, url, kwargs
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
    
    async def _save_integration_session(self, fishinglog_session_id: str, 
                                      cv_session_id: str, user_id: str, 
                                      boat_id: Optional[str]):
        """Save integration session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO integration_sessions (
                fishinglog_session_id, cv_session_id, user_id, boat_id, start_time
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            fishinglog_session_id, cv_session_id, user_id, boat_id, datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    async def _save_prediction_correction(self, catch: FishCatch, 
                                        prediction: CVPredictionResult,
                                        cv_session_id: str, correction_source: str):
        """Save prediction correction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO prediction_corrections (
                id, fishinglog_entry_id, cv_session_id, original_prediction,
                corrected_species, confidence_before, confidence_after,
                correction_source, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{catch.id}_{cv_session_id}_{int(time.time())}",
            catch.id,
            cv_session_id,
            prediction.species,
            catch.species,
            prediction.confidence,
            1.0,  # Perfect confidence for manual identification
            correction_source,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    async def _save_training_example(self, catch: FishCatch, 
                                   prediction: CVPredictionResult,
                                   image: np.ndarray, cv_session_id: str):
        """Save training example to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save image temporarily
        image_filename = f"training_{catch.id}_{int(time.time())}.jpg"
        image_path = f"training_images/{image_filename}"
        cv2.imwrite(image_path, image)
        
        cursor.execute("""
            INSERT INTO training_examples (
                id, fishinglog_entry_id, image_path, species, confidence,
                environmental_context, user_id, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"{catch.id}_{cv_session_id}_{int(time.time())}",
            catch.id,
            image_path,
            catch.species,
            prediction.confidence,
            json.dumps({
                'location': catch.location,
                'depth': catch.depth,
                'bait': catch.bait_used
            }),
            catch.user_id if hasattr(catch, 'user_id') else 'unknown',
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    async def _log_sync_event(self, sync_type: str, status: str, details: str):
        """Log synchronization event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sync_log (id, sync_type, status, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            f"{sync_type}_{int(time.time())}",
            sync_type,
            status,
            details,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    # Public API methods
    
    async def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            **self.integration_stats,
            'active_sessions': len(self.active_sessions),
            'config': asdict(self.config),
            'is_running': self.is_running
        }
    
    async def get_user_training_progress(self, user_id: str) -> Dict[str, Any]:
        """Get training progress for specific user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get correction stats
        cursor.execute("""
            SELECT corrected_species, COUNT(*) as count
            FROM prediction_corrections
            WHERE cv_session_id IN (
                SELECT cv_session_id FROM integration_sessions WHERE user_id = ?
            )
            GROUP BY corrected_species
        """, (user_id,))
        
        correction_stats = dict(cursor.fetchall())
        
        # Get training example stats  
        cursor.execute("""
            SELECT species, COUNT(*) as count
            FROM training_examples
            WHERE user_id = ?
            GROUP BY species
        """, (user_id,))
        
        training_stats = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'user_id': user_id,
            'corrections_by_species': correction_stats,
            'training_examples_by_species': training_stats,
            'total_corrections': sum(correction_stats.values()),
            'total_training_examples': sum(training_stats.values())
        }
    
    async def force_sync(self) -> Dict[str, Any]:
        """Force immediate synchronization"""
        try:
            await self._sync_fishing_sessions()
            await self._process_new_catches()
            await self._update_training_data()
            
            return {'status': 'success', 'timestamp': datetime.now()}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'timestamp': datetime.now()}

# Integration setup function for easy deployment
async def setup_fishinglog_integration(
    fishinglog_api_url: str = "http://localhost:3000/api",
    cv_training_api_url: str = "http://localhost:8100/api",
    auto_start: bool = True
) -> FishingLogIntegrationService:
    """Setup FishingLog integration service"""
    
    config = FishingLogIntegrationConfig(
        fishinglog_api_url=fishinglog_api_url,
        cv_training_api_url=cv_training_api_url
    )
    
    service = FishingLogIntegrationService(config)
    
    if auto_start:
        await service.start_integration()
    
    return service

if __name__ == "__main__":
    # Test integration service
    async def test_integration():
        service = await setup_fishinglog_integration()
        
        # Run for 60 seconds
        await asyncio.sleep(60)
        
        # Get stats
        stats = await service.get_integration_stats()
        print("Integration stats:", json.dumps(stats, indent=2, default=str))
        
        # Stop service
        await service.stop_integration()
    
    asyncio.run(test_integration())