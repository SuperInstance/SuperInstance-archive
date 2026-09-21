# Implementation Roadmap - Multi-Model Content Studio

**Goal**: Build API-based multi-model system that learns and optimizes itself

**Timeline**: 4-6 weeks to production
**Budget**: $50-200/month operational costs

---

## Overview

We're building this in phases, with each phase adding capability while remaining functional:

```
Week 1: Foundation  → Basic API layer working
Week 2: Routing     → Smart model selection
Week 3: Evaluation  → Judge system learning
Week 4: Learning    → Self-optimization
Week 5-6: Content   → Studio integration
```

---

## Phase 1: API Foundation (Week 1)

### Goal
Get multi-provider API layer working with cost tracking

### Success Criteria
- [ ] Make successful API calls to Claude, OpenAI, Groq, DeepInfra
- [ ] Track costs in real-time
- [ ] Unified interface abstracts provider differences
- [ ] Basic error handling and retries

### Tasks

#### Day 1-2: Project Setup

**1.1 Create new branch**
```bash
cd /home/activeloguser/content-studio-dev
git checkout -b feature/multi-model-api
```

**1.2 Set up API keys**
```bash
# Edit .env
nano .env
```

Add:
```bash
# Existing
ANTHROPIC_API_KEY=sk-ant-...

# New providers
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
DEEPINFRA_API_KEY=...
TOGETHER_API_KEY=...

# Database for tracking
DATABASE_URL=postgresql://user:pass@localhost/content_studio
REDIS_URL=redis://localhost:6379
```

**1.3 Install dependencies**
```bash
./venv/bin/pip install \
  anthropic \
  openai \
  groq \
  together \
  psycopg2-binary \
  redis \
  asyncpg \
  httpx
```

**1.4 Create new directory structure**
```bash
mkdir -p src/api_v2/{providers,models,routing,evaluation,learning}
mkdir -p tests/api_v2
mkdir -p config/models
```

#### Day 3-4: Provider Implementation

**File: src/api_v2/models/base.py**
```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class Provider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROQ = "groq"
    DEEPINFRA = "deepinfra"
    TOGETHER = "together"

@dataclass
class ModelInfo:
    """Model metadata"""
    id: str
    provider: Provider
    context_window: int
    cost_per_1m_input: float
    cost_per_1m_output: float
    strengths: list[str]
    max_output_tokens: int = 4096

@dataclass
class Message:
    """Chat message"""
    role: str  # system, user, assistant
    content: str

@dataclass
class CompletionRequest:
    """Request for completion"""
    messages: list[Message]
    model: str
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: Dict[str, Any] = None

@dataclass
class CompletionResponse:
    """Response from completion"""
    content: str
    model: str
    provider: Provider
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: int
    finish_reason: str
    request_id: str
    created_at: datetime
```

**File: src/api_v2/providers/base.py**
```python
from abc import ABC, abstractmethod
from typing import List, AsyncIterator
from ..models.base import (
    CompletionRequest,
    CompletionResponse,
    ModelInfo,
    Provider
)

class BaseProvider(ABC):
    """Abstract base for all API providers"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def complete(
        self,
        request: CompletionRequest
    ) -> CompletionResponse:
        """Generate completion"""
        pass

    @abstractmethod
    async def stream(
        self,
        request: CompletionRequest
    ) -> AsyncIterator[str]:
        """Stream completion (if supported)"""
        pass

    @abstractmethod
    def get_model_info(self, model: str) -> ModelInfo:
        """Get model metadata"""
        pass

    @abstractmethod
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD"""
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """List available models"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> Provider:
        """Provider enum"""
        pass
```

