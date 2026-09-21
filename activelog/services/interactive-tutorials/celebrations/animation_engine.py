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

class CelebrationType(Enum):
    STEP_COMPLETE = "step_complete"
    MILESTONE_REACHED = "milestone_reached"  
    PERFECT_EXECUTION = "perfect_execution"
    BREAKTHROUGH_MOMENT = "breakthrough_moment"
    TUTORIAL_COMPLETE = "tutorial_complete"
    STREAK_ACHIEVEMENT = "streak_achievement"
    IMPROVEMENT_SHOWN = "improvement_shown"
    CHALLENGE_OVERCOME = "challenge_overcome"

class AnimationStyle(Enum):
    CONFETTI_BURST = "confetti_burst"
    FIREWORKS = "fireworks"
    SPARKLES = "sparkles" 
    TROPHY_RISE = "trophy_rise"
    STAR_SHOWER = "star_shower"
    RAINBOW_WAVE = "rainbow_wave"
    BALLOONS_FLOAT = "balloons_float"
    HEARTS_FLOAT = "hearts_float"
    LIGHT_RAYS = "light_rays"
    PARTICLE_EXPLOSION = "particle_explosion"

class IntensityLevel(Enum):
    SUBTLE = "subtle"
    MODERATE = "moderate"
    ENTHUSIASTIC = "enthusiastic"
    SPECTACULAR = "spectacular"

@dataclass
class AnimationElement:
    id: str
    element_type: str
    position: Dict[str, float]  # x, y, z coordinates
    velocity: Dict[str, float]  # movement vector
    rotation: Dict[str, float]  # rotation angles
    scale: float
    color: str
    opacity: float
    lifespan: float  # seconds
    physics_properties: Dict[str, Any]
    texture: str
    glow_effect: bool

@dataclass
class CelebrationAnimation:
    id: str
    celebration_type: CelebrationType
    animation_style: AnimationStyle
    intensity_level: IntensityLevel
    duration: float  # seconds
    elements: List[AnimationElement]
    sound_effects: List[str]
    screen_effects: List[Dict[str, Any]]
    camera_effects: List[Dict[str, Any]]
    haptic_feedback: Optional[Dict[str, Any]]
    trigger_conditions: List[str]
    personalization_data: Dict[str, Any]
    created_at: str

@dataclass
class UserCelebrationProfile:
    user_id: str
    preferred_styles: List[AnimationStyle]
    intensity_preference: IntensityLevel
    accessibility_settings: Dict[str, bool]
    motion_sensitivity: int  # 1-10 scale
    sound_preferences: Dict[str, Any]
    celebration_frequency: str  # frequent, moderate, minimal
    cultural_preferences: List[str]
    disable_flashing: bool
    reduced_motion: bool

class AnimationPhysicsEngine:
    def __init__(self):
        self.gravity = 9.81  # m/s²
        self.air_resistance = 0.1
        
    def calculate_particle_motion(self, element: AnimationElement, 
                                time_delta: float) -> AnimationElement:
        """Calculate particle motion based on physics."""
        
        # Update position based on velocity
        element.position["x"] += element.velocity["x"] * time_delta
        element.position["y"] += element.velocity["y"] * time_delta
        element.position["z"] += element.velocity["z"] * time_delta
        
        # Apply gravity
        if element.physics_properties.get("affected_by_gravity", True):
            element.velocity["y"] -= self.gravity * time_delta
        
        # Apply air resistance
        resistance_factor = 1.0 - (self.air_resistance * time_delta)
        element.velocity["x"] *= resistance_factor
        element.velocity["z"] *= resistance_factor
        
        # Update rotation
        rotation_speed = element.physics_properties.get("rotation_speed", 0)
        element.rotation["y"] += rotation_speed * time_delta
        
        # Update scale for growing/shrinking effects
        scale_rate = element.physics_properties.get("scale_rate", 0)
        element.scale += scale_rate * time_delta
        element.scale = max(0.1, element.scale)  # Prevent negative/zero scale
        
        # Update opacity for fade effects
        fade_rate = element.physics_properties.get("fade_rate", 0)
        element.opacity += fade_rate * time_delta
        element.opacity = max(0.0, min(1.0, element.opacity))
        
        # Decrease lifespan
        element.lifespan -= time_delta
        
        return element
    
    def apply_forces(self, element: AnimationElement, forces: List[Dict[str, Any]]) -> AnimationElement:
        """Apply external forces to an element."""
        
        for force in forces:
            force_type = force.get("type")
            strength = force.get("strength", 1.0)
            
            if force_type == "wind":
                direction = force.get("direction", {"x": 1, "y": 0, "z": 0})
                element.velocity["x"] += direction["x"] * strength * 0.1
                element.velocity["z"] += direction["z"] * strength * 0.1
            
            elif force_type == "magnetic":
                target = force.get("target_position", {"x": 0, "y": 0, "z": 0})
                dx = target["x"] - element.position["x"]
                dy = target["y"] - element.position["y"]
                dz = target["z"] - element.position["z"]
                
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                if distance > 0:
                    force_strength = strength / (distance * distance)  # Inverse square law
                    element.velocity["x"] += (dx / distance) * force_strength
                    element.velocity["y"] += (dy / distance) * force_strength
                    element.velocity["z"] += (dz / distance) * force_strength
            
            elif force_type == "explosion":
                center = force.get("center", {"x": 0, "y": 0, "z": 0})
                dx = element.position["x"] - center["x"]
                dy = element.position["y"] - center["y"]
                dz = element.position["z"] - center["z"]
                
                distance = math.sqrt(dx*dx + dy*dy + dz*dz)
                if distance > 0:
                    explosion_strength = strength / max(1.0, distance)
                    element.velocity["x"] += (dx / distance) * explosion_strength
                    element.velocity["y"] += (dy / distance) * explosion_strength
                    element.velocity["z"] += (dz / distance) * explosion_strength
        
        return element

