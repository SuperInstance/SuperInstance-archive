#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Semantic Search
Advanced semantic search using embeddings and vector similarity
"""

import asyncio
import json
import logging
import time
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import sqlite3
import threading
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import TruncatedSVD
import pickle

logger = logging.getLogger(__name__)

@dataclass
class SemanticVector:
    """Semantic vector representation of content"""
    document_id: str
    vector: np.ndarray
    vector_type: str  # "tfidf", "word2vec", "bert", "custom"
    created_at: float = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()

class EmbeddingModel:
    """Base class for embedding models"""
    
    def __init__(self, name: str, dimension: int):
        self.name = name
        self.dimension = dimension
    
    def encode(self, text: str) -> np.ndarray:
        """Encode text to vector representation"""
        raise NotImplementedError
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts to vector representations"""
        return np.array([self.encode(text) for text in texts])

class TFIDFEmbeddingModel(EmbeddingModel):
    """TF-IDF based embedding model"""
    
    def __init__(self, max_features: int = 10000, dimension: int = 512):
        super().__init__("tfidf", dimension)
        self.max_features = max_features
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95
        )
        self.svd = TruncatedSVD(n_components=dimension, random_state=42)
        self.is_fitted = False
    
    def fit(self, corpus: List[str]):
        """Fit the TF-IDF model on corpus"""
        logger.info(f"Fitting TF-IDF model on {len(corpus)} documents")
        
        # Fit TF-IDF
        tfidf_matrix = self.vectorizer.fit_transform(corpus)
        
        # Fit SVD for dimensionality reduction
        self.svd.fit(tfidf_matrix)
        
        self.is_fitted = True
        logger.info(f"TF-IDF model fitted with {len(self.vectorizer.vocabulary_)} features")
    
    def encode(self, text: str) -> np.ndarray:
        """Encode single text"""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        tfidf_vector = self.vectorizer.transform([text])
        semantic_vector = self.svd.transform(tfidf_vector)
        return semantic_vector[0]
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode batch of texts"""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        tfidf_matrix = self.vectorizer.transform(texts)
        semantic_vectors = self.svd.transform(tfidf_matrix)
        return semantic_vectors

class MockBERTEmbeddingModel(EmbeddingModel):
    """Mock BERT-like embedding model for demonstration"""
    
    def __init__(self, dimension: int = 768):
        super().__init__("mock_bert", dimension)
        # In production, use actual BERT/Sentence-BERT models
        np.random.seed(42)
    
    def encode(self, text: str) -> np.ndarray:
        """Generate mock BERT-like embeddings"""
        # Hash text to get consistent embeddings
        text_hash = hash(text) % (2**32)
        np.random.seed(text_hash)
        
        # Generate normalized random vector (mock BERT output)
        vector = np.random.normal(0, 1, self.dimension)
        vector = vector / np.linalg.norm(vector)
        
        return vector
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode batch of texts"""
        return np.array([self.encode(text) for text in texts])

