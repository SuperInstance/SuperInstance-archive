#!/usr/bin/env python3
"""
OpenAI Integration Service - Main API Server
Intelligent OpenAI integration with user preference learning and cost optimization
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

from unified_model_orchestrator import UnifiedModelOrchestrator, TaskRequest, ExecutionResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="OpenAI Integration Service", version="1.0.0")

# Initialize orchestrator
orchestrator = UnifiedModelOrchestrator()

# Request/Response Models
class ModelExecutionRequest(BaseModel):
    task_description: str
    user_id: str = "default"
    context: Optional[str] = None
    user_initiated: bool = False
    priority: int = 5
    max_cost: Optional[float] = None
    preferred_provider: Optional[str] = None  # 'claude', 'openai', 'local'
    quality_requirement: int = 7
    speed_requirement: int = 5
    creativity_needed: bool = False
    multimodal_needed: bool = False

class UserFeedbackRequest(BaseModel):
    user_id: str
    provider: str
    model: str
    task_category: str = "general"
    satisfaction_score: float  # 1-10
    feedback_text: str = ""

class RecommendationRequest(BaseModel):
    task_description: str
    user_id: str = "default"
    user_initiated: bool = False

class EmergencyOverrideRequest(BaseModel):
    enabled: bool
    reason: str = ""

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🤖 Starting OpenAI Integration Service")
    logger.info("✅ Unified Model Orchestrator initialized")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "OpenAI Integration Service",
        "status": "operational", 
        "timestamp": datetime.now().isoformat(),
        "providers_available": list(orchestrator.providers.keys()),
        "total_executions": len(orchestrator.execution_history)
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    
    system_analytics = orchestrator.get_system_analytics()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "unified_orchestrator": "operational",
            "openai_manager": "operational",
            "provider_health": orchestrator.provider_health
        },
        "metrics": {
            "total_executions": system_analytics.get("total_executions", 0),
            "total_cost": system_analytics.get("total_cost", 0.0),
            "total_users": system_analytics.get("total_users", 0)
        },
        "openai_config": {
            "api_key_configured": bool(orchestrator.openai_manager.api_key),
            "rate_limiting_enabled": orchestrator.openai_manager.rate_limit_enforced,
            "emergency_override": orchestrator.openai_manager.emergency_override
        }
    }

@app.post("/execute")
async def execute_task(request: ModelExecutionRequest):
    """Execute task with intelligent model selection"""
    
    try:
        # Convert to internal task request
        task_request = TaskRequest(
            user_id=request.user_id,
            task_description=request.task_description,
            context=request.context,
            priority=request.priority,
            user_initiated=request.user_initiated,
            max_cost=request.max_cost,
            preferred_provider=request.preferred_provider,
            quality_requirement=request.quality_requirement,
            speed_requirement=request.speed_requirement,
            creativity_needed=request.creativity_needed,
            multimodal_needed=request.multimodal_needed
        )
        
        # Execute task
        result = await orchestrator.execute_task(task_request)
        
        return {
            "success": result.success,
            "provider_used": result.provider_used,
            "model_used": result.model_used,
            "content": result.content,
            "tokens_used": result.tokens_used,
            "cost": result.cost,
            "execution_time": result.execution_time,
            "quality_score": result.quality_score,
            "user_id": request.user_id,
            "task_completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommend")
async def get_recommendation(request: RecommendationRequest):
    """Get provider/model recommendation without executing"""
    
    try:
        recommendation = await orchestrator.get_recommendation(
            request.task_description,
            request.user_id,
            request.user_initiated
        )
        
        return recommendation
        
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(feedback: UserFeedbackRequest):
    """Submit user feedback to improve model selection"""
    
    try:
        orchestrator.learn_from_feedback(
            feedback.user_id,
            feedback.provider,
            feedback.model,
            feedback.task_category,
            feedback.satisfaction_score,
            feedback.feedback_text
        )
        
        return {
            "message": "Feedback recorded successfully",
            "user_id": feedback.user_id,
            "satisfaction_score": feedback.satisfaction_score,
            "learning_updated": True
        }
        
    except Exception as e:
        logger.error(f"Feedback processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/providers")
async def get_providers():
    """Get information about available providers"""
    
    providers_info = {}
    for name, provider in orchestrator.providers.items():
        providers_info[name] = {
            "name": provider.name,
            "cost_structure": provider.cost_structure,
            "strengths": provider.strengths,
            "weaknesses": provider.weaknesses,
            "models": list(provider.models.keys()),
            "health": orchestrator.provider_health.get(name, {})
        }
    
    return {
        "available_providers": providers_info,
        "provider_count": len(providers_info),
        "selection_algorithm": "intelligent_scoring_with_user_preferences"
    }

@app.get("/openai/models")
async def get_openai_models():
    """Get OpenAI models information"""
    
    models_info = {}
    for name, model in orchestrator.openai_manager.models.items():
        models_info[name] = {
            "name": model.name,
            "model_id": model.model_id,
            "capabilities": model.capabilities,
            "cost_per_1k_tokens": model.cost_per_1k_tokens,
            "context_length": model.context_length,
            "multimodal": model.multimodal,
            "strengths": model.strengths,
            "use_cases": model.use_cases,
            "speed_tier": model.speed_tier
        }
    
    return {
        "openai_models": models_info,
        "rate_limiting": {
            "user_requests": "unlimited (pay-as-you-go)",
            "bot_requests": "10 minute intervals",
            "current_status": orchestrator.openai_manager.rate_limit_enforced
        }
    }

@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str):
    """Get analytics for specific user"""
    
    try:
        analytics = orchestrator.get_user_analytics(user_id)
        return analytics
        
    except Exception as e:
        logger.error(f"User analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/system")
async def get_system_analytics():
    """Get system-wide analytics"""
    
    try:
        analytics = orchestrator.get_system_analytics()
        
        # Add OpenAI-specific analytics
        openai_analytics = orchestrator.openai_manager.get_usage_analytics()
        analytics["openai_specific"] = openai_analytics
        
        return analytics
        
    except Exception as e:
        logger.error(f"System analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get learned user preferences"""
    
    try:
        # Get preferences from orchestrator
        orchestrator_prefs = orchestrator.user_model_preferences.get(user_id, {})
        
        # Get OpenAI-specific preferences
        openai_prefs = orchestrator.openai_manager.get_user_preference_insights(user_id)
        
        return {
            "user_id": user_id,
            "unified_preferences": orchestrator_prefs,
            "openai_preferences": openai_prefs,
            "learning_status": "active" if orchestrator_prefs or openai_prefs else "no_data"
        }
        
    except Exception as e:
        logger.error(f"User preferences failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preferences/global")
