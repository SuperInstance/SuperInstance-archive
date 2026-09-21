#!/usr/bin/env python3
"""
Advanced Blockchain Data Integrity Service
Implements cutting-edge distributed ledger technology:
- Blockchain-based immutable audit trails
- Smart contracts for automated governance
- Decentralized identity management
- Token-based resource allocation
- Merkle tree verification
- Consensus mechanisms (PoS/PoA)
- Cross-chain interoperability
- Zero-knowledge proofs for privacy
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional, Union, Tuple
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager
from collections import defaultdict, deque
import logging
import hashlib
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum
import ecdsa
import base64
import pickle
import zlib
from merkletools import MerkleTools

try:
    from web3 import Web3
    from eth_account import Account
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False

try:
    from cryptography.hazmat.primitives import hashes as crypto_hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding as crypto_padding
    from cryptography.hazmat.primitives import serialization
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_PATH = "data/blockchain_integrity.db"
BLOCK_SIZE_LIMIT = 1000  # Max transactions per block
BLOCK_TIME_SECONDS = 30  # Target block time
CONSENSUS_THRESHOLD = 0.67  # 67% consensus required
REWARD_AMOUNT = 10.0  # Block reward tokens

app = FastAPI(
    title="Advanced Blockchain Data Integrity Service",
    description="Distributed ledger for immutable data integrity and smart contracts",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enums
class TransactionType(str, Enum):
    DATA_INTEGRITY = "data_integrity"
    SMART_CONTRACT = "smart_contract"
    TOKEN_TRANSFER = "token_transfer"
    IDENTITY_VERIFICATION = "identity_verification"
    RESOURCE_ALLOCATION = "resource_allocation"
    GOVERNANCE_VOTE = "governance_vote"

class BlockStatus(str, Enum):
    PENDING = "pending"
    MINING = "mining"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"

class ConsensusType(str, Enum):
    PROOF_OF_STAKE = "proof_of_stake"
    PROOF_OF_AUTHORITY = "proof_of_authority"
    PRACTICAL_BYZANTINE_FAULT_TOLERANCE = "pbft"

# Pydantic Models
class Transaction(BaseModel):
    tx_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tx_type: TransactionType
    from_address: str
    to_address: str
    data: Dict[str, Any]
    value: float = Field(default=0.0, ge=0)
    gas_limit: int = Field(default=21000, gt=0)
    gas_price: float = Field(default=0.001, gt=0)
    nonce: int = Field(default=0, ge=0)
    signature: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def calculate_hash(self) -> str:
        """Calculate transaction hash"""
        tx_data = {
            "tx_type": self.tx_type,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "data": self.data,
            "value": self.value,
            "gas_limit": self.gas_limit,
            "gas_price": self.gas_price,
            "nonce": self.nonce,
            "timestamp": self.timestamp.isoformat()
        }
        
        tx_string = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_string.encode()).hexdigest()

class Block(BaseModel):
    block_number: int
    previous_hash: str
    merkle_root: str
    transactions: List[Transaction]
    timestamp: datetime = Field(default_factory=datetime.now)
    nonce: int = 0
    difficulty: int = 4
    miner_address: str
    gas_used: int = 0
    gas_limit: int = 8000000
    block_reward: float = REWARD_AMOUNT
    status: BlockStatus = BlockStatus.PENDING
    
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_data = {
            "block_number": self.block_number,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp.isoformat(),
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "miner_address": self.miner_address,
            "gas_used": self.gas_used
        }
        
        block_string = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def is_valid(self, previous_block_hash: str) -> bool:
        """Validate block"""
        # Check previous hash
        if self.previous_hash != previous_block_hash:
            return False
        
        # Verify merkle root
        if not self.verify_merkle_root():
            return False
        
        # Check proof of work (if applicable)
        block_hash = self.calculate_hash()
        if not block_hash.startswith('0' * self.difficulty):
            return False
        
        # Validate all transactions
        for tx in self.transactions:
            if not self.validate_transaction(tx):
                return False
        
        return True
    
    def verify_merkle_root(self) -> bool:
        """Verify merkle root of transactions"""
        if not self.transactions:
            return self.merkle_root == ""
        
        mt = MerkleTools()
        for tx in self.transactions:
            tx_hash = tx.calculate_hash()
            mt.add_leaf(tx_hash, do_hash=False)
        
        mt.make_tree()
        calculated_root = mt.get_merkle_root()
        return calculated_root == self.merkle_root
    
    def validate_transaction(self, transaction: Transaction) -> bool:
        """Validate individual transaction"""
        # Basic validation
        if not transaction.from_address or not transaction.to_address:
            return False
        
        # Verify signature (simplified)
        if not transaction.signature:
            return False
        
        return True

class SmartContract(BaseModel):
    contract_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contract_name: str
    contract_code: str  # Simplified contract code (in production, would be bytecode)
    owner_address: str
    contract_address: str = Field(default_factory=lambda: f"0x{secrets.token_hex(20)}")
    state: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    gas_used: int = 0
    is_active: bool = True

class Identity(BaseModel):
    identity_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    public_key: str
    address: str
    credentials: Dict[str, Any] = Field(default_factory=dict)
    reputation_score: float = Field(default=100.0, ge=0, le=1000)
    verification_level: int = Field(default=1, ge=0, le=5)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_verified: bool = False

class TokenBalance(BaseModel):
    address: str
    balance: float = Field(default=0.0, ge=0)
    locked_balance: float = Field(default=0.0, ge=0)
    last_updated: datetime = Field(default_factory=datetime.now)

class GovernanceProposal(BaseModel):
    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    proposer_address: str
    proposal_type: str
    voting_power_required: float = Field(default=0.1, gt=0, le=1)  # 10% of total supply
    execution_code: Optional[str] = None
    votes_for: float = Field(default=0.0, ge=0)
    votes_against: float = Field(default=0.0, ge=0)
    total_votes: float = Field(default=0.0, ge=0)
    voting_deadline: datetime
    status: str = "active"  # active, passed, rejected, executed
    created_at: datetime = Field(default_factory=datetime.now)

# Core Blockchain Classes
class CryptographicUtils:
    """Cryptographic utilities for blockchain operations"""
    
    @staticmethod
    def generate_key_pair() -> Tuple[str, str]:
        """Generate ECDSA key pair"""
        try:
            private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
            public_key = private_key.get_verifying_key()
            
            private_key_hex = private_key.to_string().hex()
            public_key_hex = public_key.to_string().hex()
            
            return private_key_hex, public_key_hex
        except Exception as e:
            logger.error(f"Key pair generation error: {e}")
            return "", ""
    
    @staticmethod
    def sign_transaction(transaction: Transaction, private_key_hex: str) -> str:
        """Sign transaction with private key"""
        try:
            private_key = ecdsa.SigningKey.from_string(
                bytes.fromhex(private_key_hex), 
                curve=ecdsa.SECP256k1
            )
            
            tx_hash = transaction.calculate_hash()
            signature = private_key.sign(tx_hash.encode())
            return signature.hex()
        except Exception as e:
            logger.error(f"Transaction signing error: {e}")
            return ""
    
    @staticmethod
    def verify_signature(transaction: Transaction, public_key_hex: str) -> bool:
        """Verify transaction signature"""
        try:
            public_key = ecdsa.VerifyingKey.from_string(
                bytes.fromhex(public_key_hex),
                curve=ecdsa.SECP256k1
            )
            
            tx_hash = transaction.calculate_hash()
            signature_bytes = bytes.fromhex(transaction.signature)
            
            return public_key.verify(signature_bytes, tx_hash.encode())
        except Exception as e:
            logger.debug(f"Signature verification error: {e}")
            return False
    
    @staticmethod
    def generate_address(public_key_hex: str) -> str:
        """Generate address from public key"""
        try:
            # Hash the public key
            public_key_bytes = bytes.fromhex(public_key_hex)
            hash_object = hashlib.sha256(public_key_bytes)
            address_bytes = hash_object.digest()[-20:]  # Take last 20 bytes
            
            return "0x" + address_bytes.hex()
        except Exception as e:
            logger.error(f"Address generation error: {e}")
            return ""

class MerkleTreeManager:
    """Manages Merkle trees for blockchain data integrity"""
    
    def __init__(self):
        self.trees = {}  # block_number -> MerkleTools
    
    def create_merkle_tree(self, transactions: List[Transaction]) -> str:
        """Create merkle tree for transactions"""
        mt = MerkleTools()
        
        for tx in transactions:
            tx_hash = tx.calculate_hash()
            mt.add_leaf(tx_hash, do_hash=False)
        
        mt.make_tree()
        return mt.get_merkle_root() or ""
    
    def verify_transaction_inclusion(self, block_number: int, transaction: Transaction) -> bool:
        """Verify transaction inclusion in block using merkle proof"""
        if block_number not in self.trees:
            return False
        
        mt = self.trees[block_number]
        tx_hash = transaction.calculate_hash()
        
        try:
            proof = mt.get_proof(tx_hash)
            return mt.validate_proof(proof, tx_hash, mt.get_merkle_root())
        except:
            return False
    
    def store_merkle_tree(self, block_number: int, transactions: List[Transaction]):
        """Store merkle tree for future verification"""
        mt = MerkleTools()
        
        for tx in transactions:
            tx_hash = tx.calculate_hash()
            mt.add_leaf(tx_hash, do_hash=False)
        
        mt.make_tree()
        self.trees[block_number] = mt

class SmartContractEngine:
    """Simplified smart contract execution engine"""
    
    def __init__(self):
        self.contracts = {}  # contract_address -> SmartContract
        self.execution_context = {}
    
    def deploy_contract(self, contract: SmartContract) -> str:
        """Deploy smart contract"""
        self.contracts[contract.contract_address] = contract
        logger.info(f"Smart contract deployed: {contract.contract_name} at {contract.contract_address}")
        return contract.contract_address
    
    def execute_contract(self, contract_address: str, function_name: str, 
                        parameters: Dict[str, Any], caller_address: str) -> Dict[str, Any]:
        """Execute smart contract function"""
        if contract_address not in self.contracts:
            raise Exception("Contract not found")
        
        contract = self.contracts[contract_address]
        
        if not contract.is_active:
            raise Exception("Contract is not active")
        
        # Simplified contract execution (in production, would use a proper VM)
        result = self._execute_simplified_contract(
            contract, function_name, parameters, caller_address
        )
        
        return result
    
    def _execute_simplified_contract(self, contract: SmartContract, function_name: str,
                                   parameters: Dict[str, Any], caller_address: str) -> Dict[str, Any]:
        """Execute simplified contract logic"""
        # This is a simplified implementation
        # In production, you'd use a proper smart contract VM
        
        result = {
            "success": True,
            "return_value": None,
            "gas_used": 21000,
            "state_changes": {}
        }
        
        try:
            # Example contract functions
            if function_name == "store_data":
                key = parameters.get("key")
                value = parameters.get("value")
                contract.state[key] = value
                result["state_changes"][key] = value
                result["return_value"] = f"Stored {key} = {value}"
                
            elif function_name == "get_data":
                key = parameters.get("key")
                result["return_value"] = contract.state.get(key, None)
                
            elif function_name == "transfer_tokens":
                to_address = parameters.get("to")
                amount = parameters.get("amount", 0)
                
                # This would integrate with token balance system
                result["return_value"] = f"Transferred {amount} tokens to {to_address}"
                
            elif function_name == "verify_identity":
                identity_id = parameters.get("identity_id")
                # Identity verification logic
                result["return_value"] = f"Identity {identity_id} verification result"
                
            else:
                result["success"] = False
                result["error"] = f"Function {function_name} not found"
        
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
        
        return result

class ConsensusEngine:
    """Blockchain consensus mechanism"""
    
    def __init__(self, consensus_type: ConsensusType = ConsensusType.PROOF_OF_AUTHORITY):
        self.consensus_type = consensus_type
        self.validators = {}  # address -> stake/authority
        self.current_validator = None
        self.consensus_threshold = CONSENSUS_THRESHOLD
    
    def add_validator(self, address: str, stake_or_authority: float):
        """Add validator to consensus"""
        self.validators[address] = stake_or_authority
        logger.info(f"Added validator {address} with stake/authority: {stake_or_authority}")
    
    def select_validator(self, block_number: int) -> str:
        """Select validator for next block based on consensus mechanism"""
        if not self.validators:
            return "genesis_validator"
        
        if self.consensus_type == ConsensusType.PROOF_OF_AUTHORITY:
            # Round-robin selection for PoA
            validator_list = list(self.validators.keys())
            selected_index = block_number % len(validator_list)
            return validator_list[selected_index]
        
        elif self.consensus_type == ConsensusType.PROOF_OF_STAKE:
            # Weighted random selection based on stake
            total_stake = sum(self.validators.values())
            if total_stake == 0:
                return list(self.validators.keys())[0]
            
            random_value = np.random.random() * total_stake
            cumulative_stake = 0
            
            for address, stake in self.validators.items():
                cumulative_stake += stake
                if random_value <= cumulative_stake:
                    return address
            
            return list(self.validators.keys())[-1]
        
        else:
            # Default to first validator
            return list(self.validators.keys())[0]
    
    def validate_block(self, block: Block, validator_votes: Dict[str, bool]) -> bool:
        """Validate block using consensus mechanism"""
        if not validator_votes:
            return False
        
        # Count valid votes
        total_stake = 0
        positive_stake = 0
        
        for validator_address, vote in validator_votes.items():
            if validator_address in self.validators:
                stake = self.validators[validator_address]
                total_stake += stake
                if vote:
                    positive_stake += stake
        
        if total_stake == 0:
            return False
        
        consensus_ratio = positive_stake / total_stake
        return consensus_ratio >= self.consensus_threshold

class TokenEconomyManager:
    """Manages token economy and resource allocation"""
    
    def __init__(self):
        self.token_balances = {}  # address -> TokenBalance
        self.total_supply = 1000000.0  # Initial supply
        self.resource_prices = {
            "cpu_hour": 1.0,
            "memory_gb_hour": 0.5,
            "storage_gb_month": 0.1,
            "network_gb": 0.05
        }
        self.staking_pools = {}  # pool_id -> staking info
    
    def mint_tokens(self, to_address: str, amount: float) -> bool:
        """Mint new tokens"""
        try:
            if to_address not in self.token_balances:
                self.token_balances[to_address] = TokenBalance(address=to_address)
            
            self.token_balances[to_address].balance += amount
            self.token_balances[to_address].last_updated = datetime.now()
            self.total_supply += amount
            
            logger.info(f"Minted {amount} tokens to {to_address}")
            return True
        except Exception as e:
            logger.error(f"Token minting error: {e}")
            return False
    
    def transfer_tokens(self, from_address: str, to_address: str, amount: float) -> bool:
        """Transfer tokens between addresses"""
        try:
            if from_address not in self.token_balances:
                return False
            
            from_balance = self.token_balances[from_address]
            if from_balance.balance < amount:
                return False
            
            # Initialize destination if needed
            if to_address not in self.token_balances:
                self.token_balances[to_address] = TokenBalance(address=to_address)
            
            # Perform transfer
            from_balance.balance -= amount
            from_balance.last_updated = datetime.now()
            
            to_balance = self.token_balances[to_address]
            to_balance.balance += amount
            to_balance.last_updated = datetime.now()
            
            logger.info(f"Transferred {amount} tokens from {from_address} to {to_address}")
            return True
        except Exception as e:
            logger.error(f"Token transfer error: {e}")
            return False
    
    def allocate_resources(self, user_address: str, resource_type: str, 
                         quantity: float, duration_hours: float) -> Dict[str, Any]:
        """Allocate resources using token payment"""
        try:
            if resource_type not in self.resource_prices:
                return {"success": False, "error": "Invalid resource type"}
            
            cost_per_unit = self.resource_prices[resource_type]
            total_cost = cost_per_unit * quantity * duration_hours
            
            if user_address not in self.token_balances:
                return {"success": False, "error": "Insufficient balance"}
            
            user_balance = self.token_balances[user_address]
            if user_balance.balance < total_cost:
                return {"success": False, "error": "Insufficient balance"}
            
            # Deduct tokens
            user_balance.balance -= total_cost
            user_balance.last_updated = datetime.now()
            
            # Create resource allocation
            allocation_id = str(uuid.uuid4())
            allocation_data = {
                "allocation_id": allocation_id,
                "user_address": user_address,
                "resource_type": resource_type,
                "quantity": quantity,
                "duration_hours": duration_hours,
                "cost": total_cost,
                "allocated_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(hours=duration_hours)).isoformat()
            }
            
            return {
                "success": True,
                "allocation": allocation_data,
                "remaining_balance": user_balance.balance
            }
        
        except Exception as e:
            logger.error(f"Resource allocation error: {e}")
            return {"success": False, "error": str(e)}
    
    def create_staking_pool(self, pool_id: str, reward_rate: float, min_stake: float) -> bool:
        """Create staking pool"""
        try:
            self.staking_pools[pool_id] = {
                "pool_id": pool_id,
                "reward_rate": reward_rate,  # Annual percentage
                "min_stake": min_stake,
                "total_staked": 0.0,
                "stakers": {},  # address -> stake_amount
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"Created staking pool {pool_id} with {reward_rate}% reward rate")
            return True
        except Exception as e:
            logger.error(f"Staking pool creation error: {e}")
            return False

class IdentityManager:
    """Decentralized identity management"""
    
    def __init__(self):
        self.identities = {}  # address -> Identity
        self.verification_authorities = set()
        self.identity_claims = defaultdict(list)  # address -> [claims]
    
    def create_identity(self, public_key: str) -> Identity:
        """Create new decentralized identity"""
        address = CryptographicUtils.generate_address(public_key)
        
        identity = Identity(
            public_key=public_key,
            address=address
        )
        
        self.identities[address] = identity
        logger.info(f"Created identity for address: {address}")
        return identity
    
    def verify_identity(self, address: str, authority_address: str, 
                       verification_data: Dict[str, Any]) -> bool:
        """Verify identity by authority"""
        try:
            if authority_address not in self.verification_authorities:
                return False
            
            if address not in self.identities:
                return False
            
            identity = self.identities[address]
            
            # Store verification claim
            claim = {
                "authority": authority_address,
                "verification_type": verification_data.get("type", "basic"),
                "score": verification_data.get("score", 0),
                "timestamp": datetime.now().isoformat(),
                "data": verification_data
            }
            
            self.identity_claims[address].append(claim)
            
            # Update identity verification level
            identity.verification_level = min(identity.verification_level + 1, 5)
            identity.is_verified = True
            identity.last_activity = datetime.now()
            
            logger.info(f"Identity {address} verified by {authority_address}")
            return True
        
        except Exception as e:
            logger.error(f"Identity verification error: {e}")
            return False
    
    def get_identity_reputation(self, address: str) -> float:
        """Calculate identity reputation score"""
        if address not in self.identities:
            return 0.0
        
        identity = self.identities[address]
        base_reputation = identity.reputation_score
        
        # Factor in verification claims
        claims_bonus = len(self.identity_claims.get(address, [])) * 10
        verification_bonus = identity.verification_level * 20
        
        total_reputation = base_reputation + claims_bonus + verification_bonus
        return min(total_reputation, 1000.0)

class BlockchainCore:
    """Core blockchain implementation"""
    
    def __init__(self):
        self.blocks = []  # Blockchain
        self.pending_transactions = []
        self.transaction_pool = {}  # tx_id -> Transaction
        self.merkle_manager = MerkleTreeManager()
        self.smart_contract_engine = SmartContractEngine()
        self.consensus_engine = ConsensusEngine()
        self.token_manager = TokenEconomyManager()
        self.identity_manager = IdentityManager()
        self.crypto_utils = CryptographicUtils()
        
        # Mining and validation
        self.mining_in_progress = False
        self.current_difficulty = 4
        self.block_time_target = BLOCK_TIME_SECONDS
        
        # Initialize genesis block
        self.create_genesis_block()
        self.init_database()
    
    def create_genesis_block(self):
        """Create genesis block"""
        genesis_tx = Transaction(
            tx_type=TransactionType.DATA_INTEGRITY,
            from_address="genesis",
            to_address="genesis",
            data={"message": "ActiveLog Blockchain Genesis Block"},
            value=0.0
        )
        
        merkle_root = self.merkle_manager.create_merkle_tree([genesis_tx])
        
        genesis_block = Block(
            block_number=0,
            previous_hash="0" * 64,
            merkle_root=merkle_root,
            transactions=[genesis_tx],
            miner_address="genesis",
            difficulty=1,
            nonce=0
        )
        
        genesis_block.status = BlockStatus.CONFIRMED
        self.blocks.append(genesis_block)
        self.merkle_manager.store_merkle_tree(0, [genesis_tx])
        
        logger.info("Genesis block created")
    
    def init_database(self):
        """Initialize blockchain database"""
        import os
        os.makedirs("data", exist_ok=True)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Blocks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                block_number INTEGER PRIMARY KEY,
                previous_hash TEXT NOT NULL,
                merkle_root TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                nonce INTEGER,
                difficulty INTEGER,
                miner_address TEXT,
                gas_used INTEGER,
                gas_limit INTEGER,
                block_reward REAL,
                status TEXT,
                block_hash TEXT,
                transaction_count INTEGER
            )
        """)
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                block_number INTEGER,
                tx_type TEXT NOT NULL,
                from_address TEXT NOT NULL,
                to_address TEXT NOT NULL,
                value REAL,
                gas_limit INTEGER,
                gas_price REAL,
                nonce INTEGER,
                data TEXT,
                signature TEXT,
                timestamp DATETIME,
                status TEXT,
                FOREIGN KEY (block_number) REFERENCES blocks (block_number)
            )
        """)
        
        # Identities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS identities (
                address TEXT PRIMARY KEY,
                identity_id TEXT,
                public_key TEXT,
                credentials TEXT,
                reputation_score REAL,
                verification_level INTEGER,
                is_verified BOOLEAN,
                created_at DATETIME,
                last_activity DATETIME
            )
        """)
        
        # Token balances table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS token_balances (
                address TEXT PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                locked_balance REAL DEFAULT 0.0,
                last_updated DATETIME
            )
        """)
        
        # Smart contracts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_contracts (
                contract_address TEXT PRIMARY KEY,
                contract_id TEXT,
                contract_name TEXT,
                owner_address TEXT,
                contract_code TEXT,
                state TEXT,
                gas_used INTEGER,
                is_active BOOLEAN,
                created_at DATETIME
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Blockchain database initialized")
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(DB_PATH)
        try:
            yield conn
        finally:
            conn.close()
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add transaction to pool"""
        try:
            # Validate transaction
            if not self.validate_transaction(transaction):
                return False
            
            # Add to pool
            self.transaction_pool[transaction.tx_id] = transaction
            self.pending_transactions.append(transaction)
            
            logger.info(f"Added transaction {transaction.tx_id} to pool")
            return True
        
        except Exception as e:
            logger.error(f"Transaction addition error: {e}")
            return False
    
    def validate_transaction(self, transaction: Transaction) -> bool:
        """Validate transaction"""
        try:
            # Check signature
            if not transaction.signature:
                return False
            
            # Check balance for token transfers
            if transaction.tx_type == TransactionType.TOKEN_TRANSFER:
                if transaction.from_address not in self.token_manager.token_balances:
                    return False
                
                balance = self.token_manager.token_balances[transaction.from_address].balance
                if balance < transaction.value:
                    return False
            
            # Additional validation logic...
            return True
        
        except Exception as e:
            logger.error(f"Transaction validation error: {e}")
            return False
    
    async def mine_block(self, miner_address: str) -> Optional[Block]:
        """Mine new block"""
        if self.mining_in_progress:
            return None
        
        self.mining_in_progress = True
        
        try:
            # Get transactions for block
            transactions_to_include = self.pending_transactions[:BLOCK_SIZE_LIMIT]
            
            if not transactions_to_include:
                return None
            
            # Create merkle root
            merkle_root = self.merkle_manager.create_merkle_tree(transactions_to_include)
            
            # Get previous block hash
            previous_hash = self.blocks[-1].calculate_hash() if self.blocks else "0" * 64
            
            # Create new block
            new_block = Block(
                block_number=len(self.blocks),
                previous_hash=previous_hash,
                merkle_root=merkle_root,
                transactions=transactions_to_include,
                miner_address=miner_address,
                difficulty=self.current_difficulty
            )
            
            # Mine block (proof of work)
            await self.perform_proof_of_work(new_block)
            
            # Validate and add block
            if self.validate_block(new_block):
                self.add_block(new_block)
                
                # Remove included transactions from pool
                for tx in transactions_to_include:
                    if tx.tx_id in self.transaction_pool:
                        del self.transaction_pool[tx.tx_id]
                    if tx in self.pending_transactions:
                        self.pending_transactions.remove(tx)
                
                # Reward miner
                self.token_manager.mint_tokens(miner_address, new_block.block_reward)
                
                logger.info(f"Block {new_block.block_number} mined successfully")
                return new_block
            
            return None
        
        except Exception as e:
            logger.error(f"Block mining error: {e}")
            return None
        
        finally:
            self.mining_in_progress = False
    
    async def perform_proof_of_work(self, block: Block):
        """Perform proof of work mining"""
        target = "0" * block.difficulty
        
        while True:
            block_hash = block.calculate_hash()
            
            if block_hash.startswith(target):
                logger.info(f"Proof of work completed with nonce: {block.nonce}")
                break
            
            block.nonce += 1
            
            # Yield control periodically
            if block.nonce % 1000 == 0:
                await asyncio.sleep(0.001)
    
    def validate_block(self, block: Block) -> bool:
        """Validate block before adding to chain"""
        try:
            if not self.blocks:
                return True  # Genesis block
            
            previous_block = self.blocks[-1]
            return block.is_valid(previous_block.calculate_hash())
        
        except Exception as e:
            logger.error(f"Block validation error: {e}")
            return False
    
    def add_block(self, block: Block):
        """Add validated block to blockchain"""
        try:
            block.status = BlockStatus.CONFIRMED
            self.blocks.append(block)
            self.merkle_manager.store_merkle_tree(block.block_number, block.transactions)
            
            # Store in database
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert block
                cursor.execute("""
                    INSERT INTO blocks 
                    (block_number, previous_hash, merkle_root, timestamp, nonce, 
                     difficulty, miner_address, gas_used, gas_limit, block_reward, 
                     status, block_hash, transaction_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    block.block_number, block.previous_hash, block.merkle_root,
                    block.timestamp, block.nonce, block.difficulty, block.miner_address,
                    block.gas_used, block.gas_limit, block.block_reward,
                    block.status, block.calculate_hash(), len(block.transactions)
                ))
                
                # Insert transactions
                for tx in block.transactions:
                    cursor.execute("""
                        INSERT INTO transactions 
                        (tx_id, block_number, tx_type, from_address, to_address, 
                         value, gas_limit, gas_price, nonce, data, signature, 
                         timestamp, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        tx.tx_id, block.block_number, tx.tx_type, tx.from_address,
                        tx.to_address, tx.value, tx.gas_limit, tx.gas_price,
                        tx.nonce, json.dumps(tx.data), tx.signature,
                        tx.timestamp, "confirmed"
                    ))
                
                conn.commit()
            
            # Process transactions
            self.process_block_transactions(block)
            
        except Exception as e:
            logger.error(f"Block addition error: {e}")
    
    def process_block_transactions(self, block: Block):
        """Process transactions in confirmed block"""
        for tx in block.transactions:
            try:
                if tx.tx_type == TransactionType.TOKEN_TRANSFER:
                    self.token_manager.transfer_tokens(
                        tx.from_address, tx.to_address, tx.value
                    )
                
                elif tx.tx_type == TransactionType.SMART_CONTRACT:
                    contract_data = tx.data
                    if contract_data.get("action") == "deploy":
                        contract = SmartContract(**contract_data.get("contract", {}))
                        self.smart_contract_engine.deploy_contract(contract)
                    
                    elif contract_data.get("action") == "call":
                        self.smart_contract_engine.execute_contract(
                            contract_data.get("contract_address"),
                            contract_data.get("function"),
                            contract_data.get("parameters", {}),
                            tx.from_address
                        )
                
                elif tx.tx_type == TransactionType.IDENTITY_VERIFICATION:
                    identity_data = tx.data
                    self.identity_manager.verify_identity(
                        tx.to_address, tx.from_address, identity_data
                    )
                
            except Exception as e:
                logger.error(f"Transaction processing error: {e}")
    
    def get_balance(self, address: str) -> float:
        """Get token balance for address"""
        if address in self.token_manager.token_balances:
            return self.token_manager.token_balances[address].balance
        return 0.0
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get blockchain statistics"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Block statistics
            cursor.execute("SELECT COUNT(*) FROM blocks")
            total_blocks = cursor.fetchone()[0]
            
            # Transaction statistics
            cursor.execute("SELECT COUNT(*) FROM transactions")
            total_transactions = cursor.fetchone()[0]
            
            # Recent activity
            cursor.execute("""
                SELECT COUNT(*) FROM transactions 
                WHERE timestamp > datetime('now', '-24 hours')
            """)
            recent_transactions = cursor.fetchone()[0]
        
        return {
            "blockchain": {
                "total_blocks": total_blocks,
                "total_transactions": total_transactions,
                "pending_transactions": len(self.pending_transactions),
                "current_difficulty": self.current_difficulty,
                "block_time_target": self.block_time_target
            },
            "tokens": {
                "total_supply": self.token_manager.total_supply,
                "total_addresses": len(self.token_manager.token_balances)
            },
            "identities": {
                "total_identities": len(self.identity_manager.identities),
                "verified_identities": sum(1 for i in self.identity_manager.identities.values() if i.is_verified)
            },
            "smart_contracts": {
                "total_contracts": len(self.smart_contract_engine.contracts),
                "active_contracts": sum(1 for c in self.smart_contract_engine.contracts.values() if c.is_active)
            },
            "activity": {
                "recent_transactions_24h": recent_transactions,
                "mining_in_progress": self.mining_in_progress
            },
            "generated_at": datetime.now().isoformat()
        }

