"""
Smart Payment Escrow System for ActiveLog
Automated payment processing with dispute resolution and multi-party agreements
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal
from datetime import datetime, timedelta
import hashlib
import logging
from web3 import Web3
from web3.contract import Contract

from ..config.blockchain_config import (
    blockchain_config, 
    BlockchainNetwork, 
    ContractType
)

logger = logging.getLogger(__name__)

class EscrowStatus(Enum):
    CREATED = "created"
    FUNDED = "funded"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class DisputeReason(Enum):
    NON_DELIVERY = "non_delivery"
    QUALITY_ISSUE = "quality_issue"
    TIMEOUT = "timeout"
    FRAUD = "fraud"
    OTHER = "other"

class PaymentType(Enum):
    INSTANT = "instant"
    MILESTONE = "milestone"
    SUBSCRIPTION = "subscription"
    COMPUTE_RENTAL = "compute_rental"

@dataclass
class EscrowParty:
    address: str
    role: str  # buyer, seller, arbitrator, stakeholder
    stake_percentage: float = 0.0
    voting_weight: int = 1

@dataclass
class Milestone:
    id: str
    description: str
    amount: Decimal
    due_date: datetime
    completed: bool = False
    approved_by: List[str] = None

    def __post_init__(self):
        if self.approved_by is None:
            self.approved_by = []

@dataclass
class EscrowAgreement:
    escrow_id: str
    payment_type: PaymentType
    total_amount: Decimal
    currency: str
    buyer: EscrowParty
    seller: EscrowParty
    arbitrators: List[EscrowParty]
    milestones: List[Milestone]
    dispute_timeout: int  # hours
    auto_release_timeout: int  # hours
    completion_requirements: Dict[str, Any]
    created_at: datetime
    status: EscrowStatus = EscrowStatus.CREATED

class SmartPaymentEscrow:
    """Smart contract-based payment escrow system"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.PAYMENT_ESCROW, 
            network
        )
        
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        self.contract = None
        self.escrows: Dict[str, EscrowAgreement] = {}
        
        if self.contract_config:
            self._load_contract()
    
    def _load_contract(self):
        """Load the escrow smart contract"""
        try:
            with open(f"contracts/{self.contract_config.abi_file}", 'r') as f:
                abi = json.load(f)
            
            self.contract = self.w3.eth.contract(
                address=self.contract_config.address,
                abi=abi
            )
            logger.info(f"Loaded escrow contract on {self.network.value}")
        except Exception as e:
            logger.error(f"Failed to load contract: {e}")
    
    async def create_escrow(
        self,
        buyer_address: str,
        seller_address: str,
        amount: Decimal,
        currency: str = "ETH",
        payment_type: PaymentType = PaymentType.INSTANT,
        milestones: List[Dict[str, Any]] = None,
        arbitrators: List[str] = None,
        dispute_timeout: int = 72,
        auto_release_timeout: int = 168,
        completion_requirements: Dict[str, Any] = None,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Create a new payment escrow agreement"""
        try:
            escrow_id = self._generate_escrow_id(buyer_address, seller_address)
            
            # Create parties
            buyer = EscrowParty(address=buyer_address, role="buyer")
            seller = EscrowParty(address=seller_address, role="seller")
            
            # Create arbitrators
            arbitrator_parties = []
            if arbitrators:
                for arb_addr in arbitrators:
                    arbitrator_parties.append(
                        EscrowParty(address=arb_addr, role="arbitrator", voting_weight=2)
                    )
            
            # Create milestones
            milestone_objects = []
            if milestones:
                for i, milestone_data in enumerate(milestones):
                    milestone_objects.append(Milestone(
                        id=f"{escrow_id}_milestone_{i}",
                        description=milestone_data.get("description", ""),
                        amount=Decimal(str(milestone_data.get("amount", 0))),
                        due_date=datetime.fromisoformat(milestone_data.get("due_date")),
                        completed=False
                    ))
            else:
                # Single milestone for instant payment
                milestone_objects.append(Milestone(
                    id=f"{escrow_id}_milestone_0",
                    description="Full payment release",
                    amount=amount,
                    due_date=datetime.now() + timedelta(hours=auto_release_timeout),
                    completed=False
                ))
            
            # Create agreement
            agreement = EscrowAgreement(
                escrow_id=escrow_id,
                payment_type=payment_type,
                total_amount=amount,
                currency=currency,
                buyer=buyer,
                seller=seller,
                arbitrators=arbitrator_parties,
                milestones=milestone_objects,
                dispute_timeout=dispute_timeout,
                auto_release_timeout=auto_release_timeout,
                completion_requirements=completion_requirements or {},
                created_at=datetime.now(),
                status=EscrowStatus.CREATED
            )
            
            # Store agreement
            self.escrows[escrow_id] = agreement
            
            # Create on-chain escrow
            if self.contract and private_key:
                tx_hash = await self._create_on_chain_escrow(agreement, private_key)
            else:
                tx_hash = None
            
            logger.info(f"Created escrow {escrow_id} for {amount} {currency}")
            
            return {
                "escrow_id": escrow_id,
                "status": agreement.status.value,
                "total_amount": float(amount),
                "currency": currency,
                "buyer": buyer_address,
                "seller": seller_address,
                "milestones": len(milestone_objects),
                "transaction_hash": tx_hash,
                "created_at": agreement.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create escrow: {e}")
            raise
    
    async def fund_escrow(
        self,
        escrow_id: str,
        private_key: str,
        amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Fund an escrow with the required amount"""
        try:
            if escrow_id not in self.escrows:
                raise ValueError(f"Escrow {escrow_id} not found")
            
            agreement = self.escrows[escrow_id]
            fund_amount = amount or agreement.total_amount
            
            if agreement.status != EscrowStatus.CREATED:
                raise ValueError(f"Escrow {escrow_id} is not in CREATED status")
            
            # Fund on-chain escrow
            tx_hash = None
            if self.contract:
                tx_hash = await self._fund_on_chain_escrow(
                    escrow_id, 
                    fund_amount, 
                    private_key
                )
            
            # Update status
            agreement.status = EscrowStatus.FUNDED
            
            logger.info(f"Funded escrow {escrow_id} with {fund_amount} {agreement.currency}")
            
            return {
                "escrow_id": escrow_id,
                "status": agreement.status.value,
                "funded_amount": float(fund_amount),
                "transaction_hash": tx_hash,
                "funded_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to fund escrow {escrow_id}: {e}")
            raise
    
    async def complete_milestone(
        self,
        escrow_id: str,
        milestone_id: str,
        completion_proof: Dict[str, Any],
        approver_address: str,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Mark a milestone as completed and request approval"""
        try:
            if escrow_id not in self.escrows:
                raise ValueError(f"Escrow {escrow_id} not found")
            
            agreement = self.escrows[escrow_id]
            
            # Find milestone
            milestone = None
            for m in agreement.milestones:
                if m.id == milestone_id:
                    milestone = m
                    break
            
            if not milestone:
                raise ValueError(f"Milestone {milestone_id} not found")
            
            if milestone.completed:
                raise ValueError(f"Milestone {milestone_id} already completed")
            
            # Verify approver is authorized
            authorized_approvers = [agreement.buyer.address]
            authorized_approvers.extend([arb.address for arb in agreement.arbitrators])
            
            if approver_address not in authorized_approvers:
                raise ValueError(f"Address {approver_address} not authorized to approve")
            
            # Store completion proof
            completion_data = {
                "milestone_id": milestone_id,
                "completion_proof": completion_proof,
                "completed_at": datetime.now().isoformat(),
                "approver": approver_address
            }
            
            # Add approver
            milestone.approved_by.append(approver_address)
            
            # Check if milestone can be marked as completed
            required_approvals = 1  # Buyer approval required
            if agreement.arbitrators:
                required_approvals += 1  # At least one arbitrator
            
            if len(milestone.approved_by) >= required_approvals:
                milestone.completed = True
                
                # Trigger payment release if conditions met
                if agreement.payment_type == PaymentType.MILESTONE:
                    await self._release_milestone_payment(
                        escrow_id, 
                        milestone_id, 
                        private_key
                    )
            
            # Update agreement status
            if all(m.completed for m in agreement.milestones):
                agreement.status = EscrowStatus.COMPLETED
            else:
                agreement.status = EscrowStatus.IN_PROGRESS
            
            logger.info(f"Milestone {milestone_id} approved by {approver_address}")
            
            return {
                "escrow_id": escrow_id,
                "milestone_id": milestone_id,
                "completed": milestone.completed,
                "approvals": len(milestone.approved_by),
                "status": agreement.status.value,
                "completion_data": completion_data
            }
            
        except Exception as e:
            logger.error(f"Failed to complete milestone {milestone_id}: {e}")
            raise
    
    async def release_payment(
        self,
        escrow_id: str,
        recipient_address: str,
        amount: Optional[Decimal] = None,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Release payment from escrow to recipient"""
        try:
            if escrow_id not in self.escrows:
                raise ValueError(f"Escrow {escrow_id} not found")
            
            agreement = self.escrows[escrow_id]
            release_amount = amount or agreement.total_amount
            
            # Verify release conditions
            if agreement.status not in [EscrowStatus.FUNDED, EscrowStatus.IN_PROGRESS]:
                raise ValueError(f"Escrow {escrow_id} not in releasable status")
            
            # Check if all milestones are completed for full release
            if not amount and not all(m.completed for m in agreement.milestones):
                raise ValueError("Cannot release full payment - milestones not completed")
            
            # Execute on-chain release
            tx_hash = None
            if self.contract and private_key:
                tx_hash = await self._release_on_chain_payment(
                    escrow_id,
                    recipient_address,
                    release_amount,
                    private_key
                )
            
            # Update status
            if not amount or amount >= agreement.total_amount:
                agreement.status = EscrowStatus.COMPLETED
            
            logger.info(
                f"Released {release_amount} {agreement.currency} "
                f"from escrow {escrow_id} to {recipient_address}"
            )
            
            return {
                "escrow_id": escrow_id,
                "recipient": recipient_address,
                "amount": float(release_amount),
                "currency": agreement.currency,
                "status": agreement.status.value,
                "transaction_hash": tx_hash,
                "released_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to release payment from escrow {escrow_id}: {e}")
            raise
    
    async def dispute_escrow(
        self,
        escrow_id: str,
        disputant_address: str,
        reason: DisputeReason,
        evidence: Dict[str, Any],
        private_key: str = None
    ) -> Dict[str, Any]:
        """Initiate a dispute for an escrow"""
        try:
            if escrow_id not in self.escrows:
                raise ValueError(f"Escrow {escrow_id} not found")
            
            agreement = self.escrows[escrow_id]
            
            # Verify disputant is authorized
            authorized_disputants = [agreement.buyer.address, agreement.seller.address]
            if disputant_address not in authorized_disputants:
                raise ValueError(f"Address {disputant_address} not authorized to dispute")
            
            # Check if dispute is still possible
            if agreement.status == EscrowStatus.COMPLETED:
                raise ValueError("Cannot dispute completed escrow")
            
            # Create dispute record
            dispute_data = {
                "dispute_id": f"{escrow_id}_dispute_{int(datetime.now().timestamp())}",
                "escrow_id": escrow_id,
                "disputant": disputant_address,
                "reason": reason.value,
                "evidence": evidence,
                "created_at": datetime.now().isoformat(),
                "resolution_deadline": (
                    datetime.now() + timedelta(hours=agreement.dispute_timeout)
                ).isoformat()
            }
            
            # Update agreement status
            agreement.status = EscrowStatus.DISPUTED
            
            # Notify arbitrators (in real implementation)
            if agreement.arbitrators:
                await self._notify_arbitrators(escrow_id, dispute_data)
            
            # Record dispute on-chain
            tx_hash = None
            if self.contract and private_key:
                tx_hash = await self._record_dispute_on_chain(
                    escrow_id,
                    reason.value,
                    private_key
                )
            
            logger.info(
                f"Dispute initiated for escrow {escrow_id} "
                f"by {disputant_address}, reason: {reason.value}"
            )
            
            return {
                "escrow_id": escrow_id,
                "dispute_id": dispute_data["dispute_id"],
                "status": agreement.status.value,
                "disputant": disputant_address,
                "reason": reason.value,
                "transaction_hash": tx_hash,
                "created_at": dispute_data["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to dispute escrow {escrow_id}: {e}")
            raise
    
    async def resolve_dispute(
        self,
        escrow_id: str,
        arbitrator_address: str,
        resolution: Dict[str, Any],
        private_key: str
    ) -> Dict[str, Any]:
        """Resolve a dispute as an arbitrator"""
        try:
            if escrow_id not in self.escrows:
                raise ValueError(f"Escrow {escrow_id} not found")
            
            agreement = self.escrows[escrow_id]
            
            # Verify arbitrator is authorized
            arbitrator_addresses = [arb.address for arb in agreement.arbitrators]
            if arbitrator_address not in arbitrator_addresses:
                raise ValueError(f"Address {arbitrator_address} not authorized arbitrator")
            
            if agreement.status != EscrowStatus.DISPUTED:
                raise ValueError(f"Escrow {escrow_id} is not in dispute")
            
            # Process resolution
            buyer_percentage = resolution.get("buyer_percentage", 0)
            seller_percentage = resolution.get("seller_percentage", 100)
            
            if buyer_percentage + seller_percentage != 100:
                raise ValueError("Resolution percentages must sum to 100")
            
            # Execute resolution
            results = []
            
            if buyer_percentage > 0:
                buyer_amount = agreement.total_amount * Decimal(buyer_percentage / 100)
                buyer_result = await self.release_payment(
                    escrow_id,
                    agreement.buyer.address,
                    buyer_amount,
                    private_key
                )
                results.append({"recipient": "buyer", "result": buyer_result})
            
            if seller_percentage > 0:
                seller_amount = agreement.total_amount * Decimal(seller_percentage / 100)
                seller_result = await self.release_payment(
                    escrow_id,
                    agreement.seller.address,
                    seller_amount,
                    private_key
                )
                results.append({"recipient": "seller", "result": seller_result})
            
            # Update status
            agreement.status = EscrowStatus.COMPLETED
            
            logger.info(
                f"Dispute resolved for escrow {escrow_id} by {arbitrator_address}, "
                f"buyer: {buyer_percentage}%, seller: {seller_percentage}%"
            )
            
            return {
                "escrow_id": escrow_id,
                "status": agreement.status.value,
                "arbitrator": arbitrator_address,
                "resolution": resolution,
                "payments": results,
                "resolved_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to resolve dispute for escrow {escrow_id}: {e}")
            raise
    
    async def get_escrow_details(self, escrow_id: str) -> Dict[str, Any]:
        """Get detailed information about an escrow"""
        try:
            if escrow_id not in self.escrows:
                raise ValueError(f"Escrow {escrow_id} not found")
            
            agreement = self.escrows[escrow_id]
            
            return {
                "escrow_id": escrow_id,
                "status": agreement.status.value,
                "payment_type": agreement.payment_type.value,
                "total_amount": float(agreement.total_amount),
                "currency": agreement.currency,
                "buyer": asdict(agreement.buyer),
                "seller": asdict(agreement.seller),
                "arbitrators": [asdict(arb) for arb in agreement.arbitrators],
                "milestones": [
                    {
                        "id": m.id,
                        "description": m.description,
                        "amount": float(m.amount),
                        "due_date": m.due_date.isoformat(),
                        "completed": m.completed,
                        "approved_by": m.approved_by
                    }
                    for m in agreement.milestones
                ],
                "dispute_timeout": agreement.dispute_timeout,
                "auto_release_timeout": agreement.auto_release_timeout,
                "completion_requirements": agreement.completion_requirements,
                "created_at": agreement.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get escrow details {escrow_id}: {e}")
            raise
    
    def _generate_escrow_id(self, buyer: str, seller: str) -> str:
        """Generate unique escrow ID"""
        timestamp = str(int(datetime.now().timestamp()))
        data = f"{buyer}{seller}{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _create_on_chain_escrow(
        self, 
        agreement: EscrowAgreement, 
        private_key: str
    ) -> str:
        """Create escrow on blockchain"""
        if not self.contract:
            return None
        
        # Implementation would interact with smart contract
        # For now, return mock transaction hash
        return f"0x{hashlib.sha256(agreement.escrow_id.encode()).hexdigest()}"
    
    async def _fund_on_chain_escrow(
        self,
        escrow_id: str,
        amount: Decimal,
        private_key: str
    ) -> str:
        """Fund escrow on blockchain"""
        if not self.contract:
            return None
        
        # Implementation would interact with smart contract
        return f"0x{hashlib.sha256(f'{escrow_id}_fund'.encode()).hexdigest()}"
    
    async def _release_milestone_payment(
        self,
        escrow_id: str,
        milestone_id: str,
        private_key: str
    ) -> str:
        """Release payment for completed milestone"""
        agreement = self.escrows[escrow_id]
        milestone = next(m for m in agreement.milestones if m.id == milestone_id)
        
        return await self.release_payment(
            escrow_id,
            agreement.seller.address,
            milestone.amount,
            private_key
        )
    
    async def _release_on_chain_payment(
        self,
        escrow_id: str,
        recipient: str,
        amount: Decimal,
        private_key: str
    ) -> str:
        """Release payment on blockchain"""
        if not self.contract:
            return None
        
        # Implementation would interact with smart contract
        return f"0x{hashlib.sha256(f'{escrow_id}_release'.encode()).hexdigest()}"
    
    async def _record_dispute_on_chain(
        self,
        escrow_id: str,
        reason: str,
        private_key: str
    ) -> str:
        """Record dispute on blockchain"""
        if not self.contract:
            return None
        
        # Implementation would interact with smart contract
        return f"0x{hashlib.sha256(f'{escrow_id}_dispute'.encode()).hexdigest()}"
    
    async def _notify_arbitrators(
        self,
        escrow_id: str,
        dispute_data: Dict[str, Any]
    ):
        """Notify arbitrators of dispute (placeholder)"""
        # Implementation would send notifications
        logger.info(f"Notifying arbitrators of dispute for escrow {escrow_id}")

# Global escrow manager instance
payment_escrow = SmartPaymentEscrow()