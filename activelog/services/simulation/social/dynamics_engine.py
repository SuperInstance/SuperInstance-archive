"""
Social Dynamics Simulation Module

This module provides comprehensive social dynamics simulation for modeling human behavior,
social networks, group interactions, cultural evolution, and societal trends. Includes
agent-based modeling, network analysis, opinion dynamics, and social influence mechanisms.

Key Features:
- Agent-based social modeling
- Social network analysis and evolution
- Opinion dynamics and consensus formation
- Cultural transmission and evolution
- Group behavior and collective decision making
- Social influence and contagion models
- Demographic transitions and migration
- Social stratification and mobility
- Community formation and dissolution
- Social movements and collective action
- Information diffusion and viral spread
- Trust networks and reputation systems
"""

import asyncio
import logging
import random
import time
import json
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union, Set
from enum import Enum
from collections import defaultdict, deque
import math
import networkx as nx


class AgentPersonality(Enum):
    """Agent personality types"""
    EXTROVERT = "extrovert"
    INTROVERT = "introvert"
    AGREEABLE = "agreeable"
    DISAGREEABLE = "disagreeable"
    CONSCIENTIOUS = "conscientious"
    UNCONSCIENTIOUS = "unconscientious"
    NEUROTIC = "neurotic"
    EMOTIONALLY_STABLE = "emotionally_stable"
    OPEN = "open"
    CLOSED = "closed"


class SocialRole(Enum):
    """Social roles in the simulation"""
    LEADER = "leader"
    FOLLOWER = "follower"
    INFLUENCER = "influencer"
    INNOVATOR = "innovator"
    EARLY_ADOPTER = "early_adopter"
    MAJORITY = "majority"
    LAGGARD = "laggard"
    BRIDGE = "bridge"
    ISOLATE = "isolate"
    CONNECTOR = "connector"


class InteractionType(Enum):
    """Types of social interactions"""
    CONVERSATION = "conversation"
    COLLABORATION = "collaboration"
    CONFLICT = "conflict"
    INFORMATION_SHARING = "information_sharing"
    INFLUENCE_ATTEMPT = "influence_attempt"
    TRUST_BUILDING = "trust_building"
    REPUTATION_UPDATE = "reputation_update"
    GROUP_FORMATION = "group_formation"
    NETWORK_EXPANSION = "network_expansion"
    SOCIAL_SUPPORT = "social_support"


class CulturalTrait(Enum):
    """Cultural traits that can evolve"""
    LANGUAGE = "language"
    RELIGION = "religion"
    POLITICAL_VIEW = "political_view"
    VALUES = "values"
    TRADITIONS = "traditions"
    TECHNOLOGY_ADOPTION = "technology_adoption"
    SOCIAL_NORMS = "social_norms"
    ECONOMIC_BEHAVIOR = "economic_behavior"
    EDUCATIONAL_ATTITUDE = "educational_attitude"
    ENVIRONMENTAL_CONCERN = "environmental_concern"


class SocialGroup(Enum):
    """Types of social groups"""
    FAMILY = "family"
    FRIENDS = "friends"
    COLLEAGUES = "colleagues"
    COMMUNITY = "community"
    ORGANIZATION = "organization"
    MOVEMENT = "movement"
    CLUB = "club"
    ONLINE_COMMUNITY = "online_community"
    PROFESSIONAL_NETWORK = "professional_network"
    INTEREST_GROUP = "interest_group"


@dataclass
class Agent:
    """Individual agent in the social simulation"""
    agent_id: str
    age: int
    personality: Dict[AgentPersonality, float]
    social_roles: List[SocialRole]
    cultural_traits: Dict[CulturalTrait, float]
    opinions: Dict[str, float]  # Topic -> Opinion strength (-1 to 1)
    trust_scores: Dict[str, float]  # Agent ID -> Trust score
    reputation: float = 0.5
    influence: float = 0.5
    social_capital: float = 0.5
    network_position: Tuple[float, float] = (0.0, 0.0)
    groups: List[str] = field(default_factory=list)
    interaction_history: List[Dict] = field(default_factory=list)
    last_active: datetime = field(default_factory=datetime.now)
    status: str = "active"


@dataclass
class SocialConnection:
    """Connection between agents"""
    agent1: str
    agent2: str
    connection_type: str
    strength: float  # 0 to 1
    duration: int  # days
    last_interaction: datetime
    interaction_count: int = 0
    trust_level: float = 0.5
    influence_weight: float = 0.5


@dataclass
class SocialInteraction:
    """Single social interaction event"""
    interaction_id: str
    participants: List[str]
    interaction_type: InteractionType
    topic: Optional[str]
    outcome: Dict[str, Any]
    influence_changes: Dict[str, float]
    opinion_changes: Dict[str, Dict[str, float]]
    timestamp: datetime = field(default_factory=datetime.now)
    duration: int = 1  # minutes
    success: bool = True


@dataclass
class SocialMovement:
    """Social movement or collective action"""
    movement_id: str
    name: str
    cause: str
    leaders: List[str]
    members: Set[str]
    supporters: Set[str]
    opposers: Set[str]
    momentum: float = 0.0
    public_support: float = 0.0
    media_attention: float = 0.0
    organizational_strength: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True


class OpinionDynamicsModel(ABC):
    """Abstract base for opinion dynamics models"""
    
    @abstractmethod
    def update_opinions(self, agents: List[Agent], connections: List[SocialConnection],
                       topic: str) -> Dict[str, float]:
        """Update agent opinions based on social influence"""
        pass
    
    @abstractmethod
    def calculate_influence(self, agent: Agent, neighbor: Agent, connection: SocialConnection) -> float:
        """Calculate influence between two agents"""
        pass


