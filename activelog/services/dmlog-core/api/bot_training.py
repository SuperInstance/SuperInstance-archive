"""
Bot Training API for DMLog Gaming Intelligence
Revolutionary autonomous gaming AI bot training and management system.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from bot_training_system import (
    gaming_bot_training_system,
    BotSpecialization,
    GamingSession
)

router = APIRouter()
logger = logging.getLogger(__name__)

class CreateBotRequest(BaseModel):
    """Request to create a specialized gaming bot."""
    specialization: str
    initial_training_data: Dict[str, Any] = {}

class TrainBotRequest(BaseModel):
    """Request to train a bot on gaming session data."""
    bot_id: str
    session_data: Dict[str, Any]

class GamingSessionTrainingData(BaseModel):
    """Complete gaming session data for bot training."""
    session_id: str
    duration_hours: float = 3.0
    dm_user_id: str = "demo_dm"
    players: List[Dict[str, Any]] = []
    game_system: str = "dnd5e"
    session_type: str = "standard"
    quality_metrics: Dict[str, float] = {}
    cross_domain_enhancements: List[Dict[str, Any]] = []
    economic_events: List[Dict[str, Any]] = []
    narrative_elements: List[str] = []
    player_satisfaction: float = 0.7
    collaboration_score: float = 0.6

@router.post("/create-bot")
async def create_specialized_gaming_bot(request: CreateBotRequest):
    """
    🤖 CREATE SPECIALIZED GAMING BOT
    
    Create an autonomous gaming AI bot with specific specialization:
    - campaign_ai_generator: Generates personalized campaigns
    - cross_domain_enhancer: Enhances gaming with cross-domain data
    - economic_optimizer: Optimizes compute capital gaming economy
    - player_experience_analyst: Analyzes and improves player experience
    - collaborative_gaming_engine: Powers real-time collaborative gaming
    - narrative_intelligence: Advanced story and character AI
    """
    try:
        # Validate specialization
        try:
            specialization = BotSpecialization(request.specialization)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid specialization. Choose from: {[s.value for s in BotSpecialization]}"
            )
        
        # Create the bot
        bot_id = await gaming_bot_training_system.create_specialized_bot(specialization)
        
        return {
            "status": "success",
            "bot_id": bot_id,
            "specialization": specialization.value,
            "message": f"🤖 Revolutionary gaming AI bot created: {specialization.value}",
            "training_phase": "observation",
            "superinstance_revolution": {
                "bot_intelligence": "Data + Tools + Configuration = Gaming Intelligence",
                "cost": "$2/month for infinite gaming possibilities",
                "capability": "Autonomous gaming improvement through AI learning"
            }
        }
        
    except Exception as e:
        logger.error(f"Bot creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bot creation failed: {str(e)}")

@router.post("/train-bot")
async def train_bot_on_session(request: TrainBotRequest):
    """
    🎓 TRAIN BOT ON GAMING SESSION
    
    Train a specialized bot using real gaming session data.
    The bot learns patterns, extracts insights, and improves gaming experiences.
    """
    try:
        result = await gaming_bot_training_system.train_bot_on_session(
            request.bot_id, 
            request.session_data
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Bot {request.bot_id} not found")
        
        return {
            "status": "success",
            "bot_id": request.bot_id,
            "training_results": result,
            "message": "🎓 Bot successfully trained on gaming session",
            "learning_progress": f"Training phase: {result['training_phase']}",
            "superinstance_learning": "Bot intelligence continuously improving through experience"
        }
        
    except Exception as e:
        logger.error(f"Bot training failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bot training failed: {str(e)}")

@router.get("/bot-insights/{bot_id}")
async def get_bot_insights(bot_id: str):
    """
    🧠 GET BOT INSIGHTS
    
    Retrieve insights and discoveries made by a trained gaming bot.
    These insights drive gaming experience improvements.
    """
    try:
        insights = await gaming_bot_training_system.get_bot_insights(bot_id)
        
        return {
            "status": "success",
            "bot_id": bot_id,
            "insights_count": len(insights),
            "insights": insights,
            "message": f"🧠 Retrieved {len(insights)} gaming insights from bot",
            "superinstance_intelligence": "Bot-discovered patterns enhance gaming for all players"
        }
        
    except Exception as e:
        logger.error(f"Failed to get bot insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")

@router.get("/training-summary")
async def get_training_summary():
    """
    📊 TRAINING SYSTEM SUMMARY
    
    Get comprehensive summary of the bot training system status.
    Shows all active bots, their specializations, and training progress.
    """
    try:
        summary = await gaming_bot_training_system.get_training_summary()
        
        return {
            "status": "success",
            "training_summary": summary,
            "message": "📊 Gaming bot training system operational",
            "superinstance_revolution": {
                "active_bots": summary["total_active_bots"],
                "specializations": list(summary["bot_specializations"].keys()),
                "total_insights": summary["total_insights"],
                "learning_status": "Autonomous gaming AI learning in progress",
                "cost_revolution": "$2/month for infinite AI-enhanced gaming"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get training summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

@router.post("/simulate-training-session")
async def simulate_bot_training_session(training_data: GamingSessionTrainingData):
    """
    🎮 SIMULATE BOT TRAINING SESSION
    
    Create a simulated gaming session to demonstrate bot learning capabilities.
    Perfect for testing and demonstrating the revolutionary bot training system.
    """
    try:
        # Create session data from request
        session_data = training_data.dict()
        
        # Train all active bots on this session
        training_results = {}
        
        for bot_id in gaming_bot_training_system.active_bots:
            result = await gaming_bot_training_system.train_bot_on_session(bot_id, session_data)
            training_results[bot_id] = result
        
        # Get insights from all bots
        all_insights = {}
        for bot_id in gaming_bot_training_system.active_bots:
            insights = await gaming_bot_training_system.get_bot_insights(bot_id)
            all_insights[bot_id] = insights
        
        return {
            "status": "success",
            "session_id": training_data.session_id,
            "bots_trained": len(training_results),
            "training_results": training_results,
            "insights_generated": {k: len(v) for k, v in all_insights.items()},
            "message": "🎮 Simulated gaming session processed by all bots",
            "demonstration": {
                "bot_learning": "All specialized bots learned from the gaming session",
                "pattern_extraction": "Bots extracted patterns for future improvements",
                "insight_generation": "New insights created for gaming enhancement",
                "revolution": "This is how $2/month AI transforms gaming forever"
            }
        }
        
    except Exception as e:
        logger.error(f"Training simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@router.post("/save-bot-states")
async def save_all_bot_training_states(background_tasks: BackgroundTasks):
    """
    💾 SAVE BOT TRAINING STATES
    
    Save training states for all active bots for persistence.
    Ensures bot learning is preserved across restarts.
    """
    try:
        background_tasks.add_task(gaming_bot_training_system.save_all_bot_states)
        
        return {
            "status": "success",
            "message": "💾 Bot training state save initiated",
            "note": "Saving bot states in background",
            "superinstance_persistence": "Bot intelligence preserved across sessions"
        }
        
    except Exception as e:
        logger.error(f"Failed to save bot states: {e}")
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")

@router.post("/create-demo-bots")
async def create_demo_bot_ecosystem():
    """
    🚀 CREATE DEMO BOT ECOSYSTEM
    
    Create a complete ecosystem of specialized gaming bots for demonstration.
    Shows the full power of the SuperInstance gaming revolution.
    """
    try:
        demo_bots = {}
        
        # Create one bot of each specialization
        for specialization in BotSpecialization:
            bot_id = await gaming_bot_training_system.create_specialized_bot(specialization)
            demo_bots[specialization.value] = bot_id
        
        # Create demo training data
        demo_session = GamingSessionTrainingData(
            session_id="demo_session_001",
            duration_hours=4.0,
            dm_user_id="demo_master_dm",
            players=[
                {"user_id": "player1", "engagement_score": 0.9, "player_type": "veteran"},
                {"user_id": "player2", "engagement_score": 0.8, "player_type": "casual"},
                {"user_id": "player3", "engagement_score": 0.85, "player_type": "new_player"}
            ],
            game_system="dnd5e",
            session_type="adventure",
            quality_metrics={
                "story_rating": 0.9,
                "player_feedback": 0.85,
                "rule_accuracy": 0.8,
                "adaptation_rating": 0.9
            },
            cross_domain_enhancements=[
                {"source_domain": "fitness", "enhancement_type": "character_stats", "strength": 0.8},
                {"source_domain": "business", "enhancement_type": "campaign_economics", "strength": 0.7}
            ],
            economic_events=[
                {"event_type": "campaign_mastery", "value_generated": 2.5, "quality_factors": {"dm_skill": 0.9}}
            ],
            narrative_elements=["epic_battle", "character_development", "plot_twist", "emotional_moment"],
            player_satisfaction=0.9,
            collaboration_score=0.85
        )
        
        # Train all demo bots
        for bot_id in demo_bots.values():
            await gaming_bot_training_system.train_bot_on_session(bot_id, demo_session.dict())
        
        return {
            "status": "success",
            "demo_bots_created": demo_bots,
            "message": "🚀 Complete gaming bot ecosystem created and trained!",
            "demonstration": {
                "bot_count": len(demo_bots),
                "specializations": list(demo_bots.keys()),
                "training_session": "All bots trained on high-quality demo session",
                "ready_for": "Real gaming session enhancement",
                "revolution": "This is the $2/month SuperInstance gaming transformation!"
            },
            "next_steps": [
                "Use /bot-insights/{bot_id} to see what each bot learned",
                "Use /simulate-training-session to train on your gaming sessions",
                "Watch as bots continuously improve your gaming experience"
            ]
        }
        
    except Exception as e:
        logger.error(f"Demo bot ecosystem creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Demo creation failed: {str(e)}")