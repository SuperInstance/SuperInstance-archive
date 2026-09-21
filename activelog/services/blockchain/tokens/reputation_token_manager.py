"""
Reputation Token System for ActiveLog Marketplace
Manages reputation tokens, scoring, and incentive mechanisms
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
from ..models.blockchain_models import ReputationToken


class ReputationCategory(Enum):
    AI_TOOLS = "ai_tools"
    MARKETPLACE = "marketplace"  
    GOVERNANCE = "governance"
    COMMUNITY = "community"
    COMPUTE_PROVIDER = "compute_provider"
    DATA_QUALITY = "data_quality"
    SECURITY = "security"
    SUPPORT = "support"


class ReputationAction(Enum):
    # AI Tools
    AI_MODEL_QUALITY = "ai_model_quality"
    AI_OUTPUT_RATING = "ai_output_rating"
    AI_TOOL_CONTRIBUTION = "ai_tool_contribution"
    
    # Marketplace
    SUCCESSFUL_TRANSACTION = "successful_transaction"
    HIGH_RATING_RECEIVED = "high_rating_received"
    PROMPT_DELIVERY = "prompt_delivery"
    DISPUTE_RESOLUTION = "dispute_resolution"
    
    # Compute Provider
    UPTIME_ACHIEVEMENT = "uptime_achievement"
    PERFORMANCE_EXCELLENCE = "performance_excellence"
    COST_EFFICIENCY = "cost_efficiency"
    RESOURCE_SHARING = "resource_sharing"
    
    # Governance
    PROPOSAL_PARTICIPATION = "proposal_participation"
    VALUABLE_VOTING = "valuable_voting"
    PROPOSAL_CREATION = "proposal_creation"
    COMMUNITY_MODERATION = "community_moderation"
    
    # Data Quality
    DATA_VERIFICATION = "data_verification"
    QUALITY_CONTROL = "quality_control"
    METADATA_CONTRIBUTION = "metadata_contribution"
    
    # Community
    HELPFUL_RESPONSE = "helpful_response"
    TUTORIAL_CREATION = "tutorial_creation"
    BUG_REPORTING = "bug_reporting"
    KNOWLEDGE_SHARING = "knowledge_sharing"
    
    # Negative actions (reputation loss)
    POOR_PERFORMANCE = "poor_performance"
    VIOLATION_REPORTED = "violation_reported"
    SPAM_DETECTED = "spam_detected"
    MALICIOUS_BEHAVIOR = "malicious_behavior"


@dataclass
class ReputationEvent:
    user_address: str
    action: ReputationAction
    category: ReputationCategory
    base_amount: Decimal
    multipliers: Dict[str, Decimal]
    context_data: Dict[str, Any]
    evidence_ipfs_hash: Optional[str]
    timestamp: datetime


@dataclass
class ReputationScore:
    user_address: str
    category: ReputationCategory
    current_score: Decimal
    total_earned: Decimal
    total_burned: Decimal
    score_history: List[Dict[str, Any]]
    last_updated: datetime
    reputation_level: str


@dataclass
class ReputationMultiplier:
    name: str
    description: str
    multiplier: Decimal
    conditions: Dict[str, Any]
    expiry_date: Optional[datetime]


class ReputationTokenManager:
    """Manages reputation tokens and scoring system"""
    
    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.POLYGON):
        self.network = network
        self.config = blockchain_config.get_network_config(network)
        self.contract_config = blockchain_config.get_contract_config(
            ContractType.REPUTATION_TOKEN, network
        )
        
        self.w3 = Web3(Web3.HTTPProvider(self.config.rpc_url))
        self.ipfs_manager = IPFSManager()
        
        # Load contract ABI
        self.contract_abi = self._load_contract_abi()
        self.contract = self.w3.eth.contract(
            address=self.contract_config.address,
            abi=self.contract_abi
        )
        
        # Reputation scoring configuration
        self.base_rewards = self._init_base_rewards()
        self.multipliers = self._init_reputation_multipliers()
        self.decay_rates = self._init_decay_rates()
        self.level_thresholds = self._init_level_thresholds()
    
    def _load_contract_abi(self) -> List[Dict]:
        """Load reputation token contract ABI"""
        return [
            {
                "inputs": [
                    {"name": "user", "type": "address"},
                    {"name": "category", "type": "uint8"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "action", "type": "string"},
                    {"name": "evidenceHash", "type": "string"}
                ],
                "name": "mintReputation",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "user", "type": "address"},
                    {"name": "category", "type": "uint8"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "reason", "type": "string"}
                ],
                "name": "burnReputation",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "user", "type": "address"},
                    {"name": "category", "type": "uint8"}
                ],
                "name": "getReputationBalance",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "user", "type": "address"}
                ],
                "name": "getTotalReputation",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "category", "type": "uint8"},
                    {"name": "minAmount", "type": "uint256"},
                    {"name": "limit", "type": "uint256"}
                ],
                "name": "getTopUsers",
                "outputs": [
                    {"name": "users", "type": "address[]"},
                    {"name": "scores", "type": "uint256[]"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "fromCategory", "type": "uint8"},
                    {"name": "toCategory", "type": "uint8"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "exchangeRate", "type": "uint256"}
                ],
                "name": "exchangeReputation",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]
    
    def _init_base_rewards(self) -> Dict[ReputationAction, Decimal]:
        """Initialize base reward amounts for different actions"""
        return {
            # AI Tools (0.1 - 10 tokens)
            ReputationAction.AI_MODEL_QUALITY: Decimal("5.0"),
            ReputationAction.AI_OUTPUT_RATING: Decimal("0.5"),
            ReputationAction.AI_TOOL_CONTRIBUTION: Decimal("10.0"),
            
            # Marketplace (0.1 - 5 tokens)
            ReputationAction.SUCCESSFUL_TRANSACTION: Decimal("1.0"),
            ReputationAction.HIGH_RATING_RECEIVED: Decimal("2.0"),
            ReputationAction.PROMPT_DELIVERY: Decimal("1.5"),
            ReputationAction.DISPUTE_RESOLUTION: Decimal("5.0"),
            
            # Compute Provider (1 - 20 tokens)
            ReputationAction.UPTIME_ACHIEVEMENT: Decimal("10.0"),
            ReputationAction.PERFORMANCE_EXCELLENCE: Decimal("15.0"),
            ReputationAction.COST_EFFICIENCY: Decimal("8.0"),
            ReputationAction.RESOURCE_SHARING: Decimal("12.0"),
            
            # Governance (1 - 25 tokens)
            ReputationAction.PROPOSAL_PARTICIPATION: Decimal("3.0"),
            ReputationAction.VALUABLE_VOTING: Decimal("1.0"),
            ReputationAction.PROPOSAL_CREATION: Decimal("25.0"),
            ReputationAction.COMMUNITY_MODERATION: Decimal("8.0"),
            
            # Data Quality (0.5 - 8 tokens)
            ReputationAction.DATA_VERIFICATION: Decimal("3.0"),
            ReputationAction.QUALITY_CONTROL: Decimal("5.0"),
            ReputationAction.METADATA_CONTRIBUTION: Decimal("2.0"),
            
            # Community (0.2 - 15 tokens)
            ReputationAction.HELPFUL_RESPONSE: Decimal("1.0"),
            ReputationAction.TUTORIAL_CREATION: Decimal("15.0"),
            ReputationAction.BUG_REPORTING: Decimal("5.0"),
            ReputationAction.KNOWLEDGE_SHARING: Decimal("3.0"),
            
            # Negative actions (reputation loss)
            ReputationAction.POOR_PERFORMANCE: Decimal("-5.0"),
            ReputationAction.VIOLATION_REPORTED: Decimal("-10.0"),
            ReputationAction.SPAM_DETECTED: Decimal("-3.0"),
            ReputationAction.MALICIOUS_BEHAVIOR: Decimal("-50.0"),
        }
    
    def _init_reputation_multipliers(self) -> List[ReputationMultiplier]:
        """Initialize reputation multipliers"""
        return [
            ReputationMultiplier(
                name="Early Adopter",
                description="2x multiplier for actions in first 90 days",
                multiplier=Decimal("2.0"),
                conditions={"account_age_days": {"max": 90}},
                expiry_date=None
            ),
            ReputationMultiplier(
                name="Consistency Bonus",
                description="1.5x multiplier for daily activity streak",
                multiplier=Decimal("1.5"),
                conditions={"streak_days": {"min": 7}},
                expiry_date=None
            ),
            ReputationMultiplier(
                name="Quality Expert",
                description="1.3x multiplier for users with >4.5 average rating",
                multiplier=Decimal("1.3"),
                conditions={"average_rating": {"min": 4.5}},
                expiry_date=None
            ),
            ReputationMultiplier(
                name="High Volume",
                description="1.2x multiplier for >100 completed transactions",
                multiplier=Decimal("1.2"),
                conditions={"transaction_count": {"min": 100}},
                expiry_date=None
            ),
            ReputationMultiplier(
                name="Community Leader",
                description="1.4x multiplier for active community moderators",
                multiplier=Decimal("1.4"),
                conditions={"role": "moderator"},
                expiry_date=None
            ),
            ReputationMultiplier(
                name="Beta Tester",
                description="1.8x multiplier for beta testing participation",
                multiplier=Decimal("1.8"),
                conditions={"beta_tester": True},
                expiry_date=datetime(2024, 12, 31)
            )
        ]
    
    def _init_decay_rates(self) -> Dict[ReputationCategory, Decimal]:
        """Initialize reputation decay rates (daily percentage decay)"""
        return {
            ReputationCategory.AI_TOOLS: Decimal("0.001"),      # 0.1% daily
            ReputationCategory.MARKETPLACE: Decimal("0.0005"),   # 0.05% daily
            ReputationCategory.GOVERNANCE: Decimal("0.0002"),    # 0.02% daily
            ReputationCategory.COMMUNITY: Decimal("0.0003"),     # 0.03% daily
            ReputationCategory.COMPUTE_PROVIDER: Decimal("0.001"), # 0.1% daily
            ReputationCategory.DATA_QUALITY: Decimal("0.0004"),  # 0.04% daily
            ReputationCategory.SECURITY: Decimal("0.0001"),      # 0.01% daily
            ReputationCategory.SUPPORT: Decimal("0.0005"),       # 0.05% daily
        }
    
    def _init_level_thresholds(self) -> Dict[str, Decimal]:
        """Initialize reputation level thresholds"""
        return {
            "Newcomer": Decimal("0"),
            "Bronze": Decimal("100"),
            "Silver": Decimal("500"),
            "Gold": Decimal("2000"),
            "Platinum": Decimal("10000"),
            "Diamond": Decimal("50000"),
            "Legend": Decimal("200000"),
            "Mythic": Decimal("1000000")
        }
    
    async def award_reputation(
        self,
        user_address: str,
        action: ReputationAction,
        context_data: Dict[str, Any] = None,
        evidence_data: Optional[Dict[str, Any]] = None,
        private_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Award reputation tokens for a specific action"""
        
        # Determine category from action
        category = self._get_category_for_action(action)
        
        # Calculate reputation amount
        base_amount = self.base_rewards[action]
        multipliers = await self._calculate_multipliers(user_address, action, context_data or {})
        
        # Apply multipliers
        final_amount = base_amount
        for multiplier_name, multiplier_value in multipliers.items():
            final_amount *= multiplier_value
        
        # Ensure non-negative (except for penalty actions)
        if final_amount < 0 and not action.name.startswith(('POOR_', 'VIOLATION_', 'SPAM_', 'MALICIOUS_')):
            final_amount = Decimal("0")
        
        # Store evidence on IPFS if provided
        evidence_ipfs_hash = None
        if evidence_data:
            evidence_result = await self.ipfs_manager.pin_json({
                "action": action.value,
                "user_address": user_address,
                "evidence": evidence_data,
                "timestamp": datetime.utcnow().isoformat(),
                "context": context_data or {}
            })
            evidence_ipfs_hash = evidence_result['hash']
        
        # Create reputation event
        event = ReputationEvent(
            user_address=user_address,
            action=action,
            category=category,
            base_amount=base_amount,
            multipliers=multipliers,
            context_data=context_data or {},
            evidence_ipfs_hash=evidence_ipfs_hash,
            timestamp=datetime.utcnow()
        )
        
        if private_key:
            # Execute on-chain transaction
            if final_amount >= 0:
                return await self._mint_reputation(event, final_amount, private_key)
            else:
                return await self._burn_reputation(event, abs(final_amount), private_key)
        else:
            # Return transaction data for external signing
            return self._prepare_reputation_transaction(event, final_amount)
    
    async def _mint_reputation(
        self,
        event: ReputationEvent,
        amount: Decimal,
        private_key: str
    ) -> Dict[str, Any]:
        """Mint reputation tokens on-chain"""
        
        account = Account.from_key(private_key)
        
        # Convert amount to wei (18 decimals)
        amount_wei = int(amount * (10 ** 18))
        
        tx_data = self.contract.functions.mintReputation(
            event.user_address,
            list(ReputationCategory).index(event.category),
            amount_wei,
            event.action.value,
            event.evidence_ipfs_hash or ""
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 200000,
            'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Store in database
        await self._store_reputation_event(event, amount, receipt.transactionHash.hex())
        
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "user_address": event.user_address,
            "action": event.action.value,
            "category": event.category.value,
            "amount_awarded": amount,
            "evidence_ipfs_hash": event.evidence_ipfs_hash,
            "multipliers_applied": event.multipliers,
            "success": receipt.status == 1
        }
    
    async def _burn_reputation(
        self,
        event: ReputationEvent,
        amount: Decimal,
        private_key: str
    ) -> Dict[str, Any]:
        """Burn reputation tokens (for penalties)"""
        
        account = Account.from_key(private_key)
        
        # Convert amount to wei
        amount_wei = int(amount * (10 ** 18))
        
        tx_data = self.contract.functions.burnReputation(
            event.user_address,
            list(ReputationCategory).index(event.category),
            amount_wei,
            event.action.value
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 150000,
            'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Store in database
        await self._store_reputation_event(event, -amount, receipt.transactionHash.hex())
        
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "user_address": event.user_address,
            "action": event.action.value,
            "category": event.category.value,
            "amount_burned": amount,
            "reason": event.action.value,
            "success": receipt.status == 1
        }
    
    async def get_user_reputation_score(self, user_address: str) -> Dict[str, ReputationScore]:
        """Get comprehensive reputation scores for a user"""
        
        reputation_scores = {}
        
        for category in ReputationCategory:
            try:
                # Get on-chain balance
                balance_wei = self.contract.functions.getReputationBalance(
                    user_address,
                    list(ReputationCategory).index(category)
                ).call()
                
                balance = Decimal(str(balance_wei)) / (10 ** 18)
                
                # Apply decay based on last activity
                decayed_balance = await self._apply_reputation_decay(user_address, category, balance)
                
                # Get reputation level
                level = self._get_reputation_level(decayed_balance)
                
                # Get history from database (would be implemented)
                history = await self._get_reputation_history(user_address, category)
                
                reputation_scores[category.value] = ReputationScore(
                    user_address=user_address,
                    category=category,
                    current_score=decayed_balance,
                    total_earned=balance,  # Before decay
                    total_burned=Decimal("0"),  # Would be tracked separately
                    score_history=history,
                    last_updated=datetime.utcnow(),
                    reputation_level=level
                )
                
            except Exception as e:
                print(f"Error getting reputation for {category.value}: {e}")
                continue
        
        return reputation_scores
    
    async def get_leaderboard(
        self,
        category: ReputationCategory,
        limit: int = 50,
        min_score: Decimal = Decimal("10")
    ) -> List[Dict[str, Any]]:
        """Get reputation leaderboard for a category"""
        
        try:
            min_score_wei = int(min_score * (10 ** 18))
            
            result = self.contract.functions.getTopUsers(
                list(ReputationCategory).index(category),
                min_score_wei,
                limit
            ).call()
            
            users = result[0]
            scores = result[1]
            
            leaderboard = []
            for i, (user, score_wei) in enumerate(zip(users, scores)):
                score = Decimal(str(score_wei)) / (10 ** 18)
                level = self._get_reputation_level(score)
                
                leaderboard.append({
                    "rank": i + 1,
                    "user_address": user,
                    "score": score,
                    "level": level,
                    "category": category.value
                })
            
            return leaderboard
            
        except Exception as e:
            print(f"Error getting leaderboard: {e}")
            return []
    
    async def exchange_reputation(
        self,
        user_address: str,
        from_category: ReputationCategory,
        to_category: ReputationCategory,
        amount: Decimal,
        private_key: str
    ) -> Dict[str, Any]:
        """Exchange reputation between categories"""
        
        # Calculate exchange rate (simplified)
        exchange_rate = await self._calculate_exchange_rate(from_category, to_category)
        
        account = Account.from_key(private_key)
        
        amount_wei = int(amount * (10 ** 18))
        rate_wei = int(exchange_rate * (10 ** 18))
        
        tx_data = self.contract.functions.exchangeReputation(
            list(ReputationCategory).index(from_category),
            list(ReputationCategory).index(to_category),
            amount_wei,
            rate_wei
        ).build_transaction({
            'from': account.address,
            'nonce': self.w3.eth.get_transaction_count(account.address),
            'gas': 250000,
            'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx_data, private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        
        received_amount = amount * exchange_rate
        
        return {
            "transaction_hash": receipt.transactionHash.hex(),
            "from_category": from_category.value,
            "to_category": to_category.value,
            "amount_exchanged": amount,
            "amount_received": received_amount,
            "exchange_rate": exchange_rate,
            "success": receipt.status == 1
        }
    
    def _get_category_for_action(self, action: ReputationAction) -> ReputationCategory:
        """Determine reputation category for an action"""
        
        action_to_category = {
            ReputationAction.AI_MODEL_QUALITY: ReputationCategory.AI_TOOLS,
            ReputationAction.AI_OUTPUT_RATING: ReputationCategory.AI_TOOLS,
            ReputationAction.AI_TOOL_CONTRIBUTION: ReputationCategory.AI_TOOLS,
            
            ReputationAction.SUCCESSFUL_TRANSACTION: ReputationCategory.MARKETPLACE,
            ReputationAction.HIGH_RATING_RECEIVED: ReputationCategory.MARKETPLACE,
            ReputationAction.PROMPT_DELIVERY: ReputationCategory.MARKETPLACE,
            ReputationAction.DISPUTE_RESOLUTION: ReputationCategory.MARKETPLACE,
            
            ReputationAction.UPTIME_ACHIEVEMENT: ReputationCategory.COMPUTE_PROVIDER,
            ReputationAction.PERFORMANCE_EXCELLENCE: ReputationCategory.COMPUTE_PROVIDER,
            ReputationAction.COST_EFFICIENCY: ReputationCategory.COMPUTE_PROVIDER,
            ReputationAction.RESOURCE_SHARING: ReputationCategory.COMPUTE_PROVIDER,
            
            ReputationAction.PROPOSAL_PARTICIPATION: ReputationCategory.GOVERNANCE,
            ReputationAction.VALUABLE_VOTING: ReputationCategory.GOVERNANCE,
            ReputationAction.PROPOSAL_CREATION: ReputationCategory.GOVERNANCE,
            ReputationAction.COMMUNITY_MODERATION: ReputationCategory.GOVERNANCE,
            
            ReputationAction.DATA_VERIFICATION: ReputationCategory.DATA_QUALITY,
            ReputationAction.QUALITY_CONTROL: ReputationCategory.DATA_QUALITY,
            ReputationAction.METADATA_CONTRIBUTION: ReputationCategory.DATA_QUALITY,
            
            ReputationAction.HELPFUL_RESPONSE: ReputationCategory.COMMUNITY,
            ReputationAction.TUTORIAL_CREATION: ReputationCategory.COMMUNITY,
            ReputationAction.BUG_REPORTING: ReputationCategory.COMMUNITY,
            ReputationAction.KNOWLEDGE_SHARING: ReputationCategory.COMMUNITY,
        }
        
        return action_to_category.get(action, ReputationCategory.COMMUNITY)
    
    async def _calculate_multipliers(
        self,
        user_address: str,
        action: ReputationAction,
        context_data: Dict[str, Any]
    ) -> Dict[str, Decimal]:
        """Calculate applicable multipliers for user action"""
        
        applicable_multipliers = {}
        
        # Get user stats (would be from database in production)
        user_stats = await self._get_user_stats(user_address)
        
        for multiplier in self.multipliers:
            # Check if multiplier has expired
            if multiplier.expiry_date and multiplier.expiry_date < datetime.utcnow():
                continue
            
            # Check conditions
            if self._check_multiplier_conditions(multiplier, user_stats, context_data):
                applicable_multipliers[multiplier.name] = multiplier.multiplier
        
        return applicable_multipliers
    
    def _check_multiplier_conditions(
        self,
        multiplier: ReputationMultiplier,
        user_stats: Dict[str, Any],
        context_data: Dict[str, Any]
    ) -> bool:
        """Check if multiplier conditions are met"""
        
        for condition_key, condition_value in multiplier.conditions.items():
            if condition_key in user_stats:
                user_value = user_stats[condition_key]
                
                if isinstance(condition_value, dict):
                    if "min" in condition_value and user_value < condition_value["min"]:
                        return False
                    if "max" in condition_value and user_value > condition_value["max"]:
                        return False
                else:
                    if user_value != condition_value:
                        return False
            else:
                # Condition not met if required stat is missing
                return False
        
        return True
    
    async def _get_user_stats(self, user_address: str) -> Dict[str, Any]:
        """Get user statistics for multiplier calculation"""
        
        # In production, this would query the database
        # For now, return mock data
        return {
            "account_age_days": 30,
            "streak_days": 5,
            "average_rating": 4.2,
            "transaction_count": 25,
            "role": "user",
            "beta_tester": True
        }
    
    async def _apply_reputation_decay(
        self,
        user_address: str,
        category: ReputationCategory,
        current_balance: Decimal
    ) -> Decimal:
        """Apply time-based reputation decay"""
        
        decay_rate = self.decay_rates[category]
        
        # Get last activity time (would be from database)
        last_activity = await self._get_last_activity(user_address, category)
        
        if last_activity:
            days_inactive = (datetime.utcnow() - last_activity).days
            decay_factor = (1 - decay_rate) ** days_inactive
            return current_balance * decay_factor
        
        return current_balance
    
    def _get_reputation_level(self, score: Decimal) -> str:
        """Get reputation level based on score"""
        
        for level, threshold in reversed(list(self.level_thresholds.items())):
            if score >= threshold:
                return level
        
        return "Newcomer"
    
    async def _calculate_exchange_rate(
        self,
        from_category: ReputationCategory,
        to_category: ReputationCategory
    ) -> Decimal:
        """Calculate exchange rate between reputation categories"""
        
        # Simplified exchange rate calculation
        # In production, this would consider supply/demand, category importance, etc.
        
        base_rates = {
            ReputationCategory.GOVERNANCE: Decimal("1.2"),
            ReputationCategory.SECURITY: Decimal("1.1"),
            ReputationCategory.DATA_QUALITY: Decimal("1.05"),
            ReputationCategory.AI_TOOLS: Decimal("1.0"),
            ReputationCategory.MARKETPLACE: Decimal("0.95"),
            ReputationCategory.COMPUTE_PROVIDER: Decimal("0.9"),
            ReputationCategory.COMMUNITY: Decimal("0.85"),
            ReputationCategory.SUPPORT: Decimal("0.8")
        }
        
        from_rate = base_rates.get(from_category, Decimal("1.0"))
        to_rate = base_rates.get(to_category, Decimal("1.0"))
        
        # Exchange rate includes a small fee
        exchange_rate = (to_rate / from_rate) * Decimal("0.95")  # 5% exchange fee
        
        return exchange_rate
    
    def _prepare_reputation_transaction(
        self,
        event: ReputationEvent,
        amount: Decimal
    ) -> Dict[str, Any]:
        """Prepare reputation transaction for external signing"""
        
        amount_wei = int(abs(amount) * (10 ** 18))
        
        if amount >= 0:
            # Mint transaction
            function_data = self.contract.functions.mintReputation(
                event.user_address,
                list(ReputationCategory).index(event.category),
                amount_wei,
                event.action.value,
                event.evidence_ipfs_hash or ""
            ).build_transaction({
                'gas': 200000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })['data']
        else:
            # Burn transaction  
            function_data = self.contract.functions.burnReputation(
                event.user_address,
                list(ReputationCategory).index(event.category),
                amount_wei,
                event.action.value
            ).build_transaction({
                'gas': 150000,
                'gasPrice': self.w3.to_wei(self.config.gas_price_gwei, 'gwei')
            })['data']
        
        return {
            "contract_address": self.contract_config.address,
            "function_data": function_data,
            "user_address": event.user_address,
            "action": event.action.value,
            "category": event.category.value,
            "amount": amount,
            "multipliers": event.multipliers,
            "evidence_ipfs_hash": event.evidence_ipfs_hash
        }
    
    async def _store_reputation_event(
        self,
        event: ReputationEvent,
        final_amount: Decimal,
        tx_hash: str
    ):
        """Store reputation event in database"""
        
        # This would use SQLAlchemy to store in ReputationToken table
        # Implementation depends on database setup
        pass
    
    async def _get_reputation_history(
        self,
        user_address: str,
        category: ReputationCategory
    ) -> List[Dict[str, Any]]:
        """Get reputation history for user and category"""
        
        # This would query the database for historical reputation events
        # For now, return empty list
        return []
    
    async def _get_last_activity(
        self,
        user_address: str,
        category: ReputationCategory
    ) -> Optional[datetime]:
        """Get last activity timestamp for user in category"""
        
        # This would query the database for last reputation-earning activity
        # For now, return current time to avoid decay
        return datetime.utcnow()
    
    async def create_reputation_badge_nft(
        self,
        user_address: str,
        achievement: str,
        evidence_data: Dict[str, Any],
        private_key: str
    ) -> Dict[str, Any]:
        """Create special NFT badge for reputation milestones"""
        
        badge_metadata = {
            "achievement": achievement,
            "user_address": user_address,
            "earned_at": datetime.utcnow().isoformat(),
            "evidence": evidence_data,
            "badge_type": "reputation_milestone"
        }
        
        # Store badge metadata on IPFS
        badge_result = await self.ipfs_manager.pin_json(badge_metadata)
        
        # This would mint a special NFT badge
        # Implementation would depend on badge NFT contract
        
        return {
            "badge_id": create_data_hash(badge_metadata),
            "metadata_ipfs_hash": badge_result['hash'],
            "achievement": achievement,
            "user_address": user_address
        }