"""
ActiveLog Integration Hub - Main Application
Orchestrates all integration components on port 8100
"""

import asyncio
import logging
import signal
import json
from pathlib import Path
from aiohttp import web
from typing import Dict, Any

from service_discovery import ServiceDiscovery
from health_monitor import HealthMonitor
from integration_tests import IntegrationTestEngine
from dependency_mapper import DependencyMapper
from api_gateway import APIGateway
from distributed_tracing import init_tracing, get_tracer
from configuration_manager import ConfigurationManager
from service_orchestrator import ServiceOrchestrator

class IntegrationHub:
    """Central integration hub for all ActiveLog services"""
    
    def __init__(self, port: int = 8100):
        self.port = port
        self.running = False
        
        # Initialize components
        self.discovery = ServiceDiscovery()
        self.health_monitor = HealthMonitor(self.discovery)
        self.config_manager = ConfigurationManager(self.discovery)
        self.dependency_mapper = DependencyMapper(self.discovery)
        self.test_engine = IntegrationTestEngine(self.discovery, self.health_monitor)
        self.orchestrator = ServiceOrchestrator(self.discovery, self.health_monitor, self.config_manager)
        self.api_gateway = APIGateway(self.discovery, self.health_monitor, port=8100)
        
        # Initialize tracing
        self.tracer = init_tracing("integration-hub")
        
        # Web application for management interface
        self.app = web.Application()
        self.setup_management_routes()
        
    def setup_management_routes(self):
        """Setup management web interface routes"""
        # Hub status and overview
        self.app.router.add_get('/', self.dashboard)
        self.app.router.add_get('/api/status', self.get_status)
        self.app.router.add_get('/api/services', self.get_services)
        self.app.router.add_get('/api/health', self.get_health_status)
        
        # Service discovery
        self.app.router.add_get('/api/discovery/services', self.get_discovered_services)
        self.app.router.add_post('/api/discovery/refresh', self.refresh_discovery)
        
        # Health monitoring
        self.app.router.add_get('/api/health/dashboard', self.get_health_dashboard)
        self.app.router.add_get('/api/health/service/{service_name}', self.get_service_health)
        self.app.router.add_get('/api/health/alerts', self.get_health_alerts)
        
        # Integration tests
        self.app.router.add_get('/api/tests/suites', self.get_test_suites)
        self.app.router.add_post('/api/tests/run/{suite_id}', self.run_test_suite)
        self.app.router.add_get('/api/tests/report', self.get_test_report)
        
        # Dependency mapping
        self.app.router.add_get('/api/dependencies/map', self.get_dependency_map)
        self.app.router.add_get('/api/dependencies/analysis', self.get_dependency_analysis)
        self.app.router.add_get('/api/dependencies/service/{service_name}', self.get_service_dependencies)
        
        # Configuration management
        self.app.router.add_get('/api/config/services', self.get_all_configs)
        self.app.router.add_get('/api/config/{service_name}', self.get_service_config)
        self.app.router.add_put('/api/config/{service_name}', self.update_service_config)
        
        # Service orchestration
        self.app.router.add_get('/api/orchestration/status', self.get_orchestration_status)
        self.app.router.add_post('/api/orchestration/start/{service_name}', self.start_service)
        self.app.router.add_post('/api/orchestration/stop/{service_name}', self.stop_service)
        self.app.router.add_post('/api/orchestration/scale/{service_name}', self.scale_service)
        
        # Distributed tracing
        self.app.router.add_get('/api/tracing/traces', self.get_traces)
        self.app.router.add_get('/api/tracing/service-map', self.get_service_map)
        
        # Static files for dashboard
        self.setup_static_dashboard()
    
    def setup_static_dashboard(self):
        """Setup static dashboard files"""
        dashboard_dir = Path("/home/activeloguser/activelog/services/integration-hub/dashboard")
        dashboard_dir.mkdir(exist_ok=True)
        
        # Create simple HTML dashboard
        dashboard_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>ActiveLog Integration Hub</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .status { display: inline-block; padding: 2px 8px; border-radius: 3px; color: white; }
                .status.healthy { background: green; }
                .status.unhealthy { background: red; }
                .status.unknown { background: gray; }
                table { width: 100%; border-collapse: collapse; }
                th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
                .metric { display: inline-block; margin: 10px; padding: 10px; background: #f9f9f9; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>ActiveLog Integration Hub</h1>
                <p>Central management for all 70+ services</p>
            </div>
            
            <div class="section">
                <h2>System Overview</h2>
                <div id="overview-metrics"></div>
            </div>
            
            <div class="section">
                <h2>Service Status</h2>
                <div id="service-status"></div>
            </div>
            
            <div class="section">
                <h2>Health Monitoring</h2>
                <div id="health-status"></div>
            </div>
            
            <div class="section">
                <h2>Integration Tests</h2>
                <div id="test-status"></div>
            </div>
            
            <script>
                async function loadDashboard() {
                    try {
                        // Load overview
                        const statusResponse = await fetch('/api/status');
                        const status = await statusResponse.json();
                        document.getElementById('overview-metrics').innerHTML = `
                            <div class="metric">Services: ${status.total_services}</div>
                            <div class="metric">Healthy: ${status.healthy_services}</div>
                            <div class="metric">Tests Passed: ${status.tests_passed || 0}</div>
                            <div class="metric">Dependencies: ${status.total_dependencies || 0}</div>
                        `;
                        
                        // Load services
                        const servicesResponse = await fetch('/api/services');
                        const services = await servicesResponse.json();
                        let serviceTable = '<table><tr><th>Service</th><th>Status</th><th>Port</th><th>Type</th></tr>';
                        for (const [name, service] of Object.entries(services)) {
                            const statusClass = service.status === 'healthy' ? 'healthy' : 
                                              service.status === 'unhealthy' ? 'unhealthy' : 'unknown';
                            serviceTable += `
                                <tr>
                                    <td>${name}</td>
                                    <td><span class="status ${statusClass}">${service.status}</span></td>
                                    <td>${service.port || 'N/A'}</td>
                                    <td>${service.service_type}</td>
                                </tr>
                            `;
                        }
                        serviceTable += '</table>';
                        document.getElementById('service-status').innerHTML = serviceTable;
                        
                    } catch (error) {
                        console.error('Failed to load dashboard:', error);
                    }
                }
                
                // Load dashboard on page load
                loadDashboard();
                
                // Refresh every 30 seconds
                setInterval(loadDashboard, 30000);
            </script>
        </body>
        </html>
        """
        
        with open(dashboard_dir / "index.html", 'w') as f:
            f.write(dashboard_html)
        
        self.app.router.add_static('/', dashboard_dir, name='dashboard')
    
    async def initialize(self):
        """Initialize all hub components"""
        logging.info("Initializing ActiveLog Integration Hub...")
        
        # Initialize components in order
        await self.discovery.discover_all_services()
        logging.info(f"Service Discovery: Found {len(self.discovery.services)} services")
        
        await self.config_manager.initialize()
        logging.info("Configuration Manager: Initialized")
        
        # Start health monitoring
        asyncio.create_task(self.health_monitor.start_monitoring())
        logging.info("Health Monitor: Started")
        
        await self.test_engine.initialize()
        logging.info(f"Integration Tests: Generated {len(self.test_engine.test_suites)} test suites")
        
        await self.dependency_mapper.discover_all_dependencies()
        analysis = await self.dependency_mapper.analyze_dependencies()
        logging.info(f"Dependency Mapper: Found {analysis.total_dependencies} dependencies")
        
        await self.orchestrator.initialize()
        logging.info("Service Orchestrator: Initialized")
        
        # API Gateway will be started separately
        await self.api_gateway.initialize()
        
        logging.info("🚀 ActiveLog Integration Hub fully initialized")
    
    # Web API handlers
    async def dashboard(self, request):
        """Serve main dashboard"""
        dashboard_path = Path("/home/activeloguser/activelog/services/integration-hub/dashboard/index.html")
        if dashboard_path.exists():
            return web.FileResponse(dashboard_path)
        else:
            return web.Response(text="Dashboard not available", status=404)
    
    async def get_status(self, request):
        """Get overall hub status"""
        services = await self.discovery.discover_all_services()
        healthy_services = len([s for s in services.values() if s.status.value == "healthy"])
        
        # Get test results
        test_report = self.test_engine.get_test_report()
        
        # Get dependency analysis
        if self.dependency_mapper.analysis_cache:
            analysis = self.dependency_mapper.analysis_cache
            total_deps = analysis.total_dependencies
        else:
            total_deps = 0
        
        return web.json_response({
            "status": "running",
            "timestamp": "2025-08-22T22:17:17Z",
            "total_services": len(services),
            "healthy_services": healthy_services,
            "unhealthy_services": len(services) - healthy_services,
            "tests_passed": test_report.get('summary', {}).get('passed', 0),
            "tests_failed": test_report.get('summary', {}).get('failed', 0),
            "total_dependencies": total_deps,
            "orchestration_status": self.orchestrator.get_orchestration_status()
        })
    
    async def get_services(self, request):
        """Get all discovered services"""
        services = {}
        for name, service in self.discovery.services.items():
            services[name] = {
                "name": name,
                "status": service.status.value,
                "service_type": service.service_type.value,
                "port": service.port,
                "host": service.host,
                "endpoints": len(service.endpoints),
                "dependencies": len(service.dependencies),
                "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None
            }
        
        return web.json_response(services)
    
    async def get_health_status(self, request):
        """Get health monitoring status"""
        return web.json_response(self.health_monitor.get_overall_health_dashboard())
    
    async def get_discovered_services(self, request):
        """Get service discovery information"""
        return web.json_response(self.discovery.to_dict())
    
    async def refresh_discovery(self, request):
        """Refresh service discovery"""
        services = await self.discovery.discover_all_services()
        return web.json_response({
            "message": "Service discovery refreshed",
            "services_found": len(services)
        })
    
    async def get_health_dashboard(self, request):
        """Get health dashboard data"""
        return web.json_response(self.health_monitor.get_overall_health_dashboard())
    
    async def get_service_health(self, request):
        """Get health status for specific service"""
        service_name = request.match_info['service_name']
        health_data = self.health_monitor.get_service_health_summary(service_name)
        return web.json_response(health_data)
    
    async def get_health_alerts(self, request):
        """Get active health alerts"""
        all_alerts = []
        for service_name, alerts in self.health_monitor.active_alerts.items():
            for alert in alerts:
                if not alert.resolved:
                    all_alerts.append({
                        "service_name": service_name,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat()
                    })
        
        return web.json_response({"alerts": all_alerts})
    
    async def get_test_suites(self, request):
        """Get all test suites"""
        suites = {}
        for suite_id, suite in self.test_engine.test_suites.items():
            suites[suite_id] = {
                "name": suite.name,
                "description": suite.description,
                "test_count": len(suite.tests),
                "parallel_execution": suite.parallel_execution
            }
        
        return web.json_response(suites)
    
    async def run_test_suite(self, request):
        """Run a specific test suite"""
        suite_id = request.match_info['suite_id']
        results = await self.test_engine.run_test_suite(suite_id)
        return web.json_response(results)
    
    async def get_test_report(self, request):
        """Get comprehensive test report"""
        return web.json_response(self.test_engine.get_test_report())
    
    async def get_dependency_map(self, request):
        """Get service dependency map"""
        if self.dependency_mapper.analysis_cache:
            return web.json_response(self.dependency_mapper.generate_dependency_report())
        else:
            analysis = await self.dependency_mapper.analyze_dependencies()
            return web.json_response(self.dependency_mapper.generate_dependency_report())
    
    async def get_dependency_analysis(self, request):
        """Get dependency analysis"""
        if not self.dependency_mapper.analysis_cache:
            await self.dependency_mapper.analyze_dependencies()
        
        return web.json_response(self.dependency_mapper.to_dict())
    
    async def get_service_dependencies(self, request):
        """Get dependencies for specific service"""
        service_name = request.match_info['service_name']
        deps = self.dependency_mapper.get_service_dependencies(service_name, include_transitive=True)
        return web.json_response(deps)
    
    async def get_all_configs(self, request):
        """Get all service configurations"""
        summary = await self.config_manager.get_config_summary()
        return web.json_response(summary)
    
    async def get_service_config(self, request):
        """Get configuration for specific service"""
        service_name = request.match_info['service_name']
        config = await self.config_manager.get_service_config(service_name)
        return web.json_response(config)
    
    async def update_service_config(self, request):
        """Update service configuration"""
        service_name = request.match_info['service_name']
        data = await request.json()
        
        success = True
        for key, value in data.items():
            if not await self.config_manager.set_config_value(service_name, key, value):
                success = False
        
        return web.json_response({"success": success})
    
    async def get_orchestration_status(self, request):
        """Get orchestration status"""
        return web.json_response(self.orchestrator.get_orchestration_status())
    
    async def start_service(self, request):
        """Start service instances"""
        service_name = request.match_info['service_name']
        data = await request.json()
        instances = data.get('instances', 1)
        
        task_id = await self.orchestrator.start_service(service_name, instances)
        return web.json_response({"task_id": task_id})
    
    async def stop_service(self, request):
        """Stop service instances"""
        service_name = request.match_info['service_name']
        task_id = await self.orchestrator.stop_service(service_name)
        return web.json_response({"task_id": task_id})
    
    async def scale_service(self, request):
        """Scale service instances"""
        service_name = request.match_info['service_name']
        data = await request.json()
        target_instances = data.get('target_instances', 1)
        
        task_id = await self.orchestrator.scale_service(service_name, target_instances)
        return web.json_response({"task_id": task_id})
    
    async def get_traces(self, request):
        """Get distributed traces"""
        if self.tracer and self.tracer.traces:
            traces_data = {}
            for trace_id, trace in list(self.tracer.traces.items())[-50:]:  # Last 50 traces
                traces_data[trace_id] = {
                    "trace_id": trace_id,
                    "span_count": trace.span_count,
                    "service_count": trace.service_count,
                    "duration_ms": trace.duration_ms,
                    "error_count": trace.error_count,
                    "root_service": trace.root_service,
                    "root_operation": trace.root_operation,
                    "start_time": trace.start_time.isoformat() if trace.start_time else None
                }
            return web.json_response(traces_data)
        else:
            return web.json_response({})
    
    async def get_service_map(self, request):
        """Get service map from tracing"""
        if self.tracer:
            service_map = self.tracer.get_service_map()
            return web.json_response(service_map)
        else:
            return web.json_response({"services": {}, "total_services": 0})
    
    async def start_server(self):
        """Start the integration hub server"""
        await self.initialize()
        
        # Start the API Gateway (which includes hub management)
        await self.api_gateway.start_server()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logging.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def shutdown(self):
        """Graceful shutdown"""
        logging.info("Shutting down Integration Hub...")
        
        self.running = False
        
        # Stop components
        await self.health_monitor.stop_monitoring()
        self.config_manager.stop()
        self.orchestrator.stop()
        
        # Clean up tracer
        if self.tracer:
            await self.tracer.collector.flush_spans()
        
        logging.info("Integration Hub shutdown complete")

async def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and start integration hub
    hub = IntegrationHub(port=8100)
    hub.setup_signal_handlers()
    
    try:
        await hub.start_server()
    except KeyboardInterrupt:
        await hub.shutdown()
    except Exception as e:
        logging.error(f"Integration Hub failed: {e}")
        await hub.shutdown()

if __name__ == "__main__":
    asyncio.run(main())