"""
Session notes service with timestamp linking.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid
import re

try:
    import spacy
    from spacy.matcher import Matcher
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not available - advanced note features disabled")

from ..config import Config
from ..models.session import SessionSchema, SessionNote, TranscriptionSegment
from ..models.base import SessionHighlight, HighlightType

logger = logging.getLogger(__name__)

class NoteTemplateService:
    """Service for managing note templates."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize default note templates."""
        
        return {
            "character_moment": {
                "title": "Character Moment - {character_name}",
                "content": "Character: {character_name}\nMoment: {description}\nContext: {context}",
                "tags": ["character", "roleplay"],
                "category": "character"
            },
            
            "plot_development": {
                "title": "Plot Development - {event}",
                "content": "Event: {event}\nConsequences: {consequences}\nNext Steps: {next_steps}",
                "tags": ["plot", "story"],
                "category": "plot"
            },
            
            "combat_encounter": {
                "title": "Combat: {encounter_name}",
                "content": "Enemies: {enemies}\nLocation: {location}\nOutcome: {outcome}\nNotable Events: {events}",
                "tags": ["combat", "encounter"],
                "category": "combat"
            },
            
            "npc_interaction": {
                "title": "NPC: {npc_name}",
                "content": "NPC: {npc_name}\nLocation: {location}\nPersonality: {personality}\nImportant Info: {info}",
                "tags": ["npc", "social"],
                "category": "npc"
            },
            
            "discovery": {
                "title": "Discovery - {item}",
                "content": "Discovery: {item}\nLocation: {location}\nSignificance: {significance}\nFollow-up: {followup}",
                "tags": ["discovery", "lore"],
                "category": "discovery"
            },
            
            "rule_clarification": {
                "title": "Rule Clarification - {rule}",
                "content": "Rule: {rule}\nSituation: {situation}\nRuling: {ruling}\nReference: {reference}",
                "tags": ["rules", "mechanics"],
                "category": "rules"
            },
            
            "session_recap": {
                "title": "Session {session_number} Recap",
                "content": "Key Events:\n{events}\n\nCharacter Highlights:\n{character_highlights}\n\nNext Session:\n{next_session}",
                "tags": ["recap", "summary"],
                "category": "recap"
            }
        }
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Get note template by name."""
        return self.templates.get(template_name)
    
    def apply_template(
        self,
        template_name: str,
        variables: Dict[str, Any],
        created_by: str,
        timestamp: Optional[float] = None
    ) -> Optional[SessionNote]:
        """Apply template with variables to create a note."""
        
        template = self.get_template(template_name)
        if not template:
            return None
        
        # Replace variables in template
        title = template["title"].format(**variables)
        content = template["content"].format(**variables)
        
        note = SessionNote(
            title=title,
            content=content,
            note_type=template["category"],
            tags=template["tags"].copy(),
            category=template["category"],
            timestamp=timestamp,
            created_by=created_by
        )
        
        return note

class NoteLinkingService:
    """Service for linking notes to transcription and other content."""
    
    def __init__(self, config: Config):
        self.config = config
        self.nlp = None
        self.matcher = None
        
        if SPACY_AVAILABLE:
            try:
                # Load spaCy model
                self.nlp = spacy.load("en_core_web_sm")
                self.matcher = Matcher(self.nlp.vocab)
                self._setup_patterns()
            except OSError:
                logger.warning("spaCy English model not found - install with: python -m spacy download en_core_web_sm")
                SPACY_AVAILABLE = False
    
    def _setup_patterns(self):
        """Setup spaCy patterns for entity recognition."""
        
        if not self.matcher:
            return
        
        # Character name patterns
        character_patterns = [
            [{"POS": "PROPN", "OP": "+"}, {"LOWER": {"IN": ["says", "does", "casts", "attacks"]}}],
            [{"LOWER": "as"}, {"POS": "PROPN", "OP": "+"}],
        ]
        
        # Combat patterns
        combat_patterns = [
            [{"LOWER": {"IN": ["rolls", "roll"]}}, {"LIKE_NUM": True, "OP": "?"}, {"LOWER": "d"}, {"LIKE_NUM": True}],
            [{"LOWER": {"IN": ["attacks", "attack"]}}, {"POS": "PROPN", "OP": "?"}],
            [{"LOWER": {"IN": ["casts", "cast"]}}, {"POS": "PROPN", "OP": "+"}],
        ]
        
        # Location patterns
        location_patterns = [
            [{"LOWER": {"IN": ["enters", "enter", "goes", "go", "travels", "travel"]}}, {"LOWER": "to"}, {"POS": "PROPN", "OP": "+"}],
            [{"LOWER": {"IN": ["in", "at"]}}, {"LOWER": "the"}, {"POS": "PROPN", "OP": "+"}],
        ]
        
        self.matcher.add("CHARACTER", character_patterns)
        self.matcher.add("COMBAT", combat_patterns)
        self.matcher.add("LOCATION", location_patterns)
    
    def link_note_to_transcription(
        self,
        note: SessionNote,
        transcription_segments: List[TranscriptionSegment],
        time_window: float = 300.0  # 5 minutes
    ) -> List[str]:
        """Link note to relevant transcription segments."""
        
        if not note.timestamp:
            return []
        
        linked_segments = []
        
        # Find segments within time window
        for segment in transcription_segments:
            time_diff = abs(segment.start_time - note.timestamp)
            
            if time_diff <= time_window:
                # Check content relevance
                relevance_score = self._calculate_relevance(note, segment)
                
                if relevance_score > 0.3:  # Threshold for relevance
                    linked_segments.append(segment.id)
        
        note.linked_transcription = linked_segments
        return linked_segments
    
    def _calculate_relevance(self, note: SessionNote, segment: TranscriptionSegment) -> float:
        """Calculate relevance score between note and transcription segment."""
        
        # Simple keyword matching
        note_words = set(note.title.lower().split() + note.content.lower().split())
        segment_words = set(segment.text.lower().split())
        
        # Calculate overlap
        common_words = note_words.intersection(segment_words)
        total_words = len(note_words.union(segment_words))
        
        if total_words == 0:
            return 0.0
        
        basic_score = len(common_words) / total_words
        
        # Boost score for certain patterns
        if SPACY_AVAILABLE and self.nlp:
            enhanced_score = self._calculate_nlp_relevance(note, segment)
            return max(basic_score, enhanced_score)
        
        return basic_score
    
    def _calculate_nlp_relevance(self, note: SessionNote, segment: TranscriptionSegment) -> float:
        """Calculate relevance using NLP analysis."""
        
        if not self.nlp:
            return 0.0
        
        try:
            # Process texts
            note_doc = self.nlp(f"{note.title} {note.content}")
            segment_doc = self.nlp(segment.text)
            
            # Compare entities
            note_entities = set(ent.text.lower() for ent in note_doc.ents)
            segment_entities = set(ent.text.lower() for ent in segment_doc.ents)
            
            entity_overlap = len(note_entities.intersection(segment_entities))
            entity_total = len(note_entities.union(segment_entities))
            
            entity_score = entity_overlap / entity_total if entity_total > 0 else 0
            
            # Calculate semantic similarity
            similarity = note_doc.similarity(segment_doc)
            
            # Combine scores
            return max(entity_score, similarity)
            
        except Exception as e:
            logger.warning(f"NLP relevance calculation failed: {e}")
            return 0.0
    
    def extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using NLP."""
        
        entities = {
            "characters": [],
            "locations": [],
            "items": [],
            "spells": [],
            "creatures": []
        }
        
        if not SPACY_AVAILABLE or not self.nlp:
            return entities
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    entities["characters"].append(ent.text)
                elif ent.label_ in ["GPE", "LOC", "FAC"]:
                    entities["locations"].append(ent.text)
                elif ent.label_ == "PRODUCT":
                    entities["items"].append(ent.text)
            
            # Use matcher for specific patterns
            matches = self.matcher(doc)
            for match_id, start, end in matches:
                span = doc[start:end]
                label = self.nlp.vocab.strings[match_id]
                
                if label == "CHARACTER":
                    entities["characters"].append(span.text)
                elif label == "LOCATION":
                    entities["locations"].append(span.text)
            
            # Remove duplicates
            for key in entities:
                entities[key] = list(set(entities[key]))
            
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
        
        return entities

