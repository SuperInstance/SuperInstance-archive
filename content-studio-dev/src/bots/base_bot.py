# src/bots/base_bot.py

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import json

# Import ollama only if available (optional dependency)
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ Ollama not available - will use API-only mode")


class BotStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    STUCK = "stuck"
    ERROR = "error"
    WAITING_HELP = "waiting_help"


@dataclass
class BotConfig:
    bot_id: str
    bot_type: str
    model: str
    specialty: str = ""
    lora_path: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    always_running: bool = False


class BaseBot(ABC):
    """Base class for all specialized content creation bots"""

    def __init__(self, config: BotConfig, help_queue, message_bus, knowledge_base, api_client=None):
        self.config = config
        self.status = BotStatus.IDLE
        self.current_task = None
        self.help_queue = help_queue
        self.message_bus = message_bus
        self.knowledge_base = knowledge_base
        self.conversation_history = []

        # NEW: API client for making AI calls
        self.api_client = api_client

        # NEW: Task backlog for parallel work
        self.backlog = []  # List of tasks to work through
        self.max_backlog_size = 20  # Maximum tasks in backlog
        self.completed_tasks = []  # History of completed tasks

        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "help_requests": 0,
            "avg_response_time": 0,
            "tokens_used": 0
        }

    async def start(self):
        """Start the bot's main loop"""
        print(f"🤖 Starting {self.config.bot_id} ({self.config.bot_type})")

        if self.config.always_running:
            # Always-running bots (story_indexer, asset_monitor)
            asyncio.create_task(self.continuous_work_loop())
        else:
            # Task-based bots - work through backlog
            asyncio.create_task(self.backlog_work_loop())

    async def continuous_work_loop(self):
        """For bots that always run (story_indexer, asset_monitor, etc.)"""
        while True:
            try:
                self.status = BotStatus.WORKING
                await self.do_continuous_work()
                await asyncio.sleep(5)  # Adjust based on bot type
            except Exception as e:
                print(f"❌ Error in {self.config.bot_id}: {e}")
                await asyncio.sleep(10)

    async def task_listener(self):
        """Listen for assigned tasks (legacy - kept for compatibility)"""
        while True:
            task = await self.message_bus.get_task_for_bot(self.config.bot_id)
            if task:
                await self.execute_task(task)
            await asyncio.sleep(0.5)

    async def backlog_work_loop(self):
        """
        NEW: Continuously work through task backlog
        This replaces task_listener for better parallel performance
        """
        while True:
            try:
                if self.backlog:
                    # Get next task from backlog
                    self.current_task = self.backlog.pop(0)
                    self.status = BotStatus.WORKING

                    # Execute task
                    result = await self.execute_task(self.current_task)

                    # Handle result safely
                    if result and result.get('status') == 'completed':
                        # Store completed task
                        self.completed_tasks.append({
                            'task': self.current_task,
                            'result': result,
                            'completed_at': time.time()
                        })

                        # Report completion to Foreman via message bus
                        await self.message_bus.publish('task_completed', {
                            'bot_id': self.config.bot_id,
                            'task_id': self.current_task.get('id') if self.current_task else None,
                            'result': result
                        })
                    elif result and result.get('status') == 'help_requested':
                        # Task needs help, wait for assistance
                        print(f"⏸️  {self.config.bot_id} waiting for help on task")
                    else:
                        # Task failed or returned None
                        print(f"⚠️  {self.config.bot_id} task returned: {result}")

                    self.current_task = None
                else:
                    # Backlog empty - idle
                    self.status = BotStatus.IDLE
                    await asyncio.sleep(2)  # Check again in 2 seconds

            except Exception as e:
                # Don't crash the whole loop on error
                print(f"❌ {self.config.bot_id} error in backlog_work_loop: {e}")
                self.status = BotStatus.ERROR
                self.current_task = None
                await asyncio.sleep(5)  # Wait before retrying

    async def assign_tasks(self, tasks: List[Dict]):
        """
        NEW: Receive batch of tasks from Foreman

        Args:
            tasks: List of task dictionaries
        """
        # Add to backlog
        self.backlog.extend(tasks)

        # Limit backlog size
        if len(self.backlog) > self.max_backlog_size:
            print(f"⚠️ {self.config.bot_id} backlog full, truncating to {self.max_backlog_size}")
            self.backlog = self.backlog[:self.max_backlog_size]

        print(f"📋 {self.config.bot_id} received {len(tasks)} tasks. Backlog now: {len(self.backlog)}")

    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task with error handling and help requests"""
        self.current_task = task
        self.status = BotStatus.WORKING
        start_time = time.time()

        try:
            # Load project-specific context - USE SEMANTIC SEARCH to limit size
            task_description = task.get("description", "")

            # Search for relevant stories instead of loading all 60
            relevant_stories = await self.knowledge_base.search_stories(
                query=task_description,
                n_results=3  # Only get 3 most relevant stories
            )

            # Build lightweight context from search results
            context = {
                "project_id": task.get("project_id", "default"),
                "relevant_stories": relevant_stories.get('documents', [])[:3] if relevant_stories else [],
                "story_count": 3
            }

            # Build prompt with context
            prompt = await self.build_prompt(task, context)

            # Try to complete task
            result = await self.process_with_retry(prompt, max_retries=2)

            if result.get("success"):
                self.status = BotStatus.IDLE
                self.metrics["tasks_completed"] += 1
                execution_time = time.time() - start_time
                self._update_avg_time(execution_time)

                # Store successful patterns for learning
                await self.knowledge_base.store_success(
                    bot_type=self.config.bot_type,
                    task=task,
                    result=result,
                    execution_time=execution_time
                )

                return {
                    "status": "completed",
                    "bot_id": self.config.bot_id,
                    "result": result,
                    "execution_time": execution_time
                }
            else:
                # Bot is stuck, request help
                return await self.request_help(task, result.get("error"))

        except Exception as e:
            self.status = BotStatus.ERROR
            self.metrics["tasks_failed"] += 1
            return await self.request_help(task, str(e))
        finally:
            self.current_task = None

    async def process_with_retry(self, prompt: str, max_retries: int = 2) -> Dict[str, Any]:
        """Process with the LLM with retry logic"""
        for attempt in range(max_retries):
            try:
                response = await self.call_llm(prompt)

                # Validate response
                if self.validate_response(response):
                    return {
                        "success": True,
                        "response": response,
                        "tokens": len(response.split())  # Approximate
                    }
                else:
                    if attempt < max_retries - 1:
                        # Adjust prompt and retry
                        prompt = self.refine_prompt(prompt, response)
                        continue
                    else:
                        return {
                            "success": False,
                            "error": "Invalid response after retries",
                            "last_response": response
                        }

            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    return {"success": False, "error": str(e)}

        return {"success": False, "error": "Max retries exceeded"}

    async def call_llm(self, prompt: str) -> str:
        """
        Call the LLM via APIClient (supports all providers)
        Falls back to Ollama if no API client available
        """
        model = self.config.model

        # Build messages with conversation history
        messages = self.conversation_history + [
            {"role": "user", "content": prompt}
        ]

        # Keep history manageable
        if len(messages) > 10:
            messages = messages[-10:]

        # Use API client if available
        if self.api_client:
            try:
                assistant_msg = await self.api_client.chat_completion(
                    model=model,
                    messages=messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )

                # Update conversation history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_msg})

                # Estimate tokens
                self.metrics["tokens_used"] += len(assistant_msg.split())

                return assistant_msg

            except Exception as e:
                print(f"⚠️ API call failed for {self.config.bot_id}: {e}")
                # Fall through to Ollama fallback

        # Fallback to Ollama if available
        if OLLAMA_AVAILABLE:
            try:
                response = ollama.chat(
                    model=model,
                    messages=messages,
                    options={
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens
                    }
                )

                assistant_msg = response['message']['content']

                # Update conversation history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_msg})

                # Track tokens
                self.metrics["tokens_used"] += response.get("eval_count", 0)

                return assistant_msg

            except Exception as e:
                print(f"⚠️ Ollama call failed for {self.config.bot_id}: {e}")
                raise Exception(f"No AI provider available for {self.config.bot_id}")

        else:
            raise Exception(f"No AI provider available for {self.config.bot_id}")

    async def request_help(self, task: Dict[str, Any], error: str) -> Dict[str, Any]:
        """Request help from a more capable bot or orchestrator"""
        self.status = BotStatus.WAITING_HELP
        self.metrics["help_requests"] += 1

        help_request = {
            "bot_id": self.config.bot_id,
            "bot_type": self.config.bot_type,
            "task_id": task.get("task_id"),
            "task": task,
            "error": error,
            "context": self.current_task,
            "conversation_history": self.conversation_history[-5:],
            "timestamp": time.time()
        }

        await self.help_queue.add(help_request)

        print(f"🆘 {self.config.bot_id} requested help: {error[:100]}")

        return {
            "status": "help_requested",
            "bot_id": self.config.bot_id,
            "help_request_id": help_request["task_id"]
        }

    def validate_response(self, response: str) -> bool:
        """Validate that the response is usable - override in subclasses"""
        return len(response) > 10 and response.strip() != ""

    def refine_prompt(self, original_prompt: str, failed_response: str) -> str:
        """Refine prompt after failed attempt"""
        return f"""{original_prompt}

Previous attempt failed with response: {failed_response[:200]}

Please try again with more detail and ensure the response is complete."""

    async def build_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build prompt with task and context - override in subclasses"""
        return f"""Task: {task.get('description')}

Context: {json.dumps(context, indent=2)}

Please complete this task."""

    @abstractmethod
    async def do_continuous_work(self):
        """Override for always-running bots"""
        pass

    def _update_avg_time(self, new_time: float):
        """Update rolling average response time"""
        n = self.metrics["tasks_completed"]
        current_avg = self.metrics["avg_response_time"]
        self.metrics["avg_response_time"] = ((n - 1) * current_avg + new_time) / n

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status for monitoring"""
        return {
            "bot_id": self.config.bot_id,
            "bot_type": self.config.bot_type,
            "status": self.status.value,
            "current_task": self.current_task.get("id") if self.current_task and isinstance(self.current_task, dict) else None,
            "backlog_size": len(self.backlog),
            "completed_count": len(self.completed_tasks),
            "capacity": "idle" if len(self.backlog) == 0 else "busy",
            "metrics": self.metrics,
            "model": self.config.model,
            "specialty": self.config.specialty
        }
