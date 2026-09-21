"""
Guest access management with expiry and rate limiting
"""

import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

from core.database import db_manager, guest_access_tokens, guest_sessions, documents, activity_feed
from core.database import ActivityType
from core.config import settings

logger = logging.getLogger(__name__)

class GuestManager:
    def __init__(self):
        self.active_tokens = {}  # Cache for active guest tokens
        self.rate_limits = {}    # Rate limiting for guest users
        self.session_cache = {}  # Cache for active guest sessions
        
    async def initialize(self):
        """Initialize guest manager"""
        logger.info("Initializing guest manager")
        await self._load_active_tokens()
        await self._load_active_sessions()
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up guest manager")
        self.active_tokens.clear()
        self.rate_limits.clear()
        self.session_cache.clear()
        
    async def _load_active_tokens(self):
        """Load active guest tokens into cache"""
        try:
            query = f"""
                SELECT gat.*, d.name as document_name, d.workspace_id
                FROM {guest_access_tokens.name} gat
                JOIN {documents.name} d ON gat.document_id = d.id
                WHERE gat.is_active = true 
                AND gat.expires_at > NOW()
                ORDER BY gat.created_at DESC
                LIMIT 10000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for token_data in results:
                token_dict = dict(token_data)
                token = token_dict["token"]
                self.active_tokens[token] = token_dict
                
            logger.info(f"Loaded {len(results)} active guest tokens")
            
        except Exception as e:
            logger.error(f"Failed to load active guest tokens: {e}")
            
    async def _load_active_sessions(self):
        """Load active guest sessions into cache"""
        try:
            query = f"""
                SELECT gs.*, gat.token, d.name as document_name
                FROM {guest_sessions.name} gs
                JOIN {guest_access_tokens.name} gat ON gs.token_id = gat.id
                JOIN {documents.name} d ON gs.document_id = d.id
                WHERE gs.is_active = true 
                AND gs.last_activity_at > NOW() - INTERVAL '1 hour'
                ORDER BY gs.last_activity_at DESC
                LIMIT 5000
            """
            
            results = await db_manager.database.fetch_all(query)
            
            for session_data in results:
                session_dict = dict(session_data)
                session_id = session_dict["session_id"]
                self.session_cache[session_id] = session_dict
                
            logger.info(f"Loaded {len(results)} active guest sessions")
            
        except Exception as e:
            logger.error(f"Failed to load active guest sessions: {e}")
            
    async def create_guest_token(self, document_id: str, permissions: List[str],
                               created_by: str, guest_email: str = None,
                               guest_name: str = None, max_uses: int = 1,
                               expires_hours: int = None) -> Dict[str, Any]:
        """Create a guest access token"""
        try:
            # Validate permissions
            valid_permissions = {"read", "comment"}
            if not set(permissions).issubset(valid_permissions):
                raise ValueError(f"Invalid permissions. Valid permissions: {valid_permissions}")
            
            # Check if document exists and user has permission
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                raise ValueError(f"Document {document_id} not found")
                
            document = dict(doc_result)
            
            # TODO: Check if created_by has admin permission on document
            
            # Set expiry
            expires_hours = expires_hours or settings.GUEST_TOKEN_EXPIRE_HOURS
            expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
            
            # Generate secure token
            token = secrets.token_urlsafe(32)
            
            # Ensure token is unique
            while token in self.active_tokens:
                token = secrets.token_urlsafe(32)
            
            # Create token record
            token_data = {
                "id": str(uuid4()),
                "token": token,
                "document_id": document_id,
                "permissions": permissions,
                "created_by": created_by,
                "guest_email": guest_email,
                "guest_name": guest_name,
                "max_uses": max_uses,
                "current_uses": 0,
                "expires_at": expires_at,
                "is_active": True,
                "metadata": {},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = guest_access_tokens.insert().values(**token_data)
            await db_manager.database.execute(query)
            
            # Add to cache
            token_data["document_name"] = document["name"]
            token_data["workspace_id"] = document["workspace_id"]
            self.active_tokens[token] = token_data
            
            # Log activity
            await self._log_guest_activity(
                document_id=document_id,
                user_id=created_by,
                activity_type="guest_token_created",
                details={
                    "guest_email": guest_email,
                    "guest_name": guest_name,
                    "permissions": permissions,
                    "expires_at": expires_at.isoformat(),
                    "max_uses": max_uses
                }
            )
            
            logger.info(f"Created guest token {token} for document {document_id}")
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to create guest token: {e}")
            raise
            
    async def validate_guest_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a guest access token"""
        try:
            # Check cache first
            if token in self.active_tokens:
                token_data = self.active_tokens[token]
                
                # Check if expired
                if token_data["expires_at"] <= datetime.now(timezone.utc):
                    await self._deactivate_token(token)
                    return None
                    
                # Check if uses exceeded
                if token_data["current_uses"] >= token_data["max_uses"]:
                    await self._deactivate_token(token)
                    return None
                    
                return token_data
            
            # Query database
            token_data = await db_manager.validate_guest_token(token)
            
            if token_data:
                # Add to cache
                self.active_tokens[token] = token_data
                return token_data
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to validate guest token: {e}")
            return None
            
    async def create_guest_session(self, token: str, guest_ip: str = None,
                                 guest_user_agent: str = None) -> Dict[str, Any]:
        """Create a guest session"""
        try:
            # Validate token
            token_data = await self.validate_guest_token(token)
            if not token_data:
                raise ValueError("Invalid or expired token")
            
            # Check session limit
            active_sessions_count = await self._get_active_sessions_count(token_data["document_id"])
            if active_sessions_count >= settings.MAX_GUEST_SESSIONS_PER_DOCUMENT:
                raise ValueError("Maximum guest sessions reached for this document")
            
            # Generate session ID
            session_id = secrets.token_urlsafe(16)
            
            # Create session record
            session_data = {
                "id": str(uuid4()),
                "token_id": token_data["id"],
                "session_id": session_id,
                "document_id": token_data["document_id"],
                "guest_ip": guest_ip,
                "guest_user_agent": guest_user_agent,
                "is_active": True,
                "last_activity_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc)
            }
            
            query = guest_sessions.insert().values(**session_data)
            await db_manager.database.execute(query)
            
            # Update token usage
            await self._increment_token_usage(token)
            
            # Add to cache
            session_data["token"] = token
            session_data["document_name"] = token_data.get("document_name")
            self.session_cache[session_id] = session_data
            
            # Log activity
            await self._log_guest_activity(
                document_id=token_data["document_id"],
                user_id="guest",
                activity_type="guest_session_created",
                details={
                    "session_id": session_id,
                    "guest_name": token_data.get("guest_name"),
                    "guest_email": token_data.get("guest_email"),
                    "guest_ip": guest_ip
                }
            )
            
            logger.info(f"Created guest session {session_id} for token {token}")
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to create guest session: {e}")
            raise
            
    async def validate_guest_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate a guest session"""
        try:
            # Check cache first
            if session_id in self.session_cache:
                session_data = self.session_cache[session_id]
                
                # Check if session is still active (within last hour)
                if session_data["last_activity_at"] < datetime.now(timezone.utc) - timedelta(hours=1):
                    await self._deactivate_session(session_id)
                    return None
                    
                return session_data
            
            # Query database
            query = f"""
                SELECT gs.*, gat.token, gat.permissions, gat.expires_at as token_expires_at,
                       d.name as document_name
                FROM {guest_sessions.name} gs
                JOIN {guest_access_tokens.name} gat ON gs.token_id = gat.id
                JOIN {documents.name} d ON gs.document_id = d.id
                WHERE gs.session_id = :session_id 
                AND gs.is_active = true
                AND gat.is_active = true
                AND gat.expires_at > NOW()
            """
            
            result = await db_manager.database.fetch_one(query, {"session_id": session_id})
            
            if result:
                session_data = dict(result)
                
                # Check if session is recent
                if session_data["last_activity_at"] < datetime.now(timezone.utc) - timedelta(hours=1):
                    await self._deactivate_session(session_id)
                    return None
                
                # Add to cache
                self.session_cache[session_id] = session_data
                return session_data
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to validate guest session: {e}")
            return None
            
    async def update_session_activity(self, session_id: str):
        """Update last activity timestamp for a guest session"""
        try:
            # Update database
            update_data = {"last_activity_at": datetime.now(timezone.utc)}
            
            query = (guest_sessions.update()
                    .where(guest_sessions.c.session_id == session_id)
                    .values(**update_data))
            await db_manager.database.execute(query)
            
            # Update cache
            if session_id in self.session_cache:
                self.session_cache[session_id]["last_activity_at"] = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Failed to update session activity: {e}")
            
    async def end_guest_session(self, session_id: str):
        """End a guest session"""
        try:
            await self._deactivate_session(session_id)
            logger.info(f"Ended guest session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to end guest session: {e}")
            
    async def revoke_guest_token(self, token: str, revoked_by: str) -> bool:
        """Revoke a guest access token"""
        try:
            # Deactivate token
            await self._deactivate_token(token)
            
            # Deactivate all associated sessions
            if token in self.active_tokens:
                token_data = self.active_tokens[token]
                document_id = token_data["document_id"]
                
                # Find and deactivate sessions
                sessions_to_deactivate = []
                for session_id, session_data in self.session_cache.items():
                    if session_data.get("token") == token:
                        sessions_to_deactivate.append(session_id)
                        
                for session_id in sessions_to_deactivate:
                    await self._deactivate_session(session_id)
                
                # Log activity
                await self._log_guest_activity(
                    document_id=document_id,
                    user_id=revoked_by,
                    activity_type="guest_token_revoked",
                    details={
                        "token": token,
                        "guest_name": token_data.get("guest_name"),
                        "guest_email": token_data.get("guest_email")
                    }
                )
            
            logger.info(f"Revoked guest token {token}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke guest token: {e}")
            return False
            
    async def check_rate_limit(self, session_id: str, action: str = "general") -> bool:
        """Check if guest session is within rate limits"""
        try:
            current_time = datetime.now(timezone.utc)
            rate_key = f"{session_id}:{action}"
            
            if rate_key not in self.rate_limits:
                self.rate_limits[rate_key] = {"count": 0, "window_start": current_time}
            
            rate_data = self.rate_limits[rate_key]
            
            # Reset window if it's been more than a minute
            if current_time - rate_data["window_start"] > timedelta(minutes=1):
                rate_data["count"] = 0
                rate_data["window_start"] = current_time
            
            # Check limit
            if rate_data["count"] >= settings.GUEST_RATE_LIMIT_PER_MINUTE:
                logger.warning(f"Rate limit exceeded for guest session {session_id}")
                return False
            
            # Increment counter
            rate_data["count"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return False
            
    async def get_document_guest_tokens(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all active guest tokens for a document"""
        try:
            query = guest_access_tokens.select().where(
                (guest_access_tokens.c.document_id == document_id) &
                (guest_access_tokens.c.is_active == True) &
                (guest_access_tokens.c.expires_at > datetime.now(timezone.utc))
            ).order_by(guest_access_tokens.c.created_at.desc())
            
            results = await db_manager.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get document guest tokens: {e}")
            return []
            
    async def get_active_guest_sessions(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all active guest sessions for a document"""
        try:
            query = f"""
                SELECT gs.*, gat.guest_name, gat.guest_email, gat.permissions
                FROM {guest_sessions.name} gs
                JOIN {guest_access_tokens.name} gat ON gs.token_id = gat.id
                WHERE gs.document_id = :document_id 
                AND gs.is_active = true
                AND gs.last_activity_at > NOW() - INTERVAL '1 hour'
                ORDER BY gs.last_activity_at DESC
            """
            
            results = await db_manager.database.fetch_all(query, {"document_id": document_id})
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get active guest sessions: {e}")
            return []
            
    async def _increment_token_usage(self, token: str):
        """Increment usage count for a token"""
        try:
            query = (guest_access_tokens.update()
                    .where(guest_access_tokens.c.token == token)
                    .values(
                        current_uses=guest_access_tokens.c.current_uses + 1,
                        last_used_at=datetime.now(timezone.utc)
                    ))
            await db_manager.database.execute(query)
            
            # Update cache
            if token in self.active_tokens:
                self.active_tokens[token]["current_uses"] += 1
                self.active_tokens[token]["last_used_at"] = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Failed to increment token usage: {e}")
            
    async def _deactivate_token(self, token: str):
        """Deactivate a guest token"""
        try:
            query = (guest_access_tokens.update()
                    .where(guest_access_tokens.c.token == token)
                    .values(is_active=False))
            await db_manager.database.execute(query)
            
            # Remove from cache
            if token in self.active_tokens:
                del self.active_tokens[token]
                
        except Exception as e:
            logger.error(f"Failed to deactivate token: {e}")
            
    async def _deactivate_session(self, session_id: str):
        """Deactivate a guest session"""
        try:
            query = (guest_sessions.update()
                    .where(guest_sessions.c.session_id == session_id)
                    .values(is_active=False))
            await db_manager.database.execute(query)
            
            # Remove from cache
            if session_id in self.session_cache:
                del self.session_cache[session_id]
                
        except Exception as e:
            logger.error(f"Failed to deactivate session: {e}")
            
    async def _get_active_sessions_count(self, document_id: str) -> int:
        """Get count of active sessions for a document"""
        try:
            query = f"""
                SELECT COUNT(*) 
                FROM {guest_sessions.name} gs
                WHERE gs.document_id = :document_id 
                AND gs.is_active = true
                AND gs.last_activity_at > NOW() - INTERVAL '1 hour'
            """
            
            result = await db_manager.database.fetch_one(query, {"document_id": document_id})
            return result[0] if result else 0
            
        except Exception as e:
            logger.error(f"Failed to get active sessions count: {e}")
            return 0
            
    async def _log_guest_activity(self, document_id: str, user_id: str,
                                activity_type: str, details: Dict[str, Any] = None):
        """Log guest-related activity"""
        try:
            # Get document workspace
            doc_query = documents.select().where(documents.c.id == document_id)
            doc_result = await db_manager.database.fetch_one(doc_query)
            
            if not doc_result:
                return
                
            workspace_id = str(doc_result["workspace_id"])
            
            activity_data = {
                "workspace_id": workspace_id,
                "document_id": document_id,
                "actor_id": user_id,
                "activity_type": "guest_access",  # Custom activity type
                "target_type": "guest",
                "details": details or {},
                "metadata": {"action": activity_type},
                "created_at": datetime.now(timezone.utc)
            }
            
            query = activity_feed.insert().values(**activity_data)
            await db_manager.database.execute(query)
            
        except Exception as e:
            logger.warning(f"Failed to log guest activity: {e}")
            
    async def cleanup_expired_tokens_and_sessions(self) -> Dict[str, int]:
        """Clean up expired tokens and inactive sessions"""
        try:
            cleanup_stats = {"expired_tokens": 0, "inactive_sessions": 0}
            
            # Deactivate expired tokens
            expired_tokens_query = (guest_access_tokens.update()
                                   .where(
                                       (guest_access_tokens.c.expires_at <= datetime.now(timezone.utc)) &
                                       (guest_access_tokens.c.is_active == True)
                                   )
                                   .values(is_active=False))
            
            expired_tokens_result = await db_manager.database.execute(expired_tokens_query)
            cleanup_stats["expired_tokens"] = expired_tokens_result
            
            # Deactivate inactive sessions (more than 1 hour old)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)
            inactive_sessions_query = (guest_sessions.update()
                                      .where(
                                          (guest_sessions.c.last_activity_at < cutoff_time) &
                                          (guest_sessions.c.is_active == True)
                                      )
                                      .values(is_active=False))
            
            inactive_sessions_result = await db_manager.database.execute(inactive_sessions_query)
            cleanup_stats["inactive_sessions"] = inactive_sessions_result
            
            # Clean up caches
            expired_token_keys = []
            for token, token_data in self.active_tokens.items():
                if token_data["expires_at"] <= datetime.now(timezone.utc):
                    expired_token_keys.append(token)
                    
            for token in expired_token_keys:
                del self.active_tokens[token]
                
            inactive_session_keys = []
            for session_id, session_data in self.session_cache.items():
                if session_data["last_activity_at"] < cutoff_time:
                    inactive_session_keys.append(session_id)
                    
            for session_id in inactive_session_keys:
                del self.session_cache[session_id]
                
            # Clean up old rate limit data
            current_time = datetime.now(timezone.utc)
            expired_rate_keys = []
            for rate_key, rate_data in self.rate_limits.items():
                if current_time - rate_data["window_start"] > timedelta(hours=1):
                    expired_rate_keys.append(rate_key)
                    
            for rate_key in expired_rate_keys:
                del self.rate_limits[rate_key]
                
            logger.info(f"Cleaned up {cleanup_stats['expired_tokens']} expired tokens and {cleanup_stats['inactive_sessions']} inactive sessions")
            return cleanup_stats
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens and sessions: {e}")
            return {"expired_tokens": 0, "inactive_sessions": 0}
            
    async def get_guest_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get guest access statistics for a document"""
        try:
            # Token statistics
            token_query = f"""
                SELECT 
                    COUNT(*) as total_tokens,
                    COUNT(CASE WHEN is_active = true AND expires_at > NOW() THEN 1 END) as active_tokens,
                    COUNT(CASE WHEN expires_at <= NOW() THEN 1 END) as expired_tokens,
                    SUM(current_uses) as total_uses,
                    AVG(current_uses) as avg_uses_per_token,
                    MIN(created_at) as first_token_created,
                    MAX(created_at) as latest_token_created
                FROM {guest_access_tokens.name}
                WHERE document_id = :document_id
            """
            
            token_result = await db_manager.database.fetch_one(token_query, {"document_id": document_id})
            token_stats = dict(token_result) if token_result else {}
            
            # Session statistics
            session_query = f"""
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(CASE WHEN is_active = true AND last_activity_at > NOW() - INTERVAL '1 hour' THEN 1 END) as active_sessions,
                    COUNT(DISTINCT guest_ip) as unique_ips,
                    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/3600) as avg_session_duration_hours
                FROM {guest_sessions.name}
                WHERE document_id = :document_id
            """
            
            session_result = await db_manager.database.fetch_one(session_query, {"document_id": document_id})
            session_stats = dict(session_result) if session_result else {}
            
            return {
                "tokens": token_stats,
                "sessions": session_stats,
                "current_active_sessions": len([
                    s for s in self.session_cache.values() 
                    if s.get("document_id") == document_id
                ]),
                "current_active_tokens": len([
                    t for t in self.active_tokens.values() 
                    if t.get("document_id") == document_id
                ])
            }
            
        except Exception as e:
            logger.error(f"Failed to get guest statistics: {e}")
            return {}