#!/usr/bin/env python3
"""
UI Engine Service - Visual App Builder with Advanced Features
Port: 8445

Features:
- Visual wiring for app building
- Bubble map workflow designer
- Multi-monitor support
- Chatbot-driven development
- Real-time preview
- Drag-drop component library
- Theme marketplace
- Interface versioning
- Preference persistence
- Export/import layouts
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import json
import asyncio
import logging
import os
import uuid
from datetime import datetime
import sqlite3
import aiofiles
from pathlib import Path
import zipfile
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="UI Engine Service",
    description="Visual App Builder with Advanced UI Customization",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class Component(BaseModel):
    id: str
    type: str
    properties: Dict[str, Any]
    position: Dict[str, float]
    size: Dict[str, float]
    connections: List[str] = []

class Workflow(BaseModel):
    id: str
    name: str
    components: List[Component]
    connections: List[Dict[str, str]]
    metadata: Dict[str, Any] = {}

class Theme(BaseModel):
    id: str
    name: str
    description: str
    colors: Dict[str, str]
    fonts: Dict[str, str]
    styles: Dict[str, Any]
    author: str
    version: str
    price: float = 0.0
    
class Layout(BaseModel):
    id: str
    name: str
    components: List[Component]
    theme_id: str
    version: str
    metadata: Dict[str, Any]

class Preference(BaseModel):
    user_id: str
    key: str
    value: Any
    category: str = "general"

# In-memory storage (in production, use proper database)
workflows: Dict[str, Workflow] = {}
themes: Dict[str, Theme] = {}
layouts: Dict[str, Layout] = {}
preferences: Dict[str, Dict[str, Any]] = {}
active_connections: List[WebSocket] = []
component_library = {
    "input": {
        "name": "Text Input",
        "category": "forms",
        "properties": ["placeholder", "value", "required", "disabled"],
        "events": ["onChange", "onFocus", "onBlur"]
    },
    "button": {
        "name": "Button",
        "category": "controls",
        "properties": ["label", "variant", "size", "disabled"],
        "events": ["onClick"]
    },
    "chart": {
        "name": "Chart",
        "category": "visualization",
        "properties": ["type", "data", "width", "height"],
        "events": ["onDataChange"]
    },
    "table": {
        "name": "Data Table",
        "category": "data",
        "properties": ["columns", "data", "sortable", "filterable"],
        "events": ["onRowClick", "onSort", "onFilter"]
    },
    "container": {
        "name": "Container",
        "category": "layout",
        "properties": ["padding", "margin", "backgroundColor", "border"],
        "events": []
    }
}

# Database initialization
def init_database():
    """Initialize SQLite database for persistent storage"""
    os.makedirs("/home/activeloguser/activelog/services/ui-engine/data", exist_ok=True)
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS themes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            data TEXT NOT NULL,
            author TEXT,
            version TEXT,
            price REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS layouts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            data TEXT NOT NULL,
            theme_id TEXT,
            version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Import all modules
from visual_wiring import WiringEngine
from bubble_workflow import BubbleWorkflowDesigner  
from multi_monitor import MultiMonitorManager
from chatbot_dev import ChatbotDevelopmentInterface
from realtime_preview import RealTimePreviewSystem
from component_library import ComponentLibrary
from theme_marketplace import ThemeMarketplace
from interface_versioning import InterfaceVersioning
from preferences import PreferenceManager
from layout_import_export import LayoutImportExport

# Initialize subsystems
wiring_engine = WiringEngine()
bubble_designer = BubbleWorkflowDesigner()
monitor_manager = MultiMonitorManager()
chatbot_interface = ChatbotDevelopmentInterface()
preview_system = RealTimePreviewSystem()
component_lib = ComponentLibrary()
theme_marketplace = ThemeMarketplace()
interface_versioning = InterfaceVersioning()
preference_manager = PreferenceManager()
layout_manager = LayoutImportExport()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    # Load default themes
    await load_default_themes()
    logger.info("UI Engine Service started on port 8324")
    logger.info("All subsystems initialized successfully")

async def load_default_themes():
    """Load default themes into the system"""
    default_themes = [
        Theme(
            id="default-dark",
            name="Dark Theme",
            description="Professional dark theme",
            colors={
                "primary": "#007acc",
                "secondary": "#6c757d",
                "background": "#1e1e1e",
                "surface": "#2d2d30",
                "text": "#ffffff",
                "border": "#404040"
            },
            fonts={
                "primary": "Inter, sans-serif",
                "mono": "JetBrains Mono, monospace"
            },
            styles={
                "borderRadius": "8px",
                "shadow": "0 4px 6px rgba(0, 0, 0, 0.1)"
            },
            author="UI Engine",
            version="1.0.0"
        ),
        Theme(
            id="default-light",
            name="Light Theme",
            description="Clean light theme",
            colors={
                "primary": "#007acc",
                "secondary": "#6c757d",
                "background": "#ffffff",
                "surface": "#f8f9fa",
                "text": "#212529",
                "border": "#dee2e6"
            },
            fonts={
                "primary": "Inter, sans-serif",
                "mono": "JetBrains Mono, monospace"
            },
            styles={
                "borderRadius": "8px",
                "shadow": "0 2px 4px rgba(0, 0, 0, 0.1)"
            },
            author="UI Engine",
            version="1.0.0"
        )
    ]
    
    for theme in default_themes:
        themes[theme.id] = theme

# API Routes

@app.get("/")
async def root():
    return {"service": "UI Engine", "version": "1.0.0", "port": 8324}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Component Library Routes
@app.get("/api/components")
async def get_component_library():
    """Get available component library"""
    return {"components": component_library}

@app.post("/api/components")
async def add_custom_component(component_data: Dict[str, Any]):
    """Add custom component to library"""
    component_id = component_data.get("id", str(uuid.uuid4()))
    component_library[component_id] = component_data
    await manager.broadcast(json.dumps({
        "type": "component_added",
        "data": {"id": component_id, "component": component_data}
    }))
    return {"id": component_id, "status": "added"}

# Workflow Routes
@app.get("/api/workflows")
async def get_workflows():
    """Get all workflows"""
    return {"workflows": list(workflows.values())}

@app.post("/api/workflows")
async def create_workflow(workflow: Workflow):
    """Create new workflow"""
    if not workflow.id:
        workflow.id = str(uuid.uuid4())
    
    workflows[workflow.id] = workflow
    
    # Save to database
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO workflows (id, name, data) VALUES (?, ?, ?)",
        (workflow.id, workflow.name, json.dumps(workflow.dict()))
    )
    conn.commit()
    conn.close()
    
    await manager.broadcast(json.dumps({
        "type": "workflow_created",
        "data": workflow.dict()
    }))
    
    return {"id": workflow.id, "status": "created"}

@app.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get specific workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflows[workflow_id]

@app.put("/api/workflows/{workflow_id}")
async def update_workflow(workflow_id: str, workflow: Workflow):
    """Update workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow.id = workflow_id
    workflows[workflow_id] = workflow
    
    # Save to database
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE workflows SET name = ?, data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (workflow.name, json.dumps(workflow.dict()), workflow_id)
    )
    conn.commit()
    conn.close()
    
    await manager.broadcast(json.dumps({
        "type": "workflow_updated",
        "data": workflow.dict()
    }))
    
    return {"status": "updated"}

