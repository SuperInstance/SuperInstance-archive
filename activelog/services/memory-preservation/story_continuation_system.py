"""
Story Continuation Across Generations System

This module provides comprehensive story continuation and narrative inheritance
tracking across generations, including story evolution, character development,
theme preservation, and multi-generational narrative analysis.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime, date
import uuid
import numpy as np
from collections import defaultdict

class StoryType(Enum):
    """Types of stories"""
    FAMILY_LEGEND = "family_legend"
    PERSONAL_MEMOIR = "personal_memoir"
    ORIGIN_STORY = "origin_story"
    CAUTIONARY_TALE = "cautionary_tale"
    HEROIC_JOURNEY = "heroic_journey"
    LOVE_STORY = "love_story"
    ADVENTURE = "adventure"
    FOLKLORE = "folklore"
    HISTORICAL_ACCOUNT = "historical_account"
    MORAL_TEACHING = "moral_teaching"
    CULTURAL_MYTH = "cultural_myth"
    COMING_OF_AGE = "coming_of_age"

class NarrativeTheme(Enum):
    """Common narrative themes"""
    PERSEVERANCE = "perseverance"
    LOVE = "love"
    SACRIFICE = "sacrifice"
    REDEMPTION = "redemption"
    COURAGE = "courage"
    WISDOM = "wisdom"
    FAMILY_BONDS = "family_bonds"
    TRADITION = "tradition"
    CHANGE = "change"
    LOSS = "loss"
    DISCOVERY = "discovery"
    JUSTICE = "justice"
    IDENTITY = "identity"
    SURVIVAL = "survival"

class ContinuationType(Enum):
    """Types of story continuation"""
    DIRECT_SEQUEL = "direct_sequel"
    PARALLEL_STORY = "parallel_story"
    PREQUEL = "prequel"
    ADAPTATION = "adaptation"
    RETELLING = "retelling"
    EXPANSION = "expansion"
    MODERNIZATION = "modernization"
    PERSPECTIVE_SHIFT = "perspective_shift"

class StoryMedium(Enum):
    """Medium of story telling"""
    ORAL = "oral"
    WRITTEN = "written"
    VISUAL = "visual"
    AUDIO = "audio"
    VIDEO = "video"
    DIGITAL = "digital"
    PERFORMANCE = "performance"
    MIXED_MEDIA = "mixed_media"

@dataclass
class Character:
    """Story character with traits and development"""
    character_id: str
    name: str
    role: str  # protagonist, antagonist, mentor, etc.
    traits: List[str]
    relationships: Dict[str, str]  # character_id -> relationship_type
    character_arc: Optional[str] = None
    symbolic_meaning: Optional[str] = None
    historical_basis: Optional[str] = None
    cultural_significance: Optional[str] = None

@dataclass
class StoryElement:
    """Core story elements"""
    plot_points: List[str]
    setting: Dict[str, Any]  # time, place, context
    themes: List[NarrativeTheme]
    moral_lessons: List[str]
    cultural_context: List[str]
    symbolic_elements: List[str]
    emotional_beats: List[str]
    conflict_types: List[str]

@dataclass
class StoryVersion:
    """A specific version of a story"""
    version_id: str
    story_title: str
    story_type: StoryType
    narrator_name: str
    narrator_generation: int
    telling_date: date
    audience: List[str]  # who was told this story
    medium: StoryMedium
    content: str
    characters: List[Character]
    story_elements: StoryElement
    duration: Optional[str] = None  # length of telling
    context: Optional[str] = None  # occasion, setting
    variations_from_previous: List[str] = field(default_factory=list)
    additions: List[str] = field(default_factory=list)
    omissions: List[str] = field(default_factory=list)
    embellishments: List[str] = field(default_factory=list)
    source_version_id: Optional[str] = None
    cultural_adaptations: List[str] = field(default_factory=list)
    language_used: str = "english"
    preservation_quality: float = 1.0  # 0-1 scale
    multimedia_attachments: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class StoryContinuation:
    """Tracks continuation between story versions"""
    continuation_id: str
    original_version_id: str
    continued_version_id: str
    continuation_type: ContinuationType
    continuation_date: date
    continuator_name: str
    continuator_relationship: str  # to original narrator
    time_gap: int  # years between versions
    changes_made: List[str]
    reasons_for_changes: List[str]
    preservation_fidelity: float  # 0-1 how faithful to original
    innovation_level: float  # 0-1 how much new content added
    cultural_shift_indicators: List[str]
    language_evolution: List[str]
    theme_evolution: Dict[str, str]  # old_theme -> new_theme

@dataclass
class StoryLineage:
    """Tracks complete lineage of a story across generations"""
    lineage_id: str
    story_family_name: str
    origin_version_id: str
    current_generation: int
    version_timeline: List[str]  # version IDs in chronological order
    continuation_chain: List[str]  # continuation IDs
    family_branches: Dict[str, List[str]]  # different family lines
    character_evolution: Dict[str, List[Dict[str, Any]]]  # character -> evolution stages
    theme_persistence: Dict[NarrativeTheme, float]  # theme -> persistence score
    cultural_adaptations: List[Dict[str, Any]]
    geographic_spread: List[str]
    language_variations: List[str]
    time_span: Tuple[date, date]
    preservation_status: str  # active, declining, lost, revived
    core_message_stability: float  # 0-1 how stable the core message is
    narrative_complexity_evolution: List[float]  # complexity over time

@dataclass
class StoryCollection:
    """Collection of related stories"""
    collection_id: str
    collection_name: str
    story_lineages: List[str]  # lineage IDs
    common_themes: List[NarrativeTheme]
    cultural_group: str
    story_cycle_type: str  # epic, saga, folklore collection
    interconnections: Dict[str, List[str]]  # story -> related stories
    collective_significance: str
    preservation_priority: str

class NarrativeAnalyzer:
    """Analyzes narrative structure and themes"""
    
    def __init__(self):
        self.theme_keywords = {
            NarrativeTheme.PERSEVERANCE: ["persevere", "endure", "overcome", "struggle", "persist"],
            NarrativeTheme.LOVE: ["love", "devotion", "romance", "affection", "bond"],
            NarrativeTheme.SACRIFICE: ["sacrifice", "give up", "selfless", "sacrifice for"],
            NarrativeTheme.COURAGE: ["brave", "courage", "fearless", "bold", "heroic"],
            NarrativeTheme.WISDOM: ["wise", "learned", "knowledge", "understanding", "insight"],
            NarrativeTheme.FAMILY_BONDS: ["family", "blood", "kinship", "relatives", "heritage"],
            NarrativeTheme.TRADITION: ["tradition", "custom", "heritage", "legacy", "passed down"],
            NarrativeTheme.CHANGE: ["change", "transformation", "evolution", "adaptation", "growth"],
            NarrativeTheme.LOSS: ["loss", "grief", "death", "gone", "departed", "mourning"],
            NarrativeTheme.DISCOVERY: ["discover", "find", "learn", "realize", "uncover"],
        }
        
        self.character_archetypes = {
            "hero": ["protagonist", "champion", "leader", "savior"],
            "mentor": ["teacher", "guide", "wise one", "elder"],
            "villain": ["antagonist", "enemy", "evil", "opponent"],
            "trickster": ["clever", "cunning", "mischievous", "sly"],
            "innocent": ["pure", "naive", "young", "inexperienced"],
            "explorer": ["adventurer", "seeker", "wanderer", "pioneer"]
        }
    
    async def analyze_story_themes(self, content: str) -> List[Tuple[NarrativeTheme, float]]:
        """Analyze themes present in story content"""
        content_lower = content.lower()
        theme_scores = []
        
        for theme, keywords in self.theme_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > 0:
                # Normalize by content length and keyword count
                normalized_score = min(score / (len(keywords) * 0.5), 1.0)
                theme_scores.append((theme, normalized_score))
        
        return sorted(theme_scores, key=lambda x: x[1], reverse=True)
    
    async def identify_character_archetypes(self, characters: List[Character]) -> Dict[str, str]:
        """Identify character archetypes"""
        character_archetypes = {}
        
        for character in characters:
            best_archetype = None
            best_score = 0
            
            character_text = f"{character.role} {' '.join(character.traits)}".lower()
            
            for archetype, keywords in self.character_archetypes.items():
                score = sum(1 for keyword in keywords if keyword in character_text)
                if score > best_score:
                    best_score = score
                    best_archetype = archetype
            
            if best_archetype:
                character_archetypes[character.character_id] = best_archetype
            else:
                character_archetypes[character.character_id] = "supporting"
        
        return character_archetypes
    
    async def analyze_narrative_structure(self, content: str) -> Dict[str, Any]:
        """Analyze narrative structure elements"""
        sentences = content.split('.')
        structure_analysis = {
            'story_length': len(sentences),
            'complexity_score': 0.0,
            'dialogue_ratio': 0.0,
            'descriptive_ratio': 0.0,
            'action_ratio': 0.0,
            'emotional_intensity': 0.0
        }
        
        dialogue_indicators = ['"', "'", "said", "asked", "replied", "spoke"]
        action_indicators = ["ran", "jumped", "fought", "moved", "went", "came"]
        descriptive_indicators = ["was", "were", "looked", "seemed", "appeared"]
        emotional_indicators = ["felt", "emotion", "happy", "sad", "angry", "excited", "afraid"]
        
        dialogue_count = sum(1 for sentence in sentences 
                           if any(indicator in sentence.lower() for indicator in dialogue_indicators))
        action_count = sum(1 for sentence in sentences 
                         if any(indicator in sentence.lower() for indicator in action_indicators))
        descriptive_count = sum(1 for sentence in sentences 
                              if any(indicator in sentence.lower() for indicator in descriptive_indicators))
        emotional_count = sum(1 for sentence in sentences 
                            if any(indicator in sentence.lower() for indicator in emotional_indicators))
        
        if sentences:
            structure_analysis['dialogue_ratio'] = dialogue_count / len(sentences)
            structure_analysis['action_ratio'] = action_count / len(sentences)
            structure_analysis['descriptive_ratio'] = descriptive_count / len(sentences)
            structure_analysis['emotional_intensity'] = emotional_count / len(sentences)
            
            # Complexity based on variety of narrative elements
            element_variety = len([r for r in [
                structure_analysis['dialogue_ratio'],
                structure_analysis['action_ratio'],
                structure_analysis['descriptive_ratio'],
                structure_analysis['emotional_intensity']
            ] if r > 0.1])
            
            structure_analysis['complexity_score'] = element_variety / 4.0
        
        return structure_analysis
    
    async def extract_moral_lessons(self, content: str) -> List[str]:
        """Extract moral lessons from story content"""
        lesson_indicators = [
            "learned that", "taught me", "showed that", "realized that",
            "moral of", "lesson is", "wisdom of", "understood that"
        ]
        
        lessons = []
        sentences = content.split('.')
        
        for sentence in sentences:
            sentence_lower = sentence.lower().strip()
            for indicator in lesson_indicators:
                if indicator in sentence_lower:
                    # Extract the lesson part
                    lesson_start = sentence_lower.find(indicator) + len(indicator)
                    lesson = sentence[lesson_start:].strip()
                    if lesson and len(lesson) > 10:  # Substantial lesson
                        lessons.append(lesson)
                    break
        
        # If no explicit lessons found, infer from themes
        if not lessons:
            themes = await self.analyze_story_themes(content)
            for theme, score in themes[:2]:  # Top 2 themes
                if score > 0.3:
                    lesson = self._theme_to_lesson(theme)
                    if lesson:
                        lessons.append(lesson)
        
        return lessons[:5]  # Limit to 5 lessons
    
    def _theme_to_lesson(self, theme: NarrativeTheme) -> Optional[str]:
        """Convert theme to implicit lesson"""
        theme_lessons = {
            NarrativeTheme.PERSEVERANCE: "Never give up in the face of adversity",
            NarrativeTheme.LOVE: "Love conquers all obstacles",
            NarrativeTheme.SACRIFICE: "Sometimes we must sacrifice for others",
            NarrativeTheme.COURAGE: "Courage is needed to overcome fear",
            NarrativeTheme.WISDOM: "Wisdom comes from experience and reflection",
            NarrativeTheme.FAMILY_BONDS: "Family bonds are precious and enduring",
            NarrativeTheme.TRADITION: "Traditions connect us to our heritage",
            NarrativeTheme.CHANGE: "Change is inevitable and can be positive"
        }
        
        return theme_lessons.get(theme)

class StoryContinuationSystem:
    """Main system for tracking story continuation across generations"""
    
    def __init__(self):
        self.story_versions: Dict[str, StoryVersion] = {}
        self.story_continuations: Dict[str, StoryContinuation] = {}
        self.story_lineages: Dict[str, StoryLineage] = {}
        self.story_collections: Dict[str, StoryCollection] = {}
        self.narrator_network: Dict[str, Set[str]] = defaultdict(set)
        self.narrative_analyzer = NarrativeAnalyzer()
        
    async def add_story_version(self, story_version: StoryVersion) -> Dict[str, Any]:
        """Add new story version and analyze relationships"""
        self.story_versions[story_version.version_id] = story_version
        
        # Update narrator network
        self.narrator_network[story_version.narrator_name].update(story_version.audience)
        
        # Analyze story content
        narrative_analysis = await self.narrative_analyzer.analyze_narrative_structure(story_version.content)
        story_version.story_elements.emotional_beats = [f"intensity_{narrative_analysis['emotional_intensity']:.2f}"]
        
        # Extract themes if not provided
        if not story_version.story_elements.themes:
            themes = await self.narrative_analyzer.analyze_story_themes(story_version.content)
            story_version.story_elements.themes = [theme for theme, score in themes if score > 0.3]
        
        # Extract moral lessons if not provided
        if not story_version.story_elements.moral_lessons:
            story_version.story_elements.moral_lessons = await self.narrative_analyzer.extract_moral_lessons(story_version.content)
        
        # Check for lineage connections
        lineage_updates = await self._analyze_lineage_connections(story_version)
        
        return {
            'success': True,
            'version_id': story_version.version_id,
            'lineage_updates': lineage_updates,
            'themes_identified': len(story_version.story_elements.themes),
            'lessons_extracted': len(story_version.story_elements.moral_lessons),
            'narrative_complexity': narrative_analysis['complexity_score']
        }
    
    async def document_story_continuation(self, continuation: StoryContinuation) -> Dict[str, Any]:
        """Document continuation between story versions"""
        self.story_continuations[continuation.continuation_id] = continuation
        
        # Update or create lineage
        lineage_result = await self._update_story_lineage(continuation)
        
        # Analyze continuation patterns
        continuation_analysis = await self._analyze_continuation_patterns(continuation)
        
        return {
            'success': True,
            'continuation_id': continuation.continuation_id,
            'lineage_updated': lineage_result['success'],
            'lineage_id': lineage_result.get('lineage_id'),
            'fidelity_score': continuation.preservation_fidelity,
            'innovation_score': continuation.innovation_level,
            'continuation_analysis': continuation_analysis
        }
    
    async def trace_story_lineage(self, story_title: str) -> List[StoryLineage]:
        """Trace complete lineage of a story family"""
        matching_lineages = []
        
        for lineage in self.story_lineages.values():
            if story_title.lower() in lineage.story_family_name.lower():
                matching_lineages.append(lineage)
        
        # Sort by preservation status and generation count
        status_priority = {'active': 4, 'declining': 3, 'revived': 2, 'lost': 1}
        matching_lineages.sort(
            key=lambda x: (status_priority.get(x.preservation_status, 0), x.current_generation),
            reverse=True
        )
        
        return matching_lineages
    
    async def analyze_theme_evolution(self, lineage_id: str) -> Dict[str, Any]:
        """Analyze how themes evolve across story versions"""
        if lineage_id not in self.story_lineages:
            return {'error': 'Lineage not found'}
        
        lineage = self.story_lineages[lineage_id]
        theme_evolution = {}
        
        # Track themes across versions
        for version_id in lineage.version_timeline:
            if version_id in self.story_versions:
                version = self.story_versions[version_id]
                for theme in version.story_elements.themes:
                    if theme not in theme_evolution:
                        theme_evolution[theme] = {
                            'first_appearance': version.telling_date,
                            'appearances': [],
                            'strength_over_time': [],
                            'cultural_contexts': set()
                        }
                    
                    theme_evolution[theme]['appearances'].append({
                        'version_id': version_id,
                        'date': version.telling_date,
                        'narrator': version.narrator_name,
                        'generation': version.narrator_generation
                    })
                    
                    # Analyze theme strength (simplified)
                    theme_analysis = await self.narrative_analyzer.analyze_story_themes(version.content)
                    theme_strength = next((score for t, score in theme_analysis if t == theme), 0.0)
                    theme_evolution[theme]['strength_over_time'].append(theme_strength)
                    
                    theme_evolution[theme]['cultural_contexts'].update(version.story_elements.cultural_context)
        
        # Calculate theme persistence and evolution patterns
        theme_analysis = {}
        for theme, data in theme_evolution.items():
            appearances = len(data['appearances'])
            total_versions = len(lineage.version_timeline)
            persistence = appearances / total_versions if total_versions > 0 else 0.0
            
            strength_trend = "stable"
            if len(data['strength_over_time']) > 1:
                first_strength = data['strength_over_time'][0]
                last_strength = data['strength_over_time'][-1]
                if last_strength > first_strength * 1.2:
                    strength_trend = "strengthening"
                elif last_strength < first_strength * 0.8:
                    strength_trend = "weakening"
            
            theme_analysis[theme.value] = {
                'persistence_score': persistence,
                'total_appearances': appearances,
                'strength_trend': strength_trend,
                'first_appearance': data['first_appearance'].isoformat(),
                'cultural_contexts': list(data['cultural_contexts']),
                'generational_span': max(app['generation'] for app in data['appearances']) - 
                                   min(app['generation'] for app in data['appearances']) if data['appearances'] else 0
            }
        
        return {
            'lineage_id': lineage_id,
            'story_family': lineage.story_family_name,
            'theme_evolution': theme_analysis,
            'dominant_themes': sorted(theme_analysis.keys(), 
                                    key=lambda t: theme_analysis[t]['persistence_score'], 
                                    reverse=True)[:5],
            'theme_stability_score': np.mean([data['persistence_score'] for data in theme_analysis.values()]) if theme_analysis else 0.0
        }
    
    async def generate_continuation_predictions(self, version_id: str) -> List[Dict[str, Any]]:
        """Predict potential story continuations"""
        if version_id not in self.story_versions:
            return []
        
        story = self.story_versions[version_id]
        predictions = []
        
        # Predict direct sequel
        if story.story_type in [StoryType.ADVENTURE, StoryType.HEROIC_JOURNEY]:
            predictions.append({
                'continuation_type': ContinuationType.DIRECT_SEQUEL.value,
                'probability': 0.7,
                'suggested_focus': 'Continue the adventure with new challenges',
                'potential_themes': ['growth', 'new_challenges', 'expanded_world'],
                'recommended_narrator': 'next_generation',
                'estimated_time_gap': '10-20 years'
            })
        
        # Predict perspective shift
        if len(story.characters) > 1:
            secondary_characters = [c for c in story.characters if c.role != 'protagonist']
            if secondary_characters:
                predictions.append({
                    'continuation_type': ContinuationType.PERSPECTIVE_SHIFT.value,
                    'probability': 0.6,
                    'suggested_focus': f'Tell story from {secondary_characters[0].name}\'s perspective',
                    'potential_themes': ['different_viewpoint', 'hidden_story', 'parallel_experience'],
                    'recommended_narrator': 'same_generation',
                    'character_focus': secondary_characters[0].name
                })
        
        # Predict modernization
        time_since_creation = (date.today() - story.telling_date).days / 365.25
        if time_since_creation > 20:
            predictions.append({
                'continuation_type': ContinuationType.MODERNIZATION.value,
                'probability': 0.5,
                'suggested_focus': 'Update story for modern context while preserving core themes',
                'potential_themes': story.story_elements.themes,
                'recommended_narrator': 'current_generation',
                'modernization_aspects': ['technology', 'social_context', 'language_updates']
            })
        
        # Predict prequel
        if story.characters and any('mysterious past' in c.traits for c in story.characters):
            predictions.append({
                'continuation_type': ContinuationType.PREQUEL.value,
                'probability': 0.4,
                'suggested_focus': 'Explore character backgrounds and origins',
                'potential_themes': ['origins', 'formative_events', 'history'],
                'recommended_narrator': 'knowledgeable_elder'
            })
        
        return sorted(predictions, key=lambda x: x['probability'], reverse=True)
    
    async def assess_story_preservation_risk(self, lineage_id: str) -> Dict[str, Any]:
        """Assess risk factors for story preservation"""
        if lineage_id not in self.story_lineages:
            return {'error': 'Lineage not found'}
        
        lineage = self.story_lineages[lineage_id]
        risk_factors = []
        risk_level = "low"
        
        # Check recent activity
        latest_version_date = max(self.story_versions[vid].telling_date 
                                 for vid in lineage.version_timeline 
                                 if vid in self.story_versions)
        
        years_since_last_telling = (date.today() - latest_version_date).days / 365.25
        
        if years_since_last_telling > 20:
            risk_factors.append("No new versions in over 20 years")
            risk_level = "high"
        elif years_since_last_telling > 10:
            risk_factors.append("No new versions in over 10 years")
            risk_level = "medium"
        
        # Check narrator diversity
        narrators = set(self.story_versions[vid].narrator_name 
                       for vid in lineage.version_timeline 
                       if vid in self.story_versions)
        
        if len(narrators) < 2:
            risk_factors.append("Limited to single narrator family line")
            if risk_level == "low":
                risk_level = "medium"
        
        # Check preservation quality
        avg_quality = np.mean([self.story_versions[vid].preservation_quality 
                              for vid in lineage.version_timeline 
                              if vid in self.story_versions])
        
        if avg_quality < 0.5:
            risk_factors.append("Low preservation quality of existing versions")
            risk_level = "high"
        
        # Check theme stability
        if lineage.core_message_stability < 0.5:
            risk_factors.append("Core message becoming unstable")
            if risk_level != "high":
                risk_level = "medium"
        
        # Check cultural continuity
        recent_versions = [vid for vid in lineage.version_timeline[-3:] if vid in self.story_versions]
        if recent_versions:
            cultural_consistency = len(set(
                ctx for vid in recent_versions 
                for ctx in self.story_versions[vid].story_elements.cultural_context
            ))
            
            if cultural_consistency > 5:  # Too much cultural drift
                risk_factors.append("Excessive cultural drift in recent versions")
                if risk_level == "low":
                    risk_level = "medium"
        
        return {
            'lineage_id': lineage_id,
            'story_family': lineage.story_family_name,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'years_since_last_telling': years_since_last_telling,
            'narrator_diversity': len(narrators),
            'preservation_quality': avg_quality,
            'core_message_stability': lineage.core_message_stability,
            'recommendations': await self._generate_preservation_recommendations(lineage, risk_level, risk_factors)
        }
    
    async def generate_story_continuation_report(self, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive story continuation report"""
        if collection_id:
            collections = [self.story_collections[collection_id]] if collection_id in self.story_collections else []
        else:
            collections = list(self.story_collections.values())
        
        report = {
            'total_story_lineages': len(self.story_lineages),
            'active_lineages': 0,
            'at_risk_lineages': 0,
            'lost_lineages': 0,
            'average_generations': 0.0,
            'theme_persistence_analysis': {},
            'continuation_patterns': {},
            'preservation_recommendations': [],
            'narrator_network_analysis': {}
        }
        
        # Analyze lineage health
        lineage_generations = []
        for lineage in self.story_lineages.values():
            lineage_generations.append(lineage.current_generation)
            
            if lineage.preservation_status == 'active':
                report['active_lineages'] += 1
            elif lineage.preservation_status in ['at_risk', 'declining']:
                report['at_risk_lineages'] += 1
            elif lineage.preservation_status == 'lost':
                report['lost_lineages'] += 1
        
        if lineage_generations:
            report['average_generations'] = np.mean(lineage_generations)
        
        # Analyze continuation patterns
        continuation_types = defaultdict(int)
        for continuation in self.story_continuations.values():
            continuation_types[continuation.continuation_type.value] += 1
        
        report['continuation_patterns'] = dict(continuation_types)
        
        # Analyze theme persistence across all lineages
        all_theme_persistence = defaultdict(list)
        for lineage in self.story_lineages.values():
            for theme, persistence in lineage.theme_persistence.items():
                all_theme_persistence[theme.value].append(persistence)
        
        report['theme_persistence_analysis'] = {
            theme: {
                'average_persistence': np.mean(scores),
                'lineages_with_theme': len(scores),
                'stability_rating': 'high' if np.mean(scores) > 0.7 else 'medium' if np.mean(scores) > 0.4 else 'low'
            }
            for theme, scores in all_theme_persistence.items()
        }
        
        # Narrator network analysis
        network_size = len(self.narrator_network)
        avg_connections = np.mean([len(connections) for connections in self.narrator_network.values()]) if network_size > 0 else 0
        
        report['narrator_network_analysis'] = {
            'total_narrators': network_size,
            'average_audience_size': avg_connections,
            'most_connected_narrators': sorted(
                [(narrator, len(connections)) for narrator, connections in self.narrator_network.items()],
                key=lambda x: x[1], reverse=True
            )[:5]
        }
        
        return report
    
    async def _analyze_lineage_connections(self, story_version: StoryVersion) -> List[str]:
        """Analyze potential lineage connections for new story"""
        connections = []
        
        # Look for similar story titles
        for existing_version in self.story_versions.values():
            if (existing_version.version_id != story_version.version_id and
                self._calculate_title_similarity(story_version.story_title, existing_version.story_title) > 0.7):
                
                # Find lineage for existing version
                lineage = await self._find_lineage_by_version(existing_version.version_id)
                if lineage:
                    # Add to existing lineage
                    if story_version.version_id not in lineage.version_timeline:
                        lineage.version_timeline.append(story_version.version_id)
                        lineage.current_generation += 1
                        connections.append(lineage.lineage_id)
                else:
                    # Create new lineage
                    new_lineage = await self._create_new_lineage(existing_version, story_version)
                    connections.append(new_lineage.lineage_id)
        
        # If no connections found and has source version, create lineage
        if not connections and story_version.source_version_id:
            source_version = self.story_versions.get(story_version.source_version_id)
            if source_version:
                lineage = await self._find_lineage_by_version(story_version.source_version_id)
                if lineage:
                    lineage.version_timeline.append(story_version.version_id)
                    lineage.current_generation += 1
                    connections.append(lineage.lineage_id)
                else:
                    new_lineage = await self._create_new_lineage(source_version, story_version)
                    connections.append(new_lineage.lineage_id)
        
        return connections
    
    async def _update_story_lineage(self, continuation: StoryContinuation) -> Dict[str, Any]:
        """Update story lineage with new continuation"""
        # Find or create lineage
        original_version = self.story_versions.get(continuation.original_version_id)
        continued_version = self.story_versions.get(continuation.continued_version_id)
        
        if not original_version or not continued_version:
            return {'success': False, 'error': 'Version not found'}
        
        lineage = await self._find_lineage_by_version(continuation.original_version_id)
        
        if lineage:
            # Add to existing lineage
            if continuation.continued_version_id not in lineage.version_timeline:
                lineage.version_timeline.append(continuation.continued_version_id)
                lineage.continuation_chain.append(continuation.continuation_id)
                lineage.current_generation += 1
            
            # Update lineage metrics
            await self._update_lineage_metrics(lineage, continuation)
            
            return {'success': True, 'lineage_id': lineage.lineage_id}
        else:
            # Create new lineage
            new_lineage = await self._create_new_lineage(original_version, continued_version, continuation)
            return {'success': True, 'lineage_id': new_lineage.lineage_id}
    
    async def _create_new_lineage(self, original: StoryVersion, continued: StoryVersion,
                                continuation: Optional[StoryContinuation] = None) -> StoryLineage:
        """Create new story lineage"""
        lineage_id = f"lineage_{uuid.uuid4().hex}"
        
        # Calculate initial theme persistence
        theme_persistence = {}
        original_themes = set(original.story_elements.themes)
        continued_themes = set(continued.story_elements.themes)
        
        all_themes = original_themes.union(continued_themes)
        for theme in all_themes:
            appearances = 0
            if theme in original_themes:
                appearances += 1
            if theme in continued_themes:
                appearances += 1
            theme_persistence[theme] = appearances / 2.0
        
        lineage = StoryLineage(
            lineage_id=lineage_id,
            story_family_name=original.story_title,
            origin_version_id=original.version_id,
            current_generation=2,
            version_timeline=[original.version_id, continued.version_id],
            continuation_chain=[continuation.continuation_id] if continuation else [],
            family_branches={},
            character_evolution={},
            theme_persistence=theme_persistence,
            cultural_adaptations=[],
            geographic_spread=[],
            language_variations=[original.language_used, continued.language_used],
            time_span=(original.telling_date, continued.telling_date),
            preservation_status="active",
            core_message_stability=0.8,  # Initial assumption
            narrative_complexity_evolution=[]
        )
        
        self.story_lineages[lineage_id] = lineage
        return lineage
    
    async def _find_lineage_by_version(self, version_id: str) -> Optional[StoryLineage]:
        """Find lineage containing specific version"""
        for lineage in self.story_lineages.values():
            if version_id in lineage.version_timeline:
                return lineage
        return None
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between story titles"""
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _analyze_continuation_patterns(self, continuation: StoryContinuation) -> Dict[str, Any]:
        """Analyze patterns in story continuation"""
        return {
            'continuation_type': continuation.continuation_type.value,
            'time_gap_category': self._categorize_time_gap(continuation.time_gap),
            'fidelity_level': self._categorize_fidelity(continuation.preservation_fidelity),
            'innovation_level': self._categorize_innovation(continuation.innovation_level),
            'cultural_shift_detected': len(continuation.cultural_shift_indicators) > 0,
            'language_evolution_detected': len(continuation.language_evolution) > 0
        }
    
    def _categorize_time_gap(self, years: int) -> str:
        """Categorize time gap between story versions"""
        if years <= 5:
            return "immediate"
        elif years <= 15:
            return "generational"
        elif years <= 30:
            return "multigenerational"
        else:
            return "historical"
    
    def _categorize_fidelity(self, fidelity: float) -> str:
        """Categorize preservation fidelity level"""
        if fidelity >= 0.8:
            return "high_fidelity"
        elif fidelity >= 0.6:
            return "moderate_fidelity"
        elif fidelity >= 0.4:
            return "low_fidelity"
        else:
            return "loose_adaptation"
    
    def _categorize_innovation(self, innovation: float) -> str:
        """Categorize innovation level"""
        if innovation >= 0.8:
            return "highly_innovative"
        elif innovation >= 0.6:
            return "moderately_innovative"
        elif innovation >= 0.4:
            return "slightly_innovative"
        else:
            return "conservative"
    
    async def _update_lineage_metrics(self, lineage: StoryLineage, continuation: StoryContinuation):
        """Update lineage metrics based on new continuation"""
        # Update theme persistence
        continued_version = self.story_versions.get(continuation.continued_version_id)
        if continued_version:
            continued_themes = set(continued_version.story_elements.themes)
            
            # Adjust theme persistence scores
            for theme in lineage.theme_persistence:
                if theme in continued_themes:
                    lineage.theme_persistence[theme] = min(1.0, lineage.theme_persistence[theme] + 0.1)
                else:
                    lineage.theme_persistence[theme] = max(0.0, lineage.theme_persistence[theme] - 0.1)
            
            # Add new themes
            for theme in continued_themes:
                if theme not in lineage.theme_persistence:
                    lineage.theme_persistence[theme] = 0.3  # Initial score for new theme
        
        # Update core message stability
        stability_change = continuation.preservation_fidelity - 0.5  # Neutral point
        lineage.core_message_stability = max(0.0, min(1.0, lineage.core_message_stability + stability_change * 0.1))
        
        # Update preservation status
        if continuation.preservation_fidelity > 0.7 and continuation.innovation_level > 0.3:
            lineage.preservation_status = "active"
        elif continuation.preservation_fidelity > 0.5:
            lineage.preservation_status = "stable"
        elif continuation.preservation_fidelity > 0.3:
            lineage.preservation_status = "declining"
        else:
            lineage.preservation_status = "at_risk"
    
    async def _generate_preservation_recommendations(self, lineage: StoryLineage, 
                                                   risk_level: str, risk_factors: List[str]) -> List[str]:
        """Generate recommendations for story preservation"""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("URGENT: Document all known versions immediately")
            recommendations.append("Interview all family members who know the story")
            recommendations.append("Create multimedia recordings of story tellings")
        
        if "No new versions" in str(risk_factors):
            recommendations.append("Encourage story sharing at family gatherings")
            recommendations.append("Create opportunities for story continuation")
            recommendations.append("Consider modernizing story for younger audiences")
        
        if "Limited to single narrator" in str(risk_factors):
            recommendations.append("Share story with extended family members")
            recommendations.append("Teach story to multiple family branches")
            recommendations.append("Consider appointing story keepers")
        
        if "Low preservation quality" in str(risk_factors):
            recommendations.append("Create high-quality recordings of story tellings")
            recommendations.append("Document story variations and context")
            recommendations.append("Preserve original language versions")
        
        if "Core message becoming unstable" in str(risk_factors):
            recommendations.append("Document original core message and themes")
            recommendations.append("Create reference version for family")
            recommendations.append("Balance innovation with tradition preservation")
        
        # General recommendations
        recommendations.append("Create written version alongside oral tradition")
        recommendations.append("Include cultural context and historical background")
        recommendations.append("Connect story to family history and values")
        
        return recommendations

# Example usage
async def main():
    """Example usage of story continuation system"""
    
    print("Story Continuation Across Generations System Demo")
    print("=" * 60)
    
    # Initialize system
    story_system = StoryContinuationSystem()
    
    # Create sample characters
    characters = [
        Character(
            character_id="char_001",
            name="Elena Rodriguez",
            role="protagonist",
            traits=["brave", "determined", "family-oriented"],
            relationships={"char_002": "grandmother"},
            character_arc="Young woman overcomes adversity through family wisdom",
            symbolic_meaning="Represents new generation honoring old ways"
        ),
        Character(
            character_id="char_002", 
            name="Abuela Maria",
            role="mentor",
            traits=["wise", "spiritual", "storyteller"],
            relationships={"char_001": "granddaughter"},
            cultural_significance="Keeper of family traditions"
        )
    ]
    
    # Create story elements
    story_elements = StoryElement(
        plot_points=[
            "Elena faces financial hardship",
            "Abuela shares family recipe and story",
            "Elena starts successful catering business",
            "Family traditions preserved and shared"
        ],
        setting={"time": "1990s", "place": "East Los Angeles", "context": "immigrant family"},
        themes=[NarrativeTheme.FAMILY_BONDS, NarrativeTheme.TRADITION, NarrativeTheme.PERSEVERANCE],
        moral_lessons=["Family wisdom transcends generations", "Traditions can adapt while preserving essence"],
        cultural_context=["Mexican-American", "immigrant experience", "family business"],
        symbolic_elements=["grandmother's recipes", "family photos", "traditional dress"],
        emotional_beats=["struggle", "revelation", "triumph", "celebration"],
        conflict_types=["person vs. society", "tradition vs. modernity"]
    )
    
    # Create original story version
    original_story = StoryVersion(
        version_id="story_v1_001",
        story_title="The Recipe Book Legacy",
        story_type=StoryType.FAMILY_LEGEND,
        narrator_name="Maria Rodriguez",
        narrator_generation=2,
        telling_date=date(1995, 12, 24),
        audience=["Elena Rodriguez", "family children"],
        medium=StoryMedium.ORAL,
        content="""Once upon a time, there was a young woman named Elena who struggled to make ends meet after her husband left. She had two small children and worked multiple jobs, but it was never enough. One Christmas Eve, feeling desperate, she visited her grandmother, Abuela Maria.

