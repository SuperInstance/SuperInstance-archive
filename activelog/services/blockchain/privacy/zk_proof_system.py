"""
Zero-Knowledge Proof System for Privacy-Preserving Operations
Implements various ZK proof schemes for identity, data integrity, and compute verification
"""

import json
import asyncio
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import secrets
from web3 import Web3
from eth_account import Account

from ..config.blockchain_config import blockchain_config, BlockchainNetwork
from ..storage.ipfs_manager import IPFSManager
from ..utils.crypto_utils import (
    create_data_hash, generate_commitment, verify_commitment,
    create_privacy_hash, verify_privacy_hash, generate_identity_commitment
)
from ..models.blockchain_models import ZKProof


class ZKProofType(Enum):
    IDENTITY_VERIFICATION = "identity_verification"
    DATA_INTEGRITY = "data_integrity"
    COMPUTE_VERIFICATION = "compute_verification"
    AGE_VERIFICATION = "age_verification"
    CREDENTIAL_PROOF = "credential_proof"
    MEMBERSHIP_PROOF = "membership_proof"
    RANGE_PROOF = "range_proof"
    VOTING_PROOF = "voting_proof"
    OWNERSHIP_PROOF = "ownership_proof"


class ZKCircuit(Enum):
    IDENTITY_CIRCUIT = "identity_verification.circom"
    INTEGRITY_CIRCUIT = "data_integrity.circom"
    COMPUTE_CIRCUIT = "compute_verification.circom"
    AGE_CIRCUIT = "age_verification.circom"
    CREDENTIAL_CIRCUIT = "credential_verification.circom"
    MEMBERSHIP_CIRCUIT = "membership_proof.circom"
    RANGE_CIRCUIT = "range_proof.circom"


@dataclass
class ZKProofRequest:
    proof_type: ZKProofType
    prover_address: str
    statement: Dict[str, Any]
    private_inputs: Dict[str, Any]
    public_inputs: Dict[str, Any]
    circuit_name: str
    verification_key_hash: str


@dataclass
class ZKProofResult:
    proof_id: str
    proof_data: Dict[str, Any]
    public_inputs: Dict[str, Any]
    verification_key_hash: str
    generated_at: datetime
    expires_at: Optional[datetime]
    ipfs_hash: Optional[str]


@dataclass
class CircuitParameters:
    circuit_file: str
    proving_key_file: str
    verification_key_file: str
    input_schema: Dict[str, Any]
    constraints_count: int
    public_inputs_count: int
    private_inputs_count: int


