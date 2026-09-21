"""
Ollama Plugin for ActiveLog AI Orchestrator
Provides local LLM capabilities with streaming support and model management
"""
import os
import json
import asyncio
import logging
import aiohttp
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import hashlib
import redis.asyncio as redis

# Configure logging
logger = logging.getLogger(__name__)

class OllamaPlugin:
    """Ollama plugin for local LLM integration"""
    
    def __init__(self):
        self.name = "ollama"
        self.version = "1.0.0"
        
        # Configuration from environment
        self.ollama_host = os.getenv("OLLAMA_HOST", "localhost")
        self.ollama_port = int(os.getenv("OLLAMA_PORT", "11434"))
        self.ollama_base_url = f"http://{self.ollama_host}:{self.ollama_port}"
        
        # Default models and settings
        self.default_model = os.getenv("OLLAMA_DEFAULT_MODEL", "llama2")
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))
        self.max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "2048"))
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        
        # Caching configuration
        self.enable_caching = os.getenv("OLLAMA_ENABLE_CACHING", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("OLLAMA_CACHE_TTL", "1800"))  # 30 minutes
        
        # Fallback configuration
        self.enable_fallback = os.getenv("OLLAMA_ENABLE_FALLBACK", "true").lower() == "true"
        self.fallback_to_openai = os.getenv("OLLAMA_FALLBACK_TO_OPENAI", "true").lower() == "true"
        
        # Rate limiting
        self.rate_limit_rpm = int(os.getenv("OLLAMA_RATE_LIMIT_RPM", "100"))
        self.rate_limit_per_minute = {}
        
        # Internal state
        self.redis_client = None
        self.session = None
        self.available_models = []
        self.stats = {
            "chat_completions": 0,
            "embeddings_generated": 0,
            "models_listed": 0,
            "models_pulled": 0,
            "models_deleted": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "fallback_used": 0,
            "errors": 0,
            "stream_sessions": 0
        }
    
    async def initialize(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the Ollama plugin"""
        self.redis_client = redis_client
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Test connection and get available models
        try:
            await self.refresh_models()
            logger.info(f"Ollama plugin initialized. Available models: {len(self.available_models)}")
        except Exception as e:
            logger.warning(f"Ollama connection failed during initialization: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if Ollama is healthy and accessible"""
        try:
            async with self.session.get(f"{self.ollama_base_url}/api/tags") as response:
                if response.status == 200:
                    models = await response.json()
                    return {
                        "status": "healthy",
                        "ollama_version": response.headers.get("ollama-version", "unknown"),
                        "models_available": len(models.get("models", [])),
                        "base_url": self.ollama_base_url,
                        "fallback_enabled": self.enable_fallback
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "fallback_available": self.enable_fallback
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": [
                "chat_completion",
                "text_generation", 
                "embeddings",
                "model_management",
                "streaming",
                "fallback_support"
            ],
            "stats": self.stats.copy(),
            "config": {
                "base_url": self.ollama_base_url,
                "default_model": self.default_model,
                "caching_enabled": self.enable_caching,
                "fallback_enabled": self.enable_fallback,
                "available_models": len(self.available_models)
            }
        }
    
    def _generate_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operations"""
        key_data = f"{operation}:{json.dumps(kwargs, sort_keys=True)}"
        return f"ollama:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available"""
        if not self.enable_caching or not self.redis_client:
            return None
        
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                self.stats["cache_hits"] += 1
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        
        self.stats["cache_misses"] += 1
        return None
    
    async def _cache_response(self, cache_key: str, response: Dict[str, Any]):
        """Cache response"""
        if not self.enable_caching or not self.redis_client:
            return
        
        try:
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(response)
            )
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    async def _check_rate_limit(self, identifier: str = "global") -> bool:
        """Check rate limiting"""
        current_time = datetime.utcnow()
        minute_key = current_time.strftime("%Y-%m-%d-%H-%M")
        
        if identifier not in self.rate_limit_per_minute:
            self.rate_limit_per_minute[identifier] = {}
        
        # Clean old entries
        for key in list(self.rate_limit_per_minute[identifier].keys()):
            if key != minute_key:
                del self.rate_limit_per_minute[identifier][key]
        
        current_count = self.rate_limit_per_minute[identifier].get(minute_key, 0)
        if current_count >= self.rate_limit_rpm:
            return False
        
        self.rate_limit_per_minute[identifier][minute_key] = current_count + 1
        return True
    
    async def refresh_models(self) -> List[Dict[str, Any]]:
        """Refresh the list of available models"""
        try:
            async with self.session.get(f"{self.ollama_base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self.available_models = data.get("models", [])
                    self.stats["models_listed"] += 1
                    return self.available_models
                else:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
        except Exception as e:
            logger.error(f"Failed to refresh models: {e}")
            self.stats["errors"] += 1
            raise
    
    async def list_models(self) -> Dict[str, Any]:
        """List all available models"""
        try:
            models = await self.refresh_models()
            
            formatted_models = []
            for model in models:
                formatted_models.append({
                    "name": model.get("name"),
                    "size": model.get("size", 0),
                    "digest": model.get("digest"),
                    "modified_at": model.get("modified_at"),
                    "details": model.get("details", {})
                })
            
            return {
                "models": formatted_models,
                "total": len(formatted_models),
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"List models failed: {e}")
            self.stats["errors"] += 1
            raise Exception(f"Failed to list models: {e}")
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull a model from Ollama library"""
        if not await self._check_rate_limit(f"pull:{model_name}"):
            raise Exception("Rate limit exceeded for model pulling")
        
        try:
            payload = {"name": model_name}
            
            async with self.session.post(
                f"{self.ollama_base_url}/api/pull",
                json=payload
            ) as response:
                if response.status == 200:
                    # For streaming response, we'll collect all chunks
                    progress_info = []
                    async for line in response.content:
                        if line:
                            try:
                                chunk = json.loads(line.decode())
                                progress_info.append(chunk)
                            except json.JSONDecodeError:
                                continue
                    
                    self.stats["models_pulled"] += 1
                    await self.refresh_models()  # Refresh model list
                    
                    return {
                        "model": model_name,
                        "status": "pulled",
                        "progress": progress_info,
                        "pulled_at": datetime.utcnow().isoformat()
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Pull model failed: {e}")
            self.stats["errors"] += 1
            raise Exception(f"Failed to pull model {model_name}: {e}")
    
    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """Delete a model"""
        try:
            payload = {"name": model_name}
            
            async with self.session.delete(
                f"{self.ollama_base_url}/api/delete",
                json=payload
            ) as response:
                if response.status == 200:
                    self.stats["models_deleted"] += 1
                    await self.refresh_models()  # Refresh model list
                    
                    return {
                        "model": model_name,
                        "status": "deleted",
                        "deleted_at": datetime.utcnow().isoformat()
                    }
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Delete model failed: {e}")
            self.stats["errors"] += 1
            raise Exception(f"Failed to delete model {model_name}: {e}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate chat completion"""
        if not await self._check_rate_limit("chat"):
            raise Exception("Rate limit exceeded for chat completions")
        
        model = model or self.default_model
        
        # Check cache for non-streaming requests
        cache_key = None
        if not stream and self.enable_caching:
            cache_key = self._generate_cache_key(
                "chat", messages=messages, model=model, **kwargs
            )
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens)
                }
            }
            
            # Add additional options
            if "system" in kwargs:
                payload["system"] = kwargs["system"]
            
            async with self.session.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    if stream:
                        return await self._handle_streaming_response(response, "chat")
                    else:
                        result = await response.json()
                        
                        formatted_response = {
                            "model": model,
                            "content": result.get("message", {}).get("content", ""),
                            "role": result.get("message", {}).get("role", "assistant"),
                            "done": result.get("done", True),
                            "total_duration": result.get("total_duration"),
                            "load_duration": result.get("load_duration"),
                            "prompt_eval_count": result.get("prompt_eval_count"),
                            "eval_count": result.get("eval_count"),
                            "created_at": datetime.utcnow().isoformat()
                        }
                        
                        # Cache the response
                        if cache_key:
                            await self._cache_response(cache_key, formatted_response)
                        
                        self.stats["chat_completions"] += 1
                        return formatted_response
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            self.stats["errors"] += 1
            
            # Try fallback if enabled
            if self.enable_fallback and self.fallback_to_openai:
                return await self._fallback_to_openai("chat", messages=messages, **kwargs)
            
            raise Exception(f"Chat completion failed: {e}")
    
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text completion"""
        if not await self._check_rate_limit("generate"):
            raise Exception("Rate limit exceeded for text generation")
        
        model = model or self.default_model
        
        # Check cache for non-streaming requests
        cache_key = None
        if not stream and self.enable_caching:
            cache_key = self._generate_cache_key(
                "generate", prompt=prompt, model=model, **kwargs
            )
            cached_response = await self._get_cached_response(cache_key)
            if cached_response:
                return cached_response
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {
                    "temperature": kwargs.get("temperature", self.temperature),
                    "num_predict": kwargs.get("max_tokens", self.max_tokens)
                }
            }
            
            # Add additional options
            if "system" in kwargs:
                payload["system"] = kwargs["system"]
            
            async with self.session.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    if stream:
                        return await self._handle_streaming_response(response, "generate")
                    else:
                        result = await response.json()
                        
                        formatted_response = {
                            "model": model,
                            "response": result.get("response", ""),
                            "done": result.get("done", True),
                            "total_duration": result.get("total_duration"),
                            "load_duration": result.get("load_duration"),
                            "prompt_eval_count": result.get("prompt_eval_count"),
                            "eval_count": result.get("eval_count"),
                            "created_at": datetime.utcnow().isoformat()
                        }
                        
                        # Cache the response
                        if cache_key:
                            await self._cache_response(cache_key, formatted_response)
                        
                        return formatted_response
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            self.stats["errors"] += 1
            
            # Try fallback if enabled
            if self.enable_fallback and self.fallback_to_openai:
                return await self._fallback_to_openai("generate", prompt=prompt, **kwargs)
            
            raise Exception(f"Text generation failed: {e}")
    
    async def generate_embeddings(
        self,
        text: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate embeddings for text"""
        if not await self._check_rate_limit("embeddings"):
            raise Exception("Rate limit exceeded for embeddings")
        
        model = model or "llama2"  # Default embedding model
        
        # Check cache
        cache_key = self._generate_cache_key("embeddings", text=text, model=model)
        cached_response = await self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        try:
            payload = {
                "model": model,
                "prompt": text
            }
            
            async with self.session.post(
                f"{self.ollama_base_url}/api/embeddings",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    formatted_response = {
                        "model": model,
                        "embeddings": result.get("embedding", []),
                        "dimensions": len(result.get("embedding", [])),
                        "text": text,
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    # Cache the response
                    await self._cache_response(cache_key, formatted_response)
                    
                    self.stats["embeddings_generated"] += 1
                    return formatted_response
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            logger.error(f"Embeddings generation failed: {e}")
            self.stats["errors"] += 1
            
            # Try fallback if enabled
            if self.enable_fallback and self.fallback_to_openai:
                return await self._fallback_to_openai("embeddings", text=text)
            
            raise Exception(f"Embeddings generation failed: {e}")
    
    async def _handle_streaming_response(
        self,
        response: aiohttp.ClientResponse,
        operation_type: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming response from Ollama"""
        self.stats["stream_sessions"] += 1
        
        try:
            async for line in response.content:
                if line:
                    try:
                        chunk = json.loads(line.decode())
                        
                        if operation_type == "chat":
                            yield {
                                "type": "chat_chunk",
                                "content": chunk.get("message", {}).get("content", ""),
                                "done": chunk.get("done", False),
                                "model": chunk.get("model"),
                                "created_at": datetime.utcnow().isoformat()
                            }
                        elif operation_type == "generate":
                            yield {
                                "type": "text_chunk",
                                "response": chunk.get("response", ""),
                                "done": chunk.get("done", False),
                                "model": chunk.get("model"),
                                "created_at": datetime.utcnow().isoformat()
                            }
                        
                        if chunk.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield {
                "type": "error",
                "error": str(e),
                "created_at": datetime.utcnow().isoformat()
            }
    
    async def _fallback_to_openai(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Fallback to OpenAI when Ollama fails"""
        try:
            # Import OpenAI plugin dynamically to avoid circular imports
            from .openai_plugin import create_plugin as create_openai_plugin
            
            openai_plugin = create_openai_plugin()
            await openai_plugin.initialize(self.redis_client)
            
            self.stats["fallback_used"] += 1
            
            if operation == "chat":
                # Convert to OpenAI format
                content = ""
                for msg in kwargs.get("messages", []):
                    content += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
                
                result = await openai_plugin.analyze_content(
                    content, "general", kwargs.get("system")
                )
                return {
                    "model": "openai-fallback",
                    "content": result.get("analysis", ""),
                    "role": "assistant",
                    "fallback": True,
                    "created_at": datetime.utcnow().isoformat()
                }
                
            elif operation == "generate":
                result = await openai_plugin.analyze_content(
                    kwargs.get("prompt", ""), "general"
                )
                return {
                    "model": "openai-fallback",
                    "response": result.get("analysis", ""),
                    "fallback": True,
                    "created_at": datetime.utcnow().isoformat()
                }
                
            elif operation == "embeddings":
                result = await openai_plugin.generate_embeddings(kwargs.get("text", ""))
                return {
                    "model": "openai-fallback",
                    "embeddings": result.get("embedding", []),
                    "dimensions": len(result.get("embedding", [])),
                    "fallback": True,
                    "created_at": datetime.utcnow().isoformat()
                }
            
        except Exception as e:
            logger.error(f"Fallback to OpenAI failed: {e}")
            raise Exception(f"Both Ollama and OpenAI fallback failed: {e}")


def create_plugin():
    """Factory function to create Ollama plugin instance"""
    return OllamaPlugin()