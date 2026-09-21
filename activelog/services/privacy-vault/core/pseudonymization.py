import asyncio
import logging
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from enum import Enum
from dataclasses import dataclass
import uuid
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import re

logger = logging.getLogger(__name__)

class PseudonymizationMethod(Enum):
    HASH_BASED = "hash_based"
    ENCRYPTION_BASED = "encryption_based"
    TOKEN_BASED = "token_based"
    KEY_DERIVATION = "key_derivation"
    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non_deterministic"
    FORMAT_PRESERVING = "format_preserving"
    SYNTHETIC_DATA = "synthetic_data"

class HashAlgorithm(Enum):
    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    ARGON2 = "argon2"

class PseudonymScope(Enum):
    SINGLE_DATASET = "single_dataset"
    CROSS_DATASET = "cross_dataset"
    TEMPORAL_LIMITED = "temporal_limited"
    PURPOSE_LIMITED = "purpose_limited"
    GLOBAL = "global"

class ReversibilityLevel(Enum):
    IRREVERSIBLE = "irreversible"
    REVERSIBLE_WITH_KEY = "reversible_with_key"
    REVERSIBLE_WITH_MAPPING = "reversible_with_mapping"
    CONDITIONAL_REVERSIBLE = "conditional_reversible"

@dataclass
class PseudonymizationPolicy:
    policy_id: str
    policy_name: str
    applicable_data_types: List[str]
    method: PseudonymizationMethod
    hash_algorithm: Optional[HashAlgorithm]
    reversibility: ReversibilityLevel
    scope: PseudonymScope
    key_rotation_period: int  # days
    salt_strategy: str
    purpose_limitation: List[str]
    retention_period: Optional[int]  # days
    created_date: datetime
    created_by: str
    approved_by: Optional[str]
    version: str

@dataclass
class PseudonymizationKey:
    key_id: str
    key_value: bytes
    algorithm: str
    purpose: str
    created_date: datetime
    expiry_date: Optional[datetime]
    rotation_count: int
    status: str  # active, expired, revoked
    scope: PseudonymScope
    associated_policies: List[str]

@dataclass
class PseudonymRecord:
    record_id: str
    original_identifier: str
    pseudonym: str
    method_used: PseudonymizationMethod
    policy_id: str
    key_id: Optional[str]
    salt: Optional[str]
    created_date: datetime
    expiry_date: Optional[datetime]
    dataset_context: str
    purpose: List[str]
    reversible: bool
    access_log: List[str]

@dataclass
class SyntheticDataProfile:
    profile_id: str
    data_type: str
    statistical_properties: Dict[str, Any]
    distribution_parameters: Dict[str, Any]
    correlation_matrix: Optional[List[List[float]]]
    privacy_budget: float
    noise_parameters: Dict[str, float]
    generated_samples: int
    validation_metrics: Dict[str, float]

