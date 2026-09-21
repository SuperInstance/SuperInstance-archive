# ENHANCED PARALLEL MULTI-AGENT ARCHITECTURE
## With Foreman Pattern & True Parallelism

**Created**: 2025-10-13
**Hardware Target**: RTX 4050, Multi-core CPU
**Approach**: API-based (no local model downloads)

---

## EXECUTIVE SUMMARY

This document describes an **enhanced parallel architecture** that transforms the sequential multi-agent system into a **true parallel swarm** where:

- **Multiple agents work simultaneously** on different tasks
- Each agent has its own **backlog of 10-20 tasks** to work through
- A **Foreman Bot** manages workload distribution and keeps agents busy
- **Background workers** do research/summarizing while main work happens
- **CPU/GPU resources** are pooled and allocated efficiently across all agents
- Agents operate **independently**, checking off their own task lists

---

## CURRENT ARCHITECTURE (What You Have)

```
User Request
    ↓
ORCHESTRATOR (Claude Sonnet)
    ↓
Task Manager (Global Priority Queue)
    ↓
Message Bus (Single queue per bot)
    ↓
Individual Bots → Process ONE task at a time → Report back
```

### Current Limitations:
❌ **Sequential processing**: Bots work one task at a time
❌ **No task backlogs**: Each bot has only 1 queue, no visibility into upcoming work
❌ **Direct assignment**: Orchestrator assigns directly to bots (no foreman layer)
❌ **No resource management**: CPU/GPU not explicitly allocated
❌ **No background work**: Research must wait for main task to finish
❌ **Underutilized hardware**: Multi-core CPU and GPU sit idle

---

## ENHANCED ARCHITECTURE (What You Need)

```
                    User Request
                          ↓
          ┌─────────────────────────────────┐
          │  ORCHESTRATOR (Claude Opus)     │
          │  - Project planning              │
          │  - High-level strategy           │
          │  - Quality review                │
          └─────────────────────────────────┘
                          ↓
          ┌─────────────────────────────────┐
          │  FOREMAN BOT (Claude Sonnet)    │
          │  - Break down into agent tasks   │
          │  - Manage agent workloads        │
          │  - Keep agents busy              │
          │  - Resource allocation           │
          │  - Progress monitoring           │
          └─────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────┐
    │      AGENT POOL (Independent Workers)        │
    │                                              │
    │  ┌────────────┐  ┌────────────┐  ┌────────┐│
    │  │ Agent 1    │  │ Agent 2    │  │Agent 3 ││
    │  │ [Task 1]   │  │ [Task 7]   │  │[Task12]││
    │  │ [Task 2]   │  │ [Task 8]   │  │[Task13]││
    │  │ [Task 3]   │  │ [Task 9]   │  │[Task14]││
    │  │ [Task 4]   │  │ [Task 10]  │  │[Task15]││
    │  │ ...        │  │ ...        │  │...     ││
    │  │ [Task 20]  │  │ [Task 26]  │  │[Task30]││
    │  │            │  │            │  │        ││
    │  │ Working ⚙️  │  │ Working ⚙️  │  │Working⚙││
    │  └────────────┘  └────────────┘  └────────┘│
    └─────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────┐
    │       BACKGROUND RESEARCH POOL               │
    │  (Cheap/fast models for prep work)           │
    │                                              │
    │  ┌────────────┐  ┌────────────┐  ┌────────┐│
    │  │Researcher 1│  │Researcher 2│  │Summar. ││
    │  │ [Research  │  │ [Gather    │  │[Condense││
    │  │  story     │  │  character │  │ docs]  ││
    │  │  context]  │  │  refs]     │  │        ││
    │  │            │  │            │  │        ││
    │  │ Working 📚  │  │ Working 📚  │  │Working 📚││
    │  └────────────┘  └────────────┘  └────────┘│
    └─────────────────────────────────────────────┘
                          ↓
    ┌─────────────────────────────────────────────┐
    │       RESOURCE MANAGER                       │
    │  - CPU Core Pool (8 cores)                   │
    │  - GPU Queue (RTX 4050)                      │
    │  - API Rate Limiting                         │
    │  - Cost Tracking                             │
    └─────────────────────────────────────────────┘
```

