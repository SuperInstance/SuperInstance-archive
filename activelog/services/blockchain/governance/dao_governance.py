"""
DAO Governance System for ActiveLog
Decentralized governance for feature requests, proposals, and community decisions
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

from ..config.blockchain_config import (
    blockchain_config, 
    BlockchainNetwork, 
    ContractType
)

logger = logging.getLogger(__name__)

class ProposalType(Enum):
    FEATURE_REQUEST = "feature_request"
    SYSTEM_UPGRADE = "system_upgrade"
    PARAMETER_CHANGE = "parameter_change"
    TREASURY_SPENDING = "treasury_spending"
    PARTNERSHIP = "partnership"
    POLICY_CHANGE = "policy_change"
    EMERGENCY_ACTION = "emergency_action"

class ProposalStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class VoteType(Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"

class GovernanceRole(Enum):
    MEMBER = "member"
    DELEGATE = "delegate"
    GUARDIAN = "guardian"
    COUNCIL = "council"
    ADMIN = "admin"

@dataclass
class GovernanceMember:
    address: str
    voting_power: Decimal
    delegated_to: Optional[str]
    role: GovernanceRole
    joined_at: datetime
    reputation_score: float
    participation_rate: float
    last_activity: datetime

@dataclass
class Vote:
    voter: str
    proposal_id: str
    vote_type: VoteType
    voting_power: Decimal
    reason: Optional[str]
    timestamp: datetime

@dataclass
class ProposalExecution:
    action_type: str
    target_contract: Optional[str]
    function_call: Optional[str]
    parameters: Dict[str, Any]
    required_confirmations: int

@dataclass
class Proposal:
    id: str
    title: str
    description: str
    proposer: str
    proposal_type: ProposalType
    execution: Optional[ProposalExecution]
    voting_start: datetime
    voting_end: datetime
    min_quorum: Decimal
    approval_threshold: Decimal
    status: ProposalStatus
    votes: List[Vote]
    total_yes: Decimal
    total_no: Decimal
    total_abstain: Decimal
    discussion_url: Optional[str]
    created_at: datetime

    def __post_init__(self):
        if self.votes is None:
            self.votes = []

@dataclass
class Delegation:
    delegator: str
    delegatee: str
    voting_power: Decimal
    created_at: datetime
    expires_at: Optional[datetime]

@dataclass
class TreasuryProposal:
    recipient: str
    amount: Decimal
    currency: str
    purpose: str
    milestone_based: bool
    milestones: List[Dict[str, Any]]

class DAOGovernance:
    """Decentralized Autonomous Organization governance system"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.ETHEREUM):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.DAO_GOVERNANCE, 
            network
        )
        
        self.members: Dict[str, GovernanceMember] = {}
        self.proposals: Dict[str, Proposal] = {}
        self.delegations: Dict[str, Delegation] = {}
        self.voting_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Governance parameters
        self.min_proposal_threshold = Decimal('1000')  # Minimum tokens to create proposal
        self.default_voting_period = timedelta(days=7)
        self.default_execution_delay = timedelta(days=2)
        self.emergency_voting_period = timedelta(days=1)
        self.quorum_threshold = Decimal('0.1')  # 10% of total supply
        self.approval_threshold = Decimal('0.5')  # 50% of votes cast
        self.guardian_override_threshold = Decimal('0.8')  # 80% for guardian actions
        
        # Treasury management
        self.treasury_balance = {
            'ALOG': Decimal('10000000'),  # 10M ALOG tokens
            'ETH': Decimal('1000'),
            'USDC': Decimal('500000')
        }
        
        # Initialize default members
        self._init_default_members()
    
    def _init_default_members(self):
        """Initialize default governance members"""
        # Founder council members
        council_members = [
            ("0x1111111111111111111111111111111111111111", Decimal('50000')),
            ("0x2222222222222222222222222222222222222222", Decimal('45000')),
            ("0x3333333333333333333333333333333333333333", Decimal('40000'))
        ]
        
        for address, power in council_members:
            self.members[address] = GovernanceMember(
                address=address,
                voting_power=power,
                delegated_to=None,
                role=GovernanceRole.COUNCIL,
                joined_at=datetime.now(),
                reputation_score=1.0,
                participation_rate=0.95,
                last_activity=datetime.now()
            )
        
        # Guardian members
        guardian_members = [
            ("0x4444444444444444444444444444444444444444", Decimal('25000')),
            ("0x5555555555555555555555555555555555555555", Decimal('25000'))
        ]
        
        for address, power in guardian_members:
            self.members[address] = GovernanceMember(
                address=address,
                voting_power=power,
                delegated_to=None,
                role=GovernanceRole.GUARDIAN,
                joined_at=datetime.now(),
                reputation_score=0.98,
                participation_rate=0.90,
                last_activity=datetime.now()
            )
        
        logger.info(f"Initialized {len(self.members)} default governance members")
    
    async def create_proposal(
        self,
        proposer: str,
        title: str,
        description: str,
        proposal_type: ProposalType,
        execution: Optional[ProposalExecution] = None,
        voting_period_days: int = 7,
        min_quorum: Optional[Decimal] = None,
        approval_threshold: Optional[Decimal] = None,
        discussion_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new governance proposal"""
        try:
            # Verify proposer has sufficient voting power
            if proposer not in self.members:
                raise ValueError("Proposer is not a governance member")
            
            member = self.members[proposer]
            if member.voting_power < self.min_proposal_threshold:
                raise ValueError(f"Insufficient voting power. Required: {self.min_proposal_threshold}")
            
            # Generate proposal ID
            proposal_id = self._generate_proposal_id(proposer, title)
            
            # Set voting parameters
            voting_start = datetime.now()
            if proposal_type == ProposalType.EMERGENCY_ACTION:
                voting_end = voting_start + self.emergency_voting_period
            else:
                voting_end = voting_start + timedelta(days=voting_period_days)
            
            quorum = min_quorum or self.quorum_threshold
            threshold = approval_threshold or self.approval_threshold
            
            # Create proposal
            proposal = Proposal(
                id=proposal_id,
                title=title,
                description=description,
                proposer=proposer,
                proposal_type=proposal_type,
                execution=execution,
                voting_start=voting_start,
                voting_end=voting_end,
                min_quorum=quorum,
                approval_threshold=threshold,
                status=ProposalStatus.ACTIVE,
                votes=[],
                total_yes=Decimal('0'),
                total_no=Decimal('0'),
                total_abstain=Decimal('0'),
                discussion_url=discussion_url,
                created_at=datetime.now()
            )
            
            # Store proposal
            self.proposals[proposal_id] = proposal
            
            # Create voting session
            self.voting_sessions[proposal_id] = {
                "proposal_id": proposal_id,
                "voters": set(),
                "delegated_votes": {},
                "vote_history": []
            }
            
            # Schedule automatic closure
            asyncio.create_task(self._schedule_proposal_closure(proposal_id))
            
            logger.info(f"Created proposal {proposal_id}: {title}")
            
            return {
                "proposal_id": proposal_id,
                "title": title,
                "status": proposal.status.value,
                "voting_start": voting_start.isoformat(),
                "voting_end": voting_end.isoformat(),
                "min_quorum": float(quorum),
                "approval_threshold": float(threshold),
                "created_at": proposal.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def cast_vote(
        self,
        voter: str,
        proposal_id: str,
        vote_type: VoteType,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cast a vote on a proposal"""
        try:
            # Verify proposal exists and is active
            if proposal_id not in self.proposals:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            proposal = self.proposals[proposal_id]
            
            if proposal.status != ProposalStatus.ACTIVE:
                raise ValueError(f"Proposal {proposal_id} is not active for voting")
            
            if datetime.now() > proposal.voting_end:
                raise ValueError("Voting period has ended")
            
            # Verify voter is eligible
            if voter not in self.members:
                raise ValueError("Voter is not a governance member")
            
            member = self.members[voter]
            
            # Check if already voted
            existing_vote = next((v for v in proposal.votes if v.voter == voter), None)
            if existing_vote:
                raise ValueError("Already voted on this proposal")
            
            # Get effective voting power (including delegated power)
            effective_voting_power = await self._get_effective_voting_power(voter)
            
            # Create vote
            vote = Vote(
                voter=voter,
                proposal_id=proposal_id,
                vote_type=vote_type,
                voting_power=effective_voting_power,
                reason=reason,
                timestamp=datetime.now()
            )
            
            # Add vote to proposal
            proposal.votes.append(vote)
            
            # Update vote tallies
            if vote_type == VoteType.YES:
                proposal.total_yes += effective_voting_power
            elif vote_type == VoteType.NO:
                proposal.total_no += effective_voting_power
            else:  # ABSTAIN
                proposal.total_abstain += effective_voting_power
            
            # Update voting session
            session = self.voting_sessions[proposal_id]
            session["voters"].add(voter)
            session["vote_history"].append({
                "voter": voter,
                "vote": vote_type.value,
                "power": float(effective_voting_power),
                "timestamp": vote.timestamp.isoformat()
            })
            
            # Update member activity
            member.last_activity = datetime.now()
            member.participation_rate = await self._calculate_participation_rate(voter)
            
            # Check if proposal should be closed early
            if await self._should_close_early(proposal_id):
                await self._close_proposal(proposal_id)
            
            logger.info(f"Vote cast by {voter} on proposal {proposal_id}: {vote_type.value}")
            
            return {
                "proposal_id": proposal_id,
                "voter": voter,
                "vote": vote_type.value,
                "voting_power": float(effective_voting_power),
                "proposal_status": proposal.status.value,
                "current_results": {
                    "yes": float(proposal.total_yes),
                    "no": float(proposal.total_no),
                    "abstain": float(proposal.total_abstain)
                },
                "voted_at": vote.timestamp.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to cast vote: {e}")
            raise
    
    async def delegate_voting_power(
        self,
        delegator: str,
        delegatee: str,
        expires_in_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """Delegate voting power to another member"""
        try:
            # Verify both parties are governance members
            if delegator not in self.members or delegatee not in self.members:
                raise ValueError("Both parties must be governance members")
            
            if delegator == delegatee:
                raise ValueError("Cannot delegate to yourself")
            
            delegator_member = self.members[delegator]
            
            # Check if already delegated
            existing_delegation = next(
                (d for d in self.delegations.values() if d.delegator == delegator),
                None
            )
            if existing_delegation:
                raise ValueError("Already delegated voting power")
            
            # Calculate expiration
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now() + timedelta(days=expires_in_days)
            
            # Create delegation
            delegation_id = f"{delegator}_{delegatee}_{int(datetime.now().timestamp())}"
            delegation = Delegation(
                delegator=delegator,
                delegatee=delegatee,
                voting_power=delegator_member.voting_power,
                created_at=datetime.now(),
                expires_at=expires_at
            )
            
            # Store delegation
            self.delegations[delegation_id] = delegation
            
            # Update member delegation status
            delegator_member.delegated_to = delegatee
            
            logger.info(f"Delegated voting power from {delegator} to {delegatee}")
            
            return {
                "delegation_id": delegation_id,
                "delegator": delegator,
                "delegatee": delegatee,
                "voting_power": float(delegation.voting_power),
                "expires_at": expires_at.isoformat() if expires_at else None,
                "created_at": delegation.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to delegate voting power: {e}")
            raise
    
    async def execute_proposal(
        self,
        proposal_id: str,
        executor: str
    ) -> Dict[str, Any]:
        """Execute a passed proposal"""
        try:
            if proposal_id not in self.proposals:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            proposal = self.proposals[proposal_id]
            
            # Verify proposal is ready for execution
            if proposal.status != ProposalStatus.PASSED:
                raise ValueError(f"Proposal {proposal_id} has not passed")
            
            # Verify executor authority
            executor_member = self.members.get(executor)
            if not executor_member or executor_member.role not in [
                GovernanceRole.COUNCIL, 
                GovernanceRole.GUARDIAN, 
                GovernanceRole.ADMIN
            ]:
                raise ValueError("Executor does not have sufficient authority")
            
            # Check execution delay (except for emergency actions)
            if proposal.proposal_type != ProposalType.EMERGENCY_ACTION:
                execution_ready = proposal.voting_end + self.default_execution_delay
                if datetime.now() < execution_ready:
                    raise ValueError("Execution delay period not yet passed")
            
            # Execute based on proposal type
            execution_result = await self._execute_proposal_action(proposal, executor)
            
            # Update proposal status
            proposal.status = ProposalStatus.EXECUTED
            
            logger.info(f"Executed proposal {proposal_id} by {executor}")
            
            return {
                "proposal_id": proposal_id,
                "executor": executor,
                "status": proposal.status.value,
                "execution_result": execution_result,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to execute proposal {proposal_id}: {e}")
            raise
    
    async def get_proposal_details(self, proposal_id: str) -> Dict[str, Any]:
        """Get detailed information about a proposal"""
        try:
            if proposal_id not in self.proposals:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            proposal = self.proposals[proposal_id]
            
            # Calculate voting statistics
            total_votes = proposal.total_yes + proposal.total_no + proposal.total_abstain
            total_supply = sum(member.voting_power for member in self.members.values())
            
            quorum_reached = total_votes >= (proposal.min_quorum * total_supply)
            approval_reached = False
            
            if total_votes > 0:
                approval_rate = proposal.total_yes / total_votes
                approval_reached = approval_rate >= proposal.approval_threshold
            
            return {
                "proposal_id": proposal_id,
                "title": proposal.title,
                "description": proposal.description,
                "proposer": proposal.proposer,
                "type": proposal.proposal_type.value,
                "status": proposal.status.value,
                "voting_period": {
                    "start": proposal.voting_start.isoformat(),
                    "end": proposal.voting_end.isoformat(),
                    "is_active": proposal.voting_start <= datetime.now() <= proposal.voting_end
                },
                "voting_stats": {
                    "yes_votes": float(proposal.total_yes),
                    "no_votes": float(proposal.total_no),
                    "abstain_votes": float(proposal.total_abstain),
                    "total_votes": float(total_votes),
                    "participation_rate": float(total_votes / total_supply) if total_supply > 0 else 0,
                    "quorum_required": float(proposal.min_quorum),
                    "quorum_reached": quorum_reached,
                    "approval_threshold": float(proposal.approval_threshold),
                    "approval_reached": approval_reached
                },
                "execution": asdict(proposal.execution) if proposal.execution else None,
                "discussion_url": proposal.discussion_url,
                "vote_count": len(proposal.votes),
                "created_at": proposal.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get proposal details {proposal_id}: {e}")
            raise
    
    async def get_governance_stats(self) -> Dict[str, Any]:
        """Get overall governance statistics"""
        try:
            total_members = len(self.members)
            active_members = len([m for m in self.members.values() if m.last_activity > datetime.now() - timedelta(days=30)])
            total_supply = sum(member.voting_power for member in self.members.values())
            
            # Role distribution
            role_distribution = {}
            for role in GovernanceRole:
                role_distribution[role.value] = len([
                    m for m in self.members.values() if m.role == role
                ])
            
            # Proposal statistics
            proposal_stats = {}
            for status in ProposalStatus:
                proposal_stats[status.value] = len([
                    p for p in self.proposals.values() if p.status == status
                ])
            
            # Recent activity
            recent_proposals = len([
                p for p in self.proposals.values() 
                if p.created_at > datetime.now() - timedelta(days=30)
            ])
            
            recent_votes = sum([
                len([v for v in p.votes if v.timestamp > datetime.now() - timedelta(days=30)])
                for p in self.proposals.values()
            ])
            
            return {
                "membership": {
                    "total_members": total_members,
                    "active_members": active_members,
                    "total_voting_power": float(total_supply),
                    "role_distribution": role_distribution
                },
                "proposals": {
                    "total_proposals": len(self.proposals),
                    "by_status": proposal_stats,
                    "recent_proposals_30d": recent_proposals
                },
                "activity": {
                    "recent_votes_30d": recent_votes,
                    "active_delegations": len(self.delegations),
                    "treasury_balance": {k: float(v) for k, v in self.treasury_balance.items()}
                },
                "parameters": {
                    "min_proposal_threshold": float(self.min_proposal_threshold),
                    "default_voting_period_days": self.default_voting_period.days,
                    "quorum_threshold": float(self.quorum_threshold),
                    "approval_threshold": float(self.approval_threshold)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get governance stats: {e}")
            raise
    
    async def create_treasury_proposal(
        self,
        proposer: str,
        recipient: str,
        amount: Decimal,
        currency: str,
        purpose: str,
        milestone_based: bool = False,
        milestones: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a treasury spending proposal"""
        try:
            # Verify sufficient treasury balance
            if currency not in self.treasury_balance:
                raise ValueError(f"Currency {currency} not available in treasury")
            
            if amount > self.treasury_balance[currency]:
                raise ValueError(f"Insufficient treasury balance. Available: {self.treasury_balance[currency]}")
            
            # Create treasury proposal details
            treasury_proposal = TreasuryProposal(
                recipient=recipient,
                amount=amount,
                currency=currency,
                purpose=purpose,
                milestone_based=milestone_based,
                milestones=milestones or []
            )
            
            # Create execution plan
            execution = ProposalExecution(
                action_type="treasury_transfer",
                target_contract="treasury",
                function_call="transfer",
                parameters={
                    "recipient": recipient,
                    "amount": float(amount),
                    "currency": currency,
                    "treasury_proposal": asdict(treasury_proposal)
                },
                required_confirmations=2
            )
            
            # Create proposal with higher quorum for treasury spending
            higher_quorum = self.quorum_threshold * Decimal('2')  # 20% for treasury
            
            result = await self.create_proposal(
                proposer=proposer,
                title=f"Treasury Proposal: {amount} {currency} to {recipient}",
                description=f"Purpose: {purpose}\n\nRecipient: {recipient}\nAmount: {amount} {currency}",
                proposal_type=ProposalType.TREASURY_SPENDING,
                execution=execution,
                min_quorum=higher_quorum,
                approval_threshold=Decimal('0.6')  # 60% approval for treasury
            )
            
            logger.info(f"Created treasury proposal for {amount} {currency} to {recipient}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to create treasury proposal: {e}")
            raise
    
    async def _get_effective_voting_power(self, voter: str) -> Decimal:
        """Get effective voting power including delegated votes"""
        if voter not in self.members:
            return Decimal('0')
        
        member = self.members[voter]
        effective_power = member.voting_power
        
        # Add delegated power from others
        for delegation in self.delegations.values():
            if (delegation.delegatee == voter and 
                (delegation.expires_at is None or delegation.expires_at > datetime.now())):
                effective_power += delegation.voting_power
        
        return effective_power
    
    async def _calculate_participation_rate(self, voter: str) -> float:
        """Calculate member's participation rate"""
        if voter not in self.members:
            return 0.0
        
        # Count votes in last 90 days
        recent_votes = 0
        recent_proposals = 0
        
        cutoff_date = datetime.now() - timedelta(days=90)
        
        for proposal in self.proposals.values():
            if proposal.created_at > cutoff_date:
                recent_proposals += 1
                voter_voted = any(vote.voter == voter for vote in proposal.votes)
                if voter_voted:
                    recent_votes += 1
        
        return recent_votes / recent_proposals if recent_proposals > 0 else 0.0
    
    async def _should_close_early(self, proposal_id: str) -> bool:
        """Check if proposal should be closed early due to overwhelming consensus"""
        if proposal_id not in self.proposals:
            return False
        
        proposal = self.proposals[proposal_id]
        total_supply = sum(member.voting_power for member in self.members.values())
        total_votes = proposal.total_yes + proposal.total_no + proposal.total_abstain
        
        # Close early if 80% of supply has voted
        if total_votes >= (total_supply * Decimal('0.8')):
            return True
        
        # Close early if overwhelming majority (90%+ yes or no)
        if total_votes > 0:
            yes_ratio = proposal.total_yes / total_votes
            no_ratio = proposal.total_no / total_votes
            
            if yes_ratio >= Decimal('0.9') or no_ratio >= Decimal('0.9'):
                return True
        
        return False
    
    async def _close_proposal(self, proposal_id: str):
        """Close a proposal and determine outcome"""
        if proposal_id not in self.proposals:
            return
        
        proposal = self.proposals[proposal_id]
        total_supply = sum(member.voting_power for member in self.members.values())
        total_votes = proposal.total_yes + proposal.total_no + proposal.total_abstain
        
        # Check quorum
        quorum_met = total_votes >= (proposal.min_quorum * total_supply)
        
        if not quorum_met:
            proposal.status = ProposalStatus.REJECTED
            logger.info(f"Proposal {proposal_id} rejected - quorum not met")
            return
        
        # Check approval
        if total_votes > 0:
            approval_rate = proposal.total_yes / total_votes
            if approval_rate >= proposal.approval_threshold:
                proposal.status = ProposalStatus.PASSED
                logger.info(f"Proposal {proposal_id} passed with {approval_rate:.2%} approval")
            else:
                proposal.status = ProposalStatus.REJECTED
                logger.info(f"Proposal {proposal_id} rejected with {approval_rate:.2%} approval")
        else:
            proposal.status = ProposalStatus.REJECTED
    
    async def _schedule_proposal_closure(self, proposal_id: str):
        """Schedule automatic proposal closure"""
        if proposal_id not in self.proposals:
            return
        
        proposal = self.proposals[proposal_id]
        
        # Wait until voting end time
        now = datetime.now()
        if proposal.voting_end > now:
            wait_time = (proposal.voting_end - now).total_seconds()
            await asyncio.sleep(wait_time)
        
        # Close proposal if still active
        if proposal.status == ProposalStatus.ACTIVE:
            await self._close_proposal(proposal_id)
    
    async def _execute_proposal_action(
        self,
        proposal: Proposal,
        executor: str
    ) -> Dict[str, Any]:
        """Execute the action defined in a proposal"""
        if not proposal.execution:
            return {"status": "no_action_required"}
        
        execution = proposal.execution
        
        if execution.action_type == "treasury_transfer":
            # Execute treasury transfer
            params = execution.parameters
            recipient = params["recipient"]
            amount = Decimal(str(params["amount"]))
            currency = params["currency"]
            
            # Update treasury balance
            self.treasury_balance[currency] -= amount
            
            logger.info(f"Treasury transfer executed: {amount} {currency} to {recipient}")
            
            return {
                "status": "executed",
                "action": "treasury_transfer",
                "recipient": recipient,
                "amount": float(amount),
                "currency": currency,
                "remaining_balance": float(self.treasury_balance[currency])
            }
        
        elif execution.action_type == "parameter_change":
            # Execute parameter change
            params = execution.parameters
            param_name = params.get("parameter_name")
            new_value = params.get("new_value")
            
            # Update governance parameters
            if hasattr(self, param_name):
                setattr(self, param_name, Decimal(str(new_value)))
                logger.info(f"Parameter {param_name} updated to {new_value}")
                
                return {
                    "status": "executed",
                    "action": "parameter_change",
                    "parameter": param_name,
                    "new_value": new_value
                }
        
        return {"status": "action_not_implemented", "action_type": execution.action_type}
    
    def _generate_proposal_id(self, proposer: str, title: str) -> str:
        """Generate unique proposal ID"""
        timestamp = str(int(datetime.now().timestamp()))
        data = f"{proposer}{title}{timestamp}"
        return f"prop_{hashlib.sha256(data.encode()).hexdigest()[:12]}"

# Global DAO governance instance
dao_governance = DAOGovernance()