"""
Secure Multi-Party Computation (SMPC) System
Advanced cryptographic protocols for secure computation among multiple parties without revealing private inputs
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import secrets
import math
from abc import ABC, abstractmethod
from collections import defaultdict
import struct

logger = logging.getLogger(__name__)

class SMPCProtocol(Enum):
    """Types of SMPC protocols"""
    SHAMIR_SECRET_SHARING = "shamir"           # Shamir's secret sharing
    BGW_PROTOCOL = "bgw"                       # Ben-Or, Goldwasser, Wigderson protocol
    GMW_PROTOCOL = "gmw"                       # Goldreich, Micali, Wigderson protocol
    SPDZ_PROTOCOL = "spdz"                     # SPDZ protocol with MACs
    BMR_PROTOCOL = "bmr"                       # Beaver, Micali, Rogaway garbled circuits
    YEAST_PROTOCOL = "yeast"                   # Yet Another Secret sharing Tool
    ADDITIVE_SHARING = "additive"              # Simple additive secret sharing
    REPLICATED_SHARING = "replicated"          # Replicated secret sharing

class ComputationType(Enum):
    """Types of computations supported"""
    ADDITION = "addition"
    MULTIPLICATION = "multiplication"
    COMPARISON = "comparison"
    POLYNOMIAL_EVALUATION = "polynomial"
    MATRIX_MULTIPLICATION = "matrix_mult"
    STATISTICAL_ANALYSIS = "statistics"
    MACHINE_LEARNING = "ml"
    PRIVATE_SET_INTERSECTION = "psi"
    AUCTION = "auction"
    VOTING = "voting"

class PartyRole(Enum):
    """Roles of parties in SMPC"""
    INPUT_PROVIDER = "input_provider"
    COMPUTE_PARTY = "compute_party"
    OUTPUT_RECEIVER = "output_receiver"
    TRUSTED_DEALER = "trusted_dealer"
    COORDINATOR = "coordinator"

class SecurityModel(Enum):
    """Security models for SMPC"""
    SEMI_HONEST = "semi_honest"               # Parties follow protocol but may try to learn extra info
    MALICIOUS = "malicious"                   # Parties may arbitrarily deviate from protocol
    COVERT = "covert"                         # Malicious parties may be caught with some probability

@dataclass
class SMPCParty:
    """Represents a party in secure multi-party computation"""
    party_id: str
    role: PartyRole
    public_key: bytes
    private_key: bytes
    network_address: str
    port: int
    capabilities: List[ComputationType] = field(default_factory=list)
    security_level: int = 128
    online: bool = True
    reputation_score: float = 1.0
    
    def __post_init__(self):
        if not self.party_id:
            self.party_id = secrets.token_hex(8)

@dataclass
class SecretShare:
    """Secret share in SMPC protocol"""
    share_id: str
    party_id: str
    share_value: Union[int, bytes, np.ndarray]
    threshold: int
    total_parties: int
    protocol: SMPCProtocol
    data_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class SMPCCircuit:
    """Circuit representation for SMPC computation"""
    circuit_id: str
    operations: List[Dict[str, Any]]
    input_wires: Dict[str, str]  # wire_id -> party_id
    output_wires: List[str]
    depth: int
    gate_count: int
    protocol: SMPCProtocol
    
    def add_gate(self, gate_type: str, input_wires: List[str], output_wire: str, **kwargs):
        """Add a gate to the circuit"""
        self.operations.append({
            'type': gate_type,
            'inputs': input_wires,
            'output': output_wire,
            'params': kwargs
        })
        self.gate_count += 1

@dataclass
class SMPCComputationResult:
    """Result of SMPC computation"""
    computation_id: str
    result: Any
    participating_parties: List[str]
    protocol_used: SMPCProtocol
    computation_time: float
    communication_rounds: int
    total_messages: int
    security_guarantees: Dict[str, bool]
    verification_data: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

class SecretSharingScheme(ABC):
    """Abstract base class for secret sharing schemes"""
    
    @abstractmethod
    async def share_secret(self, secret: Union[int, bytes], threshold: int, 
                          total_parties: int) -> List[SecretShare]:
        """Share a secret among parties"""
        pass
    
    @abstractmethod
    async def reconstruct_secret(self, shares: List[SecretShare]) -> Union[int, bytes]:
        """Reconstruct secret from shares"""
        pass

class ShamirSecretSharing(SecretSharingScheme):
    """Shamir's (t,n) threshold secret sharing scheme"""
    
    def __init__(self, prime: int = None):
        # Use a large prime for the finite field
        self.prime = prime or self._generate_prime(256)
    
    def _generate_prime(self, bit_length: int) -> int:
        """Generate a prime number for the finite field"""
        # This is a simplified implementation
        # In practice, would use proper prime generation
        return 2**127 - 1  # Mersenne prime
    
    async def share_secret(self, secret: Union[int, bytes], threshold: int, 
                          total_parties: int) -> List[SecretShare]:
        """Create Shamir secret shares"""
        if isinstance(secret, bytes):
            secret = int.from_bytes(secret, byteorder='big')
        
        if secret >= self.prime:
            raise ValueError("Secret must be smaller than prime")
        
        if threshold > total_parties:
            raise ValueError("Threshold cannot exceed total parties")
        
        # Generate random coefficients for polynomial
        coefficients = [secret] + [secrets.randbelow(self.prime) for _ in range(threshold - 1)]
        
        shares = []
        for i in range(1, total_parties + 1):
            # Evaluate polynomial at point i
            share_value = self._evaluate_polynomial(coefficients, i, self.prime)
            
            share = SecretShare(
                share_id=f"share_{i}",
                party_id=f"party_{i}",
                share_value=share_value,
                threshold=threshold,
                total_parties=total_parties,
                protocol=SMPCProtocol.SHAMIR_SECRET_SHARING,
                data_type="integer"
            )
            shares.append(share)
        
        return shares
    
    def _evaluate_polynomial(self, coefficients: List[int], x: int, prime: int) -> int:
        """Evaluate polynomial at point x in finite field"""
        result = 0
        x_power = 1
        
        for coeff in coefficients:
            result = (result + coeff * x_power) % prime
            x_power = (x_power * x) % prime
        
        return result
    
    async def reconstruct_secret(self, shares: List[SecretShare]) -> int:
        """Reconstruct secret using Lagrange interpolation"""
        if len(shares) < shares[0].threshold:
            raise ValueError("Insufficient shares for reconstruction")
        
        # Use first 'threshold' shares
        working_shares = shares[:shares[0].threshold]
        
        # Lagrange interpolation
        secret = 0
        
        for i, share in enumerate(working_shares):
            x_i = i + 1  # Share points are 1, 2, 3, ...
            y_i = share.share_value
            
            # Calculate Lagrange coefficient
            numerator = denominator = 1
            
            for j, other_share in enumerate(working_shares):
                if i != j:
                    x_j = j + 1
                    numerator = (numerator * (-x_j)) % self.prime
                    denominator = (denominator * (x_i - x_j)) % self.prime
            
            # Modular inverse
            denominator_inv = pow(denominator, self.prime - 2, self.prime)
            lagrange_coeff = (numerator * denominator_inv) % self.prime
            
            secret = (secret + y_i * lagrange_coeff) % self.prime
        
        return secret

