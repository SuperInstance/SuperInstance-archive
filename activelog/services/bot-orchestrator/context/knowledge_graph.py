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
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import pickle

logger = logging.getLogger(__name__)

class NodeType(Enum):
    TASK = "task"
    RESOURCE = "resource" 
    BOT = "bot"
    CONCEPT = "concept"
    ENTITY = "entity"
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    ERROR = "error"
    SYSTEM = "system"

class RelationType(Enum):
    DEPENDS_ON = "depends_on"
    USES = "uses"
    CREATES = "creates"
    MODIFIES = "modifies"
    CONTAINS = "contains"
    SIMILAR_TO = "similar_to"
    RELATES_TO = "relates_to"
    EXECUTES = "executes"
    INHERITS_FROM = "inherits_from"
    IMPLEMENTS = "implements"
    CALLS = "calls"
    REFERENCES = "references"

@dataclass
class GraphNode:
    id: str
    type: NodeType
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    content: str = ""
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "properties": self.properties,
            "content": self.content,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "access_count": self.access_count
        }

@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    last_confirmed: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "properties": self.properties,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_confirmed": self.last_confirmed.isoformat()
        }

class EntityExtractor:
    def __init__(self, claude_api):
        self.claude_api = claude_api
        
        # Predefined patterns for common entities
        self.entity_patterns = {
            NodeType.FUNCTION: [r"def\s+(\w+)\s*\(", r"function\s+(\w+)\s*\(", r"(\w+)\s*\(.*\)\s*{"],
            NodeType.CLASS: [r"class\s+(\w+)", r"interface\s+(\w+)", r"struct\s+(\w+)"],
            NodeType.VARIABLE: [r"(\w+)\s*=", r"var\s+(\w+)", r"let\s+(\w+)", r"const\s+(\w+)"],
            NodeType.FILE: [r"([a-zA-Z0-9_/-]+\.[a-zA-Z0-9]+)", r"'([^']+\.[^']+)'", r'"([^"]+\.[^"]+)"'],
            NodeType.ERROR: [r"(\w*Error)", r"(\w*Exception)", r"ERROR:\s*(\w+)"]
        }
        
        # Keyword-based entity classification
        self.entity_keywords = {
            NodeType.SYSTEM: ["system", "server", "service", "daemon", "process"],
            NodeType.RESOURCE: ["database", "cache", "memory", "cpu", "disk", "network"],
            NodeType.CONCEPT: ["algorithm", "pattern", "principle", "methodology", "approach"]
        }
    
    async def extract_entities(self, text: str, context_type: str = "") -> List[GraphNode]:
        """Extract entities from text using AI and pattern matching"""
        entities = []
        
        # Pattern-based extraction
        pattern_entities = self._extract_with_patterns(text)
        entities.extend(pattern_entities)
        
        # Keyword-based extraction
        keyword_entities = self._extract_with_keywords(text)
        entities.extend(keyword_entities)
        
        # AI-based extraction for complex entities
        if len(text) > 100:  # Only for substantial content
            ai_entities = await self._extract_with_ai(text, context_type)
            entities.extend(ai_entities)
        
        # Deduplicate and clean up
        unique_entities = self._deduplicate_entities(entities)
        
        return unique_entities
    
    def _extract_with_patterns(self, text: str) -> List[GraphNode]:
        """Extract entities using regex patterns"""
        import re
        entities = []
        
        for node_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    entity_name = match.group(1) if match.groups() else match.group(0)
                    
                    entity_id = f"{node_type.value}_{hashlib.md5(entity_name.encode()).hexdigest()[:8]}"
                    
                    entities.append(GraphNode(
                        id=entity_id,
                        type=node_type,
                        name=entity_name,
                        content=match.group(0),
                        confidence=0.8,
                        properties={"extraction_method": "pattern", "pattern": pattern}
                    ))
        
        return entities
    
    def _extract_with_keywords(self, text: str) -> List[GraphNode]:
        """Extract entities using keyword matching"""
        entities = []
        text_lower = text.lower()
        
        for node_type, keywords in self.entity_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Find the actual mention in text
                    import re
                    pattern = rf'\b{re.escape(keyword)}\b'
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        entity_name = match.group(0)
                        entity_id = f"{node_type.value}_{hashlib.md5(entity_name.encode()).hexdigest()[:8]}"
                        
                        entities.append(GraphNode(
                            id=entity_id,
                            type=node_type,
                            name=entity_name,
                            content=entity_name,
                            confidence=0.6,
                            properties={"extraction_method": "keyword", "keyword": keyword}
                        ))
        
        return entities
    
    async def _extract_with_ai(self, text: str, context_type: str = "") -> List[GraphNode]:
        """Extract entities using AI analysis"""
        extraction_prompt = f"""
        Analyze the following text and extract important entities. Focus on:
        - Technical concepts and terms
        - System components and resources
        - Key processes and functions
        - Important relationships
        
        Context type: {context_type}
        
        Text to analyze:
        {text}
        
        Return a JSON list of entities with this format:
        [
            {{
                "name": "entity name",
                "type": "task|resource|bot|concept|entity|file|function|class|variable|error|system",
                "confidence": 0.9,
                "description": "brief description"
            }}
        ]
        
        Entities:
        """
        
        try:
            response = await self.claude_api.complete(extraction_prompt, max_tokens=1500)
            
            # Parse AI response
            entities_data = json.loads(response.strip())
            
            entities = []
            for entity_data in entities_data:
                try:
                    node_type = NodeType(entity_data["type"])
                    entity_name = entity_data["name"]
                    confidence = entity_data.get("confidence", 0.7)
                    description = entity_data.get("description", "")
                    
                    entity_id = f"{node_type.value}_{hashlib.md5(entity_name.encode()).hexdigest()[:8]}"
                    
                    entities.append(GraphNode(
                        id=entity_id,
                        type=node_type,
                        name=entity_name,
                        content=description,
                        confidence=confidence,
                        properties={
                            "extraction_method": "ai",
                            "description": description,
                            "context_type": context_type
                        }
                    ))
                
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid entity data: {entity_data}, error: {e}")
                    continue
            
            return entities
            
        except Exception as e:
            logger.error(f"AI entity extraction failed: {e}")
            return []
    
    def _deduplicate_entities(self, entities: List[GraphNode]) -> List[GraphNode]:
        """Remove duplicate entities and merge similar ones"""
        unique_entities = {}
        
        for entity in entities:
            # Use normalized name as key for deduplication
            normalized_name = entity.name.lower().strip()
            key = f"{entity.type.value}_{normalized_name}"
            
            if key in unique_entities:
                # Merge with existing entity (keep higher confidence)
                existing = unique_entities[key]
                if entity.confidence > existing.confidence:
                    unique_entities[key] = entity
                else:
                    # Merge properties
                    existing.properties.update(entity.properties)
            else:
                unique_entities[key] = entity
        
        return list(unique_entities.values())

