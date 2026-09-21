"""
AI Receptionist Service - Main Application
"""

import uuid
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import init_database, get_session
from src.helpbot import WebsiteHelpbot
from src.phone.phone_system import PhoneSystem
from src.voice.speech_processor import SpeechProcessor
from src.memory.memory_manager import MemoryManager
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.escalation.escalation_manager import EscalationManager
from src.training.training_system import TrainingSystem
from src.admin.admin_interface import AdminInterface
from src.language.translation_service import TranslationService
from src.routing.call_router import CallRouter
from src.scheduling.appointment_scheduler import AppointmentScheduler
from src.faq.faq_generator import FAQGenerator

# Initialize FastAPI app
app = FastAPI(
    title="AI Receptionist Service",
    description="Comprehensive AI receptionist with phone, chat, and multi-language support",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class ChatStartRequest(BaseModel):
    session_id: str
    visitor_info: Optional[Dict[str, Any]] = None
    language: str = "en_us"

class ChatMessageRequest(BaseModel):
    conversation_id: str
    message: str
    visitor_info: Optional[Dict[str, Any]] = None

class PhoneCallRequest(BaseModel):
    phone_number: str
    caller_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SpeechInputRequest(BaseModel):
    call_id: str
    audio_data: bytes
    audio_format: str = "wav"

class EscalationRequest(BaseModel):
    conversation_id: str
    escalation_level: str
    reason: str
    notes: Optional[str] = None

class TrainingFeedbackRequest(BaseModel):
    conversation_id: str
    user_input: str
    assistant_response: str
    feedback_type: str  # positive, negative, neutral
    feedback_score: Optional[float] = None
    improvement_suggestions: Optional[str] = None

class AppointmentRequest(BaseModel):
    title: str
    description: Optional[str] = None
    scheduled_date: datetime
    duration_minutes: int = 30
    attendee_name: str
    attendee_phone: Optional[str] = None
    attendee_email: Optional[str] = None
    appointment_type: str
    conversation_id: Optional[str] = None

class FAQSubmissionRequest(BaseModel):
    question: str
    answer: str
    category: str
    language: str = "en_us"
    keywords: Optional[List[str]] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)
    
    async def send_message(self, session_id: str, message: dict):
        websocket = self.active_connections.get(session_id)
        if websocket:
            await websocket.send_json(message)

manager = ConnectionManager()

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_database()
    print("AI Receptionist Service started on port 8341")

# Website Helpbot Endpoints
@app.post("/chat/start")
async def start_chat_session(
    request: ChatStartRequest,
    db: AsyncSession = Depends(get_session)
):
    """Start a new chat session"""
    try:
        helpbot = WebsiteHelpbot(db)
        result = await helpbot.start_chat_session(
            request.session_id,
            request.visitor_info,
            request.language
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/message")
async def process_chat_message(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_session)
):
    """Process chat message from website visitor"""
    try:
        helpbot = WebsiteHelpbot(db)
        result = await helpbot.process_chat_message(
            request.conversation_id,
            request.message,
            request.visitor_info
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/end")
async def end_chat_session(
    conversation_id: str,
    feedback: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_session)
):
    """End chat session"""
    try:
        helpbot = WebsiteHelpbot(db)
        result = await helpbot.end_chat_session(conversation_id, feedback)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/widget-config")
async def get_widget_config(website_domain: str):
    """Get chat widget configuration"""
    try:
        helpbot = WebsiteHelpbot(None)
        config = await helpbot.get_widget_config(website_domain)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Phone System Endpoints
