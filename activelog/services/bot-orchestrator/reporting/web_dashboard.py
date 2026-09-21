"""
Web Dashboard for Progress Reporting
Real-time web interface for monitoring bot orchestration progress
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

from .progress_reporter import ProgressReporter, ReportType

logger = logging.getLogger(__name__)

class WebDashboard:
    """Web-based dashboard for progress monitoring"""
    
    def __init__(self, progress_reporter: ProgressReporter, port: int = 8481):
        self.progress_reporter = progress_reporter
        self.port = port
        self.app = FastAPI(title="Bot Orchestration Dashboard")
        self.templates = Jinja2Templates(directory="templates")
        
        # WebSocket connections
        self.websocket_connections: List[WebSocket] = []
        
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            return self.templates.TemplateResponse("dashboard.html", {"request": request})
        
        @self.app.get("/api/overview")
        async def get_overview():
            return self.progress_reporter.get_system_overview()
        
        @self.app.get("/api/reports/{report_type}")
        async def get_report(report_type: str, task_ids: Optional[str] = None):
            try:
                report_enum = ReportType(report_type)
                task_list = task_ids.split(",") if task_ids else None
                return await self.progress_reporter.generate_report(report_enum, task_list)
            except ValueError:
                return {"error": f"Invalid report type: {report_type}"}
        
        @self.app.get("/api/tasks/{task_id}/progress")
        async def get_task_progress(task_id: str):
            progress = self.progress_reporter.get_progress_summary(task_id)
            if progress:
                return progress
            else:
                return {"error": "Task not found"}
        
        @self.app.websocket("/ws/progress")
        async def progress_websocket(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            # Subscribe to progress updates
            subscriber_id = f"websocket_{id(websocket)}"
            queue = await self.progress_reporter.subscribe_to_progress(subscriber_id)
            
            try:
                while True:
                    # Get progress updates
                    event = await queue.get()
                    await websocket.send_json(event)
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
                await self.progress_reporter.unsubscribe_from_progress(subscriber_id)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_connections:
                    self.websocket_connections.remove(websocket)
                await self.progress_reporter.unsubscribe_from_progress(subscriber_id)
        
        @self.app.on_event("startup")
        async def startup():
            logger.info(f"Bot Orchestration Dashboard starting on port {self.port}")
        
        @self.app.on_event("shutdown")
        async def shutdown():
            logger.info("Bot Orchestration Dashboard shutting down")
    
    async def start(self):
        """Start the web dashboard"""
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0", 
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all connected WebSocket clients"""
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(data)
            except:
                disconnected.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            if websocket in self.websocket_connections:
                self.websocket_connections.remove(websocket)