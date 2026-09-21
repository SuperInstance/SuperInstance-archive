#!/usr/bin/env python3
"""
Compare costs across different models for same task

Shows real cost differences between models to help guide routing decisions.

Run: python compare_costs.py
"""
import asyncio
import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

async def test_all_models(prompt: str):
    """Run same prompt on different models and compare costs"""

    print(f"\n{'='*60}")
    print(f"Prompt: {prompt}")
    print(f"{'='*60}\n")

    results = []

    # Test Claude Haiku (cheap Claude)
    try:
        from anthropic import AsyncAnthropic

        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key and api_key != 'your_anthropic_api_key_here':
            print("Testing Claude 3.5 Haiku...")
            start = time.time()

            claude = AsyncAnthropic(api_key=api_key)
            c_response = await claude.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            duration = time.time() - start
            content = c_response.content[0].text
            cost = (c_response.usage.input_tokens / 1_000_000) * 0.80 + \
                   (c_response.usage.output_tokens / 1_000_000) * 4.00

            results.append({
                'name': 'Claude 3.5 Haiku',
                'provider': 'Anthropic',
                'cost': cost,
                'duration': duration,
                'tokens_in': c_response.usage.input_tokens,
                'tokens_out': c_response.usage.output_tokens,
                'content': content,
                'cost_per_char': cost / len(content) if content else 0
            })
            print(f"  ✓ Done ({duration:.2f}s)\n")
    except Exception as e:
        print(f"  ✗ Skipped: {e}\n")

    # Test GPT-4o-mini
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print("Testing GPT-4o-mini...")
            start = time.time()

            openai_client = AsyncOpenAI(api_key=api_key)
            o_response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            duration = time.time() - start
            content = o_response.choices[0].message.content
            cost = (o_response.usage.prompt_tokens / 1_000_000) * 0.15 + \
                   (o_response.usage.completion_tokens / 1_000_000) * 0.60

            results.append({
                'name': 'GPT-4o-mini',
                'provider': 'OpenAI',
                'cost': cost,
                'duration': duration,
                'tokens_in': o_response.usage.prompt_tokens,
                'tokens_out': o_response.usage.completion_tokens,
                'content': content,
                'cost_per_char': cost / len(content) if content else 0
            })
            print(f"  ✓ Done ({duration:.2f}s)\n")
    except Exception as e:
        print(f"  ✗ Skipped: {e}\n")

    # Test Groq Llama 8B (ultra cheap, ultra fast)
    try:
        from groq import AsyncGroq

        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            print("Testing Groq Llama 3.1 8B (FREE tier)...")
            start = time.time()

            groq_client = AsyncGroq(api_key=api_key)
            g_response = await groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

            duration = time.time() - start
            content = g_response.choices[0].message.content
            cost = (g_response.usage.prompt_tokens / 1_000_000) * 0.05 + \
                   (g_response.usage.completion_tokens / 1_000_000) * 0.08

            results.append({
                'name': 'Groq Llama 3.1 8B',
                'provider': 'Groq',
                'cost': cost,
                'duration': duration,
                'tokens_in': g_response.usage.prompt_tokens,
                'tokens_out': g_response.usage.completion_tokens,
                'content': content,
                'cost_per_char': cost / len(content) if content else 0,
                'note': 'FREE tier available!'
            })
            print(f"  ✓ Done ({duration:.2f}s) - Ultra fast!\n")
    except Exception as e:
        print(f"  ✗ Skipped: {e}\n")

    if not results:
        print("✗ No models tested successfully")
        print("Check API keys in .env")
        return

    # Sort by cost
    results.sort(key=lambda x: x['cost'])

    # Print comparison
    print(f"\n{'='*60}")
    print("COST COMPARISON")
    print(f"{'='*60}\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['name']} ({r['provider']})")
        print(f"   Cost: ${r['cost']:.6f}")
        print(f"   Speed: {r['duration']:.2f}s")
        print(f"   Tokens: {r['tokens_in']} in, {r['tokens_out']} out")
        print(f"   Output length: {len(r['content'])} chars")
        print(f"   Cost per char: ${r['cost_per_char']:.8f}")
        if r.get('note'):
            print(f"   Note: {r['note']}")
        print()

    # Show responses
    print(f"{'='*60}")
    print("RESPONSE QUALITY")
    print(f"{'='*60}\n")

    for r in results:
        print(f"{r['name']}:")
        print(f"  {r['content'][:200]}...")
        print()

    # Calculate savings
    if len(results) > 1:
        cheapest = results[0]
        most_expensive = results[-1]

        print(f"{'='*60}")
        print("SAVINGS ANALYSIS")
        print(f"{'='*60}\n")

        print(f"Cheapest: {cheapest['name']} at ${cheapest['cost']:.6f}")
        print(f"Most expensive: {most_expensive['name']} at ${most_expensive['cost']:.6f}")

        if cheapest['cost'] > 0:
            savings_pct = ((most_expensive['cost'] - cheapest['cost']) / most_expensive['cost']) * 100
            multiplier = most_expensive['cost'] / cheapest['cost']

            print(f"\nSavings: {savings_pct:.1f}%")
            print(f"Multiplier: {multiplier:.1f}x cheaper")

            print(f"\nAt scale (1000 requests):")
            print(f"  {cheapest['name']}: ${cheapest['cost'] * 1000:.2f}")
            print(f"  {most_expensive['name']}: ${most_expensive['cost'] * 1000:.2f}")
            print(f"  You save: ${(most_expensive['cost'] - cheapest['cost']) * 1000:.2f}")

    print(f"\n{'='*60}")
    print("KEY INSIGHT")
    print(f"{'='*60}\n")
    print("For simple tasks, using the cheapest model can save 80-95%!")
    print("Reserve expensive models for complex reasoning tasks.")
    print("\nThis is why smart routing matters! 💡")

async def main():
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║          Multi-Model Cost Comparison                    ║")
    print("╚══════════════════════════════════════════════════════════╝")

    # Test with a simple task
    await test_all_models(
        "Write a 50-word summary of how AI language models work."
    )

    print("\n" + "="*60)
    print("TIP: For your content studio")
    print("="*60)
    print("• Use Groq for simple tasks (indexing, classification)")
    print("• Use GPT-4o-mini for moderate tasks (formatting, simple writing)")
    print("• Use Claude Sonnet for creative content (scripts, stories)")
    print("• Use Claude Opus only for final review/orchestration")
    print("\nExpected savings: 60-80% vs using premium models for everything")
    print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