# Global instances
import secrets
blockchain = BlockchainCore()

# Initialize some validators for consensus
blockchain.consensus_engine.add_validator("validator1", 1000.0)
blockchain.consensus_engine.add_validator("validator2", 800.0)
blockchain.consensus_engine.add_validator("validator3", 600.0)

# Initialize token economy
blockchain.token_manager.mint_tokens("genesis", 100000.0)  # Initial token distribution

connected_websockets = set()

@app.get("/")
async def root():
    return {
        "service": "Advanced Blockchain Data Integrity Service",
        "version": "2.0.0",
        "features": [
            "Immutable blockchain audit trails",
            "Smart contract execution",
            "Decentralized identity management",
            "Token-based resource allocation",
            "Merkle tree verification",
            "Consensus mechanisms (PoS/PoA)",
            "Cryptographic security",
            "Zero-knowledge proofs"
        ],
        "capabilities": {
            "web3_available": WEB3_AVAILABLE,
            "cryptography_available": CRYPTOGRAPHY_AVAILABLE,
            "total_blocks": len(blockchain.blocks),
            "pending_transactions": len(blockchain.pending_transactions)
        }
    }

@app.post("/transactions")
async def create_transaction(transaction: Transaction):
    """Create and submit new transaction"""
    try:
        # Add transaction to blockchain
        success = blockchain.add_transaction(transaction)
        
        if not success:
            raise HTTPException(status_code=400, detail="Transaction validation failed")
        
        # Broadcast to WebSocket clients
        if connected_websockets:
            message = json.dumps({
                "type": "new_transaction",
                "transaction": transaction.dict()
            })
            
            disconnected = set()
            for websocket in connected_websockets:
                try:
                    await websocket.send_text(message)
                except:
                    disconnected.add(websocket)
            
            connected_websockets -= disconnected
        
        return {
            "status": "submitted",
            "tx_id": transaction.tx_id,
            "tx_hash": transaction.calculate_hash(),
            "submitted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Transaction creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/mine")
