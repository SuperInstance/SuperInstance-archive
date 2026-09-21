"""
Narrative Flow Manager for maintaining story coherence and flow
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..models.base import (
    Campaign, PlotThread, NarrativeEvent, SessionState, 
    DecisionContext, LoreEntry, StorylineStatus
)
from ..config import NARRATIVE_CONFIG
from ..utils.ai_client import AIClient
from ..utils.coherence_analyzer import CoherenceAnalyzer


logger = logging.getLogger(__name__)


class NarrativeFlowManager:
    """Manages narrative flow and maintains story coherence"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        self.coherence_analyzer = CoherenceAnalyzer()
        
        # Story state tracking
        self.active_plotlines: Dict[str, PlotThread] = {}
        self.narrative_memory: List[NarrativeEvent] = []
        self.story_beats: Dict[str, float] = {}
        self.coherence_score: float = 1.0
        
        # Flow control
        self.action_counter: int = 0
        self.last_coherence_check: datetime = datetime.utcnow()
        self.transition_triggers: List[str] = []
        
    async def initialize_narrative(self, campaign: Campaign, session_state: SessionState) -> None:
        """Initialize narrative tracking for a session"""
        try:
            # Load active plotlines
            for plotline_id in campaign.active_plotlines:
                plotline = await self._load_plotline(plotline_id)
                if plotline:
                    self.active_plotlines[plotline_id] = plotline
            
            # Initialize story beats
            self._initialize_story_beats(session_state)
            
            # Load recent narrative memory
            await self._load_narrative_memory(campaign, session_state)
            
            logger.info(f"Narrative initialized: {len(self.active_plotlines)} plotlines, "
                       f"coherence score: {self.coherence_score}")
                       
        except Exception as e:
            logger.error(f"Error initializing narrative: {e}")
            raise
    
    async def process_player_action(self, action: Dict[str, Any], 
                                  session_state: SessionState) -> Dict[str, Any]:
        """Process a player action and maintain narrative flow"""
        try:
            self.action_counter += 1
            
            # Analyze action impact on story
            story_impact = await self._analyze_story_impact(action, session_state)
            
            # Update plotline progress
            await self._update_plotline_progress(action, story_impact)
            
            # Check for story beat transitions
            transitions = await self._check_story_transitions(action, session_state)
            
            # Maintain coherence
            if self.action_counter % NARRATIVE_CONFIG["coherence_check_frequency"] == 0:
                await self._check_coherence(session_state)
            
            # Generate narrative guidance
            guidance = await self._generate_narrative_guidance(
                action, story_impact, transitions, session_state
            )
            
            return {
                "story_impact": story_impact,
                "transitions_triggered": transitions,
                "narrative_guidance": guidance,
                "coherence_score": self.coherence_score,
                "active_plotlines": len(self.active_plotlines)
            }
            
        except Exception as e:
            logger.error(f"Error processing player action: {e}")
            return {"error": str(e)}
    
    async def suggest_story_continuation(self, session_state: SessionState) -> Dict[str, Any]:
        """Suggest ways to continue the story"""
        try:
            context = DecisionContext(
                situation_type="story_continuation",
                active_plotlines=list(self.active_plotlines.values()),
                recent_events=self.narrative_memory[-5:] if self.narrative_memory else []
            )
            
            # Analyze current story state
            story_analysis = await self._analyze_current_story_state(session_state)
            
            # Generate continuation options
            continuations = await self._generate_story_continuations(
                context, story_analysis, session_state
            )
            
            # Prioritize based on narrative flow
            prioritized_continuations = self._prioritize_continuations(
                continuations, story_analysis
            )
            
            return {
                "story_analysis": story_analysis,
                "continuation_options": prioritized_continuations,
                "recommended_option": prioritized_continuations[0] if prioritized_continuations else None,
                "narrative_flow_score": self._calculate_flow_score(session_state)
            }
            
        except Exception as e:
            logger.error(f"Error suggesting story continuation: {e}")
            return {"error": str(e)}
    
    async def handle_narrative_inconsistency(self, inconsistency: Dict[str, Any], 
                                           session_state: SessionState) -> Dict[str, Any]:
        """Handle detected narrative inconsistencies"""
        try:
            inconsistency_type = inconsistency.get("type", "unknown")
            severity = inconsistency.get("severity", 0.5)
            
            logger.warning(f"Narrative inconsistency detected: {inconsistency_type} "
                         f"(severity: {severity})")
            
            # Generate resolution strategies
            if inconsistency_type == "character_contradiction":
                resolution = await self._resolve_character_contradiction(
                    inconsistency, session_state
                )
            elif inconsistency_type == "timeline_conflict":
                resolution = await self._resolve_timeline_conflict(
                    inconsistency, session_state
                )
            elif inconsistency_type == "lore_violation":
                resolution = await self._resolve_lore_violation(
                    inconsistency, session_state
                )
            else:
                resolution = await self._resolve_generic_inconsistency(
                    inconsistency, session_state
                )
            
            # Update coherence score
            self.coherence_score = max(0.0, self.coherence_score - severity * 0.1)
            
            return {
                "inconsistency": inconsistency,
                "resolution_strategy": resolution,
                "coherence_impact": -severity * 0.1,
                "new_coherence_score": self.coherence_score
            }
            
        except Exception as e:
            logger.error(f"Error handling narrative inconsistency: {e}")
            return {"error": str(e)}
    
    async def get_story_health_report(self, session_state: SessionState) -> Dict[str, Any]:
        """Generate a report on the overall story health"""
        try:
            # Analyze plotline balance
            plotline_analysis = self._analyze_plotline_balance()
            
            # Check pacing
            pacing_analysis = self._analyze_story_pacing(session_state)
            
            # Assess coherence
            coherence_analysis = await self._assess_story_coherence(session_state)
            
            # Calculate overall health score
            health_score = self._calculate_story_health_score(
                plotline_analysis, pacing_analysis, coherence_analysis
            )
            
            # Generate recommendations
            recommendations = await self._generate_story_recommendations(
                plotline_analysis, pacing_analysis, coherence_analysis
            )
            
            return {
                "health_score": health_score,
                "plotline_balance": plotline_analysis,
                "pacing_analysis": pacing_analysis,
                "coherence_analysis": coherence_analysis,
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating story health report: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _load_plotline(self, plotline_id: str) -> Optional[PlotThread]:
        """Load a plotline from storage"""
        # Implementation would load from database
        # For now, return a placeholder
        return PlotThread(
            id=plotline_id,
            title=f"Plotline {plotline_id}",
            description="A story thread in the campaign"
        )
    
    def _initialize_story_beats(self, session_state: SessionState) -> None:
        """Initialize story beat tracking for the session"""
        for beat, config in NARRATIVE_CONFIG["story_beats"].items():
            self.story_beats[beat] = {
                "weight": config["weight"],
                "duration": config["duration"],
                "progress": 0.0,
                "active": beat == "introduction"
            }
    
    async def _load_narrative_memory(self, campaign: Campaign, 
                                   session_state: SessionState) -> None:
        """Load recent narrative events into memory"""
        memory_window = NARRATIVE_CONFIG["narrative_memory_window"]
        # Load last N sessions worth of events
        # Implementation would query database
        self.narrative_memory = []
    
    async def _analyze_story_impact(self, action: Dict[str, Any], 
                                  session_state: SessionState) -> Dict[str, Any]:
        """Analyze how an action impacts the story"""
        try:
            prompt = f"""
            Analyze the story impact of this player action:
            Action: {action.get('description', 'Unknown action')}
            Current scene: {session_state.current_scene}
            Active plotlines: {[p.title for p in self.active_plotlines.values()]}
            
            Assess:
            1. Which plotlines are affected (0-1 scale)
            2. Story momentum change (-1 to 1)
            3. New story possibilities created
            4. Potential complications introduced
            """
            
            response = await self.ai_client.generate_completion(prompt, max_tokens=300)
            
            # Parse AI response into structured impact analysis
            return {
                "plotline_effects": {},  # Would parse from AI response
                "momentum_change": 0.0,
                "new_possibilities": [],
                "complications": [],
                "impact_magnitude": 0.5
            }
            
        except Exception as e:
            logger.error(f"Error analyzing story impact: {e}")
            return {"impact_magnitude": 0.0}
    
    async def _update_plotline_progress(self, action: Dict[str, Any], 
                                      story_impact: Dict[str, Any]) -> None:
        """Update progress on affected plotlines"""
        for plotline_id, plotline in self.active_plotlines.items():
            if plotline_id in story_impact.get("plotline_effects", {}):
                effect = story_impact["plotline_effects"][plotline_id]
                
                # Update sessions active
                plotline.sessions_active += 1
                
                # Check for milestone completion
                if effect > 0.7:  # Significant progress
                    await self._check_plotline_milestones(plotline, action)
    
    async def _check_story_transitions(self, action: Dict[str, Any], 
                                     session_state: SessionState) -> List[str]:
        """Check if any story beat transitions should occur"""
        transitions = []
        
        # Check configured transition triggers
        for trigger in NARRATIVE_CONFIG["transition_triggers"]:
            if await self._evaluate_transition_trigger(trigger, action, session_state):
                transitions.append(trigger)
        
        # Check natural story beat progression
        current_beat = self._get_current_story_beat()
        if await self._should_advance_story_beat(current_beat, session_state):
            transitions.append(f"advance_to_next_beat")
        
        return transitions
    
    async def _check_coherence(self, session_state: SessionState) -> None:
        """Check and update story coherence score"""
        try:
            # Analyze recent narrative events for consistency
            consistency_score = await self.coherence_analyzer.analyze_consistency(
                self.narrative_memory[-10:] if self.narrative_memory else [],
                self.active_plotlines
            )
            
            # Update overall coherence score
            self.coherence_score = (self.coherence_score * 0.8 + consistency_score * 0.2)
            
            # Log coherence issues if score drops significantly
            if self.coherence_score < NARRATIVE_CONFIG["story_coherence_threshold"]:
                logger.warning(f"Story coherence below threshold: {self.coherence_score}")
                
        except Exception as e:
            logger.error(f"Error checking coherence: {e}")
    
    async def _generate_narrative_guidance(self, action: Dict[str, Any], 
                                         story_impact: Dict[str, Any],
                                         transitions: List[str],
                                         session_state: SessionState) -> Dict[str, Any]:
        """Generate guidance for the DM based on narrative analysis"""
        try:
            prompt = f"""
            Provide DM guidance based on this narrative analysis:
            
            Player action: {action.get('description', 'Unknown')}
            Story impact magnitude: {story_impact.get('impact_magnitude', 0)}
            Transitions triggered: {transitions}
            Current coherence score: {self.coherence_score}
            Active plotlines: {len(self.active_plotlines)}
            
            Provide:
            1. Immediate response suggestions
            2. Opportunities to advance plotlines
            3. Foreshadowing opportunities
            4. Potential complications to introduce
            5. Pacing recommendations
            """
            
            response = await self.ai_client.generate_completion(prompt, max_tokens=500)
            
            return {
                "immediate_suggestions": [],  # Would parse from AI response
                "plotline_advancement": [],
                "foreshadowing_opportunities": [],
                "potential_complications": [],
                "pacing_advice": "",
                "confidence": 0.8
            }
            
        except Exception as e:
            logger.error(f"Error generating narrative guidance: {e}")
            return {"error": str(e)}
    
    async def _analyze_current_story_state(self, session_state: SessionState) -> Dict[str, Any]:
        """Analyze the current state of the story"""
        return {
            "dominant_plotlines": self._identify_dominant_plotlines(),
            "story_momentum": self._calculate_story_momentum(),
            "tension_level": session_state.current_tension,
            "pacing_score": self._calculate_pacing_score(session_state),
            "player_agency_level": 0.7,  # Would calculate based on recent decisions
            "dramatic_potential": 0.6    # Would analyze based on active elements
        }
    
    async def _generate_story_continuations(self, context: DecisionContext,
                                          story_analysis: Dict[str, Any],
                                          session_state: SessionState) -> List[Dict[str, Any]]:
        """Generate possible story continuation options"""
        try:
            prompt = f"""
            Generate story continuation options for this situation:
            
            Context: {context.situation_type}
            Active plotlines: {[p.title for p in context.active_plotlines]}
            Story momentum: {story_analysis.get('story_momentum', 0)}
            Tension level: {session_state.current_tension.value}
            Scene: {session_state.current_scene}
            
            Generate 3-5 continuation options focusing on:
            1. Advancing main plotlines
            2. Character development moments
            3. Tension building/release
            4. Player agency opportunities
            5. Narrative coherence
            """
            
            response = await self.ai_client.generate_completion(prompt, max_tokens=600)
            
            # Would parse AI response into structured options
            return [
                {
                    "title": "Advance Main Quest",
                    "description": "Move forward with the primary storyline",
                    "plotlines_advanced": ["main_quest"],
                    "expected_duration": 30,
                    "tension_impact": 0.2,
                    "coherence_bonus": 0.1
                }
            ]
            
        except Exception as e:
            logger.error(f"Error generating story continuations: {e}")
            return []
    
    def _prioritize_continuations(self, continuations: List[Dict[str, Any]],
                                story_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize story continuation options"""
        def priority_score(continuation):
            score = 0.0
            
            # Favor coherence improvements
            score += continuation.get("coherence_bonus", 0) * 2.0
            
            # Consider current story momentum
            momentum = story_analysis.get("story_momentum", 0)
            if momentum > 0.7:
                score += continuation.get("tension_impact", 0) * 1.5
            elif momentum < 0.3:
                score += (1.0 - continuation.get("tension_impact", 0)) * 1.5
            
            # Favor plotline advancement if needed
            dominant_plotlines = story_analysis.get("dominant_plotlines", [])
            if len(dominant_plotlines) < 2:
                score += len(continuation.get("plotlines_advanced", [])) * 0.5
            
            return score
        
        return sorted(continuations, key=priority_score, reverse=True)
    
    def _calculate_flow_score(self, session_state: SessionState) -> float:
        """Calculate overall narrative flow score"""
        coherence_weight = 0.4
        pacing_weight = 0.3
        plotline_balance_weight = 0.3
        
        pacing_score = self._calculate_pacing_score(session_state)
        plotline_score = self._calculate_plotline_balance_score()
        
        return (
            self.coherence_score * coherence_weight +
            pacing_score * pacing_weight +
            plotline_score * plotline_balance_weight
        )
    
    def _identify_dominant_plotlines(self) -> List[str]:
        """Identify which plotlines are currently dominant"""
        return [
            plotline.id for plotline in self.active_plotlines.values()
            if plotline.priority >= 4 and plotline.sessions_active > 0
        ][:2]  # Top 2 most dominant
    
    def _calculate_story_momentum(self) -> float:
        """Calculate current story momentum"""
        recent_events = self.narrative_memory[-5:] if self.narrative_memory else []
        if not recent_events:
            return 0.5
        
        momentum = sum(event.impact_level for event in recent_events) / len(recent_events)
        return min(1.0, max(0.0, momentum))
    
    def _calculate_pacing_score(self, session_state: SessionState) -> float:
        """Calculate story pacing score"""
        # Would implement based on scene changes, tension curve, etc.
        return 0.7  # Placeholder
    
    def _calculate_plotline_balance_score(self) -> float:
        """Calculate how balanced the active plotlines are"""
        if not self.active_plotlines:
            return 0.0
        
        # Check if all plotlines are getting attention
        sessions_active = [p.sessions_active for p in self.active_plotlines.values()]
        if not sessions_active:
            return 0.5
        
        # Lower variance in sessions_active indicates better balance
        mean_sessions = sum(sessions_active) / len(sessions_active)
        variance = sum((s - mean_sessions) ** 2 for s in sessions_active) / len(sessions_active)
        
        # Convert variance to 0-1 score (lower variance = higher score)
        return max(0.0, 1.0 - variance / (mean_sessions + 1))
    
    def _get_current_story_beat(self) -> str:
        """Get the currently active story beat"""
        for beat, config in self.story_beats.items():
            if config.get("active", False):
                return beat
        return "introduction"
    
    async def _should_advance_story_beat(self, current_beat: str, 
                                       session_state: SessionState) -> bool:
        """Check if it's time to advance to the next story beat"""
        beat_config = self.story_beats.get(current_beat, {})
        
        # Check if current beat has been active long enough
        duration = beat_config.get("duration", 30)  # minutes
        if session_state.time_elapsed >= duration:
            return True
        
        # Check if beat objectives have been met
        progress = beat_config.get("progress", 0.0)
        if progress >= 0.8:
            return True
        
        return False
    
    async def _evaluate_transition_trigger(self, trigger: str, action: Dict[str, Any], 
                                         session_state: SessionState) -> bool:
        """Evaluate if a transition trigger condition is met"""
        if trigger == "major_goal_achieved":
            return action.get("achieves_major_goal", False)
        elif trigger == "critical_failure":
            return action.get("is_critical_failure", False)
        elif trigger == "revelation_discovered":
            return action.get("reveals_information", False)
        # ... other trigger evaluations
        
        return False
    
    async def _check_plotline_milestones(self, plotline: PlotThread, 
                                       action: Dict[str, Any]) -> None:
        """Check if any plotline milestones have been completed"""
        # Implementation would check against plotline milestones
        # and update completion status
        pass
    
    # Inconsistency resolution methods
    
    async def _resolve_character_contradiction(self, inconsistency: Dict[str, Any], 
                                             session_state: SessionState) -> Dict[str, Any]:
        """Resolve a character behavior contradiction"""
        return {
            "strategy": "character_development",
            "explanation": "Character has grown/changed due to recent events",
            "implementation": "Address in next character interaction"
        }
    
    async def _resolve_timeline_conflict(self, inconsistency: Dict[str, Any], 
                                       session_state: SessionState) -> Dict[str, Any]:
        """Resolve a timeline inconsistency"""
        return {
            "strategy": "clarification",
            "explanation": "Clarify the actual sequence of events",
            "implementation": "Provide corrected timeline to players"
        }
    
    async def _resolve_lore_violation(self, inconsistency: Dict[str, Any], 
                                    session_state: SessionState) -> Dict[str, Any]:
        """Resolve a lore consistency violation"""
        return {
            "strategy": "retcon_or_evolve",
            "explanation": "Either retcon the inconsistency or evolve the world",
            "implementation": "Discuss with players or make narrative adjustment"
        }
    
    async def _resolve_generic_inconsistency(self, inconsistency: Dict[str, Any], 
                                           session_state: SessionState) -> Dict[str, Any]:
        """Resolve any other type of inconsistency"""
        return {
            "strategy": "narrative_smoothing",
            "explanation": "Smooth over with additional context",
            "implementation": "Provide bridging narrative"
        }
    
    def _analyze_plotline_balance(self) -> Dict[str, Any]:
        """Analyze balance between active plotlines"""
        if not self.active_plotlines:
            return {"balance_score": 0.0, "issues": ["No active plotlines"]}
        
        # Calculate attention distribution
        total_sessions = sum(p.sessions_active for p in self.active_plotlines.values())
        if total_sessions == 0:
            return {"balance_score": 0.5, "issues": ["No plotline progress"]}
        
        attention_distribution = {
            p.id: p.sessions_active / total_sessions
            for p in self.active_plotlines.values()
        }
        
        # Identify imbalances
        issues = []
        for plotline in self.active_plotlines.values():
            attention = attention_distribution[plotline.id]
            expected_attention = plotline.priority / sum(p.priority for p in self.active_plotlines.values())
            
            if attention < expected_attention * 0.7:
                issues.append(f"Plotline '{plotline.title}' needs more attention")
            elif attention > expected_attention * 1.3:
                issues.append(f"Plotline '{plotline.title}' may be dominating")
        
        balance_score = 1.0 - len(issues) / (len(self.active_plotlines) + 1)
        
        return {
            "balance_score": balance_score,
            "attention_distribution": attention_distribution,
            "issues": issues,
            "recommendations": self._generate_balance_recommendations(issues)
        }
    
    def _analyze_story_pacing(self, session_state: SessionState) -> Dict[str, Any]:
        """Analyze story pacing"""
        return {
            "pacing_score": self._calculate_pacing_score(session_state),
            "current_beat": self._get_current_story_beat(),
            "time_in_beat": session_state.time_elapsed,
            "recommended_transitions": []
        }
    
    async def _assess_story_coherence(self, session_state: SessionState) -> Dict[str, Any]:
        """Assess overall story coherence"""
        return {
            "coherence_score": self.coherence_score,
            "consistency_issues": [],
            "narrative_gaps": [],
            "continuity_strengths": []
        }
    
    def _calculate_story_health_score(self, plotline_analysis: Dict[str, Any],
                                    pacing_analysis: Dict[str, Any],
                                    coherence_analysis: Dict[str, Any]) -> float:
        """Calculate overall story health score"""
        plotline_score = plotline_analysis.get("balance_score", 0.5)
        pacing_score = pacing_analysis.get("pacing_score", 0.5)
        coherence_score = coherence_analysis.get("coherence_score", 0.5)
        
        return (plotline_score * 0.4 + pacing_score * 0.3 + coherence_score * 0.3)
    
    async def _generate_story_recommendations(self, plotline_analysis: Dict[str, Any],
                                            pacing_analysis: Dict[str, Any],
                                            coherence_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving story health"""
        recommendations = []
        
        # Plotline recommendations
        if plotline_analysis.get("balance_score", 1.0) < 0.7:
            recommendations.extend(plotline_analysis.get("recommendations", []))
        
        # Pacing recommendations
        if pacing_analysis.get("pacing_score", 1.0) < 0.6:
            recommendations.append("Consider varying scene pacing")
        
        # Coherence recommendations
        if coherence_analysis.get("coherence_score", 1.0) < 0.8:
            recommendations.append("Review recent narrative for consistency")
        
        return recommendations
    
    def _generate_balance_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations for plotline balance"""
        recommendations = []
        
        for issue in issues:
            if "needs more attention" in issue:
                recommendations.append("Schedule scenes focusing on neglected plotlines")
            elif "dominating" in issue:
                recommendations.append("Reduce focus on dominant plotlines")
        
        return recommendations