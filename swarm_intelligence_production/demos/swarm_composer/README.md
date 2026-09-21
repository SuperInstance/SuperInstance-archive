# SwarmComposer - Music Generation System

Revolutionary music composition through multi-swarm intelligence.

## Overview

SwarmComposer uses multiple specialized swarms to create original music:
- **Melody Swarm** (100 agents): Explores melodic possibilities
- **Harmony Swarm** (50 agents): Generates chord progressions
- **Rhythm Swarm** (30 agents): Creates rhythmic patterns
- **Dynamics Swarm** (20 agents): Shapes expression and dynamics

Total: 200 coordinated agents working democratically

## Features

### ✨ Core Capabilities

- **Multi-Style Composition**: Major, minor, pentatonic, blues, chromatic scales
- **Real-Time Adaptation**: Adjusts to listener preferences dynamically
- **Democratic Optimization**: Swarms vote on best musical choices
- **Export Formats**: MIDI, MusicXML, JSON
- **Collaborative Creation**: Human-AI co-composition

### 🎵 Musical Elements

- Melody generation with contour control
- Harmonic progressions (I-IV-V, I-V-vi-IV, etc.)
- Rhythmic patterns based on energy level
- Dynamic expression curves
- Tempo and key modulation

### 🎯 Personalization

Adapts to:
- Energy level (0-1): calm to energetic
- Complexity preference (0-1): simple to complex
- Tempo preference (BPM)
- Mood: "upbeat", "mellow", "dramatic"
- Instrument preferences

## Quick Start

```python
import asyncio
from swarm_composer import SwarmComposer, ListenerPreference, MusicalScale

async def main():
    composer = SwarmComposer()

    # Define preferences
    listener = ListenerPreference(
        energy_level=0.7,
        complexity_preference=0.6,
        tempo_preference=128,
        mood="upbeat",
        favorite_instruments=["piano", "strings"]
    )

    # Compose
    composition = await composer.compose(
        key="C",
        scale=MusicalScale.MAJOR,
        tempo=128,
        listener_prefs=listener,
        measures=4
    )

    # Export
    composer.export_to_midi(composition, "output.mid")
    print(f"Composition fitness: {composition['fitness_score']:.3f}")

asyncio.run(main())
```

## Installation

```bash
pip install mido numpy asyncio
```

Optional for audio playback:
```bash
pip install python-rtmidi pygame
```

## Usage Examples

See `examples/` directory for:
- `basic_composition.py` - Simple composition
- `adaptive_music.py` - Real-time adaptation
- `multi_mood.py` - Generate multiple moods
- `interactive_session.py` - Interactive composition

## Templates

See `templates/` directory for:
- Preset listener preferences
- Musical scales and modes
- Common chord progressions
- Rhythmic patterns

## Output Examples

Generated MIDI files can be imported into:
- **DAWs**: Ableton Live, Logic Pro, FL Studio
- **Notation Software**: MuseScore, Finale, Sibelius
- **Online Tools**: Flat.io, Noteflight

## API Reference

### SwarmComposer Class

#### `compose(key, scale, tempo, listener_prefs, measures)`
Generate complete musical composition.

**Parameters**:
- `key`: str - Root note ("C", "D", "E", etc.)
- `scale`: MusicalScale - Scale type
- `tempo`: int - Beats per minute
- `listener_prefs`: ListenerPreference - User preferences
- `measures`: int - Number of measures to generate

**Returns**: Dict with melody, harmony, rhythm, dynamics

#### `adapt_to_listener(composition, feedback)`
Adapt composition based on feedback.

**Parameters**:
- `composition`: Dict - Current composition
- `feedback`: Dict - Adjustment values

**Returns**: Updated composition

#### `export_to_midi(composition, filename)`
Export to MIDI file.

#### `export_to_sheet_music(composition, filename)`
Export to MusicXML for notation.

### ListenerPreference Class

```python
ListenerPreference(
    energy_level=0.5,          # 0-1
    complexity_preference=0.5,  # 0-1
    tempo_preference=120,       # BPM
    mood="upbeat",             # str
    favorite_instruments=[]     # List[str]
)
```

## Performance

- **Composition Time**: 5-10 seconds
- **Melody Optimization**: 30 generations
- **Quality Score**: 0.85-0.95 fitness
- **Agent Count**: 200 total

## Advanced Features

### Custom Scale Creation

```python
from enum import Enum

class CustomScale(Enum):
    MY_SCALE = [0, 2, 3, 7, 9]  # Custom intervals

composition = await composer.compose(
    scale=CustomScale.MY_SCALE
)
```

### Multi-Track Composition

```python
# Generate bass line
bass_prefs = ListenerPreference(energy_level=0.3)
bass = await composer.compose(key="C", listener_prefs=bass_prefs)

# Generate melody
melody_prefs = ListenerPreference(energy_level=0.8)
melody = await composer.compose(key="C", listener_prefs=melody_prefs)

# Combine tracks
combined = combine_tracks([bass, melody])
```

### Real-Time Performance

```python
# Stream composition in real-time
async for measure in composer.stream_composition(listener_prefs):
    play_measure(measure)
    feedback = get_listener_response()
    listener_prefs = update_preferences(listener_prefs, feedback)
```

## Tutorials

See `tutorials/` directory for video guides:
- Getting Started (10 min)
- Advanced Composition Techniques (20 min)
- Real-Time Adaptation (15 min)
- Integration with DAWs (12 min)

## Troubleshooting

**No sound from MIDI**:
- Ensure MIDI output device is configured
- Check `mido.get_output_names()`

**Low quality compositions**:
- Increase generations: `generations=50`
- Increase swarm size: `MelodySwarm(size=200)`

**Slow performance**:
- Reduce swarm size
- Decrease generation count
- Use simpler scales

## Research Applications

SwarmComposer demonstrates:
- Emergent musical creativity from simple rules
- Democratic aesthetic decision-making
- Real-time adaptive systems
- Human-AI collaborative creation

## License

MIT License
