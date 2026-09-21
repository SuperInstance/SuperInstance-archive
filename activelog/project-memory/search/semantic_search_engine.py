"""
ActiveLog Project Memory - Advanced Semantic Search Engine
Vector embeddings and neural search with contextual understanding
"""

from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import json
import asyncio
import hashlib
import pickle
import math
from datetime import datetime, timezone
from collections import defaultdict, Counter
import re

class SearchStrategy(Enum):
    """Different search strategies available"""
    KEYWORD_MATCH = "keyword"
    SEMANTIC_VECTOR = "semantic"
    CONTEXTUAL_SIMILARITY = "contextual"
    HYBRID_SEARCH = "hybrid"
    NEURAL_RANKING = "neural"

class SearchIntent(Enum):
    """Types of search intent"""
    EXACT_LOOKUP = "exact"
    CONCEPTUAL_SEARCH = "conceptual"
    RELATED_CONCEPTS = "related"
    CODE_SEARCH = "code"
    API_DISCOVERY = "api"
    TROUBLESHOOTING = "troubleshoot"

@dataclass
class SearchQuery:
    """Structured search query with intent and context"""
    query_text: str
    intent: SearchIntent = SearchIntent.CONCEPTUAL_SEARCH
    context: Dict[str, Any] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)
    max_results: int = 10
    similarity_threshold: float = 0.7
    boost_categories: List[str] = field(default_factory=list)

@dataclass
class SearchResult:
    """Enhanced search result with relevance scoring"""
    concept_id: str
    content: str
    category: str
    relevance_score: float
    semantic_similarity: float
    keyword_matches: List[str]
    context_relevance: float
    explanation: str = ""
    related_concepts: List[str] = field(default_factory=list)

class VectorEmbeddingEngine:
    """
    Simple vector embedding engine for semantic search
    In production, this would use pre-trained embeddings like sentence-transformers
    """
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.word_vectors = {}
        self.concept_vectors = {}
        self.vocabulary = set()
        
        # Initialize with basic word embeddings
        self._initialize_basic_embeddings()
    
    def _initialize_basic_embeddings(self):
        """Initialize basic word embeddings for common technical terms"""
        
        # Technical domain clusters
        tech_clusters = {
            "api": ["endpoint", "route", "handler", "controller", "rest", "http", "request", "response"],
            "auth": ["authentication", "authorization", "jwt", "token", "login", "session", "security"],
            "data": ["database", "model", "schema", "repository", "query", "table", "record"],
            "ui": ["interface", "component", "react", "frontend", "view", "template", "render"],
            "ai": ["artificial", "intelligence", "machine", "learning", "neural", "model", "training"],
            "system": ["service", "microservice", "architecture", "integration", "orchestration"],
            "business": ["portfolio", "financial", "trading", "market", "analytics", "management"],
            "development": ["code", "programming", "framework", "library", "deployment", "testing"]
        }
        
        # Generate cluster-based embeddings
        for cluster_name, words in tech_clusters.items():
            base_vector = self._generate_cluster_vector(cluster_name)
            
            for word in words:
                # Add some variation to base vector
                variation = np.random.normal(0, 0.1, self.embedding_dim)
                self.word_vectors[word] = base_vector + variation
                self.vocabulary.add(word)
    
    def _generate_cluster_vector(self, cluster_name: str) -> np.ndarray:
        """Generate base vector for a semantic cluster"""
        # Use cluster name hash to generate consistent base vector
        hash_val = int(hashlib.md5(cluster_name.encode()).hexdigest(), 16)
        np.random.seed(hash_val % 2**32)  # Ensure reproducible vectors
        
        vector = np.random.normal(0, 1, self.embedding_dim)
        return vector / np.linalg.norm(vector)  # Normalize
    
    def get_text_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a text using word vectors"""
        words = self._tokenize(text.lower())
        
        if not words:
            return np.zeros(self.embedding_dim)
        
        word_embeddings = []
        for word in words:
            if word in self.word_vectors:
                word_embeddings.append(self.word_vectors[word])
            else:
                # Generate embedding for unknown word
                word_embeddings.append(self._generate_word_vector(word))
        
        if not word_embeddings:
            return np.zeros(self.embedding_dim)
        
        # Average word embeddings (simple but effective)
        text_embedding = np.mean(word_embeddings, axis=0)
        return text_embedding / np.linalg.norm(text_embedding)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        return [word for word in text.split() if len(word) > 2]
    
    def _generate_word_vector(self, word: str) -> np.ndarray:
        """Generate vector for unknown word"""
        # Use word characters to create consistent vector
        char_sum = sum(ord(c) for c in word)
        np.random.seed(char_sum % 2**32)
        
        vector = np.random.normal(0, 0.5, self.embedding_dim)
        self.word_vectors[word] = vector  # Cache for future use
        return vector
    
    def calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between vectors"""
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def store_concept_embedding(self, concept_id: str, content: str):
        """Store embedding for a concept"""
        embedding = self.get_text_embedding(content)
        self.concept_vectors[concept_id] = embedding
    
    def find_similar_concepts(self, query_embedding: np.ndarray, 
                            top_k: int = 10) -> List[Tuple[str, float]]:
        """Find concepts most similar to query"""
        similarities = []
        
        for concept_id, concept_embedding in self.concept_vectors.items():
            similarity = self.calculate_similarity(query_embedding, concept_embedding)
            similarities.append((concept_id, similarity))
        
        # Sort by similarity and return top k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]

