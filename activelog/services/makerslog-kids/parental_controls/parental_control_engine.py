#!/usr/bin/env python3
"""
Parental Control Engine for MakersLog Kids
Comprehensive parental control system with compute limits, purchase controls, and safety features
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PermissionType(Enum):
    COMPUTE_QUOTA = "compute_quota"
    PURCHASE = "purchase"
    PROJECT_SHARE = "project_share"
    FRIEND_ADD = "friend_add"
    CONTENT_ACCESS = "content_access"
    EXTENDED_TIME = "extended_time"

class PermissionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"

class AgeGroup(Enum):
    PRESCHOOL = "preschool"  # 3-5 years
    EARLY_ELEMENTARY = "early_elementary"  # 6-8 years
    LATE_ELEMENTARY = "late_elementary"  # 9-11 years
    MIDDLE_SCHOOL = "middle_school"  # 12-14 years
    HIGH_SCHOOL = "high_school"  # 15-17 years

class RestrictionLevel(Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    RELAXED = "relaxed"

@dataclass
class ComputeLimit:
    """Compute usage limits"""
    daily_cpu_minutes: int
    daily_memory_mb: int
    daily_storage_mb: int
    max_concurrent_projects: int
    max_project_runtime_minutes: int

@dataclass
class PurchaseLimit:
    """Purchase limits and controls"""
    daily_limit: float
    weekly_limit: float
    monthly_limit: float
    single_purchase_limit: float
    requires_approval_above: float
    allowed_categories: List[str]
    blocked_categories: List[str]

@dataclass
class TimeRestriction:
    """Time-based restrictions"""
    allowed_hours_start: time
    allowed_hours_end: time
    max_daily_minutes: int
    allowed_days: List[str]  # ["monday", "tuesday", etc.]
    break_required_after_minutes: int
    min_break_duration_minutes: int

@dataclass
class ContentFilter:
    """Content filtering settings"""
    age_group: AgeGroup
    restriction_level: RestrictionLevel
    blocked_keywords: List[str]
    allowed_domains: List[str]
    blocked_domains: List[str]
    enable_safe_search: bool
    enable_profanity_filter: bool

@dataclass
class ChildProfile:
    """Child user profile with parental controls"""
    child_id: str
    parent_id: str
    name: str
    age: int
    age_group: AgeGroup
    compute_limits: ComputeLimit
    purchase_limits: PurchaseLimit
    time_restrictions: TimeRestriction
    content_filter: ContentFilter
    is_active: bool = True
    created_at: Optional[datetime] = None

@dataclass
class PermissionRequest:
    """Permission request from child to parent"""
    request_id: str
    child_id: str
    parent_id: str
    permission_type: PermissionType
    request_data: Dict[str, Any]
    reason: str
    status: PermissionStatus
    requested_at: datetime
    expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    response_reason: Optional[str] = None

class ParentalControlEngine:
    """Main parental control engine"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        
        # Default limits by age group
        self.default_compute_limits = {
            AgeGroup.PRESCHOOL: ComputeLimit(30, 256, 100, 1, 15),
            AgeGroup.EARLY_ELEMENTARY: ComputeLimit(60, 512, 250, 2, 30),
            AgeGroup.LATE_ELEMENTARY: ComputeLimit(120, 1024, 500, 3, 60),
            AgeGroup.MIDDLE_SCHOOL: ComputeLimit(180, 2048, 1000, 4, 90),
            AgeGroup.HIGH_SCHOOL: ComputeLimit(240, 4096, 2000, 5, 120)
        }
        
        self.default_purchase_limits = {
            AgeGroup.PRESCHOOL: PurchaseLimit(0, 0, 0, 0, 0, [], ["all"]),
            AgeGroup.EARLY_ELEMENTARY: PurchaseLimit(5, 20, 50, 5, 1, ["educational"], ["games", "entertainment"]),
            AgeGroup.LATE_ELEMENTARY: PurchaseLimit(10, 40, 100, 10, 5, ["educational", "tools"], ["games"]),
            AgeGroup.MIDDLE_SCHOOL: PurchaseLimit(20, 80, 200, 20, 10, ["educational", "tools", "games"], []),
            AgeGroup.HIGH_SCHOOL: PurchaseLimit(50, 200, 500, 50, 25, ["educational", "tools", "games"], [])
        }
        
        self.default_time_restrictions = {
            AgeGroup.PRESCHOOL: TimeRestriction(time(9, 0), time(17, 0), 30, ["monday", "tuesday", "wednesday", "thursday", "friday"], 15, 10),
            AgeGroup.EARLY_ELEMENTARY: TimeRestriction(time(8, 0), time(19, 0), 60, ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"], 30, 15),
            AgeGroup.LATE_ELEMENTARY: TimeRestriction(time(7, 0), time(20, 0), 90, ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], 45, 15),
            AgeGroup.MIDDLE_SCHOOL: TimeRestriction(time(6, 0), time(21, 0), 120, ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], 60, 20),
            AgeGroup.HIGH_SCHOOL: TimeRestriction(time(6, 0), time(22, 0), 180, ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"], 90, 20)
        }
    
    async def create_child_profile(self, parent_id: str, child_data: Dict[str, Any]) -> str:
        """Create a new child profile with parental controls"""
        child_id = str(uuid.uuid4())
        age = child_data['age']
        age_group = self._determine_age_group(age)
        
        # Get default limits for age group
        compute_limits = child_data.get('compute_limits', self.default_compute_limits[age_group])
        purchase_limits = child_data.get('purchase_limits', self.default_purchase_limits[age_group])
        time_restrictions = child_data.get('time_restrictions', self.default_time_restrictions[age_group])
        
        # Create content filter
        content_filter = ContentFilter(
            age_group=age_group,
            restriction_level=RestrictionLevel(child_data.get('restriction_level', 'moderate')),
            blocked_keywords=child_data.get('blocked_keywords', []),
            allowed_domains=child_data.get('allowed_domains', []),
            blocked_domains=child_data.get('blocked_domains', []),
            enable_safe_search=child_data.get('enable_safe_search', True),
            enable_profanity_filter=child_data.get('enable_profanity_filter', True)
        )
        
        child_profile = ChildProfile(
            child_id=child_id,
            parent_id=parent_id,
            name=child_data['name'],
            age=age,
            age_group=age_group,
            compute_limits=compute_limits,
            purchase_limits=purchase_limits,
            time_restrictions=time_restrictions,
            content_filter=content_filter,
            created_at=datetime.now()
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO child_profiles 
                (child_id, parent_id, name, age, age_group, compute_limits, 
                 purchase_limits, time_restrictions, content_filter, is_active, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            ''',
            child_id, parent_id, child_data['name'], age, age_group.value,
            json.dumps(asdict(compute_limits)), json.dumps(asdict(purchase_limits)),
            json.dumps(asdict(time_restrictions)), json.dumps(asdict(content_filter)),
            True, datetime.now()
            )
        
        logger.info(f"Created child profile {child_id} for parent {parent_id}")
        return child_id
    
    def _determine_age_group(self, age: int) -> AgeGroup:
        """Determine age group based on age"""
        if age <= 5:
            return AgeGroup.PRESCHOOL
        elif age <= 8:
            return AgeGroup.EARLY_ELEMENTARY
        elif age <= 11:
            return AgeGroup.LATE_ELEMENTARY
        elif age <= 14:
            return AgeGroup.MIDDLE_SCHOOL
        else:
            return AgeGroup.HIGH_SCHOOL
    
    async def get_child_profile(self, child_id: str) -> Optional[ChildProfile]:
        """Get child profile by ID"""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM child_profiles WHERE child_id = $1
            ''', child_id)
            
            if not row:
                return None
            
            return ChildProfile(
                child_id=row['child_id'],
                parent_id=row['parent_id'],
                name=row['name'],
                age=row['age'],
                age_group=AgeGroup(row['age_group']),
                compute_limits=ComputeLimit(**json.loads(row['compute_limits'])),
                purchase_limits=PurchaseLimit(**json.loads(row['purchase_limits'])),
                time_restrictions=TimeRestriction(
                    **{k: time.fromisoformat(v) if k.endswith('_start') or k.endswith('_end') else v 
                       for k, v in json.loads(row['time_restrictions']).items()}
                ),
                content_filter=ContentFilter(**{
                    **json.loads(row['content_filter']),
                    'age_group': AgeGroup(json.loads(row['content_filter'])['age_group']),
                    'restriction_level': RestrictionLevel(json.loads(row['content_filter'])['restriction_level'])
                }),
                is_active=row['is_active'],
                created_at=row['created_at']
            )
    
    async def update_child_profile(self, child_id: str, updates: Dict[str, Any]) -> bool:
        """Update child profile settings"""
        try:
            async with self.db_pool.acquire() as conn:
                # Build dynamic update query
                set_clauses = []
                values = []
                value_index = 1
                
                for field, value in updates.items():
                    if field in ['compute_limits', 'purchase_limits', 'time_restrictions', 'content_filter']:
                        value = json.dumps(asdict(value) if hasattr(value, '__dict__') else value)
                    
                    set_clauses.append(f"{field} = ${value_index}")
                    values.append(value)
                    value_index += 1
                
                set_clauses.append(f"updated_at = ${value_index}")
                values.append(datetime.now())
                values.append(child_id)
                
                query = f"""
                    UPDATE child_profiles 
                    SET {', '.join(set_clauses)}
                    WHERE child_id = ${value_index + 1}
                """
                
                result = await conn.execute(query, *values)
                return result != 'UPDATE 0'
                
        except Exception as e:
            logger.error(f"Failed to update child profile {child_id}: {e}")
            return False
    
    # Compute Usage Tracking and Limits
    
    async def check_compute_limit(self, child_id: str, resource_type: str, 
                                amount: int) -> Tuple[bool, str]:
        """Check if compute usage is within limits"""
        profile = await self.get_child_profile(child_id)
        if not profile:
            return False, "Child profile not found"
        
        # Get today's usage
        today_usage = await self._get_daily_compute_usage(child_id)
        
        limits = profile.compute_limits
        
        if resource_type == 'cpu_minutes':
            if today_usage.get('cpu_minutes', 0) + amount > limits.daily_cpu_minutes:
                return False, f"Daily CPU limit exceeded ({limits.daily_cpu_minutes} minutes)"
        
        elif resource_type == 'memory_mb':
            if today_usage.get('memory_mb', 0) + amount > limits.daily_memory_mb:
                return False, f"Daily memory limit exceeded ({limits.daily_memory_mb} MB)"
        
        elif resource_type == 'storage_mb':
            if today_usage.get('storage_mb', 0) + amount > limits.daily_storage_mb:
                return False, f"Daily storage limit exceeded ({limits.daily_storage_mb} MB)"
        
        elif resource_type == 'concurrent_projects':
            active_projects = await self._get_active_project_count(child_id)
            if active_projects >= limits.max_concurrent_projects:
                return False, f"Maximum concurrent projects limit reached ({limits.max_concurrent_projects})"
        
        return True, "Within limits"
    
    async def _get_daily_compute_usage(self, child_id: str) -> Dict[str, int]:
        """Get today's compute usage for a child"""
        today = datetime.now().date()
        
        async with self.db_pool.acquire() as conn:
            usage = await conn.fetchrow('''
                SELECT 
                    COALESCE(SUM(cpu_minutes), 0) as cpu_minutes,
                    COALESCE(SUM(memory_mb), 0) as memory_mb,
                    COALESCE(SUM(storage_mb), 0) as storage_mb
                FROM compute_usage 
                WHERE child_id = $1 AND DATE(created_at) = $2
            ''', child_id, today)
            
            return dict(usage) if usage else {'cpu_minutes': 0, 'memory_mb': 0, 'storage_mb': 0}
    
    async def _get_active_project_count(self, child_id: str) -> int:
        """Get number of active projects for a child"""
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval('''
                SELECT COUNT(*) FROM projects 
                WHERE child_id = $1 AND status = 'active'
            ''', child_id)
            return count or 0
    
    async def record_compute_usage(self, child_id: str, resource_type: str, 
                                 amount: int, project_id: str = None):
        """Record compute usage"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO compute_usage 
                (child_id, project_id, resource_type, amount, created_at)
                VALUES ($1, $2, $3, $4, $5)
            ''', child_id, project_id, resource_type, amount, datetime.now())
    
    # Purchase Controls
    
    async def check_purchase_limit(self, child_id: str, amount: float, 
                                 category: str) -> Tuple[bool, str]:
        """Check if purchase is within limits"""
        profile = await self.get_child_profile(child_id)
        if not profile:
            return False, "Child profile not found"
        
        limits = profile.purchase_limits
        
        # Check category restrictions
        if category in limits.blocked_categories or "all" in limits.blocked_categories:
            return False, f"Category '{category}' is not allowed"
        
        if limits.allowed_categories and category not in limits.allowed_categories:
            return False, f"Category '{category}' is not in allowed list"
        
        # Check single purchase limit
        if amount > limits.single_purchase_limit:
            return False, f"Single purchase limit exceeded (${limits.single_purchase_limit})"
        
        # Get spending history
        spending = await self._get_spending_history(child_id)
        
        # Check daily limit
        if spending['today'] + amount > limits.daily_limit:
            return False, f"Daily spending limit exceeded (${limits.daily_limit})"
        
        # Check weekly limit
        if spending['this_week'] + amount > limits.weekly_limit:
            return False, f"Weekly spending limit exceeded (${limits.weekly_limit})"
        
        # Check monthly limit
        if spending['this_month'] + amount > limits.monthly_limit:
            return False, f"Monthly spending limit exceeded (${limits.monthly_limit})"
        
        # Check if requires approval
        if amount > limits.requires_approval_above:
            return False, f"Purchase above ${limits.requires_approval_above} requires parent approval"
        
        return True, "Purchase approved"
    
    async def _get_spending_history(self, child_id: str) -> Dict[str, float]:
        """Get spending history for a child"""
        now = datetime.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        async with self.db_pool.acquire() as conn:
            # Today's spending
            today_spending = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM purchases 
                WHERE child_id = $1 AND DATE(created_at) = $2 AND status = 'approved'
            ''', child_id, today) or 0
            
            # This week's spending
            week_spending = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM purchases 
                WHERE child_id = $1 AND DATE(created_at) >= $2 AND status = 'approved'
            ''', child_id, week_start) or 0
            
            # This month's spending
            month_spending = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM purchases 
                WHERE child_id = $1 AND DATE(created_at) >= $2 AND status = 'approved'
            ''', child_id, month_start) or 0
            
            return {
                'today': float(today_spending),
                'this_week': float(week_spending),
                'this_month': float(month_spending)
            }
    
    # Time Restrictions
    
    async def check_time_restriction(self, child_id: str) -> Tuple[bool, str]:
        """Check if current time is within allowed hours"""
        profile = await self.get_child_profile(child_id)
        if not profile:
            return False, "Child profile not found"
        
        now = datetime.now()
        current_time = now.time()
        current_day = now.strftime('%A').lower()
        
        restrictions = profile.time_restrictions
        
        # Check if current day is allowed
        if current_day not in restrictions.allowed_days:
            return False, f"Access not allowed on {current_day.title()}"
        
        # Check if current time is within allowed hours
        if not (restrictions.allowed_hours_start <= current_time <= restrictions.allowed_hours_end):
            return False, f"Access only allowed between {restrictions.allowed_hours_start} and {restrictions.allowed_hours_end}"
        
        # Check daily usage limit
        today_minutes = await self._get_daily_usage_minutes(child_id)
        if today_minutes >= restrictions.max_daily_minutes:
            return False, f"Daily usage limit of {restrictions.max_daily_minutes} minutes exceeded"
        
        # Check if break is required
        if await self._is_break_required(child_id, restrictions):
            return False, f"Break required after {restrictions.break_required_after_minutes} minutes of use"
        
        return True, "Time restriction passed"
    
    async def _get_daily_usage_minutes(self, child_id: str) -> int:
        """Get today's usage minutes for a child"""
        today = datetime.now().date()
        
        async with self.db_pool.acquire() as conn:
            minutes = await conn.fetchval('''
                SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (logout_time - login_time))/60), 0)
                FROM session_logs 
                WHERE child_id = $1 AND DATE(login_time) = $2 AND logout_time IS NOT NULL
            ''', child_id, today)
            return int(minutes or 0)
    
    async def _is_break_required(self, child_id: str, restrictions: TimeRestriction) -> bool:
        """Check if a break is required based on continuous usage"""
        async with self.db_pool.acquire() as conn:
            # Get the most recent continuous session
            last_session = await conn.fetchrow('''
                SELECT login_time, logout_time FROM session_logs 
                WHERE child_id = $1 
                ORDER BY login_time DESC 
                LIMIT 1
            ''', child_id)
            
            if not last_session or last_session['logout_time']:
                return False  # No active session
            
            # Calculate continuous usage time
            usage_duration = datetime.now() - last_session['login_time']
            usage_minutes = usage_duration.total_seconds() / 60
            
            if usage_minutes >= restrictions.break_required_after_minutes:
                # Check if sufficient break was taken
                last_break = await conn.fetchval('''
                    SELECT MAX(logout_time) FROM session_logs 
                    WHERE child_id = $1 AND logout_time IS NOT NULL
                    AND logout_time < $2
                ''', child_id, last_session['login_time'])
                
                if last_break:
                    break_duration = (last_session['login_time'] - last_break).total_seconds() / 60
                    return break_duration < restrictions.min_break_duration_minutes
                
                return True  # No previous break found, break required
        
        return False
    
    # Permission Request System
    
    async def create_permission_request(self, child_id: str, permission_type: PermissionType,
                                      request_data: Dict[str, Any], reason: str,
                                      expires_in_hours: int = 24) -> str:
        """Create a permission request"""
        profile = await self.get_child_profile(child_id)
        if not profile:
            raise ValueError("Child profile not found")
        
        request_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        permission_request = PermissionRequest(
            request_id=request_id,
            child_id=child_id,
            parent_id=profile.parent_id,
            permission_type=permission_type,
            request_data=request_data,
            reason=reason,
            status=PermissionStatus.PENDING,
            requested_at=datetime.now(),
            expires_at=expires_at
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO permission_requests 
                (request_id, child_id, parent_id, permission_type, request_data, 
                 reason, status, requested_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ''',
            request_id, child_id, profile.parent_id, permission_type.value,
            json.dumps(request_data), reason, PermissionStatus.PENDING.value,
            datetime.now(), expires_at
            )
        
        # TODO: Send notification to parent
        await self._send_permission_notification(permission_request)
        
        logger.info(f"Created permission request {request_id} for child {child_id}")
        return request_id
    
    async def respond_to_permission_request(self, request_id: str, parent_id: str,
                                          approved: bool, response_reason: str = None) -> bool:
        """Respond to a permission request"""
        async with self.db_pool.acquire() as conn:
            # Get the request
            request_row = await conn.fetchrow('''
                SELECT * FROM permission_requests 
                WHERE request_id = $1 AND parent_id = $2
            ''', request_id, parent_id)
            
            if not request_row:
                return False
            
            # Check if request is still valid
            if request_row['expires_at'] < datetime.now():
                status = PermissionStatus.EXPIRED
            else:
                status = PermissionStatus.APPROVED if approved else PermissionStatus.DENIED
            
            # Update request
            await conn.execute('''
                UPDATE permission_requests 
                SET status = $1, responded_at = $2, response_reason = $3
                WHERE request_id = $4
            ''', status.value, datetime.now(), response_reason, request_id)
            
            # If approved, apply the permission temporarily
            if approved and status == PermissionStatus.APPROVED:
                await self._apply_temporary_permission(request_row)
        
        logger.info(f"Permission request {request_id} {status.value}")
        return True
    
    async def _send_permission_notification(self, request: PermissionRequest):
        """Send notification to parent about permission request"""
        # This would integrate with the notification system
        logger.info(f"Sending permission notification to parent {request.parent_id}")
        # TODO: Implement actual notification sending
    
    async def _apply_temporary_permission(self, request_row: Dict[str, Any]):
        """Apply temporary permission based on approval"""
        permission_type = PermissionType(request_row['permission_type'])
        request_data = json.loads(request_row['request_data'])
        
        if permission_type == PermissionType.EXTENDED_TIME:
            # Grant extended time for today
            await self._grant_extended_time(request_row['child_id'], request_data.get('extra_minutes', 60))
        
        elif permission_type == PermissionType.COMPUTE_QUOTA:
            # Increase compute quota temporarily
            await self._increase_compute_quota(request_row['child_id'], request_data)
        
        # TODO: Implement other permission types
    
    async def _grant_extended_time(self, child_id: str, extra_minutes: int):
        """Grant extended screen time for today"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO temporary_permissions 
                (child_id, permission_type, permission_data, valid_until)
                VALUES ($1, $2, $3, $4)
            ''',
            child_id, 'extended_time', 
            json.dumps({'extra_minutes': extra_minutes}),
            datetime.now().replace(hour=23, minute=59, second=59)
            )
    
    async def _increase_compute_quota(self, child_id: str, quota_increase: Dict[str, int]):
        """Temporarily increase compute quota"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO temporary_permissions 
                (child_id, permission_type, permission_data, valid_until)
                VALUES ($1, $2, $3, $4)
            ''',
            child_id, 'compute_quota',
            json.dumps(quota_increase),
            datetime.now() + timedelta(hours=24)
            )
    
    # Activity Monitoring
    
    async def log_activity(self, child_id: str, activity_type: str, 
                         activity_data: Dict[str, Any]):
        """Log child activity for monitoring"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO activity_logs 
                (child_id, activity_type, activity_data, created_at)
                VALUES ($1, $2, $3, $4)
            ''', child_id, activity_type, json.dumps(activity_data), datetime.now())
    
    async def get_activity_summary(self, child_id: str, days: int = 7) -> Dict[str, Any]:
        """Get activity summary for a child"""
        since_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            # Get activity counts by type
            activities = await conn.fetch('''
                SELECT activity_type, COUNT(*) as count
                FROM activity_logs 
                WHERE child_id = $1 AND created_at >= $2
                GROUP BY activity_type
                ORDER BY count DESC
            ''', child_id, since_date)
            
            # Get daily usage minutes
            usage_minutes = await conn.fetch('''
                SELECT DATE(login_time) as date, 
                       SUM(EXTRACT(EPOCH FROM (logout_time - login_time))/60) as minutes
                FROM session_logs 
                WHERE child_id = $1 AND login_time >= $2 AND logout_time IS NOT NULL
                GROUP BY DATE(login_time)
                ORDER BY date
            ''', child_id, since_date)
            
            return {
                'activities': [dict(row) for row in activities],
                'daily_usage': [{'date': row['date'].isoformat(), 'minutes': int(row['minutes'] or 0)} for row in usage_minutes],
                'period_days': days
            }
    
    async def get_children_for_parent(self, parent_id: str) -> List[ChildProfile]:
        """Get all children for a parent"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM child_profiles 
                WHERE parent_id = $1 AND is_active = TRUE
                ORDER BY name
            ''', parent_id)
            
            children = []
            for row in rows:
                child = ChildProfile(
                    child_id=row['child_id'],
                    parent_id=row['parent_id'],
                    name=row['name'],
                    age=row['age'],
                    age_group=AgeGroup(row['age_group']),
                    compute_limits=ComputeLimit(**json.loads(row['compute_limits'])),
                    purchase_limits=PurchaseLimit(**json.loads(row['purchase_limits'])),
                    time_restrictions=TimeRestriction(
                        **{k: time.fromisoformat(v) if k.endswith('_start') or k.endswith('_end') else v 
                           for k, v in json.loads(row['time_restrictions']).items()}
                    ),
                    content_filter=ContentFilter(**{
                        **json.loads(row['content_filter']),
                        'age_group': AgeGroup(json.loads(row['content_filter'])['age_group']),
                        'restriction_level': RestrictionLevel(json.loads(row['content_filter'])['restriction_level'])
                    }),
                    is_active=row['is_active'],
                    created_at=row['created_at']
                )
                children.append(child)
            
            return children
    
    async def get_pending_permissions(self, parent_id: str) -> List[PermissionRequest]:
        """Get pending permission requests for a parent"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM permission_requests 
                WHERE parent_id = $1 AND status = 'pending' AND expires_at > NOW()
                ORDER BY requested_at DESC
            ''', parent_id)
            
            requests = []
            for row in rows:
                request = PermissionRequest(
                    request_id=row['request_id'],
                    child_id=row['child_id'],
                    parent_id=row['parent_id'],
                    permission_type=PermissionType(row['permission_type']),
                    request_data=json.loads(row['request_data']),
                    reason=row['reason'],
                    status=PermissionStatus(row['status']),
                    requested_at=row['requested_at'],
                    expires_at=row['expires_at']
                )
                requests.append(request)
            
            return requests

def main():
    """Example usage"""
    async def test_parental_controls():
        # This would be initialized with actual database connection
        # db_pool = await asyncpg.create_pool("postgresql://...")
        # control_engine = ParentalControlEngine(db_pool)
        
        print("Parental Control Engine example - would integrate with database")
        
        # Example usage:
        # child_id = await control_engine.create_child_profile("parent123", {
        #     "name": "Alice",
        #     "age": 8,
        #     "restriction_level": "moderate"
        # })
        
        # allowed, message = await control_engine.check_compute_limit(child_id, "cpu_minutes", 30)
        # print(f"Compute check: {allowed} - {message}")
        
        # allowed, message = await control_engine.check_time_restriction(child_id)
        # print(f"Time check: {allowed} - {message}")
        
    asyncio.run(test_parental_controls())

if __name__ == '__main__':
    main()