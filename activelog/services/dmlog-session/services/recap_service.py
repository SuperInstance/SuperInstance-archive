"""
Session Recap Generator Service

Automatically generates comprehensive session recaps from transcripts, notes, highlights,
and other session data using AI and pattern recognition.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict, Counter
import re
import statistics

from ..models.base import BaseSessionModel, SessionHighlight, HighlightType
from ..models.session import SessionSchema, SessionNote, SessionParticipant, TranscriptionSegment
from ..config import AI_CONFIG, RECAP_CONFIG


@dataclass
class RecapSection:
    title: str
    content: str
    importance: float
    timestamp_range: Tuple[float, float]
    participants: List[str]
    highlights: List[SessionHighlight]


@dataclass
class SessionSummary:
    session_id: str
    generated_at: datetime
    duration_minutes: int
    participant_count: int
    total_words: int
    key_moments: List[SessionHighlight]
    participant_stats: Dict[str, Dict[str, Any]]
    session_flow: List[RecapSection]
    narrative_summary: str
    action_summary: str
    character_developments: Dict[str, str]
    plot_progression: str
    next_session_hooks: List[str]


class TranscriptAnalyzer:
    """Analyzes transcription data for recap generation"""
    
    def __init__(self):
        # Patterns for different types of content
        self.combat_patterns = [
            r"\b(?:roll|rolled|attack|damage|hit|miss|initiative|AC|HP|health)\b",
            r"\b(?:spell|magic|cast|casting)\b",
            r"\b(?:sword|bow|arrow|weapon|fight|fighting)\b"
        ]
        
        self.roleplay_patterns = [
            r"\b(?:says?|asks?|whispers?|shouts?|tells?)\b",
            r"\b(?:persuasion|deception|insight|investigation)\b",
            r"\b(?:character|personality|feeling|emotion)\b"
        ]
        
        self.exploration_patterns = [
            r"\b(?:look|looks|search|searching|examine|find|found)\b",
            r"\b(?:room|door|chest|treasure|hidden|secret)\b",
            r"\b(?:perception|investigation|stealth)\b"
        ]
        
        self.story_patterns = [
            r"\b(?:quest|mission|objective|goal)\b",
            r"\b(?:NPC|villain|enemy|ally|friend)\b",
            r"\b(?:plot|story|mystery|secret|reveal)\b"
        ]
    
    async def analyze_transcript_segments(self, segments: List[TranscriptionSegment]) -> Dict[str, Any]:
        """Analyze transcription segments for content patterns"""
        analysis = {
            "total_segments": len(segments),
            "total_duration": sum(seg.end_time - seg.start_time for seg in segments),
            "speaker_stats": defaultdict(lambda: {
                "segments": 0,
                "words": 0,
                "speaking_time": 0.0
            }),
            "content_types": {
                "combat": 0,
                "roleplay": 0,
                "exploration": 0,
                "story": 0,
                "other": 0
            },
            "key_phrases": [],
            "named_entities": [],
            "emotional_markers": []
        }
        
        for segment in segments:
            # Speaker statistics
            if segment.speaker_id:
                stats = analysis["speaker_stats"][segment.speaker_id]
                stats["segments"] += 1
                stats["words"] += len(segment.text.split())
                stats["speaking_time"] += segment.end_time - segment.start_time
            
            # Content type classification
            text_lower = segment.text.lower()
            content_type = self._classify_content_type(text_lower)
            analysis["content_types"][content_type] += 1
            
            # Extract key phrases and entities
            key_phrases = self._extract_key_phrases(segment.text)
            analysis["key_phrases"].extend(key_phrases)
            
            entities = self._extract_named_entities(segment.text)
            analysis["named_entities"].extend(entities)
            
            # Emotional markers
            emotions = self._detect_emotional_markers(segment.text)
            analysis["emotional_markers"].extend(emotions)
        
        # Post-process aggregated data
        analysis["key_phrases"] = self._get_most_common_phrases(analysis["key_phrases"])
        analysis["named_entities"] = list(set(analysis["named_entities"]))
        
        return analysis
    
    def _classify_content_type(self, text: str) -> str:
        """Classify text content type based on patterns"""
        scores = {
            "combat": sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                         for pattern in self.combat_patterns),
            "roleplay": sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                           for pattern in self.roleplay_patterns),
            "exploration": sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                              for pattern in self.exploration_patterns),
            "story": sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                        for pattern in self.story_patterns)
        }
        
        if max(scores.values()) == 0:
            return "other"
        
        return max(scores, key=scores.get)
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text"""
        # Simple implementation - in production, use NLP library
        phrases = []
        
        # Look for quoted speech
        quoted_matches = re.findall(r'"([^"]+)"', text)
        phrases.extend(quoted_matches)
        
        # Look for character names (capitalized words)
        name_matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        phrases.extend(name_matches)
        
        # Look for dice roll mentions
        dice_matches = re.findall(r'\bd\d+|\b\d+d\d+', text, re.IGNORECASE)
        phrases.extend(dice_matches)
        
        return phrases
    
    def _extract_named_entities(self, text: str) -> List[str]:
        """Extract named entities (characters, places, items)"""
        # Simple pattern-based extraction
        entities = []
        
        # Proper nouns (simplified)
        proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        entities.extend(proper_nouns)
        
        return entities
    
    def _detect_emotional_markers(self, text: str) -> List[str]:
        """Detect emotional content in text"""
        emotional_words = [
            "excited", "happy", "sad", "angry", "frustrated", "confused",
            "surprised", "shocked", "worried", "relieved", "disappointed",
            "proud", "embarrassed", "scared", "brave", "determined"
        ]
        
        markers = []
        text_lower = text.lower()
        
        for word in emotional_words:
            if word in text_lower:
                markers.append(word)
        
        return markers
    
    def _get_most_common_phrases(self, phrases: List[str], top_n: int = 20) -> List[Tuple[str, int]]:
        """Get most common phrases"""
        phrase_counts = Counter(phrases)
        return phrase_counts.most_common(top_n)


