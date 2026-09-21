"""
AI Society Portal - FastAPI Backend
====================================
REST API and WebSocket server for the web portal
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
import json
from datetime import datetime
import decimal

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from orchestration_engine import AISocietyOrchestrator, ConversationTurn
from room_system import RoomType
from character_system import CharacterState
from memory_system import MemoryType
from cultural_transmission import (
    CulturalTransmissionSystem, KnowledgeType, TransmissionMethod,
    Knowledge, CulturalArtifact
)
from skill_system import (
    SkillSystem, SkillType, SkillCategory, SkillLevel,
    get_available_skills, recommend_starter_skills
)
from autobiographical_memory import (
    AutobiographicalMemorySystem, NarrativeTheme, IdentityAspect, ReflectionType
)


# ============================================================================
# CUSTOM JSON ENCODER
# ============================================================================
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        return super().default(obj)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CreateCharacterRequest(BaseModel):
    name: str
    specialization: str
    backstory: str
    personality: Optional[Dict[str, float]] = None
    skills: Optional[List[str]] = None
    goals: Optional[List[str]] = None
    storage_size_mb: Optional[int] = 100


class CreateRoomRequest(BaseModel):
    name: str
    room_type: str  # Will be converted to RoomType enum
    purpose: Optional[str] = ""
    max_characters: Optional[int] = 10
    conversation_pace_seconds: Optional[float] = 3.0
    objects_in_room: Optional[List[Dict[str, Any]]] = None
    background_media: Optional[List[Dict[str, Any]]] = None


class StartSessionRequest(BaseModel):
    duration_minutes: Optional[int] = None
    rounds: Optional[int] = None


class AddCharacterToRoomRequest(BaseModel):
    character_id: str
    room_id: str


class InjectMessageRequest(BaseModel):
    message: str
    sender: Optional[str] = "Moderator"


class NaturalLanguageRequest(BaseModel):
    message: str


class AddMemoryRequest(BaseModel):
    content: str
    memory_type: str = "experience"  # conversational, learning, relationship, self_reflection, experience, emotional
    importance: int = 5  # 1-10 scale
    context: Optional[Dict[str, Any]] = None
    related_characters: Optional[List[str]] = None
    topics: Optional[List[str]] = None
    emotional_valence: float = 0.0  # -1 to 1


class SearchMemoriesRequest(BaseModel):
    query: str
    limit: int = 20


class GetMemoriesRequest(BaseModel):
    limit: int = 50
    memory_type: Optional[str] = None
    related_character: Optional[str] = None
    topic: Optional[str] = None
    min_importance: int = 1
    sort_by: str = "retrieval_score"  # retrieval_score, importance, recent


class TeachCharacterRequest(BaseModel):
    target_character_id: str
    knowledge_id: str
    method: str = "direct_teaching"  # direct_teaching, observational, artifact, social, discovery


class DiscoverKnowledgeRequest(BaseModel):
    content: str
    knowledge_type: str  # fact, skill, practice, approach, technique, insight, story
    importance: int = 5
    topics: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class CreateArtifactRequest(BaseModel):
    name: str
    description: str
    embedded_knowledge_ids: List[str]
    artifact_type: str = "document"
    explicit_instructions: str = ""
    implicit_wisdom: str = ""


class LearnFromArtifactRequest(BaseModel):
    artifact_id: str


class GroupCulturalTransmissionRequest(BaseModel):
    character_ids: List[str]
    room_id: Optional[str] = None


class GetCharacterKnowledgeRequest(BaseModel):
    knowledge_type: Optional[str] = None


# ============================================================================
# SKILL SYSTEM PYDANTIC MODELS
# ============================================================================

class PracticeSkillRequest(BaseModel):
    skill_type: str
    difficulty: float = 0.5  # 0.0 (easy) to 1.0 (very hard)
    duration_minutes: int = 30


class AddSkillRequest(BaseModel):
    skill_type: str
    learning_rate: float = 1.0
    plateau_resistance: float = 1.0


class SkillWorkshopRequest(BaseModel):
    character_ids: List[str]
    skill_type: str
    duration_minutes: int = 60


# ============================================================================
# AUTOBIOGRAPHICAL MEMORY PYDANTIC MODELS
# ============================================================================

class TriggerSelfReflectionRequest(BaseModel):
    reflection_type: Optional[str] = None  # periodic_review, milestone_reflection, identity_crises, growth_reflection, relationship_reflection, future_planning
    focus_area: Optional[str] = None


class GetLifeStoryRequest(BaseModel):
    detail_level: str = "summary"  # summary, detailed, comprehensive


class UpdateIdentityAspectRequest(BaseModel):
    aspect: str  # professional_identity, social_identity, personal_values, core_beliefs, self_concept, life_goals, communication_style, worldview
    new_expression: Optional[str] = None
    core_value: Optional[str] = None


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(title="AI Society Portal API", version="1.0.0")

# CORS middleware for web frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = AISocietyOrchestrator()

# Initialize cultural transmission system
from pathlib import Path
cultural_system = CulturalTransmissionSystem(Path("ai_society_data") / "cultural_transmission")

# Initialize skill system
skill_system = SkillSystem(Path("ai_society_data") / "skills")

# Initialize consciousness metrics system
from consciousness_metrics import (
    ConsciousnessMetricsSystem, ConsciousnessIndicator,
    sleep_consolidation, get_dashboard_data
)

# Initialize cultural ratchet system
from cultural_ratchet import (
    CulturalRatchetSystem, RatchetType, TransmissionFidelity,
    simulate_cultural_evolution
)
cultural_ratchet = CulturalRatchetSystem(Path("ai_society_data") / "cultural_ratchet")

# WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {}


# ============================================================================
# CHARACTER ENDPOINTS
# ============================================================================

@app.post("/characters")
async def create_character(request: CreateCharacterRequest):
    """Create a new character with automatic skill assignment"""
    try:
        character = orchestrator.create_character(
            name=request.name,
            specialization=request.specialization,
            backstory=request.backstory,
            personality=request.personality or {},
            skills=request.skills or [],
            current_goals=request.goals or []
        )

        # Set storage size
        if request.storage_size_mb:
            character.laptop.storage_size_mb = request.storage_size_mb

        # Automatically add recommended skills based on specialization
        recommended_skills = recommend_starter_skills(character.specialization)
        added_skills = []

        for skill_type in recommended_skills:
            skill = skill_system.add_skill(character.id, skill_type)
            added_skills.append({
                "skill_type": skill_type.value,
                "category": skill.category.value,
                "level": skill.skill_level.value
            })

        # Save character and skills
        orchestrator.character_manager.save_character(character)
        skill_system.save_to_disk()

        # Add memory about character creation with skills
        character.add_memory(
            content=f"Created as {character.specialization} with initial skills: {', '.join([s['skill_type'] for s in added_skills])}",
            memory_type=MemoryType.SELF_REFLECTION,
            importance=7,
            topics=["character_creation", "skill_development"],
            context={"source": "character_creation", "skills_added": len(added_skills)}
        )

        orchestrator.character_manager.save_character(character)

        return {
            "id": character.id,
            "name": character.name,
            "specialization": character.specialization,
            "message": "Character created successfully with starter skills",
            "added_skills": added_skills,
            "total_skills": len(added_skills)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters")
async def list_characters():
    """List all characters"""
    try:
        characters = orchestrator.character_manager.list_characters()
        return {"characters": characters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    """Get character details"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        return character.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/work-at-home")
