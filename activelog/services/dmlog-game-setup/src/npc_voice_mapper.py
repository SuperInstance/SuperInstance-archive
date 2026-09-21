import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import numpy as np
from dataclasses import dataclass
import tempfile
import os

from .voice_processor import VoiceProcessor, VoiceCharacteristics

logger = logging.getLogger(__name__)

@dataclass
class VoiceToNPCMapping:
    npc_name: str
    voice_sample_path: str
    voice_characteristics: VoiceCharacteristics
    personality_from_voice: Dict[str, float]
    speech_patterns: List[str]
    accent_type: str
    confidence_score: float
    tts_voice_config: Dict[str, Any]

class NPCVoiceProfile(BaseModel):
    npc_id: str
    name: str
    base_voice_characteristics: VoiceCharacteristics
    voice_variations: List[VoiceCharacteristics]  # Different emotional states
    personality_mapping: Dict[str, float]
    speech_patterns: List[str]
    accent_markers: Dict[str, float]
    emotional_range: Dict[str, Tuple[float, float]]  # min, max values
    tts_configurations: Dict[str, Dict]  # Different configs for different emotions

class CharacterVoiceContext(BaseModel):
    context_snippet: str
    emotion_detected: str
    confidence: float
    voice_characteristics: VoiceCharacteristics
    character_name: Optional[str] = None

