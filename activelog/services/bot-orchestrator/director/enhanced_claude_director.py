"""
Enhanced Claude Director with Local LLM Integration
Extends the base Claude Director to support local and free LLMs through the bot ecosystem
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from .claude_director import ClaudeDirector, Task, TaskPriority, TaskStatus
from ..integrations.local_llm_connector import LocalLLMConnector

logger = logging.getLogger(__name__)

@dataclass 
class EnhancedTaskResult:
    """Enhanced task result with local LLM integration"""
    task_id: str
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    cost: float = 0.0
    latency_ms: float = 0.0
    model_used: str = "unknown"
    provider: str = "unknown"
    confidence_score: Optional[float] = None
    is_local: bool = False
    fallback_used: bool = False
    total_attempts: int = 1

class EnhancedTaskDecomposer:
    """Enhanced task decomposer that can use local LLMs for decomposition"""
    
    def __init__(self, claude_api, local_llm_connector: LocalLLMConnector):
        self.claude_api = claude_api
        self.local_llm_connector = local_llm_connector
        
    async def decompose_task(self, task: Task) -> List[Task]:
        """Decompose task using the most appropriate model"""
        if self._is_simple_task(task):
            return [task]
        
        decomposition_request = {
            "task_id": f"decompose_{task.id}",
            "description": self._build_decomposition_prompt(task),
            "task_type": "reasoning", 
            "max_tokens": 2000,
            "temperature": 0.3,
            "max_cost": 0.02  # Prefer cheaper models for decomposition
        }
        
        # Try local LLMs first for cost efficiency
        try:
            if self.local_llm_connector.connected:
                result = await self.local_llm_connector.execute_task(decomposition_request)
                if result["success"]:
                    return self._parse_decomposition_response(result["response"], task)
        except Exception as e:
            logger.warning(f"Local LLM decomposition failed: {e}")
        
        # Fallback to Claude API
        try:
            response = await self.claude_api.complete(
                decomposition_request["description"], 
                max_tokens=decomposition_request["max_tokens"]
            )
            return self._parse_decomposition_response(response, task)
        except Exception as e:
            logger.error(f"Failed to decompose task {task.id}: {e}")
            return [task]
    
    def _build_decomposition_prompt(self, task: Task) -> str:
        return f"""
        Analyze this task and break it down into smaller, independent subtasks:
        
        Task: {task.description}
        Priority: {task.priority.name}
        Estimated tokens: {task.estimated_tokens}
        
        Return a JSON list of subtasks with this format:
        [
            {{
                "id": "unique_id",
                "description": "clear subtask description",
                "estimated_tokens": 1000,
                "dependencies": ["other_task_id"],
                "task_type": "code_generation|analysis|research|chat"
            }}
        ]
        
        Guidelines:
        - Keep subtasks atomic and executable by different models
        - Prefer simple tasks that can use local/free models
        - Only create complex subtasks when absolutely necessary
        - Minimize dependencies between subtasks
        """
    
    def _parse_decomposition_response(self, response: str, original_task: Task) -> List[Task]:
        """Parse decomposition response into Task objects"""
        try:
            subtasks_data = json.loads(response.strip())
            if not isinstance(subtasks_data, list):
                return [original_task]
            
            subtasks = []
            for subtask_data in subtasks_data:
                subtask = Task(
                    id=subtask_data.get("id", f"{original_task.id}_sub_{len(subtasks)}"),
                    description=subtask_data["description"],
                    priority=original_task.priority,
                    estimated_tokens=subtask_data.get("estimated_tokens", 1000),
                    dependencies=subtask_data.get("dependencies", [])
                )
                subtasks.append(subtask)
            
            original_task.subtasks = [st.id for st in subtasks]
            return subtasks
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse decomposition response: {e}")
            return [original_task]
    
    def _is_simple_task(self, task: Task) -> bool:
        """Determine if a task is simple enough to not need decomposition"""
        simple_keywords = [
            "read file", "write file", "list files", "check status",
            "run command", "test", "validate", "format", "summarize",
            "translate", "simple question", "basic calculation"
        ]
        return (
            any(keyword in task.description.lower() for keyword in simple_keywords) or
            task.estimated_tokens < 2000
        )

class SmartBotAllocator:
    """Smart bot allocator that considers both Claude and local LLMs"""
    
    def __init__(self, local_llm_connector: LocalLLMConnector):
        self.local_llm_connector = local_llm_connector
        
        # Enhanced bot capabilities including local models
        self.bot_capabilities = {
            "claude-opus-4": {
                "max_tokens": 200000,
                "cost_per_1k_tokens": 15.0,
                "strengths": ["complex_reasoning", "code_generation", "analysis", "research"],
                "current_load": 0,
                "max_load": 3,
                "provider": "anthropic",
                "is_local": False
            },
            "claude-sonnet": {
                "max_tokens": 200000,
                "cost_per_1k_tokens": 3.0,
                "strengths": ["balanced", "writing", "editing", "code_review"],
                "current_load": 0,
                "max_load": 5,
                "provider": "anthropic", 
                "is_local": False
            },
            "claude-haiku": {
                "max_tokens": 100000,
                "cost_per_1k_tokens": 0.25,
                "strengths": ["simple_tasks", "summarization", "formatting"],
                "current_load": 0,
                "max_load": 8,
                "provider": "anthropic",
                "is_local": False
            },
            "local-llm-pool": {
                "max_tokens": 32000,
                "cost_per_1k_tokens": 0.0,
                "strengths": ["simple_tasks", "chat", "basic_reasoning", "summarization"],
                "current_load": 0,
                "max_load": 20,  # Higher capacity for free models
                "provider": "local",
                "is_local": True
            }
        }
        
        # Task type preferences for different models
        self.task_preferences = {
            "simple_chat": ["local-llm-pool", "claude-haiku", "claude-sonnet"],
            "code_generation": ["claude-opus-4", "claude-sonnet", "local-llm-pool"],
            "code_review": ["claude-sonnet", "claude-opus-4", "local-llm-pool"],
            "analysis": ["claude-opus-4", "claude-sonnet", "local-llm-pool"],
            "research": ["claude-opus-4", "claude-sonnet"],
            "summarization": ["local-llm-pool", "claude-haiku", "claude-sonnet"],
            "translation": ["local-llm-pool", "claude-sonnet", "claude-haiku"],
            "creative_writing": ["local-llm-pool", "claude-sonnet", "claude-opus-4"]
        }
    
    async def allocate_bot(self, task: Task) -> Optional[Dict[str, Any]]:
        """Allocate the best bot for a given task with cost optimization"""
        task_type = self._classify_task_type(task)
        
        # Get preference order for this task type
        preference_order = self.task_preferences.get(task_type, 
            ["local-llm-pool", "claude-haiku", "claude-sonnet", "claude-opus-4"])
        
        # Score and rank available bots
        suitable_bots = []
        
        for bot_id in preference_order:
            if bot_id not in self.bot_capabilities:
                continue
                
            capabilities = self.bot_capabilities[bot_id]
            
            # Check availability
            if capabilities["current_load"] >= capabilities["max_load"]:
                continue
            
            # Check token capacity
            if task.estimated_tokens > capabilities["max_tokens"]:
                continue
            
            # For local LLM pool, check actual availability
            if bot_id == "local-llm-pool" and self.local_llm_connector:
                if not await self._check_local_llm_availability():
                    continue
            
            score = await self._calculate_bot_score(task, bot_id, capabilities)
            suitable_bots.append((bot_id, score, capabilities))
        
        if not suitable_bots:
            return None
        
        # Sort by score (higher is better)
        suitable_bots.sort(key=lambda x: x[1], reverse=True)
        best_bot_id, _, best_capabilities = suitable_bots[0]
        
        # Reserve the bot
        self.bot_capabilities[best_bot_id]["current_load"] += 1
        
        return {
            "bot_id": best_bot_id,
            "provider": best_capabilities["provider"],
            "is_local": best_capabilities["is_local"],
            "estimated_cost": self._estimate_task_cost(task, best_capabilities),
            "capabilities": best_capabilities
        }
    
    async def _calculate_bot_score(self, task: Task, bot_id: str, capabilities: Dict) -> float:
        """Calculate suitability score for a bot"""
        score = 0.0
        
        # Cost efficiency (heavily weighted)
        if capabilities["is_local"]:
            score += 50.0  # Strong preference for free models
        else:
            # Lower cost per token = higher score
            cost_score = max(0, 20 - capabilities["cost_per_1k_tokens"])
            score += cost_score
        
        # Token capacity score
        token_utilization = task.estimated_tokens / capabilities["max_tokens"]
        if token_utilization < 0.3:
            score += 15.0
        elif token_utilization < 0.6:
            score += 10.0
        elif token_utilization < 0.8:
            score += 5.0
        
        # Load balancing
        load_factor = 1.0 - (capabilities["current_load"] / capabilities["max_load"])
        score += load_factor * 10.0
        
        # Capability matching
        task_keywords = task.description.lower().split()
        capability_matches = sum(
            2 for strength in capabilities["strengths"]
            if any(keyword in strength or strength in task.description.lower() 
                  for keyword in task_keywords)
        )
        score += capability_matches
        
        # Priority boost for high-priority tasks on premium models
        if task.priority == TaskPriority.CRITICAL and not capabilities["is_local"]:
            score += 15.0
        elif task.priority == TaskPriority.HIGH and not capabilities["is_local"]:
            score += 10.0
        
        return score
    
    async def _check_local_llm_availability(self) -> bool:
        """Check if local LLMs are available"""
        if not self.local_llm_connector or not self.local_llm_connector.connected:
            return False
        
        try:
            health = await self.local_llm_connector.health_check()
            return health.get("status") == "healthy"
        except:
            return False
    
    def _classify_task_type(self, task: Task) -> str:
        """Classify task type based on description"""
        description_lower = task.description.lower()
        
        if any(keyword in description_lower for keyword in 
               ["write code", "implement", "function", "class", "programming"]):
            return "code_generation"
        elif any(keyword in description_lower for keyword in 
                 ["review code", "analyze code", "check code", "debug"]):
            return "code_review"
        elif any(keyword in description_lower for keyword in 
                 ["research", "find information", "investigate", "study"]):
            return "research"
        elif any(keyword in description_lower for keyword in 
                 ["analyze", "examination", "evaluate", "assess"]):
            return "analysis"
        elif any(keyword in description_lower for keyword in 
                 ["summarize", "summary", "condense", "brief"]):
            return "summarization"
        elif any(keyword in description_lower for keyword in 
                 ["translate", "translation", "convert language"]):
            return "translation"
        elif any(keyword in description_lower for keyword in 
                 ["write story", "creative", "poem", "fiction"]):
            return "creative_writing"
        else:
            return "simple_chat"
    
    def _estimate_task_cost(self, task: Task, capabilities: Dict) -> float:
        """Estimate cost for executing a task"""
        if capabilities["is_local"]:
            return 0.0
        
        tokens = task.estimated_tokens
        cost_per_1k = capabilities["cost_per_1k_tokens"]
        return (tokens / 1000) * cost_per_1k
    
    def release_bot(self, bot_id: str):
        """Release a bot after task completion"""
        if bot_id in self.bot_capabilities:
            self.bot_capabilities[bot_id]["current_load"] = max(
                0, self.bot_capabilities[bot_id]["current_load"] - 1
            )

class EnhancedClaudeDirector(ClaudeDirector):
    """Enhanced Claude Director with local LLM integration"""
    
    def __init__(self, claude_api_key: str, bot_ecosystem_url: str = "http://localhost:8450"):
        super().__init__(claude_api_key)
        self.local_llm_connector = LocalLLMConnector(bot_ecosystem_url)
        self.smart_allocator = SmartBotAllocator(self.local_llm_connector)
        self.enhanced_decomposer = None
        self.execution_stats = {
            "total_tasks": 0,
            "local_llm_tasks": 0,
            "claude_tasks": 0,
            "cost_saved": 0.0,
            "avg_latency_local": 0.0,
            "avg_latency_claude": 0.0
        }
    
    async def start(self):
        """Start the enhanced director with local LLM support"""
        await super().start()
        
        try:
            await self.local_llm_connector.initialize()
            self.enhanced_decomposer = EnhancedTaskDecomposer(
                self.claude_api, self.local_llm_connector
            )
            logger.info("Enhanced Claude Director started with local LLM support")
        except Exception as e:
            logger.warning(f"Local LLM integration failed, continuing with Claude only: {e}")
    
    async def stop(self):
        """Stop the enhanced director"""
        if self.local_llm_connector:
            await self.local_llm_connector.close()
        await super().stop()
    
    async def execute_task(self, task_id: str) -> EnhancedTaskResult:
        """Execute a task using the optimal model (local or Claude)"""
        task = self.tasks.get(task_id)
        if not task:
            return EnhancedTaskResult(
                task_id=task_id,
                success=False,
                error="Task not found"
            )
        
        # Allocate the best bot for this task
        allocation = await self.smart_allocator.allocate_bot(task)
        if not allocation:
            return EnhancedTaskResult(
                task_id=task_id,
                success=False,
                error="No suitable bot available"
            )
        
        task.assigned_bot = allocation["bot_id"]
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        result = None
        fallback_used = False
        attempts = 0
        
        try:
            # Try the allocated model first
            if allocation["is_local"]:
                result = await self._execute_with_local_llm(task, allocation)
                attempts += 1
                
                # Fallback to Claude if local model fails
                if not result.success and result.error:
                    logger.warning(f"Local LLM failed for task {task_id}, trying Claude fallback")
                    fallback_result = await self._execute_with_claude(task)
                    if fallback_result.success:
                        result = fallback_result
                        fallback_used = True
                        attempts += 1
            else:
                result = await self._execute_with_claude(task)
                attempts += 1
            
            # Update task status
            if result.success:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
            else:
                task.status = TaskStatus.FAILED
                task.error_message = result.error
            
            # Update statistics
            self._update_execution_stats(result, fallback_used)
            
            # Release bot
            self.smart_allocator.release_bot(allocation["bot_id"])
            
            result.fallback_used = fallback_used
            result.total_attempts = attempts
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            self.smart_allocator.release_bot(allocation["bot_id"])
            
            return EnhancedTaskResult(
                task_id=task_id,
                success=False,
                error=str(e),
                total_attempts=attempts
            )
    
    async def _execute_with_local_llm(self, task: Task, allocation: Dict) -> EnhancedTaskResult:
        """Execute task using local LLM"""
        start_time = datetime.now()
        
        # Prepare task request for local LLM
        task_request = {
            "task_id": task.id,
            "description": task.description,
            "task_type": self.smart_allocator._classify_task_type(task),
            "max_tokens": min(task.estimated_tokens, 4000),  # Limit for local models
            "temperature": 0.7,
            "context": {"priority": task.priority.name}
        }
        
        try:
            result = await self.local_llm_connector.execute_task(task_request)
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            return EnhancedTaskResult(
                task_id=task.id,
                success=result["success"],
                response=result.get("response"),
                error=result.get("error"),
                cost=0.0,  # Local models are free
                latency_ms=latency_ms,
                model_used=result.get("model_used", "local-unknown"),
                provider="local",
                confidence_score=result.get("confidence_score"),
                is_local=True
            )
            
        except Exception as e:
            logger.error(f"Local LLM execution failed: {e}")
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            return EnhancedTaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                cost=0.0,
                latency_ms=latency_ms,
                model_used="local-error",
                provider="local",
                is_local=True
            )
    
    async def _execute_with_claude(self, task: Task) -> EnhancedTaskResult:
        """Execute task using Claude API"""
        start_time = datetime.now()
        
        try:
            response = await self.claude_api.complete(
                task.description,
                max_tokens=task.estimated_tokens
            )
            
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Estimate cost (rough approximation)
            estimated_cost = (task.estimated_tokens / 1000) * 0.015  # Claude API pricing
            
            return EnhancedTaskResult(
                task_id=task.id,
                success=bool(response),
                response=response,
                error=None if response else "Empty response from Claude",
                cost=estimated_cost,
                latency_ms=latency_ms,
                model_used="claude-api",
                provider="anthropic",
                is_local=False
            )
            
        except Exception as e:
            logger.error(f"Claude API execution failed: {e}")
            end_time = datetime.now()
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            return EnhancedTaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                cost=0.0,
                latency_ms=latency_ms,
                model_used="claude-error",
                provider="anthropic",
                is_local=False
            )
    
    def _update_execution_stats(self, result: EnhancedTaskResult, fallback_used: bool):
        """Update execution statistics"""
        self.execution_stats["total_tasks"] += 1
        
        if result.is_local:
            self.execution_stats["local_llm_tasks"] += 1
            
            # Update average latency for local models
            current_avg = self.execution_stats["avg_latency_local"]
            count = self.execution_stats["local_llm_tasks"]
            self.execution_stats["avg_latency_local"] = (
                (current_avg * (count - 1) + result.latency_ms) / count
            )
        else:
            self.execution_stats["claude_tasks"] += 1
            
            # Update average latency for Claude
            current_avg = self.execution_stats["avg_latency_claude"]
            count = self.execution_stats["claude_tasks"]
            self.execution_stats["avg_latency_claude"] = (
                (current_avg * (count - 1) + result.latency_ms) / count
            )
            
        # Estimate cost savings by using local models
        if result.is_local and not fallback_used:
            # Rough estimate of what Claude would have cost
            estimated_claude_cost = (2000 / 1000) * 0.015  # Assume 2k tokens avg
            self.execution_stats["cost_saved"] += estimated_claude_cost
    
    async def get_enhanced_system_metrics(self) -> Dict[str, Any]:
        """Get enhanced system metrics including local LLM stats"""
        base_metrics = await self.get_system_metrics()
        
        # Add local LLM metrics
        local_llm_health = {}
        local_models_info = {}
        
        if self.local_llm_connector and self.local_llm_connector.connected:
            try:
                local_llm_health = await self.local_llm_connector.health_check()
                local_models_info = await self.local_llm_connector.get_local_models_info()
            except Exception as e:
                logger.error(f"Failed to get local LLM metrics: {e}")
        
        enhanced_metrics = {
            **base_metrics,
            "local_llm_integration": {
                "connected": self.local_llm_connector.connected if self.local_llm_connector else False,
                "health": local_llm_health,
                "local_models": local_models_info
            },
            "execution_stats": self.execution_stats,
            "bot_allocation": {
                "available_bots": len(self.smart_allocator.bot_capabilities),
                "bot_loads": {
                    bot_id: caps["current_load"] 
                    for bot_id, caps in self.smart_allocator.bot_capabilities.items()
                }
            }
        }
        
        return enhanced_metrics
    
    async def recommend_optimization(self, task_description: str) -> Dict[str, Any]:
        """Get recommendations for optimizing task execution"""
        recommendations = {
            "cost_optimization": [],
            "performance_optimization": [],
            "model_suggestions": []
        }
        
        # Create a temporary task for analysis
        temp_task = Task(
            id="temp_analysis",
            description=task_description,
            priority=TaskPriority.MEDIUM,
            estimated_tokens=len(task_description.split()) * 4  # Rough estimate
        )
        
        # Get model recommendations
        if self.local_llm_connector and self.local_llm_connector.connected:
            try:
                llm_recommendation = await self.local_llm_connector.get_model_recommendation({
                    "task_id": "recommendation",
                    "description": task_description,
                    "task_type": self.smart_allocator._classify_task_type(temp_task)
                })
                
                if "recommendation" in llm_recommendation:
                    rec = llm_recommendation["recommendation"]
                    recommendations["model_suggestions"].append({
                        "model": rec.get("model_name", "unknown"),
                        "provider": rec.get("provider", "unknown"),
                        "confidence": rec.get("confidence", 0.0),
                        "expected_cost": rec.get("expected_cost", 0.0),
                        "reasoning": rec.get("reasoning", "")
                    })
            except Exception as e:
                logger.error(f"Failed to get model recommendation: {e}")
        
        # Cost optimization suggestions
        task_type = self.smart_allocator._classify_task_type(temp_task)
        if task_type in ["simple_chat", "summarization", "translation"]:
            recommendations["cost_optimization"].append(
                "This task can likely be handled by free local models"
            )
        
        if temp_task.estimated_tokens > 10000:
            recommendations["performance_optimization"].append(
                "Consider breaking this large task into smaller subtasks"
            )
        
        return recommendations