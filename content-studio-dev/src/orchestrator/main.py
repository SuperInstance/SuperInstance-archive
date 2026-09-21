# src/orchestrator/main.py

import asyncio
import os
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import anthropic
import json
from datetime import datetime

from .task_manager import TaskManager
from ..communication.message_bus import MessageBus
from ..communication.help_queue import HelpQueue
from ..knowledge.knowledge_base import KnowledgeBase
from ..lora.lora_manager import LoRAManager
from ..bots.content_bots import (
    ScriptWriterBot, ImagePrompterBot, DialogueFormatterBot,
    StoryIndexerBot, AssetMonitorBot, MetadataGeneratorBot, QAContentBot
)
from ..bots.base_bot import BotConfig

app = FastAPI(title="Loopless Content Studio - Multi-Agent System")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ContentStudioOrchestrator:
    """Master orchestrator for content creation using Claude API"""

    def __init__(self):
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.task_manager = TaskManager()
        self.message_bus = MessageBus()
        self.help_queue = HelpQueue()
        self.knowledge_base = KnowledgeBase()
        self.lora_manager = LoRAManager()
        self.bots: Dict[str, Any] = {}
        self.active_websockets: List[WebSocket] = []
        self.bootcamp_content = None

    async def initialize(self):
        """Initialize the content studio system"""
        print("🚀 Initializing Loopless Content Studio...")

        # Load bootcamp file
        self.bootcamp_content = await self.load_bootcamp()

        # Initialize bot pool
        await self.create_bot_pool()

        # Start always-running bots
        await self.start_continuous_bots()

        # Start help queue monitor
        asyncio.create_task(self.monitor_help_queue())

        print("✅ Content Studio initialized successfully!")
        print(f"📊 {len(self.bots)} bots ready")

    async def load_bootcamp(self) -> str:
        """Load bootcamp training file"""
        try:
            with open("config/content_bootcamp.md", "r") as f:
                content = f.read()
            print("📚 Content bootcamp file loaded")
            return content
        except FileNotFoundError:
            print("⚠️ Bootcamp file not found at config/content_bootcamp.md")
            return ""

    async def create_bot_pool(self):
        """Create all specialized content creation bots"""
        # Load from YAML config
        import yaml
        try:
            with open("config/content_bot_configs.yaml", "r") as f:
                config_data = yaml.safe_load(f)

            bot_classes = {
                "script_writer": ScriptWriterBot,
                "image_prompt": ImagePrompterBot,
                "dialogue": DialogueFormatterBot,
                "story_indexer": StoryIndexerBot,
                "asset_monitor": AssetMonitorBot,
                "metadata": MetadataGeneratorBot,
                "quality_assurance": QAContentBot
            }

            for bot_cfg in config_data.get('bots', []):
                bot_type = bot_cfg['type']
                if bot_type in bot_classes:
                    config = BotConfig(
                        bot_id=bot_cfg['id'],
                        bot_type=bot_type,
                        model=bot_cfg['model'],
                        specialty=bot_cfg.get('specialty', ''),
                        max_tokens=bot_cfg.get('max_tokens', 2048),
                        temperature=bot_cfg.get('temperature', 0.7),
                        always_running=bot_cfg.get('always_running', False)
                    )

                    bot_class = bot_classes[bot_type]
                    bot = bot_class(
                        config,
                        self.help_queue,
                        self.message_bus,
                        self.knowledge_base
                    )
                    self.bots[config.bot_id] = bot
                    print(f" ✓ Created {config.bot_id} ({bot_type})")

        except Exception as e:
            print(f"❌ Error loading bot configs: {e}")
            print("Creating default bot pool...")
            await self.create_default_bots()

    async def create_default_bots(self):
        """Create default bots if config fails"""
        bot_configs = [
            BotConfig("script_writer_1", "script_writer", "llama3.2:3b",
                      specialty="Video script adaptation", max_tokens=4096),
            BotConfig("image_prompter_1", "image_prompt", "llama3.2:3b",
                      specialty="Image prompt generation"),
            BotConfig("story_indexer_1", "story_indexer", "llama3.2:1b",
                      specialty="Story indexing", always_running=True),
            BotConfig("asset_monitor_1", "asset_monitor", "llama3.2:1b",
                      specialty="Asset tracking", always_running=True),
        ]

        bot_classes = {
            "script_writer": ScriptWriterBot,
            "image_prompt": ImagePrompterBot,
            "story_indexer": StoryIndexerBot,
            "asset_monitor": AssetMonitorBot,
        }

        for config in bot_configs:
            bot_class = bot_classes[config.bot_type]
            bot = bot_class(config, self.help_queue, self.message_bus, self.knowledge_base)
            self.bots[config.bot_id] = bot
            print(f" ✓ Created {config.bot_id}")

    async def start_continuous_bots(self):
        """Start bots that run continuously"""
        for bot in self.bots.values():
            await bot.start()

    async def process_user_request(self, request: str, user_id: str = "default") -> str:
        """Process user request through Claude with full context"""

        # Get user-specific context
        user_context = await self.lora_manager.get_user_context(user_id)

        # Get current project context
        project_context = await self.knowledge_base.get_project_context()

        # Get bot statuses
        bot_statuses = {bot_id: bot.get_status()
                        for bot_id, bot in self.bots.items()}

        # Build comprehensive prompt for Claude
        prompt = f"""{self.bootcamp_content}

## Current System State
{json.dumps({
    'bot_statuses': bot_statuses,
    'pending_tasks': self.task_manager.get_queue_status(),
    'help_requests': len(self.help_queue.queue)
}, indent=2)}

## User Context
{json.dumps(user_context, indent=2)}

## Project Context
{json.dumps(project_context, indent=2)}

## User Request
{request}

## Your Task
1. Analyze the request
2. Break it down into bot-appropriate subtasks
3. Assign tasks to suitable bots
4. Provide response to user about what's happening

Respond with JSON:
{{
  "analysis": "Brief analysis of request",
  "tasks": [
    {{"bot_type": "...", "description": "...", "priority": "high|medium|low", "data": {{}}}},
    ...
  ],
  "user_message": "What you're telling the user"
}}
"""

        try:
            # Call Claude API
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Parse response
            plan = json.loads(response_text.strip().strip('```json').strip('```'))

            # Create and assign tasks
            for task_def in plan.get('tasks', []):
                task = await self.task_manager.create_task(
                    bot_type=task_def['bot_type'],
                    description=task_def['description'],
                    priority=task_def.get('priority', 'medium'),
                    user_id=user_id,
                    metadata=task_def.get('data', {})
                )

                # Find available bot of this type
                bot = self.find_available_bot(task_def['bot_type'])
                if bot:
                    await self.message_bus.assign_task(bot.config.bot_id, task)
                    print(f"📋 Assigned task {task['task_id']} to {bot.config.bot_id}")

            # Broadcast updates
            await self.broadcast_status_update()

            return plan.get('user_message', 'Tasks assigned to bot team!')

        except json.JSONDecodeError:
            return response_text
        except Exception as e:
            print(f"❌ Error processing request: {e}")
            return f"Error processing request: {str(e)}"

    async def monitor_help_queue(self):
        """Monitor and handle help requests from bots"""
        while True:
            if not self.help_queue.is_empty():
                help_request = await self.help_queue.get()

                print(f"🆘 Processing help request from {help_request['bot_id']}")

                # Try to handle with another bot first
                resolved = await self.try_bot_resolution(help_request)

                if not resolved:
                    # Escalate to Claude
                    await self.escalate_to_claude(help_request)

            await asyncio.sleep(2)

    async def try_bot_resolution(self, help_request: Dict[str, Any]) -> bool:
        """Try to resolve help request with a more capable bot"""
        requesting_bot_type = help_request['bot_type']

        # Find a more capable bot of similar type
        for bot in self.bots.values():
            if (bot.config.bot_type == requesting_bot_type and
                    bot.config.bot_id != help_request['bot_id'] and
                    "3b" in bot.config.model.lower()):

                task = help_request['task']
                task['context'] = help_request['context']
                task['previous_attempts'] = help_request.get('conversation_history', [])

                result = await bot.execute_task(task)

                if result['status'] == 'completed':
                    print(f"✅ Help resolved by {bot.config.bot_id}")
                    return True

        return False

    async def escalate_to_claude(self, help_request: Dict[str, Any]):
        """Escalate stuck task to Claude"""
        print(f"⬆️ Escalating to Claude: {help_request['error'][:100]}")

        prompt = f"""A bot needs help with this content creation task:

Bot: {help_request['bot_id']} ({help_request['bot_type']})
Task: {help_request['task']}
Error: {help_request['error']}

Context:
{json.dumps(help_request.get('context', {}), indent=2)}

Please either:
1. Provide specific guidance to help the bot succeed
2. Complete the task yourself if it's too complex for bots
3. Suggest a different approach

Respond with JSON:
{{
  "action": "guide|complete|redesign",
  "guidance": "...",
  "solution": "...",
  "approach": "..."
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            resolution = json.loads(response.content[0].text.strip().strip('```json').strip('```'))
            print(f"✓ Claude resolved with action: {resolution.get('action')}")

        except Exception as e:
            print(f"❌ Error in Claude escalation: {e}")

    def find_available_bot(self, bot_type: str):
        """Find an available bot of given type"""
        for bot in self.bots.values():
            if bot.config.bot_type == bot_type and bot.status.value == "idle":
                return bot
        # Return any bot of that type if none idle
        for bot in self.bots.values():
            if bot.config.bot_type == bot_type:
                return bot
        return None

    async def broadcast_status_update(self):
        """Broadcast status to all connected websockets"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'bots': {bot_id: bot.get_status()
                     for bot_id, bot in self.bots.items()},
            'queue': self.task_manager.get_queue_status(),
            'help_requests': len(self.help_queue.queue)
        }

        for ws in self.active_websockets:
            try:
                await ws.send_json(status)
            except:
                self.active_websockets.remove(ws)


# Global orchestrator instance
orchestrator = ContentStudioOrchestrator()


@app.on_event("startup")
async def startup():
    await orchestrator.initialize()


@app.post("/api/request")
async def handle_request(request: Dict[str, Any]):
    """Handle user request"""
    user_request = request.get("message", "")
    user_id = request.get("user_id", "default")

    response = await orchestrator.process_user_request(user_request, user_id)

    return {"response": response}


@app.get("/api/status")
async def get_status():
    """Get system status"""
    return {
        'bots': {bot_id: bot.get_status()
                 for bot_id, bot in orchestrator.bots.items()},
        'queue': orchestrator.task_manager.get_queue_status(),
        'help_requests': len(orchestrator.help_queue.queue)
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    orchestrator.active_websockets.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except:
        orchestrator.active_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
