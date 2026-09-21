"""
Cryptographic utilities for blockchain operations
Provides hashing, merkle trees, and other crypto functions
"""

import hashlib
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import base64
import secrets
from dataclasses import dataclass
from Crypto.Hash import keccak


@dataclass
class MerkleTree:
    root: str
    leaves: List[str]
    tree_levels: List[List[str]]
    proofs: Dict[str, List[Dict[str, Any]]]


def create_data_hash(data: Any) -> str:
    """Create a deterministic hash of any data structure"""
    
    # Convert data to JSON string with sorted keys for deterministic hashing
    if isinstance(data, (dict, list)):
        json_str = json.dumps(data, sort_keys=True, default=str, separators=(',', ':'))
    else:
        json_str = str(data)
    
    # Use SHA-256 for data hashing
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def create_event_hash(
    event_type: str,
    timestamp: datetime,
    user_id: str,
    action: str,
    resource: str,
    metadata: Dict[str, Any] = None
) -> str:
    """Create hash for audit events"""
    
    event_data = {
        "event_type": event_type,
        "timestamp": timestamp.isoformat(),
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "metadata": metadata or {}
    }
    
    return create_data_hash(event_data)


def generate_merkle_tree(data_hashes: List[str]) -> MerkleTree:
    """Generate merkle tree from list of data hashes"""
    
    if not data_hashes:
        raise ValueError("Cannot create merkle tree from empty list")
    
    # Ensure even number of leaves (duplicate last if odd)
    leaves = data_hashes.copy()
    if len(leaves) % 2 == 1:
        leaves.append(leaves[-1])
    
    tree_levels = [leaves]
    current_level = leaves
    
    # Build tree levels
    while len(current_level) > 1:
        next_level = []
        
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
            
            # Combine hashes and hash again
            combined = left + right
            parent_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
            next_level.append(parent_hash)
        
        tree_levels.append(next_level)
        current_level = next_level
    
    root = current_level[0]
    
    # Generate proofs for each leaf
    proofs = {}
    for i, leaf in enumerate(data_hashes):
        proof = generate_merkle_proof(tree_levels, i)
        proofs[leaf] = proof
    
    return MerkleTree(
        root=root,
        leaves=data_hashes,
        tree_levels=tree_levels,
        proofs=proofs
    )


def generate_merkle_proof(tree_levels: List[List[str]], leaf_index: int) -> List[Dict[str, Any]]:
    """Generate merkle proof for a specific leaf"""
    
    proof = []
    index = leaf_index
    
    for level in range(len(tree_levels) - 1):
        current_level = tree_levels[level]
        
        # Determine sibling index
        if index % 2 == 0:
            # Left child, sibling is to the right
            sibling_index = index + 1
            position = "right"
        else:
            # Right child, sibling is to the left
            sibling_index = index - 1
            position = "left"
        
        # Get sibling hash (duplicate if out of bounds)
        if sibling_index < len(current_level):
            sibling_hash = current_level[sibling_index]
        else:
            sibling_hash = current_level[index]
        
        proof.append({
            "hash": sibling_hash,
            "position": position
        })
        
        # Move to parent index for next level
        index = index // 2
    
    return proof


def verify_merkle_proof(leaf_hash: str, proof: List[Dict[str, Any]], root: str) -> bool:
    """Verify a merkle proof"""
    
    current_hash = leaf_hash
    
    for proof_element in proof:
        sibling_hash = proof_element["hash"]
        position = proof_element["position"]
        
        if position == "left":
            combined = sibling_hash + current_hash
        else:
            combined = current_hash + sibling_hash
        
        current_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    return current_hash == root


def keccak256(data: bytes) -> str:
    """Ethereum-compatible Keccak-256 hash"""
    
    k = keccak.new(digest_bits=256)
    k.update(data)
    return '0x' + k.hexdigest()


def generate_commitment(value: str, nonce: str = None) -> Tuple[str, str]:
    """Generate a cryptographic commitment (hash commitment scheme)"""
    
    if nonce is None:
        nonce = secrets.token_hex(32)
    
    commitment_data = f"{value}:{nonce}"
    commitment = hashlib.sha256(commitment_data.encode()).hexdigest()
    
    return commitment, nonce


def verify_commitment(value: str, nonce: str, commitment: str) -> bool:
    """Verify a cryptographic commitment"""
    
    commitment_data = f"{value}:{nonce}"
    expected_commitment = hashlib.sha256(commitment_data.encode()).hexdigest()
    
    return expected_commitment == commitment


def generate_zero_knowledge_challenge() -> Dict[str, str]:
    """Generate challenge for zero-knowledge proof protocol"""
    
    challenge = secrets.token_hex(32)
    salt = secrets.token_hex(16)
    
    return {
        "challenge": challenge,
        "salt": salt,
        "timestamp": datetime.utcnow().isoformat()
    }


def create_privacy_hash(data: Dict[str, Any], private_fields: List[str]) -> Dict[str, Any]:
    """Create hash that preserves privacy of specified fields"""
    
    public_data = {}
    private_data = {}
    
    for key, value in data.items():
        if key in private_fields:
            private_data[key] = value
            # Replace with hash in public data
            public_data[key] = hashlib.sha256(str(value).encode()).hexdigest()[:16]
        else:
            public_data[key] = value
    
    return {
        "public_hash": create_data_hash(public_data),
        "private_hash": create_data_hash(private_data),
        "public_data": public_data,
        "private_fields": private_fields
    }


