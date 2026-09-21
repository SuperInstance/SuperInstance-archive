#!/usr/bin/env python3
"""
ActiveLog Unified Search Engine - Saved Searches & Suggestions
Advanced search suggestions, autocomplete, and saved search functionality
"""

import asyncio
import json
import logging
import time
import sqlite3
import threading
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import uuid
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SavedSearch:
    """Saved search configuration"""
    id: str
    user_id: str
    name: str
    query: str
    filters: Dict[str, Any] = None
    facets: List[str] = None
    alert_enabled: bool = False
    alert_frequency: str = "daily"  # "immediate", "hourly", "daily", "weekly"
    created_at: float = 0
    last_executed: float = 0
    execution_count: int = 0
    is_public: bool = False
    tags: List[str] = None
    
    def __post_init__(self):
        if self.filters is None:
            self.filters = {}
        if self.facets is None:
            self.facets = []
        if self.tags is None:
            self.tags = []
        if self.created_at == 0:
            self.created_at = time.time()

@dataclass
class SearchSuggestion:
    """Search suggestion with metadata"""
    text: str
    type: str  # "query", "filter", "completion", "trending"
    score: float
    metadata: Dict[str, Any] = None
    source: str = "system"
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AutocompleteResult:
    """Autocomplete result"""
    suggestion: str
    type: str
    score: float
    highlight_positions: List[Tuple[int, int]] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.highlight_positions is None:
            self.highlight_positions = []
        if self.metadata is None:
            self.metadata = {}