---

## KEY COMPONENTS

### 1. ORCHESTRATOR (Project-Level Intelligence)

**Role**: Strategic planning and quality oversight
**Model**: Claude Opus (expensive, used sparingly)
**Responsibilities**:
- Receives user request: "Create Episode 1 for YouTube"
- Creates high-level project plan
- Defines success criteria
- Reviews final output
- Handles escalations from Foreman

**NOT responsible for**:
- Breaking down into small tasks (Foreman does this)
- Managing individual agents (Foreman does this)
- Monitoring progress (Foreman does this)

**Example Interaction**:
```
User: "Create Episode 1 for YouTube"

Orchestrator →
{
  "project": "episode_1_youtube",
  "goal": "28-minute animated episode of Story 1",
  "phases": [
    "Story adaptation & script writing",
    "Visual asset generation (characters, backgrounds)",
    "Audio production (dialogue, music)",
    "Video assembly & editing",
    "QA & publishing"
  ],
  "success_criteria": {
    "duration": "26-30 minutes",
    "quality": "broadcast standard",
    "story_accuracy": "95%+",
    "cost_target": "<$50"
  },
  "assign_to_foreman": true
}
```

---

### 2. FOREMAN BOT (Team Lead)

**Role**: Workload management and agent coordination
**Model**: Claude Sonnet (good balance of cost/intelligence)
**Responsibilities**:
- Receives project plan from Orchestrator
- Breaks down into 50-200 small agent tasks
- Assigns tasks to agent backlogs (10-20 tasks per agent)
- Monitors agent progress
- Reassigns work if agents get stuck
- Keeps agents busy with new tasks as they complete old ones
- Detects bottlenecks and requests more agents if needed
- Reports progress to Orchestrator

**Key Innovation**: **Continuous workload balancing**

```python
class ForemanBot:
    """Manages agent workload and keeps them busy"""

    async def manage_project(self, project_plan):
        # 1. Break down project
        all_tasks = await self.decompose_project(project_plan)
        # Example: 200 tasks for Episode 1

        # 2. Assign to agent backlogs
        await self.distribute_tasks(all_tasks)
        # Each agent gets 10-20 tasks initially

        # 3. Monitor and rebalance
        while not project_complete:
            # Check agent status
            for agent in self.agents:
                if agent.backlog_size < 5:
                    # Agent running low on work
                    await self.assign_more_tasks(agent)

                if agent.is_stuck():
                    # Agent needs help
                    await self.reassign_task(agent.current_task)

            # Check for blockers
            if self.detect_bottleneck():
                # Request more agents or escalate
                await self.request_help()

            await asyncio.sleep(10)  # Check every 10 seconds
```

**Task Decomposition Example**:
```
Project: "Create Episode 1 script"
↓
Foreman breaks into:
[
  {id: 1, type: "research", desc: "Index Story_01_v3.md", agent: "story_indexer"},
  {id: 2, type: "research", desc: "Extract character list", agent: "character_analyzer"},
  {id: 3, type: "research", desc: "Identify key scenes", agent: "scene_analyzer"},
  {id: 4, type: "write", desc: "Scene 1 script adaptation", agent: "script_writer"},
  {id: 5, type: "write", desc: "Scene 2 script adaptation", agent: "script_writer"},
  ... (50 more tasks)
]
```

---

### 3. AGENT POOL (Workers with Backlogs)

**Enhancement**: Each agent now has:
- **Task Backlog**: 10-20 queued tasks
- **Current Task**: What they're working on now
- **Completed List**: History of finished work
- **Independent Execution**: Work through backlog autonomously

