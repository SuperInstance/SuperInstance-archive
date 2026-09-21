# Quick Start: Building Your Multi-Agent Coding Assistant
## From Zero to MVP in 4 Weeks

**Goal**: Get a working multi-model coding assistant with cost optimization and local inference.

---

## Week 1: Foundation & Setup

### Day 1-2: Environment Setup

**Install Prerequisites:**
```bash
# Python environment
python3.11 -m venv venv
source venv/bin/activate

# Core dependencies
pip install anthropic rich prompt_toolkit asyncio redis

# Local inference (start with Ollama for simplicity)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5-coder:7b  # Fast, good quality
```

**GPU Check:**
```bash
nvidia-smi  # Verify CUDA available
# Minimum: 6GB VRAM for Qwen 7B
# Recommended: 24GB for Qwen 32B
```

**Project Structure:**
```
autocoder/
├── src/
│   ├── cli/           # Terminal interface
│   ├── providers/     # Model provider implementations
│   ├── orchestrator/  # Task routing & execution
│   ├── tools/         # Tool integrations
│   └── state/         # State management
├── tests/
├── config/
│   └── models.yaml    # Model configurations
├── .env               # API keys
└── main.py            # Entry point
```

### Day 3-4: Model Provider Abstraction

**Create Base Interface:**
```python
# src/providers/base.py
from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator, Union

class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class Response:
    def __init__(self, content: str, model: str, tokens: dict):
        self.content = content
        self.model = model
        self.input_tokens = tokens.get('input', 0)
        self.output_tokens = tokens.get('output', 0)

class ModelProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False
    ) -> Union[Response, AsyncIterator[str]]:
        """Send chat request to model"""
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        pass
```

**Implement Claude Provider:**
```python
# src/providers/claude.py
import anthropic
from .base import ModelProvider, Message, Response

class ClaudeProvider(ModelProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.costs = {
            "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
            "claude-3-5-haiku-20250219": {"input": 0.80, "output": 4.00},
        }

    async def chat(self, messages, temperature=0.7, max_tokens=4096, stream=False):
        response = await self.client.messages.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream
        )

        if stream:
            async for chunk in response:
                if chunk.type == "content_block_delta":
                    yield chunk.delta.text
        else:
            return Response(
                content=response.content[0].text,
                model=self.model,
                tokens={"input": response.usage.input_tokens,
                       "output": response.usage.output_tokens}
            )

    def estimate_cost(self, input_tokens, output_tokens):
        costs = self.costs[self.model]
        return (input_tokens / 1_000_000 * costs["input"] +
                output_tokens / 1_000_000 * costs["output"])
```

**Implement Ollama Provider:**
```python
# src/providers/ollama.py
import aiohttp
from .base import ModelProvider, Message, Response

class OllamaProvider(ModelProvider):
    def __init__(self, model: str = "qwen2.5-coder:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def chat(self, messages, temperature=0.7, max_tokens=4096, stream=False):
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": self.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": stream,
                "options": {"temperature": temperature, "num_predict": max_tokens}
            }

            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                if stream:
                    async for line in resp.content:
                        data = json.loads(line)
                        if data.get("message"):
                            yield data["message"]["content"]
                else:
                    result = await resp.json()
                    return Response(
                        content=result["message"]["content"],
                        model=self.model,
                        tokens={"input": 0, "output": 0}  # Ollama doesn't provide counts
                    )

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.0  # Local = free
```

### Day 5-7: Basic CLI

