"""
Parental Controls System
Comprehensive parental control features for managing child access and safety
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentRating(Enum):
    """Content rating levels"""
    EVERYONE = "everyone"
    EVERYONE_10_PLUS = "everyone_10_plus" 
    TEEN = "teen"
    MATURE = "mature"
    ADULTS_ONLY = "adults_only"


class SafetyLevel(Enum):
    """Safety restriction levels"""
    MINIMAL = "minimal"
    MODERATE = "moderate"
    STRICT = "strict"
    MAXIMUM = "maximum"


class SupervisionLevel(Enum):
    """Level of supervision required"""
    NONE = "none"
    NOTIFICATION = "notification"
    APPROVAL_REQUIRED = "approval_required"
    REAL_TIME_MONITORING = "real_time_monitoring"


@dataclass
class Child:
    """Child user profile with parental controls"""
    child_id: str
    name: str
    date_of_birth: datetime
    parent_ids: List[str]
    age_group: str
    safety_level: SafetyLevel
    content_rating: ContentRating
    supervision_level: SupervisionLevel
    allowed_hours: Dict[str, Dict[str, str]]  # day -> start/end times
    time_limits: Dict[str, int]  # category -> minutes per day
    blocked_categories: List[str]
    allowed_websites: List[str]
    blocked_websites: List[str]
    allowed_applications: List[str]
    blocked_applications: List[str]
    emergency_contacts: List[str]
    location_restrictions: List[str]
    requires_approval_for: List[str]
    is_active: bool
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class ParentalRule:
    """Individual parental control rule"""
    rule_id: str
    child_id: str
    parent_id: str
    rule_type: str
    rule_name: str
    conditions: Dict[str, Any]
    restrictions: Dict[str, Any]
    exceptions: List[Dict[str, Any]]
    is_active: bool
    priority: int
    created_at: datetime
    last_modified: datetime
    metadata: Dict[str, Any]


@dataclass
class ActivityLog:
    """Child activity log entry"""
    log_id: str
    child_id: str
    activity_type: str
    resource_accessed: str
    timestamp: datetime
    duration: int  # seconds
    was_blocked: bool
    block_reason: Optional[str]
    parent_notified: bool
    location: Optional[str]
    device_id: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class ApprovalRequest:
    """Request for parental approval"""
    request_id: str
    child_id: str
    requested_resource: str
    request_type: str
    justification: str
    requested_at: datetime
    expires_at: datetime
    status: str  # pending, approved, denied, expired
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_comment: Optional[str]
    metadata: Dict[str, Any]


class ParentalControlsManager:
    """Comprehensive parental controls management system"""
    
    def __init__(self, data_dir: str = "parental_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self.children: Dict[str, Child] = {}
        self.parental_rules: Dict[str, ParentalRule] = {}
        self.activity_logs: List[ActivityLog] = []
        self.approval_requests: Dict[str, ApprovalRequest] = {}
        
        # Content filtering databases
        self.content_categories = {
            "educational": {"allowed_ages": [0, 100], "rating": ContentRating.EVERYONE},
            "games": {"allowed_ages": [6, 100], "rating": ContentRating.EVERYONE},
            "social_media": {"allowed_ages": [13, 100], "rating": ContentRating.TEEN},
            "video_streaming": {"allowed_ages": [8, 100], "rating": ContentRating.EVERYONE_10_PLUS},
            "news": {"allowed_ages": [10, 100], "rating": ContentRating.EVERYONE_10_PLUS},
            "shopping": {"allowed_ages": [16, 100], "rating": ContentRating.TEEN},
            "adult_content": {"allowed_ages": [18, 100], "rating": ContentRating.ADULTS_ONLY},
            "violence": {"allowed_ages": [17, 100], "rating": ContentRating.MATURE},
            "gambling": {"allowed_ages": [21, 100], "rating": ContentRating.ADULTS_ONLY}
        }
        
        # Predefined blocked domains for children
        self.blocked_domains = [
            "adult-content.com",
            "gambling-site.com",
            "violent-games.net",
            "inappropriate-content.org"
        ]
        
        # Safe domains that are generally appropriate for children
        self.safe_domains = [
            "education.gov",
            "pbskids.org",
            "nationalgeographic.kids",
            "kidshealth.org",
            "scholastic.com",
            "funbrain.com"
        ]
        
        # Time tracking
        self.daily_usage: Dict[str, Dict[str, int]] = {}  # child_id -> category -> minutes_used
        
        logger.info("ParentalControlsManager initialized")
    
    async def create_child_profile(
        self,
        name: str,
        date_of_birth: datetime,
        parent_ids: List[str],
        safety_level: SafetyLevel = SafetyLevel.MODERATE
    ) -> str:
        """Create a new child profile with appropriate default settings"""
        try:
            child_id = f"child_{uuid.uuid4().hex[:12]}"
            
            # Calculate age and determine appropriate settings
            age = self._calculate_age(date_of_birth)
            age_group = self._determine_age_group(age)
            content_rating = self._determine_content_rating(age)
            default_time_limits = self._get_default_time_limits(age_group)
            default_allowed_hours = self._get_default_allowed_hours(age_group)
            
            child = Child(
                child_id=child_id,
                name=name,
                date_of_birth=date_of_birth,
                parent_ids=parent_ids,
                age_group=age_group,
                safety_level=safety_level,
                content_rating=content_rating,
                supervision_level=SupervisionLevel.NOTIFICATION if age >= 13 else SupervisionLevel.APPROVAL_REQUIRED,
                allowed_hours=default_allowed_hours,
                time_limits=default_time_limits,
                blocked_categories=self._get_blocked_categories_for_age(age),
                allowed_websites=self.safe_domains.copy(),
                blocked_websites=self.blocked_domains.copy(),
                allowed_applications=[],
                blocked_applications=[],
                emergency_contacts=parent_ids.copy(),
                location_restrictions=[],
                requires_approval_for=self._get_approval_requirements(age),
                is_active=True,
                created_at=datetime.now(timezone.utc),
                metadata={"age": age}
            )
            
            self.children[child_id] = child
            
            # Initialize daily usage tracking
            self.daily_usage[child_id] = {category: 0 for category in self.content_categories.keys()}
            
            await self.save_data()
            
            logger.info(f"Created child profile {child_id} for {name} (age {age})")
            return child_id
            
        except Exception as e:
            logger.error(f"Error creating child profile: {e}")
            raise
    
    def _calculate_age(self, date_of_birth: datetime) -> int:
        """Calculate current age from date of birth"""
        today = datetime.now(timezone.utc)
        return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    
    def _determine_age_group(self, age: int) -> str:
        """Determine age group category"""
        if age < 6:
            return "preschool"
        elif age < 13:
            return "elementary"
        elif age < 18:
            return "teen"
        else:
            return "adult"
    
    def _determine_content_rating(self, age: int) -> ContentRating:
        """Determine appropriate content rating based on age"""
        if age < 10:
            return ContentRating.EVERYONE
        elif age < 13:
            return ContentRating.EVERYONE_10_PLUS
        elif age < 17:
            return ContentRating.TEEN
        elif age < 18:
            return ContentRating.MATURE
        else:
            return ContentRating.ADULTS_ONLY
    
    def _get_default_time_limits(self, age_group: str) -> Dict[str, int]:
        """Get default daily time limits by age group (in minutes)"""
        limits = {
            "preschool": {
                "educational": 60,
                "games": 30,
                "video_streaming": 45,
                "total_screen_time": 120
            },
            "elementary": {
                "educational": 120,
                "games": 60,
                "video_streaming": 90,
                "social_media": 0,  # Not allowed
                "total_screen_time": 180
            },
            "teen": {
                "educational": 180,
                "games": 120,
                "video_streaming": 120,
                "social_media": 60,
                "total_screen_time": 300
            },
            "adult": {
                "total_screen_time": 0  # No limits
            }
        }
        return limits.get(age_group, limits["teen"])
    
    def _get_default_allowed_hours(self, age_group: str) -> Dict[str, Dict[str, str]]:
        """Get default allowed hours by age group"""
        schedules = {
            "preschool": {
                "monday": {"start": "09:00", "end": "18:00"},
                "tuesday": {"start": "09:00", "end": "18:00"},
                "wednesday": {"start": "09:00", "end": "18:00"},
                "thursday": {"start": "09:00", "end": "18:00"},
                "friday": {"start": "09:00", "end": "18:00"},
                "saturday": {"start": "08:00", "end": "19:00"},
                "sunday": {"start": "08:00", "end": "19:00"}
            },
            "elementary": {
                "monday": {"start": "07:00", "end": "20:00"},
                "tuesday": {"start": "07:00", "end": "20:00"},
                "wednesday": {"start": "07:00", "end": "20:00"},
                "thursday": {"start": "07:00", "end": "20:00"},
                "friday": {"start": "07:00", "end": "21:00"},
                "saturday": {"start": "07:00", "end": "21:00"},
                "sunday": {"start": "07:00", "end": "20:00"}
            },
            "teen": {
                "monday": {"start": "06:00", "end": "21:00"},
                "tuesday": {"start": "06:00", "end": "21:00"},
                "wednesday": {"start": "06:00", "end": "21:00"},
                "thursday": {"start": "06:00", "end": "21:00"},
                "friday": {"start": "06:00", "end": "22:00"},
                "saturday": {"start": "07:00", "end": "23:00"},
                "sunday": {"start": "07:00", "end": "21:00"}
            },
            "adult": {}  # No restrictions
        }
        return schedules.get(age_group, schedules["teen"])
    
    def _get_blocked_categories_for_age(self, age: int) -> List[str]:
        """Get categories that should be blocked for the given age"""
        blocked = []
        for category, info in self.content_categories.items():
            min_age, max_age = info["allowed_ages"]
            if age < min_age or age > max_age:
                blocked.append(category)
        return blocked
    
    def _get_approval_requirements(self, age: int) -> List[str]:
        """Get activities that require parental approval based on age"""
        if age < 10:
            return ["all_internet", "app_downloads", "social_contact", "purchases"]
        elif age < 13:
            return ["social_media", "app_downloads", "purchases", "location_sharing"]
        elif age < 16:
            return ["app_downloads", "purchases", "mature_content"]
        else:
            return ["purchases"]
    
    async def check_access_permission(
        self,
        child_id: str,
        resource: str,
        resource_type: str,
        device_id: Optional[str] = None,
        location: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Check if child has permission to access a resource"""
        try:
            child = self.children.get(child_id)
            if not child or not child.is_active:
                return False, "Child profile not found or inactive"
            
            current_time = datetime.now(timezone.utc)
            
            # Check time restrictions
            time_allowed, time_reason = await self._check_time_restrictions(child, current_time)
            if not time_allowed:
                return False, time_reason
            
            # Check daily time limits
            limit_ok, limit_reason = await self._check_daily_limits(child, resource_type)
            if not limit_ok:
                return False, limit_reason
            
            # Check content filtering
            content_ok, content_reason = await self._check_content_filtering(child, resource, resource_type)
            if not content_ok:
                return False, content_reason
            
            # Check location restrictions
            if location and child.location_restrictions:
                if location not in child.location_restrictions:
                    return False, f"Access not allowed from location: {location}"
            
            # Check if approval is required
            if await self._requires_approval(child, resource, resource_type):
                # Create approval request
                request_id = await self.create_approval_request(
                    child_id, resource, resource_type, "Child requested access"
                )
                return False, f"Parental approval required. Request ID: {request_id}"
            
            # Log the access attempt
            await self._log_activity(
                child_id, resource_type, resource, 0, False, None, device_id, location
            )
            
            return True, "Access granted"
            
        except Exception as e:
            logger.error(f"Error checking access permission: {e}")
            return False, f"Permission check failed: {str(e)}"
    
    async def _check_time_restrictions(
        self,
        child: Child,
        current_time: datetime
    ) -> Tuple[bool, str]:
        """Check if current time falls within allowed hours"""
        try:
            current_day = current_time.strftime("%A").lower()
            current_time_only = current_time.time()
            
            if current_day not in child.allowed_hours:
                return True, "No time restrictions for this day"
            
            day_schedule = child.allowed_hours[current_day]
            start_time = datetime.strptime(day_schedule["start"], "%H:%M").time()
            end_time = datetime.strptime(day_schedule["end"], "%H:%M").time()
            
            if start_time <= current_time_only <= end_time:
                return True, "Within allowed hours"
            else:
                return False, f"Outside allowed hours ({day_schedule['start']}-{day_schedule['end']})"
                
        except Exception as e:
            logger.error(f"Error checking time restrictions: {e}")
            return True, "Time check failed, allowing access"
    
    async def _check_daily_limits(
        self,
        child: Child,
        resource_type: str
    ) -> Tuple[bool, str]:
        """Check if daily usage limits have been exceeded"""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            child_usage = self.daily_usage.get(child.child_id, {})
            
            # Check category-specific limit
            if resource_type in child.time_limits:
                limit = child.time_limits[resource_type]
                used = child_usage.get(f"{resource_type}_{today}", 0)
                
                if used >= limit:
                    return False, f"Daily limit exceeded for {resource_type} ({used}/{limit} minutes)"
            
            # Check total screen time limit
            if "total_screen_time" in child.time_limits:
                total_limit = child.time_limits["total_screen_time"]
                total_used = sum(
                    time for key, time in child_usage.items() 
                    if key.endswith(today) and key != f"total_screen_time_{today}"
                )
                
                if total_used >= total_limit:
                    return False, f"Daily screen time limit exceeded ({total_used}/{total_limit} minutes)"
            
            return True, "Within daily limits"
            
        except Exception as e:
            logger.error(f"Error checking daily limits: {e}")
            return True, "Limit check failed, allowing access"
    
    async def _check_content_filtering(
        self,
        child: Child,
        resource: str,
        resource_type: str
    ) -> Tuple[bool, str]:
        """Check content filtering rules"""
        try:
            # Check blocked categories
            if resource_type in child.blocked_categories:
                return False, f"Category '{resource_type}' is blocked"
            
            # Check content rating
            category_info = self.content_categories.get(resource_type)
            if category_info:
                required_rating = category_info["rating"]
                child_age = self._calculate_age(child.date_of_birth)
                
                # Define minimum ages for content ratings
                rating_ages = {
                    ContentRating.EVERYONE: 0,
                    ContentRating.EVERYONE_10_PLUS: 10,
                    ContentRating.TEEN: 13,
                    ContentRating.MATURE: 17,
                    ContentRating.ADULTS_ONLY: 18
                }
                
                required_age = rating_ages.get(required_rating, 18)
                if child_age < required_age:
                    return False, f"Content rating {required_rating.value} requires age {required_age}+"
            
            # Check website filtering
            if resource_type == "website":
                # Extract domain from URL
                domain = self._extract_domain(resource)
                
                # Check blocked websites
                if domain in child.blocked_websites:
                    return False, f"Website '{domain}' is blocked"
                
                # If allowed websites list is not empty, check if domain is in it
                if child.allowed_websites and domain not in child.allowed_websites:
                    # Check if it's in safe domains
                    if domain not in self.safe_domains:
                        return False, f"Website '{domain}' is not in allowed list"
            
            # Check application filtering
            if resource_type == "application":
                if resource in child.blocked_applications:
                    return False, f"Application '{resource}' is blocked"
                
                if child.allowed_applications and resource not in child.allowed_applications:
                    return False, f"Application '{resource}' is not in allowed list"
            
            return True, "Content filtering passed"
            
        except Exception as e:
            logger.error(f"Error checking content filtering: {e}")
            return True, "Content filtering failed, allowing access"
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        # Simple domain extraction
        if url.startswith(("http://", "https://")):
            url = url.split("://", 1)[1]
        return url.split("/")[0].split(":")[0].lower()
    
    async def _requires_approval(
        self,
        child: Child,
        resource: str,
        resource_type: str
    ) -> bool:
        """Check if the resource requires parental approval"""
        
        # Check supervision level
        if child.supervision_level == SupervisionLevel.APPROVAL_REQUIRED:
            return True
        
        # Check specific approval requirements
        for requirement in child.requires_approval_for:
            if (requirement == "all_internet" and resource_type in ["website", "social_media"]) or \
               (requirement == resource_type) or \
               (requirement in resource.lower()):
                return True
        
        return False
    
    async def create_approval_request(
        self,
        child_id: str,
        requested_resource: str,
        request_type: str,
        justification: str
    ) -> str:
        """Create a new approval request"""
        try:
            request_id = f"approval_{uuid.uuid4().hex[:12]}"
            
            # Set expiration (24 hours for most requests)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            if request_type in ["emergency", "urgent"]:
                expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
            
            request = ApprovalRequest(
                request_id=request_id,
                child_id=child_id,
                requested_resource=requested_resource,
                request_type=request_type,
                justification=justification,
                requested_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                status="pending",
                reviewed_by=None,
                reviewed_at=None,
                review_comment=None,
                metadata={}
            )
            
            self.approval_requests[request_id] = request
            
            # Notify parents
            child = self.children.get(child_id)
            if child:
                await self._notify_parents(child.parent_ids, request)
            
            await self.save_data()
            
            logger.info(f"Created approval request {request_id} for child {child_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"Error creating approval request: {e}")
            raise
    
    async def _notify_parents(
        self,
        parent_ids: List[str],
        request: ApprovalRequest
    ):
        """Notify parents of approval request"""
        logger.info(f"Notifying parents {parent_ids} of approval request {request.request_id}")
        # In a real system, this would send push notifications, emails, or SMS
    
    async def approve_request(
        self,
        request_id: str,
        parent_id: str,
        comment: str = ""
    ) -> bool:
        """Approve a child's request"""
        try:
            request = self.approval_requests.get(request_id)
            if not request:
                return False
            
            if request.status != "pending":
                return False
            
            # Verify parent has authority over this child
            child = self.children.get(request.child_id)
            if not child or parent_id not in child.parent_ids:
                return False
            
            request.status = "approved"
            request.reviewed_by = parent_id
            request.reviewed_at = datetime.now(timezone.utc)
            request.review_comment = comment
            
            await self.save_data()
            
            logger.info(f"Approved request {request_id} by parent {parent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error approving request: {e}")
            return False
    
    async def deny_request(
        self,
        request_id: str,
        parent_id: str,
        reason: str
    ) -> bool:
        """Deny a child's request"""
        try:
            request = self.approval_requests.get(request_id)
            if not request:
                return False
            
            if request.status != "pending":
                return False
            
            # Verify parent has authority over this child
            child = self.children.get(request.child_id)
            if not child or parent_id not in child.parent_ids:
                return False
            
            request.status = "denied"
            request.reviewed_by = parent_id
            request.reviewed_at = datetime.now(timezone.utc)
            request.review_comment = reason
            
            await self.save_data()
            
            logger.info(f"Denied request {request_id} by parent {parent_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error denying request: {e}")
            return False
    
    async def _log_activity(
        self,
        child_id: str,
        activity_type: str,
        resource: str,
        duration: int,
        was_blocked: bool,
        block_reason: Optional[str] = None,
        device_id: Optional[str] = None,
        location: Optional[str] = None
    ):
        """Log child activity"""
        try:
            log_id = f"log_{uuid.uuid4().hex[:12]}"
            
            activity = ActivityLog(
                log_id=log_id,
                child_id=child_id,
                activity_type=activity_type,
                resource_accessed=resource,
                timestamp=datetime.now(timezone.utc),
                duration=duration,
                was_blocked=was_blocked,
                block_reason=block_reason,
                parent_notified=False,  # Will be updated if notification is sent
                location=location,
                device_id=device_id,
                metadata={}
            )
            
            self.activity_logs.append(activity)
            
            # Update usage tracking if not blocked
            if not was_blocked and duration > 0:
                await self._update_usage_tracking(child_id, activity_type, duration)
            
            # Check if parents should be notified
            child = self.children.get(child_id)
            if child and child.supervision_level in [SupervisionLevel.NOTIFICATION, SupervisionLevel.REAL_TIME_MONITORING]:
                if was_blocked or activity_type in child.requires_approval_for:
                    await self._notify_parents_of_activity(child.parent_ids, activity)
                    activity.parent_notified = True
            
            # Trim old logs to prevent memory issues
            if len(self.activity_logs) > 10000:
                self.activity_logs = self.activity_logs[-5000:]
            
        except Exception as e:
            logger.error(f"Error logging activity: {e}")
    
    async def _update_usage_tracking(
        self,
        child_id: str,
        activity_type: str,
        duration_seconds: int
    ):
        """Update daily usage tracking"""
        try:
            today = datetime.now(timezone.utc).date().isoformat()
            minutes = duration_seconds // 60
            
            if child_id not in self.daily_usage:
                self.daily_usage[child_id] = {}
            
            usage_key = f"{activity_type}_{today}"
            self.daily_usage[child_id][usage_key] = self.daily_usage[child_id].get(usage_key, 0) + minutes
            
            # Update total screen time
            total_key = f"total_screen_time_{today}"
            self.daily_usage[child_id][total_key] = self.daily_usage[child_id].get(total_key, 0) + minutes
            
        except Exception as e:
            logger.error(f"Error updating usage tracking: {e}")
    
    async def _notify_parents_of_activity(
        self,
        parent_ids: List[str],
        activity: ActivityLog
    ):
        """Notify parents of child activity"""
        logger.info(f"Notifying parents {parent_ids} of activity: {activity.activity_type} - {activity.resource_accessed}")
    
    async def get_child_activity_report(
        self,
        child_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Generate activity report for a child"""
        try:
            child = self.children.get(child_id)
            if not child:
                return {}
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Filter activities for this child and time period
            child_activities = [
                log for log in self.activity_logs
                if log.child_id == child_id and log.timestamp >= cutoff_date
            ]
            
            # Calculate statistics
            total_activities = len(child_activities)
            blocked_activities = sum(1 for log in child_activities if log.was_blocked)
            total_screen_time = sum(log.duration for log in child_activities if not log.was_blocked) // 60  # minutes
            
            # Activities by type
            activity_breakdown = {}
            for log in child_activities:
                activity_type = log.activity_type
                if activity_type not in activity_breakdown:
                    activity_breakdown[activity_type] = {"count": 0, "duration": 0, "blocked": 0}
                
                activity_breakdown[activity_type]["count"] += 1
                if not log.was_blocked:
                    activity_breakdown[activity_type]["duration"] += log.duration // 60
                else:
                    activity_breakdown[activity_type]["blocked"] += 1
            
            # Most visited resources
            resource_counts = {}
            for log in child_activities:
                if not log.was_blocked:
                    resource_counts[log.resource_accessed] = resource_counts.get(log.resource_accessed, 0) + 1
            
            top_resources = sorted(resource_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "child_name": child.name,
                "report_period": f"Last {days} days",
                "summary": {
                    "total_activities": total_activities,
                    "blocked_activities": blocked_activities,
                    "total_screen_time_minutes": total_screen_time,
                    "average_daily_screen_time": total_screen_time // days
                },
                "activity_breakdown": activity_breakdown,
                "top_resources": top_resources,
                "current_restrictions": {
                    "safety_level": child.safety_level.value,
                    "content_rating": child.content_rating.value,
                    "supervision_level": child.supervision_level.value,
                    "blocked_categories": child.blocked_categories
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating activity report: {e}")
            return {}
    
    async def update_child_settings(
        self,
        child_id: str,
        parent_id: str,
        settings: Dict[str, Any]
    ) -> bool:
        """Update child's parental control settings"""
        try:
            child = self.children.get(child_id)
            if not child or parent_id not in child.parent_ids:
                return False
            
            # Update allowed settings
            allowed_updates = [
                "safety_level", "content_rating", "supervision_level",
                "time_limits", "allowed_hours", "blocked_categories",
                "allowed_websites", "blocked_websites",
                "allowed_applications", "blocked_applications",
                "requires_approval_for"
            ]
            
            for key, value in settings.items():
                if key in allowed_updates:
                    if key in ["safety_level", "content_rating", "supervision_level"]:
                        # Convert string values to enums
                        enum_map = {
                            "safety_level": SafetyLevel,
                            "content_rating": ContentRating,
                            "supervision_level": SupervisionLevel
                        }
                        setattr(child, key, enum_map[key](value))
                    else:
                        setattr(child, key, value)
            
            await self.save_data()
            
            logger.info(f"Updated settings for child {child_id} by parent {parent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating child settings: {e}")
            return False
    
    async def load_data(self):
        """Load parental controls data from disk"""
        try:
            # Load children profiles
            children_file = self.data_dir / "children.json"
            if children_file.exists():
                with open(children_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item["date_of_birth"] = datetime.fromisoformat(item["date_of_birth"])
                        item["created_at"] = datetime.fromisoformat(item["created_at"])
                        item["safety_level"] = SafetyLevel(item["safety_level"])
                        item["content_rating"] = ContentRating(item["content_rating"])
                        item["supervision_level"] = SupervisionLevel(item["supervision_level"])
                        
                        child = Child(**item)
                        self.children[child.child_id] = child
            
            # Load activity logs
            logs_file = self.data_dir / "activity_logs.json"
            if logs_file.exists():
                with open(logs_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                        log = ActivityLog(**item)
                        self.activity_logs.append(log)
            
            # Load approval requests
            requests_file = self.data_dir / "approval_requests.json"
            if requests_file.exists():
                with open(requests_file, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        item["requested_at"] = datetime.fromisoformat(item["requested_at"])
                        item["expires_at"] = datetime.fromisoformat(item["expires_at"])
                        if item["reviewed_at"]:
                            item["reviewed_at"] = datetime.fromisoformat(item["reviewed_at"])
                        
                        request = ApprovalRequest(**item)
                        self.approval_requests[request.request_id] = request
            
            # Load usage tracking
            usage_file = self.data_dir / "daily_usage.json"
            if usage_file.exists():
                with open(usage_file, 'r') as f:
                    self.daily_usage = json.load(f)
            
            logger.info("Loaded parental controls data from disk")
            
        except Exception as e:
            logger.error(f"Error loading parental controls data: {e}")
    
    async def save_data(self):
        """Save parental controls data to disk"""
        try:
            # Save children profiles
            children_file = self.data_dir / "children.json"
            with open(children_file, 'w') as f:
                data = []
                for child in self.children.values():
                    item = asdict(child)
                    item["date_of_birth"] = child.date_of_birth.isoformat()
                    item["created_at"] = child.created_at.isoformat()
                    item["safety_level"] = child.safety_level.value
                    item["content_rating"] = child.content_rating.value
                    item["supervision_level"] = child.supervision_level.value
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            # Save activity logs (only recent ones to prevent file from getting too large)
            logs_file = self.data_dir / "activity_logs.json"
            with open(logs_file, 'w') as f:
                # Only save last 1000 logs
                recent_logs = self.activity_logs[-1000:]
                data = []
                for log in recent_logs:
                    item = asdict(log)
                    item["timestamp"] = log.timestamp.isoformat()
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            # Save approval requests
            requests_file = self.data_dir / "approval_requests.json"
            with open(requests_file, 'w') as f:
                data = []
                for request in self.approval_requests.values():
                    item = asdict(request)
                    item["requested_at"] = request.requested_at.isoformat()
                    item["expires_at"] = request.expires_at.isoformat()
                    if request.reviewed_at:
                        item["reviewed_at"] = request.reviewed_at.isoformat()
                    data.append(item)
                
                json.dump(data, f, indent=2)
            
            # Save usage tracking
            usage_file = self.data_dir / "daily_usage.json"
            with open(usage_file, 'w') as f:
                json.dump(self.daily_usage, f, indent=2)
            
            logger.info("Saved parental controls data to disk")
            
        except Exception as e:
            logger.error(f"Error saving parental controls data: {e}")