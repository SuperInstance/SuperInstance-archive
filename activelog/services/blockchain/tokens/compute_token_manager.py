"""
Tokenized Compute Resources Manager
Creates and manages NFT/tokens representing compute resources
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
from web3 import Web3
from eth_account import Account

from ..config.blockchain_config import blockchain_config, BlockchainNetwork, ContractType
from ..storage.ipfs_manager import IPFSManager
from ..utils.crypto_utils import create_data_hash, generate_merkle_tree
from ..models.blockchain_models import ComputeToken, ComputeMarketplace


class ResourceType(Enum):
    GPU = "gpu"
    CPU = "cpu" 
    STORAGE = "storage"
    MEMORY = "memory"
    BANDWIDTH = "bandwidth"
    HYBRID = "hybrid"


class PricingModel(Enum):
    PER_HOUR = "per_hour"
    PER_MINUTE = "per_minute"
    PER_JOB = "per_job"
    AUCTION = "auction"
    FIXED_TERM = "fixed_term"


@dataclass
class ComputeResourceSpec:
    resource_type: ResourceType
    quantity: float
    unit: str
    performance_metrics: Dict[str, Any]
    minimum_duration: int  # minutes
    maximum_duration: int  # minutes
    availability_zones: List[str]
    hardware_details: Dict[str, Any]


@dataclass
class ResourcePricing:
    model: PricingModel
    base_price_per_hour: Decimal
    currency: str  # ETH, MATIC, USDC, etc.
    volume_discounts: Dict[str, Decimal]
    peak_hour_multiplier: Decimal
    minimum_charge: Decimal
    cancellation_fee: Decimal


@dataclass
class AvailabilitySchedule:
    timezone: str
    available_hours: List[Tuple[int, int]]  # (start_hour, end_hour) pairs
    blackout_periods: List[Tuple[datetime, datetime]]
    advance_booking_required: int  # hours
    maximum_booking_ahead: int  # days


@dataclass
class ComputeTokenMetadata:
    token_id: str
    resource_spec: ComputeResourceSpec
    pricing: ResourcePricing
    availability: AvailabilitySchedule
    provider_info: Dict[str, Any]
    performance_history: List[Dict[str, Any]]
    certifications: List[str]
    compliance_standards: List[str]
    insurance_coverage: Optional[Dict[str, Any]]


class ComputeTokenManager:
    """Manages tokenized compute resources"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.COMPUTE_TOKEN, network
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
        """Load compute token contract ABI"""
        return [
            {
                "inputs": [
                    {"name": "provider", "type": "address"},
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "resourceType", "type": "uint8"},
                    {"name": "metadataURI", "type": "string"},
                    {"name": "pricingData", "type": "bytes"}
                ],
                "name": "mintComputeToken",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "consumer", "type": "address"},
                    {"name": "startTime", "type": "uint256"},
                    {"name": "duration", "type": "uint256"},
                    {"name": "paymentAmount", "type": "uint256"}
                ],
                "name": "reserveResource",
                "outputs": [],
                "stateMutability": "payable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"}
                ],
                "name": "completeJob",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"},
                    {"name": "rating", "type": "uint8"},
                    {"name": "review", "type": "string"}
                ],
                "name": "submitRating",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "tokenId", "type": "uint256"}
                ],
                "name": "getResourceInfo",
                "outputs": [
                    {"name": "provider", "type": "address"},
                    {"name": "resourceType", "type": "uint8"},
                    {"name": "isAvailable", "type": "bool"},
                    {"name": "currentConsumer", "type": "address"},
                    {"name": "reservedUntil", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "resourceType", "type": "uint8"},
                    {"name": "minRating", "type": "uint8"}
                ],
                "name": "findAvailableResources",
                "outputs": [{"name": "tokenIds", "type": "uint256[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]
    
    async def tokenize_compute_resource(
        self,
        provider_address: str,
        resource_spec: ComputeResourceSpec,
        pricing: ResourcePricing,
        availability: AvailabilitySchedule,
        provider_info: Dict[str, Any],
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tokenize a compute resource as an NFT"""
        
        # Generate unique token ID based on provider and resource
        token_data = {
            "provider": provider_address,
            "resource_type": resource_spec.resource_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "resource_hash": create_data_hash(asdict(resource_spec))
        }
        token_id = int(create_data_hash(token_data)[:16], 16)
        
        # Create comprehensive metadata
        metadata = ComputeTokenMetadata(
            token_id=str(token_id),
            resource_spec=resource_spec,
            pricing=pricing,
            availability=availability,
            provider_info=provider_info,
            performance_history=[],
            certifications=provider_info.get("certifications", []),
            compliance_standards=provider_info.get("compliance", []),
            insurance_coverage=provider_info.get("insurance")
        )
        
        # Store metadata on IPFS
        metadata_result = await self.ipfs_manager.pin_json(asdict(metadata))
        
        # Encode pricing data for smart contract
        pricing_data = self._encode_pricing_data(pricing)
        
        if private_key:
            # Execute minting transaction
            account = Account.from_key(private_key)
            tx_data = self.contract.functions.mintComputeToken(
                provider_address,
                token_id,
                list(ResourceType).index(resource_spec.resource_type),
                f"ipfs://{metadata_result['hash']}",
                pricing_data
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 500000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Store in database
            await self._store_compute_token(
                token_id, provider_address, metadata, 
                receipt.transactionHash.hex(), receipt.blockNumber
            )
            
            return {
                "token_id": token_id,
                "transaction_hash": receipt.transactionHash.hex(),
                "block_number": receipt.blockNumber,
                "metadata_ipfs_hash": metadata_result['hash'],
                "gas_used": receipt.gasUsed,
                "success": receipt.status == 1
            }
        else:
            # Return transaction data for external signing
            return {
                "token_id": token_id,
                "contract_address": self.contract_config.address,
                "function_data": self.contract.functions.mintComputeToken(
                    provider_address,
                    token_id,
                    list(ResourceType).index(resource_spec.resource_type),
                    f"ipfs://{metadata_result['hash']}",
                    pricing_data
                ).build_transaction({
                    'gas': 500000,
                    'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
                })['data'],
                "metadata_ipfs_hash": metadata_result['hash']
            }
    
    async def reserve_compute_resource(
        self,
        token_id: int,
        consumer_address: str,
        start_time: datetime,
        duration_hours: float,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reserve a compute resource for specified time period"""
        
        # Get resource metadata to calculate cost
        metadata = await self.get_compute_token_metadata(token_id)
        if not metadata:
            raise ValueError(f"Compute token {token_id} not found")
        
        # Calculate payment amount
        payment_amount = await self._calculate_payment_amount(
            metadata, duration_hours, start_time
        )
        
        start_timestamp = int(start_time.timestamp())
        duration_seconds = int(duration_hours * 3600)
        
        if private_key:
            account = Account.from_key(private_key)
            tx_data = self.contract.functions.reserveResource(
                token_id,
                consumer_address,
                start_timestamp,
                duration_seconds,
                payment_amount
            ).build_transaction({
                'from': account.address,
                'nonce': self.w3.eth.get_transaction_count(account.address),
                'gas': 300000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei'),
                'value': payment_amount
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Update database
            await self._update_resource_reservation(
                token_id, consumer_address, start_time, duration_hours,
                receipt.transactionHash.hex()
            )
            
            return {
                "reservation_id": f"{token_id}_{consumer_address}_{start_timestamp}",
                "transaction_hash": receipt.transactionHash.hex(),
                "payment_amount": payment_amount,
                "start_time": start_time,
                "end_time": start_time + timedelta(hours=duration_hours),
                "success": receipt.status == 1
            }
        else:
            return {
                "contract_address": self.contract_config.address,
                "function_data": self.contract.functions.reserveResource(
                    token_id,
                    consumer_address,
                    start_timestamp,
                    duration_seconds,
                    payment_amount
                ).build_transaction({
                    'gas': 300000,
                    'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei'),
                    'value': payment_amount
                })['data'],
                "payment_amount": payment_amount
            }
    
    async def complete_compute_job(
        self,
        token_id: int,
        performance_metrics: Dict[str, Any],
        private_key: str
    ) -> Dict[str, Any]:
        """Mark compute job as completed and release payment"""
        
        account = Account.from_key(private_key)
        tx_data = self.contract.functions.completeJob(token_id).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Store performance metrics on IPFS
        metrics_result = await self.ipfs_manager.pin_json({
            "token_id": token_id,
            "completion_time": datetime.utcnow().isoformat(),
            "performance_metrics": performance_metrics,
            "job_status": "completed"
        })
        
        # Update database with completion
        await self._update_job_completion(
            token_id, performance_metrics, metrics_result['hash'],
            receipt.transactionHash.hex()
        )
        
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "performance_ipfs_hash": metrics_result['hash'],
            "completed_at": datetime.utcnow(),
            "success": receipt.status == 1
        }
    
    async def submit_resource_rating(
        self,
        token_id: int,
        rating: int,  # 1-5 stars
        review_text: str,
        consumer_address: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Submit rating and review for completed job"""
        
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
        
        account = Account.from_key(private_key)
        tx_data = self.contract.functions.submitRating(
            token_id,
            rating,
            review_text
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 150000,
            'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Store detailed review on IPFS
        review_data = {
            "token_id": token_id,
            "consumer_address": consumer_address,
            "rating": rating,
            "review_text": review_text,
            "submitted_at": datetime.utcnow().isoformat()
        }
        review_result = await self.ipfs_manager.pin_json(review_data)
        
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "review_ipfs_hash": review_result['hash'],
            "rating": rating,
            "success": receipt.status == 1
        }
    
    async def find_available_resources(
        self,
        resource_type: ResourceType,
        min_rating: float = 4.0,
        location_preference: Optional[str] = None,
        max_price_per_hour: Optional[Decimal] = None
    ) -> List[Dict[str, Any]]:
        """Find available compute resources matching criteria"""
        
        # Query smart contract for available resources
        resource_type_index = list(ResourceType).index(resource_type)
        min_rating_scaled = int(min_rating * 20)  # Scale 0-5 to 0-100
        
        try:
            token_ids = self.contract.functions.findAvailableResources(
                resource_type_index, 
                min_rating_scaled
            ).call()
            
            available_resources = []
            
            for token_id in token_ids:
                # Get resource details
                resource_info = await self.get_compute_resource_info(token_id)
                if not resource_info:
                    continue
                
                # Get metadata from IPFS
                metadata = await self.get_compute_token_metadata(token_id)
                if not metadata:
                    continue
                
                # Apply filters
                if max_price_per_hour and metadata.pricing.base_price_per_hour > max_price_per_hour:
                    continue
                
                if location_preference:
                    available_zones = metadata.resource_spec.availability_zones
                    if location_preference not in available_zones:
                        continue
                
                available_resources.append({
                    "token_id": token_id,
                    "provider_address": resource_info["provider"],
                    "resource_spec": asdict(metadata.resource_spec),
                    "pricing": asdict(metadata.pricing),
                    "availability": asdict(metadata.availability),
                    "performance_history": metadata.performance_history,
                    "rating": resource_info.get("rating", 0) / 20.0  # Scale back to 0-5
                })
            
            return available_resources
            
        except Exception as e:
            print(f"Error finding available resources: {e}")
            return []
    
    async def get_compute_resource_info(self, token_id: int) -> Optional[Dict[str, Any]]:
        """Get basic resource info from smart contract"""
        
        try:
            result = self.contract.functions.getResourceInfo(token_id).call()
            
            return {
                "provider": result[0],
                "resource_type": list(ResourceType)[result[1]].value,
                "is_available": result[2],
                "current_consumer": result[3] if result[3] != "0x0000000000000000000000000000000000000000" else None,
                "reserved_until": datetime.fromtimestamp(result[4]) if result[4] > 0 else None
            }
            
        except Exception as e:
            print(f"Error getting resource info for token {token_id}: {e}")
            return None
    
    async def get_compute_token_metadata(self, token_id: int) -> Optional[ComputeTokenMetadata]:
        """Get full metadata for compute token from IPFS"""
        
        try:
            # This would typically get the tokenURI from the contract
            # For now, we'll simulate getting metadata
            # In production, implement tokenURI() function in contract
            
            # Placeholder: return None to indicate not found
            # Real implementation would:
            # 1. Call contract.functions.tokenURI(token_id).call()
            # 2. Extract IPFS hash from URI
            # 3. Fetch metadata from IPFS
            # 4. Parse and return ComputeTokenMetadata
            
            return None
            
        except Exception as e:
            print(f"Error getting token metadata for {token_id}: {e}")
            return None
    
    async def get_provider_resources(self, provider_address: str) -> List[Dict[str, Any]]:
        """Get all compute resources owned by a provider"""
        
        # In production, this would query contract events or use a subgraph
        # For now, return empty list
        return []
    
    async def get_consumer_reservations(self, consumer_address: str) -> List[Dict[str, Any]]:
        """Get all resource reservations by a consumer"""
        
        # In production, this would query contract events or use a subgraph
        # For now, return empty list
        return []
    
    def _encode_pricing_data(self, pricing: ResourcePricing) -> bytes:
        """Encode pricing data for smart contract storage"""
        
        # Simplified encoding - in production use proper ABI encoding
        pricing_dict = asdict(pricing)
        pricing_json = json.dumps(pricing_dict, default=str)
        return pricing_json.encode('utf-8')
    
    async def _calculate_payment_amount(
        self,
        metadata: ComputeTokenMetadata,
        duration_hours: float,
        start_time: datetime
    ) -> int:
        """Calculate payment amount in wei for resource reservation"""
        
        base_cost = metadata.pricing.base_price_per_hour * Decimal(str(duration_hours))
        
        # Apply peak hour multiplier if applicable
        hour = start_time.hour
        if 9 <= hour <= 17:  # Business hours
            base_cost *= metadata.pricing.peak_hour_multiplier
        
        # Apply volume discounts
        for threshold, discount in metadata.pricing.volume_discounts.items():
            if duration_hours >= float(threshold):
                base_cost *= (1 - discount)
                break
        
        # Ensure minimum charge
        if base_cost < metadata.pricing.minimum_charge:
            base_cost = metadata.pricing.minimum_charge
        
        # Convert to wei (assuming pricing is in ETH)
        return self.w3.to_wei(base_cost, 'ether')
    
    async def _store_compute_token(
        self,
        token_id: int,
        provider_address: str,
        metadata: ComputeTokenMetadata,
        tx_hash: str,
        block_number: int
    ):
        """Store compute token in database"""
        
        # This would use SQLAlchemy session to store in database
        # Implementation depends on database setup
        pass
    
    async def _update_resource_reservation(
        self,
        token_id: int,
        consumer_address: str,
        start_time: datetime,
        duration_hours: float,
        tx_hash: str
    ):
        """Update resource reservation in database"""
        
        # Update database with reservation details
        pass
    
    async def _update_job_completion(
        self,
        token_id: int,
        performance_metrics: Dict[str, Any],
        metrics_ipfs_hash: str,
        tx_hash: str
    ):
        """Update job completion in database"""
        
        # Update database with completion details
        pass
    
    async def create_resource_bundle(
        self,
        provider_address: str,
        resources: List[ComputeTokenMetadata],
        bundle_pricing: ResourcePricing,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a bundle of multiple compute resources"""
        
        # Generate bundle ID
        bundle_data = {
            "provider": provider_address,
            "resources": [r.token_id for r in resources],
            "created_at": datetime.utcnow().isoformat()
        }
        bundle_id = create_data_hash(bundle_data)
        
        # Create bundle metadata
        bundle_metadata = {
            "bundle_id": bundle_id,
            "provider_address": provider_address,
            "included_resources": [asdict(r) for r in resources],
            "bundle_pricing": asdict(bundle_pricing),
            "created_at": datetime.utcnow().isoformat(),
            "total_compute_units": sum(r.resource_spec.quantity for r in resources),
            "combined_performance": self._calculate_combined_performance(resources)
        }
        
        # Store bundle metadata on IPFS
        bundle_result = await self.ipfs_manager.pin_json(bundle_metadata)
        
        return {
            "bundle_id": bundle_id,
            "bundle_ipfs_hash": bundle_result['hash'],
            "included_tokens": [r.token_id for r in resources],
            "total_resources": len(resources)
        }
    
    def _calculate_combined_performance(self, resources: List[ComputeTokenMetadata]) -> Dict[str, Any]:
        """Calculate combined performance metrics for resource bundle"""
        
        total_compute = 0
        total_memory = 0
        total_storage = 0
        
        for resource in resources:
            metrics = resource.resource_spec.performance_metrics
            total_compute += metrics.get("compute_units", 0)
            total_memory += metrics.get("memory_gb", 0)  
            total_storage += metrics.get("storage_gb", 0)
        
        return {
            "total_compute_units": total_compute,
            "total_memory_gb": total_memory,
            "total_storage_gb": total_storage,
            "resource_count": len(resources)
        }