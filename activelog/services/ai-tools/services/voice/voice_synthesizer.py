"""
Voice Synthesis and Cloning Service
Integrates ElevenLabs, OpenAI TTS, and local voice synthesis
"""

import asyncio
import aiohttp
import aiofiles
import base64
import hashlib
import json
import os
from decimal import Decimal
from typing import Dict, List, Optional, Any, BinaryIO
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from ...models.ai_operations import AIOperation, AIOperationType, AIProvider, OperationStatus
from ...config.settings import settings, AI_OPERATION_COSTS
from ..cache.result_cache import ResultCache
from ..compute.optimizer import ComputeOptimizer
from ..cost.estimator import CostEstimator

logger = logging.getLogger(__name__)

class VoiceSynthesizer:
    """Unified voice synthesis and cloning service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cache = ResultCache(db)
        self.optimizer = ComputeOptimizer(db)
        self.cost_estimator = CostEstimator(db)
        
        # Provider configurations
        self.providers = {
            AIProvider.OPENAI: self._openai_tts,
            AIProvider.LOCAL: self._local_tts,
            # ElevenLabs would be a custom provider enum
        }
        
        # Voice models and configurations
        self.voice_models = {
            "elevenlabs": {
                "rachel": {"voice_id": "21m00Tcm4TlvDq8ikWAM", "gender": "female", "accent": "american"},
                "domi": {"voice_id": "AZnzlk1XvdvUeBnXmlld", "gender": "female", "accent": "american"},
                "bella": {"voice_id": "EXAVITQu4vr4xnSDxMaL", "gender": "female", "accent": "american"},
                "antoni": {"voice_id": "ErXwobaYiN019PkySvjV", "gender": "male", "accent": "american"},
                "elli": {"voice_id": "MF3mGyEYCl7XYWbV9V6O", "gender": "female", "accent": "american"}
            },
            "openai": {
                "alloy": {"gender": "neutral", "style": "neutral"},
                "echo": {"gender": "male", "style": "neutral"},
                "fable": {"gender": "neutral", "style": "expressive"},
                "onyx": {"gender": "male", "style": "deep"},
                "nova": {"gender": "female", "style": "warm"},
                "shimmer": {"gender": "female", "style": "bright"}
            },
            "local": {
                "tortoise-v2": {"quality": "high", "speed": "slow"},
                "bark": {"quality": "medium", "speed": "medium"},
                "coqui-tts": {"quality": "medium", "speed": "fast"}
            }
        }
    
    async def synthesize_speech(
        self,
        user_id: str,
        text: str,
        voice: str = "alloy",
        provider: Optional[AIProvider] = None,
        model: Optional[str] = None,
        speed: float = 1.0,
        output_format: str = "mp3",
        **kwargs
    ) -> Dict[str, Any]:
        """Synthesize speech from text"""
        
        # Auto-select provider if not specified
        if not provider:
            provider = await self._select_optimal_provider(text, voice, kwargs)
        
        # Create operation record
        operation = AIOperation(
            user_id=user_id,
            operation_type=AIOperationType.VOICE_SYNTHESIS,
            provider=provider,
            model_name=model or voice,
            input_data={
                "text": text,
                "voice": voice,
                "speed": speed,
                "output_format": output_format,
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
                input_hash, AIOperationType.VOICE_SYNTHESIS
            )
            
            if cached_result:
                operation.status = OperationStatus.COMPLETED
                operation.output_data = cached_result["output_data"]
                operation.output_files = cached_result["output_files"]
                operation.actual_cost_cc = Decimal("0")
                operation.cost_saved_cc = cached_result.get("original_cost_cc", Decimal("0"))
                operation.completed_at = datetime.utcnow()
                self.db.commit()
                
                return {
                    "operation_id": operation.id,
                    "status": "completed",
                    "audio_file": cached_result["output_files"][0],
                    "cached": True,
                    "cost_cc": 0,
                    "cost_saved_cc": float(operation.cost_saved_cc)
                }
            
            # Estimate cost
            character_count = len(text)
            cost_estimate = await self.cost_estimator.estimate_voice_synthesis_cost(
                provider, character_count
            )
            operation.estimated_cost_cc = cost_estimate["total_cost_cc"]
            
            operation.status = OperationStatus.PROCESSING
            operation.started_at = datetime.utcnow()
            self.db.commit()
            
            # Synthesize speech using selected provider
            generator_func = self.providers.get(provider)
            if not generator_func:
                # Handle ElevenLabs separately
                if provider.value == "elevenlabs":
                    result = await self._elevenlabs_tts(operation)
                else:
                    raise ValueError(f"Unsupported provider: {provider}")
            else:
                result = await generator_func(operation)
            
            # Store result in cache
            await self.cache.store_result(
                input_hash,
                AIOperationType.VOICE_SYNTHESIS,
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
                "audio_file": result["output_files"][0],
                "cached": False,
                "cost_cc": float(operation.actual_cost_cc),
                "processing_time": float(operation.processing_time_seconds),
                "provider": provider.value,
                "duration_seconds": result["output_data"].get("duration_seconds", 0)
            }
            
        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Voice synthesis failed for operation {operation.id}: {str(e)}")
            raise
    
    async def clone_voice(
        self,
        user_id: str,
        audio_file_path: str,
        voice_name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Clone a voice from audio sample"""
        
        if not settings.voice.enable_voice_cloning:
            raise Exception("Voice cloning is not enabled")
        
        # Validate audio file
        audio_duration = await self._get_audio_duration(audio_file_path)
        if audio_duration < settings.voice.min_audio_duration_seconds:
            raise ValueError(f"Audio must be at least {settings.voice.min_audio_duration_seconds} seconds")
        
        if audio_duration > settings.voice.max_audio_duration_seconds:
            raise ValueError(f"Audio must be no more than {settings.voice.max_audio_duration_seconds} seconds")
        
        # Create operation record
        operation = AIOperation(
            user_id=user_id,
            operation_type=AIOperationType.VOICE_CLONING,
            provider=AIProvider.LOCAL,  # Voice cloning typically done locally for privacy
            model_name="voice_cloner",
            input_data={
                "audio_file_path": audio_file_path,
                "voice_name": voice_name,
                "description": description,
                "duration_seconds": audio_duration
            }
        )
        
        self.db.add(operation)
        self.db.commit()
        
        try:
            operation.status = OperationStatus.PROCESSING
            operation.started_at = datetime.utcnow()
            self.db.commit()
            
            # Process voice cloning
            result = await self._process_voice_cloning(operation)
            
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
                "voice_id": result["output_data"]["voice_id"],
                "voice_name": voice_name,
                "model_files": result["output_files"],
                "cost_cc": float(operation.actual_cost_cc),
                "processing_time": float(operation.processing_time_seconds)
            }
            
        except Exception as e:
            operation.status = OperationStatus.FAILED
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Voice cloning failed for operation {operation.id}: {str(e)}")
            raise
    
    async def _openai_tts(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate speech using OpenAI TTS"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        headers = {
            "Authorization": f"Bearer {settings.llm.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "tts-1",
            "input": input_data["text"],
            "voice": input_data["voice"],
            "response_format": input_data.get("output_format", "mp3"),
            "speed": input_data.get("speed", 1.0)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/speech",
                headers=headers,
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI TTS API error: {error_text}")
                
                audio_data = await response.read()
        
        # Store audio file
        filename = f"openai_tts_{operation.id}.{input_data.get('output_format', 'mp3')}"
        audio_path = await self._store_audio_data(audio_data, filename)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        character_count = len(input_data["text"])
        actual_cost = settings.voice.openai_tts_cost_per_character * character_count
        
        # Estimate duration (rough calculation)
        estimated_duration = len(input_data["text"].split()) * 0.6  # ~0.6 seconds per word
        
        return {
            "output_data": {
                "voice": input_data["voice"],
                "character_count": character_count,
                "duration_seconds": estimated_duration,
                "format": input_data.get("output_format", "mp3")
            },
            "output_files": [{
                "filename": filename,
                "local_path": audio_path,
                "format": input_data.get("output_format", "mp3"),
                "size_bytes": len(audio_data)
            }],
            "actual_cost_cc": actual_cost / settings.voice.openai_tts_cost_per_character,  # Convert to CC
            "processing_time": processing_time
        }
    
    async def _elevenlabs_tts(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate speech using ElevenLabs"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        # Get voice configuration
        voice = input_data["voice"]
        voice_config = self.voice_models["elevenlabs"].get(voice)
        if not voice_config:
            raise ValueError(f"Unknown ElevenLabs voice: {voice}")
        
        headers = {
            "xi-api-key": settings.voice.elevenlabs_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": input_data["text"],
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        voice_id = voice_config["voice_id"]
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"ElevenLabs API error: {error_text}")
                
                audio_data = await response.read()
        
        # Store audio file
        filename = f"elevenlabs_{operation.id}.mp3"
        audio_path = await self._store_audio_data(audio_data, filename)
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        character_count = len(input_data["text"])
        actual_cost = settings.voice.elevenlabs_cost_per_character * character_count
        
        return {
            "output_data": {
                "voice": voice,
                "voice_id": voice_id,
                "character_count": character_count,
                "format": "mp3"
            },
            "output_files": [{
                "filename": filename,
                "local_path": audio_path,
                "format": "mp3",
                "size_bytes": len(audio_data)
            }],
            "actual_cost_cc": actual_cost / settings.voice.elevenlabs_cost_per_character,
            "processing_time": processing_time
        }
    
    async def _local_tts(self, operation: AIOperation) -> Dict[str, Any]:
        """Generate speech using local TTS"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        if not settings.voice.enable_local_tts:
            raise Exception("Local TTS is not enabled")
        
        # Simulate local TTS processing
        await asyncio.sleep(3)  # Local TTS typically takes a few seconds
        
        # In reality, this would interface with local TTS systems like:
        # - Tortoise TTS
        # - Bark
        # - Coqui TTS
        # - Festival
        # etc.
        
        filename = f"local_tts_{operation.id}.wav"
        
        # Simulate audio file creation
        audio_path = f"/tmp/audio/{filename}"
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        
        # Create a dummy audio file (in reality, this would be generated audio)
        with open(audio_path, 'wb') as f:
            f.write(b'dummy_audio_data')
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        character_count = len(input_data["text"])
        actual_cost = settings.voice.local_tts_cost_per_character * character_count
        
        return {
            "output_data": {
                "voice": input_data["voice"],
                "character_count": character_count,
                "format": "wav",
                "model": settings.voice.local_tts_model
            },
            "output_files": [{
                "filename": filename,
                "local_path": audio_path,
                "format": "wav",
                "size_bytes": 1024  # Dummy size
            }],
            "actual_cost_cc": actual_cost / settings.voice.local_tts_cost_per_character,
            "processing_time": processing_time
        }
    
    async def _process_voice_cloning(self, operation: AIOperation) -> Dict[str, Any]:
        """Process voice cloning from audio sample"""
        
        input_data = operation.input_data
        start_time = datetime.utcnow()
        
        # Simulate voice cloning process
        await asyncio.sleep(60)  # Voice cloning typically takes 1-10 minutes
        
        voice_id = f"cloned_{operation.id}"
        model_filename = f"voice_model_{voice_id}.pth"
        
        # In reality, this would:
        # 1. Extract voice features from the audio sample
        # 2. Train or fine-tune a voice model
        # 3. Save the model files
        # 4. Test the cloned voice
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Estimate cost based on processing time
        actual_cost = Decimal("5.0")  # Base cost for voice cloning
        
        return {
            "output_data": {
                "voice_id": voice_id,
                "voice_name": input_data["voice_name"],
                "original_duration": input_data["duration_seconds"],
                "quality_score": 0.85  # Simulated quality score
            },
            "output_files": [{
                "filename": model_filename,
                "local_path": f"/models/voices/{model_filename}",
                "type": "voice_model",
                "size_bytes": 50000000  # ~50MB model file
            }],
            "actual_cost_cc": actual_cost,
            "processing_time": processing_time
        }
    
    async def _select_optimal_provider(
        self, 
        text: str, 
        voice: str, 
        kwargs: Dict
    ) -> AIProvider:
        """Select optimal provider based on requirements and cost"""
        
        character_count = len(text)
        
        # For short text and standard voices, prefer cheaper options
        if character_count < 1000 and voice in self.voice_models["openai"]:
            return AIProvider.OPENAI
        
        # For longer text, consider local TTS if available
        if settings.voice.enable_local_tts and character_count > 5000:
            return AIProvider.LOCAL
        
        # Default to OpenAI for general use
        return AIProvider.OPENAI
    
    async def _store_audio_data(self, audio_data: bytes, filename: str) -> str:
        """Store audio data to local file"""
        
        storage_dir = "/tmp/audio"
        os.makedirs(storage_dir, exist_ok=True)
        
        local_path = os.path.join(storage_dir, filename)
        
        async with aiofiles.open(local_path, 'wb') as f:
            await f.write(audio_data)
        
        return local_path
    
    async def _get_audio_duration(self, file_path: str) -> float:
        """Get audio file duration in seconds"""
        
        # This would use a library like librosa, pydub, or ffmpeg
        # For now, simulate duration detection
        try:
            # Simulate reading file and getting duration
            return 45.0  # 45 seconds
        except:
            raise ValueError("Could not determine audio duration")
    
    def _generate_input_hash(self, input_data: Dict) -> str:
        """Generate hash for caching purposes"""
        
        cache_data = {
            "text": input_data.get("text", ""),
            "voice": input_data.get("voice", ""),
            "speed": input_data.get("speed", 1.0),
            "output_format": input_data.get("output_format", "mp3")
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    async def list_available_voices(self) -> Dict[str, Any]:
        """List all available voices by provider"""
        
        return {
            "providers": {
                "openai": {
                    "voices": self.voice_models["openai"],
                    "cost_per_character": float(settings.voice.openai_tts_cost_per_character),
                    "supported_formats": ["mp3", "opus", "aac", "flac"]
                },
                "elevenlabs": {
                    "voices": self.voice_models["elevenlabs"],
                    "cost_per_character": float(settings.voice.elevenlabs_cost_per_character),
                    "supported_formats": ["mp3"]
                },
                "local": {
                    "voices": self.voice_models["local"],
                    "cost_per_character": float(settings.voice.local_tts_cost_per_character),
                    "supported_formats": ["wav", "mp3"]
                }
            },
            "voice_cloning": {
                "enabled": settings.voice.enable_voice_cloning,
                "min_duration_seconds": settings.voice.min_audio_duration_seconds,
                "max_duration_seconds": settings.voice.max_audio_duration_seconds,
                "supported_formats": ["wav", "mp3", "flac"]
            }
        }
    
    async def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of a voice synthesis operation"""
        
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
            result["audio_files"] = operation.output_files
        
        if operation.error_message:
            result["error"] = operation.error_message
        
        return result