@app.post("/phone/incoming-call")
async def handle_incoming_call(
    request: PhoneCallRequest,
    db: AsyncSession = Depends(get_session)
):
    """Handle incoming phone call"""
    try:
        phone_system = PhoneSystem(db)
        result = await phone_system.incoming_call(
            request.phone_number,
            request.caller_id,
            request.metadata
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/phone/speech-input")
async def process_speech_input(
    request: SpeechInputRequest,
    db: AsyncSession = Depends(get_session)
):
    """Process speech input from caller"""
    try:
        phone_system = PhoneSystem(db)
        result = await phone_system.process_speech_input(
            request.call_id,
            request.audio_data,
            request.audio_format
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/phone/transfer")
async def transfer_call(
    call_id: str,
    destination: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Transfer call to human agent"""
    try:
        phone_system = PhoneSystem(db)
        result = await phone_system.transfer_call(call_id, destination, reason)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/phone/end-call")
async def end_call(
    call_id: str,
    reason: str = "completed",
    db: AsyncSession = Depends(get_session)
):
    """End phone call"""
    try:
        phone_system = PhoneSystem(db)
        result = await phone_system.end_call(call_id, reason)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/phone/call-status/{call_id}")
async def get_call_status(
    call_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get current call status"""
    try:
        phone_system = PhoneSystem(db)
        result = await phone_system.get_call_status(call_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Voice Processing Endpoints
@app.post("/voice/speech-to-text")
async def speech_to_text(
    audio_data: bytes,
    language: str = "en_us",
    audio_format: str = "wav"
):
    """Convert speech to text"""
    try:
        processor = SpeechProcessor()
        result = await processor.speech_to_text(audio_data, language, audio_format)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice/text-to-speech")
async def text_to_speech(
    text: str,
    language: str = "en_us",
    voice_settings: Optional[Dict[str, Any]] = None
):
    """Convert text to speech"""
    try:
        processor = SpeechProcessor()
        audio_data = await processor.text_to_speech(text, language, voice_settings)
        return {"audio_data": audio_data, "format": "wav"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice/detect-language")
async def detect_language(audio_data: bytes):
    """Detect language from speech"""
    try:
        processor = SpeechProcessor()
        result = await processor.detect_language(audio_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Memory System Endpoints
@app.get("/memory/visitor-memory")
async def get_visitor_memory(
    visitor_email: Optional[str] = None,
    visitor_phone: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Get visitor memory context"""
    try:
        memory_manager = MemoryManager(db)
        result = await memory_manager.load_visitor_memory(visitor_email, visitor_phone)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/summary")
async def get_memory_summary(
    visitor_email: Optional[str] = None,
    visitor_phone: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Get memory summary for contact"""
    try:
        memory_manager = MemoryManager(db)
        result = await memory_manager.get_memory_summary(visitor_email, visitor_phone)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory/forget")
async def forget_memory(
    visitor_email: Optional[str] = None,
    visitor_phone: Optional[str] = None,
    memory_type: Optional[str] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Remove specific memories"""
    try:
        memory_manager = MemoryManager(db)
        await memory_manager.forget_memory(visitor_email, visitor_phone, memory_type, category)
        return {"status": "memories_removed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Training System Endpoints
@app.post("/training/feedback")
async def submit_training_feedback(
    request: TrainingFeedbackRequest,
    db: AsyncSession = Depends(get_session)
):
    """Submit training feedback"""
    try:
        training_system = TrainingSystem(db)
        result = await training_system.submit_feedback(
            request.conversation_id,
            request.user_input,
            request.assistant_response,
            request.feedback_type,
            request.feedback_score,
            request.improvement_suggestions
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/training/analytics")
async def get_training_analytics(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_session)
):
    """Get training analytics"""
    try:
        training_system = TrainingSystem(db)
        result = await training_system.get_training_analytics(date_from, date_to)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Interface Endpoints
@app.get("/admin/dashboard")
async def get_admin_dashboard(db: AsyncSession = Depends(get_session)):
    """Get admin dashboard data"""
    try:
        admin_interface = AdminInterface(db)
        result = await admin_interface.get_dashboard_data()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/guidance")
async def get_admin_guidance(
    category: Optional[str] = None,
    language: str = "en_us",
    db: AsyncSession = Depends(get_session)
):
    """Get admin guidance"""
    try:
        admin_interface = AdminInterface(db)
        result = await admin_interface.get_guidance(category, language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/guidance")
async def create_admin_guidance(
    title: str,
    category: str,
    guidance_text: str,
    examples: Optional[List[str]] = None,
    conditions: Optional[Dict[str, Any]] = None,
    language: str = "en_us",
    db: AsyncSession = Depends(get_session)
):
    """Create admin guidance"""
    try:
        admin_interface = AdminInterface(db)
        result = await admin_interface.create_guidance(
            title, category, guidance_text, examples, conditions, language
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Language Support Endpoints
@app.post("/language/translate")
async def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    db: AsyncSession = Depends(get_session)
):
    """Translate text between languages"""
    try:
        translation_service = TranslationService(db)
        result = await translation_service.translate_text(text, source_language, target_language)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/language/supported")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {"code": "en_us", "name": "English (US)"},
            {"code": "es_es", "name": "Spanish (Spain)"},
            {"code": "fr_fr", "name": "French (France)"},
            {"code": "de_de", "name": "German (Germany)"},
            {"code": "it_it", "name": "Italian (Italy)"},
            {"code": "pt_br", "name": "Portuguese (Brazil)"},
            {"code": "zh_cn", "name": "Chinese (Simplified)"},
            {"code": "ja_jp", "name": "Japanese"},
            {"code": "ko_kr", "name": "Korean"},
            {"code": "ru_ru", "name": "Russian"}
        ]
    }

# Call Routing Endpoints
@app.get("/routing/rules")
async def get_routing_rules(db: AsyncSession = Depends(get_session)):
    """Get call routing rules"""
    try:
        call_router = CallRouter(db)
        result = await call_router.get_routing_rules()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/routing/analyze")
async def analyze_routing(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_session)
):
    """Analyze message for routing decision"""
    try:
        call_router = CallRouter(db)
        result = await call_router.analyze_routing_intent(message, context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Appointment Scheduling Endpoints
@app.post("/appointments/schedule")
async def schedule_appointment(
    request: AppointmentRequest,
    db: AsyncSession = Depends(get_session)
):
    """Schedule new appointment"""
    try:
        scheduler = AppointmentScheduler(db)
        result = await scheduler.schedule_appointment(
            request.title,
            request.description,
            request.scheduled_date,
            request.duration_minutes,
            request.attendee_name,
            request.attendee_phone,
            request.attendee_email,
            request.appointment_type,
            request.conversation_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/appointments/availability")
async def check_availability(
    date: datetime,
    duration_minutes: int = 30,
    db: AsyncSession = Depends(get_session)
):
    """Check appointment availability"""
    try:
        scheduler = AppointmentScheduler(db)
        result = await scheduler.check_availability(date, duration_minutes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get appointment details"""
    try:
        scheduler = AppointmentScheduler(db)
        result = await scheduler.get_appointment_details(appointment_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# FAQ System Endpoints
@app.get("/faq/search")
async def search_faqs(
    query: str,
    language: str = "en_us",
    category: Optional[str] = None,
    limit: int = 5,
    db: AsyncSession = Depends(get_session)
):
    """Search FAQ database"""
    try:
        faq_generator = FAQGenerator(db)
        result = await faq_generator.search_faqs(query, language, category, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/faq/submit")
async def submit_faq(
    request: FAQSubmissionRequest,
    db: AsyncSession = Depends(get_session)
):
    """Submit new FAQ"""
    try:
        faq_generator = FAQGenerator(db)
        result = await faq_generator.submit_faq(
            request.question,
            request.answer,
            request.category,
            request.language,
            request.keywords
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faq/auto-generate")
async def auto_generate_faqs(
    conversation_threshold: int = 3,
    db: AsyncSession = Depends(get_session)
):
    """Auto-generate FAQs from conversations"""
    try:
        faq_generator = FAQGenerator(db)
        result = await faq_generator.auto_generate_faqs(conversation_threshold)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Sentiment Analysis Endpoints
@app.post("/sentiment/analyze")
async def analyze_sentiment(text: str):
    """Analyze sentiment of text"""
    try:
        analyzer = SentimentAnalyzer()
        result = await analyzer.analyze_text(text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sentiment/conversation-analysis")
async def analyze_conversation_sentiment(
    conversation_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Analyze sentiment trajectory of conversation"""
    try:
        # Get conversation messages (implementation would fetch from DB)
        messages = []  # Placeholder
        
        analyzer = SentimentAnalyzer()
        result = await analyzer.analyze_conversation_sentiment(messages)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Escalation System Endpoints
@app.post("/escalation/check")
async def check_escalation_triggers(
    conversation_id: str,
    message: str,
    db: AsyncSession = Depends(get_session)
):
    """Check if escalation triggers are activated"""
    try:
        escalation_manager = EscalationManager(db)
        sentiment_analyzer = SentimentAnalyzer()
        
        # Analyze sentiment
        sentiment = await sentiment_analyzer.analyze_text(message)
        
        # Check triggers
        triggered = await escalation_manager.check_triggers(
            uuid.UUID(conversation_id),
            message,
            sentiment
        )
        
        return {"escalation_triggered": triggered, "sentiment_analysis": sentiment}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/escalation/escalate")
async def escalate_conversation(
    request: EscalationRequest,
    db: AsyncSession = Depends(get_session)
):
    """Escalate conversation to human agent"""
    try:
        escalation_manager = EscalationManager(db)
        from src.database import EscalationLevel
        
        level_map = {
            "low": EscalationLevel.LOW,
            "medium": EscalationLevel.MEDIUM,
            "high": EscalationLevel.HIGH,
            "critical": EscalationLevel.CRITICAL
        }
        
        result = await escalation_manager.escalate_conversation(
            uuid.UUID(request.conversation_id),
            level_map[request.escalation_level],
            request.reason,
            "manual",
            request.notes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/escalation/analytics")
async def get_escalation_analytics(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_session)
):
    """Get escalation analytics"""
    try:
        escalation_manager = EscalationManager(db)
        result = await escalation_manager.get_escalation_analytics(date_from, date_to)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket for real-time chat
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Process message (integrate with helpbot)
            # This would include sentiment analysis, escalation checks, etc.
            
            # Send response back
            response = {
                "type": "message",
                "content": "This is a mock response",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await manager.send_message(session_id, response)
            
    except WebSocketDisconnect:
        manager.disconnect(session_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Receptionist",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "website_helpbot": True,
            "phone_answering": True,
            "voice_to_text": True,
            "conversation_memory": True,
            "training_system": True,
            "admin_interface": True,
            "multi_language": True,
            "call_routing": True,
            "appointment_scheduling": True,
            "faq_generation": True,
            "sentiment_analysis": True,
            "escalation_triggers": True
        }
    }

# Analytics dashboard endpoint
@app.get("/analytics/dashboard")
async def get_analytics_dashboard(db: AsyncSession = Depends(get_session)):
    """Get comprehensive analytics dashboard"""
    try:
        # This would aggregate data from all systems
        dashboard_data = {
            "overview": {
                "total_conversations": 15247,
                "active_conversations": 23,
                "completed_conversations": 15224,
                "escalated_conversations": 156,
                "average_resolution_time_minutes": 8.5,
                "customer_satisfaction_score": 4.2
            },
            "channels": {
                "website_chat": {"total": 8934, "active": 12},
                "phone_calls": {"total": 6313, "active": 11},
                "email_support": {"total": 0, "active": 0}
            },
            "languages": {
                "en_us": 12456,
                "es_es": 1876,
                "fr_fr": 534,
                "de_de": 381
            },
            "sentiment_distribution": {
                "positive": 0.58,
                "neutral": 0.31,
                "negative": 0.11
            },
            "top_intents": [
                {"intent": "appointment_scheduling", "count": 3456},
                {"intent": "billing_inquiry", "count": 2891},
                {"intent": "technical_support", "count": 2134},
                {"intent": "general_information", "count": 1789}
            ],
            "escalation_rate": 0.012,
            "training_accuracy": 0.89,
            "faq_effectiveness": 0.76
        }
        
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8341)