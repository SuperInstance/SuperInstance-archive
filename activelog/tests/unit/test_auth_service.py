"""
Unit tests for Authentication Service
Tests user authentication, session management, and permission handling
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import bcrypt
import jwt

# Import the auth service components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../services'))

from auth.auth_utils import PasswordManager, JWTManager
from auth.auth_models import User, UserSession
from auth.auth_routes import AuthRoutes


class TestPasswordManager:
    """Test password hashing and verification"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password_manager = PasswordManager()
        password = "test_password_123"
        
        hashed = password_manager.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hash should be long
        assert hashed.startswith('$2b$')  # bcrypt identifier
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password_manager = PasswordManager()
        password = "test_password_123"
        
        hashed = password_manager.hash_password(password)
        is_valid = password_manager.verify_password(password, hashed)
        
        assert is_valid is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password_manager = PasswordManager()
        password = "test_password_123"
        wrong_password = "wrong_password_456"
        
        hashed = password_manager.hash_password(password)
        is_valid = password_manager.verify_password(wrong_password, hashed)
        
        assert is_valid is False
    
    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash"""
        password_manager = PasswordManager()
        password = "test_password_123"
        invalid_hash = "invalid_hash"
        
        is_valid = password_manager.verify_password(password, invalid_hash)
        
        assert is_valid is False
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        password_manager = PasswordManager()
        
        # Weak passwords
        assert not password_manager.validate_password_strength("123")
        assert not password_manager.validate_password_strength("password")
        assert not password_manager.validate_password_strength("PASSWORD")
        assert not password_manager.validate_password_strength("12345678")
        
        # Strong passwords
        assert password_manager.validate_password_strength("Password123!")
        assert password_manager.validate_password_strength("MyStr0ng@Pass")
        assert password_manager.validate_password_strength("T3st!ng#2024")


class TestJWTManager:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test access token creation"""
        jwt_manager = JWTManager(secret_key="test_secret")
        user_data = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com'
        }
        
        token = jwt_manager.create_access_token(user_data)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3  # JWT has 3 parts
    
    def test_create_refresh_token(self):
        """Test refresh token creation"""
        jwt_manager = JWTManager(secret_key="test_secret")
        user_data = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com'
        }
        
        token = jwt_manager.create_refresh_token(user_data)
        
        assert isinstance(token, str)
        assert len(token.split('.')) == 3
    
    def test_decode_token_valid(self):
        """Test decoding valid token"""
        jwt_manager = JWTManager(secret_key="test_secret")
        user_data = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com'
        }
        
        token = jwt_manager.create_access_token(user_data)
        decoded = jwt_manager.decode_token(token)
        
        assert decoded['user_id'] == user_data['user_id']
        assert decoded['email'] == user_data['email']
        assert 'exp' in decoded
    
    def test_decode_token_expired(self):
        """Test decoding expired token"""
        jwt_manager = JWTManager(secret_key="test_secret", access_token_expire_minutes=-1)
        user_data = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@example.com'
        }
        
        token = jwt_manager.create_access_token(user_data)
        decoded = jwt_manager.decode_token(token)
        
        assert decoded is None
    
    def test_decode_token_invalid(self):
        """Test decoding invalid token"""
        jwt_manager = JWTManager(secret_key="test_secret")
        
        decoded = jwt_manager.decode_token("invalid.token.here")
        
        assert decoded is None
    
    def test_decode_token_wrong_secret(self):
        """Test decoding token with wrong secret"""
        jwt_manager1 = JWTManager(secret_key="secret1")
        jwt_manager2 = JWTManager(secret_key="secret2")
        
        user_data = {'user_id': str(uuid.uuid4())}
        token = jwt_manager1.create_access_token(user_data)
        decoded = jwt_manager2.decode_token(token)
        
        assert decoded is None


class TestUser:
    """Test User model"""
    
    def test_user_creation(self, sample_user):
        """Test user model creation"""
        user = User(**sample_user)
        
        assert user.id == sample_user['id']
        assert user.email == sample_user['email']
        assert user.name == sample_user['name']
        assert user.is_active == sample_user['is_active']
    
    def test_user_serialization(self, sample_user):
        """Test user model serialization"""
        user = User(**sample_user)
        user_dict = user.to_dict()
        
        assert user_dict['id'] == sample_user['id']
        assert user_dict['email'] == sample_user['email']
        assert 'password_hash' not in user_dict  # Sensitive data excluded
    
    def test_user_password_validation(self):
        """Test user password validation"""
        user_data = {
            'id': str(uuid.uuid4()),
            'email': 'test@example.com',
            'name': 'Test User',
            'password_hash': 'invalid_hash'
        }
        
        user = User(**user_data)
        
        # Test with PasswordManager
        password_manager = PasswordManager()
        assert not user.verify_password("any_password", password_manager)
    
    def test_user_permissions(self, sample_user):
        """Test user permission checking"""
        user = User(**sample_user)
        
        assert user.has_permission('read')
        assert user.has_permission('write')
        assert not user.has_permission('admin')
    
    def test_user_update_last_login(self, sample_user):
        """Test updating user last login"""
        user = User(**sample_user)
        original_login = user.last_login_at
        
        user.update_last_login()
        
        assert user.last_login_at != original_login
        assert isinstance(user.last_login_at, datetime)


