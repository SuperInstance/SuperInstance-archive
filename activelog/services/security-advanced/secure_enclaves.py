"""
Secure Enclaves for Sensitive Processing
Hardware-based trusted execution environments for protecting code and data
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from enum import Enum
import hashlib
import hmac
import secrets
import asyncio
from datetime import datetime, timedelta
import json
import base64
from abc import ABC, abstractmethod
import subprocess
import tempfile
import os

class EnclaveType(Enum):
    INTEL_SGX = "intel_sgx"
    ARM_TRUSTZONE = "arm_trustzone"
    AMD_SEV = "amd_sev"
    SOFTWARE_SIMULATION = "software_simulation"

class EnclaveState(Enum):
    CREATED = "created"
    LOADED = "loaded"
    RUNNING = "running"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    ERROR = "error"

class AttestationType(Enum):
    LOCAL = "local"
    REMOTE = "remote"
    ECDSA = "ecdsa"
    EPID = "epid"

class SecurityLevel(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    HIGH_SECURITY = "high_security"

@dataclass
class EnclaveConfiguration:
    """Configuration for secure enclave"""
    enclave_type: EnclaveType
    security_level: SecurityLevel
    memory_size: int  # in MB
    max_threads: int
    attestation_type: AttestationType
    debug_enabled: bool
    sealed_storage_enabled: bool
    remote_attestation_endpoint: Optional[str] = None

@dataclass
class EnclaveIdentity:
    """Identity and measurement of an enclave"""
    enclave_id: str
    measurement: str  # Hash of enclave code and data
    signer: str  # Identity of enclave signer
    product_id: str
    security_version: int
    attributes: Dict[str, Any]

@dataclass
class AttestationEvidence:
    """Evidence for enclave attestation"""
    enclave_identity: EnclaveIdentity
    attestation_type: AttestationType
    signature: str
    certificate_chain: List[str]
    timestamp: datetime
    nonce: Optional[str] = None

@dataclass
class SealedData:
    """Data sealed by enclave for persistent storage"""
    sealed_blob: bytes
    additional_data: bytes
    policy: str  # Sealing policy (MRENCLAVE, MRSIGNER, etc.)
    security_version: int

@dataclass
class EnclaveMetrics:
    """Performance and security metrics for enclave"""
    cpu_usage: float
    memory_usage: int
    attestation_count: int
    seal_operations: int
    unseal_operations: int
    exceptions_raised: int
    uptime: timedelta

@dataclass
class SecureComputationRequest:
    """Request for secure computation in enclave"""
    computation_id: str
    function_name: str
    encrypted_input: bytes
    input_hash: str
    requester_id: str
    attestation_required: bool

@dataclass
class SecureComputationResult:
    """Result from secure computation"""
    computation_id: str
    encrypted_output: bytes
    output_hash: str
    attestation_evidence: Optional[AttestationEvidence]
    execution_time: float
    memory_used: int

class TrustedExecutionEnvironment(ABC):
    """Abstract base for trusted execution environments"""
    
    @abstractmethod
    async def create_enclave(self, config: EnclaveConfiguration) -> str:
        """Create a new enclave instance"""
        pass
    
    @abstractmethod
    async def load_enclave(self, enclave_id: str, code: bytes) -> bool:
        """Load code into enclave"""
        pass
    
    @abstractmethod
    async def get_enclave_identity(self, enclave_id: str) -> EnclaveIdentity:
        """Get enclave identity and measurement"""
        pass
    
    @abstractmethod
    async def attest_enclave(self, enclave_id: str, nonce: Optional[str] = None) -> AttestationEvidence:
        """Generate attestation evidence for enclave"""
        pass
    
    @abstractmethod
    async def execute_in_enclave(
        self, 
        enclave_id: str, 
        request: SecureComputationRequest
    ) -> SecureComputationResult:
        """Execute computation inside enclave"""
        pass

class IntelSGXEnclave(TrustedExecutionEnvironment):
    """Intel SGX implementation of secure enclaves"""
    
    def __init__(self):
        self.enclaves: Dict[str, Dict[str, Any]] = {}
        self.attestation_keys = self._initialize_attestation_keys()
    
    def _initialize_attestation_keys(self) -> Dict[str, str]:
        """Initialize attestation keys (simulated)"""
        return {
            "signing_key": secrets.token_hex(32),
            "attestation_key": secrets.token_hex(32)
        }
    
    async def create_enclave(self, config: EnclaveConfiguration) -> str:
        """Create Intel SGX enclave"""
        enclave_id = f"sgx_{secrets.token_hex(8)}"
        
        # Simulate SGX enclave creation
        enclave_info = {
            "config": config,
            "state": EnclaveState.CREATED,
            "created_at": datetime.now(),
            "memory_allocated": config.memory_size * 1024 * 1024,  # Convert to bytes
            "threads_available": config.max_threads,
            "code_loaded": False,
            "attestation_count": 0,
            "sealed_data": {}
        }
        
        self.enclaves[enclave_id] = enclave_info
        return enclave_id
    
    async def load_enclave(self, enclave_id: str, code: bytes) -> bool:
        """Load code into SGX enclave"""
        if enclave_id not in self.enclaves:
            return False
        
        enclave = self.enclaves[enclave_id]
        
        # Simulate code measurement (MRENCLAVE)
        code_hash = hashlib.sha256(code).hexdigest()
        enclave["code_hash"] = code_hash
        enclave["code_size"] = len(code)
        enclave["code_loaded"] = True
        enclave["state"] = EnclaveState.LOADED
        
        return True
    
    async def get_enclave_identity(self, enclave_id: str) -> EnclaveIdentity:
        """Get SGX enclave identity"""
        if enclave_id not in self.enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave = self.enclaves[enclave_id]
        
        return EnclaveIdentity(
            enclave_id=enclave_id,
            measurement=enclave.get("code_hash", ""),
            signer=hashlib.sha256(self.attestation_keys["signing_key"].encode()).hexdigest(),
            product_id="activelog_enclave",
            security_version=1,
            attributes={
                "debug": enclave["config"].debug_enabled,
                "mode64bit": True,
                "provisionkey": True,
                "einittokenkey": True
            }
        )
    
    async def attest_enclave(self, enclave_id: str, nonce: Optional[str] = None) -> AttestationEvidence:
        """Generate SGX attestation evidence"""
        if enclave_id not in self.enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave = self.enclaves[enclave_id]
        identity = await self.get_enclave_identity(enclave_id)
        
        # Create attestation data
        attestation_data = {
            "enclave_identity": {
                "enclave_id": identity.enclave_id,
                "measurement": identity.measurement,
                "signer": identity.signer,
                "product_id": identity.product_id,
                "security_version": identity.security_version
            },
            "nonce": nonce or secrets.token_hex(16),
            "timestamp": datetime.now().isoformat()
        }
        
        # Sign attestation data
        attestation_json = json.dumps(attestation_data, sort_keys=True)
        signature = hmac.new(
            self.attestation_keys["attestation_key"].encode(),
            attestation_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Simulate certificate chain
        certificate_chain = [
            base64.b64encode(f"root_cert_{secrets.token_hex(16)}".encode()).decode(),
            base64.b64encode(f"intermediate_cert_{secrets.token_hex(16)}".encode()).decode(),
            base64.b64encode(f"leaf_cert_{secrets.token_hex(16)}".encode()).decode()
        ]
        
        enclave["attestation_count"] += 1
        
        return AttestationEvidence(
            enclave_identity=identity,
            attestation_type=enclave["config"].attestation_type,
            signature=signature,
            certificate_chain=certificate_chain,
            timestamp=datetime.now(),
            nonce=nonce
        )
    
    async def execute_in_enclave(
        self, 
        enclave_id: str, 
        request: SecureComputationRequest
    ) -> SecureComputationResult:
        """Execute computation inside SGX enclave"""
        if enclave_id not in self.enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave = self.enclaves[enclave_id]
        
        if not enclave["code_loaded"]:
            raise RuntimeError("No code loaded in enclave")
        
        start_time = datetime.now()
        
        # Simulate secure computation
        # In real implementation, this would execute inside the enclave
        computation_result = self._simulate_secure_computation(request)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Generate attestation if required
        attestation_evidence = None
        if request.attestation_required:
            attestation_evidence = await self.attest_enclave(enclave_id)
        
        enclave["state"] = EnclaveState.RUNNING
        
        return SecureComputationResult(
            computation_id=request.computation_id,
            encrypted_output=computation_result,
            output_hash=hashlib.sha256(computation_result).hexdigest(),
            attestation_evidence=attestation_evidence,
            execution_time=execution_time,
            memory_used=len(computation_result)
        )
    
    def _simulate_secure_computation(self, request: SecureComputationRequest) -> bytes:
        """Simulate secure computation (placeholder)"""
        # In real implementation, this would be actual computation inside enclave
        if request.function_name == "sum":
            # Simulate encrypted addition
            result_data = f"result_sum_{request.computation_id}_{secrets.token_hex(8)}"
        elif request.function_name == "analyze":
            # Simulate data analysis
            result_data = f"analysis_result_{request.computation_id}_{secrets.token_hex(16)}"
        else:
            # Generic computation
            result_data = f"computation_result_{request.computation_id}_{secrets.token_hex(12)}"
        
        return result_data.encode()
    
    async def seal_data(self, enclave_id: str, data: bytes, policy: str = "MRENCLAVE") -> SealedData:
        """Seal data for persistent storage"""
        if enclave_id not in self.enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave = self.enclaves[enclave_id]
        identity = await self.get_enclave_identity(enclave_id)
        
        # Create sealing key based on policy
        if policy == "MRENCLAVE":
            sealing_key = identity.measurement
        elif policy == "MRSIGNER":
            sealing_key = identity.signer
        else:
            sealing_key = "default_key"
        
        # Encrypt data (simplified)
        sealed_key = hashlib.sha256(f"{sealing_key}_{secrets.token_hex(16)}".encode()).digest()
        
        # Simple XOR encryption for simulation
        sealed_blob = bytes(a ^ b for a, b in zip(data, (sealed_key * (len(data) // len(sealed_key) + 1))[:len(data)]))
        
        sealed_data = SealedData(
            sealed_blob=sealed_blob,
            additional_data=b"sealed_metadata",
            policy=policy,
            security_version=identity.security_version
        )
        
        # Store sealed data
        sealed_id = f"sealed_{secrets.token_hex(8)}"
        enclave["sealed_data"][sealed_id] = sealed_data
        
        return sealed_data
    
    async def unseal_data(self, enclave_id: str, sealed_data: SealedData) -> bytes:
        """Unseal previously sealed data"""
        if enclave_id not in self.enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        identity = await self.get_enclave_identity(enclave_id)
        
        # Recreate sealing key
        if sealed_data.policy == "MRENCLAVE":
            sealing_key = identity.measurement
        elif sealed_data.policy == "MRSIGNER":
            sealing_key = identity.signer
        else:
            sealing_key = "default_key"
        
        unsealing_key = hashlib.sha256(f"{sealing_key}_{secrets.token_hex(16)}".encode()).digest()
        
        # Decrypt data (reverse XOR)
        unsealed_data = bytes(
            a ^ b for a, b in zip(
                sealed_data.sealed_blob, 
                (unsealing_key * (len(sealed_data.sealed_blob) // len(unsealing_key) + 1))[:len(sealed_data.sealed_blob)]
            )
        )
        
        return unsealed_data

class SecureEnclaveManager:
    """Manager for secure enclaves across different TEE implementations"""
    
    def __init__(self):
        self.tee_implementations: Dict[EnclaveType, TrustedExecutionEnvironment] = {
            EnclaveType.INTEL_SGX: IntelSGXEnclave(),
            EnclaveType.SOFTWARE_SIMULATION: IntelSGXEnclave()  # Use SGX impl for simulation
        }
        self.active_enclaves: Dict[str, str] = {}  # enclave_id -> enclave_type
        self.enclave_metrics: Dict[str, EnclaveMetrics] = {}
    
    async def create_enclave(self, config: EnclaveConfiguration) -> str:
        """Create enclave using appropriate TEE implementation"""
        if config.enclave_type not in self.tee_implementations:
            raise ValueError(f"Unsupported enclave type: {config.enclave_type}")
        
        tee = self.tee_implementations[config.enclave_type]
        enclave_id = await tee.create_enclave(config)
        
        self.active_enclaves[enclave_id] = config.enclave_type.value
        self.enclave_metrics[enclave_id] = EnclaveMetrics(
            cpu_usage=0.0,
            memory_usage=0,
            attestation_count=0,
            seal_operations=0,
            unseal_operations=0,
            exceptions_raised=0,
            uptime=timedelta(0)
        )
        
        return enclave_id
    
    async def load_secure_application(self, enclave_id: str, application_code: bytes) -> bool:
        """Load application into enclave"""
        if enclave_id not in self.active_enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave_type = EnclaveType(self.active_enclaves[enclave_id])
        tee = self.tee_implementations[enclave_type]
        
        return await tee.load_enclave(enclave_id, application_code)
    
    async def execute_secure_computation(
        self, 
        enclave_id: str, 
        function_name: str,
        encrypted_input: bytes,
        requester_id: str,
        require_attestation: bool = True
    ) -> SecureComputationResult:
        """Execute computation securely in enclave"""
        if enclave_id not in self.active_enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave_type = EnclaveType(self.active_enclaves[enclave_id])
        tee = self.tee_implementations[enclave_type]
        
        request = SecureComputationRequest(
            computation_id=f"comp_{secrets.token_hex(8)}",
            function_name=function_name,
            encrypted_input=encrypted_input,
            input_hash=hashlib.sha256(encrypted_input).hexdigest(),
            requester_id=requester_id,
            attestation_required=require_attestation
        )
        
        result = await tee.execute_in_enclave(enclave_id, request)
        
        # Update metrics
        metrics = self.enclave_metrics[enclave_id]
        metrics.memory_usage += result.memory_used
        if result.attestation_evidence:
            metrics.attestation_count += 1
        
        return result
    
    async def get_enclave_attestation(self, enclave_id: str, nonce: Optional[str] = None) -> AttestationEvidence:
        """Get attestation evidence for enclave"""
        if enclave_id not in self.active_enclaves:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        enclave_type = EnclaveType(self.active_enclaves[enclave_id])
        tee = self.tee_implementations[enclave_type]
        
        return await tee.attest_enclave(enclave_id, nonce)
    
    async def verify_attestation(self, evidence: AttestationEvidence, expected_measurement: str) -> bool:
        """Verify attestation evidence"""
        # Check if measurement matches expected value
        if evidence.enclave_identity.measurement != expected_measurement:
            return False
        
        # Check if attestation is recent (within last hour)
        if datetime.now() - evidence.timestamp > timedelta(hours=1):
            return False
        
        # In production, would verify signature against certificate chain
        # and check certificate chain validity
        
        return True
    
    async def get_enclave_metrics(self, enclave_id: str) -> EnclaveMetrics:
        """Get performance metrics for enclave"""
        if enclave_id not in self.enclave_metrics:
            raise ValueError(f"Enclave {enclave_id} not found")
        
        return self.enclave_metrics[enclave_id]
    
    async def terminate_enclave(self, enclave_id: str) -> bool:
        """Terminate enclave and cleanup resources"""
        if enclave_id not in self.active_enclaves:
            return False
        
        # Cleanup
        del self.active_enclaves[enclave_id]
        del self.enclave_metrics[enclave_id]
        
        return True

def create_secure_enclave_manager() -> SecureEnclaveManager:
    """Factory function to create secure enclave manager"""
    return SecureEnclaveManager()

# Example usage
async def example_usage():
    """Example of using secure enclaves"""
    
    # Create enclave manager
    enclave_manager = create_secure_enclave_manager()
    
    # Configure enclave
    config = EnclaveConfiguration(
        enclave_type=EnclaveType.INTEL_SGX,
        security_level=SecurityLevel.PRODUCTION,
        memory_size=64,  # 64 MB
        max_threads=4,
        attestation_type=AttestationType.REMOTE,
        debug_enabled=False,
        sealed_storage_enabled=True,
        remote_attestation_endpoint="https://attestation.intel.com"
    )
    
    # Create enclave
    enclave_id = await enclave_manager.create_enclave(config)
    print(f"Created enclave: {enclave_id}")
    
    # Load application code
    application_code = b"secure_computation_app_v1.0"
    loaded = await enclave_manager.load_secure_application(enclave_id, application_code)
    print(f"Application loaded: {loaded}")
    
    # Execute secure computation
    encrypted_input = b"sensitive_data_to_process"
    result = await enclave_manager.execute_secure_computation(
        enclave_id=enclave_id,
        function_name="analyze",
        encrypted_input=encrypted_input,
        requester_id="user123",
        require_attestation=True
    )
    
    print(f"Computation completed:")
    print(f"  Computation ID: {result.computation_id}")
    print(f"  Output hash: {result.output_hash}")
    print(f"  Execution time: {result.execution_time:.3f}s")
    print(f"  Memory used: {result.memory_used} bytes")
    
    # Verify attestation
    if result.attestation_evidence:
        expected_measurement = hashlib.sha256(application_code).hexdigest()
        is_valid = await enclave_manager.verify_attestation(
            result.attestation_evidence, 
            expected_measurement
        )
        print(f"Attestation valid: {is_valid}")
    
    # Get enclave metrics
    metrics = await enclave_manager.get_enclave_metrics(enclave_id)
    print(f"Enclave metrics:")
    print(f"  Memory usage: {metrics.memory_usage} bytes")
    print(f"  Attestations: {metrics.attestation_count}")
    
    # Cleanup
    await enclave_manager.terminate_enclave(enclave_id)
    print("Enclave terminated")

if __name__ == "__main__":
    asyncio.run(example_usage())