**Simple REPL Interface:**
```python
# src/cli/interface.py
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

class CLI:
    def __init__(self):
        self.console = Console()
        self.session = PromptSession(history=FileHistory('.autocoder_history'))
        self.providers = {}
        self.current_provider = None

    async def run(self):
        self.console.print("[bold blue]AutoCoder v0.1[/bold blue] - Multi-Model Coding Assistant\n")

        while True:
            try:
                user_input = await self.session.prompt_async("You: ")

                if user_input.startswith(":"):
                    await self.handle_command(user_input)
                    continue

                # Check for model override (@claude, @local)
                provider = self.parse_model_override(user_input)
                if not provider:
                    provider = self.current_provider

                # Stream response
                with Live(console=self.console, refresh_per_second=10) as live:
                    full_response = ""
                    async for chunk in provider.chat(
                        [Message("user", user_input)],
                        stream=True
                    ):
                        full_response += chunk
                        live.update(Markdown(full_response))

                self.console.print()  # Newline after response

            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    def parse_model_override(self, text: str):
        """Check for @model syntax"""
        if text.startswith("@claude"):
            return self.providers["claude"]
        elif text.startswith("@local"):
            return self.providers["ollama"]
        return None

    async def handle_command(self, cmd: str):
        """Handle :commands"""
        if cmd == ":quit":
            raise EOFError
        elif cmd == ":models":
            self.console.print("Available models:")
            for name in self.providers:
                self.console.print(f"  - {name}")
        elif cmd == ":help":
            self.console.print("""
Commands:
  :quit       Exit AutoCoder
  :models     List available models
  :cost       Show session costs

Model Selection:
  @claude     Force use Claude
  @local      Force use local model
            """)

# main.py
import asyncio
import os
from src.cli.interface import CLI
from src.providers.claude import ClaudeProvider
from src.providers.ollama import OllamaProvider

async def main():
    cli = CLI()

    # Initialize providers
    cli.providers["claude"] = ClaudeProvider(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-sonnet-4-5-20250929"
    )
    cli.providers["ollama"] = OllamaProvider(model="qwen2.5-coder:7b")

    # Default to local
    cli.current_provider = cli.providers["ollama"]

    await cli.run()

if __name__ == "__main__":
    asyncio.run(main())
```

**Test it:**
```bash
python main.py

# Try:
You: Write a function to calculate fibonacci
You: @claude Explain the time complexity
You: :models
You: :quit
```

---

## Week 2: Intelligent Routing

### Day 8-10: Task Complexity Analyzer

**Implement Complexity Scorer:**
```python
# src/orchestrator/analyzer.py
import re
from dataclasses import dataclass
from enum import Enum

class TaskComplexity(Enum):
    TRIVIAL = 1      # <500 tokens, simple formatting
    SIMPLE = 2       # <2K tokens, basic functions
    MODERATE = 3     # <10K tokens, multi-step
    COMPLEX = 4      # 10K+ tokens, reasoning required
    VERY_COMPLEX = 5 # Multi-file, architecture

@dataclass
class TaskAnalysis:
    complexity: TaskComplexity
    estimated_tokens: int
    requires_reasoning: bool
    needs_tools: bool
    suggested_model: str

class TaskAnalyzer:
    KEYWORDS_COMPLEX = [
        "architecture", "design system", "refactor", "migrate",
        "race condition", "security", "optimize algorithm"
    ]

    KEYWORDS_MODERATE = [
        "implement", "create feature", "add functionality",
        "bug fix", "integration", "api"
    ]

    KEYWORDS_SIMPLE = [
        "format", "docstring", "comment", "rename",
        "simple function", "helper", "utility"
    ]

    def analyze(self, task: str) -> TaskAnalysis:
        task_lower = task.lower()

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(task) // 4

        # Check for complexity keywords
        complexity = TaskComplexity.SIMPLE
        requires_reasoning = False

        if any(kw in task_lower for kw in self.KEYWORDS_COMPLEX):
            complexity = TaskComplexity.COMPLEX
            requires_reasoning = True
        elif any(kw in task_lower for kw in self.KEYWORDS_MODERATE):
            complexity = TaskComplexity.MODERATE
        elif any(kw in task_lower for kw in self.KEYWORDS_SIMPLE):
            complexity = TaskComplexity.TRIVIAL

        # Check for multi-file indicators
        if "multiple files" in task_lower or "across codebase" in task_lower:
            complexity = TaskComplexity.VERY_COMPLEX

        # Detect tool needs
        needs_tools = any(word in task_lower for word in [
            "read", "write", "file", "git", "run", "test", "execute"
        ])

        # Suggest model based on complexity
        suggested_model = self._suggest_model(complexity, estimated_tokens)

        return TaskAnalysis(
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            requires_reasoning=requires_reasoning,
            needs_tools=needs_tools,
            suggested_model=suggested_model
        )

    def _suggest_model(self, complexity: TaskComplexity, tokens: int) -> str:
        if complexity == TaskComplexity.TRIVIAL:
            return "ollama"  # Local fast model
        elif complexity == TaskComplexity.SIMPLE:
            return "ollama"  # Still local
        elif complexity == TaskComplexity.MODERATE:
            return "ollama" if tokens < 5000 else "claude-haiku"
        elif complexity == TaskComplexity.COMPLEX:
            return "claude-sonnet"
        else:  # VERY_COMPLEX
            return "claude-sonnet"
```

