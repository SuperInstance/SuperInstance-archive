#!/usr/bin/env python3
"""
ActiveLog Compute Tiers Service
Intelligent compute resource management with automatic right-sizing, GPU scheduling,
and hybrid cloud orchestration
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

# Import compute tiers components
from core.compute_manager import ComputeManager
from engines.recommendation_engine import RecommendationEngine
from engines.rightsizing_engine import RightsizingEngine
from optimization.cost_performance_optimizer import CostPerformanceOptimizer
from optimization.burst_capacity_manager import BurstCapacityManager
from scheduling.gpu_scheduler import GPUScheduler
from scheduling.sla_scheduler import SLAScheduler
from batch.batch_optimizer import BatchOptimizer
from batch.job_queue_manager import JobQueueManager
from routing.priority_router import PriorityRouter
from hybrid.orchestrator import HybridOrchestrator
from edge.edge_manager import EdgeManager
from green.green_optimizer import GreenEnergyOptimizer
from config.settings import ComputeTiersConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/compute-tiers.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ComputeTiersService:
    """Main service orchestrating all compute tier management components"""
    
    def __init__(self):
        self.config = ComputeTiersConfig()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize AWS clients
        self.ec2_client = boto3.client('ec2', region_name=self.config.aws_region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.config.aws_region)
        self.batch_client = boto3.client('batch', region_name=self.config.aws_region)
        
        # Initialize core components
        self.compute_manager = ComputeManager(self.ec2_client, self.cloudwatch)
        self.recommendation_engine = RecommendationEngine(self.ec2_client, self.cloudwatch)
        self.rightsizing_engine = RightsizingEngine(self.ec2_client, self.cloudwatch)
        self.cost_performance_optimizer = CostPerformanceOptimizer(self.ec2_client, self.cloudwatch)
        self.burst_manager = BurstCapacityManager(self.ec2_client, self.cloudwatch)
        
        # Initialize scheduling components
        self.gpu_scheduler = GPUScheduler(self.ec2_client, self.batch_client)
        self.sla_scheduler = SLAScheduler(self.ec2_client, self.cloudwatch)
        
        # Initialize batch processing components
        self.batch_optimizer = BatchOptimizer(self.batch_client, self.ec2_client)
        self.job_queue_manager = JobQueueManager(self.batch_client)
        
        # Initialize routing and orchestration
        self.priority_router = PriorityRouter(self.config)
        self.hybrid_orchestrator = HybridOrchestrator(self.config)
        self.edge_manager = EdgeManager(self.config)
        self.green_optimizer = GreenEnergyOptimizer(self.config)
        
        # Background tasks
        self.background_tasks = set()
        
        self._setup_routes()
        logger.info("Compute Tiers Service initialized")

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
                    'service': 'compute-tiers',
                    'version': '1.0.0'
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503

        @self.app.route('/recommend', methods=['POST'])
        def recommend_instance():
            """Get instance type recommendations"""
            try:
                data = request.get_json() or {}
                workload_requirements = data.get('workload_requirements', {})
                constraints = data.get('constraints', {})
                
                recommendations = self.recommendation_engine.recommend_instance_types(
                    workload_requirements, constraints
                )
                
                return jsonify(recommendations)
            except Exception as e:
                logger.error(f"Failed to generate recommendations: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/rightsize', methods=['POST'])
        def rightsize_instances():
            """Analyze and recommend right-sizing for instances"""
            try:
                data = request.get_json() or {}
                instance_ids = data.get('instance_ids', [])
                analysis_period_days = data.get('analysis_period_days', 7)
                
                results = self.rightsizing_engine.analyze_instances(
                    instance_ids, analysis_period_days
                )
                
                return jsonify(results)
            except Exception as e:
                logger.error(f"Failed to analyze right-sizing: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/burst/analyze', methods=['POST'])
        def analyze_burst_capacity():
            """Analyze burst capacity needs"""
            try:
                data = request.get_json() or {}
                instance_ids = data.get('instance_ids', [])
                
                analysis = self.burst_manager.analyze_burst_needs(instance_ids)
                return jsonify(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze burst capacity: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/gpu/schedule', methods=['POST'])
        def schedule_gpu_job():
            """Schedule a GPU compute job"""
            try:
                data = request.get_json()
                job_definition = data.get('job_definition')
                resource_requirements = data.get('resource_requirements', {})
                priority = data.get('priority', 'normal')
                
                result = self.gpu_scheduler.schedule_job(
                    job_definition, resource_requirements, priority
                )
                
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to schedule GPU job: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/batch/optimize', methods=['POST'])
        def optimize_batch_jobs():
            """Optimize batch job configuration"""
            try:
                data = request.get_json() or {}
                job_queue = data.get('job_queue')
                optimization_goals = data.get('optimization_goals', ['cost', 'time'])
                
                optimization = self.batch_optimizer.optimize_jobs(
                    job_queue, optimization_goals
                )
                
                return jsonify(optimization)
            except Exception as e:
                logger.error(f"Failed to optimize batch jobs: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/queue/status', methods=['GET'])
        def get_queue_status():
            """Get job queue status"""
            try:
                queue_name = request.args.get('queue_name')
                status = self.job_queue_manager.get_queue_status(queue_name)
                return jsonify(status)
            except Exception as e:
                logger.error(f"Failed to get queue status: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/route', methods=['POST'])
        def route_workload():
            """Route workload to appropriate compute tier"""
            try:
                data = request.get_json()
                workload_spec = data.get('workload_spec')
                routing_preferences = data.get('routing_preferences', {})
                
                routing_decision = self.priority_router.route_workload(
                    workload_spec, routing_preferences
                )
                
                return jsonify(routing_decision)
            except Exception as e:
                logger.error(f"Failed to route workload: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/optimize/cost-performance', methods=['POST'])
        def optimize_cost_performance():
            """Optimize cost vs performance trade-offs"""
            try:
                data = request.get_json() or {}
                workload_profile = data.get('workload_profile', {})
                optimization_target = data.get('target', 'balanced')  # cost, performance, balanced
                
                optimization = self.cost_performance_optimizer.optimize(
                    workload_profile, optimization_target
                )
                
                return jsonify(optimization)
            except Exception as e:
                logger.error(f"Failed to optimize cost-performance: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/sla/select', methods=['POST'])
        def select_sla_instances():
            """Select instances based on SLA requirements"""
            try:
                data = request.get_json()
                sla_requirements = data.get('sla_requirements')
                workload_characteristics = data.get('workload_characteristics', {})
                
                selection = self.sla_scheduler.select_instances(
                    sla_requirements, workload_characteristics
                )
                
                return jsonify(selection)
            except Exception as e:
                logger.error(f"Failed to select SLA instances: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/hybrid/orchestrate', methods=['POST'])
        def orchestrate_hybrid():
            """Orchestrate hybrid local/cloud workload"""
            try:
                data = request.get_json()
                workload_spec = data.get('workload_spec')
                hybrid_preferences = data.get('hybrid_preferences', {})
                
                orchestration = self.hybrid_orchestrator.orchestrate(
                    workload_spec, hybrid_preferences
                )
                
                return jsonify(orchestration)
            except Exception as e:
                logger.error(f"Failed to orchestrate hybrid workload: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/edge/deploy', methods=['POST'])
        def deploy_edge():
            """Deploy workload to edge compute"""
            try:
                data = request.get_json()
                workload_spec = data.get('workload_spec')
                edge_preferences = data.get('edge_preferences', {})
                
                deployment = self.edge_manager.deploy_workload(
                    workload_spec, edge_preferences
                )
                
                return jsonify(deployment)
            except Exception as e:
                logger.error(f"Failed to deploy to edge: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/green/optimize', methods=['POST'])
        def optimize_green_energy():
            """Optimize for green energy usage"""
            try:
                data = request.get_json() or {}
                workload_flexibility = data.get('workload_flexibility', {})
                green_preferences = data.get('green_preferences', {})
                
                optimization = self.green_optimizer.optimize_for_green_energy(
                    workload_flexibility, green_preferences
                )
                
                return jsonify(optimization)
            except Exception as e:
                logger.error(f"Failed to optimize green energy: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/dashboard', methods=['GET'])
        def get_dashboard_data():
            """Get dashboard metrics and status"""
            try:
                dashboard_data = self.compute_manager.get_dashboard_metrics()
                return jsonify(dashboard_data)
            except Exception as e:
                logger.error(f"Failed to get dashboard data: {e}")
                return jsonify({'error': str(e)}), 500

    async def start_background_tasks(self):
        """Start background monitoring and optimization tasks"""
        
        async def rightsizing_monitor():
            """Monitor and suggest right-sizing opportunities"""
            while True:
                try:
                    await self.rightsizing_engine.continuous_analysis()
                    await asyncio.sleep(3600)  # Run every hour
                except Exception as e:
                    logger.error(f"Rightsizing monitor error: {e}")
                    await asyncio.sleep(3600)

        async def burst_capacity_monitor():
            """Monitor burst capacity utilization"""
            while True:
                try:
                    await self.burst_manager.monitor_burst_capacity()
                    await asyncio.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Burst capacity monitor error: {e}")
                    await asyncio.sleep(300)

        async def gpu_scheduler_monitor():
            """Monitor GPU job queue and optimization"""
            while True:
                try:
                    await self.gpu_scheduler.optimize_gpu_usage()
                    await asyncio.sleep(600)  # Check every 10 minutes
                except Exception as e:
                    logger.error(f"GPU scheduler monitor error: {e}")
                    await asyncio.sleep(600)

        async def green_energy_monitor():
            """Monitor green energy opportunities"""
            while True:
                try:
                    await self.green_optimizer.monitor_green_opportunities()
                    await asyncio.sleep(1800)  # Check every 30 minutes
                except Exception as e:
                    logger.error(f"Green energy monitor error: {e}")
                    await asyncio.sleep(1800)

        async def cost_performance_monitor():
            """Monitor cost vs performance optimization opportunities"""
            while True:
                try:
                    await self.cost_performance_optimizer.continuous_optimization()
                    await asyncio.sleep(3600)  # Run every hour
                except Exception as e:
                    logger.error(f"Cost performance monitor error: {e}")
                    await asyncio.sleep(3600)

        # Start background tasks
        tasks = [
            asyncio.create_task(rightsizing_monitor()),
            asyncio.create_task(burst_capacity_monitor()),
            asyncio.create_task(gpu_scheduler_monitor()),
            asyncio.create_task(green_energy_monitor()),
            asyncio.create_task(cost_performance_monitor())
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
            logger.info("Starting Compute Tiers Service on port 8331")
            self.app.run(
                host='0.0.0.0',
                port=8331,
                debug=False,
                threaded=True
            )
            
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            logger.info("Compute Tiers Service stopped")

def main():
    """Main entry point"""
    try:
        # Ensure required directories exist
        os.makedirs('/home/activeloguser/activelog/logs', exist_ok=True)
        os.makedirs('/home/activeloguser/activelog/data/compute-tiers', exist_ok=True)
        
        # Initialize and run service
        service = ComputeTiersService()
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()