"""
Character relationship tracking system
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional
from ..models.base import Relationship, RelationshipType


class RelationshipManager:
    """Manages character relationships with NPCs, PCs, and organizations"""
    
    def __init__(self):
        self.relationships: Dict[str, Relationship] = {}
        self.character_relationships: Dict[str, List[str]] = {}  # character_id -> relationship_ids
        self.target_index: Dict[str, List[str]] = {}  # target_name -> relationship_ids
        self.relationship_templates: Dict[str, Dict[str, Any]] = {}
        
        self._initialize_relationship_templates()
    
    def create_relationship(
        self, 
        character_id: str,
        target_name: str,
        target_type: str = "npc",
        relationship_type: RelationshipType = RelationshipType.NEUTRAL,
        trust_level: int = 5,
        influence: int = 5,
        notes: str = "",
        first_met: Optional[date] = None
    ) -> Relationship:
        """Create a new relationship"""
        
        relationship = Relationship(
            character_id=character_id,
            target_name=target_name,
            target_type=target_type,
            relationship_type=relationship_type,
            trust_level=max(1, min(10, trust_level)),  # Clamp to 1-10
            influence=max(1, min(10, influence)),  # Clamp to 1-10
            notes=notes,
            first_met=first_met or date.today()
        )
        
        # Store relationship
        self.relationships[relationship.id] = relationship
        
        # Index by character
        if character_id not in self.character_relationships:
            self.character_relationships[character_id] = []
        self.character_relationships[character_id].append(relationship.id)
        
        # Index by target
        target_key = target_name.lower()
        if target_key not in self.target_index:
            self.target_index[target_key] = []
        self.target_index[target_key].append(relationship.id)
        
        return relationship
    
    def update_relationship(
        self, 
        relationship_id: str,
        relationship_type: Optional[RelationshipType] = None,
        trust_level: Optional[int] = None,
        influence: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Optional[Relationship]:
        """Update an existing relationship"""
        
        if relationship_id not in self.relationships:
            return None
        
        relationship = self.relationships[relationship_id]
        
        if relationship_type is not None:
            relationship.relationship_type = relationship_type
        
        if trust_level is not None:
            relationship.trust_level = max(1, min(10, trust_level))
        
        if influence is not None:
            relationship.influence = max(1, min(10, influence))
        
        if notes is not None:
            relationship.notes = notes
        
        relationship.updated_at = datetime.utcnow()
        relationship.last_interaction = date.today()
        
        return relationship
    
    def add_interaction(
        self, 
        relationship_id: str,
        interaction_type: str,
        description: str,
        outcome: str = "",
        trust_change: int = 0,
        influence_change: int = 0,
        interaction_date: Optional[date] = None
    ) -> bool:
        """Add an interaction to a relationship"""
        
        if relationship_id not in self.relationships:
            return False
        
        relationship = self.relationships[relationship_id]
        
        interaction = {
            "type": interaction_type,
            "description": description,
            "outcome": outcome,
            "trust_change": trust_change,
            "influence_change": influence_change,
            "date": interaction_date or date.today(),
            "recorded_at": datetime.utcnow()
        }
        
        relationship.interaction_history.append(interaction)
        
        # Apply changes
        if trust_change != 0:
            relationship.trust_level = max(1, min(10, relationship.trust_level + trust_change))
        
        if influence_change != 0:
            relationship.influence = max(1, min(10, relationship.influence + influence_change))
        
        relationship.last_interaction = interaction_date or date.today()
        relationship.updated_at = datetime.utcnow()
        
        return True
    
    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """Get a relationship by ID"""
        return self.relationships.get(relationship_id)
    
    def get_character_relationships(
        self, 
        character_id: str,
        target_type: Optional[str] = None,
        relationship_type: Optional[RelationshipType] = None
    ) -> List[Relationship]:
        """Get all relationships for a character with optional filters"""
        
        if character_id not in self.character_relationships:
            return []
        
        relationship_ids = self.character_relationships[character_id]
        relationships = [self.relationships[rid] for rid in relationship_ids if rid in self.relationships]
        
        # Apply filters
        if target_type is not None:
            relationships = [r for r in relationships if r.target_type == target_type]
        
        if relationship_type is not None:
            relationships = [r for r in relationships if r.relationship_type == relationship_type]
        
        # Sort by relationship strength (trust + influence), then by last interaction
        def sort_key(rel):
            strength = rel.trust_level + rel.influence
            last_interaction = rel.last_interaction or date.min
            return (-strength, -last_interaction.toordinal())
        
        return sorted(relationships, key=sort_key)
    
    def find_relationship_by_target(
        self, 
        character_id: str, 
        target_name: str
    ) -> Optional[Relationship]:
        """Find a relationship by target name"""
        
        target_key = target_name.lower()
        if target_key not in self.target_index:
            return None
        
        relationship_ids = self.target_index[target_key]
        
        for rid in relationship_ids:
            relationship = self.relationships.get(rid)
            if relationship and relationship.character_id == character_id:
                return relationship
        
        return None
    
    def search_relationships(
        self, 
        character_id: str,
        query: str,
        include_interaction_history: bool = False
    ) -> List[Relationship]:
        """Search relationships by name, notes, or interaction history"""
        
        relationships = self.get_character_relationships(character_id)
        results = []
        query_lower = query.lower()
        
        for relationship in relationships:
            # Search in target name and notes
            if (query_lower in relationship.target_name.lower() or
                query_lower in relationship.notes.lower()):
                results.append(relationship)
                continue
            
            # Search in interaction history if requested
            if include_interaction_history:
                for interaction in relationship.interaction_history:
                    if (query_lower in interaction["description"].lower() or
                        query_lower in interaction["outcome"].lower()):
                        results.append(relationship)
                        break
        
        return results
    
    def get_relationship_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get relationship statistics for a character"""
        
        relationships = self.get_character_relationships(character_id)
        
        if not relationships:
            return {
                "total_relationships": 0,
                "by_type": {},
                "by_target_type": {},
                "average_trust": 0.0,
                "average_influence": 0.0,
                "strongest_relationships": [],
                "recent_interactions": 0
            }
        
        # Count by relationship type
        type_counts = {}
        for rel in relationships:
            rel_type = rel.relationship_type.value
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
        
        # Count by target type
        target_type_counts = {}
        for rel in relationships:
            target_type = rel.target_type
            target_type_counts[target_type] = target_type_counts.get(target_type, 0) + 1
        
        # Calculate averages
        total_trust = sum(rel.trust_level for rel in relationships)
        total_influence = sum(rel.influence for rel in relationships)
        avg_trust = total_trust / len(relationships)
        avg_influence = total_influence / len(relationships)
        
        # Find strongest relationships (by trust + influence)
        strongest = sorted(
            relationships,
            key=lambda r: r.trust_level + r.influence,
            reverse=True
        )[:5]
        
        # Count recent interactions (last 30 days)
        thirty_days_ago = date.today() - datetime.timedelta(days=30)
        recent_interactions = 0
        
        for rel in relationships:
            if rel.last_interaction and rel.last_interaction >= thirty_days_ago:
                recent_interactions += 1
        
        return {
            "total_relationships": len(relationships),
            "by_type": type_counts,
            "by_target_type": target_type_counts,
            "average_trust": avg_trust,
            "average_influence": avg_influence,
            "strongest_relationships": [
                {"name": r.target_name, "strength": r.trust_level + r.influence}
                for r in strongest
            ],
            "recent_interactions": recent_interactions
        }
    
    def get_faction_standings(self, character_id: str) -> Dict[str, Dict[str, Any]]:
        """Get character's standing with different factions/organizations"""
        
        org_relationships = self.get_character_relationships(
            character_id, 
            target_type="organization"
        )
        
        standings = {}
        
        for rel in org_relationships:
            standings[rel.target_name] = {
                "relationship_type": rel.relationship_type.value,
                "trust_level": rel.trust_level,
                "influence": rel.influence,
                "last_interaction": rel.last_interaction,
                "interaction_count": len(rel.interaction_history),
                "standing_score": self._calculate_standing_score(rel)
            }
        
        return standings
    
    def suggest_relationship_actions(
        self, 
        character_id: str,
        relationship_id: str
    ) -> List[Dict[str, Any]]:
        """Suggest actions to improve or maintain a relationship"""
        
        relationship = self.get_relationship(relationship_id)
        if not relationship or relationship.character_id != character_id:
            return []
        
        suggestions = []
        
        # Based on relationship type and current levels
        if relationship.trust_level < 5:
            suggestions.append({
                "action": "Build Trust",
                "description": "Engage in trust-building activities or conversations",
                "expected_outcome": "Increase trust level",
                "difficulty": "medium"
            })
        
        if relationship.influence < 5:
            suggestions.append({
                "action": "Increase Influence",
                "description": "Perform favors or demonstrate value to this contact",
                "expected_outcome": "Increase influence level",
                "difficulty": "medium"
            })
        
        # Time-based suggestions
        if relationship.last_interaction:
            days_since = (date.today() - relationship.last_interaction).days
            
            if days_since > 30:
                suggestions.append({
                    "action": "Reconnect",
                    "description": "It's been a while - reach out to maintain the relationship",
                    "expected_outcome": "Prevent relationship decay",
                    "difficulty": "easy"
                })
        
        # Type-specific suggestions
        if relationship.relationship_type == RelationshipType.RIVAL:
            suggestions.append({
                "action": "Competitive Challenge",
                "description": "Engage in a friendly competition to improve mutual respect",
                "expected_outcome": "Could improve relationship or create interesting conflict",
                "difficulty": "hard"
            })
        
        elif relationship.relationship_type == RelationshipType.ALLY:
            suggestions.append({
                "action": "Mutual Support",
                "description": "Offer assistance with their goals or problems",
                "expected_outcome": "Strengthen alliance",
                "difficulty": "medium"
            })
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def track_relationship_changes(
        self, 
        character_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Track relationship changes over time"""
        
        relationships = self.get_character_relationships(character_id)
        changes = []
        
        cutoff_date = date.today() - datetime.timedelta(days=days)
        
        for rel in relationships:
            recent_interactions = [
                interaction for interaction in rel.interaction_history
                if interaction["date"] >= cutoff_date
            ]
            
            if recent_interactions:
                trust_change = sum(i["trust_change"] for i in recent_interactions)
                influence_change = sum(i["influence_change"] for i in recent_interactions)
                
                if trust_change != 0 or influence_change != 0:
                    changes.append({
                        "target_name": rel.target_name,
                        "trust_change": trust_change,
                        "influence_change": influence_change,
                        "interaction_count": len(recent_interactions),
                        "net_change": trust_change + influence_change
                    })
        
        # Sort by net change (most positive first)
        return sorted(changes, key=lambda x: x["net_change"], reverse=True)
    
    def create_relationship_network(self, character_id: str) -> Dict[str, Any]:
        """Create a network visualization of relationships"""
        
        relationships = self.get_character_relationships(character_id)
        
        nodes = [{"id": character_id, "type": "character", "name": "Player Character"}]
        edges = []
        
        for rel in relationships:
            # Add target as node
            nodes.append({
                "id": rel.target_name,
                "type": rel.target_type,
                "name": rel.target_name
            })
            
            # Add relationship as edge
            edges.append({
                "source": character_id,
                "target": rel.target_name,
                "relationship_type": rel.relationship_type.value,
                "strength": rel.trust_level + rel.influence,
                "trust": rel.trust_level,
                "influence": rel.influence
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "character_id": character_id,
            "generated_at": datetime.utcnow()
        }
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship"""
        
        if relationship_id not in self.relationships:
            return False
        
        relationship = self.relationships[relationship_id]
        
        # Remove from character index
        character_id = relationship.character_id
        if character_id in self.character_relationships:
            self.character_relationships[character_id].remove(relationship_id)
        
        # Remove from target index
        target_key = relationship.target_name.lower()
        if target_key in self.target_index:
            self.target_index[target_key].remove(relationship_id)
            if not self.target_index[target_key]:
                del self.target_index[target_key]
        
        # Delete relationship
        del self.relationships[relationship_id]
        return True
    
    def _calculate_standing_score(self, relationship: Relationship) -> int:
        """Calculate overall standing score (0-100)"""
        
        base_score = (relationship.trust_level + relationship.influence) * 5  # 0-100 range
        
        # Modify based on relationship type
        type_modifiers = {
            RelationshipType.ENEMY: -20,
            RelationshipType.RIVAL: -10,
            RelationshipType.NEUTRAL: 0,
            RelationshipType.ALLY: 10,
            RelationshipType.FRIEND: 15,
            RelationshipType.ROMANTIC: 20,
            RelationshipType.FAMILY: 15,
            RelationshipType.MENTOR: 10,
            RelationshipType.STUDENT: 5
        }
        
        modifier = type_modifiers.get(relationship.relationship_type, 0)
        score = base_score + modifier
        
        return max(0, min(100, score))  # Clamp to 0-100
    
    def _initialize_relationship_templates(self):
        """Initialize relationship templates for quick creation"""
        
        self.relationship_templates = {
            "mentor": {
                "relationship_type": RelationshipType.MENTOR,
                "trust_level": 7,
                "influence": 3,
                "notes": "Provides guidance and wisdom"
            },
            "rival": {
                "relationship_type": RelationshipType.RIVAL,
                "trust_level": 4,
                "influence": 4,
                "notes": "Competitive relationship, pushes character to improve"
            },
            "ally": {
                "relationship_type": RelationshipType.ALLY,
                "trust_level": 6,
                "influence": 5,
                "notes": "Reliable partner in adventures"
            },
            "informant": {
                "relationship_type": RelationshipType.NEUTRAL,
                "trust_level": 5,
                "influence": 7,
                "notes": "Provides information in exchange for favors or payment"
            },
            "love_interest": {
                "relationship_type": RelationshipType.ROMANTIC,
                "trust_level": 8,
                "influence": 6,
                "notes": "Romantic relationship with emotional stakes"
            }
        }