**File: src/api_v2/providers/anthropic_provider.py**
```python
import anthropic
import time
from datetime import datetime
from typing import List, AsyncIterator
from .base import BaseProvider
from ..models.base import *

class AnthropicProvider(BaseProvider):
    """Anthropic (Claude) API provider"""

    # Model registry
    MODELS = {
        "claude-opus-4": ModelInfo(
            id="claude-opus-4",
            provider=Provider.ANTHROPIC,
            context_window=200000,
            cost_per_1m_input=20.00,
            cost_per_1m_output=80.00,
            strengths=["complex_reasoning", "long_context", "planning"],
            max_output_tokens=8192
        ),
        "claude-sonnet-4.5": ModelInfo(
            id="claude-sonnet-4.5",
            provider=Provider.ANTHROPIC,
            context_window=200000,
            cost_per_1m_input=3.00,
            cost_per_1m_output=15.00,
            strengths=["balanced", "coding", "creative"],
            max_output_tokens=8192
        ),
        "claude-sonnet-3.5": ModelInfo(
            id="claude-3-5-sonnet-20241022",
            provider=Provider.ANTHROPIC,
            context_window=200000,
            cost_per_1m_input=3.00,
            cost_per_1m_output=15.00,
            strengths=["balanced", "general"],
            max_output_tokens=8192
        ),
        "claude-haiku-3.5": ModelInfo(
            id="claude-3-5-haiku-20241022",
            provider=Provider.ANTHROPIC,
            context_window=200000,
            cost_per_1m_input=0.80,
            cost_per_1m_output=4.00,
            strengths=["speed", "simple_tasks"],
            max_output_tokens=8192
        ),
    }

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        request: CompletionRequest
    ) -> CompletionResponse:
        """Generate completion using Claude"""
        start_time = time.time()

        # Convert messages format
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]

        # Extract system message if present
        system_msg = next(
            (m.content for m in request.messages if m.role == "system"),
            None
        )

        # API call
        response = await self.client.messages.create(
            model=self._get_model_id(request.model),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system_msg,
            messages=messages
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Calculate cost
        cost = self.calculate_cost(
            request.model,
            response.usage.input_tokens,
            response.usage.output_tokens
        )

        return CompletionResponse(
            content=response.content[0].text,
            model=request.model,
            provider=Provider.ANTHROPIC,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            finish_reason=response.stop_reason,
            request_id=response.id,
            created_at=datetime.now()
        )

    async def stream(
        self,
        request: CompletionRequest
    ) -> AsyncIterator[str]:
        """Stream completion"""
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role != "system"
        ]

        system_msg = next(
            (m.content for m in request.messages if m.role == "system"),
            None
        )

        async with self.client.messages.stream(
            model=self._get_model_id(request.model),
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            system=system_msg,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield text

    def get_model_info(self, model: str) -> ModelInfo:
        """Get model metadata"""
        return self.MODELS.get(model)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD"""
        info = self.get_model_info(model)
        if not info:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * info.cost_per_1m_input
        output_cost = (output_tokens / 1_000_000) * info.cost_per_1m_output

        return input_cost + output_cost

    def list_models(self) -> List[ModelInfo]:
        """List available models"""
        return list(self.MODELS.values())

    @property
    def provider_name(self) -> Provider:
        return Provider.ANTHROPIC

    def _get_model_id(self, model: str) -> str:
        """Get actual model ID for API"""
        info = self.MODELS.get(model)
        return info.id if info else model
```