class CelebrationFactory:
    def __init__(self):
        self.physics_engine = AnimationPhysicsEngine()
        
        self.color_schemes = {
            "rainbow": ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"],
            "gold": ["#FFD700", "#FFA500", "#FFFF00", "#FFC125"],
            "celebration": ["#FF1493", "#00CED1", "#FF69B4", "#32CD32", "#FFD700"],
            "success": ["#00FF00", "#32CD32", "#90EE90", "#00FA9A"],
            "achievement": ["#4169E1", "#1E90FF", "#87CEEB", "#B0E0E6"]
        }
        
        self.sound_libraries = {
            CelebrationType.STEP_COMPLETE: ["ding", "chime", "bell"],
            CelebrationType.MILESTONE_REACHED: ["fanfare", "trumpet", "celebration"],
            CelebrationType.PERFECT_EXECUTION: ["perfect", "excellent", "stellar"],
            CelebrationType.TUTORIAL_COMPLETE: ["victory", "achievement", "complete"]
        }

    def create_celebration(self, celebration_type: CelebrationType,
                          intensity: IntensityLevel,
                          user_profile: UserCelebrationProfile = None,
                          context: Dict[str, Any] = None) -> CelebrationAnimation:
        """Create a celebration animation."""
        
        animation_id = str(uuid.uuid4())
        
        # Choose animation style based on user preference or celebration type
        if user_profile and user_profile.preferred_styles:
            style = random.choice(user_profile.preferred_styles)
        else:
            style = self._choose_default_style(celebration_type)
        
        # Adjust intensity based on user preference
        if user_profile and user_profile.intensity_preference:
            intensity = user_profile.intensity_preference
        
        # Create animation elements
        elements = self._create_animation_elements(style, intensity, user_profile)
        
        # Add sound effects
        sound_effects = self._select_sound_effects(celebration_type, intensity, user_profile)
        
        # Create screen effects
        screen_effects = self._create_screen_effects(style, intensity, user_profile)
        
        # Create camera effects
        camera_effects = self._create_camera_effects(style, intensity, user_profile)
        
        # Haptic feedback
        haptic = self._create_haptic_feedback(intensity, user_profile) if user_profile else None
        
        # Calculate duration
        duration = self._calculate_duration(intensity, len(elements))
        
        return CelebrationAnimation(
            id=animation_id,
            celebration_type=celebration_type,
            animation_style=style,
            intensity_level=intensity,
            duration=duration,
            elements=elements,
            sound_effects=sound_effects,
            screen_effects=screen_effects,
            camera_effects=camera_effects,
            haptic_feedback=haptic,
            trigger_conditions=self._generate_trigger_conditions(celebration_type),
            personalization_data=self._create_personalization_data(user_profile, context),
            created_at=datetime.now().isoformat()
        )

    def _choose_default_style(self, celebration_type: CelebrationType) -> AnimationStyle:
        """Choose default animation style for celebration type."""
        
        style_mappings = {
            CelebrationType.STEP_COMPLETE: AnimationStyle.SPARKLES,
            CelebrationType.MILESTONE_REACHED: AnimationStyle.FIREWORKS,
            CelebrationType.PERFECT_EXECUTION: AnimationStyle.STAR_SHOWER,
            CelebrationType.BREAKTHROUGH_MOMENT: AnimationStyle.LIGHT_RAYS,
            CelebrationType.TUTORIAL_COMPLETE: AnimationStyle.CONFETTI_BURST,
            CelebrationType.STREAK_ACHIEVEMENT: AnimationStyle.RAINBOW_WAVE,
            CelebrationType.IMPROVEMENT_SHOWN: AnimationStyle.TROPHY_RISE,
            CelebrationType.CHALLENGE_OVERCOME: AnimationStyle.PARTICLE_EXPLOSION
        }
        
        return style_mappings.get(celebration_type, AnimationStyle.SPARKLES)

    def _create_animation_elements(self, style: AnimationStyle, 
                                 intensity: IntensityLevel,
                                 user_profile: UserCelebrationProfile) -> List[AnimationElement]:
        """Create animation elements based on style and intensity."""
        
        elements = []
        
        # Determine number of elements based on intensity
        element_counts = {
            IntensityLevel.SUBTLE: 10,
            IntensityLevel.MODERATE: 25,
            IntensityLevel.ENTHUSIASTIC: 50,
            IntensityLevel.SPECTACULAR: 100
        }
        
        num_elements = element_counts.get(intensity, 25)
        
        # Reduce elements if user has accessibility needs
        if user_profile and user_profile.reduced_motion:
            num_elements = min(num_elements, 15)
        
        # Create elements based on animation style
        if style == AnimationStyle.CONFETTI_BURST:
            elements = self._create_confetti_elements(num_elements, intensity)
        elif style == AnimationStyle.FIREWORKS:
            elements = self._create_fireworks_elements(num_elements, intensity)
        elif style == AnimationStyle.SPARKLES:
            elements = self._create_sparkle_elements(num_elements, intensity)
        elif style == AnimationStyle.TROPHY_RISE:
            elements = self._create_trophy_elements(num_elements, intensity)
        elif style == AnimationStyle.STAR_SHOWER:
            elements = self._create_star_elements(num_elements, intensity)
        elif style == AnimationStyle.RAINBOW_WAVE:
            elements = self._create_rainbow_elements(num_elements, intensity)
        elif style == AnimationStyle.BALLOONS_FLOAT:
            elements = self._create_balloon_elements(num_elements, intensity)
        elif style == AnimationStyle.PARTICLE_EXPLOSION:
            elements = self._create_particle_elements(num_elements, intensity)
        else:
            elements = self._create_generic_elements(num_elements, intensity)
        
        return elements

    def _create_confetti_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create confetti animation elements."""
        
        elements = []
        colors = self.color_schemes["celebration"]
        
        for i in range(count):
            # Start position (above screen)
            start_x = random.uniform(-1.0, 1.0)
            start_y = random.uniform(1.2, 1.5)
            start_z = random.uniform(-0.5, 0.5)
            
            # Initial velocity (spread outward and downward)
            vel_x = random.uniform(-2.0, 2.0)
            vel_y = random.uniform(-1.0, 1.0)
            vel_z = random.uniform(-1.0, 1.0)
            
            # Random rotation
            rotation_speed = random.uniform(180, 720)  # degrees per second
            
            element = AnimationElement(
                id=str(uuid.uuid4()),
                element_type="confetti_piece",
                position={"x": start_x, "y": start_y, "z": start_z},
                velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                rotation={"x": 0, "y": 0, "z": 0},
                scale=random.uniform(0.02, 0.05),
                color=random.choice(colors),
                opacity=1.0,
                lifespan=random.uniform(3.0, 6.0),
                physics_properties={
                    "affected_by_gravity": True,
                    "rotation_speed": rotation_speed,
                    "fade_rate": -0.1  # Fade out slowly
                },
                texture="confetti",
                glow_effect=False
            )
            
            elements.append(element)
        
        return elements

    def _create_fireworks_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create fireworks animation elements."""
        
        elements = []
        colors = self.color_schemes["rainbow"]
        
        # Create multiple firework bursts
        num_bursts = max(1, count // 20)
        
        for burst in range(num_bursts):
            # Burst center
            center_x = random.uniform(-0.5, 0.5)
            center_y = random.uniform(0.2, 0.8)
            center_z = 0
            
            # Particles per burst
            particles_per_burst = count // num_bursts
            
            for i in range(particles_per_burst):
                # Radial explosion pattern
                angle = (2 * math.pi * i) / particles_per_burst
                speed = random.uniform(1.0, 3.0)
                
                vel_x = math.cos(angle) * speed
                vel_y = math.sin(angle) * speed + random.uniform(0.5, 1.0)
                vel_z = random.uniform(-0.5, 0.5)
                
                element = AnimationElement(
                    id=str(uuid.uuid4()),
                    element_type="firework_particle",
                    position={"x": center_x, "y": center_y, "z": center_z},
                    velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                    rotation={"x": 0, "y": 0, "z": 0},
                    scale=random.uniform(0.01, 0.03),
                    color=random.choice(colors),
                    opacity=1.0,
                    lifespan=random.uniform(2.0, 4.0),
                    physics_properties={
                        "affected_by_gravity": True,
                        "fade_rate": -0.2,
                        "scale_rate": -0.01  # Shrink over time
                    },
                    texture="spark",
                    glow_effect=True
                )
                
                elements.append(element)
        
        return elements

    def _create_sparkle_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create sparkle animation elements."""
        
        elements = []
        colors = self.color_schemes["gold"]
        
        for i in range(count):
            # Random position around screen
            pos_x = random.uniform(-1.2, 1.2)
            pos_y = random.uniform(-1.0, 1.0)
            pos_z = random.uniform(-0.2, 0.2)
            
            # Gentle floating motion
            vel_x = random.uniform(-0.2, 0.2)
            vel_y = random.uniform(-0.1, 0.3)
            vel_z = 0
            
            element = AnimationElement(
                id=str(uuid.uuid4()),
                element_type="sparkle",
                position={"x": pos_x, "y": pos_y, "z": pos_z},
                velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                rotation={"x": 0, "y": 0, "z": 0},
                scale=random.uniform(0.01, 0.02),
                color=random.choice(colors),
                opacity=random.uniform(0.7, 1.0),
                lifespan=random.uniform(1.5, 3.0),
                physics_properties={
                    "affected_by_gravity": False,
                    "rotation_speed": random.uniform(90, 360),
                    "fade_rate": 0.0,
                    "scale_rate": random.uniform(-0.005, 0.005)  # Gentle pulsing
                },
                texture="star",
                glow_effect=True
            )
            
            elements.append(element)
        
        return elements

    def _create_trophy_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create trophy animation elements."""
        
        elements = []
        
        # Main trophy
        trophy = AnimationElement(
            id=str(uuid.uuid4()),
            element_type="trophy",
            position={"x": 0, "y": -1.0, "z": 0},
            velocity={"x": 0, "y": 1.0, "z": 0},
            rotation={"x": 0, "y": 0, "z": 0},
            scale=0.1,
            color="#FFD700",
            opacity=1.0,
            lifespan=4.0,
            physics_properties={
                "affected_by_gravity": False,
                "rotation_speed": 90,
                "scale_rate": 0.05,  # Grow as it rises
                "fade_rate": 0.0
            },
            texture="trophy",
            glow_effect=True
        )
        elements.append(trophy)
        
        # Add sparkles around trophy
        remaining_count = count - 1
        sparkle_elements = self._create_sparkle_elements(remaining_count, intensity)
        elements.extend(sparkle_elements)
        
        return elements

    def _create_star_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create star shower elements."""
        
        elements = []
        colors = self.color_schemes["achievement"]
        
        for i in range(count):
            # Start from top, fall down
            start_x = random.uniform(-1.5, 1.5)
            start_y = random.uniform(1.2, 2.0)
            start_z = random.uniform(-0.3, 0.3)
            
            # Downward velocity with slight horizontal drift
            vel_x = random.uniform(-0.3, 0.3)
            vel_y = random.uniform(-0.5, -1.5)
            vel_z = 0
            
            element = AnimationElement(
                id=str(uuid.uuid4()),
                element_type="star",
                position={"x": start_x, "y": start_y, "z": start_z},
                velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                rotation={"x": 0, "y": 0, "z": 0},
                scale=random.uniform(0.02, 0.04),
                color=random.choice(colors),
                opacity=1.0,
                lifespan=random.uniform(3.0, 5.0),
                physics_properties={
                    "affected_by_gravity": False,  # Controlled falling
                    "rotation_speed": random.uniform(180, 360),
                    "fade_rate": -0.05
                },
                texture="star",
                glow_effect=True
            )
            
            elements.append(element)
        
        return elements

    def _create_rainbow_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create rainbow wave elements."""
        
        elements = []
        rainbow_colors = self.color_schemes["rainbow"]
        
        # Create wave pattern
        wave_amplitude = 0.3
        wave_frequency = 2.0
        
        for i in range(count):
            # Distribute across screen width
            progress = i / count
            pos_x = -1.5 + progress * 3.0  # -1.5 to 1.5
            
            # Wave height
            pos_y = wave_amplitude * math.sin(wave_frequency * progress * 2 * math.pi)
            pos_z = 0
            
            # Color based on position in rainbow
            color_index = int(progress * len(rainbow_colors))
            color = rainbow_colors[min(color_index, len(rainbow_colors) - 1)]
            
            # Horizontal movement
            vel_x = random.uniform(0.5, 1.0)
            vel_y = random.uniform(-0.1, 0.1)
            vel_z = 0
            
            element = AnimationElement(
                id=str(uuid.uuid4()),
                element_type="rainbow_particle",
                position={"x": pos_x, "y": pos_y, "z": pos_z},
                velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                rotation={"x": 0, "y": 0, "z": 0},
                scale=random.uniform(0.02, 0.04),
                color=color,
                opacity=0.8,
                lifespan=random.uniform(2.0, 4.0),
                physics_properties={
                    "affected_by_gravity": False,
                    "rotation_speed": 0,
                    "fade_rate": -0.1
                },
                texture="circle",
                glow_effect=True
            )
            
            elements.append(element)
        
        return elements

    def _create_balloon_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create floating balloon elements."""
        
        elements = []
        balloon_colors = ["#FF69B4", "#FF1493", "#00CED1", "#32CD32", "#FFD700"]
        
        for i in range(min(count, 10)):  # Limit balloons
            # Start from bottom
            start_x = random.uniform(-0.8, 0.8)
            start_y = -1.2
            start_z = random.uniform(-0.2, 0.2)
            
            # Float upward
            vel_x = random.uniform(-0.1, 0.1)
            vel_y = random.uniform(0.3, 0.6)
            vel_z = 0
            
            element = AnimationElement(
                id=str(uuid.uuid4()),
                element_type="balloon",
                position={"x": start_x, "y": start_y, "z": start_z},
                velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                rotation={"x": 0, "y": 0, "z": 0},
                scale=random.uniform(0.05, 0.08),
                color=random.choice(balloon_colors),
                opacity=1.0,
                lifespan=random.uniform(4.0, 6.0),
                physics_properties={
                    "affected_by_gravity": False,  # Balloons float
                    "rotation_speed": random.uniform(-30, 30),
                    "fade_rate": 0.0
                },
                texture="balloon",
                glow_effect=False
            )
            
            elements.append(element)
        
        return elements

    def _create_particle_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create particle explosion elements."""
        
        elements = []
        colors = self.color_schemes["celebration"]
        
        # Central explosion point
        center = {"x": 0, "y": 0, "z": 0}
        
        for i in range(count):
            # Random direction for explosion
            angle_xy = random.uniform(0, 2 * math.pi)
            angle_z = random.uniform(-math.pi/4, math.pi/4)
            
            speed = random.uniform(2.0, 4.0)
            vel_x = speed * math.cos(angle_xy) * math.cos(angle_z)
            vel_y = speed * math.sin(angle_xy) * math.cos(angle_z)
            vel_z = speed * math.sin(angle_z)
            
            element = AnimationElement(
                id=str(uuid.uuid4()),
                element_type="particle",
                position=center.copy(),
                velocity={"x": vel_x, "y": vel_y, "z": vel_z},
                rotation={"x": 0, "y": 0, "z": 0},
                scale=random.uniform(0.01, 0.03),
                color=random.choice(colors),
                opacity=1.0,
                lifespan=random.uniform(1.5, 3.0),
                physics_properties={
                    "affected_by_gravity": True,
                    "rotation_speed": random.uniform(360, 720),
                    "fade_rate": -0.3,
                    "scale_rate": -0.01
                },
                texture="particle",
                glow_effect=True
            )
            
            elements.append(element)
        
        return elements

    def _create_generic_elements(self, count: int, intensity: IntensityLevel) -> List[AnimationElement]:
        """Create generic celebration elements."""
        # Default to sparkles
        return self._create_sparkle_elements(count, intensity)

    def _select_sound_effects(self, celebration_type: CelebrationType, 
                            intensity: IntensityLevel,
                            user_profile: UserCelebrationProfile) -> List[str]:
        """Select appropriate sound effects."""
        
        if user_profile and not user_profile.sound_preferences.get("enabled", True):
            return []
        
        base_sounds = self.sound_libraries.get(celebration_type, ["chime"])
        
        intensity_multipliers = {
            IntensityLevel.SUBTLE: 1,
            IntensityLevel.MODERATE: 1,
            IntensityLevel.ENTHUSIASTIC: 2,
            IntensityLevel.SPECTACULAR: 3
        }
        
        num_sounds = intensity_multipliers.get(intensity, 1)
        return base_sounds[:num_sounds]

    def _create_screen_effects(self, style: AnimationStyle, 
                             intensity: IntensityLevel,
                             user_profile: UserCelebrationProfile) -> List[Dict[str, Any]]:
        """Create screen-wide visual effects."""
        
        effects = []
        
        # Disable flashing effects if user has accessibility needs
        if user_profile and user_profile.disable_flashing:
            return effects
        
        if intensity in [IntensityLevel.ENTHUSIASTIC, IntensityLevel.SPECTACULAR]:
            # Screen flash effect
            effects.append({
                "type": "flash",
                "color": "#FFFFFF",
                "opacity": 0.3,
                "duration": 0.2,
                "fade_out": True
            })
            
            # Screen border glow
            effects.append({
                "type": "border_glow", 
                "color": "#FFD700",
                "thickness": 10,
                "duration": 1.0,
                "pulse": True
            })
        
        if style == AnimationStyle.RAINBOW_WAVE:
            # Rainbow gradient overlay
            effects.append({
                "type": "gradient_overlay",
                "colors": self.color_schemes["rainbow"],
                "direction": "horizontal",
                "opacity": 0.2,
                "duration": 2.0,
                "animation": "wave"
            })
        
        return effects

    def _create_camera_effects(self, style: AnimationStyle,
                             intensity: IntensityLevel, 
                             user_profile: UserCelebrationProfile) -> List[Dict[str, Any]]:
        """Create camera movement effects."""
        
        effects = []
        
        # Skip camera effects if user has motion sensitivity
        if user_profile and (user_profile.reduced_motion or user_profile.motion_sensitivity > 7):
            return effects
        
        if intensity == IntensityLevel.SPECTACULAR:
            # Gentle zoom effect
            effects.append({
                "type": "zoom",
                "start_scale": 1.0,
                "end_scale": 1.05,
                "duration": 0.5,
                "easing": "ease_out",
                "return": True
            })
            
            # Subtle shake for impact
            effects.append({
                "type": "shake",
                "intensity": 0.02,
                "duration": 0.3,
                "frequency": 10
            })
        
        return effects

    def _create_haptic_feedback(self, intensity: IntensityLevel,
                              user_profile: UserCelebrationProfile) -> Optional[Dict[str, Any]]:
        """Create haptic feedback pattern."""
        
        if not user_profile or not user_profile.sound_preferences.get("haptic_enabled", False):
            return None
        
        patterns = {
            IntensityLevel.SUBTLE: {"pattern": "light_tap", "duration": 0.1},
            IntensityLevel.MODERATE: {"pattern": "medium_buzz", "duration": 0.3},
            IntensityLevel.ENTHUSIASTIC: {"pattern": "strong_pulse", "duration": 0.5},
            IntensityLevel.SPECTACULAR: {"pattern": "celebration_sequence", "duration": 1.0}
        }
        
        return patterns.get(intensity)

    def _calculate_duration(self, intensity: IntensityLevel, element_count: int) -> float:
        """Calculate total animation duration."""
        
        base_durations = {
            IntensityLevel.SUBTLE: 2.0,
            IntensityLevel.MODERATE: 3.0,
            IntensityLevel.ENTHUSIASTIC: 4.0,
            IntensityLevel.SPECTACULAR: 5.0
        }
        
        base_duration = base_durations.get(intensity, 3.0)
        
        # Adjust for element count
        if element_count > 50:
            base_duration += 1.0
        elif element_count > 100:
            base_duration += 2.0
        
        return base_duration

    def _generate_trigger_conditions(self, celebration_type: CelebrationType) -> List[str]:
        """Generate conditions that should trigger this celebration."""
        
        conditions = {
            CelebrationType.STEP_COMPLETE: ["step_completed", "validation_passed"],
            CelebrationType.MILESTONE_REACHED: ["milestone_achieved", "progress_threshold"],
            CelebrationType.PERFECT_EXECUTION: ["no_mistakes", "first_try_success"],
            CelebrationType.BREAKTHROUGH_MOMENT: ["concept_mastered", "skill_breakthrough"],
            CelebrationType.TUTORIAL_COMPLETE: ["tutorial_finished", "final_step_complete"],
            CelebrationType.STREAK_ACHIEVEMENT: ["consecutive_successes", "streak_milestone"],
            CelebrationType.IMPROVEMENT_SHOWN: ["performance_improved", "time_reduced"],
            CelebrationType.CHALLENGE_OVERCOME: ["difficult_task_completed", "retry_success"]
        }
        
        return conditions.get(celebration_type, ["generic_success"])

    def _create_personalization_data(self, user_profile: UserCelebrationProfile,
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Create personalization data for the animation."""
        
        data = {}
        
        if user_profile:
            data["user_preferences"] = {
                "preferred_styles": [style.value for style in user_profile.preferred_styles],
                "intensity_preference": user_profile.intensity_preference.value,
                "accessibility_mode": user_profile.reduced_motion,
                "cultural_preferences": user_profile.cultural_preferences
            }
        
        if context:
            data["context"] = {
                "achievement_level": context.get("achievement_level", "normal"),
                "user_skill_level": context.get("user_skill_level", "beginner"),
                "tutorial_difficulty": context.get("tutorial_difficulty", "medium"),
                "time_of_day": context.get("time_of_day", "unknown")
            }
        
        return data

class CelebrationSystem:
    def __init__(self, db_path: str = "celebrations.db"):
        self.db_path = db_path
        self.factory = CelebrationFactory()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS celebration_animations (
            id TEXT PRIMARY KEY,
            celebration_type TEXT,
            animation_style TEXT,
            intensity_level TEXT,
            duration REAL,
            elements TEXT,
            sound_effects TEXT,
            screen_effects TEXT,
            camera_effects TEXT,
            haptic_feedback TEXT,
            trigger_conditions TEXT,
            personalization_data TEXT,
            created_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_celebration_profiles (
            user_id TEXT PRIMARY KEY,
            preferred_styles TEXT,
            intensity_preference TEXT,
            accessibility_settings TEXT,
            motion_sensitivity INTEGER,
            sound_preferences TEXT,
            celebration_frequency TEXT,
            cultural_preferences TEXT,
            disable_flashing BOOLEAN,
            reduced_motion BOOLEAN,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS celebration_history (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            animation_id TEXT,
            triggered_at TEXT,
            context TEXT,
            user_reaction TEXT,
            effectiveness_rating REAL
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_user_profile(self, user_id: str, 
                                preferences: Dict[str, Any] = None) -> UserCelebrationProfile:
        """Create user celebration profile."""
        
        if preferences is None:
            preferences = {}
        
        # Convert style preferences
        preferred_styles = []
        if "preferred_styles" in preferences:
            for style_name in preferences["preferred_styles"]:
                try:
                    preferred_styles.append(AnimationStyle(style_name))
                except ValueError:
                    pass  # Skip invalid styles
        
        profile = UserCelebrationProfile(
            user_id=user_id,
            preferred_styles=preferred_styles or [AnimationStyle.SPARKLES],
            intensity_preference=IntensityLevel(preferences.get("intensity", "moderate")),
            accessibility_settings=preferences.get("accessibility_settings", {}),
            motion_sensitivity=preferences.get("motion_sensitivity", 5),
            sound_preferences=preferences.get("sound_preferences", {"enabled": True}),
            celebration_frequency=preferences.get("frequency", "moderate"),
            cultural_preferences=preferences.get("cultural_preferences", []),
            disable_flashing=preferences.get("disable_flashing", False),
            reduced_motion=preferences.get("reduced_motion", False)
        )
        
        await self._save_user_profile(profile)
        return profile

    async def _save_user_profile(self, profile: UserCelebrationProfile):
        """Save user profile to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_celebration_profiles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.user_id,
            json.dumps([style.value for style in profile.preferred_styles]),
            profile.intensity_preference.value,
            json.dumps(profile.accessibility_settings),
            profile.motion_sensitivity,
            json.dumps(profile.sound_preferences),
            profile.celebration_frequency,
            json.dumps(profile.cultural_preferences),
            profile.disable_flashing,
            profile.reduced_motion,
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()

    async def trigger_celebration(self, celebration_type: str, user_id: str,
                                context: Dict[str, Any] = None,
                                intensity: str = None) -> CelebrationAnimation:
        """Trigger a celebration animation."""
        
        # Get user profile
        user_profile = await self.get_user_profile(user_id)
        
        # Convert string parameters to enums
        celebration_enum = CelebrationType(celebration_type)
        intensity_enum = IntensityLevel(intensity) if intensity else IntensityLevel.MODERATE
        
        # Create animation
        animation = self.factory.create_celebration(
            celebration_enum, intensity_enum, user_profile, context
        )
        
        # Save animation
        await self._save_animation(animation)
        
        # Record in history
        await self._record_celebration_history(user_id, animation.id, context)
        
        return animation

    async def _save_animation(self, animation: CelebrationAnimation):
        """Save animation to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO celebration_animations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            animation.id, animation.celebration_type.value, animation.animation_style.value,
            animation.intensity_level.value, animation.duration,
            json.dumps([asdict(elem) for elem in animation.elements]),
            json.dumps(animation.sound_effects),
            json.dumps(animation.screen_effects),
            json.dumps(animation.camera_effects),
            json.dumps(animation.haptic_feedback) if animation.haptic_feedback else None,
            json.dumps(animation.trigger_conditions),
            json.dumps(animation.personalization_data),
            animation.created_at
        ))
        
        conn.commit()
        conn.close()

    async def get_user_profile(self, user_id: str) -> Optional[UserCelebrationProfile]:
        """Get user celebration profile."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM user_celebration_profiles WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct profile
        preferred_styles = [AnimationStyle(style) for style in json.loads(row[1])]
        
        return UserCelebrationProfile(
            user_id=row[0], preferred_styles=preferred_styles,
            intensity_preference=IntensityLevel(row[2]),
            accessibility_settings=json.loads(row[3]),
            motion_sensitivity=row[4], sound_preferences=json.loads(row[5]),
            celebration_frequency=row[6], cultural_preferences=json.loads(row[7]),
            disable_flashing=row[8], reduced_motion=row[9]
        )

    async def _record_celebration_history(self, user_id: str, animation_id: str,
                                        context: Dict[str, Any]):
        """Record celebration in user history."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO celebration_history (id, user_id, animation_id, triggered_at, context)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), user_id, animation_id, 
            datetime.now().isoformat(), json.dumps(context or {})
        ))
        
        conn.commit()
        conn.close()

    async def get_celebration_stats(self, user_id: str) -> Dict[str, Any]:
        """Get celebration statistics for user."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT COUNT(*) as total_celebrations,
               AVG(effectiveness_rating) as avg_rating
        FROM celebration_history 
        WHERE user_id = ? AND effectiveness_rating IS NOT NULL
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return {
            "total_celebrations": result[0] if result else 0,
            "average_effectiveness": result[1] if result and result[1] else 0.0,
            "user_engagement": "high" if result and result[0] > 10 else "moderate"
        }

if __name__ == "__main__":
    async def main():
        celebration_system = CelebrationSystem()
        
        # Create user profile
        user_profile = await celebration_system.create_user_profile(
            "user123",
            {
                "preferred_styles": ["sparkles", "fireworks"],
                "intensity": "enthusiastic",
                "motion_sensitivity": 3,
                "sound_preferences": {"enabled": True, "haptic_enabled": True},
                "reduced_motion": False
            }
        )
        
        print(f"Created celebration profile for: {user_profile.user_id}")
        print(f"Preferred styles: {[style.value for style in user_profile.preferred_styles]}")
        print(f"Intensity preference: {user_profile.intensity_preference.value}")
        
        # Trigger different celebrations
        celebrations = [
            ("step_complete", "moderate"),
            ("perfect_execution", "enthusiastic"),
            ("tutorial_complete", "spectacular")
        ]
        
        for celebration_type, intensity in celebrations:
            animation = await celebration_system.trigger_celebration(
                celebration_type, "user123", 
                {"achievement_level": "high", "user_skill_level": "intermediate"},
                intensity
            )
            
            print(f"\nTriggered {celebration_type} celebration:")
            print(f"  Animation: {animation.animation_style.value}")
            print(f"  Duration: {animation.duration} seconds")
            print(f"  Elements: {len(animation.elements)}")
            print(f"  Sound effects: {animation.sound_effects}")
        
        # Get stats
        stats = await celebration_system.get_celebration_stats("user123")
        print(f"\nCelebration stats:")
        print(f"  Total celebrations: {stats['total_celebrations']}")
        print(f"  User engagement: {stats['user_engagement']}")
    
    asyncio.run(main())