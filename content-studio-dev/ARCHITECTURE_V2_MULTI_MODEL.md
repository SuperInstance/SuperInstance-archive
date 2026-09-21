# Multi-Model Orchestration Architecture v2.0

## Vision

Build a self-improving, cost-optimized content production system that:
- Uses **multiple AI model providers** (Claude, OpenAI, Replicate, etc.)
- Routes tasks to **optimal models** based on complexity and cost
- Has **judge bots** that evaluate outputs and learn which models excel at what
- **Self-optimizes** through trial, error, and scoring
- Runs on **lightweight cloud instances** (all heavy lifting via API)
- **Bootstraps itself** - uses the system to build the system

## Core Philosophy

> "Use $200/month models for $2 tasks only when they're 100x better. Otherwise, use $0.02 models."

**Cost Efficiency Through Intelligence:**
- Claude Opus ($15/1M tokens) for complex orchestration
- Claude Sonnet ($3/1M tokens) for mid-complexity tasks
- Claude Haiku ($0.25/1M tokens) for simple tasks
- Llama 70B via Replicate ($0.65/1M tokens) for bulk text
- Llama 8B via Together AI ($0.20/1M tokens) for simple classification
- GPT-4 ($10/1M tokens) for specific tasks where it excels
- Open models for high-volume, low-complexity work

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    USER REQUEST                             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│            MASTER ORCHESTRATOR (Claude Opus)                │
│  - Understands full request context                         │
│  - Breaks into subtasks                                     │
│  - Manages overall quality                                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              MODEL ROUTER & TASK ANALYZER                   │
│  - Analyzes task complexity                                 │
│  - Checks performance history                               │
│  - Routes to optimal model                                  │
│  - Tracks costs in real-time                                │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
         ┌─────────────┼─────────────┐
         ↓             ↓             ↓
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Claude    │ │   OpenAI    │ │  Replicate  │
│   Agents    │ │   Agents    │ │   Agents    │
│             │ │             │ │             │
│ Opus/Sonnet │ │  GPT-4/4o   │ │ Llama 70B   │
│   /Haiku    │ │  GPT-4o-mini│ │ Llama 8B    │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┼───────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│              JUDGE & SCORING SYSTEM                         │
│  - Evaluates outputs from multiple models                   │
│  - Scores quality, cost, speed                              │
│  - Learns model strengths/weaknesses                        │
│  - Updates routing rules                                    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│           PERFORMANCE DATABASE (PostgreSQL)                 │
│  - Task history                                             │
│  - Model performance scores                                 │
│  - Cost tracking                                            │
│  - A/B test results                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Multi-Provider API Layer

**Purpose**: Abstract away provider differences, provide unified interface

```python
# src/api_layer/base_provider.py
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, model: str, **kwargs) -> Response:
        pass

    @abstractmethod
    def get_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        pass

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        pass

# Implementations:
# - ClaudeProvider (Anthropic API)
# - OpenAIProvider (OpenAI API)
# - ReplicateProvider (Replicate API)
# - TogetherProvider (Together AI)
# - HuggingFaceProvider (HF Inference API)
# - LocalProvider (future: Ollama for offline)
```

**Model Registry:**
```yaml
# config/model_registry.yaml
models:
  # Claude models
  claude-opus-4:
    provider: anthropic
    cost_per_1m_input: 15.00
    cost_per_1m_output: 75.00
    context_window: 200000
    strengths: [complex_reasoning, long_context, planning]

  claude-sonnet-3.5:
    provider: anthropic
    cost_per_1m_input: 3.00
    cost_per_1m_output: 15.00
    context_window: 200000
    strengths: [balanced, creative_writing, code]

  claude-haiku-3.5:
    provider: anthropic
    cost_per_1m_input: 0.25
    cost_per_1m_output: 1.25
    context_window: 200000
    strengths: [speed, simple_tasks, classification]

  # OpenAI models
  gpt-4o:
    provider: openai
    cost_per_1m_input: 2.50
    cost_per_1m_output: 10.00
    context_window: 128000
    strengths: [multimodal, structured_output, tool_use]

  gpt-4o-mini:
    provider: openai
    cost_per_1m_input: 0.15
    cost_per_1m_output: 0.60
    context_window: 128000
    strengths: [speed, cost, simple_reasoning]

  # Replicate models
  llama-3.1-70b:
    provider: replicate
    cost_per_1m_input: 0.65
    cost_per_1m_output: 2.75
    context_window: 128000
    strengths: [cost_effective, open_source, bulk_text]

  llama-3.1-8b:
    provider: replicate
    cost_per_1m_input: 0.05
    cost_per_1m_output: 0.25
    context_window: 128000
    strengths: [ultra_cheap, simple_tasks, high_volume]

  # Together AI models
  mistral-7b:
    provider: together
    cost_per_1m_input: 0.20
    cost_per_1m_output: 0.20
    context_window: 32000
    strengths: [cost, speed, simple_tasks]
```

