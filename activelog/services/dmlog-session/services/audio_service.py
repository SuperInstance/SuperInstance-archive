"""
Audio recording service with speaker identification.
"""

import asyncio
import numpy as np
import librosa
import soundfile as sf
import webrtcvad
import logging
from typing import Dict, List, Optional, Tuple, Any, AsyncIterator
from datetime import datetime, timedelta
import uuid
import os
import json
from pathlib import Path
import threading
from queue import Queue
import wave

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("PyAudio not available - audio recording disabled")

try:
    from pyannote.audio import Pipeline
    from speechbrain.pretrained import EncoderClassifier
    SPEAKER_ID_AVAILABLE = True
except ImportError:
    SPEAKER_ID_AVAILABLE = False
    logging.warning("Speaker identification libraries not available")

from ..config import Config
from ..models.base import (
    AudioSegment, SpeakerProfile, AudioQuality, SessionStatus
)
from ..models.session import SessionSchema, SessionParticipant

logger = logging.getLogger(__name__)

class AudioBuffer:
    """Thread-safe audio buffer for real-time processing."""
    
    def __init__(self, max_size: int = 1000):
        self.buffer = Queue(maxsize=max_size)
        self.lock = threading.Lock()
        
    def put(self, audio_data: np.ndarray, timestamp: float) -> None:
        """Add audio data to buffer."""
        try:
            self.buffer.put_nowait((audio_data, timestamp))
        except:
            # Buffer full - remove oldest and add new
            try:
                self.buffer.get_nowait()
                self.buffer.put_nowait((audio_data, timestamp))
            except:
                pass
    
    def get(self) -> Optional[Tuple[np.ndarray, float]]:
        """Get audio data from buffer."""
        try:
            return self.buffer.get_nowait()
        except:
            return None
    
    def empty(self) -> bool:
        """Check if buffer is empty."""
        return self.buffer.empty()

class VoiceActivityDetector:
    """Voice activity detection using WebRTC VAD."""
    
    def __init__(self, sample_rate: int = 16000, mode: int = 3):
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad(mode)  # Mode 3 = most aggressive
        self.frame_duration = 30  # ms
        self.frame_size = int(sample_rate * self.frame_duration / 1000)
        
    def is_speech(self, audio_data: np.ndarray) -> bool:
        """Detect if audio contains speech."""
        if len(audio_data) < self.frame_size:
            return False
        
        # Convert to 16-bit PCM
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Check multiple frames
        speech_frames = 0
        total_frames = 0
        
        for i in range(0, len(audio_int16) - self.frame_size, self.frame_size):
            frame = audio_int16[i:i + self.frame_size].tobytes()
            if self.vad.is_speech(frame, self.sample_rate):
                speech_frames += 1
            total_frames += 1
        
        # Return True if more than 50% of frames contain speech
        return total_frames > 0 and (speech_frames / total_frames) > 0.5

