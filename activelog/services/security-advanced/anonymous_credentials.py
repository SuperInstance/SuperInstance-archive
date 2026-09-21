"""
Anonymous Credentials System
Cryptographic credentials that allow authentication without revealing identity
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from enum import Enum
import hashlib
import hmac
import secrets
import asyncio
from datetime import datetime, timedelta
import json
import base64
from abc import ABC, abstractmethod
import math

class CredentialType(Enum):
    BASIC_ANONYMOUS = "basic_anonymous"
    ATTRIBUTE_BASED = "attribute_based"
    GROUP_SIGNATURE = "group_signature"
    RING_SIGNATURE = "ring_signature"
    ZERO_KNOWLEDGE_PROOF = "zero_knowledge_proof"

class AttributeType(Enum):
    AGE = "age"
    ROLE = "role"
    CLEARANCE_LEVEL = "clearance_level"
    DEPARTMENT = "department"
    LOCATION = "location"
    MEMBERSHIP = "membership"
    CERTIFICATION = "certification"

class ProofType(Enum):
    POSSESSION = "possession"
    RANGE = "range"
    SET_MEMBERSHIP = "set_membership"
    INEQUALITY = "inequality"
    AND = "and"
    OR = "or"

class CredentialStatus(Enum):
    VALID = "valid"
    REVOKED = "revoked"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

@dataclass
class CredentialAttribute:
    """Attribute within an anonymous credential"""
    attribute_type: AttributeType
    value: Any
    is_revealed: bool
    proof_type: Optional[ProofType] = None
    proof_parameters: Optional[Dict[str, Any]] = None

@dataclass
class CredentialSchema:
    """Schema defining structure of credentials"""
    schema_id: str
    name: str
    version: str
    issuer: str
    attributes: List[AttributeType]
    validity_period: timedelta
    revocation_supported: bool

@dataclass
class AnonymousCredential:
    """Anonymous credential containing encrypted attributes"""
    credential_id: str
    schema_id: str
    credential_blob: bytes  # Encrypted credential data
    signature: str
    issued_at: datetime
    expires_at: datetime
    status: CredentialStatus
    revocation_registry_id: Optional[str] = None

@dataclass
class CredentialRequest:
    """Request for issuing a new credential"""
    request_id: str
    schema_id: str
    attributes: Dict[AttributeType, Any]
    requester_proof: str  # Proof of identity/eligibility
    nonce: str

@dataclass
class CredentialProof:
    """Zero-knowledge proof for credential attributes"""
    proof_id: str
    credential_id: str
    revealed_attributes: Dict[AttributeType, Any]
    proof_data: bytes
    challenge: str
    response: str
    timestamp: datetime

@dataclass
class PresentationRequest:
    """Request for credential presentation with specific requirements"""
    request_id: str
    verifier_id: str
    required_schema: str
    required_attributes: List[AttributeType]
    revealed_attributes: List[AttributeType]
    predicates: List[Dict[str, Any]]  # Age > 18, Role in [admin, user], etc.
    nonce: str

@dataclass
class CredentialPresentation:
    """Presentation of credential with proofs"""
    presentation_id: str
    request_id: str
    proofs: List[CredentialProof]
    revealed_data: Dict[AttributeType, Any]
    timestamp: datetime
    verifier_id: str

@dataclass
class RevocationRegistry:
    """Registry for tracking revoked credentials"""
    registry_id: str
    schema_id: str
    revoked_credentials: Set[str]
    accumulator_value: str
    last_updated: datetime

class CryptoProvider(ABC):
    """Abstract cryptographic provider for anonymous credentials"""
    
    @abstractmethod
    async def generate_keypair(self) -> Tuple[str, str]:
        """Generate public/private key pair"""
        pass
    
    @abstractmethod
    async def sign_credential(self, credential_data: bytes, private_key: str) -> str:
        """Sign credential data"""
        pass
    
    @abstractmethod
    async def verify_signature(self, data: bytes, signature: str, public_key: str) -> bool:
        """Verify signature"""
        pass
    
    @abstractmethod
    async def generate_zero_knowledge_proof(
        self, 
        secret: str, 
        public_value: str, 
        challenge: str
    ) -> str:
        """Generate zero-knowledge proof"""
        pass
    
    @abstractmethod
    async def verify_zero_knowledge_proof(
        self, 
        proof: str, 
        public_value: str, 
        challenge: str
    ) -> bool:
        """Verify zero-knowledge proof"""
        pass

class BasicCryptoProvider(CryptoProvider):
    """Basic cryptographic provider using standard algorithms"""
    
    async def generate_keypair(self) -> Tuple[str, str]:
        """Generate ECDSA-like keypair (simulated)"""
        private_key = secrets.token_hex(32)
        public_key = hashlib.sha256(private_key.encode()).hexdigest()
        return public_key, private_key
    
    async def sign_credential(self, credential_data: bytes, private_key: str) -> str:
        """Sign credential using HMAC"""
        return hmac.new(
            private_key.encode(),
            credential_data,
            hashlib.sha256
        ).hexdigest()
    
    async def verify_signature(self, data: bytes, signature: str, public_key: str) -> bool:
        """Verify HMAC signature (simplified)"""
        # In real implementation, would derive private key from public key relationship
        # This is a simplified version for demonstration
        expected_signature = hmac.new(
            public_key.encode(),  # Simplified - would use actual private key
            data,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    
    async def generate_zero_knowledge_proof(
        self, 
        secret: str, 
        public_value: str, 
        challenge: str
    ) -> str:
        """Generate Schnorr-like zero-knowledge proof"""
        # Simplified ZK proof (Fiat-Shamir heuristic)
        r = secrets.token_hex(16)  # Random nonce
        commitment = hashlib.sha256(f"{r}{secret}".encode()).hexdigest()
        response = hashlib.sha256(f"{r}{challenge}{secret}".encode()).hexdigest()
        return f"{commitment}:{response}"
    
    async def verify_zero_knowledge_proof(
        self, 
        proof: str, 
        public_value: str, 
        challenge: str
    ) -> bool:
        """Verify zero-knowledge proof"""
        try:
            commitment, response = proof.split(":")
            # Simplified verification
            expected_commitment = hashlib.sha256(f"{response}{challenge}".encode()).hexdigest()
            return len(commitment) == 64 and len(response) == 64  # Basic format check
        except:
            return False

class AttributeBasedCredentialSystem:
    """Attribute-based anonymous credential system"""
    
    def __init__(self, crypto_provider: CryptoProvider):
        self.crypto_provider = crypto_provider
        self.schemas: Dict[str, CredentialSchema] = {}
        self.issued_credentials: Dict[str, AnonymousCredential] = {}
        self.revocation_registries: Dict[str, RevocationRegistry] = {}
        self.issuer_keys: Dict[str, Tuple[str, str]] = {}  # issuer_id -> (public_key, private_key)
    
    async def create_credential_schema(
        self,
        name: str,
        version: str,
        issuer: str,
        attributes: List[AttributeType],
        validity_period: timedelta,
        revocation_supported: bool = True
    ) -> CredentialSchema:
        """Create a new credential schema"""
        schema_id = f"schema_{hashlib.sha256(f'{name}_{version}_{issuer}'.encode()).hexdigest()[:16]}"
        
        schema = CredentialSchema(
            schema_id=schema_id,
            name=name,
            version=version,
            issuer=issuer,
            attributes=attributes,
            validity_period=validity_period,
            revocation_supported=revocation_supported
        )
        
        self.schemas[schema_id] = schema
        
        # Create revocation registry if supported
        if revocation_supported:
            registry = RevocationRegistry(
                registry_id=f"reg_{schema_id}",
                schema_id=schema_id,
                revoked_credentials=set(),
                accumulator_value=secrets.token_hex(32),
                last_updated=datetime.now()
            )
            self.revocation_registries[registry.registry_id] = registry
        
        # Generate issuer keys if not exist
        if issuer not in self.issuer_keys:
            public_key, private_key = await self.crypto_provider.generate_keypair()
            self.issuer_keys[issuer] = (public_key, private_key)
        
        return schema
    
    async def issue_credential(
        self,
        request: CredentialRequest,
        issuer_id: str
    ) -> AnonymousCredential:
        """Issue an anonymous credential"""
        if request.schema_id not in self.schemas:
            raise ValueError(f"Schema {request.schema_id} not found")
        
        if issuer_id not in self.issuer_keys:
            raise ValueError(f"Issuer {issuer_id} not found")
        
        schema = self.schemas[request.schema_id]
        public_key, private_key = self.issuer_keys[issuer_id]
        
        # Verify requester proof (simplified)
        # In real implementation, would verify eligibility proofs
        
        # Create credential data
        credential_data = {
            "schema_id": request.schema_id,
            "attributes": {attr.value: value for attr, value in request.attributes.items()},
            "issued_at": datetime.now().isoformat(),
            "nonce": request.nonce
        }
        
        credential_json = json.dumps(credential_data, sort_keys=True)
        credential_blob = credential_json.encode()
        
        # Sign credential
        signature = await self.crypto_provider.sign_credential(credential_blob, private_key)
        
        # Create credential
        credential_id = f"cred_{secrets.token_hex(16)}"
        issued_at = datetime.now()
        expires_at = issued_at + schema.validity_period
        
        credential = AnonymousCredential(
            credential_id=credential_id,
            schema_id=request.schema_id,
            credential_blob=credential_blob,
            signature=signature,
            issued_at=issued_at,
            expires_at=expires_at,
            status=CredentialStatus.VALID,
            revocation_registry_id=f"reg_{request.schema_id}" if schema.revocation_supported else None
        )
        
        self.issued_credentials[credential_id] = credential
        return credential
    
    async def create_presentation(
        self,
        credential: AnonymousCredential,
        presentation_request: PresentationRequest
    ) -> CredentialPresentation:
        """Create credential presentation with zero-knowledge proofs"""
        if credential.status != CredentialStatus.VALID:
            raise ValueError("Credential is not valid")
        
        if credential.expires_at < datetime.now():
            raise ValueError("Credential has expired")
        
        # Parse credential data
        credential_data = json.loads(credential.credential_blob.decode())
        attributes = credential_data["attributes"]
        
        # Generate proofs for each required attribute
        proofs = []
        revealed_data = {}
        
        for attr_type in presentation_request.required_attributes:
            if attr_type.value not in attributes:
                raise ValueError(f"Required attribute {attr_type.value} not found in credential")
            
            # Check if attribute should be revealed
            if attr_type in presentation_request.revealed_attributes:
                revealed_data[attr_type] = attributes[attr_type.value]
            
            # Generate zero-knowledge proof
            secret_value = str(attributes[attr_type.value])
            public_commitment = hashlib.sha256(secret_value.encode()).hexdigest()
            challenge = hashlib.sha256(f"{presentation_request.nonce}{attr_type.value}".encode()).hexdigest()
            
            proof_data = await self.crypto_provider.generate_zero_knowledge_proof(
                secret_value,
                public_commitment,
                challenge
            )
            
            proof = CredentialProof(
                proof_id=f"proof_{secrets.token_hex(8)}",
                credential_id=credential.credential_id,
                revealed_attributes={attr_type: attributes[attr_type.value]} if attr_type in presentation_request.revealed_attributes else {},
                proof_data=proof_data.encode(),
                challenge=challenge,
                response=proof_data,
                timestamp=datetime.now()
            )
            proofs.append(proof)
        
        # Check predicates
        for predicate in presentation_request.predicates:
            self._verify_predicate(attributes, predicate)
        
        presentation = CredentialPresentation(
            presentation_id=f"pres_{secrets.token_hex(12)}",
            request_id=presentation_request.request_id,
            proofs=proofs,
            revealed_data=revealed_data,
            timestamp=datetime.now(),
            verifier_id=presentation_request.verifier_id
        )
        
        return presentation
    
    def _verify_predicate(self, attributes: Dict[str, Any], predicate: Dict[str, Any]) -> bool:
        """Verify a predicate against attributes"""
        predicate_type = predicate.get("type")
        attribute = predicate.get("attribute")
        value = predicate.get("value")
        
        if attribute not in attributes:
            return False
        
        attr_value = attributes[attribute]
        
        if predicate_type == "greater_than":
            return attr_value > value
        elif predicate_type == "less_than":
            return attr_value < value
        elif predicate_type == "equals":
            return attr_value == value
        elif predicate_type == "in_set":
            return attr_value in value
        elif predicate_type == "not_in_set":
            return attr_value not in value
        else:
            return False
    
    async def verify_presentation(
        self,
        presentation: CredentialPresentation,
        presentation_request: PresentationRequest
    ) -> bool:
        """Verify credential presentation"""
        # Check if presentation matches request
        if presentation.request_id != presentation_request.request_id:
            return False
        
        # Check timestamp freshness
        if datetime.now() - presentation.timestamp > timedelta(minutes=5):
            return False
        
        # Verify each proof
        for proof in presentation.proofs:
            # Check if credential exists and is valid
            if proof.credential_id not in self.issued_credentials:
                return False
            
            credential = self.issued_credentials[proof.credential_id]
            
            if credential.status != CredentialStatus.VALID:
                return False
            
            if credential.expires_at < datetime.now():
                return False
            
            # Verify zero-knowledge proof
            public_commitment = hashlib.sha256(str(proof.response).encode()).hexdigest()
            is_valid_proof = await self.crypto_provider.verify_zero_knowledge_proof(
                proof.response,
                public_commitment,
                proof.challenge
            )
            
            if not is_valid_proof:
                return False
        
        return True
    
    async def revoke_credential(self, credential_id: str, issuer_id: str) -> bool:
        """Revoke a credential"""
        if credential_id not in self.issued_credentials:
            return False
        
        credential = self.issued_credentials[credential_id]
        schema = self.schemas[credential.schema_id]
        
        # Check if issuer has authority to revoke
        if schema.issuer != issuer_id:
            return False
        
        # Update credential status
        credential.status = CredentialStatus.REVOKED
        
        # Update revocation registry
        if credential.revocation_registry_id and credential.revocation_registry_id in self.revocation_registries:
            registry = self.revocation_registries[credential.revocation_registry_id]
            registry.revoked_credentials.add(credential_id)
            registry.last_updated = datetime.now()
            # Update accumulator value
            registry.accumulator_value = hashlib.sha256(
                f"{registry.accumulator_value}{credential_id}".encode()
            ).hexdigest()
        
        return True
    
    async def check_revocation_status(self, credential_id: str) -> CredentialStatus:
        """Check revocation status of a credential"""
        if credential_id not in self.issued_credentials:
            return CredentialStatus.EXPIRED
        
        credential = self.issued_credentials[credential_id]
        
        # Check expiration
        if credential.expires_at < datetime.now():
            credential.status = CredentialStatus.EXPIRED
        
        return credential.status

def create_anonymous_credential_system(
    crypto_provider: Optional[CryptoProvider] = None
) -> AttributeBasedCredentialSystem:
    """Factory function to create anonymous credential system"""
    if crypto_provider is None:
        crypto_provider = BasicCryptoProvider()
    
    return AttributeBasedCredentialSystem(crypto_provider)

# Example usage
async def example_usage():
    """Example of using anonymous credentials"""
    
    # Create credential system
    credential_system = create_anonymous_credential_system()
    
    # Create a credential schema for employee badges
    employee_schema = await credential_system.create_credential_schema(
        name="Employee Badge",
        version="1.0",
        issuer="company_hr",
        attributes=[
            AttributeType.ROLE,
            AttributeType.DEPARTMENT,
            AttributeType.CLEARANCE_LEVEL,
            AttributeType.AGE
        ],
        validity_period=timedelta(days=365),
        revocation_supported=True
    )
    
    print(f"Created schema: {employee_schema.name} (ID: {employee_schema.schema_id})")
    
    # Create credential request
    request = CredentialRequest(
        request_id=f"req_{secrets.token_hex(8)}",
        schema_id=employee_schema.schema_id,
        attributes={
            AttributeType.ROLE: "developer",
            AttributeType.DEPARTMENT: "engineering",
            AttributeType.CLEARANCE_LEVEL: "level_2",
            AttributeType.AGE: 28
        },
        requester_proof="identity_proof_123",
        nonce=secrets.token_hex(16)
    )
    
    # Issue credential
    credential = await credential_system.issue_credential(request, "company_hr")
    print(f"Issued credential: {credential.credential_id}")
    
    # Create presentation request (e.g., for accessing secure area)
    presentation_request = PresentationRequest(
        request_id=f"pres_req_{secrets.token_hex(8)}",
        verifier_id="security_system",
        required_schema=employee_schema.schema_id,
        required_attributes=[AttributeType.CLEARANCE_LEVEL, AttributeType.DEPARTMENT],
        revealed_attributes=[AttributeType.DEPARTMENT],  # Only reveal department
        predicates=[
            {"type": "greater_than", "attribute": "age", "value": 21},  # Age > 21
            {"type": "in_set", "attribute": "clearance_level", "value": ["level_2", "level_3"]}  # Sufficient clearance
        ],
        nonce=secrets.token_hex(16)
    )
    
    # Create presentation
    presentation = await credential_system.create_presentation(credential, presentation_request)
    print(f"Created presentation: {presentation.presentation_id}")
    print(f"Revealed data: {presentation.revealed_data}")
    print(f"Number of proofs: {len(presentation.proofs)}")
    
    # Verify presentation
    is_valid = await credential_system.verify_presentation(presentation, presentation_request)
    print(f"Presentation valid: {is_valid}")
    
    # Check revocation status
    status = await credential_system.check_revocation_status(credential.credential_id)
    print(f"Credential status: {status.value}")
    
    # Revoke credential
    revoked = await credential_system.revoke_credential(credential.credential_id, "company_hr")
    print(f"Credential revoked: {revoked}")
    
    # Check status after revocation
    status = await credential_system.check_revocation_status(credential.credential_id)
    print(f"Credential status after revocation: {status.value}")

if __name__ == "__main__":
    asyncio.run(example_usage())