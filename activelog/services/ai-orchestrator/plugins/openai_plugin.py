import os
import json
import hashlib
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import base64
import io
from PIL import Image
import redis.asyncio as redis
import openai
from openai import AsyncOpenAI
import aiohttp
import time
from dataclasses import dataclass
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Rate limiting configuration for OpenAI API"""
    requests_per_minute: int = 60
    tokens_per_minute: int = 150000
    requests_per_day: int = 5000

class RateLimiter:
    """Rate limiter for OpenAI API calls"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.config = RateLimitConfig()
        self.local_state = {}
    
    async def check_rate_limit(self, endpoint: str) -> bool:
        """Check if request is within rate limits"""
        current_time = int(time.time())
        minute_key = f"rate_limit:{endpoint}:minute:{current_time // 60}"
        day_key = f"rate_limit:{endpoint}:day:{current_time // 86400}"
        
        if self.redis_client:
            return await self._check_redis_rate_limit(minute_key, day_key)
        else:
            return await self._check_local_rate_limit(endpoint, current_time)
    
    async def _check_redis_rate_limit(self, minute_key: str, day_key: str) -> bool:
        """Redis-based rate limiting"""
        try:
            pipe = self.redis_client.pipeline()
            
            # Check and increment minute counter
            await pipe.incr(minute_key)
            await pipe.expire(minute_key, 60)
            
            # Check and increment day counter
            await pipe.incr(day_key)
            await pipe.expire(day_key, 86400)
            
            results = await pipe.execute()
            minute_count = results[0]
            day_count = results[2]
            
            return (minute_count <= self.config.requests_per_minute and 
                   day_count <= self.config.requests_per_day)
        except Exception as e:
            logger.warning(f"Redis rate limiting error: {e}")
            return True  # Allow request on Redis failure
    
    async def _check_local_rate_limit(self, endpoint: str, current_time: int) -> bool:
        """Local in-memory rate limiting"""
        if endpoint not in self.local_state:
            self.local_state[endpoint] = {'minute': [], 'day': []}
        
        state = self.local_state[endpoint]
        
        # Clean old entries
        minute_cutoff = current_time - 60
        day_cutoff = current_time - 86400
        
        state['minute'] = [t for t in state['minute'] if t > minute_cutoff]
        state['day'] = [t for t in state['day'] if t > day_cutoff]
        
        # Check limits
        if (len(state['minute']) >= self.config.requests_per_minute or
            len(state['day']) >= self.config.requests_per_day):
            return False
        
        # Add current request
        state['minute'].append(current_time)
        state['day'].append(current_time)
        
        return True

