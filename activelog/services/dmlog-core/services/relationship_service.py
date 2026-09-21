"""
Character relationship mapping and analysis service.
"""

import math
from typing import List, Dict, Optional, Tuple, Set, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from uuid import uuid4
from datetime import datetime
from collections import defaultdict, Counter

from models.relationship import (
    Character, Relationship, RelationshipEvent, RelationshipWeb,
    CharacterSchema, RelationshipSchema, RelationshipEventSchema, RelationshipWebSchema,
    RelationshipNode, RelationshipEdge, RelationshipGraph, RelationshipAnalysis,
    RelationshipSuggestion, RelationshipConflict,
    RelationshipType, RelationshipStatus, CharacterType
)

class GraphAnalyzer:
    """Analyzes relationship graphs for patterns and insights."""
    
    @staticmethod
    def calculate_centrality(graph: RelationshipGraph, character_id: str) -> Dict[str, float]:
        """Calculate various centrality measures for a character."""
        # Build adjacency information
        connections = defaultdict(set)
        all_characters = set(node.character_id for node in graph.nodes)
        
        for edge in graph.edges:
            connections[edge.source_id].add(edge.target_id)
            if edge.is_bidirectional:
                connections[edge.target_id].add(edge.source_id)
        
        # Degree centrality (direct connections)
        degree = len(connections[character_id])
        max_possible = len(all_characters) - 1
        degree_centrality = degree / max_possible if max_possible > 0 else 0
        
        # Closeness centrality (average distance to all others)
        distances = GraphAnalyzer._calculate_shortest_paths(connections, character_id, all_characters)
        total_distance = sum(distances.values())
        closeness_centrality = (len(distances) - 1) / total_distance if total_distance > 0 else 0
        
        # Betweenness centrality (how often character is on shortest paths)
        betweenness_centrality = GraphAnalyzer._calculate_betweenness(connections, character_id, all_characters)
        
        return {
            "degree": degree_centrality,
            "closeness": closeness_centrality,
            "betweenness": betweenness_centrality,
            "raw_degree": degree
        }
    
    @staticmethod
    def _calculate_shortest_paths(connections: Dict[str, Set[str]], start: str, all_chars: Set[str]) -> Dict[str, int]:
        """Calculate shortest paths from start character to all others using BFS."""
        distances = {start: 0}
        queue = [start]
        
        while queue:
            current = queue.pop(0)
            current_dist = distances[current]
            
            for neighbor in connections[current]:
                if neighbor not in distances:
                    distances[neighbor] = current_dist + 1
                    queue.append(neighbor)
        
        return {char: dist for char, dist in distances.items() if char != start}
    
    @staticmethod
    def _calculate_betweenness(connections: Dict[str, Set[str]], character_id: str, all_chars: Set[str]) -> float:
        """Calculate betweenness centrality (simplified version)."""
        # This is a simplified calculation - full betweenness centrality requires
        # finding all shortest paths between all pairs of nodes
        betweenness = 0.0
        
        for source in all_chars:
            if source == character_id:
                continue
            
            for target in all_chars:
                if target == character_id or target == source:
                    continue
                
                # Check if character_id is on shortest path from source to target
                # Simplified: just check if removing character_id increases distance
                direct_path = GraphAnalyzer._shortest_path_length(connections, source, target)
                
                # Remove character_id temporarily
                modified_connections = {k: v.copy() for k, v in connections.items()}
                modified_connections.pop(character_id, None)
                for char_connections in modified_connections.values():
                    char_connections.discard(character_id)
                
                indirect_path = GraphAnalyzer._shortest_path_length(modified_connections, source, target)
                
                if indirect_path > direct_path:
                    betweenness += 1.0
        
        # Normalize by maximum possible betweenness
        n = len(all_chars)
        max_betweenness = (n - 1) * (n - 2) / 2
        
        return betweenness / max_betweenness if max_betweenness > 0 else 0.0
    
    @staticmethod
    def _shortest_path_length(connections: Dict[str, Set[str]], source: str, target: str) -> int:
        """Calculate shortest path length between two characters."""
        if source == target:
            return 0
        
        visited = {source}
        queue = [(source, 0)]
        
        while queue:
            current, distance = queue.pop(0)
            
            for neighbor in connections.get(current, set()):
                if neighbor == target:
                    return distance + 1
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, distance + 1))
        
        return float('inf')  # No path found
    
    @staticmethod
    def find_cliques(graph: RelationshipGraph, min_size: int = 3) -> List[List[str]]:
        """Find cliques (groups of mutually connected characters)."""
        # Build adjacency list of strong positive relationships
        adjacency = defaultdict(set)
        
        for edge in graph.edges:
            # Only consider strong positive relationships for cliques
            if (edge.intensity >= 7 and 
                edge.relationship_type in [RelationshipType.FRIEND, RelationshipType.ALLY]):
                
                adjacency[edge.source_id].add(edge.target_id)
                if edge.is_bidirectional:
                    adjacency[edge.target_id].add(edge.source_id)
        
        # Find maximal cliques using Bron-Kerbosch algorithm (simplified)
        all_nodes = set(node.character_id for node in graph.nodes)
        cliques = []
        
        def bron_kerbosch(r: Set[str], p: Set[str], x: Set[str]):
            if not p and not x:
                if len(r) >= min_size:
                    cliques.append(list(r))
                return
            
            for v in list(p):
                neighbors = adjacency[v]
                bron_kerbosch(
                    r.union({v}),
                    p.intersection(neighbors),
                    x.intersection(neighbors)
                )
                p.remove(v)
                x.add(v)
        
        bron_kerbosch(set(), all_nodes, set())
        return cliques
    
    @staticmethod
    def detect_relationship_conflicts(graph: RelationshipGraph) -> List[RelationshipConflict]:
        """Detect potential conflicts in relationships."""
        conflicts = []
        
        # Group relationships by character pairs
        char_relationships = defaultdict(list)
        
        for edge in graph.edges:
            pair_key = tuple(sorted([edge.source_id, edge.target_id]))
            char_relationships[pair_key].append(edge)
        
        # Check for conflicting relationship types
        for pair, relationships in char_relationships.items():
            if len(relationships) > 1:
                types = [rel.relationship_type for rel in relationships]
                
                # Check for contradictory types
                if RelationshipType.ENEMY in types and RelationshipType.FRIEND in types:
                    conflicts.append(RelationshipConflict(
                        relationship_ids=[rel.source_id + "-" + rel.target_id for rel in relationships],
                        conflict_type="contradictory_types",
                        description=f"Character pair has both enemy and friend relationships",
                        severity=8
                    ))
        
        # Check for impossible relationship combinations
        for node in graph.nodes:
            char_id = node.character_id
            
            # Get all relationships for this character
            char_edges = [edge for edge in graph.edges 
                         if edge.source_id == char_id or edge.target_id == char_id]
            
            # Check for mentor-student loops
            mentors = set()
            students = set()
            
            for edge in char_edges:
                if edge.relationship_type == RelationshipType.MENTOR:
                    if edge.source_id == char_id:
                        students.add(edge.target_id)
                    else:
                        mentors.add(edge.source_id)
                elif edge.relationship_type == RelationshipType.STUDENT:
                    if edge.source_id == char_id:
                        mentors.add(edge.target_id)
                    else:
                        students.add(edge.source_id)
            
            # Check for cycles
            for mentor in mentors:
                if mentor in students:
                    conflicts.append(RelationshipConflict(
                        relationship_ids=[char_id + "-" + mentor],
                        conflict_type="mentor_student_cycle",
                        description=f"Circular mentor-student relationship detected",
                        severity=6,
                        suggested_resolution="Clarify the hierarchy or make one relationship more specific"
                    ))
        
        return conflicts

