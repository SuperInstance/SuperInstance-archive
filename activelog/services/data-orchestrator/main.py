#!/usr/bin/env python3
"""
DMLog Data Orchestrator - Main Service Entry Point
Comprehensive data flow system for DMLog microservices ecosystem
Port: 8204
"""

import asyncio
import logging
import sys
import signal
from typing import Optional
from contextlib import asynccontextmanager

import uvloop
from aiohttp import web, ClientSession, WSMsgType
import aiohttp_cors
import structlog
from prometheus_client import start_http_server, Counter, Histogram, Gauge
import redis.asyncio as redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Internal imports
from src.orchestrator.core import DataOrchestrator
from src.orchestrator.service_registry import ServiceRegistry
from src.orchestrator.relationship_mapper import RelationshipMapper
from src.etl.pipeline_manager import ETLPipelineManager
from src.etl.data_transformer import DataTransformer
from src.streaming.event_hub import EventStreamingHub
from src.streaming.kafka_manager import KafkaManager
from src.quality.quality_monitor import DataQualityMonitor
from src.quality.validation_engine import ValidationEngine
from src.governance.governance_manager import DataGovernanceManager
from src.governance.lineage_tracker import DataLineageTracker
from src.mdm.master_data_manager import MasterDataManager
from src.api.routes import setup_routes
# from src.models.database import Base
from config import Config, load_config, get_database_url
from src.utils.health import HealthChecker
from src.utils.metrics import MetricsCollector


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Metrics
REQUEST_COUNT = Counter('data_orchestrator_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('data_orchestrator_request_duration_seconds', 'Request duration')
ACTIVE_PIPELINES = Gauge('data_orchestrator_active_pipelines', 'Number of active ETL pipelines')
DATA_QUALITY_SCORE = Gauge('data_orchestrator_data_quality_score', 'Overall data quality score', ['service'])
STREAM_EVENTS = Counter('data_orchestrator_stream_events_total', 'Total stream events processed', ['event_type'])


class DataOrchestratorService:
    """Main Data Orchestrator Service"""
    
    def __init__(self, config: Config):
        self.config = config
        self.app = web.Application(middlewares=[
            self._metrics_middleware,
            self._logging_middleware
        ])
        
        # Core components
        self.orchestrator: Optional[DataOrchestrator] = None
        self.service_registry: Optional[ServiceRegistry] = None
        self.relationship_mapper: Optional[RelationshipMapper] = None
        self.etl_manager: Optional[ETLPipelineManager] = None
        self.streaming_hub: Optional[EventStreamingHub] = None
        self.quality_monitor: Optional[DataQualityMonitor] = None
        self.governance_manager: Optional[DataGovernanceManager] = None
        self.mdm_engine: Optional[MasterDataManager] = None
        
        # Infrastructure
        self.db_engine = None
        self.db_session_factory = None
        self.redis_client: Optional[redis.Redis] = None
        self.http_session: Optional[ClientSession] = None
        self.health_checker: Optional[HealthChecker] = None
        self.metrics_collector: Optional[MetricsCollector] = None
        
        # Service state
        self._shutdown_event = asyncio.Event()
        self._background_tasks = set()

    async def _metrics_middleware(self, request, handler):
        """Metrics collection middleware"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await handler(request)
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.path,
                status=response.status
            ).inc()
            return response
        except Exception as e:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.path,
                status=500
            ).inc()
            raise
        finally:
            REQUEST_DURATION.observe(asyncio.get_event_loop().time() - start_time)

    async def _logging_middleware(self, request, handler):
        """Structured logging middleware"""
        request_id = request.headers.get('X-Request-ID', 'unknown')
        start_time = asyncio.get_event_loop().time()
        
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.path,
            remote=request.remote
        )
        
        try:
            response = await handler(request)
            logger.info(
                "Request completed",
                request_id=request_id,
                status=response.status,
                duration=asyncio.get_event_loop().time() - start_time
            )
            return response
        except Exception as e:
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                duration=asyncio.get_event_loop().time() - start_time
            )
            raise

    async def initialize(self):
        """Initialize all service components"""
        logger.info("Initializing Data Orchestrator Service")
        
        try:
            # Database setup
            self.db_engine = create_async_engine(
                get_database_url(self.config),
                echo=self.config.database.echo,
                pool_size=self.config.database.pool_size,
                max_overflow=self.config.database.max_overflow
            )
            
            self.db_session_factory = sessionmaker(
                self.db_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables
            async with self.db_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Redis setup
            self.redis_client = redis.Redis.from_url(
                self.config.redis.url,
                decode_responses=True
            )
            await self.redis_client.ping()
            
            # HTTP client setup
            self.http_session = ClientSession(
                timeout=self.config.http.timeout,
                connector_limit=self.config.http.connector_limit
            )
            
            # Initialize core components
            await self._initialize_core_components()
            await self._initialize_infrastructure_components()
            
            # Setup API routes
            setup_routes(self.app, self)
            
            # Setup CORS
            cors = aiohttp_cors.setup(self.app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Start background tasks
            await self._start_background_tasks()
            
            logger.info("Data Orchestrator Service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Data Orchestrator Service", error=str(e))
            await self.cleanup()
            raise

    async def _initialize_core_components(self):
        """Initialize core orchestration components"""
        
        # Service Registry
        self.service_registry = ServiceRegistry(
            db_session_factory=self.db_session_factory,
            redis_client=self.redis_client,
            http_session=self.http_session,
            config=self.config
        )
        await self.service_registry.initialize()
        
        # Relationship Mapper
        self.relationship_mapper = RelationshipMapper(
            service_registry=self.service_registry,
            db_session_factory=self.db_session_factory,
            config=self.config
        )
        await self.relationship_mapper.initialize()
        
        # ETL Pipeline Manager
        self.etl_manager = ETLPipelineManager(
            service_registry=self.service_registry,
            relationship_mapper=self.relationship_mapper,
            db_session_factory=self.db_session_factory,
            redis_client=self.redis_client,
            config=self.config
        )
        await self.etl_manager.initialize()
        
        # Event Streaming Hub
        self.streaming_hub = EventStreamingHub(
            service_registry=self.service_registry,
            redis_client=self.redis_client,
            config=self.config
        )
        await self.streaming_hub.initialize()
        
        # Data Quality Monitor
        self.quality_monitor = DataQualityMonitor(
            service_registry=self.service_registry,
            db_session_factory=self.db_session_factory,
            config=self.config
        )
        await self.quality_monitor.initialize()
        
        # Data Governance Manager
        self.governance_manager = DataGovernanceManager(
            service_registry=self.service_registry,
            relationship_mapper=self.relationship_mapper,
            db_session_factory=self.db_session_factory,
            config=self.config
        )
        await self.governance_manager.initialize()
        
        # Master Data Manager
        mdm_config = {
            'database_url': get_database_url(self.config).replace('postgresql+asyncpg://', 'postgresql://'),
            'redis_url': self.config.redis.url,
            'service_endpoints': {
                'dmlog-core': 'http://localhost:8200',
                'character-ai': 'http://localhost:8201',
                'world-builder': 'http://localhost:8202',
                'session-manager': 'http://localhost:8203',
                'battle-simulator': 'http://localhost:8205',
                'marketplace': 'http://localhost:8206',
                'voice-synthesis': 'http://localhost:8207'
            }
        }
        self.mdm_engine = MasterDataManager(mdm_config)
        await self.mdm_engine.initialize()
        
        # Main Orchestrator
        self.orchestrator = DataOrchestrator(
            service_registry=self.service_registry,
            relationship_mapper=self.relationship_mapper,
            etl_manager=self.etl_manager,
            streaming_hub=self.streaming_hub,
            quality_monitor=self.quality_monitor,
            governance_manager=self.governance_manager,
            mdm_engine=self.mdm_engine,
            config=self.config
        )
        await self.orchestrator.initialize()

    async def _initialize_infrastructure_components(self):
        """Initialize infrastructure components"""
        
        # Health Checker
        self.health_checker = HealthChecker(
            db_engine=self.db_engine,
            redis_client=self.redis_client,
            service_registry=self.service_registry,
            config=self.config
        )
        
        # Metrics Collector
        self.metrics_collector = MetricsCollector(
            service_registry=self.service_registry,
            etl_manager=self.etl_manager,
            streaming_hub=self.streaming_hub,
            quality_monitor=self.quality_monitor,
            config=self.config
        )

    async def _start_background_tasks(self):
        """Start background monitoring and maintenance tasks"""
        
        # Health monitoring
        task1 = asyncio.create_task(self._health_monitor_loop())
        self._background_tasks.add(task1)
        
        # Metrics collection
        task2 = asyncio.create_task(self._metrics_collection_loop())
        self._background_tasks.add(task2)
        
        # Data quality monitoring
        task3 = asyncio.create_task(self._data_quality_loop())
        self._background_tasks.add(task3)
        
        # ETL pipeline monitoring
        task4 = asyncio.create_task(self._pipeline_monitoring_loop())
        self._background_tasks.add(task4)
        
        # Event stream monitoring
        task5 = asyncio.create_task(self._stream_monitoring_loop())
        self._background_tasks.add(task5)
        
        # Master data synchronization
        task6 = asyncio.create_task(self._mdm_sync_loop())
        self._background_tasks.add(task6)
        
        # Data governance auditing
        task7 = asyncio.create_task(self._governance_audit_loop())
        self._background_tasks.add(task7)

    async def _health_monitor_loop(self):
        """Background health monitoring"""
        while not self._shutdown_event.is_set():
            try:
                await self.health_checker.check_all_services()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error("Health monitoring error", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error

    async def _metrics_collection_loop(self):
        """Background metrics collection"""
        while not self._shutdown_event.is_set():
            try:
                metrics = await self.metrics_collector.collect_all_metrics()
                
                # Update Prometheus metrics
                if metrics.get('active_pipelines'):
                    ACTIVE_PIPELINES.set(metrics['active_pipelines'])
                
                if metrics.get('quality_scores'):
                    for service, score in metrics['quality_scores'].items():
                        DATA_QUALITY_SCORE.labels(service=service).set(score)
                
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error("Metrics collection error", error=str(e))
                await asyncio.sleep(120)

    async def _data_quality_loop(self):
        """Background data quality monitoring"""
        while not self._shutdown_event.is_set():
            try:
                await self.quality_monitor.run_quality_checks()
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error("Data quality monitoring error", error=str(e))
                await asyncio.sleep(600)

    async def _pipeline_monitoring_loop(self):
        """Background ETL pipeline monitoring"""
        while not self._shutdown_event.is_set():
            try:
                await self.etl_manager.monitor_active_pipelines()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error("Pipeline monitoring error", error=str(e))
                await asyncio.sleep(120)

    async def _stream_monitoring_loop(self):
        """Background event stream monitoring"""
        while not self._shutdown_event.is_set():
            try:
                await self.streaming_hub.monitor_stream_health()
                await asyncio.sleep(60)
            except Exception as e:
                logger.error("Stream monitoring error", error=str(e))
                await asyncio.sleep(120)

    async def _mdm_sync_loop(self):
        """Background master data synchronization"""
        while not self._shutdown_event.is_set():
            try:
                # Synchronize different entity types
                entity_types = ['user', 'character', 'campaign', 'session']
                services = ['dmlog-core', 'character-ai', 'world-builder', 'session-manager']
                
                for entity_type in entity_types:
                    for service in services:
                        await self.mdm_engine.synchronize_entities(entity_type, service)
                        
                await asyncio.sleep(1800)  # Sync every 30 minutes
            except Exception as e:
                logger.error("MDM synchronization error", error=str(e))
                await asyncio.sleep(3600)

    async def _governance_audit_loop(self):
        """Background data governance auditing"""
        while not self._shutdown_event.is_set():
            try:
                await self.governance_manager.run_governance_audit()
                await asyncio.sleep(3600)  # Audit every hour
            except Exception as e:
                logger.error("Governance audit error", error=str(e))
                await asyncio.sleep(7200)

    async def start_server(self, host: str = "0.0.0.0", port: int = 8204):
        """Start the HTTP server"""
        logger.info(f"Starting Data Orchestrator server on {host}:{port}")
        
        # Start Prometheus metrics server
        start_http_server(port + 1000)  # Port 9204 for metrics
        
        # Start main server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"🔄 Data Orchestrator started successfully!")
        logger.info(f"📡 Server running on http://{host}:{port}")
        logger.info(f"🎯 Port: {port} (as requested)")
        logger.info(f"📊 Metrics: http://{host}:{port + 1000}/metrics")
        logger.info(f"🔍 Health: http://{host}:{port}/health")
        logger.info(f"📈 Status: http://{host}:{port}/api/status")
        logger.info(f"🔗 Managing data flow for all DMLog services")
        
        # Wait for shutdown
        await self._shutdown_event.wait()

    async def cleanup(self):
        """Clean up resources"""
        logger.info("Shutting down Data Orchestrator Service")
        
        # Signal shutdown to background tasks
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Cleanup components
        components = [
            self.orchestrator,
            self.etl_manager,
            self.streaming_hub,
            self.quality_monitor,
            self.governance_manager,
            self.mdm_engine,
            self.service_registry
        ]
        
        for component in components:
            if component and hasattr(component, 'cleanup'):
                try:
                    await component.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up {component.__class__.__name__}", error=str(e))
        
        # Close connections
        if self.http_session:
            await self.http_session.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.db_engine:
            await self.db_engine.dispose()
        
        logger.info("Data Orchestrator Service shutdown complete")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main service entry point"""
    
    # Set event loop policy for better performance
    if sys.platform != 'win32':
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    setup_logging(config)
    
    # Create service instance
    service = DataOrchestratorService(config)
    service._setup_signal_handlers()
    
    try:
        # Initialize service
        await service.initialize()
        
        # Start server
        await service.start_server(
            host=config.server.host,
            port=config.server.port
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Service startup failed", error=str(e))
        sys.exit(1)
    finally:
        await service.cleanup()


if __name__ == "__main__":
    asyncio.run(main())