class TestUserSession:
    """Test UserSession model"""
    
    def test_session_creation(self, sample_user):
        """Test session creation"""
        session = UserSession(
            user_id=sample_user['id'],
            session_token='test_token_123',
            device_info={'platform': 'web', 'browser': 'chrome'}
        )
        
        assert session.user_id == sample_user['id']
        assert session.session_token == 'test_token_123'
        assert session.is_active is True
        assert isinstance(session.created_at, datetime)
    
    def test_session_expiration(self, sample_user):
        """Test session expiration checking"""
        # Create expired session
        session = UserSession(
            user_id=sample_user['id'],
            session_token='test_token_123',
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        assert session.is_expired() is True
        
        # Create valid session
        session_valid = UserSession(
            user_id=sample_user['id'],
            session_token='test_token_456',
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert session_valid.is_expired() is False
    
    def test_session_invalidation(self, sample_user):
        """Test session invalidation"""
        session = UserSession(
            user_id=sample_user['id'],
            session_token='test_token_123'
        )
        
        assert session.is_active is True
        
        session.invalidate()
        
        assert session.is_active is False
        assert isinstance(session.invalidated_at, datetime)


@pytest.mark.asyncio
class TestAuthRoutes:
    """Test authentication API routes"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.auth_routes = AuthRoutes()
        self.password_manager = PasswordManager()
        self.jwt_manager = JWTManager(secret_key="test_secret")
    
    @patch('auth.auth_routes.database')
    async def test_register_user_success(self, mock_db, sample_user):
        """Test successful user registration"""
        # Mock database operations
        mock_db.create_user.return_value = sample_user
        mock_db.get_user_by_email.return_value = None
        
        registration_data = {
            'email': 'new@example.com',
            'password': 'Password123!',
            'name': 'New User'
        }
        
        result = await self.auth_routes.register_user(registration_data)
        
        assert result['success'] is True
        assert 'user' in result
        assert result['user']['email'] == registration_data['email']
        mock_db.create_user.assert_called_once()
    
    @patch('auth.auth_routes.database')
    async def test_register_user_email_exists(self, mock_db, sample_user):
        """Test registration with existing email"""
        mock_db.get_user_by_email.return_value = sample_user
        
        registration_data = {
            'email': sample_user['email'],
            'password': 'Password123!',
            'name': 'New User'
        }
        
        result = await self.auth_routes.register_user(registration_data)
        
        assert result['success'] is False
        assert 'already exists' in result['error']
    
    @patch('auth.auth_routes.database')
    async def test_login_success(self, mock_db, sample_user):
        """Test successful login"""
        # Hash the password for comparison
        password = 'test_password_123'
        sample_user['password_hash'] = self.password_manager.hash_password(password)
        
        mock_db.get_user_by_email.return_value = sample_user
        mock_db.create_session.return_value = {
            'session_id': str(uuid.uuid4()),
            'expires_at': datetime.utcnow() + timedelta(hours=24)
        }
        
        login_data = {
            'email': sample_user['email'],
            'password': password,
            'device_info': {'platform': 'web'}
        }
        
        with patch.object(self.auth_routes, 'jwt_manager', self.jwt_manager):
            result = await self.auth_routes.login_user(login_data)
        
        assert result['success'] is True
        assert 'access_token' in result
        assert 'refresh_token' in result
        assert 'user' in result
    
    @patch('auth.auth_routes.database')
    async def test_login_invalid_credentials(self, mock_db, sample_user):
        """Test login with invalid credentials"""
        sample_user['password_hash'] = self.password_manager.hash_password('correct_password')
        mock_db.get_user_by_email.return_value = sample_user
        
        login_data = {
            'email': sample_user['email'],
            'password': 'wrong_password',
            'device_info': {'platform': 'web'}
        }
        
        result = await self.auth_routes.login_user(login_data)
        
        assert result['success'] is False
        assert 'Invalid credentials' in result['error']
    
    @patch('auth.auth_routes.database')
    async def test_login_user_not_found(self, mock_db):
        """Test login with non-existent user"""
        mock_db.get_user_by_email.return_value = None
        
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'any_password',
            'device_info': {'platform': 'web'}
        }
        
        result = await self.auth_routes.login_user(login_data)
        
        assert result['success'] is False
        assert 'Invalid credentials' in result['error']
    
    @patch('auth.auth_routes.database')
    async def test_refresh_token_success(self, mock_db, sample_user):
        """Test successful token refresh"""
        mock_session = {
            'user_id': sample_user['id'],
            'is_active': True,
            'expires_at': datetime.utcnow() + timedelta(hours=24)
        }
        
        mock_db.get_session_by_refresh_token.return_value = mock_session
        mock_db.get_user_by_id.return_value = sample_user
        
        refresh_data = {
            'refresh_token': 'valid_refresh_token'
        }
        
        with patch.object(self.auth_routes, 'jwt_manager', self.jwt_manager):
            result = await self.auth_routes.refresh_token(refresh_data)
        
        assert result['success'] is True
        assert 'access_token' in result
    
    @patch('auth.auth_routes.database')
    async def test_logout_success(self, mock_db, sample_user):
        """Test successful logout"""
        mock_db.invalidate_session.return_value = True
        
        logout_data = {
            'session_id': str(uuid.uuid4())
        }
        
        result = await self.auth_routes.logout_user(logout_data)
        
        assert result['success'] is True
        mock_db.invalidate_session.assert_called_once_with(logout_data['session_id'])
    
    @patch('auth.auth_routes.database')
    async def test_get_user_profile(self, mock_db, sample_user):
        """Test getting user profile"""
        mock_db.get_user_by_id.return_value = sample_user
        
        result = await self.auth_routes.get_user_profile(sample_user['id'])
        
        assert result['success'] is True
        assert result['user']['id'] == sample_user['id']
        assert 'password_hash' not in result['user']
    
    @patch('auth.auth_routes.database')
    async def test_update_user_profile(self, mock_db, sample_user):
        """Test updating user profile"""
        updated_user = sample_user.copy()
        updated_user['name'] = 'Updated Name'
        
        mock_db.get_user_by_id.return_value = sample_user
        mock_db.update_user.return_value = updated_user
        
        update_data = {
            'user_id': sample_user['id'],
            'name': 'Updated Name'
        }
        
        result = await self.auth_routes.update_user_profile(update_data)
        
        assert result['success'] is True
        assert result['user']['name'] == 'Updated Name'
    
    @patch('auth.auth_routes.database')
    async def test_change_password_success(self, mock_db, sample_user):
        """Test successful password change"""
        old_password = 'old_password_123'
        new_password = 'new_password_456'
        
        sample_user['password_hash'] = self.password_manager.hash_password(old_password)
        mock_db.get_user_by_id.return_value = sample_user
        mock_db.update_user.return_value = sample_user
        
        change_data = {
            'user_id': sample_user['id'],
            'old_password': old_password,
            'new_password': new_password
        }
        
        result = await self.auth_routes.change_password(change_data)
        
        assert result['success'] is True
        mock_db.update_user.assert_called_once()
    
    @patch('auth.auth_routes.database')
    async def test_change_password_invalid_old_password(self, mock_db, sample_user):
        """Test password change with invalid old password"""
        sample_user['password_hash'] = self.password_manager.hash_password('correct_old_password')
        mock_db.get_user_by_id.return_value = sample_user
        
        change_data = {
            'user_id': sample_user['id'],
            'old_password': 'wrong_old_password',
            'new_password': 'new_password_456'
        }
        
        result = await self.auth_routes.change_password(change_data)
        
        assert result['success'] is False
        assert 'Invalid current password' in result['error']


@pytest.mark.unit
class TestAuthServiceIntegration:
    """Integration tests for auth service components"""
    
    def test_complete_auth_flow(self, sample_user):
        """Test complete authentication flow"""
        password_manager = PasswordManager()
        jwt_manager = JWTManager(secret_key="test_secret")
        
        # 1. Hash password (registration)
        password = "test_password_123"
        hashed_password = password_manager.hash_password(password)
        
        # 2. Verify password (login)
        is_valid = password_manager.verify_password(password, hashed_password)
        assert is_valid
        
        # 3. Create tokens
        user_data = {
            'user_id': sample_user['id'],
            'email': sample_user['email']
        }
        access_token = jwt_manager.create_access_token(user_data)
        refresh_token = jwt_manager.create_refresh_token(user_data)
        
        # 4. Verify tokens
        decoded_access = jwt_manager.decode_token(access_token)
        decoded_refresh = jwt_manager.decode_token(refresh_token)
        
        assert decoded_access['user_id'] == sample_user['id']
        assert decoded_refresh['user_id'] == sample_user['id']
    
    def test_security_measures(self):
        """Test security measures implementation"""
        password_manager = PasswordManager()
        
        # Test password hashing is not reversible
        password = "sensitive_password_123"
        hashed = password_manager.hash_password(password)
        
        assert password not in hashed
        assert len(hashed) > 50  # Strong hash length
        
        # Test password strength requirements
        weak_passwords = ["123", "password", "12345678"]
        strong_passwords = ["StrongPass123!", "MyP@ssw0rd", "Secure#2024"]
        
        for weak in weak_passwords:
            assert not password_manager.validate_password_strength(weak)
        
        for strong in strong_passwords:
            assert password_manager.validate_password_strength(strong)