@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    del workflows[workflow_id]
    
    # Delete from database
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    conn.commit()
    conn.close()
    
    await manager.broadcast(json.dumps({
        "type": "workflow_deleted",
        "data": {"id": workflow_id}
    }))
    
    return {"status": "deleted"}

# Theme Marketplace Routes
@app.get("/api/themes")
async def get_themes():
    """Get all themes"""
    return {"themes": list(themes.values())}

@app.post("/api/themes")
async def create_theme(theme: Theme):
    """Create new theme"""
    if not theme.id:
        theme.id = str(uuid.uuid4())
    
    themes[theme.id] = theme
    
    # Save to database
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO themes (id, name, data, author, version, price) VALUES (?, ?, ?, ?, ?, ?)",
        (theme.id, theme.name, json.dumps(theme.dict()), theme.author, theme.version, theme.price)
    )
    conn.commit()
    conn.close()
    
    return {"id": theme.id, "status": "created"}

@app.get("/api/themes/{theme_id}")
async def get_theme(theme_id: str):
    """Get specific theme"""
    if theme_id not in themes:
        raise HTTPException(status_code=404, detail="Theme not found")
    return themes[theme_id]

# Layout Management Routes
@app.get("/api/layouts")
async def get_layouts():
    """Get all layouts"""
    return {"layouts": list(layouts.values())}

