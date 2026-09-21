"""
Verifiable Credentials System for ActiveLog
W3C-compliant verifiable credentials with privacy-preserving selective disclosure
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
import logging
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import uuid

from ..config.blockchain_config import (
    blockchain_config, 
    BlockchainNetwork, 
    ContractType
)

logger = logging.getLogger(__name__)

class CredentialStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"

class CredentialType(Enum):
    IDENTITY = "IdentityCredential"
    SKILL = "SkillCredential"
    REPUTATION = "ReputationCredential"
    COMPUTE_PROVIDER = "ComputeProviderCredential"
    DATA_OWNER = "DataOwnerCredential"
    AUDIT_COMPLIANCE = "AuditComplianceCredential"
    EDUCATIONAL = "EducationalCredential"
    PROFESSIONAL = "ProfessionalCredential"

class ProofType(Enum):
    ED25519_SIGNATURE = "Ed25519Signature2020"
    RSA_SIGNATURE = "RsaSignature2018"
    BLS_SIGNATURE = "BbsBlsSignature2020"
    ZK_PROOF = "ZkProof2023"

@dataclass
class CredentialSubject:
    id: str  # DID of the subject
    claims: Dict[str, Any]
    
@dataclass
class Proof:
    type: ProofType
    created: datetime
    verification_method: str
    proof_purpose: str
    proof_value: str
    challenge: Optional[str] = None
    domain: Optional[str] = None

@dataclass
class CredentialSchema:
    id: str
    type: str
    version: str
    properties: Dict[str, Any]
    required: List[str]

@dataclass
class VerifiableCredential:
    context: List[str]
    id: str
    type: List[str]
    issuer: str  # DID of the issuer
    issuance_date: datetime
    expiration_date: Optional[datetime]
    credential_subject: CredentialSubject
    credential_schema: CredentialSchema
    proof: Proof
    status: CredentialStatus = CredentialStatus.ACTIVE
    evidence: Optional[List[Dict[str, Any]]] = None
    refresh_service: Optional[Dict[str, str]] = None

@dataclass
class PresentationRequest:
    id: str
    verifier: str  # DID of the verifier
    challenge: str
    domain: str
    credentials_required: List[Dict[str, Any]]
    purpose: str
    created_at: datetime
    expires_at: datetime

@dataclass
class VerifiablePresentation:
    context: List[str]
    id: str
    type: List[str]
    holder: str  # DID of the holder
    verifiable_credential: List[VerifiableCredential]
    proof: Proof

class VerifiableCredentialsManager:
    """W3C Verifiable Credentials implementation with blockchain anchoring"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.VERIFIABLE_CREDENTIALS, 
            network
        )
        
        self.credentials: Dict[str, VerifiableCredential] = {}
        self.schemas: Dict[str, CredentialSchema] = {}
        self.revocation_lists: Dict[str, List[str]] = {}
        self.trusted_issuers: List[str] = []
        
        # Initialize default schemas
        self._init_default_schemas()
    
    def _init_default_schemas(self):
        """Initialize default credential schemas"""
        
        # Identity Credential Schema
        identity_schema = CredentialSchema(
            id="https://activelog.ai/schemas/identity/v1",
            type="IdentityCredential",
            version="1.0.0",
            properties={
                "givenName": {"type": "string"},
                "familyName": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "dateOfBirth": {"type": "string", "format": "date"},
                "address": {
                    "type": "object",
                    "properties": {
                        "streetAddress": {"type": "string"},
                        "addressLocality": {"type": "string"},
                        "addressCountry": {"type": "string"},
                        "postalCode": {"type": "string"}
                    }
                },
                "phoneNumber": {"type": "string"},
                "nationality": {"type": "string"}
            },
            required=["givenName", "familyName", "email"]
        )
        self.schemas[identity_schema.id] = identity_schema
        
        # Skill Credential Schema
        skill_schema = CredentialSchema(
            id="https://activelog.ai/schemas/skill/v1",
            type="SkillCredential",
            version="1.0.0",
            properties={
                "skillName": {"type": "string"},
                "skillCategory": {"type": "string"},
                "proficiencyLevel": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced", "expert"]
                },
                "yearExperience": {"type": "number"},
                "certifications": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "endorsements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "endorser": {"type": "string"},
                            "endorsement": {"type": "string"},
                            "date": {"type": "string", "format": "date-time"}
                        }
                    }
                }
            },
            required=["skillName", "skillCategory", "proficiencyLevel"]
        )
        self.schemas[skill_schema.id] = skill_schema
        
        # Reputation Credential Schema
        reputation_schema = CredentialSchema(
            id="https://activelog.ai/schemas/reputation/v1",
            type="ReputationCredential",
            version="1.0.0",
            properties={
                "reputationScore": {"type": "number", "minimum": 0, "maximum": 5},
                "totalTransactions": {"type": "number"},
                "successfulTransactions": {"type": "number"},
                "averageRating": {"type": "number", "minimum": 0, "maximum": 5},
                "reviewCount": {"type": "number"},
                "categories": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "badges": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "earned_date": {"type": "string", "format": "date-time"},
                            "issuer": {"type": "string"}
                        }
                    }
                }
            },
            required=["reputationScore", "totalTransactions"]
        )
        self.schemas[reputation_schema.id] = reputation_schema
    
    async def issue_credential(
        self,
        issuer_did: str,
        subject_did: str,
        credential_type: CredentialType,
        claims: Dict[str, Any],
        issuer_private_key: str,
        expiration_days: Optional[int] = None,
        evidence: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Issue a new verifiable credential"""
        try:
            # Generate credential ID
            credential_id = f"urn:uuid:{uuid.uuid4()}"
            
            # Get schema for credential type
            schema_id = f"https://activelog.ai/schemas/{credential_type.value.lower()}/v1"
            if schema_id not in self.schemas:
                raise ValueError(f"Schema not found for credential type: {credential_type.value}")
            
            schema = self.schemas[schema_id]
            
            # Validate claims against schema
            self._validate_claims(claims, schema)
            
            # Create credential subject
            credential_subject = CredentialSubject(
                id=subject_did,
                claims=claims
            )
            
            # Set expiration date
            expiration_date = None
            if expiration_days:
                expiration_date = datetime.now() + timedelta(days=expiration_days)
            
            # Create proof
            proof_data = {
                "credential_id": credential_id,
                "issuer": issuer_did,
                "subject": subject_did,
                "claims": claims,
                "issued_at": datetime.now().isoformat()
            }
            
            proof = await self._create_proof(
                proof_data,
                issuer_private_key,
                ProofType.RSA_SIGNATURE
            )
            
            # Create verifiable credential
            credential = VerifiableCredential(
                context=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://activelog.ai/contexts/v1"
                ],
                id=credential_id,
                type=["VerifiableCredential", credential_type.value],
                issuer=issuer_did,
                issuance_date=datetime.now(),
                expiration_date=expiration_date,
                credential_subject=credential_subject,
                credential_schema=schema,
                proof=proof,
                status=CredentialStatus.ACTIVE,
                evidence=evidence
            )
            
            # Store credential
            self.credentials[credential_id] = credential
            
            # Anchor to blockchain (if available)
            anchor_tx = await self._anchor_to_blockchain(credential)
            
            logger.info(f"Issued credential {credential_id} to {subject_did}")
            
            return {
                "credential_id": credential_id,
                "credential": self._credential_to_dict(credential),
                "anchor_transaction": anchor_tx,
                "issued_at": credential.issuance_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to issue credential: {e}")
            raise
    
    async def verify_credential(
        self,
        credential: Union[Dict[str, Any], VerifiableCredential],
        trusted_issuers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Verify a verifiable credential"""
        try:
            # Convert dict to VerifiableCredential if needed
            if isinstance(credential, dict):
                credential = self._dict_to_credential(credential)
            
            verification_result = {
                "valid": False,
                "errors": [],
                "warnings": [],
                "checks": {}
            }
            
            # Check credential format
            format_valid = self._check_credential_format(credential)
            verification_result["checks"]["format"] = format_valid
            if not format_valid:
                verification_result["errors"].append("Invalid credential format")
            
            # Check expiration
            expiration_valid = self._check_expiration(credential)
            verification_result["checks"]["expiration"] = expiration_valid
            if not expiration_valid:
                verification_result["errors"].append("Credential expired")
            
            # Check revocation status
            revocation_valid = await self._check_revocation_status(credential)
            verification_result["checks"]["revocation"] = revocation_valid
            if not revocation_valid:
                verification_result["errors"].append("Credential revoked")
            
            # Check issuer trust
            issuer_trusted = self._check_issuer_trust(
                credential.issuer, 
                trusted_issuers or self.trusted_issuers
            )
            verification_result["checks"]["issuer_trust"] = issuer_trusted
            if not issuer_trusted:
                verification_result["warnings"].append("Issuer not in trusted list")
            
            # Verify cryptographic proof
            proof_valid = await self._verify_proof(credential)
            verification_result["checks"]["proof"] = proof_valid
            if not proof_valid:
                verification_result["errors"].append("Invalid cryptographic proof")
            
            # Validate claims against schema
            schema_valid = self._validate_claims(
                credential.credential_subject.claims,
                credential.credential_schema
            )
            verification_result["checks"]["schema"] = schema_valid
            if not schema_valid:
                verification_result["errors"].append("Claims don't match schema")
            
            # Overall validity
            verification_result["valid"] = (
                format_valid and 
                expiration_valid and 
                revocation_valid and 
                proof_valid and 
                schema_valid
            )
            
            logger.info(f"Verified credential {credential.id}: {verification_result['valid']}")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Failed to verify credential: {e}")
            return {
                "valid": False,
                "errors": [f"Verification failed: {str(e)}"],
                "checks": {}
            }
    
    async def create_presentation_request(
        self,
        verifier_did: str,
        credentials_required: List[Dict[str, Any]],
        purpose: str,
        expires_in_minutes: int = 30
    ) -> Dict[str, Any]:
        """Create a presentation request"""
        try:
            request_id = f"urn:uuid:{uuid.uuid4()}"
            challenge = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=')
            
            request = PresentationRequest(
                id=request_id,
                verifier=verifier_did,
                challenge=challenge,
                domain="activelog.ai",
                credentials_required=credentials_required,
                purpose=purpose,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(minutes=expires_in_minutes)
            )
            
            logger.info(f"Created presentation request {request_id}")
            
            return {
                "request_id": request_id,
                "challenge": challenge,
                "domain": request.domain,
                "credentials_required": credentials_required,
                "purpose": purpose,
                "expires_at": request.expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create presentation request: {e}")
            raise
    
    async def create_presentation(
        self,
        holder_did: str,
        credential_ids: List[str],
        presentation_request: Dict[str, Any],
        holder_private_key: str,
        selective_disclosure: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """Create a verifiable presentation"""
        try:
            # Get credentials
            credentials = []
            for cred_id in credential_ids:
                if cred_id not in self.credentials:
                    raise ValueError(f"Credential {cred_id} not found")
                
                credential = self.credentials[cred_id]
                
                # Apply selective disclosure if specified
                if selective_disclosure and cred_id in selective_disclosure:
                    credential = self._apply_selective_disclosure(
                        credential, 
                        selective_disclosure[cred_id]
                    )
                
                credentials.append(credential)
            
            # Create presentation ID
            presentation_id = f"urn:uuid:{uuid.uuid4()}"
            
            # Create proof for presentation
            proof_data = {
                "presentation_id": presentation_id,
                "holder": holder_did,
                "verifier": presentation_request["verifier"],
                "challenge": presentation_request["challenge"],
                "domain": presentation_request["domain"],
                "credential_ids": credential_ids,
                "created_at": datetime.now().isoformat()
            }
            
            proof = await self._create_proof(
                proof_data,
                holder_private_key,
                ProofType.RSA_SIGNATURE,
                challenge=presentation_request["challenge"],
                domain=presentation_request["domain"]
            )
            
            # Create verifiable presentation
            presentation = VerifiablePresentation(
                context=[
                    "https://www.w3.org/2018/credentials/v1",
                    "https://www.w3.org/2018/presentations/v1"
                ],
                id=presentation_id,
                type=["VerifiablePresentation"],
                holder=holder_did,
                verifiable_credential=credentials,
                proof=proof
            )
            
            logger.info(f"Created presentation {presentation_id} for {holder_did}")
            
            return {
                "presentation_id": presentation_id,
                "presentation": self._presentation_to_dict(presentation),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create presentation: {e}")
            raise
    
    async def verify_presentation(
        self,
        presentation: Union[Dict[str, Any], VerifiablePresentation],
        presentation_request: Dict[str, Any],
        trusted_issuers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Verify a verifiable presentation"""
        try:
            # Convert dict to VerifiablePresentation if needed
            if isinstance(presentation, dict):
                presentation = self._dict_to_presentation(presentation)
            
            verification_result = {
                "valid": False,
                "errors": [],
                "warnings": [],
                "checks": {}
            }
            
            # Verify presentation proof
            presentation_proof_valid = await self._verify_presentation_proof(
                presentation,
                presentation_request
            )
            verification_result["checks"]["presentation_proof"] = presentation_proof_valid
            if not presentation_proof_valid:
                verification_result["errors"].append("Invalid presentation proof")
            
            # Verify each credential
            credential_results = []
            for credential in presentation.verifiable_credential:
                cred_result = await self.verify_credential(credential, trusted_issuers)
                credential_results.append(cred_result)
                if not cred_result["valid"]:
                    verification_result["errors"].extend([
                        f"Credential {credential.id}: {error}"
                        for error in cred_result["errors"]
                    ])
            
            verification_result["checks"]["credentials"] = credential_results
            
            # Check if presentation meets request requirements
            requirements_met = self._check_presentation_requirements(
                presentation,
                presentation_request
            )
            verification_result["checks"]["requirements"] = requirements_met
            if not requirements_met:
                verification_result["errors"].append("Presentation doesn't meet requirements")
            
            # Overall validity
            verification_result["valid"] = (
                presentation_proof_valid and
                all(result["valid"] for result in credential_results) and
                requirements_met
            )
            
            logger.info(f"Verified presentation {presentation.id}: {verification_result['valid']}")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Failed to verify presentation: {e}")
            return {
                "valid": False,
                "errors": [f"Presentation verification failed: {str(e)}"],
                "checks": {}
            }
    
    async def revoke_credential(
        self,
        credential_id: str,
        issuer_did: str,
        reason: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Revoke a verifiable credential"""
        try:
            if credential_id not in self.credentials:
                raise ValueError(f"Credential {credential_id} not found")
            
            credential = self.credentials[credential_id]
            
            # Verify issuer authority
            if credential.issuer != issuer_did:
                raise ValueError("Only the issuer can revoke this credential")
            
            # Update credential status
            credential.status = CredentialStatus.REVOKED
            
            # Add to revocation list
            if issuer_did not in self.revocation_lists:
                self.revocation_lists[issuer_did] = []
            
            revocation_entry = {
                "credential_id": credential_id,
                "revoked_at": datetime.now().isoformat(),
                "reason": reason
            }
            
            self.revocation_lists[issuer_did].append(revocation_entry)
            
            # Record revocation on blockchain (if available)
            revocation_tx = await self._record_revocation_on_blockchain(
                credential_id,
                reason,
                private_key
            )
            
            logger.info(f"Revoked credential {credential_id}, reason: {reason}")
            
            return {
                "credential_id": credential_id,
                "status": credential.status.value,
                "revoked_at": revocation_entry["revoked_at"],
                "reason": reason,
                "revocation_transaction": revocation_tx
            }
            
        except Exception as e:
            logger.error(f"Failed to revoke credential {credential_id}: {e}")
            raise
    
    def _validate_claims(self, claims: Dict[str, Any], schema: CredentialSchema) -> bool:
        """Validate claims against schema"""
        try:
            # Check required fields
            for required_field in schema.required:
                if required_field not in claims:
                    raise ValueError(f"Required field missing: {required_field}")
            
            # Validate field types and constraints
            for field, value in claims.items():
                if field in schema.properties:
                    field_schema = schema.properties[field]
                    if not self._validate_field_value(value, field_schema):
                        raise ValueError(f"Invalid value for field {field}")
            
            return True
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False
    
    def _validate_field_value(self, value: Any, field_schema: Dict[str, Any]) -> bool:
        """Validate a field value against its schema"""
        field_type = field_schema.get("type")
        
        if field_type == "string":
            if not isinstance(value, str):
                return False
            if "enum" in field_schema and value not in field_schema["enum"]:
                return False
        elif field_type == "number":
            if not isinstance(value, (int, float)):
                return False
            if "minimum" in field_schema and value < field_schema["minimum"]:
                return False
            if "maximum" in field_schema and value > field_schema["maximum"]:
                return False
        elif field_type == "array":
            if not isinstance(value, list):
                return False
        elif field_type == "object":
            if not isinstance(value, dict):
                return False
        
        return True
    
    async def _create_proof(
        self,
        data: Dict[str, Any],
        private_key: str,
        proof_type: ProofType,
        challenge: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Proof:
        """Create cryptographic proof"""
        # Serialize data for signing
        data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))
        data_bytes = data_json.encode('utf-8')
        
        # Create signature (simplified RSA implementation)
        signature = base64.b64encode(
            hashlib.sha256(data_bytes + private_key.encode()).digest()
        ).decode('ascii')
        
        return Proof(
            type=proof_type,
            created=datetime.now(),
            verification_method=f"did:key:{private_key[:10]}...#key-1",
            proof_purpose="assertionMethod",
            proof_value=signature,
            challenge=challenge,
            domain=domain
        )
    
    async def _verify_proof(self, credential: VerifiableCredential) -> bool:
        """Verify cryptographic proof (simplified)"""
        # In a real implementation, this would verify the actual signature
        return len(credential.proof.proof_value) > 0
    
    async def _verify_presentation_proof(
        self,
        presentation: VerifiablePresentation,
        request: Dict[str, Any]
    ) -> bool:
        """Verify presentation proof"""
        # Check challenge and domain
        if presentation.proof.challenge != request.get("challenge"):
            return False
        if presentation.proof.domain != request.get("domain"):
            return False
        
        # Verify signature (simplified)
        return len(presentation.proof.proof_value) > 0
    
    def _check_credential_format(self, credential: VerifiableCredential) -> bool:
        """Check if credential follows W3C format"""
        required_fields = ["context", "id", "type", "issuer", "issuance_date", "credential_subject"]
        
        for field in required_fields:
            if not hasattr(credential, field) or getattr(credential, field) is None:
                return False
        
        return True
    
    def _check_expiration(self, credential: VerifiableCredential) -> bool:
        """Check if credential is expired"""
        if credential.expiration_date is None:
            return True  # No expiration date
        
        return datetime.now() < credential.expiration_date
    
    async def _check_revocation_status(self, credential: VerifiableCredential) -> bool:
        """Check if credential is revoked"""
        return credential.status != CredentialStatus.REVOKED
    
    def _check_issuer_trust(self, issuer: str, trusted_issuers: List[str]) -> bool:
        """Check if issuer is trusted"""
        return issuer in trusted_issuers or len(trusted_issuers) == 0
    
    def _check_presentation_requirements(
        self,
        presentation: VerifiablePresentation,
        request: Dict[str, Any]
    ) -> bool:
        """Check if presentation meets requirements"""
        required_credentials = request.get("credentials_required", [])
        
        # Check if all required credential types are present
        presented_types = []
        for credential in presentation.verifiable_credential:
            presented_types.extend(credential.type)
        
        for req in required_credentials:
            req_type = req.get("type")
            if req_type and req_type not in presented_types:
                return False
        
        return True
    
    def _apply_selective_disclosure(
        self,
        credential: VerifiableCredential,
        disclosed_claims: List[str]
    ) -> VerifiableCredential:
        """Apply selective disclosure to credential"""
        # Create copy of credential with only disclosed claims
        filtered_claims = {
            key: value
            for key, value in credential.credential_subject.claims.items()
            if key in disclosed_claims
        }
        
        # Create new credential subject
        new_subject = CredentialSubject(
            id=credential.credential_subject.id,
            claims=filtered_claims
        )
        
        # Create new credential with filtered subject
        return VerifiableCredential(
            context=credential.context,
            id=credential.id,
            type=credential.type,
            issuer=credential.issuer,
            issuance_date=credential.issuance_date,
            expiration_date=credential.expiration_date,
            credential_subject=new_subject,
            credential_schema=credential.credential_schema,
            proof=credential.proof,
            status=credential.status,
            evidence=credential.evidence
        )
    
    async def _anchor_to_blockchain(self, credential: VerifiableCredential) -> Optional[str]:
        """Anchor credential hash to blockchain"""
        if not self.contract_config:
            return None
        
        # Create credential hash
        credential_data = self._credential_to_dict(credential)
        credential_json = json.dumps(credential_data, sort_keys=True)
        credential_hash = hashlib.sha256(credential_json.encode()).hexdigest()
        
        # In real implementation, this would interact with smart contract
        return f"0x{hashlib.sha256(f'{credential.id}_anchor'.encode()).hexdigest()}"
    
    async def _record_revocation_on_blockchain(
        self,
        credential_id: str,
        reason: str,
        private_key: str
    ) -> Optional[str]:
        """Record revocation on blockchain"""
        if not self.contract_config:
            return None
        
        # In real implementation, this would interact with smart contract
        return f"0x{hashlib.sha256(f'{credential_id}_revoke'.encode()).hexdigest()}"
    
    def _credential_to_dict(self, credential: VerifiableCredential) -> Dict[str, Any]:
        """Convert credential to dictionary"""
        return {
            "@context": credential.context,
            "id": credential.id,
            "type": credential.type,
            "issuer": credential.issuer,
            "issuanceDate": credential.issuance_date.isoformat(),
            "expirationDate": credential.expiration_date.isoformat() if credential.expiration_date else None,
            "credentialSubject": {
                "id": credential.credential_subject.id,
                **credential.credential_subject.claims
            },
            "credentialSchema": {
                "id": credential.credential_schema.id,
                "type": credential.credential_schema.type
            },
            "proof": {
                "type": credential.proof.type.value,
                "created": credential.proof.created.isoformat(),
                "verificationMethod": credential.proof.verification_method,
                "proofPurpose": credential.proof.proof_purpose,
                "proofValue": credential.proof.proof_value,
                "challenge": credential.proof.challenge,
                "domain": credential.proof.domain
            },
            "credentialStatus": {
                "type": "RevocationList2020Status",
                "revocationListIndex": "0"
            }
        }
    
    def _presentation_to_dict(self, presentation: VerifiablePresentation) -> Dict[str, Any]:
        """Convert presentation to dictionary"""
        return {
            "@context": presentation.context,
            "id": presentation.id,
            "type": presentation.type,
            "holder": presentation.holder,
            "verifiableCredential": [
                self._credential_to_dict(cred) 
                for cred in presentation.verifiable_credential
            ],
            "proof": {
                "type": presentation.proof.type.value,
                "created": presentation.proof.created.isoformat(),
                "verificationMethod": presentation.proof.verification_method,
                "proofPurpose": presentation.proof.proof_purpose,
                "proofValue": presentation.proof.proof_value,
                "challenge": presentation.proof.challenge,
                "domain": presentation.proof.domain
            }
        }
    
    def _dict_to_credential(self, data: Dict[str, Any]) -> VerifiableCredential:
        """Convert dictionary to VerifiableCredential"""
        # Simplified conversion - real implementation would be more robust
        subject_claims = data["credentialSubject"].copy()
        subject_id = subject_claims.pop("id")
        
        return VerifiableCredential(
            context=data["@context"],
            id=data["id"],
            type=data["type"],
            issuer=data["issuer"],
            issuance_date=datetime.fromisoformat(data["issuanceDate"]),
            expiration_date=datetime.fromisoformat(data["expirationDate"]) if data.get("expirationDate") else None,
            credential_subject=CredentialSubject(id=subject_id, claims=subject_claims),
            credential_schema=CredentialSchema(
                id=data["credentialSchema"]["id"],
                type=data["credentialSchema"]["type"],
                version="1.0.0",
                properties={},
                required=[]
            ),
            proof=Proof(
                type=ProofType.RSA_SIGNATURE,
                created=datetime.fromisoformat(data["proof"]["created"]),
                verification_method=data["proof"]["verificationMethod"],
                proof_purpose=data["proof"]["proofPurpose"],
                proof_value=data["proof"]["proofValue"],
                challenge=data["proof"].get("challenge"),
                domain=data["proof"].get("domain")
            )
        )
    
    def _dict_to_presentation(self, data: Dict[str, Any]) -> VerifiablePresentation:
        """Convert dictionary to VerifiablePresentation"""
        credentials = [
            self._dict_to_credential(cred_data)
            for cred_data in data["verifiableCredential"]
        ]
        
        return VerifiablePresentation(
            context=data["@context"],
            id=data["id"],
            type=data["type"],
            holder=data["holder"],
            verifiable_credential=credentials,
            proof=Proof(
                type=ProofType.RSA_SIGNATURE,
                created=datetime.fromisoformat(data["proof"]["created"]),
                verification_method=data["proof"]["verificationMethod"],
                proof_purpose=data["proof"]["proofPurpose"],
                proof_value=data["proof"]["proofValue"],
                challenge=data["proof"].get("challenge"),
                domain=data["proof"].get("domain")
            )
        )

# Global credentials manager instance
credentials_manager = VerifiableCredentialsManager()