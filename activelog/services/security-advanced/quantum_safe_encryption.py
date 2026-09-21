"""
Quantum-Safe Encryption Migration
Transition to post-quantum cryptographic algorithms resistant to quantum computer attacks
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from enum import Enum
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
import json
import base64
from abc import ABC, abstractmethod
import numpy as np

class QuantumSafeAlgorithm(Enum):
    # NIST Post-Quantum Cryptography Standardized Algorithms
    CRYSTALS_KYBER = "crystals_kyber"  # Key encapsulation
    CRYSTALS_DILITHIUM = "crystals_dilithium"  # Digital signatures
    FALCON = "falcon"  # Digital signatures
    SPHINCS_PLUS = "sphincs_plus"  # Digital signatures
    
    # Lattice-based
    NTRU = "ntru"
    FRODO_KEM = "frodo_kem"
    
    # Code-based
    CLASSIC_MCELIECE = "classic_mceliece"
    HQC = "hqc"
    
    # Multivariate
    RAINBOW = "rainbow"
    
    # Hash-based
    XMSS = "xmss"
    LMS = "lms"

class CryptoFunction(Enum):
    KEY_ENCAPSULATION = "key_encapsulation"
    DIGITAL_SIGNATURE = "digital_signature"
    PUBLIC_KEY_ENCRYPTION = "public_key_encryption"
    SYMMETRIC_ENCRYPTION = "symmetric_encryption"
    HASH_FUNCTION = "hash_function"

class MigrationStatus(Enum):
    NOT_STARTED = "not_started"
    ASSESSMENT = "assessment"
    PLANNING = "planning"
    TESTING = "testing"
    HYBRID_DEPLOYMENT = "hybrid_deployment"
    FULL_MIGRATION = "full_migration"
    COMPLETED = "completed"

class SecurityLevel(Enum):
    LEVEL_1 = "level_1"  # 128-bit security
    LEVEL_3 = "level_3"  # 192-bit security  
    LEVEL_5 = "level_5"  # 256-bit security

@dataclass
class CryptoAlgorithmSpec:
    """Specification for a cryptographic algorithm"""
    algorithm: QuantumSafeAlgorithm
    function: CryptoFunction
    security_level: SecurityLevel
    key_size: int
    signature_size: Optional[int]
    ciphertext_overhead: int
    performance_tier: str  # "fast", "medium", "slow"
    standardized: bool
    quantum_safe: bool

@dataclass
class CryptoAsset:
    """Cryptographic asset requiring migration"""
    asset_id: str
    asset_type: str  # "certificate", "key", "signature", "encrypted_data"
    current_algorithm: str
    location: str
    usage: str
    criticality: str  # "low", "medium", "high", "critical"
    dependencies: List[str]
    last_updated: datetime

@dataclass
class MigrationPlan:
    """Migration plan for cryptographic transition"""
    plan_id: str
    target_algorithms: Dict[CryptoFunction, QuantumSafeAlgorithm]
    migration_phases: List[Dict[str, Any]]
    timeline: Dict[str, datetime]
    risk_assessment: Dict[str, Any]
    rollback_procedures: List[str]
    testing_requirements: List[str]

@dataclass
class HybridKeyPair:
    """Hybrid key pair combining classical and quantum-safe algorithms"""
    key_id: str
    classical_public_key: bytes
    classical_private_key: bytes
    quantum_safe_public_key: bytes
    quantum_safe_private_key: bytes
    classical_algorithm: str
    quantum_safe_algorithm: QuantumSafeAlgorithm
    created_at: datetime
    expires_at: datetime

@dataclass
class QuantumThreatAssessment:
    """Assessment of quantum computing threat to current cryptography"""
    assessment_id: str
    assessed_at: datetime
    estimated_quantum_timeline: int  # Years until cryptographically relevant quantum computer
    current_vulnerabilities: List[str]
    priority_assets: List[str]
    recommended_timeline: Dict[str, datetime]
    risk_score: float

class PostQuantumAlgorithm(ABC):
    """Abstract base for post-quantum cryptographic algorithms"""
    
    @abstractmethod
    async def generate_keypair(self, security_level: SecurityLevel) -> Tuple[bytes, bytes]:
        """Generate public/private key pair"""
        pass
    
    @abstractmethod
    async def encrypt(self, public_key: bytes, plaintext: bytes) -> bytes:
        """Encrypt data with public key"""
        pass
    
    @abstractmethod
    async def decrypt(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Decrypt data with private key"""
        pass
    
    @abstractmethod
    async def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign message with private key"""
        pass
    
    @abstractmethod
    async def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify signature with public key"""
        pass

