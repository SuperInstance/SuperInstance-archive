"""
LLM Router Service
Routes requests to optimal LLM providers (OpenAI, Claude, Llama, etc.)
"""

import asyncio
import aiohttp
import hashlib
import json
import tiktoken
from decimal import Decimal
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from ...models.ai_operations import AIOperation, AIOperationType, AIProvider, OperationStatus
from ...config.settings import settings, AI_OPERATION_COSTS
from ..cache.result_cache import ResultCache
from ..compute.optimizer import ComputeOptimizer
from ..cost.estimator import CostEstimator

logger = logging.getLogger(__name__)

class LLMRouter:
    """Intelligent LLM routing with cost optimization and caching"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = ResultCache(db)
        self.optimizer = ComputeOptimizer(db)
        self.cost_estimator = CostEstimator(db)
        
        # Provider configurations
        self.providers = {
            AIProvider.OPENAI: self._openai_generate,
            AIProvider.ANTHROPIC: self._anthropic_generate,
            AIProvider.LOCAL: self._local_llm_generate,
            AIProvider.TOGETHER_AI: self._together_generate,
            AIProvider.REPLICATE: self._replicate_generate
        }
        
        # Model capabilities mapping
        self.model_capabilities = {
            "gpt-4": {
                "context_length": 8192,
                "supports_functions": True,
                "supports_vision": False,
                "cost_per_1k_tokens": Decimal("0.03"),
                "provider": AIProvider.OPENAI
            },
            "gpt-4-turbo": {
                "context_length": 128000,
                "supports_functions": True,
                "supports_vision": True,
                "cost_per_1k_tokens": Decimal("0.01"),
                "provider": AIProvider.OPENAI
            },
            "gpt-3.5-turbo": {
                "context_length": 16385,
                "supports_functions": True,
                "supports_vision": False,
                "cost_per_1k_tokens": Decimal("0.002"),
                "provider": AIProvider.OPENAI
            },
            "claude-3-opus": {
                "context_length": 200000,
                "supports_functions": False,
                "supports_vision": True,
                "cost_per_1k_tokens": Decimal("0.015"),
                "provider": AIProvider.ANTHROPIC
            },
            "claude-3-sonnet": {
                "context_length": 200000,
                "supports_functions": False,
                "supports_vision": True,
                "cost_per_1k_tokens": Decimal("0.003"),
                "provider": AIProvider.ANTHROPIC
            },
            "claude-3-haiku": {
                "context_length": 200000,
                "supports_functions": False,
                "supports_vision": True,
                "cost_per_1k_tokens": Decimal("0.00025"),
                "provider": AIProvider.ANTHROPIC
            },
            "llama-2-70b": {
                "context_length": 4096,
                "supports_functions": False,
                "supports_vision": False,
                "cost_per_1k_tokens": Decimal("0.001"),
                "provider": AIProvider.TOGETHER_AI
            },
            "local-llama": {
                "context_length": 4096,
                "supports_functions": False,
                "supports_vision": False,
                "cost_per_1k_tokens": Decimal("0.0001"),
                "provider": AIProvider.LOCAL
            }
        }
    
    async def generate_text(
        self,
        user_id: str,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = False,
        functions: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text with optimal model selection"""
        
        # Auto-select model if not specified
        if not model:
            model = await self._select_optimal_model(messages, functions, kwargs)
        
        # Create operation record
        operation = AIOperation(
            user_id=user_id,
            operation_type=AIOperationType.TEXT_GENERATION,
            provider=self.model_capabilities[model]["provider"],
            model_name=model,
            input_data={
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "functions": functions,
                **kwargs
            }
        )
        
        # Generate input hash for caching
        input_hash = self._generate_input_hash(operation.input_data)
        operation.input_hash = input_hash
        
        self.db.add(operation)
        self.db.commit()
        
        try:
            # Check cache first (only for non-streaming requests)
            if not stream:
                cached_result = await self.cache.get_cached_result(
                    input_hash, AIOperationType.TEXT_GENERATION
                )
                
                if cached_result:
                    operation.status = OperationStatus.COMPLETED
                    operation.output_data = cached_result["output_data"]
                    operation.actual_cost_cc = Decimal("0")
                    operation.cost_saved_cc = cached_result.get("original_cost_cc", Decimal("0"))
                    operation.completed_at = datetime.utcnow()
                    self.db.commit()
                    
                    return {
                        "operation_id": operation.id,
                        "status": "completed",
                        "response": cached_result["output_data"]["response"],
                        "cached": True,
                        "cost_cc": 0,
                        "cost_saved_cc": float(operation.cost_saved_cc),
                        "model": model
                    }
            
            # Estimate cost
            estimated_tokens = self._estimate_token_count(messages, max_tokens)
            cost_estimate = await self.cost_estimator.estimate_text_generation_cost(
                model, estimated_tokens
            )
            operation.estimated_cost_cc = cost_estimate["total_cost_cc"]
            
            operation.status = OperationStatus.PROCESSING
            operation.started_at = datetime.utcnow()
            self.db.commit()
            
            # Generate text using selected provider
            provider = self.model_capabilities[model]["provider"]
            generator_func = self.providers.get(provider)
            if not generator_func:
                raise ValueError(f"Unsupported provider: {provider}")
            
            if stream:
                return await self._handle_streaming_generation(operation, generator_func)
            else:
                return await self._handle_standard_generation(operation, generator_func)
                
        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Text generation failed for operation {operation.id}: {str(e)}")
            raise
    
    async def _handle_standard_generation(
        self, 
        operation: AIOperation, 
        generator_func
    ) -> Dict[str, Any]:
        """Handle standard (non-streaming) text generation"""
        
        result = await generator_func(operation)
        
        # Store result in cache
        await self.cache.store_result(
            operation.input_hash,
            AIOperationType.TEXT_GENERATION,
            result["output_data"],
            {},  # No files for text generation
            operation.estimated_cost_cc
        )
        
        # Update operation with results
        operation.status = OperationStatus.COMPLETED
        operation.output_data = result["output_data"]
        operation.actual_cost_cc = result["actual_cost_cc"]
        operation.processing_time_seconds = result.get("processing_time", 0)
        operation.completed_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "operation_id": operation.id,
            "status": "completed",
            "response": result["output_data"]["response"],
            "cached": False,
            "cost_cc": float(operation.actual_cost_cc),
            "processing_time": float(operation.processing_time_seconds),
            "model": operation.model_name,
            "usage": result["output_data"].get("usage", {})
        }
    
    async def _handle_streaming_generation(
        self, 
        operation: AIOperation, 
        generator_func
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Handle streaming text generation"""
        
        full_response = ""
        start_time = datetime.utcnow()
        
        try:
            async for chunk in generator_func(operation, stream=True):
                if "content" in chunk:
                    full_response += chunk["content"]
                yield chunk
            
            # Update operation after streaming completes
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            actual_tokens = self._count_tokens(full_response, operation.model_name)
            actual_cost = self._calculate_actual_cost(operation.model_name, actual_tokens)
            
            operation.status = OperationStatus.COMPLETED
            operation.output_data = {
                "response": full_response,
                "usage": {"total_tokens": actual_tokens}
            }
            operation.actual_cost_cc = actual_cost
            operation.processing_time_seconds = Decimal(str(processing_time))
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            
        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            raise
    
    async def _openai_generate(self, operation: AIOperation, stream: bool = False) -> Any:
        """Generate text using OpenAI API"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {settings.llm.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": operation.model_name,
            "messages": input_data["messages"],
            "temperature": input_data.get("temperature", 0.7),
            "stream": stream
        }
        
        if input_data.get("max_tokens"):
            payload["max_tokens"] = input_data["max_tokens"]
        
        if input_data.get("functions"):
            payload["functions"] = input_data["functions"]
        
        if stream:
            return self._openai_stream(payload, headers)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {error_text}")
                
                result = await response.json()
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "output_data": {
                "response": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result["model"]
            },
            "actual_cost_cc": self._calculate_cost_from_usage(
                operation.model_name, result.get("usage", {})
            ),
            "processing_time": processing_time
        }
    
    async def _openai_stream(self, payload: Dict, headers: Dict) -> AsyncGenerator:
        """Handle OpenAI streaming responses"""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {error_text}")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                if "choices" in data and data["choices"]:
                                    delta = data["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield {
                                            "content": delta["content"],
                                            "type": "content"
                                        }
                            except json.JSONDecodeError:
                                continue
    
    async def _anthropic_generate(self, operation: AIOperation, stream: bool = False) -> Any:
        """Generate text using Anthropic Claude API"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        headers = {
            "x-api-key": settings.llm.anthropic_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert OpenAI format to Anthropic format
        messages = input_data["messages"]
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append(msg)
        
        payload = {
            "model": operation.model_name,
            "messages": anthropic_messages,
            "max_tokens": input_data.get("max_tokens", 1000),
            "temperature": input_data.get("temperature", 0.7),
            "stream": stream
        }
        
        if system_message:
            payload["system"] = system_message
        
        if stream:
            return self._anthropic_stream(payload, headers)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error: {error_text}")
                
                result = await response.json()
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "output_data": {
                "response": result["content"][0]["text"],
                "usage": result.get("usage", {}),
                "model": result["model"]
            },
            "actual_cost_cc": self._calculate_cost_from_usage(
                operation.model_name, result.get("usage", {})
            ),
            "processing_time": processing_time
        }
    
    async def _anthropic_stream(self, payload: Dict, headers: Dict) -> AsyncGenerator:
        """Handle Anthropic streaming responses"""
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Anthropic API error: {error_text}")
                
                async for line in response.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            
                            try:
                                data = json.loads(data_str)
                                if data.get("type") == "content_block_delta":
                                    delta = data.get("delta", {})
                                    if "text" in delta:
                                        yield {
                                            "content": delta["text"],
                                            "type": "content"
                                        }
                            except json.JSONDecodeError:
                                continue
    
    async def _local_llm_generate(self, operation: AIOperation, stream: bool = False) -> Any:
        """Generate text using local LLM"""
        
        # This would interface with a local LLM installation (Ollama, LM Studio, etc.)
        # For now, we'll simulate the process
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        if not settings.llm.enable_local_llm:
            raise Exception("Local LLM is not enabled")
        
        # Simulate local generation
        await asyncio.sleep(2)  # Simulate processing time
        
        # Extract the last user message as a simple prompt
        user_messages = [msg for msg in input_data["messages"] if msg["role"] == "user"]
        prompt = user_messages[-1]["content"] if user_messages else ""
        
        # Simulate a response
        response = f"Local LLM response to: {prompt[:100]}..."
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        estimated_tokens = len(response.split()) * 1.3  # Rough token estimate
        
        return {
            "output_data": {
                "response": response,
                "usage": {"total_tokens": int(estimated_tokens)},
                "model": "local-llama"
            },
            "actual_cost_cc": self.model_capabilities["local-llama"]["cost_per_1k_tokens"] * 
                              (estimated_tokens / 1000),
            "processing_time": processing_time
        }
    
    async def _together_generate(self, operation: AIOperation, stream: bool = False) -> Any:
        """Generate text using Together AI"""
        
        # Similar implementation to OpenAI but with Together AI endpoints
        # For brevity, showing simplified version
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        # Simulate API call
        await asyncio.sleep(3)
        
        response = "Together AI generated response..."
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        estimated_tokens = len(response.split()) * 1.3
        
        return {
            "output_data": {
                "response": response,
                "usage": {"total_tokens": int(estimated_tokens)},
                "model": operation.model_name
            },
            "actual_cost_cc": self.model_capabilities.get(
                operation.model_name, {"cost_per_1k_tokens": Decimal("0.001")}
            )["cost_per_1k_tokens"] * (estimated_tokens / 1000),
            "processing_time": processing_time
        }
    
    async def _replicate_generate(self, operation: AIOperation, stream: bool = False) -> Any:
        """Generate text using Replicate"""
        
        # Similar implementation for Replicate API
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        await asyncio.sleep(4)  # Replicate can be slower
        
        response = "Replicate generated response..."
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        estimated_tokens = len(response.split()) * 1.3
        
        return {
            "output_data": {
                "response": response,
                "usage": {"total_tokens": int(estimated_tokens)},
                "model": operation.model_name
            },
            "actual_cost_cc": Decimal("0.002") * (estimated_tokens / 1000),
            "processing_time": processing_time
        }
    
    async def _select_optimal_model(
        self, 
        messages: List[Dict], 
        functions: Optional[List[Dict]], 
        kwargs: Dict
    ) -> str:
        """Select optimal model based on requirements"""
        
        # Calculate required context length
        total_text = " ".join([msg["content"] for msg in messages])
        required_tokens = len(total_text.split()) * 1.3  # Rough estimate
        
        # Check if functions are needed
        needs_functions = functions is not None
        
        # Check if vision is needed
        needs_vision = any(
            isinstance(msg.get("content"), list) for msg in messages
        )
        
        # Filter compatible models
        compatible_models = []
        for model, capabilities in self.model_capabilities.items():
            if required_tokens > capabilities["context_length"]:
                continue
            if needs_functions and not capabilities["supports_functions"]:
                continue
            if needs_vision and not capabilities["supports_vision"]:
                continue
            
            compatible_models.append((model, capabilities))
        
        if not compatible_models:
            raise Exception("No compatible model found for requirements")
        
        # Select cheapest compatible model
        cheapest_model = min(compatible_models, key=lambda x: x[1]["cost_per_1k_tokens"])
        return cheapest_model[0]
    
    def _estimate_token_count(self, messages: List[Dict], max_tokens: Optional[int]) -> int:
        """Estimate token count for cost calculation"""
        
        total_text = ""
        for msg in messages:
            total_text += msg.get("content", "")
        
        # Rough token estimation (GPT tokenizer would be more accurate)
        input_tokens = len(total_text.split()) * 1.3
        output_tokens = max_tokens or 1000
        
        return int(input_tokens + output_tokens)
    
    def _count_tokens(self, text: str, model: str) -> int:
        """Count actual tokens in text"""
        
        try:
            # Use tiktoken for OpenAI models
            if "gpt" in model:
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(text))
        except:
            pass
        
        # Fallback to word-based estimation
        return int(len(text.split()) * 1.3)
    
    def _calculate_actual_cost(self, model: str, token_count: int) -> Decimal:
        """Calculate actual cost based on token usage"""
        
        model_info = self.model_capabilities.get(model)
        if not model_info:
            return Decimal("0")
        
        cost_per_1k = model_info["cost_per_1k_tokens"]
        return cost_per_1k * (token_count / 1000)
    
    def _calculate_cost_from_usage(self, model: str, usage: Dict) -> Decimal:
        """Calculate cost from API usage response"""
        
        total_tokens = usage.get("total_tokens", 0)
        return self._calculate_actual_cost(model, total_tokens)
    
    def _generate_input_hash(self, input_data: Dict) -> str:
        """Generate hash for caching purposes"""
        
        # Create a deterministic hash from input parameters
        cache_data = {
            "messages": input_data.get("messages", []),
            "temperature": input_data.get("temperature", 0.7),
            "max_tokens": input_data.get("max_tokens"),
            "functions": input_data.get("functions")
        }
        
        # Remove None values
        cache_data = {k: v for k, v in cache_data.items() if v is not None}
        
        # Create hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    async def list_available_models(self) -> Dict[str, Any]:
        """List all available models with their capabilities"""
        
        return {
            "models": self.model_capabilities,
            "providers": list(set(model["provider"].value for model in self.model_capabilities.values()))
        }