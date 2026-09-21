#!/usr/bin/env python3
"""
ActiveWorkLog Coordination System

A distributed coordination system for the Building Bots Network that enables bots to:
- Register ongoing work to prevent conflicts
- Check for existing work before starting tasks
- Maintain continuity when bots are interrupted
- Coordinate resource allocation and task handoffs
- Provide visibility into network-wide bot activities

Features:
1. Work Registration - Bots declare what they're working on
2. Conflict Prevention - Automatic detection of overlapping work
3. Continuity Handoffs - Seamless task transfers between bots
4. Resource Coordination - Prevent conflicts over files/services
5. Network Visibility - Real-time view of all bot activities
"""

import json
import time
import sqlite3
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/services/activeworklog/coordination.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class WorkEntry:
    """Represents an active work entry in the system"""
    work_id: str
    bot_name: str
    task_description: str
    resources: List[str]  # Files, services, APIs being used
    priority: int  # 1-10, higher is more important
    started_at: datetime
    last_heartbeat: datetime
    estimated_completion: Optional[datetime]
    progress_percentage: float
    status: str  # 'active', 'paused', 'completing', 'blocked'
    metadata: Dict[str, Any]
    dependencies: List[str]  # Other work_ids this depends on
    can_be_shared: bool  # Whether multiple bots can work on this
    checkpoint_data: Dict[str, Any]  # Data needed for continuity

class WorkRegistrationModel(BaseModel):
    bot_name: str
    task_description: str
    resources: List[str] = []
    priority: int = 5
    estimated_duration_minutes: Optional[int] = None
    dependencies: List[str] = []
    can_be_shared: bool = False
    metadata: Dict[str, Any] = {}

class WorkUpdateModel(BaseModel):
    progress_percentage: Optional[float] = None
    status: Optional[str] = None
    estimated_completion: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    checkpoint_data: Optional[Dict[str, Any]] = None

class CoordinationConflict:
    """Represents a coordination conflict between work entries"""
    def __init__(self, work1: WorkEntry, work2: WorkEntry, conflict_type: str, severity: str):
        self.work1 = work1
        self.work2 = work2
        self.conflict_type = conflict_type  # 'resource', 'dependency', 'overlap'
        self.severity = severity  # 'critical', 'warning', 'info'
        self.detected_at = datetime.now()

