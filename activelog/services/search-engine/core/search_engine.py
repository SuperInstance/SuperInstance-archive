#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Core Engine
Implements semantic search across all 70+ services with ML-powered ranking
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Set, Union, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from enum import Enum
import sqlite3
import threading
import numpy as np
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

class SearchType(Enum):
    """Types of search queries"""
    TEXT = "text"
    SEMANTIC = "semantic"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"
    NATURAL_LANGUAGE = "natural_language"
    FUZZY = "fuzzy"
    PHONETIC = "phonetic"

class ContentType(Enum):
    """Types of searchable content"""
    DOCUMENT = "document"
    IMAGE = "image" 
    AUDIO = "audio"
    VIDEO = "video"
    LOG_ENTRY = "log_entry"
    EMAIL = "email"
    CHAT_MESSAGE = "chat_message"
    FILE = "file"
    CODE = "code"
    DATABASE_RECORD = "database_record"
    CUSTOM = "custom"

@dataclass
class SearchDocument:
    """Document in search index"""
    id: str
    service_id: str
    content_type: ContentType
    title: str
    content: str
    metadata: Dict[str, Any]
    embeddings: Optional[np.ndarray] = None
    indexed_at: float = 0
    last_modified: float = 0
    language: str = "en"
    tags: List[str] = None
    file_path: Optional[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.indexed_at == 0:
            self.indexed_at = time.time()
        if self.last_modified == 0:
            self.last_modified = time.time()

@dataclass
class SearchQuery:
    """Search query structure"""
    id: str
    query: str
    search_type: SearchType
    filters: Dict[str, Any] = None
    facets: List[str] = None
    limit: int = 50
    offset: int = 0
    user_id: Optional[str] = None
    language: str = "en"
    boost_fields: Dict[str, float] = None
    exclude_services: List[str] = None
    include_services: List[str] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}
        if self.facets is None:
            self.facets = []
        if self.boost_fields is None:
            self.boost_fields = {}

@dataclass
class SearchResult:
    """Individual search result"""
    document_id: str
    service_id: str
    title: str
    content_snippet: str
    content_type: ContentType
    score: float
    metadata: Dict[str, Any] = None
    highlights: List[str] = None
    explanation: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.highlights is None:
            self.highlights = []

@dataclass
class SearchResponse:
    """Search response with results and metadata"""
    query_id: str
    results: List[SearchResult]
    total_hits: int
    facets: Dict[str, Dict[str, int]] = None
    suggestions: List[str] = None
    query_time_ms: float = 0
    explanation: str = ""
    
    def __post_init__(self):
        if self.facets is None:
            self.facets = {}
        if self.suggestions is None:
            self.suggestions = []