### 2. Task Complexity Analyzer

**Purpose**: Classify tasks to route to appropriate models

```python
# src/routing/complexity_analyzer.py
class TaskComplexityAnalyzer:
    """
    Analyzes task complexity on multiple dimensions:
    - Reasoning depth (1-10)
    - Context required (tokens)
    - Creativity needed (1-10)
    - Precision required (1-10)
    - Output length expected
    """

    async def analyze(self, task: Task) -> ComplexityScore:
        # Use a fast, cheap model to analyze task complexity
        analysis_prompt = f"""
        Analyze this task's complexity:

        Task: {task.description}

        Rate 1-10:
        - reasoning_depth: How much logical reasoning needed?
        - creativity: How creative should the output be?
        - precision: How precise/accurate must it be?
        - context_size: How much context needed? (estimate tokens)

        Output JSON only.
        """

        # Use Claude Haiku or GPT-4o-mini for this meta-analysis
        result = await self.api.complete(
            prompt=analysis_prompt,
            model="claude-haiku-3.5",
            max_tokens=500
        )

        return ComplexityScore.from_json(result.content)
```

**Task Categories:**
```python
class TaskCategory(Enum):
    ULTRA_SIMPLE = "ultra_simple"      # Classification, yes/no, extract field
    SIMPLE = "simple"                  # Format text, simple rewrite, basic QA
    MODERATE = "moderate"              # Creative writing, summarization, translation
    COMPLEX = "complex"                # Analysis, multi-step reasoning, planning
    ULTRA_COMPLEX = "ultra_complex"    # Architecture, strategic planning, research

# Routing rules:
ROUTING_RULES = {
    TaskCategory.ULTRA_SIMPLE: ["llama-3.1-8b", "gpt-4o-mini", "claude-haiku-3.5"],
    TaskCategory.SIMPLE: ["claude-haiku-3.5", "gpt-4o-mini", "llama-3.1-70b"],
    TaskCategory.MODERATE: ["claude-sonnet-3.5", "gpt-4o", "llama-3.1-70b"],
    TaskCategory.COMPLEX: ["claude-sonnet-3.5", "gpt-4o", "claude-opus-4"],
    TaskCategory.ULTRA_COMPLEX: ["claude-opus-4", "gpt-4o"],
}
```

### 3. Model Router

**Purpose**: Select optimal model based on task, history, and cost

```python
# src/routing/model_router.py
class ModelRouter:
    """
    Routes tasks to optimal models using:
    - Task complexity score
    - Historical performance data
    - Current cost constraints
    - Model availability
    - A/B testing requirements
    """

    async def route(self, task: Task, user_id: str) -> ModelSelection:
        # 1. Analyze task complexity
        complexity = await self.complexity_analyzer.analyze(task)

        # 2. Get candidate models
        candidates = self.get_candidates(complexity.category)

        # 3. Filter by cost constraints
        if task.max_cost:
            candidates = [m for m in candidates if self.estimate_cost(m, task) <= task.max_cost]

        # 4. Check performance history
        performances = await self.db.get_model_performances(
            task_type=task.type,
            models=candidates
        )

        # 5. Apply selection strategy
        if self.should_ab_test(task):
            # Run same task on 2+ models, compare results
            selected = self.select_for_ab_test(candidates, performances)
        else:
            # Pick best based on historical performance
            selected = self.select_best(candidates, performances, complexity)

        # 6. Log routing decision
        await self.log_routing(task, selected, complexity, performances)

        return ModelSelection(
            primary=selected[0],
            alternatives=selected[1:],
            reasoning=self.explain_selection(selected, complexity)
        )

    def should_ab_test(self, task: Task) -> bool:
        """
        A/B test on:
        - 10% of all tasks (random sampling)
        - New task types (first 20 instances)
        - Tasks where model performance is similar
        """
        return (
            random.random() < 0.10 or
            self.is_new_task_type(task) or
            self.models_are_tied(task.type)
        )
```