class DeGrootModel(OpinionDynamicsModel):
    """DeGroot consensus model for opinion dynamics"""
    
    def __init__(self, convergence_threshold: float = 0.001):
        self.convergence_threshold = convergence_threshold
        self.max_iterations = 100
    
    def update_opinions(self, agents: List[Agent], connections: List[SocialConnection],
                       topic: str) -> Dict[str, float]:
        """Update opinions using DeGroot consensus model"""
        agent_dict = {agent.agent_id: agent for agent in agents}
        opinion_changes = {}
        
        # Create influence matrix
        agent_ids = list(agent_dict.keys())
        n = len(agent_ids)
        influence_matrix = np.zeros((n, n))
        
        for i, agent_id in enumerate(agent_ids):
            # Self-influence (stubborness)
            influence_matrix[i, i] = 0.1
            
            # Neighbor influence
            neighbors = self._get_neighbors(agent_id, connections)
            if neighbors:
                neighbor_influence = 0.9 / len(neighbors)
                for neighbor_id in neighbors:
                    if neighbor_id in agent_ids:
                        j = agent_ids.index(neighbor_id)
                        connection = self._get_connection(agent_id, neighbor_id, connections)
                        influence_matrix[i, j] = neighbor_influence * connection.strength
        
        # Normalize rows
        for i in range(n):
            row_sum = np.sum(influence_matrix[i, :])
            if row_sum > 0:
                influence_matrix[i, :] /= row_sum
        
        # Get current opinions
        current_opinions = np.array([
            agent_dict[agent_id].opinions.get(topic, 0.0)
            for agent_id in agent_ids
        ])
        
        # Iterate until convergence
        for iteration in range(self.max_iterations):
            new_opinions = np.dot(influence_matrix, current_opinions)
            
            # Check convergence
            if np.max(np.abs(new_opinions - current_opinions)) < self.convergence_threshold:
                break
            
            current_opinions = new_opinions
        
        # Calculate changes
        for i, agent_id in enumerate(agent_ids):
            old_opinion = agent_dict[agent_id].opinions.get(topic, 0.0)
            new_opinion = current_opinions[i]
            opinion_changes[agent_id] = new_opinion - old_opinion
        
        return opinion_changes
    
    def calculate_influence(self, agent: Agent, neighbor: Agent, connection: SocialConnection) -> float:
        """Calculate influence between agents"""
        # Influence based on trust, reputation, and connection strength
        base_influence = connection.strength * connection.trust_level
        reputation_factor = (neighbor.reputation + neighbor.influence) / 2
        return base_influence * reputation_factor
    
    def _get_neighbors(self, agent_id: str, connections: List[SocialConnection]) -> List[str]:
        """Get neighbors of an agent"""
        neighbors = []
        for conn in connections:
            if conn.agent1 == agent_id:
                neighbors.append(conn.agent2)
            elif conn.agent2 == agent_id:
                neighbors.append(conn.agent1)
        return neighbors
    
    def _get_connection(self, agent1: str, agent2: str, connections: List[SocialConnection]) -> Optional[SocialConnection]:
        """Get connection between two agents"""
        for conn in connections:
            if (conn.agent1 == agent1 and conn.agent2 == agent2) or \
               (conn.agent1 == agent2 and conn.agent2 == agent1):
                return conn
        return None


class BoundedConfidenceModel(OpinionDynamicsModel):
    """Bounded confidence model (Hegselmann-Krause)"""
    
    def __init__(self, confidence_threshold: float = 0.3):
        self.confidence_threshold = confidence_threshold
        self.update_rate = 0.1
    
    def update_opinions(self, agents: List[Agent], connections: List[SocialConnection],
                       topic: str) -> Dict[str, float]:
        """Update opinions with bounded confidence"""
        agent_dict = {agent.agent_id: agent for agent in agents}
        opinion_changes = {}
        
        for agent in agents:
            current_opinion = agent.opinions.get(topic, 0.0)
            neighbors = self._get_neighbors(agent.agent_id, connections)
            
            # Find neighbors within confidence bound
            confident_neighbors = []
            for neighbor_id in neighbors:
                neighbor = agent_dict.get(neighbor_id)
                if neighbor:
                    neighbor_opinion = neighbor.opinions.get(topic, 0.0)
                    if abs(current_opinion - neighbor_opinion) <= self.confidence_threshold:
                        confident_neighbors.append(neighbor)
            
            if confident_neighbors:
                # Average with confident neighbors
                neighbor_opinions = [n.opinions.get(topic, 0.0) for n in confident_neighbors]
                avg_neighbor_opinion = np.mean(neighbor_opinions)
                
                # Update towards average
                new_opinion = current_opinion + self.update_rate * (avg_neighbor_opinion - current_opinion)
                opinion_changes[agent.agent_id] = new_opinion - current_opinion
            else:
                opinion_changes[agent.agent_id] = 0.0
        
        return opinion_changes
    
    def calculate_influence(self, agent: Agent, neighbor: Agent, connection: SocialConnection) -> float:
        """Calculate bounded confidence influence"""
        return connection.strength if connection else 0.0
    
    def _get_neighbors(self, agent_id: str, connections: List[SocialConnection]) -> List[str]:
        """Get neighbors of an agent"""
        neighbors = []
        for conn in connections:
            if conn.agent1 == agent_id:
                neighbors.append(conn.agent2)
            elif conn.agent2 == agent_id:
                neighbors.append(conn.agent1)
        return neighbors