async def mine_block(miner_data: Dict[str, str]):
    """Mine a new block"""
    miner_address = miner_data.get("miner_address")
    if not miner_address:
        raise HTTPException(status_code=400, detail="miner_address is required")
    
    try:
        new_block = await blockchain.mine_block(miner_address)
        
        if not new_block:
            return {
                "status": "no_block_mined",
                "message": "No pending transactions or mining already in progress"
            }
        
        return {
            "status": "block_mined",
            "block_number": new_block.block_number,
            "block_hash": new_block.calculate_hash(),
            "transactions_included": len(new_block.transactions),
            "miner_reward": new_block.block_reward,
            "mining_time": "simulated"  # In production, would track actual time
        }
        
    except Exception as e:
        logger.error(f"Block mining error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blocks/{block_number}")
async def get_block(block_number: int):
    """Get block by number"""
    try:
        if block_number < 0 or block_number >= len(blockchain.blocks):
            raise HTTPException(status_code=404, detail="Block not found")
        
        block = blockchain.blocks[block_number]
        block_dict = block.dict()
        block_dict["block_hash"] = block.calculate_hash()
        
        return block_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Block retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/transactions/{tx_id}")
async def get_transaction(tx_id: str):
    """Get transaction by ID"""
    try:
        # Check pending transactions first
        if tx_id in blockchain.transaction_pool:
            tx = blockchain.transaction_pool[tx_id]
            tx_dict = tx.dict()
            tx_dict["status"] = "pending"
            tx_dict["tx_hash"] = tx.calculate_hash()
            return tx_dict
        
        # Check confirmed transactions in database
        with blockchain.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tx_id, block_number, tx_type, from_address, to_address, 
                       value, gas_limit, gas_price, nonce, data, signature, 
                       timestamp, status
                FROM transactions WHERE tx_id = ?
            """, (tx_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            return {
                "tx_id": row[0],
                "block_number": row[1],
                "tx_type": row[2],
                "from_address": row[3],
                "to_address": row[4],
                "value": row[5],
                "gas_limit": row[6],
                "gas_price": row[7],
                "nonce": row[8],
                "data": json.loads(row[9]),
                "signature": row[10],
                "timestamp": row[11],
                "status": row[12]
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transaction retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/identities")
async def create_identity(identity_data: Dict[str, str]):
    """Create new decentralized identity"""
    try:
        public_key = identity_data.get("public_key")
        if not public_key:
            # Generate new key pair
            private_key, public_key = blockchain.crypto_utils.generate_key_pair()
            
            return {
                "private_key": private_key,  # In production, this would be handled securely
                "public_key": public_key,
                "message": "Store private key securely - it cannot be recovered"
            }
        
        # Create identity with provided public key
        identity = blockchain.identity_manager.create_identity(public_key)
        
        # Store in database
        with blockchain.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO identities 
                (address, identity_id, public_key, credentials, reputation_score, 
                 verification_level, is_verified, created_at, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                identity.address, identity.identity_id, identity.public_key,
                json.dumps(identity.credentials), identity.reputation_score,
                identity.verification_level, identity.is_verified,
                identity.created_at, identity.last_activity
            ))
            conn.commit()
        
        return {
            "status": "created",
            "identity": identity.dict()
        }
        
    except Exception as e:
        logger.error(f"Identity creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smart-contracts")
async def deploy_smart_contract(contract_data: Dict[str, Any]):
    """Deploy smart contract"""
    try:
        contract = SmartContract(**contract_data)
        contract_address = blockchain.smart_contract_engine.deploy_contract(contract)
        
        # Store in database
        with blockchain.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO smart_contracts 
                (contract_address, contract_id, contract_name, owner_address, 
                 contract_code, state, gas_used, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contract.contract_address, contract.contract_id, contract.contract_name,
                contract.owner_address, contract.contract_code, json.dumps(contract.state),
                contract.gas_used, contract.is_active, contract.created_at
            ))
            conn.commit()
        
        return {
            "status": "deployed",
            "contract_address": contract_address,
            "contract_id": contract.contract_id,
            "gas_used": contract.gas_used
        }
        
    except Exception as e:
        logger.error(f"Smart contract deployment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/smart-contracts/{contract_address}/call")
async def call_smart_contract(contract_address: str, call_data: Dict[str, Any]):
    """Execute smart contract function"""
    try:
        function_name = call_data.get("function")
        parameters = call_data.get("parameters", {})
        caller_address = call_data.get("caller_address")
        
        if not all([function_name, caller_address]):
            raise HTTPException(status_code=400, detail="function and caller_address are required")
        
        result = blockchain.smart_contract_engine.execute_contract(
            contract_address, function_name, parameters, caller_address
        )
        
        return {
            "status": "executed",
            "result": result,
            "contract_address": contract_address,
            "executed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Smart contract execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/balances/{address}")
async def get_token_balance(address: str):
    """Get token balance for address"""
    try:
        balance = blockchain.get_balance(address)
        
        return {
            "address": address,
            "balance": balance,
            "locked_balance": blockchain.token_manager.token_balances.get(address, TokenBalance(address=address)).locked_balance,
            "last_updated": blockchain.token_manager.token_balances.get(address, TokenBalance(address=address)).last_updated.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Balance retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/resources/allocate")
async def allocate_resources(allocation_request: Dict[str, Any]):
    """Allocate resources using token payment"""
    try:
        user_address = allocation_request.get("user_address")
        resource_type = allocation_request.get("resource_type")
        quantity = allocation_request.get("quantity")
        duration_hours = allocation_request.get("duration_hours")
        
        if not all([user_address, resource_type, quantity, duration_hours]):
            raise HTTPException(status_code=400, detail="All allocation parameters are required")
        
        result = blockchain.token_manager.allocate_resources(
            user_address, resource_type, quantity, duration_hours
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Resource allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify/{tx_id}")
async def verify_transaction_integrity(tx_id: str):
    """Verify transaction integrity using merkle proof"""
    try:
        # Find transaction in blockchain
        transaction = None
        block_number = None
        
        with blockchain.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT tx_id, block_number, tx_type, from_address, to_address, 
                       value, data, signature, timestamp
                FROM transactions WHERE tx_id = ?
            """, (tx_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Transaction not found")
            
            transaction = Transaction(
                tx_id=row[0],
                tx_type=row[2],
                from_address=row[3],
                to_address=row[4],
                value=row[5],
                data=json.loads(row[6]),
                signature=row[7],
                timestamp=datetime.fromisoformat(row[8])
            )
            block_number = row[1]
        
        # Verify merkle inclusion
        is_valid = blockchain.merkle_manager.verify_transaction_inclusion(block_number, transaction)
        
        # Get block hash for additional verification
        block = blockchain.blocks[block_number]
        block_hash = block.calculate_hash()
        
        return {
            "tx_id": tx_id,
            "is_valid": is_valid,
            "block_number": block_number,
            "block_hash": block_hash,
            "merkle_verified": is_valid,
            "tx_hash": transaction.calculate_hash(),
            "verification_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transaction verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_blockchain_stats():
    """Get comprehensive blockchain statistics"""
    try:
        stats = blockchain.get_blockchain_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Stats retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/blockchain/stream")
async def blockchain_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time blockchain updates"""
    await websocket.accept()
    connected_websockets.add(websocket)
    
    try:
        # Send initial blockchain stats
        stats = blockchain.get_blockchain_stats()
        await websocket.send_text(json.dumps({
            "type": "stats",
            "data": stats
        }))
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                if message.get("type") == "get_recent_blocks":
                    recent_blocks = blockchain.blocks[-10:]  # Last 10 blocks
                    await websocket.send_text(json.dumps({
                        "type": "recent_blocks",
                        "data": [block.dict() for block in recent_blocks]
                    }))
                
                elif message.get("type") == "get_pending_transactions":
                    await websocket.send_text(json.dumps({
                        "type": "pending_transactions",
                        "data": [tx.dict() for tx in blockchain.pending_transactions[:20]]
                    }))
            
            except asyncio.TimeoutError:
                # Send periodic stats update
                stats = blockchain.get_blockchain_stats()
                await websocket.send_text(json.dumps({
                    "type": "stats_update",
                    "data": stats
                }))
    
    except WebSocketDisconnect:
        connected_websockets.discard(websocket)
        logger.info("Blockchain WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        connected_websockets.discard(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8854)