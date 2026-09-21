import asyncio
import asyncpg
import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
from datetime import datetime, timedelta


class ContentType(Enum):
    TEXT = "text"
    URL = "url"
    IMAGE = "image"
    VIDEO = "video"
    PROJECT_CODE = "project_code"
    CHAT_MESSAGE = "chat_message"


class FilterAction(Enum):
    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"
    MODERATE = "moderate"


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    BLOCKED = "blocked"


@dataclass
class FilterRule:
    rule_id: str
    name: str
    description: str
    content_types: List[ContentType]
    age_min: int
    age_max: int
    keywords_blocked: List[str]
    keywords_flagged: List[str]
    regex_patterns: List[str]
    domain_whitelist: List[str]
    domain_blacklist: List[str]
    action: FilterAction
    is_active: bool = True


@dataclass
class ContentAnalysisResult:
    content_id: str
    content_type: ContentType
    risk_level: RiskLevel
    action: FilterAction
    confidence_score: float
    flagged_elements: List[str]
    suggested_modifications: List[str]
    parent_review_required: bool
    analysis_details: Dict


class ContentFilter:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.filter_rules: Dict[str, List[FilterRule]] = {}
        self.blocked_keywords = self._initialize_blocked_keywords()
        self.educational_keywords = self._initialize_educational_keywords()
        
    async def initialize_tables(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS content_filter_rules (
                    id SERIAL PRIMARY KEY,
                    rule_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    content_types JSONB NOT NULL,
                    age_min INTEGER NOT NULL,
                    age_max INTEGER NOT NULL,
                    keywords_blocked JSONB DEFAULT '[]',
                    keywords_flagged JSONB DEFAULT '[]',
                    regex_patterns JSONB DEFAULT '[]',
                    domain_whitelist JSONB DEFAULT '[]',
                    domain_blacklist JSONB DEFAULT '[]',
                    action VARCHAR(20) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS content_analysis_log (
                    id SERIAL PRIMARY KEY,
                    content_id VARCHAR(100) NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    content_type VARCHAR(20) NOT NULL,
                    risk_level VARCHAR(20) NOT NULL,
                    action VARCHAR(20) NOT NULL,
                    confidence_score FLOAT NOT NULL,
                    flagged_elements JSONB DEFAULT '[]',
                    analysis_details JSONB DEFAULT '{}',
                    parent_notified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked_content (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    content_hash VARCHAR(64) NOT NULL,
                    content_type VARCHAR(20) NOT NULL,
                    reason TEXT NOT NULL,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(content_hash, user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parent_review_queue (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    content_id VARCHAR(100) NOT NULL,
                    content_preview TEXT,
                    content_type VARCHAR(20) NOT NULL,
                    flagged_reason TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    parent_decision VARCHAR(20),
                    reviewed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _initialize_blocked_keywords(self) -> Dict[str, List[str]]:
        """Initialize age-appropriate blocked keywords"""
        return {
            "violence": [
                "kill", "murder", "death", "weapon", "gun", "knife", "blood", "hurt",
                "fight", "attack", "war", "bomb", "explosive", "dangerous"
            ],
            "inappropriate_content": [
                "adult", "mature", "explicit", "inappropriate", "private", "secret"
            ],
            "personal_info": [
                "address", "phone number", "credit card", "password", "social security",
                "full name", "school name", "location"
            ],
            "negative_behavior": [
                "hate", "bully", "mean", "stupid", "dumb", "loser", "ugly",
                "cheat", "steal", "lie"
            ],
            "unsafe_activities": [
                "meet stranger", "run away", "skip school", "sneak out",
                "dangerous challenge", "risky behavior"
            ]
        }
    
    def _initialize_educational_keywords(self) -> Dict[str, List[str]]:
        """Initialize educational and positive keywords"""
        return {
            "learning": [
                "learn", "study", "education", "knowledge", "skill", "practice",
                "improve", "grow", "develop", "understand"
            ],
            "creativity": [
                "create", "build", "design", "art", "music", "story", "imagine",
                "invent", "craft", "project"
            ],
            "positive_values": [
                "kind", "help", "share", "friend", "team", "cooperation",
                "respect", "honest", "caring", "supportive"
            ],
            "science_tech": [
                "science", "experiment", "discover", "technology", "robot",
                "coding", "program", "math", "engineering"
            ]
        }

    async def analyze_content(self, content: str, content_type: ContentType, user_id: str, context: Dict = None) -> ContentAnalysisResult:
        """Analyze content for age-appropriateness and safety"""
        user_age = await self.get_user_age(user_id)
        rules = await self.get_active_rules(user_age, content_type)
        
        analysis_result = ContentAnalysisResult(
            content_id=f"{user_id}_{datetime.now().timestamp()}",
            content_type=content_type,
            risk_level=RiskLevel.SAFE,
            action=FilterAction.ALLOW,
            confidence_score=1.0,
            flagged_elements=[],
            suggested_modifications=[],
            parent_review_required=False,
            analysis_details={}
        )
        
        # Run content through filters
        content_lower = content.lower()
        flagged_issues = []
        risk_scores = []
        
        # Check blocked keywords
        for category, keywords in self.blocked_keywords.items():
            found_keywords = [kw for kw in keywords if kw in content_lower]
            if found_keywords:
                flagged_issues.append(f"Contains {category} keywords: {', '.join(found_keywords[:3])}")
                risk_scores.append(0.8)
                analysis_result.flagged_elements.extend(found_keywords)
        
        # Check against custom rules
        for rule in rules:
            rule_violations = self._check_rule_violations(content, rule)
            if rule_violations:
                flagged_issues.extend(rule_violations)
                risk_scores.append(0.7)
        
        # URL-specific checks
        if content_type == ContentType.URL:
            url_analysis = await self._analyze_url(content, user_age)
            if url_analysis["blocked"]:
                flagged_issues.append(f"Blocked domain: {url_analysis['reason']}")
                risk_scores.append(0.9)
        
        # Project code checks
        if content_type == ContentType.PROJECT_CODE:
            code_issues = self._analyze_code_safety(content)
            flagged_issues.extend(code_issues)
            if code_issues:
                risk_scores.append(0.6)
        
        # Calculate overall risk level
        if risk_scores:
            avg_risk = sum(risk_scores) / len(risk_scores)
            analysis_result.confidence_score = avg_risk
            
            if avg_risk >= 0.8:
                analysis_result.risk_level = RiskLevel.BLOCKED
                analysis_result.action = FilterAction.BLOCK
            elif avg_risk >= 0.6:
                analysis_result.risk_level = RiskLevel.HIGH
                analysis_result.action = FilterAction.REVIEW
                analysis_result.parent_review_required = True
            elif avg_risk >= 0.4:
                analysis_result.risk_level = RiskLevel.MEDIUM
                analysis_result.action = FilterAction.MODERATE
            else:
                analysis_result.risk_level = RiskLevel.LOW
                analysis_result.action = FilterAction.ALLOW
        
        # Generate suggestions for blocked content
        if analysis_result.action in [FilterAction.BLOCK, FilterAction.REVIEW]:
            analysis_result.suggested_modifications = self._generate_content_suggestions(
                content, flagged_issues, user_age
            )
        
        analysis_result.analysis_details = {
            "flagged_issues": flagged_issues,
            "user_age": user_age,
            "rules_applied": len(rules),
            "educational_score": self._calculate_educational_score(content),
            "timestamp": datetime.now().isoformat()
        }
        
        # Log the analysis
        await self._log_content_analysis(user_id, analysis_result)
        
        return analysis_result

    def _check_rule_violations(self, content: str, rule: FilterRule) -> List[str]:
        """Check content against specific filter rule"""
        violations = []
        content_lower = content.lower()
        
        # Check blocked keywords
        for keyword in rule.keywords_blocked:
            if keyword.lower() in content_lower:
                violations.append(f"Rule '{rule.name}': blocked keyword '{keyword}'")
        
        # Check regex patterns
        for pattern in rule.regex_patterns:
            try:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(f"Rule '{rule.name}': pattern match")
            except re.error:
                continue  # Skip invalid regex
        
        return violations

    async def _analyze_url(self, url: str, user_age: int) -> Dict:
        """Analyze URL for safety and age-appropriateness"""
        import urllib.parse
        
        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Educational domains (always allowed)
        educational_domains = {
            "khan-academy.org", "scratch.mit.edu", "code.org", "nasa.gov",
            "nationalgeographic.com", "smithsonian.com", "britannica.com"
        }
        
        if any(edu_domain in domain for edu_domain in educational_domains):
            return {"blocked": False, "reason": "Educational content", "category": "educational"}
        
        # Age-specific domain restrictions
        if user_age < 10:
            # Very restrictive for young children
            allowed_domains = {
                "pbskids.org", "sesamestreet.org", "nickjr.com", "disney.com",
                "scratch.mit.edu", "code.org"
            }
            if not any(allowed in domain for allowed in allowed_domains):
                return {"blocked": True, "reason": "Not in allowed list for age group", "category": "age_restriction"}
        
        # Check for problematic domains
        blocked_domains = {
            "social media", "gaming", "streaming", "shopping", "news"
        }
        
        # Simple domain categorization (in real implementation, use proper categorization service)
        if any(blocked in domain for blocked in ["facebook", "instagram", "twitter", "tiktok"]):
            return {"blocked": True, "reason": "Social media platform", "category": "social_media"}
        
        return {"blocked": False, "reason": "No restrictions found", "category": "general"}

    def _analyze_code_safety(self, code: str) -> List[str]:
        """Analyze code for potentially unsafe operations"""
        issues = []
        code_lower = code.lower()
        
        # Check for potentially dangerous operations
        unsafe_operations = [
            ("file deletion", ["delete", "remove", "unlink", "rm "]),
            ("network requests", ["http", "request", "fetch", "download"]),
            ("system commands", ["system", "exec", "shell", "command"]),
            ("file system access", ["open(", "file(", "read(", "write("]),
        ]
        
        for operation_name, keywords in unsafe_operations:
            if any(keyword in code_lower for keyword in keywords):
                issues.append(f"Code contains {operation_name} operations")
        
        # Check for good practices
        if "import" in code_lower and ("os" in code_lower or "sys" in code_lower):
            issues.append("Code imports system modules - requires review")
        
        return issues

    def _calculate_educational_score(self, content: str) -> float:
        """Calculate how educational/beneficial the content is"""
        content_lower = content.lower()
        educational_score = 0.0
        
        for category, keywords in self.educational_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            educational_score += matches * 0.1
        
        return min(educational_score, 1.0)

    def _generate_content_suggestions(self, content: str, issues: List[str], user_age: int) -> List[str]:
        """Generate suggestions to make content more appropriate"""
        suggestions = []
        
        if any("violence" in issue.lower() for issue in issues):
            suggestions.append("Consider using friendlier language like 'stop', 'pause', or 'reset' instead")
        
        if any("personal" in issue.lower() for issue in issues):
            suggestions.append("Remove any personal information like names, addresses, or phone numbers")
        
        if any("negative" in issue.lower() for issue in issues):
            suggestions.append("Try using more positive and encouraging words")
        
        if user_age < 10:
            suggestions.append("Use simple, clear language appropriate for younger children")
        
        suggestions.append("Focus on learning, creativity, and positive interactions")
        
        return suggestions

    async def get_user_age(self, user_id: str) -> int:
        """Get user age from parent/user profile"""
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval("""
                SELECT age FROM user_profiles WHERE user_id = $1
            """, user_id)
            
            return result if result else 10  # Default age

    async def get_active_rules(self, user_age: int, content_type: ContentType) -> List[FilterRule]:
        """Get active filter rules for user age and content type"""
        cache_key = f"{user_age}_{content_type.value}"
        if cache_key in self.filter_rules:
            return self.filter_rules[cache_key]
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM content_filter_rules
                WHERE is_active = TRUE 
                AND age_min <= $1 AND age_max >= $1
                AND content_types @> $2::jsonb
            """, user_age, json.dumps([content_type.value]))
        
        rules = []
        for row in rows:
            rule = FilterRule(
                rule_id=row['rule_id'],
                name=row['name'],
                description=row['description'],
                content_types=[ContentType(ct) for ct in json.loads(row['content_types'])],
                age_min=row['age_min'],
                age_max=row['age_max'],
                keywords_blocked=json.loads(row['keywords_blocked']),
                keywords_flagged=json.loads(row['keywords_flagged']),
                regex_patterns=json.loads(row['regex_patterns']),
                domain_whitelist=json.loads(row['domain_whitelist']),
                domain_blacklist=json.loads(row['domain_blacklist']),
                action=FilterAction(row['action']),
                is_active=row['is_active']
            )
            rules.append(rule)
        
        self.filter_rules[cache_key] = rules
        return rules

    async def _log_content_analysis(self, user_id: str, result: ContentAnalysisResult):
        """Log content analysis results"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO content_analysis_log (
                    content_id, user_id, content_type, risk_level, action,
                    confidence_score, flagged_elements, analysis_details
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                result.content_id, user_id, result.content_type.value,
                result.risk_level.value, result.action.value,
                result.confidence_score, json.dumps(result.flagged_elements),
                json.dumps(result.analysis_details)
            )

    async def add_to_parent_review_queue(self, user_id: str, content_id: str, content_preview: str, 
                                       content_type: ContentType, reason: str) -> Dict:
        """Add content to parent review queue"""
        async with self.db_pool.acquire() as conn:
            review_id = await conn.fetchval("""
                INSERT INTO parent_review_queue (
                    user_id, content_id, content_preview, content_type, flagged_reason
                ) VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, user_id, content_id, content_preview[:500], content_type.value, reason)
        
        # Notify parent (integrate with notification system)
        await self._notify_parent_review_needed(user_id, review_id, reason)
        
        return {
            "review_id": review_id,
            "message": "Content has been sent for parent review",
            "estimated_review_time": "Usually within 1 hour"
        }

    async def _notify_parent_review_needed(self, user_id: str, review_id: int, reason: str):
        """Send notification to parent about content needing review"""
        # This would integrate with the notification system
        notification_data = {
            "type": "content_review_needed",
            "user_id": user_id,
            "review_id": review_id,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        # TODO: Send notification via email, SMS, or app notification

    async def get_content_safety_report(self, user_id: str, days: int = 7) -> Dict:
        """Generate content safety report for parents"""
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            # Get analysis statistics
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_analyzed,
                    COUNT(*) FILTER (WHERE action = 'block') as blocked_count,
                    COUNT(*) FILTER (WHERE action = 'review') as review_count,
                    AVG(confidence_score) as avg_confidence,
                    COUNT(DISTINCT content_type) as content_types_analyzed
                FROM content_analysis_log
                WHERE user_id = $1 AND created_at >= $2
            """, user_id, start_date)
            
            # Get most common flagged elements
            flagged_elements = await conn.fetch("""
                SELECT 
                    jsonb_array_elements_text(flagged_elements) as element,
                    COUNT(*) as frequency
                FROM content_analysis_log
                WHERE user_id = $1 AND created_at >= $2
                    AND jsonb_array_length(flagged_elements) > 0
                GROUP BY element
                ORDER BY frequency DESC
                LIMIT 10
            """, user_id, start_date)
            
            # Get pending reviews
            pending_reviews = await conn.fetch("""
                SELECT content_type, flagged_reason, created_at
                FROM parent_review_queue
                WHERE user_id = $1 AND status = 'pending'
                ORDER BY created_at DESC
            """, user_id)
        
        return {
            "period_days": days,
            "total_content_analyzed": stats['total_analyzed'] or 0,
            "content_blocked": stats['blocked_count'] or 0,
            "content_flagged_for_review": stats['review_count'] or 0,
            "average_safety_score": round(1 - (stats['avg_confidence'] or 0), 2),
            "content_types_analyzed": stats['content_types_analyzed'] or 0,
            "most_common_flags": [
                {"element": elem['element'], "frequency": elem['frequency']} 
                for elem in flagged_elements
            ],
            "pending_parent_reviews": len(pending_reviews),
            "review_details": [
                {
                    "type": review['content_type'],
                    "reason": review['flagged_reason'],
                    "time": review['created_at'].isoformat()
                } for review in pending_reviews[:5]  # Show latest 5
            ],
            "safety_trends": await self._get_safety_trends(user_id, days),
            "recommendations": await self._generate_safety_recommendations(user_id)
        }

    async def _get_safety_trends(self, user_id: str, days: int) -> List[Dict]:
        """Get daily safety trends"""
        start_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            daily_stats = await conn.fetch("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total_content,
                    COUNT(*) FILTER (WHERE action = 'block') as blocked,
                    COUNT(*) FILTER (WHERE action = 'review') as reviewed,
                    AVG(confidence_score) as avg_risk
                FROM content_analysis_log
                WHERE user_id = $1 AND created_at >= $2
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, user_id, start_date)
        
        return [
            {
                "date": stat['date'].isoformat(),
                "total_content": stat['total_content'],
                "blocked": stat['blocked'],
                "reviewed": stat['reviewed'],
                "safety_score": round(1 - (stat['avg_risk'] or 0), 2)
            } for stat in daily_stats
        ]

    async def _generate_safety_recommendations(self, user_id: str) -> List[str]:
        """Generate personalized safety recommendations"""
        recommendations = []
        user_age = await self.get_user_age(user_id)
        
        # Get recent analysis data
        recent_data = await self.get_content_safety_report(user_id, 7)
        
        if recent_data["content_blocked"] > recent_data["total_content_analyzed"] * 0.2:
            recommendations.append(
                "Consider reviewing content guidelines with your child - they may need help understanding appropriate content."
            )
        
        if recent_data["pending_parent_reviews"] > 5:
            recommendations.append(
                "You have several items waiting for review. Regular reviews help your child learn boundaries."
            )
        
        if user_age < 10 and recent_data["total_content_analyzed"] > 50:
            recommendations.append(
                "Your child is very active online. Consider setting specific times for digital activities."
            )
        
        # Add age-appropriate general recommendations
        if user_age < 8:
            recommendations.append("Encourage supervised browsing and co-viewing content together.")
        elif user_age < 12:
            recommendations.append("Help your child develop critical thinking about online content.")
        else:
            recommendations.append("Focus on teaching digital citizenship and responsible online behavior.")
        
        return recommendations

    async def create_filter_rule(self, rule_data: Dict) -> Dict:
        """Create a new content filter rule"""
        rule = FilterRule(**rule_data)
        
        async with self.db_pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO content_filter_rules (
                        rule_id, name, description, content_types, age_min, age_max,
                        keywords_blocked, keywords_flagged, regex_patterns,
                        domain_whitelist, domain_blacklist, action
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    rule.rule_id, rule.name, rule.description,
                    json.dumps([ct.value for ct in rule.content_types]),
                    rule.age_min, rule.age_max,
                    json.dumps(rule.keywords_blocked),
                    json.dumps(rule.keywords_flagged),
                    json.dumps(rule.regex_patterns),
                    json.dumps(rule.domain_whitelist),
                    json.dumps(rule.domain_blacklist),
                    rule.action.value
                )
                
                # Clear cache
                self.filter_rules.clear()
                
                return {"success": True, "rule_id": rule.rule_id}
                
            except asyncpg.UniqueViolationError:
                return {"success": False, "error": "Rule ID already exists"}

    async def update_filter_rule(self, rule_id: str, updates: Dict) -> Dict:
        """Update an existing filter rule"""
        # Build update query dynamically
        set_clauses = []
        values = []
        param_count = 1
        
        allowed_fields = {
            'name', 'description', 'content_types', 'age_min', 'age_max',
            'keywords_blocked', 'keywords_flagged', 'regex_patterns',
            'domain_whitelist', 'domain_blacklist', 'action', 'is_active'
        }
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ${param_count}")
                if field in ['content_types', 'keywords_blocked', 'keywords_flagged', 
                           'regex_patterns', 'domain_whitelist', 'domain_blacklist']:
                    values.append(json.dumps(value))
                else:
                    values.append(value)
                param_count += 1
        
        if not set_clauses:
            return {"success": False, "error": "No valid fields to update"}
        
        values.append(rule_id)
        
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(f"""
                UPDATE content_filter_rules
                SET {', '.join(set_clauses)}
                WHERE rule_id = ${param_count}
            """, *values)
            
            if result == "UPDATE 0":
                return {"success": False, "error": "Rule not found"}
            
            # Clear cache
            self.filter_rules.clear()
            
            return {"success": True, "message": "Rule updated successfully"}

    async def get_filter_rules(self, age_range: Tuple[int, int] = None) -> List[Dict]:
        """Get all filter rules, optionally filtered by age range"""
        async with self.db_pool.acquire() as conn:
            if age_range:
                rows = await conn.fetch("""
                    SELECT * FROM content_filter_rules
                    WHERE age_min <= $2 AND age_max >= $1
                    ORDER BY age_min, name
                """, age_range[0], age_range[1])
            else:
                rows = await conn.fetch("""
                    SELECT * FROM content_filter_rules
                    ORDER BY age_min, name
                """)
        
        rules = []
        for row in rows:
            rule_dict = dict(row)
            # Parse JSON fields
            json_fields = ['content_types', 'keywords_blocked', 'keywords_flagged', 
                          'regex_patterns', 'domain_whitelist', 'domain_blacklist']
            for field in json_fields:
                rule_dict[field] = json.loads(rule_dict[field])
            rules.append(rule_dict)
        
        return rules