def rate_limited(endpoint: str):
    """Decorator for rate limiting OpenAI API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if hasattr(self, 'rate_limiter'):
                if not await self.rate_limiter.check_rate_limit(endpoint):
                    raise Exception(f"Rate limit exceeded for {endpoint}")
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator

class OpenAIPlugin:
    """
    Comprehensive OpenAI plugin for AI Orchestrator
    
    Features:
    - Text embeddings using text-embedding-ada-002
    - GPT-4 for content analysis and tagging
    - DALL-E integration for image understanding
    - Redis caching
    - Rate limiting
    - Error handling
    """
    
    def __init__(self):
        self.name = "openai"
        self.version = "1.0.0"
        self.capabilities = [
            "text_embedding",
            "content_analysis", 
            "auto_tagging",
            "image_understanding",
            "text_generation"
        ]
        
        # Load configuration from environment
        self.config = self._load_config()
        
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.config['api_key'],
            timeout=self.config['timeout']
        )
        
        # Initialize Redis client for caching
        self.redis_client = None
        self.cache_ttl = self.config['cache_ttl']
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter()
        
        # Statistics
        self.stats = {
            'embeddings_generated': 0,
            'content_analyses': 0,
            'images_analyzed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'model_text': os.getenv('OPENAI_TEXT_MODEL', 'gpt-4'),
            'model_embedding': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-ada-002'),
            'model_vision': os.getenv('OPENAI_VISION_MODEL', 'gpt-4-vision-preview'),
            'model_dalle': os.getenv('OPENAI_DALLE_MODEL', 'dall-e-3'),
            'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '4000')),
            'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            'timeout': int(os.getenv('OPENAI_TIMEOUT', '30')),
            'cache_ttl': int(os.getenv('OPENAI_CACHE_TTL', '3600')),
            'enable_caching': os.getenv('OPENAI_ENABLE_CACHING', 'true').lower() == 'true',
            'rate_limit_rpm': int(os.getenv('OPENAI_RATE_LIMIT_RPM', '60')),
            'rate_limit_tpm': int(os.getenv('OPENAI_RATE_LIMIT_TPM', '150000')),
        }
    
    async def initialize(self, redis_client: Optional[redis.Redis] = None):
        """Initialize the plugin with Redis connection"""
        self.redis_client = redis_client
        self.rate_limiter = RateLimiter(redis_client)
        
        # Test OpenAI API connection
        if self.config['api_key']:
            try:
                await self._test_api_connection()
                logger.info("OpenAI plugin initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI plugin: {e}")
                raise
        else:
            logger.warning("OpenAI API key not provided. Plugin will not function.")
    
    async def _test_api_connection(self):
        """Test OpenAI API connection"""
        try:
            models = await self.client.models.list()
            logger.info(f"OpenAI API connected. Available models: {len(models.data)}")
        except Exception as e:
            raise Exception(f"OpenAI API connection failed: {e}")
    
    def _generate_cache_key(self, operation: str, content: str, **kwargs) -> str:
        """Generate cache key for operations"""
        key_data = {
            'operation': operation,
            'content': content[:1000],  # Limit content length for key
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"openai:{hashlib.sha256(key_string.encode()).hexdigest()}"
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from Redis cache"""
        if not self.config['enable_caching'] or not self.redis_client:
            return None
        
        try:
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                self.stats['cache_hits'] += 1
                return json.loads(cached_result)
            else:
                self.stats['cache_misses'] += 1
                return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    async def _save_to_cache(self, cache_key: str, result: Dict[str, Any]):
        """Save result to Redis cache"""
        if not self.config['enable_caching'] or not self.redis_client:
            return
        
        try:
            cached_data = {
                **result,
                'cached_at': datetime.utcnow().isoformat(),
                'ttl': self.cache_ttl
            }
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cached_data, default=str)
            )
        except Exception as e:
            logger.warning(f"Cache save error: {e}")
    
    @rate_limited("embeddings")
    async def generate_embeddings(self, text: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate text embeddings using OpenAI's text-embedding-ada-002
        
        Args:
            text: Text to generate embeddings for
            model: Optional model override
            
        Returns:
            Dict containing embeddings and metadata
        """
        if not self.config['api_key']:
            raise Exception("OpenAI API key not configured")
        
        model = model or self.config['model_embedding']
        cache_key = self._generate_cache_key('embeddings', text, model=model)
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text.strip()
            )
            
            result = {
                'embeddings': response.data[0].embedding,
                'model': model,
                'dimensions': len(response.data[0].embedding),
                'text_length': len(text),
                'created_at': datetime.utcnow().isoformat(),
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
            # Cache the result
            await self._save_to_cache(cache_key, result)
            
            self.stats['embeddings_generated'] += 1
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error generating embeddings: {e}")
            raise Exception(f"Failed to generate embeddings: {e}")
    
    @rate_limited("chat")
    async def analyze_content(self, 
                            content: str, 
                            analysis_type: str = "general",
                            custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze content using GPT-4
        
        Args:
            content: Content to analyze
            analysis_type: Type of analysis (general, sentiment, summary, etc.)
            custom_prompt: Custom analysis prompt
            
        Returns:
            Dict containing analysis results
        """
        if not self.config['api_key']:
            raise Exception("OpenAI API key not configured")
        
        cache_key = self._generate_cache_key('analysis', content, 
                                           analysis_type=analysis_type, 
                                           custom_prompt=custom_prompt)
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Build prompt based on analysis type
        if custom_prompt:
            system_prompt = custom_prompt
        else:
            system_prompt = self._get_analysis_prompt(analysis_type)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config['model_text'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature']
            )
            
            analysis_result = response.choices[0].message.content
            
            result = {
                'analysis': analysis_result,
                'analysis_type': analysis_type,
                'model': self.config['model_text'],
                'content_length': len(content),
                'created_at': datetime.utcnow().isoformat(),
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
            # Cache the result
            await self._save_to_cache(cache_key, result)
            
            self.stats['content_analyses'] += 1
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error analyzing content: {e}")
            raise Exception(f"Failed to analyze content: {e}")
    
    @rate_limited("chat")
    async def generate_tags(self, content: str, max_tags: int = 10) -> Dict[str, Any]:
        """
        Generate tags for content using GPT-4
        
        Args:
            content: Content to generate tags for
            max_tags: Maximum number of tags to generate
            
        Returns:
            Dict containing generated tags and metadata
        """
        if not self.config['api_key']:
            raise Exception("OpenAI API key not configured")
        
        cache_key = self._generate_cache_key('tags', content, max_tags=max_tags)
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        system_prompt = f"""
        You are an expert content tagger. Analyze the provided content and generate relevant tags.
        
        Requirements:
        - Generate up to {max_tags} relevant tags
        - Tags should be single words or short phrases (max 3 words)
        - Focus on topics, themes, categories, and key concepts
        - Avoid generic tags like "content" or "text"
        - Return tags as a JSON array of strings
        - Order tags by relevance (most relevant first)
        
        Example output: ["artificial intelligence", "machine learning", "technology", "automation"]
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config['model_text'],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for more consistent tagging
            )
            
            tags_text = response.choices[0].message.content.strip()
            
            # Parse JSON tags
            try:
                tags = json.loads(tags_text)
                if not isinstance(tags, list):
                    tags = [tags_text]  # Fallback if not proper JSON
            except json.JSONDecodeError:
                # Fallback: split by common delimiters
                tags = [tag.strip() for tag in tags_text.replace('[', '').replace(']', '').replace('"', '').split(',')]
            
            # Clean and validate tags
            tags = [tag.strip() for tag in tags if tag.strip()][:max_tags]
            
            result = {
                'tags': tags,
                'model': self.config['model_text'],
                'content_length': len(content),
                'max_tags': max_tags,
                'created_at': datetime.utcnow().isoformat(),
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
            # Cache the result
            await self._save_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error generating tags: {e}")
            raise Exception(f"Failed to generate tags: {e}")
    
    @rate_limited("vision")
    async def analyze_image(self, 
                          image_data: Union[str, bytes], 
                          analysis_type: str = "description",
                          detail_level: str = "auto") -> Dict[str, Any]:
        """
        Analyze image using GPT-4 Vision
        
        Args:
            image_data: Base64 encoded image or image bytes
            analysis_type: Type of analysis (description, objects, text, etc.)
            detail_level: Level of detail (low, high, auto)
            
        Returns:
            Dict containing image analysis results
        """
        if not self.config['api_key']:
            raise Exception("OpenAI API key not configured")
        
        # Convert image to base64 if needed
        if isinstance(image_data, bytes):
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        else:
            image_b64 = image_data
        
        # Generate cache key from image hash
        image_hash = hashlib.sha256(image_b64.encode()).hexdigest()[:16]
        cache_key = self._generate_cache_key('image_analysis', image_hash, 
                                           analysis_type=analysis_type,
                                           detail_level=detail_level)
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        # Build prompt based on analysis type
        prompt = self._get_image_analysis_prompt(analysis_type)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config['model_vision'],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}",
                                    "detail": detail_level
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.config['max_tokens'],
                temperature=self.config['temperature']
            )
            
            analysis_result = response.choices[0].message.content
            
            result = {
                'analysis': analysis_result,
                'analysis_type': analysis_type,
                'detail_level': detail_level,
                'model': self.config['model_vision'],
                'image_hash': image_hash,
                'created_at': datetime.utcnow().isoformat(),
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
            # Cache the result
            await self._save_to_cache(cache_key, result)
            
            self.stats['images_analyzed'] += 1
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error analyzing image: {e}")
            raise Exception(f"Failed to analyze image: {e}")
    
    @rate_limited("images")
    async def generate_image(self, 
                           prompt: str, 
                           size: str = "1024x1024", 
                           quality: str = "standard",
                           style: str = "vivid") -> Dict[str, Any]:
        """
        Generate image using DALL-E
        
        Args:
            prompt: Text prompt for image generation
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Image quality (standard, hd)
            style: Image style (vivid, natural)
            
        Returns:
            Dict containing generated image data
        """
        if not self.config['api_key']:
            raise Exception("OpenAI API key not configured")
        
        cache_key = self._generate_cache_key('image_generation', prompt, 
                                           size=size, quality=quality, style=style)
        
        # Check cache first
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            response = await self.client.images.generate(
                model=self.config['model_dalle'],
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1
            )
            
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], 'revised_prompt', prompt)
            
            result = {
                'image_url': image_url,
                'prompt': prompt,
                'revised_prompt': revised_prompt,
                'size': size,
                'quality': quality,
                'style': style,
                'model': self.config['model_dalle'],
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Cache the result
            await self._save_to_cache(cache_key, result)
            
            return result
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error generating image: {e}")
            raise Exception(f"Failed to generate image: {e}")
    
    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """Get system prompt for different analysis types"""
        prompts = {
            "general": """
            You are an expert content analyzer. Analyze the provided content and provide:
            1. A brief summary (2-3 sentences)
            2. Key topics and themes
            3. Sentiment analysis (positive, negative, neutral)
            4. Content type and structure
            5. Notable insights or patterns
            
            Provide your analysis in a clear, structured format.
            """,
            "sentiment": """
            You are a sentiment analysis expert. Analyze the emotional tone and sentiment of the content.
            Provide:
            1. Overall sentiment (positive, negative, neutral) with confidence score
            2. Specific emotions detected
            3. Key phrases that indicate sentiment
            4. Sentiment distribution if mixed
            """,
            "summary": """
            You are an expert summarizer. Create a concise but comprehensive summary of the content.
            Include:
            1. Main points and key information
            2. Important details and context
            3. Conclusion or outcome if applicable
            
            Keep the summary clear and well-structured.
            """,
            "topics": """
            You are a topic extraction expert. Identify and analyze the main topics in the content.
            Provide:
            1. Primary topics and themes
            2. Secondary topics
            3. Topic relationships and connections
            4. Topic relevance scores
            """,
            "quality": """
            You are a content quality analyst. Evaluate the content for:
            1. Clarity and readability
            2. Structure and organization
            3. Factual accuracy (if verifiable)
            4. Completeness and depth
            5. Overall quality score (1-10)
            
            Provide specific feedback and suggestions for improvement.
            """
        }
        
        return prompts.get(analysis_type, prompts["general"])
    
    def _get_image_analysis_prompt(self, analysis_type: str) -> str:
        """Get prompt for different image analysis types"""
        prompts = {
            "description": "Provide a detailed description of this image, including objects, people, setting, colors, and overall composition.",
            "objects": "Identify and list all objects, people, and elements visible in this image. Provide locations and descriptions for each.",
            "text": "Extract and transcribe any text visible in this image, including signs, labels, documents, or written content.",
            "scene": "Analyze the scene in this image. Describe the setting, environment, activity, and context.",
            "style": "Analyze the artistic style, composition, lighting, and visual elements of this image.",
            "emotions": "Analyze the emotions, mood, and feelings conveyed by this image. Consider facial expressions, body language, and overall atmosphere.",
            "technical": "Provide a technical analysis of this image including composition, lighting, color palette, perspective, and photographic techniques used."
        }
        
        return prompts.get(analysis_type, prompts["description"])
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get plugin statistics"""
        return {
            'plugin': self.name,
            'version': self.version,
            'capabilities': self.capabilities,
            'stats': self.stats,
            'config': {
                'models': {
                    'text': self.config['model_text'],
                    'embedding': self.config['model_embedding'],
                    'vision': self.config['model_vision'],
                    'dalle': self.config['model_dalle']
                },
                'caching_enabled': self.config['enable_caching'],
                'cache_ttl': self.cache_ttl
            },
            'status': 'active' if self.config['api_key'] else 'inactive'
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        try:
            if not self.config['api_key']:
                return {'status': 'unhealthy', 'reason': 'API key not configured'}
            
            # Test API connection
            await self._test_api_connection()
            
            return {
                'status': 'healthy',
                'plugin': self.name,
                'version': self.version,
                'api_connected': True,
                'redis_connected': self.redis_client is not None,
                'last_check': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'plugin': self.name,
                'reason': str(e),
                'last_check': datetime.utcnow().isoformat()
            }

# Plugin factory function
def create_plugin() -> OpenAIPlugin:
    """Factory function to create OpenAI plugin instance"""
    return OpenAIPlugin()

# Export the plugin class and factory
__all__ = ['OpenAIPlugin', 'create_plugin']