"""
AI Society Portal - Vector Memory Store (Qdrant Integration)
=============================================================
High-performance semantic memory retrieval using Qdrant vector database.
Each character gets their own memory collection with weighted retrieval.

Weeks 1-2: Vector Database Infrastructure
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
import json

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    print("Warning: qdrant-client not installed. Install with: pip install qdrant-client")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")


# ============================================================================
# VECTOR STORE INTERFACE
# ============================================================================

@dataclass
class MemoryVector:
    """Memory with embedding and metadata"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    character_id: str = ""
    timestamp: str = ""
    memory_type: str = ""
    importance: float = 5.0
    emotional_valence: float = 0.0
    participants: List[str] = None
    location: str = ""
    consolidated: bool = False
    is_temporal_landmark: bool = False
    landmark_type: Optional[str] = None
    access_count: int = 0


class EmbeddingModel:
    """Wrapper for embedding generation"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                print(f"Error loading embedding model: {e}")
    
    def encode(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if self.model is None:
            # Fallback: simple hash-based embedding
            return self._hash_embedding(text)
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=False)
            return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
        except Exception as e:
            print(f"Error encoding text: {e}")
            return self._hash_embedding(text)
    
    def _hash_embedding(self, text: str) -> List[float]:
        """Simple hash-based embedding (fallback)"""
        import hashlib
        # Create 384-dim embedding from hash (matches MiniLM size)
        hash_digest = hashlib.sha256(text.encode()).hexdigest()
        embedding = []
        for i in range(384):
            byte_val = int(hash_digest[i % len(hash_digest)], 16)
            embedding.append((byte_val - 7.5) / 7.5)  # Normalize to ~[-1, 1]
        return embedding


class QdrantMemoryStore:
    """
    Vector memory store using Qdrant.
    Each character gets their own collection with semantic search.
    """
    
    def __init__(self, character_id: str,
                 qdrant_url: str = "http://localhost:6333",
                 collection_name_prefix: str = "character_memories_"):
        self.character_id = character_id
        self.qdrant_url = qdrant_url
        self.collection_name = f"{collection_name_prefix}{character_id}"
        
        # Initialize client
        self.client = None
        self.embedding_model = EmbeddingModel()
        
        if QDRANT_AVAILABLE:
            try:
                self.client = QdrantClient(url=qdrant_url)
            except Exception as e:
                print(f"Warning: Could not connect to Qdrant at {qdrant_url}: {e}")
                self.client = None
        
        # In-memory fallback storage (if Qdrant not available)
        self.fallback_memories: Dict[str, MemoryVector] = {}
        
        # Initialize collection if using Qdrant
        if self.client:
            self._init_collection()
    
    def _init_collection(self):
        """Initialize Qdrant collection for this character"""
        if not self.client:
            return
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create new collection
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=384,  # MiniLM dimension
                        distance=Distance.COSINE
                    )
                )
                print(f"Created memory collection: {self.collection_name}")
        except Exception as e:
            print(f"Error initializing collection: {e}")
    
    def store_memory(self, memory_vector: MemoryVector) -> bool:
        """
        Store memory with embedding to Qdrant.
        Returns True if successful.
        """
        # Generate embedding if not provided
        if memory_vector.embedding is None:
            memory_vector.embedding = self.embedding_model.encode(memory_vector.content)
        
        # Try Qdrant first
        if self.client:
            try:
                point = PointStruct(
                    id=hash(memory_vector.id) % (2**31),  # Convert to int
                    vector=memory_vector.embedding,
                    payload={
                        "id": memory_vector.id,
                        "content": memory_vector.content,
                        "character_id": memory_vector.character_id,
                        "timestamp": memory_vector.timestamp,
                        "memory_type": memory_vector.memory_type,
                        "importance": memory_vector.importance,
                        "emotional_valence": memory_vector.emotional_valence,
                        "participants": memory_vector.participants or [],
                        "location": memory_vector.location,
                        "consolidated": memory_vector.consolidated,
                        "is_temporal_landmark": memory_vector.is_temporal_landmark,
                        "landmark_type": memory_vector.landmark_type,
                        "access_count": memory_vector.access_count,
                    }
                )
                
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[point]
                )
                return True
            except Exception as e:
                print(f"Error storing to Qdrant: {e}")
                # Fall back to memory storage
                self.fallback_memories[memory_vector.id] = memory_vector
                return False
        else:
            # Use fallback storage
            self.fallback_memories[memory_vector.id] = memory_vector
            return True
    
    def retrieve_memories(self, query: str, top_k: int = 10,
                         filters: Optional[Dict[str, Any]] = None,
                         α_recency: float = 1.0,
                         α_importance: float = 1.0,
                         α_relevance: float = 1.0) -> List[MemoryVector]:
        """
        Retrieve memories with weighted scoring.
        
        Weights:
        - α_recency: How much to weight recency (0.995^hours decay)
        - α_importance: How much to weight importance
        - α_relevance: How much to weight semantic similarity
        """
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query)
        
        # Try Qdrant first
        if self.client:
            try:
                # Build filter if provided
                search_filter = None
                if filters:
                    from qdrant_client.models import Filter, FieldCondition, MatchValue
                    conditions = []
                    
                    if "memory_type" in filters:
                        conditions.append(
                            FieldCondition(
                                key="memory_type",
                                match=MatchValue(value=filters["memory_type"])
                            )
                        )
                    
                    if "consolidated" in filters:
                        conditions.append(
                            FieldCondition(
                                key="consolidated",
                                match=MatchValue(value=filters["consolidated"])
                            )
                        )
                    
                    if conditions:
                        search_filter = Filter(must=conditions)
                
                # Search in Qdrant
                search_results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    query_filter=search_filter,
                    limit=top_k * 3,  # Get 3x for re-ranking
                    with_payload=True
                )
                
                # Re-rank with weighted scoring
                memories = []
                current_time = datetime.now()
                
                for result in search_results:
                    payload = result.payload
                    
                    # Calculate scores
                    relevance_score = result.score  # Cosine similarity already from Qdrant
                    
                    # Recency score
                    try:
                        timestamp = datetime.fromisoformat(payload["timestamp"])
                        hours_ago = (current_time - timestamp).total_seconds() / 3600
                        recency_score = 0.995 ** hours_ago
                    except:
                        recency_score = 0.5
                    
                    # Importance score
                    importance_score = payload.get("importance", 5.0) / 10.0
                    
                    # Weighted combination
                    total_weight = α_recency + α_importance + α_relevance
                    combined_score = (
                        α_recency * recency_score +
                        α_importance * importance_score +
                        α_relevance * relevance_score
                    ) / total_weight
                    
                    memory = MemoryVector(
                        id=payload["id"],
                        content=payload["content"],
                        embedding=result.vector,
                        character_id=payload["character_id"],
                        timestamp=payload["timestamp"],
                        memory_type=payload["memory_type"],
                        importance=payload["importance"],
                        emotional_valence=payload.get("emotional_valence", 0.0),
                        participants=payload.get("participants", []),
                        location=payload.get("location", ""),
                        consolidated=payload["consolidated"],
                        is_temporal_landmark=payload.get("is_temporal_landmark", False),
                        landmark_type=payload.get("landmark_type"),
                        access_count=payload.get("access_count", 0)
                    )
                    
                    memories.append((combined_score, memory))
                
                # Sort and return top_k
                memories.sort(reverse=True, key=lambda x: x[0])
                return [m for _, m in memories[:top_k]]
                
            except Exception as e:
                print(f"Error querying Qdrant: {e}")
                # Fall back to memory storage
        
        # Use fallback retrieval
        return self._fallback_retrieve(query, top_k, α_recency, α_importance, α_relevance)
    
    def _fallback_retrieve(self, query: str, top_k: int,
                          α_recency: float, α_importance: float,
                          α_relevance: float) -> List[MemoryVector]:
        """Fallback retrieval from in-memory storage"""
        scored = []
        current_time = datetime.now()
        
        for memory in self.fallback_memories.values():
            # Simple text similarity
            relevance_score = self._text_similarity(query, memory.content)
            
            # Recency
            try:
                timestamp = datetime.fromisoformat(memory.timestamp)
                hours_ago = (current_time - timestamp).total_seconds() / 3600
                recency_score = 0.995 ** hours_ago
            except:
                recency_score = 0.5
            
            # Importance
            importance_score = memory.importance / 10.0
            
            # Combined
            total_weight = α_recency + α_importance + α_relevance
            score = (
                α_recency * recency_score +
                α_importance * importance_score +
                α_relevance * relevance_score
            ) / total_weight
            
            scored.append((score, memory))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [m for _, m in scored[:top_k]]
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity (word overlap)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about this character's memory collection"""
        if self.client:
            try:
                info = self.client.get_collection(self.collection_name)
                return {
                    "name": self.collection_name,
                    "points_count": info.points_count,
                    "vectors_count": info.vectors_count if hasattr(info, 'vectors_count') else "N/A",
                    "status": "Qdrant"
                }
            except:
                pass
        
        return {
            "name": self.collection_name,
            "memories_count": len(self.fallback_memories),
            "status": "Fallback (in-memory)"
        }


