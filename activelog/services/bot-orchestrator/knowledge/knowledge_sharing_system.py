"""
Advanced Knowledge Sharing and Context Passing System
Enables bots to share knowledge, context, and learned experiences intelligently
"""

import asyncio
import json
import logging
import uuid
import time
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
import sqlite3
import pickle
import networkx as nx
from collections import defaultdict

logger = logging.getLogger(__name__)

class KnowledgeType(Enum):
    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    EXPERIENTIAL = "experiential"
    CONTEXTUAL = "contextual"
    PATTERN = "pattern"
    SOLUTION = "solution"
    ERROR_RECOVERY = "error_recovery"
    BEST_PRACTICE = "best_practice"
    DOMAIN_EXPERTISE = "domain_expertise"
    COLLABORATIVE = "collaborative"

class ContextScope(Enum):
    TASK_SPECIFIC = "task_specific"
    SESSION_SPECIFIC = "session_specific"
    DOMAIN_SPECIFIC = "domain_specific"
    GLOBAL = "global"
    TEMPORAL = "temporal"
    COLLABORATIVE = "collaborative"

class KnowledgeSource(Enum):
    BOT_EXECUTION = "bot_execution"
    COLLABORATION = "collaboration"
    ERROR_ANALYSIS = "error_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    USER_FEEDBACK = "user_feedback"
    EXTERNAL_SOURCE = "external_source"
    INFERENCE = "inference"

class AccessLevel(Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"
    COLLABORATIVE_ONLY = "collaborative_only"

@dataclass
class KnowledgeItem:
    """Individual piece of knowledge in the system"""
    id: str
    knowledge_type: KnowledgeType
    content: Dict[str, Any]
    source: KnowledgeSource
    creator_bot_id: str
    
    # Metadata
    created_at: datetime
    updated_at: datetime
    access_level: AccessLevel = AccessLevel.PUBLIC
    
    # Context and relevance
    domain_tags: List[str] = field(default_factory=list)
    context_tags: List[str] = field(default_factory=list)
    relevance_score: float = 1.0
    confidence: float = 1.0
    
    # Usage and validation
    usage_count: int = 0
    success_rate: float = 1.0
    validation_votes: Dict[str, float] = field(default_factory=dict)  # bot_id -> vote
    
    # Relationships
    related_items: Set[str] = field(default_factory=set)
    derived_from: Optional[str] = None
    
    # Lifecycle
    expiry_date: Optional[datetime] = None
    is_deprecated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'knowledge_type': self.knowledge_type.value,
            'content': self.content,
            'source': self.source.value,
            'creator_bot_id': self.creator_bot_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'access_level': self.access_level.value,
            'domain_tags': self.domain_tags,
            'context_tags': self.context_tags,
            'relevance_score': self.relevance_score,
            'confidence': self.confidence,
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'validation_votes': self.validation_votes,
            'related_items': list(self.related_items),
            'derived_from': self.derived_from,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_deprecated': self.is_deprecated
        }

@dataclass
class ContextFrame:
    """Context frame for sharing contextual information"""
    id: str
    session_id: Optional[str]
    task_id: Optional[str]
    scope: ContextScope
    
    # Context data
    context_data: Dict[str, Any]
    shared_variables: Dict[str, Any] = field(default_factory=dict)
    execution_state: Dict[str, Any] = field(default_factory=dict)
    
    # Temporal context
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Access control
    authorized_bots: Set[str] = field(default_factory=set)
    access_level: AccessLevel = AccessLevel.COLLABORATIVE_ONLY
    
    # Relevance and lifecycle
    relevance_decay_rate: float = 0.1  # Per hour
    max_lifetime_hours: float = 24.0
    
    def is_accessible_by(self, bot_id: str) -> bool:
        """Check if bot has access to this context"""
        if self.access_level == AccessLevel.PUBLIC:
            return True
        elif self.access_level == AccessLevel.COLLABORATIVE_ONLY:
            return bot_id in self.authorized_bots
        elif self.access_level == AccessLevel.PRIVATE:
            return False  # Would need more specific checks
        else:
            return bot_id in self.authorized_bots
    
    def get_current_relevance(self) -> float:
        """Calculate current relevance based on age and decay"""
        age_hours = (datetime.now() - self.last_updated).total_seconds() / 3600
        relevance = max(0.0, 1.0 - (age_hours * self.relevance_decay_rate))
        return relevance
    
    def is_expired(self) -> bool:
        """Check if context frame has expired"""
        age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
        return age_hours > self.max_lifetime_hours

