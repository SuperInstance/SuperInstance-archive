"""
Unit tests for AI Orchestrator Service
Tests AI model management, query processing, and plugin system
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import numpy as np

# Import AI orchestrator components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

from ai_orchestrator.main import AIOrchestrator
from ai_orchestrator.plugin_manager import PluginManager
from ai_orchestrator.plugins.openai_plugin import OpenAIPlugin
from ai_orchestrator.plugins.ollama_plugin import OllamaPlugin
from ai_orchestrator.plugins.whisper_plugin import WhisperPlugin


class TestOpenAIPlugin:
    """Test OpenAI plugin functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.plugin = OpenAIPlugin(api_key="test_key")
    
    @patch('openai.ChatCompletion.create')
    async def test_chat_completion(self, mock_openai):
        """Test chat completion functionality"""
        mock_response = {
            'id': 'chatcmpl-test',
            'choices': [{
                'message': {
                    'role': 'assistant',
                    'content': 'This is a test response from OpenAI.'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 15,
                'total_tokens': 25
            }
        }
        mock_openai.return_value = mock_response
        
        messages = [
            {'role': 'user', 'content': 'What is the capital of France?'}
        ]
        
        result = await self.plugin.chat_completion(messages)
        
        assert result['success'] is True
        assert result['response'] == 'This is a test response from OpenAI.'
        assert result['usage']['total_tokens'] == 25
        mock_openai.assert_called_once()
    
    @patch('openai.ChatCompletion.create')
    async def test_chat_completion_with_error(self, mock_openai):
        """Test chat completion error handling"""
        mock_openai.side_effect = Exception("API Error")
        
        messages = [
            {'role': 'user', 'content': 'Test question'}
        ]
        
        result = await self.plugin.chat_completion(messages)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'API Error' in result['error']
    
    @patch('openai.Embedding.create')
    async def test_create_embeddings(self, mock_embedding):
        """Test embedding creation"""
        mock_response = {
            'data': [
                {
                    'embedding': [0.1] * 1536,
                    'index': 0
                }
            ],
            'usage': {
                'prompt_tokens': 5,
                'total_tokens': 5
            }
        }
        mock_embedding.return_value = mock_response
        
        texts = ["Sample text for embedding"]
        
        result = await self.plugin.create_embeddings(texts)
        
        assert result['success'] is True
        assert len(result['embeddings']) == 1
        assert len(result['embeddings'][0]) == 1536
        mock_embedding.assert_called_once()
    
    async def test_calculate_cost(self):
        """Test cost calculation"""
        usage = {
            'prompt_tokens': 1000,
            'completion_tokens': 500,
            'total_tokens': 1500
        }
        
        cost = self.plugin.calculate_cost(usage, model='gpt-4')
        
        assert cost > 0
        assert isinstance(cost, float)
    
    async def test_validate_configuration(self):
        """Test plugin configuration validation"""
        # Valid configuration
        valid_config = {
            'api_key': 'sk-test123',
            'model': 'gpt-4',
            'max_tokens': 2000
        }
        
        assert self.plugin.validate_config(valid_config) is True
        
        # Invalid configuration
        invalid_config = {
            'model': 'gpt-4'
            # Missing api_key
        }
        
        assert self.plugin.validate_config(invalid_config) is False


class TestOllamaPlugin:
    """Test Ollama plugin functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.plugin = OllamaPlugin(base_url="http://localhost:11434")
    
    @patch('requests.post')
    async def test_chat_completion_ollama(self, mock_post):
        """Test Ollama chat completion"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': 'This is a response from Ollama',
            'done': True,
            'context': [1, 2, 3, 4, 5]
        }
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        messages = [
            {'role': 'user', 'content': 'Hello, Ollama!'}
        ]
        
        result = await self.plugin.chat_completion(messages, model='llama2')
        
        assert result['success'] is True
        assert result['response'] == 'This is a response from Ollama'
        mock_post.assert_called_once()
    
    @patch('requests.get')
    async def test_list_models(self, mock_get):
        """Test listing available models"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama2:latest', 'size': 3800000000},
                {'name': 'codellama:latest', 'size': 3800000000}
            ]
        }
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        models = await self.plugin.list_models()
        
        assert len(models) == 2
        assert 'llama2:latest' in [model['name'] for model in models]
        mock_get.assert_called_once()
    
    @patch('requests.post')
    async def test_pull_model(self, mock_post):
        """Test model pulling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b'{"status":"downloading","completed":100,"total":3800000000}',
            b'{"status":"verifying sha256"}',
            b'{"status":"success"}'
        ]
        mock_post.return_value = mock_response
        
        result = await self.plugin.pull_model('llama2:latest')
        
        assert result['success'] is True
        mock_post.assert_called_once()
    
    async def test_health_check(self):
        """Test Ollama health check"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            is_healthy = await self.plugin.health_check()
            
            assert is_healthy is True


class TestWhisperPlugin:
    """Test Whisper plugin functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.plugin = WhisperPlugin()
    
    @patch('openai.Audio.transcribe')
    async def test_transcribe_audio(self, mock_transcribe):
        """Test audio transcription"""
        mock_response = {
            'text': 'This is the transcribed text from audio.',
            'language': 'en'
        }
        mock_transcribe.return_value = mock_response
        
        # Mock audio file
        audio_data = b'fake_audio_data'
        
        result = await self.plugin.transcribe_audio(audio_data, 'test.wav')
        
        assert result['success'] is True
        assert result['text'] == 'This is the transcribed text from audio.'
        assert result['language'] == 'en'
        mock_transcribe.assert_called_once()
    
    @patch('openai.Audio.translate')
    async def test_translate_audio(self, mock_translate):
        """Test audio translation"""
        mock_response = {
            'text': 'This is the translated text to English.',
            'language': 'en'
        }
        mock_translate.return_value = mock_response
        
        audio_data = b'fake_audio_data_in_spanish'
        
        result = await self.plugin.translate_audio(audio_data, 'spanish_audio.wav')
        
        assert result['success'] is True
        assert result['text'] == 'This is the translated text to English.'
        mock_translate.assert_called_once()
    
    def test_validate_audio_format(self):
        """Test audio format validation"""
        valid_formats = ['wav', 'mp3', 'm4a', 'flac']
        invalid_formats = ['txt', 'pdf', 'jpg']
        
        for fmt in valid_formats:
            assert self.plugin.validate_audio_format(f'test.{fmt}') is True
        
        for fmt in invalid_formats:
            assert self.plugin.validate_audio_format(f'test.{fmt}') is False
    
    async def test_audio_preprocessing(self):
        """Test audio preprocessing"""
        # Mock audio processing
        with patch('whisper_plugin.preprocess_audio') as mock_preprocess:
            mock_preprocess.return_value = b'preprocessed_audio_data'
            
            raw_audio = b'raw_audio_data'
            processed = await self.plugin.preprocess_audio(raw_audio)
            
            assert processed == b'preprocessed_audio_data'
            mock_preprocess.assert_called_once_with(raw_audio)


