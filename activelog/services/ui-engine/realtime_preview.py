"""
Real-time Preview System
Live preview and hot reload functionality for UI development
"""

from typing import Dict, List, Optional, Any, Callable
from pydantic import BaseModel
from datetime import datetime
import asyncio
import json
import uuid
import hashlib
import websockets
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class PreviewSession(BaseModel):
    """Preview session for a UI project"""
    id: str
    project_id: str
    user_id: str
    preview_url: str
    is_active: bool = True
    last_update: datetime
    config: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class ComponentSnapshot(BaseModel):
    """Snapshot of component state"""
    component_id: str
    type: str
    properties: Dict[str, Any]
    children: List[str] = []
    timestamp: datetime
    hash: str

class PreviewUpdate(BaseModel):
    """Update event for preview system"""
    id: str
    session_id: str
    type: str  # 'component_added', 'component_updated', 'component_removed', 'style_changed'
    component_id: Optional[str] = None
    data: Dict[str, Any]
    timestamp: datetime

class HotReloadManager(BaseModel):
    """Manages hot reload functionality"""
    enabled: bool = True
    debounce_ms: int = 300
    auto_save: bool = True
    preserve_state: bool = True
    reload_on_error: bool = False

class PreviewConfiguration(BaseModel):
    """Configuration for preview system"""
    id: str
    name: str
    viewport_width: int = 1200
    viewport_height: int = 800
    device_type: str = "desktop"  # desktop, mobile, tablet
    theme: str = "default"
    show_grid: bool = False
    show_rulers: bool = False
    zoom_level: float = 1.0
    responsive_mode: bool = False
    hot_reload: HotReloadManager = HotReloadManager()

