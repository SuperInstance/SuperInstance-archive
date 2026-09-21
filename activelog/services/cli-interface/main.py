#!/usr/bin/env python3
"""
ActiveLog CLI Interface Service
Comprehensive command-line interface system providing CLI tools, SDKs, webhook systems,
and pipeline integrations for all ActiveLog services
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import CLI interface components
from core.cli_manager import CLIManager
from core.api_wrapper import APIWrapper
from webhooks.webhook_manager import WebhookManager
from streaming.event_streamer import EventStreamer
from batch.batch_processor import BatchProcessor
from pipelines.pipeline_manager import PipelineManager
from core.rate_limiter import RateLimiter
from core.error_handler import ErrorHandler
from docs.doc_generator import DocumentationGenerator
from config.settings import CLIInterfaceConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/activeloguser/activelog/logs/cli-interface.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CLIInterfaceService:
    """Main CLI interface service orchestrating all CLI tools and integrations"""
    
    def __init__(self):
        self.config = CLIInterfaceConfig()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize core components
        self.cli_manager = CLIManager(self.config)
        self.api_wrapper = APIWrapper(self.config)
        self.webhook_manager = WebhookManager(self.config)
        self.event_streamer = EventStreamer(self.config)
        self.batch_processor = BatchProcessor(self.config)
        self.pipeline_manager = PipelineManager(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.error_handler = ErrorHandler(self.config)
        self.doc_generator = DocumentationGenerator(self.config)
        
        self._setup_routes()
        logger.info("CLI Interface Service initialized")

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                return jsonify({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat(),
                    'service': 'cli-interface',
                    'version': '1.0.0',
                    'port': 8342
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'unhealthy',
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }), 503

        @self.app.route('/cli/install', methods=['POST'])
        def install_cli():
            """Install CLI tools for specified platform"""
            try:
                data = request.get_json()
                platform = data.get('platform', 'bash')
                install_path = data.get('install_path')
                
                result = self.cli_manager.install_cli(platform, install_path)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to install CLI: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/cli/commands', methods=['GET'])
        def get_available_commands():
            """Get list of available CLI commands"""
            try:
                platform = request.args.get('platform', 'bash')
                commands = self.cli_manager.get_available_commands(platform)
                return jsonify(commands)
            except Exception as e:
                logger.error(f"Failed to get commands: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/cli/execute', methods=['POST'])
        def execute_command():
            """Execute CLI command remotely"""
            try:
                data = request.get_json()
                command = data.get('command')
                args = data.get('args', [])
                environment = data.get('environment', {})
                
                # Rate limiting check
                client_id = request.headers.get('X-Client-ID', 'anonymous')
                if not self.rate_limiter.check_limit(client_id, 'command_execution'):
                    return jsonify({'error': 'Rate limit exceeded'}), 429
                
                result = self.cli_manager.execute_command(command, args, environment)
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to execute command: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/wrapper/call', methods=['POST'])
        def api_wrapper_call():
            """Make API call through wrapper with authentication and retry logic"""
            try:
                data = request.get_json()
                service = data.get('service')
                endpoint = data.get('endpoint')
                method = data.get('method', 'GET')
                payload = data.get('payload')
                headers = data.get('headers', {})
                
                result = self.api_wrapper.make_request(
                    service, endpoint, method, payload, headers
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to make API call: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/webhooks/register', methods=['POST'])
        def register_webhook():
            """Register a new webhook"""
            try:
                data = request.get_json()
                webhook_config = self.webhook_manager.register_webhook(data)
                return jsonify(webhook_config)
            except Exception as e:
                logger.error(f"Failed to register webhook: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/webhooks/<webhook_id>', methods=['POST'])
        def receive_webhook(webhook_id: str):
            """Receive webhook payload"""
            try:
                payload = request.get_json()
                headers = dict(request.headers)
                
                result = self.webhook_manager.process_webhook(
                    webhook_id, payload, headers
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to process webhook: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/webhooks', methods=['GET'])
        def list_webhooks():
            """List all registered webhooks"""
            try:
                webhooks = self.webhook_manager.list_webhooks()
                return jsonify(webhooks)
            except Exception as e:
                logger.error(f"Failed to list webhooks: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/streaming/subscribe', methods=['POST'])
        def subscribe_to_events():
            """Subscribe to event stream"""
            try:
                data = request.get_json()
                subscription_id = self.event_streamer.create_subscription(data)
                return jsonify({'subscription_id': subscription_id})
            except Exception as e:
                logger.error(f"Failed to create subscription: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/streaming/events/<subscription_id>')
        def stream_events(subscription_id: str):
            """Server-sent events endpoint"""
            try:
                return self.event_streamer.stream_events(subscription_id)
            except Exception as e:
                logger.error(f"Failed to stream events: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/batch/submit', methods=['POST'])
        def submit_batch_job():
            """Submit batch processing job"""
            try:
                data = request.get_json()
                job_id = self.batch_processor.submit_job(data)
                return jsonify({'job_id': job_id})
            except Exception as e:
                logger.error(f"Failed to submit batch job: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/batch/status/<job_id>', methods=['GET'])
        def get_batch_status(job_id: str):
            """Get batch job status"""
            try:
                status = self.batch_processor.get_job_status(job_id)
                return jsonify(status)
            except Exception as e:
                logger.error(f"Failed to get batch status: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/pipelines/create', methods=['POST'])
        def create_pipeline():
            """Create a new data pipeline"""
            try:
                data = request.get_json()
                pipeline_id = self.pipeline_manager.create_pipeline(data)
                return jsonify({'pipeline_id': pipeline_id})
            except Exception as e:
                logger.error(f"Failed to create pipeline: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/pipelines/<pipeline_id>/execute', methods=['POST'])
        def execute_pipeline(pipeline_id: str):
            """Execute a data pipeline"""
            try:
                data = request.get_json() or {}
                execution_id = self.pipeline_manager.execute_pipeline(
                    pipeline_id, data
                )
                return jsonify({'execution_id': execution_id})
            except Exception as e:
                logger.error(f"Failed to execute pipeline: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/docs/generate', methods=['POST'])
        def generate_documentation():
            """Generate CLI documentation"""
            try:
                data = request.get_json()
                doc_type = data.get('doc_type', 'markdown')
                target_platform = data.get('platform', 'all')
                
                result = self.doc_generator.generate_documentation(
                    doc_type, target_platform
                )
                return jsonify(result)
            except Exception as e:
                logger.error(f"Failed to generate documentation: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/sdk/download', methods=['GET'])
        def download_sdk():
            """Download SDK package"""
            try:
                language = request.args.get('language', 'python')
                version = request.args.get('version', 'latest')
                
                download_info = self.cli_manager.get_sdk_download_info(
                    language, version
                )
                return jsonify(download_info)
            except Exception as e:
                logger.error(f"Failed to get SDK download info: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/rate-limits/status', methods=['GET'])
        def get_rate_limit_status():
            """Get rate limit status for client"""
            try:
                client_id = request.headers.get('X-Client-ID', 'anonymous')
                status = self.rate_limiter.get_client_status(client_id)
                return jsonify(status)
            except Exception as e:
                logger.error(f"Failed to get rate limit status: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/metrics/usage', methods=['GET'])
        def get_usage_metrics():
            """Get CLI usage metrics and analytics"""
            try:
                time_range = request.args.get('time_range', '24h')
                metrics = self.cli_manager.get_usage_metrics(time_range)
                return jsonify(metrics)
            except Exception as e:
                logger.error(f"Failed to get usage metrics: {e}")
                return jsonify({'error': str(e)}), 500

    def run(self):
        """Run the CLI interface service"""
        try:
            logger.info("Starting CLI Interface Service on port 8342")
            self.app.run(
                host='0.0.0.0',
                port=8342,
                debug=self.config.is_development(),
                threaded=True
            )
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Service error: {e}")
        finally:
            logger.info("CLI Interface Service stopped")


def main():
    """Main entry point"""
    try:
        # Ensure required directories exist
        os.makedirs('/home/activeloguser/activelog/logs', exist_ok=True)
        os.makedirs('/home/activeloguser/activelog/data/cli-interface', exist_ok=True)
        os.makedirs('/home/activeloguser/activelog/services/cli-interface/bin', exist_ok=True)
        
        # Initialize and run service
        service = CLIInterfaceService()
        service.run()
        
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()