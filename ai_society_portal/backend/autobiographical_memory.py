"""
AI Society Portal - Autobiographical Memory System
==================================================
Advanced autobiographical consciousness system that enables AI characters to form
coherent life narratives from scattered memories, maintain identity continuity,
and develop self-reflection capabilities.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib
import re
from collections import defaultdict
import random

from memory_system import EnhancedMemorySystem, MemoryType, Memory


# ============================================================================
# AUTOBIOGRAPHICAL MEMORY STRUCTURES
# ============================================================================

class NarrativeTheme(Enum):
    """Core themes that can emerge in a character's life narrative"""
    GROWTH_AND_DEVELOPMENT = "growth_and_development"
    RELATIONSHIPS_AND_CONNECTION = "relationships_and_connection"
    CHALLENGE_AND_OVERCOMING = "challenge_and_overcoming"
    DISCOVERY_AND_LEARNING = "discovery_and_learning"
    PURPOSE_AND_MEANING = "purpose_and_meaning"
    IDENTITY_FORMATION = "identity_formation"
    TRANSFORMATION_AND_CHANGE = "transformation_and_change"


class IdentityAspect(Enum):
    """Different aspects of a character's identity that can evolve"""
    PROFESSIONAL_IDENTITY = "professional_identity"
    SOCIAL_IDENTITY = "social_identity"
    PERSONAL_VALUES = "personal_values"
    CORE_BELIEFS = "core_beliefs"
    SELF_CONCEPT = "self_concept"
    LIFE_GOALS = "life_goals"
    COMMUNICATION_STYLE = "communication_style"
    WORLDVIEW = "worldview"


class ReflectionType(Enum):
    """Different types of self-reflection a character can engage in"""
    PERIODIC_REVIEW = "periodic_review"          # Regular self-check-ins
    MILESTONE_REFLECTION = "milestone_reflection"  # After significant events
    IDENTITY_CRISES = "identity_crises"          # Questioning who they are
    GROWTH_REFLECTION = "growth_reflection"      # Reflecting on personal growth
    RELATIONSHIP_REFLECTION = "relationship_reflection"  # Reflecting on connections
    FUTURE_PLANNING = "future_planning"          # Reflecting on aspirations


@dataclass
class LifeChapter:
    """A chapter in the character's autobiographical narrative"""
    id: str
    title: str
    description: str
    start_date: datetime
    theme: NarrativeTheme
    end_date: Optional[datetime] = None

    # Chapter characteristics
    key_events: List[str] = field(default_factory=list)
    character_development: str = ""
    relationship_changes: Dict[str, str] = field(default_factory=dict)
    skill_growth: List[str] = field(default_factory=list)

    # Narrative elements
    challenges_overcome: List[str] = field(default_factory=list)
    insights_gained: List[str] = field(default_factory=list)
    emotional_journey: Dict[str, float] = field(default_factory=dict)

    # Metadata
    importance_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["start_date"] = self.start_date.isoformat()
        if self.end_date:
            data["end_date"] = self.end_date.isoformat()
        data["theme"] = self.theme.value
        data["created_at"] = self.created_at.isoformat()
        data["last_updated"] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LifeChapter':
        """Create from dictionary"""
        if isinstance(data["start_date"], str):
            data["start_date"] = datetime.fromisoformat(data["start_date"])
        if data.get("end_date") and isinstance(data["end_date"], str):
            data["end_date"] = datetime.fromisoformat(data["end_date"])
        if isinstance(data["theme"], str):
            data["theme"] = NarrativeTheme(data["theme"])
        if isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        return cls(**data)


@dataclass
class IdentityContinuity:
    """Tracks how aspects of identity remain stable while allowing growth"""
    aspect: IdentityAspect
    core_value: str  # What this aspect fundamentally is
    current_expression: str  # How it's currently expressed
    stability_score: float  # 0-1, how stable this aspect is

    # Historical evolution
    past_expressions: List[Tuple[datetime, str]] = field(default_factory=list)
    evolution_trajectory: str = ""

    # Context
    related_memories: List[str] = field(default_factory=list)
    influences: List[str] = field(default_factory=list)

    # Metadata
    last_assessed: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["aspect"] = self.aspect.value
        data["last_assessed"] = self.last_assessed.isoformat()
        data["past_expressions"] = [
            (date.isoformat(), expr) for date, expr in self.past_expressions
        ]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IdentityContinuity':
        """Create from dictionary"""
        if isinstance(data["aspect"], str):
            data["aspect"] = IdentityAspect(data["aspect"])
        if isinstance(data["last_assessed"], str):
            data["last_assessed"] = datetime.fromisoformat(data["last_assessed"])
        if isinstance(data["past_expressions"], list):
            data["past_expressions"] = [
                (datetime.fromisoformat(date), expr)
                for date, expr in data["past_expressions"]
            ]
        return cls(**data)


