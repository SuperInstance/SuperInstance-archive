# src/orchestrator/api_server.py
"""
FastAPI Server for Content Studio V2
Provides REST API endpoints for the enhanced parallel orchestrator
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio

from .orchestrator_v2 import ContentStudioOrchestrator

# Create FastAPI app
app = FastAPI(
    title="Loopless Content Studio API",
    description="Multi-Agent Parallel Content Production System",
    version="2.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator: Optional[ContentStudioOrchestrator] = None
active_websockets = []


# Request/Response Models
class UserRequest(BaseModel):
    message: str
    user_id: str = "default"


class StatusResponse(BaseModel):
    status: str
    details: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize the orchestrator on startup"""
    global orchestrator

    print("\n" + "="*70)
    print("🚀 Starting FastAPI Server")
    print("="*70 + "\n")

    orchestrator = ContentStudioOrchestrator()
    await orchestrator.initialize()

    print("\n" + "="*70)
    print("✅ FastAPI Server Ready")
    print("="*70 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\n🛑 Shutting down FastAPI server...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Loopless Content Studio",
        "version": "2.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "status": "/api/status",
            "request": "POST /api/request",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "orchestrator": "initialized" if orchestrator else "not_initialized"
    }


@app.get("/api/status")
async def get_status():
    """Get comprehensive system status"""
    if not orchestrator:
        return {"error": "Orchestrator not initialized"}

    status = orchestrator.get_status()
    return status


@app.post("/api/request")
async def handle_request(request: UserRequest):
    """
    Handle user request

    Example:
    {
        "message": "Create Episode 1 for YouTube",
        "user_id": "casey"
    }
    """
    if not orchestrator:
        return {"error": "Orchestrator not initialized"}

    print(f"\n📨 API Request received from user: {request.user_id}")
    print(f"Message: {request.message}\n")

    try:
        result = await orchestrator.process_user_request(
            request.message,
            request.user_id
        )

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        print(f"❌ Error processing request: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/agents")
async def get_agents():
    """Get list of all agents and their status"""
    if not orchestrator:
        return {"error": "Orchestrator not initialized"}

    agents = {}
    for bot_id, bot in orchestrator.bots.items():
        agents[bot_id] = bot.get_status()

    return {"agents": agents}


@app.get("/api/foreman")
async def get_foreman_status():
    """Get Foreman status"""
    if not orchestrator or not orchestrator.foreman:
        return {"error": "Foreman not initialized"}

    return orchestrator.foreman.get_status()


@app.get("/api/resources")
async def get_resources():
    """Get resource manager status"""
    if not orchestrator:
        return {"error": "Orchestrator not initialized"}

    return orchestrator.resource_manager.get_status()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    active_websockets.append(websocket)

    try:
        while True:
            # Send status updates every 5 seconds
            if orchestrator:
                status = orchestrator.get_status()
                await websocket.send_json(status)

            await asyncio.sleep(5)

    except WebSocketDisconnect:
        active_websockets.remove(websocket)
        print("WebSocket client disconnected")


# For running with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
