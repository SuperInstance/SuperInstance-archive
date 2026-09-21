# Getting Started - Multi-Model API System v2

**You asked**: Can we use APIs with better models for orchestration and lightweight models for simple tasks, with bots judging each other and learning what works best?

**Answer**: YES! Here's how to build it.

---

## What We're Building

A self-improving multi-agent system that:
1. Uses **multiple AI providers** (Claude, OpenAI, Groq, DeepInfra)
2. **Intelligently routes** tasks to optimal models
3. Has **judge bots** that evaluate outputs and score performance
4. **Learns over time** which models excel at which tasks
5. Runs on **small cloud instances** (all compute via API)
6. **Optimizes costs** automatically (80-95% savings possible!)

---

## The Big Picture

```
Your Request
    ↓
[Master Orchestrator] ← Claude Opus (smart, expensive, used sparingly)
    ↓
[Task Analyzer] ← Cheap model analyzes complexity
    ↓
[Model Router] ← Routes to best model based on task + history
    ↓
┌────────────┬───────────┬─────────────┬──────────────┐
│  Claude    │  OpenAI   │    Groq     │  DeepInfra   │
│  (quality) │ (balance) │   (fast)    │   (cheap)    │
└────────────┴───────────┴─────────────┴──────────────┘
    ↓
[Judge System] ← Evaluates outputs, scores quality
    ↓
[Learning System] ← Updates routing rules based on performance
```

---

## Phase 1: Get APIs Working (Week 1)

### Step 1: Get API Keys

**Anthropic (Claude)**
1. Go to https://console.anthropic.com/
2. Sign up / sign in
3. Click "API Keys"
4. Create key named "Content Studio v2"
5. Copy key (starts with `sk-ant-...`)

**OpenAI (GPT)**
1. Go to https://platform.openai.com/
2. Sign in
3. Go to API keys
4. Create new key
5. Copy (starts with `sk-proj-...`)

**Groq (Free Fast Llama)**
1. Go to https://console.groq.com/
2. Sign up (FREE tier available!)
3. Create API key
4. Copy (starts with `gsk_...`)

**DeepInfra (Cheapest Llama)**
1. Go to https://deepinfra.com/
2. Sign up
3. Get API key
4. Copy

### Step 2: Add Keys to .env

```bash
cd /home/activeloguser/content-studio-dev
nano .env
```

Add these lines:
```bash
# Multi-model API keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
DEEPINFRA_API_KEY=...

# Database for tracking (we'll set up later)
DATABASE_URL=postgresql://localhost/content_studio
REDIS_URL=redis://localhost:6379
```

Save: `Ctrl+X`, `Y`, `Enter`

### Step 3: Install New Dependencies

```bash
./venv/bin/pip install anthropic openai groq together psycopg2-binary redis asyncpg httpx
```

### Step 4: Test Each Provider

Create test file:
```bash
nano test_api_v2.py
```

```python
#!/usr/bin/env python3
"""
Quick test of multi-model APIs
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_anthropic():
    """Test Claude"""
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 5 words"}]
        )

        content = response.content[0].text
        cost = (response.usage.input_tokens / 1_000_000) * 0.80 + \
               (response.usage.output_tokens / 1_000_000) * 4.00

        print(f"✓ Claude: {content}")
        print(f"  Cost: ${cost:.6f}")
        return True
    except Exception as e:
        print(f"✗ Claude failed: {e}")
        return False

async def test_openai():
    """Test OpenAI"""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 5 words"}]
        )

        content = response.choices[0].message.content
        cost = (response.usage.prompt_tokens / 1_000_000) * 0.15 + \
               (response.usage.completion_tokens / 1_000_000) * 0.60

        print(f"✓ OpenAI: {content}")
        print(f"  Cost: ${cost:.6f}")
        return True
    except Exception as e:
        print(f"✗ OpenAI failed: {e}")
        return False

async def test_groq():
    """Test Groq (free tier!)"""
    try:
        from groq import AsyncGroq

        client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))

        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 5 words"}]
        )

        content = response.choices[0].message.content
        cost = (response.usage.prompt_tokens / 1_000_000) * 0.05 + \
               (response.usage.completion_tokens / 1_000_000) * 0.08

        print(f"✓ Groq: {content}")
        print(f"  Cost: ${cost:.6f}")
        print(f"  Speed: Ultra-fast! (LPU hardware)")
        return True
    except Exception as e:
        print(f"✗ Groq failed: {e}")
        return False

async def main():
    print("=== Testing Multi-Model APIs ===\n")

    results = await asyncio.gather(
        test_anthropic(),
        test_openai(),
        test_groq()
    )

    print(f"\n=== Results ===")
    print(f"Working: {sum(results)}/3")

    if all(results):
        print("\n✓ All APIs working! Ready for Phase 1.")
    else:
        print("\n! Some APIs failed. Check your API keys in .env")

if __name__ == "__main__":
    asyncio.run(main())
```

