"""
AI Society Portal - Character System
=====================================
Each character is a persistent entity with their own "laptop" (folder system),
memories, ongoing projects, and ability to work independently or in rooms.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import random
import hashlib

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


# ============================================================================
# CHARACTER ARCHITECTURE
# ============================================================================

class CharacterState(Enum):
    """What the character is currently doing"""
    HOME_WORKING = "home_working"          # At home, working on projects
    HOME_REFLECTING = "home_reflecting"    # At home, self-reflection
    IN_ROOM = "in_room"                    # Participating in a room
    TRAVELING = "traveling"                # Moving between locations
    OFFLINE = "offline"                    # Not active


class WorkMode(Enum):
    """How the character approaches their work"""
    DEEP_FOCUS = "deep_focus"             # High-level thinking with large model
    NUTS_AND_BOLTS = "nuts_and_bolts"     # Detailed work with smaller model
    RESEARCH = "research"                 # Learning and gathering information
    CREATIVE = "creative"                 # Generative work
    COLLABORATIVE = "collaborative"        # Working with others


@dataclass
class CharacterLaptop:
    """The character's personal computing environment and file system"""
    owner_id: str
    storage_size_mb: int = 100  # How much storage they have
    current_usage_mb: float = 0.0
    
    # File organization
    documents: List[Dict[str, Any]] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    code_files: List[Dict[str, Any]] = field(default_factory=list)
    conversation_logs: List[Dict[str, Any]] = field(default_factory=list)
    research_notes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Active work
    current_projects: List[Dict[str, Any]] = field(default_factory=list)
    active_tasks: List[str] = field(default_factory=list)
    
    # Private LLM conversations
    private_chats: Dict[str, List[BaseMessage]] = field(default_factory=dict)
    
    # Tools and access
    available_tools: List[str] = field(default_factory=lambda: [
        "text_editor", "image_generator", "code_runner", 
        "web_search", "vector_search", "calculator"
    ])
    
    # Preferences
    preferred_home_model: str = "gpt-4o-mini"  # For cost-effective home work
    preferred_deep_model: str = "claude-sonnet-4"  # For complex thinking
    current_mode: WorkMode = WorkMode.NUTS_AND_BOLTS
    
    def add_file(self, file_type: str, name: str, content: Any, metadata: Dict = None):
        """Add a file to the laptop"""
        file_data = {
            "name": name,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "size_mb": len(str(content)) / (1024 * 1024)  # Rough estimate
        }
        
        # Check storage
        if self.current_usage_mb + file_data["size_mb"] > self.storage_size_mb:
            # Need to archive or delete old files
            self._make_space(file_data["size_mb"])
        
        # Add to appropriate collection
        if file_type == "document":
            self.documents.append(file_data)
        elif file_type == "image":
            self.images.append(file_data)
        elif file_type == "code":
            self.code_files.append(file_data)
        elif file_type == "conversation":
            self.conversation_logs.append(file_data)
        elif file_type == "research":
            self.research_notes.append(file_data)
            
        self.current_usage_mb += file_data["size_mb"]
        
    def _make_space(self, needed_mb: float):
        """Archive or delete old files to make space"""
        # Sort by age and delete oldest, least important files
        all_files = (
            [(f, "document") for f in self.documents] +
            [(f, "image") for f in self.images] +
            [(f, "code") for f in self.code_files] +
            [(f, "conversation") for f in self.conversation_logs]
        )
        
        # Sort by created_at
        all_files.sort(key=lambda x: x[0]["created_at"])
        
        freed_space = 0.0
        while freed_space < needed_mb and all_files:
            file_to_remove, file_type = all_files.pop(0)
            freed_space += file_to_remove["size_mb"]
            self.current_usage_mb -= file_to_remove["size_mb"]
            
            # Remove from appropriate collection
            if file_type == "document":
                self.documents.remove(file_to_remove)
            elif file_type == "image":
                self.images.remove(file_to_remove)
            # ... etc
    
    def get_recent_work(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent work summary for context"""
        recent = []
        
        # Get recent files from each category
        for files, category in [
            (self.documents, "document"),
            (self.code_files, "code"),
            (self.research_notes, "research")
        ]:
            sorted_files = sorted(files, key=lambda x: x["created_at"], reverse=True)
            for file in sorted_files[:2]:
                recent.append({
                    "category": category,
                    "name": file["name"],
                    "summary": str(file["content"])[:200] + "...",
                    "created": file["created_at"]
                })
        
        return recent[:limit]


@dataclass
class CharacterMemory:
    """Simplified memory system for characters"""
    owner_id: str
    
    # Current session memory (cleared periodically)
    working_memory: List[str] = field(default_factory=list)
    
    # Important experiences (kept longer)
    episodic_memory: List[Dict[str, Any]] = field(default_factory=list)
    
    # Core knowledge and identity
    semantic_memory: Dict[str, Any] = field(default_factory=dict)
    
    # Memory of other characters
    relationship_memories: Dict[str, List[str]] = field(default_factory=dict)
    
    max_working_memory: int = 20
    
    def remember(self, content: str, importance: float = 0.5, 
                 context: str = "general"):
        """Add a memory"""
        self.working_memory.append(content)
        
        # If working memory is full, consolidate
        if len(self.working_memory) > self.max_working_memory:
            self._consolidate()
            
        # If important, also add to episodic
        if importance > 0.7:
            self.episodic_memory.append({
                "content": content,
                "importance": importance,
                "context": context,
                "timestamp": datetime.now().isoformat()
            })
    
    def _consolidate(self):
        """Move working memory to episodic, keeping only recent items"""
        # Keep only most recent items in working memory
        self.working_memory = self.working_memory[-10:]
    
    def recall_about(self, character_id: str, limit: int = 3) -> List[str]:
        """Recall memories about a specific character"""
        if character_id in self.relationship_memories:
            return self.relationship_memories[character_id][-limit:]
        return []
    
    def get_context_summary(self, max_length: int = 500) -> str:
        """Get a summary of memories for context window"""
        summary_parts = []
        
        # Recent working memory
        if self.working_memory:
            summary_parts.append("Recent thoughts: " + "; ".join(self.working_memory[-3:]))
        
        # Key episodic memories
        important_episodes = sorted(
            self.episodic_memory, 
            key=lambda x: x["importance"], 
            reverse=True
        )[:2]
        
        if important_episodes:
            summary_parts.append("Important memories: " + "; ".join(
                [e["content"][:100] for e in important_episodes]
            ))
        
        summary = " | ".join(summary_parts)
        return summary[:max_length]


@dataclass
class Character:
    """A persistent AI character with their own life, work, and personality"""
    
    # Identity
    id: str
    name: str
    specialization: str
    backstory: str
    
    # Personality (0-1 scales)
    personality: Dict[str, float] = field(default_factory=lambda: {
        "curious": 0.7,
        "analytical": 0.6,
        "creative": 0.5,
        "social": 0.6,
        "methodical": 0.5,
        "playful": 0.4,
        "skeptical": 0.5,
        "empathetic": 0.6
    })
    
    # Current state
    state: CharacterState = CharacterState.HOME_WORKING
    current_room_id: Optional[str] = None
    current_mood: Dict[str, float] = field(default_factory=lambda: {
        "energy": 0.7,
        "focus": 0.6,
        "enthusiasm": 0.5
    })
    
    # Systems
    laptop: CharacterLaptop = None
    memory: CharacterMemory = None
    
    # Skills and expertise
    skills: List[str] = field(default_factory=list)
    expertise_areas: List[str] = field(default_factory=list)
    
    # Goals and motivations
    current_goals: List[str] = field(default_factory=list)
    long_term_aspirations: List[str] = field(default_factory=list)
    
    # Quirks and traits
    quirks: List[str] = field(default_factory=list)
    communication_style: str = "balanced"
    
    # Relationships with other characters
    relationships: Dict[str, float] = field(default_factory=dict)  # character_id -> affinity (-1 to 1)
    
    # Stats
    total_room_hours: float = 0.0
    total_projects_completed: int = 0
    insights_contributed: int = 0
    
    def __post_init__(self):
        if self.laptop is None:
            self.laptop = CharacterLaptop(owner_id=self.id)
        if self.memory is None:
            self.memory = CharacterMemory(owner_id=self.id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["state"] = self.state.value
        data["laptop"]["current_mode"] = self.laptop.current_mode.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Character':
        """Create from dictionary"""
        # Convert enums
        data["state"] = CharacterState(data["state"])
        
        # Create laptop
        laptop_data = data.pop("laptop")
        laptop_data["current_mode"] = WorkMode(laptop_data["current_mode"])
        laptop = CharacterLaptop(**laptop_data)
        
        # Create memory
        memory_data = data.pop("memory")
        memory = CharacterMemory(**memory_data)
        
        # Create character
        char = cls(**data)
        char.laptop = laptop
        char.memory = memory
        return char
    
    def get_room_context(self, room_atmosphere: str) -> str:
        """Generate context for when character is in a room"""
        context = f"""You are {self.name}, {self.specialization}.
        
{self.backstory}

Personality: {', '.join([f'{k}: {v:.1f}' for k, v in self.personality.items() if v > 0.6])}
Current mood: {', '.join([f'{k}: {v:.1f}' for k, v in self.current_mood.items()])}

The room atmosphere is: {room_atmosphere}

Your recent work:
{chr(10).join([f"- {work['name']} ({work['category']})" for work in self.laptop.get_recent_work()])}

{self.memory.get_context_summary()}

Your communication style: {self.communication_style}
"""
        return context
    
    def get_home_context(self) -> str:
        """Generate context for when character is at home working"""
        context = f"""You are {self.name}, {self.specialization}, working at home.

{self.backstory}

Current goals: {', '.join(self.current_goals)}
Current projects: {', '.join([p['name'] for p in self.laptop.current_projects])}

Work mode: {self.laptop.current_mode.value}

Recent work:
{chr(10).join([f"- {work['name']}: {work['summary']}" for work in self.laptop.get_recent_work()])}

You have access to: {', '.join(self.laptop.available_tools)}

{self.memory.get_context_summary()}
"""
        return context
    
    async def work_at_home(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Character works on their projects at home"""
        
        # Simulate work session
        work_log = {
            "character_id": self.id,
            "character_name": self.name,
            "duration_minutes": duration_minutes,
            "work_done": [],
            "thoughts": [],
            "files_created": []
        }
        
        # Determine what to work on based on current projects and goals
        if self.laptop.current_projects:
            project = self.laptop.current_projects[0]
            
            # Generate some work on the project
            # In a real implementation, this would interact with LLMs
            work_log["work_done"].append(f"Made progress on {project['name']}")
            
            # Add a memory
            self.memory.remember(
                f"Worked on {project['name']} for {duration_minutes} minutes",
                importance=0.5,
                context="home_work"
            )
        
        # Self-reflection
        if random.random() < 0.3:  # 30% chance of reflection
            work_log["thoughts"].append(
                f"Reflected on my identity as {self.specialization}"
            )
        
        return work_log
    
    def interact_with_character(self, other_char: 'Character', 
                               context: str, valence: float):
        """Update relationship based on interaction"""
        if other_char.id not in self.relationships:
            self.relationships[other_char.id] = 0.0
        
        # Update affinity
        self.relationships[other_char.id] += valence * 0.1
        self.relationships[other_char.id] = max(-1.0, min(1.0, 
                                                           self.relationships[other_char.id]))
        
        # Remember the interaction
        if other_char.id not in self.memory.relationship_memories:
            self.memory.relationship_memories[other_char.id] = []
        
        self.memory.relationship_memories[other_char.id].append(
            f"Interaction in {context}: {valence:.2f} valence"
        )


class CharacterManager:
    """Manages all characters in the system"""
    
    def __init__(self, characters_dir: Path):
        self.characters_dir = Path(characters_dir)
        self.characters_dir.mkdir(exist_ok=True, parents=True)
        self.active_characters: Dict[str, Character] = {}
    
    def create_character(self, name: str, specialization: str, 
                        backstory: str, **kwargs) -> Character:
        """Create a new character"""
        char_id = hashlib.md5(f"{name}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        character = Character(
            id=char_id,
            name=name,
            specialization=specialization,
            backstory=backstory,
            **kwargs
        )
        
        # Create character's folder
        char_folder = self.characters_dir / char_id
        char_folder.mkdir(exist_ok=True)
        
        # Save character
        self.save_character(character)
        self.active_characters[char_id] = character
        
        return character
    
    def save_character(self, character: Character):
        """Save character to disk"""
        char_folder = self.characters_dir / character.id
        char_folder.mkdir(exist_ok=True)
        
        # Save main character data
        with open(char_folder / "character.json", "w") as f:
            json.dump(character.to_dict(), f, indent=2)
        
        # Save laptop files separately for easier access
        laptop_folder = char_folder / "laptop"
        laptop_folder.mkdir(exist_ok=True)
        
        # Save documents
        for doc in character.laptop.documents:
            doc_path = laptop_folder / "documents" / f"{doc['name']}"
            doc_path.parent.mkdir(exist_ok=True)
            with open(doc_path, "w") as f:
                f.write(str(doc["content"]))
    
    def load_character(self, character_id: str) -> Character:
        """Load character from disk"""
        char_folder = self.characters_dir / character_id
        
        with open(char_folder / "character.json", "r") as f:
            data = json.load(f)
        
        character = Character.from_dict(data)
        self.active_characters[character_id] = character
        
        return character
    
    def list_characters(self) -> List[Dict[str, str]]:
        """List all saved characters"""
        characters = []
        for char_dir in self.characters_dir.iterdir():
            if char_dir.is_dir():
                try:
                    with open(char_dir / "character.json", "r") as f:
                        data = json.load(f)
                    characters.append({
                        "id": data["id"],
                        "name": data["name"],
                        "specialization": data["specialization"]
                    })
                except:
                    pass
        return characters
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """Get character (load if not in memory)"""
        if character_id in self.active_characters:
            return self.active_characters[character_id]
        
        try:
            return self.load_character(character_id)
        except:
            return None
