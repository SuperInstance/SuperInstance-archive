from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio
import logging
from typing import Dict, List, Optional
import os
from datetime import datetime
from pydantic import BaseModel

from src.voice_processor import VoiceProcessor
from src.context_extractor import ContextExtractor
from src.predictive_interface import PredictiveInterface
from src.npc_voice_mapper import NPCVoiceMapper
from src.context_manager import ContextManager
from src.ai_dungeon_master import AIDungeonMaster, GameState, SuggestionType, UrgencyLevel
from src.ai_companions import AICompanion, CompanionManager, DecisionContext
from src.voice_print_magic import VoicePrintMagic, VoiceCommand
from src.story_memory_system import StoryMemorySystem, MemoryType, MemoryImportance
from src.one_click_everything import OneClickGenerator, GenerationType, DifficultyLevel
from models.game_models import GameSession, NPC, Location, Item, Encounter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="D&D Game Setup AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

voice_processor = VoiceProcessor()
context_extractor = ContextExtractor()
predictive_interface = PredictiveInterface()
npc_voice_mapper = NPCVoiceMapper()
context_manager = ContextManager()
ai_dungeon_master = AIDungeonMaster()
companion_manager = CompanionManager()
voice_print_magic = VoicePrintMagic()
story_memory_system = StoryMemorySystem()
one_click_generator = OneClickGenerator()

active_sessions: Dict[str, GameSession] = {}
websocket_connections: Dict[str, WebSocket] = {}

class SetupStep(BaseModel):
    step_id: str
    step_type: str
    content: dict
    voice_notes: Optional[str] = None

class VoiceInput(BaseModel):
    session_id: str
    audio_data: str
    context: str

@app.get("/", response_class=HTMLResponse)
async def get_setup_interface():
    with open("templates/setup_interface.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/advanced", response_class=HTMLResponse)
async def get_advanced_interface():
    with open("templates/advanced_interface.html", "r") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/api/sessions/create")