class NPCVoiceMapper:
    def __init__(self):
        self.voice_processor = VoiceProcessor()
        self.npc_voices = {}  # npc_name -> NPCVoiceProfile
        self.voice_contexts = []  # List of CharacterVoiceContext
        self.personality_voice_mappings = self._initialize_personality_mappings()
        self.accent_classifiers = self._initialize_accent_classifiers()
        self.emotion_voice_patterns = self._initialize_emotion_patterns()

    def _initialize_personality_mappings(self) -> Dict[str, Dict]:
        """Initialize mappings between voice characteristics and personality traits."""
        return {
            'pitch_personality': {
                'high_pitch': {'cheerful': 0.7, 'energetic': 0.8, 'youthful': 0.6, 'nervous': 0.5},
                'low_pitch': {'authoritative': 0.8, 'calm': 0.7, 'mature': 0.6, 'intimidating': 0.5},
                'varied_pitch': {'expressive': 0.8, 'emotional': 0.7, 'dramatic': 0.6}
            },
            'rate_personality': {
                'fast_speech': {'excited': 0.8, 'nervous': 0.6, 'impatient': 0.7, 'energetic': 0.5},
                'slow_speech': {'thoughtful': 0.8, 'wise': 0.7, 'deliberate': 0.6, 'lazy': 0.4},
                'varied_rate': {'dynamic': 0.7, 'engaging': 0.6, 'storyteller': 0.8}
            },
            'energy_personality': {
                'high_energy': {'enthusiastic': 0.9, 'confident': 0.7, 'outgoing': 0.8},
                'low_energy': {'mysterious': 0.6, 'tired': 0.8, 'melancholic': 0.7},
                'varied_energy': {'versatile': 0.7, 'adaptive': 0.6}
            }
        }

    def _initialize_accent_classifiers(self) -> Dict[str, Dict]:
        """Initialize accent classification patterns."""
        return {
            'regional_markers': {
                'northern': {
                    'formant_patterns': [800, 1200, 2400, 3200],
                    'pitch_tendency': 'lower',
                    'rate_tendency': 'slower'
                },
                'southern': {
                    'formant_patterns': [600, 1400, 2600, 3400],
                    'pitch_tendency': 'varied',
                    'rate_tendency': 'slower'
                },
                'urban': {
                    'formant_patterns': [700, 1300, 2500, 3300],
                    'pitch_tendency': 'higher',
                    'rate_tendency': 'faster'
                },
                'rural': {
                    'formant_patterns': [650, 1250, 2450, 3250],
                    'pitch_tendency': 'stable',
                    'rate_tendency': 'moderate'
                }
            },
            'fantasy_accents': {
                'noble': {
                    'characteristics': 'clear articulation, measured pace, controlled pitch',
                    'personality': {'refined': 0.9, 'educated': 0.8, 'authoritative': 0.7}
                },
                'common_folk': {
                    'characteristics': 'relaxed articulation, natural pace, expressive pitch',
                    'personality': {'friendly': 0.8, 'down_to_earth': 0.9, 'honest': 0.7}
                },
                'scholarly': {
                    'characteristics': 'precise pronunciation, thoughtful pace, varied pitch for emphasis',
                    'personality': {'intelligent': 0.9, 'curious': 0.8, 'patient': 0.7}
                },
                'merchant': {
                    'characteristics': 'persuasive tone, moderate pace, pitch variations for emphasis',
                    'personality': {'charismatic': 0.8, 'opportunistic': 0.7, 'sociable': 0.8}
                }
            }
        }

    def _initialize_emotion_patterns(self) -> Dict[str, Dict]:
        """Initialize emotion-voice pattern mappings."""
        return {
            'anger': {
                'pitch': {'mean_increase': 50, 'variance_increase': 30},
                'energy': {'increase': 0.3},
                'rate': {'increase': 0.2},
                'spectral_changes': {'harshness_increase': 0.4}
            },
            'joy': {
                'pitch': {'mean_increase': 30, 'variance_increase': 40},
                'energy': {'increase': 0.4},
                'rate': {'increase': 0.1},
                'spectral_changes': {'brightness_increase': 0.3}
            },
            'sadness': {
                'pitch': {'mean_decrease': 20, 'variance_decrease': 20},
                'energy': {'decrease': 0.3},
                'rate': {'decrease': 0.2},
                'spectral_changes': {'warmth_decrease': 0.2}
            },
            'fear': {
                'pitch': {'mean_increase': 40, 'variance_increase': 50},
                'energy': {'increase': 0.2},
                'rate': {'increase': 0.3},
                'spectral_changes': {'tension_increase': 0.5}
            },
            'surprise': {
                'pitch': {'mean_increase': 60, 'variance_increase': 60},
                'energy': {'increase': 0.3},
                'rate': {'increase': 0.1},
                'spectral_changes': {'brightness_increase': 0.4}
            },
            'disgust': {
                'pitch': {'mean_decrease': 10, 'variance_increase': 20},
                'energy': {'decrease': 0.1},
                'rate': {'decrease': 0.1},
                'spectral_changes': {'harshness_increase': 0.3}
            }
        }

    async def map_voice_to_npc(self, audio_data: bytes, context: Dict[str, Any]) -> Optional[VoiceToNPCMapping]:
        """Map voice characteristics to NPC creation data."""
        try:
            # Analyze voice characteristics
            voice_characteristics = await self.voice_processor.analyze_voice_characteristics(audio_data)
            
            # Detect character context from conversation
            character_name = await self._extract_character_name_from_context(context)
            
            if not character_name:
                # Generate a name based on voice characteristics
                character_name = await self._generate_name_from_voice(voice_characteristics)
            
            # Map voice to personality
            personality_from_voice = await self._map_voice_to_personality(voice_characteristics)
            
            # Detect speech patterns
            speech_patterns = await self._detect_speech_patterns_from_voice(voice_characteristics)
            
            # Classify accent
            accent_type = await self._classify_accent(voice_characteristics)
            
            # Generate TTS configuration
            tts_config = await self.voice_processor.generate_tts_voice_config(voice_characteristics)
            
            # Calculate confidence score
            confidence_score = await self._calculate_mapping_confidence(
                voice_characteristics, context, character_name
            )
            
            # Save voice sample
            voice_sample_path = await self._save_voice_sample(audio_data, character_name)
            
            mapping = VoiceToNPCMapping(
                npc_name=character_name,
                voice_sample_path=voice_sample_path,
                voice_characteristics=voice_characteristics,
                personality_from_voice=personality_from_voice,
                speech_patterns=speech_patterns,
                accent_type=accent_type,
                confidence_score=confidence_score,
                tts_voice_config=tts_config
            )
            
            # Store the mapping
            await self._store_npc_voice_profile(mapping)
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error mapping voice to NPC: {e}")
            return None

    async def _extract_character_name_from_context(self, context: Dict[str, Any]) -> Optional[str]:
        """Extract character name from conversation context."""
        # Check for explicit character mentions
        characters_mentioned = context.get('characters_mentioned', [])
        if characters_mentioned:
            return characters_mentioned[-1].get('name')  # Use most recent
        
        # Check for direct name mentions in key points
        key_points = context.get('key_points', [])
        for point in key_points:
            # Look for patterns like "This is [Name]" or "Character named [Name]"
            import re
            name_patterns = [
                r'this is ([A-Z][a-z]+)',
                r'character named ([A-Z][a-z]+)',
                r'([A-Z][a-z]+) says',
                r'([A-Z][a-z]+) speaks'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, point, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None

    async def _generate_name_from_voice(self, characteristics: VoiceCharacteristics) -> str:
        """Generate a character name based on voice characteristics."""
        # Name generation based on voice qualities
        pitch_names = {
            'high': ['Melody', 'Aria', 'Soprano', 'Piper', 'Chirp', 'Trill'],
            'medium': ['Harmony', 'Chord', 'Tone', 'Voice', 'Sound', 'Echo'],
            'low': ['Bass', 'Rumble', 'Deep', 'Baritone', 'Gruff', 'Growl']
        }
        
        energy_modifiers = {
            'high': ['Bright', 'Vibrant', 'Energetic', 'Lively', 'Dynamic'],
            'medium': ['Steady', 'Balanced', 'Even', 'Moderate'],
            'low': ['Quiet', 'Soft', 'Gentle', 'Whisper', 'Calm']
        }
        
        # Determine pitch category
        if characteristics.pitch_mean > 200:
            pitch_category = 'high'
        elif characteristics.pitch_mean < 120:
            pitch_category = 'low'
        else:
            pitch_category = 'medium'
        
        # Determine energy category
        if characteristics.energy_mean > 0.1:
            energy_category = 'high'
        elif characteristics.energy_mean < 0.05:
            energy_category = 'low'
        else:
            energy_category = 'medium'
        
        # Combine for unique name
        import random
        base_name = random.choice(pitch_names[pitch_category])
        modifier = random.choice(energy_modifiers[energy_category])
        
        return f"{modifier}-{base_name}"

    async def _map_voice_to_personality(self, characteristics: VoiceCharacteristics) -> Dict[str, float]:
        """Map voice characteristics to personality traits."""
        personality = {}
        
        # Pitch-based personality mapping
        if characteristics.pitch_mean > 200:
            pitch_category = 'high_pitch'
        elif characteristics.pitch_mean < 120:
            pitch_category = 'low_pitch'
        elif characteristics.pitch_std > 30:
            pitch_category = 'varied_pitch'
        else:
            pitch_category = 'high_pitch'  # default
        
        pitch_traits = self.personality_voice_mappings['pitch_personality'].get(pitch_category, {})
        personality.update(pitch_traits)
        
        # Rate-based personality mapping
        if characteristics.speaking_rate > 5:
            rate_category = 'fast_speech'
        elif characteristics.speaking_rate < 2:
            rate_category = 'slow_speech'
        else:
            rate_category = 'varied_rate'
        
        rate_traits = self.personality_voice_mappings['rate_personality'].get(rate_category, {})
        for trait, score in rate_traits.items():
            personality[trait] = personality.get(trait, 0) + score * 0.5
        
        # Energy-based personality mapping
        if characteristics.energy_mean > 0.1:
            energy_category = 'high_energy'
        elif characteristics.energy_mean < 0.05:
            energy_category = 'low_energy'
        else:
            energy_category = 'varied_energy'
        
        energy_traits = self.personality_voice_mappings['energy_personality'].get(energy_category, {})
        for trait, score in energy_traits.items():
            personality[trait] = personality.get(trait, 0) + score * 0.3
        
        # Normalize scores
        max_score = max(personality.values()) if personality else 1.0
        for trait in personality:
            personality[trait] = min(1.0, personality[trait] / max_score)
        
        return personality

    async def _detect_speech_patterns_from_voice(self, characteristics: VoiceCharacteristics) -> List[str]:
        """Detect speech patterns from voice analysis."""
        patterns = []
        
        # Use existing speech patterns from characteristics
        if characteristics.speech_patterns:
            patterns.extend(characteristics.speech_patterns)
        
        # Add additional patterns based on other characteristics
        if characteristics.pitch_std > 50:
            patterns.append('expressive_intonation')
        
        if characteristics.speaking_rate > 6:
            patterns.append('rapid_fire_speech')
        elif characteristics.speaking_rate < 1.5:
            patterns.append('deliberate_speech')
        
        if characteristics.energy_mean > 0.15:
            patterns.append('emphatic_delivery')
        
        # Check emotional markers for additional patterns
        if characteristics.emotional_markers.get('confidence', 0) > 0.7:
            patterns.append('authoritative_tone')
        if characteristics.emotional_markers.get('excitement', 0) > 0.6:
            patterns.append('enthusiastic_delivery')
        if characteristics.emotional_markers.get('calmness', 0) > 0.7:
            patterns.append('measured_speech')
        
        return list(set(patterns))  # Remove duplicates

    async def _classify_accent(self, characteristics: VoiceCharacteristics) -> str:
        """Classify accent type from voice characteristics."""
        # Compare formants to known accent patterns
        accent_scores = {}
        
        for accent, markers in self.accent_classifiers['regional_markers'].items():
            score = 0
            expected_formants = markers['formant_patterns']
            
            # Compare formant frequencies (simplified)
            if characteristics.formant_frequencies:
                actual_formants = characteristics.formant_frequencies[:4]  # First 4 formants
                
                for i, (expected, actual) in enumerate(zip(expected_formants, actual_formants)):
                    if actual > 0:  # Valid formant
                        difference = abs(expected - actual) / expected
                        score += max(0, 1 - difference)
            
            # Check pitch tendencies
            pitch_tendency = markers.get('pitch_tendency', 'stable')
            if pitch_tendency == 'higher' and characteristics.pitch_mean > 180:
                score += 0.5
            elif pitch_tendency == 'lower' and characteristics.pitch_mean < 140:
                score += 0.5
            elif pitch_tendency == 'varied' and characteristics.pitch_std > 40:
                score += 0.5
            
            accent_scores[accent] = score
        
        # Find best matching accent
        if accent_scores:
            best_accent = max(accent_scores, key=accent_scores.get)
            if accent_scores[best_accent] > 0.5:
                return best_accent
        
        # Fallback to fantasy accent classification
        return await self._classify_fantasy_accent(characteristics)

    async def _classify_fantasy_accent(self, characteristics: VoiceCharacteristics) -> str:
        """Classify fantasy-appropriate accent."""
        # Base classification on voice quality and emotional markers
        if characteristics.voice_quality == 'clear' and characteristics.speaking_rate < 3:
            return 'noble'
        elif characteristics.emotional_markers.get('confidence', 0) > 0.8:
            return 'scholarly'
        elif characteristics.energy_mean > 0.1 and characteristics.speaking_rate > 4:
            return 'merchant'
        else:
            return 'common_folk'

    async def _calculate_mapping_confidence(self, characteristics: VoiceCharacteristics, 
                                         context: Dict, character_name: str) -> float:
        """Calculate confidence score for the voice-to-NPC mapping."""
        confidence = 0.5  # Base confidence
        
        # Voice quality contributes to confidence
        quality_scores = {'clear': 0.3, 'good': 0.2, 'fair': 0.1, 'poor': -0.1}
        confidence += quality_scores.get(characteristics.voice_quality, 0)
        
        # Context clarity contributes
        if context.get('contains_character_voice'):
            confidence += 0.2
        
        if character_name and not character_name.startswith('Unknown'):
            confidence += 0.2
        
        # Voice characteristic completeness
        if characteristics.formant_frequencies:
            confidence += 0.1
        if characteristics.emotional_markers:
            confidence += 0.1
        
        return max(0.1, min(1.0, confidence))

    async def _save_voice_sample(self, audio_data: bytes, character_name: str) -> str:
        """Save voice sample to file system."""
        try:
            # Create voice samples directory
            samples_dir = "static/voice_samples"
            os.makedirs(samples_dir, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = ''.join(c for c in character_name if c.isalnum() or c in '-_')
            filename = f"{safe_name}_{timestamp}.wav"
            file_path = os.path.join(samples_dir, filename)
            
            # Save audio data
            with open(file_path, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Saved voice sample for {character_name}: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error saving voice sample: {e}")
            return ""

    async def _store_npc_voice_profile(self, mapping: VoiceToNPCMapping):
        """Store NPC voice profile for later use."""
        try:
            profile = NPCVoiceProfile(
                npc_id=f"{mapping.npc_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=mapping.npc_name,
                base_voice_characteristics=mapping.voice_characteristics,
                voice_variations=[mapping.voice_characteristics],  # Start with base
                personality_mapping=mapping.personality_from_voice,
                speech_patterns=mapping.speech_patterns,
                accent_markers={mapping.accent_type: 1.0},
                emotional_range={
                    emotion: (score * 0.8, score * 1.2)
                    for emotion, score in mapping.voice_characteristics.emotional_markers.items()
                },
                tts_configurations={'default': mapping.tts_voice_config}
            )
            
            self.npc_voices[mapping.npc_name] = profile
            logger.info(f"Stored voice profile for NPC: {mapping.npc_name}")
            
        except Exception as e:
            logger.error(f"Error storing NPC voice profile: {e}")

    async def detect_character_voice_in_context(self, audio_data: bytes, transcription: str) -> Optional[CharacterVoiceContext]:
        """Detect when DM is mimicking a character voice."""
        try:
            characteristics = await self.voice_processor.analyze_voice_characteristics(audio_data)
            
            # Look for voice acting indicators in transcription
            voice_indicators = [
                'says', 'shouts', 'whispers', 'growls', 'laughs',
                'in a deep voice', 'squeakily', 'gruffly', 'softly'
            ]
            
            contains_voice_acting = any(indicator in transcription.lower() for indicator in voice_indicators)
            
            if not contains_voice_acting:
                return None
            
            # Detect emotion from voice
            emotion_detected = await self._detect_primary_emotion(characteristics)
            
            # Calculate confidence based on how different this voice is from baseline
            confidence = await self._calculate_voice_acting_confidence(characteristics, transcription)
            
            return CharacterVoiceContext(
                context_snippet=transcription[:200],  # First 200 chars
                emotion_detected=emotion_detected,
                confidence=confidence,
                voice_characteristics=characteristics,
                character_name=None  # Will be filled by context extraction
            )
            
        except Exception as e:
            logger.error(f"Error detecting character voice: {e}")
            return None

    async def _detect_primary_emotion(self, characteristics: VoiceCharacteristics) -> str:
        """Detect primary emotion from voice characteristics."""
        emotions = characteristics.emotional_markers
        if not emotions:
            return 'neutral'
        
        # Find strongest emotion
        primary_emotion = max(emotions, key=emotions.get)
        
        # Only return if confidence is high enough
        if emotions[primary_emotion] > 0.5:
            return primary_emotion
        
        return 'neutral'

    async def _calculate_voice_acting_confidence(self, characteristics: VoiceCharacteristics, 
                                               transcription: str) -> float:
        """Calculate confidence that this is character voice acting."""
        confidence = 0.3  # Base confidence
        
        # Strong voice acting indicators
        strong_indicators = ['shouts', 'whispers', 'growls', 'roars', 'squeaks']
        if any(indicator in transcription.lower() for indicator in strong_indicators):
            confidence += 0.4
        
        # Extreme pitch variations suggest character voice
        if characteristics.pitch_std > 60:
            confidence += 0.3
        
        # High emotional markers suggest character acting
        max_emotion = max(characteristics.emotional_markers.values()) if characteristics.emotional_markers else 0
        if max_emotion > 0.7:
            confidence += 0.2
        
        # Speech pattern variations
        if len(characteristics.speech_patterns) > 2:
            confidence += 0.1
        
        return min(1.0, confidence)

    async def generate_npc_voice_variations(self, npc_name: str, emotions: List[str]) -> Dict[str, VoiceCharacteristics]:
        """Generate voice variations for different emotional states."""
        if npc_name not in self.npc_voices:
            return {}
        
        base_profile = self.npc_voices[npc_name]
        base_characteristics = base_profile.base_voice_characteristics
        variations = {}
        
        for emotion in emotions:
            if emotion in self.emotion_voice_patterns:
                pattern = self.emotion_voice_patterns[emotion]
                
                # Create modified characteristics
                modified_characteristics = VoiceCharacteristics(
                    pitch_mean=base_characteristics.pitch_mean + pattern.get('pitch', {}).get('mean_increase', 0) - pattern.get('pitch', {}).get('mean_decrease', 0),
                    pitch_std=base_characteristics.pitch_std + pattern.get('pitch', {}).get('variance_increase', 0) - pattern.get('pitch', {}).get('variance_decrease', 0),
                    pitch_range=base_characteristics.pitch_range,
                    speaking_rate=base_characteristics.speaking_rate + pattern.get('rate', {}).get('increase', 0) - pattern.get('rate', {}).get('decrease', 0),
                    energy_mean=base_characteristics.energy_mean + pattern.get('energy', {}).get('increase', 0) - pattern.get('energy', {}).get('decrease', 0),
                    spectral_centroid=base_characteristics.spectral_centroid,
                    formant_frequencies=base_characteristics.formant_frequencies,
                    voice_quality=base_characteristics.voice_quality,
                    accent_indicators=base_characteristics.accent_indicators,
                    emotional_markers={emotion: 0.8},  # High score for target emotion
                    speech_patterns=base_characteristics.speech_patterns + [f"{emotion}_delivery"]
                )
                
                variations[emotion] = modified_characteristics
        
        return variations

    async def test_npc_conversation(self, npc_name: str, test_phrases: List[str]) -> Dict[str, Any]:
        """Test conversation with NPC using their voice profile."""
        if npc_name not in self.npc_voices:
            return {'error': f'No voice profile found for {npc_name}'}
        
        profile = self.npc_voices[npc_name]
        test_results = {
            'npc_name': npc_name,
            'personality_traits': profile.personality_mapping,
            'speech_patterns': profile.speech_patterns,
            'test_responses': []
        }
        
        for phrase in test_phrases:
            # Generate response based on personality
            response = await self._generate_personality_response(profile, phrase)
            
            # Select appropriate voice configuration
            emotion_detected = await self._detect_phrase_emotion(phrase)
            voice_config = profile.tts_configurations.get(emotion_detected, profile.tts_configurations['default'])
            
            test_results['test_responses'].append({
                'input_phrase': phrase,
                'npc_response': response,
                'emotion_used': emotion_detected,
                'voice_config': voice_config
            })
        
        return test_results

    async def _generate_personality_response(self, profile: NPCVoiceProfile, input_phrase: str) -> str:
        """Generate a response based on NPC personality."""
        # Get dominant personality traits
        top_traits = sorted(profile.personality_mapping.items(), 
                          key=lambda x: x[1], reverse=True)[:3]
        
        # Simple personality-based response generation
        if any(trait in ['cheerful', 'energetic'] for trait, _ in top_traits):
            return f"*enthusiastically* Oh, that's wonderful! {input_phrase}? I'd love to help!"
        elif any(trait in ['authoritative', 'intimidating'] for trait, _ in top_traits):
            return f"*with authority* Indeed. {input_phrase} is something I can address."
        elif any(trait in ['mysterious', 'secretive'] for trait, _ in top_traits):
            return f"*mysteriously* Ah, {input_phrase}... there's more to that than meets the eye."
        else:
            return f"*thoughtfully* {input_phrase}? That's an interesting question."

    async def _detect_phrase_emotion(self, phrase: str) -> str:
        """Detect emotion from text phrase."""
        phrase_lower = phrase.lower()
        
        emotion_keywords = {
            'anger': ['angry', 'mad', 'furious', 'rage'],
            'joy': ['happy', 'joyful', 'excited', 'wonderful'],
            'sadness': ['sad', 'depressed', 'melancholy', 'sorrow'],
            'fear': ['scared', 'afraid', 'terrified', 'worried'],
            'surprise': ['surprised', 'amazed', 'shocked', 'astonished']
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in phrase_lower for keyword in keywords):
                return emotion
        
        return 'neutral'