**Agent Structure**:
```python
class EnhancedAgent:
    def __init__(self, agent_id, agent_type, model):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.model = model

        # NEW: Task backlog
        self.backlog = []  # List of 10-20 tasks
        self.current_task = None
        self.completed_tasks = []

        # Status
        self.status = "idle"  # idle, working, researching, stuck
        self.progress_percent = 0

    async def work_loop(self):
        """Continuously work through backlog"""
        while True:
            if self.backlog:
                # Get next task
                self.current_task = self.backlog.pop(0)
                self.status = "working"

                # Execute
                result = await self.execute_task(self.current_task)

                if result.success:
                    self.completed_tasks.append(self.current_task)
                    await self.report_completion(result)
                else:
                    # Request help
                    await self.request_help(self.current_task)

                self.current_task = None
            else:
                # Backlog empty, wait for more work
                self.status = "idle"
                await asyncio.sleep(5)

    async def assign_tasks(self, tasks: List[Task]):
        """Foreman assigns batch of tasks"""
        self.backlog.extend(tasks)
        print(f"{self.agent_id} received {len(tasks)} tasks. Backlog: {len(self.backlog)}")

    def get_status(self):
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "backlog_size": len(self.backlog),
            "completed_count": len(self.completed_tasks),
            "current_task": self.current_task.id if self.current_task else None,
            "progress": f"{len(self.completed_tasks)}/{len(self.backlog) + len(self.completed_tasks)}"
        }
```

**Example Agent Backlogs**:
```
Agent: script_writer_1
Backlog:
  [1] Adapt Scene 1 (2 min)      ← WORKING
  [2] Adapt Scene 2 (3 min)      ← NEXT
  [3] Adapt Scene 3 (2.5 min)
  [4] Adapt Scene 4 (4 min)
  [5] Review all dialogue
  ... (10 more tasks)
Completed: 0/15

Agent: image_prompter_1
Backlog:
  [1] Generate prompt: Casey wonder   ← WORKING
  [2] Generate prompt: Casey excited
  [3] Generate prompt: Anna frustrated
  ... (15 more tasks)
Completed: 0/18

Agent: researcher_1 (background)
Backlog:
  [1] Summarize Story 1 themes        ← WORKING
  [2] Extract character descriptions
  [3] List all locations
  ... (12 more tasks)
Completed: 0/15
```

---

### 4. BACKGROUND RESEARCH POOL

**NEW COMPONENT**: Separate pool of cheap/fast agents for preparatory work

**Purpose**:
- While main agents work on critical tasks, background agents:
  - Research story context
  - Summarize reference materials
  - Gather character descriptions
  - Prepare visual references
  - Pre-analyze scenes for complexity

**Models**: Use CHEAP models (Groq Llama 3.1 8B - FREE!)
**Parallelism**: 3-5 background workers running simultaneously
**Cost**: Near zero (using free tier)

**Example**:
```
Main Work:
  script_writer_1 → Adapting Scene 5 (needs character info)

Background Work (happening simultaneously):
  researcher_1 → Extracting all Casey Chen dialogue patterns
  researcher_2 → Gathering Anna's character development arc
  summarizer_1 → Condensing Story 2 for continuity reference
```

**When main agent needs info**:
```python
# Main agent checks if background research is ready
character_info = await self.check_research_cache("Casey_personality")

if character_info:
    # Use pre-researched data (fast!)
    prompt = f"Based on this research: {character_info}, adapt scene..."
else:
    # Fall back to inline research (slower)
    prompt = "Analyze character from scratch and adapt scene..."
```

---

### 5. RESOURCE MANAGER

**NEW COMPONENT**: Manages CPU/GPU allocation across all agents

**Purpose**:
- **RTX 4050 GPU**: Queue for image generation tasks
- **Multi-core CPU**: Parallelize API calls and text processing
- **API Rate Limits**: Ensure we don't exceed provider limits
- **Cost Tracking**: Monitor spending in real-time

