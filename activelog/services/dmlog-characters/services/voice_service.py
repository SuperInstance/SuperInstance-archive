"""
Voice synthesis and audio processing service.
"""

import os
import asyncio
import tempfile
import hashlib
from typing import Optional, Dict, List, Any, Tuple
from uuid import uuid4
from datetime import datetime
import numpy as np
import torch
import librosa
import soundfile as sf
from pydub import AudioSegment
from sqlalchemy.orm import Session

# Voice synthesis imports
try:
    from TTS.api import TTS
    from TTS.utils.synthesizer import Synthesizer
except ImportError:
    print("Warning: TTS library not available. Voice synthesis will be limited.")

from ..models.voice import (
    VoiceProfile, VoiceClone, VoiceSynthesisJob, SpeechSample,
    VoiceProfileSchema, VoiceCloneSchema, VoiceSynthesisRequest,
    VoiceSynthesisResponse, VoiceAnalysis, VoiceParameters,
    EmotionalVoiceModifiers
)
from ..models.base import EmotionType, VoiceGender, AccentType, SpeechPattern
from ..config import settings

class VoiceAnalyzer:
    """Analyzes audio characteristics for voice profiling."""
    
    @staticmethod
    def analyze_audio(audio_path: str) -> VoiceAnalysis:
        """Analyze audio file for voice characteristics."""
        # Load audio
        y, sr = librosa.load(audio_path, sr=None)
        
        # Extract features
        fundamental_freq = float(np.mean(librosa.yin(y, fmin=50, fmax=500)))
        
        # Formant analysis (simplified)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        formant_frequencies = [float(f) for f in np.mean(mfccs[1:4], axis=1) * 1000]
        
        # Spectral features
        spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        zero_crossing_rate = float(np.mean(librosa.feature.zero_crossing_rate(y)))
        
        # MFCC features
        mfcc_features = [float(f) for f in np.mean(mfccs, axis=1)]
        
        # Pitch variability
        pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
        pitch_values = []
        for t in range(pitches.shape[1]):
            index = magnitudes[:, t].argmax()
            pitch = pitches[index, t]
            if pitch > 0:
                pitch_values.append(pitch)
        
        pitch_variability = float(np.std(pitch_values)) if pitch_values else 0.0
        
        # Speaking rate estimation
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        speaking_rate = float(tempo / 60)  # Convert to Hz
        
        # Pause detection
        rms = librosa.feature.rms(y=y)[0]
        silence_threshold = np.percentile(rms, 20)
        silent_frames = rms < silence_threshold
        
        pause_patterns = []
        in_pause = False
        pause_start = 0
        
        for i, is_silent in enumerate(silent_frames):
            if is_silent and not in_pause:
                in_pause = True
                pause_start = i
            elif not is_silent and in_pause:
                in_pause = False
                pause_duration = (i - pause_start) * 512 / sr  # Frame size 512
                if pause_duration > 0.1:  # Only record pauses > 100ms
                    pause_patterns.append({
                        "start_time": pause_start * 512 / sr,
                        "duration": pause_duration
                    })
        
        # Emotional indicators (basic)
        emotional_indicators = {
            "energy": float(np.mean(rms)),
            "brightness": float(spectral_centroid / sr * 2),
            "stability": 1.0 - (pitch_variability / fundamental_freq) if fundamental_freq > 0 else 0.0
        }
        
        return VoiceAnalysis(
            fundamental_frequency=fundamental_freq,
            formant_frequencies=formant_frequencies,
            spectral_centroid=spectral_centroid,
            zero_crossing_rate=zero_crossing_rate,
            mfcc_features=mfcc_features,
            pitch_variability=pitch_variability,
            speaking_rate=speaking_rate,
            pause_patterns=pause_patterns,
            emotional_indicators=emotional_indicators
        )
    
    @staticmethod
    def detect_characteristics(audio_path: str) -> Dict[str, Any]:
        """Detect gender, age, accent from audio."""
        analysis = VoiceAnalyzer.analyze_audio(audio_path)
        
        characteristics = {}
        
        # Gender detection (simplified heuristic)
        if analysis.fundamental_frequency > 180:
            characteristics["gender"] = VoiceGender.FEMALE
        elif analysis.fundamental_frequency < 120:
            characteristics["gender"] = VoiceGender.MALE
        else:
            characteristics["gender"] = VoiceGender.NEUTRAL
        
        # Age estimation (very simplified)
        if analysis.fundamental_frequency > 250:
            characteristics["age"] = 20  # Young
        elif analysis.fundamental_frequency < 90:
            characteristics["age"] = 60  # Older
        else:
            characteristics["age"] = 35  # Adult
        
        # Accent detection would require trained models
        characteristics["accent"] = AccentType.AMERICAN_WEST  # Default
        
        # Voice qualities
        characteristics["vocal_qualities"] = {
            "breathiness": min(1.0, analysis.emotional_indicators["energy"] * 2),
            "roughness": min(1.0, analysis.pitch_variability / 50),
            "brightness": analysis.emotional_indicators["brightness"]
        }
        
        return characteristics

