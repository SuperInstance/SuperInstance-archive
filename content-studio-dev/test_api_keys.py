#!/usr/bin/env python3
"""
Quick API Key Test Script
Tests all configured API keys
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("="*60)
print("Testing API Keys")
print("="*60 + "\n")

# Test Anthropic
print("1. Testing Anthropic (Claude)...")
anthropic_key = os.getenv("ANTHROPIC_API_KEY")
if anthropic_key and anthropic_key.startswith("sk-ant"):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=anthropic_key)

        # Simple test call
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Cheap model for testing
            max_tokens=50,
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )

        result = response.content[0].text
        print(f"   ✓ SUCCESS: {result}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage.input_tokens + response.usage.output_tokens}")
    except Exception as e:
        print(f"   ✗ FAILED: {str(e)[:100]}")
else:
    print("   ⚠ Key not configured")

print()

# Test OpenAI
print("2. Testing OpenAI (GPT)...")
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key and openai_key.startswith("sk-"):
    try:
        import openai
        client = openai.OpenAI(api_key=openai_key)

        # Simple test call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Cheap model for testing
            max_tokens=20,
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )

        result = response.choices[0].message.content
        print(f"   ✓ SUCCESS: {result}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage.total_tokens}")
    except Exception as e:
        print(f"   ✗ FAILED: {str(e)[:100]}")
else:
    print("   ⚠ Key not configured")

print()

# Test Groq
print("3. Testing Groq (Llama)...")
groq_key = os.getenv("GROQ_API_KEY")
if groq_key and groq_key.startswith("gsk_"):
    try:
        import groq
        client = groq.Groq(api_key=groq_key)

        # Simple test call
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Free model
            max_tokens=20,
            messages=[{"role": "user", "content": "Say hello in 3 words"}]
        )

        result = response.choices[0].message.content
        print(f"   ✓ SUCCESS: {result}")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage.total_tokens}")
    except Exception as e:
        print(f"   ✗ FAILED: {str(e)[:100]}")
else:
    print("   ⚠ Key not configured")

print("\n" + "="*60)
print("API Key Testing Complete")
print("="*60)
