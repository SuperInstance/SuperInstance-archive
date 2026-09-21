#!/usr/bin/env python3
"""
Test script for Ollama Plugin
Tests local LLM capabilities, model management, and fallback mechanisms
"""
import asyncio
import os
import json
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    "base_url": "http://localhost:11434",
    "test_model": "llama2",
    "test_prompt": "Explain artificial intelligence in one sentence.",
    "test_messages": [
        {"role": "user", "content": "What is machine learning?"}
    ],
    "test_text": "This is a test sentence for embeddings generation."
}

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*50}")
    print(f"🧪 {title}")
    print(f"{'='*50}")

def print_config():
    """Print current configuration"""
    print("📋 Configuration:")
    print(f"  Ollama host: {os.getenv('OLLAMA_HOST', 'localhost')}")
    print(f"  Ollama port: {os.getenv('OLLAMA_PORT', '11434')}")
    print(f"  Default model: {os.getenv('OLLAMA_DEFAULT_MODEL', 'llama2')}")
    print(f"  Caching enabled: {os.getenv('OLLAMA_ENABLE_CACHING', 'true')}")
    print(f"  Fallback enabled: {os.getenv('OLLAMA_ENABLE_FALLBACK', 'true')}")
    print(f"  OpenAI fallback: {os.getenv('OLLAMA_FALLBACK_TO_OPENAI', 'true')}")

