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

class ARElementType(Enum):
    TEXT_OVERLAY = "text_overlay"
    ARROW_POINTER = "arrow_pointer"
    HIGHLIGHT_BOX = "highlight_box"
    ANIMATED_GUIDE = "animated_guide"
    STEP_COUNTER = "step_counter"
    MEASUREMENT_TOOL = "measurement_tool"
    VIRTUAL_HAND = "virtual_hand"
    PROGRESS_BAR = "progress_bar"
    WARNING_SIGN = "warning_sign"
    SUCCESS_CHECKMARK = "success_checkmark"

class AnchorType(Enum):
    WORLD_SPACE = "world_space"        # Fixed in 3D world
    SCREEN_SPACE = "screen_space"      # Fixed to screen position
    OBJECT_RELATIVE = "object_relative" # Attached to detected object
    USER_RELATIVE = "user_relative"    # Relative to user position
    SURFACE_PLANE = "surface_plane"    # Anchored to detected surface

class InteractionType(Enum):
    TAP = "tap"
    PINCH = "pinch"
    SWIPE = "swipe"
    VOICE_COMMAND = "voice_command"
    GAZE = "gaze"
    HAND_GESTURE = "hand_gesture"
    PROXIMITY = "proximity"

@dataclass
class ARPosition:
    x: float
    y: float
    z: float
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    scale: float = 1.0

@dataclass
class ARAnimation:
    id: str
    animation_type: str  # fade_in, slide_in, pulse, bounce, etc.
    duration: float      # seconds
    loop: bool
    easing: str         # linear, ease_in, ease_out, etc.
    delay: float        # seconds before starting
    parameters: Dict[str, Any]  # Animation-specific parameters

@dataclass
class ARElement:
    id: str
    element_type: ARElementType
    title: str
    content: str
    position: ARPosition
    anchor_type: AnchorType
    anchor_target: Optional[str]  # Object ID or surface ID for anchoring
    visibility_conditions: List[str]  # When this element should be visible
    interaction_types: List[InteractionType]
    style_properties: Dict[str, Any]  # Color, size, font, etc.
    animations: List[ARAnimation]
    audio_cue: Optional[str]
    duration: Optional[float]  # How long to display (None = until dismissed)
    priority: int  # Higher priority elements shown first
    created_at: str

@dataclass
class ObjectDetectionTarget:
    id: str
    name: str
    description: str
    detection_model: str  # Model used for detection
    confidence_threshold: float
    bounding_box_color: str
    label_text: str
    tracking_enabled: bool
    occlusion_handling: bool

@dataclass
class SurfacePlane:
    id: str
    plane_type: str  # horizontal, vertical, angled
    normal_vector: Tuple[float, float, float]
    center_point: ARPosition
    dimensions: Tuple[float, float]  # width, height
    confidence: float
    is_stable: bool

@dataclass
class ARScene:
    id: str
    tutorial_step_id: str
    scene_title: str
    description: str
    elements: List[ARElement]
    detection_targets: List[ObjectDetectionTarget]
    required_surfaces: List[str]  # Types of surfaces needed
    lighting_requirements: Dict[str, Any]
    camera_requirements: Dict[str, Any]
    user_position_requirements: Dict[str, Any]
    estimated_setup_time: int  # seconds
    difficulty_level: str
    created_at: str
    updated_at: str

class ARElementFactory:
    def __init__(self):
        self.default_styles = {
            ARElementType.TEXT_OVERLAY: {
                "font_size": 16,
                "font_color": "#FFFFFF",
                "background_color": "#000000AA",
                "padding": 10,
                "border_radius": 8,
                "shadow": True
            },
            ARElementType.ARROW_POINTER: {
                "color": "#FF6600",
                "thickness": 4,
                "head_size": 20,
                "animation": "pulse"
            },
            ARElementType.HIGHLIGHT_BOX: {
                "border_color": "#00FF00",
                "border_thickness": 3,
                "fill_color": "#00FF0030",
                "corner_radius": 5
            },
            ARElementType.STEP_COUNTER: {
                "background_color": "#0080FF",
                "text_color": "#FFFFFF",
                "size": 40,
                "position": "top_right"
            }
        }
        
        self.animation_presets = {
            "attention_grabber": {
                "animation_type": "pulse",
                "duration": 1.0,
                "loop": True,
                "easing": "ease_in_out",
                "parameters": {"scale_factor": 1.2}
            },
            "smooth_entry": {
                "animation_type": "fade_in",
                "duration": 0.5,
                "loop": False,
                "easing": "ease_out",
                "parameters": {"start_alpha": 0.0}
            },
            "gentle_bounce": {
                "animation_type": "bounce",
                "duration": 0.8,
                "loop": False,
                "easing": "bounce_out",
                "parameters": {"bounce_height": 10}
            }
        }

    def create_text_overlay(self, text: str, position: ARPosition,
                          anchor_type: AnchorType = AnchorType.SCREEN_SPACE,
                          style_overrides: Dict[str, Any] = None) -> ARElement:
        """Create a text overlay AR element."""
        
        element_id = str(uuid.uuid4())
        
        # Merge default styles with overrides
        style = self.default_styles[ARElementType.TEXT_OVERLAY].copy()
        if style_overrides:
            style.update(style_overrides)
        
        # Add smooth entry animation
        animations = [
            ARAnimation(
                id=str(uuid.uuid4()),
                **self.animation_presets["smooth_entry"]
            )
        ]
        
        return ARElement(
            id=element_id,
            element_type=ARElementType.TEXT_OVERLAY,
            title="Instruction Text",
            content=text,
            position=position,
            anchor_type=anchor_type,
            anchor_target=None,
            visibility_conditions=["always"],
            interaction_types=[InteractionType.TAP],
            style_properties=style,
            animations=animations,
            audio_cue=None,
            duration=None,
            priority=5,
            created_at=datetime.now().isoformat()
        )

    def create_arrow_pointer(self, start_pos: ARPosition, end_pos: ARPosition,
                           message: str = "", animated: bool = True) -> ARElement:
        """Create an arrow pointer AR element."""
        
        element_id = str(uuid.uuid4())
        
        style = self.default_styles[ARElementType.ARROW_POINTER].copy()
        
        animations = []
        if animated:
            animations.append(ARAnimation(
                id=str(uuid.uuid4()),
                **self.animation_presets["attention_grabber"]
            ))
        
        # Calculate arrow direction
        direction = {
            "start_x": start_pos.x,
            "start_y": start_pos.y,
            "start_z": start_pos.z,
            "end_x": end_pos.x,
            "end_y": end_pos.y,
            "end_z": end_pos.z
        }
        style.update(direction)
        
        return ARElement(
            id=element_id,
            element_type=ARElementType.ARROW_POINTER,
            title="Direction Pointer",
            content=message,
            position=start_pos,
            anchor_type=AnchorType.WORLD_SPACE,
            anchor_target=None,
            visibility_conditions=["always"],
            interaction_types=[InteractionType.TAP],
            style_properties=style,
            animations=animations,
            audio_cue="pointer_sound",
            duration=None,
            priority=8,
            created_at=datetime.now().isoformat()
        )

    def create_highlight_box(self, target_position: ARPosition,
                           dimensions: Tuple[float, float, float],
                           message: str = "Focus here") -> ARElement:
        """Create a highlight box AR element."""
        
        element_id = str(uuid.uuid4())
        
        style = self.default_styles[ARElementType.HIGHLIGHT_BOX].copy()
        style.update({
            "width": dimensions[0],
            "height": dimensions[1],
            "depth": dimensions[2]
        })
        
        animations = [
            ARAnimation(
                id=str(uuid.uuid4()),
                animation_type="glow_pulse",
                duration=2.0,
                loop=True,
                easing="ease_in_out",
                delay=0.0,
                parameters={"glow_intensity": 0.8}
            )
        ]
        
        return ARElement(
            id=element_id,
            element_type=ARElementType.HIGHLIGHT_BOX,
            title="Focus Area",
            content=message,
            position=target_position,
            anchor_type=AnchorType.OBJECT_RELATIVE,
            anchor_target=None,
            visibility_conditions=["object_detected"],
            interaction_types=[InteractionType.TAP, InteractionType.GAZE],
            style_properties=style,
            animations=animations,
            audio_cue=None,
            duration=None,
            priority=7,
            created_at=datetime.now().isoformat()
        )

    def create_virtual_hand(self, gesture_type: str, position: ARPosition,
                          instruction: str) -> ARElement:
        """Create a virtual hand demonstration AR element."""
        
        element_id = str(uuid.uuid4())
        
        style = {
            "hand_model": "realistic_hand_v2",
            "skin_tone": "neutral",
            "opacity": 0.8,
            "gesture": gesture_type,
            "scale": 1.2
        }
        
        # Animation based on gesture type
        if gesture_type == "tap":
            animation_params = {"tap_count": 1, "tap_interval": 0.5}
        elif gesture_type == "swipe":
            animation_params = {"swipe_direction": "right", "swipe_distance": 50}
        elif gesture_type == "pinch":
            animation_params = {"pinch_scale": 0.5, "release_delay": 1.0}
        else:
            animation_params = {}
        
        animations = [
            ARAnimation(
                id=str(uuid.uuid4()),
                animation_type=f"hand_{gesture_type}",
                duration=1.5,
                loop=True,
                easing="natural",
                delay=0.5,
                parameters=animation_params
            )
        ]
        
        return ARElement(
            id=element_id,
            element_type=ARElementType.VIRTUAL_HAND,
            title="Gesture Guide",
            content=instruction,
            position=position,
            anchor_type=AnchorType.WORLD_SPACE,
            anchor_target=None,
            visibility_conditions=["gesture_needed"],
            interaction_types=[InteractionType.HAND_GESTURE],
            style_properties=style,
            animations=animations,
            audio_cue="gesture_prompt",
            duration=10.0,  # Show for 10 seconds max
            priority=9,
            created_at=datetime.now().isoformat()
        )

    def create_progress_indicator(self, current_step: int, total_steps: int,
                                position: ARPosition) -> ARElement:
        """Create a progress indicator AR element."""
        
        element_id = str(uuid.uuid4())
        
        style = {
            "progress_type": "circular",
            "background_color": "#FFFFFF30",
            "progress_color": "#00AA00",
            "text_color": "#FFFFFF",
            "size": 60,
            "thickness": 8,
            "show_percentage": True,
            "show_step_numbers": True
        }
        
        progress_percentage = (current_step / total_steps) * 100
        content = f"Step {current_step} of {total_steps} ({progress_percentage:.0f}%)"
        
        animations = [
            ARAnimation(
                id=str(uuid.uuid4()),
                animation_type="progress_fill",
                duration=0.8,
                loop=False,
                easing="ease_out",
                delay=0.0,
                parameters={"target_progress": progress_percentage}
            )
        ]
        
        return ARElement(
            id=element_id,
            element_type=ARElementType.PROGRESS_BAR,
            title="Tutorial Progress",
            content=content,
            position=position,
            anchor_type=AnchorType.SCREEN_SPACE,
            anchor_target=None,
            visibility_conditions=["always"],
            interaction_types=[InteractionType.TAP],
            style_properties=style,
            animations=animations,
            audio_cue=None,
            duration=None,
            priority=3,
            created_at=datetime.now().isoformat()
        )

    def create_warning_indicator(self, warning_text: str, position: ARPosition,
                               severity: str = "medium") -> ARElement:
        """Create a warning indicator AR element."""
        
        element_id = str(uuid.uuid4())
        
        severity_colors = {
            "low": "#FFAA00",
            "medium": "#FF6600",
            "high": "#FF0000",
            "critical": "#AA0000"
        }
        
        style = {
            "icon": "warning_triangle",
            "color": severity_colors.get(severity, "#FF6600"),
            "background_color": "#FFFFFF",
            "border_color": severity_colors.get(severity, "#FF6600"),
            "border_thickness": 3,
            "icon_size": 32,
            "padding": 12,
            "shadow": True
        }
        
        # More urgent animation for higher severity
        if severity in ["high", "critical"]:
            animation_type = "urgent_flash"
            duration = 0.5
            loop_count = 6
        else:
            animation_type = "gentle_pulse"
            duration = 1.5
            loop_count = 3
        
        animations = [
            ARAnimation(
                id=str(uuid.uuid4()),
                animation_type=animation_type,
                duration=duration,
                loop=True,
                easing="ease_in_out",
                delay=0.0,
                parameters={"loop_count": loop_count}
            )
        ]
        
        return ARElement(
            id=element_id,
            element_type=ARElementType.WARNING_SIGN,
            title="Warning",
            content=warning_text,
            position=position,
            anchor_type=AnchorType.WORLD_SPACE,
            anchor_target=None,
            visibility_conditions=["warning_needed"],
            interaction_types=[InteractionType.TAP, InteractionType.VOICE_COMMAND],
            style_properties=style,
            animations=animations,
            audio_cue="warning_beep",
            duration=15.0,
            priority=10,
            created_at=datetime.now().isoformat()
        )

