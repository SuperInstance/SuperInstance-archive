import asyncio
import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import aiohttp
import backoff
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    id: str
    description: str
    priority: TaskPriority
    status: TaskStatus = TaskStatus.PENDING
    estimated_tokens: int = 0
    actual_tokens: int = 0
    dependencies: List[str] = None
    assigned_bot: str = None
    context_summary: str = ""
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    error_message: str = None
    subtasks: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.subtasks is None:
            self.subtasks = []
        if self.created_at is None:
            self.created_at = datetime.now()

class TokenUsageTracker:
    def __init__(self):
        self.total_tokens = 0
        self.tokens_per_bot = {}
        self.tokens_per_task = {}
        self.rate_limit_remaining = 100000
        self.rate_limit_reset_time = datetime.now() + timedelta(minutes=1)
    
    def add_usage(self, bot_id: str, task_id: str, tokens: int):
        self.total_tokens += tokens
        self.tokens_per_bot[bot_id] = self.tokens_per_bot.get(bot_id, 0) + tokens
        self.tokens_per_task[task_id] = self.tokens_per_task.get(task_id, 0) + tokens
        self.rate_limit_remaining = max(0, self.rate_limit_remaining - tokens)
    
    def can_make_request(self, estimated_tokens: int) -> bool:
        if datetime.now() > self.rate_limit_reset_time:
            self.rate_limit_remaining = 100000
            self.rate_limit_reset_time = datetime.now() + timedelta(minutes=1)
        
        return self.rate_limit_remaining >= estimated_tokens

class TaskDecomposer:
    def __init__(self, claude_api):
        self.claude_api = claude_api
    
    async def decompose_task(self, task: Task) -> List[Task]:
        """Break down complex tasks into smaller subtasks"""
        if self._is_simple_task(task):
            return [task]
        
        decomposition_prompt = f"""
        Analyze this task and break it down into smaller, independent subtasks:
        
        Task: {task.description}
        Priority: {task.priority.name}
        
        Return a JSON list of subtasks with the following format:
        [
            {{
                "id": "unique_id",
                "description": "subtask description",
                "estimated_tokens": 1000,
                "dependencies": ["other_task_id"]
            }}
        ]
        
        Keep subtasks atomic and executable by different bots.
        """
        
        try:
            response = await self.claude_api.complete(decomposition_prompt, max_tokens=2000)
            subtasks_data = json.loads(response.strip())
            
            subtasks = []
            for subtask_data in subtasks_data:
                subtask = Task(
                    id=subtask_data["id"],
                    description=subtask_data["description"],
                    priority=task.priority,
                    estimated_tokens=subtask_data.get("estimated_tokens", 1000),
                    dependencies=subtask_data.get("dependencies", [])
                )
                subtasks.append(subtask)
            
            task.subtasks = [st.id for st in subtasks]
            return subtasks
            
        except Exception as e:
            logger.error(f"Failed to decompose task {task.id}: {e}")
            return [task]
    
    def _is_simple_task(self, task: Task) -> bool:
        """Determine if a task is simple enough to not need decomposition"""
        simple_keywords = [
            "read file", "write file", "list files", "check status",
            "run command", "test", "validate", "format"
        ]
        return any(keyword in task.description.lower() for keyword in simple_keywords)