class CrystalsKyberKEM:
    """CRYSTALS-KYBER Key Encapsulation Mechanism (simplified implementation)"""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.LEVEL_3):
        self.security_level = security_level
        self.params = self._get_parameters(security_level)
    
    def _get_parameters(self, level: SecurityLevel) -> Dict[str, int]:
        """Get algorithm parameters based on security level"""
        if level == SecurityLevel.LEVEL_1:
            return {"k": 2, "eta1": 3, "eta2": 2, "du": 10, "dv": 4}
        elif level == SecurityLevel.LEVEL_3:
            return {"k": 3, "eta1": 2, "eta2": 2, "du": 10, "dv": 4}
        else:  # LEVEL_5
            return {"k": 4, "eta1": 2, "eta2": 2, "du": 11, "dv": 5}
    
    async def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate Kyber keypair (simplified)"""
        # In real implementation, this would use lattice-based cryptography
        # Here we simulate with secure random generation
        
        private_key_size = 32 * self.params["k"]
        public_key_size = 32 * self.params["k"] + 32
        
        private_key = secrets.token_bytes(private_key_size)
        public_key = secrets.token_bytes(public_key_size)
        
        return public_key, private_key
    
    async def encapsulate(self, public_key: bytes) -> Tuple[bytes, bytes]:
        """Encapsulate shared secret (KEM)"""
        # Generate shared secret
        shared_secret = secrets.token_bytes(32)
        
        # Encapsulate (in real implementation, this uses lattice operations)
        ciphertext_size = 32 * self.params["k"] + 32
        ciphertext = secrets.token_bytes(ciphertext_size)
        
        return ciphertext, shared_secret
    
    async def decapsulate(self, private_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate shared secret"""
        # In real implementation, this would recover the shared secret
        # For simulation, return a deterministic value based on inputs
        combined = private_key[:16] + ciphertext[:16]
        shared_secret = hashlib.sha256(combined).digest()
        return shared_secret

class CrystalsDilithiumSignature:
    """CRYSTALS-DILITHIUM Digital Signature (simplified implementation)"""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.LEVEL_3):
        self.security_level = security_level
        self.params = self._get_parameters(security_level)
    
    def _get_parameters(self, level: SecurityLevel) -> Dict[str, int]:
        """Get algorithm parameters based on security level"""
        if level == SecurityLevel.LEVEL_1:
            return {"k": 4, "l": 4, "eta": 2, "tau": 39, "gamma1": 17, "gamma2": 88}
        elif level == SecurityLevel.LEVEL_3:
            return {"k": 6, "l": 5, "eta": 4, "tau": 49, "gamma1": 19, "gamma2": 95}
        else:  # LEVEL_5
            return {"k": 8, "l": 7, "eta": 2, "tau": 60, "gamma1": 19, "gamma2": 95}
    
    async def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate Dilithium keypair"""
        private_key_size = 32 + 32 + 32 * (self.params["k"] + self.params["l"])
        public_key_size = 32 + 32 * self.params["k"]
        
        private_key = secrets.token_bytes(private_key_size)
        public_key = secrets.token_bytes(public_key_size)
        
        return public_key, private_key
    
    async def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign message with Dilithium"""
        # Hash message
        message_hash = hashlib.sha3_256(message).digest()
        
        # Generate signature (simplified)
        signature_size = 64 + 32 * (self.params["l"] + self.params["k"])
        signature = secrets.token_bytes(signature_size)
        
        # Include message hash in signature for verification
        signature_with_hash = message_hash + signature
        
        return signature_with_hash
    
    async def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify Dilithium signature"""
        if len(signature) < 32:
            return False
        
        # Extract message hash from signature
        stored_hash = signature[:32]
        actual_hash = hashlib.sha3_256(message).digest()
        
        # For simulation, verify hash matches
        return stored_hash == actual_hash

class FalconSignature:
    """FALCON Digital Signature (simplified implementation)"""
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.LEVEL_1):
        self.security_level = security_level
        self.n = 512 if security_level == SecurityLevel.LEVEL_1 else 1024
    
    async def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate FALCON keypair"""
        private_key_size = self.n // 4  # Simplified size
        public_key_size = self.n // 8
        
        private_key = secrets.token_bytes(private_key_size)
        public_key = secrets.token_bytes(public_key_size)
        
        return public_key, private_key
    
    async def sign(self, private_key: bytes, message: bytes) -> bytes:
        """Sign with FALCON"""
        # FALCON produces compact signatures
        signature_size = self.n // 8 + 40  # Approximate size
        
        message_hash = hashlib.sha3_256(message).digest()
        signature = message_hash + secrets.token_bytes(signature_size - 32)
        
        return signature
    
    async def verify(self, public_key: bytes, message: bytes, signature: bytes) -> bool:
        """Verify FALCON signature"""
        if len(signature) < 32:
            return False
        
        stored_hash = signature[:32]
        actual_hash = hashlib.sha3_256(message).digest()
        
        return stored_hash == actual_hash

