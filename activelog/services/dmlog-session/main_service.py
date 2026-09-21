"""
D&D Session Management Service

Main orchestrator that coordinates all session management features including
audio recording, transcription, notes, highlights, scheduling, virtual tabletop,
content sharing, ambiance, analytics, and feedback collection.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models.session import SessionSchema, SessionParticipant
from .models.base import SessionHighlight, TranscriptionSegment
from .services.audio_service import AudioRecordingService
from .services.transcription_service import TranscriptionService
from .services.notes_service import SessionNotesService
from .services.highlight_service import HighlightDetectionService
from .services.recap_service import RecapGeneratorService
from .services.scheduling_service import SchedulingService
from .services.tabletop_service import VirtualTabletopService
from .services.content_service import ContentSharingService
from .services.audio_ambiance_service import AudioAmbianceService
from .services.analytics_service import SessionAnalyticsService
from .services.feedback_service import FeedbackService
from .config import SERVICE_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionRequest(BaseModel):
    title: str
    description: str = ""
    participants: List[str]
    scheduled_start: Optional[datetime] = None
    estimated_duration_minutes: int = 240


class SessionManager:
    """Main session management coordinator"""
    
    def __init__(self):
        # Initialize all services
        self.audio_service = AudioRecordingService()
        self.transcription_service = TranscriptionService()
        self.notes_service = SessionNotesService()
        self.highlight_service = HighlightDetectionService()
        self.recap_service = RecapGeneratorService()
        self.scheduling_service = SchedulingService()
        self.tabletop_service = VirtualTabletopService()
        self.content_service = ContentSharingService()
        self.ambiance_service = AudioAmbianceService()
        self.analytics_service = SessionAnalyticsService()
        self.feedback_service = FeedbackService()
        
        # Session state tracking
        self.active_sessions: Dict[str, SessionSchema] = {}
        self.session_transcripts: Dict[str, List[TranscriptionSegment]] = {}
        self.session_highlights: Dict[str, List[SessionHighlight]] = {}
        
        logger.info("Session Manager initialized with all services")
    
    async def create_session(self, session_request: SessionRequest) -> SessionSchema:
        """Create a new D&D session"""
        try:
            # Create participants
            participants = [
                SessionParticipant(user_id=user_id, joined_at=datetime.utcnow())
                for user_id in session_request.participants
            ]
            
            # Create session
            session = SessionSchema(
                title=session_request.title,
                description=session_request.description,
                participants=participants,
                scheduled_start=session_request.scheduled_start or datetime.utcnow(),
                estimated_duration_minutes=session_request.estimated_duration_minutes,
                created_at=datetime.utcnow(),
                status="created"
            )
            
            # Initialize session in all services
            await self._initialize_session_services(session)
            
            # Store session
            self.active_sessions[session.id] = session
            self.session_transcripts[session.id] = []
            self.session_highlights[session.id] = []
            
            logger.info(f"Created session {session.id}: {session.title}")
            return session
        
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def start_session(self, session_id: str) -> bool:
        """Start a D&D session with full recording and analysis"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Start audio recording
            await self.audio_service.start_recording(session)
            
            # Initialize real-time transcription
            await self.transcription_service.start_real_time_transcription(session)
            
            # Initialize tabletop session
            await self.tabletop_service.create_tabletop_session(session)
            
            # Initialize audio ambiance
            await self.ambiance_service.initialize_session_audio(session)
            
            # Update session status
            session.status = "active"
            session.started_at = datetime.utcnow()
            
            logger.info(f"Started session {session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error starting session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a session and generate comprehensive analysis"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Stop audio recording
            audio_files = await self.audio_service.stop_recording(session_id)
            
            # Get final transcription
            transcription_segments = await self.transcription_service.get_session_transcription(session_id)
            self.session_transcripts[session_id] = transcription_segments
            
            # Generate highlights if not already generated
            if session_id not in self.session_highlights or not self.session_highlights[session_id]:
                highlights = await self.highlight_service.detect_highlights(session, transcription_segments)
                self.session_highlights[session_id] = highlights
            
            # Generate session notes
            await self.notes_service.generate_automatic_notes(session, transcription_segments)
            
            # Generate session recap
            recap = await self.recap_service.generate_session_recap(
                session, transcription_segments, self.session_highlights[session_id],
                await self.notes_service.get_session_notes(session_id)
            )
            
            # Generate analytics
            analytics = await self.analytics_service.analyze_session(
                session, transcription_segments, self.session_highlights[session_id]
            )
            
            # Create post-session survey
            survey_id = await self.feedback_service.create_survey(
                session_id, "standard", "system"
            )
            
            # Update session status
            session.status = "completed"
            session.ended_at = datetime.utcnow()
            
            # Clean up audio ambiance
            await self.ambiance_service.cleanup_session_audio(session_id)
            
            logger.info(f"Ended session {session_id}")
            
            return {
                "session_id": session_id,
                "audio_files": audio_files,
                "transcription_segments": len(transcription_segments),
                "highlights_generated": len(self.session_highlights[session_id]),
                "recap_id": recap.session_id,
                "analytics_rating": analytics.overall_rating,
                "survey_id": survey_id,
                "status": "completed"
            }
        
        except Exception as e:
            logger.error(f"Error ending session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _initialize_session_services(self, session: SessionSchema):
        """Initialize all services for a new session"""
        try:
            # Initialize notes service
            await self.notes_service.create_session_notebook(session)
            
            # Initialize highlight service
            await self.highlight_service.initialize_session(session)
            
            # Initialize scheduling service (for future sessions)
            await self.scheduling_service.initialize_session_tracking(session)
            
            logger.info(f"Initialized all services for session {session.id}")
        
        except Exception as e:
            logger.error(f"Error initializing services for session {session.id}: {e}")
            raise
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive session status"""
        session = self.active_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        status = {
            "session": session.dict(),
            "transcription_segments": len(self.session_transcripts.get(session_id, [])),
            "highlights": len(self.session_highlights.get(session_id, [])),
            "notes_count": len(await self.notes_service.get_session_notes(session_id)),
            "tabletop_state": await self.tabletop_service.get_session_state(session_id),
            "audio_state": await self.ambiance_service.get_session_audio_state(session_id),
            "analytics_available": session_id in self.analytics_service.session_analytics,
            "feedback_available": session_id in self.feedback_service.session_feedback
        }
        
        return status
    
    async def process_real_time_audio(self, session_id: str, audio_data: bytes, 
                                    participant_id: str):
        """Process real-time audio stream"""
        try:
            # Process audio for recording
            await self.audio_service.process_audio_stream(session_id, audio_data, participant_id)
            
            # Process for real-time transcription
            transcription = await self.transcription_service.process_real_time_audio(
                session_id, audio_data, participant_id
            )
            
            if transcription:
                # Add to session transcripts
                if session_id not in self.session_transcripts:
                    self.session_transcripts[session_id] = []
                self.session_transcripts[session_id].append(transcription)
                
                # Check for highlights
                session = self.active_sessions.get(session_id)
                if session:
                    potential_highlights = await self.highlight_service.analyze_segment_for_highlights(
                        transcription, session
                    )
                    
                    if potential_highlights:
                        if session_id not in self.session_highlights:
                            self.session_highlights[session_id] = []
                        self.session_highlights[session_id].extend(potential_highlights)
                
                # Update real-time analytics
                await self.analytics_service.engagement_tracker.update_speaker_activity(
                    participant_id, transcription
                )
        
        except Exception as e:
            logger.error(f"Error processing real-time audio for session {session_id}: {e}")


# FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting D&D Session Management Service")
    yield
    logger.info("Shutting down D&D Session Management Service")


app = FastAPI(
    title="D&D Session Management Service",
    description="Comprehensive session management for D&D games",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=SERVICE_CONFIG.get("allowed_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize session manager
session_manager = SessionManager()

# WebSocket connections for real-time features
active_websockets: Dict[str, List[WebSocket]] = {}


@app.post("/sessions", response_model=Dict[str, Any])
async def create_session(request: SessionRequest):
    """Create a new D&D session"""
    session = await session_manager.create_session(request)
    return {"session_id": session.id, "session": session.dict()}


@app.post("/sessions/{session_id}/start")
async def start_session(session_id: str):
    """Start a D&D session"""
    success = await session_manager.start_session(session_id)
    return {"success": success, "message": "Session started successfully"}


@app.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    """End a D&D session and generate analysis"""
    result = await session_manager.end_session(session_id)
    return result


@app.get("/sessions/{session_id}/status")
async def get_session_status(session_id: str):
    """Get comprehensive session status"""
    return await session_manager.get_session_status(session_id)


@app.get("/sessions/{session_id}/recap")
async def get_session_recap(session_id: str):
    """Get session recap"""
    recap = await session_manager.recap_service.get_recap_summary(session_id)
    if not recap:
        raise HTTPException(status_code=404, detail="Recap not found")
    return recap


@app.get("/sessions/{session_id}/analytics")
async def get_session_analytics(session_id: str):
    """Get session analytics"""
    analytics = await session_manager.analytics_service.get_session_analytics(session_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Analytics not found")
    return analytics


@app.get("/sessions/{session_id}/feedback")
async def get_session_feedback(session_id: str):
    """Get session feedback"""
    feedback = await session_manager.feedback_service.get_session_feedback(session_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


@app.websocket("/sessions/{session_id}/realtime")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time session features"""
    await websocket.accept()
    
    # Add to active connections
    if session_id not in active_websockets:
        active_websockets[session_id] = []
    active_websockets[session_id].append(websocket)
    
    try:
        while True:
            # Receive data from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "audio_data":
                # Process real-time audio
                await session_manager.process_real_time_audio(
                    session_id, 
                    data.get("audio_data", b""),
                    data.get("participant_id")
                )
            
            elif message_type == "tabletop_action":
                # Handle tabletop actions
                await session_manager.tabletop_service.handle_websocket_message(
                    websocket, json.dumps(data), session_id, data.get("user_id")
                )
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        # Remove from active connections
        if session_id in active_websockets:
            active_websockets[session_id].remove(websocket)
            if not active_websockets[session_id]:
                del active_websockets[session_id]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "active_sessions": len(session_manager.active_sessions),
        "services": {
            "audio": "operational",
            "transcription": "operational",
            "notes": "operational",
            "highlights": "operational",
            "recap": "operational",
            "scheduling": "operational",
            "tabletop": "operational",
            "content": "operational",
            "ambiance": "operational",
            "analytics": "operational",
            "feedback": "operational"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )