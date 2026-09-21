"""
User-Friendly Web Dashboard for Multi-Bot Orchestration
Modern web interface with real-time updates and intuitive controls
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import uuid
from dataclasses import asdict
import os

from ..director.claude_director import ClaudeDirector, Task, TaskStatus, TaskPriority
from ..collaboration.collaborative_executor import CollaborativeTaskExecutor, CollaborationPattern, CollaborationPlan
from ..synchronization.bot_synchronizer import BotSynchronizer, SynchronizationBarrierType, CoordinationMode
from ..knowledge.knowledge_sharing_system import KnowledgeSharingSystem
from ..reporting.enhanced_progress_reporter import EnhancedProgressReporter, CollaborationEventType

logger = logging.getLogger(__name__)

class WebDashboard:
    """Modern web dashboard for multi-bot orchestration system"""
    
    def __init__(
        self,
        director: ClaudeDirector,
        collaborative_executor: CollaborativeTaskExecutor,
        bot_synchronizer: BotSynchronizer,
        knowledge_system: KnowledgeSharingSystem,
        progress_reporter: EnhancedProgressReporter,
        static_dir: str = "/home/activeloguser/activelog/services/bot-orchestrator/ui/static",
        templates_dir: str = "/home/activeloguser/activelog/services/bot-orchestrator/ui/templates"
    ):
        self.director = director
        self.collaborative_executor = collaborative_executor
        self.bot_synchronizer = bot_synchronizer
        self.knowledge_system = knowledge_system
        self.progress_reporter = progress_reporter
        
        # FastAPI app
        self.app = FastAPI(title="Multi-Bot Orchestrator Dashboard", version="1.0.0")
        
        # WebSocket connections for real-time updates
        self.websocket_connections: Set[WebSocket] = set()
        
        # Create directories if they don't exist
        os.makedirs(static_dir, exist_ok=True)
        os.makedirs(templates_dir, exist_ok=True)
        
        # Setup static files and templates
        self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
        self.templates = Jinja2Templates(directory=templates_dir)
        
        # Setup routes
        self._setup_routes()
        
        # Background tasks
        self._background_task = None
        self._running = False
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page"""
            return self.templates.TemplateResponse("dashboard.html", {"request": request})
        
        @self.app.get("/api/system/overview")
        async def get_system_overview():
            """Get system overview data"""
            try:
                # Get data from various components
                collaboration_overview = self.progress_reporter.get_collaboration_overview()
                system_overview = self.progress_reporter.get_system_overview()
                sync_status = self.bot_synchronizer.get_synchronization_status()
                
                return {
                    "collaboration": collaboration_overview,
                    "system": system_overview,
                    "synchronization": sync_status,
                    "knowledge_stats": await self._get_knowledge_stats(),
                    "bot_stats": await self._get_bot_stats()
                }
            except Exception as e:
                logger.error(f"Error getting system overview: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/tasks")
        async def get_tasks(status: Optional[str] = None, limit: int = 50):
            """Get tasks with optional filtering"""
            try:
                # Get tasks from director (placeholder - implement based on your director interface)
                tasks = await self._get_tasks_data(status, limit)
                return {"tasks": tasks}
            except Exception as e:
                logger.error(f"Error getting tasks: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/tasks")
        async def create_task(task_data: dict):
            """Create a new task"""
            try:
                # Create task through director
                task = await self._create_task_from_data(task_data)
                return {"task_id": task.id, "status": "created"}
            except Exception as e:
                logger.error(f"Error creating task: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/tasks/{task_id}")
        async def get_task_details(task_id: str):
            """Get detailed task information"""
            try:
                progress = self.progress_reporter.get_progress_summary(task_id)
                if not progress:
                    raise HTTPException(status_code=404, detail="Task not found")
                return progress
            except Exception as e:
                logger.error(f"Error getting task details: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/collaboration/start")
        async def start_collaboration(collaboration_data: dict):
            """Start a new collaboration session"""
            try:
                # Parse collaboration data
                pattern = CollaborationPattern(collaboration_data.get("pattern", "PARALLEL"))
                task_ids = set(collaboration_data.get("task_ids", []))
                bot_preferences = collaboration_data.get("bot_preferences", {})
                
                # Create collaboration plan
                plan = CollaborationPlan(
                    collaboration_id=str(uuid.uuid4()),
                    pattern=pattern,
                    task_assignments={},  # Will be filled by executor
                    coordination_requirements=[],
                    estimated_duration=collaboration_data.get("estimated_duration", 3600),
                    success_criteria=[],
                    fallback_strategy="ABORT"
                )
                
                # Execute collaboration
                result = await self.collaborative_executor.execute_collaboration(
                    plan, list(task_ids), bot_preferences
                )
                
                return {
                    "collaboration_id": plan.collaboration_id,
                    "status": "started",
                    "result": asdict(result) if result else None
                }
            except Exception as e:
                logger.error(f"Error starting collaboration: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/collaboration/sessions")
        async def get_collaboration_sessions(active_only: bool = False):
            """Get collaboration sessions"""
            try:
                report = await self.progress_reporter.generate_collaboration_report()
                sessions = report.get("active_sessions", []) if active_only else report
                return {"sessions": sessions}
            except Exception as e:
                logger.error(f"Error getting collaboration sessions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/bots")
        async def get_bots():
            """Get bot status and information"""
            try:
                bot_stats = await self._get_detailed_bot_stats()
                return {"bots": bot_stats}
            except Exception as e:
                logger.error(f"Error getting bot information: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/bots/{bot_id}/register")
        async def register_bot(bot_id: str, bot_data: dict):
            """Register a new bot"""
            try:
                success = self.bot_synchronizer.register_bot(bot_id, bot_data)
                return {"success": success, "message": f"Bot {bot_id} registered"}
            except Exception as e:
                logger.error(f"Error registering bot: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/api/knowledge")
        async def get_knowledge_overview():
            """Get knowledge system overview"""
            try:
                stats = await self._get_detailed_knowledge_stats()
                return stats
            except Exception as e:
                logger.error(f"Error getting knowledge overview: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/reports/{report_type}")
        async def generate_report(report_type: str):
            """Generate various types of reports"""
            try:
                if report_type == "collaboration":
                    report = await self.progress_reporter.generate_collaboration_report()
                elif report_type == "performance":
                    report = await self.progress_reporter.generate_report("performance")
                elif report_type == "cost":
                    report = await self.progress_reporter.generate_report("cost_analysis")
                else:
                    report = await self.progress_reporter.generate_report(report_type)
                
                return report
            except Exception as e:
                logger.error(f"Error generating report: {e}")
                raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_connections.add(websocket)
            
            try:
                # Subscribe to progress updates
                subscriber_id = str(uuid.uuid4())
                progress_queue = await self.progress_reporter.subscribe_to_progress(subscriber_id)
                collaboration_queue = await self.progress_reporter.subscribe_to_collaboration(subscriber_id)
                
                # Send real-time updates
                async def send_updates():
                    while True:
                        try:
                            # Check for progress updates
                            try:
                                progress_event = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                                await websocket.send_json({
                                    "type": "progress_update",
                                    "data": progress_event
                                })
                            except asyncio.TimeoutError:
                                pass
                            
                            # Check for collaboration updates
                            try:
                                collab_event = await asyncio.wait_for(collaboration_queue.get(), timeout=0.1)
                                await websocket.send_json({
                                    "type": "collaboration_update",
                                    "data": collab_event
                                })
                            except asyncio.TimeoutError:
                                pass
                            
                            # Send periodic system updates
                            await asyncio.sleep(5)  # Send updates every 5 seconds
                            system_data = await self._get_realtime_system_data()
                            await websocket.send_json({
                                "type": "system_update",
                                "data": system_data
                            })
                            
                        except WebSocketDisconnect:
                            break
                        except Exception as e:
                            logger.error(f"Error in WebSocket updates: {e}")
                            await asyncio.sleep(1)
                
                # Start sending updates
                await send_updates()
                
            except WebSocketDisconnect:
                pass
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.discard(websocket)
                try:
                    await self.progress_reporter.unsubscribe_from_progress(subscriber_id)
                    await self.progress_reporter.unsubscribe_from_collaboration(subscriber_id)
                except:
                    pass
    
    async def _get_knowledge_stats(self) -> Dict:
        """Get knowledge system statistics"""
        try:
            # Get basic stats from knowledge system
            total_items = len(self.knowledge_system.knowledge_items)
            total_contexts = len(self.knowledge_system.context_frames)
            total_patterns = len(self.knowledge_system.learning_patterns)
            
            return {
                "total_knowledge_items": total_items,
                "total_context_frames": total_contexts,
                "total_learning_patterns": total_patterns,
                "knowledge_graph_nodes": self.knowledge_system.knowledge_graph.number_of_nodes(),
                "knowledge_graph_edges": self.knowledge_system.knowledge_graph.number_of_edges()
            }
        except Exception as e:
            logger.error(f"Error getting knowledge stats: {e}")
            return {}
    
    async def _get_bot_stats(self) -> Dict:
        """Get bot statistics"""
        try:
            sync_status = self.bot_synchronizer.get_synchronization_status()
            return {
                "active_bots": sync_status.get("active_bots", 0),
                "total_bots": sync_status.get("total_bots", 0),
                "active_barriers": sync_status.get("active_barriers", 0),
                "shared_resources": sync_status.get("shared_resources", 0)
            }
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {}
    
    async def _get_detailed_bot_stats(self) -> List[Dict]:
        """Get detailed bot statistics"""
        bots = []
        try:
            for bot_id in self.bot_synchronizer.bot_states.keys():
                bot_status = self.bot_synchronizer.get_bot_status(bot_id)
                if bot_status:
                    # Get collaboration profile if available
                    collab_profile = self.progress_reporter.bot_profiles.get(bot_id)
                    
                    bot_info = {
                        **bot_status,
                        "collaboration_profile": {
                            "total_collaborations": collab_profile.total_collaborations if collab_profile else 0,
                            "success_rate": collab_profile.successful_collaborations / max(1, collab_profile.total_collaborations) if collab_profile else 0,
                            "coordination_score": collab_profile.coordination_score if collab_profile else 0,
                            "preferred_patterns": [p.value for p in collab_profile.preferred_patterns] if collab_profile else []
                        } if collab_profile else None
                    }
                    bots.append(bot_info)
        except Exception as e:
            logger.error(f"Error getting detailed bot stats: {e}")
        
        return bots
    
    async def _get_detailed_knowledge_stats(self) -> Dict:
        """Get detailed knowledge system statistics"""
        try:
            basic_stats = await self._get_knowledge_stats()
            
            # Get recent activity
            recent_items = [
                {
                    "id": item.item_id,
                    "title": item.title,
                    "created_at": item.created_at.isoformat(),
                    "access_level": item.access_level.value,
                    "confidence_score": item.confidence_score
                }
                for item in sorted(self.knowledge_system.knowledge_items.values(), 
                                 key=lambda x: x.created_at, reverse=True)[:10]
            ]
            
            # Get top patterns
            top_patterns = [
                {
                    "pattern_id": pattern.pattern_id,
                    "description": pattern.description,
                    "confidence_score": pattern.confidence_score,
                    "usage_count": pattern.usage_count
                }
                for pattern in sorted(self.knowledge_system.learning_patterns.values(),
                                    key=lambda x: x.usage_count, reverse=True)[:5]
            ]
            
            return {
                **basic_stats,
                "recent_knowledge_items": recent_items,
                "top_learning_patterns": top_patterns,
                "knowledge_categories": self._get_knowledge_categories()
            }
        except Exception as e:
            logger.error(f"Error getting detailed knowledge stats: {e}")
            return {}
    
    def _get_knowledge_categories(self) -> Dict[str, int]:
        """Get knowledge items grouped by category"""
        categories = {}
        try:
            for item in self.knowledge_system.knowledge_items.values():
                category = item.metadata.get("category", "uncategorized")
                categories[category] = categories.get(category, 0) + 1
        except Exception as e:
            logger.error(f"Error getting knowledge categories: {e}")
        
        return categories
    
    async def _get_tasks_data(self, status: Optional[str], limit: int) -> List[Dict]:
        """Get tasks data (placeholder - implement based on your director interface)"""
        # This would interface with your actual task storage system
        tasks = []
        try:
            # Get tasks from progress reporter
            for task_id, progress in list(self.progress_reporter.task_progress.items())[:limit]:
                if status and progress.status.value != status:
                    continue
                    
                tasks.append({
                    "id": task_id,
                    "description": progress.task_description,
                    "status": progress.status.value,
                    "progress_percentage": progress.progress_percentage,
                    "created_at": progress.created_at.isoformat(),
                    "allocated_bot": progress.allocated_bot,
                    "cost_incurred": progress.cost_incurred,
                    "estimated_completion": progress.estimated_completion.isoformat() if progress.estimated_completion else None
                })
        except Exception as e:
            logger.error(f"Error getting tasks data: {e}")
        
        return tasks
    
    async def _create_task_from_data(self, task_data: dict):
        """Create task from web form data"""
        # This would interface with your director to create actual tasks
        task_id = str(uuid.uuid4())
        
        # Create a mock task object (replace with actual task creation)
        class MockTask:
            def __init__(self):
                self.id = task_id
                self.description = task_data.get("description", "")
                self.priority = TaskPriority.MEDIUM
                self.status = TaskStatus.PENDING
                self.estimated_tokens = task_data.get("estimated_tokens", 1000)
                self.created_at = datetime.now()
        
        task = MockTask()
        
        # Track in progress reporter
        await self.progress_reporter.track_task(task)
        
        return task
    
    async def _get_realtime_system_data(self) -> Dict:
        """Get real-time system data for WebSocket updates"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "active_tasks": len([p for p in self.progress_reporter.task_progress.values() 
                                  if p.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]]),
                "active_collaborations": len([s for s in self.progress_reporter.collaboration_sessions.values() 
                                            if s.status == "active"]),
                "active_bots": self.bot_synchronizer.get_synchronization_status().get("active_bots", 0),
                "system_health": "healthy",  # Could implement actual health checks
                "recent_events": len([e for e in self.progress_reporter.event_history 
                                    if e.timestamp > datetime.now() - timedelta(minutes=5)])
            }
        except Exception as e:
            logger.error(f"Error getting realtime system data: {e}")
            return {}
    
    async def start_dashboard(self, host: str = "0.0.0.0", port: int = 8080):
        """Start the web dashboard"""
        import uvicorn
        self._running = True
        
        # Start background tasks
        self._background_task = asyncio.create_task(self._background_updates())
        
        logger.info(f"Starting Multi-Bot Orchestrator Dashboard on {host}:{port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def _background_updates(self):
        """Background task for system maintenance and updates"""
        while self._running:
            try:
                # Broadcast system updates to all WebSocket connections
                if self.websocket_connections:
                    system_data = await self._get_realtime_system_data()
                    disconnected = set()
                    
                    for websocket in self.websocket_connections:
                        try:
                            await websocket.send_json({
                                "type": "system_heartbeat",
                                "data": system_data
                            })
                        except:
                            disconnected.add(websocket)
                    
                    # Remove disconnected WebSockets
                    self.websocket_connections -= disconnected
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in background updates: {e}")
                await asyncio.sleep(10)
    
    def stop_dashboard(self):
        """Stop the dashboard"""
        self._running = False
        if self._background_task:
            self._background_task.cancel()


# HTML Templates will be created in the templates directory
def create_dashboard_templates():
    """Create HTML templates for the dashboard"""
    
    templates_dir = "/home/activeloguser/activelog/services/bot-orchestrator/ui/templates"
    os.makedirs(templates_dir, exist_ok=True)
    
    # Main dashboard template
    dashboard_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Bot Orchestrator Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body class="bg-gray-100" x-data="dashboard()">
    <!-- Navigation -->
    <nav class="bg-blue-600 text-white p-4">
        <div class="container mx-auto flex justify-between items-center">
            <h1 class="text-2xl font-bold">
                <i class="fas fa-robot mr-2"></i>
                Multi-Bot Orchestrator
            </h1>
            <div class="flex space-x-4">
                <span class="bg-green-500 px-2 py-1 rounded text-sm" x-text="`${systemData.active_bots || 0} Bots Active`"></span>
                <span class="bg-blue-500 px-2 py-1 rounded text-sm" x-text="`${systemData.active_tasks || 0} Tasks`"></span>
                <span class="bg-purple-500 px-2 py-1 rounded text-sm" x-text="`${systemData.active_collaborations || 0} Collaborations`"></span>
            </div>
        </div>
    </nav>

    <!-- Main Dashboard -->
    <div class="container mx-auto p-6">
        <!-- System Overview Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">Active Bots</p>
                        <p class="text-3xl font-bold text-blue-600" x-text="systemData.active_bots || 0"></p>
                    </div>
                    <i class="fas fa-robot text-4xl text-blue-200"></i>
                </div>
            </div>

            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">Active Tasks</p>
                        <p class="text-3xl font-bold text-green-600" x-text="systemData.active_tasks || 0"></p>
                    </div>
                    <i class="fas fa-tasks text-4xl text-green-200"></i>
                </div>
            </div>

            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">Collaborations</p>
                        <p class="text-3xl font-bold text-purple-600" x-text="systemData.active_collaborations || 0"></p>
                    </div>
                    <i class="fas fa-users text-4xl text-purple-200"></i>
                </div>
            </div>

            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-500 text-sm">System Health</p>
                        <p class="text-xl font-bold text-green-600" x-text="systemData.system_health || 'Unknown'"></p>
                    </div>
                    <i class="fas fa-heartbeat text-4xl text-red-200"></i>
                </div>
            </div>
        </div>

        <!-- Tabs -->
        <div class="bg-white rounded-lg shadow-md mb-8">
            <div class="border-b border-gray-200">
                <nav class="-mb-px flex">
                    <button @click="activeTab = 'overview'" 
                            :class="activeTab === 'overview' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'"
                            class="py-4 px-6 border-b-2 font-medium text-sm">
                        Overview
                    </button>
                    <button @click="activeTab = 'tasks'" 
                            :class="activeTab === 'tasks' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'"
                            class="py-4 px-6 border-b-2 font-medium text-sm">
                        Tasks
                    </button>
                    <button @click="activeTab = 'bots'" 
                            :class="activeTab === 'bots' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'"
                            class="py-4 px-6 border-b-2 font-medium text-sm">
                        Bots
                    </button>
                    <button @click="activeTab = 'collaborations'" 
                            :class="activeTab === 'collaborations' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'"
                            class="py-4 px-6 border-b-2 font-medium text-sm">
                        Collaborations
                    </button>
                    <button @click="activeTab = 'knowledge'" 
                            :class="activeTab === 'knowledge' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'"
                            class="py-4 px-6 border-b-2 font-medium text-sm">
                        Knowledge
                    </button>
                </nav>
            </div>

            <!-- Tab Content -->
            <div class="p-6">
                <!-- Overview Tab -->
                <div x-show="activeTab === 'overview'">
                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <!-- System Performance Chart -->
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h3 class="text-lg font-semibold mb-4">System Performance</h3>
                            <canvas id="performanceChart" width="400" height="200"></canvas>
                        </div>

                        <!-- Recent Activities -->
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <h3 class="text-lg font-semibold mb-4">Recent Activities</h3>
                            <div class="space-y-2" id="recentActivities">
                                <!-- Activities will be populated by JavaScript -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Tasks Tab -->
                <div x-show="activeTab === 'tasks'">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-semibold">Tasks</h3>
                        <button @click="showCreateTask = true" class="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600">
                            <i class="fas fa-plus mr-2"></i>Create Task
                        </button>
                    </div>
                    
                    <div class="overflow-x-auto">
                        <table class="min-w-full table-auto">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-2 text-left">ID</th>
                                    <th class="px-4 py-2 text-left">Description</th>
                                    <th class="px-4 py-2 text-left">Status</th>
                                    <th class="px-4 py-2 text-left">Progress</th>
                                    <th class="px-4 py-2 text-left">Bot</th>
                                    <th class="px-4 py-2 text-left">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="tasksTable">
                                <!-- Tasks will be populated by JavaScript -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Other tabs... -->
                <div x-show="activeTab === 'bots'">
                    <h3 class="text-lg font-semibold mb-4">Bot Management</h3>
                    <div id="botsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <!-- Bots will be populated by JavaScript -->
                    </div>
                </div>

                <div x-show="activeTab === 'collaborations'">
                    <h3 class="text-lg font-semibold mb-4">Active Collaborations</h3>
                    <div id="collaborationsGrid">
                        <!-- Collaborations will be populated by JavaScript -->
                    </div>
                </div>

                <div x-show="activeTab === 'knowledge'">
                    <h3 class="text-lg font-semibold mb-4">Knowledge System</h3>
                    <div id="knowledgeOverview">
                        <!-- Knowledge data will be populated by JavaScript -->
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Create Task Modal -->
    <div x-show="showCreateTask" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
        <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 class="text-lg font-bold text-gray-900 mb-4">Create New Task</h3>
            <form @submit.prevent="createTask()">
                <div class="mb-4">
                    <label class="block text-gray-700 text-sm font-bold mb-2">Description</label>
                    <textarea x-model="newTask.description" class="w-full px-3 py-2 border rounded-lg" rows="3" required></textarea>
                </div>
                <div class="mb-4">
                    <label class="block text-gray-700 text-sm font-bold mb-2">Priority</label>
                    <select x-model="newTask.priority" class="w-full px-3 py-2 border rounded-lg">
                        <option value="LOW">Low</option>
                        <option value="MEDIUM" selected>Medium</option>
                        <option value="HIGH">High</option>
                        <option value="CRITICAL">Critical</option>
                    </select>
                </div>
                <div class="flex justify-end space-x-2">
                    <button @click="showCreateTask = false" type="button" class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                        Cancel
                    </button>
                    <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
                        Create
                    </button>
                </div>
            </form>
        </div>
    </div>

    <script>
        function dashboard() {
            return {
                activeTab: 'overview',
                systemData: {},
                tasks: [],
                bots: [],
                collaborations: [],
                showCreateTask: false,
                newTask: {
                    description: '',
                    priority: 'MEDIUM',
                    estimated_tokens: 1000
                },
                websocket: null,

                async init() {
                    await this.loadSystemData();
                    this.setupWebSocket();
                    this.setupCharts();
                    
                    // Refresh data periodically
                    setInterval(() => this.loadSystemData(), 30000);
                },

                async loadSystemData() {
                    try {
                        const response = await fetch('/api/system/overview');
                        const data = await response.json();
                        this.systemData = data.system || {};
                        
                        // Load specific tab data
                        if (this.activeTab === 'tasks') {
                            await this.loadTasks();
                        } else if (this.activeTab === 'bots') {
                            await this.loadBots();
                        }
                    } catch (error) {
                        console.error('Error loading system data:', error);
                    }
                },

                async loadTasks() {
                    try {
                        const response = await fetch('/api/tasks');
                        const data = await response.json();
                        this.tasks = data.tasks || [];
                        this.renderTasks();
                    } catch (error) {
                        console.error('Error loading tasks:', error);
                    }
                },

                async loadBots() {
                    try {
                        const response = await fetch('/api/bots');
                        const data = await response.json();
                        this.bots = data.bots || [];
                        this.renderBots();
                    } catch (error) {
                        console.error('Error loading bots:', error);
                    }
                },

                async createTask() {
                    try {
                        const response = await fetch('/api/tasks', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(this.newTask)
                        });
                        
                        if (response.ok) {
                            this.showCreateTask = false;
                            this.newTask = { description: '', priority: 'MEDIUM', estimated_tokens: 1000 };
                            await this.loadTasks();
                        }
                    } catch (error) {
                        console.error('Error creating task:', error);
                    }
                },

                setupWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = `${protocol}//${window.location.host}/ws`;
                    
                    this.websocket = new WebSocket(wsUrl);
                    
                    this.websocket.onmessage = (event) => {
                        const message = JSON.parse(event.data);
                        this.handleWebSocketMessage(message);
                    };
                    
                    this.websocket.onclose = () => {
                        // Reconnect after 5 seconds
                        setTimeout(() => this.setupWebSocket(), 5000);
                    };
                },

                handleWebSocketMessage(message) {
                    switch (message.type) {
                        case 'system_update':
                            this.systemData = { ...this.systemData, ...message.data };
                            break;
                        case 'progress_update':
                            this.handleProgressUpdate(message.data);
                            break;
                        case 'collaboration_update':
                            this.handleCollaborationUpdate(message.data);
                            break;
                    }
                },

                handleProgressUpdate(data) {
                    // Update task progress in real-time
                    const taskIndex = this.tasks.findIndex(t => t.id === data.task_id);
                    if (taskIndex !== -1) {
                        this.tasks[taskIndex].progress_percentage = data.progress_percentage || this.tasks[taskIndex].progress_percentage;
                        this.renderTasks();
                    }
                },

                handleCollaborationUpdate(data) {
                    // Handle collaboration updates
                    console.log('Collaboration update:', data);
                },

                renderTasks() {
                    const tbody = document.getElementById('tasksTable');
                    tbody.innerHTML = this.tasks.map(task => `
                        <tr class="border-t">
                            <td class="px-4 py-2 text-sm text-gray-600">${task.id.substring(0, 8)}...</td>
                            <td class="px-4 py-2">${task.description.substring(0, 50)}...</td>
                            <td class="px-4 py-2">
                                <span class="px-2 py-1 rounded text-xs ${this.getStatusColor(task.status)}">
                                    ${task.status}
                                </span>
                            </td>
                            <td class="px-4 py-2">
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-blue-600 h-2 rounded-full" style="width: ${task.progress_percentage}%"></div>
                                </div>
                                <span class="text-xs text-gray-500">${task.progress_percentage.toFixed(1)}%</span>
                            </td>
                            <td class="px-4 py-2 text-sm">${task.allocated_bot || 'None'}</td>
                            <td class="px-4 py-2">
                                <button class="text-blue-600 hover:text-blue-800 text-sm">View</button>
                            </td>
                        </tr>
                    `).join('');
                },

                renderBots() {
                    const grid = document.getElementById('botsGrid');
                    grid.innerHTML = this.bots.map(bot => `
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <div class="flex items-center justify-between mb-2">
                                <h4 class="font-semibold">${bot.bot_id}</h4>
                                <span class="w-3 h-3 rounded-full ${bot.is_active ? 'bg-green-500' : 'bg-red-500'}"></span>
                            </div>
                            <p class="text-sm text-gray-600">Last heartbeat: ${new Date(bot.last_heartbeat).toLocaleTimeString()}</p>
                            <p class="text-sm text-gray-600">Barriers: ${bot.current_barriers}</p>
                            ${bot.collaboration_profile ? `
                                <p class="text-sm text-gray-600">Success rate: ${(bot.collaboration_profile.success_rate * 100).toFixed(1)}%</p>
                            ` : ''}
                        </div>
                    `).join('');
                },

                getStatusColor(status) {
                    const colors = {
                        'PENDING': 'bg-yellow-100 text-yellow-800',
                        'IN_PROGRESS': 'bg-blue-100 text-blue-800',
                        'COMPLETED': 'bg-green-100 text-green-800',
                        'FAILED': 'bg-red-100 text-red-800',
                        'CANCELLED': 'bg-gray-100 text-gray-800'
                    };
                    return colors[status] || 'bg-gray-100 text-gray-800';
                },

                setupCharts() {
                    // Setup Chart.js charts
                    const ctx = document.getElementById('performanceChart').getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: ['1h ago', '45m', '30m', '15m', 'Now'],
                            datasets: [{
                                label: 'Active Tasks',
                                data: [12, 19, 3, 5, 2],
                                borderColor: 'rgb(75, 192, 192)',
                                tension: 0.1
                            }, {
                                label: 'Bot Utilization',
                                data: [8, 15, 10, 12, 7],
                                borderColor: 'rgb(255, 99, 132)',
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
            }
        }
    </script>
</body>
</html>
    '''
    
    with open(os.path.join(templates_dir, "dashboard.html"), "w") as f:
        f.write(dashboard_html)


# Create the templates when module is imported
create_dashboard_templates()