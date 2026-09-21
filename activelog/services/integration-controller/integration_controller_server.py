"""
Integration Controller Main Server

The main server that integrates all components and provides unified API endpoints.
Runs on port 8200 and coordinates all integration controller services.

Features:
- REST API for all integration controller components
- WebSocket support for real-time updates
- Service orchestration endpoints
- Workflow management API
- Event bus integration
- Data transformation pipelines
- Saga transaction coordination
- Compensation mechanisms
- Health monitoring dashboard
- Dependency injection container
- API gateway integration
- Service migration tools
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from aiohttp import web, WSMsgType
import aiohttp_cors

# Import all integration controller components
from orchestrator.service_orchestrator import create_service_orchestrator
from workflow.workflow_coordinator import create_workflow_coordinator
from messaging.event_bus import create_event_bus
from pipelines.data_transformer import create_pipeline_engine
from transactions.saga_coordinator import create_saga_coordinator
from recovery.compensation_engine import create_compensation_engine
from monitoring.health_dashboard import create_health_monitoring_dashboard
from injection.dependency_injector import create_dependency_container
from gateway.api_gateway import create_api_gateway
from migration.service_migrator import create_service_migrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegrationController:
    """Main Integration Controller class"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._load_default_config()
        self.app = web.Application()
        self.running = False
        
        # Core components
        self.service_orchestrator = None
        self.workflow_coordinator = None
        self.event_bus = None
        self.pipeline_engine = None
        self.saga_coordinator = None
        self.compensation_engine = None
        self.health_dashboard = None
        self.dependency_container = None
        self.api_gateway = None
        self.service_migrator = None
        
        # Server components
        self.web_server = None
        self.websocket_connections = set()
        
        # Integration with service mesh
        self.service_mesh = None
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            "server": {
                "host": "0.0.0.0",
                "port": 8200,
                "enable_ssl": False
            },
            "service_mesh": {
                "enable_integration": True,
                "consul_host": "localhost",
                "consul_port": 8500
            },
            "event_bus": {
                "enable": True,
                "storage_path": "event_bus.db"
            },
            "workflows": {
                "enable": True,
                "storage_path": "workflow_storage.db"
            },
            "sagas": {
                "enable": True,
                "storage_path": "saga_storage.db"
            },
            "health_monitoring": {
                "enable": True,
                "dashboard_port": 8201,
                "collection_interval": 30
            },
            "api_gateway": {
                "enable": True,
                "gateway_port": 8202
            },
            "logging": {
                "level": "INFO",
                "file": "integration_controller.log"
            }
        }
    
    async def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Integration Controller...")
        
        # Initialize dependency injection container first
        self.dependency_container = create_dependency_container()
        await self._register_services()
        
        # Initialize core orchestration
        self.service_orchestrator = create_service_orchestrator()
        
        # Initialize event bus
        if self.config.get("event_bus", {}).get("enable", True):
            self.event_bus = create_event_bus()
            await self.event_bus.start()
        
        # Initialize workflow coordinator
        if self.config.get("workflows", {}).get("enable", True):
            self.workflow_coordinator = create_workflow_coordinator(self.service_orchestrator)
            await self.workflow_coordinator.start()
        
        # Initialize pipeline engine
        self.pipeline_engine = create_pipeline_engine()
        
        # Initialize saga coordinator
        if self.config.get("sagas", {}).get("enable", True):
            self.saga_coordinator = create_saga_coordinator(self.service_orchestrator, self.event_bus)
        
        # Initialize compensation engine
        self.compensation_engine = create_compensation_engine(self.service_orchestrator)
        
        # Initialize service migrator
        self.service_migrator = create_service_migrator(self.service_orchestrator)
        
        # Initialize health monitoring dashboard
        if self.config.get("health_monitoring", {}).get("enable", True):
            self.health_dashboard = create_health_monitoring_dashboard(self.service_orchestrator)
        
        # Initialize API gateway
        if self.config.get("api_gateway", {}).get("enable", True):
            self.api_gateway = create_api_gateway()
        
        # Setup service mesh integration
        await self._setup_service_mesh_integration()
        
        # Setup web routes
        self._setup_routes()
        
        # Setup CORS
        self._setup_cors()
        
        logger.info("Integration Controller initialized successfully")
    
    async def _register_services(self):
        """Register services in dependency injection container"""
        # Register core services
        self.dependency_container.register_singleton(
            "service_orchestrator", 
            type(self.service_orchestrator) if self.service_orchestrator else object
        )
        
        if self.event_bus:
            self.dependency_container.register_singleton("event_bus", type(self.event_bus))
        
        if self.workflow_coordinator:
            self.dependency_container.register_singleton("workflow_coordinator", type(self.workflow_coordinator))
        
        logger.info("Registered core services in dependency container")
    
    async def _setup_service_mesh_integration(self):
        """Setup integration with service mesh"""
        if not self.config.get("service_mesh", {}).get("enable_integration", True):
            return
        
        try:
            # Import service mesh components
            sys.path.append(str(Path(__file__).parent.parent.parent / "infrastructure" / "service-mesh"))
            
            from service_mesh import initialize_service_mesh, ServiceMeshConfig
            
            # Initialize service mesh
            mesh_config = ServiceMeshConfig(
                consul_host=self.config["service_mesh"]["consul_host"],
                consul_port=self.config["service_mesh"]["consul_port"],
                enable_auto_discovery=True,
                enable_health_monitoring=True
            )
            
            self.service_mesh = initialize_service_mesh(mesh_config)
            
            # Integrate with health dashboard
            if self.health_dashboard:
                self.health_dashboard.set_service_mesh_integration(self.service_mesh)
            
            # Integrate with API gateway
            if self.api_gateway:
                self.api_gateway.set_service_mesh_integration(self.service_mesh)
            
            logger.info("Service mesh integration configured")
            
        except ImportError as e:
            logger.warning(f"Service mesh integration not available: {e}")
        except Exception as e:
            logger.error(f"Failed to setup service mesh integration: {e}")
    
    def _setup_routes(self):
        """Setup API routes"""
        # Health and status endpoints
        self.app.router.add_get('/health', self._health_endpoint)
        self.app.router.add_get('/status', self._status_endpoint)
        self.app.router.add_get('/metrics', self._metrics_endpoint)
        
        # Service orchestration endpoints
        self.app.router.add_get('/api/services', self._list_services)
        self.app.router.add_post('/api/services/{service_name}/actions/{action}', self._execute_service_action)
        self.app.router.add_get('/api/services/{service_name}/health', self._get_service_health)
        
        # Workflow endpoints
        self.app.router.add_post('/api/workflows', self._create_workflow)
        self.app.router.add_post('/api/workflows/{workflow_id}/execute', self._execute_workflow)
        self.app.router.add_get('/api/workflows/{workflow_id}/status', self._get_workflow_status)
        self.app.router.add_post('/api/workflows/{workflow_id}/cancel', self._cancel_workflow)
        
        # Event bus endpoints
        self.app.router.add_post('/api/events/publish', self._publish_event)
        self.app.router.add_post('/api/events/subscribe', self._create_subscription)
        self.app.router.add_get('/api/events/metrics', self._get_event_metrics)
        
        # Data pipeline endpoints
        self.app.router.add_post('/api/pipelines', self._create_pipeline)
        self.app.router.add_post('/api/pipelines/{pipeline_id}/execute', self._execute_pipeline)
        self.app.router.add_get('/api/pipelines/{pipeline_id}/status', self._get_pipeline_status)
        
        # Saga endpoints
        self.app.router.add_post('/api/sagas', self._create_saga)
        self.app.router.add_post('/api/sagas/{saga_id}/execute', self._execute_saga)
        self.app.router.add_get('/api/sagas/{saga_id}/status', self._get_saga_status)
        
        # Compensation endpoints
        self.app.router.add_post('/api/compensation/plans', self._create_compensation_plan)
        self.app.router.add_post('/api/compensation/plans/{plan_id}/execute', self._execute_compensation)
        self.app.router.add_get('/api/compensation/executions/{execution_id}/status', self._get_compensation_status)
        
        # Migration endpoints
        self.app.router.add_post('/api/migrations', self._create_migration_plan)
        self.app.router.add_post('/api/migrations/{plan_id}/execute', self._execute_migration)
        self.app.router.add_get('/api/migrations/{execution_id}/status', self._get_migration_status)
        self.app.router.add_post('/api/migrations/{execution_id}/approve', self._approve_migration)
        
        # Dependency injection endpoints
        self.app.router.add_get('/api/dependencies/services', self._list_registered_services)
        self.app.router.add_post('/api/dependencies/resolve', self._resolve_dependency)
        
        # WebSocket endpoint
        self.app.router.add_get('/ws', self._websocket_handler)
        
        # Static file serving for documentation
        current_dir = Path(__file__).parent
        static_dir = current_dir / "static"
        if static_dir.exists():
            self.app.router.add_static('/', path=static_dir, name='static')
    
    def _setup_cors(self):
        """Setup CORS for API endpoints"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    # Health and Status Endpoints
    async def _health_endpoint(self, request: web.Request) -> web.Response:
        """System health endpoint"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "components": {}
        }
        
        # Check component health
        if self.service_orchestrator:
            health_status["components"]["service_orchestrator"] = {"status": "healthy"}
        
        if self.event_bus and self.event_bus.running:
            health_status["components"]["event_bus"] = {"status": "healthy"}
        
        if self.workflow_coordinator and self.workflow_coordinator.running:
            health_status["components"]["workflow_coordinator"] = {"status": "healthy"}
        
        return web.json_response(health_status)
    
    async def _status_endpoint(self, request: web.Request) -> web.Response:
        """System status endpoint"""
        status = {
            "server": {
                "running": self.running,
                "uptime": "0m",  # Would calculate actual uptime
                "port": self.config["server"]["port"]
            },
            "components": {
                "service_orchestrator": bool(self.service_orchestrator),
                "workflow_coordinator": bool(self.workflow_coordinator),
                "event_bus": bool(self.event_bus),
                "pipeline_engine": bool(self.pipeline_engine),
                "saga_coordinator": bool(self.saga_coordinator),
                "compensation_engine": bool(self.compensation_engine),
                "health_dashboard": bool(self.health_dashboard),
                "api_gateway": bool(self.api_gateway),
                "service_migrator": bool(self.service_migrator)
            },
            "active_connections": len(self.websocket_connections)
        }
        
        return web.json_response(status)
    
    async def _metrics_endpoint(self, request: web.Request) -> web.Response:
        """System metrics endpoint"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_usage": 0.0,  # Would get actual CPU usage
                "memory_usage": 0.0,  # Would get actual memory usage
                "disk_usage": 0.0
            },
            "components": {}
        }
        
        # Get component metrics
        if self.event_bus:
            metrics["components"]["event_bus"] = self.event_bus.get_metrics()
        
        if self.api_gateway:
            metrics["components"]["api_gateway"] = {
                "requests_total": self.api_gateway.metrics.get("requests_total", 0),
                "requests_success": self.api_gateway.metrics.get("requests_success", 0),
                "requests_error": self.api_gateway.metrics.get("requests_error", 0)
            }
        
        return web.json_response(metrics)
    
    # Service Orchestration Endpoints
    async def _list_services(self, request: web.Request) -> web.Response:
        """List all registered services"""
        if not self.service_orchestrator:
            return web.json_response({"error": "Service orchestrator not available"}, status=503)
        
        try:
            services = self.service_orchestrator.list_services()
            return web.json_response({"services": services})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _execute_service_action(self, request: web.Request) -> web.Response:
        """Execute an action on a service"""
        service_name = request.match_info['service_name']
        action = request.match_info['action']
        
        try:
            data = await request.json() if request.can_read_body else {}
            parameters = data.get('parameters', {})
            
            result = await self.service_orchestrator.execute_action(
                service_name, action, parameters
            )
            
            return web.json_response({"result": result})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_service_health(self, request: web.Request) -> web.Response:
        """Get service health status"""
        service_name = request.match_info['service_name']
        
        try:
            health = await self.service_orchestrator.get_service_health(service_name)
            return web.json_response({"health": health})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    # Workflow Endpoints
    async def _create_workflow(self, request: web.Request) -> web.Response:
        """Create a new workflow"""
        if not self.workflow_coordinator:
            return web.json_response({"error": "Workflow coordinator not available"}, status=503)
        
        try:
            data = await request.json()
            workflow_id = self.workflow_coordinator.create_workflow(
                name=data['name'],
                description=data.get('description', ''),
                **data.get('config', {})
            )
            
            return web.json_response({"workflow_id": workflow_id})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _execute_workflow(self, request: web.Request) -> web.Response:
        """Execute a workflow"""
        workflow_id = request.match_info['workflow_id']
        
        try:
            await self.workflow_coordinator.execute_workflow(workflow_id)
            return web.json_response({"status": "started"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_workflow_status(self, request: web.Request) -> web.Response:
        """Get workflow execution status"""
        workflow_id = request.match_info['workflow_id']
        
        try:
            status = self.workflow_coordinator.get_workflow_status(workflow_id)
            if status:
                return web.json_response(status)
            else:
                return web.json_response({"error": "Workflow not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _cancel_workflow(self, request: web.Request) -> web.Response:
        """Cancel a running workflow"""
        workflow_id = request.match_info['workflow_id']
        
        try:
            await self.workflow_coordinator.cancel_workflow(workflow_id)
            return web.json_response({"status": "cancelled"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    # Event Bus Endpoints
    async def _publish_event(self, request: web.Request) -> web.Response:
        """Publish an event to the event bus"""
        if not self.event_bus:
            return web.json_response({"error": "Event bus not available"}, status=503)
        
        try:
            data = await request.json()
            
            from messaging.event_bus import create_event
            event = create_event(
                event_type=data['event_type'],
                source=data['source'],
                data=data.get('data', {}),
                **data.get('metadata', {})
            )
            
            event_id = await self.event_bus.publish(event)
            return web.json_response({"event_id": event_id})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _create_subscription(self, request: web.Request) -> web.Response:
        """Create an event subscription"""
        try:
            data = await request.json()
            # This would create a subscription with a webhook or callback
            # For now, just return success
            return web.json_response({"subscription_id": "sub_" + str(hash(str(data)))})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _get_event_metrics(self, request: web.Request) -> web.Response:
        """Get event bus metrics"""
        if not self.event_bus:
            return web.json_response({"error": "Event bus not available"}, status=503)
        
        metrics = self.event_bus.get_metrics()
        return web.json_response(metrics)
    
    # Data Pipeline Endpoints
    async def _create_pipeline(self, request: web.Request) -> web.Response:
        """Create a data transformation pipeline"""
        try:
            data = await request.json()
            
            from pipelines.data_transformer import create_simple_pipeline
            pipeline = create_simple_pipeline(
                name=data['name'],
                steps=data.get('steps', [])
            )
            
            return web.json_response({"pipeline_id": pipeline.pipeline_id})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _execute_pipeline(self, request: web.Request) -> web.Response:
        """Execute a data pipeline"""
        pipeline_id = request.match_info['pipeline_id']
        
        try:
            data = await request.json()
            input_data = data.get('data')
            
            # This would load the pipeline and execute it
            # For now, return a mock response
            return web.json_response({
                "status": "completed",
                "output": input_data  # Echo input as output for now
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_pipeline_status(self, request: web.Request) -> web.Response:
        """Get pipeline execution status"""
        pipeline_id = request.match_info['pipeline_id']
        
        return web.json_response({
            "pipeline_id": pipeline_id,
            "status": "completed"  # Mock response
        })
    
    # Saga Endpoints
    async def _create_saga(self, request: web.Request) -> web.Response:
        """Create a new saga"""
        if not self.saga_coordinator:
            return web.json_response({"error": "Saga coordinator not available"}, status=503)
        
        try:
            data = await request.json()
            saga_id = self.saga_coordinator.create_saga(
                name=data['name'],
                description=data.get('description', ''),
                **data.get('config', {})
            )
            
            return web.json_response({"saga_id": saga_id})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _execute_saga(self, request: web.Request) -> web.Response:
        """Execute a saga"""
        saga_id = request.match_info['saga_id']
        
        try:
            data = await request.json() if request.can_read_body else {}
            instance_id = data.get('instance_id')
            
            execution = await self.saga_coordinator.execute_saga(saga_id, instance_id)
            
            return web.json_response({
                "execution_id": execution.execution_id,
                "status": execution.status.value
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_saga_status(self, request: web.Request) -> web.Response:
        """Get saga execution status"""
        saga_id = request.match_info['saga_id']
        
        # This would need to be implemented to get saga status by saga_id
        return web.json_response({
            "saga_id": saga_id,
            "status": "completed"  # Mock response
        })
    
    # Compensation Endpoints
    async def _create_compensation_plan(self, request: web.Request) -> web.Response:
        """Create a compensation plan"""
        try:
            data = await request.json()
            plan_id = self.compensation_engine.create_compensation_plan(
                name=data['name'],
                target_entity=data['target_entity'],
                target_entity_type=data['target_entity_type'],
                **data.get('config', {})
            )
            
            return web.json_response({"plan_id": plan_id})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _execute_compensation(self, request: web.Request) -> web.Response:
        """Execute a compensation plan"""
        plan_id = request.match_info['plan_id']
        
        try:
            data = await request.json() if request.can_read_body else {}
            context = data.get('context', {})
            
            execution = await self.compensation_engine.execute_compensation_plan(plan_id, context)
            
            return web.json_response({
                "execution_id": execution.execution_id,
                "status": execution.status.value
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_compensation_status(self, request: web.Request) -> web.Response:
        """Get compensation execution status"""
        execution_id = request.match_info['execution_id']
        
        status = self.compensation_engine.get_compensation_status(execution_id)
        if status:
            return web.json_response(status)
        else:
            return web.json_response({"error": "Execution not found"}, status=404)
    
    # Migration Endpoints
    async def _create_migration_plan(self, request: web.Request) -> web.Response:
        """Create a migration plan"""
        try:
            data = await request.json()
            
            from migration.service_migrator import MigrationStrategy, MigrationType
            
            strategy = MigrationStrategy(data['strategy'])
            migration_type = MigrationType(data['migration_type'])
            
            plan_id = self.service_migrator.create_migration_plan(
                name=data['name'],
                strategy=strategy,
                migration_type=migration_type,
                **data.get('config', {})
            )
            
            return web.json_response({"plan_id": plan_id})
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    async def _execute_migration(self, request: web.Request) -> web.Response:
        """Execute a migration plan"""
        plan_id = request.match_info['plan_id']
        
        try:
            data = await request.json() if request.can_read_body else {}
            approved_by = data.get('approved_by')
            
            execution = await self.service_migrator.execute_migration(plan_id, approved_by)
            
            return web.json_response({
                "execution_id": execution.execution_id,
                "status": execution.status.value
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _get_migration_status(self, request: web.Request) -> web.Response:
        """Get migration execution status"""
        execution_id = request.match_info['execution_id']
        
        status = self.service_migrator.get_migration_status(execution_id)
        if status:
            return web.json_response(status)
        else:
            return web.json_response({"error": "Execution not found"}, status=404)
    
    async def _approve_migration(self, request: web.Request) -> web.Response:
        """Approve a pending migration"""
        execution_id = request.match_info['execution_id']
        
        try:
            data = await request.json()
            approved_by = data['approved_by']
            
            success = await self.service_migrator.approve_migration(execution_id, approved_by)
            
            if success:
                return web.json_response({"status": "approved"})
            else:
                return web.json_response({"error": "Migration not found or not pending approval"}, status=404)
                
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)
    
    # Dependency Injection Endpoints
    async def _list_registered_services(self, request: web.Request) -> web.Response:
        """List all registered services in DI container"""
        services = self.dependency_container.list_services()
        return web.json_response({"services": services})
    
    async def _resolve_dependency(self, request: web.Request) -> web.Response:
        """Resolve a dependency by name or type"""
        try:
            data = await request.json()
            service_name = data.get('service_name')
            
            if service_name:
                # This would actually resolve the dependency
                # For now, return service info
                service_info = self.dependency_container.get_service_info(service_name)
                return web.json_response({"service": service_info})
            else:
                return web.json_response({"error": "service_name required"}, status=400)
                
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    # WebSocket Handler
    async def _websocket_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connections for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        logger.info("WebSocket connection established")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    # Handle incoming WebSocket messages
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "error": "Invalid JSON format"
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            logger.info("WebSocket connection closed")
        
        return ws
    
    async def _handle_websocket_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            # Subscribe to real-time updates
            await ws.send_str(json.dumps({
                "type": "subscription_ack",
                "message": "Subscribed to real-time updates"
            }))
        elif message_type == 'ping':
            # Respond to ping
            await ws.send_str(json.dumps({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            }))
        else:
            await ws.send_str(json.dumps({
                "error": f"Unknown message type: {message_type}"
            }))
    
    async def broadcast_update(self, update: Dict[str, Any]):
        """Broadcast update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = json.dumps(update)
        disconnected = []
        
        for ws in self.websocket_connections.copy():
            try:
                await ws.send_str(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket update: {e}")
                disconnected.append(ws)
        
        # Remove disconnected WebSockets
        for ws in disconnected:
            self.websocket_connections.discard(ws)
    
    async def start(self):
        """Start the integration controller server"""
        logger.info("Starting Integration Controller...")
        
        # Initialize all components
        await self.initialize()
        
        # Start health dashboard if enabled
        if self.health_dashboard and self.config.get("health_monitoring", {}).get("enable", True):
            dashboard_port = self.config.get("health_monitoring", {}).get("dashboard_port", 8201)
            await self.health_dashboard.start(port=dashboard_port)
        
        # Start API gateway if enabled
        if self.api_gateway and self.config.get("api_gateway", {}).get("enable", True):
            gateway_port = self.config.get("api_gateway", {}).get("gateway_port", 8202)
            await self.api_gateway.start_server(port=gateway_port)
        
        # Start main web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        server_config = self.config.get("server", {})
        site = web.TCPSite(
            runner,
            server_config.get("host", "0.0.0.0"),
            server_config.get("port", 8200)
        )
        await site.start()
        
        self.running = True
        self.web_server = runner
        
        logger.info(f"Integration Controller started on http://{server_config.get('host', '0.0.0.0')}:{server_config.get('port', 8200)}")
        
        # Register with service mesh if available
        if self.service_mesh:
            try:
                self.service_mesh.register_service(
                    service_name="integration-controller",
                    port=server_config.get("port", 8200),
                    health_check_path="/health",
                    tags=["integration", "controller", "orchestration"],
                    metadata={"version": "1.0.0", "component": "integration-controller"}
                )
                logger.info("Registered with service mesh")
            except Exception as e:
                logger.warning(f"Failed to register with service mesh: {e}")
    
    async def stop(self):
        """Stop the integration controller server"""
        logger.info("Stopping Integration Controller...")
        
        self.running = False
        
        # Stop all components
        if self.workflow_coordinator:
            await self.workflow_coordinator.stop()
        
        if self.event_bus:
            await self.event_bus.stop()
        
        if self.health_dashboard:
            await self.health_dashboard.stop()
        
        if self.api_gateway:
            await self.api_gateway.stop_server()
        
        if self.dependency_container:
            await self.dependency_container.dispose()
        
        # Stop web server
        if self.web_server:
            await self.web_server.cleanup()
        
        # Close WebSocket connections
        for ws in self.websocket_connections.copy():
            await ws.close()
        
        logger.info("Integration Controller stopped")

async def main():
    """Main entry point"""
    # Load configuration
    config = {}
    config_file = os.environ.get('CONFIG_FILE', 'config.json')
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
    
    # Create and start integration controller
    controller = IntegrationController(config)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(controller.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await controller.start()
        
        # Keep the server running
        while controller.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}")
    finally:
        await controller.stop()

if __name__ == "__main__":
    asyncio.run(main())