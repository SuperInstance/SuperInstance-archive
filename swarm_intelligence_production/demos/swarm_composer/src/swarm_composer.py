"""
SwarmComposer - Distributed Music Generation System
Revolutionary music creation through multi-swarm intelligence
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import mido
import numpy as np


class MusicalScale(Enum):
    """Musical scales for composition"""
    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    MINOR = [0, 2, 3, 5, 7, 8, 10]
    PENTATONIC = [0, 2, 4, 7, 9]
    BLUES = [0, 3, 5, 6, 7, 10]
    CHROMATIC = list(range(12))


@dataclass
class MusicalNote:
    """Individual musical note representation"""
    pitch: int  # MIDI pitch (0-127)
    velocity: int  # Volume (0-127)
    duration: float  # Duration in beats
    time: float  # Start time in beats


@dataclass
class MusicalPhrase:
    """Collection of notes forming a phrase"""
    notes: List[MusicalNote]
    key: str
    scale: MusicalScale
    tempo: int


@dataclass
class ListenerPreference:
    """Real-time listener preference data"""
    energy_level: float  # 0-1
    complexity_preference: float  # 0-1
    tempo_preference: int  # BPM
    mood: str  # "upbeat", "mellow", "dramatic", etc.
    favorite_instruments: List[str]


class MelodySwarmAgent:
    """Individual agent exploring melodic space"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.fitness = 0.0
        self.current_melody: List[MusicalNote] = []
        self.exploration_rate = 0.3

    def generate_melody(self, key: str, scale: MusicalScale,
                       length: int = 16) -> List[MusicalNote]:
        """Generate a melodic phrase"""
        melody = []
        root_note = self._key_to_midi(key)
        scale_notes = [root_note + interval for interval in scale.value]

        current_time = 0.0
        for i in range(length):
            # Melodic contour using random walk with constraints
            if i == 0:
                pitch = np.random.choice(scale_notes)
            else:
                # Prefer stepwise motion
                prev_pitch = melody[-1].pitch
                step = np.random.choice([-2, -1, 0, 1, 2],
                                       p=[0.1, 0.3, 0.2, 0.3, 0.1])
                pitch = prev_pitch + step

                # Constrain to scale
                pitch = min(max(pitch, scale_notes[0]), scale_notes[-1])

            velocity = np.random.randint(60, 100)
            duration = np.random.choice([0.5, 1.0, 1.5, 2.0],
                                       p=[0.3, 0.4, 0.2, 0.1])

            note = MusicalNote(pitch, velocity, duration, current_time)
            melody.append(note)
            current_time += duration

        self.current_melody = melody
        return melody

    def _key_to_midi(self, key: str) -> int:
        """Convert key string to MIDI note number"""
        note_map = {'C': 60, 'D': 62, 'E': 64, 'F': 65,
                   'G': 67, 'A': 69, 'B': 71}
        return note_map.get(key, 60)

    def evaluate_melody(self, listener_prefs: ListenerPreference) -> float:
        """Evaluate melody fitness based on listener preferences"""
        if not self.current_melody:
            return 0.0

        # Calculate contour variety
        pitches = [note.pitch for note in self.current_melody]
        intervals = [pitches[i+1] - pitches[i]
                    for i in range(len(pitches)-1)]
        contour_variety = len(set(intervals)) / len(intervals) if intervals else 0

        # Calculate rhythmic interest
        durations = [note.duration for note in self.current_melody]
        rhythm_variety = len(set(durations)) / len(durations) if durations else 0

        # Match complexity to preference
        complexity = (contour_variety + rhythm_variety) / 2
        complexity_match = 1 - abs(complexity - listener_prefs.complexity_preference)

        self.fitness = complexity_match
        return self.fitness


