import asyncio
import logging
import hashlib
import secrets
import os
from typing import Dict, Any, Optional, Union, List
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import base64
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class EncryptedData:
    ciphertext: bytes
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            metadata=data["metadata"]
        )

class SymmetricEncryption:
    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self.fernet = Fernet(self.key)
    
    def encrypt(self, data: Union[str, bytes]) -> EncryptedData:
        """Encrypt data using Fernet (AES 128 in CBC mode)"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        ciphertext = self.fernet.encrypt(data)
        
        return EncryptedData(
            ciphertext=ciphertext,
            metadata={
                "algorithm": "fernet",
                "encrypted_at": datetime.now().isoformat()
            }
        )
    
    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt data"""
        return self.fernet.decrypt(encrypted_data.ciphertext)
    
    def decrypt_to_string(self, encrypted_data: EncryptedData) -> str:
        """Decrypt data and return as string"""
        return self.decrypt(encrypted_data).decode('utf-8')

class AESEncryption:
    def __init__(self):
        pass
    
    def generate_key(self) -> bytes:
        """Generate a 256-bit AES key"""
        return secrets.token_bytes(32)
    
    def encrypt(self, data: Union[str, bytes], key: bytes) -> EncryptedData:
        """Encrypt data using AES-256-GCM"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Generate random IV
        iv = secrets.token_bytes(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        # Combine IV + tag + ciphertext
        encrypted_data = iv + encryptor.tag + ciphertext
        
        return EncryptedData(
            ciphertext=encrypted_data,
            metadata={
                "algorithm": "aes-256-gcm",
                "key_length": len(key) * 8,
                "encrypted_at": datetime.now().isoformat()
            }
        )
    
    def decrypt(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt AES-256-GCM encrypted data"""
        data = encrypted_data.ciphertext
        
        # Extract IV, tag, and ciphertext
        iv = data[:16]
        tag = data[16:32]
        ciphertext = data[32:]
        
        # Create cipher
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        
        # Decrypt data
        return decryptor.update(ciphertext) + decryptor.finalize()