Run the test:
```bash
python test_api_v2.py
```

**Expected output**:
```
=== Testing Multi-Model APIs ===

✓ Claude: Hello, how are you today?
  Cost: $0.000023
✓ OpenAI: Hi there! Nice day!
  Cost: $0.000018
✓ Groq: Hello! How are you?
  Cost: $0.000004
  Speed: Ultra-fast! (LPU hardware)

=== Results ===
Working: 3/3

✓ All APIs working! Ready for Phase 1.
```

---

## Phase 2: Build the System (Week 1-2)

### Architecture Files to Create

Follow [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) for detailed steps.

**Week 1**:
- `src/api_v2/models/base.py` - Data models
- `src/api_v2/providers/base.py` - Abstract provider
- `src/api_v2/providers/anthropic_provider.py` - Claude
- `src/api_v2/providers/openai_provider.py` - OpenAI
- `src/api_v2/providers/groq_provider.py` - Groq
- `src/api_v2/client.py` - Unified client
- `src/api_v2/tracking/cost_tracker.py` - Cost tracking

**Week 2**:
- `src/api_v2/routing/complexity_analyzer.py` - Analyze tasks
- `src/api_v2/routing/model_router.py` - Route to best model
- Tests and optimization

---

## Quick Win: Try Cost Comparison

Create `compare_costs.py`:
```python
#!/usr/bin/env python3
"""
Compare costs across different models for same task
"""
import asyncio
import os
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

async def test_all_models(prompt: str):
    """Run same prompt on 3 different models"""

    # Claude Haiku (fast, cheap)
    claude = AsyncAnthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    c_response = await claude.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    c_cost = (c_response.usage.input_tokens / 1_000_000) * 0.80 + \
             (c_response.usage.output_tokens / 1_000_000) * 4.00

    # GPT-4o-mini (cheap, fast)
    openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    o_response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    o_cost = (o_response.usage.prompt_tokens / 1_000_000) * 0.15 + \
             (o_response.usage.completion_tokens / 1_000_000) * 0.60

    # Groq Llama (ultra cheap, ultra fast)
    groq_client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
    g_response = await groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    g_cost = (g_response.usage.prompt_tokens / 1_000_000) * 0.05 + \
             (g_response.usage.completion_tokens / 1_000_000) * 0.08

    # Print comparison
    print(f"\n=== Prompt: {prompt[:50]}... ===\n")

    print(f"Claude Haiku:")
    print(f"  Response: {c_response.content[0].text[:100]}...")
    print(f"  Cost: ${c_cost:.6f}")

    print(f"\nGPT-4o-mini:")
    print(f"  Response: {o_response.choices[0].message.content[:100]}...")
    print(f"  Cost: ${o_cost:.6f}")

    print(f"\nGroq Llama 8B:")
    print(f"  Response: {g_response.choices[0].message.content[:100]}...")
    print(f"  Cost: ${g_cost:.6f}")
    print(f"  (Ultra-fast!)")

    print(f"\n=== Cost Comparison ===")
    print(f"Cheapest: Groq at ${g_cost:.6f}")
    print(f"Groq is {c_cost/g_cost:.1f}x cheaper than Claude")
    print(f"Groq is {o_cost/g_cost:.1f}x cheaper than OpenAI")

asyncio.run(test_all_models(
    "Write a 50-word summary of how AI models work"
))
```