class RealTimePreviewSystem:
    """Real-time preview system with hot reload"""
    
    def __init__(self):
        self.sessions: Dict[str, PreviewSession] = {}
        self.websocket_connections: Dict[str, List[WebSocket]] = {}
        self.component_snapshots: Dict[str, List[ComponentSnapshot]] = {}
        self.preview_configs: Dict[str, PreviewConfiguration] = {}
        self.update_queue: Dict[str, List[PreviewUpdate]] = {}
        self.change_listeners: List[Callable] = []
        
        # Device presets
        self.device_presets = {
            "desktop": {"width": 1920, "height": 1080, "dpi": 96},
            "laptop": {"width": 1366, "height": 768, "dpi": 96},
            "tablet": {"width": 768, "height": 1024, "dpi": 132},
            "mobile": {"width": 375, "height": 667, "dpi": 163},
            "mobile_large": {"width": 414, "height": 896, "dpi": 163}
        }
        
    async def create_preview_session(self, project_id: str, user_id: str, 
                                   config: Dict[str, Any] = None) -> str:
        """Create a new preview session"""
        session_id = str(uuid.uuid4())
        preview_url = f"/preview/{session_id}"
        
        session = PreviewSession(
            id=session_id,
            project_id=project_id,
            user_id=user_id,
            preview_url=preview_url,
            last_update=datetime.now(),
            config=config or {}
        )
        
        self.sessions[session_id] = session
        self.websocket_connections[session_id] = []
        self.update_queue[session_id] = []
        self.component_snapshots[session_id] = []
        
        # Create default preview configuration
        preview_config = PreviewConfiguration(
            id=str(uuid.uuid4()),
            name=f"Preview Config for {project_id}"
        )
        self.preview_configs[session_id] = preview_config
        
        logger.info(f"Created preview session {session_id} for project {project_id}")
        return session_id
    
    async def connect_websocket(self, session_id: str, websocket: WebSocket):
        """Connect WebSocket to preview session"""
        if session_id not in self.sessions:
            await websocket.close(code=4004, reason="Session not found")
            return
        
        await websocket.accept()
        self.websocket_connections[session_id].append(websocket)
        
        # Send initial state
        initial_data = {
            "type": "session_connected",
            "session_id": session_id,
            "config": self.preview_configs[session_id].dict(),
            "snapshots": [s.dict() for s in self.component_snapshots.get(session_id, [])]
        }
        
        await websocket.send_text(json.dumps(initial_data))
        logger.info(f"WebSocket connected to session {session_id}")
    
    async def disconnect_websocket(self, session_id: str, websocket: WebSocket):
        """Disconnect WebSocket from preview session"""
        if session_id in self.websocket_connections:
            if websocket in self.websocket_connections[session_id]:
                self.websocket_connections[session_id].remove(websocket)
        
        logger.info(f"WebSocket disconnected from session {session_id}")
    
    async def update_component(self, session_id: str, component_id: str, 
                              component_type: str, properties: Dict[str, Any],
                              children: List[str] = None):
        """Update component in preview"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        # Create component snapshot
        snapshot = ComponentSnapshot(
            component_id=component_id,
            type=component_type,
            properties=properties,
            children=children or [],
            timestamp=datetime.now(),
            hash=self._calculate_hash(component_id, properties)
        )
        
        # Update or add snapshot
        session_snapshots = self.component_snapshots[session_id]
        existing_index = next((i for i, s in enumerate(session_snapshots) 
                              if s.component_id == component_id), None)
        
        if existing_index is not None:
            session_snapshots[existing_index] = snapshot
            update_type = "component_updated"
        else:
            session_snapshots.append(snapshot)
            update_type = "component_added"
        
        # Create update event
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type=update_type,
            component_id=component_id,
            data={
                "component_type": component_type,
                "properties": properties,
                "children": children or [],
                "snapshot": snapshot.dict()
            },
            timestamp=datetime.now()
        )
        
        # Queue update
        await self._queue_update(session_id, update)
        
        # Update session timestamp
        self.sessions[session_id].last_update = datetime.now()
    
    async def remove_component(self, session_id: str, component_id: str):
        """Remove component from preview"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        # Remove snapshot
        session_snapshots = self.component_snapshots[session_id]
        self.component_snapshots[session_id] = [
            s for s in session_snapshots if s.component_id != component_id
        ]
        
        # Create update event
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="component_removed",
            component_id=component_id,
            data={"component_id": component_id},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def update_theme(self, session_id: str, theme: str):
        """Update theme for preview"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        self.preview_configs[session_id].theme = theme
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="theme_changed",
            data={"theme": theme},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def update_viewport(self, session_id: str, width: int, height: int, 
                             device_type: str = None):
        """Update viewport dimensions"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        config = self.preview_configs[session_id]
        config.viewport_width = width
        config.viewport_height = height
        
        if device_type:
            config.device_type = device_type
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="viewport_changed",
            data={
                "width": width,
                "height": height,
                "device_type": device_type
            },
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def set_device_preset(self, session_id: str, device_type: str):
        """Set viewport to device preset"""
        if device_type not in self.device_presets:
            raise ValueError(f"Unknown device type: {device_type}")
        
        preset = self.device_presets[device_type]
        await self.update_viewport(
            session_id, 
            preset["width"], 
            preset["height"], 
            device_type
        )
    
    async def toggle_responsive_mode(self, session_id: str, enabled: bool):
        """Toggle responsive preview mode"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        self.preview_configs[session_id].responsive_mode = enabled
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="responsive_mode_changed",
            data={"enabled": enabled},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def update_zoom(self, session_id: str, zoom_level: float):
        """Update zoom level"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        # Clamp zoom level
        zoom_level = max(0.1, min(3.0, zoom_level))
        self.preview_configs[session_id].zoom_level = zoom_level
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="zoom_changed",
            data={"zoom_level": zoom_level},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def toggle_grid(self, session_id: str, show_grid: bool):
        """Toggle grid display"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        self.preview_configs[session_id].show_grid = show_grid
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="grid_changed",
            data={"show_grid": show_grid},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def toggle_rulers(self, session_id: str, show_rulers: bool):
        """Toggle rulers display"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        self.preview_configs[session_id].show_rulers = show_rulers
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="rulers_changed",
            data={"show_rulers": show_rulers},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def configure_hot_reload(self, session_id: str, config: Dict[str, Any]):
        """Configure hot reload settings"""
        if session_id not in self.preview_configs:
            raise ValueError(f"Preview config for session {session_id} not found")
        
        hot_reload = self.preview_configs[session_id].hot_reload
        
        if "enabled" in config:
            hot_reload.enabled = config["enabled"]
        if "debounce_ms" in config:
            hot_reload.debounce_ms = config["debounce_ms"]
        if "auto_save" in config:
            hot_reload.auto_save = config["auto_save"]
        if "preserve_state" in config:
            hot_reload.preserve_state = config["preserve_state"]
        if "reload_on_error" in config:
            hot_reload.reload_on_error = config["reload_on_error"]
        
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="hot_reload_config_changed",
            data={"config": hot_reload.dict()},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def force_reload(self, session_id: str):
        """Force reload of preview"""
        update = PreviewUpdate(
            id=str(uuid.uuid4()),
            session_id=session_id,
            type="force_reload",
            data={},
            timestamp=datetime.now()
        )
        
        await self._queue_update(session_id, update)
    
    async def capture_screenshot(self, session_id: str) -> Dict[str, Any]:
        """Capture screenshot of current preview"""
        # In real implementation, this would capture actual screenshot
        screenshot_id = str(uuid.uuid4())
        
        return {
            "screenshot_id": screenshot_id,
            "session_id": session_id,
            "url": f"/screenshots/{screenshot_id}.png",
            "timestamp": datetime.now().isoformat(),
            "viewport": self.preview_configs[session_id].dict() if session_id in self.preview_configs else {}
        }
    
    async def get_performance_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get performance metrics for preview session"""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        snapshots = self.component_snapshots.get(session_id, [])
        updates = self.update_queue.get(session_id, [])
        
        # Calculate metrics
        component_count = len(snapshots)
        update_count = len(updates)
        
        # Estimate render time (simplified)
        estimated_render_time = component_count * 2  # 2ms per component
        
        # Memory usage estimate
        memory_usage = sum(len(json.dumps(s.dict())) for s in snapshots)
        
        return {
            "session_id": session_id,
            "component_count": component_count,
            "update_count": update_count,
            "estimated_render_time_ms": estimated_render_time,
            "memory_usage_bytes": memory_usage,
            "websocket_connections": len(self.websocket_connections.get(session_id, [])),
            "last_update": session.last_update.isoformat(),
            "session_duration_seconds": (datetime.now() - session.last_update).total_seconds()
        }
    
    async def _queue_update(self, session_id: str, update: PreviewUpdate):
        """Queue update for processing"""
        if session_id not in self.update_queue:
            self.update_queue[session_id] = []
        
        self.update_queue[session_id].append(update)
        
        # Process update immediately if hot reload is enabled
        config = self.preview_configs.get(session_id)
        if config and config.hot_reload.enabled:
            await self._process_update(session_id, update)
    
    async def _process_update(self, session_id: str, update: PreviewUpdate):
        """Process update and send to connected WebSockets"""
        websockets_list = self.websocket_connections.get(session_id, [])
        
        if not websockets_list:
            return
        
        message = {
            "type": "preview_update",
            "update": update.dict()
        }
        
        # Send to all connected WebSockets
        disconnected_sockets = []
        for websocket in websockets_list:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"Failed to send update to WebSocket: {e}")
                disconnected_sockets.append(websocket)
        
        # Remove disconnected WebSockets
        for websocket in disconnected_sockets:
            websockets_list.remove(websocket)
        
        # Notify change listeners
        for listener in self.change_listeners:
            try:
                await listener(session_id, update)
            except Exception as e:
                logger.warning(f"Change listener error: {e}")
    
    def _calculate_hash(self, component_id: str, properties: Dict[str, Any]) -> str:
        """Calculate hash for component state"""
        content = f"{component_id}{json.dumps(properties, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def add_change_listener(self, listener: Callable):
        """Add change listener"""
        self.change_listeners.append(listener)
    
    def remove_change_listener(self, listener: Callable):
        """Remove change listener"""
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)
    
    def get_session(self, session_id: str) -> Optional[PreviewSession]:
        """Get preview session"""
        return self.sessions.get(session_id)
    
    def get_preview_config(self, session_id: str) -> Optional[PreviewConfiguration]:
        """Get preview configuration"""
        return self.preview_configs.get(session_id)
    
    def list_sessions(self, user_id: str = None) -> List[Dict]:
        """List preview sessions"""
        sessions = []
        for session in self.sessions.values():
            if user_id is None or session.user_id == user_id:
                sessions.append({
                    "id": session.id,
                    "project_id": session.project_id,
                    "user_id": session.user_id,
                    "preview_url": session.preview_url,
                    "is_active": session.is_active,
                    "last_update": session.last_update.isoformat(),
                    "component_count": len(self.component_snapshots.get(session.id, [])),
                    "websocket_connections": len(self.websocket_connections.get(session.id, []))
                })
        return sessions
    
    async def close_session(self, session_id: str):
        """Close preview session"""
        if session_id not in self.sessions:
            return
        
        # Close all WebSocket connections
        websockets_list = self.websocket_connections.get(session_id, [])
        for websocket in websockets_list:
            try:
                await websocket.close()
            except Exception:
                pass
        
        # Clean up data
        self.sessions.pop(session_id, None)
        self.websocket_connections.pop(session_id, None)
        self.component_snapshots.pop(session_id, None)
        self.preview_configs.pop(session_id, None)
        self.update_queue.pop(session_id, None)
        
        logger.info(f"Closed preview session {session_id}")
    
    def get_device_presets(self) -> Dict[str, Dict]:
        """Get available device presets"""
        return self.device_presets.copy()