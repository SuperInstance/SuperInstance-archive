"""
AI Society Portal - Cultural Transmission System
===============================================
System for AI characters to share knowledge and skills with each other,
enabling cultural evolution and knowledge accumulation across generations.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import random

from memory_system import EnhancedMemorySystem, MemoryType


# ============================================================================
# KNOWLEDGE TYPES AND STRUCTURES
# ============================================================================

class KnowledgeType(Enum):
    """Different types of knowledge that can be transmitted"""
    FACT = "fact"                              # Factual information
    SKILL = "skill"                            # Practical abilities
    PRACTICE = "practice"                      # Cultural practices and norms
    APPROACH = "approach"                      # Problem-solving methods
    TECHNIQUE = "technique"                    # Emotional regulation techniques
    INSIGHT = "insight"                        # Personal insights and wisdom
    STORY = "story"                            # Narratives and experiences


class TransmissionMethod(Enum):
    """Methods of knowledge transmission"""
    DIRECT_TEACHING = "direct_teaching"        # One character explicitly teaches another
    OBSERVATIONAL = "observational"            # Learning by watching others
    ARTIFACT = "artifact"                      # Through created knowledge objects
    SOCIAL = "social"                          # Group interactions and discussions
    DISCOVERY = "discovery"                    # Rediscovering transmitted knowledge


@dataclass
class Knowledge:
    """A unit of knowledge that can be transmitted between characters"""
    id: str
    content: str
    knowledge_type: KnowledgeType
    importance: int  # 1-10 scale

    # Origin and transmission history
    origin_character_id: str
    discovered_at: datetime
    transmission_chain: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    topics: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    emotional_valence: float = 0.0  # -1 to 1

    # Transmission properties
    transmission_difficulty: float = 0.5  # 0-1, how hard to learn
    retention_rate: float = 0.8  # 0-1, how well it's retained
    adaptability: float = 0.7  # 0-1, how easily it can be modified

    # Usage tracking
    times_used: int = 0
    last_used: Optional[datetime] = None
    successful_transmissions: int = 0

    def __post_init__(self):
        if isinstance(self.discovered_at, str):
            self.discovered_at = datetime.fromisoformat(self.discovered_at)
        if isinstance(self.knowledge_type, str):
            self.knowledge_type = KnowledgeType(self.knowledge_type)
        if self.last_used and isinstance(self.last_used, str):
            self.last_used = datetime.fromisoformat(self.last_used)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["discovered_at"] = self.discovered_at.isoformat()
        data["knowledge_type"] = self.knowledge_type.value
        if self.last_used:
            data["last_used"] = self.last_used.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Knowledge':
        """Create from dictionary"""
        return cls(**data)

    def add_transmission_event(self, from_character: str, to_character: str,
                             method: TransmissionMethod, success: bool):
        """Record a transmission event in the chain"""
        event = {
            "from_character": from_character,
            "to_character": to_character,
            "method": method.value,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        self.transmission_chain.append(event)
        if success:
            self.successful_transmissions += 1

    def use(self):
        """Record that this knowledge was used"""
        self.times_used += 1
        self.last_used = datetime.now()

    def get_generation(self) -> int:
        """Get the generation number of this knowledge (0 = original)"""
        return len([t for t in self.transmission_chain if t["success"]])


@dataclass
class CulturalArtifact:
    """A created object that contains knowledge"""
    id: str
    name: str
    description: str
    creator_character_id: str
    created_at: datetime

    # Knowledge content
    embedded_knowledge_ids: List[str] = field(default_factory=list)
    explicit_instructions: str = ""
    implicit_wisdom: str = ""

    # Artifact properties
    artifact_type: str = "document"  # document, art, tool, story, etc.
    accessibility: float = 0.7  # 0-1, how easy to understand
    preservation_quality: float = 0.8  # 0-1, how well knowledge is preserved

    def __post_init__(self):
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CulturalArtifact':
        """Create from dictionary"""
        return cls(**data)


class CulturalTransmissionSystem:
    """Manages cultural knowledge transmission between characters"""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir / "cultural_transmission"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Knowledge storage
        self.knowledge: Dict[str, Knowledge] = {}
        self.artifacts: Dict[str, CulturalArtifact] = {}

        # Character knowledge bases
        self.character_knowledge: Dict[str, Set[str]] = {}  # character_id -> knowledge_ids
        self.character_skills: Dict[str, Set[str]] = {}    # character_id -> skill_knowledge_ids

        # Transmission tracking
        self.transmission_network: Dict[str, Set[str]] = {}  # character_id -> set of characters they learned from
        self.teaching_relationships: Dict[str, List[str]] = {}  # teacher_id -> list of student_ids

        # Cultural evolution metrics
        self.generation_count: Dict[str, int] = {}  # knowledge_id -> max generation
        self.variation_instances: Dict[str, List[str]] = {}  # original_knowledge_id -> variant_ids

        # Load existing data
        self.load_cultural_data()

    def discover_knowledge(self, character_id: str, content: str,
                          knowledge_type: KnowledgeType,
                          importance: int = 5,
                          topics: List[str] = None,
                          context: Dict[str, Any] = None) -> str:
        """Character discovers new knowledge (through insight, learning, etc.)"""

        knowledge_id = hashlib.md5(
            f"{content}_{character_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        knowledge = Knowledge(
            id=knowledge_id,
            content=content,
            knowledge_type=knowledge_type,
            importance=max(1, min(10, importance)),
            origin_character_id=character_id,
            discovered_at=datetime.now(),
            topics=topics or [],
            context=context or {},
            transmission_difficulty=self._calculate_difficulty(knowledge_type, importance),
            retention_rate=self._calculate_retention(knowledge_type, importance),
            adaptability=self._calculate_adaptability(knowledge_type)
        )

        # Store knowledge
        self.knowledge[knowledge_id] = knowledge

        # Give to discovering character
        self._give_knowledge_to_character(character_id, knowledge_id)

        # Save
        self.save_cultural_data()

        return knowledge_id

    def teach_character(self, teacher_id: str, student_id: str,
                       knowledge_id: str, method: TransmissionMethod = TransmissionMethod.DIRECT_TEACHING) -> Dict[str, Any]:
        """Teacher transmits knowledge to student"""

        # Validate inputs
        if knowledge_id not in self.knowledge:
            return {"success": False, "reason": "Knowledge not found"}

        if teacher_id not in self.character_knowledge:
            return {"success": False, "reason": "Teacher doesn't have any knowledge"}

        if knowledge_id not in self.character_knowledge[teacher_id]:
            return {"success": False, "reason": "Teacher doesn't possess this knowledge"}

        knowledge = self.knowledge[knowledge_id]

        # Calculate transmission success based on multiple factors
        success_probability = self._calculate_transmission_success(
            teacher_id, student_id, knowledge, method
        )

        success = random.random() < success_probability

        # Record transmission attempt
        knowledge.add_transmission_event(teacher_id, student_id, method, success)

        if success:
            # Student receives knowledge
            self._give_knowledge_to_character(student_id, knowledge_id)

            # Update teaching relationships
            if teacher_id not in self.teaching_relationships:
                self.teaching_relationships[teacher_id] = []
            if student_id not in self.teaching_relationships[teacher_id]:
                self.teaching_relationships[teacher_id].append(student_id)

            # Update transmission network
            if student_id not in self.transmission_network:
                self.transmission_network[student_id] = set()
            self.transmission_network[student_id].add(teacher_id)

            # Create variation possibility
            if random.random() < knowledge.adaptability:
                variant_id = self._create_knowledge_variant(knowledge_id, student_id)
                self._give_knowledge_to_character(student_id, variant_id)

        # Save changes
        self.save_cultural_data()

        return {
            "success": success,
            "knowledge_id": knowledge_id,
            "method": method.value,
            "success_probability": success_probability,
            "teacher_id": teacher_id,
            "student_id": student_id
        }

    def create_artifact(self, creator_id: str, name: str, description: str,
                       embedded_knowledge_ids: List[str],
                       artifact_type: str = "document",
                       explicit_instructions: str = "",
                       implicit_wisdom: str = "") -> str:
        """Character creates a cultural artifact containing knowledge"""

        # Validate that creator has the knowledge to embed
        if creator_id not in self.character_knowledge:
            return None

        creator_knowledge = self.character_knowledge[creator_id]
        valid_knowledge_ids = [
            kid for kid in embedded_knowledge_ids
            if kid in creator_knowledge and kid in self.knowledge
        ]

        if not valid_knowledge_ids:
            return None

        artifact_id = hashlib.md5(
            f"{name}_{creator_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        artifact = CulturalArtifact(
            id=artifact_id,
            name=name,
            description=description,
            creator_character_id=creator_id,
            created_at=datetime.now(),
            embedded_knowledge_ids=valid_knowledge_ids,
            explicit_instructions=explicit_instructions,
            implicit_wisdom=implicit_wisdom,
            artifact_type=artifact_type,
            accessibility=self._calculate_artifact_accessibility(valid_knowledge_ids),
            preservation_quality=self._calculate_preservation_quality(creator_id, valid_knowledge_ids)
        )

        # Store artifact
        self.artifacts[artifact_id] = artifact

        # Mark embedded knowledge as used
        for kid in valid_knowledge_ids:
            if kid in self.knowledge:
                self.knowledge[kid].use()

        self.save_cultural_data()
        return artifact_id

    def learn_from_artifact(self, character_id: str, artifact_id: str) -> Dict[str, Any]:
        """Character learns from a cultural artifact"""

        if artifact_id not in self.artifacts:
            return {"success": False, "reason": "Artifact not found"}

        artifact = self.artifacts[artifact_id]
        learned_knowledge = []

        for knowledge_id in artifact.embedded_knowledge_ids:
            if knowledge_id not in self.knowledge:
                continue

            knowledge = self.knowledge[knowledge_id]

            # Calculate learning success based on artifact accessibility and knowledge difficulty
            learning_probability = artifact.accessibility * (1 - knowledge.transmission_difficulty)

            if random.random() < learning_probability:
                self._give_knowledge_to_character(character_id, knowledge_id)

                # Record transmission
                knowledge.add_transmission_event(
                    artifact.creator_character_id,
                    character_id,
                    TransmissionMethod.ARTIFACT,
                    True
                )

                learned_knowledge.append(knowledge_id)

        self.save_cultural_data()

        return {
            "success": len(learned_knowledge) > 0,
            "artifact_id": artifact_id,
            "learned_knowledge_ids": learned_knowledge,
            "total_available": len(artifact.embedded_knowledge_ids)
        }

    def group_cultural_transmission(self, character_ids: List[str],
                                 room_id: str = None) -> Dict[str, Any]:
        """Simulate cultural transmission in a group setting"""

        transmission_events = []
        new_knowledge_created = []

        # Find who has knowledge to share
        knowledge_holders = {}
        for char_id in character_ids:
            if char_id in self.character_knowledge:
                for knowledge_id in self.character_knowledge[char_id]:
                    if knowledge_id not in knowledge_holders:
                        knowledge_holders[knowledge_id] = []
                    knowledge_holders[knowledge_id].append(char_id)

        # For each piece of knowledge, see who learns it
        for knowledge_id, holders in knowledge_holders.items():
            if len(holders) == len(character_ids):
                continue  # Everyone already has it

            knowledge = self.knowledge[knowledge_id]
            non_holders = [cid for cid in character_ids if cid not in holders]

            for holder_id in holders:
                for learner_id in non_holders:
                    # Social transmission with moderate success rate
                    success_prob = 0.6 * (1 - knowledge.transmission_difficulty)

                    if random.random() < success_prob:
                        self._give_knowledge_to_character(learner_id, knowledge_id)

                        knowledge.add_transmission_event(
                            holder_id, learner_id,
                            TransmissionMethod.SOCIAL, True
                        )

                        transmission_events.append({
                            "from": holder_id,
                            "to": learner_id,
                            "knowledge": knowledge_id,
                            "method": "social"
                        })

                        # Update transmission network
                        if learner_id not in self.transmission_network:
                            self.transmission_network[learner_id] = set()
                        self.transmission_network[learner_id].add(holder_id)

        # Occasionally create new insights through group interaction
        if random.random() < 0.2:  # 20% chance
            # Create a new insight based on shared knowledge
            shared_topics = set()
            for char_id in character_ids:
                if char_id in self.character_knowledge:
                    for kid in self.character_knowledge[char_id]:
                        if kid in self.knowledge:
                            shared_topics.update(self.knowledge[kid].topics)

            if shared_topics:
                creator_id = random.choice(character_ids)
                insight_content = f"Group insight about {', '.join(list(shared_topics)[:3])}"

                new_knowledge_id = self.discover_knowledge(
                    creator_id, insight_content,
                    KnowledgeType.INSIGHT,
                    importance=6,
                    topics=list(shared_topics),
                    context={"source": "group_interaction", "room_id": room_id}
                )

                new_knowledge_created.append(new_knowledge_id)

                # Give insight to all participants
                for char_id in character_ids:
                    self._give_knowledge_to_character(char_id, new_knowledge_id)

        self.save_cultural_data()

        return {
            "transmission_events": transmission_events,
            "new_knowledge_created": new_knowledge_created,
            "participants": character_ids
        }

    def get_character_knowledge(self, character_id: str,
                              knowledge_type: Optional[KnowledgeType] = None) -> List[Dict[str, Any]]:
        """Get all knowledge possessed by a character"""

        if character_id not in self.character_knowledge:
            return []

        knowledge_ids = self.character_knowledge[character_id]
        character_knowledge = []

        for kid in knowledge_ids:
            if kid in self.knowledge:
                knowledge = self.knowledge[kid]

                if knowledge_type is None or knowledge.knowledge_type == knowledge_type:
                    knowledge_dict = knowledge.to_dict()
                    knowledge_dict["possession_since"] = self._get_possession_since(character_id, kid)
                    character_knowledge.append(knowledge_dict)

        # Sort by importance and then by acquisition time
        character_knowledge.sort(key=lambda k: (-k["importance"], k["possession_since"]))

        return character_knowledge

    def get_transmission_history(self, knowledge_id: str) -> List[Dict[str, Any]]:
        """Get the transmission history of a piece of knowledge"""

        if knowledge_id not in self.knowledge:
            return []

        return self.knowledge[knowledge_id].transmission_chain

    def get_cultural_stats(self) -> Dict[str, Any]:
        """Get statistics about cultural transmission"""

        total_knowledge = len(self.knowledge)
        total_artifacts = len(self.artifacts)
        total_characters = len(self.character_knowledge)

        # Knowledge distribution
        knowledge_by_type = {}
        for knowledge in self.knowledge.values():
            ktype = knowledge.knowledge_type.value
            knowledge_by_type[ktype] = knowledge_by_type.get(ktype, 0) + 1

        # Transmission network stats
        avg_connections = 0
        if self.transmission_network:
            connections = [len(conns) for conns in self.transmission_network.values()]
            avg_connections = sum(connections) / len(connections) if connections else 0

        # Generation tracking
        max_generation = 0
        if self.knowledge:
            max_generation = max(k.get_generation() for k in self.knowledge.values())

        return {
            "total_knowledge": total_knowledge,
            "total_artifacts": total_artifacts,
            "knowledgeable_characters": total_characters,
            "knowledge_by_type": knowledge_by_type,
            "average_connections": avg_connections,
            "max_generation": max_generation,
            "total_transmissions": sum(len(k.transmission_chain) for k in self.knowledge.values()),
            "successful_transmissions": sum(k.successful_transmissions for k in self.knowledge.values())
        }

    # ==========================================================================
    # PRIVATE HELPER METHODS
    # ==========================================================================

    def _give_knowledge_to_character(self, character_id: str, knowledge_id: str):
        """Give knowledge to a character"""
        if character_id not in self.character_knowledge:
            self.character_knowledge[character_id] = set()

        self.character_knowledge[character_id].add(knowledge_id)

        # Track skills separately
        if knowledge_id in self.knowledge:
            knowledge = self.knowledge[knowledge_id]
            if knowledge.knowledge_type == KnowledgeType.SKILL:
                if character_id not in self.character_skills:
                    self.character_skills[character_id] = set()
                self.character_skills[character_id].add(knowledge_id)

    def _calculate_transmission_success(self, teacher_id: str, student_id: str,
                                      knowledge: Knowledge, method: TransmissionMethod) -> float:
        """Calculate probability of successful transmission"""

        base_probability = 0.7  # Base 70% success rate

        # Method modifier
        method_modifiers = {
            TransmissionMethod.DIRECT_TEACHING: 1.0,
            TransmissionMethod.OBSERVATIONAL: 0.7,
            TransmissionMethod.ARTIFACT: 0.8,
            TransmissionMethod.SOCIAL: 0.6,
            TransmissionMethod.DISCOVERY: 0.4
        }

        method_modifier = method_modifiers.get(method, 0.5)

        # Difficulty modifier
        difficulty_modifier = 1 - knowledge.transmission_difficulty

        # Retention modifier
        retention_modifier = knowledge.retention_rate

        # Teaching experience bonus (has this character taught before?)
        teaching_bonus = 0.1 if teacher_id in self.teaching_relationships else 0.0

        # Learning experience bonus (has this character learned from others?)
        learning_bonus = 0.05 if student_id in self.transmission_network else 0.0

        success_probability = (base_probability *
                             method_modifier *
                             difficulty_modifier *
                             retention_modifier +
                             teaching_bonus +
                             learning_bonus)

        return min(0.95, max(0.1, success_probability))  # Clamp between 10% and 95%

    def _calculate_difficulty(self, knowledge_type: KnowledgeType, importance: int) -> float:
        """Calculate transmission difficulty based on type and importance"""

        type_difficulties = {
            KnowledgeType.FACT: 0.3,          # Easy to transmit
            KnowledgeType.STORY: 0.4,         # Relatively easy
            KnowledgeType.TECHNIQUE: 0.5,     # Moderate
            KnowledgeType.APPROACH: 0.6,      # Moderate-hard
            KnowledgeType.INSIGHT: 0.7,       # Hard to transmit
            KnowledgeType.PRACTICE: 0.8,      # Very hard (requires experience)
            KnowledgeType.SKILL: 0.9          # Hardest (requires practice)
        }

        base_difficulty = type_difficulties.get(knowledge_type, 0.5)

        # More important knowledge is slightly harder to transmit (more complex)
        importance_modifier = (importance / 10) * 0.1

        return min(0.95, base_difficulty + importance_modifier)

    def _calculate_retention(self, knowledge_type: KnowledgeType, importance: int) -> float:
        """Calculate how well knowledge is retained"""

        type_retention = {
            KnowledgeType.SKILL: 0.9,         # Skills stick well
            KnowledgeType.PRACTICE: 0.8,      # Practices are retained
            KnowledgeType.INSIGHT: 0.7,       # Insights are memorable
            KnowledgeType.FACT: 0.6,          # Facts can be forgotten
            KnowledgeType.APPROACH: 0.7,      # Approaches are retained
            KnowledgeType.TECHNIQUE: 0.8,     # Techniques stick
            KnowledgeType.STORY: 0.9          # Stories are very memorable
        }

        base_retention = type_retention.get(knowledge_type, 0.7)

        # More important knowledge is retained better
        importance_modifier = (importance / 10) * 0.2

        return min(0.95, base_retention + importance_modifier)

    def _calculate_adaptability(self, knowledge_type: KnowledgeType) -> float:
        """Calculate how easily knowledge can be adapted/modified"""

        type_adaptability = {
            KnowledgeType.APPROACH: 0.9,      # Very adaptable
            KnowledgeType.TECHNIQUE: 0.8,     # Can be adapted
            KnowledgeType.INSIGHT: 0.7,       # Can inspire new insights
            KnowledgeType.STORY: 0.6,         # Stories can be retold
            KnowledgeType.FACT: 0.3,          # Facts don't change much
            KnowledgeType.SKILL: 0.4,         # Skills have core elements
            KnowledgeType.PRACTICE: 0.5       # Practices can evolve
        }

        return type_adaptability.get(knowledge_type, 0.6)

    def _calculate_artifact_accessibility(self, knowledge_ids: List[str]) -> float:
        """Calculate how accessible an artifact's knowledge is"""
        if not knowledge_ids:
            return 0.5

        total_difficulty = 0
        for kid in knowledge_ids:
            if kid in self.knowledge:
                total_difficulty += self.knowledge[kid].transmission_difficulty

        avg_difficulty = total_difficulty / len(knowledge_ids)
        return max(0.1, 1 - avg_difficulty)

    def _calculate_preservation_quality(self, creator_id: str, knowledge_ids: List[str]) -> float:
        """Calculate how well knowledge is preserved in artifact"""
        base_quality = 0.8

        # Creator's expertise with the knowledge matters
        creator_expertise = 0
        if creator_id in self.character_skills:
            creator_expertise = len(self.character_skills[creator_id] & set(knowledge_ids))

        expertise_bonus = min(0.2, creator_expertise * 0.1)

        return min(0.95, base_quality + expertise_bonus)

    def _create_knowledge_variant(self, original_id: str, adapter_id: str) -> str:
        """Create a variant of existing knowledge through adaptation"""

        if original_id not in self.knowledge:
            return original_id  # Return original if can't create variant

        original = self.knowledge[original_id]

        variant_id = hashlib.md5(
            f"variant_{original_id}_{adapter_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Create variant with slightly modified content
        variant_content = f"Adapted version: {original.content}"
        if original.knowledge_type == KnowledgeType.APPROACH:
            variant_content = f"Personal approach based on: {original.content}"
        elif original.knowledge_type == KnowledgeType.TECHNIQUE:
            variant_content = f"Modified technique derived from: {original.content}"

        variant = Knowledge(
            id=variant_id,
            content=variant_content,
            knowledge_type=original.knowledge_type,
            importance=original.importance,
            origin_character_id=adapter_id,
            discovered_at=datetime.now(),
            topics=original.topics.copy(),
            context={**original.context, "variant_of": original_id, "adapter": adapter_id},
            transmission_difficulty=original.transmission_difficulty * 0.9,  # Slightly easier
            retention_rate=original.retention_rate * 1.1,  # Better retention (personal connection)
            adaptability=min(0.95, original.adaptability * 1.2)  # More adaptable
        )

        # Store variant
        self.knowledge[variant_id] = variant

        # Track variation
        if original_id not in self.variation_instances:
            self.variation_instances[original_id] = []
        self.variation_instances[original_id].append(variant_id)

        return variant_id

    def _get_possession_since(self, character_id: str, knowledge_id: str) -> str:
        """Get when character acquired knowledge"""
        if knowledge_id not in self.knowledge:
            return datetime.now().isoformat()

        knowledge = self.knowledge[knowledge_id]

        # Find first transmission event where this character received the knowledge
        for event in knowledge.transmission_chain:
            if event["to_character"] == character_id and event["success"]:
                return event["timestamp"]

        # If no transmission found, assume origin character
        if knowledge.origin_character_id == character_id:
            return knowledge.discovered_at.isoformat()

        # Default to now
        return datetime.now().isoformat()

    def save_cultural_data(self):
        """Save all cultural transmission data to disk"""
        try:
            # Save knowledge
            knowledge_file = self.storage_dir / "knowledge.json"
            knowledge_data = {
                "knowledge": [k.to_dict() for k in self.knowledge.values()],
                "last_saved": datetime.now().isoformat()
            }

            with open(knowledge_file, "w") as f:
                json.dump(knowledge_data, f, indent=2)

            # Save artifacts
            artifacts_file = self.storage_dir / "artifacts.json"
            artifacts_data = {
                "artifacts": [a.to_dict() for a in self.artifacts.values()],
                "last_saved": datetime.now().isoformat()
            }

            with open(artifacts_file, "w") as f:
                json.dump(artifacts_data, f, indent=2)

            # Save character knowledge mappings
            character_knowledge_file = self.storage_dir / "character_knowledge.json"
            character_knowledge_data = {
                "character_knowledge": {k: list(v) for k, v in self.character_knowledge.items()},
                "character_skills": {k: list(v) for k, v in self.character_skills.items()},
                "transmission_network": {k: list(v) for k, v in self.transmission_network.items()},
                "teaching_relationships": self.teaching_relationships,
                "last_saved": datetime.now().isoformat()
            }

            with open(character_knowledge_file, "w") as f:
                json.dump(character_knowledge_data, f, indent=2)

            # Save metadata
            metadata_file = self.storage_dir / "metadata.json"
            metadata_data = {
                "generation_count": self.generation_count,
                "variation_instances": self.variation_instances,
                "last_saved": datetime.now().isoformat()
            }

            with open(metadata_file, "w") as f:
                json.dump(metadata_data, f, indent=2)

        except Exception as e:
            print(f"[CULTURAL] Error saving cultural data: {e}")

    def load_cultural_data(self):
        """Load cultural transmission data from disk"""
        try:
            # Load knowledge
            knowledge_file = self.storage_dir / "knowledge.json"
            if knowledge_file.exists():
                with open(knowledge_file, "r") as f:
                    knowledge_data = json.load(f)

                for knowledge_dict in knowledge_data.get("knowledge", []):
                    knowledge = Knowledge.from_dict(knowledge_dict)
                    self.knowledge[knowledge.id] = knowledge

            # Load artifacts
            artifacts_file = self.storage_dir / "artifacts.json"
            if artifacts_file.exists():
                with open(artifacts_file, "r") as f:
                    artifacts_data = json.load(f)

                for artifact_dict in artifacts_data.get("artifacts", []):
                    artifact = CulturalArtifact.from_dict(artifact_dict)
                    self.artifacts[artifact.id] = artifact

            # Load character knowledge mappings
            character_knowledge_file = self.storage_dir / "character_knowledge.json"
            if character_knowledge_file.exists():
                with open(character_knowledge_file, "r") as f:
                    character_knowledge_data = json.load(f)

                self.character_knowledge = {
                    k: set(v) for k, v in character_knowledge_data.get("character_knowledge", {}).items()
                }
                self.character_skills = {
                    k: set(v) for k, v in character_knowledge_data.get("character_skills", {}).items()
                }
                self.transmission_network = {
                    k: set(v) for k, v in character_knowledge_data.get("transmission_network", {}).items()
                }
                self.teaching_relationships = character_knowledge_data.get("teaching_relationships", {})

            # Load metadata
            metadata_file = self.storage_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata_data = json.load(f)

                self.generation_count = metadata_data.get("generation_count", {})
                self.variation_instances = metadata_data.get("variation_instances", {})

            print(f"[CULTURAL] Loaded {len(self.knowledge)} knowledge items and {len(self.artifacts)} artifacts")

        except Exception as e:
            print(f"[CULTURAL] Error loading cultural data: {e}")