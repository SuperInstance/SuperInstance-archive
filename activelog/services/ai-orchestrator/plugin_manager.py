"""
Plugin Manager for AI Orchestrator
Handles loading and managing AI plugins including OpenAI
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
import importlib
import sys
from pathlib import Path
import redis.asyncio as redis

# Configure logging
logger = logging.getLogger(__name__)

class PluginManager:
    """Manages AI plugins for the orchestrator"""
    
    def __init__(self):
        self.plugins = {}
        self.redis_client = None
        self.plugin_stats = {
            'loaded': 0,
            'active': 0,
            'errors': 0
        }
    
    async def initialize(self, redis_client: Optional[redis.Redis] = None):
        """Initialize plugin manager with Redis connection"""
        self.redis_client = redis_client
        await self.load_plugins()
    
    async def load_plugins(self):
        """Load all available plugins"""
        plugins_dir = Path(__file__).parent / "plugins"
        
        # Ensure plugins directory exists
        if not plugins_dir.exists():
            logger.warning(f"Plugins directory not found: {plugins_dir}")
            return
        
        # Add plugins directory to Python path
        sys.path.insert(0, str(plugins_dir.parent))
        
        try:
            await self.load_openai_plugin()
        except Exception as e:
            logger.error(f"Failed to load OpenAI plugin: {e}")
            self.plugin_stats['errors'] += 1
        
        try:
            await self.load_ollama_plugin()
        except Exception as e:
            logger.error(f"Failed to load Ollama plugin: {e}")
            self.plugin_stats['errors'] += 1
        
        try:
            await self.load_whisper_plugin()
        except Exception as e:
            logger.error(f"Failed to load Whisper plugin: {e}")
            self.plugin_stats['errors'] += 1
        
        logger.info(f"Plugin loading completed. Stats: {self.plugin_stats}")
    
    async def load_openai_plugin(self):
        """Load OpenAI plugin specifically"""
        try:
            # Import the OpenAI plugin
            from plugins.openai_plugin import create_plugin
            
            # Create plugin instance
            plugin = create_plugin()
            
            # Initialize plugin with Redis
            await plugin.initialize(self.redis_client)
            
            # Store plugin
            self.plugins['openai'] = plugin
            self.plugin_stats['loaded'] += 1
            
            # Check if plugin is active (has API key)
            health = await plugin.health_check()
            if health['status'] == 'healthy':
                self.plugin_stats['active'] += 1
            
            logger.info(f"OpenAI plugin loaded successfully. Status: {health['status']}")
            
        except ImportError as e:
            logger.error(f"Failed to import OpenAI plugin: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI plugin: {e}")
            raise
    
    async def load_ollama_plugin(self):
        """Load Ollama plugin specifically"""
        try:
            # Import the Ollama plugin
            from plugins.ollama_plugin import create_plugin
            
            # Create plugin instance
            plugin = create_plugin()
            
            # Initialize plugin with Redis
            await plugin.initialize(self.redis_client)
            
            # Store plugin
            self.plugins['ollama'] = plugin
            self.plugin_stats['loaded'] += 1
            
            # Check if plugin is active (can connect to Ollama)
            health = await plugin.health_check()
            if health['status'] == 'healthy':
                self.plugin_stats['active'] += 1
            
            logger.info(f"Ollama plugin loaded successfully. Status: {health['status']}")
            
        except ImportError as e:
            logger.error(f"Failed to import Ollama plugin: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Ollama plugin: {e}")
            raise
    
    async def load_whisper_plugin(self):
        """Load Whisper plugin specifically"""
        try:
            # Import the Whisper plugin
            from plugins.whisper_plugin import create_plugin
            
            # Create plugin instance
            plugin = create_plugin()
            
            # Initialize plugin with Redis
            await plugin.initialize(self.redis_client)
            
            # Store plugin
            self.plugins['whisper'] = plugin
            self.plugin_stats['loaded'] += 1
            
            # Check if plugin is active (has API key and ES connection)
            health = await plugin.health_check()
            if health['status'] == 'healthy':
                self.plugin_stats['active'] += 1
            
            logger.info(f"Whisper plugin loaded successfully. Status: {health['status']}")
            
        except ImportError as e:
            logger.error(f"Failed to import Whisper plugin: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Whisper plugin: {e}")
            raise
    
    async def get_plugin(self, plugin_name: str):
        """Get a specific plugin by name"""
        return self.plugins.get(plugin_name)
    
    async def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins with their status"""
        plugin_list = []
        
        for name, plugin in self.plugins.items():
            try:
                health = await plugin.health_check()
                stats = await plugin.get_stats()
                
                plugin_info = {
                    'name': name,
                    'version': stats.get('version', 'unknown'),
                    'capabilities': stats.get('capabilities', []),
                    'status': health['status'],
                    'stats': stats.get('stats', {}),
                    'config': stats.get('config', {})
                }
                plugin_list.append(plugin_info)
                
            except Exception as e:
                plugin_list.append({
                    'name': name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return plugin_list
    
    async def get_plugin_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities map for all plugins"""
        capabilities = {}
        
        for name, plugin in self.plugins.items():
            try:
                stats = await plugin.get_stats()
                capabilities[name] = stats.get('capabilities', [])
            except Exception as e:
                logger.error(f"Error getting capabilities for {name}: {e}")
                capabilities[name] = []
        
        return capabilities
    
    # OpenAI Plugin specific methods
    async def generate_embeddings(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Generate text embeddings using OpenAI plugin"""
        openai_plugin = await self.get_plugin('openai')
        if not openai_plugin:
            raise Exception("OpenAI plugin not available")
        
        return await openai_plugin.generate_embeddings(text, model)
    
    async def analyze_content(self, content: str, analysis_type: str = "general", 
                            custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Analyze content using OpenAI plugin"""
        openai_plugin = await self.get_plugin('openai')
        if not openai_plugin:
            raise Exception("OpenAI plugin not available")
        
        return await openai_plugin.analyze_content(content, analysis_type, custom_prompt)
    
    async def generate_tags(self, content: str, max_tags: int = 10) -> Dict[str, Any]:
        """Generate tags using OpenAI plugin"""
        openai_plugin = await self.get_plugin('openai')
        if not openai_plugin:
            raise Exception("OpenAI plugin not available")
        
        return await openai_plugin.generate_tags(content, max_tags)
    
    async def analyze_image(self, image_data, analysis_type: str = "description", 
                          detail_level: str = "auto") -> Dict[str, Any]:
        """Analyze image using OpenAI plugin"""
        openai_plugin = await self.get_plugin('openai')
        if not openai_plugin:
            raise Exception("OpenAI plugin not available")
        
        return await openai_plugin.analyze_image(image_data, analysis_type, detail_level)
    
    async def generate_image(self, prompt: str, size: str = "1024x1024", 
                           quality: str = "standard", style: str = "vivid") -> Dict[str, Any]:
        """Generate image using OpenAI plugin"""
        openai_plugin = await self.get_plugin('openai')
        if not openai_plugin:
            raise Exception("OpenAI plugin not available")
        
        return await openai_plugin.generate_image(prompt, size, quality, style)
    
    # Ollama Plugin specific methods
    async def chat_completion(self, messages: List[Dict[str, str]], model: Optional[str] = None, 
                            stream: bool = False, **kwargs) -> Dict[str, Any]:
        """Generate chat completion using Ollama plugin"""
        ollama_plugin = await self.get_plugin('ollama')
        if not ollama_plugin:
            raise Exception("Ollama plugin not available")
        
        return await ollama_plugin.chat_completion(messages, model, stream, **kwargs)
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, 
                          stream: bool = False, **kwargs) -> Dict[str, Any]:
        """Generate text using Ollama plugin"""
        ollama_plugin = await self.get_plugin('ollama')
        if not ollama_plugin:
            raise Exception("Ollama plugin not available")
        
        return await ollama_plugin.generate_text(prompt, model, stream, **kwargs)
    
    async def list_models(self) -> Dict[str, Any]:
        """List available models in Ollama"""
        ollama_plugin = await self.get_plugin('ollama')
        if not ollama_plugin:
            raise Exception("Ollama plugin not available")
        
        return await ollama_plugin.list_models()
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull a model in Ollama"""
        ollama_plugin = await self.get_plugin('ollama')
        if not ollama_plugin:
            raise Exception("Ollama plugin not available")
        
        return await ollama_plugin.pull_model(model_name)
    
    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """Delete a model in Ollama"""
        ollama_plugin = await self.get_plugin('ollama')
        if not ollama_plugin:
            raise Exception("Ollama plugin not available")
        
        return await ollama_plugin.delete_model(model_name)
    
    # Whisper Plugin specific methods
    async def transcribe_audio(self, audio_file, file_name: Optional[str] = None, 
                             language: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Transcribe audio using Whisper plugin"""
        whisper_plugin = await self.get_plugin('whisper')
        if not whisper_plugin:
            raise Exception("Whisper plugin not available")
        
        return await whisper_plugin.transcribe_audio(audio_file, file_name, language, **kwargs)
    
    async def search_transcripts(self, query: str, limit: int = 10, 
                               offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Search transcripts using Whisper plugin"""
        whisper_plugin = await self.get_plugin('whisper')
        if not whisper_plugin:
            raise Exception("Whisper plugin not available")
        
        return await whisper_plugin.search_transcripts(query, limit, offset, filters)
    
    async def get_transcript(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get transcript by file hash using Whisper plugin"""
        whisper_plugin = await self.get_plugin('whisper')
        if not whisper_plugin:
            raise Exception("Whisper plugin not available")
        
        return await whisper_plugin.get_transcript(file_hash)
    
    async def delete_transcript(self, file_hash: str) -> bool:
        """Delete transcript using Whisper plugin"""
        whisper_plugin = await self.get_plugin('whisper')
        if not whisper_plugin:
            raise Exception("Whisper plugin not available")
        
        return await whisper_plugin.delete_transcript(file_hash)
    
    async def get_manager_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics"""
        plugin_stats = {}
        total_requests = 0
        total_errors = 0
        
        for name, plugin in self.plugins.items():
            try:
                stats = await plugin.get_stats()
                plugin_stats[name] = stats['stats']
                
                # Aggregate stats
                if 'embeddings_generated' in stats['stats']:
                    total_requests += stats['stats']['embeddings_generated']
                if 'content_analyses' in stats['stats']:
                    total_requests += stats['stats']['content_analyses']
                if 'images_analyzed' in stats['stats']:
                    total_requests += stats['stats']['images_analyzed']
                if 'errors' in stats['stats']:
                    total_errors += stats['stats']['errors']
                    
            except Exception as e:
                logger.error(f"Error getting stats for {name}: {e}")
        
        return {
            'manager_stats': self.plugin_stats,
            'plugin_stats': plugin_stats,
            'aggregate_stats': {
                'total_requests': total_requests,
                'total_errors': total_errors,
                'error_rate': total_errors / max(total_requests, 1) * 100
            },
            'plugins_loaded': len(self.plugins),
            'redis_connected': self.redis_client is not None
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all plugins"""
        health_status = {
            'manager': 'healthy',
            'plugins': {},
            'summary': {
                'total': len(self.plugins),
                'healthy': 0,
                'unhealthy': 0
            }
        }
        
        for name, plugin in self.plugins.items():
            try:
                plugin_health = await plugin.health_check()
                health_status['plugins'][name] = plugin_health
                
                if plugin_health['status'] == 'healthy':
                    health_status['summary']['healthy'] += 1
                else:
                    health_status['summary']['unhealthy'] += 1
                    
            except Exception as e:
                health_status['plugins'][name] = {
                    'status': 'error',
                    'error': str(e)
                }
                health_status['summary']['unhealthy'] += 1
        
        # Set overall manager status
        if health_status['summary']['unhealthy'] > 0:
            health_status['manager'] = 'degraded'
        
        return health_status

# Global plugin manager instance
plugin_manager = PluginManager()