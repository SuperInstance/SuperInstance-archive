#!/usr/bin/env python3
"""
Hierarchical Task System - Main Server
Provides API for Claude bots to delegate tasks to local AI assistants
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import os

from claude_delegation_orchestrator import ClaudeDelegationOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Hierarchical Task System", version="1.0.0")

# Initialize orchestrator
orchestrator = ClaudeDelegationOrchestrator()

# Request/Response Models
class TaskDelegationRequest(BaseModel):
    task_description: str
    file_context: Optional[str] = None
    priority: int = 5  # 1-10 scale
    require_claude_review: bool = False

class TaskDelegationResponse(BaseModel):
    session_id: str
    estimated_subtasks: int
    execution_strategy: str
    estimated_time: int
    message: str

class SessionStatusResponse(BaseModel):
    session_id: str
    status: str  # 'running', 'completed', 'failed'
    progress: float  # 0-100%
    completed_subtasks: int
    total_subtasks: int
    current_subtask: Optional[str]
    quality_score: float
    lessons_learned: list

# Background task tracking
background_tasks: Dict[str, Dict] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    logger.info("🚀 Starting Hierarchical Task System")
    logger.info("✅ Claude Delegation Orchestrator initialized")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Hierarchical Task System",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(orchestrator.active_sessions),
        "background_tasks": len(background_tasks)
    }

@app.post("/delegate", response_model=TaskDelegationResponse)
async def delegate_task(request: TaskDelegationRequest, background_tasks_manager: BackgroundTasks):
    """Delegate a task to local AI assistants"""
    
    try:
        # First, break down the task to provide immediate feedback
        breakdown = orchestrator.breakdown_engine.breakdown_task(
            request.task_description, 
            request.file_context
        )
        
        # Create session ID
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start background execution
        background_tasks_manager.add_task(
            execute_delegation_background,
            session_id,
            request.task_description,
            request.file_context
        )
        
        # Track background task
        background_tasks[session_id] = {
            "status": "starting",
            "start_time": datetime.now(),
            "task_description": request.task_description
        }
        
        return TaskDelegationResponse(
            session_id=session_id,
            estimated_subtasks=len(breakdown.subtasks),
            execution_strategy=breakdown.execution_strategy,
            estimated_time=breakdown.total_estimated_time,
            message=f"Task delegation started. Monitor progress at /status/{session_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to start task delegation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def execute_delegation_background(session_id: str, task_description: str, file_context: Optional[str]):
    """Execute task delegation in the background"""
    
    try:
        background_tasks[session_id]["status"] = "running"
        
        # Execute the delegation
        session = await orchestrator.execute_delegated_task(task_description, file_context)
        
        # Update tracking
        background_tasks[session_id].update({
            "status": "completed",
            "end_time": datetime.now(),
            "session": session,
            "success": session.overall_success,
            "quality_score": session.quality_score
        })
        
        logger.info(f"✅ Background task {session_id} completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Background task {session_id} failed: {e}")
        background_tasks[session_id].update({
            "status": "failed",
            "end_time": datetime.now(),
            "error": str(e)
        })

@app.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """Get status of a delegation session"""
    
    if session_id not in background_tasks:
        raise HTTPException(status_code=404, detail="Session not found")
    
    task_info = background_tasks[session_id]
    
    # Basic status from background task tracker
    status = task_info["status"]
    
    if status == "completed" and "session" in task_info:
        session = task_info["session"]
        completed_subtasks = len(session.subtask_results)
        total_subtasks = len(session.breakdown.subtasks)
        progress = 100.0
        quality_score = session.quality_score
        lessons_learned = session.lessons_learned
        current_subtask = None
    elif status == "running":
        # Try to get progress from active session
        if session_id in orchestrator.active_sessions:
            session = orchestrator.active_sessions[session_id]
            completed_subtasks = len(session.subtask_results)
            total_subtasks = len(session.breakdown.subtasks)
            progress = (completed_subtasks / total_subtasks) * 100 if total_subtasks > 0 else 0
            quality_score = sum(r.quality_score for r in session.subtask_results.values()) / max(completed_subtasks, 1)
            lessons_learned = session.lessons_learned
            
            # Find current subtask
            remaining_subtasks = [st for st in session.breakdown.subtasks if st.id not in session.subtask_results]
            current_subtask = remaining_subtasks[0].description[:60] + "..." if remaining_subtasks else None
        else:
            completed_subtasks = 0
            total_subtasks = 0
            progress = 0
            quality_score = 0
            lessons_learned = []
            current_subtask = "Initializing..."
    else:  # failed or other
        completed_subtasks = 0
        total_subtasks = 0
        progress = 0
        quality_score = 0
        lessons_learned = [task_info.get("error", "Unknown error")]
        current_subtask = None
    
    return SessionStatusResponse(
        session_id=session_id,
        status=status,
        progress=progress,
        completed_subtasks=completed_subtasks,
        total_subtasks=total_subtasks,
        current_subtask=current_subtask,
        quality_score=quality_score,
        lessons_learned=lessons_learned
    )

@app.get("/report/{session_id}")
async def get_session_report(session_id: str):
    """Get detailed report for a completed session"""
    
    if session_id not in orchestrator.active_sessions and session_id not in background_tasks:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get report from orchestrator
    report = orchestrator.get_session_report(session_id)
    
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    
    return report

@app.get("/insights")
async def get_delegation_insights():
    """Get overall insights from all delegation sessions"""
    
    insights = orchestrator.get_delegation_insights()
    
    # Add prompt optimization insights
    prompt_insights = orchestrator.prompt_optimizer.get_optimization_insights()
    
    return {
        "delegation_insights": insights,
        "prompt_optimization_insights": prompt_insights,
        "system_status": {
            "active_sessions": len(orchestrator.active_sessions),
            "background_tasks": len(background_tasks),
            "available_assistants": len([a for a in orchestrator.delegator.assistant_manager.assistants if a.installation_status])
        }
    }

@app.get("/assistants")
async def get_available_assistants():
    """Get information about available local assistants"""
    
    assistants = orchestrator.delegator.assistant_manager.assistants
    
    return {
        "assistants": [
            {
                "name": a.name,
                "installed": a.installation_status,
                "supported_languages": a.supported_languages,
                "max_complexity": a.max_complexity,
                "strengths": a.strengths,
                "performance_rating": a.performance_rating
            }
            for a in assistants
        ],
        "installed_count": len([a for a in assistants if a.installation_status]),
        "total_count": len(assistants)
    }

@app.post("/test-delegation")
async def test_delegation():
    """Test the delegation system with a sample task"""
    
    test_task = "Add comprehensive error handling to a Python function that processes user input data"
    
    try:
        # Quick test without full background processing
        breakdown = orchestrator.breakdown_engine.breakdown_task(test_task)
        
        # Test first subtask delegation
        if breakdown.subtasks:
            first_subtask = breakdown.subtasks[0]
            result = await orchestrator.delegator.delegate_task(
                first_subtask.description,
                None,
                "def process_user_data(data):\n    return data.upper()"
            )
            
            return {
                "test_task": test_task,
                "breakdown_success": True,
                "subtask_count": len(breakdown.subtasks),
                "test_delegation_result": {
                    "success": result.success,
                    "assistant_used": result.assistant_used,
                    "quality_score": result.quality_score,
                    "output": result.output[:200] + "..." if len(result.output) > 200 else result.output
                }
            }
        else:
            return {
                "test_task": test_task,
                "breakdown_success": False,
                "error": "No subtasks generated"
            }
            
    except Exception as e:
        logger.error(f"Test delegation failed: {e}")
        return {
            "test_task": test_task,
            "breakdown_success": False,
            "error": str(e)
        }

@app.delete("/sessions/{session_id}")
async def cancel_session(session_id: str):
    """Cancel an active session"""
    
    if session_id in background_tasks:
        background_tasks[session_id]["status"] = "cancelled"
    
    if session_id in orchestrator.active_sessions:
        del orchestrator.active_sessions[session_id]
    
    return {"message": f"Session {session_id} cancelled"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    
    assistant_manager = orchestrator.delegator.assistant_manager
    installed_assistants = [a.name for a in assistant_manager.assistants if a.installation_status]
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "orchestrator": "operational",
            "breakdown_engine": "operational", 
            "prompt_optimizer": "operational",
            "delegation_controller": "operational"
        },
        "metrics": {
            "active_sessions": len(orchestrator.active_sessions),
            "background_tasks": len(background_tasks),
            "installed_assistants": len(installed_assistants),
            "available_assistants": installed_assistants
        }
    }

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8471)),
        log_level="info",
        reload=True
    )