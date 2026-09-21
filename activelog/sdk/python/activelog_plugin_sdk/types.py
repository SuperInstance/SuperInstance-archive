"""
ActiveLog Plugin SDK - Type definitions for Python
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Awaitable
import asyncio

# Base exception classes
class PluginError(Exception):
    """Base exception for plugin-related errors"""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class PermissionError(PluginError):
    """Exception raised when plugin lacks required permissions"""
    
    def __init__(self, permission: str):
        super().__init__(f"Permission denied: {permission}", "PERMISSION_DENIED", {"permission": permission})


class ResourceLimitError(PluginError):
    """Exception raised when plugin exceeds resource limits"""
    
    def __init__(self, resource: str, limit: str):
        super().__init__(f"Resource limit exceeded: {resource} ({limit})", "RESOURCE_LIMIT", {"resource": resource, "limit": limit})


class ValidationError(PluginError):
    """Exception raised for validation errors"""
    
    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error: {field} - {message}", "VALIDATION_ERROR", {"field": field})


# Enums
class PluginCategory(str, Enum):
    DATA_IMPORT = "data-import"
    DATA_EXPORT = "data-export"
    ANALYTICS = "analytics"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    UTILITY = "utility"
    VISUALIZATION = "visualization"
    AI_ML = "ai-ml"
    SECURITY = "security"
    PRODUCTIVITY = "productivity"


class RuntimeType(str, Enum):
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    DOCKER = "docker"
    WASM = "wasm"


class RuntimeEnvironment(str, Enum):
    NODE = "node"
    BROWSER = "browser"
    PYTHON3 = "python3"
    DOCKER = "docker"
    WASM = "wasm"


class TriggerType(str, Enum):
    FILE_UPLOAD = "file-upload"
    FILE_CHANGE = "file-change"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    USER_ACTION = "user-action"
    SYSTEM_EVENT = "system-event"


class ActiveLogService(str, Enum):
    AUTH = "auth"
    METADATA = "metadata"
    FILE_SYNC = "file-sync"
    AI_ORCHESTRATOR = "ai-orchestrator"
    VIDEO_PIPELINE = "video-pipeline"
    ANALYTICS = "analytics"
    NOTIFICATIONS = "notifications"


# Data classes
@dataclass
class PluginAuthor:
    name: str
    email: Optional[str] = None
    url: Optional[str] = None


@dataclass
class PluginRuntime:
    type: RuntimeType
    version: Optional[str] = None
    environment: Optional[RuntimeEnvironment] = None


@dataclass
class NetworkPermissions:
    enabled: bool = False
    domains: List[str] = field(default_factory=list)
    ports: List[int] = field(default_factory=list)


@dataclass
class FilesystemPermissions:
    read: List[str] = field(default_factory=list)
    write: List[str] = field(default_factory=list)
    temp: bool = True


@dataclass
class DatabasePermissions:
    read: bool = False
    write: bool = False
    tables: List[str] = field(default_factory=list)


@dataclass
class PluginPermissions:
    network: Optional[NetworkPermissions] = None
    filesystem: Optional[FilesystemPermissions] = None
    database: Optional[DatabasePermissions] = None
    services: List[ActiveLogService] = field(default_factory=list)


@dataclass
class PluginResources:
    cpu: float = 0.5
    memory: str = "256MB"
    disk: str = "100MB"
    network: str = "10MB"
    timeout: int = 60


@dataclass
class PluginTrigger:
    type: TriggerType
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginConfig:
    schema: Optional[Dict[str, Any]] = None
    defaults: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginDependencies:
    plugins: Dict[str, str] = field(default_factory=dict)
    npm: Dict[str, str] = field(default_factory=dict)
    pip: Dict[str, str] = field(default_factory=dict)


@dataclass
class PluginUI:
    settings: Optional[str] = None
    dashboard: Optional[str] = None
    icon: Optional[str] = None


@dataclass
class APIEndpoint:
    path: str
    method: str
    description: Optional[str] = None


@dataclass
class PluginAPI:
    endpoints: List[APIEndpoint] = field(default_factory=list)


@dataclass
class PluginCompatibility:
    activelog_version: Optional[str] = None
    os: List[str] = field(default_factory=list)
    arch: List[str] = field(default_factory=list)


@dataclass
class PluginPricing:
    model: str = "free"  # free, freemium, paid, subscription
    price: Optional[float] = None
    currency: Optional[str] = None


@dataclass
class PluginMarketplace:
    pricing: Optional[PluginPricing] = None
    featured: bool = False
    verified: bool = False


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    main: str
    runtime: PluginRuntime
    permissions: PluginPermissions
    display_name: Optional[str] = None
    author: Optional[PluginAuthor] = None
    license: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    category: Optional[PluginCategory] = None
    resources: Optional[PluginResources] = None
    triggers: List[PluginTrigger] = field(default_factory=list)
    config: Optional[PluginConfig] = None
    dependencies: Optional[PluginDependencies] = None
    ui: Optional[PluginUI] = None
    api: Optional[PluginAPI] = None
    compatibility: Optional[PluginCompatibility] = None
    marketplace: Optional[PluginMarketplace] = None


@dataclass
class UserContext:
    id: str
    username: str
    email: str
    name: str
    avatar: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrganizationContext:
    id: str
    name: str
    plan: str
    features: List[str] = field(default_factory=list)
    limits: Dict[str, Union[int, float]] = field(default_factory=dict)


@dataclass
class TriggerEvent:
    type: TriggerType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TriggerResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class HTTPOptions:
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[int] = None
    retries: int = 0


@dataclass
class HTTPResponse:
    status: int
    status_text: str
    headers: Dict[str, str]
    data: Any


@dataclass
class DatabaseField:
    name: str
    type: str


@dataclass
class DatabaseResult:
    rows: List[Dict[str, Any]]
    row_count: int
    fields: List[DatabaseField]


@dataclass
class FileMetadata:
    id: str
    name: str
    path: str
    size: int
    type: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    total: int
    results: List[FileMetadata]
    aggregations: Optional[Dict[str, Any]] = None


@dataclass
class FileEvent:
    type: str  # created, modified, deleted
    path: str
    metadata: Optional[FileMetadata] = None


@dataclass
class AnalysisResult:
    job_id: str
    status: str  # pending, processing, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class JobStatus:
    id: str
    status: str
    progress: float
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class VideoUploadResult:
    video_id: str
    status: str
    url: str


@dataclass
class VideoStatus:
    video_id: str
    status: str
    progress: float
    error: Optional[str] = None


@dataclass
class TranscodeOptions:
    formats: List[str]
    resolutions: List[str]
    quality: str


@dataclass
class AnalyticsQuery:
    metric: str
    dimensions: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    date_range: Optional[Dict[str, datetime]] = None


@dataclass
class AnalyticsResult:
    data: List[Dict[str, Any]]
    total: int
    aggregations: Optional[Dict[str, Any]] = None


@dataclass
class NotificationRequest:
    type: str  # email, push, in-app
    recipient: str
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationStatus:
    id: str
    status: str  # pending, sent, failed
    sent_at: Optional[datetime] = None
    error: Optional[str] = None


# Abstract interfaces
class PluginLogger(ABC):
    @abstractmethod
    def debug(self, message: str, *args: Any) -> None:
        pass

    @abstractmethod
    def info(self, message: str, *args: Any) -> None:
        pass

    @abstractmethod
    def warn(self, message: str, *args: Any) -> None:
        pass

    @abstractmethod
    def error(self, message: str, error: Optional[Exception] = None, *args: Any) -> None:
        pass


class PluginStorage(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def keys(self, pattern: Optional[str] = None) -> List[str]:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass


class PluginHTTP(ABC):
    @abstractmethod
    async def get(self, url: str, options: Optional[HTTPOptions] = None) -> HTTPResponse:
        pass

    @abstractmethod
    async def post(self, url: str, data: Optional[Any] = None, options: Optional[HTTPOptions] = None) -> HTTPResponse:
        pass

    @abstractmethod
    async def put(self, url: str, data: Optional[Any] = None, options: Optional[HTTPOptions] = None) -> HTTPResponse:
        pass

    @abstractmethod
    async def delete(self, url: str, options: Optional[HTTPOptions] = None) -> HTTPResponse:
        pass

    @abstractmethod
    async def patch(self, url: str, data: Optional[Any] = None, options: Optional[HTTPOptions] = None) -> HTTPResponse:
        pass


class PluginDatabase(ABC):
    @abstractmethod
    async def query(self, sql: str, params: Optional[List[Any]] = None) -> DatabaseResult:
        pass

    @abstractmethod
    async def select(self, table: str, where: Optional[Dict[str, Any]] = None) -> DatabaseResult:
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict[str, Any]) -> DatabaseResult:
        pass

    @abstractmethod
    async def update(self, table: str, data: Dict[str, Any], where: Optional[Dict[str, Any]] = None) -> DatabaseResult:
        pass

    @abstractmethod
    async def delete(self, table: str, where: Dict[str, Any]) -> DatabaseResult:
        pass


class AuthService(ABC):
    @abstractmethod
    async def get_current_user(self) -> UserContext:
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        pass

    @abstractmethod
    async def has_permission(self, permission: str) -> bool:
        pass


class MetadataService(ABC):
    @abstractmethod
    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> SearchResult:
        pass

    @abstractmethod
    async def get_file(self, file_id: str) -> FileMetadata:
        pass

    @abstractmethod
    async def update_file(self, file_id: str, metadata: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    async def create_embedding(self, text: str) -> List[float]:
        pass


class FileSyncService(ABC):
    @abstractmethod
    async def watch(self, path: str, callback: Callable[[FileEvent], Awaitable[None]]) -> str:
        pass

    @abstractmethod
    async def unwatch(self, watch_id: str) -> None:
        pass

    @abstractmethod
    async def sync(self, path: str) -> None:
        pass


class AIService(ABC):
    @abstractmethod
    async def analyze(self, data: Any, analysis_type: str) -> AnalysisResult:
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobStatus:
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> None:
        pass


class VideoService(ABC):
    @abstractmethod
    async def upload(self, file_path: str) -> VideoUploadResult:
        pass

    @abstractmethod
    async def get_status(self, video_id: str) -> VideoStatus:
        pass

    @abstractmethod
    async def transcode(self, video_id: str, options: TranscodeOptions) -> str:
        pass


class AnalyticsService(ABC):
    @abstractmethod
    async def track(self, event: str, properties: Optional[Dict[str, Any]] = None) -> None:
        pass

    @abstractmethod
    async def query(self, query: AnalyticsQuery) -> AnalyticsResult:
        pass


class NotificationService(ABC):
    @abstractmethod
    async def send(self, notification: NotificationRequest) -> str:
        pass

    @abstractmethod
    async def get_status(self, notification_id: str) -> NotificationStatus:
        pass


@dataclass
class PluginServices:
    auth: AuthService
    metadata: MetadataService
    file_sync: FileSyncService
    ai_orchestrator: AIService
    video_pipeline: VideoService
    analytics: AnalyticsService
    notifications: NotificationService


class PluginEvents(ABC):
    @abstractmethod
    def on(self, event: str, listener: Callable[..., None]) -> None:
        pass

    @abstractmethod
    def off(self, event: str, listener: Callable[..., None]) -> None:
        pass

    @abstractmethod
    def emit(self, event: str, *args: Any) -> None:
        pass

    @abstractmethod
    def once(self, event: str, listener: Callable[..., None]) -> None:
        pass


@dataclass
class PluginContext:
    manifest: PluginManifest
    config: Dict[str, Any]
    logger: PluginLogger
    storage: PluginStorage
    http: PluginHTTP
    database: PluginDatabase
    services: PluginServices
    events: PluginEvents
    user: UserContext
    organization: OrganizationContext


# Plugin interface
class PluginInterface(ABC):
    """Abstract base class for all plugins"""

    @abstractmethod
    def get_manifest(self) -> PluginManifest:
        """Return the plugin manifest"""
        pass

    async def on_load(self, context: PluginContext) -> None:
        """Called when the plugin is first loaded"""
        pass

    async def on_activate(self, context: PluginContext) -> None:
        """Called when the plugin is activated"""
        pass

    async def on_deactivate(self, context: PluginContext) -> None:
        """Called when the plugin is deactivated"""
        pass

    async def on_unload(self, context: PluginContext) -> None:
        """Called when the plugin is unloaded"""
        pass

    async def on_config_change(self, config: Dict[str, Any], context: PluginContext) -> None:
        """Called when configuration changes"""
        pass

    async def on_trigger(self, event: TriggerEvent, context: PluginContext) -> TriggerResult:
        """Called when a trigger event occurs"""
        return TriggerResult(success=True)

    async def handle_api(self, path: str, method: str, data: Any, context: PluginContext) -> Any:
        """Called for API endpoint handlers"""
        raise PluginError(f"API endpoint not implemented: {method} {path}")