"""
Shared Context Manager
Provides unified context that can be passed between different models and agents
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class MessageRole(Enum):
    """Message roles in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class TaskStatus(Enum):
    """Status of a task or subtask"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class ContextMessage:
    """A single message in the context"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            'role': self.role.value,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'model': self.model,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ContextMessage':
        """Create from dictionary"""
        return cls(
            role=MessageRole(data['role']),
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            model=data.get('model'),
            metadata=data.get('metadata', {})
        )


@dataclass
class SubTask:
    """A decomposed subtask"""
    id: str
    parent_id: Optional[str]
    description: str
    status: TaskStatus
    assigned_model: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'parent_id': self.parent_id,
            'description': self.description,
            'status': self.status.value,
            'assigned_model': self.assigned_model,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'dependencies': self.dependencies,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'SubTask':
        """Create from dictionary"""
        return cls(
            id=data['id'],
            parent_id=data.get('parent_id'),
            description=data['description'],
            status=TaskStatus(data['status']),
            assigned_model=data.get('assigned_model'),
            result=data.get('result'),
            error=data.get('error'),
            created_at=datetime.fromisoformat(data['created_at']),
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            dependencies=data.get('dependencies', []),
            metadata=data.get('metadata', {})
        )


@dataclass
class SharedContext:
    """
    Shared context that can be passed between models
    Contains conversation history, task state, and intermediate results
    """
    session_id: str
    messages: List[ContextMessage] = field(default_factory=list)
    tasks: Dict[str, SubTask] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)  # Intermediate results
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_message(self, role: MessageRole, content: str, model: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> ContextMessage:
        """Add a message to the context"""
        msg = ContextMessage(
            role=role,
            content=content,
            model=model,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.updated_at = datetime.now()
        return msg

    def add_task(self, task: SubTask):
        """Add a task to the context"""
        self.tasks[task.id] = task
        self.updated_at = datetime.now()

    def update_task_status(self, task_id: str, status: TaskStatus,
                          result: Optional[str] = None, error: Optional[str] = None):
        """Update task status"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status

            if status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now()
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                task.completed_at = datetime.now()

            if result:
                task.result = result
            if error:
                task.error = error

            self.updated_at = datetime.now()

    def get_task(self, task_id: str) -> Optional[SubTask]:
        """Get a task by ID"""
        return self.tasks.get(task_id)

    def get_pending_tasks(self) -> List[SubTask]:
        """Get all pending tasks that have dependencies met"""
        pending = []
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                # Check if dependencies are met
                deps_met = all(
                    self.tasks.get(dep_id, SubTask(id='', parent_id=None, description='', status=TaskStatus.FAILED)).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if deps_met:
                    pending.append(task)
        return pending

    def get_completed_tasks(self) -> List[SubTask]:
        """Get all completed tasks"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]

    def get_failed_tasks(self) -> List[SubTask]:
        """Get all failed tasks"""
        return [t for t in self.tasks.values() if t.status == TaskStatus.FAILED]

    def store_artifact(self, key: str, value: Any):
        """Store an intermediate result or artifact"""
        self.artifacts[key] = value
        self.updated_at = datetime.now()

    def get_artifact(self, key: str) -> Optional[Any]:
        """Get a stored artifact"""
        return self.artifacts.get(key)

    def get_recent_messages(self, n: int = 10) -> List[ContextMessage]:
        """Get the N most recent messages"""
        return self.messages[-n:] if len(self.messages) > n else self.messages

    def get_conversation_summary(self) -> str:
        """Generate a summary of the conversation so far"""
        summary_parts = []

        # Add recent conversation
        recent = self.get_recent_messages(5)
        if recent:
            summary_parts.append("## Recent Conversation")
            for msg in recent:
                role = msg.role.value.upper()
                content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                summary_parts.append(f"{role}: {content_preview}")

        # Add task status
        if self.tasks:
            completed = self.get_completed_tasks()
            pending = self.get_pending_tasks()
            failed = self.get_failed_tasks()

            summary_parts.append("\n## Task Status")
            summary_parts.append(f"Completed: {len(completed)}")
            summary_parts.append(f"Pending: {len(pending)}")
            summary_parts.append(f"Failed: {len(failed)}")

            if completed:
                summary_parts.append("\n### Completed Tasks:")
                for task in completed[-3:]:  # Last 3 completed
                    summary_parts.append(f"- {task.description}")
                    if task.result:
                        result_preview = task.result[:100] + "..." if len(task.result) > 100 else task.result
                        summary_parts.append(f"  Result: {result_preview}")

        # Add artifacts
        if self.artifacts:
            summary_parts.append(f"\n## Artifacts: {len(self.artifacts)} stored")
            for key in list(self.artifacts.keys())[:3]:  # First 3
                summary_parts.append(f"- {key}")

        return "\n".join(summary_parts)

    def get_context_for_model(self, include_system_prompt: bool = True) -> List[Dict[str, str]]:
        """
        Get context formatted for model consumption
        Returns list of message dicts compatible with most LLM APIs
        """
        formatted = []

        if include_system_prompt:
            system_context = self.get_conversation_summary()
            formatted.append({
                'role': 'system',
                'content': f"Context from previous interactions:\n\n{system_context}"
            })

        # Add conversation messages
        for msg in self.messages:
            if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]:
                formatted.append({
                    'role': msg.role.value,
                    'content': msg.content
                })

        return formatted

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            'session_id': self.session_id,
            'messages': [m.to_dict() for m in self.messages],
            'tasks': {k: v.to_dict() for k, v in self.tasks.items()},
            'artifacts': self.artifacts,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'SharedContext':
        """Deserialize from dictionary"""
        return cls(
            session_id=data['session_id'],
            messages=[ContextMessage.from_dict(m) for m in data.get('messages', [])],
            tasks={k: SubTask.from_dict(v) for k, v in data.get('tasks', {}).items()},
            artifacts=data.get('artifacts', {}),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'SharedContext':
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))


class ContextManager:
    """
    Manages shared contexts across the application
    Provides context persistence and retrieval
    """

    def __init__(self, persist_dir: str = "./contexts"):
        self.persist_dir = persist_dir
        self.active_contexts: Dict[str, SharedContext] = {}

        # Create persist directory if needed
        import os
        os.makedirs(persist_dir, exist_ok=True)

    def create_context(self, session_id: str) -> SharedContext:
        """Create a new shared context"""
        context = SharedContext(session_id=session_id)
        self.active_contexts[session_id] = context
        return context

    def get_context(self, session_id: str) -> Optional[SharedContext]:
        """Get an active context"""
        return self.active_contexts.get(session_id)

    def save_context(self, session_id: str):
        """Persist context to disk"""
        context = self.active_contexts.get(session_id)
        if context:
            import os
            filepath = os.path.join(self.persist_dir, f"{session_id}.json")
            with open(filepath, 'w') as f:
                f.write(context.to_json())

    def load_context(self, session_id: str) -> Optional[SharedContext]:
        """Load context from disk"""
        import os
        filepath = os.path.join(self.persist_dir, f"{session_id}.json")

        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                context = SharedContext.from_json(f.read())
                self.active_contexts[session_id] = context
                return context

        return None

    def clear_context(self, session_id: str):
        """Clear an active context"""
        if session_id in self.active_contexts:
            del self.active_contexts[session_id]
