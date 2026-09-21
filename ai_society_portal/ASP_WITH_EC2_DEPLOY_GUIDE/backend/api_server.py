"""
AI Society Portal - FastAPI Backend
====================================
REST API and WebSocket server for the web portal
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime

from orchestration_engine import AISocietyOrchestrator, ConversationTurn
from room_system import RoomType
from character_system import CharacterState


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CreateCharacterRequest(BaseModel):
    name: str
    specialization: str
    backstory: str
    personality: Optional[Dict[str, float]] = None
    skills: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    storage_size_mb: Optional[int] = 100


class CreateRoomRequest(BaseModel):
    name: str
    room_type: str  # Will be converted to RoomType enum
    purpose: Optional[str] = ""
    max_characters: Optional[int] = 10
    conversation_pace_seconds: Optional[float] = 3.0
    objects_in_room: Optional[List[Dict[str, Any]]] = None
    background_media: Optional[List[Dict[str, Any]]] = None


class StartSessionRequest(BaseModel):
    duration_minutes: Optional[int] = None
    rounds: Optional[int] = None


class AddCharacterToRoomRequest(BaseModel):
    character_id: str
    room_id: str


class InjectMessageRequest(BaseModel):
    message: str
    sender: Optional[str] = "Moderator"


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="AI Society Portal API", version="1.0.0")

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = AISocietyOrchestrator()

# WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}


# ============================================================================
# CHARACTER ENDPOINTS
# ============================================================================

@app.post("/characters")
async def create_character(request: CreateCharacterRequest):
    """Create a new character"""
    try:
        character = orchestrator.create_character(
            name=request.name,
            specialization=request.specialization,
            backstory=request.backstory,
            personality=request.personality or {},
            skills=request.skills or [],
            current_goals=request.goals or []
        )
        
        # Set storage size
        if request.storage_size_mb:
            character.laptop.storage_size_mb = request.storage_size_mb
        
        orchestrator.character_manager.save_character(character)
        
        return {
            "id": character.id,
            "name": character.name,
            "specialization": character.specialization,
            "message": "Character created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters")
async def list_characters():
    """List all characters"""
    try:
        characters = orchestrator.character_manager.list_characters()
        return {"characters": characters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    """Get character details"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return character.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/work-at-home")
async def character_work_at_home(character_id: str, 
                                duration_minutes: int = 60,
                                background_tasks: BackgroundTasks = None):
    """Have character work at home"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Run in background
        if background_tasks:
            background_tasks.add_task(
                orchestrator.conversation_engine.character_work_at_home,
                character_id,
                duration_minutes
            )
            return {"message": "Character started working at home"}
        else:
            work_log = await orchestrator.conversation_engine.character_work_at_home(
                character_id, duration_minutes
            )
            return work_log
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROOM ENDPOINTS
# ============================================================================

@app.post("/rooms")
async def create_room(request: CreateRoomRequest):
    """Create a new room"""
    try:
        # Convert room_type string to enum
        try:
            room_type = RoomType(request.room_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid room_type. Must be one of: {[rt.value for rt in RoomType]}"
            )
        
        room = orchestrator.create_room(
            name=request.name,
            room_type=room_type,
            purpose=request.purpose,
            max_characters=request.max_characters,
            conversation_pace_seconds=request.conversation_pace_seconds
        )
        
        # Add objects and media if provided
        if request.objects_in_room:
            room.objects_in_room = request.objects_in_room
        if request.background_media:
            room.background_media = request.background_media
        
        orchestrator.room_manager.save_room(room)
        
        return {
            "id": room.id,
            "name": room.name,
            "room_type": room.room_type.value,
            "message": "Room created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rooms")
async def list_rooms():
    """List all rooms"""
    try:
        rooms = orchestrator.room_manager.list_rooms()
        return {"rooms": rooms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room details"""
    try:
        room = orchestrator.room_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        return room.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/add-character")
async def add_character_to_room(room_id: str, request: AddCharacterToRoomRequest):
    """Add a character to a room"""
    try:
        success = orchestrator.add_character_to_room(
            request.character_id,
            request.room_id
        )
        
        if success:
            return {"message": "Character added to room"}
        else:
            raise HTTPException(status_code=400, detail="Could not add character to room")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/start")
