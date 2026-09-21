"""
User-related test fixtures and data generators
"""

import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from faker import Faker

fake = Faker()


class UserFixtures:
    """Generate user test data and fixtures"""
    
    @staticmethod
    def create_user(
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        is_active: bool = True,
        permissions: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a single user fixture"""
        
        user_id = user_id or str(uuid.uuid4())
        email = email or fake.email()
        name = name or fake.name()
        permissions = permissions or ['read', 'write']
        
        return {
            'id': user_id,
            'email': email,
            'name': name,
            'password_hash': fake.sha256(),
            'is_active': is_active,
            'created_at': fake.date_time_between(start_date='-1y', end_date='now'),
            'updated_at': datetime.utcnow(),
            'last_login_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'permissions': permissions,
            'profile': {
                'avatar_url': fake.image_url(),
                'bio': fake.text(max_nb_chars=200),
                'timezone': fake.timezone(),
                'language': random.choice(['en', 'es', 'fr', 'de', 'ja']),
                'theme': random.choice(['light', 'dark', 'auto'])
            },
            'settings': {
                'notifications_enabled': fake.boolean(),
                'email_notifications': fake.boolean(),
                'auto_sync': fake.boolean(),
                'sync_frequency': random.choice(['realtime', 'hourly', 'daily'])
            },
            'subscription': {
                'plan': random.choice(['free', 'pro', 'enterprise']),
                'status': random.choice(['active', 'trial', 'expired']),
                'expires_at': fake.date_time_between(start_date='now', end_date='+1y')
            },
            **kwargs
        }
    
    @staticmethod
    def create_admin_user(**kwargs) -> Dict[str, Any]:
        """Create an admin user fixture"""
        return UserFixtures.create_user(
            permissions=['read', 'write', 'admin', 'delete', 'manage_users'],
            **kwargs
        )
    
    @staticmethod
    def create_readonly_user(**kwargs) -> Dict[str, Any]:
        """Create a read-only user fixture"""
        return UserFixtures.create_user(
            permissions=['read'],
            **kwargs
        )
    
    @staticmethod
    def create_test_users(count: int = 10) -> List[Dict[str, Any]]:
        """Create multiple test users"""
        users = []
        
        # Ensure we have different types of users
        user_types = [
            {'type': 'admin', 'ratio': 0.1},
            {'type': 'readonly', 'ratio': 0.2},
            {'type': 'regular', 'ratio': 0.7}
        ]
        
        for i in range(count):
            # Determine user type based on ratio
            rand = random.random()
            if rand < 0.1:
                user = UserFixtures.create_admin_user()
            elif rand < 0.3:
                user = UserFixtures.create_readonly_user()
            else:
                user = UserFixtures.create_user()
            
            users.append(user)
        
        return users
    
    @staticmethod
    def create_user_session(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create a user session fixture"""
        return {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'session_token': fake.sha256(),
            'refresh_token': fake.sha256(),
            'created_at': fake.date_time_between(start_date='-7d', end_date='now'),
            'expires_at': fake.date_time_between(start_date='now', end_date='+1d'),
            'last_accessed_at': fake.date_time_between(start_date='-1h', end_date='now'),
            'ip_address': fake.ipv4(),
            'user_agent': fake.user_agent(),
            'device_info': {
                'platform': random.choice(['web', 'mobile', 'desktop']),
                'browser': random.choice(['chrome', 'firefox', 'safari', 'edge']),
                'os': random.choice(['windows', 'macos', 'linux', 'ios', 'android']),
                'version': fake.bothify('##.#.#')
            },
            'is_active': True,
            **kwargs
        }
    
    @staticmethod
    def create_user_activity(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create user activity log fixture"""
        actions = [
            'login', 'logout', 'file_upload', 'file_download', 'file_delete',
            'search', 'semantic_search', 'profile_update', 'settings_change',
            'share_file', 'create_folder', 'delete_folder'
        ]
        
        return {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'action': random.choice(actions),
            'resource_type': random.choice(['file', 'folder', 'user', 'system']),
            'resource_id': str(uuid.uuid4()),
            'timestamp': fake.date_time_between(start_date='-30d', end_date='now'),
            'ip_address': fake.ipv4(),
            'user_agent': fake.user_agent(),
            'metadata': {
                'duration_ms': random.randint(100, 5000),
                'success': fake.boolean(chance_of_getting_true=95),
                'error_code': None if fake.boolean(chance_of_getting_true=95) else random.randint(400, 500)
            },
            **kwargs
        }
    
    @staticmethod
    def create_user_preferences(user_id: str, **kwargs) -> Dict[str, Any]:
        """Create user preferences fixture"""
        return {
            'user_id': user_id,
            'ui_preferences': {
                'theme': random.choice(['light', 'dark', 'auto']),
                'language': random.choice(['en', 'es', 'fr', 'de', 'ja']),
                'timezone': fake.timezone(),
                'date_format': random.choice(['MM/DD/YYYY', 'DD/MM/YYYY', 'YYYY-MM-DD']),
                'time_format': random.choice(['12h', '24h']),
                'items_per_page': random.choice([10, 25, 50, 100]),
                'default_view': random.choice(['list', 'grid', 'table'])
            },
            'sync_preferences': {
                'auto_sync': fake.boolean(),
                'sync_frequency': random.choice(['realtime', 'hourly', 'daily']),
                'sync_on_mobile': fake.boolean(),
                'sync_large_files': fake.boolean(),
                'conflict_resolution': random.choice(['ask', 'local', 'remote', 'merge'])
            },
            'privacy_preferences': {
                'profile_visibility': random.choice(['public', 'private', 'friends']),
                'search_indexing': fake.boolean(),
                'analytics_tracking': fake.boolean(),
                'marketing_emails': fake.boolean(),
                'activity_sharing': fake.boolean()
            },
            'ai_preferences': {
                'enable_semantic_search': fake.boolean(),
                'enable_auto_tagging': fake.boolean(),
                'enable_smart_suggestions': fake.boolean(),
                'ai_model_preference': random.choice(['fast', 'accurate', 'balanced']),
                'content_analysis': fake.boolean()
            },
            **kwargs
        }
    
    @staticmethod
    def create_organization(owner_id: str, **kwargs) -> Dict[str, Any]:
        """Create organization fixture"""
        return {
            'id': str(uuid.uuid4()),
            'name': fake.company(),
            'slug': fake.slug(),
            'description': fake.text(max_nb_chars=500),
            'owner_id': owner_id,
            'created_at': fake.date_time_between(start_date='-2y', end_date='-30d'),
            'updated_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'settings': {
                'max_users': random.randint(10, 1000),
                'max_storage_gb': random.randint(100, 10000),
                'features_enabled': {
                    'ai_features': fake.boolean(),
                    'advanced_analytics': fake.boolean(),
                    'api_access': fake.boolean(),
                    'custom_integrations': fake.boolean()
                },
                'security_settings': {
                    'require_2fa': fake.boolean(),
                    'password_policy': random.choice(['basic', 'strong', 'enterprise']),
                    'session_timeout_hours': random.randint(1, 24),
                    'ip_whitelist_enabled': fake.boolean()
                }
            },
            'billing': {
                'plan': random.choice(['starter', 'business', 'enterprise']),
                'status': random.choice(['active', 'trial', 'suspended', 'cancelled']),
                'next_billing_date': fake.date_time_between(start_date='now', end_date='+1y')
            },
            **kwargs
        }
    
    @staticmethod
    def create_team(organization_id: str, **kwargs) -> Dict[str, Any]:
        """Create team fixture"""
        return {
            'id': str(uuid.uuid4()),
            'organization_id': organization_id,
            'name': fake.bs().title(),
            'description': fake.text(max_nb_chars=200),
            'created_at': fake.date_time_between(start_date='-1y', end_date='-7d'),
            'updated_at': fake.date_time_between(start_date='-7d', end_date='now'),
            'settings': {
                'visibility': random.choice(['public', 'private', 'organization']),
                'join_policy': random.choice(['open', 'invite', 'request']),
                'permissions': {
                    'can_create_files': fake.boolean(),
                    'can_delete_files': fake.boolean(),
                    'can_share_externally': fake.boolean(),
                    'can_manage_tags': fake.boolean()
                }
            },
            **kwargs
        }
    
    @staticmethod
    def create_user_invitation(invited_by_id: str, **kwargs) -> Dict[str, Any]:
        """Create user invitation fixture"""
        return {
            'id': str(uuid.uuid4()),
            'email': fake.email(),
            'invited_by_id': invited_by_id,
            'organization_id': kwargs.get('organization_id'),
            'team_id': kwargs.get('team_id'),
            'role': random.choice(['member', 'admin', 'viewer']),
            'permissions': random.sample(['read', 'write', 'delete', 'share'], 2),
            'token': fake.sha256(),
            'status': random.choice(['pending', 'accepted', 'expired', 'cancelled']),
            'created_at': fake.date_time_between(start_date='-30d', end_date='now'),
            'expires_at': fake.date_time_between(start_date='now', end_date='+7d'),
            'accepted_at': fake.date_time_between(start_date='-7d', end_date='now') if fake.boolean() else None,
            'message': fake.text(max_nb_chars=100) if fake.boolean() else None,
            **kwargs
        }


class UserFactory:
    """Factory class for creating multiple related user objects"""
    
    def __init__(self):
        self.users = []
        self.organizations = []
        self.teams = []
        
    def create_organization_with_users(
        self, 
        user_count: int = 10,
        team_count: int = 2
    ) -> Dict[str, Any]:
        """Create a complete organization with users and teams"""
        
        # Create owner
        owner = UserFixtures.create_admin_user()
        self.users.append(owner)
        
        # Create organization
        org = UserFixtures.create_organization(owner['id'])
        self.organizations.append(org)
        
        # Create teams
        teams = []
        for _ in range(team_count):
            team = UserFixtures.create_team(org['id'])
            teams.append(team)
            self.teams.append(team)
        
        # Create users
        users = []
        for _ in range(user_count - 1):  # -1 because we already have owner
            user = UserFixtures.create_user()
            users.append(user)
            self.users.append(user)
        
        return {
            'organization': org,
            'owner': owner,
            'users': users,
            'teams': teams,
            'all_users': [owner] + users
        }
    
    def create_user_with_history(self, activity_count: int = 50) -> Dict[str, Any]:
        """Create user with complete activity history"""
        
        user = UserFixtures.create_user()
        
        # Create sessions
        sessions = []
        for _ in range(random.randint(5, 15)):
            session = UserFixtures.create_user_session(user['id'])
            sessions.append(session)
        
        # Create activity logs
        activities = []
        for _ in range(activity_count):
            activity = UserFixtures.create_user_activity(user['id'])
            activities.append(activity)
        
        # Create preferences
        preferences = UserFixtures.create_user_preferences(user['id'])
        
        return {
            'user': user,
            'sessions': sessions,
            'activities': activities,
            'preferences': preferences
        }