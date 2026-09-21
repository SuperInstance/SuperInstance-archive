"""
Session Analytics Service

Tracks and analyzes session metrics including speaking time, engagement levels,
participation patterns, and provides insights for improving game sessions.
"""

import asyncio
import json
import statistics
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import math

from ..models.base import BaseSessionModel, SessionHighlight, HighlightType
from ..models.session import SessionSchema, SessionParticipant, TranscriptionSegment
from ..config import ANALYTICS_CONFIG


class EngagementLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class ParticipantMetrics:
    participant_id: str
    total_speaking_time: float
    percentage_of_session: float
    word_count: int
    average_words_per_segment: float
    segments_count: int
    longest_monologue: float
    engagement_level: EngagementLevel
    interaction_score: float
    questions_asked: int
    responses_given: int
    emotional_expressions: int
    character_voice_consistency: float
    initiative_taken: int


@dataclass
class SessionFlowMetrics:
    session_id: str
    total_duration: float
    active_speaking_time: float
    silence_periods: List[Tuple[float, float]]
    energy_timeline: List[Tuple[float, float]]  # timestamp, energy_score
    peak_engagement_moments: List[Tuple[float, str]]  # timestamp, reason
    pacing_score: float
    balance_score: float
    interaction_density: float


@dataclass
class GroupDynamicsMetrics:
    dominant_speakers: List[str]
    quiet_participants: List[str]
    interaction_pairs: Dict[Tuple[str, str], int]
    group_cohesion_score: float
    leadership_rotation: List[Tuple[float, str]]  # timestamp, leader
    conflict_moments: List[Tuple[float, str]]  # timestamp, description
    collaborative_moments: List[Tuple[float, str]]  # timestamp, description


@dataclass
class ContentAnalytics:
    content_distribution: Dict[str, float]  # combat, roleplay, exploration, etc.
    story_progression_score: float
    problem_solving_instances: int
    creative_solutions: int
    rules_questions: int
    immersion_breaks: int
    character_development_score: float


@dataclass
class SessionAnalytics:
    session_id: str
    generated_at: datetime
    session_duration: float
    participant_count: int
    participant_metrics: List[ParticipantMetrics]
    flow_metrics: SessionFlowMetrics
    group_dynamics: GroupDynamicsMetrics
    content_analytics: ContentAnalytics
    overall_rating: float
    recommendations: List[str]
    trends: Dict[str, Any]


class RealTimeEngagementTracker:
    """Tracks engagement in real-time during sessions"""
    
    def __init__(self, window_size: int = 300):  # 5-minute windows
        self.window_size = window_size
        self.engagement_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.current_speakers: Set[str] = set()
        self.last_activity: Dict[str, datetime] = {}
        self.energy_indicators: deque = deque(maxlen=1000)
    
    async def update_speaker_activity(self, participant_id: str, 
                                    segment: TranscriptionSegment):
        """Update real-time speaker activity"""
        now = datetime.utcnow()
        
        # Update activity tracking
        self.last_activity[participant_id] = now
        self.current_speakers.add(participant_id)
        
        # Calculate engagement indicators
        word_count = len(segment.text.split())
        segment_duration = segment.end_time - segment.start_time
        speaking_rate = word_count / max(segment_duration, 0.1)
        
        # Energy indicators (simplified)
        energy_score = min(speaking_rate / 2.0, 1.0)  # Normalize to 0-1
        
        # Add emotional markers
        emotional_words = self._count_emotional_words(segment.text)
        if emotional_words > 0:
            energy_score = min(energy_score + (emotional_words * 0.1), 1.0)
        
        # Questions and responses
        question_marks = segment.text.count('?')
        exclamation_marks = segment.text.count('!')
        
        if question_marks > 0:
            energy_score = min(energy_score + 0.1, 1.0)
        if exclamation_marks > 0:
            energy_score = min(energy_score + (exclamation_marks * 0.05), 1.0)
        
        # Store engagement data
        engagement_data = {
            "timestamp": segment.start_time,
            "energy": energy_score,
            "word_count": word_count,
            "duration": segment_duration,
            "emotional_markers": emotional_words,
            "questions": question_marks,
            "exclamations": exclamation_marks
        }
        
        self.engagement_history[participant_id].append(engagement_data)
        self.energy_indicators.append((segment.start_time, energy_score))
    
    def _count_emotional_words(self, text: str) -> int:
        """Count emotional expressions in text"""
        emotional_words = [
            "love", "hate", "excited", "angry", "happy", "sad", "worried",
            "amazed", "shocked", "surprised", "confused", "frustrated",
            "proud", "disappointed", "relieved", "scared", "brave"
        ]
        
        text_lower = text.lower()
        return sum(1 for word in emotional_words if word in text_lower)
    
    async def get_current_engagement_levels(self) -> Dict[str, float]:
        """Get current engagement levels for all participants"""
        levels = {}
        
        for participant_id, history in self.engagement_history.items():
            if not history:
                levels[participant_id] = 0.0
                continue
            
            # Calculate recent engagement (last 10 entries)
            recent_data = list(history)[-10:]
            
            if not recent_data:
                levels[participant_id] = 0.0
                continue
            
            # Weight recent activity more heavily
            weights = [i + 1 for i in range(len(recent_data))]
            weighted_energy = sum(
                data["energy"] * weight 
                for data, weight in zip(recent_data, weights)
            ) / sum(weights)
            
            levels[participant_id] = weighted_energy
        
        return levels
    
    async def detect_engagement_patterns(self, participant_id: str) -> Dict[str, Any]:
        """Detect engagement patterns for a participant"""
        history = self.engagement_history.get(participant_id, deque())
        
        if len(history) < 5:
            return {"pattern": "insufficient_data"}
        
        recent_data = list(history)[-20:]  # Last 20 entries
        energies = [data["energy"] for data in recent_data]
        
        # Calculate trends
        if len(energies) >= 3:
            recent_trend = (energies[-1] - energies[-3]) / 2  # Simple trend
            overall_energy = statistics.mean(energies)
            energy_variance = statistics.variance(energies) if len(energies) > 1 else 0
            
            pattern = {
                "overall_energy": overall_energy,
                "trend": "increasing" if recent_trend > 0.1 else "decreasing" if recent_trend < -0.1 else "stable",
                "volatility": "high" if energy_variance > 0.2 else "low",
                "consistency": 1.0 - energy_variance  # Higher consistency = lower variance
            }
            
            return pattern
        
        return {"pattern": "insufficient_data"}