class TestPluginManager:
    """Test plugin management system"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.plugin_manager = PluginManager()
    
    def test_register_plugin(self):
        """Test plugin registration"""
        plugin = OpenAIPlugin(api_key="test_key")
        
        result = self.plugin_manager.register_plugin('openai', plugin)
        
        assert result is True
        assert 'openai' in self.plugin_manager.plugins
    
    def test_get_plugin(self):
        """Test getting registered plugin"""
        plugin = OpenAIPlugin(api_key="test_key")
        self.plugin_manager.register_plugin('openai', plugin)
        
        retrieved_plugin = self.plugin_manager.get_plugin('openai')
        
        assert retrieved_plugin is plugin
    
    def test_get_nonexistent_plugin(self):
        """Test getting non-existent plugin"""
        plugin = self.plugin_manager.get_plugin('nonexistent')
        
        assert plugin is None
    
    def test_list_plugins(self):
        """Test listing all plugins"""
        openai_plugin = OpenAIPlugin(api_key="test_key")
        ollama_plugin = OllamaPlugin(base_url="http://localhost:11434")
        
        self.plugin_manager.register_plugin('openai', openai_plugin)
        self.plugin_manager.register_plugin('ollama', ollama_plugin)
        
        plugins = self.plugin_manager.list_plugins()
        
        assert len(plugins) == 2
        assert 'openai' in plugins
        assert 'ollama' in plugins
    
    async def test_plugin_health_check(self):
        """Test plugin health checking"""
        plugin = Mock()
        plugin.health_check = AsyncMock(return_value=True)
        
        self.plugin_manager.register_plugin('test_plugin', plugin)
        
        health_status = await self.plugin_manager.check_plugin_health('test_plugin')
        
        assert health_status is True
        plugin.health_check.assert_called_once()
    
    def test_unregister_plugin(self):
        """Test plugin unregistration"""
        plugin = OpenAIPlugin(api_key="test_key")
        self.plugin_manager.register_plugin('openai', plugin)
        
        result = self.plugin_manager.unregister_plugin('openai')
        
        assert result is True
        assert 'openai' not in self.plugin_manager.plugins
    
    async def test_plugin_load_balancing(self):
        """Test load balancing between plugins"""
        # Register multiple OpenAI plugins
        plugin1 = Mock()
        plugin1.chat_completion = AsyncMock(return_value={'success': True, 'response': 'Response 1'})
        
        plugin2 = Mock()
        plugin2.chat_completion = AsyncMock(return_value={'success': True, 'response': 'Response 2'})
        
        self.plugin_manager.register_plugin('openai_1', plugin1)
        self.plugin_manager.register_plugin('openai_2', plugin2)
        
        # Test round-robin distribution
        plugin = self.plugin_manager.get_plugin_with_load_balancing(['openai_1', 'openai_2'])
        assert plugin in [plugin1, plugin2]


class TestAIOrchestrator:
    """Test main AI orchestrator functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.orchestrator = AIOrchestrator()
    
    @patch('ai_orchestrator.main.PluginManager')
    async def test_process_query(self, mock_plugin_manager):
        """Test query processing"""
        # Mock plugin manager and OpenAI plugin
        mock_plugin = Mock()
        mock_plugin.chat_completion = AsyncMock(return_value={
            'success': True,
            'response': 'The capital of France is Paris.',
            'usage': {'total_tokens': 20}
        })
        
        mock_plugin_manager.return_value.get_plugin.return_value = mock_plugin
        
        query = {
            'text': 'What is the capital of France?',
            'user_id': str(uuid.uuid4()),
            'context': [],
            'plugin': 'openai'
        }
        
        result = await self.orchestrator.process_query(query)
        
        assert result['success'] is True
        assert 'Paris' in result['response']
        assert 'usage' in result
    
    @patch('ai_orchestrator.main.PluginManager')
    async def test_process_query_with_context(self, mock_plugin_manager):
        """Test query processing with conversation context"""
        mock_plugin = Mock()
        mock_plugin.chat_completion = AsyncMock(return_value={
            'success': True,
            'response': 'Based on our previous conversation, the answer is 42.',
            'usage': {'total_tokens': 25}
        })
        
        mock_plugin_manager.return_value.get_plugin.return_value = mock_plugin
        
        query = {
            'text': 'What was the answer again?',
            'user_id': str(uuid.uuid4()),
            'context': [
                {'role': 'user', 'content': 'What is the meaning of life?'},
                {'role': 'assistant', 'content': 'The answer is 42.'}
            ],
            'plugin': 'openai'
        }
        
        result = await self.orchestrator.process_query(query)
        
        assert result['success'] is True
        assert '42' in result['response']
        
        # Check that context was included in the call
        call_args = mock_plugin.chat_completion.call_args[0][0]
        assert len(call_args) == 3  # Previous context + new query
    
    async def test_query_routing(self):
        """Test query routing to appropriate plugin"""
        # Test different query types
        queries = [
            ('Transcribe this audio file', 'whisper'),
            ('Generate embeddings for this text', 'openai'),
            ('Run this on local model', 'ollama')
        ]
        
        for query_text, expected_plugin in queries:
            plugin = self.orchestrator.route_query({'text': query_text})
            assert plugin == expected_plugin
    
    async def test_response_caching(self):
        """Test response caching functionality"""
        with patch.object(self.orchestrator, 'cache') as mock_cache:
            mock_cache.get.return_value = None  # Cache miss
            mock_cache.set.return_value = True
            
            query = {
                'text': 'What is 2 + 2?',
                'user_id': str(uuid.uuid4()),
                'plugin': 'openai'
            }
            
            # First call - should miss cache
            with patch.object(self.orchestrator.plugin_manager, 'get_plugin') as mock_get_plugin:
                mock_plugin = Mock()
                mock_plugin.chat_completion = AsyncMock(return_value={
                    'success': True,
                    'response': '2 + 2 = 4',
                    'usage': {'total_tokens': 10}
                })
                mock_get_plugin.return_value = mock_plugin
                
                result1 = await self.orchestrator.process_query(query)
            
            # Second call - should hit cache
            mock_cache.get.return_value = {
                'response': '2 + 2 = 4',
                'cached': True
            }
            
            result2 = await self.orchestrator.process_query(query)
            
            assert result1['response'] == result2['response']
            assert result2.get('cached') is True
    
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        user_id = str(uuid.uuid4())
        
        # Mock rate limiter
        with patch.object(self.orchestrator, 'rate_limiter') as mock_limiter:
            mock_limiter.is_allowed.return_value = True
            
            query = {
                'text': 'Test query',
                'user_id': user_id,
                'plugin': 'openai'
            }
            
            # First few queries should be allowed
            for i in range(5):
                result = await self.orchestrator.check_rate_limit(query)
                assert result is True
            
            # Simulate rate limit exceeded
            mock_limiter.is_allowed.return_value = False
            
            result = await self.orchestrator.check_rate_limit(query)
            assert result is False
    
    async def test_cost_tracking(self):
        """Test cost tracking functionality"""
        user_id = str(uuid.uuid4())
        
        usage_data = {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
        
        with patch.object(self.orchestrator, 'cost_tracker') as mock_tracker:
            mock_tracker.track_usage.return_value = True
            mock_tracker.get_user_costs.return_value = {'total': 0.025}
            
            await self.orchestrator.track_usage(user_id, usage_data, 'gpt-4')
            
            costs = await self.orchestrator.get_user_costs(user_id)
            
            assert costs['total'] == 0.025
            mock_tracker.track_usage.assert_called_once()
    
    async def test_error_handling(self):
        """Test error handling in orchestrator"""
        with patch.object(self.orchestrator.plugin_manager, 'get_plugin') as mock_get_plugin:
            # Test plugin not found
            mock_get_plugin.return_value = None
            
            query = {
                'text': 'Test query',
                'plugin': 'nonexistent_plugin'
            }
            
            result = await self.orchestrator.process_query(query)
            
            assert result['success'] is False
            assert 'Plugin not found' in result['error']
    
    async def test_plugin_failover(self):
        """Test plugin failover functionality"""
        primary_plugin = Mock()
        primary_plugin.chat_completion = AsyncMock(side_effect=Exception("Primary plugin failed"))
        
        fallback_plugin = Mock()
        fallback_plugin.chat_completion = AsyncMock(return_value={
            'success': True,
            'response': 'Fallback response'
        })
        
        with patch.object(self.orchestrator.plugin_manager, 'get_plugin') as mock_get_plugin:
            # First call returns primary plugin, second call returns fallback
            mock_get_plugin.side_effect = [primary_plugin, fallback_plugin]
            
            query = {
                'text': 'Test query',
                'plugin': 'openai',
                'fallback_plugin': 'ollama'
            }
            
            result = await self.orchestrator.process_query_with_failover(query)
            
            assert result['success'] is True
            assert result['response'] == 'Fallback response'
            assert result['used_fallback'] is True


@pytest.mark.asyncio
class TestAIOrchestrationIntegration:
    """Integration tests for AI orchestration"""
    
    @patch('ai_orchestrator.plugins.openai_plugin.openai')
    async def test_multi_plugin_workflow(self, mock_openai):
        """Test workflow using multiple plugins"""
        orchestrator = AIOrchestrator()
        
        # Register plugins
        openai_plugin = OpenAIPlugin(api_key="test_key")
        whisper_plugin = WhisperPlugin()
        
        orchestrator.plugin_manager.register_plugin('openai', openai_plugin)
        orchestrator.plugin_manager.register_plugin('whisper', whisper_plugin)
        
        # Mock OpenAI responses
        mock_openai.ChatCompletion.create.return_value = {
            'choices': [{'message': {'content': 'This is a response about the audio content.'}}],
            'usage': {'total_tokens': 20}
        }
        
        mock_openai.Audio.transcribe.return_value = {
            'text': 'This is transcribed audio content.'
        }
        
        # 1. First transcribe audio
        audio_query = {
            'audio_data': b'fake_audio_data',
            'filename': 'test.wav',
            'plugin': 'whisper'
        }
        
        transcription_result = await orchestrator.process_audio_query(audio_query)
        assert transcription_result['success'] is True
        
        # 2. Then analyze the transcribed text
        analysis_query = {
            'text': f"Analyze this transcription: {transcription_result['text']}",
            'plugin': 'openai'
        }
        
        analysis_result = await orchestrator.process_query(analysis_query)
        assert analysis_result['success'] is True
    
    async def test_conversation_memory(self):
        """Test conversation memory management"""
        orchestrator = AIOrchestrator()
        user_id = str(uuid.uuid4())
        
        with patch.object(orchestrator, 'memory_manager') as mock_memory:
            mock_memory.get_conversation_history.return_value = []
            mock_memory.add_to_history.return_value = True
            
            # Simulate a conversation
            queries = [
                "What is machine learning?",
                "Can you give me an example?",
                "What about deep learning?"
            ]
            
            conversation_history = []
            
            for query_text in queries:
                query = {
                    'text': query_text,
                    'user_id': user_id,
                    'context': conversation_history,
                    'plugin': 'openai'
                }
                
                # Mock response
                with patch.object(orchestrator.plugin_manager, 'get_plugin') as mock_get_plugin:
                    mock_plugin = Mock()
                    mock_plugin.chat_completion = AsyncMock(return_value={
                        'success': True,
                        'response': f'Response to: {query_text}',
                        'usage': {'total_tokens': 15}
                    })
                    mock_get_plugin.return_value = mock_plugin
                    
                    result = await orchestrator.process_query(query)
                    
                    # Add to conversation history
                    conversation_history.extend([
                        {'role': 'user', 'content': query_text},
                        {'role': 'assistant', 'content': result['response']}
                    ])
            
            # Verify conversation history was maintained
            assert len(conversation_history) == 6  # 3 queries + 3 responses
            mock_memory.add_to_history.call_count == 6


@pytest.mark.performance
class TestAIOrchestrationPerformance:
    """Performance tests for AI orchestration"""
    
    async def test_concurrent_query_processing(self):
        """Test performance with concurrent queries"""
        orchestrator = AIOrchestrator()
        
        # Mock plugin
        mock_plugin = Mock()
        mock_plugin.chat_completion = AsyncMock(return_value={
            'success': True,
            'response': 'Concurrent response',
            'usage': {'total_tokens': 10}
        })
        
        orchestrator.plugin_manager.register_plugin('openai', mock_plugin)
        
        # Create multiple concurrent queries
        queries = []
        for i in range(10):
            queries.append({
                'text': f'Query {i}',
                'user_id': str(uuid.uuid4()),
                'plugin': 'openai'
            })
        
        # Process queries concurrently
        tasks = [orchestrator.process_query(query) for query in queries]
        results = await asyncio.gather(*tasks)
        
        # All queries should complete successfully
        assert len(results) == 10
        assert all(result['success'] for result in results)
    
    async def test_memory_usage(self, performance_monitor):
        """Test memory usage with large conversations"""
        orchestrator = AIOrchestrator()
        
        performance_monitor.start()
        
        # Simulate large conversation history
        large_context = []
        for i in range(100):
            large_context.extend([
                {'role': 'user', 'content': f'Question {i}' * 100},
                {'role': 'assistant', 'content': f'Answer {i}' * 100}
            ])
        
        query = {
            'text': 'Final question',
            'context': large_context,
            'plugin': 'openai'
        }
        
        # Mock plugin
        with patch.object(orchestrator.plugin_manager, 'get_plugin') as mock_get_plugin:
            mock_plugin = Mock()
            mock_plugin.chat_completion = AsyncMock(return_value={
                'success': True,
                'response': 'Final answer'
            })
            mock_get_plugin.return_value = mock_plugin
            
            result = await orchestrator.process_query(query)
        
        duration = performance_monitor.stop('large_context_processing')
        memory_used = performance_monitor.peak_memory_delta
        
        assert result['success'] is True
        assert duration < 10  # Should process within 10 seconds
        assert memory_used < 100 * 1024 * 1024  # Should use less than 100MB