#!/usr/bin/env python3
"""
DMLog Mobile Backend Server
FastAPI server optimized for mobile DMLog app running on EC2

Provides all DMLog functionality through mobile-optimized APIs
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import asyncio
import json
import sqlite3
import logging
import os
from datetime import datetime, timedelta
import uuid
import hashlib
import jwt
from contextlib import asynccontextmanager
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "dmlog-mobile-secret-key-2025")

# Database setup
DATABASE_PATH = "/tmp/dmlog_mobile.db"

# Pydantic models for mobile API
class MobileUser(BaseModel):
    user_id: str
    username: str
    device_id: str
    app_version: str

class Character(BaseModel):
    character_id: Optional[str] = None
    name: str
    class_name: str
    race: str
    level: int
    stats: Dict[str, Any]
    equipment: List[Dict[str, Any]]
    spells: List[Dict[str, Any]]

class VoiceCommand(BaseModel):
    command_text: str
    user_id: str
    timestamp: str
    confidence: float

class BehaviorEvent(BaseModel):
    user_id: str
    event_type: str
    screen_name: str
    duration_ms: int
    metadata: Dict[str, Any]

class CampaignSession(BaseModel):
    session_id: Optional[str] = None
    campaign_name: str
    dm_user_id: str
    players: List[str]
    current_scene: Dict[str, Any]

# Connection manager for WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: str):
        self.active_connections.remove(websocket)
        if user_id in self.user_connections:
            del self.user_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# Initialize connection manager
manager = ConnectionManager()

# Database initialization
def init_mobile_database():
    """Initialize mobile-optimized database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Mobile users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            device_id TEXT UNIQUE NOT NULL,
            app_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            push_token TEXT
        )
    """)
    
    # Characters optimized for mobile
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_characters (
            character_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            race TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            stats_json TEXT NOT NULL,
            equipment_json TEXT DEFAULT '[]',
            spells_json TEXT DEFAULT '[]',
            appearance_data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES mobile_users (user_id)
        )
    """)
    
    # Mobile behavior tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_behavior_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            screen_name TEXT NOT NULL,
            duration_ms INTEGER DEFAULT 0,
            metadata_json TEXT DEFAULT '{}',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES mobile_users (user_id)
        )
    """)
    
    # Voice commands log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_voice_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            command_text TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            processed BOOLEAN DEFAULT FALSE,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES mobile_users (user_id)
        )
    """)
    
    # Campaign sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mobile_campaign_sessions (
            session_id TEXT PRIMARY KEY,
            campaign_name TEXT NOT NULL,
            dm_user_id TEXT NOT NULL,
            players_json TEXT DEFAULT '[]',
            current_scene_json TEXT DEFAULT '{}',
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dm_user_id) REFERENCES mobile_users (user_id)
        )
    """)
    
    conn.commit()
    conn.close()

# Startup event
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_mobile_database()
    logger.info("DMLog Mobile Backend started successfully")
    yield
    # Shutdown
    logger.info("DMLog Mobile Backend shutting down")

# FastAPI app
app = FastAPI(
    title="DMLog Mobile Backend",
    description="Mobile-optimized backend for DMLog Revolutionary D&D Beyond clone",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify mobile app domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication functions
def create_jwt_token(user_id: str, device_id: str) -> str:
    """Create JWT token for mobile authentication"""
    payload = {
        "user_id": user_id,
        "device_id": device_id,
        "exp": datetime.utcnow() + timedelta(days=30),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, str]:
    """Verify JWT token and return user info"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return {"user_id": payload["user_id"], "device_id": payload["device_id"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# API Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "DMLog Mobile Backend",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/auth/register")
async def register_user(user: MobileUser):
    """Register new mobile user"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO mobile_users (user_id, username, device_id, app_version)
            VALUES (?, ?, ?, ?)
        """, (user.user_id, user.username, user.device_id, user.app_version))
        
        conn.commit()
        
        # Create JWT token
        token = create_jwt_token(user.user_id, user.device_id)
        
        return {
            "success": True,
            "token": token,
            "user": user.dict()
        }
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User or device already registered")
    finally:
        conn.close()

@app.post("/auth/login")
async def login_user(device_id: str, username: str):
    """Login existing mobile user"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT user_id, username, device_id, app_version
        FROM mobile_users
        WHERE device_id = ? AND username = ?
    """, (device_id, username))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user_id, username, device_id, app_version = result
    token = create_jwt_token(user_id, device_id)
    
    return {
        "success": True,
        "token": token,
        "user": {
            "user_id": user_id,
            "username": username,
            "device_id": device_id,
            "app_version": app_version
        }
    }

@app.get("/characters")
async def get_characters(auth: Dict[str, str] = Depends(verify_jwt_token)):
    """Get user's characters"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT character_id, name, class_name, race, level, stats_json, 
               equipment_json, spells_json, appearance_data, updated_at
        FROM mobile_characters
        WHERE user_id = ?
        ORDER BY updated_at DESC
    """, (auth["user_id"],))
    
    results = cursor.fetchall()
    conn.close()
    
    characters = []
    for row in results:
        character = {
            "character_id": row[0],
            "name": row[1],
            "class_name": row[2],
            "race": row[3],
            "level": row[4],
            "stats": json.loads(row[5]),
            "equipment": json.loads(row[6]),
            "spells": json.loads(row[7]),
            "appearance": json.loads(row[8]),
            "updated_at": row[9]
        }
        characters.append(character)
    
    return {"characters": characters}

