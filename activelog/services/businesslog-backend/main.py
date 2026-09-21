#!/usr/bin/env python3
"""
BusinessLog.ai Backend Service - SuperInstance.AI Domain
Production-ready backend for enterprise logging and analytics
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import sqlite3
from pathlib import Path

app = FastAPI(
    title="BusinessLog.ai Backend",
    description="Enterprise logging and analytics platform",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Database setup
DB_PATH = Path(__file__).parent / "businesslog.db"

def init_db():
    """Initialize the BusinessLog database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Business entries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS business_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            company_id TEXT,
            entry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT,
            tags TEXT,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Analytics data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            metric_value REAL,
            metric_data TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Companies table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            industry TEXT,
            settings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("BusinessLog.ai backend initialized")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "businesslog-backend",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": "operational"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "BusinessLog.ai Backend",
        "version": "2.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "entries": "/entries",
            "analytics": "/analytics",
            "companies": "/companies"
        }
    }

@app.get("/entries")
async def get_entries(user_id: str, company_id: Optional[str] = None, limit: int = 100):
    """Get business entries for a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT * FROM business_entries WHERE user_id = ?"
    params = [user_id]
    
    if company_id:
        query += " AND company_id = ?"
        params.append(company_id)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    entries = cursor.fetchall()
    conn.close()
    
    # Convert to dict format
    columns = ['id', 'user_id', 'company_id', 'entry_type', 'title', 'content', 
               'metadata', 'tags', 'priority', 'status', 'created_at', 'updated_at']
    
    result = []
    for entry in entries:
        entry_dict = dict(zip(columns, entry))
        # Parse JSON fields
        if entry_dict['metadata']:
            entry_dict['metadata'] = json.loads(entry_dict['metadata'])
        if entry_dict['tags']:
            entry_dict['tags'] = entry_dict['tags'].split(',')
        result.append(entry_dict)
    
    return {"entries": result, "count": len(result)}

@app.post("/entries")
async def create_entry(entry_data: Dict[str, Any]):
    """Create a new business entry"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Validate required fields
    required_fields = ['user_id', 'entry_type', 'title', 'content']
    for field in required_fields:
        if field not in entry_data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Prepare data
    metadata = json.dumps(entry_data.get('metadata', {}))
    tags = ','.join(entry_data.get('tags', []))
    
    cursor.execute("""
        INSERT INTO business_entries (user_id, company_id, entry_type, title, content, metadata, tags, priority)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry_data['user_id'],
        entry_data.get('company_id'),
        entry_data['entry_type'],
        entry_data['title'],
        entry_data['content'],
        metadata,
        tags,
        entry_data.get('priority', 'medium')
    ))
    
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"success": True, "entry_id": entry_id}

@app.get("/analytics")
async def get_analytics(user_id: str, metric: Optional[str] = None):
    """Get analytics data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if metric:
        cursor.execute("""
            SELECT metric_name, metric_value, metric_data, timestamp 
            FROM analytics_data 
            WHERE user_id = ? AND metric_name = ?
            ORDER BY timestamp DESC LIMIT 100
        """, (user_id, metric))
    else:
        cursor.execute("""
            SELECT metric_name, AVG(metric_value) as avg_value, COUNT(*) as count
            FROM analytics_data 
            WHERE user_id = ?
            GROUP BY metric_name
        """, (user_id,))
    
    data = cursor.fetchall()
    conn.close()
    
    if metric:
        columns = ['metric_name', 'value', 'data', 'timestamp']
        result = [dict(zip(columns, row)) for row in data]
    else:
        columns = ['metric_name', 'average_value', 'count']
        result = [dict(zip(columns, row)) for row in data]
    
    return {"analytics": result}

@app.post("/analytics")
async def record_analytics(analytics_data: Dict[str, Any]):
    """Record analytics data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO analytics_data (user_id, metric_name, metric_value, metric_data)
        VALUES (?, ?, ?, ?)
    """, (
        analytics_data.get('user_id'),
        analytics_data.get('metric_name'),
        analytics_data.get('metric_value'),
        json.dumps(analytics_data.get('metric_data', {}))
    ))
    
    conn.commit()
    conn.close()
    
    return {"success": True}

@app.get("/companies/{company_id}")
async def get_company(company_id: str):
    """Get company information"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
    company = cursor.fetchone()
    conn.close()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    columns = ['id', 'name', 'industry', 'settings', 'created_at']
    company_dict = dict(zip(columns, company))
    
    if company_dict['settings']:
        company_dict['settings'] = json.loads(company_dict['settings'])
    
    return company_dict

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8400))
    print(f"Starting BusinessLog.ai backend on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)