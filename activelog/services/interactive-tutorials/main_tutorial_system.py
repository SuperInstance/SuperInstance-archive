#!/usr/bin/env python3

import asyncio
import sys
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
import uvicorn
import json
from datetime import datetime
import uuid

# Add the service directories to the Python path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "3d-explorer"))
sys.path.append(str(current_dir / "project-walkthrough"))
sys.path.append(str(current_dir / "voice-guide"))
sys.path.append(str(current_dir / "ar-overlay"))
sys.path.append(str(current_dir / "mistake-learning"))
sys.path.append(str(current_dir / "celebrations"))

# Import all the subsystems
from model_guide import Model3DGuideSystem
from tutorial_engine import ProjectTutorialSystem
from voice_assistant import VoiceGuidanceSystem
from ar_instructions import ARInstructionSystem
from adaptive_paths import MistakeBasedLearningSystem
from animation_engine import CelebrationSystem

app = FastAPI(
    title="Interactive Tutorial System",
    description="Comprehensive tutorial platform with 3D exploration, voice guidance, AR overlays, and adaptive learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class TutorialCreateRequest(BaseModel):
    title: str = Field(..., description="Tutorial title")
    description: str = Field(..., description="Tutorial description")
    project_type: str = Field(..., description="Type of project (coding, crafting, etc.)")
    difficulty: str = Field(..., description="Difficulty level")
    steps_data: List[Dict[str, Any]] = Field(..., description="Tutorial steps")

class UserActionRequest(BaseModel):
    user_action: Dict[str, Any] = Field(..., description="User's action")
    expected_action: Dict[str, Any] = Field(..., description="Expected action")
    context: Dict[str, Any] = Field(..., description="Context information")

class VoicePreferencesRequest(BaseModel):
    personality: str = Field(default="friendly_teacher")
    pace: str = Field(default="normal")
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    use_audio_cues: bool = Field(default=True)
    language_code: str = Field(default="en-US")

class ARSceneRequest(BaseModel):
    tutorial_step: Dict[str, Any] = Field(..., description="Tutorial step data")
    environment_context: Optional[Dict[str, Any]] = Field(default=None)

class CelebrationRequest(BaseModel):
    celebration_type: str = Field(..., description="Type of celebration")
    intensity: Optional[str] = Field(default="moderate")
    context: Optional[Dict[str, Any]] = Field(default=None)

# Initialize all subsystems
class TutorialSystemManager:
    def __init__(self):
        self.model_3d_system = Model3DGuideSystem()
        self.tutorial_system = ProjectTutorialSystem()
        self.voice_system = VoiceGuidanceSystem()
        self.ar_system = ARInstructionSystem()
        self.mistake_learning_system = MistakeBasedLearningSystem()
        self.celebration_system = CelebrationSystem()
        
        # WebSocket connections for real-time features
        self.websocket_connections: Dict[str, WebSocket] = {}
        
    async def initialize(self):
        """Initialize all subsystems."""
        print("🚀 Initializing Interactive Tutorial System...")
        print("   ✓ 3D Model Guide System")
        print("   ✓ Project Tutorial System") 
        print("   ✓ Voice Guidance System")
        print("   ✓ AR Instruction System")
        print("   ✓ Mistake-Based Learning System")
        print("   ✓ Celebration System")
        print("🎉 All systems initialized successfully!")

# Global system manager
tutorial_manager = TutorialSystemManager()

@app.on_event("startup")
async def startup_event():
    await tutorial_manager.initialize()

@app.get("/", response_class=HTMLResponse)
async def root():
    """Main dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Interactive Tutorial System</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }
            .systems { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .system-card { background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #667eea; }
            .system-card h3 { margin-top: 0; color: #333; }
            .feature-list { list-style: none; padding: 0; }
            .feature-list li { background: #e9ecef; margin: 5px 0; padding: 8px 12px; border-radius: 5px; }
            .api-link { display: inline-block; background: #667eea; color: white; padding: 8px 16px; border-radius: 5px; text-decoration: none; margin: 5px; }
            .api-link:hover { background: #5a67d8; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎓 Interactive Tutorial System</h1>
            <p>Comprehensive learning platform with multiple modalities and adaptive features</p>
            <p><strong>Server running on port 8216</strong></p>
        </div>
        
        <div class="systems">
            <div class="system-card">
                <h3>🔍 3D Model Explorer</h3>
                <ul class="feature-list">
                    <li>Interactive 3D model exploration</li>
                    <li>Guided learning paths</li>
                    <li>Component highlighting</li>
                    <li>Achievement tracking</li>
                </ul>
                <a href="/docs#/3D%20Models" class="api-link">API Documentation</a>
            </div>
            
            <div class="system-card">
                <h3>📝 Project Walkthroughs</h3>
                <ul class="feature-list">
                    <li>Step-by-step tutorials</li>
                    <li>Adaptive difficulty</li>
                    <li>Progress validation</li>
                    <li>Multiple project types</li>
                </ul>
                <a href="/docs#/Tutorials" class="api-link">API Documentation</a>
            </div>
            
            <div class="system-card">
                <h3>🎤 Voice Guidance</h3>
                <ul class="feature-list">
                    <li>Personalized voice instructions</li>
                    <li>Multiple personalities</li>
                    <li>Contextual responses</li>
                    <li>Accessibility support</li>
                </ul>
                <a href="/docs#/Voice" class="api-link">API Documentation</a>
            </div>
            
            <div class="system-card">
                <h3>🥽 AR Overlays</h3>
                <ul class="feature-list">
                    <li>Augmented reality instructions</li>
                    <li>Object detection</li>
                    <li>Spatial anchoring</li>
                    <li>Interactive elements</li>
                </ul>
                <a href="/docs#/AR" class="api-link">API Documentation</a>
            </div>
            
            <div class="system-card">
                <h3>🧠 Mistake Learning</h3>
                <ul class="feature-list">
                    <li>Automatic mistake detection</li>
                    <li>Personalized learning paths</li>
                    <li>Adaptive interventions</li>
                    <li>Progress tracking</li>
                </ul>
                <a href="/docs#/Learning" class="api-link">API Documentation</a>
            </div>
            
            <div class="system-card">
                <h3>🎉 Celebrations</h3>
                <ul class="feature-list">
                    <li>Dynamic celebration animations</li>
                    <li>Personalized intensity</li>
                    <li>Multiple animation styles</li>
                    <li>Accessibility options</li>
                </ul>
                <a href="/docs#/Celebrations" class="api-link">API Documentation</a>
            </div>
        </div>
        
        <div style="margin-top: 30px; text-align: center;">
            <a href="/docs" class="api-link">📚 Full API Documentation</a>
            <a href="/redoc" class="api-link">📖 ReDoc Documentation</a>
        </div>
    </body>
    </html>
    """

# 3D Model Exploration Endpoints
@app.post("/api/3d-models", tags=["3D Models"])
async def create_3d_model(name: str, model_type: str, file_path: str, 
                         description: str = "", subject_area: str = "general"):
    """Create a new 3D model for exploration."""
    try:
        model = await tutorial_manager.model_3d_system.create_3d_model(
            name, model_type, file_path, description, subject_area
        )
        return {"success": True, "model_id": model.id, "model": model}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/3d-models", tags=["3D Models"])
async def get_model_catalog(filter_type: Optional[str] = None, subject_area: Optional[str] = None):
    """Get catalog of available 3D models."""
    try:
        catalog = await tutorial_manager.model_3d_system.get_model_catalog(filter_type, subject_area)
        return {"success": True, "models": catalog}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/3d-models/{model_id}/explore", tags=["3D Models"])
async def start_3d_exploration(model_id: str, user_id: str, difficulty: str = "beginner"):
    """Start a 3D model exploration session."""
    try:
        session = await tutorial_manager.model_3d_system.start_exploration_session(
            model_id, user_id, difficulty
        )
        return {"success": True, "session": session}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Project Tutorial Endpoints
@app.post("/api/tutorials", tags=["Tutorials"])
async def create_tutorial(request: TutorialCreateRequest):
    """Create a new project tutorial."""
    try:
        tutorial = await tutorial_manager.tutorial_system.create_tutorial(
            request.title, request.description, request.project_type, 
            request.difficulty, request.steps_data
        )
        return {"success": True, "tutorial_id": tutorial.id, "tutorial": tutorial}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tutorials", tags=["Tutorials"])
async def get_tutorial_catalog(project_type: Optional[str] = None, 
                              difficulty: Optional[str] = None):
    """Get catalog of available tutorials."""
    try:
        catalog = await tutorial_manager.tutorial_system.get_tutorial_catalog(
            project_type, difficulty
        )
        return {"success": True, "tutorials": catalog}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tutorials/{tutorial_id}/start", tags=["Tutorials"])
async def start_tutorial_session(tutorial_id: str, user_id: str, 
                                user_profile: Optional[Dict[str, Any]] = None):
    """Start a tutorial session."""
    try:
        session = await tutorial_manager.tutorial_system.start_tutorial_session(
            tutorial_id, user_id, user_profile or {}
        )
        return {"success": True, "session": session}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tutorials/{tutorial_id}/submit-step", tags=["Tutorials"])
async def submit_step_completion(tutorial_id: str, user_id: str, step_id: str,
                                validation_data: Dict[str, Any]):
    """Submit step completion for validation."""
    try:
        result = await tutorial_manager.tutorial_system.submit_step_completion(
            user_id, tutorial_id, step_id, validation_data
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Voice Guidance Endpoints
@app.post("/api/voice/profile", tags=["Voice"])
async def create_voice_profile(user_id: str, preferences: VoicePreferencesRequest):
    """Create user voice profile."""
    try:
        profile = await tutorial_manager.voice_system.create_user_voice_profile(
            user_id, preferences.dict()
        )
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/guidance", tags=["Voice"])
async def generate_voice_guidance(tutorial_step: Dict[str, Any], user_id: str,
                                 progress_context: Optional[Dict[str, Any]] = None):
    """Generate voice guidance for a tutorial step."""
    try:
        instruction = await tutorial_manager.voice_system.generate_step_guidance(
            tutorial_step, user_id, progress_context
        )
        return {"success": True, "voice_instruction": instruction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice/input", tags=["Voice"])
async def handle_voice_input(user_input: str, user_id: str, 
                            current_context: Dict[str, Any]):
    """Handle user voice input."""
    try:
        response = await tutorial_manager.voice_system.handle_user_voice_input(
            user_input, user_id, current_context
        )
        return {"success": True, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# AR Overlay Endpoints
@app.post("/api/ar/scene", tags=["AR"])
async def create_ar_scene(request: ARSceneRequest):
    """Create AR scene for tutorial step."""
    try:
        scene = await tutorial_manager.ar_system.create_ar_scene(
            request.tutorial_step, request.environment_context
        )
        return {"success": True, "scene": scene}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ar/scene/{scene_id}/optimize", tags=["AR"])
async def optimize_ar_scene(scene_id: str, user_position: Dict[str, float],
                           detected_objects: List[Dict[str, Any]],
                           lighting_conditions: Dict[str, Any]):
    """Optimize AR scene for current environment."""
    try:
        optimized_scene = await tutorial_manager.ar_system.optimize_scene_for_environment(
            scene_id, user_position, detected_objects, lighting_conditions
        )
        return {"success": True, "optimized_scene": optimized_scene}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ar/interaction", tags=["AR"])
async def handle_ar_interaction(scene_id: str, element_id: str, 
                               interaction_type: str, interaction_data: Dict[str, Any]):
    """Handle AR element interaction."""
    try:
        result = await tutorial_manager.ar_system.handle_ar_interaction(
            scene_id, element_id, interaction_type, interaction_data
        )
        return {"success": True, "interaction_result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ar/setup/{scene_id}", tags=["AR"])
async def get_ar_setup_instructions(scene_id: str):
    """Get AR setup instructions."""
    try:
        instructions = await tutorial_manager.ar_system.get_ar_setup_instructions(scene_id)
        return {"success": True, "setup_instructions": instructions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mistake-Based Learning Endpoints
@app.post("/api/learning/profile", tags=["Learning"])
async def create_learning_profile(user_id: str, initial_data: Optional[Dict[str, Any]] = None):
    """Create user learning profile."""
    try:
        profile = await tutorial_manager.mistake_learning_system.create_user_learning_profile(
            user_id, initial_data or {}
        )
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learning/process-action", tags=["Learning"])
async def process_user_action(request: UserActionRequest):
    """Process user action and detect/handle mistakes."""
    try:
        result = await tutorial_manager.mistake_learning_system.process_user_action(
            request.user_action, request.expected_action, request.context
        )
        return {"success": True, "learning_result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/learning/path/{path_id}/progress", tags=["Learning"])
async def get_learning_path_progress(path_id: str):
    """Get learning path progress."""
    try:
        progress = await tutorial_manager.mistake_learning_system.get_learning_path_progress(path_id)
        return {"success": True, "progress": progress}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Celebration System Endpoints
@app.post("/api/celebrations/profile", tags=["Celebrations"])
async def create_celebration_profile(user_id: str, preferences: Optional[Dict[str, Any]] = None):
    """Create user celebration profile."""
    try:
        profile = await tutorial_manager.celebration_system.create_user_profile(
            user_id, preferences or {}
        )
        return {"success": True, "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/celebrations/trigger", tags=["Celebrations"])
async def trigger_celebration(user_id: str, request: CelebrationRequest):
    """Trigger a celebration animation."""
    try:
        animation = await tutorial_manager.celebration_system.trigger_celebration(
            request.celebration_type, user_id, request.context, request.intensity
        )
        
        # Notify connected WebSocket clients
        if user_id in tutorial_manager.websocket_connections:
            await tutorial_manager.websocket_connections[user_id].send_json({
                "type": "celebration",
                "animation": animation.__dict__
            })
        
        return {"success": True, "celebration": animation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/celebrations/stats/{user_id}", tags=["Celebrations"])
async def get_celebration_stats(user_id: str):
    """Get celebration statistics for user."""
    try:
        stats = await tutorial_manager.celebration_system.get_celebration_stats(user_id)
        return {"success": True, "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Integrated Learning Session Endpoints
@app.post("/api/session/start", tags=["Integrated Sessions"])
async def start_integrated_session(user_id: str, tutorial_id: str, 
                                  preferences: Optional[Dict[str, Any]] = None):
    """Start an integrated learning session with all systems."""
    try:
        session_id = str(uuid.uuid4())
        
        # Initialize all user profiles if they don't exist
        voice_profile = await tutorial_manager.voice_system.get_user_voice_profile(user_id)
        if not voice_profile:
            await tutorial_manager.voice_system.create_user_voice_profile(user_id, preferences or {})
        
        learning_profile = await tutorial_manager.mistake_learning_system.get_user_learning_profile(user_id)
        if not learning_profile:
            await tutorial_manager.mistake_learning_system.create_user_learning_profile(user_id, preferences or {})
        
        celebration_profile = await tutorial_manager.celebration_system.get_user_profile(user_id)
        if not celebration_profile:
            await tutorial_manager.celebration_system.create_user_profile(user_id, preferences or {})
        
        # Start tutorial session
        tutorial_session = await tutorial_manager.tutorial_system.start_tutorial_session(
            tutorial_id, user_id, preferences or {}
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "tutorial_session": tutorial_session,
            "message": "Integrated learning session started with all systems active"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/session/{session_id}/step", tags=["Integrated Sessions"])
async def process_integrated_step(session_id: str, user_id: str, tutorial_id: str,
                                 step_data: Dict[str, Any], user_action: Dict[str, Any]):
    """Process a step with integrated feedback from all systems."""
    try:
        results = {}
        
        # 1. Generate voice guidance for the step
        if step_data:
            voice_guidance = await tutorial_manager.voice_system.generate_step_guidance(
                step_data, user_id, {"session_id": session_id}
            )
            results["voice_guidance"] = voice_guidance
        
        # 2. Create AR scene if applicable
        if step_data.get("supports_ar", False):
            ar_scene = await tutorial_manager.ar_system.create_ar_scene(
                step_data, {"session_id": session_id, "user_id": user_id}
            )
            results["ar_scene"] = ar_scene
        
        # 3. Process user action for mistake detection
        if user_action:
            expected_action = step_data.get("expected_action", {})
            context = {
                "user_id": user_id,
                "tutorial_id": tutorial_id,
                "step_id": step_data.get("id"),
                "session_id": session_id
            }
            
            mistake_result = await tutorial_manager.mistake_learning_system.process_user_action(
                user_action, expected_action, context
            )
            results["mistake_analysis"] = mistake_result
            
            # 4. Trigger celebration if step completed successfully
            if not mistake_result["mistake_detected"]:
                celebration = await tutorial_manager.celebration_system.trigger_celebration(
                    "step_complete", user_id, context, "moderate"
                )
                results["celebration"] = celebration
                
                # Send real-time celebration to WebSocket
                if user_id in tutorial_manager.websocket_connections:
                    await tutorial_manager.websocket_connections[user_id].send_json({
                        "type": "celebration",
                        "animation": celebration.__dict__
                    })
        
        return {"success": True, "integrated_results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time features
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket connection for real-time tutorial features."""
    await websocket.accept()
    tutorial_manager.websocket_connections[user_id] = websocket
    
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to Interactive Tutorial System",
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        })
        
        while True:
            # Listen for client messages
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            
            elif message_type == "voice_input":
                # Handle voice input
                response = await tutorial_manager.voice_system.handle_user_voice_input(
                    data["input"], user_id, data.get("context", {})
                )
                await websocket.send_json({
                    "type": "voice_response",
                    "response": response.__dict__
                })
            
            elif message_type == "ar_interaction":
                # Handle AR interaction
                result = await tutorial_manager.ar_system.handle_ar_interaction(
                    data["scene_id"], data["element_id"], 
                    data["interaction_type"], data.get("interaction_data", {})
                )
                await websocket.send_json({
                    "type": "ar_interaction_result",
                    "result": result
                })
            
            elif message_type == "request_celebration":
                # Trigger celebration
                celebration = await tutorial_manager.celebration_system.trigger_celebration(
                    data["celebration_type"], user_id, 
                    data.get("context", {}), data.get("intensity", "moderate")
                )
                await websocket.send_json({
                    "type": "celebration",
                    "animation": celebration.__dict__
                })
    
    except WebSocketDisconnect:
        # Clean up connection
        if user_id in tutorial_manager.websocket_connections:
            del tutorial_manager.websocket_connections[user_id]
    except Exception as e:
        print(f"WebSocket error for user {user_id}: {e}")
        if user_id in tutorial_manager.websocket_connections:
            del tutorial_manager.websocket_connections[user_id]

# System Status and Health Endpoints
@app.get("/api/health", tags=["System"])
async def health_check():
    """System health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "systems": {
            "3d_models": "operational",
            "tutorials": "operational", 
            "voice_guidance": "operational",
            "ar_overlays": "operational",
            "mistake_learning": "operational",
            "celebrations": "operational"
        },
        "active_connections": len(tutorial_manager.websocket_connections),
        "server_info": {
            "version": "1.0.0",
            "port": 8216
        }
    }

@app.get("/api/system/stats", tags=["System"])
async def get_system_stats():
    """Get system usage statistics."""
    return {
        "active_websocket_connections": len(tutorial_manager.websocket_connections),
        "connected_users": list(tutorial_manager.websocket_connections.keys()),
        "system_uptime": "N/A",  # Would calculate actual uptime
        "total_tutorials": "N/A",  # Would query actual count
        "total_3d_models": "N/A",  # Would query actual count
        "celebration_stats": "N/A"  # Would aggregate celebration stats
    }

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "status_code": 404}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error", "status_code": 500, "detail": str(exc)}

if __name__ == "__main__":
    print("🎓 Starting Interactive Tutorial System...")
    print("🌟 Features:")
    print("   • 3D Model Exploration with guided learning")
    print("   • Step-by-step Project Walkthroughs") 
    print("   • Voice-guided Instructions with personalities")
    print("   • AR Overlay Instructions with object detection")
    print("   • Mistake-based Learning Paths with adaptation")
    print("   • Celebration Animations with personalization")
    print("   • Real-time WebSocket communication")
    print("   • Integrated learning sessions")
    print()
    print("🚀 Server starting on http://localhost:8216")
    print("📚 API Documentation: http://localhost:8216/docs")
    print("📖 ReDoc Documentation: http://localhost:8216/redoc")
    
    uvicorn.run(
        "main_tutorial_system:app",
        host="0.0.0.0", 
        port=8216,
        reload=True,
        log_level="info"
    )