Run it:
```bash
python compare_costs.py
```

This shows you the cost differences in action!

---

## Understanding the Savings

### Example: Generate 30 Scripts

**All Claude Opus** (premium for everything):
- 30 scripts × $1.00 each = **$30.00**

**Smart Routing**:
- Index stories (simple): Groq 8B × 30 = $0.006
- Create outlines (simple): Groq 70B × 30 = $0.030
- Write scripts (moderate): Claude Sonnet × 30 = $6.00
- Review quality (complex): Claude Opus × 30 = $4.50
- **Total: $10.54**

**Savings: 65%** just by routing intelligently!

---

## Next Steps

### Today (30 minutes):
1. ✓ Get API keys from all providers
2. ✓ Add keys to `.env`
3. ✓ Run `test_api_v2.py`
4. ✓ Run `compare_costs.py`

### This Week (10-15 hours):
1. Read [ARCHITECTURE_V2_MULTI_MODEL.md](ARCHITECTURE_V2_MULTI_MODEL.md)
2. Read [API_COST_ANALYSIS_2025.md](API_COST_ANALYSIS_2025.md)
3. Follow [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) Week 1
4. Build provider abstraction layer
5. Add cost tracking
6. Test with real content tasks

### Next Week:
1. Implement task complexity analyzer
2. Build model router
3. Test routing decisions
4. See 40-60% cost savings!

### Week 3-4:
1. Add judge system
2. Implement A/B testing
3. Build learning/optimization
4. Watch system improve itself!

---

## Key Documents

| Document | Purpose | Read When |
|----------|---------|-----------|
| **GETTING_STARTED_V2.md** | 👈 You are here | Start here |
| **ARCHITECTURE_V2_MULTI_MODEL.md** | Full system design | Before coding |
| **API_COST_ANALYSIS_2025.md** | Cost optimization strategies | Planning budget |
| **IMPLEMENTATION_ROADMAP.md** | Week-by-week build plan | During development |

---

## FAQ

**Q: Do I need the Ollama models anymore?**
A: Not to start! Focus on APIs first. We can add local models later for even more cost savings.

**Q: What if I only have slow internet?**
A: Perfect! APIs are ideal for slow internet. You're only sending text prompts (small), not downloading 5GB models.

**Q: How much will testing cost?**
A: Week 1 testing: $5-10. Use Groq free tier to minimize costs.

**Q: Can I run this on a tiny instance?**
A: YES! That's the point. A t4g.small (2GB RAM, $12/month) can handle this since all compute is via API.

**Q: What about GPU usage?**
A: You don't need GPU! All inference happens on provider servers. Your laptop/small instance just orchestrates.

**Q: How does the judge system work?**
A: After a bot completes a task, a judge bot (using a premium model) evaluates the output and scores it. Over time, we learn which models perform best at which tasks.

**Q: When will I see cost savings?**
A: Immediately! Even basic routing (cheap models for simple tasks, premium for complex) saves 40-60%.

**Q: Can this build itself?**
A: YES! That's Phase 5. We'll use the multi-model system to design, implement, and test new components. Meta!

---

## Support

**Stuck?** Check:
1. API keys in `.env` are correct
2. Virtual environment activated: `source venv/bin/activate`
3. Dependencies installed: `pip list | grep -E "anthropic|openai|groq"`

**Questions?**
- Read the architecture doc for system design
- Read the cost analysis for optimization strategies
- Read the roadmap for implementation steps

---

## Let's Build! 🚀

You now have:
- ✓ Clear architecture
- ✓ Cost analysis and optimization strategies
- ✓ Week-by-week implementation plan
- ✓ Starter code and tests

**Your next command**:
```bash
python test_api_v2.py
```

Then start Week 1 of the implementation roadmap!

---

**Built for**: Bootstrapping a self-improving multi-agent content studio
**Cost**: $50-200/month operational (vs $500-2000 without optimization)
**Timeline**: 4-6 weeks to production
**ROI**: 80-95% cost savings = break-even in < 1 month

Let's do this! 🎬✨
