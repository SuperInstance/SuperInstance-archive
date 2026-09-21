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
import git
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class ShareScope(Enum):
    PRIVATE = "private"
    BOT_LEVEL = "bot_level"
    TEAM_LEVEL = "team_level"
    GLOBAL = "global"

class InformationType(Enum):
    TASK_RESULT = "task_result"
    LEARNED_PATTERN = "learned_pattern"
    ERROR_SOLUTION = "error_solution"
    OPTIMIZATION = "optimization"
    CONFIGURATION = "configuration"
    KNOWLEDGE = "knowledge"
    CODE_SNIPPET = "code_snippet"
    BEST_PRACTICE = "best_practice"
    WARNING = "warning"

class SharePriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class SharedInformation:
    id: str
    type: InformationType
    scope: ShareScope
    priority: SharePriority
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    source_bot_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    relevance_score: float = 1.0
    version: int = 1
    parent_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "scope": self.scope.value,
            "priority": self.priority.value,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "tags": list(self.tags),
            "source_bot_id": self.source_bot_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score,
            "version": self.version,
            "parent_id": self.parent_id
        }

@dataclass
class AccessPermission:
    bot_id: str
    scope: ShareScope
    can_read: bool = True
    can_write: bool = False
    can_delete: bool = False
    granted_by: str = "system"
    granted_at: datetime = field(default_factory=datetime.now)

