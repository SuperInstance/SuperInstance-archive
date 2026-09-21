"""
Customer Account Management
Handles customer registration, profiles, authentication, and account management
"""

import json
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import re


class CustomerStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class AccountType(Enum):
    INDIVIDUAL = "individual"
    BUSINESS = "business"
    WHOLESALE = "wholesale"


@dataclass
class CustomerAddress:
    address_id: str
    address_type: str  # 'shipping', 'billing', 'both'
    first_name: str
    last_name: str
    company: Optional[str]
    address1: str
    address2: Optional[str]
    city: str
    state: str
    zip: str
    country: str
    phone: Optional[str]
    is_default: bool = False


class CustomerAccountManager:
    """Manages customer accounts and authentication"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Authentication settings
        self.jwt_secret = config.get('jwt_secret', 'your-secret-key')
        self.token_expiry_hours = config.get('token_expiry_hours', 24)
        self.require_email_verification = config.get('require_email_verification', True)
        
        # Password requirements
        self.min_password_length = config.get('min_password_length', 8)
        self.require_password_complexity = config.get('require_password_complexity', True)
        
        # Account features
        self.allow_guest_checkout = config.get('allow_guest_checkout', True)
        self.automatic_account_creation = config.get('automatic_account_creation', True)
        self.customer_groups_enabled = config.get('customer_groups_enabled', True)
        
        # Privacy settings
        self.gdpr_compliance = config.get('gdpr_compliance', True)
        self.data_retention_days = config.get('data_retention_days', 2555)  # 7 years
        
    def create_customer_account(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new customer account"""
        try:
            # Validate input data
            validation_result = self.validate_customer_data(account_data)
            if not validation_result['valid']:
                raise ValueError(validation_result['error'])
                
            # Check if email already exists
            existing_customer = self.db.get_customer_by_email(account_data['email'])
            if existing_customer:
                raise ValueError("An account with this email already exists")
                
            # Generate customer ID
            customer_id = f"cust_{datetime.now().timestamp()}"
            
            # Hash password
            password_hash = self.hash_password(account_data['password'])
            
            # Create customer record
            customer = {
                'customer_id': customer_id,
                'email': account_data['email'].lower(),
                'first_name': account_data['first_name'],
                'last_name': account_data['last_name'],
                'phone': account_data.get('phone'),
                'date_of_birth': account_data.get('date_of_birth'),
                'gender': account_data.get('gender'),
                'password_hash': password_hash,
                'account_type': account_data.get('account_type', AccountType.INDIVIDUAL.value),
                'status': CustomerStatus.PENDING_VERIFICATION.value if self.require_email_verification else CustomerStatus.ACTIVE.value,
                'email_verified': not self.require_email_verification,
                'email_verification_token': secrets.token_urlsafe(32) if self.require_email_verification else None,
                'accepts_marketing': account_data.get('accepts_marketing', False),
                'tax_exempt': account_data.get('tax_exempt', False),
                'customer_group': account_data.get('customer_group', 'default'),
                'notes': account_data.get('notes', ''),
                'tags': account_data.get('tags', []),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'last_login': None,
                'login_count': 0
            }
            
            # Save customer
            success = self.db.save_customer(customer)
            if not success:
                raise Exception("Failed to create customer account")
                
            # Create default address if provided
            if account_data.get('default_address'):
                self.add_customer_address(customer_id, account_data['default_address'])
                
            # Send verification email if required
            if self.require_email_verification:
                self.send_email_verification(customer_id)
                
            # Create customer profile
            self.create_customer_profile(customer_id, account_data)
            
            # Log account creation
            self.log_customer_event(customer_id, 'account_created', {
                'email': customer['email'],
                'account_type': customer['account_type']
            })
            
            return {
                'success': True,
                'customer_id': customer_id,
                'email': customer['email'],
                'status': customer['status'],
                'verification_required': self.require_email_verification,
                'message': 'Account created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating customer account: {e}")
            
    def authenticate_customer(self, auth_data: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate customer login"""
        try:
            email = auth_data['email'].lower()
            password = auth_data['password']
            
            # Get customer by email
            customer = self.db.get_customer_by_email(email)
            if not customer:
                raise ValueError("Invalid email or password")
                
            # Verify password
            if not self.verify_password(password, customer['password_hash']):
                # Log failed login attempt
                self.log_customer_event(customer['customer_id'], 'login_failed', {
                    'email': email,
                    'ip_address': auth_data.get('ip_address'),
                    'user_agent': auth_data.get('user_agent')
                })
                raise ValueError("Invalid email or password")
                
            # Check account status
            if customer['status'] == CustomerStatus.SUSPENDED.value:
                raise ValueError("Account is suspended")
            elif customer['status'] == CustomerStatus.INACTIVE.value:
                raise ValueError("Account is inactive")
            elif customer['status'] == CustomerStatus.PENDING_VERIFICATION.value:
                raise ValueError("Please verify your email address before logging in")
                
            # Generate JWT token
            token_payload = {
                'customer_id': customer['customer_id'],
                'email': customer['email'],
                'account_type': customer['account_type'],
                'exp': datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
                'iat': datetime.utcnow()
            }
            
            access_token = jwt.encode(token_payload, self.jwt_secret, algorithm='HS256')
            
            # Update login stats
            login_updates = {
                'last_login': datetime.now().isoformat(),
                'login_count': customer.get('login_count', 0) + 1,
                'updated_at': datetime.now().isoformat()
            }
            
            self.db.update_customer(customer['customer_id'], login_updates)
            
            # Log successful login
            self.log_customer_event(customer['customer_id'], 'login_successful', {
                'ip_address': auth_data.get('ip_address'),
                'user_agent': auth_data.get('user_agent')
            })
            
            return {
                'success': True,
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': self.token_expiry_hours * 3600,
                'customer': self.sanitize_customer_data(customer)
            }
            
        except Exception as e:
            raise Exception(f"Authentication failed: {e}")
            
    def get_customer_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get customer profile"""
        try:
            customer = self.db.get_customer(customer_id)
            if not customer:
                return None
                
            # Get additional profile data
            profile = self.db.get_customer_profile(customer_id)
            addresses = self.db.get_customer_addresses(customer_id)
            order_stats = self.db.get_customer_order_stats(customer_id)
            
            # Combine all data
            customer_profile = {
                **self.sanitize_customer_data(customer),
                'profile': profile or {},
                'addresses': addresses or [],
                'order_statistics': order_stats or {
                    'total_orders': 0,
                    'total_spent': 0.0,
                    'average_order_value': 0.0,
                    'last_order_date': None
                }
            }
            
            return customer_profile
            
        except Exception as e:
            raise Exception(f"Error getting customer profile: {e}")
            
    def update_customer_profile(self, customer_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer profile"""
        try:
            customer = self.db.get_customer(customer_id)
            if not customer:
                raise ValueError("Customer not found")
                
            # Separate profile updates from account updates
            account_updates = {}
            profile_updates = update_data.get('profile', {})
            
            # Handle account-level updates
            allowed_account_fields = [
                'first_name', 'last_name', 'phone', 'date_of_birth', 'gender',
                'accepts_marketing', 'notes', 'tags'
            ]
            
            for field in allowed_account_fields:
                if field in update_data:
                    account_updates[field] = update_data[field]
                    
            # Handle email change (requires verification)
            if 'email' in update_data and update_data['email'] != customer['email']:
                new_email = update_data['email'].lower()
                
                # Check if email is already in use
                existing = self.db.get_customer_by_email(new_email)
                if existing and existing['customer_id'] != customer_id:
                    raise ValueError("Email address is already in use")
                    
                account_updates['email'] = new_email
                
                if self.require_email_verification:
                    account_updates['email_verified'] = False
                    account_updates['email_verification_token'] = secrets.token_urlsafe(32)
                    # Send verification email for new address
                    self.send_email_verification(customer_id, new_email)
                    
            # Handle password change
            if 'password' in update_data:
                if 'current_password' not in update_data:
                    raise ValueError("Current password is required to change password")
                    
                if not self.verify_password(update_data['current_password'], customer['password_hash']):
                    raise ValueError("Current password is incorrect")
                    
                # Validate new password
                password_validation = self.validate_password(update_data['password'])
                if not password_validation['valid']:
                    raise ValueError(password_validation['error'])
                    
                account_updates['password_hash'] = self.hash_password(update_data['password'])
                
                # Log password change
                self.log_customer_event(customer_id, 'password_changed', {})
                
            # Update timestamps
            if account_updates:
                account_updates['updated_at'] = datetime.now().isoformat()
                success = self.db.update_customer(customer_id, account_updates)
                if not success:
                    raise Exception("Failed to update customer account")
                    
            # Update profile data
            if profile_updates:
                profile_updates['updated_at'] = datetime.now().isoformat()
                success = self.db.update_customer_profile(customer_id, profile_updates)
                if not success:
                    raise Exception("Failed to update customer profile")
                    
            return {
                'success': True,
                'customer_id': customer_id,
                'message': 'Profile updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating customer profile: {e}")
            
    def add_customer_address(self, customer_id: str, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add address to customer account"""
        try:
            # Validate address data
            required_fields = ['first_name', 'last_name', 'address1', 'city', 'state', 'zip', 'country']
            for field in required_fields:
                if field not in address_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Generate address ID
            address_id = f"addr_{datetime.now().timestamp()}"
            
            # Create address record
            address = {
                'address_id': address_id,
                'customer_id': customer_id,
                'address_type': address_data.get('address_type', 'both'),
                'first_name': address_data['first_name'],
                'last_name': address_data['last_name'],
                'company': address_data.get('company'),
                'address1': address_data['address1'],
                'address2': address_data.get('address2'),
                'city': address_data['city'],
                'state': address_data['state'],
                'zip': address_data['zip'],
                'country': address_data['country'],
                'phone': address_data.get('phone'),
                'is_default': address_data.get('is_default', False),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # If this is the default address, unset other defaults
            if address['is_default']:
                self.db.unset_default_addresses(customer_id)
                
            # Save address
            success = self.db.save_customer_address(address)
            if not success:
                raise Exception("Failed to save customer address")
                
            return {
                'success': True,
                'address_id': address_id,
                'message': 'Address added successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error adding customer address: {e}")
            
    def update_customer_address(self, customer_id: str, address_id: str, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update customer address"""
        try:
            # Verify address belongs to customer
            address = self.db.get_customer_address(customer_id, address_id)
            if not address:
                raise ValueError("Address not found")
                
            # Update address data
            address_updates = {**address_data}
            address_updates['updated_at'] = datetime.now().isoformat()
            
            # Handle default address change
            if address_data.get('is_default') and not address['is_default']:
                self.db.unset_default_addresses(customer_id)
                
            success = self.db.update_customer_address(address_id, address_updates)
            if not success:
                raise Exception("Failed to update address")
                
            return {
                'success': True,
                'address_id': address_id,
                'message': 'Address updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error updating customer address: {e}")
            
    def delete_customer_address(self, customer_id: str, address_id: str) -> Dict[str, Any]:
        """Delete customer address"""
        try:
            # Verify address belongs to customer
            address = self.db.get_customer_address(customer_id, address_id)
            if not address:
                raise ValueError("Address not found")
                
            # Delete address
            success = self.db.delete_customer_address(address_id)
            if not success:
                raise Exception("Failed to delete address")
                
            return {
                'success': True,
                'address_id': address_id,
                'message': 'Address deleted successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error deleting customer address: {e}")
            
    def verify_email(self, verification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify customer email address"""
        try:
            token = verification_data['verification_token']
            
            # Find customer by verification token
            customer = self.db.get_customer_by_verification_token(token)
            if not customer:
                raise ValueError("Invalid or expired verification token")
                
            # Update customer status
            updates = {
                'email_verified': True,
                'email_verification_token': None,
                'status': CustomerStatus.ACTIVE.value,
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.update_customer(customer['customer_id'], updates)
            if not success:
                raise Exception("Failed to verify email")
                
            # Log verification
            self.log_customer_event(customer['customer_id'], 'email_verified', {
                'email': customer['email']
            })
            
            return {
                'success': True,
                'customer_id': customer['customer_id'],
                'message': 'Email verified successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error verifying email: {e}")
            
    def reset_password_request(self, reset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Request password reset"""
        try:
            email = reset_data['email'].lower()
            
            customer = self.db.get_customer_by_email(email)
            if not customer:
                # Don't reveal if email exists or not
                return {
                    'success': True,
                    'message': 'If the email exists, a reset link has been sent'
                }
                
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            reset_expires = datetime.now() + timedelta(hours=1)  # 1 hour expiry
            
            # Save reset token
            updates = {
                'password_reset_token': reset_token,
                'password_reset_expires': reset_expires.isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.update_customer(customer['customer_id'], updates)
            if success:
                # Send reset email
                self.send_password_reset_email(customer['customer_id'], reset_token)
                
                # Log password reset request
                self.log_customer_event(customer['customer_id'], 'password_reset_requested', {
                    'email': customer['email']
                })
                
            return {
                'success': True,
                'message': 'If the email exists, a reset link has been sent'
            }
            
        except Exception as e:
            raise Exception(f"Error requesting password reset: {e}")
            
    def reset_password(self, reset_data: Dict[str, Any]) -> Dict[str, Any]:
        """Reset customer password"""
        try:
            token = reset_data['reset_token']
            new_password = reset_data['new_password']
            
            # Find customer by reset token
            customer = self.db.get_customer_by_reset_token(token)
            if not customer:
                raise ValueError("Invalid or expired reset token")
                
            # Check token expiry
            if customer.get('password_reset_expires'):
                expires = datetime.fromisoformat(customer['password_reset_expires'])
                if datetime.now() > expires:
                    raise ValueError("Reset token has expired")
                    
            # Validate new password
            password_validation = self.validate_password(new_password)
            if not password_validation['valid']:
                raise ValueError(password_validation['error'])
                
            # Update password and clear reset token
            updates = {
                'password_hash': self.hash_password(new_password),
                'password_reset_token': None,
                'password_reset_expires': None,
                'updated_at': datetime.now().isoformat()
            }
            
            success = self.db.update_customer(customer['customer_id'], updates)
            if not success:
                raise Exception("Failed to reset password")
                
            # Log password reset
            self.log_customer_event(customer['customer_id'], 'password_reset_completed', {
                'email': customer['email']
            })
            
            return {
                'success': True,
                'customer_id': customer['customer_id'],
                'message': 'Password reset successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error resetting password: {e}")
            
    def deactivate_customer_account(self, customer_id: str, deactivation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deactivate customer account"""
        try:
            customer = self.db.get_customer(customer_id)
            if not customer:
                raise ValueError("Customer not found")
                
            reason = deactivation_data.get('reason', 'Customer request')
            retain_data = deactivation_data.get('retain_data', True)
            
            updates = {
                'status': CustomerStatus.INACTIVE.value,
                'deactivated_at': datetime.now().isoformat(),
                'deactivation_reason': reason,
                'updated_at': datetime.now().isoformat()
            }
            
            # If not retaining data, anonymize personal information
            if not retain_data and self.gdpr_compliance:
                updates.update({
                    'first_name': 'Deleted',
                    'last_name': 'User',
                    'email': f'deleted_{customer_id}@example.com',
                    'phone': None,
                    'date_of_birth': None
                })
                
            success = self.db.update_customer(customer_id, updates)
            if not success:
                raise Exception("Failed to deactivate account")
                
            # Log deactivation
            self.log_customer_event(customer_id, 'account_deactivated', {
                'reason': reason,
                'data_retained': retain_data
            })
            
            return {
                'success': True,
                'customer_id': customer_id,
                'message': 'Account deactivated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error deactivating customer account: {e}")
            
    def validate_customer_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate customer registration data"""
        try:
            # Required fields
            required_fields = ['email', 'first_name', 'last_name', 'password']
            for field in required_fields:
                if field not in data or not data[field]:
                    return {'valid': False, 'error': f'Missing required field: {field}'}
                    
            # Validate email format
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, data['email']):
                return {'valid': False, 'error': 'Invalid email format'}
                
            # Validate password
            password_validation = self.validate_password(data['password'])
            if not password_validation['valid']:
                return password_validation
                
            return {'valid': True}
            
        except Exception as e:
            return {'valid': False, 'error': f'Validation error: {e}'}
            
    def validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        try:
            if len(password) < self.min_password_length:
                return {
                    'valid': False,
                    'error': f'Password must be at least {self.min_password_length} characters long'
                }
                
            if self.require_password_complexity:
                has_upper = any(c.isupper() for c in password)
                has_lower = any(c.islower() for c in password)
                has_digit = any(c.isdigit() for c in password)
                has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
                
                if not (has_upper and has_lower and has_digit and has_special):
                    return {
                        'valid': False,
                        'error': 'Password must contain uppercase, lowercase, number, and special character'
                    }
                    
            return {'valid': True}
            
        except Exception:
            return {'valid': False, 'error': 'Password validation failed'}
            
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt-like method"""
        try:
            # In production, use bcrypt or similar
            salt = secrets.token_hex(16)
            password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return f"{salt}${password_hash.hex()}"
        except Exception:
            raise Exception("Password hashing failed")
            
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_part = password_hash.split('$', 1)
            computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return computed_hash.hex() == hash_part
        except Exception:
            return False
            
    def sanitize_customer_data(self, customer: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from customer object"""
        try:
            sensitive_fields = [
                'password_hash', 'email_verification_token', 
                'password_reset_token', 'password_reset_expires'
            ]
            
            sanitized = customer.copy()
            for field in sensitive_fields:
                sanitized.pop(field, None)
                
            return sanitized
            
        except Exception:
            return customer
            
    def create_customer_profile(self, customer_id: str, profile_data: Dict[str, Any]) -> bool:
        """Create extended customer profile"""
        try:
            profile = {
                'customer_id': customer_id,
                'preferences': profile_data.get('preferences', {}),
                'communication_preferences': {
                    'email_marketing': profile_data.get('accepts_marketing', False),
                    'sms_marketing': profile_data.get('accepts_sms', False),
                    'push_notifications': profile_data.get('accepts_push', True)
                },
                'interests': profile_data.get('interests', []),
                'custom_fields': profile_data.get('custom_fields', {}),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            return self.db.save_customer_profile(profile)
            
        except Exception:
            return False
            
    def log_customer_event(self, customer_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log customer account events"""
        try:
            event = {
                'customer_id': customer_id,
                'event_type': event_type,
                'event_data': json.dumps(event_data),
                'created_at': datetime.now().isoformat(),
                'ip_address': event_data.get('ip_address'),
                'user_agent': event_data.get('user_agent')
            }
            
            self.db.save_customer_event(event)
            
        except Exception as e:
            print(f"Error logging customer event: {e}")
            
    def send_email_verification(self, customer_id: str, email: Optional[str] = None):
        """Send email verification"""
        try:
            customer = self.db.get_customer(customer_id)
            if customer and customer.get('email_verification_token'):
                # This would integrate with email service
                print(f"Verification email sent to {email or customer['email']}")
        except Exception as e:
            print(f"Error sending verification email: {e}")
            
    def send_password_reset_email(self, customer_id: str, reset_token: str):
        """Send password reset email"""
        try:
            customer = self.db.get_customer(customer_id)
            if customer:
                # This would integrate with email service
                print(f"Password reset email sent to {customer['email']}")
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
            
    def get_customer_orders(self, customer_id: str, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """Get customer order history"""
        try:
            orders = self.db.get_customer_orders(customer_id, page, limit)
            total_count = self.db.get_customer_order_count(customer_id)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'orders': orders,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting customer orders: {e}")
            
    def get_customer_analytics(self, customer_id: str) -> Dict[str, Any]:
        """Get customer analytics and insights"""
        try:
            analytics = self.db.get_customer_analytics(customer_id)
            
            return {
                'customer_id': customer_id,
                'total_orders': analytics.get('total_orders', 0),
                'total_spent': analytics.get('total_spent', 0.0),
                'average_order_value': analytics.get('average_order_value', 0.0),
                'first_order_date': analytics.get('first_order_date'),
                'last_order_date': analytics.get('last_order_date'),
                'favorite_categories': analytics.get('favorite_categories', []),
                'customer_lifetime_value': analytics.get('customer_lifetime_value', 0.0),
                'loyalty_tier': analytics.get('loyalty_tier', 'bronze'),
                'referrals_made': analytics.get('referrals_made', 0)
            }
            
        except Exception as e:
            raise Exception(f"Error getting customer analytics: {e}")