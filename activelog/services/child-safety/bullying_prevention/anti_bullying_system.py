import asyncio
import asyncpg
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re
from datetime import datetime, timedelta
import logging
import hashlib


class BullyingType(Enum):
    VERBAL_AGGRESSION = "verbal_aggression"
    EXCLUSION = "exclusion"
    CYBERBULLYING = "cyberbullying"
    INTIMIDATION = "intimidation"
    HARASSMENT = "harassment"
    DISCRIMINATION = "discrimination"
    RELATIONAL_AGGRESSION = "relational_aggression"


class SeverityLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class InterventionType(Enum):
    WARNING = "warning"
    EDUCATION = "education"
    COOLING_OFF = "cooling_off"
    MEDIATION = "mediation"
    PARENT_NOTIFICATION = "parent_notification"
    TEMPORARY_RESTRICTION = "temporary_restriction"
    COUNSELING_REFERRAL = "counseling_referral"


class ParticipantRole(Enum):
    AGGRESSOR = "aggressor"
    TARGET = "target"
    BYSTANDER = "bystander"
    UPSTANDER = "upstander"  # Positive bystander who intervenes


@dataclass
class BullyingIncident:
    incident_id: str
    participants: Dict[str, ParticipantRole]  # user_id -> role
    bullying_type: BullyingType
    severity: SeverityLevel
    evidence: Dict[str, Any]  # Anonymized evidence
    context: Dict[str, Any]
    confidence_score: float
    detected_at: datetime
    resolved: bool = False
    interventions_applied: List[InterventionType] = field(default_factory=list)


@dataclass
class BullyingPattern:
    pattern_id: str
    primary_aggressor: str
    targets: List[str]
    pattern_type: str
    frequency: int
    timespan_days: int
    escalation_trend: str  # "increasing", "stable", "decreasing"
    risk_score: float


@dataclass
class SafetyEducationContent:
    content_id: str
    title: str
    description: str
    age_group: str
    content_type: str  # "interactive", "video", "article", "game"
    key_concepts: List[str]
    expected_duration_minutes: int
    effectiveness_metrics: Dict[str, float]