class ParticipantAnalyzer:
    """Analyzes individual participant behavior and engagement"""
    
    def __init__(self):
        self.speaking_patterns = {}
        self.interaction_tracker = defaultdict(lambda: defaultdict(int))
    
    async def analyze_participant(self, participant_id: str,
                                segments: List[TranscriptionSegment],
                                session_duration: float) -> ParticipantMetrics:
        """Analyze a single participant's session metrics"""
        
        # Filter segments for this participant
        participant_segments = [
            seg for seg in segments if seg.speaker_id == participant_id
        ]
        
        if not participant_segments:
            return self._create_empty_metrics(participant_id)
        
        # Basic speaking time metrics
        total_speaking_time = sum(
            seg.end_time - seg.start_time for seg in participant_segments
        )
        percentage_of_session = (total_speaking_time / session_duration) * 100
        
        # Word count analysis
        all_text = " ".join(seg.text for seg in participant_segments)
        word_count = len(all_text.split())
        average_words_per_segment = word_count / len(participant_segments)
        
        # Longest monologue
        longest_monologue = max(
            seg.end_time - seg.start_time for seg in participant_segments
        )
        
        # Engagement analysis
        engagement_level = await self._calculate_engagement_level(
            participant_segments, percentage_of_session
        )
        
        # Interaction analysis
        interaction_score = await self._calculate_interaction_score(
            participant_segments, all_text
        )
        
        # Question and response analysis
        questions_asked = sum(seg.text.count('?') for seg in participant_segments)
        responses_given = await self._count_responses(participant_segments)
        
        # Emotional expression analysis
        emotional_expressions = sum(
            self._count_emotional_expressions(seg.text) for seg in participant_segments
        )
        
        # Character voice consistency (simplified)
        character_voice_consistency = await self._analyze_character_consistency(
            participant_segments
        )
        
        # Initiative analysis
        initiative_taken = await self._count_initiative_moments(participant_segments)
        
        return ParticipantMetrics(
            participant_id=participant_id,
            total_speaking_time=total_speaking_time,
            percentage_of_session=percentage_of_session,
            word_count=word_count,
            average_words_per_segment=average_words_per_segment,
            segments_count=len(participant_segments),
            longest_monologue=longest_monologue,
            engagement_level=engagement_level,
            interaction_score=interaction_score,
            questions_asked=questions_asked,
            responses_given=responses_given,
            emotional_expressions=emotional_expressions,
            character_voice_consistency=character_voice_consistency,
            initiative_taken=initiative_taken
        )
    
    def _create_empty_metrics(self, participant_id: str) -> ParticipantMetrics:
        """Create empty metrics for participant with no speaking time"""
        return ParticipantMetrics(
            participant_id=participant_id,
            total_speaking_time=0.0,
            percentage_of_session=0.0,
            word_count=0,
            average_words_per_segment=0.0,
            segments_count=0,
            longest_monologue=0.0,
            engagement_level=EngagementLevel.VERY_LOW,
            interaction_score=0.0,
            questions_asked=0,
            responses_given=0,
            emotional_expressions=0,
            character_voice_consistency=0.0,
            initiative_taken=0
        )
    
    async def _calculate_engagement_level(self, segments: List[TranscriptionSegment],
                                        percentage: float) -> EngagementLevel:
        """Calculate engagement level based on various factors"""
        
        # Speaking time factor
        time_score = min(percentage / 25.0, 1.0)  # 25% is considered high participation
        
        # Activity factor (segments per hour)
        if segments:
            session_hours = (segments[-1].end_time - segments[0].start_time) / 3600
            segments_per_hour = len(segments) / max(session_hours, 0.1)
            activity_score = min(segments_per_hour / 20.0, 1.0)  # 20 segments/hour is active
        else:
            activity_score = 0.0
        
        # Interaction factor
        total_text = " ".join(seg.text for seg in segments)
        questions = total_text.count('?')
        exclamations = total_text.count('!')
        interaction_score = min((questions + exclamations) / 10.0, 1.0)
        
        # Combined score
        engagement_score = (time_score * 0.4 + activity_score * 0.4 + interaction_score * 0.2)
        
        if engagement_score >= 0.8:
            return EngagementLevel.VERY_HIGH
        elif engagement_score >= 0.6:
            return EngagementLevel.HIGH
        elif engagement_score >= 0.4:
            return EngagementLevel.MODERATE
        elif engagement_score >= 0.2:
            return EngagementLevel.LOW
        else:
            return EngagementLevel.VERY_LOW
    
    async def _calculate_interaction_score(self, segments: List[TranscriptionSegment],
                                         all_text: str) -> float:
        """Calculate how much a participant interacts with others"""
        
        # Look for interaction indicators
        interaction_indicators = [
            "you", "your", "what do you", "do you think",
            "agrees", "disagrees", "responds", "replies",
            "turns to", "looks at", "says to"
        ]
        
        interaction_count = 0
        for indicator in interaction_indicators:
            interaction_count += all_text.lower().count(indicator)
        
        # Normalize to 0-1 scale
        return min(interaction_count / 10.0, 1.0)
    
    async def _count_responses(self, segments: List[TranscriptionSegment]) -> int:
        """Count responses to others' questions or statements"""
        responses = 0
        
        response_indicators = [
            "yes", "no", "i think", "i agree", "i disagree",
            "that's right", "exactly", "i don't think so"
        ]
        
        for segment in segments:
            text_lower = segment.text.lower()
            for indicator in response_indicators:
                if indicator in text_lower:
                    responses += 1
                    break  # Count once per segment
        
        return responses
    
    def _count_emotional_expressions(self, text: str) -> int:
        """Count emotional expressions in text"""
        emotional_indicators = [
            "!", "wow", "amazing", "awesome", "terrible", "horrible",
            "love", "hate", "excited", "worried", "happy", "sad"
        ]
        
        text_lower = text.lower()
        count = text.count('!')  # Exclamation marks
        
        for indicator in emotional_indicators:
            count += text_lower.count(indicator)
        
        return count
    
    async def _analyze_character_consistency(self, segments: List[TranscriptionSegment]) -> float:
        """Analyze consistency in character voice/roleplay"""
        
        if not segments:
            return 0.0
        
        # Simple heuristic: look for consistent use of first person vs third person
        first_person_count = 0
        third_person_count = 0
        
        for segment in segments:
            text = segment.text.lower()
            
            # First person indicators
            if any(word in text for word in ["i ", "my ", "me ", "myself"]):
                first_person_count += 1
            
            # Third person indicators (character name mentions)
            if any(word in text for word in [" says", " does", " walks", " looks"]):
                third_person_count += 1
        
        total_segments = len(segments)
        
        if total_segments == 0:
            return 0.0
        
        # Consistency is higher when one style dominates
        first_person_ratio = first_person_count / total_segments
        third_person_ratio = third_person_count / total_segments
        
        # Return the higher ratio as consistency score
        return max(first_person_ratio, third_person_ratio)
    
    async def _count_initiative_moments(self, segments: List[TranscriptionSegment]) -> int:
        """Count moments where participant takes initiative"""
        initiative_count = 0
        
        initiative_phrases = [
            "i suggest", "let's", "we should", "what if we",
            "i'll go", "i want to", "let me try", "i propose"
        ]
        
        for segment in segments:
            text_lower = segment.text.lower()
            for phrase in initiative_phrases:
                if phrase in text_lower:
                    initiative_count += 1
                    break  # Count once per segment
        
        return initiative_count


