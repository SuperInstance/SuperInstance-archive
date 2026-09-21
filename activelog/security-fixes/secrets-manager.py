#!/usr/bin/env python3
"""
Critical Security Fixes - Secrets Manager
Replace all hardcoded secrets with environment variables and secure storage
"""

import os
import secrets
import base64
import json
from typing import Dict, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecureSecretsManager:
    """Secure secrets management to replace hardcoded values"""
    
    def __init__(self):
        self.secrets_cache: Dict[str, str] = {}
        self.master_key = self._get_or_generate_master_key()
        self.cipher_suite = Fernet(self.master_key)
        
    def _get_or_generate_master_key(self) -> bytes:
        """Get or generate master encryption key"""
        key_file = os.path.expanduser("~/.activelogai/master.key")
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Generate new key
        os.makedirs(os.path.dirname(key_file), exist_ok=True, mode=0o700)
        master_key = Fernet.generate_key()
        
        with open(key_file, 'wb') as f:
            f.write(master_key)
        os.chmod(key_file, 0o600)
        
        return master_key
    
    def get_secret(self, secret_name: str, default: Optional[str] = None) -> str:
        """Get secret from environment or secure storage"""
        # Try environment variable first
        env_value = os.getenv(secret_name)
        if env_value and env_value not in ['your-secret-key-here', 'change-in-production', 'your-api-key']:
            return env_value
        
        # Try secure storage
        if secret_name in self.secrets_cache:
            return self.secrets_cache[secret_name]
        
        # Generate secure default if none exists
        if default is None:
            secure_value = self._generate_secure_secret(secret_name)
            self.store_secret(secret_name, secure_value)
            return secure_value
        
        return default
    
    def store_secret(self, secret_name: str, secret_value: str):
        """Store secret securely"""
        self.secrets_cache[secret_name] = secret_value
        
        # Store encrypted in file system
        secrets_file = os.path.expanduser("~/.activelogai/secrets.enc")
        
        if os.path.exists(secrets_file):
            with open(secrets_file, 'rb') as f:
                encrypted_data = f.read()
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            secrets_dict = json.loads(decrypted_data.decode())
        else:
            secrets_dict = {}
        
        secrets_dict[secret_name] = secret_value
        
        # Encrypt and store
        encrypted_data = self.cipher_suite.encrypt(
            json.dumps(secrets_dict).encode()
        )
        
        os.makedirs(os.path.dirname(secrets_file), exist_ok=True, mode=0o700)
        with open(secrets_file, 'wb') as f:
            f.write(encrypted_data)
        os.chmod(secrets_file, 0o600)
    
    def _generate_secure_secret(self, secret_type: str) -> str:
        """Generate cryptographically secure secrets"""
        if 'jwt' in secret_type.lower() or 'token' in secret_type.lower():
            return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
        elif 'password' in secret_type.lower():
            return secrets.token_urlsafe(16)
        elif 'key' in secret_type.lower():
            return secrets.token_hex(32)
        else:
            return secrets.token_urlsafe(24)
    
    def rotate_secret(self, secret_name: str) -> str:
        """Rotate a secret to new secure value"""
        new_secret = self._generate_secure_secret(secret_name)
        self.store_secret(secret_name, new_secret)
        return new_secret
    
    def list_secrets(self) -> list:
        """List all stored secret names"""
        secrets_file = os.path.expanduser("~/.activelogai/secrets.enc")
        if not os.path.exists(secrets_file):
            return []
        
        with open(secrets_file, 'rb') as f:
            encrypted_data = f.read()
        decrypted_data = self.cipher_suite.decrypt(encrypted_data)
        secrets_dict = json.loads(decrypted_data.decode())
        
        return list(secrets_dict.keys())

# Global instance
secrets_manager = SecureSecretsManager()

# Common secret keys that need fixing
CRITICAL_SECRETS = {
    'JWT_SECRET_KEY': 'JWT secret key for authentication',
    'SERVICE_TO_SERVICE_KEY': 'Internal service authentication key',
    'MINIO_ROOT_PASSWORD': 'MinIO storage root password',
    'MINIO_ACCESS_KEY': 'MinIO storage access key',
    'GF_SECURITY_ADMIN_PASSWORD': 'Grafana admin password',
    'POSTGRES_PASSWORD': 'PostgreSQL database password',
    'REDIS_PASSWORD': 'Redis cache password',
    'API_GATEWAY_KEY': 'API Gateway authentication key',
    'ENCRYPTION_KEY': 'Data encryption key',
    'WEBHOOK_SECRET': 'Webhook verification secret'
}

def fix_hardcoded_secrets():
    """Generate secure replacements for all hardcoded secrets"""
    print("🔒 Generating secure replacements for hardcoded secrets...")
    
    for secret_name, description in CRITICAL_SECRETS.items():
        if secret_name not in secrets_manager.list_secrets():
            secure_value = secrets_manager._generate_secure_secret(secret_name)
            secrets_manager.store_secret(secret_name, secure_value)
            print(f"✅ Generated secure {secret_name}")
    
    print("\n🔑 Environment variables to set:")
    print("=====================================")
    for secret_name in CRITICAL_SECRETS.keys():
        secure_value = secrets_manager.get_secret(secret_name)
        print(f"export {secret_name}='{secure_value}'")
    
    print("\n⚠️  IMPORTANT:")
    print("1. Set these environment variables in your production system")
    print("2. Remove all hardcoded secrets from source code")
    print("3. Add secrets scanning to CI/CD pipeline")
    print("4. Rotate secrets immediately if system is already deployed")

if __name__ == "__main__":
    fix_hardcoded_secrets()