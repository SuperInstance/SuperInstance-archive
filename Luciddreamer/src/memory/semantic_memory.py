"""
Semantic Memory System

Stores abstract knowledge and facts using vector embeddings for semantic similarity.
Implements knowledge graphs, concept hierarchies, and fact verification systems.
Supports both ChromaDB and FAISS for local vector storage.
"""

import time
import uuid
import json
import pickle
import math
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logger.warning("ChromaDB not available, using fallback storage")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available, using fallback storage")

class FactStatus(Enum):
    """Verification status of semantic facts"""
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    DISPUTED = "disputed"
    DEPRECATED = "deprecated"
    HYPOTHETICAL = "hypothetical"

class ConceptType(Enum):
    """Types of semantic concepts"""
    ENTITY = "entity"           # Person, place, thing
    RELATION = "relation"       # Relationships between entities
    ATTRIBUTE = "attribute"     # Properties and characteristics
    RULE = "rule"              # Rules and principles
    PROCEDURE = "procedure"     # How-to knowledge
    DEFINITION = "definition"   # Concept definitions

@dataclass
class SemanticFact:
    """Individual semantic fact with confidence and verification"""
    fact_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 0.5  # 0-1 confidence in fact validity
    status: FactStatus = FactStatus.UNKNOWN
    source_evidence: List[str] = field(default_factory=list)
    created_timestamp: float = field(default_factory=time.time)
    last_verified: float = field(default_factory=time.time)
    verification_count: int = 0
    contradictions: Set[str] = field(default_factory=set)  # Contradictory fact IDs
    supporting_facts: Set[str] = field(default_factory=set)  # Supporting fact IDs

    def to_triple(self) -> Tuple[str, str, str]:
        """Return as (subject, predicate, object) triple"""
        return (self.subject, self.predicate, self.object)

    def get_age_days(self) -> float:
        """Get age in days"""
        return (time.time() - self.created_timestamp) / 86400.0

    def add_evidence(self, evidence: str):
        """Add supporting evidence"""
        if evidence not in self.source_evidence:
            self.source_evidence.append(evidence)

    def verify(self, verification_result: bool):
        """Update verification status"""
        self.last_verified = time.time()
        self.verification_count += 1

        if verification_result:
            self.confidence = min(1.0, self.confidence + 0.1)
            if self.status == FactStatus.UNKNOWN:
                self.status = FactStatus.VERIFIED
        else:
            self.confidence = max(0.0, self.confidence - 0.2)
            if self.status == FactStatus.VERIFIED:
                self.status = FactStatus.DISPUTED

@dataclass
class SemanticConcept:
    """Semantic concept with embedding and relationships"""
    concept_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    concept_type: ConceptType = ConceptType.ENTITY
    definition: str = ""
    embedding: Optional[np.ndarray] = None
    aliases: Set[str] = field(default_factory=set)
    parent_concepts: Set[str] = field(default_factory=set)  # IS-A relationships
    child_concepts: Set[str] = field(default_factory=set)   # HAS-A relationships
    related_concepts: Set[str] = field(default_factory=set) # Related concepts
    attributes: Dict[str, Any] = field(default_factory=dict)
    created_timestamp: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    def mark_accessed(self):
        """Mark concept as accessed"""
        self.access_count += 1
        self.last_accessed = time.time()

    def add_alias(self, alias: str):
        """Add alternative name for concept"""
        self.aliases.add(alias.lower())

    def has_alias(self, name: str) -> bool:
        """Check if name matches concept or alias"""
        return name.lower() == self.name.lower() or name.lower() in self.aliases