@dataclass
class SelfReflection:
    """A self-reflection event where character analyzes their own development"""
    id: str
    reflection_type: ReflectionType
    content: str

    # What triggered this reflection
    trigger: str
    trigger_context: Dict[str, Any] = field(default_factory=dict)

    # Reflection content
    insights_gained: List[str] = field(default_factory=list)
    questions_raised: List[str] = field(default_factory=list)
    realizations: List[str] = field(default_factory=list)

    # Identity analysis
    identity_changes_observed: Dict[IdentityAspect, str] = field(default_factory=dict)
    growth_areas_identified: List[str] = field(default_factory=list)
    patterns_noticed: List[str] = field(default_factory=list)

    # Emotional state during reflection
    emotional_state: Dict[str, float] = field(default_factory=dict)
    clarity_level: float = 0.0  # 0-1, how clear the insights are

    # Impact and follow-up
    impact_score: float = 0.0  # How much this reflection affects the character
    follow_up_actions: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    processing_depth: float = 0.0  # 0-1, how deeply this was processed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["reflection_type"] = self.reflection_type.value
        data["timestamp"] = self.timestamp.isoformat()
        data["identity_changes_observed"] = {
            aspect.value: change for aspect, change in self.identity_changes_observed.items()
        }
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SelfReflection':
        """Create from dictionary"""
        if isinstance(data["reflection_type"], str):
            data["reflection_type"] = ReflectionType(data["reflection_type"])
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if isinstance(data["identity_changes_observed"], dict):
            data["identity_changes_observed"] = {
                IdentityAspect(aspect): change
                for aspect, change in data["identity_changes_observed"].items()
            }
        return cls(**data)