class MelodySwarm:
    """Swarm of agents exploring melodic possibilities"""

    def __init__(self, size: int = 100):
        self.agents = [MelodySwarmAgent(i) for i in range(size)]
        self.best_melody: Optional[List[MusicalNote]] = None
        self.best_fitness = 0.0

    async def evolve_melody(self, key: str, scale: MusicalScale,
                           listener_prefs: ListenerPreference,
                           generations: int = 50) -> List[MusicalNote]:
        """Evolve optimal melody through swarm intelligence"""

        for generation in range(generations):
            # Generate melodies
            for agent in self.agents:
                agent.generate_melody(key, scale)
                agent.evaluate_melody(listener_prefs)

            # Find best performers
            self.agents.sort(key=lambda a: a.fitness, reverse=True)

            if self.agents[0].fitness > self.best_fitness:
                self.best_fitness = self.agents[0].fitness
                self.best_melody = self.agents[0].current_melody.copy()

            # Democratic voting on best melodies
            top_performers = self.agents[:20]

            # Breed new generation
            if generation < generations - 1:
                await self._breed_new_generation(top_performers)

        return self.best_melody

    async def _breed_new_generation(self, top_performers: List[MelodySwarmAgent]):
        """Create new generation through crossover and mutation"""
        new_agents = []

        # Keep elite
        new_agents.extend(top_performers[:10])

        # Crossover
        while len(new_agents) < len(self.agents):
            parent1 = np.random.choice(top_performers)
            parent2 = np.random.choice(top_performers)

            child = MelodySwarmAgent(len(new_agents))
            # Simple crossover: take first half from parent1, second from parent2
            if parent1.current_melody and parent2.current_melody:
                split = len(parent1.current_melody) // 2
                child.current_melody = (parent1.current_melody[:split] +
                                       parent2.current_melody[split:])

            new_agents.append(child)

        self.agents = new_agents


class HarmonySwarm:
    """Swarm generating harmonic progressions"""

    def __init__(self, size: int = 50):
        self.size = size
        self.chord_progressions: List[List[List[int]]] = []

    async def generate_harmony(self, melody: List[MusicalNote],
                               key: str, scale: MusicalScale) -> List[List[int]]:
        """Generate harmonic accompaniment for melody"""

        # Common chord progressions in the key
        progressions = [
            [0, 4, 5, 0],  # I-IV-V-I
            [0, 5, 3, 4],  # I-V-vi-IV
            [0, 3, 4, 5],  # I-vi-IV-V
            [0, 4, 0, 5],  # I-IV-I-V
        ]

        root = self._key_to_midi(key)

        # Build chords from scale
        harmony = []
        measures = len(melody) // 4

        for i in range(measures):
            # Select chord from progression
            chord_root_interval = progressions[i % len(progressions)][i % 4]
            chord_root = root + scale.value[chord_root_interval % len(scale.value)]

            # Build triad
            chord = [
                chord_root,
                chord_root + scale.value[2],
                chord_root + scale.value[4]
            ]
            harmony.append(chord)

        return harmony

    def _key_to_midi(self, key: str) -> int:
        """Convert key string to MIDI note number"""
        note_map = {'C': 60, 'D': 62, 'E': 64, 'F': 65,
                   'G': 67, 'A': 69, 'B': 71}
        return note_map.get(key, 60)


class RhythmSwarm:
    """Swarm optimizing rhythmic patterns"""

    def __init__(self, size: int = 30):
        self.size = size
        self.patterns: List[List[float]] = []

    async def generate_rhythm(self, tempo: int,
                             listener_prefs: ListenerPreference,
                             measures: int = 4) -> List[float]:
        """Generate rhythmic pattern"""

        # Energy-based rhythm complexity
        if listener_prefs.energy_level > 0.7:
            # High energy: more subdivisions
            pattern = [0.25] * 16  # 16th notes
        elif listener_prefs.energy_level > 0.4:
            # Medium energy: mix of quarters and eighths
            pattern = [0.5, 0.5, 0.25, 0.25, 0.5, 0.5]
        else:
            # Low energy: simple quarters
            pattern = [1.0] * 4

        return pattern * measures


class DynamicsSwarm:
    """Swarm controlling dynamic expression"""

    def __init__(self, size: int = 20):
        self.size = size

    async def generate_dynamics(self, melody: List[MusicalNote],
                               listener_prefs: ListenerPreference) -> List[int]:
        """Generate dynamic contour (velocity changes)"""

        dynamics = []
        length = len(melody)

        for i, note in enumerate(melody):
            # Create dynamic arc
            position = i / length

            if listener_prefs.mood == "dramatic":
                # Strong crescendo and diminuendo
                velocity = int(40 + 60 * np.sin(position * np.pi))
            elif listener_prefs.mood == "mellow":
                # Gentle variations
                velocity = int(60 + 20 * np.sin(position * np.pi * 2))
            else:
                # Moderate dynamics
                velocity = int(70 + 30 * np.sin(position * np.pi))

            dynamics.append(velocity)

        return dynamics