class SessionNotesService:
    """Main session notes service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.template_service = NoteTemplateService()
        self.linking_service = NoteLinkingService(config)
        
        # Note storage (in production, this would be a database)
        self.session_notes: Dict[str, List[SessionNote]] = {}
    
    async def create_note(
        self,
        session_id: str,
        title: str,
        content: str,
        created_by: str,
        note_type: str = "general",
        timestamp: Optional[float] = None,
        tags: List[str] = None,
        template_name: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None
    ) -> SessionNote:
        """Create a new session note."""
        
        if template_name and template_variables:
            # Use template
            note = self.template_service.apply_template(
                template_name, template_variables, created_by, timestamp
            )
            if not note:
                raise ValueError(f"Template '{template_name}' not found")
        else:
            # Create regular note
            note = SessionNote(
                title=title,
                content=content,
                note_type=note_type,
                timestamp=timestamp,
                created_by=created_by,
                tags=tags or []
            )
        
        # Add to storage
        if session_id not in self.session_notes:
            self.session_notes[session_id] = []
        
        self.session_notes[session_id].append(note)
        
        logger.info(f"Note created for session {session_id}: {note.title}")
        return note
    
    async def update_note(
        self,
        session_id: str,
        note_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> Optional[SessionNote]:
        """Update an existing note."""
        
        note = self.get_note(session_id, note_id)
        if not note:
            return None
        
        # Update fields
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags
        if category is not None:
            note.category = category
        
        note.updated_at = datetime.utcnow()
        
        logger.info(f"Note updated: {note_id}")
        return note
    
    async def delete_note(self, session_id: str, note_id: str) -> bool:
        """Delete a note."""
        
        if session_id not in self.session_notes:
            return False
        
        notes = self.session_notes[session_id]
        original_length = len(notes)
        
        self.session_notes[session_id] = [n for n in notes if n.id != note_id]
        
        success = len(self.session_notes[session_id]) < original_length
        
        if success:
            logger.info(f"Note deleted: {note_id}")
        
        return success
    
    def get_note(self, session_id: str, note_id: str) -> Optional[SessionNote]:
        """Get a specific note."""
        
        if session_id not in self.session_notes:
            return None
        
        return next(
            (note for note in self.session_notes[session_id] if note.id == note_id),
            None
        )
    
    def get_session_notes(
        self,
        session_id: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search_query: Optional[str] = None,
        time_range: Optional[Tuple[float, float]] = None
    ) -> List[SessionNote]:
        """Get notes for a session with optional filtering."""
        
        if session_id not in self.session_notes:
            return []
        
        notes = self.session_notes[session_id]
        
        # Apply filters
        if category:
            notes = [n for n in notes if n.category == category]
        
        if tags:
            notes = [n for n in notes if any(tag in n.tags for tag in tags)]
        
        if search_query:
            query_lower = search_query.lower()
            notes = [
                n for n in notes
                if query_lower in n.title.lower() or query_lower in n.content.lower()
            ]
        
        if time_range:
            start_time, end_time = time_range
            notes = [
                n for n in notes
                if n.timestamp and start_time <= n.timestamp <= end_time
            ]
        
        # Sort by timestamp, then by creation time
        return sorted(
            notes,
            key=lambda x: (x.timestamp or 0, x.created_at),
            reverse=False
        )
    
    async def link_notes_to_transcription(
        self,
        session_id: str,
        transcription_segments: List[TranscriptionSegment]
    ) -> int:
        """Link all notes to relevant transcription segments."""
        
        if session_id not in self.session_notes:
            return 0
        
        linked_count = 0
        
        for note in self.session_notes[session_id]:
            if note.timestamp:
                linked_segments = self.linking_service.link_note_to_transcription(
                    note, transcription_segments
                )
                
                if linked_segments:
                    linked_count += 1
                    logger.debug(f"Note '{note.title}' linked to {len(linked_segments)} segments")
        
        logger.info(f"Linked {linked_count} notes to transcription")
        return linked_count
    
    async def auto_generate_notes(
        self,
        session: SessionSchema,
        transcription_segments: List[TranscriptionSegment],
        highlights: List[SessionHighlight] = None
    ) -> List[SessionNote]:
        """Auto-generate notes from transcription and highlights."""
        
        generated_notes = []
        
        # Generate notes from highlights
        if highlights:
            for highlight in highlights:
                note = await self._generate_note_from_highlight(
                    session, highlight, transcription_segments
                )
                if note:
                    generated_notes.append(note)
        
        # Generate notes from transcription patterns
        pattern_notes = await self._generate_notes_from_patterns(
            session, transcription_segments
        )
        generated_notes.extend(pattern_notes)
        
        # Add generated notes to session
        if session.id not in self.session_notes:
            self.session_notes[session.id] = []
        
        self.session_notes[session.id].extend(generated_notes)
        
        logger.info(f"Auto-generated {len(generated_notes)} notes")
        return generated_notes
    
    async def _generate_note_from_highlight(
        self,
        session: SessionSchema,
        highlight: SessionHighlight,
        transcription_segments: List[TranscriptionSegment]
    ) -> Optional[SessionNote]:
        """Generate a note from a highlight."""
        
        # Get transcription content around highlight
        relevant_segments = [
            seg for seg in transcription_segments
            if (highlight.timestamp <= seg.start_time <= highlight.timestamp + highlight.duration)
        ]
        
        if not relevant_segments:
            return None
        
        # Combine segment texts
        content_parts = []
        for segment in relevant_segments:
            speaker = segment.character_attribution or segment.speaker_name or "Unknown"
            content_parts.append(f"{speaker}: {segment.text}")
        
        content = "\n".join(content_parts)
        
        # Create note
        note = SessionNote(
            title=f"{highlight.highlight_type.value.title()}: {highlight.title}",
            content=f"{highlight.description}\n\n--- Transcript ---\n{content}",
            note_type=highlight.highlight_type.value,
            timestamp=highlight.timestamp,
            created_by="system",
            tags=[highlight.highlight_type.value, "auto-generated"],
            linked_highlights=[highlight.id]
        )
        
        return note
    
    async def _generate_notes_from_patterns(
        self,
        session: SessionSchema,
        transcription_segments: List[TranscriptionSegment]
    ) -> List[SessionNote]:
        """Generate notes from recognized patterns in transcription."""
        
        notes = []
        
        # Combine all transcription text
        all_text = " ".join(seg.text for seg in transcription_segments)
        
        # Extract entities
        entities = self.linking_service.extract_entities_from_text(all_text)
        
        # Generate character notes
        for character in entities["characters"]:
            character_segments = [
                seg for seg in transcription_segments
                if character.lower() in seg.text.lower()
            ]
            
            if len(character_segments) >= 3:  # At least 3 mentions
                note = SessionNote(
                    title=f"Character: {character}",
                    content=f"Character mentioned {len(character_segments)} times in session.",
                    note_type="character",
                    created_by="system",
                    tags=["character", "auto-generated", "entity-extraction"]
                )
                notes.append(note)
        
        # Generate location notes
        for location in entities["locations"]:
            location_segments = [
                seg for seg in transcription_segments
                if location.lower() in seg.text.lower()
            ]
            
            if len(location_segments) >= 2:  # At least 2 mentions
                note = SessionNote(
                    title=f"Location: {location}",
                    content=f"Location mentioned {len(location_segments)} times in session.",
                    note_type="location",
                    created_by="system",
                    tags=["location", "auto-generated", "entity-extraction"]
                )
                notes.append(note)
        
        return notes
    
    async def export_notes(
        self,
        session_id: str,
        format_type: str = "markdown",
        include_timestamps: bool = True,
        include_links: bool = True
    ) -> str:
        """Export session notes in various formats."""
        
        notes = self.get_session_notes(session_id)
        
        if format_type.lower() == "markdown":
            return self._export_markdown(notes, include_timestamps, include_links)
        elif format_type.lower() == "html":
            return self._export_html(notes, include_timestamps, include_links)
        elif format_type.lower() == "txt":
            return self._export_txt(notes, include_timestamps)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _export_markdown(
        self,
        notes: List[SessionNote],
        include_timestamps: bool,
        include_links: bool
    ) -> str:
        """Export notes as Markdown."""
        
        content = ["# Session Notes", ""]
        
        # Group notes by category
        categories = {}
        for note in notes:
            category = note.category or "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(note)
        
        for category, category_notes in categories.items():
            content.append(f"## {category.title()}")
            content.append("")
            
            for note in sorted(category_notes, key=lambda x: x.timestamp or 0):
                # Title with timestamp
                if include_timestamps and note.timestamp:
                    timestamp = self._format_timestamp(note.timestamp)
                    content.append(f"### {note.title} `[{timestamp}]`")
                else:
                    content.append(f"### {note.title}")
                
                content.append("")
                content.append(note.content)
                
                # Tags
                if note.tags:
                    tag_line = " ".join(f"`{tag}`" for tag in note.tags)
                    content.append(f"\n**Tags:** {tag_line}")
                
                # Links
                if include_links:
                    if note.linked_transcription:
                        content.append(f"\n**Linked Transcription:** {len(note.linked_transcription)} segments")
                    
                    if note.linked_highlights:
                        content.append(f"**Linked Highlights:** {len(note.linked_highlights)} highlights")
                
                content.append("")
                content.append("---")
                content.append("")
        
        return "\n".join(content)
    
    def _export_html(
        self,
        notes: List[SessionNote],
        include_timestamps: bool,
        include_links: bool
    ) -> str:
        """Export notes as HTML."""
        
        # Basic HTML template
        html = ["<html><head><title>Session Notes</title></head><body>"]
        html.append("<h1>Session Notes</h1>")
        
        # Group by category
        categories = {}
        for note in notes:
            category = note.category or "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(note)
        
        for category, category_notes in categories.items():
            html.append(f"<h2>{category.title()}</h2>")
            
            for note in sorted(category_notes, key=lambda x: x.timestamp or 0):
                html.append("<div class='note'>")
                
                # Title
                if include_timestamps and note.timestamp:
                    timestamp = self._format_timestamp(note.timestamp)
                    html.append(f"<h3>{note.title} <span class='timestamp'>[{timestamp}]</span></h3>")
                else:
                    html.append(f"<h3>{note.title}</h3>")
                
                # Content
                content_html = note.content.replace("\n", "<br>")
                html.append(f"<p>{content_html}</p>")
                
                # Tags
                if note.tags:
                    tag_spans = " ".join(f"<span class='tag'>{tag}</span>" for tag in note.tags)
                    html.append(f"<div class='tags'>Tags: {tag_spans}</div>")
                
                html.append("</div>")
        
        html.append("</body></html>")
        
        return "\n".join(html)
    
    def _export_txt(self, notes: List[SessionNote], include_timestamps: bool) -> str:
        """Export notes as plain text."""
        
        content = ["SESSION NOTES", "=" * 50, ""]
        
        for note in sorted(notes, key=lambda x: x.timestamp or 0):
            if include_timestamps and note.timestamp:
                timestamp = self._format_timestamp(note.timestamp)
                content.append(f"{note.title} [{timestamp}]")
            else:
                content.append(note.title)
            
            content.append("-" * len(note.title))
            content.append(note.content)
            
            if note.tags:
                content.append(f"Tags: {', '.join(note.tags)}")
            
            content.append("")
        
        return "\n".join(content)
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format timestamp for display."""
        hours = int(timestamp // 3600)
        minutes = int((timestamp % 3600) // 60)
        seconds = int(timestamp % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"