class SpeakerIdentificationService:
    """Speaker identification and diarization service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.speaker_profiles: Dict[str, SpeakerProfile] = {}
        self.embedding_model = None
        self.diarization_pipeline = None
        
        if SPEAKER_ID_AVAILABLE:
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize speaker identification models."""
        try:
            # Initialize speaker embedding model
            model_name = self.config.SPEAKER_CONFIG["embedding_model"]
            self.embedding_model = EncoderClassifier.from_hparams(source=model_name)
            
            # Initialize diarization pipeline
            self.diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
            
            logger.info("Speaker identification models initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize speaker identification models: {e}")
            SPEAKER_ID_AVAILABLE = False
    
    async def enroll_speaker(
        self,
        audio_data: np.ndarray,
        speaker_id: str,
        participant: SessionParticipant
    ) -> SpeakerProfile:
        """Enroll a new speaker or update existing profile."""
        
        if not SPEAKER_ID_AVAILABLE:
            # Create basic profile without embeddings
            profile = SpeakerProfile(
                speaker_id=speaker_id,
                name=participant.character_name or f"Player {participant.user_id}",
                player_id=participant.user_id,
                confidence=0.5
            )
            self.speaker_profiles[speaker_id] = profile
            return profile
        
        try:
            # Extract speaker embedding
            embedding = self._extract_embedding(audio_data)
            
            if speaker_id in self.speaker_profiles:
                # Update existing profile
                profile = self.speaker_profiles[speaker_id]
                profile.voice_embedding = self._update_embedding(
                    profile.voice_embedding, embedding
                )
                profile.sample_count += 1
                profile.confidence = min(1.0, profile.confidence + 0.1)
            else:
                # Create new profile
                profile = SpeakerProfile(
                    speaker_id=speaker_id,
                    name=participant.character_name or f"Player {participant.user_id}",
                    player_id=participant.user_id,
                    voice_embedding=embedding,
                    confidence=0.7,
                    sample_count=1
                )
            
            profile.last_updated = datetime.utcnow()
            self.speaker_profiles[speaker_id] = profile
            
            logger.info(f"Speaker {speaker_id} enrolled/updated")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to enroll speaker {speaker_id}: {e}")
            raise
    
    def identify_speaker(self, audio_data: np.ndarray) -> Tuple[Optional[str], float]:
        """Identify speaker from audio data."""
        
        if not SPEAKER_ID_AVAILABLE or not self.speaker_profiles:
            return None, 0.0
        
        try:
            # Extract embedding from audio
            embedding = self._extract_embedding(audio_data)
            
            best_match = None
            best_similarity = 0.0
            
            # Compare with all known speakers
            for speaker_id, profile in self.speaker_profiles.items():
                if profile.voice_embedding is None:
                    continue
                
                similarity = self._calculate_similarity(embedding, profile.voice_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = speaker_id
            
            # Check if similarity is above threshold
            threshold = self.config.SPEAKER_CONFIG["similarity_threshold"]
            if best_similarity >= threshold:
                return best_match, best_similarity
            else:
                return None, best_similarity
                
        except Exception as e:
            logger.error(f"Failed to identify speaker: {e}")
            return None, 0.0
    
    def _extract_embedding(self, audio_data: np.ndarray) -> List[float]:
        """Extract speaker embedding from audio."""
        if not SPEAKER_ID_AVAILABLE:
            return []
        
        # Resample if necessary
        if len(audio_data) < 16000:  # Minimum 1 second
            return []
        
        # Extract embedding using SpeechBrain
        waveform = audio_data.reshape(1, -1)  # Add batch dimension
        embeddings = self.embedding_model.encode_batch(waveform)
        
        return embeddings[0].squeeze().tolist()
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings."""
        if not embedding1 or not embedding2:
            return 0.0
        
        # Convert to numpy arrays
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(emb1, emb2)
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    def _update_embedding(
        self,
        old_embedding: List[float],
        new_embedding: List[float],
        alpha: float = 0.1
    ) -> List[float]:
        """Update speaker embedding with new sample."""
        if not old_embedding:
            return new_embedding
        
        # Exponential moving average
        old_array = np.array(old_embedding)
        new_array = np.array(new_embedding)
        
        updated = (1 - alpha) * old_array + alpha * new_array
        return updated.tolist()

class AudioRecordingService:
    """Main audio recording service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, 'SessionAudioRecorder'] = {}
        self.speaker_service = SpeakerIdentificationService(config)
        
    async def start_recording(self, session: SessionSchema) -> str:
        """Start recording for a session."""
        
        if session.id in self.sessions:
            raise ValueError(f"Recording already active for session {session.id}")
        
        recorder = SessionAudioRecorder(session, self.config, self.speaker_service)
        self.sessions[session.id] = recorder
        
        recording_id = await recorder.start()
        logger.info(f"Started recording for session {session.id}: {recording_id}")
        
        return recording_id
    
    async def stop_recording(self, session_id: str) -> Optional[str]:
        """Stop recording for a session."""
        
        if session_id not in self.sessions:
            return None
        
        recorder = self.sessions[session_id]
        file_path = await recorder.stop()
        
        del self.sessions[session_id]
        logger.info(f"Stopped recording for session {session_id}")
        
        return file_path
    
    async def pause_recording(self, session_id: str) -> bool:
        """Pause recording for a session."""
        
        if session_id not in self.sessions:
            return False
        
        return await self.sessions[session_id].pause()
    
    async def resume_recording(self, session_id: str) -> bool:
        """Resume recording for a session."""
        
        if session_id not in self.sessions:
            return False
        
        return await self.sessions[session_id].resume()
    
    def get_recording_status(self, session_id: str) -> Dict[str, Any]:
        """Get current recording status."""
        
        if session_id not in self.sessions:
            return {"active": False}
        
        return self.sessions[session_id].get_status()
    
    async def process_audio_stream(
        self,
        session_id: str,
        audio_data: bytes,
        participant_id: str
    ) -> Optional[AudioSegment]:
        """Process incoming audio stream data."""
        
        if session_id not in self.sessions:
            return None
        
        return await self.sessions[session_id].process_stream_data(
            audio_data, participant_id
        )

