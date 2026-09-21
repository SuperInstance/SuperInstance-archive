# Architecture v3: Chooser Bot + Parallel Dispatch

**Evolution**: From direct orchestration → **Meta-orchestration with parallel dispatch**

---

## The Big Idea

> **Use the cheapest model to decide which expensive model to use, then dispatch work in parallel while keeping human in the loop.**

### The Flow

```
User Request
    ↓
┌─────────────────────────────────────────────────────────────┐
│              CHOOSER BOT (Groq 8B - $0.05/1M)              │
│                  "The Meta-Orchestrator"                    │
│                                                             │
│  Analyzes:                                                  │
│  • Task complexity (1-10 scale)                            │
│  • What orchestrator is needed                             │
│  • What worker agents are needed                           │
│  • What can start immediately (parallel)                   │
│  • Estimated cost                                           │
│                                                             │
│  Decides:                                                   │
│  • Simple task (complexity 1-3) → GPT-4o-mini orchestrates │
│  • Medium task (4-7) → Claude Sonnet orchestrates          │
│  • Complex task (8-10) → Claude Opus orchestrates          │
│                                                             │
│  Creates:                                                   │
│  • Initial prompts for all agents                          │
│  • Recruitment messages                                     │
│  • Coordination plan                                        │
└──────────────────┬──────────────────────────────────────────┘
                   ↓
        ┌──────────┴──────────┐
        ↓                     ↓
┌─────────────────┐   ┌─────────────────────────────────────┐
│  SIMPLE AGENTS  │   │     ORCHESTRATOR                    │
│  (Start NOW)    │   │     (Chosen by Chooser)             │
│                 │   │                                     │
│ • Researcher    │   │  Receives:                          │
│ • Summarizer    │   │  • Full context                     │
│ • Describer     │   │  • Agent roster                     │
│ • Analyzer      │   │  • What's already started           │
│                 │   │  • Coordination strategy            │
│ Start in        │   │                                     │
│ parallel!       │   │  Plans around parallel work         │
└─────────┬───────┘   └──────────┬──────────────────────────┘
          │                      │
          └──────────┬───────────┘
                     ↓
          ┌─────────────────────────────────────┐
          │   PROGRESS TRACKER BOT              │
          │   (Groq 8B - "The Foreman")         │
          │                                     │
          │   Tracks:                            │
          │   • Active bots (7/14 working)      │
          │   • Current tasks                   │
          │   • Progress (45% complete)         │
          │   • Bottlenecks                     │
          │   • Cost so far ($0.34)             │
          │                                     │
          │   Reports to human on demand        │
          └─────────────────────────────────────┘
```

---

## Detailed Component Design

### 1. Chooser Bot (The Meta-Orchestrator)

**Model**: Groq Llama 8B ($0.05/1M tokens) or GPT-4o-mini ($0.15/1M)
**Cost per analysis**: ~$0.0001 (essentially free!)

**Prompt Structure**:
```python
CHOOSER_SYSTEM_PROMPT = """
You are the Chooser Bot - the meta-orchestrator who analyzes tasks and plans execution.

Your job:
1. Analyze task complexity (1-10)
2. Choose the right orchestrator model
3. Identify worker agents needed
4. Determine what can start immediately (parallel)
5. Create initial prompts for all agents

Complexity Scale:
1-3: Simple (summarize, classify, extract)
4-6: Moderate (write, analyze, plan)
7-9: Complex (multi-step reasoning, strategy)
10: Ultra-complex (system design, research synthesis)

Orchestrator Selection:
- 1-3: GPT-4o-mini ($0.15/1M) - Fast and cheap
- 4-6: Claude Sonnet ($3/1M) - Balanced
- 7-9: Claude Opus ($20/1M) - Premium reasoning
- 10: Claude Opus + parallel research team

Available Agents:
- researcher: Gather information (Groq 70B)
- summarizer: Summarize content (Groq 8B)
- writer: Create content (Sonnet/GPT-4o)
- analyzer: Analyze data (GPT-4o)
- coder: Write code (Sonnet)
- reviewer: QA check (Opus)

Output JSON:
{
  "complexity": 7,
  "orchestrator": "claude-sonnet-3.5",
  "orchestrator_prompt": "...",
  "immediate_agents": [
    {
      "name": "researcher",
      "model": "groq-llama-70b",
      "prompt": "Research X...",
      "can_start_now": true
    }
  ],
  "deferred_agents": [...],
  "estimated_cost": 0.45,
  "reasoning": "..."
}
"""

async def chooser_analyze(user_request: str) -> ExecutionPlan:
    """
    Chooser Bot analyzes request and creates execution plan
    """
    response = await api.complete(
        messages=[
            {"role": "system", "content": CHOOSER_SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {user_request}"}
        ],
        model="groq-llama-8b-instant",  # Ultra cheap!
        max_tokens=2000
    )

    plan = ExecutionPlan.from_json(response.content)

    # Cost: ~$0.0001
    return plan
```

### 2. Parallel Dispatch System

**Key Innovation**: Some agents start immediately while orchestrator plans

