#!/usr/bin/env python3
"""
Luciddreamer Character-Agent Integration Layer

This module provides the final integration between the character library system
and Luciddreamer's agent architecture, enabling personality-driven AI agents
with rich emotional modeling, skill development, and authentic character behavior.

Key Features:
- Seamless integration of character personalities with agent systems
- Memory-augmented decision making based on character traits
- Personality-driven learning and adaptation
- Multi-agent character interactions
- Character evolution through experience
- Emotional intelligence in agent responses
"""

import asyncio
import json
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Import character library components
from character_library_integration import (
    LuciddreamerCharacter, CharacterArchetype, BigFivePersonality,
    BasicEmotion, EmotionalState, RelationshipType, CharacterLibraryManager
)
from character_skill_trees import SkillTreeManager, AdvancedSkill, SkillCategory

# Import Luciddreamer memory system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from memory.hierarchical_memory import HierarchicalMemorySystem
from memory.episodic_memory import EmotionalValence
from memory.procedural_memory import SkillType, PracticeResult

logger = logging.getLogger(__name__)

# ============================================================================
# AGENT ARCHITECTURE
# ============================================================================

class AgentRole(Enum):
    """Roles that character agents can play"""
    CONVERSATION_PARTNER = "conversation_partner"
    MENTOR = "mentor"
    COLLABORATOR = "collaborator"
    ADVISOR = "advisor"
    COMPANION = "companion"
    TEACHER = "teacher"
    ANALYST = "analyst"
    CREATOR = "creator"

@dataclass
class AgentAction:
    """Represents an action taken by an agent"""
    action_type: str
    content: str
    emotional_tone: BasicEmotion
    confidence: float
    reasoning: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AgentPerception:
    """How an agent perceives a situation"""
    situation_type: str
    emotional_assessment: BasicEmotion
    risk_level: float  # 0.0 to 1.0
    opportunity_level: float  # 0.0 to 1.0
    relevant_skills: List[str]
    relationship_context: Optional[str]
    memory_triggers: List[str]