class SessionAudioRecorder:
    """Audio recorder for individual session."""
    
    def __init__(
        self,
        session: SessionSchema,
        config: Config,
        speaker_service: SpeakerIdentificationService
    ):
        self.session = session
        self.config = config
        self.speaker_service = speaker_service
        
        # Recording state
        self.recording_id = str(uuid.uuid4())
        self.is_recording = False
        self.is_paused = False
        self.start_time = None
        
        # Audio settings
        self.sample_rate = config.AUDIO_CONFIG["sample_rate"]
        self.channels = config.AUDIO_CONFIG["channels"]
        self.chunk_size = config.AUDIO_CONFIG["chunk_size"]
        
        # File paths
        self.storage_path = Path(config.SESSION_CONFIG["audio_path"])
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.master_file_path = self.storage_path / f"{session.id}_{self.recording_id}.wav"
        
        # Audio processing
        self.audio_buffer = AudioBuffer()
        self.vad = VoiceActivityDetector(self.sample_rate)
        self.audio_segments: List[AudioSegment] = []
        
        # Multi-participant recording
        self.participant_streams: Dict[str, List[np.ndarray]] = {}
        self.participant_files: Dict[str, str] = {}
        
        # Background processing
        self.processing_task = None
        self.should_stop = threading.Event()
        
        # PyAudio setup
        self.audio_interface = None
        self.audio_stream = None
        
        if PYAUDIO_AVAILABLE:
            self.audio_interface = pyaudio.PyAudio()
    
    async def start(self) -> str:
        """Start recording."""
        
        if self.is_recording:
            raise RuntimeError("Recording already active")
        
        self.start_time = datetime.utcnow()
        self.is_recording = True
        self.should_stop.clear()
        
        # Start audio capture if available
        if PYAUDIO_AVAILABLE and self.audio_interface:
            self._start_audio_stream()
        
        # Start background processing
        self.processing_task = asyncio.create_task(self._process_audio_loop())
        
        logger.info(f"Recording started: {self.recording_id}")
        return self.recording_id
    
    async def stop(self) -> str:
        """Stop recording and finalize files."""
        
        if not self.is_recording:
            return str(self.master_file_path)
        
        self.is_recording = False
        self.should_stop.set()
        
        # Stop audio stream
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            self.audio_stream = None
        
        # Wait for processing to complete
        if self.processing_task:
            await self.processing_task
        
        # Finalize recording files
        await self._finalize_recording()
        
        logger.info(f"Recording stopped: {self.recording_id}")
        return str(self.master_file_path)
    
    async def pause(self) -> bool:
        """Pause recording."""
        
        if not self.is_recording or self.is_paused:
            return False
        
        self.is_paused = True
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
        
        logger.info(f"Recording paused: {self.recording_id}")
        return True
    
    async def resume(self) -> bool:
        """Resume recording."""
        
        if not self.is_recording or not self.is_paused:
            return False
        
        self.is_paused = False
        
        if self.audio_stream and PYAUDIO_AVAILABLE:
            self.audio_stream.start_stream()
        
        logger.info(f"Recording resumed: {self.recording_id}")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get current recording status."""
        
        duration = 0
        if self.start_time:
            duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "active": self.is_recording,
            "paused": self.is_paused,
            "recording_id": self.recording_id,
            "duration": duration,
            "segments_count": len(self.audio_segments),
            "participants": list(self.participant_streams.keys()),
            "file_path": str(self.master_file_path) if self.master_file_path.exists() else None
        }
    
    async def process_stream_data(
        self,
        audio_data: bytes,
        participant_id: str
    ) -> Optional[AudioSegment]:
        """Process audio data from participant stream."""
        
        if not self.is_recording or self.is_paused:
            return None
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32767.0  # Normalize to [-1, 1]
            
            # Store for participant-specific file
            if participant_id not in self.participant_streams:
                self.participant_streams[participant_id] = []
            
            self.participant_streams[participant_id].append(audio_array)
            
            # Add to main buffer for processing
            timestamp = (datetime.utcnow() - self.start_time).total_seconds()
            self.audio_buffer.put(audio_array, timestamp)
            
            # Process for voice activity and speaker identification
            return await self._process_audio_chunk(audio_array, timestamp, participant_id)
            
        except Exception as e:
            logger.error(f"Error processing stream data: {e}")
            return None
    
    def _start_audio_stream(self):
        """Start PyAudio stream for local recording."""
        
        if not PYAUDIO_AVAILABLE:
            return
        
        try:
            self.audio_stream = self.audio_interface.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.audio_stream.start_stream()
            logger.info("Audio stream started")
            
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for local audio capture."""
        
        if self.is_recording and not self.is_paused:
            # Convert to numpy array
            audio_array = np.frombuffer(in_data, dtype=np.int16).astype(np.float32)
            audio_array = audio_array / 32767.0
            
            # Add to buffer
            timestamp = (datetime.utcnow() - self.start_time).total_seconds()
            self.audio_buffer.put(audio_array, timestamp)
        
        return (in_data, pyaudio.paContinue)
    
    async def _process_audio_loop(self):
        """Background audio processing loop."""
        
        while not self.should_stop.is_set():
            try:
                # Process buffered audio
                await self._process_buffer()
                
                # Brief pause to avoid overwhelming CPU
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}")
        
        # Final buffer processing
        await self._process_buffer()
        logger.info("Audio processing loop stopped")
    
    async def _process_buffer(self):
        """Process audio buffer for VAD and speaker identification."""
        
        while not self.audio_buffer.empty():
            audio_data, timestamp = self.audio_buffer.get()
            
            if audio_data is None:
                continue
            
            # Voice activity detection
            has_speech = self.vad.is_speech(audio_data)
            
            if has_speech:
                # Speaker identification
                speaker_id, confidence = self.speaker_service.identify_speaker(audio_data)
                
                # Create audio segment
                segment = AudioSegment(
                    start_time=timestamp,
                    end_time=timestamp + len(audio_data) / self.sample_rate,
                    speaker_id=speaker_id,
                    confidence=confidence,
                    volume_level=float(np.sqrt(np.mean(audio_data**2)))  # RMS volume
                )
                
                self.audio_segments.append(segment)
    
    async def _process_audio_chunk(
        self,
        audio_data: np.ndarray,
        timestamp: float,
        participant_id: str
    ) -> Optional[AudioSegment]:
        """Process individual audio chunk."""
        
        # Voice activity detection
        has_speech = self.vad.is_speech(audio_data)
        
        if not has_speech:
            return None
        
        # Speaker identification
        speaker_id, confidence = self.speaker_service.identify_speaker(audio_data)
        
        # If no match and we have participant ID, enroll new speaker
        if not speaker_id and participant_id:
            # Find participant
            participant = self.session.get_participant(participant_id)
            if participant and len(audio_data) >= self.sample_rate:  # At least 1 second
                try:
                    profile = await self.speaker_service.enroll_speaker(
                        audio_data, participant_id, participant
                    )
                    speaker_id = profile.speaker_id
                    confidence = profile.confidence
                except Exception as e:
                    logger.error(f"Failed to enroll speaker: {e}")
        
        # Create segment
        segment = AudioSegment(
            start_time=timestamp,
            end_time=timestamp + len(audio_data) / self.sample_rate,
            speaker_id=speaker_id,
            confidence=confidence,
            volume_level=float(np.sqrt(np.mean(audio_data**2)))
        )
        
        self.audio_segments.append(segment)
        return segment
    
    async def _finalize_recording(self):
        """Finalize recording and save files."""
        
        try:
            # Save master audio file
            await self._save_master_file()
            
            # Save individual participant files
            await self._save_participant_files()
            
            # Save segments metadata
            await self._save_segments_metadata()
            
            logger.info(f"Recording finalized: {self.recording_id}")
            
        except Exception as e:
            logger.error(f"Error finalizing recording: {e}")
            raise
    
    async def _save_master_file(self):
        """Save master audio file combining all streams."""
        
        if not self.participant_streams:
            logger.warning("No audio data to save")
            return
        
        # Combine all participant streams
        all_audio = []
        max_length = 0
        
        for participant_streams in self.participant_streams.values():
            if participant_streams:
                combined = np.concatenate(participant_streams)
                all_audio.append(combined)
                max_length = max(max_length, len(combined))
        
        if not all_audio:
            return
        
        # Mix all streams together
        mixed_audio = np.zeros(max_length)
        for audio in all_audio:
            # Pad to max length if necessary
            if len(audio) < max_length:
                audio = np.pad(audio, (0, max_length - len(audio)))
            mixed_audio += audio
        
        # Normalize
        if np.max(np.abs(mixed_audio)) > 0:
            mixed_audio = mixed_audio / np.max(np.abs(mixed_audio)) * 0.8
        
        # Save as WAV file
        sf.write(
            str(self.master_file_path),
            mixed_audio,
            self.sample_rate,
            format='WAV',
            subtype='PCM_16'
        )
        
        logger.info(f"Master audio file saved: {self.master_file_path}")
    
    async def _save_participant_files(self):
        """Save individual participant audio files."""
        
        for participant_id, streams in self.participant_streams.items():
            if not streams:
                continue
            
            # Combine participant streams
            combined = np.concatenate(streams)
            
            # Save individual file
            file_path = self.storage_path / f"{self.session.id}_{participant_id}.wav"
            sf.write(
                str(file_path),
                combined,
                self.sample_rate,
                format='WAV',
                subtype='PCM_16'
            )
            
            self.participant_files[participant_id] = str(file_path)
            logger.info(f"Participant audio saved: {file_path}")
    
    async def _save_segments_metadata(self):
        """Save audio segments metadata."""
        
        metadata = {
            "recording_id": self.recording_id,
            "session_id": self.session.id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "speaker_id": seg.speaker_id,
                    "confidence": seg.confidence,
                    "volume_level": seg.volume_level
                }
                for seg in self.audio_segments
            ],
            "participant_files": self.participant_files,
            "speaker_profiles": {
                sid: {
                    "name": prof.name,
                    "player_id": prof.player_id,
                    "confidence": prof.confidence,
                    "sample_count": prof.sample_count
                }
                for sid, prof in self.speaker_service.speaker_profiles.items()
            }
        }
        
        metadata_path = self.storage_path / f"{self.recording_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved: {metadata_path}")
    
    def __del__(self):
        """Cleanup resources."""
        if self.audio_interface:
            self.audio_interface.terminate()