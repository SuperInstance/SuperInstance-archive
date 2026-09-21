#!/usr/bin/env python3
"""
Vector Database Integration for Semantic Search
Handles document embeddings, vector storage, and semantic search
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
import uuid
from datetime import datetime
import numpy as np

# Vector databases
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

# Embeddings
from sentence_transformers import SentenceTransformer
try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

# Text processing
import spacy
from nltk.tokenize import sent_tokenize, word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd

# Utilities
import warnings
warnings.filterwarnings('ignore')

class VectorSearch:
    """Vector database integration for semantic document search"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.output_dir = self.config.get('output_dir', './output/vectors')
        self.vector_db_type = self.config.get('vector_db_type', 'chroma')  # 'chroma', 'faiss', 'memory'
        self.embedding_model_name = self.config.get('embedding_model', 'all-MiniLM-L6-v2')
        self.chunk_size = self.config.get('chunk_size', 500)
        self.chunk_overlap = self.config.get('chunk_overlap', 50)
        
        # Vector database instances
        self.chroma_client = None
        self.chroma_collection = None
        self.faiss_index = None
        self.memory_vectors = {}
        
        # Embedding models
        self.sentence_transformer = None
        self.custom_model = None
        self.custom_tokenizer = None
        
        # Text processing
        self.spacy_model = None
        
        # Setup directories
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self._initialize_models()
        self._initialize_vector_db()
    
    def _initialize_models(self):
        """Initialize embedding models"""
        
        try:
            # Initialize sentence transformer
            try:
                self.sentence_transformer = SentenceTransformer(self.embedding_model_name)
                self.logger.info(f"Sentence transformer loaded: {self.embedding_model_name}")
            except Exception as e:
                self.logger.warning(f"Could not load sentence transformer: {str(e)}")
                self.sentence_transformer = None
            
            # Initialize custom transformer model if needed
            if HAS_TRANSFORMERS and not self.sentence_transformer:
                try:
                    model_name = "sentence-transformers/all-MiniLM-L6-v2"
                    self.custom_tokenizer = AutoTokenizer.from_pretrained(model_name)
                    self.custom_model = AutoModel.from_pretrained(model_name)
                    self.logger.info(f"Custom transformer model loaded: {model_name}")
                except Exception as e:
                    self.logger.warning(f"Could not load custom transformer: {str(e)}")
            
            # Initialize spaCy for text processing
            try:
                self.spacy_model = spacy.load("en_core_web_sm")
            except OSError:
                self.logger.warning("spaCy English model not found")
                self.spacy_model = None
                
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
    
    def _initialize_vector_db(self):
        """Initialize vector database"""
        
        try:
            if self.vector_db_type == 'chroma' and HAS_CHROMA:
                self._initialize_chroma()
            elif self.vector_db_type == 'faiss' and HAS_FAISS:
                self._initialize_faiss()
            else:
                self.vector_db_type = 'memory'
                self._initialize_memory_db()
                
        except Exception as e:
            self.logger.error(f"Vector database initialization failed: {str(e)}")
            # Fallback to memory
            self.vector_db_type = 'memory'
            self._initialize_memory_db()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB"""
        
        try:
            # Create Chroma client
            chroma_dir = os.path.join(self.output_dir, 'chroma_db')
            os.makedirs(chroma_dir, exist_ok=True)
            
            self.chroma_client = chromadb.PersistentClient(path=chroma_dir)
            
            # Create or get collection
            collection_name = "document_embeddings"
            try:
                self.chroma_collection = self.chroma_client.get_collection(collection_name)
                self.logger.info(f"Loaded existing ChromaDB collection: {collection_name}")
            except:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                self.logger.info(f"Created new ChromaDB collection: {collection_name}")
                
        except Exception as e:
            self.logger.error(f"ChromaDB initialization failed: {str(e)}")
            raise
    
    def _initialize_faiss(self):
        """Initialize FAISS index"""
        
        try:
            # FAISS will be initialized when we know the embedding dimension
            self.faiss_index = None
            self.faiss_metadata = {}
            self.logger.info("FAISS will be initialized on first embedding")
            
        except Exception as e:
            self.logger.error(f"FAISS initialization failed: {str(e)}")
            raise
    
    def _initialize_memory_db(self):
        """Initialize in-memory vector store"""
        
        try:
            self.memory_vectors = {
                'embeddings': [],
                'metadata': [],
                'ids': []
            }
            self.logger.info("Memory vector store initialized")
            
        except Exception as e:
            self.logger.error(f"Memory DB initialization failed: {str(e)}")
            raise
    
    def create_embeddings(self, text: str, metadata: Dict = None) -> Dict:
        """
        Create embeddings for document text
        """
        session_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        try:
            self.logger.info(f"Creating embeddings for document (session: {session_id})")
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'original_text_length': len(text),
                'metadata': metadata
            }
            
            # Split text into chunks
            chunks = self._chunk_text(text)
            result['chunk_count'] = len(chunks)
            
            # Create embeddings for each chunk
            chunk_embeddings = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = self._create_single_embedding(chunk['text'])
                    
                    chunk_data = {
                        'chunk_id': f"{session_id}_chunk_{i}",
                        'text': chunk['text'],
                        'start_pos': chunk['start_pos'],
                        'end_pos': chunk['end_pos'],
                        'embedding': embedding,
                        'metadata': {
                            **metadata,
                            'chunk_index': i,
                            'session_id': session_id
                        }
                    }
                    
                    chunk_embeddings.append(chunk_data)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to create embedding for chunk {i}: {str(e)}")
            
            result['embeddings'] = chunk_embeddings
            
            # Store embeddings in vector database
            if chunk_embeddings:
                storage_result = self._store_embeddings(chunk_embeddings)
                result['storage'] = storage_result
            
            # Save results
            self._save_embedding_results(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Embedding creation failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    def _chunk_text(self, text: str) -> List[Dict]:
        """Split text into chunks for embedding"""
        
        chunks = []
        
        # Method 1: Sentence-based chunking (preferred)
        if self.spacy_model:
            chunks = self._chunk_by_sentences(text)
        else:
            # Fallback: Simple word-based chunking
            chunks = self._chunk_by_words(text)
        
        return chunks
    
    def _chunk_by_sentences(self, text: str) -> List[Dict]:
        """Chunk text by sentences using spaCy"""
        
        try:
            doc = self.spacy_model(text)
            sentences = [sent.text.strip() for sent in doc.sents]
            
            chunks = []
            current_chunk = ""
            current_start = 0
            
            for sentence in sentences:
                # Check if adding this sentence would exceed chunk size
                if len(current_chunk + " " + sentence) > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        'text': current_chunk.strip(),
                        'start_pos': current_start,
                        'end_pos': current_start + len(current_chunk)
                    })
                    
                    # Start new chunk with overlap
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    current_start = current_start + len(current_chunk) - len(overlap_text) - len(sentence) - 1
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
                        current_start = text.find(sentence)
            
            # Add final chunk
            if current_chunk.strip():
                chunks.append({
                    'text': current_chunk.strip(),
                    'start_pos': current_start,
                    'end_pos': current_start + len(current_chunk)
                })
            
            return chunks
            
        except Exception as e:
            self.logger.warning(f"Sentence-based chunking failed: {str(e)}")
            return self._chunk_by_words(text)
    
    def _chunk_by_words(self, text: str) -> List[Dict]:
        """Chunk text by words (fallback method)"""
        
        words = text.split()
        chunks = []
        
        words_per_chunk = self.chunk_size // 5  # Estimate ~5 chars per word
        overlap_words = self.chunk_overlap // 5
        
        for i in range(0, len(words), words_per_chunk - overlap_words):
            chunk_words = words[i:i + words_per_chunk]
            chunk_text = " ".join(chunk_words)
            
            start_pos = text.find(chunk_words[0]) if chunk_words else 0
            end_pos = start_pos + len(chunk_text)
            
            chunks.append({
                'text': chunk_text,
                'start_pos': start_pos,
                'end_pos': min(end_pos, len(text))
            })
        
        return chunks
    
    def _create_single_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text chunk"""
        
        try:
            if self.sentence_transformer:
                # Use sentence transformer
                embedding = self.sentence_transformer.encode(text, convert_to_tensor=False)
                return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
            
            elif self.custom_model and self.custom_tokenizer:
                # Use custom transformer model
                inputs = self.custom_tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
                
                with torch.no_grad():
                    outputs = self.custom_model(**inputs)
                    # Use mean pooling
                    embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                
                return embedding.tolist()
            
            else:
                # Fallback: TF-IDF (not ideal but better than nothing)
                return self._create_tfidf_embedding(text)
                
        except Exception as e:
            self.logger.warning(f"Embedding creation failed, using fallback: {str(e)}")
            return self._create_tfidf_embedding(text)
    
    def _create_tfidf_embedding(self, text: str) -> List[float]:
        """Create TF-IDF based embedding (fallback)"""
        
        try:
            # Simple TF-IDF embedding
            vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
            
            # We need a corpus, so we'll split the text into sentences
            sentences = sent_tokenize(text) if text else [text]
            if len(sentences) < 2:
                sentences = [text, ""]  # Add dummy sentence
            
            tfidf_matrix = vectorizer.fit_transform(sentences)
            embedding = tfidf_matrix[0].toarray().flatten()
            
            # Pad or truncate to standard size
            target_size = 384
            if len(embedding) < target_size:
                embedding = np.pad(embedding, (0, target_size - len(embedding)))
            else:
                embedding = embedding[:target_size]
            
            return embedding.tolist()
            
        except Exception as e:
            self.logger.warning(f"TF-IDF embedding failed: {str(e)}")
            # Return zero vector as last resort
            return [0.0] * 384
    
    def _store_embeddings(self, chunk_embeddings: List[Dict]) -> Dict:
        """Store embeddings in vector database"""
        
        try:
            if self.vector_db_type == 'chroma':
                return self._store_in_chroma(chunk_embeddings)
            elif self.vector_db_type == 'faiss':
                return self._store_in_faiss(chunk_embeddings)
            else:
                return self._store_in_memory(chunk_embeddings)
                
        except Exception as e:
            self.logger.error(f"Embedding storage failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _store_in_chroma(self, chunk_embeddings: List[Dict]) -> Dict:
        """Store embeddings in ChromaDB"""
        
        try:
            ids = [chunk['chunk_id'] for chunk in chunk_embeddings]
            embeddings = [chunk['embedding'] for chunk in chunk_embeddings]
            documents = [chunk['text'] for chunk in chunk_embeddings]
            metadatas = [chunk['metadata'] for chunk in chunk_embeddings]
            
            self.chroma_collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            return {
                'success': True,
                'method': 'chroma',
                'stored_count': len(ids)
            }
            
        except Exception as e:
            self.logger.error(f"ChromaDB storage failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _store_in_faiss(self, chunk_embeddings: List[Dict]) -> Dict:
        """Store embeddings in FAISS index"""
        
        try:
            embeddings = np.array([chunk['embedding'] for chunk in chunk_embeddings]).astype('float32')
            
            # Initialize FAISS index if not exists
            if self.faiss_index is None:
                dimension = embeddings.shape[1]
                self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
                self.faiss_metadata = {}
            
            # Add embeddings to index
            start_id = self.faiss_index.ntotal
            self.faiss_index.add(embeddings)
            
            # Store metadata separately
            for i, chunk in enumerate(chunk_embeddings):
                self.faiss_metadata[start_id + i] = {
                    'chunk_id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'metadata': chunk['metadata']
                }
            
            return {
                'success': True,
                'method': 'faiss',
                'stored_count': len(chunk_embeddings),
                'total_vectors': self.faiss_index.ntotal
            }
            
        except Exception as e:
            self.logger.error(f"FAISS storage failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _store_in_memory(self, chunk_embeddings: List[Dict]) -> Dict:
        """Store embeddings in memory"""
        
        try:
            for chunk in chunk_embeddings:
                self.memory_vectors['embeddings'].append(chunk['embedding'])
                self.memory_vectors['metadata'].append({
                    'chunk_id': chunk['chunk_id'],
                    'text': chunk['text'],
                    'metadata': chunk['metadata']
                })
                self.memory_vectors['ids'].append(chunk['chunk_id'])
            
            return {
                'success': True,
                'method': 'memory',
                'stored_count': len(chunk_embeddings),
                'total_vectors': len(self.memory_vectors['embeddings'])
            }
            
        except Exception as e:
            self.logger.error(f"Memory storage failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def semantic_search(self, query: str, top_k: int = 10, filters: Dict = None) -> Dict:
        """
        Perform semantic search using vector similarity
        """
        session_id = str(uuid.uuid4())
        filters = filters or {}
        
        try:
            self.logger.info(f"Performing semantic search (session: {session_id})")
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'query': query,
                'top_k': top_k,
                'filters': filters,
                'results': []
            }
            
            # Create embedding for query
            query_embedding = self._create_single_embedding(query)
            
            # Search in vector database
            if self.vector_db_type == 'chroma':
                search_results = await self._search_chroma(query_embedding, top_k, filters)
            elif self.vector_db_type == 'faiss':
                search_results = await self._search_faiss(query_embedding, top_k, filters)
            else:
                search_results = await self._search_memory(query_embedding, top_k, filters)
            
            result['results'] = search_results
            result['result_count'] = len(search_results)
            
            # Add search analytics
            result['analytics'] = self._analyze_search_results(search_results, query)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Semantic search failed: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'success': False
            }
    
    async def _search_chroma(self, query_embedding: List[float], top_k: int, filters: Dict) -> List[Dict]:
        """Search using ChromaDB"""
        
        try:
            # Prepare filter conditions
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    where_clause[key] = value
            
            # Perform search
            results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause if where_clause else None
            )
            
            # Format results
            search_results = []
            for i in range(len(results['ids'][0])):
                search_results.append({
                    'id': results['ids'][0][i],
                    'text': results['documents'][0][i],
                    'distance': results['distances'][0][i],
                    'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                    'metadata': results['metadatas'][0][i]
                })
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"ChromaDB search failed: {str(e)}")
            return []
    
    async def _search_faiss(self, query_embedding: List[float], top_k: int, filters: Dict) -> List[Dict]:
        """Search using FAISS"""
        
        try:
            if self.faiss_index is None or self.faiss_index.ntotal == 0:
                return []
            
            # Prepare query
            query_vector = np.array([query_embedding]).astype('float32')
            
            # Search
            scores, indices = self.faiss_index.search(query_vector, min(top_k, self.faiss_index.ntotal))
            
            # Format results
            search_results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx in self.faiss_metadata:
                    metadata_entry = self.faiss_metadata[idx]
                    
                    # Apply filters if specified
                    if self._matches_filters(metadata_entry['metadata'], filters):
                        search_results.append({
                            'id': metadata_entry['chunk_id'],
                            'text': metadata_entry['text'],
                            'distance': 1 - score,  # FAISS returns similarity scores
                            'score': score,
                            'metadata': metadata_entry['metadata']
                        })
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"FAISS search failed: {str(e)}")
            return []
    
    async def _search_memory(self, query_embedding: List[float], top_k: int, filters: Dict) -> List[Dict]:
        """Search using in-memory vectors"""
        
        try:
            if not self.memory_vectors['embeddings']:
                return []
            
            # Calculate similarities
            query_vector = np.array(query_embedding).reshape(1, -1)
            stored_vectors = np.array(self.memory_vectors['embeddings'])
            
            similarities = cosine_similarity(query_vector, stored_vectors)[0]
            
            # Get top k results
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            # Format results
            search_results = []
            for idx in top_indices:
                metadata_entry = self.memory_vectors['metadata'][idx]
                
                # Apply filters if specified
                if self._matches_filters(metadata_entry['metadata'], filters):
                    search_results.append({
                        'id': metadata_entry['chunk_id'],
                        'text': metadata_entry['text'],
                        'distance': 1 - similarities[idx],
                        'score': similarities[idx],
                        'metadata': metadata_entry['metadata']
                    })
            
            return search_results
            
        except Exception as e:
            self.logger.error(f"Memory search failed: {str(e)}")
            return []
    
    def _matches_filters(self, metadata: Dict, filters: Dict) -> bool:
        """Check if metadata matches filter conditions"""
        
        if not filters:
            return True
        
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        
        return True
    
    def _analyze_search_results(self, results: List[Dict], query: str) -> Dict:
        """Analyze search results for insights"""
        
        analysis = {
            'score_distribution': {},
            'metadata_analysis': {},
            'query_coverage': 0
        }
        
        if not results:
            return analysis
        
        # Score distribution
        scores = [result['score'] for result in results]
        analysis['score_distribution'] = {
            'min_score': min(scores),
            'max_score': max(scores),
            'avg_score': sum(scores) / len(scores),
            'high_relevance_count': len([s for s in scores if s > 0.8]),
            'medium_relevance_count': len([s for s in scores if 0.5 < s <= 0.8]),
            'low_relevance_count': len([s for s in scores if s <= 0.5])
        }
        
        # Metadata analysis
        session_ids = [result['metadata'].get('session_id') for result in results if result.get('metadata')]
        unique_sessions = set(filter(None, session_ids))
        
        analysis['metadata_analysis'] = {
            'unique_documents': len(unique_sessions),
            'results_per_document': len(results) / len(unique_sessions) if unique_sessions else 0
        }
        
        # Query coverage (simple keyword overlap)
        query_words = set(query.lower().split())
        coverage_scores = []
        
        for result in results:
            result_words = set(result['text'].lower().split())
            overlap = len(query_words.intersection(result_words))
            coverage = overlap / len(query_words) if query_words else 0
            coverage_scores.append(coverage)
        
        analysis['query_coverage'] = sum(coverage_scores) / len(coverage_scores) if coverage_scores else 0
        
        return analysis
    
    def create_document_clusters(self, session_ids: List[str] = None, cluster_count: int = 5) -> Dict:
        """
        Create clusters of similar documents based on embeddings
        """
        cluster_session_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Creating document clusters (session: {cluster_session_id})")
            
            # Get embeddings from vector database
            embeddings_data = self._get_embeddings_for_clustering(session_ids)
            
            if not embeddings_data:
                return {
                    'session_id': cluster_session_id,
                    'error': 'No embeddings found for clustering',
                    'success': False
                }
            
            # Perform clustering
            from sklearn.cluster import KMeans
            from sklearn.decomposition import PCA
            
            embeddings_matrix = np.array([item['embedding'] for item in embeddings_data])
            
            # K-means clustering
            kmeans = KMeans(n_clusters=min(cluster_count, len(embeddings_data)), random_state=42)
            cluster_labels = kmeans.fit_predict(embeddings_matrix)
            
            # Reduce dimensionality for visualization
            pca = PCA(n_components=2)
            embeddings_2d = pca.fit_transform(embeddings_matrix)
            
            # Organize results by cluster
            clusters = {}
            for i, (item, label, coord_2d) in enumerate(zip(embeddings_data, cluster_labels, embeddings_2d)):
                if label not in clusters:
                    clusters[label] = {
                        'documents': [],
                        'centroid': kmeans.cluster_centers_[label].tolist(),
                        'size': 0
                    }
                
                clusters[label]['documents'].append({
                    'chunk_id': item['chunk_id'],
                    'text_preview': item['text'][:200] + "..." if len(item['text']) > 200 else item['text'],
                    'metadata': item['metadata'],
                    'coordinates_2d': coord_2d.tolist()
                })
                clusters[label]['size'] += 1
            
            # Generate cluster summaries
            for cluster_id, cluster_data in clusters.items():
                cluster_texts = [doc['text_preview'] for doc in cluster_data['documents']]
                
                # Simple keyword extraction for cluster summary
                all_text = ' '.join(cluster_texts).lower()
                words = all_text.split()
                word_freq = {}
                
                for word in words:
                    if len(word) > 3:  # Filter short words
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get top keywords
                top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
                cluster_data['keywords'] = [word for word, freq in top_keywords]
                cluster_data['summary'] = f"Cluster with {len(cluster_data['documents'])} documents focusing on: {', '.join(cluster_data['keywords'][:5])}"
            
            result = {
                'session_id': cluster_session_id,
                'timestamp': datetime.now().isoformat(),
                'cluster_count': len(clusters),
                'total_documents': len(embeddings_data),
                'clusters': clusters,
                'clustering_method': 'kmeans',
                'dimensionality_reduction': 'pca'
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Document clustering failed: {str(e)}")
            return {
                'session_id': cluster_session_id,
                'error': str(e),
                'success': False
            }
    
    def _get_embeddings_for_clustering(self, session_ids: List[str] = None) -> List[Dict]:
        """Get embeddings from vector database for clustering"""
        
        try:
            if self.vector_db_type == 'chroma':
                return self._get_chroma_embeddings_for_clustering(session_ids)
            elif self.vector_db_type == 'faiss':
                return self._get_faiss_embeddings_for_clustering(session_ids)
            else:
                return self._get_memory_embeddings_for_clustering(session_ids)
                
        except Exception as e:
            self.logger.error(f"Failed to get embeddings for clustering: {str(e)}")
            return []
    
    def _get_chroma_embeddings_for_clustering(self, session_ids: List[str] = None) -> List[Dict]:
        """Get embeddings from ChromaDB for clustering"""
        
        try:
            # Query all or filtered embeddings
            where_clause = {}
            if session_ids:
                where_clause['session_id'] = {'$in': session_ids}
            
            results = self.chroma_collection.get(
                where=where_clause if where_clause else None,
                include=['embeddings', 'documents', 'metadatas']
            )
            
            embeddings_data = []
            for i in range(len(results['ids'])):
                embeddings_data.append({
                    'chunk_id': results['ids'][i],
                    'text': results['documents'][i],
                    'embedding': results['embeddings'][i],
                    'metadata': results['metadatas'][i]
                })
            
            return embeddings_data
            
        except Exception as e:
            self.logger.error(f"ChromaDB embeddings retrieval failed: {str(e)}")
            return []
    
    def _get_faiss_embeddings_for_clustering(self, session_ids: List[str] = None) -> List[Dict]:
        """Get embeddings from FAISS for clustering"""
        
        try:
            if self.faiss_index is None:
                return []
            
            embeddings_data = []
            
            # Get all vectors from FAISS
            all_vectors = self.faiss_index.reconstruct_n(0, self.faiss_index.ntotal)
            
            for idx in range(self.faiss_index.ntotal):
                if idx in self.faiss_metadata:
                    metadata_entry = self.faiss_metadata[idx]
                    
                    # Filter by session IDs if specified
                    if session_ids and metadata_entry['metadata'].get('session_id') not in session_ids:
                        continue
                    
                    embeddings_data.append({
                        'chunk_id': metadata_entry['chunk_id'],
                        'text': metadata_entry['text'],
                        'embedding': all_vectors[idx].tolist(),
                        'metadata': metadata_entry['metadata']
                    })
            
            return embeddings_data
            
        except Exception as e:
            self.logger.error(f"FAISS embeddings retrieval failed: {str(e)}")
            return []
    
    def _get_memory_embeddings_for_clustering(self, session_ids: List[str] = None) -> List[Dict]:
        """Get embeddings from memory for clustering"""
        
        try:
            embeddings_data = []
            
            for i, (embedding, metadata) in enumerate(zip(self.memory_vectors['embeddings'], self.memory_vectors['metadata'])):
                # Filter by session IDs if specified
                if session_ids and metadata['metadata'].get('session_id') not in session_ids:
                    continue
                
                embeddings_data.append({
                    'chunk_id': metadata['chunk_id'],
                    'text': metadata['text'],
                    'embedding': embedding,
                    'metadata': metadata['metadata']
                })
            
            return embeddings_data
            
        except Exception as e:
            self.logger.error(f"Memory embeddings retrieval failed: {str(e)}")
            return []
    
    def get_similar_documents(self, document_session_id: str, top_k: int = 5) -> Dict:
        """
        Find documents similar to a given document
        """
        similarity_session_id = str(uuid.uuid4())
        
        try:
            self.logger.info(f"Finding similar documents for {document_session_id} (session: {similarity_session_id})")
            
            # Get embeddings for the target document
            target_embeddings = self._get_document_embeddings(document_session_id)
            
            if not target_embeddings:
                return {
                    'session_id': similarity_session_id,
                    'error': 'Target document not found',
                    'success': False
                }
            
            # Calculate average embedding for the document
            avg_embedding = np.mean([emb['embedding'] for emb in target_embeddings], axis=0)
            
            # Search for similar documents
            search_result = await self.semantic_search(
                "", top_k=top_k * 5,  # Get more results to filter out self-matches
                filters={'session_id': {'$ne': document_session_id}} if self.vector_db_type == 'chroma' else {}
            )
            
            # Filter out self-matches for other vector DBs
            if self.vector_db_type != 'chroma':
                search_result['results'] = [
                    result for result in search_result['results'] 
                    if result['metadata'].get('session_id') != document_session_id
                ]
            
            # Group by document (session_id) and aggregate scores
            document_similarities = {}
            for result in search_result['results'][:top_k * 2]:
                session_id = result['metadata'].get('session_id')
                if session_id and session_id != document_session_id:
                    if session_id not in document_similarities:
                        document_similarities[session_id] = {
                            'scores': [],
                            'chunks': [],
                            'metadata': result['metadata']
                        }
                    
                    document_similarities[session_id]['scores'].append(result['score'])
                    document_similarities[session_id]['chunks'].append({
                        'text': result['text'],
                        'score': result['score']
                    })
            
            # Calculate document-level similarity scores
            similar_docs = []
            for session_id, data in document_similarities.items():
                avg_score = sum(data['scores']) / len(data['scores'])
                max_score = max(data['scores'])
                
                similar_docs.append({
                    'document_session_id': session_id,
                    'average_similarity': avg_score,
                    'max_similarity': max_score,
                    'matching_chunks': len(data['chunks']),
                    'best_chunk': max(data['chunks'], key=lambda x: x['score']),
                    'metadata': data['metadata']
                })
            
            # Sort by average similarity
            similar_docs.sort(key=lambda x: x['average_similarity'], reverse=True)
            
            result = {
                'session_id': similarity_session_id,
                'timestamp': datetime.now().isoformat(),
                'target_document_id': document_session_id,
                'similar_documents': similar_docs[:top_k],
                'similarity_count': len(similar_docs)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Similar document search failed: {str(e)}")
            return {
                'session_id': similarity_session_id,
                'error': str(e),
                'success': False
            }
    
    def _get_document_embeddings(self, session_id: str) -> List[Dict]:
        """Get all embeddings for a specific document"""
        
        try:
            if self.vector_db_type == 'chroma':
                results = self.chroma_collection.get(
                    where={'session_id': session_id},
                    include=['embeddings', 'documents', 'metadatas']
                )
                
                embeddings_data = []
                for i in range(len(results['ids'])):
                    embeddings_data.append({
                        'chunk_id': results['ids'][i],
                        'text': results['documents'][i],
                        'embedding': results['embeddings'][i],
                        'metadata': results['metadatas'][i]
                    })
                
                return embeddings_data
                
            elif self.vector_db_type == 'faiss':
                embeddings_data = []
                
                for idx, metadata_entry in self.faiss_metadata.items():
                    if metadata_entry['metadata'].get('session_id') == session_id:
                        vector = self.faiss_index.reconstruct(idx)
                        embeddings_data.append({
                            'chunk_id': metadata_entry['chunk_id'],
                            'text': metadata_entry['text'],
                            'embedding': vector.tolist(),
                            'metadata': metadata_entry['metadata']
                        })
                
                return embeddings_data
                
            else:  # memory
                embeddings_data = []
                
                for i, metadata in enumerate(self.memory_vectors['metadata']):
                    if metadata['metadata'].get('session_id') == session_id:
                        embeddings_data.append({
                            'chunk_id': metadata['chunk_id'],
                            'text': metadata['text'],
                            'embedding': self.memory_vectors['embeddings'][i],
                            'metadata': metadata['metadata']
                        })
                
                return embeddings_data
                
        except Exception as e:
            self.logger.error(f"Failed to get document embeddings: {str(e)}")
            return []
    
    def _save_embedding_results(self, results: Dict):
        """Save embedding results to file"""
        
        try:
            # Don't save the actual embeddings to JSON (too large)
            save_results = {
                'session_id': results['session_id'],
                'timestamp': results['timestamp'],
                'original_text_length': results['original_text_length'],
                'chunk_count': results['chunk_count'],
                'metadata': results['metadata'],
                'storage': results.get('storage', {})
            }
            
            output_file = os.path.join(self.output_dir, f"embeddings_{results['session_id']}.json")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(save_results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Embedding results saved to {output_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save embedding results: {str(e)}")
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the vector database"""
        
        try:
            stats = {
                'database_type': self.vector_db_type,
                'embedding_model': self.embedding_model_name,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.vector_db_type == 'chroma':
                collection_info = self.chroma_collection.count()
                stats['total_vectors'] = collection_info
                
            elif self.vector_db_type == 'faiss':
                stats['total_vectors'] = self.faiss_index.ntotal if self.faiss_index else 0
                stats['index_type'] = 'IndexFlatIP'
                
            else:  # memory
                stats['total_vectors'] = len(self.memory_vectors['embeddings'])
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get database stats: {str(e)}")
            return {'error': str(e)}

def main():
    """Command line interface for vector search"""
    import argparse
    import asyncio
    
    parser = argparse.ArgumentParser(description='Vector search operations')
    parser.add_argument('action', choices=['embed', 'search', 'cluster', 'similar'], help='Action to perform')
    parser.add_argument('input', help='Text/query or file path')
    parser.add_argument('--output-dir', default='./output/vectors', help='Output directory')
    parser.add_argument('--vector-db', choices=['chroma', 'faiss', 'memory'], default='chroma', help='Vector database type')
    parser.add_argument('--embedding-model', default='all-MiniLM-L6-v2', help='Embedding model name')
    parser.add_argument('--top-k', type=int, default=10, help='Number of results to return')
    parser.add_argument('--file', action='store_true', help='Input is a file path')
    
    args = parser.parse_args()
    
    # Configure vector search
    config = {
        'output_dir': args.output_dir,
        'vector_db_type': args.vector_db,
        'embedding_model': args.embedding_model
    }
    
    # Get text
    if args.file:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = args.input
    
    # Process
    vector_search = VectorSearch(config)
    
    async def run_processing():
        if args.action == 'embed':
            result = vector_search.create_embeddings(text, metadata={'source': 'cli'})
            
            if 'embeddings' in result:
                print(f"✓ Embeddings created")
                print(f"  Session ID: {result['session_id']}")
                print(f"  Chunks: {result['chunk_count']}")
                print(f"  Storage: {result.get('storage', {}).get('method', 'unknown')}")
            else:
                print(f"✗ Embedding creation failed: {result.get('error', 'Unknown error')}")
        
        elif args.action == 'search':
            result = await vector_search.semantic_search(text, top_k=args.top_k)
            
            if 'results' in result:
                print(f"✓ Semantic search completed")
                print(f"  Query: {result['query']}")
                print(f"  Results: {result['result_count']}")
                print(f"  Session ID: {result['session_id']}")
                
                for i, res in enumerate(result['results'][:5]):
                    print(f"\n  Result {i+1}:")
                    print(f"    Score: {res['score']:.3f}")
                    print(f"    Text: {res['text'][:100]}...")
            else:
                print(f"✗ Search failed: {result.get('error', 'Unknown error')}")
        
        elif args.action == 'cluster':
            result = vector_search.create_document_clusters(cluster_count=5)
            
            if 'clusters' in result:
                print(f"✓ Document clustering completed")
                print(f"  Clusters: {result['cluster_count']}")
                print(f"  Total documents: {result['total_documents']}")
                print(f"  Session ID: {result['session_id']}")
                
                for cluster_id, cluster_data in result['clusters'].items():
                    print(f"\n  Cluster {cluster_id}:")
                    print(f"    Size: {cluster_data['size']}")
                    print(f"    Keywords: {', '.join(cluster_data['keywords'][:5])}")
            else:
                print(f"✗ Clustering failed: {result.get('error', 'Unknown error')}")
        
        elif args.action == 'similar':
            # For similar documents, treat input as session ID
            result = vector_search.get_similar_documents(text, top_k=args.top_k)
            
            if 'similar_documents' in result:
                print(f"✓ Similar documents found")
                print(f"  Target: {result['target_document_id']}")
                print(f"  Similar docs: {result['similarity_count']}")
                print(f"  Session ID: {result['session_id']}")
                
                for i, doc in enumerate(result['similar_documents'][:3]):
                    print(f"\n  Similar Document {i+1}:")
                    print(f"    ID: {doc['document_session_id']}")
                    print(f"    Similarity: {doc['average_similarity']:.3f}")
                    print(f"    Matching chunks: {doc['matching_chunks']}")
            else:
                print(f"✗ Similar document search failed: {result.get('error', 'Unknown error')}")
    
    asyncio.run(run_processing())

if __name__ == '__main__':
    main()