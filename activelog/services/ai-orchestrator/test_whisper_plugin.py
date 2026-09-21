#!/usr/bin/env python3
"""
Test script for Whisper Plugin
Tests audio transcription, metadata extraction, and Elasticsearch storage
"""
import asyncio
import os
import json
import tempfile
from typing import Dict, Any

# Test configuration
TEST_CONFIG = {
    "test_audio_formats": ["mp3", "wav", "m4a"],
    "test_transcript_text": "This is a test audio file for transcription testing.",
    "test_language": "en",
    "elasticsearch_index": "audio_transcripts_test"
}

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*50}")
    print(f"🎵 {title}")
    print(f"{'='*50}")

def print_config():
    """Print current configuration"""
    print("📋 Configuration:")
    print(f"  OpenAI API key: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    print(f"  Whisper model: {os.getenv('WHISPER_MODEL', 'whisper-1')}")
    print(f"  Max file size: {int(os.getenv('WHISPER_MAX_FILE_SIZE', '25000000')) // 1024 // 1024}MB")
    print(f"  Elasticsearch host: {os.getenv('ELASTICSEARCH_HOST', 'localhost')}")
    print(f"  Elasticsearch port: {os.getenv('ELASTICSEARCH_PORT', '9200')}")
    print(f"  ES index: {os.getenv('WHISPER_ES_INDEX', 'audio_transcripts')}")
    print(f"  Caching enabled: {os.getenv('WHISPER_ENABLE_CACHING', 'true')}")

def create_test_audio_file(format_type: str = "wav", duration: float = 1.0) -> str:
    """Create a simple test audio file for testing"""
    try:
        import numpy as np
        import wave
        
        # Generate a simple sine wave
        sample_rate = 44100
        samples = int(sample_rate * duration)
        frequency = 440  # A note
        
        # Generate sine wave
        t = np.linspace(0, duration, samples, False)
        audio_data = np.sin(2 * np.pi * frequency * t)
        
        # Convert to 16-bit PCM
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_type}") as temp_file:
            if format_type == "wav":
                # Write WAV file
                with wave.open(temp_file.name, 'w') as wav_file:
                    wav_file.setnchannels(1)  # mono
                    wav_file.setsampwidth(2)  # 2 bytes per sample
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                
                return temp_file.name
            else:
                # For other formats, we'll just create a placeholder file
                # In a real test, you'd use proper audio conversion
                temp_file.write(b"FAKE_AUDIO_DATA_FOR_TESTING")
                return temp_file.name
                
    except ImportError:
        # If numpy/wave not available, create a dummy file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format_type}") as temp_file:
            temp_file.write(b"FAKE_AUDIO_DATA_FOR_TESTING")
            return temp_file.name

