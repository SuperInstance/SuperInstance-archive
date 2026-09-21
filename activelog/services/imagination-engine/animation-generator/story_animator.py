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
import re

class AnimationStyle(Enum):
    TRADITIONAL_2D = "traditional_2d"
    DIGITAL_2D = "digital_2d"
    STOP_MOTION = "stop_motion"
    CUT_OUT = "cut_out"
    SKETCH = "sketch"
    WATERCOLOR = "watercolor"
    MINIMALIST = "minimalist"
    COMIC_BOOK = "comic_book"

class CameraMovement(Enum):
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ORBIT = "orbit"

class TransitionType(Enum):
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"
    SLIDE = "slide"
    ZOOM = "zoom"
    SPIRAL = "spiral"

@dataclass
class AnimationFrame:
    id: str
    scene_id: str
    frame_number: int
    timestamp: float  # seconds from start
    description: str
    camera_position: Dict[str, float]  # x, y, z, rotation
    camera_movement: CameraMovement
    characters: List[Dict[str, Any]]  # character positions and actions
    props: List[Dict[str, Any]]  # props and their states
    background_elements: List[str]
    lighting: Dict[str, Any]
    audio_cues: List[str]
    animation_notes: str

@dataclass
class AnimationScene:
    id: str
    name: str
    description: str
    duration: float  # seconds
    frames: List[AnimationFrame]
    transition_in: TransitionType
    transition_out: TransitionType
    mood: str
    color_palette: List[str]
    music_style: str
    sound_effects: List[str]

@dataclass
class Character:
    id: str
    name: str
    description: str
    design_notes: str
    color_scheme: List[str]
    personality_traits: List[str]
    signature_poses: List[str]
    voice_characteristics: str
    animation_style_notes: str

@dataclass
class AnimationProject:
    id: str
    title: str
    story_source: str  # Reference to original story
    animation_style: AnimationStyle
    target_duration: float  # total seconds
    aspect_ratio: str  # "16:9", "4:3", etc.
    frame_rate: int  # fps
    characters: List[Character]
    scenes: List[AnimationScene]
    color_palette: List[str]
    style_guide: Dict[str, Any]
    production_notes: str
    created_at: str
    updated_at: str