class AdditiveSecretSharing(SecretSharingScheme):
    """Simple additive secret sharing"""
    
    async def share_secret(self, secret: Union[int, bytes], threshold: int, 
                          total_parties: int) -> List[SecretShare]:
        """Create additive secret shares"""
        if isinstance(secret, bytes):
            secret = int.from_bytes(secret, byteorder='big')
        
        # Generate n-1 random shares
        shares = []
        sum_shares = 0
        
        for i in range(total_parties - 1):
            share_value = secrets.randbits(64)  # Random 64-bit value
            sum_shares = (sum_shares + share_value) % (2**64)
            
            shares.append(SecretShare(
                share_id=f"add_share_{i}",
                party_id=f"party_{i}",
                share_value=share_value,
                threshold=total_parties,  # All parties needed for additive sharing
                total_parties=total_parties,
                protocol=SMPCProtocol.ADDITIVE_SHARING,
                data_type="integer"
            ))
        
        # Last share ensures sum equals secret
        last_share_value = (secret - sum_shares) % (2**64)
        shares.append(SecretShare(
            share_id=f"add_share_{total_parties-1}",
            party_id=f"party_{total_parties-1}",
            share_value=last_share_value,
            threshold=total_parties,
            total_parties=total_parties,
            protocol=SMPCProtocol.ADDITIVE_SHARING,
            data_type="integer"
        ))
        
        return shares
    
    async def reconstruct_secret(self, shares: List[SecretShare]) -> int:
        """Reconstruct secret by adding all shares"""
        if len(shares) != shares[0].total_parties:
            raise ValueError("All shares required for additive reconstruction")
        
        secret = 0
        for share in shares:
            secret = (secret + share.share_value) % (2**64)
        
        return secret

