#!/usr/bin/env python3
"""
Test configuration loading
Verifies YAML configs and bootcamp file can be read
"""

import sys
import os
from pathlib import Path

print("=" * 60)
print("CONFIGURATION TEST")
print("=" * 60)
print()

# Test 1: Check .env file
print("1. Checking .env file...")
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        content = f.read()
        if "your_anthropic_api_key_here" in content:
            print("   ⚠️  .env exists but API key not set")
            print("   Edit .env and add your Claude API key")
        else:
            print("   ✓ .env configured")
else:
    print("   ✗ .env file not found")
    print("   Run: cp .env.example .env")

print()

# Test 2: Check bot configs YAML
print("2. Checking bot configuration...")
try:
    import yaml
    with open("config/content_bot_configs.yaml") as f:
        config = yaml.safe_load(f)
        bot_count = len(config.get('bots', []))
        print(f"   ✓ Found {bot_count} bot configurations")

        # Show bot types
        bot_types = set(b['type'] for b in config.get('bots', []))
        print(f"   Bot types: {', '.join(sorted(bot_types))}")
except FileNotFoundError:
    print("   ✗ config/content_bot_configs.yaml not found")
except Exception as e:
    print(f"   ✗ Error loading config: {e}")

print()

# Test 3: Check bootcamp file
print("3. Checking bootcamp file...")
bootcamp_file = Path("config/content_bootcamp.md")
if bootcamp_file.exists():
    size = bootcamp_file.stat().st_size
    with open(bootcamp_file) as f:
        lines = len(f.readlines())
    print(f"   ✓ Bootcamp file found ({size:,} bytes, {lines} lines)")
else:
    print("   ✗ config/content_bootcamp.md not found")

print()

# Test 4: Check directory structure
print("4. Checking directory structure...")
required_dirs = [
    "src/orchestrator",
    "src/bots",
    "src/communication",
    "src/knowledge",
    "src/lora",
    "config",
    "data",
]

all_exist = True
for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✓ {dir_path}")
    else:
        print(f"   ✗ {dir_path} missing")
        all_exist = False

print()

# Test 5: Check Python files
print("5. Checking Python files...")
python_files = [
    "src/orchestrator/main.py",
    "src/bots/base_bot.py",
    "src/bots/content_bots.py",
    "src/orchestrator/task_manager.py",
    "src/communication/message_bus.py",
    "src/communication/help_queue.py",
    "src/knowledge/knowledge_base.py",
    "src/lora/lora_manager.py",
]

all_files_exist = True
for file_path in python_files:
    if Path(file_path).exists():
        size = Path(file_path).stat().st_size
        print(f"   ✓ {file_path} ({size:,} bytes)")
    else:
        print(f"   ✗ {file_path} missing")
        all_files_exist = False

print()
print("=" * 60)

# Summary
if all_exist and all_files_exist:
    print("✓ Configuration complete!")
    print()
    print("Next steps:")
    print("  1. Edit .env with your Claude API key")
    print("  2. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
    print("  3. Download models: ./download_models.sh")
    print("  4. Start system: ./start.sh")
else:
    print("✗ Some files missing. Re-run setup.")
    sys.exit(1)