class QuantumSafeCryptoSystem:
    """Main system for managing quantum-safe cryptography migration"""
    
    def __init__(self):
        self.supported_algorithms: Dict[QuantumSafeAlgorithm, CryptoAlgorithmSpec] = {
            QuantumSafeAlgorithm.CRYSTALS_KYBER: CryptoAlgorithmSpec(
                algorithm=QuantumSafeAlgorithm.CRYSTALS_KYBER,
                function=CryptoFunction.KEY_ENCAPSULATION,
                security_level=SecurityLevel.LEVEL_3,
                key_size=1568,
                signature_size=None,
                ciphertext_overhead=1088,
                performance_tier="fast",
                standardized=True,
                quantum_safe=True
            ),
            QuantumSafeAlgorithm.CRYSTALS_DILITHIUM: CryptoAlgorithmSpec(
                algorithm=QuantumSafeAlgorithm.CRYSTALS_DILITHIUM,
                function=CryptoFunction.DIGITAL_SIGNATURE,
                security_level=SecurityLevel.LEVEL_3,
                key_size=1952,
                signature_size=3293,
                ciphertext_overhead=0,
                performance_tier="fast",
                standardized=True,
                quantum_safe=True
            ),
            QuantumSafeAlgorithm.FALCON: CryptoAlgorithmSpec(
                algorithm=QuantumSafeAlgorithm.FALCON,
                function=CryptoFunction.DIGITAL_SIGNATURE,
                security_level=SecurityLevel.LEVEL_1,
                key_size=897,
                signature_size=690,
                ciphertext_overhead=0,
                performance_tier="medium",
                standardized=True,
                quantum_safe=True
            )
        }
        
        self.algorithm_implementations = {
            QuantumSafeAlgorithm.CRYSTALS_KYBER: CrystalsKyberKEM(),
            QuantumSafeAlgorithm.CRYSTALS_DILITHIUM: CrystalsDilithiumSignature(),
            QuantumSafeAlgorithm.FALCON: FalconSignature()
        }
        
        self.crypto_assets: Dict[str, CryptoAsset] = {}
        self.hybrid_keys: Dict[str, HybridKeyPair] = {}
        self.migration_plans: Dict[str, MigrationPlan] = {}
        self.threat_assessments: List[QuantumThreatAssessment] = []
    
    async def assess_quantum_threat(self) -> QuantumThreatAssessment:
        """Assess current quantum computing threat landscape"""
        # Current expert estimates for cryptographically relevant quantum computers
        estimated_timeline = 15  # Years (conservative estimate)
        
        # Identify vulnerable algorithms currently in use
        vulnerabilities = []
        classical_algorithms = ["RSA", "ECDSA", "ECDH", "DH"]
        
        for asset in self.crypto_assets.values():
            if any(alg in asset.current_algorithm.upper() for alg in classical_algorithms):
                vulnerabilities.append(f"{asset.asset_id}: {asset.current_algorithm}")
        
        # Prioritize critical assets
        priority_assets = [
            asset.asset_id for asset in self.crypto_assets.values() 
            if asset.criticality in ["high", "critical"]
        ]
        
        # Calculate risk score
        risk_score = min(1.0, len(vulnerabilities) / max(1, len(self.crypto_assets)) * 
                        (20 / max(1, estimated_timeline)))  # Higher risk if timeline is shorter
        
        # Recommend migration timeline
        recommended_timeline = {
            "start_assessment": datetime.now(),
            "begin_testing": datetime.now() + timedelta(days=90),
            "start_migration": datetime.now() + timedelta(days=180),
            "complete_critical": datetime.now() + timedelta(days=365),
            "complete_all": datetime.now() + timedelta(days=730)
        }
        
        assessment = QuantumThreatAssessment(
            assessment_id=f"qta_{secrets.token_hex(8)}",
            assessed_at=datetime.now(),
            estimated_quantum_timeline=estimated_timeline,
            current_vulnerabilities=vulnerabilities[:10],  # Limit to top 10
            priority_assets=priority_assets,
            recommended_timeline=recommended_timeline,
            risk_score=risk_score
        )
        
        self.threat_assessments.append(assessment)
        return assessment
    
    async def create_migration_plan(
        self,
        target_functions: Dict[CryptoFunction, QuantumSafeAlgorithm]
    ) -> MigrationPlan:
        """Create comprehensive migration plan"""
        plan_id = f"plan_{secrets.token_hex(8)}"
        
        # Define migration phases
        phases = [
            {
                "phase": "assessment",
                "duration_days": 30,
                "activities": ["inventory_crypto_assets", "threat_assessment", "algorithm_selection"],
                "deliverables": ["asset_inventory", "risk_assessment", "algorithm_recommendations"]
            },
            {
                "phase": "testing",
                "duration_days": 90,
                "activities": ["algorithm_testing", "performance_benchmarking", "integration_testing"],
                "deliverables": ["test_results", "performance_metrics", "integration_guide"]
            },
            {
                "phase": "hybrid_deployment",
                "duration_days": 180,
                "activities": ["deploy_hybrid_systems", "dual_mode_operation", "monitoring_setup"],
                "deliverables": ["hybrid_infrastructure", "monitoring_dashboard", "operational_procedures"]
            },
            {
                "phase": "full_migration",
                "duration_days": 365,
                "activities": ["migrate_critical_systems", "update_all_certificates", "legacy_cleanup"],
                "deliverables": ["migrated_systems", "new_certificates", "cleanup_report"]
            }
        ]
        
        # Calculate timeline
        start_date = datetime.now()
        timeline = {"start": start_date}
        current_date = start_date
        
        for phase in phases:
            phase_end = current_date + timedelta(days=phase["duration_days"])
            timeline[phase["phase"]] = phase_end
            current_date = phase_end
        
        # Risk assessment
        risk_assessment = {
            "compatibility_risks": ["legacy_system_integration", "third_party_dependencies"],
            "performance_risks": ["increased_key_sizes", "signature_verification_overhead"],
            "operational_risks": ["staff_training_required", "new_key_management_procedures"],
            "mitigation_strategies": ["hybrid_deployment", "phased_rollout", "comprehensive_testing"]
        }
        
        # Rollback procedures
        rollback_procedures = [
            "maintain_classical_keys_during_transition",
            "implement_dual_mode_signatures",
            "establish_rapid_rollback_triggers",
            "document_rollback_procedures_for_each_phase"
        ]
        
        # Testing requirements
        testing_requirements = [
            "algorithm_correctness_testing",
            "performance_benchmarking",
            "interoperability_testing",
            "security_penetration_testing",
            "stress_testing_under_load"
        ]
        
        plan = MigrationPlan(
            plan_id=plan_id,
            target_algorithms=target_functions,
            migration_phases=phases,
            timeline=timeline,
            risk_assessment=risk_assessment,
            rollback_procedures=rollback_procedures,
            testing_requirements=testing_requirements
        )
        
        self.migration_plans[plan_id] = plan
        return plan
    
    async def generate_hybrid_keypair(
        self,
        classical_algorithm: str,
        quantum_safe_algorithm: QuantumSafeAlgorithm,
        validity_period: timedelta = timedelta(days=365)
    ) -> HybridKeyPair:
        """Generate hybrid key pair for transition period"""
        # Generate classical keypair (simulated)
        classical_private = secrets.token_bytes(32)
        classical_public = hashlib.sha256(classical_private).digest()
        
        # Generate quantum-safe keypair
        if quantum_safe_algorithm in self.algorithm_implementations:
            impl = self.algorithm_implementations[quantum_safe_algorithm]
            if hasattr(impl, 'generate_keypair'):
                qs_public, qs_private = await impl.generate_keypair()
            else:
                # Fallback for KEM
                qs_public, qs_private = await impl.generate_keypair()
        else:
            # Default quantum-safe keys
            qs_private = secrets.token_bytes(64)
            qs_public = hashlib.sha256(qs_private).digest()
        
        hybrid_key = HybridKeyPair(
            key_id=f"hybrid_{secrets.token_hex(8)}",
            classical_public_key=classical_public,
            classical_private_key=classical_private,
            quantum_safe_public_key=qs_public,
            quantum_safe_private_key=qs_private,
            classical_algorithm=classical_algorithm,
            quantum_safe_algorithm=quantum_safe_algorithm,
            created_at=datetime.now(),
            expires_at=datetime.now() + validity_period
        )
        
        self.hybrid_keys[hybrid_key.key_id] = hybrid_key
        return hybrid_key
    
    async def hybrid_sign(
        self,
        key_id: str,
        message: bytes,
        use_both: bool = True
    ) -> Dict[str, bytes]:
        """Sign message using hybrid approach"""
        if key_id not in self.hybrid_keys:
            raise ValueError(f"Hybrid key {key_id} not found")
        
        hybrid_key = self.hybrid_keys[key_id]
        signatures = {}
        
        if use_both:
            # Classical signature (simulated)
            classical_sig = hashlib.sha256(
                message + hybrid_key.classical_private_key
            ).digest()
            signatures["classical"] = classical_sig
            
            # Quantum-safe signature
            if hybrid_key.quantum_safe_algorithm in self.algorithm_implementations:
                impl = self.algorithm_implementations[hybrid_key.quantum_safe_algorithm]
                if hasattr(impl, 'sign'):
                    qs_sig = await impl.sign(hybrid_key.quantum_safe_private_key, message)
                    signatures["quantum_safe"] = qs_sig
        
        return signatures
    
    async def hybrid_verify(
        self,
        key_id: str,
        message: bytes,
        signatures: Dict[str, bytes],
        require_both: bool = False
    ) -> bool:
        """Verify hybrid signatures"""
        if key_id not in self.hybrid_keys:
            return False
        
        hybrid_key = self.hybrid_keys[key_id]
        results = {}
        
        # Verify classical signature
        if "classical" in signatures:
            expected_sig = hashlib.sha256(
                message + hybrid_key.classical_private_key
            ).digest()
            results["classical"] = signatures["classical"] == expected_sig
        
        # Verify quantum-safe signature
        if "quantum_safe" in signatures:
            if hybrid_key.quantum_safe_algorithm in self.algorithm_implementations:
                impl = self.algorithm_implementations[hybrid_key.quantum_safe_algorithm]
                if hasattr(impl, 'verify'):
                    qs_valid = await impl.verify(
                        hybrid_key.quantum_safe_public_key,
                        message,
                        signatures["quantum_safe"]
                    )
                    results["quantum_safe"] = qs_valid
        
        # Determine overall validity
        if require_both:
            return all(results.values()) if results else False
        else:
            return any(results.values()) if results else False
    
    async def register_crypto_asset(
        self,
        asset_type: str,
        current_algorithm: str,
        location: str,
        usage: str,
        criticality: str,
        dependencies: Optional[List[str]] = None
    ) -> CryptoAsset:
        """Register cryptographic asset for migration tracking"""
        asset = CryptoAsset(
            asset_id=f"asset_{secrets.token_hex(8)}",
            asset_type=asset_type,
            current_algorithm=current_algorithm,
            location=location,
            usage=usage,
            criticality=criticality,
            dependencies=dependencies or [],
            last_updated=datetime.now()
        )
        
        self.crypto_assets[asset.asset_id] = asset
        return asset
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get overall migration status and metrics"""
        total_assets = len(self.crypto_assets)
        quantum_vulnerable = len([
            asset for asset in self.crypto_assets.values()
            if any(alg in asset.current_algorithm.upper() for alg in ["RSA", "ECDSA", "ECDH", "DH"])
        ])
        
        critical_assets = len([
            asset for asset in self.crypto_assets.values()
            if asset.criticality in ["high", "critical"]
        ])
        
        hybrid_keys_count = len(self.hybrid_keys)
        active_plans = len(self.migration_plans)
        
        latest_assessment = self.threat_assessments[-1] if self.threat_assessments else None
        
        return {
            "total_crypto_assets": total_assets,
            "quantum_vulnerable_assets": quantum_vulnerable,
            "critical_assets": critical_assets,
            "vulnerability_percentage": quantum_vulnerable / total_assets if total_assets > 0 else 0,
            "hybrid_keys_deployed": hybrid_keys_count,
            "active_migration_plans": active_plans,
            "supported_algorithms": len(self.supported_algorithms),
            "latest_threat_assessment": {
                "assessment_id": latest_assessment.assessment_id,
                "risk_score": latest_assessment.risk_score,
                "estimated_timeline": latest_assessment.estimated_quantum_timeline
            } if latest_assessment else None,
            "recommended_algorithms": {
                "key_encapsulation": "CRYSTALS-KYBER",
                "digital_signatures": "CRYSTALS-DILITHIUM or FALCON",
                "hash_functions": "SHA-3 family"
            }
        }

def create_quantum_safe_crypto_system() -> QuantumSafeCryptoSystem:
    """Factory function to create quantum-safe cryptography system"""
    return QuantumSafeCryptoSystem()

# Example usage
async def example_usage():
    """Example of using quantum-safe encryption migration"""
    
    # Create quantum-safe crypto system
    qsc_system = create_quantum_safe_crypto_system()
    
    # Register some crypto assets
    cert_asset = await qsc_system.register_crypto_asset(
        asset_type="certificate",
        current_algorithm="RSA-2048",
        location="web_server",
        usage="TLS_certificate",
        criticality="high",
        dependencies=["load_balancer", "application_servers"]
    )
    
    key_asset = await qsc_system.register_crypto_asset(
        asset_type="signing_key",
        current_algorithm="ECDSA-P256",
        location="application_server",
        usage="document_signing",
        criticality="critical"
    )
    
    print(f"Registered crypto assets:")
    print(f"  Certificate: {cert_asset.asset_id} (RSA-2048)")
    print(f"  Signing Key: {key_asset.asset_id} (ECDSA-P256)")
    
    # Perform quantum threat assessment
    assessment = await qsc_system.assess_quantum_threat()
    print(f"\nQuantum Threat Assessment:")
    print(f"  Assessment ID: {assessment.assessment_id}")
    print(f"  Risk Score: {assessment.risk_score:.3f}")
    print(f"  Estimated Timeline: {assessment.estimated_quantum_timeline} years")
    print(f"  Vulnerabilities Found: {len(assessment.current_vulnerabilities)}")
    print(f"  Priority Assets: {len(assessment.priority_assets)}")
    
    # Create migration plan
    target_algorithms = {
        CryptoFunction.KEY_ENCAPSULATION: QuantumSafeAlgorithm.CRYSTALS_KYBER,
        CryptoFunction.DIGITAL_SIGNATURE: QuantumSafeAlgorithm.CRYSTALS_DILITHIUM
    }
    
    migration_plan = await qsc_system.create_migration_plan(target_algorithms)
    print(f"\nMigration Plan:")
    print(f"  Plan ID: {migration_plan.plan_id}")
    print(f"  Phases: {len(migration_plan.migration_phases)}")
    print(f"  Target Completion: {migration_plan.timeline['complete_all'].strftime('%Y-%m-%d')}")
    
    # Generate hybrid keypair for transition
    hybrid_key = await qsc_system.generate_hybrid_keypair(
        classical_algorithm="ECDSA-P256",
        quantum_safe_algorithm=QuantumSafeAlgorithm.CRYSTALS_DILITHIUM,
        validity_period=timedelta(days=365)
    )
    
    print(f"\nGenerated Hybrid Key:")
    print(f"  Key ID: {hybrid_key.key_id}")
    print(f"  Classical: {hybrid_key.classical_algorithm}")
    print(f"  Quantum-Safe: {hybrid_key.quantum_safe_algorithm.value}")
    print(f"  Expires: {hybrid_key.expires_at.strftime('%Y-%m-%d')}")
    
    # Test hybrid signing
    test_message = b"This is a test document that needs to be signed securely."
    
    signatures = await qsc_system.hybrid_sign(
        key_id=hybrid_key.key_id,
        message=test_message,
        use_both=True
    )
    
    print(f"\nHybrid Signing:")
    print(f"  Message: {test_message.decode()}")
    print(f"  Signatures generated: {list(signatures.keys())}")
    
    # Verify signatures
    is_valid = await qsc_system.hybrid_verify(
        key_id=hybrid_key.key_id,
        message=test_message,
        signatures=signatures,
        require_both=False  # Accept if either signature is valid
    )
    
    print(f"  Verification result: {is_valid}")
    
    # Get migration status
    status = await qsc_system.get_migration_status()
    print(f"\nMigration Status:")
    for key, value in status.items():
        if key != "latest_threat_assessment" and key != "recommended_algorithms":
            print(f"  {key}: {value}")
    
    print(f"\nRecommended Algorithms:")
    for function, algorithm in status["recommended_algorithms"].items():
        print(f"  {function}: {algorithm}")

if __name__ == "__main__":
    asyncio.run(example_usage())