async def start_room_session(room_id: str, request: StartSessionRequest,
                            background_tasks: BackgroundTasks):
    """Start a conversation session in a room"""
    try:
        room = orchestrator.room_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Start session in background
        background_tasks.add_task(
            _run_room_session,
            room_id,
            request.duration_minutes,
            request.rounds
        )
        
        return {
            "message": "Room session started",
            "room_id": room_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_room_session(room_id: str, duration_minutes: Optional[int],
                            rounds: Optional[int]):
    """Background task to run room session"""
    try:
        result = await orchestrator.start_room_session(
            room_id=room_id,
            duration_minutes=duration_minutes,
            rounds=rounds
        )
        print(f"Session completed: {result['summary']}")
    except Exception as e:
        print(f"Error in room session: {e}")


@app.post("/rooms/{room_id}/pause")
async def pause_room(room_id: str):
    """Pause conversation in a room"""
    try:
        orchestrator.conversation_engine.pause_room(room_id)
        return {"message": "Room paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/resume")
async def resume_room(room_id: str):
    """Resume conversation in a room"""
    try:
        orchestrator.conversation_engine.resume_room(room_id)
        return {"message": "Room resumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/inject")
async def inject_message(room_id: str, request: InjectMessageRequest):
    """Inject a message into the room conversation"""
    try:
        orchestrator.conversation_engine.inject_message(
            room_id=room_id,
            message=request.message,
            sender=request.sender
        )
        return {"message": "Message injected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rooms/{room_id}/conversation")
async def get_room_conversation(room_id: str):
    """Get current conversation in a room"""
    try:
        if room_id in orchestrator.conversation_engine.active_conversations:
            conversation = orchestrator.conversation_engine.active_conversations[room_id]
            return {
                "room_id": room_id,
                "messages": [turn.__dict__ for turn in conversation]
            }
        else:
            return {
                "room_id": room_id,
                "messages": []
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET FOR LIVE ROOM STREAMING
# ============================================================================

@app.websocket("/ws/rooms/{room_id}")
async def websocket_room_stream(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for live room conversation streaming"""
    await websocket.accept()
    
    # Add to connections
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)
    
    # Callback for broadcasting messages
    def broadcast_turn(turn: ConversationTurn):
        asyncio.create_task(_broadcast_to_websocket(room_id, turn))
    
    # Subscribe to room
    orchestrator.subscribe_to_room(room_id, broadcast_turn)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Could handle commands from client here
            
    except WebSocketDisconnect:
        # Remove from connections
        active_connections[room_id].remove(websocket)
        if not active_connections[room_id]:
            del active_connections[room_id]


async def _broadcast_to_websocket(room_id: str, turn: ConversationTurn):
    """Broadcast turn to all websocket connections for a room"""
    if room_id not in active_connections:
        return
    
    message = json.dumps({
        "type": "conversation_turn",
        "character_id": turn.character_id,
        "character_name": turn.character_name,
        "content": turn.content,
        "timestamp": turn.timestamp.isoformat(),
        "laptop_activity": turn.laptop_activity,
        "tokens_used": turn.tokens_used
    })
    
    # Send to all connected clients
    disconnected = []
    for websocket in active_connections[room_id]:
        try:
            await websocket.send_text(message)
        except:
            disconnected.append(websocket)
    
    # Clean up disconnected clients
    for ws in disconnected:
        active_connections[room_id].remove(ws)


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "AI Society Portal API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/room-types")
async def get_room_types():
    """Get all available room types"""
    return {
        "room_types": [
            {
                "value": rt.value,
                "name": rt.value.replace("_", " ").title()
            }
            for rt in RoomType
        ]
    }


@app.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        characters = orchestrator.character_manager.list_characters()
        rooms = orchestrator.room_manager.list_rooms()
        
        return {
            "total_characters": len(characters),
            "total_rooms": len(rooms),
            "active_rooms": len([r for r in rooms if r.get("is_active")]),
            "active_conversations": len(orchestrator.conversation_engine.active_conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
