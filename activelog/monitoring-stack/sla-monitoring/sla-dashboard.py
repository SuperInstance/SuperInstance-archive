#!/usr/bin/env python3
"""
ActiveLog SLA Dashboard Web Interface
Provides a web interface for viewing SLA status, trends, and reports
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import aiohttp
from aiohttp import web, WSMsgType
import aiohttp_cors
import asyncpg
import jinja2
import yaml
from prometheus_client import generate_latest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SLADashboard:
    """SLA monitoring web dashboard"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.db_pool = None
        self.websocket_connections = set()
        
        # Initialize Jinja2 templates
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader('templates'),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def connect_database(self):
        """Connect to PostgreSQL database"""
        db_config = self.config['database']
        self.db_pool = await asyncpg.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            min_size=2,
            max_size=10
        )
    
    async def get_current_sla_status(self) -> List[Dict[str, Any]]:
        """Get current SLA status for all targets"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT DISTINCT ON (service, sla_name) 
                    service, sla_name, metric_type, current_value, target_value,
                    target_met, error_budget_remaining, measurement_time
                FROM sla_measurements 
                ORDER BY service, sla_name, measurement_time DESC
            ''')
            return [dict(row) for row in rows]
    
    async def get_sla_history(self, service: str, sla_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get SLA history for a specific target"""
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT current_value, target_value, target_met, 
                       error_budget_remaining, measurement_time
                FROM sla_measurements 
                WHERE service = $1 AND sla_name = $2 AND measurement_time >= $3
                ORDER BY measurement_time ASC
            ''', service, sla_name, since)
            return [dict(row) for row in rows]
    
    async def get_recent_violations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent SLA violations"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT service, sla_name, metric_type, violation_start, 
                       violation_end, duration_minutes, severity, resolved
                FROM sla_violations 
                ORDER BY violation_start DESC
                LIMIT $1
            ''', limit)
            return [dict(row) for row in rows]
    
    async def get_service_summary(self) -> Dict[str, Any]:
        """Get service-level SLA summary"""
        async with self.db_pool.acquire() as conn:
            # Get current status counts by service
            service_status = await conn.fetch('''
                SELECT service, 
                       COUNT(*) as total_slas,
                       SUM(CASE WHEN target_met THEN 1 ELSE 0 END) as slas_met,
                       AVG(error_budget_remaining) as avg_error_budget
                FROM (
                    SELECT DISTINCT ON (service, sla_name) 
                        service, target_met, error_budget_remaining
                    FROM sla_measurements 
                    ORDER BY service, sla_name, measurement_time DESC
                ) current_status
                GROUP BY service
            ''')
            
            # Get violation counts by service (last 24h)
            since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
            violation_counts = await conn.fetch('''
                SELECT service, COUNT(*) as violations_24h
                FROM sla_violations 
                WHERE violation_start >= $1
                GROUP BY service
            ''', since_24h)
            
            # Combine results
            services = {}
            for row in service_status:
                services[row['service']] = dict(row)
                services[row['service']]['violations_24h'] = 0
            
            for row in violation_counts:
                if row['service'] in services:
                    services[row['service']]['violations_24h'] = row['violations_24h']
            
            return services
    
    async def index_handler(self, request):
        """Main dashboard page"""
        template = self.jinja_env.get_template('sla_dashboard.html')
        
        # Get data for the dashboard
        current_status = await self.get_current_sla_status()
        recent_violations = await self.get_recent_violations(10)
        service_summary = await self.get_service_summary()
        
        html = template.render(
            current_status=current_status,
            recent_violations=recent_violations,
            service_summary=service_summary,
            current_time=datetime.now(timezone.utc)
        )
        
        return web.Response(text=html, content_type='text/html')
    
    async def api_status_handler(self, request):
        """API endpoint for current SLA status"""
        status = await self.get_current_sla_status()
        return web.json_response(status)
    
    async def api_history_handler(self, request):
        """API endpoint for SLA history"""
        service = request.match_info.get('service')
        sla_name = request.match_info.get('sla_name')
        hours = int(request.query.get('hours', 24))
        
        if not service or not sla_name:
            return web.json_response({'error': 'Service and SLA name required'}, status=400)
        
        history = await self.get_sla_history(service, sla_name, hours)
        return web.json_response(history)
    
    async def api_violations_handler(self, request):
        """API endpoint for recent violations"""
        limit = int(request.query.get('limit', 20))
        violations = await self.get_recent_violations(limit)
        
        # Convert datetime objects to ISO strings
        for violation in violations:
            if violation['violation_start']:
                violation['violation_start'] = violation['violation_start'].isoformat()
            if violation['violation_end']:
                violation['violation_end'] = violation['violation_end'].isoformat()
        
        return web.json_response(violations)
    
    async def api_summary_handler(self, request):
        """API endpoint for service summary"""
        summary = await self.get_service_summary()
        
        # Convert Decimal objects to float for JSON serialization
        for service_data in summary.values():
            if 'avg_error_budget' in service_data and service_data['avg_error_budget']:
                service_data['avg_error_budget'] = float(service_data['avg_error_budget'])
        
        return web.json_response(summary)
    
    async def websocket_handler(self, request):
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        logger.info(f"WebSocket connection added. Total: {len(self.websocket_connections)}")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if data.get('type') == 'ping':
                        await ws.send_str(json.dumps({'type': 'pong'}))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')
                    break
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            logger.info(f"WebSocket connection removed. Total: {len(self.websocket_connections)}")
        
        return ws
    
    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        message = json.dumps(data)
        disconnected = set()
        
        for ws in self.websocket_connections:
            try:
                await ws.send_str(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(ws)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected
    
    async def metrics_handler(self, request):
        """Prometheus metrics endpoint"""
        # This would integrate with the SLA monitor to expose metrics
        return web.Response(text="# Metrics endpoint placeholder\n", content_type='text/plain')
    
    async def periodic_update_task(self):
        """Periodic task to send updates to WebSocket clients"""
        while True:
            try:
                if self.websocket_connections:
                    # Get fresh data
                    current_status = await self.get_current_sla_status()
                    service_summary = await self.get_service_summary()
                    
                    # Convert Decimal objects for JSON serialization
                    for service_data in service_summary.values():
                        if 'avg_error_budget' in service_data and service_data['avg_error_budget']:
                            service_data['avg_error_budget'] = float(service_data['avg_error_budget'])
                    
                    # Broadcast update
                    await self.broadcast_update({
                        'type': 'update',
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'data': {
                            'current_status': current_status,
                            'service_summary': service_summary
                        }
                    })
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in periodic update task: {e}")
                await asyncio.sleep(60)
    
    def create_app(self) -> web.Application:
        """Create and configure the web application"""
        app = web.Application()
        
        # Configure CORS
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Routes
        app.router.add_get('/', self.index_handler)
        app.router.add_get('/api/status', self.api_status_handler)
        app.router.add_get('/api/history/{service}/{sla_name}', self.api_history_handler)
        app.router.add_get('/api/violations', self.api_violations_handler)
        app.router.add_get('/api/summary', self.api_summary_handler)
        app.router.add_get('/ws', self.websocket_handler)
        app.router.add_get('/metrics', self.metrics_handler)
        
        # Add CORS to all routes
        for route in list(app.router.routes()):
            cors.add(route)
        
        # Static files
        app.router.add_static('/static/', path='static', name='static')
        
        return app
    
    async def run(self, host='0.0.0.0', port=8081):
        """Run the SLA dashboard server"""
        await self.connect_database()
        
        app = self.create_app()
        
        # Start periodic update task
        asyncio.create_task(self.periodic_update_task())
        
        # Start the web server
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"SLA Dashboard started at http://{host}:{port}")
        
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down SLA Dashboard...")
        finally:
            await runner.cleanup()

def main():
    """Main entry point"""
    config_path = os.getenv('SLA_CONFIG_PATH', 'sla-config.yml')
    dashboard = SLADashboard(config_path)
    
    host = os.getenv('SLA_DASHBOARD_HOST', '0.0.0.0')
    port = int(os.getenv('SLA_DASHBOARD_PORT', '8081'))
    
    try:
        asyncio.run(dashboard.run(host, port))
    except KeyboardInterrupt:
        logger.info("SLA dashboard stopped by user")
    except Exception as e:
        logger.error(f"SLA dashboard crashed: {e}")
        raise

if __name__ == '__main__':
    main()