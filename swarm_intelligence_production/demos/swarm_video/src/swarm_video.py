"""
SwarmVideo - Automated Video Production System
Revolutionary video creation through multi-swarm intelligence
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class ShotType(Enum):
    """Types of camera shots"""
    EXTREME_WIDE = "extreme_wide"
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    OVER_SHOULDER = "over_shoulder"
    POV = "point_of_view"


class CameraMovement(Enum):
    """Types of camera movements"""
    STATIC = "static"
    PAN = "pan"
    TILT = "tilt"
    DOLLY = "dolly"
    TRACK = "track"
    ZOOM = "zoom"
    CRANE = "crane"
    HANDHELD = "handheld"
    STEADICAM = "steadicam"


class TransitionType(Enum):
    """Types of transitions between scenes"""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    CROSSFADE = "crossfade"


@dataclass
class Shot:
    """Individual camera shot"""
    shot_id: int
    shot_type: ShotType
    duration: float  # seconds
    camera_movement: CameraMovement
    subject: str
    location: str
    framing: str
    lighting: str
    composition_rules: List[str]  # e.g., ["rule_of_thirds", "leading_lines"]


@dataclass
class Scene:
    """Collection of shots forming a scene"""
    scene_id: int
    shots: List[Shot]
    location: str
    time_of_day: str
    mood: str
    narrative_purpose: str
    duration: float


@dataclass
class ColorGrade:
    """Color grading parameters"""
    temperature: float  # -100 to 100
    tint: float  # -100 to 100
    exposure: float  # -5 to 5
    contrast: float  # -100 to 100
    highlights: float  # -100 to 100
    shadows: float  # -100 to 100
    saturation: float  # -100 to 100
    vibrance: float  # -100 to 100
    lut_name: Optional[str] = None  # Color lookup table


@dataclass
class Transition:
    """Transition between scenes"""
    transition_type: TransitionType
    duration: float  # seconds
    from_scene: int
    to_scene: int


@dataclass
class Subtitle:
    """Subtitle/caption entry"""
    text: str
    start_time: float  # seconds
    end_time: float  # seconds
    position: str = "bottom"  # "top", "middle", "bottom"
    style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VideoProject:
    """Complete video project"""
    scenes: List[Scene]
    transitions: List[Transition]
    color_grade: ColorGrade
    subtitles: List[Subtitle]
    music_track: Optional[str] = None
    aspect_ratio: str = "16:9"
    frame_rate: int = 24
    resolution: str = "1920x1080"
    total_duration: float = 0.0


class SceneCompositionSwarmAgent:
    """Agent creating scene compositions"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self.fitness = 0.0

    def compose_scene(self,
                     narrative_purpose: str,
                     mood: str,
                     location: str,
                     num_shots: int = 5) -> Scene:
        """Compose scene with optimal shot sequence"""

        shots = []

        # Shot progression strategy
        if narrative_purpose == "introduction":
            # Wide to close pattern
            shot_types = [ShotType.WIDE, ShotType.MEDIUM,
                         ShotType.CLOSE_UP, ShotType.MEDIUM, ShotType.WIDE]
        elif narrative_purpose == "action":
            # Dynamic cutting
            shot_types = [ShotType.MEDIUM, ShotType.CLOSE_UP,
                         ShotType.WIDE, ShotType.CLOSE_UP, ShotType.MEDIUM]
        elif narrative_purpose == "dialogue":
            # Over-shoulder and close-ups
            shot_types = [ShotType.MEDIUM, ShotType.OVER_SHOULDER,
                         ShotType.CLOSE_UP, ShotType.OVER_SHOULDER, ShotType.CLOSE_UP]
        elif narrative_purpose == "tension":
            # Tight shots with slow movement
            shot_types = [ShotType.CLOSE_UP, ShotType.EXTREME_CLOSE_UP,
                         ShotType.MEDIUM, ShotType.CLOSE_UP, ShotType.EXTREME_CLOSE_UP]
        else:
            # Balanced coverage
            shot_types = [ShotType.WIDE, ShotType.MEDIUM,
                         ShotType.CLOSE_UP, ShotType.MEDIUM, ShotType.WIDE]

        # Ensure we have enough shot types
        while len(shot_types) < num_shots:
            shot_types.extend(shot_types[:num_shots - len(shot_types)])

        for i in range(num_shots):
            # Camera movement based on mood
            if mood == "tense":
                movement = random.choice([CameraMovement.STATIC,
                                        CameraMovement.HANDHELD])
            elif mood == "dramatic":
                movement = random.choice([CameraMovement.DOLLY,
                                        CameraMovement.CRANE])
            elif mood == "intimate":
                movement = random.choice([CameraMovement.STATIC,
                                        CameraMovement.STEADICAM])
            else:
                movement = random.choice(list(CameraMovement))

            # Shot duration
            if narrative_purpose == "action":
                duration = random.uniform(1.5, 3.0)  # Quick cuts
            elif narrative_purpose == "contemplative":
                duration = random.uniform(5.0, 10.0)  # Long takes
            else:
                duration = random.uniform(3.0, 6.0)  # Standard

            # Composition rules
            composition_rules = ["rule_of_thirds"]
            if shot_types[i] in [ShotType.WIDE, ShotType.EXTREME_WIDE]:
                composition_rules.append("leading_lines")
            if mood == "dramatic":
                composition_rules.append("dramatic_angle")

            shot = Shot(
                shot_id=i,
                shot_type=shot_types[i],
                duration=duration,
                camera_movement=movement,
                subject="main_subject",
                location=location,
                framing="centered",
                lighting=self._lighting_for_mood(mood),
                composition_rules=composition_rules
            )

            shots.append(shot)

        total_duration = sum(shot.duration for shot in shots)

        scene = Scene(
            scene_id=0,
            shots=shots,
            location=location,
            time_of_day="day",
            mood=mood,
            narrative_purpose=narrative_purpose,
            duration=total_duration
        )

        return scene

    def _lighting_for_mood(self, mood: str) -> str:
        """Suggest lighting based on mood"""
        lighting_map = {
            "tense": "low_key",
            "dramatic": "high_contrast",
            "intimate": "soft_light",
            "happy": "bright",
            "mysterious": "low_key",
            "romantic": "warm_tones"
        }
        return lighting_map.get(mood, "standard")

    def evaluate_scene_flow(self, scene: Scene) -> float:
        """Evaluate visual flow of scene"""

        if not scene.shots:
            return 0.0

        flow_score = 1.0

        # Check shot variety
        shot_types = [shot.shot_type for shot in scene.shots]
        variety = len(set(shot_types)) / len(shot_types)
        flow_score *= variety

        # Check pacing (duration variance)
        durations = [shot.duration for shot in scene.shots]
        if len(durations) > 1:
            avg_duration = sum(durations) / len(durations)
            variance = sum((d - avg_duration)**2 for d in durations) / len(durations)
            # Moderate variance is good
            pacing_score = 1.0 - abs(variance - 2.0) / 10.0
            flow_score *= max(0, min(1, pacing_score))

        self.fitness = flow_score
        return flow_score


