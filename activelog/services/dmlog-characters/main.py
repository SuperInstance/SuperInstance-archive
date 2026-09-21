"""
Main FastAPI service for the character AI system.
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import uvicorn
from typing import Dict, List, Optional, Any
import logging

from .config import Config
from .models.base import CharacterType, CharacterRace, EmotionType
from .models.personality import PersonalityProfileSchema, PersonalityGenerationRequest
from .models.voice import VoiceProfileSchema, VoiceSynthesisRequest
from .models.dialogue import DialogueRequest, DialogueGenerationOptions
from .models.memory import MemoryCreationRequest, MemoryQueryRequest
from .models.emotion import EmotionalTriggerEvent
from .models.portrait import PortraitGenerationRequest
from .models.mannerism import MannerismGenerationRequest, GestureGenerationRequest
from .models.faction import ReputationEventSchema
from .models.character_arc import ArcCreationRequest, ArcProgressRequest

from .services.voice_service import VoiceService
from .services.personality_service import PersonalityService
from .services.dialogue_service import DialogueService
from .services.memory_service import MemoryService
from .services.emotion_service import EmotionService
from .services.portrait_service import PortraitService
from .services.mannerism_service import MannerismService
from .services.faction_service import FactionService
from .services.character_arc_service import CharacterArcService
from .services.banter_service import BanterService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize configuration
config = Config()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    logger.info("Starting Character AI Service")
    logger.info(f"Service running on port {config.SERVICE_PORT}")
    yield
    logger.info("Shutting down Character AI Service")

# Initialize FastAPI app
app = FastAPI(
    title="DM Log Characters AI Service",
    description="Advanced AI system for bringing NPCs to life with voice synthesis, personality engines, and dynamic interactions",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
voice_service = VoiceService()
personality_service = PersonalityService()
dialogue_service = DialogueService()
memory_service = MemoryService()
emotion_service = EmotionService()
portrait_service = PortraitService()
mannerism_service = MannerismService()
faction_service = FactionService()
arc_service = CharacterArcService()
banter_service = BanterService()

# Dependency for database session (mock for now)
def get_db():
    # In a real implementation, this would return a database session
    return None

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "DM Log Characters AI Service",
        "version": "1.0.0",
        "status": "active",
        "features": [
            "Voice synthesis with emotional modulation",
            "Personality-driven behavior prediction",
            "Dynamic dialogue generation",
            "Memory system for consistent interactions",
            "Emotion engine for realistic responses",
            "Voice cloning from audio samples",
            "Accent and speech pattern system",
            "AI portrait generation",
            "Mannerism and gesture descriptions",
            "Faction reputation tracking",
            "Character arc progression",
            "Party banter generation"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

# Personality endpoints
@app.post("/personality/generate")
async def generate_personality(
    request: PersonalityGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a personality profile for a character."""
    try:
        personality = await personality_service.generate_personality_profile(request, db)
        return personality
    except Exception as e:
        logger.error(f"Error generating personality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/personality/{character_id}")
