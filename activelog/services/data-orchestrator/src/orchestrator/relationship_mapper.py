"""
Data Relationship Mapper
Maps and manages data relationships between all DMLog services
"""

import asyncio
import json
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime, timedelta

import networkx as nx
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from pydantic import BaseModel, Field

from ..models.relationships import (
    DataRelationship, RelationshipType, DataEntity, 
    ServiceDataMap, CrossServiceReference
)
from ..utils.config import Config

logger = logging.getLogger(__name__)


class RelationshipStrength(Enum):
    """Strength of data relationships"""
    WEAK = "weak"           # Optional reference
    MODERATE = "moderate"   # Important but not critical
    STRONG = "strong"       # Critical dependency
    CRITICAL = "critical"   # Cannot function without


class DataDependencyType(Enum):
    """Types of data dependencies"""
    PARENT_CHILD = "parent_child"       # One-to-many
    REFERENCE = "reference"             # Foreign key reference
    AGGREGATION = "aggregation"         # Computed from multiple sources
    SYNCHRONIZATION = "synchronization" # Must stay in sync
    DERIVATION = "derivation"           # Derived/calculated from other data
    VALIDATION = "validation"           # Used for data validation


@dataclass
class DataEntitySchema:
    """Schema definition for data entities"""
    entity_id: str
    service_name: str
    entity_name: str
    schema_version: str
    fields: Dict[str, Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, str]]
    indexes: List[str]
    constraints: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


@dataclass
class RelationshipMapping:
    """Complete relationship mapping between services"""
    source_service: str
    source_entity: str
    source_field: str
    target_service: str
    target_entity: str
    target_field: str
    relationship_type: DataDependencyType
    strength: RelationshipStrength
    is_bidirectional: bool
    cascade_deletes: bool
    validation_rules: List[str]
    transformation_required: bool
    transformation_logic: Optional[str]
    data_lineage: List[str]


