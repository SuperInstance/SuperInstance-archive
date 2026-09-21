# src/bots/foreman_bot.py
"""
Foreman Bot - Workload Manager
Breaks down projects into tasks and keeps agents busy
"""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import anthropic
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.utils.json_parser import extract_json_from_text, safe_json_parse


class ForemanBot:
    """Manages agent workload distribution and monitoring"""

    def __init__(self, agent_pool: Dict, resource_manager, message_bus, knowledge_base):
        """
        Initialize the Foreman

        Args:
            agent_pool: Dict of all available agents {agent_id: agent_instance}
            resource_manager: ResourceManager instance for CPU/GPU allocation
            message_bus: MessageBus for communication
            knowledge_base: KnowledgeBase for project context
        """
        self.agent_pool = agent_pool
        self.resource_manager = resource_manager
        self.message_bus = message_bus
        self.knowledge_base = knowledge_base

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.claude = anthropic.Anthropic(api_key=api_key)
        else:
            self.claude = None
            print("⚠️ Foreman: No Anthropic API key - will use fallback mode")

        # Project tracking
        self.active_project = None
        self.all_tasks = []
        self.completed_task_ids = set()
        self.failed_task_ids = set()

        # Monitoring
        self.start_time = None
        self.last_status_time = 0
        self.status_interval = 30  # Report every 30 seconds

    async def start_project(self, project_plan: Dict) -> Dict:
        """
        Start managing a project

        Args:
            project_plan: Dict with 'project', 'goal', 'phases', 'success_criteria'

        Returns:
            Dict with project status
        """
        self.active_project = project_plan
        self.start_time = time.time()

        print(f"\n{'='*60}")
        print(f"👷 FOREMAN: Starting project '{project_plan['project']}'")
        print(f"{'='*60}\n")

        try:
            # Step 1: Decompose project into tasks
            print("📋 Decomposing project into tasks...")
            all_tasks = await self.decompose_project(project_plan)
            self.all_tasks = all_tasks

            print(f"✓ Created {len(all_tasks)} tasks")

            # Step 2: Distribute tasks to agent backlogs
            print("\n📦 Distributing tasks to agents...")
            await self.distribute_tasks(all_tasks)

            print(f"✓ Tasks distributed to {len(self.agent_pool)} agents")

            # Step 3: Start monitoring
            print("\n👀 Starting project monitoring...\n")
            asyncio.create_task(self.monitor_project())

            return {
                "status": "started",
                "project": project_plan['project'],
                "total_tasks": len(all_tasks),
                "agents": len(self.agent_pool),
                "start_time": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ Error starting project: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def decompose_project(self, project_plan: Dict) -> List[Dict]:
        """
        Break project into 100-200 small tasks using Claude

        If no API key, uses predefined task templates
        """
        if self.claude:
            return await self._decompose_with_claude(project_plan)
        else:
            return await self._decompose_with_templates(project_plan)

    async def _decompose_with_claude(self, project_plan: Dict) -> List[Dict]:
        """Decompose using Claude API"""

        # Get available agent types
        agent_types = list(set(agent.config.bot_type for agent in self.agent_pool.values()))

        prompt = f"""You are a project foreman managing a content production team.

PROJECT DETAILS:
Goal: {project_plan['goal']}
Phases: {json.dumps(project_plan.get('phases', []), indent=2)}

AVAILABLE AGENT TYPES:
{json.dumps(agent_types, indent=2)}

Agent capabilities:
- script_writer: Adapts stories into scripts with scenes and dialogue
- image_prompter: Creates detailed prompts for AI image generation
- dialogue_formatter: Formats dialogue for voice synthesis with emotion tags
- researcher: Gathers information, summarizes content, extracts data
- qa_content: Reviews quality, checks consistency and accuracy
- metadata_gen: Creates titles, descriptions, tags for publishing
- story_indexer: Maintains searchable database of all story content
- asset_monitor: Tracks generated assets and manages inventory

YOUR TASK:
Break this project into 100-200 small, specific tasks that agents can complete independently.

Each task should:
1. Be completable in 1-5 minutes
2. Have clear success criteria
3. Specify which agent type should handle it
4. List any dependencies (other tasks that must complete first)
5. Include all necessary context/data

IMPORTANT GUIDELINES:
- Start with research tasks (indexing, gathering info)
- Then planning tasks (scene breakdown, character lists)
- Then creation tasks (writing, prompting, formatting)
- Then review tasks (QA, refinement)
- Finally publication tasks (metadata, packaging)

Return as JSON array (be thorough - aim for 150+ tasks):
[
  {{
    "id": "task_001",
    "agent_type": "researcher",
    "description": "Index Story_01_v3.md and extract metadata",
    "dependencies": [],
    "estimated_minutes": 2,
    "priority": "high",
    "data": {{
      "story_file": "/home/activeloguser/Story_01_The_Knock_That_Changes_Everything_v3.md"
    }}
  }},
  {{
    "id": "task_002",
    "agent_type": "researcher",
    "description": "Extract list of all characters from Story 01",
    "dependencies": ["task_001"],
    "estimated_minutes": 3,
    "priority": "high",
    "data": {{}}
  }},
  ... (continue with 150+ tasks)
]

Make tasks granular and specific. Think about EVERY step needed.
"""

        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.content[0].text

            # Extract JSON from response using robust parser
            tasks = extract_json_from_text(response_text)

            if not tasks or not isinstance(tasks, list):
                raise ValueError("Could not extract valid task list from Claude response")

            # Validate and enrich tasks
            for i, task in enumerate(tasks):
                if 'id' not in task:
                    task['id'] = f"task_{i+1:03d}"
                if 'status' not in task:
                    task['status'] = 'pending'
                if 'assigned_to' not in task:
                    task['assigned_to'] = None
                if 'result' not in task:
                    task['result'] = None

            return tasks

        except Exception as e:
            print(f"⚠️ Error using Claude for decomposition: {e}")
            print("Falling back to template-based decomposition...")
            return await self._decompose_with_templates(project_plan)

    async def _decompose_with_templates(self, project_plan: Dict) -> List[Dict]:
        """
        Fallback: Generate tasks using predefined templates

        This is used when no API key is available
        """
        tasks = []
        task_id = 1

        # Determine project type
        project_goal = project_plan.get('goal', '').lower()

        if 'episode' in project_goal or 'script' in project_goal:
            # Episode production tasks
            story_num = 1  # Extract from goal if possible

            # Phase 1: Research (10 tasks)
            tasks.append({
                "id": f"task_{task_id:03d}",
                "agent_type": "story_indexer",
                "description": f"Index Story_{story_num:02d}_v3.md",
                "dependencies": [],
                "estimated_minutes": 2,
                "priority": "high",
                "data": {"story_number": story_num},
                "status": "pending",
                "assigned_to": None
            })
            task_id += 1

            tasks.append({
                "id": f"task_{task_id:03d}",
                "agent_type": "researcher",
                "description": "Extract all character names and descriptions",
                "dependencies": [f"task_001"],
                "estimated_minutes": 3,
                "priority": "high",
                "data": {"story_number": story_num},
                "status": "pending",
                "assigned_to": None
            })
            task_id += 1

            tasks.append({
                "id": f"task_{task_id:03d}",
                "agent_type": "researcher",
                "description": "List all locations and settings",
                "dependencies": [f"task_001"],
                "estimated_minutes": 3,
                "priority": "high",
                "data": {"story_number": story_num},
                "status": "pending",
                "assigned_to": None
            })
            task_id += 1

            tasks.append({
                "id": f"task_{task_id:03d}",
                "agent_type": "researcher",
                "description": "Identify key scenes and story beats",
                "dependencies": [f"task_001"],
                "estimated_minutes": 4,
                "priority": "high",
                "data": {"story_number": story_num},
                "status": "pending",
                "assigned_to": None
            })
            task_id += 1

            # Phase 2: Script Writing (15 tasks - one per scene)
            for scene_num in range(1, 13):  # 12 scenes typical
                tasks.append({
                    "id": f"task_{task_id:03d}",
                    "agent_type": "script_writer",
                    "description": f"Adapt Scene {scene_num} to video script",
                    "dependencies": [f"task_001", f"task_002", f"task_003", f"task_004"],
                    "estimated_minutes": 5,
                    "priority": "medium",
                    "data": {
                        "story_number": story_num,
                        "scene_number": scene_num,
                        "format": "youtube_episode"
                    },
                    "status": "pending",
                    "assigned_to": None
                })
                task_id += 1

            # Phase 3: Visual Prompts (30 tasks)
            # Character prompts
            characters = ["Casey", "Anna", "Finn", "Michele", "SuperInstance"]
            expressions = ["neutral", "happy", "concerned", "excited", "thoughtful"]

            for char in characters:
                for expr in expressions:
                    tasks.append({
                        "id": f"task_{task_id:03d}",
                        "agent_type": "image_prompter",
                        "description": f"Create prompt: {char} - {expr} expression",
                        "dependencies": [f"task_002"],
                        "estimated_minutes": 2,
                        "priority": "medium",
                        "data": {
                            "character": char,
                            "expression": expr,
                            "type": "character"
                        },
                        "status": "pending",
                        "assigned_to": None
                    })
                    task_id += 1

            # Background prompts (10 locations)
            locations = [
                "Boat interior bedroom",
                "Boat deck at sunset",
                "Tavern cozy interior",
                "Dock with boats",
                "Ocean horizon",
                "Dance studio",
                "Research station",
                "Holographic interface",
                "Night sky with stars",
                "Underwater scene"
            ]

            for location in locations:
                tasks.append({
                    "id": f"task_{task_id:03d}",
                    "agent_type": "image_prompter",
                    "description": f"Create prompt: {location}",
                    "dependencies": [f"task_003"],
                    "estimated_minutes": 3,
                    "priority": "medium",
                    "data": {
                        "location": location,
                        "type": "background"
                    },
                    "status": "pending",
                    "assigned_to": None
                })
                task_id += 1

            # Phase 4: Dialogue Formatting (12 tasks)
            for scene_num in range(1, 13):
                base_task_id = 4 + scene_num
                tasks.append({
                    "id": f"task_{task_id:03d}",
                    "agent_type": "dialogue_formatter",
                    "description": f"Format dialogue for Scene {scene_num}",
                    "dependencies": [f"task_{base_task_id:03d}"],
                    "estimated_minutes": 3,
                    "priority": "low",
                    "data": {
                        "scene_number": scene_num
                    },
                    "status": "pending",
                    "assigned_to": None
                })
                task_id += 1

            # Phase 5: QA (15 tasks)
            for scene_num in range(1, 13):
                base_task_id = 4 + scene_num
                tasks.append({
                    "id": f"task_{task_id:03d}",
                    "agent_type": "qa_content",
                    "description": f"Review Scene {scene_num} script quality",
                    "dependencies": [f"task_{base_task_id:03d}"],
                    "estimated_minutes": 4,
                    "priority": "low",
                    "data": {
                        "scene_number": scene_num,
                        "check_type": "script_accuracy"
                    },
                    "status": "pending",
                    "assigned_to": None
                })
                task_id += 1

            # Phase 6: Metadata (5 tasks)
            tasks.append({
                "id": f"task_{task_id:03d}",
                "agent_type": "metadata_gen",
                "description": "Generate YouTube title and description",
                "dependencies": [f"task_001"],
                "estimated_minutes": 3,
                "priority": "low",
                "data": {
                    "platform": "youtube",
                    "episode_number": story_num
                },
                "status": "pending",
                "assigned_to": None
            })
            task_id += 1

            tasks.append({
                "id": f"task_{task_id:03d}",
                "agent_type": "metadata_gen",
                "description": "Generate SEO tags and keywords",
                "dependencies": [f"task_{task_id-1:03d}"],
                "estimated_minutes": 2,
                "priority": "low",
                "data": {
                    "platform": "youtube",
                    "episode_number": story_num
                },
                "status": "pending",
                "assigned_to": None
            })
            task_id += 1

        else:
            # Generic project tasks
            print("⚠️ Unknown project type - generating minimal task set")
            tasks.append({
                "id": f"task_001",
                "agent_type": "researcher",
                "description": "Analyze project requirements",
                "dependencies": [],
                "estimated_minutes": 5,
                "priority": "high",
                "data": {},
                "status": "pending",
                "assigned_to": None
            })

        print(f"✓ Generated {len(tasks)} tasks from templates")
        return tasks

    async def distribute_tasks(self, tasks: List[Dict]):
        """
        Distribute tasks to agent backlogs based on agent type
        """
        # Group tasks by agent type
        tasks_by_type = {}
        for task in tasks:
            agent_type = task['agent_type']
            if agent_type not in tasks_by_type:
                tasks_by_type[agent_type] = []
            tasks_by_type[agent_type].append(task)

        # Distribute to agents
        for agent_type, type_tasks in tasks_by_type.items():
            # Find all agents of this type
            matching_agents = [
                agent for agent in self.agent_pool.values()
                if agent.config.bot_type == agent_type
            ]

            if not matching_agents:
                print(f"  ⚠️ No agents available for type '{agent_type}' ({len(type_tasks)} tasks)")
                # Store for later or escalate
                continue

            # Distribute evenly
            tasks_per_agent = len(type_tasks) // len(matching_agents)
            remainder = len(type_tasks) % len(matching_agents)

            start_idx = 0
            for i, agent in enumerate(matching_agents):
                # Give remainder tasks to first few agents
                agent_task_count = tasks_per_agent + (1 if i < remainder else 0)
                end_idx = start_idx + agent_task_count

                agent_tasks = type_tasks[start_idx:end_idx]

                if agent_tasks:
                    await agent.assign_tasks(agent_tasks)
                    print(f"  ✓ {agent.config.bot_id}: {len(agent_tasks)} tasks")

                start_idx = end_idx

    async def monitor_project(self):
        """
        Continuously monitor project progress and manage workload
        """
        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            # Update completion status
            for agent in self.agent_pool.values():
                status = agent.get_status()
                for completed in agent.completed_tasks:
                    # Safety check: completed['task'] might be None
                    task = completed.get('task')
                    if task and isinstance(task, dict):
                        task_id = task.get('id')
                        if task_id and task_id not in self.completed_task_ids:
                            self.completed_task_ids.add(task_id)

            # Periodic status report
            current_time = time.time()
            if current_time - self.last_status_time >= self.status_interval:
                await self.report_status()
                self.last_status_time = current_time

            # Check if project is complete
            total_tasks = len(self.all_tasks)
            completed_tasks = len(self.completed_task_ids)

            if completed_tasks >= total_tasks and total_tasks > 0:
                await self.project_complete()
                break

            # Check for idle agents and rebalance if needed
            await self.rebalance_workload()

    async def rebalance_workload(self):
        """
        Check for idle agents or unbalanced workload and rebalance
        """
        idle_agents = []
        busy_agents = []

        for agent in self.agent_pool.values():
            status = agent.get_status()
            if status['capacity'] == 'idle':
                idle_agents.append(agent)
            elif status['backlog_size'] > 15:
                busy_agents.append(agent)

        # If we have idle agents and some agents are overloaded
        if idle_agents and busy_agents:
            # Take tasks from busy agents and give to idle
            for idle_agent in idle_agents:
                for busy_agent in busy_agents:
                    if len(busy_agent.backlog) > 10:
                        # Transfer some tasks
                        tasks_to_move = busy_agent.backlog[-5:]  # Take 5 from end
                        busy_agent.backlog = busy_agent.backlog[:-5]

                        await idle_agent.assign_tasks(tasks_to_move)
                        print(f"⚖️ Rebalanced: {len(tasks_to_move)} tasks from {busy_agent.config.bot_id} to {idle_agent.config.bot_id}")
                        break

    async def report_status(self):
        """Print progress report"""
        total_tasks = len(self.all_tasks)
        completed_tasks = len(self.completed_task_ids)
        failed_tasks = len(self.failed_task_ids)

        if total_tasks == 0:
            return

        progress_pct = (completed_tasks / total_tasks) * 100
        elapsed_time = time.time() - self.start_time

        print(f"\n{'='*60}")
        print(f"📊 PROJECT STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        print(f"Progress: {completed_tasks}/{total_tasks} tasks ({progress_pct:.1f}%)")
        print(f"Failed: {failed_tasks}")
        print(f"Elapsed: {elapsed_time/60:.1f} minutes")

        # Agent status
        print(f"\nAgent Status:")
        for agent in self.agent_pool.values():
            status = agent.get_status()
            print(f"  {status['bot_id']:20s} | Backlog: {status['backlog_size']:2d} | "
                  f"Completed: {status['completed_count']:3d} | Status: {status['status']}")

        # Resource status
        if self.resource_manager:
            res_status = self.resource_manager.get_status()
            print(f"\nResources:")
            print(f"  CPU: {res_status['cpu']['in_use']}/{res_status['cpu']['total_cores']} cores in use")
            if 'gpu' in res_status:
                print(f"  GPU: {'ACTIVE' if res_status['gpu']['active'] else 'idle'} | Queue: {res_status['gpu']['queue_size']}")
            if 'costs' in res_status:
                print(f"  Cost: ${res_status['costs']['total']:.2f} / ${res_status['costs']['limit']:.2f}")

        print(f"{'='*60}\n")

    async def project_complete(self):
        """Handle project completion"""
        elapsed_time = time.time() - self.start_time

        print(f"\n{'='*60}")
        print(f"✅ PROJECT COMPLETE!")
        print(f"{'='*60}")
        print(f"Project: {self.active_project['project']}")
        print(f"Total tasks: {len(self.all_tasks)}")
        print(f"Completed: {len(self.completed_task_ids)}")
        print(f"Failed: {len(self.failed_task_ids)}")
        print(f"Duration: {elapsed_time/60:.1f} minutes ({elapsed_time/3600:.2f} hours)")

        if self.resource_manager:
            res_status = self.resource_manager.get_status()
            if 'costs' in res_status:
                print(f"Total cost: ${res_status['costs']['total']:.2f}")

        print(f"{'='*60}\n")

        # Notify orchestrator
        await self.message_bus.publish('project_complete', {
            'project': self.active_project['project'],
            'total_tasks': len(self.all_tasks),
            'completed': len(self.completed_task_ids),
            'duration_minutes': elapsed_time / 60
        })

    def get_status(self) -> Dict:
        """Get current foreman status"""
        if not self.active_project:
            return {
                "status": "idle",
                "active_project": None
            }

        return {
            "status": "managing_project",
            "active_project": self.active_project.get('project'),
            "total_tasks": len(self.all_tasks),
            "completed_tasks": len(self.completed_task_ids),
            "failed_tasks": len(self.failed_task_ids),
            "progress_percent": (len(self.completed_task_ids) / len(self.all_tasks) * 100) if self.all_tasks else 0,
            "elapsed_minutes": (time.time() - self.start_time) / 60 if self.start_time else 0,
            "agent_count": len(self.agent_pool)
        }