class VoiceSynthesizer:
    """Handles voice synthesis using various TTS engines."""
    
    def __init__(self):
        self.tts = None
        self.model_cache = {}
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize TTS models."""
        try:
            # Initialize default TTS model
            self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", 
                          progress_bar=False, gpu=torch.cuda.is_available())
        except Exception as e:
            print(f"Warning: Could not initialize TTS model: {e}")
            self.tts = None
    
    async def synthesize_speech(self, 
                              text: str, 
                              voice_profile: VoiceProfileSchema,
                              parameters: Optional[VoiceParameters] = None,
                              emotion: Optional[EmotionType] = None) -> str:
        """Synthesize speech with given parameters."""
        
        if not self.tts:
            raise RuntimeError("TTS engine not available")
        
        # Apply emotional modifiers if specified
        if emotion and parameters is None:
            parameters = self._get_emotional_voice_parameters(emotion, voice_profile)
        elif parameters is None:
            parameters = VoiceParameters()
        
        # Create temporary output file
        output_path = os.path.join(tempfile.gettempdir(), f"speech_{uuid4().hex}.wav")
        
        try:
            # Apply accent and speech pattern modifications to text
            modified_text = self._apply_speech_patterns(text, voice_profile)
            
            # Synthesize using TTS
            self.tts.tts_to_file(
                text=modified_text,
                file_path=output_path,
                speaker_wav=voice_profile.model_path if voice_profile.model_type == "cloned" else None
            )
            
            # Post-process audio with parameters
            processed_path = await self._post_process_audio(
                output_path, parameters, voice_profile
            )
            
            return processed_path
            
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise RuntimeError(f"Speech synthesis failed: {e}")
    
    def _apply_speech_patterns(self, text: str, voice_profile: VoiceProfileSchema) -> str:
        """Apply speech pattern modifications to text."""
        modified_text = text
        
        # Apply accent-specific modifications
        if voice_profile.accent == AccentType.BRITISH:
            modified_text = modified_text.replace("can't", "cannot")
            modified_text = modified_text.replace("won't", "will not")
        elif voice_profile.accent == AccentType.SCOTTISH:
            modified_text = modified_text.replace("you", "ye")
            modified_text = modified_text.replace("from", "frae")
        elif voice_profile.accent == AccentType.FANTASY_ELVISH:
            modified_text = modified_text.replace("magic", "magick")
            modified_text = modified_text.replace("forest", "woodland")
        elif voice_profile.accent == AccentType.FANTASY_DWARVEN:
            modified_text = modified_text.replace("gold", "goold")
            modified_text = modified_text.replace("mountain", "mount'n")
        
        # Apply speech pattern modifications
        if voice_profile.speech_pattern == SpeechPattern.ARCHAIC:
            modified_text = modified_text.replace("you", "thou")
            modified_text = modified_text.replace("your", "thy")
            modified_text = modified_text.replace("are", "art")
        elif voice_profile.speech_pattern == SpeechPattern.FORMAL:
            modified_text = modified_text.replace("don't", "do not")
            modified_text = modified_text.replace("won't", "will not")
            modified_text = modified_text.replace("can't", "cannot")
        
        # Add speech quirks
        if voice_profile.speech_quirks:
            quirks = voice_profile.speech_quirks
            
            # Add filler words
            if "filler_words" in quirks:
                import random
                words = modified_text.split()
                for i in range(len(words)):
                    if random.random() < quirks.get("filler_frequency", 0.05):
                        filler = random.choice(quirks["filler_words"])
                        words.insert(i, filler)
                modified_text = " ".join(words)
            
            # Add pronunciation variants
            if "pronunciation_variants" in quirks:
                for original, variant in quirks["pronunciation_variants"].items():
                    modified_text = modified_text.replace(original, variant)
        
        return modified_text
    
    async def _post_process_audio(self, 
                                audio_path: str, 
                                parameters: VoiceParameters,
                                voice_profile: VoiceProfileSchema) -> str:
        """Post-process synthesized audio with parameters."""
        
        # Load audio
        audio = AudioSegment.from_wav(audio_path)
        
        # Apply pitch modification
        if parameters.pitch != 1.0:
            # Simple pitch shifting (not perfect but functional)
            new_sample_rate = int(audio.frame_rate * parameters.pitch)
            audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
            audio = audio.set_frame_rate(22050)
        
        # Apply speed modification
        if parameters.speed != 1.0:
            # Change playback speed
            audio = audio.speedup(playback_speed=parameters.speed)
        
        # Apply volume modification
        if parameters.volume != 1.0:
            volume_change = 20 * np.log10(parameters.volume)  # Convert to dB
            audio = audio + volume_change
        
        # Apply emotional modifications based on voice profile
        if voice_profile.emotional_range:
            emotion_str = parameters.emotion.value if parameters.emotion else "neutral"
            if emotion_str in voice_profile.emotional_range:
                emotion_params = voice_profile.emotional_range[emotion_str]
                # Apply additional emotional processing
                pass
        
        # Add pauses for emphasis
        if parameters.emphasis_words:
            # This would require more sophisticated text-to-audio alignment
            pass
        
        # Save processed audio
        output_path = os.path.join(tempfile.gettempdir(), f"processed_{uuid4().hex}.wav")
        audio.export(output_path, format="wav")
        
        # Clean up original file
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        return output_path
    
    def _get_emotional_voice_parameters(self, 
                                      emotion: EmotionType, 
                                      voice_profile: VoiceProfileSchema) -> VoiceParameters:
        """Get voice parameters for a specific emotion."""
        modifiers = EmotionalVoiceModifiers()
        
        base_params = VoiceParameters(
            pitch=voice_profile.base_pitch,
            speed=voice_profile.base_speed,
            volume=voice_profile.base_volume,
            emotion=emotion
        )
        
        if emotion == EmotionType.JOY:
            emotion_params = modifiers.joy
        elif emotion == EmotionType.ANGER:
            emotion_params = modifiers.anger
        elif emotion == EmotionType.FEAR:
            emotion_params = modifiers.fear
        elif emotion == EmotionType.SADNESS:
            emotion_params = modifiers.sadness
        elif emotion == EmotionType.SURPRISE:
            emotion_params = modifiers.surprise
        elif emotion == EmotionType.DISGUST:
            emotion_params = modifiers.disgust
        elif emotion == EmotionType.TRUST:
            emotion_params = modifiers.trust
        elif emotion == EmotionType.ANTICIPATION:
            emotion_params = modifiers.anticipation
        else:
            return base_params
        
        # Combine base parameters with emotional modifiers
        return VoiceParameters(
            pitch=base_params.pitch * emotion_params.pitch,
            speed=base_params.speed * emotion_params.speed,
            volume=base_params.volume * emotion_params.volume,
            emotion=emotion,
            pause_duration=emotion_params.pause_duration
        )

class VoiceCloneTrainer:
    """Handles voice cloning model training."""
    
    def __init__(self):
        self.training_jobs = {}
    
    async def start_training(self, 
                           clone_request: VoiceCloneSchema, 
                           db: Session) -> str:
        """Start voice cloning training process."""
        
        job_id = str(uuid4())
        
        # Validate source audio
        if not os.path.exists(clone_request.source_audio_path):
            raise FileNotFoundError("Source audio file not found")
        
        # Analyze source audio
        characteristics = VoiceAnalyzer.detect_characteristics(clone_request.source_audio_path)
        
        # Update clone record with detected characteristics
        clone_record = db.query(VoiceClone).filter(VoiceClone.id == clone_request.id).first()
        if clone_record:
            clone_record.detected_gender = characteristics.get("gender")
            clone_record.detected_age = characteristics.get("age")
            clone_record.detected_accent = characteristics.get("accent")
            clone_record.voice_characteristics = characteristics.get("vocal_qualities")
            clone_record.training_status = "training"
            clone_record.training_started_at = datetime.utcnow()
            db.commit()
        
        # Start training in background
        asyncio.create_task(self._train_voice_clone(job_id, clone_request, db))
        
        return job_id
    
    async def _train_voice_clone(self, 
                               job_id: str, 
                               clone_request: VoiceCloneSchema,
                               db: Session):
        """Train voice cloning model (simplified simulation)."""
        
        try:
            # This is a simplified simulation of voice cloning training
            # In a real implementation, this would involve:
            # 1. Preprocessing the audio data
            # 2. Training a speaker embedding model
            # 3. Fine-tuning a TTS model on the speaker's voice
            
            clone_record = db.query(VoiceClone).filter(VoiceClone.id == clone_request.id).first()
            
            # Simulate training progress
            for progress in range(0, 101, 10):
                await asyncio.sleep(1)  # Simulate training time
                
                if clone_record:
                    clone_record.training_progress = progress / 100.0
                    db.commit()
            
            # Simulate model creation
            model_path = os.path.join(settings.VOICE_MODEL_PATH, f"clone_{clone_request.id}.pth")
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Create dummy model file
            torch.save({"model": "dummy"}, model_path)
            
            # Calculate quality score (simulated)
            quality_score = min(0.95, max(0.6, 0.8 + np.random.normal(0, 0.1)))
            
            # Update clone record
            if clone_record:
                clone_record.training_status = "completed"
                clone_record.training_progress = 1.0
                clone_record.model_path = model_path
                clone_record.model_quality_score = quality_score
                clone_record.model_size_bytes = os.path.getsize(model_path)
                clone_record.training_completed_at = datetime.utcnow()
                db.commit()
            
        except Exception as e:
            # Handle training failure
            clone_record = db.query(VoiceClone).filter(VoiceClone.id == clone_request.id).first()
            if clone_record:
                clone_record.training_status = "failed"
                clone_record.training_logs = str(e)
                db.commit()

class VoiceService:
    """Main voice service orchestrating all voice-related functionality."""
    
    def __init__(self):
        self.synthesizer = VoiceSynthesizer()
        self.analyzer = VoiceAnalyzer()
        self.clone_trainer = VoiceCloneTrainer()
    
    def create_voice_profile(self, profile_data: VoiceProfileSchema, db: Session) -> VoiceProfile:
        """Create a new voice profile."""
        
        profile = VoiceProfile(
            id=str(uuid4()),
            character_id=profile_data.character_id,
            name=profile_data.name,
            gender=profile_data.gender.value,
            accent=profile_data.accent.value,
            speech_pattern=profile_data.speech_pattern.value,
            base_pitch=profile_data.base_pitch,
            base_speed=profile_data.base_speed,
            base_volume=profile_data.base_volume,
            voice_age=profile_data.voice_age,
            vocal_qualities=profile_data.vocal_qualities,
            emotional_range=profile_data.emotional_range,
            speech_quirks=profile_data.speech_quirks,
            model_type=profile_data.model_type
        )
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
        return profile
    
    async def synthesize_speech(self, 
                              request: VoiceSynthesisRequest, 
                              db: Session) -> VoiceSynthesisResponse:
        """Synthesize speech for a character."""
        
        # Get voice profile
        profile = db.query(VoiceProfile).filter(
            VoiceProfile.character_id == request.character_id
        ).first()
        
        if not profile:
            raise ValueError("No voice profile found for character")
        
        # Create synthesis job
        job = VoiceSynthesisJob(
            id=str(uuid4()),
            character_id=request.character_id,
            voice_profile_id=profile.id,
            text=request.text,
            synthesis_parameters=request.voice_parameters.dict() if request.voice_parameters else {},
            context_data=request.context_data,
            status="processing"
        )
        
        db.add(job)
        db.commit()
        
        try:
            # Convert to schema
            profile_schema = VoiceProfileSchema.from_orm(profile)
            
            # Synthesize speech
            start_time = datetime.utcnow()
            audio_path = await self.synthesizer.synthesize_speech(
                request.text,
                profile_schema,
                request.voice_parameters,
                request.voice_parameters.emotion if request.voice_parameters else None
            )
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Get audio duration
            audio = AudioSegment.from_wav(audio_path)
            duration_seconds = len(audio) / 1000.0
            
            # Update job
            job.status = "completed"
            job.output_path = audio_path
            job.duration_seconds = duration_seconds
            job.processing_time_seconds = processing_time
            job.file_size_bytes = os.path.getsize(audio_path)
            
            # Update profile statistics
            profile.generation_count += 1
            profile.total_duration_seconds += duration_seconds
            
            db.commit()
            
            return VoiceSynthesisResponse(
                job_id=job.id,
                status="completed",
                audio_url=f"/audio/{os.path.basename(audio_path)}",
                duration_seconds=duration_seconds,
                processing_time=processing_time
            )
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
            
            return VoiceSynthesisResponse(
                job_id=job.id,
                status="failed"
            )
    
    async def create_voice_clone(self, 
                               clone_data: VoiceCloneSchema, 
                               db: Session) -> VoiceClone:
        """Create and train a voice clone."""
        
        clone = VoiceClone(
            id=str(uuid4()),
            character_id=clone_data.character_id,
            name=clone_data.name,
            source_audio_path=clone_data.source_audio_path,
            audio_duration_seconds=clone_data.audio_duration_seconds,
            sample_rate=clone_data.sample_rate,
            audio_format=clone_data.audio_format
        )
        
        db.add(clone)
        db.commit()
        db.refresh(clone)
        
        # Start training
        clone_schema = VoiceCloneSchema.from_orm(clone)
        await self.clone_trainer.start_training(clone_schema, db)
        
        return clone
    
    def get_voice_profile(self, character_id: str, db: Session) -> Optional[VoiceProfile]:
        """Get voice profile for a character."""
        return db.query(VoiceProfile).filter(
            VoiceProfile.character_id == character_id
        ).first()
    
    def list_voice_profiles(self, db: Session, skip: int = 0, limit: int = 100) -> List[VoiceProfile]:
        """List all voice profiles."""
        return db.query(VoiceProfile).offset(skip).limit(limit).all()
    
    def analyze_voice_sample(self, audio_path: str) -> VoiceAnalysis:
        """Analyze a voice sample."""
        return self.analyzer.analyze_audio(audio_path)