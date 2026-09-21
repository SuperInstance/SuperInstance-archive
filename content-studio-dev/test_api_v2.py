#!/usr/bin/env python3
"""
Quick test of multi-model APIs

Tests basic connectivity to:
- Anthropic (Claude)
- OpenAI (GPT)
- Groq (fast Llama)

Run: python test_api_v2.py
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

async def test_anthropic():
    """Test Claude Haiku (cheapest Claude model)"""
    try:
        from anthropic import AsyncAnthropic

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key or api_key == 'your_anthropic_api_key_here':
            print("✗ Claude: No API key in .env")
            return False

        client = AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 5 words"}]
        )

        content = response.content[0].text
        cost = (response.usage.input_tokens / 1_000_000) * 0.80 + \
               (response.usage.output_tokens / 1_000_000) * 4.00

        print(f"✓ Claude Haiku:")
        print(f"  Response: {content}")
        print(f"  Cost: ${cost:.6f}")
        print(f"  Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
        return True

    except ImportError:
        print("✗ Claude: anthropic package not installed")
        print("  Run: pip install anthropic")
        return False
    except Exception as e:
        print(f"✗ Claude failed: {e}")
        return False

async def test_openai():
    """Test GPT-4o-mini (cheapest OpenAI model)"""
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("✗ OpenAI: No API key in .env")
            return False

        client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 5 words"}]
        )

        content = response.choices[0].message.content
        cost = (response.usage.prompt_tokens / 1_000_000) * 0.15 + \
               (response.usage.completion_tokens / 1_000_000) * 0.60

        print(f"✓ GPT-4o-mini:")
        print(f"  Response: {content}")
        print(f"  Cost: ${cost:.6f}")
        print(f"  Tokens: {response.usage.prompt_tokens} in, {response.usage.completion_tokens} out")
        return True

    except ImportError:
        print("✗ OpenAI: openai package not installed")
        print("  Run: pip install openai")
        return False
    except Exception as e:
        print(f"✗ OpenAI failed: {e}")
        return False

async def test_groq():
    """Test Groq Llama 8B (FREE tier available!)"""
    try:
        from groq import AsyncGroq

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("✗ Groq: No API key in .env")
            print("  Get free key at: https://console.groq.com/")
            return False

        client = AsyncGroq(api_key=api_key)

        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 5 words"}]
        )

        content = response.choices[0].message.content
        cost = (response.usage.prompt_tokens / 1_000_000) * 0.05 + \
               (response.usage.completion_tokens / 1_000_000) * 0.08

        print(f"✓ Groq Llama 8B:")
        print(f"  Response: {content}")
        print(f"  Cost: ${cost:.6f} (or FREE on free tier!)")
        print(f"  Tokens: {response.usage.prompt_tokens} in, {response.usage.completion_tokens} out")
        print(f"  Speed: Ultra-fast (LPU hardware)")
        return True

    except ImportError:
        print("✗ Groq: groq package not installed")
        print("  Run: pip install groq")
        return False
    except Exception as e:
        print(f"✗ Groq failed: {e}")
        return False

async def main():
    print("╔══════════════════════════════════════════╗")
    print("║   Multi-Model API Test                  ║")
    print("╚══════════════════════════════════════════╝\n")

    results = await asyncio.gather(
        test_anthropic(),
        test_openai(),
        test_groq()
    )

    print(f"\n{'='*45}")
    print(f"Results: {sum(results)}/3 providers working")
    print(f"{'='*45}\n")

    if all(results):
        print("✓ All APIs working!")
        print("✓ Ready to start Phase 1")
        print("\nNext steps:")
        print("1. Read GETTING_STARTED_V2.md")
        print("2. Run: python compare_costs.py")
        print("3. Follow IMPLEMENTATION_ROADMAP.md Week 1")
    elif any(results):
        print("! Some APIs working")
        print("! Fix the failed ones or continue with working APIs")
        print("\nTip: Groq has a FREE tier - start there!")
    else:
        print("✗ No APIs working")
        print("\nCheck:")
        print("1. API keys in .env file")
        print("2. pip install anthropic openai groq")
        print("3. Internet connection")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
