"""
Social Pattern Insights

AI-powered system for analyzing social interaction patterns, behavioral trends,
and relationship dynamics to provide actionable insights.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import json
import numpy as np
from collections import defaultdict, Counter
import math

class PatternType(Enum):
    COMMUNICATION = "communication"
    COLLABORATION = "collaboration"
    NETWORK_STRUCTURE = "network_structure"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    INFLUENCE = "influence"
    RELATIONSHIP_EVOLUTION = "relationship_evolution"
    GROUP_DYNAMICS = "group_dynamics"

class TrendDirection(Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLICAL = "cyclical"
    VOLATILE = "volatile"

class InsightType(Enum):
    OPPORTUNITY = "opportunity"
    RISK = "risk"
    TREND = "trend"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    PREDICTION = "prediction"

@dataclass
class SocialInteraction:
    id: Optional[int] = None
    person1_id: str = ""
    person2_id: str = ""
    interaction_type: str = "communication"  # communication, meeting, collaboration, etc.
    medium: str = "email"  # email, chat, video, in_person, etc.
    duration_minutes: int = 0
    sentiment: float = 0.0  # -1 to 1 scale
    frequency_score: float = 1.0  # How frequent/regular this type of interaction is
    context: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    occurred_at: datetime = datetime.now()

    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.metadata is None:
            self.metadata = {}

@dataclass
class SocialPattern:
    id: Optional[int] = None
    pattern_type: PatternType = PatternType.BEHAVIORAL
    title: str = ""
    description: str = ""
    participants: List[str] = None  # Person IDs involved
    pattern_strength: float = 0.0  # 0-1 confidence in pattern
    frequency: str = "weekly"  # daily, weekly, monthly, irregular
    trend_direction: TrendDirection = TrendDirection.STABLE
    first_observed: datetime = datetime.now()
    last_observed: datetime = datetime.now()
    supporting_evidence: List[Dict[str, Any]] = None
    related_metrics: Dict[str, float] = None
    impact_assessment: Dict[str, float] = None

    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.supporting_evidence is None:
            self.supporting_evidence = []
        if self.related_metrics is None:
            self.related_metrics = {}
        if self.impact_assessment is None:
            self.impact_assessment = {}

@dataclass
class SocialInsight:
    id: Optional[int] = None
    insight_type: InsightType = InsightType.TREND
    title: str = ""
    description: str = ""
    related_patterns: List[int] = None  # Pattern IDs
    affected_individuals: List[str] = None  # Person IDs
    affected_groups: List[str] = None  # Group/team IDs
    confidence_score: float = 0.5  # 0-1 confidence level
    priority: str = "medium"  # low, medium, high, critical
    actionable_recommendations: List[str] = None
    expected_outcomes: List[str] = None
    time_horizon: str = "short_term"  # short_term, medium_term, long_term
    supporting_data: Dict[str, Any] = None
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.related_patterns is None:
            self.related_patterns = []
        if self.affected_individuals is None:
            self.affected_individuals = []
        if self.affected_groups is None:
            self.affected_groups = []
        if self.actionable_recommendations is None:
            self.actionable_recommendations = []
        if self.expected_outcomes is None:
            self.expected_outcomes = []
        if self.supporting_data is None:
            self.supporting_data = {}

@dataclass
class NetworkSnapshot:
    id: Optional[int] = None
    snapshot_date: datetime = datetime.now()
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    clustering_coefficient: float = 0.0
    average_path_length: float = 0.0
    key_influencers: List[str] = None  # Top influencer IDs
    isolated_nodes: List[str] = None  # Isolated person IDs
    community_structure: Dict[str, List[str]] = None
    centrality_measures: Dict[str, Dict[str, float]] = None
    network_health_score: float = 0.5

    def __post_init__(self):
        if self.key_influencers is None:
            self.key_influencers = []
        if self.isolated_nodes is None:
            self.isolated_nodes = []
        if self.community_structure is None:
            self.community_structure = {}
        if self.centrality_measures is None:
            self.centrality_measures = {}

class SocialPatternAnalyzer:
    """AI-powered social pattern analysis and insight generation system"""
    
    def __init__(self, db_path: str = "social_patterns.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the social pattern analysis database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_interactions (
                id INTEGER PRIMARY KEY,
                person1_id TEXT NOT NULL,
                person2_id TEXT NOT NULL,
                interaction_type TEXT DEFAULT 'communication',
                medium TEXT DEFAULT 'email',
                duration_minutes INTEGER DEFAULT 0,
                sentiment REAL DEFAULT 0.0,
                frequency_score REAL DEFAULT 1.0,
                context TEXT,
                metadata TEXT,
                occurred_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_patterns (
                id INTEGER PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                participants TEXT,
                pattern_strength REAL DEFAULT 0.0,
                frequency TEXT DEFAULT 'weekly',
                trend_direction TEXT DEFAULT 'stable',
                first_observed TEXT,
                last_observed TEXT,
                supporting_evidence TEXT,
                related_metrics TEXT,
                impact_assessment TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS social_insights (
                id INTEGER PRIMARY KEY,
                insight_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                related_patterns TEXT,
                affected_individuals TEXT,
                affected_groups TEXT,
                confidence_score REAL DEFAULT 0.5,
                priority TEXT DEFAULT 'medium',
                actionable_recommendations TEXT,
                expected_outcomes TEXT,
                time_horizon TEXT DEFAULT 'short_term',
                supporting_data TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_snapshots (
                id INTEGER PRIMARY KEY,
                snapshot_date TEXT,
                total_nodes INTEGER,
                total_edges INTEGER,
                density REAL,
                clustering_coefficient REAL,
                average_path_length REAL,
                key_influencers TEXT,
                isolated_nodes TEXT,
                community_structure TEXT,
                centrality_measures TEXT,
                network_health_score REAL DEFAULT 0.5
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def record_interaction(self, interaction: SocialInteraction) -> int:
        """Record a social interaction for pattern analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO social_interactions 
            (person1_id, person2_id, interaction_type, medium, duration_minutes,
             sentiment, frequency_score, context, metadata, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.person1_id, interaction.person2_id, interaction.interaction_type,
            interaction.medium, interaction.duration_minutes, interaction.sentiment,
            interaction.frequency_score, json.dumps(interaction.context),
            json.dumps(interaction.metadata), interaction.occurred_at.isoformat()
        ))
        
        interaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return interaction_id
    
    async def analyze_communication_patterns(self, days_back: int = 30) -> List[SocialPattern]:
        """Analyze communication patterns in the social network"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Get recent interactions
        cursor.execute("""
            SELECT * FROM social_interactions 
            WHERE occurred_at >= ? 
            ORDER BY occurred_at DESC
        """, (start_date.isoformat(),))
        
        interactions = cursor.fetchall()
        patterns = []
        
        if not interactions:
            conn.close()
            return patterns
        
        # Convert to dictionaries
        cols = [description[0] for description in cursor.description]
        interaction_dicts = [dict(zip(cols, row)) for row in interactions]
        
        # Analyze frequency patterns
        patterns.extend(await self._analyze_frequency_patterns(interaction_dicts))
        
        # Analyze time-based patterns
        patterns.extend(await self._analyze_temporal_patterns(interaction_dicts))
        
        # Analyze sentiment patterns
        patterns.extend(await self._analyze_sentiment_patterns(interaction_dicts))
        
        # Analyze medium preferences
        patterns.extend(await self._analyze_medium_patterns(interaction_dicts))
        
        # Store identified patterns
        for pattern in patterns:
            await self._store_pattern(pattern, conn)
        
        conn.close()
        return patterns
    
    async def _analyze_frequency_patterns(self, interactions: List[Dict]) -> List[SocialPattern]:
        """Analyze interaction frequency patterns"""
        patterns = []
        
        # Count interactions per person pair
        pair_interactions = defaultdict(list)
        for interaction in interactions:
            pair_key = tuple(sorted([interaction['person1_id'], interaction['person2_id']]))
            pair_interactions[pair_key].append(interaction)
        
        # Identify high-frequency pairs
        avg_interactions = np.mean([len(interactions) for interactions in pair_interactions.values()])
        high_threshold = avg_interactions + np.std([len(interactions) for interactions in pair_interactions.values()])
        
        for pair, pair_ints in pair_interactions.items():
            if len(pair_ints) > high_threshold:
                # Calculate interaction frequency
                days_span = (datetime.fromisoformat(max(i['occurred_at'] for i in pair_ints)) - 
                           datetime.fromisoformat(min(i['occurred_at'] for i in pair_ints))).days
                frequency_per_day = len(pair_ints) / max(1, days_span)
                
                pattern = SocialPattern(
                    pattern_type=PatternType.COMMUNICATION,
                    title=f"High-frequency communication between {pair[0]} and {pair[1]}",
                    description=f"These individuals communicate {frequency_per_day:.1f} times per day on average",
                    participants=list(pair),
                    pattern_strength=min(1.0, frequency_per_day / 3.0),  # Normalize to 0-1
                    frequency="daily" if frequency_per_day >= 1 else "weekly",
                    first_observed=datetime.fromisoformat(min(i['occurred_at'] for i in pair_ints)),
                    last_observed=datetime.fromisoformat(max(i['occurred_at'] for i in pair_ints)),
                    related_metrics={"interactions_per_day": frequency_per_day, "total_interactions": len(pair_ints)},
                    supporting_evidence=[{"type": "frequency", "value": len(pair_ints), "timeframe": f"{days_span} days"}]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _analyze_temporal_patterns(self, interactions: List[Dict]) -> List[SocialPattern]:
        """Analyze temporal communication patterns"""
        patterns = []
        
        # Analyze by hour of day
        hourly_counts = defaultdict(int)
        for interaction in interactions:
            hour = datetime.fromisoformat(interaction['occurred_at']).hour
            hourly_counts[hour] += 1
        
        # Find peak communication hours
        if hourly_counts:
            max_hour = max(hourly_counts.keys(), key=lambda k: hourly_counts[k])
            peak_count = hourly_counts[max_hour]
            avg_count = np.mean(list(hourly_counts.values()))
            
            if peak_count > avg_count * 1.5:  # Significant peak
                pattern = SocialPattern(
                    pattern_type=PatternType.TEMPORAL,
                    title=f"Peak communication at {max_hour}:00",
                    description=f"Communication activity peaks at {max_hour}:00 with {peak_count} interactions",
                    participants=[],  # Network-wide pattern
                    pattern_strength=min(1.0, peak_count / (avg_count * 2)),
                    frequency="daily",
                    trend_direction=TrendDirection.STABLE,
                    related_metrics={"peak_hour": max_hour, "peak_count": peak_count, "average_count": avg_count},
                    supporting_evidence=[{"type": "temporal", "peak_hour": max_hour, "relative_increase": peak_count/avg_count}]
                )
                patterns.append(pattern)
        
        # Analyze by day of week
        daily_counts = defaultdict(int)
        for interaction in interactions:
            weekday = datetime.fromisoformat(interaction['occurred_at']).weekday()
            daily_counts[weekday] += 1
        
        if daily_counts:
            weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            peak_day = max(daily_counts.keys(), key=lambda k: daily_counts[k])
            peak_count = daily_counts[peak_day]
            avg_count = np.mean(list(daily_counts.values()))
            
            if peak_count > avg_count * 1.3:  # Significant weekly peak
                pattern = SocialPattern(
                    pattern_type=PatternType.TEMPORAL,
                    title=f"Peak weekly communication on {weekday_names[peak_day]}",
                    description=f"Communication is highest on {weekday_names[peak_day]} with {peak_count} interactions",
                    participants=[],
                    pattern_strength=min(1.0, peak_count / (avg_count * 1.5)),
                    frequency="weekly",
                    related_metrics={"peak_day": peak_day, "peak_count": peak_count},
                    supporting_evidence=[{"type": "weekly", "peak_day": weekday_names[peak_day], "count": peak_count}]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _analyze_sentiment_patterns(self, interactions: List[Dict]) -> List[SocialPattern]:
        """Analyze sentiment trends in communications"""
        patterns = []
        
        # Analyze overall sentiment trends
        sentiment_interactions = [i for i in interactions if i['sentiment'] != 0.0]
        if not sentiment_interactions:
            return patterns
        
        # Group by person for individual sentiment analysis
        person_sentiments = defaultdict(list)
        for interaction in sentiment_interactions:
            person_sentiments[interaction['person1_id']].append(interaction['sentiment'])
            person_sentiments[interaction['person2_id']].append(interaction['sentiment'])
        
        # Identify consistently positive or negative individuals
        for person_id, sentiments in person_sentiments.items():
            if len(sentiments) >= 5:  # Minimum interactions for pattern
                avg_sentiment = np.mean(sentiments)
                sentiment_std = np.std(sentiments)
                
                if avg_sentiment > 0.3 and sentiment_std < 0.3:  # Consistently positive
                    pattern = SocialPattern(
                        pattern_type=PatternType.BEHAVIORAL,
                        title=f"Consistently positive communication from {person_id}",
                        description=f"This person maintains positive sentiment (avg: {avg_sentiment:.2f}) in communications",
                        participants=[person_id],
                        pattern_strength=min(1.0, avg_sentiment * 2),
                        frequency="ongoing",
                        related_metrics={"average_sentiment": avg_sentiment, "sentiment_consistency": 1 - sentiment_std},
                        impact_assessment={"team_morale": 0.7, "collaboration_quality": 0.6}
                    )
                    patterns.append(pattern)
                
                elif avg_sentiment < -0.3 and sentiment_std < 0.3:  # Consistently negative
                    pattern = SocialPattern(
                        pattern_type=PatternType.BEHAVIORAL,
                        title=f"Consistently negative communication from {person_id}",
                        description=f"This person shows negative sentiment (avg: {avg_sentiment:.2f}) in communications",
                        participants=[person_id],
                        pattern_strength=min(1.0, abs(avg_sentiment) * 2),
                        frequency="ongoing",
                        related_metrics={"average_sentiment": avg_sentiment, "sentiment_consistency": 1 - sentiment_std},
                        impact_assessment={"team_morale": -0.5, "collaboration_quality": -0.4}
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _analyze_medium_patterns(self, interactions: List[Dict]) -> List[SocialPattern]:
        """Analyze communication medium preferences and patterns"""
        patterns = []
        
        # Count medium usage
        medium_counts = Counter(i['medium'] for i in interactions)
        total_interactions = len(interactions)
        
        # Identify dominant communication mediums
        for medium, count in medium_counts.items():
            usage_percentage = count / total_interactions
            
            if usage_percentage > 0.4:  # More than 40% of interactions
                pattern = SocialPattern(
                    pattern_type=PatternType.COMMUNICATION,
                    title=f"Dominant use of {medium} for communication",
                    description=f"{medium} is used for {usage_percentage:.1%} of all communications",
                    participants=[],  # Network-wide
                    pattern_strength=usage_percentage,
                    frequency="ongoing",
                    related_metrics={"usage_percentage": usage_percentage, "total_count": count},
                    supporting_evidence=[{"type": "medium_usage", "medium": medium, "count": count}]
                )
                patterns.append(pattern)
        
        # Analyze medium preferences by person pairs
        pair_medium_prefs = defaultdict(lambda: defaultdict(int))
        for interaction in interactions:
            pair_key = tuple(sorted([interaction['person1_id'], interaction['person2_id']]))
            pair_medium_prefs[pair_key][interaction['medium']] += 1
        
        for pair, medium_counts in pair_medium_prefs.items():
            if sum(medium_counts.values()) >= 5:  # Minimum interactions
                preferred_medium = max(medium_counts.keys(), key=lambda k: medium_counts[k])
                preference_strength = medium_counts[preferred_medium] / sum(medium_counts.values())
                
                if preference_strength > 0.7:  # Strong preference
                    pattern = SocialPattern(
                        pattern_type=PatternType.COMMUNICATION,
                        title=f"Strong {preferred_medium} preference between {pair[0]} and {pair[1]}",
                        description=f"This pair uses {preferred_medium} for {preference_strength:.1%} of their communications",
                        participants=list(pair),
                        pattern_strength=preference_strength,
                        frequency="ongoing",
                        related_metrics={"preferred_medium": preferred_medium, "preference_strength": preference_strength}
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def generate_social_insights(self, days_back: int = 30) -> List[SocialInsight]:
        """Generate actionable insights from identified patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Get recent patterns
        cursor.execute("""
            SELECT * FROM social_patterns 
            WHERE last_observed >= ?
            ORDER BY pattern_strength DESC
        """, (start_date.isoformat(),))
        
        pattern_rows = cursor.fetchall()
        insights = []
        
        if not pattern_rows:
            conn.close()
            return insights
        
        # Convert to pattern objects
        pattern_cols = [description[0] for description in cursor.description]
        patterns = []
        for row in pattern_rows:
            pattern_data = dict(zip(pattern_cols, row))
            pattern_data['participants'] = json.loads(pattern_data['participants']) if pattern_data['participants'] else []
            pattern_data['related_metrics'] = json.loads(pattern_data['related_metrics']) if pattern_data['related_metrics'] else {}
            pattern_data['impact_assessment'] = json.loads(pattern_data['impact_assessment']) if pattern_data['impact_assessment'] else {}
            patterns.append(pattern_data)
        
        # Generate different types of insights
        insights.extend(await self._generate_opportunity_insights(patterns))
        insights.extend(await self._generate_risk_insights(patterns))
        insights.extend(await self._generate_trend_insights(patterns))
        insights.extend(await self._generate_recommendation_insights(patterns))
        
        # Store insights
        for insight in insights:
            await self._store_insight(insight, conn)
        
        conn.close()
        return insights
    
    async def _generate_opportunity_insights(self, patterns: List[Dict]) -> List[SocialInsight]:
        """Generate insights about opportunities"""
        insights = []
        
        # Look for positive collaboration patterns
        for pattern in patterns:
            if (pattern['pattern_type'] == 'communication' and 
                pattern['pattern_strength'] > 0.7 and 
                len(pattern['participants']) == 2):
                
                insight = SocialInsight(
                    insight_type=InsightType.OPPORTUNITY,
                    title=f"Strong collaboration opportunity between {pattern['participants'][0]} and {pattern['participants'][1]}",
                    description=f"These individuals show strong communication patterns that could be leveraged for important projects",
                    related_patterns=[pattern['id']] if pattern.get('id') else [],
                    affected_individuals=pattern['participants'],
                    confidence_score=pattern['pattern_strength'],
                    priority="medium",
                    actionable_recommendations=[
                        "Consider pairing these individuals for high-priority projects",
                        "Use their collaboration as a model for other team pairs",
                        "Explore opportunities for them to mentor other team members"
                    ],
                    expected_outcomes=[
                        "Increased project success rates",
                        "Improved team collaboration patterns",
                        "Enhanced knowledge sharing"
                    ],
                    time_horizon="short_term"
                )
                insights.append(insight)
        
        return insights
    
    async def _generate_risk_insights(self, patterns: List[Dict]) -> List[SocialInsight]:
        """Generate insights about risks"""
        insights = []
        
        # Look for negative sentiment patterns
        for pattern in patterns:
            if (pattern['pattern_type'] == 'behavioral' and 
                'negative' in pattern['title'].lower()):
                
                impact = pattern.get('impact_assessment', {})
                if impact.get('team_morale', 0) < -0.3:
                    
                    insight = SocialInsight(
                        insight_type=InsightType.RISK,
                        title=f"Team morale risk from negative communication patterns",
                        description=f"Consistently negative communication from {pattern['participants'][0]} may impact team dynamics",
                        related_patterns=[pattern['id']] if pattern.get('id') else [],
                        affected_individuals=pattern['participants'],
                        confidence_score=pattern['pattern_strength'],
                        priority="high",
                        actionable_recommendations=[
                            "Schedule 1-on-1 meeting to understand concerns",
                            "Provide communication coaching or support",
                            "Monitor team sentiment and address issues proactively",
                            "Consider workload or role adjustments if needed"
                        ],
                        expected_outcomes=[
                            "Improved team morale",
                            "Better communication climate",
                            "Reduced risk of team dysfunction"
                        ],
                        time_horizon="short_term"
                    )
                    insights.append(insight)
        
        return insights
    
    async def _generate_trend_insights(self, patterns: List[Dict]) -> List[SocialInsight]:
        """Generate insights about trends"""
        insights = []
        
        # Analyze temporal patterns for trends
        temporal_patterns = [p for p in patterns if p['pattern_type'] == 'temporal']
        
        if temporal_patterns:
            # Look for communication peak patterns
            peak_patterns = [p for p in temporal_patterns if 'peak' in p['title'].lower()]
            
            if peak_patterns:
                insight = SocialInsight(
                    insight_type=InsightType.TREND,
                    title="Communication peak patterns identified",
                    description="Team communication shows clear peak periods that can be optimized",
                    related_patterns=[p['id'] for p in peak_patterns if p.get('id')],
                    affected_individuals=[],  # Team-wide
                    confidence_score=np.mean([p['pattern_strength'] for p in peak_patterns]),
                    priority="medium",
                    actionable_recommendations=[
                        "Schedule important meetings during peak communication times",
                        "Avoid scheduling deep work during high-interaction periods",
                        "Use quiet periods for focused individual work",
                        "Consider flexible scheduling to accommodate peak patterns"
                    ],
                    expected_outcomes=[
                        "More effective meeting participation",
                        "Better work-life balance",
                        "Increased productivity during optimal times"
                    ],
                    time_horizon="medium_term"
                )
                insights.append(insight)
        
        return insights
    
    async def _generate_recommendation_insights(self, patterns: List[Dict]) -> List[SocialInsight]:
        """Generate actionable recommendations"""
        insights = []
        
        # Look for medium preference patterns
        medium_patterns = [p for p in patterns if 'medium' in p['title'].lower() or 'preference' in p['title'].lower()]
        
        if medium_patterns:
            # Analyze if there's over-reliance on a single medium
            dominant_medium_patterns = [p for p in medium_patterns if p['pattern_strength'] > 0.8]
            
            if dominant_medium_patterns:
                insight = SocialInsight(
                    insight_type=InsightType.RECOMMENDATION,
                    title="Diversify communication channels",
                    description="Team shows heavy reliance on single communication medium",
                    related_patterns=[p['id'] for p in dominant_medium_patterns if p.get('id')],
                    affected_individuals=[],
                    confidence_score=np.mean([p['pattern_strength'] for p in dominant_medium_patterns]),
                    priority="low",
                    actionable_recommendations=[
                        "Introduce variety in communication channels",
                        "Train team on effective use of different mediums",
                        "Match communication medium to message urgency and complexity",
                        "Encourage face-to-face interaction for relationship building"
                    ],
                    expected_outcomes=[
                        "More effective communication",
                        "Reduced miscommunication risks",
                        "Better relationship building",
                        "Improved message clarity"
                    ],
                    time_horizon="medium_term"
                )
                insights.append(insight)
        
        return insights
    
    async def _store_pattern(self, pattern: SocialPattern, conn):
        """Store identified pattern in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO social_patterns 
            (pattern_type, title, description, participants, pattern_strength,
             frequency, trend_direction, first_observed, last_observed,
             supporting_evidence, related_metrics, impact_assessment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.pattern_type.value, pattern.title, pattern.description,
            json.dumps(pattern.participants), pattern.pattern_strength,
            pattern.frequency, pattern.trend_direction.value,
            pattern.first_observed.isoformat(), pattern.last_observed.isoformat(),
            json.dumps(pattern.supporting_evidence), json.dumps(pattern.related_metrics),
            json.dumps(pattern.impact_assessment), pattern.created_at.isoformat()
        ))
        
        pattern.id = cursor.lastrowid
    
    async def _store_insight(self, insight: SocialInsight, conn):
        """Store generated insight in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO social_insights 
            (insight_type, title, description, related_patterns, affected_individuals,
             affected_groups, confidence_score, priority, actionable_recommendations,
             expected_outcomes, time_horizon, supporting_data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            insight.insight_type.value, insight.title, insight.description,
            json.dumps(insight.related_patterns), json.dumps(insight.affected_individuals),
            json.dumps(insight.affected_groups), insight.confidence_score,
            insight.priority, json.dumps(insight.actionable_recommendations),
            json.dumps(insight.expected_outcomes), insight.time_horizon,
            json.dumps(insight.supporting_data), insight.created_at.isoformat()
        ))
        
        insight.id = cursor.lastrowid
    
    async def get_insights_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """Get a summary of insights and patterns"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Get insights count by type
        cursor.execute("""
            SELECT insight_type, COUNT(*) as count, AVG(confidence_score) as avg_confidence
            FROM social_insights 
            WHERE created_at >= ?
            GROUP BY insight_type
        """, (start_date.isoformat(),))
        
        insight_summary = {}
        for row in cursor.fetchall():
            insight_summary[row[0]] = {
                'count': row[1],
                'average_confidence': round(row[2], 3)
            }
        
        # Get patterns count by type
        cursor.execute("""
            SELECT pattern_type, COUNT(*) as count, AVG(pattern_strength) as avg_strength
            FROM social_patterns 
            WHERE last_observed >= ?
            GROUP BY pattern_type
        """, (start_date.isoformat(),))
        
        pattern_summary = {}
        for row in cursor.fetchall():
            pattern_summary[row[0]] = {
                'count': row[1],
                'average_strength': round(row[2], 3)
            }
        
        # Get high-priority insights
        cursor.execute("""
            SELECT title, priority, confidence_score 
            FROM social_insights 
            WHERE created_at >= ? AND priority IN ('high', 'critical')
            ORDER BY confidence_score DESC
            LIMIT 5
        """, (start_date.isoformat(),))
        
        high_priority_insights = []
        for row in cursor.fetchall():
            high_priority_insights.append({
                'title': row[0],
                'priority': row[1],
                'confidence': row[2]
            })
        
        conn.close()
        
        return {
            'analysis_period_days': days_back,
            'insights_by_type': insight_summary,
            'patterns_by_type': pattern_summary,
            'high_priority_insights': high_priority_insights,
            'total_insights': sum(data['count'] for data in insight_summary.values()),
            'total_patterns': sum(data['count'] for data in pattern_summary.values())
        }

# Demo function
async def demo_social_pattern_analyzer():
    """Demonstrate the Social Pattern Analyzer functionality"""
    print("🔍 Social Pattern Insights Demo")
    print("=" * 50)
    
    analyzer = SocialPatternAnalyzer()
    
    print("\n✅ Social Pattern Analyzer Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_social_pattern_analyzer())