class NarrativeGenerator:
    """Generates narrative summaries from session data"""
    
    def __init__(self):
        self.session_openers = [
            "The session began with",
            "Our adventurers started by",
            "The party found themselves",
            "As the session opened,"
        ]
        
        self.transition_phrases = [
            "Following this,",
            "The group then",
            "After some discussion,",
            "Moving forward,",
            "Subsequently,",
            "Next,"
        ]
        
        self.conclusion_phrases = [
            "The session concluded with",
            "By the end of the session,",
            "As we wrapped up,",
            "The evening ended on"
        ]
    
    async def generate_narrative_summary(self, session: SessionSchema,
                                       transcript_analysis: Dict[str, Any],
                                       highlights: List[SessionHighlight],
                                       notes: List[SessionNote]) -> str:
        """Generate a narrative summary of the session"""
        
        # Build narrative sections
        sections = []
        
        # Opening
        opening = await self._generate_opening_section(session, transcript_analysis)
        sections.append(opening)
        
        # Main events (from highlights and notes)
        main_events = await self._generate_main_events_section(highlights, notes)
        sections.extend(main_events)
        
        # Character moments
        character_section = await self._generate_character_section(transcript_analysis)
        if character_section:
            sections.append(character_section)
        
        # Conclusion
        conclusion = await self._generate_conclusion_section(highlights, notes)
        sections.append(conclusion)
        
        return " ".join(sections)
    
    async def _generate_opening_section(self, session: SessionSchema,
                                      analysis: Dict[str, Any]) -> str:
        """Generate opening paragraph"""
        opener = "The session began with"
        
        # Determine session focus from content types
        content_types = analysis["content_types"]
        dominant_type = max(content_types, key=content_types.get)
        
        participant_count = len(session.participants)
        duration = analysis["total_duration"] / 60  # Convert to minutes
        
        if dominant_type == "combat":
            focus = "intense battles and tactical encounters"
        elif dominant_type == "roleplay":
            focus = "rich character interactions and dialogue"
        elif dominant_type == "exploration":
            focus = "discovery and investigation"
        elif dominant_type == "story":
            focus = "significant plot developments"
        else:
            focus = "varied adventures and experiences"
        
        return f"{opener} {participant_count} players engaging in {focus} over approximately {duration:.0f} minutes."
    
    async def _generate_main_events_section(self, highlights: List[SessionHighlight],
                                          notes: List[SessionNote]) -> List[str]:
        """Generate main events sections from highlights and notes"""
        sections = []
        
        # Sort events by timestamp
        all_events = []
        
        for highlight in highlights:
            all_events.append({
                "timestamp": highlight.timestamp,
                "type": "highlight",
                "content": highlight,
                "importance": self._get_highlight_importance(highlight.highlight_type)
            })
        
        for note in notes:
            all_events.append({
                "timestamp": note.timestamp,
                "type": "note", 
                "content": note,
                "importance": 0.7  # Default importance for notes
            })
        
        # Sort by timestamp and importance
        all_events.sort(key=lambda x: (x["timestamp"], -x["importance"]))
        
        # Group related events
        event_groups = self._group_related_events(all_events)
        
        # Generate narrative for each group
        for group in event_groups:
            section = await self._generate_event_group_narrative(group)
            if section:
                sections.append(section)
        
        return sections
    
    def _get_highlight_importance(self, highlight_type: HighlightType) -> float:
        """Get importance score for highlight type"""
        importance_map = {
            HighlightType.COMBAT_START: 0.9,
            HighlightType.CRITICAL_SUCCESS: 0.95,
            HighlightType.CRITICAL_FAILURE: 0.8,
            HighlightType.CHARACTER_MOMENT: 0.85,
            HighlightType.PLOT_REVELATION: 0.98,
            HighlightType.FUNNY_MOMENT: 0.7,
            HighlightType.DRAMATIC_MOMENT: 0.9,
            HighlightType.PUZZLE_SOLVED: 0.8,
            HighlightType.NPC_INTERACTION: 0.75
        }
        return importance_map.get(highlight_type, 0.6)
    
    def _group_related_events(self, events: List[Dict[str, Any]],
                             time_threshold: float = 300.0) -> List[List[Dict[str, Any]]]:
        """Group events that are close in time"""
        if not events:
            return []
        
        groups = []
        current_group = [events[0]]
        
        for event in events[1:]:
            # Check if this event should be grouped with the current group
            last_event_time = current_group[-1]["timestamp"]
            
            if event["timestamp"] - last_event_time <= time_threshold:
                current_group.append(event)
            else:
                groups.append(current_group)
                current_group = [event]
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    async def _generate_event_group_narrative(self, event_group: List[Dict[str, Any]]) -> str:
        """Generate narrative for a group of related events"""
        if not event_group:
            return ""
        
        # Determine the primary event type in the group
        event_types = [event["content"].highlight_type.value if event["type"] == "highlight" 
                      else "note" for event in event_group]
        primary_type = max(set(event_types), key=event_types.count)
        
        # Generate appropriate transition
        transition = "Meanwhile," if len(event_group) > 1 else "Next,"
        
        # Generate content based on primary type
        if primary_type == "combat_start":
            return f"{transition} the party engaged in combat, facing challenging encounters that tested their tactical skills."
        elif primary_type == "critical_success":
            return f"{transition} the adventurers achieved remarkable success, with critical moments that significantly advanced their goals."
        elif primary_type == "character_moment":
            return f"{transition} meaningful character development occurred, with party members revealing important aspects of their personalities and backgrounds."
        elif primary_type == "plot_revelation":
            return f"{transition} crucial plot information was revealed, changing the party's understanding of their situation."
        elif primary_type == "funny_moment":
            return f"{transition} the session featured memorable humorous moments that brought levity to the adventure."
        else:
            # Generic event description
            event_count = len(event_group)
            return f"{transition} several important events unfolded, including {event_count} notable moments that shaped the session's direction."
    
    async def _generate_character_section(self, analysis: Dict[str, Any]) -> Optional[str]:
        """Generate character-focused section"""
        speaker_stats = analysis["speaker_stats"]
        
        if not speaker_stats:
            return None
        
        # Find most active speakers
        active_speakers = sorted(
            speaker_stats.items(),
            key=lambda x: x[1]["speaking_time"],
            reverse=True
        )[:3]  # Top 3 speakers
        
        if not active_speakers:
            return None
        
        speaker_names = [speaker[0] for speaker in active_speakers]
        
        if len(speaker_names) == 1:
            return f"The session featured significant contributions from {speaker_names[0]}, who drove much of the roleplay and decision-making."
        elif len(speaker_names) == 2:
            return f"Both {speaker_names[0]} and {speaker_names[1]} were particularly active in driving the narrative forward through their character interactions."
        else:
            return f"The roleplay was particularly rich, with {', '.join(speaker_names[:-1])}, and {speaker_names[-1]} all contributing memorable character moments."
    
    async def _generate_conclusion_section(self, highlights: List[SessionHighlight],
                                         notes: List[SessionNote]) -> str:
        """Generate conclusion paragraph"""
        conclusion_base = "The session concluded with"
        
        # Look for session-ending highlights
        if highlights:
            last_highlight = max(highlights, key=lambda h: h.timestamp)
            if last_highlight.highlight_type == HighlightType.PLOT_REVELATION:
                return f"{conclusion_base} a major plot revelation that sets up exciting developments for future sessions."
            elif last_highlight.highlight_type == HighlightType.COMBAT_START:
                return f"{conclusion_base} the party entering combat, creating a dramatic cliffhanger for next time."
            elif last_highlight.highlight_type == HighlightType.CHARACTER_MOMENT:
                return f"{conclusion_base} meaningful character development that deepened the party's bonds."
        
        return f"{conclusion_base} the party making progress on their objectives and setting up new challenges to tackle in future sessions."


