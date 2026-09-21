#!/usr/bin/env python3
"""
Integration Test Script
Tests all major components without requiring API keys
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print(" "*15 + "🧪 INTEGRATION TEST SUITE")
print("="*70 + "\n")

# Track test results
passed = []
failed = []
warnings = []


def test_section(name):
    """Print test section header"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"{'='*70}\n")


def test(description):
    """Test decorator/context"""
    print(f"  Testing: {description}...", end=" ")
    return description


def success(desc):
    """Mark test as passed"""
    print("✓")
    passed.append(desc)


def fail(desc, error):
    """Mark test as failed"""
    print(f"✗\n    Error: {error}")
    failed.append((desc, error))


def warn(desc, message):
    """Mark test as warning"""
    print(f"⚠️\n    Warning: {message}")
    warnings.append((desc, message))


# Test 1: Import Tests
test_section("Core Imports")

desc = test("Import orchestrator")
try:
    from src.orchestrator.orchestrator_v2 import ContentStudioOrchestrator
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import resource manager")
try:
    from src.resources.resource_manager import ResourceManager
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import API client")
try:
    from src.api.api_client import APIClient
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import foreman bot")
try:
    from src.bots.foreman_bot import ForemanBot
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import base bot")
try:
    from src.bots.base_bot import BaseBot, BotConfig
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import content bots")
try:
    from src.bots.content_bots import (
        ScriptWriterBot, ImagePrompterBot, DialogueFormatterBot
    )
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import research bots")
try:
    from src.bots.research_bots import (
        BackgroundResearcherBot, SummarizerBot
    )
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Import JSON parser")
try:
    from src.utils.json_parser import extract_json_from_text, safe_json_parse
    success(desc)
except Exception as e:
    fail(desc, str(e))

# Test 2: Component Initialization
test_section("Component Initialization")

desc = test("Initialize ResourceManager")
try:
    from src.resources.resource_manager import ResourceManager
    rm = ResourceManager(cpu_cores=4, gpu_available=False)
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Initialize APIClient")
try:
    from src.api.api_client import APIClient
    client = APIClient()
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Check model provider mapping")
try:
    from src.api.api_client import APIClient
    client = APIClient()
    provider = client.get_provider_for_model("gpt-4o-mini")
    assert provider == "openai", f"Expected 'openai', got '{provider}'"
    success(desc)
except Exception as e:
    fail(desc, str(e))

# Test 3: JSON Parser
test_section("JSON Parser")

desc = test("Parse plain JSON")
try:
    from src.utils.json_parser import extract_json_from_text
    result = extract_json_from_text('{"key": "value"}')
    assert result == {"key": "value"}
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Parse JSON from markdown")
try:
    from src.utils.json_parser import extract_json_from_text
    text = '```json\n{"key": "value"}\n```'
    result = extract_json_from_text(text)
    assert result == {"key": "value"}
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Parse JSON with surrounding text")
try:
    from src.utils.json_parser import extract_json_from_text
    text = 'Here is the data: {"key": "value"} end'
    result = extract_json_from_text(text)
    assert result == {"key": "value"}
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Handle invalid JSON gracefully")
try:
    from src.utils.json_parser import safe_json_parse
    result = safe_json_parse("not json", default={"fallback": True})
    assert result == {"fallback": True}
    success(desc)
except Exception as e:
    fail(desc, str(e))

# Test 4: Configuration
test_section("Configuration")

desc = test("Check .env file exists")
try:
    env_path = Path(".env")
    if not env_path.exists():
        warn(desc, ".env file not found (run setup)")
    else:
        success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Load environment variables")
try:
    from dotenv import load_dotenv
    load_dotenv()
    # Just check if dotenv works, don't require keys
    success(desc)
except Exception as e:
    fail(desc, str(e))

# Test 5: Dependencies
test_section("Python Packages")

packages = [
    ("anthropic", "Anthropic Claude API"),
    ("openai", "OpenAI API"),
    ("groq", "Groq API"),
    ("fastapi", "FastAPI web server"),
    ("uvicorn", "Uvicorn ASGI server"),
    ("aiolimiter", "Async rate limiting"),
    ("chromadb", "Vector database"),
    ("python-dotenv", "Environment variables"),
]

for package, description in packages:
    desc = test(f"Import {package}")
    try:
        __import__(package)
        success(desc)
    except ImportError:
        warn(desc, f"{description} not installed (optional for some features)")

# Test 6: File Structure
test_section("File Structure")

required_files = [
    "run_studio.py",
    "requirements.txt",
    ".env.example",
    "src/__init__.py",
    "src/orchestrator/orchestrator_v2.py",
    "src/resources/resource_manager.py",
    "src/api/api_client.py",
    "src/bots/foreman_bot.py",
    "src/bots/base_bot.py",
    "src/bots/research_bots.py",
    "src/utils/json_parser.py",
    "src/utils/first_run_setup.py",
]

for file_path in required_files:
    desc = test(f"File exists: {file_path}")
    try:
        path = Path(file_path)
        if not path.exists():
            fail(desc, "File not found")
        else:
            success(desc)
    except Exception as e:
        fail(desc, str(e))

# Test 7: Resource Manager Functionality
test_section("Resource Manager Functionality")

desc = test("CPU pool management")
try:
    from src.resources.resource_manager import ResourceManager
    rm = ResourceManager(cpu_cores=2, gpu_available=False)
    status = rm.get_status()
    assert "cpu" in status
    assert status["cpu"]["total_cores"] == 2
    success(desc)
except Exception as e:
    fail(desc, str(e))

desc = test("Cost tracking")
try:
    from src.resources.resource_manager import ResourceManager
    rm = ResourceManager(cpu_cores=2, gpu_available=False)
    rm._record_cost("openai", 0.10)
    assert rm.costs["openai"] == 0.10
    success(desc)
except Exception as e:
    fail(desc, str(e))

# Print Results
print("\n" + "="*70)
print(" "*20 + "📊 TEST RESULTS")
print("="*70 + "\n")

print(f"✅ Passed: {len(passed)}")
print(f"❌ Failed: {len(failed)}")
print(f"⚠️  Warnings: {len(warnings)}")

if failed:
    print("\n" + "="*70)
    print("❌ FAILED TESTS:")
    print("="*70)
    for desc, error in failed:
        print(f"\n  • {desc}")
        print(f"    Error: {error}")

if warnings:
    print("\n" + "="*70)
    print("⚠️  WARNINGS:")
    print("="*70)
    for desc, message in warnings:
        print(f"\n  • {desc}")
        print(f"    {message}")

print("\n" + "="*70)
if not failed:
    print(" "*15 + "✅ ALL CORE TESTS PASSED!")
    print("="*70 + "\n")
    print("System is ready to run!")
    print("\nNext steps:")
    print("  1. Add API keys: python -m src.utils.first_run_setup")
    print("  2. Start system: python run_studio.py")
    sys.exit(0)
else:
    print(" "*15 + "❌ SOME TESTS FAILED")
    print("="*70 + "\n")
    print("Please fix the failed tests before running the system.")
    sys.exit(1)