class NetworkEvolution:
    """Models evolution of social networks"""
    
    def __init__(self):
        self.preferential_attachment_strength = 0.7
        self.homophily_strength = 0.5
        self.triadic_closure_probability = 0.3
        self.edge_decay_rate = 0.01
    
    def evolve_network(self, agents: List[Agent], connections: List[SocialConnection]) -> List[SocialConnection]:
        """Evolve the social network"""
        new_connections = connections.copy()
        
        # Remove weak connections (edge decay)
        new_connections = self._decay_edges(new_connections)
        
        # Add new connections
        new_connections.extend(self._form_new_connections(agents, new_connections))
        
        # Strengthen existing connections through repeated interactions
        new_connections = self._strengthen_connections(new_connections)
        
        # Form triadic closures
        new_connections.extend(self._form_triadic_closures(agents, new_connections))
        
        return new_connections
    
    def _decay_edges(self, connections: List[SocialConnection]) -> List[SocialConnection]:
        """Remove weak or inactive connections"""
        active_connections = []
        for conn in connections:
            # Decay connection strength over time
            days_since_interaction = (datetime.now() - conn.last_interaction).days
            decay = days_since_interaction * self.edge_decay_rate
            conn.strength = max(0, conn.strength - decay)
            
            # Keep connection if still strong enough
            if conn.strength > 0.1:
                active_connections.append(conn)
        
        return active_connections
    
    def _form_new_connections(self, agents: List[Agent], 
                            existing_connections: List[SocialConnection]) -> List[SocialConnection]:
        """Form new connections based on preferential attachment and homophily"""
        new_connections = []
        agent_dict = {agent.agent_id: agent for agent in agents}
        
        # Calculate current degree for each agent
        degrees = defaultdict(int)
        for conn in existing_connections:
            degrees[conn.agent1] += 1
            degrees[conn.agent2] += 1
        
        # Form new connections
        for agent in agents:
            if random.random() < 0.1:  # 10% chance to form new connection per step
                potential_partners = self._find_potential_partners(
                    agent, agents, existing_connections
                )
                
                if potential_partners:
                    # Choose partner based on preferential attachment and homophily
                    partner = self._choose_partner(agent, potential_partners, degrees)
                    
                    new_connection = SocialConnection(
                        agent1=agent.agent_id,
                        agent2=partner.agent_id,
                        connection_type="new_acquaintance",
                        strength=random.uniform(0.1, 0.3),
                        duration=0,
                        last_interaction=datetime.now(),
                        trust_level=0.3
                    )
                    new_connections.append(new_connection)
        
        return new_connections
    
    def _strengthen_connections(self, connections: List[SocialConnection]) -> List[SocialConnection]:
        """Strengthen connections through repeated interactions"""
        for conn in connections:
            if random.random() < 0.2:  # 20% chance of interaction strengthening
                strength_increase = random.uniform(0.01, 0.05)
                conn.strength = min(1.0, conn.strength + strength_increase)
                conn.interaction_count += 1
                conn.last_interaction = datetime.now()
        
        return connections
    
    def _form_triadic_closures(self, agents: List[Agent], 
                              connections: List[SocialConnection]) -> List[SocialConnection]:
        """Form triadic closures (friend of friend becomes friend)"""
        new_connections = []
        agent_dict = {agent.agent_id: agent for agent in agents}
        
        # Build adjacency for faster lookup
        adjacency = defaultdict(set)
        for conn in connections:
            adjacency[conn.agent1].add(conn.agent2)
            adjacency[conn.agent2].add(conn.agent1)
        
        for agent in agents:
            neighbors = list(adjacency[agent.agent_id])
            
            # Find mutual neighbors (potential triangles)
            for i, neighbor1 in enumerate(neighbors):
                for neighbor2 in neighbors[i+1:]:
                    # Check if neighbor1 and neighbor2 are not connected
                    if neighbor2 not in adjacency[neighbor1]:
                        if random.random() < self.triadic_closure_probability:
                            new_connection = SocialConnection(
                                agent1=neighbor1,
                                agent2=neighbor2,
                                connection_type="triadic_closure",
                                strength=random.uniform(0.2, 0.4),
                                duration=0,
                                last_interaction=datetime.now(),
                                trust_level=0.4
                            )
                            new_connections.append(new_connection)
        
        return new_connections
    
    def _find_potential_partners(self, agent: Agent, all_agents: List[Agent],
                               existing_connections: List[SocialConnection]) -> List[Agent]:
        """Find potential connection partners"""
        connected_agents = set()
        for conn in existing_connections:
            if conn.agent1 == agent.agent_id:
                connected_agents.add(conn.agent2)
            elif conn.agent2 == agent.agent_id:
                connected_agents.add(conn.agent1)
        
        potential_partners = [
            a for a in all_agents 
            if a.agent_id != agent.agent_id and a.agent_id not in connected_agents
        ]
        
        return potential_partners
    
    def _choose_partner(self, agent: Agent, potential_partners: List[Agent],
                       degrees: Dict[str, int]) -> Agent:
        """Choose connection partner based on preferential attachment and homophily"""
        scores = []
        
        for partner in potential_partners:
            # Preferential attachment score
            degree_score = degrees.get(partner.agent_id, 0) * self.preferential_attachment_strength
            
            # Homophily score (similarity in traits and opinions)
            similarity_score = self._calculate_similarity(agent, partner) * self.homophily_strength
            
            total_score = degree_score + similarity_score + random.uniform(0, 1)
            scores.append(total_score)
        
        # Choose partner with highest score
        max_score_idx = np.argmax(scores)
        return potential_partners[max_score_idx]
    
    def _calculate_similarity(self, agent1: Agent, agent2: Agent) -> float:
        """Calculate similarity between two agents"""
        similarity = 0.0
        
        # Age similarity
        age_diff = abs(agent1.age - agent2.age)
        age_similarity = max(0, 1 - age_diff / 50.0)
        similarity += age_similarity * 0.3
        
        # Personality similarity
        personality_similarity = 0.0
        for trait in AgentPersonality:
            if trait in agent1.personality and trait in agent2.personality:
                diff = abs(agent1.personality[trait] - agent2.personality[trait])
                personality_similarity += max(0, 1 - diff)
        personality_similarity /= len(AgentPersonality)
        similarity += personality_similarity * 0.4
        
        # Cultural trait similarity
        cultural_similarity = 0.0
        common_traits = set(agent1.cultural_traits.keys()) & set(agent2.cultural_traits.keys())
        if common_traits:
            for trait in common_traits:
                diff = abs(agent1.cultural_traits[trait] - agent2.cultural_traits[trait])
                cultural_similarity += max(0, 1 - diff)
            cultural_similarity /= len(common_traits)
            similarity += cultural_similarity * 0.3
        
        return similarity