class RecapGeneratorService:
    """Main recap generation service"""
    
    def __init__(self):
        self.transcript_analyzer = TranscriptAnalyzer()
        self.narrative_generator = NarrativeGenerator()
        self.generated_recaps: Dict[str, SessionSummary] = {}
    
    async def generate_session_recap(self, session: SessionSchema,
                                   transcription_segments: List[TranscriptionSegment],
                                   highlights: List[SessionHighlight],
                                   notes: List[SessionNote]) -> SessionSummary:
        """Generate comprehensive session recap"""
        
        # Analyze transcript data
        transcript_analysis = await self.transcript_analyzer.analyze_transcript_segments(
            transcription_segments
        )
        
        # Generate narrative summary
        narrative_summary = await self.narrative_generator.generate_narrative_summary(
            session, transcript_analysis, highlights, notes
        )
        
        # Generate action summary
        action_summary = await self._generate_action_summary(highlights, transcript_analysis)
        
        # Extract character developments
        character_developments = await self._extract_character_developments(
            transcript_analysis, highlights, notes
        )
        
        # Generate plot progression summary
        plot_progression = await self._generate_plot_progression(highlights, notes)
        
        # Generate next session hooks
        next_session_hooks = await self._generate_next_session_hooks(highlights, notes)
        
        # Create session flow
        session_flow = await self._create_session_flow(
            transcription_segments, highlights, notes
        )
        
        # Calculate session statistics
        duration_minutes = int(transcript_analysis["total_duration"] / 60)
        total_words = sum(
            stats["words"] for stats in transcript_analysis["speaker_stats"].values()
        )
        
        # Create comprehensive summary
        summary = SessionSummary(
            session_id=session.id,
            generated_at=datetime.utcnow(),
            duration_minutes=duration_minutes,
            participant_count=len(session.participants),
            total_words=total_words,
            key_moments=highlights,
            participant_stats=dict(transcript_analysis["speaker_stats"]),
            session_flow=session_flow,
            narrative_summary=narrative_summary,
            action_summary=action_summary,
            character_developments=character_developments,
            plot_progression=plot_progression,
            next_session_hooks=next_session_hooks
        )
        
        # Store generated recap
        self.generated_recaps[session.id] = summary
        
        return summary
    
    async def _generate_action_summary(self, highlights: List[SessionHighlight],
                                     analysis: Dict[str, Any]) -> str:
        """Generate action-focused summary"""
        action_items = []
        
        # Combat actions
        combat_highlights = [h for h in highlights if h.highlight_type in [
            HighlightType.COMBAT_START, HighlightType.CRITICAL_SUCCESS, HighlightType.CRITICAL_FAILURE
        ]]
        
        if combat_highlights:
            action_items.append(f"Engaged in {len(combat_highlights)} significant combat encounters")
        
        # Problem solving
        puzzle_highlights = [h for h in highlights if h.highlight_type == HighlightType.PUZZLE_SOLVED]
        if puzzle_highlights:
            action_items.append(f"Solved {len(puzzle_highlights)} puzzles or challenges")
        
        # NPC interactions
        npc_highlights = [h for h in highlights if h.highlight_type == HighlightType.NPC_INTERACTION]
        if npc_highlights:
            action_items.append(f"Had {len(npc_highlights)} significant NPC interactions")
        
        # Content type analysis
        content_types = analysis["content_types"]
        if content_types["exploration"] > content_types["combat"]:
            action_items.append("Focused primarily on exploration and discovery")
        elif content_types["roleplay"] > content_types["combat"]:
            action_items.append("Emphasized character interaction and roleplay")
        
        if not action_items:
            action_items.append("Engaged in varied activities throughout the session")
        
        return ". ".join(action_items) + "."
    
    async def _extract_character_developments(self, analysis: Dict[str, Any],
                                            highlights: List[SessionHighlight],
                                            notes: List[SessionNote]) -> Dict[str, str]:
        """Extract character development moments"""
        developments = {}
        
        # From highlights
        character_highlights = [h for h in highlights if h.highlight_type == HighlightType.CHARACTER_MOMENT]
        
        for highlight in character_highlights:
            if highlight.description:
                # Extract character name from description (simplified)
                words = highlight.description.split()
                for word in words:
                    if word[0].isupper() and len(word) > 2:
                        developments[word] = highlight.description
                        break
        
        # From speaker analysis
        emotional_markers = analysis.get("emotional_markers", [])
        if emotional_markers:
            most_emotional = max(set(emotional_markers), key=emotional_markers.count)
            developments["Party"] = f"The session featured significant {most_emotional} moments that brought the characters closer together."
        
        return developments
    
    async def _generate_plot_progression(self, highlights: List[SessionHighlight],
                                       notes: List[SessionNote]) -> str:
        """Generate plot progression summary"""
        plot_elements = []
        
        # Plot revelations from highlights
        plot_highlights = [h for h in highlights if h.highlight_type == HighlightType.PLOT_REVELATION]
        
        if plot_highlights:
            plot_elements.append(f"Discovered {len(plot_highlights)} crucial plot revelations")
        
        # Important notes that might indicate plot progression
        important_notes = [n for n in notes if len(n.content) > 100]  # Longer notes likely more important
        
        if important_notes:
            plot_elements.append(f"Recorded {len(important_notes)} significant story developments")
        
        if not plot_elements:
            plot_elements.append("Made steady progress on ongoing storylines")
        
        return ". ".join(plot_elements) + "."
    
    async def _generate_next_session_hooks(self, highlights: List[SessionHighlight],
                                         notes: List[SessionNote]) -> List[str]:
        """Generate hooks for next session"""
        hooks = []
        
        # Look for unresolved elements in highlights
        for highlight in highlights[-3:]:  # Last few highlights
            if highlight.highlight_type == HighlightType.COMBAT_START:
                hooks.append("Resolve the ongoing combat encounter")
            elif highlight.highlight_type == HighlightType.PLOT_REVELATION:
                hooks.append("Explore the implications of recent revelations")
            elif highlight.description and "?" in highlight.description:
                hooks.append("Address the questions raised during the session")
        
        # Look for incomplete elements in notes
        for note in notes[-2:]:  # Last couple notes
            if any(word in note.content.lower() for word in ["next", "later", "tomorrow", "continue"]):
                hooks.append("Continue the activities planned at session end")
        
        # Default hooks if none found
        if not hooks:
            hooks = [
                "Continue the party's current objectives",
                "Explore new opportunities that emerged from this session",
                "Address any unfinished business from today's adventures"
            ]
        
        return hooks[:3]  # Limit to 3 hooks
    
    async def _create_session_flow(self, segments: List[TranscriptionSegment],
                                 highlights: List[SessionHighlight],
                                 notes: List[SessionNote]) -> List[RecapSection]:
        """Create chronological session flow"""
        flow = []
        
        if not segments:
            return flow
        
        # Divide session into time-based sections (e.g., 30-minute chunks)
        section_duration = RECAP_CONFIG.get("section_duration_minutes", 30) * 60  # Convert to seconds
        session_start = min(seg.start_time for seg in segments)
        session_end = max(seg.end_time for seg in segments)
        
        current_time = session_start
        section_number = 1
        
        while current_time < session_end:
            section_end = min(current_time + section_duration, session_end)
            
            # Get content for this time range
            section_segments = [
                seg for seg in segments 
                if seg.start_time >= current_time and seg.start_time < section_end
            ]
            section_highlights = [
                h for h in highlights
                if h.timestamp >= current_time and h.timestamp < section_end
            ]
            section_notes = [
                n for n in notes
                if n.timestamp >= current_time and n.timestamp < section_end
            ]
            
            if section_segments:  # Only create section if there's content
                # Generate section summary
                section_summary = await self._generate_section_summary(
                    section_segments, section_highlights, section_notes
                )
                
                # Get participants for this section
                participants = list(set(seg.speaker_id for seg in section_segments if seg.speaker_id))
                
                # Calculate importance
                importance = len(section_highlights) * 0.3 + len(section_notes) * 0.2 + len(section_segments) * 0.01
                
                section = RecapSection(
                    title=f"Session Part {section_number} ({int((current_time - session_start) / 60)}min - {int((section_end - session_start) / 60)}min)",
                    content=section_summary,
                    importance=importance,
                    timestamp_range=(current_time, section_end),
                    participants=participants,
                    highlights=section_highlights
                )
                
                flow.append(section)
                section_number += 1
            
            current_time = section_end
        
        return flow
    
    async def _generate_section_summary(self, segments: List[TranscriptionSegment],
                                      highlights: List[SessionHighlight],
                                      notes: List[SessionNote]) -> str:
        """Generate summary for a session section"""
        summary_parts = []
        
        # Activity type analysis
        if segments:
            text_combined = " ".join(seg.text for seg in segments)
            content_type = self.transcript_analyzer._classify_content_type(text_combined.lower())
            
            type_descriptions = {
                "combat": "The party engaged in combat encounters",
                "roleplay": "Character interactions and dialogue were the focus",
                "exploration": "The group explored and investigated their surroundings",
                "story": "Significant story developments occurred",
                "other": "Various activities took place"
            }
            
            summary_parts.append(type_descriptions.get(content_type, "Activities occurred"))
        
        # Highlight integration
        if highlights:
            highlight_types = [h.highlight_type.value for h in highlights]
            unique_types = list(set(highlight_types))
            
            if len(unique_types) == 1:
                summary_parts.append(f"featuring notable {unique_types[0].replace('_', ' ')} moments")
            else:
                summary_parts.append(f"with {len(highlights)} memorable moments")
        
        # Notes integration
        if notes:
            summary_parts.append(f"resulting in {len(notes)} important notes")
        
        if not summary_parts:
            summary_parts.append("Session content occurred during this period")
        
        return ". ".join(summary_parts) + "."
    
    async def get_recap_summary(self, session_id: str) -> Optional[SessionSummary]:
        """Get generated recap summary"""
        return self.generated_recaps.get(session_id)
    
    async def export_recap_formats(self, session_id: str) -> Dict[str, str]:
        """Export recap in different formats"""
        summary = self.generated_recaps.get(session_id)
        if not summary:
            return {}
        
        formats = {}
        
        # Markdown format
        formats["markdown"] = await self._export_markdown(summary)
        
        # Plain text format
        formats["text"] = await self._export_plain_text(summary)
        
        # JSON format
        formats["json"] = await self._export_json(summary)
        
        return formats
    
    async def _export_markdown(self, summary: SessionSummary) -> str:
        """Export recap as markdown"""
        md = f"# Session Recap - {summary.generated_at.strftime('%Y-%m-%d')}\n\n"
        
        md += f"**Duration:** {summary.duration_minutes} minutes  \n"
        md += f"**Participants:** {summary.participant_count}  \n"
        md += f"**Total Words:** {summary.total_words:,}  \n\n"
        
        md += "## Narrative Summary\n\n"
        md += f"{summary.narrative_summary}\n\n"
        
        md += "## Action Summary\n\n"
        md += f"{summary.action_summary}\n\n"
        
        if summary.character_developments:
            md += "## Character Developments\n\n"
            for character, development in summary.character_developments.items():
                md += f"**{character}:** {development}\n\n"
        
        md += "## Plot Progression\n\n"
        md += f"{summary.plot_progression}\n\n"
        
        if summary.next_session_hooks:
            md += "## Next Session Hooks\n\n"
            for hook in summary.next_session_hooks:
                md += f"- {hook}\n"
            md += "\n"
        
        if summary.key_moments:
            md += "## Key Moments\n\n"
            for moment in summary.key_moments:
                timestamp_min = int(moment.timestamp / 60)
                md += f"**{timestamp_min}min:** {moment.title}\n"
                if moment.description:
                    md += f"  {moment.description}\n"
                md += "\n"
        
        return md
    
    async def _export_plain_text(self, summary: SessionSummary) -> str:
        """Export recap as plain text"""
        text = f"SESSION RECAP - {summary.generated_at.strftime('%Y-%m-%d')}\n"
        text += "=" * 50 + "\n\n"
        
        text += f"Duration: {summary.duration_minutes} minutes\n"
        text += f"Participants: {summary.participant_count}\n"
        text += f"Total Words: {summary.total_words:,}\n\n"
        
        text += "NARRATIVE SUMMARY\n"
        text += "-" * 20 + "\n"
        text += f"{summary.narrative_summary}\n\n"
        
        text += "ACTION SUMMARY\n"
        text += "-" * 20 + "\n"
        text += f"{summary.action_summary}\n\n"
        
        text += "PLOT PROGRESSION\n"
        text += "-" * 20 + "\n"
        text += f"{summary.plot_progression}\n\n"
        
        if summary.next_session_hooks:
            text += "NEXT SESSION HOOKS\n"
            text += "-" * 20 + "\n"
            for hook in summary.next_session_hooks:
                text += f"- {hook}\n"
            text += "\n"
        
        return text
    
    async def _export_json(self, summary: SessionSummary) -> str:
        """Export recap as JSON"""
        data = {
            "session_id": summary.session_id,
            "generated_at": summary.generated_at.isoformat(),
            "duration_minutes": summary.duration_minutes,
            "participant_count": summary.participant_count,
            "total_words": summary.total_words,
            "narrative_summary": summary.narrative_summary,
            "action_summary": summary.action_summary,
            "plot_progression": summary.plot_progression,
            "character_developments": summary.character_developments,
            "next_session_hooks": summary.next_session_hooks,
            "key_moments": [
                {
                    "timestamp": moment.timestamp,
                    "title": moment.title,
                    "description": moment.description,
                    "type": moment.highlight_type.value
                }
                for moment in summary.key_moments
            ],
            "participant_stats": summary.participant_stats
        }
        
        return json.dumps(data, indent=2)