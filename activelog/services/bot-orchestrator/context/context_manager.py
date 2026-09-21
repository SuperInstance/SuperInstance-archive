import asyncio
import logging
import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import sqlite3
import threading
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle

logger = logging.getLogger(__name__)

class ContextType(Enum):
    SYSTEM_STATE = "system_state"
    TASK_CONTEXT = "task_context"
    CONVERSATION = "conversation"
    CODE_CONTEXT = "code_context"
    KNOWLEDGE_BASE = "knowledge_base"
    ERROR_CONTEXT = "error_context"

class ContextPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    ARCHIVAL = 5

@dataclass
class ContextItem:
    id: str
    type: ContextType
    priority: ContextPriority
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    relevance_score: float = 1.0
    size_bytes: int = 0
    expires_at: Optional[datetime] = None
    dependencies: Set[str] = field(default_factory=set)
    
    def __post_init__(self):
        self.size_bytes = len(self.content.encode('utf-8'))

@dataclass
class ContextSummary:
    id: str
    original_context_ids: List[str]
    summary_content: str
    compression_ratio: float
    created_at: datetime = field(default_factory=datetime.now)
    summary_method: str = "ai_summarization"
    reliability_score: float = 0.95

class SmartSummarizer:
    def __init__(self, claude_api):
        self.claude_api = claude_api
        self.summarization_strategies = {
            "extractive": self._extractive_summary,
            "abstractive": self._abstractive_summary,
            "hierarchical": self._hierarchical_summary,
            "topic_based": self._topic_based_summary
        }
        
        # TF-IDF vectorizer for extractive summarization
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    async def summarize_context(self, context_items: List[ContextItem], 
                              target_length: int = 2000,
                              strategy: str = "abstractive") -> ContextSummary:
        """Intelligently summarize context items"""
        
        if not context_items:
            return ContextSummary(
                id=f"empty_summary_{int(time.time())}",
                original_context_ids=[],
                summary_content="No context available.",
                compression_ratio=1.0
            )
        
        # Sort by priority and relevance
        sorted_items = sorted(context_items, 
                            key=lambda x: (x.priority.value, -x.relevance_score))
        
        # Apply summarization strategy
        if strategy in self.summarization_strategies:
            summary_func = self.summarization_strategies[strategy]
            summary_content = await summary_func(sorted_items, target_length)
        else:
            summary_content = await self._abstractive_summary(sorted_items, target_length)
        
        original_size = sum(item.size_bytes for item in context_items)
        summary_size = len(summary_content.encode('utf-8'))
        compression_ratio = original_size / max(summary_size, 1)
        
        return ContextSummary(
            id=f"summary_{hashlib.md5(summary_content.encode()).hexdigest()[:8]}",
            original_context_ids=[item.id for item in context_items],
            summary_content=summary_content,
            compression_ratio=compression_ratio,
            summary_method=strategy
        )
    
    async def _extractive_summary(self, context_items: List[ContextItem], 
                                target_length: int) -> str:
        """Extract most important sentences"""
        
        # Combine all content
        all_text = "\n\n".join([item.content for item in context_items])
        sentences = all_text.split('. ')
        
        if len(sentences) <= 3:
            return all_text[:target_length]
        
        try:
            # Calculate TF-IDF scores for sentences
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(sentences)
            sentence_scores = tfidf_matrix.sum(axis=1).A1
            
            # Select top sentences based on scores
            top_indices = np.argsort(sentence_scores)[::-1]
            
            selected_sentences = []
            current_length = 0
            
            for idx in top_indices:
                sentence = sentences[idx].strip()
                if current_length + len(sentence) <= target_length:
                    selected_sentences.append((idx, sentence))
                    current_length += len(sentence)
                else:
                    break
            
            # Sort by original order
            selected_sentences.sort(key=lambda x: x[0])
            return '. '.join([sent[1] for sent in selected_sentences]) + '.'
            
        except Exception as e:
            logger.error(f"Extractive summarization failed: {e}")
            return all_text[:target_length]
    
    async def _abstractive_summary(self, context_items: List[ContextItem], 
                                 target_length: int) -> str:
        """Use AI to create abstractive summary"""
        
        # Prioritize content by type and priority
        prioritized_content = []
        
        for item in context_items:
            prefix = f"[{item.type.value.upper()}]"
            if item.priority == ContextPriority.CRITICAL:
                prefix = f"🔥 {prefix}"
            elif item.priority == ContextPriority.HIGH:
                prefix = f"⚡ {prefix}"
            
            prioritized_content.append(f"{prefix} {item.content}")
        
        full_content = "\n\n".join(prioritized_content)
        
        # If content is already small enough, return as-is
        if len(full_content) <= target_length:
            return full_content
        
        summarization_prompt = f"""
        Please create a comprehensive summary of the following context information.
        Target length: approximately {target_length} characters.
        
        Focus on:
        1. Critical information (marked with 🔥)
        2. High priority information (marked with ⚡)
        3. Key relationships and dependencies
        4. Actionable information
        5. Current system state
        
        Context to summarize:
        {full_content}
        
        Summary:
        """
        
        try:
            summary = await self.claude_api.complete(
                summarization_prompt, 
                max_tokens=min(target_length // 4, 2000)
            )
            return summary.strip()
        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return self._fallback_summary(context_items, target_length)
    
    async def _hierarchical_summary(self, context_items: List[ContextItem], 
                                  target_length: int) -> str:
        """Create hierarchical summary by context type"""
        
        # Group by context type
        type_groups = defaultdict(list)
        for item in context_items:
            type_groups[item.type].append(item)
        
        summaries = []
        remaining_length = target_length
        
        # Prioritize context types
        type_priority = {
            ContextType.SYSTEM_STATE: 1,
            ContextType.TASK_CONTEXT: 2,
            ContextType.ERROR_CONTEXT: 3,
            ContextType.CODE_CONTEXT: 4,
            ContextType.CONVERSATION: 5,
            ContextType.KNOWLEDGE_BASE: 6
        }
        
        sorted_types = sorted(type_groups.keys(), 
                            key=lambda x: type_priority.get(x, 10))
        
        for context_type in sorted_types:
            if remaining_length <= 0:
                break
            
            items = type_groups[context_type]
            section_length = min(remaining_length // len(sorted_types), 
                               remaining_length)
            
            section_summary = await self._summarize_section(items, section_length)
            summaries.append(f"## {context_type.value.title()}\n{section_summary}")
            
            remaining_length -= len(section_summary)
        
        return "\n\n".join(summaries)
    
    async def _topic_based_summary(self, context_items: List[ContextItem], 
                                 target_length: int) -> str:
        """Create summary organized by topics/tags"""
        
        # Group by tags
        tag_groups = defaultdict(list)
        untagged = []
        
        for item in context_items:
            if item.tags:
                for tag in item.tags:
                    tag_groups[tag].append(item)
            else:
                untagged.append(item)
        
        summaries = []
        remaining_length = target_length
        
        # Summarize tagged content
        for tag, items in tag_groups.items():
            if remaining_length <= 0:
                break
            
            section_length = min(remaining_length // max(len(tag_groups), 1), 
                               remaining_length)
            section_summary = await self._summarize_section(items, section_length)
            summaries.append(f"**{tag.title()}**: {section_summary}")
            remaining_length -= len(section_summary)
        
        # Add untagged content if space remains
        if untagged and remaining_length > 100:
            untagged_summary = await self._summarize_section(untagged, remaining_length)
            summaries.append(f"**General**: {untagged_summary}")
        
        return "\n\n".join(summaries)
    
    async def _summarize_section(self, items: List[ContextItem], 
                               max_length: int) -> str:
        """Summarize a section of context items"""
        
        if not items:
            return ""
        
        # Sort by priority and relevance
        sorted_items = sorted(items, 
                            key=lambda x: (x.priority.value, -x.relevance_score))
        
        # Take most important items that fit
        selected_content = []
        current_length = 0
        
        for item in sorted_items:
            if current_length + item.size_bytes <= max_length:
                selected_content.append(item.content)
                current_length += item.size_bytes
            else:
                # Try to fit a truncated version
                remaining = max_length - current_length
                if remaining > 100:  # Only if meaningful space remains
                    truncated = item.content[:remaining-3] + "..."
                    selected_content.append(truncated)
                break
        
        return " | ".join(selected_content)
    
    def _fallback_summary(self, context_items: List[ContextItem], 
                         target_length: int) -> str:
        """Simple fallback summarization when AI fails"""
        
        # Just concatenate highest priority items
        sorted_items = sorted(context_items, 
                            key=lambda x: (x.priority.value, -x.relevance_score))
        
        summary_parts = []
        current_length = 0
        
        for item in sorted_items:
            if current_length + item.size_bytes <= target_length:
                summary_parts.append(f"[{item.type.value}] {item.content}")
                current_length += item.size_bytes
            else:
                # Truncate last item
                remaining = target_length - current_length
                if remaining > 50:
                    truncated = item.content[:remaining-3] + "..."
                    summary_parts.append(f"[{item.type.value}] {truncated}")
                break
        
        return "\n\n".join(summary_parts)

class RelevanceFilter:
    def __init__(self):
        self.keyword_weights = {
            "error": 2.0, "failed": 2.0, "critical": 2.0,
            "task": 1.5, "function": 1.5, "variable": 1.3,
            "config": 1.2, "setting": 1.2, "parameter": 1.2
        }
    
    def calculate_relevance(self, context_item: ContextItem, 
                          task_description: str, 
                          current_context: str = "") -> float:
        """Calculate relevance score for a context item"""
        
        base_score = 1.0
        
        # Priority boost
        priority_boost = {
            ContextPriority.CRITICAL: 2.0,
            ContextPriority.HIGH: 1.5,
            ContextPriority.MEDIUM: 1.0,
            ContextPriority.LOW: 0.7,
            ContextPriority.ARCHIVAL: 0.3
        }
        base_score *= priority_boost.get(context_item.priority, 1.0)
        
        # Recency boost
        age_hours = (datetime.now() - context_item.created_at).total_seconds() / 3600
        if age_hours < 1:
            base_score *= 1.5
        elif age_hours < 24:
            base_score *= 1.2
        elif age_hours > 168:  # 1 week
            base_score *= 0.8
        
        # Access frequency boost
        if context_item.access_count > 5:
            base_score *= 1.3
        elif context_item.access_count > 10:
            base_score *= 1.5
        
        # Content relevance
        content_score = self._calculate_content_relevance(
            context_item.content, task_description, current_context
        )
        base_score *= content_score
        
        # Type relevance for current task
        type_relevance = self._get_type_relevance(context_item.type, task_description)
        base_score *= type_relevance
        
        return min(base_score, 10.0)  # Cap at 10.0
    
    def _calculate_content_relevance(self, content: str, 
                                   task_description: str, 
                                   current_context: str) -> float:
        """Calculate content-based relevance"""
        
        content_lower = content.lower()
        task_lower = task_description.lower()
        context_lower = current_context.lower()
        
        # Keyword matching
        task_keywords = set(task_lower.split())
        context_keywords = set(context_lower.split()) if current_context else set()
        content_keywords = set(content_lower.split())
        
        # Calculate overlap scores
        task_overlap = len(task_keywords.intersection(content_keywords)) / max(len(task_keywords), 1)
        context_overlap = len(context_keywords.intersection(content_keywords)) / max(len(context_keywords), 1) if context_keywords else 0
        
        # Weighted keyword scoring
        weighted_score = 0
        for keyword, weight in self.keyword_weights.items():
            if keyword in content_lower:
                if keyword in task_lower:
                    weighted_score += weight * 2  # Double if in both
                else:
                    weighted_score += weight
        
        # Combine scores
        relevance_score = (
            task_overlap * 2.0 +      # Task relevance most important
            context_overlap * 1.5 +   # Context relevance
            min(weighted_score, 3.0)  # Keyword bonus (capped)
        ) / 4.5
        
        return max(0.1, min(2.0, relevance_score))  # Bounded between 0.1 and 2.0
    
    def _get_type_relevance(self, context_type: ContextType, 
                          task_description: str) -> float:
        """Get type-based relevance multiplier"""
        
        task_lower = task_description.lower()
        
        # Task-specific type relevance
        type_keywords = {
            ContextType.SYSTEM_STATE: ["status", "state", "system", "health"],
            ContextType.TASK_CONTEXT: ["task", "job", "work", "execute"],
            ContextType.CONVERSATION: ["conversation", "chat", "dialogue"],
            ContextType.CODE_CONTEXT: ["code", "function", "class", "method", "variable"],
            ContextType.KNOWLEDGE_BASE: ["knowledge", "documentation", "reference"],
            ContextType.ERROR_CONTEXT: ["error", "exception", "failure", "bug"]
        }
        
        keywords = type_keywords.get(context_type, [])
        if any(keyword in task_lower for keyword in keywords):
            return 1.5
        
        # Default type priorities
        default_relevance = {
            ContextType.SYSTEM_STATE: 1.3,
            ContextType.TASK_CONTEXT: 1.4,
            ContextType.ERROR_CONTEXT: 1.2,
            ContextType.CODE_CONTEXT: 1.1,
            ContextType.CONVERSATION: 0.9,
            ContextType.KNOWLEDGE_BASE: 0.8
        }
        
        return default_relevance.get(context_type, 1.0)

class ContextStorage:
    def __init__(self, db_path: str = "context_storage.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for context storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_items (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    created_at TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    relevance_score REAL DEFAULT 1.0,
                    size_bytes INTEGER,
                    expires_at TIMESTAMP,
                    dependencies TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_summaries (
                    id TEXT PRIMARY KEY,
                    original_context_ids TEXT NOT NULL,
                    summary_content TEXT NOT NULL,
                    compression_ratio REAL,
                    created_at TIMESTAMP,
                    summary_method TEXT,
                    reliability_score REAL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_type_priority 
                ON context_items (type, priority)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_context_created_at 
                ON context_items (created_at)
            """)
    
    def store_context(self, item: ContextItem) -> bool:
        """Store a context item"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO context_items 
                        (id, type, priority, content, metadata, tags, created_at, 
                         last_accessed, access_count, relevance_score, size_bytes, 
                         expires_at, dependencies)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        item.id, item.type.value, item.priority.value, item.content,
                        json.dumps(item.metadata), json.dumps(list(item.tags)),
                        item.created_at, item.last_accessed, item.access_count,
                        item.relevance_score, item.size_bytes, item.expires_at,
                        json.dumps(list(item.dependencies))
                    ))
                return True
        except Exception as e:
            logger.error(f"Failed to store context item {item.id}: {e}")
            return False
    
    def get_context(self, item_id: str) -> Optional[ContextItem]:
        """Retrieve a context item by ID"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT * FROM context_items WHERE id = ?", (item_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        # Update access count
                        conn.execute("""
                            UPDATE context_items 
                            SET access_count = access_count + 1, last_accessed = ?
                            WHERE id = ?
                        """, (datetime.now(), item_id))
                        
                        return self._row_to_context_item(row)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve context item {item_id}: {e}")
            return None
    
    def search_context(self, filters: Dict[str, Any], 
                      limit: int = 100) -> List[ContextItem]:
        """Search context items with filters"""
        try:
            with self.lock:
                query = "SELECT * FROM context_items WHERE 1=1"
                params = []
                
                if 'type' in filters:
                    query += " AND type = ?"
                    params.append(filters['type'])
                
                if 'priority' in filters:
                    query += " AND priority <= ?"
                    params.append(filters['priority'])
                
                if 'keywords' in filters:
                    query += " AND content LIKE ?"
                    params.append(f"%{filters['keywords']}%")
                
                if 'after_date' in filters:
                    query += " AND created_at >= ?"
                    params.append(filters['after_date'])
                
                if 'tags' in filters:
                    for tag in filters['tags']:
                        query += " AND tags LIKE ?"
                        params.append(f'%"{tag}"%')
                
                query += " ORDER BY priority, relevance_score DESC, created_at DESC"
                query += f" LIMIT {limit}"
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()
                    
                    return [self._row_to_context_item(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Context search failed: {e}")
            return []
    
    def store_summary(self, summary: ContextSummary) -> bool:
        """Store a context summary"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO context_summaries
                        (id, original_context_ids, summary_content, compression_ratio,
                         created_at, summary_method, reliability_score)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        summary.id, json.dumps(summary.original_context_ids),
                        summary.summary_content, summary.compression_ratio,
                        summary.created_at, summary.summary_method,
                        summary.reliability_score
                    ))
                return True
        except Exception as e:
            logger.error(f"Failed to store summary {summary.id}: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Clean up expired context items"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute("""
                        DELETE FROM context_items 
                        WHERE expires_at IS NOT NULL AND expires_at < ?
                    """, (datetime.now(),))
                    
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"Context cleanup failed: {e}")
            return 0
    
    def _row_to_context_item(self, row) -> ContextItem:
        """Convert database row to ContextItem"""
        return ContextItem(
            id=row[0],
            type=ContextType(row[1]),
            priority=ContextPriority(row[2]),
            content=row[3],
            metadata=json.loads(row[4]) if row[4] else {},
            tags=set(json.loads(row[5])) if row[5] else set(),
            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            last_accessed=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
            access_count=row[8] or 0,
            relevance_score=row[9] or 1.0,
            size_bytes=row[10] or 0,
            expires_at=datetime.fromisoformat(row[11]) if row[11] else None,
            dependencies=set(json.loads(row[12])) if row[12] else set()
        )

