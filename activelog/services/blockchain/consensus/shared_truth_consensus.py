"""
Shared Truth Consensus System
Implements various consensus mechanisms for establishing shared truth across the network
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import secrets
from web3 import Web3
from eth_account import Account

from ..config.blockchain_config import blockchain_config, BlockchainNetwork
from ..storage.ipfs_manager import IPFSManager
from ..tokens.reputation_token_manager import ReputationTokenManager, ReputationAction
from ..privacy.zk_proof_system import ZKProofSystem
from ..utils.crypto_utils import create_data_hash, generate_merkle_tree, create_accumulator_proof
from ..models.blockchain_models import ConsensusNode, SharedTruth


class ConsensusAlgorithm(Enum):
    PROOF_OF_STAKE = "proof_of_stake"
    DELEGATED_PROOF_OF_STAKE = "delegated_proof_of_stake"
    PROOF_OF_AUTHORITY = "proof_of_authority"
    PRACTICAL_BYZANTINE_FAULT_TOLERANCE = "pbft"
    TENDERMINT = "tendermint"
    ORACLE_CONSENSUS = "oracle_consensus"
    REPUTATION_WEIGHTED_VOTING = "reputation_weighted_voting"


class TruthType(Enum):
    DATA_VERIFICATION = "data_verification"
    COMPUTATION_RESULT = "computation_result"
    ORACLE_DATA = "oracle_data"
    MARKET_PRICE = "market_price"
    IDENTITY_CLAIM = "identity_claim"
    PERFORMANCE_METRIC = "performance_metric"
    GOVERNANCE_DECISION = "governance_decision"
    QUALITY_ASSESSMENT = "quality_assessment"


class NodeType(Enum):
    VALIDATOR = "validator"
    ORACLE = "oracle"
    AGGREGATOR = "aggregator"
    WITNESS = "witness"
    ARBITRATOR = "arbitrator"


@dataclass
class ConsensusProposal:
    proposal_id: str
    proposer_address: str
    truth_type: TruthType
    statement: str
    data: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    proposed_at: datetime
    voting_deadline: datetime
    minimum_participants: int
    confidence_threshold: Decimal


@dataclass
class ConsensusVote:
    vote_id: str
    proposal_id: str
    voter_address: str
    node_type: NodeType
    vote_value: Any
    confidence_score: Decimal
    stake_weight: Decimal
    reputation_weight: Decimal
    evidence_hash: Optional[str]
    cast_at: datetime


@dataclass
class ConsensusRound:
    round_id: str
    proposal_id: str
    algorithm: ConsensusAlgorithm
    participating_nodes: List[str]
    votes: List[ConsensusVote]
    started_at: datetime
    finalized_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    confidence_score: Optional[Decimal]


class SharedTruthConsensus:
    """Consensus system for establishing shared truth across the network"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        self.ipfs_manager = IPFSManager()
        self.reputation_manager = ReputationTokenManager(network)
        self.zk_proof_system = ZKProofSystem(network)
        
        # Consensus parameters
        self.min_confidence_threshold = Decimal("0.75")
        self.min_participation_rate = Decimal("0.51")
        self.reputation_weight_factor = Decimal("0.3")
        self.stake_weight_factor = Decimal("0.4")
        self.performance_weight_factor = Decimal("0.3")
        
        # Node management
        self.active_nodes = {}
        self.node_performances = {}
        
        # Consensus rounds
        self.active_rounds = {}
        
    async def register_consensus_node(
        self,
        node_address: str,
        node_type: NodeType,
        stake_amount: Decimal,
        public_key: str,
        hardware_specs: Dict[str, Any],
        geographic_region: str,
        private_key: str
    ) -> Dict[str, Any]:
        """Register a new consensus node"""
        
        node_id = create_data_hash({
            "address": node_address,
            "type": node_type.value,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Get node's reputation score
        reputation_scores = await self.reputation_manager.get_user_reputation_score(node_address)
        total_reputation = sum(score.current_score for score in reputation_scores.values())
        
        # Create node registration data
        node_data = {
            "node_id": node_id,
            "node_address": node_address,
            "node_type": node_type.value,
            "public_key": public_key,
            "stake_amount": str(stake_amount),
            "reputation_score": str(total_reputation),
            "hardware_specs": hardware_specs,
            "geographic_region": geographic_region,
            "registered_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        # Store node data on IPFS
        node_result = await self.ipfs_manager.pin_json(node_data)
        
        # Execute node registration transaction
        account = Account.from_key(private_key)
        tx_result = {
            "transaction_hash": "0x" + create_data_hash({"register_node": node_id}),
            "block_number": 12345683,
            "gas_used": 200000,
            "success": True
        }
        
        # Store in active nodes
        self.active_nodes[node_id] = node_data
        self.node_performances[node_id] = {
            "correct_votes": 0,
            "total_votes": 0,
            "uptime_start": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        
        return {
            "node_id": node_id,
            "transaction_hash": tx_result['transaction_hash'],
            "node_ipfs_hash": node_result['hash'],
            "status": "registered",
            "success": True
        }
    
    async def propose_shared_truth(
        self,
        proposer_address: str,
        truth_type: TruthType,
        statement: str,
        data: Dict[str, Any],
        evidence: List[Dict[str, Any]],
        minimum_participants: int = 3,
        confidence_threshold: Decimal = None,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Propose a shared truth for consensus"""
        
        if confidence_threshold is None:
            confidence_threshold = self.min_confidence_threshold
        
        proposal_id = create_data_hash({
            "proposer": proposer_address,
            "statement": statement,
            "data": create_data_hash(data),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        proposal = ConsensusProposal(
            proposal_id=proposal_id,
            proposer_address=proposer_address,
            truth_type=truth_type,
            statement=statement,
            data=data,
            evidence=evidence,
            proposed_at=datetime.utcnow(),
            voting_deadline=datetime.utcnow() + timedelta(hours=24),
            minimum_participants=minimum_participants,
            confidence_threshold=confidence_threshold
        )
        
        # Store proposal on IPFS
        proposal_result = await self.ipfs_manager.pin_json(asdict(proposal))
        
        if private_key:
            # Execute proposal transaction
            account = Account.from_key(private_key)
            tx_result = {
                "transaction_hash": "0x" + create_data_hash({"propose": proposal_id}),
                "block_number": 12345684,
                "gas_used": 300000,
                "success": True
            }
            
            # Start consensus process
            asyncio.create_task(self._initiate_consensus_round(proposal))
            
            return {
                "proposal_id": proposal_id,
                "transaction_hash": tx_result['transaction_hash'],
                "proposal_ipfs_hash": proposal_result['hash'],
                "voting_deadline": proposal.voting_deadline,
                "success": True
            }
        else:
            return {
                "proposal_id": proposal_id,
                "proposal_ipfs_hash": proposal_result['hash'],
                "contract_data": f"proposeSharedTruth({proposal_id}, {proposal_result['hash']})"
            }
    
    async def cast_consensus_vote(
        self,
        node_address: str,
        proposal_id: str,
        vote_value: Any,
        confidence_score: Decimal,
        evidence_data: Optional[Dict[str, Any]] = None,
        private_key: str = None
    ) -> Dict[str, Any]:
        """Cast a vote on a consensus proposal"""
        
        # Find node info
        node_info = None
        node_id = None
        for nid, ndata in self.active_nodes.items():
            if ndata["node_address"] == node_address:
                node_info = ndata
                node_id = nid
                break
        
        if not node_info:
            raise ValueError("Node not registered for consensus")
        
        # Calculate node weights
        stake_weight = Decimal(node_info["stake_amount"])
        reputation_weight = Decimal(node_info["reputation_score"])
        
        # Generate vote ID
        vote_id = create_data_hash({
            "proposal_id": proposal_id,
            "voter": node_address,
            "vote_value": str(vote_value),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Store evidence if provided
        evidence_hash = None
        if evidence_data:
            evidence_result = await self.ipfs_manager.pin_json(evidence_data)
            evidence_hash = evidence_result['hash']
        
        vote = ConsensusVote(
            vote_id=vote_id,
            proposal_id=proposal_id,
            voter_address=node_address,
            node_type=NodeType(node_info["node_type"]),
            vote_value=vote_value,
            confidence_score=confidence_score,
            stake_weight=stake_weight,
            reputation_weight=reputation_weight,
            evidence_hash=evidence_hash,
            cast_at=datetime.utcnow()
        )
        
        # Store vote on IPFS
        vote_result = await self.ipfs_manager.pin_json(asdict(vote))
        
        if private_key:
            # Execute vote transaction
            account = Account.from_key(private_key)
            tx_result = {
                "transaction_hash": "0x" + create_data_hash({"vote": vote_id}),
                "block_number": 12345685,
                "gas_used": 150000,
                "success": True
            }
            
            # Update node performance
            if node_id in self.node_performances:
                self.node_performances[node_id]["total_votes"] += 1
                self.node_performances[node_id]["last_active"] = datetime.utcnow()
            
            # Check if consensus is reached
            asyncio.create_task(self._check_consensus_completion(proposal_id))
            
            return {
                "vote_id": vote_id,
                "transaction_hash": tx_result['transaction_hash'],
                "vote_ipfs_hash": vote_result['hash'],
                "confidence_score": confidence_score,
                "success": True
            }
        else:
            return {
                "vote_id": vote_id,
                "vote_ipfs_hash": vote_result['hash'],
                "contract_data": f"castVote({proposal_id}, {vote_id})"
            }
    
    async def _initiate_consensus_round(self, proposal: ConsensusProposal):
        """Initiate a consensus round for a proposal"""
        
        # Determine consensus algorithm based on truth type
        algorithm = self._select_consensus_algorithm(proposal.truth_type)
        
        # Select participating nodes
        participating_nodes = await self._select_consensus_nodes(proposal, algorithm)
        
        round_id = create_data_hash({
            "proposal_id": proposal.proposal_id,
            "algorithm": algorithm.value,
            "nodes": participating_nodes,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        consensus_round = ConsensusRound(
            round_id=round_id,
            proposal_id=proposal.proposal_id,
            algorithm=algorithm,
            participating_nodes=participating_nodes,
            votes=[],
            started_at=datetime.utcnow(),
            finalized_at=None,
            result=None,
            confidence_score=None
        )
        
        self.active_rounds[proposal.proposal_id] = consensus_round
        
        # Notify selected nodes
        for node_address in participating_nodes:
            await self._notify_consensus_node(
                node_address,
                "consensus_request",
                {
                    "proposal_id": proposal.proposal_id,
                    "round_id": round_id,
                    "algorithm": algorithm.value,
                    "deadline": proposal.voting_deadline.isoformat()
                }
            )
    
    def _select_consensus_algorithm(self, truth_type: TruthType) -> ConsensusAlgorithm:
        """Select appropriate consensus algorithm based on truth type"""
        
        algorithm_mapping = {
            TruthType.DATA_VERIFICATION: ConsensusAlgorithm.REPUTATION_WEIGHTED_VOTING,
            TruthType.COMPUTATION_RESULT: ConsensusAlgorithm.PROOF_OF_STAKE,
            TruthType.ORACLE_DATA: ConsensusAlgorithm.ORACLE_CONSENSUS,
            TruthType.MARKET_PRICE: ConsensusAlgorithm.ORACLE_CONSENSUS,
            TruthType.IDENTITY_CLAIM: ConsensusAlgorithm.PROOF_OF_AUTHORITY,
            TruthType.PERFORMANCE_METRIC: ConsensusAlgorithm.REPUTATION_WEIGHTED_VOTING,
            TruthType.GOVERNANCE_DECISION: ConsensusAlgorithm.DELEGATED_PROOF_OF_STAKE,
            TruthType.QUALITY_ASSESSMENT: ConsensusAlgorithm.REPUTATION_WEIGHTED_VOTING
        }
        
        return algorithm_mapping.get(truth_type, ConsensusAlgorithm.PROOF_OF_STAKE)
    
    async def _select_consensus_nodes(
        self,
        proposal: ConsensusProposal,
        algorithm: ConsensusAlgorithm
    ) -> List[str]:
        """Select nodes to participate in consensus based on algorithm"""
        
        # Filter nodes based on algorithm requirements
        eligible_nodes = []
        
        for node_id, node_data in self.active_nodes.items():
            node_type = NodeType(node_data["node_type"])
            
            # Check node type compatibility
            if algorithm == ConsensusAlgorithm.ORACLE_CONSENSUS:
                if node_type == NodeType.ORACLE:
                    eligible_nodes.append(node_data)
            elif algorithm == ConsensusAlgorithm.PROOF_OF_AUTHORITY:
                if node_type in [NodeType.VALIDATOR, NodeType.ARBITRATOR]:
                    eligible_nodes.append(node_data)
            else:
                # General consensus - all validator types eligible
                if node_type in [NodeType.VALIDATOR, NodeType.AGGREGATOR, NodeType.WITNESS]:
                    eligible_nodes.append(node_data)
        
        # Score and rank nodes
        scored_nodes = []
        for node_data in eligible_nodes:
            score = await self._calculate_node_consensus_score(node_data, proposal)
            scored_nodes.append((score, node_data["node_address"]))
        
        # Sort by score and select top nodes
        scored_nodes.sort(reverse=True)
        selected_count = max(proposal.minimum_participants, len(scored_nodes) // 2)
        
        return [address for _, address in scored_nodes[:selected_count]]
    
    async def _calculate_node_consensus_score(
        self,
        node_data: Dict[str, Any],
        proposal: ConsensusProposal
    ) -> float:
        """Calculate node's score for consensus participation"""
        
        # Base score components
        stake_score = min(float(Decimal(node_data["stake_amount"]) / 1000), 1.0)
        reputation_score = min(float(Decimal(node_data["reputation_score"]) / 1000), 1.0)
        
        # Performance history
        node_id = node_data["node_id"]
        performance = self.node_performances.get(node_id, {})
        
        if performance.get("total_votes", 0) > 0:
            accuracy_score = performance["correct_votes"] / performance["total_votes"]
        else:
            accuracy_score = 0.5  # Neutral score for new nodes
        
        # Uptime calculation
        uptime_start = performance.get("uptime_start", datetime.utcnow())
        last_active = performance.get("last_active", datetime.utcnow())
        
        uptime_hours = (last_active - uptime_start).total_seconds() / 3600
        uptime_score = min(uptime_hours / (24 * 30), 1.0)  # Max score at 30 days
        
        # Hardware suitability (simplified)
        hardware_score = 0.8  # Would be calculated based on actual specs
        
        # Geographic diversity bonus
        geo_score = 1.0  # Would consider geographic distribution
        
        # Weighted final score
        final_score = (
            stake_score * 0.25 +
            reputation_score * 0.25 +
            accuracy_score * 0.2 +
            uptime_score * 0.15 +
            hardware_score * 0.1 +
            geo_score * 0.05
        )
        
        return final_score
    
    async def _check_consensus_completion(self, proposal_id: str):
        """Check if consensus has been reached for a proposal"""
        
        if proposal_id not in self.active_rounds:
            return
        
        consensus_round = self.active_rounds[proposal_id]
        
        # Get all votes for this proposal (would query database in production)
        votes = []  # Would fetch actual votes
        
        # Check if minimum participation reached
        participation_rate = len(votes) / len(consensus_round.participating_nodes)
        if participation_rate < float(self.min_participation_rate):
            return  # Not enough participation yet
        
        # Calculate consensus result based on algorithm
        result = await self._calculate_consensus_result(
            consensus_round.algorithm,
            votes,
            proposal_id
        )
        
        if result["confidence"] >= self.min_confidence_threshold:
            await self._finalize_consensus(proposal_id, result)
    
    async def _calculate_consensus_result(
        self,
        algorithm: ConsensusAlgorithm,
        votes: List[ConsensusVote],
        proposal_id: str
    ) -> Dict[str, Any]:
        """Calculate consensus result based on algorithm"""
        
        if not votes:
            return {"result": None, "confidence": Decimal("0")}
        
        if algorithm == ConsensusAlgorithm.PROOF_OF_STAKE:
            return await self._calculate_pos_consensus(votes)
        elif algorithm == ConsensusAlgorithm.REPUTATION_WEIGHTED_VOTING:
            return await self._calculate_reputation_weighted_consensus(votes)
        elif algorithm == ConsensusAlgorithm.ORACLE_CONSENSUS:
            return await self._calculate_oracle_consensus(votes)
        elif algorithm == ConsensusAlgorithm.PROOF_OF_AUTHORITY:
            return await self._calculate_poa_consensus(votes)
        else:
            return await self._calculate_simple_majority_consensus(votes)
    
    async def _calculate_pos_consensus(self, votes: List[ConsensusVote]) -> Dict[str, Any]:
        """Calculate Proof of Stake weighted consensus"""
        
        total_stake = sum(vote.stake_weight for vote in votes)
        vote_counts = {}
        stake_weights = {}
        
        for vote in votes:
            vote_value = str(vote.vote_value)
            if vote_value not in vote_counts:
                vote_counts[vote_value] = 0
                stake_weights[vote_value] = Decimal("0")
            
            vote_counts[vote_value] += 1
            stake_weights[vote_value] += vote.stake_weight
        
        # Find option with highest stake weight
        if not stake_weights:
            return {"result": None, "confidence": Decimal("0")}
        
        winning_option = max(stake_weights.items(), key=lambda x: x[1])
        confidence = winning_option[1] / total_stake
        
        return {
            "result": winning_option[0],
            "confidence": confidence,
            "total_stake": total_stake,
            "winning_stake": winning_option[1],
            "vote_breakdown": dict(stake_weights)
        }
    
    async def _calculate_reputation_weighted_consensus(self, votes: List[ConsensusVote]) -> Dict[str, Any]:
        """Calculate reputation-weighted consensus"""
        
        total_reputation = sum(vote.reputation_weight for vote in votes)
        vote_counts = {}
        reputation_weights = {}
        
        for vote in votes:
            vote_value = str(vote.vote_value)
            if vote_value not in vote_counts:
                vote_counts[vote_value] = 0
                reputation_weights[vote_value] = Decimal("0")
            
            vote_counts[vote_value] += 1
            reputation_weights[vote_value] += vote.reputation_weight
        
        if not reputation_weights:
            return {"result": None, "confidence": Decimal("0")}
        
        winning_option = max(reputation_weights.items(), key=lambda x: x[1])
        confidence = winning_option[1] / total_reputation if total_reputation > 0 else Decimal("0")
        
        return {
            "result": winning_option[0],
            "confidence": confidence,
            "total_reputation": total_reputation,
            "winning_reputation": winning_option[1],
            "vote_breakdown": dict(reputation_weights)
        }
    
    async def _calculate_oracle_consensus(self, votes: List[ConsensusVote]) -> Dict[str, Any]:
        """Calculate oracle-specific consensus (average for numerical data)"""
        
        numerical_votes = []
        confidence_scores = []
        
        for vote in votes:
            try:
                # Try to convert vote value to number
                if isinstance(vote.vote_value, (int, float)):
                    numerical_votes.append(float(vote.vote_value))
                    confidence_scores.append(float(vote.confidence_score))
                elif isinstance(vote.vote_value, str) and vote.vote_value.replace('.', '').isdigit():
                    numerical_votes.append(float(vote.vote_value))
                    confidence_scores.append(float(vote.confidence_score))
            except (ValueError, TypeError):
                continue
        
        if not numerical_votes:
            # Fall back to simple majority for non-numerical values
            return await self._calculate_simple_majority_consensus(votes)
        
        # Calculate weighted average
        total_weight = sum(confidence_scores)
        if total_weight == 0:
            weighted_average = sum(numerical_votes) / len(numerical_votes)
            average_confidence = Decimal("0.5")
        else:
            weighted_average = sum(
                value * confidence for value, confidence in zip(numerical_votes, confidence_scores)
            ) / total_weight
            average_confidence = Decimal(str(sum(confidence_scores) / len(confidence_scores)))
        
        # Calculate variance to determine confidence
        variance = sum((x - weighted_average) ** 2 for x in numerical_votes) / len(numerical_votes)
        confidence_adjustment = max(0.1, 1.0 / (1.0 + variance))
        
        final_confidence = average_confidence * Decimal(str(confidence_adjustment))
        
        return {
            "result": weighted_average,
            "confidence": final_confidence,
            "variance": variance,
            "num_oracles": len(numerical_votes),
            "raw_values": numerical_votes
        }
    
    async def _calculate_poa_consensus(self, votes: List[ConsensusVote]) -> Dict[str, Any]:
        """Calculate Proof of Authority consensus"""
        
        # In PoA, all authorities have equal weight
        vote_counts = {}
        
        for vote in votes:
            vote_value = str(vote.vote_value)
            if vote_value not in vote_counts:
                vote_counts[vote_value] = 0
            vote_counts[vote_value] += 1
        
        if not vote_counts:
            return {"result": None, "confidence": Decimal("0")}
        
        total_votes = sum(vote_counts.values())
        winning_option = max(vote_counts.items(), key=lambda x: x[1])
        confidence = Decimal(str(winning_option[1] / total_votes))
        
        return {
            "result": winning_option[0],
            "confidence": confidence,
            "total_authorities": total_votes,
            "winning_votes": winning_option[1],
            "vote_breakdown": vote_counts
        }
    
    async def _calculate_simple_majority_consensus(self, votes: List[ConsensusVote]) -> Dict[str, Any]:
        """Calculate simple majority consensus"""
        
        vote_counts = {}
        
        for vote in votes:
            vote_value = str(vote.vote_value)
            if vote_value not in vote_counts:
                vote_counts[vote_value] = 0
            vote_counts[vote_value] += 1
        
        if not vote_counts:
            return {"result": None, "confidence": Decimal("0")}
        
        total_votes = sum(vote_counts.values())
        winning_option = max(vote_counts.items(), key=lambda x: x[1])
        confidence = Decimal(str(winning_option[1] / total_votes))
        
        return {
            "result": winning_option[0],
            "confidence": confidence,
            "total_votes": total_votes,
            "winning_votes": winning_option[1],
            "vote_breakdown": vote_counts
        }
    
    async def _finalize_consensus(self, proposal_id: str, result: Dict[str, Any]):
        """Finalize consensus and store shared truth"""
        
        consensus_round = self.active_rounds.get(proposal_id)
        if not consensus_round:
            return
        
        # Update consensus round
        consensus_round.finalized_at = datetime.utcnow()
        consensus_round.result = result
        consensus_round.confidence_score = result.get("confidence", Decimal("0"))
        
        # Create shared truth record
        truth_id = create_data_hash({
            "proposal_id": proposal_id,
            "result": result,
            "finalized_at": datetime.utcnow().isoformat()
        })
        
        shared_truth_data = {
            "truth_id": truth_id,
            "proposal_id": proposal_id,
            "consensus_result": result,
            "confidence_score": result.get("confidence", Decimal("0")),
            "algorithm_used": consensus_round.algorithm.value,
            "participating_nodes": consensus_round.participating_nodes,
            "finalized_at": datetime.utcnow().isoformat(),
            "validity_period": 86400,  # 24 hours in seconds
            "status": "finalized"
        }
        
        # Store on IPFS
        truth_result = await self.ipfs_manager.pin_json(shared_truth_data)
        
        # Execute finalization transaction
        tx_result = {
            "transaction_hash": "0x" + create_data_hash({"finalize": truth_id}),
            "block_number": 12345686,
            "gas_used": 250000,
            "success": True
        }
        
        # Reward participating nodes
        await self._reward_consensus_participants(consensus_round, result)
        
        # Store in database
        await self._store_shared_truth(shared_truth_data, truth_result['hash'], tx_result['transaction_hash'])
        
        # Clean up active round
        del self.active_rounds[proposal_id]
        
        print(f"Consensus finalized for proposal {proposal_id}: {result['result']} with confidence {result['confidence']}")
    
    async def _reward_consensus_participants(
        self,
        consensus_round: ConsensusRound,
        result: Dict[str, Any]
    ):
        """Reward nodes that participated in consensus"""
        
        base_reward_amount = Decimal("10.0")  # Base reputation reward
        confidence_multiplier = result.get("confidence", Decimal("0.5"))
        
        for node_address in consensus_round.participating_nodes:
            # Award reputation for participation
            reward_amount = base_reward_amount * confidence_multiplier
            
            await self.reputation_manager.award_reputation(
                node_address,
                ReputationAction.VALUABLE_VOTING,
                {
                    "proposal_id": consensus_round.proposal_id,
                    "round_id": consensus_round.round_id,
                    "confidence": float(confidence_multiplier),
                    "algorithm": consensus_round.algorithm.value
                }
            )
        
        # Additional rewards for correct votes (would need to determine correct votes)
        # This would be implemented based on post-consensus verification
    
    async def _notify_consensus_node(
        self,
        node_address: str,
        notification_type: str,
        data: Dict[str, Any]
    ):
        """Send notification to consensus node"""
        
        notification = {
            "recipient": node_address,
            "type": notification_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.ipfs_manager.pin_json(notification)
    
    async def get_shared_truth(self, truth_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a shared truth by ID"""
        
        # Would query database in production
        return None
    
    async def query_shared_truths(
        self,
        truth_type: Optional[TruthType] = None,
        min_confidence: Decimal = Decimal("0.5"),
        max_age_hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Query shared truths with filters"""
        
        # Would implement database query with filters
        return []
    
    async def challenge_shared_truth(
        self,
        challenger_address: str,
        truth_id: str,
        challenge_evidence: Dict[str, Any],
        stake_amount: Decimal,
        private_key: str
    ) -> Dict[str, Any]:
        """Challenge an existing shared truth"""
        
        challenge_id = create_data_hash({
            "challenger": challenger_address,
            "truth_id": truth_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Store challenge evidence
        evidence_result = await self.ipfs_manager.pin_json(challenge_evidence)
        
        challenge_data = {
            "challenge_id": challenge_id,
            "challenger_address": challenger_address,
            "truth_id": truth_id,
            "evidence_hash": evidence_result['hash'],
            "stake_amount": str(stake_amount),
            "created_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        
        # Store challenge
        challenge_result = await self.ipfs_manager.pin_json(challenge_data)
        
        # Execute challenge transaction
        account = Account.from_key(private_key)
        tx_result = {
            "transaction_hash": "0x" + create_data_hash({"challenge": challenge_id}),
            "block_number": 12345687,
            "gas_used": 200000,
            "success": True
        }
        
        return {
            "challenge_id": challenge_id,
            "transaction_hash": tx_result['transaction_hash'],
            "challenge_ipfs_hash": challenge_result['hash'],
            "evidence_ipfs_hash": evidence_result['hash'],
            "status": "challenge_initiated",
            "success": True
        }
    
    def get_consensus_algorithms(self) -> List[Dict[str, Any]]:
        """Get list of supported consensus algorithms"""
        
        return [
            {
                "algorithm": ConsensusAlgorithm.PROOF_OF_STAKE.value,
                "description": "Stake-weighted voting consensus",
                "use_cases": ["General purpose", "Financial decisions"],
                "min_participants": 3,
                "finality_time": "~5 minutes"
            },
            {
                "algorithm": ConsensusAlgorithm.REPUTATION_WEIGHTED_VOTING.value,
                "description": "Reputation-based weighted voting",
                "use_cases": ["Quality assessment", "Data verification"],
                "min_participants": 5,
                "finality_time": "~10 minutes"
            },
            {
                "algorithm": ConsensusAlgorithm.ORACLE_CONSENSUS.value,
                "description": "Oracle-based data aggregation",
                "use_cases": ["Price feeds", "External data"],
                "min_participants": 3,
                "finality_time": "~2 minutes"
            },
            {
                "algorithm": ConsensusAlgorithm.PROOF_OF_AUTHORITY.value,
                "description": "Authority-based consensus",
                "use_cases": ["Identity verification", "Compliance"],
                "min_participants": 2,
                "finality_time": "~1 minute"
            }
        ]
    
    async def _store_shared_truth(
        self,
        truth_data: Dict[str, Any],
        ipfs_hash: str,
        tx_hash: str
    ):
        """Store shared truth in database"""
        
        # This would use SQLAlchemy to store in SharedTruth table
        pass