### Day 11-12: Router Implementation

**Create Smart Router:**
```python
# src/orchestrator/router.py
from .analyzer import TaskAnalyzer

class Router:
    def __init__(self, providers: dict, budget_manager=None):
        self.providers = providers
        self.analyzer = TaskAnalyzer()
        self.budget_manager = budget_manager

    async def route(self, task: str, override: str = None) -> tuple:
        """Returns (provider, analysis)"""

        # Manual override takes precedence
        if override:
            return self.providers[override], None

        # Analyze task
        analysis = self.analyzer.analyze(task)

        # Check budget constraints
        if self.budget_manager and self.budget_manager.is_near_limit():
            # Force local-only
            return self.providers["ollama"], analysis

        # Route based on analysis
        provider_name = analysis.suggested_model

        # Fallback if provider not available
        if provider_name not in self.providers:
            provider_name = "ollama"  # Safe default

        return self.providers[provider_name], analysis
```

### Day 13-14: Integrate Router into CLI

**Update CLI:**
```python
# Update CLI.run() method
async def run(self):
    router = Router(self.providers)

    while True:
        user_input = await self.session.prompt_async("You: ")

        # Parse override
        override = self.parse_model_override(user_input)

        # Route task
        provider, analysis = await router.route(user_input, override)

        # Show routing decision (optional)
        if analysis:
            self.console.print(
                f"[dim]Routing to {provider.__class__.__name__} "
                f"(complexity: {analysis.complexity.name})[/dim]"
            )

        # Execute...
        async for chunk in provider.chat([Message("user", user_input)], stream=True):
            # ... (same as before)
```

**Test Routing:**
```bash
You: format this code  # Should use local
You: implement OAuth with JWT tokens  # Should consider complexity
You: @claude fix this race condition  # Manual override
```

---

## Week 3: Tools & State

### Day 15-17: Basic Tool Integration

**Simple Tool System:**
```python
# src/tools/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class Tool(ABC):
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def parameters(self) -> Dict:
        """JSON schema for parameters"""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass

# src/tools/filesystem.py
import aiofiles
from .base import Tool

class ReadFileTool(Tool):
    def name(self) -> str:
        return "read_file"

    def description(self) -> str:
        return "Read contents of a file"

    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"]
        }

    async def execute(self, path: str) -> str:
        async with aiofiles.open(path, 'r') as f:
            return await f.read()

class WriteFileTool(Tool):
    def name(self) -> str:
        return "write_file"

    def description(self) -> str:
        return "Write content to a file"

    def parameters(self) -> Dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }

    async def execute(self, path: str, content: str) -> str:
        async with aiofiles.open(path, 'w') as f:
            await f.write(content)
        return f"Wrote {len(content)} bytes to {path}"

# src/tools/registry.py
class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name()] = tool

    def get_tool_schemas(self) -> list:
        """Format for Claude/OpenAI function calling"""
        return [
            {
                "name": tool.name(),
                "description": tool.description(),
                "input_schema": tool.parameters()
            }
            for tool in self.tools.values()
        ]

    async def execute(self, name: str, params: Dict) -> Any:
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        return await self.tools[name].execute(**params)
```

**Update Claude Provider for Tool Calling:**
```python
# Add to ClaudeProvider.chat()
async def chat(self, messages, temperature=0.7, max_tokens=4096, stream=False, tools=None):
    kwargs = {
        "model": self.model,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if tools:
        kwargs["tools"] = tools

    response = await self.client.messages.create(**kwargs)

    # Handle tool calls
    if response.stop_reason == "tool_use":
        tool_calls = [block for block in response.content if block.type == "tool_use"]
        return ToolResponse(tool_calls=tool_calls, model=self.model)

    # Regular response...
```