class CulturalEvolution:
    """Models cultural trait evolution and transmission"""
    
    def __init__(self):
        self.mutation_rate = 0.01
        self.transmission_probability = 0.1
        self.innovation_rate = 0.005
    
    def evolve_culture(self, agents: List[Agent], connections: List[SocialConnection]) -> Dict[str, Any]:
        """Evolve cultural traits across the population"""
        changes = {
            'mutations': 0,
            'transmissions': 0,
            'innovations': 0,
            'trait_changes': defaultdict(list)
        }
        
        # Cultural transmission through connections
        changes.update(self._cultural_transmission(agents, connections))
        
        # Random mutations
        changes.update(self._cultural_mutation(agents))
        
        # Innovation by creative agents
        changes.update(self._cultural_innovation(agents))
        
        return changes
    
    def _cultural_transmission(self, agents: List[Agent], 
                              connections: List[SocialConnection]) -> Dict[str, Any]:
        """Transmit cultural traits through social connections"""
        changes = {'transmissions': 0, 'trait_changes': defaultdict(list)}
        agent_dict = {agent.agent_id: agent for agent in agents}
        
        for connection in connections:
            if random.random() < self.transmission_probability * connection.strength:
                agent1 = agent_dict[connection.agent1]
                agent2 = agent_dict[connection.agent2]
                
                # Choose random trait to potentially transmit
                all_traits = set(agent1.cultural_traits.keys()) | set(agent2.cultural_traits.keys())
                if all_traits:
                    trait = random.choice(list(all_traits))
                    
                    # Determine who influences whom based on influence scores
                    if agent1.influence > agent2.influence:
                        influencer, influenced = agent1, agent2
                    else:
                        influencer, influenced = agent2, agent1
                    
                    if trait in influencer.cultural_traits:
                        old_value = influenced.cultural_traits.get(trait, 0.5)
                        new_value = influencer.cultural_traits[trait]
                        
                        # Partial transmission based on trust and influence
                        trust_factor = connection.trust_level
                        transmission_strength = trust_factor * connection.strength
                        
                        influenced_new_value = old_value + transmission_strength * (new_value - old_value)
                        influenced.cultural_traits[trait] = np.clip(influenced_new_value, 0, 1)
                        
                        changes['transmissions'] += 1
                        changes['trait_changes'][trait].append({
                            'agent': influenced.agent_id,
                            'old_value': old_value,
                            'new_value': influenced_new_value,
                            'influencer': influencer.agent_id
                        })
        
        return changes
    
    def _cultural_mutation(self, agents: List[Agent]) -> Dict[str, Any]:
        """Random mutations in cultural traits"""
        changes = {'mutations': 0, 'trait_changes': defaultdict(list)}
        
        for agent in agents:
            for trait, value in agent.cultural_traits.items():
                if random.random() < self.mutation_rate:
                    old_value = value
                    mutation = random.gauss(0, 0.1)  # Small random change
                    new_value = np.clip(value + mutation, 0, 1)
                    agent.cultural_traits[trait] = new_value
                    
                    changes['mutations'] += 1
                    changes['trait_changes'][trait].append({
                        'agent': agent.agent_id,
                        'old_value': old_value,
                        'new_value': new_value,
                        'type': 'mutation'
                    })
        
        return changes
    
    def _cultural_innovation(self, agents: List[Agent]) -> Dict[str, Any]:
        """Innovation of new cultural variants"""
        changes = {'innovations': 0, 'trait_changes': defaultdict(list)}
        
        for agent in agents:
            # High-influence agents more likely to innovate
            innovation_probability = self.innovation_rate * (1 + agent.influence)
            
            if random.random() < innovation_probability:
                # Create new variant of existing trait or entirely new trait
                if agent.cultural_traits and random.random() < 0.8:
                    # Modify existing trait
                    trait = random.choice(list(agent.cultural_traits.keys()))
                    old_value = agent.cultural_traits[trait]
                    new_value = np.clip(random.uniform(0, 1), 0, 1)
                    agent.cultural_traits[trait] = new_value
                    
                    changes['innovations'] += 1
                    changes['trait_changes'][trait].append({
                        'agent': agent.agent_id,
                        'old_value': old_value,
                        'new_value': new_value,
                        'type': 'innovation'
                    })
                else:
                    # Create entirely new trait (rare)
                    new_trait = CulturalTrait.VALUES  # Default to values
                    new_value = random.uniform(0, 1)
                    agent.cultural_traits[new_trait] = new_value
                    
                    changes['innovations'] += 1
                    changes['trait_changes'][new_trait].append({
                        'agent': agent.agent_id,
                        'old_value': 0.5,  # Default
                        'new_value': new_value,
                        'type': 'new_trait'
                    })
        
        return changes


