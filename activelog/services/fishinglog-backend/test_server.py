#!/usr/bin/env python3
"""
FishingLog.ai Backend Service - Simplified Test Version
For testing the core fishing functionality
"""

import json
import uuid
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import uvicorn

# Ensure data directory exists
Path('data').mkdir(exist_ok=True)

# Data Models
class FishingCatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "test-user"
    title: str
    content: str
    fish_type: str  # Required fishing field
    location: str   # Required for fishing
    weight: Optional[float] = None  # Weight in pounds/kg
    length: Optional[float] = None
    bait_used: Optional[str] = None
    technique: Optional[str] = None
    weather_conditions: Optional[str] = None
    catch_released: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('fish_type')
    def validate_fish_type(cls, v):
        return v.strip().title()
    
    @validator('location')
    def validate_location(cls, v):
        return v.strip()

class FishingLogBackend:
    """Simplified FishingLog backend for testing"""
    
    def __init__(self):
        self.db_path = Path("data/fishinglog_test.db")
        self.init_database()
    
    def init_database(self):
        """Initialize simple SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_catches (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                fish_type TEXT NOT NULL,
                location TEXT NOT NULL,
                weight REAL,
                length REAL,
                bait_used TEXT,
                technique TEXT,
                weather_conditions TEXT,
                catch_released BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ FishingLog test database initialized")
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_catch(self, catch: FishingCatch) -> FishingCatch:
        """Create new fishing catch entry"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fishing_catches (
                id, user_id, title, content, fish_type, location, weight, length,
                bait_used, technique, weather_conditions, catch_released, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            catch.id, catch.user_id, catch.title, catch.content, catch.fish_type,
            catch.location, catch.weight, catch.length, catch.bait_used, catch.technique,
            catch.weather_conditions, catch.catch_released, catch.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        print(f"🎣 Created catch: {catch.title} - Fish: {catch.fish_type} at {catch.location}")
        return catch
    
    def get_catches(self, user_id: str = "test-user", limit: int = 50) -> List[Dict]:
        """Get fishing catches"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM fishing_catches 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        catches = []
        for row in cursor.fetchall():
            catches.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'fish_type': row['fish_type'],
                'location': row['location'],
                'weight': row['weight'],
                'length': row['length'],
                'bait_used': row['bait_used'],
                'technique': row['technique'],
                'weather_conditions': row['weather_conditions'],
                'catch_released': bool(row['catch_released']),
                'created_at': row['created_at']
            })
        
        conn.close()
        return catches

# Initialize backend
backend = FishingLogBackend()

# FastAPI app
app = FastAPI(
    title="FishingLog.ai Test Backend",
    description="Simplified fishing log backend for testing",
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

# API Endpoints
@app.post("/api/catches")
async def create_catch(catch: FishingCatch):
    """Create new fishing catch entry"""
    return backend.create_catch(catch)

@app.get("/api/catches")
async def get_catches(limit: int = 50):
    """Get fishing catch entries"""
    catches = backend.get_catches(limit=limit)
    return {"catches": catches, "total": len(catches)}

@app.get("/api/catches/{catch_id}")
async def get_catch(catch_id: str):
    """Get specific fishing catch"""
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM fishing_catches WHERE id = ?', (catch_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Catch not found")
    
    return {
        'id': row['id'],
        'title': row['title'],
        'content': row['content'],
        'fish_type': row['fish_type'],
        'location': row['location'],
        'weight': row['weight'],
        'length': row['length'],
        'bait_used': row['bait_used'],
        'technique': row['technique'],
        'weather_conditions': row['weather_conditions'],
        'catch_released': bool(row['catch_released']),
        'created_at': row['created_at']
    }

@app.get("/api/species")
async def get_fish_species():
    """Get list of common fish species"""
    species = [
        {"name": "Bass", "category": "Freshwater Sport Fish"},
        {"name": "Trout", "category": "Freshwater Game Fish"},
        {"name": "Salmon", "category": "Anadromous Game Fish"},
        {"name": "Pike", "category": "Predator Fish"},
        {"name": "Walleye", "category": "Freshwater Game Fish"},
        {"name": "Catfish", "category": "Freshwater Fish"},
        {"name": "Bluegill", "category": "Panfish"},
        {"name": "Perch", "category": "Freshwater Fish"}
    ]
    return {"species": species}

@app.get("/api/analytics")
async def get_fishing_analytics():
    """Get basic fishing analytics"""
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    # Get basic stats
    cursor.execute('''
        SELECT 
            COUNT(*) as total_catches,
            COUNT(DISTINCT fish_type) as species_count,
            COUNT(DISTINCT location) as locations_count,
            AVG(weight) as avg_weight,
            MAX(weight) as max_weight
        FROM fishing_catches
    ''')
    
    stats = cursor.fetchone()
    
    # Get top species
    cursor.execute('''
        SELECT fish_type, COUNT(*) as count
        FROM fishing_catches 
        GROUP BY fish_type
        ORDER BY count DESC
        LIMIT 5
    ''')
    
    top_species = [{"fish_type": row['fish_type'], "count": row['count']} for row in cursor.fetchall()]
    
    # Get top locations
    cursor.execute('''
        SELECT location, COUNT(*) as count
        FROM fishing_catches 
        GROUP BY location
        ORDER BY count DESC
        LIMIT 5
    ''')
    
    top_locations = [{"location": row['location'], "count": row['count']} for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "summary": {
            "total_catches": stats['total_catches'] or 0,
            "species_count": stats['species_count'] or 0,
            "locations_count": stats['locations_count'] or 0,
            "avg_weight": round(stats['avg_weight'] or 0, 2),
            "max_weight": stats['max_weight'] or 0
        },
        "top_species": top_species,
        "top_locations": top_locations
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "FishingLog.ai Test Backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Fishing catch logging",
            "Fish type tracking", 
            "Location recording",
            "Weight measurements",
            "Basic analytics"
        ]
    }

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": "FishingLog.ai Test Backend",
        "version": "1.0.0",
        "description": "Simplified fishing log backend for testing",
        "endpoints": {
            "create_catch": "POST /api/catches",
            "get_catches": "GET /api/catches",
            "get_catch": "GET /api/catches/{id}",
            "species": "GET /api/species",
            "analytics": "GET /api/analytics",
            "health": "GET /api/health"
        }
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FishingLog.ai Test Backend")
    parser.add_argument("--port", type=int, default=8001, help="Port to run on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    print("🚀 Starting FishingLog.ai Test Backend")
    print(f"🎣 Fishing catch tracking and analytics")
    print(f"🐟 Fish type and location logging")
    print(f"📊 Basic fishing analytics")
    print(f"🌐 Running on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "test_server:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=True
    )