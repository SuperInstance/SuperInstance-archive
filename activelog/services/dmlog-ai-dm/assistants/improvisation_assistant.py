"""
Improvisation Assistant for handling unexpected player actions and generating content on-the-fly
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import random

from ..models.base import (
    Campaign, SessionState, Player, DecisionContext, AIResponse,
    LoreEntry, NarrativeEvent
)
from ..config import IMPROVISATION_CONFIG
from ..utils.ai_client import AIClient
from ..utils.random_tables import RandomTables


logger = logging.getLogger(__name__)


class ImprovisationAssistant:
    """Assists DMs with improvising content for unexpected player actions"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.random_tables = RandomTables()
        
        # Improvisation context
        self.active_scenarios: Dict[str, Dict[str, Any]] = {}
        self.improvisation_history: List[Dict[str, Any]] = []
        self.quick_response_cache: Dict[str, AIResponse] = {}
        
        # Content generators
        self.npc_generator = NPCGenerator(ai_client)
        self.location_generator = LocationGenerator(ai_client)
        self.consequence_predictor = ConsequencePredictor(ai_client)
        self.connection_finder = ConnectionFinder(ai_client)
        
        # Response patterns
        self.response_templates: Dict[str, List[str]] = {}
        self.last_improvisation_time: Optional[datetime] = None
    
    async def initialize_improvisation(self, campaign: Campaign) -> None:
        """Initialize improvisation system for a campaign"""
        try:
            # Load campaign context
            self.campaign_context = {
                "world_state": campaign.world_state,
                "lore_database": campaign.lore_database,
                "active_plotlines": campaign.active_plotlines,
                "npc_registry": campaign.npc_registry,
                "location_registry": campaign.location_registry
            }
            
            # Initialize response templates
            await self._load_response_templates()
            
            # Initialize random tables for quick generation
            await self.random_tables.initialize()
            
            logger.info("Improvisation assistant initialized")
            
        except Exception as e:
            logger.error(f"Error initializing improvisation assistant: {e}")
            raise
    
    async def handle_unexpected_action(self, action: Dict[str, Any], 
                                     session_state: SessionState) -> Dict[str, Any]:
        """Handle an unexpected player action"""
        try:
            action_type = action.get("type", "unknown")
            player_id = action.get("player_id", "")
            description = action.get("description", "")
            urgency = action.get("urgency", "medium")
            
            # Determine scenario category
            scenario_category = await self._categorize_scenario(action, session_state)
            
            # Generate quick response if high urgency
            if urgency == "high":
                response = await self._generate_quick_response(
                    scenario_category, action, session_state
                )
            else:
                response = await self._generate_detailed_response(
                    scenario_category, action, session_state
                )
            
            # Record improvisation
            await self._record_improvisation(action, response, scenario_category)
            
            return {
                "scenario_category": scenario_category,
                "response": response,
                "follow_up_suggestions": await self._generate_follow_up_suggestions(
                    response, action, session_state
                ),
                "world_state_updates": await self._suggest_world_state_updates(
                    response, action
                )
            }
            
        except Exception as e:
            logger.error(f"Error handling unexpected action: {e}")
            return {
                "error": str(e),
                "fallback_response": await self._generate_fallback_response(action)
            }
    
    async def generate_improvised_npc(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an NPC on the fly"""
        try:
            location = context.get("location", "unknown")
            interaction_type = context.get("interaction_type", "casual")
            plot_relevance = context.get("plot_relevance", "none")
            required_traits = context.get("required_traits", [])
            
            npc_data = await self.npc_generator.generate_quick_npc(
                location, interaction_type, plot_relevance, required_traits
            )
            
            # Connect to existing plot if relevant
            if plot_relevance != "none":
                plot_connections = await self.connection_finder.find_plot_connections(
                    npc_data, self.campaign_context["active_plotlines"]
                )
                npc_data["plot_connections"] = plot_connections
            
            # Generate conversation starters
            conversation_hooks = await self._generate_conversation_hooks(npc_data, context)
            npc_data["conversation_hooks"] = conversation_hooks
            
            return {
                "npc": npc_data,
                "usage_tips": await self._generate_npc_usage_tips(npc_data, context),
                "potential_developments": await self._predict_npc_developments(npc_data)
            }
            
        except Exception as e:
            logger.error(f"Error generating improvised NPC: {e}")
            return {"error": str(e)}
    
    async def generate_improvised_location(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a location on the fly"""
        try:
            location_type = context.get("type", "generic")
            atmosphere = context.get("atmosphere", "neutral")
            purpose = context.get("purpose", "exploration")
            connections_needed = context.get("connections_needed", [])
            
            location_data = await self.location_generator.generate_quick_location(
                location_type, atmosphere, purpose, connections_needed
            )
            
            # Add interactive elements
            interactive_elements = await self._generate_interactive_elements(
                location_data, context
            )
            location_data["interactive_elements"] = interactive_elements
            
            # Suggest encounter possibilities
            encounter_possibilities = await self._suggest_location_encounters(
                location_data, context
            )
            
            return {
                "location": location_data,
                "encounter_possibilities": encounter_possibilities,
                "exploration_opportunities": await self._generate_exploration_opportunities(
                    location_data
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating improvised location: {e}")
            return {"error": str(e)}
    
    async def suggest_fair_ruling(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest a fair ruling for an unconventional situation"""
        try:
            situation_description = situation.get("description", "")
            rules_involved = situation.get("rules_involved", [])
            player_request = situation.get("player_request", "")
            precedents = situation.get("precedents", [])
            
            # Generate ruling options
            ruling_options = await self._generate_ruling_options(
                situation_description, rules_involved, player_request
            )
            
            # Evaluate fairness of each option
            fairness_analysis = await self._evaluate_ruling_fairness(
                ruling_options, situation
            )
            
            # Predict consequences
            consequence_predictions = await self.consequence_predictor.predict_ruling_consequences(
                ruling_options, situation
            )
            
            # Generate recommended ruling
            recommended_ruling = await self._select_recommended_ruling(
                ruling_options, fairness_analysis, consequence_predictions
            )
            
            return {
                "ruling_options": ruling_options,
                "fairness_analysis": fairness_analysis,
                "consequence_predictions": consequence_predictions,
                "recommended_ruling": recommended_ruling,
                "reasoning": await self._generate_ruling_reasoning(
                    recommended_ruling, fairness_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Error suggesting fair ruling: {e}")
            return {"error": str(e)}
    
    async def handle_creative_solution_attempt(self, solution: Dict[str, Any],
                                             session_state: SessionState) -> Dict[str, Any]:
        """Handle a creative solution attempt from players"""
        try:
            solution_description = solution.get("description", "")
            target_problem = solution.get("target_problem", "")
            player_id = solution.get("player_id", "")
            resources_used = solution.get("resources_used", [])
            
            # Analyze solution creativity and feasibility
            creativity_analysis = await self._analyze_solution_creativity(
                solution_description, target_problem
            )
            
            feasibility_analysis = await self._analyze_solution_feasibility(
                solution_description, resources_used, session_state
            )
            
            # Generate outcome options
            outcome_options = await self._generate_solution_outcomes(
                solution, creativity_analysis, feasibility_analysis
            )
            
            # Suggest skill checks or requirements
            requirements = await self._suggest_solution_requirements(
                solution, outcome_options
            )
            
            # Predict narrative impact
            narrative_impact = await self._predict_solution_narrative_impact(
                solution, outcome_options, session_state
            )
            
            return {
                "creativity_analysis": creativity_analysis,
                "feasibility_analysis": feasibility_analysis,
                "outcome_options": outcome_options,
                "requirements": requirements,
                "narrative_impact": narrative_impact,
                "dm_guidance": await self._generate_creative_solution_guidance(
                    solution, outcome_options
                )
            }
            
        except Exception as e:
            logger.error(f"Error handling creative solution attempt: {e}")
            return {"error": str(e)}
    
    async def generate_scene_continuation(self, current_scene: Dict[str, Any],
                                        player_actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate ways to continue a scene after unexpected developments"""
        try:
            scene_type = current_scene.get("type", "unknown")
            scene_context = current_scene.get("context", {})
            unexpected_developments = current_scene.get("unexpected_developments", [])
            
            # Analyze scene state
            scene_analysis = await self._analyze_scene_state(
                current_scene, player_actions, unexpected_developments
            )
            
            # Generate continuation options
            continuation_options = await self._generate_scene_continuations(
                scene_analysis, player_actions
            )
            
            # Connect to larger story
            story_connections = await self.connection_finder.find_story_connections(
                continuation_options, self.campaign_context
            )
            
            # Prioritize options
            prioritized_options = self._prioritize_continuation_options(
                continuation_options, story_connections, scene_analysis
            )
            
            return {
                "scene_analysis": scene_analysis,
                "continuation_options": prioritized_options,
                "story_connections": story_connections,
                "transition_suggestions": await self._generate_transition_suggestions(
                    current_scene, prioritized_options[0] if prioritized_options else None
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating scene continuation: {e}")
            return {"error": str(e)}
    
    async def get_improvisation_suggestions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get general improvisation suggestions based on current context"""
        try:
            situation_type = context.get("situation_type", "general")
            urgency = context.get("urgency", "medium")
            available_time = context.get("available_time", 30)  # seconds
            
            # Get quick suggestions
            if available_time < 15:
                suggestions = await self._get_quick_suggestions(situation_type, context)
            else:
                suggestions = await self._get_detailed_suggestions(situation_type, context)
            
            # Add random elements if needed
            if context.get("need_randomness", False):
                random_elements = await self._generate_random_elements(situation_type)
                suggestions["random_elements"] = random_elements
            
            # Provide implementation guidance
            implementation_guidance = await self._generate_implementation_guidance(
                suggestions, context
            )
            
            return {
                "suggestions": suggestions,
                "implementation_guidance": implementation_guidance,
                "confidence_level": self._calculate_suggestion_confidence(context),
                "follow_up_hooks": await self._generate_suggestion_follow_ups(suggestions)
            }
            
        except Exception as e:
            logger.error(f"Error getting improvisation suggestions: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _categorize_scenario(self, action: Dict[str, Any], 
                                 session_state: SessionState) -> str:
        """Categorize the improvisation scenario"""
        action_description = action.get("description", "").lower()
        
        # Check against configured scenario categories
        for category, config in IMPROVISATION_CONFIG["scenario_categories"].items():
            for trigger in config["triggers"]:
                if trigger in action_description:
                    return category
        
        # Default categorization logic
        if "attack" in action_description or "fight" in action_description:
            return "unexpected_combat"
        elif "go to" in action_description or "visit" in action_description:
            return "off_script_exploration"
        elif "talk to" in action_description or "ask" in action_description:
            return "social_improvisation"
        else:
            return "creative_problem_solving"
    
    async def _generate_quick_response(self, scenario_category: str, 
                                     action: Dict[str, Any],
                                     session_state: SessionState) -> AIResponse:
        """Generate a quick response for time-sensitive situations"""
        try:
            # Check cache first
            cache_key = f"{scenario_category}_{hash(str(action))}"
            if cache_key in self.quick_response_cache:
                cached_response = self.quick_response_cache[cache_key]
                if (datetime.utcnow() - cached_response.created_at).seconds < 300:  # 5 minutes
                    return cached_response
            
            # Generate quick response
            config = IMPROVISATION_CONFIG["scenario_categories"].get(scenario_category, {})
            response_options = config.get("responses", ["Acknowledge and adapt"])
            
            selected_response = random.choice(response_options)
            
            # Use AI for quick elaboration
            prompt = f"""
            Player unexpected action: {action.get('description', '')}
            Scenario category: {scenario_category}
            Quick response approach: {selected_response}
            
            Provide a brief, immediate response (2-3 sentences) that:
            1. Acknowledges the player action
            2. Provides immediate guidance
            3. Maintains story flow
            """
            
            ai_content = await self.ai_client.generate_completion(
                prompt, max_tokens=150, temperature=0.8
            )
            
            response = AIResponse(
                response_type="quick_improvisation",
                context=scenario_category,
                content=ai_content,
                confidence=0.7
            )
            
            # Cache the response
            self.quick_response_cache[cache_key] = response
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating quick response: {e}")
            return AIResponse(
                response_type="fallback",
                context="error",
                content="Let's see what happens...",
                confidence=0.3
            )
    
    async def _generate_detailed_response(self, scenario_category: str,
                                        action: Dict[str, Any],
                                        session_state: SessionState) -> AIResponse:
        """Generate a detailed response with more analysis time"""
        try:
            prompt = f"""
            Player Action: {action.get('description', '')}
            Scenario Category: {scenario_category}
            Current Scene: {session_state.current_scene}
            Active Plotlines: {session_state.active_plotlines}
            
            Generate a detailed improvisation response that includes:
            1. Immediate consequence or outcome
            2. How this connects to or affects the story
            3. Opportunities this creates
            4. Potential complications
            5. Next steps or options for the DM
            
            Make the response helpful and actionable.
            """
            
            ai_content = await self.ai_client.generate_completion(
                prompt, max_tokens=400, temperature=0.7
            )
            
            return AIResponse(
                response_type="detailed_improvisation",
                context=scenario_category,
                content=ai_content,
                confidence=0.8
            )
            
        except Exception as e:
            logger.error(f"Error generating detailed response: {e}")
            return await self._generate_quick_response(scenario_category, action, session_state)
    
    async def _record_improvisation(self, action: Dict[str, Any], 
                                  response: AIResponse,
                                  scenario_category: str) -> None:
        """Record improvisation for learning and analysis"""
        improvisation_record = {
            "timestamp": datetime.utcnow(),
            "action": action,
            "response": response.dict(),
            "scenario_category": scenario_category,
            "effectiveness": None  # To be updated later based on feedback
        }
        
        self.improvisation_history.append(improvisation_record)
        self.last_improvisation_time = datetime.utcnow()
    
    async def _generate_follow_up_suggestions(self, response: AIResponse,
                                            action: Dict[str, Any],
                                            session_state: SessionState) -> List[str]:
        """Generate follow-up suggestions for after the improvisation"""
        suggestions = []
        
        if response.response_type == "quick_improvisation":
            suggestions.append("Take a moment to think through longer-term consequences")
            suggestions.append("Consider how this affects ongoing plotlines")
        
        if action.get("type") == "creative_solution":
            suggestions.append("Reward creative thinking with interesting outcomes")
            suggestions.append("Note this for future character development")
        
        if "combat" in response.context:
            suggestions.append("Be prepared to adjust encounter difficulty")
            suggestions.append("Consider environmental factors in the fight")
        
        return suggestions
    
    async def _suggest_world_state_updates(self, response: AIResponse,
                                         action: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest updates to world state based on improvisation"""
        updates = []
        
        # Location updates
        if "location" in action.get("description", "").lower():
            updates.append({
                "type": "location",
                "description": "New location discovered or visited",
                "data": {"location": action.get("location", "unknown")}
            })
        
        # NPC updates
        if "talk to" in action.get("description", "").lower():
            updates.append({
                "type": "npc_interaction",
                "description": "New NPC interaction occurred",
                "data": {"npc": action.get("npc", "improvised")}
            })
        
        # Plot updates
        if response.confidence > 0.7:
            updates.append({
                "type": "plot_development",
                "description": "Player action advances or creates plot thread",
                "data": {"action": action.get("description", "")}
            })
        
        return updates
    
    async def _generate_fallback_response(self, action: Dict[str, Any]) -> AIResponse:
        """Generate a fallback response when other methods fail"""
        fallback_responses = [
            "The situation is more complex than it initially appeared. Let me think about this...",
            "Interesting choice! Let's see how this plays out.",
            "Your character attempts this action. Roll a d20 and add your most relevant ability modifier.",
            "This creates an interesting situation. Give me a moment to consider the implications."
        ]
        
        return AIResponse(
            response_type="fallback",
            context="error_recovery",
            content=random.choice(fallback_responses),
            confidence=0.4
        )
    
    async def _load_response_templates(self) -> None:
        """Load response templates for common scenarios"""
        self.response_templates = {
            "unexpected_combat": [
                "Combat begins! Let's determine initiative and positioning.",
                "The situation escalates to violence. Roll initiative!",
                "Weapons are drawn! Time for combat."
            ],
            "off_script_exploration": [
                "You venture into unexplored territory...",
                "The path leads you to somewhere new...",
                "Your exploration reveals..."
            ],
            "social_improvisation": [
                "The NPC reacts to your approach...",
                "Your words have an unexpected effect...",
                "The conversation takes an interesting turn..."
            ],
            "creative_problem_solving": [
                "That's an innovative approach!",
                "Your creative solution might work if...",
                "Interesting idea! Let's see how it plays out."
            ]
        }
    
    async def _generate_conversation_hooks(self, npc_data: Dict[str, Any], 
                                         context: Dict[str, Any]) -> List[str]:
        """Generate conversation hooks for an improvised NPC"""
        hooks = []
        
        # Based on NPC background
        background = npc_data.get("background", "commoner")
        if background == "merchant":
            hooks.append("Complain about recent business troubles")
            hooks.append("Offer to sell something unusual")
        elif background == "guard":
            hooks.append("Ask about recent suspicious activity")
            hooks.append("Mention increased patrols")
        
        # Based on location
        location = context.get("location", "")
        if "tavern" in location.lower():
            hooks.append("Share local gossip")
            hooks.append("Offer to buy the party a drink")
        elif "market" in location.lower():
            hooks.append("Recommend the best shops")
            hooks.append("Warn about pickpockets")
        
        return hooks
    
    async def _generate_npc_usage_tips(self, npc_data: Dict[str, Any],
                                     context: Dict[str, Any]) -> List[str]:
        """Generate tips for using the improvised NPC"""
        tips = []
        
        personality = npc_data.get("personality", [])
        if "friendly" in personality:
            tips.append("NPC is helpful and willing to share information")
        if "suspicious" in personality:
            tips.append("NPC is wary of strangers and needs convincing")
        
        if npc_data.get("plot_connections"):
            tips.append("NPC has connections to ongoing plots - use carefully")
        
        tips.append("Remember to give NPC distinctive speech patterns or mannerisms")
        
        return tips
    
    async def _predict_npc_developments(self, npc_data: Dict[str, Any]) -> List[str]:
        """Predict how the NPC might develop in future sessions"""
        developments = []
        
        background = npc_data.get("background", "")
        if background in ["merchant", "noble"]:
            developments.append("Could become recurring contact for information or services")
        elif background in ["guard", "soldier"]:
            developments.append("Might provide security assistance or official backing")
        
        if npc_data.get("secrets"):
            developments.append("Secrets could be revealed later for plot development")
        
        return developments
    
    async def _generate_interactive_elements(self, location_data: Dict[str, Any],
                                           context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate interactive elements for a location"""
        elements = []
        
        location_type = location_data.get("type", "generic")
        
        if location_type == "tavern":
            elements.extend([
                {"type": "social", "description": "Patrons with stories to tell"},
                {"type": "information", "description": "Bulletin board with notices"},
                {"type": "services", "description": "Rooms for rent and meals"}
            ])
        elif location_type == "shop":
            elements.extend([
                {"type": "commerce", "description": "Goods for sale"},
                {"type": "information", "description": "Shopkeeper knows local news"},
                {"type": "social", "description": "Other customers to interact with"}
            ])
        elif location_type == "dungeon_room":
            elements.extend([
                {"type": "exploration", "description": "Hidden passages or secrets"},
                {"type": "hazard", "description": "Environmental dangers"},
                {"type": "loot", "description": "Treasure or useful items"}
            ])
        
        return elements
    
    async def _suggest_location_encounters(self, location_data: Dict[str, Any],
                                         context: Dict[str, Any]) -> List[str]:
        """Suggest possible encounters for the location"""
        encounters = []
        
        atmosphere = location_data.get("atmosphere", "neutral")
        location_type = location_data.get("type", "generic")
        
        if atmosphere == "dangerous":
            encounters.append("Hostile creatures or bandits")
            encounters.append("Environmental hazards")
        elif atmosphere == "mysterious":
            encounters.append("Strange phenomena to investigate")
            encounters.append("Cryptic NPCs with hidden knowledge")
        elif atmosphere == "peaceful":
            encounters.append("Friendly locals seeking help")
            encounters.append("Opportunities for rest and recovery")
        
        return encounters
    
    async def _generate_exploration_opportunities(self, location_data: Dict[str, Any]) -> List[str]:
        """Generate exploration opportunities for the location"""
        opportunities = []
        
        features = location_data.get("notable_features", [])
        
        for feature in features:
            if "door" in feature.lower():
                opportunities.append("Investigate locked or hidden doors")
            elif "book" in feature.lower() or "scroll" in feature.lower():
                opportunities.append("Research information in texts")
            elif "statue" in feature.lower() or "altar" in feature.lower():
                opportunities.append("Examine religious or magical artifacts")
        
        # Default opportunities
        opportunities.extend([
            "Search for hidden compartments or passages",
            "Look for clues about the location's history",
            "Check for valuable or useful items"
        ])
        
        return opportunities
    
    async def _generate_ruling_options(self, situation_description: str,
                                     rules_involved: List[str],
                                     player_request: str) -> List[Dict[str, Any]]:
        """Generate ruling options for an unconventional situation"""
        options = []
        
        # Strict interpretation option
        options.append({
            "type": "strict",
            "description": "Apply rules as written, no flexibility",
            "reasoning": "Maintains consistency and precedent",
            "player_satisfaction": 0.3,
            "narrative_flow": 0.4
        })
        
        # Flexible interpretation option
        options.append({
            "type": "flexible",
            "description": "Allow creative interpretation within reason",
            "reasoning": "Encourages creativity while maintaining balance",
            "player_satisfaction": 0.8,
            "narrative_flow": 0.7
        })
        
        # Compromise option
        options.append({
            "type": "compromise",
            "description": "Meet halfway with modified requirements",
            "reasoning": "Balances rules adherence with player agency",
            "player_satisfaction": 0.6,
            "narrative_flow": 0.6
        })
        
        # Rule of cool option
        if "creative" in player_request.lower() or "cool" in situation_description.lower():
            options.append({
                "type": "rule_of_cool",
                "description": "Allow it because it's awesome",
                "reasoning": "Prioritizes fun and memorable moments",
                "player_satisfaction": 0.9,
                "narrative_flow": 0.8
            })
        
        return options
    
    async def _evaluate_ruling_fairness(self, ruling_options: List[Dict[str, Any]],
                                       situation: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate fairness of ruling options"""
        fairness_scores = {}
        
        for option in ruling_options:
            fairness_score = 0.5  # Base fairness
            
            # Adjust based on option type
            if option["type"] == "strict":
                fairness_score += 0.2  # Consistent application is fair
            elif option["type"] == "flexible":
                fairness_score += 0.1  # Some flexibility is fair
            elif option["type"] == "rule_of_cool":
                fairness_score -= 0.1  # Might be unfair to other players
            
            # Consider precedents
            precedents = situation.get("precedents", [])
            if precedents:
                # Consistency with precedents improves fairness
                fairness_score += 0.1
            
            fairness_scores[option["type"]] = fairness_score
        
        return fairness_scores
    
    async def _select_recommended_ruling(self, ruling_options: List[Dict[str, Any]],
                                       fairness_analysis: Dict[str, Any],
                                       consequence_predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Select the recommended ruling based on analysis"""
        best_option = None
        best_score = 0
        
        for option in ruling_options:
            option_type = option["type"]
            
            # Calculate composite score
            fairness = fairness_analysis.get(option_type, 0.5)
            player_satisfaction = option.get("player_satisfaction", 0.5)
            narrative_flow = option.get("narrative_flow", 0.5)
            
            # Weight factors
            composite_score = (
                fairness * 0.4 +
                player_satisfaction * 0.3 +
                narrative_flow * 0.3
            )
            
            if composite_score > best_score:
                best_score = composite_score
                best_option = option
        
        return best_option or ruling_options[0]
    
    async def _generate_ruling_reasoning(self, recommended_ruling: Dict[str, Any],
                                       fairness_analysis: Dict[str, Any]) -> str:
        """Generate reasoning for the recommended ruling"""
        option_type = recommended_ruling["type"]
        
        reasoning_templates = {
            "strict": "This maintains consistency with the rules and sets clear precedent.",
            "flexible": "This allows for creativity while keeping the game balanced.",
            "compromise": "This balances rule adherence with player agency.",
            "rule_of_cool": "This prioritizes an awesome, memorable moment."
        }
        
        base_reasoning = reasoning_templates.get(option_type, "This seems like the best approach.")
        
        # Add fairness consideration
        fairness_score = fairness_analysis.get(option_type, 0.5)
        if fairness_score > 0.7:
            base_reasoning += " It's also fair to all players."
        elif fairness_score < 0.4:
            base_reasoning += " Consider how this might affect other players."
        
        return base_reasoning
    
    async def _analyze_solution_creativity(self, solution_description: str,
                                         target_problem: str) -> Dict[str, Any]:
        """Analyze the creativity of a proposed solution"""
        # Simple heuristic analysis
        creativity_indicators = [
            "unusual", "creative", "innovative", "unexpected", "clever",
            "outside the box", "unconventional", "novel"
        ]
        
        creativity_score = 0.5  # Base score
        
        # Check for creativity indicators
        for indicator in creativity_indicators:
            if indicator in solution_description.lower():
                creativity_score += 0.1
        
        # Check for combining different elements
        if "and" in solution_description or "with" in solution_description:
            creativity_score += 0.1
        
        # Cap at 1.0
        creativity_score = min(1.0, creativity_score)
        
        return {
            "creativity_score": creativity_score,
            "creativity_level": "high" if creativity_score > 0.7 else "moderate" if creativity_score > 0.4 else "low",
            "creative_elements": [indicator for indicator in creativity_indicators 
                                if indicator in solution_description.lower()]
        }
    
    async def _analyze_solution_feasibility(self, solution_description: str,
                                          resources_used: List[str],
                                          session_state: SessionState) -> Dict[str, Any]:
        """Analyze the feasibility of a proposed solution"""
        feasibility_score = 0.7  # Base feasibility
        
        constraints = []
        
        # Check resource availability
        # (This would check against actual character resources in a real implementation)
        
        # Check for impossible actions
        impossible_keywords = ["teleport", "fly", "invisible", "time travel"]
        for keyword in impossible_keywords:
            if keyword in solution_description.lower():
                feasibility_score -= 0.3
                constraints.append(f"'{keyword}' may not be possible without magic")
        
        # Check for reasonable actions
        reasonable_keywords = ["use", "combine", "move", "talk", "climb", "jump"]
        for keyword in reasonable_keywords:
            if keyword in solution_description.lower():
                feasibility_score += 0.1
        
        feasibility_score = max(0.0, min(1.0, feasibility_score))
        
        return {
            "feasibility_score": feasibility_score,
            "feasibility_level": "high" if feasibility_score > 0.7 else "moderate" if feasibility_score > 0.4 else "low",
            "constraints": constraints,
            "resource_requirements": resources_used
        }
    
    async def _generate_solution_outcomes(self, solution: Dict[str, Any],
                                        creativity_analysis: Dict[str, Any],
                                        feasibility_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate possible outcomes for a creative solution"""
        outcomes = []
        
        creativity_score = creativity_analysis["creativity_score"]
        feasibility_score = feasibility_analysis["feasibility_score"]
        
        # Success outcome
        success_probability = (creativity_score + feasibility_score) / 2
        outcomes.append({
            "type": "success",
            "probability": success_probability,
            "description": "The creative solution works as intended",
            "consequences": ["Problem solved", "Player feels rewarded for creativity"]
        })
        
        # Partial success outcome
        if creativity_score > 0.5:
            outcomes.append({
                "type": "partial_success",
                "probability": 0.3,
                "description": "The solution works but with unexpected complications",
                "consequences": ["Partial problem resolution", "New challenges created"]
            })
        
        # Failure outcome
        failure_probability = 1 - success_probability
        outcomes.append({
            "type": "failure",
            "probability": failure_probability,
            "description": "The solution doesn't work as expected",
            "consequences": ["Problem remains", "Possible negative consequences"]
        })
        
        return outcomes
    
    async def _suggest_solution_requirements(self, solution: Dict[str, Any],
                                           outcome_options: List[Dict[str, Any]]) -> List[str]:
        """Suggest requirements for implementing the creative solution"""
        requirements = []
        
        solution_description = solution.get("description", "").lower()
        
        # Physical actions
        if any(word in solution_description for word in ["climb", "jump", "lift"]):
            requirements.append("Strength or Athletics check")
        
        # Mental actions
        if any(word in solution_description for word in ["figure out", "solve", "analyze"]):
            requirements.append("Intelligence or Investigation check")
        
        # Social actions
        if any(word in solution_description for word in ["convince", "persuade", "deceive"]):
            requirements.append("Charisma-based skill check")
        
        # Magical actions
        if any(word in solution_description for word in ["magic", "spell", "enchant"]):
            requirements.append("Arcana check or spell slot expenditure")
        
        # Timing requirements
        if "quickly" in solution_description or "fast" in solution_description:
            requirements.append("Time pressure - must act in current turn")
        
        return requirements
    
    async def _predict_solution_narrative_impact(self, solution: Dict[str, Any],
                                               outcome_options: List[Dict[str, Any]],
                                               session_state: SessionState) -> Dict[str, Any]:
        """Predict the narrative impact of the creative solution"""
        impact = {
            "immediate_impact": "low",
            "long_term_impact": "low",
            "plot_relevance": "none",
            "character_development": "minimal"
        }
        
        creativity_score = 0.5  # Would get from previous analysis
        
        # High creativity solutions have more impact
        if creativity_score > 0.7:
            impact["immediate_impact"] = "high"
            impact["character_development"] = "significant"
        
        # Check if solution relates to active plotlines
        active_plotlines = session_state.active_plotlines
        solution_desc = solution.get("description", "").lower()
        
        for plotline in active_plotlines:
            # Simple keyword matching - would be more sophisticated in real implementation
            if any(keyword in solution_desc for keyword in ["villain", "mystery", "quest"]):
                impact["plot_relevance"] = "high"
                impact["long_term_impact"] = "moderate"
                break
        
        return impact
    
    async def _generate_creative_solution_guidance(self, solution: Dict[str, Any],
                                                 outcome_options: List[Dict[str, Any]]) -> List[str]:
        """Generate guidance for handling the creative solution"""
        guidance = []
        
        # Always encourage creativity
        guidance.append("Acknowledge the player's creative thinking")
        
        # Based on outcome probabilities
        success_option = next((o for o in outcome_options if o["type"] == "success"), None)
        if success_option and success_option["probability"] > 0.7:
            guidance.append("High chance of success - be generous with the outcome")
        elif success_option and success_option["probability"] < 0.4:
            guidance.append("Low chance of success - but allow partial success for effort")
        
        # General guidance
        guidance.extend([
            "Consider long-term implications of allowing this approach",
            "Set appropriate difficulty for skill checks",
            "Remember 'yes, and...' or 'no, but...' principles"
        ])
        
        return guidance
    
    # Additional helper methods would continue here...
    # For brevity, I'll include the essential structure and key methods
    
    def _calculate_suggestion_confidence(self, context: Dict[str, Any]) -> float:
        """Calculate confidence in suggestions based on context"""
        confidence = 0.5  # Base confidence
        
        # More context = higher confidence
        if len(context.keys()) > 5:
            confidence += 0.2
        
        # Recent improvisation experience
        if self.last_improvisation_time:
            time_since = (datetime.utcnow() - self.last_improvisation_time).total_seconds()
            if time_since < 300:  # 5 minutes
                confidence += 0.1
        
        return min(1.0, confidence)


class NPCGenerator:
    """Helper class for generating NPCs"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def generate_quick_npc(self, location: str, interaction_type: str,
                               plot_relevance: str, required_traits: List[str]) -> Dict[str, Any]:
        """Generate a quick NPC"""
        # Placeholder implementation
        return {
            "name": f"Quick NPC for {location}",
            "background": "commoner",
            "personality": ["friendly"],
            "secrets": [],
            "motivation": "live peacefully",
            "appearance": "ordinary person"
        }


class LocationGenerator:
    """Helper class for generating locations"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def generate_quick_location(self, location_type: str, atmosphere: str,
                                    purpose: str, connections_needed: List[str]) -> Dict[str, Any]:
        """Generate a quick location"""
        # Placeholder implementation
        return {
            "name": f"Improvised {location_type}",
            "type": location_type,
            "atmosphere": atmosphere,
            "notable_features": ["standard features for this type"],
            "connections": connections_needed
        }


class ConsequencePredictor:
    """Helper class for predicting consequences"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def predict_ruling_consequences(self, ruling_options: List[Dict[str, Any]],
                                        situation: Dict[str, Any]) -> Dict[str, Any]:
        """Predict consequences of different rulings"""
        # Placeholder implementation
        return {
            "short_term": ["Immediate player reaction"],
            "long_term": ["Precedent setting effects"],
            "narrative_impact": ["Story flow changes"]
        }


class ConnectionFinder:
    """Helper class for finding story connections"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
    
    async def find_plot_connections(self, element_data: Dict[str, Any],
                                  active_plotlines: List[str]) -> List[str]:
        """Find connections to active plotlines"""
        # Placeholder implementation
        return ["Potential connection to main quest"]
    
    async def find_story_connections(self, continuation_options: List[Dict[str, Any]],
                                   campaign_context: Dict[str, Any]) -> Dict[str, Any]:
        """Find connections to broader story"""
        # Placeholder implementation
        return {
            "plot_threads": ["Main quest", "Character arc"],
            "world_elements": ["Important locations", "Key NPCs"]
        }