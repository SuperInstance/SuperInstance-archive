"""
Music Notation Translation System

This module provides comprehensive translation capabilities between different musical
notation systems, including staff notation, tablature, chord symbols, and various
cultural musical notations.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from datetime import datetime, timedelta
import numpy as np

class NotationSystem(Enum):
    """Supported musical notation systems"""
    WESTERN_STAFF = "western_staff"
    TABLATURE = "tablature"
    CHORD_SYMBOLS = "chord_symbols"
    NASHVILLE_NUMBERS = "nashville_numbers"
    ROMAN_NUMERALS = "roman_numerals"
    SOLFEGE = "solfege"
    INDIAN_SARGAM = "indian_sargam"
    CHINESE_JIANPU = "chinese_jianpu"
    LEAD_SHEET = "lead_sheet"
    DRUM_NOTATION = "drum_notation"
    FINGERING_CHART = "fingering_chart"
    ABC_NOTATION = "abc_notation"

class Instrument(Enum):
    """Supported instruments"""
    PIANO = "piano"
    GUITAR = "guitar"
    VIOLIN = "violin"
    DRUMS = "drums"
    BASS = "bass"
    SAXOPHONE = "saxophone"
    TRUMPET = "trumpet"
    FLUTE = "flute"
    VOICE = "voice"
    MANDOLIN = "mandolin"
    BANJO = "banjo"
    UKULELE = "ukulele"

class TimeSignature:
    """Represents musical time signature"""
    def __init__(self, numerator: int, denominator: int):
        self.numerator = numerator
        self.denominator = denominator
    
    def __str__(self):
        return f"{self.numerator}/{self.denominator}"

class KeySignature:
    """Represents musical key signature"""
    def __init__(self, key: str, mode: str = "major"):
        self.key = key
        self.mode = mode
        self.sharps_flats = self._calculate_accidentals()
    
    def _calculate_accidentals(self) -> List[str]:
        """Calculate sharps and flats for the key"""
        major_keys = {
            "C": [], "G": ["F#"], "D": ["F#", "C#"], "A": ["F#", "C#", "G#"],
            "E": ["F#", "C#", "G#", "D#"], "B": ["F#", "C#", "G#", "D#", "A#"],
            "F#": ["F#", "C#", "G#", "D#", "A#", "E#"],
            "F": ["Bb"], "Bb": ["Bb", "Eb"], "Eb": ["Bb", "Eb", "Ab"],
            "Ab": ["Bb", "Eb", "Ab", "Db"], "Db": ["Bb", "Eb", "Ab", "Db", "Gb"],
            "Gb": ["Bb", "Eb", "Ab", "Db", "Gb", "Cb"]
        }
        return major_keys.get(self.key, [])
    
    def __str__(self):
        return f"{self.key} {self.mode}"

@dataclass
class Note:
    """Represents a musical note"""
    pitch: str  # e.g., "C4", "F#5", "Bb3"
    duration: str  # e.g., "quarter", "eighth", "whole"
    velocity: int = 64  # MIDI velocity (0-127)
    articulation: Optional[str] = None  # staccato, legato, accent, etc.
    tie: bool = False
    rest: bool = False
    
    def to_midi_note(self) -> int:
        """Convert note to MIDI note number"""
        note_map = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, 
                   "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, 
                   "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
        
        if self.rest:
            return -1
        
        # Extract pitch class and octave
        pitch_match = re.match(r'([A-G][b#]?)(\d+)', self.pitch)
        if pitch_match:
            pitch_class = pitch_match.group(1)
            octave = int(pitch_match.group(2))
            return note_map[pitch_class] + (octave * 12)
        return 60  # Default to middle C

@dataclass
class Chord:
    """Represents a musical chord"""
    root: str
    quality: str  # major, minor, dominant7, etc.
    bass: Optional[str] = None
    extensions: List[str] = field(default_factory=list)
    
    def to_notes(self) -> List[str]:
        """Convert chord to constituent notes"""
        chord_tones = {
            "major": [0, 4, 7],
            "minor": [0, 3, 7],
            "diminished": [0, 3, 6],
            "augmented": [0, 4, 8],
            "dominant7": [0, 4, 7, 10],
            "major7": [0, 4, 7, 11],
            "minor7": [0, 3, 7, 10]
        }
        
        intervals = chord_tones.get(self.quality, [0, 4, 7])
        root_note = Note(f"{self.root}4", "quarter").to_midi_note() % 12
        
        chord_notes = []
        for interval in intervals:
            midi_note = root_note + interval
            note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
            note_name = note_names[midi_note % 12]
            chord_notes.append(f"{note_name}4")
        
        return chord_notes

@dataclass
class Measure:
    """Represents a musical measure"""
    notes: List[Note]
    chords: List[Chord] = field(default_factory=list)
    time_signature: Optional[TimeSignature] = None
    measure_number: int = 1
    
    def get_total_duration(self) -> float:
        """Calculate total duration of notes in measure"""
        duration_map = {"whole": 1.0, "half": 0.5, "quarter": 0.25, "eighth": 0.125, "sixteenth": 0.0625}
        return sum(duration_map.get(note.duration, 0.25) for note in self.notes)

@dataclass
class MusicalScore:
    """Represents a complete musical score"""
    title: str
    composer: Optional[str]
    key_signature: KeySignature
    time_signature: TimeSignature
    tempo: int  # BPM
    measures: List[Measure]
    instruments: List[Instrument] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class NotationTranslationResult:
    """Result of music notation translation"""
    source_notation: NotationSystem
    target_notation: NotationSystem
    source_score: str
    translated_score: str
    confidence: float
    processing_time: float
    translation_notes: List[str]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class MusicParser:
    """Parses various musical notation formats"""
    
    def __init__(self):
        self.parsers = {
            NotationSystem.ABC_NOTATION: self._parse_abc,
            NotationSystem.CHORD_SYMBOLS: self._parse_chord_symbols,
            NotationSystem.TABLATURE: self._parse_tablature,
            NotationSystem.SOLFEGE: self._parse_solfege
        }
    
    async def parse_notation(self, notation_text: str, notation_system: NotationSystem) -> MusicalScore:
        """Parse musical notation text into structured format"""
        parser = self.parsers.get(notation_system, self._parse_generic)
        return await parser(notation_text)
    
    async def _parse_abc(self, abc_text: str) -> MusicalScore:
        """Parse ABC notation"""
        lines = abc_text.strip().split('\n')
        
        # Extract headers
        title = "Untitled"
        composer = None
        key_signature = KeySignature("C", "major")
        time_signature = TimeSignature(4, 4)
        tempo = 120
        
        music_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('T:'):
                title = line[2:].strip()
            elif line.startswith('C:'):
                composer = line[2:].strip()
            elif line.startswith('K:'):
                key_str = line[2:].strip()
                key_signature = KeySignature(key_str)
            elif line.startswith('M:'):
                time_str = line[2:].strip()
                if '/' in time_str:
                    num, den = map(int, time_str.split('/'))
                    time_signature = TimeSignature(num, den)
            elif line.startswith('Q:'):
                tempo = int(line[2:].strip())
            elif line and not line.startswith(('T:', 'C:', 'K:', 'M:', 'Q:', 'X:')):
                music_lines.append(line)
        
        # Parse music content
        measures = await self._parse_abc_music(' '.join(music_lines))
        
        return MusicalScore(
            title=title,
            composer=composer,
            key_signature=key_signature,
            time_signature=time_signature,
            tempo=tempo,
            measures=measures
        )
    
    async def _parse_abc_music(self, music_text: str) -> List[Measure]:
        """Parse ABC music notation into measures"""
        measures = []
        
        # Split by bar lines
        measure_texts = music_text.split('|')
        
        for i, measure_text in enumerate(measure_texts):
            measure_text = measure_text.strip()
            if not measure_text:
                continue
            
            notes = []
            
            # Simple note parsing (basic implementation)
            note_pattern = r'([A-Ga-g][#b]?)(\d*)'
            matches = re.findall(note_pattern, measure_text)
            
            for match in matches:
                pitch_class = match[0].upper()
                duration_marker = match[1]
                
                # Determine octave based on case
                octave = 4 if match[0].isupper() else 5
                pitch = f"{pitch_class}{octave}"
                
                # Determine duration from marker
                if duration_marker == '2':
                    duration = "half"
                elif duration_marker == '4':
                    duration = "quarter"
                elif duration_marker == '8':
                    duration = "eighth"
                else:
                    duration = "quarter"  # default
                
                note = Note(pitch=pitch, duration=duration)
                notes.append(note)
            
            if notes:
                measure = Measure(notes=notes, measure_number=i+1)
                measures.append(measure)
        
        return measures
    
    async def _parse_chord_symbols(self, chord_text: str) -> MusicalScore:
        """Parse chord symbol notation"""
        chord_lines = chord_text.strip().split('\n')
        measures = []
        
        for i, line in enumerate(chord_lines):
            chords = []
            chord_symbols = line.split()
            
            for symbol in chord_symbols:
                chord = await self._parse_single_chord(symbol)
                if chord:
                    chords.append(chord)
            
            if chords:
                # Create notes from chord tones
                notes = []
                for chord in chords:
                    chord_notes = chord.to_notes()
                    for note_pitch in chord_notes:
                        note = Note(pitch=note_pitch, duration="quarter")
                        notes.append(note)
                
                measure = Measure(notes=notes, chords=chords, measure_number=i+1)
                measures.append(measure)
        
        return MusicalScore(
            title="Chord Progression",
            composer=None,
            key_signature=KeySignature("C", "major"),
            time_signature=TimeSignature(4, 4),
            tempo=120,
            measures=measures
        )
    
    async def _parse_single_chord(self, chord_symbol: str) -> Optional[Chord]:
        """Parse a single chord symbol"""
        # Basic chord parsing
        chord_pattern = r'^([A-G][#b]?)(m|maj|dim|aug|\+)?(7|9|11|13)?(/([A-G][#b]?))?$'
        match = re.match(chord_pattern, chord_symbol)
        
        if match:
            root = match.group(1)
            quality_marker = match.group(2) or ""
            extension = match.group(3)
            bass = match.group(5)
            
            # Determine chord quality
            if quality_marker == "m":
                quality = "minor"
            elif quality_marker in ["maj", ""]:
                quality = "major"
            elif quality_marker == "dim":
                quality = "diminished"
            elif quality_marker in ["aug", "+"]:
                quality = "augmented"
            else:
                quality = "major"
            
            # Add extension to quality
            if extension == "7":
                quality = "dominant7" if quality == "major" else "minor7"
            elif extension in ["9", "11", "13"]:
                quality = f"{quality}{extension}"
            
            return Chord(root=root, quality=quality, bass=bass)
        
        return None
    
    async def _parse_tablature(self, tab_text: str) -> MusicalScore:
        """Parse guitar tablature"""
        lines = tab_text.strip().split('\n')
        
        # Find tablature lines (usually 6 lines for guitar)
        tab_lines = []
        for line in lines:
            if re.match(r'^[eEaAdDgGbB]\|', line) or re.match(r'^\d+\|', line):
                tab_lines.append(line)
        
        measures = []
        if len(tab_lines) >= 6:  # Standard guitar tuning
            # Parse fret numbers from tablature
            measure = Measure(notes=[], measure_number=1)
            
            # Simple parsing - extract fret numbers
            for line in tab_lines[:6]:
                fret_numbers = re.findall(r'\d+', line)
                for fret in fret_numbers[:4]:  # Limit to 4 notes per measure
                    # Convert fret to note (simplified)
                    string_pitches = ["E2", "A2", "D3", "G3", "B3", "E4"]  # Standard tuning
                    string_idx = tab_lines.index(line) % 6
                    base_pitch = string_pitches[string_idx]
                    
                    # Calculate actual pitch from fret
                    base_midi = Note(base_pitch, "quarter").to_midi_note()
                    fret_midi = base_midi + int(fret)
                    
                    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
                    octave = fret_midi // 12
                    note_name = note_names[fret_midi % 12]
                    
                    note = Note(pitch=f"{note_name}{octave}", duration="quarter")
                    measure.notes.append(note)
            
            measures.append(measure)
        
        return MusicalScore(
            title="Guitar Tablature",
            composer=None,
            key_signature=KeySignature("C", "major"),
            time_signature=TimeSignature(4, 4),
            tempo=120,
            measures=measures,
            instruments=[Instrument.GUITAR]
        )
    
    async def _parse_solfege(self, solfege_text: str) -> MusicalScore:
        """Parse solfege notation"""
        solfege_map = {
            "do": "C", "re": "D", "mi": "E", "fa": "F", 
            "sol": "G", "la": "A", "ti": "B"
        }
        
        words = solfege_text.lower().split()
        notes = []
        
        for word in words:
            # Remove punctuation and get base solfege syllable
            clean_word = re.sub(r'[^\w]', '', word)
            
            if clean_word in solfege_map:
                pitch_class = solfege_map[clean_word]
                note = Note(pitch=f"{pitch_class}4", duration="quarter")
                notes.append(note)
        
        measure = Measure(notes=notes, measure_number=1)
        
        return MusicalScore(
            title="Solfege Exercise",
            composer=None,
            key_signature=KeySignature("C", "major"),
            time_signature=TimeSignature(4, 4),
            tempo=120,
            measures=[measure]
        )
    
    async def _parse_generic(self, notation_text: str) -> MusicalScore:
        """Generic parser for unknown notation systems"""
        return MusicalScore(
            title="Unknown Notation",
            composer=None,
            key_signature=KeySignature("C", "major"),
            time_signature=TimeSignature(4, 4),
            tempo=120,
            measures=[]
        )

class NotationGenerator:
    """Generates various musical notation formats"""
    
    def __init__(self):
        self.generators = {
            NotationSystem.ABC_NOTATION: self._generate_abc,
            NotationSystem.CHORD_SYMBOLS: self._generate_chord_symbols,
            NotationSystem.TABLATURE: self._generate_tablature,
            NotationSystem.SOLFEGE: self._generate_solfege,
            NotationSystem.NASHVILLE_NUMBERS: self._generate_nashville,
            NotationSystem.ROMAN_NUMERALS: self._generate_roman_numerals,
            NotationSystem.INDIAN_SARGAM: self._generate_sargam,
            NotationSystem.CHINESE_JIANPU: self._generate_jianpu
        }
    
    async def generate_notation(self, score: MusicalScore, target_system: NotationSystem) -> str:
        """Generate notation in target system"""
        generator = self.generators.get(target_system, self._generate_generic)
        return await generator(score)
    
    async def _generate_abc(self, score: MusicalScore) -> str:
        """Generate ABC notation"""
        abc_text = f"X:1\nT:{score.title}\n"
        if score.composer:
            abc_text += f"C:{score.composer}\n"
        
        abc_text += f"M:{score.time_signature}\n"
        abc_text += f"K:{score.key_signature.key}\n"
        abc_text += f"Q:{score.tempo}\n"
        
        for measure in score.measures:
            abc_text += "|"
            for note in measure.notes:
                if note.rest:
                    abc_text += "z"
                else:
                    # Extract pitch class and octave
                    pitch_match = re.match(r'([A-G][#b]?)(\d+)', note.pitch)
                    if pitch_match:
                        pitch_class = pitch_match.group(1)
                        octave = int(pitch_match.group(2))
                        
                        # ABC uses case to indicate octave
                        if octave >= 5:
                            abc_note = pitch_class.lower()
                        else:
                            abc_note = pitch_class.upper()
                        
                        # Add duration modifier
                        if note.duration == "half":
                            abc_note += "2"
                        elif note.duration == "eighth":
                            abc_note += "/2"
                        elif note.duration == "sixteenth":
                            abc_note += "/4"
                        
                        abc_text += abc_note
        
        abc_text += "|"
        return abc_text
    
    async def _generate_chord_symbols(self, score: MusicalScore) -> str:
        """Generate chord symbol notation"""
        chord_text = ""
        
        for measure in score.measures:
            if measure.chords:
                chord_symbols = []
                for chord in measure.chords:
                    symbol = chord.root
                    
                    if chord.quality == "minor":
                        symbol += "m"
                    elif chord.quality == "dominant7":
                        symbol += "7"
                    elif chord.quality == "major7":
                        symbol += "maj7"
                    elif chord.quality == "minor7":
                        symbol += "m7"
                    elif chord.quality == "diminished":
                        symbol += "dim"
                    elif chord.quality == "augmented":
                        symbol += "aug"
                    
                    if chord.bass:
                        symbol += f"/{chord.bass}"
                    
                    chord_symbols.append(symbol)
                
                chord_text += " ".join(chord_symbols) + "\n"
            else:
                # Generate chords from notes (basic harmonization)
                if measure.notes:
                    root_note = measure.notes[0].pitch[0]  # Get pitch class
                    chord_text += f"{root_note}\n"
        
        return chord_text.strip()
    
    async def _generate_tablature(self, score: MusicalScore) -> str:
        """Generate guitar tablature"""
        if Instrument.GUITAR not in score.instruments and score.instruments:
            return "Tablature generation requires guitar as target instrument"
        
        # Standard guitar tuning (6th to 1st string)
        string_tunings = [40, 45, 50, 55, 59, 64]  # MIDI note numbers for E2, A2, D3, G3, B3, E4
        tab_lines = ["e|", "B|", "G|", "D|", "A|", "E|"]
        
        for measure in score.measures:
            for note in measure.notes:
                if note.rest:
                    for i in range(6):
                        tab_lines[i] += "-"
                else:
                    midi_note = note.to_midi_note()
                    
                    # Find best string and fret
                    best_string = 0
                    best_fret = 12  # High fret number as default
                    
                    for string_idx, string_tuning in enumerate(string_tunings):
                        if midi_note >= string_tuning:
                            fret = midi_note - string_tuning
                            if 0 <= fret <= 12 and fret < best_fret:
                                best_string = string_idx
                                best_fret = fret
                    
                    # Add fret numbers to tablature
                    for i in range(6):
                        if i == (5 - best_string):  # Reverse order for display
                            tab_lines[i] += str(best_fret) if best_fret < 10 else "X"
                        else:
                            tab_lines[i] += "-"
        
        return "\n".join(tab_lines)
    
    async def _generate_solfege(self, score: MusicalScore) -> str:
        """Generate solfege notation"""
        solfege_map = {
            "C": "do", "D": "re", "E": "mi", "F": "fa",
            "G": "sol", "A": "la", "B": "ti"
        }
        
        # Adjust for key signature
        key_note = score.key_signature.key
        key_offset = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}.get(key_note, 0)
        
        solfege_syllables = []
        
        for measure in score.measures:
            for note in measure.notes:
                if note.rest:
                    solfege_syllables.append("rest")
                else:
                    pitch_class = note.pitch[:-1]  # Remove octave
                    # Handle sharps/flats
                    if "#" in pitch_class:
                        pitch_class = pitch_class[0]
                        sharp = True
                    elif "b" in pitch_class:
                        pitch_class = pitch_class[0]
                        flat = True
                    else:
                        sharp = flat = False
                    
                    if pitch_class in solfege_map:
                        syllable = solfege_map[pitch_class]
                        if sharp:
                            syllable += "i"  # Sharp indication
                        elif flat:
                            syllable += "e"  # Flat indication
                        solfege_syllables.append(syllable)
        
        return " ".join(solfege_syllables)
    
    async def _generate_nashville(self, score: MusicalScore) -> str:
        """Generate Nashville number system notation"""
        key_note = score.key_signature.key
        
        # Major scale degrees
        scale_degrees = {
            "C": 1, "D": 2, "E": 3, "F": 4, "G": 5, "A": 6, "B": 7
        }
        
        # Transpose to key center
        key_degree = scale_degrees.get(key_note, 1)
        
        nashville_numbers = []
        
        for measure in score.measures:
            measure_numbers = []
            
            if measure.chords:
                for chord in measure.chords:
                    root_degree = scale_degrees.get(chord.root, 1)
                    # Adjust for key
                    adjusted_degree = ((root_degree - key_degree) % 7) + 1
                    
                    number = str(adjusted_degree)
                    if chord.quality == "minor":
                        number = number.lower()
                    elif chord.quality == "diminished":
                        number += "°"
                    elif chord.quality in ["dominant7", "major7"]:
                        number += "7"
                    
                    measure_numbers.append(number)
            else:
                # Generate numbers from melody
                for note in measure.notes:
                    if not note.rest:
                        pitch_class = note.pitch[0]
                        degree = scale_degrees.get(pitch_class, 1)
                        adjusted_degree = ((degree - key_degree) % 7) + 1
                        measure_numbers.append(str(adjusted_degree))
            
            if measure_numbers:
                nashville_numbers.extend(measure_numbers)
        
        return " | ".join(nashville_numbers)
    
    async def _generate_roman_numerals(self, score: MusicalScore) -> str:
        """Generate Roman numeral analysis"""
        major_numerals = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
        minor_numerals = ["i", "ii°", "III", "iv", "v", "VI", "VII"]
        
        is_minor = score.key_signature.mode == "minor"
        numerals = minor_numerals if is_minor else major_numerals
        
        key_note = score.key_signature.key
        scale_degrees = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
        key_degree = scale_degrees.get(key_note, 0)
        
        roman_analysis = []
        
        for measure in score.measures:
            if measure.chords:
                for chord in measure.chords:
                    root_degree = scale_degrees.get(chord.root, 0)
                    adjusted_degree = (root_degree - key_degree) % 7
                    
                    numeral = numerals[adjusted_degree]
                    
                    if chord.quality in ["dominant7", "major7", "minor7"]:
                        numeral += "7"
                    
                    roman_analysis.append(numeral)
        
        return " - ".join(roman_analysis)
    
    async def _generate_sargam(self, score: MusicalScore) -> str:
        """Generate Indian Sargam notation"""
        sargam_map = {
            "C": "Sa", "D": "Re", "E": "Ga", "F": "Ma",
            "G": "Pa", "A": "Dha", "B": "Ni"
        }
        
        sargam_syllables = []
        
        for measure in score.measures:
            for note in measure.notes:
                if note.rest:
                    sargam_syllables.append("_")
                else:
                    pitch_class = note.pitch[0]
                    if pitch_class in sargam_map:
                        syllable = sargam_map[pitch_class]
                        
                        # Add octave indicators
                        octave = int(note.pitch[-1])
                        if octave < 4:
                            syllable = syllable.lower()  # Lower octave
                        elif octave > 5:
                            syllable += "'"  # Higher octave
                        
                        sargam_syllables.append(syllable)
        
        return " ".join(sargam_syllables)
    
    async def _generate_jianpu(self, score: MusicalScore) -> str:
        """Generate Chinese Jianpu number notation"""
        number_map = {
            "C": "1", "D": "2", "E": "3", "F": "4",
            "G": "5", "A": "6", "B": "7"
        }
        
        jianpu_numbers = []
        
        for measure in score.measures:
            for note in measure.notes:
                if note.rest:
                    jianpu_numbers.append("0")
                else:
                    pitch_class = note.pitch[0]
                    if pitch_class in number_map:
                        number = number_map[pitch_class]
                        
                        # Add octave indicators
                        octave = int(note.pitch[-1])
                        if octave < 4:
                            number = number.lower()
                        elif octave > 5:
                            number += "·"  # Dot above
                        
                        jianpu_numbers.append(number)
        
        return " ".join(jianpu_numbers)
    
    async def _generate_generic(self, score: MusicalScore) -> str:
        """Generic notation generator"""
        return f"Title: {score.title}\nKey: {score.key_signature}\nTime: {score.time_signature}\nTempo: {score.tempo} BPM\nMeasures: {len(score.measures)}"

class MusicNotationTranslationSystem:
    """Main system for music notation translation"""
    
    def __init__(self):
        self.parser = MusicParser()
        self.generator = NotationGenerator()
    
    async def translate_notation(self, source_notation: str, 
                               source_system: NotationSystem,
                               target_system: NotationSystem,
                               instrument: Optional[Instrument] = None) -> NotationTranslationResult:
        """Translate between musical notation systems"""
        start_time = datetime.now()
        
        try:
            # Step 1: Parse source notation
            musical_score = await self.parser.parse_notation(source_notation, source_system)
            
            # Step 2: Add instrument information if provided
            if instrument and instrument not in musical_score.instruments:
                musical_score.instruments.append(instrument)
            
            # Step 3: Generate target notation
            translated_notation = await self.generator.generate_notation(musical_score, target_system)
            
            # Step 4: Calculate confidence and generate notes
            confidence = await self._calculate_confidence(source_system, target_system, musical_score)
            translation_notes = await self._generate_translation_notes(source_system, target_system)
            warnings = await self._generate_warnings(source_system, target_system, musical_score)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return NotationTranslationResult(
                source_notation=source_system,
                target_notation=target_system,
                source_score=source_notation,
                translated_score=translated_notation,
                confidence=confidence,
                processing_time=processing_time,
                translation_notes=translation_notes,
                warnings=warnings,
                metadata={
                    "parsed_measures": len(musical_score.measures),
                    "key_signature": str(musical_score.key_signature),
                    "time_signature": str(musical_score.time_signature),
                    "tempo": musical_score.tempo,
                    "instruments": [inst.value for inst in musical_score.instruments]
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return NotationTranslationResult(
                source_notation=source_system,
                target_notation=target_system,
                source_score=source_notation,
                translated_score=f"Translation error: {str(e)}",
                confidence=0.0,
                processing_time=processing_time,
                translation_notes=[f"Error during translation: {str(e)}"],
                warnings=["Translation failed due to parsing or generation error"]
            )
    
    async def _calculate_confidence(self, source_system: NotationSystem, 
                                  target_system: NotationSystem, 
                                  score: MusicalScore) -> float:
        """Calculate translation confidence"""
        base_confidence = 0.8
        
        # System compatibility matrix
        compatibility = {
            (NotationSystem.ABC_NOTATION, NotationSystem.WESTERN_STAFF): 0.95,
            (NotationSystem.CHORD_SYMBOLS, NotationSystem.NASHVILLE_NUMBERS): 0.9,
            (NotationSystem.CHORD_SYMBOLS, NotationSystem.ROMAN_NUMERALS): 0.85,
            (NotationSystem.SOLFEGE, NotationSystem.ABC_NOTATION): 0.8,
            (NotationSystem.TABLATURE, NotationSystem.WESTERN_STAFF): 0.7,
        }
        
        # Check direct compatibility
        direct_compat = compatibility.get((source_system, target_system))
        if direct_compat:
            base_confidence = direct_compat
        
        # Adjust based on score complexity
        measure_count = len(score.measures)
        if measure_count > 0:
            avg_notes_per_measure = sum(len(m.notes) for m in score.measures) / measure_count
            complexity_factor = min(avg_notes_per_measure / 8, 1.0)  # Normalize to 8 notes per measure
            base_confidence *= (1.0 - complexity_factor * 0.2)
        
        return min(base_confidence, 1.0)
    
    async def _generate_translation_notes(self, source_system: NotationSystem, 
                                        target_system: NotationSystem) -> List[str]:
        """Generate notes about the translation process"""
        notes = []
        
        if source_system == NotationSystem.TABLATURE and target_system == NotationSystem.WESTERN_STAFF:
            notes.append("Tablature conversion assumes standard guitar tuning")
            notes.append("Rhythm information may be approximate")
        
        if target_system == NotationSystem.SOLFEGE:
            notes.append("Solfege uses moveable do system")
            notes.append("Accidentals indicated with 'i' (sharp) and 'e' (flat)")
        
        if target_system == NotationSystem.NASHVILLE_NUMBERS:
            notes.append("Numbers relative to key center")
            notes.append("Minor chords shown in lowercase")
        
        if source_system == NotationSystem.CHORD_SYMBOLS:
            notes.append("Rhythm and voicing inferred from chord symbols")
        
        return notes
    
    async def _generate_warnings(self, source_system: NotationSystem, 
                               target_system: NotationSystem, 
                               score: MusicalScore) -> List[str]:
        """Generate warnings about potential translation issues"""
        warnings = []
        
        if not score.measures:
            warnings.append("No musical content was parsed from source")
        
        if source_system == NotationSystem.TABLATURE and target_system != NotationSystem.WESTERN_STAFF:
            warnings.append("Tablature source may lose instrument-specific information")
        
        if target_system == NotationSystem.TABLATURE and Instrument.GUITAR not in score.instruments:
            warnings.append("Tablature output assumes guitar - specify instrument for better results")
        
        # Check for complex time signatures
        if score.time_signature and (score.time_signature.numerator > 4 or score.time_signature.denominator > 4):
            if target_system in [NotationSystem.SOLFEGE, NotationSystem.NASHVILLE_NUMBERS]:
                warnings.append("Complex time signatures may not translate well to simplified notation")
        
        return warnings
    
    async def batch_translate_scores(self, scores: List[Tuple[str, NotationSystem]], 
                                   target_system: NotationSystem,
                                   instrument: Optional[Instrument] = None) -> List[NotationTranslationResult]:
        """Translate multiple scores in batch"""
        tasks = [
            self.translate_notation(score, source_system, target_system, instrument)
            for score, source_system in scores
        ]
        
        return await asyncio.gather(*tasks)

# Example usage
async def main():
    """Example usage of music notation translation system"""
    
    # Initialize the system
    translator = MusicNotationTranslationSystem()
    
    print("Music Notation Translation System Demo")
    print("=" * 50)
    
    # Example 1: ABC to Chord Symbols
    abc_tune = '''X:1
T:Mary Had a Little Lamb
M:4/4
K:C
Q:120
|C D E C | C D E C | E E E2 | D D D2 |
|C D E C | C D E C | E E D D | C4 |'''
    
    print("Original ABC notation:")
    print(abc_tune)
    print("\n" + "=" * 30)
    
    result1 = await translator.translate_notation(
        source_notation=abc_tune,
        source_system=NotationSystem.ABC_NOTATION,
        target_system=NotationSystem.CHORD_SYMBOLS
    )
    
    print(f"Translated to chord symbols:")
    print(result1.translated_score)
    print(f"Confidence: {result1.confidence:.3f}")
    print(f"Processing time: {result1.processing_time:.2f}s")
    
    # Example 2: Chord symbols to Nashville Numbers
    print("\n" + "=" * 50)
    chord_progression = '''C Am F G
C Am F G C'''
    
    print(f"Chord progression: {chord_progression}")
    
    result2 = await translator.translate_notation(
        source_notation=chord_progression,
        source_system=NotationSystem.CHORD_SYMBOLS,
        target_system=NotationSystem.NASHVILLE_NUMBERS
    )
    
    print(f"Nashville numbers: {result2.translated_score}")
    print(f"Confidence: {result2.confidence:.3f}")
    
    # Example 3: Solfege to ABC
    print("\n" + "=" * 50)
    solfege_scale = "do re mi fa sol la ti do"
    
    result3 = await translator.translate_notation(
        source_notation=solfege_scale,
        source_system=NotationSystem.SOLFEGE,
        target_system=NotationSystem.ABC_NOTATION
    )
    
    print(f"Solfege: {solfege_scale}")
    print(f"ABC notation: {result3.translated_score}")
    
    # Show translation notes and warnings
    if result3.translation_notes:
        print("\nTranslation notes:")
        for note in result3.translation_notes:
            print(f"  📝 {note}")
    
    if result3.warnings:
        print("\nWarnings:")
        for warning in result3.warnings:
            print(f"  ⚠️  {warning}")

if __name__ == "__main__":
    asyncio.run(main())