class StoryParser:
    def __init__(self):
        self.scene_markers = [
            r"Chapter \d+", r"Scene \d+", r"\*\*\*", r"---", 
            r"Meanwhile", r"Later", r"The next day", r"Hours later"
        ]
        self.action_verbs = [
            "walks", "runs", "jumps", "speaks", "whispers", "shouts",
            "looks", "turns", "opens", "closes", "picks up", "puts down",
            "sits", "stands", "enters", "exits", "approaches", "retreats"
        ]
        self.emotion_keywords = [
            "angry", "sad", "happy", "excited", "nervous", "calm",
            "frightened", "confident", "surprised", "thoughtful"
        ]

    def parse_story_text(self, story_text: str) -> Dict[str, Any]:
        """Extract scenes, characters, and actions from story text."""
        
        # Split into scenes
        scenes = self._split_into_scenes(story_text)
        
        # Extract characters
        characters = self._extract_characters(story_text)
        
        # Analyze each scene
        parsed_scenes = []
        for i, scene_text in enumerate(scenes):
            parsed_scene = self._analyze_scene(scene_text, i, characters)
            parsed_scenes.append(parsed_scene)
        
        # Extract overall mood and themes
        mood_analysis = self._analyze_overall_mood(story_text)
        
        return {
            "scenes": parsed_scenes,
            "characters": characters,
            "mood": mood_analysis,
            "themes": self._extract_themes(story_text),
            "setting": self._extract_setting(story_text)
        }

    def _split_into_scenes(self, text: str) -> List[str]:
        """Split text into scenes based on markers and narrative flow."""
        scenes = []
        current_scene = ""
        
        lines = text.split('\n')
        
        for line in lines:
            is_scene_break = any(re.search(marker, line, re.IGNORECASE) for marker in self.scene_markers)
            
            if is_scene_break and current_scene.strip():
                scenes.append(current_scene.strip())
                current_scene = line + '\n'
            else:
                current_scene += line + '\n'
        
        if current_scene.strip():
            scenes.append(current_scene.strip())
        
        # If no explicit scene breaks, split by paragraphs and group
        if len(scenes) == 1:
            paragraphs = text.split('\n\n')
            scenes = []
            current_scene = ""
            
            for para in paragraphs:
                current_scene += para + '\n\n'
                if len(current_scene) > 300:  # Rough scene length
                    scenes.append(current_scene.strip())
                    current_scene = ""
            
            if current_scene.strip():
                scenes.append(current_scene.strip())
        
        return scenes

    def _extract_characters(self, text: str) -> List[str]:
        """Extract character names from the text."""
        # Simple name extraction - looks for capitalized words that appear multiple times
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        word_counts = {}
        
        for word in words:
            if word not in ["The", "And", "But", "When", "Then", "That", "This", "They"]:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Characters are likely names that appear multiple times
        characters = [name for name, count in word_counts.items() if count >= 3]
        
        # Add pronouns as generic characters if no specific names found
        if not characters:
            characters = ["Protagonist", "Supporting Character"]
        
        return characters[:6]  # Limit to 6 main characters

    def _analyze_scene(self, scene_text: str, scene_index: int, characters: List[str]) -> Dict[str, Any]:
        """Analyze individual scene for visual and action elements."""
        
        # Extract actions
        actions = []
        for verb in self.action_verbs:
            if verb in scene_text.lower():
                # Find sentences containing this action
                sentences = re.split(r'[.!?]', scene_text)
                for sentence in sentences:
                    if verb in sentence.lower():
                        actions.append(sentence.strip())
        
        # Extract emotions
        emotions = []
        for emotion in self.emotion_keywords:
            if emotion in scene_text.lower():
                emotions.append(emotion)
        
        # Extract dialogue
        dialogue = re.findall(r'"([^"]*)"', scene_text)
        
        # Extract setting details
        setting_clues = self._extract_setting_from_scene(scene_text)
        
        # Determine scene type
        scene_type = self._classify_scene_type(scene_text, actions, dialogue)
        
        return {
            "index": scene_index,
            "text": scene_text,
            "actions": actions[:5],  # Top 5 actions
            "emotions": list(set(emotions)),
            "dialogue": dialogue[:3],  # Top 3 dialogue lines
            "setting": setting_clues,
            "scene_type": scene_type,
            "characters_present": [char for char in characters if char in scene_text],
            "visual_elements": self._extract_visual_elements(scene_text)
        }

    def _extract_setting_from_scene(self, scene_text: str) -> List[str]:
        """Extract setting and location clues from scene text."""
        setting_words = [
            "forest", "castle", "room", "kitchen", "garden", "street", "mountain",
            "ocean", "desert", "city", "village", "house", "tower", "cave", "bridge"
        ]
        
        found_settings = []
        for setting in setting_words:
            if setting in scene_text.lower():
                found_settings.append(setting)
        
        return found_settings

    def _classify_scene_type(self, text: str, actions: List[str], dialogue: List[str]) -> str:
        """Classify the type of scene for animation purposes."""
        
        if dialogue and len(dialogue) > len(actions):
            return "dialogue_heavy"
        elif any(word in text.lower() for word in ["fight", "battle", "chase", "run"]):
            return "action"
        elif any(word in text.lower() for word in ["whisper", "secret", "hide", "sneak"]):
            return "suspense"
        elif any(word in text.lower() for word in ["laugh", "smile", "joy", "celebrate"]):
            return "lighthearted"
        elif any(word in text.lower() for word in ["cry", "sad", "loss", "mourn"]):
            return "emotional"
        else:
            return "narrative"

    def _extract_visual_elements(self, text: str) -> List[str]:
        """Extract visual elements that can be animated."""
        visual_elements = []
        
        # Colors
        colors = ["red", "blue", "green", "yellow", "purple", "orange", "black", "white", "gray", "brown"]
        for color in colors:
            if color in text.lower():
                visual_elements.append(f"color:{color}")
        
        # Objects
        objects = ["sword", "book", "door", "window", "tree", "flower", "stone", "fire", "water", "light"]
        for obj in objects:
            if obj in text.lower():
                visual_elements.append(f"object:{obj}")
        
        # Weather/atmosphere
        weather = ["rain", "snow", "wind", "storm", "sunshine", "clouds", "fog", "mist"]
        for w in weather:
            if w in text.lower():
                visual_elements.append(f"weather:{w}")
        
        return visual_elements

    def _analyze_overall_mood(self, text: str) -> str:
        """Analyze the overall mood of the story."""
        positive_words = ["happy", "joy", "love", "hope", "bright", "beautiful", "wonderful", "amazing"]
        negative_words = ["sad", "dark", "fear", "death", "terrible", "horrible", "awful", "nightmare"]
        
        positive_count = sum(1 for word in positive_words if word in text.lower())
        negative_count = sum(1 for word in negative_words if word in text.lower())
        
        if positive_count > negative_count + 2:
            return "uplifting"
        elif negative_count > positive_count + 2:
            return "dark"
        else:
            return "balanced"

    def _extract_themes(self, text: str) -> List[str]:
        """Extract major themes from the story."""
        themes = []
        
        theme_keywords = {
            "friendship": ["friend", "together", "help", "support"],
            "adventure": ["journey", "quest", "explore", "discover"],
            "love": ["love", "romance", "heart", "beloved"],
            "conflict": ["fight", "battle", "enemy", "war"],
            "growth": ["learn", "change", "grow", "become"],
            "mystery": ["secret", "mystery", "hidden", "unknown"]
        }
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in text.lower() for keyword in keywords):
                themes.append(theme)
        
        return themes

    def _extract_setting(self, text: str) -> str:
        """Extract the primary setting of the story."""
        settings = {
            "medieval": ["castle", "knight", "dragon", "kingdom", "sword"],
            "modern": ["car", "phone", "computer", "city", "apartment"],
            "fantasy": ["magic", "wizard", "elf", "dwarf", "spell"],
            "nature": ["forest", "mountain", "river", "tree", "wild"]
        }
        
        for setting, keywords in settings.items():
            if sum(1 for keyword in keywords if keyword in text.lower()) >= 2:
                return setting
        
        return "generic"