class RelationshipDetector:
    def __init__(self, claude_api):
        self.claude_api = claude_api
        
        # Pattern-based relationship detection
        self.relation_patterns = {
            RelationType.DEPENDS_ON: [
                r"(\w+)\s+depends\s+on\s+(\w+)",
                r"(\w+)\s+requires\s+(\w+)",
                r"import\s+(\w+).*from\s+(\w+)"
            ],
            RelationType.USES: [
                r"(\w+)\s+uses\s+(\w+)",
                r"(\w+)\.(\w+)\s*\(",
                r"(\w+)\s+utilizes\s+(\w+)"
            ],
            RelationType.CREATES: [
                r"(\w+)\s+creates\s+(\w+)",
                r"new\s+(\w+)\s*\(",
                r"(\w+)\s+generates\s+(\w+)"
            ],
            RelationType.CALLS: [
                r"(\w+)\.(\w+)\s*\(",
                r"(\w+)\s*\(\s*(\w+)",
                r"invoke\s+(\w+)"
            ]
        }
    
    async def detect_relationships(self, entities: List[GraphNode], 
                                 text: str, context: str = "") -> List[GraphEdge]:
        """Detect relationships between entities"""
        relationships = []
        
        # Pattern-based detection
        pattern_rels = self._detect_with_patterns(entities, text)
        relationships.extend(pattern_rels)
        
        # Proximity-based relationships
        proximity_rels = self._detect_proximity_relationships(entities, text)
        relationships.extend(proximity_rels)
        
        # AI-based relationship detection
        if len(entities) >= 2:
            ai_rels = await self._detect_with_ai(entities, text, context)
            relationships.extend(ai_rels)
        
        # Deduplicate relationships
        unique_rels = self._deduplicate_relationships(relationships)
        
        return unique_rels
    
    def _detect_with_patterns(self, entities: List[GraphNode], text: str) -> List[GraphEdge]:
        """Detect relationships using regex patterns"""
        import re
        relationships = []
        
        # Create entity lookup by name
        entity_by_name = {entity.name.lower(): entity for entity in entities}
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                
                for match in matches:
                    if len(match.groups()) >= 2:
                        source_name = match.group(1).lower()
                        target_name = match.group(2).lower()
                        
                        source_entity = entity_by_name.get(source_name)
                        target_entity = entity_by_name.get(target_name)
                        
                        if source_entity and target_entity and source_entity.id != target_entity.id:
                            relationships.append(GraphEdge(
                                source_id=source_entity.id,
                                target_id=target_entity.id,
                                relation_type=relation_type,
                                weight=0.8,
                                confidence=0.7,
                                properties={"detection_method": "pattern", "pattern": pattern}
                            ))
        
        return relationships
    
    def _detect_proximity_relationships(self, entities: List[GraphNode], text: str) -> List[GraphEdge]:
        """Detect relationships based on entity proximity in text"""
        relationships = []
        
        # Find entity positions in text
        entity_positions = []
        for entity in entities:
            import re
            pattern = rf'\b{re.escape(entity.name)}\b'
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                entity_positions.append({
                    "entity": entity,
                    "start": match.start(),
                    "end": match.end()
                })
        
        # Sort by position
        entity_positions.sort(key=lambda x: x["start"])
        
        # Detect relationships between nearby entities
        proximity_threshold = 200  # characters
        
        for i, pos1 in enumerate(entity_positions):
            for j, pos2 in enumerate(entity_positions[i+1:], i+1):
                distance = pos2["start"] - pos1["end"]
                
                if distance > proximity_threshold:
                    break  # Too far apart
                
                if pos1["entity"].id == pos2["entity"].id:
                    continue  # Same entity
                
                # Calculate relationship strength based on proximity
                weight = max(0.1, 1.0 - (distance / proximity_threshold))
                
                # Determine relationship type based on entity types
                relation_type = self._infer_relation_type(pos1["entity"], pos2["entity"])
                
                relationships.append(GraphEdge(
                    source_id=pos1["entity"].id,
                    target_id=pos2["entity"].id,
                    relation_type=relation_type,
                    weight=weight,
                    confidence=0.5,
                    properties={"detection_method": "proximity", "distance": distance}
                ))
        
        return relationships
    
    def _infer_relation_type(self, entity1: GraphNode, entity2: GraphNode) -> RelationType:
        """Infer relationship type based on entity types"""
        
        type_pairs = {
            (NodeType.FUNCTION, NodeType.VARIABLE): RelationType.USES,
            (NodeType.FUNCTION, NodeType.CLASS): RelationType.USES,
            (NodeType.TASK, NodeType.RESOURCE): RelationType.USES,
            (NodeType.BOT, NodeType.TASK): RelationType.EXECUTES,
            (NodeType.CLASS, NodeType.FUNCTION): RelationType.CONTAINS,
            (NodeType.FILE, NodeType.CLASS): RelationType.CONTAINS,
            (NodeType.FILE, NodeType.FUNCTION): RelationType.CONTAINS,
            (NodeType.SYSTEM, NodeType.RESOURCE): RelationType.CONTAINS,
        }
        
        pair = (entity1.type, entity2.type)
        reverse_pair = (entity2.type, entity1.type)
        
        if pair in type_pairs:
            return type_pairs[pair]
        elif reverse_pair in type_pairs:
            return type_pairs[reverse_pair]
        else:
            return RelationType.RELATES_TO
    
    async def _detect_with_ai(self, entities: List[GraphNode], 
                            text: str, context: str = "") -> List[GraphEdge]:
        """Detect relationships using AI analysis"""
        
        entity_list = [{"name": e.name, "type": e.type.value, "id": e.id} for e in entities]
        
        detection_prompt = f"""
        Analyze the relationships between these entities based on the provided text:
        
        Entities: {json.dumps(entity_list, indent=2)}
        
        Context: {context}
        
        Text: {text}
        
        Return a JSON list of relationships with this format:
        [
            {{
                "source_name": "entity1_name",
                "target_name": "entity2_name", 
                "relation_type": "depends_on|uses|creates|modifies|contains|similar_to|relates_to|executes|inherits_from|implements|calls|references",
                "confidence": 0.9,
                "explanation": "brief explanation of the relationship"
            }}
        ]
        
        Only include relationships that are clearly evident from the text.
        
        Relationships:
        """
        
        try:
            response = await self.claude_api.complete(detection_prompt, max_tokens=2000)
            
            relationships_data = json.loads(response.strip())
            relationships = []
            
            # Create lookup for entities by name
            entity_by_name = {entity.name.lower(): entity for entity in entities}
            
            for rel_data in relationships_data:
                try:
                    source_name = rel_data["source_name"].lower()
                    target_name = rel_data["target_name"].lower()
                    
                    source_entity = entity_by_name.get(source_name)
                    target_entity = entity_by_name.get(target_name)
                    
                    if source_entity and target_entity and source_entity.id != target_entity.id:
                        relation_type = RelationType(rel_data["relation_type"])
                        confidence = rel_data.get("confidence", 0.7)
                        explanation = rel_data.get("explanation", "")
                        
                        relationships.append(GraphEdge(
                            source_id=source_entity.id,
                            target_id=target_entity.id,
                            relation_type=relation_type,
                            weight=confidence,
                            confidence=confidence,
                            properties={
                                "detection_method": "ai",
                                "explanation": explanation
                            }
                        ))
                
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid relationship data: {rel_data}, error: {e}")
                    continue
            
            return relationships
            
        except Exception as e:
            logger.error(f"AI relationship detection failed: {e}")
            return []
    
    def _deduplicate_relationships(self, relationships: List[GraphEdge]) -> List[GraphEdge]:
        """Remove duplicate relationships"""
        unique_rels = {}
        
        for rel in relationships:
            # Create key for deduplication
            key = f"{rel.source_id}_{rel.target_id}_{rel.relation_type.value}"
            
            if key in unique_rels:
                # Keep relationship with higher confidence
                existing = unique_rels[key]
                if rel.confidence > existing.confidence:
                    unique_rels[key] = rel
            else:
                unique_rels[key] = rel
        
        return list(unique_rels.values())