**Resource Pools**:
```python
class ResourceManager:
    def __init__(self):
        # CPU Pool (8 cores on your system)
        self.cpu_pool = asyncio.Semaphore(8)  # Max 8 parallel CPU tasks

        # GPU Queue (RTX 4050 - one task at a time)
        self.gpu_queue = asyncio.Queue()
        self.gpu_worker = self.start_gpu_worker()

        # API Rate Limiters
        self.api_limiters = {
            "anthropic": AsyncLimiter(50, 60),  # 50 requests per minute
            "openai": AsyncLimiter(500, 60),    # 500 rpm
            "groq": AsyncLimiter(30, 60),       # 30 rpm (free tier)
        }

        # Cost Tracker
        self.cost_tracker = CostTracker()

    async def execute_with_cpu(self, task, agent_id):
        """Execute task with CPU resource allocation"""
        async with self.cpu_pool:
            # Agent gets a CPU core
            result = await task.execute()
            return result

    async def execute_with_gpu(self, task, agent_id):
        """Queue task for GPU execution"""
        await self.gpu_queue.put((task, agent_id))
        result = await task.wait_for_result()
        return result

    async def execute_api_call(self, provider, **kwargs):
        """Execute API call with rate limiting"""
        async with self.api_limiters[provider]:
            response = await self.call_api(provider, **kwargs)

            # Track cost
            cost = self.calculate_cost(provider, response)
            self.cost_tracker.add(cost)

            return response
```

**CPU Utilization**:
```
8 CPU cores available:

Core 1: script_writer_1   (writing scene 1)
Core 2: script_writer_2   (writing scene 2)
Core 3: image_prompter_1  (generating prompt 1)
Core 4: researcher_1      (summarizing story)
Core 5: researcher_2      (extracting characters)
Core 6: dialogue_fmt_1    (formatting audio)
Core 7: qa_content_1      (reviewing output)
Core 8: foreman_bot       (managing workload)

All cores utilized! ✅
```

**GPU Queue** (RTX 4050):
```
GPU Task Queue:
  [1] Generate image: Casey wonder    ← PROCESSING (30 sec)
  [2] Generate image: Anna frustrated ← QUEUED
  [3] Generate image: Boat interior   ← QUEUED
  ... (10 more in queue)

Note: While GPU works, CPU agents continue their tasks!
```

---

## WORKFLOW EXAMPLE: "Create Episode 1 for YouTube"

### Phase 1: Project Planning (Orchestrator)

```
User: "Create Episode 1 for YouTube"

Orchestrator (Claude Opus):
  → Analyzes request
  → Creates project plan
  → Estimates: 200 tasks, 4-6 hours, $30-50 cost
  → Passes to Foreman
```

### Phase 2: Task Decomposition (Foreman)

```
Foreman (Claude Sonnet):
  → Breaks down into 200 small tasks:

  Research Tasks (30):
    - Index Story_01_v3.md
    - Extract characters (5 characters)
    - List all locations (8 locations)
    - Summarize each scene (12 scenes)
    - Gather visual references

  Script Writing Tasks (40):
    - Adapt Scene 1 (intro)
    - Adapt Scene 2 (discovery)
    ... (12 scenes)
    - Format dialogue for each scene
    - Add timing marks

  Visual Asset Tasks (60):
    - Generate prompts for Casey (10 variations)
    - Generate prompts for Anna (10 variations)
    - Generate prompts for backgrounds (20)
    - Generate prompts for effects (20)

  Audio Tasks (30):
    - Format dialogue Scene 1
    - Format dialogue Scene 2
    ... (12 scenes)
    - Music cue planning

  QA Tasks (20):
    - Review script Scene 1
    - Review script Scene 2
    ... (12 scenes)
    - Check continuity

  Assembly Tasks (20):
    - Plan video sequence
    - Generate metadata
    - Create social media clips

  → Assigns tasks to agent backlogs
```

