"""
Main player interface service - orchestrates all player management functionality
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import uvicorn
from datetime import datetime, date

from .models.base import (
    Character, JournalEntry, InventoryItem, Quest, Party, Relationship,
    DowntimeActivity, CraftingProject, LevelPlan, RestRecord, 
    QuestStatus, Priority, RelationshipType, ActivityType, RestType
)
from .managers.journal_manager import JournalManager
from .managers.spell_reference_manager import SpellReferenceManager
from .managers.inventory_manager import InventoryManager
from .managers.quest_tracker import QuestTracker
from .managers.party_manager import PartyManager
from .managers.relationship_manager import RelationshipManager


class PlayerInterfaceService:
    """Main service orchestrating all player interface functionality"""
    
    def __init__(self):
        # Initialize managers
        self.journal_manager = JournalManager()
        self.spell_manager = SpellReferenceManager()
        self.inventory_manager = InventoryManager()
        self.quest_tracker = QuestTracker()
        self.party_manager = PartyManager()
        self.relationship_manager = RelationshipManager()
        
        # Character storage (in real implementation, this would be a database)
        self.characters: Dict[str, Character] = {}
    
    # Character Management
    def create_character(self, character_data: Dict[str, Any]) -> Character:
        """Create a new character"""
        
        character = Character(**character_data)
        self.characters[character.id] = character
        return character
    
    def get_character(self, character_id: str) -> Optional[Character]:
        """Get character by ID"""
        return self.characters.get(character_id)
    
    def update_character(self, character_id: str, updates: Dict[str, Any]) -> Optional[Character]:
        """Update character data"""
        
        character = self.get_character(character_id)
        if not character:
            return None
        
        for field, value in updates.items():
            if hasattr(character, field):
                setattr(character, field, value)
        
        character.last_updated = datetime.utcnow()
        return character
    
    # Journal Management
    def create_journal_entry(
        self, 
        character_id: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        is_private: bool = True,
        session_date: Optional[date] = None
    ) -> JournalEntry:
        """Create a journal entry"""
        
        return self.journal_manager.create_entry(
            character_id=character_id,
            title=title,
            content=content,
            tags=tags,
            is_private=is_private,
            session_date=session_date
        )
    
    def get_character_journal(self, character_id: str) -> List[JournalEntry]:
        """Get character's journal entries"""
        return self.journal_manager.get_character_entries(character_id)
    
    def search_journal(self, character_id: str, query: str) -> List[JournalEntry]:
        """Search journal entries"""
        return self.journal_manager.search_entries(character_id, query)
    
    # Spell and Ability Management
    def add_character_spell(self, character_id: str, spell_name: str) -> bool:
        """Add spell to character"""
        return self.spell_manager.add_character_spell(character_id, spell_name)
    
    def get_character_spells(self, character_id: str) -> List[Dict[str, Any]]:
        """Get character's spells"""
        return self.spell_manager.get_character_spells(character_id)
    
    def get_spell_quick_reference(self, character_id: str) -> Dict[str, Any]:
        """Get spell quick reference card"""
        return self.spell_manager.get_quick_reference_card(character_id)
    
    def track_spell_usage(
        self, 
        character_id: str,
        spell_name: str,
        spell_level: int,
        effectiveness: int = 5
    ) -> Any:
        """Track spell usage"""
        return self.spell_manager.track_spell_usage(
            character_id, spell_name, spell_level, effectiveness=effectiveness
        )
    
    # Inventory Management
    def add_inventory_item(
        self, 
        character_id: str,
        name: str,
        quantity: int = 1,
        weight: float = 0.0,
        value: Optional[Dict[str, float]] = None
    ) -> InventoryItem:
        """Add item to inventory"""
        return self.inventory_manager.add_item(
            character_id=character_id,
            name=name,
            quantity=quantity,
            weight=weight,
            value=value or {}
        )
    
    def get_character_inventory(self, character_id: str) -> List[InventoryItem]:
        """Get character's inventory"""
        return self.inventory_manager.get_inventory(character_id)
    
    def calculate_encumbrance(self, character_id: str) -> Dict[str, Any]:
        """Calculate character encumbrance"""
        character = self.get_character(character_id)
        if not character:
            return {}
        
        return self.inventory_manager.calculate_encumbrance(character)
    
    def organize_inventory(self, character_id: str) -> Dict[str, List[InventoryItem]]:
        """Organize inventory by type"""
        return self.inventory_manager.organize_inventory(character_id, "type")
    
    # Quest and Goal Management
    def create_quest(
        self, 
        character_id: str,
        title: str,
        description: str,
        category: str = "personal",
        priority: str = "medium"
    ) -> Quest:
        """Create a quest"""
        return self.quest_tracker.create_quest(
            character_id=character_id,
            title=title,
            description=description,
            category=category,
            priority=Priority(priority)
        )
    
    def get_character_quests(self, character_id: str) -> List[Quest]:
        """Get character's quests"""
        return self.quest_tracker.get_character_quests(character_id)
    
    def get_active_quests(self, character_id: str) -> List[Quest]:
        """Get active quests"""
        return self.quest_tracker.get_active_quests(character_id)
    
    def complete_quest_milestone(self, quest_id: str, milestone_index: int) -> bool:
        """Complete a quest milestone"""
        return self.quest_tracker.complete_milestone(quest_id, milestone_index)
    
    # Party Management
    def create_party(
        self, 
        name: str,
        campaign_id: str,
        leader_id: str,
        description: str = ""
    ) -> Party:
        """Create a party"""
        return self.party_manager.create_party(name, campaign_id, leader_id, description)
    
    def invite_to_party(
        self, 
        party_id: str,
        character_id: str,
        inviter_id: str
    ) -> bool:
        """Invite character to party"""
        return self.party_manager.invite_character(party_id, character_id, inviter_id)
    
    def get_character_party(self, character_id: str) -> Optional[Party]:
        """Get character's party"""
        return self.party_manager.get_character_party(character_id)
    
    def calculate_party_synergy(self, party_id: str) -> Dict[str, Any]:
        """Calculate party synergy"""
        # Get characters in party
        party = self.party_manager.get_party(party_id)
        if not party:
            return {}
        
        characters = [self.get_character(cid) for cid in party.member_ids if self.get_character(cid)]
        return self.party_manager.calculate_party_synergy(party_id, characters)
    
    # Relationship Management
    def create_relationship(
        self, 
        character_id: str,
        target_name: str,
        target_type: str = "npc",
        relationship_type: str = "neutral"
    ) -> Relationship:
        """Create a relationship"""
        return self.relationship_manager.create_relationship(
            character_id=character_id,
            target_name=target_name,
            target_type=target_type,
            relationship_type=RelationshipType(relationship_type)
        )
    
    def get_character_relationships(self, character_id: str) -> List[Relationship]:
        """Get character relationships"""
        return self.relationship_manager.get_character_relationships(character_id)
    
    def add_relationship_interaction(
        self, 
        relationship_id: str,
        interaction_type: str,
        description: str,
        trust_change: int = 0,
        influence_change: int = 0
    ) -> bool:
        """Add relationship interaction"""
        return self.relationship_manager.add_interaction(
            relationship_id=relationship_id,
            interaction_type=interaction_type,
            description=description,
            trust_change=trust_change,
            influence_change=influence_change
        )
    
    # Dashboard and Analytics
    def get_character_dashboard(self, character_id: str) -> Dict[str, Any]:
        """Get comprehensive character dashboard"""
        
        character = self.get_character(character_id)
        if not character:
            return {}
        
        # Gather data from all managers
        journal_stats = self.journal_manager.get_character_statistics(character_id)
        quest_stats = self.quest_tracker.get_quest_statistics(character_id)
        inventory_stats = self.inventory_manager.get_inventory_statistics(character_id)
        relationship_stats = self.relationship_manager.get_relationship_statistics(character_id)
        spell_stats = self.spell_manager.get_spell_usage_stats(character_id)
        
        # Recent activity
        recent_journal = self.journal_manager.get_character_entries(character_id, limit=3)
        active_quests = self.quest_tracker.get_active_quests(character_id)
        upcoming_deadlines = self.quest_tracker.get_upcoming_deadlines(character_id)
        
        # Encumbrance status
        encumbrance = self.calculate_encumbrance(character_id)
        
        return {
            "character": {
                "id": character.id,
                "name": character.name,
                "level": character.level,
                "character_class": character.character_class,
                "race": character.race
            },
            "statistics": {
                "journal": journal_stats,
                "quests": quest_stats,
                "inventory": inventory_stats,
                "relationships": relationship_stats,
                "spells": spell_stats
            },
            "recent_activity": {
                "journal_entries": [e.dict() for e in recent_journal],
                "active_quests": len(active_quests),
                "upcoming_deadlines": len(upcoming_deadlines)
            },
            "status": {
                "encumbrance": encumbrance.get("encumbrance_level", "normal"),
                "health_percentage": (character.hit_points.get("current", 0) / 
                                    character.hit_points.get("max", 1)) * 100 if character.hit_points else 100
            },
            "generated_at": datetime.utcnow()
        }
    
    def get_session_preparation(self, character_id: str) -> Dict[str, Any]:
        """Get session preparation information"""
        
        character = self.get_character(character_id)
        if not character:
            return {}
        
        # Active quests
        active_quests = self.quest_tracker.get_active_quests(character_id)
        
        # Spell preparation suggestions
        spell_suggestions = self.spell_manager.suggest_spell_preparation(character_id)
        
        # Quick reference
        spell_reference = self.spell_manager.get_quick_reference_card(character_id)
        
        # Important relationships
        relationships = self.relationship_manager.get_character_relationships(character_id)[:10]
        
        # Inventory quick access
        important_items = self.inventory_manager.get_equipped_items(character_id)
        magical_items = self.inventory_manager.get_magical_items(character_id)
        
        return {
            "character_summary": {
                "name": character.name,
                "level": character.level,
                "class": character.character_class,
                "current_hp": character.hit_points.get("current", 0),
                "max_hp": character.hit_points.get("max", 0),
                "ac": character.armor_class
            },
            "active_quests": [
                {
                    "title": q.title,
                    "progress": q.progress,
                    "priority": q.priority.value
                }
                for q in active_quests[:5]
            ],
            "spell_preparation": spell_suggestions,
            "spell_slots": spell_reference.get("spell_slots", {}),
            "key_relationships": [
                {
                    "name": r.target_name,
                    "type": r.relationship_type.value,
                    "trust": r.trust_level
                }
                for r in relationships[:5]
            ],
            "equipped_items": [item.name for item in important_items],
            "magical_items": [item.name for item in magical_items],
            "prepared_at": datetime.utcnow()
        }


# FastAPI app setup
app = FastAPI(
    title="Player Interface API",
    description="Comprehensive player interface for D&D and other tabletop RPGs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize service
player_service = PlayerInterfaceService()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Character endpoints
@app.post("/characters")
async def create_character(character_data: Dict[str, Any]):
    """Create a new character"""
    try:
        character = player_service.create_character(character_data)
        return character
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    """Get character details"""
    character = player_service.get_character(character_id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@app.get("/characters/{character_id}/dashboard")
async def get_dashboard(character_id: str):
    """Get character dashboard"""
    dashboard = player_service.get_character_dashboard(character_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Character not found")
    return dashboard


@app.get("/characters/{character_id}/session-prep")
async def get_session_prep(character_id: str):
    """Get session preparation info"""
    prep_info = player_service.get_session_preparation(character_id)
    if not prep_info:
        raise HTTPException(status_code=404, detail="Character not found")
    return prep_info


# Journal endpoints
@app.post("/characters/{character_id}/journal")
async def create_journal_entry(
    character_id: str,
    title: str,
    content: str,
    tags: Optional[List[str]] = None,
    is_private: bool = True
):
    """Create journal entry"""
    entry = player_service.create_journal_entry(
        character_id, title, content, tags, is_private
    )
    return entry


@app.get("/characters/{character_id}/journal")
async def get_journal(character_id: str):
    """Get character journal"""
    return player_service.get_character_journal(character_id)


# Inventory endpoints
@app.post("/characters/{character_id}/inventory")
async def add_item(
    character_id: str,
    name: str,
    quantity: int = 1,
    weight: float = 0.0,
    value: Optional[Dict[str, float]] = None
):
    """Add item to inventory"""
    item = player_service.add_inventory_item(character_id, name, quantity, weight, value)
    return item


@app.get("/characters/{character_id}/inventory")
async def get_inventory(character_id: str):
    """Get character inventory"""
    return player_service.get_character_inventory(character_id)


@app.get("/characters/{character_id}/encumbrance")
async def get_encumbrance(character_id: str):
    """Get encumbrance status"""
    return player_service.calculate_encumbrance(character_id)


# Quest endpoints
@app.post("/characters/{character_id}/quests")
async def create_quest(
    character_id: str,
    title: str,
    description: str,
    category: str = "personal",
    priority: str = "medium"
):
    """Create a quest"""
    quest = player_service.create_quest(character_id, title, description, category, priority)
    return quest


@app.get("/characters/{character_id}/quests")
async def get_quests(character_id: str):
    """Get character quests"""
    return player_service.get_character_quests(character_id)


@app.get("/characters/{character_id}/quests/active")
async def get_active_quests(character_id: str):
    """Get active quests"""
    return player_service.get_active_quests(character_id)


# Spell endpoints
@app.post("/characters/{character_id}/spells")
async def add_spell(character_id: str, spell_name: str):
    """Add spell to character"""
    success = player_service.add_character_spell(character_id, spell_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add spell")
    return {"success": True}


@app.get("/characters/{character_id}/spells")
async def get_spells(character_id: str):
    """Get character spells"""
    return player_service.get_character_spells(character_id)


@app.get("/characters/{character_id}/spells/quick-reference")
async def get_spell_reference(character_id: str):
    """Get spell quick reference"""
    return player_service.get_spell_quick_reference(character_id)


# Party endpoints
@app.post("/parties")
async def create_party(
    name: str,
    campaign_id: str,
    leader_id: str,
    description: str = ""
):
    """Create a party"""
    party = player_service.create_party(name, campaign_id, leader_id, description)
    return party


@app.get("/characters/{character_id}/party")
async def get_character_party(character_id: str):
    """Get character's party"""
    party = player_service.get_character_party(character_id)
    if not party:
        raise HTTPException(status_code=404, detail="Character not in a party")
    return party


# Relationship endpoints
@app.post("/characters/{character_id}/relationships")
async def create_relationship(
    character_id: str,
    target_name: str,
    target_type: str = "npc",
    relationship_type: str = "neutral"
):
    """Create a relationship"""
    relationship = player_service.create_relationship(
        character_id, target_name, target_type, relationship_type
    )
    return relationship


@app.get("/characters/{character_id}/relationships")
async def get_relationships(character_id: str):
    """Get character relationships"""
    return player_service.get_character_relationships(character_id)


if __name__ == "__main__":
    uvicorn.run(
        "main_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )