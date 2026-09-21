"""
Local LLM Connector for Bot Orchestration System
Integrates with the bot ecosystem service to access local and free LLMs
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)

class LocalLLMConnector:
    """Connector to interface with local LLMs through the bot ecosystem service"""
    
    def __init__(self, bot_ecosystem_url: str = "http://localhost:8450"):
        self.bot_ecosystem_url = bot_ecosystem_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.available_models: List[Dict[str, Any]] = []
        self.connected = False
        
    async def initialize(self):
        """Initialize connection to bot ecosystem service"""
        try:
            self.session = aiohttp.ClientSession()
            await self._check_connection()
            await self._discover_models()
            self.connected = True
            logger.info(f"LocalLLMConnector initialized with {len(self.available_models)} models")
        except Exception as e:
            logger.error(f"Failed to initialize LocalLLMConnector: {e}")
            raise
    
    async def close(self):
        """Close the connection"""
        if self.session:
            await self.session.close()
        self.connected = False
    
    async def _check_connection(self) -> bool:
        """Check if bot ecosystem service is available"""
        try:
            async with self.session.get(f"{self.bot_ecosystem_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('status') == 'healthy'
                return False
        except Exception as e:
            logger.error(f"Bot ecosystem service connection failed: {e}")
            return False
    
    async def _discover_models(self):
        """Discover available models from bot ecosystem service"""
        try:
            async with self.session.get(f"{self.bot_ecosystem_url}/models") as response:
                if response.status == 200:
                    self.available_models = await response.json()
                    logger.info(f"Discovered {len(self.available_models)} models")
                else:
                    logger.warning(f"Failed to discover models: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error discovering models: {e}")
    
    async def execute_task(self, task_request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task using the bot ecosystem service"""
        if not self.connected:
            raise RuntimeError("LocalLLMConnector not initialized")
        
        try:
            # Map orchestrator task format to bot ecosystem format
            ecosystem_request = {
                "prompt": task_request.get("description", ""),
                "task_type": self._map_task_type(task_request.get("task_type", "chat")),
                "max_tokens": task_request.get("max_tokens", 1000),
                "temperature": task_request.get("temperature", 0.7),
                "max_latency_ms": task_request.get("max_latency_ms", 30000),
                "min_accuracy": task_request.get("min_accuracy", 0.7),
                "max_cost": task_request.get("max_cost", 0.10),
                "preferred_model": task_request.get("preferred_model"),
                "context": task_request.get("context", {})
            }
            
            async with self.session.post(
                f"{self.bot_ecosystem_url}/tasks/execute",
                json=ecosystem_request
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Map back to orchestrator format
                    return {
                        "task_id": result.get("task_id"),
                        "success": result.get("success", False),
                        "response": result.get("response"),
                        "error": result.get("error"),
                        "cost": result.get("cost", 0.0),
                        "latency_ms": result.get("latency_ms", 0),
                        "model_used": result.get("model_used"),
                        "confidence_score": result.get("confidence_score"),
                        "provider": "local_llm",
                        "execution_stats": result.get("execution_stats", {}),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Task execution failed: HTTP {response.status} - {error_text}")
                    return {
                        "task_id": task_request.get("task_id"),
                        "success": False,
                        "error": f"HTTP {response.status}: {error_text}",
                        "cost": 0.0,
                        "latency_ms": 0,
                        "model_used": "unknown",
                        "provider": "local_llm"
                    }
                    
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            return {
                "task_id": task_request.get("task_id"),
                "success": False,
                "error": str(e),
                "cost": 0.0,
                "latency_ms": 0,
                "model_used": "unknown",
                "provider": "local_llm"
            }
    
    async def get_model_recommendation(self, task_request: Dict[str, Any]) -> Dict[str, Any]:
        """Get model recommendation without executing the task"""
        if not self.connected:
            raise RuntimeError("LocalLLMConnector not initialized")
        
        try:
            params = {
                "task_id": task_request.get("task_id", "recommendation"),
                "prompt": task_request.get("description", ""),
                "task_type": self._map_task_type(task_request.get("task_type", "chat")),
                "complexity": task_request.get("complexity")
            }
            
            async with self.session.get(
                f"{self.bot_ecosystem_url}/tasks/{params['task_id']}/recommend",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Recommendation failed: HTTP {response.status}")
                    return {"error": f"HTTP {response.status}"}
                    
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return {"error": str(e)}
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models with capabilities"""
        await self._discover_models()  # Refresh model list
        return self.available_models
    
    async def get_performance_analytics(self) -> Dict[str, Any]:
        """Get performance analytics from bot ecosystem service"""
        if not self.connected:
            return {}
        
        try:
            async with self.session.get(f"{self.bot_ecosystem_url}/analytics/performance") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to get analytics: HTTP {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Analytics error: {e}")
            return {}
    
    async def get_cost_analysis(self, task_request: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cost implications of a task"""
        if not self.connected:
            return {}
        
        try:
            params = {
                "prompt": task_request.get("description", ""),
                "task_type": self._map_task_type(task_request.get("task_type", "chat")),
                "max_tokens": task_request.get("max_tokens", 1000)
            }
            
            async with self.session.get(
                f"{self.bot_ecosystem_url}/cost/analysis",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Cost analysis failed: HTTP {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Cost analysis error: {e}")
            return {}
    
    async def get_local_models_info(self) -> Dict[str, Any]:
        """Get information about local models specifically"""
        if not self.connected:
            return {}
        
        try:
            async with self.session.get(f"{self.bot_ecosystem_url}/models/local") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"Local models info error: {e}")
            return {}
    
    def _map_task_type(self, orchestrator_task_type: str) -> str:
        """Map orchestrator task types to bot ecosystem task types"""
        mapping = {
            "text_generation": "chat",
            "code_generation": "code_generation",
            "code_review": "code_review",
            "analysis": "analysis",
            "research": "research",
            "translation": "translation",
            "summarization": "summarization",
            "creative": "creative_writing",
            "math": "math",
            "reasoning": "reasoning"
        }
        return mapping.get(orchestrator_task_type.lower(), "chat")
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of the local LLM ecosystem"""
        if not self.connected:
            return {"status": "disconnected"}
        
        try:
            async with self.session.get(f"{self.bot_ecosystem_url}/health") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"status": "error", "http_status": response.status}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        if not self.connected:
            return {}
        
        try:
            async with self.session.get(f"{self.bot_ecosystem_url}/admin/stats") as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"System stats error: {e}")
            return {}
    
    def is_local_model(self, model_name: str) -> bool:
        """Check if a model is a local/free model"""
        local_prefixes = ["ollama:", "lmstudio:", "gpt4all:", "llamacpp:"]
        free_providers = ["mistral", "cohere", "huggingface"]
        
        model_lower = model_name.lower()
        
        # Check for local model prefixes
        if any(model_lower.startswith(prefix) for prefix in local_prefixes):
            return True
        
        # Check for free API providers
        if any(provider in model_lower for provider in free_providers):
            return True
        
        return False
    
    def get_model_cost_estimate(self, model_name: str, tokens: int) -> float:
        """Estimate cost for a model (returns 0 for local/free models)"""
        if self.is_local_model(model_name):
            return 0.0
        
        # Cost estimates for paid models (per 1000 tokens)
        cost_per_1k = {
            "claude": 0.075,
            "gpt-4": 0.06,
            "gpt-3.5": 0.002
        }
        
        for model_key, cost in cost_per_1k.items():
            if model_key in model_name.lower():
                return (tokens / 1000) * cost
        
        # Default estimate for unknown paid models
        return (tokens / 1000) * 0.01