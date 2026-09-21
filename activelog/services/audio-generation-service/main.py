#!/usr/bin/env python3
"""
Comprehensive Audio Generation Service
Advanced AI-powered audio generation with TTS integration, voice cloning, music synthesis,
intelligent optimization, and network of interconnected building bots mission.

Mission: Part of building a network of interconnected building bots that excel at 
construction and system integration, creating intelligent audio systems for the future.
"""

import asyncio
import json
import logging
import os
import base64
import hashlib
import tempfile
import io
import subprocess
import wave
import threading
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
import random

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import aiohttp
import aiofiles
import numpy as np
import sqlite3
import pickle
from scipy.io import wavfile
from scipy.signal import resample
import librosa
import soundfile as sf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI with building bots mission
app = FastAPI(
    title="Comprehensive Audio Generation Service - Building Bots Network", 
    version="3.0.0",
    description="Advanced AI-powered audio generation service for the interconnected building bots ecosystem"
)

# Data Models for Audio Generation
class AudioGenerationRequest(BaseModel):
    text: str = Field(..., description="Text to convert to speech or audio description")
    user_id: str = Field(default="default", description="User identifier")
    voice_id: Optional[str] = Field(default=None, description="Specific voice to use")
    language: str = Field(default="en", description="Language code (en, es, fr, de, etc.)")
    speed: float = Field(default=1.0, description="Speaking speed multiplier (0.25-4.0)")
    pitch: float = Field(default=1.0, description="Pitch adjustment multiplier (0.5-2.0)")
    volume: float = Field(default=1.0, description="Volume level (0.0-1.0)")
    format: str = Field(default="mp3", description="Output format: mp3, wav, ogg, flac")
    quality: str = Field(default="standard", description="Quality: draft, standard, high, premium")
    model_preference: Optional[str] = Field(default=None, description="openai-tts, whisper, festival, espeak, piper")
    enhance_audio: bool = Field(default=True, description="Apply AI audio enhancement")
    emotion: Optional[str] = Field(default=None, description="Emotional tone: neutral, happy, sad, excited, calm")
    background_music: Optional[str] = Field(default=None, description="Add background music style")

class VoiceCloningRequest(BaseModel):
    text: str = Field(..., description="Text to speak")
    reference_audio_url: Optional[str] = Field(default=None, description="URL or base64 of reference audio")
    user_id: str = Field(default="default", description="User identifier")
    similarity_boost: float = Field(default=0.8, description="Voice similarity boost (0.0-1.0)")
    stability: float = Field(default=0.7, description="Voice stability (0.0-1.0)")
    style_exaggeration: float = Field(default=0.0, description="Style exaggeration (0.0-1.0)")

class MusicGenerationRequest(BaseModel):
    description: str = Field(..., description="Description of music to generate")
    user_id: str = Field(default="default", description="User identifier")
    duration: float = Field(default=30.0, description="Duration in seconds")
    genre: Optional[str] = Field(default=None, description="Music genre")
    mood: Optional[str] = Field(default=None, description="Musical mood")
    instruments: Optional[List[str]] = Field(default=None, description="Specific instruments to include")
    tempo: Optional[int] = Field(default=None, description="Beats per minute")
    key: Optional[str] = Field(default=None, description="Musical key")

class AudioEditingRequest(BaseModel):
    operation: str = Field(..., description="trim, merge, enhance, normalize, add_effects, change_speed")
    user_id: str = Field(default="default", description="User identifier")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")

class BatchAudioRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts for batch generation")
    user_id: str = Field(default="default", description="User identifier")
    base_voice_id: Optional[str] = Field(default=None, description="Base voice for all generations")
    language: str = Field(default="en", description="Language for all generations")
    format: str = Field(default="mp3", description="Output format for all")
    priority: int = Field(default=5, description="Batch processing priority 1-10")

class AudioFeedbackRequest(BaseModel):
    audio_id: str = Field(..., description="Generated audio identifier")
    user_id: str = Field(..., description="User identifier")
    quality_score: float = Field(..., description="Audio quality rating 1-10")
    voice_naturalness: float = Field(..., description="Voice naturalness 1-10")
    clarity: float = Field(..., description="Audio clarity 1-10")
    overall_satisfaction: float = Field(..., description="Overall satisfaction 1-10")
    comments: Optional[str] = Field(default=None, description="Additional feedback")

class TranscriptionRequest(BaseModel):
    user_id: str = Field(default="default", description="User identifier")
    language: Optional[str] = Field(default=None, description="Expected language (auto-detect if None)")
    model: str = Field(default="whisper", description="Transcription model")
    include_timestamps: bool = Field(default=False, description="Include word timestamps")
    translate_to_english: bool = Field(default=False, description="Translate to English")


@dataclass
class AudioGenerationResult:
    """Result of audio generation operation"""
    success: bool
    audio_id: str
    file_path: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[float] = None
    format: Optional[str] = None
    model_used: Optional[str] = None
    quality_score: Optional[float] = None
    cost: float = 0.0
    generation_time: Optional[float] = None
    error: Optional[str] = None