async def create_session():
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session = GameSession(
        session_id=session_id,
        created_at=datetime.now(),
        current_step="initial_setup",
        voice_recordings=[],
        context_history=[],
        npcs=[],
        locations=[],
        items=[],
        encounters=[]
    )
    active_sessions[session_id] = session
    context_manager.create_session(session_id)
    return {"session_id": session_id, "status": "created"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    websocket_connections[session_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "voice_input":
                await handle_voice_input(session_id, message["data"])
            elif message["type"] == "setup_step":
                await handle_setup_step(session_id, message["data"])
            elif message["type"] == "predict_next":
                await handle_prediction_request(session_id)
                
    except WebSocketDisconnect:
        if session_id in websocket_connections:
            del websocket_connections[session_id]

async def handle_voice_input(session_id: str, voice_data: dict):
    if session_id not in active_sessions:
        return
    
    session = active_sessions[session_id]
    websocket = websocket_connections.get(session_id)
    
    # Process voice input
    transcription = await voice_processor.transcribe_audio(voice_data["audio"])
    voice_characteristics = await voice_processor.analyze_voice_characteristics(voice_data["audio"])
    
    # Extract context from rambling
    extracted_context = await context_extractor.extract_structured_data(
        transcription, session.context_history
    )
    
    # Update context manager
    context_manager.add_voice_input(session_id, {
        "transcription": transcription,
        "voice_characteristics": voice_characteristics,
        "extracted_context": extracted_context,
        "timestamp": datetime.now()
    })
    
    # Check for NPC voice mapping
    if extracted_context.get("contains_character_voice"):
        npc_voice_data = await npc_voice_mapper.map_voice_to_npc(
            voice_data["audio"], extracted_context
        )
        if npc_voice_data:
            await create_or_update_npc(session_id, npc_voice_data)
    
    # Generate parallel creations
    parallel_creations = await generate_parallel_content(session_id, extracted_context)
    
    # Send updates to client
    if websocket:
        await websocket.send_text(json.dumps({
            "type": "voice_processed",
            "transcription": transcription,
            "extracted_context": extracted_context,
            "parallel_creations": parallel_creations,
            "voice_characteristics": voice_characteristics
        }))

async def handle_setup_step(session_id: str, step_data: dict):
    if session_id not in active_sessions:
        return
    
    session = active_sessions[session_id]
    websocket = websocket_connections.get(session_id)
    
    # Update session step
    session.current_step = step_data["step_id"]
    
    # Get predictions for next steps
    predictions = await predictive_interface.predict_next_steps(
        session, step_data
    )
    
    # Pre-populate fields based on context
    pre_populated = await predictive_interface.pre_populate_fields(
        session, step_data["step_type"]
    )
    
    if websocket:
        await websocket.send_text(json.dumps({
            "type": "step_updated",
            "current_step": step_data["step_id"],
            "predictions": predictions,
            "pre_populated": pre_populated
        }))

async def handle_prediction_request(session_id: str):
    if session_id not in active_sessions:
        return
    
    session = active_sessions[session_id]
    websocket = websocket_connections.get(session_id)
    
    # Analyze conversation to predict next step
    next_step_prediction = await predictive_interface.analyze_conversation_flow(session)
    
    # Determine UI complexity based on user expertise
    ui_complexity = await predictive_interface.determine_ui_complexity(session)
    
    # Show relevant options based on campaign style
    relevant_options = await predictive_interface.get_relevant_options(session)
    
    if websocket:
        await websocket.send_text(json.dumps({
            "type": "predictions_updated",
            "next_step": next_step_prediction,
            "ui_complexity": ui_complexity,
            "relevant_options": relevant_options
        }))

async def generate_parallel_content(session_id: str, context: dict):
    session = active_sessions[session_id]
    parallel_content = {}
    
    # Auto-generate NPCs from story descriptions
    if context.get("mentions_characters"):
        npcs = await context_extractor.extract_npcs_from_context(context)
        parallel_content["npcs"] = npcs
        session.npcs.extend(npcs)
    
    # Auto-generate locations from mentions
    if context.get("mentions_locations"):
        locations = await context_extractor.extract_locations_from_context(context)
        parallel_content["locations"] = locations
        session.locations.extend(locations)
    
    # Auto-generate items from story context
    if context.get("mentions_items"):
        items = await context_extractor.extract_items_from_context(context)
        parallel_content["items"] = items
        session.items.extend(items)
    
    # Auto-generate encounters based on narrative tension
    if context.get("narrative_tension_detected"):
        encounters = await context_extractor.generate_encounters_from_tension(context)
        parallel_content["encounters"] = encounters
        session.encounters.extend(encounters)
    
    return parallel_content

async def create_or_update_npc(session_id: str, npc_voice_data: dict):
    session = active_sessions[session_id]
    
    npc = NPC(
        name=npc_voice_data["name"],
        voice_characteristics=npc_voice_data["voice_characteristics"],
        personality_traits=npc_voice_data.get("personality_traits", []),
        speech_patterns=npc_voice_data.get("speech_patterns", []),
        voice_sample_path=npc_voice_data.get("voice_sample_path"),
        tts_voice_id=npc_voice_data.get("tts_voice_id")
    )
    
    # Check if NPC already exists and update
    existing_npc = next((n for n in session.npcs if n.name == npc.name), None)
    if existing_npc:
        existing_npc.voice_characteristics = npc.voice_characteristics
        existing_npc.speech_patterns = npc.speech_patterns
    else:
        session.npcs.append(npc)

@app.get("/api/sessions/{session_id}/context")
async def get_session_context(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    knowledge_graph = context_manager.get_knowledge_graph(session_id)
    
    return {
        "session": session.dict(),
        "knowledge_graph": knowledge_graph,
        "relationship_map": context_manager.get_relationship_map(session_id),
        "plot_threads": context_manager.get_plot_threads(session_id)
    }

@app.post("/api/sessions/{session_id}/voice/upload")
async def upload_voice_sample(session_id: str, file: UploadFile = File(...)):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Save voice file
    file_path = f"static/voice_samples/{session_id}_{file.filename}"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Process the voice sample
    voice_characteristics = await voice_processor.analyze_voice_characteristics(content)
    
    return {
        "file_path": file_path,
        "voice_characteristics": voice_characteristics,
        "status": "uploaded"
    }

# AI Dungeon Master endpoints
@app.post("/api/ai-dm/{session_id}/start")
async def start_ai_dm_session(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    
    # Create initial game state
    game_state = GameState(
        current_scene="initial_setup",
        active_players=[],  # Would be populated from session data
        current_location="unknown",
        initiative_order=[],
        combat_active=False,
        tension_level=0.0,
        last_action="session_start",
        unresolved_plot_points=[],
        active_npcs=[],
        environmental_factors=[]
    )
    
    await ai_dungeon_master.start_session_listening(session_id, game_state)
    
    return {"status": "AI DM activated", "session_id": session_id}

@app.get("/api/ai-dm/{session_id}/suggestions")
async def get_dm_suggestions(session_id: str, urgency: str = None):
    urgency_filter = UrgencyLevel(urgency) if urgency else None
    suggestions = ai_dungeon_master.get_active_suggestions(session_id, urgency_filter)
    
    return {
        "suggestions": [
            {
                "id": s.suggestion_id,
                "type": s.type.value,
                "urgency": s.urgency.value,
                "title": s.title,
                "description": s.description,
                "implementation": s.implementation,
                "confidence": s.confidence
            } for s in suggestions
        ]
    }

@app.post("/api/ai-dm/{session_id}/update-state")
async def update_game_state(session_id: str, updates: dict):
    await ai_dungeon_master.update_game_state(session_id, updates)
    return {"status": "Game state updated"}

@app.post("/api/ai-dm/{session_id}/npc-response")
async def generate_npc_response(session_id: str, npc_name: str, context: str, player_input: str):
    response = await ai_dungeon_master.generate_npc_response(session_id, npc_name, context, player_input)
    
    return {
        "npc_name": response.npc_name,
        "response_text": response.response_text,
        "emotional_state": response.emotional_state,
        "voice_characteristics": response.voice_characteristics,
        "body_language": response.body_language,
        "intent": response.intent
    }

# AI Companions endpoints
@app.post("/api/companions/create")
async def create_ai_companion(name: str, character_class: str, level: int = 1):
    companion = AICompanion(name, character_class, level)
    return {
        "companion_id": f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "summary": companion.get_character_summary()
    }

@app.post("/api/companions/{session_id}/add")
async def add_companion_to_session(session_id: str, companion_data: dict):
    companion = AICompanion(
        name=companion_data["name"],
        character_class=companion_data["character_class"],
        level=companion_data.get("level", 1)
    )
    companion_manager.add_companion_to_session(session_id, companion)
    
    return {"status": "Companion added to session"}

@app.post("/api/companions/{session_id}/decision")
async def get_companion_decisions(session_id: str, context: str, situation: dict, actions: list):
    decision_context = DecisionContext(context)
    decisions = await companion_manager.process_group_decision(
        session_id, decision_context, situation, actions
    )
    
    return {
        "decisions": [
            {
                "companion": d.description.split()[0],  # Extract name
                "action": d.action_type,
                "reasoning": d.reasoning,
                "confidence": d.confidence
            } for d in decisions
        ]
    }

# Voice Print Magic endpoints
@app.post("/api/voice-magic/create-print")
async def create_voice_print(character_name: str, file: UploadFile = File(...)):
    audio_data = await file.read()
    voice_print = await voice_print_magic.create_voice_print_from_sample(character_name, audio_data)
    
    return {
        "voice_id": voice_print.voice_id,
        "character_name": voice_print.character_name,
        "fundamental_freq": voice_print.fundamental_freq,
        "voice_quality": voice_print.voice_quality_markers
    }

@app.post("/api/voice-magic/{session_id}/start-transformation")
async def start_voice_transformation(session_id: str, dm_voice_id: str, target_character: str):
    config = await voice_print_magic.start_real_time_transformation(session_id, dm_voice_id, target_character)
    
    return {
        "status": "Voice transformation started",
        "target_character": config.target_character,
        "confidence": config.transformation.confidence_score
    }

@app.post("/api/voice-magic/{session_id}/emotion")
async def apply_emotional_modification(session_id: str, emotion: str, intensity: float):
    await voice_print_magic.apply_emotional_modification(session_id, emotion, intensity)
    return {"status": f"Applied {emotion} with intensity {intensity}"}

@app.post("/api/voice-magic/command")
async def process_voice_command(session_id: str, file: UploadFile = File(...)):
    audio_data = await file.read()
    result = await voice_print_magic.process_voice_command(session_id, audio_data)
    
    if result:
        return result
    else:
        return {"status": "No command recognized"}

@app.get("/api/voice-magic/voices")
async def get_available_voices():
    return {"voices": voice_print_magic.get_available_voices()}

# Story Memory System endpoints
@app.post("/api/story-memory/{campaign_id}/memory")
async def create_story_memory(
    campaign_id: str,
    session_number: int,
    memory_type: str,
    importance: str,
    title: str,
    description: str,
    participants: list,
    location: str,
    tags: list = None,
    dm_notes: str = ""
):
    memory = await story_memory_system.create_story_memory(
        campaign_id=campaign_id,
        session_number=session_number,
        memory_type=MemoryType(memory_type),
        importance=MemoryImportance(importance),
        title=title,
        description=description,
        participants=participants,
        location=location,
        tags=tags,
        dm_notes=dm_notes
    )
    
    return {
        "memory_id": memory.memory_id,
        "title": memory.title,
        "importance": memory.importance.value
    }

@app.get("/api/story-memory/{campaign_id}/recap")
async def get_campaign_recap(campaign_id: str, current_session: int):
    recap = await story_memory_system.generate_previously_on_recap(campaign_id, current_session)
    return {"recap": recap}

@app.get("/api/story-memory/{campaign_id}/forgotten-plots")
async def get_forgotten_plot_threads(campaign_id: str):
    forgotten = await story_memory_system.get_forgotten_plot_threads(campaign_id)
    return {"forgotten_threads": forgotten}

@app.get("/api/story-memory/{campaign_id}/wiki")
async def get_campaign_wiki(campaign_id: str):
    wiki = story_memory_system.get_campaign_wiki(campaign_id)
    if wiki:
        return wiki.dict()
    else:
        return {"message": "No wiki data found"}

# One-Click Everything endpoints
@app.post("/api/one-click/generate")
async def generate_one_click_content(
    generation_type: str,
    session_context: dict,
    parameters: dict = None
):
    content = await one_click_generator.generate_one_click_content(
        GenerationType(generation_type),
        session_context,
        parameters
    )
    
    return {
        "content_id": content.content_id,
        "title": content.title,
        "description": content.description,
        "implementation_notes": content.implementation_notes,
        "voice_notes": content.voice_notes,
        "estimated_duration": content.estimated_duration,
        "difficulty_level": content.difficulty_level.value if content.difficulty_level else None,
        "details": content.details
    }

@app.post("/api/one-click/tavern-brawl")
async def create_tavern_brawl(session_context: dict):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.TAVERN_BRAWL,
        session_context
    )
    return content

@app.post("/api/one-click/mysterious-npc")
async def create_mysterious_npc(session_context: dict):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.NPC,
        session_context
    )
    return content

@app.post("/api/one-click/side-quest")
async def create_side_quest(session_context: dict):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.QUEST,
        session_context
    )
    return content

@app.post("/api/one-click/balanced-encounter")
async def create_balanced_encounter(session_context: dict, encounter_type: str = "combat"):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.ENCOUNTER,
        session_context,
        {"encounter_type": encounter_type}
    )
    return content

@app.post("/api/one-click/plot-twist")
async def create_plot_twist(session_context: dict):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.PLOT_TWIST,
        session_context
    )
    return content

@app.post("/api/one-click/cliffhanger")
async def create_cliffhanger(session_context: dict):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.CLIFFHANGER,
        session_context
    )
    return content

@app.post("/api/one-click/enhance-scene")
async def enhance_current_scene(session_context: dict):
    content = await one_click_generator.generate_one_click_content(
        GenerationType.SCENE_ENHANCEMENT,
        session_context
    )
    return content

@app.get("/api/sessions/{session_id}/export")
async def export_session(session_id: str):
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = active_sessions[session_id]
    knowledge_graph = context_manager.get_knowledge_graph(session_id)
    
    export_data = {
        "session": session.dict(),
        "knowledge_graph": knowledge_graph,
        "full_audio_references": [r.file_path for r in session.voice_recordings],
        "compressed_context": context_manager.get_compressed_context(session_id),
        "export_timestamp": datetime.now().isoformat()
    }
    
    return export_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8406)