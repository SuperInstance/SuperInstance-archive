"""
Relationship Strength Mapping System

Advanced AI system for analyzing and mapping the strength, quality, and dynamics
of personal and professional relationships through interaction patterns, 
communication analysis, and behavioral indicators.
"""

import asyncio
import sqlite3
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Any
from enum import Enum
import numpy as np
import networkx as nx
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RelationshipType(Enum):
    FAMILY = "family"
    FRIEND = "friend"
    ROMANTIC = "romantic"
    COLLEAGUE = "colleague"
    MENTOR = "mentor"
    ACQUAINTANCE = "acquaintance"
    PROFESSIONAL = "professional"
    BUSINESS = "business"

class InteractionChannel(Enum):
    EMAIL = "email"
    TEXT = "text"
    PHONE = "phone"
    VIDEO_CALL = "video_call"
    IN_PERSON = "in_person"
    SOCIAL_MEDIA = "social_media"
    MESSAGING = "messaging"
    COLLABORATION_TOOL = "collaboration_tool"

class RelationshipStrength(Enum):
    VERY_STRONG = "very_strong"      # 0.8-1.0
    STRONG = "strong"                # 0.6-0.8
    MODERATE = "moderate"            # 0.4-0.6
    WEAK = "weak"                    # 0.2-0.4
    VERY_WEAK = "very_weak"          # 0.0-0.2

@dataclass
class Interaction:
    interaction_id: str
    user_id: str
    contact_id: str
    channel: InteractionChannel
    direction: str  # "outgoing", "incoming", "mutual"
    timestamp: datetime
    duration: Optional[int] = None  # seconds for calls, None for messages
    content_analysis: Dict[str, Any] = field(default_factory=dict)
    sentiment: Optional[float] = None
    response_time: Optional[int] = None  # seconds
    context: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RelationshipMetrics:
    user_id: str
    contact_id: str
    relationship_type: RelationshipType
    strength_score: float
    strength_category: RelationshipStrength
    interaction_frequency: float
    communication_balance: float
    response_consistency: float
    sentiment_trend: float
    trust_indicators: float
    shared_connections: int
    relationship_age: int  # days
    last_interaction: datetime
    analysis_date: datetime = field(default_factory=datetime.now)

@dataclass
class RelationshipInsight:
    insight_id: str
    user_id: str
    contact_id: str
    insight_type: str
    description: str
    confidence: float
    actionable_suggestions: List[str] = field(default_factory=list)
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)
    generated_date: datetime = field(default_factory=datetime.now)

@dataclass
class ConnectionPattern:
    pattern_id: str
    user_id: str
    pattern_type: str
    description: str
    affected_relationships: List[str] = field(default_factory=list)
    pattern_strength: float = 0.0
    temporal_trends: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

@dataclass
class RelationshipNode:
    node_id: str
    user_id: str
    contact_id: str
    relationship_metrics: RelationshipMetrics
    centrality_measures: Dict[str, float] = field(default_factory=dict)
    community_membership: Optional[str] = None
    influence_score: float = 0.0