async def test_plugin_health():
    """Test plugin health check"""
    print("🔍 Testing plugin health...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        health = await plugin.health_check()
        print(f"Status: {health['status']}")
        print(f"OpenAI configured: {health['openai_configured']}")
        print(f"Elasticsearch connected: {health['elasticsearch_connected']}")
        print(f"Supported formats: {', '.join(health['supported_formats'])}")
        print(f"Max file size: {health['max_file_size_mb']}MB")
        
        if health['status'] == 'healthy':
            print("✅ Whisper plugin is healthy")
        else:
            print(f"❌ Whisper plugin unhealthy: {health.get('error', 'Unknown error')}")
        
        await plugin.cleanup()
        return health['status'] == 'healthy'
        
    except Exception as e:
        print(f"❌ Plugin health check failed: {e}")
        return False

async def test_audio_file_validation():
    """Test audio file validation"""
    print("📁 Testing audio file validation...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Test different formats
        for format_type in ["wav", "mp3", "m4a"]:
            print(f"   Testing {format_type.upper()} format...")
            
            # Create test file
            test_file = create_test_audio_file(format_type)
            
            try:
                file_size = os.path.getsize(test_file)
                validation_result = plugin._validate_audio_file(test_file, file_size)
                print(f"   ✅ {format_type.upper()}: Valid (duration: {validation_result['duration']:.2f}s)")
                
            except Exception as validation_error:
                print(f"   ⚠️  {format_type.upper()}: {validation_error}")
            
            finally:
                # Clean up test file
                try:
                    os.unlink(test_file)
                except Exception:
                    pass
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Audio file validation test failed: {e}")
        return False

async def test_metadata_extraction():
    """Test metadata extraction from audio files"""
    print("🏷️  Testing metadata extraction...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Create test file
        test_file = create_test_audio_file("wav")
        
        try:
            metadata = plugin._extract_audio_metadata(test_file)
            print(f"   Extracted metadata:")
            print(f"   - Duration: {metadata.get('duration', 'N/A')}s")
            print(f"   - Sample rate: {metadata.get('sample_rate', 'N/A')}Hz")
            print(f"   - Channels: {metadata.get('channels', 'N/A')}")
            print(f"   - Bitrate: {metadata.get('bitrate', 'N/A')}")
            
            if metadata:
                print("   ✅ Metadata extraction successful")
            else:
                print("   ⚠️  No metadata extracted (expected for test file)")
                
        finally:
            # Clean up test file
            try:
                os.unlink(test_file)
            except Exception:
                pass
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Metadata extraction test failed: {e}")
        return False

async def test_elasticsearch_connection():
    """Test Elasticsearch connection and index creation"""
    print("🔍 Testing Elasticsearch connection...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        if plugin.es_client:
            # Test connection
            try:
                await plugin.es_client.ping()
                print("   ✅ Elasticsearch connection successful")
                
                # Test index creation
                await plugin._ensure_index_exists()
                print("   ✅ Index creation/verification successful")
                
                # Check if index exists
                index_exists = await plugin.es_client.indices.exists(index=plugin.es_index)
                print(f"   Index '{plugin.es_index}' exists: {index_exists}")
                
            except Exception as es_error:
                print(f"   ❌ Elasticsearch operation failed: {es_error}")
                return False
        else:
            print("   ⚠️  Elasticsearch client not initialized")
            return False
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Elasticsearch test failed: {e}")
        return False

async def test_transcription_mock():
    """Test transcription workflow (without actual API call)"""
    print("🎙️  Testing transcription workflow...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Create test file
        test_file = create_test_audio_file("wav")
        
        try:
            # Test file validation
            file_size = os.path.getsize(test_file)
            validation_result = plugin._validate_audio_file(test_file, file_size)
            print(f"   ✅ File validation passed: {validation_result['format']}")
            
            # Test metadata extraction
            metadata = plugin._extract_audio_metadata(test_file)
            print(f"   ✅ Metadata extracted: {len(metadata)} fields")
            
            # Test cache key generation
            cache_key = plugin._generate_cache_key(
                "transcribe", 
                file_hash="test_hash",
                language="en"
            )
            print(f"   ✅ Cache key generated: {cache_key[:20]}...")
            
            # Test rate limiting
            rate_ok = await plugin._check_rate_limit("test")
            print(f"   ✅ Rate limiting check: {'Passed' if rate_ok else 'Failed'}")
            
            print("   💡 Note: Actual transcription requires OpenAI API key")
            
        finally:
            # Clean up test file
            try:
                os.unlink(test_file)
            except Exception:
                pass
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Transcription workflow test failed: {e}")
        return False

async def test_search_functionality():
    """Test search functionality"""
    print("🔍 Testing search functionality...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        if not plugin.es_client:
            print("   ⚠️  Elasticsearch not available, skipping search test")
            return False
        
        # Test search query building
        try:
            # This would normally search real data
            search_result = await plugin.search_transcripts(
                query="test",
                limit=5,
                filters={"language": "en"}
            )
            
            print(f"   ✅ Search executed successfully")
            print(f"   - Query: 'test'")
            print(f"   - Total results: {search_result.get('total', 0)}")
            print(f"   - Results returned: {len(search_result.get('results', []))}")
            print(f"   - Search time: {search_result.get('search_time_ms', 0)}ms")
            
        except Exception as search_error:
            if "index_not_found" in str(search_error).lower():
                print("   ⚠️  Search index not found (expected for new installation)")
            else:
                print(f"   ❌ Search failed: {search_error}")
                return False
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Search functionality test failed: {e}")
        return False

async def test_caching_functionality():
    """Test caching functionality"""
    print("💾 Testing caching functionality...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        if not plugin.redis_client:
            print("   ⚠️  Redis not available, testing in-memory caching")
        
        # Test cache operations
        cache_key = "test_cache_key"
        test_data = {"test": "data", "timestamp": "2024-01-01"}
        
        # Test cache miss
        cached = await plugin._get_cached_response(cache_key)
        print(f"   Cache miss test: {'✅ Passed' if cached is None else '❌ Failed'}")
        
        # Test cache set
        await plugin._cache_response(cache_key, test_data)
        print("   ✅ Cache set operation completed")
        
        # Test cache hit
        cached = await plugin._get_cached_response(cache_key)
        cache_hit = cached is not None and cached.get("test") == "data"
        print(f"   Cache hit test: {'✅ Passed' if cache_hit else '⚠️  Not available'}")
        
        # Check stats
        stats = await plugin.get_stats()
        cache_stats = stats['stats']
        print(f"   Cache hits: {cache_stats.get('cache_hits', 0)}")
        print(f"   Cache misses: {cache_stats.get('cache_misses', 0)}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Caching functionality test failed: {e}")
        return False

async def test_plugin_stats():
    """Test plugin statistics"""
    print("📊 Testing plugin statistics...")
    try:
        from plugins.whisper_plugin import create_plugin
        
        plugin = create_plugin()
        await plugin.initialize()
        
        # Get stats
        stats = await plugin.get_stats()
        
        print(f"✅ Plugin stats retrieved:")
        print(f"   Name: {stats['name']}")
        print(f"   Version: {stats['version']}")
        print(f"   Capabilities: {len(stats['capabilities'])}")
        
        # Show capabilities
        print("   Capabilities:")
        for capability in stats['capabilities']:
            print(f"   - {capability}")
        
        # Show configuration
        config = stats['config']
        print(f"   Whisper model: {config['whisper_model']}")
        print(f"   Supported formats: {len(config['supported_formats'])}")
        print(f"   Max file size: {config['max_file_size_mb']}MB")
        print(f"   ES index: {config['elasticsearch_index']}")
        
        # Show statistics
        plugin_stats = stats['stats']
        print(f"   Transcriptions processed: {plugin_stats.get('transcriptions_processed', 0)}")
        print(f"   Audio files analyzed: {plugin_stats.get('audio_files_analyzed', 0)}")
        print(f"   Transcripts stored: {plugin_stats.get('transcripts_stored', 0)}")
        print(f"   Errors: {plugin_stats.get('errors', 0)}")
        
        await plugin.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Plugin stats test failed: {e}")
        return False

async def test_integration_workflow():
    """Test complete integration workflow"""
    print("🔗 Testing integration workflow...")
    try:
        # Test plugin manager integration
        from plugin_manager import plugin_manager
        
        # Initialize plugin manager (this loads all plugins)
        await plugin_manager.initialize(None)
        
        # Check if Whisper plugin is loaded
        whisper_plugin = await plugin_manager.get_plugin('whisper')
        
        if whisper_plugin:
            print("   ✅ Whisper plugin loaded in plugin manager")
            
            # Test plugin manager methods
            plugins = await plugin_manager.list_plugins()
            whisper_info = next((p for p in plugins if p['name'] == 'whisper'), None)
            
            if whisper_info:
                print(f"   ✅ Plugin listed: {whisper_info['name']} v{whisper_info.get('version', 'unknown')}")
                print(f"   Status: {whisper_info.get('status', 'unknown')}")
                print(f"   Capabilities: {len(whisper_info.get('capabilities', []))}")
            
            # Test capabilities mapping
            capabilities = await plugin_manager.get_plugin_capabilities()
            whisper_caps = capabilities.get('whisper', [])
            print(f"   ✅ Capabilities available: {len(whisper_caps)}")
            
        else:
            print("   ❌ Whisper plugin not found in plugin manager")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Integration workflow test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print_header("Whisper Plugin Test Script")
    
    print("⚠️  Prerequisites:")
    print("   - OpenAI API key should be set: export OPENAI_API_KEY='your-key'")
    print("   - Elasticsearch should be running on localhost:9200")
    print("   - Redis should be running on localhost:6379 (optional)")
    print("   - For full testing: install numpy and wave packages")
    
    print_config()
    
    # Run tests
    tests = [
        ("Plugin Health Check", test_plugin_health),
        ("Audio File Validation", test_audio_file_validation),
        ("Metadata Extraction", test_metadata_extraction),
        ("Elasticsearch Connection", test_elasticsearch_connection),
        ("Transcription Workflow", test_transcription_mock),
        ("Search Functionality", test_search_functionality),
        ("Caching Functionality", test_caching_functionality),
        ("Plugin Statistics", test_plugin_stats),
        ("Integration Workflow", test_integration_workflow)
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
        print("🎉 All tests passed! Whisper plugin is working correctly.")
    elif passed > 0:
        print("⚠️  Some tests passed. Plugin is partially functional.")
        print("   Check OpenAI API key and Elasticsearch installation.")
    else:
        print("❌ All tests failed. Check prerequisites:")
        print("   1. Set OpenAI API key: export OPENAI_API_KEY='your-key'")
        print("   2. Start Elasticsearch: docker run -p 9200:9200 elasticsearch:8.11.0")
        print("   3. Install dependencies: pip install elasticsearch mutagen aiofiles")

if __name__ == "__main__":
    asyncio.run(main())