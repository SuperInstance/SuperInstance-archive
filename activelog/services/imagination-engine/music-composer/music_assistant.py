#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
import uuid
import math

class MusicGenre(Enum):
    CLASSICAL = "classical"
    JAZZ = "jazz"
    ROCK = "rock"
    ELECTRONIC = "electronic"
    AMBIENT = "ambient"
    FOLK = "folk"
    WORLD = "world"
    CINEMATIC = "cinematic"
    EXPERIMENTAL = "experimental"
    MINIMALIST = "minimalist"

class Mood(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ENERGETIC = "energetic"
    CALM = "calm"
    MYSTERIOUS = "mysterious"
    DRAMATIC = "dramatic"
    ROMANTIC = "romantic"
    TENSE = "tense"
    TRIUMPHANT = "triumphant"
    MELANCHOLIC = "melancholic"

class ScaleType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    DORIAN = "dorian"
    MIXOLYDIAN = "mixolydian"
    PENTATONIC = "pentatonic"
    BLUES = "blues"
    CHROMATIC = "chromatic"
    WHOLE_TONE = "whole_tone"

class TimeSignature(Enum):
    FOUR_FOUR = "4/4"
    THREE_FOUR = "3/4"
    TWO_FOUR = "2/4"
    SIX_EIGHT = "6/8"
    FIVE_FOUR = "5/4"
    SEVEN_EIGHT = "7/8"

@dataclass
class Note:
    pitch: str  # C, C#, D, etc.
    octave: int  # 1-8
    duration: float  # in beats
    velocity: int  # 0-127 (MIDI velocity)
    start_time: float  # beat position in measure

@dataclass
class Chord:
    root: str  # Root note
    chord_type: str  # major, minor, dim, aug, etc.
    inversion: int  # 0 = root position, 1 = first inversion, etc.
    duration: float  # in beats
    start_time: float  # beat position

@dataclass
class Rhythm:
    pattern: List[float]  # Beat durations
    emphasis: List[int]  # Velocity emphasis for each beat
    swing_factor: float  # 0.0 = straight, 1.0 = full swing
    syncopation_level: int  # 0-10 scale

@dataclass
class MusicSection:
    id: str
    name: str
    bars: int
    tempo: int  # BPM
    key: str  # Key signature (C, Dm, etc.)
    scale: ScaleType
    time_signature: TimeSignature
    chord_progression: List[Chord]
    melody: List[Note]
    bass_line: List[Note]
    rhythm: Rhythm
    dynamics: str  # pp, p, mp, mf, f, ff
    mood: Mood

@dataclass
class Instrument:
    id: str
    name: str
    type: str  # percussion, string, wind, electronic, etc.
    range_low: str  # Lowest note (e.g., "C2")
    range_high: str  # Highest note (e.g., "C7")
    timbral_characteristics: List[str]
    common_techniques: List[str]
    genre_associations: List[MusicGenre]
    midi_program: int  # General MIDI program number

@dataclass
class MusicComposition:
    id: str
    title: str
    composer: str
    genre: MusicGenre
    mood: Mood
    key: str
    tempo: int
    time_signature: TimeSignature
    sections: List[MusicSection]
    instruments: List[Instrument]
    arrangement_notes: str
    inspiration_sources: List[str]
    target_duration: int  # seconds
    complexity_level: int  # 1-10 scale
    created_at: str
    updated_at: str

class MusicTheory:
    def __init__(self):
        self.notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        
        self.scales = {
            ScaleType.MAJOR: [0, 2, 4, 5, 7, 9, 11],
            ScaleType.MINOR: [0, 2, 3, 5, 7, 8, 10],
            ScaleType.DORIAN: [0, 2, 3, 5, 7, 9, 10],
            ScaleType.MIXOLYDIAN: [0, 2, 4, 5, 7, 9, 10],
            ScaleType.PENTATONIC: [0, 2, 4, 7, 9],
            ScaleType.BLUES: [0, 3, 5, 6, 7, 10],
            ScaleType.CHROMATIC: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            ScaleType.WHOLE_TONE: [0, 2, 4, 6, 8, 10]
        }
        
        self.chord_formulas = {
            "major": [0, 4, 7],
            "minor": [0, 3, 7],
            "dim": [0, 3, 6],
            "aug": [0, 4, 8],
            "maj7": [0, 4, 7, 11],
            "min7": [0, 3, 7, 10],
            "dom7": [0, 4, 7, 10],
            "sus2": [0, 2, 7],
            "sus4": [0, 5, 7]
        }
        
        self.genre_characteristics = {
            MusicGenre.CLASSICAL: {
                "common_scales": [ScaleType.MAJOR, ScaleType.MINOR],
                "typical_tempos": (60, 120),
                "time_signatures": [TimeSignature.FOUR_FOUR, TimeSignature.THREE_FOUR],
                "chord_preferences": ["major", "minor", "dim", "maj7"],
                "complexity_range": (6, 10)
            },
            MusicGenre.JAZZ: {
                "common_scales": [ScaleType.MAJOR, ScaleType.MINOR, ScaleType.DORIAN],
                "typical_tempos": (80, 160),
                "time_signatures": [TimeSignature.FOUR_FOUR, TimeSignature.THREE_FOUR],
                "chord_preferences": ["maj7", "min7", "dom7", "dim"],
                "complexity_range": (7, 10)
            },
            MusicGenre.ROCK: {
                "common_scales": [ScaleType.MINOR, ScaleType.PENTATONIC],
                "typical_tempos": (100, 140),
                "time_signatures": [TimeSignature.FOUR_FOUR],
                "chord_preferences": ["major", "minor", "sus4"],
                "complexity_range": (4, 7)
            },
            MusicGenre.ELECTRONIC: {
                "common_scales": [ScaleType.MINOR, ScaleType.CHROMATIC],
                "typical_tempos": (120, 140),
                "time_signatures": [TimeSignature.FOUR_FOUR],
                "chord_preferences": ["minor", "aug", "sus2"],
                "complexity_range": (5, 9)
            },
            MusicGenre.FOLK: {
                "common_scales": [ScaleType.MAJOR, ScaleType.MINOR, ScaleType.PENTATONIC],
                "typical_tempos": (70, 120),
                "time_signatures": [TimeSignature.FOUR_FOUR, TimeSignature.THREE_FOUR],
                "chord_preferences": ["major", "minor"],
                "complexity_range": (2, 6)
            }
        }
        
        self.mood_mappings = {
            Mood.HAPPY: {"scales": [ScaleType.MAJOR, ScaleType.MIXOLYDIAN], "tempo_range": (100, 140)},
            Mood.SAD: {"scales": [ScaleType.MINOR], "tempo_range": (60, 90)},
            Mood.ENERGETIC: {"scales": [ScaleType.MAJOR, ScaleType.PENTATONIC], "tempo_range": (120, 160)},
            Mood.CALM: {"scales": [ScaleType.MAJOR, ScaleType.DORIAN], "tempo_range": (60, 100)},
            Mood.MYSTERIOUS: {"scales": [ScaleType.MINOR, ScaleType.WHOLE_TONE], "tempo_range": (70, 110)},
            Mood.DRAMATIC: {"scales": [ScaleType.MINOR, ScaleType.CHROMATIC], "tempo_range": (80, 130)}
        }

    def get_scale_notes(self, root: str, scale_type: ScaleType) -> List[str]:
        """Get all notes in a scale starting from the root note."""
        root_index = self.notes.index(root)
        scale_intervals = self.scales[scale_type]
        
        scale_notes = []
        for interval in scale_intervals:
            note_index = (root_index + interval) % 12
            scale_notes.append(self.notes[note_index])
        
        return scale_notes

    def build_chord(self, root: str, chord_type: str, inversion: int = 0) -> List[str]:
        """Build a chord from root note and type."""
        root_index = self.notes.index(root)
        chord_intervals = self.chord_formulas[chord_type]
        
        chord_notes = []
        for interval in chord_intervals:
            note_index = (root_index + interval) % 12
            chord_notes.append(self.notes[note_index])
        
        # Apply inversion
        for _ in range(inversion):
            if chord_notes:
                chord_notes.append(chord_notes.pop(0))
        
        return chord_notes

    def suggest_chord_progression(self, key: str, scale_type: ScaleType, 
                                length: int = 4) -> List[str]:
        """Suggest a chord progression in the given key and scale."""
        scale_notes = self.get_scale_notes(key, scale_type)
        
        # Common chord progressions based on scale degrees
        if scale_type == ScaleType.MAJOR:
            common_progressions = [
                [1, 5, 6, 4],  # I-V-vi-IV
                [1, 6, 4, 5],  # I-vi-IV-V
                [6, 4, 1, 5],  # vi-IV-I-V
                [1, 4, 5, 1],  # I-IV-V-I
            ]
        elif scale_type == ScaleType.MINOR:
            common_progressions = [
                [1, 7, 6, 7],  # i-VII-VI-VII
                [1, 4, 5, 1],  # i-iv-v-i
                [1, 6, 7, 1],  # i-VI-VII-i
                [1, 3, 7, 1],  # i-III-VII-i
            ]
        else:
            # Generic progression for other scales
            common_progressions = [
                [1, 3, 5, 7],
                [1, 4, 5, 1],
                [1, 2, 3, 1]
            ]
        
        progression_pattern = random.choice(common_progressions)
        
        # Extend or truncate to desired length
        while len(progression_pattern) < length:
            progression_pattern.extend(progression_pattern)
        progression_pattern = progression_pattern[:length]
        
        # Convert scale degrees to actual chords
        chord_progression = []
        for degree in progression_pattern:
            if degree <= len(scale_notes):
                root = scale_notes[degree - 1]
                chord_type = "minor" if scale_type == ScaleType.MINOR and degree in [1, 4, 5] else "major"
                chord_progression.append(f"{root}{chord_type}")
        
        return chord_progression

    def get_compatible_scales(self, mood: Mood) -> List[ScaleType]:
        """Get scales that work well with the given mood."""
        mood_info = self.mood_mappings.get(mood, {})
        return mood_info.get("scales", [ScaleType.MAJOR, ScaleType.MINOR])

    def get_tempo_range(self, mood: Mood) -> Tuple[int, int]:
        """Get appropriate tempo range for the mood."""
        mood_info = self.mood_mappings.get(mood, {})
        return mood_info.get("tempo_range", (80, 120))

class MelodyGenerator:
    def __init__(self, music_theory: MusicTheory):
        self.theory = music_theory

    def generate_melody(self, scale_notes: List[str], bars: int, 
                       time_signature: TimeSignature, mood: Mood) -> List[Note]:
        """Generate a melody using the given scale and parameters."""
        melody = []
        
        # Determine note durations based on time signature
        if time_signature == TimeSignature.FOUR_FOUR:
            possible_durations = [0.25, 0.5, 1.0, 2.0]  # 16th, 8th, quarter, half
            beats_per_bar = 4
        elif time_signature == TimeSignature.THREE_FOUR:
            possible_durations = [0.5, 1.0, 2.0]  # 8th, quarter, half
            beats_per_bar = 3
        else:
            possible_durations = [0.5, 1.0]
            beats_per_bar = 4
        
        current_beat = 0
        
        for bar in range(bars):
            bar_start = bar * beats_per_bar
            
            while current_beat < bar_start + beats_per_bar:
                # Choose note duration
                remaining_beats = (bar_start + beats_per_bar) - current_beat
                valid_durations = [d for d in possible_durations if d <= remaining_beats]
                duration = random.choice(valid_durations) if valid_durations else 0.25
                
                # Choose pitch based on mood and previous notes
                pitch = self._choose_melodic_pitch(scale_notes, melody, mood)
                octave = self._choose_octave(mood)
                velocity = self._choose_velocity(mood, current_beat, beats_per_bar)
                
                note = Note(
                    pitch=pitch,
                    octave=octave,
                    duration=duration,
                    velocity=velocity,
                    start_time=current_beat
                )
                
                melody.append(note)
                current_beat += duration
        
        return melody

    def _choose_melodic_pitch(self, scale_notes: List[str], 
                            previous_notes: List[Note], mood: Mood) -> str:
        """Choose next pitch based on melodic principles."""
        
        # If no previous notes, start with tonic or dominant
        if not previous_notes:
            return random.choice([scale_notes[0], scale_notes[4] if len(scale_notes) > 4 else scale_notes[0]])
        
        last_note = previous_notes[-1]
        last_index = scale_notes.index(last_note.pitch) if last_note.pitch in scale_notes else 0
        
        # Melodic movement preferences based on mood
        if mood in [Mood.CALM, Mood.ROMANTIC]:
            # Prefer stepwise motion
            movement_options = [-1, 0, 1]
            weights = [3, 1, 3]  # Favor small steps
        elif mood in [Mood.ENERGETIC, Mood.DRAMATIC]:
            # Allow larger jumps
            movement_options = [-3, -2, -1, 1, 2, 3]
            weights = [1, 2, 3, 3, 2, 1]
        else:
            # Balanced approach
            movement_options = [-2, -1, 0, 1, 2]
            weights = [2, 3, 1, 3, 2]
        
        # Choose movement
        movement = random.choices(movement_options, weights=weights)[0]
        new_index = (last_index + movement) % len(scale_notes)
        
        return scale_notes[new_index]

    def _choose_octave(self, mood: Mood) -> int:
        """Choose appropriate octave based on mood."""
        octave_preferences = {
            Mood.SAD: [3, 4],
            Mood.CALM: [4, 5],
            Mood.HAPPY: [4, 5, 6],
            Mood.ENERGETIC: [5, 6],
            Mood.DRAMATIC: [3, 4, 5, 6],
            Mood.MYSTERIOUS: [3, 4]
        }
        
        return random.choice(octave_preferences.get(mood, [4, 5]))

    def _choose_velocity(self, mood: Mood, beat_position: float, beats_per_bar: int) -> int:
        """Choose note velocity based on mood and position."""
        base_velocities = {
            Mood.CALM: 60,
            Mood.ENERGETIC: 100,
            Mood.SAD: 50,
            Mood.DRAMATIC: 90,
            Mood.HAPPY: 80
        }
        
        base_velocity = base_velocities.get(mood, 70)
        
        # Add rhythmic emphasis (stronger on beats 1 and 3 in 4/4)
        if beats_per_bar == 4 and beat_position % 1 == 0:  # On the beat
            if beat_position % beats_per_bar == 0:  # Beat 1
                base_velocity += 15
            elif beat_position % beats_per_bar == 2:  # Beat 3
                base_velocity += 8
        
        # Add some randomness
        velocity = base_velocity + random.randint(-10, 10)
        return max(30, min(127, velocity))

class RhythmGenerator:
    def __init__(self):
        self.common_patterns = {
            TimeSignature.FOUR_FOUR: {
                "basic": [1.0, 1.0, 1.0, 1.0],
                "syncopated": [0.5, 0.5, 1.0, 0.5, 0.5, 1.0],
                "complex": [0.25, 0.75, 0.5, 0.5, 1.0, 1.0]
            },
            TimeSignature.THREE_FOUR: {
                "waltz": [1.0, 1.0, 1.0],
                "compound": [0.5, 0.5, 1.0, 1.0]
            }
        }

    def generate_rhythm(self, time_signature: TimeSignature, 
                       mood: Mood, complexity: int = 5) -> Rhythm:
        """Generate a rhythm pattern."""
        
        # Choose base pattern
        patterns = self.common_patterns.get(time_signature, {})
        if patterns:
            pattern_name = random.choice(list(patterns.keys()))
            base_pattern = patterns[pattern_name].copy()
        else:
            base_pattern = [1.0, 1.0, 1.0, 1.0]  # Default 4/4
        
        # Generate emphasis pattern
        emphasis = [80 + random.randint(-10, 20) for _ in base_pattern]
        
        # Adjust for mood
        if mood == Mood.ENERGETIC:
            emphasis = [v + 15 for v in emphasis]
        elif mood == Mood.CALM:
            emphasis = [v - 15 for v in emphasis]
        
        # Add swing if appropriate
        swing_factor = 0.0
        if mood in [Mood.HAPPY, Mood.ROMANTIC] and random.random() < 0.3:
            swing_factor = random.uniform(0.1, 0.3)
        
        # Set syncopation level
        syncopation = min(10, complexity)
        if mood == Mood.ENERGETIC:
            syncopation += 2
        
        return Rhythm(
            pattern=base_pattern,
            emphasis=emphasis,
            swing_factor=swing_factor,
            syncopation_level=syncopation
        )

class InstrumentLibrary:
    def __init__(self):
        self.instruments = {
            "piano": Instrument(
                id="piano",
                name="Piano",
                type="keyboard",
                range_low="A0",
                range_high="C8",
                timbral_characteristics=["percussive attack", "sustained", "dynamic range"],
                common_techniques=["legato", "staccato", "pedaling", "arpeggiation"],
                genre_associations=[MusicGenre.CLASSICAL, MusicGenre.JAZZ, MusicGenre.ROCK],
                midi_program=1
            ),
            
            "acoustic_guitar": Instrument(
                id="acoustic_guitar",
                name="Acoustic Guitar",
                type="string",
                range_low="E2",
                range_high="E6",
                timbral_characteristics=["warm", "resonant", "plucked"],
                common_techniques=["fingerpicking", "strumming", "bending", "harmonics"],
                genre_associations=[MusicGenre.FOLK, MusicGenre.ROCK, MusicGenre.CLASSICAL],
                midi_program=25
            ),
            
            "violin": Instrument(
                id="violin",
                name="Violin",
                type="string",
                range_low="G3",
                range_high="E7",
                timbral_characteristics=["expressive", "lyrical", "bowed"],
                common_techniques=["legato", "staccato", "vibrato", "pizzicato"],
                genre_associations=[MusicGenre.CLASSICAL, MusicGenre.FOLK, MusicGenre.WORLD],
                midi_program=41
            ),
            
            "flute": Instrument(
                id="flute",
                name="Flute",
                type="wind",
                range_low="C4",
                range_high="C7",
                timbral_characteristics=["bright", "airy", "agile"],
                common_techniques=["legato", "flutter tonguing", "overblowing"],
                genre_associations=[MusicGenre.CLASSICAL, MusicGenre.WORLD, MusicGenre.JAZZ],
                midi_program=74
            ),
            
            "synthesizer": Instrument(
                id="synthesizer",
                name="Synthesizer",
                type="electronic",
                range_low="C0",
                range_high="C8",
                timbral_characteristics=["versatile", "synthetic", "programmable"],
                common_techniques=["modulation", "filtering", "sequencing"],
                genre_associations=[MusicGenre.ELECTRONIC, MusicGenre.ROCK, MusicGenre.AMBIENT],
                midi_program=81
            ),
            
            "drums": Instrument(
                id="drums",
                name="Drum Kit",
                type="percussion",
                range_low="C1",
                range_high="C6",
                timbral_characteristics=["rhythmic", "percussive", "dynamic"],
                common_techniques=["rolls", "fills", "cross-sticking", "rim shots"],
                genre_associations=[MusicGenre.ROCK, MusicGenre.JAZZ, MusicGenre.ELECTRONIC],
                midi_program=1  # Drum kit uses channel 10
            ),
            
            "bass": Instrument(
                id="bass",
                name="Bass Guitar",
                type="string",
                range_low="E1",
                range_high="G4",
                timbral_characteristics=["deep", "foundational", "rhythmic"],
                common_techniques=["fingerstyle", "slapping", "sliding"],
                genre_associations=[MusicGenre.ROCK, MusicGenre.JAZZ, MusicGenre.FUNK],
                midi_program=34
            )
        }

    def get_instruments_for_genre(self, genre: MusicGenre) -> List[Instrument]:
        """Get instruments commonly used in a genre."""
        return [inst for inst in self.instruments.values() 
                if genre in inst.genre_associations]

    def suggest_ensemble(self, genre: MusicGenre, size: str = "small") -> List[Instrument]:
        """Suggest an instrumental ensemble for the genre."""
        available_instruments = self.get_instruments_for_genre(genre)
        
        if size == "solo":
            return random.sample(available_instruments, 1)
        elif size == "small":
            return random.sample(available_instruments, min(3, len(available_instruments)))
        elif size == "medium":
            return random.sample(available_instruments, min(5, len(available_instruments)))
        else:  # large
            return available_instruments

class MusicComposer:
    def __init__(self):
        self.music_theory = MusicTheory()
        self.melody_generator = MelodyGenerator(self.music_theory)
        self.rhythm_generator = RhythmGenerator()
        self.instrument_library = InstrumentLibrary()

    def compose_piece(self, title: str, genre: MusicGenre, mood: Mood,
                     target_duration: int = 180, complexity: int = 5) -> MusicComposition:
        """Compose a complete piece of music."""
        
        composition_id = str(uuid.uuid4())
        
        # Choose key and scale based on mood and genre
        compatible_scales = self.music_theory.get_compatible_scales(mood)
        scale = random.choice(compatible_scales)
        
        # Choose key (root note)
        key = random.choice(self.music_theory.notes)
        
        # Choose tempo based on mood
        tempo_range = self.music_theory.get_tempo_range(mood)
        tempo = random.randint(*tempo_range)
        
        # Choose time signature based on genre
        genre_chars = self.music_theory.genre_characteristics.get(genre, {})
        time_signatures = genre_chars.get("time_signatures", [TimeSignature.FOUR_FOUR])
        time_signature = random.choice(time_signatures)
        
        # Select instruments
        instruments = self.instrument_library.suggest_ensemble(genre, "small")
        
        # Generate sections (intro, verse, chorus, bridge, outro)
        sections = self._generate_sections(
            key, scale, tempo, time_signature, mood, complexity, target_duration
        )
        
        composition = MusicComposition(
            id=composition_id,
            title=title,
            composer="AI Music Assistant",
            genre=genre,
            mood=mood,
            key=f"{key} {scale.value}",
            tempo=tempo,
            time_signature=time_signature,
            sections=sections,
            instruments=instruments,
            arrangement_notes=self._generate_arrangement_notes(genre, instruments),
            inspiration_sources=self._generate_inspiration_sources(genre, mood),
            target_duration=target_duration,
            complexity_level=complexity,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        return composition

    def _generate_sections(self, key: str, scale: ScaleType, tempo: int,
                         time_signature: TimeSignature, mood: Mood,
                         complexity: int, target_duration: int) -> List[MusicSection]:
        """Generate musical sections for the composition."""
        
        sections = []
        
        # Calculate total bars needed
        beats_per_bar = 4 if time_signature == TimeSignature.FOUR_FOUR else 3
        beats_per_second = tempo / 60
        total_bars = int((target_duration * beats_per_second) / beats_per_bar)
        
        # Section structure
        section_plan = [
            {"name": "Intro", "bars": max(4, total_bars // 8)},
            {"name": "Main Theme A", "bars": max(8, total_bars // 4)},
            {"name": "Main Theme B", "bars": max(8, total_bars // 4)},
            {"name": "Development", "bars": max(8, total_bars // 3)},
            {"name": "Outro", "bars": max(4, total_bars // 8)}
        ]
        
        # Adjust if total is too long
        current_total = sum(s["bars"] for s in section_plan)
        if current_total > total_bars:
            scale_factor = total_bars / current_total
            for section in section_plan:
                section["bars"] = max(2, int(section["bars"] * scale_factor))
        
        scale_notes = self.music_theory.get_scale_notes(key, scale)
        
        for i, section_info in enumerate(section_plan):
            section = self._create_music_section(
                section_info["name"], section_info["bars"],
                key, scale, scale_notes, tempo, time_signature,
                mood, complexity, i == 0  # is_first_section
            )
            sections.append(section)
        
        return sections

    def _create_music_section(self, name: str, bars: int, key: str,
                            scale: ScaleType, scale_notes: List[str],
                            tempo: int, time_signature: TimeSignature,
                            mood: Mood, complexity: int, 
                            is_first_section: bool) -> MusicSection:
        """Create an individual music section."""
        
        section_id = str(uuid.uuid4())
        
        # Generate chord progression
        chord_names = self.music_theory.suggest_chord_progression(key, scale, bars)
        chord_progression = []
        
        beats_per_bar = 4 if time_signature == TimeSignature.FOUR_FOUR else 3
        
        for i, chord_name in enumerate(chord_names):
            # Parse chord name (e.g., "Cmajor" -> root="C", type="major")
            if "major" in chord_name:
                root = chord_name.replace("major", "")
                chord_type = "major"
            elif "minor" in chord_name:
                root = chord_name.replace("minor", "")
                chord_type = "minor"
            else:
                root = key
                chord_type = "major"
            
            chord = Chord(
                root=root,
                chord_type=chord_type,
                inversion=0,
                duration=beats_per_bar,
                start_time=i * beats_per_bar
            )
            chord_progression.append(chord)
        
        # Generate melody
        melody = self.melody_generator.generate_melody(
            scale_notes, bars, time_signature, mood
        )
        
        # Generate bass line
        bass_line = self._generate_bass_line(chord_progression, scale_notes, mood)
        
        # Generate rhythm
        rhythm = self.rhythm_generator.generate_rhythm(time_signature, mood, complexity)
        
        # Set dynamics based on section and mood
        dynamics = self._choose_dynamics(name, mood, is_first_section)
        
        return MusicSection(
            id=section_id,
            name=name,
            bars=bars,
            tempo=tempo,
            key=key,
            scale=scale,
            time_signature=time_signature,
            chord_progression=chord_progression,
            melody=melody,
            bass_line=bass_line,
            rhythm=rhythm,
            dynamics=dynamics,
            mood=mood
        )

    def _generate_bass_line(self, chord_progression: List[Chord], 
                          scale_notes: List[str], mood: Mood) -> List[Note]:
        """Generate a bass line that follows the chord progression."""
        bass_line = []
        
        for chord in chord_progression:
            # Use chord root as primary bass note
            bass_note = Note(
                pitch=chord.root,
                octave=2,  # Bass octave
                duration=chord.duration,
                velocity=self._get_bass_velocity(mood),
                start_time=chord.start_time
            )
            bass_line.append(bass_note)
        
        return bass_line

    def _get_bass_velocity(self, mood: Mood) -> int:
        """Get appropriate bass velocity for mood."""
        base_velocities = {
            Mood.ENERGETIC: 90,
            Mood.DRAMATIC: 85,
            Mood.HAPPY: 75,
            Mood.CALM: 60,
            Mood.SAD: 55
        }
        
        return base_velocities.get(mood, 70)

    def _choose_dynamics(self, section_name: str, mood: Mood, 
                        is_first_section: bool) -> str:
        """Choose appropriate dynamics marking."""
        
        if "Intro" in section_name or is_first_section:
            return "mp" if mood in [Mood.CALM, Mood.ROMANTIC] else "mf"
        elif "Development" in section_name or "Climax" in section_name:
            return "f" if mood in [Mood.DRAMATIC, Mood.ENERGETIC] else "mf"
        elif "Outro" in section_name:
            return "mp" if mood not in [Mood.TRIUMPHANT, Mood.ENERGETIC] else "mf"
        else:
            mood_dynamics = {
                Mood.ENERGETIC: "f",
                Mood.DRAMATIC: "f",
                Mood.HAPPY: "mf",
                Mood.CALM: "mp",
                Mood.SAD: "p",
                Mood.MYSTERIOUS: "mp"
            }
            return mood_dynamics.get(mood, "mf")

    def _generate_arrangement_notes(self, genre: MusicGenre, 
                                  instruments: List[Instrument]) -> str:
        """Generate notes about the musical arrangement."""
        
        notes = f"Arrangement for {genre.value} style featuring:\n"
        
        for instrument in instruments:
            role = self._get_instrument_role(instrument, genre)
            notes += f"- {instrument.name}: {role}\n"
        
        genre_notes = {
            MusicGenre.CLASSICAL: "Use traditional orchestral balances and formal structure",
            MusicGenre.JAZZ: "Allow space for improvisation and swing feel",
            MusicGenre.ROCK: "Emphasize rhythmic drive and power",
            MusicGenre.ELECTRONIC: "Utilize synthetic textures and electronic effects",
            MusicGenre.FOLK: "Keep arrangements simple and organic"
        }
        
        notes += f"\nStyle notes: {genre_notes.get(genre, 'Appropriate for genre')}"
        
        return notes

    def _get_instrument_role(self, instrument: Instrument, genre: MusicGenre) -> str:
        """Get the role description for an instrument in the genre."""
        
        roles = {
            "Piano": {
                MusicGenre.CLASSICAL: "Melodic lead and harmonic foundation",
                MusicGenre.JAZZ: "Comping and improvisation",
                MusicGenre.ROCK: "Harmonic support and melodic accents"
            },
            "Acoustic Guitar": {
                MusicGenre.FOLK: "Primary accompaniment and melody",
                MusicGenre.ROCK: "Rhythmic and harmonic foundation",
                MusicGenre.CLASSICAL: "Melodic voice and arpeggiation"
            },
            "Violin": {
                MusicGenre.CLASSICAL: "Primary melodic voice",
                MusicGenre.FOLK: "Ornamental and melodic lines",
                MusicGenre.WORLD: "Cultural melodic expressions"
            }
        }
        
        instrument_roles = roles.get(instrument.name, {})
        return instrument_roles.get(genre, "Supporting harmonic and melodic role")

    def _generate_inspiration_sources(self, genre: MusicGenre, mood: Mood) -> List[str]:
        """Generate inspiration sources for the composition."""
        
        sources = []
        
        # Genre-specific inspirations
        genre_inspirations = {
            MusicGenre.CLASSICAL: ["Bach's counterpoint", "Beethoven's development", "Mozart's elegance"],
            MusicGenre.JAZZ: ["Miles Davis' modal approach", "Bill Evans' harmonies", "Coltrane's spirituality"],
            MusicGenre.ROCK: ["Beatles' songcraft", "Led Zeppelin's power", "Pink Floyd's atmosphere"],
            MusicGenre.ELECTRONIC: ["Kraftwerk's innovation", "Brian Eno's ambience", "Aphex Twin's complexity"],
            MusicGenre.FOLK: ["Traditional melodies", "Storytelling tradition", "Acoustic intimacy"]
        }
        
        sources.extend(random.sample(genre_inspirations.get(genre, ["Musical tradition"]), 2))
        
        # Mood-specific inspirations
        mood_inspirations = {
            Mood.HAPPY: ["Sunny day", "Children playing", "Celebration"],
            Mood.SAD: ["Rainy evening", "Lost love", "Autumn leaves"],
            Mood.MYSTERIOUS: ["Fog at midnight", "Ancient secrets", "Hidden paths"],
            Mood.DRAMATIC: ["Storm clouds", "Epic journey", "Conflict resolution"],
            Mood.CALM: ["Still water", "Meditation", "Gentle breeze"]
        }
        
        sources.extend(random.sample(mood_inspirations.get(mood, ["Life experience"]), 2))
        
        return sources

class MusicCompositionAssistant:
    def __init__(self, db_path: str = "music_compositions.db"):
        self.db_path = db_path
        self.composer = MusicComposer()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS compositions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            composer TEXT,
            genre TEXT,
            mood TEXT,
            key_signature TEXT,
            tempo INTEGER,
            time_signature TEXT,
            sections TEXT,
            instruments TEXT,
            arrangement_notes TEXT,
            inspiration_sources TEXT,
            target_duration INTEGER,
            complexity_level INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS composition_sessions (
            id TEXT PRIMARY KEY,
            composition_id TEXT,
            session_notes TEXT,
            changes_made TEXT,
            feedback TEXT,
            created_at TEXT,
            FOREIGN KEY (composition_id) REFERENCES compositions (id)
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_composition(self, title: str, genre: str, mood: str,
                               target_duration: int = 180, 
                               complexity: int = 5) -> MusicComposition:
        """Create a new musical composition."""
        
        genre_enum = MusicGenre(genre)
        mood_enum = Mood(mood)
        
        composition = self.composer.compose_piece(
            title, genre_enum, mood_enum, target_duration, complexity
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO compositions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            composition.id, composition.title, composition.composer,
            composition.genre.value, composition.mood.value,
            composition.key, composition.tempo, composition.time_signature.value,
            json.dumps([asdict(section) for section in composition.sections]),
            json.dumps([asdict(instrument) for instrument in composition.instruments]),
            composition.arrangement_notes, json.dumps(composition.inspiration_sources),
            composition.target_duration, composition.complexity_level,
            composition.created_at, composition.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return composition

    async def get_composition(self, composition_id: str) -> Optional[MusicComposition]:
        """Retrieve a composition from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM compositions WHERE id = ?', (composition_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct objects from JSON
        sections_data = json.loads(row[8])
        sections = [MusicSection(**section_data) for section_data in sections_data]
        
        instruments_data = json.loads(row[9])
        instruments = [Instrument(**instrument_data) for instrument_data in instruments_data]
        
        return MusicComposition(
            id=row[0], title=row[1], composer=row[2],
            genre=MusicGenre(row[3]), mood=Mood(row[4]),
            key=row[5], tempo=row[6], time_signature=TimeSignature(row[7]),
            sections=sections, instruments=instruments,
            arrangement_notes=row[10], inspiration_sources=json.loads(row[11]),
            target_duration=row[12], complexity_level=row[13],
            created_at=row[14], updated_at=row[15]
        )

    async def analyze_composition(self, composition_id: str) -> Dict[str, Any]:
        """Analyze a composition and provide insights."""
        composition = await self.get_composition(composition_id)
        if not composition:
            return {"error": "Composition not found"}
        
        analysis = {
            "title": composition.title,
            "basic_info": {
                "genre": composition.genre.value,
                "mood": composition.mood.value,
                "key": composition.key,
                "tempo": f"{composition.tempo} BPM",
                "time_signature": composition.time_signature.value
            },
            "structure_analysis": self._analyze_structure(composition.sections),
            "harmonic_analysis": self._analyze_harmony(composition.sections),
            "melodic_analysis": self._analyze_melody(composition.sections),
            "instrumentation": [inst.name for inst in composition.instruments],
            "complexity_score": composition.complexity_level,
            "estimated_difficulty": self._estimate_performance_difficulty(composition),
            "suggestions": self._generate_improvement_suggestions(composition)
        }
        
        return analysis

    def _analyze_structure(self, sections: List[MusicSection]) -> Dict[str, Any]:
        """Analyze the structural aspects of the composition."""
        total_bars = sum(section.bars for section in sections)
        
        section_proportions = {}
        for section in sections:
            proportion = (section.bars / total_bars) * 100
            section_proportions[section.name] = round(proportion, 1)
        
        return {
            "total_sections": len(sections),
            "total_bars": total_bars,
            "section_proportions": section_proportions,
            "balance_assessment": "Well-balanced" if all(10 <= p <= 40 for p in section_proportions.values()) else "Consider section balance"
        }

    def _analyze_harmony(self, sections: List[MusicSection]) -> Dict[str, Any]:
        """Analyze harmonic content of the composition."""
        all_chords = []
        chord_types = {}
        
        for section in sections:
            for chord in section.chord_progression:
                all_chords.append(f"{chord.root}{chord.chord_type}")
                chord_types[chord.chord_type] = chord_types.get(chord.chord_type, 0) + 1
        
        return {
            "total_unique_chords": len(set(all_chords)),
            "chord_type_distribution": chord_types,
            "harmonic_complexity": "High" if len(set(all_chords)) > 8 else "Moderate" if len(set(all_chords)) > 4 else "Simple",
            "common_progressions": self._identify_common_progressions(all_chords)
        }

    def _identify_common_progressions(self, chords: List[str]) -> List[str]:
        """Identify common chord progressions in the piece."""
        # This is a simplified version - could be expanded
        progressions = []
        
        if len(chords) >= 4:
            # Look for I-V-vi-IV pattern (very common)
            if any("major" in chords[i] and "major" in chords[i+1] for i in range(len(chords)-3)):
                progressions.append("Pop progression elements detected")
        
        if any("7" in chord for chord in chords):
            progressions.append("Jazz harmony influences")
        
        return progressions if progressions else ["Original harmonic approach"]

    def _analyze_melody(self, sections: List[MusicSection]) -> Dict[str, Any]:
        """Analyze melodic aspects of the composition."""
        all_notes = []
        pitch_classes = {}
        
        for section in sections:
            for note in section.melody:
                all_notes.append(note)
                pitch_classes[note.pitch] = pitch_classes.get(note.pitch, 0) + 1
        
        if not all_notes:
            return {"error": "No melody to analyze"}
        
        # Calculate range
        octaves = [note.octave for note in all_notes]
        melodic_range = max(octaves) - min(octaves) if octaves else 0
        
        return {
            "total_notes": len(all_notes),
            "melodic_range": f"{melodic_range} octaves",
            "pitch_class_distribution": pitch_classes,
            "average_note_duration": round(sum(note.duration for note in all_notes) / len(all_notes), 2),
            "melodic_character": self._assess_melodic_character(all_notes)
        }

    def _assess_melodic_character(self, notes: List[Note]) -> str:
        """Assess the character of the melody."""
        if not notes or len(notes) < 2:
            return "Insufficient data"
        
        # Analyze interval sizes between consecutive notes
        intervals = []
        for i in range(len(notes) - 1):
            # Simple interval calculation (could be more sophisticated)
            curr_pitch = notes[i].octave * 12 + (ord(notes[i].pitch[0]) - ord('C'))
            next_pitch = notes[i+1].octave * 12 + (ord(notes[i+1].pitch[0]) - ord('C'))
            interval = abs(next_pitch - curr_pitch)
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        
        if avg_interval < 2:
            return "Stepwise and conjunct"
        elif avg_interval < 4:
            return "Moderately disjunct"
        else:
            return "Highly disjunct with large leaps"

    def _estimate_performance_difficulty(self, composition: MusicComposition) -> str:
        """Estimate how difficult the piece would be to perform."""
        
        difficulty_factors = 0
        
        # Tempo factor
        if composition.tempo > 140:
            difficulty_factors += 2
        elif composition.tempo > 120:
            difficulty_factors += 1
        
        # Complexity factor
        difficulty_factors += composition.complexity_level // 2
        
        # Time signature factor
        if composition.time_signature not in [TimeSignature.FOUR_FOUR, TimeSignature.THREE_FOUR]:
            difficulty_factors += 1
        
        # Instrumentation factor
        if len(composition.instruments) > 4:
            difficulty_factors += 1
        
        if difficulty_factors <= 3:
            return "Beginner"
        elif difficulty_factors <= 6:
            return "Intermediate"
        elif difficulty_factors <= 9:
            return "Advanced"
        else:
            return "Professional"

    def _generate_improvement_suggestions(self, composition: MusicComposition) -> List[str]:
        """Generate suggestions for improving the composition."""
        suggestions = []
        
        # Check section balance
        total_bars = sum(section.bars for section in composition.sections)
        for section in composition.sections:
            proportion = (section.bars / total_bars) * 100
            if proportion > 40:
                suggestions.append(f"Consider shortening the '{section.name}' section for better balance")
            elif proportion < 10:
                suggestions.append(f"Consider expanding the '{section.name}' section")
        
        # Check harmonic variety
        unique_chord_types = set()
        for section in composition.sections:
            for chord in section.chord_progression:
                unique_chord_types.add(chord.chord_type)
        
        if len(unique_chord_types) < 3:
            suggestions.append("Consider adding more chord types for harmonic interest")
        
        # Check instrumentation
        if len(composition.instruments) < 2:
            suggestions.append("Consider adding more instruments for richer texture")
        
        # Tempo suggestions based on mood
        if composition.mood == Mood.ENERGETIC and composition.tempo < 120:
            suggestions.append("Consider increasing tempo to match energetic mood")
        elif composition.mood == Mood.CALM and composition.tempo > 100:
            suggestions.append("Consider slowing tempo to enhance calm mood")
        
        return suggestions if suggestions else ["Composition appears well-balanced"]

    async def export_composition_summary(self, composition_id: str) -> Dict[str, Any]:
        """Export a comprehensive summary of the composition."""
        composition = await self.get_composition(composition_id)
        if not composition:
            return {"error": "Composition not found"}
        
        summary = {
            "composition_details": {
                "title": composition.title,
                "composer": composition.composer,
                "genre": composition.genre.value,
                "mood": composition.mood.value,
                "duration": f"{composition.target_duration // 60}:{composition.target_duration % 60:02d}",
                "complexity": composition.complexity_level
            },
            "musical_elements": {
                "key": composition.key,
                "tempo": f"{composition.tempo} BPM",
                "time_signature": composition.time_signature.value,
                "total_sections": len(composition.sections),
                "instruments": [inst.name for inst in composition.instruments]
            },
            "sections": [
                {
                    "name": section.name,
                    "bars": section.bars,
                    "key": section.key,
                    "tempo": section.tempo,
                    "mood": section.mood.value,
                    "chord_count": len(section.chord_progression),
                    "melody_notes": len(section.melody)
                }
                for section in composition.sections
            ],
            "arrangement_notes": composition.arrangement_notes,
            "inspiration_sources": composition.inspiration_sources,
            "created_at": composition.created_at
        }
        
        return summary

if __name__ == "__main__":
    async def main():
        assistant = MusicCompositionAssistant()
        
        # Create a sample composition
        composition = await assistant.create_composition(
            title="Mystic Journey",
            genre="ambient",
            mood="mysterious",
            target_duration=240,  # 4 minutes
            complexity=6
        )
        
        print(f"Created composition: {composition.title}")
        print(f"Genre: {composition.genre.value}")
        print(f"Mood: {composition.mood.value}")
        print(f"Key: {composition.key}")
        print(f"Tempo: {composition.tempo} BPM")
        print(f"Sections: {len(composition.sections)}")
        print(f"Instruments: {[inst.name for inst in composition.instruments]}")
        
        # Analyze the composition
        analysis = await assistant.analyze_composition(composition.id)
        print(f"\nStructural Analysis:")
        print(f"Total sections: {analysis['structure_analysis']['total_sections']}")
        print(f"Total bars: {analysis['structure_analysis']['total_bars']}")
        print(f"Balance assessment: {analysis['structure_analysis']['balance_assessment']}")
        
        print(f"\nHarmonic Analysis:")
        print(f"Harmonic complexity: {analysis['harmonic_analysis']['harmonic_complexity']}")
        print(f"Unique chords: {analysis['harmonic_analysis']['total_unique_chords']}")
        
        print(f"\nPerformance difficulty: {analysis['estimated_difficulty']}")
        
        if analysis['suggestions']:
            print(f"\nSuggestions:")
            for suggestion in analysis['suggestions'][:3]:
                print(f"- {suggestion}")
    
    asyncio.run(main())