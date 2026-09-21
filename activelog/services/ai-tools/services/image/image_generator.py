"""
Image Generation Service
Integrates DALL-E, Midjourney, Stable Diffusion with unified interface
"""

import asyncio
import aiohttp
import base64
import hashlib
import json
import os
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from ...models.ai_operations import AIOperation, AIOperationType, AIProvider, OperationStatus
from ...config.settings import settings, AI_OPERATION_COSTS
from ..cache.result_cache import ResultCache
from ..compute.optimizer import ComputeOptimizer
from ..cost.estimator import CostEstimator

logger = logging.getLogger(__name__)

class ImageGenerator:
    """Unified image generation service supporting multiple providers"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = ResultCache(db)
        self.optimizer = ComputeOptimizer(db)
        self.cost_estimator = CostEstimator(db)
        
        # Provider configurations
        self.providers = {
            AIProvider.OPENAI: self._dalle_generate,
            AIProvider.STABILITY_AI: self._stability_generate,
            AIProvider.MIDJOURNEY: self._midjourney_generate,
            AIProvider.LOCAL: self._local_sd_generate
        }
    
    async def generate_image(
        self,
        user_id: str,
        prompt: str,
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        resolution: str = "1024x1024",
        num_images: int = 1,
        style: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        seed: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate images with optimal provider selection"""
        
        # Create operation record
        operation = AIOperation(
            user_id=user_id,
            operation_type=AIOperationType.IMAGE_GENERATION,
            provider=provider or AIProvider.OPENAI,
            model_name=model or "auto",
            input_data={
                "prompt": prompt,
                "resolution": resolution,
                "num_images": num_images,
                "style": style,
                "negative_prompt": negative_prompt,
                "seed": seed,
                **kwargs
            }
        )
        
        # Generate input hash for caching
        input_hash = self._generate_input_hash(operation.input_data)
        operation.input_hash = input_hash
        
        self.db.add(operation)
        self.db.commit()
        
        try:
            # Check cache first
            cached_result = await self.cache.get_cached_result(
                input_hash, AIOperationType.IMAGE_GENERATION
            )
            
            if cached_result:
                operation.status = OperationStatus.COMPLETED
                operation.output_data = cached_result["output_data"]
                operation.output_files = cached_result["output_files"]
                operation.actual_cost_cc = Decimal("0")  # No cost for cached results
                operation.cost_saved_cc = cached_result.get("original_cost_cc", Decimal("0"))
                operation.completed_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "operation_id": operation.id,
                    "status": "completed",
                    "images": cached_result["output_files"],
                    "cached": True,
                    "cost_cc": 0,
                    "cost_saved_cc": float(operation.cost_saved_cc)
                }
            
            # Estimate costs and optimize provider selection
            if not provider:
                provider = await self.optimizer.select_optimal_provider(
                    AIOperationType.IMAGE_GENERATION, operation.input_data
                )
                operation.provider = provider
            
            # Estimate cost
            cost_estimate = await self.cost_estimator.estimate_image_generation_cost(
                provider, num_images, resolution
            )
            operation.estimated_cost_cc = cost_estimate["total_cost_cc"]
            
            # Check if user has sufficient credits (would integrate with ActiveLedger)
            # await self._check_user_credits(user_id, operation.estimated_cost_cc)
            
            operation.status = OperationStatus.PROCESSING
            operation.started_at = datetime.utcnow()
            self.db.commit()
            
            # Generate images using selected provider
            generator_func = self.providers.get(provider)
            if not generator_func:
                raise ValueError(f"Unsupported provider: {provider}")
            
            result = await generator_func(operation)
            
            # Store result in cache
            await self.cache.store_result(
                input_hash,
                AIOperationType.IMAGE_GENERATION,
                result["output_data"],
                result["output_files"],
                operation.estimated_cost_cc
            )
            
            # Update operation with results
            operation.status = OperationStatus.COMPLETED
            operation.output_data = result["output_data"]
            operation.output_files = result["output_files"]
            operation.actual_cost_cc = result["actual_cost_cc"]
            operation.processing_time_seconds = result.get("processing_time", 0)
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "operation_id": operation.id,
                "status": "completed",
                "images": result["output_files"],
                "cached": False,
                "cost_cc": float(operation.actual_cost_cc),
                "processing_time": float(operation.processing_time_seconds),
                "provider": provider.value
            }
            
        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Image generation failed for operation {operation.id}: {str(e)}")
            raise
    
    async def _dalle_generate(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate images using OpenAI DALL-E"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {settings.image_generation.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": settings.image_generation.dalle_model,
            "prompt": input_data["prompt"],
            "n": input_data["num_images"],
            "size": input_data["resolution"],
            "response_format": "url"
        }
        
        # Add optional parameters
        if input_data.get("style"):
            payload["style"] = input_data["style"]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"DALL-E API error: {error_text}")
                
                result = await response.json()
        
        # Download and store images
        image_files = []
        for i, image_data in enumerate(result["data"]):
            image_url = image_data["url"]
            filename = f"dalle_{operation.id}_{i}.png"
            local_path = await self._download_and_store_image(image_url, filename)
            image_files.append({
                "url": image_url,
                "local_path": local_path,
                "filename": filename
            })
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        actual_cost = settings.image_generation.dalle_cost_per_image * input_data["num_images"]
        
        return {
            "output_data": {
                "model": settings.image_generation.dalle_model,
                "resolution": input_data["resolution"],
                "num_images": len(image_files)
            },
            "output_files": image_files,
            "actual_cost_cc": actual_cost / settings.ai_tools.cost_estimation.min_operation_cost,  # Convert to CC
            "processing_time": processing_time
        }
    
    async def _stability_generate(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate images using Stability AI"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {settings.image_generation.stability_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "text_prompts": [
                {
                    "text": input_data["prompt"],
                    "weight": 1.0
                }
            ],
            "cfg_scale": 7,
            "height": int(input_data["resolution"].split("x")[1]),
            "width": int(input_data["resolution"].split("x")[0]),
            "samples": input_data["num_images"],
            "steps": 50
        }
        
        # Add negative prompt if provided
        if input_data.get("negative_prompt"):
            payload["text_prompts"].append({
                "text": input_data["negative_prompt"],
                "weight": -1.0
            })
        
        # Add seed if provided
        if input_data.get("seed"):
            payload["seed"] = input_data["seed"]
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://api.stability.ai/v1/generation/{settings.image_generation.stability_engine}/text-to-image",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Stability AI error: {error_text}")
                
                result = await response.json()
        
        # Process base64 images
        image_files = []
        for i, artifact in enumerate(result["artifacts"]):
            if artifact["finishReason"] == "SUCCESS":
                image_data = base64.b64decode(artifact["base64"])
                filename = f"stability_{operation.id}_{i}.png"
                local_path = await self._store_image_data(image_data, filename)
                image_files.append({
                    "local_path": local_path,
                    "filename": filename,
                    "seed": artifact.get("seed")
                })
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        actual_cost = settings.image_generation.stability_cost_per_image * len(image_files)
        
        return {
            "output_data": {
                "model": settings.image_generation.stability_engine,
                "resolution": input_data["resolution"],
                "num_images": len(image_files)
            },
            "output_files": image_files,
            "actual_cost_cc": actual_cost / settings.ai_tools.cost_estimation.min_operation_cost,
            "processing_time": processing_time
        }
    
    async def _midjourney_generate(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate images using Midjourney (via Discord bot)"""
        
        # This would require a Discord bot integration
        # For now, we'll simulate the response
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        # Simulate processing time
        await asyncio.sleep(30)  # Midjourney typically takes 30-60 seconds
        
        # Simulate generated images
        image_files = []
        for i in range(input_data["num_images"]):
            filename = f"midjourney_{operation.id}_{i}.png"
            # In reality, you'd get the image from Discord and download it
            image_files.append({
                "filename": filename,
                "local_path": f"/images/{filename}",
                "midjourney_id": f"mj_{operation.id}_{i}"
            })
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        actual_cost = settings.image_generation.midjourney_cost_per_image * len(image_files)
        
        return {
            "output_data": {
                "model": "midjourney",
                "resolution": input_data["resolution"],
                "num_images": len(image_files)
            },
            "output_files": image_files,
            "actual_cost_cc": actual_cost / settings.ai_tools.cost_estimation.min_operation_cost,
            "processing_time": processing_time
        }
    
    async def _local_sd_generate(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate images using local Stable Diffusion"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        # This would interface with a local Stable Diffusion installation
        # For now, we'll simulate the process
        
        if not settings.image_generation.enable_local_sd:
            raise Exception("Local Stable Diffusion is not enabled")
        
        # Simulate local generation (much faster but requires GPU)
        await asyncio.sleep(5)  # Local generation is much faster
        
        image_files = []
        for i in range(input_data["num_images"]):
            filename = f"local_sd_{operation.id}_{i}.png"
            image_files.append({
                "filename": filename,
                "local_path": f"/images/{filename}",
                "model": "stable-diffusion-xl"
            })
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        actual_cost = settings.image_generation.local_sd_cost_per_image * len(image_files)
        
        return {
            "output_data": {
                "model": "stable-diffusion-xl-local",
                "resolution": input_data["resolution"],
                "num_images": len(image_files)
            },
            "output_files": image_files,
            "actual_cost_cc": actual_cost / settings.ai_tools.cost_estimation.min_operation_cost,
            "processing_time": processing_time
        }
    
    async def _download_and_store_image(self, url: str, filename: str) -> str:
        """Download image from URL and store locally"""
        
        storage_dir = "/tmp/ai_images"  # Should be configurable
        os.makedirs(storage_dir, exist_ok=True)
        
        local_path = os.path.join(storage_dir, filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    with open(local_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
        
        return local_path
    
    async def _store_image_data(self, image_data: bytes, filename: str) -> str:
        """Store image data to local file"""
        
        storage_dir = "/tmp/ai_images"
        os.makedirs(storage_dir, exist_ok=True)
        
        local_path = os.path.join(storage_dir, filename)
        
        with open(local_path, 'wb') as f:
            f.write(image_data)
        
        return local_path
    
    def _generate_input_hash(self, input_data: Dict) -> str:
        """Generate hash for caching purposes"""
        
        # Create a deterministic hash from input parameters
        cache_data = {
            "prompt": input_data.get("prompt", ""),
            "resolution": input_data.get("resolution", "1024x1024"),
            "style": input_data.get("style"),
            "negative_prompt": input_data.get("negative_prompt"),
            "seed": input_data.get("seed")
        }
        
        # Remove None values
        cache_data = {k: v for k, v in cache_data.items() if v is not None}
        
        # Create hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    async def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of an image generation operation"""
        
        operation = self.db.query(AIOperation).filter(AIOperation.id == operation_id).first()
        if not operation:
            raise ValueError(f"Operation {operation_id} not found")
        
        result = {
            "operation_id": operation_id,
            "status": operation.status.value,
            "operation_type": operation.operation_type.value,
            "provider": operation.provider.value,
            "created_at": operation.created_at.isoformat(),
            "estimated_cost_cc": float(operation.estimated_cost_cc or 0),
            "actual_cost_cc": float(operation.actual_cost_cc or 0)
        }
        
        if operation.started_at:
            result["started_at"] = operation.started_at.isoformat()
        
        if operation.completed_at:
            result["completed_at"] = operation.completed_at.isoformat()
            result["processing_time_seconds"] = float(operation.processing_time_seconds or 0)
        
        if operation.output_files:
            result["images"] = operation.output_files
        
        if operation.error_message:
            result["error"] = operation.error_message
        
        return result
    
    async def list_supported_models(self) -> Dict[str, List[str]]:
        """List all supported models by provider"""
        
        return {
            "openai": ["dall-e-3", "dall-e-2"],
            "stability_ai": [
                "stable-diffusion-xl-1024-v1-0",
                "stable-diffusion-v1-6",
                "stable-diffusion-512-v2-1"
            ],
            "midjourney": ["midjourney-v6", "midjourney-v5.2"],
            "local": ["stable-diffusion-xl", "stable-diffusion-1.5"]
        }