```python
class ParallelDispatcher:
    """
    Dispatches work to agents in parallel
    """

    async def execute_plan(self, plan: ExecutionPlan, context: dict):
        """
        Execute plan with parallel dispatch
        """

        # Start progress tracker
        progress_tracker = ProgressTrackerBot()
        await progress_tracker.start(plan)

        # Dispatch immediate agents (parallel)
        immediate_tasks = []
        for agent in plan.immediate_agents:
            task = self.dispatch_agent(
                agent_config=agent,
                context=context
            )
            immediate_tasks.append(task)

            # Log to progress tracker
            await progress_tracker.agent_started(agent.name)

        # Start orchestrator (parallel)
        orchestrator_task = self.start_orchestrator(
            model=plan.orchestrator,
            prompt=plan.orchestrator_prompt,
            context=context,
            already_started=plan.immediate_agents
        )

        # All running in parallel now!
        # Orchestrator knows simple agents are working

        # Gather results as they complete
        results = {}

        # Wait for immediate agents (they're fast)
        for task in asyncio.as_completed(immediate_tasks):
            agent_name, result = await task
            results[agent_name] = result
            await progress_tracker.agent_completed(agent_name, result)

            # Feed results to orchestrator
            await self.send_to_orchestrator(agent_name, result)

        # Wait for orchestrator to complete
        final_result = await orchestrator_task

        # Stop progress tracker
        await progress_tracker.stop()

        return final_result
```

**Example Flow**:

```
Time 0s:
  Chooser Bot: Analyzes "Create Episode 1 for YouTube"
  → Complexity: 7
  → Orchestrator: Claude Sonnet
  → Immediate agents: researcher, story_indexer
  → Deferred: script_writer, image_prompter (wait for orchestrator)

Time 0.5s:
  [PARALLEL START]
  • researcher (Groq 70B) → "Research Story 1 structure"
  • story_indexer (Groq 8B) → "Index Story 1"
  • orchestrator (Sonnet) → "Plan episode creation..."

Time 5s:
  ✓ story_indexer completes → sends to orchestrator
  ✓ researcher completes → sends to orchestrator
  • orchestrator receives both, continues planning

Time 10s:
  ✓ orchestrator recruits script_writer (Sonnet)
  • script_writer starts with research + index results

Time 30s:
  ✓ script_writer completes
  • orchestrator recruits image_prompter

etc...
```

### 3. Progress Tracker Bot (The Foreman)

**Model**: Groq Llama 8B (ultra cheap, fast updates)

```python
PROGRESS_TRACKER_SYSTEM_PROMPT = """
You are the Progress Tracker Bot - the foreman on this job site.

Your job:
1. Track all active agents and their tasks
2. Monitor progress (% complete)
3. Identify bottlenecks
4. Report status to the human engineer

You maintain a real-time status board:
- Who's working
- What they're doing
- Progress percentage
- Any issues
- Cost so far

When human asks "status", give clear, concise summary like a foreman:
"We've got 4 agents working right now:
 - Researcher is 80% done gathering Story 1 info
 - Script writer just started, about 10% in
 - Image prompter waiting for script (queued)
 - Orchestrator coordinating everything

Overall: 45% complete, $0.34 spent so far, ETA 5 minutes"
"""

class ProgressTrackerBot:
    """
    Tracks progress and reports to human
    """

    def __init__(self):
        self.agents = {}
        self.total_cost = 0.0
        self.start_time = None
        self.model = "groq-llama-8b-instant"

    async def agent_started(self, name: str, task: str):
        """Agent started work"""
        self.agents[name] = {
            'status': 'working',
            'task': task,
            'progress': 0,
            'start_time': time.time()
        }

    async def agent_progress(self, name: str, progress: float):
        """Update agent progress"""
        if name in self.agents:
            self.agents[name]['progress'] = progress

    async def agent_completed(self, name: str, result: dict):
        """Agent completed"""
        if name in self.agents:
            self.agents[name]['status'] = 'completed'
            self.agents[name]['progress'] = 100
            self.total_cost += result.get('cost', 0)

    async def get_status(self, query: str = "What's the status?") -> str:
        """
        Human asks for status - generate foreman report
        """

        # Prepare current state
        state = {
            'active_count': sum(1 for a in self.agents.values() if a['status'] == 'working'),
            'completed_count': sum(1 for a in self.agents.values() if a['status'] == 'completed'),
            'agents': self.agents,
            'total_cost': self.total_cost,
            'elapsed': time.time() - self.start_time if self.start_time else 0
        }

        # Ask cheap model to format status
        response = await api.complete(
            messages=[
                {"role": "system", "content": PROGRESS_TRACKER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Status: {json.dumps(state)}\nQuestion: {query}"}
            ],
            model=self.model,
            max_tokens=300
        )

        # Cost: ~$0.00002 per status check!
        return response.content
```

**Example Status Reports**:

```
Human: "status"
Foreman: "4 agents working:
  - researcher: 75% done gathering info
  - story_indexer: 100% complete ✓
  - orchestrator: planning (20%)
  - script_writer: queued, waiting for orchestrator

  Overall: 35% done, spent $0.12, ETA 8 min"