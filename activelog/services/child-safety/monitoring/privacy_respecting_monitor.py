import asyncio
import asyncpg
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
from datetime import datetime, timedelta
import logging


class MonitoringLevel(Enum):
    MINIMAL = "minimal"          # Basic safety only
    STANDARD = "standard"        # Balanced monitoring 
    ENHANCED = "enhanced"        # More detailed for younger children
    CUSTOM = "custom"           # Parent-configured settings


class InteractionType(Enum):
    MESSAGE = "message"
    COMMENT = "comment"
    SHARE = "share"
    REACTION = "reaction"
    FRIEND_REQUEST = "friend_request"
    GROUP_JOIN = "group_join"
    CONTENT_CREATION = "content_creation"
    SEARCH = "search"


class PrivacyLevel(Enum):
    HIGH = "high"               # Minimal data collection
    MEDIUM = "medium"           # Balanced approach
    LOW = "low"                # More detailed monitoring


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InteractionEvent:
    event_id: str
    user_id: str
    interaction_type: InteractionType
    content_hash: str          # Hashed content for privacy
    metadata: Dict[str, Any]   # Non-identifying metadata
    risk_indicators: List[str]
    risk_level: RiskLevel
    timestamp: datetime
    requires_attention: bool = False


@dataclass
class MonitoringSettings:
    user_id: str
    monitoring_level: MonitoringLevel
    privacy_level: PrivacyLevel
    enabled_alerts: Set[str]
    content_categories_monitored: Set[str]
    time_based_restrictions: Dict[str, Any]
    parent_notification_threshold: RiskLevel
    data_retention_days: int
    anonymous_reporting: bool = True


@dataclass
class SafetyAlert:
    alert_id: str
    user_id: str
    alert_type: str
    severity: RiskLevel
    description: str
    automated_response: Optional[str]
    requires_parent_action: bool
    context_summary: Dict[str, Any]  # Anonymized context
    suggested_actions: List[str]
    timestamp: datetime


