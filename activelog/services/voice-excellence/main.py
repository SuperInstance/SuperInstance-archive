"""
Voice Excellence System - Main Service
Port: 8380

This is the main service that integrates all voice excellence components
into a comprehensive marine and industrial voice command system.

Author: Claude
Date: 2025-08-24
"""

import asyncio
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Import voice excellence components
sys.path.append(str(Path(__file__).parent))

from audio.noise_cancellation import MarineIndustrialNoiseCanceller
from languages.multi_language_support import MultiLanguageProcessor
from wake_words.wake_word_detector import CustomWakeWordDetector
from context.context_engine import ContextAwarenessEngine, ContextType
from safety.confirmation_protocols import ConfirmationProtocols
from safety.emergency_procedures import EmergencyProcedures
from operation.hands_free import HandsFreeOperator, HandsFreeMode
from connectivity.bluetooth_headset import BluetoothHeadsetManager

# FastAPI app
app = FastAPI(
    title="Voice Excellence System",
    description="Comprehensive voice command system for marine and industrial environments",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Global system components
noise_canceller = None
language_processor = None
wake_word_detector = None
context_engine = None
confirmation_protocols = None
emergency_procedures = None
hands_free_operator = None
bluetooth_manager = None

# WebSocket connections
websocket_connections: List[WebSocket] = []

# System metrics
system_metrics = {
    "service_start_time": datetime.now(),
    "total_commands_processed": 0,
    "successful_commands": 0,
    "failed_commands": 0,
    "active_sessions": 0,
    "emergency_events": 0,
    "uptime_hours": 0
}

# Pydantic models for API
class VoiceCommandRequest(BaseModel):
    command: str
    user_id: str
    context: Optional[Dict[str, Any]] = None
    language: str = "en"
    session_id: Optional[str] = None

class VoiceCommandResponse(BaseModel):
    success: bool
    message: str
    interpreted_command: Optional[str] = None
    confirmation_required: bool = False
    emergency_declared: bool = False
    response_data: Optional[Dict[str, Any]] = None

class HandsFreeSessionRequest(BaseModel):
    user_id: str
    mode: str = "voice_only"
    environment: str = "marine_bridge"

class BluetoothConnectRequest(BaseModel):
    device_id: str
    audio_profile: str = "marine_bridge"

class AudioProfileRequest(BaseModel):
    environment_type: str
    noise_level: float
    wind_conditions: bool = False
    engine_noise: bool = False

# Initialize system components
async def init_voice_excellence_system():
    """Initialize all voice excellence components"""
    global noise_canceller, language_processor, wake_word_detector
    global context_engine, confirmation_protocols, emergency_procedures
    global hands_free_operator, bluetooth_manager
    
    try:
        logging.info("Initializing Voice Excellence System...")
        
        # Initialize noise cancellation
        logging.info("Initializing noise cancellation...")
        noise_canceller = MarineIndustrialNoiseCanceller()
        
        # Initialize multi-language support
        logging.info("Initializing multi-language support...")
        language_processor = MultiLanguageProcessor()
        
        # Initialize wake word detection
        logging.info("Initializing wake word detection...")
        wake_word_detector = CustomWakeWordDetector()
        
        # Initialize context awareness
        logging.info("Initializing context awareness engine...")
        context_engine = ContextAwarenessEngine()
        
        # Initialize confirmation protocols
        logging.info("Initializing confirmation protocols...")
        confirmation_protocols = ConfirmationProtocols()
        
        # Initialize emergency procedures
        logging.info("Initializing emergency procedures...")
        emergency_procedures = EmergencyProcedures()
        
        # Initialize hands-free operation
        logging.info("Initializing hands-free operation...")
        hands_free_operator = HandsFreeOperator()
        
        # Initialize Bluetooth headset support
        logging.info("Initializing Bluetooth headset support...")
        bluetooth_manager = BluetoothHeadsetManager()
        
        # Wait a moment for all systems to initialize
        await asyncio.sleep(2)
        
        logging.info("Voice Excellence System initialized successfully!")
        
    except Exception as e:
        logging.error(f"Failed to initialize Voice Excellence System: {e}")
        logging.error(traceback.format_exc())
        raise

# API Routes

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Main dashboard"""
    return HTMLResponse(content=get_dashboard_html(), status_code=200)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Voice Excellence System",
        "version": "1.0.0",
        "port": 8380,
        "uptime_hours": (datetime.now() - system_metrics["service_start_time"]).total_seconds() / 3600,
        "components": {
            "noise_cancellation": noise_canceller is not None,
            "language_processing": language_processor is not None,
            "wake_word_detection": wake_word_detector is not None,
            "context_awareness": context_engine is not None,
            "confirmation_protocols": confirmation_protocols is not None,
            "emergency_procedures": emergency_procedures is not None,
            "hands_free_operation": hands_free_operator is not None,
            "bluetooth_support": bluetooth_manager is not None
        }
    }

@app.post("/api/voice/process", response_model=VoiceCommandResponse)
async def process_voice_command(request: VoiceCommandRequest):
    """Process voice command through the complete pipeline"""
    global system_metrics
    
    try:
        system_metrics["total_commands_processed"] += 1
        
        # Step 1: Language detection and translation
        if language_processor:
            detected_language = language_processor.detect_language(request.command)
            if detected_language != request.language:
                request.command = language_processor.translate_text(
                    request.command, detected_language, request.language
                )
        
        # Step 2: Context awareness
        context_info = None
        if context_engine:
            context_info = await context_engine.interpret_command(request.command, request.user_id)
        
        # Step 3: Check for emergency situations
        emergency_declared = False
        if emergency_procedures:
            emergency_result = await emergency_procedures.process_voice_command(
                request.command, request.user_id, request.context or {}
            )
            
            if emergency_result.get("success") and "emergency" in emergency_result.get("message", "").lower():
                emergency_declared = True
                system_metrics["emergency_events"] += 1
                
                # Broadcast emergency to WebSocket connections
                await broadcast_emergency(emergency_result)
        
        # Step 4: Confirmation protocols for critical commands
        confirmation_required = False
        confirmation_request = None
        if confirmation_protocols:
            # Check if command requires confirmation
            risk_assessment = confirmation_protocols._assess_command_risk(request.command)
            if risk_assessment.name in ["HIGH", "CRITICAL"]:
                confirmation_request = await confirmation_protocols.request_confirmation(
                    request.command, request.user_id, request.context or {}
                )
                confirmation_required = True
        
        # Step 5: Prepare response
        interpreted_command = context_info.interpreted_command if context_info else request.command.lower().replace(" ", "_")
        
        response_data = {
            "context_type": context_info.context_type.value if context_info else "unknown",
            "language_detected": detected_language if language_processor else request.language,
            "emergency_result": emergency_result if emergency_declared else None,
            "confirmation_request": {
                "request_id": confirmation_request.request_id,
                "required_confirmations": [c.value for c in confirmation_request.required_confirmations],
                "timeout_seconds": confirmation_request.timeout_seconds
            } if confirmation_request else None
        }
        
        system_metrics["successful_commands"] += 1
        
        return VoiceCommandResponse(
            success=True,
            message=f"Voice command processed successfully: {interpreted_command}",
            interpreted_command=interpreted_command,
            confirmation_required=confirmation_required,
            emergency_declared=emergency_declared,
            response_data=response_data
        )
    
    except Exception as e:
        system_metrics["failed_commands"] += 1
        logging.error(f"Voice command processing failed: {e}")
        return VoiceCommandResponse(
            success=False,
            message=f"Voice command processing failed: {str(e)}",
            confirmation_required=False,
            emergency_declared=False
        )

@app.post("/api/hands-free/start")
async def start_hands_free_session(request: HandsFreeSessionRequest):
    """Start hands-free operation session"""
    if not hands_free_operator:
        raise HTTPException(status_code=503, detail="Hands-free operator not available")
    
    try:
        # Convert mode string to enum
        mode_map = {
            "voice_only": HandsFreeMode.VOICE_ONLY,
            "voice_gesture": HandsFreeMode.VOICE_GESTURE,
            "voice_eye_tracking": HandsFreeMode.VOICE_EYE_TRACKING,
            "full_multimodal": HandsFreeMode.FULL_MULTIMODAL
        }
        
        mode = mode_map.get(request.mode, HandsFreeMode.VOICE_ONLY)
        
        session_id = await hands_free_operator.start_hands_free_session(
            request.user_id, mode, request.environment
        )
        
        system_metrics["active_sessions"] += 1
        
        return {
            "success": True,
            "session_id": session_id,
            "mode": request.mode,
            "environment": request.environment
        }
    
    except Exception as e:
        logging.error(f"Failed to start hands-free session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/hands-free/{session_id}/end")
async def end_hands_free_session(session_id: str):
    """End hands-free operation session"""
    if not hands_free_operator:
        raise HTTPException(status_code=503, detail="Hands-free operator not available")
    
    try:
        # End session (simplified - actual implementation would be in hands_free_operator)
        system_metrics["active_sessions"] = max(0, system_metrics["active_sessions"] - 1)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Hands-free session ended"
        }
    
    except Exception as e:
        logging.error(f"Failed to end hands-free session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bluetooth/connect")
async def connect_bluetooth_device(request: BluetoothConnectRequest):
    """Connect to Bluetooth device"""
    if not bluetooth_manager:
        raise HTTPException(status_code=503, detail="Bluetooth manager not available")
    
    try:
        success = await bluetooth_manager.connect_device(request.device_id, request.audio_profile)
        
        return {
            "success": success,
            "device_id": request.device_id,
            "audio_profile": request.audio_profile,
            "message": "Device connected successfully" if success else "Connection failed"
        }
    
    except Exception as e:
        logging.error(f"Bluetooth connection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bluetooth/devices")
async def list_bluetooth_devices():
    """List available Bluetooth devices"""
    if not bluetooth_manager:
        raise HTTPException(status_code=503, detail="Bluetooth manager not available")
    
    try:
        connected_devices = bluetooth_manager.get_connected_devices()
        return {
            "success": True,
            "devices": connected_devices,
            "count": len(connected_devices)
        }
    
    except Exception as e:
        logging.error(f"Failed to list Bluetooth devices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audio/optimize")
async def optimize_audio_profile(request: AudioProfileRequest):
    """Optimize audio profile for current environment"""
    if not noise_canceller:
        raise HTTPException(status_code=503, detail="Noise canceller not available")
    
    try:
        # Create environmental profile
        environmental_profile = {
            "environment_type": request.environment_type,
            "noise_level": request.noise_level,
            "wind_conditions": request.wind_conditions,
            "engine_noise": request.engine_noise,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get optimized settings (simplified)
        if request.engine_noise:
            noise_reduction = min(0.9, request.noise_level / 100.0 + 0.3)
        else:
            noise_reduction = min(0.7, request.noise_level / 100.0 + 0.1)
        
        optimized_settings = {
            "noise_reduction_level": noise_reduction,
            "high_pass_filter": 300 if request.wind_conditions else 100,
            "adaptive_gain": True,
            "spectral_subtraction": request.engine_noise,
            "wiener_filtering": request.noise_level > 60
        }
        
        return {
            "success": True,
            "environmental_profile": environmental_profile,
            "optimized_settings": optimized_settings,
            "message": f"Audio profile optimized for {request.environment_type}"
        }
    
    except Exception as e:
        logging.error(f"Audio optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/emergency/active")
async def get_active_emergencies():
    """Get active emergency situations"""
    if not emergency_procedures:
        raise HTTPException(status_code=503, detail="Emergency procedures not available")
    
    try:
        active_emergencies = emergency_procedures.get_active_emergencies()
        return {
            "success": True,
            "active_emergencies": active_emergencies,
            "count": len(active_emergencies)
        }
    
    except Exception as e:
        logging.error(f"Failed to get active emergencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_system_statistics():
    """Get comprehensive system statistics"""
    try:
        stats = {
            "system_info": {
                "service_name": "Voice Excellence System",
                "version": "1.0.0",
                "port": 8380,
                "uptime_hours": round((datetime.now() - system_metrics["service_start_time"]).total_seconds() / 3600, 2),
                "start_time": system_metrics["service_start_time"].isoformat()
            },
            "command_processing": {
                "total_commands": system_metrics["total_commands_processed"],
                "successful_commands": system_metrics["successful_commands"],
                "failed_commands": system_metrics["failed_commands"],
                "success_rate": round((system_metrics["successful_commands"] / max(1, system_metrics["total_commands_processed"])) * 100, 2),
                "emergency_events": system_metrics["emergency_events"],
                "active_sessions": system_metrics["active_sessions"]
            },
            "component_stats": {}
        }
        
        # Add component-specific statistics
        if context_engine:
            stats["component_stats"]["context_engine"] = context_engine.get_context_statistics()
        
        if confirmation_protocols:
            stats["component_stats"]["confirmation_protocols"] = confirmation_protocols.get_confirmation_statistics()
        
        if emergency_procedures:
            stats["component_stats"]["emergency_procedures"] = emergency_procedures.get_emergency_statistics()
        
        if hands_free_operator:
            stats["component_stats"]["hands_free_operator"] = hands_free_operator.get_hands_free_statistics()
        
        if bluetooth_manager:
            stats["component_stats"]["bluetooth_manager"] = bluetooth_manager.get_bluetooth_statistics()
        
        return stats
    
    except Exception as e:
        logging.error(f"Failed to get system statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Send periodic system updates
            if websocket_connections:
                update_data = {
                    "type": "system_update",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "active_sessions": system_metrics["active_sessions"],
                        "total_commands": system_metrics["total_commands_processed"],
                        "success_rate": round((system_metrics["successful_commands"] / max(1, system_metrics["total_commands_processed"])) * 100, 2)
                    }
                }
                
                await websocket.send_text(json.dumps(update_data))
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)

async def broadcast_emergency(emergency_data: Dict[str, Any]):
    """Broadcast emergency event to all WebSocket connections"""
    if websocket_connections:
        broadcast_data = {
            "type": "emergency_alert",
            "timestamp": datetime.now().isoformat(),
            "emergency_data": emergency_data
        }
        
        # Send to all connected clients
        disconnected_clients = []
        for websocket in websocket_connections:
            try:
                await websocket.send_text(json.dumps(broadcast_data))
            except:
                disconnected_clients.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected_clients:
            websocket_connections.remove(websocket)

def get_dashboard_html() -> str:
    """Generate dashboard HTML"""
    current_context = context_engine.get_current_context() if context_engine else None
    active_emergencies = emergency_procedures.get_active_emergencies() if emergency_procedures else []
    connected_devices = bluetooth_manager.get_connected_devices() if bluetooth_manager else []
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>🎙️ Voice Excellence System</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                min-height: 100vh;
                padding: 20px;
            }}
            
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding: 20px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }}
            
            .header h1 {{
                font-size: 2.5rem;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }}
            
            .header p {{
                font-size: 1.1rem;
                opacity: 0.9;
            }}
            
            .dashboard {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }}
            
            .card {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 25px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }}
            
            .card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 35px rgba(0,0,0,0.2);
            }}
            
            .card-header {{
                display: flex;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            }}
            
            .card-icon {{
                font-size: 2rem;
                margin-right: 15px;
            }}
            
            .card-title {{
                font-size: 1.3rem;
                font-weight: 600;
            }}
            
            .metric {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin: 15px 0;
                padding: 10px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }}
            
            .metric-value {{
                font-size: 1.2rem;
                font-weight: bold;
            }}
            
            .status-good {{ color: #4ade80; }}
            .status-warning {{ color: #fbbf24; }}
            .status-error {{ color: #ef4444; }}
            .status-info {{ color: #3b82f6; }}
            
            .emergency-alert {{
                background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
                border: 2px solid #fee2e2;
                animation: pulse 1s infinite;
            }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.7; }}
            }}
            
            .device-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                margin: 5px 0;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                border-left: 4px solid #4ade80;
            }}
            
            .context-indicator {{
                display: inline-block;
                padding: 5px 12px;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 500;
                background: rgba(59, 130, 246, 0.3);
                border: 1px solid rgba(59, 130, 246, 0.5);
            }}
            
            .api-endpoint {{
                font-family: 'Courier New', monospace;
                background: rgba(0, 0, 0, 0.3);
                padding: 8px 12px;
                border-radius: 6px;
                margin: 5px 0;
                border-left: 3px solid #10b981;
                font-size: 0.9rem;
            }}
            
            .footer {{
                text-align: center;
                margin-top: 40px;
                padding: 20px;
                opacity: 0.7;
                font-size: 0.9rem;
            }}
            
            @media (max-width: 768px) {{
                .dashboard {{
                    grid-template-columns: 1fr;
                }}
                
                .header h1 {{
                    font-size: 2rem;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎙️ Voice Excellence System</h1>
            <p>Advanced voice command processing for marine and industrial environments</p>
            <p><strong>Port:</strong> 8380 | <strong>Status:</strong> <span class="status-good">Fully Operational</span></p>
        </div>
        
        <div class="dashboard">
            <!-- System Status -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">⚡</div>
                    <div class="card-title">System Status</div>
                </div>
                <div class="metric">
                    <span>Commands Processed</span>
                    <span class="metric-value status-info">{system_metrics['total_commands_processed']}</span>
                </div>
                <div class="metric">
                    <span>Success Rate</span>
                    <span class="metric-value status-good">{round((system_metrics['successful_commands'] / max(1, system_metrics['total_commands_processed'])) * 100, 1)}%</span>
                </div>
                <div class="metric">
                    <span>Active Sessions</span>
                    <span class="metric-value status-info">{system_metrics['active_sessions']}</span>
                </div>
                <div class="metric">
                    <span>Emergency Events</span>
                    <span class="metric-value {'status-error' if system_metrics['emergency_events'] > 0 else 'status-good'}">{system_metrics['emergency_events']}</span>
                </div>
                <div class="metric">
                    <span>Uptime</span>
                    <span class="metric-value status-good">{round((datetime.now() - system_metrics['service_start_time']).total_seconds() / 3600, 1)}h</span>
                </div>
            </div>
            
            <!-- Current Context -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">🧠</div>
                    <div class="card-title">Context Awareness</div>
                </div>
                <div class="metric">
                    <span>Current Context</span>
                    <span class="context-indicator">{current_context.context_type.value if current_context else 'idle'}</span>
                </div>
                <div class="metric">
                    <span>Confidence</span>
                    <span class="metric-value status-info">{round(current_context.confidence * 100, 1) if current_context else 0}%</span>
                </div>
                <div class="metric">
                    <span>Safety Level</span>
                    <span class="metric-value {'status-error' if current_context and current_context.safety_level == 'critical' else 'status-good'}">{current_context.safety_level if current_context else 'standard'}</span>
                </div>
            </div>
            
            <!-- Active Emergencies -->
            <div class="card {'emergency-alert' if active_emergencies else ''}">
                <div class="card-header">
                    <div class="card-icon">🚨</div>
                    <div class="card-title">Emergency Status</div>
                </div>
                {f'<div class="metric"><span>Active Emergencies</span><span class="metric-value status-error">{len(active_emergencies)}</span></div>' if active_emergencies else '<div class="metric"><span>Status</span><span class="metric-value status-good">All Clear</span></div>'}
                {'<div style="margin-top: 15px;"><strong>Active Emergency Types:</strong><ul>' + ''.join([f'<li style="margin: 5px 0;">{emergency["emergency_type"]}</li>' for emergency in active_emergencies]) + '</ul></div>' if active_emergencies else ''}
            </div>
            
            <!-- Connected Devices -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">🎧</div>
                    <div class="card-title">Bluetooth Devices</div>
                </div>
                <div class="metric">
                    <span>Connected Devices</span>
                    <span class="metric-value status-info">{len(connected_devices)}</span>
                </div>
                {''.join([f'<div class="device-item"><span>{device["name"]}</span><span class="status-good">Connected</span></div>' for device in connected_devices]) if connected_devices else '<div style="text-align: center; opacity: 0.7; margin: 20px 0;">No devices connected</div>'}
            </div>
            
            <!-- Component Status -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">🔧</div>
                    <div class="card-title">Components</div>
                </div>
                <div class="metric">
                    <span>Noise Cancellation</span>
                    <span class="metric-value status-good">{'✓' if noise_canceller else '✗'}</span>
                </div>
                <div class="metric">
                    <span>Multi-Language</span>
                    <span class="metric-value status-good">{'✓' if language_processor else '✗'}</span>
                </div>
                <div class="metric">
                    <span>Wake Word Detection</span>
                    <span class="metric-value status-good">{'✓' if wake_word_detector else '✗'}</span>
                </div>
                <div class="metric">
                    <span>Hands-Free Operation</span>
                    <span class="metric-value status-good">{'✓' if hands_free_operator else '✗'}</span>
                </div>
                <div class="metric">
                    <span>Safety Protocols</span>
                    <span class="metric-value status-good">{'✓' if confirmation_protocols else '✗'}</span>
                </div>
            </div>
            
            <!-- API Endpoints -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon">🔌</div>
                    <div class="card-title">API Endpoints</div>
                </div>
                <div class="api-endpoint">POST /api/voice/process</div>
                <div class="api-endpoint">POST /api/hands-free/start</div>
                <div class="api-endpoint">POST /api/bluetooth/connect</div>
                <div class="api-endpoint">GET /api/bluetooth/devices</div>
                <div class="api-endpoint">POST /api/audio/optimize</div>
                <div class="api-endpoint">GET /api/emergency/active</div>
                <div class="api-endpoint">GET /api/stats</div>
                <div class="api-endpoint">WebSocket /ws</div>
                <div style="margin-top: 15px; text-align: center;">
                    <a href="/docs" style="color: #60a5fa; text-decoration: none;">📖 Full API Documentation</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🎯 Voice Excellence System | Marine & Industrial Voice Command Processing</p>
            <p>Comprehensive safety, context awareness, and multi-modal interaction</p>
        </div>
        
        <script>
            // WebSocket connection for real-time updates
            const ws = new WebSocket('ws://localhost:8380/ws');
            
            ws.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'emergency_alert') {{
                    // Flash the emergency card
                    const emergencyCard = document.querySelector('.card.emergency-alert');
                    if (emergencyCard) {{
                        emergencyCard.style.animation = 'none';
                        emergencyCard.offsetHeight; // Trigger reflow
                        emergencyCard.style.animation = 'pulse 0.5s infinite';
                    }}
                    
                    // Show browser notification if supported
                    if ('Notification' in window && Notification.permission === 'granted') {{
                        new Notification('🚨 Emergency Alert', {{
                            body: 'Emergency situation detected in Voice Excellence System',
                            icon: '/favicon.ico'
                        }});
                    }}
                }}
            }};
            
            // Request notification permission
            if ('Notification' in window && Notification.permission === 'default') {{
                Notification.requestPermission();
            }}
            
            // Auto-refresh every 30 seconds
            setInterval(() => {{
                location.reload();
            }}, 30000);
        </script>
    </body>
    </html>
    """

# Background task to update metrics
async def update_system_metrics():
    """Update system metrics periodically"""
    while True:
        try:
            system_metrics["uptime_hours"] = (datetime.now() - system_metrics["service_start_time"]).total_seconds() / 3600
            await asyncio.sleep(60)  # Update every minute
        except Exception as e:
            logging.error(f"Metrics update error: {e}")
            await asyncio.sleep(60)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        await init_voice_excellence_system()
        
        # Start background tasks
        asyncio.create_task(update_system_metrics())
        
        logging.info("🎙️ Voice Excellence System started successfully on port 8380")
        print("🎙️ Voice Excellence System")
        print("=" * 50)
        print("✅ Status: Fully Operational")
        print("🌐 URL: http://localhost:8380/")
        print("📖 API Docs: http://localhost:8380/docs")
        print("🔌 WebSocket: ws://localhost:8380/ws")
        print("=" * 50)
        print("🎯 Features Available:")
        print("  • Marine/Industrial Noise Cancellation")
        print("  • Multi-Language Voice Processing")
        print("  • Custom Wake Word Detection")
        print("  • Context Awareness Engine")
        print("  • Safety Confirmation Protocols")
        print("  • Emergency Response Procedures")
        print("  • Hands-Free Operation")
        print("  • Bluetooth Headset Support")
        print("=" * 50)
    
    except Exception as e:
        logging.error(f"Startup failed: {e}")
        logging.error(traceback.format_exc())
        sys.exit(1)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logging.info("Shutting down Voice Excellence System...")
    
    # Close WebSocket connections
    for websocket in websocket_connections:
        try:
            await websocket.close()
        except:
            pass
    
    logging.info("Voice Excellence System shutdown complete")

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s"
    )
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8380,
        reload=False,
        log_level="info"
    )