class GroupDynamics:
    """Models group formation, cohesion, and dissolution"""
    
    def __init__(self):
        self.min_group_size = 3
        self.max_group_size = 50
        self.cohesion_threshold = 0.6
        self.dissolution_threshold = 0.2
        
    def update_groups(self, agents: List[Agent], connections: List[SocialConnection],
                     existing_groups: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """Update group memberships"""
        updated_groups = existing_groups.copy()
        
        # Form new groups
        new_groups = self._form_new_groups(agents, connections, existing_groups)
        updated_groups.update(new_groups)
        
        # Update group cohesion and potentially dissolve groups
        updated_groups = self._update_group_cohesion(agents, connections, updated_groups)
        
        # Merge similar groups
        updated_groups = self._merge_groups(agents, updated_groups)
        
        return updated_groups
    
    def _form_new_groups(self, agents: List[Agent], connections: List[SocialConnection],
                        existing_groups: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """Form new groups based on network structure"""
        new_groups = {}
        agent_dict = {agent.agent_id: agent for agent in agents}
        
        # Build network graph
        G = nx.Graph()
        for agent in agents:
            G.add_node(agent.agent_id)
        for conn in connections:
            if conn.strength > 0.3:  # Only consider strong connections
                G.add_edge(conn.agent1, conn.agent2, weight=conn.strength)
        
        # Find communities using modularity-based clustering
        if len(G.nodes()) > 2:
            communities = nx.community.greedy_modularity_communities(G)
            
            for i, community in enumerate(communities):
                community_set = set(community)
                
                # Check if this is a genuinely new group
                if (len(community_set) >= self.min_group_size and 
                    not self._overlaps_existing_group(community_set, existing_groups)):
                    
                    group_id = f"group_{int(time.time())}_{i}"
                    new_groups[group_id] = community_set
                    
                    # Update agent group memberships
                    for agent_id in community_set:
                        if agent_id in agent_dict:
                            agent_dict[agent_id].groups.append(group_id)
        
        return new_groups
    
    def _update_group_cohesion(self, agents: List[Agent], connections: List[SocialConnection],
                              groups: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """Update group cohesion and dissolve weak groups"""
        agent_dict = {agent.agent_id: agent for agent in agents}
        active_groups = {}
        
        for group_id, members in groups.items():
            if len(members) < self.min_group_size:
                # Remove group membership from agents
                for member_id in members:
                    if member_id in agent_dict:
                        agent = agent_dict[member_id]
                        if group_id in agent.groups:
                            agent.groups.remove(group_id)
                continue
            
            cohesion = self._calculate_group_cohesion(members, connections)
            
            if cohesion > self.dissolution_threshold:
                active_groups[group_id] = members
            else:
                # Dissolve group
                for member_id in members:
                    if member_id in agent_dict:
                        agent = agent_dict[member_id]
                        if group_id in agent.groups:
                            agent.groups.remove(group_id)
        
        return active_groups
    
    def _calculate_group_cohesion(self, members: Set[str], 
                                 connections: List[SocialConnection]) -> float:
        """Calculate cohesion within a group"""
        if len(members) < 2:
            return 0.0
        
        internal_connections = []
        for conn in connections:
            if conn.agent1 in members and conn.agent2 in members:
                internal_connections.append(conn)
        
        # Calculate density of internal connections
        possible_connections = len(members) * (len(members) - 1) / 2
        actual_connections = len(internal_connections)
        
        if possible_connections == 0:
            return 0.0
        
        density = actual_connections / possible_connections
        
        # Weight by connection strength
        if internal_connections:
            avg_strength = np.mean([conn.strength for conn in internal_connections])
            cohesion = density * avg_strength
        else:
            cohesion = 0.0
        
        return cohesion
    
    def _overlaps_existing_group(self, new_group: Set[str], 
                               existing_groups: Dict[str, Set[str]]) -> bool:
        """Check if new group significantly overlaps with existing groups"""
        for group_members in existing_groups.values():
            overlap = len(new_group & group_members)
            overlap_ratio = overlap / len(new_group)
            if overlap_ratio > 0.7:  # 70% overlap threshold
                return True
        return False
    
    def _merge_groups(self, agents: List[Agent], 
                     groups: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        """Merge groups with high overlap and similarity"""
        agent_dict = {agent.agent_id: agent for agent in agents}
        merged_groups = groups.copy()
        groups_to_remove = set()
        
        group_items = list(groups.items())
        for i, (group1_id, members1) in enumerate(group_items):
            if group1_id in groups_to_remove:
                continue
                
            for j, (group2_id, members2) in enumerate(group_items[i+1:], i+1):
                if group2_id in groups_to_remove:
                    continue
                
                # Check overlap
                overlap = len(members1 & members2)
                min_size = min(len(members1), len(members2))
                overlap_ratio = overlap / min_size if min_size > 0 else 0
                
                if overlap_ratio > 0.5:  # 50% overlap threshold for merging
                    # Merge groups
                    new_group_id = f"merged_{group1_id}_{group2_id}"
                    merged_members = members1 | members2
                    
                    if len(merged_members) <= self.max_group_size:
                        merged_groups[new_group_id] = merged_members
                        groups_to_remove.add(group1_id)
                        groups_to_remove.add(group2_id)
                        
                        # Update agent group memberships
                        for member_id in merged_members:
                            if member_id in agent_dict:
                                agent = agent_dict[member_id]
                                if group1_id in agent.groups:
                                    agent.groups.remove(group1_id)
                                if group2_id in agent.groups:
                                    agent.groups.remove(group2_id)
                                if new_group_id not in agent.groups:
                                    agent.groups.append(new_group_id)
        
        # Remove merged groups
        for group_id in groups_to_remove:
            if group_id in merged_groups:
                del merged_groups[group_id]
        
        return merged_groups


class SocialDynamicsEngine:
    """Main social dynamics simulation engine"""
    
    def __init__(self, population_size: int = 1000):
        self.population_size = population_size
        self.agents = []
        self.connections = []
        self.groups = {}
        self.movements = {}
        self.opinion_model = DeGrootModel()
        self.network_evolution = NetworkEvolution()
        self.cultural_evolution = CulturalEvolution()
        self.group_dynamics = GroupDynamics()
        self.simulation_time = datetime.now()
        self.step_count = 0
        self.event_log = deque(maxlen=10000)
        self.metrics = defaultdict(list)
        
    def initialize_population(self, demographic_profile: Dict[str, Any] = None):
        """Initialize agent population with diversity"""
        if demographic_profile is None:
            demographic_profile = self._default_demographic_profile()
        
        self.agents = []
        for i in range(self.population_size):
            agent = self._create_agent(f"agent_{i}", demographic_profile)
            self.agents.append(agent)
        
        # Initialize network with random connections
        self._initialize_network()
        
        # Form initial groups
        self.groups = self.group_dynamics._form_new_groups(self.agents, self.connections, {})
        
        self._log_event("population_initialized", f"Created {len(self.agents)} agents")
    
    def _create_agent(self, agent_id: str, demographic_profile: Dict[str, Any]) -> Agent:
        """Create a single agent with random characteristics"""
        # Random age based on demographic profile
        age = np.random.choice(
            demographic_profile['age_groups'], 
            p=demographic_profile['age_distribution']
        )
        
        # Random personality traits
        personality = {}
        for trait in AgentPersonality:
            personality[trait] = random.uniform(0, 1)
        
        # Random social roles
        num_roles = random.randint(1, 3)
        social_roles = random.sample(list(SocialRole), num_roles)
        
        # Random cultural traits
        cultural_traits = {}
        for trait in CulturalTrait:
            cultural_traits[trait] = random.uniform(0, 1)
        
        # Random initial opinions on various topics
        topics = ["politics", "environment", "technology", "economy", "education"]
        opinions = {topic: random.uniform(-1, 1) for topic in topics}
        
        # Initial reputation and influence based on personality
        reputation = (personality.get(AgentPersonality.AGREEABLE, 0.5) + 
                     personality.get(AgentPersonality.CONSCIENTIOUS, 0.5)) / 2
        
        influence = (personality.get(AgentPersonality.EXTROVERT, 0.5) + 
                    personality.get(AgentPersonality.OPEN, 0.5)) / 2
        
        return Agent(
            agent_id=agent_id,
            age=age,
            personality=personality,
            social_roles=social_roles,
            cultural_traits=cultural_traits,
            opinions=opinions,
            trust_scores={},
            reputation=reputation,
            influence=influence,
            social_capital=random.uniform(0.3, 0.7),
            network_position=(random.uniform(-1, 1), random.uniform(-1, 1))
        )
    
    def _default_demographic_profile(self) -> Dict[str, Any]:
        """Default demographic profile for population"""
        return {
            'age_groups': [20, 30, 40, 50, 60, 70],
            'age_distribution': [0.15, 0.25, 0.25, 0.20, 0.10, 0.05]
        }
    
    def _initialize_network(self):
        """Initialize social network with random connections"""
        self.connections = []
        
        # Erdős–Rényi random graph as starting point
        connection_probability = 0.01  # Sparse network
        
        for i in range(len(self.agents)):
            for j in range(i + 1, len(self.agents)):
                if random.random() < connection_probability:
                    connection = SocialConnection(
                        agent1=self.agents[i].agent_id,
                        agent2=self.agents[j].agent_id,
                        connection_type="initial_random",
                        strength=random.uniform(0.1, 0.5),
                        duration=0,
                        last_interaction=self.simulation_time,
                        trust_level=random.uniform(0.2, 0.6)
                    )
                    self.connections.append(connection)
        
        # Add some preferential attachment
        high_degree_agents = sorted(self.agents, key=lambda a: self._get_degree(a), reverse=True)[:10]
        for agent in self.agents:
            if agent not in high_degree_agents and random.random() < 0.1:
                target = random.choice(high_degree_agents)
                if not self._are_connected(agent.agent_id, target.agent_id):
                    connection = SocialConnection(
                        agent1=agent.agent_id,
                        agent2=target.agent_id,
                        connection_type="preferential_attachment",
                        strength=random.uniform(0.2, 0.4),
                        duration=0,
                        last_interaction=self.simulation_time,
                        trust_level=random.uniform(0.3, 0.5)
                    )
                    self.connections.append(connection)
    
    def simulate_step(self) -> Dict[str, Any]:
        """Run one simulation step"""
        step_results = {
            'step': self.step_count,
            'timestamp': self.simulation_time.isoformat(),
            'events': [],
            'metrics': {}
        }
        
        # Update opinions through social influence
        opinion_changes = self._update_opinions()
        if opinion_changes:
            step_results['events'].append(('opinion_updates', len(opinion_changes)))
        
        # Evolve social network
        old_connection_count = len(self.connections)
        self.connections = self.network_evolution.evolve_network(self.agents, self.connections)
        new_connection_count = len(self.connections)
        if new_connection_count != old_connection_count:
            step_results['events'].append(('network_evolution', new_connection_count - old_connection_count))
        
        # Evolve culture
        cultural_changes = self.cultural_evolution.evolve_culture(self.agents, self.connections)
        if cultural_changes['transmissions'] > 0:
            step_results['events'].append(('cultural_transmission', cultural_changes['transmissions']))
        
        # Update groups
        old_group_count = len(self.groups)
        self.groups = self.group_dynamics.update_groups(self.agents, self.connections, self.groups)
        new_group_count = len(self.groups)
        if new_group_count != old_group_count:
            step_results['events'].append(('group_changes', new_group_count - old_group_count))
        
        # Generate social interactions
        interactions = self._generate_interactions()
        if interactions:
            step_results['events'].append(('social_interactions', len(interactions)))
        
        # Update metrics
        step_results['metrics'] = self._calculate_metrics()
        
        # Advance time
        self.step_count += 1
        self.simulation_time += timedelta(hours=1)
        
        # Log significant events
        for event_type, count in step_results['events']:
            self._log_event(event_type, f"Step {self.step_count}: {count}")
        
        return step_results
    
    async def run_simulation(self, steps: int = 100, step_interval: float = 0.1) -> Dict[str, Any]:
        """Run multi-step simulation"""
        simulation_results = {
            'total_steps': steps,
            'start_time': self.simulation_time.isoformat(),
            'step_results': [],
            'final_metrics': {},
            'summary': {}
        }
        
        self._log_event("simulation_started", f"Running {steps} steps")
        
        for step in range(steps):
            step_result = self.simulate_step()
            simulation_results['step_results'].append(step_result)
            
            # Store metrics for analysis
            for metric, value in step_result['metrics'].items():
                self.metrics[metric].append(value)
            
            await asyncio.sleep(step_interval)
        
        # Calculate final metrics and summary
        simulation_results['final_metrics'] = self._calculate_metrics()
        simulation_results['summary'] = self._generate_summary()
        simulation_results['end_time'] = self.simulation_time.isoformat()
        
        self._log_event("simulation_completed", f"Completed {steps} steps")
        
        return simulation_results
    
    def _update_opinions(self) -> Dict[str, Dict[str, float]]:
        """Update agent opinions through social influence"""
        all_opinion_changes = {}
        topics = ["politics", "environment", "technology", "economy", "education"]
        
        for topic in topics:
            opinion_changes = self.opinion_model.update_opinions(self.agents, self.connections, topic)
            
            # Apply changes to agents
            agent_dict = {agent.agent_id: agent for agent in self.agents}
            for agent_id, change in opinion_changes.items():
                if agent_id in agent_dict:
                    old_opinion = agent_dict[agent_id].opinions.get(topic, 0.0)
                    new_opinion = old_opinion + change
                    agent_dict[agent_id].opinions[topic] = np.clip(new_opinion, -1, 1)
            
            if any(abs(change) > 0.001 for change in opinion_changes.values()):
                all_opinion_changes[topic] = opinion_changes
        
        return all_opinion_changes
    
    def _generate_interactions(self) -> List[SocialInteraction]:
        """Generate social interactions between agents"""
        interactions = []
        
        # Random interactions based on network connections
        for connection in self.connections:
            if random.random() < 0.05 * connection.strength:  # Probability based on connection strength
                agent1 = self._get_agent(connection.agent1)
                agent2 = self._get_agent(connection.agent2)
                
                if agent1 and agent2:
                    interaction = self._create_interaction(agent1, agent2, connection)
                    interactions.append(interaction)
                    
                    # Update agent interaction histories
                    agent1.interaction_history.append({
                        'partner': agent2.agent_id,
                        'type': interaction.interaction_type.value,
                        'timestamp': interaction.timestamp.isoformat()
                    })
                    agent2.interaction_history.append({
                        'partner': agent1.agent_id,
                        'type': interaction.interaction_type.value,
                        'timestamp': interaction.timestamp.isoformat()
                    })
        
        return interactions
    
    def _create_interaction(self, agent1: Agent, agent2: Agent, 
                          connection: SocialConnection) -> SocialInteraction:
        """Create a social interaction between two agents"""
        interaction_types = list(InteractionType)
        interaction_type = random.choice(interaction_types)
        
        topic = random.choice(["politics", "environment", "technology", "economy", "education", None])
        
        # Simple interaction outcome
        outcome = {
            'success': random.random() > 0.2,
            'satisfaction': random.uniform(0.3, 1.0),
            'trust_change': random.uniform(-0.05, 0.1)
        }
        
        # Update trust in connection
        connection.trust_level = np.clip(
            connection.trust_level + outcome['trust_change'], 
            0, 1
        )
        
        return SocialInteraction(
            interaction_id=f"interaction_{self.step_count}_{int(time.time())}",
            participants=[agent1.agent_id, agent2.agent_id],
            interaction_type=interaction_type,
            topic=topic,
            outcome=outcome,
            influence_changes={},
            opinion_changes={}
        )
    
    def _calculate_metrics(self) -> Dict[str, float]:
        """Calculate simulation metrics"""
        metrics = {}
        
        # Network metrics
        metrics['total_agents'] = len(self.agents)
        metrics['total_connections'] = len(self.connections)
        metrics['average_degree'] = np.mean([self._get_degree(agent) for agent in self.agents])
        metrics['network_density'] = self._calculate_network_density()
        
        # Opinion metrics
        for topic in ["politics", "environment", "technology", "economy", "education"]:
            opinions = [agent.opinions.get(topic, 0) for agent in self.agents]
            metrics[f'{topic}_opinion_mean'] = np.mean(opinions)
            metrics[f'{topic}_opinion_std'] = np.std(opinions)
            metrics[f'{topic}_polarization'] = self._calculate_polarization(opinions)
        
        # Cultural diversity
        metrics['cultural_diversity'] = self._calculate_cultural_diversity()
        
        # Group metrics
        metrics['total_groups'] = len(self.groups)
        if self.groups:
            group_sizes = [len(members) for members in self.groups.values()]
            metrics['average_group_size'] = np.mean(group_sizes)
            metrics['max_group_size'] = max(group_sizes)
        else:
            metrics['average_group_size'] = 0
            metrics['max_group_size'] = 0
        
        # Social capital
        social_capitals = [agent.social_capital for agent in self.agents]
        metrics['average_social_capital'] = np.mean(social_capitals)
        metrics['social_capital_inequality'] = np.std(social_capitals)
        
        return metrics
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate simulation summary"""
        return {
            'population_size': self.population_size,
            'total_steps': self.step_count,
            'final_network_size': len(self.connections),
            'final_group_count': len(self.groups),
            'opinion_convergence': self._analyze_opinion_convergence(),
            'cultural_evolution_summary': self._analyze_cultural_evolution(),
            'network_evolution_summary': self._analyze_network_evolution()
        }
    
    def _analyze_opinion_convergence(self) -> Dict[str, Any]:
        """Analyze opinion convergence across topics"""
        convergence = {}
        topics = ["politics", "environment", "technology", "economy", "education"]
        
        for topic in topics:
            opinions = [agent.opinions.get(topic, 0) for agent in self.agents]
            convergence[topic] = {
                'final_mean': np.mean(opinions),
                'final_std': np.std(opinions),
                'is_converged': np.std(opinions) < 0.1
            }
        
        return convergence
    
    def _analyze_cultural_evolution(self) -> Dict[str, Any]:
        """Analyze cultural trait evolution"""
        cultural_summary = {}
        
        for trait in CulturalTrait:
            values = [agent.cultural_traits.get(trait, 0.5) for agent in self.agents]
            cultural_summary[trait.value] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'diversity_index': self._calculate_diversity_index(values)
            }
        
        return cultural_summary
    
    def _analyze_network_evolution(self) -> Dict[str, Any]:
        """Analyze network structure evolution"""
        # Build NetworkX graph for analysis
        G = nx.Graph()
        for agent in self.agents:
            G.add_node(agent.agent_id)
        for conn in self.connections:
            G.add_edge(conn.agent1, conn.agent2, weight=conn.strength)
        
        if len(G.nodes()) > 0:
            try:
                clustering = nx.average_clustering(G)
                components = nx.number_connected_components(G)
                if len(G.nodes()) > 1:
                    avg_path_length = nx.average_shortest_path_length(G) if nx.is_connected(G) else float('inf')
                else:
                    avg_path_length = 0
            except:
                clustering = 0
                components = len(G.nodes())
                avg_path_length = float('inf')
        else:
            clustering = 0
            components = 0
            avg_path_length = 0
        
        return {
            'clustering_coefficient': clustering,
            'connected_components': components,
            'average_path_length': avg_path_length,
            'network_efficiency': 1 / avg_path_length if avg_path_length != 0 and avg_path_length != float('inf') else 0
        }
    
    def _get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None
    
    def _get_degree(self, agent: Agent) -> int:
        """Get degree of agent in network"""
        degree = 0
        for conn in self.connections:
            if conn.agent1 == agent.agent_id or conn.agent2 == agent.agent_id:
                degree += 1
        return degree
    
    def _are_connected(self, agent1_id: str, agent2_id: str) -> bool:
        """Check if two agents are connected"""
        for conn in self.connections:
            if (conn.agent1 == agent1_id and conn.agent2 == agent2_id) or \
               (conn.agent1 == agent2_id and conn.agent2 == agent1_id):
                return True
        return False
    
    def _calculate_network_density(self) -> float:
        """Calculate network density"""
        n = len(self.agents)
        if n < 2:
            return 0.0
        possible_edges = n * (n - 1) / 2
        actual_edges = len(self.connections)
        return actual_edges / possible_edges if possible_edges > 0 else 0.0
    
    def _calculate_polarization(self, opinions: List[float]) -> float:
        """Calculate opinion polarization"""
        if len(opinions) < 2:
            return 0.0
        
        # Calculate distance from center (0) weighted by frequency
        distances = [abs(op) for op in opinions]
        return np.mean(distances)
    
    def _calculate_cultural_diversity(self) -> float:
        """Calculate cultural diversity using Shannon diversity index"""
        # Sample diversity calculation based on cultural trait distributions
        diversity_scores = []
        
        for trait in CulturalTrait:
            values = [agent.cultural_traits.get(trait, 0.5) for agent in self.agents]
            diversity_scores.append(self._calculate_diversity_index(values))
        
        return np.mean(diversity_scores)
    
    def _calculate_diversity_index(self, values: List[float], bins: int = 10) -> float:
        """Calculate diversity index for a set of values"""
        if not values:
            return 0.0
        
        # Bin values and calculate Shannon diversity
        hist, _ = np.histogram(values, bins=bins, range=(0, 1))
        hist = hist[hist > 0]  # Remove empty bins
        
        if len(hist) <= 1:
            return 0.0
        
        proportions = hist / np.sum(hist)
        shannon_index = -np.sum(proportions * np.log(proportions))
        
        # Normalize by maximum possible diversity
        max_diversity = np.log(len(hist))
        return shannon_index / max_diversity if max_diversity > 0 else 0.0
    
    def _log_event(self, event_type: str, description: str):
        """Log simulation event"""
        event = {
            'timestamp': self.simulation_time.isoformat(),
            'step': self.step_count,
            'type': event_type,
            'description': description
        }
        self.event_log.append(event)
    
    def export_simulation_state(self) -> Dict[str, Any]:
        """Export complete simulation state"""
        return {
            'population_size': self.population_size,
            'step_count': self.step_count,
            'simulation_time': self.simulation_time.isoformat(),
            'agents': [
                {
                    'agent_id': agent.agent_id,
                    'age': agent.age,
                    'personality': {k.value: v for k, v in agent.personality.items()},
                    'social_roles': [role.value for role in agent.social_roles],
                    'cultural_traits': {k.value: v for k, v in agent.cultural_traits.items()},
                    'opinions': agent.opinions,
                    'reputation': agent.reputation,
                    'influence': agent.influence,
                    'social_capital': agent.social_capital,
                    'groups': agent.groups
                }
                for agent in self.agents
            ],
            'connections': [
                {
                    'agent1': conn.agent1,
                    'agent2': conn.agent2,
                    'connection_type': conn.connection_type,
                    'strength': conn.strength,
                    'trust_level': conn.trust_level,
                    'duration': conn.duration,
                    'interaction_count': conn.interaction_count
                }
                for conn in self.connections
            ],
            'groups': {group_id: list(members) for group_id, members in self.groups.items()},
            'metrics_history': dict(self.metrics),
            'recent_events': list(self.event_log)[-100:]  # Last 100 events
        }


# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Create social dynamics engine
        engine = SocialDynamicsEngine(population_size=200)
        
        # Initialize population
        engine.initialize_population()
        print(f"Initialized population of {len(engine.agents)} agents")
        print(f"Initial network has {len(engine.connections)} connections")
        print(f"Formed {len(engine.groups)} initial groups")
        
        # Run simulation
        results = await engine.run_simulation(steps=50, step_interval=0.1)
        
        print(f"\nSimulation completed after {results['total_steps']} steps")
        print(f"Final network size: {results['final_metrics']['total_connections']}")
        print(f"Final group count: {results['final_metrics']['total_groups']}")
        print(f"Average degree: {results['final_metrics']['average_degree']:.2f}")
        print(f"Network density: {results['final_metrics']['network_density']:.4f}")
        
        # Opinion convergence analysis
        convergence = results['summary']['opinion_convergence']
        print(f"\nOpinion Convergence:")
        for topic, data in convergence.items():
            print(f"  {topic}: mean={data['final_mean']:.3f}, std={data['final_std']:.3f}, converged={data['is_converged']}")
        
        # Cultural diversity
        cultural_div = results['final_metrics']['cultural_diversity']
        print(f"\nCultural diversity: {cultural_div:.3f}")
        
        # Network analysis
        net_analysis = results['summary']['network_evolution_summary']
        print(f"Clustering coefficient: {net_analysis['clustering_coefficient']:.3f}")
        print(f"Connected components: {net_analysis['connected_components']}")
        
        # Export final state
        export_data = engine.export_simulation_state()
        print(f"\nExported simulation state with {len(export_data['agents'])} agents and {len(export_data['connections'])} connections")
    
    # Run the example
    asyncio.run(main())