class RelationshipMapper:
    """Maps and manages data relationships between all DMLog services"""
    
    def __init__(self, service_registry, db_session_factory, config: Config):
        self.service_registry = service_registry
        self.db_session_factory = db_session_factory
        self.config = config
        
        # Relationship graph
        self.relationship_graph = nx.DiGraph()
        self.entity_schemas: Dict[str, DataEntitySchema] = {}
        self.service_relationships: Dict[str, Dict[str, List[RelationshipMapping]]] = {}
        
        # DMLog service mappings
        self.dmlog_services = {
            "dmlog-core": 8019,
            "dmlog-ai-dm": 8020,
            "dmlog-battle": 8021,
            "dmlog-characters": 8022,
            "dmlog-session": 8023,
            "dmlog-templates": 8024,
            "dmlog-world": 8025,
            "dmlog-player": 8026,
            "dmlog-marketplace": 8027,
            "dmlog-converter": 8028,
            "dmlog-gamedev": 3006,
            "dmlog-stream": 8030,
            "dmlog-integration": 8203
        }
        
        # Cache for performance
        self._relationship_cache: Dict[str, Any] = {}
        self._schema_cache: Dict[str, DataEntitySchema] = {}
        self._last_cache_update = datetime.now()
        self._cache_ttl = timedelta(minutes=5)

    async def initialize(self):
        """Initialize the relationship mapper"""
        logger.info("Initializing Data Relationship Mapper")
        
        try:
            # Load existing schemas and relationships
            await self._load_existing_relationships()
            
            # Map DMLog service relationships
            await self._map_dmlog_relationships()
            
            # Build relationship graph
            await self._build_relationship_graph()
            
            # Start background refresh
            asyncio.create_task(self._periodic_refresh())
            
            logger.info("Data Relationship Mapper initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize relationship mapper: {e}")
            raise

    async def _load_existing_relationships(self):
        """Load existing relationship mappings from database"""
        async with self.db_session_factory() as session:
            # Load data entities
            result = await session.execute(select(DataEntity))
            entities = result.scalars().all()
            
            for entity in entities:
                schema = DataEntitySchema(
                    entity_id=entity.id,
                    service_name=entity.service_name,
                    entity_name=entity.entity_name,
                    schema_version=entity.schema_version,
                    fields=json.loads(entity.schema_definition),
                    primary_keys=json.loads(entity.primary_keys or "[]"),
                    foreign_keys=json.loads(entity.foreign_keys or "[]"),
                    indexes=json.loads(entity.indexes or "[]"),
                    constraints=json.loads(entity.constraints or "[]"),
                    created_at=entity.created_at,
                    updated_at=entity.updated_at
                )
                self.entity_schemas[entity.id] = schema
            
            # Load relationships
            result = await session.execute(select(DataRelationship))
            relationships = result.scalars().all()
            
            for rel in relationships:
                source_key = f"{rel.source_service}.{rel.source_entity}"
                if source_key not in self.service_relationships:
                    self.service_relationships[source_key] = {}
                
                target_key = f"{rel.target_service}.{rel.target_entity}"
                if target_key not in self.service_relationships[source_key]:
                    self.service_relationships[source_key][target_key] = []
                
                mapping = RelationshipMapping(
                    source_service=rel.source_service,
                    source_entity=rel.source_entity,
                    source_field=rel.source_field,
                    target_service=rel.target_service,
                    target_entity=rel.target_entity,
                    target_field=rel.target_field,
                    relationship_type=DataDependencyType(rel.relationship_type),
                    strength=RelationshipStrength(rel.strength),
                    is_bidirectional=rel.is_bidirectional,
                    cascade_deletes=rel.cascade_deletes,
                    validation_rules=json.loads(rel.validation_rules or "[]"),
                    transformation_required=rel.transformation_required,
                    transformation_logic=rel.transformation_logic,
                    data_lineage=json.loads(rel.data_lineage or "[]")
                )
                
                self.service_relationships[source_key][target_key].append(mapping)

    async def _map_dmlog_relationships(self):
        """Map the core DMLog service data relationships"""
        
        # Define DMLog data entity relationships
        dmlog_relationships = [
            # Core Campaign relationships
            RelationshipMapping(
                source_service="dmlog-core",
                source_entity="campaigns",
                source_field="id",
                target_service="dmlog-characters",
                target_entity="characters",
                target_field="campaign_id",
                relationship_type=DataDependencyType.PARENT_CHILD,
                strength=RelationshipStrength.CRITICAL,
                is_bidirectional=False,
                cascade_deletes=True,
                validation_rules=["campaign_must_exist"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-core.campaigns"]
            ),
            
            # Campaign to Sessions
            RelationshipMapping(
                source_service="dmlog-core",
                source_entity="campaigns",
                source_field="id",
                target_service="dmlog-session",
                target_entity="sessions",
                target_field="campaign_id",
                relationship_type=DataDependencyType.PARENT_CHILD,
                strength=RelationshipStrength.CRITICAL,
                is_bidirectional=False,
                cascade_deletes=True,
                validation_rules=["campaign_must_exist"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-core.campaigns"]
            ),
            
            # Characters to NPCs (AI DM)
            RelationshipMapping(
                source_service="dmlog-characters",
                source_entity="characters",
                source_field="id",
                target_service="dmlog-ai-dm",
                target_entity="npc_interactions",
                target_field="character_id",
                relationship_type=DataDependencyType.REFERENCE,
                strength=RelationshipStrength.MODERATE,
                is_bidirectional=False,
                cascade_deletes=False,
                validation_rules=["character_must_exist"],
                transformation_required=True,
                transformation_logic="extract_character_traits_for_ai",
                data_lineage=["dmlog-core.campaigns", "dmlog-characters.characters"]
            ),
            
            # Battle encounters
            RelationshipMapping(
                source_service="dmlog-session",
                source_entity="sessions",
                source_field="id",
                target_service="dmlog-battle",
                target_entity="encounters",
                target_field="session_id",
                relationship_type=DataDependencyType.PARENT_CHILD,
                strength=RelationshipStrength.STRONG,
                is_bidirectional=False,
                cascade_deletes=True,
                validation_rules=["session_must_be_active"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-core.campaigns", "dmlog-session.sessions"]
            ),
            
            # World building to templates
            RelationshipMapping(
                source_service="dmlog-world",
                source_entity="locations",
                source_field="template_id",
                target_service="dmlog-templates",
                target_entity="location_templates",
                target_field="id",
                relationship_type=DataDependencyType.REFERENCE,
                strength=RelationshipStrength.MODERATE,
                is_bidirectional=False,
                cascade_deletes=False,
                validation_rules=["template_must_exist"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-templates.location_templates"]
            ),
            
            # Marketplace purchases
            RelationshipMapping(
                source_service="dmlog-core",
                source_entity="users",
                source_field="id",
                target_service="dmlog-marketplace",
                target_entity="purchases",
                target_field="user_id",
                relationship_type=DataDependencyType.PARENT_CHILD,
                strength=RelationshipStrength.STRONG,
                is_bidirectional=False,
                cascade_deletes=False,
                validation_rules=["user_must_exist"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-core.users"]
            ),
            
            # Session recording
            RelationshipMapping(
                source_service="dmlog-session",
                source_entity="sessions",
                source_field="id",
                target_service="dmlog-stream",
                target_entity="recordings",
                target_field="session_id",
                relationship_type=DataDependencyType.PARENT_CHILD,
                strength=RelationshipStrength.STRONG,
                is_bidirectional=False,
                cascade_deletes=True,
                validation_rules=["session_must_exist"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-core.campaigns", "dmlog-session.sessions"]
            ),
            
            # Game development export
            RelationshipMapping(
                source_service="dmlog-core",
                source_entity="campaigns",
                source_field="id",
                target_service="dmlog-gamedev",
                target_entity="exports",
                target_field="campaign_id",
                relationship_type=DataDependencyType.AGGREGATION,
                strength=RelationshipStrength.MODERATE,
                is_bidirectional=False,
                cascade_deletes=False,
                validation_rules=["campaign_must_exist"],
                transformation_required=True,
                transformation_logic="aggregate_campaign_data_for_export",
                data_lineage=["dmlog-core.campaigns", "dmlog-characters.characters", "dmlog-world.locations"]
            ),
            
            # Character progression tracking
            RelationshipMapping(
                source_service="dmlog-characters",
                source_entity="characters",
                source_field="id",
                target_service="dmlog-player",
                target_entity="character_progression",
                target_field="character_id",
                relationship_type=DataDependencyType.SYNCHRONIZATION,
                strength=RelationshipStrength.STRONG,
                is_bidirectional=True,
                cascade_deletes=True,
                validation_rules=["character_must_exist", "sync_level_and_xp"],
                transformation_required=False,
                transformation_logic=None,
                data_lineage=["dmlog-core.campaigns", "dmlog-characters.characters"]
            ),
            
            # Content conversion relationships
            RelationshipMapping(
                source_service="dmlog-templates",
                source_entity="campaign_templates",
                source_field="id",
                target_service="dmlog-converter",
                target_entity="conversion_jobs",
                target_field="source_template_id",
                relationship_type=DataDependencyType.REFERENCE,
                strength=RelationshipStrength.MODERATE,
                is_bidirectional=False,
                cascade_deletes=False,
                validation_rules=["template_must_exist"],
                transformation_required=True,
                transformation_logic="convert_template_format",
                data_lineage=["dmlog-templates.campaign_templates"]
            )
        ]
        
        # Store relationships
        for mapping in dmlog_relationships:
            source_key = f"{mapping.source_service}.{mapping.source_entity}"
            target_key = f"{mapping.target_service}.{mapping.target_entity}"
            
            if source_key not in self.service_relationships:
                self.service_relationships[source_key] = {}
            if target_key not in self.service_relationships[source_key]:
                self.service_relationships[source_key][target_key] = []
            
            self.service_relationships[source_key][target_key].append(mapping)
            
            # Store in database
            await self._store_relationship_mapping(mapping)

    async def _store_relationship_mapping(self, mapping: RelationshipMapping):
        """Store relationship mapping in database"""
        async with self.db_session_factory() as session:
            try:
                relationship = DataRelationship(
                    source_service=mapping.source_service,
                    source_entity=mapping.source_entity,
                    source_field=mapping.source_field,
                    target_service=mapping.target_service,
                    target_entity=mapping.target_entity,
                    target_field=mapping.target_field,
                    relationship_type=mapping.relationship_type.value,
                    strength=mapping.strength.value,
                    is_bidirectional=mapping.is_bidirectional,
                    cascade_deletes=mapping.cascade_deletes,
                    validation_rules=json.dumps(mapping.validation_rules),
                    transformation_required=mapping.transformation_required,
                    transformation_logic=mapping.transformation_logic,
                    data_lineage=json.dumps(mapping.data_lineage),
                    is_active=True
                )
                
                session.add(relationship)
                await session.commit()
                
            except Exception as e:
                logger.error(f"Failed to store relationship mapping: {e}")
                await session.rollback()

    async def _build_relationship_graph(self):
        """Build NetworkX graph of service relationships"""
        self.relationship_graph.clear()
        
        # Add service nodes
        for service in self.dmlog_services:
            self.relationship_graph.add_node(service, type="service")
        
        # Add entity nodes and relationships
        for source_key, targets in self.service_relationships.items():
            source_service, source_entity = source_key.split('.', 1)
            entity_node = f"{source_service}.{source_entity}"
            
            if not self.relationship_graph.has_node(entity_node):
                self.relationship_graph.add_node(entity_node, type="entity", service=source_service)
            
            for target_key, mappings in targets.items():
                target_service, target_entity = target_key.split('.', 1)
                target_node = f"{target_service}.{target_entity}"
                
                if not self.relationship_graph.has_node(target_node):
                    self.relationship_graph.add_node(target_node, type="entity", service=target_service)
                
                # Add edges for each mapping
                for mapping in mappings:
                    edge_data = {
                        'relationship_type': mapping.relationship_type.value,
                        'strength': mapping.strength.value,
                        'bidirectional': mapping.is_bidirectional,
                        'cascade_deletes': mapping.cascade_deletes,
                        'transformation_required': mapping.transformation_required
                    }
                    
                    self.relationship_graph.add_edge(entity_node, target_node, **edge_data)
                    
                    if mapping.is_bidirectional:
                        self.relationship_graph.add_edge(target_node, entity_node, **edge_data)

    async def get_service_dependencies(self, service_name: str) -> Dict[str, List[str]]:
        """Get all dependencies for a service"""
        dependencies = {
            'upstream': [],    # Services this service depends on
            'downstream': [],  # Services that depend on this service
            'critical': [],    # Critical dependencies
            'optional': []     # Optional dependencies
        }
        
        for node in self.relationship_graph.nodes():
            if node.startswith(service_name + '.'):
                # Find upstream dependencies
                for predecessor in self.relationship_graph.predecessors(node):
                    pred_service = predecessor.split('.')[0]
                    if pred_service != service_name and pred_service not in dependencies['upstream']:
                        dependencies['upstream'].append(pred_service)
                        
                        # Check if critical
                        edge_data = self.relationship_graph.get_edge_data(predecessor, node)
                        if edge_data and edge_data.get('strength') in ['critical', 'strong']:
                            if pred_service not in dependencies['critical']:
                                dependencies['critical'].append(pred_service)
                        else:
                            if pred_service not in dependencies['optional']:
                                dependencies['optional'].append(pred_service)
                
                # Find downstream dependencies
                for successor in self.relationship_graph.successors(node):
                    succ_service = successor.split('.')[0]
                    if succ_service != service_name and succ_service not in dependencies['downstream']:
                        dependencies['downstream'].append(succ_service)
        
        return dependencies

    async def get_data_lineage(self, service_name: str, entity_name: str, field_name: str) -> List[Dict[str, Any]]:
        """Get complete data lineage for a field"""
        lineage = []
        entity_key = f"{service_name}.{entity_name}"
        
        if entity_key in self.service_relationships:
            for target_key, mappings in self.service_relationships[entity_key].items():
                for mapping in mappings:
                    if mapping.source_field == field_name:
                        lineage_entry = {
                            'source_service': mapping.source_service,
                            'source_entity': mapping.source_entity,
                            'source_field': mapping.source_field,
                            'target_service': mapping.target_service,
                            'target_entity': mapping.target_entity,
                            'target_field': mapping.target_field,
                            'transformation': mapping.transformation_logic,
                            'lineage_path': mapping.data_lineage
                        }
                        lineage.append(lineage_entry)
        
        return lineage

    async def analyze_impact(self, service_name: str, entity_name: str) -> Dict[str, Any]:
        """Analyze impact of changes to an entity"""
        impact_analysis = {
            'directly_affected': [],
            'cascading_affected': [],
            'transformation_required': [],
            'validation_failures': [],
            'critical_impacts': [],
            'impact_score': 0
        }
        
        entity_key = f"{service_name}.{entity_name}"
        
        # Direct impacts
        if entity_key in self.service_relationships:
            for target_key, mappings in self.service_relationships[entity_key].items():
                for mapping in mappings:
                    impact_entry = {
                        'service': mapping.target_service,
                        'entity': mapping.target_entity,
                        'field': mapping.target_field,
                        'strength': mapping.strength.value,
                        'cascade_deletes': mapping.cascade_deletes
                    }
                    
                    impact_analysis['directly_affected'].append(impact_entry)
                    
                    if mapping.transformation_required:
                        impact_analysis['transformation_required'].append(impact_entry)
                    
                    if mapping.strength in [RelationshipStrength.CRITICAL, RelationshipStrength.STRONG]:
                        impact_analysis['critical_impacts'].append(impact_entry)
                        impact_analysis['impact_score'] += 10 if mapping.strength == RelationshipStrength.CRITICAL else 5
                    else:
                        impact_analysis['impact_score'] += 2 if mapping.strength == RelationshipStrength.MODERATE else 1
        
        # Find cascading impacts using graph traversal
        entity_node = f"{service_name}.{entity_name}"
        if self.relationship_graph.has_node(entity_node):
            visited = set()
            
            def dfs_impact(node, depth=0):
                if node in visited or depth > 5:  # Prevent infinite loops and limit depth
                    return
                visited.add(node)
                
                for successor in self.relationship_graph.successors(node):
                    if successor != entity_node:  # Don't include self
                        succ_service, succ_entity = successor.split('.', 1)
                        impact_entry = {
                            'service': succ_service,
                            'entity': succ_entity,
                            'depth': depth + 1,
                            'path_length': depth + 1
                        }
                        
                        if impact_entry not in impact_analysis['cascading_affected']:
                            impact_analysis['cascading_affected'].append(impact_entry)
                        
                        dfs_impact(successor, depth + 1)
            
            dfs_impact(entity_node)
        
        return impact_analysis

    async def validate_relationships(self) -> Dict[str, List[Dict[str, Any]]]:
        """Validate all relationship mappings"""
        validation_results = {
            'valid': [],
            'invalid': [],
            'warnings': [],
            'missing_services': [],
            'orphaned_entities': []
        }
        
        # Check each relationship
        for source_key, targets in self.service_relationships.items():
            source_service = source_key.split('.')[0]
            
            # Check if source service exists
            if source_service not in self.dmlog_services:
                validation_results['missing_services'].append({
                    'service': source_service,
                    'reason': 'Source service not found in DMLog services registry'
                })
                continue
            
            for target_key, mappings in targets.items():
                target_service = target_key.split('.')[0]
                
                # Check if target service exists
                if target_service not in self.dmlog_services:
                    validation_results['missing_services'].append({
                        'service': target_service,
                        'reason': 'Target service not found in DMLog services registry'
                    })
                    continue
                
                for mapping in mappings:
                    validation_entry = {
                        'source': source_key,
                        'target': target_key,
                        'mapping': asdict(mapping)
                    }
                    
                    # Validate mapping consistency
                    if await self._validate_mapping(mapping):
                        validation_results['valid'].append(validation_entry)
                    else:
                        validation_results['invalid'].append(validation_entry)
        
        return validation_results

    async def _validate_mapping(self, mapping: RelationshipMapping) -> bool:
        """Validate a single relationship mapping"""
        try:
            # Check if services are reachable
            source_available = await self.service_registry.is_service_healthy(mapping.source_service)
            target_available = await self.service_registry.is_service_healthy(mapping.target_service)
            
            if not source_available or not target_available:
                return False
            
            # Additional validation logic can be added here
            # e.g., check if entities and fields actually exist
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating mapping: {e}")
            return False

    async def get_relationship_statistics(self) -> Dict[str, Any]:
        """Get comprehensive relationship statistics"""
        stats = {
            'total_services': len(self.dmlog_services),
            'total_entities': len(self.entity_schemas),
            'total_relationships': sum(len(mappings) for targets in self.service_relationships.values() for mappings in targets.values()),
            'relationship_types': {},
            'strength_distribution': {},
            'transformation_required': 0,
            'bidirectional_relationships': 0,
            'cascade_deletes': 0,
            'graph_metrics': {}
        }
        
        # Count relationship types and strengths
        for targets in self.service_relationships.values():
            for mappings in targets.values():
                for mapping in mappings:
                    # Count relationship types
                    rel_type = mapping.relationship_type.value
                    stats['relationship_types'][rel_type] = stats['relationship_types'].get(rel_type, 0) + 1
                    
                    # Count strength distribution
                    strength = mapping.strength.value
                    stats['strength_distribution'][strength] = stats['strength_distribution'].get(strength, 0) + 1
                    
                    # Count special properties
                    if mapping.transformation_required:
                        stats['transformation_required'] += 1
                    if mapping.is_bidirectional:
                        stats['bidirectional_relationships'] += 1
                    if mapping.cascade_deletes:
                        stats['cascade_deletes'] += 1
        
        # Graph metrics
        if self.relationship_graph:
            stats['graph_metrics'] = {
                'nodes': self.relationship_graph.number_of_nodes(),
                'edges': self.relationship_graph.number_of_edges(),
                'density': nx.density(self.relationship_graph),
                'is_connected': nx.is_weakly_connected(self.relationship_graph),
                'strongly_connected_components': nx.number_strongly_connected_components(self.relationship_graph)
            }
            
            # Calculate centrality measures
            try:
                stats['graph_metrics']['betweenness_centrality'] = nx.betweenness_centrality(self.relationship_graph)
                stats['graph_metrics']['degree_centrality'] = nx.degree_centrality(self.relationship_graph)
            except:
                pass  # Skip if graph is too complex
        
        return stats

    async def _periodic_refresh(self):
        """Periodically refresh relationship mappings"""
        while True:
            try:
                await asyncio.sleep(300)  # Refresh every 5 minutes
                
                # Check if cache needs refresh
                if datetime.now() - self._last_cache_update > self._cache_ttl:
                    await self._refresh_cache()
                    self._last_cache_update = datetime.now()
                
                # Validate relationships periodically
                await self.validate_relationships()
                
            except Exception as e:
                logger.error(f"Error in periodic refresh: {e}")
                await asyncio.sleep(60)

    async def _refresh_cache(self):
        """Refresh internal caches"""
        self._relationship_cache.clear()
        self._schema_cache.clear()
        
        # Reload from database
        await self._load_existing_relationships()
        
        # Rebuild graph
        await self._build_relationship_graph()

    async def export_relationship_map(self, format_type: str = "json") -> str:
        """Export relationship map in various formats"""
        if format_type == "json":
            export_data = {
                'services': list(self.dmlog_services.keys()),
                'entities': {k: asdict(v) for k, v in self.entity_schemas.items()},
                'relationships': {}
            }
            
            for source_key, targets in self.service_relationships.items():
                export_data['relationships'][source_key] = {}
                for target_key, mappings in targets.items():
                    export_data['relationships'][source_key][target_key] = [
                        asdict(mapping) for mapping in mappings
                    ]
            
            return json.dumps(export_data, indent=2, default=str)
        
        elif format_type == "graphml":
            # Export as GraphML for visualization tools
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.graphml', delete=False) as f:
                nx.write_graphml(self.relationship_graph, f.name)
                with open(f.name, 'r') as graph_file:
                    return graph_file.read()
        
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up Relationship Mapper")
        self.relationship_graph.clear()
        self._relationship_cache.clear()
        self._schema_cache.clear()