class SessionFlowAnalyzer:
    """Analyzes session flow, pacing, and timing patterns"""
    
    async def analyze_session_flow(self, segments: List[TranscriptionSegment],
                                 highlights: List[SessionHighlight],
                                 session_id: str) -> SessionFlowMetrics:
        """Analyze overall session flow and pacing"""
        
        if not segments:
            return self._create_empty_flow_metrics(session_id)
        
        session_start = min(seg.start_time for seg in segments)
        session_end = max(seg.end_time for seg in segments)
        total_duration = session_end - session_start
        
        # Calculate active speaking time
        active_speaking_time = sum(
            seg.end_time - seg.start_time for seg in segments
        )
        
        # Find silence periods
        silence_periods = await self._find_silence_periods(segments)
        
        # Generate energy timeline
        energy_timeline = await self._generate_energy_timeline(segments, highlights)
        
        # Find peak engagement moments
        peak_moments = await self._find_peak_moments(energy_timeline, highlights)
        
        # Calculate pacing score
        pacing_score = await self._calculate_pacing_score(
            segments, silence_periods, total_duration
        )
        
        # Calculate balance score
        balance_score = await self._calculate_balance_score(segments)
        
        # Calculate interaction density
        interaction_density = len(segments) / (total_duration / 3600)  # segments per hour
        
        return SessionFlowMetrics(
            session_id=session_id,
            total_duration=total_duration,
            active_speaking_time=active_speaking_time,
            silence_periods=silence_periods,
            energy_timeline=energy_timeline,
            peak_engagement_moments=peak_moments,
            pacing_score=pacing_score,
            balance_score=balance_score,
            interaction_density=interaction_density
        )
    
    def _create_empty_flow_metrics(self, session_id: str) -> SessionFlowMetrics:
        """Create empty flow metrics"""
        return SessionFlowMetrics(
            session_id=session_id,
            total_duration=0.0,
            active_speaking_time=0.0,
            silence_periods=[],
            energy_timeline=[],
            peak_engagement_moments=[],
            pacing_score=0.0,
            balance_score=0.0,
            interaction_density=0.0
        )
    
    async def _find_silence_periods(self, segments: List[TranscriptionSegment],
                                  min_silence: float = 30.0) -> List[Tuple[float, float]]:
        """Find periods of silence longer than threshold"""
        silence_periods = []
        
        if len(segments) < 2:
            return silence_periods
        
        # Sort segments by start time
        sorted_segments = sorted(segments, key=lambda x: x.start_time)
        
        for i in range(len(sorted_segments) - 1):
            current_end = sorted_segments[i].end_time
            next_start = sorted_segments[i + 1].start_time
            
            silence_duration = next_start - current_end
            
            if silence_duration >= min_silence:
                silence_periods.append((current_end, next_start))
        
        return silence_periods
    
    async def _generate_energy_timeline(self, segments: List[TranscriptionSegment],
                                      highlights: List[SessionHighlight]) -> List[Tuple[float, float]]:
        """Generate timeline of session energy levels"""
        timeline = []
        
        if not segments:
            return timeline
        
        # Create time windows (5-minute intervals)
        session_start = min(seg.start_time for seg in segments)
        session_end = max(seg.end_time for seg in segments)
        window_size = 300  # 5 minutes
        
        current_time = session_start
        
        while current_time < session_end:
            window_end = min(current_time + window_size, session_end)
            
            # Get segments in this window
            window_segments = [
                seg for seg in segments
                if seg.start_time >= current_time and seg.start_time < window_end
            ]
            
            # Get highlights in this window
            window_highlights = [
                h for h in highlights
                if h.timestamp >= current_time and h.timestamp < window_end
            ]
            
            # Calculate energy score for window
            energy_score = await self._calculate_window_energy(
                window_segments, window_highlights
            )
            
            timeline.append((current_time, energy_score))
            current_time = window_end
        
        return timeline
    
    async def _calculate_window_energy(self, segments: List[TranscriptionSegment],
                                     highlights: List[SessionHighlight]) -> float:
        """Calculate energy score for a time window"""
        if not segments and not highlights:
            return 0.0
        
        energy_score = 0.0
        
        # Segment-based energy
        if segments:
            # Speaking activity
            total_words = sum(len(seg.text.split()) for seg in segments)
            activity_energy = min(total_words / 50.0, 1.0)  # Normalize
            
            # Emotional content
            emotional_content = sum(
                seg.text.count('!') + seg.text.count('?') for seg in segments
            )
            emotional_energy = min(emotional_content / 10.0, 1.0)
            
            energy_score += (activity_energy * 0.7 + emotional_energy * 0.3)
        
        # Highlight-based energy boost
        if highlights:
            highlight_boost = len(highlights) * 0.2
            energy_score += min(highlight_boost, 0.5)  # Cap boost
        
        return min(energy_score, 1.0)
    
    async def _find_peak_moments(self, energy_timeline: List[Tuple[float, float]],
                               highlights: List[SessionHighlight]) -> List[Tuple[float, str]]:
        """Find peak engagement moments"""
        peaks = []
        
        # Find energy peaks
        if len(energy_timeline) >= 3:
            for i in range(1, len(energy_timeline) - 1):
                prev_energy = energy_timeline[i - 1][1]
                current_energy = energy_timeline[i][1]
                next_energy = energy_timeline[i + 1][1]
                
                # Check if this is a local maximum above threshold
                if (current_energy > prev_energy and 
                    current_energy > next_energy and 
                    current_energy >= 0.7):
                    peaks.append((energy_timeline[i][0], "High energy period"))
        
        # Add highlight-based peaks
        for highlight in highlights:
            if highlight.highlight_type in [
                HighlightType.CRITICAL_SUCCESS, HighlightType.PLOT_REVELATION,
                HighlightType.DRAMATIC_MOMENT
            ]:
                peaks.append((highlight.timestamp, f"Major moment: {highlight.title}"))
        
        # Sort by timestamp and limit
        peaks.sort(key=lambda x: x[0])
        return peaks[:5]  # Top 5 peaks
    
    async def _calculate_pacing_score(self, segments: List[TranscriptionSegment],
                                    silence_periods: List[Tuple[float, float]],
                                    total_duration: float) -> float:
        """Calculate session pacing quality score"""
        if not segments:
            return 0.0
        
        # Ideal pacing has good mix of activity and breaks
        speaking_ratio = sum(seg.end_time - seg.start_time for seg in segments) / total_duration
        
        # Good pacing is around 60-80% speaking time
        if 0.6 <= speaking_ratio <= 0.8:
            speaking_score = 1.0
        else:
            speaking_score = 1.0 - abs(speaking_ratio - 0.7) / 0.3
        
        # Silence distribution score
        if silence_periods:
            silence_lengths = [end - start for start, end in silence_periods]
            avg_silence = statistics.mean(silence_lengths)
            
            # Ideal silence periods are 30-120 seconds
            if 30 <= avg_silence <= 120:
                silence_score = 1.0
            else:
                silence_score = max(0.0, 1.0 - abs(avg_silence - 75) / 75)
        else:
            silence_score = 0.5  # No breaks might indicate rushed pacing
        
        return (speaking_score * 0.7 + silence_score * 0.3)
    
    async def _calculate_balance_score(self, segments: List[TranscriptionSegment]) -> float:
        """Calculate speaking time balance among participants"""
        if not segments:
            return 0.0
        
        # Count speaking time per participant
        participant_times = defaultdict(float)
        
        for segment in segments:
            if segment.speaker_id:
                participant_times[segment.speaker_id] += segment.end_time - segment.start_time
        
        if len(participant_times) <= 1:
            return 1.0  # Perfect balance with one speaker
        
        speaking_times = list(participant_times.values())
        
        # Calculate coefficient of variation (lower is more balanced)
        if statistics.mean(speaking_times) > 0:
            cv = statistics.stdev(speaking_times) / statistics.mean(speaking_times)
            # Convert to balance score (0 = perfectly balanced, 1+ = imbalanced)
            balance_score = max(0.0, 1.0 - cv)
        else:
            balance_score = 0.0
        
        return balance_score


