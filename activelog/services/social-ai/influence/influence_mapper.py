"""
Influence Network Mapping

AI-powered system for mapping, analyzing, and visualizing influence networks,
identifying key influencers, influence paths, and power dynamics.
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
from collections import defaultdict, deque
import math

class InfluenceType(Enum):
    FORMAL_AUTHORITY = "formal_authority"
    EXPERTISE = "expertise"
    INFORMATION = "information"
    PERSONAL = "personal"
    RESOURCE = "resource"
    NETWORK = "network"
    THOUGHT_LEADERSHIP = "thought_leadership"
    SOCIAL = "social"

class InfluenceDirection(Enum):
    INBOUND = "inbound"  # Receives influence
    OUTBOUND = "outbound"  # Exerts influence
    BIDIRECTIONAL = "bidirectional"  # Mutual influence

class InfluencerTier(Enum):
    MEGA_INFLUENCER = "mega_influencer"  # Top 1%
    MACRO_INFLUENCER = "macro_influencer"  # Top 5%
    MICRO_INFLUENCER = "micro_influencer"  # Top 15%
    REGULAR_MEMBER = "regular_member"  # Everyone else

@dataclass
class InfluenceNode:
    id: str = ""
    name: str = ""
    role: str = ""
    department: str = ""
    formal_authority_level: float = 0.0  # Org chart position influence
    expertise_areas: List[str] = None
    influence_scores: Dict[str, float] = None  # Type -> score mapping
    total_influence_score: float = 0.0
    influence_reach: int = 0  # Number of people they can influence
    influence_depth: int = 0  # Degrees of separation their influence travels
    influence_tier: InfluencerTier = InfluencerTier.REGULAR_MEMBER
    influence_growth_rate: float = 0.0  # Rate of influence change
    key_relationships: List[str] = None  # Important connection IDs
    influence_tactics: List[str] = None  # How they exert influence
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.expertise_areas is None:
            self.expertise_areas = []
        if self.influence_scores is None:
            self.influence_scores = {}
        if self.key_relationships is None:
            self.key_relationships = []
        if self.influence_tactics is None:
            self.influence_tactics = []

@dataclass
class InfluenceEdge:
    id: Optional[int] = None
    source_id: str = ""
    target_id: str = ""
    influence_type: InfluenceType = InfluenceType.PERSONAL
    influence_strength: float = 0.0  # 0-1 strength of influence
    direction: InfluenceDirection = InfluenceDirection.OUTBOUND
    context: str = ""  # Project, topic, or domain context
    evidence: List[Dict[str, Any]] = None  # Supporting evidence for influence
    frequency: float = 1.0  # How often influence is exercised
    reciprocity: float = 0.0  # Level of mutual influence
    decay_rate: float = 0.1  # How quickly influence diminishes
    established_date: datetime = datetime.now()
    last_observed: datetime = datetime.now()

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []

@dataclass
class InfluencePath:
    id: Optional[int] = None
    source_id: str = ""
    target_id: str = ""
    path_nodes: List[str] = None  # Ordered list of node IDs in path
    path_length: int = 0
    total_influence_strength: float = 0.0
    weakest_link_strength: float = 0.0
    path_type: str = "direct"  # direct, indirect, multi_hop
    influence_types_in_path: List[str] = None  # Types of influence along path
    bottleneck_nodes: List[str] = None  # Critical nodes that could block influence
    alternative_paths: int = 0  # Number of alternative paths available
    path_reliability: float = 0.0  # Stability of the influence path
    calculated_at: datetime = datetime.now()

    def __post_init__(self):
        if self.path_nodes is None:
            self.path_nodes = []
        if self.influence_types_in_path is None:
            self.influence_types_in_path = []
        if self.bottleneck_nodes is None:
            self.bottleneck_nodes = []

@dataclass
class InfluenceCluster:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    member_ids: List[str] = None
    cluster_leader: str = ""  # Most influential member
    cluster_influence_score: float = 0.0
    internal_cohesion: float = 0.0  # How tightly connected internally
    external_connections: int = 0  # Connections to other clusters
    dominant_influence_types: List[str] = None  # Most common influence types
    cluster_topics: List[str] = None  # Main areas of influence
    cluster_stability: float = 0.0  # How stable the cluster is over time
    formed_date: datetime = datetime.now()
    last_updated: datetime = datetime.now()

    def __post_init__(self):
        if self.member_ids is None:
            self.member_ids = []
        if self.dominant_influence_types is None:
            self.dominant_influence_types = []
        if self.cluster_topics is None:
            self.cluster_topics = []

@dataclass
class InfluenceCampaign:
    id: Optional[int] = None
    name: str = ""
    objective: str = ""
    target_audience: List[str] = None  # Target node IDs
    key_influencers: List[str] = None  # Selected influencer IDs
    influence_strategy: str = ""
    campaign_messages: List[str] = None
    expected_reach: int = 0
    predicted_effectiveness: float = 0.0
    campaign_timeline: List[Dict[str, Any]] = None
    success_metrics: List[str] = None
    status: str = "planned"  # planned, active, completed, cancelled
    created_at: datetime = datetime.now()

    def __post_init__(self):
        if self.target_audience is None:
            self.target_audience = []
        if self.key_influencers is None:
            self.key_influencers = []
        if self.campaign_messages is None:
            self.campaign_messages = []
        if self.campaign_timeline is None:
            self.campaign_timeline = []
        if self.success_metrics is None:
            self.success_metrics = []

class InfluenceMapper:
    """AI-powered influence network mapping and analysis system"""
    
    def __init__(self, db_path: str = "influence_networks.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the influence mapping database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS influence_nodes (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                department TEXT,
                formal_authority_level REAL DEFAULT 0.0,
                expertise_areas TEXT,
                influence_scores TEXT,
                total_influence_score REAL DEFAULT 0.0,
                influence_reach INTEGER DEFAULT 0,
                influence_depth INTEGER DEFAULT 0,
                influence_tier TEXT DEFAULT 'regular_member',
                influence_growth_rate REAL DEFAULT 0.0,
                key_relationships TEXT,
                influence_tactics TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS influence_edges (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                influence_type TEXT NOT NULL,
                influence_strength REAL DEFAULT 0.0,
                direction TEXT DEFAULT 'outbound',
                context TEXT,
                evidence TEXT,
                frequency REAL DEFAULT 1.0,
                reciprocity REAL DEFAULT 0.0,
                decay_rate REAL DEFAULT 0.1,
                established_date TEXT,
                last_observed TEXT,
                FOREIGN KEY (source_id) REFERENCES influence_nodes (id),
                FOREIGN KEY (target_id) REFERENCES influence_nodes (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS influence_paths (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                path_nodes TEXT,
                path_length INTEGER,
                total_influence_strength REAL,
                weakest_link_strength REAL,
                path_type TEXT DEFAULT 'direct',
                influence_types_in_path TEXT,
                bottleneck_nodes TEXT,
                alternative_paths INTEGER DEFAULT 0,
                path_reliability REAL DEFAULT 0.0,
                calculated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS influence_clusters (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                member_ids TEXT,
                cluster_leader TEXT,
                cluster_influence_score REAL DEFAULT 0.0,
                internal_cohesion REAL DEFAULT 0.0,
                external_connections INTEGER DEFAULT 0,
                dominant_influence_types TEXT,
                cluster_topics TEXT,
                cluster_stability REAL DEFAULT 0.0,
                formed_date TEXT,
                last_updated TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS influence_campaigns (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                objective TEXT,
                target_audience TEXT,
                key_influencers TEXT,
                influence_strategy TEXT,
                campaign_messages TEXT,
                expected_reach INTEGER DEFAULT 0,
                predicted_effectiveness REAL DEFAULT 0.0,
                campaign_timeline TEXT,
                success_metrics TEXT,
                status TEXT DEFAULT 'planned',
                created_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def add_influence_node(self, node: InfluenceNode) -> str:
        """Add or update an influence node"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO influence_nodes 
            (id, name, role, department, formal_authority_level, expertise_areas,
             influence_scores, total_influence_score, influence_reach, influence_depth,
             influence_tier, influence_growth_rate, key_relationships, influence_tactics,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node.id, node.name, node.role, node.department, node.formal_authority_level,
            json.dumps(node.expertise_areas), json.dumps(node.influence_scores),
            node.total_influence_score, node.influence_reach, node.influence_depth,
            node.influence_tier.value, node.influence_growth_rate,
            json.dumps(node.key_relationships), json.dumps(node.influence_tactics),
            node.created_at.isoformat(), node.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return node.id
    
    async def add_influence_edge(self, edge: InfluenceEdge) -> int:
        """Add or update an influence relationship"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO influence_edges 
            (source_id, target_id, influence_type, influence_strength, direction,
             context, evidence, frequency, reciprocity, decay_rate, established_date, last_observed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            edge.source_id, edge.target_id, edge.influence_type.value, edge.influence_strength,
            edge.direction.value, edge.context, json.dumps(edge.evidence),
            edge.frequency, edge.reciprocity, edge.decay_rate,
            edge.established_date.isoformat(), edge.last_observed.isoformat()
        ))
        
        edge_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return edge_id
    
    async def calculate_influence_scores(self) -> Dict[str, float]:
        """Calculate comprehensive influence scores for all nodes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build influence network graph
        G = await self._build_influence_graph(conn)
        
        if G.number_of_nodes() == 0:
            conn.close()
            return {}
        
        # Calculate various centrality measures
        centrality_scores = await self._calculate_centrality_measures(G)
        
        # Calculate composite influence scores
        influence_scores = {}
        
        for node_id in G.nodes():
            # Get node data
            cursor.execute("SELECT * FROM influence_nodes WHERE id = ?", (node_id,))
            node_row = cursor.fetchone()
            
            if node_row:
                node_cols = [description[0] for description in cursor.description]
                node_data = dict(zip(node_cols, node_row))
                
                # Calculate weighted influence score
                formal_weight = 0.2
                expertise_weight = 0.15
                network_weight = 0.35
                personal_weight = 0.3
                
                formal_score = node_data['formal_authority_level']
                expertise_score = len(json.loads(node_data['expertise_areas']) if node_data['expertise_areas'] else []) / 10.0
                network_score = centrality_scores.get('pagerank', {}).get(node_id, 0.0)
                personal_score = centrality_scores.get('eigenvector', {}).get(node_id, 0.0)
                
                total_score = (
                    formal_score * formal_weight +
                    expertise_score * expertise_weight +
                    network_score * network_weight +
                    personal_score * personal_weight
                )
                
                influence_scores[node_id] = min(1.0, total_score)
                
                # Calculate influence reach and depth
                reach, depth = await self._calculate_influence_reach_depth(G, node_id)
                
                # Determine influence tier
                tier = await self._determine_influence_tier(total_score, reach)
                
                # Update node with calculated scores
                cursor.execute("""
                    UPDATE influence_nodes 
                    SET total_influence_score = ?, influence_reach = ?, influence_depth = ?,
                        influence_tier = ?, updated_at = ?
                    WHERE id = ?
                """, (
                    total_score, reach, depth, tier.value, datetime.now().isoformat(), node_id
                ))
        
        conn.commit()
        conn.close()
        return influence_scores
    
    async def _build_influence_graph(self, conn) -> nx.DiGraph:
        """Build NetworkX directed graph from influence edges"""
        cursor = conn.cursor()
        
        G = nx.DiGraph()
        
        # Add nodes
        cursor.execute("SELECT id FROM influence_nodes")
        for (node_id,) in cursor.fetchall():
            G.add_node(node_id)
        
        # Add edges with weights
        cursor.execute("SELECT source_id, target_id, influence_strength FROM influence_edges")
        for source_id, target_id, strength in cursor.fetchall():
            G.add_edge(source_id, target_id, weight=strength)
        
        return G
    
    async def _calculate_centrality_measures(self, G: nx.DiGraph) -> Dict[str, Dict[str, float]]:
        """Calculate various centrality measures"""
        centrality_scores = {}
        
        if G.number_of_nodes() == 0:
            return centrality_scores
        
        try:
            # PageRank - measures importance based on incoming links
            centrality_scores['pagerank'] = nx.pagerank(G, weight='weight')
            
            # Eigenvector centrality - measures influence based on connections to influential nodes
            try:
                centrality_scores['eigenvector'] = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
            except:
                centrality_scores['eigenvector'] = {node: 0.0 for node in G.nodes()}
            
            # Betweenness centrality - measures brokerage power
            centrality_scores['betweenness'] = nx.betweenness_centrality(G, weight='weight')
            
            # Closeness centrality - measures access to others
            centrality_scores['closeness'] = nx.closeness_centrality(G, distance='weight')
            
            # In-degree centrality - measures how much influence flows to a node
            centrality_scores['in_degree'] = dict(G.in_degree(weight='weight'))
            
            # Out-degree centrality - measures how much influence flows from a node
            centrality_scores['out_degree'] = dict(G.out_degree(weight='weight'))
            
            # Normalize scores
            for measure in centrality_scores:
                if centrality_scores[measure]:
                    max_score = max(centrality_scores[measure].values())
                    if max_score > 0:
                        centrality_scores[measure] = {
                            node: score / max_score 
                            for node, score in centrality_scores[measure].items()
                        }
            
        except Exception as e:
            print(f"Error calculating centrality measures: {e}")
            centrality_scores = {measure: {} for measure in ['pagerank', 'eigenvector', 'betweenness', 'closeness', 'in_degree', 'out_degree']}
        
        return centrality_scores
    
    async def _calculate_influence_reach_depth(self, G: nx.DiGraph, node_id: str) -> Tuple[int, int]:
        """Calculate how far and deep a node's influence extends"""
        if node_id not in G:
            return 0, 0
        
        # Calculate reach (number of nodes reachable)
        reachable = set()
        
        # BFS to find all reachable nodes
        visited = set()
        queue = deque([node_id])
        depth = 0
        max_depth = 0
        
        while queue:
            level_size = len(queue)
            depth += 1
            max_depth = depth
            
            for _ in range(level_size):
                current = queue.popleft()
                if current in visited:
                    continue
                
                visited.add(current)
                if current != node_id:
                    reachable.add(current)
                
                # Add neighbors with sufficient influence strength
                for neighbor in G.neighbors(current):
                    edge_data = G[current][neighbor]
                    influence_strength = edge_data.get('weight', 0)
                    
                    # Only follow edges with meaningful influence (> 0.1)
                    if influence_strength > 0.1 and neighbor not in visited:
                        queue.append(neighbor)
        
        return len(reachable), max_depth - 1  # Subtract 1 since we start at depth 0
    
    async def _determine_influence_tier(self, total_score: float, reach: int) -> InfluencerTier:
        """Determine influence tier based on score and reach"""
        if total_score >= 0.8 and reach >= 20:
            return InfluencerTier.MEGA_INFLUENCER
        elif total_score >= 0.6 and reach >= 10:
            return InfluencerTier.MACRO_INFLUENCER
        elif total_score >= 0.4 and reach >= 5:
            return InfluencerTier.MICRO_INFLUENCER
        else:
            return InfluencerTier.REGULAR_MEMBER
    
    async def find_influence_paths(self, source_id: str, target_id: str, max_paths: int = 5) -> List[InfluencePath]:
        """Find influence paths between two nodes"""
        conn = sqlite3.connect(self.db_path)
        G = await self._build_influence_graph(conn)
        
        if source_id not in G or target_id not in G:
            conn.close()
            return []
        
        influence_paths = []
        
        try:
            # Find all simple paths up to length 5
            all_paths = list(nx.all_simple_paths(G, source_id, target_id, cutoff=5))
            
            # Limit to max_paths
            all_paths = all_paths[:max_paths]
            
            for path_nodes in all_paths:
                # Calculate path influence strength
                total_strength = 1.0
                weakest_link = 1.0
                influence_types = []
                
                for i in range(len(path_nodes) - 1):
                    current_node = path_nodes[i]
                    next_node = path_nodes[i + 1]
                    
                    edge_data = G[current_node][next_node]
                    edge_strength = edge_data.get('weight', 0.5)
                    
                    total_strength *= edge_strength
                    weakest_link = min(weakest_link, edge_strength)
                    
                    # Get influence type for this edge
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT influence_type FROM influence_edges 
                        WHERE source_id = ? AND target_id = ?
                    """, (current_node, next_node))
                    
                    edge_row = cursor.fetchone()
                    if edge_row:
                        influence_types.append(edge_row[0])
                
                # Identify bottleneck nodes (nodes with high betweenness in this path)
                bottleneck_nodes = await self._identify_bottlenecks(path_nodes[1:-1], G)
                
                # Count alternative paths
                try:
                    alternative_count = len(list(nx.all_simple_paths(G, source_id, target_id, cutoff=5))) - 1
                except:
                    alternative_count = 0
                
                # Calculate path reliability
                path_reliability = total_strength * (1.0 / max(1, len(path_nodes) - 1))
                
                path = InfluencePath(
                    source_id=source_id,
                    target_id=target_id,
                    path_nodes=path_nodes,
                    path_length=len(path_nodes) - 1,
                    total_influence_strength=total_strength,
                    weakest_link_strength=weakest_link,
                    path_type="direct" if len(path_nodes) == 2 else "indirect",
                    influence_types_in_path=list(set(influence_types)),
                    bottleneck_nodes=bottleneck_nodes,
                    alternative_paths=alternative_count,
                    path_reliability=path_reliability
                )
                
                influence_paths.append(path)
                
                # Store path in database
                await self._store_influence_path(path, conn)
        
        except nx.NetworkXNoPath:
            pass  # No path exists
        
        conn.close()
        return influence_paths
    
    async def _identify_bottlenecks(self, intermediate_nodes: List[str], G: nx.DiGraph) -> List[str]:
        """Identify bottleneck nodes in a path"""
        bottlenecks = []
        
        # Calculate betweenness centrality for the subgraph
        if len(intermediate_nodes) > 0:
            try:
                betweenness = nx.betweenness_centrality(G)
                avg_betweenness = np.mean(list(betweenness.values()))
                
                for node in intermediate_nodes:
                    if betweenness.get(node, 0) > avg_betweenness * 1.5:
                        bottlenecks.append(node)
            except:
                pass  # Error in calculation, skip bottleneck identification
        
        return bottlenecks
    
    async def detect_influence_clusters(self) -> List[InfluenceCluster]:
        """Detect clusters of mutually influencing nodes"""
        conn = sqlite3.connect(self.db_path)
        G = await self._build_influence_graph(conn)
        
        clusters = []
        
        if G.number_of_nodes() < 3:
            conn.close()
            return clusters
        
        try:
            # Convert to undirected for community detection
            G_undirected = G.to_undirected()
            
            # Detect communities using modularity-based method
            communities = nx.community.greedy_modularity_communities(G_undirected)
            
            cursor = conn.cursor()
            
            for i, community in enumerate(communities):
                if len(community) >= 3:  # Minimum cluster size
                    member_ids = list(community)
                    
                    # Find cluster leader (highest influence score)
                    leader_id = ""
                    max_influence = 0
                    
                    for member_id in member_ids:
                        cursor.execute("SELECT total_influence_score FROM influence_nodes WHERE id = ?", (member_id,))
                        score_row = cursor.fetchone()
                        if score_row and score_row[0] > max_influence:
                            max_influence = score_row[0]
                            leader_id = member_id
                    
                    # Calculate cluster metrics
                    internal_cohesion = await self._calculate_internal_cohesion(community, G)
                    external_connections = await self._count_external_connections(community, G)
                    cluster_influence_score = await self._calculate_cluster_influence(member_ids, conn)
                    
                    # Identify dominant influence types
                    dominant_types = await self._get_dominant_influence_types(member_ids, conn)
                    
                    cluster = InfluenceCluster(
                        name=f"Influence Cluster {i+1}",
                        description=f"Cluster of {len(member_ids)} mutually influencing members",
                        member_ids=member_ids,
                        cluster_leader=leader_id,
                        cluster_influence_score=cluster_influence_score,
                        internal_cohesion=internal_cohesion,
                        external_connections=external_connections,
                        dominant_influence_types=dominant_types,
                        cluster_stability=0.8  # Default stability score
                    )
                    
                    clusters.append(cluster)
                    await self._store_influence_cluster(cluster, conn)
        
        except Exception as e:
            print(f"Error detecting influence clusters: {e}")
        
        conn.close()
        return clusters
    
    async def _calculate_internal_cohesion(self, community: Set[str], G: nx.DiGraph) -> float:
        """Calculate internal cohesion of a community"""
        if len(community) < 2:
            return 0.0
        
        internal_edges = 0
        possible_edges = len(community) * (len(community) - 1)  # Directed graph
        
        for node1 in community:
            for node2 in community:
                if node1 != node2 and G.has_edge(node1, node2):
                    internal_edges += 1
        
        return internal_edges / possible_edges if possible_edges > 0 else 0.0
    
    async def _count_external_connections(self, community: Set[str], G: nx.DiGraph) -> int:
        """Count connections to nodes outside the community"""
        external_connections = 0
        
        for node in community:
            for neighbor in G.neighbors(node):
                if neighbor not in community:
                    external_connections += 1
        
        return external_connections
    
    async def _calculate_cluster_influence(self, member_ids: List[str], conn) -> float:
        """Calculate overall influence score of a cluster"""
        cursor = conn.cursor()
        
        total_influence = 0.0
        for member_id in member_ids:
            cursor.execute("SELECT total_influence_score FROM influence_nodes WHERE id = ?", (member_id,))
            score_row = cursor.fetchone()
            if score_row:
                total_influence += score_row[0]
        
        return total_influence / len(member_ids) if member_ids else 0.0
    
    async def _get_dominant_influence_types(self, member_ids: List[str], conn) -> List[str]:
        """Get dominant influence types within a cluster"""
        cursor = conn.cursor()
        
        type_counts = defaultdict(int)
        
        # Count influence types for edges within the cluster
        for source_id in member_ids:
            for target_id in member_ids:
                if source_id != target_id:
                    cursor.execute("""
                        SELECT influence_type FROM influence_edges 
                        WHERE source_id = ? AND target_id = ?
                    """, (source_id, target_id))
                    
                    edge_row = cursor.fetchone()
                    if edge_row:
                        type_counts[edge_row[0]] += 1
        
        # Return top 3 most common types
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        return [influence_type for influence_type, count in sorted_types[:3]]
    
    async def _store_influence_path(self, path: InfluencePath, conn):
        """Store influence path in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO influence_paths 
            (source_id, target_id, path_nodes, path_length, total_influence_strength,
             weakest_link_strength, path_type, influence_types_in_path, bottleneck_nodes,
             alternative_paths, path_reliability, calculated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            path.source_id, path.target_id, json.dumps(path.path_nodes), path.path_length,
            path.total_influence_strength, path.weakest_link_strength, path.path_type,
            json.dumps(path.influence_types_in_path), json.dumps(path.bottleneck_nodes),
            path.alternative_paths, path.path_reliability, path.calculated_at.isoformat()
        ))
        
        path.id = cursor.lastrowid
    
    async def _store_influence_cluster(self, cluster: InfluenceCluster, conn):
        """Store influence cluster in database"""
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO influence_clusters 
            (name, description, member_ids, cluster_leader, cluster_influence_score,
             internal_cohesion, external_connections, dominant_influence_types,
             cluster_topics, cluster_stability, formed_date, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cluster.name, cluster.description, json.dumps(cluster.member_ids),
            cluster.cluster_leader, cluster.cluster_influence_score, cluster.internal_cohesion,
            cluster.external_connections, json.dumps(cluster.dominant_influence_types),
            json.dumps(cluster.cluster_topics), cluster.cluster_stability,
            cluster.formed_date.isoformat(), cluster.last_updated.isoformat()
        ))
        
        cluster.id = cursor.lastrowid
    
    async def get_top_influencers(self, limit: int = 10, influence_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get top influencers in the network"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if influence_type:
            # Filter by specific influence type - would need to join with edges
            # For now, just return top overall influencers
            pass
        
        cursor.execute("""
            SELECT id, name, role, department, total_influence_score, influence_reach, 
                   influence_depth, influence_tier
            FROM influence_nodes 
            ORDER BY total_influence_score DESC 
            LIMIT ?
        """, (limit,))
        
        influencers = []
        cols = [description[0] for description in cursor.description]
        
        for row in cursor.fetchall():
            influencer_data = dict(zip(cols, row))
            influencers.append(influencer_data)
        
        conn.close()
        return influencers
    
    async def analyze_influence_network_health(self) -> Dict[str, Any]:
        """Analyze overall health and structure of the influence network"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        G = await self._build_influence_graph(conn)
        
        # Basic network metrics
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()
        density = nx.density(G) if total_nodes > 0 else 0
        
        # Influence distribution
        cursor.execute("SELECT AVG(total_influence_score), MIN(total_influence_score), MAX(total_influence_score) FROM influence_nodes")
        avg_influence, min_influence, max_influence = cursor.fetchone()
        
        # Tier distribution
        cursor.execute("SELECT influence_tier, COUNT(*) FROM influence_nodes GROUP BY influence_tier")
        tier_distribution = dict(cursor.fetchall())
        
        # Connectivity analysis
        if total_nodes > 0:
            try:
                # Convert to undirected for connectivity analysis
                G_undirected = G.to_undirected()
                connected_components = nx.number_connected_components(G_undirected)
                largest_component_size = len(max(nx.connected_components(G_undirected), key=len)) if connected_components > 0 else 0
            except:
                connected_components = 0
                largest_component_size = 0
        else:
            connected_components = 0
            largest_component_size = 0
        
        # Influence concentration (Gini coefficient approximation)
        cursor.execute("SELECT total_influence_score FROM influence_nodes ORDER BY total_influence_score")
        influence_scores = [row[0] for row in cursor.fetchall()]
        influence_concentration = self._calculate_gini_coefficient(influence_scores)
        
        conn.close()
        
        return {
            'network_size': {
                'total_nodes': total_nodes,
                'total_edges': total_edges,
                'density': round(density, 4)
            },
            'influence_distribution': {
                'average_influence': round(avg_influence or 0, 4),
                'min_influence': round(min_influence or 0, 4),
                'max_influence': round(max_influence or 0, 4),
                'influence_concentration': round(influence_concentration, 4)
            },
            'tier_distribution': tier_distribution,
            'connectivity': {
                'connected_components': connected_components,
                'largest_component_size': largest_component_size,
                'connectivity_ratio': round(largest_component_size / total_nodes, 4) if total_nodes > 0 else 0
            },
            'network_health_score': self._calculate_network_health_score(
                density, influence_concentration, connected_components, total_nodes
            )
        }
    
    def _calculate_gini_coefficient(self, values: List[float]) -> float:
        """Calculate Gini coefficient for influence concentration"""
        if not values or all(v == 0 for v in values):
            return 0.0
        
        values = sorted([v for v in values if v >= 0])
        n = len(values)
        
        if n == 0:
            return 0.0
        
        cumsum = np.cumsum(values)
        return (n + 1 - 2 * sum((n + 1 - i) * y for i, y in enumerate(cumsum, 1))) / (n * sum(values))
    
    def _calculate_network_health_score(self, density: float, concentration: float, 
                                      components: int, total_nodes: int) -> float:
        """Calculate overall network health score (0-1)"""
        if total_nodes == 0:
            return 0.0
        
        # Ideal characteristics:
        # - Moderate density (not too sparse, not too dense)
        # - Low concentration (influence is distributed)
        # - High connectivity (few components)
        
        density_score = 1.0 - abs(density - 0.1)  # Ideal density around 0.1
        concentration_score = 1.0 - concentration  # Lower concentration is better
        connectivity_score = 1.0 - (components - 1) / total_nodes if total_nodes > 0 else 0  # Fewer components is better
        
        # Weight the scores
        health_score = (density_score * 0.3 + concentration_score * 0.4 + connectivity_score * 0.3)
        
        return max(0.0, min(1.0, health_score))

# Demo function
async def demo_influence_mapper():
    """Demonstrate the Influence Mapper functionality"""
    print("🌐 Influence Network Mapping Demo")
    print("=" * 50)
    
    mapper = InfluenceMapper()
    
    print("\n✅ Influence Network Mapping Demo Complete!")

if __name__ == "__main__":
    asyncio.run(demo_influence_mapper())