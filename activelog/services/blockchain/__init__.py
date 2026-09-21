"""
ActiveLog Blockchain Services
Comprehensive Web3 infrastructure for decentralized features
"""

# Core configuration and utilities
from .config.blockchain_config import blockchain_config, BlockchainNetwork, ContractType
from .utils.crypto_utils import (
    create_data_hash, generate_merkle_tree, verify_merkle_proof,
    generate_commitment, verify_commitment, create_privacy_hash
)
from .storage.ipfs_manager import IPFSManager

# Existing implementations (already built)
from .nft.data_ownership_nft import DataOwnershipNFT, DataType, AccessLevel
from .audit.immutable_audit_trail import ImmutableAuditTrail, EventType, Severity  
from .payments.smart_payment_escrow import SmartPaymentEscrow
from .credentials.verifiable_credentials import VerifiableCredentialSystem
from .bridges.cross_chain_bridge import CrossChainBridge
from .governance.dao_governance import DAOGovernance

# New implementations (just built)
from .tokens.compute_token_manager import ComputeTokenManager, ResourceType, PricingModel
from .tokens.reputation_token_manager import (
    ReputationTokenManager, ReputationAction, ReputationCategory
)
from .privacy.zk_proof_system import ZKProofSystem, ZKProofType, ZKCircuit
from .marketplace.distributed_compute_marketplace import (
    DistributedComputeMarketplace, JobType, JobStatus
)
from .consensus.shared_truth_consensus import (
    SharedTruthConsensus, ConsensusAlgorithm, TruthType, NodeType
)

# Database models
from .models.blockchain_models import (
    NFTOwnership, DataAccessGrant, AuditEvent, VerifiableCredential,
    ReputationToken, ComputeToken, DAOProposal, DAOVote, CrossChainBridge,
    ZKProof, ComputeMarketplace, ConsensusNode, SharedTruth, BlockchainTransaction
)

__all__ = [
    # Core
    'blockchain_config', 'BlockchainNetwork', 'ContractType', 
    'IPFSManager', 'create_data_hash', 'generate_merkle_tree',
    
    # Existing services
    'DataOwnershipNFT', 'DataType', 'AccessLevel',
    'ImmutableAuditTrail', 'EventType', 'Severity',
    'SmartPaymentEscrow', 'VerifiableCredentialSystem',
    'CrossChainBridge', 'DAOGovernance',
    
    # New services
    'ComputeTokenManager', 'ResourceType', 'PricingModel',
    'ReputationTokenManager', 'ReputationAction', 'ReputationCategory',
    'ZKProofSystem', 'ZKProofType', 'ZKCircuit',
    'DistributedComputeMarketplace', 'JobType', 'JobStatus',
    'SharedTruthConsensus', 'ConsensusAlgorithm', 'TruthType', 'NodeType',
    
    # Database models
    'NFTOwnership', 'DataAccessGrant', 'AuditEvent', 'VerifiableCredential',
    'ReputationToken', 'ComputeToken', 'DAOProposal', 'DAOVote',
    'CrossChainBridge', 'ZKProof', 'ComputeMarketplace', 
    'ConsensusNode', 'SharedTruth', 'BlockchainTransaction'
]

# Version information
__version__ = '1.0.0'
__author__ = 'ActiveLog Blockchain Team'
__description__ = 'Comprehensive Web3 infrastructure for ActiveLog platform'

# Service initialization helpers
def get_blockchain_service(service_name: str, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
    """Factory function to get blockchain service instances"""
    
    services = {
        'data_ownership': lambda: DataOwnershipNFT(network),
        'audit_trail': lambda: ImmutableAuditTrail(network),
        'payment_escrow': lambda: SmartPaymentEscrow(network),
        'credentials': lambda: VerifiableCredentialSystem(network),
        'cross_chain_bridge': lambda: CrossChainBridge(network),
        'dao_governance': lambda: DAOGovernance(network),
        'compute_tokens': lambda: ComputeTokenManager(network),
        'reputation_tokens': lambda: ReputationTokenManager(network),
        'zk_proofs': lambda: ZKProofSystem(network),
        'compute_marketplace': lambda: DistributedComputeMarketplace(network),
        'consensus': lambda: SharedTruthConsensus(network),
        'ipfs': lambda: IPFSManager()
    }
    
    if service_name not in services:
        raise ValueError(f"Unknown service: {service_name}. Available: {list(services.keys())}")
    
    return services[service_name]()


def get_all_blockchain_services(network: BlockchainNetwork = BlockchainNetwork.POLYGON) -> dict:
    """Get all blockchain service instances"""
    
    return {
        'data_ownership': DataOwnershipNFT(network),
        'audit_trail': ImmutableAuditTrail(network),
        'payment_escrow': SmartPaymentEscrow(network),
        'credentials': VerifiableCredentialSystem(network),
        'cross_chain_bridge': CrossChainBridge(network),
        'dao_governance': DAOGovernance(network),
        'compute_tokens': ComputeTokenManager(network),
        'reputation_tokens': ReputationTokenManager(network),
        'zk_proofs': ZKProofSystem(network),
        'compute_marketplace': DistributedComputeMarketplace(network),
        'consensus': SharedTruthConsensus(network),
        'ipfs': IPFSManager()
    }


# Configuration validation
def validate_blockchain_config():
    """Validate blockchain configuration"""
    
    issues = []
    
    # Check if all required networks are configured
    required_networks = [BlockchainNetwork.ETHEREUM, BlockchainNetwork.POLYGON]
    for network in required_networks:
        if network not in blockchain_config.networks:
            issues.append(f"Missing configuration for {network.value}")
    
    # Check contract configurations
    for contract_type in ContractType:
        for network in required_networks:
            if not blockchain_config.is_contract_deployed(contract_type, network):
                issues.append(f"Contract {contract_type.value} not deployed on {network.value}")
    
    return issues