import asyncio
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import networkx as nx
from dataclasses import dataclass, asdict
from collections import defaultdict
import sqlite3
import os

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    id: str
    type: str  # 'character', 'location', 'item', 'event', 'concept'
    name: str
    properties: Dict[str, Any]
    confidence: float
    first_mentioned: datetime
    last_updated: datetime
    mention_count: int

@dataclass
class KnowledgeRelation:
    source_id: str
    target_id: str
    relation_type: str  # 'located_in', 'knows', 'owns', 'part_of', 'caused_by'
    properties: Dict[str, Any]
    confidence: float
    first_established: datetime
    last_confirmed: datetime

@dataclass
class PlotThread:
    thread_id: str
    title: str
    description: str
    status: str  # 'active', 'resolved', 'dormant', 'foreshadowed'
    priority: int
    related_nodes: List[str]
    events: List[Dict[str, Any]]
    foreshadowing_elements: List[str]
    resolution_hints: List[str]

class ContextCompression(BaseModel):
    session_id: str
    original_length: int
    compressed_length: int
    key_elements: List[Dict[str, Any]]
    compression_ratio: float
    last_updated: datetime

class ContextManager:
    def __init__(self):
        self.knowledge_graphs = {}  # session_id -> nx.DiGraph
        self.plot_threads = {}  # session_id -> List[PlotThread]
        self.voice_inputs = {}  # session_id -> List[voice_input_data]
        self.compressed_contexts = {}  # session_id -> ContextCompression
        self.relationship_patterns = self._initialize_relationship_patterns()
        self._setup_database()

    def _setup_database(self):
        """Set up SQLite database for persistent storage."""
        try:
            db_dir = "database"
            os.makedirs(db_dir, exist_ok=True)
            self.db_path = os.path.join(db_dir, "context_manager.db")
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    type TEXT,
                    name TEXT,
                    properties TEXT,
                    confidence REAL,
                    first_mentioned TEXT,
                    last_updated TEXT,
                    mention_count INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_relations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    source_id TEXT,
                    target_id TEXT,
                    relation_type TEXT,
                    properties TEXT,
                    confidence REAL,
                    first_established TEXT,
                    last_confirmed TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS plot_threads (
                    thread_id TEXT PRIMARY KEY,
                    session_id TEXT,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    priority INTEGER,
                    related_nodes TEXT,
                    events TEXT,
                    foreshadowing_elements TEXT,
                    resolution_hints TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS voice_inputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    transcription TEXT,
                    voice_characteristics TEXT,
                    extracted_context TEXT,
                    timestamp TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up database: {e}")

    def _initialize_relationship_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize patterns for detecting relationships between entities."""
        return {
            'location_relationships': [
                {'pattern': r'(.*) is in (.*)', 'type': 'located_in'},
                {'pattern': r'(.*) travels to (.*)', 'type': 'connects_to'},
                {'pattern': r'(.*) near (.*)', 'type': 'adjacent_to'},
                {'pattern': r'(.*) under (.*)', 'type': 'beneath'},
                {'pattern': r'(.*) above (.*)', 'type': 'above'}
            ],
            'character_relationships': [
                {'pattern': r'(.*) knows (.*)', 'type': 'knows'},
                {'pattern': r'(.*) friend of (.*)', 'type': 'friend'},
                {'pattern': r'(.*) enemy of (.*)', 'type': 'enemy'},
                {'pattern': r'(.*) works for (.*)', 'type': 'employee'},
                {'pattern': r'(.*) leads (.*)', 'type': 'leader'},
                {'pattern': r'(.*) married to (.*)', 'type': 'spouse'},
                {'pattern': r'(.*) child of (.*)', 'type': 'child'}
            ],
            'possession_relationships': [
                {'pattern': r'(.*) owns (.*)', 'type': 'owns'},
                {'pattern': r'(.*) has (.*)', 'type': 'possesses'},
                {'pattern': r'(.*) carries (.*)', 'type': 'equipped'},
                {'pattern': r'(.*) wields (.*)', 'type': 'wields'},
                {'pattern': r'(.*) gave (.*) to (.*)', 'type': 'transfer'}
            ],
            'causal_relationships': [
                {'pattern': r'(.*) caused (.*)', 'type': 'caused'},
                {'pattern': r'(.*) because of (.*)', 'type': 'caused_by'},
                {'pattern': r'(.*) led to (.*)', 'type': 'led_to'},
                {'pattern': r'(.*) prevents (.*)', 'type': 'prevents'},
                {'pattern': r'(.*) enables (.*)', 'type': 'enables'}
            ]
        }

    def create_session(self, session_id: str):
        """Create a new context management session."""
        self.knowledge_graphs[session_id] = nx.DiGraph()
        self.plot_threads[session_id] = []
        self.voice_inputs[session_id] = []
        self.compressed_contexts[session_id] = ContextCompression(
            session_id=session_id,
            original_length=0,
            compressed_length=0,
            key_elements=[],
            compression_ratio=1.0,
            last_updated=datetime.now()
        )
        logger.info(f"Created context management session: {session_id}")

    def add_voice_input(self, session_id: str, voice_data: Dict[str, Any]):
        """Add voice input data to context management."""
        if session_id not in self.voice_inputs:
            self.create_session(session_id)
        
        self.voice_inputs[session_id].append({
            'timestamp': datetime.now(),
            'transcription': voice_data.get('transcription', ''),
            'voice_characteristics': voice_data.get('voice_characteristics'),
            'extracted_context': voice_data.get('extracted_context', {})
        })
        
        # Process the input to update knowledge graph
        asyncio.create_task(self._process_voice_input_for_knowledge_graph(session_id, voice_data))
        
        # Save to database
        self._save_voice_input_to_db(session_id, voice_data)

    async def _process_voice_input_for_knowledge_graph(self, session_id: str, voice_data: Dict[str, Any]):
        """Process voice input to update knowledge graph."""
        try:
            extracted_context = voice_data.get('extracted_context', {})
            
            # Add characters to knowledge graph
            for char in extracted_context.get('characters_mentioned', []):
                await self._add_or_update_character_node(session_id, char)
            
            # Add locations to knowledge graph
            for loc in extracted_context.get('locations_mentioned', []):
                await self._add_or_update_location_node(session_id, loc)
            
            # Add items to knowledge graph
            for item in extracted_context.get('items_mentioned', []):
                await self._add_or_update_item_node(session_id, item)
            
            # Extract and add relationships
            transcription = voice_data.get('transcription', '')
            await self._extract_and_add_relationships(session_id, transcription)
            
            # Update plot threads
            await self._update_plot_threads(session_id, extracted_context)
            
            # Compress context if needed
            await self._compress_context_if_needed(session_id)
            
        except Exception as e:
            logger.error(f"Error processing voice input for knowledge graph: {e}")

    async def _add_or_update_character_node(self, session_id: str, char_data: Dict[str, Any]):
        """Add or update a character node in the knowledge graph."""
        graph = self.knowledge_graphs[session_id]
        char_id = f"char_{char_data['name'].lower().replace(' ', '_')}"
        
        if graph.has_node(char_id):
            # Update existing node
            node_data = graph.nodes[char_id]
            node_data['mention_count'] += 1
            node_data['last_updated'] = datetime.now()
            
            # Merge properties
            existing_props = node_data.get('properties', {})
            new_props = {
                'personality_hints': char_data.get('personality_hints', []),
                'role_hints': char_data.get('role_hints', []),
                'context_mentions': char_data.get('context_mentions', [])
            }
            
            for key, value in new_props.items():
                if key in existing_props and isinstance(existing_props[key], list):
                    existing_props[key].extend(value)
                    existing_props[key] = list(set(existing_props[key]))  # Remove duplicates
                else:
                    existing_props[key] = value
            
            node_data['properties'] = existing_props
        else:
            # Add new node
            node = KnowledgeNode(
                id=char_id,
                type='character',
                name=char_data['name'],
                properties={
                    'personality_hints': char_data.get('personality_hints', []),
                    'role_hints': char_data.get('role_hints', []),
                    'context_mentions': char_data.get('context_mentions', [])
                },
                confidence=0.8,
                first_mentioned=datetime.now(),
                last_updated=datetime.now(),
                mention_count=1
            )
            
            graph.add_node(char_id, **asdict(node))
        
        # Save to database
        self._save_node_to_db(session_id, char_id, graph.nodes[char_id])

    async def _add_or_update_location_node(self, session_id: str, loc_data: Dict[str, Any]):
        """Add or update a location node in the knowledge graph."""
        graph = self.knowledge_graphs[session_id]
        loc_id = f"loc_{loc_data['name'].lower().replace(' ', '_')}"
        
        if graph.has_node(loc_id):
            # Update existing node
            node_data = graph.nodes[loc_id]
            node_data['mention_count'] += 1
            node_data['last_updated'] = datetime.now()
        else:
            # Add new node
            node = KnowledgeNode(
                id=loc_id,
                type='location',
                name=loc_data['name'],
                properties={
                    'location_type': loc_data.get('type', 'unknown'),
                    'features': loc_data.get('features', []),
                    'atmosphere_hints': loc_data.get('atmosphere_hints', [])
                },
                confidence=0.7,
                first_mentioned=datetime.now(),
                last_updated=datetime.now(),
                mention_count=1
            )
            
            graph.add_node(loc_id, **asdict(node))
        
        # Save to database
        self._save_node_to_db(session_id, loc_id, graph.nodes[loc_id])

    async def _add_or_update_item_node(self, session_id: str, item_data: Dict[str, Any]):
        """Add or update an item node in the knowledge graph."""
        graph = self.knowledge_graphs[session_id]
        item_id = f"item_{item_data['name'].lower().replace(' ', '_')}"
        
        if graph.has_node(item_id):
            # Update existing node
            node_data = graph.nodes[item_id]
            node_data['mention_count'] += 1
            node_data['last_updated'] = datetime.now()
        else:
            # Add new node
            node = KnowledgeNode(
                id=item_id,
                type='item',
                name=item_data['name'],
                properties={
                    'item_type': item_data.get('type', 'unknown'),
                    'properties': item_data.get('properties', []),
                    'rarity_hints': item_data.get('rarity_hints', [])
                },
                confidence=0.6,
                first_mentioned=datetime.now(),
                last_updated=datetime.now(),
                mention_count=1
            )
            
            graph.add_node(item_id, **asdict(node))
        
        # Save to database
        self._save_node_to_db(session_id, item_id, graph.nodes[item_id])

    async def _extract_and_add_relationships(self, session_id: str, transcription: str):
        """Extract relationships from transcription and add to knowledge graph."""
        graph = self.knowledge_graphs[session_id]
        
        import re
        
        # Extract relationships using patterns
        for category, patterns in self.relationship_patterns.items():
            for pattern_info in patterns:
                pattern = pattern_info['pattern']
                relation_type = pattern_info['type']
                
                matches = re.finditer(pattern, transcription, re.IGNORECASE)
                for match in matches:
                    groups = match.groups()
                    if len(groups) >= 2:
                        source_name = groups[0].strip()
                        target_name = groups[1].strip()
                        
                        # Find corresponding nodes
                        source_id = self._find_node_by_name(graph, source_name)
                        target_id = self._find_node_by_name(graph, target_name)
                        
                        if source_id and target_id:
                            await self._add_relationship(
                                session_id, source_id, target_id, relation_type
                            )

    def _find_node_by_name(self, graph: nx.DiGraph, name: str) -> Optional[str]:
        """Find a node by name in the graph."""
        name_lower = name.lower()
        for node_id, node_data in graph.nodes(data=True):
            if node_data.get('name', '').lower() == name_lower:
                return node_id
        return None

    async def _add_relationship(self, session_id: str, source_id: str, target_id: str, relation_type: str):
        """Add a relationship between two nodes."""
        graph = self.knowledge_graphs[session_id]
        
        if graph.has_edge(source_id, target_id):
            # Update existing relationship
            edge_data = graph.edges[source_id, target_id]
            edge_data['last_confirmed'] = datetime.now()
            edge_data['confidence'] = min(1.0, edge_data.get('confidence', 0.5) + 0.1)
        else:
            # Add new relationship
            relation = KnowledgeRelation(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                properties={},
                confidence=0.7,
                first_established=datetime.now(),
                last_confirmed=datetime.now()
            )
            
            graph.add_edge(source_id, target_id, **asdict(relation))
        
        # Save to database
        self._save_relation_to_db(session_id, source_id, target_id, graph.edges[source_id, target_id])

    async def _update_plot_threads(self, session_id: str, extracted_context: Dict[str, Any]):
        """Update plot threads based on extracted context."""
        plot_elements = extracted_context.get('plot_elements', [])
        
        for element in plot_elements:
            if element.get('type') == 'quest':
                await self._create_or_update_plot_thread(
                    session_id, 'quest', element['content'], 'active'
                )
            elif element.get('type') == 'mystery':
                await self._create_or_update_plot_thread(
                    session_id, 'mystery', element['content'], 'foreshadowed'
                )
            elif element.get('type') == 'conflict':
                await self._create_or_update_plot_thread(
                    session_id, 'conflict', element['content'], 'active'
                )

    async def _create_or_update_plot_thread(self, session_id: str, thread_type: str, content: str, status: str):
        """Create or update a plot thread."""
        threads = self.plot_threads[session_id]
        
        # Look for existing thread with similar content
        existing_thread = None
        for thread in threads:
            if thread_type in thread.title.lower() and any(word in thread.description for word in content.split()[:3]):
                existing_thread = thread
                break
        
        if existing_thread:
            # Update existing thread
            existing_thread.description += f" {content}"
            existing_thread.last_updated = datetime.now()
        else:
            # Create new thread
            thread_id = f"{thread_type}_{len(threads) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            new_thread = PlotThread(
                thread_id=thread_id,
                title=f"{thread_type.title()} Thread",
                description=content,
                status=status,
                priority=self._calculate_thread_priority(thread_type, content),
                related_nodes=[],
                events=[{
                    'timestamp': datetime.now().isoformat(),
                    'description': content,
                    'type': 'mention'
                }],
                foreshadowing_elements=[],
                resolution_hints=[]
            )
            
            threads.append(new_thread)
        
        # Save to database
        self._save_plot_thread_to_db(session_id, existing_thread or new_thread)

    def _calculate_thread_priority(self, thread_type: str, content: str) -> int:
        """Calculate priority for a plot thread."""
        base_priorities = {
            'quest': 8,
            'conflict': 9,
            'mystery': 6,
            'backstory': 4
        }
        
        base_priority = base_priorities.get(thread_type, 5)
        
        # Increase priority for urgent keywords
        urgent_keywords = ['urgent', 'immediate', 'crisis', 'danger', 'threat']
        if any(keyword in content.lower() for keyword in urgent_keywords):
            base_priority += 2
        
        return min(10, base_priority)

    async def _compress_context_if_needed(self, session_id: str):
        """Compress context if it's getting too large."""
        voice_inputs = self.voice_inputs[session_id]
        
        # Check if compression is needed (more than 50 voice inputs)
        if len(voice_inputs) > 50:
            await self._compress_context(session_id)

    async def _compress_context(self, session_id: str):
        """Compress context by summarizing older voice inputs."""
        voice_inputs = self.voice_inputs[session_id]
        original_length = len(voice_inputs)
        
        # Keep recent inputs (last 20)
        recent_inputs = voice_inputs[-20:]
        older_inputs = voice_inputs[:-20]
        
        # Summarize older inputs
        key_elements = []
        for input_data in older_inputs:
            extracted = input_data.get('extracted_context', {})
            if extracted.get('key_points'):
                key_elements.extend(extracted['key_points'])
        
        # Remove duplicates and keep top elements
        unique_elements = list(set(key_elements))[:20]
        
        # Update compressed context
        compression = self.compressed_contexts[session_id]
        compression.original_length = original_length
        compression.compressed_length = len(recent_inputs) + len(unique_elements)
        compression.key_elements = [{'content': elem, 'type': 'key_point'} for elem in unique_elements]
        compression.compression_ratio = compression.compressed_length / original_length
        compression.last_updated = datetime.now()
        
        # Keep only recent inputs
        self.voice_inputs[session_id] = recent_inputs
        
        logger.info(f"Compressed context for {session_id}: {original_length} -> {compression.compressed_length}")

    def get_knowledge_graph(self, session_id: str) -> Dict[str, Any]:
        """Get knowledge graph data for a session."""
        if session_id not in self.knowledge_graphs:
            return {'nodes': [], 'edges': []}
        
        graph = self.knowledge_graphs[session_id]
        
        # Convert to serializable format
        nodes = []
        for node_id, node_data in graph.nodes(data=True):
            node_dict = dict(node_data)
            # Convert datetime objects to strings
            if 'first_mentioned' in node_dict and isinstance(node_dict['first_mentioned'], datetime):
                node_dict['first_mentioned'] = node_dict['first_mentioned'].isoformat()
            if 'last_updated' in node_dict and isinstance(node_dict['last_updated'], datetime):
                node_dict['last_updated'] = node_dict['last_updated'].isoformat()
            nodes.append(node_dict)
        
        edges = []
        for source, target, edge_data in graph.edges(data=True):
            edge_dict = dict(edge_data)
            edge_dict['source'] = source
            edge_dict['target'] = target
            # Convert datetime objects to strings
            if 'first_established' in edge_dict and isinstance(edge_dict['first_established'], datetime):
                edge_dict['first_established'] = edge_dict['first_established'].isoformat()
            if 'last_confirmed' in edge_dict and isinstance(edge_dict['last_confirmed'], datetime):
                edge_dict['last_confirmed'] = edge_dict['last_confirmed'].isoformat()
            edges.append(edge_dict)
        
        return {
            'nodes': nodes,
            'edges': edges,
            'node_count': len(nodes),
            'edge_count': len(edges)
        }

    def get_relationship_map(self, session_id: str) -> Dict[str, List[Dict]]:
        """Get relationship map grouped by type."""
        if session_id not in self.knowledge_graphs:
            return {}
        
        graph = self.knowledge_graphs[session_id]
        relationship_map = defaultdict(list)
        
        for source, target, edge_data in graph.edges(data=True):
            relation_type = edge_data.get('relation_type', 'unknown')
            source_name = graph.nodes[source].get('name', source)
            target_name = graph.nodes[target].get('name', target)
            
            relationship_map[relation_type].append({
                'source': source_name,
                'target': target_name,
                'confidence': edge_data.get('confidence', 0.5),
                'last_confirmed': edge_data.get('last_confirmed', datetime.now()).isoformat() if isinstance(edge_data.get('last_confirmed'), datetime) else edge_data.get('last_confirmed')
            })
        
        return dict(relationship_map)

    def get_plot_threads(self, session_id: str) -> List[Dict[str, Any]]:
        """Get plot threads for a session."""
        if session_id not in self.plot_threads:
            return []
        
        threads = self.plot_threads[session_id]
        result = []
        
        for thread in threads:
            thread_dict = asdict(thread)
            # Convert datetime objects to strings in events
            for event in thread_dict['events']:
                if 'timestamp' in event and isinstance(event['timestamp'], datetime):
                    event['timestamp'] = event['timestamp'].isoformat()
            result.append(thread_dict)
        
        return result

    def get_compressed_context(self, session_id: str) -> Dict[str, Any]:
        """Get compressed context for a session."""
        if session_id not in self.compressed_contexts:
            return {}
        
        compression = self.compressed_contexts[session_id]
        result = {
            'session_id': compression.session_id,
            'original_length': compression.original_length,
            'compressed_length': compression.compressed_length,
            'key_elements': compression.key_elements,
            'compression_ratio': compression.compression_ratio,
            'last_updated': compression.last_updated.isoformat()
        }
        
        return result

    # Database operations
    def _save_voice_input_to_db(self, session_id: str, voice_data: Dict[str, Any]):
        """Save voice input to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO voice_inputs 
                (session_id, transcription, voice_characteristics, extracted_context, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                session_id,
                voice_data.get('transcription', ''),
                json.dumps(voice_data.get('voice_characteristics', {}), default=str),
                json.dumps(voice_data.get('extracted_context', {}), default=str),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving voice input to DB: {e}")

    def _save_node_to_db(self, session_id: str, node_id: str, node_data: Dict[str, Any]):
        """Save knowledge node to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_nodes 
                (id, session_id, type, name, properties, confidence, first_mentioned, last_updated, mention_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                node_id, session_id, node_data.get('type'),
                node_data.get('name'), json.dumps(node_data.get('properties', {}), default=str),
                node_data.get('confidence'), 
                node_data.get('first_mentioned').isoformat() if isinstance(node_data.get('first_mentioned'), datetime) else node_data.get('first_mentioned'),
                node_data.get('last_updated').isoformat() if isinstance(node_data.get('last_updated'), datetime) else node_data.get('last_updated'),
                node_data.get('mention_count')
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving node to DB: {e}")

    def _save_relation_to_db(self, session_id: str, source_id: str, target_id: str, edge_data: Dict[str, Any]):
        """Save knowledge relation to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            relation_id = f"{source_id}-{edge_data.get('relation_type', 'unknown')}-{target_id}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO knowledge_relations 
                (id, session_id, source_id, target_id, relation_type, properties, confidence, first_established, last_confirmed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                relation_id, session_id, source_id, target_id,
                edge_data.get('relation_type'), json.dumps(edge_data.get('properties', {}), default=str),
                edge_data.get('confidence'),
                edge_data.get('first_established').isoformat() if isinstance(edge_data.get('first_established'), datetime) else edge_data.get('first_established'),
                edge_data.get('last_confirmed').isoformat() if isinstance(edge_data.get('last_confirmed'), datetime) else edge_data.get('last_confirmed')
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving relation to DB: {e}")

    def _save_plot_thread_to_db(self, session_id: str, thread: PlotThread):
        """Save plot thread to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO plot_threads 
                (thread_id, session_id, title, description, status, priority, related_nodes, events, foreshadowing_elements, resolution_hints, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                thread.thread_id, session_id, thread.title, thread.description,
                thread.status, thread.priority,
                json.dumps(thread.related_nodes), json.dumps(thread.events, default=str),
                json.dumps(thread.foreshadowing_elements), json.dumps(thread.resolution_hints),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving plot thread to DB: {e}")