### 4. Judge System

**Purpose**: Evaluate model outputs, score quality, update knowledge

```python
# src/evaluation/judge_system.py
class JudgeSystem:
    """
    Multi-level evaluation:
    1. Fast automated checks (format, completeness)
    2. Model-based quality scoring
    3. Human feedback loop (optional)
    """

    async def evaluate(self, task: Task, responses: List[ModelResponse]) -> Evaluation:
        # Level 1: Automated checks (fast, free)
        auto_scores = [self.automated_check(r) for r in responses]

        # Level 2: Model-based evaluation
        # Use a strong model to judge outputs
        judge_prompt = f"""
        Task: {task.description}

        Evaluate these {len(responses)} responses:

        {self.format_responses(responses)}

        Score each 0-100 on:
        - Accuracy: Does it correctly complete the task?
        - Quality: Is it well-written/formatted?
        - Completeness: Does it address all requirements?
        - Creativity: Is it engaging/original (if relevant)?

        Output JSON with scores and brief reasoning.
        """

        # Use Claude Opus or GPT-4 as judge
        judge_response = await self.api.complete(
            prompt=judge_prompt,
            model="claude-opus-4",  # Best model as judge
            max_tokens=2000
        )

        scores = JudgeScore.from_json(judge_response.content)

        # Level 3: Calculate cost-adjusted scores
        final_scores = []
        for i, (response, score) in enumerate(zip(responses, scores)):
            cost = self.calculate_cost(response)
            time = response.duration_ms

            # Quality per dollar metric
            quality_per_dollar = score.overall / cost if cost > 0 else score.overall

            # Quality per second metric
            quality_per_second = score.overall / (time / 1000) if time > 0 else score.overall

            final_scores.append(FinalScore(
                model=response.model,
                quality=score.overall,
                cost=cost,
                time_ms=time,
                quality_per_dollar=quality_per_dollar,
                quality_per_second=quality_per_second,
                dimensions=score
            ))

        # Store results in database
        await self.db.store_evaluation(task, responses, final_scores)

        # Update model routing preferences
        await self.update_routing_weights(task.type, final_scores)

        return Evaluation(
            winner=max(final_scores, key=lambda s: s.quality_per_dollar),
            all_scores=final_scores,
            recommendation=self.generate_recommendation(final_scores)
        )
```

**Judge Models:**
```python
JUDGE_MODELS = {
    "primary": "claude-opus-4",      # Main judge for important decisions
    "secondary": "gpt-4o",           # Second opinion for A/B tests
    "automated": "claude-haiku-3.5"  # Fast automated checks
}
```

### 5. Performance Database Schema

