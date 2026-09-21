#!/usr/bin/env python3
"""
DMLog Mobile Backend Server - Simplified Version
FastAPI server optimized for mobile DMLog app running on EC2
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import json
import sqlite3
import logging
import os
from datetime import datetime
import uuid
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
DATABASE_PATH = "/tmp/dmlog_mobile_simple.db"

# Pydantic models
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

class VoiceCommand(BaseModel):
    command_text: str
    user_id: str
    confidence: float

# FastAPI app
app = FastAPI(
    title="DMLog Mobile Backend",
    description="Mobile backend for DMLog Revolutionary",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization
def init_database():
    """Initialize database"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            device_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            character_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            class_name TEXT NOT NULL,
            race TEXT NOT NULL,
            level INTEGER DEFAULT 1,
            stats_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            command_text TEXT NOT NULL,
            confidence REAL DEFAULT 0.0,
            response TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

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
            INSERT INTO users (user_id, username, device_id)
            VALUES (?, ?, ?)
        """, (user.user_id, user.username, user.device_id))
        
        conn.commit()
        return {"success": True, "user_id": user.user_id}
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="User already registered")
    finally:
        conn.close()

@app.get("/characters/{user_id}")
async def get_characters(user_id: str):
    """Get user's characters"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT character_id, name, class_name, race, level, stats_json
        FROM characters
        WHERE user_id = ?
    """, (user_id,))
    
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
            "stats": json.loads(row[5])
        }
        characters.append(character)
    
    return {"characters": characters}

@app.post("/characters")
async def create_character(character: Character):
    """Create new character"""
    character_id = character.character_id or str(uuid.uuid4())
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Default user_id for testing
    user_id = "test-user-001"
    
    cursor.execute("""
        INSERT INTO characters 
        (character_id, user_id, name, class_name, race, level, stats_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        character_id,
        user_id,
        character.name,
        character.class_name,
        character.race,
        character.level,
        json.dumps(character.stats)
    ))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "character_id": character_id}

@app.post("/voice/command")
async def process_voice_command(command: VoiceCommand):
    """Process voice command"""
    
    # Simple command processing
    command_lower = command.command_text.lower()
    
    if "roll" in command_lower and "dice" in command_lower:
        import random
        roll = random.randint(1, 20)
        response = f"Rolling d20... You got a {roll}!"
    elif "create" in command_lower and "character" in command_lower:
        response = "Opening character creation screen..."
    elif "show" in command_lower and "character" in command_lower:
        response = "Displaying character sheet..."
    elif "spell" in command_lower:
        response = "Accessing spell list..."
    else:
        response = f"I heard: '{command.command_text}'. How can I help with your D&D game?"
    
    # Log command
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO voice_commands (user_id, command_text, confidence, response)
        VALUES (?, ?, ?, ?)
    """, (command.user_id, command.command_text, command.confidence, response))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "response": response}

@app.get("/dice/roll/{sides}")
async def roll_dice(sides: int, count: int = 1):
    """Roll dice endpoint"""
    import random
    
    results = [random.randint(1, sides) for _ in range(count)]
    total = sum(results)
    
    return {
        "dice": f"{count}d{sides}",
        "results": results,
        "total": total
    }

@app.get("/spells/search")
async def search_spells(query: str = "", level: Optional[int] = None):
    """Search D&D spells"""
    spells = [
        {"name": "Fireball", "level": 3, "school": "Evocation", "damage": "8d6", "range": "150 feet"},
        {"name": "Magic Missile", "level": 1, "school": "Evocation", "damage": "1d4+1", "range": "120 feet"},
        {"name": "Healing Word", "level": 1, "school": "Evocation", "healing": "1d4+mod", "range": "60 feet"},
        {"name": "Shield", "level": 1, "school": "Abjuration", "ac_bonus": "+5 AC", "range": "Self"},
        {"name": "Counterspell", "level": 3, "school": "Abjuration", "effect": "Counter spell", "range": "60 feet"},
        {"name": "Cure Wounds", "level": 1, "school": "Evocation", "healing": "1d8+mod", "range": "Touch"},
        {"name": "Eldritch Blast", "level": 0, "school": "Evocation", "damage": "1d10", "range": "120 feet"},
        {"name": "Mage Hand", "level": 0, "school": "Transmutation", "effect": "Telekinetic hand", "range": "30 feet"}
    ]
    
    # Filter spells
    filtered_spells = []
    for spell in spells:
        if query.lower() in spell["name"].lower() or query == "":
            if level is None or spell["level"] == level:
                filtered_spells.append(spell)
    
    return {"spells": filtered_spells, "count": len(filtered_spells)}

@app.get("/stats")
async def get_stats():
    """Get server stats"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM characters")
    character_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM voice_commands")
    command_count = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        "users": user_count,
        "characters": character_count,
        "voice_commands": command_count,
        "server_uptime": "Running",
        "database": DATABASE_PATH
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8099))
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False
    )