"""
Network Effect Visualizer

Advanced system for visualizing social network structures, analyzing network effects,
and identifying key patterns in social connections and influence propagation.
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple, Any, Set
from enum import Enum
import json
import networkx as nx
import numpy as np
from collections import defaultdict
import math

class NetworkType(Enum):
    SOCIAL = "social"
    PROFESSIONAL = "professional"
    COLLABORATION = "collaboration"
    COMMUNICATION = "communication"
    INFLUENCE = "influence"

class ConnectionStrength(Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class NodeType(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    GROUP = "group"
    COMMUNITY = "community"

class CentralityType(Enum):
    DEGREE = "degree"
    BETWEENNESS = "betweenness"
    CLOSENESS = "closeness"
    EIGENVECTOR = "eigenvector"
    PAGERANK = "pagerank"

@dataclass
class NetworkNode:
    id: str
    node_type: NodeType = NodeType.PERSON
    name: str = ""
    attributes: Dict[str, Any] = None
    position: Tuple[float, float] = (0.0, 0.0)
    size: float = 1.0
    color: str = "#3498db"
    labels: List[str] = None
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.labels is None:
            self.labels = []

@dataclass
class NetworkEdge:
    id: Optional[int] = None
    source_id: str = ""
    target_id: str = ""
    edge_type: str = "connection"
    strength: ConnectionStrength = ConnectionStrength.MODERATE
    weight: float = 1.0
    attributes: Dict[str, Any] = None
    interaction_count: int = 0
    last_interaction: Optional[datetime] = None
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}

@dataclass
class NetworkMetrics:
    network_id: str = ""
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    clustering_coefficient: float = 0.0
    average_path_length: float = 0.0
    diameter: int = 0
    connected_components: int = 0
    modularity: float = 0.0
    small_world_coefficient: float = 0.0
    centrality_scores: Dict[str, Dict[str, float]] = None
    community_structure: Dict[str, List[str]] = None
    calculated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.centrality_scores is None:
            self.centrality_scores = {}
        if self.community_structure is None:
            self.community_structure = {}

@dataclass
class InfluenceFlow:
    source_id: str = ""
    target_id: str = ""
    influence_type: str = "information"
    strength: float = 0.5
    direction: str = "bidirectional"  # unidirectional, bidirectional
    decay_rate: float = 0.1
    propagation_steps: int = 1
    timestamp: datetime = datetime.now()

class NetworkVisualizer:
    """Advanced social network visualization and analysis system"""
    
    def __init__(self, db_path: str = "social_networks.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the network visualization database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                name TEXT NOT NULL,
                attributes TEXT,
                position_x REAL DEFAULT 0.0,
                position_y REAL DEFAULT 0.0,
                size REAL DEFAULT 1.0,
                color TEXT DEFAULT '#3498db',
                labels TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_edges (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT DEFAULT 'connection',
                strength TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                attributes TEXT,
                interaction_count INTEGER DEFAULT 0,
                last_interaction TEXT,
                created_at TEXT,
                FOREIGN KEY (source_id) REFERENCES network_nodes (id),
                FOREIGN KEY (target_id) REFERENCES network_nodes (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS network_metrics (
                network_id TEXT PRIMARY KEY,
                total_nodes INTEGER,
                total_edges INTEGER,
                density REAL,
                clustering_coefficient REAL,
                average_path_length REAL,
                diameter INTEGER,
                connected_components INTEGER,
                modularity REAL,
                small_world_coefficient REAL,
                centrality_scores TEXT,
                community_structure TEXT,
                calculated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS influence_flows (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                influence_type TEXT DEFAULT 'information',
                strength REAL DEFAULT 0.5,
                direction TEXT DEFAULT 'bidirectional',
                decay_rate REAL DEFAULT 0.1,
                propagation_steps INTEGER DEFAULT 1,
                timestamp TEXT,
                FOREIGN KEY (source_id) REFERENCES network_nodes (id),
                FOREIGN KEY (target_id) REFERENCES network_nodes (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_network_node(self, node: NetworkNode) -> str:
        """Add a node to the network"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO network_nodes 
            (id, node_type, name, attributes, position_x, position_y, size, color, labels, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id, node.node_type.value, node.name, json.dumps(node.attributes),
            node.position[0], node.position[1], node.size, node.color,
            json.dumps(node.labels), node.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return node.id
    
    async def add_network_edge(self, edge: NetworkEdge) -> int:
        """Add an edge to the network"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO network_edges 
            (source_id, target_id, edge_type, strength, weight, attributes,
             interaction_count, last_interaction, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            edge.source_id, edge.target_id, edge.edge_type, edge.strength.value,
            edge.weight, json.dumps(edge.attributes), edge.interaction_count,
            edge.last_interaction.isoformat() if edge.last_interaction else None,
            edge.created_at.isoformat()
        ))
        
        edge_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return edge_id
    
    async def build_network_graph(self, network_type: NetworkType = NetworkType.SOCIAL) -> nx.Graph:
        """Build a NetworkX graph from stored network data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create graph
        if network_type in [NetworkType.INFLUENCE]:
            G = nx.DiGraph()  # Directed graph for influence networks
        else:
            G = nx.Graph()   # Undirected graph for social networks
        
        # Add nodes
        cursor.execute("SELECT * FROM network_nodes")
        for row in cursor.fetchall():
            node_data = dict(zip([col[0] for col in cursor.description], row))
            attributes = json.loads(node_data['attributes']) if node_data['attributes'] else {}
            labels = json.loads(node_data['labels']) if node_data['labels'] else []
            
            G.add_node(node_data['id'], **{
                'node_type': node_data['node_type'],
                'name': node_data['name'],
                'position': (node_data['position_x'], node_data['position_y']),
                'size': node_data['size'],
                'color': node_data['color'],
                'labels': labels,
                **attributes
            })
        
        # Add edges
        cursor.execute("SELECT * FROM network_edges")
        for row in cursor.fetchall():
            edge_data = dict(zip([col[0] for col in cursor.description], row))
            attributes = json.loads(edge_data['attributes']) if edge_data['attributes'] else {}
            
            G.add_edge(edge_data['source_id'], edge_data['target_id'], **{
                'edge_type': edge_data['edge_type'],
                'strength': edge_data['strength'],
                'weight': edge_data['weight'],
                'interaction_count': edge_data['interaction_count'],
                **attributes
            })
        
        conn.close()
        return G
    
    async def calculate_network_metrics(self, network_type: NetworkType = NetworkType.SOCIAL) -> NetworkMetrics:
        """Calculate comprehensive network metrics"""
        G = await self.build_network_graph(network_type)
        
        if len(G.nodes()) == 0:
            return NetworkMetrics()
        
        # Basic metrics
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()
        density = nx.density(G)
        
        # Clustering and path metrics
        clustering_coefficient = nx.average_clustering(G) if total_nodes > 0 else 0
        
        if nx.is_connected(G) and total_nodes > 1:
            average_path_length = nx.average_shortest_path_length(G)
            diameter = nx.diameter(G)
        else:
            average_path_length = float('inf')
            diameter = 0
        
        connected_components = nx.number_connected_components(G)
        
        # Centrality measures
        centrality_scores = {}
        if total_nodes > 0:
            centrality_scores['degree'] = nx.degree_centrality(G)
            centrality_scores['betweenness'] = nx.betweenness_centrality(G)
            centrality_scores['closeness'] = nx.closeness_centrality(G)
            centrality_scores['eigenvector'] = nx.eigenvector_centrality(G, max_iter=1000)
            centrality_scores['pagerank'] = nx.pagerank(G)
        
        # Community detection
        community_structure = {}
        if total_nodes > 2:
            try:
                communities = nx.community.greedy_modularity_communities(G)
                for i, community in enumerate(communities):
                    community_structure[f'community_{i}'] = list(community)
                modularity = nx.community.modularity(G, communities)
            except:
                modularity = 0.0
        else:
            modularity = 0.0
        
        # Small world coefficient
        if total_nodes > 10 and nx.is_connected(G):
            random_graph = nx.random_reference(G)
            lattice_graph = nx.lattice_reference(G)
            
            clustering_ratio = clustering_coefficient / nx.average_clustering(random_graph) if nx.average_clustering(random_graph) > 0 else 1
            path_ratio = average_path_length / nx.average_shortest_path_length(lattice_graph) if nx.average_shortest_path_length(lattice_graph) > 0 else 1
            
            small_world_coefficient = clustering_ratio / path_ratio if path_ratio > 0 else 0
        else:
            small_world_coefficient = 0.0
        
        metrics = NetworkMetrics(
            network_id=f"{network_type.value}_{datetime.now().strftime('%Y%m%d')}",
            total_nodes=total_nodes,
            total_edges=total_edges,
            density=density,
            clustering_coefficient=clustering_coefficient,
            average_path_length=average_path_length,
            diameter=diameter,
            connected_components=connected_components,
            modularity=modularity,
            small_world_coefficient=small_world_coefficient,
            centrality_scores=centrality_scores,
            community_structure=community_structure
        )
        
        # Store metrics
        await self._store_network_metrics(metrics)
        
        return metrics
    
    async def _store_network_metrics(self, metrics: NetworkMetrics):
        """Store calculated network metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO network_metrics 
            (network_id, total_nodes, total_edges, density, clustering_coefficient,
             average_path_length, diameter, connected_components, modularity,
             small_world_coefficient, centrality_scores, community_structure, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.network_id, metrics.total_nodes, metrics.total_edges,
            metrics.density, metrics.clustering_coefficient, metrics.average_path_length,
            metrics.diameter, metrics.connected_components, metrics.modularity,
            metrics.small_world_coefficient, json.dumps(metrics.centrality_scores),
            json.dumps(metrics.community_structure), metrics.calculated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def identify_key_players(self, centrality_type: CentralityType = CentralityType.BETWEENNESS, 
                                 top_n: int = 10) -> List[Dict[str, Any]]:
        """Identify key players in the network based on centrality measures"""
        metrics = await self.calculate_network_metrics()
        
        if not metrics.centrality_scores or centrality_type.value not in metrics.centrality_scores:
            return []
        
        centrality_scores = metrics.centrality_scores[centrality_type.value]
        
        # Sort by centrality score
        sorted_nodes = sorted(centrality_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get node details
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        key_players = []
        for node_id, score in sorted_nodes[:top_n]:
            cursor.execute("SELECT * FROM network_nodes WHERE id = ?", (node_id,))
            node_row = cursor.fetchone()
            
            if node_row:
                node_data = dict(zip([col[0] for col in cursor.description], node_row))
                attributes = json.loads(node_data['attributes']) if node_data['attributes'] else {}
                
                key_players.append({
                    'node_id': node_id,
                    'name': node_data['name'],
                    'node_type': node_data['node_type'],
                    'centrality_score': round(score, 4),
                    'centrality_type': centrality_type.value,
                    'attributes': attributes
                })
        
        conn.close()
        return key_players
    
    async def analyze_influence_propagation(self, source_id: str, influence_type: str = "information", 
                                          steps: int = 3) -> Dict[str, Any]:
        """Analyze how influence propagates through the network"""
        G = await self.build_network_graph(NetworkType.INFLUENCE)
        
        if source_id not in G:
            return {"error": f"Source node {source_id} not found in network"}
        
        # Simulate influence propagation
        influence_levels = {source_id: 1.0}  # Starting influence
        propagation_history = []
        
        current_influenced = {source_id}
        
        for step in range(steps):
            new_influenced = set()
            step_propagation = {}
            
            for node in current_influenced:
                if node in G:
                    neighbors = list(G.neighbors(node))
                    for neighbor in neighbors:
                        if neighbor not in influence_levels:
                            # Calculate influence strength based on edge weight and distance
                            edge_data = G[node][neighbor]
                            edge_weight = edge_data.get('weight', 0.5)
                            decay = 0.8 ** (step + 1)  # Influence decays with steps
                            
                            influence_strength = influence_levels[node] * edge_weight * decay
                            
                            if neighbor not in step_propagation:
                                step_propagation[neighbor] = 0
                            step_propagation[neighbor] = max(step_propagation[neighbor], influence_strength)
                            
                            if influence_strength > 0.1:  # Threshold for significant influence
                                new_influenced.add(neighbor)
            
            # Update influence levels
            for node, strength in step_propagation.items():
                influence_levels[node] = strength
            
            propagation_history.append({
                'step': step + 1,
                'newly_influenced': list(new_influenced),
                'influence_strengths': step_propagation.copy(),
                'total_influenced': len(influence_levels)
            })
            
            current_influenced = new_influenced
            
            if not new_influenced:  # No more propagation
                break
        
        # Calculate reach metrics
        total_reach = len(influence_levels) - 1  # Exclude source
        max_influence = max(influence_levels.values()) if influence_levels else 0
        avg_influence = sum(influence_levels.values()) / len(influence_levels) if influence_levels else 0
        
        return {
            'source_id': source_id,
            'influence_type': influence_type,
            'total_steps': len(propagation_history),
            'total_reach': total_reach,
            'reach_percentage': (total_reach / (len(G) - 1) * 100) if len(G) > 1 else 0,
            'max_influence_strength': round(max_influence, 3),
            'average_influence_strength': round(avg_influence, 3),
            'final_influence_distribution': {k: round(v, 3) for k, v in influence_levels.items()},
            'propagation_history': propagation_history,
            'influence_effectiveness': round(total_reach * avg_influence, 3)
        }
    
    async def detect_communities(self, algorithm: str = "modularity") -> Dict[str, Any]:
        """Detect communities within the network"""
        G = await self.build_network_graph()
        
        if len(G.nodes()) < 3:
            return {"error": "Network too small for community detection"}
        
        try:
            if algorithm == "modularity":
                communities = nx.community.greedy_modularity_communities(G)
                modularity = nx.community.modularity(G, communities)
            elif algorithm == "label_propagation":
                communities = list(nx.community.label_propagation_communities(G))
                modularity = nx.community.modularity(G, communities)
            else:
                communities = nx.community.greedy_modularity_communities(G)
                modularity = nx.community.modularity(G, communities)
            
            # Analyze community structure
            community_analysis = {}
            for i, community in enumerate(communities):
                community_nodes = list(community)
                subgraph = G.subgraph(community_nodes)
                
                # Get node details
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                node_details = []
                for node_id in community_nodes:
                    cursor.execute("SELECT name, node_type FROM network_nodes WHERE id = ?", (node_id,))
                    row = cursor.fetchone()
                    if row:
                        node_details.append({'id': node_id, 'name': row[0], 'type': row[1]})
                
                conn.close()
                
                community_analysis[f'community_{i}'] = {
                    'size': len(community_nodes),
                    'density': nx.density(subgraph),
                    'clustering': nx.average_clustering(subgraph),
                    'members': node_details,
                    'internal_edges': subgraph.number_of_edges(),
                    'external_connections': sum(1 for node in community_nodes 
                                             for neighbor in G.neighbors(node) 
                                             if neighbor not in community_nodes)
                }
            
            return {
                'algorithm': algorithm,
                'total_communities': len(communities),
                'modularity_score': round(modularity, 4),
                'community_sizes': [len(c) for c in communities],
                'largest_community_size': max(len(c) for c in communities),
                'smallest_community_size': min(len(c) for c in communities),
                'average_community_size': sum(len(c) for c in communities) / len(communities),
                'communities': community_analysis
            }
            
        except Exception as e:
            return {"error": f"Community detection failed: {str(e)}"}
    
    async def analyze_network_evolution(self, days_back: int = 30) -> Dict[str, Any]:
        """Analyze how the network has evolved over time"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Get network growth metrics
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_nodes
            FROM network_nodes 
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (start_date.isoformat(),))
        
        node_growth = {}
        for row in cursor.fetchall():
            node_growth[row[0]] = row[1]
        
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_edges
            FROM network_edges 
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (start_date.isoformat(),))
        
        edge_growth = {}
        for row in cursor.fetchall():
            edge_growth[row[0]] = row[1]
        
        # Calculate growth rates
        total_new_nodes = sum(node_growth.values())
        total_new_edges = sum(edge_growth.values())
        
        nodes_per_day = total_new_nodes / days_back if days_back > 0 else 0
        edges_per_day = total_new_edges / days_back if days_back > 0 else 0
        
        # Get current network size
        cursor.execute("SELECT COUNT(*) FROM network_nodes")
        total_nodes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM network_edges")
        total_edges = cursor.fetchone()[0]
        
        conn.close()
        
        # Calculate network health metrics
        growth_rate_nodes = (nodes_per_day / total_nodes * 100) if total_nodes > 0 else 0
        growth_rate_edges = (edges_per_day / total_edges * 100) if total_edges > 0 else 0
        
        return {
            'analysis_period_days': days_back,
            'total_nodes': total_nodes,
            'total_edges': total_edges,
            'new_nodes_added': total_new_nodes,
            'new_edges_added': total_new_edges,
            'average_nodes_per_day': round(nodes_per_day, 2),
            'average_edges_per_day': round(edges_per_day, 2),
            'node_growth_rate_percent': round(growth_rate_nodes, 2),
            'edge_growth_rate_percent': round(growth_rate_edges, 2),
            'network_health': 'growing' if growth_rate_nodes > 0 and growth_rate_edges > 0 else 'stable' if growth_rate_nodes == 0 else 'declining',
            'daily_node_growth': node_growth,
            'daily_edge_growth': edge_growth
        }
    
    async def find_shortest_paths(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """Find all shortest paths between two nodes"""
        G = await self.build_network_graph()
        
        if source_id not in G or target_id not in G:
            return {"error": "Source or target node not found in network"}
        
        try:
            # Find all shortest paths
            all_paths = list(nx.all_shortest_paths(G, source_id, target_id))
            path_length = nx.shortest_path_length(G, source_id, target_id)
            
            # Analyze path qualities
            path_analysis = []
            for i, path in enumerate(all_paths):
                path_strength = 1.0
                path_edges = []
                
                for j in range(len(path) - 1):
                    edge_data = G[path[j]][path[j+1]]
                    edge_weight = edge_data.get('weight', 0.5)
                    path_strength *= edge_weight
                    
                    path_edges.append({
                        'from': path[j],
                        'to': path[j+1],
                        'weight': edge_weight,
                        'type': edge_data.get('edge_type', 'connection')
                    })
                
                path_analysis.append({
                    'path_id': i,
                    'nodes': path,
                    'length': len(path) - 1,
                    'strength': round(path_strength, 4),
                    'edges': path_edges
                })
            
            # Sort by path strength
            path_analysis.sort(key=lambda x: x['strength'], reverse=True)
            
            return {
                'source_id': source_id,
                'target_id': target_id,
                'shortest_path_length': path_length,
                'total_shortest_paths': len(all_paths),
                'strongest_path': path_analysis[0] if path_analysis else None,
                'all_paths': path_analysis,
                'connection_strength': round(path_analysis[0]['strength'], 4) if path_analysis else 0
            }
            
        except nx.NetworkXNoPath:
            return {
                'source_id': source_id,
                'target_id': target_id,
                'connected': False,
                'message': "No path exists between the specified nodes"
            }

# Demo function
async def demo_network_visualizer():
    """Demonstrate the Network Visualizer functionality"""
    print("🕸️ Network Visualizer Demo")
    print("=" * 50)
    
    visualizer = NetworkVisualizer()
    
    # Create network nodes
    print("\n1. Creating Network Nodes...")
    nodes = [
        NetworkNode(
            id="alice",
            name="Alice Johnson",
            node_type=NodeType.PERSON,
            attributes={"department": "Engineering", "role": "Senior Developer"},
            size=1.5,
            color="#e74c3c"
        ),
        NetworkNode(
            id="bob",
            name="Bob Smith",
            node_type=NodeType.PERSON,
            attributes={"department": "Engineering", "role": "Team Lead"},
            size=1.8,
            color="#3498db"
        ),
        NetworkNode(
            id="carol",
            name="Carol Davis",
            node_type=NodeType.PERSON,
            attributes={"department": "Marketing", "role": "Manager"},
            size=1.3,
            color="#2ecc71"
        ),
        NetworkNode(
            id="david",
            name="David Wilson",
            node_type=NodeType.PERSON,
            attributes={"department": "Engineering", "role": "Developer"},
            size=1.2,
            color="#f39c12"
        ),
        NetworkNode(
            id="engineering_team",
            name="Engineering Team",
            node_type=NodeType.GROUP,
            attributes={"department": "Engineering", "size": 15},
            size=2.0,
            color="#9b59b6"
        )
    ]
    
    for node in nodes:
        await visualizer.add_network_node(node)
        print(f"✅ Added node: {node.name}")
    
    # Create network edges
    print("\n2. Creating Network Connections...")
    edges = [
        NetworkEdge(
            source_id="alice",
            target_id="bob",
            edge_type="collaboration",
            strength=ConnectionStrength.STRONG,
            weight=0.9,
            interaction_count=15,
            attributes={"project": "AI Platform"}
        ),
        NetworkEdge(
            source_id="bob",
            target_id="david",
            edge_type="mentorship",
            strength=ConnectionStrength.STRONG,
            weight=0.8,
            interaction_count=12,
            attributes={"type": "technical_guidance"}
        ),
        NetworkEdge(
            source_id="alice",
            target_id="carol",
            edge_type="cross_functional",
            strength=ConnectionStrength.MODERATE,
            weight=0.6,
            interaction_count=8,
            attributes={"project": "Product Launch"}
        ),
        NetworkEdge(
            source_id="carol",
            target_id="david",
            edge_type="project",
            strength=ConnectionStrength.WEAK,
            weight=0.4,
            interaction_count=3,
            attributes={"project": "Documentation"}
        ),
        NetworkEdge(
            source_id="alice",
            target_id="engineering_team",
            edge_type="membership",
            strength=ConnectionStrength.VERY_STRONG,
            weight=1.0,
            interaction_count=25
        ),
        NetworkEdge(
            source_id="bob",
            target_id="engineering_team",
            edge_type="leadership",
            strength=ConnectionStrength.VERY_STRONG,
            weight=1.0,
            interaction_count=30
        ),
        NetworkEdge(
            source_id="david",
            target_id="engineering_team",
            edge_type="membership",
            strength=ConnectionStrength.STRONG,
            weight=0.8,
            interaction_count=20
        )
    ]
    
    for edge in edges:
        await visualizer.add_network_edge(edge)
        print(f"✅ Added connection: {edge.source_id} ↔ {edge.target_id} ({edge.strength.value})")
    
    # Calculate network metrics
    print("\n3. Calculating Network Metrics...")
    metrics = await visualizer.calculate_network_metrics()
    
    print(f"📊 Network Size: {metrics.total_nodes} nodes, {metrics.total_edges} edges")
    print(f"📊 Network Density: {metrics.density:.3f}")
    print(f"📊 Clustering Coefficient: {metrics.clustering_coefficient:.3f}")
    print(f"📊 Average Path Length: {metrics.average_path_length:.2f}")
    print(f"📊 Connected Components: {metrics.connected_components}")
    print(f"📊 Modularity: {metrics.modularity:.3f}")
    
    # Identify key players
    print("\n4. Key Players Analysis...")
    for centrality_type in [CentralityType.BETWEENNESS, CentralityType.DEGREE, CentralityType.PAGERANK]:
        key_players = await visualizer.identify_key_players(centrality_type, 3)
        print(f"\n📈 Top 3 by {centrality_type.value} centrality:")
        for i, player in enumerate(key_players, 1):
            print(f"   {i}. {player['name']}: {player['centrality_score']:.4f}")
    
    # Analyze influence propagation
    print("\n5. Influence Propagation Analysis...")
    influence_analysis = await visualizer.analyze_influence_propagation("bob", "technical_knowledge", 3)
    
    print(f"🌊 Influence from {influence_analysis['source_id']}:")
    print(f"   Total reach: {influence_analysis['total_reach']} people")
    print(f"   Reach percentage: {influence_analysis['reach_percentage']:.1f}%")
    print(f"   Effectiveness score: {influence_analysis['influence_effectiveness']:.2f}")
    
    print("\n   Propagation steps:")
    for step_data in influence_analysis['propagation_history']:
        print(f"   Step {step_data['step']}: {len(step_data['newly_influenced'])} new people influenced")
    
    # Detect communities
    print("\n6. Community Detection...")
    communities = await visualizer.detect_communities("modularity")
    
    print(f"🏘️ Found {communities['total_communities']} communities")
    print(f"🏘️ Modularity score: {communities['modularity_score']}")
    print(f"🏘️ Largest community: {communities['largest_community_size']} members")
    
    for comm_id, comm_data in list(communities['communities'].items())[:2]:  # Show first 2 communities
        print(f"\n   {comm_id}: {comm_data['size']} members")
        print(f"   Density: {comm_data['density']:.3f}")
        print(f"   Members: {', '.join([m['name'] for m in comm_data['members']])}")
    
    # Find shortest paths
    print("\n7. Path Analysis...")
    path_analysis = await visualizer.find_shortest_paths("alice", "david")
    
    print(f"🗺️ Paths from Alice to David:")
    print(f"   Shortest path length: {path_analysis['shortest_path_length']}")
    print(f"   Total shortest paths: {path_analysis['total_shortest_paths']}")
    
    if path_analysis['strongest_path']:
        strongest = path_analysis['strongest_path']
        print(f"   Strongest path: {' → '.join(strongest['nodes'])}")
        print(f"   Connection strength: {strongest['strength']:.4f}")
    
    # Network evolution
    print("\n8. Network Evolution Analysis...")
    evolution = await visualizer.analyze_network_evolution(7)  # Last 7 days
    
    print(f"📈 Network growth (7 days):")
    print(f"   Current size: {evolution['total_nodes']} nodes, {evolution['total_edges']} edges")
    print(f"   New nodes: {evolution['new_nodes_added']}")
    print(f"   New connections: {evolution['new_edges_added']}")
    print(f"   Network health: {evolution['network_health']}")
    print(f"   Growth rate: {evolution['node_growth_rate_percent']:.2f}% nodes, {evolution['edge_growth_rate_percent']:.2f}% edges")
    
    print("\n✅ Network Visualizer Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_network_visualizer())