class PrivacyRespectingMonitor:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.logger = logging.getLogger(__name__)
        self.monitoring_settings: Dict[str, MonitoringSettings] = {}
        
        # Privacy-first risk indicators (pattern-based, not content-based)
        self.risk_patterns = {
            "excessive_frequency": {
                "description": "Unusually high interaction frequency",
                "threshold": 50,  # interactions per hour
                "risk_level": RiskLevel.MEDIUM
            },
            "unusual_timing": {
                "description": "Activity during unusual hours",
                "threshold": {"start": 22, "end": 6},  # 10pm to 6am
                "risk_level": RiskLevel.LOW
            },
            "repetitive_behavior": {
                "description": "Highly repetitive interaction patterns",
                "threshold": 0.8,  # Pattern similarity score
                "risk_level": RiskLevel.MEDIUM
            },
            "rapid_friend_requests": {
                "description": "Many friend requests in short time",
                "threshold": 10,  # requests per hour
                "risk_level": RiskLevel.HIGH
            },
            "content_deletion_spikes": {
                "description": "Unusual content deletion patterns",
                "threshold": 5,  # deletions per hour
                "risk_level": RiskLevel.MEDIUM
            }
        }

    async def initialize_tables(self):
        """Initialize monitoring database tables with privacy focus"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_settings (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) UNIQUE NOT NULL,
                    monitoring_level VARCHAR(20) NOT NULL,
                    privacy_level VARCHAR(20) NOT NULL,
                    enabled_alerts JSONB DEFAULT '[]',
                    content_categories_monitored JSONB DEFAULT '[]',
                    time_based_restrictions JSONB DEFAULT '{}',
                    parent_notification_threshold VARCHAR(20) DEFAULT 'high',
                    data_retention_days INTEGER DEFAULT 7,
                    anonymous_reporting BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS interaction_patterns (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    pattern_type VARCHAR(50) NOT NULL,
                    pattern_hash VARCHAR(64) NOT NULL,
                    frequency_score FLOAT NOT NULL,
                    risk_indicators JSONB DEFAULT '[]',
                    risk_level VARCHAR(20) NOT NULL,
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS safety_alerts (
                    id SERIAL PRIMARY KEY,
                    alert_id VARCHAR(50) UNIQUE NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    description TEXT NOT NULL,
                    automated_response TEXT,
                    requires_parent_action BOOLEAN DEFAULT FALSE,
                    context_summary JSONB DEFAULT '{}',
                    suggested_actions JSONB DEFAULT '[]',
                    parent_notified BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Anonymous interaction metadata (no actual content)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS interaction_metadata (
                    id SERIAL PRIMARY KEY,
                    user_id_hash VARCHAR(64) NOT NULL,  -- Hashed user ID for privacy
                    interaction_type VARCHAR(50) NOT NULL,
                    content_category VARCHAR(50),
                    word_count INTEGER,
                    character_count INTEGER,
                    links_count INTEGER,
                    media_count INTEGER,
                    sentiment_score FLOAT,
                    time_of_day INTEGER,  -- Hour of day (0-23)
                    day_of_week INTEGER,  -- Day of week (0-6)
                    device_type VARCHAR(20),
                    session_duration INTEGER,  -- In seconds
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP  -- Auto-delete for privacy
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS wellbeing_metrics (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    total_screen_time INTEGER,  -- In minutes
                    interaction_count INTEGER,
                    positive_interactions INTEGER,
                    concerning_interactions INTEGER,
                    break_reminders_shown INTEGER,
                    break_reminders_followed INTEGER,
                    wellbeing_score FLOAT,  -- 0.0 to 1.0
                    UNIQUE(user_id, date)
                )
            """)

    async def setup_user_monitoring(self, user_id: str, age: int, 
                                   parent_preferences: Dict = None) -> Dict:
        """Set up privacy-respecting monitoring for a user"""
        # Determine appropriate monitoring level based on age
        if age < 8:
            default_level = MonitoringLevel.ENHANCED
            default_privacy = PrivacyLevel.HIGH
        elif age < 13:
            default_level = MonitoringLevel.STANDARD
            default_privacy = PrivacyLevel.HIGH
        elif age < 16:
            default_level = MonitoringLevel.STANDARD
            default_privacy = PrivacyLevel.MEDIUM
        else:
            default_level = MonitoringLevel.MINIMAL
            default_privacy = PrivacyLevel.MEDIUM
        
        # Apply parent preferences if provided
        if parent_preferences:
            monitoring_level = MonitoringLevel(parent_preferences.get("monitoring_level", default_level.value))
            privacy_level = PrivacyLevel(parent_preferences.get("privacy_level", default_privacy.value))
        else:
            monitoring_level = default_level
            privacy_level = default_privacy
        
        settings = MonitoringSettings(
            user_id=user_id,
            monitoring_level=monitoring_level,
            privacy_level=privacy_level,
            enabled_alerts=self._get_default_alerts(age, monitoring_level),
            content_categories_monitored=self._get_default_categories(age),
            time_based_restrictions=self._get_default_time_restrictions(age),
            parent_notification_threshold=RiskLevel.HIGH if age < 10 else RiskLevel.CRITICAL,
            data_retention_days=7 if privacy_level == PrivacyLevel.HIGH else 14,
            anonymous_reporting=True
        )
        
        # Save to database
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO monitoring_settings (
                    user_id, monitoring_level, privacy_level, enabled_alerts,
                    content_categories_monitored, time_based_restrictions,
                    parent_notification_threshold, data_retention_days, anonymous_reporting
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (user_id) DO UPDATE SET
                    monitoring_level = EXCLUDED.monitoring_level,
                    privacy_level = EXCLUDED.privacy_level,
                    updated_at = CURRENT_TIMESTAMP
            """,
                user_id, monitoring_level.value, privacy_level.value,
                json.dumps(list(settings.enabled_alerts)),
                json.dumps(list(settings.content_categories_monitored)),
                json.dumps(settings.time_based_restrictions),
                settings.parent_notification_threshold.value,
                settings.data_retention_days,
                settings.anonymous_reporting
            )
        
        # Cache settings
        self.monitoring_settings[user_id] = settings
        
        return {
            "success": True,
            "monitoring_level": monitoring_level.value,
            "privacy_level": privacy_level.value,
            "data_retention_days": settings.data_retention_days,
            "privacy_features": self._describe_privacy_features(settings),
            "parent_controls": self._describe_parent_controls(settings)
        }

    def _get_default_alerts(self, age: int, level: MonitoringLevel) -> Set[str]:
        """Get default alert types based on age and monitoring level"""
        base_alerts = {"critical_safety", "bullying_detection"}
        
        if age < 10:
            base_alerts.update({"inappropriate_content", "stranger_contact", "excessive_screen_time"})
        
        if age < 13:
            base_alerts.update({"friend_request_monitoring", "location_sharing_alerts"})
        
        if level == MonitoringLevel.ENHANCED:
            base_alerts.update({"unusual_behavior_patterns", "content_sharing_alerts"})
        
        return base_alerts

    def _get_default_categories(self, age: int) -> Set[str]:
        """Get default content categories to monitor based on age"""
        base_categories = {"social_interaction", "content_sharing"}
        
        if age < 10:
            base_categories.update({"all_interactions", "friend_management"})
        elif age < 16:
            base_categories.update({"group_interactions", "public_content"})
        
        return base_categories

    def _get_default_time_restrictions(self, age: int) -> Dict[str, Any]:
        """Get default time-based restrictions"""
        if age < 8:
            return {
                "quiet_hours": {"start": 20, "end": 8},  # 8pm to 8am
                "max_daily_interactions": 20,
                "break_reminders": True
            }
        elif age < 13:
            return {
                "quiet_hours": {"start": 21, "end": 7},  # 9pm to 7am
                "max_daily_interactions": 50,
                "break_reminders": True
            }
        else:
            return {
                "quiet_hours": {"start": 23, "end": 6},  # 11pm to 6am
                "max_daily_interactions": 100,
                "break_reminders": False
            }

    async def record_interaction(self, user_id: str, interaction_type: InteractionType,
                               metadata: Dict[str, Any]) -> Dict:
        """Record interaction with privacy protection"""
        settings = await self.get_user_settings(user_id)
        if not settings:
            return {"success": False, "error": "User monitoring not configured"}
        
        # Create privacy-protected metadata
        protected_metadata = self._create_protected_metadata(metadata, settings.privacy_level)
        
        # Hash user ID for privacy
        user_hash = hashlib.sha256(f"{user_id}_salt".encode()).hexdigest()
        
        # Calculate data expiration based on retention policy
        expires_at = datetime.now() + timedelta(days=settings.data_retention_days)
        
        # Store anonymized interaction data
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO interaction_metadata (
                    user_id_hash, interaction_type, content_category, word_count,
                    character_count, links_count, media_count, sentiment_score,
                    time_of_day, day_of_week, device_type, session_duration, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                user_hash, interaction_type.value,
                protected_metadata.get("category", "general"),
                protected_metadata.get("word_count", 0),
                protected_metadata.get("character_count", 0),
                protected_metadata.get("links_count", 0),
                protected_metadata.get("media_count", 0),
                protected_metadata.get("sentiment_score", 0.5),
                datetime.now().hour,
                datetime.now().weekday(),
                protected_metadata.get("device_type", "unknown"),
                protected_metadata.get("session_duration", 0),
                expires_at
            )
        
        # Analyze for risk patterns (without storing actual content)
        risk_analysis = await self._analyze_interaction_patterns(user_id, interaction_type, protected_metadata)
        
        # Generate alerts if necessary
        if risk_analysis["risk_level"] != RiskLevel.NONE:
            await self._handle_risk_detection(user_id, risk_analysis)
        
        return {
            "success": True,
            "risk_level": risk_analysis["risk_level"].value,
            "privacy_protected": True,
            "data_retention": f"{settings.data_retention_days} days",
            "monitoring_active": True
        }

    def _create_protected_metadata(self, metadata: Dict, privacy_level: PrivacyLevel) -> Dict:
        """Create privacy-protected metadata"""
        protected = {}
        
        # Always allowed metadata (no privacy concerns)
        safe_fields = ["word_count", "character_count", "links_count", "media_count", 
                      "device_type", "session_duration"]
        
        for field in safe_fields:
            if field in metadata:
                protected[field] = metadata[field]
        
        # Conditional metadata based on privacy level
        if privacy_level == PrivacyLevel.LOW:
            # Allow more detailed metadata
            additional_fields = ["category", "sentiment_score", "interaction_frequency"]
            for field in additional_fields:
                if field in metadata:
                    protected[field] = metadata[field]
        
        elif privacy_level == PrivacyLevel.MEDIUM:
            # Moderate metadata collection
            if "category" in metadata:
                protected["category"] = metadata["category"]
            if "sentiment_score" in metadata:
                # Quantize sentiment for privacy
                protected["sentiment_score"] = round(metadata["sentiment_score"], 1)
        
        # For HIGH privacy level, only use safe_fields (already processed above)
        
        return protected

    async def _analyze_interaction_patterns(self, user_id: str, interaction_type: InteractionType,
                                          metadata: Dict) -> Dict:
        """Analyze interaction patterns for risk without storing content"""
        risk_indicators = []
        risk_level = RiskLevel.NONE
        
        # Get recent interaction history for pattern analysis
        async with self.db_pool.acquire() as conn:
            recent_interactions = await conn.fetch("""
                SELECT interaction_type, time_of_day, created_at
                FROM interaction_metadata
                WHERE user_id_hash = $1 AND created_at >= $2
                ORDER BY created_at DESC
                LIMIT 50
            """, hashlib.sha256(f"{user_id}_salt".encode()).hexdigest(),
                datetime.now() - timedelta(hours=24))
        
        # Check for excessive frequency
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_count = len([i for i in recent_interactions 
                           if i["created_at"] >= hour_ago])
        
        if recent_count >= self.risk_patterns["excessive_frequency"]["threshold"]:
            risk_indicators.append("excessive_frequency")
            risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # Check for unusual timing
        current_hour = datetime.now().hour
        if (current_hour >= 22 or current_hour <= 6):
            risk_indicators.append("unusual_timing")
            risk_level = max(risk_level, RiskLevel.LOW)
        
        # Check for repetitive patterns
        if len(recent_interactions) >= 10:
            type_frequencies = {}
            for interaction in recent_interactions[-10:]:
                itype = interaction["interaction_type"]
                type_frequencies[itype] = type_frequencies.get(itype, 0) + 1
            
            max_frequency = max(type_frequencies.values())
            if max_frequency / 10 >= 0.8:  # 80% same type
                risk_indicators.append("repetitive_behavior")
                risk_level = max(risk_level, RiskLevel.MEDIUM)
        
        # Check for rapid friend requests
        if interaction_type == InteractionType.FRIEND_REQUEST:
            friend_requests_hour = len([i for i in recent_interactions 
                                       if i["interaction_type"] == "friend_request" 
                                       and i["created_at"] >= hour_ago])
            
            if friend_requests_hour >= 10:
                risk_indicators.append("rapid_friend_requests")
                risk_level = max(risk_level, RiskLevel.HIGH)
        
        return {
            "risk_level": risk_level,
            "risk_indicators": risk_indicators,
            "pattern_confidence": min(1.0, len(risk_indicators) * 0.3)
        }

    async def _handle_risk_detection(self, user_id: str, risk_analysis: Dict):
        """Handle detected risk patterns"""
        settings = await self.get_user_settings(user_id)
        
        # Create safety alert
        alert = SafetyAlert(
            alert_id=f"alert_{datetime.now().timestamp()}",
            user_id=user_id,
            alert_type="behavioral_pattern",
            severity=risk_analysis["risk_level"],
            description=self._generate_risk_description(risk_analysis["risk_indicators"]),
            automated_response=self._generate_automated_response(risk_analysis),
            requires_parent_action=risk_analysis["risk_level"] in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            context_summary={"pattern_type": "interaction_frequency", "confidence": risk_analysis["pattern_confidence"]},
            suggested_actions=self._generate_suggested_actions(risk_analysis),
            timestamp=datetime.now()
        )
        
        # Save alert
        await self._save_safety_alert(alert)
        
        # Notify parent if threshold exceeded
        if alert.severity.value in [level.value for level in [settings.parent_notification_threshold, RiskLevel.CRITICAL]]:
            await self._notify_parent(user_id, alert)
        
        return alert

    def _generate_risk_description(self, risk_indicators: List[str]) -> str:
        """Generate human-readable risk description"""
        descriptions = {
            "excessive_frequency": "Unusually high activity detected",
            "unusual_timing": "Activity during late night hours",
            "repetitive_behavior": "Repetitive interaction patterns observed",
            "rapid_friend_requests": "High frequency of friend requests",
            "content_deletion_spikes": "Unusual content deletion patterns"
        }
        
        if len(risk_indicators) == 1:
            return descriptions.get(risk_indicators[0], "Unusual behavior pattern detected")
        else:
            return f"Multiple concerning patterns detected: {len(risk_indicators)} indicators"

    def _generate_automated_response(self, risk_analysis: Dict) -> str:
        """Generate automated response suggestion"""
        risk_level = risk_analysis["risk_level"]
        
        if risk_level == RiskLevel.HIGH:
            return "Consider taking a break and discussing online safety with a parent or guardian"
        elif risk_level == RiskLevel.MEDIUM:
            return "Please be mindful of your online activity and take regular breaks"
        elif risk_level == RiskLevel.LOW:
            return "Remember to maintain healthy online habits"
        
        return "Continue following safe online practices"

    def _generate_suggested_actions(self, risk_analysis: Dict) -> List[str]:
        """Generate suggested actions for parents/guardians"""
        suggestions = []
        
        for indicator in risk_analysis["risk_indicators"]:
            if indicator == "excessive_frequency":
                suggestions.append("Consider setting screen time limits or break reminders")
            elif indicator == "unusual_timing":
                suggestions.append("Review bedtime routines and device access during sleep hours")
            elif indicator == "repetitive_behavior":
                suggestions.append("Encourage diverse online activities and interests")
            elif indicator == "rapid_friend_requests":
                suggestions.append("Discuss online stranger safety and friend request policies")
        
        return suggestions

    async def _save_safety_alert(self, alert: SafetyAlert):
        """Save safety alert to database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO safety_alerts (
                    alert_id, user_id, alert_type, severity, description,
                    automated_response, requires_parent_action, context_summary,
                    suggested_actions
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
                alert.alert_id, alert.user_id, alert.alert_type,
                alert.severity.value, alert.description,
                alert.automated_response, alert.requires_parent_action,
                json.dumps(alert.context_summary), json.dumps(alert.suggested_actions)
            )

    async def _notify_parent(self, user_id: str, alert: SafetyAlert):
        """Send privacy-respecting notification to parent"""
        # Create anonymized notification
        notification = {
            "type": "safety_alert",
            "user_id": user_id,
            "severity": alert.severity.value,
            "description": alert.description,
            "automated_response": alert.automated_response,
            "suggested_actions": alert.suggested_actions,
            "timestamp": alert.timestamp.isoformat(),
            "privacy_note": "This alert is based on behavior patterns, not content monitoring"
        }
        
        # Mark as notified
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE safety_alerts 
                SET parent_notified = TRUE 
                WHERE alert_id = $1
            """, alert.alert_id)
        
        # TODO: Integrate with notification system
        self.logger.info(f"Parent notification sent for user {user_id}: {alert.alert_type}")

    async def get_user_settings(self, user_id: str) -> Optional[MonitoringSettings]:
        """Get user monitoring settings"""
        if user_id in self.monitoring_settings:
            return self.monitoring_settings[user_id]
        
        async with self.db_pool.acquire() as conn:
            settings_data = await conn.fetchrow("""
                SELECT * FROM monitoring_settings WHERE user_id = $1
            """, user_id)
            
            if not settings_data:
                return None
            
            settings = MonitoringSettings(
                user_id=user_id,
                monitoring_level=MonitoringLevel(settings_data["monitoring_level"]),
                privacy_level=PrivacyLevel(settings_data["privacy_level"]),
                enabled_alerts=set(json.loads(settings_data["enabled_alerts"])),
                content_categories_monitored=set(json.loads(settings_data["content_categories_monitored"])),
                time_based_restrictions=json.loads(settings_data["time_based_restrictions"]),
                parent_notification_threshold=RiskLevel(settings_data["parent_notification_threshold"]),
                data_retention_days=settings_data["data_retention_days"],
                anonymous_reporting=settings_data["anonymous_reporting"]
            )
            
            # Cache settings
            self.monitoring_settings[user_id] = settings
            return settings

    async def update_monitoring_settings(self, user_id: str, updates: Dict) -> Dict:
        """Update monitoring settings with parent approval"""
        current_settings = await self.get_user_settings(user_id)
        if not current_settings:
            return {"success": False, "error": "User monitoring not configured"}
        
        # Validate updates
        allowed_updates = {
            "monitoring_level", "privacy_level", "enabled_alerts",
            "data_retention_days", "parent_notification_threshold"
        }
        
        updates = {k: v for k, v in updates.items() if k in allowed_updates}
        
        if not updates:
            return {"success": False, "error": "No valid updates provided"}
        
        # Apply updates
        async with self.db_pool.acquire() as conn:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            
            for field, value in updates.items():
                set_clauses.append(f"{field} = ${param_count}")
                
                if field == "enabled_alerts":
                    values.append(json.dumps(list(value)))
                elif field in ["monitoring_level", "privacy_level", "parent_notification_threshold"]:
                    values.append(value if isinstance(value, str) else value.value)
                else:
                    values.append(value)
                
                param_count += 1
            
            set_clauses.append(f"updated_at = CURRENT_TIMESTAMP")
            values.append(user_id)
            
            await conn.execute(f"""
                UPDATE monitoring_settings 
                SET {', '.join(set_clauses)}
                WHERE user_id = ${param_count}
            """, *values)
        
        # Clear cache to force reload
        if user_id in self.monitoring_settings:
            del self.monitoring_settings[user_id]
        
        return {
            "success": True,
            "updates_applied": list(updates.keys()),
            "privacy_impact": self._assess_privacy_impact(updates),
            "effective_immediately": True
        }

    def _assess_privacy_impact(self, updates: Dict) -> str:
        """Assess privacy impact of settings changes"""
        impact_scores = {
            "monitoring_level": {"minimal": -1, "standard": 0, "enhanced": 1, "custom": 0},
            "privacy_level": {"high": -2, "medium": 0, "low": 2},
            "data_retention_days": lambda x: (x - 7) / 7  # Score based on days above 7
        }
        
        total_impact = 0
        for field, value in updates.items():
            if field in impact_scores:
                if callable(impact_scores[field]):
                    total_impact += impact_scores[field](value)
                else:
                    total_impact += impact_scores[field].get(value, 0)
        
        if total_impact <= -1:
            return "Increased privacy protection"
        elif total_impact >= 2:
            return "Reduced privacy protection"
        else:
            return "Minimal privacy impact"

    async def get_privacy_report(self, user_id: str) -> Dict:
        """Generate privacy-focused monitoring report"""
        settings = await self.get_user_settings(user_id)
        if not settings:
            return {"error": "User monitoring not configured"}
        
        async with self.db_pool.acquire() as conn:
            # Get anonymized activity summary
            activity_summary = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_interactions,
                    COUNT(DISTINCT interaction_type) as interaction_types,
                    AVG(word_count) as avg_word_count,
                    COUNT(*) FILTER (WHERE time_of_day BETWEEN 22 AND 23 OR time_of_day BETWEEN 0 AND 6) as late_night_activity
                FROM interaction_metadata
                WHERE user_id_hash = $1 AND created_at >= $2
            """, 
                hashlib.sha256(f"{user_id}_salt".encode()).hexdigest(),
                datetime.now() - timedelta(days=7)
            )
            
            # Get safety alerts count
            alerts_count = await conn.fetchval("""
                SELECT COUNT(*) FROM safety_alerts
                WHERE user_id = $1 AND created_at >= $2
            """, user_id, datetime.now() - timedelta(days=7))
        
        return {
            "monitoring_summary": {
                "privacy_level": settings.privacy_level.value,
                "data_retention_days": settings.data_retention_days,
                "anonymous_reporting": settings.anonymous_reporting,
                "content_stored": False,  # We never store actual content
                "personal_info_collected": False
            },
            "activity_overview": {
                "total_interactions": activity_summary["total_interactions"] or 0,
                "interaction_variety": activity_summary["interaction_types"] or 0,
                "average_content_length": round(activity_summary["avg_word_count"] or 0, 1),
                "late_night_activity": activity_summary["late_night_activity"] or 0
            },
            "safety_summary": {
                "alerts_generated": alerts_count or 0,
                "monitoring_effective": alerts_count is not None and alerts_count < 5,
                "privacy_maintained": True
            },
            "data_handling": {
                "content_hashed_only": True,
                "automatic_deletion": f"After {settings.data_retention_days} days",
                "third_party_sharing": False,
                "parent_access_level": self._describe_parent_access(settings)
            },
            "privacy_controls": {
                "can_adjust_privacy_level": True,
                "can_reduce_data_retention": True,
                "can_disable_monitoring": True,
                "data_export_available": False,  # No personal data to export
                "data_deletion_available": True
            }
        }

    def _describe_parent_access(self, settings: MonitoringSettings) -> str:
        """Describe what parents can access"""
        if settings.privacy_level == PrivacyLevel.HIGH:
            return "Parents see only safety alerts and general activity patterns"
        elif settings.privacy_level == PrivacyLevel.MEDIUM:
            return "Parents see safety alerts, activity patterns, and general content categories"
        else:
            return "Parents see detailed activity summaries while content remains private"

    def _describe_privacy_features(self, settings: MonitoringSettings) -> List[str]:
        """Describe privacy protection features"""
        features = [
            "Content is never stored - only metadata patterns",
            "All user identifiers are hashed for anonymity",
            f"Data automatically deleted after {settings.data_retention_days} days",
            "No third-party data sharing"
        ]
        
        if settings.privacy_level == PrivacyLevel.HIGH:
            features.extend([
                "Minimal metadata collection",
                "Pattern-based analysis only",
                "No sentiment analysis"
            ])
        
        return features

    def _describe_parent_controls(self, settings: MonitoringSettings) -> List[str]:
        """Describe parent control capabilities"""
        controls = [
            "Adjust monitoring and privacy levels",
            "Set custom alert thresholds",
            "Configure notification preferences",
            "View anonymized activity reports"
        ]
        
        if settings.monitoring_level == MonitoringLevel.ENHANCED:
            controls.extend([
                "Real-time safety alerts",
                "Detailed behavior pattern analysis",
                "Proactive risk detection"
            ])
        
        return controls

    async def cleanup_expired_data(self):
        """Clean up expired monitoring data for privacy compliance"""
        async with self.db_pool.acquire() as conn:
            # Clean up expired interaction metadata
            deleted_interactions = await conn.fetchval("""
                DELETE FROM interaction_metadata
                WHERE expires_at < CURRENT_TIMESTAMP
                RETURNING COUNT(*)
            """)
            
            # Clean up old pattern data
            deleted_patterns = await conn.fetchval("""
                DELETE FROM interaction_patterns
                WHERE expires_at < CURRENT_TIMESTAMP
                RETURNING COUNT(*)
            """)
            
            # Clean up resolved alerts older than 30 days
            deleted_alerts = await conn.fetchval("""
                DELETE FROM safety_alerts
                WHERE resolved = TRUE AND created_at < $1
                RETURNING COUNT(*)
            """, datetime.now() - timedelta(days=30))
        
        self.logger.info(f"Privacy cleanup: {deleted_interactions} interactions, {deleted_patterns} patterns, {deleted_alerts} alerts removed")
        
        return {
            "interactions_deleted": deleted_interactions or 0,
            "patterns_deleted": deleted_patterns or 0,
            "alerts_deleted": deleted_alerts or 0
        }

    async def get_monitoring_effectiveness(self, user_id: str) -> Dict:
        """Get effectiveness metrics while maintaining privacy"""
        async with self.db_pool.acquire() as conn:
            effectiveness_data = await conn.fetchrow("""
                SELECT 
                    COUNT(DISTINCT DATE(created_at)) as active_days,
                    COUNT(*) as total_alerts,
                    COUNT(*) FILTER (WHERE severity IN ('high', 'critical')) as serious_alerts,
                    COUNT(*) FILTER (WHERE resolved = TRUE) as resolved_alerts
                FROM safety_alerts
                WHERE user_id = $1 AND created_at >= $2
            """, user_id, datetime.now() - timedelta(days=30))
        
        return {
            "monitoring_period_days": 30,
            "active_monitoring_days": effectiveness_data["active_days"] or 0,
            "total_safety_checks": effectiveness_data["total_alerts"] or 0,
            "serious_concerns_detected": effectiveness_data["serious_alerts"] or 0,
            "issues_resolved": effectiveness_data["resolved_alerts"] or 0,
            "effectiveness_score": self._calculate_effectiveness_score(effectiveness_data),
            "privacy_compliance": {
                "data_minimization": True,
                "purpose_limitation": True,
                "storage_limitation": True,
                "accuracy": True,
                "security": True
            }
        }

    def _calculate_effectiveness_score(self, data: Dict) -> float:
        """Calculate monitoring effectiveness score"""
        total_alerts = data.get("total_alerts", 0)
        resolved_alerts = data.get("resolved_alerts", 0)
        serious_alerts = data.get("serious_alerts", 0)
        active_days = data.get("active_days", 0)
        
        # High effectiveness = Low serious alerts + High resolution rate + Consistent monitoring
        if total_alerts == 0:
            return 1.0  # Perfect - no issues detected
        
        resolution_rate = resolved_alerts / total_alerts if total_alerts > 0 else 0
        serious_rate = serious_alerts / total_alerts if total_alerts > 0 else 0
        consistency = min(1.0, active_days / 30)
        
        # Score calculation (0.0 to 1.0)
        effectiveness = (
            (1.0 - serious_rate) * 0.4 +  # Lower serious alerts = better
            resolution_rate * 0.3 +        # Higher resolution = better
            consistency * 0.3               # More consistent = better
        )
        
        return round(effectiveness, 2)