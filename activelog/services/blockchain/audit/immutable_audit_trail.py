"""
Immutable Audit Trail System
Creates tamper-proof records of all system activities and changes
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
from web3 import Web3
from eth_account import Account

from ..config.blockchain_config import blockchain_config, BlockchainNetwork, ContractType
from ..storage.ipfs_manager import IPFSManager
from ..utils.crypto_utils import generate_merkle_tree, create_event_hash

class EventType(Enum):
    USER_ACTION = "user_action"
    SYSTEM_CHANGE = "system_change"
    DATA_ACCESS = "data_access"
    PERMISSION_CHANGE = "permission_change"
    FINANCIAL_TRANSACTION = "financial_transaction"
    AI_OPERATION = "ai_operation"
    SECURITY_EVENT = "security_event"
    COMPLIANCE_EVENT = "compliance_event"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    event_id: str
    event_type: EventType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    action: str
    resource: str
    resource_id: Optional[str]
    old_value: Optional[Any]
    new_value: Optional[Any]
    metadata: Dict[str, Any]
    severity: Severity
    success: bool
    error_message: Optional[str]
    correlation_id: Optional[str]
    parent_event_id: Optional[str]

@dataclass
class AuditBatch:
    batch_id: str
    events: List[AuditEvent]
    merkle_root: str
    ipfs_hash: str
    blockchain_tx_hash: Optional[str]
    block_number: Optional[int]
    created_at: datetime
    batch_size: int

class ImmutableAuditTrail:
    """Manages immutable audit trails on blockchain with IPFS storage"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.AUDIT_TRAIL, network
        )
        
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        self.ipfs_manager = IPFSManager()
        
        # Load contract ABI
        self.contract_abi = self._load_contract_abi()
        self.contract = self.w3.eth.contract(
            address=self.contract_config.address,
            abi=self.contract_abi
        )
        
        # Event batching
        self.pending_events: List[AuditEvent] = []
        self.batch_size = 100
        self.batch_timeout_seconds = 300  # 5 minutes
        
    def _load_contract_abi(self) -> List[Dict]:
        """Load audit trail contract ABI"""
        return [
            {
                "inputs": [
                    {"name": "batchId", "type": "string"},
                    {"name": "merkleRoot", "type": "bytes32"},
                    {"name": "ipfsHash", "type": "string"},
                    {"name": "eventCount", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"}
                ],
                "name": "recordBatch",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "batchId", "type": "string"}
                ],
                "name": "getBatch",
                "outputs": [
                    {"name": "merkleRoot", "type": "bytes32"},
                    {"name": "ipfsHash", "type": "string"},
                    {"name": "eventCount", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "blockNumber", "type": "uint256"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "merkleRoot", "type": "bytes32"},
                    {"name": "proof", "type": "bytes32[]"},
                    {"name": "eventHash", "type": "bytes32"}
                ],
                "name": "verifyEvent",
                "outputs": [{"name": "", "type": "bool"}],
                "stateMutability": "pure",
                "type": "function"
            }
        ]
    
    async def log_event(
        self,
        event_type: EventType,
        action: str,
        resource: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: Severity = Severity.LOW,
        success: bool = True,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        correlation_id: Optional[str] = None,
        parent_event_id: Optional[str] = None
    ) -> str:
        """Log a single audit event"""
        
        # Generate unique event ID
        event_id = self._generate_event_id(event_type, action, user_id)
        
        # Create audit event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=action,
            resource=resource,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata or {},
            severity=severity,
            success=success,
            error_message=error_message,
            correlation_id=correlation_id,
            parent_event_id=parent_event_id
        )
        
        # Add to pending events
        self.pending_events.append(event)
        
        # Check if we should commit a batch
        if len(self.pending_events) >= self.batch_size:
            await self._commit_batch()
        
        return event_id
    
    async def log_user_action(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """Log a user action event"""
        return await self.log_event(
            event_type=EventType.USER_ACTION,
            action=action,
            resource=resource,
            user_id=user_id,
            resource_id=resource_id,
            metadata=metadata,
            severity=Severity.LOW,
            session_id=session_id,
            ip_address=ip_address
        )
    
    async def log_data_access(
        self,
        user_id: str,
        data_type: str,
        data_id: str,
        access_type: str,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log data access event"""
        return await self.log_event(
            event_type=EventType.DATA_ACCESS,
            action=f"access_{access_type}",
            resource=data_type,
            user_id=user_id,
            resource_id=data_id,
            metadata=metadata,
            severity=Severity.MEDIUM if not success else Severity.LOW,
            success=success
        )
    
    async def log_permission_change(
        self,
        admin_user_id: str,
        target_user_id: str,
        resource: str,
        old_permissions: List[str],
        new_permissions: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log permission change event"""
        return await self.log_event(
            event_type=EventType.PERMISSION_CHANGE,
            action="modify_permissions",
            resource=resource,
            user_id=admin_user_id,
            resource_id=target_user_id,
            old_value=old_permissions,
            new_value=new_permissions,
            metadata=metadata,
            severity=Severity.HIGH
        )
    
    async def log_financial_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: float,
        currency: str,
        transaction_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> str:
        """Log financial transaction event"""
        return await self.log_event(
            event_type=EventType.FINANCIAL_TRANSACTION,
            action=transaction_type,
            resource="financial_transaction",
            user_id=user_id,
            resource_id=transaction_id,
            new_value={"amount": amount, "currency": currency},
            metadata=metadata,
            severity=Severity.HIGH,
            success=success
        )
    
    async def log_ai_operation(
        self,
        user_id: str,
        operation_type: str,
        model_name: str,
        operation_id: str,
        cost: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True
    ) -> str:
        """Log AI operation event"""
        ai_metadata = metadata or {}
        if cost is not None:
            ai_metadata["cost"] = cost
        ai_metadata["model"] = model_name
        
        return await self.log_event(
            event_type=EventType.AI_OPERATION,
            action=operation_type,
            resource="ai_operation",
            user_id=user_id,
            resource_id=operation_id,
            metadata=ai_metadata,
            severity=Severity.MEDIUM,
            success=success
        )
    
    async def log_security_event(
        self,
        event_name: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        severity: Severity = Severity.HIGH
    ) -> str:
        """Log security event"""
        return await self.log_event(
            event_type=EventType.SECURITY_EVENT,
            action=event_name,
            resource="security",
            user_id=user_id,
            ip_address=ip_address,
            metadata=metadata,
            severity=severity
        )
    
    async def _commit_batch(self, private_key: Optional[str] = None) -> Optional[AuditBatch]:
        """Commit pending events to blockchain and IPFS"""
        
        if not self.pending_events:
            return None
        
        # Generate batch ID
        batch_id = self._generate_batch_id()
        
        # Create event hashes for merkle tree
        event_hashes = []
        events_data = []
        
        for event in self.pending_events:
            event_dict = asdict(event)
            # Convert datetime to ISO string
            event_dict['timestamp'] = event.timestamp.isoformat()
            # Convert enums to strings
            event_dict['event_type'] = event.event_type.value
            event_dict['severity'] = event.severity.value
            
            events_data.append(event_dict)
            event_hash = create_event_hash(event_dict)
            event_hashes.append(event_hash)
        
        # Generate merkle tree
        merkle_tree = generate_merkle_tree(event_hashes)
        
        # Store batch on IPFS
        batch_data = {
            "batch_id": batch_id,
            "events": events_data,
            "merkle_tree": merkle_tree,
            "created_at": datetime.utcnow().isoformat(),
            "network": self.network.value
        }
        
        ipfs_result = await self.ipfs_manager.pin_json(batch_data)
        
        # Create audit batch record
        audit_batch = AuditBatch(
            batch_id=batch_id,
            events=self.pending_events.copy(),
            merkle_root=merkle_tree["root"],
            ipfs_hash=ipfs_result["hash"],
            blockchain_tx_hash=None,
            block_number=None,
            created_at=datetime.utcnow(),
            batch_size=len(self.pending_events)
        )
        
        # Record on blockchain if private key provided
        if private_key:
            try:
                tx_result = await self._record_batch_on_chain(
                    batch_id,
                    merkle_tree["root"],
                    ipfs_result["hash"],
                    len(self.pending_events),
                    private_key
                )
                
                audit_batch.blockchain_tx_hash = tx_result["tx_hash"]
                audit_batch.block_number = tx_result["block_number"]
                
            except Exception as e:
                print(f"Failed to record batch on blockchain: {e}")
        
        # Clear pending events
        self.pending_events.clear()
        
        return audit_batch
    
    async def _record_batch_on_chain(
        self,
        batch_id: str,
        merkle_root: str,
        ipfs_hash: str,
        event_count: int,
        private_key: str
    ) -> Dict[str, Any]:
        """Record audit batch on blockchain"""
        
        account = Account.from_key(private_key)
        
        # Convert merkle root to bytes32
        merkle_root_bytes = bytes.fromhex(merkle_root[2:] if merkle_root.startswith('0x') else merkle_root)
        
        tx_data = self.contract.functions.recordBatch(
            batch_id,
            merkle_root_bytes,
            ipfs_hash,
            event_count,
            int(datetime.utcnow().timestamp())
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 300000,
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
    
    async def verify_event_integrity(
        self,
        event_id: str,
        batch_id: str
    ) -> Dict[str, Any]:
        """Verify the integrity of a specific event"""
        
        try:
            # Get batch from blockchain
            batch_data = self.contract.functions.getBatch(batch_id).call()
            merkle_root = batch_data[0].hex()
            ipfs_hash = batch_data[1]
            
            # Get batch from IPFS
            batch_json = await self.ipfs_manager.get_json(ipfs_hash)
            
            # Find the event in the batch
            target_event = None
            event_index = None
            
            for i, event_data in enumerate(batch_json["events"]):
                if event_data["event_id"] == event_id:
                    target_event = event_data
                    event_index = i
                    break
            
            if not target_event:
                return {
                    "valid": False,
                    "error": "Event not found in batch"
                }
            
            # Calculate event hash
            event_hash = create_event_hash(target_event)
            
            # Get merkle proof
            merkle_tree = batch_json["merkle_tree"]
            proof = self._get_merkle_proof(merkle_tree, event_index)
            
            # Verify on blockchain
            proof_bytes = [bytes.fromhex(p[2:] if p.startswith('0x') else p) for p in proof]
            event_hash_bytes = bytes.fromhex(event_hash[2:] if event_hash.startswith('0x') else event_hash)
            merkle_root_bytes = bytes.fromhex(merkle_root[2:] if merkle_root.startswith('0x') else merkle_root)
            
            is_valid = self.contract.functions.verifyEvent(
                merkle_root_bytes,
                proof_bytes,
                event_hash_bytes
            ).call()
            
            return {
                "valid": is_valid,
                "event_hash": event_hash,
                "merkle_root": merkle_root,
                "proof": proof,
                "batch_id": batch_id,
                "event_data": target_event
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit trail with filtering options"""
        
        # In production, this would query an indexing service or subgraph
        # For now, we'll return a simulated response
        
        return [
            {
                "event_id": "evt_123456",
                "event_type": "user_action",
                "timestamp": "2024-01-15T10:30:00Z",
                "user_id": user_id,
                "action": "login",
                "resource": "authentication",
                "success": True,
                "batch_id": "batch_789",
                "verified": True
            }
        ]
    
    async def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        report_type: str = "full"
    ) -> Dict[str, Any]:
        """Generate compliance report for audit purposes"""
        
        # Get all audit events in date range
        events = await self.get_audit_trail(
            start_time=start_date,
            end_time=end_date,
            limit=10000
        )
        
        # Aggregate statistics
        event_counts = {}
        user_activity = {}
        security_events = []
        failed_operations = []
        
        for event in events:
            event_type = event.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            user_id = event.get("user_id")
            if user_id:
                user_activity[user_id] = user_activity.get(user_id, 0) + 1
            
            if event_type == "security_event":
                security_events.append(event)
            
            if not event.get("success", True):
                failed_operations.append(event)
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_events": len(events),
                "event_type_breakdown": event_counts,
                "unique_users": len(user_activity),
                "security_events_count": len(security_events),
                "failed_operations_count": len(failed_operations)
            },
            "security_events": security_events,
            "failed_operations": failed_operations[:50],  # Limit for report size
            "top_active_users": sorted(
                user_activity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20],
            "generated_at": datetime.utcnow().isoformat(),
            "report_type": report_type
        }
    
    def _generate_event_id(self, event_type: EventType, action: str, user_id: Optional[str]) -> str:
        """Generate unique event ID"""
        timestamp = str(int(datetime.utcnow().timestamp() * 1000000))
        content = f"{event_type.value}:{action}:{user_id or 'system'}:{timestamp}"
        hash_obj = hashlib.sha256(content.encode())
        return f"evt_{hash_obj.hexdigest()[:12]}"
    
    def _generate_batch_id(self) -> str:
        """Generate unique batch ID"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        hash_obj = hashlib.sha256(f"batch_{timestamp}_{len(self.pending_events)}".encode())
        return f"batch_{hash_obj.hexdigest()[:16]}"
    
    def _get_merkle_proof(self, merkle_tree: Dict[str, Any], leaf_index: int) -> List[str]:
        """Get merkle proof for a specific leaf"""
        # This would implement the actual merkle proof generation
        # For now, return a placeholder
        return merkle_tree.get("proofs", {}).get(str(leaf_index), [])