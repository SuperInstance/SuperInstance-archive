#!/usr/bin/env python3
"""
ActiveLog Integration Hub
Main service file for managing all third-party integrations
Port: 8348
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from flask import Flask, jsonify, request
from flask_cors import CORS

# Integration components
from integrations.zapier_connector import ZapierConnector
from integrations.ifttt_integration import IFTTTIntegration
from integrations.power_automate import PowerAutomateConnector
from integrations.google_workspace import GoogleWorkspaceIntegration
from integrations.salesforce_connector import SalesforceConnector
from integrations.quickbooks_sync import QuickBooksSync
from integrations.shopify_integration import ShopifyIntegration
from integrations.wordpress_plugin import WordPressPlugin
from integrations.discord_bot import DiscordBot
from integrations.slack_app import SlackApp
from integrations.teams_integration import TeamsIntegration

from config.integration_config import IntegrationHubConfig
from database.integration_db import IntegrationDatabase


class IntegrationStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


@dataclass
class IntegrationInfo:
    name: str
    status: IntegrationStatus
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    sync_count: int = 0


class IntegrationHubService:
    """Main integration hub service orchestrating all third-party integrations"""
    
    def __init__(self):
        self.config = IntegrationHubConfig()
        self.db = IntegrationDatabase()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize integrations
        self.zapier = ZapierConnector(self.config)
        self.ifttt = IFTTTIntegration(self.config)
        self.power_automate = PowerAutomateConnector(self.config)
        self.google_workspace = GoogleWorkspaceIntegration(self.config)
        self.salesforce = SalesforceConnector(self.config)
        self.quickbooks = QuickBooksSync(self.config)
        self.shopify = ShopifyIntegration(self.config)
        self.wordpress = WordPressPlugin(self.config)
        self.discord = DiscordBot(self.config)
        self.slack = SlackApp(self.config)
        self.teams = TeamsIntegration(self.config)
        
        # Integration registry
        self.integrations = {
            'zapier': self.zapier,
            'ifttt': self.ifttt,
            'power_automate': self.power_automate,
            'google_workspace': self.google_workspace,
            'salesforce': self.salesforce,
            'quickbooks': self.quickbooks,
            'shopify': self.shopify,
            'wordpress': self.wordpress,
            'discord': self.discord,
            'slack': self.slack,
            'teams': self.teams
        }
        
        self.setup_routes()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('integration-hub')
        
    def setup_routes(self):
        """Setup all API routes"""
        
        # Health check
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'service': 'integration-hub',
                'port': 8348,
                'timestamp': datetime.now().isoformat(),
                'integrations_count': len(self.integrations)
            })
            
        # Integration management
        @self.app.route('/integrations', methods=['GET'])
        def list_integrations():
            """List all available integrations"""
            try:
                integrations_status = {}
                for name, integration in self.integrations.items():
                    try:
                        status = integration.get_status()
                        integrations_status[name] = {
                            'name': name,
                            'status': status.get('status', 'unknown'),
                            'last_sync': status.get('last_sync'),
                            'sync_count': status.get('sync_count', 0),
                            'enabled': status.get('enabled', False)
                        }
                    except Exception as e:
                        integrations_status[name] = {
                            'name': name,
                            'status': 'error',
                            'error': str(e),
                            'enabled': False
                        }
                        
                return jsonify({
                    'integrations': integrations_status,
                    'total_count': len(integrations_status)
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/integrations/<integration_name>/status', methods=['GET'])
        def get_integration_status(integration_name):
            """Get status of specific integration"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                integration = self.integrations[integration_name]
                status = integration.get_status()
                
                return jsonify({
                    'name': integration_name,
                    'status': status
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/integrations/<integration_name>/enable', methods=['POST'])
        def enable_integration(integration_name):
            """Enable specific integration"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                integration = self.integrations[integration_name]
                result = integration.enable()
                
                self.logger.info(f"Integration {integration_name} enabled")
                return jsonify({
                    'message': f'Integration {integration_name} enabled',
                    'result': result
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/integrations/<integration_name>/disable', methods=['POST'])
        def disable_integration(integration_name):
            """Disable specific integration"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                integration = self.integrations[integration_name]
                result = integration.disable()
                
                self.logger.info(f"Integration {integration_name} disabled")
                return jsonify({
                    'message': f'Integration {integration_name} disabled',
                    'result': result
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/integrations/<integration_name>/sync', methods=['POST'])
        def trigger_sync(integration_name):
            """Trigger manual sync for specific integration"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                integration = self.integrations[integration_name]
                result = integration.sync()
                
                self.logger.info(f"Manual sync triggered for {integration_name}")
                return jsonify({
                    'message': f'Sync triggered for {integration_name}',
                    'result': result
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/integrations/<integration_name>/configure', methods=['POST'])
        def configure_integration(integration_name):
            """Configure integration settings"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                config_data = request.json
                integration = self.integrations[integration_name]
                result = integration.configure(config_data)
                
                self.logger.info(f"Integration {integration_name} configured")
                return jsonify({
                    'message': f'Integration {integration_name} configured',
                    'result': result
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # Webhook endpoints for integrations
        @self.app.route('/webhooks/<integration_name>', methods=['POST'])
        def handle_webhook(integration_name):
            """Handle incoming webhooks from integrations"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                webhook_data = request.json or request.form.to_dict()
                integration = self.integrations[integration_name]
                
                if hasattr(integration, 'handle_webhook'):
                    result = integration.handle_webhook(webhook_data)
                    return jsonify({
                        'message': 'Webhook processed',
                        'result': result
                    })
                else:
                    return jsonify({'error': 'Webhook not supported for this integration'}), 400
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # Data flow endpoints
        @self.app.route('/data/export/<integration_name>', methods=['POST'])
        def export_to_integration(integration_name):
            """Export data to specific integration"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                export_data = request.json
                integration = self.integrations[integration_name]
                
                if hasattr(integration, 'export_data'):
                    result = integration.export_data(export_data)
                    return jsonify({
                        'message': f'Data exported to {integration_name}',
                        'result': result
                    })
                else:
                    return jsonify({'error': 'Export not supported for this integration'}), 400
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/data/import/<integration_name>', methods=['GET'])
        def import_from_integration(integration_name):
            """Import data from specific integration"""
            try:
                if integration_name not in self.integrations:
                    return jsonify({'error': 'Integration not found'}), 404
                    
                integration = self.integrations[integration_name]
                
                if hasattr(integration, 'import_data'):
                    result = integration.import_data()
                    return jsonify({
                        'message': f'Data imported from {integration_name}',
                        'result': result
                    })
                else:
                    return jsonify({'error': 'Import not supported for this integration'}), 400
                    
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # Workflow automation
        @self.app.route('/workflows', methods=['GET'])
        def list_workflows():
            """List all automation workflows"""
            try:
                workflows = self.db.get_workflows()
                return jsonify({
                    'workflows': workflows,
                    'count': len(workflows)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/workflows', methods=['POST'])
        def create_workflow():
            """Create new automation workflow"""
            try:
                workflow_data = request.json
                workflow_id = self.db.create_workflow(workflow_data)
                
                return jsonify({
                    'message': 'Workflow created',
                    'workflow_id': workflow_id,
                    'workflow': workflow_data
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/workflows/<workflow_id>/execute', methods=['POST'])
        def execute_workflow(workflow_id):
            """Execute specific workflow"""
            try:
                workflow = self.db.get_workflow(workflow_id)
                if not workflow:
                    return jsonify({'error': 'Workflow not found'}), 404
                    
                # Execute workflow steps
                result = self.execute_workflow_steps(workflow)
                
                return jsonify({
                    'message': 'Workflow executed',
                    'workflow_id': workflow_id,
                    'result': result
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # Analytics and reporting
        @self.app.route('/analytics/sync-stats', methods=['GET'])
        def get_sync_stats():
            """Get synchronization statistics"""
            try:
                stats = {}
                for name, integration in self.integrations.items():
                    status = integration.get_status()
                    stats[name] = {
                        'sync_count': status.get('sync_count', 0),
                        'last_sync': status.get('last_sync'),
                        'error_count': status.get('error_count', 0),
                        'success_rate': status.get('success_rate', 0)
                    }
                    
                return jsonify({
                    'sync_statistics': stats,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/analytics/integration-usage', methods=['GET'])
        def get_integration_usage():
            """Get integration usage analytics"""
            try:
                usage_data = self.db.get_integration_usage_stats()
                return jsonify({
                    'usage_statistics': usage_data,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
    def execute_workflow_steps(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow steps in sequence"""
        results = []
        
        for step in workflow.get('steps', []):
            integration_name = step.get('integration')
            action = step.get('action')
            parameters = step.get('parameters', {})
            
            if integration_name in self.integrations:
                integration = self.integrations[integration_name]
                
                try:
                    if hasattr(integration, action):
                        result = getattr(integration, action)(**parameters)
                        results.append({
                            'step': step,
                            'status': 'success',
                            'result': result
                        })
                    else:
                        results.append({
                            'step': step,
                            'status': 'error',
                            'error': f'Action {action} not supported'
                        })
                except Exception as e:
                    results.append({
                        'step': step,
                        'status': 'error',
                        'error': str(e)
                    })
            else:
                results.append({
                    'step': step,
                    'status': 'error',
                    'error': f'Integration {integration_name} not found'
                })
                
        return {
            'workflow_id': workflow.get('id'),
            'execution_time': datetime.now().isoformat(),
            'steps_executed': len(results),
            'results': results
        }
        
    def run(self, host='0.0.0.0', port=8348, debug=False):
        """Run the integration hub service"""
        self.logger.info(f"Starting Integration Hub Service on {host}:{port}")
        self.logger.info(f"Available integrations: {list(self.integrations.keys())}")
        
        try:
            self.app.run(host=host, port=port, debug=debug)
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            raise


def main():
    """Main entry point"""
    service = IntegrationHubService()
    service.run(debug=True)


if __name__ == '__main__':
    main()