class InformationStore:
    def __init__(self, db_path: str = "shared_information.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for information sharing"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_information (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    source_bot_id TEXT,
                    created_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    access_count INTEGER DEFAULT 0,
                    relevance_score REAL DEFAULT 1.0,
                    version INTEGER DEFAULT 1,
                    parent_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_permissions (
                    bot_id TEXT,
                    scope TEXT,
                    can_read BOOLEAN DEFAULT TRUE,
                    can_write BOOLEAN DEFAULT FALSE,
                    can_delete BOOLEAN DEFAULT FALSE,
                    granted_by TEXT,
                    granted_at TIMESTAMP,
                    PRIMARY KEY (bot_id, scope)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT,
                    information_id TEXT,
                    action TEXT,
                    timestamp TIMESTAMP,
                    success BOOLEAN
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_info_type_scope 
                ON shared_information (type, scope)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_info_created_at 
                ON shared_information (created_at DESC)
            """)
    
    def store_information(self, info: SharedInformation) -> bool:
        """Store shared information"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO shared_information
                        (id, type, scope, priority, title, content, metadata, tags,
                         source_bot_id, created_at, expires_at, access_count,
                         relevance_score, version, parent_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        info.id, info.type.value, info.scope.value, info.priority.value,
                        info.title, info.content, json.dumps(info.metadata),
                        json.dumps(list(info.tags)), info.source_bot_id,
                        info.created_at, info.expires_at, info.access_count,
                        info.relevance_score, info.version, info.parent_id
                    ))
                return True
        except Exception as e:
            logger.error(f"Failed to store information {info.id}: {e}")
            return False
    
    def get_information(self, info_id: str, bot_id: str) -> Optional[SharedInformation]:
        """Retrieve information with access control"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    # Get the information
                    cursor = conn.execute(
                        "SELECT * FROM shared_information WHERE id = ?", (info_id,)
                    )
                    row = cursor.fetchone()
                    
                    if not row:
                        return None
                    
                    info = self._row_to_information(row)
                    
                    # Check access permissions
                    if not self._check_read_permission(bot_id, info.scope, conn):
                        self._log_access(bot_id, info_id, "read_denied", False, conn)
                        return None
                    
                    # Update access count
                    conn.execute("""
                        UPDATE shared_information 
                        SET access_count = access_count + 1
                        WHERE id = ?
                    """, (info_id,))
                    
                    self._log_access(bot_id, info_id, "read", True, conn)
                    return info
        
        except Exception as e:
            logger.error(f"Failed to retrieve information {info_id}: {e}")
            return None
    
    def search_information(self, bot_id: str, filters: Dict[str, Any], 
                         limit: int = 100) -> List[SharedInformation]:
        """Search information with access control"""
        try:
            with self.lock:
                query_parts = ["SELECT * FROM shared_information WHERE 1=1"]
                params = []
                
                # Add filters
                if 'type' in filters:
                    query_parts.append("AND type = ?")
                    params.append(filters['type'])
                
                if 'scope' in filters:
                    query_parts.append("AND scope = ?")
                    params.append(filters['scope'])
                
                if 'tags' in filters:
                    for tag in filters['tags']:
                        query_parts.append("AND tags LIKE ?")
                        params.append(f'%"{tag}"%')
                
                if 'content_search' in filters:
                    query_parts.append("AND (title LIKE ? OR content LIKE ?)")
                    search_term = f"%{filters['content_search']}%"
                    params.extend([search_term, search_term])
                
                if 'min_priority' in filters:
                    query_parts.append("AND priority >= ?")
                    params.append(filters['min_priority'])
                
                if 'after_date' in filters:
                    query_parts.append("AND created_at >= ?")
                    params.append(filters['after_date'])
                
                # Add ordering and limit
                query_parts.append("ORDER BY priority DESC, relevance_score DESC, created_at DESC")
                query_parts.append(f"LIMIT {limit}")
                
                query = " ".join(query_parts)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Filter by access permissions
                    accessible_info = []
                    for row in rows:
                        info = self._row_to_information(row)
                        if self._check_read_permission(bot_id, info.scope, conn):
                            accessible_info.append(info)
                    
                    return accessible_info
        
        except Exception as e:
            logger.error(f"Information search failed for bot {bot_id}: {e}")
            return []
    
    def _check_read_permission(self, bot_id: str, scope: ShareScope, 
                              conn: sqlite3.Connection) -> bool:
        """Check if bot has read permission for scope"""
        try:
            # System always has access
            if bot_id == "system":
                return True
            
            # Check explicit permissions
            cursor = conn.execute("""
                SELECT can_read FROM access_permissions 
                WHERE bot_id = ? AND scope = ?
            """, (bot_id, scope.value))
            
            result = cursor.fetchone()
            if result:
                return bool(result[0])
            
            # Default permissions based on scope
            if scope == ShareScope.GLOBAL:
                return True
            elif scope == ShareScope.TEAM_LEVEL:
                return True  # For now, all bots are in same team
            elif scope == ShareScope.BOT_LEVEL:
                return False  # Need explicit permission
            else:  # PRIVATE
                return False
        
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False
    
    def _log_access(self, bot_id: str, info_id: str, action: str, 
                   success: bool, conn: sqlite3.Connection):
        """Log access attempt"""
        try:
            conn.execute("""
                INSERT INTO access_log (bot_id, information_id, action, timestamp, success)
                VALUES (?, ?, ?, ?, ?)
            """, (bot_id, info_id, action, datetime.now(), success))
        except Exception as e:
            logger.error(f"Failed to log access: {e}")
    
    def _row_to_information(self, row) -> SharedInformation:
        """Convert database row to SharedInformation"""
        return SharedInformation(
            id=row[0],
            type=InformationType(row[1]),
            scope=ShareScope(row[2]),
            priority=SharePriority(row[3]),
            title=row[4],
            content=row[5],
            metadata=json.loads(row[6]) if row[6] else {},
            tags=set(json.loads(row[7])) if row[7] else set(),
            source_bot_id=row[8] or "",
            created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now(),
            expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
            access_count=row[11] or 0,
            relevance_score=row[12] or 1.0,
            version=row[13] or 1,
            parent_id=row[14]
        )

class VersionControlIntegration:
    def __init__(self, repo_path: str = "/home/activeloguser/activelog"):
        self.repo_path = repo_path
        self.shared_knowledge_dir = os.path.join(repo_path, "shared_knowledge")
        self.ensure_knowledge_directory()
        self.repo = None
        self._init_git_repo()
    
    def ensure_knowledge_directory(self):
        """Ensure shared knowledge directory exists"""
        os.makedirs(self.shared_knowledge_dir, exist_ok=True)
        
        # Create subdirectories for different types of shared information
        subdirs = [
            "patterns", "solutions", "optimizations", 
            "configurations", "snippets", "best_practices"
        ]
        
        for subdir in subdirs:
            os.makedirs(os.path.join(self.shared_knowledge_dir, subdir), exist_ok=True)
    
    def _init_git_repo(self):
        """Initialize or load existing git repository"""
        try:
            if os.path.exists(os.path.join(self.repo_path, ".git")):
                self.repo = git.Repo(self.repo_path)
            else:
                logger.warning(f"No git repository found at {self.repo_path}")
        except Exception as e:
            logger.error(f"Failed to initialize git repo: {e}")
    
    def save_knowledge_to_file(self, info: SharedInformation) -> Optional[str]:
        """Save information to version-controlled file"""
        try:
            # Determine subdirectory based on information type
            type_mapping = {
                InformationType.LEARNED_PATTERN: "patterns",
                InformationType.ERROR_SOLUTION: "solutions",
                InformationType.OPTIMIZATION: "optimizations",
                InformationType.CONFIGURATION: "configurations",
                InformationType.CODE_SNIPPET: "snippets",
                InformationType.BEST_PRACTICE: "best_practices"
            }
            
            subdir = type_mapping.get(info.type, "general")
            dir_path = os.path.join(self.shared_knowledge_dir, subdir)
            
            # Create filename
            safe_title = "".join(c for c in info.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')[:50]
            filename = f"{safe_title}_{info.id[:8]}.md"
            file_path = os.path.join(dir_path, filename)
            
            # Create markdown content
            md_content = self._create_markdown_content(info)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            logger.info(f"Saved knowledge to file: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save knowledge to file: {e}")
            return None
    
    def _create_markdown_content(self, info: SharedInformation) -> str:
        """Create markdown content for shared information"""
        md_lines = [
            f"# {info.title}\n",
            f"**Type**: {info.type.value}",
            f"**Scope**: {info.scope.value}",
            f"**Priority**: {info.priority.value}",
            f"**Source Bot**: {info.source_bot_id}",
            f"**Created**: {info.created_at.isoformat()}",
            f"**Version**: {info.version}\n"
        ]
        
        if info.tags:
            md_lines.append(f"**Tags**: {', '.join(info.tags)}\n")
        
        if info.metadata:
            md_lines.append("## Metadata\n")
            for key, value in info.metadata.items():
                md_lines.append(f"- **{key}**: {value}")
            md_lines.append("")
        
        md_lines.extend([
            "## Content\n",
            info.content,
            "\n---",
            f"*ID: {info.id}*",
            f"*Access Count: {info.access_count}*",
            f"*Relevance Score: {info.relevance_score:.2f}*"
        ])
        
        return "\n".join(md_lines)
    
    def commit_knowledge_changes(self, message: str = "Update shared knowledge") -> bool:
        """Commit changes to version control"""
        if not self.repo:
            return False
        
        try:
            # Add all files in shared_knowledge directory
            self.repo.git.add(self.shared_knowledge_dir)
            
            # Check if there are changes to commit
            if not self.repo.git.diff("--staged"):
                logger.debug("No knowledge changes to commit")
                return True
            
            # Commit changes
            self.repo.git.commit("-m", message)
            logger.info(f"Committed knowledge changes: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to commit knowledge changes: {e}")
            return False
    
    def get_knowledge_history(self, file_path: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get version history for a knowledge file"""
        if not self.repo:
            return []
        
        try:
            # Get relative path from repo root
            rel_path = os.path.relpath(file_path, self.repo_path)
            
            # Get commit history for file
            commits = list(self.repo.iter_commits(paths=rel_path, max_count=limit))
            
            history = []
            for commit in commits:
                history.append({
                    "commit_hash": commit.hexsha,
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat(),
                    "message": commit.message.strip(),
                    "summary": commit.summary
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get knowledge history: {e}")
            return []
    
    def load_knowledge_from_files(self) -> List[SharedInformation]:
        """Load shared information from version-controlled files"""
        knowledge_items = []
        
        try:
            for root, dirs, files in os.walk(self.shared_knowledge_dir):
                for file in files:
                    if file.endswith('.md'):
                        file_path = os.path.join(root, file)
                        knowledge_item = self._parse_markdown_file(file_path)
                        if knowledge_item:
                            knowledge_items.append(knowledge_item)
            
            logger.info(f"Loaded {len(knowledge_items)} knowledge items from files")
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Failed to load knowledge from files: {e}")
            return []
    
    def _parse_markdown_file(self, file_path: str) -> Optional[SharedInformation]:
        """Parse markdown file back to SharedInformation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Extract metadata from header
            title = ""
            info_type = InformationType.KNOWLEDGE
            scope = ShareScope.GLOBAL
            priority = SharePriority.MEDIUM
            source_bot_id = ""
            created_at = datetime.now()
            version = 1
            tags = set()
            metadata = {}
            info_id = ""
            
            # Parse header
            content_start = 0
            for i, line in enumerate(lines):
                if line.startswith('# '):
                    title = line[2:].strip()
                elif line.startswith('**Type**:'):
                    try:
                        info_type = InformationType(line.split(': ')[1].strip())
                    except ValueError:
                        pass
                elif line.startswith('**Scope**:'):
                    try:
                        scope = ShareScope(line.split(': ')[1].strip())
                    except ValueError:
                        pass
                elif line.startswith('**Priority**:'):
                    try:
                        priority = SharePriority[line.split(': ')[1].strip().upper()]
                    except (KeyError, ValueError):
                        pass
                elif line.startswith('**Source Bot**:'):
                    source_bot_id = line.split(': ')[1].strip()
                elif line.startswith('**Created**:'):
                    try:
                        created_at = datetime.fromisoformat(line.split(': ')[1].strip())
                    except ValueError:
                        pass
                elif line.startswith('**Tags**:'):
                    tag_str = line.split(': ')[1].strip()
                    tags = set(tag.strip() for tag in tag_str.split(',') if tag.strip())
                elif line.startswith('## Content'):
                    content_start = i + 2
                    break
                elif line.startswith('*ID: '):
                    info_id = line.replace('*ID: ', '').replace('*', '').strip()
            
            # Extract main content
            main_content_lines = []
            for i in range(content_start, len(lines)):
                if lines[i].startswith('---'):
                    break
                main_content_lines.append(lines[i])
            
            main_content = '\n'.join(main_content_lines).strip()
            
            if not info_id:
                info_id = hashlib.md5(f"{title}_{main_content}".encode()).hexdigest()[:16]
            
            return SharedInformation(
                id=info_id,
                type=info_type,
                scope=scope,
                priority=priority,
                title=title,
                content=main_content,
                tags=tags,
                metadata=metadata,
                source_bot_id=source_bot_id,
                created_at=created_at,
                version=version
            )
            
        except Exception as e:
            logger.error(f"Failed to parse markdown file {file_path}: {e}")
            return None

class InformationSharingSystem:
    def __init__(self, claude_api, enable_version_control: bool = True):
        self.claude_api = claude_api
        self.store = InformationStore()
        self.version_control = VersionControlIntegration() if enable_version_control else None
        
        # Learning and pattern detection
        self.pattern_detector = PatternDetector(claude_api)
        self.knowledge_synthesizer = KnowledgeSynthesizer(claude_api)
        
        # Caching and optimization
        self.information_cache = {}
        self.cache_max_size = 1000
        self.cache_access_order = deque(maxlen=self.cache_max_size)
        
        # Background maintenance
        self.maintenance_interval = 1800  # 30 minutes
        self.maintenance_task = None
        self.running = False
    
    async def start(self):
        """Start the information sharing system"""
        self.running = True
        
        # Load existing knowledge from version control
        if self.version_control:
            existing_knowledge = self.version_control.load_knowledge_from_files()
            for info in existing_knowledge:
                self.store.store_information(info)
        
        # Start background maintenance
        self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        
        logger.info("Information Sharing System started")
    
    async def stop(self):
        """Stop the information sharing system"""
        self.running = False
        
        if self.maintenance_task:
            self.maintenance_task.cancel()
            try:
                await self.maintenance_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Information Sharing System stopped")
    
    async def share_information(self, bot_id: str, info_type: InformationType,
                              title: str, content: str, scope: ShareScope = ShareScope.TEAM_LEVEL,
                              priority: SharePriority = SharePriority.MEDIUM,
                              tags: Set[str] = None, metadata: Dict[str, Any] = None,
                              expires_in_hours: Optional[int] = None) -> str:
        """Share information from a bot"""
        
        info_id = f"{info_type.value}_{hashlib.md5(f'{title}_{content}'.encode()).hexdigest()[:12]}"
        
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
        
        # Analyze and enhance content
        enhanced_content, detected_patterns = await self._analyze_content(content, info_type)
        
        info = SharedInformation(
            id=info_id,
            type=info_type,
            scope=scope,
            priority=priority,
            title=title,
            content=enhanced_content,
            tags=tags or set(),
            metadata=metadata or {},
            source_bot_id=bot_id,
            expires_at=expires_at
        )
        
        # Add detected patterns to metadata
        if detected_patterns:
            info.metadata["detected_patterns"] = detected_patterns
        
        # Store in database
        success = self.store.store_information(info)
        
        if success:
            # Cache the information
            self._cache_information(info)
            
            # Save to version control if enabled
            if self.version_control and info_type in [
                InformationType.LEARNED_PATTERN, InformationType.ERROR_SOLUTION,
                InformationType.OPTIMIZATION, InformationType.BEST_PRACTICE
            ]:
                file_path = self.version_control.save_knowledge_to_file(info)
                if file_path:
                    commit_message = f"Add {info_type.value}: {title}"
                    self.version_control.commit_knowledge_changes(commit_message)
            
            logger.info(f"Bot {bot_id} shared information: {title}")
            return info_id
        else:
            raise Exception(f"Failed to store information: {info_id}")
    
    async def get_relevant_information(self, bot_id: str, query: str,
                                     info_types: List[InformationType] = None,
                                     max_results: int = 20) -> List[SharedInformation]:
        """Get information relevant to a query"""
        
        # Build search filters
        filters = {
            "content_search": query,
        }
        
        if info_types:
            # Search each type separately and combine
            all_results = []
            for info_type in info_types:
                type_filters = filters.copy()
                type_filters["type"] = info_type.value
                results = self.store.search_information(bot_id, type_filters, max_results)
                all_results.extend(results)
        else:
            all_results = self.store.search_information(bot_id, filters, max_results * 2)
        
        # Score by relevance
        scored_results = []
        for info in all_results:
            relevance = self._calculate_relevance(info, query)
            scored_results.append((info, relevance))
        
        # Sort by relevance and return top results
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [info for info, score in scored_results[:max_results]]
    
    async def synthesize_knowledge(self, bot_id: str, topic: str) -> Optional[SharedInformation]:
        """Synthesize knowledge on a topic from shared information"""
        
        # Gather relevant information
        relevant_info = await self.get_relevant_information(
            bot_id, topic, max_results=50
        )
        
        if len(relevant_info) < 3:
            logger.info(f"Insufficient information to synthesize knowledge on: {topic}")
            return None
        
        # Synthesize using AI
        synthesis_result = await self.knowledge_synthesizer.synthesize(
            topic, relevant_info
        )
        
        if synthesis_result:
            # Create synthesized knowledge item
            synth_id = f"synthesis_{hashlib.md5(f'{topic}_{time.time()}'.encode()).hexdigest()[:12]}"
            
            synthesized_info = SharedInformation(
                id=synth_id,
                type=InformationType.KNOWLEDGE,
                scope=ShareScope.GLOBAL,
                priority=SharePriority.HIGH,
                title=f"Synthesized Knowledge: {topic}",
                content=synthesis_result["content"],
                tags=set(synthesis_result.get("tags", [])),
                metadata={
                    "synthesis_sources": [info.id for info in relevant_info],
                    "synthesis_confidence": synthesis_result.get("confidence", 0.8),
                    "synthesis_method": "ai_enhanced"
                },
                source_bot_id="knowledge_synthesizer"
            )
            
            # Store synthesized knowledge
            self.store.store_information(synthesized_info)
            self._cache_information(synthesized_info)
            
            logger.info(f"Synthesized knowledge on topic: {topic}")
            return synthesized_info
        
        return None
    
    async def _analyze_content(self, content: str, info_type: InformationType) -> Tuple[str, List[Dict[str, Any]]]:
        """Analyze content for patterns and enhancements"""
        
        # Detect patterns
        patterns = await self.pattern_detector.detect_patterns(content, info_type)
        
        # Enhance content with AI
        enhancement_prompt = f"""
        Analyze and enhance this {info_type.value} information:
        
        Original Content:
        {content}
        
        Please:
        1. Improve clarity and structure
        2. Add relevant context or examples
        3. Highlight key insights or actionable items
        4. Maintain the original meaning and technical accuracy
        
        Enhanced Content:
        """
        
        try:
            enhanced_content = await self.claude_api.complete(
                enhancement_prompt, max_tokens=1500
            )
            return enhanced_content.strip(), patterns
        except Exception as e:
            logger.error(f"Content enhancement failed: {e}")
            return content, patterns
    
    def _calculate_relevance(self, info: SharedInformation, query: str) -> float:
        """Calculate relevance score for information"""
        query_lower = query.lower()
        
        relevance = 0.0
        
        # Title matching (highest weight)
        if query_lower in info.title.lower():
            relevance += 3.0
        
        # Content matching
        content_lower = info.content.lower()
        query_words = query_lower.split()
        content_words = content_lower.split()
        
        matching_words = sum(1 for word in query_words if word in content_words)
        word_match_ratio = matching_words / len(query_words) if query_words else 0
        relevance += word_match_ratio * 2.0
        
        # Tag matching
        for tag in info.tags:
            if query_lower in tag.lower():
                relevance += 1.0
        
        # Priority and recency bonuses
        priority_bonus = info.priority.value * 0.5
        relevance += priority_bonus
        
        age_hours = (datetime.now() - info.created_at).total_seconds() / 3600
        if age_hours < 24:
            relevance += 0.5
        elif age_hours > 168:  # 1 week
            relevance *= 0.8
        
        # Access frequency bonus
        if info.access_count > 10:
            relevance += 0.5
        
        return relevance
    
    def _cache_information(self, info: SharedInformation):
        """Add information to cache"""
        self.information_cache[info.id] = info
        
        # Maintain cache size
        if info.id in self.cache_access_order:
            self.cache_access_order.remove(info.id)
        self.cache_access_order.append(info.id)
        
        while len(self.information_cache) > self.cache_max_size:
            oldest_id = self.cache_access_order.popleft()
            self.information_cache.pop(oldest_id, None)
    
    async def _maintenance_loop(self):
        """Background maintenance tasks"""
        while self.running:
            try:
                # Clean up expired information
                await self._cleanup_expired_information()
                
                # Update relevance scores
                await self._update_relevance_scores()
                
                # Commit version control changes
                if self.version_control:
                    self.version_control.commit_knowledge_changes(
                        "Automated maintenance update"
                    )
                
                await asyncio.sleep(self.maintenance_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Information sharing maintenance error: {e}")
                await asyncio.sleep(600)  # Wait 10 minutes on error
    
    async def _cleanup_expired_information(self):
        """Remove expired information"""
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM shared_information 
                    WHERE expires_at IS NOT NULL AND expires_at < ?
                """, (datetime.now(),))
                
                if cursor.rowcount > 0:
                    logger.info(f"Cleaned up {cursor.rowcount} expired information items")
        
        except Exception as e:
            logger.error(f"Expired information cleanup failed: {e}")
    
    async def _update_relevance_scores(self):
        """Update relevance scores based on access patterns"""
        try:
            # Simple relevance decay for old items
            decay_date = datetime.now() - timedelta(days=7)
            
            with sqlite3.connect(self.store.db_path) as conn:
                conn.execute("""
                    UPDATE shared_information 
                    SET relevance_score = relevance_score * 0.95
                    WHERE created_at < ? AND relevance_score > 0.1
                """, (decay_date,))
        
        except Exception as e:
            logger.error(f"Relevance score update failed: {e}")
    
    def get_sharing_stats(self) -> Dict[str, Any]:
        """Get information sharing statistics"""
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                stats = {}
                
                # Count by type
                cursor = conn.execute("""
                    SELECT type, COUNT(*) FROM shared_information GROUP BY type
                """)
                stats["by_type"] = {row[0]: row[1] for row in cursor}
                
                # Count by scope
                cursor = conn.execute("""
                    SELECT scope, COUNT(*) FROM shared_information GROUP BY scope
                """)
                stats["by_scope"] = {row[0]: row[1] for row in cursor}
                
                # Count by bot
                cursor = conn.execute("""
                    SELECT source_bot_id, COUNT(*) FROM shared_information 
                    GROUP BY source_bot_id ORDER BY COUNT(*) DESC LIMIT 10
                """)
                stats["top_contributors"] = {row[0]: row[1] for row in cursor}
                
                # Total statistics
                cursor = conn.execute("SELECT COUNT(*) FROM shared_information")
                stats["total_items"] = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT SUM(access_count) FROM shared_information")
                stats["total_accesses"] = cursor.fetchone()[0] or 0
                
                return stats
        
        except Exception as e:
            logger.error(f"Failed to get sharing stats: {e}")
            return {"error": str(e)}

class PatternDetector:
    def __init__(self, claude_api):
        self.claude_api = claude_api
    
    async def detect_patterns(self, content: str, info_type: InformationType) -> List[Dict[str, Any]]:
        """Detect patterns in shared information"""
        
        pattern_prompt = f"""
        Analyze this {info_type.value} information and identify any notable patterns:
        
        Content: {content}
        
        Look for:
        1. Common approaches or solutions
        2. Recurring themes or concepts
        3. Best practices or anti-patterns
        4. Technical patterns or structures
        5. Process or workflow patterns
        
        Return a JSON list of patterns found:
        [
            {{
                "type": "pattern_type",
                "description": "pattern description",
                "examples": ["example1", "example2"],
                "confidence": 0.8
            }}
        ]
        
        Patterns:
        """
        
        try:
            response = await self.claude_api.complete(pattern_prompt, max_tokens=1000)
            patterns_data = json.loads(response.strip())
            return patterns_data
        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            return []

class KnowledgeSynthesizer:
    def __init__(self, claude_api):
        self.claude_api = claude_api
    
    async def synthesize(self, topic: str, information_items: List[SharedInformation]) -> Optional[Dict[str, Any]]:
        """Synthesize knowledge from multiple information sources"""
        
        if not information_items:
            return None
        
        # Prepare source materials
        source_materials = []
        for i, info in enumerate(information_items[:10]):  # Limit to top 10
            source_materials.append(f"### Source {i+1}: {info.title}\n{info.content}\n")
        
        sources_text = "\n".join(source_materials)
        
        synthesis_prompt = f"""
        Synthesize comprehensive knowledge about "{topic}" based on the following sources:
        
        {sources_text}
        
        Create a synthesis that:
        1. Identifies common themes and patterns
        2. Resolves any contradictions
        3. Provides a coherent overview
        4. Highlights key insights and best practices
        5. Suggests practical applications
        
        Return JSON with:
        {{
            "content": "synthesized knowledge content",
            "key_insights": ["insight1", "insight2", ...],
            "tags": ["tag1", "tag2", ...],
            "confidence": 0.85,
            "source_count": {len(information_items)}
        }}
        
        Synthesis:
        """
        
        try:
            response = await self.claude_api.complete(synthesis_prompt, max_tokens=2000)
            synthesis_data = json.loads(response.strip())
            return synthesis_data
        except Exception as e:
            logger.error(f"Knowledge synthesis failed: {e}")
            return None