Abuela Maria saw Elena's tears and knew her granddaughter's heart was breaking. She took Elena into the kitchen and pulled out an old wooden recipe box that had belonged to Elena's great-grandmother. 'Mija,' she said, 'these recipes are not just food. They are love, they are history, they are our family's strength.'

As Abuela Maria taught Elena to make the traditional tamales, mole, and pan dulce, she shared stories of how each recipe had sustained the family through difficult times. She told of Elena's great-grandmother selling food on the streets to survive the revolution, and how each generation had added their own touch while preserving the essence.

Elena learned not just the recipes, but the stories, the techniques passed down through generations. She started a small catering business, specializing in authentic family recipes. The business grew as people tasted not just the food, but the love and history in every dish.

Years later, Elena's own daughter would stand in the same kitchen, learning the same recipes, hearing the same stories, understanding that she was part of something much larger than herself. The recipe box became a symbol of family strength, tradition, and the power of love passed down through generations.""",
        characters=characters,
        story_elements=story_elements,
        context="Christmas Eve family gathering",
        language_used="English with Spanish phrases",
        preservation_quality=0.9
    )
    
    # Add original story
    result1 = await story_system.add_story_version(original_story)
    print(f"Added original story: Success: {result1['success']}")
    print(f"Themes identified: {result1['themes_identified']}")
    print(f"Lessons extracted: {result1['lessons_extracted']}")
    print(f"Narrative complexity: {result1['narrative_complexity']:.2f}")
    
    # Create continued version (next generation)
    continued_story = StoryVersion(
        version_id="story_v2_001",
        story_title="The Recipe Book Legacy: Sofia's Chapter",
        story_type=StoryType.FAMILY_LEGEND,
        narrator_name="Elena Rodriguez",
        narrator_generation=3,
        telling_date=date(2020, 12, 24),
        audience=["Sofia Martinez", "family grandchildren"],
        medium=StoryMedium.VIDEO,
        content="""Let me tell you about your grandmother Elena, and how our family's recipe box saved us once again, but in a way no one expected.

It was 2008, and the economy crashed. Elena's catering business was struggling - people stopped ordering for parties, restaurants weren't buying her food anymore. She was in her fifties, worried she'd lose everything she'd built from Abuela Maria's teachings.

But Elena remembered what Abuela had taught her - that these recipes were more than food, they were community, they were healing. So she did something no one expected. She started teaching cooking classes in her kitchen, sharing not just the recipes but the stories behind them.

People came not just to learn to cook, but to connect with something real, something authentic. Young Mexican-Americans who had lost touch with their culture found their way home through these recipes. Other immigrant families found comfort in sharing their own food stories.

Elena realized that the true legacy wasn't just preserving the recipes, but sharing them, growing the family beyond blood relations. She started a community kitchen, teaching anyone who wanted to learn, creating a family of choice bound by food and story.

Now, during the pandemic in 2020, when everyone was isolated, Elena started virtual cooking classes. Families stuck at home were cooking together, sharing stories across video calls, keeping traditions alive in new ways.

The recipe box that started with your great-great-grandmother surviving revolution had evolved into something bigger - a way to build community, preserve culture, and adapt tradition to serve each generation's needs.

Sofia, when you take these recipes forward, remember: the ingredients matter, but the love and the stories matter more. This is how we survive, how we thrive, how we stay connected across time and distance.""",
        characters=characters + [Character(
            character_id="char_003",
            name="Sofia Martinez",
            role="next_generation",
            traits=["curious", "tech-savvy", "culturally-aware"],
            relationships={"char_001": "daughter"}
        )],
        story_elements=StoryElement(
            plot_points=[
                "Economic crisis threatens family business",
                "Elena innovates by teaching cooking classes", 
                "Community forms around shared food traditions",
                "Pandemic drives virtual adaptation",
                "Legacy passes to next generation"
            ],
            setting={"time": "2008-2020", "place": "East Los Angeles", "context": "economic crisis and pandemic"},
            themes=[NarrativeTheme.FAMILY_BONDS, NarrativeTheme.TRADITION, NarrativeTheme.CHANGE, NarrativeTheme.WISDOM],
            moral_lessons=["Adaptation preserves tradition better than rigid conservation", "Community extends beyond blood family"],
            cultural_context=["Mexican-American", "economic resilience", "digital adaptation"],
            symbolic_elements=["recipe box", "community kitchen", "video calls", "shared meals"],
            emotional_beats=["crisis", "innovation", "connection", "hope"],
            conflict_types=["person vs. economy", "tradition vs. innovation"]
        ),
        source_version_id="story_v1_001",
        variations_from_previous=["Added pandemic context", "Emphasized community building"],
        additions=["Virtual teaching element", "Community kitchen concept"],
        cultural_adaptations=["Digital technology integration"],
        context="Virtual family Christmas gathering during pandemic",
        preservation_quality=0.95
    )
    
    # Add continued story
    result2 = await story_system.add_story_version(continued_story)
    print(f"\nAdded continued story: Success: {result2['success']}")
    
    # Document continuation
    continuation = StoryContinuation(
        continuation_id="cont_001",
        original_version_id="story_v1_001",
        continued_version_id="story_v2_001", 
        continuation_type=ContinuationType.EXPANSION,
        continuation_date=date(2020, 12, 24),
        continuator_name="Elena Rodriguez",
        continuator_relationship="protagonist_of_original",
        time_gap=25,
        changes_made=[
            "Added economic crisis context",
            "Expanded community building theme",
            "Introduced digital adaptation"
        ],
        reasons_for_changes=[
            "Reflect lived experience of financial crisis",
            "Show evolution of family business model", 
            "Adapt to pandemic circumstances"
        ],
        preservation_fidelity=0.8,
        innovation_level=0.7,
        cultural_shift_indicators=["digital technology adoption"],
        language_evolution=["incorporated pandemic terminology"],
        theme_evolution={
            "tradition": "adaptive_tradition",
            "family": "extended_community_family"
        }
    )
    
    continuation_result = await story_system.document_story_continuation(continuation)
    print(f"Documented continuation: Success: {continuation_result['success']}")
    print(f"Fidelity score: {continuation_result['fidelity_score']:.2f}")
    print(f"Innovation score: {continuation_result['innovation_score']:.2f}")
    
    # Trace story lineage
    print("\n" + "=" * 60)
    print("STORY LINEAGE ANALYSIS")
    print("=" * 60)
    
    lineages = await story_system.trace_story_lineage("Recipe Book Legacy")
    print(f"Found {len(lineages)} lineages")
    
    for lineage in lineages:
        print(f"\nLineage: {lineage.story_family_name}")
        print(f"Generations: {lineage.current_generation}")
        print(f"Time span: {lineage.time_span[0]} to {lineage.time_span[1]}")
        print(f"Preservation status: {lineage.preservation_status}")
        print(f"Core message stability: {lineage.core_message_stability:.2f}")
        print(f"Theme persistence: {[f'{theme.value}: {score:.2f}' for theme, score in list(lineage.theme_persistence.items())[:3]]}")
    
    # Analyze theme evolution
    print("\n" + "=" * 60)
    print("THEME EVOLUTION ANALYSIS")
    print("=" * 60)
    
    if lineages:
        theme_evolution = await story_system.analyze_theme_evolution(lineages[0].lineage_id)
        print(f"Theme stability score: {theme_evolution['theme_stability_score']:.2f}")
        print(f"Dominant themes: {theme_evolution['dominant_themes']}")
        
        print("\nDetailed theme analysis:")
        for theme, data in list(theme_evolution['theme_evolution'].items())[:3]:
            print(f"- {theme}: persistence {data['persistence_score']:.2f}, trend: {data['strength_trend']}")
    
    # Generate continuation predictions
    print("\n" + "=" * 60)
    print("CONTINUATION PREDICTIONS")
    print("=" * 60)
    
    predictions = await story_system.generate_continuation_predictions("story_v2_001")
    print(f"Generated {len(predictions)} continuation predictions:")
    
    for pred in predictions:
        print(f"\n- Type: {pred['continuation_type']}")
        print(f"  Probability: {pred['probability']:.1%}")
        print(f"  Focus: {pred['suggested_focus']}")
        print(f"  Recommended narrator: {pred['recommended_narrator']}")
    
    # Assess preservation risk
    print("\n" + "=" * 60)
    print("PRESERVATION RISK ASSESSMENT")
    print("=" * 60)
    
    if lineages:
        risk_assessment = await story_system.assess_story_preservation_risk(lineages[0].lineage_id)
        print(f"Risk level: {risk_assessment['risk_level']}")
        print(f"Years since last telling: {risk_assessment['years_since_last_telling']:.1f}")
        print(f"Narrator diversity: {risk_assessment['narrator_diversity']}")
        print(f"Risk factors: {risk_assessment['risk_factors']}")
        
        print("\nRecommendations:")
        for rec in risk_assessment['recommendations'][:5]:
            print(f"  - {rec}")

if __name__ == "__main__":
    asyncio.run(main())