class GraphStorage:
    def __init__(self, db_path: str = "knowledge_graph.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for graph storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    properties TEXT,
                    content TEXT,
                    confidence REAL,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    source_id TEXT,
                    target_id TEXT,
                    relation_type TEXT,
                    weight REAL,
                    properties TEXT,
                    confidence REAL,
                    created_at TIMESTAMP,
                    last_confirmed TIMESTAMP,
                    PRIMARY KEY (source_id, target_id, relation_type)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_type_name 
                ON graph_nodes (type, name)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_edges_source_target 
                ON graph_edges (source_id, target_id)
            """)
    
    def store_node(self, node: GraphNode) -> bool:
        """Store a graph node"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO graph_nodes 
                        (id, type, name, properties, content, confidence, 
                         created_at, last_updated, access_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node.id, node.type.value, node.name, json.dumps(node.properties),
                        node.content, node.confidence, node.created_at,
                        node.last_updated, node.access_count
                    ))
                return True
        except Exception as e:
            logger.error(f"Failed to store node {node.id}: {e}")
            return False
    
    def store_edge(self, edge: GraphEdge) -> bool:
        """Store a graph edge"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO graph_edges 
                        (source_id, target_id, relation_type, weight, properties, 
                         confidence, created_at, last_confirmed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        edge.source_id, edge.target_id, edge.relation_type.value,
                        edge.weight, json.dumps(edge.properties), edge.confidence,
                        edge.created_at, edge.last_confirmed
                    ))
                return True
        except Exception as e:
            logger.error(f"Failed to store edge {edge.source_id} -> {edge.target_id}: {e}")
            return False
    
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Retrieve a graph node"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(
                        "SELECT * FROM graph_nodes WHERE id = ?", (node_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        return GraphNode(
                            id=row[0],
                            type=NodeType(row[1]),
                            name=row[2],
                            properties=json.loads(row[3]) if row[3] else {},
                            content=row[4] or "",
                            confidence=row[5] or 1.0,
                            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                            last_updated=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                            access_count=row[8] or 0
                        )
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve node {node_id}: {e}")
            return None
    
    def search_nodes(self, filters: Dict[str, Any], limit: int = 100) -> List[GraphNode]:
        """Search nodes with filters"""
        try:
            with self.lock:
                query = "SELECT * FROM graph_nodes WHERE 1=1"
                params = []
                
                if 'type' in filters:
                    query += " AND type = ?"
                    params.append(filters['type'])
                
                if 'name_contains' in filters:
                    query += " AND name LIKE ?"
                    params.append(f"%{filters['name_contains']}%")
                
                if 'content_contains' in filters:
                    query += " AND content LIKE ?"
                    params.append(f"%{filters['content_contains']}%")
                
                if 'min_confidence' in filters:
                    query += " AND confidence >= ?"
                    params.append(filters['min_confidence'])
                
                query += " ORDER BY confidence DESC, access_count DESC LIMIT ?"
                params.append(limit)
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.execute(query, params)
                    rows = cursor.fetchall()
                    
                    return [self._row_to_node(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Node search failed: {e}")
            return []
    
    def get_node_relationships(self, node_id: str, 
                             direction: str = "both") -> List[GraphEdge]:
        """Get relationships for a node"""
        try:
            with self.lock:
                relationships = []
                
                with sqlite3.connect(self.db_path) as conn:
                    if direction in ["outgoing", "both"]:
                        cursor = conn.execute(
                            "SELECT * FROM graph_edges WHERE source_id = ?", (node_id,)
                        )
                        for row in cursor:
                            relationships.append(self._row_to_edge(row))
                    
                    if direction in ["incoming", "both"]:
                        cursor = conn.execute(
                            "SELECT * FROM graph_edges WHERE target_id = ?", (node_id,)
                        )
                        for row in cursor:
                            relationships.append(self._row_to_edge(row))
                
                return relationships
        
        except Exception as e:
            logger.error(f"Failed to get relationships for node {node_id}: {e}")
            return []
    
    def _row_to_node(self, row) -> GraphNode:
        """Convert database row to GraphNode"""
        return GraphNode(
            id=row[0],
            type=NodeType(row[1]),
            name=row[2],
            properties=json.loads(row[3]) if row[3] else {},
            content=row[4] or "",
            confidence=row[5] or 1.0,
            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            last_updated=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
            access_count=row[8] or 0
        )
    
    def _row_to_edge(self, row) -> GraphEdge:
        """Convert database row to GraphEdge"""
        return GraphEdge(
            source_id=row[0],
            target_id=row[1],
            relation_type=RelationType(row[2]),
            weight=row[3] or 1.0,
            properties=json.loads(row[4]) if row[4] else {},
            confidence=row[5] or 1.0,
            created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
            last_confirmed=datetime.fromisoformat(row[7]) if row[7] else datetime.now()
        )

class KnowledgeGraph:
    def __init__(self, claude_api):
        self.claude_api = claude_api
        self.storage = GraphStorage()
        self.entity_extractor = EntityExtractor(claude_api)
        self.relationship_detector = RelationshipDetector(claude_api)
        
        # In-memory graph for fast queries
        self.graph = nx.DiGraph()
        self.last_sync = datetime.now()
        self.sync_interval = 300  # 5 minutes
        
        # Analysis tools
        self.clustering_model = None
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        
        # Background tasks
        self.background_task = None
        self.running = False
    
    async def start(self):
        """Start the knowledge graph"""
        self.running = True
        await self._sync_from_storage()
        self.background_task = asyncio.create_task(self._background_loop())
        logger.info("Knowledge Graph started")
    
    async def stop(self):
        """Stop the knowledge graph"""
        self.running = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        logger.info("Knowledge Graph stopped")
    
    async def add_content(self, content: str, content_type: str = "",
                         source: str = "", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add content to the knowledge graph"""
        
        # Extract entities
        entities = await self.entity_extractor.extract_entities(content, content_type)
        
        # Extract relationships
        relationships = await self.relationship_detector.detect_relationships(
            entities, content, content_type
        )
        
        # Store in database
        stored_entities = 0
        stored_relationships = 0
        
        for entity in entities:
            if metadata:
                entity.properties.update(metadata)
            entity.properties["source"] = source
            
            if self.storage.store_node(entity):
                stored_entities += 1
                # Add to in-memory graph
                self.graph.add_node(entity.id, **entity.to_dict())
        
        for relationship in relationships:
            relationship.properties["source"] = source
            
            if self.storage.store_edge(relationship):
                stored_relationships += 1
                # Add to in-memory graph
                self.graph.add_edge(
                    relationship.source_id,
                    relationship.target_id,
                    **relationship.to_dict()
                )
        
        logger.info(f"Added {stored_entities} entities and {stored_relationships} relationships")
        
        return {
            "entities_added": stored_entities,
            "relationships_added": stored_relationships,
            "total_entities": len(entities),
            "total_relationships": len(relationships)
        }
    
    async def get_related_context(self, query: str, max_depth: int = 2,
                                max_nodes: int = 50) -> Dict[str, Any]:
        """Get context related to a query using graph traversal"""
        
        # Find relevant starting nodes
        start_nodes = self._find_relevant_nodes(query)
        
        if not start_nodes:
            return {"nodes": [], "edges": [], "context": "No relevant context found."}
        
        # Perform graph traversal
        relevant_nodes, relevant_edges = self._traverse_graph(start_nodes, max_depth, max_nodes)
        
        # Generate contextual summary
        context_summary = await self._generate_context_summary(relevant_nodes, relevant_edges, query)
        
        return {
            "nodes": [node.to_dict() for node in relevant_nodes],
            "edges": [edge.to_dict() for edge in relevant_edges],
            "context": context_summary,
            "query": query
        }
    
    def _find_relevant_nodes(self, query: str, limit: int = 20) -> List[GraphNode]:
        """Find nodes relevant to a query"""
        query_lower = query.lower()
        relevant_nodes = []
        
        # Search by name and content similarity
        filters = {"name_contains": query, "min_confidence": 0.3}
        name_matches = self.storage.search_nodes(filters, limit=limit//2)
        relevant_nodes.extend(name_matches)
        
        # Search by content
        filters = {"content_contains": query, "min_confidence": 0.3}
        content_matches = self.storage.search_nodes(filters, limit=limit//2)
        relevant_nodes.extend(content_matches)
        
        # Remove duplicates
        seen_ids = set()
        unique_nodes = []
        for node in relevant_nodes:
            if node.id not in seen_ids:
                unique_nodes.append(node)
                seen_ids.add(node.id)
        
        # Score nodes by relevance
        scored_nodes = []
        for node in unique_nodes:
            relevance_score = self._calculate_node_relevance(node, query)
            scored_nodes.append((node, relevance_score))
        
        # Sort by relevance and return top nodes
        scored_nodes.sort(key=lambda x: x[1], reverse=True)
        return [node for node, score in scored_nodes[:limit]]
    
    def _calculate_node_relevance(self, node: GraphNode, query: str) -> float:
        """Calculate node relevance to query"""
        query_lower = query.lower()
        
        # Base relevance from confidence
        relevance = node.confidence
        
        # Name matching bonus
        if query_lower in node.name.lower():
            relevance += 2.0
        
        # Content matching bonus
        if query_lower in node.content.lower():
            relevance += 1.0
        
        # Type-based relevance
        if node.type in [NodeType.TASK, NodeType.FUNCTION, NodeType.CLASS]:
            relevance += 0.5
        
        # Access frequency bonus
        if node.access_count > 5:
            relevance += 0.5
        
        # Recency bonus
        age_days = (datetime.now() - node.last_updated).total_seconds() / 86400
        if age_days < 1:
            relevance += 0.5
        elif age_days > 30:
            relevance *= 0.8
        
        return relevance
    
    def _traverse_graph(self, start_nodes: List[GraphNode], 
                       max_depth: int, max_nodes: int) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """Traverse the graph from starting nodes"""
        
        visited_nodes = {}
        visited_edges = {}
        queue = deque([(node.id, 0) for node in start_nodes])
        
        # Add start nodes to visited
        for node in start_nodes:
            visited_nodes[node.id] = node
        
        while queue and len(visited_nodes) < max_nodes:
            node_id, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            # Get relationships for this node
            relationships = self.storage.get_node_relationships(node_id)
            
            for edge in relationships:
                edge_key = f"{edge.source_id}_{edge.target_id}_{edge.relation_type.value}"
                
                if edge_key not in visited_edges:
                    visited_edges[edge_key] = edge
                
                # Add connected nodes to queue
                connected_id = edge.target_id if edge.source_id == node_id else edge.source_id
                
                if connected_id not in visited_nodes:
                    connected_node = self.storage.get_node(connected_id)
                    if connected_node:
                        visited_nodes[connected_id] = connected_node
                        queue.append((connected_id, depth + 1))
        
        return list(visited_nodes.values()), list(visited_edges.values())
    
    async def _generate_context_summary(self, nodes: List[GraphNode], 
                                      edges: List[GraphEdge], query: str) -> str:
        """Generate a contextual summary of the graph data"""
        
        if not nodes:
            return "No relevant context found."
        
        # Organize nodes by type
        nodes_by_type = defaultdict(list)
        for node in nodes:
            nodes_by_type[node.type].append(node)
        
        # Organize edges by type
        edges_by_type = defaultdict(list)
        for edge in edges:
            edges_by_type[edge.relation_type].append(edge)
        
        # Build summary sections
        summary_sections = []
        
        # Entity summary
        for node_type, type_nodes in nodes_by_type.items():
            if len(type_nodes) > 0:
                type_name = node_type.value.replace('_', ' ').title() + 's'
                node_names = [node.name for node in type_nodes[:5]]  # Limit to top 5
                if len(type_nodes) > 5:
                    node_names.append(f"and {len(type_nodes) - 5} more")
                
                summary_sections.append(f"**{type_name}**: {', '.join(node_names)}")
        
        # Relationship summary
        key_relationships = []
        for rel_type, type_edges in edges_by_type.items():
            if len(type_edges) > 0:
                rel_name = rel_type.value.replace('_', ' ')
                key_relationships.append(f"{len(type_edges)} {rel_name} relationships")
        
        if key_relationships:
            summary_sections.append(f"**Relationships**: {', '.join(key_relationships)}")
        
        # Generate AI-enhanced summary
        context_data = "\n".join(summary_sections)
        
        enhancement_prompt = f"""
        Based on the following knowledge graph data related to the query "{query}", 
        create a concise and informative context summary:
        
        Graph Data:
        {context_data}
        
        Key Nodes:
        {json.dumps([{"name": n.name, "type": n.type.value, "content": n.content[:100]} for n in nodes[:10]], indent=2)}
        
        Please provide a structured summary that highlights:
        1. Main entities and components
        2. Key relationships and dependencies
        3. Relevant information for the query
        
        Summary:
        """
        
        try:
            ai_summary = await self.claude_api.complete(enhancement_prompt, max_tokens=800)
            return ai_summary.strip()
        except Exception as e:
            logger.error(f"AI context summary failed: {e}")
            return "\n".join(summary_sections)
    
    async def _sync_from_storage(self):
        """Sync in-memory graph with database"""
        try:
            # Clear current graph
            self.graph.clear()
            
            # Load all nodes
            all_nodes = self.storage.search_nodes({}, limit=10000)
            for node in all_nodes:
                self.graph.add_node(node.id, **node.to_dict())
            
            # Load all edges
            with sqlite3.connect(self.storage.db_path) as conn:
                cursor = conn.execute("SELECT * FROM graph_edges")
                for row in cursor:
                    edge = self.storage._row_to_edge(row)
                    if edge.source_id in self.graph and edge.target_id in self.graph:
                        self.graph.add_edge(
                            edge.source_id,
                            edge.target_id,
                            **edge.to_dict()
                        )
            
            self.last_sync = datetime.now()
            logger.info(f"Synced {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
            
        except Exception as e:
            logger.error(f"Graph sync failed: {e}")
    
    async def _background_loop(self):
        """Background maintenance tasks"""
        while self.running:
            try:
                # Periodic sync
                if (datetime.now() - self.last_sync).total_seconds() > self.sync_interval:
                    await self._sync_from_storage()
                
                # Cleanup old low-confidence relationships
                await self._cleanup_weak_relationships()
                
                # Update node clusters
                await self._update_clusters()
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Knowledge graph background loop error: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_weak_relationships(self):
        """Remove low-confidence relationships that are old"""
        try:
            cutoff_date = datetime.now() - timedelta(days=7)
            
            with sqlite3.connect(self.storage.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM graph_edges 
                    WHERE confidence < 0.3 AND last_confirmed < ?
                """, (cutoff_date,))
                
                if cursor.rowcount > 0:
                    logger.info(f"Cleaned up {cursor.rowcount} weak relationships")
                    # Trigger resync
                    self.last_sync = datetime.now() - timedelta(seconds=self.sync_interval + 1)
        
        except Exception as e:
            logger.error(f"Relationship cleanup failed: {e}")
    
    async def _update_clusters(self):
        """Update node clusters based on content similarity"""
        try:
            nodes_with_content = [
                node for node in self.storage.search_nodes({}, limit=1000)
                if node.content and len(node.content) > 20
            ]
            
            if len(nodes_with_content) < 10:
                return
            
            # Vectorize content
            content_texts = [node.content for node in nodes_with_content]
            tfidf_matrix = self.vectorizer.fit_transform(content_texts)
            
            # Perform clustering
            n_clusters = min(10, len(nodes_with_content) // 5)
            self.clustering_model = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = self.clustering_model.fit_predict(tfidf_matrix)
            
            # Update node properties with cluster information
            for i, node in enumerate(nodes_with_content):
                cluster_id = int(cluster_labels[i])
                node.properties["cluster_id"] = cluster_id
                self.storage.store_node(node)
            
            logger.info(f"Updated clusters for {len(nodes_with_content)} nodes")
            
        except Exception as e:
            logger.error(f"Cluster update failed: {e}")
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        try:
            stats = {
                "total_nodes": len(self.graph.nodes),
                "total_edges": len(self.graph.edges),
                "node_types": defaultdict(int),
                "edge_types": defaultdict(int),
                "connected_components": nx.number_connected_components(self.graph.to_undirected()),
                "average_degree": 0,
                "graph_density": nx.density(self.graph)
            }
            
            # Count nodes by type
            for node_id, node_data in self.graph.nodes(data=True):
                node_type = node_data.get("type", "unknown")
                stats["node_types"][node_type] += 1
            
            # Count edges by type
            for source, target, edge_data in self.graph.edges(data=True):
                edge_type = edge_data.get("relation_type", "unknown")
                stats["edge_types"][edge_type] += 1
            
            # Calculate average degree
            if len(self.graph.nodes) > 0:
                degrees = [d for n, d in self.graph.degree()]
                stats["average_degree"] = sum(degrees) / len(degrees)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get graph stats: {e}")
            return {"error": str(e)}