class AnimationPlanner:
    def __init__(self):
        self.style_characteristics = {
            AnimationStyle.TRADITIONAL_2D: {
                "frame_rate": 24,
                "color_palette": ["warm", "hand_drawn"],
                "camera_movements": [CameraMovement.PAN_LEFT, CameraMovement.PAN_RIGHT, CameraMovement.STATIC],
                "transitions": [TransitionType.DISSOLVE, TransitionType.FADE]
            },
            AnimationStyle.DIGITAL_2D: {
                "frame_rate": 30,
                "color_palette": ["vibrant", "saturated"],
                "camera_movements": [CameraMovement.ZOOM_IN, CameraMovement.ZOOM_OUT, CameraMovement.ORBIT],
                "transitions": [TransitionType.SLIDE, TransitionType.WIPE]
            },
            AnimationStyle.SKETCH: {
                "frame_rate": 12,
                "color_palette": ["monochrome", "pencil"],
                "camera_movements": [CameraMovement.STATIC, CameraMovement.TILT_UP],
                "transitions": [TransitionType.CUT, TransitionType.FADE]
            }
        }

    def create_animation_plan(self, parsed_story: Dict[str, Any], 
                            animation_style: AnimationStyle,
                            target_duration: float = 300) -> AnimationProject:
        """Create a complete animation plan from parsed story data."""
        
        project_id = str(uuid.uuid4())
        
        # Create characters
        characters = self._design_characters(parsed_story["characters"], animation_style)
        
        # Plan scenes
        scenes = self._plan_scenes(parsed_story["scenes"], animation_style, target_duration, characters)
        
        # Create overall style guide
        style_guide = self._create_style_guide(animation_style, parsed_story["mood"], parsed_story["setting"])
        
        return AnimationProject(
            id=project_id,
            title=f"Animated Story - {datetime.now().strftime('%Y%m%d')}",
            story_source="Parsed story text",
            animation_style=animation_style,
            target_duration=target_duration,
            aspect_ratio="16:9",
            frame_rate=self.style_characteristics[animation_style]["frame_rate"],
            characters=characters,
            scenes=scenes,
            color_palette=self._generate_color_palette(parsed_story["mood"]),
            style_guide=style_guide,
            production_notes=self._generate_production_notes(parsed_story, animation_style),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _design_characters(self, character_names: List[str], style: AnimationStyle) -> List[Character]:
        """Design animated characters based on names and style."""
        characters = []
        
        character_templates = {
            "protagonist": {
                "traits": ["brave", "curious", "determined"],
                "colors": ["blue", "red", "green"],
                "poses": ["heroic stance", "thinking pose", "action ready"]
            },
            "mentor": {
                "traits": ["wise", "calm", "patient"],
                "colors": ["purple", "brown", "gray"],
                "poses": ["teaching gesture", "contemplative", "supportive"]
            },
            "antagonist": {
                "traits": ["cunning", "powerful", "mysterious"],
                "colors": ["black", "dark red", "purple"],
                "poses": ["threatening", "scheming", "dramatic"]
            }
        }
        
        for i, name in enumerate(character_names):
            char_type = "protagonist" if i == 0 else "mentor" if i == 1 else "antagonist" if i == len(character_names) - 1 else "protagonist"
            template = character_templates[char_type]
            
            character = Character(
                id=str(uuid.uuid4()),
                name=name,
                description=f"A {char_type} character with {', '.join(template['traits'])} personality",
                design_notes=self._generate_design_notes(style, char_type),
                color_scheme=random.sample(template["colors"], min(2, len(template["colors"]))),
                personality_traits=template["traits"],
                signature_poses=template["poses"],
                voice_characteristics=self._generate_voice_notes(char_type),
                animation_style_notes=self._generate_animation_notes(style, char_type)
            )
            characters.append(character)
        
        return characters

    def _generate_design_notes(self, style: AnimationStyle, char_type: str) -> str:
        """Generate character design notes based on animation style."""
        style_notes = {
            AnimationStyle.TRADITIONAL_2D: "Hand-drawn look with soft lines and traditional proportions",
            AnimationStyle.DIGITAL_2D: "Clean vector-style design with bold outlines",
            AnimationStyle.SKETCH: "Loose, sketchy lines with visible construction marks",
            AnimationStyle.MINIMALIST: "Simple geometric shapes, minimal details"
        }
        
        return style_notes.get(style, "Standard animation design")

    def _generate_voice_notes(self, char_type: str) -> str:
        """Generate voice characteristic notes."""
        voice_notes = {
            "protagonist": "Clear, relatable voice with emotional range",
            "mentor": "Deeper, slower voice with wisdom and authority",
            "antagonist": "Distinctive voice with menacing or mysterious quality"
        }
        
        return voice_notes.get(char_type, "Standard character voice")

    def _generate_animation_notes(self, style: AnimationStyle, char_type: str) -> str:
        """Generate animation-specific notes for characters."""
        notes = f"Animated in {style.value} style. "
        
        if char_type == "protagonist":
            notes += "Expressive facial animations, dynamic movement"
        elif char_type == "mentor":
            notes += "Slower, more deliberate movements, wise gestures"
        elif char_type == "antagonist":
            notes += "Sharp, angular movements, dramatic poses"
        
        return notes

    def _plan_scenes(self, parsed_scenes: List[Dict[str, Any]], 
                    style: AnimationStyle, 
                    total_duration: float,
                    characters: List[Character]) -> List[AnimationScene]:
        """Plan animation scenes from parsed story scenes."""
        
        scenes = []
        scene_duration = total_duration / len(parsed_scenes) if parsed_scenes else 60
        
        for i, parsed_scene in enumerate(parsed_scenes):
            scene = self._create_animation_scene(
                parsed_scene, i, scene_duration, style, characters
            )
            scenes.append(scene)
        
        return scenes

    def _create_animation_scene(self, parsed_scene: Dict[str, Any], 
                               scene_index: int,
                               duration: float,
                               style: AnimationStyle,
                               characters: List[Character]) -> AnimationScene:
        """Create detailed animation scene from parsed scene data."""
        
        scene_id = str(uuid.uuid4())
        
        # Determine mood and color palette for scene
        mood = self._determine_scene_mood(parsed_scene)
        color_palette = self._generate_scene_colors(mood, style)
        
        # Create frames for the scene
        frames = self._generate_scene_frames(
            scene_id, parsed_scene, duration, style, characters
        )
        
        # Choose transitions
        style_chars = self.style_characteristics.get(style, {})
        transitions = style_chars.get("transitions", [TransitionType.CUT, TransitionType.FADE])
        
        return AnimationScene(
            id=scene_id,
            name=f"Scene {scene_index + 1}",
            description=parsed_scene.get("text", "")[:100] + "...",
            duration=duration,
            frames=frames,
            transition_in=random.choice(transitions),
            transition_out=random.choice(transitions),
            mood=mood,
            color_palette=color_palette,
            music_style=self._suggest_music_style(mood, parsed_scene.get("scene_type", "narrative")),
            sound_effects=self._suggest_sound_effects(parsed_scene)
        )

    def _determine_scene_mood(self, parsed_scene: Dict[str, Any]) -> str:
        """Determine the mood of a specific scene."""
        scene_type = parsed_scene.get("scene_type", "narrative")
        emotions = parsed_scene.get("emotions", [])
        
        if "action" in scene_type:
            return "intense"
        elif "emotional" in scene_type:
            return "poignant"
        elif "lighthearted" in scene_type:
            return "cheerful"
        elif "suspense" in scene_type:
            return "tense"
        elif emotions:
            if any(emotion in ["happy", "joy", "excited"] for emotion in emotions):
                return "upbeat"
            elif any(emotion in ["sad", "angry", "frightened"] for emotion in emotions):
                return "somber"
        
        return "neutral"

    def _generate_scene_colors(self, mood: str, style: AnimationStyle) -> List[str]:
        """Generate color palette for a scene based on mood."""
        color_palettes = {
            "intense": ["red", "orange", "yellow", "black"],
            "poignant": ["blue", "purple", "gray", "soft pink"],
            "cheerful": ["yellow", "green", "light blue", "orange"],
            "tense": ["dark blue", "black", "gray", "deep purple"],
            "upbeat": ["bright green", "yellow", "orange", "light blue"],
            "somber": ["gray", "dark blue", "muted green", "brown"],
            "neutral": ["blue", "green", "brown", "beige"]
        }
        
        return color_palettes.get(mood, color_palettes["neutral"])

    def _generate_scene_frames(self, scene_id: str, 
                             parsed_scene: Dict[str, Any],
                             duration: float,
                             style: AnimationStyle,
                             characters: List[Character]) -> List[AnimationFrame]:
        """Generate key frames for the scene."""
        
        frames = []
        frame_rate = self.style_characteristics.get(style, {}).get("frame_rate", 24)
        total_frames = int(duration * frame_rate)
        
        # Create key frames at important moments
        key_moments = len(parsed_scene.get("actions", [])) + len(parsed_scene.get("dialogue", []))
        key_moments = max(3, min(key_moments, 8))  # Between 3-8 key frames
        
        frame_interval = total_frames // key_moments
        
        for i in range(key_moments):
            frame_number = i * frame_interval
            timestamp = frame_number / frame_rate
            
            frame = AnimationFrame(
                id=str(uuid.uuid4()),
                scene_id=scene_id,
                frame_number=frame_number,
                timestamp=timestamp,
                description=self._generate_frame_description(i, parsed_scene),
                camera_position=self._generate_camera_position(i, key_moments),
                camera_movement=self._choose_camera_movement(parsed_scene, style),
                characters=self._position_characters(characters, parsed_scene, i),
                props=self._generate_props(parsed_scene),
                background_elements=self._generate_background_elements(parsed_scene),
                lighting=self._generate_lighting(parsed_scene, i, key_moments),
                audio_cues=self._generate_audio_cues(parsed_scene, i),
                animation_notes=self._generate_frame_notes(parsed_scene, i)
            )
            frames.append(frame)
        
        return frames

    def _generate_frame_description(self, frame_index: int, parsed_scene: Dict[str, Any]) -> str:
        """Generate description for individual frame."""
        actions = parsed_scene.get("actions", [])
        dialogue = parsed_scene.get("dialogue", [])
        
        if frame_index < len(actions):
            return f"Frame showing: {actions[frame_index]}"
        elif frame_index - len(actions) < len(dialogue):
            return f"Dialogue frame: {dialogue[frame_index - len(actions)]}"
        else:
            return f"Establishing shot or transition frame {frame_index + 1}"

    def _generate_camera_position(self, frame_index: int, total_frames: int) -> Dict[str, float]:
        """Generate camera position for frame."""
        # Simple camera positioning - can be made more sophisticated
        progress = frame_index / max(1, total_frames - 1)
        
        return {
            "x": 0.0 + progress * 100,  # Slow pan across scene
            "y": 50.0,  # Standard eye level
            "z": 200.0,  # Distance from subjects
            "rotation": 0.0 + progress * 10  # Slight rotation
        }

    def _choose_camera_movement(self, parsed_scene: Dict[str, Any], style: AnimationStyle) -> CameraMovement:
        """Choose appropriate camera movement for scene."""
        scene_type = parsed_scene.get("scene_type", "narrative")
        available_movements = self.style_characteristics.get(style, {}).get("camera_movements", [CameraMovement.STATIC])
        
        if scene_type == "action":
            dynamic_movements = [CameraMovement.PAN_LEFT, CameraMovement.PAN_RIGHT, CameraMovement.ORBIT]
            return random.choice([m for m in dynamic_movements if m in available_movements] or available_movements)
        elif scene_type == "dialogue_heavy":
            return CameraMovement.STATIC
        else:
            return random.choice(available_movements)

    def _position_characters(self, characters: List[Character], 
                           parsed_scene: Dict[str, Any], 
                           frame_index: int) -> List[Dict[str, Any]]:
        """Position characters in the frame."""
        present_characters = parsed_scene.get("characters_present", [])
        positioned_characters = []
        
        for i, char_name in enumerate(present_characters[:3]):  # Max 3 characters per frame
            character = next((c for c in characters if c.name == char_name), None)
            if character:
                positioned_characters.append({
                    "character_id": character.id,
                    "name": character.name,
                    "x": 100 + i * 150,  # Spread characters across frame
                    "y": 100,
                    "scale": 1.0,
                    "pose": random.choice(character.signature_poses),
                    "facing": "center" if i == 1 else ("left" if i == 0 else "right"),
                    "emotion": self._choose_character_emotion(parsed_scene, frame_index)
                })
        
        return positioned_characters

    def _choose_character_emotion(self, parsed_scene: Dict[str, Any], frame_index: int) -> str:
        """Choose appropriate emotion for character in this frame."""
        emotions = parsed_scene.get("emotions", ["neutral"])
        scene_type = parsed_scene.get("scene_type", "narrative")
        
        if scene_type == "action":
            return random.choice(["determined", "focused", "intense"])
        elif scene_type == "emotional":
            return random.choice(emotions) if emotions else "thoughtful"
        elif scene_type == "lighthearted":
            return random.choice(["happy", "amused", "cheerful"])
        else:
            return random.choice(emotions + ["neutral"])

    def _generate_props(self, parsed_scene: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate props for the scene."""
        visual_elements = parsed_scene.get("visual_elements", [])
        props = []
        
        for element in visual_elements:
            if element.startswith("object:"):
                obj_name = element.split(":")[1]
                props.append({
                    "name": obj_name,
                    "x": random.randint(50, 350),
                    "y": random.randint(50, 200),
                    "scale": random.uniform(0.5, 1.5),
                    "rotation": 0,
                    "visible": True
                })
        
        return props[:5]  # Limit props to avoid clutter

    def _generate_background_elements(self, parsed_scene: Dict[str, Any]) -> List[str]:
        """Generate background elements for the scene."""
        setting_elements = parsed_scene.get("setting", [])
        visual_elements = parsed_scene.get("visual_elements", [])
        
        backgrounds = []
        
        for setting in setting_elements:
            if setting == "forest":
                backgrounds.extend(["trees", "foliage", "dappled sunlight"])
            elif setting == "castle":
                backgrounds.extend(["stone walls", "tapestries", "tall windows"])
            elif setting == "room":
                backgrounds.extend(["furniture", "walls", "lighting"])
        
        # Add weather elements
        for element in visual_elements:
            if element.startswith("weather:"):
                weather = element.split(":")[1]
                backgrounds.append(f"{weather} effects")
        
        return backgrounds[:5]

    def _generate_lighting(self, parsed_scene: Dict[str, Any], 
                         frame_index: int, 
                         total_frames: int) -> Dict[str, Any]:
        """Generate lighting setup for frame."""
        mood = self._determine_scene_mood(parsed_scene)
        
        lighting_setups = {
            "intense": {"primary": "harsh", "color": "red-orange", "shadows": "dramatic"},
            "poignant": {"primary": "soft", "color": "blue", "shadows": "gentle"},
            "cheerful": {"primary": "bright", "color": "warm yellow", "shadows": "minimal"},
            "tense": {"primary": "low", "color": "cold blue", "shadows": "deep"},
            "neutral": {"primary": "standard", "color": "white", "shadows": "normal"}
        }
        
        return lighting_setups.get(mood, lighting_setups["neutral"])

    def _generate_audio_cues(self, parsed_scene: Dict[str, Any], frame_index: int) -> List[str]:
        """Generate audio cues for the frame."""
        audio_cues = []
        
        dialogue = parsed_scene.get("dialogue", [])
        if frame_index < len(dialogue):
            audio_cues.append(f"Dialogue: {dialogue[frame_index][:30]}...")
        
        scene_type = parsed_scene.get("scene_type", "narrative")
        if scene_type == "action":
            audio_cues.extend(["Action music", "Sound effects"])
        elif scene_type == "emotional":
            audio_cues.append("Emotional music")
        
        return audio_cues

    def _generate_frame_notes(self, parsed_scene: Dict[str, Any], frame_index: int) -> str:
        """Generate animation notes for the frame."""
        scene_type = parsed_scene.get("scene_type", "narrative")
        
        if scene_type == "action":
            return "Fast-paced animation with dynamic movement"
        elif scene_type == "dialogue_heavy":
            return "Focus on lip-sync and facial expressions"
        elif scene_type == "emotional":
            return "Slow, expressive animation emphasizing emotion"
        else:
            return "Standard animation timing and movement"

    def _suggest_music_style(self, mood: str, scene_type: str) -> str:
        """Suggest appropriate music style for the scene."""
        music_suggestions = {
            ("intense", "action"): "Fast-paced orchestral with percussion",
            ("poignant", "emotional"): "Slow piano or strings",
            ("cheerful", "lighthearted"): "Upbeat acoustic or folk",
            ("tense", "suspense"): "Low strings with dissonance",
            ("neutral", "dialogue_heavy"): "Subtle ambient background"
        }
        
        return music_suggestions.get((mood, scene_type), "Ambient background music")

    def _suggest_sound_effects(self, parsed_scene: Dict[str, Any]) -> List[str]:
        """Suggest sound effects for the scene."""
        effects = []
        
        actions = parsed_scene.get("actions", [])
        for action in actions:
            if "walk" in action.lower():
                effects.append("footsteps")
            elif "door" in action.lower():
                effects.append("door creak/slam")
            elif "water" in action.lower():
                effects.append("water sounds")
        
        visual_elements = parsed_scene.get("visual_elements", [])
        for element in visual_elements:
            if "weather:wind" in element:
                effects.append("wind sounds")
            elif "weather:rain" in element:
                effects.append("rainfall")
        
        return list(set(effects))  # Remove duplicates

    def _create_style_guide(self, style: AnimationStyle, mood: str, setting: str) -> Dict[str, Any]:
        """Create comprehensive style guide for the animation."""
        return {
            "animation_style": style.value,
            "overall_mood": mood,
            "setting_type": setting,
            "line_style": self._get_line_style(style),
            "color_approach": self._get_color_approach(style, mood),
            "character_proportions": self._get_proportions(style),
            "timing_notes": self._get_timing_notes(style),
            "special_effects": self._get_effects_notes(style, setting)
        }

    def _get_line_style(self, style: AnimationStyle) -> str:
        line_styles = {
            AnimationStyle.TRADITIONAL_2D: "Hand-drawn, slightly varying line weight",
            AnimationStyle.DIGITAL_2D: "Clean vector lines, consistent weight",
            AnimationStyle.SKETCH: "Loose, sketchy lines with visible texture",
            AnimationStyle.MINIMALIST: "Simple, geometric lines"
        }
        return line_styles.get(style, "Standard animation lines")

    def _get_color_approach(self, style: AnimationStyle, mood: str) -> str:
        if style == AnimationStyle.SKETCH:
            return "Minimal color, focus on line work"
        elif mood == "intense":
            return "High contrast, saturated colors"
        elif mood == "poignant":
            return "Muted, desaturated palette"
        else:
            return "Balanced color palette with mood-appropriate saturation"

    def _get_proportions(self, style: AnimationStyle) -> str:
        proportions = {
            AnimationStyle.TRADITIONAL_2D: "Classic animation proportions (6-7 heads tall)",
            AnimationStyle.DIGITAL_2D: "Modern animation proportions (7-8 heads tall)",
            AnimationStyle.SKETCH: "Loose, expressive proportions",
            AnimationStyle.MINIMALIST: "Simplified, geometric proportions"
        }
        return proportions.get(style, "Standard human proportions")

    def _get_timing_notes(self, style: AnimationStyle) -> str:
        timing = {
            AnimationStyle.TRADITIONAL_2D: "Classic 12 principles timing",
            AnimationStyle.DIGITAL_2D: "Modern, slightly faster timing",
            AnimationStyle.SKETCH: "Loose, impressionistic timing",
            AnimationStyle.MINIMALIST: "Simple, clear timing"
        }
        return timing.get(style, "Standard animation timing")

    def _get_effects_notes(self, style: AnimationStyle, setting: str) -> str:
        if setting == "fantasy":
            return "Magical effects with particle systems and glows"
        elif setting == "modern":
            return "Realistic effects, minimal stylization"
        else:
            return "Style-appropriate effects matching overall aesthetic"

    def _generate_production_notes(self, parsed_story: Dict[str, Any], style: AnimationStyle) -> str:
        """Generate overall production notes."""
        notes = f"Animation project in {style.value} style.\n"
        notes += f"Story themes: {', '.join(parsed_story.get('themes', []))}\n"
        notes += f"Overall mood: {parsed_story.get('mood', 'balanced')}\n"
        notes += f"Primary setting: {parsed_story.get('setting', 'generic')}\n"
        notes += f"Number of scenes: {len(parsed_story.get('scenes', []))}\n"
        notes += f"Main characters: {', '.join(parsed_story.get('characters', []))}\n"
        
        return notes

    def _generate_color_palette(self, mood: str) -> List[str]:
        """Generate main color palette for the entire animation."""
        palettes = {
            "uplifting": ["#FFD700", "#87CEEB", "#98FB98", "#FFA07A"],  # Gold, Sky Blue, Pale Green, Light Salmon
            "dark": ["#2F4F4F", "#8B0000", "#483D8B", "#696969"],  # Dark Slate Gray, Dark Red, Dark Slate Blue, Dim Gray
            "balanced": ["#4682B4", "#228B22", "#DAA520", "#CD853F"]  # Steel Blue, Forest Green, Goldenrod, Peru
        }
        
        return palettes.get(mood, palettes["balanced"])

class StoryAnimator:
    def __init__(self, db_path: str = "story_animation.db"):
        self.db_path = db_path
        self.story_parser = StoryParser()
        self.animation_planner = AnimationPlanner()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS animation_projects (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            story_source TEXT,
            animation_style TEXT,
            target_duration REAL,
            aspect_ratio TEXT,
            frame_rate INTEGER,
            characters TEXT,
            scenes TEXT,
            color_palette TEXT,
            style_guide TEXT,
            production_notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_animation_from_story(self, story_text: str, 
                                        animation_style: str = "digital_2d",
                                        target_duration: float = 300) -> AnimationProject:
        """Create complete animation project from story text."""
        
        # Parse the story
        parsed_story = self.story_parser.parse_story_text(story_text)
        
        # Create animation plan
        style_enum = AnimationStyle(animation_style)
        animation_project = self.animation_planner.create_animation_plan(
            parsed_story, style_enum, target_duration
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO animation_projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            animation_project.id,
            animation_project.title,
            animation_project.story_source,
            animation_project.animation_style.value,
            animation_project.target_duration,
            animation_project.aspect_ratio,
            animation_project.frame_rate,
            json.dumps([asdict(char) for char in animation_project.characters]),
            json.dumps([asdict(scene) for scene in animation_project.scenes]),
            json.dumps(animation_project.color_palette),
            json.dumps(animation_project.style_guide),
            animation_project.production_notes,
            animation_project.created_at,
            animation_project.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return animation_project

    async def get_animation_project(self, project_id: str) -> Optional[AnimationProject]:
        """Retrieve animation project from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM animation_projects WHERE id = ?', (project_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct objects
        characters_data = json.loads(row[7])
        characters = [Character(**char_data) for char_data in characters_data]
        
        scenes_data = json.loads(row[8])
        scenes = []
        for scene_data in scenes_data:
            # Reconstruct frames
            frames_data = scene_data.pop('frames', [])
            scene = AnimationScene(**scene_data)
            scene.frames = [AnimationFrame(**frame_data) for frame_data in frames_data]
            scenes.append(scene)
        
        return AnimationProject(
            id=row[0], title=row[1], story_source=row[2],
            animation_style=AnimationStyle(row[3]),
            target_duration=row[4], aspect_ratio=row[5], frame_rate=row[6],
            characters=characters, scenes=scenes,
            color_palette=json.loads(row[9]),
            style_guide=json.loads(row[10]),
            production_notes=row[11],
            created_at=row[12], updated_at=row[13]
        )

    async def export_storyboard(self, project_id: str) -> Dict[str, Any]:
        """Export storyboard information for the animation."""
        project = await self.get_animation_project(project_id)
        if not project:
            return {"error": "Project not found"}
        
        storyboard = {
            "project_title": project.title,
            "animation_style": project.animation_style.value,
            "total_duration": project.target_duration,
            "total_scenes": len(project.scenes),
            "characters": [{"name": char.name, "description": char.description} 
                         for char in project.characters],
            "scenes": []
        }
        
        for scene in project.scenes:
            scene_info = {
                "name": scene.name,
                "duration": scene.duration,
                "mood": scene.mood,
                "description": scene.description,
                "key_frames": []
            }
            
            for frame in scene.frames[:3]:  # First 3 key frames per scene
                frame_info = {
                    "timestamp": frame.timestamp,
                    "description": frame.description,
                    "characters": len(frame.characters),
                    "camera_movement": frame.camera_movement.value,
                    "notes": frame.animation_notes
                }
                scene_info["key_frames"].append(frame_info)
            
            storyboard["scenes"].append(scene_info)
        
        return storyboard

    async def generate_production_timeline(self, project_id: str) -> Dict[str, Any]:
        """Generate production timeline and estimates."""
        project = await self.get_animation_project(project_id)
        if not project:
            return {"error": "Project not found"}
        
        # Estimate production time based on animation complexity
        total_frames = sum(len(scene.frames) for scene in project.scenes)
        frame_rate = project.frame_rate
        total_animation_seconds = project.target_duration
        
        # Production estimates (in days)
        pre_production_days = 5  # Script, storyboard, design
        character_design_days = len(project.characters) * 2
        background_design_days = len(project.scenes) * 1
        animation_days = total_animation_seconds * 0.5  # 2 seconds per day average
        post_production_days = 3  # Editing, sound, final
        
        total_days = (pre_production_days + character_design_days + 
                     background_design_days + animation_days + post_production_days)
        
        timeline = {
            "project_title": project.title,
            "total_estimated_days": int(total_days),
            "phases": {
                "pre_production": {
                    "days": pre_production_days,
                    "tasks": ["Script finalization", "Storyboard creation", "Style guide"]
                },
                "character_design": {
                    "days": character_design_days,
                    "tasks": [f"Design {char.name}" for char in project.characters]
                },
                "background_design": {
                    "days": background_design_days,
                    "tasks": [f"Create backgrounds for {scene.name}" for scene in project.scenes]
                },
                "animation": {
                    "days": int(animation_days),
                    "tasks": ["Keyframe animation", "In-between frames", "Cleanup"]
                },
                "post_production": {
                    "days": post_production_days,
                    "tasks": ["Compositing", "Sound design", "Final editing"]
                }
            },
            "milestones": [
                f"Day {pre_production_days}: Pre-production complete",
                f"Day {pre_production_days + character_design_days}: Character design complete",
                f"Day {int(total_days * 0.7)}: Animation 70% complete",
                f"Day {int(total_days)}: Final delivery"
            ]
        }
        
        return timeline

if __name__ == "__main__":
    async def main():
        animator = StoryAnimator()
        
        # Sample story
        story_text = """
        Once upon a time, there was a brave young knight named Elena who lived in a peaceful village. 
        One day, a terrible dragon appeared and threatened her home. Elena picked up her sword and 
        set out on a quest to defeat the monster.
        
        She traveled through the dark forest, where she met an old wizard who gave her magical armor. 
        "This will protect you," he said with a wise smile. Elena thanked him and continued her journey.
        
        Finally, she reached the dragon's lair on top of a tall mountain. The dragon was huge and 
        breathed fire, but Elena was brave. She fought the dragon with all her strength and finally 
        defeated it, saving her village and becoming a hero.
        """
        
        # Create animation project
        project = await animator.create_animation_from_story(
            story_text,
            animation_style="traditional_2d",
            target_duration=180  # 3 minutes
        )
        
        print(f"Created animation project: {project.title}")
        print(f"Animation style: {project.animation_style.value}")
        print(f"Number of characters: {len(project.characters)}")
        print(f"Number of scenes: {len(project.scenes)}")
        
        # Export storyboard
        storyboard = await animator.export_storyboard(project.id)
        print(f"\nStoryboard exported with {len(storyboard['scenes'])} scenes")
        
        # Get production timeline
        timeline = await animator.generate_production_timeline(project.id)
        print(f"Estimated production time: {timeline['total_estimated_days']} days")
        
        # Show first scene details
        if project.scenes:
            first_scene = project.scenes[0]
            print(f"\nFirst scene: {first_scene.name}")
            print(f"Duration: {first_scene.duration} seconds")
            print(f"Mood: {first_scene.mood}")
            print(f"Key frames: {len(first_scene.frames)}")
    
    asyncio.run(main())