async def character_work_at_home(character_id: str, 
                                duration_minutes: int = 60,
                                background_tasks: BackgroundTasks = None):
    """Have character work at home"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")
        
        # Run in background
        if background_tasks:
            background_tasks.add_task(
                orchestrator.conversation_engine.character_work_at_home,
                character_id,
                duration_minutes
            )
            return {"message": "Character started working at home"}
        else:
            work_log = await orchestrator.conversation_engine.character_work_at_home(
                character_id, duration_minutes
            )
            return work_log
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MEMORY ENDPOINTS
# ============================================================================

@app.get("/characters/{character_id}/memories")
async def get_character_memories(character_id: str,
                               limit: int = 50,
                               memory_type: Optional[str] = None,
                               related_character: Optional[str] = None,
                               topic: Optional[str] = None,
                               min_importance: int = 1,
                               sort_by: str = "retrieval_score"):
    """Get character memories with optional filters"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Check if character has enhanced memory system
        if not isinstance(character.memory, type(orchestrator.character_manager.get_character(character_id).memory if orchestrator.character_manager.get_character(character_id) else None)):
            # Try to get character again to check memory type
            character = orchestrator.character_manager.get_character(character_id)

        if not isinstance(character.memory, type(character.memory)):
            # If we can't determine the memory type, return a simple response
            return {
                "character_id": character_id,
                "memories": [],
                "message": "Character does not have enhanced memory system enabled",
                "memory_stats": {}
            }

        # Import here to avoid circular imports
        from memory_system import EnhancedMemorySystem

        if not isinstance(character.memory, EnhancedMemorySystem):
            return {
                "character_id": character_id,
                "memories": [],
                "message": "Character does not have enhanced memory system enabled",
                "memory_stats": {}
            }

        # Parse memory type if provided
        parsed_memory_type = None
        if memory_type:
            try:
                parsed_memory_type = MemoryType(memory_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid memory_type. Must be one of: {[mt.value for mt in MemoryType]}"
                )

        # Get memories
        memories = character.memory.get_memories(
            limit=limit,
            memory_type=parsed_memory_type,
            related_character=related_character,
            topic=topic,
            min_importance=min_importance,
            sort_by=sort_by
        )

        # Convert to dictionary format
        memories_data = [memory.to_dict() for memory in memories]

        return {
            "character_id": character_id,
            "memories": memories_data,
            "memory_stats": character.memory.get_memory_stats()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/memories")
async def add_character_memory(character_id: str, request: AddMemoryRequest):
    """Add a new memory to a character"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate importance
        if not 1 <= request.importance <= 10:
            raise HTTPException(status_code=400, detail="Importance must be between 1 and 10")

        # Validate emotional valence
        if not -1 <= request.emotional_valence <= 1:
            raise HTTPException(status_code=400, detail="Emotional valence must be between -1 and 1")

        # Validate memory type
        try:
            memory_type_enum = MemoryType(request.memory_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid memory_type. Must be one of: {[mt.value for mt in MemoryType]}"
            )

        # Add memory using character's method
        memory_id = character.add_memory(
            content=request.content,
            memory_type=memory_type_enum,
            importance=request.importance,
            context=request.context or {},
            related_characters=request.related_characters or [],
            topics=request.topics or [],
            emotional_valence=request.emotional_valence
        )

        if memory_id is None:
            raise HTTPException(
                status_code=400,
                detail="Character does not have enhanced memory system enabled"
            )

        # Save character to ensure persistence
        orchestrator.character_manager.save_character(character)

        return {
            "message": "Memory added successfully",
            "memory_id": memory_id,
            "character_id": character_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/memories/search")
async def search_character_memories(character_id: str, request: SearchMemoriesRequest):
    """Search character memories by content"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Import here to avoid circular imports
        from memory_system import EnhancedMemorySystem

        if not isinstance(character.memory, EnhancedMemorySystem):
            return {
                "character_id": character_id,
                "query": request.query,
                "results": [],
                "message": "Character does not have enhanced memory system enabled"
            }

        # Search memories
        results = character.memory.search_memories(request.query, request.limit)

        # Convert to dictionary format
        results_data = []
        for result in results:
            memory_dict = result["memory"].to_dict()
            memory_dict["relevance"] = result["relevance"]
            memory_dict["retrieval_score"] = result["retrieval_score"]
            results_data.append(memory_dict)

        return {
            "character_id": character_id,
            "query": request.query,
            "results": results_data,
            "total_found": len(results_data)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/memories/stats")
async def get_character_memory_stats(character_id: str):
    """Get memory statistics for a character"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Import here to avoid circular imports
        from memory_system import EnhancedMemorySystem

        if not isinstance(character.memory, EnhancedMemorySystem):
            return {
                "character_id": character_id,
                "message": "Character does not have enhanced memory system enabled",
                "stats": {}
            }

        stats = character.memory.get_memory_stats()

        return {
            "character_id": character_id,
            "stats": stats
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/memories/consolidate")
async def consolidate_character_memories(character_id: str):
    """Force consolidation of working memory into long-term storage"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Import here to avoid circular imports
        from memory_system import EnhancedMemorySystem

        if not isinstance(character.memory, EnhancedMemorySystem):
            raise HTTPException(
                status_code=400,
                detail="Character does not have enhanced memory system enabled"
            )

        # Force consolidation
        character.memory.force_memory_consolidation()

        # Save character
        orchestrator.character_manager.save_character(character)

        return {
            "message": "Memory consolidation completed",
            "character_id": character_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CULTURAL TRANSMISSION ENDPOINTS
# ============================================================================

@app.post("/characters/{character_id}/discover-knowledge")
async def character_discovers_knowledge(character_id: str, request: DiscoverKnowledgeRequest):
    """Character discovers new knowledge through insight or learning"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate knowledge type
        try:
            knowledge_type_enum = KnowledgeType(request.knowledge_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid knowledge_type. Must be one of: {[kt.value for kt in KnowledgeType]}"
            )

        # Validate importance
        if not 1 <= request.importance <= 10:
            raise HTTPException(status_code=400, detail="Importance must be between 1 and 10")

        # Discover knowledge
        knowledge_id = cultural_system.discover_knowledge(
            character_id=character_id,
            content=request.content,
            knowledge_type=knowledge_type_enum,
            importance=request.importance,
            topics=request.topics or [],
            context=request.context or {}
        )

        # Add memory about discovery
        character.add_memory(
            content=f"Discovered new knowledge: {request.content}",
            memory_type=MemoryType.LEARNING,
            importance=request.importance,
            topics=request.topics,
            context={"source": "knowledge_discovery", "knowledge_id": knowledge_id}
        )

        # Save character
        orchestrator.character_manager.save_character(character)

        return {
            "message": "Knowledge discovered successfully",
            "knowledge_id": knowledge_id,
            "character_id": character_id,
            "knowledge_type": request.knowledge_type
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/teach")
async def character_teaches(character_id: str, request: TeachCharacterRequest):
    """Character teaches another character"""
    try:
        teacher = orchestrator.character_manager.get_character(character_id)
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher character not found")

        student = orchestrator.character_manager.get_character(request.target_character_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student character not found")

        # Validate transmission method
        try:
            method_enum = TransmissionMethod(request.method)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid method. Must be one of: {[tm.value for tm in TransmissionMethod]}"
            )

        # Perform teaching
        result = cultural_system.teach_character(
            teacher_id=character_id,
            student_id=request.target_character_id,
            knowledge_id=request.knowledge_id,
            method=method_enum
        )

        # Add memories for both participants
        teaching_memory = f"Taught {student.name}: {result.get('knowledge_id', 'unknown knowledge')}"
        teacher.add_memory(
            content=teaching_memory,
            memory_type=MemoryType.EXPERIENCE,
            importance=6,
            related_characters=[request.target_character_id],
            context={"source": "teaching", "success": result["success"]}
        )

        if result["success"]:
            learning_memory = f"Learned from {teacher.name}: {result.get('knowledge_id', 'unknown knowledge')}"
            student.add_memory(
                content=learning_memory,
                memory_type=MemoryType.LEARNING,
                importance=7,
                related_characters=[character_id],
                context={"source": "learning", "method": request.method}
            )

        # Save both characters
        orchestrator.character_manager.save_character(teacher)
        orchestrator.character_manager.save_character(student)

        return {
            "message": "Teaching attempt completed",
            "result": result,
            "teacher_id": character_id,
            "student_id": request.target_character_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/knowledge")
async def get_character_knowledge(character_id: str, request: GetCharacterKnowledgeRequest = None):
    """Get character's knowledge base"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Parse knowledge type if provided
        knowledge_type = None
        if request and request.knowledge_type:
            try:
                knowledge_type = KnowledgeType(request.knowledge_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid knowledge_type. Must be one of: {[kt.value for kt in KnowledgeType]}"
                )

        # Get character knowledge
        character_knowledge = cultural_system.get_character_knowledge(
            character_id=character_id,
            knowledge_type=knowledge_type
        )

        return {
            "character_id": character_id,
            "knowledge": character_knowledge,
            "total_knowledge_items": len(character_knowledge)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/create-artifact")
async def character_creates_artifact(character_id: str, request: CreateArtifactRequest):
    """Character creates a cultural artifact containing knowledge"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Create artifact
        artifact_id = cultural_system.create_artifact(
            creator_id=character_id,
            name=request.name,
            description=request.description,
            embedded_knowledge_ids=request.embedded_knowledge_ids,
            artifact_type=request.artifact_type,
            explicit_instructions=request.explicit_instructions,
            implicit_wisdom=request.implicit_wisdom
        )

        if artifact_id is None:
            raise HTTPException(
                status_code=400,
                detail="Character doesn't possess the required knowledge to create this artifact"
            )

        # Add memory about artifact creation
        character.add_memory(
            content=f"Created artifact '{request.name}' containing knowledge",
            memory_type=MemoryType.EXPERIENCE,
            importance=6,
            topics=["artifact_creation", request.artifact_type],
            context={"source": "artifact_creation", "artifact_id": artifact_id}
        )

        # Save character
        orchestrator.character_manager.save_character(character)

        return {
            "message": "Artifact created successfully",
            "artifact_id": artifact_id,
            "character_id": character_id,
            "artifact_name": request.name
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/learn-from-artifact")
async def character_learns_from_artifact(character_id: str, request: LearnFromArtifactRequest):
    """Character learns from a cultural artifact"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Learn from artifact
        result = cultural_system.learn_from_artifact(
            character_id=character_id,
            artifact_id=request.artifact_id
        )

        if result["success"]:
            # Add memory about learning from artifact
            character.add_memory(
                content=f"Learned {len(result['learned_knowledge_ids'])} items from artifact",
                memory_type=MemoryType.LEARNING,
                importance=5,
                topics=["artifact_learning"],
                context={"source": "artifact_learning", "artifact_id": request.artifact_id}
            )

            # Save character
            orchestrator.character_manager.save_character(character)

        return {
            "message": "Artifact learning attempt completed",
            "result": result,
            "character_id": character_id,
            "artifact_id": request.artifact_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/cultural-transmission")
async def room_cultural_transmission(room_id: str, request: GroupCulturalTransmissionRequest):
    """Simulate cultural transmission in a group setting"""
    try:
        room = orchestrator.room_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Validate that all characters exist
        characters = []
        for char_id in request.character_ids:
            character = orchestrator.character_manager.get_character(char_id)
            if character:
                characters.append(character)
            else:
                raise HTTPException(status_code=404, detail=f"Character {char_id} not found")

        if len(characters) < 2:
            raise HTTPException(status_code=400, detail="At least 2 characters required for cultural transmission")

        # Perform group cultural transmission
        result = cultural_system.group_cultural_transmission(
            character_ids=request.character_ids,
            room_id=room_id
        )

        # Add memories for participants about the cultural exchange
        for character in characters:
            num_transmissions = len(result["transmission_events"])
            num_new_insights = len(result["new_knowledge_created"])

            memory_content = f"Participated in cultural exchange with {len(characters)-1} others"
            if num_transmissions > 0:
                memory_content += f", {num_transmissions} knowledge items shared"
            if num_new_insights > 0:
                memory_content += f", {num_new_insights} new insights created"

            character.add_memory(
                content=memory_content,
                memory_type=MemoryType.EXPERIENCE,
                importance=5,
                related_characters=[c.id for c in characters if c.id != character.id],
                context={"source": "group_cultural_transmission", "room_id": room_id}
            )

            # Save character
            orchestrator.character_manager.save_character(character)

        return {
            "message": "Group cultural transmission completed",
            "room_id": room_id,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cultural-transmission/knowledge/{knowledge_id}/history")
async def get_knowledge_transmission_history(knowledge_id: str):
    """Get the transmission history of a piece of knowledge"""
    try:
        history = cultural_system.get_transmission_history(knowledge_id)

        if not history:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        return {
            "knowledge_id": knowledge_id,
            "transmission_history": history,
            "total_transmissions": len(history)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cultural-transmission/stats")
async def get_cultural_transmission_stats():
    """Get cultural transmission system statistics"""
    try:
        stats = cultural_system.get_cultural_stats()

        return {
            "message": "Cultural transmission statistics",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SKILL SYSTEM ENDPOINTS
# ============================================================================

@app.get("/skills/available")
async def get_available_skills_endpoint():
    """Get all available skills grouped by category"""
    try:
        available_skills = get_available_skills()
        return {
            "skills_by_category": available_skills,
            "total_skills": sum(len(skills) for skills in available_skills.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/skills/recommendations/{specialization}")
async def get_skill_recommendations(specialization: str):
    """Get recommended starter skills based on specialization"""
    try:
        recommended_skills = recommend_starter_skills(specialization)
        return {
            "specialization": specialization,
            "recommended_skills": [skill.value for skill in recommended_skills]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/skills")
async def get_character_skills(character_id: str):
    """Get all skills for a character"""
    try:
        # Verify character exists
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        skills_overview = skill_system.get_all_skills_overview(character_id)
        return skills_overview
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/skills/{skill_type}")
async def get_character_skill(character_id: str, skill_type: str):
    """Get detailed progress for a specific skill"""
    try:
        # Verify character exists
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate skill type
        try:
            skill_enum = SkillType(skill_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skill_type. Must be one of: {[st.value for st in SkillType]}"
            )

        skill_progress = skill_system.get_skill_progress(character_id, skill_enum)
        return skill_progress
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/skills")
async def add_character_skill(character_id: str, request: AddSkillRequest):
    """Add a new skill for a character"""
    try:
        # Verify character exists
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate skill type
        try:
            skill_enum = SkillType(request.skill_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skill_type. Must be one of: {[st.value for st in SkillType]}"
            )

        # Validate parameters
        if not 0.1 <= request.learning_rate <= 3.0:
            raise HTTPException(status_code=400, detail="learning_rate must be between 0.1 and 3.0")
        if not 0.1 <= request.plateau_resistance <= 3.0:
            raise HTTPException(status_code=400, detail="plateau_resistance must be between 0.1 and 3.0")

        # Add the skill
        skill = skill_system.add_skill(
            character_id=character_id,
            skill_type=skill_enum,
            learning_rate=request.learning_rate,
            plateau_resistance=request.plateau_resistance
        )

        # Save skill system data
        skill_system.save_to_disk()

        # Add memory about learning new skill
        character.add_memory(
            content=f"Started learning new skill: {request.skill_type}",
            memory_type=MemoryType.LEARNING,
            importance=5,
            topics=["skill_development", request.skill_type],
            context={"source": "skill_acquisition", "skill_type": request.skill_type}
        )

        # Save character
        orchestrator.character_manager.save_character(character)

        return {
            "message": "Skill added successfully",
            "character_id": character_id,
            "skill": skill.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/practice/{skill_type}")
async def practice_character_skill(character_id: str, skill_type: str, request: PracticeSkillRequest):
    """Have a character practice a skill"""
    try:
        # Verify character exists
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate skill type
        try:
            skill_enum = SkillType(skill_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skill_type. Must be one of: {[st.value for st in SkillType]}"
            )

        # Validate parameters
        if not 0.0 <= request.difficulty <= 1.0:
            raise HTTPException(status_code=400, detail="difficulty must be between 0.0 and 1.0")
        if request.duration_minutes < 5 or request.duration_minutes > 240:
            raise HTTPException(status_code=400, detail="duration_minutes must be between 5 and 240")

        # Practice the skill
        practice_result = skill_system.practice_skill(
            character_id=character_id,
            skill_type=skill_enum,
            difficulty=request.difficulty,
            duration_minutes=request.duration_minutes
        )

        # Save skill system data
        skill_system.save_to_disk()

        # Add memory about practice session
        memory_content = f"Practiced {skill_type} for {request.duration_minutes} minutes"
        if practice_result["session_results"]["breakthrough_achieved"]:
            memory_content += " - ACHIEVED BREAKTHROUGH!"

        character.add_memory(
            content=memory_content,
            memory_type=MemoryType.EXPERIENCE,
            importance=6 if practice_result["session_results"]["breakthrough_achieved"] else 4,
            topics=["skill_practice", skill_type],
            context={
                "source": "skill_practice",
                "skill_type": skill_type,
                "duration_minutes": request.duration_minutes,
                "difficulty": request.difficulty,
                "xp_gained": practice_result["session_results"]["total_xp_gained"],
                "breakthrough": practice_result["session_results"]["breakthrough_achieved"]
            }
        )

        # Save character
        orchestrator.character_manager.save_character(character)

        return practice_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/skills/{skill_type}/progress")
async def get_character_skill_progress(character_id: str, skill_type: str):
    """Get detailed progress tracking for a character's skill"""
    try:
        # Verify character exists
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        # Validate skill type
        try:
            skill_enum = SkillType(skill_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skill_type. Must be one of: {[st.value for st in SkillType]}"
            )

        progress_data = skill_system.get_skill_progress(character_id, skill_enum)
        return progress_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/skill-workshop")
async def conduct_skill_workshop(room_id: str, request: SkillWorkshopRequest):
    """Conduct a group skill workshop in a room"""
    try:
        # Verify room exists
        room = orchestrator.room_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Validate skill type
        try:
            skill_enum = SkillType(request.skill_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid skill_type. Must be one of: {[st.value for st in SkillType]}"
            )

        # Validate characters
        if len(request.character_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 characters required for workshop")

        for char_id in request.character_ids:
            character = orchestrator.character_manager.get_character(char_id)
            if not character:
                raise HTTPException(status_code=404, detail=f"Character {char_id} not found")

        # Validate parameters
        if request.duration_minutes < 15 or request.duration_minutes > 180:
            raise HTTPException(status_code=400, detail="duration_minutes must be between 15 and 180")

        # Conduct the workshop
        workshop_result = skill_system.conduct_skill_workshop(
            character_ids=request.character_ids,
            skill_type=skill_enum,
            duration_minutes=request.duration_minutes
        )

        # Save skill system data
        skill_system.save_to_disk()

        # Add memories for all participants
        for char_id in request.character_ids:
            character = orchestrator.character_manager.get_character(char_id)
            if character:
                character.add_memory(
                    content=f"Participated in {request.skill_type} workshop with {len(request.character_ids)-1} others",
                    memory_type=MemoryType.EXPERIENCE,
                    importance=6,
                    related_characters=[c for c in request.character_ids if c != char_id],
                    topics=["skill_workshop", request.skill_type, "collaborative_learning"],
                    context={
                        "source": "skill_workshop",
                        "room_id": room_id,
                        "skill_type": request.skill_type,
                        "participants": len(request.character_ids),
                        "duration_minutes": request.duration_minutes
                    }
                )
                # Save character
                orchestrator.character_manager.save_character(character)

        return {
            "message": "Skill workshop completed successfully",
            "room_id": room_id,
            "workshop_result": workshop_result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/badges")
async def get_character_badges(character_id: str):
    """Get all badges earned by a character"""
    try:
        # Verify character exists
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        badges = skill_system.earned_badges.get(character_id, [])

        # Group badges by type
        badges_by_type = {}
        for badge in badges:
            if badge.badge_type not in badges_by_type:
                badges_by_type[badge.badge_type] = []
            badges_by_type[badge.badge_type].append(badge.to_dict())

        return {
            "character_id": character_id,
            "total_badges": len(badges),
            "badges_by_type": badges_by_type,
            "recent_badges": [badge.to_dict() for badge in badges[-10:]]  # Last 10 badges
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ROOM ENDPOINTS
# ============================================================================

@app.post("/rooms")
async def create_room(request: CreateRoomRequest):
    """Create a new room"""
    try:
        # Convert room_type string to enum
        try:
            room_type = RoomType(request.room_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid room_type. Must be one of: {[rt.value for rt in RoomType]}"
            )
        
        room = orchestrator.create_room(
            name=request.name,
            room_type=room_type,
            purpose=request.purpose,
            max_characters=request.max_characters,
            conversation_pace_seconds=request.conversation_pace_seconds
        )
        
        # Add objects and media if provided
        if request.objects_in_room:
            room.objects_in_room = request.objects_in_room
        if request.background_media:
            room.background_media = request.background_media
        
        orchestrator.room_manager.save_room(room)
        
        return {
            "id": room.id,
            "name": room.name,
            "room_type": room.room_type.value,
            "created_at": room.created_at.isoformat() if room.created_at else None,
            "message": "Room created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rooms")
async def list_rooms():
    """List all rooms"""
    try:
        rooms = orchestrator.room_manager.list_rooms()
        return {"rooms": rooms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room details"""
    try:
        room = orchestrator.room_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        return room.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/add-character")
async def add_character_to_room(room_id: str, request: AddCharacterToRoomRequest):
    """Add a character to a room"""
    try:
        success = orchestrator.add_character_to_room(
            request.character_id,
            request.room_id
        )
        
        if success:
            return {"message": "Character added to room"}
        else:
            raise HTTPException(status_code=400, detail="Could not add character to room")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/start")
async def start_room_session(room_id: str, request: StartSessionRequest,
                            background_tasks: BackgroundTasks):
    """Start a conversation session in a room"""
    try:
        room = orchestrator.room_manager.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")
        
        # Start session in background
        background_tasks.add_task(
            _run_room_session,
            room_id,
            request.duration_minutes,
            request.rounds
        )
        
        return {
            "message": "Room session started",
            "room_id": room_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_room_session(room_id: str, duration_minutes: Optional[int],
                            rounds: Optional[int]):
    """Background task to run room session"""
    print(f"[DEBUG] _run_room_session called for room {room_id}")
    try:
        print(f"[DEBUG] About to call orchestrator.start_room_session")
        result = await orchestrator.start_room_session(
            room_id=room_id,
            duration_minutes=duration_minutes,
            rounds=rounds
        )
        print(f"Session completed: {result['summary']}")
    except Exception as e:
        print(f"Error in room session: {e}")
        import traceback
        traceback.print_exc()


@app.post("/rooms/{room_id}/pause")
async def pause_room(room_id: str):
    """Pause conversation in a room"""
    try:
        orchestrator.conversation_engine.pause_room(room_id)
        return {"message": "Room paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/resume")
async def resume_room(room_id: str):
    """Resume conversation in a room"""
    try:
        orchestrator.conversation_engine.resume_room(room_id)
        return {"message": "Room resumed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rooms/{room_id}/inject")
async def inject_message(room_id: str, request: InjectMessageRequest):
    """Inject a message into the room conversation"""
    try:
        orchestrator.conversation_engine.inject_message(
            room_id=room_id,
            message=request.message,
            sender=request.sender
        )
        return {"message": "Message injected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rooms/{room_id}/conversation")
async def get_room_conversation(room_id: str):
    """Get current conversation in a room"""
    try:
        if room_id in orchestrator.conversation_engine.active_conversations:
            conversation = orchestrator.conversation_engine.active_conversations[room_id]
            return {
                "room_id": room_id,
                "messages": [turn.__dict__ for turn in conversation]
            }
        else:
            return {
                "room_id": room_id,
                "messages": []
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET FOR LIVE ROOM STREAMING
# ============================================================================

@app.websocket("/ws/rooms/{room_id}")
async def websocket_room_stream(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for live room conversation streaming"""
    await websocket.accept()
    
    # Add to connections
    if room_id not in active_connections:
        active_connections[room_id] = []
    active_connections[room_id].append(websocket)
    
    # Callback for broadcasting messages
    def broadcast_turn(turn: ConversationTurn):
        asyncio.create_task(_broadcast_to_websocket(room_id, turn))
    
    # Subscribe to room
    orchestrator.subscribe_to_room(room_id, broadcast_turn)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Could handle commands from client here
            
    except WebSocketDisconnect:
        # Remove from connections
        active_connections[room_id].remove(websocket)
        if not active_connections[room_id]:
            del active_connections[room_id]


async def _broadcast_to_websocket(room_id: str, turn: ConversationTurn):
    """Broadcast turn to all websocket connections for a room"""
    if room_id not in active_connections:
        return
    
    message = json.dumps({
        "type": "conversation_turn",
        "character_id": turn.character_id,
        "character_name": turn.character_name,
        "content": turn.content,
        "timestamp": turn.timestamp.isoformat(),
        "laptop_activity": turn.laptop_activity,
        "tokens_used": turn.tokens_used
    })
    
    # Send to all connected clients
    disconnected = []
    for websocket in active_connections[room_id]:
        try:
            await websocket.send_text(message)
        except:
            disconnected.append(websocket)
    
    # Clean up disconnected clients
    for ws in disconnected:
        active_connections[room_id].remove(ws)


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "AI Society Portal API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/room-types")
async def get_room_types():
    """Get all available room types"""
    return {
        "room_types": [
            {
                "value": rt.value,
                "name": rt.value.replace("_", " ").title()
            }
            for rt in RoomType
        ]
    }


@app.post("/natural-language")
async def process_natural_language(request: NaturalLanguageRequest):
    """Process natural language requests to create rooms/characters"""
    import re
    try:
        # Keep original message for name extraction (preserves capitalization)
        original_message = request.message
        message = original_message.lower()

        # Check for character creation intent - more flexible patterns
        # Pattern 1: "create a character" or "make a character"
        character_creation_intent = (any(word in message for word in ["create", "make", "add", "new"]) and "character" in message) or \
                                   (re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+who\s+is\s+(?:a|an)', original_message))

        if character_creation_intent:
            return await handle_character_creation(original_message)

        # Check for room creation intent
        elif any(word in message for word in ["create", "make", "add", "new", "set up"]) and "room" in message:
            return await handle_room_creation(original_message)

        # Check for starting conversations
        elif any(word in message for word in ["start", "begin", "launch"]) and any(word in message for word in ["conversation", "session", "chat"]):
            return {
                "response": "To start a conversation, first add characters to a room, then click 'Start Session' on that room. Which room would you like to start?",
                "action": None
            }

        # Default help response
        else:
            return {
                "response": """I can help you create characters and rooms using natural language! Try saying:

• "Create a character named Alex who is a scientist"
• "Make a room called Jazz Club for creative discussions"
• "Add a philosopher character named Sofia"
• "Create a laboratory room for research"

What would you like to create?""",
                "action": None
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def handle_character_creation(original_message):
    """Extract character details and create character"""
    import re

    # Keep both original and lowercase versions
    message = original_message.lower()

    # Pattern 1: "Einstein who is a scientist" - name followed by "who is"
    name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+who\s+is\s+(?:a|an)', original_message)

    # Pattern 2: "Create character named Einstein" - named/called + name
    if not name_match:
        name_match = re.search(r'(?:named|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', original_message, re.IGNORECASE)

    # Pattern 3: "a character Einstein" - "character" + name
    if not name_match:
        name_match = re.search(r'character\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', original_message, re.IGNORECASE)

    # Pattern 4: "Create Einstein" - create/make + name (at start of sentence)
    if not name_match:
        name_match = re.search(r'^(?:create|make|add)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', original_message, re.IGNORECASE)

    # Pattern 5: Just look for any capitalized word that could be a name
    if not name_match:
        name_match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', original_message)

    name = name_match.group(1) if name_match else "Unnamed Character"

    # Try to extract specialization/profession
    specializations = {
        "scientist": "Scientist",
        "philosopher": "Philosopher",
        "artist": "Artist",
        "writer": "Writer",
        "programmer": "Programmer",
        "teacher": "Teacher",
        "doctor": "Doctor",
        "engineer": "Engineer",
        "psychologist": "Psychologist",
        "musician": "Musician"
    }

    specialization = "Generalist"
    for key, value in specializations.items():
        if key in message:
            specialization = value
            break

    # Create the character
    try:
        character = orchestrator.create_character(
            name=name,
            specialization=specialization,
            backstory=f"Created via natural language request: {message}",
            personality={"curiosity": 0.7, "creativity": 0.6},
            skills=[specialization.lower()],
            current_goals=["Explore new ideas"]
        )

        orchestrator.character_manager.save_character(character)

        return {
            "response": f"✅ Created {name} the {specialization}! You can now add them to a room to start conversations.",
            "action": "character_created",
            "data": {
                "id": character.id,
                "name": character.name,
                "specialization": character.specialization
            }
        }
    except Exception as e:
        return {
            "response": f"❌ Sorry, I couldn't create the character. Error: {str(e)}",
            "action": None
        }


async def handle_room_creation(original_message):
    """Extract room details and create room"""
    import re

    # Keep both original and lowercase versions
    message = original_message.lower()

    # Try to extract room name
    name_match = re.search(r'(?:room|called?|named?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', original_message, re.IGNORECASE)
    name = name_match.group(1) if name_match else "New Room"

    # Determine room type based on keywords
    room_types = {
        "jazz": RoomType.JAZZ_CLUB,
        "coffee": RoomType.COFFEE_HOUSE,
        "lab": RoomType.LABORATORY,
        "laboratory": RoomType.LABORATORY,
        "study": RoomType.STUDY_HALL,
        "library": RoomType.LIBRARY,
        "debate": RoomType.DEBATE_HALL,
        "creative": RoomType.ART_STUDIO,
        "meditation": RoomType.MEDITATION_GARDEN,
        "brainstorm": RoomType.BRAINSTORM_ROOM
    }

    room_type = RoomType.COFFEE_HOUSE  # default
    for key, value in room_types.items():
        if key in message:
            room_type = value
            break

    # Create the room
    try:
        room = orchestrator.create_room(
            name=name,
            room_type=room_type,
            purpose=f"Created via natural language request: {message}",
            max_characters=10,
            conversation_pace_seconds=3.0
        )

        orchestrator.room_manager.save_room(room)

        return {
            "response": f"✅ Created '{name}' ({room_type.value.replace('_', ' ').title()})! Now add characters to it and start a conversation.",
            "action": "room_created",
            "data": {
                "id": room.id,
                "name": room.name,
                "room_type": room.room_type.value
            }
        }
    except Exception as e:
        return {
            "response": f"❌ Sorry, I couldn't create the room. Error: {str(e)}",
            "action": None
        }


@app.get("/stats")
async def get_system_stats():
    """Get system statistics"""
    try:
        characters = orchestrator.character_manager.list_characters()
        rooms = orchestrator.room_manager.list_rooms()

        return {
            "total_characters": len(characters),
            "total_rooms": len(rooms),
            "active_rooms": len([r for r in rooms if r.get("is_active")]),
            "active_conversations": len(orchestrator.conversation_engine.active_conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DASHBOARD ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/characters/{character_id}/analytics")
async def get_character_analytics(character_id: str):
    """Get comprehensive analytics data for dashboard"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        analytics_data = {
            "character_id": character_id,
            "character_info": {
                "name": character.name,
                "specialization": character.specialization,
                "created_at": "unknown",  # Would need to track creation time
                "state": character.state.value,
                "total_room_hours": character.total_room_hours,
                "total_projects_completed": character.total_projects_completed,
                "insights_contributed": character.insights_contributed
            },
            "personality": character.personality,
            "relationships": character.relationships,
            "current_mood": character.current_mood,
            "skills": {},
            "memory_analytics": {},
            "knowledge_analytics": {},
            "cultural_impact": {},
            "development_timeline": []
        }

        # Get skills data
        try:
            skills_overview = skill_system.get_all_skills_overview(character_id)
            analytics_data["skills"] = skills_overview
        except Exception as e:
            print(f"Error getting skills for {character_id}: {e}")
            analytics_data["skills"] = {"skills": []}

        # Get memory analytics
        try:
            from memory_system import EnhancedMemorySystem
            if isinstance(character.memory, EnhancedMemorySystem):
                memory_stats = character.memory.get_memory_stats()
                recent_memories = character.memory.get_memories(limit=20, sort_by="recent")

                analytics_data["memory_analytics"] = {
                    "stats": memory_stats,
                    "recent_memories": [memory.to_dict() for memory in recent_memories],
                    "memory_types": memory_stats.get("memories_by_type", {}),
                    "total_memories": memory_stats.get("total_memories", 0)
                }
            else:
                analytics_data["memory_analytics"] = {
                    "stats": {},
                    "recent_memories": [],
                    "memory_types": {},
                    "total_memories": 0
                }
        except Exception as e:
            print(f"Error getting memory analytics for {character_id}: {e}")
            analytics_data["memory_analytics"] = {
                "stats": {},
                "recent_memories": [],
                "memory_types": {},
                "total_memories": 0
            }

        # Get knowledge analytics
        try:
            character_knowledge = cultural_system.get_character_knowledge(character_id)

            # Analyze knowledge by type and importance
            knowledge_by_type = {}
            high_importance_count = 0

            for knowledge in character_knowledge:
                ktype = knowledge.get("knowledge_type", "unknown")
                knowledge_by_type[ktype] = knowledge_by_type.get(ktype, 0) + 1
                if knowledge.get("importance", 0) >= 7:
                    high_importance_count += 1

            analytics_data["knowledge_analytics"] = {
                "total_knowledge": len(character_knowledge),
                "knowledge_by_type": knowledge_by_type,
                "high_importance_count": high_importance_count,
                "recent_discoveries": character_knowledge[:5]  # Last 5 discoveries
            }
        except Exception as e:
            print(f"Error getting knowledge analytics for {character_id}: {e}")
            analytics_data["knowledge_analytics"] = {
                "total_knowledge": 0,
                "knowledge_by_type": {},
                "high_importance_count": 0,
                "recent_discoveries": []
            }

        # Calculate cultural impact
        try:
            # Get cultural transmission stats
            cultural_stats = cultural_system.get_cultural_stats()

            # Count character's contributions to cultural transmission
            character_knowledge_ids = [k.get("id") for k in analytics_data["knowledge_analytics"]["recent_discoveries"]]
            transmission_events = 0

            for knowledge_id in character_knowledge_ids:
                try:
                    history = cultural_system.get_transmission_history(knowledge_id)
                    transmission_events += len(history)
                except:
                    pass

            analytics_data["cultural_impact"] = {
                "knowledge_created": analytics_data["knowledge_analytics"]["total_knowledge"],
                "transmission_events": transmission_events,
                "cultural_reach": len(set([r for r in character.relationships.values() if r > 0.3])),
                "influence_score": min(100, (analytics_data["knowledge_analytics"]["total_knowledge"] * 5) + transmission_events)
            }
        except Exception as e:
            print(f"Error calculating cultural impact for {character_id}: {e}")
            analytics_data["cultural_impact"] = {
                "knowledge_created": 0,
                "transmission_events": 0,
                "cultural_reach": 0,
                "influence_score": 0
            }

        # Generate development timeline (sample data based on recent memories)
        try:
            memories = analytics_data["memory_analytics"]["recent_memories"]
            timeline_events = []

            for memory in memories[:10]:  # Last 10 memories for timeline
                timeline_events.append({
                    "timestamp": memory.get("timestamp", "unknown"),
                    "type": memory.get("memory_type", "experience"),
                    "title": memory.get("content", "Memory")[:100] + ("..." if len(memory.get("content", "")) > 100 else ""),
                    "importance": memory.get("importance", 5),
                    "related_characters": memory.get("related_characters", [])
                })

            analytics_data["development_timeline"] = timeline_events
        except Exception as e:
            print(f"Error generating timeline for {character_id}: {e}")
            analytics_data["development_timeline"] = []

        # Calculate evolution metrics
        try:
            total_memories = analytics_data["memory_analytics"]["total_memories"]
            total_skills = len(analytics_data["skills"].get("skills", []))
            total_knowledge = analytics_data["knowledge_analytics"]["total_knowledge"]
            total_relationships = len(character.relationships)
            cultural_impact_score = analytics_data["cultural_impact"]["influence_score"]

            # Evolution score calculation (0-100)
            evolution_score = min(100, (
                (total_memories * 2) +          # Memory contribution
                (total_skills * 8) +           # Skills contribution
                (total_knowledge * 3) +         # Knowledge contribution
                (total_relationships * 5) +    # Social contribution
                (cultural_impact_score * 0.1)  # Cultural contribution
            ))

            analytics_data["evolution_metrics"] = {
                "evolution_score": round(evolution_score, 1),
                "memory_growth": total_memories,
                "skill_development": total_skills,
                "knowledge_acquisition": total_knowledge,
                "social_connections": total_relationships,
                "cultural_influence": round(cultural_impact_score, 1),
                "development_rate": "active" if evolution_score > 50 else "moderate" if evolution_score > 20 else "emerging"
            }
        except Exception as e:
            print(f"Error calculating evolution metrics for {character_id}: {e}")
            analytics_data["evolution_metrics"] = {
                "evolution_score": 0,
                "memory_growth": 0,
                "skill_development": 0,
                "knowledge_acquisition": 0,
                "social_connections": 0,
                "cultural_influence": 0,
                "development_rate": "emerging"
            }

        return analytics_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Analytics endpoint error for {character_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/system-overview")
async def get_dashboard_system_overview():
    """Get system-wide overview for dashboard"""
    try:
        # Get basic stats
        characters = orchestrator.character_manager.list_characters()
        rooms = orchestrator.room_manager.list_rooms()

        # Get cultural stats
        cultural_stats = cultural_system.get_cultural_stats()

        # Get skill system stats
        skill_stats = skill_system.get_system_stats() if hasattr(skill_system, 'get_system_stats') else {}

        # Calculate system metrics
        total_characters = len(characters)
        active_characters = 0
        total_skills = 0
        high_level_characters = 0

        for char in characters:
            try:
                character = orchestrator.character_manager.get_character(char["id"])
                if character:
                    if character.state != CharacterState.OFFLINE:
                        active_characters += 1

                    # Count skills
                    char_skills = skill_system.get_all_skills_overview(char["id"])
                    total_skills += len(char_skills.get("skills", []))

                    # Count high evolution score characters
                    if character.total_projects_completed > 5 or character.insights_contributed > 10:
                        high_level_characters += 1
            except:
                continue

        system_overview = {
            "system_stats": {
                "total_characters": total_characters,
                "active_characters": active_characters,
                "total_rooms": len(rooms),
                "total_skills": total_skills,
                "high_level_characters": high_level_characters,
                "active_conversations": len(orchestrator.conversation_engine.active_conversations)
            },
            "cultural_stats": cultural_stats,
            "skill_stats": skill_stats,
            "health_indicators": {
                "system_health": "healthy" if active_characters > 0 else "idle",
                "engagement_level": "high" if active_characters / max(total_characters, 1) > 0.5 else "moderate",
                "development_rate": "active" if high_level_characters > 0 else "emerging"
            },
            "recent_activities": {
                "characters_created": 0,  # Would need to track creation events
                "rooms_created": 0,       # Would need to track creation events
                "conversations_completed": 0  # Would need to track conversation completion
            }
        }

        return system_overview

    except Exception as e:
        print(f"System overview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUTOBIOGRAPHICAL MEMORY ENDPOINTS
# ============================================================================

def get_autobiographical_system(character_id: str) -> Optional[AutobiographicalMemorySystem]:
    """Get or create autobiographical memory system for a character"""
    try:
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            return None

        # Check if character has enhanced memory system
        from memory_system import EnhancedMemorySystem
        if not isinstance(character.memory, EnhancedMemorySystem):
            return None

        # Initialize autobiographical system if not already cached
        if not hasattr(character, '_autobiographical_system'):
            from pathlib import Path
            storage_dir = Path("ai_society_data") / "characters" / "autobiographical"
            character._autobiographical_system = AutobiographicalMemorySystem(
                character_id=character_id,
                character_name=character.name,
                memory_system=character.memory,
                storage_dir=storage_dir
            )

        return character._autobiographical_system
    except Exception as e:
        print(f"Error getting autobiographical system for {character_id}: {e}")
        return None


@app.get("/characters/{character_id}/life-story")
async def get_character_life_story(character_id: str, request: GetLifeStoryRequest = None):
    """Get character's autobiographical life story narrative"""
    try:
        if request is None:
            request = GetLifeStoryRequest()

        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Validate detail level
        if request.detail_level not in ["summary", "detailed", "comprehensive"]:
            raise HTTPException(
                status_code=400,
                detail="detail_level must be one of: summary, detailed, comprehensive"
            )

        # Generate life story
        life_story = await auto_system.generate_life_story(detail_level=request.detail_level)

        return {
            "character_id": character_id,
            "life_story": life_story,
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/identity-analysis")
async def get_character_identity_analysis(character_id: str):
    """Get character's identity and self-awareness analysis"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Analyze identity
        identity_analysis = await auto_system.analyze_identity()

        return {
            "character_id": character_id,
            "identity_analysis": identity_analysis,
            "generated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/self-reflection")
async def trigger_character_self_reflection(character_id: str, request: TriggerSelfReflectionRequest):
    """Trigger a self-reflection session for the character"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Validate reflection type if provided
        if request.reflection_type:
            valid_types = [rt.value for rt in ReflectionType]
            if request.reflection_type not in valid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"reflection_type must be one of: {valid_types}"
                )

        # Trigger self-reflection
        reflection_result = await auto_system.trigger_self_reflection_session(
            reflection_type=request.reflection_type,
            focus_area=request.focus_area
        )

        # Save the updated autobiographical data
        auto_system.save_autobiographical_data()

        return {
            "character_id": character_id,
            "reflection_result": reflection_result,
            "triggered_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/life-chapters")
async def get_character_life_chapters(character_id: str, include_complete: bool = True):
    """Get character's life chapters (organized life segments)"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Get life chapters
        chapters = auto_system.get_life_chapters(include_complete=include_complete)

        return {
            "character_id": character_id,
            "life_chapters": chapters,
            "total_chapters": len(chapters),
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/autobiographical-stats")
async def get_character_autobiographical_stats(character_id: str):
    """Get statistics about the character's autobiographical memory system"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Get autobiographical stats
        stats = auto_system.get_autobiographical_stats()

        return {
            "character_id": character_id,
            "autobiographical_stats": stats,
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/process-memory-for-autobiography")
async def process_memory_for_autobiography(character_id: str, memory_id: str):
    """Manually trigger processing of a specific memory for autobiographical understanding"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Find the memory
        memory = auto_system.memory_system.memories.get(memory_id)
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        # Process the memory for autobiographical understanding
        await auto_system.process_new_memory(memory)

        # Save updated data
        auto_system.save_autobiographical_data()

        return {
            "character_id": character_id,
            "memory_id": memory_id,
            "message": "Memory processed for autobiographical understanding",
            "processed_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/recent-reflections")
async def get_character_recent_reflections(character_id: str, limit: int = 5):
    """Get character's recent self-reflections"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Get recent reflections
        sorted_reflections = sorted(
            auto_system.self_reflections.values(),
            key=lambda r: r.timestamp,
            reverse=True
        )

        recent_reflections = []
        for reflection in sorted_reflections[:limit]:
            recent_reflections.append(reflection.to_dict())

        return {
            "character_id": character_id,
            "recent_reflections": recent_reflections,
            "total_reflections": len(auto_system.self_reflections),
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/identity-aspects")
async def get_character_identity_aspects(character_id: str):
    """Get detailed information about character's identity aspects"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Get identity aspects
        identity_aspects = {}
        for aspect, continuity in auto_system.identity_continuity.items():
            identity_aspects[aspect.value] = continuity.to_dict()

        return {
            "character_id": character_id,
            "identity_aspects": identity_aspects,
            "total_aspects": len(identity_aspects),
            "identity_coherence": auto_system.identity_coherence,
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/force-autobiographical-update")
async def force_autobiographical_update(character_id: str):
    """Force a complete update of the character's autobiographical understanding"""
    try:
        auto_system = get_autobiographical_system(character_id)
        if not auto_system:
            raise HTTPException(
                status_code=404,
                detail="Character not found or does not have enhanced memory system enabled"
            )

        # Get recent memories to process
        recent_memories = auto_system.memory_system.get_memories(limit=20, sort_by="recent")

        processed_count = 0
        for memory in recent_memories:
            try:
                await auto_system.process_new_memory(memory)
                processed_count += 1
            except Exception as e:
                print(f"Error processing memory {memory.id}: {e}")

        # Update narrative understanding
        await auto_system._update_narrative_understanding()

        # Save everything
        auto_system.save_autobiographical_data()

        return {
            "character_id": character_id,
            "memories_processed": processed_count,
            "total_chapters": len(auto_system.life_chapters),
            "total_reflections": len(auto_system.self_reflections),
            "self_awareness_level": auto_system.self_awareness_level,
            "updated_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONSCIOUSNESS METRICS ENDPOINTS
# ============================================================================

@app.post("/characters/{character_id}/assess-consciousness")
async def assess_character_consciousness(character_id: str):
    """Perform comprehensive consciousness assessment for a character"""
    try:
        # Get character and memory system
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        if not isinstance(character.memory, EnhancedMemorySystem):
            raise HTTPException(
                status_code=400,
                detail="Character must have enhanced memory system enabled"
            )

        # Initialize consciousness metrics system
        consciousness_system = ConsciousnessMetricsSystem(
            character_id,
            Path("ai_society_data") / "consciousness_metrics"
        )

        # Get recent conversations for context
        recent_conversations = []
        if character.current_room_id:
            room = orchestrator.room_manager.get_room(character.current_room_id)
            if room and hasattr(room, 'conversation_history'):
                recent_conversations = [
                    {"messages": turn.messages}
                    for turn in room.conversation_history[-5:]
                ]

        # Perform assessment
        profile = await consciousness_system.assess_consciousness(
            character.memory,
            recent_conversations,
            {"current_role": character.specialization}
        )

        # Generate report
        report = consciousness_system.get_consciousness_report()

        return {
            "character_id": character_id,
            "assessment_date": profile.last_assessment.isoformat(),
            "consciousness_profile": profile.to_dict(),
            "report": report,
            "engineering_benchmarks": {
                "current_llm_baseline": 0.21,  # From EngineeringAI.md
                "target_threshold": 0.57,      # From EngineeringAI.md
                "indicators_achieved": report["engineering_metrics"]["indicators_above_threshold"],
                "total_indicators": 14
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}/consciousness-profile")
async def get_character_consciousness_profile(character_id: str):
    """Get current consciousness profile for a character"""
    try:
        consciousness_system = ConsciousnessMetricsSystem(
            character_id,
            Path("ai_society_data") / "consciousness_metrics"
        )

        # Get dashboard data
        dashboard_data = get_dashboard_data(
            [character_id],
            Path("ai_society_data") / "consciousness_metrics"
        )

        return {
            "character_id": character_id,
            "profile": consciousness_system.profile.to_dict(),
            "consciousness_level": consciousness_system.get_consciousness_level(),
            "dashboard_data": dashboard_data,
            "retrieved_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/characters/{character_id}/sleep-consolidation")
async def trigger_sleep_consolidation(character_id: str):
    """Trigger sleep-like memory consolidation with consciousness assessment"""
    try:
        # Get character and memory system
        character = orchestrator.character_manager.get_character(character_id)
        if not character:
            raise HTTPException(status_code=404, detail="Character not found")

        if not isinstance(character.memory, EnhancedMemorySystem):
            raise HTTPException(
                status_code=400,
                detail="Character must have enhanced memory system enabled"
            )

        # Initialize systems
        consciousness_system = ConsciousnessMetricsSystem(
            character_id,
            Path("ai_society_data") / "consciousness_metrics"
        )

        # Perform sleep consolidation
        consolidation_log = await sleep_consolidation(
            character_id,
            character.memory,
            consciousness_system
        )

        return {
            "character_id": character_id,
            "consolidation_completed": True,
            "consolidation_log": consolidation_log,
            "post_consolidation_profile": consciousness_system.profile.to_dict(),
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/consciousness-dashboard")
async def get_consciousness_dashboard():
    """Get aggregated consciousness data for all characters"""
    try:
        # Get all character IDs
        characters = orchestrator.character_manager.list_characters()
        character_ids = [char["id"] for char in characters]

        # Get dashboard data
        dashboard_data = get_dashboard_data(
            character_ids,
            Path("ai_society_data") / "consciousness_metrics"
        )

        return dashboard_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CULTURAL RATCHET ENDPOINTS
# ============================================================================

@app.post("/cultural-ratchet/create-artifact")
async def create_cultural_artifact(
    name: str,
    artifact_type: str,
    content: str,
    creator_id: str,
    complexity_score: float = 0.5
):
    """Create a new cultural artifact for the ratchet system"""
    try:
        # Validate artifact type
        try:
            ratchet_type = RatchetType(artifact_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid artifact type. Must be one of: {[t.value for t in RatchetType]}"
            )

        # Create artifact
        artifact_id = cultural_ratchet.create_artifact(
            name=name,
            artifact_type=ratchet_type,
            content=content,
            creator_id=creator_id,
            complexity_score=min(1.0, max(0.0, complexity_score))
        )

        # Update generation metrics
        cultural_ratchet.update_generation_metrics()

        return {
            "artifact_id": artifact_id,
            "name": name,
            "type": artifact_type,
            "creator_id": creator_id,
            "generation": cultural_ratchet.current_generation,
            "complexity_score": complexity_score,
            "created_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cultural-ratchet/transmit-artifact")
async def transmit_cultural_artifact(
    artifact_id: str,
    transmitter_id: str,
    receiver_id: str,
    fidelity: str = "medium"
):
    """Transmit a cultural artifact between characters"""
    try:
        # Validate fidelity
        try:
            transmission_fidelity = TransmissionFidelity(fidelity)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid fidelity. Must be one of: {[f.value for f in TransmissionFidelity]}"
            )

        # Perform transmission
        transmission_record = cultural_ratchet.transmit_artifact(
            artifact_id=artifact_id,
            transmitter_id=transmitter_id,
            receiver_id=receiver_id,
            fidelity=transmission_fidelity
        )

        return transmission_record

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cultural-ratchet/create-generation")
async def create_cultural_generation(name: str, members: List[str]):
    """Create a new AI generation for cultural evolution tracking"""
    try:
        generation_id = cultural_ratchet.create_new_generation(name, members)

        return {
            "generation_id": generation_id,
            "name": name,
            "members": members,
            "total_generations": len(cultural_ratchet.generations),
            "created_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cultural-ratchet/heritage")
async def get_cultural_heritage(generation_limit: Optional[int] = None):
    """Get the cultural heritage accumulated across generations"""
    try:
        heritage = cultural_ratchet.get_cultural_heritage(generation_limit)

        return {
            "cultural_heritage": heritage,
            "retrieved_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cultural-ratchet/evolution-analysis")
async def get_cultural_evolution_analysis():
    """Analyze cultural evolution patterns and metrics"""
    try:
        analysis = cultural_ratchet.analyze_cultural_evolution()
        recommendations = cultural_ratchet.get_ratchet_recommendations()

        return {
            "evolution_analysis": analysis,
            "recommendations": recommendations,
            "current_generation": cultural_ratchet.current_generation,
            "total_artifacts": len(cultural_ratchet.artifacts),
            "ratchet_threshold": cultural_ratchet.ratchet_threshold,
            "analyzed_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cultural-ratchet/simulate-evolution")
async def simulate_cultural_evolution_endpoint(
    character_ids: List[str],
    generations: int = 3
):
    """Simulate cultural evolution across multiple generations"""
    try:
        # Run simulation
        simulation_results = await simulate_cultural_evolution(
            cultural_ratchet,
            character_ids,
            generations
        )

        return {
            "simulation_results": simulation_results,
            "parameters": {
                "character_ids": character_ids,
                "generations_simulated": generations
            },
            "completed_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cultural-ratchet/artifacts")
async def list_cultural_artifacts(artifact_type: Optional[str] = None):
    """List all cultural artifacts, optionally filtered by type"""
    try:
        artifacts = list(cultural_ratchet.artifacts.values())

        # Filter by type if specified
        if artifact_type:
            try:
                ratchet_type = RatchetType(artifact_type)
                artifacts = [a for a in artifacts if a.type == ratchet_type]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid artifact type. Must be one of: {[t.value for t in RatchetType]}"
                )

        # Sort by creation time
        artifacts.sort(key=lambda a: a.creation_timestamp, reverse=True)

        return {
            "total_artifacts": len(artifacts),
            "artifact_type": artifact_type,
            "artifacts": [a.to_dict() for a in artifacts[:50]],  # Limit to 50
            "retrieved_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv

    load_dotenv()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    uvicorn.run(app, host=host, port=port)