class BotAllocator:
    def __init__(self):
        self.bot_capabilities = {
            "claude-opus-4": {
                "max_tokens": 200000,
                "cost_per_token": 0.015,
                "strengths": ["complex_reasoning", "code_generation", "analysis"],
                "current_load": 0,
                "max_load": 5
            },
            "claude-haiku": {
                "max_tokens": 100000,
                "cost_per_token": 0.0025,
                "strengths": ["simple_tasks", "summarization", "formatting"],
                "current_load": 0,
                "max_load": 10
            },
            "claude-sonnet": {
                "max_tokens": 200000,
                "cost_per_token": 0.003,
                "strengths": ["balanced", "writing", "editing"],
                "current_load": 0,
                "max_load": 8
            }
        }
    
    def allocate_bot(self, task: Task) -> Optional[str]:
        """Allocate the best bot for a given task"""
        suitable_bots = []
        
        for bot_id, capabilities in self.bot_capabilities.items():
            if capabilities["current_load"] >= capabilities["max_load"]:
                continue
                
            if task.estimated_tokens > capabilities["max_tokens"]:
                continue
            
            score = self._calculate_suitability_score(task, capabilities)
            suitable_bots.append((bot_id, score))
        
        if not suitable_bots:
            return None
        
        suitable_bots.sort(key=lambda x: x[1], reverse=True)
        best_bot = suitable_bots[0][0]
        
        self.bot_capabilities[best_bot]["current_load"] += 1
        return best_bot
    
    def release_bot(self, bot_id: str):
        """Release a bot after task completion"""
        if bot_id in self.bot_capabilities:
            self.bot_capabilities[bot_id]["current_load"] = max(
                0, self.bot_capabilities[bot_id]["current_load"] - 1
            )
    
    def _calculate_suitability_score(self, task: Task, capabilities: Dict) -> float:
        """Calculate how suitable a bot is for a task"""
        score = 0.0
        
        # Token capacity score
        if task.estimated_tokens < capabilities["max_tokens"] * 0.5:
            score += 2.0
        elif task.estimated_tokens < capabilities["max_tokens"] * 0.8:
            score += 1.0
        
        # Cost efficiency score
        cost_efficiency = 1.0 / capabilities["cost_per_token"]
        score += cost_efficiency * 0.5
        
        # Load balancing score
        load_factor = 1.0 - (capabilities["current_load"] / capabilities["max_load"])
        score += load_factor * 2.0
        
        # Capability matching score
        task_keywords = task.description.lower().split()
        capability_matches = sum(
            1 for strength in capabilities["strengths"]
            if any(keyword in strength for keyword in task_keywords)
        )
        score += capability_matches * 1.5
        
        return score

