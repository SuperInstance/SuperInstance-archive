#!/usr/bin/env python3
"""
Claude Task Hierarchy Service - Main API Server
Intelligent delegation between Claude model tiers (Opus, Sonnet, Haiku) with cost optimization
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

from intelligent_claude_delegator import IntelligentClaudeDelegator, TaskAnalysis, DelegationPlan

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Claude Task Hierarchy Service", version="1.0.0")

# Initialize delegator
delegator = IntelligentClaudeDelegator()

# Request/Response Models
class TaskDelegationRequest(BaseModel):
    task_description: str
    context: Optional[str] = None
    max_cost: Optional[float] = None
    time_priority: str = "medium"  # 'low', 'medium', 'high'
    quality_requirement: int = 8  # 1-10 scale

class ModelRecommendationRequest(BaseModel):
    task_description: str
    context: Optional[str] = None
    cost_constraint: Optional[float] = None

class DelegationPlanResponse(BaseModel):
    plan_id: str
    primary_model: str
    subtask_count: int
    estimated_cost: float
    estimated_time: int
    quality_expectation: float
    task_breakdown: list

class ExecutionStatusResponse(BaseModel):
    plan_id: str
    status: str
    progress: float
    completed_subtasks: int
    total_subtasks: int
    current_subtask: Optional[str]
    total_cost: float
    quality_score: float

# Background execution tracking
active_executions: Dict[str, Dict] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🧠 Starting Claude Task Hierarchy Service")
    logger.info("✅ Intelligent Claude Delegator initialized")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Claude Task Hierarchy Service",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "active_plans": len(active_executions),
        "total_cost_tracked": delegator.cost_tracker["total_cost"]
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    
    cost_analysis = delegator.get_cost_analysis()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "model_manager": "operational",
            "task_analyzer": "operational",
            "delegator": "operational"
        },
        "metrics": {
            "total_delegations": len(delegator.delegation_history),
            "total_cost": delegator.cost_tracker["total_cost"],
            "total_tokens": delegator.cost_tracker["tokens_used"],
            "active_executions": len(active_executions)
        },
        "model_availability": {
            model_name: "available" for model_name in delegator.model_manager.models.keys()
        }
    }

@app.post("/analyze", response_model=Dict)
async def analyze_task(request: ModelRecommendationRequest):
    """Analyze task complexity and get model recommendations"""
    
    try:
        recommendations = delegator.get_model_recommendations(
            request.task_description,
            request.context
        )
        
        # Apply cost constraint if provided
        if request.cost_constraint:
            filtered_recommendations = [
                rec for rec in recommendations["recommendations"] 
                if rec["estimated_cost"] <= request.cost_constraint
            ]
            
            if filtered_recommendations:
                recommendations["recommendations"] = filtered_recommendations
                recommendations["top_choice"] = filtered_recommendations[0]
                recommendations["cost_constraint_applied"] = request.cost_constraint
            else:
                recommendations["warning"] = f"No models meet cost constraint of ${request.cost_constraint:.4f}"
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to analyze task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plan", response_model=DelegationPlanResponse)
async def create_delegation_plan(request: TaskDelegationRequest):
    """Create intelligent delegation plan"""
    
    try:
        # Create delegation plan
        plan = delegator.create_delegation_plan(
            request.task_description,
            request.context,
            request.max_cost
        )
        
        # Generate unique plan ID
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"
        
        # Store plan for execution
        active_executions[plan_id] = {
            "plan": plan,
            "request": request,
            "created_at": datetime.now(),
            "status": "planned"
        }
        
        return DelegationPlanResponse(
            plan_id=plan_id,
            primary_model=plan.primary_model,
            subtask_count=len(plan.task_breakdown),
            estimated_cost=plan.estimated_total_cost,
            estimated_time=plan.estimated_completion_time,
            quality_expectation=plan.quality_expectation,
            task_breakdown=[
                {
                    "id": subtask["id"],
                    "description": subtask["description"][:100] + "..." if len(subtask["description"]) > 100 else subtask["description"],
                    "model": subtask["assigned_model"],
                    "complexity": subtask["complexity"],
                    "estimated_cost": subtask["estimated_cost"]
                }
                for subtask in plan.task_breakdown
            ]
        )
        
    except Exception as e:
        logger.error(f"Failed to create delegation plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute/{plan_id}")
async def execute_delegation_plan(plan_id: str, background_tasks: BackgroundTasks):
    """Execute a delegation plan"""
    
    if plan_id not in active_executions:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    execution_data = active_executions[plan_id]
    
    if execution_data["status"] != "planned":
        raise HTTPException(status_code=400, detail=f"Plan already {execution_data['status']}")
    
    # Start background execution
    background_tasks.add_task(execute_plan_background, plan_id)
    
    # Update status
    execution_data["status"] = "executing"
    execution_data["started_at"] = datetime.now()
    
    return {
        "message": f"Plan {plan_id} execution started",
        "plan_id": plan_id,
        "estimated_completion": datetime.now().isoformat(),
        "monitor_endpoint": f"/status/{plan_id}"
    }

async def execute_plan_background(plan_id: str):
    """Execute delegation plan in background"""
    
    try:
        execution_data = active_executions[plan_id]
        plan = execution_data["plan"]
        
        logger.info(f"🚀 Starting background execution of plan {plan_id}")
        
        # Execute the plan
        results = await delegator.execute_delegation_plan(plan)
        
        # Update execution data
        execution_data.update({
            "status": "completed",
            "results": results,
            "completed_at": datetime.now()
        })
        
        logger.info(f"✅ Plan {plan_id} completed - Quality: {results['overall_quality']:.1f}/10")
        
    except Exception as e:
        logger.error(f"❌ Plan {plan_id} execution failed: {e}")
        execution_data.update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now()
        })

@app.get("/status/{plan_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(plan_id: str):
    """Get execution status of a plan"""
    
    if plan_id not in active_executions:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    execution_data = active_executions[plan_id]
    plan = execution_data["plan"]
    
    if execution_data["status"] == "completed":
        results = execution_data["results"]
        completed_subtasks = len(results["subtask_results"])
        total_subtasks = len(plan.task_breakdown)
        progress = 100.0
        quality_score = results.get("overall_quality", 0.0)
        total_cost = results.get("actual_cost", 0.0)
        current_subtask = None
        
    elif execution_data["status"] == "executing":
        # Simulate progress tracking (in real implementation, would track actual progress)
        time_elapsed = (datetime.now() - execution_data["started_at"]).total_seconds()
        estimated_duration = plan.estimated_completion_time
        progress = min((time_elapsed / max(estimated_duration, 1)) * 100, 95.0)  # Cap at 95% until complete
        
        completed_subtasks = int((progress / 100) * len(plan.task_breakdown))
        total_subtasks = len(plan.task_breakdown)
        quality_score = 0.0  # Won't know until complete
        total_cost = 0.0  # Won't know until complete
        
        # Current subtask simulation
        if completed_subtasks < len(plan.task_breakdown):
            current_subtask = plan.task_breakdown[completed_subtasks]["description"][:60] + "..."
        else:
            current_subtask = "Finalizing results..."
        
    else:  # planned, failed
        completed_subtasks = 0
        total_subtasks = len(plan.task_breakdown)
        progress = 0.0
        quality_score = 0.0
        total_cost = 0.0
        current_subtask = None
    
    return ExecutionStatusResponse(
        plan_id=plan_id,
        status=execution_data["status"],
        progress=progress,
        completed_subtasks=completed_subtasks,
        total_subtasks=total_subtasks,
        current_subtask=current_subtask,
        total_cost=total_cost,
        quality_score=quality_score
    )

@app.get("/results/{plan_id}")
async def get_execution_results(plan_id: str):
    """Get detailed execution results"""
    
    if plan_id not in active_executions:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    execution_data = active_executions[plan_id]
    
    if execution_data["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Plan is {execution_data['status']}, not completed")
    
    results = execution_data["results"]
    plan = execution_data["plan"]
    
    # Prepare detailed results
    detailed_results = {
        "plan_id": plan_id,
        "execution_summary": {
            "status": "completed",
            "overall_quality": results["overall_quality"],
            "total_cost": results["actual_cost"],
            "total_tokens": results["total_tokens_used"],
            "execution_time": (results["execution_end"] - results["execution_start"]).total_seconds(),
            "cost_efficiency": results["cost_efficiency"]
        },
        "task_breakdown_results": [
            {
                "subtask_id": subtask["id"],
                "description": subtask["description"],
                "assigned_model": subtask["assigned_model"],
                "planned_cost": subtask["estimated_cost"],
                "actual_results": results["subtask_results"].get(subtask["id"], {})
            }
            for subtask in plan.task_breakdown
        ],
        "model_usage": {},
        "cost_breakdown": {},
        "quality_analysis": {
            "average_quality": results["overall_quality"],
            "quality_by_model": {},
            "quality_distribution": results["quality_scores"]
        }
    }
    
    # Calculate model usage and cost breakdown
    for subtask_id, subtask_result in results["subtask_results"].items():
        model = subtask_result["model_used"]
        
        # Model usage tracking
        if model not in detailed_results["model_usage"]:
            detailed_results["model_usage"][model] = {"count": 0, "total_tokens": 0, "total_cost": 0.0}
        
        detailed_results["model_usage"][model]["count"] += 1
        detailed_results["model_usage"][model]["total_tokens"] += subtask_result["tokens_used"]
        detailed_results["model_usage"][model]["total_cost"] += subtask_result["cost"]
        
        # Quality by model
        if model not in detailed_results["quality_analysis"]["quality_by_model"]:
            detailed_results["quality_analysis"]["quality_by_model"][model] = []
        detailed_results["quality_analysis"]["quality_by_model"][model].append(subtask_result["quality_score"])
    
    # Calculate averages for quality by model
    for model in detailed_results["quality_analysis"]["quality_by_model"]:
        scores = detailed_results["quality_analysis"]["quality_by_model"][model]
        detailed_results["quality_analysis"]["quality_by_model"][model] = sum(scores) / len(scores)
    
    return detailed_results

@app.get("/models")
async def get_available_models():
    """Get information about available Claude models"""
    
    models_info = {}
    for name, model in delegator.model_manager.models.items():
        models_info[name] = {
            "name": model.name,
            "model_id": model.model_id,
            "capabilities": model.capabilities,
            "cost_per_token": model.cost_per_token,
            "max_context": model.max_context,
            "reasoning_strength": model.reasoning_strength,
            "speed": model.speed,
            "best_for": model.best_for
        }
    
    return {
        "available_models": models_info,
        "model_count": len(models_info),
        "cost_range": {
            "min": min(m.cost_per_token for m in delegator.model_manager.models.values()),
            "max": max(m.cost_per_token for m in delegator.model_manager.models.values())
        }
    }

@app.get("/analytics")
async def get_delegation_analytics():
    """Get delegation analytics and insights"""
    
    cost_analysis = delegator.get_cost_analysis()
    
    # Additional analytics
    if delegator.delegation_history:
        recent_plans = delegator.delegation_history[-10:]  # Last 10 plans
        
        success_rate = len([p for p in recent_plans if p["results"]["overall_quality"] >= 7.0]) / len(recent_plans)
        avg_cost_per_plan = sum(p["results"]["actual_cost"] for p in recent_plans) / len(recent_plans)
        
        # Model efficiency analysis
        model_efficiency = {}
        for plan_data in recent_plans:
            for subtask_id, result in plan_data["results"]["subtask_results"].items():
                model = result["model_used"]
                if model not in model_efficiency:
                    model_efficiency[model] = {"total_quality": 0, "total_cost": 0, "count": 0}
                
                model_efficiency[model]["total_quality"] += result["quality_score"]
                model_efficiency[model]["total_cost"] += result["cost"]
                model_efficiency[model]["count"] += 1
        
        # Calculate efficiency ratios
        for model in model_efficiency:
            stats = model_efficiency[model]
            avg_quality = stats["total_quality"] / stats["count"]
            avg_cost = stats["total_cost"] / stats["count"]
            stats["efficiency_ratio"] = (avg_quality / 10) / max(avg_cost, 0.001)  # Quality per cost
            stats["avg_quality"] = avg_quality
            stats["avg_cost"] = avg_cost
    else:
        success_rate = 0
        avg_cost_per_plan = 0
        model_efficiency = {}
    
    return {
        "cost_analysis": cost_analysis,
        "performance_metrics": {
            "success_rate": success_rate,
            "average_cost_per_plan": avg_cost_per_plan,
            "total_active_executions": len(active_executions)
        },
        "model_efficiency": model_efficiency,
        "recommendations": [
            "Use Haiku for simple formatting and basic tasks",
            "Use Sonnet for implementation and analysis work", 
            "Reserve Opus for architecture and complex reasoning",
            "Consider breaking down complex tasks for cost efficiency"
        ]
    }

@app.post("/optimize/{plan_id}")
async def optimize_existing_plan(plan_id: str, cost_constraint: Optional[float] = None):
    """Optimize an existing plan for cost or performance"""
    
    if plan_id not in active_executions:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    execution_data = active_executions[plan_id]
    
    if execution_data["status"] not in ["planned", "failed"]:
        raise HTTPException(status_code=400, detail="Can only optimize planned or failed plans")
    
    original_plan = execution_data["plan"]
    original_request = execution_data["request"]
    
    # Create optimized plan
    optimized_plan = delegator.create_delegation_plan(
        original_request.task_description,
        original_request.context,
        cost_constraint or original_request.max_cost
    )
    
    # Compare plans
    comparison = {
        "original_plan": {
            "cost": original_plan.estimated_total_cost,
            "time": original_plan.estimated_completion_time,
            "quality": original_plan.quality_expectation,
            "subtasks": len(original_plan.task_breakdown)
        },
        "optimized_plan": {
            "cost": optimized_plan.estimated_total_cost,
            "time": optimized_plan.estimated_completion_time,
            "quality": optimized_plan.quality_expectation,
            "subtasks": len(optimized_plan.task_breakdown)
        },
        "improvements": {
            "cost_savings": original_plan.estimated_total_cost - optimized_plan.estimated_total_cost,
            "time_difference": original_plan.estimated_completion_time - optimized_plan.estimated_completion_time,
            "quality_difference": optimized_plan.quality_expectation - original_plan.quality_expectation
        }
    }
    
    # Update execution data with optimized plan
    execution_data["plan"] = optimized_plan
    execution_data["status"] = "planned"
    execution_data["optimized_at"] = datetime.now()
    
    return {
        "message": f"Plan {plan_id} optimized",
        "comparison": comparison,
        "new_plan_ready": True
    }

@app.delete("/plans/{plan_id}")
async def cancel_plan(plan_id: str):
    """Cancel a plan execution"""
    
    if plan_id not in active_executions:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    execution_data = active_executions[plan_id]
    
    if execution_data["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel completed plan")
    
    # Update status
    execution_data["status"] = "cancelled"
    execution_data["cancelled_at"] = datetime.now()
    
    return {
        "message": f"Plan {plan_id} cancelled",
        "plan_id": plan_id,
        "cancelled_at": datetime.now().isoformat()
    }

@app.get("/dashboard")
async def get_dashboard_summary():
    """Get dashboard summary for monitoring"""
    
    active_count = len([e for e in active_executions.values() if e["status"] == "executing"])
    completed_count = len([e for e in active_executions.values() if e["status"] == "completed"])
    failed_count = len([e for e in active_executions.values() if e["status"] == "failed"])
    
    return {
        "timestamp": datetime.now().isoformat(),
        "execution_summary": {
            "active_executions": active_count,
            "completed_plans": completed_count,
            "failed_plans": failed_count,
            "success_rate": completed_count / max(completed_count + failed_count, 1) * 100
        },
        "cost_tracking": delegator.cost_tracker,
        "model_availability": {name: "available" for name in delegator.model_manager.models.keys()},
        "recent_activity": [
            {
                "plan_id": plan_id,
                "status": data["status"],
                "created_at": data["created_at"].isoformat(),
                "model": data["plan"].primary_model
            }
            for plan_id, data in list(active_executions.items())[-5:]
        ]
    }

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8474))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )