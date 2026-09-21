"""
Blockchain Configuration for ActiveLog Web3 Features
Multi-chain support with enterprise-grade security
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal

class BlockchainNetwork(Enum):
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    BASE = "base"
    AVALANCHE = "avalanche"
    BSC = "bsc"
    SOLANA = "solana"

class ContractType(Enum):
    NFT_DATA_OWNERSHIP = "nft_data_ownership"
    AUDIT_TRAIL = "audit_trail"
    PAYMENT_ESCROW = "payment_escrow"
    REPUTATION_TOKEN = "reputation_token"
    COMPUTE_TOKEN = "compute_token"
    DAO_GOVERNANCE = "dao_governance"
    VERIFIABLE_CREDENTIALS = "verifiable_credentials"

@dataclass
class NetworkConfig:
    name: str
    chain_id: int
    rpc_url: str
    currency_symbol: str
    block_explorer: str
    gas_price_gwei: int
    confirmation_blocks: int
    supports_eip1559: bool
    layer_type: str  # L1, L2, sidechain

@dataclass
class ContractConfig:
    address: str
    abi_file: str
    deployment_block: int
    version: str
    upgradeable: bool

class BlockchainConfig:
    """Central configuration for all blockchain features"""
    
    def __init__(self):
        self.networks = self._init_networks()
        self.contracts = self._init_contracts()
        self.ipfs_config = self._init_ipfs_config()
        self.privacy_config = self._init_privacy_config()
        self.token_config = self._init_token_config()
        
    def _init_networks(self) -> Dict[BlockchainNetwork, NetworkConfig]:
        """Initialize supported blockchain networks"""
        return {
            BlockchainNetwork.ETHEREUM: NetworkConfig(
                name="Ethereum Mainnet",
                chain_id=1,
                rpc_url="https://eth-mainnet.g.alchemy.com/v2/your-api-key",
                currency_symbol="ETH",
                block_explorer="https://etherscan.io",
                gas_price_gwei=20,
                confirmation_blocks=12,
                supports_eip1559=True,
                layer_type="L1"
            ),
            BlockchainNetwork.POLYGON: NetworkConfig(
                name="Polygon Mainnet",
                chain_id=137,
                rpc_url="https://polygon-mainnet.g.alchemy.com/v2/your-api-key",
                currency_symbol="MATIC",
                block_explorer="https://polygonscan.com",
                gas_price_gwei=30,
                confirmation_blocks=5,
                supports_eip1559=True,
                layer_type="sidechain"
            ),
            BlockchainNetwork.ARBITRUM: NetworkConfig(
                name="Arbitrum One",
                chain_id=42161,
                rpc_url="https://arb-mainnet.g.alchemy.com/v2/your-api-key",
                currency_symbol="ETH",
                block_explorer="https://arbiscan.io",
                gas_price_gwei=1,
                confirmation_blocks=1,
                supports_eip1559=True,
                layer_type="L2"
            ),
            BlockchainNetwork.OPTIMISM: NetworkConfig(
                name="Optimism",
                chain_id=10,
                rpc_url="https://opt-mainnet.g.alchemy.com/v2/your-api-key",
                currency_symbol="ETH",
                block_explorer="https://optimistic.etherscan.io",
                gas_price_gwei=1,
                confirmation_blocks=1,
                supports_eip1559=True,
                layer_type="L2"
            ),
            BlockchainNetwork.BASE: NetworkConfig(
                name="Base",
                chain_id=8453,
                rpc_url="https://mainnet.base.org",
                currency_symbol="ETH",
                block_explorer="https://basescan.org",
                gas_price_gwei=1,
                confirmation_blocks=1,
                supports_eip1559=True,
                layer_type="L2"
            ),
            BlockchainNetwork.AVALANCHE: NetworkConfig(
                name="Avalanche C-Chain",
                chain_id=43114,
                rpc_url="https://api.avax.network/ext/bc/C/rpc",
                currency_symbol="AVAX",
                block_explorer="https://snowtrace.io",
                gas_price_gwei=25,
                confirmation_blocks=1,
                supports_eip1559=True,
                layer_type="L1"
            ),
            BlockchainNetwork.BSC: NetworkConfig(
                name="BNB Smart Chain",
                chain_id=56,
                rpc_url="https://bsc-dataseed.binance.org/",
                currency_symbol="BNB",
                block_explorer="https://bscscan.com",
                gas_price_gwei=5,
                confirmation_blocks=3,
                supports_eip1559=False,
                layer_type="sidechain"
            ),
            BlockchainNetwork.SOLANA: NetworkConfig(
                name="Solana Mainnet",
                chain_id=0,  # Solana doesn't use chain IDs
                rpc_url="https://api.mainnet-beta.solana.com",
                currency_symbol="SOL",
                block_explorer="https://explorer.solana.com",
                gas_price_gwei=0,  # Solana uses different fee structure
                confirmation_blocks=32,
                supports_eip1559=False,
                layer_type="L1"
            )
        }
    
    def _init_contracts(self) -> Dict[ContractType, Dict[BlockchainNetwork, ContractConfig]]:
        """Initialize contract addresses for each network"""
        return {
            ContractType.NFT_DATA_OWNERSHIP: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x1234567890123456789012345678901234567890",
                    abi_file="DataOwnershipNFT.json",
                    deployment_block=18500000,
                    version="1.0.0",
                    upgradeable=True
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x2345678901234567890123456789012345678901",
                    abi_file="DataOwnershipNFT.json",
                    deployment_block=49000000,
                    version="1.0.0",
                    upgradeable=True
                )
            },
            ContractType.AUDIT_TRAIL: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x3456789012345678901234567890123456789012",
                    abi_file="AuditTrail.json",
                    deployment_block=18500001,
                    version="1.0.0",
                    upgradeable=False
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x4567890123456789012345678901234567890123",
                    abi_file="AuditTrail.json",
                    deployment_block=49000001,
                    version="1.0.0",
                    upgradeable=False
                )
            },
            ContractType.PAYMENT_ESCROW: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x5678901234567890123456789012345678901234",
                    abi_file="PaymentEscrow.json",
                    deployment_block=18500002,
                    version="1.0.0",
                    upgradeable=True
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x6789012345678901234567890123456789012345",
                    abi_file="PaymentEscrow.json",
                    deployment_block=49000002,
                    version="1.0.0",
                    upgradeable=True
                )
            },
            ContractType.REPUTATION_TOKEN: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x7890123456789012345678901234567890123456",
                    abi_file="ReputationToken.json",
                    deployment_block=18500003,
                    version="1.0.0",
                    upgradeable=True
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x8901234567890123456789012345678901234567",
                    abi_file="ReputationToken.json",
                    deployment_block=49000003,
                    version="1.0.0",
                    upgradeable=True
                )
            },
            ContractType.COMPUTE_TOKEN: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x9012345678901234567890123456789012345678",
                    abi_file="ComputeToken.json",
                    deployment_block=18500004,
                    version="1.0.0",
                    upgradeable=True
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x0123456789012345678901234567890123456789",
                    abi_file="ComputeToken.json",
                    deployment_block=49000004,
                    version="1.0.0",
                    upgradeable=True
                )
            },
            ContractType.DAO_GOVERNANCE: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x1122334455667788990011223344556677889900",
                    abi_file="DAOGovernance.json",
                    deployment_block=18500005,
                    version="1.0.0",
                    upgradeable=True
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x2233445566778899001122334455667788990011",
                    abi_file="DAOGovernance.json",
                    deployment_block=49000005,
                    version="1.0.0",
                    upgradeable=True
                )
            },
            ContractType.VERIFIABLE_CREDENTIALS: {
                BlockchainNetwork.ETHEREUM: ContractConfig(
                    address="0x3344556677889900112233445566778899001122",
                    abi_file="VerifiableCredentials.json",
                    deployment_block=18500006,
                    version="1.0.0",
                    upgradeable=True
                ),
                BlockchainNetwork.POLYGON: ContractConfig(
                    address="0x4455667788990011223344556677889900112233",
                    abi_file="VerifiableCredentials.json",
                    deployment_block=49000006,
                    version="1.0.0",
                    upgradeable=True
                )
            }
        }
    
    def _init_ipfs_config(self) -> Dict[str, any]:
        """Initialize IPFS configuration"""
        return {
            "gateway_url": "https://ipfs.infura.io:5001",
            "pinning_service": "pinata",
            "pinata_api_key": "your-pinata-api-key",
            "pinata_secret_key": "your-pinata-secret-key",
            "local_node": {
                "enabled": True,
                "api_url": "http://localhost:5001",
                "gateway_url": "http://localhost:8080"
            },
            "backup_gateways": [
                "https://cloudflare-ipfs.com",
                "https://dweb.link",
                "https://ipfs.io"
            ],
            "encryption": {
                "enabled": True,
                "algorithm": "AES-256-GCM",
                "key_derivation": "PBKDF2"
            }
        }
    
    def _init_privacy_config(self) -> Dict[str, any]:
        """Initialize privacy and zero-knowledge proof configuration"""
        return {
            "zk_circuits": {
                "identity_proof": {
                    "circuit_file": "identity_verification.circom",
                    "proving_key": "identity_pk.zkey",
                    "verification_key": "identity_vk.json"
                },
                "data_integrity": {
                    "circuit_file": "data_integrity.circom",
                    "proving_key": "integrity_pk.zkey",
                    "verification_key": "integrity_vk.json"
                },
                "compute_proof": {
                    "circuit_file": "compute_verification.circom",
                    "proving_key": "compute_pk.zkey",
                    "verification_key": "compute_vk.json"
                }
            },
            "commitment_schemes": {
                "merkle_trees": {
                    "hash_function": "poseidon",
                    "tree_depth": 20
                },
                "polynomial_commitments": {
                    "scheme": "KZG",
                    "trusted_setup": "ceremony_2023.ptau"
                }
            },
            "anonymous_credentials": {
                "scheme": "BBS+",
                "curve": "BLS12-381",
                "key_length": 256
            }
        }
    
    def _init_token_config(self) -> Dict[str, any]:
        """Initialize token configuration"""
        return {
            "activelog_token": {
                "symbol": "ALOG",
                "name": "ActiveLog Token",
                "decimals": 18,
                "total_supply": 1000000000,  # 1 billion tokens
                "distribution": {
                    "team": 0.15,
                    "advisors": 0.05,
                    "treasury": 0.20,
                    "community": 0.30,
                    "liquidity": 0.15,
                    "ecosystem": 0.15
                }
            },
            "reputation_token": {
                "symbol": "REP",
                "name": "ActiveLog Reputation",
                "decimals": 18,
                "max_supply": None,  # Unlimited supply based on activity
                "burning_mechanism": True
            },
            "compute_token": {
                "symbol": "COMP",
                "name": "ActiveLog Compute",
                "decimals": 18,
                "max_supply": None,  # Dynamic supply based on compute availability
                "staking_rewards": True
            }
        }
    
    def get_network_config(self, network: BlockchainNetwork) -> NetworkConfig:
        """Get configuration for a specific network"""
        return self.networks[network]
    
    def get_contract_config(
        self, 
        contract_type: ContractType, 
        network: BlockchainNetwork
    ) -> Optional[ContractConfig]:
        """Get contract configuration for specific type and network"""
        return self.contracts.get(contract_type, {}).get(network)
    
    def get_supported_networks(self, contract_type: ContractType) -> List[BlockchainNetwork]:
        """Get list of networks that support a specific contract type"""
        return list(self.contracts.get(contract_type, {}).keys())
    
    def is_contract_deployed(
        self, 
        contract_type: ContractType, 
        network: BlockchainNetwork
    ) -> bool:
        """Check if a contract is deployed on a specific network"""
        config = self.get_contract_config(contract_type, network)
        return config is not None and config.address != "0x0000000000000000000000000000000000000000"

# Global configuration instance
blockchain_config = BlockchainConfig()