class PseudonymizationManager:
    def __init__(self):
        self.policies: Dict[str, PseudonymizationPolicy] = {}
        self.keys: Dict[str, PseudonymizationKey] = {}
        self.pseudonym_records: Dict[str, PseudonymRecord] = {}
        self.reverse_mapping: Dict[str, str] = {}  # pseudonym -> original
        self.synthetic_profiles: Dict[str, SyntheticDataProfile] = {}
        self.format_preserving_mappings: Dict[str, Dict[str, str]] = {}
        logger.info("Pseudonymization Manager initialized")

    async def initialize(self):
        await self._create_default_policies()
        await self._initialize_key_management()
        logger.info("Pseudonymization Manager initialization completed")

    async def _create_default_policies(self):
        policies = [
            PseudonymizationPolicy(
                policy_id="email_hash",
                policy_name="Email Address Hashing",
                applicable_data_types=["email"],
                method=PseudonymizationMethod.HASH_BASED,
                hash_algorithm=HashAlgorithm.SHA256,
                reversibility=ReversibilityLevel.IRREVERSIBLE,
                scope=PseudonymScope.SINGLE_DATASET,
                key_rotation_period=90,
                salt_strategy="per_dataset",
                purpose_limitation=["analytics", "research"],
                retention_period=365,
                created_date=datetime.now(),
                created_by="system",
                approved_by="admin",
                version="1.0"
            ),
            PseudonymizationPolicy(
                policy_id="user_id_encrypt",
                policy_name="User ID Encryption",
                applicable_data_types=["user_id", "customer_id"],
                method=PseudonymizationMethod.ENCRYPTION_BASED,
                hash_algorithm=None,
                reversibility=ReversibilityLevel.REVERSIBLE_WITH_KEY,
                scope=PseudonymScope.CROSS_DATASET,
                key_rotation_period=180,
                salt_strategy="per_record",
                purpose_limitation=["processing", "analytics"],
                retention_period=None,
                created_date=datetime.now(),
                created_by="system",
                approved_by="admin",
                version="1.0"
            ),
            PseudonymizationPolicy(
                policy_id="phone_format_preserve",
                policy_name="Phone Number Format Preserving",
                applicable_data_types=["phone_number"],
                method=PseudonymizationMethod.FORMAT_PRESERVING,
                hash_algorithm=None,
                reversibility=ReversibilityLevel.REVERSIBLE_WITH_MAPPING,
                scope=PseudonymScope.PURPOSE_LIMITED,
                key_rotation_period=365,
                salt_strategy="global",
                purpose_limitation=["testing", "development"],
                retention_period=180,
                created_date=datetime.now(),
                created_by="system",
                approved_by="admin",
                version="1.0"
            ),
            PseudonymizationPolicy(
                policy_id="synthetic_demographics",
                policy_name="Synthetic Demographics Generation",
                applicable_data_types=["age", "gender", "location"],
                method=PseudonymizationMethod.SYNTHETIC_DATA,
                hash_algorithm=None,
                reversibility=ReversibilityLevel.IRREVERSIBLE,
                scope=PseudonymScope.SINGLE_DATASET,
                key_rotation_period=0,  # Not applicable
                salt_strategy="none",
                purpose_limitation=["research", "testing"],
                retention_period=None,
                created_date=datetime.now(),
                created_by="system",
                approved_by="admin",
                version="1.0"
            )
        ]
        
        for policy in policies:
            self.policies[policy.policy_id] = policy
            logger.info(f"Created pseudonymization policy: {policy.policy_name}")

    async def _initialize_key_management(self):
        # Generate master keys for different purposes
        master_keys = [
            {
                "purpose": "encryption",
                "algorithm": "AES-256",
                "scope": PseudonymScope.CROSS_DATASET
            },
            {
                "purpose": "hashing",
                "algorithm": "HMAC-SHA256",
                "scope": PseudonymScope.SINGLE_DATASET
            },
            {
                "purpose": "tokenization",
                "algorithm": "AES-256",
                "scope": PseudonymScope.PURPOSE_LIMITED
            }
        ]
        
        for key_config in master_keys:
            await self._generate_key(
                purpose=key_config["purpose"],
                algorithm=key_config["algorithm"],
                scope=key_config["scope"]
            )
        
        logger.info("Initialized key management system")

    async def _generate_key(
        self,
        purpose: str,
        algorithm: str,
        scope: PseudonymScope,
        expiry_days: Optional[int] = None
    ) -> str:
        key_id = f"key_{uuid.uuid4().hex[:8]}"
        
        # Generate key based on algorithm
        if algorithm == "AES-256":
            key_value = Fernet.generate_key()
        elif algorithm == "HMAC-SHA256":
            key_value = secrets.token_bytes(32)
        else:
            key_value = secrets.token_bytes(32)
        
        expiry_date = None
        if expiry_days:
            expiry_date = datetime.now() + timedelta(days=expiry_days)
        
        key_record = PseudonymizationKey(
            key_id=key_id,
            key_value=key_value,
            algorithm=algorithm,
            purpose=purpose,
            created_date=datetime.now(),
            expiry_date=expiry_date,
            rotation_count=0,
            status="active",
            scope=scope,
            associated_policies=[]
        )
        
        self.keys[key_id] = key_record
        logger.info(f"Generated {algorithm} key for {purpose}: {key_id}")
        
        return key_id

    async def pseudonymize_data(
        self,
        data: Union[str, List[str], Dict[str, Any]],
        policy_id: str,
        context: str = "default"
    ) -> Union[str, List[str], Dict[str, Any]]:
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")
        
        policy = self.policies[policy_id]
        
        if isinstance(data, str):
            return await self._pseudonymize_single_value(data, policy, context)
        elif isinstance(data, list):
            return [await self._pseudonymize_single_value(item, policy, context) for item in data]
        elif isinstance(data, dict):
            result = {}
            for key, value in data.items():
                if isinstance(value, str):
                    result[key] = await self._pseudonymize_single_value(value, policy, context)
                else:
                    result[key] = value
            return result
        else:
            raise ValueError("Unsupported data type for pseudonymization")

    async def _pseudonymize_single_value(
        self,
        value: str,
        policy: PseudonymizationPolicy,
        context: str
    ) -> str:
        if policy.method == PseudonymizationMethod.HASH_BASED:
            return await self._hash_based_pseudonymization(value, policy, context)
        elif policy.method == PseudonymizationMethod.ENCRYPTION_BASED:
            return await self._encryption_based_pseudonymization(value, policy, context)
        elif policy.method == PseudonymizationMethod.TOKEN_BASED:
            return await self._token_based_pseudonymization(value, policy, context)
        elif policy.method == PseudonymizationMethod.FORMAT_PRESERVING:
            return await self._format_preserving_pseudonymization(value, policy, context)
        elif policy.method == PseudonymizationMethod.SYNTHETIC_DATA:
            return await self._synthetic_data_generation(value, policy, context)
        else:
            raise ValueError(f"Unsupported pseudonymization method: {policy.method}")

    async def _hash_based_pseudonymization(
        self,
        value: str,
        policy: PseudonymizationPolicy,
        context: str
    ) -> str:
        # Get or generate salt based on strategy
        salt = await self._get_salt(policy.salt_strategy, context, value)
        
        # Get appropriate key for HMAC
        key = await self._get_key_for_policy(policy, "hashing")
        
        if policy.hash_algorithm == HashAlgorithm.SHA256:
            if key:
                pseudonym = hmac.new(key.key_value, (value + salt).encode(), hashlib.sha256).hexdigest()
            else:
                pseudonym = hashlib.sha256((value + salt).encode()).hexdigest()
        elif policy.hash_algorithm == HashAlgorithm.SHA512:
            if key:
                pseudonym = hmac.new(key.key_value, (value + salt).encode(), hashlib.sha512).hexdigest()
            else:
                pseudonym = hashlib.sha512((value + salt).encode()).hexdigest()
        elif policy.hash_algorithm == HashAlgorithm.PBKDF2:
            # Use PBKDF2 for key stretching
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            key_material = base64.urlsafe_b64encode(kdf.derive(value.encode()))
            pseudonym = key_material.decode()[:32]  # Truncate to reasonable length
        else:
            pseudonym = hashlib.sha256((value + salt).encode()).hexdigest()
        
        # Record the pseudonymization
        await self._record_pseudonymization(
            original=value,
            pseudonym=pseudonym,
            policy=policy,
            context=context,
            salt=salt,
            key_id=key.key_id if key else None
        )
        
        return pseudonym

    async def _encryption_based_pseudonymization(
        self,
        value: str,
        policy: PseudonymizationPolicy,
        context: str
    ) -> str:
        # Get encryption key
        key = await self._get_key_for_policy(policy, "encryption")
        if not key:
            raise ValueError("No encryption key available for policy")
        
        # Use Fernet for symmetric encryption
        fernet = Fernet(key.key_value)
        encrypted_bytes = fernet.encrypt(value.encode())
        pseudonym = base64.urlsafe_b64encode(encrypted_bytes).decode()
        
        # Record the pseudonymization
        await self._record_pseudonymization(
            original=value,
            pseudonym=pseudonym,
            policy=policy,
            context=context,
            key_id=key.key_id
        )
        
        return pseudonym

    async def _token_based_pseudonymization(
        self,
        value: str,
        policy: PseudonymizationPolicy,
        context: str
    ) -> str:
        # Check if we already have a token for this value
        existing_record = await self._find_existing_pseudonym(value, policy.policy_id, context)
        if existing_record:
            return existing_record.pseudonym
        
        # Generate new token
        token = f"TKN_{secrets.token_hex(16)}"
        
        # Store the mapping for reversibility
        if policy.reversibility == ReversibilityLevel.REVERSIBLE_WITH_MAPPING:
            self.reverse_mapping[token] = value
        
        # Record the pseudonymization
        await self._record_pseudonymization(
            original=value,
            pseudonym=token,
            policy=policy,
            context=context
        )
        
        return token

    async def _format_preserving_pseudonymization(
        self,
        value: str,
        policy: PseudonymizationPolicy,
        context: str
    ) -> str:
        # Detect format and apply appropriate transformation
        if re.match(r'^[\+]?[1-9]?[\d\s\-\(\)]{10,}$', value):  # Phone number
            return await self._format_preserving_phone(value, policy, context)
        elif re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):  # Email
            return await self._format_preserving_email(value, policy, context)
        elif re.match(r'^\d{4}-?\d{4}-?\d{4}-?\d{4}$', value):  # Credit card
            return await self._format_preserving_credit_card(value, policy, context)
        else:
            # Default: preserve length and character types
            return await self._format_preserving_generic(value, policy, context)

    async def _format_preserving_phone(self, phone: str, policy: PseudonymizationPolicy, context: str) -> str:
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        
        # Generate pseudonym with same format
        mapping_key = f"phone_{policy.policy_id}_{context}"
        if mapping_key not in self.format_preserving_mappings:
            self.format_preserving_mappings[mapping_key] = {}
        
        if digits in self.format_preserving_mappings[mapping_key]:
            pseudo_digits = self.format_preserving_mappings[mapping_key][digits]
        else:
            # Generate new pseudonym digits
            pseudo_digits = ''.join([str(secrets.randbelow(10)) for _ in range(len(digits))])
            self.format_preserving_mappings[mapping_key][digits] = pseudo_digits
        
        # Apply original format
        pseudo_phone = phone
        for i, (orig, pseudo) in enumerate(zip(digits, pseudo_digits)):
            pseudo_phone = pseudo_phone.replace(orig, pseudo, 1)
        
        await self._record_pseudonymization(phone, pseudo_phone, policy, context)
        return pseudo_phone

    async def _format_preserving_email(self, email: str, policy: PseudonymizationPolicy, context: str) -> str:
        local, domain = email.split('@', 1)
        
        # Pseudonymize local part while preserving length
        pseudo_local = await self._format_preserving_generic(local, policy, context)
        
        # Keep domain or pseudonymize it
        if '.' in domain:
            domain_parts = domain.split('.')
            pseudo_domain = f"{secrets.token_hex(4)}.{domain_parts[-1]}"  # Keep TLD
        else:
            pseudo_domain = secrets.token_hex(6)
        
        pseudo_email = f"{pseudo_local}@{pseudo_domain}"
        await self._record_pseudonymization(email, pseudo_email, policy, context)
        return pseudo_email

    async def _format_preserving_credit_card(self, cc: str, policy: PseudonymizationPolicy, context: str) -> str:
        # Remove non-digits
        digits = re.sub(r'\D', '', cc)
        
        # Generate pseudonym digits (preserve first digit for card type)
        first_digit = digits[0]
        pseudo_digits = first_digit + ''.join([str(secrets.randbelow(10)) for _ in range(len(digits) - 1)])
        
        # Apply original format
        pseudo_cc = cc
        for orig, pseudo in zip(digits, pseudo_digits):
            pseudo_cc = pseudo_cc.replace(orig, pseudo, 1)
        
        await self._record_pseudonymization(cc, pseudo_cc, policy, context)
        return pseudo_cc

    async def _format_preserving_generic(self, value: str, policy: PseudonymizationPolicy, context: str) -> str:
        # Preserve character types and positions
        result = []
        for char in value:
            if char.isalpha():
                if char.isupper():
                    result.append(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
                else:
                    result.append(secrets.choice('abcdefghijklmnopqrstuvwxyz'))
            elif char.isdigit():
                result.append(str(secrets.randbelow(10)))
            else:
                result.append(char)  # Preserve special characters
        
        pseudonym = ''.join(result)
        await self._record_pseudonymization(value, pseudonym, policy, context)
        return pseudonym

    async def _synthetic_data_generation(self, value: str, policy: PseudonymizationPolicy, context: str) -> str:
        # Generate synthetic data based on detected type
        data_type = await self._detect_data_type(value)
        
        if data_type == "age":
            # Generate realistic age
            return str(secrets.randbelow(80) + 18)
        elif data_type == "name":
            # Generate synthetic name
            first_names = ["Alex", "Sam", "Jordan", "Taylor", "Casey", "Morgan", "Riley", "Avery"]
            last_names = ["Smith", "Johnson", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
            return f"{secrets.choice(first_names)} {secrets.choice(last_names)}"
        elif data_type == "location":
            # Generate synthetic location
            cities = ["Springfield", "Riverside", "Franklin", "Georgetown", "Clinton", "Fairview"]
            states = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA"]
            return f"{secrets.choice(cities)}, {secrets.choice(states)}"
        else:
            # Default synthetic generation
            return f"SYNTHETIC_{secrets.token_hex(8)}"

    async def _detect_data_type(self, value: str) -> str:
        # Simple data type detection
        if value.isdigit() and 18 <= int(value) <= 100:
            return "age"
        elif re.match(r'^[A-Za-z\s]+$', value) and len(value.split()) <= 3:
            return "name"
        elif ',' in value and any(state in value.upper() for state in ['CA', 'NY', 'TX', 'FL']):
            return "location"
        else:
            return "unknown"

    async def _get_salt(self, strategy: str, context: str, value: str) -> str:
        if strategy == "per_dataset":
            return hashlib.sha256(context.encode()).hexdigest()[:16]
        elif strategy == "per_record":
            return hashlib.sha256((context + value).encode()).hexdigest()[:16]
        elif strategy == "global":
            return "global_salt_12345"  # Should be configurable
        else:
            return secrets.token_hex(16)

    async def _get_key_for_policy(self, policy: PseudonymizationPolicy, purpose: str) -> Optional[PseudonymizationKey]:
        for key in self.keys.values():
            if (key.purpose == purpose and 
                key.status == "active" and
                key.scope == policy.scope):
                return key
        return None

    async def _find_existing_pseudonym(self, original: str, policy_id: str, context: str) -> Optional[PseudonymRecord]:
        for record in self.pseudonym_records.values():
            if (record.original_identifier == original and
                record.policy_id == policy_id and
                record.dataset_context == context):
                return record
        return None

    async def _record_pseudonymization(
        self,
        original: str,
        pseudonym: str,
        policy: PseudonymizationPolicy,
        context: str,
        salt: Optional[str] = None,
        key_id: Optional[str] = None
    ):
        record_id = f"pr_{uuid.uuid4().hex[:8]}"
        
        expiry_date = None
        if policy.retention_period:
            expiry_date = datetime.now() + timedelta(days=policy.retention_period)
        
        record = PseudonymRecord(
            record_id=record_id,
            original_identifier=original,
            pseudonym=pseudonym,
            method_used=policy.method,
            policy_id=policy.policy_id,
            key_id=key_id,
            salt=salt,
            created_date=datetime.now(),
            expiry_date=expiry_date,
            dataset_context=context,
            purpose=policy.purpose_limitation,
            reversible=(policy.reversibility != ReversibilityLevel.IRREVERSIBLE),
            access_log=[]
        )
        
        self.pseudonym_records[record_id] = record

    async def de_pseudonymize(self, pseudonym: str, policy_id: str, context: str = "default") -> Optional[str]:
        # Find the pseudonym record
        pseudonym_record = None
        for record in self.pseudonym_records.values():
            if (record.pseudonym == pseudonym and
                record.policy_id == policy_id and
                record.dataset_context == context):
                pseudonym_record = record
                break
        
        if not pseudonym_record:
            logger.warning(f"Pseudonym record not found for {pseudonym}")
            return None
        
        if not pseudonym_record.reversible:
            logger.warning(f"Pseudonym {pseudonym} is not reversible")
            return None
        
        policy = self.policies[policy_id]
        
        # Log access
        pseudonym_record.access_log.append(f"de_pseudonymize_{datetime.now().isoformat()}")
        
        if policy.method == PseudonymizationMethod.ENCRYPTION_BASED:
            return await self._decrypt_pseudonym(pseudonym, pseudonym_record)
        elif policy.method == PseudonymizationMethod.TOKEN_BASED:
            return self.reverse_mapping.get(pseudonym)
        elif policy.method == PseudonymizationMethod.FORMAT_PRESERVING:
            return await self._reverse_format_preserving(pseudonym, policy, context)
        else:
            logger.warning(f"De-pseudonymization not supported for method: {policy.method}")
            return None

    async def _decrypt_pseudonym(self, pseudonym: str, record: PseudonymRecord) -> Optional[str]:
        if not record.key_id:
            return None
        
        key = self.keys.get(record.key_id)
        if not key or key.status != "active":
            logger.warning(f"Key {record.key_id} not available for decryption")
            return None
        
        try:
            fernet = Fernet(key.key_value)
            encrypted_bytes = base64.urlsafe_b64decode(pseudonym.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt pseudonym: {e}")
            return None

    async def _reverse_format_preserving(self, pseudonym: str, policy: PseudonymizationPolicy, context: str) -> Optional[str]:
        # Search through format preserving mappings
        mapping_key = f"phone_{policy.policy_id}_{context}"  # Simplified - should detect type
        
        if mapping_key in self.format_preserving_mappings:
            for original, pseudo in self.format_preserving_mappings[mapping_key].items():
                if pseudo in pseudonym:  # Approximate match
                    return original
        
        return None

    async def rotate_keys(self, policy_id: str) -> bool:
        if policy_id not in self.policies:
            raise ValueError(f"Policy {policy_id} not found")
        
        policy = self.policies[policy_id]
        
        # Find keys associated with this policy
        associated_keys = []
        for key in self.keys.values():
            if policy_id in key.associated_policies:
                associated_keys.append(key)
        
        # Generate new keys
        new_keys = []
        for old_key in associated_keys:
            new_key_id = await self._generate_key(
                purpose=old_key.purpose,
                algorithm=old_key.algorithm,
                scope=old_key.scope,
                expiry_days=policy.key_rotation_period
            )
            
            new_key = self.keys[new_key_id]
            new_key.associated_policies.append(policy_id)
            new_keys.append(new_key)
            
            # Mark old key as expired
            old_key.status = "expired"
            old_key.rotation_count += 1
        
        logger.info(f"Rotated {len(new_keys)} keys for policy {policy_id}")
        return True

    async def cleanup_expired_pseudonyms(self) -> int:
        expired_count = 0
        now = datetime.now()
        
        expired_records = []
        for record_id, record in self.pseudonym_records.items():
            if record.expiry_date and record.expiry_date < now:
                expired_records.append(record_id)
        
        for record_id in expired_records:
            record = self.pseudonym_records[record_id]
            
            # Clean up reverse mappings
            if record.pseudonym in self.reverse_mapping:
                del self.reverse_mapping[record.pseudonym]
            
            # Remove record
            del self.pseudonym_records[record_id]
            expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired pseudonym records")
        return expired_count

    async def get_pseudonymization_statistics(self) -> Dict[str, Any]:
        stats = {
            "total_pseudonyms": len(self.pseudonym_records),
            "active_policies": len([p for p in self.policies.values()]),
            "active_keys": len([k for k in self.keys.values() if k.status == "active"]),
            "method_breakdown": {},
            "reversibility_breakdown": {},
            "scope_breakdown": {},
            "expiring_soon": 0
        }
        
        # Calculate breakdowns
        now = datetime.now()
        thirty_days = timedelta(days=30)
        
        for record in self.pseudonym_records.values():
            method = record.method_used.value
            stats["method_breakdown"][method] = stats["method_breakdown"].get(method, 0) + 1
            
            if record.expiry_date and record.expiry_date - now < thirty_days:
                stats["expiring_soon"] += 1
        
        for policy in self.policies.values():
            reversibility = policy.reversibility.value
            scope = policy.scope.value
            
            stats["reversibility_breakdown"][reversibility] = stats["reversibility_breakdown"].get(reversibility, 0) + 1
            stats["scope_breakdown"][scope] = stats["scope_breakdown"].get(scope, 0) + 1
        
        return stats

    async def validate_pseudonym_integrity(self, pseudonym: str, original: Optional[str] = None) -> Dict[str, Any]:
        # Find pseudonym record
        pseudonym_record = None
        for record in self.pseudonym_records.values():
            if record.pseudonym == pseudonym:
                pseudonym_record = record
                break
        
        if not pseudonym_record:
            return {
                "valid": False,
                "issues": ["pseudonym_not_found"],
                "record_exists": False
            }
        
        issues = []
        
        # Check if policy still exists
        if pseudonym_record.policy_id not in self.policies:
            issues.append("policy_not_found")
        
        # Check if key is still available (for reversible pseudonyms)
        if pseudonym_record.key_id and pseudonym_record.key_id not in self.keys:
            issues.append("key_not_found")
        elif pseudonym_record.key_id:
            key = self.keys[pseudonym_record.key_id]
            if key.status != "active":
                issues.append("key_inactive")
        
        # Check expiry
        if pseudonym_record.expiry_date and pseudonym_record.expiry_date < datetime.now():
            issues.append("pseudonym_expired")
        
        # Verify integrity if original is provided
        if original and pseudonym_record.original_identifier != original:
            issues.append("original_mismatch")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "record_exists": True,
            "created_date": pseudonym_record.created_date.isoformat(),
            "expiry_date": pseudonym_record.expiry_date.isoformat() if pseudonym_record.expiry_date else None,
            "reversible": pseudonym_record.reversible
        }

    async def export_pseudonymization_data(self, include_mappings: bool = False) -> Dict[str, Any]:
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_records": len(self.pseudonym_records),
            "policies": {},
            "statistics": await self.get_pseudonymization_statistics()
        }
        
        # Export policies
        for policy_id, policy in self.policies.items():
            export_data["policies"][policy_id] = {
                "policy_name": policy.policy_name,
                "method": policy.method.value,
                "reversibility": policy.reversibility.value,
                "scope": policy.scope.value,
                "applicable_data_types": policy.applicable_data_types
            }
        
        # Export pseudonym records (without original identifiers for security)
        export_data["pseudonym_records"] = {}
        for record_id, record in self.pseudonym_records.items():
            record_data = {
                "pseudonym": record.pseudonym,
                "method_used": record.method_used.value,
                "policy_id": record.policy_id,
                "created_date": record.created_date.isoformat(),
                "dataset_context": record.dataset_context,
                "reversible": record.reversible
            }
            
            if include_mappings and record.reversible:
                record_data["original_identifier"] = record.original_identifier
            
            export_data["pseudonym_records"][record_id] = record_data
        
        logger.info(f"Exported pseudonymization data: {len(self.pseudonym_records)} records")
        return export_data