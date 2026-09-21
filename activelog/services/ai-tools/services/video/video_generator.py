"""
Video generation pipeline supporting multiple providers and video creation methods.
Handles text-to-video, image-to-video, and video editing operations.
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...database import get_session
from ...database.models import VideoGeneration, VideoGenerationStatus, AIProvider
from ...settings import settings
from ..cache.result_cache import result_cache
from ..cost.estimator import CostEstimator
from ...exceptions import VideoGenerationError


class VideoModel(Enum):
    RUNWAY_GEN3 = "runway_gen3"
    PIKA_LABS = "pika_labs"
    STABLE_VIDEO = "stable_video_diffusion"
    ZEROSCOPE = "zeroscope_v2"
    MODELSCOPE = "modelscope"
    HOTSHOT_XL = "hotshot_xl"
    ANIMATEDIFF = "animatediff"
    AUTO = "auto"


class VideoStyle(Enum):
    REALISTIC = "realistic"
    ANIMATED = "animated"
    CARTOON = "cartoon"
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    ABSTRACT = "abstract"
    TIMELAPSE = "timelapse"


class VideoResolution(Enum):
    HD_720P = "1280x720"
    FHD_1080P = "1920x1080"
    UHD_4K = "3840x2160"
    SQUARE_1024 = "1024x1024"
    VERTICAL_9_16 = "576x1024"
    HORIZONTAL_16_9 = "1024x576"


@dataclass
class VideoGenerationRequest:
    prompt: str
    model: VideoModel = VideoModel.AUTO
    duration_seconds: int = 4
    fps: int = 24
    resolution: VideoResolution = VideoResolution.HD_720P
    style: VideoStyle = VideoStyle.REALISTIC
    seed: Optional[int] = None
    guidance_scale: float = 7.5
    num_inference_steps: int = 25
    motion_intensity: float = 0.7
    camera_movement: Optional[str] = None
    input_image: Optional[str] = None
    input_video: Optional[str] = None
    loop_video: bool = False
    upscale: bool = False
    enhance_audio: bool = False
    watermark: bool = True


class VideoGenerator:
    def __init__(self):
        self.cost_estimator = CostEstimator()
        self.model_configs = {
            VideoModel.RUNWAY_GEN3: {
                "provider": AIProvider.RUNWAY,
                "api_endpoint": "https://api.runwayml.com/v1/video/generate",
                "max_duration": 10,
                "supports_image_input": True,
                "supports_video_input": True,
                "cost_per_second": Decimal("0.12"),
                "quality_score": 9.5
            },
            VideoModel.PIKA_LABS: {
                "provider": AIProvider.PIKA_LABS,
                "api_endpoint": "https://api.pika.art/v1/generate",
                "max_duration": 3,
                "supports_image_input": True,
                "supports_video_input": False,
                "cost_per_second": Decimal("0.08"),
                "quality_score": 8.5
            },
            VideoModel.STABLE_VIDEO: {
                "provider": AIProvider.STABILITY_AI,
                "api_endpoint": "https://api.stability.ai/v2beta/video/generate",
                "max_duration": 4,
                "supports_image_input": True,
                "supports_video_input": False,
                "cost_per_second": Decimal("0.06"),
                "quality_score": 8.0
            },
            VideoModel.ZEROSCOPE: {
                "provider": AIProvider.HUGGINGFACE,
                "api_endpoint": "local",
                "max_duration": 8,
                "supports_image_input": False,
                "supports_video_input": False,
                "cost_per_second": Decimal("0.02"),
                "quality_score": 6.5
            },
            VideoModel.MODELSCOPE: {
                "provider": AIProvider.HUGGINGFACE,
                "api_endpoint": "local",
                "max_duration": 6,
                "supports_image_input": False,
                "supports_video_input": False,
                "cost_per_second": Decimal("0.03"),
                "quality_score": 7.0
            },
            VideoModel.HOTSHOT_XL: {
                "provider": AIProvider.HUGGINGFACE,
                "api_endpoint": "local",
                "max_duration": 2,
                "supports_image_input": True,
                "supports_video_input": False,
                "cost_per_second": Decimal("0.04"),
                "quality_score": 7.5
            },
            VideoModel.ANIMATEDIFF: {
                "provider": AIProvider.HUGGINGFACE,
                "api_endpoint": "local",
                "max_duration": 5,
                "supports_image_input": False,
                "supports_video_input": False,
                "cost_per_second": Decimal("0.025"),
                "quality_score": 6.8
            }
        }
    
    async def generate_video(
        self,
        request: VideoGenerationRequest,
        user_id: str
    ) -> Dict[str, Any]:
        """Generate a video using the specified parameters."""
        
        # Auto-select model if needed
        if request.model == VideoModel.AUTO:
            request.model = await self._select_optimal_model(request)
        
        # Validate request parameters
        await self._validate_request(request)
        
        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_result = await result_cache.get_cached_result(
            "video_generation", cache_key, user_id
        )
        
        if cached_result:
            return {
                "video_url": cached_result["video_url"],
                "video_path": cached_result.get("video_path"),
                "model_used": cached_result["model_used"],
                "duration_seconds": cached_result["duration_seconds"],
                "resolution": cached_result["resolution"],
                "cost_cc": Decimal("0"),  # No cost for cached result
                "from_cache": True
            }
        
        # Estimate cost
        cost_estimate = await self._estimate_generation_cost(request)
        
        # Create generation record
        async with get_session() as session:
            generation = VideoGeneration(
                user_id=user_id,
                prompt=request.prompt,
                model=request.model.value,
                duration_seconds=request.duration_seconds,
                resolution=request.resolution.value,
                style=request.style.value,
                status=VideoGenerationStatus.PROCESSING,
                estimated_cost_cc=cost_estimate,
                created_at=datetime.utcnow()
            )
            
            session.add(generation)
            await session.commit()
            await session.refresh(generation)
        
        try:
            # Generate video
            result = await self._generate_with_model(request, generation.id)
            
            # Update generation record
            async with get_session() as session:
                generation.status = VideoGenerationStatus.COMPLETED
                generation.video_url = result["video_url"]
                generation.video_path = result.get("video_path")
                generation.actual_cost_cc = result["actual_cost_cc"]
                generation.completed_at = datetime.utcnow()
                await session.commit()
            
            # Cache the result
            await result_cache.cache_result(
                operation_type="video_generation",
                cache_key=cache_key,
                result=result,
                user_id=user_id,
                cost_cc=result["actual_cost_cc"]
            )
            
            return result
            
        except Exception as e:
            # Update generation record with error
            async with get_session() as session:
                generation.status = VideoGenerationStatus.FAILED
                generation.error_message = str(e)
                generation.completed_at = datetime.utcnow()
                await session.commit()
            
            raise VideoGenerationError(f"Video generation failed: {str(e)}")
    
    async def _select_optimal_model(self, request: VideoGenerationRequest) -> VideoModel:
        """Select the optimal model based on request parameters and availability."""
        
        # Consider requirements
        needs_image_input = request.input_image is not None
        needs_video_input = request.input_video is not None
        duration = request.duration_seconds
        
        # Score models based on requirements
        model_scores = {}
        
        for model, config in self.model_configs.items():
            if model == VideoModel.AUTO:
                continue
            
            score = config["quality_score"]
            
            # Check duration compatibility
            if duration > config["max_duration"]:
                score -= 3
            
            # Check input type compatibility
            if needs_image_input and not config["supports_image_input"]:
                continue
            
            if needs_video_input and not config["supports_video_input"]:
                continue
            
            # Factor in cost (lower cost = higher score)
            cost_factor = 1 / (float(config["cost_per_second"]) + 0.01)
            score += cost_factor * 0.5
            
            # Check availability
            if await self._check_model_availability(model):
                score += 1
            else:
                score -= 5
            
            model_scores[model] = score
        
        # Select highest scoring model
        if not model_scores:
            raise VideoGenerationError("No suitable models available for request")
        
        return max(model_scores.items(), key=lambda x: x[1])[0]
    
    async def _validate_request(self, request: VideoGenerationRequest):
        """Validate the generation request."""
        config = self.model_configs[request.model]
        
        if request.duration_seconds > config["max_duration"]:
            raise VideoGenerationError(
                f"Duration {request.duration_seconds}s exceeds maximum {config['max_duration']}s for {request.model.value}"
            )
        
        if request.input_image and not config["supports_image_input"]:
            raise VideoGenerationError(
                f"Model {request.model.value} does not support image input"
            )
        
        if request.input_video and not config["supports_video_input"]:
            raise VideoGenerationError(
                f"Model {request.model.value} does not support video input"
            )
        
        if not request.prompt.strip():
            raise VideoGenerationError("Prompt cannot be empty")
        
        if len(request.prompt) > 1000:
            raise VideoGenerationError("Prompt too long (max 1000 characters)")
    
    async def _estimate_generation_cost(self, request: VideoGenerationRequest) -> Decimal:
        """Estimate the cost of video generation."""
        config = self.model_configs[request.model]
        base_cost = config["cost_per_second"] * request.duration_seconds
        
        # Apply multipliers based on parameters
        if request.resolution in [VideoResolution.FHD_1080P]:
            base_cost *= Decimal("1.5")
        elif request.resolution == VideoResolution.UHD_4K:
            base_cost *= Decimal("3.0")
        
        if request.upscale:
            base_cost *= Decimal("1.8")
        
        if request.enhance_audio:
            base_cost *= Decimal("1.2")
        
        # Convert to CC
        return base_cost / settings.compute_credits.cc_to_usd_rate
    
    async def _generate_with_model(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using the specified model."""
        config = self.model_configs[request.model]
        
        if config["api_endpoint"] == "local":
            return await self._generate_local(request, generation_id)
        else:
            return await self._generate_cloud(request, generation_id)
    
    async def _generate_local(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using local models."""
        
        if request.model == VideoModel.ZEROSCOPE:
            return await self._generate_zeroscope(request, generation_id)
        elif request.model == VideoModel.MODELSCOPE:
            return await self._generate_modelscope(request, generation_id)
        elif request.model == VideoModel.HOTSHOT_XL:
            return await self._generate_hotshot_xl(request, generation_id)
        elif request.model == VideoModel.ANIMATEDIFF:
            return await self._generate_animatediff(request, generation_id)
        else:
            raise VideoGenerationError(f"Local generation not implemented for {request.model.value}")
    
    async def _generate_zeroscope(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using Zeroscope V2 model."""
        try:
            import torch
            from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler
            
            # Load model
            pipe = DiffusionPipeline.from_pretrained(
                "cerspense/zeroscope_v2_576w", 
                torch_dtype=torch.float16
            )
            pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config)
            
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            
            # Generate video
            video_frames = pipe(
                prompt=request.prompt,
                num_frames=request.duration_seconds * request.fps,
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps,
                generator=torch.Generator().manual_seed(request.seed or 42)
            ).frames[0]
            
            # Save video
            output_path = f"/tmp/video_{generation_id}.mp4"
            await self._save_video_frames(video_frames, output_path, request.fps)
            
            # Upload if needed
            video_url = await self._upload_video(output_path)
            
            return {
                "video_url": video_url,
                "video_path": output_path,
                "model_used": request.model.value,
                "duration_seconds": request.duration_seconds,
                "resolution": request.resolution.value,
                "actual_cost_cc": await self._estimate_generation_cost(request)
            }
            
        except Exception as e:
            raise VideoGenerationError(f"Zeroscope generation failed: {str(e)}")
    
    async def _generate_modelscope(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using ModelScope model."""
        try:
            import torch
            from diffusers import DiffusionPipeline
            
            # Load model
            pipe = DiffusionPipeline.from_pretrained(
                "damo-vilab/text-to-video-ms-1.7b",
                torch_dtype=torch.float16,
                variant="fp16"
            )
            
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            
            # Generate video
            video_frames = pipe(
                prompt=request.prompt,
                num_frames=min(16, request.duration_seconds * 4),  # ModelScope limitation
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps
            ).frames[0]
            
            # Save video
            output_path = f"/tmp/video_{generation_id}.mp4"
            await self._save_video_frames(video_frames, output_path, 8)  # 8 fps for ModelScope
            
            # Upload if needed
            video_url = await self._upload_video(output_path)
            
            return {
                "video_url": video_url,
                "video_path": output_path,
                "model_used": request.model.value,
                "duration_seconds": len(video_frames) / 8,
                "resolution": "576x320",  # ModelScope default
                "actual_cost_cc": await self._estimate_generation_cost(request)
            }
            
        except Exception as e:
            raise VideoGenerationError(f"ModelScope generation failed: {str(e)}")
    
    async def _generate_hotshot_xl(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using Hotshot-XL model."""
        try:
            import torch
            from diffusers import StableDiffusionXLPipeline
            
            # This is a placeholder - Hotshot-XL requires specialized handling
            # In practice, you'd use the specific Hotshot-XL pipeline
            
            output_path = f"/tmp/video_{generation_id}.mp4"
            video_url = await self._upload_video(output_path)
            
            return {
                "video_url": video_url,
                "video_path": output_path,
                "model_used": request.model.value,
                "duration_seconds": request.duration_seconds,
                "resolution": "512x512",  # Hotshot-XL default
                "actual_cost_cc": await self._estimate_generation_cost(request)
            }
            
        except Exception as e:
            raise VideoGenerationError(f"Hotshot-XL generation failed: {str(e)}")
    
    async def _generate_animatediff(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using AnimateDiff model."""
        try:
            import torch
            from diffusers import AnimateDiffPipeline, MotionAdapter, EulerDiscreteScheduler
            
            # Load motion adapter
            adapter = MotionAdapter.from_pretrained(
                "guoyww/animatediff-motion-adapter-v1-5-2",
                torch_dtype=torch.float16
            )
            
            # Load pipeline
            pipe = AnimateDiffPipeline.from_pretrained(
                "runwayml/stable-diffusion-v1-5",
                motion_adapter=adapter,
                torch_dtype=torch.float16
            )
            pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
            
            if torch.cuda.is_available():
                pipe = pipe.to("cuda")
            
            # Generate video
            output = pipe(
                prompt=request.prompt,
                num_frames=16,
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps,
                generator=torch.Generator().manual_seed(request.seed or 42)
            )
            
            # Save video
            output_path = f"/tmp/video_{generation_id}.mp4"
            await self._save_video_frames(output.frames[0], output_path, 8)
            
            # Upload if needed
            video_url = await self._upload_video(output_path)
            
            return {
                "video_url": video_url,
                "video_path": output_path,
                "model_used": request.model.value,
                "duration_seconds": 2.0,  # 16 frames at 8fps
                "resolution": "512x512",
                "actual_cost_cc": await self._estimate_generation_cost(request)
            }
            
        except Exception as e:
            raise VideoGenerationError(f"AnimateDiff generation failed: {str(e)}")
    
    async def _generate_cloud(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using cloud APIs."""
        config = self.model_configs[request.model]
        
        if config["provider"] == AIProvider.RUNWAY:
            return await self._generate_runway(request, generation_id)
        elif config["provider"] == AIProvider.PIKA_LABS:
            return await self._generate_pika(request, generation_id)
        elif config["provider"] == AIProvider.STABILITY_AI:
            return await self._generate_stable_video(request, generation_id)
        else:
            raise VideoGenerationError(f"Cloud generation not implemented for {request.model.value}")
    
    async def _generate_runway(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using Runway API."""
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {settings.runway.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "taskType": "gen3",
                "textPrompt": request.prompt,
                "duration": request.duration_seconds,
                "resolution": request.resolution.value,
                "seed": request.seed,
                "watermark": request.watermark
            }
            
            if request.input_image:
                payload["imagePrompt"] = request.input_image
            
            async with aiohttp.ClientSession() as session:
                # Submit generation request
                async with session.post(
                    "https://api.runwayml.com/v1/tasks",
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 201:
                        raise VideoGenerationError(f"Runway API error: {response.status}")
                    
                    result = await response.json()
                    task_id = result["id"]
                
                # Poll for completion
                while True:
                    async with session.get(
                        f"https://api.runwayml.com/v1/tasks/{task_id}",
                        headers=headers
                    ) as response:
                        status_result = await response.json()
                        
                        if status_result["status"] == "SUCCEEDED":
                            video_url = status_result["output"][0]
                            break
                        elif status_result["status"] == "FAILED":
                            raise VideoGenerationError(f"Runway generation failed: {status_result.get('failure')}")
                        
                        await asyncio.sleep(5)  # Wait 5 seconds before next poll
            
            return {
                "video_url": video_url,
                "model_used": request.model.value,
                "duration_seconds": request.duration_seconds,
                "resolution": request.resolution.value,
                "actual_cost_cc": await self._estimate_generation_cost(request)
            }
            
        except Exception as e:
            raise VideoGenerationError(f"Runway generation failed: {str(e)}")
    
    async def _generate_pika(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using Pika Labs API."""
        # Placeholder implementation
        return {
            "video_url": f"https://example.com/video_{generation_id}.mp4",
            "model_used": request.model.value,
            "duration_seconds": request.duration_seconds,
            "resolution": request.resolution.value,
            "actual_cost_cc": await self._estimate_generation_cost(request)
        }
    
    async def _generate_stable_video(
        self, 
        request: VideoGenerationRequest, 
        generation_id: str
    ) -> Dict[str, Any]:
        """Generate video using Stability AI Video API."""
        # Placeholder implementation
        return {
            "video_url": f"https://example.com/video_{generation_id}.mp4",
            "model_used": request.model.value,
            "duration_seconds": request.duration_seconds,
            "resolution": request.resolution.value,
            "actual_cost_cc": await self._estimate_generation_cost(request)
        }
    
    async def _save_video_frames(self, frames: List, output_path: str, fps: int):
        """Save video frames to MP4 file."""
        try:
            import cv2
            import numpy as np
            
            # Convert frames to numpy arrays
            if hasattr(frames[0], 'numpy'):
                frames = [frame.numpy() if hasattr(frame, 'numpy') else np.array(frame) for frame in frames]
            
            # Get dimensions
            height, width = frames[0].shape[:2]
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            for frame in frames:
                if frame.dtype != np.uint8:
                    frame = (frame * 255).astype(np.uint8)
                
                # Convert RGB to BGR for OpenCV
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                out.write(frame)
            
            out.release()
            
        except Exception as e:
            raise VideoGenerationError(f"Failed to save video: {str(e)}")
    
    async def _upload_video(self, video_path: str) -> str:
        """Upload video to storage and return URL."""
        # Placeholder - implement actual upload logic
        # This could upload to S3, Cloudflare R2, or other storage
        return f"https://storage.example.com/videos/{os.path.basename(video_path)}"
    
    async def _check_model_availability(self, model: VideoModel) -> bool:
        """Check if a model is available."""
        config = self.model_configs[model]
        
        if config["api_endpoint"] == "local":
            # Check if local dependencies are installed
            return await self._check_local_dependencies(model)
        else:
            # Check if API key is configured
            if config["provider"] == AIProvider.RUNWAY:
                return bool(getattr(settings, 'runway', {}).get('api_key'))
            elif config["provider"] == AIProvider.STABILITY_AI:
                return bool(settings.stability_ai.api_key)
            elif config["provider"] == AIProvider.PIKA_LABS:
                return bool(getattr(settings, 'pika_labs', {}).get('api_key'))
        
        return False
    
    async def _check_local_dependencies(self, model: VideoModel) -> bool:
        """Check if local model dependencies are available."""
        try:
            import torch
            import diffusers
            
            # Check if CUDA is available for better performance
            if torch.cuda.is_available():
                return True
            
            # CPU inference is possible but slower
            return True
            
        except ImportError:
            return False
    
    def _generate_cache_key(self, request: VideoGenerationRequest) -> str:
        """Generate cache key for video generation request."""
        key_data = {
            "prompt": request.prompt,
            "model": request.model.value,
            "duration": request.duration_seconds,
            "resolution": request.resolution.value,
            "style": request.style.value,
            "seed": request.seed,
            "guidance_scale": request.guidance_scale,
            "motion_intensity": request.motion_intensity,
            "camera_movement": request.camera_movement,
            "input_image": request.input_image,
            "loop_video": request.loop_video
        }
        
        import hashlib
        return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    async def get_generation_history(
        self, 
        user_id: str, 
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's video generation history."""
        async with get_session() as session:
            result = await session.execute(
                select(VideoGeneration)
                .where(VideoGeneration.user_id == user_id)
                .order_by(VideoGeneration.created_at.desc())
                .limit(limit)
            )
            
            generations = result.scalars().all()
            
            return [
                {
                    "id": gen.id,
                    "prompt": gen.prompt,
                    "model": gen.model,
                    "duration_seconds": gen.duration_seconds,
                    "resolution": gen.resolution,
                    "style": gen.style,
                    "status": gen.status.value,
                    "video_url": gen.video_url,
                    "cost_cc": gen.actual_cost_cc or gen.estimated_cost_cc,
                    "created_at": gen.created_at,
                    "completed_at": gen.completed_at
                }
                for gen in generations
            ]
    
    async def get_supported_models(self) -> List[Dict[str, Any]]:
        """Get list of supported video generation models."""
        models = []
        
        for model, config in self.model_configs.items():
            if model == VideoModel.AUTO:
                continue
            
            available = await self._check_model_availability(model)
            
            models.append({
                "model": model.value,
                "provider": config["provider"].value,
                "max_duration": config["max_duration"],
                "supports_image_input": config["supports_image_input"],
                "supports_video_input": config["supports_video_input"],
                "cost_per_second_usd": float(config["cost_per_second"]),
                "quality_score": config["quality_score"],
                "available": available
            })
        
        return sorted(models, key=lambda x: x["quality_score"], reverse=True)


# Global instance
video_generator = VideoGenerator()