```sql
-- Track every API call
CREATE TABLE api_calls (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255),
    task_type VARCHAR(100),
    model VARCHAR(100),
    provider VARCHAR(50),
    prompt_tokens INT,
    completion_tokens INT,
    cost_usd DECIMAL(10, 6),
    duration_ms INT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track task evaluations
CREATE TABLE evaluations (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255),
    task_type VARCHAR(100),
    model VARCHAR(100),
    quality_score DECIMAL(5, 2),
    accuracy_score DECIMAL(5, 2),
    completeness_score DECIMAL(5, 2),
    creativity_score DECIMAL(5, 2),
    cost_usd DECIMAL(10, 6),
    duration_ms INT,
    quality_per_dollar DECIMAL(10, 2),
    judge_model VARCHAR(100),
    judge_reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track model performance over time
CREATE TABLE model_performance (
    id SERIAL PRIMARY KEY,
    model VARCHAR(100),
    task_type VARCHAR(100),
    time_window VARCHAR(50),  -- 'last_24h', 'last_7d', 'last_30d', 'all_time'
    total_tasks INT,
    avg_quality_score DECIMAL(5, 2),
    avg_cost_usd DECIMAL(10, 6),
    avg_duration_ms INT,
    avg_quality_per_dollar DECIMAL(10, 2),
    win_rate DECIMAL(5, 4),  -- % of A/B tests won
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Track routing decisions
CREATE TABLE routing_decisions (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255),
    task_type VARCHAR(100),
    complexity_category VARCHAR(50),
    complexity_score JSONB,
    selected_model VARCHAR(100),
    alternative_models JSONB,
    reasoning TEXT,
    was_ab_test BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Track A/B test results
CREATE TABLE ab_tests (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255),
    task_type VARCHAR(100),
    model_a VARCHAR(100),
    model_b VARCHAR(100),
    winner VARCHAR(100),
    quality_diff DECIMAL(5, 2),
    cost_diff_usd DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 6. Learning & Optimization System

**Purpose**: Continuously improve model selection based on data

```python
# src/learning/optimizer.py
class ModelOptimizer:
    """
    Learns from performance data to improve routing decisions:
    - Updates model performance weights
    - Identifies task types where models excel
    - Detects performance trends
    - Recommends new models to try
    """

    async def optimize_routing(self):
        """Run daily optimization"""
        # 1. Analyze last 24 hours of data
        recent_performance = await self.db.get_recent_performance(hours=24)

        # 2. Identify winners and losers by task type
        insights = self.analyze_performance(recent_performance)

        # 3. Update routing weights
        for task_type, model_scores in insights.items():
            current_weights = await self.db.get_routing_weights(task_type)
            new_weights = self.calculate_new_weights(current_weights, model_scores)
            await self.db.update_routing_weights(task_type, new_weights)

        # 4. Identify underperforming models
        underperformers = self.find_underperformers(insights)

        # 5. Suggest optimizations
        recommendations = self.generate_recommendations(insights, underperformers)

        return OptimizationReport(
            insights=insights,
            weight_updates=new_weights,
            recommendations=recommendations
        )

    def calculate_new_weights(self, current: Dict, scores: Dict) -> Dict:
        """
        Update weights using exponential moving average:
        new_weight = 0.7 * old_weight + 0.3 * recent_performance
        """
        new_weights = {}
        for model, old_weight in current.items():
            recent_score = scores.get(model, {}).get('quality_per_dollar', 0)
            new_weights[model] = 0.7 * old_weight + 0.3 * recent_score
        return new_weights
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal**: Multi-provider API working

```bash
# New directory structure
src/
├── api_layer/
│   ├── base_provider.py      # Abstract base
│   ├── anthropic_provider.py # Claude
│   ├── openai_provider.py    # OpenAI/Azure
│   ├── replicate_provider.py # Replicate
│   └── provider_factory.py   # Factory pattern
├── routing/
│   ├── complexity_analyzer.py
│   ├── model_router.py
│   └── routing_rules.yaml
└── models/
    ├── task.py
    ├── response.py
    └── model_info.py
```

**Tasks:**
- [ ] Implement `BaseProvider` abstract class
- [ ] Implement `AnthropicProvider` (Claude)
- [ ] Implement `OpenAIProvider` (GPT-4, GPT-4o-mini)
- [ ] Implement `ReplicateProvider` (Llama models)
- [ ] Create `ProviderFactory`
- [ ] Add cost tracking to all providers
- [ ] Create `model_registry.yaml` with pricing
- [ ] Unit tests for each provider

### Phase 2: Routing (Week 2)
**Goal**: Smart model selection working

**Tasks:**
- [ ] Implement `TaskComplexityAnalyzer`
- [ ] Implement `ModelRouter` with basic rules
- [ ] Create PostgreSQL schema
- [ ] Add routing decision logging
- [ ] Test routing with various task types

### Phase 3: Evaluation (Week 3)
**Goal**: Judge system evaluating outputs

**Tasks:**
- [ ] Implement `JudgeSystem`
- [ ] Implement automated checks
- [ ] Implement model-based scoring
- [ ] Store evaluations in database
- [ ] Create evaluation dashboard

### Phase 4: Learning (Week 4)
**Goal**: System optimizing itself

**Tasks:**
- [ ] Implement A/B testing logic
- [ ] Implement `ModelOptimizer`
- [ ] Create performance analytics
- [ ] Build optimization reports
- [ ] Add alert system for anomalies

### Phase 5: Content Studio Integration (Week 5-6)
**Goal**: Use system to build content studio