class ContextOptimizer:
    def __init__(self):
        self.max_context_tokens = 150000
        self.summarization_threshold = 100000
    
    async def optimize_context(self, task: Task, full_context: str, claude_api) -> str:
        """Optimize context for token efficiency"""
        context_tokens = self._estimate_tokens(full_context)
        
        if context_tokens <= self.max_context_tokens:
            return full_context
        
        # Smart summarization for large contexts
        if context_tokens > self.summarization_threshold:
            return await self._summarize_context(full_context, task, claude_api)
        
        # Context trimming
        return self._trim_context(full_context, task)
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)"""
        return len(text) // 4
    
    async def _summarize_context(self, context: str, task: Task, claude_api) -> str:
        """Summarize large context while preserving task-relevant information"""
        summarization_prompt = f"""
        Summarize the following context, preserving information relevant to this task:
        Task: {task.description}
        
        Context to summarize:
        {context}
        
        Provide a concise summary that includes:
        1. Key facts and data relevant to the task
        2. Important relationships and dependencies
        3. Critical constraints or requirements
        4. Current state information
        
        Summary:
        """
        
        try:
            summary = await claude_api.complete(summarization_prompt, max_tokens=5000)
            return summary.strip()
        except Exception as e:
            logger.error(f"Context summarization failed: {e}")
            return self._trim_context(context, task)
    
    def _trim_context(self, context: str, task: Task) -> str:
        """Trim context by removing less relevant sections"""
        lines = context.split('\n')
        task_keywords = set(task.description.lower().split())
        
        # Score lines by relevance to task
        scored_lines = []
        for i, line in enumerate(lines):
            line_words = set(line.lower().split())
            relevance_score = len(task_keywords.intersection(line_words))
            scored_lines.append((relevance_score, i, line))
        
        # Sort by relevance and keep most relevant lines
        scored_lines.sort(key=lambda x: x[0], reverse=True)
        
        trimmed_lines = []
        current_tokens = 0
        
        for score, original_index, line in scored_lines:
            line_tokens = self._estimate_tokens(line)
            if current_tokens + line_tokens <= self.max_context_tokens:
                trimmed_lines.append((original_index, line))
                current_tokens += line_tokens
            else:
                break
        
        # Sort back to original order
        trimmed_lines.sort(key=lambda x: x[0])
        return '\n'.join(line for _, line in trimmed_lines)

class ClaudeAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    async def complete(self, prompt: str, max_tokens: int = 4000, model: str = "claude-opus-4") -> str:
        """Make API call to Claude"""
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with self.session.post(
            f"{self.base_url}/messages",
            headers=headers,
            json=data
        ) as response:
            if response.status == 200:
                result = await response.json()
                return result["content"][0]["text"]
            else:
                error_text = await response.text()
                raise Exception(f"API request failed: {response.status} - {error_text}")

class ProgressMonitor:
    def __init__(self):
        self.task_progress = {}
        self.error_counts = {}
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_completion_time": 0,
            "total_tokens_used": 0
        }
    
    def update_task_progress(self, task: Task):
        """Update progress tracking for a task"""
        self.task_progress[task.id] = {
            "status": task.status.value,
            "progress_percentage": self._calculate_progress(task),
            "estimated_completion": self._estimate_completion_time(task),
            "tokens_used": task.actual_tokens
        }
    
    def record_error(self, task_id: str, error: str, bot_id: str):
        """Record error for analysis and recovery"""
        if task_id not in self.error_counts:
            self.error_counts[task_id] = []
        
        self.error_counts[task_id].append({
            "error": error,
            "bot_id": bot_id,
            "timestamp": datetime.now(),
            "retry_count": len(self.error_counts[task_id])
        })
    
    def should_retry_task(self, task_id: str) -> bool:
        """Determine if a failed task should be retried"""
        if task_id not in self.error_counts:
            return True
        
        return len(self.error_counts[task_id]) < 3
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        total_tasks = self.performance_metrics["tasks_completed"] + self.performance_metrics["tasks_failed"]
        success_rate = (
            self.performance_metrics["tasks_completed"] / max(total_tasks, 1) * 100
        )
        
        return {
            "success_rate": success_rate,
            "total_tasks_processed": total_tasks,
            "average_completion_time": self.performance_metrics["average_completion_time"],
            "total_tokens_used": self.performance_metrics["total_tokens_used"],
            "error_rate": len(self.error_counts) / max(total_tasks, 1) * 100
        }
    
    def _calculate_progress(self, task: Task) -> float:
        """Calculate task completion percentage"""
        if task.status == TaskStatus.COMPLETED:
            return 100.0
        elif task.status == TaskStatus.IN_PROGRESS:
            if task.subtasks:
                completed_subtasks = sum(1 for st_id in task.subtasks 
                                       if st_id in self.task_progress 
                                       and self.task_progress[st_id]["status"] == "completed")
                return (completed_subtasks / len(task.subtasks)) * 100.0
            else:
                return 50.0
        else:
            return 0.0
    
    def _estimate_completion_time(self, task: Task) -> Optional[datetime]:
        """Estimate when a task will be completed"""
        if task.status == TaskStatus.COMPLETED:
            return task.completed_at
        
        if task.started_at and task.estimated_tokens:
            avg_tokens_per_minute = 1000  # Rough estimate
            estimated_minutes = task.estimated_tokens / avg_tokens_per_minute
            return task.started_at + timedelta(minutes=estimated_minutes)
        
        return None

class ErrorRecovery:
    def __init__(self, bot_allocator: BotAllocator, progress_monitor: ProgressMonitor):
        self.bot_allocator = bot_allocator
        self.progress_monitor = progress_monitor
        self.recovery_strategies = {
            "context_too_large": self._handle_context_overflow,
            "rate_limit": self._handle_rate_limit,
            "api_error": self._handle_api_error,
            "timeout": self._handle_timeout,
            "allocation_failed": self._handle_allocation_failed
        }
    
    async def handle_error(self, task: Task, error: str, bot_id: str) -> Tuple[bool, str]:
        """Handle task errors and attempt recovery"""
        self.progress_monitor.record_error(task.id, error, bot_id)
        
        # Detect error type
        error_type = self._classify_error(error)
        
        # Apply recovery strategy
        if error_type in self.recovery_strategies:
            try:
                recovery_action = await self.recovery_strategies[error_type](task, error, bot_id)
                return True, recovery_action
            except Exception as e:
                logger.error(f"Recovery failed for task {task.id}: {e}")
        
        # Check if we should retry
        if self.progress_monitor.should_retry_task(task.id):
            return True, "retry_with_different_bot"
        
        return False, "max_retries_exceeded"
    
    def _classify_error(self, error: str) -> str:
        """Classify error type for appropriate recovery strategy"""
        error_lower = error.lower()
        
        if "context" in error_lower and ("large" in error_lower or "limit" in error_lower):
            return "context_too_large"
        elif "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif "timeout" in error_lower:
            return "timeout"
        elif "allocation" in error_lower or "no available" in error_lower:
            return "allocation_failed"
        else:
            return "api_error"
    
    async def _handle_context_overflow(self, task: Task, error: str, bot_id: str) -> str:
        """Handle context too large errors"""
        task.estimated_tokens = min(task.estimated_tokens // 2, 50000)
        return "reduced_context_size"
    
    async def _handle_rate_limit(self, task: Task, error: str, bot_id: str) -> str:
        """Handle rate limit errors"""
        await asyncio.sleep(60)  # Wait for rate limit reset
        return "waited_for_rate_limit_reset"
    
    async def _handle_api_error(self, task: Task, error: str, bot_id: str) -> str:
        """Handle general API errors"""
        await asyncio.sleep(5)  # Brief pause before retry
        return "brief_pause_before_retry"
    
    async def _handle_timeout(self, task: Task, error: str, bot_id: str) -> str:
        """Handle timeout errors"""
        task.estimated_tokens = min(task.estimated_tokens, 10000)
        return "reduced_task_complexity"
    
    async def _handle_allocation_failed(self, task: Task, error: str, bot_id: str) -> str:
        """Handle bot allocation failures"""
        await asyncio.sleep(30)  # Wait for bots to become available
        return "waited_for_bot_availability"

class ClaudeDirector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.claude_api = None
        self.tasks = {}
        self.bot_allocator = BotAllocator()
        self.token_tracker = TokenUsageTracker()
        self.task_decomposer = None
        self.context_optimizer = ContextOptimizer()
        self.progress_monitor = ProgressMonitor()
        self.error_recovery = ErrorRecovery(self.bot_allocator, self.progress_monitor)
        self.running = False
    
    async def start(self):
        """Start the Claude Director service"""
        self.claude_api = ClaudeAPI(self.api_key)
        await self.claude_api.__aenter__()
        self.task_decomposer = TaskDecomposer(self.claude_api)
        self.running = True
        logger.info("Claude Director started")
    
    async def stop(self):
        """Stop the Claude Director service"""
        self.running = False
        if self.claude_api:
            await self.claude_api.__aexit__(None, None, None)
        logger.info("Claude Director stopped")
    
    async def submit_task(self, description: str, priority: TaskPriority = TaskPriority.MEDIUM,
                         estimated_tokens: int = 5000, context: str = "") -> str:
        """Submit a new task for processing"""
        task_id = f"task_{int(time.time() * 1000)}"
        
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            estimated_tokens=estimated_tokens,
            context_summary=context[:1000]  # Store abbreviated context
        )
        
        self.tasks[task_id] = task
        
        # Decompose complex tasks
        subtasks = await self.task_decomposer.decompose_task(task)
        
        if len(subtasks) > 1:
            for subtask in subtasks:
                self.tasks[subtask.id] = subtask
        
        logger.info(f"Task {task_id} submitted with {len(subtasks)} subtasks")
        return task_id
    
    async def execute_task(self, task_id: str, full_context: str = "") -> Dict[str, Any]:
        """Execute a specific task"""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        
        # Check if dependencies are completed
        if not self._dependencies_completed(task):
            return {"status": "waiting_for_dependencies", "task_id": task_id}
        
        # Allocate bot
        bot_id = self.bot_allocator.allocate_bot(task)
        if not bot_id:
            return {"status": "no_bot_available", "task_id": task_id}
        
        task.assigned_bot = bot_id
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        try:
            # Optimize context
            optimized_context = await self.context_optimizer.optimize_context(
                task, full_context, self.claude_api
            )
            
            # Execute task
            result = await self._execute_with_bot(task, optimized_context, bot_id)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.actual_tokens = result.get("tokens_used", 0)
            
            self.token_tracker.add_usage(bot_id, task_id, task.actual_tokens)
            self.progress_monitor.performance_metrics["tasks_completed"] += 1
            
            return {
                "status": "completed",
                "task_id": task_id,
                "result": result["content"],
                "tokens_used": task.actual_tokens,
                "bot_used": bot_id
            }
            
        except Exception as e:
            # Handle error with recovery
            can_recover, recovery_action = await self.error_recovery.handle_error(
                task, str(e), bot_id
            )
            
            if can_recover and recovery_action == "retry_with_different_bot":
                # Release current bot and try again
                self.bot_allocator.release_bot(bot_id)
                task.status = TaskStatus.PENDING
                task.assigned_bot = None
                return await self.execute_task(task_id, full_context)
            else:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                self.progress_monitor.performance_metrics["tasks_failed"] += 1
                return {
                    "status": "failed",
                    "task_id": task_id,
                    "error": str(e),
                    "recovery_action": recovery_action
                }
        finally:
            if task.assigned_bot:
                self.bot_allocator.release_bot(task.assigned_bot)
            self.progress_monitor.update_task_progress(task)
    
    async def _execute_with_bot(self, task: Task, context: str, bot_id: str) -> Dict[str, Any]:
        """Execute task using specified bot"""
        prompt = f"""
        Task: {task.description}
        Priority: {task.priority.name}
        
        Context:
        {context}
        
        Please execute this task and provide a clear, actionable result.
        """
        
        model_mapping = {
            "claude-opus-4": "claude-3-opus-20240229",
            "claude-haiku": "claude-3-haiku-20240307",
            "claude-sonnet": "claude-3-sonnet-20240229"
        }
        
        model = model_mapping.get(bot_id, "claude-3-sonnet-20240229")
        max_tokens = min(task.estimated_tokens, self.bot_allocator.bot_capabilities[bot_id]["max_tokens"])
        
        content = await self.claude_api.complete(prompt, max_tokens, model)
        
        return {
            "content": content,
            "tokens_used": self._estimate_tokens_used(prompt, content)
        }
    
    def _dependencies_completed(self, task: Task) -> bool:
        """Check if all task dependencies are completed"""
        for dep_id in task.dependencies:
            if dep_id not in self.tasks or self.tasks[dep_id].status != TaskStatus.COMPLETED:
                return False
        return True
    
    def _estimate_tokens_used(self, prompt: str, response: str) -> int:
        """Estimate tokens used in API call"""
        return (len(prompt) + len(response)) // 4
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get detailed status of a task"""
        if task_id not in self.tasks:
            return {"error": "Task not found"}
        
        task = self.tasks[task_id]
        progress_info = self.progress_monitor.task_progress.get(task_id, {})
        
        return {
            "task_id": task_id,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.name,
            "assigned_bot": task.assigned_bot,
            "progress_percentage": progress_info.get("progress_percentage", 0),
            "estimated_completion": progress_info.get("estimated_completion"),
            "tokens_used": task.actual_tokens,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "subtasks": task.subtasks,
            "dependencies": task.dependencies
        }
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics and health information"""
        health = self.progress_monitor.get_system_health()
        
        return {
            "system_health": health,
            "bot_status": {
                bot_id: {
                    "current_load": info["current_load"],
                    "max_load": info["max_load"],
                    "utilization": info["current_load"] / info["max_load"] * 100
                }
                for bot_id, info in self.bot_allocator.bot_capabilities.items()
            },
            "token_usage": {
                "total_tokens": self.token_tracker.total_tokens,
                "tokens_per_bot": self.token_tracker.tokens_per_bot,
                "rate_limit_remaining": self.token_tracker.rate_limit_remaining,
                "rate_limit_reset_time": self.token_tracker.rate_limit_reset_time.isoformat()
            },
            "task_counts": {
                "pending": sum(1 for task in self.tasks.values() if task.status == TaskStatus.PENDING),
                "in_progress": sum(1 for task in self.tasks.values() if task.status == TaskStatus.IN_PROGRESS),
                "completed": sum(1 for task in self.tasks.values() if task.status == TaskStatus.COMPLETED),
                "failed": sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
            }
        }

    async def rebalance_tasks(self):
        """Rebalance tasks across available bots"""
        pending_tasks = [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
        
        # Sort by priority and creation time
        pending_tasks.sort(key=lambda x: (x.priority.value, x.created_at), reverse=True)
        
        reallocated = 0
        for task in pending_tasks:
            if self._dependencies_completed(task):
                new_bot = self.bot_allocator.allocate_bot(task)
                if new_bot and new_bot != task.assigned_bot:
                    if task.assigned_bot:
                        self.bot_allocator.release_bot(task.assigned_bot)
                    task.assigned_bot = new_bot
                    reallocated += 1
        
        logger.info(f"Rebalanced {reallocated} tasks")
        return reallocated