@dataclass
class LearningPattern:
    """Pattern learned from bot interactions and outcomes"""
    id: str
    pattern_type: str
    pattern_data: Dict[str, Any]
    
    # Context
    domain: str
    applicable_contexts: List[str]
    
    # Evidence
    supporting_instances: List[Dict[str, Any]]
    success_rate: float
    confidence_interval: Tuple[float, float]
    
    # Metadata
    discovered_at: datetime
    last_validated: datetime
    discovery_bot: str
    
    # Application
    application_count: int = 0
    successful_applications: int = 0

class KnowledgeSharingSystem:
    """Advanced system for bot knowledge sharing and context management"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/data/knowledge_sharing.db"):
        self.db_path = db_path
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        self.context_frames: Dict[str, ContextFrame] = {}
        self.learned_patterns: Dict[str, LearningPattern] = {}
        
        # Knowledge graph for relationships
        self.knowledge_graph = nx.DiGraph()
        
        # Caching and indexing
        self.domain_index: Dict[str, Set[str]] = defaultdict(set)  # domain -> knowledge_ids
        self.bot_knowledge_index: Dict[str, Set[str]] = defaultdict(set)  # bot_id -> knowledge_ids
        self.temporal_index: Dict[str, List[str]] = defaultdict(list)  # date_key -> knowledge_ids
        
        # Context tracking
        self.active_contexts: Dict[str, Set[str]] = defaultdict(set)  # session_id -> context_ids
        
        # Learning and adaptation
        self.learning_rules: List[Dict[str, Any]] = []
        self.adaptation_strategies: Dict[str, Callable] = {}
        
        # Performance metrics
        self.sharing_stats = {
            "total_items_shared": 0,
            "successful_retrievals": 0,
            "context_hits": 0,
            "pattern_applications": 0,
            "collaborative_contributions": 0
        }
        
        self._initialize_database()
        self._setup_learning_rules()
    
    def _initialize_database(self):
        """Initialize SQLite database for persistent storage"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Knowledge items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_items (
                    id TEXT PRIMARY KEY,
                    knowledge_type TEXT,
                    content TEXT,
                    source TEXT,
                    creator_bot_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    access_level TEXT,
                    domain_tags TEXT,
                    context_tags TEXT,
                    relevance_score REAL,
                    confidence REAL,
                    usage_count INTEGER,
                    success_rate REAL,
                    validation_votes TEXT,
                    related_items TEXT,
                    derived_from TEXT,
                    expiry_date TEXT,
                    is_deprecated BOOLEAN
                )
            ''')
            
            # Context frames table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS context_frames (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    task_id TEXT,
                    scope TEXT,
                    context_data TEXT,
                    shared_variables TEXT,
                    execution_state TEXT,
                    created_at TEXT,
                    last_updated TEXT,
                    authorized_bots TEXT,
                    access_level TEXT,
                    relevance_decay_rate REAL,
                    max_lifetime_hours REAL
                )
            ''')
            
            # Learning patterns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS learning_patterns (
                    id TEXT PRIMARY KEY,
                    pattern_type TEXT,
                    pattern_data TEXT,
                    domain TEXT,
                    applicable_contexts TEXT,
                    supporting_instances TEXT,
                    success_rate REAL,
                    confidence_interval TEXT,
                    discovered_at TEXT,
                    last_validated TEXT,
                    discovery_bot TEXT,
                    application_count INTEGER,
                    successful_applications INTEGER
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_domain ON knowledge_items(domain_tags)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_knowledge_creator ON knowledge_items(creator_bot_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_context_session ON context_frames(session_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_domain ON learning_patterns(domain)')
            
            conn.commit()
            conn.close()
            
            # Load existing data
            self._load_from_database()
            
            logger.info("Knowledge sharing database initialized")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    def _setup_learning_rules(self):
        """Setup learning and pattern recognition rules"""
        
        self.learning_rules = [
            {
                "name": "success_pattern_recognition",
                "condition": lambda data: data.get("success_rate", 0) > 0.8,
                "action": self._extract_success_pattern
            },
            {
                "name": "error_pattern_recognition", 
                "condition": lambda data: data.get("error_count", 0) > 2,
                "action": self._extract_error_pattern
            },
            {
                "name": "collaboration_pattern_recognition",
                "condition": lambda data: data.get("collaboration_score", 0) > 0.7,
                "action": self._extract_collaboration_pattern
            },
            {
                "name": "context_optimization",
                "condition": lambda data: data.get("context_usage", 0) > 5,
                "action": self._optimize_context_sharing
            }
        ]
    
    async def share_knowledge(
        self,
        creator_bot_id: str,
        knowledge_type: KnowledgeType,
        content: Dict[str, Any],
        domain_tags: List[str] = None,
        context_tags: List[str] = None,
        access_level: AccessLevel = AccessLevel.PUBLIC,
        confidence: float = 1.0
    ) -> str:
        """Share a piece of knowledge in the system"""
        
        knowledge_id = str(uuid.uuid4())
        
        knowledge_item = KnowledgeItem(
            id=knowledge_id,
            knowledge_type=knowledge_type,
            content=content,
            source=KnowledgeSource.BOT_EXECUTION,
            creator_bot_id=creator_bot_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            access_level=access_level,
            domain_tags=domain_tags or [],
            context_tags=context_tags or [],
            confidence=confidence
        )
        
        # Store in memory
        self.knowledge_items[knowledge_id] = knowledge_item
        
        # Update indexes
        for tag in knowledge_item.domain_tags:
            self.domain_index[tag].add(knowledge_id)
        
        self.bot_knowledge_index[creator_bot_id].add(knowledge_id)
        
        date_key = knowledge_item.created_at.strftime("%Y-%m-%d")
        self.temporal_index[date_key].append(knowledge_id)
        
        # Add to knowledge graph
        self.knowledge_graph.add_node(knowledge_id, **asdict(knowledge_item))
        
        # Persist to database
        await self._persist_knowledge_item(knowledge_item)
        
        # Update stats
        self.sharing_stats["total_items_shared"] += 1
        
        logger.info(f"Knowledge shared by {creator_bot_id}: {knowledge_type.value} (ID: {knowledge_id})")
        
        return knowledge_id
    
    async def retrieve_knowledge(
        self,
        requester_bot_id: str,
        query_context: Dict[str, Any],
        knowledge_types: List[KnowledgeType] = None,
        domain_filter: List[str] = None,
        max_results: int = 10
    ) -> List[KnowledgeItem]:
        """Retrieve relevant knowledge based on context and filters"""
        
        relevant_items = []
        
        # Search through knowledge items
        for item in self.knowledge_items.values():
            
            # Access control check
            if not self._check_access(item, requester_bot_id):
                continue
            
            # Type filter
            if knowledge_types and item.knowledge_type not in knowledge_types:
                continue
            
            # Domain filter
            if domain_filter and not any(tag in item.domain_tags for tag in domain_filter):
                continue
            
            # Skip deprecated items
            if item.is_deprecated:
                continue
            
            # Skip expired items
            if item.expiry_date and datetime.now() > item.expiry_date:
                continue
            
            # Calculate relevance score
            relevance = self._calculate_relevance(item, query_context)
            
            if relevance > 0.1:  # Minimum relevance threshold
                item.relevance_score = relevance
                relevant_items.append(item)
        
        # Sort by relevance and confidence
        relevant_items.sort(key=lambda x: (x.relevance_score * x.confidence), reverse=True)
        
        # Update usage statistics
        for item in relevant_items[:max_results]:
            item.usage_count += 1
        
        self.sharing_stats["successful_retrievals"] += len(relevant_items[:max_results])
        
        logger.info(f"Retrieved {len(relevant_items[:max_results])} knowledge items for {requester_bot_id}")
        
        return relevant_items[:max_results]
    
    async def create_context_frame(
        self,
        session_id: Optional[str],
        task_id: Optional[str],
        scope: ContextScope,
        context_data: Dict[str, Any],
        authorized_bots: Set[str] = None,
        access_level: AccessLevel = AccessLevel.COLLABORATIVE_ONLY
    ) -> str:
        """Create a new context frame for sharing"""
        
        context_id = str(uuid.uuid4())
        
        context_frame = ContextFrame(
            id=context_id,
            session_id=session_id,
            task_id=task_id,
            scope=scope,
            context_data=context_data,
            authorized_bots=authorized_bots or set(),
            access_level=access_level
        )
        
        self.context_frames[context_id] = context_frame
        
        # Track active contexts
        if session_id:
            self.active_contexts[session_id].add(context_id)
        
        # Persist to database
        await self._persist_context_frame(context_frame)
        
        logger.info(f"Context frame created: {context_id} for session {session_id}")
        
        return context_id
    
    async def update_context_frame(
        self,
        context_id: str,
        bot_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing context frame"""
        
        context_frame = self.context_frames.get(context_id)
        if not context_frame:
            return False
        
        # Access control check
        if not context_frame.is_accessible_by(bot_id):
            logger.warning(f"Bot {bot_id} denied access to context {context_id}")
            return False
        
        # Apply updates
        if "shared_variables" in updates:
            context_frame.shared_variables.update(updates["shared_variables"])
        
        if "execution_state" in updates:
            context_frame.execution_state.update(updates["execution_state"])
        
        if "context_data" in updates:
            context_frame.context_data.update(updates["context_data"])
        
        context_frame.last_updated = datetime.now()
        
        # Persist changes
        await self._persist_context_frame(context_frame)
        
        logger.info(f"Context frame {context_id} updated by {bot_id}")
        
        return True
    
    async def get_context_for_bot(
        self,
        bot_id: str,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        scope_filter: List[ContextScope] = None
    ) -> List[ContextFrame]:
        """Get relevant context frames for a bot"""
        
        relevant_contexts = []
        
        for context in self.context_frames.values():
            
            # Access control
            if not context.is_accessible_by(bot_id):
                continue
            
            # Expiry check
            if context.is_expired():
                continue
            
            # Scope filter
            if scope_filter and context.scope not in scope_filter:
                continue
            
            # Session/task filtering
            if session_id and context.session_id != session_id:
                continue
            
            if task_id and context.task_id != task_id:
                continue
            
            relevant_contexts.append(context)
        
        # Sort by relevance
        relevant_contexts.sort(key=lambda x: x.get_current_relevance(), reverse=True)
        
        self.sharing_stats["context_hits"] += len(relevant_contexts)
        
        return relevant_contexts
    
    async def learn_from_interaction(
        self,
        bot_id: str,
        interaction_data: Dict[str, Any]
    ):
        """Learn patterns from bot interactions"""
        
        # Apply learning rules
        for rule in self.learning_rules:
            if rule["condition"](interaction_data):
                try:
                    await rule["action"](bot_id, interaction_data)
                except Exception as e:
                    logger.error(f"Learning rule '{rule['name']}' failed: {e}")
        
        # Extract general patterns
        await self._extract_general_patterns(bot_id, interaction_data)
    
    async def validate_knowledge(
        self,
        knowledge_id: str,
        validator_bot_id: str,
        validation_score: float,
        feedback: Optional[str] = None
    ):
        """Validate a piece of knowledge"""
        
        item = self.knowledge_items.get(knowledge_id)
        if not item:
            return
        
        # Add validation vote
        item.validation_votes[validator_bot_id] = validation_score
        
        # Recalculate confidence based on validations
        if item.validation_votes:
            avg_validation = sum(item.validation_votes.values()) / len(item.validation_votes)
            item.confidence = (item.confidence + avg_validation) / 2
        
        # Create validation knowledge item if feedback provided
        if feedback:
            await self.share_knowledge(
                creator_bot_id=validator_bot_id,
                knowledge_type=KnowledgeType.EXPERIENTIAL,
                content={
                    "validated_item": knowledge_id,
                    "validation_score": validation_score,
                    "feedback": feedback
                },
                domain_tags=item.domain_tags,
                access_level=AccessLevel.PUBLIC,
                confidence=0.8
            )
        
        item.updated_at = datetime.now()
        await self._persist_knowledge_item(item)
        
        logger.info(f"Knowledge {knowledge_id} validated by {validator_bot_id}: {validation_score}")
    
    async def find_related_knowledge(
        self,
        base_knowledge_id: str,
        relation_depth: int = 2
    ) -> List[Tuple[str, str, float]]:
        """Find knowledge items related to a base item"""
        
        related = []
        
        if base_knowledge_id not in self.knowledge_graph:
            return related
        
        # Use graph traversal to find related items
        try:
            # Get direct connections
            if relation_depth >= 1:
                direct_neighbors = list(self.knowledge_graph.neighbors(base_knowledge_id))
                for neighbor_id in direct_neighbors:
                    related.append((neighbor_id, "direct", 1.0))
            
            # Get second-degree connections
            if relation_depth >= 2:
                for neighbor_id in direct_neighbors:
                    second_neighbors = list(self.knowledge_graph.neighbors(neighbor_id))
                    for second_neighbor_id in second_neighbors:
                        if second_neighbor_id != base_knowledge_id:
                            related.append((second_neighbor_id, "indirect", 0.5))
            
        except Exception as e:
            logger.error(f"Error finding related knowledge: {e}")
        
        return related
    
    async def create_knowledge_summary(
        self,
        domain: str,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Create a summary of knowledge in a domain"""
        
        cutoff_date = datetime.now() - timedelta(days=time_period_days)
        
        domain_knowledge = []
        for item in self.knowledge_items.values():
            if domain in item.domain_tags and item.created_at >= cutoff_date:
                domain_knowledge.append(item)
        
        if not domain_knowledge:
            return {"domain": domain, "items": 0, "summary": "No recent knowledge found"}
        
        # Statistics
        knowledge_types = defaultdict(int)
        creators = defaultdict(int)
        avg_confidence = 0
        total_usage = 0
        
        for item in domain_knowledge:
            knowledge_types[item.knowledge_type.value] += 1
            creators[item.creator_bot_id] += 1
            avg_confidence += item.confidence
            total_usage += item.usage_count
        
        avg_confidence /= len(domain_knowledge)
        
        # Top contributors
        top_contributors = sorted(creators.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Recent patterns
        recent_patterns = [
            pattern for pattern in self.learned_patterns.values()
            if pattern.domain == domain and 
            (datetime.now() - pattern.discovered_at).days <= time_period_days
        ]
        
        return {
            "domain": domain,
            "time_period_days": time_period_days,
            "total_items": len(domain_knowledge),
            "knowledge_types": dict(knowledge_types),
            "avg_confidence": round(avg_confidence, 2),
            "total_usage": total_usage,
            "top_contributors": top_contributors,
            "recent_patterns": len(recent_patterns),
            "active_contexts": len([
                ctx for ctx in self.context_frames.values()
                if not ctx.is_expired() and domain in str(ctx.context_data)
            ])
        }
    
    # Private helper methods
    
    def _check_access(self, item: KnowledgeItem, bot_id: str) -> bool:
        """Check if bot has access to knowledge item"""
        
        if item.access_level == AccessLevel.PUBLIC:
            return True
        elif item.access_level == AccessLevel.PRIVATE:
            return bot_id == item.creator_bot_id
        elif item.access_level == AccessLevel.RESTRICTED:
            # Could implement more sophisticated access control
            return bot_id == item.creator_bot_id
        else:
            return True  # Default to allow
    
    def _calculate_relevance(self, item: KnowledgeItem, query_context: Dict[str, Any]) -> float:
        """Calculate relevance score for a knowledge item"""
        
        relevance = 0.0
        
        # Domain tag matching
        query_domains = query_context.get("domains", [])
        if query_domains:
            domain_overlap = len(set(item.domain_tags) & set(query_domains))
            relevance += (domain_overlap / len(query_domains)) * 0.4
        
        # Context tag matching
        query_contexts = query_context.get("contexts", [])
        if query_contexts:
            context_overlap = len(set(item.context_tags) & set(query_contexts))
            relevance += (context_overlap / len(query_contexts)) * 0.3
        
        # Temporal relevance (more recent = more relevant)
        age_days = (datetime.now() - item.created_at).days
        temporal_score = max(0, 1.0 - (age_days / 365.0))  # Decay over a year
        relevance += temporal_score * 0.2
        
        # Usage-based relevance
        usage_score = min(1.0, item.usage_count / 10.0)  # Normalize to max 10 uses
        relevance += usage_score * 0.1
        
        return min(1.0, relevance)
    
    async def _extract_success_pattern(self, bot_id: str, data: Dict[str, Any]):
        """Extract success pattern from interaction data"""
        
        pattern_id = str(uuid.uuid4())
        
        pattern = LearningPattern(
            id=pattern_id,
            pattern_type="success_pattern",
            pattern_data={
                "approach": data.get("approach", ""),
                "context": data.get("context", {}),
                "outcome_factors": data.get("outcome_factors", [])
            },
            domain=data.get("domain", "general"),
            applicable_contexts=data.get("contexts", []),
            supporting_instances=[data],
            success_rate=data.get("success_rate", 0.8),
            confidence_interval=(0.7, 0.9),  # Placeholder
            discovered_at=datetime.now(),
            last_validated=datetime.now(),
            discovery_bot=bot_id
        )
        
        self.learned_patterns[pattern_id] = pattern
        await self._persist_learning_pattern(pattern)
        
        logger.info(f"Success pattern extracted by {bot_id}: {pattern_id}")
    
    async def _extract_error_pattern(self, bot_id: str, data: Dict[str, Any]):
        """Extract error pattern from interaction data"""
        
        pattern_id = str(uuid.uuid4())
        
        pattern = LearningPattern(
            id=pattern_id,
            pattern_type="error_pattern",
            pattern_data={
                "error_conditions": data.get("error_conditions", []),
                "recovery_actions": data.get("recovery_actions", []),
                "prevention_strategies": data.get("prevention_strategies", [])
            },
            domain=data.get("domain", "general"),
            applicable_contexts=data.get("contexts", []),
            supporting_instances=[data],
            success_rate=0.0,  # Error patterns track failure
            confidence_interval=(0.0, 0.3),
            discovered_at=datetime.now(),
            last_validated=datetime.now(),
            discovery_bot=bot_id
        )
        
        self.learned_patterns[pattern_id] = pattern
        await self._persist_learning_pattern(pattern)
        
        # Also create recovery knowledge
        await self.share_knowledge(
            creator_bot_id=bot_id,
            knowledge_type=KnowledgeType.ERROR_RECOVERY,
            content=pattern.pattern_data,
            domain_tags=[pattern.domain],
            context_tags=pattern.applicable_contexts,
            confidence=0.7
        )
        
        logger.info(f"Error pattern extracted by {bot_id}: {pattern_id}")
    
    async def _extract_collaboration_pattern(self, bot_id: str, data: Dict[str, Any]):
        """Extract collaboration pattern from interaction data"""
        
        pattern_id = str(uuid.uuid4())
        
        pattern = LearningPattern(
            id=pattern_id,
            pattern_type="collaboration_pattern",
            pattern_data={
                "collaboration_structure": data.get("collaboration_structure", {}),
                "communication_patterns": data.get("communication_patterns", []),
                "coordination_strategies": data.get("coordination_strategies", []),
                "success_factors": data.get("success_factors", [])
            },
            domain=data.get("domain", "collaboration"),
            applicable_contexts=data.get("contexts", []),
            supporting_instances=[data],
            success_rate=data.get("collaboration_score", 0.7),
            confidence_interval=(0.6, 0.8),
            discovered_at=datetime.now(),
            last_validated=datetime.now(),
            discovery_bot=bot_id
        )
        
        self.learned_patterns[pattern_id] = pattern
        await self._persist_learning_pattern(pattern)
        
        # Share as collaborative knowledge
        await self.share_knowledge(
            creator_bot_id=bot_id,
            knowledge_type=KnowledgeType.COLLABORATIVE,
            content=pattern.pattern_data,
            domain_tags=[pattern.domain],
            access_level=AccessLevel.COLLABORATIVE_ONLY,
            confidence=0.8
        )
        
        self.sharing_stats["collaborative_contributions"] += 1
        
        logger.info(f"Collaboration pattern extracted by {bot_id}: {pattern_id}")
    
    async def _optimize_context_sharing(self, bot_id: str, data: Dict[str, Any]):
        """Optimize context sharing based on usage patterns"""
        
        # Analyze context usage patterns
        context_usage = data.get("context_usage", {})
        
        for context_id, usage_data in context_usage.items():
            context_frame = self.context_frames.get(context_id)
            if context_frame:
                # Adjust decay rate based on usage frequency
                if usage_data.get("frequency", 0) > 5:
                    context_frame.relevance_decay_rate *= 0.8  # Slower decay for frequently used context
                    context_frame.max_lifetime_hours *= 1.2  # Longer lifetime
                
                await self._persist_context_frame(context_frame)
        
        logger.info(f"Context sharing optimized based on usage patterns")
    
    async def _extract_general_patterns(self, bot_id: str, data: Dict[str, Any]):
        """Extract general patterns from any interaction"""
        
        # Look for recurring themes, successful strategies, etc.
        # This is a simplified implementation
        
        task_type = data.get("task_type", "general")
        outcome_quality = data.get("outcome_quality", 0.5)
        
        if outcome_quality > 0.8:  # High quality outcome
            await self.share_knowledge(
                creator_bot_id=bot_id,
                knowledge_type=KnowledgeType.BEST_PRACTICE,
                content={
                    "task_type": task_type,
                    "approach": data.get("approach", ""),
                    "outcome_quality": outcome_quality,
                    "key_factors": data.get("key_factors", [])
                },
                domain_tags=[task_type],
                confidence=outcome_quality
            )
    
    def _load_from_database(self):
        """Load existing knowledge from database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load knowledge items
            cursor.execute("SELECT * FROM knowledge_items")
            for row in cursor.fetchall():
                item = self._row_to_knowledge_item(row)
                if item:
                    self.knowledge_items[item.id] = item
                    
                    # Rebuild indexes
                    for tag in item.domain_tags:
                        self.domain_index[tag].add(item.id)
                    self.bot_knowledge_index[item.creator_bot_id].add(item.id)
            
            # Load context frames
            cursor.execute("SELECT * FROM context_frames")
            for row in cursor.fetchall():
                frame = self._row_to_context_frame(row)
                if frame and not frame.is_expired():
                    self.context_frames[frame.id] = frame
            
            # Load learning patterns
            cursor.execute("SELECT * FROM learning_patterns")
            for row in cursor.fetchall():
                pattern = self._row_to_learning_pattern(row)
                if pattern:
                    self.learned_patterns[pattern.id] = pattern
            
            conn.close()
            
            logger.info(f"Loaded {len(self.knowledge_items)} knowledge items, "
                       f"{len(self.context_frames)} context frames, "
                       f"{len(self.learned_patterns)} patterns from database")
            
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")
    
    async def _persist_knowledge_item(self, item: KnowledgeItem):
        """Persist knowledge item to database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_items VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.id,
                item.knowledge_type.value,
                json.dumps(item.content),
                item.source.value,
                item.creator_bot_id,
                item.created_at.isoformat(),
                item.updated_at.isoformat(),
                item.access_level.value,
                json.dumps(item.domain_tags),
                json.dumps(item.context_tags),
                item.relevance_score,
                item.confidence,
                item.usage_count,
                item.success_rate,
                json.dumps(item.validation_votes),
                json.dumps(list(item.related_items)),
                item.derived_from,
                item.expiry_date.isoformat() if item.expiry_date else None,
                item.is_deprecated
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to persist knowledge item: {e}")
    
    async def _persist_context_frame(self, frame: ContextFrame):
        """Persist context frame to database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO context_frames VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                frame.id,
                frame.session_id,
                frame.task_id,
                frame.scope.value,
                json.dumps(frame.context_data),
                json.dumps(frame.shared_variables),
                json.dumps(frame.execution_state),
                frame.created_at.isoformat(),
                frame.last_updated.isoformat(),
                json.dumps(list(frame.authorized_bots)),
                frame.access_level.value,
                frame.relevance_decay_rate,
                frame.max_lifetime_hours
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to persist context frame: {e}")
    
    async def _persist_learning_pattern(self, pattern: LearningPattern):
        """Persist learning pattern to database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO learning_patterns VALUES 
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.id,
                pattern.pattern_type,
                json.dumps(pattern.pattern_data),
                pattern.domain,
                json.dumps(pattern.applicable_contexts),
                json.dumps(pattern.supporting_instances),
                pattern.success_rate,
                json.dumps(pattern.confidence_interval),
                pattern.discovered_at.isoformat(),
                pattern.last_validated.isoformat(),
                pattern.discovery_bot,
                pattern.application_count,
                pattern.successful_applications
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to persist learning pattern: {e}")
    
    def _row_to_knowledge_item(self, row) -> Optional[KnowledgeItem]:
        """Convert database row to KnowledgeItem"""
        
        try:
            return KnowledgeItem(
                id=row[0],
                knowledge_type=KnowledgeType(row[1]),
                content=json.loads(row[2]),
                source=KnowledgeSource(row[3]),
                creator_bot_id=row[4],
                created_at=datetime.fromisoformat(row[5]),
                updated_at=datetime.fromisoformat(row[6]),
                access_level=AccessLevel(row[7]),
                domain_tags=json.loads(row[8]),
                context_tags=json.loads(row[9]),
                relevance_score=row[10],
                confidence=row[11],
                usage_count=row[12],
                success_rate=row[13],
                validation_votes=json.loads(row[14]),
                related_items=set(json.loads(row[15])),
                derived_from=row[16],
                expiry_date=datetime.fromisoformat(row[17]) if row[17] else None,
                is_deprecated=bool(row[18])
            )
        except Exception as e:
            logger.error(f"Failed to parse knowledge item from database: {e}")
            return None
    
    def _row_to_context_frame(self, row) -> Optional[ContextFrame]:
        """Convert database row to ContextFrame"""
        
        try:
            return ContextFrame(
                id=row[0],
                session_id=row[1],
                task_id=row[2],
                scope=ContextScope(row[3]),
                context_data=json.loads(row[4]),
                shared_variables=json.loads(row[5]),
                execution_state=json.loads(row[6]),
                created_at=datetime.fromisoformat(row[7]),
                last_updated=datetime.fromisoformat(row[8]),
                authorized_bots=set(json.loads(row[9])),
                access_level=AccessLevel(row[10]),
                relevance_decay_rate=row[11],
                max_lifetime_hours=row[12]
            )
        except Exception as e:
            logger.error(f"Failed to parse context frame from database: {e}")
            return None
    
    def _row_to_learning_pattern(self, row) -> Optional[LearningPattern]:
        """Convert database row to LearningPattern"""
        
        try:
            return LearningPattern(
                id=row[0],
                pattern_type=row[1],
                pattern_data=json.loads(row[2]),
                domain=row[3],
                applicable_contexts=json.loads(row[4]),
                supporting_instances=json.loads(row[5]),
                success_rate=row[6],
                confidence_interval=tuple(json.loads(row[7])),
                discovered_at=datetime.fromisoformat(row[8]),
                last_validated=datetime.fromisoformat(row[9]),
                discovery_bot=row[10],
                application_count=row[11],
                successful_applications=row[12]
            )
        except Exception as e:
            logger.error(f"Failed to parse learning pattern from database: {e}")
            return None
    
    # Public API methods
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get knowledge sharing system statistics"""
        
        active_contexts = sum(1 for ctx in self.context_frames.values() if not ctx.is_expired())
        
        return {
            "knowledge_items": len(self.knowledge_items),
            "active_contexts": active_contexts,
            "learned_patterns": len(self.learned_patterns),
            "domains_covered": len(self.domain_index),
            "contributing_bots": len(self.bot_knowledge_index),
            "sharing_stats": self.sharing_stats.copy()
        }
    
    async def cleanup_expired_data(self):
        """Clean up expired context frames and deprecated knowledge"""
        
        # Clean up expired contexts
        expired_contexts = []
        for context_id, context in self.context_frames.items():
            if context.is_expired():
                expired_contexts.append(context_id)
        
        for context_id in expired_contexts:
            del self.context_frames[context_id]
        
        # Clean up deprecated knowledge (could be more sophisticated)
        deprecated_items = []
        cutoff_date = datetime.now() - timedelta(days=365)  # 1 year old
        
        for item_id, item in self.knowledge_items.items():
            if item.is_deprecated or (item.expiry_date and datetime.now() > item.expiry_date):
                deprecated_items.append(item_id)
            elif item.created_at < cutoff_date and item.usage_count == 0:
                deprecated_items.append(item_id)  # Unused old knowledge
        
        for item_id in deprecated_items:
            if item_id in self.knowledge_items:
                del self.knowledge_items[item_id]
        
        logger.info(f"Cleaned up {len(expired_contexts)} expired contexts and {len(deprecated_items)} deprecated knowledge items")