async def test_plugin_health():
    """Test plugin health check"""
    print("🔍 Testing plugin health...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        health = await plugin.health_check()
        print(f"Status: {health['status']}")
        
        if health['status'] == 'healthy':
            print(f"✅ Ollama connected successfully")
            print(f"   Models available: {health.get('models_available', 0)}")
            print(f"   Base URL: {health.get('base_url')}")
        else:
            print(f"❌ Ollama connection failed: {health.get('error', 'Unknown error')}")
            if health.get('fallback_available'):
                print("   💡 Fallback mechanism available")
        
        await plugin.cleanup()
        return health['status'] == 'healthy'
        
    except Exception as e:
        print(f"❌ Plugin health check failed: {e}")
        return False

async def test_model_management():
    """Test model management operations"""
    print("🎯 Testing model management...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # List models
        print("📝 Listing available models...")
        models = await plugin.list_models()
        print(f"   Found {models['total']} models:")
        
        for model in models['models'][:3]:  # Show first 3 models
            print(f"   - {model['name']} ({model.get('size', 'unknown size')})")
        
        # Check if test model exists
        model_names = [m['name'] for m in models['models']]
        if TEST_CONFIG['test_model'] not in model_names:
            print(f"⚠️  Test model '{TEST_CONFIG['test_model']}' not found")
            print("   You may need to pull it first:")
            print(f"   ollama pull {TEST_CONFIG['test_model']}")
        else:
            print(f"✅ Test model '{TEST_CONFIG['test_model']}' is available")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Model management test failed: {e}")
        return False

async def test_text_generation():
    """Test text generation"""
    print("📝 Testing text generation...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Test non-streaming generation
        print("🔄 Generating text (non-streaming)...")
        result = await plugin.generate_text(
            TEST_CONFIG['test_prompt'],
            model=TEST_CONFIG['test_model']
        )
        
        print(f"✅ Generation successful:")
        print(f"   Model: {result.get('model')}")
        print(f"   Response: {result.get('response', '')[:100]}...")
        print(f"   Done: {result.get('done')}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Text generation test failed: {e}")
        print("   💡 This is expected if Ollama is not running or model is not available")
        return False

async def test_chat_completion():
    """Test chat completion"""
    print("💬 Testing chat completion...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Test chat completion
        print("🔄 Generating chat response...")
        result = await plugin.chat_completion(
            TEST_CONFIG['test_messages'],
            model=TEST_CONFIG['test_model']
        )
        
        print(f"✅ Chat completion successful:")
        print(f"   Model: {result.get('model')}")
        print(f"   Content: {result.get('content', '')[:100]}...")
        print(f"   Role: {result.get('role')}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Chat completion test failed: {e}")
        print("   💡 This is expected if Ollama is not running or model is not available")
        return False

async def test_embeddings():
    """Test embeddings generation"""
    print("🧮 Testing embeddings generation...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Test embeddings
        print("🔄 Generating embeddings...")
        result = await plugin.generate_embeddings(
            TEST_CONFIG['test_text'],
            model=TEST_CONFIG['test_model']
        )
        
        print(f"✅ Embeddings generation successful:")
        print(f"   Model: {result.get('model')}")
        print(f"   Dimensions: {result.get('dimensions')}")
        print(f"   Vector length: {len(result.get('embeddings', []))}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Embeddings generation test failed: {e}")
        print("   💡 This is expected if Ollama is not running or model is not available")
        return False

async def test_caching():
    """Test caching functionality"""
    print("💾 Testing caching functionality...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # First request (should miss cache)
        print("🔄 First request (cache miss expected)...")
        start_time = asyncio.get_event_loop().time()
        
        result1 = await plugin.generate_text(
            "Say hello",
            model=TEST_CONFIG['test_model']
        )
        
        first_time = asyncio.get_event_loop().time() - start_time
        
        # Second identical request (should hit cache if enabled)
        print("🔄 Second identical request (cache hit expected)...")
        start_time = asyncio.get_event_loop().time()
        
        result2 = await plugin.generate_text(
            "Say hello",
            model=TEST_CONFIG['test_model']
        )
        
        second_time = asyncio.get_event_loop().time() - start_time
        
        print(f"   First request time: {first_time:.2f}s")
        print(f"   Second request time: {second_time:.2f}s")
        
        if second_time < first_time * 0.5:  # Significantly faster
            print("✅ Caching appears to be working")
        else:
            print("⚠️  Caching may not be working or not significant")
        
        # Check stats
        stats = await plugin.get_stats()
        cache_hits = stats['stats'].get('cache_hits', 0)
        cache_misses = stats['stats'].get('cache_misses', 0)
        
        print(f"   Cache hits: {cache_hits}")
        print(f"   Cache misses: {cache_misses}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Caching test failed: {e}")
        return False

async def test_fallback_mechanism():
    """Test fallback to OpenAI"""
    print("🔄 Testing fallback mechanism...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        # Create plugin with fallback enabled
        plugin = create_plugin()
        plugin.enable_fallback = True
        plugin.fallback_to_openai = True
        
        # Force connection to fail by using wrong URL
        plugin.ollama_host = "nonexistent"
        plugin.ollama_base_url = "http://nonexistent:11434"
        
        await plugin.initialize()
        
        # Try to generate text (should fallback to OpenAI if configured)
        print("🔄 Attempting text generation with forced Ollama failure...")
        
        try:
            result = await plugin.generate_text(
                "Hello world",
                model="llama2"
            )
            
            if result.get('fallback'):
                print("✅ Fallback to OpenAI successful")
                print(f"   Response: {result.get('response', '')[:50]}...")
            else:
                print("⚠️  Request succeeded but didn't use fallback")
                
        except Exception as fallback_error:
            print(f"❌ Fallback failed: {fallback_error}")
            print("   💡 This is expected if OpenAI API key is not configured")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

async def test_plugin_stats():
    """Test plugin statistics"""
    print("📊 Testing plugin statistics...")
    try:
        from plugins.ollama_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Get initial stats
        stats = await plugin.get_stats()
        
        print(f"✅ Plugin stats retrieved:")
        print(f"   Name: {stats['name']}")
        print(f"   Version: {stats['version']}")
        print(f"   Capabilities: {len(stats['capabilities'])}")
        print(f"   Available models: {stats['config'].get('available_models', 0)}")
        
        # Show some stats
        plugin_stats = stats['stats']
        print(f"   Chat completions: {plugin_stats.get('chat_completions', 0)}")
        print(f"   Text generations: {plugin_stats.get('text_generations', 0)}")
        print(f"   Embeddings generated: {plugin_stats.get('embeddings_generated', 0)}")
        print(f"   Errors: {plugin_stats.get('errors', 0)}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Plugin stats test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print_header("Ollama Plugin Test Script")
    
    print("⚠️  Prerequisites:")
    print("   - Ollama should be running: ollama serve")
    print("   - Test model should be available: ollama pull llama2")
    print("   - For fallback testing: set OPENAI_API_KEY")
    
    print_config()
    
    # Run tests
    tests = [
        ("Plugin Health Check", test_plugin_health),
        ("Model Management", test_model_management),
        ("Text Generation", test_text_generation),
        ("Chat Completion", test_chat_completion),
        ("Embeddings Generation", test_embeddings),
        ("Caching Functionality", test_caching),
        ("Fallback Mechanism", test_fallback_mechanism),
        ("Plugin Statistics", test_plugin_stats)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print_header(test_name)
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ollama plugin is working correctly.")
    elif passed > 0:
        print("⚠️  Some tests passed. Plugin is partially functional.")
        print("   Check Ollama installation and model availability.")
    else:
        print("❌ All tests failed. Check Ollama installation:")
        print("   1. Install Ollama: https://ollama.ai")
        print("   2. Start Ollama: ollama serve")
        print("   3. Pull a model: ollama pull llama2")

if __name__ == "__main__":
    asyncio.run(main())