class AdvancedSemanticSearchEngine:
    """
    Advanced semantic search engine with multiple search strategies
    and intelligent result ranking
    """
    
    def __init__(self):
        self.vector_engine = VectorEmbeddingEngine()
        self.search_history = []
        self.concept_graph = {}  # Concept relationships
        self.category_weights = {}
        self.query_patterns = defaultdict(list)
        
        # Search optimization
        self.result_cache = {}
        self.popularity_scores = defaultdict(float)
        self.click_through_rates = defaultdict(float)
        
    async def search(self, query: SearchQuery, 
                   knowledge_base: Dict[str, Any]) -> List[SearchResult]:
        """
        Perform advanced semantic search with multiple strategies
        """
        
        # Analyze query intent and context
        analyzed_query = await self._analyze_query(query)
        
        # Get candidates using multiple strategies
        candidates = await self._get_search_candidates(analyzed_query, knowledge_base)
        
        # Rank and score results
        ranked_results = await self._rank_results(analyzed_query, candidates)
        
        # Apply filters and limits
        filtered_results = await self._apply_filters(ranked_results, query)
        
        # Store search for learning
        await self._update_search_history(query, filtered_results)
        
        return filtered_results[:query.max_results]
    
    async def _analyze_query(self, query: SearchQuery) -> Dict[str, Any]:
        """Analyze query to understand intent and extract features"""
        
        query_text = query.query_text.lower()
        
        analysis = {
            "original_query": query,
            "tokens": query_text.split(),
            "technical_terms": [],
            "question_type": None,
            "entity_mentions": [],
            "intent_confidence": 0.0,
            "query_embedding": None
        }
        
        # Detect technical terms
        for token in analysis["tokens"]:
            if token in self.vector_engine.vocabulary:
                analysis["technical_terms"].append(token)
        
        # Detect question type
        question_patterns = {
            "what": SearchIntent.CONCEPTUAL_SEARCH,
            "how": SearchIntent.CODE_SEARCH, 
            "why": SearchIntent.TROUBLESHOOTING,
            "where": SearchIntent.API_DISCOVERY,
            "when": SearchIntent.RELATED_CONCEPTS
        }
        
        for pattern, intent in question_patterns.items():
            if pattern in query_text:
                analysis["question_type"] = intent
                analysis["intent_confidence"] = 0.8
                break
        
        # Extract entities (service names, technical terms)
        activelog_entities = [
            "bot-orchestrator", "luciddreamer", "dream-simulator", 
            "code-director", "project-memory", "business-platform",
            "paper-trading", "hatchery-manager", "claude", "api",
            "authentication", "database", "redis", "postgresql"
        ]
        
        for entity in activelog_entities:
            if entity.lower() in query_text:
                analysis["entity_mentions"].append(entity)
        
        # Generate query embedding
        analysis["query_embedding"] = self.vector_engine.get_text_embedding(query_text)
        
        return analysis
    
    async def _get_search_candidates(self, analyzed_query: Dict[str, Any],
                                   knowledge_base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get candidate results using multiple search strategies"""
        
        candidates = []
        query = analyzed_query["original_query"]
        
        # Strategy 1: Keyword matching
        keyword_candidates = await self._keyword_search(analyzed_query, knowledge_base)
        candidates.extend(keyword_candidates)
        
        # Strategy 2: Vector similarity search
        if analyzed_query["query_embedding"] is not None:
            vector_candidates = await self._vector_search(analyzed_query, knowledge_base)
            candidates.extend(vector_candidates)
        
        # Strategy 3: Category-based search
        if query.boost_categories:
            category_candidates = await self._category_search(analyzed_query, knowledge_base)
            candidates.extend(category_candidates)
        
        # Strategy 4: Entity-based search
        if analyzed_query["entity_mentions"]:
            entity_candidates = await self._entity_search(analyzed_query, knowledge_base)
            candidates.extend(entity_candidates)
        
        # Remove duplicates while preserving candidate info
        unique_candidates = {}
        for candidate in candidates:
            concept_id = candidate["concept_id"]
            if concept_id not in unique_candidates:
                unique_candidates[concept_id] = candidate
            else:
                # Merge scores from different strategies
                existing = unique_candidates[concept_id]
                existing["combined_score"] = max(
                    existing.get("combined_score", 0),
                    candidate.get("combined_score", 0)
                )
        
        return list(unique_candidates.values())
    
    async def _keyword_search(self, analyzed_query: Dict[str, Any],
                            knowledge_base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform keyword-based search"""
        
        candidates = []
        query_tokens = analyzed_query["tokens"]
        
        for concept_id, concept_data in knowledge_base.items():
            content = concept_data.get("content", "").lower()
            category = concept_data.get("category", "")
            
            # Calculate keyword match score
            matches = []
            match_score = 0
            
            for token in query_tokens:
                if len(token) > 2:  # Skip very short tokens
                    if token in content:
                        matches.append(token)
                        # Weight by term frequency and position
                        term_freq = content.count(token)
                        position_weight = 1.0 if content.startswith(token) else 0.5
                        match_score += term_freq * position_weight
            
            if matches:
                # Normalize score by content length
                normalized_score = match_score / len(content.split())
                
                candidates.append({
                    "concept_id": concept_id,
                    "content": concept_data.get("content", ""),
                    "category": category,
                    "search_strategy": "keyword",
                    "combined_score": normalized_score,
                    "keyword_matches": matches,
                    "match_details": {
                        "raw_score": match_score,
                        "match_count": len(matches)
                    }
                })
        
        return candidates
    
    async def _vector_search(self, analyzed_query: Dict[str, Any],
                           knowledge_base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        
        candidates = []
        query_embedding = analyzed_query["query_embedding"]
        
        # Find similar concepts using vector engine
        similar_concepts = self.vector_engine.find_similar_concepts(
            query_embedding, top_k=20
        )
        
        for concept_id, similarity in similar_concepts:
            if concept_id in knowledge_base:
                concept_data = knowledge_base[concept_id]
                
                candidates.append({
                    "concept_id": concept_id,
                    "content": concept_data.get("content", ""),
                    "category": concept_data.get("category", ""),
                    "search_strategy": "vector",
                    "combined_score": similarity,
                    "semantic_similarity": similarity,
                    "match_details": {
                        "vector_similarity": similarity
                    }
                })
        
        return candidates
    
    async def _category_search(self, analyzed_query: Dict[str, Any],
                             knowledge_base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search within specific categories"""
        
        candidates = []
        boost_categories = analyzed_query["original_query"].boost_categories
        
        for concept_id, concept_data in knowledge_base.items():
            category = concept_data.get("category", "")
            
            # Check if concept is in boosted categories
            category_match = False
            for boost_cat in boost_categories:
                if boost_cat.upper() in category or category.startswith(boost_cat.upper()):
                    category_match = True
                    break
            
            if category_match:
                # Calculate relevance within category
                content = concept_data.get("content", "").lower()
                query_text = analyzed_query["original_query"].query_text.lower()
                
                # Simple relevance based on query terms in content
                relevance = 0
                query_words = query_text.split()
                for word in query_words:
                    if word in content:
                        relevance += 1
                
                if relevance > 0:
                    normalized_relevance = relevance / len(query_words)
                    
                    candidates.append({
                        "concept_id": concept_id,
                        "content": concept_data.get("content", ""),
                        "category": category,
                        "search_strategy": "category",
                        "combined_score": normalized_relevance + 0.2,  # Category boost
                        "category_boost": True,
                        "match_details": {
                            "category_relevance": normalized_relevance
                        }
                    })
        
        return candidates
    
    async def _entity_search(self, analyzed_query: Dict[str, Any],
                           knowledge_base: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search based on entity mentions"""
        
        candidates = []
        entities = analyzed_query["entity_mentions"]
        
        for concept_id, concept_data in knowledge_base.items():
            content = concept_data.get("content", "").lower()
            category = concept_data.get("category", "")
            
            # Check for entity matches
            entity_matches = []
            entity_score = 0
            
            for entity in entities:
                if entity.lower() in content:
                    entity_matches.append(entity)
                    entity_score += 1
                    
                    # Bonus for exact category match
                    if entity.upper().replace("-", "_") in category:
                        entity_score += 0.5
            
            if entity_matches:
                candidates.append({
                    "concept_id": concept_id,
                    "content": concept_data.get("content", ""),
                    "category": category,
                    "search_strategy": "entity",
                    "combined_score": entity_score,
                    "entity_matches": entity_matches,
                    "match_details": {
                        "entity_score": entity_score,
                        "matched_entities": entity_matches
                    }
                })
        
        return candidates
    
    async def _rank_results(self, analyzed_query: Dict[str, Any],
                          candidates: List[Dict[str, Any]]) -> List[SearchResult]:
        """Rank and score search results using multiple factors"""
        
        results = []
        
        for candidate in candidates:
            concept_id = candidate["concept_id"]
            
            # Base relevance score from search strategy
            base_score = candidate.get("combined_score", 0)
            
            # Apply popularity boost
            popularity_boost = self.popularity_scores.get(concept_id, 0) * 0.1
            
            # Apply recency boost (newer concepts slightly preferred)
            recency_boost = 0.05  # Small constant boost for now
            
            # Apply category boost if applicable
            category_boost = 0
            if candidate.get("category_boost", False):
                category_boost = 0.15
            
            # Calculate final relevance score
            final_score = base_score + popularity_boost + recency_boost + category_boost
            
            # Calculate individual components
            semantic_similarity = candidate.get("semantic_similarity", 0)
            keyword_matches = candidate.get("keyword_matches", [])
            
            # Calculate context relevance
            context_relevance = await self._calculate_context_relevance(
                analyzed_query, candidate
            )
            
            # Generate explanation
            explanation = await self._generate_result_explanation(
                analyzed_query, candidate, final_score
            )
            
            result = SearchResult(
                concept_id=concept_id,
                content=candidate["content"],
                category=candidate["category"],
                relevance_score=final_score,
                semantic_similarity=semantic_similarity,
                keyword_matches=keyword_matches,
                context_relevance=context_relevance,
                explanation=explanation
            )
            
            results.append(result)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return results
    
    async def _calculate_context_relevance(self, analyzed_query: Dict[str, Any],
                                         candidate: Dict[str, Any]) -> float:
        """Calculate how relevant the result is to the query context"""
        
        query_context = analyzed_query["original_query"].context
        relevance = 0.5  # Base relevance
        
        # Check for context matches
        if "bot_type" in query_context:
            bot_type = query_context["bot_type"]
            
            # Adjust relevance based on content complexity for bot type
            content_length = len(candidate.get("content", ""))
            
            if bot_type == "simple" and content_length < 100:
                relevance += 0.2
            elif bot_type == "expert" and content_length > 200:
                relevance += 0.2
            elif bot_type in ["intermediate", "advanced"]:
                relevance += 0.1
        
        # Check for task context relevance
        if "task_type" in query_context:
            task_type = query_context["task_type"]
            category = candidate.get("category", "")
            
            task_category_mapping = {
                "api": ["API", "SERVICE"],
                "auth": ["AUTH", "SECURITY"],
                "business": ["BIZ", "BUSINESS"],
                "development": ["DEV", "CODE"]
            }
            
            if task_type in task_category_mapping:
                relevant_categories = task_category_mapping[task_type]
                if any(cat in category for cat in relevant_categories):
                    relevance += 0.15
        
        return min(1.0, relevance)
    
    async def _generate_result_explanation(self, analyzed_query: Dict[str, Any],
                                         candidate: Dict[str, Any],
                                         final_score: float) -> str:
        """Generate explanation for why this result was returned"""
        
        explanations = []
        
        # Strategy explanation
        strategy = candidate.get("search_strategy", "unknown")
        if strategy == "keyword":
            matches = candidate.get("keyword_matches", [])
            if matches:
                explanations.append(f"Matches keywords: {', '.join(matches[:3])}")
        
        elif strategy == "vector":
            similarity = candidate.get("semantic_similarity", 0)
            explanations.append(f"Semantic similarity: {similarity:.2f}")
        
        elif strategy == "category":
            explanations.append(f"Relevant category match")
        
        elif strategy == "entity":
            entities = candidate.get("entity_matches", [])
            if entities:
                explanations.append(f"Mentions: {', '.join(entities[:2])}")
        
        # Score explanation
        if final_score > 0.8:
            explanations.append("High relevance")
        elif final_score > 0.6:
            explanations.append("Good match")
        else:
            explanations.append("Partial match")
        
        return " • ".join(explanations)
    
    async def _apply_filters(self, results: List[SearchResult],
                           query: SearchQuery) -> List[SearchResult]:
        """Apply query filters to results"""
        
        filtered = []
        
        for result in results:
            # Apply similarity threshold
            if result.relevance_score < query.similarity_threshold:
                continue
            
            # Apply category filters
            if "categories" in query.filters:
                allowed_categories = query.filters["categories"]
                if not any(cat in result.category for cat in allowed_categories):
                    continue
            
            # Apply content length filters
            if "min_length" in query.filters:
                if len(result.content) < query.filters["min_length"]:
                    continue
            
            if "max_length" in query.filters:
                if len(result.content) > query.filters["max_length"]:
                    continue
            
            filtered.append(result)
        
        return filtered
    
    async def _update_search_history(self, query: SearchQuery,
                                   results: List[SearchResult]):
        """Update search history for learning and optimization"""
        
        search_record = {
            "query": query.query_text,
            "intent": query.intent.value,
            "timestamp": datetime.now(timezone.utc),
            "results_count": len(results),
            "top_result": results[0].concept_id if results else None,
            "categories_returned": list(set(r.category for r in results))
        }
        
        self.search_history.append(search_record)
        
        # Update popularity scores for returned concepts
        for result in results[:5]:  # Top 5 results get popularity boost
            self.popularity_scores[result.concept_id] += 0.1
    
    async def index_concepts(self, knowledge_base: Dict[str, Any]):
        """Index concepts for improved search performance"""
        
        for concept_id, concept_data in knowledge_base.items():
            content = concept_data.get("content", "")
            category = concept_data.get("category", "")
            
            # Store vector embedding
            self.vector_engine.store_concept_embedding(concept_id, content)
            
            # Update category weights
            if category not in self.category_weights:
                self.category_weights[category] = 0
            self.category_weights[category] += 1
    
    async def suggest_related_queries(self, query: str) -> List[str]:
        """Suggest related queries based on search history and patterns"""
        
        suggestions = []
        query_lower = query.lower()
        
        # Find similar historical queries
        for record in self.search_history:
            hist_query = record["query"].lower()
            
            # Simple similarity check
            common_words = set(query_lower.split()) & set(hist_query.split())
            if len(common_words) >= 2 and hist_query != query_lower:
                suggestions.append(record["query"])
        
        # Add pattern-based suggestions
        if "api" in query_lower:
            suggestions.extend([
                "API documentation",
                "API endpoints",
                "API authentication"
            ])
        
        if "auth" in query_lower:
            suggestions.extend([
                "Authentication flow",
                "JWT tokens",
                "User permissions"
            ])
        
        # Remove duplicates and limit
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:5]
    
    async def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics and performance metrics"""
        
        if not self.search_history:
            return {"message": "No search history available"}
        
        total_searches = len(self.search_history)
        
        # Intent distribution
        intent_counts = Counter(record["intent"] for record in self.search_history)
        
        # Popular categories
        category_counts = defaultdict(int)
        for record in self.search_history:
            for category in record.get("categories_returned", []):
                category_counts[category] += 1
        
        # Average results per query
        avg_results = sum(record["results_count"] for record in self.search_history) / total_searches
        
        # Most popular concepts
        concept_popularity = sorted(
            self.popularity_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_searches": total_searches,
            "intent_distribution": dict(intent_counts),
            "popular_categories": dict(category_counts),
            "average_results_per_query": avg_results,
            "most_popular_concepts": concept_popularity,
            "indexed_concepts": len(self.vector_engine.concept_vectors),
            "vocabulary_size": len(self.vector_engine.vocabulary)
        }