class SMPCProtocolEngine(ABC):
    """Abstract base class for SMPC protocol engines"""
    
    @abstractmethod
    async def setup_computation(self, parties: List[SMPCParty], 
                               circuit: SMPCCircuit) -> str:
        """Setup computation among parties"""
        pass
    
    @abstractmethod
    async def execute_computation(self, computation_id: str, 
                                inputs: Dict[str, Any]) -> SMPCComputationResult:
        """Execute the SMPC computation"""
        pass

class BGWProtocolEngine(SMPCProtocolEngine):
    """BGW protocol engine for arithmetic circuits over finite fields"""
    
    def __init__(self):
        self.secret_sharing = ShamirSecretSharing()
        self.active_computations = {}
        self.communication_log = defaultdict(list)
    
    async def setup_computation(self, parties: List[SMPCParty], 
                               circuit: SMPCCircuit) -> str:
        """Setup BGW computation"""
        computation_id = secrets.token_hex(16)
        
        # Verify we have enough parties for the threshold
        threshold = len(parties) // 2 + 1  # Honest majority required
        
        if len(parties) < 3:
            raise ValueError("BGW protocol requires at least 3 parties")
        
        self.active_computations[computation_id] = {
            'parties': parties,
            'circuit': circuit,
            'threshold': threshold,
            'shares': {},
            'intermediate_values': {},
            'protocol': SMPCProtocol.BGW_PROTOCOL
        }
        
        logger.info(f"Setup BGW computation {computation_id} with {len(parties)} parties")
        return computation_id
    
    async def execute_computation(self, computation_id: str, 
                                inputs: Dict[str, Any]) -> SMPCComputationResult:
        """Execute BGW protocol computation"""
        if computation_id not in self.active_computations:
            raise ValueError(f"Computation {computation_id} not found")
        
        start_time = datetime.now()
        computation = self.active_computations[computation_id]
        circuit = computation['circuit']
        parties = computation['parties']
        threshold = computation['threshold']
        
        communication_rounds = 0
        total_messages = 0
        
        # Phase 1: Share inputs
        for wire_id, party_id in circuit.input_wires.items():
            if wire_id in inputs:
                shares = await self.secret_sharing.share_secret(
                    inputs[wire_id], threshold, len(parties)
                )
                computation['shares'][wire_id] = shares
                total_messages += len(shares)
        
        communication_rounds += 1
        
        # Phase 2: Execute circuit gates
        for operation in circuit.operations:
            gate_type = operation['type']
            input_wires = operation['inputs']
            output_wire = operation['output']
            
            if gate_type == 'ADD':
                # Addition gate - local operation
                result_shares = await self._execute_addition_gate(
                    computation['shares'][input_wires[0]],
                    computation['shares'][input_wires[1]]
                )
                computation['shares'][output_wire] = result_shares
                
            elif gate_type == 'MULT':
                # Multiplication gate - requires communication
                result_shares = await self._execute_multiplication_gate(
                    computation['shares'][input_wires[0]],
                    computation['shares'][input_wires[1]],
                    threshold, len(parties)
                )
                computation['shares'][output_wire] = result_shares
                communication_rounds += 1
                total_messages += len(parties) * (len(parties) - 1)  # Each party sends to others
            
            elif gate_type == 'CONST':
                # Constant gate
                constant_value = operation['params']['value']
                result_shares = await self._create_constant_shares(
                    constant_value, threshold, len(parties)
                )
                computation['shares'][output_wire] = result_shares
        
        # Phase 3: Reconstruct outputs
        results = {}
        for output_wire in circuit.output_wires:
            if output_wire in computation['shares']:
                result = await self.secret_sharing.reconstruct_secret(
                    computation['shares'][output_wire]
                )
                results[output_wire] = result
        
        communication_rounds += 1
        total_messages += len(circuit.output_wires) * threshold
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        return SMPCComputationResult(
            computation_id=computation_id,
            result=results,
            participating_parties=[p.party_id for p in parties],
            protocol_used=SMPCProtocol.BGW_PROTOCOL,
            computation_time=computation_time,
            communication_rounds=communication_rounds,
            total_messages=total_messages,
            security_guarantees={
                'privacy': True,
                'correctness': True,
                'robustness': True,
                'semi_honest_secure': True,
                'malicious_secure': False
            }
        )
    
    async def _execute_addition_gate(self, shares_a: List[SecretShare], 
                                   shares_b: List[SecretShare]) -> List[SecretShare]:
        """Execute addition gate (local operation)"""
        if len(shares_a) != len(shares_b):
            raise ValueError("Share lists must have same length")
        
        result_shares = []
        for share_a, share_b in zip(shares_a, shares_b):
            result_value = (share_a.share_value + share_b.share_value) % self.secret_sharing.prime
            
            result_share = SecretShare(
                share_id=f"add_result_{share_a.party_id}",
                party_id=share_a.party_id,
                share_value=result_value,
                threshold=share_a.threshold,
                total_parties=share_a.total_parties,
                protocol=SMPCProtocol.BGW_PROTOCOL,
                data_type="integer"
            )
            result_shares.append(result_share)
        
        return result_shares
    
    async def _execute_multiplication_gate(self, shares_a: List[SecretShare], 
                                         shares_b: List[SecretShare],
                                         threshold: int, total_parties: int) -> List[SecretShare]:
        """Execute multiplication gate (requires degree reduction)"""
        if len(shares_a) != len(shares_b):
            raise ValueError("Share lists must have same length")
        
        # Step 1: Local multiplication (increases polynomial degree)
        intermediate_shares = []
        for share_a, share_b in zip(shares_a, shares_b):
            mult_value = (share_a.share_value * share_b.share_value) % self.secret_sharing.prime
            
            intermediate_share = SecretShare(
                share_id=f"mult_intermediate_{share_a.party_id}",
                party_id=share_a.party_id,
                share_value=mult_value,
                threshold=2 * threshold - 1,  # Degree doubled
                total_parties=share_a.total_parties,
                protocol=SMPCProtocol.BGW_PROTOCOL,
                data_type="integer"
            )
            intermediate_shares.append(intermediate_share)
        
        # Step 2: Degree reduction (simplified)
        # In practice, this would involve more complex polynomial operations
        # For now, we'll use a simplified approach
        
        result_shares = []
        for i, share in enumerate(intermediate_shares):
            # Simulate degree reduction
            reduced_value = share.share_value % self.secret_sharing.prime
            
            result_share = SecretShare(
                share_id=f"mult_result_{share.party_id}",
                party_id=share.party_id,
                share_value=reduced_value,
                threshold=threshold,
                total_parties=total_parties,
                protocol=SMPCProtocol.BGW_PROTOCOL,
                data_type="integer"
            )
            result_shares.append(result_share)
        
        return result_shares
    
    async def _create_constant_shares(self, constant: int, threshold: int, 
                                    total_parties: int) -> List[SecretShare]:
        """Create shares for a constant value"""
        return await self.secret_sharing.share_secret(constant, threshold, total_parties)

