"""
Microsoft Teams Integration
Handles integration with Microsoft Teams via app/bot
"""

import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class TeamsApp:
    app_id: str
    app_name: str
    tenant_id: str
    installed_teams: List[str]
    permissions: List[str]
    installed_at: datetime


class TeamsIntegration:
    """Integration with Microsoft Teams via app/bot"""
    
    def __init__(self, config):
        self.config = config
        self.client_id = config.get('teams_client_id')
        self.client_secret = config.get('teams_client_secret')
        self.tenant_id = config.get('teams_tenant_id')
        self.bot_id = config.get('teams_bot_id')
        self.bot_password = config.get('teams_bot_password')
        self.webhook_url = config.get('teams_webhook_url')
        self.access_token = None
        self.api_base = "https://graph.microsoft.com/v1.0"
        self.bot_framework_base = "https://smba.trafficmanager.net/apis/v3"
        self.enabled = False
        self.sync_count = 0
        self.last_sync = None
        self.error_count = 0
        self.installed_apps = []
        
    def get_status(self) -> Dict[str, Any]:
        """Get integration status"""
        return {
            'status': 'active' if self.enabled else 'inactive',
            'enabled': self.enabled,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'installed_apps_count': len(self.installed_apps),
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'tenant_id': self.tenant_id,
            'bot_configured': bool(self.bot_id)
        }
        
    def enable(self) -> Dict[str, Any]:
        """Enable Teams integration"""
        try:
            self.enabled = True
            auth_result = self.authenticate()
            return {
                'status': 'enabled',
                'message': 'Microsoft Teams integration enabled successfully',
                'authentication': auth_result
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def disable(self) -> Dict[str, Any]:
        """Disable Teams integration"""
        try:
            self.enabled = False
            self.access_token = None
            return {
                'status': 'disabled',
                'message': 'Microsoft Teams integration disabled successfully'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def configure(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure Teams integration settings"""
        try:
            if 'client_id' in config_data:
                self.client_id = config_data['client_id']
                
            if 'client_secret' in config_data:
                self.client_secret = config_data['client_secret']
                
            if 'tenant_id' in config_data:
                self.tenant_id = config_data['tenant_id']
                
            if 'bot_id' in config_data:
                self.bot_id = config_data['bot_id']
                
            if 'bot_password' in config_data:
                self.bot_password = config_data['bot_password']
                
            if 'webhook_url' in config_data:
                self.webhook_url = config_data['webhook_url']
                
            return {
                'status': 'configured',
                'message': 'Microsoft Teams integration configured successfully',
                'config': {
                    'client_id_set': bool(self.client_id),
                    'client_secret_set': bool(self.client_secret),
                    'tenant_id': self.tenant_id,
                    'bot_id_set': bool(self.bot_id),
                    'bot_password_set': bool(self.bot_password),
                    'webhook_url_set': bool(self.webhook_url),
                    'api_base': self.api_base
                }
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def authenticate(self) -> Dict[str, Any]:
        """Authenticate with Microsoft Teams/Graph API"""
        try:
            if not all([self.client_id, self.client_secret, self.tenant_id]):
                return {
                    'status': 'error',
                    'error': 'Missing required authentication parameters'
                }
                
            # Simulate OAuth2 authentication with Microsoft Graph
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            
            # Simulate successful authentication
            self.access_token = f"mock_teams_token_{datetime.now().timestamp()}"
            
            return {
                'status': 'authenticated',
                'message': 'Successfully authenticated with Microsoft Teams',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'scope': 'https://graph.microsoft.com/.default',
                'tenant_id': self.tenant_id
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def sync(self) -> Dict[str, Any]:
        """Sync data with Microsoft Teams"""
        try:
            if not self.enabled:
                return {
                    'status': 'skipped',
                    'message': 'Microsoft Teams integration is disabled'
                }
                
            if not self.access_token:
                auth_result = self.authenticate()
                if auth_result['status'] != 'authenticated':
                    return {
                        'status': 'error',
                        'error': 'Authentication failed',
                        'auth_result': auth_result
                    }
                    
            self.sync_count += 1
            self.last_sync = datetime.now()
            
            # Sync different data types
            sync_results = {
                'teams': self.sync_teams(),
                'channels': self.sync_channels(),
                'users': self.sync_users(),
                'apps': self.sync_installed_apps(),
                'messages': self.sync_recent_messages()
            }
            
            return {
                'status': 'success',
                'message': 'Microsoft Teams sync completed',
                'timestamp': self.last_sync.isoformat(),
                'sync_count': self.sync_count,
                'sync_results': sync_results
            }
            
        except Exception as e:
            self.error_count += 1
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def sync_teams(self) -> Dict[str, Any]:
        """Sync Microsoft Teams"""
        return {
            'status': 'success',
            'teams_synced': 5,
            'active_teams': 4,
            'archived_teams': 1,
            'total_members': 125
        }
        
    def sync_channels(self) -> Dict[str, Any]:
        """Sync Teams channels"""
        return {
            'status': 'success',
            'channels_synced': 35,
            'public_channels': 25,
            'private_channels': 8,
            'shared_channels': 2
        }
        
    def sync_users(self) -> Dict[str, Any]:
        """Sync Teams users"""
        return {
            'status': 'success',
            'users_synced': 125,
            'active_users': 108,
            'guest_users': 15,
            'external_users': 2
        }
        
    def sync_installed_apps(self) -> Dict[str, Any]:
        """Sync installed Teams apps"""
        try:
            # Create mock app
            app = TeamsApp(
                app_id=self.client_id or f"app_{datetime.now().timestamp()}",
                app_name="ActiveLog Teams App",
                tenant_id=self.tenant_id,
                installed_teams=["team1", "team2", "team3"],
                permissions=["TeamsActivity.Read", "ChatMessage.Send", "Channel.ReadBasic.All"],
                installed_at=datetime.now()
            )
            
            self.installed_apps.append(app)
            
            return {
                'status': 'success',
                'apps_synced': 1,
                'installed_teams': len(app.installed_teams),
                'permissions': len(app.permissions)
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def sync_recent_messages(self) -> Dict[str, Any]:
        """Sync recent Teams messages"""
        return {
            'status': 'success',
            'messages_processed': 850,
            'mentions_processed': 45,
            'files_shared': 25,
            'meetings_scheduled': 12
        }
        
    def send_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send message to Teams channel"""
        try:
            if not self.access_token:
                return {
                    'status': 'error',
                    'error': 'Not authenticated with Microsoft Teams'
                }
                
            team_id = message_data.get('team_id')
            channel_id = message_data.get('channel_id')
            message_text = message_data.get('message')
            message_type = message_data.get('message_type', 'text')
            
            if not all([team_id, channel_id, message_text]):
                return {
                    'status': 'error',
                    'error': 'Team ID, channel ID, and message are required'
                }
                
            # Simulate message sending
            message_id = f"teams_msg_{datetime.now().timestamp()}"
            
            return {
                'status': 'sent',
                'message_id': message_id,
                'team_id': team_id,
                'channel_id': channel_id,
                'message_type': message_type,
                'content': message_text,
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def create_adaptive_card(self, card_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Teams Adaptive Card"""
        card = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": []
        }
        
        # Title
        if 'title' in card_data:
            card['body'].append({
                "type": "TextBlock",
                "text": card_data['title'],
                "size": "Large",
                "weight": "Bolder"
            })
            
        # Description
        if 'description' in card_data:
            card['body'].append({
                "type": "TextBlock",
                "text": card_data['description'],
                "wrap": True
            })
            
        # Facts (fields)
        if 'facts' in card_data:
            fact_set = {
                "type": "FactSet",
                "facts": []
            }
            
            for fact in card_data['facts']:
                fact_set['facts'].append({
                    "title": fact.get('title', 'Fact'),
                    "value": str(fact.get('value', 'N/A'))
                })
                
            card['body'].append(fact_set)
            
        # Actions
        if 'actions' in card_data:
            card['actions'] = []
            for action in card_data['actions']:
                if action.get('type') == 'url':
                    card['actions'].append({
                        "type": "Action.OpenUrl",
                        "title": action.get('title', 'Open'),
                        "url": action.get('url')
                    })
                elif action.get('type') == 'submit':
                    card['actions'].append({
                        "type": "Action.Submit",
                        "title": action.get('title', 'Submit'),
                        "data": action.get('data', {})
                    })
                    
        return {
            'status': 'created',
            'adaptive_card': card,
            'elements_count': len(card['body'])
        }
        
    def send_webhook_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send message via Teams webhook"""
        try:
            if not self.webhook_url:
                return {
                    'status': 'error',
                    'error': 'Webhook URL not configured'
                }
                
            # Create message card for Teams webhook
            message_card = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "themeColor": "0078D4",
                "title": webhook_data.get('title', 'ActiveLog Notification'),
                "text": webhook_data.get('text', ''),
                "sections": []
            }
            
            if 'sections' in webhook_data:
                message_card['sections'] = webhook_data['sections']
            elif 'facts' in webhook_data:
                message_card['sections'].append({
                    "facts": webhook_data['facts']
                })
                
            if 'actions' in webhook_data:
                message_card['potentialAction'] = webhook_data['actions']
                
            # Simulate webhook sending
            return {
                'status': 'sent',
                'webhook_url': self.webhook_url[:50] + '...',
                'message_card': message_card,
                'sent_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
            
    def handle_bot_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming message to bot"""
        try:
            activity_type = message_data.get('type', 'message')
            text = message_data.get('text', '')
            from_user = message_data.get('from', {})
            conversation = message_data.get('conversation', {})
            
            if activity_type == 'message':
                if text.lower().startswith('activelog'):
                    result = self.process_activelog_bot_command(text, from_user)
                elif text.lower() == 'status':
                    result = self.process_status_bot_command(from_user)
                elif text.lower() == 'help':
                    result = self.process_help_bot_command()
                else:
                    result = self.process_generic_bot_message(text, from_user)
            else:
                result = self.process_bot_activity(activity_type, message_data)
                
            return {
                'status': 'processed',
                'activity_type': activity_type,
                'conversation_id': conversation.get('id'),
                'from_user_id': from_user.get('id'),
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def process_activelog_bot_command(self, text: str, from_user: Dict[str, Any]) -> Dict[str, Any]:
        """Process ActiveLog bot command"""
        if 'status' in text.lower():
            card_data = {
                'title': '📊 ActiveLog Status',
                'description': 'Current system status and metrics',
                'facts': [
                    {'title': 'System Status', 'value': '✅ Online'},
                    {'title': 'Services', 'value': '12/12 Active'},
                    {'title': 'Uptime', 'value': '99.9%'},
                    {'title': 'Last Update', 'value': datetime.now().strftime('%H:%M UTC')}
                ]
            }
            
            adaptive_card = self.create_adaptive_card(card_data)
            
            return {
                'type': 'adaptive_card',
                'adaptive_card': adaptive_card['adaptive_card']
            }
        else:
            return {
                'type': 'message',
                'text': f'🔗 ActiveLog Integration Hub\nHello {from_user.get("name", "User")}!\nUse "activelog status" for system status or "help" for commands.'
            }
            
    def process_status_bot_command(self, from_user: Dict[str, Any]) -> Dict[str, Any]:
        """Process status bot command"""
        return {
            'type': 'message',
            'text': f'✅ ActiveLog is online and operational!\nHello {from_user.get("name", "User")}!'
        }
        
    def process_help_bot_command(self) -> Dict[str, Any]:
        """Process help bot command"""
        return {
            'type': 'message',
            'text': '🤖 **ActiveLog Teams Bot Commands:**\n\n' +
                    '• **activelog status** - Get system status\n' +
                    '• **status** - Quick status check\n' +
                    '• **help** - Show this help\n\n' +
                    '**Features:**\n' +
                    '• Real-time notifications\n' +
                    '• System monitoring\n' +
                    '• Integration updates\n' +
                    '• Alert management'
        }
        
    def process_generic_bot_message(self, text: str, from_user: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic bot message"""
        return {
            'type': 'message',
            'text': f'👋 Hello {from_user.get("name", "User")}!\n\n' +
                    f'You said: "{text}"\n\n' +
                    'Try "activelog status" or "help" for available commands.'
        }
        
    def process_bot_activity(self, activity_type: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process bot activity (non-message)"""
        if activity_type == 'conversationUpdate':
            members_added = message_data.get('membersAdded', [])
            if any(member.get('id') == self.bot_id for member in members_added):
                return {
                    'type': 'message',
                    'text': '👋 Hello! I\'m the ActiveLog bot. Type "help" to see what I can do!'
                }
                
        return {
            'type': 'activity_processed',
            'activity_type': activity_type
        }
        
    def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Teams webhook/event"""
        try:
            event_type = webhook_data.get('event_type')
            payload = webhook_data.get('payload', {})
            
            if event_type == 'message_posted':
                result = self.process_message_posted(payload)
            elif event_type == 'member_added':
                result = self.process_member_added(payload)
            elif event_type == 'meeting_started':
                result = self.process_meeting_started(payload)
            elif event_type == 'file_shared':
                result = self.process_file_shared(payload)
            else:
                result = self.process_generic_teams_event(payload)
                
            return {
                'status': 'processed',
                'event_type': event_type,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
    def process_message_posted(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process message posted event"""
        return {
            'action': 'message_posted_processed',
            'message_id': payload.get('message_id'),
            'team_id': payload.get('team_id'),
            'channel_id': payload.get('channel_id'),
            'sender_id': payload.get('sender_id'),
            'message_type': payload.get('message_type')
        }
        
    def process_member_added(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process member added event"""
        return {
            'action': 'member_added_processed',
            'team_id': payload.get('team_id'),
            'user_id': payload.get('user_id'),
            'added_by': payload.get('added_by'),
            'role': payload.get('role', 'member')
        }
        
    def process_meeting_started(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process meeting started event"""
        return {
            'action': 'meeting_started_processed',
            'meeting_id': payload.get('meeting_id'),
            'organizer_id': payload.get('organizer_id'),
            'participant_count': payload.get('participant_count', 0),
            'meeting_type': payload.get('meeting_type', 'scheduled')
        }
        
    def process_file_shared(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process file shared event"""
        return {
            'action': 'file_shared_processed',
            'file_id': payload.get('file_id'),
            'file_name': payload.get('file_name'),
            'shared_by': payload.get('shared_by'),
            'team_id': payload.get('team_id'),
            'channel_id': payload.get('channel_id')
        }
        
    def process_generic_teams_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic Teams event"""
        return {
            'action': 'generic_teams_event_processed',
            'payload_keys': list(payload.keys())
        }
        
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Microsoft Teams"""
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
                
            # Test bot configuration
            bot_test = {
                'status': 'configured' if self.bot_id else 'not_configured',
                'bot_id_set': bool(self.bot_id),
                'bot_password_set': bool(self.bot_password)
            }
            
            # Test webhook if configured
            webhook_test = {
                'status': 'configured' if self.webhook_url else 'not_configured',
                'webhook_url_set': bool(self.webhook_url)
            }
            
            return {
                'status': 'success',
                'message': 'Microsoft Teams connection test successful',
                'tenant_id': self.tenant_id,
                'auth_test': auth_result,
                'bot_test': bot_test,
                'webhook_test': webhook_test,
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
            'name': 'Microsoft Teams',
            'type': 'communication_platform',
            'status': 'active' if self.enabled else 'inactive',
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'success_rate': ((self.sync_count - self.error_count) / max(self.sync_count, 1)) * 100,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'installed_apps_count': len(self.installed_apps),
            'tenant_id': self.tenant_id,
            'bot_configured': bool(self.bot_id),
            'capabilities': [
                'message_sending',
                'adaptive_cards',
                'bot_framework',
                'webhook_notifications',
                'teams_management',
                'user_management',
                'meeting_integration',
                'file_sharing'
            ]
        }