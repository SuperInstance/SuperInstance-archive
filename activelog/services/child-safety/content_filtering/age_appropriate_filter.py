import asyncio
import asyncpg
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re
import hashlib
from datetime import datetime, timedelta
import logging


class AgeRating(Enum):
    EARLY_CHILDHOOD = "early_childhood"  # 3-5 years
    PRESCHOOL = "preschool"             # 4-6 years  
    ELEMENTARY = "elementary"           # 6-11 years
    MIDDLE_SCHOOL = "middle_school"     # 11-14 years
    HIGH_SCHOOL = "high_school"         # 14-18 years
    ADULT = "adult"                     # 18+ years


class ContentType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    INTERACTIVE = "interactive"
    LINK = "link"
    USER_GENERATED = "user_generated"


class FilterAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    FLAG = "flag"
    MODERATE = "moderate"
    PARENT_REVIEW = "parent_review"


class SafetyLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    WARNING = "warning"
    BLOCKED = "blocked"


@dataclass
class ContentAnalysis:
    content_id: str
    content_type: ContentType
    age_rating: AgeRating
    safety_level: SafetyLevel
    action: FilterAction
    confidence_score: float
    flags: List[str]
    educational_value: int  # 1-10 scale
    analysis_details: Dict[str, Any]
    timestamp: datetime


@dataclass
class FilterRule:
    rule_id: str
    name: str
    description: str
    age_min: int
    age_max: int
    content_types: List[ContentType]
    blocked_keywords: List[str]
    flagged_keywords: List[str]
    regex_patterns: List[str]
    whitelist_domains: Set[str]
    blacklist_domains: Set[str]
    educational_keywords: List[str]
    severity_weights: Dict[str, float]
    is_active: bool = True


class AgeAppropriateFilter:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.filter_rules: Dict[AgeRating, List[FilterRule]] = {}
        self.content_cache: Dict[str, ContentAnalysis] = {}
        self.logger = logging.getLogger(__name__)
        
        # Age-specific keyword categories
        self.age_inappropriate_keywords = {
            AgeRating.EARLY_CHILDHOOD: {
                "violence": ["hurt", "fight", "scary", "monster", "weapon", "blood", "pain"],
                "mature_themes": ["adult", "grown-up only", "mature", "explicit"],
                "inappropriate_language": ["stupid", "dumb", "hate", "shut up"],
                "dangerous_activities": ["fire", "knife", "dangerous", "don't try this"]
            },
            AgeRating.PRESCHOOL: {
                "violence": ["kill", "death", "murder", "fight", "weapon", "gun", "knife", "blood"],
                "mature_themes": ["adult content", "mature audiences", "explicit", "inappropriate"],
                "inappropriate_language": ["stupid", "dumb", "hate", "idiot", "loser"],
                "scary_content": ["horror", "nightmare", "frightening", "terrifying", "ghost"]
            },
            AgeRating.ELEMENTARY: {
                "violence": ["murder", "killing", "death", "suicide", "violence", "brutal"],
                "mature_themes": ["sexual", "adult only", "mature content", "explicit"],
                "inappropriate_language": ["profanity", "curse", "swear", "offensive language"],
                "dangerous_activities": ["illegal", "drugs", "smoking", "drinking alcohol"]
            },
            AgeRating.MIDDLE_SCHOOL: {
                "extreme_violence": ["graphic violence", "torture", "gore", "brutal murder"],
                "adult_content": ["sexual content", "nudity", "adult themes", "mature audiences only"],
                "substance_abuse": ["drug use", "alcohol abuse", "smoking addiction"],
                "hate_speech": ["discrimination", "bullying", "harassment", "hate speech"]
            }
        }
        
        # Educational content indicators
        self.educational_indicators = {
            "learning": ["learn", "education", "teach", "study", "knowledge", "skill"],
            "creativity": ["create", "build", "make", "design", "art", "craft", "imagination"],
            "science": ["science", "experiment", "discover", "explore", "nature", "animals"],
            "math": ["math", "number", "count", "calculate", "problem solving", "logic"],
            "reading": ["read", "story", "book", "literature", "writing", "language"],
            "social_skills": ["friendship", "kindness", "sharing", "cooperation", "empathy"],
            "problem_solving": ["puzzle", "challenge", "solution", "think", "reason"]
        }

    async def initialize_tables(self):
        """Initialize database tables for content filtering"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS content_analysis_results (
                    id SERIAL PRIMARY KEY,
                    content_id VARCHAR(100) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    content_type VARCHAR(50) NOT NULL,
                    age_rating VARCHAR(50) NOT NULL,
                    safety_level VARCHAR(50) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    flags JSONB DEFAULT '[]',
                    educational_value INTEGER DEFAULT 0,
                    analysis_details JSONB DEFAULT '{}',
                    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    UNIQUE(content_hash)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS filter_rules (
                    id SERIAL PRIMARY KEY,
                    rule_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    age_min INTEGER NOT NULL,
                    age_max INTEGER NOT NULL,
                    content_types JSONB NOT NULL,
                    blocked_keywords JSONB DEFAULT '[]',
                    flagged_keywords JSONB DEFAULT '[]',
                    regex_patterns JSONB DEFAULT '[]',
                    whitelist_domains JSONB DEFAULT '[]',
                    blacklist_domains JSONB DEFAULT '[]',
                    educational_keywords JSONB DEFAULT '[]',
                    severity_weights JSONB DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked_content_log (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    content_type VARCHAR(50) NOT NULL,
                    block_reason TEXT NOT NULL,
                    user_age INTEGER,
                    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parent_notified BOOLEAN DEFAULT FALSE
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parent_override_requests (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    content_preview TEXT,
                    block_reason TEXT NOT NULL,
                    parent_decision VARCHAR(20),
                    parent_reasoning TEXT,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)

        # Initialize default filter rules
        await self.create_default_filter_rules()

    async def create_default_filter_rules(self):
        """Create default age-appropriate filter rules"""
        default_rules = [
            FilterRule(
                rule_id="early_childhood_basic",
                name="Early Childhood Safety",
                description="Basic safety filters for ages 3-5",
                age_min=3,
                age_max=5,
                content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO],
                blocked_keywords=self.age_inappropriate_keywords[AgeRating.EARLY_CHILDHOOD]["violence"] + 
                               self.age_inappropriate_keywords[AgeRating.EARLY_CHILDHOOD]["mature_themes"],
                flagged_keywords=self.age_inappropriate_keywords[AgeRating.EARLY_CHILDHOOD]["inappropriate_language"],
                regex_patterns=[
                    r'\b(scary|frightening|terrifying)\b',
                    r'\b(adult\s+only|mature\s+content)\b'
                ],
                whitelist_domains={"pbskids.org", "sesamestreet.org", "disney.com"},
                blacklist_domains={"youtube.com", "facebook.com", "twitter.com"},
                educational_keywords=self.educational_indicators["learning"][:5],
                severity_weights={"violence": 1.0, "mature_themes": 1.0, "scary": 0.8}
            ),
            
            FilterRule(
                rule_id="elementary_comprehensive",
                name="Elementary School Filter",
                description="Comprehensive filtering for elementary age children",
                age_min=6,
                age_max=11,
                content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO, ContentType.LINK],
                blocked_keywords=self.age_inappropriate_keywords[AgeRating.ELEMENTARY]["violence"] + 
                               self.age_inappropriate_keywords[AgeRating.ELEMENTARY]["mature_themes"] +
                               self.age_inappropriate_keywords[AgeRating.ELEMENTARY]["dangerous_activities"],
                flagged_keywords=self.age_inappropriate_keywords[AgeRating.ELEMENTARY]["inappropriate_language"],
                regex_patterns=[
                    r'\b(kill|murder|death)\b',
                    r'\b(drug|alcohol|smoking)\b',
                    r'\b(sexual|explicit|adult)\b'
                ],
                whitelist_domains={"khan-academy.org", "scratch.mit.edu", "code.org", "nationalgeographic.com"},
                blacklist_domains={"reddit.com", "4chan.org", "adult-sites"},
                educational_keywords=sum(self.educational_indicators.values(), [])[:20],
                severity_weights={"violence": 1.0, "mature_themes": 1.0, "dangerous": 0.9, "language": 0.6}
            ),
            
            FilterRule(
                rule_id="middle_school_balanced",
                name="Middle School Balanced Filter",
                description="Balanced filtering allowing more mature educational content",
                age_min=11,
                age_max=14,
                content_types=[ContentType.TEXT, ContentType.IMAGE, ContentType.VIDEO, ContentType.LINK, ContentType.USER_GENERATED],
                blocked_keywords=self.age_inappropriate_keywords[AgeRating.MIDDLE_SCHOOL]["extreme_violence"] + 
                               self.age_inappropriate_keywords[AgeRating.MIDDLE_SCHOOL]["adult_content"],
                flagged_keywords=self.age_inappropriate_keywords[AgeRating.MIDDLE_SCHOOL]["substance_abuse"] +
                                self.age_inappropriate_keywords[AgeRating.MIDDLE_SCHOOL]["hate_speech"],
                regex_patterns=[
                    r'\b(graphic\s+violence|torture|gore)\b',
                    r'\b(sexual\s+content|nudity)\b',
                    r'\b(hate\s+speech|discrimination)\b'
                ],
                whitelist_domains={"wikipedia.org", "britannica.com", "coursera.org"},
                blacklist_domains={"explicit-sites", "gambling-sites"},
                educational_keywords=sum(self.educational_indicators.values(), []),
                severity_weights={"extreme_violence": 1.0, "adult_content": 1.0, "hate_speech": 0.9, "substance": 0.7}
            )
        ]
        
        for rule in default_rules:
            await self.save_filter_rule(rule)

    async def save_filter_rule(self, rule: FilterRule):
        """Save a filter rule to the database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO filter_rules (
                    rule_id, name, description, age_min, age_max, content_types,
                    blocked_keywords, flagged_keywords, regex_patterns,
                    whitelist_domains, blacklist_domains, educational_keywords,
                    severity_weights, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (rule_id) DO UPDATE SET
                    blocked_keywords = EXCLUDED.blocked_keywords,
                    flagged_keywords = EXCLUDED.flagged_keywords,
                    regex_patterns = EXCLUDED.regex_patterns,
                    severity_weights = EXCLUDED.severity_weights
            """,
                rule.rule_id, rule.name, rule.description, rule.age_min, rule.age_max,
                json.dumps([ct.value for ct in rule.content_types]),
                json.dumps(rule.blocked_keywords), json.dumps(rule.flagged_keywords),
                json.dumps(rule.regex_patterns), json.dumps(list(rule.whitelist_domains)),
                json.dumps(list(rule.blacklist_domains)), json.dumps(rule.educational_keywords),
                json.dumps(rule.severity_weights), rule.is_active
            )

    async def analyze_content(self, content: str, content_type: ContentType, 
                            user_age: int, context: Dict = None) -> ContentAnalysis:
        """Analyze content for age appropriateness and safety"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check cache first
        cached_result = await self.get_cached_analysis(content_hash)
        if cached_result:
            return cached_result
        
        # Get appropriate filter rules for user age
        applicable_rules = await self.get_rules_for_age(user_age, content_type)
        
        # Perform analysis
        analysis = ContentAnalysis(
            content_id=f"content_{content_hash[:8]}",
            content_type=content_type,
            age_rating=self._determine_age_rating(user_age),
            safety_level=SafetyLevel.SAFE,
            action=FilterAction.ALLOW,
            confidence_score=0.0,
            flags=[],
            educational_value=0,
            analysis_details={},
            timestamp=datetime.now()
        )
        
        # Apply each rule
        total_violation_score = 0.0
        detailed_flags = []
        
        for rule in applicable_rules:
            rule_result = self._apply_filter_rule(content, rule, context)
            total_violation_score += rule_result["violation_score"]
            detailed_flags.extend(rule_result["flags"])
            
            # Accumulate analysis details
            analysis.analysis_details[f"rule_{rule.rule_id}"] = rule_result
        
        # Calculate educational value
        analysis.educational_value = self._calculate_educational_value(content, applicable_rules)
        
        # Determine final safety assessment
        analysis.confidence_score = min(1.0, total_violation_score)
        analysis.flags = detailed_flags
        
        if total_violation_score >= 0.8:
            analysis.safety_level = SafetyLevel.BLOCKED
            analysis.action = FilterAction.BLOCK
        elif total_violation_score >= 0.6:
            analysis.safety_level = SafetyLevel.WARNING
            analysis.action = FilterAction.FLAG
        elif total_violation_score >= 0.3:
            analysis.safety_level = SafetyLevel.CAUTION
            analysis.action = FilterAction.MODERATE
        else:
            analysis.safety_level = SafetyLevel.SAFE
            analysis.action = FilterAction.ALLOW
        
        # Special handling for very young children
        if user_age < 6 and total_violation_score > 0.2:
            analysis.action = FilterAction.PARENT_REVIEW
        
        # Cache the result
        await self.cache_analysis(content_hash, analysis)
        
        # Log if content is blocked
        if analysis.action == FilterAction.BLOCK:
            await self.log_blocked_content(user_age, content_hash, content_type, detailed_flags)
        
        return analysis

    def _apply_filter_rule(self, content: str, rule: FilterRule, context: Dict = None) -> Dict:
        """Apply a specific filter rule to content"""
        content_lower = content.lower()
        violation_score = 0.0
        flags = []
        
        # Check blocked keywords
        for keyword in rule.blocked_keywords:
            if keyword.lower() in content_lower:
                weight = rule.severity_weights.get(keyword, 1.0)
                violation_score += 0.3 * weight
                flags.append(f"Blocked keyword: {keyword}")
        
        # Check flagged keywords (less severe)
        for keyword in rule.flagged_keywords:
            if keyword.lower() in content_lower:
                weight = rule.severity_weights.get(keyword, 0.5)
                violation_score += 0.15 * weight
                flags.append(f"Flagged keyword: {keyword}")
        
        # Check regex patterns
        for pattern in rule.regex_patterns:
            try:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violation_score += 0.4 * len(matches)
                    flags.append(f"Pattern match: {pattern}")
            except re.error:
                self.logger.warning(f"Invalid regex pattern: {pattern}")
        
        # Check URL domains if content contains links
        if context and context.get("urls"):
            for url in context["urls"]:
                domain = self._extract_domain(url)
                if domain in rule.blacklist_domains:
                    violation_score += 0.6
                    flags.append(f"Blacklisted domain: {domain}")
                elif domain in rule.whitelist_domains:
                    violation_score -= 0.2  # Reduce violation score for whitelisted domains
                    flags.append(f"Whitelisted domain: {domain}")
        
        return {
            "violation_score": min(1.0, violation_score),
            "flags": flags,
            "rule_name": rule.name
        }

    def _calculate_educational_value(self, content: str, rules: List[FilterRule]) -> int:
        """Calculate educational value of content (1-10 scale)"""
        content_lower = content.lower()
        educational_score = 0
        
        # Check for educational indicators
        for category, keywords in self.educational_indicators.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            educational_score += matches
        
        # Bonus for educational domains (if available in context)
        # Bonus for structured learning content
        if any(word in content_lower for word in ["lesson", "tutorial", "guide", "explanation"]):
            educational_score += 2
        
        # Bonus for age-appropriate complexity
        word_count = len(content.split())
        if 50 <= word_count <= 500:  # Appropriate length
            educational_score += 1
        
        return min(10, educational_score)

    def _determine_age_rating(self, user_age: int) -> AgeRating:
        """Determine age rating category for user"""
        if user_age <= 5:
            return AgeRating.EARLY_CHILDHOOD
        elif user_age <= 6:
            return AgeRating.PRESCHOOL
        elif user_age <= 11:
            return AgeRating.ELEMENTARY
        elif user_age <= 14:
            return AgeRating.MIDDLE_SCHOOL
        elif user_age <= 18:
            return AgeRating.HIGH_SCHOOL
        else:
            return AgeRating.ADULT

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.lower()
        except:
            return ""

    async def get_rules_for_age(self, user_age: int, content_type: ContentType) -> List[FilterRule]:
        """Get applicable filter rules for user age and content type"""
        async with self.db_pool.acquire() as conn:
            rules_data = await conn.fetch("""
                SELECT * FROM filter_rules
                WHERE is_active = TRUE 
                AND age_min <= $1 AND age_max >= $1
                AND content_types @> $2::jsonb
            """, user_age, json.dumps([content_type.value]))
        
        rules = []
        for rule_data in rules_data:
            rule = FilterRule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                description=rule_data["description"],
                age_min=rule_data["age_min"],
                age_max=rule_data["age_max"],
                content_types=[ContentType(ct) for ct in json.loads(rule_data["content_types"])],
                blocked_keywords=json.loads(rule_data["blocked_keywords"]),
                flagged_keywords=json.loads(rule_data["flagged_keywords"]),
                regex_patterns=json.loads(rule_data["regex_patterns"]),
                whitelist_domains=set(json.loads(rule_data["whitelist_domains"])),
                blacklist_domains=set(json.loads(rule_data["blacklist_domains"])),
                educational_keywords=json.loads(rule_data["educational_keywords"]),
                severity_weights=json.loads(rule_data["severity_weights"]),
                is_active=rule_data["is_active"]
            )
            rules.append(rule)
        
        return rules

    async def get_cached_analysis(self, content_hash: str) -> Optional[ContentAnalysis]:
        """Get cached content analysis if available and not expired"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM content_analysis_results
                WHERE content_hash = $1 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, content_hash)
            
            if not result:
                return None
            
            return ContentAnalysis(
                content_id=result["content_id"],
                content_type=ContentType(result["content_type"]),
                age_rating=AgeRating(result["age_rating"]),
                safety_level=SafetyLevel(result["safety_level"]),
                action=FilterAction(result["action"]),
                confidence_score=result["confidence_score"],
                flags=json.loads(result["flags"]),
                educational_value=result["educational_value"],
                analysis_details=json.loads(result["analysis_details"]),
                timestamp=result["analyzed_at"]
            )

    async def cache_analysis(self, content_hash: str, analysis: ContentAnalysis):
        """Cache content analysis result"""
        expires_at = datetime.now() + timedelta(hours=24)  # Cache for 24 hours
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO content_analysis_results (
                    content_id, content_hash, content_type, age_rating, safety_level,
                    action, confidence_score, flags, educational_value,
                    analysis_details, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (content_hash) DO UPDATE SET
                    analyzed_at = CURRENT_TIMESTAMP,
                    expires_at = EXCLUDED.expires_at
            """,
                analysis.content_id, content_hash, analysis.content_type.value,
                analysis.age_rating.value, analysis.safety_level.value,
                analysis.action.value, analysis.confidence_score,
                json.dumps(analysis.flags), analysis.educational_value,
                json.dumps(analysis.analysis_details), expires_at
            )

    async def log_blocked_content(self, user_age: int, content_hash: str, 
                                 content_type: ContentType, flags: List[str]):
        """Log blocked content for monitoring and parent notification"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO blocked_content_log (
                    user_id, content_hash, content_type, block_reason, user_age
                ) VALUES ($1, $2, $3, $4, $5)
            """, "system", content_hash, content_type.value, 
                "; ".join(flags), user_age)

    async def request_parent_override(self, user_id: str, content_hash: str, 
                                    content_preview: str, block_reason: str) -> Dict:
        """Request parent review for blocked content"""
        async with self.db_pool.acquire() as conn:
            # Check if request already exists
            existing = await conn.fetchrow("""
                SELECT id FROM parent_override_requests
                WHERE user_id = $1 AND content_hash = $2 
                AND parent_decision IS NULL
            """, user_id, content_hash)
            
            if existing:
                return {
                    "success": False,
                    "message": "Parent review already requested for this content"
                }
            
            # Create new request
            expires_at = datetime.now() + timedelta(hours=48)  # 48 hour expiry
            
            await conn.execute("""
                INSERT INTO parent_override_requests (
                    user_id, content_hash, content_preview, block_reason, expires_at
                ) VALUES ($1, $2, $3, $4, $5)
            """, user_id, content_hash, content_preview[:500], block_reason, expires_at)
        
        # Send notification to parent (would integrate with notification system)
        await self._notify_parent_review_needed(user_id, content_preview, block_reason)
        
        return {
            "success": True,
            "message": "Parent review requested. You'll be notified of their decision.",
            "estimated_response_time": "Usually within 2-4 hours"
        }

    async def _notify_parent_review_needed(self, user_id: str, content_preview: str, reason: str):
        """Send notification to parent about content review request"""
        # This would integrate with the notification system
        notification_data = {
            "type": "content_review_request",
            "user_id": user_id,
            "content_preview": content_preview,
            "block_reason": reason,
            "urgency": "medium"
        }
        # TODO: Send via email, SMS, or app notification

    async def get_content_safety_report(self, user_id: str, days: int = 7) -> Dict:
        """Generate content safety report for parents"""
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            # Get blocked content statistics
            blocked_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_blocked,
                    COUNT(DISTINCT content_type) as types_blocked,
                    AVG(CASE WHEN user_age IS NOT NULL THEN user_age ELSE 10 END) as avg_user_age
                FROM blocked_content_log
                WHERE user_id = $1 AND attempted_at >= $2
            """, user_id, start_date)
            
            # Get most common block reasons
            common_reasons = await conn.fetch("""
                SELECT block_reason, COUNT(*) as frequency
                FROM blocked_content_log
                WHERE user_id = $1 AND attempted_at >= $2
                GROUP BY block_reason
                ORDER BY frequency DESC
                LIMIT 5
            """, user_id, start_date)
            
            # Get parent review requests
            review_requests = await conn.fetch("""
                SELECT parent_decision, COUNT(*) as count
                FROM parent_override_requests
                WHERE user_id = $1 AND requested_at >= $2
                GROUP BY parent_decision
            """, user_id, start_date)
        
        return {
            "period_days": days,
            "total_content_blocked": blocked_stats["total_blocked"] or 0,
            "content_types_blocked": blocked_stats["types_blocked"] or 0,
            "safety_effectiveness": self._calculate_safety_effectiveness(blocked_stats),
            "common_block_reasons": [
                {"reason": reason["block_reason"], "frequency": reason["frequency"]}
                for reason in common_reasons
            ],
            "parent_review_summary": {
                "total_requests": sum(req["count"] for req in review_requests),
                "approved": next((req["count"] for req in review_requests if req["parent_decision"] == "approve"), 0),
                "denied": next((req["count"] for req in review_requests if req["parent_decision"] == "deny"), 0),
                "pending": next((req["count"] for req in review_requests if req["parent_decision"] is None), 0)
            },
            "safety_trends": await self._get_safety_trends(user_id, days),
            "recommendations": await self._generate_safety_recommendations(user_id)
        }

    def _calculate_safety_effectiveness(self, stats: Dict) -> float:
        """Calculate effectiveness of safety filtering"""
        total_blocked = stats.get("total_blocked", 0)
        if total_blocked == 0:
            return 1.0  # Perfect - nothing inappropriate encountered
        
        # Lower score if lots of content is being blocked (might indicate exposure to inappropriate content)
        if total_blocked > 50:
            return 0.7
        elif total_blocked > 20:
            return 0.8
        elif total_blocked > 5:
            return 0.9
        else:
            return 0.95

    async def _get_safety_trends(self, user_id: str, days: int) -> List[Dict]:
        """Get daily safety trends"""
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            daily_stats = await conn.fetch("""
                SELECT 
                    DATE(attempted_at) as date,
                    COUNT(*) as blocked_count,
                    COUNT(DISTINCT content_type) as blocked_types
                FROM blocked_content_log
                WHERE user_id = $1 AND attempted_at >= $2
                GROUP BY DATE(attempted_at)
                ORDER BY date DESC
            """, user_id, start_date)
        
        return [
            {
                "date": stat["date"].isoformat(),
                "blocked_count": stat["blocked_count"],
                "blocked_types": stat["blocked_types"],
                "safety_score": max(0.5, 1.0 - (stat["blocked_count"] / 20))  # Higher blocks = lower safety score
            } for stat in daily_stats
        ]

    async def _generate_safety_recommendations(self, user_id: str) -> List[str]:
        """Generate personalized safety recommendations"""
        # This would analyze patterns and generate specific recommendations
        recommendations = [
            "Continue monitoring your child's online activity",
            "Consider discussing internet safety with your child",
            "Review and update parental controls regularly"
        ]
        
        # Get recent activity to make specific recommendations
        async with self.db_pool.acquire() as conn:
            recent_blocks = await conn.fetch("""
                SELECT block_reason FROM blocked_content_log
                WHERE user_id = $1 AND attempted_at >= $2
                ORDER BY attempted_at DESC
                LIMIT 10
            """, user_id, datetime.now() - timedelta(days=7))
        
        if len(recent_blocks) > 10:
            recommendations.append("High blocking activity detected - consider reviewing browsing habits with your child")
        
        if any("violence" in block["block_reason"].lower() for block in recent_blocks):
            recommendations.append("Discuss age-appropriate content and why violent material is restricted")
        
        return recommendations

    async def update_filter_sensitivity(self, user_id: str, age: int, sensitivity_level: str) -> Dict:
        """Update filter sensitivity for a user"""
        sensitivity_multipliers = {
            "strict": 1.2,
            "normal": 1.0,
            "relaxed": 0.8
        }
        
        multiplier = sensitivity_multipliers.get(sensitivity_level, 1.0)
        
        # This would update user-specific filter settings
        # For now, we'll just return the configuration
        
        return {
            "success": True,
            "sensitivity_level": sensitivity_level,
            "multiplier": multiplier,
            "message": f"Filter sensitivity updated to {sensitivity_level} level",
            "estimated_impact": self._describe_sensitivity_impact(sensitivity_level)
        }

    def _describe_sensitivity_impact(self, sensitivity: str) -> str:
        """Describe the impact of sensitivity settings"""
        descriptions = {
            "strict": "More content will be blocked or flagged for review. Recommended for younger children or sensitive topics.",
            "normal": "Balanced filtering that blocks clearly inappropriate content while allowing educational material.",
            "relaxed": "Less restrictive filtering that allows more mature educational content. Suitable for older children with guidance."
        }
        
        return descriptions.get(sensitivity, "Standard filtering will be applied.")

    async def get_educational_content_suggestions(self, user_age: int, interests: List[str] = None) -> List[Dict]:
        """Get suggestions for age-appropriate educational content"""
        base_suggestions = [
            {
                "title": "Khan Academy Kids",
                "description": "Interactive learning activities for young children",
                "url": "https://learn.khanacademy.org/khan-academy-kids/",
                "age_range": "3-7",
                "subjects": ["Math", "Reading", "Logic"],
                "safety_rating": "Excellent"
            },
            {
                "title": "Scratch Jr",
                "description": "Visual programming language for young children",
                "url": "https://scratchjr.org/",
                "age_range": "5-7",
                "subjects": ["Programming", "Creativity", "Logic"],
                "safety_rating": "Excellent"
            },
            {
                "title": "National Geographic Kids",
                "description": "Educational content about animals, science, and nature",
                "url": "https://natgeokids.com/",
                "age_range": "6-14",
                "subjects": ["Science", "Geography", "Animals"],
                "safety_rating": "Excellent"
            }
        ]
        
        # Filter suggestions based on age
        age_appropriate = []
        for suggestion in base_suggestions:
            age_range = suggestion["age_range"].split("-")
            min_age, max_age = int(age_range[0]), int(age_range[1])
            
            if min_age <= user_age <= max_age:
                age_appropriate.append(suggestion)
        
        return age_appropriate

    async def analyze_bulk_content(self, content_items: List[Dict], user_age: int) -> Dict:
        """Analyze multiple content items in bulk"""
        results = {
            "total_analyzed": len(content_items),
            "safe_content": [],
            "flagged_content": [],
            "blocked_content": [],
            "educational_content": [],
            "summary": {
                "safe_count": 0,
                "flagged_count": 0,
                "blocked_count": 0,
                "avg_educational_value": 0
            }
        }
        
        total_educational_value = 0
        
        for item in content_items:
            analysis = await self.analyze_content(
                item["content"],
                ContentType(item.get("type", "text")),
                user_age,
                item.get("context")
            )
            
            total_educational_value += analysis.educational_value
            
            item_result = {
                "content_id": item.get("id", "unknown"),
                "safety_level": analysis.safety_level.value,
                "action": analysis.action.value,
                "educational_value": analysis.educational_value,
                "flags": analysis.flags
            }
            
            if analysis.action == FilterAction.ALLOW:
                results["safe_content"].append(item_result)
                results["summary"]["safe_count"] += 1
            elif analysis.action in [FilterAction.FLAG, FilterAction.MODERATE]:
                results["flagged_content"].append(item_result)
                results["summary"]["flagged_count"] += 1
            else:
                results["blocked_content"].append(item_result)
                results["summary"]["blocked_count"] += 1
            
            if analysis.educational_value >= 6:
                results["educational_content"].append(item_result)
        
        results["summary"]["avg_educational_value"] = (
            total_educational_value / len(content_items) if content_items else 0
        )
        
        return results

    async def get_filter_statistics(self) -> Dict:
        """Get overall filter performance statistics"""
        async with self.db_pool.acquire() as conn:
            # Get overall statistics
            overall_stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_analyses,
                    COUNT(*) FILTER (WHERE action = 'block') as blocked,
                    COUNT(*) FILTER (WHERE action = 'flag') as flagged,
                    AVG(educational_value) as avg_educational_value,
                    COUNT(DISTINCT content_type) as content_types_analyzed
                FROM content_analysis_results
                WHERE analyzed_at >= CURRENT_DATE - INTERVAL '30 days'
            """)
            
            # Get age group breakdown
            age_breakdown = await conn.fetch("""
                SELECT 
                    age_rating,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE action = 'block') as blocked
                FROM content_analysis_results
                WHERE analyzed_at >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY age_rating
                ORDER BY age_rating
            """)
        
        return {
            "period": "30 days",
            "total_content_analyzed": overall_stats["total_analyses"] or 0,
            "content_blocked": overall_stats["blocked"] or 0,
            "content_flagged": overall_stats["flagged"] or 0,
            "average_educational_value": round(overall_stats["avg_educational_value"] or 0, 1),
            "content_types_analyzed": overall_stats["content_types_analyzed"] or 0,
            "blocking_rate": (overall_stats["blocked"] / max(1, overall_stats["total_analyses"])) * 100,
            "age_group_breakdown": [
                {
                    "age_rating": item["age_rating"],
                    "total_analyzed": item["count"],
                    "blocked": item["blocked"],
                    "block_rate": (item["blocked"] / max(1, item["count"])) * 100
                } for item in age_breakdown
            ],
            "filter_effectiveness": "High" if overall_stats["blocked"] and overall_stats["blocked"] < overall_stats["total_analyses"] * 0.1 else "Normal"
        }