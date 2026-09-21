"""
Automatic transcription service with character attribution.
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pathlib import Path
import uuid

try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logging.warning("Whisper not available - transcription disabled")

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning("SpeechRecognition not available")

try:
    from transformers import pipeline
    NLP_AVAILABLE = True
except ImportError:
    NLP_AVAILABLE = False
    logging.warning("Transformers not available - NLP features disabled")

import numpy as np
import librosa

from ..config import Config
from ..models.base import AudioSegment, SpeakerProfile, TranscriptionStatus
from ..models.session import (
    SessionSchema, SessionTranscription, TranscriptionSegment,
    SessionParticipant
)

logger = logging.getLogger(__name__)

class CharacterAttributionService:
    """Service for attributing speech to characters vs players."""
    
    def __init__(self, config: Config):
        self.config = config
        self.character_patterns: Dict[str, List[str]] = {}
        self.nlp_pipeline = None
        
        if NLP_AVAILABLE:
            try:
                # Initialize NLP pipeline for character detection
                self.nlp_pipeline = pipeline(
                    "text-classification",
                    model="distilbert-base-uncased",
                    device=0 if torch.cuda.is_available() else -1
                )
            except Exception as e:
                logger.warning(f"Could not initialize NLP pipeline: {e}")
    
    def learn_character_patterns(
        self,
        session: SessionSchema,
        transcription_segments: List[TranscriptionSegment]
    ) -> None:
        """Learn character speech patterns from transcription."""
        
        # Extract character names and common phrases
        for participant in session.participants:
            if participant.character_name:
                patterns = self._extract_character_patterns(
                    participant.character_name,
                    transcription_segments
                )
                self.character_patterns[participant.user_id] = patterns
    
    def attribute_speech(
        self,
        text: str,
        speaker_id: str,
        session: SessionSchema
    ) -> Tuple[str, str]:
        """Determine if speech is in-character or out-of-character."""
        
        participant = session.get_participant(speaker_id)
        if not participant or not participant.character_name:
            return "player", speaker_id
        
        # Check for explicit character indicators
        character_indicators = [
            # Direct character speech
            rf'\b{re.escape(participant.character_name)}\s+says?\b',
            r'\bas\s+\w+\b',  # "as Gandalf"
            r'^".*"$',  # Quoted speech
            
            # First person indicators in fantasy context
            r'\bi\s+(cast|attack|move|search)\b',
            r'\blet\s+me\s+(try|check|look)\b',
            r'\bi\s+(want|need|should)\s+to\b',
            
            # Action descriptions
            r'\b(rolls?|rolling)\s+\w*\s*d\d+\b',  # Dice rolling
            r'\bi\s+(roll|rolled)\b',
        ]
        
        out_of_character_indicators = [
            # Meta-game discussion
            r'\b(rules?|mechanics?|stats?)\b',
            r'\bwhat\s+do\s+i\s+roll\b',
            r'\bhow\s+does\s+\w+\s+work\b',
            r'\bmy\s+character\b',
            r'\bthe\s+dm\b',
            
            # Real world references
            r'\b(bathroom|phone|food|drink)\b',
            r'\breal\s+life\b',
            r'\birl\b',  # In real life
            
            # Session management
            r'\bbreak\s+time\b',
            r'\bwe\s+should\s+(stop|pause|continue)\b',
        ]
        
        text_lower = text.lower()
        
        # Check character indicators
        character_score = 0
        for pattern in character_indicators:
            if re.search(pattern, text_lower):
                character_score += 1
        
        # Check out-of-character indicators
        ooc_score = 0
        for pattern in out_of_character_indicators:
            if re.search(pattern, text_lower):
                ooc_score += 2  # Weight OOC patterns higher
        
        # Use learned patterns
        if speaker_id in self.character_patterns:
            for pattern in self.character_patterns[speaker_id]:
                if pattern.lower() in text_lower:
                    character_score += 1
        
        # Determine attribution
        if ooc_score > character_score:
            return "player", speaker_id
        elif character_score > 0:
            return "character", participant.character_name or participant.user_id
        else:
            # Default to character if they have one
            if participant.character_name:
                return "character", participant.character_name
            else:
                return "player", speaker_id
    
    def _extract_character_patterns(
        self,
        character_name: str,
        segments: List[TranscriptionSegment]
    ) -> List[str]:
        """Extract common phrases associated with a character."""
        
        patterns = []
        
        # Find segments attributed to this character
        character_segments = [
            seg for seg in segments
            if seg.character_attribution == character_name
        ]
        
        # Extract common phrases and vocabulary
        all_text = " ".join(seg.text for seg in character_segments)
        words = all_text.lower().split()
        
        # Find common phrases (3-grams)
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            if len(phrase) > 10 and phrase.count(" ") == 2:
                patterns.append(phrase)
        
        # Remove duplicates and sort by frequency
        pattern_counts = {}
        for pattern in patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Return top patterns
        sorted_patterns = sorted(
            pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [pattern for pattern, count in sorted_patterns[:20] if count > 1]

class TranscriptionService:
    """Main transcription service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.whisper_model = None
        self.speech_recognizer = None
        self.character_service = CharacterAttributionService(config)
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize transcription models."""
        
        if WHISPER_AVAILABLE:
            try:
                model_name = self.config.SPEECH_CONFIG["model"]
                self.whisper_model = whisper.load_model(model_name)
                logger.info(f"Whisper model '{model_name}' loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Whisper model: {e}")
        
        if SPEECH_RECOGNITION_AVAILABLE:
            self.speech_recognizer = sr.Recognizer()
            self.speech_recognizer.energy_threshold = 300
            self.speech_recognizer.dynamic_energy_threshold = True
    
    async def transcribe_session(
        self,
        session: SessionSchema,
        audio_file_path: str,
        audio_segments: List[AudioSegment] = None
    ) -> SessionTranscription:
        """Transcribe complete session audio."""
        
        transcription = SessionTranscription(
            session_id=session.id,
            recording_id=str(uuid.uuid4()),
            status=TranscriptionStatus.PROCESSING,
            started_at=datetime.utcnow(),
            model_used=self.config.SPEECH_CONFIG["model"]
        )
        
        try:
            if WHISPER_AVAILABLE and self.whisper_model:
                segments = await self._transcribe_with_whisper(
                    audio_file_path, session, audio_segments
                )
            elif SPEECH_RECOGNITION_AVAILABLE and self.speech_recognizer:
                segments = await self._transcribe_with_speech_recognition(
                    audio_file_path, session, audio_segments
                )
            else:
                raise RuntimeError("No transcription engine available")
            
            # Apply character attribution
            for segment in segments:
                attribution_type, attribution_name = self.character_service.attribute_speech(
                    segment.text, segment.speaker_id, session
                )
                segment.character_attribution = attribution_name
            
            transcription.segments = segments
            transcription.full_text = self._combine_segments_to_text(segments)
            transcription.word_count = len(transcription.full_text.split())
            transcription.duration = segments[-1].end_time if segments else 0
            
            # Calculate statistics
            transcription.speaking_time_by_participant = self._calculate_speaking_time(segments)
            transcription.average_confidence = np.mean([s.confidence for s in segments]) if segments else 0
            
            # Identify low confidence segments
            confidence_threshold = self.config.SPEECH_CONFIG["confidence_threshold"]
            transcription.low_confidence_segments = [
                s.id for s in segments if s.confidence < confidence_threshold
            ]
            
            transcription.status = TranscriptionStatus.COMPLETED
            transcription.completed_at = datetime.utcnow()
            
            logger.info(f"Transcription completed: {len(segments)} segments, {transcription.word_count} words")
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            transcription.status = TranscriptionStatus.FAILED
            raise
        
        return transcription
    
    async def transcribe_real_time(
        self,
        audio_data: np.ndarray,
        session: SessionSchema,
        speaker_id: str = None
    ) -> Optional[TranscriptionSegment]:
        """Real-time transcription of audio chunk."""
        
        if not WHISPER_AVAILABLE or not self.whisper_model:
            return None
        
        try:
            # Ensure minimum length for transcription
            min_duration = 1.0  # seconds
            min_samples = int(min_duration * self.config.AUDIO_CONFIG["sample_rate"])
            
            if len(audio_data) < min_samples:
                return None
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(
                audio_data,
                language=self.config.SPEECH_CONFIG["language"] if not self.config.SPEECH_CONFIG["auto_detect_language"] else None,
                temperature=0.0,
                word_timestamps=True
            )
            
            if not result["text"].strip():
                return None
            
            # Create segment
            segment = TranscriptionSegment(
                start_time=0,
                end_time=len(audio_data) / self.config.AUDIO_CONFIG["sample_rate"],
                speaker_id=speaker_id,
                text=result["text"].strip(),
                confidence=1.0,  # Whisper doesn't provide confidence scores
                language=result.get("language", "en")
            )
            
            # Add word timestamps if available
            if "segments" in result:
                for whisper_segment in result["segments"]:
                    if "words" in whisper_segment:
                        for word in whisper_segment["words"]:
                            segment.word_timestamps.append({
                                "word": word["word"],
                                "start": word["start"],
                                "end": word["end"]
                            })
            
            # Apply character attribution
            attribution_type, attribution_name = self.character_service.attribute_speech(
                segment.text, speaker_id, session
            )
            segment.character_attribution = attribution_name
            
            return segment
            
        except Exception as e:
            logger.error(f"Real-time transcription failed: {e}")
            return None
    
    async def _transcribe_with_whisper(
        self,
        audio_file_path: str,
        session: SessionSchema,
        audio_segments: List[AudioSegment] = None
    ) -> List[TranscriptionSegment]:
        """Transcribe using Whisper."""
        
        if not WHISPER_AVAILABLE or not self.whisper_model:
            raise RuntimeError("Whisper not available")
        
        # Load audio file
        audio, _ = librosa.load(
            audio_file_path,
            sr=self.config.AUDIO_CONFIG["sample_rate"]
        )
        
        # Transcribe entire file
        result = self.whisper_model.transcribe(
            audio,
            language=self.config.SPEECH_CONFIG["language"] if not self.config.SPEECH_CONFIG["auto_detect_language"] else None,
            word_timestamps=True,
            temperature=0.0
        )
        
        segments = []
        
        for whisper_segment in result["segments"]:
            # Map to speaker if we have audio segments
            speaker_id = self._map_to_speaker(
                whisper_segment["start"],
                whisper_segment["end"],
                audio_segments
            )
            
            segment = TranscriptionSegment(
                start_time=whisper_segment["start"],
                end_time=whisper_segment["end"],
                speaker_id=speaker_id,
                text=whisper_segment["text"].strip(),
                confidence=1.0,  # Whisper doesn't provide confidence
                language=result.get("language", "en")
            )
            
            # Add word timestamps
            if "words" in whisper_segment:
                for word in whisper_segment["words"]:
                    segment.word_timestamps.append({
                        "word": word["word"],
                        "start": word["start"],
                        "end": word["end"]
                    })
            
            segments.append(segment)
        
        return segments
    
    async def _transcribe_with_speech_recognition(
        self,
        audio_file_path: str,
        session: SessionSchema,
        audio_segments: List[AudioSegment] = None
    ) -> List[TranscriptionSegment]:
        """Transcribe using Google Speech Recognition."""
        
        if not SPEECH_RECOGNITION_AVAILABLE:
            raise RuntimeError("SpeechRecognition not available")
        
        # Load and process audio in chunks
        audio, sr = librosa.load(audio_file_path, sr=None)
        
        # Convert to the format expected by speech_recognition
        chunk_duration = 30  # seconds
        chunk_samples = chunk_duration * sr
        
        segments = []
        
        for start_idx in range(0, len(audio), chunk_samples):
            end_idx = min(start_idx + chunk_samples, len(audio))
            chunk = audio[start_idx:end_idx]
            
            start_time = start_idx / sr
            end_time = end_idx / sr
            
            try:
                # Convert chunk to the format expected by speech_recognition
                chunk_int16 = (chunk * 32767).astype(np.int16)
                
                # Create AudioData object
                audio_data = sr.AudioData(
                    chunk_int16.tobytes(),
                    sr,
                    2  # 16-bit samples
                )
                
                # Recognize speech
                text = self.speech_recognizer.recognize_google(
                    audio_data,
                    language=self.config.SPEECH_CONFIG["language"]
                )
                
                if text.strip():
                    # Map to speaker
                    speaker_id = self._map_to_speaker(
                        start_time, end_time, audio_segments
                    )
                    
                    segment = TranscriptionSegment(
                        start_time=start_time,
                        end_time=end_time,
                        speaker_id=speaker_id,
                        text=text.strip(),
                        confidence=0.8,  # Approximate confidence
                        language=self.config.SPEECH_CONFIG["language"]
                    )
                    
                    segments.append(segment)
                    
            except sr.UnknownValueError:
                # No speech detected in this chunk
                continue
            except sr.RequestError as e:
                logger.error(f"Speech recognition error: {e}")
                continue
            
        return segments
    
    def _map_to_speaker(
        self,
        start_time: float,
        end_time: float,
        audio_segments: List[AudioSegment] = None
    ) -> Optional[str]:
        """Map transcription segment to speaker based on audio segments."""
        
        if not audio_segments:
            return None
        
        # Find overlapping audio segments
        overlapping_segments = []
        
        for audio_seg in audio_segments:
            if (audio_seg.start_time < end_time and 
                audio_seg.end_time > start_time):
                overlap_duration = min(end_time, audio_seg.end_time) - max(start_time, audio_seg.start_time)
                overlapping_segments.append((audio_seg, overlap_duration))
        
        if not overlapping_segments:
            return None
        
        # Return speaker with longest overlap
        best_segment = max(overlapping_segments, key=lambda x: x[1])
        return best_segment[0].speaker_id
    
    def _combine_segments_to_text(self, segments: List[TranscriptionSegment]) -> str:
        """Combine segments into readable text."""
        
        if not segments:
            return ""
        
        # Sort segments by time
        sorted_segments = sorted(segments, key=lambda x: x.start_time)
        
        # Group by speaker for better formatting
        text_parts = []
        current_speaker = None
        current_text = []
        
        for segment in sorted_segments:
            speaker_name = segment.character_attribution or segment.speaker_name or segment.speaker_id
            
            if speaker_name != current_speaker:
                # New speaker - finalize previous and start new
                if current_text:
                    speaker_label = current_speaker or "Unknown"
                    combined_text = " ".join(current_text)
                    text_parts.append(f"{speaker_label}: {combined_text}")
                
                current_speaker = speaker_name
                current_text = [segment.text]
            else:
                # Same speaker - continue
                current_text.append(segment.text)
        
        # Add final speaker
        if current_text:
            speaker_label = current_speaker or "Unknown"
            combined_text = " ".join(current_text)
            text_parts.append(f"{speaker_label}: {combined_text}")
        
        return "\n\n".join(text_parts)
    
    def _calculate_speaking_time(
        self,
        segments: List[TranscriptionSegment]
    ) -> Dict[str, float]:
        """Calculate speaking time by participant."""
        
        speaking_time = {}
        
        for segment in segments:
            speaker_id = segment.speaker_id or "unknown"
            duration = segment.end_time - segment.start_time
            
            speaking_time[speaker_id] = speaking_time.get(speaker_id, 0) + duration
        
        return speaking_time
    
    async def correct_transcription(
        self,
        transcription: SessionTranscription,
        segment_id: str,
        corrected_text: str,
        corrected_by: str
    ) -> bool:
        """Apply manual correction to transcription segment."""
        
        # Find segment
        segment = next((s for s in transcription.segments if s.id == segment_id), None)
        if not segment:
            return False
        
        # Store original text as correction history
        correction = {
            "original": segment.text,
            "corrected": corrected_text,
            "timestamp": datetime.utcnow().isoformat(),
            "corrected_by": corrected_by
        }
        
        # Update segment
        segment.text = corrected_text
        segment.corrections.append(correction["original"])
        
        # Update transcription
        transcription.corrections.append(correction)
        transcription.full_text = self._combine_segments_to_text(transcription.segments)
        transcription.word_count = len(transcription.full_text.split())
        
        logger.info(f"Transcription correction applied to segment {segment_id}")
        return True
    
    async def export_transcription(
        self,
        transcription: SessionTranscription,
        format_type: str = "srt",
        include_speakers: bool = True,
        include_timestamps: bool = True
    ) -> str:
        """Export transcription in various formats."""
        
        if format_type.lower() == "srt":
            return self._export_srt(transcription, include_speakers)
        elif format_type.lower() == "vtt":
            return self._export_vtt(transcription, include_speakers)
        elif format_type.lower() == "txt":
            return self._export_txt(transcription, include_speakers, include_timestamps)
        elif format_type.lower() == "json":
            return self._export_json(transcription)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _export_srt(self, transcription: SessionTranscription, include_speakers: bool) -> str:
        """Export as SRT subtitle format."""
        
        srt_content = []
        
        for i, segment in enumerate(transcription.segments, 1):
            start_time = self._format_srt_time(segment.start_time)
            end_time = self._format_srt_time(segment.end_time)
            
            speaker_prefix = ""
            if include_speakers and segment.character_attribution:
                speaker_prefix = f"{segment.character_attribution}: "
            
            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(f"{speaker_prefix}{segment.text}")
            srt_content.append("")  # Empty line
        
        return "\n".join(srt_content)
    
    def _export_vtt(self, transcription: SessionTranscription, include_speakers: bool) -> str:
        """Export as WebVTT format."""
        
        vtt_content = ["WEBVTT", ""]
        
        for segment in transcription.segments:
            start_time = self._format_vtt_time(segment.start_time)
            end_time = self._format_vtt_time(segment.end_time)
            
            speaker_prefix = ""
            if include_speakers and segment.character_attribution:
                speaker_prefix = f"<v {segment.character_attribution}>"
            
            vtt_content.append(f"{start_time} --> {end_time}")
            vtt_content.append(f"{speaker_prefix}{segment.text}")
            vtt_content.append("")
        
        return "\n".join(vtt_content)
    
    def _export_txt(
        self,
        transcription: SessionTranscription,
        include_speakers: bool,
        include_timestamps: bool
    ) -> str:
        """Export as plain text."""
        
        if not include_speakers and not include_timestamps:
            return transcription.full_text
        
        text_parts = []
        
        for segment in transcription.segments:
            parts = []
            
            if include_timestamps:
                timestamp = self._format_timestamp(segment.start_time)
                parts.append(f"[{timestamp}]")
            
            if include_speakers and segment.character_attribution:
                parts.append(f"{segment.character_attribution}:")
            
            parts.append(segment.text)
            
            text_parts.append(" ".join(parts))
        
        return "\n".join(text_parts)
    
    def _export_json(self, transcription: SessionTranscription) -> str:
        """Export as JSON format."""
        
        data = {
            "transcription_id": transcription.id,
            "session_id": transcription.session_id,
            "status": transcription.status,
            "model_used": transcription.model_used,
            "language": transcription.language,
            "duration": transcription.duration,
            "word_count": transcription.word_count,
            "average_confidence": transcription.average_confidence,
            "segments": [
                {
                    "id": seg.id,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "speaker_id": seg.speaker_id,
                    "speaker_name": seg.speaker_name,
                    "character_attribution": seg.character_attribution,
                    "text": seg.text,
                    "confidence": seg.confidence,
                    "language": seg.language,
                    "word_timestamps": seg.word_timestamps
                }
                for seg in transcription.segments
            ]
        }
        
        return json.dumps(data, indent=2, default=str)
    
    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_vtt_time(self, seconds: float) -> str:
        """Format time for VTT format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for display."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"