# ============================================================================
# BATCH MEMORY OPERATIONS
# ============================================================================

class MemoryBatchProcessor:
    """Batch operations for efficient memory processing"""
    
    @staticmethod
    def batch_consolidate_memories(store: QdrantMemoryStore,
                                   memories: List[MemoryVector],
                                   batch_size: int = 100) -> int:
        """Efficiently store batch of memories"""
        stored_count = 0
        
        for i in range(0, len(memories), batch_size):
            batch = memories[i:i+batch_size]
            for memory in batch:
                if store.store_memory(memory):
                    stored_count += 1
        
        return stored_count
    
    @staticmethod
    def batch_retrieve_for_context(stores: Dict[str, QdrantMemoryStore],
                                   query: str,
                                   top_k_per_character: int = 5) -> Dict[str, List[MemoryVector]]:
        """Retrieve memories from multiple character stores for context"""
        results = {}
        
        for char_id, store in stores.items():
            results[char_id] = store.retrieve_memories(
                query,
                top_k=top_k_per_character,
                α_recency=1.0,
                α_importance=1.0,
                α_relevance=1.0
            )
        
        return results


# ============================================================================
# MEMORY SEARCH UTILITIES
# ============================================================================

class MemorySearchEngine:
    """Advanced memory search and retrieval patterns"""
    
    def __init__(self, character_memory_stores: Dict[str, QdrantMemoryStore]):
        self.stores = character_memory_stores
    
    def search_by_theme(self, theme: str, character_id: str,
                       top_k: int = 10) -> List[MemoryVector]:
        """Search for memories related to a theme"""
        if character_id not in self.stores:
            return []
        
        return self.stores[character_id].retrieve_memories(
            query=theme,
            top_k=top_k,
            α_recency=0.5,  # Less weight on recency
            α_importance=1.5,  # More weight on importance
            α_relevance=1.0
        )
    
    def search_by_time_period(self, character_id: str,
                             days_back: int = 7,
                             top_k: int = 10) -> List[MemoryVector]:
        """Search for recent memories within time period"""
        if character_id not in self.stores:
            return []
        
        # Would be better with Qdrant range filter
        # For now, use a dummy query to get recent memories
        return self.stores[character_id].retrieve_memories(
            query="recent past present",
            top_k=top_k,
            α_recency=2.0,  # Heavy weight on recency
            α_importance=0.5,
            α_relevance=0.0  # Ignore semantic relevance
        )
    
    def cross_character_memory_search(self, query: str,
                                      top_k_per_character: int = 5) -> Dict[str, List[MemoryVector]]:
        """Search across all characters' memories"""
        results = {}
        
        for char_id, store in self.stores.items():
            results[char_id] = store.retrieve_memories(
                query=query,
                top_k=top_k_per_character,
                α_recency=1.0,
                α_importance=1.0,
                α_relevance=1.0
            )
        
        return results