#!/usr/bin/env python3
"""
Adaptive UX Main Service

This service provides an adaptive user experience system that learns from user behavior
and automatically adjusts the interface for optimal usability and productivity.

Features:
- Interface Intelligence: Device detection, expertise analysis, usage patterns
- Progressive Disclosure: Gradual revelation of features based on user readiness
- Chatbot Assistant: Natural language configuration and setup help
- Zero-Knowledge Success: Intuitive first-run experiences requiring no prior knowledge
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import our adaptive UX modules
from interface_intelligence import InterfaceIntelligence, UserProfile, InteractionEvent, InteractionContext
from progressive_disclosure import ProgressiveDisclosureEngine, FeatureComplexity
from chatbot_assistant import ChatbotConfigurationAssistant, ConversationState, ResponseType
from zero_knowledge_success import ZeroKnowledgeSuccessSystem, OnboardingStage, SafetyLevel
from accessibility_ai import AccessibilityAI, AccessibilityNeed, AdaptationLevel
from predictive_interface_generation import PredictiveInterfaceGenerator, UserContext, InterfaceType, LayoutPattern, InteractionMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Adaptive UX Service",
    description="Intelligent user experience adaptation system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API requests/responses
class InteractionEventRequest(BaseModel):
    user_id: str
    event_type: str
    target_element: str
    duration: Optional[float] = None
    success: bool = True
    metadata: Optional[Dict[str, Any]] = None

class UserProfileRequest(BaseModel):
    user_id: str
    device_info: Dict[str, Any]
    system_settings: Dict[str, Any]
    user_preferences: Optional[Dict[str, Any]] = None

class ChatMessageRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None

class FeatureUsageRequest(BaseModel):
    user_id: str
    feature_id: str
    duration: Optional[float] = None
    success: bool = True
    context: Optional[str] = None

class SafeExplorationRequest(BaseModel):
    user_id: str
    exploration_type: Optional[str] = "general"
    safety_level: Optional[str] = None

# Global service instances
interface_intelligence = None
disclosure_engine = None
chatbot_assistant = None
zero_knowledge_system = None
accessibility_ai = None
predictive_generator = None

# WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global interface_intelligence, disclosure_engine, chatbot_assistant, zero_knowledge_system, accessibility_ai, predictive_generator
    
    logger.info("Initializing Adaptive UX services...")
    
    try:
        # Initialize core intelligence system
        interface_intelligence = InterfaceIntelligence()
        logger.info("Interface Intelligence initialized")
        
        # Initialize progressive disclosure
        disclosure_engine = ProgressiveDisclosureEngine(interface_intelligence)
        logger.info("Progressive Disclosure Engine initialized")
        
        # Initialize chatbot assistant
        chatbot_assistant = ChatbotConfigurationAssistant(interface_intelligence, disclosure_engine)
        logger.info("Chatbot Configuration Assistant initialized")
        
        # Initialize accessibility AI
        accessibility_ai = AccessibilityAI()
        logger.info("Accessibility AI initialized")
        
        # Initialize predictive interface generator
        predictive_generator = PredictiveInterfaceGenerator()
        logger.info("Predictive Interface Generator initialized")
        
        # Initialize zero-knowledge success system
        zero_knowledge_system = ZeroKnowledgeSuccessSystem(interface_intelligence, disclosure_engine)
        logger.info("Zero-Knowledge Success System initialized")
        
        logger.info("All Adaptive UX services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time UX adaptation"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different types of real-time events
            if message.get("type") == "interaction":
                await handle_realtime_interaction(user_id, message, websocket)
            elif message.get("type") == "help_request":
                await handle_realtime_help_request(user_id, message, websocket)
            elif message.get("type") == "chat":
                await handle_realtime_chat(user_id, message, websocket)
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def handle_realtime_interaction(user_id: str, message: Dict[str, Any], websocket: WebSocket):
    """Handle real-time interaction events"""
    try:
        # Record interaction
        interaction = InteractionEvent(
            user_id=user_id,
            event_type=message.get("event_type"),
            target_element=message.get("target_element"),
            timestamp=datetime.utcnow(),
            duration=message.get("duration"),
            success=message.get("success", True),
            metadata=message.get("metadata", {})
        )
        
        await interface_intelligence.record_interaction(
            user_id, interaction.event_type, interaction.target_element,
            interaction.duration, interaction.success, interaction.metadata
        )
        
        # Record for disclosure engine
        context = InteractionContext(message.get("context", "PRODUCTIVE"))
        await disclosure_engine.record_feature_usage(
            user_id, interaction.target_element, interaction.duration,
            interaction.success, context
        )
        
        # Record for zero-knowledge system
        await zero_knowledge_system.record_user_interaction(user_id, interaction)
        
        # Get updated interface configuration
        config = await get_adaptive_interface_config(user_id, context)
        
        # Send real-time updates
        await websocket.send_text(json.dumps({
            "type": "interface_update",
            "config": config
        }))
        
    except Exception as e:
        logger.error(f"Error handling real-time interaction: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process interaction"
        }))

async def handle_realtime_help_request(user_id: str, message: Dict[str, Any], websocket: WebSocket):
    """Handle real-time help requests"""
    try:
        context = message.get("context", "")
        help_content = await zero_knowledge_system.get_contextual_help(user_id, context)
        
        await websocket.send_text(json.dumps({
            "type": "help_response",
            "content": help_content
        }))
        
    except Exception as e:
        logger.error(f"Error handling help request: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to get help content"
        }))

async def handle_realtime_chat(user_id: str, message: Dict[str, Any], websocket: WebSocket):
    """Handle real-time chat with configuration assistant"""
    try:
        user_message = message.get("message", "")
        session_id = message.get("session_id")
        
        if session_id:
            response = await chatbot_assistant.continue_conversation(session_id, user_message)
        else:
            response = await chatbot_assistant.start_conversation(user_id, user_message)
        
        await websocket.send_text(json.dumps({
            "type": "chat_response",
            "response": {
                "type": response.response_type.value,
                "message": response.message,
                "options": response.options,
                "next_question": response.next_question,
                "configuration_data": response.configuration_data,
                "requires_confirmation": response.requires_confirmation
            }
        }))
        
    except Exception as e:
        logger.error(f"Error handling chat: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Failed to process chat message"
        }))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "interface_intelligence": interface_intelligence is not None,
            "disclosure_engine": disclosure_engine is not None,
            "chatbot_assistant": chatbot_assistant is not None,
            "zero_knowledge_system": zero_knowledge_system is not None
        }
    }

# Interface Intelligence endpoints
@app.post("/api/users/profile")
async def create_user_profile(request: UserProfileRequest):
    """Create or update user profile"""
    try:
        profile = await interface_intelligence.create_user_profile(
            request.user_id,
            request.device_info,
            request.system_settings,
            request.user_preferences
        )
        
        return {
            "success": True,
            "profile": {
                "user_id": profile.user_id,
                "expertise_level": profile.expertise_level.value,
                "device_info": profile.device_info,
                "accessibility_needs": [need.value for need in profile.accessibility_needs],
                "interface_preferences": profile.interface_preferences
            }
        }
    except Exception as e:
        logger.error(f"Error creating user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}/profile")
async def get_user_profile(user_id: str):
    """Get user profile"""
    try:
        profile = await interface_intelligence.get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {
            "user_id": profile.user_id,
            "expertise_level": profile.expertise_level.value,
            "device_info": profile.device_info,
            "accessibility_needs": [need.value for need in profile.accessibility_needs],
            "interface_preferences": profile.interface_preferences,
            "created_at": profile.created_at.isoformat() if profile.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interactions")
async def record_interaction(request: InteractionEventRequest):
    """Record user interaction"""
    try:
        interaction = await interface_intelligence.record_interaction(
            request.user_id,
            request.event_type,
            request.target_element,
            request.duration,
            request.success,
            request.metadata
        )
        
        return {
            "success": True,
            "interaction_id": interaction.interaction_id,
            "timestamp": interaction.timestamp.isoformat()
        }
    except Exception as e:
        logger.error(f"Error recording interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}/interface-config")
async def get_interface_config(user_id: str, context: Optional[str] = None):
    """Get adaptive interface configuration"""
    try:
        interaction_context = InteractionContext(context) if context else None
        config = await get_adaptive_interface_config(user_id, interaction_context)
        return config
    except Exception as e:
        logger.error(f"Error getting interface config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_adaptive_interface_config(user_id: str, context: Optional[InteractionContext] = None) -> Dict[str, Any]:
    """Get combined adaptive interface configuration"""
    try:
        # Get base interface configuration
        base_config = await interface_intelligence.generate_interface_config(user_id, context)
        
        # Get progressive disclosure configuration
        disclosure_config = await disclosure_engine.get_interface_configuration(user_id, context)
        
        # Get zero-knowledge onboarding status
        zk_progress = zero_knowledge_system.get_user_progress_summary(user_id)
        
        # Combine configurations
        combined_config = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "base_interface": base_config,
            "feature_disclosure": {
                "visible_features": disclosure_config.get("visible_features", []),
                "suggested_features": disclosure_config.get("suggested_features", []),
                "hidden_features": disclosure_config.get("hidden_features", []),
                "feature_groups": dict(disclosure_config.get("feature_groups", {})),
                "disclosure_hints": disclosure_config.get("disclosure_hints", {}),
                "learning_suggestions": disclosure_config.get("learning_suggestions", [])
            },
            "onboarding": {
                "stage": zk_progress.get("current_stage", "first_visit"),
                "confidence_level": zk_progress.get("confidence_level", "building"),
                "next_milestone": zk_progress.get("next_milestone", {}),
                "achievements": zk_progress.get("achievements", []),
                "help_available": True
            },
            "adaptive_elements": {
                "complexity_level": base_config.get("complexity_level", "basic"),
                "layout_density": base_config.get("layout_density", "comfortable"),
                "interaction_style": base_config.get("interaction_style", "standard"),
                "help_system": "proactive" if zk_progress.get("confidence_level") == "building" else "available"
            }
        }
        
        return combined_config
        
    except Exception as e:
        logger.error(f"Error generating adaptive interface config: {e}")
        raise

# Progressive Disclosure endpoints
@app.post("/api/features/usage")
async def record_feature_usage(request: FeatureUsageRequest):
    """Record feature usage for progressive disclosure"""
    try:
        context = InteractionContext(request.context) if request.context else None
        await disclosure_engine.record_feature_usage(
            request.user_id,
            request.feature_id,
            request.duration,
            request.success,
            context
        )
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error recording feature usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/features/{feature_id}/accept")
async def accept_feature_suggestion(user_id: str, feature_id: str):
    """Accept a suggested feature"""
    try:
        success = await disclosure_engine.accept_feature_suggestion(user_id, feature_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error accepting feature suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/features/{feature_id}/dismiss")
async def dismiss_feature_suggestion(user_id: str, feature_id: str, hide_permanently: bool = False):
    """Dismiss a suggested feature"""
    try:
        success = await disclosure_engine.dismiss_feature_suggestion(user_id, feature_id, hide_permanently)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error dismissing feature suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}/analytics")
async def get_user_analytics(user_id: str):
    """Get user analytics and feature usage statistics"""
    try:
        analytics = disclosure_engine.get_feature_analytics(user_id)
        return analytics
    except Exception as e:
        logger.error(f"Error getting user analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Chatbot Assistant endpoints
@app.post("/api/chat/start")
async def start_chat_conversation(request: ChatMessageRequest):
    """Start a new configuration conversation"""
    try:
        response = await chatbot_assistant.start_conversation(request.user_id, request.message)
        
        return {
            "success": True,
            "response": {
                "type": response.response_type.value,
                "message": response.message,
                "options": response.options,
                "next_question": response.next_question,
                "configuration_data": response.configuration_data,
                "requires_confirmation": response.requires_confirmation
            }
        }
    except Exception as e:
        logger.error(f"Error starting chat conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/continue")
async def continue_chat_conversation(request: ChatMessageRequest):
    """Continue an existing conversation"""
    try:
        if not request.session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        response = await chatbot_assistant.continue_conversation(request.session_id, request.message)
        
        return {
            "success": True,
            "response": {
                "type": response.response_type.value,
                "message": response.message,
                "options": response.options,
                "next_question": response.next_question,
                "configuration_data": response.configuration_data,
                "requires_confirmation": response.requires_confirmation
            }
        }
    except Exception as e:
        logger.error(f"Error continuing chat conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/{session_id}/summary")
async def get_conversation_summary(session_id: str):
    """Get conversation summary"""
    try:
        summary = chatbot_assistant.get_conversation_summary(session_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Zero-Knowledge Success endpoints
@app.post("/api/users/{user_id}/initialize")
async def initialize_user_journey(user_id: str, context: Optional[Dict[str, Any]] = None):
    """Initialize zero-knowledge success journey"""
    try:
        result = await zero_knowledge_system.initialize_user_journey(user_id, context)
        return result
    except Exception as e:
        logger.error(f"Error initializing user journey: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}/progress")
async def get_user_progress(user_id: str):
    """Get user's progress through zero-knowledge journey"""
    try:
        progress = zero_knowledge_system.get_user_progress_summary(user_id)
        return progress
    except Exception as e:
        logger.error(f"Error getting user progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}/help")