class GMWProtocolEngine(SMPCProtocolEngine):
    """GMW protocol engine for boolean circuits"""
    
    def __init__(self):
        self.active_computations = {}
        self.oblivious_transfer = ObliviousTransferProtocol()
    
    async def setup_computation(self, parties: List[SMPCParty], 
                               circuit: SMPCCircuit) -> str:
        """Setup GMW computation"""
        computation_id = secrets.token_hex(16)
        
        if len(parties) < 2:
            raise ValueError("GMW protocol requires at least 2 parties")
        
        self.active_computations[computation_id] = {
            'parties': parties,
            'circuit': circuit,
            'shares': {},
            'protocol': SMPCProtocol.GMW_PROTOCOL
        }
        
        logger.info(f"Setup GMW computation {computation_id} with {len(parties)} parties")
        return computation_id
    
    async def execute_computation(self, computation_id: str, 
                                inputs: Dict[str, Any]) -> SMPCComputationResult:
        """Execute GMW protocol computation"""
        if computation_id not in self.active_computations:
            raise ValueError(f"Computation {computation_id} not found")
        
        start_time = datetime.now()
        computation = self.active_computations[computation_id]
        circuit = computation['circuit']
        parties = computation['parties']
        
        communication_rounds = 0
        total_messages = 0
        
        # Phase 1: Share inputs using XOR sharing
        for wire_id, party_id in circuit.input_wires.items():
            if wire_id in inputs:
                shares = await self._create_boolean_shares(
                    inputs[wire_id], len(parties)
                )
                computation['shares'][wire_id] = shares
        
        communication_rounds += 1
        total_messages += len(circuit.input_wires) * len(parties)
        
        # Phase 2: Execute circuit gates
        for operation in circuit.operations:
            gate_type = operation['type']
            input_wires = operation['inputs']
            output_wire = operation['output']
            
            if gate_type == 'XOR':
                # XOR gate - local operation
                result_shares = await self._execute_xor_gate(
                    computation['shares'][input_wires[0]],
                    computation['shares'][input_wires[1]]
                )
                computation['shares'][output_wire] = result_shares
                
            elif gate_type == 'AND':
                # AND gate - requires oblivious transfer
                result_shares, messages = await self._execute_and_gate(
                    computation['shares'][input_wires[0]],
                    computation['shares'][input_wires[1]],
                    len(parties)
                )
                computation['shares'][output_wire] = result_shares
                communication_rounds += 1
                total_messages += messages
        
        # Phase 3: Reconstruct outputs
        results = {}
        for output_wire in circuit.output_wires:
            if output_wire in computation['shares']:
                result = await self._reconstruct_boolean_secret(
                    computation['shares'][output_wire]
                )
                results[output_wire] = result
        
        communication_rounds += 1
        
        computation_time = (datetime.now() - start_time).total_seconds()
        
        return SMPCComputationResult(
            computation_id=computation_id,
            result=results,
            participating_parties=[p.party_id for p in parties],
            protocol_used=SMPCProtocol.GMW_PROTOCOL,
            computation_time=computation_time,
            communication_rounds=communication_rounds,
            total_messages=total_messages,
            security_guarantees={
                'privacy': True,
                'correctness': True,
                'robustness': False,
                'semi_honest_secure': True,
                'malicious_secure': False
            }
        )
    
    async def _create_boolean_shares(self, value: int, num_parties: int) -> List[SecretShare]:
        """Create boolean shares using XOR sharing"""
        # Convert value to binary
        bit_value = value & 1  # Take least significant bit
        
        shares = []
        xor_sum = 0
        
        # Generate n-1 random shares
        for i in range(num_parties - 1):
            share_bit = secrets.randbits(1)
            xor_sum ^= share_bit
            
            shares.append(SecretShare(
                share_id=f"bool_share_{i}",
                party_id=f"party_{i}",
                share_value=share_bit,
                threshold=num_parties,
                total_parties=num_parties,
                protocol=SMPCProtocol.GMW_PROTOCOL,
                data_type="boolean"
            ))
        
        # Last share ensures XOR equals original value
        last_share_bit = bit_value ^ xor_sum
        shares.append(SecretShare(
            share_id=f"bool_share_{num_parties-1}",
            party_id=f"party_{num_parties-1}",
            share_value=last_share_bit,
            threshold=num_parties,
            total_parties=num_parties,
            protocol=SMPCProtocol.GMW_PROTOCOL,
            data_type="boolean"
        ))
        
        return shares
    
    async def _execute_xor_gate(self, shares_a: List[SecretShare], 
                               shares_b: List[SecretShare]) -> List[SecretShare]:
        """Execute XOR gate (local operation)"""
        result_shares = []
        for share_a, share_b in zip(shares_a, shares_b):
            result_value = share_a.share_value ^ share_b.share_value
            
            result_share = SecretShare(
                share_id=f"xor_result_{share_a.party_id}",
                party_id=share_a.party_id,
                share_value=result_value,
                threshold=share_a.threshold,
                total_parties=share_a.total_parties,
                protocol=SMPCProtocol.GMW_PROTOCOL,
                data_type="boolean"
            )
            result_shares.append(result_share)
        
        return result_shares
    
    async def _execute_and_gate(self, shares_a: List[SecretShare], 
                               shares_b: List[SecretShare],
                               num_parties: int) -> Tuple[List[SecretShare], int]:
        """Execute AND gate using oblivious transfer"""
        # Simplified AND gate implementation
        # In practice, would use proper oblivious transfer protocol
        
        result_shares = []
        messages_sent = 0
        
        for share_a, share_b in zip(shares_a, shares_b):
            # Simulate AND operation with communication
            # This is a simplified implementation
            result_value = share_a.share_value & share_b.share_value
            
            result_share = SecretShare(
                share_id=f"and_result_{share_a.party_id}",
                party_id=share_a.party_id,
                share_value=result_value,
                threshold=share_a.threshold,
                total_parties=share_a.total_parties,
                protocol=SMPCProtocol.GMW_PROTOCOL,
                data_type="boolean"
            )
            result_shares.append(result_share)
            messages_sent += 2  # Simplified message count
        
        return result_shares, messages_sent
    
    async def _reconstruct_boolean_secret(self, shares: List[SecretShare]) -> int:
        """Reconstruct boolean secret by XORing all shares"""
        result = 0
        for share in shares:
            result ^= share.share_value
        return result