class SceneCompositionSwarm:
    """Swarm creating optimal scene compositions"""

    def __init__(self, size: int = 40):
        self.agents = [SceneCompositionSwarmAgent(i) for i in range(size)]
        self.best_scenes: List[Scene] = []

    async def create_scenes(self,
                           script: List[Dict[str, Any]],
                           generations: int = 20) -> List[Scene]:
        """Create optimal scene compositions"""

        print("🎬 Scene composition swarm creating shots...")

        scenes = []

        for scene_desc in script:
            # Multiple agents propose scenes
            proposals = []

            for agent in self.agents[:10]:
                scene = agent.compose_scene(
                    narrative_purpose=scene_desc.get('purpose', 'general'),
                    mood=scene_desc.get('mood', 'neutral'),
                    location=scene_desc.get('location', 'unknown'),
                    num_shots=scene_desc.get('num_shots', 5)
                )

                # Evaluate
                fitness = agent.evaluate_scene_flow(scene)
                proposals.append((scene, fitness))

            # Democratic selection
            proposals.sort(key=lambda x: x[1], reverse=True)
            best_scene = proposals[0][0]
            best_scene.scene_id = len(scenes)

            scenes.append(best_scene)

            print(f"  Scene {len(scenes)}: {best_scene.narrative_purpose} "
                  f"({len(best_scene.shots)} shots, {best_scene.duration:.1f}s)")

        self.best_scenes = scenes
        return scenes