class RelationshipSuggester:
    """Suggests new relationships based on existing patterns."""
    
    @staticmethod
    def suggest_relationships(graph: RelationshipGraph, character_id: str) -> List[RelationshipSuggestion]:
        """Suggest new relationships for a character."""
        suggestions = []
        
        # Get character's existing relationships
        existing_relations = set()
        character_edges = []
        
        for edge in graph.edges:
            if edge.source_id == character_id:
                existing_relations.add(edge.target_id)
                character_edges.append(edge)
            elif edge.target_id == character_id and edge.is_bidirectional:
                existing_relations.add(edge.source_id)
                character_edges.append(edge)
        
        # Get character info
        character_node = next((node for node in graph.nodes if node.character_id == character_id), None)
        if not character_node:
            return suggestions
        
        # Suggest based on mutual connections (friends of friends)
        mutual_connections = RelationshipSuggester._find_mutual_connections(
            graph, character_id, existing_relations
        )
        
        for target_id, mutual_count in mutual_connections:
            confidence = min(0.8, mutual_count * 0.2)
            suggestions.append(RelationshipSuggestion(
                character_a_id=character_id,
                character_b_id=target_id,
                suggested_type=RelationshipType.ACQUAINTANCE,
                reasoning=f"Has {mutual_count} mutual connections",
                confidence=confidence,
                potential_events=[
                    "Introduced by mutual friend",
                    "Met at social gathering",
                    "Worked together on a project"
                ]
            ))
        
        # Suggest based on faction alignment
        if character_node.faction:
            faction_suggestions = RelationshipSuggester._suggest_by_faction(
                graph, character_id, character_node.faction, existing_relations
            )
            suggestions.extend(faction_suggestions)
        
        # Suggest based on location proximity
        if character_node.location:
            location_suggestions = RelationshipSuggester._suggest_by_location(
                graph, character_id, character_node.location, existing_relations
            )
            suggestions.extend(location_suggestions)
        
        return suggestions[:10]  # Limit to top 10 suggestions
    
    @staticmethod
    def _find_mutual_connections(graph: RelationshipGraph, character_id: str, 
                               existing_relations: Set[str]) -> List[Tuple[str, int]]:
        """Find characters with mutual connections."""
        mutual_counts = defaultdict(int)
        
        # For each existing relationship, find their connections
        for edge in graph.edges:
            if edge.source_id in existing_relations:
                target = edge.target_id
                if target != character_id and target not in existing_relations:
                    mutual_counts[target] += 1
            elif edge.target_id in existing_relations and edge.is_bidirectional:
                target = edge.source_id
                if target != character_id and target not in existing_relations:
                    mutual_counts[target] += 1
        
        return sorted(mutual_counts.items(), key=lambda x: x[1], reverse=True)
    
    @staticmethod
    def _suggest_by_faction(graph: RelationshipGraph, character_id: str, faction: str,
                          existing_relations: Set[str]) -> List[RelationshipSuggestion]:
        """Suggest relationships based on faction membership."""
        suggestions = []
        
        for node in graph.nodes:
            if (node.character_id != character_id and 
                node.character_id not in existing_relations and
                node.faction == faction):
                
                suggestions.append(RelationshipSuggestion(
                    character_a_id=character_id,
                    character_b_id=node.character_id,
                    suggested_type=RelationshipType.ALLY,
                    reasoning=f"Both members of {faction}",
                    confidence=0.6,
                    potential_events=[
                        "Fought together for the faction",
                        "Met at faction meeting",
                        "Assigned to work together"
                    ]
                ))
        
        return suggestions
    
    @staticmethod
    def _suggest_by_location(graph: RelationshipGraph, character_id: str, location: str,
                           existing_relations: Set[str]) -> List[RelationshipSuggestion]:
        """Suggest relationships based on shared location."""
        suggestions = []
        
        for node in graph.nodes:
            if (node.character_id != character_id and 
                node.character_id not in existing_relations and
                node.location == location):
                
                suggestions.append(RelationshipSuggestion(
                    character_a_id=character_id,
                    character_b_id=node.character_id,
                    suggested_type=RelationshipType.ACQUAINTANCE,
                    reasoning=f"Both located in {location}",
                    confidence=0.4,
                    potential_events=[
                        "Neighbors in the same area",
                        "Frequent the same establishments",
                        "Encountered during local events"
                    ]
                ))
        
        return suggestions

