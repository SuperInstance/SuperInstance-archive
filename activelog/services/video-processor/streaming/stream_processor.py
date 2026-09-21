"""
Streaming video processing support for real-time analysis
"""

import asyncio
import cv2
import numpy as np
import os
import tempfile
import time
from datetime import datetime
from typing import List, Dict, Optional, Any, AsyncGenerator, Callable
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import websockets
import aiohttp
from dataclasses import dataclass, asdict
import uuid
import base64

from ..core.config import settings
from ..core.database import DatabaseManager
from ..processors.keyframe_extractor import KeyframeExtractor
from ..processors.scene_detector import SceneDetector
from ..processors.ocr_processor import OCRProcessor

streaming_logger = logging.getLogger('streaming')

@dataclass
class StreamFrame:
    """Represents a frame from streaming video"""
    timestamp: float
    frame_number: int
    frame_data: np.ndarray
    metadata: Dict[str, Any]

@dataclass
class StreamAnalysisResult:
    """Results from streaming video analysis"""
    session_id: str
    timestamp: float
    frame_number: int
    analysis_type: str
    results: Dict[str, Any]
    confidence: float

class StreamingVideoProcessor:
    """Real-time video processing for streaming content"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_JOBS)
        
        # Initialize processors
        self.keyframe_extractor = KeyframeExtractor(db_manager)
        self.scene_detector = SceneDetector(db_manager)
        self.ocr_processor = OCRProcessor(db_manager)
        
        # Streaming configuration
        self.max_concurrent_streams = 5
        self.frame_buffer_size = 100
        self.analysis_interval = 2.0  # seconds
        
        # Active streaming sessions
        self.active_sessions = {}
        self.session_callbacks = {}
        
        # WebSocket connections
        self.websocket_connections = {}
    
    async def start_stream_session(self, session_id: str, stream_source: str,
                                 analysis_types: List[str] = None,
                                 callback_url: str = None,
                                 websocket_url: str = None) -> Dict[str, Any]:
        """
        Start a new streaming video processing session
        
        Args:
            session_id: Unique session identifier
            stream_source: Video stream source (URL, device, etc.)
            analysis_types: Types of analysis to perform
            callback_url: HTTP callback URL for results
            websocket_url: WebSocket URL for real-time updates
            
        Returns:
            Session information
        """
        if analysis_types is None:
            analysis_types = ['keyframes', 'ocr', 'scene_detection']
        
        try:
            streaming_logger.info(f"Starting streaming session {session_id}")
            
            if len(self.active_sessions) >= self.max_concurrent_streams:
                raise Exception("Maximum concurrent streams reached")
            
            # Create session data
            session_data = {
                'session_id': session_id,
                'stream_source': stream_source,
                'analysis_types': analysis_types,
                'callback_url': callback_url,
                'websocket_url': websocket_url,
                'start_time': datetime.utcnow(),
                'status': 'starting',
                'frame_count': 0,
                'last_analysis': None,
                'statistics': {
                    'frames_processed': 0,
                    'keyframes_detected': 0,
                    'scenes_detected': 0,
                    'text_instances': 0,
                    'processing_errors': 0
                }
            }
            
            self.active_sessions[session_id] = session_data
            
            # Save session to database
            await self._save_stream_session(session_data)
            
            # Start processing task
            asyncio.create_task(self._process_stream(session_id))
            
            return {
                'session_id': session_id,
                'status': 'started',
                'analysis_types': analysis_types,
                'start_time': session_data['start_time'].isoformat()
            }
            
        except Exception as e:
            streaming_logger.error(f"Failed to start streaming session {session_id}: {str(e)}")
            raise
    
    async def stop_stream_session(self, session_id: str) -> Dict[str, Any]:
        """Stop an active streaming session"""
        
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise Exception(f"Session {session_id} not found")
            
            streaming_logger.info(f"Stopping streaming session {session_id}")
            
            # Update session status
            session['status'] = 'stopping'
            session['end_time'] = datetime.utcnow()
            
            # Update database
            await self._update_stream_session(session_id, session)
            
            # Close WebSocket connection if exists
            if session_id in self.websocket_connections:
                await self.websocket_connections[session_id].close()
                del self.websocket_connections[session_id]
            
            # Remove from active sessions
            final_stats = session['statistics'].copy()
            del self.active_sessions[session_id]
            
            return {
                'session_id': session_id,
                'status': 'stopped',
                'statistics': final_stats,
                'duration': (session['end_time'] - session['start_time']).total_seconds()
            }
            
        except Exception as e:
            streaming_logger.error(f"Failed to stop streaming session {session_id}: {str(e)}")
            raise
    
    async def _process_stream(self, session_id: str):
        """Main processing loop for a streaming session"""
        
        session = self.active_sessions[session_id]
        stream_source = session['stream_source']
        
        try:
            # Open video stream
            cap = cv2.VideoCapture(stream_source)
            if not cap.isOpened():
                raise Exception(f"Cannot open stream source: {stream_source}")
            
            session['status'] = 'processing'
            fps = cap.get(cv2.CAP_PROP_FPS) or 25  # Default to 25 FPS if unknown
            frame_interval = int(fps * self.analysis_interval)
            
            streaming_logger.info(f"Stream {session_id} processing started, FPS: {fps}")
            
            frame_buffer = []
            last_analysis_time = 0
            
            while session.get('status') == 'processing':
                ret, frame = cap.read()
                
                if not ret:
                    # End of stream or connection lost
                    streaming_logger.info(f"Stream {session_id} ended")
                    break
                
                current_time = time.time()
                frame_number = session['frame_count']
                
                # Add frame to buffer
                stream_frame = StreamFrame(
                    timestamp=current_time,
                    frame_number=frame_number,
                    frame_data=frame,
                    metadata={
                        'width': frame.shape[1],
                        'height': frame.shape[0],
                        'channels': frame.shape[2] if len(frame.shape) > 2 else 1
                    }
                )
                
                frame_buffer.append(stream_frame)
                session['frame_count'] += 1
                session['statistics']['frames_processed'] += 1
                
                # Perform analysis at intervals
                if (current_time - last_analysis_time) >= self.analysis_interval:
                    try:
                        await self._analyze_stream_frames(session_id, frame_buffer)
                        last_analysis_time = current_time
                        frame_buffer = []  # Clear buffer after analysis
                        
                    except Exception as e:
                        streaming_logger.warning(f"Stream analysis error: {str(e)}")
                        session['statistics']['processing_errors'] += 1
                
                # Limit buffer size
                if len(frame_buffer) > self.frame_buffer_size:
                    frame_buffer = frame_buffer[-self.frame_buffer_size//2:]
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.01)
            
            cap.release()
            session['status'] = 'completed'
            
        except Exception as e:
            streaming_logger.error(f"Stream processing error for {session_id}: {str(e)}")
            session['status'] = 'failed'
            session['error'] = str(e)
        
        finally:
            # Update final session status
            session['end_time'] = datetime.utcnow()
            await self._update_stream_session(session_id, session)
    
    async def _analyze_stream_frames(self, session_id: str, frames: List[StreamFrame]):
        """Analyze a batch of stream frames"""
        
        if not frames:
            return
        
        session = self.active_sessions[session_id]
        analysis_types = session['analysis_types']
        
        # Use the latest frame for most analysis
        latest_frame = frames[-1]
        
        results = []
        
        # Keyframe detection
        if 'keyframes' in analysis_types:
            try:
                keyframe_result = await self._detect_stream_keyframes(session_id, frames)
                if keyframe_result:
                    results.append(keyframe_result)
                    session['statistics']['keyframes_detected'] += 1
            except Exception as e:
                streaming_logger.warning(f"Keyframe detection failed: {str(e)}")
        
        # Scene detection
        if 'scene_detection' in analysis_types:
            try:
                scene_result = await self._detect_stream_scenes(session_id, frames)
                if scene_result:
                    results.append(scene_result)
                    session['statistics']['scenes_detected'] += 1
            except Exception as e:
                streaming_logger.warning(f"Scene detection failed: {str(e)}")
        
        # OCR processing
        if 'ocr' in analysis_types:
            try:
                ocr_result = await self._process_stream_ocr(session_id, latest_frame)
                if ocr_result:
                    results.append(ocr_result)
                    session['statistics']['text_instances'] += len(ocr_result.results.get('texts', []))
            except Exception as e:
                streaming_logger.warning(f"OCR processing failed: {str(e)}")
        
        # Send results
        if results:
            session['last_analysis'] = datetime.utcnow()
            await self._send_stream_results(session_id, results)
    
    async def _detect_stream_keyframes(self, session_id: str, 
                                     frames: List[StreamFrame]) -> Optional[StreamAnalysisResult]:
        """Detect keyframes in streaming video"""
        
        if len(frames) < 2:
            return None
        
        # Use simple difference method for real-time processing
        latest_frame = frames[-1]
        prev_frame = frames[-2]
        
        # Calculate frame difference
        gray1 = cv2.cvtColor(latest_frame.frame_data, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(prev_frame.frame_data, cv2.COLOR_BGR2GRAY)
        
        diff = cv2.absdiff(gray1, gray2)
        diff_score = np.mean(diff) / 255.0
        
        # Consider as keyframe if significant difference
        if diff_score > 0.1:  # Threshold for keyframe detection
            # Extract basic features
            features = {
                'difference_score': float(diff_score),
                'brightness': float(np.mean(gray1)),
                'contrast': float(np.std(gray1)),
                'edges': int(np.sum(cv2.Canny(gray1, 50, 150) > 0))
            }
            
            return StreamAnalysisResult(
                session_id=session_id,
                timestamp=latest_frame.timestamp,
                frame_number=latest_frame.frame_number,
                analysis_type='keyframe',
                results={
                    'is_keyframe': True,
                    'features': features,
                    'method': 'difference'
                },
                confidence=min(diff_score * 2, 1.0)
            )
        
        return None
    
    async def _detect_stream_scenes(self, session_id: str,
                                  frames: List[StreamFrame]) -> Optional[StreamAnalysisResult]:
        """Detect scene changes in streaming video"""
        
        if len(frames) < 3:
            return None
        
        # Simple scene change detection using histogram comparison
        latest_frame = frames[-1]
        
        # Calculate histogram
        hist_current = cv2.calcHist([latest_frame.frame_data], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        # Compare with previous frames
        scene_change_score = 0.0
        
        for i in range(min(5, len(frames) - 1)):  # Check last 5 frames
            prev_frame = frames[-(i+2)]
            hist_prev = cv2.calcHist([prev_frame.frame_data], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
            
            correlation = cv2.compareHist(hist_current, hist_prev, cv2.HISTCMP_CORREL)
            scene_change_score = max(scene_change_score, 1.0 - correlation)
        
        # Detect scene change if significant
        if scene_change_score > 0.3:  # Threshold for scene change
            return StreamAnalysisResult(
                session_id=session_id,
                timestamp=latest_frame.timestamp,
                frame_number=latest_frame.frame_number,
                analysis_type='scene_change',
                results={
                    'scene_change_detected': True,
                    'change_score': float(scene_change_score),
                    'method': 'histogram_correlation'
                },
                confidence=min(scene_change_score * 1.5, 1.0)
            )
        
        return None
    
    async def _process_stream_ocr(self, session_id: str,
                                frame: StreamFrame) -> Optional[StreamAnalysisResult]:
        """Process OCR on streaming frame"""
        
        try:
            # Use simplified OCR processing for real-time
            gray = cv2.cvtColor(frame.frame_data, cv2.COLOR_BGR2GRAY)
            
            # Quick preprocessing
            enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
            
            # Run OCR in executor to avoid blocking
            loop = asyncio.get_event_loop()
            ocr_results = await loop.run_in_executor(
                self.executor,
                self._run_fast_ocr,
                enhanced
            )
            
            if ocr_results:
                return StreamAnalysisResult(
                    session_id=session_id,
                    timestamp=frame.timestamp,
                    frame_number=frame.frame_number,
                    analysis_type='ocr',
                    results={
                        'texts': ocr_results,
                        'text_count': len(ocr_results)
                    },
                    confidence=0.7  # Lower confidence for real-time processing
                )
        
        except Exception as e:
            streaming_logger.warning(f"Stream OCR error: {str(e)}")
        
        return None
    
    def _run_fast_ocr(self, image: np.ndarray) -> List[Dict]:
        """Fast OCR processing for streaming"""
        
        try:
            import pytesseract
            from PIL import Image
            
            # Quick OCR configuration for speed
            config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz .,!?-'
            
            pil_image = Image.fromarray(image)
            
            # Get OCR data
            ocr_data = pytesseract.image_to_data(
                pil_image,
                config=config,
                output_type=pytesseract.Output.DICT
            )
            
            texts = []
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                if confidence > 40 and len(text) > 2:  # Lower threshold for speed
                    texts.append({
                        'text': text,
                        'confidence': confidence,
                        'bbox': {
                            'x': int(ocr_data['left'][i]),
                            'y': int(ocr_data['top'][i]),
                            'width': int(ocr_data['width'][i]),
                            'height': int(ocr_data['height'][i])
                        }
                    })
            
            return texts
            
        except Exception:
            return []
    
    async def _send_stream_results(self, session_id: str, results: List[StreamAnalysisResult]):
        """Send streaming analysis results via configured methods"""
        
        session = self.active_sessions.get(session_id)
        if not session:
            return
        
        # Prepare results data
        results_data = {
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
            'results': [asdict(result) for result in results]
        }
        
        # Send via WebSocket if connected
        if session_id in self.websocket_connections:
            try:
                await self.websocket_connections[session_id].send(json.dumps(results_data))
            except Exception as e:
                streaming_logger.warning(f"WebSocket send failed: {str(e)}")
        
        # Send via HTTP callback if configured
        callback_url = session.get('callback_url')
        if callback_url:
            try:
                async with aiohttp.ClientSession() as http_session:
                    await http_session.post(
                        callback_url,
                        json=results_data,
                        timeout=aiohttp.ClientTimeout(total=10)
                    )
            except Exception as e:
                streaming_logger.warning(f"Callback send failed: {str(e)}")
        
        # Store in database for persistence
        try:
            await self._store_stream_results(session_id, results_data)
        except Exception as e:
            streaming_logger.warning(f"Database storage failed: {str(e)}")
    
    async def _save_stream_session(self, session_data: Dict):
        """Save streaming session to database"""
        
        try:
            await self.db_manager.execute_command("""
                INSERT INTO streaming_sessions (
                    session_id, session_type, status, start_time,
                    client_info
                ) VALUES ($1, $2, $3, $4, $5)
            """, 
            session_data['session_id'],
            'live_analysis',
            session_data['status'],
            session_data['start_time'],
            json.dumps({
                'stream_source': session_data['stream_source'],
                'analysis_types': session_data['analysis_types'],
                'callback_url': session_data.get('callback_url'),
                'websocket_url': session_data.get('websocket_url')
            }))
            
        except Exception as e:
            streaming_logger.error(f"Failed to save session to database: {str(e)}")
    
    async def _update_stream_session(self, session_id: str, session_data: Dict):
        """Update streaming session in database"""
        
        try:
            await self.db_manager.execute_command("""
                UPDATE streaming_sessions
                SET status = $1, end_time = $2, last_activity = $3,
                    client_info = $4
                WHERE session_id = $5
            """,
            session_data['status'],
            session_data.get('end_time'),
            datetime.utcnow(),
            json.dumps({
                'statistics': session_data['statistics'],
                'frame_count': session_data['frame_count'],
                'error': session_data.get('error')
            }),
            session_id)
            
        except Exception as e:
            streaming_logger.error(f"Failed to update session in database: {str(e)}")
    
    async def _store_stream_results(self, session_id: str, results_data: Dict):
        """Store streaming results in database for later retrieval"""
        
        # This would store results in a dedicated streaming results table
        # For now, we'll log the results
        streaming_logger.info(f"Stream results for {session_id}: {len(results_data['results'])} analyses")
    
    async def get_stream_status(self, session_id: str) -> Optional[Dict]:
        """Get current status of a streaming session"""
        
        session = self.active_sessions.get(session_id)
        if not session:
            return None
        
        return {
            'session_id': session_id,
            'status': session['status'],
            'start_time': session['start_time'].isoformat(),
            'frame_count': session['frame_count'],
            'statistics': session['statistics'],
            'last_analysis': session['last_analysis'].isoformat() if session['last_analysis'] else None
        }
    
    async def list_active_sessions(self) -> List[Dict]:
        """List all active streaming sessions"""
        
        sessions = []
        for session_id, session_data in self.active_sessions.items():
            sessions.append({
                'session_id': session_id,
                'status': session_data['status'],
                'start_time': session_data['start_time'].isoformat(),
                'frame_count': session_data['frame_count'],
                'analysis_types': session_data['analysis_types']
            })
        
        return sessions
    
    async def connect_websocket(self, session_id: str, websocket):
        """Connect WebSocket for real-time streaming results"""
        
        if session_id not in self.active_sessions:
            raise Exception(f"Session {session_id} not found")
        
        self.websocket_connections[session_id] = websocket
        streaming_logger.info(f"WebSocket connected for session {session_id}")
        
        try:
            # Send initial status
            status = await self.get_stream_status(session_id)
            await websocket.send(json.dumps({
                'type': 'status',
                'data': status
            }))
            
            # Keep connection alive until session ends
            while session_id in self.active_sessions:
                await asyncio.sleep(1)
                
                # Send periodic heartbeat
                await websocket.send(json.dumps({
                    'type': 'heartbeat',
                    'timestamp': datetime.utcnow().isoformat()
                }))
        
        except websockets.exceptions.ConnectionClosed:
            streaming_logger.info(f"WebSocket disconnected for session {session_id}")
        
        finally:
            if session_id in self.websocket_connections:
                del self.websocket_connections[session_id]