class CameraMovementSwarmAgent:
    """Agent optimizing camera movements"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id

    def optimize_camera_path(self, shot: Shot,
                            subject_motion: str = "static") -> Dict[str, Any]:
        """Generate optimal camera movement path"""

        path = {
            'shot_id': shot.shot_id,
            'movement_type': shot.camera_movement.value,
            'keyframes': []
        }

        # Generate keyframes based on movement type
        if shot.camera_movement == CameraMovement.PAN:
            path['keyframes'] = [
                {'time': 0.0, 'pan': 0, 'tilt': 0},
                {'time': shot.duration * 0.5, 'pan': 45, 'tilt': 0},
                {'time': shot.duration, 'pan': 90, 'tilt': 0}
            ]
        elif shot.camera_movement == CameraMovement.DOLLY:
            path['keyframes'] = [
                {'time': 0.0, 'position_z': 0},
                {'time': shot.duration, 'position_z': -5}
            ]
        elif shot.camera_movement == CameraMovement.ZOOM:
            path['keyframes'] = [
                {'time': 0.0, 'focal_length': 50},
                {'time': shot.duration, 'focal_length': 85}
            ]
        elif shot.camera_movement == CameraMovement.CRANE:
            path['keyframes'] = [
                {'time': 0.0, 'height': 0, 'tilt': -15},
                {'time': shot.duration * 0.5, 'height': 10, 'tilt': 0},
                {'time': shot.duration, 'height': 15, 'tilt': 15}
            ]

        return path


class ColorGradingSwarm:
    """Swarm optimizing color grading"""

    def __init__(self, size: int = 30):
        self.size = size

    async def grade_scenes(self,
                          scenes: List[Scene],
                          overall_mood: str = "cinematic") -> Dict[int, ColorGrade]:
        """Generate color grades for scenes"""

        print("🎨 Color grading swarm optimizing look...")

        grades = {}

        # Mood-based grading presets
        mood_grades = {
            "cinematic": ColorGrade(
                temperature=5, tint=2, exposure=0.2,
                contrast=15, highlights=-10, shadows=-5,
                saturation=-10, vibrance=5, lut_name="cinematic_teal_orange"
            ),
            "bright": ColorGrade(
                temperature=10, tint=0, exposure=0.5,
                contrast=10, highlights=5, shadows=5,
                saturation=10, vibrance=15, lut_name="bright_clean"
            ),
            "dark": ColorGrade(
                temperature=-10, tint=-5, exposure=-0.3,
                contrast=25, highlights=-20, shadows=-15,
                saturation=-15, vibrance=-5, lut_name="dark_moody"
            ),
            "vintage": ColorGrade(
                temperature=-5, tint=5, exposure=-0.1,
                contrast=-10, highlights=-5, shadows=10,
                saturation=-20, vibrance=-10, lut_name="vintage_film"
            ),
            "warm": ColorGrade(
                temperature=20, tint=5, exposure=0.3,
                contrast=5, highlights=0, shadows=5,
                saturation=5, vibrance=10, lut_name="warm_glow"
            ),
            "cool": ColorGrade(
                temperature=-15, tint=-10, exposure=0,
                contrast=10, highlights=-5, shadows=-5,
                saturation=0, vibrance=5, lut_name="cool_blue"
            )
        }

        base_grade = mood_grades.get(overall_mood,
                                     mood_grades["cinematic"])

        for scene in scenes:
            # Adjust grade based on scene mood and time of day
            scene_grade = ColorGrade(
                temperature=base_grade.temperature,
                tint=base_grade.tint,
                exposure=base_grade.exposure,
                contrast=base_grade.contrast,
                highlights=base_grade.highlights,
                shadows=base_grade.shadows,
                saturation=base_grade.saturation,
                vibrance=base_grade.vibrance,
                lut_name=base_grade.lut_name
            )

            # Time of day adjustments
            if scene.time_of_day == "dawn":
                scene_grade.temperature += 15
                scene_grade.exposure += 0.2
            elif scene.time_of_day == "night":
                scene_grade.temperature -= 10
                scene_grade.exposure -= 0.5
                scene_grade.shadows -= 10

            # Mood adjustments
            if scene.mood == "tense":
                scene_grade.contrast += 10
                scene_grade.saturation -= 5
            elif scene.mood == "romantic":
                scene_grade.temperature += 10
                scene_grade.vibrance += 10

            grades[scene.scene_id] = scene_grade

        print(f"  ✓ Graded {len(grades)} scenes with {overall_mood} look")

        return grades


class TransitionSwarmAgent:
    """Agent determining optimal transitions"""

    def __init__(self, agent_id: int):
        self.agent_id = agent_id

    def suggest_transition(self,
                          from_scene: Scene,
                          to_scene: Scene) -> Transition:
        """Suggest transition between scenes"""

        # Determine transition type based on scene relationships
        mood_change = from_scene.mood != to_scene.mood
        location_change = from_scene.location != to_scene.location
        time_change = from_scene.time_of_day != to_scene.time_of_day

        if location_change or time_change:
            # Significant change: use dissolve or fade
            transition_type = random.choice([TransitionType.DISSOLVE,
                                            TransitionType.FADE])
            duration = 1.0
        elif mood_change:
            # Mood shift: use crossfade
            transition_type = TransitionType.CROSSFADE
            duration = 0.5
        else:
            # Continuity: use cut
            transition_type = TransitionType.CUT
            duration = 0.0

        return Transition(
            transition_type=transition_type,
            duration=duration,
            from_scene=from_scene.scene_id,
            to_scene=to_scene.scene_id
        )


class PacingSwarm:
    """Swarm optimizing video pacing"""

    def __init__(self, size: int = 20):
        self.size = size

    async def optimize_pacing(self,
                             scenes: List[Scene],
                             target_duration: Optional[float] = None) -> List[Scene]:
        """Optimize scene durations for ideal pacing"""

        print("⏱️ Pacing swarm optimizing timing...")

        if not scenes:
            return scenes

        current_duration = sum(scene.duration for scene in scenes)

        if target_duration and current_duration != target_duration:
            # Scale durations
            scale_factor = target_duration / current_duration

            for scene in scenes:
                scene.duration *= scale_factor
                for shot in scene.shots:
                    shot.duration *= scale_factor

        # Adjust pacing based on narrative arc
        for i, scene in enumerate(scenes):
            position = i / len(scenes)

            # Accelerate in middle (rising action)
            if 0.3 < position < 0.7:
                # Shorter shots for faster pacing
                for shot in scene.shots:
                    shot.duration *= 0.9

            # Slow down at climax
            elif 0.7 <= position < 0.8:
                for shot in scene.shots:
                    shot.duration *= 1.2

            # Recalculate scene duration
            scene.duration = sum(shot.duration for shot in scene.shots)

        total = sum(scene.duration for scene in scenes)
        print(f"  ✓ Optimized pacing: {total:.1f}s total")

        return scenes


class SubtitleGenerationSwarm:
    """Swarm generating subtitles"""

    def __init__(self, size: int = 15):
        self.size = size

    async def generate_subtitles(self,
                                scenes: List[Scene],
                                dialogue: List[Dict[str, Any]]) -> List[Subtitle]:
        """Generate subtitles with optimal timing"""

        print("💬 Subtitle swarm generating captions...")

        subtitles = []
        current_time = 0.0

        for i, line in enumerate(dialogue):
            # Calculate timing
            duration = line.get('duration', 3.0)
            text = line.get('text', '')

            # Style based on speaker
            style = {
                'font_size': 24,
                'font_family': 'Arial',
                'color': '#FFFFFF',
                'background': 'rgba(0, 0, 0, 0.7)',
                'position': 'bottom'
            }

            if line.get('speaker') == 'narrator':
                style['position'] = 'top'
                style['color'] = '#FFFF00'

            subtitle = Subtitle(
                text=text,
                start_time=current_time,
                end_time=current_time + duration,
                position=style['position'],
                style=style
            )

            subtitles.append(subtitle)
            current_time += duration

        print(f"  ✓ Generated {len(subtitles)} subtitle entries")

        return subtitles


class SwarmVideo:
    """
    Main SwarmVideo system coordinating all video production swarms
    """

    def __init__(self):
        self.scene_swarm = SceneCompositionSwarm(size=40)
        self.color_swarm = ColorGradingSwarm(size=30)
        self.pacing_swarm = PacingSwarm(size=20)
        self.subtitle_swarm = SubtitleGenerationSwarm(size=15)

        self.projects: List[VideoProject] = []

    async def produce_video(self,
                           script: List[Dict[str, Any]],
                           dialogue: List[Dict[str, Any]],
                           style: str = "cinematic",
                           target_duration: Optional[float] = None) -> VideoProject:
        """
        Produce complete video using all swarms
        """

        print("\n" + "="*60)
        print("SWARMVIDEO - Automated Video Production")
        print("="*60 + "\n")

        # Phase 1: Create scene compositions
        scenes = await self.scene_swarm.create_scenes(script)

        # Phase 2: Optimize pacing
        scenes = await self.pacing_swarm.optimize_pacing(scenes, target_duration)

        # Phase 3: Color grading
        color_grades = await self.color_swarm.grade_scenes(scenes, style)

        # Phase 4: Determine transitions
        print("🔄 Generating transitions...")
        transitions = []
        transition_agent = TransitionSwarmAgent(0)

        for i in range(len(scenes) - 1):
            transition = transition_agent.suggest_transition(
                scenes[i],
                scenes[i + 1]
            )
            transitions.append(transition)

        print(f"  ✓ Created {len(transitions)} transitions")

        # Phase 5: Generate subtitles
        subtitles = await self.subtitle_swarm.generate_subtitles(scenes, dialogue)

        # Create project
        total_duration = sum(scene.duration for scene in scenes)

        project = VideoProject(
            scenes=scenes,
            transitions=transitions,
            color_grade=color_grades[0] if color_grades else ColorGrade(
                temperature=0, tint=0, exposure=0, contrast=0,
                highlights=0, shadows=0, saturation=0, vibrance=0
            ),
            subtitles=subtitles,
            total_duration=total_duration
        )

        self.projects.append(project)

        print("\n" + "="*60)
        print("✨ Video production complete!")
        print(f"Scenes: {len(scenes)}")
        print(f"Total shots: {sum(len(scene.shots) for scene in scenes)}")
        print(f"Duration: {total_duration:.1f}s")
        print(f"Subtitles: {len(subtitles)}")
        print("="*60 + "\n")

        return project

    def export_edl(self, project: VideoProject, filename: str = "project.edl"):
        """Export Edit Decision List"""

        edl = "TITLE: SwarmVideo Project\n\n"

        event_num = 1
        for scene in project.scenes:
            for shot in scene.shots:
                edl += f"{event_num:03d}  001  V  C  "
                edl += f"00:00:00:00  00:00:{int(shot.duration):02d}:00  "
                edl += f"00:00:00:00  00:00:{int(shot.duration):02d}:00\n"
                edl += f"* SHOT: {shot.shot_type.value}\n"
                edl += f"* MOVEMENT: {shot.camera_movement.value}\n"
                edl += f"* LOCATION: {shot.location}\n\n"
                event_num += 1

        with open(filename, 'w') as f:
            f.write(edl)

        print(f"📋 EDL exported to {filename}")

    def export_json(self, project: VideoProject, filename: str = "project.json"):
        """Export project to JSON"""

        project_data = {
            'metadata': {
                'aspect_ratio': project.aspect_ratio,
                'frame_rate': project.frame_rate,
                'resolution': project.resolution,
                'total_duration': project.total_duration
            },
            'scenes': [
                {
                    'scene_id': scene.scene_id,
                    'location': scene.location,
                    'mood': scene.mood,
                    'duration': scene.duration,
                    'shots': [
                        {
                            'shot_id': shot.shot_id,
                            'type': shot.shot_type.value,
                            'duration': shot.duration,
                            'movement': shot.camera_movement.value,
                            'composition': shot.composition_rules
                        }
                        for shot in scene.shots
                    ]
                }
                for scene in project.scenes
            ],
            'transitions': [
                {
                    'type': t.transition_type.value,
                    'duration': t.duration,
                    'from_scene': t.from_scene,
                    'to_scene': t.to_scene
                }
                for t in project.transitions
            ],
            'subtitles': [
                {
                    'text': sub.text,
                    'start': sub.start_time,
                    'end': sub.end_time,
                    'position': sub.position
                }
                for sub in project.subtitles
            ]
        }

        with open(filename, 'w') as f:
            json.dump(project_data, f, indent=2)

        print(f"💾 Project exported to {filename}")

    def export_srt(self, project: VideoProject, filename: str = "subtitles.srt"):
        """Export subtitles to SRT format"""

        srt = ""
        for i, subtitle in enumerate(project.subtitles, 1):
            start_time = self._format_srt_time(subtitle.start_time)
            end_time = self._format_srt_time(subtitle.end_time)

            srt += f"{i}\n"
            srt += f"{start_time} --> {end_time}\n"
            srt += f"{subtitle.text}\n\n"

        with open(filename, 'w') as f:
            f.write(srt)

        print(f"📝 Subtitles exported to {filename}")

    def _format_srt_time(self, seconds: float) -> str:
        """Format time for SRT"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