### Phase 3: Parallel Execution

```
T=0min: Project starts

Agents receive their backlogs:
  script_writer_1:   [20 scene adaptation tasks]
  script_writer_2:   [20 dialogue formatting tasks]
  image_prompter_1:  [20 character prompt tasks]
  image_prompter_2:  [20 background prompt tasks]
  researcher_1:      [15 research tasks]
  researcher_2:      [15 summarization tasks]
  qa_agent_1:        [20 review tasks]

T=1min: All agents working simultaneously!

┌──────────────────────────────────────────────────┐
│ script_writer_1:   Scene 1 [████░░░░░░] 40%      │
│ script_writer_2:   Dialogue 1 [██░░░░░░░░] 20%   │
│ image_prompter_1:  Casey_wonder [████████] 100%  │ ✓ Done!
│ image_prompter_2:  Boat_int [█████░░░░░] 50%     │
│ researcher_1:      Story index [████████] 100%   │ ✓ Done!
│ researcher_2:      Char list [██████░░░░] 60%    │
│ qa_agent_1:        Waiting for script...         │
└──────────────────────────────────────────────────┘

T=3min: Tasks completing, new tasks assigned

┌──────────────────────────────────────────────────┐
│ script_writer_1:   Scene 1 [████████] 100%       │ ✓ Done!
│                    Scene 2 [░░░░░░░░░░] 0%       │ ← New task!
│ script_writer_2:   Dialogue 1 [████████] 100%    │ ✓ Done!
│                    Dialogue 2 [░░░░░░░░░░] 0%    │ ← New task!
│ image_prompter_1:  Casey_excited [░░░░░░░░] 0%   │ ← New task!
│ researcher_1:      Locations [████░░░░░░] 40%    │ ← New task!
└──────────────────────────────────────────────────┘

Foreman monitors:
  - All agents busy ✓
  - Backlogs healthy (5-15 tasks each) ✓
  - No blockers ✓
  - Progress: 8/200 tasks (4%) ✓
```

### Phase 4: Background Research Helps Main Work

```
T=10min: script_writer_1 needs character info

script_writer_1:
  Current task: "Adapt Scene 4 - Casey discovers music bug"

  Needs: Casey's personality, speech patterns, motivations

  Checks research cache:
    ✓ researcher_1 already completed:
      "Casey Chen full character analysis"

  Uses cached research (instant!) instead of re-analyzing

  Adapts scene faster (2 min instead of 5 min)
```

### Phase 5: Progress Monitoring (Foreman)

```
T=30min: Foreman checks progress

Status Report:
  Total tasks: 200
  Completed: 52 (26%)
  In progress: 8 (agents working)
  Queued: 140 (in agent backlogs)

  Agent Utilization:
    script_writer_1: 95% (working)
    script_writer_2: 95% (working)
    image_prompter_1: 98% (working)
    researcher_1: 20% (mostly idle - tasks done)

  Bottleneck detected:
    researcher_1 has completed all tasks

  Action:
    Foreman reassigns researcher_1 to help with QA
    New tasks: "Review completed scripts"
```

### Phase 6: Completion

```
T=4 hours: All 200 tasks complete

Foreman → Orchestrator:
  "Episode 1 production complete"

  Final Stats:
    - Duration: 4.2 hours
    - Tasks completed: 200
    - Average task time: 1.3 minutes
    - Total cost: $42
    - Agent utilization: 87% (good!)

  Deliverables:
    ✓ Complete script (28 minutes)
    ✓ 150 image prompts (characters, backgrounds)
    ✓ Audio formatting (all scenes)
    ✓ QA passed (95% accuracy)
    ✓ Metadata generated
    ✓ Social clips planned

Orchestrator reviews:
  ✓ Meets success criteria
  ✓ Ready for asset generation phase
```

---

