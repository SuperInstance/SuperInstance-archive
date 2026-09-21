#!/usr/bin/env python3
"""
Relationship Mapping Engine - Creates intelligent connections between files, events, and people.
Builds a knowledge graph of relationships to improve predictions and provide contextual insights.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter
import hashlib
import math

class RelationshipType(Enum):
    CO_OCCURRENCE = "co_occurrence"        # Files accessed together
    TEMPORAL = "temporal"                   # Files accessed in time proximity
    SEMANTIC = "semantic"                   # Content similarity
    HIERARCHICAL = "hierarchical"          # Parent-child relationships
    SEQUENCE = "sequence"                   # Files in workflow sequence
    COLLABORATION = "collaboration"        # Files shared between people
    EVENT_BASED = "event_based"           # Files related to same event
    LOCATION = "location"                  # Files from same location
    PROJECT = "project"                    # Files in same project/context

class EntityType(Enum):
    FILE = "file"
    PERSON = "person"
    EVENT = "event"
    LOCATION = "location"
    PROJECT = "project"
    CONCEPT = "concept"
    ORGANIZATION = "organization"
    DATE = "date"

class RelationshipStrength(Enum):
    WEAK = "weak"           # 0.0 - 0.3
    MODERATE = "moderate"   # 0.3 - 0.6
    STRONG = "strong"       # 0.6 - 0.8
    VERY_STRONG = "very_strong"  # 0.8 - 1.0

@dataclass
class Entity:
    """Represents an entity in the relationship graph."""
    entity_id: str
    entity_type: EntityType
    name: str
    attributes: Dict[str, Any]
    created_at: datetime
    last_updated: datetime
    access_count: int = 0
    metadata: Dict[str, Any] = None

@dataclass
class Relationship:
    """Represents a relationship between two entities."""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: RelationshipType
    strength: float  # 0.0 to 1.0
    confidence: float  # How confident we are in this relationship
    evidence: List[str]  # Evidence supporting this relationship
    created_at: datetime
    last_seen: datetime
    occurrence_count: int
    metadata: Dict[str, Any] = None

@dataclass
class RelationshipInsight:
    """Insight derived from relationship analysis."""
    insight_id: str
    user_id: str
    insight_type: str
    title: str
    description: str
    confidence: float
    supporting_entities: List[str]
    supporting_relationships: List[str]
    actionable_suggestions: List[str]
    created_at: datetime

class EntityExtractor:
    """Extracts entities from file content and metadata."""
    
    def __init__(self):
        self.person_patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last names
            r'\b[A-Za-z]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',  # Email addresses
        ]
        
        self.organization_patterns = [
            r'\b[A-Z][a-zA-Z]+ (?:Inc|Corp|LLC|Ltd|Company|Co)\b',
            r'\b(?:Department of|Ministry of) [A-Z][a-zA-Z ]+\b'
        ]
        
        self.location_patterns = [
            r'\b[A-Z][a-z]+ (?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive)\b',
            r'\b[A-Z][a-z]+, [A-Z][A-Z]\b',  # City, State
            r'\b\d{5}(?:-\d{4})?\b'  # ZIP codes
        ]
        
        self.date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{4}\b',  # MM/DD/YYYY
            r'\b\d{4}-\d{2}-\d{2}\b',      # YYYY-MM-DD
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}, \d{4}\b'
        ]
        
        self.concept_keywords = {
            "financial": ["budget", "expense", "revenue", "profit", "investment", "tax", "invoice"],
            "medical": ["doctor", "patient", "diagnosis", "treatment", "medication", "appointment"],
            "legal": ["contract", "agreement", "lawsuit", "defendant", "plaintiff", "court"],
            "education": ["student", "teacher", "course", "assignment", "grade", "exam"],
            "technology": ["software", "hardware", "database", "server", "network", "security"],
            "project": ["milestone", "deadline", "deliverable", "requirement", "specification"]
        }
    
    def extract_entities(self, file_info: Dict[str, Any]) -> List[Entity]:
        """Extract entities from file information."""
        entities = []
        content = file_info.get("content", "")
        filename = file_info.get("name", "")
        full_text = f"{filename} {content}"
        
        current_time = datetime.now()
        
        # Extract file entity (always present)
        file_entity = Entity(
            entity_id=self._generate_entity_id(EntityType.FILE, filename),
            entity_type=EntityType.FILE,
            name=filename,
            attributes={
                "path": file_info.get("path", ""),
                "size": file_info.get("size", 0),
                "extension": filename.split(".")[-1] if "." in filename else "",
                "created_at": file_info.get("created_at"),
                "modified_at": file_info.get("modified_at")
            },
            created_at=current_time,
            last_updated=current_time,
            metadata={"original_file_info": file_info}
        )
        entities.append(file_entity)
        
        # Extract people
        for pattern in self.person_patterns:
            matches = re.findall(pattern, full_text)
            for match in set(matches):  # Remove duplicates
                if self._is_valid_person_name(match):
                    person_entity = Entity(
                        entity_id=self._generate_entity_id(EntityType.PERSON, match),
                        entity_type=EntityType.PERSON,
                        name=match,
                        attributes={"confidence": 0.8},
                        created_at=current_time,
                        last_updated=current_time
                    )
                    entities.append(person_entity)
        
        # Extract organizations
        for pattern in self.organization_patterns:
            matches = re.findall(pattern, full_text)
            for match in set(matches):
                org_entity = Entity(
                    entity_id=self._generate_entity_id(EntityType.ORGANIZATION, match),
                    entity_type=EntityType.ORGANIZATION,
                    name=match,
                    attributes={"confidence": 0.7},
                    created_at=current_time,
                    last_updated=current_time
                )
                entities.append(org_entity)
        
        # Extract locations
        for pattern in self.location_patterns:
            matches = re.findall(pattern, full_text)
            for match in set(matches):
                location_entity = Entity(
                    entity_id=self._generate_entity_id(EntityType.LOCATION, match),
                    entity_type=EntityType.LOCATION,
                    name=match,
                    attributes={"confidence": 0.6},
                    created_at=current_time,
                    last_updated=current_time
                )
                entities.append(location_entity)
        
        # Extract dates
        for pattern in self.date_patterns:
            matches = re.findall(pattern, full_text)
            for match in set(matches):
                try:
                    # Try to parse the date to validate it
                    parsed_date = self._parse_date(match)
                    if parsed_date:
                        date_entity = Entity(
                            entity_id=self._generate_entity_id(EntityType.DATE, match),
                            entity_type=EntityType.DATE,
                            name=match,
                            attributes={
                                "parsed_date": parsed_date.isoformat(),
                                "confidence": 0.9
                            },
                            created_at=current_time,
                            last_updated=current_time
                        )
                        entities.append(date_entity)
                except:
                    pass
        
        # Extract concepts
        content_lower = full_text.lower()
        for concept_category, keywords in self.concept_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in content_lower)
            if matches >= 2:  # At least 2 keywords from category
                concept_entity = Entity(
                    entity_id=self._generate_entity_id(EntityType.CONCEPT, concept_category),
                    entity_type=EntityType.CONCEPT,
                    name=concept_category.title(),
                    attributes={
                        "keyword_matches": matches,
                        "confidence": min(0.9, matches * 0.2)
                    },
                    created_at=current_time,
                    last_updated=current_time
                )
                entities.append(concept_entity)
        
        return entities
    
    def _generate_entity_id(self, entity_type: EntityType, name: str) -> str:
        """Generate unique entity ID."""
        return hashlib.md5(f"{entity_type.value}_{name.lower()}".encode()).hexdigest()
    
    def _is_valid_person_name(self, name: str) -> bool:
        """Validate if extracted text is likely a person name."""
        # Simple heuristics to filter out false positives
        if len(name.split()) != 2:
            return False
        
        # Exclude common false positives
        false_positives = {
            "United States", "New York", "Los Angeles", "San Francisco",
            "Microsoft Corporation", "Apple Inc", "Google LLC"
        }
        
        return name not in false_positives
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object."""
        date_formats = [
            "%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y"
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None

class RelationshipAnalyzer:
    """Analyzes relationships between entities."""
    
    def __init__(self):
        self.co_occurrence_window = timedelta(hours=2)
        self.temporal_window = timedelta(days=1)
        
    def analyze_relationships(self, entities_by_file: Dict[str, List[Entity]], 
                            access_history: List[Dict[str, Any]]) -> List[Relationship]:
        """Analyze relationships between entities."""
        relationships = []
        
        # 1. Co-occurrence relationships
        co_occurrence_rels = self._analyze_co_occurrence(entities_by_file)
        relationships.extend(co_occurrence_rels)
        
        # 2. Temporal relationships
        temporal_rels = self._analyze_temporal_relationships(entities_by_file, access_history)
        relationships.extend(temporal_rels)
        
        # 3. Semantic relationships
        semantic_rels = self._analyze_semantic_relationships(entities_by_file)
        relationships.extend(semantic_rels)
        
        # 4. Hierarchical relationships
        hierarchical_rels = self._analyze_hierarchical_relationships(entities_by_file)
        relationships.extend(hierarchical_rels)
        
        # 5. Sequence relationships
        sequence_rels = self._analyze_sequence_relationships(entities_by_file, access_history)
        relationships.extend(sequence_rels)
        
        return relationships
    
    def _analyze_co_occurrence(self, entities_by_file: Dict[str, List[Entity]]) -> List[Relationship]:
        """Find entities that frequently appear together in files."""
        relationships = []
        entity_pairs = defaultdict(int)
        entity_files = defaultdict(set)
        
        # Build co-occurrence matrix
        for file_path, entities in entities_by_file.items():
            # Skip file entities for co-occurrence
            non_file_entities = [e for e in entities if e.entity_type != EntityType.FILE]
            
            # Record which files each entity appears in
            for entity in non_file_entities:
                entity_files[entity.entity_id].add(file_path)
            
            # Count co-occurrences
            for i, entity1 in enumerate(non_file_entities):
                for entity2 in non_file_entities[i+1:]:
                    pair = tuple(sorted([entity1.entity_id, entity2.entity_id]))
                    entity_pairs[pair] += 1
        
        # Create relationships for significant co-occurrences
        for (entity1_id, entity2_id), count in entity_pairs.items():
            if count >= 2:  # At least 2 co-occurrences
                # Calculate Jaccard similarity
                files1 = entity_files[entity1_id]
                files2 = entity_files[entity2_id]
                intersection = len(files1 & files2)
                union = len(files1 | files2)
                strength = intersection / union if union > 0 else 0
                
                if strength >= 0.2:  # Minimum strength threshold
                    relationship = Relationship(
                        relationship_id=self._generate_relationship_id(entity1_id, entity2_id, RelationshipType.CO_OCCURRENCE),
                        source_entity_id=entity1_id,
                        target_entity_id=entity2_id,
                        relationship_type=RelationshipType.CO_OCCURRENCE,
                        strength=strength,
                        confidence=min(0.9, count * 0.2),
                        evidence=[f"Co-occurred in {count} files", f"Jaccard similarity: {strength:.2f}"],
                        created_at=datetime.now(),
                        last_seen=datetime.now(),
                        occurrence_count=count,
                        metadata={"shared_files": list(files1 & files2)}
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _analyze_temporal_relationships(self, entities_by_file: Dict[str, List[Entity]], 
                                      access_history: List[Dict[str, Any]]) -> List[Relationship]:
        """Find entities that appear in temporally related files."""
        relationships = []
        
        # Group access history by time windows
        time_windows = defaultdict(list)
        
        for access in access_history:
            access_time = access.get("access_time")
            if isinstance(access_time, str):
                access_time = datetime.fromisoformat(access_time)
            
            # Create time windows (e.g., daily windows)
            window_key = access_time.strftime("%Y-%m-%d")
            time_windows[window_key].append(access)
        
        # Find entities that appear in same time windows
        for window_key, accesses in time_windows.items():
            if len(accesses) < 2:
                continue
            
            # Get all entities from files in this time window
            window_entities = []
            for access in accesses:
                file_path = access.get("file_path", "")
                if file_path in entities_by_file:
                    window_entities.extend(entities_by_file[file_path])
            
            # Create temporal relationships
            entity_pairs = defaultdict(int)
            for i, entity1 in enumerate(window_entities):
                for entity2 in window_entities[i+1:]:
                    if entity1.entity_type != EntityType.FILE and entity2.entity_type != EntityType.FILE:
                        pair = tuple(sorted([entity1.entity_id, entity2.entity_id]))
                        entity_pairs[pair] += 1
            
            for (entity1_id, entity2_id), count in entity_pairs.items():
                if count >= 2:
                    relationship = Relationship(
                        relationship_id=self._generate_relationship_id(entity1_id, entity2_id, RelationshipType.TEMPORAL),
                        source_entity_id=entity1_id,
                        target_entity_id=entity2_id,
                        relationship_type=RelationshipType.TEMPORAL,
                        strength=min(1.0, count * 0.3),
                        confidence=0.6,
                        evidence=[f"Appeared in {count} files within {window_key}"],
                        created_at=datetime.now(),
                        last_seen=datetime.now(),
                        occurrence_count=count,
                        metadata={"time_window": window_key}
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _analyze_semantic_relationships(self, entities_by_file: Dict[str, List[Entity]]) -> List[Relationship]:
        """Find entities with semantic relationships."""
        relationships = []
        
        # Group entities by type and look for semantic similarities
        entities_by_type = defaultdict(list)
        all_entities = []
        
        for entities in entities_by_file.values():
            all_entities.extend(entities)
        
        for entity in all_entities:
            entities_by_type[entity.entity_type].append(entity)
        
        # Semantic relationships between concepts
        concepts = entities_by_type[EntityType.CONCEPT]
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Check for semantic similarity (simplified)
                similarity = self._calculate_semantic_similarity(concept1, concept2)
                if similarity >= 0.5:
                    relationship = Relationship(
                        relationship_id=self._generate_relationship_id(concept1.entity_id, concept2.entity_id, RelationshipType.SEMANTIC),
                        source_entity_id=concept1.entity_id,
                        target_entity_id=concept2.entity_id,
                        relationship_type=RelationshipType.SEMANTIC,
                        strength=similarity,
                        confidence=0.7,
                        evidence=[f"Semantic similarity: {similarity:.2f}"],
                        created_at=datetime.now(),
                        last_seen=datetime.now(),
                        occurrence_count=1,
                        metadata={"similarity_type": "concept"}
                    )
                    relationships.append(relationship)
        
        return relationships
    
    def _analyze_hierarchical_relationships(self, entities_by_file: Dict[str, List[Entity]]) -> List[Relationship]:
        """Find hierarchical relationships (parent-child)."""
        relationships = []
        
        # Look for file path hierarchies
        file_entities = []
        for entities in entities_by_file.values():
            file_entities.extend([e for e in entities if e.entity_type == EntityType.FILE])
        
        # Create parent-child relationships based on file paths
        for entity in file_entities:
            file_path = entity.attributes.get("path", entity.name)
            if "/" in file_path:
                parent_path = "/".join(file_path.split("/")[:-1])
                
                # Find potential parent file
                for potential_parent in file_entities:
                    parent_file_path = potential_parent.attributes.get("path", potential_parent.name)
                    if parent_file_path == parent_path:
                        relationship = Relationship(
                            relationship_id=self._generate_relationship_id(potential_parent.entity_id, entity.entity_id, RelationshipType.HIERARCHICAL),
                            source_entity_id=potential_parent.entity_id,
                            target_entity_id=entity.entity_id,
                            relationship_type=RelationshipType.HIERARCHICAL,
                            strength=1.0,
                            confidence=0.9,
                            evidence=["File system hierarchy"],
                            created_at=datetime.now(),
                            last_seen=datetime.now(),
                            occurrence_count=1,
                            metadata={"hierarchy_type": "file_system"}
                        )
                        relationships.append(relationship)
        
        return relationships
    
    def _analyze_sequence_relationships(self, entities_by_file: Dict[str, List[Entity]], 
                                      access_history: List[Dict[str, Any]]) -> List[Relationship]:
        """Find entities that appear in sequence workflows."""
        relationships = []
        
        # Sort access history by time
        sorted_access = sorted(access_history, key=lambda x: x.get("access_time", datetime.now()))
        
        # Look for sequential patterns
        for i in range(len(sorted_access) - 1):
            current_access = sorted_access[i]
            next_access = sorted_access[i + 1]
            
            current_file = current_access.get("file_path", "")
            next_file = next_access.get("file_path", "")
            
            if current_file != next_file and current_file in entities_by_file and next_file in entities_by_file:
                current_entities = entities_by_file[current_file]
                next_entities = entities_by_file[next_file]
                
                # Check time proximity
                current_time = current_access.get("access_time")
                next_time = next_access.get("access_time")
                
                if isinstance(current_time, str):
                    current_time = datetime.fromisoformat(current_time)
                if isinstance(next_time, str):
                    next_time = datetime.fromisoformat(next_time)
                
                if (next_time - current_time) <= timedelta(hours=1):
                    # Create sequence relationships between file entities
                    current_file_entity = next((e for e in current_entities if e.entity_type == EntityType.FILE), None)
                    next_file_entity = next((e for e in next_entities if e.entity_type == EntityType.FILE), None)
                    
                    if current_file_entity and next_file_entity:
                        relationship = Relationship(
                            relationship_id=self._generate_relationship_id(current_file_entity.entity_id, next_file_entity.entity_id, RelationshipType.SEQUENCE),
                            source_entity_id=current_file_entity.entity_id,
                            target_entity_id=next_file_entity.entity_id,
                            relationship_type=RelationshipType.SEQUENCE,
                            strength=0.8,
                            confidence=0.7,
                            evidence=[f"Sequential access within {(next_time - current_time).total_seconds()/60:.0f} minutes"],
                            created_at=datetime.now(),
                            last_seen=datetime.now(),
                            occurrence_count=1,
                            metadata={
                                "time_gap_minutes": (next_time - current_time).total_seconds() / 60,
                                "session_id": current_access.get("session_id")
                            }
                        )
                        relationships.append(relationship)
        
        return relationships
    
    def _calculate_semantic_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate semantic similarity between entities."""
        if entity1.entity_type != entity2.entity_type:
            return 0.0
        
        if entity1.entity_type == EntityType.CONCEPT:
            # Simple name similarity for concepts
            name1 = entity1.name.lower()
            name2 = entity2.name.lower()
            
            # Check for common word roots or categories
            similar_concepts = {
                "financial": ["finance", "money", "budget", "accounting"],
                "medical": ["health", "healthcare", "medicine", "wellness"],
                "legal": ["law", "legal", "attorney", "court"],
                "education": ["school", "learning", "academic", "study"]
            }
            
            for category, keywords in similar_concepts.items():
                if any(keyword in name1 for keyword in keywords) and any(keyword in name2 for keyword in keywords):
                    return 0.8
        
        return 0.0
    
    def _generate_relationship_id(self, entity1_id: str, entity2_id: str, rel_type: RelationshipType) -> str:
        """Generate unique relationship ID."""
        combined = f"{entity1_id}_{entity2_id}_{rel_type.value}"
        return hashlib.md5(combined.encode()).hexdigest()

class RelationshipGraphEngine:
    """Main engine for building and analyzing relationship graphs."""
    
    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.relationship_analyzer = RelationshipAnalyzer()
        self.entities: Dict[str, Entity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.user_graphs: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"entities": {}, "relationships": {}})
        
        print("🔗 Relationship Mapping Engine initialized")
    
    async def process_file_access(self, user_id: str, file_info: Dict[str, Any], 
                                access_time: datetime, session_id: str):
        """Process file access and update relationship graph."""
        
        # Extract entities from file
        entities = self.entity_extractor.extract_entities(file_info)
        
        # Add entities to user graph
        user_graph = self.user_graphs[user_id]
        for entity in entities:
            if entity.entity_id in user_graph["entities"]:
                # Update existing entity
                existing = user_graph["entities"][entity.entity_id]
                existing.access_count += 1
                existing.last_updated = datetime.now()
            else:
                # Add new entity
                user_graph["entities"][entity.entity_id] = entity
        
        # Update access history for relationship analysis
        if "access_history" not in user_graph:
            user_graph["access_history"] = []
        
        user_graph["access_history"].append({
            "file_path": file_info.get("path", file_info.get("name", "")),
            "access_time": access_time,
            "session_id": session_id,
            "entities": [e.entity_id for e in entities]
        })
        
        # Keep only recent history
        if len(user_graph["access_history"]) > 500:
            user_graph["access_history"] = user_graph["access_history"][-500:]
        
        # Analyze relationships periodically
        if len(user_graph["access_history"]) % 10 == 0:  # Every 10 accesses
            await self._update_relationships(user_id)
    
    async def _update_relationships(self, user_id: str):
        """Update relationships for a user's graph."""
        user_graph = self.user_graphs[user_id]
        
        # Group entities by file for analysis
        entities_by_file = defaultdict(list)
        for access in user_graph.get("access_history", []):
            file_path = access["file_path"]
            for entity_id in access.get("entities", []):
                if entity_id in user_graph["entities"]:
                    entities_by_file[file_path].append(user_graph["entities"][entity_id])
        
        # Analyze relationships
        new_relationships = self.relationship_analyzer.analyze_relationships(
            entities_by_file, user_graph.get("access_history", [])
        )
        
        # Update relationship graph
        for relationship in new_relationships:
            rel_id = relationship.relationship_id
            if rel_id in user_graph["relationships"]:
                # Update existing relationship
                existing = user_graph["relationships"][rel_id]
                existing.occurrence_count += 1
                existing.last_seen = datetime.now()
                # Update strength based on increased occurrences
                existing.strength = min(1.0, existing.strength + 0.1)
            else:
                # Add new relationship
                user_graph["relationships"][rel_id] = relationship
    
    async def get_entity_relationships(self, user_id: str, entity_id: str) -> Dict[str, Any]:
        """Get all relationships for a specific entity."""
        user_graph = self.user_graphs[user_id]
        
        if entity_id not in user_graph["entities"]:
            return {"error": "Entity not found"}
        
        entity = user_graph["entities"][entity_id]
        
        # Find all relationships involving this entity
        related_relationships = []
        for relationship in user_graph["relationships"].values():
            if relationship.source_entity_id == entity_id or relationship.target_entity_id == entity_id:
                related_relationships.append(relationship)
        
        # Get connected entities
        connected_entities = []
        for rel in related_relationships:
            other_entity_id = rel.target_entity_id if rel.source_entity_id == entity_id else rel.source_entity_id
            if other_entity_id in user_graph["entities"]:
                connected_entities.append(user_graph["entities"][other_entity_id])
        
        return {
            "entity": asdict(entity),
            "relationships": [asdict(rel) for rel in related_relationships],
            "connected_entities": [asdict(ent) for ent in connected_entities],
            "relationship_count": len(related_relationships),
            "connection_strength": sum(rel.strength for rel in related_relationships)
        }
    
    async def find_similar_entities(self, user_id: str, entity_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find entities similar to the given entity."""
        user_graph = self.user_graphs[user_id]
        
        if entity_id not in user_graph["entities"]:
            return []
        
        target_entity = user_graph["entities"][entity_id]
        
        # Find similar entities based on relationships
        similar_entities = []
        
        # Get entities connected to the target
        connected_entity_ids = set()
        for relationship in user_graph["relationships"].values():
            if relationship.source_entity_id == entity_id:
                connected_entity_ids.add(relationship.target_entity_id)
            elif relationship.target_entity_id == entity_id:
                connected_entity_ids.add(relationship.source_entity_id)
        
        # Find entities that share connections
        for other_entity_id, other_entity in user_graph["entities"].items():
            if other_entity_id == entity_id or other_entity.entity_type != target_entity.entity_type:
                continue
            
            # Get connections for this entity
            other_connections = set()
            for relationship in user_graph["relationships"].values():
                if relationship.source_entity_id == other_entity_id:
                    other_connections.add(relationship.target_entity_id)
                elif relationship.target_entity_id == other_entity_id:
                    other_connections.add(relationship.source_entity_id)
            
            # Calculate connection overlap (Jaccard similarity)
            if connected_entity_ids and other_connections:
                intersection = len(connected_entity_ids & other_connections)
                union = len(connected_entity_ids | other_connections)
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.1:
                    similar_entities.append({
                        "entity": asdict(other_entity),
                        "similarity": similarity,
                        "shared_connections": intersection
                    })
        
        # Sort by similarity and return top results
        similar_entities.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_entities[:limit]
    
    async def get_graph_insights(self, user_id: str) -> List[RelationshipInsight]:
        """Generate insights from the relationship graph."""
        user_graph = self.user_graphs[user_id]
        insights = []
        
        # Insight 1: Most connected entities
        entity_connections = defaultdict(int)
        for relationship in user_graph["relationships"].values():
            entity_connections[relationship.source_entity_id] += 1
            entity_connections[relationship.target_entity_id] += 1
        
        if entity_connections:
            most_connected_id = max(entity_connections.items(), key=lambda x: x[1])[0]
            most_connected_entity = user_graph["entities"].get(most_connected_id)
            
            if most_connected_entity:
                insight = RelationshipInsight(
                    insight_id=f"most_connected_{user_id}",
                    user_id=user_id,
                    insight_type="centrality",
                    title="Most Connected Entity",
                    description=f"{most_connected_entity.name} ({most_connected_entity.entity_type.value}) has the most connections ({entity_connections[most_connected_id]} relationships)",
                    confidence=0.9,
                    supporting_entities=[most_connected_id],
                    supporting_relationships=[],
                    actionable_suggestions=[
                        f"Consider organizing files related to {most_connected_entity.name}",
                        "This entity might be central to your work patterns"
                    ],
                    created_at=datetime.now()
                )
                insights.append(insight)
        
        # Insight 2: Strong concept clusters
        concept_entities = [e for e in user_graph["entities"].values() if e.entity_type == EntityType.CONCEPT]
        if len(concept_entities) >= 2:
            insight = RelationshipInsight(
                insight_id=f"concept_clusters_{user_id}",
                user_id=user_id,
                insight_type="clustering",
                title="Content Categories",
                description=f"You work with {len(concept_entities)} different content categories: {', '.join([e.name for e in concept_entities])}",
                confidence=0.8,
                supporting_entities=[e.entity_id for e in concept_entities],
                supporting_relationships=[],
                actionable_suggestions=[
                    "Consider organizing files by these content categories",
                    "Create separate workflows for different content types"
                ],
                created_at=datetime.now()
            )
            insights.append(insight)
        
        # Insight 3: Collaboration patterns
        person_entities = [e for e in user_graph["entities"].values() if e.entity_type == EntityType.PERSON]
        if len(person_entities) >= 2:
            insight = RelationshipInsight(
                insight_id=f"collaboration_{user_id}",
                user_id=user_id,
                insight_type="collaboration",
                title="Collaboration Network",
                description=f"You collaborate with {len(person_entities)} people: {', '.join([e.name for e in person_entities[:3]])}{'...' if len(person_entities) > 3 else ''}",
                confidence=0.7,
                supporting_entities=[e.entity_id for e in person_entities],
                supporting_relationships=[],
                actionable_suggestions=[
                    "Consider creating shared folders for collaboration",
                    "Set up notifications for files involving these people"
                ],
                created_at=datetime.now()
            )
            insights.append(insight)
        
        return insights
    
    async def get_graph_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about the relationship graph."""
        user_graph = self.user_graphs[user_id]
        
        entities = user_graph["entities"]
        relationships = user_graph["relationships"]
        
        if not entities:
            return {"message": "No entities in graph"}
        
        # Entity type distribution
        entity_type_counts = Counter([e.entity_type.value for e in entities.values()])
        
        # Relationship type distribution
        relationship_type_counts = Counter([r.relationship_type.value for r in relationships.values()])
        
        # Relationship strength distribution
        strength_counts = Counter()
        for rel in relationships.values():
            if rel.strength >= 0.8:
                strength_counts["very_strong"] += 1
            elif rel.strength >= 0.6:
                strength_counts["strong"] += 1
            elif rel.strength >= 0.3:
                strength_counts["moderate"] += 1
            else:
                strength_counts["weak"] += 1
        
        # Most connected entities
        entity_connections = defaultdict(int)
        for relationship in relationships.values():
            entity_connections[relationship.source_entity_id] += 1
            entity_connections[relationship.target_entity_id] += 1
        
        top_entities = []
        for entity_id, count in sorted(entity_connections.items(), key=lambda x: x[1], reverse=True)[:5]:
            if entity_id in entities:
                entity = entities[entity_id]
                top_entities.append({
                    "name": entity.name,
                    "type": entity.entity_type.value,
                    "connections": count
                })
        
        return {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "entity_type_distribution": dict(entity_type_counts),
            "relationship_type_distribution": dict(relationship_type_counts),
            "relationship_strength_distribution": dict(strength_counts),
            "top_connected_entities": top_entities,
            "graph_density": len(relationships) / (len(entities) * (len(entities) - 1) / 2) if len(entities) > 1 else 0
        }

# CLI interface for testing
async def main():
    """CLI interface for Relationship Mapping Engine testing."""
    engine = RelationshipGraphEngine()
    
    print("🔗 Relationship Mapping Engine Test Suite")
    print("=" * 50)
    
    user_id = "test_user"
    current_time = datetime.now()
    
    # Test 1: Process file accesses with entities
    print("\n1. Processing file accesses with entities...")
    
    mock_files = [
        {
            "name": "project_proposal.docx",
            "path": "/work/projects/project_proposal.docx",
            "content": "Project proposal for John Smith and Sarah Johnson. Meeting scheduled for January 15, 2024 at Microsoft Corporation.",
            "size": 25000,
            "created_at": current_time - timedelta(days=5)
        },
        {
            "name": "client_contract.pdf", 
            "path": "/work/legal/client_contract.pdf",
            "content": "Contract agreement between our company and Apple Inc. Legal review by attorney David Wilson. Due date: 02/01/2024.",
            "size": 150000,
            "created_at": current_time - timedelta(days=3)
        },
        {
            "name": "meeting_notes.txt",
            "path": "/work/meetings/meeting_notes.txt", 
            "content": "Meeting with John Smith and David Wilson about the Apple Inc contract. Project timeline and budget discussed.",
            "size": 5000,
            "created_at": current_time - timedelta(days=1)
        },
        {
            "name": "budget_analysis.xlsx",
            "path": "/finance/budget_analysis.xlsx",
            "content": "Budget analysis for project. Expense tracking and revenue projections. Tax implications reviewed.",
            "size": 75000,
            "created_at": current_time - timedelta(hours=12)
        }
    ]
    
    for i, file_info in enumerate(mock_files):
        session_id = f"session_{i}"
        access_time = current_time - timedelta(hours=i*2)
        await engine.process_file_access(user_id, file_info, access_time, session_id)
    
    print(f"✅ Processed {len(mock_files)} file accesses")
    
    # Test 2: Get graph statistics
    print("\n2. Getting graph statistics...")
    
    stats = await engine.get_graph_statistics(user_id)
    if "message" not in stats:
        print(f"✅ Graph statistics:")
        print(f"   Total entities: {stats['total_entities']}")
        print(f"   Total relationships: {stats['total_relationships']}")
        print(f"   Entity types: {stats['entity_type_distribution']}")
        print(f"   Relationship types: {stats['relationship_type_distribution']}")
        print(f"   Graph density: {stats['graph_density']:.3f}")
    else:
        print(f"ℹ️ {stats['message']}")
    
    # Test 3: Get entity relationships
    print("\n3. Analyzing entity relationships...")
    
    # Get a person entity to analyze
    user_graph = engine.user_graphs[user_id]
    person_entities = [e for e in user_graph["entities"].values() if e.entity_type == EntityType.PERSON]
    
    if person_entities:
        person_entity = person_entities[0]
        relationships = await engine.get_entity_relationships(user_id, person_entity.entity_id)
        
        print(f"✅ Relationships for {person_entity.name}:")
        print(f"   Connected to {len(relationships['connected_entities'])} entities")
        print(f"   {relationships['relationship_count']} total relationships")
        print(f"   Connection strength: {relationships['connection_strength']:.2f}")
        
        # Show some connections
        for conn_entity in relationships['connected_entities'][:3]:
            print(f"   - Connected to: {conn_entity['name']} ({conn_entity['entity_type']})")
    
    # Test 4: Find similar entities
    print("\n4. Finding similar entities...")
    
    if person_entities and len(person_entities) >= 2:
        similar = await engine.find_similar_entities(user_id, person_entities[0].entity_id)
        
        print(f"✅ Entities similar to {person_entities[0].name}:")
        for sim_entity in similar[:3]:
            print(f"   - {sim_entity['entity']['name']}: {sim_entity['similarity']:.2f} similarity")
    
    # Test 5: Generate insights
    print("\n5. Generating relationship insights...")
    
    insights = await engine.get_graph_insights(user_id)
    print(f"✅ Generated {len(insights)} insights:")
    
    for insight in insights[:3]:
        print(f"   - {insight.title}")
        print(f"     {insight.description}")
        print(f"     Confidence: {insight.confidence:.2f}")
        if insight.actionable_suggestions:
            print(f"     Suggestion: {insight.actionable_suggestions[0]}")
    
    print("\n🎉 Relationship Mapping Engine tests completed!")

if __name__ == "__main__":
    asyncio.run(main())