# Demo usage
async def demo_short_film():
    """Produce a short film"""

    producer = SwarmVideo()

    # Script
    script = [
        {
            'purpose': 'introduction',
            'mood': 'mysterious',
            'location': 'abandoned_warehouse',
            'num_shots': 5
        },
        {
            'purpose': 'dialogue',
            'mood': 'tense',
            'location': 'abandoned_warehouse',
            'num_shots': 6
        },
        {
            'purpose': 'action',
            'mood': 'intense',
            'location': 'warehouse_exterior',
            'num_shots': 8
        },
        {
            'purpose': 'resolution',
            'mood': 'contemplative',
            'location': 'rooftop',
            'num_shots': 4
        }
    ]

    # Dialogue
    dialogue = [
        {'speaker': 'character1', 'text': 'What are you doing here?', 'duration': 2.5},
        {'speaker': 'character2', 'text': 'I could ask you the same thing.', 'duration': 2.8},
        {'speaker': 'character1', 'text': 'This ends now.', 'duration': 2.0},
        {'speaker': 'narrator', 'text': 'And so it did.', 'duration': 3.0}
    ]

    # Produce video
    project = await producer.produce_video(
        script=script,
        dialogue=dialogue,
        style="cinematic",
        target_duration=60.0
    )

    # Export
    producer.export_edl(project, "short_film.edl")
    producer.export_json(project, "short_film.json")
    producer.export_srt(project, "short_film.srt")


async def demo_music_video():
    """Produce a music video"""

    producer = SwarmVideo()

    # Music video script
    script = [
        {'purpose': 'introduction', 'mood': 'energetic',
         'location': 'city_streets', 'num_shots': 8},
        {'purpose': 'action', 'mood': 'dynamic',
         'location': 'concert_venue', 'num_shots': 12},
        {'purpose': 'contemplative', 'mood': 'intimate',
         'location': 'backstage', 'num_shots': 6},
        {'purpose': 'action', 'mood': 'explosive',
         'location': 'main_stage', 'num_shots': 15}
    ]

    dialogue = []  # No dialogue in music video

    project = await producer.produce_video(
        script=script,
        dialogue=dialogue,
        style="bright",
        target_duration=180.0
    )

    producer.export_json(project, "music_video.json")


if __name__ == "__main__":
    # Run demos
    asyncio.run(demo_short_film())
    asyncio.run(demo_music_video())

    print("\n✨ SwarmVideo demo complete!")
    print("🎬 Check the generated files for video projects")
