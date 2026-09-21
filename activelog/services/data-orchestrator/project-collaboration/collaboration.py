#!/usr/bin/env python3
"""
Project Collaboration System
Real-time collaborative platform for project management and team coordination
"""

import os
import json
import asyncio
import logging
import websockets
from typing import Dict, List, Optional, Tuple, Any, Callable, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import threading
from datetime import datetime, timedelta
import uuid
import hashlib
from concurrent.futures import ThreadPoolExecutor
import weakref


class UserRole(Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"
    GUEST = "guest"


class ProjectStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class TaskStatus(Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageType(Enum):
    TEXT = "text"
    FILE = "file"
    SYSTEM = "system"
    TASK_UPDATE = "task_update"
    STATUS_CHANGE = "status_change"


class NotificationType(Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_UPDATED = "task_updated"
    COMMENT_ADDED = "comment_added"
    FILE_SHARED = "file_shared"
    DEADLINE_APPROACHING = "deadline_approaching"
    PROJECT_STATUS_CHANGED = "project_status_changed"


@dataclass
class User:
    id: str
    username: str
    email: str
    full_name: str
    avatar_url: Optional[str] = None
    timezone: str = "UTC"
    created_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    is_online: bool = False


@dataclass
class Project:
    id: str
    name: str
    description: str
    owner_id: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    id: str
    project_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_by: str
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)


@dataclass
class Comment:
    id: str
    project_id: str
    task_id: Optional[str]
    user_id: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    parent_id: Optional[str] = None
    attachments: List[str] = field(default_factory=list)


@dataclass
class Message:
    id: str
    project_id: str
    user_id: str
    message_type: MessageType
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Notification:
    id: str
    user_id: str
    project_id: str
    notification_type: NotificationType
    title: str
    content: str
    created_at: datetime
    read: bool = False
    data: Dict[str, Any] = field(default_factory=dict)


class CollaborationDatabase:
    def __init__(self, db_path: str = "collaboration.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                avatar_url TEXT,
                timezone TEXT DEFAULT 'UTC',
                created_at TEXT,
                last_active TEXT,
                is_online BOOLEAN DEFAULT FALSE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                owner_id TEXT,
                status TEXT DEFAULT 'draft',
                created_at TEXT,
                updated_at TEXT,
                start_date TEXT,
                end_date TEXT,
                budget REAL,
                tags TEXT,
                settings TEXT,
                FOREIGN KEY (owner_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_members (
                project_id TEXT,
                user_id TEXT,
                role TEXT,
                joined_at TEXT,
                PRIMARY KEY (project_id, user_id),
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                created_by TEXT,
                assigned_to TEXT,
                created_at TEXT,
                updated_at TEXT,
                due_date TEXT,
                estimated_hours REAL,
                actual_hours REAL,
                dependencies TEXT,
                tags TEXT,
                attachments TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (created_by) REFERENCES users (id),
                FOREIGN KEY (assigned_to) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                task_id TEXT,
                user_id TEXT,
                content TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT,
                parent_id TEXT,
                attachments TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (task_id) REFERENCES tasks (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                user_id TEXT,
                message_type TEXT,
                content TEXT NOT NULL,
                created_at TEXT,
                metadata TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                project_id TEXT,
                notification_type TEXT,
                title TEXT,
                content TEXT,
                created_at TEXT,
                read BOOLEAN DEFAULT FALSE,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                user_id TEXT,
                action TEXT,
                entity_type TEXT,
                entity_id TEXT,
                details TEXT,
                created_at TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks(assigned_to)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_project ON activity_logs(project_id)")
        
        conn.commit()
        conn.close()
    
    def add_user(self, user: User) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO users
            (id, username, email, full_name, avatar_url, timezone, created_at, last_active, is_online)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.id, user.username, user.email, user.full_name, user.avatar_url,
            user.timezone, user.created_at.isoformat(), user.last_active.isoformat(), user.is_online
        ))
        
        conn.commit()
        conn.close()
        return user.id
    
    def add_project(self, project: Project) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO projects
            (id, name, description, owner_id, status, created_at, updated_at,
             start_date, end_date, budget, tags, settings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project.id, project.name, project.description, project.owner_id,
            project.status.value, project.created_at.isoformat(), project.updated_at.isoformat(),
            project.start_date.isoformat() if project.start_date else None,
            project.end_date.isoformat() if project.end_date else None,
            project.budget, json.dumps(project.tags), json.dumps(project.settings)
        ))
        
        conn.commit()
        conn.close()
        return project.id
    
    def add_task(self, task: Task) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO tasks
            (id, project_id, title, description, status, priority, created_by, assigned_to,
             created_at, updated_at, due_date, estimated_hours, actual_hours, dependencies, tags, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id, task.project_id, task.title, task.description, task.status.value,
            task.priority.value, task.created_by, task.assigned_to,
            task.created_at.isoformat(), task.updated_at.isoformat(),
            task.due_date.isoformat() if task.due_date else None,
            task.estimated_hours, task.actual_hours,
            json.dumps(task.dependencies), json.dumps(task.tags), json.dumps(task.attachments)
        ))
        
        conn.commit()
        conn.close()
        return task.id
    
    def get_project_tasks(self, project_id: str) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_user_projects(self, user_id: str) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.*, pm.role FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            WHERE p.owner_id = ? OR pm.user_id = ?
            ORDER BY p.updated_at DESC
        """, (user_id, user_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def add_project_member(self, project_id: str, user_id: str, role: UserRole) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO project_members (project_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            """, (project_id, user_id, role.value, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False


class RealTimeManager:
    def __init__(self):
        self.clients: Dict[str, Set[websockets.WebSocketServerProtocol]] = {}
        self.user_connections: Dict[str, str] = {}  # websocket -> user_id
        self.project_subscriptions: Dict[str, Set[str]] = {}  # project_id -> set of user_ids
        self.server = None
        self.host = "localhost"
        self.port = 8765
    
    async def start_server(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client, self.host, self.port
            )
            logging.info(f"Real-time server started on ws://{self.host}:{self.port}")
            return self.server
        except Exception as e:
            logging.error(f"Failed to start real-time server: {e}")
            return None
    
    async def handle_client(self, websocket, path):
        """Handle new WebSocket client connection"""
        client_id = str(uuid.uuid4())
        logging.info(f"Client connected: {client_id}")
        
        try:
            # Wait for authentication
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            if auth_data.get('type') == 'auth':
                user_id = auth_data.get('user_id')
                if user_id:
                    self.user_connections[client_id] = user_id
                    if user_id not in self.clients:
                        self.clients[user_id] = set()
                    self.clients[user_id].add(websocket)
                    
                    # Send authentication confirmation
                    await websocket.send(json.dumps({
                        'type': 'auth_success',
                        'client_id': client_id
                    }))
                    
                    # Handle client messages
                    async for message in websocket:
                        await self.handle_message(user_id, message)
            
        except websockets.exceptions.ConnectionClosed:
            logging.info(f"Client disconnected: {client_id}")
        except Exception as e:
            logging.error(f"Client connection error: {e}")
        finally:
            # Clean up
            if client_id in self.user_connections:
                user_id = self.user_connections[client_id]
                if user_id in self.clients:
                    self.clients[user_id].discard(websocket)
                    if not self.clients[user_id]:
                        del self.clients[user_id]
                del self.user_connections[client_id]
    
    async def handle_message(self, user_id: str, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe_project':
                project_id = data.get('project_id')
                if project_id:
                    if project_id not in self.project_subscriptions:
                        self.project_subscriptions[project_id] = set()
                    self.project_subscriptions[project_id].add(user_id)
            
            elif message_type == 'unsubscribe_project':
                project_id = data.get('project_id')
                if project_id and project_id in self.project_subscriptions:
                    self.project_subscriptions[project_id].discard(user_id)
            
            elif message_type == 'task_update':
                await self.broadcast_task_update(data)
            
            elif message_type == 'chat_message':
                await self.broadcast_chat_message(data)
            
        except json.JSONDecodeError:
            logging.warning(f"Invalid JSON message from user {user_id}")
        except Exception as e:
            logging.error(f"Error handling message from user {user_id}: {e}")
    
    async def broadcast_task_update(self, update_data: Dict[str, Any]):
        """Broadcast task update to project subscribers"""
        project_id = update_data.get('project_id')
        if project_id in self.project_subscriptions:
            subscribers = self.project_subscriptions[project_id]
            message = json.dumps(update_data)
            
            for user_id in subscribers:
                if user_id in self.clients:
                    # Send to all connections for this user
                    for websocket in self.clients[user_id].copy():
                        try:
                            await websocket.send(message)
                        except websockets.exceptions.ConnectionClosed:
                            self.clients[user_id].discard(websocket)
    
    async def broadcast_chat_message(self, message_data: Dict[str, Any]):
        """Broadcast chat message to project subscribers"""
        project_id = message_data.get('project_id')
        if project_id in self.project_subscriptions:
            subscribers = self.project_subscriptions[project_id]
            message = json.dumps(message_data)
            
            for user_id in subscribers:
                if user_id in self.clients:
                    for websocket in self.clients[user_id].copy():
                        try:
                            await websocket.send(message)
                        except websockets.exceptions.ConnectionClosed:
                            self.clients[user_id].discard(websocket)
    
    async def notify_user(self, user_id: str, notification_data: Dict[str, Any]):
        """Send notification to specific user"""
        if user_id in self.clients:
            message = json.dumps({
                'type': 'notification',
                **notification_data
            })
            
            for websocket in self.clients[user_id].copy():
                try:
                    await websocket.send(message)
                except websockets.exceptions.ConnectionClosed:
                    self.clients[user_id].discard(websocket)
    
    def get_online_users(self, project_id: str = None) -> List[str]:
        """Get list of online users, optionally filtered by project"""
        if project_id and project_id in self.project_subscriptions:
            return list(self.project_subscriptions[project_id])
        return list(self.clients.keys())
    
    async def stop_server(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logging.info("Real-time server stopped")


class NotificationManager:
    def __init__(self, database: CollaborationDatabase, real_time: RealTimeManager):
        self.database = database
        self.real_time = real_time
    
    async def create_notification(self, notification: Notification):
        """Create and send notification"""
        # Store in database
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO notifications
            (id, user_id, project_id, notification_type, title, content, created_at, read, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notification.id, notification.user_id, notification.project_id,
            notification.notification_type.value, notification.title, notification.content,
            notification.created_at.isoformat(), notification.read, json.dumps(notification.data)
        ))
        
        conn.commit()
        conn.close()
        
        # Send real-time notification
        await self.real_time.notify_user(notification.user_id, {
            'id': notification.id,
            'type': notification.notification_type.value,
            'title': notification.title,
            'content': notification.content,
            'project_id': notification.project_id,
            'created_at': notification.created_at.isoformat(),
            'data': notification.data
        })
    
    async def notify_task_assignment(self, task: Task, assigned_by: str):
        """Notify user about task assignment"""
        if task.assigned_to:
            notification = Notification(
                id=str(uuid.uuid4()),
                user_id=task.assigned_to,
                project_id=task.project_id,
                notification_type=NotificationType.TASK_ASSIGNED,
                title="New Task Assignment",
                content=f"You have been assigned to task: {task.title}",
                created_at=datetime.now(),
                data={
                    'task_id': task.id,
                    'assigned_by': assigned_by
                }
            )
            await self.create_notification(notification)
    
    async def notify_comment_added(self, comment: Comment, project_members: List[str]):
        """Notify project members about new comment"""
        for user_id in project_members:
            if user_id != comment.user_id:  # Don't notify the commenter
                notification = Notification(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    project_id=comment.project_id,
                    notification_type=NotificationType.COMMENT_ADDED,
                    title="New Comment",
                    content=f"New comment added to {'task' if comment.task_id else 'project'}",
                    created_at=datetime.now(),
                    data={
                        'comment_id': comment.id,
                        'task_id': comment.task_id
                    }
                )
                await self.create_notification(notification)


class ActivityLogger:
    def __init__(self, database: CollaborationDatabase):
        self.database = database
    
    async def log_activity(self, project_id: str, user_id: str, action: str,
                          entity_type: str, entity_id: str, details: Dict[str, Any] = None):
        """Log activity to database"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        activity_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO activity_logs
            (id, project_id, user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            activity_id, project_id, user_id, action, entity_type, entity_id,
            json.dumps(details or {}), datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_project_activity(self, project_id: str, limit: int = 50) -> List[Dict]:
        """Get recent activity for a project"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT al.*, u.username FROM activity_logs al
            JOIN users u ON al.user_id = u.id
            WHERE al.project_id = ?
            ORDER BY al.created_at DESC
            LIMIT ?
        """, (project_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


class ProjectCollaborationSystem:
    def __init__(self, data_dir: str = "collaboration_data"):
        self.data_dir = data_dir
        self.database = CollaborationDatabase()
        self.real_time = RealTimeManager()
        self.notifications = NotificationManager(self.database, self.real_time)
        self.activity_logger = ActivityLogger(self.database)
        
        # Callbacks
        self.on_project_created: Optional[Callable] = None
        self.on_task_updated: Optional[Callable] = None
        self.on_user_joined: Optional[Callable] = None
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        logging.info("Project Collaboration System initialized")
    
    async def start_real_time_server(self):
        """Start the real-time WebSocket server"""
        server = await self.real_time.start_server()
        return server
    
    async def create_project(self, project_data: Dict[str, Any]) -> str:
        """Create a new project"""
        project = Project(
            id=str(uuid.uuid4()),
            name=project_data['name'],
            description=project_data.get('description', ''),
            owner_id=project_data['owner_id'],
            status=ProjectStatus(project_data.get('status', 'draft')),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            start_date=datetime.fromisoformat(project_data['start_date']) if project_data.get('start_date') else None,
            end_date=datetime.fromisoformat(project_data['end_date']) if project_data.get('end_date') else None,
            budget=project_data.get('budget'),
            tags=project_data.get('tags', []),
            settings=project_data.get('settings', {})
        )
        
        project_id = self.database.add_project(project)
        
        # Add owner as project admin
        self.database.add_project_member(project_id, project.owner_id, UserRole.ADMIN)
        
        # Log activity
        await self.activity_logger.log_activity(
            project_id, project.owner_id, "create", "project", project_id,
            {"project_name": project.name}
        )
        
        # Trigger callback
        if self.on_project_created:
            self.on_project_created(project)
        
        logging.info(f"Project created: {project.name} ({project_id})")
        return project_id
    
    async def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new task"""
        task = Task(
            id=str(uuid.uuid4()),
            project_id=task_data['project_id'],
            title=task_data['title'],
            description=task_data.get('description', ''),
            status=TaskStatus(task_data.get('status', 'todo')),
            priority=TaskPriority(task_data.get('priority', 'medium')),
            created_by=task_data['created_by'],
            assigned_to=task_data.get('assigned_to'),
            due_date=datetime.fromisoformat(task_data['due_date']) if task_data.get('due_date') else None,
            estimated_hours=task_data.get('estimated_hours'),
            dependencies=task_data.get('dependencies', []),
            tags=task_data.get('tags', [])
        )
        
        task_id = self.database.add_task(task)
        
        # Notify assigned user
        if task.assigned_to:
            await self.notifications.notify_task_assignment(task, task.created_by)
        
        # Broadcast real-time update
        await self.real_time.broadcast_task_update({
            'type': 'task_created',
            'project_id': task.project_id,
            'task': asdict(task)
        })
        
        # Log activity
        await self.activity_logger.log_activity(
            task.project_id, task.created_by, "create", "task", task_id,
            {"task_title": task.title, "assigned_to": task.assigned_to}
        )
        
        return task_id
    
    async def update_task(self, task_id: str, updates: Dict[str, Any], updated_by: str) -> bool:
        """Update an existing task"""
        try:
            # Get current task
            conn = sqlite3.connect(self.database.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            current_task_data = cursor.fetchone()
            if not current_task_data:
                conn.close()
                return False
            
            # Apply updates
            update_fields = []
            update_values = []
            
            for field, value in updates.items():
                if field in ['status', 'priority', 'assigned_to', 'title', 'description', 'due_date']:
                    update_fields.append(f"{field} = ?")
                    if field == 'due_date' and value:
                        update_values.append(datetime.fromisoformat(value).isoformat())
                    else:
                        update_values.append(value)
            
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now().isoformat())
            update_values.append(task_id)
            
            cursor.execute(f"""
                UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?
            """, update_values)
            
            conn.commit()
            conn.close()
            
            # Get updated task data
            conn = sqlite3.connect(self.database.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            updated_task_data = cursor.fetchone()
            conn.close()
            
            # Broadcast real-time update
            if updated_task_data:
                task_dict = dict(zip([col[0] for col in cursor.description], updated_task_data))
                await self.real_time.broadcast_task_update({
                    'type': 'task_updated',
                    'project_id': task_dict['project_id'],
                    'task_id': task_id,
                    'updates': updates,
                    'updated_by': updated_by
                })
            
            # Log activity
            await self.activity_logger.log_activity(
                task_dict['project_id'], updated_by, "update", "task", task_id,
                {"updates": updates}
            )
            
            # Trigger callback
            if self.on_task_updated:
                self.on_task_updated(task_id, updates)
            
            return True
            
        except Exception as e:
            logging.error(f"Error updating task {task_id}: {e}")
            return False
    
    async def add_comment(self, comment_data: Dict[str, Any]) -> str:
        """Add a comment to a task or project"""
        comment = Comment(
            id=str(uuid.uuid4()),
            project_id=comment_data['project_id'],
            task_id=comment_data.get('task_id'),
            user_id=comment_data['user_id'],
            content=comment_data['content'],
            created_at=datetime.now(),
            parent_id=comment_data.get('parent_id'),
            attachments=comment_data.get('attachments', [])
        )
        
        # Store in database
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO comments
            (id, project_id, task_id, user_id, content, created_at, updated_at, parent_id, attachments)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            comment.id, comment.project_id, comment.task_id, comment.user_id,
            comment.content, comment.created_at.isoformat(), None,
            comment.parent_id, json.dumps(comment.attachments)
        ))
        
        conn.commit()
        conn.close()
        
        # Get project members for notifications
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM project_members WHERE project_id = ?", (comment.project_id,))
        project_members = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        # Send notifications
        await self.notifications.notify_comment_added(comment, project_members)
        
        # Broadcast real-time update
        await self.real_time.broadcast_chat_message({
            'type': 'comment_added',
            'project_id': comment.project_id,
            'comment': asdict(comment)
        })
        
        # Log activity
        await self.activity_logger.log_activity(
            comment.project_id, comment.user_id, "comment", 
            "task" if comment.task_id else "project",
            comment.task_id or comment.project_id,
            {"comment_id": comment.id}
        )
        
        return comment.id
    
    async def join_project(self, project_id: str, user_id: str, role: UserRole = UserRole.CONTRIBUTOR) -> bool:
        """Add a user to a project"""
        success = self.database.add_project_member(project_id, user_id, role)
        
        if success:
            # Log activity
            await self.activity_logger.log_activity(
                project_id, user_id, "join", "project", project_id,
                {"role": role.value}
            )
            
            # Trigger callback
            if self.on_user_joined:
                self.on_user_joined(project_id, user_id, role)
            
            logging.info(f"User {user_id} joined project {project_id} as {role.value}")
        
        return success
    
    def get_project_dashboard(self, project_id: str) -> Dict[str, Any]:
        """Get project dashboard data"""
        # Get project info
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project_data = cursor.fetchone()
        
        # Get task statistics
        cursor.execute("""
            SELECT status, COUNT(*) FROM tasks WHERE project_id = ? GROUP BY status
        """, (project_id,))
        task_stats = dict(cursor.fetchall())
        
        # Get recent activity
        cursor.execute("""
            SELECT al.*, u.username FROM activity_logs al
            JOIN users u ON al.user_id = u.id
            WHERE al.project_id = ?
            ORDER BY al.created_at DESC
            LIMIT 10
        """, (project_id,))
        recent_activity = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        # Get project members
        cursor.execute("""
            SELECT u.id, u.username, u.full_name, pm.role FROM users u
            JOIN project_members pm ON u.id = pm.user_id
            WHERE pm.project_id = ?
        """, (project_id,))
        members = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        conn.close()
        
        # Get online members
        online_users = self.real_time.get_online_users(project_id)
        
        if project_data:
            project_dict = dict(zip([col[0] for col in cursor.description], project_data))
            return {
                'project': project_dict,
                'task_statistics': task_stats,
                'recent_activity': recent_activity,
                'members': members,
                'online_members': online_users,
                'generated_at': datetime.now().isoformat()
            }
        
        return {}
    
    def get_user_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Get user dashboard data"""
        projects = self.database.get_user_projects(user_id)
        
        # Get assigned tasks
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.*, p.name as project_name FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.assigned_to = ? AND t.status != 'done'
            ORDER BY t.due_date ASC, t.priority DESC
        """, (user_id,))
        
        assigned_tasks = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        # Get recent notifications
        cursor.execute("""
            SELECT * FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (user_id,))
        
        notifications = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'projects': projects,
            'assigned_tasks': assigned_tasks,
            'notifications': notifications,
            'generated_at': datetime.now().isoformat()
        }
    
    def search_projects(self, query: str, user_id: str = None) -> List[Dict]:
        """Search projects"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM projects WHERE name LIKE ? OR description LIKE ?"
        params = [f"%{query}%", f"%{query}%"]
        
        if user_id:
            sql += " AND (owner_id = ? OR id IN (SELECT project_id FROM project_members WHERE user_id = ?))"
            params.extend([user_id, user_id])
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    async def export_project_data(self, project_id: str) -> Optional[str]:
        """Export project data to JSON file"""
        try:
            dashboard_data = self.get_project_dashboard(project_id)
            tasks = self.database.get_project_tasks(project_id)
            activity = self.activity_logger.get_project_activity(project_id, 100)
            
            export_data = {
                'dashboard': dashboard_data,
                'tasks': tasks,
                'activity': activity,
                'exported_at': datetime.now().isoformat()
            }
            
            export_path = os.path.join(self.data_dir, f"project_{project_id}_export.json")
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            return export_path
            
        except Exception as e:
            logging.error(f"Error exporting project data: {e}")
            return None


# Demo function
async def demo_project_collaboration():
    """Demonstrate Project Collaboration System functionality"""
    print("=== Project Collaboration System Demo ===")
    
    collaboration = ProjectCollaborationSystem()
    
    # Set up callbacks
    collaboration.on_project_created = lambda proj: print(f"Project created: {proj.name}")
    collaboration.on_task_updated = lambda task_id, updates: print(f"Task updated: {task_id}")
    collaboration.on_user_joined = lambda proj_id, user_id, role: print(f"User joined: {user_id} as {role.value}")
    
    # Create sample users
    users = [
        User("user1", "alice", "alice@example.com", "Alice Johnson"),
        User("user2", "bob", "bob@example.com", "Bob Smith"),
        User("user3", "charlie", "charlie@example.com", "Charlie Brown")
    ]
    
    for user in users:
        collaboration.database.add_user(user)
    
    # Create sample project
    project_data = {
        'name': 'Product Development Project',
        'description': 'Development of new product line',
        'owner_id': 'user1',
        'status': 'active',
        'start_date': datetime.now().isoformat(),
        'end_date': (datetime.now() + timedelta(days=90)).isoformat(),
        'budget': 50000.0,
        'tags': ['product', 'development', 'priority']
    }
    
    project_id = await collaboration.create_project(project_data)
    
    # Add project members
    await collaboration.join_project(project_id, "user2", UserRole.CONTRIBUTOR)
    await collaboration.join_project(project_id, "user3", UserRole.VIEWER)
    
    # Create sample tasks
    tasks_data = [
        {
            'project_id': project_id,
            'title': 'Research market requirements',
            'description': 'Analyze market needs and competition',
            'created_by': 'user1',
            'assigned_to': 'user2',
            'priority': 'high',
            'due_date': (datetime.now() + timedelta(days=7)).isoformat()
        },
        {
            'project_id': project_id,
            'title': 'Create initial prototypes',
            'description': 'Build first working prototypes',
            'created_by': 'user1',
            'assigned_to': 'user2',
            'priority': 'medium',
            'due_date': (datetime.now() + timedelta(days=21)).isoformat()
        }
    ]
    
    for task_data in tasks_data:
        await collaboration.create_task(task_data)
    
    # Add comments
    await collaboration.add_comment({
        'project_id': project_id,
        'user_id': 'user1',
        'content': 'Great progress on the project so far!'
    })
    
    # Get project dashboard
    dashboard = collaboration.get_project_dashboard(project_id)
    print(f"Project dashboard generated with {len(dashboard.get('members', []))} members")
    
    # Get user dashboard
    user_dashboard = collaboration.get_user_dashboard('user2')
    print(f"User dashboard shows {len(user_dashboard.get('assigned_tasks', []))} assigned tasks")
    
    # Export project data
    export_path = await collaboration.export_project_data(project_id)
    print(f"Project data exported to: {export_path}")
    
    print("Project Collaboration System demo completed")


if __name__ == "__main__":
    asyncio.run(demo_project_collaboration())