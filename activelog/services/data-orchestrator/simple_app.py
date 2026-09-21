#!/usr/bin/env python3
"""
Simple Data Orchestrator Service
Minimal version to test on port 8204
"""

import asyncio
import logging
from aiohttp import web
import aiohttp_cors
from datetime import datetime
from src.mdm.master_data_manager import MasterDataManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint"""
    return web.json_response({
        'status': 'healthy',
        'service': 'data-orchestrator',
        'timestamp': datetime.utcnow().isoformat(),
        'port': 8204
    })

async def status_endpoint(request):
    """Service status endpoint"""
    return web.json_response({
        'service': 'DMLog Data Orchestrator',
        'description': 'Data flow system for DMLog microservices ecosystem',
        'version': '1.0.0',
        'features': [
            'Data relationship mapping',
            'ETL pipelines',
            'Event streaming',
            'Data quality monitoring',
            'Data governance',
            'Master data management'
        ],
        'port': 8204,
        'endpoints': {
            'health': '/health',
            'status': '/api/status',
            'mdm': '/api/mdm',
            'pipelines': '/api/pipelines',
            'quality': '/api/quality'
        }
    })

async def mdm_demo(request):
    """MDM demo endpoint"""
    try:
        # Initialize MDM with minimal config
        mdm_config = {
            'database_url': 'sqlite:///mdm_demo.db',
            'redis_url': 'redis://localhost:6379',
            'service_endpoints': {
                'dmlog-core': 'http://localhost:8200',
                'character-ai': 'http://localhost:8201'
            }
        }
        
        mdm = MasterDataManager(mdm_config)
        await mdm.initialize()
        
        # Demo entity processing
        demo_user = {
            'id': 'user123',
            'email': 'demo@dmlog.com',
            'username': 'demo_user',
            'full_name': 'Demo User'
        }
        
        result = await mdm.process_entity('user', demo_user, 'dmlog-core')
        
        return web.json_response({
            'status': 'success',
            'demo': 'Master Data Management',
            'processed_entity': result,
            'capabilities': [
                'Entity deduplication',
                'Golden record creation',
                'Cross-service synchronization',
                'Data lineage tracking',
                'Conflict resolution'
            ]
        })
        
    except Exception as e:
        logger.error(f"MDM demo error: {e}")
        return web.json_response({
            'status': 'error',
            'message': str(e),
            'note': 'Redis connection required for full functionality'
        }, status=500)

async def create_app():
    """Create and configure the web application"""
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # Add routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/api/status', status_endpoint)
    app.router.add_get('/api/mdm/demo', mdm_demo)
    app.router.add_get('/', status_endpoint)
    
    # Add CORS to routes
    for resource in app.router.resources():
        cors.add(resource)
    
    return app

async def main():
    """Main entry point"""
    logger.info("🔄 Starting DMLog Data Orchestrator...")
    
    app = await create_app()
    
    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, '0.0.0.0', 8204)
    await site.start()
    
    logger.info("🚀 Data Orchestrator started successfully!")
    logger.info("📡 Server running on http://0.0.0.0:8204")
    logger.info("🎯 Port: 8204 (as requested)")
    logger.info("🔍 Health: http://localhost:8204/health")
    logger.info("📈 Status: http://localhost:8204/api/status")
    logger.info("🔗 Managing data flow for all DMLog services")
    
    try:
        # Keep the server running
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())