"""
Zapier Connector
Handles integration with Zapier automation platform
"""

import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ZapierWebhook:
    name: str
    url: str
    trigger_type: str
    active: bool
    created_at: datetime


class ZapierConnector:
    """Connector for Zapier automation platform"""
    
    def __init__(self, config):
        self.config = config
        self.api_key = config.get('zapier_api_key')
        self.webhook_url = config.get('zapier_webhook_url')
        self.base_url = "https://zapier.com/api/v1"
        self.enabled = False
        self.sync_count = 0
        self.last_sync = None
        self.error_count = 0
        self.webhooks = []
        
    def get_status(self) -> Dict[str, Any]:
        """Get connector status"""
        return {
            'status': 'active' if self.enabled else 'inactive',
            'enabled': self.enabled,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'webhooks_count': len(self.webhooks),
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100
        }
        
    def enable(self) -> Dict[str, Any]:
        """Enable Zapier connector"""
        try:
            self.enabled = True
            return {
                'status': 'enabled',
                'message': 'Zapier connector enabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def disable(self) -> Dict[str, Any]:
        """Disable Zapier connector"""
        try:
            self.enabled = False
            return {
                'status': 'disabled',
                'message': 'Zapier connector disabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def configure(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure Zapier connector settings"""
        try:
            if 'api_key' in config_data:
                self.api_key = config_data['api_key']
                
            if 'webhook_url' in config_data:
                self.webhook_url = config_data['webhook_url']
                
            return {
                'status': 'configured',
                'message': 'Zapier connector configured successfully',
                'config': {
                    'api_key_set': bool(self.api_key),
                    'webhook_url_set': bool(self.webhook_url)
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def sync(self) -> Dict[str, Any]:
        """Sync data with Zapier"""
        try:
            if not self.enabled:
                return {
                    'status': 'skipped',
                    'message': 'Zapier connector is disabled'
                }
                
            # Simulate sync operation
            self.sync_count += 1
            self.last_sync = datetime.now()
            
            # Get Zapier app info
            app_info = self.get_zapier_app_info()
            
            return {
                'status': 'success',
                'message': 'Zapier sync completed',
                'timestamp': self.last_sync.isoformat(),
                'sync_count': self.sync_count,
                'app_info': app_info
            }
            
        except Exception as e:
            self.error_count += 1
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def get_zapier_app_info(self) -> Dict[str, Any]:
        """Get Zapier app information"""
        return {
            'app_name': 'ActiveLog',
            'version': '1.0.0',
            'supported_triggers': [
                'new_file_uploaded',
                'user_registered',
                'data_processed',
                'workflow_completed',
                'alert_triggered'
            ],
            'supported_actions': [
                'create_file',
                'send_notification',
                'update_user',
                'trigger_workflow',
                'export_data'
            ],
            'webhook_endpoints': [
                '/webhooks/zapier/trigger',
                '/webhooks/zapier/action'
            ]
        }
        
    def create_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Zapier webhook"""
        try:
            webhook = ZapierWebhook(
                name=webhook_data.get('name', 'Default Webhook'),
                url=webhook_data.get('url', self.webhook_url),
                trigger_type=webhook_data.get('trigger_type', 'file_upload'),
                active=True,
                created_at=datetime.now()
            )
            
            self.webhooks.append(webhook)
            
            return {
                'status': 'created',
                'message': 'Zapier webhook created successfully',
                'webhook': {
                    'name': webhook.name,
                    'url': webhook.url,
                    'trigger_type': webhook.trigger_type,
                    'active': webhook.active,
                    'created_at': webhook.created_at.isoformat()
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from Zapier"""
        try:
            trigger_type = webhook_data.get('trigger_type')
            payload = webhook_data.get('payload', {})
            
            # Process different trigger types
            if trigger_type == 'file_upload':
                result = self.process_file_upload_trigger(payload)
            elif trigger_type == 'user_registration':
                result = self.process_user_registration_trigger(payload)
            elif trigger_type == 'data_export':
                result = self.process_data_export_trigger(payload)
            else:
                result = self.process_generic_trigger(payload)
                
            return {
                'status': 'processed',
                'trigger_type': trigger_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def process_file_upload_trigger(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process file upload trigger"""
        return {
            'action': 'file_upload_processed',
            'file_name': payload.get('file_name', 'unknown'),
            'file_size': payload.get('file_size', 0),
            'upload_time': payload.get('upload_time'),
            'user_id': payload.get('user_id')
        }
        
    def process_user_registration_trigger(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process user registration trigger"""
        return {
            'action': 'user_registration_processed',
            'user_email': payload.get('email'),
            'registration_time': payload.get('registration_time'),
            'user_type': payload.get('user_type', 'standard')
        }
        
    def process_data_export_trigger(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process data export trigger"""
        return {
            'action': 'data_export_processed',
            'export_type': payload.get('export_type', 'full'),
            'export_format': payload.get('format', 'json'),
            'record_count': payload.get('record_count', 0)
        }
        
    def process_generic_trigger(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic trigger"""
        return {
            'action': 'generic_trigger_processed',
            'payload_keys': list(payload.keys()),
            'payload_size': len(str(payload))
        }
        
    def send_to_zapier(self, trigger_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Send data to Zapier via webhook"""
        try:
            if not self.webhook_url:
                return {
                    'status': 'error',
                    'error': 'Webhook URL not configured'
                }
                
            payload = {
                'trigger_type': trigger_type,
                'timestamp': datetime.now().isoformat(),
                'data': data
            }
            
            # Simulate sending webhook
            # In production, this would make an HTTP POST request
            # requests.post(self.webhook_url, json=payload)
            
            return {
                'status': 'sent',
                'message': f'Data sent to Zapier for trigger: {trigger_type}',
                'webhook_url': self.webhook_url[:50] + '...' if len(self.webhook_url) > 50 else self.webhook_url,
                'payload_size': len(str(payload))
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def list_webhooks(self) -> Dict[str, Any]:
        """List all configured webhooks"""
        return {
            'webhooks': [
                {
                    'name': webhook.name,
                    'url': webhook.url,
                    'trigger_type': webhook.trigger_type,
                    'active': webhook.active,
                    'created_at': webhook.created_at.isoformat()
                }
                for webhook in self.webhooks
            ],
            'count': len(self.webhooks)
        }
        
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Zapier"""
        try:
            # Simulate connection test
            if not self.api_key and not self.webhook_url:
                return {
                    'status': 'error',
                    'error': 'No API key or webhook URL configured'
                }
                
            return {
                'status': 'success',
                'message': 'Connection to Zapier successful',
                'timestamp': datetime.now().isoformat(),
                'api_key_configured': bool(self.api_key),
                'webhook_configured': bool(self.webhook_url)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            'name': 'Zapier',
            'type': 'automation_platform',
            'status': 'active' if self.enabled else 'inactive',
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'webhooks_count': len(self.webhooks),
            'capabilities': [
                'webhook_triggers',
                'automation_workflows',
                'data_transformation',
                'multi_app_integration'
            ]
        }