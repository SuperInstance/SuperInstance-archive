#!/usr/bin/env python3
"""
Smart Task API - RESTful interface for intelligent task management
Provides endpoints for bots to submit and process tasks optimally
"""

import asyncio
import logging
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from task_intelligence import TaskIntelligenceClassifier, SmartTaskQueue, ModelTier
from smart_bot_integration import SmartBotRouter, SuperInstanceSmartBotManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/smart-task-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class TaskSubmissionRequest(BaseModel):
    description: str = Field(..., description="Task description")
    context: str = Field(default="", description="Additional context")
    priority: str = Field(default="MEDIUM", description="Task priority: LOW, MEDIUM, HIGH, CRITICAL")
    files: List[str] = Field(default_factory=list, description="Related files")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    user_id: str = Field(default="api", description="User/bot submitting task")

class BatchTaskRequest(BaseModel):
    tasks: List[TaskSubmissionRequest] = Field(..., description="List of tasks to process")
    optimize_distribution: bool = Field(default=True, description="Optimize task distribution across models")

class ModelPreferenceRequest(BaseModel):
    preferred_model: str = Field(..., description="Preferred model tier: haiku, sonnet, opus")
    override_analysis: bool = Field(default=False, description="Override intelligent analysis")

class TaskQueryRequest(BaseModel):
    complexity: Optional[str] = Field(default=None, description="Filter by complexity")
    model: Optional[str] = Field(default=None, description="Filter by recommended model")
    priority: Optional[str] = Field(default=None, description="Filter by priority")
    status: Optional[str] = Field(default="pending", description="Filter by status")
    limit: int = Field(default=20, description="Maximum number of tasks to return")

# Global manager instance
smart_manager = None