### Day 18-19: State Management

**Simple In-Memory State:**
```python
# src/state/manager.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4

@dataclass
class Event:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    agent_id: str = ""
    model_used: str = ""
    event_type: str = ""  # TASK_STARTED, TOOL_CALLED, etc.
    payload: Dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0

class StateManager:
    def __init__(self):
        self.events: List[Event] = []
        self.context: Dict[str, Any] = {}

    def record_event(self, event: Event):
        self.events.append(event)
        self._update_context(event)

    def _update_context(self, event: Event):
        """Update shared context based on event"""
        if event.event_type == "TOOL_RESULT":
            self.context[f"tool_result_{event.event_id}"] = event.payload

    def get_context_snapshot(self) -> Dict:
        return self.context.copy()

    def get_total_cost(self) -> float:
        return sum(e.cost for e in self.events)
```

### Day 20-21: Cost Tracking

**Budget Manager:**
```python
# src/orchestrator/budget.py
from datetime import datetime, timedelta

class BudgetManager:
    def __init__(self, daily_limit: float = 10.0):
        self.daily_limit = daily_limit
        self.costs_today: List[tuple[datetime, float]] = []

    def record_cost(self, cost: float):
        self.costs_today.append((datetime.now(), cost))
        self._cleanup_old_costs()

    def _cleanup_old_costs(self):
        """Remove costs older than 24 hours"""
        cutoff = datetime.now() - timedelta(days=1)
        self.costs_today = [(ts, cost) for ts, cost in self.costs_today if ts > cutoff]

    def get_today_total(self) -> float:
        return sum(cost for _, cost in self.costs_today)

    def is_near_limit(self, threshold: float = 0.8) -> bool:
        return self.get_today_total() >= (self.daily_limit * threshold)

    def remaining_budget(self) -> float:
        return max(0, self.daily_limit - self.get_today_total())
```

**Add :cost Command:**
```python
# In CLI.handle_command()
elif cmd == ":cost":
    total = self.state_manager.get_total_cost()
    remaining = self.budget_manager.remaining_budget()
    self.console.print(f"Session cost: ${total:.4f}")
    self.console.print(f"Remaining today: ${remaining:.2f}")
```

---

## Week 4: Polish & Testing

### Day 22-24: Error Handling & Retry Logic

**Robust Provider Wrapper:**
```python
# src/providers/resilient.py
import asyncio
from typing import Optional

class ResilientProvider:
    def __init__(self, provider, max_retries=3, timeout=30):
        self.provider = provider
        self.max_retries = max_retries
        self.timeout = timeout

    async def chat(self, *args, **kwargs):
        for attempt in range(self.max_retries):
            try:
                return await asyncio.wait_for(
                    self.provider.chat(*args, **kwargs),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                # Log error, retry
                await asyncio.sleep(1)
```

### Day 25-26: Configuration System

**YAML Config:**
```yaml
# config/models.yaml
providers:
  claude:
    api_key_env: ANTHROPIC_API_KEY
    models:
      sonnet:
        id: claude-sonnet-4-5-20250929
        cost_per_1m_input: 3.00
        cost_per_1m_output: 15.00
      haiku:
        id: claude-3-5-haiku-20250219
        cost_per_1m_input: 0.80
        cost_per_1m_output: 4.00

  ollama:
    base_url: http://localhost:11434
    models:
      qwen-8b:
        id: qwen2.5-coder:7b
      qwen-32b:
        id: qwen2.5-coder:32b

routing:
  strategy: predictive
  prefer_local: true
  budget:
    daily_limit: 10.00
    warning_threshold: 0.8
```

**Load Config:**
```python
# src/config/loader.py
import yaml
import os

def load_config(path="config/models.yaml"):
    with open(path) as f:
        config = yaml.safe_load(f)

    # Expand env vars
    for provider in config['providers'].values():
        if 'api_key_env' in provider:
            provider['api_key'] = os.getenv(provider['api_key_env'])

    return config
```

### Day 27-28: Testing & Documentation