class VectorDatabase:
    """Abstract interface for vector database backends"""

    def __init__(self, embedding_dimension: int = 384):
        self.embedding_dimension = embedding_dimension
        self.is_initialized = False

    def add_vectors(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Add vectors to database"""
        raise NotImplementedError

    def search(self, query_vector: np.ndarray, n_results: int = 10,
               where: Optional[Dict] = None) -> Tuple[List[str], List[float], List[Dict]]:
        """Search for similar vectors"""
        raise NotImplementedError

    def delete(self, ids: List[str]) -> bool:
        """Delete vectors by ID"""
        raise NotImplementedError

    def update(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Update existing vectors"""
        raise NotImplementedError

    def get(self, ids: List[str]) -> Tuple[List[Optional[np.ndarray]], List[Optional[Dict]]]:
        """Get vectors by ID"""
        raise NotImplementedError

class ChromaDBBackend(VectorDatabase):
    """ChromaDB backend for vector storage"""

    def __init__(self, collection_name: str = "semantic_memory",
                 persist_directory: str = "./chroma_db", embedding_dimension: int = 384):
        super().__init__(embedding_dimension)

        if not CHROMADB_AVAILABLE:
            raise ImportError("ChromaDB is not installed")

        self.collection_name = collection_name
        self.persist_directory = persist_directory

        try:
            self.client = chromadb.PersistentClient(path=persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self.is_initialized = True
            logger.info(f"Initialized ChromaDB collection: {collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.is_initialized = False

    def add_vectors(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Add vectors to ChromaDB"""
        if not self.is_initialized:
            return False

        try:
            # Convert numpy arrays to lists for ChromaDB
            vectors_list = vectors.tolist()

            self.collection.add(
                ids=ids,
                embeddings=vectors_list,
                metadatas=metadatas
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors to ChromaDB: {e}")
            return False

    def search(self, query_vector: np.ndarray, n_results: int = 10,
               where: Optional[Dict] = None) -> Tuple[List[str], List[float], List[Dict]]:
        """Search ChromaDB for similar vectors"""
        if not self.is_initialized:
            return [], [], []

        try:
            query_list = query_vector.tolist()

            results = self.collection.query(
                query_embeddings=[query_list],
                n_results=n_results,
                where=where
            )

            ids = results['ids'][0] if results['ids'] else []
            distances = results['distances'][0] if results['distances'] else []
            metadatas = results['metadatas'][0] if results['metadatas'] else []

            return ids, distances, metadatas
        except Exception as e:
            logger.error(f"Failed to search ChromaDB: {e}")
            return [], [], []

    def delete(self, ids: List[str]) -> bool:
        """Delete vectors from ChromaDB"""
        if not self.is_initialized:
            return False

        try:
            self.collection.delete(ids=ids)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from ChromaDB: {e}")
            return False

    def update(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Update vectors in ChromaDB"""
        if not self.is_initialized:
            return False

        try:
            vectors_list = vectors.tolist()

            self.collection.update(
                ids=ids,
                embeddings=vectors_list,
                metadatas=metadatas
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update ChromaDB: {e}")
            return False

    def get(self, ids: List[str]) -> Tuple[List[Optional[np.ndarray]], List[Optional[Dict]]]:
        """Get vectors from ChromaDB"""
        if not self.is_initialized:
            return [], []

        try:
            results = self.collection.get(ids=ids, include=['embeddings', 'metadatas'])

            vectors = []
            metadatas = []

            for i, embedding_id in enumerate(ids):
                if i < len(results['embeddings']):
                    vectors.append(np.array(results['embeddings'][i]))
                else:
                    vectors.append(None)

                if i < len(results['metadatas']):
                    metadatas.append(results['metadatas'][i])
                else:
                    metadatas.append(None)

            return vectors, metadatas
        except Exception as e:
            logger.error(f"Failed to get from ChromaDB: {e}")
            return [], []

class FAISSBackend(VectorDatabase):
    """FAISS backend for vector storage"""

    def __init__(self, embedding_dimension: int = 384, index_type: str = "IVF_Flat"):
        super().__init__(embedding_dimension)

        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is not installed")

        self.index_type = index_type
        self.id_mapping: Dict[int, str] = {}
        self.metadata_mapping: Dict[int, Dict] = {}
        self.next_id = 0

        # Initialize FAISS index
        if index_type == "IVF_Flat":
            quantizer = faiss.IndexFlatIP(embedding_dimension)
            self.index = faiss.IndexIVFFlat(quantizer, embedding_dimension, 100)
        elif index_type == "Flat":
            self.index = faiss.IndexFlatIP(embedding_dimension)
        else:
            self.index = faiss.IndexFlatIP(embedding_dimension)

        self.is_initialized = True
        logger.info(f"Initialized FAISS index: {index_type}")

    def add_vectors(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Add vectors to FAISS index"""
        if not self.is_initialized:
            return False

        try:
            # Normalize vectors for cosine similarity
            normalized_vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

            # Add to index
            start_id = self.next_id
            self.index.add(normalized_vectors)

            # Update mappings
            for i, (id_, metadata) in enumerate(zip(ids, metadatas)):
                internal_id = start_id + i
                self.id_mapping[internal_id] = id_
                self.metadata_mapping[internal_id] = metadata

            self.next_id += len(ids)
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors to FAISS: {e}")
            return False

    def search(self, query_vector: np.ndarray, n_results: int = 10,
               where: Optional[Dict] = None) -> Tuple[List[str], List[float], List[Dict]]:
        """Search FAISS index for similar vectors"""
        if not self.is_initialized:
            return [], [], []

        try:
            # Normalize query vector
            normalized_query = query_vector / np.linalg.norm(query_vector)
            normalized_query = normalized_query.reshape(1, -1)

            # Search
            scores, indices = self.index.search(normalized_query, min(n_results * 2, self.next_id))

            # Filter results and map back to original IDs
            result_ids = []
            result_scores = []
            result_metadatas = []

            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for invalid results
                    continue

                if idx in self.id_mapping:
                    original_id = self.id_mapping[idx]
                    metadata = self.metadata_mapping[idx]

                    # Apply metadata filter if specified
                    if where:
                        if not self._matches_filter(metadata, where):
                            continue

                    result_ids.append(original_id)
                    result_scores.append(float(score))
                    result_metadatas.append(metadata)

                    if len(result_ids) >= n_results:
                        break

            return result_ids, result_scores, result_metadatas
        except Exception as e:
            logger.error(f"Failed to search FAISS: {e}")
            return [], [], []

    def delete(self, ids: List[str]) -> bool:
        """Delete vectors from FAISS (not fully supported)"""
        # FAISS doesn't support deletion well, so we'd need to rebuild
        logger.warning("FAISS deletion not fully supported")
        return False

    def update(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Update vectors in FAISS (not fully supported)"""
        logger.warning("FAISS update not fully supported")
        return False

    def get(self, ids: List[str]) -> Tuple[List[Optional[np.ndarray]], List[Optional[Dict]]]:
        """Get vectors from FAISS (inefficient)"""
        vectors = []
        metadatas = []

        for target_id in ids:
            vector = None
            metadata = None

            # Find internal ID
            for internal_id, original_id in self.id_mapping.items():
                if original_id == target_id:
                    # FAISS doesn't provide efficient retrieval by ID
                    # This is a limitation of the current implementation
                    metadata = self.metadata_mapping.get(internal_id)
                    break

            vectors.append(vector)
            metadatas.append(metadata)

        return vectors, metadatas

    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

class FallbackBackend(VectorDatabase):
    """Fallback in-memory vector storage"""

    def __init__(self, embedding_dimension: int = 384):
        super().__init__(embedding_dimension)
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadatas: Dict[str, Dict] = {}
        self.is_initialized = True
        logger.info("Initialized fallback in-memory vector store")

    def add_vectors(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Add vectors to memory"""
        try:
            for id_, vector, metadata in zip(ids, vectors, metadatas):
                self.vectors[id_] = vector
                self.metadatas[id_] = metadata
            return True
        except Exception as e:
            logger.error(f"Failed to add vectors to fallback: {e}")
            return False

    def search(self, query_vector: np.ndarray, n_results: int = 10,
               where: Optional[Dict] = None) -> Tuple[List[str], List[float], List[Dict]]:
        """Search for similar vectors"""
        try:
            results = []

            for id_, vector in self.vectors.items():
                # Apply metadata filter
                if where and not self._matches_filter(self.metadatas[id_], where):
                    continue

                # Calculate cosine similarity
                similarity = np.dot(query_vector, vector) / (
                    np.linalg.norm(query_vector) * np.linalg.norm(vector)
                )

                results.append((id_, similarity, self.metadatas[id_]))

            # Sort by similarity
            results.sort(key=lambda x: x[1], reverse=True)

            # Return top results
            top_results = results[:n_results]
            ids = [r[0] for r in top_results]
            scores = [r[1] for r in top_results]
            metadatas = [r[2] for r in top_results]

            return ids, scores, metadatas
        except Exception as e:
            logger.error(f"Failed to search fallback: {e}")
            return [], [], []

    def delete(self, ids: List[str]) -> bool:
        """Delete vectors"""
        try:
            for id_ in ids:
                self.vectors.pop(id_, None)
                self.metadatas.pop(id_, None)
            return True
        except Exception as e:
            logger.error(f"Failed to delete from fallback: {e}")
            return False

    def update(self, ids: List[str], vectors: np.ndarray, metadatas: List[Dict]) -> bool:
        """Update vectors"""
        return self.add_vectors(ids, vectors, metadatas)

    def get(self, ids: List[str]) -> Tuple[List[Optional[np.ndarray]], List[Optional[Dict]]]:
        """Get vectors"""
        vectors = []
        metadatas = []

        for id_ in ids:
            vectors.append(self.vectors.get(id_))
            metadatas.append(self.metadatas.get(id_))

        return vectors, metadatas

    def _matches_filter(self, metadata: Dict, filter_dict: Dict) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

class SemanticMemory:
    """
    Semantic memory system for storing abstract knowledge and facts.
    Supports multiple vector database backends and implements knowledge graphs.
    """

    def __init__(self, backend: str = "auto", storage_path: Optional[str] = None,
                 embedding_dimension: int = 384):
        """
        Initialize semantic memory system

        Args:
            backend: Vector database backend ("chroma", "faiss", "fallback", "auto")
            storage_path: Path for persistent storage
            embedding_dimension: Dimension of embedding vectors
        """
        self.embedding_dimension = embedding_dimension
        self.storage_path = storage_path

        # Initialize vector database backend
        self.vector_db = self._initialize_backend(backend)

        # In-memory stores for concepts and facts
        self.concepts: Dict[str, SemanticConcept] = {}
        self.facts: Dict[str, SemanticFact] = {}

        # Indexes for efficient lookup
        self.concept_name_index: Dict[str, str] = {}  # name -> concept_id
        self.fact_triple_index: Dict[Tuple[str, str, str], str] = {}  # triple -> fact_id

        # Statistics
        self.total_concepts = 0
        self.total_facts = 0
        self.total_searches = 0

        # Load existing data if storage path provided
        if storage_path:
            self._load_data()

    def _initialize_backend(self, backend: str) -> VectorDatabase:
        """Initialize the vector database backend"""
        if backend == "auto":
            # Try ChromaDB first, then FAISS, then fallback
            if CHROMADB_AVAILABLE:
                try:
                    return ChromaDBBackend(
                        collection_name="semantic_memory",
                        persist_directory=self.storage_path + "/chroma" if self.storage_path else "./chroma_db",
                        embedding_dimension=self.embedding_dimension
                    )
                except Exception:
                    pass

            if FAISS_AVAILABLE:
                try:
                    return FAISSBackend(embedding_dimension=self.embedding_dimension)
                except Exception:
                    pass

            return FallbackBackend(embedding_dimension=self.embedding_dimension)

        elif backend == "chroma":
            if not CHROMADB_AVAILABLE:
                logger.warning("ChromaDB not available, falling back to in-memory storage")
                return FallbackBackend(embedding_dimension=self.embedding_dimension)
            return ChromaDBBackend(embedding_dimension=self.embedding_dimension)

        elif backend == "faiss":
            if not FAISS_AVAILABLE:
                logger.warning("FAISS not available, falling back to in-memory storage")
                return FallbackBackend(embedding_dimension=self.embedding_dimension)
            return FAISSBackend(embedding_dimension=self.embedding_dimension)

        else:  # fallback
            return FallbackBackend(embedding_dimension=self.embedding_dimension)

    def add_concept(self, name: str, concept_type: ConceptType = ConceptType.ENTITY,
                   definition: str = "", embedding: Optional[np.ndarray] = None,
                   aliases: Set[str] = None, attributes: Dict[str, Any] = None) -> str:
        """
        Add a semantic concept

        Args:
            name: Concept name
            concept_type: Type of concept
            definition: Concept definition
            embedding: Vector embedding
            aliases: Alternative names
            attributes: Concept attributes

        Returns:
            Concept ID
        """
        concept = SemanticConcept(
            name=name,
            concept_type=concept_type,
            definition=definition,
            embedding=embedding,
            aliases=aliases or set(),
            attributes=attributes or {}
        )

        # Check for existing concept with same name
        if name.lower() in self.concept_name_index:
            existing_id = self.concept_name_index[name.lower()]
            logger.warning(f"Concept '{name}' already exists (ID: {existing_id})")
            return existing_id

        # Store concept
        self.concepts[concept.concept_id] = concept
        self.concept_name_index[name.lower()] = concept.concept_id

        # Add aliases to index
        for alias in concept.aliases:
            if alias.lower() not in self.concept_name_index:
                self.concept_name_index[alias.lower()] = concept.concept_id

        # Add to vector database if embedding provided
        if embedding is not None:
            metadata = {
                "type": "concept",
                "name": name,
                "concept_type": concept_type.value,
                "definition": definition
            }
            self.vector_db.add_vectors([concept.concept_id], [embedding.reshape(1, -1)], [metadata])

        self.total_concepts += 1
        logger.debug(f"Added concept: {name} ({concept.concept_id[:8]}...)")

        return concept.concept_id

    def get_concept(self, concept_id: str) -> Optional[SemanticConcept]:
        """Get concept by ID"""
        concept = self.concepts.get(concept_id)
        if concept:
            concept.mark_accessed()
        return concept

    def find_concept_by_name(self, name: str) -> Optional[SemanticConcept]:
        """Find concept by name or alias"""
        concept_id = self.concept_name_index.get(name.lower())
        if concept_id:
            return self.get_concept(concept_id)
        return None

    def add_fact(self, subject: str, predicate: str, obj: str,
                 confidence: float = 0.5, source_evidence: List[str] = None,
                 embedding: Optional[np.ndarray] = None) -> str:
        """
        Add a semantic fact

        Args:
            subject: Subject entity
            predicate: Relationship/property
            obj: Object entity/value
            confidence: Confidence in fact validity
            source_evidence: Supporting evidence
            embedding: Vector embedding for the fact

        Returns:
            Fact ID
        """
        fact = SemanticFact(
            subject=subject,
            predicate=predicate,
            object=obj,
            confidence=confidence,
            source_evidence=source_evidence or []
        )

        # Check for existing fact
        triple = (subject, predicate, obj)
        if triple in self.fact_triple_index:
            existing_id = self.fact_triple_index[triple]
            # Update confidence if new fact is more confident
            if confidence > self.facts[existing_id].confidence:
                self.facts[existing_id].confidence = confidence
                logger.debug(f"Updated fact confidence: {existing_id[:8]}...")
            return existing_id

        # Store fact
        self.facts[fact.fact_id] = fact
        self.fact_triple_index[triple] = fact.fact_id

        # Add to vector database if embedding provided
        if embedding is not None:
            metadata = {
                "type": "fact",
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "confidence": confidence
            }
            self.vector_db.add_vectors([fact.fact_id], [embedding.reshape(1, -1)], [metadata])

        self.total_facts += 1
        logger.debug(f"Added fact: {subject} {predicate} {obj} ({fact.fact_id[:8]}...)")

        return fact.fact_id

    def get_fact(self, fact_id: str) -> Optional[SemanticFact]:
        """Get fact by ID"""
        return self.facts.get(fact_id)

    def search_concepts(self, query: str, limit: int = 10,
                       concept_type: Optional[ConceptType] = None) -> List[Tuple[SemanticConcept, float]]:
        """
        Search for concepts by semantic similarity

        Args:
            query: Search query
            limit: Maximum results
            concept_type: Filter by concept type

        Returns:
            List of (concept, similarity_score) tuples
        """
        # This would typically use an embedding model to convert query to vector
        # For now, we'll implement simple text-based search
        query_lower = query.lower()
        matches = []

        for concept in self.concepts.values():
            # Filter by concept type if specified
            if concept_type and concept.concept_type != concept_type:
                continue

            # Simple text matching (would be semantic search with embeddings)
            score = 0.0
            if query_lower in concept.name.lower():
                score += 1.0
            if query_lower in concept.definition.lower():
                score += 0.5
            if any(query_lower in alias.lower() for alias in concept.aliases):
                score += 0.3

            if score > 0:
                matches.append((concept, score))

        # Sort by score and return top results
        matches.sort(key=lambda x: x[1], reverse=True)
        results = matches[:limit]

        # Mark accessed
        for concept, _ in results:
            concept.mark_accessed()

        return results

    def search_facts(self, subject: Optional[str] = None, predicate: Optional[str] = None,
                    obj: Optional[str] = None, limit: int = 20) -> List[SemanticFact]:
        """
        Search for facts by triple components

        Args:
            subject: Filter by subject
            predicate: Filter by predicate
            obj: Filter by object
            limit: Maximum results

        Returns:
            List of matching facts
        """
        matches = []

        for fact in self.facts.values():
            if subject and fact.subject != subject:
                continue
            if predicate and fact.predicate != predicate:
                continue
            if obj and fact.object != obj:
                continue

            matches.append(fact)

        # Sort by confidence
        matches.sort(key=lambda f: f.confidence, reverse=True)
        return matches[:limit]

    def get_related_concepts(self, concept_id: str, relation_type: str = "any",
                            limit: int = 10) -> List[SemanticConcept]:
        """
        Get concepts related to a given concept

        Args:
            concept_id: Source concept ID
            relation_type: Type of relation ("parent", "child", "related", "any")
            limit: Maximum results

        Returns:
            List of related concepts
        """
        if concept_id not in self.concepts:
            return []

        concept = self.concepts[concept_id]
        related_ids = set()

        if relation_type in ("parent", "any"):
            related_ids.update(concept.parent_concepts)
        if relation_type in ("child", "any"):
            related_ids.update(concept.child_concepts)
        if relation_type in ("related", "any"):
            related_ids.update(concept.related_concepts)

        # Convert to concept objects
        related_concepts = []
        for related_id in related_ids:
            if related_id in self.concepts:
                related_concepts.append(self.concepts[related_id])

        # Sort by access frequency
        related_concepts.sort(key=lambda c: c.access_count, reverse=True)
        return related_concepts[:limit]

    def link_concepts(self, concept_id1: str, concept_id2: str, relation_type: str = "related"):
        """
        Create a relationship between two concepts

        Args:
            concept_id1: First concept ID
            concept_id2: Second concept ID
            relation_type: Type of relationship
        """
        if concept_id1 not in self.concepts or concept_id2 not in self.concepts:
            return

        concept1 = self.concepts[concept_id1]
        concept2 = self.concepts[concept_id2]

        if relation_type == "parent":
            concept1.parent_concepts.add(concept_id2)
            concept2.child_concepts.add(concept_id1)
        elif relation_type == "child":
            concept1.child_concepts.add(concept_id2)
            concept2.parent_concepts.add(concept_id1)
        else:  # related
            concept1.related_concepts.add(concept_id2)
            concept2.related_concepts.add(concept_id1)

    def verify_fact(self, fact_id: str, is_correct: bool, evidence: str = ""):
        """
        Verify or dispute a fact

        Args:
            fact_id: Fact ID to verify
            is_correct: Whether the fact is correct
            evidence: Supporting evidence
        """
        if fact_id not in self.facts:
            return

        fact = self.facts[fact_id]
        fact.verify(is_correct)

        if evidence:
            fact.add_evidence(evidence)

    def get_concept_hierarchy(self, root_concept_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """
        Get concept hierarchy starting from a root concept

        Args:
            root_concept_id: Root concept ID
            max_depth: Maximum depth to traverse

        Returns:
            Hierarchical representation of concepts
        """
        if root_concept_id not in self.concepts:
            return {}

        def build_hierarchy(concept_id: str, depth: int) -> Dict[str, Any]:
            if depth >= max_depth or concept_id not in self.concepts:
                return {}

            concept = self.concepts[concept_id]

            hierarchy = {
                "id": concept_id,
                "name": concept.name,
                "type": concept.concept_type.value,
                "definition": concept.definition,
                "children": []
            }

            # Add child concepts
            for child_id in concept.child_concepts:
                child_hierarchy = build_hierarchy(child_id, depth + 1)
                if child_hierarchy:
                    hierarchy["children"].append(child_hierarchy)

            return hierarchy

        return build_hierarchy(root_concept_id, 0)

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about semantic memory"""
        # Count concept types
        concept_types = {}
        for concept in self.concepts.values():
            concept_type = concept.concept_type.value
            concept_types[concept_type] = concept_types.get(concept_type, 0) + 1

        # Count fact statuses
        fact_statuses = {}
        for fact in self.facts.values():
            status = fact.status.value
            fact_statuses[status] = fact_statuses.get(status, 0) + 1

        # Average confidence
        avg_confidence = 0.0
        if self.facts:
            avg_confidence = sum(fact.confidence for fact in self.facts.values()) / len(self.facts)

        return {
            "total_concepts": len(self.concepts),
            "total_facts": len(self.facts),
            "concept_types": concept_types,
            "fact_statuses": fact_statuses,
            "average_fact_confidence": avg_confidence,
            "vector_db_backend": type(self.vector_db).__name__,
            "vector_db_initialized": self.vector_db.is_initialized,
            "total_searches": self.total_searches
        }

    def _save_data(self):
        """Save semantic memory data to persistent storage"""
        if not self.storage_path:
            return

        try:
            data = {
                "concepts": {cid: asdict(concept) for cid, concept in self.concepts.items()},
                "facts": {fid: asdict(fact) for fid, fact in self.facts.items()},
                "concept_name_index": self.concept_name_index,
                "fact_triple_index": {str(k): v for k, v in self.fact_triple_index.items()},
                "statistics": {
                    "total_concepts": self.total_concepts,
                    "total_facts": self.total_facts,
                    "total_searches": self.total_searches
                }
            }

            # Handle numpy arrays in concepts
            for cid, concept_data in data["concepts"].items():
                if "embedding" in concept_data and concept_data["embedding"] is not None:
                    concept_data["embedding"] = concept_data["embedding"].tolist()

            with open(self.storage_path, 'wb') as f:
                pickle.dump(data, f)

        except Exception as e:
            logger.error(f"Failed to save semantic memory data: {e}")

    def _load_data(self):
        """Load semantic memory data from persistent storage"""
        if not self.storage_path:
            return

        try:
            with open(self.storage_path, 'rb') as f:
                data = pickle.load(f)

            # Load concepts
            for concept_id, concept_data in data.get("concepts", {}).items():
                # Handle embedding
                if "embedding" in concept_data and concept_data["embedding"] is not None:
                    concept_data["embedding"] = np.array(concept_data["embedding"])

                # Convert sets back
                if "aliases" in concept_data:
                    concept_data["aliases"] = set(concept_data["aliases"])
                if "parent_concepts" in concept_data:
                    concept_data["parent_concepts"] = set(concept_data["parent_concepts"])
                if "child_concepts" in concept_data:
                    concept_data["child_concepts"] = set(concept_data["child_concepts"])
                if "related_concepts" in concept_data:
                    concept_data["related_concepts"] = set(concept_data["related_concepts"])

                concept = SemanticConcept(**concept_data)
                self.concepts[concept_id] = concept

            # Load facts
            for fact_id, fact_data in data.get("facts", {}).items():
                # Convert sets back
                if "source_evidence" in fact_data:
                    fact_data["source_evidence"] = set(fact_data["source_evidence"])
                if "contradictions" in fact_data:
                    fact_data["contradictions"] = set(fact_data["contradictions"])
                if "supporting_facts" in fact_data:
                    fact_data["supporting_facts"] = set(fact_data["supporting_facts"])

                # Convert enum
                if "status" in fact_data:
                    fact_data["status"] = FactStatus[fact_data["status"]]

                fact = SemanticFact(**fact_data)
                self.facts[fact_id] = fact

            # Load indexes
            self.concept_name_index = data.get("concept_name_index", {})

            # Convert fact triple index keys back to tuples
            fact_triple_data = data.get("fact_triple_index", {})
            self.fact_triple_index = {
                eval(k): v for k, v in fact_triple_data.items()
            }

            # Load statistics
            stats = data.get("statistics", {})
            self.total_concepts = stats.get("total_concepts", 0)
            self.total_facts = stats.get("total_facts", 0)
            self.total_searches = stats.get("total_searches", 0)

            logger.info(f"Loaded semantic memory: {len(self.concepts)} concepts, {len(self.facts)} facts")

        except FileNotFoundError:
            logger.info("No existing semantic memory storage found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load semantic memory data: {e}")

    def __len__(self) -> int:
        """Return total number of items (concepts + facts)"""
        return len(self.concepts) + len(self.facts)