## IMPLEMENTATION CHANGES NEEDED

### Changes to Existing Code

#### 1. Enhanced BaseBot with Backlog

```python
# src/bots/base_bot.py

class BaseBot(ABC):
    def __init__(self, config: BotConfig, ...):
        # ... existing code ...

        # NEW: Task backlog
        self.backlog = []  # List of tasks
        self.max_backlog_size = 20
        self.current_task = None
        self.completed_tasks = []

    async def start(self):
        """Start the bot's work loop"""
        print(f"🤖 Starting {self.config.bot_id}")

        # NEW: Continuous work loop
        asyncio.create_task(self.continuous_work_loop())

    async def continuous_work_loop(self):
        """Continuously work through backlog"""
        while True:
            if self.backlog:
                # Get next task from backlog
                self.current_task = self.backlog.pop(0)
                self.status = BotStatus.WORKING

                # Execute task
                result = await self.execute_task(self.current_task)

                if result['status'] == 'completed':
                    self.completed_tasks.append({
                        'task': self.current_task,
                        'result': result,
                        'completed_at': time.time()
                    })

                    # Report to Foreman
                    await self.report_completion(result)

                self.current_task = None
            else:
                # Backlog empty
                self.status = BotStatus.IDLE
                await asyncio.sleep(2)

    async def assign_tasks(self, tasks: List[Dict]):
        """Receive batch of tasks from Foreman"""
        self.backlog.extend(tasks)

        # Limit backlog size
        if len(self.backlog) > self.max_backlog_size:
            self.backlog = self.backlog[:self.max_backlog_size]

        print(f"📋 {self.config.bot_id} backlog: {len(self.backlog)} tasks")

    def get_status(self):
        return {
            **super().get_status(),
            "backlog_size": len(self.backlog),
            "completed_count": len(self.completed_tasks),
            "current_task_id": self.current_task.get('task_id') if self.current_task else None,
            "capacity": "idle" if len(self.backlog) == 0 else "busy"
        }
```

#### 2. New ForemanBot

