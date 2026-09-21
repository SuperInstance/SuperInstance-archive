"""
Memory Sharing System

Enables memory sharing between pack agents with privacy controls,
conflict resolution, and distributed consensus mechanisms.
Implements peer-to-peer memory synchronization and collaborative learning.
"""

import time
import uuid
import json
import hashlib
import threading
from typing import Dict, List, Any, Optional, Set, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SharePermission(Enum):
    """Memory sharing permissions"""
    PRIVATE = "private"           # Not shared
    PACK_ONLY = "pack_only"       # Only within pack
    ALLIED_PACKS = "allied_packs" # With allied packs
    PUBLIC = "public"             # Anyone

class ShareType(Enum):
    """Types of memory sharing"""
    EXPERIENCE = "experience"     # Direct experiences
    KNOWLEDGE = "knowledge"       # Facts and concepts
    SKILLS = "skills"            # Procedural knowledge
    EMOTIONS = "emotions"        # Emotional experiences
    STRATEGIES = "strategies"     # Plans and tactics

class ConflictResolution(Enum):
    """Conflict resolution strategies"""
    TRUST_SOURCE = "trust_source"     # Trust the source agent
    CONSENSUS = "consensus"          # Group consensus
    MERGE = "merge"                 # Merge conflicting memories
    LATEST_WINS = "latest_wins"      # Most recent memory wins
    TRUSTED_AGENT = "trusted_agent"  # Designated trusted agent
    VOTING = "voting"               # Voting system

class SyncStatus(Enum):
    """Memory synchronization status"""
    PENDING = "pending"         # Awaiting sync
    SYNCING = "syncing"         # Currently syncing
    SYNCED = "synced"          # Successfully synced
    CONFLICT = "conflict"      # Has conflicts
    FAILED = "failed"          # Sync failed

@dataclass
class SharedMemory:
    """Memory that has been shared between agents"""
    memory_id: str
    source_agent_id: str
    content: Any
    memory_type: str
    share_type: ShareType
    permission: SharePermission
    timestamp: float = field(default_factory=time.time)
    version: int = 1
    recipients: Set[str] = field(default_factory=set)
    trust_score: float = 0.5
    verification_count: int = 0
    conflicts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MemoryConflict:
    """Conflict between shared memories"""
    conflict_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_id: str
    conflicting_memories: List[SharedMemory] = field(default_factory=list)
    conflict_type: str = "content_mismatch"
    detection_time: float = field(default_factory=time.time)
    resolution_strategy: ConflictResolution = ConflictResolution.CONSENSUS
    resolved: bool = False
    resolution_result: Optional[SharedMemory] = None

@dataclass
class PackMemoryNode:
    """Node in the pack memory network"""
    agent_id: str
    endpoint: str
    trust_level: float = 0.5
    last_seen: float = field(default_factory=time.time)
    capabilities: Set[str] = field(default_factory=set)
    memory_stats: Dict[str, int] = field(default_factory=dict)
    is_active: bool = True