class SwarmComposer:
    """
    Main SwarmComposer system coordinating all musical swarms
    """

    def __init__(self):
        self.melody_swarm = MelodySwarm(size=100)
        self.harmony_swarm = HarmonySwarm(size=50)
        self.rhythm_swarm = RhythmSwarm(size=30)
        self.dynamics_swarm = DynamicsSwarm(size=20)

        self.composition_history: List[Dict[str, Any]] = []

    async def compose(self,
                     key: str = "C",
                     scale: MusicalScale = MusicalScale.MAJOR,
                     tempo: int = 120,
                     listener_prefs: Optional[ListenerPreference] = None,
                     measures: int = 4) -> Dict[str, Any]:
        """
        Compose complete musical piece using all swarms
        """

        if listener_prefs is None:
            listener_prefs = ListenerPreference(
                energy_level=0.5,
                complexity_preference=0.5,
                tempo_preference=120,
                mood="upbeat",
                favorite_instruments=["piano"]
            )

        print(f"🎵 Composing in {key} {scale.name}...")
        print(f"🎯 Listener preferences: {listener_prefs.mood}, "
              f"energy={listener_prefs.energy_level:.2f}")

        # Phase 1: Generate melody
        print("🎼 Melody swarm evolving...")
        melody = await self.melody_swarm.evolve_melody(
            key, scale, listener_prefs, generations=30
        )

        # Phase 2: Generate harmony
        print("🎹 Harmony swarm generating chords...")
        harmony = await self.harmony_swarm.generate_harmony(melody, key, scale)

        # Phase 3: Generate rhythm
        print("🥁 Rhythm swarm creating patterns...")
        rhythm = await self.rhythm_swarm.generate_rhythm(
            tempo, listener_prefs, measures
        )

        # Phase 4: Generate dynamics
        print("📊 Dynamics swarm shaping expression...")
        dynamics = await self.dynamics_swarm.generate_dynamics(
            melody, listener_prefs
        )

        # Apply dynamics to melody
        for i, note in enumerate(melody):
            if i < len(dynamics):
                note.velocity = dynamics[i]

        composition = {
            'key': key,
            'scale': scale.name,
            'tempo': tempo,
            'melody': melody,
            'harmony': harmony,
            'rhythm': rhythm,
            'dynamics': dynamics,
            'listener_prefs': listener_prefs,
            'fitness_score': self.melody_swarm.best_fitness
        }

        self.composition_history.append(composition)

        print(f"✨ Composition complete! Fitness: {self.melody_swarm.best_fitness:.3f}")

        return composition

    async def adapt_to_listener(self,
                               current_composition: Dict[str, Any],
                               listener_feedback: Dict[str, float]) -> Dict[str, Any]:
        """
        Real-time adaptation based on listener feedback
        """

        # Update preferences based on feedback
        prefs = current_composition['listener_prefs']

        if 'energy' in listener_feedback:
            prefs.energy_level = max(0, min(1,
                prefs.energy_level + listener_feedback['energy'] * 0.1))

        if 'complexity' in listener_feedback:
            prefs.complexity_preference = max(0, min(1,
                prefs.complexity_preference + listener_feedback['complexity'] * 0.1))

        # Re-compose with updated preferences
        return await self.compose(
            key=current_composition['key'],
            scale=MusicalScale[current_composition['scale']],
            tempo=current_composition['tempo'],
            listener_prefs=prefs
        )

    def export_to_midi(self, composition: Dict[str, Any],
                      filename: str = "swarm_composition.mid"):
        """Export composition to MIDI file"""

        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Set tempo
        tempo = composition['tempo']
        track.append(mido.MetaMessage('set_tempo',
                                      tempo=mido.bpm2tempo(tempo)))

        # Add melody notes
        melody = composition['melody']
        for note in melody:
            # Note on
            track.append(mido.Message('note_on',
                                     note=note.pitch,
                                     velocity=note.velocity,
                                     time=int(note.time * 480)))

            # Note off
            track.append(mido.Message('note_off',
                                     note=note.pitch,
                                     velocity=0,
                                     time=int(note.duration * 480)))

        mid.save(filename)
        print(f"💾 MIDI exported to {filename}")

    def export_to_sheet_music(self, composition: Dict[str, Any],
                             filename: str = "swarm_composition.xml"):
        """Export composition to MusicXML for sheet music"""

        # MusicXML generation (simplified)
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>SwarmComposer</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>480</divisions>
        <key>
          <fifths>0</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
      </attributes>