class ActiveWorkLogSystem:
    """Core coordination system for the Building Bots Network"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/activeworklog/coordination.db"
        self.active_work: Dict[str, WorkEntry] = {}
        self.conflict_history: List[CoordinationConflict] = []
        self.heartbeat_timeout = 300  # 5 minutes
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_database()
        self._load_active_work()
        
        # Start background tasks
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("🤖 ActiveWorkLog Coordination System initialized")
        logger.info(f"📊 Loaded {len(self.active_work)} active work entries")
    
    def _init_database(self):
        """Initialize the coordination database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS work_entries (
                    work_id TEXT PRIMARY KEY,
                    bot_name TEXT NOT NULL,
                    task_description TEXT NOT NULL,
                    resources TEXT,  -- JSON array
                    priority INTEGER,
                    started_at TIMESTAMP,
                    last_heartbeat TIMESTAMP,
                    estimated_completion TIMESTAMP,
                    progress_percentage REAL,
                    status TEXT,
                    metadata TEXT,  -- JSON object
                    dependencies TEXT,  -- JSON array
                    can_be_shared BOOLEAN,
                    checkpoint_data TEXT  -- JSON object
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conflict_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    work1_id TEXT,
                    work2_id TEXT,
                    conflict_type TEXT,
                    severity TEXT,
                    detected_at TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolution_notes TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS coordination_metrics (
                    timestamp TIMESTAMP,
                    metric_name TEXT,
                    metric_value REAL,
                    context TEXT
                )
            """)
            
            conn.commit()
    
    def _load_active_work(self):
        """Load active work entries from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM work_entries WHERE status IN ('active', 'paused', 'blocked')
            """)
            
            for row in cursor.fetchall():
                work_entry = WorkEntry(
                    work_id=row[0],
                    bot_name=row[1],
                    task_description=row[2],
                    resources=json.loads(row[3]) if row[3] else [],
                    priority=row[4],
                    started_at=datetime.fromisoformat(row[5]),
                    last_heartbeat=datetime.fromisoformat(row[6]),
                    estimated_completion=datetime.fromisoformat(row[7]) if row[7] else None,
                    progress_percentage=row[8],
                    status=row[9],
                    metadata=json.loads(row[10]) if row[10] else {},
                    dependencies=json.loads(row[11]) if row[11] else [],
                    can_be_shared=bool(row[12]),
                    checkpoint_data=json.loads(row[13]) if row[13] else {}
                )
                self.active_work[work_entry.work_id] = work_entry
    
    def _generate_work_id(self, bot_name: str, task_description: str) -> str:
        """Generate unique work ID"""
        content = f"{bot_name}_{task_description}_{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _detect_conflicts(self, new_work: WorkEntry) -> List[CoordinationConflict]:
        """Detect potential conflicts with existing work"""
        conflicts = []
        
        for existing_work in self.active_work.values():
            if existing_work.work_id == new_work.work_id:
                continue
            
            # Resource conflicts
            overlapping_resources = set(new_work.resources) & set(existing_work.resources)
            if overlapping_resources and not (new_work.can_be_shared and existing_work.can_be_shared):
                conflict = CoordinationConflict(
                    new_work, existing_work, 'resource', 
                    'critical' if existing_work.priority >= 8 else 'warning'
                )
                conflicts.append(conflict)
            
            # Dependency conflicts
            if existing_work.work_id in new_work.dependencies and existing_work.status != 'active':
                conflict = CoordinationConflict(
                    new_work, existing_work, 'dependency', 'critical'
                )
                conflicts.append(conflict)
            
            # Task overlap detection (similar descriptions)
            similarity = self._calculate_task_similarity(
                new_work.task_description, existing_work.task_description
            )
            if similarity > 0.8:
                conflict = CoordinationConflict(
                    new_work, existing_work, 'overlap', 'info'
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _calculate_task_similarity(self, task1: str, task2: str) -> float:
        """Calculate similarity between two task descriptions"""
        words1 = set(task1.lower().split())
        words2 = set(task2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union
    
    def register_work(self, registration: WorkRegistrationModel) -> Dict[str, Any]:
        """Register new work with the coordination system"""
        work_id = self._generate_work_id(registration.bot_name, registration.task_description)
        
        # Calculate estimated completion
        estimated_completion = None
        if registration.estimated_duration_minutes:
            estimated_completion = datetime.now() + timedelta(minutes=registration.estimated_duration_minutes)
        
        work_entry = WorkEntry(
            work_id=work_id,
            bot_name=registration.bot_name,
            task_description=registration.task_description,
            resources=registration.resources,
            priority=registration.priority,
            started_at=datetime.now(),
            last_heartbeat=datetime.now(),
            estimated_completion=estimated_completion,
            progress_percentage=0.0,
            status='active',
            metadata=registration.metadata,
            dependencies=registration.dependencies,
            can_be_shared=registration.can_be_shared,
            checkpoint_data={}
        )
        
        # Detect conflicts
        conflicts = self._detect_conflicts(work_entry)
        
        # Log conflicts
        for conflict in conflicts:
            self._log_conflict(conflict)
        
        # Store in database
        self._save_work_entry(work_entry)
        
        # Add to active work
        self.active_work[work_id] = work_entry
        
        logger.info(f"🔄 Work registered: {work_id} by {registration.bot_name}")
        logger.info(f"📝 Task: {registration.task_description}")
        
        if conflicts:
            logger.warning(f"⚠️ {len(conflicts)} conflicts detected for work {work_id}")
        
        return {
            "work_id": work_id,
            "status": "registered",
            "conflicts": [
                {
                    "type": c.conflict_type,
                    "severity": c.severity,
                    "conflicting_work": c.work2.work_id,
                    "conflicting_bot": c.work2.bot_name
                } for c in conflicts
            ],
            "can_proceed": len([c for c in conflicts if c.severity == 'critical']) == 0
        }
    
    def update_work(self, work_id: str, update: WorkUpdateModel) -> Dict[str, Any]:
        """Update existing work entry"""
        if work_id not in self.active_work:
            raise HTTPException(status_code=404, detail="Work not found")
        
        work_entry = self.active_work[work_id]
        work_entry.last_heartbeat = datetime.now()
        
        # Update fields
        if update.progress_percentage is not None:
            work_entry.progress_percentage = min(100.0, max(0.0, update.progress_percentage))
        
        if update.status:
            work_entry.status = update.status
        
        if update.estimated_completion:
            work_entry.estimated_completion = datetime.fromisoformat(update.estimated_completion)
        
        if update.metadata:
            work_entry.metadata.update(update.metadata)
        
        if update.checkpoint_data:
            work_entry.checkpoint_data.update(update.checkpoint_data)
        
        # Save to database
        self._save_work_entry(work_entry)
        
        logger.info(f"📊 Work updated: {work_id} - {work_entry.progress_percentage:.1f}% complete")
        
        return {
            "work_id": work_id,
            "status": "updated",
            "progress": work_entry.progress_percentage,
            "last_heartbeat": work_entry.last_heartbeat.isoformat()
        }
    
    def complete_work(self, work_id: str, completion_notes: str = "") -> Dict[str, Any]:
        """Mark work as completed"""
        if work_id not in self.active_work:
            raise HTTPException(status_code=404, detail="Work not found")
        
        work_entry = self.active_work[work_id]
        work_entry.status = 'completed'
        work_entry.progress_percentage = 100.0
        work_entry.last_heartbeat = datetime.now()
        work_entry.metadata['completion_notes'] = completion_notes
        work_entry.metadata['completed_at'] = datetime.now().isoformat()
        
        # Save to database
        self._save_work_entry(work_entry)
        
        # Remove from active work
        del self.active_work[work_id]
        
        logger.info(f"✅ Work completed: {work_id} by {work_entry.bot_name}")
        
        return {
            "work_id": work_id,
            "status": "completed",
            "completion_time": datetime.now().isoformat()
        }
    
    def request_handoff(self, work_id: str, new_bot_name: str, reason: str = "") -> Dict[str, Any]:
        """Request handoff of work to another bot"""
        if work_id not in self.active_work:
            raise HTTPException(status_code=404, detail="Work not found")
        
        work_entry = self.active_work[work_id]
        
        # Create handoff record
        handoff_data = {
            "original_bot": work_entry.bot_name,
            "new_bot": new_bot_name,
            "handoff_time": datetime.now().isoformat(),
            "reason": reason,
            "progress_at_handoff": work_entry.progress_percentage,
            "checkpoint_data": work_entry.checkpoint_data
        }
        
        # Update work entry
        work_entry.bot_name = new_bot_name
        work_entry.last_heartbeat = datetime.now()
        work_entry.metadata['handoff_history'] = work_entry.metadata.get('handoff_history', [])
        work_entry.metadata['handoff_history'].append(handoff_data)
        
        # Save to database
        self._save_work_entry(work_entry)
        
        logger.info(f"🔄 Work handed off: {work_id} from {handoff_data['original_bot']} to {new_bot_name}")
        
        return {
            "work_id": work_id,
            "status": "handed_off",
            "new_bot": new_bot_name,
            "checkpoint_data": work_entry.checkpoint_data
        }
    
    def get_active_work(self, bot_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active work, optionally filtered by bot"""
        work_list = []
        
        for work in self.active_work.values():
            if bot_name and work.bot_name != bot_name:
                continue
                
            work_list.append({
                "work_id": work.work_id,
                "bot_name": work.bot_name,
                "task_description": work.task_description,
                "resources": work.resources,
                "priority": work.priority,
                "status": work.status,
                "progress_percentage": work.progress_percentage,
                "started_at": work.started_at.isoformat(),
                "last_heartbeat": work.last_heartbeat.isoformat(),
                "estimated_completion": work.estimated_completion.isoformat() if work.estimated_completion else None,
                "can_be_shared": work.can_be_shared,
                "dependencies": work.dependencies
            })
        
        return sorted(work_list, key=lambda x: x['priority'], reverse=True)
    
    def check_resource_availability(self, resources: List[str]) -> Dict[str, Any]:
        """Check if resources are available for use"""
        conflicts = {}
        available_resources = []
        
        for resource in resources:
            conflicting_work = []
            
            for work in self.active_work.values():
                if resource in work.resources and not work.can_be_shared:
                    conflicting_work.append({
                        "work_id": work.work_id,
                        "bot_name": work.bot_name,
                        "priority": work.priority,
                        "estimated_completion": work.estimated_completion.isoformat() if work.estimated_completion else None
                    })
            
            if conflicting_work:
                conflicts[resource] = conflicting_work
            else:
                available_resources.append(resource)
        
        return {
            "available_resources": available_resources,
            "resource_conflicts": conflicts,
            "all_available": len(conflicts) == 0
        }
    
    def get_network_status(self) -> Dict[str, Any]:
        """Get overall network status and statistics"""
        active_bots = set(work.bot_name for work in self.active_work.values())
        
        status_counts = {}
        priority_counts = {}
        
        for work in self.active_work.values():
            status_counts[work.status] = status_counts.get(work.status, 0) + 1
            priority_counts[work.priority] = priority_counts.get(work.priority, 0) + 1
        
        # Calculate network health
        total_work = len(self.active_work)
        stalled_work = len([w for w in self.active_work.values() 
                          if (datetime.now() - w.last_heartbeat).seconds > self.heartbeat_timeout])
        
        network_health = max(0.0, 1.0 - (stalled_work / max(1, total_work)))
        
        return {
            "active_work_count": total_work,
            "active_bot_count": len(active_bots),
            "active_bots": list(active_bots),
            "status_distribution": status_counts,
            "priority_distribution": priority_counts,
            "stalled_work_count": stalled_work,
            "network_health_score": network_health,
            "conflicts_detected_today": len([c for c in self.conflict_history 
                                           if c.detected_at.date() == datetime.now().date()]),
            "timestamp": datetime.now().isoformat()
        }
    
    def _save_work_entry(self, work: WorkEntry):
        """Save work entry to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO work_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                work.work_id,
                work.bot_name,
                work.task_description,
                json.dumps(work.resources),
                work.priority,
                work.started_at.isoformat(),
                work.last_heartbeat.isoformat(),
                work.estimated_completion.isoformat() if work.estimated_completion else None,
                work.progress_percentage,
                work.status,
                json.dumps(work.metadata),
                json.dumps(work.dependencies),
                work.can_be_shared,
                json.dumps(work.checkpoint_data)
            ))
            conn.commit()
    
    def _log_conflict(self, conflict: CoordinationConflict):
        """Log conflict to database"""
        self.conflict_history.append(conflict)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO conflict_log (work1_id, work2_id, conflict_type, severity, detected_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                conflict.work1.work_id,
                conflict.work2.work_id,
                conflict.conflict_type,
                conflict.severity,
                conflict.detected_at.isoformat()
            ))
            conn.commit()
    
    def _cleanup_worker(self):
        """Background worker to clean up stale work entries"""
        while True:
            try:
                current_time = datetime.now()
                stale_work = []
                
                for work_id, work in self.active_work.items():
                    time_since_heartbeat = (current_time - work.last_heartbeat).seconds
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        stale_work.append(work_id)
                
                # Mark stale work as abandoned
                for work_id in stale_work:
                    work = self.active_work[work_id]
                    work.status = 'abandoned'
                    work.metadata['abandoned_at'] = current_time.isoformat()
                    work.metadata['abandonment_reason'] = 'heartbeat_timeout'
                    
                    self._save_work_entry(work)
                    del self.active_work[work_id]
                    
                    logger.warning(f"🚨 Work abandoned due to timeout: {work_id} by {work.bot_name}")
                
                # Record metrics
                if len(self.active_work) > 0:
                    with sqlite3.connect(self.db_path) as conn:
                        conn.execute("""
                            INSERT INTO coordination_metrics VALUES (?, ?, ?, ?)
                        """, (current_time.isoformat(), 'active_work_count', len(self.active_work), ''))
                        conn.commit()
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in cleanup worker: {e}")
                time.sleep(30)

# Initialize the coordination system
coordination_system = ActiveWorkLogSystem()

# FastAPI application
app = FastAPI(title="ActiveWorkLog Coordination System", version="1.0.0")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "system": "ActiveWorkLog Coordination System",
        "active_work_count": len(coordination_system.active_work),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/work/register")
async def register_work(registration: WorkRegistrationModel):
    """Register new work with the coordination system"""
    try:
        result = coordination_system.register_work(registration)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error registering work: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/work/{work_id}")
async def update_work(work_id: str, update: WorkUpdateModel):
    """Update existing work entry"""
    try:
        result = coordination_system.update_work(work_id, update)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating work: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/work/{work_id}/complete")
async def complete_work(work_id: str, completion_notes: str = ""):
    """Mark work as completed"""
    try:
        result = coordination_system.complete_work(work_id, completion_notes)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing work: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/work/{work_id}/handoff")
async def request_handoff(work_id: str, new_bot_name: str, reason: str = ""):
    """Request handoff of work to another bot"""
    try:
        result = coordination_system.request_handoff(work_id, new_bot_name, reason)
        return JSONResponse(content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/work/active")
async def get_active_work(bot_name: Optional[str] = None):
    """Get all active work, optionally filtered by bot"""
    try:
        result = coordination_system.get_active_work(bot_name)
        return JSONResponse(content={"active_work": result})
    except Exception as e:
        logger.error(f"Error getting active work: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resources/check")
async def check_resource_availability(resources: List[str]):
    """Check if resources are available for use"""
    try:
        result = coordination_system.check_resource_availability(resources)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error checking resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/network/status")
async def get_network_status():
    """Get overall network status and statistics"""
    try:
        result = coordination_system.get_network_status()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error getting network status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/work/{work_id}")
async def get_work_details(work_id: str):
    """Get detailed information about specific work"""
    if work_id not in coordination_system.active_work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    work = coordination_system.active_work[work_id]
    return JSONResponse(content={
        "work_id": work.work_id,
        "bot_name": work.bot_name,
        "task_description": work.task_description,
        "resources": work.resources,
        "priority": work.priority,
        "status": work.status,
        "progress_percentage": work.progress_percentage,
        "started_at": work.started_at.isoformat(),
        "last_heartbeat": work.last_heartbeat.isoformat(),
        "estimated_completion": work.estimated_completion.isoformat() if work.estimated_completion else None,
        "metadata": work.metadata,
        "dependencies": work.dependencies,
        "can_be_shared": work.can_be_shared,
        "checkpoint_data": work.checkpoint_data
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8480))
    
    logger.info("🤖 Starting ActiveWorkLog Coordination System")
    logger.info("🌐 Building Bots Network Coordination Hub")
    logger.info(f"📡 Starting server on port {port}")
    logger.info("")
    logger.info("🎯 Core Features:")
    logger.info("   ✓ Work registration and conflict detection")
    logger.info("   ✓ Bot coordination and resource management")
    logger.info("   ✓ Task continuity and handoff support")
    logger.info("   ✓ Network-wide visibility and monitoring")
    logger.info("")
    
    uvicorn.run(app, host="0.0.0.0", port=port)