```python
# src/bots/foreman_bot.py

import asyncio
from typing import Dict, Any, List
import anthropic
import os

class ForemanBot:
    """Manages agent workload and keeps them busy"""

    def __init__(self, agent_pool: Dict, resource_manager):
        self.agent_pool = agent_pool  # All available agents
        self.resource_manager = resource_manager
        self.claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        self.active_project = None
        self.total_tasks = 0
        self.completed_tasks = 0

    async def start_project(self, project_plan: Dict):
        """Receive project from Orchestrator and manage execution"""
        self.active_project = project_plan

        print(f"👷 Foreman starting project: {project_plan['project']}")

        # Step 1: Decompose project into tasks
        all_tasks = await self.decompose_project(project_plan)
        self.total_tasks = len(all_tasks)

        print(f"📋 Project decomposed into {self.total_tasks} tasks")

        # Step 2: Distribute to agent backlogs
        await self.distribute_tasks(all_tasks)

        # Step 3: Monitor and manage
        await self.monitor_project()

    async def decompose_project(self, project_plan: Dict) -> List[Dict]:
        """Use Claude to break project into small tasks"""
        prompt = f"""You are a project foreman. Break this project into 100-200 small, specific tasks.

Project: {project_plan['goal']}
Phases: {project_plan['phases']}

Available agent types:
- script_writer: Adapts stories to scripts
- image_prompter: Creates image generation prompts
- dialogue_formatter: Formats dialogue for voice synthesis
- researcher: Gathers info, summarizes content
- qa_content: Reviews quality
- metadata_gen: Creates titles, descriptions

For each task, specify:
1. Task ID (unique)
2. Agent type (which agent should do it)
3. Description (clear, specific)
4. Dependencies (which tasks must complete first)
5. Estimated duration (in minutes)
6. Priority (high/medium/low)

Return as JSON array:
[
  {{
    "id": "task_001",
    "agent_type": "researcher",
    "description": "Index Story_01_v3.md into knowledge base",
    "dependencies": [],
    "duration_minutes": 2,
    "priority": "high"
  }},
  ... (100-200 more tasks)
]
"""

        response = self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}]
        )

        tasks_json = response.content[0].text.strip().strip('```json').strip('```')
        tasks = json.loads(tasks_json)

        return tasks

    async def distribute_tasks(self, tasks: List[Dict]):
        """Distribute tasks to agent backlogs"""
        # Group tasks by agent type
        tasks_by_type = {}
        for task in tasks:
            agent_type = task['agent_type']
            if agent_type not in tasks_by_type:
                tasks_by_type[agent_type] = []
            tasks_by_type[agent_type].append(task)

        # Assign to agents
        for agent_type, agent_tasks in tasks_by_type.items():
            # Find agents of this type
            agents = [a for a in self.agent_pool.values()
                     if a.config.bot_type == agent_type]

            if not agents:
                print(f"⚠️ No agents available for type: {agent_type}")
                continue

            # Distribute evenly
            tasks_per_agent = len(agent_tasks) // len(agents)
            for i, agent in enumerate(agents):
                start_idx = i * tasks_per_agent
                end_idx = start_idx + tasks_per_agent if i < len(agents) - 1 else len(agent_tasks)
                agent_batch = agent_tasks[start_idx:end_idx]

                await agent.assign_tasks(agent_batch)
                print(f"  ✓ {agent.config.bot_id}: {len(agent_batch)} tasks")

    async def monitor_project(self):
        """Continuously monitor and rebalance workload"""
        while self.completed_tasks < self.total_tasks:
            await asyncio.sleep(10)  # Check every 10 seconds

            # Check each agent
            for agent in self.agent_pool.values():
                status = agent.get_status()

                # Agent running low on work?
                if status['backlog_size'] < 3 and status['backlog_size'] > 0:
                    print(f"⚠️ {agent.config.bot_id} running low on tasks")

                # Agent idle?
                if status['capacity'] == 'idle':
                    print(f"💤 {agent.config.bot_id} is idle")

                # Update completed count
                self.completed_tasks = sum(
                    agent.get_status()['completed_count']
                    for agent in self.agent_pool.values()
                )

            # Progress report
            progress_pct = (self.completed_tasks / self.total_tasks) * 100
            print(f"📊 Progress: {self.completed_tasks}/{self.total_tasks} ({progress_pct:.1f}%)")

        print("✅ Project complete!")
```

#### 3. Resource Manager