async def get_personality(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get personality profile for a character."""
    try:
        personality = await personality_service.get_personality_profile(character_id, db)
        if not personality:
            raise HTTPException(status_code=404, detail="Personality profile not found")
        return personality
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting personality: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/personality/{character_id}/predict-behavior")
async def predict_behavior(
    character_id: str,
    situation_type: str,
    context: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Predict character behavior in a given situation."""
    try:
        personality = await personality_service.get_personality_profile(character_id, db)
        if not personality:
            raise HTTPException(status_code=404, detail="Personality profile not found")
        
        prediction = personality_service.predict_behavior(personality, situation_type, context)
        return prediction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error predicting behavior: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Voice synthesis endpoints
@app.post("/voice/synthesize")
async def synthesize_speech(
    request: VoiceSynthesisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Synthesize speech for a character."""
    try:
        # Get character's voice profile (mock for now)
        voice_profile = VoiceProfileSchema(
            character_id=request.character_id,
            name=f"Voice for {request.character_id}",
            gender="neutral",
            accent="neutral",
            speech_pattern="neutral"
        )
        
        audio_path = await voice_service.synthesize_speech(
            request.text, voice_profile, request.voice_parameters
        )
        
        return {
            "character_id": request.character_id,
            "audio_url": audio_path,
            "text": request.text,
            "voice_parameters": request.voice_parameters
        }
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voice/clone")
async def clone_voice(
    character_id: str,
    audio_file_path: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Clone a voice from audio sample."""
    try:
        result = await voice_service.clone_voice(character_id, audio_file_path, db)
        return result
    except Exception as e:
        logger.error(f"Error cloning voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dialogue generation endpoints
@app.post("/dialogue/generate")
async def generate_dialogue(
    request: DialogueRequest,
    options: Optional[DialogueGenerationOptions] = None,
    db: Session = Depends(get_db)
):
    """Generate dialogue for a character."""
    try:
        # Get character data (mock for now)
        personality = await personality_service.get_personality_profile(request.character_id, db)
        character_background = {"character_type": "warrior", "background": "noble"}
        
        if not personality:
            # Generate default personality
            gen_request = PersonalityGenerationRequest(character_id=request.character_id)
            personality = await personality_service.generate_personality_profile(gen_request, db)
        
        dialogue = await dialogue_service.generate_dialogue(
            request, personality, character_background, options
        )
        return dialogue
    except Exception as e:
        logger.error(f"Error generating dialogue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/dialogue/banter")
async def generate_party_banter(
    participants: List[str],
    trigger: str,
    context: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Generate party banter between characters."""
    try:
        # Get character data for all participants
        character_data = {}
        for char_id in participants:
            personality = await personality_service.get_personality_profile(char_id, db)
            if personality:
                character_data[char_id] = {
                    "personality": personality.dict(),
                    "character_type": CharacterType.WARRIOR,  # Mock
                    "name": char_id
                }
        
        banter = await banter_service.generate_party_banter(
            participants, trigger, context, character_data, db
        )
        
        if not banter:
            return {"message": "No banter generated for current context"}
        
        return banter
    except Exception as e:
        logger.error(f"Error generating banter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Memory system endpoints
@app.post("/memory/create")
async def create_memory(
    request: MemoryCreationRequest,
    db: Session = Depends(get_db)
):
    """Create a memory for a character."""
    try:
        memory = await memory_service.create_memory(request, None, db)
        return memory
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/search")
async def search_memories(
    request: MemoryQueryRequest,
    db: Session = Depends(get_db)
):
    """Search character memories."""
    try:
        results = await memory_service.search_memories(request)
        return results
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/recall")
async def recall_memories(
    character_id: str,
    trigger: str,
    context: Dict[str, Any],
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Trigger memory recall for a character."""
    try:
        memories = await memory_service.recall_memories(
            character_id, trigger, context, None, limit
        )
        return memories
    except Exception as e:
        logger.error(f"Error recalling memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Emotion engine endpoints
@app.post("/emotion/trigger")
async def trigger_emotional_event(
    event: EmotionalTriggerEvent,
    db: Session = Depends(get_db)
):
    """Process an emotional trigger event."""
    try:
        personality = await personality_service.get_personality_profile(event.character_id, db)
        if not personality:
            raise HTTPException(status_code=404, detail="Character not found")
        
        response = await emotion_service.trigger_emotional_event(event, personality, None, db)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing emotional event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emotion/{character_id}")
async def get_emotional_state(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get current emotional state of a character."""
    try:
        state = await emotion_service.get_emotional_state(character_id, db)
        return state
    except Exception as e:
        logger.error(f"Error getting emotional state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Portrait generation endpoints
@app.post("/portrait/generate")
async def generate_portrait(
    request: PortraitGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Generate a character portrait."""
    try:
        personality = await personality_service.get_personality_profile(request.character_id, db)
        background = {"character_type": "warrior"}  # Mock
        
        response = await portrait_service.generate_portrait(
            request, personality, background, db
        )
        return response
    except Exception as e:
        logger.error(f"Error generating portrait: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portrait/templates")
async def get_portrait_templates(
    race: Optional[CharacterRace] = None,
    character_type: Optional[CharacterType] = None
):
    """Get available portrait templates."""
    try:
        templates = await portrait_service.get_portrait_templates(race, character_type)
        return templates
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mannerism endpoints
@app.post("/mannerisms/generate")
async def generate_mannerisms(
    request: MannerismGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate mannerisms for a character."""
    try:
        response = await mannerism_service.generate_character_mannerisms(request, db)
        return response
    except Exception as e:
        logger.error(f"Error generating mannerisms: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gestures/generate")
async def generate_gesture(
    request: GestureGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate a contextual gesture."""
    try:
        personality = await personality_service.get_personality_profile(request.character_id, db)
        response = await mannerism_service.generate_contextual_gesture(request, personality, db)
        return response
    except Exception as e:
        logger.error(f"Error generating gesture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Faction reputation endpoints
@app.post("/faction/reputation/update")
async def update_reputation(
    event: ReputationEventSchema,
    db: Session = Depends(get_db)
):
    """Update character reputation with a faction."""
    try:
        result = await faction_service.update_reputation(event, db)
        return result
    except Exception as e:
        logger.error(f"Error updating reputation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faction/reputation/{character_id}")
async def get_character_reputations(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get all reputation standings for a character."""
    try:
        reputations = await faction_service.get_all_character_reputations(character_id, db)
        return reputations
    except Exception as e:
        logger.error(f"Error getting reputations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/faction/reputation/{character_id}/analysis")
async def analyze_reputation(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Analyze character's reputation patterns."""
    try:
        analysis = await faction_service.analyze_character_reputation(character_id, db)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing reputation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Character arc endpoints
@app.post("/arc/create")
async def create_character_arc(
    request: ArcCreationRequest,
    db: Session = Depends(get_db)
):
    """Create a new character arc."""
    try:
        personality = await personality_service.get_personality_profile(request.character_id, db)
        if not personality:
            raise HTTPException(status_code=404, detail="Character not found")
        
        arc = await arc_service.create_character_arc(
            request, personality, personality.moral_alignment, db
        )
        return arc
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating arc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/arc/progress")
async def progress_character_arc(
    request: ArcProgressRequest,
    db: Session = Depends(get_db)
):
    """Progress a character arc based on events."""
    try:
        personality = await personality_service.get_personality_profile(request.character_id, db)
        if not personality:
            raise HTTPException(status_code=404, detail="Character not found")
        
        response = await arc_service.progress_character_arc(request, personality, db)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error progressing arc: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/arc/{character_id}/analysis")
async def analyze_character_arcs(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Analyze character's arc progression."""
    try:
        analysis = await arc_service.analyze_character_arcs(character_id, db)
        return analysis
    except Exception as e:
        logger.error(f"Error analyzing arcs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Combined character endpoints
@app.post("/character/{character_id}/complete-interaction")
async def complete_character_interaction(
    character_id: str,
    interaction_type: str,
    context: Dict[str, Any],
    include_voice: bool = False,
    include_portrait: bool = False,
    db: Session = Depends(get_db)
):
    """Generate a complete character interaction with all systems."""
    try:
        result = {}
        
        # Get or create personality
        personality = await personality_service.get_personality_profile(character_id, db)
        if not personality:
            gen_request = PersonalityGenerationRequest(character_id=character_id)
            personality = await personality_service.generate_personality_profile(gen_request, db)
        
        result["personality"] = personality
        
        # Get emotional state
        emotional_state = await emotion_service.get_emotional_state(character_id, db)
        result["emotional_state"] = emotional_state
        
        # Generate dialogue
        dialogue_request = DialogueRequest(
            character_id=character_id,
            dialogue_type=context.get("dialogue_type", "small_talk"),
            context=context.get("dialogue_context"),
            emotional_state=emotional_state.dominant_emotion
        )
        
        dialogue = await dialogue_service.generate_dialogue(
            dialogue_request, personality, context
        )
        result["dialogue"] = dialogue
        
        # Voice synthesis if requested
        if include_voice:
            voice_request = VoiceSynthesisRequest(
                character_id=character_id,
                text=dialogue.dialogue_text,
                voice_parameters=dialogue.voice_modifiers
            )
            
            voice_profile = VoiceProfileSchema(
                character_id=character_id,
                name=f"Voice for {character_id}",
                gender="neutral",
                accent="neutral",
                speech_pattern="neutral"
            )
            
            audio_path = await voice_service.synthesize_speech(
                voice_request.text, voice_profile, voice_request.voice_parameters
            )
            result["audio_url"] = audio_path
        
        # Portrait generation if requested
        if include_portrait:
            # This would require more complex setup in a real implementation
            result["portrait_available"] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Error in complete interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/character/{character_id}/status")
async def get_character_status(
    character_id: str,
    db: Session = Depends(get_db)
):
    """Get complete status overview for a character."""
    try:
        status = {}
        
        # Personality
        personality = await personality_service.get_personality_profile(character_id, db)
        if personality:
            status["personality"] = personality
        
        # Emotional state
        try:
            emotional_state = await emotion_service.get_emotional_state(character_id, db)
            status["emotional_state"] = emotional_state
        except:
            status["emotional_state"] = None
        
        # Memory analysis
        try:
            memory_analysis = await memory_service.analyze_character_memories(character_id)
            status["memory_summary"] = memory_analysis
        except:
            status["memory_summary"] = None
        
        # Reputation analysis
        try:
            reputation_analysis = await faction_service.analyze_character_reputation(character_id, db)
            status["reputation_summary"] = reputation_analysis
        except:
            status["reputation_summary"] = None
        
        # Character arcs
        try:
            arc_analysis = await arc_service.analyze_character_arcs(character_id, db)
            status["arc_summary"] = arc_analysis
        except:
            status["arc_summary"] = None
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting character status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.SERVICE_PORT,
        reload=True,
        log_level="info"
    )