@app.post("/api/layouts")
async def create_layout(layout: Layout):
    """Create new layout"""
    if not layout.id:
        layout.id = str(uuid.uuid4())
    
    layouts[layout.id] = layout
    
    # Save to database
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO layouts (id, name, data, theme_id, version) VALUES (?, ?, ?, ?, ?)",
        (layout.id, layout.name, json.dumps(layout.dict()), layout.theme_id, layout.version)
    )
    conn.commit()
    conn.close()
    
    return {"id": layout.id, "status": "created"}

@app.get("/api/layouts/{layout_id}")
async def get_layout(layout_id: str):
    """Get specific layout"""
    if layout_id not in layouts:
        raise HTTPException(status_code=404, detail="Layout not found")
    return layouts[layout_id]

# Export/Import Routes
@app.post("/api/layouts/{layout_id}/export")
async def export_layout(layout_id: str):
    """Export layout as downloadable package"""
    if layout_id not in layouts:
        raise HTTPException(status_code=404, detail="Layout not found")
    
    layout = layouts[layout_id]
    export_data = {
        "layout": layout.dict(),
        "theme": themes.get(layout.theme_id, {}).dict() if layout.theme_id in themes else {},
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    }
    
    export_path = f"/home/activeloguser/activelog/services/ui-engine/exports/{layout_id}.json"
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    with open(export_path, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    return FileResponse(
        export_path,
        filename=f"{layout.name.replace(' ', '_')}_layout.json",
        media_type="application/json"
    )

@app.post("/api/layouts/import")
async def import_layout(file: UploadFile = File(...)):
    """Import layout from uploaded file"""
    try:
        content = await file.read()
        import_data = json.loads(content.decode())
        
        # Import layout
        layout_data = import_data.get("layout", {})
        layout_data["id"] = str(uuid.uuid4())  # Generate new ID
        layout = Layout(**layout_data)
        layouts[layout.id] = layout
        
        # Import theme if included
        theme_data = import_data.get("theme", {})
        if theme_data:
            theme_data["id"] = str(uuid.uuid4())  # Generate new ID
            theme = Theme(**theme_data)
            themes[theme.id] = theme
            layout.theme_id = theme.id
        
        # Save to database
        conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO layouts (id, name, data, theme_id, version) VALUES (?, ?, ?, ?, ?)",
            (layout.id, layout.name, json.dumps(layout.dict()), layout.theme_id, layout.version)
        )
        if theme_data:
            cursor.execute(
                "INSERT INTO themes (id, name, data, author, version, price) VALUES (?, ?, ?, ?, ?, ?)",
                (theme.id, theme.name, json.dumps(theme.dict()), theme.author, theme.version, theme.price)
            )
        conn.commit()
        conn.close()
        
        return {"id": layout.id, "status": "imported"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

# Preference Routes
@app.get("/api/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user preferences"""
    return {"preferences": preferences.get(user_id, {})}

@app.post("/api/preferences/{user_id}")
async def set_user_preference(user_id: str, preference: Preference):
    """Set user preference"""
    if user_id not in preferences:
        preferences[user_id] = {}
    
    preferences[user_id][preference.key] = {
        "value": preference.value,
        "category": preference.category
    }
    
    # Save to database
    conn = sqlite3.connect("/home/activeloguser/activelog/services/ui-engine/data/ui_engine.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO preferences (id, user_id, key, value, category) VALUES (?, ?, ?, ?, ?)",
        (f"{user_id}_{preference.key}", user_id, preference.key, json.dumps(preference.value), preference.category)
    )
    conn.commit()
    conn.close()
    
    return {"status": "set"}

# Multi-monitor Support Routes
@app.get("/api/monitors")
async def get_monitor_configurations():
    """Get available monitor configurations"""
    return {
        "configurations": [
            {"id": "single", "name": "Single Monitor", "layout": "1x1"},
            {"id": "dual-horizontal", "name": "Dual Horizontal", "layout": "2x1"},
            {"id": "dual-vertical", "name": "Dual Vertical", "layout": "1x2"},
            {"id": "triple", "name": "Triple Monitor", "layout": "3x1"},
            {"id": "quad", "name": "Quad Monitor", "layout": "2x2"}
        ]
    }

@app.post("/api/monitors/configure")
async def configure_monitors(config: Dict[str, Any]):
    """Configure multi-monitor setup"""
    monitor_config = {
        "id": str(uuid.uuid4()),
        "layout": config.get("layout", "1x1"),
        "displays": config.get("displays", []),
        "created_at": datetime.now().isoformat()
    }
    
    await manager.broadcast(json.dumps({
        "type": "monitor_configured",
        "data": monitor_config
    }))
    
    return {"status": "configured", "config": monitor_config}

# WebSocket endpoints
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time collaboration"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "component_update":
                await manager.broadcast(json.dumps({
                    "type": "component_updated",
                    "client_id": client_id,
                    "data": message.get("data")
                }))
            elif message.get("type") == "workflow_change":
                await manager.broadcast(json.dumps({
                    "type": "workflow_changed",
                    "client_id": client_id,
                    "data": message.get("data")
                }))
            elif message.get("type") == "preview_update":
                await manager.broadcast(json.dumps({
                    "type": "preview_updated",
                    "client_id": client_id,
                    "data": message.get("data")
                }))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(json.dumps({
            "type": "client_disconnected",
            "client_id": client_id
        }))

# Chatbot Development Interface Routes
@app.post("/api/chatbot/generate")
async def generate_component_from_chat(request: Dict[str, Any]):
    """Generate components based on natural language description"""
    description = request.get("description", "")
    
    # Simple NLP-based component generation (in production, use proper AI)
    component_suggestions = []
    
    if "form" in description.lower() or "input" in description.lower():
        component_suggestions.append({
            "type": "form",
            "components": [
                {"type": "input", "properties": {"placeholder": "Enter text"}},
                {"type": "button", "properties": {"label": "Submit"}}
            ]
        })
    
    if "chart" in description.lower() or "graph" in description.lower():
        component_suggestions.append({
            "type": "chart",
            "properties": {"type": "line", "data": []}
        })
    
    if "table" in description.lower() or "list" in description.lower():
        component_suggestions.append({
            "type": "table",
            "properties": {"columns": [], "data": []}
        })
    
    return {
        "suggestions": component_suggestions,
        "description": description
    }

@app.post("/api/chatbot/refine")
async def refine_component_from_chat(request: Dict[str, Any]):
    """Refine component based on additional requirements"""
    component = request.get("component", {})
    refinement = request.get("refinement", "")
    
    # Apply refinements (simplified logic)
    if "bigger" in refinement.lower():
        component.setdefault("properties", {})["size"] = "large"
    if "color" in refinement.lower():
        component.setdefault("properties", {})["color"] = "blue"
    if "required" in refinement.lower():
        component.setdefault("properties", {})["required"] = True
    
    return {"refined_component": component}

# Visual Wiring System Routes
@app.get("/api/wiring/templates")
async def get_wiring_templates():
    """Get visual wiring component templates"""
    return {"templates": wiring_engine.get_component_templates()}

@app.post("/api/wiring/canvas")
async def create_wiring_canvas(request: Dict[str, Any]):
    """Create new wiring canvas"""
    name = request.get("name", "New Canvas")
    canvas_id = wiring_engine.create_canvas(name)
    return {"canvas_id": canvas_id}

@app.get("/api/wiring/canvas/{canvas_id}")
async def get_wiring_canvas(canvas_id: str):
    """Get wiring canvas"""
    canvas = wiring_engine.get_canvas(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return {"canvas": canvas.dict()}

# Bubble Workflow Routes
@app.post("/api/bubble/workflow")
async def create_bubble_workflow(request: Dict[str, Any]):
    """Create new bubble workflow"""
    name = request.get("name", "New Workflow")
    description = request.get("description", "")
    workflow_id = bubble_designer.create_workflow(name, description)
    return {"workflow_id": workflow_id}

@app.get("/api/bubble/workflow/{workflow_id}")
async def get_bubble_workflow(workflow_id: str):
    """Get bubble workflow"""
    workflow = bubble_designer.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"workflow": workflow.dict()}

@app.get("/api/bubble/templates")
async def get_bubble_templates():
    """Get bubble templates"""
    return {"templates": bubble_designer.get_bubble_templates()}

# Multi-Monitor Routes
@app.get("/api/monitors/detect")
async def detect_displays():
    """Detect connected displays"""
    displays = await monitor_manager.detect_displays()
    return {"displays": [d.dict() for d in displays]}

@app.post("/api/monitors/configuration")
async def create_display_config(request: Dict[str, Any]):
    """Create display configuration"""
    from multi_monitor import Display
    
    name = request.get("name", "New Configuration")
    displays_data = request.get("displays", [])
    layout_mode = request.get("layout_mode", "extended")
    
    displays = [Display(**d) for d in displays_data]
    config_id = monitor_manager.create_display_configuration(name, displays, layout_mode)
    return {"config_id": config_id}

# Chatbot Development Routes
@app.post("/api/chatbot/conversation")
async def create_chatbot_conversation(request: Dict[str, Any]):
    """Create new chatbot conversation"""
    project_name = request.get("project_name", "New Project")
    conversation_id = chatbot_interface.create_conversation(project_name)
    return {"conversation_id": conversation_id}

@app.post("/api/chatbot/conversation/{conversation_id}/message")
async def send_chatbot_message(conversation_id: str, request: Dict[str, Any]):
    """Send message to chatbot"""
    message = request.get("message", "")
    response = chatbot_interface.process_message(conversation_id, message)
    return response

# Real-time Preview Routes
@app.post("/api/preview/session")
async def create_preview_session(request: Dict[str, Any]):
    """Create preview session"""
    project_id = request.get("project_id", "")
    user_id = request.get("user_id", "")
    config = request.get("config", {})
    
    session_id = await preview_system.create_preview_session(project_id, user_id, config)
    return {"session_id": session_id}

@app.websocket("/ws/preview/{session_id}")
async def preview_websocket(websocket: WebSocket, session_id: str):
    """Preview WebSocket endpoint"""
    await preview_system.connect_websocket(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        await preview_system.disconnect_websocket(session_id, websocket)

# Component Library Routes
@app.get("/api/components/library")
async def get_component_library():
    """Get component library"""
    return {
        "categories": component_lib.get_categories(),
        "components": [comp.dict() for comp in component_lib.components.values()]
    }

@app.post("/api/components/instance")
async def create_component_instance(request: Dict[str, Any]):
    """Create component instance"""
    component_id = request.get("component_id", "")
    name = request.get("name")
    position = request.get("position", (0, 0))
    
    instance_id = component_lib.create_instance(component_id, name, tuple(position))
    return {"instance_id": instance_id}

# Theme Marketplace Routes  
@app.get("/api/themes/marketplace")
async def get_marketplace_themes():
    """Get marketplace themes"""
    themes = theme_marketplace.search_themes()
    return {"themes": [theme.dict() for theme in themes]}

@app.get("/api/themes/marketplace/{theme_id}")
async def get_marketplace_theme(theme_id: str):
    """Get theme details"""
    details = theme_marketplace.get_theme_details(theme_id)
    if not details:
        raise HTTPException(status_code=404, detail="Theme not found")
    return details

@app.post("/api/themes/purchase")
async def purchase_theme(request: Dict[str, Any]):
    """Purchase theme"""
    theme_id = request.get("theme_id", "")
    user_id = request.get("user_id", "")
    payment_info = request.get("payment_info", {})
    
    purchase_id = theme_marketplace.purchase_theme(theme_id, user_id, payment_info)
    return {"purchase_id": purchase_id}

# Interface Versioning Routes
@app.post("/api/versions/snapshot")
async def create_version_snapshot(request: Dict[str, Any]):
    """Create version snapshot"""
    interface_id = request.get("interface_id", "")
    version = request.get("version", "")
    title = request.get("title", "")
    components = request.get("components", [])
    layout = request.get("layout", {})
    created_by = request.get("created_by", "")
    
    snapshot_id = interface_versioning.create_snapshot(
        interface_id, version, title, components, layout, created_by
    )
    return {"snapshot_id": snapshot_id}

@app.get("/api/versions/{interface_id}/history")
async def get_version_history(interface_id: str):
    """Get version history"""
    history = interface_versioning.get_version_history(interface_id)
    return {"history": history}

# Preferences Routes
@app.get("/api/preferences/{user_id}")
async def get_user_preferences_api(user_id: str):
    """Get user preferences"""
    preferences = preference_manager.get_user_preferences(user_id)
    return {"preferences": preferences}

@app.post("/api/preferences/{user_id}")
async def set_user_preference_api(user_id: str, request: Dict[str, Any]):
    """Set user preference"""
    from preferences import PreferenceScope
    
    key = request.get("key", "")
    value = request.get("value")
    change_reason = request.get("reason", "")
    
    success = preference_manager.set_preference(
        key, value, PreferenceScope.USER, user_id, user_id, change_reason
    )
    return {"success": success}

# Layout Import/Export Routes
@app.post("/api/layouts/export")
async def export_layout_api(request: Dict[str, Any]):
    """Export layout"""
    layout_data = request.get("layout", {})
    components = request.get("components", [])
    name = request.get("name", "Exported Layout")
    created_by = request.get("created_by", "")
    export_format = request.get("format", "json")
    
    export_id = layout_manager.export_layout(
        layout_data, components, name, created_by, export_format
    )
    return {"export_id": export_id}

@app.get("/api/layouts/export/{export_id}/download")
async def download_layout_export(export_id: str, format: str = "json"):
    """Download layout export"""
    try:
        data = layout_manager.get_export_data(export_id, format)
        
        if format == "zip":
            return Response(
                content=data,
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename=layout-{export_id}.zip"}
            )
        else:
            return Response(
                content=data,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename=layout-{export_id}.{format}"}
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/layouts/import")
async def import_layout_api(file: UploadFile = File(...)):
    """Import layout from file"""
    try:
        from layout_import_export import ImportSource
        
        content = await file.read()
        import_id = layout_manager.import_layout(
            ImportSource.FILE, content, "user", "replace"
        )
        
        import_status = layout_manager.get_import_status(import_id)
        return {
            "import_id": import_id,
            "status": import_status.dict() if import_status else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8445)