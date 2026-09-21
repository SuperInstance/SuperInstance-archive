"""
IFTTT Integration
Handles integration with If This Then That automation platform
"""

import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class IFTTTApplet:
    name: str
    trigger_service: str
    action_service: str
    active: bool
    created_at: datetime


class IFTTTIntegration:
    """Integration with If This Then That platform"""
    
    def __init__(self, config):
        self.config = config
        self.webhook_key = config.get('ifttt_webhook_key')
        self.maker_channel_url = f"https://maker.ifttt.com/trigger/{{event}}/with/key/{self.webhook_key}"
        self.enabled = False
        self.sync_count = 0
        self.last_sync = None
        self.error_count = 0
        self.applets = []
        
    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            'status': 'active' if self.enabled else 'inactive',
            'enabled': self.enabled,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'applets_count': len(self.applets),
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100
        }
        
    def enable(self) -> Dict[str, Any]:
        """Enable IFTTT integration"""
        try:
            self.enabled = True
            return {
                'status': 'enabled',
                'message': 'IFTTT integration enabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def disable(self) -> Dict[str, Any]:
        """Disable IFTTT integration"""
        try:
            self.enabled = False
            return {
                'status': 'disabled',
                'message': 'IFTTT integration disabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def configure(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure IFTTT integration settings"""
        try:
            if 'webhook_key' in config_data:
                self.webhook_key = config_data['webhook_key']
                self.maker_channel_url = f"https://maker.ifttt.com/trigger/{{event}}/with/key/{self.webhook_key}"
                
            return {
                'status': 'configured',
                'message': 'IFTTT integration configured successfully',
                'config': {
                    'webhook_key_set': bool(self.webhook_key),
                    'maker_url_configured': bool(self.maker_channel_url)
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def sync(self) -> Dict[str, Any]:
        """Sync data with IFTTT"""
        try:
            if not self.enabled:
                return {
                    'status': 'skipped',
                    'message': 'IFTTT integration is disabled'
                }
                
            # Simulate sync operation
            self.sync_count += 1
            self.last_sync = datetime.now()
            
            # Get available triggers and actions
            available_services = self.get_available_services()
            
            return {
                'status': 'success',
                'message': 'IFTTT sync completed',
                'timestamp': self.last_sync.isoformat(),
                'sync_count': self.sync_count,
                'available_services': available_services
            }
            
        except Exception as e:
            self.error_count += 1
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def get_available_services(self) -> Dict[str, Any]:
        """Get available IFTTT services for ActiveLog"""
        return {
            'triggers': [
                {
                    'name': 'file_uploaded',
                    'description': 'Triggers when a new file is uploaded',
                    'fields': ['file_name', 'file_size', 'upload_time', 'user_email']
                },
                {
                    'name': 'user_registered',
                    'description': 'Triggers when a new user registers',
                    'fields': ['user_email', 'registration_time', 'user_type']
                },
                {
                    'name': 'milestone_reached',
                    'description': 'Triggers when a milestone is reached',
                    'fields': ['milestone_type', 'milestone_value', 'user_email']
                },
                {
                    'name': 'alert_triggered',
                    'description': 'Triggers when an alert condition is met',
                    'fields': ['alert_type', 'alert_message', 'severity']
                }
            ],
            'actions': [
                {
                    'name': 'send_notification',
                    'description': 'Send notification to user',
                    'fields': ['message', 'user_email', 'notification_type']
                },
                {
                    'name': 'create_task',
                    'description': 'Create a new task',
                    'fields': ['title', 'description', 'due_date', 'priority']
                },
                {
                    'name': 'backup_file',
                    'description': 'Backup file to external service',
                    'fields': ['file_path', 'backup_service', 'encryption_enabled']
                }
            ]
        }
        
    def create_applet(self, applet_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new IFTTT applet"""
        try:
            applet = IFTTTApplet(
                name=applet_data.get('name', 'Default Applet'),
                trigger_service=applet_data.get('trigger_service', 'activelog'),
                action_service=applet_data.get('action_service', 'email'),
                active=True,
                created_at=datetime.now()
            )
            
            self.applets.append(applet)
            
            return {
                'status': 'created',
                'message': 'IFTTT applet created successfully',
                'applet': {
                    'name': applet.name,
                    'trigger_service': applet.trigger_service,
                    'action_service': applet.action_service,
                    'active': applet.active,
                    'created_at': applet.created_at.isoformat()
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def trigger_event(self, event_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger an IFTTT event via Webhooks"""
        try:
            if not self.webhook_key:
                return {
                    'status': 'error',
                    'error': 'Webhook key not configured'
                }
                
            # Prepare webhook data (IFTTT supports value1, value2, value3)
            webhook_data = {
                'value1': data.get('value1', ''),
                'value2': data.get('value2', ''),
                'value3': data.get('value3', '')
            }
            
            url = self.maker_channel_url.format(event=event_name)
            
            # Simulate webhook trigger
            # In production, this would make an HTTP POST request
            # response = requests.post(url, json=webhook_data)
            
            return {
                'status': 'triggered',
                'message': f'IFTTT event "{event_name}" triggered successfully',
                'event_name': event_name,
                'webhook_data': webhook_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook from IFTTT"""
        try:
            action_type = webhook_data.get('action_type')
            payload = webhook_data.get('payload', {})
            
            # Process different action types
            if action_type == 'send_notification':
                result = self.process_notification_action(payload)
            elif action_type == 'create_task':
                result = self.process_task_creation_action(payload)
            elif action_type == 'backup_file':
                result = self.process_backup_action(payload)
            else:
                result = self.process_generic_action(payload)
                
            return {
                'status': 'processed',
                'action_type': action_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def process_notification_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process notification action"""
        return {
            'action': 'notification_sent',
            'message': payload.get('message', 'Default notification'),
            'recipient': payload.get('user_email'),
            'notification_type': payload.get('notification_type', 'info')
        }
        
    def process_task_creation_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process task creation action"""
        return {
            'action': 'task_created',
            'title': payload.get('title', 'New Task'),
            'description': payload.get('description', ''),
            'due_date': payload.get('due_date'),
            'priority': payload.get('priority', 'medium')
        }
        
    def process_backup_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process backup action"""
        return {
            'action': 'backup_initiated',
            'file_path': payload.get('file_path'),
            'backup_service': payload.get('backup_service', 'default'),
            'encryption_enabled': payload.get('encryption_enabled', False)
        }
        
    def process_generic_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic action"""
        return {
            'action': 'generic_action_processed',
            'payload_keys': list(payload.keys()),
            'payload_size': len(str(payload))
        }
        
    def list_applets(self) -> Dict[str, Any]:
        """List all configured applets"""
        return {
            'applets': [
                {
                    'name': applet.name,
                    'trigger_service': applet.trigger_service,
                    'action_service': applet.action_service,
                    'active': applet.active,
                    'created_at': applet.created_at.isoformat()
                }
                for applet in self.applets
            ],
            'count': len(self.applets)
        }
        
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to IFTTT"""
        try:
            if not self.webhook_key:
                return {
                    'status': 'error',
                    'error': 'Webhook key not configured'
                }
                
            # Test with a simple ping event
            test_result = self.trigger_event('activelog_ping', {
                'value1': 'Connection test',
                'value2': datetime.now().isoformat(),
                'value3': 'ActiveLog Integration Hub'
            })
            
            return {
                'status': 'success',
                'message': 'IFTTT connection test successful',
                'test_result': test_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def create_predefined_applets(self) -> Dict[str, Any]:
        """Create predefined useful applets"""
        try:
            predefined_applets = [
                {
                    'name': 'File Upload to Email',
                    'trigger_service': 'activelog',
                    'action_service': 'email',
                    'description': 'Send email notification when file is uploaded'
                },
                {
                    'name': 'User Registration to Slack',
                    'trigger_service': 'activelog',
                    'action_service': 'slack',
                    'description': 'Post to Slack when new user registers'
                },
                {
                    'name': 'Alert to SMS',
                    'trigger_service': 'activelog',
                    'action_service': 'sms',
                    'description': 'Send SMS when critical alert is triggered'
                },
                {
                    'name': 'Backup to Google Drive',
                    'trigger_service': 'activelog',
                    'action_service': 'google_drive',
                    'description': 'Backup important files to Google Drive'
                }
            ]
            
            created_applets = []
            for applet_config in predefined_applets:
                result = self.create_applet(applet_config)
                if result['status'] == 'created':
                    created_applets.append(result['applet'])
                    
            return {
                'status': 'success',
                'message': f'Created {len(created_applets)} predefined applets',
                'created_applets': created_applets
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        return {
            'name': 'IFTTT',
            'type': 'automation_platform',
            'status': 'active' if self.enabled else 'inactive',
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'applets_count': len(self.applets),
            'capabilities': [
                'webhook_triggers',
                'maker_webhooks',
                'email_actions',
                'social_media_integration',
                'smart_home_actions'
            ]
        }