class RelationshipService:
    """Main relationship service handling database operations and analysis."""
    
    def __init__(self):
        self.graph_analyzer = GraphAnalyzer()
        self.suggester = RelationshipSuggester()
    
    def create_character(self, character_data: CharacterSchema, db: Session) -> Character:
        """Create a new character for relationship tracking."""
        character = Character(
            id=str(uuid4()),
            name=character_data.name,
            character_type=character_data.character_type.value,
            description=character_data.description,
            occupation=character_data.occupation,
            location=character_data.location,
            faction=character_data.faction,
            level=character_data.level,
            character_class=character_data.character_class,
            race=character_data.race,
            personality_traits=character_data.personality_traits,
            goals=character_data.goals,
            fears=character_data.fears,
            secrets=character_data.secrets,
            campaign_id=character_data.campaign_id,
            is_active=character_data.is_active
        )
        
        db.add(character)
        db.commit()
        db.refresh(character)
        
        return character
    
    def get_character(self, character_id: str, db: Session) -> Optional[Character]:
        """Get a character by ID."""
        return db.query(Character).filter(Character.id == character_id).first()
    
    def create_relationship(self, relationship_data: RelationshipSchema, db: Session) -> Relationship:
        """Create a new relationship between characters."""
        relationship = Relationship(
            id=str(uuid4()),
            character_a_id=relationship_data.character_a_id,
            character_b_id=relationship_data.character_b_id,
            relationship_type=relationship_data.relationship_type.value,
            status=relationship_data.status.value,
            intensity=relationship_data.intensity,
            is_bidirectional=relationship_data.is_bidirectional,
            is_secret=relationship_data.is_secret,
            description=relationship_data.description,
            history=relationship_data.history,
            important_events=relationship_data.important_events,
            campaign_id=relationship_data.campaign_id,
            established_date=relationship_data.established_date,
            trust_level=relationship_data.trust_level,
            respect_level=relationship_data.respect_level,
            affection_level=relationship_data.affection_level,
            notes=relationship_data.notes,
            tags=relationship_data.tags
        )
        
        db.add(relationship)
        db.commit()
        db.refresh(relationship)
        
        return relationship
    
    def get_relationship(self, relationship_id: str, db: Session) -> Optional[Relationship]:
        """Get a relationship by ID."""
        return db.query(Relationship).filter(Relationship.id == relationship_id).first()
    
    def create_relationship_event(self, event_data: RelationshipEventSchema, db: Session) -> RelationshipEvent:
        """Create a new relationship event and update relationship metrics."""
        event = RelationshipEvent(
            id=str(uuid4()),
            relationship_id=event_data.relationship_id,
            event_title=event_data.event_title,
            event_description=event_data.event_description,
            event_date=event_data.event_date,
            session_number=event_data.session_number,
            intensity_change=event_data.intensity_change,
            trust_change=event_data.trust_change,
            respect_change=event_data.respect_change,
            affection_change=event_data.affection_change,
            location=event_data.location,
            witnesses=event_data.witnesses,
            consequences=event_data.consequences
        )
        
        db.add(event)
        
        # Update the relationship metrics
        relationship = db.query(Relationship).filter(
            Relationship.id == event_data.relationship_id
        ).first()
        
        if relationship:
            relationship.intensity = max(1, min(10, relationship.intensity + event_data.intensity_change))
            relationship.trust_level = max(1, min(10, relationship.trust_level + event_data.trust_change))
            relationship.respect_level = max(1, min(10, relationship.respect_level + event_data.respect_change))
            relationship.affection_level = max(1, min(10, relationship.affection_level + event_data.affection_change))
        
        db.commit()
        db.refresh(event)
        
        return event
    
    def get_relationship_graph(self, campaign_id: str, include_secrets: bool = False, 
                             character_filter: Optional[List[str]] = None, db: Session = None) -> RelationshipGraph:
        """Get the complete relationship graph for a campaign."""
        # Get characters
        char_query = db.query(Character).filter(
            and_(
                Character.campaign_id == campaign_id,
                Character.is_active == True
            )
        )
        
        if character_filter:
            char_query = char_query.filter(Character.id.in_(character_filter))
        
        characters = char_query.all()
        
        # Get relationships
        rel_query = db.query(Relationship).filter(
            Relationship.campaign_id == campaign_id
        )
        
        if not include_secrets:
            rel_query = rel_query.filter(Relationship.is_secret == False)
        
        if character_filter:
            rel_query = rel_query.filter(
                or_(
                    Relationship.character_a_id.in_(character_filter),
                    Relationship.character_b_id.in_(character_filter)
                )
            )
        
        relationships = rel_query.all()
        
        # Build nodes
        nodes = []
        for char in characters:
            nodes.append(RelationshipNode(
                character_id=char.id,
                name=char.name,
                character_type=CharacterType(char.character_type),
                description=char.description,
                faction=char.faction,
                location=char.location
            ))
        
        # Build edges
        edges = []
        for rel in relationships:
            edges.append(RelationshipEdge(
                source_id=rel.character_a_id,
                target_id=rel.character_b_id,
                relationship_type=RelationshipType(rel.relationship_type),
                status=RelationshipStatus(rel.status),
                intensity=rel.intensity,
                trust_level=rel.trust_level,
                respect_level=rel.respect_level,
                affection_level=rel.affection_level,
                is_bidirectional=rel.is_bidirectional,
                is_secret=rel.is_secret,
                description=rel.description
            ))
        
        return RelationshipGraph(
            nodes=nodes,
            edges=edges,
            campaign_id=campaign_id
        )
    
    def analyze_character_relationships(self, character_id: str, campaign_id: str, db: Session) -> RelationshipAnalysis:
        """Analyze a character's relationship patterns."""
        graph = self.get_relationship_graph(campaign_id, include_secrets=True, db=db)
        
        # Get character's relationships
        char_relationships = []
        for edge in graph.edges:
            if edge.source_id == character_id or (edge.target_id == character_id and edge.is_bidirectional):
                char_relationships.append(edge)
        
        if not char_relationships:
            return RelationshipAnalysis(
                character_id=character_id,
                total_relationships=0,
                relationship_type_distribution={},
                average_intensity=0,
                average_trust=0,
                average_respect=0,
                average_affection=0,
                strongest_relationships=[],
                weakest_relationships=[],
                faction_connections={},
                relationship_trends={}
            )
        
        # Calculate statistics
        type_distribution = Counter(edge.relationship_type.value for edge in char_relationships)
        
        avg_intensity = sum(edge.intensity for edge in char_relationships) / len(char_relationships)
        avg_trust = sum(edge.trust_level for edge in char_relationships) / len(char_relationships)
        avg_respect = sum(edge.respect_level for edge in char_relationships) / len(char_relationships)
        avg_affection = sum(edge.affection_level for edge in char_relationships) / len(char_relationships)
        
        # Find strongest and weakest relationships
        sorted_by_intensity = sorted(char_relationships, key=lambda x: x.intensity, reverse=True)
        
        strongest = []
        weakest = []
        
        for edge in sorted_by_intensity[:3]:
            other_id = edge.target_id if edge.source_id == character_id else edge.source_id
            other_node = next((node for node in graph.nodes if node.character_id == other_id), None)
            if other_node:
                strongest.append((other_node.name, edge.relationship_type.value, edge.intensity))
        
        for edge in sorted_by_intensity[-3:]:
            other_id = edge.target_id if edge.source_id == character_id else edge.source_id
            other_node = next((node for node in graph.nodes if node.character_id == other_id), None)
            if other_node:
                weakest.append((other_node.name, edge.relationship_type.value, edge.intensity))
        
        # Analyze faction connections
        faction_connections = defaultdict(int)
        for edge in char_relationships:
            other_id = edge.target_id if edge.source_id == character_id else edge.source_id
            other_node = next((node for node in graph.nodes if node.character_id == other_id), None)
            if other_node and other_node.faction:
                faction_connections[other_node.faction] += 1
        
        return RelationshipAnalysis(
            character_id=character_id,
            total_relationships=len(char_relationships),
            relationship_type_distribution=dict(type_distribution),
            average_intensity=avg_intensity,
            average_trust=avg_trust,
            average_respect=avg_respect,
            average_affection=avg_affection,
            strongest_relationships=strongest,
            weakest_relationships=weakest,
            faction_connections=dict(faction_connections),
            relationship_trends={}  # Would require historical data
        )
    
    def get_relationship_suggestions(self, character_id: str, campaign_id: str, db: Session) -> List[RelationshipSuggestion]:
        """Get relationship suggestions for a character."""
        graph = self.get_relationship_graph(campaign_id, db=db)
        return self.suggester.suggest_relationships(graph, character_id)
    
    def detect_conflicts(self, campaign_id: str, db: Session) -> List[RelationshipConflict]:
        """Detect relationship conflicts in a campaign."""
        graph = self.get_relationship_graph(campaign_id, include_secrets=True, db=db)
        return self.graph_analyzer.detect_relationship_conflicts(graph)
    
    def find_cliques(self, campaign_id: str, min_size: int = 3, db: Session = None) -> List[List[str]]:
        """Find cliques (tight-knit groups) in the relationship network."""
        graph = self.get_relationship_graph(campaign_id, db=db)
        clique_ids = self.graph_analyzer.find_cliques(graph, min_size)
        
        # Convert character IDs to names
        id_to_name = {node.character_id: node.name for node in graph.nodes}
        
        return [[id_to_name.get(char_id, char_id) for char_id in clique] for clique in clique_ids]
    
    def calculate_character_centrality(self, character_id: str, campaign_id: str, db: Session) -> Dict[str, float]:
        """Calculate centrality measures for a character."""
        graph = self.get_relationship_graph(campaign_id, db=db)
        return self.graph_analyzer.calculate_centrality(graph, character_id)
    
    def create_relationship_web(self, web_data: RelationshipWebSchema, db: Session) -> RelationshipWeb:
        """Create a saved relationship web configuration."""
        web = RelationshipWeb(
            id=str(uuid4()),
            name=web_data.name,
            description=web_data.description,
            campaign_id=web_data.campaign_id,
            focus_character_id=web_data.focus_character_id,
            included_characters=web_data.included_characters,
            relationship_filters=web_data.relationship_filters,
            layout_settings=web_data.layout_settings,
            display_options=web_data.display_options
        )
        
        db.add(web)
        db.commit()
        db.refresh(web)
        
        return web
    
    def get_relationship_history(self, relationship_id: str, db: Session) -> List[RelationshipEvent]:
        """Get the history of events for a relationship."""
        return db.query(RelationshipEvent).filter(
            RelationshipEvent.relationship_id == relationship_id
        ).order_by(RelationshipEvent.created_at.asc()).all()
    
    def search_characters(self, campaign_id: str, search_term: str, db: Session) -> List[Character]:
        """Search for characters by name, description, or other attributes."""
        return db.query(Character).filter(
            and_(
                Character.campaign_id == campaign_id,
                Character.is_active == True,
                or_(
                    Character.name.ilike(f"%{search_term}%"),
                    Character.description.ilike(f"%{search_term}%"),
                    Character.occupation.ilike(f"%{search_term}%"),
                    Character.faction.ilike(f"%{search_term}%")
                )
            )
        ).all()