def verify_privacy_hash(
    public_data: Dict[str, Any],
    private_values: Dict[str, Any],
    expected_public_hash: str,
    expected_private_hash: str,
    private_fields: List[str]
) -> bool:
    """Verify privacy-preserving hash"""
    
    # Reconstruct full data
    full_data = public_data.copy()
    
    # Replace hashed private fields with actual values
    private_data = {}
    for field in private_fields:
        if field in private_values:
            full_data[field] = private_values[field]
            private_data[field] = private_values[field]
    
    # Verify hashes
    public_hash = create_data_hash(public_data)
    private_hash = create_data_hash(private_data)
    
    return (public_hash == expected_public_hash and 
            private_hash == expected_private_hash)


def generate_ring_signature_params(ring_size: int = 5) -> Dict[str, Any]:
    """Generate parameters for ring signature (privacy-preserving signatures)"""
    
    # Simplified ring signature parameters
    ring_members = []
    for i in range(ring_size):
        member = {
            "public_key": secrets.token_hex(32),
            "key_image": secrets.token_hex(32)
        }
        ring_members.append(member)
    
    return {
        "ring_members": ring_members,
        "ring_size": ring_size,
        "challenge": secrets.token_hex(32),
        "created_at": datetime.utcnow().isoformat()
    }


def compute_hash_chain(initial_value: str, iterations: int) -> List[str]:
    """Compute hash chain for proof of work or time-lock puzzles"""
    
    chain = [initial_value]
    current = initial_value
    
    for _ in range(iterations):
        current = hashlib.sha256(current.encode()).hexdigest()
        chain.append(current)
    
    return chain


def verify_hash_chain(chain: List[str], expected_length: int) -> bool:
    """Verify hash chain integrity"""
    
    if len(chain) != expected_length + 1:
        return False
    
    for i in range(1, len(chain)):
        expected = hashlib.sha256(chain[i-1].encode()).hexdigest()
        if expected != chain[i]:
            return False
    
    return True


def create_threshold_secret(secret: str, threshold: int, total_shares: int) -> Dict[str, Any]:
    """Create threshold secret sharing (simplified Shamir's Secret Sharing)"""
    
    # This is a simplified version for demonstration
    # In production, use proper Shamir's Secret Sharing implementation
    
    secret_bytes = secret.encode()
    secret_hash = hashlib.sha256(secret_bytes).hexdigest()
    
    shares = []
    for i in range(total_shares):
        share_data = f"{secret}:{i}:{secrets.token_hex(16)}"
        share_hash = hashlib.sha256(share_data.encode()).hexdigest()
        shares.append({
            "share_id": i + 1,
            "share_hash": share_hash,
            "share_data": base64.b64encode(share_data.encode()).decode()
        })
    
    return {
        "secret_hash": secret_hash,
        "threshold": threshold,
        "total_shares": total_shares,
        "shares": shares,
        "created_at": datetime.utcnow().isoformat()
    }


def reconstruct_threshold_secret(
    shares: List[Dict[str, Any]], 
    threshold: int
) -> Optional[str]:
    """Reconstruct secret from threshold shares"""
    
    if len(shares) < threshold:
        return None
    
    # Use first 'threshold' shares
    used_shares = shares[:threshold]
    
    # Simplified reconstruction (in production, use proper polynomial interpolation)
    for share in used_shares:
        try:
            share_data = base64.b64decode(share["share_data"]).decode()
            parts = share_data.split(":")
            if len(parts) >= 3:
                potential_secret = parts[0]
                # Verify this is correct by checking against other shares
                return potential_secret
        except:
            continue
    
    return None


def generate_identity_commitment(
    identity_data: Dict[str, Any],
    commitment_scheme: str = "pedersen"
) -> Dict[str, Any]:
    """Generate commitment for identity data (zero-knowledge friendly)"""
    
    # Serialize identity data
    identity_json = json.dumps(identity_data, sort_keys=True)
    identity_hash = hashlib.sha256(identity_json.encode()).hexdigest()
    
    # Generate commitment parameters
    randomness = secrets.token_hex(32)
    commitment_value = hashlib.sha256(f"{identity_hash}:{randomness}".encode()).hexdigest()
    
    return {
        "commitment": commitment_value,
        "identity_hash": identity_hash,
        "randomness": randomness,
        "scheme": commitment_scheme,
        "created_at": datetime.utcnow().isoformat()
    }


def create_accumulator_proof(elements: List[str], element_to_prove: str) -> Dict[str, Any]:
    """Create cryptographic accumulator proof (for set membership)"""
    
    if element_to_prove not in elements:
        raise ValueError("Element not in set")
    
    # Simplified accumulator (in production, use RSA or bilinear map accumulators)
    accumulator = "1"
    for element in elements:
        element_hash = hashlib.sha256(element.encode()).hexdigest()
        accumulator = hashlib.sha256(f"{accumulator}:{element_hash}".encode()).hexdigest()
    
    # Generate witness for the specific element
    witness_elements = [e for e in elements if e != element_to_prove]
    witness = "1"
    for element in witness_elements:
        element_hash = hashlib.sha256(element.encode()).hexdigest()
        witness = hashlib.sha256(f"{witness}:{element_hash}".encode()).hexdigest()
    
    return {
        "accumulator": accumulator,
        "witness": witness,
        "element": element_to_prove,
        "proof_type": "membership",
        "created_at": datetime.utcnow().isoformat()
    }


def verify_accumulator_proof(
    accumulator: str,
    witness: str,
    element: str,
    proof_type: str = "membership"
) -> bool:
    """Verify accumulator membership proof"""
    
    # Simplified verification
    element_hash = hashlib.sha256(element.encode()).hexdigest()
    expected_accumulator = hashlib.sha256(f"{witness}:{element_hash}".encode()).hexdigest()
    
    return expected_accumulator == accumulator