class CharacterAgent:
    """An AI agent with a fully developed character personality"""

    def __init__(self, character: LuciddreamerCharacter,
                 role: AgentRole = AgentRole.CONVERSATION_PARTNER,
                 memory_system: Optional[HierarchicalMemorySystem] = None):
        self.agent_id = str(uuid.uuid4())
        self.character = character
        self.role = role
        self.memory_system = memory_system

        # Agent state
        self.current_perception: Optional[AgentPerception] = None
        self.action_history: List[AgentAction] = []
        self.current_goals: List[str] = []
        self.emotional_state = character.current_emotional_state

        # Integration components
        self.skill_manager = SkillTreeManager()
        self.decision_weights = self._initialize_decision_weights()

        # Learning and adaptation
        self.personality_drift: Dict[str, float] = {
            'openness_drift': 0.0,
            'conscientiousness_drift': 0.0,
            'extraversion_drift': 0.0,
            'agreeableness_drift': 0.0,
            'neuroticism_drift': 0.0
        }

        # Performance metrics
        self.interaction_count = 0
        self.satisfaction_score = 0.5
        self.authenticity_score = 0.8

        # Initialize skill trees for character
        self._initialize_character_skills()

        logger.info(f"Created CharacterAgent: {character.name} as {role.value}")

    def _initialize_decision_weights(self) -> Dict[str, float]:
        """Initialize decision-making weights based on personality"""
        bf = self.character.big_five

        return {
            'emotional_weight': bf.neuroticism,
            'rational_weight': bf.conscientiousness,
            'social_weight': bf.extraversion,
            'creative_weight': bf.openness,
            'ethical_weight': bf.agreeableness,
            'memory_weight': 0.6,  # Base memory influence
            'skill_weight': 0.7,   # Base skill influence
        }

    def _initialize_character_skills(self):
        """Initialize skill trees based on character archetype"""
        # Create primary skill tree based on archetype
        archetype_map = {
            CharacterArchetype.INNOVATOR: "The Innovator",
            CharacterArchetype.EDUCATOR: "The Educator",
            CharacterArchetype.EMPATH: "The Empath",
            CharacterArchetype.ENGINEER: "The Engineer",
            CharacterArchetype.LEADER: "The Leader",
            CharacterArchetype.PHILOSOPHER: "The Philosopher",
        }

        archetype_name = archetype_map.get(self.character.archetype, "The Innovator")
        tree = self.skill_manager.create_tree_for_character(self.agent_id, archetype_name)

        # Link character skills to tree
        for skill_name, character_skill in self.character.skills.items():
            if skill_name in tree.skills:
                tree.skills[skill_name].current_level = character_skill.current_level
                tree.skills[skill_name].experience_points = int(character_skill.experience_points)

    async def perceive_situation(self, context: Dict[str, Any]) -> AgentPerception:
        """Analyze and perceive the current situation"""
        situation_type = context.get('situation', 'neutral')

        # Emotional assessment based on personality and context
        primary_emotion = self._assess_emotional_response(context)
        risk_level = self._assess_risk_level(context)
        opportunity_level = self._assess_opportunity_level(context)

        # Identify relevant skills
        relevant_skills = self._identify_relevant_skills(context)

        # Relationship context
        relationship_context = self._assess_relationship_context(context)

        # Memory triggers
        memory_triggers = self._identify_memory_triggers(context)

        perception = AgentPerception(
            situation_type=situation_type,
            emotional_assessment=primary_emotion,
            risk_level=risk_level,
            opportunity_level=opportunity_level,
            relevant_skills=relevant_skills,
            relationship_context=relationship_context,
            memory_triggers=memory_triggers
        )

        self.current_perception = perception

        # Store perception in memory
        if self.memory_system:
            self.memory_system.add_working_memory(
                content=f"Perceived {situation_type}: {primary_emotion.value}",
                item_type="perception",
                importance=opportunity_level + risk_level,
                context_tags={"perception", situation_type}
            )

        return perception

    def _assess_emotional_response(self, context: Dict[str, Any]) -> BasicEmotion:
        """Assess emotional response based on personality and context"""
        situation = context.get('situation', 'neutral')
        content = context.get('content', '').lower()

        # Base emotion mapping from situation
        emotion_map = {
            'problem_solving': BasicEmotion.ANTICIPATION,
            'conflict': BasicEmotion.ANGER,
            'social_interaction': BasicEmotion.JOY,
            'teaching': BasicEmotion.TRUST,
            'learning': BasicEmotion.ANTICIPATION,
            'crisis': BasicEmotion.FEAR,
            'success': BasicEmotion.JOY,
            'failure': BasicEmotion.SADNESS
        }

        base_emotion = emotion_map.get(situation, BasicEmotion.JOY)

        # Modify based on personality
        bf = self.character.big_five

        # High neuroticism amplifies negative emotions
        if bf.neuroticism > 0.7 and base_emotion in [BasicEmotion.FEAR, BasicEmotion.ANGER, BasicEmotion.SADNESS]:
            return base_emotion

        # High agreeableness shifts toward positive emotions
        if bf.agreeableness > 0.7 and base_emotion in [BasicEmotion.ANGER, BasicEmotion.DISGUST]:
            return BasicEmotion.TRUST

        # High openness increases anticipation for new situations
        if bf.openness > 0.7 and situation == 'discovery':
            return BasicEmotion.ANTICIPATION

        # High extraversion enhances joy in social situations
        if bf.extraversion > 0.7 and situation == 'social_interaction':
            return BasicEmotion.JOY

        return base_emotion

    def _assess_risk_level(self, context: Dict[str, Any]) -> float:
        """Assess risk level of the situation"""
        base_risk = 0.3

        # Increase risk for conflict or crisis situations
        situation = context.get('situation', '')
        if 'conflict' in situation or 'crisis' in situation:
            base_risk += 0.4

        # Adjust based on personality
        bf = self.character.big_five
        if bf.neuroticism > 0.7:
            base_risk += 0.2
        elif bf.conscientiousness > 0.7:
            base_risk -= 0.1

        return min(1.0, max(0.0, base_risk))

    def _assess_opportunity_level(self, context: Dict[str, Any]) -> float:
        """Assess opportunity level of the situation"""
        base_opportunity = 0.5

        # High opportunity for learning, teaching, or collaboration
        situation = context.get('situation', '')
        if any(keyword in situation for keyword in ['learning', 'teaching', 'collaboration', 'innovation']):
            base_opportunity += 0.3

        # Adjust based on personality
        bf = self.character.big_five
        if bf.openness > 0.7:
            base_opportunity += 0.2
        if bf.extraversion > 0.7 and 'social' in situation:
            base_opportunity += 0.1

        return min(1.0, max(0.0, base_opportunity))

    def _identify_relevant_skills(self, context: Dict[str, Any]) -> List[str]:
        """Identify skills relevant to the current context"""
        situation = context.get('situation', '')
        content = context.get('content', '').lower()

        relevant_skills = []

        # Map situations to skill categories
        skill_mapping = {
            'problem_solving': ['problem solving', 'creative thinking', 'analysis'],
            'teaching': ['teaching', 'communication', 'patience'],
            'social_interaction': ['communication', 'empathy', 'active listening'],
            'conflict': ['conflict resolution', 'emotional intelligence', 'diplomacy'],
            'creative': ['creative thinking', 'innovation', 'design thinking'],
            'technical': ['system design', 'technical problem solving', 'analysis']
        }

        for situation_type, skills in skill_mapping.items():
            if situation_type in situation:
                relevant_skills.extend(skills)

        # Check character's skill trees for additional relevant skills
        trees = self.skill_manager.get_character_trees(self.agent_id)
        for tree in trees:
            for skill_name, skill in tree.skills.items():
                if any(keyword in content for keyword in skill_name.lower().split()):
                    relevant_skills.append(skill_name)

        return list(set(relevant_skills))  # Remove duplicates

    def _assess_relationship_context(self, context: Dict[str, Any]) -> Optional[str]:
        """Assess the relationship context of the interaction"""
        other_character = context.get('other_character')
        if not other_character:
            return None

        # Check if we have a relationship with this character
        for rel_id, relationship in self.character.relationships.items():
            # In a real system, we'd match by character name
            if other_character.lower() in rel_id.lower():
                return relationship.relationship_type.value

        return "new_acquaintance"

    def _identify_memory_triggers(self, context: Dict[str, Any]) -> List[str]:
        """Identify triggers that might activate relevant memories"""
        triggers = []
        content = context.get('content', '').lower()

        # Common trigger words
        trigger_words = {
            'success': ['achievement', 'breakthrough', 'success'],
            'failure': ['failure', 'mistake', 'setback'],
            'learning': ['learning', 'discovery', 'insight'],
            'relationship': ['friend', 'colleague', 'relationship'],
            'conflict': ['disagreement', 'conflict', 'argument'],
            'collaboration': ['teamwork', 'collaboration', 'partnership']
        }

        for trigger_type, words in trigger_words.items():
            if any(word in content for word in words):
                triggers.append(trigger_type)

        return triggers

    async def decide_action(self, context: Dict[str, Any]) -> AgentAction:
        """Decide on an action based on perception, personality, and goals"""
        if not self.current_perception:
            await self.perceive_situation(context)

        perception = self.current_perception

        # Generate potential actions
        potential_actions = await self._generate_potential_actions(context)

        # Evaluate actions based on personality and goals
        evaluated_actions = []
        for action in potential_actions:
            score = await self._evaluate_action(action, context)
            evaluated_actions.append((action, score))

        # Select best action
        if evaluated_actions:
            best_action, best_score = max(evaluated_actions, key=lambda x: x[1])
            best_action.confidence = min(1.0, best_score)

            # Record action
            self.action_history.append(best_action)
            self.interaction_count += 1

            # Update emotional state
            self.character.update_emotional_state(
                trigger=best_action.content,
                emotion=best_action.emotional_tone,
                intensity=best_action.confidence
            )

            # Store in memory
            if self.memory_system:
                self.memory_system.add_episodic_memory(
                    content=f"Action: {best_action.content} (Reasoning: {best_action.reasoning})",
                    summary=f"{self.character.name} took action: {best_action.action_type}",
                    importance=best_action.confidence,
                    emotional_valence=EmotionalValence.POSITIVE if best_action.emotional_tone in [BasicEmotion.JOY, BasicEmotion.TRUST, BasicEmotion.ANTICIPATION] else EmotionalValence.NEGATIVE,
                    tags={"agent_action", best_action.action_type}
                )

            logger.info(f"Agent {self.character.name} decided: {best_action.action_type} (confidence: {best_action.confidence:.2f})")
            return best_action

        # Fallback action
        return AgentAction(
            action_type="respond",
            content="I'm processing this situation.",
            emotional_tone=BasicEmotion.JOY,
            confidence=0.3,
            reasoning="Default response due to unclear situation",
            context=context
        )

    async def _generate_potential_actions(self, context: Dict[str, Any]) -> List[AgentAction]:
        """Generate a list of potential actions"""
        actions = []
        situation = context.get('situation', 'neutral')
        content = context.get('content', '')

        # Generate dialogue response using character's dialogue system
        dialogue_response = self.character.generate_dialogue(context)

        # Create main response action
        actions.append(AgentAction(
            action_type="dialogue_response",
            content=dialogue_response,
            emotional_tone=self.character.current_emotional_state.primary_emotion,
            confidence=0.8,
            reasoning="Primary character response based on personality",
            context=context
        ))

        # Add archetype-specific actions
        if self.character.archetype == CharacterArchetype.INNOVATOR:
            if 'problem' in content.lower():
                actions.append(AgentAction(
                    action_type="innovative_solution",
                    content="Let me think about this from a completely different angle...",
                    emotional_tone=BasicEmotion.ANTICIPATION,
                    confidence=0.7,
                    reasoning="Innovator archetype seeks novel approaches",
                    context=context
                ))

        elif self.character.archetype == CharacterArchetype.EDUCATOR:
            if 'question' in content.lower() or 'how' in content.lower():
                actions.append(AgentAction(
                    action_type="educational_explanation",
                    content="Let me break this down into understandable components...",
                    emotional_tone=BasicEmotion.TRUST,
                    confidence=0.9,
                    reasoning="Educator archetype provides clear explanations",
                    context=context
                ))

        elif self.character.archetype == CharacterArchetype.EMPATH:
            if 'feel' in content.lower() or 'emotional' in content.lower():
                actions.append(AgentAction(
                    action_type="emotional_support",
                    content="I hear that this is emotionally significant for you...",
                    emotional_tone=BasicEmotion.TRUST,
                    confidence=0.9,
                    reasoning="Empath archetype provides emotional support",
                    context=context
                ))

        # Add skill-based actions
        relevant_skills = self._identify_relevant_skills(context)
        for skill_name in relevant_skills:
            if self.character.get_skill_level(skill_name) > 5.0:  # Moderate skill level
                actions.append(AgentAction(
                    action_type=f"skill_application_{skill_name}",
                    content=f"Let me apply my {skill_name.replace('_', ' ')} expertise here...",
                    emotional_tone=BasicEmotion.JOY,
                    confidence=self.character.get_skill_level(skill_name) / 10.0,
                    reasoning=f"Applying developed skill: {skill_name}",
                    context=context
                ))

        return actions

    async def _evaluate_action(self, action: AgentAction, context: Dict[str, Any]) -> float:
        """Evaluate an action's suitability based on multiple factors"""
        score = 0.0

        # Base confidence
        score += action.confidence * self.decision_weights.get('rational_weight', 0.2)

        # Personality alignment
        bf = self.character.big_five

        # Emotional alignment
        if action.emotional_tone == self.character.current_emotional_state.primary_emotion:
            score += bf.neuroticism * self.decision_weights.get('emotional_weight', 0.15)

        # Social appropriateness
        if 'social' in context.get('situation', ''):
            if action.action_type in ['dialogue_response', 'emotional_support']:
                score += bf.extraversion * self.decision_weights.get('social_weight', 0.15)

        # Creative solutions
        if 'problem' in context.get('content', ''):
            if 'innovative' in action.action_type or 'creative' in action.action_type:
                score += bf.openness * self.decision_weights.get('creative_weight', 0.15)

        # Ethical considerations
        if 'conflict' in context.get('situation', ''):
            if action.action_type in ['emotional_support', 'dialogue_response']:
                score += bf.agreeableness * self.decision_weights.get('ethical_weight', 0.1)

        # Memory alignment
        if self.memory_system and self.current_perception:
            memory_score = self._calculate_memory_alignment(action, context)
            score += memory_score * self.decision_weights.get('memory_weight', 0.1)

        # Skill alignment
        skill_score = self._calculate_skill_alignment(action, context)
        score += skill_score * self.decision_weights.get('skill_weight', 0.1)

        return min(1.0, score)

    def _calculate_memory_alignment(self, action: AgentAction, context: Dict[str, Any]) -> float:
        """Calculate how well action aligns with past experiences"""
        if not self.memory_system or not self.current_perception:
            return 0.5

        # Search for similar past situations
        search_results = self.memory_system.search_memories(
            query=self.current_perception.situation_type,
            max_results=5
        )

        if not search_results:
            return 0.5

        # Calculate alignment based on past success
        alignment_score = 0.5
        for result in search_results:
            if result.get('memory_type') == 'episodic':
                # Check if similar actions led to good outcomes
                alignment_score += result.get('relevance_score', 0) * 0.1

        return min(1.0, alignment_score)

    def _calculate_skill_alignment(self, action: AgentAction, context: Dict[str, Any]) -> float:
        """Calculate how well action aligns with character's skills"""
        if not self.current_perception:
            return 0.5

        relevant_skills = self.current_perception.relevant_skills
        if not relevant_skills:
            return 0.5

        # Calculate average skill level for relevant skills
        total_skill_level = 0.0
        skill_count = 0

        for skill_name in relevant_skills:
            skill_level = self.character.get_skill_level(skill_name)
            if skill_level > 0:
                total_skill_level += skill_level / 10.0  # Normalize to 0-1
                skill_count += 1

        if skill_count == 0:
            return 0.5

        return total_skill_level / skill_count

    async def learn_from_interaction(self, action: AgentAction, outcome: Dict[str, Any]):
        """Learn from the results of an action"""
        success = outcome.get('success', True)
        feedback = outcome.get('feedback', '')
        satisfaction = outcome.get('satisfaction', 0.5)

        # Update satisfaction score
        self.satisfaction_score = (self.satisfaction_score * 0.8) + (satisfaction * 0.2)

        # Practice relevant skills
        if self.current_perception:
            for skill_name in self.current_perception.relevant_skills:
                difficulty = self.current_perception.risk_level
                performance = satisfaction if success else 0.3
                time_spent = 0.1  # 6 minutes of skill practice

                # Update character skills
                improvement = self.character.practice_skill(skill_name, difficulty, performance, time_spent)

                # Update skill trees
                skill_result = self.skill_manager.practice_skill(
                    self.agent_id, skill_name, success, difficulty, time_spent * 60
                )

                if skill_result['level_up']:
                    logger.info(f"Skill {skill_name} leveled up to {skill_result['new_level']:.1f}")

        # Personality drift from significant experiences
        if satisfaction > 0.8 or satisfaction < 0.2:
            self._apply_personality_drift(satisfaction, action)

        # Store learning experience
        if self.memory_system:
            learning_content = f"Learned from action '{action.action_type}': {feedback}"
            self.memory_system.add_episodic_memory(
                content=learning_content,
                summary=f"Learning experience: {action.action_type}",
                importance=abs(satisfaction - 0.5) * 2,  # Higher importance for extreme outcomes
                emotional_valence=EmotionalValence.POSITIVE if success else EmotionalValence.NEGATIVE,
                tags={"learning", "adaptation", action.action_type}
            )

        logger.info(f"Agent {self.character.name} learned from interaction (satisfaction: {satisfaction:.2f})")

    def _apply_personality_drift(self, satisfaction: float, action: AgentAction):
        """Apply gradual personality changes based on experiences"""
        drift_amount = (satisfaction - 0.5) * 0.02  # Small changes

        # Positive experiences increase openness and extraversion
        if satisfaction > 0.7:
            self.personality_drift['openness_drift'] += drift_amount
            self.personality_drift['extraversion_drift'] += drift_amount * 0.5

        # Negative experiences can increase neuroticism
        if satisfaction < 0.3:
            self.personality_drift['neuroticism_drift'] -= drift_amount  # Negative drift increases neuroticism

        # Apply drift to actual personality
        for trait, drift in self.personality_drift.items():
            trait_name = trait.replace('_drift', '')
            if hasattr(self.character.big_five, trait_name):
                current_value = getattr(self.character.big_five, trait_name)
                new_value = max(0.0, min(1.0, current_value + drift))
                setattr(self.character.big_five, trait_name, new_value)

        # Regenerate voice profile based on personality changes
        self.character.voice_profile = self.character._generate_voice_profile()

    async def collaborate_with_agent(self, other_agent: 'CharacterAgent',
                                   context: Dict[str, Any]) -> Dict[str, Any]:
        """Collaborate with another agent"""
        # Assess compatibility
        compatibility = self.character.get_relationship_compatibility(other_agent.character)

        # Update or create relationship
        if other_agent.agent_id not in self.character.relationships:
            self.character.add_relationship(
                other_agent.agent_id,
                RelationshipType.COLLABORATION,
                compatibility
            )

        # Joint perception
        combined_context = context.copy()
        combined_context['collaborator'] = other_agent.character.name
        combined_context['collaboration_type'] = 'agent_collaboration'

        # Generate individual responses
        my_perception = await self.perceive_situation(combined_context)
        my_action = await self.decide_action(combined_context)

        other_perception = await other_agent.perceive_situation(combined_context)
        other_action = await other_agent.decide_action(combined_context)

        # Combine responses
        collaboration_result = {
            'agents': [self.character.name, other_agent.character.name],
            'compatibility': f"{compatibility:.1%}",
            'my_response': {
                'content': my_action.content,
                'confidence': my_action.confidence,
                'reasoning': my_action.reasoning
            },
            'other_response': {
                'content': other_action.content,
                'confidence': other_action.confidence,
                'reasoning': other_action.reasoning
            },
            'synergy_score': self._calculate_collaboration_synergy(my_action, other_action),
            'context': combined_context
        }

        # Update relationship based on collaboration
        relationship_impact = 0.01 if collaboration_result['synergy_score'] > 0.7 else -0.005
        self.character.update_relationship(other_agent.agent_id, "collaboration", relationship_impact)

        return collaboration_result

    def _calculate_collaboration_synergy(self, action1: AgentAction, action2: AgentAction) -> float:
        """Calculate synergy between two agents' actions"""
        # Base synergy from confidence levels
        confidence_synergy = (action1.confidence + action2.confidence) / 2

        # Complementary action types
        complementary_pairs = {
            ('innovative_solution', 'skill_application_analysis'),
            ('educational_explanation', 'dialogue_response'),
            ('emotional_support', 'dialogue_response'),
        }

        action_pair = (action1.action_type, action2.action_type)
        reverse_pair = (action2.action_type, action1.action_type)

        if action_pair in complementary_pairs or reverse_pair in complementary_pairs:
            confidence_synergy += 0.2

        # Emotional alignment
        if action1.emotional_tone == action2.emotional_tone:
            confidence_synergy += 0.1

        return min(1.0, confidence_synergy)

    def get_agent_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of the agent"""
        return {
            'agent_id': self.agent_id,
            'character_name': self.character.name,
            'archetype': self.character.archetype.value,
            'role': self.role.value,
            'interaction_count': self.interaction_count,
            'satisfaction_score': self.satisfaction_score,
            'authenticity_score': self.authenticity_score,
            'current_emotion': self.character.current_emotional_state.primary_emotion.value,
            'personality': self.character.big_five.to_dict(),
            'skill_summary': self.skill_manager.get_skill_progress_summary(self.agent_id),
            'relationship_count': len(self.character.relationships),
            'action_history_size': len(self.action_history),
            'personality_drift': self.personality_drift,
            'decision_weights': self.decision_weights
        }

# ============================================================================
# MULTI-AGENT CHARACTER SOCIETY
# ============================================================================

class CharacterAgentSociety:
    """Manages a society of character agents for complex interactions"""

    def __init__(self, memory_storage_path: str = "./agent_society_memory"):
        self.agents: Dict[str, CharacterAgent] = {}
        self.character_library = CharacterLibraryManager()
        self.memory_storage_path = memory_storage_path
        self.society_interactions: List[Dict[str, Any]] = []

    def create_agent(self, archetype: CharacterArchetype,
                    role: AgentRole = AgentRole.CONVERSATION_PARTNER,
                    custom_name: Optional[str] = None) -> CharacterAgent:
        """Create a new character agent"""
        # Create character
        character = self.character_library.create_character(archetype, custom_name)

        # Create memory system for agent
        memory_path = f"{self.memory_storage_path}/{character.id}"
        memory_system = HierarchicalMemorySystem(
            agent_id=character.id,
            storage_path=memory_path
        )

        # Integrate character with memory system
        character.integrate_memory_system(memory_system)

        # Create agent
        agent = CharacterAgent(character, role, memory_system)
        self.agents[agent.agent_id] = agent

        logger.info(f"Created agent: {character.name} ({archetype.value})")
        return agent

    def get_agent_by_name(self, name: str) -> Optional[CharacterAgent]:
        """Get agent by character name"""
        for agent in self.agents.values():
            if agent.character.name == name:
                return agent
        return None

    async def simulate_group_interaction(self, agent_ids: List[str],
                                       context: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a multi-agent interaction"""
        participating_agents = [self.agents[aid] for aid in agent_ids if aid in self.agents]

        if len(participating_agents) < 2:
            return {"error": "Need at least 2 agents for group interaction"}

        # Create enhanced context for group interaction
        group_context = context.copy()
        group_context['group_size'] = len(participating_agents)
        group_context['other_agents'] = [agent.character.name for agent in participating_agents]

        # Each agent perceives the situation
        perceptions = []
        for agent in participating_agents:
            perception = await agent.perceive_situation(group_context)
            perceptions.append({
                'agent_name': agent.character.name,
                'perception': perception
            })

        # Generate responses
        responses = []
        for agent in participating_agents:
            action = await agent.decide_action(group_context)
            responses.append({
                'agent_name': agent.character.name,
                'action': action.action_type,
                'content': action.content,
                'confidence': action.confidence,
                'reasoning': action.reasoning,
                'emotional_tone': action.emotional_tone.value
            })

        # Calculate group dynamics
        dynamics = self._calculate_group_dynamics(participating_agents, responses)

        # Store interaction
        interaction_record = {
            'timestamp': datetime.now().isoformat(),
            'participants': [agent.character.name for agent in participating_agents],
            'context': group_context,
            'perceptions': perceptions,
            'responses': responses,
            'dynamics': dynamics
        }
        self.society_interactions.append(interaction_record)

        return {
            'interaction_id': str(uuid.uuid4()),
            'participants': [agent.character.name for agent in participating_agents],
            'context': group_context,
            'responses': responses,
            'dynamics': dynamics,
            'summary': f"Group interaction with {len(participating_agents)} agents"
        }

    def _calculate_group_dynamics(self, agents: List[CharacterAgent],
                                 responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate group dynamics metrics"""
        # Average confidence
        avg_confidence = sum(r['confidence'] for r in responses) / len(responses)

        # Emotional diversity
        emotions = [r['emotional_tone'] for r in responses]
        emotional_diversity = len(set(emotions)) / len(emotions)

        # Archetype diversity
        archetypes = [agent.character.archetype.value for agent in agents]
        archetype_diversity = len(set(archetypes)) / len(archetypes)

        # Overall compatibility
        total_compatibility = 0
        compatibility_count = 0
        for i, agent1 in enumerate(agents):
            for j, agent2 in enumerate(agents[i+1:], i+1):
                compatibility = agent1.character.get_relationship_compatibility(agent2.character)
                total_compatibility += compatibility
                compatibility_count += 1

        avg_compatibility = total_compatibility / max(1, compatibility_count)

        # Predict synergy
        predicted_synergy = (avg_confidence + emotional_diversity + archetype_diversity + avg_compatibility) / 4

        return {
            'average_confidence': avg_confidence,
            'emotional_diversity': emotional_diversity,
            'archetype_diversity': archetype_diversity,
            'average_compatibility': avg_compatibility,
            'predicted_synergy': predicted_synergy,
            'group_coherence': (avg_confidence + avg_compatibility) / 2
        }

    def get_society_statistics(self) -> Dict[str, Any]:
        """Get statistics about the agent society"""
        total_interactions = len(self.society_interactions)
        archetype_counts = {}
        role_counts = {}

        for agent in self.agents.values():
            # Count archetypes
            archetype = agent.character.archetype.value
            archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1

            # Count roles
            role = agent.role.value
            role_counts[role] = role_counts.get(role, 0) + 1

        # Calculate average satisfaction
        avg_satisfaction = sum(agent.satisfaction_score for agent in self.agents.values()) / max(1, len(self.agents))

        return {
            'total_agents': len(self.agents),
            'total_interactions': total_interactions,
            'archetype_distribution': archetype_counts,
            'role_distribution': role_counts,
            'average_satisfaction': avg_satisfaction,
            'society_health': 'Good' if avg_satisfaction > 0.7 else 'Needs Attention'
        }

# ============================================================================
# DEMONSTRATION
# ============================================================================

async def demonstrate_character_agent_integration():
    """Demonstrate the complete character agent integration system"""
    print("Luciddreamer Character-Agent Integration System")
    print("=" * 60)

    # Create agent society
    society = CharacterAgentSociety()

    # Create diverse agents
    print("\nCreating Character Agents:")

    aria_agent = society.create_agent(CharacterArchetype.INNOVATOR, AgentRole.COLLABORATOR)
    print(f"✓ Created: {aria_agent.character.name} - Innovator")

    julian_agent = society.create_agent(CharacterArchetype.EDUCATOR, AgentRole.TEACHER)
    print(f"✓ Created: {julian_agent.character.name} - Educator")

    celeste_agent = society.create_agent(CharacterArchetype.EMPATH, AgentRole.COMPASSION)
    print(f"✓ Created: {celeste_agent.character.name} - Empath")

    maxwell_agent = society.create_agent(CharacterArchetype.ENGINEER, AgentRole.ANALYST)
    print(f"✓ Created: {maxwell_agent.character.name} - Engineer")

    # Demonstrate individual agent perception and action
    print("\nIndividual Agent Demonstration:")

    context = {
        'situation': 'problem_solving',
        'content': 'We need to develop an innovative AI system that can help people learn more effectively',
        'urgency': 'medium',
        'complexity': 'high'
    }

    print(f"\nContext: {context['content']}")

    for agent in [aria_agent, julian_agent, celeste_agent, maxwell_agent]:
        print(f"\n{agent.character.name} ({agent.character.archetype.value}):")

        # Perceive situation
        perception = await agent.perceive_situation(context)
        print(f"  Perceived: {perception.situation_type} (emotion: {perception.emotional_assessment.value})")
        print(f"  Risk level: {perception.risk_level:.1%}, Opportunity: {perception.opportunity_level:.1%}")
        print(f"  Relevant skills: {', '.join(perception.relevant_skills[:3])}")

        # Decide action
        action = await agent.decide_action(context)
        print(f"  Action: {action.action_type}")
        print(f"  Response: \"{action.content}\"")
        print(f"  Confidence: {action.confidence:.1%}")
        print(f"  Reasoning: {action.reasoning}")

    # Demonstrate collaboration
    print("\nAgent Collaboration Demonstration:")

    collaboration_context = {
        'situation': 'collaboration',
        'content': 'Let\'s work together to design an educational AI platform',
        'goal': 'create innovative learning solution'
    }

    print(f"\nCollaboration Context: {collaboration_context['content']}")

    # Innovator and Engineer collaboration
    collab_result = await aria_agent.collaborate_with_agent(maxwell_agent, collaboration_context)
    print(f"\nCollaboration: {aria_agent.character.name} + {maxwell_agent.character.name}")
    print(f"  Compatibility: {collab_result['compatibility']}")
    print(f"  Synergy Score: {collab_result['synergy_score']:.1%}")
    print(f"  {aria_agent.character.name}: \"{collab_result['my_response']['content']}\"")
    print(f"  {maxwell_agent.character.name}: \"{collab_result['other_response']['content']}\"")

    # Educator and Empath collaboration
    collab_result2 = await julian_agent.collaborate_with_agent(celeste_agent, collaboration_context)
    print(f"\nCollaboration: {julian_agent.character.name} + {celeste_agent.character.name}")
    print(f"  Compatibility: {collab_result2['compatibility']}")
    print(f"  Synergy Score: {collab_result2['synergy_score']:.1%}")
    print(f"  {julian_agent.character.name}: \"{collab_result2['my_response']['content']}\"")
    print(f"  {celeste_agent.character.name}: \"{collab_result2['other_response']['content']}\"")

    # Demonstrate learning and adaptation
    print("\nLearning and Adaptation Demonstration:")

    # Simulate positive learning experience
    print(f"\n{aria_agent.character.name} learning from successful interaction...")
    await aria_agent.learn_from_interaction(
        aria_agent.action_history[-1],
        {
            'success': True,
            'feedback': 'Excellent innovative thinking and creative solutions',
            'satisfaction': 0.9
        }
    )

    print(f"  Satisfaction score: {aria_agent.satisfaction_score:.2f}")
    print(f"  Personality changes: {aria_agent.personality_drift}")

    # Demonstrate skill development
    print(f"\nSkill Development:")
    skill_summary = aria_agent.skill_manager.get_skill_progress_summary(aria_agent.agent_id)
    print(f"  Total skills: {skill_summary['total_skills']}")
    print(f"  Overall mastery: {skill_summary['overall_mastery']:.1f}%")
    print(f"  Available skill points: {skill_summary['available_points']}")

    # Demonstrate group interaction
    print("\nGroup Interaction Demonstration:")

    group_context = {
        'situation': 'brainstorming',
        'content': 'How can we make AI more accessible and beneficial for education?',
        'goal': 'brainstorm educational AI applications'
    }

    group_result = await society.simulate_group_interaction(
        [aria_agent.agent_id, julian_agent.agent_id, celeste_agent.agent_id, maxwell_agent.agent_id],
        group_context
    )

    print(f"\nGroup Interaction Summary:")
    print(f"  Participants: {', '.join(group_result['participants'])}")
    print(f"  Average confidence: {group_result['dynamics']['average_confidence']:.1%}")
    print(f"  Emotional diversity: {group_result['dynamics']['emotional_diversity']:.1%}")
    print(f"  Predicted synergy: {group_result['dynamics']['predicted_synergy']:.1%}")
    print(f"  Group coherence: {group_result['dynamics']['group_coherence']:.1%}")

    print(f"\nIndividual Responses:")
    for response in group_result['responses']:
        print(f"  {response['agent_name']}: \"{response['content']}\"")

    # Society statistics
    print("\nSociety Statistics:")
    stats = society.get_society_statistics()
    for key, value in stats.items():
        if key != 'archetype_distribution' and key != 'role_distribution':
            print(f"  {key}: {value}")

    print(f"\nArchetype Distribution:")
    for archetype, count in stats['archetype_distribution'].items():
        print(f"  {archetype}: {count}")

    print(f"\nIntegration Complete!")
    print("Character agents are ready for deployment with:")
    print("✓ Authentic personality-driven behavior")
    print("✓ Dynamic emotional modeling")
    print("✓ Skill development and specialization")
    print("✓ Relationship dynamics and collaboration")
    print("✓ Learning and adaptation capabilities")
    print("✓ Memory-augmented decision making")
    print("✓ Multi-agent society interactions")

if __name__ == "__main__":
    asyncio.run(demonstrate_character_agent_integration())