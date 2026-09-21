"""
Microsoft Power Automate Connector
Handles integration with Microsoft Power Automate (formerly Flow)
"""

import json
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import base64


@dataclass
class PowerAutomateFlow:
    name: str
    flow_id: str
    trigger_type: str
    environment: str
    active: bool
    created_at: datetime


class PowerAutomateConnector:
    """Connector for Microsoft Power Automate"""
    
    def __init__(self, config):
        self.config = config
        self.client_id = config.get('power_automate_client_id')
        self.client_secret = config.get('power_automate_client_secret')
        self.tenant_id = config.get('power_automate_tenant_id')
        self.environment_id = config.get('power_automate_environment_id', 'Default-' + str(self.tenant_id) if self.tenant_id else None)
        self.api_base = "https://api.powerautomate.microsoft.com/providers/Microsoft.ProcessSimple/environments"
        self.access_token = None
        self.enabled = False
        self.sync_count = 0
        self.last_sync = None
        self.error_count = 0
        self.flows = []
        
    def get_status(self) -> Dict[str, Any]:
        """Get connector status"""
        return {
            'status': 'active' if self.enabled else 'inactive',
            'enabled': self.enabled,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'flows_count': len(self.flows),
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'environment_id': self.environment_id
        }
        
    def enable(self) -> Dict[str, Any]:
        """Enable Power Automate connector"""
        try:
            self.enabled = True
            # Initialize authentication
            auth_result = self.authenticate()
            return {
                'status': 'enabled',
                'message': 'Power Automate connector enabled successfully',
                'authentication': auth_result
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def disable(self) -> Dict[str, Any]:
        """Disable Power Automate connector"""
        try:
            self.enabled = False
            self.access_token = None
            return {
                'status': 'disabled',
                'message': 'Power Automate connector disabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def configure(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure Power Automate connector settings"""
        try:
            if 'client_id' in config_data:
                self.client_id = config_data['client_id']
                
            if 'client_secret' in config_data:
                self.client_secret = config_data['client_secret']
                
            if 'tenant_id' in config_data:
                self.tenant_id = config_data['tenant_id']
                self.environment_id = config_data.get('environment_id', f'Default-{self.tenant_id}')
                
            return {
                'status': 'configured',
                'message': 'Power Automate connector configured successfully',
                'config': {
                    'client_id_set': bool(self.client_id),
                    'client_secret_set': bool(self.client_secret),
                    'tenant_id_set': bool(self.tenant_id),
                    'environment_id': self.environment_id
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Microsoft Power Automate"""
        try:
            if not all([self.client_id, self.client_secret, self.tenant_id]):
                return {
                    'status': 'error',
                    'error': 'Missing required authentication parameters'
                }
                
            # Simulate OAuth2 authentication flow
            # In production, this would make actual OAuth requests
            auth_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            # Simulate successful authentication
            self.access_token = f"mock_access_token_{datetime.now().timestamp()}"
            
            return {
                'status': 'authenticated',
                'message': 'Successfully authenticated with Microsoft Power Automate',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'scope': 'https://service.flow.microsoft.com/.default'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def sync(self) -> Dict[str, Any]:
        """Sync data with Power Automate"""
        try:
            if not self.enabled:
                return {
                    'status': 'skipped',
                    'message': 'Power Automate connector is disabled'
                }
                
            if not self.access_token:
                auth_result = self.authenticate()
                if auth_result['status'] != 'authenticated':
                    return {
                        'status': 'error',
                        'error': 'Authentication failed',
                        'auth_result': auth_result
                    }
                    
            # Simulate sync operation
            self.sync_count += 1
            self.last_sync = datetime.now()
            
            # Get available connectors and flows
            connectors = self.get_available_connectors()
            flows_info = self.get_flows_info()
            
            return {
                'status': 'success',
                'message': 'Power Automate sync completed',
                'timestamp': self.last_sync.isoformat(),
                'sync_count': self.sync_count,
                'connectors': connectors,
                'flows_info': flows_info
            }
            
        except Exception as e:
            self.error_count += 1
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def get_available_connectors(self) -> Dict[str, Any]:
        """Get available Power Automate connectors"""
        return {
            'microsoft_connectors': [
                {
                    'name': 'Office 365 Outlook',
                    'id': 'shared_outlook',
                    'capabilities': ['send_email', 'read_email', 'create_calendar_event']
                },
                {
                    'name': 'SharePoint',
                    'id': 'shared_sharepoint',
                    'capabilities': ['create_file', 'update_list', 'get_items']
                },
                {
                    'name': 'Microsoft Teams',
                    'id': 'shared_teams',
                    'capabilities': ['post_message', 'create_channel', 'add_member']
                },
                {
                    'name': 'OneDrive for Business',
                    'id': 'shared_onedriveforbusiness',
                    'capabilities': ['upload_file', 'create_folder', 'share_file']
                }
            ],
            'third_party_connectors': [
                {
                    'name': 'ActiveLog',
                    'id': 'activelog_connector',
                    'capabilities': ['file_trigger', 'user_action', 'data_export']
                }
            ],
            'premium_connectors': [
                {
                    'name': 'SQL Server',
                    'id': 'shared_sql',
                    'capabilities': ['execute_query', 'insert_row', 'update_table']
                }
            ]
        }
        
    def get_flows_info(self) -> Dict[str, Any]:
        """Get information about existing flows"""
        return {
            'template_flows': [
                {
                    'name': 'ActiveLog File Upload Notification',
                    'description': 'Send email when new file is uploaded to ActiveLog',
                    'trigger': 'ActiveLog - File Uploaded',
                    'actions': ['Send an email (V2)']
                },
                {
                    'name': 'ActiveLog to SharePoint Sync',
                    'description': 'Copy files from ActiveLog to SharePoint',
                    'trigger': 'ActiveLog - File Added',
                    'actions': ['Create file (SharePoint)']
                },
                {
                    'name': 'User Registration to Teams',
                    'description': 'Post message in Teams when user registers',
                    'trigger': 'ActiveLog - User Registered',
                    'actions': ['Post message in a chat or channel']
                }
            ]
        }
        
    def create_flow(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Power Automate flow"""
        try:
            flow = PowerAutomateFlow(
                name=flow_data.get('name', 'ActiveLog Flow'),
                flow_id=f"flow_{datetime.now().timestamp()}",
                trigger_type=flow_data.get('trigger_type', 'http_request'),
                environment=self.environment_id,
                active=True,
                created_at=datetime.now()
            )
            
            self.flows.append(flow)
            
            # Create flow definition
            flow_definition = self.create_flow_definition(flow_data)
            
            return {
                'status': 'created',
                'message': 'Power Automate flow created successfully',
                'flow': {
                    'name': flow.name,
                    'flow_id': flow.flow_id,
                    'trigger_type': flow.trigger_type,
                    'environment': flow.environment,
                    'active': flow.active,
                    'created_at': flow.created_at.isoformat(),
                    'definition': flow_definition
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def create_flow_definition(self, flow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create flow definition JSON"""
        trigger_type = flow_data.get('trigger_type', 'http_request')
        
        if trigger_type == 'http_request':
            definition = {
                'definition': {
                    '$schema': 'https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#',
                    'contentVersion': '1.0.0.0',
                    'parameters': {},
                    'triggers': {
                        'manual': {
                            'type': 'Request',
                            'kind': 'Http',
                            'inputs': {
                                'schema': {
                                    'type': 'object',
                                    'properties': {
                                        'event_type': {'type': 'string'},
                                        'data': {'type': 'object'}
                                    }
                                }
                            }
                        }
                    },
                    'actions': {
                        'Send_an_email_(V2)': {
                            'runAfter': {},
                            'type': 'ApiConnection',
                            'inputs': {
                                'body': {
                                    'To': flow_data.get('email_recipient', 'admin@activelog.com'),
                                    'Subject': 'ActiveLog Notification',
                                    'Body': '<p>Event: @{triggerBody()?[\'event_type\']}</p>'
                                },
                                'host': {
                                    'connection': {
                                        'name': '@parameters(\'$connections\')[\'outlook\'][\'connectionId\']'
                                    }
                                },
                                'method': 'post',
                                'path': '/v2/Mail'
                            }
                        }
                    }
                }
            }
        else:
            definition = {
                'definition': {
                    'triggers': {
                        'activelog_trigger': {
                            'type': 'ApiConnection',
                            'inputs': {
                                'host': {
                                    'connection': {
                                        'name': '@parameters(\'$connections\')[\'activelog\'][\'connectionId\']'
                                    }
                                }
                            }
                        }
                    },
                    'actions': {}
                }
            }
            
        return definition
        
    def trigger_flow(self, flow_id: str, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger a specific flow"""
        try:
            # Find the flow
            flow = next((f for f in self.flows if f.flow_id == flow_id), None)
            if not flow:
                return {
                    'status': 'error',
                    'error': f'Flow with ID {flow_id} not found'
                }
                
            if not flow.active:
                return {
                    'status': 'error',
                    'error': f'Flow {flow.name} is not active'
                }
                
            # Simulate flow execution
            execution_id = f"exec_{datetime.now().timestamp()}"
            
            return {
                'status': 'triggered',
                'message': f'Flow "{flow.name}" triggered successfully',
                'flow_id': flow_id,
                'execution_id': execution_id,
                'trigger_data': trigger_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming webhook for flow execution"""
        try:
            flow_id = webhook_data.get('flow_id')
            action_type = webhook_data.get('action_type')
            payload = webhook_data.get('payload', {})
            
            if not flow_id:
                return {
                    'status': 'error',
                    'error': 'Flow ID not provided in webhook'
                }
                
            # Process the action
            if action_type == 'send_email':
                result = self.process_email_action(payload)
            elif action_type == 'create_sharepoint_file':
                result = self.process_sharepoint_action(payload)
            elif action_type == 'post_teams_message':
                result = self.process_teams_action(payload)
            else:
                result = self.process_generic_action(payload)
                
            return {
                'status': 'processed',
                'flow_id': flow_id,
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
            
    def process_email_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process email sending action"""
        return {
            'action': 'email_sent',
            'recipient': payload.get('to', 'default@example.com'),
            'subject': payload.get('subject', 'ActiveLog Notification'),
            'body_preview': payload.get('body', '')[:100] + '...',
            'sent_at': datetime.now().isoformat()
        }
        
    def process_sharepoint_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process SharePoint file creation action"""
        return {
            'action': 'sharepoint_file_created',
            'site_url': payload.get('site_url', 'https://company.sharepoint.com'),
            'library': payload.get('library', 'Documents'),
            'file_name': payload.get('file_name', 'document.txt'),
            'created_at': datetime.now().isoformat()
        }
        
    def process_teams_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Teams message posting action"""
        return {
            'action': 'teams_message_posted',
            'team_id': payload.get('team_id', 'default_team'),
            'channel': payload.get('channel', 'General'),
            'message': payload.get('message', 'ActiveLog notification'),
            'posted_at': datetime.now().isoformat()
        }
        
    def process_generic_action(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic action"""
        return {
            'action': 'generic_action_processed',
            'payload_keys': list(payload.keys()),
            'processed_at': datetime.now().isoformat()
        }
        
    def list_flows(self) -> Dict[str, Any]:
        """List all configured flows"""
        return {
            'flows': [
                {
                    'name': flow.name,
                    'flow_id': flow.flow_id,
                    'trigger_type': flow.trigger_type,
                    'environment': flow.environment,
                    'active': flow.active,
                    'created_at': flow.created_at.isoformat()
                }
                for flow in self.flows
            ],
            'count': len(self.flows),
            'environment_id': self.environment_id
        }
        
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Power Automate"""
        try:
            if not all([self.client_id, self.client_secret, self.tenant_id]):
                return {
                    'status': 'error',
                    'error': 'Missing authentication configuration'
                }
                
            # Test authentication
            auth_result = self.authenticate()
            if auth_result['status'] != 'authenticated':
                return {
                    'status': 'error',
                    'error': 'Authentication failed',
                    'details': auth_result
                }
                
            return {
                'status': 'success',
                'message': 'Power Automate connection test successful',
                'tenant_id': self.tenant_id,
                'environment_id': self.environment_id,
                'timestamp': datetime.now().isoformat()
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
            'name': 'Microsoft Power Automate',
            'type': 'workflow_automation',
            'status': 'active' if self.enabled else 'inactive',
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'flows_count': len(self.flows),
            'environment_id': self.environment_id,
            'capabilities': [
                'workflow_automation',
                'microsoft_365_integration',
                'custom_connectors',
                'business_process_automation',
                'ai_builder_integration'
            ]
        }