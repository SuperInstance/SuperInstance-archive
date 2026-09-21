#!/usr/bin/env python3
"""
Cloud Infrastructure Management System - Main Orchestrator
Coordinates all services: provisioning, billing, scaling, isolation, and API gateway
"""

import asyncio
import logging
import signal
import sys
import yaml
from pathlib import Path
from typing import Dict, Any
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import all service components
from core.database_manager import DatabaseManager
from provisioning.ec2_provisioner import EC2Provisioner
from billing.engine import BillingEngine
from billing.usage_tracker import UsageTracker
from billing.usage_analytics import UsageAnalytics
from billing.report_generator import ReportGenerator
from billing.user_friendly_dashboard import UserFriendlyFinanceDashboard
from billing.cost_calculator import CostCalculator
from billing.payment_processor import PaymentProcessor
from billing.forecasting import UsageForecaster
from scaling.auto_scaler import AutoScaler
from isolation.tenant_manager import TenantManager
from isolation.access_control import AccessControlManager
from enterprise.organization_manager import OrganizationManager
from api.gateway import create_app, service_registry

class CloudInfrastructureOrchestrator:
    """Main orchestrator for the cloud infrastructure system"""
    
    def __init__(self, config_path: str = "config/infrastructure.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = logging.getLogger(__name__)
        
        # Service instances
        self.database_manager = None
        self.ec2_provisioner = None
        self.billing_engine = None
        self.usage_tracker = None
        self.usage_analytics = None
        self.report_generator = None
        self.user_friendly_dashboard = None
        self.cost_calculator = None
        self.payment_processor = None
        self.usage_forecaster = None
        self.auto_scaler = None
        self.tenant_manager = None
        self.access_control = None
        self.organization_manager = None
        self.api_app = None
        
        # Runtime state
        self.running = False
        self.shutdown_event = asyncio.Event()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            self.logger.info(f"Loaded configuration from {self.config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            # Return default configuration
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration if config file is missing"""
        return {
            "aws": {
                "region": "us-west-2",
                "availability_zones": ["us-west-2a", "us-west-2b", "us-west-2c"],
                "default_instance_type": "t3.medium",
                "default_image_id": "ami-0c02fb55956c7d316",
                "max_instances_per_user": 10
            },
            "api": {
                "host": "0.0.0.0",
                "port": 8600,
                "workers": 1
            },
            "billing": {
                "billing_precision": "per_minute",
                "currency": "USD"
            },
            "scaling": {
                "scaling_enabled": True,
                "scaling_interval_seconds": 60
            },
            "isolation": {
                "enable_strict_isolation": True,
                "isolation_level": "vpc"
            }
        }
    
    async def initialize_services(self):
        """Initialize all service components"""
        try:
            self.logger.info("Initializing Cloud Infrastructure services...")
            
            # Initialize database first (required by all other services)
            self.logger.info("Initializing database...")
            db_path = self.config.get('database', {}).get('path', 'data/cloud_infrastructure.db')
            self.database_manager = DatabaseManager(db_path)
            await self.database_manager.initialize()
            
            # Initialize access control system
            self.logger.info("Initializing access control...")
            self.access_control = AccessControlManager(self.config, self.database_manager)
            
            # Initialize tenant management
            self.logger.info("Initializing tenant management...")
            self.tenant_manager = TenantManager(self.config, self.database_manager)
            
            # Initialize EC2 provisioner
            self.logger.info("Initializing EC2 provisioner...")
            self.ec2_provisioner = EC2Provisioner(self.config, self.database_manager)
            
            # Initialize usage tracker
            self.logger.info("Initializing usage tracker...")
            self.usage_tracker = UsageTracker(self.config, self.database_manager)
            
            # Initialize billing engine
            self.logger.info("Initializing billing engine...")
            self.billing_engine = BillingEngine(self.config, self.database_manager)
            
            # Initialize usage analytics
            self.logger.info("Initializing usage analytics...")
            self.usage_analytics = UsageAnalytics(self.database_manager, self.billing_engine)
            
            # Initialize report generator
            self.logger.info("Initializing report generator...")
            self.report_generator = ReportGenerator(self.database_manager, self.usage_analytics, self.billing_engine)
            
            # Initialize user-friendly dashboard
            self.logger.info("Initializing user-friendly finance dashboard...")
            self.user_friendly_dashboard = UserFriendlyFinanceDashboard(
                self.database_manager, self.billing_engine, self.usage_analytics
            )
            
            # Initialize cost calculator
            self.logger.info("Initializing cost calculator...")
            self.cost_calculator = CostCalculator(self.config)
            
            # Initialize payment processor
            self.logger.info("Initializing payment processor...")
            self.payment_processor = PaymentProcessor(self.database_manager, self.config)
            await self.payment_processor.initialize()
            
            # Initialize usage forecaster
            self.logger.info("Initializing usage forecaster...")
            self.usage_forecaster = UsageForecaster(self.database_manager, self.billing_engine)
            await self.usage_forecaster.initialize()
            
            # Initialize organization manager
            self.logger.info("Initializing organization manager...")
            self.organization_manager = OrganizationManager(self.config, self.database_manager)
            
            # Initialize auto scaler
            self.logger.info("Initializing auto scaler...")
            self.auto_scaler = AutoScaler(self.config, self.database_manager, self.ec2_provisioner)
            
            # Register services with the API gateway
            service_registry.register_services(
                database_manager=self.database_manager,
                ec2_provisioner=self.ec2_provisioner,
                billing_engine=self.billing_engine,
                usage_tracker=self.usage_tracker,
                usage_analytics=self.usage_analytics,
                report_generator=self.report_generator,
                user_friendly_dashboard=self.user_friendly_dashboard,
                cost_calculator=self.cost_calculator,
                payment_processor=self.payment_processor,
                usage_forecaster=self.usage_forecaster,
                organization_manager=self.organization_manager,
                auto_scaler=self.auto_scaler,
                tenant_manager=self.tenant_manager,
                access_control=self.access_control
            )
            
            # Create API application
            self.logger.info("Initializing API gateway...")
            self.api_app = create_app(
                self.config,
                database_manager=self.database_manager,
                ec2_provisioner=self.ec2_provisioner,
                billing_engine=self.billing_engine,
                usage_tracker=self.usage_tracker,
                payment_processor=self.payment_processor,
                usage_forecaster=self.usage_forecaster,
                organization_manager=self.organization_manager,
                auto_scaler=self.auto_scaler,
                tenant_manager=self.tenant_manager,
                access_control=self.access_control
            )
            
            self.logger.info("All services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing services: {e}")
            raise
    
    async def start_services(self):
        """Start all background services"""
        try:
            self.logger.info("Starting background services...")
            
            # Start usage tracking
            if self.usage_tracker:
                await self.usage_tracker.start_usage_tracking()
            
            # Start billing engine
            if self.billing_engine:
                await self.billing_engine.start_billing_engine()
            
            # Start auto scaler
            if self.auto_scaler:
                await self.auto_scaler.start_auto_scaling()
            
            self.running = True
            self.logger.info("All background services started")
            
        except Exception as e:
            self.logger.error(f"Error starting services: {e}")
            raise
    
    async def stop_services(self):
        """Stop all background services gracefully"""
        try:
            self.logger.info("Stopping background services...")
            
            # Stop services in reverse order
            if self.auto_scaler:
                await self.auto_scaler.stop_auto_scaling()
            
            if self.billing_engine:
                await self.billing_engine.stop_billing_engine()
            
            if self.usage_tracker:
                await self.usage_tracker.stop_usage_tracking()
            
            self.running = False
            self.logger.info("All background services stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping services: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive system health check"""
        try:
            health_status = {
                'system': 'cloud_infrastructure',
                'status': 'healthy',
                'timestamp': asyncio.get_event_loop().time(),
                'services': {}
            }
            
            overall_healthy = True
            
            # Check each service
            services_to_check = [
                ('database_manager', self.database_manager),
                ('ec2_provisioner', self.ec2_provisioner),
                ('billing_engine', self.billing_engine),
                ('usage_tracker', self.usage_tracker),
                ('organization_manager', self.organization_manager),
                ('auto_scaler', self.auto_scaler),
                ('tenant_manager', self.tenant_manager),
                ('access_control', self.access_control)
            ]
            
            for service_name, service_instance in services_to_check:
                if service_instance and hasattr(service_instance, 'health_check'):
                    try:
                        service_health = await service_instance.health_check()
                        health_status['services'][service_name] = service_health
                        
                        if not service_health.get('healthy', False):
                            overall_healthy = False
                            
                    except Exception as e:
                        health_status['services'][service_name] = {
                            'healthy': False,
                            'error': str(e)
                        }
                        overall_healthy = False
                else:
                    health_status['services'][service_name] = {
                        'healthy': False,
                        'error': 'Service not initialized'
                    }
                    overall_healthy = False
            
            health_status['status'] = 'healthy' if overall_healthy else 'degraded'
            return health_status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                'system': 'cloud_infrastructure',
                'status': 'error',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }
    
    async def create_demo_user(self) -> str:
        """Create a demo user for testing"""
        try:
            from core.models import User, UserTier, BillingStatus, current_timestamp
            
            demo_user = User(
                user_id="demo-user-001",
                email="demo@example.com",
                tier=UserTier.PREMIUM,
                created_at=current_timestamp(),
                billing_status=BillingStatus.ACTIVE,
                monthly_budget=100.0,
                current_spend=0.0
            )
            
            # Create user in database
            success = await self.database_manager.create_user(demo_user)
            
            if success:
                # Create user isolation
                isolation_info = await self.tenant_manager.create_user_isolation(demo_user)
                
                # Create API key for the demo user
                from isolation.access_control import Permission
                
                demo_permissions = [
                    Permission.INSTANCE_CREATE,
                    Permission.INSTANCE_READ,
                    Permission.INSTANCE_UPDATE,
                    Permission.INSTANCE_START,
                    Permission.INSTANCE_STOP,
                    Permission.BILLING_READ,
                    Permission.SCALING_READ,
                    Permission.SCALING_CONFIG
                ]
                
                api_key_info = await self.access_control.create_api_key(
                    demo_user.user_id,
                    "Demo API Key",
                    demo_permissions,
                    expires_in_days=30
                )
                
                self.logger.info(f"Created demo user: {demo_user.user_id}")
                self.logger.info(f"Demo API Key: {api_key_info.get('api_key', 'N/A')}")
                
                return demo_user.user_id
            else:
                raise Exception("Failed to create demo user")
                
        except Exception as e:
            self.logger.error(f"Error creating demo user: {e}")
            return None
    
    async def start_api_server(self):
        """Start the API server"""
        try:
            host = self.config.get('api', {}).get('host', '0.0.0.0')
            port = self.config.get('api', {}).get('port', 8600)
            
            self.logger.info(f"Starting API server on {host}:{port}")
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=self.api_app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                loop="asyncio"
            )
            
            server = uvicorn.Server(config)
            
            # Start server in background task
            server_task = asyncio.create_task(server.serve())
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            # Graceful shutdown
            server.should_exit = True
            await server_task
            
        except Exception as e:
            self.logger.error(f"API server error: {e}")
            raise
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler():
            self.logger.info("Received shutdown signal")
            self.shutdown_event.set()
        
        for sig in [signal.SIGTERM, signal.SIGINT]:
            try:
                asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: signal_handler())
    
    async def run(self):
        """Main run method - orchestrates the entire system"""
        try:
            # Setup signal handlers
            self.setup_signal_handlers()
            
            # Initialize all services
            await self.initialize_services()
            
            # Start background services
            await self.start_services()
            
            # Create demo user if in development mode
            environment = self.config.get('environment', 'development')
            if environment == 'development':
                demo_user_id = await self.create_demo_user()
                if demo_user_id:
                    self.logger.info(f"Demo user created: {demo_user_id}")
            
            # Perform initial health check
            health = await self.health_check()
            self.logger.info(f"System health: {health['status']}")
            
            # Start API server (this will block until shutdown)
            await self.start_api_server()
            
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"System error: {e}")
            raise
        finally:
            # Cleanup
            await self.stop_services()
            self.logger.info("Cloud Infrastructure System stopped")

async def main():
    """Main entry point"""
    try:
        # Create and run orchestrator
        orchestrator = CloudInfrastructureOrchestrator()
        await orchestrator.run()
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logging.error(f"Failed to start system: {e}")
        sys.exit(1)