class SearchIndex:
    """In-memory search index with persistence"""
    
    def __init__(self, db_path: str = "search_index.db"):
        self.documents: Dict[str, SearchDocument] = {}
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self.service_documents: Dict[str, Set[str]] = defaultdict(set)
        self.content_type_documents: Dict[ContentType, Set[str]] = defaultdict(set)
        self.language_documents: Dict[str, Set[str]] = defaultdict(set)
        
        # Full-text search structures
        self.term_frequencies: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.document_frequencies: Dict[str, int] = defaultdict(int)
        self.document_lengths: Dict[str, int] = {}
        self.avg_document_length: float = 0
        
        # Database persistence
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Statistics
        self.stats = {
            "documents_indexed": 0,
            "total_terms": 0,
            "avg_document_length": 0,
            "index_size_mb": 0
        }
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Documents table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    service_id TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    embeddings BLOB,
                    indexed_at REAL NOT NULL,
                    last_modified REAL NOT NULL,
                    language TEXT DEFAULT 'en',
                    tags TEXT,
                    file_path TEXT,
                    INDEX(service_id),
                    INDEX(content_type),
                    INDEX(language),
                    INDEX(indexed_at)
                )
            """)
            
            # Terms table for inverted index
            conn.execute("""
                CREATE TABLE IF NOT EXISTS terms (
                    term TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    tf_idf REAL NOT NULL,
                    positions TEXT,
                    PRIMARY KEY(term, document_id),
                    INDEX(term),
                    INDEX(document_id)
                )
            """)
            
            conn.commit()
            conn.close()
    
    def add_document(self, document: SearchDocument):
        """Add document to search index"""
        self.documents[document.id] = document
        self.service_documents[document.service_id].add(document.id)
        self.content_type_documents[document.content_type].add(document.id)
        self.language_documents[document.language].add(document.id)
        
        # Tokenize and index content
        tokens = self._tokenize(document.content + " " + document.title)
        self.document_lengths[document.id] = len(tokens)
        
        # Update term frequencies
        term_counts = Counter(tokens)
        for term, count in term_counts.items():
            self.term_frequencies[document.id][term] = count / len(tokens)
            self.inverted_index[term].add(document.id)
        
        # Update document frequencies
        unique_terms = set(tokens)
        for term in unique_terms:
            self.document_frequencies[term] += 1
        
        # Update statistics
        self._update_stats()
        self.stats["documents_indexed"] += 1
        
        # Persist to database
        self._persist_document(document)
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for indexing"""
        # Basic tokenization - in production, use proper NLP tokenizer
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        
        # Remove stop words (basic list)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        tokens = [token for token in tokens if token not in stop_words and len(token) > 2]
        
        return tokens
    
    def _update_stats(self):
        """Update index statistics"""
        if self.documents:
            total_length = sum(self.document_lengths.values())
            self.avg_document_length = total_length / len(self.documents)
            self.stats["avg_document_length"] = self.avg_document_length
            self.stats["total_terms"] = len(self.inverted_index)
    
    def _persist_document(self, document: SearchDocument):
        """Persist document to database"""
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                
                # Insert document
                conn.execute("""
                    INSERT OR REPLACE INTO documents 
                    (id, service_id, content_type, title, content, metadata, embeddings, 
                     indexed_at, last_modified, language, tags, file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    document.id,
                    document.service_id,
                    document.content_type.value,
                    document.title,
                    document.content,
                    json.dumps(document.metadata),
                    document.embeddings.tobytes() if document.embeddings is not None else None,
                    document.indexed_at,
                    document.last_modified,
                    document.language,
                    json.dumps(document.tags),
                    document.file_path
                ))
                
                # Insert terms
                tokens = self._tokenize(document.content + " " + document.title)
                term_counts = Counter(tokens)
                for term, count in term_counts.items():
                    tf_idf = count / len(tokens)  # Basic TF, IDF calculated later
                    conn.execute("""
                        INSERT OR REPLACE INTO terms (term, document_id, tf_idf, positions)
                        VALUES (?, ?, ?, ?)
                    """, (term, document.id, tf_idf, json.dumps([])))
                
                conn.commit()
                conn.close()
        
        # Run in thread to avoid blocking
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(_db_insert)
    
    def search_text(self, query: str, filters: Dict[str, Any] = None, limit: int = 50) -> List[Tuple[str, float]]:
        """Perform text-based search using TF-IDF"""
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        
        # Calculate query term weights
        query_term_counts = Counter(query_terms)
        query_length = len(query_terms)
        
        # Score documents
        document_scores = defaultdict(float)
        
        for term in query_terms:
            if term in self.inverted_index:
                # Calculate IDF
                df = self.document_frequencies[term]
                idf = np.log(len(self.documents) / (df + 1))
                
                # Query term frequency
                qtf = query_term_counts[term] / query_length
                
                for doc_id in self.inverted_index[term]:
                    # Apply filters
                    if not self._passes_filters(doc_id, filters):
                        continue
                    
                    # Calculate TF-IDF score
                    tf = self.term_frequencies[doc_id][term]
                    score = tf * idf * qtf
                    
                    # BM25-like normalization
                    doc_length = self.document_lengths[doc_id]
                    k1, b = 1.5, 0.75
                    score = score * (k1 + 1) / (score + k1 * (1 - b + b * doc_length / self.avg_document_length))
                    
                    document_scores[doc_id] += score
        
        # Sort by score and return top results
        sorted_results = sorted(document_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:limit]
    
    def _passes_filters(self, doc_id: str, filters: Dict[str, Any]) -> bool:
        """Check if document passes filter criteria"""
        if not filters:
            return True
        
        document = self.documents.get(doc_id)
        if not document:
            return False
        
        # Service filter
        if 'services' in filters:
            if document.service_id not in filters['services']:
                return False
        
        # Content type filter
        if 'content_types' in filters:
            if document.content_type.value not in filters['content_types']:
                return False
        
        # Language filter
        if 'language' in filters:
            if document.language != filters['language']:
                return False
        
        # Date range filter
        if 'date_from' in filters or 'date_to' in filters:
            doc_date = document.last_modified
            if 'date_from' in filters and doc_date < filters['date_from']:
                return False
            if 'date_to' in filters and doc_date > filters['date_to']:
                return False
        
        # Tags filter
        if 'tags' in filters:
            required_tags = set(filters['tags'])
            doc_tags = set(document.tags)
            if not required_tags.issubset(doc_tags):
                return False
        
        # Custom metadata filters
        for key, value in filters.items():
            if key.startswith('metadata.'):
                metadata_key = key[9:]  # Remove 'metadata.' prefix
                if metadata_key in document.metadata:
                    if document.metadata[metadata_key] != value:
                        return False
        
        return True
    
    def get_document(self, doc_id: str) -> Optional[SearchDocument]:
        """Get document by ID"""
        return self.documents.get(doc_id)
    
    def remove_document(self, doc_id: str):
        """Remove document from index"""
        if doc_id not in self.documents:
            return
        
        document = self.documents[doc_id]
        
        # Remove from indexes
        del self.documents[doc_id]
        self.service_documents[document.service_id].discard(doc_id)
        self.content_type_documents[document.content_type].discard(doc_id)
        self.language_documents[document.language].discard(doc_id)
        
        # Remove from inverted index
        tokens = self._tokenize(document.content + " " + document.title)
        unique_terms = set(tokens)
        
        for term in unique_terms:
            self.inverted_index[term].discard(doc_id)
            if not self.inverted_index[term]:
                del self.inverted_index[term]
            
            self.document_frequencies[term] -= 1
            if self.document_frequencies[term] <= 0:
                del self.document_frequencies[term]
        
        # Remove term frequencies
        if doc_id in self.term_frequencies:
            del self.term_frequencies[doc_id]
        
        if doc_id in self.document_lengths:
            del self.document_lengths[doc_id]
        
        # Update statistics
        self._update_stats()
    
    def get_facets(self, query: str, filters: Dict[str, Any] = None) -> Dict[str, Dict[str, int]]:
        """Get faceted search results"""
        # Get matching documents
        results = self.search_text(query, filters, limit=1000)  # Get more for faceting
        matching_doc_ids = [doc_id for doc_id, score in results]
        
        facets = {
            "services": defaultdict(int),
            "content_types": defaultdict(int),
            "languages": defaultdict(int),
            "tags": defaultdict(int)
        }
        
        for doc_id in matching_doc_ids:
            document = self.documents.get(doc_id)
            if document:
                facets["services"][document.service_id] += 1
                facets["content_types"][document.content_type.value] += 1
                facets["languages"][document.language] += 1
                
                for tag in document.tags:
                    facets["tags"][tag] += 1
        
        # Convert to regular dict
        return {key: dict(value) for key, value in facets.items()}
    
    def get_suggestions(self, query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on indexed terms"""
        query_lower = query.lower()
        suggestions = []
        
        # Find terms that start with query
        for term in self.inverted_index.keys():
            if term.startswith(query_lower) and term != query_lower:
                suggestions.append(term)
        
        # Sort by document frequency (popularity)
        suggestions.sort(key=lambda x: self.document_frequencies[x], reverse=True)
        return suggestions[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search index statistics"""
        return {
            **self.stats,
            "total_documents": len(self.documents),
            "total_services": len(self.service_documents),
            "content_type_distribution": {
                ct.value: len(docs) for ct, docs in self.content_type_documents.items()
            },
            "language_distribution": dict(Counter(doc.language for doc in self.documents.values())),
            "memory_usage_mb": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        # Rough estimation
        base_size = len(self.documents) * 1000  # ~1KB per document
        index_size = len(self.inverted_index) * 100  # ~100B per term
        return (base_size + index_size) / (1024 * 1024)

class UnifiedSearchEngine:
    """Main search engine coordinating all search capabilities"""
    
    def __init__(self):
        self.index = SearchIndex()
        self.query_log = []
        self.popular_queries = Counter()
        
        # Component references (will be set by main system)
        self.semantic_search = None
        self.multimodal_search = None
        self.nlp_processor = None
        self.ranking_model = None
        self.fuzzy_matcher = None
        self.multilingual_processor = None
        
        # Statistics
        self.stats = {
            "searches_performed": 0,
            "avg_query_time_ms": 0,
            "popular_queries": {},
            "search_types": defaultdict(int)
        }
    
    def set_components(self, **components):
        """Set search component references"""
        for name, component in components.items():
            setattr(self, name, component)
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Perform unified search across all capabilities"""
        start_time = time.time()
        
        # Log query
        self.query_log.append({
            "query": query.query,
            "type": query.search_type.value,
            "user_id": query.user_id,
            "timestamp": start_time
        })
        self.popular_queries[query.query] += 1
        
        try:
            # Route to appropriate search method
            if query.search_type == SearchType.SEMANTIC and self.semantic_search:
                results = await self.semantic_search.search(query)
            elif query.search_type == SearchType.MULTIMODAL and self.multimodal_search:
                results = await self.multimodal_search.search(query)
            elif query.search_type == SearchType.NATURAL_LANGUAGE and self.nlp_processor:
                # Parse natural language query first
                parsed_query = await self.nlp_processor.parse_query(query.query)
                query.query = parsed_query.get("processed_query", query.query)
                query.filters.update(parsed_query.get("filters", {}))
                results = self._search_text(query)
            elif query.search_type == SearchType.FUZZY and self.fuzzy_matcher:
                results = await self.fuzzy_matcher.search(query)
            else:
                # Default text search
                results = self._search_text(query)
            
            # Apply ML ranking if available
            if self.ranking_model and results:
                results = await self.ranking_model.rerank_results(query, results)
            
            # Calculate facets
            facets = self.index.get_facets(query.query, query.filters)
            
            # Get suggestions
            suggestions = self.index.get_suggestions(query.query)
            
            # Create response
            query_time = (time.time() - start_time) * 1000
            
            response = SearchResponse(
                query_id=query.id,
                results=results[:query.limit],
                total_hits=len(results),
                facets=facets,
                suggestions=suggestions,
                query_time_ms=query_time
            )
            
            # Update statistics
            self.stats["searches_performed"] += 1
            self.stats["search_types"][query.search_type.value] += 1
            
            # Update average query time
            current_avg = self.stats["avg_query_time_ms"]
            total_searches = self.stats["searches_performed"]
            self.stats["avg_query_time_ms"] = ((current_avg * (total_searches - 1)) + query_time) / total_searches
            
            return response
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return SearchResponse(
                query_id=query.id,
                results=[],
                total_hits=0,
                query_time_ms=(time.time() - start_time) * 1000,
                explanation=f"Search failed: {str(e)}"
            )
    
    def _search_text(self, query: SearchQuery) -> List[SearchResult]:
        """Perform text-based search"""
        # Filter by included/excluded services
        filters = query.filters.copy()
        
        if query.include_services:
            filters["services"] = query.include_services
        elif query.exclude_services:
            # Get all services except excluded ones
            all_services = set(self.index.service_documents.keys())
            included_services = all_services - set(query.exclude_services)
            filters["services"] = list(included_services)
        
        # Perform search
        search_results = self.index.search_text(query.query, filters, query.limit + query.offset)
        
        # Skip offset results
        search_results = search_results[query.offset:]
        
        # Convert to SearchResult objects
        results = []
        for doc_id, score in search_results:
            document = self.index.get_document(doc_id)
            if document:
                # Create content snippet
                snippet = self._create_snippet(document.content, query.query)
                
                # Create highlights
                highlights = self._create_highlights(document.content, query.query)
                
                result = SearchResult(
                    document_id=doc_id,
                    service_id=document.service_id,
                    title=document.title,
                    content_snippet=snippet,
                    content_type=document.content_type,
                    score=score,
                    metadata=document.metadata,
                    highlights=highlights
                )
                results.append(result)
        
        return results
    
    def _create_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Create content snippet with query context"""
        query_terms = self.index._tokenize(query)
        if not query_terms:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # Find best snippet around query terms
        content_lower = content.lower()
        best_position = 0
        best_score = 0
        
        for term in query_terms:
            position = content_lower.find(term.lower())
            if position != -1:
                # Score based on term frequency in snippet
                snippet_start = max(0, position - max_length // 2)
                snippet_end = min(len(content), snippet_start + max_length)
                snippet = content[snippet_start:snippet_end].lower()
                
                score = sum(snippet.count(t.lower()) for t in query_terms)
                if score > best_score:
                    best_score = score
                    best_position = snippet_start
        
        # Extract snippet
        snippet_end = min(len(content), best_position + max_length)
        snippet = content[best_position:snippet_end]
        
        if best_position > 0:
            snippet = "..." + snippet
        if snippet_end < len(content):
            snippet = snippet + "..."
        
        return snippet
    
    def _create_highlights(self, content: str, query: str) -> List[str]:
        """Create highlighted query terms in content"""
        query_terms = self.index._tokenize(query)
        highlights = []
        
        content_lower = content.lower()
        for term in query_terms:
            term_lower = term.lower()
            start_pos = 0
            while True:
                pos = content_lower.find(term_lower, start_pos)
                if pos == -1:
                    break
                
                # Find word boundaries
                word_start = pos
                while word_start > 0 and content[word_start - 1].isalnum():
                    word_start -= 1
                
                word_end = pos + len(term)
                while word_end < len(content) and content[word_end].isalnum():
                    word_end += 1
                
                highlighted_term = content[word_start:word_end]
                if highlighted_term not in highlights:
                    highlights.append(highlighted_term)
                
                start_pos = pos + 1
        
        return highlights[:10]  # Limit highlights
    
    def add_document(self, document: SearchDocument):
        """Add document to search index"""
        self.index.add_document(document)
    
    def remove_document(self, doc_id: str):
        """Remove document from search index"""
        self.index.remove_document(doc_id)
    
    def get_popular_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most popular search queries"""
        return self.popular_queries.most_common(limit)
    
    def get_search_analytics(self) -> Dict[str, Any]:
        """Get comprehensive search analytics"""
        recent_queries = [q for q in self.query_log if time.time() - q["timestamp"] < 3600]  # Last hour
        
        return {
            **self.stats,
            "popular_queries": dict(self.popular_queries.most_common(10)),
            "recent_queries_count": len(recent_queries),
            "index_stats": self.index.get_stats(),
            "query_log_size": len(self.query_log)
        }