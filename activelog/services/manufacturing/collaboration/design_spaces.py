"""
Collaborative Design Spaces - Multi-user design collaboration system for manufacturing
Enables real-time collaborative design, version control integration, and design review workflows.
"""

import asyncio
import sqlite3
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import aiosqlite
import websockets
import logging
from pathlib import Path
import shutil
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CollaborationRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"

class DesignStatus(Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"

class ChangeType(Enum):
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    MOVE = "move"
    COMMENT = "comment"

class ReviewStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"

@dataclass
class DesignSpace:
    id: str
    name: str
    description: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    status: DesignStatus
    visibility: str = "private"  # private, team, public
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CollaborationMember:
    user_id: str
    design_space_id: str
    role: CollaborationRole
    joined_at: datetime
    last_active: Optional[datetime] = None
    permissions: Dict[str, bool] = field(default_factory=dict)

@dataclass
class DesignFile:
    id: str
    design_space_id: str
    filename: str
    file_path: str
    file_type: str
    size: int
    checksum: str
    version: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    locked_by: Optional[str] = None
    locked_at: Optional[datetime] = None

@dataclass
class DesignChange:
    id: str
    design_space_id: str
    file_id: Optional[str]
    user_id: str
    change_type: ChangeType
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    parent_change_id: Optional[str] = None

@dataclass
class Comment:
    id: str
    design_space_id: str
    file_id: Optional[str]
    user_id: str
    content: str
    position: Dict[str, Any]  # coordinates, line numbers, etc.
    timestamp: datetime
    parent_comment_id: Optional[str] = None
    resolved: bool = False

@dataclass
class ReviewRequest:
    id: str
    design_space_id: str
    created_by: str
    reviewer_id: str
    title: str
    description: str
    files: List[str]
    status: ReviewStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    feedback: Optional[str] = None

@dataclass
class RealTimeSession:
    session_id: str
    user_id: str
    design_space_id: str
    websocket: Any
    cursor_position: Dict[str, Any]
    last_activity: datetime
    active_file: Optional[str] = None

class DesignSpaceManager:
    def __init__(self, db_path: str = "design_spaces.db", storage_path: str = "design_files"):
        self.db_path = db_path
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.active_sessions: Dict[str, RealTimeSession] = {}
        self.change_queue: asyncio.Queue = asyncio.Queue()
        
    async def initialize_database(self):
        """Initialize the database with required tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Design spaces table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS design_spaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    status TEXT,
                    visibility TEXT,
                    tags TEXT,
                    metadata TEXT
                )
            """)
            
            # Collaboration members table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS collaboration_members (
                    user_id TEXT,
                    design_space_id TEXT,
                    role TEXT,
                    joined_at TIMESTAMP,
                    last_active TIMESTAMP,
                    permissions TEXT,
                    PRIMARY KEY (user_id, design_space_id)
                )
            """)
            
            # Design files table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS design_files (
                    id TEXT PRIMARY KEY,
                    design_space_id TEXT,
                    filename TEXT,
                    file_path TEXT,
                    file_type TEXT,
                    size INTEGER,
                    checksum TEXT,
                    version INTEGER,
                    created_by TEXT,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    locked_by TEXT,
                    locked_at TIMESTAMP
                )
            """)
            
            # Design changes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS design_changes (
                    id TEXT PRIMARY KEY,
                    design_space_id TEXT,
                    file_id TEXT,
                    user_id TEXT,
                    change_type TEXT,
                    description TEXT,
                    details TEXT,
                    timestamp TIMESTAMP,
                    parent_change_id TEXT
                )
            """)
            
            # Comments table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    design_space_id TEXT,
                    file_id TEXT,
                    user_id TEXT,
                    content TEXT,
                    position TEXT,
                    timestamp TIMESTAMP,
                    parent_comment_id TEXT,
                    resolved BOOLEAN
                )
            """)
            
            # Review requests table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS review_requests (
                    id TEXT PRIMARY KEY,
                    design_space_id TEXT,
                    created_by TEXT,
                    reviewer_id TEXT,
                    title TEXT,
                    description TEXT,
                    files TEXT,
                    status TEXT,
                    created_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    feedback TEXT
                )
            """)
            
            await db.commit()

    async def create_design_space(self, name: str, description: str, owner_id: str, 
                                visibility: str = "private", tags: List[str] = None) -> str:
        """Create a new design space"""
        space_id = str(uuid.uuid4())
        now = datetime.now()
        tags = tags or []
        
        space = DesignSpace(
            id=space_id,
            name=name,
            description=description,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            status=DesignStatus.DRAFT,
            visibility=visibility,
            tags=tags
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO design_spaces 
                (id, name, description, owner_id, created_at, updated_at, status, visibility, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                space.id, space.name, space.description, space.owner_id,
                space.created_at, space.updated_at, space.status.value,
                space.visibility, json.dumps(space.tags), json.dumps(space.metadata)
            ))
            
            # Add owner as admin
            await self.add_member(space_id, owner_id, CollaborationRole.OWNER)
            await db.commit()
        
        # Create storage directory
        space_path = self.storage_path / space_id
        space_path.mkdir(exist_ok=True)
        
        logger.info(f"Created design space: {space_id}")
        return space_id

    async def add_member(self, design_space_id: str, user_id: str, role: CollaborationRole,
                        permissions: Dict[str, bool] = None) -> bool:
        """Add a member to the design space"""
        permissions = permissions or self._get_default_permissions(role)
        now = datetime.now()
        
        member = CollaborationMember(
            user_id=user_id,
            design_space_id=design_space_id,
            role=role,
            joined_at=now,
            permissions=permissions
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO collaboration_members
                (user_id, design_space_id, role, joined_at, last_active, permissions)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                member.user_id, member.design_space_id, member.role.value,
                member.joined_at, member.last_active, json.dumps(member.permissions)
            ))
            await db.commit()
        
        logger.info(f"Added member {user_id} to design space {design_space_id}")
        return True

    async def upload_file(self, design_space_id: str, filename: str, file_content: bytes,
                         user_id: str) -> str:
        """Upload a file to the design space"""
        file_id = str(uuid.uuid4())
        file_type = Path(filename).suffix.lower()
        checksum = hashlib.sha256(file_content).hexdigest()
        
        # Store file
        space_path = self.storage_path / design_space_id
        space_path.mkdir(exist_ok=True)
        file_path = space_path / f"{file_id}_{filename}"
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        now = datetime.now()
        design_file = DesignFile(
            id=file_id,
            design_space_id=design_space_id,
            filename=filename,
            file_path=str(file_path),
            file_type=file_type,
            size=len(file_content),
            checksum=checksum,
            version=1,
            created_by=user_id,
            created_at=now,
            updated_at=now
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO design_files
                (id, design_space_id, filename, file_path, file_type, size, checksum,
                 version, created_by, created_at, updated_at, locked_by, locked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                design_file.id, design_file.design_space_id, design_file.filename,
                design_file.file_path, design_file.file_type, design_file.size,
                design_file.checksum, design_file.version, design_file.created_by,
                design_file.created_at, design_file.updated_at,
                design_file.locked_by, design_file.locked_at
            ))
            await db.commit()
        
        # Record change
        await self.record_change(design_space_id, file_id, user_id, ChangeType.CREATE,
                               f"Uploaded file: {filename}", {"file_size": len(file_content)})
        
        logger.info(f"Uploaded file {filename} to design space {design_space_id}")
        return file_id

    async def lock_file(self, file_id: str, user_id: str) -> bool:
        """Lock a file for exclusive editing"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if file is already locked
            cursor = await db.execute("""
                SELECT locked_by, locked_at FROM design_files WHERE id = ?
            """, (file_id,))
            result = await cursor.fetchone()
            
            if result and result[0] is not None:
                # Check if lock is stale (older than 30 minutes)
                locked_at = datetime.fromisoformat(result[1]) if result[1] else None
                if locked_at and datetime.now() - locked_at < timedelta(minutes=30):
                    return False  # File is locked by someone else
            
            # Lock the file
            now = datetime.now()
            await db.execute("""
                UPDATE design_files SET locked_by = ?, locked_at = ? WHERE id = ?
            """, (user_id, now, file_id))
            await db.commit()
        
        logger.info(f"Locked file {file_id} for user {user_id}")
        return True

    async def unlock_file(self, file_id: str, user_id: str) -> bool:
        """Unlock a file"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check if user has lock
            cursor = await db.execute("""
                SELECT locked_by FROM design_files WHERE id = ?
            """, (file_id,))
            result = await cursor.fetchone()
            
            if not result or result[0] != user_id:
                return False  # User doesn't have lock
            
            # Unlock the file
            await db.execute("""
                UPDATE design_files SET locked_by = NULL, locked_at = NULL WHERE id = ?
            """, (file_id,))
            await db.commit()
        
        logger.info(f"Unlocked file {file_id} by user {user_id}")
        return True

    async def add_comment(self, design_space_id: str, user_id: str, content: str,
                         file_id: Optional[str] = None, position: Dict[str, Any] = None,
                         parent_comment_id: Optional[str] = None) -> str:
        """Add a comment to a file or design space"""
        comment_id = str(uuid.uuid4())
        now = datetime.now()
        position = position or {}
        
        comment = Comment(
            id=comment_id,
            design_space_id=design_space_id,
            file_id=file_id,
            user_id=user_id,
            content=content,
            position=position,
            timestamp=now,
            parent_comment_id=parent_comment_id
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO comments
                (id, design_space_id, file_id, user_id, content, position,
                 timestamp, parent_comment_id, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment.id, comment.design_space_id, comment.file_id,
                comment.user_id, comment.content, json.dumps(comment.position),
                comment.timestamp, comment.parent_comment_id, comment.resolved
            ))
            await db.commit()
        
        # Record change
        await self.record_change(design_space_id, file_id, user_id, ChangeType.COMMENT,
                               "Added comment", {"comment_id": comment_id})
        
        # Notify real-time sessions
        await self._broadcast_to_space(design_space_id, {
            "type": "comment_added",
            "comment": asdict(comment)
        })
        
        logger.info(f"Added comment {comment_id} to design space {design_space_id}")
        return comment_id

    async def create_review_request(self, design_space_id: str, created_by: str,
                                  reviewer_id: str, title: str, description: str,
                                  files: List[str]) -> str:
        """Create a review request"""
        request_id = str(uuid.uuid4())
        now = datetime.now()
        
        review = ReviewRequest(
            id=request_id,
            design_space_id=design_space_id,
            created_by=created_by,
            reviewer_id=reviewer_id,
            title=title,
            description=description,
            files=files,
            status=ReviewStatus.PENDING,
            created_at=now
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO review_requests
                (id, design_space_id, created_by, reviewer_id, title, description,
                 files, status, created_at, completed_at, feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review.id, review.design_space_id, review.created_by,
                review.reviewer_id, review.title, review.description,
                json.dumps(review.files), review.status.value,
                review.created_at, review.completed_at, review.feedback
            ))
            await db.commit()
        
        logger.info(f"Created review request {request_id}")
        return request_id

    async def record_change(self, design_space_id: str, file_id: Optional[str],
                          user_id: str, change_type: ChangeType, description: str,
                          details: Dict[str, Any], parent_change_id: Optional[str] = None):
        """Record a design change"""
        change_id = str(uuid.uuid4())
        now = datetime.now()
        
        change = DesignChange(
            id=change_id,
            design_space_id=design_space_id,
            file_id=file_id,
            user_id=user_id,
            change_type=change_type,
            description=description,
            details=details,
            timestamp=now,
            parent_change_id=parent_change_id
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO design_changes
                (id, design_space_id, file_id, user_id, change_type, description,
                 details, timestamp, parent_change_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                change.id, change.design_space_id, change.file_id,
                change.user_id, change.change_type.value, change.description,
                json.dumps(change.details), change.timestamp, change.parent_change_id
            ))
            await db.commit()
        
        # Add to change queue for real-time updates
        await self.change_queue.put(change)

    async def get_design_space(self, space_id: str) -> Optional[DesignSpace]:
        """Get design space by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM design_spaces WHERE id = ?
            """, (space_id,))
            result = await cursor.fetchone()
            
            if result:
                return DesignSpace(
                    id=result[0],
                    name=result[1],
                    description=result[2],
                    owner_id=result[3],
                    created_at=datetime.fromisoformat(result[4]),
                    updated_at=datetime.fromisoformat(result[5]),
                    status=DesignStatus(result[6]),
                    visibility=result[7],
                    tags=json.loads(result[8]) if result[8] else [],
                    metadata=json.loads(result[9]) if result[9] else {}
                )
        return None

    async def get_recent_changes(self, design_space_id: str, limit: int = 50) -> List[DesignChange]:
        """Get recent changes in design space"""
        changes = []
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM design_changes 
                WHERE design_space_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (design_space_id, limit))
            results = await cursor.fetchall()
            
            for result in results:
                changes.append(DesignChange(
                    id=result[0],
                    design_space_id=result[1],
                    file_id=result[2],
                    user_id=result[3],
                    change_type=ChangeType(result[4]),
                    description=result[5],
                    details=json.loads(result[6]),
                    timestamp=datetime.fromisoformat(result[7]),
                    parent_change_id=result[8]
                ))
        
        return changes

    async def join_realtime_session(self, websocket, user_id: str, design_space_id: str) -> str:
        """Join a real-time collaboration session"""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = RealTimeSession(
            session_id=session_id,
            user_id=user_id,
            design_space_id=design_space_id,
            websocket=websocket,
            cursor_position={},
            last_activity=now
        )
        
        self.active_sessions[session_id] = session
        
        # Notify other sessions
        await self._broadcast_to_space(design_space_id, {
            "type": "user_joined",
            "user_id": user_id,
            "session_id": session_id
        }, exclude_session=session_id)
        
        logger.info(f"User {user_id} joined real-time session {session_id}")
        return session_id

    async def _broadcast_to_space(self, design_space_id: str, message: Dict[str, Any],
                                exclude_session: Optional[str] = None):
        """Broadcast message to all active sessions in a design space"""
        message_str = json.dumps(message)
        
        for session in self.active_sessions.values():
            if (session.design_space_id == design_space_id and 
                session.session_id != exclude_session):
                try:
                    await session.websocket.send(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting to session {session.session_id}: {e}")

    def _get_default_permissions(self, role: CollaborationRole) -> Dict[str, bool]:
        """Get default permissions for a role"""
        permissions = {
            "read": False,
            "write": False,
            "delete": False,
            "admin": False,
            "review": False,
            "comment": False
        }
        
        if role == CollaborationRole.OWNER:
            return {k: True for k in permissions.keys()}
        elif role == CollaborationRole.ADMIN:
            permissions.update({
                "read": True, "write": True, "delete": True, 
                "review": True, "comment": True
            })
        elif role == CollaborationRole.CONTRIBUTOR:
            permissions.update({
                "read": True, "write": True, "comment": True
            })
        elif role == CollaborationRole.REVIEWER:
            permissions.update({
                "read": True, "review": True, "comment": True
            })
        elif role == CollaborationRole.VIEWER:
            permissions.update({
                "read": True, "comment": True
            })
        
        return permissions

class CollaborativeDesignDashboard:
    def __init__(self, manager: DesignSpaceManager):
        self.manager = manager
    
    async def generate_activity_summary(self, design_space_id: str, days: int = 7) -> Dict[str, Any]:
        """Generate activity summary for dashboard"""
        changes = await self.manager.get_recent_changes(design_space_id, limit=1000)
        
        # Filter by time range
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_changes = [c for c in changes if c.timestamp >= cutoff_date]
        
        # Activity metrics
        total_changes = len(recent_changes)
        unique_contributors = len(set(c.user_id for c in recent_changes))
        
        change_types = {}
        for change in recent_changes:
            change_types[change.change_type.value] = change_types.get(change.change_type.value, 0) + 1
        
        # Daily activity
        daily_activity = {}
        for change in recent_changes:
            date_key = change.timestamp.date().isoformat()
            daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
        
        return {
            "period_days": days,
            "total_changes": total_changes,
            "unique_contributors": unique_contributors,
            "change_types": change_types,
            "daily_activity": daily_activity,
            "most_active_day": max(daily_activity.items(), key=lambda x: x[1]) if daily_activity else None
        }

async def main():
    """Demonstration of the collaborative design spaces system"""
    manager = DesignSpaceManager()
    dashboard = CollaborativeDesignDashboard(manager)
    
    # Initialize database
    await manager.initialize_database()
    
    print("=== Collaborative Design Spaces Demo ===")
    
    # Create a design space
    space_id = await manager.create_design_space(
        name="New Product Design",
        description="Collaborative space for new product development",
        owner_id="user_001",
        visibility="team",
        tags=["product", "mechanical", "prototype"]
    )
    print(f"Created design space: {space_id}")
    
    # Add team members
    await manager.add_member(space_id, "user_002", CollaborationRole.CONTRIBUTOR)
    await manager.add_member(space_id, "user_003", CollaborationRole.REVIEWER)
    print("Added team members")
    
    # Upload some design files
    sample_cad_content = b"# Sample CAD file content\nsolid test_part\n"
    file_id1 = await manager.upload_file(space_id, "main_assembly.step", sample_cad_content, "user_001")
    
    sample_doc_content = b"# Design Requirements\n1. Material: Aluminum\n2. Tolerance: +/-0.1mm"
    file_id2 = await manager.upload_file(space_id, "requirements.md", sample_doc_content, "user_002")
    
    print(f"Uploaded files: {file_id1}, {file_id2}")
    
    # Add comments
    comment_id = await manager.add_comment(
        design_space_id=space_id,
        user_id="user_003",
        content="This assembly looks good, but we should consider the manufacturing constraints.",
        file_id=file_id1,
        position={"line": 5, "column": 10}
    )
    print(f"Added comment: {comment_id}")
    
    # Create review request
    review_id = await manager.create_review_request(
        design_space_id=space_id,
        created_by="user_001",
        reviewer_id="user_003",
        title="Design Review for Main Assembly",
        description="Please review the main assembly design for manufacturability",
        files=[file_id1, file_id2]
    )
    print(f"Created review request: {review_id}")
    
    # Generate activity summary
    activity = await dashboard.generate_activity_summary(space_id, days=1)
    print(f"\nActivity Summary:")
    print(f"- Total changes: {activity['total_changes']}")
    print(f"- Contributors: {activity['unique_contributors']}")
    print(f"- Change types: {activity['change_types']}")
    
    # Show recent changes
    changes = await manager.get_recent_changes(space_id, limit=10)
    print(f"\nRecent Changes:")
    for change in changes:
        print(f"- {change.timestamp.strftime('%H:%M:%S')}: {change.description} by {change.user_id}")
    
    print("\n=== Demo completed successfully! ===")

if __name__ == "__main__":
    asyncio.run(main())