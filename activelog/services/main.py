from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

app = FastAPI(title="ActiveLog Metadata Service")

# Database connection
def get_db():
    return psycopg2.connect(
        host="localhost",
        database="activelog",
        user="activelog_admin",
        password="SecurePass123!",
        cursor_factory=RealDictCursor
    )

class FileMetadata(BaseModel):
    file_id: str
    filename: str
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    sync_state: str = "local_only"

@app.post("/metadata")
async def create_metadata(meta: FileMetadata):
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO files (id, local_path, sync_state, metadata)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET metadata = %s, updated_at = NOW()
        """, (
            meta.file_id,
            meta.filename,
            meta.sync_state,
            json.dumps(meta.metadata),
            json.dumps(meta.metadata)
        ))
        conn.commit()
        return {"message": "Metadata saved", "file_id": meta.file_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/metadata/{file_id}")
async def get_metadata(file_id: str):
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT * FROM files WHERE id = %s", (file_id,))
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        return result
    finally:
        cur.close()
        conn.close()

@app.get("/search")
async def search_files(tag: Optional[str] = None, sync_state: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    
    query = "SELECT * FROM files WHERE 1=1"
    params = []
    
    if sync_state:
        query += " AND sync_state = %s"
        params.append(sync_state)
    
    if tag:
        query += " AND metadata @> %s"
        params.append(json.dumps({"tags": [tag]}))
    
    try:
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/")
def root():
    return {"service": "Metadata Service", "status": "running"}