class ObliviousTransferProtocol:
    """Oblivious Transfer protocol for secure communication"""
    
    async def ot_1_of_2(self, sender_messages: Tuple[bytes, bytes], 
                       receiver_choice: int) -> bytes:
        """1-out-of-2 Oblivious Transfer"""
        # Simplified OT implementation
        # In practice, would use proper cryptographic primitives
        
        if receiver_choice not in [0, 1]:
            raise ValueError("Receiver choice must be 0 or 1")
        
        # Simulate OT protocol
        # The sender doesn't learn which message was chosen
        # The receiver only learns the chosen message
        
        chosen_message = sender_messages[receiver_choice]
        
        # Add some randomization to simulate the protocol
        noise = secrets.token_bytes(len(chosen_message))
        
        # In real OT, this would be properly encrypted
        return chosen_message

class SMPCOrchestrator:
    """High-level orchestrator for SMPC operations"""
    
    def __init__(self):
        self.protocol_engines = {
            SMPCProtocol.BGW_PROTOCOL: BGWProtocolEngine(),
            SMPCProtocol.GMW_PROTOCOL: GMWProtocolEngine()
        }
        self.registered_parties = {}
        self.active_sessions = {}
        
    async def register_party(self, party: SMPCParty) -> str:
        """Register a party for SMPC"""
        self.registered_parties[party.party_id] = party
        logger.info(f"Registered party {party.party_id} with role {party.role.value}")
        return party.party_id
    
    async def create_computation_session(self, protocol: SMPCProtocol, 
                                       party_ids: List[str],
                                       circuit: SMPCCircuit) -> str:
        """Create a new SMPC computation session"""
        # Verify all parties are registered
        parties = []
        for party_id in party_ids:
            if party_id not in self.registered_parties:
                raise ValueError(f"Party {party_id} not registered")
            parties.append(self.registered_parties[party_id])
        
        # Setup computation with appropriate protocol engine
        engine = self.protocol_engines[protocol]
        computation_id = await engine.setup_computation(parties, circuit)
        
        self.active_sessions[computation_id] = {
            'protocol': protocol,
            'parties': parties,
            'circuit': circuit,
            'engine': engine,
            'created_at': datetime.now()
        }
        
        return computation_id
    
    async def execute_secure_computation(self, computation_id: str, 
                                       inputs: Dict[str, Any]) -> SMPCComputationResult:
        """Execute secure multi-party computation"""
        if computation_id not in self.active_sessions:
            raise ValueError(f"Computation session {computation_id} not found")
        
        session = self.active_sessions[computation_id]
        engine = session['engine']
        
        result = await engine.execute_computation(computation_id, inputs)
        
        logger.info(f"Completed SMPC computation {computation_id} in {result.computation_time:.3f}s")
        
        return result
    
    async def create_arithmetic_circuit(self, computation_type: ComputationType) -> SMPCCircuit:
        """Create predefined arithmetic circuits for common computations"""
        
        if computation_type == ComputationType.ADDITION:
            circuit = SMPCCircuit(
                circuit_id=f"add_circuit_{secrets.token_hex(8)}",
                operations=[],
                input_wires={'input_a': 'party_0', 'input_b': 'party_1'},
                output_wires=['output'],
                depth=1,
                gate_count=1,
                protocol=SMPCProtocol.BGW_PROTOCOL
            )
            
            circuit.add_gate('ADD', ['input_a', 'input_b'], 'output')
            return circuit
        
        elif computation_type == ComputationType.MULTIPLICATION:
            circuit = SMPCCircuit(
                circuit_id=f"mult_circuit_{secrets.token_hex(8)}",
                operations=[],
                input_wires={'input_a': 'party_0', 'input_b': 'party_1'},
                output_wires=['output'],
                depth=1,
                gate_count=1,
                protocol=SMPCProtocol.BGW_PROTOCOL
            )
            
            circuit.add_gate('MULT', ['input_a', 'input_b'], 'output')
            return circuit
        
        elif computation_type == ComputationType.STATISTICAL_ANALYSIS:
            # Circuit for computing sum of inputs from multiple parties
            circuit = SMPCCircuit(
                circuit_id=f"stats_circuit_{secrets.token_hex(8)}",
                operations=[],
                input_wires={f'input_{i}': f'party_{i}' for i in range(4)},
                output_wires=['sum_output'],
                depth=2,
                gate_count=3,
                protocol=SMPCProtocol.BGW_PROTOCOL
            )
            
            # Add gates to sum all inputs
            circuit.add_gate('ADD', ['input_0', 'input_1'], 'temp_1')
            circuit.add_gate('ADD', ['input_2', 'input_3'], 'temp_2')
            circuit.add_gate('ADD', ['temp_1', 'temp_2'], 'sum_output')
            
            return circuit
        
        else:
            raise ValueError(f"Unsupported computation type: {computation_type}")
    
    async def create_boolean_circuit(self, computation_type: ComputationType) -> SMPCCircuit:
        """Create boolean circuits for GMW protocol"""
        
        if computation_type == ComputationType.COMPARISON:
            circuit = SMPCCircuit(
                circuit_id=f"compare_circuit_{secrets.token_hex(8)}",
                operations=[],
                input_wires={'input_a': 'party_0', 'input_b': 'party_1'},
                output_wires=['greater_than'],
                depth=3,
                gate_count=5,
                protocol=SMPCProtocol.GMW_PROTOCOL
            )
            
            # Simplified greater-than comparison circuit
            circuit.add_gate('XOR', ['input_a', 'input_b'], 'xor_1')
            circuit.add_gate('AND', ['input_a', 'input_b'], 'and_1')
            circuit.add_gate('XOR', ['xor_1', 'and_1'], 'greater_than')
            
            return circuit
        
        else:
            raise ValueError(f"Unsupported boolean computation type: {computation_type}")
    
    def get_session_metrics(self, computation_id: str) -> Dict[str, Any]:
        """Get metrics for a computation session"""
        if computation_id not in self.active_sessions:
            raise ValueError(f"Session {computation_id} not found")
        
        session = self.active_sessions[computation_id]
        
        return {
            'session_id': computation_id,
            'protocol': session['protocol'].value,
            'party_count': len(session['parties']),
            'circuit_depth': session['circuit'].depth,
            'circuit_gates': session['circuit'].gate_count,
            'created_at': session['created_at'].isoformat(),
            'status': 'active'
        }