```python
# src/resources/resource_manager.py

import asyncio
from aiolimiter import AsyncLimiter
from typing import Dict, Any

class ResourceManager:
    """Manages CPU/GPU resources and API rate limits"""

    def __init__(self, cpu_cores=8):
        # CPU Pool
        self.cpu_pool = asyncio.Semaphore(cpu_cores)
        print(f"💻 CPU Pool: {cpu_cores} cores")

        # GPU Queue (RTX 4050 - one at a time)
        self.gpu_queue = asyncio.Queue()
        self.gpu_active = False
        asyncio.create_task(self.gpu_worker())
        print(f"🎮 GPU Queue: RTX 4050")

        # API Rate Limiters (requests per minute)
        self.api_limiters = {
            "anthropic": AsyncLimiter(50, 60),   # 50 rpm
            "openai": AsyncLimiter(500, 60),     # 500 rpm
            "groq": AsyncLimiter(30, 60),        # 30 rpm (free tier)
            "together": AsyncLimiter(60, 60),    # 60 rpm
        }

        # Cost tracking
        self.costs = {provider: 0.0 for provider in self.api_limiters.keys()}
        self.cost_limit = 100.0  # $100 daily limit

    async def execute_with_cpu(self, agent_id: str, task_func):
        """Execute task with CPU resource allocation"""
        async with self.cpu_pool:
            result = await task_func()
            return result

    async def execute_with_gpu(self, agent_id: str, task_func):
        """Queue task for GPU execution"""
        result_future = asyncio.Future()
        await self.gpu_queue.put((task_func, result_future))
        return await result_future

    async def gpu_worker(self):
        """Process GPU queue one task at a time"""
        while True:
            task_func, result_future = await self.gpu_queue.get()
            self.gpu_active = True

            try:
                result = await task_func()
                result_future.set_result(result)
            except Exception as e:
                result_future.set_exception(e)
            finally:
                self.gpu_active = False
                self.gpu_queue.task_done()

    async def call_api(self, provider: str, **kwargs):
        """Execute API call with rate limiting"""
        # Check cost limit
        if sum(self.costs.values()) >= self.cost_limit:
            raise Exception(f"Daily cost limit reached: ${self.cost_limit}")

        # Rate limit
        async with self.api_limiters[provider]:
            # Make actual API call here
            response = await self._make_api_call(provider, **kwargs)

            # Track cost
            cost = self._estimate_cost(provider, response)
            self.costs[provider] += cost

            return response

    def get_status(self):
        return {
            "cpu": {
                "total_cores": self.cpu_pool._value + (8 - self.cpu_pool._value),
                "available": self.cpu_pool._value,
                "in_use": 8 - self.cpu_pool._value
            },
            "gpu": {
                "active": self.gpu_active,
                "queue_size": self.gpu_queue.qsize()
            },
            "costs": {
                "by_provider": self.costs,
                "total": sum(self.costs.values()),
                "limit": self.cost_limit,
                "remaining": self.cost_limit - sum(self.costs.values())
            }
        }
```

---

## NEXT STEPS

### Week 1: Core Infrastructure

1. **Create ResourceManager** ✅ (code provided)
   - CPU pool management
   - GPU queue
   - API rate limiting
   - Cost tracking

2. **Enhance BaseBot** ✅ (code provided)
   - Add task backlog
   - Implement continuous work loop
   - Add bulk task assignment

3. **Create ForemanBot** ✅ (code provided)
   - Project decomposition
   - Task distribution
   - Workload monitoring

### Week 2: Integration

1. **Update Orchestrator**
   - Pass projects to Foreman instead of directly to agents
   - Remove direct task assignment
   - Focus on high-level strategy

2. **Add Background Research Pool**
   - Create lightweight research bots
   - Implement research caching
   - Connect to main agent workflow

3. **Test with Simple Project**
   - "Index all story files"
   - Verify parallel execution
   - Monitor resource utilization

### Week 3: Full System Test

1. **Run Episode 1 Production**
   - Full 200-task project
   - All agents working in parallel
   - Monitor completion time & cost

2. **Optimize**
   - Adjust backlog sizes
   - Tune CPU/GPU allocation
   - Improve task decomposition

3. **Measure Success**
   - Agent utilization > 80%?
   - Cost < $50?
   - Time < 6 hours?

---

## EXPECTED IMPROVEMENTS

### Current System (Sequential):
- **Time**: ~12-16 hours (agents wait for each other)
- **CPU Utilization**: 12% (one agent at a time)
- **GPU Utilization**: 5% (rarely used)
- **Cost**: $60-80 (inefficient API usage)

### Enhanced System (Parallel):
- **Time**: ~4-6 hours (all agents working simultaneously)
- **CPU Utilization**: 85%+ (6-8 agents in parallel)
- **GPU Utilization**: 40%+ (batch processing)
- **Cost**: $30-50 (better resource utilization)

### Speedup: **3-4x faster with 30-40% cost reduction** 🚀

---

## QUESTIONS?

Ready to implement this? I can help you:
1. Integrate the enhanced code into your existing system
2. Set up the Foreman bot
3. Create the background research pool
4. Configure resource management for RTX 4050
5. Test with a simple project first

Which part would you like to start with?
