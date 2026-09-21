# src/orchestrator/orchestrator_v2.py
"""
Enhanced Orchestrator with Foreman pattern and parallel execution
"""

import asyncio
import os
from typing import Dict, Any, List
from datetime import datetime
import anthropic
import json
from ..utils.json_parser import extract_json_from_text, safe_json_parse

from .task_manager import TaskManager
from ..communication.message_bus import MessageBus
from ..communication.help_queue import HelpQueue
from ..knowledge.knowledge_base import KnowledgeBase
from ..lora.lora_manager import LoRAManager
from ..resources.resource_manager import ResourceManager
from ..api.api_client import APIClient
from ..bots.foreman_bot import ForemanBot
from ..bots.content_bots import (
    ScriptWriterBot, ImagePrompterBot, DialogueFormatterBot,
    StoryIndexerBot, AssetMonitorBot, MetadataGeneratorBot, QAContentBot
)
from ..bots.research_bots import (
    BackgroundResearcherBot, SummarizerBot, ContextGathererBot, DataExtractorBot
)
from ..bots.base_bot import BotConfig


class ContentStudioOrchestrator:
    """
    Master orchestrator for multi-agent content production
    Now with Foreman pattern for parallel execution
    """

    def __init__(self):
        # API client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.claude = anthropic.Anthropic(api_key=api_key)
        else:
            self.claude = None
            print("⚠️ No Anthropic API key - Orchestrator will use limited mode")

        # Core managers
        self.task_manager = TaskManager()
        self.message_bus = MessageBus()
        self.help_queue = HelpQueue()
        self.knowledge_base = KnowledgeBase()
        self.lora_manager = LoRAManager()

        # NEW: Resource manager for CPU/GPU allocation
        self.resource_manager = ResourceManager(cpu_cores=8, gpu_available=True)

        # NEW: API client for all bots
        self.api_client = APIClient(resource_manager=self.resource_manager)

        # Bot pool
        self.bots: Dict[str, Any] = {}

        # NEW: Foreman bot for workload management
        self.foreman = None

        # Active project tracking
        self.current_project = None

    async def initialize(self):
        """Initialize the entire system"""
        print("\n" + "="*60)
        print("🚀 INITIALIZING LOOPLESS CONTENT STUDIO")
        print("="*60 + "\n")

        print("Step 1: Creating bot pool...")
        await self.create_bot_pool()

        print("\nStep 2: Initializing Foreman...")
        self.foreman = ForemanBot(
            agent_pool=self.bots,
            resource_manager=self.resource_manager,
            message_bus=self.message_bus,
            knowledge_base=self.knowledge_base
        )

        print("\nStep 3: Starting bot workers...")
        await self.start_all_bots()

        print("\nStep 4: Starting help queue monitor...")
        asyncio.create_task(self.monitor_help_queue())

        print("\n" + "="*60)
        print("✅ CONTENT STUDIO READY")
        print("="*60)
        print(f"\n📊 System Status:")
        print(f"  • Content agents: {sum(1 for b in self.bots.values() if not b.config.always_running)}")
        print(f"  • Background agents: {sum(1 for b in self.bots.values() if 'research' in b.config.bot_type or 'summar' in b.config.bot_type)}")
        print(f"  • Always-running: {sum(1 for b in self.bots.values() if b.config.always_running)}")
        print(f"  • Total bots: {len(self.bots)}")
        print(f"  • CPU cores: {self.resource_manager.cpu_cores}")
        print(f"  • GPU: {'RTX 4050 available' if self.resource_manager.gpu_available else 'Not available'}")
        print(f"\n🎯 Ready to process projects!\n")

    async def create_bot_pool(self):
        """Create all specialized bots"""

        # Main content creation agents
        main_agents = [
            BotConfig("script_writer_1", "script_writer", "gpt-4o-mini",
                     specialty="Video script adaptation", max_tokens=4096),
            BotConfig("script_writer_2", "script_writer", "gpt-4o-mini",
                     specialty="Dialogue formatting", max_tokens=3000),
            BotConfig("image_prompter_1", "image_prompter", "gpt-4o-mini",
                     specialty="Character prompts"),
            BotConfig("image_prompter_2", "image_prompter", "gpt-4o-mini",
                     specialty="Background prompts"),
            BotConfig("dialogue_formatter_1", "dialogue_formatter", "gpt-4o-mini",
                     specialty="Voice synthesis formatting"),
            BotConfig("qa_content_1", "qa_content", "gpt-4o-mini",
                     specialty="Quality assurance"),
            BotConfig("metadata_gen_1", "metadata_gen", "gpt-4o-mini",
                     specialty="Metadata generation"),
        ]

        # Background research agents (use cheap/free Groq models)
        research_agents = [
            BotConfig("researcher_1", "researcher", "llama-3.1-8b-instant",
                     specialty="Character analysis"),
            BotConfig("researcher_2", "researcher", "llama-3.1-8b-instant",
                     specialty="Scene breakdown"),
            BotConfig("summarizer_1", "summarizer", "llama-3.1-8b-instant",
                     specialty="Content summarization"),
            BotConfig("context_gatherer_1", "context_gatherer", "llama-3.1-8b-instant",
                     specialty="Context gathering"),
            BotConfig("data_extractor_1", "data_extractor", "llama-3.1-8b-instant",
                     specialty="Data extraction"),
        ]

        # Always-running monitoring agents
        monitor_agents = [
            BotConfig("story_indexer_1", "story_indexer", "llama-3.1-8b-instant",
                     specialty="Story indexing", always_running=True),
            BotConfig("asset_monitor_1", "asset_monitor", "llama-3.1-8b-instant",
                     specialty="Asset tracking", always_running=True),
        ]

        # Bot class mapping
        bot_classes = {
            "script_writer": ScriptWriterBot,
            "image_prompter": ImagePrompterBot,
            "dialogue_formatter": DialogueFormatterBot,
            "qa_content": QAContentBot,
            "metadata_gen": MetadataGeneratorBot,
            "researcher": BackgroundResearcherBot,
            "summarizer": SummarizerBot,
            "context_gatherer": ContextGathererBot,
            "data_extractor": DataExtractorBot,
            "story_indexer": StoryIndexerBot,
            "asset_monitor": AssetMonitorBot,
        }

        # Create all bots
        all_configs = main_agents + research_agents + monitor_agents

        for config in all_configs:
            bot_class = bot_classes.get(config.bot_type)
            if bot_class:
                bot = bot_class(
                    config,
                    self.help_queue,
                    self.message_bus,
                    self.knowledge_base,
                    self.api_client  # Pass API client to all bots
                )
                self.bots[config.bot_id] = bot
                print(f"  ✓ Created {config.bot_id} ({config.bot_type})")

    async def start_all_bots(self):
        """Start all bot workers"""
        for bot in self.bots.values():
            await bot.start()

    async def process_user_request(self, request: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Process high-level user request

        Orchestrator receives request, creates project plan, hands off to Foreman
        """
        print(f"\n{'='*60}")
        print(f"📨 USER REQUEST RECEIVED")
        print(f"{'='*60}")
        print(f"User: {user_id}")
        print(f"Request: {request}")
        print(f"{'='*60}\n")

        if not self.claude:
            return {
                "error": "Orchestrator requires Anthropic API key",
                "message": "Please set ANTHROPIC_API_KEY in .env file"
            }

        try:
            # Step 1: Analyze request and create project plan
            print("🧠 Orchestrator analyzing request...")
            project_plan = await self._create_project_plan(request, user_id)

            print(f"✓ Project plan created: {project_plan.get('project', 'Unnamed')}")

            # Step 2: Hand off to Foreman
            print("\n👷 Handing off to Foreman...")
            self.current_project = project_plan
            foreman_result = await self.foreman.start_project(project_plan)

            return {
                "status": "project_started",
                "project": project_plan.get('project'),
                "total_tasks": foreman_result.get('total_tasks', 0),
                "agents": foreman_result.get('agents', 0),
                "message": f"Project '{project_plan.get('project')}' is now in progress. "
                          f"{foreman_result.get('total_tasks', 0)} tasks assigned to "
                          f"{foreman_result.get('agents', 0)} agents."
            }

        except Exception as e:
            print(f"❌ Error processing request: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def _create_project_plan(self, request: str, user_id: str) -> Dict[str, Any]:
        """
        Use Claude to create high-level project plan

        Returns project plan dict with phases and success criteria
        """
        # Get context
        user_context = await self.lora_manager.get_user_context(user_id)
        project_context = await self.knowledge_base.get_project_context()

        prompt = f"""You are the Orchestrator for a multi-agent content production system.

USER REQUEST:
{request}

SYSTEM CONTEXT:
- Available stories: 60 main saga stories (v3 versions recommended)
- Production capabilities: Scripts, images, audio, video, metadata
- Multi-platform: YouTube, podcasts, social media

YOUR TASK:
Create a high-level project plan that the Foreman will break into specific tasks.

Provide plan as JSON:
{{
  "project": "Short project identifier (e.g., 'episode_1_youtube')",
  "goal": "Clear goal statement",
  "phases": [
    "Phase 1: Research and indexing",
    "Phase 2: Script writing",
    "Phase 3: Visual asset creation",
    "Phase 4: Audio production",
    "Phase 5: Assembly and QA",
    "Phase 6: Publishing"
  ],
  "success_criteria": {{
    "duration_target": "28 minutes",
    "quality_standard": "broadcast quality",
    "accuracy_target": "95%",
    "cost_target": "$50"
  }},
  "priority": "high",
  "deadline": "none"
}}

Be specific and actionable.
"""

        response = self.claude.messages.create(
            model="claude-opus-4-20250514",  # Use Opus for strategic planning
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text

        # Extract JSON using robust parser
        project_plan = extract_json_from_text(response_text)

        if not project_plan:
            # Fallback to simple plan if JSON parsing fails
            print("⚠️ Could not parse Claude response, using simple plan")
            project_plan = {
                "project": "content_production",
                "goal": request,
                "phases": [
                    "Research and preparation",
                    "Content creation",
                    "Quality assurance",
                    "Publishing"
                ],
                "success_criteria": {"quality": "high"},
                "priority": "medium"
            }

        return project_plan

    async def monitor_help_queue(self):
        """Monitor and handle help requests from stuck bots"""
        while True:
            if not self.help_queue.is_empty():
                help_request = await self.help_queue.get()

                print(f"\n🆘 HELP REQUEST from {help_request['bot_id']}")

                # Try to resolve with Foreman first
                # If Foreman can't help, escalate to Orchestrator
                if self.claude:
                    await self._escalate_to_orchestrator(help_request)

            await asyncio.sleep(5)

    async def _escalate_to_orchestrator(self, help_request: Dict[str, Any]):
        """Escalate complex issues to Orchestrator (uses expensive Opus model)"""
        print(f"⬆️ Escalating to Orchestrator (Claude Opus)")

        prompt = f"""A bot needs help with a stuck task.

BOT: {help_request['bot_id']} ({help_request['bot_type']})
TASK: {help_request['task']}
ERROR: {help_request['error']}

Your options:
1. Provide specific guidance to help the bot succeed
2. Complete the task yourself if it's too complex
3. Recommend a different approach

Respond with JSON:
{{
  "action": "guide|complete|redesign",
  "solution": "Your solution or guidance",
  "reasoning": "Why you chose this approach"
}}
"""

        try:
            response = self.claude.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )

            resolution_text = response.content[0].text

            # Extract JSON using robust parser
            resolution = extract_json_from_text(resolution_text)

            if not resolution:
                resolution = {"action": "guide", "solution": resolution_text}

            print(f"✓ Orchestrator resolved: {resolution.get('action')}")

            # TODO: Apply resolution to help the bot

        except Exception as e:
            print(f"❌ Error in Orchestrator escalation: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "orchestrator": {
                "ready": True,
                "current_project": self.current_project.get('project') if self.current_project else None
            },
            "foreman": self.foreman.get_status() if self.foreman else {"status": "not_initialized"},
            "resources": self.resource_manager.get_status(),
            "bots": {
                bot_id: bot.get_status()
                for bot_id, bot in self.bots.items()
            },
            "help_queue_size": len(self.help_queue.queue) if hasattr(self.help_queue, 'queue') else 0
        }
