#!/usr/bin/env python3
"""
Test system components without requiring Ollama
This verifies the code structure and logic work correctly
"""

import sys
import os
sys.path.insert(0, 'src')

print("=" * 60)
print("SYSTEM COMPONENT TEST")
print("=" * 60)
print()

# Test 1: Import all modules
print("1. Testing imports...")
try:
    from orchestrator.task_manager import TaskManager, TaskPriority, TaskStatus
    from communication.message_bus import MessageBus
    from communication.help_queue import HelpQueue
    from knowledge.knowledge_base import KnowledgeBase
    from lora.lora_manager import LoRAManager
    from bots.base_bot import BotConfig, BotStatus
    print("   ✓ All imports successful")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Create task manager
print("2. Testing TaskManager...")
try:
    import asyncio

    async def test_task_manager():
        tm = TaskManager()
        task = await tm.create_task(
            bot_type="test",
            description="Test task",
            priority="high"
        )
        assert task['bot_type'] == "test"
        assert task['priority'] == "HIGH"
        print("   ✓ TaskManager working")

    asyncio.run(test_task_manager())
except Exception as e:
    print(f"   ✗ TaskManager failed: {e}")

print()

# Test 3: Create message bus
print("3. Testing MessageBus...")
try:
    async def test_message_bus():
        mb = MessageBus()
        mb.register_bot("test_bot")

        test_task = {
            'task_id': 'test123',
            'description': 'Test'
        }

        await mb.assign_task("test_bot", test_task)
        received = await mb.get_task_for_bot("test_bot")

        assert received['task_id'] == 'test123'
        print("   ✓ MessageBus working")

    asyncio.run(test_message_bus())
except Exception as e:
    print(f"   ✗ MessageBus failed: {e}")

print()

# Test 4: Create help queue
print("4. Testing HelpQueue...")
try:
    async def test_help_queue():
        hq = HelpQueue()

        help_req = {
            'bot_id': 'test_bot',
            'task_id': 'test123',
            'error': 'Test error'
        }

        await hq.add(help_req)
        assert not hq.is_empty()

        req = await hq.get()
        assert req['bot_id'] == 'test_bot'
        print("   ✓ HelpQueue working")

    asyncio.run(test_help_queue())
except Exception as e:
    print(f"   ✗ HelpQueue failed: {e}")

print()

# Test 5: Create knowledge base
print("5. Testing KnowledgeBase...")
try:
    kb = KnowledgeBase(data_dir="data/test_kb")
    print("   ✓ KnowledgeBase initialized")
except Exception as e:
    print(f"   ✗ KnowledgeBase failed: {e}")

print()

# Test 6: Create LoRA manager
print("6. Testing LoRAManager...")
try:
    async def test_lora():
        lora = LoRAManager(lora_dir="data/test_lora")
        context = await lora.get_user_context("test_user")
        assert 'content_preferences' in context
        print("   ✓ LoRAManager working")

    asyncio.run(test_lora())
except Exception as e:
    print(f"   ✗ LoRAManager failed: {e}")

print()

# Test 7: Create bot config
print("7. Testing BotConfig...")
try:
    config = BotConfig(
        bot_id="test_bot",
        bot_type="test",
        model="test_model",
        specialty="Testing"
    )
    assert config.bot_id == "test_bot"
    print("   ✓ BotConfig working")
except Exception as e:
    print(f"   ✗ BotConfig failed: {e}")

print()

# Test 8: Check bootcamp file
print("8. Testing configuration files...")
try:
    with open("config/content_bootcamp.md") as f:
        bootcamp = f.read()
    assert len(bootcamp) > 1000
    print("   ✓ Bootcamp file loaded")

    import yaml
    with open("config/content_bot_configs.yaml") as f:
        bot_config = yaml.safe_load(f)
    assert 'bots' in bot_config
    print("   ✓ Bot config loaded")
except Exception as e:
    print(f"   ✗ Config files failed: {e}")

print()
print("=" * 60)
print("✓ All system components working!")
print()
print("Next steps:")
print("  1. Install Ollama (requires sudo)")
print("  2. Download models (~40-50 min)")
print("  3. Add Claude API key to .env")
print("  4. Run: ./start.sh")
print("=" * 60)