class AntiBullyingSystem:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)
        
        # Bullying detection patterns and keywords
        self.aggression_indicators = {
            "direct_insults": [
                "stupid", "ugly", "loser", "freak", "weirdo", "dumb", "idiot",
                "pathetic", "worthless", "nobody likes you", "you suck"
            ],
            "threats": [
                "gonna hurt you", "beat you up", "make you pay", "you're dead",
                "wait until", "after school", "gonna get you"
            ],
            "exclusion_language": [
                "nobody wants you here", "you don't belong", "get lost",
                "we don't want you", "go away", "leave us alone"
            ],
            "cyberbullying_patterns": [
                "kill yourself", "kys", "everyone hates you", "you should die",
                "no one would miss you", "wish you were dead"
            ],
            "discriminatory_language": [
                # Note: This would include age-appropriate detection of discriminatory language
                # while being sensitive to context and avoiding false positives
                "hate_speech_pattern", "discriminatory_slur", "prejudiced_comment"
            ]
        }
        
        # Positive interaction indicators (to avoid false positives)
        self.positive_indicators = [
            "great job", "awesome", "love this", "so cool", "amazing work",
            "you're awesome", "that's incredible", "well done", "fantastic",
            "keep it up", "proud of you", "good friend", "kind", "helpful"
        ]
        
        # Context patterns that might indicate bullying
        self.context_patterns = {
            "power_imbalance": [
                r"everyone vs \w+", r"all of us think", r"nobody likes",
                r"the whole class", r"everyone knows"
            ],
            "repeated_targeting": [
                r"again\?", r"still doing", r"always does", r"every time",
                r"keeps doing", r"won't stop"
            ],
            "social_manipulation": [
                r"don't talk to", r"ignore \w+", r"pretend \w+", 
                r"act like \w+", r"make sure nobody"
            ]
        }

    async def initialize_tables(self):
        """Initialize bullying detection and prevention tables"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bullying_incidents (
                    id SERIAL PRIMARY KEY,
                    incident_id VARCHAR(50) UNIQUE NOT NULL,
                    participants JSONB NOT NULL,
                    bullying_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    evidence JSONB NOT NULL,
                    context JSONB DEFAULT '{}',
                    confidence_score FLOAT NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT FALSE,
                    interventions_applied JSONB DEFAULT '[]',
                    resolution_notes TEXT,
                    follow_up_required BOOLEAN DEFAULT TRUE
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bullying_patterns (
                    id SERIAL PRIMARY KEY,
                    pattern_id VARCHAR(50) UNIQUE NOT NULL,
                    primary_aggressor VARCHAR(50) NOT NULL,
                    targets JSONB NOT NULL,
                    pattern_type VARCHAR(50) NOT NULL,
                    frequency INTEGER NOT NULL,
                    timespan_days INTEGER NOT NULL,
                    escalation_trend VARCHAR(20) NOT NULL,
                    risk_score FLOAT NOT NULL,
                    identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    intervention_plan JSONB DEFAULT '{}',
                    monitoring_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS intervention_history (
                    id SERIAL PRIMARY KEY,
                    incident_id VARCHAR(50) NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    intervention_type VARCHAR(50) NOT NULL,
                    intervention_details JSONB NOT NULL,
                    effectiveness_rating FLOAT,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    follow_up_scheduled BOOLEAN DEFAULT FALSE
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS safety_education_progress (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    content_id VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    engagement_score FLOAT,
                    comprehension_score FLOAT,
                    behavioral_change_indicators JSONB DEFAULT '[]',
                    UNIQUE(user_id, content_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS peer_support_network (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    supporter_id VARCHAR(50) NOT NULL,
                    support_type VARCHAR(50) NOT NULL,
                    relationship_strength FLOAT DEFAULT 0.5,
                    active_support BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, supporter_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS positive_behavior_tracking (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    behavior_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    impact_rating FLOAT,
                    recognized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    peer_nominations INTEGER DEFAULT 0
                )
            """)

        # Initialize educational content
        await self.setup_safety_education_content()

    async def setup_safety_education_content(self):
        """Set up anti-bullying education content"""
        educational_content = [
            SafetyEducationContent(
                content_id="kindness_matters_k2",
                title="Kindness Matters",
                description="Interactive story about being kind to classmates",
                age_group="5-7",
                content_type="interactive",
                key_concepts=["kindness", "empathy", "friendship", "inclusion"],
                expected_duration_minutes=10,
                effectiveness_metrics={"engagement": 0.9, "retention": 0.8}
            ),
            SafetyEducationContent(
                content_id="upstander_training_elementary",
                title="Be an Upstander, Not a Bystander",
                description="Learn how to help friends when someone is being mean",
                age_group="8-11",
                content_type="interactive",
                key_concepts=["bystander intervention", "courage", "helping others", "safety"],
                expected_duration_minutes=15,
                effectiveness_metrics={"engagement": 0.85, "retention": 0.82}
            ),
            SafetyEducationContent(
                content_id="digital_citizenship_middle",
                title="Digital Citizenship and Online Respect",
                description="Understanding respectful communication online",
                age_group="12-14",
                content_type="video",
                key_concepts=["digital citizenship", "cyberbullying", "online respect", "digital footprint"],
                expected_duration_minutes=20,
                effectiveness_metrics={"engagement": 0.88, "retention": 0.85}
            )
        ]
        
        # Store educational content metadata (actual content would be in content management system)
        async with self.db_pool.acquire() as conn:
            for content in educational_content:
                await conn.execute("""
                    INSERT INTO safety_education_content (
                        content_id, title, description, age_group, content_type,
                        key_concepts, expected_duration_minutes, effectiveness_metrics
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (content_id) DO UPDATE SET
                        effectiveness_metrics = EXCLUDED.effectiveness_metrics
                """,
                    content.content_id, content.title, content.description,
                    content.age_group, content.content_type,
                    json.dumps(content.key_concepts), content.expected_duration_minutes,
                    json.dumps(content.effectiveness_metrics)
                )

    async def analyze_interaction_for_bullying(self, content: str, participants: List[str],
                                             context: Dict[str, Any]) -> Optional[BullyingIncident]:
        """Analyze an interaction for potential bullying behavior"""
        content_lower = content.lower()
        
        # Check for positive interactions first (to avoid false positives)
        positive_score = sum(1 for indicator in self.positive_indicators 
                           if indicator in content_lower)
        
        if positive_score >= 2:
            # Likely positive interaction, low chance of bullying
            return None
        
        # Analyze for bullying indicators
        bullying_indicators = {}
        total_score = 0
        
        # Check direct aggression indicators
        for category, indicators in self.aggression_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in content_lower)
            if matches > 0:
                bullying_indicators[category] = matches
                total_score += matches * self._get_category_weight(category)
        
        # Check context patterns
        for pattern_type, patterns in self.context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    bullying_indicators[pattern_type] = bullying_indicators.get(pattern_type, 0) + 1
                    total_score += self._get_pattern_weight(pattern_type)
        
        # Check for power imbalance indicators
        if len(participants) > 2:  # Group targeting individual
            total_score += 0.3
            bullying_indicators["group_targeting"] = True
        
        # Determine if this constitutes bullying
        confidence_score = min(1.0, total_score / 5.0)  # Normalize to 0-1
        
        if confidence_score < 0.3:
            return None  # Not likely bullying
        
        # Determine bullying type and severity
        bullying_type = self._determine_bullying_type(bullying_indicators)
        severity = self._calculate_severity(bullying_indicators, confidence_score)
        
        # Create incident
        incident = BullyingIncident(
            incident_id=f"incident_{datetime.now().timestamp()}",
            participants=self._analyze_participant_roles(participants, content, context),
            bullying_type=bullying_type,
            severity=severity,
            evidence=self._create_anonymized_evidence(content, bullying_indicators),
            context=self._extract_safe_context(context),
            confidence_score=confidence_score,
            detected_at=datetime.now()
        )
        
        # Store incident
        await self._store_bullying_incident(incident)
        
        # Apply immediate interventions
        await self._apply_immediate_interventions(incident)
        
        return incident

    def _get_category_weight(self, category: str) -> float:
        """Get severity weight for different bullying categories"""
        weights = {
            "direct_insults": 0.6,
            "threats": 1.0,
            "exclusion_language": 0.7,
            "cyberbullying_patterns": 0.9,
            "discriminatory_language": 0.8
        }
        return weights.get(category, 0.5)

    def _get_pattern_weight(self, pattern_type: str) -> float:
        """Get weight for context patterns"""
        weights = {
            "power_imbalance": 0.8,
            "repeated_targeting": 0.7,
            "social_manipulation": 0.9
        }
        return weights.get(pattern_type, 0.5)

    def _determine_bullying_type(self, indicators: Dict[str, Any]) -> BullyingType:
        """Determine the primary type of bullying based on indicators"""
        if "cyberbullying_patterns" in indicators:
            return BullyingType.CYBERBULLYING
        elif "threats" in indicators:
            return BullyingType.INTIMIDATION
        elif "exclusion_language" in indicators or "social_manipulation" in indicators:
            return BullyingType.EXCLUSION
        elif "discriminatory_language" in indicators:
            return BullyingType.DISCRIMINATION
        elif "direct_insults" in indicators:
            return BullyingType.VERBAL_AGGRESSION
        else:
            return BullyingType.HARASSMENT

    def _calculate_severity(self, indicators: Dict[str, Any], confidence_score: float) -> SeverityLevel:
        """Calculate severity level based on indicators and confidence"""
        severity_score = 0
        
        # High-severity indicators
        if "cyberbullying_patterns" in indicators:
            severity_score += 0.9
        if "threats" in indicators:
            severity_score += 0.8
        if "discriminatory_language" in indicators:
            severity_score += 0.7
        
        # Context severity modifiers
        if "power_imbalance" in indicators:
            severity_score += 0.3
        if "repeated_targeting" in indicators:
            severity_score += 0.4
        if "group_targeting" in indicators:
            severity_score += 0.3
        
        # Adjust by confidence
        final_score = severity_score * confidence_score
        
        if final_score >= 1.5:
            return SeverityLevel.CRITICAL
        elif final_score >= 1.0:
            return SeverityLevel.HIGH
        elif final_score >= 0.6:
            return SeverityLevel.MODERATE
        else:
            return SeverityLevel.LOW

    def _analyze_participant_roles(self, participants: List[str], content: str, 
                                 context: Dict[str, Any]) -> Dict[str, ParticipantRole]:
        """Analyze roles of participants in the interaction"""
        roles = {}
        
        # Simple heuristic for role assignment
        # In practice, this would be more sophisticated
        if len(participants) == 2:
            # One-on-one interaction
            # Would need more context to determine aggressor vs target
            roles[participants[0]] = ParticipantRole.AGGRESSOR  # Tentative
            roles[participants[1]] = ParticipantRole.TARGET     # Tentative
        elif len(participants) > 2:
            # Group interaction - likely group targeting
            # First participant might be primary aggressor, last might be target
            roles[participants[0]] = ParticipantRole.AGGRESSOR
            roles[participants[-1]] = ParticipantRole.TARGET
            
            # Others are bystanders (could be upstanders if they intervene positively)
            for participant in participants[1:-1]:
                roles[participant] = ParticipantRole.BYSTANDER
        
        return roles

    def _create_anonymized_evidence(self, content: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Create anonymized evidence preserving only pattern information"""
        return {
            "content_length": len(content),
            "word_count": len(content.split()),
            "indicators_detected": list(indicators.keys()),
            "indicator_strength": {k: v for k, v in indicators.items() if isinstance(v, (int, float))},
            "content_hash": hashlib.sha256(content.encode()).hexdigest(),
            "analysis_timestamp": datetime.now().isoformat()
        }

    def _extract_safe_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract safe context information without personal details"""
        safe_context = {}
        
        allowed_fields = [
            "platform", "content_type", "public", "group_size", 
            "time_of_day", "day_of_week", "duration"
        ]
        
        for field in allowed_fields:
            if field in context:
                safe_context[field] = context[field]
        
        return safe_context

    async def _store_bullying_incident(self, incident: BullyingIncident):
        """Store bullying incident in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bullying_incidents (
                    incident_id, participants, bullying_type, severity,
                    evidence, context, confidence_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                incident.incident_id, json.dumps({k: v.value for k, v in incident.participants.items()}),
                incident.bullying_type.value, incident.severity.value,
                json.dumps(incident.evidence), json.dumps(incident.context),
                incident.confidence_score
            )

    async def _apply_immediate_interventions(self, incident: BullyingIncident):
        """Apply immediate interventions based on incident severity"""
        interventions = []
        
        if incident.severity == SeverityLevel.CRITICAL:
            interventions = [
                InterventionType.TEMPORARY_RESTRICTION,
                InterventionType.PARENT_NOTIFICATION,
                InterventionType.COUNSELING_REFERRAL
            ]
        elif incident.severity == SeverityLevel.HIGH:
            interventions = [
                InterventionType.COOLING_OFF,
                InterventionType.PARENT_NOTIFICATION,
                InterventionType.MEDIATION
            ]
        elif incident.severity == SeverityLevel.MODERATE:
            interventions = [
                InterventionType.WARNING,
                InterventionType.EDUCATION
            ]
        else:  # LOW
            interventions = [InterventionType.EDUCATION]
        
        # Apply each intervention
        for intervention in interventions:
            await self._apply_intervention(incident, intervention)
            incident.interventions_applied.append(intervention)

    async def _apply_intervention(self, incident: BullyingIncident, intervention: InterventionType):
        """Apply a specific intervention"""
        intervention_details = {}
        
        if intervention == InterventionType.WARNING:
            intervention_details = await self._generate_educational_warning(incident)
        
        elif intervention == InterventionType.EDUCATION:
            intervention_details = await self._assign_educational_content(incident)
        
        elif intervention == InterventionType.COOLING_OFF:
            intervention_details = await self._initiate_cooling_off_period(incident)
        
        elif intervention == InterventionType.MEDIATION:
            intervention_details = await self._setup_peer_mediation(incident)
        
        elif intervention == InterventionType.PARENT_NOTIFICATION:
            intervention_details = await self._notify_parents(incident)
        
        elif intervention == InterventionType.TEMPORARY_RESTRICTION:
            intervention_details = await self._apply_temporary_restrictions(incident)
        
        elif intervention == InterventionType.COUNSELING_REFERRAL:
            intervention_details = await self._create_counseling_referral(incident)
        
        # Log intervention
        for user_id in incident.participants.keys():
            await self._log_intervention(incident.incident_id, user_id, intervention, intervention_details)

    async def _generate_educational_warning(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Generate age-appropriate educational warning"""
        age_appropriate_messages = {
            BullyingType.VERBAL_AGGRESSION: {
                "young": "Words can hurt feelings. Let's try to use kind words instead.",
                "older": "Hurtful language can cause real harm. Consider how your words affect others."
            },
            BullyingType.EXCLUSION: {
                "young": "Everyone deserves to feel included. How can we make others feel welcome?",
                "older": "Excluding others can cause loneliness and hurt. Think about including everyone."
            },
            BullyingType.CYBERBULLYING: {
                "young": "Online words matter too. Let's be kind on the internet just like in person.",
                "older": "Cyberbullying can have serious consequences. Your digital words have real impact."
            }
        }
        
        message_set = age_appropriate_messages.get(incident.bullying_type, {
            "young": "Let's try to be kinder to each other.",
            "older": "Please consider how your actions affect others."
        })
        
        return {
            "warning_message": message_set.get("young"),  # Default to younger message for safety
            "educational_focus": self._get_educational_focus(incident.bullying_type),
            "reflection_questions": self._generate_reflection_questions(incident.bullying_type)
        }

    async def _assign_educational_content(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Assign appropriate educational content"""
        # Get educational content based on incident type and participant ages
        async with self.db_pool.acquire() as conn:
            educational_content = await conn.fetch("""
                SELECT * FROM safety_education_content
                WHERE key_concepts @> $1::jsonb
                ORDER BY effectiveness_metrics->>'engagement' DESC
                LIMIT 3
            """, json.dumps([incident.bullying_type.value]))
        
        assignments = []
        for participant_id, role in incident.participants.items():
            if role in [ParticipantRole.AGGRESSOR, ParticipantRole.BYSTANDER]:
                # Assign relevant content
                for content in educational_content:
                    assignments.append({
                        "user_id": participant_id,
                        "content_id": content["content_id"],
                        "priority": "high" if role == ParticipantRole.AGGRESSOR else "medium"
                    })
        
        return {
            "content_assignments": assignments,
            "completion_deadline": (datetime.now() + timedelta(hours=48)).isoformat(),
            "progress_monitoring": True
        }

    async def _initiate_cooling_off_period(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Initiate a cooling-off period for participants"""
        cooling_off_duration = timedelta(minutes=30) if incident.severity == SeverityLevel.MODERATE else timedelta(hours=2)
        
        return {
            "duration_minutes": int(cooling_off_duration.total_seconds() / 60),
            "restrictions": ["no_messaging", "limited_interactions"],
            "activities_suggested": [
                "Take deep breaths",
                "Think about the other person's feelings",
                "Consider a different approach"
            ],
            "expires_at": (datetime.now() + cooling_off_duration).isoformat()
        }

    async def _setup_peer_mediation(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Set up peer mediation session"""
        return {
            "mediation_type": "guided_conversation",
            "suggested_facilitator": "trained_peer_mediator",
            "talking_points": [
                "Understanding different perspectives",
                "Finding common ground",
                "Agreeing on respectful behavior"
            ],
            "follow_up_required": True,
            "scheduling_suggestion": "within 24 hours"
        }

    async def _notify_parents(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Notify parents about the bullying incident"""
        notifications = []
        
        for user_id, role in incident.participants.items():
            notification = {
                "user_id": user_id,
                "role": role.value,
                "severity": incident.severity.value,
                "incident_type": incident.bullying_type.value,
                "recommended_discussion_points": self._get_parent_discussion_points(role, incident.bullying_type),
                "resources": self._get_parent_resources(role)
            }
            notifications.append(notification)
        
        return {
            "notifications": notifications,
            "notification_method": "secure_message",
            "follow_up_meeting_suggested": incident.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        }

    def _get_parent_discussion_points(self, role: ParticipantRole, bullying_type: BullyingType) -> List[str]:
        """Get discussion points for parents based on child's role"""
        if role == ParticipantRole.AGGRESSOR:
            return [
                "Discuss the impact of hurtful behavior on others",
                "Explore better ways to handle conflicts",
                "Reinforce family values about treating others with respect",
                "Work together on empathy-building activities"
            ]
        elif role == ParticipantRole.TARGET:
            return [
                "Provide emotional support and validation",
                "Discuss strategies for handling bullying situations",
                "Reinforce that it's not their fault",
                "Consider involving school counselors if needed"
            ]
        else:  # BYSTANDER
            return [
                "Discuss the importance of standing up for others",
                "Practice safe ways to intervene or get help",
                "Explore the difference between tattling and reporting",
                "Encourage being an upstander"
            ]

    def _get_parent_resources(self, role: ParticipantRole) -> List[Dict[str, str]]:
        """Get resources for parents based on child's role"""
        common_resources = [
            {"title": "Understanding Bullying", "url": "/resources/understanding-bullying"},
            {"title": "Building Empathy at Home", "url": "/resources/building-empathy"}
        ]
        
        if role == ParticipantRole.AGGRESSOR:
            common_resources.extend([
                {"title": "Helping Children Make Amends", "url": "/resources/making-amends"},
                {"title": "Teaching Conflict Resolution", "url": "/resources/conflict-resolution"}
            ])
        elif role == ParticipantRole.TARGET:
            common_resources.extend([
                {"title": "Supporting a Bullied Child", "url": "/resources/supporting-bullied-child"},
                {"title": "Building Confidence and Resilience", "url": "/resources/building-resilience"}
            ])
        
        return common_resources

    async def _apply_temporary_restrictions(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Apply temporary restrictions for severe incidents"""
        restriction_duration = timedelta(hours=24) if incident.severity == SeverityLevel.HIGH else timedelta(hours=48)
        
        restrictions = {
            "messaging_disabled": True,
            "public_posting_disabled": True,
            "friend_requests_disabled": True,
            "group_participation_limited": True
        }
        
        return {
            "restrictions": restrictions,
            "duration_hours": int(restriction_duration.total_seconds() / 3600),
            "review_date": (datetime.now() + restriction_duration).isoformat(),
            "appeal_process_available": True,
            "educational_requirements": "Must complete anti-bullying education module"
        }

    async def _create_counseling_referral(self, incident: BullyingIncident) -> Dict[str, Any]:
        """Create counseling referral for critical incidents"""
        return {
            "referral_type": "school_counselor",
            "urgency": "high",
            "recommended_sessions": 3,
            "focus_areas": [
                "Social skills development",
                "Empathy building",
                "Conflict resolution",
                "Emotional regulation"
            ],
            "parent_involvement_required": True,
            "follow_up_timeline": "weekly"
        }

    async def _log_intervention(self, incident_id: str, user_id: str, 
                              intervention: InterventionType, details: Dict[str, Any]):
        """Log intervention details"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO intervention_history (
                    incident_id, user_id, intervention_type, intervention_details
                ) VALUES ($1, $2, $3, $4)
            """, incident_id, user_id, intervention.value, json.dumps(details))

    def _get_educational_focus(self, bullying_type: BullyingType) -> List[str]:
        """Get educational focus areas for specific bullying types"""
        focus_areas = {
            BullyingType.VERBAL_AGGRESSION: ["kindness", "respectful_communication", "empathy"],
            BullyingType.EXCLUSION: ["inclusion", "friendship", "acceptance"],
            BullyingType.CYBERBULLYING: ["digital_citizenship", "online_respect", "cyber_safety"],
            BullyingType.INTIMIDATION: ["peaceful_conflict_resolution", "personal_space", "safety"],
            BullyingType.HARASSMENT: ["boundaries", "consent", "respectful_behavior"],
            BullyingType.DISCRIMINATION: ["diversity", "equality", "acceptance"],
            BullyingType.RELATIONAL_AGGRESSION: ["healthy_relationships", "communication", "trust"]
        }
        
        return focus_areas.get(bullying_type, ["kindness", "empathy", "respect"])

    def _generate_reflection_questions(self, bullying_type: BullyingType) -> List[str]:
        """Generate age-appropriate reflection questions"""
        base_questions = [
            "How do you think the other person felt?",
            "What could you do differently next time?",
            "How would you want to be treated in this situation?"
        ]
        
        type_specific_questions = {
            BullyingType.VERBAL_AGGRESSION: [
                "What are some kind words you could use instead?",
                "How do words affect people's feelings?"
            ],
            BullyingType.EXCLUSION: [
                "How does it feel to be left out?",
                "What are ways to include everyone?"
            ],
            BullyingType.CYBERBULLYING: [
                "How is online communication different from face-to-face?",
                "What would happen if your family saw what you wrote?"
            ]
        }
        
        questions = base_questions.copy()
        questions.extend(type_specific_questions.get(bullying_type, []))
        
        return questions

    async def detect_bullying_patterns(self, user_id: str, timeframe_days: int = 30) -> List[BullyingPattern]:
        """Detect recurring bullying patterns for a user"""
        async with self.db_pool.acquire() as conn:
            # Get recent incidents involving this user
            incidents = await conn.fetch("""
                SELECT * FROM bullying_incidents
                WHERE (participants ? $1) 
                AND detected_at >= $2
                ORDER BY detected_at DESC
            """, user_id, datetime.now() - timedelta(days=timeframe_days))
        
        if len(incidents) < 3:  # Need at least 3 incidents for pattern
            return []
        
        patterns = []
        
        # Analyze if user is consistently an aggressor
        aggressor_incidents = []
        target_incidents = []
        
        for incident in incidents:
            participants = json.loads(incident["participants"])
            if participants.get(user_id) == ParticipantRole.AGGRESSOR.value:
                aggressor_incidents.append(incident)
            elif participants.get(user_id) == ParticipantRole.TARGET.value:
                target_incidents.append(incident)
        
        # Check for aggressor patterns
        if len(aggressor_incidents) >= 3:
            # Extract targets
            targets = set()
            for incident in aggressor_incidents:
                participants = json.loads(incident["participants"])
                for pid, role in participants.items():
                    if role == ParticipantRole.TARGET.value:
                        targets.add(pid)
            
            pattern = BullyingPattern(
                pattern_id=f"pattern_aggressor_{user_id}_{datetime.now().timestamp()}",
                primary_aggressor=user_id,
                targets=list(targets),
                pattern_type="persistent_aggression",
                frequency=len(aggressor_incidents),
                timespan_days=timeframe_days,
                escalation_trend=self._analyze_escalation_trend(aggressor_incidents),
                risk_score=self._calculate_pattern_risk_score(aggressor_incidents)
            )
            patterns.append(pattern)
        
        # Check for targeting patterns (being repeatedly targeted)
        if len(target_incidents) >= 3:
            # Extract aggressors
            aggressors = set()
            for incident in target_incidents:
                participants = json.loads(incident["participants"])
                for pid, role in participants.items():
                    if role == ParticipantRole.AGGRESSOR.value:
                        aggressors.add(pid)
            
            pattern = BullyingPattern(
                pattern_id=f"pattern_target_{user_id}_{datetime.now().timestamp()}",
                primary_aggressor="multiple" if len(aggressors) > 1 else list(aggressors)[0],
                targets=[user_id],
                pattern_type="repeated_targeting",
                frequency=len(target_incidents),
                timespan_days=timeframe_days,
                escalation_trend=self._analyze_escalation_trend(target_incidents),
                risk_score=self._calculate_pattern_risk_score(target_incidents)
            )
            patterns.append(pattern)
        
        # Store patterns
        for pattern in patterns:
            await self._store_bullying_pattern(pattern)
        
        return patterns

    def _analyze_escalation_trend(self, incidents: List[Dict]) -> str:
        """Analyze if bullying is escalating, stable, or decreasing"""
        if len(incidents) < 2:
            return "stable"
        
        # Sort by date
        sorted_incidents = sorted(incidents, key=lambda x: x["detected_at"])
        
        # Compare severity over time
        severities = [SeverityLevel(inc["severity"]) for inc in sorted_incidents]
        severity_scores = [self._severity_to_score(sev) for sev in severities]
        
        if len(severity_scores) < 2:
            return "stable"
        
        # Simple trend analysis
        recent_avg = sum(severity_scores[-3:]) / len(severity_scores[-3:])
        earlier_avg = sum(severity_scores[:-3]) / max(1, len(severity_scores[:-3]))
        
        if recent_avg > earlier_avg + 0.3:
            return "increasing"
        elif recent_avg < earlier_avg - 0.3:
            return "decreasing"
        else:
            return "stable"

    def _severity_to_score(self, severity: SeverityLevel) -> float:
        """Convert severity level to numeric score"""
        scores = {
            SeverityLevel.LOW: 1.0,
            SeverityLevel.MODERATE: 2.0,
            SeverityLevel.HIGH: 3.0,
            SeverityLevel.CRITICAL: 4.0
        }
        return scores.get(severity, 1.0)

    def _calculate_pattern_risk_score(self, incidents: List[Dict]) -> float:
        """Calculate risk score for a bullying pattern"""
        if not incidents:
            return 0.0
        
        # Factors: frequency, severity, recency, escalation
        frequency_score = min(1.0, len(incidents) / 10)  # Normalize to 10 incidents max
        
        severity_scores = [self._severity_to_score(SeverityLevel(inc["severity"])) for inc in incidents]
        avg_severity = sum(severity_scores) / len(severity_scores) / 4.0  # Normalize to 0-1
        
        # Recency factor (more recent = higher risk)
        most_recent = max(incidents, key=lambda x: x["detected_at"])["detected_at"]
        days_since = (datetime.now() - most_recent).days
        recency_score = max(0.0, 1.0 - (days_since / 30))  # Full score if within last month
        
        # Overall risk score
        risk_score = (frequency_score * 0.3 + avg_severity * 0.4 + recency_score * 0.3)
        
        return round(risk_score, 2)

    async def _store_bullying_pattern(self, pattern: BullyingPattern):
        """Store bullying pattern in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO bullying_patterns (
                    pattern_id, primary_aggressor, targets, pattern_type,
                    frequency, timespan_days, escalation_trend, risk_score
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
                pattern.pattern_id, pattern.primary_aggressor,
                json.dumps(pattern.targets), pattern.pattern_type,
                pattern.frequency, pattern.timespan_days,
                pattern.escalation_trend, pattern.risk_score
            )

    async def track_positive_behavior(self, user_id: str, behavior_type: str, 
                                    description: str, impact_rating: float):
        """Track positive behaviors to balance the focus on problems"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO positive_behavior_tracking (
                    user_id, behavior_type, description, impact_rating
                ) VALUES ($1, $2, $3, $4)
            """, user_id, behavior_type, description, impact_rating)

    async def build_peer_support_network(self, user_id: str, supporter_id: str, 
                                       support_type: str) -> Dict:
        """Build supportive peer relationships"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO peer_support_network (
                    user_id, supporter_id, support_type
                ) VALUES ($1, $2, $3)
                ON CONFLICT (user_id, supporter_id) DO UPDATE SET
                    support_type = EXCLUDED.support_type,
                    relationship_strength = peer_support_network.relationship_strength + 0.1
            """, user_id, supporter_id, support_type)
        
        return {
            "support_relationship_created": True,
            "supporter_id": supporter_id,
            "support_type": support_type,
            "relationship_building_activities": [
                "Collaborative projects",
                "Peer mentoring opportunities",
                "Group activities with shared interests"
            ]
        }

    async def get_bullying_prevention_report(self, user_id: str, days: int = 30) -> Dict:
        """Generate comprehensive bullying prevention report"""
        async with self.db_pool.acquire() as conn:
            # Get incident statistics
            incident_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_incidents,
                    COUNT(*) FILTER (WHERE severity = 'critical') as critical_incidents,
                    COUNT(*) FILTER (WHERE resolved = TRUE) as resolved_incidents,
                    AVG(confidence_score) as avg_confidence
                FROM bullying_incidents
                WHERE (participants ? $1) AND detected_at >= $2
            """, user_id, datetime.now() - timedelta(days=days))
            
            # Get intervention effectiveness
            intervention_stats = await conn.fetch("""
                SELECT 
                    intervention_type,
                    COUNT(*) as count,
                    AVG(effectiveness_rating) as avg_effectiveness
                FROM intervention_history
                WHERE user_id = $1 AND applied_at >= $2
                GROUP BY intervention_type
            """, user_id, datetime.now() - timedelta(days=days))
            
            # Get positive behavior tracking
            positive_behaviors = await conn.fetchval("""
                SELECT COUNT(*) FROM positive_behavior_tracking
                WHERE user_id = $1 AND recognized_at >= $2
            """, user_id, datetime.now() - timedelta(days=days))
            
            # Get support network strength
            support_network = await conn.fetchval("""
                SELECT COUNT(*) FROM peer_support_network
                WHERE user_id = $1 AND active_support = TRUE
            """, user_id)
        
        return {
            "reporting_period_days": days,
            "incident_summary": {
                "total_incidents": incident_stats["total_incidents"] or 0,
                "critical_incidents": incident_stats["critical_incidents"] or 0,
                "resolution_rate": (incident_stats["resolved_incidents"] / max(1, incident_stats["total_incidents"])) * 100,
                "detection_confidence": round(incident_stats["avg_confidence"] or 0, 2)
            },
            "intervention_effectiveness": [
                {
                    "type": stat["intervention_type"],
                    "frequency": stat["count"],
                    "effectiveness": round(stat["avg_effectiveness"] or 0, 2)
                } for stat in intervention_stats
            ],
            "positive_indicators": {
                "positive_behaviors_recognized": positive_behaviors or 0,
                "peer_support_connections": support_network or 0,
                "overall_wellbeing_trend": self._assess_wellbeing_trend(user_id)
            },
            "recommendations": await self._generate_prevention_recommendations(user_id),
            "safety_resources": self._get_safety_resources_for_user(user_id)
        }

    def _assess_wellbeing_trend(self, user_id: str) -> str:
        """Assess overall wellbeing trend (placeholder)"""
        # This would integrate with other wellbeing metrics
        return "stable"  # "improving", "stable", "concerning"

    async def _generate_prevention_recommendations(self, user_id: str) -> List[str]:
        """Generate personalized prevention recommendations"""
        # This would be based on the user's specific incident history and patterns
        return [
            "Continue building positive peer relationships",
            "Practice conflict resolution skills",
            "Engage in collaborative group activities",
            "Strengthen communication skills"
        ]

    def _get_safety_resources_for_user(self, user_id: str) -> List[Dict[str, str]]:
        """Get safety resources appropriate for the user"""
        return [
            {"title": "How to Handle Bullying", "type": "guide", "age_group": "all"},
            {"title": "Building Friendship Skills", "type": "interactive", "age_group": "all"},
            {"title": "Digital Citizenship", "type": "course", "age_group": "10+"},
            {"title": "When to Tell a Trusted Adult", "type": "guide", "age_group": "all"}
        ]