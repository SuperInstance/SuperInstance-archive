"""
Encryption Manager for HIPAA-compliant data protection
Implements AES-256 encryption for PHI data at rest and in transit
"""

import asyncio
import logging
import hashlib
import base64
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone
from enum import Enum

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import os

from ..core.config import settings

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")

class EncryptionLevel(str, Enum):
    """Encryption levels based on PHI sensitivity"""
    STANDARD = "standard"      # AES-256 for general PHI
    HIGH = "high"             # AES-256 + additional protections for sensitive PHI
    MAXIMUM = "maximum"       # AES-256 + RSA for direct identifiers

class EncryptionManager:
    def __init__(self):
        self.master_key = None
        self.field_keys = {}  # Field-specific encryption keys
        self.rsa_private_key = None
        self.rsa_public_key = None
        
    async def initialize(self):
        """Initialize encryption manager with keys"""
        logger.info("Initializing encryption manager")
        
        try:
            # Initialize master key
            await self._initialize_master_key()
            
            # Initialize RSA keys for maximum encryption
            await self._initialize_rsa_keys()
            
            # Initialize field-specific keys
            await self._initialize_field_keys()
            
            logger.info("Encryption manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption manager: {e}")
            raise
            
    async def cleanup(self):
        """Cleanup sensitive data from memory"""
        logger.info("Cleaning up encryption manager")
        
        # Clear sensitive data
        self.master_key = None
        self.field_keys.clear()
        self.rsa_private_key = None
        self.rsa_public_key = None
        
    async def _initialize_master_key(self):
        """Initialize or load master encryption key"""
        try:
            # In production, this should be loaded from a secure key management service
            master_key_material = settings.ENCRYPTION_KEY.encode()
            
            # Derive key using PBKDF2
            salt = b"activelog_healthcare_salt_2024"  # In production, use random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            derived_key = kdf.derive(master_key_material)
            self.master_key = base64.urlsafe_b64encode(derived_key)
            
        except Exception as e:
            logger.error(f"Failed to initialize master key: {e}")
            raise
            
    async def _initialize_rsa_keys(self):
        """Initialize RSA key pair for maximum security encryption"""
        try:
            # Generate RSA key pair (in production, load from secure storage)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            self.rsa_private_key = private_key
            self.rsa_public_key = private_key.public_key()
            
        except Exception as e:
            logger.error(f"Failed to initialize RSA keys: {e}")
            raise
            
    async def _initialize_field_keys(self):
        """Initialize field-specific encryption keys"""
        try:
            # Generate field-specific keys for additional security
            sensitive_fields = [
                "ssn", "medical_record_number", "full_name", "address",
                "phone_number", "email", "credit_card", "bank_account"
            ]
            
            for field in sensitive_fields:
                field_salt = hashlib.sha256(f"field_{field}".encode()).digest()[:16]
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=field_salt,
                    iterations=100000,
                    backend=default_backend()
                )
                
                field_key = kdf.derive(self.master_key)
                self.field_keys[field] = base64.urlsafe_b64encode(field_key)
                
        except Exception as e:
            logger.error(f"Failed to initialize field keys: {e}")
            raise
            
    async def encrypt_field(self, value: Any, classification: str, 
                          field_name: Optional[str] = None) -> str:
        """Encrypt a single field value based on classification"""
        try:
            if value is None:
                return None
                
            # Convert value to string for encryption
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, sort_keys=True)
            else:
                value_str = str(value)
                
            # Determine encryption level
            encryption_level = self._get_encryption_level(classification)
            
            # Encrypt based on level
            if encryption_level == EncryptionLevel.MAXIMUM:
                encrypted_value = await self._encrypt_maximum_security(value_str)
            elif encryption_level == EncryptionLevel.HIGH:
                encrypted_value = await self._encrypt_high_security(value_str, field_name)
            else:
                encrypted_value = await self._encrypt_standard(value_str)
                
            # Add metadata
            encrypted_data = {
                "value": encrypted_value,
                "level": encryption_level.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }
            
            return base64.b64encode(json.dumps(encrypted_data).encode()).decode()
            
        except Exception as e:
            logger.error(f"Failed to encrypt field: {e}")
            raise
            
    async def decrypt_field(self, encrypted_value: str, classification: str,
                          field_name: Optional[str] = None) -> Any:
        """Decrypt a single field value"""
        try:
            if not encrypted_value:
                return None
                
            # Decode metadata
            try:
                encrypted_data = json.loads(base64.b64decode(encrypted_value.encode()).decode())
            except:
                # Handle legacy format without metadata
                encrypted_data = {"value": encrypted_value, "level": "standard"}
                
            encryption_level = EncryptionLevel(encrypted_data["level"])
            encrypted_content = encrypted_data["value"]
            
            # Decrypt based on level
            if encryption_level == EncryptionLevel.MAXIMUM:
                decrypted_value = await self._decrypt_maximum_security(encrypted_content)
            elif encryption_level == EncryptionLevel.HIGH:
                decrypted_value = await self._decrypt_high_security(encrypted_content, field_name)
            else:
                decrypted_value = await self._decrypt_standard(encrypted_content)
                
            # Try to parse as JSON if it looks like structured data
            try:
                if decrypted_value.startswith(('[', '{')):
                    return json.loads(decrypted_value)
            except:
                pass
                
            return decrypted_value
            
        except Exception as e:
            logger.error(f"Failed to decrypt field: {e}")
            raise
            
    def _get_encryption_level(self, classification: str) -> EncryptionLevel:
        """Determine encryption level based on PHI classification"""
        if classification == "direct_identifier":
            return EncryptionLevel.MAXIMUM
        elif classification == "sensitive_phi":
            return EncryptionLevel.HIGH
        else:
            return EncryptionLevel.STANDARD
            
    async def _encrypt_standard(self, value: str) -> str:
        """Standard AES-256 encryption for general PHI"""
        try:
            fernet = Fernet(self.master_key)
            encrypted = fernet.encrypt(value.encode())
            return base64.b64encode(encrypted).decode()
            
        except Exception as e:
            logger.error(f"Failed standard encryption: {e}")
            raise
            
    async def _decrypt_standard(self, encrypted_value: str) -> str:
        """Standard AES-256 decryption for general PHI"""
        try:
            fernet = Fernet(self.master_key)
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Failed standard decryption: {e}")
            raise
            
    async def _encrypt_high_security(self, value: str, field_name: Optional[str] = None) -> str:
        """High security encryption with field-specific keys"""
        try:
            # Use field-specific key if available
            key = self.field_keys.get(field_name, self.master_key)
            
            fernet = Fernet(key)
            encrypted = fernet.encrypt(value.encode())
            
            # Add additional layer of encryption with master key
            master_fernet = Fernet(self.master_key)
            double_encrypted = master_fernet.encrypt(encrypted)
            
            return base64.b64encode(double_encrypted).decode()
            
        except Exception as e:
            logger.error(f"Failed high security encryption: {e}")
            raise
            
    async def _decrypt_high_security(self, encrypted_value: str, field_name: Optional[str] = None) -> str:
        """High security decryption with field-specific keys"""
        try:
            # First layer decryption with master key
            master_fernet = Fernet(self.master_key)
            double_encrypted_bytes = base64.b64decode(encrypted_value.encode())
            single_encrypted = master_fernet.decrypt(double_encrypted_bytes)
            
            # Second layer decryption with field-specific key
            key = self.field_keys.get(field_name, self.master_key)
            fernet = Fernet(key)
            decrypted = fernet.decrypt(single_encrypted)
            
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Failed high security decryption: {e}")
            raise
            
    async def _encrypt_maximum_security(self, value: str) -> str:
        """Maximum security encryption with RSA + AES hybrid"""
        try:
            # Generate random AES key for this specific value
            aes_key = os.urandom(32)
            
            # Encrypt data with AES
            iv = os.urandom(16)
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Pad data to AES block size
            padded_data = self._pad_data(value.encode())
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Encrypt AES key with RSA
            encrypted_key = self.rsa_public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Combine encrypted key, IV, and encrypted data
            combined = {
                "key": base64.b64encode(encrypted_key).decode(),
                "iv": base64.b64encode(iv).decode(),
                "data": base64.b64encode(encrypted_data).decode()
            }
            
            return base64.b64encode(json.dumps(combined).encode()).decode()
            
        except Exception as e:
            logger.error(f"Failed maximum security encryption: {e}")
            raise
            
    async def _decrypt_maximum_security(self, encrypted_value: str) -> str:
        """Maximum security decryption with RSA + AES hybrid"""
        try:
            # Parse combined data
            combined = json.loads(base64.b64decode(encrypted_value.encode()).decode())
            
            encrypted_key = base64.b64decode(combined["key"].encode())
            iv = base64.b64decode(combined["iv"].encode())
            encrypted_data = base64.b64decode(combined["data"].encode())
            
            # Decrypt AES key with RSA
            aes_key = self.rsa_private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt data with AES
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Remove padding
            decrypted_data = self._unpad_data(decrypted_padded)
            
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Failed maximum security decryption: {e}")
            raise
            
    def _pad_data(self, data: bytes) -> bytes:
        """PKCS7 padding for AES encryption"""
        padding_length = 16 - (len(data) % 16)
        padding = bytes([padding_length]) * padding_length
        return data + padding
        
    def _unpad_data(self, padded_data: bytes) -> bytes:
        """Remove PKCS7 padding after AES decryption"""
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
        
    async def encrypt_file(self, file_path: str, output_path: str) -> Dict[str, Any]:
        """Encrypt entire file for secure storage"""
        try:
            with open(file_path, 'rb') as infile:
                file_data = infile.read()
                
            # Generate file-specific encryption key
            file_key = os.urandom(32)
            iv = os.urandom(16)
            
            # Encrypt file data
            cipher = Cipher(algorithms.AES(file_key), modes.CBC(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            
            # Pad file data
            padded_data = self._pad_data(file_data)
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Encrypt file key with RSA
            encrypted_key = self.rsa_public_key.encrypt(
                file_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Create encrypted file structure
            encrypted_file = {
                "version": "1.0",
                "key": base64.b64encode(encrypted_key).decode(),
                "iv": base64.b64encode(iv).decode(),
                "data": base64.b64encode(encrypted_data).decode(),
                "original_size": len(file_data),
                "encrypted_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Write encrypted file
            with open(output_path, 'w') as outfile:
                json.dump(encrypted_file, outfile)
                
            return {
                "original_file": file_path,
                "encrypted_file": output_path,
                "original_size": len(file_data),
                "encrypted_size": len(json.dumps(encrypted_file)),
                "encryption_time": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to encrypt file {file_path}: {e}")
            raise
            
    async def decrypt_file(self, encrypted_file_path: str, output_path: str) -> Dict[str, Any]:
        """Decrypt entire file from secure storage"""
        try:
            # Read encrypted file
            with open(encrypted_file_path, 'r') as infile:
                encrypted_file = json.load(infile)
                
            encrypted_key = base64.b64decode(encrypted_file["key"].encode())
            iv = base64.b64decode(encrypted_file["iv"].encode())
            encrypted_data = base64.b64decode(encrypted_file["data"].encode())
            
            # Decrypt file key with RSA
            file_key = self.rsa_private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt file data
            cipher = Cipher(algorithms.AES(file_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Remove padding
            file_data = self._unpad_data(decrypted_padded)
            
            # Write decrypted file
            with open(output_path, 'wb') as outfile:
                outfile.write(file_data)
                
            return {
                "encrypted_file": encrypted_file_path,
                "decrypted_file": output_path,
                "file_size": len(file_data),
                "original_size": encrypted_file.get("original_size"),
                "decryption_time": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to decrypt file {encrypted_file_path}: {e}")
            raise
            
    async def generate_data_hash(self, data: Union[str, bytes]) -> str:
        """Generate SHA-256 hash for data integrity verification"""
        try:
            if isinstance(data, str):
                data = data.encode()
                
            hash_obj = hashlib.sha256(data)
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to generate data hash: {e}")
            raise
            
    async def verify_data_integrity(self, data: Union[str, bytes], expected_hash: str) -> bool:
        """Verify data integrity using hash comparison"""
        try:
            actual_hash = await self.generate_data_hash(data)
            return actual_hash == expected_hash
            
        except Exception as e:
            logger.error(f"Failed to verify data integrity: {e}")
            return False