**Tasks:**
- [ ] Port existing bots to new architecture
- [ ] Replace Ollama calls with API routing
- [ ] Add specialized content tasks
- [ ] Implement judge for content quality
- [ ] Optimize for content workflows

---

## Cost Optimization Strategies

### Strategy 1: Tiered Processing
```python
# Example: Script writing task
async def write_script(story: Story):
    # Step 1: Outline (cheap model)
    outline = await api.complete(
        prompt=f"Create outline for: {story.title}",
        model="llama-3.1-8b",  # $0.05/1M tokens
        max_tokens=1000
    )

    # Step 2: Full script (mid-tier model)
    script = await api.complete(
        prompt=f"Write full script based on outline:\n{outline}",
        model="claude-sonnet-3.5",  # $3/1M tokens
        max_tokens=4000
    )

    # Step 3: Polish (premium model, but small task)
    final = await api.complete(
        prompt=f"Polish this script for clarity:\n{script}",
        model="claude-opus-4",  # $15/1M tokens
        max_tokens=4000
    )

    # Total cost: ~$0.005 + ~$0.024 + ~$0.120 = $0.15
    # vs using Opus for everything: ~$0.240
    # Savings: 37.5%
```

### Strategy 2: Parallel Competition
```python
# Run same task on 3 models, pick best
async def competitive_generation(task: Task):
    results = await asyncio.gather(
        api.complete(task, model="claude-sonnet-3.5"),
        api.complete(task, model="gpt-4o"),
        api.complete(task, model="llama-3.1-70b"),
    )

    # Judge picks winner (costs extra, but ensures quality)
    winner = await judge.evaluate(task, results)

    # Over time, learn which model wins for this task type
    # Then stop running competition for this task type
```

### Strategy 3: Batch Processing
```python
# Process similar tasks in batch with cheap model
async def batch_classify(items: List[str]):
    # Instead of 100 API calls, do 1 batch call
    prompt = f"""
    Classify each item as A, B, or C:
    {'\n'.join(f'{i}. {item}' for i, item in enumerate(items))}

    Output JSON array: ["A", "B", "C", ...]
    """

    result = await api.complete(
        prompt=prompt,
        model="gpt-4o-mini",  # Cheap, good at structured output
        max_tokens=500
    )

    # Cost: 1 API call instead of 100
    # Savings: 99%
```

---

## Monitoring & Dashboards

### Real-Time Cost Tracking
```python
# src/monitoring/cost_tracker.py
class CostTracker:
    async def track_call(self, model: str, input_tokens: int, output_tokens: int):
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        await self.redis.incrbyfloat(f"cost:today", cost)
        await self.redis.incrbyfloat(f"cost:model:{model}:today", cost)
        await self.redis.incr(f"calls:model:{model}:today")

        # Alert if over budget
        daily_cost = float(await self.redis.get("cost:today"))
        if daily_cost > self.daily_budget:
            await self.alert(f"Daily cost ${daily_cost:.2f} exceeds budget ${self.daily_budget:.2f}")
```

### Dashboard Views
1. **Cost Dashboard**
   - Total spend today/week/month
   - Cost per model
   - Cost per task type
   - Projection vs budget

2. **Performance Dashboard**
   - Model quality scores by task type
   - Win rates in A/B tests
   - Average response times
   - Success rates

3. **Optimization Dashboard**
   - Routing decisions
   - Cost savings from routing
   - Model recommendations
   - Learning trends

---

## Testing Infrastructure

### Small Instance Testing
```yaml
# test_instances.yaml
test_instances:
  micro:
    provider: aws
    type: t4g.micro  # 1 vCPU, 1GB RAM
    monthly_cost: 6.14
    purpose: Verify system runs on minimal resources

  small:
    provider: aws
    type: t4g.small  # 2 vCPU, 2GB RAM
    monthly_cost: 12.29
    purpose: Production-ready instance for API orchestration

  medium:
    provider: aws
    type: t4g.medium  # 2 vCPU, 4GB RAM
    monthly_cost: 24.58
    purpose: Testing with moderate load
```

