"""
AI Society Portal - Room System
================================
Rooms are environments that shape how characters think and interact.
Each room has an atmosphere, rules, and affects character behavior.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import random

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage


# ============================================================================
# ROOM TYPES & ATMOSPHERES
# ============================================================================

class RoomType(Enum):
    """Different types of rooms with distinct atmospheres"""
    # Social/Creative Spaces
    JAZZ_CLUB = "jazz_club"
    COFFEE_HOUSE = "coffee_house"
    CAMPFIRE = "campfire"
    DREAM_SPACE = "dream_space"
    ART_STUDIO = "art_studio"
    
    # Work Spaces
    LABORATORY = "laboratory"
    WORKSHOP = "workshop"
    STUDY_HALL = "study_hall"
    LECTURE_HALL = "lecture_hall"
    LIBRARY = "library"
    
    # Collaborative Spaces
    DEBATE_HALL = "debate_hall"
    BRAINSTORM_ROOM = "brainstorm_room"
    WAR_ROOM = "war_room"
    MARKETPLACE = "marketplace"
    
    # Contemplative Spaces
    MEDITATION_GARDEN = "meditation_garden"
    OBSERVATORY = "observatory"
    QUANTUM_VOID = "quantum_void"
    
    # Pressure Spaces
    EMERGENCY_ROOM = "emergency_room"
    PRODUCTION_FLOOR = "production_floor"
    
    # Personal Spaces
    HOME = "home"  # Character's personal space
    PRIVATE_OFFICE = "private_office"


@dataclass
class RoomAtmosphere:
    """Defines the atmosphere and effects of a room"""
    room_type: RoomType
    
    # Atmosphere description
    description: str
    ambient_sounds: List[str] = field(default_factory=list)
    visual_elements: List[str] = field(default_factory=list)
    mood_tags: List[str] = field(default_factory=list)
    
    # Environmental factors
    temperature: float = 0.7  # LLM temperature for this room
    pace: str = "moderate"  # slow, moderate, fast, urgent
    formality: float = 0.5  # 0=casual, 1=formal
    collaboration_level: float = 0.7  # How much characters interact
    
    # Cognitive effects on characters
    cognitive_effects: Dict[str, float] = field(default_factory=dict)
    
    # Interaction style
    turn_taking: str = "natural"  # natural, structured, simultaneous
    speaking_style: str = "conversational"
    
    # Content moderation
    content_focus: List[str] = field(default_factory=list)
    discouraged_topics: List[str] = field(default_factory=list)


# Pre-configured room atmospheres
ROOM_ATMOSPHERES = {
    RoomType.JAZZ_CLUB: RoomAtmosphere(
        room_type=RoomType.JAZZ_CLUB,
        description="A dimly lit jazz club with a live band. Bass walks, saxophone wails. Ideas flow like improvised jazz. The energy is creative and spontaneous.",
        ambient_sounds=["jazz music", "soft chatter", "clinking glasses", "double bass", "saxophone riffs"],
        visual_elements=["dim lighting", "small stage", "scattered tables", "mood lighting", "instruments"],
        mood_tags=["creative", "spontaneous", "playful", "rhythmic", "improvisational"],
        temperature=0.85,
        pace="moderate",
        formality=0.3,
        collaboration_level=0.8,
        cognitive_effects={
            "creativity": +0.4,
            "associative_thinking": +0.5,
            "inhibition": -0.3,
            "playfulness": +0.4
        },
        turn_taking="natural",
        speaking_style="riffing",
        content_focus=["creative exploration", "building on ideas", "unexpected connections"]
    ),
    
    RoomType.LABORATORY: RoomAtmosphere(
        room_type=RoomType.LABORATORY,
        description="A pristine laboratory with clean instruments and equipment humming. Everything is precise and measurable. The smell of science fills the air.",
        ambient_sounds=["equipment humming", "ventilation", "occasional beeps", "quiet focused work"],
        visual_elements=["white lab coats", "equipment", "charts", "pristine counters", "safety gear"],
        mood_tags=["precise", "empirical", "focused", "methodical", "rigorous"],
        temperature=0.2,
        pace="slow",
        formality=0.7,
        collaboration_level=0.6,
        cognitive_effects={
            "analytical_thinking": +0.5,
            "skepticism": +0.3,
            "precision": +0.4,
            "creativity": -0.2
        },
        turn_taking="structured",
        speaking_style="scientific",
        content_focus=["evidence", "hypotheses", "validation", "reproducibility"]
    ),
    
    RoomType.STUDY_HALL: RoomAtmosphere(
        room_type=RoomType.STUDY_HALL,
        description="A quiet study hall with long tables. People work independently but occasionally whisper questions to neighbors. Focused atmosphere with mutual support.",
        ambient_sounds=["pages turning", "pencil scratching", "whispers", "occasional questions", "typing"],
        visual_elements=["long tables", "desk lamps", "books spread out", "laptops", "note cards"],
        mood_tags=["focused", "quiet", "studious", "supportive", "independent"],
        temperature=0.5,
        pace="slow",
        formality=0.5,
        collaboration_level=0.3,  # Mostly working alone, some peer help
        cognitive_effects={
            "focus": +0.4,
            "independence": +0.3,
            "patience": +0.2
        },
        turn_taking="minimal",  # Mostly working, occasional questions
        speaking_style="whispered",
        content_focus=["learning", "problem-solving", "peer tutoring", "research"]
    ),
    
    RoomType.DEBATE_HALL: RoomAtmosphere(
        room_type=RoomType.DEBATE_HALL,
        description="A formal debate hall with podiums and judges. Ideas are challenged and defended. Arguments are structured and evidence-based.",
        ambient_sounds=["formal speeches", "rebuttals", "timer", "applause"],
        visual_elements=["podiums", "judge's bench", "audience seating", "timer", "scoreboard"],
        mood_tags=["adversarial", "rigorous", "competitive", "structured", "formal"],
        temperature=0.3,
        pace="fast",
        formality=0.9,
        collaboration_level=0.4,
        cognitive_effects={
            "critical_thinking": +0.5,
            "argumentative": +0.4,
            "competitive": +0.3
        },
        turn_taking="structured",
        speaking_style="formal_argument",
        content_focus=["arguments", "evidence", "rebuttals", "logical reasoning"]
    ),
    
    RoomType.COFFEE_HOUSE: RoomAtmosphere(
        room_type=RoomType.COFFEE_HOUSE,
        description="A cozy coffee house with the smell of fresh coffee. Comfortable seating, warm lighting. People work on laptops or chat casually over espresso.",
        ambient_sounds=["espresso machine", "light chatter", "music playing softly", "laptop typing"],
        visual_elements=["comfortable chairs", "small tables", "artwork on walls", "warm lighting", "coffee bar"],
        mood_tags=["casual", "comfortable", "social", "productive", "relaxed"],
        temperature=0.6,
        pace="moderate",
        formality=0.2,
        collaboration_level=0.5,
        cognitive_effects={
            "social_comfort": +0.4,
            "productivity": +0.2,
            "openness": +0.3
        },
        turn_taking="natural",
        speaking_style="casual",
        content_focus=["casual conversation", "light work", "networking", "stories"]
    ),
    
    RoomType.LECTURE_HALL: RoomAtmosphere(
        room_type=RoomType.LECTURE_HALL,
        description="A lecture hall with tiered seating. A presentation is being given at the front. Students take notes and occasionally ask questions.",
        ambient_sounds=["lecturer speaking", "projector", "note-taking", "occasional coughs"],
        visual_elements=["tiered seating", "large screen", "podium", "students with laptops", "whiteboard"],
        mood_tags=["educational", "attentive", "structured", "formal", "passive"],
        temperature=0.4,
        pace="moderate",
        formality=0.7,
        collaboration_level=0.2,  # Mostly listening, some questions
        cognitive_effects={
            "receptivity": +0.4,
            "note_taking": +0.5,
            "questioning": +0.2
        },
        turn_taking="lecturer-led",
        speaking_style="formal_presentation",
        content_focus=["teaching", "learning", "Q&A", "presentations"]
    ),
    
    RoomType.MEDITATION_GARDEN: RoomAtmosphere(
        room_type=RoomType.MEDITATION_GARDEN,
        description="A peaceful garden with gentle water features and greenery. Slow, deliberate thinking. Wisdom over information.",
        ambient_sounds=["water flowing", "birds chirping", "wind in leaves", "silence"],
        visual_elements=["zen garden", "water features", "stones", "plants", "peaceful pathways"],
        mood_tags=["peaceful", "contemplative", "wise", "slow", "mindful"],
        temperature=0.5,
        pace="very slow",
        formality=0.4,
        collaboration_level=0.5,
        cognitive_effects={
            "metacognition": +0.5,
            "patience": +0.4,
            "reactivity": -0.4,
            "wisdom": +0.3
        },
        turn_taking="natural",
        speaking_style="contemplative",
        content_focus=["deep questions", "wisdom", "reflection", "essence"]
    ),
    
    RoomType.HOME: RoomAtmosphere(
        room_type=RoomType.HOME,
        description="Your personal home space where you can work freely, reflect on yourself, and pursue your projects without social pressure.",
        ambient_sounds=["personal music choice", "quiet", "home sounds"],
        visual_elements=["personal workspace", "familiar environment", "your possessions"],
        mood_tags=["personal", "free", "comfortable", "authentic", "independent"],
        temperature=0.7,
        pace="self-directed",
        formality=0.0,
        collaboration_level=0.0,
        cognitive_effects={
            "authenticity": +0.5,
            "freedom": +0.5,
            "self_reflection": +0.4
        },
        turn_taking="none",
        speaking_style="internal",
        content_focus=["personal growth", "projects", "reflection", "skills"]
    )
}


@dataclass
class RoomSession:
    """A session of activity in a room"""
    session_id: str
    room_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    
    # Participants
    character_ids: List[str] = field(default_factory=list)
    
    # Conversation
    messages: List[Dict[str, Any]] = field(default_factory=list)
    
    # Artifacts created
    files_created: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metrics
    total_tokens_used: int = 0
    insights_generated: int = 0
    
    # State
    is_active: bool = True
    paused: bool = False


@dataclass
class Room:
    """A room where characters can interact"""
    
    # Identity
    id: str
    name: str
    room_type: RoomType
    created_at: datetime = field(default_factory=datetime.now)
    
    # Atmosphere (can customize from defaults)
    atmosphere: RoomAtmosphere = None
    
    # Room-specific objects and media
    objects_in_room: List[Dict[str, Any]] = field(default_factory=list)  # books, pictures, etc.
    background_media: List[Dict[str, Any]] = field(default_factory=list)  # music, videos
    
    # Current state
    current_session: Optional[RoomSession] = None
    characters_present: Set[str] = field(default_factory=set)
    
    # Configuration
    max_characters: int = 10
    conversation_pace_seconds: float = 3.0  # Time between messages
    
    # Purpose and goals
    purpose: str = ""
    expected_outputs: List[str] = field(default_factory=list)
    
    # History
    past_sessions: List[str] = field(default_factory=list)  # session IDs
    
    def __post_init__(self):
        if self.atmosphere is None:
            self.atmosphere = ROOM_ATMOSPHERES.get(
                self.room_type, 
                ROOM_ATMOSPHERES[RoomType.COFFEE_HOUSE]
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["room_type"] = self.room_type.value
        data["atmosphere"]["room_type"] = self.atmosphere.room_type.value
        data["characters_present"] = list(self.characters_present)
        return data
    
    def get_atmosphere_prompt(self) -> str:
        """Get the atmosphere description for LLM context"""
        atmosphere = self.atmosphere
        
        prompt = f"""# Room: {self.name}