**File: src/api_v2/providers/openai_provider.py**
```python
import openai
import time
from datetime import datetime
from typing import List, AsyncIterator
from .base import BaseProvider
from ..models.base import *

class OpenAIProvider(BaseProvider):
    """OpenAI API provider"""

    MODELS = {
        "gpt-4o": ModelInfo(
            id="gpt-4o",
            provider=Provider.OPENAI,
            context_window=128000,
            cost_per_1m_input=2.50,
            cost_per_1m_output=10.00,
            strengths=["multimodal", "structured", "tool_use"],
            max_output_tokens=16384
        ),
        "gpt-4o-mini": ModelInfo(
            id="gpt-4o-mini",
            provider=Provider.OPENAI,
            context_window=128000,
            cost_per_1m_input=0.15,
            cost_per_1m_output=0.60,
            strengths=["speed", "cost", "simple_reasoning"],
            max_output_tokens=16384
        ),
    }

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        request: CompletionRequest
    ) -> CompletionResponse:
        """Generate completion using GPT"""
        start_time = time.time()

        # Convert messages
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ]

        # API call
        response = await self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Calculate cost
        cost = self.calculate_cost(
            request.model,
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )

        return CompletionResponse(
            content=response.choices[0].message.content,
            model=request.model,
            provider=Provider.OPENAI,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost_usd=cost,
            duration_ms=duration_ms,
            finish_reason=response.choices[0].finish_reason,
            request_id=response.id,
            created_at=datetime.now()
        )

    async def stream(
        self,
        request: CompletionRequest
    ) -> AsyncIterator[str]:
        """Stream completion"""
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ]

        stream = await self.client.chat.completions.create(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=True
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_model_info(self, model: str) -> ModelInfo:
        return self.MODELS.get(model)

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        info = self.get_model_info(model)
        if not info:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * info.cost_per_1m_input
        output_cost = (output_tokens / 1_000_000) * info.cost_per_1m_output

        return input_cost + output_cost

    def list_models(self) -> List[ModelInfo]:
        return list(self.MODELS.values())

    @property
    def provider_name(self) -> Provider:
        return Provider.OPENAI
```

**Continue for Groq, DeepInfra** (similar pattern)

#### Day 5: Provider Factory & API Client

**File: src/api_v2/client.py**
```python
from typing import Optional, Dict
from .providers import *
from .models.base import *

class MultiModelClient:
    """Unified client for all AI providers"""

    def __init__(self, config: Dict[str, str]):
        """
        config: {
            'anthropic_key': '...',
            'openai_key': '...',
            'groq_key': '...',
            'deepinfra_key': '...'
        }
        """
        self.providers = {}

        if config.get('anthropic_key'):
            self.providers[Provider.ANTHROPIC] = AnthropicProvider(
                config['anthropic_key']
            )

        if config.get('openai_key'):
            self.providers[Provider.OPENAI] = OpenAIProvider(
                config['openai_key']
            )

        if config.get('groq_key'):
            self.providers[Provider.GROQ] = GroqProvider(
                config['groq_key']
            )

        if config.get('deepinfra_key'):
            self.providers[Provider.DEEPINFRA] = DeepInfraProvider(
                config['deepinfra_key']
            )

    async def complete(
        self,
        request: CompletionRequest
    ) -> CompletionResponse:
        """
        Route request to appropriate provider based on model prefix
        Example: "claude-sonnet-3.5" → Anthropic
        """
        provider = self._get_provider_for_model(request.model)

        if not provider:
            raise ValueError(f"No provider found for model: {request.model}")

        return await provider.complete(request)

    async def stream(
        self,
        request: CompletionRequest
    ) -> AsyncIterator[str]:
        """Stream completion"""
        provider = self._get_provider_for_model(request.model)

        if not provider:
            raise ValueError(f"No provider found for model: {request.model}")

        async for chunk in provider.stream(request):
            yield chunk

    def list_all_models(self) -> List[ModelInfo]:
        """List all available models from all providers"""
        models = []
        for provider in self.providers.values():
            models.extend(provider.list_models())
        return models

    def get_model_info(self, model: str) -> Optional[ModelInfo]:
        """Get info for specific model"""
        provider = self._get_provider_for_model(model)
        if provider:
            return provider.get_model_info(model)
        return None

    def _get_provider_for_model(self, model: str) -> Optional[BaseProvider]:
        """Determine provider from model name"""
        if model.startswith("claude"):
            return self.providers.get(Provider.ANTHROPIC)
        elif model.startswith("gpt"):
            return self.providers.get(Provider.OPENAI)
        elif "llama" in model.lower() and "groq" in model:
            return self.providers.get(Provider.GROQ)
        elif "llama" in model.lower():
            return self.providers.get(Provider.DEEPINFRA)

        return None
```