class MemorySharingProtocol:
    """
    Protocol for sharing memories between pack agents.
    Handles permissions, conflicts, and distributed consensus.
    """

    def __init__(self, agent_id: str, pack_id: str):
        """
        Initialize memory sharing protocol

        Args:
            agent_id: This agent's ID
            pack_id: Pack identifier
        """
        self.agent_id = agent_id
        self.pack_id = pack_id

        # Memory stores
        self.shared_memories: Dict[str, SharedMemory] = {}  # memory_id -> SharedMemory
        self.received_memories: Dict[str, SharedMemory] = {}  # memory_id -> SharedMemory
        self.memory_conflicts: Dict[str, MemoryConflict] = {}  # conflict_id -> MemoryConflict

        # Network management
        self.pack_nodes: Dict[str, PackMemoryNode] = {}  # agent_id -> PackMemoryNode
        self.allied_packs: Set[str] = set()

        # Sharing configuration
        self.default_permission = SharePermission.PACK_ONLY
        self.trust_threshold = 0.3
        self.sync_interval = 60.0  # seconds
        self.conflict_resolution_strategies = {
            ShareType.EXPERIENCE: ConflictResolution.MERGE,
            ShareType.KNOWLEDGE: ConflictResolution.CONSENSUS,
            ShareType.SKILLS: ConflictVerification.MERGE,
            ShareType.EMOTIONS: ConflictResolution.TRUST_SOURCE,
            ShareType.STRATEGIES: ConflictResolution.VOTING
        }

        # Background processes
        self.sync_thread = None
        self.running = False

        # Statistics
        self.sharing_stats = {
            "total_shared": 0,
            "total_received": 0,
            "conflicts_resolved": 0,
            "sync_events": 0
        }

    def start_sync_service(self):
        """Start background memory synchronization service"""
        if self.running:
            return

        self.running = True
        self.sync_thread = threading.Thread(
            target=self._sync_loop,
            daemon=True,
            name="MemorySharingSync"
        )
        self.sync_thread.start()
        logger.info(f"Memory sharing service started for agent {self.agent_id}")

    def stop_sync_service(self):
        """Stop memory synchronization service"""
        self.running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=10.0)
        logger.info(f"Memory sharing service stopped for agent {self.agent_id}")

    def share_memory(self, memory_id: str, content: Any, memory_type: str,
                    share_type: ShareType, permission: SharePermission = None,
                    recipients: Set[str] = None, metadata: Dict[str, Any] = None) -> str:
        """
        Share a memory with other agents

        Args:
            memory_id: Memory identifier
            content: Memory content
            memory_type: Type of memory
            share_type: Type of sharing
            permission: Sharing permission level
            recipients: Specific recipients (optional)
            metadata: Additional metadata

        Returns:
            Shared memory ID
        """
        if permission is None:
            permission = self.default_permission

        shared_memory = SharedMemory(
            memory_id=memory_id,
            source_agent_id=self.agent_id,
            content=content,
            memory_type=memory_type,
            share_type=share_type,
            permission=permission,
            recipients=recipients or set(),
            metadata=metadata or {}
        )

        # Store shared memory
        self.shared_memories[memory_id] = shared_memory

        # Broadcast to network
        if permission in [SharePermission.PACK_ONLY, SharePermission.ALLIED_PACKS, SharePermission.PUBLIC]:
            self._broadcast_shared_memory(shared_memory)

        self.sharing_stats["total_shared"] += 1
        logger.debug(f"Shared memory {memory_id} with permission {permission.value}")

        return memory_id

    def receive_shared_memory(self, shared_memory: SharedMemory,
                            source_agent: str = None) -> bool:
        """
        Receive a shared memory from another agent

        Args:
            shared_memory: The shared memory
            source_agent: Source agent ID

        Returns:
            True if memory was accepted
        """
        # Check permissions
        if not self._can_receive_memory(shared_memory, source_agent):
            logger.debug(f"Rejected memory {shared_memory.memory_id} - permission denied")
            return False

        # Check for conflicts
        existing_memory = self.received_memories.get(shared_memory.memory_id)
        if existing_memory:
            conflict = self._detect_conflict(existing_memory, shared_memory)
            if conflict:
                self.memory_conflicts[conflict.conflict_id] = conflict
                self._resolve_conflict(conflict.conflict_id)
                return False  # Wait for conflict resolution

        # Store memory
        self.received_memories[shared_memory.memory_id] = shared_memory
        self.sharing_stats["total_received"] += 1

        # Update trust score for source agent
        if source_agent and source_agent in self.pack_nodes:
            self._update_trust_score(source_agent, 0.1)  # Positive reinforcement

        logger.debug(f"Received shared memory {shared_memory.memory_id} from {shared_memory.source_agent_id}")
        return True

    def sync_with_agent(self, agent_id: str) -> bool:
        """
        Synchronize memories with a specific agent

        Args:
            agent_id: Agent to sync with

        Returns:
            True if sync was successful
        """
        if agent_id not in self.pack_nodes:
            logger.warning(f"Agent {agent_id} not found in pack network")
            return False

        node = self.pack_nodes[agent_id]
        if not node.is_active:
            logger.debug(f"Agent {agent_id} is not active")
            return False

        try:
            # Exchange recent memories
            recent_memories = self._get_recent_memories(limit=50)
            agent_memories = self._request_agent_memories(agent_id, limit=50)

            # Process received memories
            for memory_data in agent_memories:
                shared_memory = self._deserialize_memory(memory_data)
                self.receive_shared_memory(shared_memory, agent_id)

            # Update last seen
            node.last_seen = time.time()
            self.sharing_stats["sync_events"] += 1

            logger.debug(f"Synced with agent {agent_id}: {len(agent_memories)} memories exchanged")
            return True

        except Exception as e:
            logger.error(f"Failed to sync with agent {agent_id}: {e}")
            return False

    def add_pack_member(self, agent_id: str, endpoint: str, trust_level: float = 0.5,
                       capabilities: Set[str] = None):
        """
        Add a new member to the pack memory network

        Args:
            agent_id: Agent identifier
            endpoint: Network endpoint
            trust_level: Initial trust level
            capabilities: Agent capabilities
        """
        node = PackMemoryNode(
            agent_id=agent_id,
            endpoint=endpoint,
            trust_level=trust_level,
            capabilities=capabilities or set()
        )

        self.pack_nodes[agent_id] = node
        logger.info(f"Added pack member {agent_id} with trust level {trust_level}")

    def remove_pack_member(self, agent_id: str):
        """Remove a member from the pack memory network"""
        if agent_id in self.pack_nodes:
            del self.pack_nodes[agent_id]
            logger.info(f"Removed pack member {agent_id}")

    def get_shared_memory(self, memory_id: str) -> Optional[SharedMemory]:
        """Get a shared memory by ID"""
        return self.shared_memories.get(memory_id) or self.received_memories.get(memory_id)

    def get_pack_memories(self, memory_type: str = None, limit: int = 100) -> List[SharedMemory]:
        """
        Get memories shared within the pack

        Args:
            memory_type: Filter by memory type
            limit: Maximum results

        Returns:
            List of shared memories
        """
        memories = []

        # Combine own shared and received memories
        all_memories = {**self.shared_memories, **self.received_memories}

        for memory in all_memories.values():
            if memory_type is None or memory.memory_type == memory_type:
                memories.append(memory)

        # Sort by timestamp and limit
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        return memories[:limit]

    def resolve_memory_conflict(self, conflict_id: str,
                               resolution_strategy: ConflictResolution = None) -> bool:
        """
        Manually resolve a memory conflict

        Args:
            conflict_id: Conflict identifier
            resolution_strategy: Resolution strategy to use

        Returns:
            True if conflict was resolved
        """
        if conflict_id not in self.memory_conflicts:
            logger.warning(f"Conflict {conflict_id} not found")
            return False

        conflict = self.memory_conflicts[conflict_id]
        if conflict.resolved:
            logger.debug(f"Conflict {conflict_id} already resolved")
            return True

        if resolution_strategy:
            conflict.resolution_strategy = resolution_strategy

        return self._resolve_conflict(conflict_id)

    def get_sharing_statistics(self) -> Dict[str, Any]:
        """Get memory sharing statistics"""
        return {
            **self.sharing_stats,
            "pack_members": len(self.pack_nodes),
            "active_members": sum(1 for node in self.pack_nodes.values() if node.is_active),
            "shared_memories": len(self.shared_memories),
            "received_memories": len(self.received_memories),
            "pending_conflicts": len([c for c in self.memory_conflicts.values() if not c.resolved]),
            "resolved_conflicts": len([c for c in self.memory_conflicts.values() if c.resolved])
        }

    def _can_receive_memory(self, shared_memory: SharedMemory, source_agent: str = None) -> bool:
        """Check if we can receive a shared memory"""
        # Check permission level
        if shared_memory.permission == SharePermission.PRIVATE:
            return False
        elif shared_memory.permission == SharePermission.PACK_ONLY:
            return source_agent in self.pack_nodes
        elif shared_memory.permission == SharePermission.ALLIED_PACKS:
            return (source_agent in self.pack_nodes or
                    any(pack_id in self.allied_packs for pack_id in []))  # Would need pack mapping
        elif shared_memory.permission == SharePermission.PUBLIC:
            return True

        # Check specific recipients
        if shared_memory.recipients and self.agent_id not in shared_memory.recipients:
            return False

        # Check trust level
        if source_agent and source_agent in self.pack_nodes:
            trust_level = self.pack_nodes[source_agent].trust_level
            if trust_level < self.trust_threshold:
                return False

        return True

    def _detect_conflict(self, existing: SharedMemory, new: SharedMemory) -> Optional[MemoryConflict]:
        """Detect conflict between two shared memories"""
        # Simple content comparison
        if str(existing.content) == str(new.content):
            return None

        # Create conflict
        conflict = MemoryConflict(
            memory_id=existing.memory_id,
            conflicting_memories=[existing, new],
            conflict_type="content_mismatch",
            resolution_strategy=self.conflict_resolution_strategies.get(
                existing.share_type, ConflictResolution.CONSENSUS
            )
        )

        return conflict

    def _resolve_conflict(self, conflict_id: str) -> bool:
        """Resolve a memory conflict"""
        if conflict_id not in self.memory_conflicts:
            return False

        conflict = self.memory_conflicts[conflict_id]
        strategy = conflict.resolution_strategy

        try:
            if strategy == ConflictResolution.TRUST_SOURCE:
                resolved_memory = self._resolve_trust_source(conflict)
            elif strategy == ConflictResolution.MERGE:
                resolved_memory = self._resolve_merge(conflict)
            elif strategy == ConflictResolution.LATEST_WINS:
                resolved_memory = self._resolve_latest_wins(conflict)
            elif strategy == ConflictResolution.CONSENSUS:
                resolved_memory = self._resolve_consensus(conflict)
            else:
                # Default to latest wins
                resolved_memory = self._resolve_latest_wins(conflict)

            if resolved_memory:
                conflict.resolved = True
                conflict.resolution_result = resolved_memory

                # Update memory stores
                self.received_memories[resolved_memory.memory_id] = resolved_memory

                self.sharing_stats["conflicts_resolved"] += 1
                logger.debug(f"Resolved conflict {conflict_id} using {strategy.value}")
                return True

        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {e}")

        return False

    def _resolve_trust_source(self, conflict: MemoryConflict) -> Optional[SharedMemory]:
        """Resolve conflict by trusting most trusted source"""
        best_memory = None
        best_trust = -1.0

        for memory in conflict.conflicting_memories:
            trust_level = self._get_agent_trust(memory.source_agent_id)
            if trust_level > best_trust:
                best_trust = trust_level
                best_memory = memory

        return best_memory

    def _resolve_merge(self, conflict: MemoryConflict) -> Optional[SharedMemory]:
        """Resolve conflict by merging memories"""
        # Simple merge: combine content from both memories
        merged_content = []
        metadata = {}

        for memory in conflict.conflicting_memories:
            merged_content.append(str(memory.content))
            metadata.update(memory.metadata)

        merged_memory = SharedMemory(
            memory_id=conflict.memory_id,
            source_agent_id="merged",
            content=" | ".join(merged_content),
            memory_type=conflict.conflicting_memories[0].memory_type,
            share_type=conflict.conflicting_memories[0].share_type,
            permission=conflict.conflicting_memories[0].permission,
            version=max(m.version for m in conflict.conflicting_memories) + 1,
            metadata=metadata
        )

        return merged_memory

    def _resolve_latest_wins(self, conflict: MemoryConflict) -> Optional[SharedMemory]:
        """Resolve conflict by keeping latest memory"""
        return max(conflict.conflicting_memories, key=lambda m: m.timestamp)

    def _resolve_consensus(self, conflict: MemoryConflict) -> Optional[SharedMemory]:
        """Resolve conflict through consensus (simplified)"""
        # For now, use voting based on trust levels
        votes = {}
        for memory in conflict.conflicting_memories:
            trust = self._get_agent_trust(memory.source_agent_id)
            votes[memory.memory_id] = votes.get(memory.memory_id, 0) + trust

        # Find memory with highest votes
        best_memory_id = max(votes, key=votes.get)
        for memory in conflict.conflicting_memories:
            if memory.memory_id == best_memory_id:
                return memory

        return None

    def _get_agent_trust(self, agent_id: str) -> float:
        """Get trust level for an agent"""
        if agent_id == self.agent_id:
            return 1.0
        elif agent_id in self.pack_nodes:
            return self.pack_nodes[agent_id].trust_level
        else:
            return 0.0

    def _update_trust_score(self, agent_id: str, delta: float):
        """Update trust score for an agent"""
        if agent_id in self.pack_nodes:
            node = self.pack_nodes[agent_id]
            node.trust_level = max(0.0, min(1.0, node.trust_level + delta))

    def _broadcast_shared_memory(self, shared_memory: SharedMemory):
        """Broadcast shared memory to pack members"""
        for agent_id, node in self.pack_nodes.items():
            if agent_id != self.agent_id and node.is_active:
                try:
                    self._send_memory_to_agent(agent_id, shared_memory)
                except Exception as e:
                    logger.error(f"Failed to send memory to {agent_id}: {e}")

    def _get_recent_memories(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent shared memories for syncing"""
        memories = []
        cutoff_time = time.time() - (24 * 3600)  # Last 24 hours

        for memory in self.shared_memories.values():
            if memory.timestamp >= cutoff_time:
                memories.append(self._serialize_memory(memory))
                if len(memories) >= limit:
                    break

        return memories

    def _serialize_memory(self, memory: SharedMemory) -> Dict[str, Any]:
        """Serialize shared memory for transmission"""
        data = asdict(memory)
        # Convert sets to lists
        data['recipients'] = list(memory.recipients)
        data['conflicts'] = list(memory.conflicts)
        return data

    def _deserialize_memory(self, data: Dict[str, Any]) -> SharedMemory:
        """Deserialize shared memory from transmission"""
        # Convert lists back to sets
        if 'recipients' in data:
            data['recipients'] = set(data['recipients'])
        if 'conflicts' in data:
            data['conflicts'] = set(data['conflicts'])
        return SharedMemory(**data)

    def _send_memory_to_agent(self, agent_id: str, shared_memory: SharedMemory):
        """Send memory to a specific agent (placeholder)"""
        # In a real implementation, this would use network communication
        # For now, just log the action
        logger.debug(f"Would send memory {shared_memory.memory_id} to agent {agent_id}")

    def _request_agent_memories(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Request memories from a specific agent (placeholder)"""
        # In a real implementation, this would make network request
        # For now, return empty list
        logger.debug(f"Would request memories from agent {agent_id}")
        return []

    def _sync_loop(self):
        """Background synchronization loop"""
        while self.running:
            try:
                # Sync with active pack members
                for agent_id, node in self.pack_nodes.items():
                    if agent_id != self.agent_id and node.is_active:
                        # Check if sync is needed (based on last seen time)
                        time_since_sync = time.time() - node.last_seen
                        if time_since_sync > self.sync_interval:
                            self.sync_with_agent(agent_id)

                # Sleep until next sync
                time.sleep(self.sync_interval)

            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                time.sleep(60)  # Wait before retrying