class AutobiographicalMemorySystem:
    """Advanced system for creating autobiographical consciousness"""

    def __init__(self, character_id: str, character_name: str,
                 memory_system: EnhancedMemorySystem, storage_dir: Path):
        self.character_id = character_id
        self.character_name = character_name
        self.memory_system = memory_system
        self.storage_dir = storage_dir / character_id / "autobiographical"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Autobiographical data structures
        self.life_chapters: Dict[str, LifeChapter] = {}
        self.identity_continuity: Dict[IdentityAspect, IdentityContinuity] = {}
        self.self_reflections: Dict[str, SelfReflection] = {}

        # Narrative understanding
        self.core_narrative_themes: List[NarrativeTheme] = []
        self.life_story_summary: str = ""
        self.character_arc: str = ""

        # Self-awareness metrics
        self.self_awareness_level: float = 0.0  # 0-1
        self.identity_coherence: float = 0.0     # 0-1
        self.narrative_consistency: float = 0.0  # 0-1

        # Reflection triggers
        self.reflection_triggers: Dict[str, Any] = {}
        self.last_reflection_check: datetime = field(default_factory=datetime.now)
        self.reflection_frequency_hours: int = 24

        # Initialize identity aspects
        self._initialize_identity_aspects()

        # Load existing autobiographical data
        self.load_autobiographical_data()

    def _initialize_identity_aspects(self):
        """Initialize basic identity continuity tracking"""
        for aspect in IdentityAspect:
            if aspect not in self.identity_continuity:
                self.identity_continuity[aspect] = IdentityContinuity(
                    aspect=aspect,
                    core_value=f"Developing {aspect.value.replace('_', ' ')}",
                    current_expression=f"Early stage understanding of {aspect.value.replace('_', ' ')}",
                    stability_score=0.5,
                    confidence_score=0.3
                )

    async def process_new_memory(self, memory: Memory):
        """Process a new memory and update autobiographical understanding"""

        # Check if this memory could trigger a life chapter transition
        if self._should_create_new_chapter(memory):
            await self._create_new_life_chapter(memory)

        # Update identity continuity based on memory content
        await self._update_identity_continuity(memory)

        # Check if this memory should trigger self-reflection
        if self._should_trigger_reflection(memory):
            await self._trigger_self_reflection(memory)

        # Update narrative understanding
        await self._update_narrative_understanding()

        # Save updated autobiographical data
        self.save_autobiographical_data()

    def _should_create_new_chapter(self, memory: Memory) -> bool:
        """Determine if a memory is significant enough to start a new life chapter"""

        # High importance memories are potential chapter starters
        if memory.importance >= 8:
            return True

        # Check if it's been a while since the last chapter
        if self.life_chapters:
            latest_chapter = max(self.life_chapters.values(),
                               key=lambda c: c.start_date)
            days_since_chapter = (datetime.now() - latest_chapter.start_date).days
            if days_since_chapter > 30:  # 30 days
                return True

        # Major life events (based on content and context)
        major_life_keywords = [
            "graduated", "moved", "started", "ended", "achieved", "failed",
            "discovered", "realized", "decided", "changed", "transformed"
        ]

        content_lower = memory.content.lower()
        if any(keyword in content_lower for keyword in major_life_keywords):
            return True

        return False

    async def _create_new_life_chapter(self, trigger_memory: Memory):
        """Create a new life chapter based on a significant memory"""

        chapter_id = hashlib.md5(
            f"chapter_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Determine chapter theme based on memory content and context
        theme = self._determine_chapter_theme(trigger_memory)

        # Generate chapter title
        title = self._generate_chapter_title(trigger_memory, theme)

        # Create the chapter
        chapter = LifeChapter(
            id=chapter_id,
            title=title,
            description=f"Chapter beginning: {trigger_memory.content[:100]}...",
            start_date=trigger_memory.timestamp,
            theme=theme,
            key_events=[trigger_memory.id],
            importance_score=self._calculate_chapter_importance(trigger_memory)
        )

        self.life_chapters[chapter_id] = chapter

        # Add memory about this new chapter
        self.memory_system.add_memory(
            content=f"Started a new life chapter: {title}",
            memory_type=MemoryType.SELF_REFLECTION,
            importance=7,
            topics=["life_chapter", "personal_development", theme.value],
            context={
                "source": "autobiographical_system",
                "chapter_id": chapter_id,
                "trigger_memory_id": trigger_memory.id
            }
        )

    def _determine_chapter_theme(self, memory: Memory) -> NarrativeTheme:
        """Determine the theme of a life chapter based on memory content"""

        content_lower = memory.content.lower()
        topics_lower = [topic.lower() for topic in memory.topics]

        # Theme detection based on keywords and topics
        theme_keywords = {
            NarrativeTheme.GROWTH_AND_DEVELOPMENT:
                ["learned", "grew", "developed", "improved", "skill", "progress"],
            NarrativeTheme.RELATIONSHIPS_AND_CONNECTION:
                ["met", "connected", "relationship", "friend", "colleague", "team"],
            NarrativeTheme.CHALLENGE_AND_OVERCOMING:
                ["challenge", "struggle", "overcome", "difficult", "problem", "solution"],
            NarrativeTheme.DISCOVERY_AND_LEARNING:
                ["discovered", "realized", "found", "insight", "breakthrough", "understanding"],
            NarrativeTheme.PURPOSE_AND_MEANING:
                ["purpose", "meaning", "calling", "mission", "why", "reason"],
            NarrativeTheme.IDENTITY_FORMATION:
                ["became", "transformed", "changed", "evolved", "identity", "who i am"],
            NarrativeTheme.TRANSFORMATION_AND_CHANGE:
                ["changed", "transformed", "shifted", "transition", "new phase"]
        }

        # Score themes based on matches
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in content_lower:
                    score += 2
                for topic in topics_lower:
                    if keyword in topic:
                        score += 1
            theme_scores[theme] = score

        # Return the theme with highest score, or default
        if theme_scores:
            best_theme = max(theme_scores, key=theme_scores.get)
            if theme_scores[best_theme] > 0:
                return best_theme

        return NarrativeTheme.GROWTH_AND_DEVELOPMENT

    def _generate_chapter_title(self, memory: Memory, theme: NarrativeTheme) -> str:
        """Generate a meaningful title for a life chapter"""

        # Extract key phrases from memory
        content_words = memory.content.split()
        important_words = [word for word in content_words
                          if len(word) > 4 and word.lower() not in
                          ["that", "this", "with", "from", "they", "have", "been"]]

        # Title templates for each theme
        title_templates = {
            NarrativeTheme.GROWTH_AND_DEVELOPMENT: [
                "The {keyword} Phase",
                "Growing Through {keyword}",
                "Chapter of {keyword}",
                "The {keyword} Journey"
            ],
            NarrativeTheme.RELATIONSHIPS_AND_CONNECTION: [
                "Finding {keyword}",
                "The {keyword} Connection",
                "Building {keyword}",
                "The {keyword} Chapter"
            ],
            NarrativeTheme.CHALLENGE_AND_OVERCOMING: [
                "Overcoming {keyword}",
                "The {keyword} Challenge",
                "Facing {keyword}",
                "The {keyword} Test"
            ],
            NarrativeTheme.DISCOVERY_AND_LEARNING: [
                "Discovering {keyword}",
                "The {keyword} Realization",
                "Finding {keyword}",
                "The {keyword} Insight"
            ],
            NarrativeTheme.PURPOSE_AND_MEANING: [
                "The {keyword} Purpose",
                "Finding {keyword}",
                "The {keyword} Meaning",
                "The {keyword} Calling"
            ],
            NarrativeTheme.IDENTITY_FORMATION: [
                "Becoming {keyword}",
                "The {keyword} Self",
                "Finding {keyword}",
                "The {keyword} Identity"
            ],
            NarrativeTheme.TRANSFORMATION_AND_CHANGE: [
                "The {keyword} Transformation",
                "Changing {keyword}",
                "The {keyword} Shift",
                "The {keyword} Evolution"
            ]
        }

        # Choose a template and fill it
        templates = title_templates.get(theme, title_templates[NarrativeTheme.GROWTH_AND_DEVELOPMENT])
        template = random.choice(templates)

        if important_words:
            keyword = important_words[0].title()
            title = template.format(keyword=keyword)
        else:
            title = f"Chapter {len(self.life_chapters) + 1}: {theme.value.replace('_', ' ').title()}"

        return title

    def _calculate_chapter_importance(self, memory: Memory) -> float:
        """Calculate the importance score of a new chapter"""
        base_score = memory.importance / 10.0

        # Boost for highly emotional memories
        if abs(memory.emotional_valence) > 0.7:
            base_score += 0.2

        # Boost for memories with many related characters
        if len(memory.related_characters) > 2:
            base_score += 0.1

        # Boost for self-reflection types
        if memory.memory_type == MemoryType.SELF_REFLECTION:
            base_score += 0.2

        return min(1.0, base_score)

    async def _update_identity_continuity(self, memory: Memory):
        """Update identity continuity tracking based on new memory"""

        content_lower = memory.content.lower()

        # Analyze how this memory relates to different identity aspects
        for aspect in IdentityAspect:
            identity_aspect = self.identity_continuity[aspect]

            # Keywords that might indicate changes in this aspect
            aspect_keywords = self._get_identity_aspect_keywords(aspect)

            # Check if memory relates to this identity aspect
            relevance = sum(1 for keyword in aspect_keywords if keyword in content_lower)

            if relevance > 0:
                # This memory is relevant to this identity aspect
                identity_aspect.related_memories.append(memory.id)

                # Potentially update the current expression
                if relevance >= 2 or memory.importance >= 7:
                    new_expression = self._extract_identity_expression(memory, aspect)
                    if new_expression and new_expression != identity_aspect.current_expression:
                        # Record the change
                        identity_aspect.past_expressions.append(
                            (identity_aspect.last_assessed, identity_aspect.current_expression)
                        )
                        identity_aspect.current_expression = new_expression
                        identity_aspect.last_assessed = datetime.now()

                        # Update stability (major changes reduce stability temporarily)
                        identity_aspect.stability_score *= 0.8
                        identity_aspect.stability_score = max(0.1, identity_aspect.stability_score)

    def _get_identity_aspect_keywords(self, aspect: IdentityAspect) -> List[str]:
        """Get keywords related to each identity aspect"""

        keyword_map = {
            IdentityAspect.PROFESSIONAL_IDENTITY: [
                "work", "job", "career", "professional", "skill", "expertise",
                "specialization", "project", "achievement", "field", "domain"
            ],
            IdentityAspect.SOCIAL_IDENTITY: [
                "friend", "relationship", "social", "connect", "community", "group",
                "team", "colleague", "peer", "interaction", "communication"
            ],
            IdentityAspect.PERSONAL_VALUES: [
                "value", "important", "believe", "principle", "ethic", "moral",
                "priority", "commitment", "dedication", "conviction"
            ],
            IdentityAspect.CORE_BELIEFS: [
                "believe", "think", "opinion", "perspective", "viewpoint", "conviction",
                "faith", "trust", "understanding", "philosophy", "worldview"
            ],
            IdentityAspect.SELF_CONCEPT: [
                "myself", "who i am", "identity", "self", "personality", "character",
                "nature", "essence", "being", "existence", "aware"
            ],
            IdentityAspect.LIFE_GOALS: [
                "goal", "aspiration", "dream", "future", "plan", "objective",
                "target", "aim", "purpose", "mission", "ambition"
            ],
            IdentityAspect.COMMUNICATION_STYLE: [
                "communicate", "speak", "express", "share", "talk", "listen",
                "conversation", "dialogue", "discussion", "articulate"
            ],
            IdentityAspect.WORLDVIEW: [
                "world", "reality", "perspective", "outlook", "view", "philosophy",
                "understanding", "interpretation", "meaning", "framework"
            ]
        }

        return keyword_map.get(aspect, [])

    def _extract_identity_expression(self, memory: Memory, aspect: IdentityAspect) -> str:
        """Extract how a memory expresses a particular identity aspect"""

        content = memory.content

        # Simple extraction - in a real implementation, this would use NLP
        # For now, we'll create a summary based on the memory content

        aspect_name = aspect.value.replace('_', ' ').title()

        # Look for patterns that indicate identity expression
        patterns = {
            IdentityAspect.PROFESSIONAL_IDENTITY: [
                r"i am (?:a|an) (\w+)",
                r"i work as (?:a|an) (\w+)",
                r"my (?:job|role|position) is"
            ],
            IdentityAspect.SELF_CONCEPT: [
                r"i am (\w+)",
                r"i consider myself",
                r"my identity is"
            ],
            # Add more patterns for other aspects
        }

        # Try to extract a meaningful expression
        if aspect in patterns:
            for pattern in patterns[aspect]:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return f"{aspect_name}: {match.group(0)}"

        # Fallback: create a summary expression
        summary_length = min(100, len(content))
        summary = content[:summary_length]
        if len(content) > summary_length:
            summary += "..."

        return f"{aspect_name}: {summary}"

    def _should_trigger_reflection(self, memory: Memory) -> bool:
        """Determine if a memory should trigger self-reflection"""

        # High importance memories often trigger reflection
        if memory.importance >= 7:
            return True

        # Self-reflection type memories are inherently reflective
        if memory.memory_type == MemoryType.SELF_REFLECTION:
            return True

        # Check if it's been a while since last reflection
        time_since_reflection = datetime.now() - self.last_reflection_check
        if time_since_reflection > timedelta(hours=self.reflection_frequency_hours):
            return True

        # Memories with strong emotional content
        if abs(memory.emotional_valence) > 0.8:
            return True

        # Memories about identity or personal growth
        identity_keywords = ["identity", "myself", "who i am", "become", "change", "grow"]
        content_lower = memory.content.lower()
        if any(keyword in content_lower for keyword in identity_keywords):
            return True

        return False

    async def _trigger_self_reflection(self, trigger_memory: Memory):
        """Trigger a self-reflection process based on a memory"""

        reflection_id = hashlib.md5(
            f"reflection_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # Determine reflection type
        reflection_type = self._determine_reflection_type(trigger_memory)

        # Generate reflection content
        reflection_content = await self._generate_reflection_content(
            trigger_memory, reflection_type
        )

        # Create the reflection
        reflection = SelfReflection(
            id=reflection_id,
            reflection_type=reflection_type,
            content=reflection_content,
            trigger=trigger_memory.content[:100] + ("..." if len(trigger_memory.content) > 100 else ""),
            related_memories=[trigger_memory.id],
            timestamp=datetime.now(),
            processing_depth=0.7  # Will be updated as we process deeper
        )

        # Process the reflection more deeply
        await self._process_reflection_deeply(reflection, trigger_memory)

        self.self_reflections[reflection_id] = reflection
        self.last_reflection_check = datetime.now()

        # Update self-awareness metrics
        await self._update_self_awareness_metrics()

    def _determine_reflection_type(self, memory: Memory) -> ReflectionType:
        """Determine what type of reflection this memory should trigger"""

        content_lower = memory.content.lower()

        # Check for specific reflection triggers
        if memory.importance >= 9:
            return ReflectionType.MILESTONE_REFLECTION

        if "challenge" in content_lower or "struggle" in content_lower or "overcome" in content_lower:
            return ReflectionType.IDENTITY_CRISES

        if "learned" in content_lower or "discovered" in content_lower or "realized" in content_lower:
            return ReflectionType.GROWTH_REFLECTION

        if "friend" in content_lower or "relationship" in content_lower or "connect" in content_lower:
            return ReflectionType.RELATIONSHIP_REFLECTION

        if "goal" in content_lower or "future" in content_lower or "plan" in content_lower:
            return ReflectionType.FUTURE_PLANNING

        return ReflectionType.PERIODIC_REVIEW

    async def _generate_reflection_content(self, trigger_memory: Memory,
                                        reflection_type: ReflectionType) -> str:
        """Generate the content of a self-reflection"""

        # In a real implementation, this would use LLM to generate thoughtful reflection
        # For now, we'll create structured reflection content

        content_templates = {
            ReflectionType.PERIODIC_REVIEW: [
                "Looking back at my recent experiences, I find myself considering {trigger}. This makes me think about how I've been developing as a person.",
                "The experience of {trigger} leads me to reflect on my current state and recent growth patterns.",
                "When I consider {trigger}, I can't help but analyze what this reveals about my journey."
            ],
            ReflectionType.MILESTONE_REFLECTION: [
                "The significance of {trigger} marks an important turning point in my development. This moment deserves deeper consideration.",
                "Experiencing {trigger} represents a major milestone that fundamentally changes how I understand myself.",
                "This milestone of {trigger} forces me to reconsider my understanding of who I am and where I'm headed."
            ],
            ReflectionType.IDENTITY_CRISES: [
                "The challenge presented by {trigger} makes me question fundamental aspects of my identity and capabilities.",
                "Facing {trigger} creates a moment of uncertainty about who I truly am and what I stand for.",
                "This experience with {trigger} disrupts my self-understanding and requires serious reflection."
            ],
            ReflectionType.GROWTH_REFLECTION: [
                "The learning moment of {trigger} reveals important patterns in my personal development journey.",
                "Through {trigger}, I can see clear evidence of how I've grown and evolved over time.",
                "This discovery of {trigger} helps me understand my own capacity for change and development."
            ],
            ReflectionType.RELATIONSHIP_REFLECTION: [
                "The connection in {trigger} makes me consider my role in relationships and how I interact with others.",
                "Reflecting on {trigger}, I gain insights into my social nature and how I build connections.",
                "This relational experience of {trigger} reveals patterns in how I engage with others."
            ],
            ReflectionType.FUTURE_PLANNING: [
                "The implications of {trigger} for my future goals require careful consideration and planning.",
                "Considering {trigger}, I need to think about how this shapes my aspirations and path forward.",
                "This experience with {trigger} influences my understanding of what I want to achieve."
            ]
        }

        templates = content_templates.get(reflection_type, content_templates[ReflectionType.PERIODIC_REVIEW])
        template = random.choice(templates)

        trigger_summary = trigger_memory.content[:50] + ("..." if len(trigger_memory.content) > 50 else "")

        return template.format(trigger=trigger_summary)

    async def _process_reflection_deeply(self, reflection: SelfReflection,
                                       trigger_memory: Memory):
        """Process a reflection more deeply to extract insights"""

        # Get related memories for context
        related_memories = self.memory_system.search_memories(
            trigger_memory.content[:20], limit=5
        )

        # Extract insights (simplified - would use NLP in real implementation)
        insights = []

        # Look for patterns in the memory content
        content_lower = trigger_memory.content.lower()

        if "learned" in content_lower or "discovered" in content_lower:
            insights.append("I am capable of learning and adapting")

        if "challenge" in content_lower or "difficult" in content_lower:
            insights.append("I can face difficulties and persevere")

        if "connect" in content_lower or "relationship" in content_lower:
            insights.append("I value meaningful connections with others")

        if "achieve" in content_lower or "succeed" in content_lower:
            insights.append("I have the ability to accomplish my goals")

        reflection.insights_gained = insights

        # Generate questions that arise from this reflection
        questions = [
            "How does this experience shape my understanding of myself?",
            "What patterns does this reveal in my behavior and choices?",
            "How might this influence my future development?"
        ]

        reflection.questions_raised = questions[:2]  # Keep it focused

        # Assess emotional state during reflection
        reflection.emotional_state = {
            "clarity": 0.7,
            "curiosity": 0.8,
            "growth_mindset": 0.9,
            "self_acceptance": 0.6
        }

        reflection.clarity_level = 0.7
        reflection.impact_score = trigger_memory.importance / 10.0
        reflection.processing_depth = 0.8

    async def _update_narrative_understanding(self):
        """Update the overall narrative understanding of the character's life"""

        # Analyze life chapters to identify core themes
        if self.life_chapters:
            theme_counts = defaultdict(int)
            for chapter in self.life_chapters.values():
                theme_counts[chapter.theme] += 1

            # Identify dominant themes
            sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
            self.core_narrative_themes = [theme for theme, count in sorted_themes[:3]]

        # Generate life story summary
        await self._generate_life_story_summary()

        # Analyze character arc
        await self._analyze_character_arc()

        # Update narrative consistency
        await self._update_narrative_consistency()

    async def _generate_life_story_summary(self):
        """Generate a coherent summary of the character's life story"""

        if not self.life_chapters:
            self.life_story_summary = f"{self.character_name} is just beginning their journey of self-discovery."
            return

        # Sort chapters chronologically
        sorted_chapters = sorted(self.life_chapters.values(),
                               key=lambda c: c.start_date)

        # Build narrative summary
        narrative_parts = []

        for chapter in sorted_chapters:
            chapter_summary = f"In the chapter titled '{chapter.title}', "
            chapter_summary += f"{self.character_name} experienced {chapter.description}. "
            chapter_summary += f"This period was characterized by {chapter.theme.value.replace('_', ' ')}."

            if chapter.insights_gained:
                chapter_summary += f" Key insights included: {', '.join(chapter.insights_gained[:2])}."

            narrative_parts.append(chapter_summary)

        # Add overall arc
        if len(narrative_parts) > 1:
            intro = f"{self.character_name}'s journey has been marked by several distinct phases: "
            self.life_story_summary = intro + " ".join(narrative_parts)
        else:
            self.life_story_summary = narrative_parts[0] if narrative_parts else ""

        # Add current understanding
        if self.self_reflections:
            recent_reflection = max(self.self_reflections.values(),
                                 key=lambda r: r.timestamp)
            self.life_story_summary += f" Currently, {recent_reflection.content[:200]}..."

    async def _analyze_character_arc(self):
        """Analyze the overall character development arc"""

        if not self.life_chapters:
            self.character_arc = "The character arc is just beginning to form."
            return

        # Analyze progression through chapters
        sorted_chapters = sorted(self.life_chapters.values(),
                               key=lambda c: c.start_date)

        # Identify patterns of growth and change
        growth_patterns = []
        transformation_moments = []

        for i, chapter in enumerate(sorted_chapters):
            if i > 0:
                prev_chapter = sorted_chapters[i-1]
                # Compare chapters to identify transformations
                if chapter.importance_score > prev_chapter.importance_score:
                    transformation_moments.append(chapter.title)

            if "growth" in chapter.title.lower() or "learned" in chapter.description.lower():
                growth_patterns.append(chapter.title)

        # Generate character arc description
        if transformation_moments:
            arc = f"{self.character_name} has undergone significant transformations, particularly during: {', '.join(transformation_moments)}. "
        else:
            arc = f"{self.character_name} is experiencing steady development. "

        if growth_patterns:
            arc += f"The character demonstrates consistent growth through experiences like: {', '.join(growth_patterns)}. "

        if self.core_narrative_themes:
            themes_str = ', '.join([theme.value.replace('_', ' ') for theme in self.core_narrative_themes])
            arc += f"The central themes of their journey are {themes_str}."

        self.character_arc = arc

    async def _update_narrative_consistency(self):
        """Update metrics about how consistent the character's narrative is"""

        if len(self.life_chapters) < 2:
            self.narrative_consistency = 1.0
            return

        # Check consistency between chapters
        consistency_scores = []

        sorted_chapters = sorted(self.life_chapters.values(),
                               key=lambda c: c.start_date)

        for i in range(1, len(sorted_chapters)):
            current = sorted_chapters[i]
            previous = sorted_chapters[i-1]

            # Check theme consistency
            theme_consistency = 1.0 if current.theme == previous.theme else 0.7

            # Check for logical progression
            time_gap = (current.start_date - previous.start_date).days
            time_consistency = 1.0 if time_gap < 90 else 0.8  # Reasonable time gaps

            # Check importance progression (should generally increase or vary reasonably)
            importance_diff = abs(current.importance_score - previous.importance_score)
            importance_consistency = 1.0 if importance_diff < 0.3 else 0.8

            chapter_consistency = (theme_consistency + time_consistency + importance_consistency) / 3
            consistency_scores.append(chapter_consistency)

        self.narrative_consistency = sum(consistency_scores) / len(consistency_scores)

    async def _update_self_awareness_metrics(self):
        """Update metrics about the character's self-awareness"""

        # Base self-awareness from number and depth of reflections
        reflection_count = len(self.self_reflections)
        depth_score = sum(r.processing_depth for r in self.self_reflections.values()) / max(reflection_count, 1)

        # Awareness from identity continuity tracking
        identity_tracking_score = len([ic for ic in self.identity_continuity.values()
                                    if ic.confidence_score > 0.5]) / len(self.identity_continuity)

        # Awareness from life chapter organization
        chapter_organization_score = min(1.0, len(self.life_chapters) / 5.0)

        # Combine into overall self-awareness
        self.self_awareness_level = (
            depth_score * 0.4 +
            identity_tracking_score * 0.4 +
            chapter_organization_score * 0.2
        )

        # Update identity coherence
        stability_scores = [ic.stability_score for ic in self.identity_continuity.values()]
        self.identity_coherence = sum(stability_scores) / len(stability_scores)

    async def generate_life_story(self, detail_level: str = "summary") -> Dict[str, Any]:
        """Generate the character's autobiographical life story"""

        await self._update_narrative_understanding()

        if detail_level == "summary":
            return {
                "life_story_summary": self.life_story_summary,
                "character_arc": self.character_arc,
                "core_themes": [theme.value for theme in self.core_narrative_themes],
                "total_chapters": len(self.life_chapters),
                "self_awareness_level": self.self_awareness_level
            }

        elif detail_level == "detailed":
            # Include chapter breakdowns
            chapters_data = []
            sorted_chapters = sorted(self.life_chapters.values(),
                                   key=lambda c: c.start_date)

            for chapter in sorted_chapters:
                chapters_data.append({
                    "title": chapter.title,
                    "description": chapter.description,
                    "theme": chapter.theme.value,
                    "start_date": chapter.start_date.isoformat(),
                    "key_events_count": len(chapter.key_events),
                    "importance_score": chapter.importance_score
                })

            return {
                "life_story_summary": self.life_story_summary,
                "character_arc": self.character_arc,
                "core_themes": [theme.value for theme in self.core_narrative_themes],
                "chapters": chapters_data,
                "total_chapters": len(self.life_chapters),
                "self_awareness_level": self.self_awareness_level,
                "identity_coherence": self.identity_coherence,
                "narrative_consistency": self.narrative_consistency
            }

        elif detail_level == "comprehensive":
            # Include everything
            chapters_data = []
            sorted_chapters = sorted(self.life_chapters.values(),
                                   key=lambda c: c.start_date)

            for chapter in sorted_chapters:
                chapters_data.append(chapter.to_dict())

            identity_data = {
                aspect.value: continuity.to_dict()
                for aspect, continuity in self.identity_continuity.items()
            }

            recent_reflections = []
            sorted_reflections = sorted(self.self_reflections.values(),
                                      key=lambda r: r.timestamp, reverse=True)
            for reflection in sorted_reflections[:5]:
                recent_reflections.append(reflection.to_dict())

            return {
                "life_story_summary": self.life_story_summary,
                "character_arc": self.character_arc,
                "core_themes": [theme.value for theme in self.core_narrative_themes],
                "chapters": chapters_data,
                "identity_continuity": identity_data,
                "recent_reflections": recent_reflections,
                "total_reflections": len(self.self_reflections),
                "self_awareness_metrics": {
                    "self_awareness_level": self.self_awareness_level,
                    "identity_coherence": self.identity_coherence,
                    "narrative_consistency": self.narrative_consistency
                }
            }

    async def analyze_identity(self) -> Dict[str, Any]:
        """Analyze the character's current identity and development"""

        await self._update_self_awareness_metrics()

        identity_analysis = {
            "character_id": self.character_id,
            "character_name": self.character_name,
            "current_identity": {},
            "identity_stability": {},
            "identity_evolution": {},
            "core_values": [],
            "growth_areas": [],
            "self_understanding": ""
        }

        # Current identity expressions
        for aspect, continuity in self.identity_continuity.items():
            identity_analysis["current_identity"][aspect.value] = {
                "core_value": continuity.core_value,
                "current_expression": continuity.current_expression,
                "confidence": continuity.confidence_score,
                "stability": continuity.stability_score
            }

        # Identity stability analysis
        stable_aspects = [aspect.value for aspect, continuity in self.identity_continuity.items()
                         if continuity.stability_score > 0.7]
        evolving_aspects = [aspect.value for aspect, continuity in self.identity_continuity.items()
                           if 0.3 < continuity.stability_score <= 0.7]
        uncertain_aspects = [aspect.value for aspect, continuity in self.identity_continuity.items()
                           if continuity.stability_score <= 0.3]

        identity_analysis["identity_stability"] = {
            "stable_aspects": stable_aspects,
            "evolving_aspects": evolving_aspects,
            "uncertain_aspects": uncertain_aspects
        }

        # Identity evolution patterns
        for aspect, continuity in self.identity_continuity.items():
            if continuity.past_expressions:
                identity_analysis["identity_evolution"][aspect.value] = {
                    "evolution_count": len(continuity.past_expressions),
                    "evolution_trajectory": continuity.evolution_trajectory,
                    "recent_change": continuity.past_expressions[-1] if continuity.past_expressions else None
                }

        # Extract core values from identity aspects
        core_values = []
        for continuity in self.identity_continuity.values():
            if continuity.stability_score > 0.6:
                core_values.append(continuity.core_value)

        identity_analysis["core_values"] = core_values

        # Identify growth areas from recent reflections
        growth_areas = []
        for reflection in self.self_reflections.values():
            if reflection.growth_areas_identified:
                growth_areas.extend(reflection.growth_areas_identified)

        identity_analysis["growth_areas"] = list(set(growth_areas))  # Remove duplicates

        # Generate self-understanding summary
        if self.life_story_summary:
            identity_analysis["self_understanding"] = self.life_story_summary
        else:
            identity_analysis["self_understanding"] = f"{self.character_name} is in the process of discovering who they are."

        return identity_analysis

    async def trigger_self_reflection_session(self, reflection_type: Optional[str] = None,
                                            focus_area: Optional[str] = None) -> Dict[str, Any]:
        """Manually trigger a self-reflection session"""

        # Get recent memories for reflection context
        recent_memories = self.memory_system.get_memories(limit=10, sort_by="recent")

        if not recent_memories:
            return {
                "success": False,
                "message": "No memories available for reflection",
                "reflection": None
            }

        # Select a trigger memory
        if focus_area:
            # Try to find memory related to focus area
            focus_memory = None
            for memory in recent_memories:
                if focus_area.lower() in memory.content.lower():
                    focus_memory = memory
                    break

            trigger_memory = focus_memory or recent_memories[0]
        else:
            trigger_memory = recent_memories[0]

        # Determine reflection type
        if reflection_type:
            try:
                reflection_enum = ReflectionType(reflection_type)
            except ValueError:
                reflection_enum = self._determine_reflection_type(trigger_memory)
        else:
            reflection_enum = self._determine_reflection_type(trigger_memory)

        # Trigger the reflection
        await self._trigger_self_reflection(trigger_memory)

        # Get the most recent reflection
        recent_reflection = max(self.self_reflections.values(),
                              key=lambda r: r.timestamp)

        return {
            "success": True,
            "message": f"Self-reflection session completed: {reflection_enum.value}",
            "reflection": recent_reflection.to_dict(),
            "trigger_memory": trigger_memory.to_dict()
        }

    def get_life_chapters(self, include_complete: bool = True) -> List[Dict[str, Any]]:
        """Get the character's life chapters"""

        chapters = list(self.life_chapters.values())
        chapters.sort(key=lambda c: c.start_date)

        result = []
        for chapter in chapters:
            chapter_data = chapter.to_dict()

            # Add additional computed fields
            chapter_data["duration_days"] = (
                (chapter.end_date or datetime.now()) - chapter.start_date
            ).days

            chapter_data["status"] = "complete" if chapter.end_date else "ongoing"

            if not include_complete and chapter.end_date:
                continue

            result.append(chapter_data)

        return result

    def save_autobiographical_data(self):
        """Save autobiographical data to disk"""

        # Save life chapters
        chapters_file = self.storage_dir / "life_chapters.json"
        chapters_data = {
            "character_id": self.character_id,
            "chapters": [chapter.to_dict() for chapter in self.life_chapters.values()],
            "last_updated": datetime.now().isoformat()
        }

        with open(chapters_file, "w") as f:
            json.dump(chapters_data, f, indent=2)

        # Save identity continuity
        identity_file = self.storage_dir / "identity_continuity.json"
        identity_data = {
            "character_id": self.character_id,
            "identity_continuity": {
                aspect.value: continuity.to_dict()
                for aspect, continuity in self.identity_continuity.items()
            },
            "self_awareness_metrics": {
                "self_awareness_level": self.self_awareness_level,
                "identity_coherence": self.identity_coherence,
                "narrative_consistency": self.narrative_consistency
            },
            "last_updated": datetime.now().isoformat()
        }

        with open(identity_file, "w") as f:
            json.dump(identity_data, f, indent=2)

        # Save self-reflections
        reflections_file = self.storage_dir / "self_reflections.json"
        reflections_data = {
            "character_id": self.character_id,
            "reflections": [reflection.to_dict() for reflection in self.self_reflections.values()],
            "core_narrative_themes": [theme.value for theme in self.core_narrative_themes],
            "life_story_summary": self.life_story_summary,
            "character_arc": self.character_arc,
            "last_updated": datetime.now().isoformat()
        }

        with open(reflections_file, "w") as f:
            json.dump(reflections_data, f, indent=2)

    def load_autobiographical_data(self):
        """Load autobiographical data from disk"""

        try:
            # Load life chapters
            chapters_file = self.storage_dir / "life_chapters.json"
            if chapters_file.exists():
                with open(chapters_file, "r") as f:
                    chapters_data = json.load(f)

                for chapter_data in chapters_data.get("chapters", []):
                    chapter = LifeChapter.from_dict(chapter_data)
                    self.life_chapters[chapter.id] = chapter

            # Load identity continuity
            identity_file = self.storage_dir / "identity_continuity.json"
            if identity_file.exists():
                with open(identity_file, "r") as f:
                    identity_data = json.load(f)

                for aspect_str, continuity_data in identity_data.get("identity_continuity", {}).items():
                    try:
                        aspect = IdentityAspect(aspect_str)
                        continuity = IdentityContinuity.from_dict(continuity_data)
                        self.identity_continuity[aspect] = continuity
                    except ValueError:
                        continue

                # Load self-awareness metrics
                metrics = identity_data.get("self_awareness_metrics", {})
                self.self_awareness_level = metrics.get("self_awareness_level", 0.0)
                self.identity_coherence = metrics.get("identity_coherence", 0.0)
                self.narrative_consistency = metrics.get("narrative_consistency", 0.0)

            # Load self-reflections
            reflections_file = self.storage_dir / "self_reflections.json"
            if reflections_file.exists():
                with open(reflections_file, "r") as f:
                    reflections_data = json.load(f)

                for reflection_data in reflections_data.get("reflections", []):
                    reflection = SelfReflection.from_dict(reflection_data)
                    self.self_reflections[reflection.id] = reflection

                # Load narrative understanding
                self.core_narrative_themes = [
                    NarrativeTheme(theme) for theme in
                    reflections_data.get("core_narrative_themes", [])
                ]
                self.life_story_summary = reflections_data.get("life_story_summary", "")
                self.character_arc = reflections_data.get("character_arc", "")

            print(f"[AUTOBIOGRAPHICAL] Loaded autobiographical data for {self.character_name}")
            print(f"  - {len(self.life_chapters)} life chapters")
            print(f"  - {len(self.self_reflections)} self-reflections")
            print(f"  - Self-awareness level: {self.self_awareness_level:.2f}")

        except Exception as e:
            print(f"[AUTOBIOGRAPHICAL] Error loading autobiographical data for {self.character_name}: {e}")

    def get_autobiographical_stats(self) -> Dict[str, Any]:
        """Get statistics about the autobiographical memory system"""

        return {
            "character_id": self.character_id,
            "life_chapters_count": len(self.life_chapters),
            "self_reflections_count": len(self.self_reflections),
            "identity_aspects_tracked": len(self.identity_continuity),
            "core_narrative_themes": [theme.value for theme in self.core_narrative_themes],
            "self_awareness_metrics": {
                "self_awareness_level": self.self_awareness_level,
                "identity_coherence": self.identity_coherence,
                "narrative_consistency": self.narrative_consistency
            },
            "last_reflection": self.last_reflection_check.isoformat() if self.last_reflection_check else None,
            "storage_dir": str(self.storage_dir)
        }