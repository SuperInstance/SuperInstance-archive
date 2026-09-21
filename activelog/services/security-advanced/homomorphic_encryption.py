"""
Homomorphic Encryption for Computation on Encrypted Data
Advanced privacy-preserving computation system that allows operations on encrypted data without decryption
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import secrets
from abc import ABC, abstractmethod
import struct

logger = logging.getLogger(__name__)

class EncryptionScheme(Enum):
    """Types of homomorphic encryption schemes"""
    PARTIAL_HE = "partial_he"          # Supports either addition or multiplication
    SOMEWHAT_HE = "somewhat_he"        # Limited operations and noise
    LEVELED_FHE = "leveled_fhe"        # Full operations with circuit depth limit
    FULL_FHE = "full_fhe"              # Unlimited operations (theoretical)
    BGV = "bgv"                        # BGV scheme for packed operations
    BFV = "bfv"                        # BFV scheme for integer arithmetic
    CKKS = "ckks"                      # CKKS scheme for approximate arithmetic

class OperationType(Enum):
    """Types of operations supported"""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    COMPARE = "compare"
    EVALUATE_POLYNOMIAL = "evaluate_polynomial"
    MATRIX_MULTIPLY = "matrix_multiply"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    MACHINE_LEARNING = "machine_learning"

class NoiseLevel(Enum):
    """Noise levels in homomorphic encryption"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HomomorphicKey:
    """Homomorphic encryption key pair"""
    public_key: bytes
    private_key: bytes
    evaluation_key: Optional[bytes] = None
    relinearization_key: Optional[bytes] = None
    rotation_keys: Optional[Dict[int, bytes]] = None
    key_id: str = field(default_factory=lambda: secrets.token_hex(16))
    scheme: EncryptionScheme = EncryptionScheme.BFV
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class HomomorphicCiphertext:
    """Encrypted data that supports homomorphic operations"""
    ciphertext: bytes
    noise_level: NoiseLevel
    operation_depth: int
    data_type: str
    dimensions: Tuple[int, ...]
    scheme: EncryptionScheme
    key_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ComputationResult:
    """Result of homomorphic computation"""
    result_ciphertext: HomomorphicCiphertext
    operation_log: List[Dict[str, Any]]
    noise_growth: float
    computation_time: float
    accuracy_estimate: Optional[float] = None
    verification_data: Optional[Dict[str, Any]] = None

