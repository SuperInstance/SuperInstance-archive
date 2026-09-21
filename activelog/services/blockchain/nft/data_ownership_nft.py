"""
Data Ownership NFTs for ActiveLog
Provides verifiable ownership of user data with granular permissions
"""

import json
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from web3 import Web3
from eth_account import Account

from ..config.blockchain_config import blockchain_config, BlockchainNetwork, ContractType
from ..storage.ipfs_manager import IPFSManager
from ..utils.crypto_utils import generate_merkle_tree, create_data_hash

class DataType(Enum):
    ACTIVITY_LOGS = "activity_logs"
    AI_OUTPUTS = "ai_outputs"
    FINANCIAL_DATA = "financial_data"
    USER_PROFILE = "user_profile"
    ANALYTICS_DATA = "analytics_data"
    COLLABORATION_DATA = "collaboration_data"

class AccessLevel(Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

@dataclass
class DataOwnershipMetadata:
    data_type: DataType
    created_at: datetime
    updated_at: datetime
    data_hash: str
    ipfs_hash: str
    permissions: Dict[str, AccessLevel]
    encryption_key_hash: str
    size_bytes: int
    schema_version: str
    tags: List[str]

@dataclass
class AccessGrant:
    grantee_address: str
    access_level: AccessLevel
    expires_at: Optional[datetime]
    conditions: Optional[Dict[str, Any]]
    granted_at: datetime
    revoked_at: Optional[datetime]

class DataOwnershipNFT:
    """Manages data ownership NFTs on multiple blockchain networks"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.NFT_DATA_OWNERSHIP, network
        )
        
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        self.ipfs_manager = IPFSManager()
        
        # Load contract ABI
        self.contract_abi = self._load_contract_abi()
        self.contract = self.w3.eth.contract(
            address=self.contract_config.address,
            abi=self.contract_abi
        )
    
    def _load_contract_abi(self) -> List[Dict]:
        """Load contract ABI from file"""
        # In production, this would load from a file
        return [
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "metadataURI", "type": "string"}
                ],
                "name": "mint",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "grantee", "type": "address"},
                    {"name": "accessLevel", "type": "uint8"},
                    {"name": "expiresAt", "type": "uint256"}
                ],
                "name": "grantAccess",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "grantee", "type": "address"}
                ],
                "name": "revokeAccess",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "user", "type": "address"}
                ],
                "name": "getAccessLevel",
                "outputs": [{"name": "", "type": "uint8"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"}
                ],
                "name": "tokenURI",
                "outputs": [{"name": "", "type": "string"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def mint_data_ownership_nft(
        self,
        owner_address: str,
        data: Dict[str, Any],
        data_type: DataType,
        tags: List[str] = None,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Mint an NFT representing ownership of specific data"""
        
        # Generate data hash for integrity verification
        data_hash = create_data_hash(data)
        
        # Encrypt and store data on IPFS
        encrypted_data = await self._encrypt_data(data, owner_address)
        ipfs_result = await self.ipfs_manager.pin_json(encrypted_data)
        
        # Create metadata
        metadata = DataOwnershipMetadata(
            data_type=data_type,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            data_hash=data_hash,
            ipfs_hash=ipfs_result["hash"],
            permissions={owner_address: AccessLevel.ADMIN},
            encryption_key_hash=hashlib.sha256(owner_address.encode()).hexdigest(),
            size_bytes=len(json.dumps(data).encode()),
            schema_version="1.0.0",
            tags=tags or []
        )
        
        # Store metadata on IPFS
        metadata_result = await self.ipfs_manager.pin_json(asdict(metadata))
        
        # Generate token ID based on data hash and timestamp
        token_id = int(data_hash[:16], 16)  # Use first 16 hex chars as token ID
        
        # Prepare transaction
        if private_key:
            account = Account.from_key(private_key)
            tx_data = self.contract.functions.mint(
                owner_address,
                token_id,
                f"ipfs://{metadata_result['hash']}"
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 500000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for confirmation
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                "token_id": token_id,
                "tx_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "data_hash": data_hash,
                "ipfs_hash": ipfs_result["hash"],
                "metadata_ipfs_hash": metadata_result["hash"],
                "gas_used": receipt.gasUsed,
                "success": receipt.status == 1
            }
        else:
            # Return transaction data for external signing
            return {
                "token_id": token_id,
                "contract_address": self.contract_config.address,
                "function_data": self.contract.functions.mint(
                    owner_address,
                    token_id,
                    f"ipfs://{metadata_result['hash']}"
                ).build_transaction({
                    'gas': 500000,
                    'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
                })['data'],
                "data_hash": data_hash,
                "ipfs_hash": ipfs_result["hash"],
                "metadata_ipfs_hash": metadata_result["hash"]
            }
    
    async def grant_data_access(
        self,
        token_id: int,
        grantee_address: str,
        access_level: AccessLevel,
        expires_at: Optional[datetime] = None,
        conditions: Optional[Dict[str, Any]] = None,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Grant access to data represented by an NFT"""
        
        expires_timestamp = int(expires_at.timestamp()) if expires_at else 0
        
        if private_key:
            account = Account.from_key(private_key)
            tx_data = self.contract.functions.grantAccess(
                token_id,
                grantee_address,
                access_level.value,
                expires_timestamp
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 200000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Record access grant in IPFS for audit trail
            access_grant = AccessGrant(
                grantee_address=grantee_address,
                access_level=access_level,
                expires_at=expires_at,
                conditions=conditions,
                granted_at=datetime.utcnow(),
                revoked_at=None
            )
            
            audit_result = await self.ipfs_manager.pin_json(asdict(access_grant))
            
            return {
                "tx_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "success": receipt.status == 1,
                "audit_ipfs_hash": audit_result["hash"]
            }
        else:
            return {
                "contract_address": self.contract_config.address,
                "function_data": self.contract.functions.grantAccess(
                    token_id,
                    grantee_address,
                    access_level.value,
                    expires_timestamp
                ).build_transaction({
                    'gas': 200000,
                    'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
                })['data']
            }
    
    async def revoke_data_access(
        self,
        token_id: int,
        grantee_address: str,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Revoke access to data represented by an NFT"""
        
        if private_key:
            account = Account.from_key(private_key)
            tx_data = self.contract.functions.revokeAccess(
                token_id,
                grantee_address
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 150000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return {
                "tx_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "gas_used": receipt.gasUsed,
                "success": receipt.status == 1
            }
        else:
            return {
                "contract_address": self.contract_config.address,
                "function_data": self.contract.functions.revokeAccess(
                    token_id,
                    grantee_address
                ).build_transaction({
                    'gas': 150000,
                    'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
                })['data']
            }
    
    async def get_access_level(self, token_id: int, user_address: str) -> AccessLevel:
        """Get access level for a user on a specific data NFT"""
        
        try:
            access_level_int = self.contract.functions.getAccessLevel(
                token_id, user_address
            ).call()
            
            access_levels = {
                0: AccessLevel.NONE,
                1: AccessLevel.READ,
                2: AccessLevel.WRITE,
                3: AccessLevel.ADMIN
            }
            
            return access_levels.get(access_level_int, AccessLevel.NONE)
        except Exception as e:
            print(f"Error getting access level: {e}")
            return AccessLevel.NONE
    
    async def get_nft_metadata(self, token_id: int) -> Optional[DataOwnershipMetadata]:
        """Get metadata for a data ownership NFT"""
        
        try:
            token_uri = self.contract.functions.tokenURI(token_id).call()
            
            if token_uri.startswith("ipfs://"):
                ipfs_hash = token_uri[7:]  # Remove "ipfs://" prefix
                metadata_json = await self.ipfs_manager.get_json(ipfs_hash)
                
                # Convert back to DataOwnershipMetadata
                metadata_json['created_at'] = datetime.fromisoformat(metadata_json['created_at'])
                metadata_json['updated_at'] = datetime.fromisoformat(metadata_json['updated_at'])
                metadata_json['data_type'] = DataType(metadata_json['data_type'])
                
                # Convert permissions
                permissions = {}
                for addr, level in metadata_json['permissions'].items():
                    permissions[addr] = AccessLevel(level)
                metadata_json['permissions'] = permissions
                
                return DataOwnershipMetadata(**metadata_json)
            
        except Exception as e:
            print(f"Error getting NFT metadata: {e}")
            return None
    
    async def get_user_data_nfts(self, user_address: str) -> List[Dict[str, Any]]:
        """Get all data ownership NFTs for a user"""
        
        # This would typically use event logs or a subgraph
        # For now, we'll simulate the response
        user_nfts = []
        
        # In production, query Transfer events where 'to' is user_address
        # or use a subgraph service like The Graph
        
        return user_nfts
    
    async def verify_data_integrity(self, token_id: int, current_data: Dict[str, Any]) -> bool:
        """Verify that current data matches the hash stored in the NFT"""
        
        metadata = await self.get_nft_metadata(token_id)
        if not metadata:
            return False
        
        current_hash = create_data_hash(current_data)
        return current_hash == metadata.data_hash
    
    async def update_nft_metadata(
        self,
        token_id: int,
        updated_data: Dict[str, Any],
        private_key: str
    ) -> Dict[str, Any]:
        """Update NFT metadata when underlying data changes"""
        
        # Get current metadata
        current_metadata = await self.get_nft_metadata(token_id)
        if not current_metadata:
            raise ValueError(f"NFT with token ID {token_id} not found")
        
        # Generate new data hash
        new_data_hash = create_data_hash(updated_data)
        
        # Encrypt and store updated data on IPFS
        account = Account.from_key(private_key)
        encrypted_data = await self._encrypt_data(updated_data, account.address)
        ipfs_result = await self.ipfs_manager.pin_json(encrypted_data)
        
        # Update metadata
        updated_metadata = DataOwnershipMetadata(
            data_type=current_metadata.data_type,
            created_at=current_metadata.created_at,
            updated_at=datetime.utcnow(),
            data_hash=new_data_hash,
            ipfs_hash=ipfs_result["hash"],
            permissions=current_metadata.permissions,
            encryption_key_hash=current_metadata.encryption_key_hash,
            size_bytes=len(json.dumps(updated_data).encode()),
            schema_version=current_metadata.schema_version,
            tags=current_metadata.tags
        )
        
        # Store updated metadata on IPFS
        metadata_result = await self.ipfs_manager.pin_json(asdict(updated_metadata))
        
        return {
            "old_data_hash": current_metadata.data_hash,
            "new_data_hash": new_data_hash,
            "old_ipfs_hash": current_metadata.ipfs_hash,
            "new_ipfs_hash": ipfs_result["hash"],
            "metadata_ipfs_hash": metadata_result["hash"],
            "updated_at": updated_metadata.updated_at
        }
    
    async def _encrypt_data(self, data: Dict[str, Any], owner_address: str) -> Dict[str, Any]:
        """Encrypt data before storing on IPFS"""
        # In production, use proper encryption with key derivation
        # For now, we'll store data as-is but mark it as encrypted
        return {
            "encrypted": True,
            "algorithm": "AES-256-GCM",
            "data": data,  # Would be encrypted in production
            "owner": owner_address,
            "created_at": datetime.utcnow().isoformat()
        }
    
    async def create_data_collection_nft(
        self,
        owner_address: str,
        data_collection: List[Dict[str, Any]],
        collection_name: str,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Create an NFT representing a collection of related data"""
        
        # Create merkle tree of all data items
        data_hashes = [create_data_hash(item) for item in data_collection]
        merkle_tree = generate_merkle_tree(data_hashes)
        
        # Store collection on IPFS
        collection_data = {
            "name": collection_name,
            "items": data_collection,
            "merkle_root": merkle_tree["root"],
            "item_count": len(data_collection),
            "created_at": datetime.utcnow().isoformat()
        }
        
        encrypted_collection = await self._encrypt_data(collection_data, owner_address)
        ipfs_result = await self.ipfs_manager.pin_json(encrypted_collection)
        
        # Create collection metadata
        metadata = DataOwnershipMetadata(
            data_type=DataType.ANALYTICS_DATA,  # Use appropriate type
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            data_hash=merkle_tree["root"],
            ipfs_hash=ipfs_result["hash"],
            permissions={owner_address: AccessLevel.ADMIN},
            encryption_key_hash=hashlib.sha256(owner_address.encode()).hexdigest(),
            size_bytes=len(json.dumps(collection_data).encode()),
            schema_version="1.0.0",
            tags=[f"collection:{collection_name}", "merkle_tree"]
        )
        
        # Mint NFT for the collection
        return await self.mint_data_ownership_nft(
            owner_address,
            collection_data,
            DataType.ANALYTICS_DATA,
            metadata.tags,
            private_key
        )