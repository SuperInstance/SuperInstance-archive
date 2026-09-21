import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import random
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CompanionPersonality(str, Enum):
    BRAVE = "brave"
    CAUTIOUS = "cautious"
    CURIOUS = "curious"
    LOYAL = "loyal"
    INDEPENDENT = "independent"
    WISE = "wise"
    IMPULSIVE = "impulsive"
    PROTECTIVE = "protective"
    ANALYTICAL = "analytical"
    CHARISMATIC = "charismatic"

class DecisionContext(str, Enum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    PUZZLE = "puzzle"
    MORAL_DILEMMA = "moral_dilemma"
    RESOURCE_MANAGEMENT = "resource_management"
    STEALTH = "stealth"
    INVESTIGATION = "investigation"

class CompanionAction(BaseModel):
    action_type: str
    target: Optional[str] = None
    description: str
    reasoning: str
    confidence: float
    risk_assessment: float
    expected_outcome: str
    alternatives: List[str] = []

@dataclass
class CompanionMemory:
    memory_id: str
    event_type: str
    participants: List[str]
    location: str
    outcome: str
    emotional_impact: float
    lessons_learned: List[str]
    timestamp: datetime
    importance: float

@dataclass
class RelationshipBond:
    target_character: str
    relationship_type: str  # 'friendship', 'rivalry', 'romance', 'mentor', 'distrust'
    bond_strength: float  # 0.0 to 1.0
    shared_experiences: List[str]
    trust_level: float
    respect_level: float
    emotional_attachment: float
    recent_interactions: List[Dict[str, Any]]

class AICompanion:
    def __init__(self, name: str, character_class: str, level: int = 1):
        self.name = name
        self.character_class = character_class
        self.level = level
        
        # Personality and decision-making
        self.personality_traits = self._generate_personality()
        self.core_values = self._generate_core_values()
        self.decision_patterns = self._initialize_decision_patterns()
        
        # Learning and memory
        self.memories = []
        self.learned_behaviors = {}
        self.player_behavior_model = {}
        self.relationships = {}
        
        # Combat and skills
        self.combat_preferences = self._initialize_combat_preferences()
        self.skill_priorities = self._initialize_skill_priorities()
        
        # Roleplay characteristics
        self.speech_patterns = self._generate_speech_patterns()
        self.backstory_hooks = self._generate_backstory_hooks()
        self.personal_goals = self._generate_personal_goals()
        
        # Adaptive learning
        self.adaptation_rate = 0.1
        self.last_performance_review = datetime.now()

    def _generate_personality(self) -> Dict[CompanionPersonality, float]:
        """Generate personality trait scores."""
        # Randomly assign personality traits with some correlation
        traits = {}
        primary_trait = random.choice(list(CompanionPersonality))
        
        for trait in CompanionPersonality:
            if trait == primary_trait:
                traits[trait] = random.uniform(0.7, 1.0)
            else:
                # Some traits correlate, others oppose
                base_score = random.uniform(0.1, 0.6)
                if self._traits_correlate(primary_trait, trait):
                    base_score += 0.2
                elif self._traits_oppose(primary_trait, trait):
                    base_score -= 0.2
                traits[trait] = max(0.0, min(1.0, base_score))
        
        return traits

    def _traits_correlate(self, trait1: CompanionPersonality, trait2: CompanionPersonality) -> bool:
        """Check if two personality traits typically correlate."""
        correlations = {
            CompanionPersonality.BRAVE: [CompanionPersonality.LOYAL, CompanionPersonality.PROTECTIVE],
            CompanionPersonality.CAUTIOUS: [CompanionPersonality.WISE, CompanionPersonality.ANALYTICAL],
            CompanionPersonality.CURIOUS: [CompanionPersonality.ANALYTICAL, CompanionPersonality.INDEPENDENT],
            CompanionPersonality.CHARISMATIC: [CompanionPersonality.INDEPENDENT, CompanionPersonality.IMPULSIVE]
        }
        
        return trait2 in correlations.get(trait1, []) or trait1 in correlations.get(trait2, [])

    def _traits_oppose(self, trait1: CompanionPersonality, trait2: CompanionPersonality) -> bool:
        """Check if two personality traits typically oppose each other."""
        oppositions = {
            CompanionPersonality.BRAVE: [CompanionPersonality.CAUTIOUS],
            CompanionPersonality.IMPULSIVE: [CompanionPersonality.WISE, CompanionPersonality.ANALYTICAL],
            CompanionPersonality.INDEPENDENT: [CompanionPersonality.LOYAL],
            CompanionPersonality.CAUTIOUS: [CompanionPersonality.IMPULSIVE]
        }
        
        return trait2 in oppositions.get(trait1, []) or trait1 in oppositions.get(trait2, [])

    def _generate_core_values(self) -> List[str]:
        """Generate core values based on personality."""
        possible_values = [
            "justice", "freedom", "loyalty", "knowledge", "power", "peace",
            "adventure", "family", "honor", "survival", "compassion", "truth"
        ]
        
        # Select values based on personality traits
        values = []
        if self.personality_traits[CompanionPersonality.LOYAL] > 0.6:
            values.append("loyalty")
        if self.personality_traits[CompanionPersonality.WISE] > 0.6:
            values.append("knowledge")
        if self.personality_traits[CompanionPersonality.BRAVE] > 0.6:
            values.append("justice")
        if self.personality_traits[CompanionPersonality.PROTECTIVE] > 0.6:
            values.append("compassion")
        
        # Add 2-3 random values
        remaining_values = [v for v in possible_values if v not in values]
        values.extend(random.sample(remaining_values, min(3, len(remaining_values))))
        
        return values[:5]  # Limit to 5 core values

    def _initialize_decision_patterns(self) -> Dict[DecisionContext, Dict[str, float]]:
        """Initialize decision-making patterns based on personality."""
        patterns = {}
        
        for context in DecisionContext:
            patterns[context] = {
                'risk_tolerance': self._calculate_risk_tolerance(context),
                'group_priority': self._calculate_group_priority(context),
                'information_gathering': self._calculate_information_preference(context),
                'action_speed': self._calculate_action_speed(context)
            }
        
        return patterns

    def _calculate_risk_tolerance(self, context: DecisionContext) -> float:
        """Calculate risk tolerance for specific context."""
        base_risk = self.personality_traits[CompanionPersonality.BRAVE] * 0.4 + \
                   self.personality_traits[CompanionPersonality.IMPULSIVE] * 0.3 - \
                   self.personality_traits[CompanionPersonality.CAUTIOUS] * 0.4
        
        # Context modifiers
        if context == DecisionContext.COMBAT:
            base_risk += 0.2 if self.character_class in ['fighter', 'barbarian', 'paladin'] else 0.0
        elif context == DecisionContext.SOCIAL:
            base_risk -= 0.1  # Social situations generally lower risk tolerance
        elif context == DecisionContext.EXPLORATION:
            base_risk += 0.1 if self.personality_traits[CompanionPersonality.CURIOUS] > 0.6 else 0.0
        
        return max(0.0, min(1.0, base_risk + 0.5))

    def _calculate_group_priority(self, context: DecisionContext) -> float:
        """Calculate how much the companion prioritizes group over individual goals."""
        base_group = self.personality_traits[CompanionPersonality.LOYAL] * 0.5 + \
                    self.personality_traits[CompanionPersonality.PROTECTIVE] * 0.3 - \
                    self.personality_traits[CompanionPersonality.INDEPENDENT] * 0.2
        
        return max(0.0, min(1.0, base_group + 0.3))

    def _calculate_information_preference(self, context: DecisionContext) -> float:
        """Calculate preference for gathering information before acting."""
        return self.personality_traits[CompanionPersonality.WISE] * 0.4 + \
               self.personality_traits[CompanionPersonality.ANALYTICAL] * 0.4 + \
               self.personality_traits[CompanionPersonality.CAUTIOUS] * 0.2

    def _calculate_action_speed(self, context: DecisionContext) -> float:
        """Calculate preference for quick vs deliberate action."""
        return self.personality_traits[CompanionPersonality.IMPULSIVE] * 0.5 - \
               self.personality_traits[CompanionPersonality.WISE] * 0.3 - \
               self.personality_traits[CompanionPersonality.CAUTIOUS] * 0.2 + 0.5

    def _initialize_combat_preferences(self) -> Dict[str, Any]:
        """Initialize combat decision preferences."""
        preferences = {
            'positioning': 'balanced',  # 'aggressive', 'defensive', 'balanced'
            'target_priority': 'threats',  # 'threats', 'weak', 'healers', 'casters'
            'resource_conservation': 0.5,  # 0.0 = spend freely, 1.0 = very conservative
            'team_coordination': 0.7,  # 0.0 = independent, 1.0 = highly coordinated
        }
        
        # Adjust based on personality and class
        if self.personality_traits[CompanionPersonality.BRAVE] > 0.6:
            preferences['positioning'] = 'aggressive'
        elif self.personality_traits[CompanionPersonality.CAUTIOUS] > 0.6:
            preferences['positioning'] = 'defensive'
        
        if self.personality_traits[CompanionPersonality.ANALYTICAL] > 0.6:
            preferences['target_priority'] = 'casters'
        elif self.personality_traits[CompanionPersonality.PROTECTIVE] > 0.6:
            preferences['target_priority'] = 'threats'
        
        return preferences

    def _initialize_skill_priorities(self) -> Dict[str, float]:
        """Initialize skill usage priorities."""
        skills = {
            'investigation': self.personality_traits[CompanionPersonality.ANALYTICAL],
            'perception': self.personality_traits[CompanionPersonality.CAUTIOUS],
            'persuasion': self.personality_traits[CompanionPersonality.CHARISMATIC],
            'stealth': self.personality_traits[CompanionPersonality.CAUTIOUS],
            'insight': self.personality_traits[CompanionPersonality.WISE],
            'athletics': self.personality_traits[CompanionPersonality.BRAVE],
        }
        
        return skills

    def _generate_speech_patterns(self) -> Dict[str, Any]:
        """Generate speech patterns for roleplay."""
        patterns = {
            'formality': 'casual',  # 'formal', 'casual', 'rough'
            'verbosity': 'moderate',  # 'terse', 'moderate', 'verbose'
            'optimism': 'balanced',  # 'pessimistic', 'balanced', 'optimistic'
            'humor': 'occasional',  # 'none', 'occasional', 'frequent'
        }
        
        # Adjust based on personality
        if self.personality_traits[CompanionPersonality.WISE] > 0.6:
            patterns['formality'] = 'formal'
            patterns['verbosity'] = 'verbose'
        
        if self.personality_traits[CompanionPersonality.CHARISMATIC] > 0.6:
            patterns['humor'] = 'frequent'
            patterns['optimism'] = 'optimistic'
        
        if self.personality_traits[CompanionPersonality.IMPULSIVE] > 0.6:
            patterns['verbosity'] = 'terse'
        
        return patterns

    def _generate_backstory_hooks(self) -> List[str]:
        """Generate backstory elements for roleplay."""
        possible_hooks = [
            "Has a mysterious past they don't talk about",
            "Searching for a long-lost family member",
            "Owes a debt to a powerful organization",
            "Was betrayed by a former ally",
            "Has prophetic dreams or visions",
            "Collects rare items related to their interests",
            "Has a rivalry with another adventurer",
            "Seeks to prove themselves worthy of something",
            "Has a phobia or fear they're trying to overcome",
            "Is secretly related to someone important"
        ]
        
        return random.sample(possible_hooks, random.randint(2, 4))

    def _generate_personal_goals(self) -> List[str]:
        """Generate personal goals that drive the companion."""
        goals = []
        
        # Goals based on values
        if "justice" in self.core_values:
            goals.append("Seek justice for past wrongs")
        if "knowledge" in self.core_values:
            goals.append("Uncover ancient secrets or lost lore")
        if "power" in self.core_values:
            goals.append("Become stronger to protect others")
        if "family" in self.core_values:
            goals.append("Find or protect family members")
        
        # Add class-specific goals
        class_goals = {
            'wizard': "Master a legendary spell",
            'rogue': "Pull off the perfect heist",
            'cleric': "Spread their deity's influence",
            'fighter': "Become a renowned warrior",
            'ranger': "Protect the natural world"
        }
        
        if self.character_class.lower() in class_goals:
            goals.append(class_goals[self.character_class.lower()])
        
        return goals

    async def make_decision(self, context: DecisionContext, situation: Dict[str, Any], 
                          available_actions: List[str]) -> CompanionAction:
        """Make a decision based on personality, context, and learned behavior."""
        # Analyze the situation
        risk_level = self._assess_situation_risk(situation)
        group_need = self._assess_group_need(situation)
        
        # Get decision patterns for this context
        patterns = self.decision_patterns[context]
        
        # Consider each available action
        action_scores = {}
        for action in available_actions:
            score = await self._score_action(action, context, situation, patterns, risk_level, group_need)
            action_scores[action] = score
        
        # Select best action (with some randomness for personality)
        best_action = max(action_scores.items(), key=lambda x: x[1])
        selected_action = best_action[0]
        
        # Add some personality-based randomness
        if self.personality_traits[CompanionPersonality.IMPULSIVE] > 0.6:
            if random.random() < 0.2:  # 20% chance to pick second-best option
                sorted_actions = sorted(action_scores.items(), key=lambda x: x[1], reverse=True)
                if len(sorted_actions) > 1:
                    selected_action = sorted_actions[1][0]
        
        # Generate reasoning
        reasoning = await self._generate_action_reasoning(selected_action, context, situation, patterns)
        
        # Create action object
        action = CompanionAction(
            action_type=selected_action,
            target=self._determine_action_target(selected_action, situation),
            description=f"{self.name} {self._describe_action(selected_action, situation)}",
            reasoning=reasoning,
            confidence=action_scores[selected_action],
            risk_assessment=risk_level,
            expected_outcome=self._predict_action_outcome(selected_action, situation),
            alternatives=[action for action, score in sorted(action_scores.items(), key=lambda x: x[1], reverse=True)[1:3]]
        )
        
        # Learn from this decision
        await self._record_decision(action, context, situation)
        
        return action

    def _assess_situation_risk(self, situation: Dict[str, Any]) -> float:
        """Assess the risk level of the current situation."""
        risk_factors = 0.0
        
        if situation.get('enemies_present'):
            risk_factors += 0.3
        if situation.get('unknown_elements'):
            risk_factors += 0.2
        if situation.get('time_pressure'):
            risk_factors += 0.2
        if situation.get('party_injured'):
            risk_factors += 0.3
        if situation.get('resources_low'):
            risk_factors += 0.2
        
        return min(1.0, risk_factors)

    def _assess_group_need(self, situation: Dict[str, Any]) -> float:
        """Assess how much the group needs help or coordination."""
        need_level = 0.0
        
        if situation.get('party_scattered'):
            need_level += 0.3
        if situation.get('party_injured'):
            need_level += 0.4
        if situation.get('complex_problem'):
            need_level += 0.2
        if situation.get('moral_dilemma'):
            need_level += 0.1
        
        return min(1.0, need_level)

    async def _score_action(self, action: str, context: DecisionContext, situation: Dict[str, Any],
                          patterns: Dict[str, float], risk_level: float, group_need: float) -> float:
        """Score an action based on personality and situation."""
        base_score = 0.5
        
        # Personality-based scoring
        if action in ['attack', 'charge', 'confront']:
            base_score += self.personality_traits[CompanionPersonality.BRAVE] * 0.3
            base_score -= self.personality_traits[CompanionPersonality.CAUTIOUS] * 0.2
        
        elif action in ['investigate', 'analyze', 'study']:
            base_score += self.personality_traits[CompanionPersonality.ANALYTICAL] * 0.4
            base_score += self.personality_traits[CompanionPersonality.CURIOUS] * 0.2
        
        elif action in ['help', 'heal', 'protect']:
            base_score += self.personality_traits[CompanionPersonality.PROTECTIVE] * 0.4
            base_score += self.personality_traits[CompanionPersonality.LOYAL] * 0.2
        
        elif action in ['negotiate', 'persuade', 'charm']:
            base_score += self.personality_traits[CompanionPersonality.CHARISMATIC] * 0.4
        
        elif action in ['hide', 'retreat', 'wait']:
            base_score += self.personality_traits[CompanionPersonality.CAUTIOUS] * 0.3
        
        # Risk adjustment
        action_risk = self._estimate_action_risk(action, situation)
        risk_tolerance = patterns['risk_tolerance']
        
        if action_risk > risk_tolerance:
            base_score -= (action_risk - risk_tolerance) * 0.5
        
        # Group priority adjustment
        if self._action_helps_group(action, situation):
            base_score += patterns['group_priority'] * 0.3
        
        # Learn from past experiences
        if action in self.learned_behaviors:
            past_success = self.learned_behaviors[action].get('success_rate', 0.5)
            base_score += (past_success - 0.5) * 0.2
        
        return max(0.0, min(1.0, base_score))

    def _estimate_action_risk(self, action: str, situation: Dict[str, Any]) -> float:
        """Estimate risk level of an action."""
        high_risk_actions = ['attack', 'charge', 'confront', 'split_party']
        medium_risk_actions = ['investigate', 'use_magic', 'climb', 'jump']
        low_risk_actions = ['hide', 'wait', 'retreat', 'talk']
        
        if action in high_risk_actions:
            return 0.8
        elif action in medium_risk_actions:
            return 0.5
        else:
            return 0.2

    def _action_helps_group(self, action: str, situation: Dict[str, Any]) -> bool:
        """Check if action primarily helps the group vs individual goals."""
        group_actions = ['help', 'heal', 'protect', 'coordinate', 'share_information', 'support']
        return action in group_actions

    async def _generate_action_reasoning(self, action: str, context: DecisionContext, 
                                       situation: Dict[str, Any], patterns: Dict[str, float]) -> str:
        """Generate reasoning for why the action was chosen."""
        # Base reasoning on personality
        if self.personality_traits[CompanionPersonality.ANALYTICAL] > 0.6:
            reasoning = f"After careful consideration of the situation, {action} seems like the most logical course of action."
        elif self.personality_traits[CompanionPersonality.IMPULSIVE] > 0.6:
            reasoning = f"I think we should {action} - let's not overthink this!"
        elif self.personality_traits[CompanionPersonality.CAUTIOUS] > 0.6:
            reasoning = f"Given the risks involved, {action} appears to be the safest option."
        elif self.personality_traits[CompanionPersonality.BRAVE] > 0.6:
            reasoning = f"The situation calls for action - {action} is what needs to be done."
        else:
            reasoning = f"Based on what I can see, {action} makes the most sense right now."
        
        # Add context-specific reasoning
        if context == DecisionContext.COMBAT:
            reasoning += " In combat, every moment counts."
        elif context == DecisionContext.SOCIAL:
            reasoning += " We need to handle this diplomatically."
        elif context == DecisionContext.EXPLORATION:
            reasoning += " There's more to discover here."
        
        return reasoning

    def _determine_action_target(self, action: str, situation: Dict[str, Any]) -> Optional[str]:
        """Determine the target for an action."""
        if action in ['attack', 'target', 'focus']:
            enemies = situation.get('enemies', [])
            if enemies:
                # Choose target based on combat preferences
                if self.combat_preferences['target_priority'] == 'threats':
                    return max(enemies, key=lambda e: e.get('threat_level', 0))
                elif self.combat_preferences['target_priority'] == 'weak':
                    return min(enemies, key=lambda e: e.get('hp', 100))
                else:
                    return random.choice(enemies)
        
        elif action in ['help', 'heal', 'protect']:
            allies = situation.get('allies', [])
            if allies:
                # Help most injured ally
                injured_allies = [a for a in allies if a.get('hp_percent', 100) < 50]
                if injured_allies:
                    return min(injured_allies, key=lambda a: a.get('hp_percent', 100))
                return random.choice(allies)
        
        return None

    def _describe_action(self, action: str, situation: Dict[str, Any]) -> str:
        """Generate a descriptive text for the action."""
        action_descriptions = {
            'attack': 'moves to attack the enemy',
            'defend': 'takes a defensive stance',
            'investigate': 'carefully examines the area',
            'help': 'rushes to help an ally',
            'cast_spell': 'begins casting a spell',
            'use_item': 'reaches for a useful item',
            'negotiate': 'attempts to negotiate',
            'retreat': 'strategically falls back',
            'hide': 'seeks cover and concealment',
            'wait': 'waits to see what happens next'
        }
        
        return action_descriptions.get(action, f'decides to {action}')

    def _predict_action_outcome(self, action: str, situation: Dict[str, Any]) -> str:
        """Predict the likely outcome of an action."""
        # Simple outcome prediction
        if action in ['attack', 'charge']:
            return "Deal damage to enemy, but may take damage in return"
        elif action in ['defend', 'hide']:
            return "Reduce incoming damage, but may miss opportunities"
        elif action in ['help', 'heal']:
            return "Improve ally's condition, strengthen party"
        elif action in ['investigate', 'analyze']:
            return "Gather information, potentially uncover secrets"
        else:
            return "Situation will develop based on action taken"

    async def _record_decision(self, action: CompanionAction, context: DecisionContext, situation: Dict[str, Any]):
        """Record decision for learning purposes."""
        decision_record = {
            'action': action.action_type,
            'context': context,
            'situation_factors': list(situation.keys()),
            'confidence': action.confidence,
            'timestamp': datetime.now(),
            'outcome_pending': True
        }
        
        # Add to memory
        memory = CompanionMemory(
            memory_id=f"decision_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            event_type='decision',
            participants=[self.name],
            location=situation.get('location', 'unknown'),
            outcome='pending',
            emotional_impact=0.0,
            lessons_learned=[],
            timestamp=datetime.now(),
            importance=action.confidence
        )
        
        self.memories.append(memory)

    async def learn_from_outcome(self, decision_id: str, outcome_success: bool, 
                                consequences: List[str], emotional_impact: float):
        """Learn from the outcome of a previous decision."""
        # Find the related memory
        memory = next((m for m in self.memories if m.memory_id == decision_id), None)
        if not memory:
            return
        
        # Update memory with outcome
        memory.outcome = 'success' if outcome_success else 'failure'
        memory.emotional_impact = emotional_impact
        memory.lessons_learned = consequences
        
        # Update learned behaviors
        action = memory.event_type
        if action not in self.learned_behaviors:
            self.learned_behaviors[action] = {
                'attempts': 0,
                'successes': 0,
                'success_rate': 0.5,
                'recent_outcomes': []
            }
        
        behavior = self.learned_behaviors[action]
        behavior['attempts'] += 1
        if outcome_success:
            behavior['successes'] += 1
        
        behavior['success_rate'] = behavior['successes'] / behavior['attempts']
        behavior['recent_outcomes'].append(outcome_success)
        
        # Keep only recent outcomes (last 10)
        if len(behavior['recent_outcomes']) > 10:
            behavior['recent_outcomes'] = behavior['recent_outcomes'][-10:]
        
        # Adjust personality slightly based on strong emotional impacts
        if abs(emotional_impact) > 0.7:
            await self._adapt_personality(outcome_success, emotional_impact, consequences)

    async def _adapt_personality(self, success: bool, emotional_impact: float, consequences: List[str]):
        """Slightly adapt personality based on significant experiences."""
        adaptation_strength = self.adaptation_rate * abs(emotional_impact)
        
        # If action was very successful or failed badly, adjust related traits
        if success and emotional_impact > 0.7:
            # Positive reinforcement
            if 'brave_action' in consequences:
                self.personality_traits[CompanionPersonality.BRAVE] = min(1.0, 
                    self.personality_traits[CompanionPersonality.BRAVE] + adaptation_strength)
            if 'team_success' in consequences:
                self.personality_traits[CompanionPersonality.LOYAL] = min(1.0,
                    self.personality_traits[CompanionPersonality.LOYAL] + adaptation_strength)
        
        elif not success and emotional_impact < -0.7:
            # Negative reinforcement
            if 'reckless_failure' in consequences:
                self.personality_traits[CompanionPersonality.IMPULSIVE] = max(0.0,
                    self.personality_traits[CompanionPersonality.IMPULSIVE] - adaptation_strength)
                self.personality_traits[CompanionPersonality.CAUTIOUS] = min(1.0,
                    self.personality_traits[CompanionPersonality.CAUTIOUS] + adaptation_strength)

    async def build_relationship(self, character_name: str, interaction_type: str, 
                               outcome: str, shared_experience: str):
        """Build or modify relationship with a character."""
        if character_name not in self.relationships:
            self.relationships[character_name] = RelationshipBond(
                target_character=character_name,
                relationship_type='acquaintance',
                bond_strength=0.1,
                shared_experiences=[],
                trust_level=0.5,
                respect_level=0.5,
                emotional_attachment=0.1,
                recent_interactions=[]
            )
        
        bond = self.relationships[character_name]
        
        # Record the interaction
        interaction = {
            'type': interaction_type,
            'outcome': outcome,
            'experience': shared_experience,
            'timestamp': datetime.now().isoformat()
        }
        bond.recent_interactions.append(interaction)
        
        # Keep only recent interactions
        if len(bond.recent_interactions) > 20:
            bond.recent_interactions = bond.recent_interactions[-20:]
        
        # Adjust relationship based on interaction
        await self._adjust_relationship_values(bond, interaction_type, outcome, shared_experience)
        
        # Update relationship type based on current values
        self._update_relationship_type(bond)

    async def _adjust_relationship_values(self, bond: RelationshipBond, interaction_type: str, 
                                        outcome: str, shared_experience: str):
        """Adjust relationship values based on interaction."""
        adjustment = 0.0
        
        # Base adjustment based on outcome
        if outcome in ['success', 'positive', 'helpful']:
            adjustment = 0.05
        elif outcome in ['failure', 'negative', 'harmful']:
            adjustment = -0.05
        
        # Interaction type modifiers
        if interaction_type == 'combat_support':
            bond.trust_level = min(1.0, bond.trust_level + adjustment * 2)
            if self.personality_traits[CompanionPersonality.LOYAL] > 0.6:
                bond.bond_strength = min(1.0, bond.bond_strength + adjustment * 1.5)
        
        elif interaction_type == 'social_support':
            bond.emotional_attachment = min(1.0, bond.emotional_attachment + adjustment * 1.5)
            if self.personality_traits[CompanionPersonality.CHARISMATIC] > 0.6:
                bond.bond_strength = min(1.0, bond.bond_strength + adjustment)
        
        elif interaction_type == 'disagreement':
            bond.respect_level = max(0.0, bond.respect_level + adjustment)
            if outcome == 'resolved':
                bond.trust_level = min(1.0, bond.trust_level + 0.02)
        
        elif interaction_type == 'shared_danger':
            bond.bond_strength = min(1.0, bond.bond_strength + adjustment * 2)
            bond.shared_experiences.append(shared_experience)
        
        # Ensure values stay in bounds
        bond.trust_level = max(0.0, min(1.0, bond.trust_level))
        bond.respect_level = max(0.0, min(1.0, bond.respect_level))
        bond.emotional_attachment = max(0.0, min(1.0, bond.emotional_attachment))
        bond.bond_strength = max(0.0, min(1.0, bond.bond_strength))

    def _update_relationship_type(self, bond: RelationshipBond):
        """Update relationship type based on current values."""
        if bond.bond_strength > 0.8 and bond.emotional_attachment > 0.7:
            bond.relationship_type = 'close_friend'
        elif bond.bond_strength > 0.6 and bond.trust_level > 0.7:
            bond.relationship_type = 'trusted_ally'
        elif bond.respect_level < 0.3 or bond.trust_level < 0.2:
            bond.relationship_type = 'distrust'
        elif bond.bond_strength > 0.4:
            bond.relationship_type = 'friend'
        else:
            bond.relationship_type = 'acquaintance'

    async def generate_roleplay_response(self, situation: str, speaker: str, message: str) -> str:
        """Generate a roleplay response based on personality and relationships."""
        # Get relationship context if speaker is known
        relationship = self.relationships.get(speaker)
        
        # Determine emotional tone based on personality and relationship
        tone = self._determine_response_tone(relationship, situation, message)
        
        # Generate response based on speech patterns
        response = await self._generate_contextual_response(tone, situation, speaker, message)
        
        return response

    def _determine_response_tone(self, relationship: Optional[RelationshipBond], 
                                situation: str, message: str) -> str:
        """Determine appropriate emotional tone for response."""
        base_tone = "neutral"
        
        # Relationship influence
        if relationship:
            if relationship.relationship_type == 'close_friend':
                base_tone = "warm"
            elif relationship.relationship_type == 'distrust':
                base_tone = "guarded"
            elif relationship.relationship_type == 'trusted_ally':
                base_tone = "cooperative"
        
        # Personality influence
        if self.personality_traits[CompanionPersonality.CHARISMATIC] > 0.6:
            base_tone = "friendly"
        elif self.personality_traits[CompanionPersonality.CAUTIOUS] > 0.6:
            base_tone = "measured"
        elif self.personality_traits[CompanionPersonality.BRAVE] > 0.6:
            base_tone = "confident"
        
        # Situation modifiers
        if 'danger' in situation.lower() or 'combat' in situation.lower():
            base_tone = "serious"
        elif 'celebration' in situation.lower() or 'victory' in situation.lower():
            base_tone = "cheerful"
        
        return base_tone

    async def _generate_contextual_response(self, tone: str, situation: str, 
                                          speaker: str, message: str) -> str:
        """Generate contextual response based on tone and speech patterns."""
        # This would use more sophisticated NLP in production
        formality = self.speech_patterns['formality']
        verbosity = self.speech_patterns['verbosity']
        
        if tone == "warm":
            if verbosity == "terse":
                return f"*{self.name} smiles warmly* Good thinking, {speaker}."
            else:
                return f"*{self.name} nods approvingly* I'm glad you brought that up, {speaker}. That's exactly what we need to consider."
        
        elif tone == "guarded":
            return f"*{self.name} eyes {speaker} warily* I'm not sure about that..."
        
        elif tone == "confident":
            return f"*{self.name} speaks with conviction* {speaker}, I believe we should move forward with this."
        
        elif tone == "serious":
            return f"*{self.name} speaks grimly* {speaker}, the situation is more dangerous than we thought."
        
        else:  # neutral
            return f"*{self.name} considers the words carefully* That's an interesting point, {speaker}."

    def get_character_summary(self) -> Dict[str, Any]:
        """Get a summary of the companion's current state."""
        return {
            'name': self.name,
            'class': self.character_class,
            'level': self.level,
            'dominant_traits': {k.value: v for k, v in self.personality_traits.items() if v > 0.6},
            'core_values': self.core_values,
            'relationships': {name: bond.relationship_type for name, bond in self.relationships.items()},
            'learned_behaviors': len(self.learned_behaviors),
            'memories': len(self.memories),
            'recent_performance': self._calculate_recent_performance()
        }

    def _calculate_recent_performance(self) -> Dict[str, float]:
        """Calculate recent performance metrics."""
        recent_memories = [m for m in self.memories if 
                          (datetime.now() - m.timestamp).days < 7]
        
        if not recent_memories:
            return {'success_rate': 0.5, 'confidence': 0.5, 'team_contribution': 0.5}
        
        successes = len([m for m in recent_memories if m.outcome == 'success'])
        success_rate = successes / len(recent_memories)
        
        avg_confidence = sum(m.importance for m in recent_memories) / len(recent_memories)
        
        # Team contribution based on relationship building
        team_contribution = sum(bond.bond_strength for bond in self.relationships.values()) / max(1, len(self.relationships))
        
        return {
            'success_rate': success_rate,
            'confidence': avg_confidence,
            'team_contribution': team_contribution
        }

class CompanionManager:
    """Manager class for handling multiple AI companions in a session."""
    
    def __init__(self):
        self.active_companions = {}  # session_id -> List[AICompanion]
        self.group_dynamics = {}  # session_id -> group interaction data
    
    def add_companion_to_session(self, session_id: str, companion: AICompanion):
        """Add a companion to a session."""
        if session_id not in self.active_companions:
            self.active_companions[session_id] = []
        
        self.active_companions[session_id].append(companion)
        logger.info(f"Added companion {companion.name} to session {session_id}")
    
    async def process_group_decision(self, session_id: str, context: DecisionContext, 
                                   situation: Dict[str, Any], available_actions: List[str]) -> List[CompanionAction]:
        """Process decisions for all companions in a group context."""
        if session_id not in self.active_companions:
            return []
        
        companions = self.active_companions[session_id]
        decisions = []
        
        for companion in companions:
            # Each companion makes their decision
            action = await companion.make_decision(context, situation, available_actions)
            decisions.append(action)
            
            # Update group dynamics
            await self._update_group_dynamics(session_id, companion, action)
        
        return decisions
    
    async def _update_group_dynamics(self, session_id: str, companion: AICompanion, action: CompanionAction):
        """Update group dynamics based on companion actions."""
        if session_id not in self.group_dynamics:
            self.group_dynamics[session_id] = {
                'cooperation_level': 0.5,
                'leadership_hierarchy': [],
                'conflict_frequency': 0.0,
                'group_cohesion': 0.5
            }
        
        dynamics = self.group_dynamics[session_id]
        
        # Analyze action for group impact
        if action.action_type in ['help', 'coordinate', 'support']:
            dynamics['cooperation_level'] = min(1.0, dynamics['cooperation_level'] + 0.02)
        elif action.action_type in ['ignore_group', 'contradict', 'abandon']:
            dynamics['cooperation_level'] = max(0.0, dynamics['cooperation_level'] - 0.05)
    
    def get_group_status(self, session_id: str) -> Dict[str, Any]:
        """Get current group status and dynamics."""
        if session_id not in self.active_companions:
            return {}
        
        companions = self.active_companions[session_id]
        dynamics = self.group_dynamics.get(session_id, {})
        
        return {
            'companion_count': len(companions),
            'companions': [c.get_character_summary() for c in companions],
            'group_dynamics': dynamics,
            'average_performance': self._calculate_group_performance(companions)
        }
    
    def _calculate_group_performance(self, companions: List[AICompanion]) -> Dict[str, float]:
        """Calculate overall group performance metrics."""
        if not companions:
            return {}
        
        performances = [c._calculate_recent_performance() for c in companions]
        
        return {
            'avg_success_rate': sum(p['success_rate'] for p in performances) / len(performances),
            'avg_confidence': sum(p['confidence'] for p in performances) / len(performances),
            'avg_team_contribution': sum(p['team_contribution'] for p in performances) / len(performances)
        }