class AsymmetricEncryption:
    def __init__(self):
        self.key_size = 2048
    
    def generate_key_pair(self) -> tuple[bytes, bytes]:
        """Generate RSA key pair (private_key, public_key)"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size
        )
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    def encrypt(self, data: Union[str, bytes], public_key_pem: bytes) -> EncryptedData:
        """Encrypt data using RSA public key"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Load public key
        public_key = serialization.load_pem_public_key(public_key_pem)
        
        # Encrypt data
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptedData(
            ciphertext=ciphertext,
            metadata={
                "algorithm": "rsa-oaep-sha256",
                "key_size": self.key_size,
                "encrypted_at": datetime.now().isoformat()
            }
        )
    
    def decrypt(self, encrypted_data: EncryptedData, private_key_pem: bytes) -> bytes:
        """Decrypt data using RSA private key"""
        # Load private key
        private_key = serialization.load_pem_private_key(
            private_key_pem,
            password=None
        )
        
        # Decrypt data
        return private_key.decrypt(
            encrypted_data.ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

class KeyDerivation:
    def __init__(self):
        pass
    
    def derive_key_pbkdf2(self, password: str, salt: bytes = None, 
                         iterations: int = 100000, key_length: int = 32) -> tuple[bytes, bytes]:
        """Derive key using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=iterations
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def derive_key_scrypt(self, password: str, salt: bytes = None,
                         n: int = 2**14, r: int = 8, p: int = 1, 
                         key_length: int = 32) -> tuple[bytes, bytes]:
        """Derive key using Scrypt"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        kdf = Scrypt(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            n=n,
            r=r,
            p=p
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt

class SecretManager:
    def __init__(self, master_key: bytes = None):
        if master_key:
            self.symmetric_encryption = SymmetricEncryption(master_key)
        else:
            self.symmetric_encryption = SymmetricEncryption()
        
        self.secrets_store = {}
        self.access_log = []
    
    def store_secret(self, secret_id: str, secret_value: str, 
                    metadata: Dict[str, Any] = None) -> bool:
        """Store encrypted secret"""
        try:
            encrypted_data = self.symmetric_encryption.encrypt(secret_value)
            
            self.secrets_store[secret_id] = {
                "encrypted_data": encrypted_data,
                "metadata": metadata or {},
                "created_at": datetime.now(),
                "accessed_count": 0,
                "last_accessed": None
            }
            
            logger.info(f"Secret stored: {secret_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store secret {secret_id}: {e}")
            return False
    
    def get_secret(self, secret_id: str, requester: str = None) -> Optional[str]:
        """Retrieve and decrypt secret"""
        if secret_id not in self.secrets_store:
            return None
        
        try:
            secret_entry = self.secrets_store[secret_id]
            encrypted_data = secret_entry["encrypted_data"]
            
            # Decrypt secret
            secret_value = self.symmetric_encryption.decrypt_to_string(encrypted_data)
            
            # Update access tracking
            secret_entry["accessed_count"] += 1
            secret_entry["last_accessed"] = datetime.now()
            
            # Log access
            self.access_log.append({
                "secret_id": secret_id,
                "requester": requester,
                "accessed_at": datetime.now(),
                "success": True
            })
            
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_id}: {e}")
            
            # Log failed access
            self.access_log.append({
                "secret_id": secret_id,
                "requester": requester,
                "accessed_at": datetime.now(),
                "success": False,
                "error": str(e)
            })
            
            return None
    
    def delete_secret(self, secret_id: str) -> bool:
        """Delete secret"""
        if secret_id in self.secrets_store:
            del self.secrets_store[secret_id]
            logger.info(f"Secret deleted: {secret_id}")
            return True
        return False
    
    def list_secrets(self) -> Dict[str, Dict[str, Any]]:
        """List all secrets (without values)"""
        return {
            secret_id: {
                "metadata": entry["metadata"],
                "created_at": entry["created_at"].isoformat(),
                "accessed_count": entry["accessed_count"],
                "last_accessed": entry["last_accessed"].isoformat() if entry["last_accessed"] else None
            }
            for secret_id, entry in self.secrets_store.items()
        }
    
    def get_access_log(self, secret_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get secret access log"""
        log_entries = self.access_log[-limit:]
        
        if secret_id:
            log_entries = [entry for entry in log_entries if entry["secret_id"] == secret_id]
        
        return [
            {
                **entry,
                "accessed_at": entry["accessed_at"].isoformat()
            }
            for entry in log_entries
        ]

class DataEncryptionService:
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        
        # Initialize encryption methods
        self.symmetric = SymmetricEncryption()
        self.aes = AESEncryption()
        self.asymmetric = AsymmetricEncryption()
        self.key_derivation = KeyDerivation()
        
        # Master keys for different purposes
        self.master_keys = {}
        self._initialize_master_keys()
        
        # Secret manager
        self.secret_manager = SecretManager(self.master_keys.get("secrets"))
        
        # Key rotation settings
        self.key_rotation_interval_days = config.get("key_rotation_days", 90)
        self.key_versions = {}
        
        # Encryption preferences
        self.default_algorithm = config.get("default_algorithm", "aes-256-gcm")
        self.compression_threshold = config.get("compression_threshold", 1024)  # bytes
    
    def _initialize_master_keys(self):
        """Initialize master keys for different purposes"""
        key_purposes = ["secrets", "data", "cache", "logs", "config"]
        
        for purpose in key_purposes:
            self.master_keys[purpose] = self.aes.generate_key()
            self.key_versions[purpose] = {
                "current": 1,
                "keys": {1: {"key": self.master_keys[purpose], "created_at": datetime.now()}}
            }
    
    def encrypt_data(self, data: Union[str, bytes, Dict], purpose: str = "data",
                    algorithm: str = None) -> EncryptedData:
        """Encrypt data with specified purpose and algorithm"""
        algorithm = algorithm or self.default_algorithm
        
        # Serialize complex data
        if isinstance(data, dict):
            data = json.dumps(data)
        elif not isinstance(data, (str, bytes)):
            data = str(data)
        
        # Compress if beneficial
        original_size = len(data.encode('utf-8') if isinstance(data, str) else data)
        if original_size > self.compression_threshold:
            import gzip
            if isinstance(data, str):
                data = data.encode('utf-8')
            compressed = gzip.compress(data)
            
            if len(compressed) < original_size * 0.8:  # Only use if 20%+ compression
                data = compressed
                compression_used = True
            else:
                compression_used = False
        else:
            compression_used = False
        
        # Get appropriate key
        if purpose in self.master_keys:
            key = self.master_keys[purpose]
        else:
            key = self.master_keys["data"]
        
        # Encrypt based on algorithm
        if algorithm == "fernet":
            encrypted = self.symmetric.encrypt(data)
        elif algorithm == "aes-256-gcm":
            encrypted = self.aes.encrypt(data, key)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Add metadata
        encrypted.metadata.update({
            "purpose": purpose,
            "compression_used": compression_used,
            "original_size": original_size,
            "key_version": self.key_versions[purpose]["current"]
        })
        
        return encrypted
    
    def decrypt_data(self, encrypted_data: EncryptedData, purpose: str = "data") -> Union[str, bytes, Dict]:
        """Decrypt data"""
        algorithm = encrypted_data.metadata.get("algorithm", self.default_algorithm)
        key_version = encrypted_data.metadata.get("key_version", 1)
        
        # Get appropriate key
        if purpose in self.key_versions and key_version in self.key_versions[purpose]["keys"]:
            key = self.key_versions[purpose]["keys"][key_version]["key"]
        else:
            key = self.master_keys.get(purpose, self.master_keys["data"])
        
        # Decrypt based on algorithm
        if algorithm == "fernet":
            decrypted = self.symmetric.decrypt(encrypted_data)
        elif algorithm == "aes-256-gcm":
            decrypted = self.aes.decrypt(encrypted_data, key)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Decompress if needed
        if encrypted_data.metadata.get("compression_used", False):
            import gzip
            decrypted = gzip.decompress(decrypted)
        
        # Try to deserialize JSON
        try:
            if isinstance(decrypted, bytes):
                decrypted = decrypted.decode('utf-8')
            return json.loads(decrypted)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return decrypted
    
    def rotate_key(self, purpose: str) -> bool:
        """Rotate encryption key for a specific purpose"""
        try:
            if purpose not in self.key_versions:
                return False
            
            # Generate new key
            new_key = self.aes.generate_key()
            new_version = self.key_versions[purpose]["current"] + 1
            
            # Store new key
            self.key_versions[purpose]["keys"][new_version] = {
                "key": new_key,
                "created_at": datetime.now()
            }
            
            # Update current version
            self.key_versions[purpose]["current"] = new_version
            self.master_keys[purpose] = new_key
            
            # Clean up old keys (keep last 3 versions)
            versions_to_keep = sorted(self.key_versions[purpose]["keys"].keys())[-3:]
            for version in list(self.key_versions[purpose]["keys"].keys()):
                if version not in versions_to_keep:
                    del self.key_versions[purpose]["keys"][version]
            
            logger.info(f"Key rotated for purpose: {purpose}, new version: {new_version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate key for {purpose}: {e}")
            return False
    
    def schedule_key_rotation(self):
        """Check and perform scheduled key rotations"""
        for purpose, version_info in self.key_versions.items():
            current_key_info = version_info["keys"][version_info["current"]]
            key_age_days = (datetime.now() - current_key_info["created_at"]).days
            
            if key_age_days >= self.key_rotation_interval_days:
                logger.info(f"Performing scheduled key rotation for {purpose}")
                self.rotate_key(purpose)
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption service statistics"""
        return {
            "key_purposes": list(self.master_keys.keys()),
            "key_versions": {
                purpose: {
                    "current_version": info["current"],
                    "total_versions": len(info["keys"]),
                    "oldest_key_age_days": (
                        datetime.now() - min(
                            key_info["created_at"] for key_info in info["keys"].values()
                        )
                    ).days
                }
                for purpose, info in self.key_versions.items()
            },
            "secrets_count": len(self.secret_manager.secrets_store),
            "default_algorithm": self.default_algorithm,
            "key_rotation_interval_days": self.key_rotation_interval_days
        }
    
    # Convenience methods for common operations
    def encrypt_sensitive_data(self, data: Any) -> EncryptedData:
        """Encrypt sensitive data with highest security"""
        return self.encrypt_data(data, purpose="secrets", algorithm="aes-256-gcm")
    
    def encrypt_cache_data(self, data: Any) -> EncryptedData:
        """Encrypt cache data with performance optimization"""
        return self.encrypt_data(data, purpose="cache", algorithm="fernet")
    
    def encrypt_log_data(self, data: Any) -> EncryptedData:
        """Encrypt log data"""
        return self.encrypt_data(data, purpose="logs", algorithm="aes-256-gcm")
    
    def store_api_key(self, key_id: str, api_key: str) -> bool:
        """Store API key securely"""
        return self.secret_manager.store_secret(
            f"api_key:{key_id}",
            api_key,
            {"type": "api_key", "key_id": key_id}
        )
    
    def get_api_key(self, key_id: str, requester: str = None) -> Optional[str]:
        """Retrieve API key securely"""
        return self.secret_manager.get_secret(f"api_key:{key_id}", requester)
    
    def store_database_credential(self, db_name: str, credential: str) -> bool:
        """Store database credential securely"""
        return self.secret_manager.store_secret(
            f"db_cred:{db_name}",
            credential,
            {"type": "database_credential", "database": db_name}
        )
    
    def get_database_credential(self, db_name: str, requester: str = None) -> Optional[str]:
        """Retrieve database credential securely"""
        return self.secret_manager.get_secret(f"db_cred:{db_name}", requester)