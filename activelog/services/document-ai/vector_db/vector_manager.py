"""
Vector database manager for semantic search
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json

# Embedding libraries
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModel
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Vector database libraries
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    import pinecone
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False

try:
    import weaviate
    WEAVIATE_AVAILABLE = True
except ImportError:
    WEAVIATE_AVAILABLE = False

from ..core.config import settings
from ..core.database import DatabaseManager
from ..models.document_models import DocumentEmbedding, SemanticSearchResult

vector_logger = logging.getLogger('vector_db')

class VectorDatabaseManager:
    """Manager for vector database operations and semantic search"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Vector database clients
        self.chroma_client = None
        self.pinecone_client = None
        self.weaviate_client = None
        
        # Embedding models
        self.embedding_model = None
        self.tokenizer = None
        
        # Configuration
        self.provider = settings.vector_db.provider
        self.embedding_dimension = settings.ai_models.embedding_dimension
        
        # Initialize components
        asyncio.create_task(self._initialize_components())
    
    async def _initialize_components(self):
        """Initialize vector database and embedding models"""
        try:
            # Initialize embedding model
            await self._initialize_embedding_model()
            
            # Initialize vector database
            await self._initialize_vector_db()
            
            vector_logger.info(f"Vector database manager initialized with {self.provider}")
            
        except Exception as e:
            vector_logger.error(f"Failed to initialize vector database: {str(e)}")
    
    async def _initialize_embedding_model(self):
        """Initialize text embedding model"""
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()
                self.embedding_model = await loop.run_in_executor(
                    None, 
                    SentenceTransformer,
                    settings.ai_models.embedding_model
                )
                vector_logger.info(f"Loaded embedding model: {settings.ai_models.embedding_model}")
                return
                
            except Exception as e:
                vector_logger.warning(f"Failed to load sentence-transformers model: {str(e)}")
        
        # Fallback to basic transformers
        if TRANSFORMERS_AVAILABLE:
            try:
                loop = asyncio.get_event_loop()
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                
                self.tokenizer = await loop.run_in_executor(
                    None, AutoTokenizer.from_pretrained, model_name
                )
                self.embedding_model = await loop.run_in_executor(
                    None, AutoModel.from_pretrained, model_name
                )
                vector_logger.info("Loaded fallback embedding model with transformers")
                return
                
            except Exception as e:
                vector_logger.warning(f"Failed to load transformers model: {str(e)}")
        
        vector_logger.error("No embedding model could be loaded")
    
    async def _initialize_vector_db(self):
        """Initialize vector database based on configuration"""
        
        if self.provider == "chroma" and CHROMA_AVAILABLE:
            await self._initialize_chroma()
        elif self.provider == "pinecone" and PINECONE_AVAILABLE:
            await self._initialize_pinecone()
        elif self.provider == "weaviate" and WEAVIATE_AVAILABLE:
            await self._initialize_weaviate()
        else:
            vector_logger.warning(f"Vector database provider '{self.provider}' not available, using PostgreSQL fallback")
    
    async def _initialize_chroma(self):
        """Initialize ChromaDB"""
        try:
            self.chroma_client = chromadb.Client(Settings(
                chroma_server_host=settings.vector_db.chroma_host,
                chroma_server_http_port=settings.vector_db.chroma_port,
                chroma_api_impl="rest"
            ))
            
            # Create or get collection
            try:
                self.chroma_collection = self.chroma_client.get_collection(
                    name=settings.vector_db.chroma_collection
                )
            except:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=settings.vector_db.chroma_collection,
                    metadata={"description": "Document embeddings for semantic search"}
                )
            
            vector_logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            vector_logger.error(f"ChromaDB initialization failed: {str(e)}")
            self.chroma_client = None
    
    async def _initialize_pinecone(self):
        """Initialize Pinecone"""
        try:
            if not settings.vector_db.pinecone_api_key:
                raise ValueError("Pinecone API key not configured")
            
            pinecone.init(
                api_key=settings.vector_db.pinecone_api_key,
                environment=settings.vector_db.pinecone_environment
            )
            
            # Create index if it doesn't exist
            index_name = settings.vector_db.pinecone_index
            
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=self.embedding_dimension,
                    metric="cosine"
                )
            
            self.pinecone_client = pinecone.Index(index_name)
            vector_logger.info("Pinecone initialized successfully")
            
        except Exception as e:
            vector_logger.error(f"Pinecone initialization failed: {str(e)}")
            self.pinecone_client = None
    
    async def _initialize_weaviate(self):
        """Initialize Weaviate"""
        try:
            if not settings.vector_db.weaviate_url:
                raise ValueError("Weaviate URL not configured")
            
            auth_config = None
            if settings.vector_db.weaviate_api_key:
                auth_config = weaviate.AuthApiKey(api_key=settings.vector_db.weaviate_api_key)
            
            self.weaviate_client = weaviate.Client(
                url=settings.vector_db.weaviate_url,
                auth_client_secret=auth_config
            )
            
            # Create schema if it doesn't exist
            await self._create_weaviate_schema()
            
            vector_logger.info("Weaviate initialized successfully")
            
        except Exception as e:
            vector_logger.error(f"Weaviate initialization failed: {str(e)}")
            self.weaviate_client = None
    
    async def _create_weaviate_schema(self):
        """Create Weaviate schema for documents"""
        
        schema = {
            "classes": [{
                "class": "Document",
                "description": "Document chunks for semantic search",
                "vectorizer": "none",  # We'll provide our own vectors
                "properties": [
                    {
                        "name": "job_id",
                        "dataType": ["string"],
                        "description": "Document processing job ID"
                    },
                    {
                        "name": "chunk_id",
                        "dataType": ["int"],
                        "description": "Chunk identifier within document"
                    },
                    {
                        "name": "text",
                        "dataType": ["text"],
                        "description": "Text content of the chunk"
                    },
                    {
                        "name": "page_number",
                        "dataType": ["int"],
                        "description": "Page number in source document"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["string"],
                        "description": "Additional metadata as JSON string"
                    }
                ]
            }]
        }
        
        # Check if schema already exists
        try:
            existing_schema = self.weaviate_client.schema.get()
            document_class_exists = any(
                cls.get("class") == "Document" 
                for cls in existing_schema.get("classes", [])
            )
            
            if not document_class_exists:
                self.weaviate_client.schema.create(schema)
                vector_logger.info("Created Weaviate schema")
                
        except Exception as e:
            vector_logger.warning(f"Weaviate schema creation failed: {str(e)}")
    
    async def create_document_embeddings(self, job_id: str, text_content: str,
                                       page_texts: List[Dict] = None) -> List[DocumentEmbedding]:
        """
        Create and store document embeddings for semantic search
        
        Args:
            job_id: Processing job ID
            text_content: Full document text content
            page_texts: List of page-wise text data
            
        Returns:
            List of created document embeddings
        """
        try:
            vector_logger.info(f"Creating embeddings for job {job_id}")
            
            if not self.embedding_model:
                vector_logger.warning("No embedding model available")
                return []
            
            # Split document into chunks
            chunks = self._create_text_chunks(text_content, page_texts)
            
            if not chunks:
                vector_logger.warning("No text chunks created for embedding")
                return []
            
            # Generate embeddings
            embeddings = await self._generate_embeddings([chunk['text'] for chunk in chunks])
            
            if not embeddings or len(embeddings) != len(chunks):
                vector_logger.error("Embedding generation failed or size mismatch")
                return []
            
            # Store embeddings
            document_embeddings = []
            
            for chunk, embedding_vector in zip(chunks, embeddings):
                # Store in PostgreSQL
                embedding_id = await self.db_manager.execute_scalar("""
                    INSERT INTO document_embeddings 
                    (job_id, chunk_id, chunk_text, embedding_vector, embedding_model,
                     page_number, start_position, end_position)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING embedding_id
                """, 
                job_id, chunk['chunk_id'], chunk['text'], 
                embedding_vector.tolist(), settings.ai_models.embedding_model,
                chunk.get('page_number'), chunk.get('start_position'), 
                chunk.get('end_position'))
                
                # Store in vector database
                await self._store_vector_embedding(
                    str(embedding_id), job_id, chunk, embedding_vector
                )
                
                document_embedding = DocumentEmbedding(
                    embedding_id=str(embedding_id),
                    job_id=job_id,
                    chunk_id=chunk['chunk_id'],
                    chunk_text=chunk['text'],
                    embedding_vector=embedding_vector.tolist(),
                    embedding_model=settings.ai_models.embedding_model,
                    page_number=chunk.get('page_number'),
                    start_position=chunk.get('start_position'),
                    end_position=chunk.get('end_position'),
                    created_at=chunk.get('created_at')
                )
                document_embeddings.append(document_embedding)
            
            vector_logger.info(f"Created {len(document_embeddings)} embeddings for job {job_id}")
            return document_embeddings
            
        except Exception as e:
            vector_logger.error(f"Embedding creation failed for job {job_id}: {str(e)}")
            raise
    
    def _create_text_chunks(self, text_content: str, page_texts: List[Dict] = None) -> List[Dict]:
        """Split text into chunks suitable for embedding"""
        
        chunk_size = settings.processing.chunk_size
        chunk_overlap = settings.processing.chunk_overlap
        
        chunks = []
        
        if page_texts:
            # Use page-based chunking if available
            for page_data in page_texts:
                page_num = page_data.get('page_number', 1)
                page_text = page_data.get('cleaned_text', '')
                
                if not page_text or len(page_text.strip()) < 50:
                    continue
                
                # Split page text into chunks
                page_chunks = self._split_text_into_chunks(
                    page_text, chunk_size, chunk_overlap
                )
                
                for i, chunk_text in enumerate(page_chunks):
                    chunks.append({
                        'chunk_id': len(chunks),
                        'text': chunk_text,
                        'page_number': page_num,
                        'start_position': 0,  # Would need more sophisticated calculation
                        'end_position': len(chunk_text)
                    })
        else:
            # Use simple text chunking
            text_chunks = self._split_text_into_chunks(
                text_content, chunk_size, chunk_overlap
            )
            
            for i, chunk_text in enumerate(text_chunks):
                chunks.append({
                    'chunk_id': i,
                    'text': chunk_text,
                    'page_number': None,
                    'start_position': i * (chunk_size - chunk_overlap),
                    'end_position': i * (chunk_size - chunk_overlap) + len(chunk_text)
                })
        
        return chunks
    
    def _split_text_into_chunks(self, text: str, chunk_size: int, 
                              chunk_overlap: int) -> List[str]:
        """Split text into overlapping chunks"""
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence ending within the last 100 characters
                sentence_end = text.rfind('.', start + chunk_size - 100, end)
                if sentence_end != -1 and sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - chunk_overlap
            
            if start >= len(text):
                break
        
        return chunks
    
    async def _generate_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for list of texts"""
        
        if not self.embedding_model:
            return []
        
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE and isinstance(self.embedding_model, SentenceTransformer):
                # Use sentence-transformers
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    self.executor,
                    self.embedding_model.encode,
                    texts
                )
                return [np.array(emb) for emb in embeddings]
            
            elif TRANSFORMERS_AVAILABLE and self.tokenizer:
                # Use transformers with manual pooling
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    self.executor,
                    self._generate_transformers_embeddings,
                    texts
                )
                return embeddings
            
        except Exception as e:
            vector_logger.error(f"Embedding generation failed: {str(e)}")
        
        return []
    
    def _generate_transformers_embeddings(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings using transformers library"""
        
        embeddings = []
        
        for text in texts:
            try:
                # Tokenize
                inputs = self.tokenizer(
                    text, 
                    return_tensors="pt", 
                    padding=True, 
                    truncation=True, 
                    max_length=512
                )
                
                # Get model output
                with torch.no_grad():
                    outputs = self.embedding_model(**inputs)
                
                # Mean pooling
                token_embeddings = outputs.last_hidden_state
                attention_mask = inputs['attention_mask']
                
                input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
                sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                
                embedding = (sum_embeddings / sum_mask).numpy()[0]
                embeddings.append(embedding)
                
            except Exception as e:
                vector_logger.warning(f"Failed to generate embedding for text: {str(e)}")
                # Add zero vector as fallback
                embeddings.append(np.zeros(self.embedding_dimension))
        
        return embeddings
    
    async def _store_vector_embedding(self, embedding_id: str, job_id: str, 
                                    chunk: Dict, embedding_vector: np.ndarray):
        """Store embedding in vector database"""
        
        try:
            if self.chroma_client and self.chroma_collection:
                # Store in ChromaDB
                self.chroma_collection.add(
                    embeddings=[embedding_vector.tolist()],
                    documents=[chunk['text']],
                    metadatas=[{
                        'job_id': job_id,
                        'chunk_id': str(chunk['chunk_id']),
                        'page_number': str(chunk.get('page_number', '')),
                        'embedding_id': embedding_id
                    }],
                    ids=[embedding_id]
                )
                
            elif self.pinecone_client:
                # Store in Pinecone
                self.pinecone_client.upsert([
                    (
                        embedding_id,
                        embedding_vector.tolist(),
                        {
                            'job_id': job_id,
                            'chunk_id': chunk['chunk_id'],
                            'page_number': chunk.get('page_number'),
                            'text': chunk['text'][:1000]  # Pinecone metadata has size limits
                        }
                    )
                ])
                
            elif self.weaviate_client:
                # Store in Weaviate
                self.weaviate_client.data_object.create(
                    data_object={
                        'job_id': job_id,
                        'chunk_id': chunk['chunk_id'],
                        'text': chunk['text'],
                        'page_number': chunk.get('page_number'),
                        'metadata': json.dumps(chunk)
                    },
                    class_name='Document',
                    uuid=embedding_id,
                    vector=embedding_vector.tolist()
                )
        
        except Exception as e:
            vector_logger.warning(f"Failed to store embedding in vector DB: {str(e)}")
    
    async def semantic_search(self, query: str, limit: int = 20,
                            similarity_threshold: float = 0.7,
                            filters: Dict[str, Any] = None) -> List[SemanticSearchResult]:
        """
        Perform semantic search across document embeddings
        
        Args:
            query: Search query text
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            filters: Additional filters (document_type, job_id, etc.)
            
        Returns:
            List of semantic search results
        """
        try:
            vector_logger.info(f"Performing semantic search: '{query}'")
            
            # Generate query embedding
            query_embeddings = await self._generate_embeddings([query])
            if not query_embeddings:
                vector_logger.warning("Failed to generate query embedding")
                return []
            
            query_vector = query_embeddings[0]
            
            # Search in vector database
            vector_results = await self._search_vector_database(
                query_vector, limit * 2  # Get more results to filter
            )
            
            # Enrich results with document metadata
            enriched_results = []
            
            for result in vector_results:
                try:
                    # Get document metadata
                    job_details = await self.db_manager.get_job_details(result['job_id'])
                    if not job_details:
                        continue
                    
                    # Get document metadata
                    doc_metadata = await self.db_manager.get_job_metadata(result['job_id'])
                    
                    # Create search result
                    search_result = SemanticSearchResult(
                        job_id=result['job_id'],
                        filename=job_details.get('original_filename', 'Unknown'),
                        document_type=doc_metadata.get('document_type', 'other') if doc_metadata else 'other',
                        chunk_text=result['text'],
                        similarity_score=result['similarity_score'],
                        page_number=result.get('page_number'),
                        chunk_id=result['chunk_id'],
                        metadata={
                            'file_size': job_details.get('file_size', 0),
                            'created_at': job_details.get('created_at'),
                            'confidence_score': doc_metadata.get('confidence_score') if doc_metadata else None
                        }
                    )
                    
                    # Apply similarity threshold
                    if search_result.similarity_score >= similarity_threshold:
                        enriched_results.append(search_result)
                
                except Exception as e:
                    vector_logger.warning(f"Failed to enrich search result: {str(e)}")
                    continue
            
            # Sort by similarity score and limit results
            enriched_results.sort(key=lambda x: x.similarity_score, reverse=True)
            final_results = enriched_results[:limit]
            
            vector_logger.info(f"Semantic search completed: {len(final_results)} results")
            return final_results
            
        except Exception as e:
            vector_logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    async def _search_vector_database(self, query_vector: np.ndarray, 
                                    limit: int) -> List[Dict[str, Any]]:
        """Search in the configured vector database"""
        
        try:
            if self.chroma_client and self.chroma_collection:
                # Search ChromaDB
                results = self.chroma_collection.query(
                    query_embeddings=[query_vector.tolist()],
                    n_results=limit
                )
                
                search_results = []
                
                for i, (doc, distance, metadata) in enumerate(zip(
                    results['documents'][0],
                    results['distances'][0], 
                    results['metadatas'][0]
                )):
                    similarity_score = 1.0 - distance  # Convert distance to similarity
                    
                    search_results.append({
                        'job_id': metadata['job_id'],
                        'chunk_id': int(metadata['chunk_id']),
                        'text': doc,
                        'similarity_score': similarity_score,
                        'page_number': int(metadata['page_number']) if metadata['page_number'] else None
                    })
                
                return search_results
                
            elif self.pinecone_client:
                # Search Pinecone
                results = self.pinecone_client.query(
                    vector=query_vector.tolist(),
                    top_k=limit,
                    include_metadata=True
                )
                
                search_results = []
                
                for match in results['matches']:
                    metadata = match['metadata']
                    search_results.append({
                        'job_id': metadata['job_id'],
                        'chunk_id': metadata['chunk_id'],
                        'text': metadata['text'],
                        'similarity_score': match['score'],
                        'page_number': metadata.get('page_number')
                    })
                
                return search_results
                
            elif self.weaviate_client:
                # Search Weaviate
                result = self.weaviate_client.query.get("Document", [
                    "job_id", "chunk_id", "text", "page_number", "metadata"
                ]).with_near_vector({
                    "vector": query_vector.tolist()
                }).with_limit(limit).do()
                
                search_results = []
                
                for item in result['data']['Get']['Document']:
                    search_results.append({
                        'job_id': item['job_id'],
                        'chunk_id': item['chunk_id'],
                        'text': item['text'],
                        'similarity_score': item.get('_additional', {}).get('distance', 0),
                        'page_number': item.get('page_number')
                    })
                
                return search_results
            
            else:
                # Fallback to PostgreSQL similarity search
                return await self._postgresql_similarity_search(query_vector, limit)
                
        except Exception as e:
            vector_logger.error(f"Vector database search failed: {str(e)}")
            return []
    
    async def _postgresql_similarity_search(self, query_vector: np.ndarray, 
                                          limit: int) -> List[Dict[str, Any]]:
        """Fallback similarity search using PostgreSQL"""
        
        try:
            # This requires pgvector extension for efficient vector similarity
            # For now, we'll use a simple approach with cosine similarity
            
            results = await self.db_manager.fetch_all("""
                SELECT 
                    de.job_id,
                    de.chunk_id,
                    de.chunk_text,
                    de.page_number,
                    de.embedding_vector
                FROM document_embeddings de
                JOIN document_processing_jobs dpj ON de.job_id = dpj.job_id
                WHERE dpj.status = 'completed'
                LIMIT $1
            """, limit * 10)  # Get more for similarity calculation
            
            search_results = []
            
            for row in results:
                try:
                    stored_vector = np.array(row['embedding_vector'])
                    
                    # Calculate cosine similarity
                    similarity = np.dot(query_vector, stored_vector) / (
                        np.linalg.norm(query_vector) * np.linalg.norm(stored_vector)
                    )
                    
                    search_results.append({
                        'job_id': row['job_id'],
                        'chunk_id': row['chunk_id'],
                        'text': row['chunk_text'],
                        'similarity_score': float(similarity),
                        'page_number': row['page_number']
                    })
                
                except Exception as e:
                    vector_logger.warning(f"Error calculating similarity: {str(e)}")
                    continue
            
            # Sort by similarity and return top results
            search_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return search_results[:limit]
            
        except Exception as e:
            vector_logger.error(f"PostgreSQL similarity search failed: {str(e)}")
            return []
    
    async def delete_document_embeddings(self, job_id: str):
        """Delete all embeddings for a document"""
        
        try:
            # Delete from PostgreSQL
            await self.db_manager.execute_command("""
                DELETE FROM document_embeddings WHERE job_id = $1
            """, job_id)
            
            # Delete from vector database
            if self.chroma_client and self.chroma_collection:
                # ChromaDB - need to get IDs first
                results = self.chroma_collection.get(
                    where={"job_id": job_id}
                )
                if results['ids']:
                    self.chroma_collection.delete(ids=results['ids'])
                    
            elif self.pinecone_client:
                # Pinecone - delete by metadata filter
                self.pinecone_client.delete(filter={'job_id': job_id})
                
            elif self.weaviate_client:
                # Weaviate - delete by where filter
                self.weaviate_client.batch.delete_objects(
                    class_name='Document',
                    where={'path': ['job_id'], 'operator': 'Equal', 'valueString': job_id}
                )
            
            vector_logger.info(f"Deleted embeddings for job {job_id}")
            
        except Exception as e:
            vector_logger.error(f"Failed to delete embeddings for job {job_id}: {str(e)}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection"""
        
        try:
            stats = {
                'total_embeddings': 0,
                'unique_documents': 0,
                'embedding_model': settings.ai_models.embedding_model,
                'vector_provider': self.provider
            }
            
            # Get stats from PostgreSQL
            pg_stats = await self.db_manager.execute_query("""
                SELECT 
                    COUNT(*) as total_embeddings,
                    COUNT(DISTINCT job_id) as unique_documents
                FROM document_embeddings
            """)
            
            if pg_stats:
                stats.update(pg_stats[0])
            
            # Get vector database specific stats
            if self.chroma_client and self.chroma_collection:
                try:
                    chroma_count = self.chroma_collection.count()
                    stats['vector_db_count'] = chroma_count
                except:
                    pass
            
            return stats
            
        except Exception as e:
            vector_logger.error(f"Failed to get collection stats: {str(e)}")
            return {'error': str(e)}