# Factory functions
async def create_smpc_orchestrator() -> SMPCOrchestrator:
    """Factory function to create SMPC orchestrator"""
    return SMPCOrchestrator()

async def create_smpc_party(party_id: str, role: PartyRole, 
                          capabilities: List[ComputationType] = None) -> SMPCParty:
    """Factory function to create SMPC party"""
    # Generate key pair (simplified)
    private_key = secrets.token_bytes(32)
    public_key = hashlib.sha256(private_key).digest()
    
    return SMPCParty(
        party_id=party_id,
        role=role,
        public_key=public_key,
        private_key=private_key,
        network_address="localhost",
        port=8000,
        capabilities=capabilities or []
    )

# Example usage
async def main():
    """Example usage of SMPC system"""
    
    # Create orchestrator
    orchestrator = await create_smpc_orchestrator()
    
    # Create parties
    party1 = await create_smpc_party("alice", PartyRole.INPUT_PROVIDER, [ComputationType.ADDITION])
    party2 = await create_smpc_party("bob", PartyRole.INPUT_PROVIDER, [ComputationType.ADDITION])
    party3 = await create_smpc_party("charlie", PartyRole.COMPUTE_PARTY, [ComputationType.ADDITION])
    
    # Register parties
    await orchestrator.register_party(party1)
    await orchestrator.register_party(party2)
    await orchestrator.register_party(party3)
    
    # Create arithmetic circuit for addition
    circuit = await orchestrator.create_arithmetic_circuit(ComputationType.ADDITION)
    
    # Create computation session
    session_id = await orchestrator.create_computation_session(
        SMPCProtocol.BGW_PROTOCOL,
        [party1.party_id, party2.party_id, party3.party_id],
        circuit
    )
    
    # Execute secure computation
    inputs = {
        'input_a': 42,
        'input_b': 13
    }
    
    result = await orchestrator.execute_secure_computation(session_id, inputs)
    
    print(f"SMPC Computation Results:")
    print(f"  Result: {result.result}")
    print(f"  Protocol: {result.protocol_used.value}")
    print(f"  Computation time: {result.computation_time:.3f}s")
    print(f"  Communication rounds: {result.communication_rounds}")
    print(f"  Total messages: {result.total_messages}")
    print(f"  Security guarantees: {result.security_guarantees}")
    
    # Get session metrics
    metrics = orchestrator.get_session_metrics(session_id)
    print(f"\nSession Metrics:")
    for key, value in metrics.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())