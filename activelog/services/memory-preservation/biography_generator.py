"""
Automatic Biography Generation System

This module provides comprehensive biography generation capabilities including
life event analysis, narrative construction, and multi-modal content integration
for creating rich, personalized autobiographical content.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from datetime import datetime, date
import numpy as np

class LifeEventType(Enum):
    """Types of life events for biography organization"""
    BIRTH = "birth"
    EDUCATION = "education"
    CAREER = "career"
    RELATIONSHIP = "relationship"
    FAMILY = "family"
    ACHIEVEMENT = "achievement"
    TRAVEL = "travel"
    HEALTH = "health"
    HOBBY = "hobby"
    LOSS = "loss"
    MILESTONE = "milestone"
    CHALLENGE = "challenge"
    TRANSFORMATION = "transformation"

class BiographyStyle(Enum):
    """Biography writing styles"""
    CHRONOLOGICAL = "chronological"
    THEMATIC = "thematic"
    NARRATIVE = "narrative"
    MEMOIR = "memoir"
    ACADEMIC = "academic"
    CASUAL = "casual"
    POETIC = "poetic"
    PROFESSIONAL = "professional"

class ContentSource(Enum):
    """Sources of biographical content"""
    INTERVIEW = "interview"
    DOCUMENT = "document"
    PHOTO = "photo"
    JOURNAL = "journal"
    SOCIAL_MEDIA = "social_media"
    EMAIL = "email"
    AUDIO = "audio"
    VIDEO = "video"
    TESTIMONY = "testimony"
    PUBLIC_RECORD = "public_record"

@dataclass
class LifeEvent:
    """Represents a significant life event"""
    event_id: str
    event_type: LifeEventType
    title: str
    description: str
    date: Optional[date]
    location: Optional[str]
    people_involved: List[str]
    emotional_significance: float  # 0-1 scale
    impact_level: float  # 0-1 scale
    sources: List[ContentSource]
    multimedia: Dict[str, List[str]] = field(default_factory=dict)  # photos, videos, etc.
    themes: List[str] = field(default_factory=list)
    context: Optional[str] = None
    lessons_learned: List[str] = field(default_factory=list)

@dataclass
class PersonProfile:
    """Comprehensive person profile for biography"""
    person_id: str
    name: str
    birth_date: Optional[date]
    birth_place: Optional[str]
    current_location: Optional[str]
    occupation: List[str]
    education: List[str]
    relationships: Dict[str, List[str]]  # family, friends, colleagues
    personality_traits: List[str]
    values: List[str]
    interests: List[str]
    achievements: List[str]
    challenges_overcome: List[str]
    life_philosophy: Optional[str] = None
    cultural_background: Optional[str] = None

@dataclass
class BiographyChapter:
    """A chapter or section of a biography"""
    chapter_id: str
    title: str
    content: str
    time_period: Tuple[Optional[date], Optional[date]]
    events: List[LifeEvent]
    themes: List[str]
    word_count: int
    chapter_type: str  # introduction, childhood, career, etc.

@dataclass
class BiographyResult:
    """Complete generated biography"""
    person_profile: PersonProfile
    chapters: List[BiographyChapter]
    style: BiographyStyle
    word_count: int
    generation_time: float
    sources_used: List[ContentSource]
    multimedia_items: int
    completeness_score: float
    narrative_flow_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

class LifeEventExtractor:
    """Extracts and analyzes life events from various sources"""
    
    def __init__(self):
        self.event_keywords = {
            LifeEventType.BIRTH: ["born", "birth", "arrived", "came into the world"],
            LifeEventType.EDUCATION: ["school", "university", "graduated", "studied", "degree", "learning"],
            LifeEventType.CAREER: ["job", "career", "work", "employed", "promoted", "started working"],
            LifeEventType.RELATIONSHIP: ["met", "married", "engaged", "dating", "relationship", "partner"],
            LifeEventType.FAMILY: ["child", "baby", "parent", "sibling", "family", "adopted"],
            LifeEventType.ACHIEVEMENT: ["won", "achieved", "accomplished", "success", "award", "recognition"],
            LifeEventType.TRAVEL: ["traveled", "visited", "trip", "journey", "vacation", "moved"],
            LifeEventType.HEALTH: ["illness", "recovery", "surgery", "health", "medical", "hospital"],
            LifeEventType.CHALLENGE: ["difficult", "struggle", "challenge", "hardship", "obstacle"],
            LifeEventType.MILESTONE: ["birthday", "anniversary", "celebration", "milestone", "special day"]
        }
    
    async def extract_events_from_text(self, text: str, source: ContentSource) -> List[LifeEvent]:
        """Extract life events from text content"""
        events = []
        sentences = text.split('.')
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Analyze sentence for event indicators
            event_type = await self._classify_event_type(sentence)
            if event_type:
                # Extract event details
                event = await self._create_event_from_sentence(
                    sentence, event_type, source, f"event_{i}"
                )
                if event:
                    events.append(event)
        
        return events
    
    async def _classify_event_type(self, sentence: str) -> Optional[LifeEventType]:
        """Classify sentence as a specific type of life event"""
        sentence_lower = sentence.lower()
        
        # Score each event type based on keyword matches
        type_scores = {}
        for event_type, keywords in self.event_keywords.items():
            score = sum(1 for keyword in keywords if keyword in sentence_lower)
            if score > 0:
                type_scores[event_type] = score
        
        if not type_scores:
            return None
        
        # Return the highest scoring event type
        return max(type_scores, key=type_scores.get)
    
    async def _create_event_from_sentence(self, sentence: str, event_type: LifeEventType,
                                        source: ContentSource, event_id: str) -> Optional[LifeEvent]:
        """Create a life event from a sentence"""
        # Extract basic information
        title = await self._extract_event_title(sentence, event_type)
        date_info = await self._extract_date(sentence)
        location = await self._extract_location(sentence)
        people = await self._extract_people(sentence)
        
        # Calculate significance scores
        emotional_significance = await self._calculate_emotional_significance(sentence)
        impact_level = await self._calculate_impact_level(sentence, event_type)
        
        event = LifeEvent(
            event_id=event_id,
            event_type=event_type,
            title=title,
            description=sentence,
            date=date_info,
            location=location,
            people_involved=people,
            emotional_significance=emotional_significance,
            impact_level=impact_level,
            sources=[source],
            themes=await self._extract_themes(sentence),
            lessons_learned=await self._extract_lessons(sentence)
        )
        
        return event
    
    async def _extract_event_title(self, sentence: str, event_type: LifeEventType) -> str:
        """Extract a concise title for the event"""
        # Simple title extraction based on event type
        words = sentence.split()[:8]  # First 8 words
        title = " ".join(words)
        
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or f"{event_type.value.replace('_', ' ').title()} Event"
    
    async def _extract_date(self, sentence: str) -> Optional[date]:
        """Extract date information from sentence"""
        # Simple date extraction patterns
        date_patterns = [
            r'\b(\d{4})\b',  # Year
            r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',  # MM/DD/YYYY
            r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, sentence, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 1:  # Just year
                        year = int(match.group(1))
                        return date(year, 1, 1)
                    elif len(match.groups()) == 3:  # Full date
                        if match.group(1).isdigit():  # MM/DD/YYYY
                            month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
                            return date(year, month, day)
                        else:  # Month name format
                            month_names = {
                                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                                'september': 9, 'october': 10, 'november': 11, 'december': 12
                            }
                            month = month_names.get(match.group(1).lower(), 1)
                            day, year = int(match.group(2)), int(match.group(3))
                            return date(year, month, day)
                except (ValueError, KeyError):
                    continue
        
        return None
    
    async def _extract_location(self, sentence: str) -> Optional[str]:
        """Extract location information from sentence"""
        # Simple location extraction patterns
        location_patterns = [
            r'\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\bfrom\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, sentence)
            if match:
                location = match.group(1)
                # Filter out common non-location words
                non_locations = {'University', 'School', 'Hospital', 'Company', 'Church'}
                if location not in non_locations:
                    return location
        
        return None
    
    async def _extract_people(self, sentence: str) -> List[str]:
        """Extract people mentioned in sentence"""
        # Simple pattern for proper names
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        matches = re.findall(name_pattern, sentence)
        
        # Filter out common non-name phrases
        non_names = {'New York', 'San Francisco', 'Los Angeles', 'High School', 'Middle School'}
        people = [match for match in matches if match not in non_names]
        
        return people[:5]  # Limit to 5 people per event
    
    async def _calculate_emotional_significance(self, sentence: str) -> float:
        """Calculate emotional significance of event"""
        positive_words = ['happy', 'joy', 'love', 'excited', 'wonderful', 'amazing', 'proud', 'celebration']
        negative_words = ['sad', 'difficult', 'challenge', 'loss', 'struggle', 'pain', 'worry', 'fear']
        intense_words = ['life-changing', 'unforgettable', 'incredible', 'devastating', 'overwhelming']
        
        sentence_lower = sentence.lower()
        
        positive_score = sum(1 for word in positive_words if word in sentence_lower)
        negative_score = sum(1 for word in negative_words if word in sentence_lower)
        intense_score = sum(2 for word in intense_words if word in sentence_lower)
        
        total_emotional_words = positive_score + negative_score + intense_score
        max_possible = 10  # Reasonable maximum
        
        return min(total_emotional_words / max_possible, 1.0)
    
    async def _calculate_impact_level(self, sentence: str, event_type: LifeEventType) -> float:
        """Calculate impact level of event"""
        # Base impact levels by event type
        base_impacts = {
            LifeEventType.BIRTH: 1.0,
            LifeEventType.EDUCATION: 0.7,
            LifeEventType.CAREER: 0.8,
            LifeEventType.RELATIONSHIP: 0.9,
            LifeEventType.FAMILY: 0.9,
            LifeEventType.ACHIEVEMENT: 0.6,
            LifeEventType.TRAVEL: 0.4,
            LifeEventType.HEALTH: 0.8,
            LifeEventType.CHALLENGE: 0.7,
            LifeEventType.MILESTONE: 0.5
        }
        
        base_impact = base_impacts.get(event_type, 0.5)
        
        # Adjust based on content
        impact_words = ['changed', 'transformed', 'major', 'significant', 'important', 'crucial']
        sentence_lower = sentence.lower()
        
        impact_modifier = sum(0.1 for word in impact_words if word in sentence_lower)
        
        return min(base_impact + impact_modifier, 1.0)
    
    async def _extract_themes(self, sentence: str) -> List[str]:
        """Extract thematic elements from sentence"""
        theme_keywords = {
            'growth': ['learned', 'grew', 'developed', 'improved', 'progress'],
            'relationships': ['friend', 'family', 'love', 'together', 'support'],
            'achievement': ['success', 'accomplished', 'won', 'achieved', 'completed'],
            'challenge': ['difficult', 'struggle', 'overcome', 'persevered', 'endured'],
            'change': ['changed', 'different', 'new', 'transformed', 'shifted'],
            'discovery': ['discovered', 'found', 'realized', 'learned', 'understood']
        }
        
        sentence_lower = sentence.lower()
        themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in sentence_lower for keyword in keywords):
                themes.append(theme)
        
        return themes
    
    async def _extract_lessons(self, sentence: str) -> List[str]:
        """Extract life lessons from sentence"""
        lesson_indicators = ['learned', 'realized', 'understood', 'discovered', 'taught me']
        sentence_lower = sentence.lower()
        
        if any(indicator in sentence_lower for indicator in lesson_indicators):
            # Simple lesson extraction - in a real system this would be more sophisticated
            return [f"Life lesson from: {sentence[:100]}..."]
        
        return []

class NarrativeGenerator:
    """Generates coherent narrative from life events"""
    
    def __init__(self):
        self.transition_phrases = {
            'chronological': [
                "Following this", "Subsequently", "Later", "After that", "Meanwhile",
                "During this time", "In the years that followed", "As time progressed"
            ],
            'thematic': [
                "Similarly", "In contrast", "Another aspect", "Related to this",
                "Building on this theme", "Equally important", "In a different vein"
            ],
            'causal': [
                "As a result", "Consequently", "This led to", "Because of this",
                "The outcome was", "This experience shaped", "Influenced by"
            ]
        }
    
    async def generate_biography_chapters(self, events: List[LifeEvent], 
                                        person: PersonProfile, 
                                        style: BiographyStyle) -> List[BiographyChapter]:
        """Generate biography chapters from life events"""
        if style == BiographyStyle.CHRONOLOGICAL:
            return await self._generate_chronological_chapters(events, person)
        elif style == BiographyStyle.THEMATIC:
            return await self._generate_thematic_chapters(events, person)
        else:
            return await self._generate_narrative_chapters(events, person)
    
    async def _generate_chronological_chapters(self, events: List[LifeEvent], 
                                             person: PersonProfile) -> List[BiographyChapter]:
        """Generate chapters organized chronologically"""
        # Sort events by date
        dated_events = [e for e in events if e.date]
        undated_events = [e for e in events if not e.date]
        
        dated_events.sort(key=lambda x: x.date)
        
        # Group events into life periods
        chapters = []
        
        # Introduction chapter
        intro_content = await self._generate_introduction(person)
        chapters.append(BiographyChapter(
            chapter_id="intro",
            title="Introduction",
            content=intro_content,
            time_period=(None, None),
            events=[],
            themes=["introduction", "overview"],
            word_count=len(intro_content.split()),
            chapter_type="introduction"
        ))
        
        # Early life (birth to 18)
        early_events = [e for e in dated_events if e.date and self._calculate_age_at_event(e.date, person.birth_date) <= 18]
        if early_events:
            early_content = await self._generate_chapter_content(early_events, "Early Life", person)
            chapters.append(BiographyChapter(
                chapter_id="early_life",
                title="Early Life and Education",
                content=early_content,
                time_period=(person.birth_date, early_events[-1].date if early_events else None),
                events=early_events,
                themes=["childhood", "education", "family"],
                word_count=len(early_content.split()),
                chapter_type="childhood"
            ))
        
        # Adult life chapters (grouped by decades or major periods)
        adult_events = [e for e in dated_events if e.date and self._calculate_age_at_event(e.date, person.birth_date) > 18]
        
        if adult_events:
            # Group by life stages
            career_events = [e for e in adult_events if e.event_type == LifeEventType.CAREER]
            family_events = [e for e in adult_events if e.event_type in [LifeEventType.RELATIONSHIP, LifeEventType.FAMILY]]
            achievement_events = [e for e in adult_events if e.event_type == LifeEventType.ACHIEVEMENT]
            
            if career_events:
                career_content = await self._generate_chapter_content(career_events, "Career and Professional Life", person)
                chapters.append(BiographyChapter(
                    chapter_id="career",
                    title="Career and Professional Life",
                    content=career_content,
                    time_period=(career_events[0].date, career_events[-1].date),
                    events=career_events,
                    themes=["career", "professional", "achievement"],
                    word_count=len(career_content.split()),
                    chapter_type="career"
                ))
            
            if family_events:
                family_content = await self._generate_chapter_content(family_events, "Family and Relationships", person)
                chapters.append(BiographyChapter(
                    chapter_id="family",
                    title="Family and Relationships",
                    content=family_content,
                    time_period=(family_events[0].date, family_events[-1].date),
                    events=family_events,
                    themes=["family", "relationships", "love"],
                    word_count=len(family_content.split()),
                    chapter_type="family"
                ))
        
        return chapters
    
    async def _generate_thematic_chapters(self, events: List[LifeEvent], 
                                        person: PersonProfile) -> List[BiographyChapter]:
        """Generate chapters organized by themes"""
        chapters = []
        
        # Group events by theme
        theme_groups = {}
        for event in events:
            for theme in event.themes:
                if theme not in theme_groups:
                    theme_groups[theme] = []
                theme_groups[theme].append(event)
        
        # Create chapters for major themes
        major_themes = [(theme, events) for theme, events in theme_groups.items() if len(events) >= 3]
        major_themes.sort(key=lambda x: len(x[1]), reverse=True)
        
        for theme, theme_events in major_themes[:5]:  # Top 5 themes
            content = await self._generate_thematic_content(theme_events, theme, person)
            chapters.append(BiographyChapter(
                chapter_id=f"theme_{theme}",
                title=f"{theme.title()}: A Life Theme",
                content=content,
                time_period=(
                    min(e.date for e in theme_events if e.date) if any(e.date for e in theme_events) else None,
                    max(e.date for e in theme_events if e.date) if any(e.date for e in theme_events) else None
                ),
                events=theme_events,
                themes=[theme],
                word_count=len(content.split()),
                chapter_type="thematic"
            ))
        
        return chapters
    
    async def _generate_narrative_chapters(self, events: List[LifeEvent], 
                                         person: PersonProfile) -> List[BiographyChapter]:
        """Generate narrative-style chapters with story arcs"""
        # Create story arcs based on challenges and resolutions
        chapters = []
        
        # Find major life challenges and their resolutions
        challenges = [e for e in events if e.event_type == LifeEventType.CHALLENGE]
        achievements = [e for e in events if e.event_type == LifeEventType.ACHIEVEMENT]
        
        for i, challenge in enumerate(challenges):
            # Find related achievements or resolutions
            related_events = [challenge]
            
            # Look for events that might be related resolutions
            for achievement in achievements:
                if (achievement.date and challenge.date and 
                    abs((achievement.date - challenge.date).days) <= 365):  # Within a year
                    related_events.append(achievement)
            
            if len(related_events) > 1:
                content = await self._generate_narrative_arc(related_events, person)
                chapters.append(BiographyChapter(
                    chapter_id=f"arc_{i}",
                    title=f"Overcoming {challenge.title}",
                    content=content,
                    time_period=(challenge.date, related_events[-1].date if related_events[-1].date else challenge.date),
                    events=related_events,
                    themes=["challenge", "growth", "resilience"],
                    word_count=len(content.split()),
                    chapter_type="narrative_arc"
                ))
        
        return chapters
    
    async def _generate_introduction(self, person: PersonProfile) -> str:
        """Generate biography introduction"""
        intro_parts = []
        
        # Opening statement
        intro_parts.append(f"{person.name} is a remarkable individual whose life story encompasses {', '.join(person.occupation[:3]) if person.occupation else 'diverse experiences'}.")
        
        # Background
        if person.birth_date and person.birth_place:
            intro_parts.append(f"Born on {person.birth_date.strftime('%B %d, %Y')} in {person.birth_place}, {person.name} has lived a life marked by {', '.join(person.values[:3]) if person.values else 'strong principles and dedication'}.")
        
        # Key characteristics
        if person.personality_traits:
            intro_parts.append(f"Known for being {', '.join(person.personality_traits[:3])}, {person.name} has approached life with {person.life_philosophy or 'determination and grace'}.")
        
        # Preview of what's to come
        intro_parts.append("This biography traces the journey of a life well-lived, exploring the experiences, relationships, and moments that have shaped an extraordinary individual.")
        
        return " ".join(intro_parts)
    
    async def _generate_chapter_content(self, events: List[LifeEvent], chapter_theme: str, 
                                      person: PersonProfile) -> str:
        """Generate content for a chapter"""
        content_parts = []
        
        # Chapter introduction
        content_parts.append(f"The story of {person.name}'s {chapter_theme.lower()} reveals a journey of {', '.join(set(theme for event in events for theme in event.themes))[:3] if events else 'growth and discovery'}.")
        
        # Process events
        for i, event in enumerate(events):
            # Add transition
            if i > 0:
                transition = np.random.choice(self.transition_phrases['chronological'])
                content_parts.append(f"{transition}, {event.description}")
            else:
                content_parts.append(event.description)
            
            # Add context or reflection
            if event.lessons_learned:
                content_parts.append(f"This experience taught {person.name} {event.lessons_learned[0]}")
            
            # Add emotional context
            if event.emotional_significance > 0.7:
                content_parts.append("This moment stands out as particularly meaningful in the larger narrative of life.")
        
        # Chapter conclusion
        content_parts.append(f"Through these experiences, {person.name} demonstrated the qualities that would define much of life's journey: {', '.join(person.personality_traits[:2]) if person.personality_traits else 'resilience and wisdom'}.")
        
        return " ".join(content_parts)
    
    async def _generate_thematic_content(self, events: List[LifeEvent], theme: str, 
                                       person: PersonProfile) -> str:
        """Generate thematic chapter content"""
        content_parts = []
        
        content_parts.append(f"The theme of {theme} runs throughout {person.name}'s life story like a golden thread, connecting experiences and revealing deeper patterns of growth and meaning.")
        
        # Group events by impact level
        high_impact = [e for e in events if e.impact_level > 0.7]
        moderate_impact = [e for e in events if 0.4 <= e.impact_level <= 0.7]
        
        # Discuss high-impact events first
        for event in high_impact:
            content_parts.append(f"A pivotal moment came when {event.description}")
            if event.lessons_learned:
                content_parts.append(f"From this, {person.name} learned {event.lessons_learned[0]}")
        
        # Connect with moderate impact events
        for event in moderate_impact:
            transition = np.random.choice(self.transition_phrases['thematic'])
            content_parts.append(f"{transition}, {event.description}")
        
        return " ".join(content_parts)
    
    async def _generate_narrative_arc(self, events: List[LifeEvent], person: PersonProfile) -> str:
        """Generate narrative arc content"""
        content_parts = []
        
        # Set the stage
        content_parts.append(f"Life presented {person.name} with a significant challenge that would test character and resolve.")
        
        # Present the challenge
        challenge_events = [e for e in events if e.event_type == LifeEventType.CHALLENGE]
        if challenge_events:
            content_parts.append(challenge_events[0].description)
        
        # Show the journey
        other_events = [e for e in events if e.event_type != LifeEventType.CHALLENGE]
        for event in other_events:
            content_parts.append(f"In response, {event.description}")
        
        # Resolution and growth
        content_parts.append(f"Through this experience, {person.name} emerged stronger and wiser, embodying the resilience that would characterize future endeavors.")
        
        return " ".join(content_parts)
    
    def _calculate_age_at_event(self, event_date: date, birth_date: Optional[date]) -> int:
        """Calculate age at time of event"""
        if not birth_date:
            return 25  # Default assumption
        
        age = event_date.year - birth_date.year
        if event_date.month < birth_date.month or (event_date.month == birth_date.month and event_date.day < birth_date.day):
            age -= 1
        
        return age

class BiographyGenerator:
    """Main biography generation system"""
    
    def __init__(self):
        self.event_extractor = LifeEventExtractor()
        self.narrative_generator = NarrativeGenerator()
        self.supported_sources = list(ContentSource)
    
    async def generate_biography(self, person_profile: PersonProfile, 
                               content_sources: Dict[ContentSource, List[str]],
                               style: BiographyStyle = BiographyStyle.CHRONOLOGICAL) -> BiographyResult:
        """Generate complete biography from multiple sources"""
        start_time = datetime.now()
        
        # Extract life events from all sources
        all_events = []
        sources_used = []
        
        for source, content_list in content_sources.items():
            sources_used.append(source)
            for content in content_list:
                events = await self.event_extractor.extract_events_from_text(content, source)
                all_events.extend(events)
        
        # Remove duplicate events and merge similar ones
        unique_events = await self._deduplicate_events(all_events)
        
        # Generate chapters
        chapters = await self.narrative_generator.generate_biography_chapters(
            unique_events, person_profile, style
        )
        
        # Calculate metrics
        word_count = sum(chapter.word_count for chapter in chapters)
        multimedia_items = sum(len(event.multimedia.get('photos', [])) + 
                             len(event.multimedia.get('videos', [])) + 
                             len(event.multimedia.get('documents', []))
                             for event in unique_events)
        
        completeness_score = await self._calculate_completeness_score(unique_events, person_profile)
        narrative_flow_score = await self._calculate_narrative_flow_score(chapters)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return BiographyResult(
            person_profile=person_profile,
            chapters=chapters,
            style=style,
            word_count=word_count,
            generation_time=processing_time,
            sources_used=sources_used,
            multimedia_items=multimedia_items,
            completeness_score=completeness_score,
            narrative_flow_score=narrative_flow_score,
            metadata={
                "events_extracted": len(unique_events),
                "chapters_generated": len(chapters),
                "average_chapter_length": word_count / len(chapters) if chapters else 0,
                "primary_themes": self._extract_primary_themes(unique_events)
            }
        )
    
    async def _deduplicate_events(self, events: List[LifeEvent]) -> List[LifeEvent]:
        """Remove duplicate events and merge similar ones"""
        unique_events = []
        
        for event in events:
            # Look for similar events
            similar_found = False
            for unique_event in unique_events:
                if await self._are_events_similar(event, unique_event):
                    # Merge events
                    await self._merge_events(unique_event, event)
                    similar_found = True
                    break
            
            if not similar_found:
                unique_events.append(event)
        
        return unique_events
    
    async def _are_events_similar(self, event1: LifeEvent, event2: LifeEvent) -> bool:
        """Check if two events are similar enough to merge"""
        # Same event type
        if event1.event_type != event2.event_type:
            return False
        
        # Similar dates (within 30 days)
        if event1.date and event2.date:
            if abs((event1.date - event2.date).days) > 30:
                return False
        
        # Similar titles (word overlap)
        words1 = set(event1.title.lower().split())
        words2 = set(event2.title.lower().split())
        overlap = len(words1.intersection(words2)) / max(len(words1), len(words2))
        
        return overlap > 0.5
    
    async def _merge_events(self, primary_event: LifeEvent, secondary_event: LifeEvent):
        """Merge secondary event into primary event"""
        # Combine descriptions
        if secondary_event.description not in primary_event.description:
            primary_event.description += f" {secondary_event.description}"
        
        # Merge people involved
        primary_event.people_involved.extend(
            person for person in secondary_event.people_involved 
            if person not in primary_event.people_involved
        )
        
        # Merge sources
        primary_event.sources.extend(
            source for source in secondary_event.sources 
            if source not in primary_event.sources
        )
        
        # Take higher significance scores
        primary_event.emotional_significance = max(
            primary_event.emotional_significance, 
            secondary_event.emotional_significance
        )
        primary_event.impact_level = max(
            primary_event.impact_level, 
            secondary_event.impact_level
        )
        
        # Merge themes
        primary_event.themes.extend(
            theme for theme in secondary_event.themes 
            if theme not in primary_event.themes
        )
    
    async def _calculate_completeness_score(self, events: List[LifeEvent], 
                                          person: PersonProfile) -> float:
        """Calculate how complete the biography is"""
        # Check coverage of major life areas
        life_areas = {
            'early_life': any(e.event_type == LifeEventType.BIRTH for e in events),
            'education': any(e.event_type == LifeEventType.EDUCATION for e in events),
            'career': any(e.event_type == LifeEventType.CAREER for e in events),
            'relationships': any(e.event_type == LifeEventType.RELATIONSHIP for e in events),
            'achievements': any(e.event_type == LifeEventType.ACHIEVEMENT for e in events)
        }
        
        coverage_score = sum(life_areas.values()) / len(life_areas)
        
        # Check temporal coverage if birth date is known
        temporal_score = 1.0
        if person.birth_date and events:
            dated_events = [e for e in events if e.date]
            if dated_events:
                earliest_event = min(e.date for e in dated_events)
                latest_event = max(e.date for e in dated_events)
                
                expected_span = (date.today() - person.birth_date).days
                actual_span = (latest_event - earliest_event).days if latest_event != earliest_event else 1
                
                temporal_score = min(actual_span / expected_span, 1.0)
        
        # Check source diversity
        source_diversity = len(set(source for event in events for source in event.sources)) / len(ContentSource)
        
        return (coverage_score * 0.5 + temporal_score * 0.3 + source_diversity * 0.2)
    
    async def _calculate_narrative_flow_score(self, chapters: List[BiographyChapter]) -> float:
        """Calculate how well the narrative flows"""
        if not chapters:
            return 0.0
        
        # Check chapter length consistency
        if len(chapters) > 1:
            word_counts = [chapter.word_count for chapter in chapters]
            mean_count = np.mean(word_counts)
            std_count = np.std(word_counts)
            consistency_score = 1.0 - min(std_count / mean_count, 1.0) if mean_count > 0 else 0.0
        else:
            consistency_score = 1.0
        
        # Check thematic coherence
        all_themes = [theme for chapter in chapters for theme in chapter.themes]
        unique_themes = set(all_themes)
        theme_coverage = len(unique_themes) / len(all_themes) if all_themes else 0.0
        
        # Check chronological ordering (for chronological style)
        chronological_score = 1.0
        dated_chapters = [(i, chapter) for i, chapter in enumerate(chapters) 
                         if chapter.time_period[0] is not None]
        
        if len(dated_chapters) > 1:
            for i in range(1, len(dated_chapters)):
                current_start = dated_chapters[i][1].time_period[0]
                previous_start = dated_chapters[i-1][1].time_period[0]
                
                if current_start < previous_start:
                    chronological_score -= 0.2
        
        return (consistency_score * 0.4 + theme_coverage * 0.3 + chronological_score * 0.3)
    
    def _extract_primary_themes(self, events: List[LifeEvent]) -> List[str]:
        """Extract the most common themes from events"""
        theme_counts = {}
        for event in events:
            for theme in event.themes:
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
        
        # Return top 5 themes
        return sorted(theme_counts.keys(), key=theme_counts.get, reverse=True)[:5]
    
    async def export_biography(self, biography: BiographyResult, format_type: str = "markdown") -> str:
        """Export biography in specified format"""
        if format_type == "markdown":
            return await self._export_to_markdown(biography)
        elif format_type == "html":
            return await self._export_to_html(biography)
        else:
            return await self._export_to_text(biography)
    
    async def _export_to_markdown(self, biography: BiographyResult) -> str:
        """Export biography as Markdown"""
        lines = []
        
        # Title
        lines.append(f"# The Life Story of {biography.person_profile.name}")
        lines.append("")
        
        # Table of contents
        lines.append("## Table of Contents")
        for i, chapter in enumerate(biography.chapters, 1):
            lines.append(f"{i}. [{chapter.title}](#{chapter.title.lower().replace(' ', '-')})")
        lines.append("")
        
        # Chapters
        for chapter in biography.chapters:
            lines.append(f"## {chapter.title}")
            lines.append("")
            lines.append(chapter.content)
            lines.append("")
            
            if chapter.events:
                lines.append("### Key Events")
                for event in chapter.events:
                    date_str = event.date.strftime("%Y-%m-%d") if event.date else "Date unknown"
                    lines.append(f"- **{date_str}**: {event.title}")
                lines.append("")
        
        # Appendix
        lines.append("## Biography Metadata")
        lines.append(f"- **Word Count**: {biography.word_count}")
        lines.append(f"- **Generation Time**: {biography.generation_time:.2f} seconds")
        lines.append(f"- **Completeness Score**: {biography.completeness_score:.2f}")
        lines.append(f"- **Sources Used**: {', '.join([s.value for s in biography.sources_used])}")
        
        return "\n".join(lines)
    
    async def _export_to_html(self, biography: BiographyResult) -> str:
        """Export biography as HTML"""
        # Simplified HTML export
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"<title>The Life Story of {biography.person_profile.name}</title>",
            "<style>body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }</style>",
            "</head>",
            "<body>",
            f"<h1>The Life Story of {biography.person_profile.name}</h1>"
        ]
        
        for chapter in biography.chapters:
            html_lines.extend([
                f"<h2>{chapter.title}</h2>",
                f"<p>{chapter.content}</p>"
            ])
        
        html_lines.extend([
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_lines)
    
    async def _export_to_text(self, biography: BiographyResult) -> str:
        """Export biography as plain text"""
        lines = []
        
        lines.append(f"THE LIFE STORY OF {biography.person_profile.name.upper()}")
        lines.append("=" * 60)
        lines.append("")
        
        for chapter in biography.chapters:
            lines.append(chapter.title.upper())
            lines.append("-" * len(chapter.title))
            lines.append("")
            lines.append(chapter.content)
            lines.append("")
            lines.append("")
        
        return "\n".join(lines)

# Example usage
async def main():
    """Example usage of biography generation system"""
    
    # Create a person profile
    person = PersonProfile(
        person_id="person_001",
        name="John Smith",
        birth_date=date(1980, 5, 15),
        birth_place="Chicago, Illinois",
        current_location="San Francisco, California",
        occupation=["Software Engineer", "Writer", "Mentor"],
        education=["BS Computer Science - MIT", "MS Engineering - Stanford"],
        relationships={
            "family": ["Mary Smith (wife)", "Emma Smith (daughter)", "James Smith (son)"],
            "friends": ["Robert Johnson", "Sarah Williams"],
            "colleagues": ["Dr. Peterson", "Alice Chen"]
        },
        personality_traits=["analytical", "creative", "empathetic", "determined"],
        values=["integrity", "lifelong learning", "family", "innovation"],
        interests=["technology", "writing", "hiking", "photography"],
        achievements=["Published novel", "Tech startup founder", "Mentored 50+ engineers"],
        challenges_overcome=["Career transition", "Work-life balance", "Public speaking"],
        life_philosophy="Every challenge is an opportunity to grow and help others."
    )
    
    # Sample content sources
    content_sources = {
        ContentSource.INTERVIEW: [
            "I was born on May 15, 1980, in Chicago to wonderful parents who encouraged my curiosity. Growing up, I was always fascinated by computers and technology. I learned programming when I was 12 years old and knew I wanted to pursue computer science.",
            "My time at MIT was transformative. I learned not just technical skills but also how to think critically and solve complex problems. I met my wife Mary there during our junior year, and we supported each other through challenging coursework.",
            "After graduating from MIT, I worked at several tech companies before starting my own startup. The experience taught me about leadership, perseverance, and the importance of building great teams. Though the startup was eventually acquired, I learned invaluable lessons about entrepreneurship."
        ],
        ContentSource.JOURNAL: [
            "Today I graduated from Stanford with my Master's degree. Looking back, I'm amazed at how much I've grown both personally and professionally. The advanced courses in artificial intelligence opened up new possibilities I never imagined.",
            "Emma was born today! Holding her for the first time, I felt a profound sense of responsibility and love. Mary and I are exhausted but overjoyed. This little person has already changed our perspective on everything.",
            "I just finished writing the last chapter of my novel. It's been three years of writing in the early mornings before work, but I finally did it. The story explores themes of technology and humanity - subjects close to my heart."
        ]
    }
    
    print("Automatic Biography Generation System Demo")
    print("=" * 55)
    
    # Initialize biography generator
    generator = BiographyGenerator()
    
    # Generate biography
    biography = await generator.generate_biography(
        person_profile=person,
        content_sources=content_sources,
        style=BiographyStyle.CHRONOLOGICAL
    )
    
    print(f"Biography generated for: {person.name}")
    print(f"Generation time: {biography.generation_time:.2f} seconds")
    print(f"Word count: {biography.word_count}")
    print(f"Chapters: {len(biography.chapters)}")
    print(f"Completeness score: {biography.completeness_score:.2f}")
    print(f"Narrative flow score: {biography.narrative_flow_score:.2f}")
    print(f"Primary themes: {', '.join(biography.metadata['primary_themes'])}")
    
    # Export to markdown
    markdown_biography = await generator.export_biography(biography, "markdown")
    
    print("\n" + "=" * 55)
    print("GENERATED BIOGRAPHY (First 1000 characters):")
    print("=" * 55)
    print(markdown_biography[:1000] + "...")
    
    # Show chapter overview
    print("\n" + "=" * 55)
    print("CHAPTER OVERVIEW:")
    print("=" * 55)
    for i, chapter in enumerate(biography.chapters, 1):
        print(f"{i}. {chapter.title}")
        print(f"   - Word count: {chapter.word_count}")
        print(f"   - Events: {len(chapter.events)}")
        print(f"   - Themes: {', '.join(chapter.themes)}")
        if chapter.time_period[0]:
            print(f"   - Time period: {chapter.time_period[0]} to {chapter.time_period[1] or 'present'}")
        print()

if __name__ == "__main__":
    asyncio.run(main())