#### Day 6-7: Cost Tracking & Testing

**File: src/api_v2/tracking/cost_tracker.py**
```python
import asyncpg
from datetime import datetime
from ..models.base import CompletionResponse

class CostTracker:
    """Track API costs in PostgreSQL"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool = None

    async def init(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(self.db_url)

        # Create table if not exists
        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS api_calls (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(255),
                model VARCHAR(100),
                provider VARCHAR(50),
                input_tokens INT,
                output_tokens INT,
                cost_usd DECIMAL(10, 6),
                duration_ms INT,
                finish_reason VARCHAR(50),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

    async def track(
        self,
        response: CompletionResponse,
        metadata: dict = None
    ):
        """Track an API call"""
        await self.pool.execute("""
            INSERT INTO api_calls (
                request_id, model, provider, input_tokens, output_tokens,
                cost_usd, duration_ms, finish_reason, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
            response.request_id,
            response.model,
            response.provider.value,
            response.input_tokens,
            response.output_tokens,
            response.cost_usd,
            response.duration_ms,
            response.finish_reason,
            metadata or {}
        )

    async def get_daily_cost(self) -> float:
        """Get today's total cost"""
        row = await self.pool.fetchrow("""
            SELECT COALESCE(SUM(cost_usd), 0) as total
            FROM api_calls
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        return float(row['total'])

    async def get_cost_by_model(self, days: int = 7) -> dict:
        """Get cost breakdown by model"""
        rows = await self.pool.fetch("""
            SELECT
                model,
                COUNT(*) as call_count,
                SUM(cost_usd) as total_cost,
                AVG(cost_usd) as avg_cost,
                SUM(input_tokens) as total_input,
                SUM(output_tokens) as total_output
            FROM api_calls
            WHERE created_at > NOW() - INTERVAL '$1 days'
            GROUP BY model
            ORDER BY total_cost DESC
        """, days)

        return [dict(row) for row in rows]
```

**File: tests/api_v2/test_providers.py**
```python
import pytest
import os
from src.api_v2.client import MultiModelClient
from src.api_v2.models.base import CompletionRequest, Message

@pytest.mark.asyncio
async def test_anthropic_provider():
    """Test Claude API"""
    client = MultiModelClient({
        'anthropic_key': os.getenv('ANTHROPIC_API_KEY')
    })

    request = CompletionRequest(
        messages=[
            Message(role="user", content="Say hello in 5 words")
        ],
        model="claude-haiku-3.5",
        max_tokens=50
    )

    response = await client.complete(request)

    assert response.content
    assert response.cost_usd > 0
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    print(f"✓ Claude response: {response.content}")
    print(f"  Cost: ${response.cost_usd:.6f}")

@pytest.mark.asyncio
async def test_openai_provider():
    """Test OpenAI API"""
    client = MultiModelClient({
        'openai_key': os.getenv('OPENAI_API_KEY')
    })

    request = CompletionRequest(
        messages=[
            Message(role="user", content="Say hello in 5 words")
        ],
        model="gpt-4o-mini",
        max_tokens=50
    )

    response = await client.complete(request)

    assert response.content
    assert response.cost_usd > 0
    print(f"✓ OpenAI response: {response.content}")
    print(f"  Cost: ${response.cost_usd:.6f}")

@pytest.mark.asyncio
async def test_cost_comparison():
    """Compare costs across models"""
    client = MultiModelClient({
        'anthropic_key': os.getenv('ANTHROPIC_API_KEY'),
        'openai_key': os.getenv('OPENAI_API_KEY'),
        'groq_key': os.getenv('GROQ_API_KEY')
    })

    prompt = "Write a 100-word story about AI"

    models = [
        "claude-haiku-3.5",
        "gpt-4o-mini",
        "groq-llama-8b"
    ]

    results = []
    for model in models:
        request = CompletionRequest(
            messages=[Message(role="user", content=prompt)],
            model=model,
            max_tokens=200
        )

        response = await client.complete(request)
        results.append({
            'model': model,
            'cost': response.cost_usd,
            'duration': response.duration_ms,
            'quality': len(response.content)
        })

    # Print comparison
    print("\n=== Cost Comparison ===")
    for r in sorted(results, key=lambda x: x['cost']):
        print(f"{r['model']:20} ${r['cost']:.6f}  {r['duration']}ms")
```