"""

        # Add notes (simplified representation)
        for note in composition['melody'][:16]:
            xml += f"""      <note>
        <pitch>
          <step>{self._midi_to_note_name(note.pitch)[0]}</step>
          <octave>{self._midi_to_note_name(note.pitch)[1]}</octave>
        </pitch>
        <duration>{int(note.duration * 480)}</duration>
        <velocity>{note.velocity}</velocity>
      </note>
"""

        xml += """    </measure>
  </part>
</score-partwise>"""

        with open(filename, 'w') as f:
            f.write(xml)

        print(f"🎼 Sheet music exported to {filename}")

    def _midi_to_note_name(self, midi_note: int) -> tuple:
        """Convert MIDI note number to (note_name, octave)"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F',
                'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note = notes[midi_note % 12]
        return (note, octave)


# Demo and example usage
async def demo_interactive_composition():
    """
    Demonstrate interactive composition with real-time adaptation
    """

    composer = SwarmComposer()

    # Initial composition
    print("\n" + "="*60)
    print("SWARMCOMPOSER DEMO - Interactive Music Generation")
    print("="*60 + "\n")

    # User preference
    listener = ListenerPreference(
        energy_level=0.7,
        complexity_preference=0.6,
        tempo_preference=128,
        mood="upbeat",
        favorite_instruments=["piano", "strings"]
    )

    # Compose initial piece
    composition1 = await composer.compose(
        key="C",
        scale=MusicalScale.MAJOR,
        tempo=128,
        listener_prefs=listener,
        measures=4
    )

    # Export to MIDI
    composer.export_to_midi(composition1, "demo_composition_1.mid")

    # Simulate listener feedback
    print("\n👂 Listener feedback: wants more energy, higher complexity")
    feedback = {
        'energy': 0.2,  # Increase energy
        'complexity': 0.3  # Increase complexity
    }

    # Adapt composition
    composition2 = await composer.adapt_to_listener(composition1, feedback)
    composer.export_to_midi(composition2, "demo_composition_2.mid")

    print("\n" + "="*60)
    print(f"Compositions generated: {len(composer.composition_history)}")
    print(f"Fitness improvement: {composition1['fitness_score']:.3f} → "
          f"{composition2['fitness_score']:.3f}")
    print("="*60 + "\n")


async def demo_multi_mood_generation():
    """
    Generate compositions in different moods
    """

    composer = SwarmComposer()

    print("\n" + "="*60)
    print("SWARMCOMPOSER - Multi-Mood Generation Demo")
    print("="*60 + "\n")

    moods = ["upbeat", "mellow", "dramatic"]

    for mood in moods:
        listener = ListenerPreference(
            energy_level=0.8 if mood == "upbeat" else 0.3 if mood == "mellow" else 0.9,
            complexity_preference=0.6,
            tempo_preference=140 if mood == "upbeat" else 80 if mood == "mellow" else 120,
            mood=mood,
            favorite_instruments=["piano"]
        )

        composition = await composer.compose(
            key="C" if mood != "dramatic" else "Am",
            scale=MusicalScale.MAJOR if mood != "dramatic" else MusicalScale.MINOR,
            tempo=listener.tempo_preference,
            listener_prefs=listener
        )

        filename = f"demo_{mood}_composition.mid"
        composer.export_to_midi(composition, filename)


if __name__ == "__main__":
    # Run demos
    asyncio.run(demo_interactive_composition())
    asyncio.run(demo_multi_mood_generation())

    print("\n✨ SwarmComposer demo complete!")
    print("🎵 Check the generated MIDI files for results")