@app.post("/characters")
async def create_character(character: Character, auth: Dict[str, str] = Depends(verify_jwt_token)):
    """Create new character"""
    character_id = character.character_id or str(uuid.uuid4())
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO mobile_characters 
        (character_id, user_id, name, class_name, race, level, stats_json, equipment_json, spells_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        character_id,
        auth["user_id"],
        character.name,
        character.class_name,
        character.race,
        character.level,
        json.dumps(character.stats),
        json.dumps(character.equipment),
        json.dumps(character.spells)
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "character_id": character_id,
        "message": "Character created successfully"
    }

@app.post("/voice/command")
async def process_voice_command(command: VoiceCommand, auth: Dict[str, str] = Depends(verify_jwt_token)):
    """Process voice command from mobile app"""
    
    # Log voice command
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO mobile_voice_commands 
        (user_id, command_text, confidence, timestamp)
        VALUES (?, ?, ?, ?)
    """, (command.user_id, command.command_text, command.confidence, command.timestamp))
    
    command_id = cursor.lastrowid
    conn.commit()
    
    # Process command (simple keyword matching for now)
    response = process_simple_voice_command(command.command_text)
    
    # Update with response
    cursor.execute("""
        UPDATE mobile_voice_commands 
        SET processed = TRUE, response = ?
        WHERE id = ?
    """, (response, command_id))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "response": response,
        "command_id": command_id
    }

def process_simple_voice_command(command_text: str) -> str:
    """Simple voice command processing"""
    command_lower = command_text.lower()
    
    if "roll" in command_lower and "dice" in command_lower:
        return "Rolling dice... *rolls* You got a 15!"
    elif "create" in command_lower and "character" in command_lower:
        return "Opening character creation screen..."
    elif "show" in command_lower and ("character" in command_lower or "sheet" in command_lower):
        return "Displaying character sheet..."
    elif "spell" in command_lower:
        return "Accessing spell list..."
    elif "inventory" in command_lower or "equipment" in command_lower:
        return "Opening inventory..."
    else:
        return f"I heard: '{command_text}'. How can I help you with your D&D game?"

@app.post("/behavior/track")
async def track_behavior_event(event: BehaviorEvent, auth: Dict[str, str] = Depends(verify_jwt_token)):
    """Track user behavior for ML analysis"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO mobile_behavior_events 
        (user_id, event_type, screen_name, duration_ms, metadata_json)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event.user_id,
        event.event_type,
        event.screen_name,
        event.duration_ms,
        json.dumps(event.metadata)
    ))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "message": "Behavior event tracked"}

@app.get("/campaigns")
async def get_campaigns(auth: Dict[str, str] = Depends(verify_jwt_token)):
    """Get user's campaigns"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT session_id, campaign_name, dm_user_id, players_json, 
               current_scene_json, active, created_at
        FROM mobile_campaign_sessions
        WHERE dm_user_id = ? OR players_json LIKE ?
        ORDER BY updated_at DESC
    """, (auth["user_id"], f'%{auth["user_id"]}%'))
    
    results = cursor.fetchall()
    conn.close()
    
    campaigns = []
    for row in results:
        campaign = {
            "session_id": row[0],
            "campaign_name": row[1],
            "dm_user_id": row[2],
            "players": json.loads(row[3]),
            "current_scene": json.loads(row[4]),
            "active": bool(row[5]),
            "created_at": row[6]
        }
        campaigns.append(campaign)
    
    return {"campaigns": campaigns}

@app.post("/campaigns")
async def create_campaign(session: CampaignSession, auth: Dict[str, str] = Depends(verify_jwt_token)):
    """Create new campaign session"""
    session_id = session.session_id or str(uuid.uuid4())
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO mobile_campaign_sessions
        (session_id, campaign_name, dm_user_id, players_json, current_scene_json)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session_id,
        session.campaign_name,
        auth["user_id"],  # Current user is DM
        json.dumps(session.players),
        json.dumps(session.current_scene)
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "Campaign created successfully"
    }

# WebSocket endpoint for real-time features
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket connection for real-time updates"""
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data.get("type") == "dice_roll":
                # Broadcast dice roll to campaign members
                result = {
                    "type": "dice_result",
                    "user": user_id,
                    "result": message_data.get("result"),
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(json.dumps(result))
                
            elif message_data.get("type") == "character_update":
                # Notify other players of character changes
                update = {
                    "type": "character_updated",
                    "user": user_id,
                    "character": message_data.get("character"),
                    "timestamp": datetime.now().isoformat()
                }
                await manager.broadcast(json.dumps(update))
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# Additional utility endpoints
@app.get("/dice/roll/{sides}")
async def roll_dice(sides: int, count: int = 1):
    """Roll dice endpoint"""
    import random
    
    results = [random.randint(1, sides) for _ in range(count)]
    total = sum(results)
    
    return {
        "dice": f"{count}d{sides}",
        "results": results,
        "total": total,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/spells/search")
async def search_spells(query: str, level: Optional[int] = None):
    """Search D&D spells"""
    # Mock spell data - in production, integrate with D&D API
    spells = [
        {"name": "Fireball", "level": 3, "school": "Evocation", "damage": "8d6"},
        {"name": "Magic Missile", "level": 1, "school": "Evocation", "damage": "1d4+1"},
        {"name": "Healing Word", "level": 1, "school": "Evocation", "healing": "1d4+mod"},
        {"name": "Shield", "level": 1, "school": "Abjuration", "ac_bonus": 5},
        {"name": "Counterspell", "level": 3, "school": "Abjuration", "effect": "Counter spell"}
    ]
    
    # Filter by query and level
    filtered_spells = []
    for spell in spells:
        if query.lower() in spell["name"].lower():
            if level is None or spell["level"] == level:
                filtered_spells.append(spell)
    
    return {"spells": filtered_spells, "count": len(filtered_spells)}

if __name__ == "__main__":
    # Run server
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )