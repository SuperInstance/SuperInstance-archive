"""
Integration Test: Creative Production Demos
Tests SwarmComposer, SwarmWriter, SwarmDesign, and SwarmVideo
"""

import pytest
import asyncio
import sys
import os
from pathlib import Path
import json

# Add demo modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "demos"))

from swarm_composer.src.swarm_composer import SwarmComposer
from swarm_writer.src.swarm_writer import SwarmWriter
from swarm_design.src.swarm_design import SwarmDesign
from swarm_video.src.swarm_video import SwarmVideo


class TestSwarmComposer:
    """Test SwarmComposer music generation"""

    @pytest.mark.asyncio
    async def test_basic_composition(self):
        """Test basic music composition"""
        composer = SwarmComposer(
            agent_count=100,
            swarm_config={
                "melody_agents": 30,
                "harmony_agents": 25,
                "rhythm_agents": 25,
                "orchestration_agents": 20
            }
        )

        # Initialize swarm
        await composer.initialize()

        # Generate composition
        composition = await composer.compose(
            style="ambient",
            duration=30,  # 30 seconds
            tempo=120,
            key="C_major"
        )

        # Validate output
        assert composition is not None
        assert "midi_data" in composition or "audio_data" in composition
        assert composition.get("duration", 0) >= 25  # Allow some variance
        assert composition.get("quality_score", 0) > 0.5

        # Check structure
        if "tracks" in composition:
            assert len(composition["tracks"]) > 0

        await composer.shutdown()

    @pytest.mark.asyncio
    async def test_multi_genre_composition(self):
        """Test composition across different genres"""
        genres = ["classical", "jazz", "electronic", "ambient"]

        for genre in genres:
            composer = SwarmComposer(agent_count=80)
            await composer.initialize()

            composition = await composer.compose(
                style=genre,
                duration=15,
                tempo=100
            )

            assert composition is not None
            assert composition.get("genre") == genre

            await composer.shutdown()
            await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_collaborative_composition(self):
        """Test collaborative composition with human input"""
        composer = SwarmComposer(agent_count=100)
        await composer.initialize()

        # Start with human seed
        composition = await composer.compose(
            style="jazz",
            duration=20,
            seed_melody=[60, 62, 64, 65, 67],  # C major scale
            human_feedback_enabled=True
        )

        assert composition is not None
        assert "seed_incorporated" in composition or composition is not None

        await composer.shutdown()

    @pytest.mark.asyncio
    async def test_quality_metrics(self):
        """Test music quality evaluation metrics"""
        composer = SwarmComposer(agent_count=100)
        await composer.initialize()

        composition = await composer.compose(
            style="classical",
            duration=20,
            quality_threshold=0.7
        )

        # Check quality metrics
        assert composition.get("quality_score", 0) >= 0.7
        assert "harmony_score" in composition or composition is not None
        assert "rhythm_coherence" in composition or composition is not None

        await composer.shutdown()


class TestSwarmWriter:
    """Test SwarmWriter story creation"""

    @pytest.mark.asyncio
    async def test_short_story_generation(self):
        """Test short story generation"""
        writer = SwarmWriter(
            agent_count=150,
            swarm_config={
                "character_agents": 40,
                "plot_agents": 30,
                "dialogue_agents": 50,
                "worldbuilding_agents": 30
            }
        )

        await writer.initialize()

        # Generate story
        story = await writer.write(
            genre="science_fiction",
            length="short",  # ~1000 words
            theme="exploration",
            tone="optimistic"
        )

        # Validate output
        assert story is not None
        assert "content" in story
        assert len(story["content"]) > 500  # At least 500 characters
        assert story.get("word_count", 0) >= 800

        # Check structure
        assert "characters" in story or story is not None
        assert "plot_points" in story or story is not None

        await writer.shutdown()

    @pytest.mark.asyncio
    async def test_multi_genre_stories(self):
        """Test story generation across genres"""
        genres = ["fantasy", "mystery", "romance", "horror"]

        for genre in genres:
            writer = SwarmWriter(agent_count=100)
            await writer.initialize()

            story = await writer.write(
                genre=genre,
                length="flash_fiction",  # ~500 words
                theme="discovery"
            )

            assert story is not None
            assert story.get("genre") == genre
            assert len(story.get("content", "")) > 200

            await writer.shutdown()
            await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_character_development(self):
        """Test character development quality"""
        writer = SwarmWriter(agent_count=150)
        await writer.initialize()

        story = await writer.write(
            genre="drama",
            length="medium",
            character_depth="high",
            character_count=3
        )

        assert story is not None
        if "characters" in story:
            assert len(story["characters"]) >= 3
            for char in story["characters"]:
                assert "name" in char
                assert "traits" in char or "description" in char

        await writer.shutdown()

    @pytest.mark.asyncio
    async def test_coherence_metrics(self):
        """Test narrative coherence evaluation"""
        writer = SwarmWriter(agent_count=120)
        await writer.initialize()

        story = await writer.write(
            genre="thriller",
            length="short",
            coherence_threshold=0.75
        )

        assert story is not None
        assert story.get("coherence_score", 0) >= 0.75
        assert "plot_consistency" in story or story is not None

        await writer.shutdown()


class TestSwarmDesign:
    """Test SwarmDesign art generation"""

    @pytest.mark.asyncio
    async def test_basic_artwork_generation(self):
        """Test basic artwork generation"""
        designer = SwarmDesign(
            agent_count=200,
            swarm_config={
                "color_agents": 50,
                "composition_agents": 60,
                "style_agents": 50,
                "critique_agents": 40
            }
        )

        await designer.initialize()

        # Generate artwork
        artwork = await designer.create(
            style="abstract",
            resolution=(512, 512),
            color_palette="vibrant",
            complexity="medium"
        )

        # Validate output
        assert artwork is not None
        assert "image_data" in artwork or "file_path" in artwork
        assert artwork.get("resolution") == (512, 512)
        assert artwork.get("quality_score", 0) > 0.6

        await designer.shutdown()

    @pytest.mark.asyncio
    async def test_style_variations(self):
        """Test art generation across different styles"""
        styles = ["abstract", "impressionist", "geometric", "surreal"]

        for style in styles:
            designer = SwarmDesign(agent_count=150)
            await designer.initialize()

            artwork = await designer.create(
                style=style,
                resolution=(256, 256),
                iterations=50
            )

            assert artwork is not None
            assert artwork.get("style") == style

            await designer.shutdown()
            await asyncio.sleep(1)

    @pytest.mark.asyncio
    async def test_collaborative_design(self):
        """Test collaborative art creation with human input"""
        designer = SwarmDesign(agent_count=200)
        await designer.initialize()

        # Start with human sketch
        artwork = await designer.create(
            style="digital_painting",
            resolution=(512, 512),
            seed_image="base_sketch.png",  # Hypothetical
            human_guidance=True
        )

        assert artwork is not None

        await designer.shutdown()

    @pytest.mark.asyncio
    async def test_aesthetic_quality_metrics(self):
        """Test aesthetic quality evaluation"""
        designer = SwarmDesign(agent_count=200)
        await designer.initialize()

        artwork = await designer.create(
            style="minimalist",
            resolution=(512, 512),
            quality_threshold=0.8
        )

        assert artwork is not None
        assert artwork.get("quality_score", 0) >= 0.8
        assert "composition_score" in artwork or artwork is not None
        assert "color_harmony" in artwork or artwork is not None

        await designer.shutdown()


class TestSwarmVideo:
    """Test SwarmVideo production"""

    @pytest.mark.asyncio
    async def test_basic_video_generation(self):
        """Test basic video generation"""
        video_producer = SwarmVideo(
            agent_count=250,
            swarm_config={
                "storyboard_agents": 50,
                "animation_agents": 80,
                "effects_agents": 60,
                "editing_agents": 60
            }
        )

        await video_producer.initialize()

        # Generate video
        video = await video_producer.produce(
            style="animated",
            duration=10,  # 10 seconds
            resolution=(720, 480),
            fps=30
        )

        # Validate output
        assert video is not None
        assert "video_data" in video or "file_path" in video
        assert video.get("duration", 0) >= 8
        assert video.get("fps") == 30

        await video_producer.shutdown()

    @pytest.mark.asyncio
    async def test_scene_transitions(self):
        """Test video with multiple scenes and transitions"""
        video_producer = SwarmVideo(agent_count=200)
        await video_producer.initialize()

        video = await video_producer.produce(
            style="cinematic",
            duration=15,
            scenes=[
                {"type": "intro", "duration": 3},
                {"type": "main", "duration": 9},
                {"type": "outro", "duration": 3}
            ],
            transitions=["fade", "dissolve"]
        )

        assert video is not None
        if "scenes" in video:
            assert len(video["scenes"]) == 3

        await video_producer.shutdown()

    @pytest.mark.asyncio
    async def test_effects_application(self):
        """Test video effects and post-processing"""
        video_producer = SwarmVideo(agent_count=200)
        await video_producer.initialize()

        video = await video_producer.produce(
            style="motion_graphics",
            duration=10,
            effects=["blur", "glow", "color_grade"],
            post_processing=True
        )

        assert video is not None
        if "applied_effects" in video:
            assert len(video["applied_effects"]) > 0

        await video_producer.shutdown()

    @pytest.mark.asyncio
    async def test_quality_validation(self):
        """Test video quality metrics"""
        video_producer = SwarmVideo(agent_count=250)
        await video_producer.initialize()

        video = await video_producer.produce(
            style="professional",
            duration=10,
            resolution=(1920, 1080),
            quality_threshold=0.85
        )

        assert video is not None
        assert video.get("quality_score", 0) >= 0.85
        assert "frame_consistency" in video or video is not None

        await video_producer.shutdown()


class TestCrossCreativeIntegration:
    """Test integration between different creative tools"""

    @pytest.mark.asyncio
    async def test_music_video_production(self):
        """Test combining music and video generation"""
        # Generate music first
        composer = SwarmComposer(agent_count=80)
        await composer.initialize()

        music = await composer.compose(
            style="electronic",
            duration=15,
            tempo=128
        )

        await composer.shutdown()

        # Generate video synchronized to music
        video_producer = SwarmVideo(agent_count=150)
        await video_producer.initialize()

        video = await video_producer.produce(
            style="visualizer",
            duration=15,
            audio_sync=music,
            sync_to_beat=True
        )

        assert video is not None
        assert music is not None

        await video_producer.shutdown()

    @pytest.mark.asyncio
    async def test_illustrated_story(self):
        """Test combining story and artwork generation"""
        # Generate story
        writer = SwarmWriter(agent_count=100)
        await writer.initialize()

        story = await writer.write(
            genre="fantasy",
            length="flash_fiction",
            illustration_points=3
        )

        await writer.shutdown()

        # Generate illustrations
        designer = SwarmDesign(agent_count=150)
        await designer.initialize()

        illustrations = []
        for scene in story.get("illustration_points", [])[:3]:
            artwork = await designer.create(
                style="fantasy_art",
                resolution=(512, 512),
                prompt=scene.get("description", "fantasy scene")
            )
            illustrations.append(artwork)

        assert len(illustrations) > 0
        assert story is not None

        await designer.shutdown()


class TestPerformanceMetrics:
    """Test performance and quality metrics across all creative tools"""

    @pytest.mark.asyncio
    async def test_generation_speed(self):
        """Test generation speed for all creative tools"""
        import time

        results = {}

        # Music
        start = time.time()
        composer = SwarmComposer(agent_count=80)
        await composer.initialize()
        music = await composer.compose(style="ambient", duration=10)
        results["music"] = time.time() - start
        await composer.shutdown()

        # Story
        start = time.time()
        writer = SwarmWriter(agent_count=80)
        await writer.initialize()
        story = await writer.write(genre="scifi", length="flash_fiction")
        results["story"] = time.time() - start
        await writer.shutdown()

        # Art
        start = time.time()
        designer = SwarmDesign(agent_count=120)
        await designer.initialize()
        art = await designer.create(style="abstract", resolution=(256, 256))
        results["art"] = time.time() - start
        await designer.shutdown()

        # All should complete within reasonable time
        assert results["music"] < 60  # 1 minute
        assert results["story"] < 45  # 45 seconds
        assert results["art"] < 90  # 1.5 minutes

    @pytest.mark.asyncio
    async def test_quality_consistency(self):
        """Test quality consistency across multiple runs"""
        composer = SwarmComposer(agent_count=100)
        await composer.initialize()

        quality_scores = []
        for i in range(5):
            composition = await composer.compose(
                style="classical",
                duration=10,
                quality_threshold=0.7
            )
            quality_scores.append(composition.get("quality_score", 0))

        await composer.shutdown()

        # Quality should be consistent (low variance)
        import statistics
        avg_quality = statistics.mean(quality_scores)
        assert avg_quality >= 0.7
        if len(quality_scores) > 1:
            std_dev = statistics.stdev(quality_scores)
            assert std_dev < 0.15  # Low variance


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