class ARSceneBuilder:
    def __init__(self):
        self.element_factory = ARElementFactory()
        self.spatial_analyzer = SpatialAnalyzer()

    def create_tutorial_scene(self, tutorial_step: Dict[str, Any],
                            environment_context: Dict[str, Any]) -> ARScene:
        """Create an AR scene for a tutorial step."""
        
        scene_id = str(uuid.uuid4())
        step_id = tutorial_step.get("id", "unknown_step")
        
        # Analyze the tutorial step to determine AR elements needed
        elements = self._generate_ar_elements(tutorial_step, environment_context)
        
        # Generate object detection targets
        detection_targets = self._generate_detection_targets(tutorial_step)
        
        # Determine surface requirements
        surface_requirements = self._analyze_surface_requirements(tutorial_step)
        
        # Set up environmental requirements
        lighting_reqs = self._determine_lighting_requirements(tutorial_step)
        camera_reqs = self._determine_camera_requirements(tutorial_step)
        position_reqs = self._determine_position_requirements(tutorial_step)
        
        return ARScene(
            id=scene_id,
            tutorial_step_id=step_id,
            scene_title=tutorial_step.get("title", "Tutorial Step"),
            description=tutorial_step.get("description", ""),
            elements=elements,
            detection_targets=detection_targets,
            required_surfaces=surface_requirements,
            lighting_requirements=lighting_reqs,
            camera_requirements=camera_reqs,
            user_position_requirements=position_reqs,
            estimated_setup_time=self._estimate_setup_time(elements, detection_targets),
            difficulty_level=tutorial_step.get("difficulty", "medium"),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

    def _generate_ar_elements(self, tutorial_step: Dict[str, Any],
                            environment_context: Dict[str, Any]) -> List[ARElement]:
        """Generate AR elements based on tutorial step content."""
        
        elements = []
        instructions = tutorial_step.get("instructions", [])
        step_type = tutorial_step.get("step_type", "action")
        
        # Add progress indicator
        current_step = environment_context.get("current_step", 1)
        total_steps = environment_context.get("total_steps", 10)
        
        progress_position = ARPosition(x=0.8, y=0.9, z=0, scale=0.8)
        progress_element = self.element_factory.create_progress_indicator(
            current_step, total_steps, progress_position
        )
        elements.append(progress_element)
        
        # Process each instruction
        for i, instruction in enumerate(instructions):
            # Main instruction text
            text_position = ARPosition(
                x=0.5, y=0.7 - i * 0.1, z=0, scale=1.0
            )
            
            text_element = self.element_factory.create_text_overlay(
                instruction, text_position, AnchorType.SCREEN_SPACE
            )
            elements.append(text_element)
            
            # Add specific AR elements based on instruction content
            elements.extend(self._analyze_instruction_for_ar_elements(
                instruction, i, environment_context
            ))
        
        # Add safety warnings if needed
        safety_warnings = tutorial_step.get("safety_warnings", [])
        for warning in safety_warnings:
            warning_position = ARPosition(x=0.1, y=0.1, z=0, scale=1.0)
            warning_element = self.element_factory.create_warning_indicator(
                warning, warning_position, "high"
            )
            elements.append(warning_element)
        
        # Add step-specific elements based on type
        if step_type == "measurement":
            elements.extend(self._add_measurement_elements())
        elif step_type == "assembly":
            elements.extend(self._add_assembly_elements())
        elif step_type == "verification":
            elements.extend(self._add_verification_elements())
        
        return elements

    def _analyze_instruction_for_ar_elements(self, instruction: str, index: int,
                                           context: Dict[str, Any]) -> List[ARElement]:
        """Analyze individual instruction to determine needed AR elements."""
        
        elements = []
        instruction_lower = instruction.lower()
        
        # Look for pointing/directional language
        pointing_words = ["point", "select", "click", "touch", "press", "tap"]
        if any(word in instruction_lower for word in pointing_words):
            # Add arrow pointer
            start_pos = ARPosition(x=0.3, y=0.5, z=-1.0)
            end_pos = ARPosition(x=0.0, y=0.0, z=-0.5)  # Points to object
            
            arrow = self.element_factory.create_arrow_pointer(
                start_pos, end_pos, "Tap here"
            )
            elements.append(arrow)
        
        # Look for gesture instructions
        gesture_words = ["swipe", "pinch", "rotate", "drag"]
        for gesture in gesture_words:
            if gesture in instruction_lower:
                gesture_pos = ARPosition(x=0.0, y=0.0, z=-0.8)
                hand_demo = self.element_factory.create_virtual_hand(
                    gesture, gesture_pos, f"Perform {gesture} gesture"
                )
                elements.append(hand_demo)
                break
        
        # Look for highlighting needs
        highlight_words = ["this", "that", "here", "there", "highlighted", "marked"]
        if any(word in instruction_lower for word in highlight_words):
            highlight_pos = ARPosition(x=0.0, y=0.0, z=-0.6)
            highlight_box = self.element_factory.create_highlight_box(
                highlight_pos, (0.2, 0.2, 0.1), "Focus on this area"
            )
            elements.append(highlight_box)
        
        return elements

    def _add_measurement_elements(self) -> List[ARElement]:
        """Add AR elements for measurement steps."""
        
        elements = []
        
        # Virtual ruler/measurement tool
        ruler_element = ARElement(
            id=str(uuid.uuid4()),
            element_type=ARElementType.MEASUREMENT_TOOL,
            title="Virtual Ruler",
            content="Drag to measure distances",
            position=ARPosition(x=0.0, y=-0.3, z=-0.5),
            anchor_type=AnchorType.WORLD_SPACE,
            anchor_target=None,
            visibility_conditions=["measurement_mode"],
            interaction_types=[InteractionType.PINCH, InteractionType.SWIPE],
            style_properties={
                "ruler_type": "metric",
                "color": "#0080FF",
                "thickness": 2,
                "show_numbers": True,
                "precision": 1  # decimal places
            },
            animations=[],
            audio_cue="measurement_ready",
            duration=None,
            priority=6,
            created_at=datetime.now().isoformat()
        )
        
        elements.append(ruler_element)
        return elements

    def _add_assembly_elements(self) -> List[ARElement]:
        """Add AR elements for assembly steps."""
        
        elements = []
        
        # Assembly sequence animator
        sequence_element = ARElement(
            id=str(uuid.uuid4()),
            element_type=ARElementType.ANIMATED_GUIDE,
            title="Assembly Animation",
            content="Watch the assembly process",
            position=ARPosition(x=0.0, y=0.0, z=-1.0),
            anchor_type=AnchorType.OBJECT_RELATIVE,
            anchor_target="assembly_target",
            visibility_conditions=["object_detected"],
            interaction_types=[InteractionType.TAP],
            style_properties={
                "animation_speed": 1.0,
                "loop": True,
                "show_parts_labels": True,
                "highlight_current_step": True
            },
            animations=[
                ARAnimation(
                    id=str(uuid.uuid4()),
                    animation_type="assembly_sequence",
                    duration=5.0,
                    loop=True,
                    easing="linear",
                    delay=0.0,
                    parameters={"step_pause": 1.0}
                )
            ],
            audio_cue="assembly_start",
            duration=None,
            priority=8,
            created_at=datetime.now().isoformat()
        )
        
        elements.append(sequence_element)
        return elements

    def _add_verification_elements(self) -> List[ARElement]:
        """Add AR elements for verification steps."""
        
        elements = []
        
        # Success checkmark
        success_element = ARElement(
            id=str(uuid.uuid4()),
            element_type=ARElementType.SUCCESS_CHECKMARK,
            title="Verification Complete",
            content="Well done! Step completed successfully.",
            position=ARPosition(x=0.5, y=0.5, z=-0.5),
            anchor_type=AnchorType.SCREEN_SPACE,
            anchor_target=None,
            visibility_conditions=["step_completed"],
            interaction_types=[InteractionType.TAP],
            style_properties={
                "checkmark_color": "#00AA00",
                "background_color": "#FFFFFF",
                "size": 48,
                "animation_style": "bounce"
            },
            animations=[
                ARAnimation(
                    id=str(uuid.uuid4()),
                    animation_type="success_celebration",
                    duration=1.5,
                    loop=False,
                    easing="bounce_out",
                    delay=0.0,
                    parameters={"scale_peak": 1.3}
                )
            ],
            audio_cue="success_chime",
            duration=3.0,
            priority=10,
            created_at=datetime.now().isoformat()
        )
        
        elements.append(success_element)
        return elements

    def _generate_detection_targets(self, tutorial_step: Dict[str, Any]) -> List[ObjectDetectionTarget]:
        """Generate object detection targets based on tutorial requirements."""
        
        targets = []
        
        # Extract objects mentioned in instructions
        instructions = tutorial_step.get("instructions", [])
        materials = tutorial_step.get("materials_needed", [])
        tools = tutorial_step.get("tools_needed", [])
        
        # Common objects that might need detection
        detectable_objects = {
            "phone": {"model": "mobile_device_detector", "threshold": 0.8},
            "laptop": {"model": "computer_detector", "threshold": 0.85},
            "book": {"model": "book_detector", "threshold": 0.75},
            "cup": {"model": "container_detector", "threshold": 0.8},
            "hand": {"model": "hand_detector", "threshold": 0.9},
            "face": {"model": "face_detector", "threshold": 0.95},
            "table": {"model": "furniture_detector", "threshold": 0.8},
            "wall": {"model": "wall_detector", "threshold": 0.9}
        }
        
        # Check for mentioned objects
        all_text = " ".join(instructions + materials + tools).lower()
        
        for obj_name, obj_config in detectable_objects.items():
            if obj_name in all_text:
                target = ObjectDetectionTarget(
                    id=str(uuid.uuid4()),
                    name=obj_name,
                    description=f"Detect {obj_name} for AR overlay",
                    detection_model=obj_config["model"],
                    confidence_threshold=obj_config["threshold"],
                    bounding_box_color="#00FF00",
                    label_text=obj_name.title(),
                    tracking_enabled=True,
                    occlusion_handling=True
                )
                targets.append(target)
        
        return targets

    def _analyze_surface_requirements(self, tutorial_step: Dict[str, Any]) -> List[str]:
        """Analyze what surface types are needed for the tutorial."""
        
        requirements = []
        instructions = " ".join(tutorial_step.get("instructions", [])).lower()
        
        if any(word in instructions for word in ["table", "desk", "surface", "place on"]):
            requirements.append("horizontal")
        
        if any(word in instructions for word in ["wall", "board", "hang", "attach"]):
            requirements.append("vertical")
        
        if any(word in instructions for word in ["floor", "ground", "stand on"]):
            requirements.append("floor")
        
        return requirements

    def _determine_lighting_requirements(self, tutorial_step: Dict[str, Any]) -> Dict[str, Any]:
        """Determine lighting requirements for optimal AR performance."""
        
        return {
            "minimum_lux": 200,
            "maximum_lux": 1000,
            "avoid_direct_sunlight": True,
            "prefer_diffused_lighting": True,
            "color_temperature_range": [3000, 6500]  # Kelvin
        }

    def _determine_camera_requirements(self, tutorial_step: Dict[str, Any]) -> Dict[str, Any]:
        """Determine camera requirements for the AR experience."""
        
        step_type = tutorial_step.get("step_type", "action")
        
        base_requirements = {
            "resolution": "1080p",
            "frame_rate": 30,
            "autofocus": True,
            "stabilization": True
        }
        
        if step_type in ["measurement", "precision"]:
            base_requirements.update({
                "resolution": "4K",
                "macro_focus": True,
                "high_precision_tracking": True
            })
        elif step_type == "overview":
            base_requirements.update({
                "wide_angle": True,
                "panoramic_support": True
            })
        
        return base_requirements

    def _determine_position_requirements(self, tutorial_step: Dict[str, Any]) -> Dict[str, Any]:
        """Determine user positioning requirements."""
        
        return {
            "minimum_distance": 0.5,  # meters from target
            "maximum_distance": 3.0,
            "preferred_distance": 1.0,
            "viewing_angle_range": 45,  # degrees from center
            "height_flexibility": 0.5,  # meters above/below optimal
            "movement_space": 1.0  # meters radius for user movement
        }

    def _estimate_setup_time(self, elements: List[ARElement], 
                           targets: List[ObjectDetectionTarget]) -> int:
        """Estimate setup time in seconds."""
        
        base_time = 5  # Base AR initialization
        
        # Add time for object detection
        base_time += len(targets) * 3
        
        # Add time for complex elements
        complex_elements = [e for e in elements if e.element_type in [
            ARElementType.ANIMATED_GUIDE, 
            ARElementType.MEASUREMENT_TOOL,
            ARElementType.VIRTUAL_HAND
        ]]
        base_time += len(complex_elements) * 2
        
        return base_time

class SpatialAnalyzer:
    """Analyzes spatial relationships and optimizes AR element placement."""
    
    def __init__(self):
        self.collision_buffer = 0.1  # meters
        self.visibility_threshold = 0.7  # minimum visibility score

    def optimize_element_placement(self, elements: List[ARElement],
                                 user_position: ARPosition,
                                 detected_objects: List[Dict[str, Any]]) -> List[ARElement]:
        """Optimize AR element placement to avoid occlusion and collisions."""
        
        optimized_elements = []
        
        for element in elements:
            # Check for collisions with other elements
            optimal_position = self._find_optimal_position(
                element, optimized_elements, user_position, detected_objects
            )
            
            # Update element position
            element.position = optimal_position
            
            # Adjust scale based on distance from user
            distance = self._calculate_distance(element.position, user_position)
            scale_factor = self._calculate_scale_factor(distance, element.element_type)
            element.position.scale *= scale_factor
            
            optimized_elements.append(element)
        
        return optimized_elements

    def _find_optimal_position(self, element: ARElement, 
                             existing_elements: List[ARElement],
                             user_position: ARPosition,
                             detected_objects: List[Dict[str, Any]]) -> ARPosition:
        """Find optimal position for an AR element."""
        
        current_pos = element.position
        
        # If screen-space anchored, use screen coordinates
        if element.anchor_type == AnchorType.SCREEN_SPACE:
            return self._optimize_screen_space_position(element, existing_elements)
        
        # For world-space elements, check 3D positioning
        best_position = current_pos
        best_score = self._evaluate_position_score(
            current_pos, element, existing_elements, user_position, detected_objects
        )
        
        # Try alternative positions
        search_radius = 0.5  # meters
        search_points = self._generate_search_points(current_pos, search_radius)
        
        for test_pos in search_points:
            score = self._evaluate_position_score(
                test_pos, element, existing_elements, user_position, detected_objects
            )
            
            if score > best_score:
                best_score = score
                best_position = test_pos
        
        return best_position

    def _optimize_screen_space_position(self, element: ARElement,
                                      existing_elements: List[ARElement]) -> ARPosition:
        """Optimize position for screen-space elements."""
        
        # Get existing screen-space elements
        screen_elements = [e for e in existing_elements 
                          if e.anchor_type == AnchorType.SCREEN_SPACE]
        
        current_pos = element.position
        
        # Check for overlaps
        for other in screen_elements:
            if self._elements_overlap_2d(element, other):
                # Move to avoid overlap
                current_pos = self._find_non_overlapping_position(
                    element, screen_elements
                )
                break
        
        return current_pos

    def _evaluate_position_score(self, position: ARPosition, element: ARElement,
                               existing_elements: List[ARElement],
                               user_position: ARPosition,
                               detected_objects: List[Dict[str, Any]]) -> float:
        """Evaluate how good a position is for an AR element."""
        
        score = 1.0
        
        # Distance from user factor
        distance = self._calculate_distance(position, user_position)
        optimal_distance = 1.5  # meters
        distance_score = 1.0 - abs(distance - optimal_distance) / optimal_distance
        score *= max(0.1, distance_score)
        
        # Collision penalty
        for other in existing_elements:
            if self._elements_collide(element, other, position):
                score *= 0.3  # Heavy penalty for collision
        
        # Visibility score
        visibility = self._calculate_visibility_score(position, user_position, detected_objects)
        score *= visibility
        
        # Stability score (for object-anchored elements)
        if element.anchor_type == AnchorType.OBJECT_RELATIVE:
            stability = self._calculate_anchor_stability(element, detected_objects)
            score *= stability
        
        return score

    def _generate_search_points(self, center: ARPosition, radius: float) -> List[ARPosition]:
        """Generate search points around a center position."""
        
        points = []
        search_resolution = 8  # 8 points around circle
        
        for i in range(search_resolution):
            angle = (2 * math.pi * i) / search_resolution
            
            x = center.x + radius * math.cos(angle)
            y = center.y + radius * math.sin(angle) * 0.5  # Less vertical spread
            z = center.z + radius * math.sin(angle) * 0.3  # Minimal depth variation
            
            points.append(ARPosition(
                x=x, y=y, z=z,
                rotation_x=center.rotation_x,
                rotation_y=center.rotation_y,
                rotation_z=center.rotation_z,
                scale=center.scale
            ))
        
        return points

    def _calculate_distance(self, pos1: ARPosition, pos2: ARPosition) -> float:
        """Calculate 3D distance between two positions."""
        
        dx = pos1.x - pos2.x
        dy = pos1.y - pos2.y
        dz = pos1.z - pos2.z
        
        return math.sqrt(dx*dx + dy*dy + dz*dz)

    def _calculate_scale_factor(self, distance: float, element_type: ARElementType) -> float:
        """Calculate appropriate scale factor based on distance."""
        
        # Base scale factors for different element types at 1 meter
        base_scales = {
            ARElementType.TEXT_OVERLAY: 1.0,
            ARElementType.ARROW_POINTER: 1.2,
            ARElementType.HIGHLIGHT_BOX: 1.0,
            ARElementType.VIRTUAL_HAND: 0.8,
            ARElementType.WARNING_SIGN: 1.5,
            ARElementType.SUCCESS_CHECKMARK: 1.3
        }
        
        base_scale = base_scales.get(element_type, 1.0)
        
        # Scale based on distance (closer = smaller, farther = larger)
        if distance < 0.5:
            return base_scale * 0.7
        elif distance < 1.0:
            return base_scale
        elif distance < 2.0:
            return base_scale * 1.3
        else:
            return base_scale * 1.6

    def _elements_collide(self, element1: ARElement, element2: ARElement,
                        test_position: ARPosition) -> bool:
        """Check if two elements would collide."""
        
        # Simple bounding sphere collision detection
        pos1 = test_position
        pos2 = element2.position
        
        distance = self._calculate_distance(pos1, pos2)
        
        # Estimate element sizes (would be more accurate with actual bounding boxes)
        size1 = self._estimate_element_size(element1)
        size2 = self._estimate_element_size(element2)
        
        collision_distance = (size1 + size2) / 2 + self.collision_buffer
        
        return distance < collision_distance

    def _elements_overlap_2d(self, element1: ARElement, element2: ARElement) -> bool:
        """Check if screen-space elements overlap."""
        
        pos1 = element1.position
        pos2 = element2.position
        
        # Simple 2D overlap check
        size1 = self._estimate_element_size(element1) * 0.5
        size2 = self._estimate_element_size(element2) * 0.5
        
        return (abs(pos1.x - pos2.x) < size1 + size2 and 
                abs(pos1.y - pos2.y) < size1 + size2)

    def _estimate_element_size(self, element: ARElement) -> float:
        """Estimate the size of an AR element."""
        
        base_sizes = {
            ARElementType.TEXT_OVERLAY: 0.3,
            ARElementType.ARROW_POINTER: 0.2,
            ARElementType.HIGHLIGHT_BOX: 0.4,
            ARElementType.VIRTUAL_HAND: 0.25,
            ARElementType.WARNING_SIGN: 0.35,
            ARElementType.SUCCESS_CHECKMARK: 0.2,
            ARElementType.PROGRESS_BAR: 0.15
        }
        
        base_size = base_sizes.get(element.element_type, 0.3)
        return base_size * element.position.scale

    def _calculate_visibility_score(self, position: ARPosition,
                                  user_position: ARPosition,
                                  detected_objects: List[Dict[str, Any]]) -> float:
        """Calculate visibility score for a position."""
        
        # Check if position is within user's field of view
        fov_score = self._calculate_fov_score(position, user_position)
        
        # Check for occlusion by detected objects
        occlusion_score = self._calculate_occlusion_score(position, detected_objects)
        
        return fov_score * occlusion_score

    def _calculate_fov_score(self, position: ARPosition, user_position: ARPosition) -> float:
        """Calculate field of view score."""
        
        # Simple FOV calculation (assumes user facing forward)
        angle_to_object = math.atan2(position.x - user_position.x, 
                                   -(position.z - user_position.z))
        
        # Convert to degrees
        angle_degrees = math.degrees(angle_to_object)
        
        # Assume 60-degree FOV
        fov_half_angle = 30
        
        if abs(angle_degrees) <= fov_half_angle:
            return 1.0
        elif abs(angle_degrees) <= fov_half_angle + 15:  # Extended view
            return 0.7
        else:
            return 0.3  # Peripheral vision

    def _calculate_occlusion_score(self, position: ARPosition,
                                 detected_objects: List[Dict[str, Any]]) -> float:
        """Calculate occlusion score based on detected objects."""
        
        # Simplified occlusion calculation
        # In a real implementation, this would use ray casting
        
        occlusion_penalty = 0.0
        
        for obj in detected_objects:
            obj_pos = obj.get("position", {})
            obj_size = obj.get("size", 0.3)
            
            if obj_pos:
                obj_position = ARPosition(
                    x=obj_pos.get("x", 0),
                    y=obj_pos.get("y", 0),
                    z=obj_pos.get("z", 0)
                )
                
                distance_to_object = self._calculate_distance(position, obj_position)
                
                if distance_to_object < obj_size:
                    occlusion_penalty += 0.5  # Partially occluded
        
        return max(0.1, 1.0 - occlusion_penalty)

    def _calculate_anchor_stability(self, element: ARElement,
                                  detected_objects: List[Dict[str, Any]]) -> float:
        """Calculate anchor stability for object-relative elements."""
        
        if element.anchor_type != AnchorType.OBJECT_RELATIVE:
            return 1.0
        
        # Find the anchor object
        anchor_target = element.anchor_target
        
        for obj in detected_objects:
            if obj.get("id") == anchor_target:
                # Stability based on detection confidence and tracking quality
                confidence = obj.get("confidence", 0.5)
                tracking_quality = obj.get("tracking_quality", 0.5)
                
                return (confidence + tracking_quality) / 2
        
        return 0.1  # Low stability if anchor object not found

    def _find_non_overlapping_position(self, element: ARElement,
                                     existing_elements: List[ARElement]) -> ARPosition:
        """Find a screen position that doesn't overlap with existing elements."""
        
        # Try different positions
        test_positions = [
            ARPosition(x=0.1, y=0.1, z=0),   # Bottom left
            ARPosition(x=0.9, y=0.1, z=0),   # Bottom right
            ARPosition(x=0.1, y=0.9, z=0),   # Top left
            ARPosition(x=0.9, y=0.9, z=0),   # Top right
            ARPosition(x=0.5, y=0.1, z=0),   # Bottom center
            ARPosition(x=0.5, y=0.9, z=0),   # Top center
        ]
        
        for pos in test_positions:
            element.position = pos
            overlap = False
            
            for other in existing_elements:
                if self._elements_overlap_2d(element, other):
                    overlap = True
                    break
            
            if not overlap:
                return pos
        
        # If all positions overlap, return least overlapping
        return test_positions[0]

class ARInstructionSystem:
    def __init__(self, db_path: str = "ar_instructions.db"):
        self.db_path = db_path
        self.scene_builder = ARSceneBuilder()
        self.spatial_analyzer = SpatialAnalyzer()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ar_scenes (
            id TEXT PRIMARY KEY,
            tutorial_step_id TEXT,
            scene_title TEXT,
            description TEXT,
            elements TEXT,
            detection_targets TEXT,
            required_surfaces TEXT,
            lighting_requirements TEXT,
            camera_requirements TEXT,
            user_position_requirements TEXT,
            estimated_setup_time INTEGER,
            difficulty_level TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ar_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            scene_id TEXT,
            session_start TEXT,
            session_end TEXT,
            elements_interacted TEXT,
            user_feedback TEXT,
            performance_metrics TEXT,
            technical_issues TEXT,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_ar_scene(self, tutorial_step: Dict[str, Any],
                            environment_context: Dict[str, Any] = None) -> ARScene:
        """Create an AR scene for a tutorial step."""
        
        if environment_context is None:
            environment_context = {}
        
        scene = self.scene_builder.create_tutorial_scene(tutorial_step, environment_context)
        
        # Save to database
        await self._save_ar_scene(scene)
        
        return scene

    async def _save_ar_scene(self, scene: ARScene):
        """Save AR scene to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO ar_scenes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scene.id, scene.tutorial_step_id, scene.scene_title, scene.description,
            json.dumps([asdict(e) for e in scene.elements]),
            json.dumps([asdict(t) for t in scene.detection_targets]),
            json.dumps(scene.required_surfaces),
            json.dumps(scene.lighting_requirements),
            json.dumps(scene.camera_requirements),
            json.dumps(scene.user_position_requirements),
            scene.estimated_setup_time, scene.difficulty_level,
            scene.created_at, scene.updated_at
        ))
        
        conn.commit()
        conn.close()

    async def optimize_scene_for_environment(self, scene_id: str,
                                           user_position: Dict[str, float],
                                           detected_objects: List[Dict[str, Any]],
                                           lighting_conditions: Dict[str, Any]) -> ARScene:
        """Optimize AR scene based on current environment conditions."""
        
        scene = await self.get_ar_scene(scene_id)
        if not scene:
            return None
        
        # Convert user position
        user_pos = ARPosition(
            x=user_position.get("x", 0),
            y=user_position.get("y", 0),
            z=user_position.get("z", 0)
        )
        
        # Optimize element placement
        optimized_elements = self.spatial_analyzer.optimize_element_placement(
            scene.elements, user_pos, detected_objects
        )
        
        # Update scene
        scene.elements = optimized_elements
        scene.updated_at = datetime.now().isoformat()
        
        # Adjust for lighting conditions
        scene = await self._adjust_for_lighting(scene, lighting_conditions)
        
        # Save optimized scene
        await self._save_ar_scene(scene)
        
        return scene

    async def _adjust_for_lighting(self, scene: ARScene, 
                                 lighting_conditions: Dict[str, Any]) -> ARScene:
        """Adjust AR elements based on lighting conditions."""
        
        current_lux = lighting_conditions.get("lux", 500)
        
        for element in scene.elements:
            # Adjust text elements for readability
            if element.element_type == ARElementType.TEXT_OVERLAY:
                if current_lux < 200:  # Low light
                    element.style_properties["background_color"] = "#000000DD"
                    element.style_properties["font_color"] = "#FFFFFF"
                elif current_lux > 800:  # Bright light
                    element.style_properties["background_color"] = "#FFFFFFDD"
                    element.style_properties["font_color"] = "#000000"
            
            # Adjust highlight elements
            elif element.element_type == ARElementType.HIGHLIGHT_BOX:
                if current_lux < 200:
                    element.style_properties["border_color"] = "#FFFF00"  # More visible yellow
                else:
                    element.style_properties["border_color"] = "#00FF00"  # Standard green
        
        return scene

    async def get_ar_scene(self, scene_id: str) -> Optional[ARScene]:
        """Get AR scene by ID."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM ar_scenes WHERE id = ?', (scene_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct scene object
        elements_data = json.loads(row[4])
        elements = [ARElement(**elem_data) for elem_data in elements_data]
        
        targets_data = json.loads(row[5])
        detection_targets = [ObjectDetectionTarget(**target_data) for target_data in targets_data]
        
        return ARScene(
            id=row[0], tutorial_step_id=row[1], scene_title=row[2], description=row[3],
            elements=elements, detection_targets=detection_targets,
            required_surfaces=json.loads(row[6]),
            lighting_requirements=json.loads(row[7]),
            camera_requirements=json.loads(row[8]),
            user_position_requirements=json.loads(row[9]),
            estimated_setup_time=row[10], difficulty_level=row[11],
            created_at=row[12], updated_at=row[13]
        )

    async def handle_ar_interaction(self, scene_id: str, element_id: str,
                                  interaction_type: str, 
                                  interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle user interaction with AR elements."""
        
        scene = await self.get_ar_scene(scene_id)
        if not scene:
            return {"error": "Scene not found"}
        
        # Find the element
        element = next((e for e in scene.elements if e.id == element_id), None)
        if not element:
            return {"error": "Element not found"}
        
        # Validate interaction type
        if InteractionType(interaction_type) not in element.interaction_types:
            return {"error": f"Interaction type {interaction_type} not supported for this element"}
        
        # Process interaction
        response = await self._process_ar_interaction(element, interaction_type, interaction_data)
        
        # Record interaction for analytics
        await self._record_ar_interaction(scene_id, element_id, interaction_type, interaction_data)
        
        return response

    async def _process_ar_interaction(self, element: ARElement, 
                                    interaction_type: str,
                                    interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process specific AR interaction."""
        
        response = {
            "element_id": element.id,
            "interaction_processed": True,
            "feedback": []
        }
        
        if interaction_type == "tap":
            if element.element_type == ARElementType.TEXT_OVERLAY:
                response["action"] = "expand_text"
                response["feedback"].append("Text expanded for better readability")
            
            elif element.element_type == ARElementType.WARNING_SIGN:
                response["action"] = "show_safety_details"
                response["feedback"].append("Safety information displayed")
            
            elif element.element_type == ARElementType.PROGRESS_BAR:
                response["action"] = "show_progress_details"
                response["feedback"].append("Detailed progress information shown")
        
        elif interaction_type == "voice_command":
            command = interaction_data.get("command", "").lower()
            
            if "help" in command:
                response["action"] = "provide_help"
                response["feedback"].append("Additional guidance provided")
            
            elif "repeat" in command:
                response["action"] = "repeat_instruction"
                response["feedback"].append("Instruction repeated")
            
            elif "next" in command:
                response["action"] = "advance_step"
                response["feedback"].append("Advanced to next step")
        
        elif interaction_type == "hand_gesture":
            gesture = interaction_data.get("gesture_type", "")
            
            if gesture == "swipe":
                response["action"] = "navigate_content"
                response["feedback"].append("Content navigation activated")
            
            elif gesture == "pinch":
                response["action"] = "scale_element"
                response["feedback"].append("Element scaling activated")
        
        return response

    async def _record_ar_interaction(self, scene_id: str, element_id: str,
                                   interaction_type: str, 
                                   interaction_data: Dict[str, Any]):
        """Record AR interaction for analytics."""
        
        interaction_record = {
            "timestamp": datetime.now().isoformat(),
            "scene_id": scene_id,
            "element_id": element_id,
            "interaction_type": interaction_type,
            "interaction_data": interaction_data
        }
        
        # This would typically be stored in a dedicated analytics system
        # For now, we'll store it in the session data when a session is active
        pass

    async def get_ar_setup_instructions(self, scene_id: str) -> Dict[str, Any]:
        """Get setup instructions for AR scene."""
        
        scene = await self.get_ar_scene(scene_id)
        if not scene:
            return {"error": "Scene not found"}
        
        instructions = {
            "scene_title": scene.scene_title,
            "estimated_setup_time": f"{scene.estimated_setup_time} seconds",
            "difficulty_level": scene.difficulty_level,
            "requirements": {
                "lighting": scene.lighting_requirements,
                "camera": scene.camera_requirements,
                "positioning": scene.user_position_requirements,
                "surfaces": scene.required_surfaces
            },
            "setup_steps": [
                "Ensure adequate lighting (200-1000 lux)",
                "Position camera at arm's length from work area",
                "Clear workspace of unnecessary objects",
                "Stand at recommended distance from target area",
                "Wait for AR calibration to complete"
            ],
            "detection_targets": [
                {
                    "name": target.name,
                    "description": target.description,
                    "required": target.confidence_threshold > 0.8
                }
                for target in scene.detection_targets
            ]
        }
        
        return instructions

if __name__ == "__main__":
    async def main():
        ar_system = ARInstructionSystem()
        
        # Create a sample tutorial step
        tutorial_step = {
            "id": "step_001",
            "title": "Connect USB Cable",
            "description": "Connect the USB cable to your device",
            "instructions": [
                "Locate the USB cable in your kit",
                "Find the USB port on your device", 
                "Gently insert the USB connector",
                "Ensure the connection is secure"
            ],
            "step_type": "assembly",
            "materials_needed": ["USB cable", "device"],
            "safety_warnings": ["Do not force the connection"]
        }
        
        environment_context = {
            "current_step": 3,
            "total_steps": 10,
            "user_skill_level": "beginner"
        }
        
        # Create AR scene
        scene = await ar_system.create_ar_scene(tutorial_step, environment_context)
        
        print(f"Created AR scene: {scene.scene_title}")
        print(f"Elements: {len(scene.elements)}")
        print(f"Detection targets: {len(scene.detection_targets)}")
        print(f"Estimated setup time: {scene.estimated_setup_time} seconds")
        
        # Show AR elements
        print("\nAR Elements:")
        for element in scene.elements:
            print(f"  - {element.element_type.value}: {element.title}")
            print(f"    Position: ({element.position.x:.1f}, {element.position.y:.1f}, {element.position.z:.1f})")
            print(f"    Priority: {element.priority}")
        
        # Get setup instructions
        setup_info = await ar_system.get_ar_setup_instructions(scene.id)
        print(f"\nSetup Instructions:")
        print(f"Setup time: {setup_info['estimated_setup_time']}")
        print(f"Required surfaces: {setup_info['requirements']['surfaces']}")
        
        # Simulate user interaction
        interaction_result = await ar_system.handle_ar_interaction(
            scene.id, scene.elements[0].id, "tap", {}
        )
        
        print(f"\nInteraction result: {interaction_result.get('action', 'No action')}")
        if interaction_result.get('feedback'):
            print(f"Feedback: {interaction_result['feedback'][0]}")
    
    asyncio.run(main())