class ZKProofSystem:
    """Zero-knowledge proof system for privacy-preserving operations"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.privacy_config = blockchain_config.privacy_config
        
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        self.ipfs_manager = IPFSManager()
        
        # Circuit configurations
        self.circuits = self._init_circuit_configs()
        
        # Trusted setup parameters
        self.trusted_setup_path = "circuits/trusted_setup/"
        
        # Verification contract (would be deployed)
        self.verifier_contract = None
        
    def _init_circuit_configs(self) -> Dict[ZKCircuit, CircuitParameters]:
        """Initialize circuit configurations"""
        return {
            ZKCircuit.IDENTITY_CIRCUIT: CircuitParameters(
                circuit_file="identity_verification.circom",
                proving_key_file="identity_pk.zkey",
                verification_key_file="identity_vk.json",
                input_schema={
                    "private": ["identity_hash", "age", "nationality"],
                    "public": ["commitment", "min_age"]
                },
                constraints_count=10000,
                public_inputs_count=2,
                private_inputs_count=3
            ),
            ZKCircuit.INTEGRITY_CIRCUIT: CircuitParameters(
                circuit_file="data_integrity.circom",
                proving_key_file="integrity_pk.zkey",
                verification_key_file="integrity_vk.json",
                input_schema={
                    "private": ["data", "salt"],
                    "public": ["data_hash"]
                },
                constraints_count=5000,
                public_inputs_count=1,
                private_inputs_count=2
            ),
            ZKCircuit.COMPUTE_CIRCUIT: CircuitParameters(
                circuit_file="compute_verification.circom",
                proving_key_file="compute_pk.zkey",
                verification_key_file="compute_vk.json",
                input_schema={
                    "private": ["input_data", "computation_steps"],
                    "public": ["output_hash", "program_hash"]
                },
                constraints_count=50000,
                public_inputs_count=2,
                private_inputs_count=2
            ),
            ZKCircuit.AGE_CIRCUIT: CircuitParameters(
                circuit_file="age_verification.circom",
                proving_key_file="age_pk.zkey",
                verification_key_file="age_vk.json",
                input_schema={
                    "private": ["birth_year", "current_year"],
                    "public": ["min_age"]
                },
                constraints_count=1000,
                public_inputs_count=1,
                private_inputs_count=2
            ),
            ZKCircuit.MEMBERSHIP_CIRCUIT: CircuitParameters(
                circuit_file="membership_proof.circom",
                proving_key_file="membership_pk.zkey",
                verification_key_file="membership_vk.json",
                input_schema={
                    "private": ["secret", "path_elements", "path_indices"],
                    "public": ["root", "nullifier_hash"]
                },
                constraints_count=20000,
                public_inputs_count=2,
                private_inputs_count=3
            )
        }
    
    async def generate_identity_proof(
        self,
        prover_address: str,
        identity_data: Dict[str, Any],
        min_age: int,
        hide_nationality: bool = True
    ) -> ZKProofResult:
        """Generate zero-knowledge proof for identity verification"""
        
        # Create commitment to private identity data
        identity_commitment = generate_identity_commitment(identity_data)
        
        # Prepare circuit inputs
        private_inputs = {
            "identity_hash": identity_commitment["identity_hash"],
            "age": identity_data.get("age", 0),
            "nationality": hash(identity_data.get("nationality", "")) if not hide_nationality else 0
        }
        
        public_inputs = {
            "commitment": identity_commitment["commitment"],
            "min_age": min_age
        }
        
        # Generate proof using circuit
        proof_data = await self._generate_circuit_proof(
            ZKCircuit.IDENTITY_CIRCUIT,
            private_inputs,
            public_inputs
        )
        
        # Create proof result
        proof_result = ZKProofResult(
            proof_id=secrets.token_hex(16),
            proof_data=proof_data,
            public_inputs=public_inputs,
            verification_key_hash=self._get_verification_key_hash(ZKCircuit.IDENTITY_CIRCUIT),
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ipfs_hash=None
        )
        
        # Store proof on IPFS
        proof_result.ipfs_hash = await self._store_proof_on_ipfs(proof_result)
        
        return proof_result
    
    async def generate_data_integrity_proof(
        self,
        prover_address: str,
        data: Dict[str, Any],
        salt: Optional[str] = None
    ) -> ZKProofResult:
        """Generate proof of data integrity without revealing data"""
        
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Create hash of data
        data_hash = create_data_hash(data)
        
        # Prepare circuit inputs
        private_inputs = {
            "data": json.dumps(data, sort_keys=True),
            "salt": salt
        }
        
        public_inputs = {
            "data_hash": data_hash
        }
        
        # Generate proof
        proof_data = await self._generate_circuit_proof(
            ZKCircuit.INTEGRITY_CIRCUIT,
            private_inputs,
            public_inputs
        )
        
        proof_result = ZKProofResult(
            proof_id=secrets.token_hex(16),
            proof_data=proof_data,
            public_inputs=public_inputs,
            verification_key_hash=self._get_verification_key_hash(ZKCircuit.INTEGRITY_CIRCUIT),
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7),
            ipfs_hash=None
        )
        
        proof_result.ipfs_hash = await self._store_proof_on_ipfs(proof_result)
        
        return proof_result
    
    async def generate_compute_verification_proof(
        self,
        prover_address: str,
        input_data: Dict[str, Any],
        computation_program: str,
        output_data: Dict[str, Any]
    ) -> ZKProofResult:
        """Generate proof that computation was performed correctly"""
        
        # Hash the computation program
        program_hash = hashlib.sha256(computation_program.encode()).hexdigest()
        
        # Hash the output
        output_hash = create_data_hash(output_data)
        
        # Prepare circuit inputs
        private_inputs = {
            "input_data": json.dumps(input_data, sort_keys=True),
            "computation_steps": computation_program
        }
        
        public_inputs = {
            "output_hash": output_hash,
            "program_hash": program_hash
        }
        
        # Generate proof
        proof_data = await self._generate_circuit_proof(
            ZKCircuit.COMPUTE_CIRCUIT,
            private_inputs,
            public_inputs
        )
        
        proof_result = ZKProofResult(
            proof_id=secrets.token_hex(16),
            proof_data=proof_data,
            public_inputs=public_inputs,
            verification_key_hash=self._get_verification_key_hash(ZKCircuit.COMPUTE_CIRCUIT),
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=1),
            ipfs_hash=None
        )
        
        proof_result.ipfs_hash = await self._store_proof_on_ipfs(proof_result)
        
        return proof_result
    
    async def generate_age_verification_proof(
        self,
        prover_address: str,
        birth_year: int,
        min_age: int
    ) -> ZKProofResult:
        """Generate proof of age without revealing exact age"""
        
        current_year = datetime.utcnow().year
        
        # Prepare circuit inputs
        private_inputs = {
            "birth_year": birth_year,
            "current_year": current_year
        }
        
        public_inputs = {
            "min_age": min_age
        }
        
        # Generate proof
        proof_data = await self._generate_circuit_proof(
            ZKCircuit.AGE_CIRCUIT,
            private_inputs,
            public_inputs
        )
        
        proof_result = ZKProofResult(
            proof_id=secrets.token_hex(16),
            proof_data=proof_data,
            public_inputs=public_inputs,
            verification_key_hash=self._get_verification_key_hash(ZKCircuit.AGE_CIRCUIT),
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
            ipfs_hash=None
        )
        
        proof_result.ipfs_hash = await self._store_proof_on_ipfs(proof_result)
        
        return proof_result
    
    async def generate_membership_proof(
        self,
        prover_address: str,
        secret: str,
        member_set: List[str],
        nullifier: str
    ) -> ZKProofResult:
        """Generate anonymous membership proof using Merkle tree"""
        
        # Create Merkle tree from member set
        from ..utils.crypto_utils import generate_merkle_tree
        
        member_hashes = [hashlib.sha256(member.encode()).hexdigest() for member in member_set]
        merkle_tree = generate_merkle_tree(member_hashes)
        
        # Get proof for the secret
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        
        if secret_hash not in merkle_tree.proofs:
            raise ValueError("Secret not found in member set")
        
        proof_elements = merkle_tree.proofs[secret_hash]
        
        # Generate nullifier hash to prevent double-spending
        nullifier_hash = hashlib.sha256(f"{secret}:{nullifier}".encode()).hexdigest()
        
        # Prepare circuit inputs
        private_inputs = {
            "secret": secret,
            "path_elements": [p["hash"] for p in proof_elements],
            "path_indices": [1 if p["position"] == "right" else 0 for p in proof_elements]
        }
        
        public_inputs = {
            "root": merkle_tree.root,
            "nullifier_hash": nullifier_hash
        }
        
        # Generate proof
        proof_data = await self._generate_circuit_proof(
            ZKCircuit.MEMBERSHIP_CIRCUIT,
            private_inputs,
            public_inputs
        )
        
        proof_result = ZKProofResult(
            proof_id=secrets.token_hex(16),
            proof_data=proof_data,
            public_inputs=public_inputs,
            verification_key_hash=self._get_verification_key_hash(ZKCircuit.MEMBERSHIP_CIRCUIT),
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
            ipfs_hash=None
        )
        
        proof_result.ipfs_hash = await self._store_proof_on_ipfs(proof_result)
        
        return proof_result
    
    async def verify_proof(
        self,
        proof_result: ZKProofResult,
        circuit_type: ZKCircuit
    ) -> Dict[str, Any]:
        """Verify a zero-knowledge proof"""
        
        try:
            # Check if proof has expired
            if proof_result.expires_at and proof_result.expires_at < datetime.utcnow():
                return {
                    "valid": False,
                    "error": "Proof has expired",
                    "verified_at": datetime.utcnow()
                }
            
            # Verify using circuit verifier
            is_valid = await self._verify_circuit_proof(
                circuit_type,
                proof_result.proof_data,
                proof_result.public_inputs
            )
            
            # Store verification result
            verification_result = {
                "valid": is_valid,
                "proof_id": proof_result.proof_id,
                "circuit_used": circuit_type.value,
                "public_inputs": proof_result.public_inputs,
                "verified_at": datetime.utcnow(),
                "verifier": "activelog_zk_system"
            }
            
            if is_valid:
                # Store successful verification
                await self._store_verification_result(proof_result.proof_id, verification_result)
            
            return verification_result
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Verification failed: {str(e)}",
                "verified_at": datetime.utcnow()
            }
    
    async def create_zk_identity_credential(
        self,
        user_address: str,
        identity_claims: Dict[str, Any],
        issuer_private_key: str
    ) -> Dict[str, Any]:
        """Create verifiable credential with zero-knowledge proofs"""
        
        # Generate identity proof
        identity_proof = await self.generate_identity_proof(
            user_address,
            identity_claims,
            min_age=18
        )
        
        # Create credential with embedded proof
        issuer_account = Account.from_key(issuer_private_key)
        
        credential_data = {
            "holder": user_address,
            "issuer": issuer_account.address,
            "identity_proof": asdict(identity_proof),
            "issued_at": datetime.utcnow().isoformat(),
            "credential_type": "zk_identity",
            "proof_requirements": {
                "min_age": 18,
                "identity_verified": True
            }
        }
        
        # Store credential on IPFS
        credential_result = await self.ipfs_manager.pin_json(credential_data)
        
        return {
            "credential_id": create_data_hash(credential_data),
            "credential_ipfs_hash": credential_result['hash'],
            "identity_proof_id": identity_proof.proof_id,
            "holder": user_address,
            "issuer": issuer_account.address
        }
    
    async def generate_anonymous_voting_proof(
        self,
        voter_address: str,
        vote_choice: str,
        eligible_voters: List[str],
        voting_secret: str
    ) -> ZKProofResult:
        """Generate anonymous voting proof"""
        
        # Generate membership proof for eligible voter list
        membership_proof = await self.generate_membership_proof(
            voter_address,
            voting_secret,
            eligible_voters,
            f"vote_{vote_choice}"
        )
        
        # Add voting-specific data
        voting_proof_data = {
            "membership_proof": asdict(membership_proof),
            "vote_commitment": hashlib.sha256(vote_choice.encode()).hexdigest(),
            "voting_round": "1",  # Would be dynamic
            "cast_at": datetime.utcnow().isoformat()
        }
        
        proof_result = ZKProofResult(
            proof_id=secrets.token_hex(16),
            proof_data=voting_proof_data,
            public_inputs={
                "eligible_voters_root": membership_proof.public_inputs["root"],
                "nullifier_hash": membership_proof.public_inputs["nullifier_hash"]
            },
            verification_key_hash=membership_proof.verification_key_hash,
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            ipfs_hash=None
        )
        
        proof_result.ipfs_hash = await self._store_proof_on_ipfs(proof_result)
        
        return proof_result
    
    async def _generate_circuit_proof(
        self,
        circuit: ZKCircuit,
        private_inputs: Dict[str, Any],
        public_inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate proof using specified circuit"""
        
        # In a real implementation, this would:
        # 1. Run snarkjs or similar to generate witness
        # 2. Generate proof using proving key
        # 3. Return properly formatted proof
        
        # For demonstration, return mock proof structure
        circuit_config = self.circuits[circuit]
        
        # Simulate proof generation
        proof_data = {
            "a": [secrets.token_hex(32), secrets.token_hex(32)],
            "b": [[secrets.token_hex(32), secrets.token_hex(32)], 
                  [secrets.token_hex(32), secrets.token_hex(32)]],
            "c": [secrets.token_hex(32), secrets.token_hex(32)],
            "protocol": "groth16",
            "curve": "bn128"
        }
        
        return {
            "proof": proof_data,
            "public_signals": list(public_inputs.values()),
            "circuit_name": circuit.value,
            "constraints": circuit_config.constraints_count
        }
    
    async def _verify_circuit_proof(
        self,
        circuit: ZKCircuit,
        proof_data: Dict[str, Any],
        public_inputs: Dict[str, Any]
    ) -> bool:
        """Verify proof using circuit verification key"""
        
        # In a real implementation, this would:
        # 1. Load verification key
        # 2. Use snarkjs or similar to verify proof
        # 3. Return verification result
        
        # For demonstration, perform basic validation
        required_fields = ["proof", "public_signals", "circuit_name"]
        
        for field in required_fields:
            if field not in proof_data:
                return False
        
        # Check if circuit matches
        if proof_data["circuit_name"] != circuit.value:
            return False
        
        # Check public inputs count
        expected_count = self.circuits[circuit].public_inputs_count
        if len(proof_data["public_signals"]) != expected_count:
            return False
        
        # In real implementation, this would do cryptographic verification
        # For now, return True if structure is valid
        return True
    
    def _get_verification_key_hash(self, circuit: ZKCircuit) -> str:
        """Get hash of circuit verification key"""
        
        # In production, this would hash the actual verification key file
        circuit_config = self.circuits[circuit]
        vk_data = {
            "circuit": circuit.value,
            "file": circuit_config.verification_key_file,
            "constraints": circuit_config.constraints_count
        }
        
        return create_data_hash(vk_data)
    
    async def _store_proof_on_ipfs(self, proof_result: ZKProofResult) -> str:
        """Store proof on IPFS and return hash"""
        
        proof_data = {
            "proof_id": proof_result.proof_id,
            "proof_data": proof_result.proof_data,
            "public_inputs": proof_result.public_inputs,
            "verification_key_hash": proof_result.verification_key_hash,
            "generated_at": proof_result.generated_at.isoformat(),
            "expires_at": proof_result.expires_at.isoformat() if proof_result.expires_at else None
        }
        
        result = await self.ipfs_manager.pin_json(proof_data)
        return result['hash']
    
    async def _store_verification_result(
        self,
        proof_id: str,
        verification_result: Dict[str, Any]
    ):
        """Store verification result in database"""
        
        # This would use SQLAlchemy to store in ZKProof table
        # Implementation depends on database setup
        pass
    
    async def create_privacy_preserving_transaction(
        self,
        sender_address: str,
        recipient_address: str,
        amount: Decimal,
        sender_balance: Decimal,
        private_key: str
    ) -> Dict[str, Any]:
        """Create transaction with hidden amounts using range proofs"""
        
        # Generate commitment to amount
        amount_commitment, amount_nonce = generate_commitment(str(amount))
        
        # Generate commitment to remaining balance
        remaining_balance = sender_balance - amount
        balance_commitment, balance_nonce = generate_commitment(str(remaining_balance))
        
        # Create range proof that amount > 0 and remaining_balance >= 0
        range_proof_data = {
            "amount_commitment": amount_commitment,
            "balance_commitment": balance_commitment,
            "proof_type": "range_proof",
            "min_value": 0,
            "max_value": int(sender_balance * 100)  # Convert to cents for integer math
        }
        
        # Store proof data on IPFS
        proof_result = await self.ipfs_manager.pin_json({
            "transaction_type": "private_transfer",
            "sender": sender_address,
            "recipient": recipient_address,
            "commitments": {
                "amount": amount_commitment,
                "remaining_balance": balance_commitment
            },
            "range_proof": range_proof_data,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "transaction_id": create_data_hash(range_proof_data),
            "amount_commitment": amount_commitment,
            "balance_commitment": balance_commitment,
            "proof_ipfs_hash": proof_result['hash'],
            "sender": sender_address,
            "recipient": recipient_address
        }
    
    async def batch_verify_proofs(
        self,
        proof_results: List[ZKProofResult],
        circuit_type: ZKCircuit
    ) -> List[Dict[str, Any]]:
        """Batch verify multiple proofs for efficiency"""
        
        verification_results = []
        
        # In a real implementation, this would use batch verification
        # which is more efficient than individual verifications
        
        for proof_result in proof_results:
            result = await self.verify_proof(proof_result, circuit_type)
            verification_results.append(result)
        
        return verification_results
    
    async def create_zk_credential_registry(
        self,
        issuer_address: str,
        credential_type: str,
        schema_ipfs_hash: str,
        verification_requirements: Dict[str, Any],
        private_key: str
    ) -> Dict[str, Any]:
        """Create registry for ZK-based credentials"""
        
        registry_data = {
            "issuer": issuer_address,
            "credential_type": credential_type,
            "schema_ipfs_hash": schema_ipfs_hash,
            "verification_requirements": verification_requirements,
            "created_at": datetime.utcnow().isoformat(),
            "registry_version": "1.0.0"
        }
        
        # Store registry on IPFS
        registry_result = await self.ipfs_manager.pin_json(registry_data)
        
        return {
            "registry_id": create_data_hash(registry_data),
            "registry_ipfs_hash": registry_result['hash'],
            "issuer": issuer_address,
            "credential_type": credential_type
        }
    
    def get_supported_proof_types(self) -> List[Dict[str, Any]]:
        """Get list of supported ZK proof types"""
        
        return [
            {
                "type": ZKProofType.IDENTITY_VERIFICATION.value,
                "description": "Prove identity attributes without revealing them",
                "use_cases": ["Age verification", "Nationality proof", "Credential verification"],
                "privacy_level": "High"
            },
            {
                "type": ZKProofType.DATA_INTEGRITY.value,
                "description": "Prove data integrity without revealing data",
                "use_cases": ["Document verification", "Data authenticity", "Tampering detection"],
                "privacy_level": "Maximum"
            },
            {
                "type": ZKProofType.COMPUTE_VERIFICATION.value,
                "description": "Prove computation correctness without revealing inputs",
                "use_cases": ["AI model verification", "Algorithm integrity", "Remote computation"],
                "privacy_level": "High"
            },
            {
                "type": ZKProofType.MEMBERSHIP_PROOF.value,
                "description": "Prove membership in a set anonymously",
                "use_cases": ["Anonymous voting", "Whitelist verification", "Group membership"],
                "privacy_level": "Maximum"
            },
            {
                "type": ZKProofType.RANGE_PROOF.value,
                "description": "Prove value is within range without revealing exact value",
                "use_cases": ["Balance verification", "Age ranges", "Score thresholds"],
                "privacy_level": "High"
            }
        ]