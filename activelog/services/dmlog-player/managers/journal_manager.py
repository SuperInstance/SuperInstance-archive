"""
Character journal manager for private notes and session records
"""

from datetime import datetime, date
from typing import Dict, List, Any, Optional
from ..models.base import JournalEntry, Character


class JournalManager:
    """Manages character journals and private notes"""
    
    def __init__(self):
        self.entries: Dict[str, JournalEntry] = {}
        self.character_entries: Dict[str, List[str]] = {}  # character_id -> entry_ids
        self.tag_index: Dict[str, List[str]] = {}  # tag -> entry_ids
    
    def create_entry(
        self, 
        character_id: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        is_private: bool = True,
        session_date: Optional[date] = None,
        in_game_date: Optional[str] = None
    ) -> JournalEntry:
        """Create a new journal entry"""
        
        entry = JournalEntry(
            character_id=character_id,
            title=title,
            content=content,
            tags=tags or [],
            is_private=is_private,
            session_date=session_date,
            in_game_date=in_game_date
        )
        
        # Store entry
        self.entries[entry.id] = entry
        
        # Index by character
        if character_id not in self.character_entries:
            self.character_entries[character_id] = []
        self.character_entries[character_id].append(entry.id)
        
        # Index by tags
        for tag in entry.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = []
            self.tag_index[tag].append(entry.id)
        
        return entry
    
    def update_entry(
        self, 
        entry_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_private: Optional[bool] = None,
        session_date: Optional[date] = None,
        in_game_date: Optional[str] = None
    ) -> Optional[JournalEntry]:
        """Update an existing journal entry"""
        
        if entry_id not in self.entries:
            return None
        
        entry = self.entries[entry_id]
        
        # Update tag index if tags changed
        if tags is not None:
            # Remove from old tags
            for old_tag in entry.tags:
                if old_tag in self.tag_index:
                    self.tag_index[old_tag].remove(entry_id)
                    if not self.tag_index[old_tag]:
                        del self.tag_index[old_tag]
            
            # Add to new tags
            for new_tag in tags:
                if new_tag not in self.tag_index:
                    self.tag_index[new_tag] = []
                self.tag_index[new_tag].append(entry_id)
            
            entry.tags = tags
        
        # Update other fields
        if title is not None:
            entry.title = title
        if content is not None:
            entry.content = content
        if is_private is not None:
            entry.is_private = is_private
        if session_date is not None:
            entry.session_date = session_date
        if in_game_date is not None:
            entry.in_game_date = in_game_date
        
        entry.updated_at = datetime.utcnow()
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a journal entry by ID"""
        return self.entries.get(entry_id)
    
    def get_character_entries(
        self, 
        character_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        private_only: bool = False,
        public_only: bool = False
    ) -> List[JournalEntry]:
        """Get all journal entries for a character"""
        
        if character_id not in self.character_entries:
            return []
        
        entry_ids = self.character_entries[character_id]
        entries = [self.entries[eid] for eid in entry_ids if eid in self.entries]
        
        # Filter by privacy
        if private_only:
            entries = [e for e in entries if e.is_private]
        elif public_only:
            entries = [e for e in entries if not e.is_private]
        
        # Sort by creation date (newest first)
        entries.sort(key=lambda e: e.created_at, reverse=True)
        
        # Apply pagination
        if offset > 0:
            entries = entries[offset:]
        if limit is not None:
            entries = entries[:limit]
        
        return entries
    
    def search_entries(
        self, 
        character_id: str,
        query: str,
        tags: Optional[List[str]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        private_only: bool = False
    ) -> List[JournalEntry]:
        """Search journal entries"""
        
        entries = self.get_character_entries(character_id, private_only=private_only)
        results = []
        
        query_lower = query.lower() if query else ""
        
        for entry in entries:
            # Text search
            if query and query_lower not in entry.title.lower() and query_lower not in entry.content.lower():
                continue
            
            # Tag filter
            if tags and not any(tag in entry.tags for tag in tags):
                continue
            
            # Date filter
            if date_from and entry.session_date and entry.session_date < date_from:
                continue
            if date_to and entry.session_date and entry.session_date > date_to:
                continue
            
            results.append(entry)
        
        return results
    
    def get_entries_by_tag(self, tag: str, character_id: Optional[str] = None) -> List[JournalEntry]:
        """Get all entries with a specific tag"""
        
        if tag not in self.tag_index:
            return []
        
        entry_ids = self.tag_index[tag]
        entries = [self.entries[eid] for eid in entry_ids if eid in self.entries]
        
        if character_id:
            entries = [e for e in entries if e.character_id == character_id]
        
        return sorted(entries, key=lambda e: e.created_at, reverse=True)
    
    def get_session_entries(
        self, 
        character_id: str, 
        session_date: date
    ) -> List[JournalEntry]:
        """Get all entries for a specific session date"""
        
        entries = self.get_character_entries(character_id)
        return [e for e in entries if e.session_date == session_date]
    
    def delete_entry(self, entry_id: str) -> bool:
        """Delete a journal entry"""
        
        if entry_id not in self.entries:
            return False
        
        entry = self.entries[entry_id]
        
        # Remove from character index
        if entry.character_id in self.character_entries:
            self.character_entries[entry.character_id].remove(entry_id)
        
        # Remove from tag index
        for tag in entry.tags:
            if tag in self.tag_index:
                self.tag_index[tag].remove(entry_id)
                if not self.tag_index[tag]:
                    del self.tag_index[tag]
        
        # Delete entry
        del self.entries[entry_id]
        return True
    
    def get_character_statistics(self, character_id: str) -> Dict[str, Any]:
        """Get journal statistics for a character"""
        
        entries = self.get_character_entries(character_id)
        
        if not entries:
            return {
                "total_entries": 0,
                "private_entries": 0,
                "public_entries": 0,
                "total_words": 0,
                "most_used_tags": [],
                "first_entry": None,
                "last_entry": None
            }
        
        private_count = sum(1 for e in entries if e.is_private)
        public_count = len(entries) - private_count
        total_words = sum(len(e.content.split()) for e in entries)
        
        # Count tag usage
        tag_counts = {}
        for entry in entries:
            for tag in entry.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        most_used_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Sort for first/last
        sorted_entries = sorted(entries, key=lambda e: e.created_at)
        
        return {
            "total_entries": len(entries),
            "private_entries": private_count,
            "public_entries": public_count,
            "total_words": total_words,
            "most_used_tags": most_used_tags,
            "first_entry": sorted_entries[0].created_at if sorted_entries else None,
            "last_entry": sorted_entries[-1].created_at if sorted_entries else None
        }
    
    def create_session_summary(
        self, 
        character_id: str,
        session_date: date,
        title: str = "",
        highlights: Optional[List[str]] = None,
        npcs_met: Optional[List[str]] = None,
        locations_visited: Optional[List[str]] = None,
        loot_gained: Optional[List[str]] = None,
        character_thoughts: str = ""
    ) -> JournalEntry:
        """Create a structured session summary entry"""
        
        if not title:
            title = f"Session Summary - {session_date.strftime('%Y-%m-%d')}"
        
        # Build structured content
        content_parts = []
        
        if highlights:
            content_parts.append("## Highlights")
            for highlight in highlights:
                content_parts.append(f"- {highlight}")
            content_parts.append("")
        
        if npcs_met:
            content_parts.append("## NPCs Encountered")
            for npc in npcs_met:
                content_parts.append(f"- {npc}")
            content_parts.append("")
        
        if locations_visited:
            content_parts.append("## Locations Visited")
            for location in locations_visited:
                content_parts.append(f"- {location}")
            content_parts.append("")
        
        if loot_gained:
            content_parts.append("## Loot and Rewards")
            for item in loot_gained:
                content_parts.append(f"- {item}")
            content_parts.append("")
        
        if character_thoughts:
            content_parts.append("## Character Thoughts")
            content_parts.append(character_thoughts)
        
        content = "\n".join(content_parts)
        
        return self.create_entry(
            character_id=character_id,
            title=title,
            content=content,
            tags=["session_summary", "recap"],
            is_private=True,
            session_date=session_date
        )
    
    def create_character_milestone(
        self, 
        character_id: str,
        milestone_type: str,
        title: str,
        description: str,
        significance: str = ""
    ) -> JournalEntry:
        """Create a character milestone entry"""
        
        content_parts = [
            f"**Milestone Type:** {milestone_type}",
            "",
            description
        ]
        
        if significance:
            content_parts.extend(["", "**Personal Significance:**", significance])
        
        content = "\n".join(content_parts)
        
        return self.create_entry(
            character_id=character_id,
            title=title,
            content=content,
            tags=["milestone", milestone_type.lower().replace(" ", "_")],
            is_private=True
        )
    
    def export_character_journal(self, character_id: str) -> Dict[str, Any]:
        """Export character's journal for backup/sharing"""
        
        entries = self.get_character_entries(character_id)
        stats = self.get_character_statistics(character_id)
        
        return {
            "character_id": character_id,
            "export_date": datetime.utcnow().isoformat(),
            "statistics": stats,
            "entries": [entry.dict() for entry in entries]
        }
    
    def import_character_journal(self, journal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Import character journal from backup"""
        
        result = {
            "imported": 0,
            "skipped": 0,
            "errors": []
        }
        
        try:
            character_id = journal_data.get("character_id")
            entries_data = journal_data.get("entries", [])
            
            for entry_data in entries_data:
                try:
                    # Check for duplicate entries
                    if entry_data["id"] in self.entries:
                        result["skipped"] += 1
                        continue
                    
                    # Create entry from data
                    entry = JournalEntry(**entry_data)
                    
                    # Store entry
                    self.entries[entry.id] = entry
                    
                    # Update indexes
                    if character_id not in self.character_entries:
                        self.character_entries[character_id] = []
                    self.character_entries[character_id].append(entry.id)
                    
                    for tag in entry.tags:
                        if tag not in self.tag_index:
                            self.tag_index[tag] = []
                        self.tag_index[tag].append(entry.id)
                    
                    result["imported"] += 1
                
                except Exception as e:
                    result["errors"].append(f"Failed to import entry: {str(e)}")
        
        except Exception as e:
            result["errors"].append(f"Import failed: {str(e)}")
        
        return result