class SessionAnalyticsService:
    """Main analytics service"""
    
    def __init__(self):
        self.engagement_tracker = RealTimeEngagementTracker()
        self.participant_analyzer = ParticipantAnalyzer()
        self.flow_analyzer = SessionFlowAnalyzer()
        self.session_analytics: Dict[str, SessionAnalytics] = {}
    
    async def analyze_session(self, session: SessionSchema,
                            transcription_segments: List[TranscriptionSegment],
                            highlights: List[SessionHighlight]) -> SessionAnalytics:
        """Perform comprehensive session analysis"""
        
        if not transcription_segments:
            return await self._create_minimal_analytics(session)
        
        session_start = min(seg.start_time for seg in transcription_segments)
        session_end = max(seg.end_time for seg in transcription_segments)
        session_duration = session_end - session_start
        
        # Analyze individual participants
        participant_metrics = []
        for participant in session.participants:
            metrics = await self.participant_analyzer.analyze_participant(
                participant.user_id, transcription_segments, session_duration
            )
            participant_metrics.append(metrics)
        
        # Analyze session flow
        flow_metrics = await self.flow_analyzer.analyze_session_flow(
            transcription_segments, highlights, session.id
        )
        
        # Analyze group dynamics
        group_dynamics = await self._analyze_group_dynamics(
            transcription_segments, participant_metrics
        )
        
        # Analyze content
        content_analytics = await self._analyze_content(
            transcription_segments, highlights
        )
        
        # Calculate overall rating
        overall_rating = await self._calculate_overall_rating(
            participant_metrics, flow_metrics, group_dynamics, content_analytics
        )
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            participant_metrics, flow_metrics, group_dynamics, content_analytics
        )
        
        # Analyze trends (if we have historical data)
        trends = await self._analyze_trends(session.id)
        
        analytics = SessionAnalytics(
            session_id=session.id,
            generated_at=datetime.utcnow(),
            session_duration=session_duration,
            participant_count=len(session.participants),
            participant_metrics=participant_metrics,
            flow_metrics=flow_metrics,
            group_dynamics=group_dynamics,
            content_analytics=content_analytics,
            overall_rating=overall_rating,
            recommendations=recommendations,
            trends=trends
        )
        
        # Store analytics
        self.session_analytics[session.id] = analytics
        
        return analytics
    
    async def _create_minimal_analytics(self, session: SessionSchema) -> SessionAnalytics:
        """Create minimal analytics for sessions with no transcription"""
        return SessionAnalytics(
            session_id=session.id,
            generated_at=datetime.utcnow(),
            session_duration=0.0,
            participant_count=len(session.participants),
            participant_metrics=[],
            flow_metrics=self.flow_analyzer._create_empty_flow_metrics(session.id),
            group_dynamics=GroupDynamicsMetrics(
                dominant_speakers=[],
                quiet_participants=[],
                interaction_pairs={},
                group_cohesion_score=0.0,
                leadership_rotation=[],
                conflict_moments=[],
                collaborative_moments=[]
            ),
            content_analytics=ContentAnalytics(
                content_distribution={},
                story_progression_score=0.0,
                problem_solving_instances=0,
                creative_solutions=0,
                rules_questions=0,
                immersion_breaks=0,
                character_development_score=0.0
            ),
            overall_rating=0.0,
            recommendations=["Enable audio recording and transcription for detailed analytics"],
            trends={}
        )
    
    async def _analyze_group_dynamics(self, segments: List[TranscriptionSegment],
                                    participant_metrics: List[ParticipantMetrics]) -> GroupDynamicsMetrics:
        """Analyze group dynamics and interactions"""
        
        # Identify dominant and quiet speakers
        dominant_speakers = [
            m.participant_id for m in participant_metrics
            if m.percentage_of_session > 25.0
        ]
        
        quiet_participants = [
            m.participant_id for m in participant_metrics
            if m.percentage_of_session < 10.0
        ]
        
        # Analyze interaction pairs (simplified)
        interaction_pairs = {}
        
        # Calculate group cohesion score
        speaking_percentages = [m.percentage_of_session for m in participant_metrics]
        if speaking_percentages:
            # Lower variance indicates better cohesion
            if len(speaking_percentages) > 1:
                variance = statistics.variance(speaking_percentages)
                cohesion_score = max(0.0, 1.0 - (variance / 625))  # Normalize (25^2)
            else:
                cohesion_score = 1.0
        else:
            cohesion_score = 0.0
        
        # Analyze leadership rotation (simplified)
        leadership_rotation = []
        
        # Detect conflict and collaborative moments (simplified)
        conflict_moments = []
        collaborative_moments = []
        
        return GroupDynamicsMetrics(
            dominant_speakers=dominant_speakers,
            quiet_participants=quiet_participants,
            interaction_pairs=interaction_pairs,
            group_cohesion_score=cohesion_score,
            leadership_rotation=leadership_rotation,
            conflict_moments=conflict_moments,
            collaborative_moments=collaborative_moments
        )
    
    async def _analyze_content(self, segments: List[TranscriptionSegment],
                             highlights: List[SessionHighlight]) -> ContentAnalytics:
        """Analyze session content types and quality"""
        
        # Content distribution analysis
        content_distribution = {
            "combat": 0.0,
            "roleplay": 0.0,
            "exploration": 0.0,
            "story": 0.0,
            "other": 0.0
        }
        
        for segment in segments:
            content_type = await self._classify_segment_content(segment.text)
            content_distribution[content_type] += 1
        
        # Normalize to percentages
        total_segments = sum(content_distribution.values())
        if total_segments > 0:
            content_distribution = {
                k: (v / total_segments) * 100 
                for k, v in content_distribution.items()
            }
        
        # Story progression score (based on plot highlights)
        plot_highlights = [
            h for h in highlights 
            if h.highlight_type == HighlightType.PLOT_REVELATION
        ]
        story_progression_score = min(len(plot_highlights) / 3.0, 1.0)  # 3+ plot points = good progression
        
        # Problem solving instances
        problem_solving_instances = len([
            h for h in highlights
            if h.highlight_type == HighlightType.PUZZLE_SOLVED
        ])
        
        # Creative solutions (simplified heuristic)
        creative_solutions = sum(
            1 for segment in segments
            if any(word in segment.text.lower() for word in [
                "creative", "unusual", "clever", "unique", "innovative"
            ])
        )
        
        # Rules questions
        rules_questions = sum(
            1 for segment in segments
            if any(phrase in segment.text.lower() for phrase in [
                "how does", "can i", "is it possible", "what's the rule"
            ])
        )
        
        # Immersion breaks (out-of-character moments)
        immersion_breaks = sum(
            1 for segment in segments
            if any(phrase in segment.text.lower() for phrase in [
                "out of character", "ooc", "real life", "bathroom break"
            ])
        )
        
        # Character development score
        character_highlights = [
            h for h in highlights
            if h.highlight_type == HighlightType.CHARACTER_MOMENT
        ]
        character_development_score = min(len(character_highlights) / 2.0, 1.0)
        
        return ContentAnalytics(
            content_distribution=content_distribution,
            story_progression_score=story_progression_score,
            problem_solving_instances=problem_solving_instances,
            creative_solutions=creative_solutions,
            rules_questions=rules_questions,
            immersion_breaks=immersion_breaks,
            character_development_score=character_development_score
        )
    
    async def _classify_segment_content(self, text: str) -> str:
        """Classify a segment's content type"""
        text_lower = text.lower()
        
        # Combat indicators
        combat_words = ["roll", "attack", "damage", "hit", "miss", "initiative", "spell"]
        combat_score = sum(1 for word in combat_words if word in text_lower)
        
        # Roleplay indicators
        roleplay_words = ["says", "asks", "character", "feeling", "personality"]
        roleplay_score = sum(1 for word in roleplay_words if word in text_lower)
        
        # Exploration indicators
        exploration_words = ["look", "search", "examine", "room", "door", "find"]
        exploration_score = sum(1 for word in exploration_words if word in text_lower)
        
        # Story indicators
        story_words = ["quest", "npc", "plot", "story", "mystery", "reveal"]
        story_score = sum(1 for word in story_words if word in text_lower)
        
        scores = {
            "combat": combat_score,
            "roleplay": roleplay_score,
            "exploration": exploration_score,
            "story": story_score
        }
        
        max_score = max(scores.values())
        if max_score == 0:
            return "other"
        
        return max(scores, key=scores.get)
    
    async def _calculate_overall_rating(self, participant_metrics: List[ParticipantMetrics],
                                      flow_metrics: SessionFlowMetrics,
                                      group_dynamics: GroupDynamicsMetrics,
                                      content_analytics: ContentAnalytics) -> float:
        """Calculate overall session rating (0-10 scale)"""
        
        scores = []
        
        # Engagement score (average of participant engagement)
        if participant_metrics:
            engagement_values = {
                EngagementLevel.VERY_HIGH: 1.0,
                EngagementLevel.HIGH: 0.8,
                EngagementLevel.MODERATE: 0.6,
                EngagementLevel.LOW: 0.4,
                EngagementLevel.VERY_LOW: 0.2
            }
            
            avg_engagement = statistics.mean(
                engagement_values.get(m.engagement_level, 0.0)
                for m in participant_metrics
            )
            scores.append(avg_engagement)
        
        # Flow quality score
        scores.append(flow_metrics.pacing_score)
        scores.append(flow_metrics.balance_score)
        
        # Group dynamics score
        scores.append(group_dynamics.group_cohesion_score)
        
        # Content quality score
        scores.append(content_analytics.story_progression_score)
        scores.append(content_analytics.character_development_score)
        
        # Calculate weighted average
        if scores:
            overall_score = statistics.mean(scores)
            return round(overall_score * 10, 1)  # Convert to 0-10 scale
        
        return 0.0
    
    async def _generate_recommendations(self, participant_metrics: List[ParticipantMetrics],
                                      flow_metrics: SessionFlowMetrics,
                                      group_dynamics: GroupDynamicsMetrics,
                                      content_analytics: ContentAnalytics) -> List[str]:
        """Generate actionable recommendations for improving sessions"""
        recommendations = []
        
        # Participation recommendations
        if group_dynamics.quiet_participants:
            recommendations.append(
                f"Encourage participation from quieter players: {', '.join(group_dynamics.quiet_participants[:3])}"
            )
        
        if group_dynamics.dominant_speakers:
            recommendations.append(
                "Consider techniques to balance speaking time among all players"
            )
        
        # Pacing recommendations
        if flow_metrics.pacing_score < 0.6:
            if flow_metrics.active_speaking_time / flow_metrics.total_duration > 0.8:
                recommendations.append("Consider adding more breaks and pauses for players to process")
            else:
                recommendations.append("Sessions could benefit from more active engagement and discussion")
        
        # Content recommendations
        content_dist = content_analytics.content_distribution
        if content_dist:
            max_content_type = max(content_dist, key=content_dist.get)
            if content_dist[max_content_type] > 60:
                recommendations.append(f"Consider adding more variety - session was heavily focused on {max_content_type}")
        
        if content_analytics.character_development_score < 0.4:
            recommendations.append("Look for opportunities to incorporate more character development moments")
        
        if content_analytics.story_progression_score < 0.3:
            recommendations.append("Consider adding more plot advancement and story revelations")
        
        # Engagement recommendations
        low_engagement_count = sum(
            1 for m in participant_metrics
            if m.engagement_level in [EngagementLevel.LOW, EngagementLevel.VERY_LOW]
        )
        
        if low_engagement_count > len(participant_metrics) * 0.3:  # More than 30% low engagement
            recommendations.append("Consider techniques to increase overall player engagement")
        
        # Default recommendation if none generated
        if not recommendations:
            recommendations.append("Great session! Continue with current approach.")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    async def _analyze_trends(self, session_id: str) -> Dict[str, Any]:
        """Analyze trends across multiple sessions (placeholder)"""
        # This would analyze historical data if available
        return {
            "trend_data_available": False,
            "note": "Historical trend analysis requires multiple sessions"
        }
    
    async def get_session_analytics(self, session_id: str) -> Optional[SessionAnalytics]:
        """Get analytics for a specific session"""
        return self.session_analytics.get(session_id)
    
    async def get_participant_summary(self, participant_id: str,
                                    session_ids: List[str]) -> Dict[str, Any]:
        """Get summary analytics across multiple sessions for a participant"""
        participant_data = []
        
        for session_id in session_ids:
            analytics = self.session_analytics.get(session_id)
            if analytics:
                participant_metric = next(
                    (m for m in analytics.participant_metrics if m.participant_id == participant_id),
                    None
                )
                if participant_metric:
                    participant_data.append(participant_metric)
        
        if not participant_data:
            return {"error": "No data found for participant"}
        
        # Calculate averages and trends
        summary = {
            "total_sessions": len(participant_data),
            "average_speaking_percentage": statistics.mean(m.percentage_of_session for m in participant_data),
            "average_engagement": statistics.mode([m.engagement_level for m in participant_data]),
            "total_words": sum(m.word_count for m in participant_data),
            "average_interaction_score": statistics.mean(m.interaction_score for m in participant_data),
            "questions_asked_total": sum(m.questions_asked for m in participant_data),
            "initiative_taken_total": sum(m.initiative_taken for m in participant_data)
        }
        
        return summary