**Unit Tests:**
```python
# tests/test_analyzer.py
import pytest
from src.orchestrator.analyzer import TaskAnalyzer, TaskComplexity

def test_simple_task():
    analyzer = TaskAnalyzer()
    result = analyzer.analyze("format this code")
    assert result.complexity == TaskComplexity.TRIVIAL
    assert result.suggested_model == "ollama"

def test_complex_task():
    analyzer = TaskAnalyzer()
    result = analyzer.analyze("design a microservices architecture")
    assert result.complexity == TaskComplexity.COMPLEX
    assert result.requires_reasoning == True

# Run tests
pytest tests/ -v
```

**Quick README:**
```markdown
# AutoCoder MVP

Multi-model coding assistant with intelligent routing.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
3. Pull model: `ollama pull qwen2.5-coder:7b`
4. Set API key: `export ANTHROPIC_API_KEY=your_key`
5. Run: `python main.py`

## Usage

- Type naturally, system routes to best model
- `@claude` - Force Claude
- `@local` - Force local model
- `:cost` - Show costs
- `:models` - List available models

## Features

✅ Intelligent routing based on task complexity
✅ Local model support (free inference)
✅ Cost tracking and budget management
✅ Basic tool calling (read/write files)
✅ Streaming responses
```

---

## MVP Complete Checklist

After 4 weeks, you should have:

- [x] **Multi-provider support** (Claude + Ollama)
- [x] **Intelligent routing** (complexity-based)
- [x] **CLI interface** (Rich + streaming)
- [x] **Tool integration** (filesystem basics)
- [x] **Cost tracking** (budget management)
- [x] **State management** (event log)
- [x] **Error handling** (retries, timeouts)
- [x] **Configuration** (YAML-based)
- [x] **Tests** (unit + integration)
- [x] **Documentation** (README + comments)

---

## Next Steps (Phase 2)

1. **Task Decomposition**: Break complex tasks into subtasks
2. **Parallel Execution**: Run independent subtasks concurrently
3. **More Providers**: Add OpenAI, Gemini
4. **vLLM Migration**: Replace Ollama for performance
5. **Prompt Caching**: Semantic + exact caching
6. **MCP Integration**: Standard tool protocol
7. **Fine-tuned Router**: Learn from usage patterns

---

## Cost Comparison (MVP)

**Example Session**: 10 coding tasks

| Approach | Estimated Cost |
|----------|----------------|
| Claude-only | $4.50 |
| GPT-4-only | $3.20 |
| **AutoCoder MVP** | **$1.20** |
| **Savings** | **73%** |

*Breakdown*: 7 simple tasks (local), 2 moderate (local), 1 complex (Claude)

---

## Common Issues & Solutions

**Issue**: Ollama not responding
```bash
# Check status
ollama list
# Restart
systemctl restart ollama  # Linux
brew services restart ollama  # Mac
```

**Issue**: Out of VRAM
```bash
# Use smaller quantization
ollama pull qwen2.5-coder:7b-q4  # 4-bit version
```

**Issue**: Slow inference
```bash
# Check GPU usage
nvidia-smi -l 1
# Reduce max_tokens
# Use Q4 quantization instead of Q6
```

**Issue**: Claude API errors
- Check API key: `echo $ANTHROPIC_API_KEY`
- Verify quota: https://console.anthropic.com
- Check rate limits (reduce concurrency)

---

## Performance Expectations

**Local Inference (Qwen 7B on RTX 4090):**
- Latency: 50-200ms to first token
- Throughput: 30-60 tokens/sec
- Quality: ~88% HumanEval (GPT-4 level)

**Cloud Inference (Claude):**
- Latency: 200-500ms to first token
- Throughput: 50-100 tokens/sec
- Quality: 86% HumanEval, 72% SWE-bench

**Routing Overhead:**
- Analysis: <100ms
- Negligible vs. inference time

---

## Scaling Considerations

**For Team Use:**
- Deploy as API server (FastAPI)
- Redis for shared state
- PostgreSQL for event log persistence
- Load balancer for multiple vLLM instances

**For Production:**
- Switch to vLLM (3x faster)
- Multi-GPU inference
- Kubernetes deployment
- Monitoring (Prometheus + Grafana)

---

**Good luck building! 🚀**

**Questions?** Open an issue in the repo or consult ARCHITECTURE.md for detailed design.