class SemanticIndex:
    """Vector index for semantic search"""
    
    def __init__(self, dimension: int = 512, db_path: str = "semantic_index.db"):
        self.dimension = dimension
        self.vectors: Dict[str, SemanticVector] = {}
        self.document_vectors = None  # Numpy array for fast similarity computation
        self.document_ids = []  # Corresponding document IDs
        
        # Database persistence
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Performance optimization
        self.needs_rebuild = True
    
    def _init_database(self):
        """Initialize database for vector persistence"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_vectors (
                    document_id TEXT PRIMARY KEY,
                    vector BLOB NOT NULL,
                    vector_type TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()
            conn.close()
    
    def add_vector(self, semantic_vector: SemanticVector):
        """Add semantic vector to index"""
        self.vectors[semantic_vector.document_id] = semantic_vector
        self.needs_rebuild = True
        
        # Persist to database
        self._persist_vector(semantic_vector)
    
    def _persist_vector(self, semantic_vector: SemanticVector):
        """Persist vector to database"""
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT OR REPLACE INTO semantic_vectors 
                    (document_id, vector, vector_type, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    semantic_vector.document_id,
                    semantic_vector.vector.tobytes(),
                    semantic_vector.vector_type,
                    semantic_vector.created_at
                ))
                conn.commit()
                conn.close()
        
        # Run in background
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(_db_insert)
    
    def _rebuild_index(self):
        """Rebuild vector matrix for fast similarity search"""
        if not self.needs_rebuild or not self.vectors:
            return
        
        self.document_ids = list(self.vectors.keys())
        vectors_list = [self.vectors[doc_id].vector for doc_id in self.document_ids]
        self.document_vectors = np.vstack(vectors_list)
        
        self.needs_rebuild = False
        logger.info(f"Rebuilt semantic index with {len(self.document_ids)} vectors")
    
    def search_similar(self, query_vector: np.ndarray, limit: int = 50, threshold: float = 0.1) -> List[Tuple[str, float]]:
        """Search for similar vectors using cosine similarity"""
        self._rebuild_index()
        
        if self.document_vectors is None or len(self.document_vectors) == 0:
            return []
        
        # Compute cosine similarities
        query_vector = query_vector.reshape(1, -1)
        similarities = cosine_similarity(query_vector, self.document_vectors)[0]
        
        # Get top results above threshold
        results = []
        for i, similarity in enumerate(similarities):
            if similarity >= threshold:
                results.append((self.document_ids[i], float(similarity)))
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def remove_vector(self, document_id: str):
        """Remove vector from index"""
        if document_id in self.vectors:
            del self.vectors[document_id]
            self.needs_rebuild = True
            
            # Remove from database
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("DELETE FROM semantic_vectors WHERE document_id = ?", (document_id,))
                conn.commit()
                conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "needs_rebuild": self.needs_rebuild,
            "memory_usage_mb": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        if self.document_vectors is not None:
            vector_size = self.document_vectors.nbytes
            return vector_size / (1024 * 1024)
        return 0

class SemanticSearch:
    """Semantic search system with multiple embedding models"""
    
    def __init__(self):
        # Initialize embedding models
        self.embedding_models = {
            "tfidf": TFIDFEmbeddingModel(dimension=512),
            "bert": MockBERTEmbeddingModel(dimension=768)
        }
        
        # Initialize semantic indexes
        self.semantic_indexes = {
            "tfidf": SemanticIndex(dimension=512, db_path="tfidf_index.db"),
            "bert": SemanticIndex(dimension=768, db_path="bert_index.db")
        }
        
        # Default model
        self.default_model = "tfidf"
        
        # Model fitting status
        self.model_fitted = {model: False for model in self.embedding_models}
        
        # Statistics
        self.stats = {
            "documents_indexed": 0,
            "searches_performed": 0,
            "avg_search_time_ms": 0,
            "model_usage": defaultdict(int)
        }
    
    async def fit_models(self, corpus: List[str]):
        """Fit embedding models on corpus"""
        logger.info("Fitting semantic search models")
        
        # Fit TF-IDF model
        if "tfidf" in self.embedding_models:
            await asyncio.get_event_loop().run_in_executor(
                None, self.embedding_models["tfidf"].fit, corpus
            )
            self.model_fitted["tfidf"] = True
        
        # BERT model doesn't need fitting (mock implementation)
        self.model_fitted["bert"] = True
        
        logger.info("Semantic search models fitted")
    
    async def index_document(self, document_id: str, content: str, title: str = "", model_type: str = None):
        """Index document with semantic embeddings"""
        if model_type is None:
            model_type = self.default_model
        
        if model_type not in self.embedding_models:
            raise ValueError(f"Unknown model type: {model_type}")
        
        if not self.model_fitted[model_type]:
            logger.warning(f"Model {model_type} not fitted, skipping indexing")
            return
        
        # Combine title and content
        text = f"{title} {content}".strip()
        
        # Generate embedding
        model = self.embedding_models[model_type]
        embedding = await asyncio.get_event_loop().run_in_executor(
            None, model.encode, text
        )
        
        # Create semantic vector
        semantic_vector = SemanticVector(
            document_id=document_id,
            vector=embedding,
            vector_type=model_type
        )
        
        # Add to index
        self.semantic_indexes[model_type].add_vector(semantic_vector)
        
        self.stats["documents_indexed"] += 1
        logger.debug(f"Indexed document {document_id} with {model_type}")
    
    async def search(self, query, limit: int = 50, model_type: str = None, threshold: float = 0.1) -> List[Tuple[str, float]]:
        """Perform semantic search"""
        start_time = time.time()
        
        if model_type is None:
            model_type = self.default_model
        
        if model_type not in self.embedding_models:
            raise ValueError(f"Unknown model type: {model_type}")
        
        if not self.model_fitted[model_type]:
            logger.warning(f"Model {model_type} not fitted, returning empty results")
            return []
        
        try:
            # Handle different query types
            if hasattr(query, 'query'):
                query_text = query.query
            else:
                query_text = str(query)
            
            # Generate query embedding
            model = self.embedding_models[model_type]
            query_embedding = await asyncio.get_event_loop().run_in_executor(
                None, model.encode, query_text
            )
            
            # Search similar vectors
            index = self.semantic_indexes[model_type]
            results = index.search_similar(query_embedding, limit, threshold)
            
            # Update statistics
            search_time = (time.time() - start_time) * 1000
            self.stats["searches_performed"] += 1
            self.stats["model_usage"][model_type] += 1
            
            # Update average search time
            current_avg = self.stats["avg_search_time_ms"]
            total_searches = self.stats["searches_performed"]
            self.stats["avg_search_time_ms"] = ((current_avg * (total_searches - 1)) + search_time) / total_searches
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return []
    
    async def multi_model_search(self, query, limit: int = 50, weights: Dict[str, float] = None) -> List[Tuple[str, float]]:
        """Search using multiple models and combine results"""
        if weights is None:
            weights = {"tfidf": 0.6, "bert": 0.4}
        
        all_results = {}
        
        # Search with each model
        for model_type, weight in weights.items():
            if model_type in self.embedding_models and self.model_fitted[model_type]:
                results = await self.search(query, limit * 2, model_type)  # Get more results for combination
                
                for doc_id, score in results:
                    if doc_id not in all_results:
                        all_results[doc_id] = 0
                    all_results[doc_id] += score * weight
        
        # Sort combined results
        combined_results = sorted(all_results.items(), key=lambda x: x[1], reverse=True)
        return combined_results[:limit]
    
    def remove_document(self, document_id: str):
        """Remove document from all semantic indexes"""
        for index in self.semantic_indexes.values():
            index.remove_vector(document_id)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about embedding models"""
        return {
            model_name: {
                "name": model.name,
                "dimension": model.dimension,
                "fitted": self.model_fitted[model_name],
                "index_stats": self.semantic_indexes[model_name].get_stats()
            }
            for model_name, model in self.embedding_models.items()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get semantic search statistics"""
        return {
            **self.stats,
            "models": self.get_model_info()
        }
    
    async def find_similar_documents(self, document_id: str, limit: int = 10, model_type: str = None) -> List[Tuple[str, float]]:
        """Find documents similar to a given document"""
        if model_type is None:
            model_type = self.default_model
        
        # Get document vector
        index = self.semantic_indexes[model_type]
        if document_id not in index.vectors:
            return []
        
        document_vector = index.vectors[document_id].vector
        
        # Search for similar vectors
        results = index.search_similar(document_vector, limit + 1)  # +1 to exclude self
        
        # Remove the document itself from results
        results = [(doc_id, score) for doc_id, score in results if doc_id != document_id]
        
        return results[:limit]
    
    async def get_document_clusters(self, model_type: str = None, n_clusters: int = 5) -> Dict[int, List[str]]:
        """Cluster documents based on semantic similarity"""
        if model_type is None:
            model_type = self.default_model
        
        index = self.semantic_indexes[model_type]
        index._rebuild_index()
        
        if index.document_vectors is None or len(index.document_vectors) < n_clusters:
            return {}
        
        try:
            from sklearn.cluster import KMeans
            
            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = await asyncio.get_event_loop().run_in_executor(
                None, kmeans.fit_predict, index.document_vectors
            )
            
            # Group documents by cluster
            clusters = defaultdict(list)
            for doc_id, cluster_label in zip(index.document_ids, cluster_labels):
                clusters[int(cluster_label)].append(doc_id)
            
            return dict(clusters)
            
        except ImportError:
            logger.warning("scikit-learn not available for clustering")
            return {}
        except Exception as e:
            logger.error(f"Clustering error: {e}")
            return {}