class HomomorphicEncryptionEngine(ABC):
    """Abstract base class for homomorphic encryption engines"""
    
    @abstractmethod
    async def generate_keys(self, parameters: Dict[str, Any]) -> HomomorphicKey:
        """Generate homomorphic encryption keys"""
        pass
    
    @abstractmethod
    async def encrypt(self, data: Union[int, float, List, np.ndarray], 
                     public_key: bytes) -> HomomorphicCiphertext:
        """Encrypt data homomorphically"""
        pass
    
    @abstractmethod
    async def decrypt(self, ciphertext: HomomorphicCiphertext, 
                     private_key: bytes) -> Union[int, float, List, np.ndarray]:
        """Decrypt homomorphic ciphertext"""
        pass
    
    @abstractmethod
    async def add_encrypted(self, ct1: HomomorphicCiphertext, 
                           ct2: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Add two encrypted values"""
        pass
    
    @abstractmethod
    async def multiply_encrypted(self, ct1: HomomorphicCiphertext, 
                               ct2: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Multiply two encrypted values"""
        pass

class BFVHomomorphicEngine(HomomorphicEncryptionEngine):
    """BFV (Brakerski-Fan-Vercauteren) homomorphic encryption implementation"""
    
    def __init__(self, security_level: int = 128):
        self.security_level = security_level
        self.default_parameters = self._get_default_parameters()
        
    def _get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for BFV scheme"""
        return {
            'polynomial_modulus_degree': 8192,
            'coefficient_modulus': [60, 40, 40, 60],
            'plain_modulus': 1024,
            'security_level': self.security_level,
            'noise_standard_deviation': 3.2
        }
    
    async def generate_keys(self, parameters: Optional[Dict[str, Any]] = None) -> HomomorphicKey:
        """Generate BFV homomorphic encryption keys"""
        params = {**self.default_parameters, **(parameters or {})}
        
        # Simulate key generation (in practice, would use libraries like SEAL or Palisade)
        key_seed = secrets.randbits(256)
        
        # Generate polynomial coefficients for keys
        poly_degree = params['polynomial_modulus_degree']
        
        # Secret key (random binary polynomial)
        secret_key = self._generate_secret_key(poly_degree, key_seed)
        
        # Public key generation
        public_key = self._generate_public_key(secret_key, params)
        
        # Evaluation keys for relinearization
        evaluation_key = self._generate_evaluation_key(secret_key, params)
        
        return HomomorphicKey(
            public_key=public_key,
            private_key=secret_key,
            evaluation_key=evaluation_key,
            scheme=EncryptionScheme.BFV,
            parameters=params
        )
    
    def _generate_secret_key(self, poly_degree: int, seed: int) -> bytes:
        """Generate secret key polynomial"""
        np.random.seed(seed)
        # Generate ternary polynomial {-1, 0, 1}
        secret_coeffs = np.random.choice([-1, 0, 1], size=poly_degree, p=[0.25, 0.5, 0.25])
        return secret_coeffs.astype(np.int32).tobytes()
    
    def _generate_public_key(self, secret_key: bytes, params: Dict[str, Any]) -> bytes:
        """Generate public key from secret key"""
        secret_poly = np.frombuffer(secret_key, dtype=np.int32)
        poly_degree = len(secret_poly)
        
        # Simulate public key generation
        # In practice: (a, b) where b = -a*s + e (mod q)
        a = np.random.randint(0, params['plain_modulus'], size=poly_degree)
        error = np.random.normal(0, params['noise_standard_deviation'], size=poly_degree)
        b = (-a * secret_poly + error.astype(np.int32)) % params['plain_modulus']
        
        public_key = np.column_stack([a, b]).flatten()
        return public_key.astype(np.int32).tobytes()
    
    def _generate_evaluation_key(self, secret_key: bytes, params: Dict[str, Any]) -> bytes:
        """Generate evaluation key for relinearization"""
        # Simplified evaluation key generation
        eval_key_data = hashlib.sha256(secret_key + b"eval").digest()
        return eval_key_data
    
    async def encrypt(self, data: Union[int, float, List, np.ndarray], 
                     public_key: bytes) -> HomomorphicCiphertext:
        """Encrypt data using BFV scheme"""
        # Convert input to appropriate format
        if isinstance(data, (int, float)):
            plaintext = np.array([int(data)])
        elif isinstance(data, list):
            plaintext = np.array(data, dtype=np.int32)
        elif isinstance(data, np.ndarray):
            plaintext = data.astype(np.int32)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Simulate encryption process
        public_poly = np.frombuffer(public_key, dtype=np.int32).reshape(-1, 2)
        poly_degree = len(public_poly)
        
        # Add random noise for security
        noise = np.random.normal(0, 3.2, size=plaintext.shape).astype(np.int32)
        
        # Simulate ciphertext generation
        ciphertext_data = self._encrypt_polynomial(plaintext, public_poly, noise)
        
        return HomomorphicCiphertext(
            ciphertext=ciphertext_data,
            noise_level=NoiseLevel.LOW,
            operation_depth=0,
            data_type=str(plaintext.dtype),
            dimensions=plaintext.shape,
            scheme=EncryptionScheme.BFV,
            key_id="default"  # Would use actual key ID
        )
    
    def _encrypt_polynomial(self, plaintext: np.ndarray, public_key: np.ndarray, 
                          noise: np.ndarray) -> bytes:
        """Encrypt plaintext polynomial"""
        # Simplified encryption: ct = (pk[0] * u + e0, pk[1] * u + e1 + m)
        u = np.random.randint(0, 2, size=len(public_key))
        
        ct0 = public_key[:, 0] * u + noise
        ct1 = public_key[:, 1] * u + noise
        
        # Embed plaintext in ct1
        if len(plaintext) <= len(ct1):
            ct1[:len(plaintext)] += plaintext
        
        ciphertext = np.column_stack([ct0, ct1]).flatten()
        return ciphertext.astype(np.int32).tobytes()
    
    async def decrypt(self, ciphertext: HomomorphicCiphertext, 
                     private_key: bytes) -> Union[int, float, List, np.ndarray]:
        """Decrypt BFV ciphertext"""
        secret_poly = np.frombuffer(private_key, dtype=np.int32)
        ct_data = np.frombuffer(ciphertext.ciphertext, dtype=np.int32).reshape(-1, 2)
        
        # Decrypt: m = ct[0] * s + ct[1] (mod q)
        decrypted = (ct_data[:, 0] * secret_poly + ct_data[:, 1]) % 1024
        
        # Handle noise and extract meaningful values
        decrypted = decrypted[:np.prod(ciphertext.dimensions)]
        
        if ciphertext.dimensions == (1,):
            return int(decrypted[0])
        else:
            return decrypted.reshape(ciphertext.dimensions)
    
    async def add_encrypted(self, ct1: HomomorphicCiphertext, 
                           ct2: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Add two BFV encrypted values"""
        if ct1.scheme != ct2.scheme or ct1.scheme != EncryptionScheme.BFV:
            raise ValueError("Incompatible encryption schemes")
        
        # Homomorphic addition: ct_add = ct1 + ct2
        ct1_data = np.frombuffer(ct1.ciphertext, dtype=np.int32)
        ct2_data = np.frombuffer(ct2.ciphertext, dtype=np.int32)
        
        # Ensure compatible dimensions
        min_len = min(len(ct1_data), len(ct2_data))
        result_data = (ct1_data[:min_len] + ct2_data[:min_len]) % 1024
        
        # Calculate new noise level
        new_noise_level = self._update_noise_level([ct1.noise_level, ct2.noise_level], OperationType.ADD)
        
        return HomomorphicCiphertext(
            ciphertext=result_data.astype(np.int32).tobytes(),
            noise_level=new_noise_level,
            operation_depth=max(ct1.operation_depth, ct2.operation_depth) + 1,
            data_type=ct1.data_type,
            dimensions=ct1.dimensions,
            scheme=EncryptionScheme.BFV,
            key_id=ct1.key_id
        )
    
    async def multiply_encrypted(self, ct1: HomomorphicCiphertext, 
                               ct2: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Multiply two BFV encrypted values"""
        if ct1.scheme != ct2.scheme or ct1.scheme != EncryptionScheme.BFV:
            raise ValueError("Incompatible encryption schemes")
        
        # Homomorphic multiplication is more complex and requires relinearization
        ct1_data = np.frombuffer(ct1.ciphertext, dtype=np.int32)
        ct2_data = np.frombuffer(ct2.ciphertext, dtype=np.int32)
        
        # Simplified multiplication (real implementation would be more complex)
        min_len = min(len(ct1_data), len(ct2_data))
        result_data = (ct1_data[:min_len] * ct2_data[:min_len]) % 1024
        
        # Multiplication significantly increases noise
        new_noise_level = self._update_noise_level([ct1.noise_level, ct2.noise_level], OperationType.MULTIPLY)
        
        return HomomorphicCiphertext(
            ciphertext=result_data.astype(np.int32).tobytes(),
            noise_level=new_noise_level,
            operation_depth=max(ct1.operation_depth, ct2.operation_depth) + 1,
            data_type=ct1.data_type,
            dimensions=ct1.dimensions,
            scheme=EncryptionScheme.BFV,
            key_id=ct1.key_id
        )
    
    def _update_noise_level(self, noise_levels: List[NoiseLevel], operation: OperationType) -> NoiseLevel:
        """Update noise level based on operation"""
        noise_scores = {
            NoiseLevel.LOW: 1,
            NoiseLevel.MEDIUM: 2,
            NoiseLevel.HIGH: 3,
            NoiseLevel.CRITICAL: 4
        }
        
        max_noise = max(noise_scores[level] for level in noise_levels)
        
        if operation == OperationType.ADD:
            new_score = max_noise + 1
        elif operation == OperationType.MULTIPLY:
            new_score = max_noise + 2
        else:
            new_score = max_noise + 1
        
        score_to_level = {1: NoiseLevel.LOW, 2: NoiseLevel.MEDIUM, 3: NoiseLevel.HIGH, 4: NoiseLevel.CRITICAL}
        return score_to_level.get(min(new_score, 4), NoiseLevel.CRITICAL)

class CKKSHomomorphicEngine(HomomorphicEncryptionEngine):
    """CKKS homomorphic encryption for approximate arithmetic on real numbers"""
    
    def __init__(self, security_level: int = 128):
        self.security_level = security_level
        self.default_parameters = {
            'polynomial_modulus_degree': 8192,
            'coefficient_modulus_bits': [60, 40, 40, 60],
            'scale': 2**40,
            'security_level': security_level
        }
    
    async def generate_keys(self, parameters: Optional[Dict[str, Any]] = None) -> HomomorphicKey:
        """Generate CKKS homomorphic encryption keys"""
        params = {**self.default_parameters, **(parameters or {})}
        
        # Generate keys using complex number arithmetic
        key_seed = secrets.randbits(256)
        poly_degree = params['polynomial_modulus_degree']
        
        # Secret key (Gaussian random)
        secret_key = self._generate_secret_key_ckks(poly_degree, key_seed)
        public_key = self._generate_public_key_ckks(secret_key, params)
        evaluation_key = self._generate_evaluation_key_ckks(secret_key, params)
        
        return HomomorphicKey(
            public_key=public_key,
            private_key=secret_key,
            evaluation_key=evaluation_key,
            scheme=EncryptionScheme.CKKS,
            parameters=params
        )
    
    def _generate_secret_key_ckks(self, poly_degree: int, seed: int) -> bytes:
        """Generate CKKS secret key"""
        np.random.seed(seed)
        # Gaussian distribution for CKKS
        secret_coeffs = np.random.normal(0, 1, size=poly_degree) + 1j * np.random.normal(0, 1, size=poly_degree)
        return secret_coeffs.astype(np.complex128).tobytes()
    
    def _generate_public_key_ckks(self, secret_key: bytes, params: Dict[str, Any]) -> bytes:
        """Generate CKKS public key"""
        secret_poly = np.frombuffer(secret_key, dtype=np.complex128)
        poly_degree = len(secret_poly)
        
        # Public key generation for CKKS
        a = np.random.normal(0, 1, size=poly_degree) + 1j * np.random.normal(0, 1, size=poly_degree)
        error = np.random.normal(0, 1, size=poly_degree) + 1j * np.random.normal(0, 1, size=poly_degree)
        b = -a * secret_poly + error
        
        public_key = np.column_stack([a.view(float).reshape(-1, 2), b.view(float).reshape(-1, 2)])
        return public_key.astype(np.float64).tobytes()
    
    def _generate_evaluation_key_ckks(self, secret_key: bytes, params: Dict[str, Any]) -> bytes:
        """Generate CKKS evaluation key"""
        eval_key_data = hashlib.sha256(secret_key + b"ckks_eval").digest()
        return eval_key_data
    
    async def encrypt(self, data: Union[int, float, List, np.ndarray], 
                     public_key: bytes) -> HomomorphicCiphertext:
        """Encrypt data using CKKS scheme"""
        # Convert to complex array
        if isinstance(data, (int, float)):
            plaintext = np.array([complex(data)], dtype=np.complex128)
        elif isinstance(data, list):
            plaintext = np.array([complex(x) for x in data], dtype=np.complex128)
        elif isinstance(data, np.ndarray):
            plaintext = data.astype(np.complex128)
        
        # Simulate CKKS encryption with scaling
        scale = self.default_parameters['scale']
        scaled_plaintext = plaintext * scale
        
        # Add encryption noise
        noise = (np.random.normal(0, 1, size=plaintext.shape) + 
                1j * np.random.normal(0, 1, size=plaintext.shape))
        
        ciphertext_data = (scaled_plaintext + noise).astype(np.complex128).tobytes()
        
        return HomomorphicCiphertext(
            ciphertext=ciphertext_data,
            noise_level=NoiseLevel.LOW,
            operation_depth=0,
            data_type="complex128",
            dimensions=plaintext.shape,
            scheme=EncryptionScheme.CKKS,
            key_id="default"
        )
    
    async def decrypt(self, ciphertext: HomomorphicCiphertext, 
                     private_key: bytes) -> Union[int, float, List, np.ndarray]:
        """Decrypt CKKS ciphertext"""
        ct_data = np.frombuffer(ciphertext.ciphertext, dtype=np.complex128)
        secret_poly = np.frombuffer(private_key, dtype=np.complex128)
        
        # Simplified CKKS decryption
        scale = self.default_parameters['scale']
        decrypted = ct_data / scale
        
        # Extract real parts for real-valued results
        result = np.real(decrypted[:np.prod(ciphertext.dimensions)])
        
        if ciphertext.dimensions == (1,):
            return float(result[0])
        else:
            return result.reshape(ciphertext.dimensions)
    
    async def add_encrypted(self, ct1: HomomorphicCiphertext, 
                           ct2: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Add two CKKS encrypted values"""
        ct1_data = np.frombuffer(ct1.ciphertext, dtype=np.complex128)
        ct2_data = np.frombuffer(ct2.ciphertext, dtype=np.complex128)
        
        min_len = min(len(ct1_data), len(ct2_data))
        result_data = ct1_data[:min_len] + ct2_data[:min_len]
        
        new_noise_level = self._update_noise_level([ct1.noise_level, ct2.noise_level], OperationType.ADD)
        
        return HomomorphicCiphertext(
            ciphertext=result_data.astype(np.complex128).tobytes(),
            noise_level=new_noise_level,
            operation_depth=max(ct1.operation_depth, ct2.operation_depth) + 1,
            data_type="complex128",
            dimensions=ct1.dimensions,
            scheme=EncryptionScheme.CKKS,
            key_id=ct1.key_id
        )
    
    async def multiply_encrypted(self, ct1: HomomorphicCiphertext, 
                               ct2: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Multiply two CKKS encrypted values"""
        ct1_data = np.frombuffer(ct1.ciphertext, dtype=np.complex128)
        ct2_data = np.frombuffer(ct2.ciphertext, dtype=np.complex128)
        
        min_len = min(len(ct1_data), len(ct2_data))
        result_data = ct1_data[:min_len] * ct2_data[:min_len]
        
        new_noise_level = self._update_noise_level([ct1.noise_level, ct2.noise_level], OperationType.MULTIPLY)
        
        return HomomorphicCiphertext(
            ciphertext=result_data.astype(np.complex128).tobytes(),
            noise_level=new_noise_level,
            operation_depth=max(ct1.operation_depth, ct2.operation_depth) + 1,
            data_type="complex128",
            dimensions=ct1.dimensions,
            scheme=EncryptionScheme.CKKS,
            key_id=ct1.key_id
        )
    
    def _update_noise_level(self, noise_levels: List[NoiseLevel], operation: OperationType) -> NoiseLevel:
        """Update noise level for CKKS operations"""
        noise_scores = {
            NoiseLevel.LOW: 1,
            NoiseLevel.MEDIUM: 2,
            NoiseLevel.HIGH: 3,
            NoiseLevel.CRITICAL: 4
        }
        
        max_noise = max(noise_scores[level] for level in noise_levels)
        
        if operation == OperationType.ADD:
            new_score = max_noise
        elif operation == OperationType.MULTIPLY:
            new_score = max_noise + 1  # CKKS has better noise growth for multiplication
        else:
            new_score = max_noise + 1
        
        score_to_level = {1: NoiseLevel.LOW, 2: NoiseLevel.MEDIUM, 3: NoiseLevel.HIGH, 4: NoiseLevel.CRITICAL}
        return score_to_level.get(min(new_score, 4), NoiseLevel.CRITICAL)

class HomomorphicComputationEngine:
    """High-level engine for homomorphic computations"""
    
    def __init__(self):
        self.engines = {
            EncryptionScheme.BFV: BFVHomomorphicEngine(),
            EncryptionScheme.CKKS: CKKSHomomorphicEngine()
        }
        self.key_storage = {}
        self.computation_history = []
        
    async def register_key(self, key: HomomorphicKey) -> str:
        """Register a homomorphic key for use"""
        self.key_storage[key.key_id] = key
        logger.info(f"Registered {key.scheme.value} key: {key.key_id}")
        return key.key_id
    
    async def encrypt_data(self, data: Union[int, float, List, np.ndarray], 
                          key_id: str, scheme: EncryptionScheme) -> HomomorphicCiphertext:
        """Encrypt data using specified key and scheme"""
        if key_id not in self.key_storage:
            raise ValueError(f"Key {key_id} not found")
        
        key = self.key_storage[key_id]
        engine = self.engines[scheme]
        
        ciphertext = await engine.encrypt(data, key.public_key)
        ciphertext.key_id = key_id
        
        return ciphertext
    
    async def decrypt_data(self, ciphertext: HomomorphicCiphertext) -> Union[int, float, List, np.ndarray]:
        """Decrypt homomorphic ciphertext"""
        if ciphertext.key_id not in self.key_storage:
            raise ValueError(f"Key {ciphertext.key_id} not found")
        
        key = self.key_storage[ciphertext.key_id]
        engine = self.engines[ciphertext.scheme]
        
        return await engine.decrypt(ciphertext, key.private_key)
    
    async def compute_sum(self, ciphertexts: List[HomomorphicCiphertext]) -> ComputationResult:
        """Compute sum of encrypted values"""
        if not ciphertexts:
            raise ValueError("No ciphertexts provided")
        
        start_time = datetime.now()
        operation_log = []
        
        # Ensure all ciphertexts use the same scheme
        scheme = ciphertexts[0].scheme
        if not all(ct.scheme == scheme for ct in ciphertexts):
            raise ValueError("All ciphertexts must use the same encryption scheme")
        
        engine = self.engines[scheme]
        result = ciphertexts[0]
        
        for i, ct in enumerate(ciphertexts[1:], 1):
            result = await engine.add_encrypted(result, ct)
            operation_log.append({
                'operation': 'add',
                'operand_index': i,
                'noise_level': result.noise_level.value,
                'operation_depth': result.operation_depth
            })
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        return ComputationResult(
            result_ciphertext=result,
            operation_log=operation_log,
            noise_growth=self._calculate_noise_growth(ciphertexts[0], result),
            computation_time=computation_time
        )
    
    async def compute_product(self, ciphertexts: List[HomomorphicCiphertext]) -> ComputationResult:
        """Compute product of encrypted values"""
        if not ciphertexts:
            raise ValueError("No ciphertexts provided")
        
        start_time = datetime.now()
        operation_log = []
        
        scheme = ciphertexts[0].scheme
        if not all(ct.scheme == scheme for ct in ciphertexts):
            raise ValueError("All ciphertexts must use the same encryption scheme")
        
        engine = self.engines[scheme]
        result = ciphertexts[0]
        
        for i, ct in enumerate(ciphertexts[1:], 1):
            result = await engine.multiply_encrypted(result, ct)
            operation_log.append({
                'operation': 'multiply',
                'operand_index': i,
                'noise_level': result.noise_level.value,
                'operation_depth': result.operation_depth
            })
            
            # Check for noise overflow
            if result.noise_level == NoiseLevel.CRITICAL:
                logger.warning(f"Critical noise level reached at operation {i}")
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        return ComputationResult(
            result_ciphertext=result,
            operation_log=operation_log,
            noise_growth=self._calculate_noise_growth(ciphertexts[0], result),
            computation_time=computation_time
        )
    
    async def compute_polynomial(self, coefficients: List[float], 
                               encrypted_input: HomomorphicCiphertext) -> ComputationResult:
        """Evaluate polynomial on encrypted input"""
        start_time = datetime.now()
        operation_log = []
        
        if not coefficients:
            raise ValueError("No coefficients provided")
        
        engine = self.engines[encrypted_input.scheme]
        
        # Start with constant term
        if coefficients[0] != 0:
            # Encrypt constant term
            constant = await self.encrypt_data(coefficients[0], encrypted_input.key_id, encrypted_input.scheme)
            result = constant
        else:
            result = None
        
        # Process each power term
        current_power = encrypted_input
        
        for i, coeff in enumerate(coefficients[1:], 1):
            if coeff != 0:
                # Multiply coefficient by x^i
                coeff_encrypted = await self.encrypt_data(coeff, encrypted_input.key_id, encrypted_input.scheme)
                term = await engine.multiply_encrypted(coeff_encrypted, current_power)
                
                if result is None:
                    result = term
                else:
                    result = await engine.add_encrypted(result, term)
                
                operation_log.append({
                    'operation': 'polynomial_term',
                    'power': i,
                    'coefficient': coeff,
                    'noise_level': result.noise_level.value
                })
            
            # Compute next power if needed
            if i < len(coefficients) - 1:
                current_power = await engine.multiply_encrypted(current_power, encrypted_input)
        
        if result is None:
            # Zero polynomial
            result = await self.encrypt_data(0, encrypted_input.key_id, encrypted_input.scheme)
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        return ComputationResult(
            result_ciphertext=result,
            operation_log=operation_log,
            noise_growth=self._calculate_noise_growth(encrypted_input, result),
            computation_time=computation_time
        )
    
    async def compute_statistics(self, encrypted_data: List[HomomorphicCiphertext]) -> Dict[str, ComputationResult]:
        """Compute basic statistics on encrypted data"""
        results = {}
        
        # Mean
        sum_result = await self.compute_sum(encrypted_data)
        n = len(encrypted_data)
        
        # Divide by n (would need to implement division or multiply by 1/n)
        # For now, just return the sum (mean = sum/n can be computed after decryption)
        results['sum'] = sum_result
        
        # Variance would require more complex operations
        # This is a simplified implementation
        results['count'] = ComputationResult(
            result_ciphertext=await self.encrypt_data(n, encrypted_data[0].key_id, encrypted_data[0].scheme),
            operation_log=[{'operation': 'count', 'value': n}],
            noise_growth=0.0,
            computation_time=0.001
        )
        
        return results
    
    def _calculate_noise_growth(self, initial: HomomorphicCiphertext, 
                              final: HomomorphicCiphertext) -> float:
        """Calculate noise growth during computation"""
        noise_scores = {
            NoiseLevel.LOW: 1,
            NoiseLevel.MEDIUM: 2,
            NoiseLevel.HIGH: 3,
            NoiseLevel.CRITICAL: 4
        }
        
        initial_score = noise_scores[initial.noise_level]
        final_score = noise_scores[final.noise_level]
        
        return (final_score - initial_score) / initial_score if initial_score > 0 else 0.0
    
    async def bootstrap_ciphertext(self, ciphertext: HomomorphicCiphertext) -> HomomorphicCiphertext:
        """Bootstrap ciphertext to reduce noise (for FHE schemes)"""
        # Bootstrapping is a complex operation that "refreshes" the ciphertext
        # This is a simplified placeholder implementation
        
        logger.info(f"Bootstrapping ciphertext {ciphertext.key_id}")
        
        # Simulate bootstrapping by creating a new ciphertext with reduced noise
        bootstrapped = HomomorphicCiphertext(
            ciphertext=ciphertext.ciphertext,
            noise_level=NoiseLevel.LOW,  # Bootstrapping reduces noise
            operation_depth=0,  # Reset operation depth
            data_type=ciphertext.data_type,
            dimensions=ciphertext.dimensions,
            scheme=ciphertext.scheme,
            key_id=ciphertext.key_id,
            metadata={**ciphertext.metadata, 'bootstrapped': True}
        )
        
        return bootstrapped
    
    def get_computation_metrics(self) -> Dict[str, Any]:
        """Get metrics about homomorphic computations"""
        return {
            'total_keys_registered': len(self.key_storage),
            'schemes_available': [scheme.value for scheme in self.engines.keys()],
            'computations_performed': len(self.computation_history),
            'supported_operations': [op.value for op in OperationType]
        }

# Factory functions
async def create_homomorphic_engine(scheme: EncryptionScheme = EncryptionScheme.BFV) -> HomomorphicComputationEngine:
    """Factory function to create homomorphic computation engine"""
    engine = HomomorphicComputationEngine()
    return engine

async def generate_homomorphic_keys(scheme: EncryptionScheme = EncryptionScheme.BFV, 
                                  security_level: int = 128) -> HomomorphicKey:
    """Generate homomorphic encryption keys"""
    if scheme == EncryptionScheme.BFV:
        he_engine = BFVHomomorphicEngine(security_level)
    elif scheme == EncryptionScheme.CKKS:
        he_engine = CKKSHomomorphicEngine(security_level)
    else:
        raise ValueError(f"Unsupported scheme: {scheme}")
    
    return await he_engine.generate_keys()

# Example usage
async def main():
    """Example usage of homomorphic encryption system"""
    
    # Create computation engine
    engine = await create_homomorphic_engine()
    
    # Generate keys
    bfv_key = await generate_homomorphic_keys(EncryptionScheme.BFV)
    ckks_key = await generate_homomorphic_keys(EncryptionScheme.CKKS)
    
    # Register keys
    bfv_key_id = await engine.register_key(bfv_key)
    ckks_key_id = await engine.register_key(ckks_key)
    
    # Encrypt some data
    data1 = [10, 20, 30]
    data2 = [5, 15, 25]
    
    encrypted1 = await engine.encrypt_data(data1, bfv_key_id, EncryptionScheme.BFV)
    encrypted2 = await engine.encrypt_data(data2, bfv_key_id, EncryptionScheme.BFV)
    
    # Perform homomorphic addition
    sum_result = await engine.compute_sum([encrypted1, encrypted2])
    
    # Decrypt result
    decrypted_sum = await engine.decrypt_data(sum_result.result_ciphertext)
    
    print(f"Original data: {data1} + {data2}")
    print(f"Encrypted computation result: {decrypted_sum}")
    print(f"Computation time: {sum_result.computation_time:.4f}s")
    print(f"Noise growth: {sum_result.noise_growth:.2f}")
    
    # Demonstrate polynomial evaluation
    coeffs = [1, 2, 1]  # 1 + 2x + x^2
    x_encrypted = await engine.encrypt_data(3, bfv_key_id, EncryptionScheme.BFV)
    
    poly_result = await engine.compute_polynomial(coeffs, x_encrypted)
    decrypted_poly = await engine.decrypt_data(poly_result.result_ciphertext)
    
    expected = 1 + 2*3 + 3**2  # = 16
    print(f"Polynomial f(3) = 1 + 2*3 + 3^2 = {expected}")
    print(f"Encrypted polynomial result: {decrypted_poly}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())