async def get_global_preferences():
    """Get global preference insights"""
    
    try:
        global_insights = orchestrator.openai_manager.get_user_preference_insights()
        
        # Add orchestrator-level insights
        total_users = len(orchestrator.user_model_preferences)
        
        provider_popularity = {}
        for user_prefs in orchestrator.user_model_preferences.values():
            for pref_key, pref_data in user_prefs.items():
                if "/" not in pref_key:  # Provider-level preference
                    if pref_key not in provider_popularity:
                        provider_popularity[pref_key] = {"total_score": 0, "user_count": 0}
                    provider_popularity[pref_key]["total_score"] += pref_data["preference_score"]
                    provider_popularity[pref_key]["user_count"] += 1
        
        # Calculate averages
        for provider in provider_popularity:
            stats = provider_popularity[provider]
            stats["avg_preference"] = stats["total_score"] / stats["user_count"]
        
        return {
            "total_users_with_preferences": total_users,
            "provider_popularity": provider_popularity,
            "openai_insights": global_insights,
            "system_insights": [
                "Users prefer different providers based on task type",
                "OpenAI used strategically for creative and multimodal tasks",
                "Claude preferred for reasoning and analysis",
                "Local models used for simple, cost-free operations"
            ]
        }
        
    except Exception as e:
        logger.error(f"Global preferences failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/openai/emergency-override")
async def set_emergency_override(request: EmergencyOverrideRequest):
    """Set emergency override for OpenAI rate limiting"""
    
    try:
        orchestrator.openai_manager.set_emergency_override(request.enabled, request.reason)
        
        return {
            "message": f"Emergency override {'enabled' if request.enabled else 'disabled'}",
            "enabled": request.enabled,
            "reason": request.reason,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Emergency override failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/openai/rate-limiting/{enabled}")
async def set_rate_limiting(enabled: bool):
    """Enable/disable OpenAI rate limiting"""
    
    try:
        orchestrator.openai_manager.set_rate_limiting(enabled)
        
        return {
            "message": f"Rate limiting {'enabled' if enabled else 'disabled'}",
            "enabled": enabled,
            "applies_to": "bot_requests_only",
            "user_requests": "always_unlimited"
        }
        
    except Exception as e:
        logger.error(f"Rate limiting config failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test")
async def test_integration():
    """Test the integration with sample tasks"""
    
    test_tasks = [
        {
            "description": "Create a UI mockup for fitness tracking",
            "user_initiated": True,
            "multimodal": True,
            "expected": "openai"
        },
        {
            "description": "Fix Python indentation error",
            "user_initiated": False,
            "multimodal": False,
            "expected": "local"
        },
        {
            "description": "Design system architecture",
            "user_initiated": True,
            "multimodal": False,
            "expected": "claude"
        }
    ]
    
    test_results = []
    
    for task in test_tasks:
        recommendation = await orchestrator.get_recommendation(
            task["description"], 
            "test_user", 
            task["user_initiated"]
        )
        
        test_results.append({
            "task": task["description"],
            "user_initiated": task["user_initiated"],
            "recommended_provider": recommendation.get("recommended_provider"),
            "recommended_model": recommendation.get("recommended_model"),
            "expected_provider": task["expected"],
            "match": recommendation.get("recommended_provider") == task["expected"]
        })
    
    return {
        "test_results": test_results,
        "overall_success": all(r["match"] for r in test_results),
        "message": "Integration test completed"
    }

@app.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard data for monitoring"""
    
    system_analytics = orchestrator.get_system_analytics()
    openai_analytics = orchestrator.openai_manager.get_usage_analytics()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overview": {
            "total_executions": system_analytics.get("total_executions", 0),
            "total_cost": system_analytics.get("total_cost", 0.0),
            "total_users": system_analytics.get("total_users", 0),
            "provider_health": orchestrator.provider_health
        },
        "usage_breakdown": {
            "user_vs_bot": system_analytics.get("user_vs_bot", {}),
            "provider_stats": system_analytics.get("provider_statistics", {}),
            "openai_usage": {
                "total_requests": openai_analytics.get("total_requests", 0),
                "total_cost": openai_analytics.get("total_cost", 0.0),
                "rate_limit_status": openai_analytics.get("rate_limit_status", {})
            }
        },
        "learning_status": {
            "users_with_preferences": len(orchestrator.user_model_preferences),
            "learning_active": True,
            "feedback_enabled": True
        }
    }

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8475))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )