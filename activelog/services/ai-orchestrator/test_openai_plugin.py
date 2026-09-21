#!/usr/bin/env python3
"""
Test script for OpenAI plugin functionality
"""
import asyncio
import os
import sys
import json
import base64
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from plugins.openai_plugin import OpenAIPlugin
import redis.asyncio as redis

async def test_openai_plugin():
    """Test OpenAI plugin functionality"""
    print("🧪 Testing OpenAI Plugin")
    print("=" * 50)
    
    # Initialize plugin
    plugin = OpenAIPlugin()
    
    # Test configuration
    print("📋 Configuration:")
    config = plugin.config
    print(f"  API Key configured: {'✅' if config['api_key'] else '❌'}")
    print(f"  Text model: {config['model_text']}")
    print(f"  Embedding model: {config['model_embedding']}")
    print(f"  Vision model: {config['model_vision']}")
    print(f"  DALL-E model: {config['model_dalle']}")
    print(f"  Caching enabled: {config['enable_caching']}")
    print()
    
    if not config['api_key']:
        print("❌ OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
        print("   Example: export OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Initialize Redis (optional)
    redis_client = None
    try:
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        await redis_client.ping()
        print("✅ Redis connected for caching")
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("   Caching will use in-memory fallback")
    
    # Initialize plugin
    try:
        await plugin.initialize(redis_client)
        print("✅ Plugin initialized successfully")
    except Exception as e:
        print(f"❌ Plugin initialization failed: {e}")
        return
    
    print("\n" + "=" * 50)
    
    # Test 1: Health Check
    print("🏥 Health Check:")
    try:
        health = await plugin.health_check()
        print(f"  Status: {health['status']}")
        print(f"  API Connected: {health.get('api_connected', False)}")
        print(f"  Redis Connected: {health.get('redis_connected', False)}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    print()
    
    # Test 2: Text Embeddings
    print("🔢 Text Embeddings:")
    try:
        test_text = "This is a test document about artificial intelligence and machine learning."
        embeddings_result = await plugin.generate_embeddings(test_text)
        
        print(f"  Text: {test_text}")
        print(f"  Model: {embeddings_result['model']}")
        print(f"  Dimensions: {embeddings_result['dimensions']}")
        print(f"  First 5 values: {embeddings_result['embeddings'][:5]}")
        print(f"  Usage: {embeddings_result['usage']}")
        print("  ✅ Embeddings generated successfully")
    except Exception as e:
        print(f"  ❌ Embeddings failed: {e}")
    
    print()
    
    # Test 3: Content Analysis
    print("📊 Content Analysis:")
    try:
        test_content = """
        Artificial Intelligence (AI) is transforming industries worldwide. From healthcare to finance,
        AI applications are revolutionizing how we work and live. Machine learning algorithms can
        now process vast amounts of data to identify patterns and make predictions with remarkable
        accuracy. However, this rapid advancement also raises important questions about ethics,
        privacy, and the future of human employment.
        """
        
        analysis_result = await plugin.analyze_content(test_content, "general")
        
        print(f"  Content length: {len(test_content)} characters")
        print(f"  Analysis type: general")
        print(f"  Model: {analysis_result['model']}")
        print(f"  Analysis: {analysis_result['analysis'][:200]}...")
        print(f"  Usage: {analysis_result['usage']}")
        print("  ✅ Content analysis completed successfully")
    except Exception as e:
        print(f"  ❌ Content analysis failed: {e}")
    
    print()
    
    # Test 4: Auto-tagging
    print("🏷️  Auto-tagging:")
    try:
        tags_result = await plugin.generate_tags(test_content, max_tags=5)
        
        print(f"  Content: AI and ML content")
        print(f"  Generated tags: {tags_result['tags']}")
        print(f"  Model: {tags_result['model']}")
        print(f"  Usage: {tags_result['usage']}")
        print("  ✅ Tags generated successfully")
    except Exception as e:
        print(f"  ❌ Tag generation failed: {e}")
    
    print()
    
    # Test 5: Image Analysis (with a simple test image)
    print("🖼️  Image Analysis:")
    try:
        # Create a simple test image (1x1 pixel)
        import io
        from PIL import Image as PILImage
        
        # Create a simple red pixel image
        img = PILImage.new('RGB', (1, 1), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes = img_bytes.getvalue()
        
        image_result = await plugin.analyze_image(img_bytes, "description")
        
        print(f"  Image: Simple test image")
        print(f"  Analysis type: description")
        print(f"  Model: {image_result['model']}")
        print(f"  Analysis: {image_result['analysis'][:150]}...")
        print(f"  Usage: {image_result['usage']}")
        print("  ✅ Image analysis completed successfully")
    except Exception as e:
        print(f"  ❌ Image analysis failed: {e}")
    
    print()
    
    # Test 6: Plugin Statistics
    print("📈 Plugin Statistics:")
    try:
        stats = await plugin.get_stats()
        
        print(f"  Plugin: {stats['plugin']} v{stats['version']}")
        print(f"  Capabilities: {', '.join(stats['capabilities'])}")
        print(f"  Status: {stats['status']}")
        print(f"  Statistics:")
        for key, value in stats['stats'].items():
            print(f"    {key}: {value}")
        print("  ✅ Statistics retrieved successfully")
    except Exception as e:
        print(f"  ❌ Statistics retrieval failed: {e}")
    
    print()
    
    # Test 7: Caching (if enabled)
    if config['enable_caching'] and redis_client:
        print("💾 Cache Testing:")
        try:
            # Test the same embeddings call again (should hit cache)
            print("  Testing cache hit...")
            start_time = asyncio.get_event_loop().time()
            embeddings_result2 = await plugin.generate_embeddings(test_text)
            end_time = asyncio.get_event_loop().time()
            
            print(f"  Response time: {(end_time - start_time) * 1000:.2f}ms")
            print(f"  Cache hits: {plugin.stats['cache_hits']}")
            print(f"  Cache misses: {plugin.stats['cache_misses']}")
            print("  ✅ Cache testing completed")
        except Exception as e:
            print(f"  ❌ Cache testing failed: {e}")
        print()
    
    # Close Redis connection
    if redis_client:
        await redis_client.aclose()
    
    print("🎉 OpenAI Plugin testing completed!")
    print(f"Final stats: {plugin.stats}")

if __name__ == "__main__":
    # Example environment setup
    print("OpenAI Plugin Test Script")
    print("=" * 50)
    print()
    
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  To test the OpenAI plugin, set your API key:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        print()
        print("📋 Optional configuration variables:")
        print("   export OPENAI_TEXT_MODEL='gpt-4'")
        print("   export OPENAI_EMBEDDING_MODEL='text-embedding-ada-002'")
        print("   export OPENAI_ENABLE_CACHING='true'")
        print("   export OPENAI_CACHE_TTL='3600'")
        print()
    
    # Run the test
    asyncio.run(test_openai_plugin())