class QueryAnalyzer:
    """Analyzes search queries for patterns and suggestions"""
    
    def __init__(self):
        # Common query patterns
        self.query_patterns = {
            r'from:(\w+)': 'user_filter',
            r'type:(\w+)': 'content_type_filter', 
            r'tag:(\w+)': 'tag_filter',
            r'before:(\d{4}-\d{2}-\d{2})': 'date_filter',
            r'after:(\d{4}-\d{2}-\d{2})': 'date_filter',
            r'service:(\w+)': 'service_filter',
            r'lang:(\w+)': 'language_filter'
        }
        
        # Stop words for query processing
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'
        }
    
    def extract_terms(self, query: str) -> List[str]:
        """Extract searchable terms from query"""
        # Remove filters from query
        clean_query = query
        for pattern in self.query_patterns.keys():
            clean_query = re.sub(pattern, '', clean_query, flags=re.IGNORECASE)
        
        # Tokenize
        terms = re.findall(r'\b\w+\b', clean_query.lower())
        
        # Remove stop words
        terms = [term for term in terms if term not in self.stop_words and len(term) > 2]
        
        return terms
    
    def extract_filters(self, query: str) -> Dict[str, List[str]]:
        """Extract filters from query"""
        filters = defaultdict(list)
        
        for pattern, filter_type in self.query_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                filters[filter_type].extend(matches)
        
        return dict(filters)
    
    def suggest_filters(self, query: str, available_filters: Dict[str, Set[str]]) -> List[SearchSuggestion]:
        """Suggest relevant filters based on query"""
        suggestions = []
        terms = self.extract_terms(query)
        
        for filter_type, values in available_filters.items():
            for value in values:
                # Score based on term relevance
                score = 0
                for term in terms:
                    if term in value.lower():
                        score += 0.8
                    elif value.lower().startswith(term):
                        score += 0.6
                    elif term in value.lower().split():
                        score += 0.4
                
                if score > 0:
                    suggestions.append(SearchSuggestion(
                        text=f"{filter_type}:{value}",
                        type="filter",
                        score=score,
                        metadata={"filter_type": filter_type, "filter_value": value}
                    ))
        
        # Sort by score
        suggestions.sort(key=lambda x: x.score, reverse=True)
        return suggestions[:10]
    
    def get_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query intent"""
        terms = self.extract_terms(query)
        filters = self.extract_filters(query)
        
        # Detect intent patterns
        intents = []
        
        if any(word in query.lower() for word in ['find', 'search', 'look for']):
            intents.append('search')
        
        if any(word in query.lower() for word in ['recent', 'latest', 'new']):
            intents.append('recent')
        
        if any(word in query.lower() for word in ['old', 'archive', 'history']):
            intents.append('historical')
        
        if filters:
            intents.append('filtered')
        
        return {
            "terms": terms,
            "filters": filters,
            "intents": intents,
            "complexity": len(terms) + len(filters)
        }

class SuggestionEngine:
    """Generate search suggestions and autocomplete"""
    
    def __init__(self, db_path: str = "suggestions.db"):
        # Query history and popularity
        self.query_history: List[Dict[str, Any]] = []
        self.popular_queries = Counter()
        self.popular_terms = Counter()
        self.trending_queries = Counter()
        
        # Available filters and values
        self.available_filters: Dict[str, Set[str]] = defaultdict(set)
        
        # Query analyzer
        self.analyzer = QueryAnalyzer()
        
        # Database persistence
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Trie for fast autocomplete
        self.autocomplete_trie = {}
        self._build_autocomplete_trie()
    
    def _init_database(self):
        """Initialize database for suggestions"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            
            # Query history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    user_id TEXT,
                    results_count INTEGER,
                    timestamp REAL NOT NULL,
                    execution_time_ms REAL,
                    INDEX(query),
                    INDEX(user_id),
                    INDEX(timestamp)
                )
            """)
            
            # Popular queries table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS popular_queries (
                    query TEXT PRIMARY KEY,
                    count INTEGER NOT NULL,
                    last_used REAL NOT NULL
                )
            """)
            
            conn.commit()
            conn.close()
    
    def record_query(self, query: str, user_id: str = None, results_count: int = 0, execution_time_ms: float = 0):
        """Record query for suggestion generation"""
        query_record = {
            "id": str(uuid.uuid4()),
            "query": query,
            "user_id": user_id,
            "results_count": results_count,
            "timestamp": time.time(),
            "execution_time_ms": execution_time_ms
        }
        
        self.query_history.append(query_record)
        self.popular_queries[query.lower()] += 1
        
        # Extract and count terms
        terms = self.analyzer.extract_terms(query)
        for term in terms:
            self.popular_terms[term] += 1
        
        # Update trending (last hour)
        current_time = time.time()
        if current_time - query_record["timestamp"] < 3600:
            self.trending_queries[query.lower()] += 1
        
        # Persist to database
        self._persist_query(query_record)
        
        # Update autocomplete trie
        self._update_autocomplete_trie(query)
    
    def _persist_query(self, query_record: Dict[str, Any]):
        """Persist query to database"""
        def _db_insert():
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    INSERT INTO query_history 
                    (id, query, user_id, results_count, timestamp, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    query_record["id"],
                    query_record["query"],
                    query_record["user_id"],
                    query_record["results_count"],
                    query_record["timestamp"],
                    query_record["execution_time_ms"]
                ))
                
                # Update popular queries
                conn.execute("""
                    INSERT OR REPLACE INTO popular_queries (query, count, last_used)
                    VALUES (?, COALESCE((SELECT count + 1 FROM popular_queries WHERE query = ?), 1), ?)
                """, (query_record["query"].lower(), query_record["query"].lower(), query_record["timestamp"]))
                
                conn.commit()
                conn.close()
        
        # Run in background
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(_db_insert)
    
    def _build_autocomplete_trie(self):
        """Build trie for autocomplete"""
        # Load popular queries from database
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("""
                    SELECT query, count FROM popular_queries 
                    ORDER BY count DESC LIMIT 10000
                """)
                
                for query, count in cursor.fetchall():
                    self._insert_trie(query, count)
                
                conn.close()
        except sqlite3.Error:
            pass  # Database might not exist yet
    
    def _update_autocomplete_trie(self, query: str):
        """Update autocomplete trie with new query"""
        count = self.popular_queries[query.lower()]
        self._insert_trie(query, count)
    
    def _insert_trie(self, word: str, count: int):
        """Insert word into autocomplete trie"""
        node = self.autocomplete_trie
        word = word.lower()
        
        for char in word:
            if char not in node:
                node[char] = {}
            node = node[char]
        
        node['_count'] = count
        node['_word'] = word
    
    def _search_trie(self, prefix: str, limit: int = 10) -> List[Tuple[str, int]]:
        """Search autocomplete trie for prefix"""
        node = self.autocomplete_trie
        prefix = prefix.lower()
        
        # Navigate to prefix
        for char in prefix:
            if char not in node:
                return []
            node = node[char]
        
        # Collect completions
        results = []
        self._collect_completions(node, results, limit)
        
        # Sort by count
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]
    
    def _collect_completions(self, node: Dict, results: List, limit: int):
        """Collect completions from trie node"""
        if len(results) >= limit:
            return
        
        if '_word' in node:
            results.append((node['_word'], node['_count']))
        
        for key, child_node in node.items():
            if not key.startswith('_'):
                self._collect_completions(child_node, results, limit)
    
    def get_autocomplete(self, prefix: str, limit: int = 10) -> List[AutocompleteResult]:
        """Get autocomplete suggestions"""
        if len(prefix) < 2:
            return []
        
        # Get from trie
        trie_results = self._search_trie(prefix, limit)
        
        # Convert to AutocompleteResult
        suggestions = []
        for query, count in trie_results:
            # Find highlight positions
            prefix_lower = prefix.lower()
            query_lower = query.lower()
            start_pos = query_lower.find(prefix_lower)
            
            highlight_positions = []
            if start_pos != -1:
                highlight_positions = [(start_pos, start_pos + len(prefix))]
            
            suggestions.append(AutocompleteResult(
                suggestion=query,
                type="query",
                score=float(count),
                highlight_positions=highlight_positions,
                metadata={"popularity": count}
            ))
        
        return suggestions
    
    def get_suggestions(self, query: str, user_id: str = None, limit: int = 10) -> List[SearchSuggestion]:
        """Get search suggestions"""
        suggestions = []
        
        # Query completion suggestions
        if len(query) >= 2:
            autocomplete = self.get_autocomplete(query, 5)
            for ac in autocomplete[:3]:  # Top 3 autocomplete
                suggestions.append(SearchSuggestion(
                    text=ac.suggestion,
                    type="completion",
                    score=ac.score / 100,  # Normalize score
                    metadata=ac.metadata
                ))
        
        # Filter suggestions
        filter_suggestions = self.analyzer.suggest_filters(query, self.available_filters)
        suggestions.extend(filter_suggestions[:3])
        
        # Popular query suggestions (similar queries)
        similar_queries = self._get_similar_queries(query, 3)
        for similar_query, score in similar_queries:
            suggestions.append(SearchSuggestion(
                text=similar_query,
                type="similar",
                score=score,
                metadata={"type": "similar_query"}
            ))
        
        # Trending queries
        trending = self._get_trending_queries(3)
        for trending_query, count in trending:
            if query.lower() not in trending_query:  # Don't suggest same query
                suggestions.append(SearchSuggestion(
                    text=trending_query,
                    type="trending",
                    score=0.5,
                    metadata={"trend_count": count}
                ))
        
        # User's recent queries (if user_id provided)
        if user_id:
            recent_queries = self._get_user_recent_queries(user_id, 2)
            for recent_query in recent_queries:
                if recent_query.lower() != query.lower():
                    suggestions.append(SearchSuggestion(
                        text=recent_query,
                        type="recent",
                        score=0.3,
                        metadata={"type": "recent_query"}
                    ))
        
        # Sort by score and deduplicate
        unique_suggestions = {}
        for suggestion in suggestions:
            key = suggestion.text.lower()
            if key not in unique_suggestions or unique_suggestions[key].score < suggestion.score:
                unique_suggestions[key] = suggestion
        
        final_suggestions = list(unique_suggestions.values())
        final_suggestions.sort(key=lambda x: x.score, reverse=True)
        
        return final_suggestions[:limit]
    
    def _get_similar_queries(self, query: str, limit: int) -> List[Tuple[str, float]]:
        """Get queries similar to the given query"""
        query_terms = set(self.analyzer.extract_terms(query))
        similar_queries = []
        
        for popular_query, count in self.popular_queries.most_common(100):
            if popular_query == query.lower():
                continue
            
            # Calculate term overlap
            popular_terms = set(self.analyzer.extract_terms(popular_query))
            
            if not popular_terms:
                continue
            
            # Jaccard similarity
            intersection = len(query_terms.intersection(popular_terms))
            union = len(query_terms.union(popular_terms))
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.2:  # Minimum similarity threshold
                    similar_queries.append((popular_query, similarity))
        
        similar_queries.sort(key=lambda x: x[1], reverse=True)
        return similar_queries[:limit]
    
    def _get_trending_queries(self, limit: int) -> List[Tuple[str, int]]:
        """Get trending queries from last hour"""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Count queries from last hour
        recent_trending = Counter()
        for query_record in self.query_history:
            if query_record["timestamp"] >= hour_ago:
                recent_trending[query_record["query"].lower()] += 1
        
        return recent_trending.most_common(limit)
    
    def _get_user_recent_queries(self, user_id: str, limit: int) -> List[str]:
        """Get user's recent queries"""
        user_queries = []
        for query_record in reversed(self.query_history):  # Most recent first
            if query_record["user_id"] == user_id:
                query = query_record["query"]
                if query not in user_queries:
                    user_queries.append(query)
                    if len(user_queries) >= limit:
                        break
        
        return user_queries
    
    def update_available_filters(self, filters: Dict[str, Set[str]]):
        """Update available filter values"""
        for filter_type, values in filters.items():
            self.available_filters[filter_type].update(values)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get suggestion engine statistics"""
        return {
            "total_queries": len(self.query_history),
            "unique_queries": len(self.popular_queries),
            "unique_terms": len(self.popular_terms),
            "trending_queries": len(self.trending_queries),
            "autocomplete_entries": len(self.autocomplete_trie),
            "available_filters": {k: len(v) for k, v in self.available_filters.items()}
        }

class SavedSearchManager:
    """Manage saved searches and search alerts"""
    
    def __init__(self, db_path: str = "saved_searches.db"):
        self.saved_searches: Dict[str, SavedSearch] = {}
        self.user_searches: Dict[str, List[str]] = defaultdict(list)
        
        # Database persistence
        self.db_path = db_path
        self.db_lock = threading.Lock()
        self._init_database()
        
        # Load saved searches
        self._load_saved_searches()
    
    def _init_database(self):
        """Initialize database for saved searches"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    query TEXT NOT NULL,
                    filters TEXT,
                    facets TEXT,
                    alert_enabled BOOLEAN DEFAULT FALSE,
                    alert_frequency TEXT DEFAULT 'daily',
                    created_at REAL NOT NULL,
                    last_executed REAL DEFAULT 0,
                    execution_count INTEGER DEFAULT 0,
                    is_public BOOLEAN DEFAULT FALSE,
                    tags TEXT,
                    INDEX(user_id),
                    INDEX(is_public)
                )
            """)
            conn.commit()
            conn.close()
    
    def _load_saved_searches(self):
        """Load saved searches from database"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.execute("SELECT * FROM saved_searches")
                
                for row in cursor.fetchall():
                    saved_search = SavedSearch(
                        id=row[0],
                        user_id=row[1],
                        name=row[2],
                        query=row[3],
                        filters=json.loads(row[4]) if row[4] else {},
                        facets=json.loads(row[5]) if row[5] else [],
                        alert_enabled=bool(row[6]),
                        alert_frequency=row[7],
                        created_at=row[8],
                        last_executed=row[9],
                        execution_count=row[10],
                        is_public=bool(row[11]),
                        tags=json.loads(row[12]) if row[12] else []
                    )
                    
                    self.saved_searches[saved_search.id] = saved_search
                    self.user_searches[saved_search.user_id].append(saved_search.id)
                
                conn.close()
                logger.info(f"Loaded {len(self.saved_searches)} saved searches")
                
        except sqlite3.Error as e:
            logger.error(f"Error loading saved searches: {e}")
    
    def save_search(self, user_id: str, name: str, query: str, filters: Dict[str, Any] = None,
                   facets: List[str] = None, alert_enabled: bool = False,
                   alert_frequency: str = "daily", is_public: bool = False,
                   tags: List[str] = None) -> SavedSearch:
        """Save a search configuration"""
        saved_search = SavedSearch(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            query=query,
            filters=filters or {},
            facets=facets or [],
            alert_enabled=alert_enabled,
            alert_frequency=alert_frequency,
            is_public=is_public,
            tags=tags or []
        )
        
        self.saved_searches[saved_search.id] = saved_search
        self.user_searches[user_id].append(saved_search.id)
        
        # Persist to database
        self._persist_saved_search(saved_search)
        
        logger.info(f"Saved search '{name}' for user {user_id}")
        return saved_search
    
    def _persist_saved_search(self, saved_search: SavedSearch):
        """Persist saved search to database"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO saved_searches 
                (id, user_id, name, query, filters, facets, alert_enabled, alert_frequency,
                 created_at, last_executed, execution_count, is_public, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                saved_search.id,
                saved_search.user_id,
                saved_search.name,
                saved_search.query,
                json.dumps(saved_search.filters),
                json.dumps(saved_search.facets),
                saved_search.alert_enabled,
                saved_search.alert_frequency,
                saved_search.created_at,
                saved_search.last_executed,
                saved_search.execution_count,
                saved_search.is_public,
                json.dumps(saved_search.tags)
            ))
            conn.commit()
            conn.close()
    
    def get_user_searches(self, user_id: str) -> List[SavedSearch]:
        """Get all saved searches for a user"""
        search_ids = self.user_searches.get(user_id, [])
        return [self.saved_searches[search_id] for search_id in search_ids if search_id in self.saved_searches]
    
    def get_saved_search(self, search_id: str) -> Optional[SavedSearch]:
        """Get saved search by ID"""
        return self.saved_searches.get(search_id)
    
    def update_saved_search(self, search_id: str, **updates) -> bool:
        """Update saved search"""
        if search_id not in self.saved_searches:
            return False
        
        saved_search = self.saved_searches[search_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(saved_search, key):
                setattr(saved_search, key, value)
        
        # Persist changes
        self._persist_saved_search(saved_search)
        
        return True
    
    def delete_saved_search(self, search_id: str, user_id: str = None) -> bool:
        """Delete saved search"""
        if search_id not in self.saved_searches:
            return False
        
        saved_search = self.saved_searches[search_id]
        
        # Check ownership if user_id provided
        if user_id and saved_search.user_id != user_id:
            return False
        
        # Remove from memory
        del self.saved_searches[search_id]
        if saved_search.user_id in self.user_searches:
            self.user_searches[saved_search.user_id].remove(search_id)
        
        # Remove from database
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
            conn.commit()
            conn.close()
        
        return True
    
    def record_execution(self, search_id: str):
        """Record execution of saved search"""
        if search_id in self.saved_searches:
            saved_search = self.saved_searches[search_id]
            saved_search.last_executed = time.time()
            saved_search.execution_count += 1
            
            # Update in database
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                conn.execute("""
                    UPDATE saved_searches 
                    SET last_executed = ?, execution_count = ?
                    WHERE id = ?
                """, (saved_search.last_executed, saved_search.execution_count, search_id))
                conn.commit()
                conn.close()
    
    def get_public_searches(self, limit: int = 50) -> List[SavedSearch]:
        """Get public saved searches"""
        public_searches = [search for search in self.saved_searches.values() if search.is_public]
        public_searches.sort(key=lambda x: x.execution_count, reverse=True)
        return public_searches[:limit]
    
    def get_searches_needing_alerts(self) -> List[SavedSearch]:
        """Get saved searches that need alert execution"""
        current_time = time.time()
        searches_needing_alerts = []
        
        for saved_search in self.saved_searches.values():
            if not saved_search.alert_enabled:
                continue
            
            # Check if alert should be triggered based on frequency
            time_since_last = current_time - saved_search.last_executed
            
            should_alert = False
            if saved_search.alert_frequency == "immediate":
                should_alert = True
            elif saved_search.alert_frequency == "hourly" and time_since_last >= 3600:
                should_alert = True
            elif saved_search.alert_frequency == "daily" and time_since_last >= 86400:
                should_alert = True
            elif saved_search.alert_frequency == "weekly" and time_since_last >= 604800:
                should_alert = True
            
            if should_alert:
                searches_needing_alerts.append(saved_search)
        
        return searches_needing_alerts
    
    def get_stats(self) -> Dict[str, Any]:
        """Get saved search statistics"""
        total_searches = len(self.saved_searches)
        public_searches = sum(1 for s in self.saved_searches.values() if s.is_public)
        alert_enabled = sum(1 for s in self.saved_searches.values() if s.alert_enabled)
        
        alert_frequencies = Counter(s.alert_frequency for s in self.saved_searches.values() if s.alert_enabled)
        
        return {
            "total_saved_searches": total_searches,
            "public_searches": public_searches,
            "alert_enabled_searches": alert_enabled,
            "alert_frequencies": dict(alert_frequencies),
            "total_users": len(self.user_searches),
            "avg_searches_per_user": total_searches / max(len(self.user_searches), 1)
        }