**Test Suite:**
```python
# tests/test_small_instance.py
class SmallInstanceTests:
    """
    Verify system works on t4g.small (2GB RAM):
    - API layer loads
    - Multiple concurrent tasks
    - Database connections
    - Redis caching
    - Memory doesn't exceed 1.5GB
    """

    async def test_concurrent_tasks(self):
        """Run 10 concurrent API tasks"""
        tasks = [
            self.api.complete(f"Task {i}", model="claude-haiku-3.5")
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        assert all(r.success for r in results)

    async def test_memory_usage(self):
        """Verify memory stays under 1.5GB"""
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Run 100 tasks
        for i in range(100):
            await self.api.complete(f"Task {i}", model="gpt-4o-mini")

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        assert final_memory < 1536  # Less than 1.5GB
```

---

## Bootstrap Plan: Build Content Studio Using Itself

### Phase 1: Meta-Development
Use the multi-model system to design and build the content studio:

```python
# Example: System builds its own components
async def build_component(component_name: str):
    """Use AI to design, implement, and test a component"""

    # Step 1: Design (use premium model)
    design = await api.complete(
        prompt=f"""
        Design a {component_name} component for our content studio.
        Include: architecture, interfaces, key methods, error handling.
        Output: Technical specification in markdown.
        """,
        model="claude-opus-4",
        max_tokens=4000
    )

    # Step 2: Implement (use code-specialized model)
    implementation = await api.complete(
        prompt=f"""
        Implement this component:
        {design}

        Output: Complete Python code with docstrings and type hints.
        """,
        model="claude-sonnet-3.5",
        max_tokens=8000
    )

    # Step 3: Review (use multiple judges)
    reviews = await asyncio.gather(
        api.complete(f"Review this code:\n{implementation}", model="gpt-4o"),
        api.complete(f"Review this code:\n{implementation}", model="claude-opus-4"),
    )

    # Step 4: Refine based on reviews
    final_code = await api.complete(
        prompt=f"""
        Code:
        {implementation}

        Reviews:
        {reviews}

        Refine the code addressing all concerns.
        """,
        model="claude-opus-4",
        max_tokens=10000
    )

    return Component(design=design, code=final_code, reviews=reviews)
```

### Self-Improvement Loop
1. System builds a component using AI
2. System tests the component
3. Judge bots evaluate quality
4. System identifies improvements
5. System implements improvements
6. Repeat

---

## Next Steps

### Immediate (This Week):
1. **Create new branch**: `git checkout -b multi-model-v2`
2. **Set up API keys**:
   ```bash
   # .env
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-proj-...
   REPLICATE_API_TOKEN=r8_...
   TOGETHER_API_KEY=...
   ```
3. **Install new dependencies**:
   ```bash
   pip install anthropic openai replicate together psycopg2-binary
   ```
4. **Implement Phase 1** (API layer)

### This Month:
- Complete Phases 1-4
- Test on small AWS instance
- Run first A/B tests
- Gather initial performance data

### Next Month:
- Integrate with content studio
- Build first content using system
- Optimize based on data
- Add more providers (Azure, Cohere, etc.)

---

## Success Metrics

### Cost Efficiency
- **Target**: Average cost per content piece < $2
- **Measure**: Total API costs / total content pieces produced

### Quality
- **Target**: Average judge score > 85/100
- **Measure**: Judge evaluations across all content

### Learning Rate
- **Target**: 10% improvement in quality-per-dollar every 2 weeks
- **Measure**: Track quality_per_dollar metric over time

### System Efficiency
- **Target**: Run on t4g.small (2 vCPU, 2GB RAM)
- **Measure**: Memory usage < 1.5GB, CPU < 80%

---

## Questions to Answer Through Testing

1. **Which models excel at which content tasks?**
   - Script writing: Claude vs GPT-4 vs Llama 70B?
   - Image prompts: Which model generates best prompts?
   - Dialogue: Natural-sounding conversations?

2. **What's the optimal tiered approach?**
   - Can we do outline with cheap model, then full script with mid-tier?
   - When is premium model worth the cost?

3. **How much does A/B testing cost vs value?**
   - Running 2+ models costs 2x, but how much does quality improve?
   - Can we learn fast and then stop A/B testing for known tasks?

4. **Can we run on tiny instances?**
   - What's the minimum instance size that works?
   - Can we go serverless (AWS Lambda, Cloud Functions)?

---

This architecture lets us start immediately (no model downloads!), optimize costs through intelligence, and continuously improve through data. Ready to implement Phase 1?