class RelationshipMapper:
    def __init__(self, db_path: str = "social_ai.db"):
        self.db_path = db_path
        self.relationship_graph = nx.Graph()
        self.scaler = StandardScaler()
        self.clustering_model = KMeans(n_clusters=5, random_state=42)
        self.init_database()
        
    def init_database(self):
        """Initialize database tables for relationship mapping"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                user_id TEXT,
                contact_id TEXT,
                channel TEXT,
                direction TEXT,
                timestamp TIMESTAMP,
                duration INTEGER,
                content_analysis TEXT,
                sentiment REAL,
                response_time INTEGER,
                context TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationship_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                contact_id TEXT,
                relationship_type TEXT,
                strength_score REAL,
                strength_category TEXT,
                interaction_frequency REAL,
                communication_balance REAL,
                response_consistency REAL,
                sentiment_trend REAL,
                trust_indicators REAL,
                shared_connections INTEGER,
                relationship_age INTEGER,
                last_interaction TIMESTAMP,
                analysis_date TIMESTAMP,
                UNIQUE(user_id, contact_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS relationship_insights (
                insight_id TEXT PRIMARY KEY,
                user_id TEXT,
                contact_id TEXT,
                insight_type TEXT,
                description TEXT,
                confidence REAL,
                actionable_suggestions TEXT,
                supporting_evidence TEXT,
                generated_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connection_patterns (
                pattern_id TEXT PRIMARY KEY,
                user_id TEXT,
                pattern_type TEXT,
                description TEXT,
                affected_relationships TEXT,
                pattern_strength REAL,
                temporal_trends TEXT,
                recommendations TEXT,
                created_date TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_graph (
                edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                contact_id TEXT,
                relationship_strength REAL,
                relationship_type TEXT,
                edge_weight REAL,
                last_updated TIMESTAMP,
                UNIQUE(user_id, contact_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("Relationship mapping database initialized")

    async def record_interaction(self, interaction: Interaction) -> Interaction:
        """
        Record a social interaction for relationship analysis
        
        Args:
            interaction: Interaction data to record
            
        Returns:
            Processed interaction with analysis
        """
        # Enhance interaction with analysis
        enhanced_interaction = await self._analyze_interaction(interaction)
        
        # Save to database
        await self._save_interaction(enhanced_interaction)
        
        # Update relationship metrics
        await self.update_relationship_metrics(interaction.user_id, interaction.contact_id)
        
        # Update social graph
        await self._update_social_graph(interaction.user_id, interaction.contact_id)
        
        logger.info(f"Recorded interaction between {interaction.user_id} and {interaction.contact_id}")
        return enhanced_interaction

    async def analyze_relationship_strength(self, user_id: str, contact_id: str) -> RelationshipMetrics:
        """
        Analyze the strength and quality of a relationship
        
        Args:
            user_id: Primary user identifier
            contact_id: Contact/relationship partner identifier
            
        Returns:
            Comprehensive relationship metrics
        """
        # Get recent interactions
        interactions = await self._get_interactions(user_id, contact_id, days_back=365)
        
        if not interactions:
            # Create minimal metrics for new relationship
            return RelationshipMetrics(
                user_id=user_id,
                contact_id=contact_id,
                relationship_type=RelationshipType.ACQUAINTANCE,
                strength_score=0.0,
                strength_category=RelationshipStrength.VERY_WEAK,
                interaction_frequency=0.0,
                communication_balance=0.5,
                response_consistency=0.0,
                sentiment_trend=0.5,
                trust_indicators=0.0,
                shared_connections=0,
                relationship_age=0,
                last_interaction=datetime.now()
            )
        
        # Calculate relationship metrics
        interaction_frequency = self._calculate_interaction_frequency(interactions)
        communication_balance = self._calculate_communication_balance(interactions)
        response_consistency = self._calculate_response_consistency(interactions)
        sentiment_trend = self._calculate_sentiment_trend(interactions)
        trust_indicators = self._calculate_trust_indicators(interactions)
        shared_connections = await self._count_shared_connections(user_id, contact_id)
        relationship_age = (datetime.now() - min(i.timestamp for i in interactions)).days
        
        # Calculate overall strength score
        strength_score = self._calculate_strength_score(
            interaction_frequency, communication_balance, response_consistency,
            sentiment_trend, trust_indicators, shared_connections, relationship_age
        )
        
        # Classify relationship type and strength
        relationship_type = await self._classify_relationship_type(user_id, contact_id, interactions)
        strength_category = self._classify_strength_category(strength_score)
        
        metrics = RelationshipMetrics(
            user_id=user_id,
            contact_id=contact_id,
            relationship_type=relationship_type,
            strength_score=strength_score,
            strength_category=strength_category,
            interaction_frequency=interaction_frequency,
            communication_balance=communication_balance,
            response_consistency=response_consistency,
            sentiment_trend=sentiment_trend,
            trust_indicators=trust_indicators,
            shared_connections=shared_connections,
            relationship_age=relationship_age,
            last_interaction=max(i.timestamp for i in interactions)
        )
        
        await self._save_relationship_metrics(metrics)
        return metrics

    async def update_relationship_metrics(self, user_id: str, contact_id: str):
        """Update relationship metrics after new interaction"""
        await self.analyze_relationship_strength(user_id, contact_id)

    async def get_relationship_insights(self, user_id: str, contact_id: str) -> List[RelationshipInsight]:
        """
        Generate actionable insights about a relationship
        
        Args:
            user_id: Primary user identifier
            contact_id: Contact identifier
            
        Returns:
            List of relationship insights and recommendations
        """
        # Get current metrics
        metrics = await self.analyze_relationship_strength(user_id, contact_id)
        interactions = await self._get_interactions(user_id, contact_id, days_back=90)
        
        insights = []
        
        # Communication frequency insights
        if metrics.interaction_frequency < 0.1:  # Less than once per 10 days
            insight = RelationshipInsight(
                insight_id=f"freq_{user_id}_{contact_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                contact_id=contact_id,
                insight_type="communication_frequency",
                description="Low communication frequency detected",
                confidence=0.8,
                actionable_suggestions=[
                    "Consider reaching out more regularly",
                    "Schedule periodic check-ins",
                    "Share interesting content or updates"
                ],
                supporting_evidence={
                    "avg_days_between_contact": 1.0 / metrics.interaction_frequency if metrics.interaction_frequency > 0 else 999,
                    "last_interaction_days_ago": (datetime.now() - metrics.last_interaction).days
                }
            )
            insights.append(insight)
        
        # Communication balance insights
        if metrics.communication_balance < 0.3 or metrics.communication_balance > 0.7:
            balance_type = "one-sided" if metrics.communication_balance < 0.3 else "heavily initiated by you"
            insight = RelationshipInsight(
                insight_id=f"balance_{user_id}_{contact_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                contact_id=contact_id,
                insight_type="communication_balance",
                description=f"Communication appears {balance_type}",
                confidence=0.7,
                actionable_suggestions=[
                    "Try varying your communication approach",
                    "Give space for the other person to initiate",
                    "Ask engaging questions to encourage responses"
                ],
                supporting_evidence={
                    "communication_balance_score": metrics.communication_balance,
                    "outgoing_percentage": metrics.communication_balance * 100
                }
            )
            insights.append(insight)
        
        # Response consistency insights
        if metrics.response_consistency < 0.5:
            insight = RelationshipInsight(
                insight_id=f"response_{user_id}_{contact_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                contact_id=contact_id,
                insight_type="response_patterns",
                description="Inconsistent response patterns detected",
                confidence=0.6,
                actionable_suggestions=[
                    "Be more consistent in your response timing",
                    "Consider their preferred communication style",
                    "Respect their communication boundaries"
                ],
                supporting_evidence={
                    "response_consistency_score": metrics.response_consistency
                }
            )
            insights.append(insight)
        
        # Sentiment trend insights
        if metrics.sentiment_trend < 0.4:
            insight = RelationshipInsight(
                insight_id=f"sentiment_{user_id}_{contact_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                contact_id=contact_id,
                insight_type="sentiment_trend",
                description="Recent communications have been less positive",
                confidence=0.6,
                actionable_suggestions=[
                    "Focus on positive, uplifting communications",
                    "Share good news and celebrations",
                    "Check in on their wellbeing",
                    "Consider addressing any underlying issues"
                ],
                supporting_evidence={
                    "sentiment_trend_score": metrics.sentiment_trend,
                    "recent_sentiment_average": metrics.sentiment_trend
                }
            )
            insights.append(insight)
        
        # Relationship strength insights
        if metrics.strength_score > 0.8:
            insight = RelationshipInsight(
                insight_id=f"strength_{user_id}_{contact_id}_{int(datetime.now().timestamp())}",
                user_id=user_id,
                contact_id=contact_id,
                insight_type="relationship_strength",
                description="Very strong relationship - excellent foundation",
                confidence=0.9,
                actionable_suggestions=[
                    "Continue nurturing this valuable relationship",
                    "Consider deeper collaborations or shared activities",
                    "This person could be a great reference or advocate"
                ],
                supporting_evidence={
                    "strength_score": metrics.strength_score,
                    "strength_category": metrics.strength_category.value
                }
            )
            insights.append(insight)
        
        # Save insights
        for insight in insights:
            await self._save_insight(insight)
        
        return insights

    async def analyze_social_patterns(self, user_id: str) -> List[ConnectionPattern]:
        """
        Analyze patterns in user's social connections and behavior
        
        Args:
            user_id: User to analyze
            
        Returns:
            List of identified social patterns
        """
        # Get all relationships for user
        relationships = await self._get_user_relationships(user_id)
        interactions = await self._get_user_interactions(user_id, days_back=180)
        
        patterns = []
        
        # Communication timing patterns
        timing_pattern = await self._analyze_timing_patterns(interactions)
        if timing_pattern:
            patterns.append(timing_pattern)
        
        # Relationship maintenance patterns
        maintenance_pattern = await self._analyze_maintenance_patterns(relationships)
        if maintenance_pattern:
            patterns.append(maintenance_pattern)
        
        # Channel preference patterns
        channel_pattern = await self._analyze_channel_preferences(interactions)
        if channel_pattern:
            patterns.append(channel_pattern)
        
        # Social energy patterns
        energy_pattern = await self._analyze_social_energy_patterns(interactions)
        if energy_pattern:
            patterns.append(energy_pattern)
        
        # Save patterns
        for pattern in patterns:
            await self._save_connection_pattern(pattern)
        
        return patterns

    async def build_relationship_network(self, user_id: str) -> nx.Graph:
        """
        Build a network graph of user's relationships
        
        Args:
            user_id: Central user for the network
            
        Returns:
            NetworkX graph of relationships
        """
        # Get user's relationships
        relationships = await self._get_user_relationships(user_id)
        
        # Build graph
        G = nx.Graph()
        
        # Add central user node
        G.add_node(user_id, node_type="user", centrality=1.0)
        
        # Add relationship nodes and edges
        for rel in relationships:
            contact_id = rel.contact_id
            G.add_node(contact_id, node_type="contact", 
                      relationship_type=rel.relationship_type.value)
            
            # Add edge with weight based on relationship strength
            G.add_edge(user_id, contact_id, 
                      weight=rel.strength_score,
                      relationship_type=rel.relationship_type.value)
        
        # Add connections between contacts (if known)
        await self._add_contact_connections(G, user_id)
        
        # Calculate network metrics
        self._calculate_network_metrics(G)
        
        # Update social graph in database
        await self._update_network_in_db(user_id, G)
        
        self.relationship_graph = G
        return G

    def _calculate_interaction_frequency(self, interactions: List[Interaction]) -> float:
        """Calculate interaction frequency (interactions per day)"""
        if not interactions:
            return 0.0
        
        time_span = (max(i.timestamp for i in interactions) - 
                    min(i.timestamp for i in interactions)).days
        
        if time_span == 0:
            return len(interactions)  # All interactions on same day
        
        return len(interactions) / time_span

    def _calculate_communication_balance(self, interactions: List[Interaction]) -> float:
        """Calculate balance of outgoing vs incoming communication (0-1, 0.5 = balanced)"""
        if not interactions:
            return 0.5
        
        outgoing = sum(1 for i in interactions if i.direction == "outgoing")
        total = len(interactions)
        
        return outgoing / total

    def _calculate_response_consistency(self, interactions: List[Interaction]) -> float:
        """Calculate consistency of response patterns"""
        if not interactions:
            return 0.0
        
        # Sort by timestamp
        sorted_interactions = sorted(interactions, key=lambda x: x.timestamp)
        
        response_times = []
        for i in range(1, len(sorted_interactions)):
            prev = sorted_interactions[i-1]
            curr = sorted_interactions[i]
            
            # If current is a response to previous
            if prev.direction == "outgoing" and curr.direction == "incoming":
                response_time = (curr.timestamp - prev.timestamp).total_seconds()
                if response_time < 86400 * 7:  # Within a week
                    response_times.append(response_time)
        
        if not response_times:
            return 0.0
        
        # Calculate coefficient of variation (lower = more consistent)
        mean_time = np.mean(response_times)
        std_time = np.std(response_times)
        
        if mean_time == 0:
            return 1.0
        
        cv = std_time / mean_time
        consistency = max(0.0, 1.0 - min(cv, 1.0))  # Invert and cap
        
        return consistency

    def _calculate_sentiment_trend(self, interactions: List[Interaction]) -> float:
        """Calculate overall sentiment trend (0-1, 1 = very positive)"""
        if not interactions:
            return 0.5
        
        # Weight recent interactions more heavily
        now = datetime.now()
        weighted_sentiments = []
        
        for interaction in interactions:
            if interaction.sentiment is not None:
                days_ago = (now - interaction.timestamp).days
                weight = np.exp(-days_ago / 30)  # Exponential decay over 30 days
                weighted_sentiments.append(interaction.sentiment * weight)
        
        if not weighted_sentiments:
            return 0.5
        
        avg_sentiment = np.mean(weighted_sentiments)
        # Normalize from [-1, 1] to [0, 1]
        return (avg_sentiment + 1) / 2

    def _calculate_trust_indicators(self, interactions: List[Interaction]) -> float:
        """Calculate trust indicators based on interaction patterns"""
        if not interactions:
            return 0.0
        
        trust_score = 0.0
        
        # Consistency in communication
        if len(interactions) > 5:
            trust_score += 0.2
        
        # Response rate
        outgoing = [i for i in interactions if i.direction == "outgoing"]
        incoming = [i for i in interactions if i.direction == "incoming"]
        
        if outgoing:
            response_rate = len(incoming) / len(outgoing)
            trust_score += min(response_rate * 0.3, 0.3)
        
        # Length of relationship
        if interactions:
            relationship_days = (max(i.timestamp for i in interactions) - 
                               min(i.timestamp for i in interactions)).days
            longevity_score = min(relationship_days / 365 * 0.2, 0.2)
            trust_score += longevity_score
        
        # Channel diversity (using multiple communication channels indicates comfort)
        channels_used = len(set(i.channel for i in interactions))
        channel_diversity = min(channels_used / 5 * 0.3, 0.3)
        trust_score += channel_diversity
        
        return min(trust_score, 1.0)

    def _calculate_strength_score(self, frequency: float, balance: float, 
                                consistency: float, sentiment: float, 
                                trust: float, shared_connections: int, 
                                relationship_age: int) -> float:
        """Calculate overall relationship strength score"""
        
        # Normalize frequency (cap at 1 interaction per day)
        freq_score = min(frequency, 1.0)
        
        # Balance score (penalize extremes)
        balance_score = 1.0 - abs(balance - 0.5) * 2
        
        # Age bonus (relationships get stronger over time, up to a point)
        age_bonus = min(relationship_age / 365, 1.0) * 0.1
        
        # Shared connections bonus
        shared_bonus = min(shared_connections / 10, 0.1)
        
        # Weighted combination
        strength = (
            freq_score * 0.25 +
            balance_score * 0.15 +
            consistency * 0.2 +
            sentiment * 0.2 +
            trust * 0.2 +
            age_bonus +
            shared_bonus
        )
        
        return min(strength, 1.0)

    def _classify_strength_category(self, strength_score: float) -> RelationshipStrength:
        """Classify relationship strength into categories"""
        if strength_score >= 0.8:
            return RelationshipStrength.VERY_STRONG
        elif strength_score >= 0.6:
            return RelationshipStrength.STRONG
        elif strength_score >= 0.4:
            return RelationshipStrength.MODERATE
        elif strength_score >= 0.2:
            return RelationshipStrength.WEAK
        else:
            return RelationshipStrength.VERY_WEAK

    async def _classify_relationship_type(self, user_id: str, contact_id: str, 
                                        interactions: List[Interaction]) -> RelationshipType:
        """Classify the type of relationship based on interaction patterns"""
        
        # Analyze communication patterns
        channels = [i.channel for i in interactions]
        channel_diversity = len(set(channels))
        
        # Professional indicators
        professional_channels = sum(1 for c in channels if c in [
            InteractionChannel.EMAIL, InteractionChannel.COLLABORATION_TOOL
        ])
        
        # Personal indicators  
        personal_channels = sum(1 for c in channels if c in [
            InteractionChannel.TEXT, InteractionChannel.PHONE, InteractionChannel.IN_PERSON
        ])
        
        # Time patterns (professional relationships often during business hours)
        business_hours = sum(1 for i in interactions if 9 <= i.timestamp.hour <= 17)
        business_hour_ratio = business_hours / len(interactions)
        
        # Default classification logic (simplified)
        if professional_channels > personal_channels and business_hour_ratio > 0.7:
            return RelationshipType.COLLEAGUE
        elif personal_channels > professional_channels * 2:
            return RelationshipType.FRIEND
        else:
            return RelationshipType.ACQUAINTANCE

    async def _analyze_interaction(self, interaction: Interaction) -> Interaction:
        """Analyze and enhance interaction data"""
        # Simple sentiment analysis (in real implementation, would use NLP)
        if not interaction.sentiment:
            interaction.sentiment = np.random.uniform(-0.2, 0.8)  # Slight positive bias
        
        # Add content analysis
        interaction.content_analysis = {
            "analyzed_at": datetime.now().isoformat(),
            "confidence": 0.7
        }
        
        return interaction

    async def _count_shared_connections(self, user_id: str, contact_id: str) -> int:
        """Count shared connections between two users"""
        # Simplified implementation - in real system would query actual connections
        return np.random.randint(0, 5)

    async def _get_interactions(self, user_id: str, contact_id: str, days_back: int = 90) -> List[Interaction]:
        """Get interactions between two users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        cursor.execute('''
            SELECT interaction_id, user_id, contact_id, channel, direction, timestamp,
                   duration, content_analysis, sentiment, response_time, context, metadata
            FROM interactions
            WHERE ((user_id = ? AND contact_id = ?) OR (user_id = ? AND contact_id = ?))
            AND timestamp > ?
            ORDER BY timestamp
        ''', (user_id, contact_id, contact_id, user_id, cutoff_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in rows:
            interaction = Interaction(
                interaction_id=row[0],
                user_id=row[1],
                contact_id=row[2],
                channel=InteractionChannel(row[3]),
                direction=row[4],
                timestamp=datetime.fromisoformat(row[5]),
                duration=row[6],
                content_analysis=json.loads(row[7]) if row[7] else {},
                sentiment=row[8],
                response_time=row[9],
                context=row[10],
                metadata=json.loads(row[11]) if row[11] else {}
            )
            interactions.append(interaction)
        
        return interactions

    async def _get_user_relationships(self, user_id: str) -> List[RelationshipMetrics]:
        """Get all relationships for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, contact_id, relationship_type, strength_score,
                   strength_category, interaction_frequency, communication_balance,
                   response_consistency, sentiment_trend, trust_indicators,
                   shared_connections, relationship_age, last_interaction, analysis_date
            FROM relationship_metrics
            WHERE user_id = ?
            ORDER BY strength_score DESC
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        relationships = []
        for row in rows:
            metrics = RelationshipMetrics(
                user_id=row[0],
                contact_id=row[1],
                relationship_type=RelationshipType(row[2]),
                strength_score=row[3],
                strength_category=RelationshipStrength(row[4]),
                interaction_frequency=row[5],
                communication_balance=row[6],
                response_consistency=row[7],
                sentiment_trend=row[8],
                trust_indicators=row[9],
                shared_connections=row[10],
                relationship_age=row[11],
                last_interaction=datetime.fromisoformat(row[12]),
                analysis_date=datetime.fromisoformat(row[13])
            )
            relationships.append(metrics)
        
        return relationships

    async def _get_user_interactions(self, user_id: str, days_back: int = 90) -> List[Interaction]:
        """Get all interactions for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        cursor.execute('''
            SELECT interaction_id, user_id, contact_id, channel, direction, timestamp,
                   duration, content_analysis, sentiment, response_time, context, metadata
            FROM interactions
            WHERE user_id = ? AND timestamp > ?
            ORDER BY timestamp
        ''', (user_id, cutoff_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in rows:
            interaction = Interaction(
                interaction_id=row[0],
                user_id=row[1],
                contact_id=row[2],
                channel=InteractionChannel(row[3]),
                direction=row[4],
                timestamp=datetime.fromisoformat(row[5]),
                duration=row[6],
                content_analysis=json.loads(row[7]) if row[7] else {},
                sentiment=row[8],
                response_time=row[9],
                context=row[10],
                metadata=json.loads(row[11]) if row[11] else {}
            )
            interactions.append(interaction)
        
        return interactions

    async def _analyze_timing_patterns(self, interactions: List[Interaction]) -> Optional[ConnectionPattern]:
        """Analyze timing patterns in interactions"""
        if len(interactions) < 10:
            return None
        
        # Analyze by hour of day
        hours = [i.timestamp.hour for i in interactions]
        hour_dist = np.bincount(hours, minlength=24)
        peak_hours = np.argsort(hour_dist)[-3:]  # Top 3 hours
        
        pattern = ConnectionPattern(
            pattern_id=f"timing_{interactions[0].user_id}_{int(datetime.now().timestamp())}",
            user_id=interactions[0].user_id,
            pattern_type="timing_preferences",
            description=f"Most active during hours: {', '.join(f'{h:02d}:00' for h in peak_hours)}",
            pattern_strength=np.max(hour_dist) / len(interactions),
            temporal_trends={
                "peak_hours": peak_hours.tolist(),
                "hour_distribution": hour_dist.tolist()
            },
            recommendations=[
                "Schedule important conversations during peak activity times",
                "Respect quiet hours for non-urgent communications"
            ]
        )
        
        return pattern

    async def _analyze_maintenance_patterns(self, relationships: List[RelationshipMetrics]) -> Optional[ConnectionPattern]:
        """Analyze relationship maintenance patterns"""
        if len(relationships) < 5:
            return None
        
        # Analyze relationship strength distribution
        strengths = [r.strength_score for r in relationships]
        avg_strength = np.mean(strengths)
        
        strong_relationships = sum(1 for s in strengths if s > 0.6)
        total_relationships = len(relationships)
        
        pattern = ConnectionPattern(
            pattern_id=f"maintenance_{relationships[0].user_id}_{int(datetime.now().timestamp())}",
            user_id=relationships[0].user_id,
            pattern_type="relationship_maintenance",
            description=f"{strong_relationships}/{total_relationships} relationships are strong",
            pattern_strength=strong_relationships / total_relationships,
            temporal_trends={
                "average_strength": avg_strength,
                "strength_distribution": {
                    "very_strong": sum(1 for s in strengths if s >= 0.8),
                    "strong": sum(1 for s in strengths if 0.6 <= s < 0.8),
                    "moderate": sum(1 for s in strengths if 0.4 <= s < 0.6),
                    "weak": sum(1 for s in strengths if s < 0.4)
                }
            },
            recommendations=[
                "Focus on strengthening moderate relationships",
                "Regular check-ins with strong relationships to maintain them",
                "Consider if weak relationships should be maintained or naturally fade"
            ]
        )
        
        return pattern

    async def _analyze_channel_preferences(self, interactions: List[Interaction]) -> Optional[ConnectionPattern]:
        """Analyze communication channel preferences"""
        if len(interactions) < 10:
            return None
        
        channels = [i.channel.value for i in interactions]
        channel_counts = {}
        for channel in channels:
            channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        preferred_channels = sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        pattern = ConnectionPattern(
            pattern_id=f"channels_{interactions[0].user_id}_{int(datetime.now().timestamp())}",
            user_id=interactions[0].user_id,
            pattern_type="channel_preferences",
            description=f"Prefers: {', '.join(ch for ch, _ in preferred_channels)}",
            pattern_strength=preferred_channels[0][1] / len(interactions),
            temporal_trends={
                "channel_distribution": channel_counts,
                "preferred_channels": preferred_channels
            },
            recommendations=[
                "Use preferred channels for important communications",
                "Consider diversifying communication channels",
                "Match channel choice to relationship type and context"
            ]
        )
        
        return pattern

    async def _analyze_social_energy_patterns(self, interactions: List[Interaction]) -> Optional[ConnectionPattern]:
        """Analyze social energy and interaction intensity patterns"""
        if len(interactions) < 20:
            return None
        
        # Group interactions by week
        weekly_counts = {}
        for interaction in interactions:
            week_key = interaction.timestamp.strftime("%Y-W%U")
            weekly_counts[week_key] = weekly_counts.get(week_key, 0) + 1
        
        if len(weekly_counts) < 4:
            return None
        
        weekly_values = list(weekly_counts.values())
        avg_weekly = np.mean(weekly_values)
        std_weekly = np.std(weekly_values)
        
        consistency_score = 1.0 - min(std_weekly / avg_weekly if avg_weekly > 0 else 1, 1.0)
        
        pattern = ConnectionPattern(
            pattern_id=f"energy_{interactions[0].user_id}_{int(datetime.now().timestamp())}",
            user_id=interactions[0].user_id,
            pattern_type="social_energy",
            description=f"Social activity: {avg_weekly:.1f} interactions/week (consistency: {consistency_score:.1%})",
            pattern_strength=consistency_score,
            temporal_trends={
                "average_weekly_interactions": avg_weekly,
                "consistency_score": consistency_score,
                "weekly_distribution": weekly_counts
            },
            recommendations=[
                "Plan social activities during high-energy periods" if consistency_score > 0.7 
                else "Work on maintaining more consistent social engagement",
                "Balance high-intensity social periods with recovery time"
            ]
        )
        
        return pattern

    async def _add_contact_connections(self, G: nx.Graph, user_id: str):
        """Add known connections between user's contacts"""
        # Simplified implementation - in real system would have mutual connection data
        contacts = [n for n in G.nodes() if n != user_id]
        
        # Add some random connections between contacts
        for i, contact1 in enumerate(contacts):
            for contact2 in contacts[i+1:]:
                if np.random.random() < 0.1:  # 10% chance of connection
                    G.add_edge(contact1, contact2, weight=0.3, relationship_type="mutual_contact")

    def _calculate_network_metrics(self, G: nx.Graph):
        """Calculate network analysis metrics"""
        if len(G.nodes()) < 2:
            return
        
        # Calculate centrality measures
        try:
            betweenness = nx.betweenness_centrality(G)
            closeness = nx.closeness_centrality(G)
            degree = nx.degree_centrality(G)
            
            for node in G.nodes():
                G.nodes[node]['betweenness_centrality'] = betweenness.get(node, 0)
                G.nodes[node]['closeness_centrality'] = closeness.get(node, 0)
                G.nodes[node]['degree_centrality'] = degree.get(node, 0)
                
        except Exception as e:
            logger.warning(f"Error calculating network metrics: {e}")

    async def _update_social_graph(self, user_id: str, contact_id: str):
        """Update social graph in database"""
        # Get current relationship metrics
        try:
            metrics = await self.analyze_relationship_strength(user_id, contact_id)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO social_graph
                (user_id, contact_id, relationship_strength, relationship_type, 
                 edge_weight, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, contact_id, metrics.strength_score, 
                  metrics.relationship_type.value, metrics.strength_score, 
                  datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating social graph: {e}")

    async def _update_network_in_db(self, user_id: str, G: nx.Graph):
        """Update complete network in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing network data for user
        cursor.execute('DELETE FROM social_graph WHERE user_id = ?', (user_id,))
        
        # Insert new network data
        for edge in G.edges(data=True):
            user, contact = edge[0], edge[1]
            edge_data = edge[2]
            
            if user == user_id or contact == user_id:
                cursor.execute('''
                    INSERT INTO social_graph
                    (user_id, contact_id, relationship_strength, relationship_type,
                     edge_weight, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user if user == user_id else contact,
                      contact if user == user_id else user,
                      edge_data.get('weight', 0.5),
                      edge_data.get('relationship_type', 'unknown'),
                      edge_data.get('weight', 0.5),
                      datetime.now()))
        
        conn.commit()
        conn.close()

    async def _save_interaction(self, interaction: Interaction):
        """Save interaction to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO interactions
            (interaction_id, user_id, contact_id, channel, direction, timestamp,
             duration, content_analysis, sentiment, response_time, context, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (interaction.interaction_id, interaction.user_id, interaction.contact_id,
              interaction.channel.value, interaction.direction, interaction.timestamp,
              interaction.duration, json.dumps(interaction.content_analysis),
              interaction.sentiment, interaction.response_time, interaction.context,
              json.dumps(interaction.metadata)))
        
        conn.commit()
        conn.close()

    async def _save_relationship_metrics(self, metrics: RelationshipMetrics):
        """Save relationship metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO relationship_metrics
            (user_id, contact_id, relationship_type, strength_score, strength_category,
             interaction_frequency, communication_balance, response_consistency,
             sentiment_trend, trust_indicators, shared_connections, relationship_age,
             last_interaction, analysis_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (metrics.user_id, metrics.contact_id, metrics.relationship_type.value,
              metrics.strength_score, metrics.strength_category.value,
              metrics.interaction_frequency, metrics.communication_balance,
              metrics.response_consistency, metrics.sentiment_trend,
              metrics.trust_indicators, metrics.shared_connections,
              metrics.relationship_age, metrics.last_interaction, metrics.analysis_date))
        
        conn.commit()
        conn.close()

    async def _save_insight(self, insight: RelationshipInsight):
        """Save relationship insight to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO relationship_insights
            (insight_id, user_id, contact_id, insight_type, description, confidence,
             actionable_suggestions, supporting_evidence, generated_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (insight.insight_id, insight.user_id, insight.contact_id,
              insight.insight_type, insight.description, insight.confidence,
              json.dumps(insight.actionable_suggestions),
              json.dumps(insight.supporting_evidence), insight.generated_date))
        
        conn.commit()
        conn.close()

    async def _save_connection_pattern(self, pattern: ConnectionPattern):
        """Save connection pattern to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO connection_patterns
            (pattern_id, user_id, pattern_type, description, affected_relationships,
             pattern_strength, temporal_trends, recommendations, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (pattern.pattern_id, pattern.user_id, pattern.pattern_type,
              pattern.description, json.dumps(pattern.affected_relationships),
              pattern.pattern_strength, json.dumps(pattern.temporal_trends),
              json.dumps(pattern.recommendations), datetime.now()))
        
        conn.commit()
        conn.close()

async def demo_relationship_mapping():
    """Demonstrate relationship strength mapping"""
    mapper = RelationshipMapper()
    
    print("=== Relationship Strength Mapping Demo ===")
    
    # Create sample interactions
    interactions = [
        Interaction(
            interaction_id="int_1",
            user_id="user_alice",
            contact_id="user_bob",
            channel=InteractionChannel.EMAIL,
            direction="outgoing",
            timestamp=datetime.now() - timedelta(days=30),
            sentiment=0.7
        ),
        Interaction(
            interaction_id="int_2",
            user_id="user_bob",
            contact_id="user_alice",
            channel=InteractionChannel.EMAIL,
            direction="incoming",
            timestamp=datetime.now() - timedelta(days=29),
            sentiment=0.8
        ),
        Interaction(
            interaction_id="int_3",
            user_id="user_alice",
            contact_id="user_bob",
            channel=InteractionChannel.TEXT,
            direction="outgoing",
            timestamp=datetime.now() - timedelta(days=15),
            sentiment=0.9
        ),
        Interaction(
            interaction_id="int_4",
            user_id="user_alice",
            contact_id="user_bob",
            channel=InteractionChannel.PHONE,
            direction="outgoing",
            timestamp=datetime.now() - timedelta(days=5),
            duration=1800,  # 30 minutes
            sentiment=0.6
        )
    ]
    
    print(f"Recording {len(interactions)} interactions...")
    for interaction in interactions:
        await mapper.record_interaction(interaction)
    
    # Analyze relationship strength
    metrics = await mapper.analyze_relationship_strength("user_alice", "user_bob")
    
    print(f"\n=== Relationship Analysis ===")
    print(f"Users: user_alice ↔ user_bob")
    print(f"Relationship Type: {metrics.relationship_type.value}")
    print(f"Strength Score: {metrics.strength_score:.3f}")
    print(f"Strength Category: {metrics.strength_category.value}")
    print(f"Interaction Frequency: {metrics.interaction_frequency:.3f} per day")
    print(f"Communication Balance: {metrics.communication_balance:.3f}")
    print(f"Response Consistency: {metrics.response_consistency:.3f}")
    print(f"Sentiment Trend: {metrics.sentiment_trend:.3f}")
    print(f"Trust Indicators: {metrics.trust_indicators:.3f}")
    print(f"Relationship Age: {metrics.relationship_age} days")
    
    # Get relationship insights
    insights = await mapper.get_relationship_insights("user_alice", "user_bob")
    
    print(f"\n=== Relationship Insights ===")
    for insight in insights:
        print(f"\n{insight.insight_type.replace('_', ' ').title()}:")
        print(f"  Description: {insight.description}")
        print(f"  Confidence: {insight.confidence:.1%}")
        print("  Suggestions:")
        for suggestion in insight.actionable_suggestions:
            print(f"    • {suggestion}")
    
    # Analyze social patterns
    patterns = await mapper.analyze_social_patterns("user_alice")
    
    print(f"\n=== Social Patterns ===")
    for pattern in patterns:
        print(f"\n{pattern.pattern_type.replace('_', ' ').title()}:")
        print(f"  Description: {pattern.description}")
        print(f"  Pattern Strength: {pattern.pattern_strength:.1%}")
        print("  Recommendations:")
        for rec in pattern.recommendations:
            print(f"    • {rec}")
    
    # Build relationship network
    network = await mapper.build_relationship_network("user_alice")
    
    print(f"\n=== Relationship Network ===")
    print(f"Network Size: {len(network.nodes())} nodes, {len(network.edges())} edges")
    
    # Show network metrics for central user
    if "user_alice" in network.nodes():
        alice_node = network.nodes["user_alice"]
        print(f"Alice's Network Position:")
        print(f"  Degree Centrality: {alice_node.get('degree_centrality', 0):.3f}")
        print(f"  Betweenness Centrality: {alice_node.get('betweenness_centrality', 0):.3f}")
        print(f"  Closeness Centrality: {alice_node.get('closeness_centrality', 0):.3f}")

if __name__ == "__main__":
    asyncio.run(demo_relationship_mapping())