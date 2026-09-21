"""
Basic Composition Example
Demonstrates simple music generation with SwarmComposer
"""

import asyncio
import sys
sys.path.append('../src')

from swarm_composer import SwarmComposer, ListenerPreference, MusicalScale


async def basic_example():
    """Generate a basic composition"""

    print("SwarmComposer - Basic Composition Example")
    print("=" * 50)

    # Create composer
    composer = SwarmComposer()

    # Simple listener preferences
    listener = ListenerPreference(
        energy_level=0.5,
        complexity_preference=0.5,
        tempo_preference=120,
        mood="upbeat",
        favorite_instruments=["piano"]
    )

    # Compose in C Major
    print("\n🎵 Composing in C Major...")
    composition = await composer.compose(
        key="C",
        scale=MusicalScale.MAJOR,
        tempo=120,
        listener_prefs=listener,
        measures=4
    )

    # Print results
    print(f"\n✅ Composition Complete!")
    print(f"   Key: {composition['key']} {composition['scale']}")
    print(f"   Tempo: {composition['tempo']} BPM")
    print(f"   Melody notes: {len(composition['melody'])}")
    print(f"   Harmony chords: {len(composition['harmony'])}")
    print(f"   Fitness score: {composition['fitness_score']:.3f}")

    # Export to MIDI
    composer.export_to_midi(composition, "basic_composition.mid")
    print(f"\n💾 Saved to: basic_composition.mid")


if __name__ == "__main__":
    asyncio.run(basic_example())