app = FastAPI(
    title="SuperInstance Smart Task API",
    description="Intelligent task management with automatic model selection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    global smart_manager
    
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    orchestrator_url = os.getenv("BOT_ORCHESTRATOR_URL", "http://localhost:8450")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable required")
        
    smart_manager = SuperInstanceSmartBotManager(
        anthropic_api_key=anthropic_api_key,
        orchestrator_url=orchestrator_url,
        redis_url=redis_url
    )
    
    await smart_manager.start_smart_processing()
    logger.info("Smart Task API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    global smart_manager
    if smart_manager:
        await smart_manager.smart_router.stop()
    logger.info("Smart Task API stopped")

@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "smart_manager_active": smart_manager is not None
    }

@app.post("/tasks/submit")
async def submit_task(request: TaskSubmissionRequest):
    """Submit a single task for intelligent processing"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        result = await smart_manager.smart_router.submit_smart_task(
            description=request.description,
            context=request.context,
            priority=request.priority,
            files=request.files,
            user_id=request.user_id
        )
        
        return {
            "status": "success",
            "task_id": result["task_id"],
            "analysis": result["analysis"],
            "optimization": result["optimization_summary"],
            "execution": {
                "status": result["execution_result"]["status"],
                "model_used": result["execution_result"].get("model_used"),
                "cost": result["execution_result"].get("actual_cost", 0.0),
                "execution_time": result["execution_result"].get("execution_time", 0.0)
            }
        }
        
    except Exception as e:
        logger.error(f"Task submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/batch")
async def submit_batch_tasks(request: BatchTaskRequest):
    """Submit multiple tasks for batch processing with optimization"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        # Convert Pydantic models to dicts for processing
        tasks = [task.dict() for task in request.tasks]
        
        results = await smart_manager.smart_router.process_batch_tasks(tasks)
        
        # Calculate batch summary
        total_cost = sum(r["result"].get("actual_cost", r["analysis"]["estimated_cost"]) 
                        for r in results)
        model_distribution = {}
        
        for result in results:
            model = result["analysis"]["recommended_model"]
            model_distribution[model] = model_distribution.get(model, 0) + 1
            
        return {
            "status": "success",
            "batch_summary": {
                "total_tasks": len(results),
                "total_cost": total_cost,
                "average_cost_per_task": total_cost / len(results) if results else 0,
                "model_distribution": model_distribution
            },
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Batch task submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/query")
async def query_tasks(
    complexity: Optional[str] = None,
    model: Optional[str] = None,
    priority: Optional[str] = None,
    status: str = "pending",
    limit: int = 20
):
    """Query tasks with filters"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        tasks = []
        
        for task_id, task in smart_manager.smart_router.task_queue.tasks.items():
            # Apply filters
            if status and task.get("status") != status:
                continue
                
            analysis = task["analysis"]
            
            if complexity and analysis["complexity"] != complexity:
                continue
                
            if model and analysis["recommended_model"] != model:
                continue
                
            if priority and task.get("priority") != priority:
                continue
                
            tasks.append({
                "task_id": task_id,
                "description": task["description"][:100] + "..." if len(task["description"]) > 100 else task["description"],
                "priority": task.get("priority", "MEDIUM"),
                "status": task.get("status", "pending"),
                "analysis": {
                    "complexity": analysis["complexity"],
                    "recommended_model": analysis["recommended_model"],
                    "estimated_cost": analysis["estimated_cost"],
                    "confidence": analysis["confidence"]
                },
                "created_at": task.get("created_at"),
                "execution_time": task.get("execution_time", 0)
            })
            
            if len(tasks) >= limit:
                break
                
        return {
            "status": "success",
            "tasks": tasks,
            "total_found": len(tasks)
        }
        
    except Exception as e:
        logger.error(f"Task query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_details(task_id: str):
    """Get detailed information about a specific task"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        task = smart_manager.smart_router.task_queue.tasks.get(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return {
            "status": "success",
            "task": task
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get task details failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/capabilities")
async def get_model_capabilities():
    """Get information about available Claude models and their capabilities"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        capabilities = smart_manager.smart_router.classifier.get_model_stats()
        
        return {
            "status": "success",
            "models": capabilities
        }
        
    except Exception as e:
        logger.error(f"Get model capabilities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/performance/report")
async def get_performance_report():
    """Get comprehensive performance and cost analysis"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        report = smart_manager.smart_router.get_performance_report()
        
        return {
            "status": "success",
            "report": report,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get performance report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status")
async def get_queue_status():
    """Get current task queue status and statistics"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        queue_summary = smart_manager.smart_router.task_queue.get_queue_summary()
        
        # Add real-time queue info
        pending_tasks = [task for task in smart_manager.smart_router.task_queue.tasks.values() 
                        if task["status"] == "pending"]
        active_tasks = [task for task in smart_manager.smart_router.task_queue.tasks.values() 
                       if task["status"] in ["processing", "executing"]]
        
        return {
            "status": "success",
            "queue_summary": queue_summary,
            "real_time_status": {
                "pending_tasks": len(pending_tasks),
                "active_tasks": len(active_tasks),
                "queue_health": "healthy" if len(pending_tasks) < 100 else "congested"
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Get queue status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/analyze")
async def analyze_task_without_execution(request: TaskSubmissionRequest):
    """Analyze task complexity and get model recommendation without executing"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        analysis = smart_manager.smart_router.classifier.analyze_task(
            task_description=request.description,
            context=request.context,
            priority=request.priority,
            files=request.files
        )
        
        # Calculate cost comparison across models
        model_comparison = {}
        for model_tier in ModelTier:
            from task_intelligence import MODEL_CONFIGS
            config = MODEL_CONFIGS[model_tier]
            
            estimated_cost = (
                (analysis.estimated_input_tokens / 1000) * config.cost_per_1k_input +
                (analysis.estimated_output_tokens / 1000) * config.cost_per_1k_output
            )
            
            model_comparison[model_tier.value] = {
                "estimated_cost": estimated_cost,
                "speed_factor": config.speed_factor,
                "capability_score": config.capability_score,
                "recommended": model_tier == analysis.recommended_model
            }
        
        return {
            "status": "success",
            "analysis": {
                "complexity": analysis.complexity.value,
                "recommended_model": analysis.recommended_model.value,
                "confidence": analysis.confidence,
                "reasoning": analysis.reasoning,
                "estimated_cost": analysis.estimated_cost,
                "estimated_input_tokens": analysis.estimated_input_tokens,
                "estimated_output_tokens": analysis.estimated_output_tokens,
                "task_categories": analysis.task_categories,
                "requires_reasoning": analysis.requires_reasoning,
                "requires_creativity": analysis.requires_creativity,
                "is_time_sensitive": analysis.is_time_sensitive
            },
            "model_comparison": model_comparison
        }
        
    except Exception as e:
        logger.error(f"Task analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks/force-model")
async def submit_task_with_forced_model(
    request: TaskSubmissionRequest,
    forced_model: str = "sonnet"
):
    """Submit task with forced model selection (bypassing intelligence)"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        # Validate forced model
        try:
            model_tier = ModelTier(forced_model.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid model: {forced_model}. Use: haiku, sonnet, opus")
        
        # Override the classifier temporarily
        original_select_model = smart_manager.smart_router.classifier._select_model
        
        def force_model_selection(*args, **kwargs):
            return model_tier, 1.0, f"Forced selection of {model_tier.value}"
            
        smart_manager.smart_router.classifier._select_model = force_model_selection
        
        try:
            result = await smart_manager.smart_router.submit_smart_task(
                description=request.description,
                context=request.context,
                priority=request.priority,
                files=request.files,
                user_id=request.user_id
            )
            
            return {
                "status": "success",
                "task_id": result["task_id"],
                "forced_model": forced_model,
                "analysis": result["analysis"],
                "execution": result["execution_result"]
            }
            
        finally:
            # Restore original selection method
            smart_manager.smart_router.classifier._select_model = original_select_model
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forced model task submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/optimal/{model}")
async def get_optimal_tasks_for_model(model: str, limit: int = 10):
    """Get tasks that are optimal for a specific model"""
    
    if not smart_manager:
        raise HTTPException(status_code=503, detail="Smart manager not initialized")
        
    try:
        # Validate model
        try:
            model_tier = ModelTier(model.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid model: {model}. Use: haiku, sonnet, opus")
            
        optimal_tasks = smart_manager.smart_router.task_queue.get_optimal_tasks_for_model(
            model_tier, limit
        )
        
        # Format for API response
        formatted_tasks = []
        for task in optimal_tasks:
            analysis = task["analysis"]
            formatted_tasks.append({
                "task_id": task["id"],
                "description": task["description"][:100] + "..." if len(task["description"]) > 100 else task["description"],
                "priority": task.get("priority", "MEDIUM"),
                "estimated_cost": analysis["estimated_cost"],
                "confidence": analysis["confidence"],
                "complexity": analysis["complexity"],
                "created_at": task.get("created_at")
            })
        
        return {
            "status": "success",
            "model": model,
            "optimal_tasks": formatted_tasks,
            "total_found": len(formatted_tasks)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get optimal tasks failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time task updates (optional advanced feature)
@app.websocket("/ws/task-updates")
async def task_updates_websocket(websocket):
    """WebSocket endpoint for real-time task status updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send periodic queue updates
            if smart_manager:
                queue_status = smart_manager.smart_router.task_queue.get_queue_summary()
                await websocket.send_json({
                    "type": "queue_update",
                    "data": queue_status,
                    "timestamp": datetime.now().isoformat()
                })
            
            await asyncio.sleep(10)  # Update every 10 seconds
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Task API Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8470, help="Port to bind to")
    parser.add_argument("--log-level", default="info", help="Log level")
    
    args = parser.parse_args()
    
    # Start server
    uvicorn.run(
        "task_api:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=False
    )