class ContextManager:
    def __init__(self, claude_api, max_context_tokens: int = 150000):
        self.claude_api = claude_api
        self.max_context_tokens = max_context_tokens
        self.storage = ContextStorage()
        self.summarizer = SmartSummarizer(claude_api)
        self.relevance_filter = RelevanceFilter()
        
        # Memory optimization settings
        self.min_compression_ratio = 3.0
        self.preferred_compression_ratio = 5.0
        self.cache_size = 1000
        
        # In-memory cache for frequently accessed items
        self.context_cache = {}
        self.cache_access_order = deque(maxlen=self.cache_size)
        
        # Background maintenance
        self.maintenance_interval = 3600  # 1 hour
        self.maintenance_task = None
        self.running = False
    
    async def start(self):
        """Start the context manager"""
        self.running = True
        self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info("Context Manager started")
    
    async def stop(self):
        """Stop the context manager"""
        self.running = False
        if self.maintenance_task:
            self.maintenance_task.cancel()
            try:
                await self.maintenance_task
            except asyncio.CancelledError:
                pass
        logger.info("Context Manager stopped")
    
    async def add_context(self, context_type: ContextType, content: str,
                         priority: ContextPriority = ContextPriority.MEDIUM,
                         tags: Set[str] = None, metadata: Dict[str, Any] = None,
                         expires_in_hours: Optional[int] = None) -> str:
        """Add new context item"""
        
        item_id = f"{context_type.value}_{hashlib.md5(content.encode()).hexdigest()[:12]}"
        
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        context_item = ContextItem(
            id=item_id,
            type=context_type,
            priority=priority,
            content=content,
            tags=tags or set(),
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        # Store in database
        success = self.storage.store_context(context_item)
        
        if success:
            # Add to cache
            self._cache_context_item(context_item)
            logger.debug(f"Added context item: {item_id}")
            return item_id
        else:
            raise Exception(f"Failed to store context item: {item_id}")
    
    async def get_optimized_context(self, task_description: str,
                                  max_tokens: Optional[int] = None,
                                  include_types: List[ContextType] = None) -> str:
        """Get optimized context for a task"""
        
        target_tokens = max_tokens or self.max_context_tokens
        target_chars = target_tokens * 4  # Rough estimate
        
        # Search for relevant context
        relevant_items = await self._find_relevant_context(
            task_description, include_types
        )
        
        if not relevant_items:
            return "No relevant context found."
        
        # Calculate total size
        total_size = sum(item.size_bytes for item in relevant_items)
        
        # If within limits, return full context
        if total_size <= target_chars:
            return self._format_context_items(relevant_items)
        
        # Need to summarize
        logger.info(f"Summarizing context: {total_size} bytes -> {target_chars} bytes")
        
        summary = await self.summarizer.summarize_context(
            relevant_items, target_chars
        )
        
        # Store summary for future use
        self.storage.store_summary(summary)
        
        return summary.summary_content
    
    async def _find_relevant_context(self, task_description: str,
                                   include_types: List[ContextType] = None) -> List[ContextItem]:
        """Find relevant context items for a task"""
        
        # Build search filters
        filters = {}
        if include_types:
            # For now, search each type separately and combine
            # (SQLite doesn't easily support IN queries with our setup)
            pass
        
        # Search recent items first
        filters['after_date'] = datetime.now() - timedelta(hours=24)
        recent_items = self.storage.search_context(filters, limit=200)
        
        # If not enough recent items, expand search
        if len(recent_items) < 50:
            filters['after_date'] = datetime.now() - timedelta(days=7)
            recent_items.extend(self.storage.search_context(filters, limit=300))
        
        # Calculate relevance scores
        scored_items = []
        for item in recent_items:
            if include_types and item.type not in include_types:
                continue
            
            relevance = self.relevance_filter.calculate_relevance(
                item, task_description
            )
            
            if relevance > 0.3:  # Minimum relevance threshold
                item.relevance_score = relevance
                scored_items.append(item)
        
        # Sort by relevance and return top items
        scored_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Limit to top 100 most relevant items
        return scored_items[:100]
    
    def _format_context_items(self, items: List[ContextItem]) -> str:
        """Format context items for presentation"""
        
        if not items:
            return "No context available."
        
        # Group by type for better organization
        type_groups = defaultdict(list)
        for item in items:
            type_groups[item.type].append(item)
        
        formatted_sections = []
        
        # Order types by importance
        type_order = [
            ContextType.SYSTEM_STATE,
            ContextType.ERROR_CONTEXT,
            ContextType.TASK_CONTEXT,
            ContextType.CODE_CONTEXT,
            ContextType.CONVERSATION,
            ContextType.KNOWLEDGE_BASE
        ]
        
        for context_type in type_order:
            if context_type not in type_groups:
                continue
            
            items_of_type = sorted(type_groups[context_type], 
                                 key=lambda x: (x.priority.value, -x.relevance_score))
            
            section_content = []
            for item in items_of_type:
                priority_marker = ""
                if item.priority == ContextPriority.CRITICAL:
                    priority_marker = "🔥 "
                elif item.priority == ContextPriority.HIGH:
                    priority_marker = "⚡ "
                
                tags_str = f" #{','.join(item.tags)}" if item.tags else ""
                
                section_content.append(f"{priority_marker}{item.content}{tags_str}")
            
            if section_content:
                section_title = f"## {context_type.value.replace('_', ' ').title()}"
                formatted_sections.append(f"{section_title}\n" + "\n".join(section_content))
        
        return "\n\n".join(formatted_sections)
    
    def _cache_context_item(self, item: ContextItem):
        """Add item to memory cache"""
        self.context_cache[item.id] = item
        
        # Maintain cache size
        if item.id in self.cache_access_order:
            self.cache_access_order.remove(item.id)
        self.cache_access_order.append(item.id)
        
        # Remove oldest items if cache is full
        while len(self.context_cache) > self.cache_size:
            oldest_id = self.cache_access_order.popleft()
            self.context_cache.pop(oldest_id, None)
    
    async def _maintenance_loop(self):
        """Background maintenance tasks"""
        while self.running:
            try:
                # Clean up expired items
                expired_count = self.storage.cleanup_expired()
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired context items")
                
                # Update relevance scores based on access patterns
                await self._update_relevance_scores()
                
                # Clean up old summaries
                await self._cleanup_old_summaries()
                
                await asyncio.sleep(self.maintenance_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Context maintenance error: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    async def _update_relevance_scores(self):
        """Update relevance scores based on access patterns"""
        try:
            # This would analyze access patterns and update scores
            # For now, we'll just implement a simple decay
            
            # Items not accessed recently get lower scores
            decay_date = datetime.now() - timedelta(days=3)
            
            with sqlite3.connect(self.storage.db_path) as conn:
                conn.execute("""
                    UPDATE context_items 
                    SET relevance_score = relevance_score * 0.9
                    WHERE last_accessed < ? AND relevance_score > 0.1
                """, (decay_date,))
            
        except Exception as e:
            logger.error(f"Failed to update relevance scores: {e}")
    
    async def _cleanup_old_summaries(self):
        """Clean up old summaries"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            with sqlite3.connect(self.storage.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM context_summaries 
                    WHERE created_at < ? AND reliability_score < 0.8
                """, (cutoff_date,))
                
                if cursor.rowcount > 0:
                    logger.info(f"Cleaned up {cursor.rowcount} old summaries")
                    
        except Exception as e:
            logger.error(f"Summary cleanup failed: {e}")
    
    async def get_context_stats(self) -> Dict[str, Any]:
        """Get context management statistics"""
        try:
            with sqlite3.connect(self.storage.db_path) as conn:
                # Count items by type
                type_counts = {}
                cursor = conn.execute("""
                    SELECT type, COUNT(*) FROM context_items GROUP BY type
                """)
                for row in cursor:
                    type_counts[row[0]] = row[1]
                
                # Count items by priority
                priority_counts = {}
                cursor = conn.execute("""
                    SELECT priority, COUNT(*) FROM context_items GROUP BY priority
                """)
                for row in cursor:
                    priority_counts[row[0]] = row[1]
                
                # Total size
                cursor = conn.execute("SELECT SUM(size_bytes) FROM context_items")
                total_size = cursor.fetchone()[0] or 0
                
                # Summary count
                cursor = conn.execute("SELECT COUNT(*) FROM context_summaries")
                summary_count = cursor.fetchone()[0]
                
                return {
                    "total_items": sum(type_counts.values()),
                    "items_by_type": type_counts,
                    "items_by_priority": priority_counts,
                    "total_size_bytes": total_size,
                    "total_summaries": summary_count,
                    "cache_size": len(self.context_cache),
                    "max_context_tokens": self.max_context_tokens
                }
        
        except Exception as e:
            logger.error(f"Failed to get context stats: {e}")
            return {"error": str(e)}