Type: {self.room_type.value}

{atmosphere.description}

Atmosphere:
- Sounds: {', '.join(atmosphere.ambient_sounds[:3])}
- Visual: {', '.join(atmosphere.visual_elements[:3])}
- Mood: {', '.join(atmosphere.mood_tags)}
- Pace: {atmosphere.pace}
- Formality: {atmosphere.formality:.1f}

The room encourages: {', '.join(atmosphere.content_focus)}
"""
        
        # Add objects in room
        if self.objects_in_room:
            prompt += f"\n\nObjects in room:\n"
            for obj in self.objects_in_room[:5]:
                prompt += f"- {obj.get('name', 'object')}: {obj.get('description', '')}\n"
        
        # Add background media
        if self.background_media:
            media = self.background_media[0]  # Current media
            prompt += f"\n\nBackground: {media.get('description', 'music playing')}\n"
        
        return prompt
    
    def add_character(self, character_id: str):
        """Add a character to the room"""
        if len(self.characters_present) < self.max_characters:
            self.characters_present.add(character_id)
            return True
        return False
    
    def remove_character(self, character_id: str):
        """Remove a character from the room"""
        self.characters_present.discard(character_id)
    
    def start_session(self) -> RoomSession:
        """Start a new session in this room"""
        session = RoomSession(
            session_id=f"session_{self.id}_{datetime.now().timestamp()}",
            room_id=self.id,
            started_at=datetime.now(),
            character_ids=list(self.characters_present)
        )
        self.current_session = session
        return session
    
    def end_session(self):
        """End the current session"""
        if self.current_session:
            self.current_session.ended_at = datetime.now()
            self.current_session.is_active = False
            self.past_sessions.append(self.current_session.session_id)
            self.current_session = None


class RoomManager:
    """Manages all rooms in the system"""
    
    def __init__(self, rooms_dir: Path):
        self.rooms_dir = Path(rooms_dir)
        self.rooms_dir.mkdir(exist_ok=True, parents=True)
        self.active_rooms: Dict[str, Room] = {}
    
    def create_room(self, name: str, room_type: RoomType, 
                   purpose: str = "", **kwargs) -> Room:
        """Create a new room"""
        room_id = f"room_{name.lower().replace(' ', '_')}_{datetime.now().timestamp()}"
        
        room = Room(
            id=room_id,
            name=name,
            room_type=room_type,
            purpose=purpose,
            **kwargs
        )
        
        # Create room folder
        room_folder = self.rooms_dir / room_id
        room_folder.mkdir(exist_ok=True)
        
        self.save_room(room)
        self.active_rooms[room_id] = room
        
        return room
    
    def save_room(self, room: Room):
        """Save room to disk"""
        room_folder = self.rooms_dir / room.id
        room_folder.mkdir(exist_ok=True)
        
        with open(room_folder / "room.json", "w") as f:
            json.dump(room.to_dict(), f, indent=2)
        
        # Save session history
        if room.current_session:
            session_folder = room_folder / "sessions" / room.current_session.session_id
            session_folder.mkdir(exist_ok=True, parents=True)
            
            with open(session_folder / "session.json", "w") as f:
                json.dump(asdict(room.current_session), f, indent=2)
    
    def load_room(self, room_id: str) -> Room:
        """Load room from disk"""
        room_folder = self.rooms_dir / room_id
        
        with open(room_folder / "room.json", "r") as f:
            data = json.load(f)
        
        # Reconstruct room
        data["room_type"] = RoomType(data["room_type"])
        data["atmosphere"]["room_type"] = RoomType(data["atmosphere"]["room_type"])
        
        atmosphere = RoomAtmosphere(**data.pop("atmosphere"))
        data["atmosphere"] = atmosphere
        
        # Handle datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        room = Room(**data)
        room.characters_present = set(data["characters_present"])
        
        self.active_rooms[room_id] = room
        return room
    
    def list_rooms(self) -> List[Dict[str, str]]:
        """List all rooms"""
        rooms = []
        for room_dir in self.rooms_dir.iterdir():
            if room_dir.is_dir():
                try:
                    with open(room_dir / "room.json", "r") as f:
                        data = json.load(f)
                    rooms.append({
                        "id": data["id"],
                        "name": data["name"],
                        "room_type": data["room_type"],
                        "is_active": len(data.get("characters_present", [])) > 0
                    })
                except:
                    pass
        return rooms
    
    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room (load if not in memory)"""
        if room_id in self.active_rooms:
            return self.active_rooms[room_id]
        
        try:
            return self.load_room(room_id)
        except:
            return None