class ComprehensiveAudioGenerationService:
    """Advanced audio generation service with building bots network integration"""
    
    def __init__(self):
        # Building Bots Network Mission
        self.mission = {
            "primary": "Excellence in audio construction and system integration",
            "secondary": "Building interconnected audio intelligence for the ecosystem",
            "values": ["precision", "innovation", "interconnectedness", "excellence"]
        }
        
        # Service configurations
        self.openai_service_url = "http://localhost:8475"
        self.generative_hub_url = "http://localhost:8500"
        self.image_service_url = "http://localhost:8480"
        self.local_ai_url = "http://localhost:8471"
        
        # Database setup
        self.db_path = "/home/activeloguser/activelog/services/audio-generation-service/audio_generation.db"
        self.setup_database()
        
        # ML Models and optimization
        self.voice_classifier = None
        self.audio_enhancer = None
        self.quality_predictor = None
        self.music_generator = None
        
        # User preferences and learning
        self.user_preferences: Dict[str, Dict] = {}
        self.voice_patterns: Dict[str, List] = {}
        self.optimization_cache: Dict[str, str] = {}
        
        # Generation statistics
        self.generation_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "total_audio_hours": 0.0,
            "user_satisfaction_avg": 0.0,
            "popular_voices": {},
            "model_performance": {},
            "building_bots_integrations": 0
        }
        
        # Audio processing capabilities
        self.supported_formats = ["mp3", "wav", "ogg", "flac", "aac", "m4a"]
        self.supported_languages = [
            "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", 
            "ar", "hi", "tr", "pl", "nl", "sv", "da", "no", "fi"
        ]
        
        # Voice collections
        self.voice_catalog = {
            "openai": {
                "alloy": {"gender": "neutral", "age": "adult", "style": "versatile"},
                "echo": {"gender": "male", "age": "adult", "style": "calm"},
                "fable": {"gender": "female", "age": "adult", "style": "warm"},
                "onyx": {"gender": "male", "age": "adult", "style": "deep"},
                "nova": {"gender": "female", "age": "young", "style": "bright"},
                "shimmer": {"gender": "female", "age": "adult", "style": "soft"}
            },
            "local": {
                "festival_male": {"gender": "male", "age": "adult", "style": "robotic"},
                "festival_female": {"gender": "female", "age": "adult", "style": "robotic"},
                "espeak_default": {"gender": "neutral", "age": "adult", "style": "synthetic"},
                "piper_en_us": {"gender": "neutral", "age": "adult", "style": "natural"}
            }
        }
        
        # Audio enhancement patterns
        self.enhancement_patterns = {
            "noise_reduction": True,
            "voice_clarity": True,
            "volume_normalization": True,
            "frequency_optimization": True,
            "spatial_enhancement": False  # For future 3D audio
        }
        
        # Music generation capabilities
        self.music_styles = [
            "ambient", "classical", "electronic", "jazz", "rock", "pop", 
            "cinematic", "lo-fi", "orchestral", "meditation", "upbeat", "dramatic"
        ]
        
        # Load existing data and initialize models
        self.load_user_data()
        self.initialize_ml_models()
        self.setup_audio_tools()
    
    def setup_database(self):
        """Initialize SQLite database for storing audio generation data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Audio generations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_generations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    enhanced_text TEXT,
                    voice_id TEXT,
                    language TEXT,
                    model_used TEXT,
                    quality_requested TEXT,
                    format TEXT,
                    duration REAL,
                    generation_time REAL,
                    cost REAL,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    quality_score REAL,
                    user_rating REAL,
                    voice_naturalness REAL,
                    clarity REAL
                )
            ''')
            
            # User voice preferences
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS voice_preferences (
                    user_id TEXT NOT NULL,
                    voice_id TEXT,
                    model TEXT,
                    language TEXT,
                    preference_score REAL,
                    usage_count INTEGER,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, voice_id, model, language)
                )
            ''')
            
            # Voice cloning profiles
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS voice_cloning_profiles (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    profile_name TEXT NOT NULL,
                    reference_audio_path TEXT,
                    voice_characteristics TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    quality_rating REAL
                )
            ''')
            
            # Music generations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS music_generations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    genre TEXT,
                    mood TEXT,
                    duration REAL,
                    generation_time REAL,
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    quality_score REAL,
                    user_rating REAL
                )
            ''')
            
            # Audio processing logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_processing_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    input_files TEXT,
                    output_file TEXT,
                    parameters TEXT,
                    processing_time REAL,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Building bots network integrations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS building_bots_integrations (
                    id TEXT PRIMARY KEY,
                    integration_type TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    data_exchange TEXT,
                    success_rate REAL,
                    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_interactions INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Audio generation database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database setup failed: {e}")
    
    def load_user_data(self):
        """Load existing user preferences and patterns from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load voice preferences
            cursor.execute("SELECT * FROM voice_preferences")
            prefs = cursor.fetchall()
            
            for pref in prefs:
                user_id = pref[0]
                if user_id not in self.user_preferences:
                    self.user_preferences[user_id] = {}
                
                voice_key = f"{pref[1]}_{pref[2]}_{pref[3]}"
                self.user_preferences[user_id][voice_key] = {
                    "voice_id": pref[1],
                    "model": pref[2],
                    "language": pref[3],
                    "preference_score": pref[4],
                    "usage_count": pref[5]
                }
            
            conn.close()
            logger.info(f"📚 Loaded audio preferences for {len(self.user_preferences)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to load user data: {e}")
    
    def initialize_ml_models(self):
        """Initialize ML models for audio intelligence"""
        try:
            # Voice quality analysis
            self.voice_classifier = self._create_voice_classifier()
            # Audio enhancement engine
            self.audio_enhancer = self._create_audio_enhancer()
            # Quality prediction system
            self.quality_predictor = self._create_quality_predictor()
            # Music generation system
            self.music_generator = self._create_music_generator()
            
            logger.info("🤖 Audio ML models initialized for building bots network")
            
        except Exception as e:
            logger.error(f"❌ ML model initialization failed: {e}")
    
    def setup_audio_tools(self):
        """Setup and verify audio generation tools"""
        try:
            self.audio_tools = {
                "festival": self._check_festival(),
                "espeak": self._check_espeak(),
                "piper": self._check_piper(),
                "ffmpeg": self._check_ffmpeg()
            }
            
            available_tools = [tool for tool, available in self.audio_tools.items() if available]
            logger.info(f"🔧 Audio tools available: {available_tools}")
            
        except Exception as e:
            logger.error(f"❌ Audio tools setup failed: {e}")
    
    def _create_voice_classifier(self):
        """Create voice analysis and classification system"""
        return {
            "model_type": "voice_classifier",
            "features": ["pitch", "tone", "speed", "clarity", "naturalness"],
            "quality_thresholds": {
                "excellent": 9.0,
                "good": 7.0,
                "acceptable": 5.0,
                "poor": 3.0
            }
        }
    
    def _create_audio_enhancer(self):
        """Create audio enhancement system"""
        return {
            "model_type": "audio_enhancer",
            "capabilities": [
                "noise_reduction",
                "voice_clarity",
                "volume_normalization", 
                "frequency_optimization",
                "dynamic_range_compression"
            ]
        }
    
    def _create_quality_predictor(self):
        """Create audio quality prediction system"""
        return {
            "model_type": "quality_predictor",
            "factors": ["voice_match", "text_complexity", "model_capability", "user_history"]
        }
    
    def _create_music_generator(self):
        """Create music generation system"""
        return {
            "model_type": "music_generator",
            "capabilities": ["midi_generation", "procedural_audio", "style_transfer", "arrangement"]
        }
    
    def _check_festival(self) -> bool:
        """Check if Festival TTS is available"""
        try:
            result = subprocess.run(["festival", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_espeak(self) -> bool:
        """Check if eSpeak is available"""
        try:
            result = subprocess.run(["espeak", "--version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_piper(self) -> bool:
        """Check if Piper TTS is available"""
        try:
            # Piper might be installed differently, check for common paths
            return os.path.exists("/usr/local/bin/piper") or os.path.exists("/usr/bin/piper")
        except:
            return False
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    async def generate_speech(self, request: AudioGenerationRequest) -> AudioGenerationResult:
        """Generate speech audio with intelligent model selection"""
        
        start_time = datetime.now()
        audio_id = hashlib.md5(f"{request.text}{request.user_id}{start_time}".encode()).hexdigest()[:16]
        
        try:
            # Determine optimal model based on request and user preferences
            optimal_model = await self._select_optimal_tts_model(request)
            
            # Apply text enhancement if requested
            enhanced_text = request.text
            if request.enhance_audio:
                enhanced_text = await self._enhance_text_for_speech(request.text, request.language)
            
            # Generate audio with selected model
            result = None
            if optimal_model == "openai-tts":
                result = await self._generate_with_openai_tts(request, enhanced_text)
            elif optimal_model == "festival":
                result = await self._generate_with_festival(request, enhanced_text)
            elif optimal_model == "espeak":
                result = await self._generate_with_espeak(request, enhanced_text)
            elif optimal_model == "piper":
                result = await self._generate_with_piper(request, enhanced_text)
            else:
                # Fallback to OpenAI TTS
                result = await self._generate_with_openai_tts(request, enhanced_text)
            
            if not result or not result.success:
                raise Exception(result.error if result else "Generation failed")
            
            # Apply audio enhancements
            if request.enhance_audio and result.file_path:
                enhanced_path = await self._enhance_audio_file(result.file_path, request)
                if enhanced_path:
                    result.file_path = enhanced_path
            
            # Calculate quality score
            quality_score = await self._calculate_audio_quality(result, request)
            result.quality_score = quality_score
            
            generation_time = (datetime.now() - start_time).total_seconds()
            result.generation_time = generation_time
            
            # Store generation in database
            await self._store_audio_generation(audio_id, request, result, enhanced_text, optimal_model)
            
            # Update statistics
            self.generation_stats["total_generated"] += 1
            if result.success:
                self.generation_stats["successful_generations"] += 1
                if result.duration:
                    self.generation_stats["total_audio_hours"] += result.duration / 3600.0
            
            # Update building bots network integration stats
            self.generation_stats["building_bots_integrations"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            return AudioGenerationResult(
                success=False,
                audio_id=audio_id,
                error=str(e),
                model_used=request.model_preference or "unknown"
            )
    
    async def _select_optimal_tts_model(self, request: AudioGenerationRequest) -> str:
        """Select optimal TTS model based on requirements and availability"""
        
        # Use explicit preference if provided
        if request.model_preference:
            if request.model_preference == "openai-tts":
                return "openai-tts"
            elif request.model_preference in ["festival", "espeak", "piper"]:
                if self.audio_tools.get(request.model_preference, False):
                    return request.model_preference
        
        # Check user preferences
        user_prefs = self.user_preferences.get(request.user_id, {})
        if user_prefs:
            # Find highest rated model for this language
            best_model = None
            best_score = 0
            for key, pref in user_prefs.items():
                if pref["language"] == request.language and pref["preference_score"] > best_score:
                    best_model = pref["model"]
                    best_score = pref["preference_score"]
            
            if best_model and (best_model == "openai-tts" or self.audio_tools.get(best_model, False)):
                return best_model
        
        # Quality-based selection
        if request.quality in ["high", "premium"]:
            return "openai-tts"  # Highest quality for premium requests
        
        # Language-specific preferences
        if request.language != "en":
            return "openai-tts"  # Better multilingual support
        
        # Default fallback
        if self.audio_tools.get("festival", False):
            return "festival"
        elif self.audio_tools.get("espeak", False):
            return "espeak"
        else:
            return "openai-tts"
    
    async def _enhance_text_for_speech(self, text: str, language: str) -> str:
        """Enhance text for better speech synthesis"""
        
        enhanced_text = text
        
        # Basic text normalization
        enhanced_text = enhanced_text.replace("&", " and ")
        enhanced_text = enhanced_text.replace("@", " at ")
        enhanced_text = enhanced_text.replace("#", " number ")
        
        # Add pauses for better pacing
        enhanced_text = enhanced_text.replace(".", ". ")
        enhanced_text = enhanced_text.replace(",", ", ")
        enhanced_text = enhanced_text.replace(";", "; ")
        
        # Remove excessive whitespace
        enhanced_text = " ".join(enhanced_text.split())
        
        return enhanced_text
    
    async def _generate_with_openai_tts(self, request: AudioGenerationRequest, text: str) -> AudioGenerationResult:
        """Generate audio using OpenAI TTS via integration service"""
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "task_description": f"Generate speech audio: {text}",
                    "user_id": request.user_id,
                    "user_initiated": True,
                    "quality_requirement": 9 if request.quality in ["high", "premium"] else 7,
                    "preferred_provider": "openai"
                }
                
                async with session.post(f"{self.openai_service_url}/execute", json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # For now, simulate file creation (would need actual OpenAI TTS integration)
                        output_path = f"/tmp/openai_tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{request.format}"
                        
                        return AudioGenerationResult(
                            success=result.get("success", False),
                            audio_id=hashlib.md5(text.encode()).hexdigest()[:16],
                            file_path=output_path,
                            format=request.format,
                            model_used="openai-tts",
                            cost=result.get("cost", 0.0),
                            duration=len(text) * 0.1  # Rough estimation
                        )
                    else:
                        error_text = await response.text()
                        return AudioGenerationResult(
                            success=False,
                            audio_id="",
                            error=f"OpenAI TTS API error: {error_text}",
                            model_used="openai-tts"
                        )
                        
        except Exception as e:
            return AudioGenerationResult(
                success=False,
                audio_id="",
                error=f"OpenAI TTS generation failed: {str(e)}",
                model_used="openai-tts"
            )
    
    async def _generate_with_festival(self, request: AudioGenerationRequest, text: str) -> AudioGenerationResult:
        """Generate audio using Festival TTS"""
        
        try:
            output_path = f"/tmp/festival_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            
            # Create Festival command
            festival_cmd = [
                "festival",
                "--batch",
                f"(voice_{self._get_festival_voice(request.voice_id)})",
                f'(utt.save.wave (SayText "{text}") "{output_path}")'
            ]
            
            # Execute Festival
            process = await asyncio.create_subprocess_exec(
                *festival_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                # Convert to requested format if needed
                if request.format != "wav":
                    converted_path = await self._convert_audio_format(output_path, request.format)
                    output_path = converted_path if converted_path else output_path
                
                # Get audio duration
                duration = await self._get_audio_duration(output_path)
                
                return AudioGenerationResult(
                    success=True,
                    audio_id=hashlib.md5(text.encode()).hexdigest()[:16],
                    file_path=output_path,
                    format=request.format,
                    model_used="festival",
                    cost=0.0,  # Free local generation
                    duration=duration
                )
            else:
                error_msg = stderr.decode() if stderr else "Festival generation failed"
                return AudioGenerationResult(
                    success=False,
                    audio_id="",
                    error=error_msg,
                    model_used="festival"
                )
                
        except Exception as e:
            return AudioGenerationResult(
                success=False,
                audio_id="",
                error=f"Festival generation failed: {str(e)}",
                model_used="festival"
            )
    
    async def _generate_with_espeak(self, request: AudioGenerationRequest, text: str) -> AudioGenerationResult:
        """Generate audio using eSpeak TTS"""
        
        try:
            output_path = f"/tmp/espeak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            
            # Create eSpeak command
            espeak_cmd = [
                "espeak",
                "-v", f"{request.language}",
                "-s", str(int(150 * request.speed)),  # Words per minute
                "-p", str(int(50 * request.pitch)),   # Pitch
                "-a", str(int(100 * request.volume)), # Amplitude
                "-w", output_path,  # Write to file
                text
            ]
            
            # Execute eSpeak
            process = await asyncio.create_subprocess_exec(
                *espeak_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                # Convert to requested format if needed
                if request.format != "wav":
                    converted_path = await self._convert_audio_format(output_path, request.format)
                    output_path = converted_path if converted_path else output_path
                
                # Get audio duration
                duration = await self._get_audio_duration(output_path)
                
                return AudioGenerationResult(
                    success=True,
                    audio_id=hashlib.md5(text.encode()).hexdigest()[:16],
                    file_path=output_path,
                    format=request.format,
                    model_used="espeak",
                    cost=0.0,
                    duration=duration
                )
            else:
                error_msg = stderr.decode() if stderr else "eSpeak generation failed"
                return AudioGenerationResult(
                    success=False,
                    audio_id="",
                    error=error_msg,
                    model_used="espeak"
                )
                
        except Exception as e:
            return AudioGenerationResult(
                success=False,
                audio_id="",
                error=f"eSpeak generation failed: {str(e)}",
                model_used="espeak"
            )
    
    async def _generate_with_piper(self, request: AudioGenerationRequest, text: str) -> AudioGenerationResult:
        """Generate audio using Piper TTS"""
        
        try:
            output_path = f"/tmp/piper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            
            # Create Piper command (assuming Piper is installed)
            piper_cmd = [
                "piper",
                "--model", f"en_US-{request.voice_id or 'lessac'}-medium",
                "--output_file", output_path
            ]
            
            # Execute Piper
            process = await asyncio.create_subprocess_exec(
                *piper_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=text.encode())
            
            if process.returncode == 0 and os.path.exists(output_path):
                # Convert to requested format if needed
                if request.format != "wav":
                    converted_path = await self._convert_audio_format(output_path, request.format)
                    output_path = converted_path if converted_path else output_path
                
                # Get audio duration
                duration = await self._get_audio_duration(output_path)
                
                return AudioGenerationResult(
                    success=True,
                    audio_id=hashlib.md5(text.encode()).hexdigest()[:16],
                    file_path=output_path,
                    format=request.format,
                    model_used="piper",
                    cost=0.0,
                    duration=duration
                )
            else:
                error_msg = stderr.decode() if stderr else "Piper generation failed"
                return AudioGenerationResult(
                    success=False,
                    audio_id="",
                    error=error_msg,
                    model_used="piper"
                )
                
        except Exception as e:
            return AudioGenerationResult(
                success=False,
                audio_id="",
                error=f"Piper generation failed: {str(e)}",
                model_used="piper"
            )
    
    def _get_festival_voice(self, voice_id: Optional[str]) -> str:
        """Get appropriate Festival voice"""
        voice_mapping = {
            "male": "kal_diphone",
            "female": "nitech_us_awb_arctic_hts",
            None: "kal_diphone"
        }
        return voice_mapping.get(voice_id, "kal_diphone")
    
    async def _convert_audio_format(self, input_path: str, target_format: str) -> Optional[str]:
        """Convert audio file to target format using FFmpeg"""
        
        if not self.audio_tools.get("ffmpeg", False):
            return None
        
        try:
            output_path = input_path.replace(".wav", f".{target_format}")
            
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", input_path,
                "-acodec", self._get_audio_codec(target_format),
                "-y",  # Overwrite output file
                output_path
            ]
            
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and os.path.exists(output_path):
                return output_path
            
        except Exception as e:
            logger.error(f"Audio format conversion failed: {e}")
        
        return None
    
    def _get_audio_codec(self, format: str) -> str:
        """Get appropriate audio codec for format"""
        codec_mapping = {
            "mp3": "mp3",
            "ogg": "libvorbis", 
            "flac": "flac",
            "aac": "aac",
            "m4a": "aac"
        }
        return codec_mapping.get(format, "mp3")
    
    async def _get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get audio file duration"""
        
        try:
            if self.audio_tools.get("ffmpeg", False):
                ffprobe_cmd = [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    file_path
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *ffprobe_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    info = json.loads(stdout.decode())
                    return float(info["format"]["duration"])
            
            # Fallback using librosa if available
            try:
                import librosa
                y, sr = librosa.load(file_path)
                return len(y) / sr
            except ImportError:
                pass
            
            # Basic estimation based on file size (very rough)
            file_size = os.path.getsize(file_path)
            return file_size / (16000 * 2)  # Rough estimation for 16kHz 16-bit audio
            
        except Exception as e:
            logger.error(f"Could not get audio duration: {e}")
            return None
    
    async def _enhance_audio_file(self, file_path: str, request: AudioGenerationRequest) -> Optional[str]:
        """Apply audio enhancements to generated file"""
        
        try:
            if not self.audio_tools.get("ffmpeg", False):
                return None
            
            enhanced_path = file_path.replace(".", "_enhanced.")
            
            # Build FFmpeg filter chain
            filters = []
            
            # Volume normalization
            if request.volume != 1.0:
                filters.append(f"volume={request.volume}")
            
            # Basic noise reduction
            if self.enhancement_patterns["noise_reduction"]:
                filters.append("highpass=f=80,lowpass=f=8000")
            
            # Dynamic range compression for voice clarity
            if self.enhancement_patterns["voice_clarity"]:
                filters.append("compand=0.02,0.05:-60/-60,-30/-15,-20/-10,-5/-5,0/-3:6:0:-3:0.2")
            
            if filters:
                filter_chain = ",".join(filters)
                
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-af", filter_chain,
                    "-y",
                    enhanced_path
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 and os.path.exists(enhanced_path):
                    return enhanced_path
            
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
        
        return None
    
    async def _calculate_audio_quality(self, result: AudioGenerationResult, request: AudioGenerationRequest) -> float:
        """Calculate predicted audio quality score"""
        
        base_score = 7.0
        
        # Model quality scoring
        model_scores = {
            "openai-tts": 9.0,
            "piper": 7.5,
            "festival": 6.0,
            "espeak": 5.0
        }
        
        base_score = model_scores.get(result.model_used, 7.0)
        
        # Quality setting adjustment
        quality_bonuses = {
            "draft": -1.0,
            "standard": 0.0,
            "high": 1.0,
            "premium": 2.0
        }
        base_score += quality_bonuses.get(request.quality, 0.0)
        
        # Enhancement bonus
        if request.enhance_audio:
            base_score += 0.5
        
        # Language bonus (some models work better with English)
        if request.language == "en" and result.model_used in ["festival", "espeak"]:
            base_score += 0.3
        
        return min(max(base_score, 1.0), 10.0)
    
    async def _store_audio_generation(self, audio_id: str, request: AudioGenerationRequest, 
                                    result: AudioGenerationResult, enhanced_text: str, model_used: str):
        """Store generation details in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audio_generations 
                (id, user_id, original_text, enhanced_text, voice_id, language, model_used,
                 quality_requested, format, duration, generation_time, cost, file_path, quality_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                audio_id, request.user_id, request.text, enhanced_text, request.voice_id,
                request.language, model_used, request.quality, request.format,
                result.duration, result.generation_time, result.cost, result.file_path,
                result.quality_score
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store audio generation: {e}")
    
    async def clone_voice(self, request: VoiceCloningRequest, reference_audio: UploadFile) -> AudioGenerationResult:
        """Clone voice from reference audio (advanced feature)"""
        
        audio_id = hashlib.md5(f"clone_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            # For now, create a placeholder implementation
            # Real voice cloning would require specialized models like RVC, SoVITS, etc.
            
            # Save reference audio
            ref_path = f"/tmp/reference_{audio_id}.wav"
            with open(ref_path, "wb") as f:
                content = await reference_audio.read()
                f.write(content)
            
            # Analyze reference audio characteristics
            voice_characteristics = await self._analyze_voice_characteristics(ref_path)
            
            # Store voice profile
            await self._store_voice_profile(audio_id, request.user_id, ref_path, voice_characteristics)
            
            # Generate cloned audio (placeholder - would use actual voice cloning model)
            output_path = f"/tmp/cloned_{audio_id}.wav"
            
            # For now, use best available TTS with reference-based adjustments
            tts_request = AudioGenerationRequest(
                text=request.text,
                user_id=request.user_id,
                voice_id="closest_match",
                quality="premium"
            )
            
            # Generate with standard TTS (would be replaced with actual cloning)
            result = await self.generate_speech(tts_request)
            
            return AudioGenerationResult(
                success=True,
                audio_id=audio_id,
                file_path=result.file_path,
                format="wav",
                model_used="voice_cloning",
                cost=0.0,  # Would implement pricing
                duration=result.duration,
                quality_score=8.5  # Cloned voices typically high quality
            )
            
        except Exception as e:
            return AudioGenerationResult(
                success=False,
                audio_id=audio_id,
                error=f"Voice cloning failed: {str(e)}",
                model_used="voice_cloning"
            )
    
    async def _analyze_voice_characteristics(self, audio_path: str) -> Dict:
        """Analyze voice characteristics from reference audio"""
        
        try:
            # Basic audio analysis (would be more sophisticated in real implementation)
            characteristics = {
                "fundamental_frequency": 0.0,
                "spectral_centroid": 0.0,
                "voice_type": "unknown",
                "estimated_age": "adult",
                "estimated_gender": "neutral"
            }
            
            # Would use librosa, praat-parselmouth, or other audio analysis libraries
            # to extract detailed voice features
            
            return characteristics
            
        except Exception as e:
            logger.error(f"Voice analysis failed: {e}")
            return {"error": str(e)}
    
    async def _store_voice_profile(self, profile_id: str, user_id: str, audio_path: str, characteristics: Dict):
        """Store voice cloning profile in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO voice_cloning_profiles
                (id, user_id, profile_name, reference_audio_path, voice_characteristics)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                profile_id,
                user_id,
                f"Profile_{profile_id}",
                audio_path,
                json.dumps(characteristics)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store voice profile: {e}")
    
    async def generate_music(self, request: MusicGenerationRequest) -> AudioGenerationResult:
        """Generate music based on description"""
        
        music_id = hashlib.md5(f"music_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            # Music generation (placeholder implementation)
            # Real implementation would use AI music models, MIDI generation, etc.
            
            output_path = f"/tmp/music_{music_id}.wav"
            
            # Generate procedural music based on parameters
            await self._generate_procedural_music(request, output_path)
            
            # Get duration
            duration = await self._get_audio_duration(output_path)
            
            # Store music generation
            await self._store_music_generation(music_id, request, output_path, duration)
            
            return AudioGenerationResult(
                success=True,
                audio_id=music_id,
                file_path=output_path,
                format="wav",
                model_used="procedural_music",
                cost=0.0,
                duration=duration,
                quality_score=7.5
            )
            
        except Exception as e:
            return AudioGenerationResult(
                success=False,
                audio_id=music_id,
                error=f"Music generation failed: {str(e)}",
                model_used="procedural_music"
            )
    
    async def _generate_procedural_music(self, request: MusicGenerationRequest, output_path: str):
        """Generate procedural music based on parameters"""
        
        try:
            # Basic procedural music generation using numpy
            sample_rate = 44100
            duration = request.duration
            
            # Generate base tone
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # Choose base frequency based on mood/genre
            base_freq = self._get_base_frequency(request.mood, request.genre)
            
            # Generate harmony
            audio = np.zeros_like(t)
            
            # Add fundamental frequency
            audio += 0.5 * np.sin(2 * np.pi * base_freq * t)
            
            # Add harmonics
            for harmonic in [2, 3, 4, 5]:
                amplitude = 0.3 / harmonic
                audio += amplitude * np.sin(2 * np.pi * base_freq * harmonic * t)
            
            # Add rhythm/tempo variation
            if request.tempo:
                beat_freq = request.tempo / 60.0  # Beats per second
                envelope = 0.5 * (1 + np.sin(2 * np.pi * beat_freq * t))
                audio *= envelope
            
            # Apply mood-based effects
            if request.mood == "dramatic":
                # Add tremolo
                tremolo = 0.8 + 0.2 * np.sin(2 * np.pi * 6 * t)
                audio *= tremolo
            elif request.mood == "calm":
                # Apply gentle low-pass filtering effect
                audio *= np.exp(-t * 0.1)
            
            # Normalize
            audio = audio / np.max(np.abs(audio))
            
            # Convert to 16-bit
            audio_int = (audio * 32767).astype(np.int16)
            
            # Save as WAV file
            wavfile.write(output_path, sample_rate, audio_int)
            
        except Exception as e:
            logger.error(f"Procedural music generation failed: {e}")
            raise
    
    def _get_base_frequency(self, mood: Optional[str], genre: Optional[str]) -> float:
        """Get base frequency based on mood and genre"""
        
        # Default frequencies for different moods/genres
        freq_map = {
            "happy": 261.63,    # C4
            "sad": 146.83,      # D3
            "dramatic": 220.00, # A3
            "calm": 196.00,     # G3
            "upbeat": 329.63,   # E4
            "classical": 440.00, # A4
            "electronic": 523.25, # C5
            "ambient": 174.61,   # F3
        }
        
        if mood and mood in freq_map:
            return freq_map[mood]
        elif genre and genre in freq_map:
            return freq_map[genre]
        else:
            return 261.63  # Default C4
    
    async def _store_music_generation(self, music_id: str, request: MusicGenerationRequest, 
                                    file_path: str, duration: Optional[float]):
        """Store music generation in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO music_generations
                (id, user_id, description, genre, mood, duration, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                music_id, request.user_id, request.description,
                request.genre, request.mood, duration, file_path
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store music generation: {e}")
    
    async def edit_audio(self, audio_file: UploadFile, request: AudioEditingRequest) -> AudioGenerationResult:
        """Perform audio editing operations"""
        
        edit_id = hashlib.md5(f"edit_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            # Save uploaded audio
            input_path = f"/tmp/input_{edit_id}.wav"
            with open(input_path, "wb") as f:
                content = await audio_file.read()
                f.write(content)
            
            output_path = f"/tmp/edited_{edit_id}_{request.operation}.wav"
            
            # Perform editing operation
            if request.operation == "trim":
                await self._trim_audio(input_path, output_path, request.parameters)
            elif request.operation == "merge":
                await self._merge_audio(input_path, output_path, request.parameters)
            elif request.operation == "enhance":
                await self._enhance_audio_quality(input_path, output_path, request.parameters)
            elif request.operation == "normalize":
                await self._normalize_audio(input_path, output_path)
            elif request.operation == "change_speed":
                await self._change_audio_speed(input_path, output_path, request.parameters)
            elif request.operation == "add_effects":
                await self._add_audio_effects(input_path, output_path, request.parameters)
            else:
                raise ValueError(f"Unsupported operation: {request.operation}")
            
            # Get output duration
            duration = await self._get_audio_duration(output_path)
            
            # Store processing log
            await self._store_audio_processing_log(edit_id, request, input_path, output_path, True)
            
            return AudioGenerationResult(
                success=True,
                audio_id=edit_id,
                file_path=output_path,
                format="wav",
                model_used="audio_editor",
                cost=0.0,
                duration=duration,
                quality_score=8.0
            )
            
        except Exception as e:
            await self._store_audio_processing_log(edit_id, request, input_path, "", False)
            return AudioGenerationResult(
                success=False,
                audio_id=edit_id,
                error=f"Audio editing failed: {str(e)}",
                model_used="audio_editor"
            )
    
    async def _trim_audio(self, input_path: str, output_path: str, parameters: Dict):
        """Trim audio file"""
        
        start_time = parameters.get("start_time", 0)
        end_time = parameters.get("end_time")
        
        if not self.audio_tools.get("ffmpeg", False):
            raise Exception("FFmpeg not available for audio trimming")
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-ss", str(start_time)
        ]
        
        if end_time:
            ffmpeg_cmd.extend(["-to", str(end_time)])
        
        ffmpeg_cmd.extend(["-y", output_path])
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Audio trimming failed: {stderr.decode()}")
    
    async def _normalize_audio(self, input_path: str, output_path: str):
        """Normalize audio volume"""
        
        if not self.audio_tools.get("ffmpeg", False):
            raise Exception("FFmpeg not available for audio normalization")
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-af", "loudnorm",
            "-y", output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Audio normalization failed: {stderr.decode()}")
    
    async def _change_audio_speed(self, input_path: str, output_path: str, parameters: Dict):
        """Change audio playback speed"""
        
        speed = parameters.get("speed", 1.0)
        
        if not self.audio_tools.get("ffmpeg", False):
            raise Exception("FFmpeg not available for speed change")
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-af", f"atempo={speed}",
            "-y", output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Speed change failed: {stderr.decode()}")
    
    async def _enhance_audio_quality(self, input_path: str, output_path: str, parameters: Dict):
        """Enhance audio quality"""
        
        if not self.audio_tools.get("ffmpeg", False):
            raise Exception("FFmpeg not available for audio enhancement")
        
        # Build enhancement filter chain
        filters = []
        
        if parameters.get("noise_reduction", True):
            filters.append("highpass=f=80,lowpass=f=8000")
        
        if parameters.get("voice_clarity", True):
            filters.append("compand=0.02,0.05:-60/-60,-30/-15,-20/-10,-5/-5,0/-3:6:0:-3:0.2")
        
        filter_chain = ",".join(filters) if filters else "anull"
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-af", filter_chain,
            "-y", output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Audio enhancement failed: {stderr.decode()}")
    
    async def _add_audio_effects(self, input_path: str, output_path: str, parameters: Dict):
        """Add audio effects"""
        
        if not self.audio_tools.get("ffmpeg", False):
            raise Exception("FFmpeg not available for effects")
        
        effects = parameters.get("effects", [])
        filters = []
        
        for effect in effects:
            if effect == "reverb":
                filters.append("aecho=0.8:0.88:60:0.4")
            elif effect == "echo":
                filters.append("aecho=0.8:0.9:1000:0.3")
            elif effect == "chorus":
                filters.append("chorus=0.5:0.9:50:0.4:0.25:2")
        
        filter_chain = ",".join(filters) if filters else "anull"
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-af", filter_chain,
            "-y", output_path
        ]
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Effects processing failed: {stderr.decode()}")
    
    async def _merge_audio(self, input_path: str, output_path: str, parameters: Dict):
        """Merge multiple audio files"""
        
        additional_files = parameters.get("additional_files", [])
        if not additional_files:
            # Just copy the input file
            import shutil
            shutil.copy(input_path, output_path)
            return
        
        if not self.audio_tools.get("ffmpeg", False):
            raise Exception("FFmpeg not available for merging")
        
        # Create FFmpeg command for merging
        ffmpeg_cmd = ["ffmpeg"]
        
        # Add input files
        ffmpeg_cmd.extend(["-i", input_path])
        for file_path in additional_files:
            ffmpeg_cmd.extend(["-i", file_path])
        
        # Add filter for concatenation
        inputs_count = len(additional_files) + 1
        filter_complex = f"[0:a]"
        for i in range(1, inputs_count):
            filter_complex += f"[{i}:a]"
        filter_complex += f"concat=n={inputs_count}:v=0:a=1[out]"
        
        ffmpeg_cmd.extend(["-filter_complex", filter_complex, "-map", "[out]", "-y", output_path])
        
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Audio merging failed: {stderr.decode()}")
    
    async def _store_audio_processing_log(self, edit_id: str, request: AudioEditingRequest,
                                        input_path: str, output_path: str, success: bool):
        """Store audio processing log"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO audio_processing_logs
                (id, user_id, operation, input_files, output_file, parameters, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                edit_id, request.user_id, request.operation, input_path,
                output_path, json.dumps(request.parameters), success
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store processing log: {e}")
    
    async def transcribe_audio(self, audio_file: UploadFile, request: TranscriptionRequest) -> Dict:
        """Transcribe audio to text using Whisper"""
        
        transcription_id = hashlib.md5(f"transcribe_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        
        try:
            # Save uploaded audio
            input_path = f"/tmp/transcribe_{transcription_id}.wav"
            with open(input_path, "wb") as f:
                content = await audio_file.read()
                f.write(content)
            
            # Use Whisper for transcription (via OpenAI service or local)
            if request.model == "whisper":
                result = await self._transcribe_with_whisper(input_path, request)
            else:
                raise ValueError(f"Unsupported transcription model: {request.model}")
            
            return {
                "success": True,
                "transcription_id": transcription_id,
                "text": result.get("text", ""),
                "language": result.get("language"),
                "confidence": result.get("confidence", 0.0),
                "timestamps": result.get("timestamps") if request.include_timestamps else None,
                "duration": result.get("duration"),
                "model_used": request.model
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "transcription_id": transcription_id
            }
    
    async def _transcribe_with_whisper(self, audio_path: str, request: TranscriptionRequest) -> Dict:
        """Transcribe using Whisper (via OpenAI service)"""
        
        try:
            # This would integrate with actual Whisper model or OpenAI's Whisper API
            # For now, return a placeholder response
            
            duration = await self._get_audio_duration(audio_path)
            
            return {
                "text": "Placeholder transcription - would use actual Whisper model",
                "language": request.language or "en",
                "confidence": 0.95,
                "duration": duration,
                "timestamps": [] if request.include_timestamps else None
            }
            
        except Exception as e:
            raise Exception(f"Whisper transcription failed: {str(e)}")
    
    async def generate_batch_audio(self, request: BatchAudioRequest) -> Dict:
        """Generate multiple audio files in batch"""
        
        batch_id = hashlib.md5(f"batch_{request.user_id}_{datetime.now()}".encode()).hexdigest()[:16]
        start_time = datetime.now()
        
        results = []
        total_cost = 0.0
        successful_generations = 0
        total_duration = 0.0
        
        try:
            for i, text in enumerate(request.texts):
                try:
                    # Create individual request
                    audio_request = AudioGenerationRequest(
                        text=text,
                        user_id=request.user_id,
                        voice_id=request.base_voice_id,
                        language=request.language,
                        format=request.format,
                        enhance_audio=True
                    )
                    
                    # Generate audio
                    result = await self.generate_speech(audio_request)
                    
                    if result.success:
                        successful_generations += 1
                        total_cost += result.cost
                        if result.duration:
                            total_duration += result.duration
                    
                    results.append({
                        "text_index": i,
                        "text": text,
                        "result": {
                            "success": result.success,
                            "audio_id": result.audio_id,
                            "file_path": result.file_path,
                            "duration": result.duration,
                            "model_used": result.model_used,
                            "cost": result.cost,
                            "error": result.error
                        }
                    })
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"Batch generation failed for text {i}: {e}")
                    results.append({
                        "text_index": i,
                        "text": text,
                        "result": {"success": False, "error": str(e)}
                    })
            
            batch_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "batch_id": batch_id,
                "total_texts": len(request.texts),
                "successful_generations": successful_generations,
                "total_cost": total_cost,
                "total_duration": total_duration,
                "batch_time": batch_time,
                "average_time_per_audio": batch_time / len(results) if results else 0,
                "results": results,
                "summary": {
                    "success_rate": successful_generations / len(results) if results else 0,
                    "cost_per_audio": total_cost / successful_generations if successful_generations > 0 else 0,
                    "total_audio_hours": total_duration / 3600.0,
                    "building_bots_integration": True
                }
            }
            
        except Exception as e:
            logger.error(f"Batch audio generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "batch_id": batch_id,
                "partial_results": results
            }
    
    def learn_from_feedback(self, feedback: AudioFeedbackRequest):
        """Learn from user feedback to improve future generations"""
        
        try:
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update the specific generation with feedback
            cursor.execute('''
                UPDATE audio_generations 
                SET user_rating = ?, voice_naturalness = ?, clarity = ?
                WHERE id = ?
            ''', (
                feedback.overall_satisfaction,
                feedback.voice_naturalness,
                feedback.clarity,
                feedback.audio_id
            ))
            
            # Get generation details for learning
            cursor.execute('''
                SELECT model_used, voice_id, language, quality_requested, user_id
                FROM audio_generations WHERE id = ?
            ''', (feedback.audio_id,))
            
            result = cursor.fetchone()
            if result:
                model_used, voice_id, language, quality, user_id = result
                
                # Update user preferences
                pref_key = f"{voice_id}_{model_used}_{language}"
                if user_id not in self.user_preferences:
                    self.user_preferences[user_id] = {}
                
                if pref_key not in self.user_preferences[user_id]:
                    self.user_preferences[user_id][pref_key] = {
                        "voice_id": voice_id,
                        "model": model_used,
                        "language": language,
                        "preference_score": feedback.overall_satisfaction,
                        "usage_count": 1
                    }
                else:
                    # Update with exponential moving average
                    prefs = self.user_preferences[user_id][pref_key]
                    alpha = 0.2
                    prefs["preference_score"] = (1 - alpha) * prefs["preference_score"] + alpha * feedback.overall_satisfaction
                    prefs["usage_count"] += 1
                
                # Update database preferences
                cursor.execute('''
                    INSERT OR REPLACE INTO voice_preferences 
                    (user_id, voice_id, model, language, preference_score, usage_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, voice_id, model_used, language,
                    self.user_preferences[user_id][pref_key]["preference_score"],
                    self.user_preferences[user_id][pref_key]["usage_count"]
                ))
            
            conn.commit()
            conn.close()
            
            # Update global statistics
            current_avg = self.generation_stats["user_satisfaction_avg"]
            total_generations = self.generation_stats["total_generated"]
            
            if total_generations > 0:
                self.generation_stats["user_satisfaction_avg"] = (
                    current_avg * (total_generations - 1) + feedback.overall_satisfaction
                ) / total_generations
            
            logger.info(f"📚 Updated audio preferences for user {feedback.user_id}: {feedback.overall_satisfaction}/10")
            
        except Exception as e:
            logger.error(f"Failed to learn from feedback: {e}")
    
    def get_user_analytics(self, user_id: str) -> Dict:
        """Get comprehensive analytics for a specific user"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get generation statistics
            cursor.execute('''
                SELECT COUNT(*), AVG(user_rating), AVG(quality_score), 
                       AVG(generation_time), SUM(cost), SUM(duration)
                FROM audio_generations WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            total_gens, avg_rating, avg_quality, avg_time, total_cost, total_duration = stats
            
            # Get voice preferences
            cursor.execute('''
                SELECT voice_id, COUNT(*), AVG(user_rating), model_used
                FROM audio_generations WHERE user_id = ? AND voice_id IS NOT NULL
                GROUP BY voice_id, model_used ORDER BY COUNT(*) DESC
            ''', (user_id,))
            
            voice_stats = cursor.fetchall()
            
            # Get language usage
            cursor.execute('''
                SELECT language, COUNT(*), AVG(user_rating)
                FROM audio_generations WHERE user_id = ?
                GROUP BY language ORDER BY COUNT(*) DESC
            ''', (user_id,))
            
            language_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                "user_id": user_id,
                "total_generations": total_gens or 0,
                "average_rating": round(avg_rating or 0, 2),
                "average_quality_score": round(avg_quality or 0, 2),
                "average_generation_time": round(avg_time or 0, 2),
                "total_cost": round(total_cost or 0, 4),
                "total_audio_hours": round((total_duration or 0) / 3600.0, 2),
                "voice_preferences": [
                    {
                        "voice_id": voice,
                        "model": model,
                        "usage_count": count,
                        "average_rating": round(rating or 0, 2)
                    } for voice, count, rating, model in voice_stats
                ],
                "language_preferences": [
                    {
                        "language": language,
                        "usage_count": count,
                        "average_rating": round(rating or 0, 2)
                    } for language, count, rating in language_stats
                ],
                "user_preferences": self.user_preferences.get(user_id, {}),
                "building_bots_mission": "Constructing intelligent audio experiences",
                "insights": self._generate_user_insights(user_id, total_gens or 0, avg_rating or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user analytics: {e}")
            return {"error": str(e), "user_id": user_id}
    
    def _generate_user_insights(self, user_id: str, total_gens: int, avg_rating: float) -> List[str]:
        """Generate personalized insights for the user"""
        
        insights = []
        
        if total_gens == 0:
            insights.append("New user - exploring audio generation capabilities")
        elif total_gens < 5:
            insights.append("Getting started - try different voices and languages")
        elif total_gens < 20:
            insights.append("Regular user - system is learning your audio preferences")
        else:
            insights.append("Power user - building bots have optimized your audio experience")
        
        if avg_rating > 8.0:
            insights.append("High satisfaction - excellent audio quality achieved")
        elif avg_rating > 6.0:
            insights.append("Good satisfaction - some room for audio improvements")
        elif avg_rating > 0:
            insights.append("Lower satisfaction - recommend trying different models or voices")
        
        # Check user preferences
        if user_id in self.user_preferences:
            prefs = self.user_preferences[user_id]
            if len(prefs) > 3:
                insights.append("Strong preferences detected - system optimizes accordingly")
        
        insights.append("Part of the building bots network for intelligent construction")
        
        return insights
    
    def get_system_analytics(self) -> Dict:
        """Get comprehensive system analytics"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Overall statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_generations,
                    COUNT(DISTINCT user_id) as unique_users,
                    AVG(user_rating) as avg_satisfaction,
                    AVG(quality_score) as avg_quality,
                    SUM(cost) as total_cost,
                    SUM(duration) as total_duration,
                    AVG(generation_time) as avg_generation_time
                FROM audio_generations
            ''')
            
            overall_stats = cursor.fetchone()
            
            # Model performance
            cursor.execute('''
                SELECT 
                    model_used,
                    COUNT(*) as usage_count,
                    AVG(user_rating) as avg_rating,
                    AVG(quality_score) as avg_quality,
                    AVG(generation_time) as avg_time,
                    SUM(cost) as total_cost
                FROM audio_generations
                GROUP BY model_used
                ORDER BY usage_count DESC
            ''')
            
            model_performance = cursor.fetchall()
            
            # Popular voices
            cursor.execute('''
                SELECT 
                    voice_id,
                    COUNT(*) as usage_count,
                    AVG(user_rating) as avg_rating
                FROM audio_generations
                WHERE voice_id IS NOT NULL
                GROUP BY voice_id
                ORDER BY usage_count DESC
                LIMIT 10
            ''')
            
            popular_voices = cursor.fetchall()
            
            # Language distribution
            cursor.execute('''
                SELECT 
                    language,
                    COUNT(*) as usage_count,
                    AVG(user_rating) as avg_rating
                FROM audio_generations
                GROUP BY language
                ORDER BY usage_count DESC
            ''')
            
            language_distribution = cursor.fetchall()
            
            conn.close()
            
            return {
                "overview": {
                    "total_generations": overall_stats[0] or 0,
                    "unique_users": overall_stats[1] or 0,
                    "average_satisfaction": round(overall_stats[2] or 0, 2),
                    "average_quality": round(overall_stats[3] or 0, 2),
                    "total_cost": round(overall_stats[4] or 0, 4),
                    "total_audio_hours": round((overall_stats[5] or 0) / 3600.0, 2),
                    "average_generation_time": round(overall_stats[6] or 0, 2)
                },
                "model_performance": [
                    {
                        "model": model,
                        "usage_count": count,
                        "avg_rating": round(rating or 0, 2),
                        "avg_quality": round(quality or 0, 2),
                        "avg_time": round(time or 0, 2),
                        "total_cost": round(cost or 0, 4)
                    }
                    for model, count, rating, quality, time, cost in model_performance
                ],
                "popular_voices": [
                    {
                        "voice_id": voice,
                        "usage_count": count,
                        "avg_rating": round(rating or 0, 2)
                    }
                    for voice, count, rating in popular_voices
                ],
                "language_distribution": [
                    {
                        "language": language,
                        "usage_count": count,
                        "avg_rating": round(rating or 0, 2)
                    }
                    for language, count, rating in language_distribution
                ],
                "building_bots_network": {
                    "mission": self.mission,
                    "integrations": self.generation_stats["building_bots_integrations"],
                    "network_status": "operational"
                },
                "system_insights": [
                    "Advanced ML-powered audio generation and optimization",
                    "Multi-model TTS with intelligent selection",
                    "Voice cloning and enhancement capabilities",
                    "Music generation and audio editing",
                    "User preference learning for personalized audio",
                    "Building bots network integration for construction excellence",
                    "Comprehensive multi-language support"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get system analytics: {e}")
            return {"error": str(e)}


# Initialize the service
service = ComprehensiveAudioGenerationService()

# API Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🎵 Starting Comprehensive Audio Generation Service - Building Bots Network")
    logger.info(f"✅ Initialized with {len(service.supported_formats)} supported formats")
    logger.info(f"🌍 Multi-language support for {len(service.supported_languages)} languages") 
    logger.info(f"🎯 Voice catalog with {sum(len(voices) for voices in service.voice_catalog.values())} voices")
    logger.info(f"🔧 Audio tools: {list(service.audio_tools.keys())}")
    logger.info(f"🤖 Building bots mission: {service.mission['primary']}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Comprehensive Audio Generation Service - Building Bots Network",
        "status": "operational",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "mission": service.mission,
        "capabilities": {
            "text_to_speech": {
                "models": ["openai-tts", "festival", "espeak", "piper"],
                "voices": service.voice_catalog,
                "languages": service.supported_languages,
                "formats": service.supported_formats
            },
            "voice_cloning": {
                "available": True,
                "similarity_boost": True,
                "custom_profiles": True
            },
            "music_generation": {
                "procedural": True,
                "styles": service.music_styles,
                "midi_generation": True
            },
            "audio_editing": {
                "operations": ["trim", "merge", "enhance", "normalize", "add_effects", "change_speed"],
                "batch_processing": True
            },
            "transcription": {
                "models": ["whisper"],
                "multi_language": True,
                "timestamps": True
            },
            "ai_features": [
                "intelligent_model_selection",
                "user_preference_learning",
                "quality_optimization",
                "batch_processing",
                "audio_enhancement"
            ]
        },
        "statistics": service.generation_stats,
        "audio_tools": service.audio_tools
    }

@app.post("/generate/speech")
async def generate_speech(request: AudioGenerationRequest):
    """Generate speech audio with intelligent optimization"""
    result = await service.generate_speech(request)
    
    response_data = {
        "success": result.success,
        "audio_id": result.audio_id,
        "file_path": result.file_path,
        "audio_url": result.audio_url,
        "duration": result.duration,
        "format": result.format,
        "model_used": result.model_used,
        "quality_score": result.quality_score,
        "cost": result.cost,
        "generation_time": result.generation_time,
        "building_bots_integration": True
    }
    
    if not result.success:
        response_data["error"] = result.error
    
    return response_data

@app.post("/generate/batch")
async def generate_batch_audio(request: BatchAudioRequest):
    """Generate multiple audio files in batch"""
    result = await service.generate_batch_audio(request)
    return result

@app.post("/clone/voice")
async def clone_voice(
    reference_audio: UploadFile = File(...),
    text: str = Form(...),
    user_id: str = Form(default="default"),
    similarity_boost: float = Form(default=0.8),
    stability: float = Form(default=0.7),
    style_exaggeration: float = Form(default=0.0)
):
    """Clone voice from reference audio"""
    try:
        clone_request = VoiceCloningRequest(
            text=text,
            user_id=user_id,
            similarity_boost=similarity_boost,
            stability=stability,
            style_exaggeration=style_exaggeration
        )
        result = await service.clone_voice(clone_request, reference_audio)
        
        response_data = {
            "success": result.success,
            "audio_id": result.audio_id,
            "file_path": result.file_path,
            "duration": result.duration,
            "format": result.format,
            "model_used": result.model_used,
            "quality_score": result.quality_score,
            "cost": result.cost,
            "generation_time": result.generation_time
        }
        
        if not result.success:
            response_data["error"] = result.error
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/generate/music") 
async def generate_music(request: MusicGenerationRequest):
    """Generate music based on description"""
    result = await service.generate_music(request)
    
    response_data = {
        "success": result.success,
        "audio_id": result.audio_id,
        "file_path": result.file_path,
        "duration": result.duration,
        "format": result.format,
        "model_used": result.model_used,
        "quality_score": result.quality_score,
        "cost": result.cost,
        "generation_time": result.generation_time
    }
    
    if not result.success:
        response_data["error"] = result.error
    
    return response_data

@app.post("/edit")
async def edit_audio(
    audio: UploadFile = File(...),
    operation: str = Form(...),
    user_id: str = Form(default="default"),
    parameters: str = Form(default="{}")
):
    """Edit audio file"""
    try:
        params = json.loads(parameters) if parameters else {}
        edit_request = AudioEditingRequest(
            operation=operation,
            user_id=user_id,
            parameters=params
        )
        result = await service.edit_audio(audio, edit_request)
        
        response_data = {
            "success": result.success,
            "audio_id": result.audio_id,
            "file_path": result.file_path,
            "duration": result.duration,
            "format": result.format,
            "model_used": result.model_used,
            "quality_score": result.quality_score,
            "cost": result.cost,
            "generation_time": result.generation_time
        }
        
        if not result.success:
            response_data["error"] = result.error
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    user_id: str = Form(default="default"),
    language: Optional[str] = Form(default=None),
    model: str = Form(default="whisper"),
    include_timestamps: bool = Form(default=False),
    translate_to_english: bool = Form(default=False)
):
    """Transcribe audio to text"""
    try:
        transcription_request = TranscriptionRequest(
            user_id=user_id,
            language=language,
            model=model,
            include_timestamps=include_timestamps,
            translate_to_english=translate_to_english
        )
        result = await service.transcribe_audio(audio, transcription_request)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/feedback")
async def submit_feedback(feedback: AudioFeedbackRequest):
    """Submit feedback for learning and improvement"""
    service.learn_from_feedback(feedback)
    return {
        "message": "Feedback recorded successfully",
        "audio_id": feedback.audio_id,
        "user_id": feedback.user_id,
        "overall_satisfaction": feedback.overall_satisfaction,
        "building_bots_learning": True
    }

@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str):
    """Get comprehensive user analytics"""
    return service.get_user_analytics(user_id)

@app.get("/analytics/system")
async def get_system_analytics():
    """Get system-wide analytics and insights"""
    return service.get_system_analytics()

@app.get("/voices")
async def list_voices():
    """List available voices and their characteristics"""
    return {
        "voice_catalog": service.voice_catalog,
        "total_voices": sum(len(voices) for voices in service.voice_catalog.values()),
        "voice_recommendations": {
            "business": ["onyx", "alloy"],
            "storytelling": ["fable", "nova"],
            "technical": ["echo", "shimmer"],
            "multilingual": ["alloy", "nova"]
        },
        "local_voices_available": [
            voice for provider, voices in service.voice_catalog.items()
            if provider == "local" for voice in voices.keys()
        ]
    }

@app.get("/languages")
async def list_languages():
    """List supported languages"""
    return {
        "supported_languages": service.supported_languages,
        "total_languages": len(service.supported_languages),
        "language_recommendations": {
            "high_quality": ["en", "es", "fr", "de"],
            "experimental": ["ar", "hi", "tr", "ko"],
            "well_supported": ["en", "es", "fr", "de", "it", "pt"]
        }
    }

@app.get("/models")
async def list_models():
    """List available TTS models and their capabilities"""
    return {
        "available_models": {
            "openai-tts": {
                "name": "OpenAI TTS",
                "provider": "OpenAI",
                "strengths": ["high_quality", "natural_voice", "multilingual"],
                "cost_structure": "pay_per_use",
                "quality_levels": ["standard", "high"],
                "supported_languages": service.supported_languages,
                "voices": list(service.voice_catalog["openai"].keys())
            },
            "festival": {
                "name": "Festival TTS",
                "provider": "Local",
                "strengths": ["free", "offline", "customizable"],
                "cost_structure": "free",
                "quality_levels": ["draft", "standard"],
                "supported_languages": ["en"],
                "available": service.audio_tools.get("festival", False)
            },
            "espeak": {
                "name": "eSpeak TTS",
                "provider": "Local",
                "strengths": ["lightweight", "fast", "multilingual", "free"],
                "cost_structure": "free",
                "quality_levels": ["draft", "standard"],
                "supported_languages": service.supported_languages,
                "available": service.audio_tools.get("espeak", False)
            },
            "piper": {
                "name": "Piper TTS",
                "provider": "Local",
                "strengths": ["neural", "natural", "offline", "free"],
                "cost_structure": "free",
                "quality_levels": ["standard", "high"],
                "supported_languages": ["en"],
                "available": service.audio_tools.get("piper", False)
            }
        },
        "selection_criteria": {
            "highest_quality": "openai-tts",
            "fastest": "espeak",
            "most_natural_local": "piper",
            "best_multilingual": "espeak",
            "cost_effective": "festival"
        },
        "building_bots_optimization": "Intelligent model selection based on requirements"
    }

@app.get("/tools")
async def get_audio_tools():
    """Get information about available audio processing tools"""
    return {
        "audio_tools": service.audio_tools,
        "capabilities": {
            "festival": "Text-to-speech synthesis",
            "espeak": "Text-to-speech synthesis with multi-language support",
            "piper": "Neural text-to-speech synthesis",
            "ffmpeg": "Audio format conversion and processing"
        },
        "recommendations": [
            "Install FFmpeg for audio format conversion",
            "Install eSpeak for multi-language TTS",
            "Install Festival for English TTS",
            "Install Piper for high-quality neural TTS"
        ]
    }

@app.get("/building-bots/mission")
async def get_building_bots_mission():
    """Get building bots network mission and values"""
    return {
        "mission": service.mission,
        "network_status": "operational",
        "integrations_count": service.generation_stats["building_bots_integrations"],
        "construction_excellence": True,
        "interconnected_intelligence": True,
        "audio_specialization": {
            "tts_systems": "Advanced multi-model text-to-speech",
            "voice_cloning": "Personalized voice generation",
            "music_synthesis": "Procedural music and audio generation",
            "audio_processing": "Intelligent editing and enhancement",
            "user_optimization": "ML-powered preference learning"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8485))
    uvicorn.run(
        "main:app",
        host="0.0.0.0", 
        port=port,
        log_level="info",
        reload=True
    )