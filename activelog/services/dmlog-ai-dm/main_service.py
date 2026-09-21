"""
AI DM Assistant Main Service

Orchestrates all AI DM components to provide comprehensive DM assistance
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .models.base import (
    Campaign, Player, SessionState, GameMetrics, DecisionContext
)
from .managers.narrative_manager import NarrativeFlowManager
from .managers.difficulty_manager import DifficultyManager
from .managers.dramatic_timing_manager import DramaticTimingManager
from .managers.engagement_monitor import PlayerEngagementMonitor
from .assistants.improvisation_assistant import ImprovisationAssistant
from .utils.lore_consistency_checker import LoreConsistencyChecker
from .utils.ai_client import AIClient
from .config import AI_DM_CONFIG, DATABASE_CONFIG, LOGGING_CONFIG

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOGGING_CONFIG["level"]),
    format=LOGGING_CONFIG["format"],
    filename=LOGGING_CONFIG.get("file")
)
logger = logging.getLogger(__name__)


class AIDMService:
    """Main AI DM Assistant service orchestrator"""
    
    def __init__(self):
        # Initialize AI client
        self.ai_client = AIClient()
        
        # Initialize all managers and assistants
        self.narrative_manager = NarrativeFlowManager(self.ai_client)
        self.difficulty_manager = DifficultyManager(self.ai_client)
        self.timing_manager = DramaticTimingManager(self.ai_client)
        self.engagement_monitor = PlayerEngagementMonitor(self.ai_client)
        self.improvisation_assistant = ImprovisationAssistant(self.ai_client)
        self.lore_checker = LoreConsistencyChecker(self.ai_client)
        
        # Service state
        self.active_campaigns: Dict[str, Campaign] = {}
        self.active_sessions: Dict[str, SessionState] = {}
        self.service_metrics: Dict[str, Any] = {
            "requests_processed": 0,
            "campaigns_managed": 0,
            "sessions_run": 0,
            "start_time": datetime.utcnow()
        }
    
    async def initialize_service(self) -> None:
        """Initialize the AI DM service"""
        try:
            logger.info("Initializing AI DM Assistant Service")
            
            # Initialize all components
            # (Individual component initialization happens when campaigns are loaded)
            
            logger.info("AI DM Assistant Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing AI DM service: {e}")
            raise
    
    async def create_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and initialize a new campaign"""
        try:
            campaign = Campaign(**campaign_data)
            
            # Initialize managers for this campaign
            await self.narrative_manager.initialize_narrative(campaign, None)
            await self.difficulty_manager.initialize_difficulty_tracking(campaign.players)
            await self.timing_manager.initialize_dramatic_timing(campaign, [])
            await self.engagement_monitor.initialize_monitoring(campaign.players)
            await self.improvisation_assistant.initialize_improvisation(campaign)
            await self.lore_checker.initialize_lore_database(campaign)
            
            # Store campaign
            self.active_campaigns[campaign.id] = campaign
            self.service_metrics["campaigns_managed"] += 1
            
            logger.info(f"Campaign created: {campaign.name} ({campaign.id})")
            
            return {
                "success": True,
                "campaign_id": campaign.id,
                "campaign_name": campaign.name,
                "players_count": len(campaign.players),
                "initialization_complete": True
            }
            
        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_session(self, campaign_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new game session"""
        try:
            if campaign_id not in self.active_campaigns:
                return {"success": False, "error": "Campaign not found"}
            
            campaign = self.active_campaigns[campaign_id]
            
            # Create session state
            session_state = SessionState(
                session_id=session_data.get("session_id", f"session_{datetime.utcnow().isoformat()}"),
                current_scene=session_data.get("initial_scene", "Session beginning"),
                active_plotlines=campaign.active_plotlines,
            )
            
            # Initialize session in all managers
            await self.narrative_manager.initialize_narrative(campaign, session_state)
            await self.timing_manager.initialize_dramatic_timing(campaign, campaign.main_storylines)
            
            # Store active session
            self.active_sessions[session_state.session_id] = session_state
            self.service_metrics["sessions_run"] += 1
            
            logger.info(f"Session started: {session_state.session_id} for campaign {campaign.name}")
            
            return {
                "success": True,
                "session_id": session_state.session_id,
                "campaign_id": campaign_id,
                "initial_recommendations": await self._generate_session_start_recommendations(
                    campaign, session_state
                )
            }
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_player_action(self, session_id: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a player action and get AI DM assistance"""
        try:
            if session_id not in self.active_sessions:
                return {"error": "Session not found"}
            
            session_state = self.active_sessions[session_id]
            self.service_metrics["requests_processed"] += 1
            
            # Process action through all relevant managers
            results = {}
            
            # Narrative flow analysis
            narrative_result = await self.narrative_manager.process_player_action(action_data, session_state)
            results["narrative_analysis"] = narrative_result
            
            # Record for difficulty tracking
            if action_data.get("player_id"):
                await self.difficulty_manager.record_player_outcome(
                    action_data["player_id"], 
                    action_data.get("outcome", {})
                )
            
            # Record for engagement monitoring
            if action_data.get("player_id"):
                await self.engagement_monitor.record_player_action(
                    action_data["player_id"], action_data
                )
            
            # Check for dramatic timing opportunities
            timing_analysis = await self.timing_manager.analyze_dramatic_timing(
                session_state, {}  # Would pass player states
            )
            results["timing_analysis"] = timing_analysis
            
            # Handle unexpected actions if needed
            if action_data.get("unexpected", False):
                improv_result = await self.improvisation_assistant.handle_unexpected_action(
                    action_data, session_state
                )
                results["improvisation"] = improv_result
            
            # Verify against lore if statement made
            if action_data.get("statement"):
                lore_check = await self.lore_checker.verify_statement(
                    action_data["statement"], {"session_id": session_id}
                )
                results["lore_consistency"] = lore_check
            
            # Generate comprehensive DM guidance
            dm_guidance = await self._generate_dm_guidance(results, action_data, session_state)
            
            return {
                "action_processed": True,
                "analysis_results": results,
                "dm_guidance": dm_guidance,
                "session_updates": await self._generate_session_updates(results, session_state)
            }
            
        except Exception as e:
            logger.error(f"Error processing player action: {e}")
            return {"error": str(e)}
    
    async def get_session_assistance(self, session_id: str, assistance_type: str,
                                   context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get specific assistance for the current session"""
        try:
            if session_id not in self.active_sessions:
                return {"error": "Session not found"}
            
            session_state = self.active_sessions[session_id]
            context = context or {}
            
            if assistance_type == "narrative_suggestions":
                return await self.narrative_manager.suggest_story_continuation(session_state)
            
            elif assistance_type == "difficulty_adjustment":
                return await self.difficulty_manager.get_party_difficulty_report()
            
            elif assistance_type == "dramatic_timing":
                return await self.timing_manager.get_dramatic_pacing_report(session_state)
            
            elif assistance_type == "engagement_check":
                return await self.engagement_monitor.check_engagement_levels(session_state)
            
            elif assistance_type == "improvisation_help":
                return await self.improvisation_assistant.get_improvisation_suggestions(context)
            
            elif assistance_type == "lore_verification":
                if "query" in context:
                    return await self.lore_checker.get_lore_suggestions(context["query"], context)
                else:
                    return {"error": "Query required for lore verification"}
            
            elif assistance_type == "comprehensive_analysis":
                return await self._generate_comprehensive_session_analysis(session_state)
            
            else:
                return {"error": f"Unknown assistance type: {assistance_type}"}
            
        except Exception as e:
            logger.error(f"Error providing session assistance: {e}")
            return {"error": str(e)}
    
    async def end_session(self, session_id: str) -> Dict[str, Any]:
        """End a game session and generate summary"""
        try:
            if session_id not in self.active_sessions:
                return {"error": "Session not found"}
            
            session_state = self.active_sessions[session_id]
            
            # Generate session summary
            session_summary = await self._generate_session_summary(session_state)
            
            # Get final reports from all managers
            narrative_report = await self.narrative_manager.get_story_health_report(session_state)
            engagement_summary = await self.engagement_monitor.get_party_engagement_summary()
            difficulty_report = await self.difficulty_manager.get_party_difficulty_report()
            
            # Clean up session
            del self.active_sessions[session_id]
            
            logger.info(f"Session ended: {session_id}")
            
            return {
                "session_ended": True,
                "session_id": session_id,
                "session_summary": session_summary,
                "final_reports": {
                    "narrative": narrative_report,
                    "engagement": engagement_summary,
                    "difficulty": difficulty_report
                },
                "recommendations_for_next_session": await self._generate_next_session_recommendations(
                    session_summary
                )
            }
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return {"error": str(e)}
    
    async def get_campaign_overview(self, campaign_id: str) -> Dict[str, Any]:
        """Get comprehensive campaign overview"""
        try:
            if campaign_id not in self.active_campaigns:
                return {"error": "Campaign not found"}
            
            campaign = self.active_campaigns[campaign_id]
            
            # Get status from all managers
            lore_report = await self.lore_checker.perform_full_consistency_check()
            
            overview = {
                "campaign_info": {
                    "id": campaign.id,
                    "name": campaign.name,
                    "description": campaign.description,
                    "theme": campaign.theme,
                    "players": len(campaign.players),
                    "sessions": len(campaign.sessions)
                },
                "story_status": {
                    "main_storylines": len(campaign.main_storylines),
                    "active_plotlines": len(campaign.active_plotlines),
                    "completed_storylines": len(campaign.completed_storylines)
                },
                "world_state": {
                    "lore_entries": len(campaign.lore_database),
                    "lore_consistency": lore_report.get("overall_consistency_score", 1.0),
                    "npcs": len(campaign.npc_registry),
                    "locations": len(campaign.location_registry)
                },
                "player_analysis": await self._generate_campaign_player_analysis(campaign),
                "health_metrics": await self._generate_campaign_health_metrics(campaign)
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Error generating campaign overview: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _generate_session_start_recommendations(self, campaign: Campaign, 
                                                    session_state: SessionState) -> List[str]:
        """Generate recommendations for starting a session"""
        recommendations = []
        
        # Check if players need recap
        if len(campaign.sessions) > 0:
            recommendations.append("Consider providing a brief recap of previous session")
        
        # Check for pending storylines
        if len(campaign.active_plotlines) > 3:
            recommendations.append("Focus on 1-2 active plotlines to avoid confusion")
        
        # Check player engagement patterns
        # (Would analyze historical data)
        recommendations.append("Monitor player engagement and adjust pacing accordingly")
        
        return recommendations
    
    async def _generate_dm_guidance(self, analysis_results: Dict[str, Any],
                                  action_data: Dict[str, Any], 
                                  session_state: SessionState) -> Dict[str, Any]:
        """Generate comprehensive DM guidance"""
        guidance = {
            "immediate_actions": [],
            "considerations": [],
            "opportunities": [],
            "warnings": []
        }
        
        # Extract guidance from narrative analysis
        if "narrative_analysis" in analysis_results:
            narrative = analysis_results["narrative_analysis"]
            if "narrative_guidance" in narrative:
                guidance["immediate_actions"].extend(
                    narrative["narrative_guidance"].get("immediate_suggestions", [])
                )
                guidance["opportunities"].extend(
                    narrative["narrative_guidance"].get("foreshadowing_opportunities", [])
                )
        
        # Extract guidance from timing analysis
        if "timing_analysis" in analysis_results:
            timing = analysis_results["timing_analysis"]
            guidance["immediate_actions"].extend(timing.get("recommendations", []))
        
        # Extract guidance from improvisation
        if "improvisation" in analysis_results:
            improv = analysis_results["improvisation"]
            guidance["immediate_actions"].extend(improv.get("follow_up_suggestions", []))
        
        # Check for lore consistency issues
        if "lore_consistency" in analysis_results:
            lore = analysis_results["lore_consistency"]
            if not lore.get("consistent", True):
                guidance["warnings"].append("Statement may conflict with established lore")
        
        return guidance
    
    async def _generate_session_updates(self, analysis_results: Dict[str, Any],
                                      session_state: SessionState) -> Dict[str, Any]:
        """Generate session state updates"""
        updates = {}
        
        # Update scene if narrative suggests it
        if "narrative_analysis" in analysis_results:
            transitions = analysis_results["narrative_analysis"].get("transitions_triggered", [])
            if transitions:
                updates["scene_transitions"] = transitions
        
        # Update tension level if needed
        # (Based on timing analysis)
        
        return updates
    
    async def _generate_comprehensive_session_analysis(self, session_state: SessionState) -> Dict[str, Any]:
        """Generate comprehensive analysis of current session state"""
        analysis = {}
        
        # Get reports from all managers
        analysis["narrative"] = await self.narrative_manager.get_story_health_report(session_state)
        analysis["engagement"] = await self.engagement_monitor.get_party_engagement_summary()
        analysis["difficulty"] = await self.difficulty_manager.get_party_difficulty_report()
        analysis["timing"] = await self.timing_manager.get_dramatic_pacing_report(session_state)
        
        # Generate overall assessment
        analysis["overall_health"] = await self._calculate_session_health(analysis)
        
        return analysis
    
    async def _calculate_session_health(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall session health score"""
        health_factors = []
        
        # Narrative health
        if "narrative" in analysis:
            health_factors.append(analysis["narrative"].get("health_score", 0.7))
        
        # Engagement health
        if "engagement" in analysis:
            party_metrics = analysis["engagement"].get("party_metrics", {})
            avg_engagement = party_metrics.get("average_engagement", 2) / 4  # Normalize to 0-1
            health_factors.append(avg_engagement)
        
        # Calculate overall
        if health_factors:
            overall_health = sum(health_factors) / len(health_factors)
        else:
            overall_health = 0.5
        
        return {
            "overall_score": overall_health,
            "health_level": "excellent" if overall_health > 0.8 else "good" if overall_health > 0.6 else "needs_attention",
            "factors": health_factors
        }
    
    async def _generate_session_summary(self, session_state: SessionState) -> Dict[str, Any]:
        """Generate session summary"""
        return {
            "session_id": session_state.session_id,
            "duration_minutes": session_state.time_elapsed,
            "scenes_completed": session_state.scene_count,
            "final_tension": session_state.current_tension.value,
            "active_plotlines": session_state.active_plotlines,
            "key_events": []  # Would be populated from session events
        }
    
    async def _generate_next_session_recommendations(self, session_summary: Dict[str, Any]) -> List[str]:
        """Generate recommendations for next session"""
        recommendations = []
        
        # Based on tension level
        tension = session_summary.get("final_tension", "moderate")
        if tension == "high":
            recommendations.append("Consider resolution or escalation in next session")
        elif tension == "low":
            recommendations.append("Build tension and introduce new complications")
        
        # Based on plotlines
        active_plotlines = session_summary.get("active_plotlines", [])
        if len(active_plotlines) > 4:
            recommendations.append("Focus on fewer plotlines next session")
        
        return recommendations
    
    async def _generate_campaign_player_analysis(self, campaign: Campaign) -> Dict[str, Any]:
        """Generate analysis of players in campaign"""
        player_analysis = {}
        
        for player in campaign.players:
            analysis = await self.engagement_monitor.get_player_engagement_report(player.id)
            difficulty_analysis = await self.difficulty_manager.get_player_performance_analysis(player.id)
            
            player_analysis[player.id] = {
                "name": player.name,
                "character": player.character_name,
                "engagement": analysis.get("current_engagement", "moderate"),
                "performance": difficulty_analysis.get("overall_success_rate", 0.6),
                "needs_attention": analysis.get("current_engagement") in ["disengaged", "low"]
            }
        
        return player_analysis
    
    async def _generate_campaign_health_metrics(self, campaign: Campaign) -> Dict[str, Any]:
        """Generate overall campaign health metrics"""
        return {
            "story_coherence": 0.85,  # Would get from narrative manager
            "lore_consistency": self.lore_checker.consistency_score,
            "player_satisfaction": 0.8,  # Would calculate from engagement data
            "narrative_momentum": 0.7   # Would get from narrative manager
        }


# FastAPI Application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AI DM Assistant Service")
    await ai_dm_service.initialize_service()
    yield
    # Shutdown
    logger.info("Shutting down AI DM Assistant Service")


app = FastAPI(
    title="AI DM Assistant",
    description="Comprehensive AI assistant for D&D Dungeon Masters",
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

# Initialize service
ai_dm_service = AIDMService()

# API Models
class ActionRequest(BaseModel):
    session_id: str
    player_id: Optional[str] = None
    action_type: str
    description: str
    outcome: Optional[Dict[str, Any]] = None
    unexpected: bool = False
    statement: Optional[str] = None

class AssistanceRequest(BaseModel):
    session_id: str
    assistance_type: str
    context: Optional[Dict[str, Any]] = None

# API Endpoints

@app.post("/campaigns")
async def create_campaign(campaign_data: Dict[str, Any]):
    """Create a new campaign"""
    return await ai_dm_service.create_campaign(campaign_data)

@app.post("/campaigns/{campaign_id}/sessions")
async def start_session(campaign_id: str, session_data: Dict[str, Any]):
    """Start a new session"""
    return await ai_dm_service.start_session(campaign_id, session_data)

@app.post("/sessions/{session_id}/actions")
async def process_action(session_id: str, action: ActionRequest):
    """Process a player action"""
    return await ai_dm_service.process_player_action(session_id, action.dict())

@app.post("/sessions/{session_id}/assistance")
async def get_assistance(session_id: str, request: AssistanceRequest):
    """Get AI assistance for the session"""
    return await ai_dm_service.get_session_assistance(
        session_id, request.assistance_type, request.context
    )

@app.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    """End a session"""
    return await ai_dm_service.end_session(session_id)

@app.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get campaign overview"""
    return await ai_dm_service.get_campaign_overview(campaign_id)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI DM Assistant",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/stats")
async def get_stats():
    """Get service statistics"""
    return ai_dm_service.service_metrics


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)