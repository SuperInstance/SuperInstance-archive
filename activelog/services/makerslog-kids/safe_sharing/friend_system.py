import asyncio
import asyncpg
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import secrets
import string
import hashlib


class FriendshipStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    EXPIRED = "expired"


class ShareType(Enum):
    PROJECT = "project"
    ACHIEVEMENT = "achievement"
    ARTWORK = "artwork"
    MESSAGE = "message"
    COLLABORATION = "collaboration"


class PrivacyLevel(Enum):
    PRIVATE = "private"
    FRIENDS_ONLY = "friends_only"
    PUBLIC = "public"


@dataclass
class FriendCode:
    code: str
    user_id: str
    display_name: str
    expires_at: datetime
    uses_remaining: int
    is_active: bool


@dataclass
class SafeShare:
    share_id: str
    sender_id: str
    content_type: ShareType
    content_data: Dict
    privacy_level: PrivacyLevel
    allowed_friends: List[str]
    expires_at: Optional[datetime]
    view_count: int
    is_active: bool


class SafeSharingSystem:
    def __init__(self, db_pool: asyncpg.Pool, content_filter):
        self.db_pool = db_pool
        self.content_filter = content_filter
        self.friend_code_length = 8
        self.max_friends_per_age = {
            (5, 8): 5,
            (9, 12): 10,
            (13, 16): 20,
            (17, 18): 50
        }
        
    async def initialize_tables(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS friend_codes (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(20) UNIQUE NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    display_name VARCHAR(100) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    uses_remaining INTEGER DEFAULT 3,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS friendships (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    friend_id VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    friend_code_used VARCHAR(20),
                    parent_approved_user BOOLEAN DEFAULT FALSE,
                    parent_approved_friend BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, friend_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS safe_shares (
                    id SERIAL PRIMARY KEY,
                    share_id VARCHAR(50) UNIQUE NOT NULL,
                    sender_id VARCHAR(50) NOT NULL,
                    content_type VARCHAR(50) NOT NULL,
                    content_data JSONB NOT NULL,
                    privacy_level VARCHAR(20) NOT NULL,
                    allowed_friends JSONB DEFAULT '[]',
                    expires_at TIMESTAMP,
                    view_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    parent_approved BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS share_views (
                    id SERIAL PRIMARY KEY,
                    share_id VARCHAR(50) NOT NULL,
                    viewer_id VARCHAR(50) NOT NULL,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(share_id, viewer_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS blocked_users (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    blocked_user_id VARCHAR(50) NOT NULL,
                    reason VARCHAR(200),
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, blocked_user_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS parent_notifications (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    notification_type VARCHAR(50) NOT NULL,
                    content JSONB NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def generate_friend_code(self, user_id: str, display_name: str, 
                                 duration_hours: int = 72, max_uses: int = 3) -> Dict:
        """Generate a friend code for safe friend connections"""
        # Check if user already has an active friend code
        async with self.db_pool.acquire() as conn:
            existing_code = await conn.fetchrow("""
                SELECT * FROM friend_codes 
                WHERE user_id = $1 AND is_active = TRUE AND expires_at > CURRENT_TIMESTAMP
            """, user_id)
            
            if existing_code:
                return {
                    "success": True,
                    "friend_code": existing_code["code"],
                    "expires_at": existing_code["expires_at"].isoformat(),
                    "uses_remaining": existing_code["uses_remaining"],
                    "message": "You already have an active friend code"
                }
        
        # Generate new unique code
        while True:
            code = self._generate_code()
            
            # Check if code already exists
            async with self.db_pool.acquire() as conn:
                exists = await conn.fetchval("""
                    SELECT EXISTS(SELECT 1 FROM friend_codes WHERE code = $1)
                """, code)
                
                if not exists:
                    break
        
        # Create the friend code
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO friend_codes (code, user_id, display_name, expires_at, uses_remaining)
                VALUES ($1, $2, $3, $4, $5)
            """, code, user_id, display_name, expires_at, max_uses)
        
        return {
            "success": True,
            "friend_code": code,
            "expires_at": expires_at.isoformat(),
            "uses_remaining": max_uses,
            "instructions": [
                "Share this code only with people you know in real life",
                "Never share your friend code on public websites or social media",
                "The code will expire in 3 days",
                "Ask a parent or guardian if you're unsure about sharing"
            ]
        }

    async def use_friend_code(self, requester_id: str, friend_code: str) -> Dict:
        """Use a friend code to send a friend request"""
        # Validate the friend code
        async with self.db_pool.acquire() as conn:
            code_data = await conn.fetchrow("""
                SELECT * FROM friend_codes
                WHERE code = $1 AND is_active = TRUE 
                AND expires_at > CURRENT_TIMESTAMP AND uses_remaining > 0
            """, friend_code)
            
            if not code_data:
                return {
                    "success": False,
                    "reason": "Invalid or expired friend code",
                    "suggestions": [
                        "Check that you typed the code correctly",
                        "Ask your friend for a new code if this one expired",
                        "Make sure all letters are capitalized correctly"
                    ]
                }
            
            friend_id = code_data["user_id"]
            
            # Can't friend yourself
            if requester_id == friend_id:
                return {
                    "success": False,
                    "reason": "You can't add yourself as a friend",
                    "suggestions": ["Try getting a friend code from someone else"]
                }
            
            # Check if already friends or request pending
            existing_relationship = await conn.fetchrow("""
                SELECT status FROM friendships
                WHERE (user_id = $1 AND friend_id = $2) OR (user_id = $2 AND friend_id = $1)
            """, requester_id, friend_id)
            
            if existing_relationship:
                status = existing_relationship["status"]
                if status == "accepted":
                    return {"success": False, "reason": "You're already friends!"}
                elif status == "pending":
                    return {"success": False, "reason": "Friend request already pending"}
                elif status == "blocked":
                    return {"success": False, "reason": "Unable to send friend request"}
            
            # Check friend limits
            requester_age = await self.get_user_age(requester_id)
            friend_count = await self.get_friend_count(requester_id)
            max_friends = self.get_max_friends_for_age(requester_age)
            
            if friend_count >= max_friends:
                return {
                    "success": False,
                    "reason": f"You've reached the maximum of {max_friends} friends for your age",
                    "suggestions": ["Remove some friends before adding new ones"]
                }
            
            # Create pending friendship
            await conn.execute("""
                INSERT INTO friendships (user_id, friend_id, status, friend_code_used)
                VALUES ($1, $2, 'pending', $3)
            """, requester_id, friend_id, friend_code)
            
            # Update friend code usage
            await conn.execute("""
                UPDATE friend_codes 
                SET uses_remaining = uses_remaining - 1,
                    is_active = CASE WHEN uses_remaining - 1 <= 0 THEN FALSE ELSE TRUE END
                WHERE code = $1
            """, friend_code)
        
        # Check if parent approval is needed
        needs_approval = await self.needs_parent_approval(requester_id, friend_id)
        
        if needs_approval:
            await self.send_parent_approval_request(requester_id, friend_id)
            return {
                "success": True,
                "status": "pending_parent_approval",
                "message": "Friend request sent! Waiting for parent approval.",
                "friend_name": code_data["display_name"]
            }
        else:
            # Auto-accept for older kids or with parent settings
            await self.accept_friend_request(requester_id, friend_id)
            return {
                "success": True,
                "status": "accepted",
                "message": f"You're now friends with {code_data['display_name']}!",
                "friend_name": code_data["display_name"]
            }

    async def get_friend_requests(self, user_id: str) -> Dict:
        """Get pending friend requests for a user"""
        async with self.db_pool.acquire() as conn:
            # Incoming requests
            incoming = await conn.fetch("""
                SELECT f.*, u.display_name, u.age
                FROM friendships f
                JOIN user_profiles u ON f.user_id = u.user_id
                WHERE f.friend_id = $1 AND f.status = 'pending'
                ORDER BY f.created_at DESC
            """, user_id)
            
            # Outgoing requests
            outgoing = await conn.fetch("""
                SELECT f.*, u.display_name, u.age
                FROM friendships f
                JOIN user_profiles u ON f.friend_id = u.user_id
                WHERE f.user_id = $1 AND f.status = 'pending'
                ORDER BY f.created_at DESC
            """, user_id)
        
        return {
            "incoming": [
                {
                    "requester_id": req["user_id"],
                    "requester_name": req["display_name"],
                    "requester_age": req["age"],
                    "requested_at": req["created_at"].isoformat(),
                    "friend_code_used": req["friend_code_used"],
                    "needs_parent_approval": not req["parent_approved_user"] or not req["parent_approved_friend"]
                } for req in incoming
            ],
            "outgoing": [
                {
                    "friend_id": req["friend_id"],
                    "friend_name": req["display_name"],
                    "friend_age": req["age"],
                    "requested_at": req["created_at"].isoformat(),
                    "status": "waiting_for_response"
                } for req in outgoing
            ]
        }

    async def accept_friend_request(self, user_id: str, friend_id: str) -> Dict:
        """Accept a friend request"""
        async with self.db_pool.acquire() as conn:
            # Check if request exists and is pending
            request = await conn.fetchrow("""
                SELECT * FROM friendships
                WHERE user_id = $1 AND friend_id = $2 AND status = 'pending'
            """, friend_id, user_id)  # Note: reversed order for incoming request
            
            if not request:
                return {"success": False, "reason": "No pending friend request found"}
            
            # Check friend limits for both users
            user_age = await self.get_user_age(user_id)
            friend_age = await self.get_user_age(friend_id)
            
            user_friend_count = await self.get_friend_count(user_id)
            friend_friend_count = await self.get_friend_count(friend_id)
            
            if user_friend_count >= self.get_max_friends_for_age(user_age):
                return {"success": False, "reason": "You've reached your friend limit"}
            
            if friend_friend_count >= self.get_max_friends_for_age(friend_age):
                return {"success": False, "reason": "Your friend has reached their friend limit"}
            
            # Accept the friendship
            await conn.execute("""
                UPDATE friendships 
                SET status = 'accepted', updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1 AND friend_id = $2
            """, friend_id, user_id)
            
            # Get friend's display name
            friend_name = await conn.fetchval("""
                SELECT display_name FROM user_profiles WHERE user_id = $1
            """, friend_id)
        
        # Send notifications to both users
        await self.send_friendship_notification(user_id, friend_id, "accepted")
        await self.send_friendship_notification(friend_id, user_id, "new_friend")
        
        return {
            "success": True,
            "message": f"You're now friends with {friend_name}!",
            "friend_id": friend_id,
            "friend_name": friend_name
        }

    async def decline_friend_request(self, user_id: str, friend_id: str) -> Dict:
        """Decline a friend request"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM friendships
                WHERE user_id = $1 AND friend_id = $2 AND status = 'pending'
            """, friend_id, user_id)
            
            if result == "DELETE 0":
                return {"success": False, "reason": "No pending friend request found"}
        
        return {
            "success": True,
            "message": "Friend request declined"
        }

    async def remove_friend(self, user_id: str, friend_id: str) -> Dict:
        """Remove a friend"""
        async with self.db_pool.acquire() as conn:
            # Remove both directions of the friendship
            await conn.execute("""
                DELETE FROM friendships
                WHERE (user_id = $1 AND friend_id = $2) OR (user_id = $2 AND friend_id = $1)
            """, user_id, friend_id)
            
            friend_name = await conn.fetchval("""
                SELECT display_name FROM user_profiles WHERE user_id = $1
            """, friend_id)
        
        return {
            "success": True,
            "message": f"Removed {friend_name} from your friends list"
        }

    async def get_friends_list(self, user_id: str) -> Dict:
        """Get user's friends list"""
        async with self.db_pool.acquire() as conn:
            friends = await conn.fetch("""
                SELECT 
                    CASE 
                        WHEN f.user_id = $1 THEN f.friend_id 
                        ELSE f.user_id 
                    END as friend_id,
                    u.display_name, u.age, u.last_active,
                    f.created_at as friends_since
                FROM friendships f
                JOIN user_profiles u ON (
                    CASE 
                        WHEN f.user_id = $1 THEN f.friend_id = u.user_id
                        ELSE f.user_id = u.user_id
                    END
                )
                WHERE (f.user_id = $1 OR f.friend_id = $1) 
                AND f.status = 'accepted'
                ORDER BY u.last_active DESC
            """, user_id)
        
        return {
            "friends": [
                {
                    "friend_id": friend["friend_id"],
                    "display_name": friend["display_name"],
                    "age": friend["age"],
                    "online_status": self._get_online_status(friend["last_active"]),
                    "friends_since": friend["friends_since"].isoformat(),
                    "can_share_with": True  # Could be based on parent settings
                } for friend in friends
            ],
            "total_friends": len(friends),
            "max_friends": self.get_max_friends_for_age(await self.get_user_age(user_id))
        }

    async def create_safe_share(self, sender_id: str, content_type: ShareType, 
                              content_data: Dict, privacy_level: PrivacyLevel = PrivacyLevel.FRIENDS_ONLY,
                              allowed_friends: List[str] = None, expires_hours: int = None) -> Dict:
        """Create a safe share that can be viewed by friends"""
        
        # Content safety check
        content_text = self._extract_text_for_filtering(content_data)
        if content_text:
            from .content_filtering.content_filter import ContentType
            safety_result = await self.content_filter.analyze_content(
                content_text, ContentType.TEXT, sender_id
            )
            
            if safety_result.action.value == "block":
                return {
                    "success": False,
                    "reason": "Content doesn't meet our safety guidelines",
                    "suggestions": safety_result.suggested_modifications
                }
        
        # Check parent approval requirements
        sender_age = await self.get_user_age(sender_id)
        needs_parent_approval = await self.share_needs_parent_approval(sender_id, content_type)
        
        share_id = secrets.token_urlsafe(16)
        expires_at = None
        if expires_hours:
            expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        # Set allowed friends based on privacy level
        if privacy_level == PrivacyLevel.FRIENDS_ONLY and not allowed_friends:
            friends_list = await self.get_friends_list(sender_id)
            allowed_friends = [friend["friend_id"] for friend in friends_list["friends"]]
        elif privacy_level == PrivacyLevel.PRIVATE:
            allowed_friends = allowed_friends or []
        elif privacy_level == PrivacyLevel.PUBLIC:
            allowed_friends = []  # Public means everyone can see
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO safe_shares (
                    share_id, sender_id, content_type, content_data,
                    privacy_level, allowed_friends, expires_at, parent_approved
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, 
                share_id, sender_id, content_type.value, json.dumps(content_data),
                privacy_level.value, json.dumps(allowed_friends), expires_at,
                not needs_parent_approval
            )
        
        if needs_parent_approval:
            await self.request_share_approval(sender_id, share_id, content_type)
            return {
                "success": True,
                "share_id": share_id,
                "status": "pending_approval",
                "message": "Your share is waiting for parent approval before it becomes visible"
            }
        
        # Notify friends about new share (if appropriate)
        if privacy_level in [PrivacyLevel.FRIENDS_ONLY, PrivacyLevel.PUBLIC]:
            await self.notify_friends_about_share(sender_id, share_id, allowed_friends)
        
        return {
            "success": True,
            "share_id": share_id,
            "status": "active",
            "message": "Your content has been shared successfully!",
            "share_url": f"/share/{share_id}",
            "visible_to": len(allowed_friends) if allowed_friends else "all friends"
        }

    async def view_safe_share(self, viewer_id: str, share_id: str) -> Dict:
        """View a safe share"""
        async with self.db_pool.acquire() as conn:
            share = await conn.fetchrow("""
                SELECT s.*, u.display_name as sender_name
                FROM safe_shares s
                JOIN user_profiles u ON s.sender_id = u.user_id
                WHERE s.share_id = $1 AND s.is_active = TRUE
                AND (s.expires_at IS NULL OR s.expires_at > CURRENT_TIMESTAMP)
                AND s.parent_approved = TRUE
            """, share_id)
            
            if not share:
                return {
                    "success": False,
                    "reason": "Share not found or no longer available"
                }
            
            # Check viewing permissions
            can_view = await self.can_view_share(viewer_id, share)
            if not can_view:
                return {
                    "success": False,
                    "reason": "You don't have permission to view this share"
                }
            
            # Record the view
            await conn.execute("""
                INSERT INTO share_views (share_id, viewer_id)
                VALUES ($1, $2)
                ON CONFLICT (share_id, viewer_id) DO NOTHING
            """, share_id, viewer_id)
            
            # Update view count
            await conn.execute("""
                UPDATE safe_shares 
                SET view_count = view_count + 1
                WHERE share_id = $1
            """, share_id)
            
            content_data = json.loads(share["content_data"])
            
        return {
            "success": True,
            "share": {
                "share_id": share_id,
                "sender_id": share["sender_id"],
                "sender_name": share["sender_name"],
                "content_type": share["content_type"],
                "content_data": content_data,
                "created_at": share["created_at"].isoformat(),
                "view_count": share["view_count"] + 1,
                "privacy_level": share["privacy_level"]
            },
            "viewer_actions": await self.get_viewer_actions(viewer_id, share_id)
        }

    async def get_user_shares(self, user_id: str, include_expired: bool = False) -> Dict:
        """Get user's shares"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT * FROM safe_shares 
                WHERE sender_id = $1 AND is_active = TRUE
            """
            
            if not include_expired:
                query += " AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)"
            
            query += " ORDER BY created_at DESC"
            
            shares = await conn.fetch(query, user_id)
        
        return {
            "shares": [
                {
                    "share_id": share["share_id"],
                    "content_type": share["content_type"],
                    "privacy_level": share["privacy_level"],
                    "view_count": share["view_count"],
                    "created_at": share["created_at"].isoformat(),
                    "expires_at": share["expires_at"].isoformat() if share["expires_at"] else None,
                    "parent_approved": share["parent_approved"],
                    "is_active": share["is_active"]
                } for share in shares
            ],
            "total_shares": len(shares),
            "sharing_stats": await self.get_sharing_statistics(user_id)
        }

    async def delete_share(self, user_id: str, share_id: str) -> Dict:
        """Delete a user's share"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE safe_shares 
                SET is_active = FALSE 
                WHERE share_id = $1 AND sender_id = $2
            """, share_id, user_id)
            
            if result == "UPDATE 0":
                return {"success": False, "reason": "Share not found or not owned by you"}
        
        return {
            "success": True,
            "message": "Share has been deleted"
        }

    async def report_share(self, reporter_id: str, share_id: str, reason: str) -> Dict:
        """Report inappropriate content"""
        async with self.db_pool.acquire() as conn:
            # Check if share exists
            share = await conn.fetchrow("""
                SELECT sender_id FROM safe_shares WHERE share_id = $1
            """, share_id)
            
            if not share:
                return {"success": False, "reason": "Share not found"}
            
            # Create report
            await conn.execute("""
                INSERT INTO content_reports (
                    reporter_id, content_type, content_id, reason, reported_at
                ) VALUES ($1, 'share', $2, $3, CURRENT_TIMESTAMP)
            """, reporter_id, share_id, reason)
        
        # Notify parents and moderators
        await self.handle_content_report(reporter_id, share_id, reason)
        
        return {
            "success": True,
            "message": "Thank you for reporting. We'll review this content."
        }

    async def block_user(self, user_id: str, blocked_user_id: str, reason: str = None) -> Dict:
        """Block another user"""
        if user_id == blocked_user_id:
            return {"success": False, "reason": "You can't block yourself"}
        
        async with self.db_pool.acquire() as conn:
            # Add to blocked users
            await conn.execute("""
                INSERT INTO blocked_users (user_id, blocked_user_id, reason)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, blocked_user_id) DO NOTHING
            """, user_id, blocked_user_id, reason)
            
            # Remove any existing friendship
            await conn.execute("""
                UPDATE friendships 
                SET status = 'blocked'
                WHERE (user_id = $1 AND friend_id = $2) OR (user_id = $2 AND friend_id = $1)
            """, user_id, blocked_user_id)
            
            blocked_name = await conn.fetchval("""
                SELECT display_name FROM user_profiles WHERE user_id = $1
            """, blocked_user_id)
        
        # Notify parents
        await self.notify_parent_about_block(user_id, blocked_user_id, reason)
        
        return {
            "success": True,
            "message": f"You have blocked {blocked_name}. They can no longer contact you."
        }

    # Helper methods
    def _generate_code(self) -> str:
        """Generate a random friend code"""
        # Use a mix of letters and numbers, avoiding confusing characters
        chars = string.ascii_uppercase.replace('O', '').replace('I', '') + '23456789'
        return ''.join(secrets.choice(chars) for _ in range(self.friend_code_length))

    async def get_user_age(self, user_id: str) -> int:
        """Get user age from profile"""
        # This would integrate with user profile system
        return 10  # Default age

    def get_max_friends_for_age(self, age: int) -> int:
        """Get maximum friends allowed for user's age"""
        for (min_age, max_age), limit in self.max_friends_per_age.items():
            if min_age <= age <= max_age:
                return limit
        return 10  # Default limit

    async def get_friend_count(self, user_id: str) -> int:
        """Get user's current friend count"""
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM friendships
                WHERE (user_id = $1 OR friend_id = $1) AND status = 'accepted'
            """, user_id)
            return count or 0

    async def needs_parent_approval(self, user_id: str, friend_id: str) -> bool:
        """Check if friendship needs parent approval"""
        user_age = await self.get_user_age(user_id)
        friend_age = await self.get_user_age(friend_id)
        
        # Young kids always need parent approval
        if user_age < 10 or friend_age < 10:
            return True
        
        # Check parent settings
        # This would integrate with parental control settings
        return False

    def _get_online_status(self, last_active: datetime) -> str:
        """Get user's online status"""
        if not last_active:
            return "offline"
        
        time_diff = datetime.now() - last_active
        if time_diff < timedelta(minutes=5):
            return "online"
        elif time_diff < timedelta(minutes=30):
            return "away"
        else:
            return "offline"

    def _extract_text_for_filtering(self, content_data: Dict) -> str:
        """Extract text content for safety filtering"""
        text_parts = []
        
        if "title" in content_data:
            text_parts.append(content_data["title"])
        if "description" in content_data:
            text_parts.append(content_data["description"])
        if "message" in content_data:
            text_parts.append(content_data["message"])
        if "comments" in content_data:
            if isinstance(content_data["comments"], list):
                text_parts.extend(content_data["comments"])
            else:
                text_parts.append(str(content_data["comments"]))
        
        return " ".join(text_parts)

    async def share_needs_parent_approval(self, user_id: str, content_type: ShareType) -> bool:
        """Check if share needs parent approval"""
        user_age = await self.get_user_age(user_id)
        
        # Young kids need approval for all shares
        if user_age < 8:
            return True
        
        # Certain content types need approval
        if content_type in [ShareType.COLLABORATION, ShareType.MESSAGE]:
            return user_age < 12
        
        return False

    async def can_view_share(self, viewer_id: str, share) -> bool:
        """Check if user can view a share"""
        sender_id = share["sender_id"]
        privacy_level = share["privacy_level"]
        allowed_friends = json.loads(share["allowed_friends"]) if share["allowed_friends"] else []
        
        # Own content
        if viewer_id == sender_id:
            return True
        
        # Check if blocked
        if await self.is_user_blocked(sender_id, viewer_id):
            return False
        
        # Privacy level checks
        if privacy_level == PrivacyLevel.PUBLIC.value:
            return True
        elif privacy_level == PrivacyLevel.FRIENDS_ONLY.value:
            return await self.are_friends(viewer_id, sender_id)
        elif privacy_level == PrivacyLevel.PRIVATE.value:
            return viewer_id in allowed_friends
        
        return False

    async def are_friends(self, user_id1: str, user_id2: str) -> bool:
        """Check if two users are friends"""
        async with self.db_pool.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM friendships
                    WHERE ((user_id = $1 AND friend_id = $2) OR (user_id = $2 AND friend_id = $1))
                    AND status = 'accepted'
                )
            """, user_id1, user_id2)
            return exists

    async def is_user_blocked(self, user_id: str, potentially_blocked_user: str) -> bool:
        """Check if a user is blocked"""
        async with self.db_pool.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM blocked_users
                    WHERE user_id = $1 AND blocked_user_id = $2
                )
            """, user_id, potentially_blocked_user)
            return exists

    async def get_viewer_actions(self, viewer_id: str, share_id: str) -> List[str]:
        """Get available actions for viewer"""
        actions = ["like", "share_with_friends"]
        
        # Add report action if not own content
        async with self.db_pool.acquire() as conn:
            is_own_content = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM safe_shares WHERE share_id = $1 AND sender_id = $2)
            """, share_id, viewer_id)
            
            if not is_own_content:
                actions.append("report")
        
        return actions

    async def get_sharing_statistics(self, user_id: str) -> Dict:
        """Get user's sharing statistics"""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_shares,
                    SUM(view_count) as total_views,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') as shares_this_week
                FROM safe_shares
                WHERE sender_id = $1 AND is_active = TRUE
            """, user_id)
        
        return {
            "total_shares": stats["total_shares"] or 0,
            "total_views": stats["total_views"] or 0,
            "shares_this_week": stats["shares_this_week"] or 0,
            "average_views_per_share": (stats["total_views"] / stats["total_shares"]) if stats["total_shares"] > 0 else 0
        }

    # Integration methods (would integrate with notification system)
    async def send_friendship_notification(self, user_id: str, friend_id: str, notification_type: str):
        """Send friendship-related notification"""
        pass

    async def send_parent_approval_request(self, user_id: str, friend_id: str):
        """Send parent approval request for friendship"""
        pass

    async def request_share_approval(self, user_id: str, share_id: str, content_type: ShareType):
        """Request parent approval for share"""
        pass

    async def notify_friends_about_share(self, sender_id: str, share_id: str, friend_ids: List[str]):
        """Notify friends about new share"""
        pass

    async def handle_content_report(self, reporter_id: str, share_id: str, reason: str):
        """Handle content report"""
        pass

    async def notify_parent_about_block(self, user_id: str, blocked_user_id: str, reason: str):
        """Notify parent about user blocking another user"""
        pass