async def get_contextual_help(user_id: str, context: str = ""):
    """Get contextual help for user"""
    try:
        help_content = await zero_knowledge_system.get_contextual_help(user_id, context)
        return help_content
    except Exception as e:
        logger.error(f"Error getting contextual help: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/{user_id}/exploration")
async def start_safe_exploration(user_id: str, request: SafeExplorationRequest):
    """Start safe exploration session"""
    try:
        safety_level = SafetyLevel(request.safety_level) if request.safety_level else None
        result = await zero_knowledge_system.start_safe_exploration(
            user_id, 
            request.exploration_type
        )
        return result
    except Exception as e:
        logger.error(f"Error starting safe exploration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System management endpoints
@app.get("/api/system/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        stats = {
            "active_users": len(interface_intelligence.user_profiles) if interface_intelligence else 0,
            "active_conversations": len(chatbot_assistant.active_conversations) if chatbot_assistant else 0,
            "active_journeys": len(zero_knowledge_system.user_progress) if zero_knowledge_system else 0,
            "websocket_connections": len(active_connections),
            "uptime": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/features/catalog")
async def get_feature_catalog():
    """Get catalog of available features for disclosure"""
    try:
        catalog = {}
        if disclosure_engine:
            for feature_id, feature in disclosure_engine.features.items():
                catalog[feature_id] = {
                    "name": feature.name,
                    "description": feature.description,
                    "complexity": feature.complexity.value,
                    "category": feature.category,
                    "prerequisites": feature.prerequisites
                }
        return {"features": catalog}
    except Exception as e:
        logger.error(f"Error getting feature catalog: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Accessibility AI endpoints
@app.post("/api/accessibility/profile")
async def create_accessibility_profile(request: dict):
    """Create or update accessibility profile for user"""
    try:
        if not accessibility_ai:
            raise HTTPException(status_code=503, detail="Accessibility AI not available")
        
        user_id = request.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        initial_data = request.get("initial_data", {})
        profile = await accessibility_ai.create_accessibility_profile(user_id, initial_data)
        
        return {
            "user_id": profile.user_id,
            "detected_needs": {need.value: level.value for need, level in profile.detected_needs.items()},
            "adaptations_enabled": profile.adaptations_enabled,
            "confidence_scores": profile.confidence_scores,
            "last_updated": profile.last_updated.isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating accessibility profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accessibility/analyze")
async def analyze_accessibility_interactions(request: dict):
    """Analyze user interactions for accessibility needs"""
    try:
        if not accessibility_ai:
            raise HTTPException(status_code=503, detail="Accessibility AI not available")
        
        user_id = request.get("user_id")
        interaction_data = request.get("interaction_data", {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        profile = await accessibility_ai.analyze_user_interactions(user_id, interaction_data)
        
        return {
            "user_id": profile.user_id,
            "detected_needs": {need.value: level.value for need, level in profile.detected_needs.items()},
            "interaction_patterns": profile.interaction_patterns,
            "adaptations_enabled": profile.adaptations_enabled,
            "confidence_scores": profile.confidence_scores
        }
    except Exception as e:
        logger.error(f"Error analyzing accessibility interactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accessibility/{user_id}/adaptations")
async def get_accessibility_adaptations(user_id: str, context: dict = None):
    """Get real-time accessibility adaptations"""
    try:
        if not accessibility_ai:
            raise HTTPException(status_code=503, detail="Accessibility AI not available")
        
        context_data = context or {}
        adaptations = await accessibility_ai.get_real_time_adaptations(user_id, context_data)
        
        return {"adaptations": adaptations}
    except Exception as e:
        logger.error(f"Error getting accessibility adaptations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accessibility/{user_id}/voice")
async def handle_voice_interaction(user_id: str, request: dict):
    """Handle voice commands and provide voice guidance"""
    try:
        if not accessibility_ai:
            raise HTTPException(status_code=503, detail="Accessibility AI not available")
        
        action = request.get("action", "listen")
        
        if action == "listen":
            timeout = request.get("timeout", 10)
            command_result = await accessibility_ai.handle_voice_command(user_id, timeout)
            return {"command_result": command_result}
        
        elif action == "speak":
            content = request.get("content", "")
            urgency = request.get("urgency", "normal")
            success = await accessibility_ai.provide_voice_guidance(user_id, content, urgency)
            return {"success": success}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'listen' or 'speak'")
    
    except Exception as e:
        logger.error(f"Error in voice interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accessibility/{user_id}/report")
async def get_accessibility_report(user_id: str):
    """Get comprehensive accessibility report for user"""
    try:
        if not accessibility_ai:
            raise HTTPException(status_code=503, detail="Accessibility AI not available")
        
        report = await accessibility_ai.generate_accessibility_report(user_id)
        return report
    except Exception as e:
        logger.error(f"Error generating accessibility report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Predictive Interface Generation endpoints
@app.post("/api/interface/generate")
async def generate_interface(request: dict):
    """Generate optimal interface for given user context"""
    try:
        if not predictive_generator:
            raise HTTPException(status_code=503, detail="Predictive generator not available")
        
        # Parse user context
        context_data = request.get("user_context", {})
        
        # Create UserContext object
        user_context = UserContext(
            user_id=context_data.get("user_id", "unknown"),
            device_type=context_data.get("device_type", "desktop"),
            screen_size=tuple(context_data.get("screen_size", [1920, 1080])),
            available_space=tuple(context_data.get("available_space", [1600, 900])),
            interaction_methods=[InteractionMode(method) for method in context_data.get("interaction_methods", ["mouse"])],
            expertise_level=context_data.get("expertise_level", 0.5),
            accessibility_needs=context_data.get("accessibility_needs", []),
            task_context=context_data.get("task_context", "general"),
            time_constraints=context_data.get("time_constraints", 300.0),
            cognitive_load=context_data.get("cognitive_load", 0.5),
            stress_level=context_data.get("stress_level", 0.3),
            attention_span=context_data.get("attention_span", 600.0),
            current_goals=context_data.get("current_goals", [])
        )
        
        # Generate interface
        generated_interface = await predictive_generator.generate_interface(user_context)
        
        return {
            "interface_id": generated_interface.interface_id,
            "layout_pattern": generated_interface.layout_pattern.value,
            "interface_type": generated_interface.interface_type.value,
            "components": [
                {
                    "component_id": comp.component_id,
                    "component_type": comp.component_type,
                    "position": comp.position,
                    "size": comp.size,
                    "importance": comp.importance,
                    "complexity": comp.complexity,
                    "accessibility_features": comp.accessibility_features
                }
                for comp in generated_interface.components
            ],
            "predicted_performance": generated_interface.predicted_performance,
            "accessibility_score": generated_interface.accessibility_score,
            "usability_score": generated_interface.usability_score,
            "generation_confidence": generated_interface.generation_confidence,
            "optimization_suggestions": generated_interface.optimization_suggestions,
            "generation_time": generated_interface.generation_time.isoformat()
        }
    except Exception as e:
        logger.error(f"Error generating interface: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interface/{interface_id}/learn")
async def learn_from_interface_interaction(interface_id: str, request: dict):
    """Learn from user interaction with generated interface"""
    try:
        if not predictive_generator:
            raise HTTPException(status_code=503, detail="Predictive generator not available")
        
        interaction_data = request.get("interaction_data", {})
        await predictive_generator.learn_from_interaction(interface_id, interaction_data)
        
        return {"success": True, "message": "Learning data recorded"}
    except Exception as e:
        logger.error(f"Error learning from interface interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interface/{interface_id}/analytics")
async def get_interface_analytics(interface_id: str):
    """Get analytics for a generated interface"""
    try:
        if not predictive_generator:
            raise HTTPException(status_code=503, detail="Predictive generator not available")
        
        analytics = await predictive_generator.get_interface_analytics(interface_id)
        return analytics
    except Exception as e:
        logger.error(f"Error getting interface analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interface/train")
async def train_predictive_generator(request: dict):
    """Train the predictive interface generator"""
    try:
        if not predictive_generator:
            raise HTTPException(status_code=503, detail="Predictive generator not available")
        
        epochs = request.get("epochs", 100)
        await predictive_generator.train_neural_generator(epochs)
        
        return {"success": True, "message": f"Training completed with {epochs} epochs"}
    except Exception as e:
        logger.error(f"Error training predictive generator: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8433))
    
    print(f"""
🎨 Adaptive UX Service Starting
================================
Port: {port}
Features:
✓ Interface Intelligence - Device detection & expertise analysis
✓ Progressive Disclosure - Smart feature revelation
✓ Chatbot Assistant - Natural language configuration  
✓ Zero-Knowledge Success - Intuitive first-run experiences
✓ Accessibility AI - Advanced accessibility adaptations
✓ Predictive Interface Generation - AI-powered interface optimization

WebSocket: ws://localhost:{port}/ws/{{user_id}}
Health Check: http://localhost:{port}/health
API Docs: http://localhost:{port}/docs
""")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )