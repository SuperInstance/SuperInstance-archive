#!/usr/bin/env python3
"""
ActiveLog Instance Manager
Advanced AWS instance lifecycle management with intelligent cost optimization
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import instance manager components
from core.lifecycle_manager import LifecycleManager
from core.instance_controller import InstanceController
from scheduling.scheduler import ScheduleManager
from scheduling.workload_analyzer import WorkloadAnalyzer
from scaling.auto_scaler import AutoScaler
from scaling.spot_manager import SpotInstanceManager
from cost.cost_optimizer import CostOptimizer
from cost.reserved_instance_optimizer import ReservedInstanceOptimizer
from predictive.predictor import PredictiveScaler
from multicloud.multi_cloud_manager import MultiCloudManager
from monitoring.metrics_collector import MetricsCollector
from config.settings import InstanceManagerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/instance-manager.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class InstanceManagerService:
    """Main service orchestrating all instance management components"""
    
    def __init__(self):
        self.config = InstanceManagerConfig()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize AWS clients
        self.ec2_client = boto3.client('ec2', region_name=self.config.aws_region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.config.aws_region)
        self.pricing_client = boto3.client('pricing', region_name='us-east-1')  # Pricing API only in us-east-1
        
        # Initialize core components
        self.lifecycle_manager = LifecycleManager(self.ec2_client)
        self.instance_controller = InstanceController(self.ec2_client)
        self.schedule_manager = ScheduleManager(self.config)
        self.workload_analyzer = WorkloadAnalyzer(self.cloudwatch)
        self.auto_scaler = AutoScaler(self.ec2_client, self.cloudwatch)
        self.spot_manager = SpotInstanceManager(self.ec2_client)
        self.cost_optimizer = CostOptimizer(self.ec2_client, self.pricing_client)
        self.reserved_optimizer = ReservedInstanceOptimizer(self.ec2_client, self.pricing_client)
        self.predictive_scaler = PredictiveScaler(self.cloudwatch)
        self.multi_cloud_manager = MultiCloudManager(self.config)
        self.metrics_collector = MetricsCollector(self.cloudwatch)
        
        # Background tasks
        self.background_tasks = set()
        
        self._setup_routes()
        logger.info("Instance Manager Service initialized")

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                # Quick AWS connectivity check
                self.ec2_client.describe_regions(MaxResults=1)
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'instance-manager',
                    'version': '1.0.0'
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503

        @self.app.route('/instances', methods=['GET'])
        def list_instances():
            """List all managed instances"""
            try:
                instances = self.instance_controller.list_instances()
                return jsonify({
                    'instances': instances,
                    'count': len(instances)
                })
            except Exception as e:
                logger.error(f"Failed to list instances: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/instances/<instance_id>/start', methods=['POST'])
        def start_instance(instance_id):
            """Start a specific instance"""
            try:
                result = self.instance_controller.start_instance(instance_id)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to start instance {instance_id}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/instances/<instance_id>/stop', methods=['POST'])
        def stop_instance(instance_id):
            """Stop a specific instance"""
            try:
                result = self.instance_controller.stop_instance(instance_id)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to stop instance {instance_id}: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/scaling/analyze', methods=['POST'])
        def analyze_scaling():
            """Analyze current workload and suggest scaling"""
            try:
                data = request.get_json() or {}
                instance_ids = data.get('instance_ids', [])
                
                analysis = self.workload_analyzer.analyze_workload(
                    instance_ids=instance_ids,
                    time_range_hours=data.get('time_range_hours', 24)
                )
                
                return jsonify(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze scaling: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/cost/optimize', methods=['POST'])
        def optimize_costs():
            """Run cost optimization analysis"""
            try:
                data = request.get_json() or {}
                optimization_type = data.get('type', 'all')
                
                if optimization_type == 'spot':
                    results = self.spot_manager.analyze_spot_opportunities()
                elif optimization_type == 'reserved':
                    results = self.reserved_optimizer.analyze_reserved_opportunities()
                else:
                    results = self.cost_optimizer.optimize_all()
                
                return jsonify(results)
            except Exception as e:
                logger.error(f"Failed to optimize costs: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/schedule', methods=['GET'])
        def get_schedules():
            """Get current schedules"""
            try:
                schedules = self.schedule_manager.get_all_schedules()
                return jsonify(schedules)
            except Exception as e:
                logger.error(f"Failed to get schedules: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/schedule', methods=['POST'])
        def create_schedule():
            """Create a new schedule"""
            try:
                data = request.get_json()
                schedule_id = self.schedule_manager.create_schedule(data)
                return jsonify({'schedule_id': schedule_id})
            except Exception as e:
                logger.error(f"Failed to create schedule: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/predictive/forecast', methods=['POST'])
        def get_forecast():
            """Get predictive scaling forecast"""
            try:
                data = request.get_json() or {}
                forecast = self.predictive_scaler.generate_forecast(
                    instance_ids=data.get('instance_ids', []),
                    forecast_hours=data.get('forecast_hours', 24)
                )
                return jsonify(forecast)
            except Exception as e:
                logger.error(f"Failed to generate forecast: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/multicloud/status', methods=['GET'])
        def multicloud_status():
            """Get multi-cloud status"""
            try:
                status = self.multi_cloud_manager.get_status()
                return jsonify(status)
            except Exception as e:
                logger.error(f"Failed to get multi-cloud status: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/metrics/dashboard', methods=['GET'])
        def get_dashboard_metrics():
            """Get metrics for dashboard"""
            try:
                metrics = self.metrics_collector.get_dashboard_metrics()
                return jsonify(metrics)
            except Exception as e:
                logger.error(f"Failed to get dashboard metrics: {e}")
                return jsonify({'error': str(e)}), 500

    async def start_background_tasks(self):
        """Start background monitoring and optimization tasks"""
        
        async def schedule_monitor():
            """Monitor and execute scheduled tasks"""
            while True:
                try:
                    await self.schedule_manager.execute_pending_schedules()
                    await asyncio.sleep(60)  # Check every minute
                except Exception as e:
                    logger.error(f"Schedule monitor error: {e}")
                    await asyncio.sleep(60)

        async def workload_monitor():
            """Monitor workload and trigger scaling"""
            while True:
                try:
                    await self.auto_scaler.check_scaling_needs()
                    await asyncio.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Workload monitor error: {e}")
                    await asyncio.sleep(300)

        async def cost_monitor():
            """Monitor costs and send alerts"""
            while True:
                try:
                    await self.cost_optimizer.check_cost_alerts()
                    await asyncio.sleep(3600)  # Check every hour
                except Exception as e:
                    logger.error(f"Cost monitor error: {e}")
                    await asyncio.sleep(3600)

        async def predictive_monitor():
            """Run predictive scaling analysis"""
            while True:
                try:
                    await self.predictive_scaler.run_prediction_cycle()
                    await asyncio.sleep(1800)  # Run every 30 minutes
                except Exception as e:
                    logger.error(f"Predictive monitor error: {e}")
                    await asyncio.sleep(1800)

        # Start background tasks
        tasks = [
            asyncio.create_task(schedule_monitor()),
            asyncio.create_task(workload_monitor()),
            asyncio.create_task(cost_monitor()),
            asyncio.create_task(predictive_monitor())
        ]
        
        self.background_tasks.update(tasks)
        
        logger.info("Background tasks started")
        
        # Wait for any task to complete (shouldn't happen in normal operation)
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
        
        logger.warning("Background task completed unexpectedly")

    def run(self):
        """Run the service"""
        try:
            # Start background tasks in separate thread
            import threading
            def run_background():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.start_background_tasks())
                loop.close()
            
            background_thread = threading.Thread(target=run_background)
            background_thread.daemon = True
            background_thread.start()
            
            # Start Flask app
            logger.info("Starting Instance Manager Service on port 8330")
            self.app.run(
                host='0.0.0.0',
                port=8330,
                debug=False,
                threaded=True
            )
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            logger.info("Instance Manager Service stopped")

def main():
    """Main entry point"""
    try:
        # Ensure required directories exist
        os.makedirs('/home/activeloguser/activelog/logs', exist_ok=True)
        os.makedirs('/home/activeloguser/activelog/data/instance-manager', exist_ok=True)
        
        # Initialize and run service
        service = InstanceManagerService()
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()