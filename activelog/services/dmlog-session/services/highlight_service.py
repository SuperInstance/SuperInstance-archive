"""
Highlight marking service for important session moments.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid
import numpy as np

try:
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    logging.warning("TextBlob not available - sentiment analysis disabled")

from ..config import Config
from ..models.base import SessionHighlight, HighlightType, AudioSegment
from ..models.session import SessionSchema, TranscriptionSegment

logger = logging.getLogger(__name__)

class HighlightDetectionService:
    """Service for automatically detecting highlights in session content."""
    
    def __init__(self, config: Config):
        self.config = config
        
        # Detection patterns
        self.combat_keywords = [
            "roll initiative", "attack", "damage", "hit", "miss", "crit", "critical",
            "saves", "saving throw", "spell attack", "armor class", "hit points"
        ]
        
        self.story_keywords = [
            "discovers", "reveals", "learns", "realizes", "finds out", "uncovers",
            "plot twist", "surprise", "shocking", "unexpected"
        ]
        
        self.character_keywords = [
            "character development", "backstory", "personal", "emotional", "feels",
            "relationship", "bonds", "connects", "trusts", "betrays"
        ]
        
        self.funny_keywords = [
            "laughter", "hilarious", "funny", "joke", "pun", "witty", "amusing",
            "ridiculous", "absurd", "comedic"
        ]
        
        self.rule_keywords = [
            "how does", "rule", "mechanics", "clarification", "ruling", "interpret",
            "page", "handbook", "manual", "reference"
        ]
    
    async def detect_highlights(
        self,
        session: SessionSchema,
        transcription_segments: List[TranscriptionSegment],
        audio_segments: List[AudioSegment] = None
    ) -> List[SessionHighlight]:
        """Detect highlights from transcription and audio data."""
        
        highlights = []
        
        # Detect different types of highlights
        combat_highlights = await self._detect_combat_highlights(transcription_segments)
        story_highlights = await self._detect_story_highlights(transcription_segments)
        character_highlights = await self._detect_character_highlights(transcription_segments)
        funny_highlights = await self._detect_funny_highlights(transcription_segments)
        rule_highlights = await self._detect_rule_highlights(transcription_segments)
        
        highlights.extend(combat_highlights)
        highlights.extend(story_highlights)
        highlights.extend(character_highlights)
        highlights.extend(funny_highlights)
        highlights.extend(rule_highlights)
        
        # Detect audio-based highlights
        if audio_segments:
            audio_highlights = await self._detect_audio_highlights(
                transcription_segments, audio_segments
            )
            highlights.extend(audio_highlights)
        
        # Remove overlapping highlights and rank by importance
        highlights = self._deduplicate_highlights(highlights)
        highlights = self._rank_highlights(highlights)
        
        # Set created_by for auto-detected highlights
        for highlight in highlights:
            highlight.created_by = "system"
        
        logger.info(f"Detected {len(highlights)} highlights")
        return highlights
    
    async def _detect_combat_highlights(
        self,
        segments: List[TranscriptionSegment]
    ) -> List[SessionHighlight]:
        """Detect combat-related highlights."""
        
        highlights = []
        
        for i, segment in enumerate(segments):
            text_lower = segment.text.lower()
            
            # Look for combat keywords
            combat_score = sum(1 for keyword in self.combat_keywords if keyword in text_lower)
            
            if combat_score >= 2:  # At least 2 combat keywords
                # Look for context around this segment
                context_segments = self._get_context_segments(segments, i, 3)
                context_text = " ".join(seg.text for seg in context_segments)
                
                # Determine specific combat moment
                if "critical" in text_lower or "nat 20" in text_lower:
                    title = "Critical Hit!"
                    description = "Natural 20 or critical hit rolled"
                elif "fumble" in text_lower or "nat 1" in text_lower:
                    title = "Critical Fumble!"
                    description = "Natural 1 or fumble rolled"
                elif any(word in text_lower for word in ["dies", "killed", "defeated"]):
                    title = "Enemy Defeated"
                    description = "Combat victory moment"
                else:
                    title = "Combat Moment"
                    description = "Significant combat action"
                
                highlight = SessionHighlight(
                    timestamp=segment.start_time,
                    duration=max(30, sum(seg.end_time - seg.start_time for seg in context_segments)),
                    highlight_type=HighlightType.COMBAT_HIGHLIGHT,
                    title=title,
                    description=f"{description}: {segment.text[:100]}...",
                    transcription_segments=[seg.id for seg in context_segments],
                    created_by="system"
                )
                
                highlights.append(highlight)
        
        return highlights
    
    async def _detect_story_highlights(
        self,
        segments: List[TranscriptionSegment]
    ) -> List[SessionHighlight]:
        """Detect story and plot-related highlights."""
        
        highlights = []
        
        for i, segment in enumerate(segments):
            text_lower = segment.text.lower()
            
            # Look for story keywords
            story_score = sum(1 for keyword in self.story_keywords if keyword in text_lower)
            
            if story_score >= 1:
                # Get context
                context_segments = self._get_context_segments(segments, i, 5)
                
                highlight = SessionHighlight(
                    timestamp=segment.start_time,
                    duration=60,  # 1 minute for story moments
                    highlight_type=HighlightType.STORY_BEAT,
                    title="Story Development",
                    description=f"Plot development: {segment.text[:100]}...",
                    transcription_segments=[seg.id for seg in context_segments],
                    created_by="system"
                )
                
                highlights.append(highlight)
        
        return highlights
    
    async def _detect_character_highlights(
        self,
        segments: List[TranscriptionSegment]
    ) -> List[SessionHighlight]:
        """Detect character development highlights."""
        
        highlights = []
        
        for i, segment in enumerate(segments):
            text_lower = segment.text.lower()
            
            # Look for character keywords
            character_score = sum(1 for keyword in self.character_keywords if keyword in text_lower)
            
            # Also look for emotional content using sentiment analysis
            emotion_score = 0
            if SENTIMENT_AVAILABLE:
                try:
                    blob = TextBlob(segment.text)
                    # Strong positive or negative sentiment indicates emotional moment
                    if abs(blob.sentiment.polarity) > 0.5:
                        emotion_score = 1
                except:
                    pass
            
            if character_score >= 1 or emotion_score >= 1:
                context_segments = self._get_context_segments(segments, i, 4)
                
                # Determine if character is speaking
                character_name = segment.character_attribution
                if character_name:
                    title = f"Character Moment: {character_name}"
                else:
                    title = "Character Development"
                
                highlight = SessionHighlight(
                    timestamp=segment.start_time,
                    duration=45,
                    highlight_type=HighlightType.CHARACTER_MOMENT,
                    title=title,
                    description=f"Character development: {segment.text[:100]}...",
                    transcription_segments=[seg.id for seg in context_segments],
                    created_by="system"
                )
                
                highlights.append(highlight)
        
        return highlights
    
    async def _detect_funny_highlights(
        self,
        segments: List[TranscriptionSegment]
    ) -> List[SessionHighlight]:
        """Detect funny moments."""
        
        highlights = []
        
        for i, segment in enumerate(segments):
            text_lower = segment.text.lower()
            
            # Look for funny keywords
            funny_score = sum(1 for keyword in self.funny_keywords if keyword in text_lower)
            
            # Look for patterns that indicate laughter or humor
            laughter_patterns = ["haha", "lol", "lmao", "*laughs*", "laughing", "giggles"]
            laughter_score = sum(1 for pattern in laughter_patterns if pattern in text_lower)
            
            if funny_score >= 1 or laughter_score >= 1:
                context_segments = self._get_context_segments(segments, i, 3)
                
                highlight = SessionHighlight(
                    timestamp=segment.start_time,
                    duration=30,
                    highlight_type=HighlightType.FUNNY_MOMENT,
                    title="Funny Moment",
                    description=f"Humorous moment: {segment.text[:100]}...",
                    transcription_segments=[seg.id for seg in context_segments],
                    created_by="system"
                )
                
                highlights.append(highlight)
        
        return highlights
    
    async def _detect_rule_highlights(
        self,
        segments: List[TranscriptionSegment]
    ) -> List[SessionHighlight]:
        """Detect rule clarifications."""
        
        highlights = []
        
        for i, segment in enumerate(segments):
            text_lower = segment.text.lower()
            
            # Look for rule keywords
            rule_score = sum(1 for keyword in self.rule_keywords if keyword in text_lower)
            
            if rule_score >= 2:
                context_segments = self._get_context_segments(segments, i, 4)
                
                highlight = SessionHighlight(
                    timestamp=segment.start_time,
                    duration=60,
                    highlight_type=HighlightType.RULE_CLARIFICATION,
                    title="Rule Clarification",
                    description=f"Rule discussion: {segment.text[:100]}...",
                    transcription_segments=[seg.id for seg in context_segments],
                    created_by="system"
                )
                
                highlights.append(highlight)
        
        return highlights
    
    async def _detect_audio_highlights(
        self,
        transcription_segments: List[TranscriptionSegment],
        audio_segments: List[AudioSegment]
    ) -> List[SessionHighlight]:
        """Detect highlights from audio characteristics."""
        
        highlights = []
        
        # Group audio segments by time periods
        time_windows = {}
        window_size = 30  # 30-second windows
        
        for audio_seg in audio_segments:
            window_start = int(audio_seg.start_time // window_size) * window_size
            
            if window_start not in time_windows:
                time_windows[window_start] = []
            
            time_windows[window_start].append(audio_seg)
        
        # Analyze each time window
        for window_start, segments in time_windows.items():
            if len(segments) < 3:  # Need minimum segments for analysis
                continue
            
            # Calculate average volume
            volumes = [seg.volume_level for seg in segments]
            avg_volume = np.mean(volumes)
            volume_std = np.std(volumes)
            
            # Detect volume spikes (excitement, laughter, shouting)
            if avg_volume > 0.7 and volume_std > 0.2:
                # Find corresponding transcription
                transcription_segs = [
                    seg for seg in transcription_segments
                    if window_start <= seg.start_time <= window_start + window_size
                ]
                
                if transcription_segs:
                    highlight = SessionHighlight(
                        timestamp=window_start,
                        duration=window_size,
                        highlight_type=HighlightType.IMPORTANT_MOMENT,
                        title="High Energy Moment",
                        description="Moment with high audio energy and volume",
                        transcription_segments=[seg.id for seg in transcription_segs],
                        created_by="system"
                    )
                    
                    highlights.append(highlight)
        
        return highlights
    
    def _get_context_segments(
        self,
        segments: List[TranscriptionSegment],
        center_index: int,
        context_size: int
    ) -> List[TranscriptionSegment]:
        """Get segments around a center segment for context."""
        
        start_idx = max(0, center_index - context_size // 2)
        end_idx = min(len(segments), center_index + context_size // 2 + 1)
        
        return segments[start_idx:end_idx]
    
    def _deduplicate_highlights(self, highlights: List[SessionHighlight]) -> List[SessionHighlight]:
        """Remove overlapping highlights, keeping the most important ones."""
        
        if not highlights:
            return highlights
        
        # Sort by timestamp
        sorted_highlights = sorted(highlights, key=lambda x: x.timestamp)
        
        deduplicated = []
        
        for current in sorted_highlights:
            # Check for overlap with existing highlights
            overlaps = False
            
            for existing in deduplicated:
                # Check if timestamps overlap
                if (current.timestamp < existing.timestamp + existing.duration and
                    current.timestamp + current.duration > existing.timestamp):
                    
                    # Overlaps - keep the more important one
                    current_importance = self._calculate_importance(current)
                    existing_importance = self._calculate_importance(existing)
                    
                    if current_importance > existing_importance:
                        # Replace existing with current
                        deduplicated.remove(existing)
                        deduplicated.append(current)
                    
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(current)
        
        return deduplicated
    
    def _rank_highlights(self, highlights: List[SessionHighlight]) -> List[SessionHighlight]:
        """Rank highlights by importance."""
        
        return sorted(highlights, key=self._calculate_importance, reverse=True)
    
    def _calculate_importance(self, highlight: SessionHighlight) -> float:
        """Calculate importance score for a highlight."""
        
        # Base scores by type
        type_scores = {
            HighlightType.COMBAT_HIGHLIGHT: 0.8,
            HighlightType.CHARACTER_MOMENT: 0.9,
            HighlightType.STORY_BEAT: 1.0,
            HighlightType.FUNNY_MOMENT: 0.7,
            HighlightType.RULE_CLARIFICATION: 0.6,
            HighlightType.DISCOVERY: 0.85,
            HighlightType.DECISION_POINT: 0.75,
            HighlightType.IMPORTANT_MOMENT: 0.5
        }
        
        base_score = type_scores.get(highlight.highlight_type, 0.5)
        
        # Adjust for duration (longer highlights are more important)
        duration_factor = min(1.2, highlight.duration / 60)  # Cap at 20% bonus
        
        # Adjust for number of linked segments
        segment_factor = min(1.3, len(highlight.transcription_segments) / 5)
        
        return base_score * duration_factor * segment_factor

class HighlightService:
    """Main highlight service."""
    
    def __init__(self, config: Config):
        self.config = config
        self.detection_service = HighlightDetectionService(config)
        
        # Highlight storage
        self.session_highlights: Dict[str, List[SessionHighlight]] = {}
    
    async def create_highlight(
        self,
        session_id: str,
        timestamp: float,
        duration: float,
        highlight_type: HighlightType,
        title: str,
        description: str,
        created_by: str,
        transcription_segments: List[str] = None,
        tags: List[str] = None
    ) -> SessionHighlight:
        """Create a manual highlight."""
        
        highlight = SessionHighlight(
            timestamp=timestamp,
            duration=duration,
            highlight_type=highlight_type,
            title=title,
            description=description,
            transcription_segments=transcription_segments or [],
            created_by=created_by,
            tags=tags or []
        )
        
        # Add to storage
        if session_id not in self.session_highlights:
            self.session_highlights[session_id] = []
        
        self.session_highlights[session_id].append(highlight)
        
        logger.info(f"Manual highlight created: {title}")
        return highlight
    
    async def auto_detect_highlights(
        self,
        session: SessionSchema,
        transcription_segments: List[TranscriptionSegment],
        audio_segments: List[AudioSegment] = None
    ) -> List[SessionHighlight]:
        """Auto-detect highlights from session content."""
        
        highlights = await self.detection_service.detect_highlights(
            session, transcription_segments, audio_segments
        )
        
        # Add to storage
        if session.id not in self.session_highlights:
            self.session_highlights[session.id] = []
        
        self.session_highlights[session.id].extend(highlights)
        
        logger.info(f"Auto-detected {len(highlights)} highlights")
        return highlights
    
    def get_session_highlights(
        self,
        session_id: str,
        highlight_type: Optional[HighlightType] = None,
        time_range: Optional[Tuple[float, float]] = None,
        created_by: Optional[str] = None
    ) -> List[SessionHighlight]:
        """Get highlights for a session with optional filtering."""
        
        if session_id not in self.session_highlights:
            return []
        
        highlights = self.session_highlights[session_id]
        
        # Apply filters
        if highlight_type:
            highlights = [h for h in highlights if h.highlight_type == highlight_type]
        
        if time_range:
            start_time, end_time = time_range
            highlights = [
                h for h in highlights
                if start_time <= h.timestamp <= end_time
            ]
        
        if created_by:
            highlights = [h for h in highlights if h.created_by == created_by]
        
        # Sort by timestamp
        return sorted(highlights, key=lambda x: x.timestamp)
    
    async def vote_on_highlight(
        self,
        session_id: str,
        highlight_id: str,
        user_id: str,
        vote: int  # -1, 0, or 1
    ) -> Optional[SessionHighlight]:
        """Vote on a highlight (upvote/downvote)."""
        
        highlight = self.get_highlight(session_id, highlight_id)
        if not highlight:
            return None
        
        # Simple voting - would need more sophisticated system for production
        highlight.votes += vote
        
        logger.info(f"Vote recorded for highlight {highlight_id}: {vote}")
        return highlight
    
    def get_highlight(self, session_id: str, highlight_id: str) -> Optional[SessionHighlight]:
        """Get a specific highlight."""
        
        if session_id not in self.session_highlights:
            return None
        
        return next(
            (h for h in self.session_highlights[session_id] if h.id == highlight_id),
            None
        )
    
    async def update_highlight(
        self,
        session_id: str,
        highlight_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[SessionHighlight]:
        """Update an existing highlight."""
        
        highlight = self.get_highlight(session_id, highlight_id)
        if not highlight:
            return None
        
        if title is not None:
            highlight.title = title
        if description is not None:
            highlight.description = description
        if tags is not None:
            highlight.tags = tags
        
        logger.info(f"Highlight updated: {highlight_id}")
        return highlight
    
    async def delete_highlight(self, session_id: str, highlight_id: str) -> bool:
        """Delete a highlight."""
        
        if session_id not in self.session_highlights:
            return False
        
        highlights = self.session_highlights[session_id]
        original_length = len(highlights)
        
        self.session_highlights[session_id] = [
            h for h in highlights if h.id != highlight_id
        ]
        
        success = len(self.session_highlights[session_id]) < original_length
        
        if success:
            logger.info(f"Highlight deleted: {highlight_id}")
        
        return success
    
    async def export_highlights(
        self,
        session_id: str,
        format_type: str = "json",
        include_transcription: bool = True
    ) -> str:
        """Export session highlights."""
        
        highlights = self.get_session_highlights(session_id)
        
        if format_type.lower() == "json":
            import json
            
            data = []
            for highlight in highlights:
                highlight_data = {
                    "id": highlight.id,
                    "timestamp": highlight.timestamp,
                    "duration": highlight.duration,
                    "type": highlight.highlight_type.value,
                    "title": highlight.title,
                    "description": highlight.description,
                    "created_by": highlight.created_by,
                    "votes": highlight.votes,
                    "tags": highlight.tags,
                    "created_at": highlight.created_at.isoformat()
                }
                
                if include_transcription:
                    highlight_data["transcription_segments"] = highlight.transcription_segments
                
                data.append(highlight_data)
            
            return json.dumps(data, indent=2)
        
        elif format_type.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            header = ["timestamp", "duration", "type", "title", "description", "created_by", "votes"]
            if include_transcription:
                header.append("transcription_segments")
            writer.writerow(header)
            
            # Data
            for highlight in highlights:
                row = [
                    highlight.timestamp,
                    highlight.duration,
                    highlight.highlight_type.value,
                    highlight.title,
                    highlight.description,
                    highlight.created_by,
                    highlight.votes
                ]
                
                if include_transcription:
                    row.append(";".join(highlight.transcription_segments))
                
                writer.writerow(row)
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def get_highlight_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about session highlights."""
        
        highlights = self.get_session_highlights(session_id)
        
        if not highlights:
            return {"total": 0}
        
        # Count by type
        type_counts = {}
        for highlight in highlights:
            type_name = highlight.highlight_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # Count by creator
        creator_counts = {}
        for highlight in highlights:
            creator = highlight.created_by
            creator_counts[creator] = creator_counts.get(creator, 0) + 1
        
        # Calculate timing distribution
        timestamps = [h.timestamp for h in highlights]
        
        return {
            "total": len(highlights),
            "by_type": type_counts,
            "by_creator": creator_counts,
            "auto_detected": creator_counts.get("system", 0),
            "manual": len(highlights) - creator_counts.get("system", 0),
            "average_duration": sum(h.duration for h in highlights) / len(highlights),
            "earliest_timestamp": min(timestamps),
            "latest_timestamp": max(timestamps),
            "total_votes": sum(h.votes for h in highlights)
        }