### Week 1 Deliverables
- ✓ Multi-provider API client working
- ✓ Cost tracking in database
- ✓ Tests passing for all providers
- ✓ Can make calls to Claude, OpenAI, Groq, DeepInfra

**Estimated Cost**: $5-10 for testing

---

## Phase 2: Smart Routing (Week 2)

### Goal
Implement intelligent model selection based on task complexity

### Success Criteria
- [ ] Tasks automatically routed to appropriate models
- [ ] Cost 40-60% lower than using single premium model
- [ ] Routing decisions logged for analysis

### Tasks

#### Day 8-9: Task Analyzer

**File: src/api_v2/routing/complexity_analyzer.py**

*(Implementation details)*

#### Day 10-11: Model Router

**File: src/api_v2/routing/model_router.py**

*(Implementation details)*

#### Day 12-14: Testing & Optimization

---

## Phase 3: Evaluation System (Week 3)

### Goal
Judge system that evaluates outputs and learns preferences

*(Detailed task breakdown)*

---

## Phase 4: Learning & Optimization (Week 4)

### Goal
System learns which models excel at which tasks

*(Detailed task breakdown)*

---

## Phase 5-6: Content Studio Integration

### Goal
Apply multi-model system to content production

*(Detailed task breakdown)*

---

## Daily Checklist

### Every Day:
- [ ] Check daily API cost: `SELECT SUM(cost_usd) FROM api_calls WHERE DATE(created_at) = CURRENT_DATE`
- [ ] Review error logs
- [ ] Run test suite
- [ ] Commit progress to git

### Every Week:
- [ ] Review cost by model
- [ ] Analyze routing decisions
- [ ] Update model weights based on performance
- [ ] Document learnings

---

## Risk Mitigation

### Risk: API costs spiral out of control
**Mitigation**:
- Set hard limits in code
- Alert at 75% of daily budget
- Auto-switch to cheaper models if over budget
- Use free tiers (Groq) for testing

### Risk: One provider goes down
**Mitigation**:
- Implement fallback logic
- Test all providers weekly
- Have 3+ providers available

### Risk: Quality suffers with cheap models
**Mitigation**:
- Implement cascade logic (try cheap first, escalate if needed)
- Run A/B tests regularly
- Use judge system to catch poor outputs

---

## Success Metrics

### Week 1
- All provider APIs working ✓
- Cost tracking operational ✓
- <$10 spent on testing ✓

### Week 2
- Routing reducing costs by 40%+ ✓
- 90% of tasks routed correctly ✓
- <$20 spent ✓

### Week 3
- Judge system evaluating outputs ✓
- A/B tests running ✓
- Quality maintained ✓

### Week 4
- System learning from data ✓
- Cost-per-quality improving 10% weekly ✓
- Ready for production ✓

---

## Next Steps After Roadmap

1. Read [ARCHITECTURE_V2_MULTI_MODEL.md](ARCHITECTURE_V2_MULTI_MODEL.md) for full design
2. Read [API_COST_ANALYSIS_2025.md](API_COST_ANALYSIS_2025.md) for cost optimization
3. Create API accounts and get keys
4. Start Phase 1, Day 1!

---

**Estimated Total Cost**:
- Week 1 (testing): $10-20
- Week 2 (routing): $20-30
- Week 3 (evaluation): $30-40
- Week 4 (learning): $40-50
- **Total**: $100-140 to build entire system

**Estimated Monthly Operational Cost**: $50-200 depending on volume
