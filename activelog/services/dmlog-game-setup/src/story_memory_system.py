import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import sqlite3
import os
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class MemoryType(str, Enum):
    CHARACTER_DEVELOPMENT = "character_development"
    PLOT_EVENT = "plot_event"
    RELATIONSHIP_CHANGE = "relationship_change"
    LOCATION_DISCOVERY = "location_discovery"
    ITEM_ACQUISITION = "item_acquisition"
    COMBAT_ENCOUNTER = "combat_encounter"
    SOCIAL_ENCOUNTER = "social_encounter"
    QUEST_PROGRESSION = "quest_progression"
    WORLD_REVELATION = "world_revelation"
    EMOTIONAL_MOMENT = "emotional_moment"

class MemoryImportance(str, Enum):
    TRIVIAL = "trivial"
    MINOR = "minor"
    MODERATE = "moderate"
    IMPORTANT = "important"
    MAJOR = "major"
    LEGENDARY = "legendary"

@dataclass
class StoryMemory:
    memory_id: str
    campaign_id: str
    session_number: int
    memory_type: MemoryType
    importance: MemoryImportance
    title: str
    description: str
    participants: List[str]
    location: str
    timestamp: datetime
    session_timestamp: datetime
    tags: List[str]
    emotional_weight: float
    consequences: List[str]
    related_memories: List[str]
    player_reactions: Dict[str, str]
    dm_notes: str
    audio_reference: Optional[str] = None

@dataclass
class SessionSummary:
    session_id: str
    campaign_id: str
    session_number: int
    date: datetime
    duration_minutes: int
    participants: List[str]
    key_events: List[str]
    character_developments: List[str]
    plot_progressions: List[str]
    new_relationships: List[str]
    discoveries: List[str]
    challenges_overcome: List[str]
    mysteries_introduced: List[str]
    emotional_highlights: List[str]
    cliff_hangers: List[str]
    dm_notes: str
    player_feedback: Dict[str, str]

@dataclass
class CampaignTimeline:
    campaign_id: str
    events: List[Dict[str, Any]]
    character_arcs: Dict[str, List[Dict[str, Any]]]
    plot_threads: Dict[str, Dict[str, Any]]
    world_changes: List[Dict[str, Any]]
    relationship_evolution: Dict[str, List[Dict[str, Any]]]

@dataclass
class CharacterArc:
    character_name: str
    player_name: str
    campaign_id: str
    arc_type: str  # 'growth', 'redemption', 'fall', 'mystery', 'romance'
    current_stage: str
    key_moments: List[str]
    relationships: Dict[str, str]
    goals: List[str]
    internal_conflicts: List[str]
    growth_areas: List[str]
    future_hooks: List[str]

class RelationshipWeb(BaseModel):
    campaign_id: str
    relationships: Dict[str, Dict[str, Any]]  # character_pair -> relationship_data
    relationship_history: Dict[str, List[Dict[str, Any]]]
    network_analysis: Dict[str, float]  # centrality scores, etc.

class CampaignWiki(BaseModel):
    campaign_id: str
    characters: Dict[str, Dict[str, Any]]
    locations: Dict[str, Dict[str, Any]]
    organizations: Dict[str, Dict[str, Any]]
    items: Dict[str, Dict[str, Any]]
    lore: Dict[str, str]
    timeline: List[Dict[str, Any]]
    mysteries: Dict[str, Dict[str, Any]]

class StoryMemorySystem:
    def __init__(self):
        self.db_path = "database/story_memory.db"
        self.active_campaigns = {}  # campaign_id -> campaign data
        self.session_memories = {}  # session_id -> List[StoryMemory]
        self.character_arcs = {}    # campaign_id -> Dict[character_name, CharacterArc]
        self.relationship_webs = {} # campaign_id -> RelationshipWeb
        self.campaign_wikis = {}    # campaign_id -> CampaignWiki
        self._setup_database()

    def _setup_database(self):
        """Set up SQLite database for persistent story memory."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Story memories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS story_memories (
                    memory_id TEXT PRIMARY KEY,
                    campaign_id TEXT,
                    session_number INTEGER,
                    memory_type TEXT,
                    importance TEXT,
                    title TEXT,
                    description TEXT,
                    participants TEXT,
                    location TEXT,
                    timestamp TEXT,
                    session_timestamp TEXT,
                    tags TEXT,
                    emotional_weight REAL,
                    consequences TEXT,
                    related_memories TEXT,
                    player_reactions TEXT,
                    dm_notes TEXT,
                    audio_reference TEXT
                )
            ''')
            
            # Session summaries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    campaign_id TEXT,
                    session_number INTEGER,
                    date TEXT,
                    duration_minutes INTEGER,
                    participants TEXT,
                    key_events TEXT,
                    character_developments TEXT,
                    plot_progressions TEXT,
                    new_relationships TEXT,
                    discoveries TEXT,
                    challenges_overcome TEXT,
                    mysteries_introduced TEXT,
                    emotional_highlights TEXT,
                    cliff_hangers TEXT,
                    dm_notes TEXT,
                    player_feedback TEXT
                )
            ''')
            
            # Character arcs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS character_arcs (
                    id TEXT PRIMARY KEY,
                    character_name TEXT,
                    player_name TEXT,
                    campaign_id TEXT,
                    arc_type TEXT,
                    current_stage TEXT,
                    key_moments TEXT,
                    relationships TEXT,
                    goals TEXT,
                    internal_conflicts TEXT,
                    growth_areas TEXT,
                    future_hooks TEXT,
                    last_updated TEXT
                )
            ''')
            
            # Campaign timelines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_timelines (
                    campaign_id TEXT PRIMARY KEY,
                    events TEXT,
                    character_arcs TEXT,
                    plot_threads TEXT,
                    world_changes TEXT,
                    relationship_evolution TEXT,
                    last_updated TEXT
                )
            ''')
            
            # Campaign wikis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_wikis (
                    campaign_id TEXT PRIMARY KEY,
                    characters TEXT,
                    locations TEXT,
                    organizations TEXT,
                    items TEXT,
                    lore TEXT,
                    timeline TEXT,
                    mysteries TEXT,
                    last_updated TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Story memory database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up story memory database: {e}")

    async def create_story_memory(self, campaign_id: str, session_number: int,
                                memory_type: MemoryType, importance: MemoryImportance,
                                title: str, description: str, participants: List[str],
                                location: str, tags: List[str] = None,
                                emotional_weight: float = 0.0, consequences: List[str] = None,
                                player_reactions: Dict[str, str] = None, dm_notes: str = "",
                                audio_reference: str = None) -> StoryMemory:
        """Create a new story memory."""
        
        memory_id = f"{campaign_id}_s{session_number}_{datetime.now().strftime('%H%M%S')}_{len(self.session_memories.get(session_number, []))}"
        
        memory = StoryMemory(
            memory_id=memory_id,
            campaign_id=campaign_id,
            session_number=session_number,
            memory_type=memory_type,
            importance=importance,
            title=title,
            description=description,
            participants=participants or [],
            location=location,
            timestamp=datetime.now(),
            session_timestamp=datetime.now(),
            tags=tags or [],
            emotional_weight=emotional_weight,
            consequences=consequences or [],
            related_memories=[],
            player_reactions=player_reactions or {},
            dm_notes=dm_notes,
            audio_reference=audio_reference
        )
        
        # Store in memory
        if session_number not in self.session_memories:
            self.session_memories[session_number] = []
        self.session_memories[session_number].append(memory)
        
        # Save to database
        await self._save_memory_to_db(memory)
        
        # Update related systems
        await self._update_character_arcs(memory)
        await self._update_relationship_web(memory)
        await self._update_campaign_wiki(memory)
        
        # Find related memories
        await self._link_related_memories(memory)
        
        logger.info(f"Created story memory: {title} ({memory_id})")
        return memory

    async def _save_memory_to_db(self, memory: StoryMemory):
        """Save story memory to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO story_memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.memory_id,
                memory.campaign_id,
                memory.session_number,
                memory.memory_type.value,
                memory.importance.value,
                memory.title,
                memory.description,
                json.dumps(memory.participants),
                memory.location,
                memory.timestamp.isoformat(),
                memory.session_timestamp.isoformat(),
                json.dumps(memory.tags),
                memory.emotional_weight,
                json.dumps(memory.consequences),
                json.dumps(memory.related_memories),
                json.dumps(memory.player_reactions),
                memory.dm_notes,
                memory.audio_reference
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving memory to database: {e}")

    async def _update_character_arcs(self, memory: StoryMemory):
        """Update character arcs based on new memory."""
        campaign_id = memory.campaign_id
        
        if campaign_id not in self.character_arcs:
            self.character_arcs[campaign_id] = {}
        
        arcs = self.character_arcs[campaign_id]
        
        # Update arcs for each participant
        for participant in memory.participants:
            if participant not in arcs:
                # Create new character arc
                arc = CharacterArc(
                    character_name=participant,
                    player_name="Unknown",  # Would be filled from session data
                    campaign_id=campaign_id,
                    arc_type="growth",  # Default, would be determined by analysis
                    current_stage="beginning",
                    key_moments=[],
                    relationships={},
                    goals=[],
                    internal_conflicts=[],
                    growth_areas=[],
                    future_hooks=[]
                )
                arcs[participant] = arc
            
            arc = arcs[participant]
            
            # Add key moment if important enough
            if memory.importance in [MemoryImportance.IMPORTANT, MemoryImportance.MAJOR, MemoryImportance.LEGENDARY]:
                arc.key_moments.append(memory.memory_id)
            
            # Update arc based on memory type
            if memory.memory_type == MemoryType.CHARACTER_DEVELOPMENT:
                await self._analyze_character_development(arc, memory)
            elif memory.memory_type == MemoryType.RELATIONSHIP_CHANGE:
                await self._update_character_relationships(arc, memory)
            
            # Save updated arc
            await self._save_character_arc(arc)

    async def _analyze_character_development(self, arc: CharacterArc, memory: StoryMemory):
        """Analyze character development from memory."""
        # Simple keyword-based analysis (would use NLP in production)
        description_lower = memory.description.lower()
        
        # Growth indicators
        growth_keywords = ['learned', 'realized', 'overcame', 'achieved', 'mastered', 'understood']
        if any(keyword in description_lower for keyword in growth_keywords):
            if 'personal_growth' not in arc.growth_areas:
                arc.growth_areas.append('personal_growth')
        
        # Conflict indicators
        conflict_keywords = ['struggled', 'conflict', 'doubt', 'fear', 'challenge', 'difficulty']
        if any(keyword in description_lower for keyword in conflict_keywords):
            potential_conflict = f"Internal struggle related to {memory.title}"
            if potential_conflict not in arc.internal_conflicts:
                arc.internal_conflicts.append(potential_conflict)
        
        # Goal indicators
        goal_keywords = ['wants', 'seeks', 'hopes', 'plans', 'intends', 'determined']
        if any(keyword in description_lower for keyword in goal_keywords):
            potential_goal = f"Goal related to {memory.title}"
            if potential_goal not in arc.goals:
                arc.goals.append(potential_goal)

    async def _update_character_relationships(self, arc: CharacterArc, memory: StoryMemory):
        """Update character relationships from memory."""
        # Extract relationship information
        for participant in memory.participants:
            if participant != arc.character_name:
                # Determine relationship type from memory
                relationship_type = self._infer_relationship_type(memory, arc.character_name, participant)
                
                if relationship_type:
                    arc.relationships[participant] = relationship_type

    def _infer_relationship_type(self, memory: StoryMemory, character1: str, character2: str) -> Optional[str]:
        """Infer relationship type between characters from memory."""
        description_lower = memory.description.lower()
        
        # Friendship indicators
        if any(word in description_lower for word in ['friend', 'ally', 'helped', 'supported']):
            return 'friend'
        
        # Romance indicators
        if any(word in description_lower for word in ['love', 'romance', 'kiss', 'attraction']):
            return 'romantic_interest'
        
        # Rivalry indicators
        if any(word in description_lower for word in ['rival', 'compete', 'opposed', 'conflict']):
            return 'rival'
        
        # Mentor indicators
        if any(word in description_lower for word in ['taught', 'mentor', 'guide', 'trained']):
            return 'mentor' if character2 in memory.description else 'student'
        
        # Default to acquaintance
        return 'acquaintance'

    async def _update_relationship_web(self, memory: StoryMemory):
        """Update relationship web based on new memory."""
        campaign_id = memory.campaign_id
        
        if campaign_id not in self.relationship_webs:
            self.relationship_webs[campaign_id] = RelationshipWeb(
                campaign_id=campaign_id,
                relationships={},
                relationship_history={},
                network_analysis={}
            )
        
        web = self.relationship_webs[campaign_id]
        
        # Update relationships between all participants
        participants = memory.participants
        for i, char1 in enumerate(participants):
            for j, char2 in enumerate(participants):
                if i < j:  # Avoid duplicates
                    pair_key = f"{char1}_{char2}"
                    
                    if pair_key not in web.relationships:
                        web.relationships[pair_key] = {
                            'type': 'acquaintance',
                            'strength': 0.1,
                            'history': [],
                            'first_meeting': memory.memory_id
                        }
                    
                    # Update relationship strength based on memory importance
                    strength_increase = {
                        MemoryImportance.TRIVIAL: 0.01,
                        MemoryImportance.MINOR: 0.02,
                        MemoryImportance.MODERATE: 0.05,
                        MemoryImportance.IMPORTANT: 0.1,
                        MemoryImportance.MAJOR: 0.2,
                        MemoryImportance.LEGENDARY: 0.5
                    }
                    
                    current_strength = web.relationships[pair_key]['strength']
                    web.relationships[pair_key]['strength'] = min(1.0, 
                        current_strength + strength_increase[memory.importance])
                    
                    # Add to history
                    if pair_key not in web.relationship_history:
                        web.relationship_history[pair_key] = []
                    
                    web.relationship_history[pair_key].append({
                        'memory_id': memory.memory_id,
                        'event': memory.title,
                        'type_change': self._infer_relationship_type(memory, char1, char2),
                        'timestamp': memory.timestamp.isoformat()
                    })

    async def _update_campaign_wiki(self, memory: StoryMemory):
        """Update campaign wiki based on new memory."""
        campaign_id = memory.campaign_id
        
        if campaign_id not in self.campaign_wikis:
            self.campaign_wikis[campaign_id] = CampaignWiki(
                campaign_id=campaign_id,
                characters={},
                locations={},
                organizations={},
                items={},
                lore={},
                timeline=[],
                mysteries={}
            )
        
        wiki = self.campaign_wikis[campaign_id]
        
        # Update characters
        for participant in memory.participants:
            if participant not in wiki.characters:
                wiki.characters[participant] = {
                    'name': participant,
                    'first_appearance': memory.memory_id,
                    'key_moments': [],
                    'relationships': {},
                    'notable_quotes': [],
                    'character_traits': []
                }
            
            wiki.characters[participant]['key_moments'].append({
                'memory_id': memory.memory_id,
                'event': memory.title,
                'session': memory.session_number
            })
        
        # Update locations
        if memory.location and memory.location not in wiki.locations:
            wiki.locations[memory.location] = {
                'name': memory.location,
                'first_visited': memory.memory_id,
                'description': '',
                'notable_events': [],
                'inhabitants': [],
                'features': []
            }
        
        if memory.location in wiki.locations:
            wiki.locations[memory.location]['notable_events'].append({
                'memory_id': memory.memory_id,
                'event': memory.title,
                'session': memory.session_number
            })
        
        # Update timeline
        wiki.timeline.append({
            'memory_id': memory.memory_id,
            'session': memory.session_number,
            'title': memory.title,
            'participants': memory.participants,
            'location': memory.location,
            'timestamp': memory.timestamp.isoformat(),
            'importance': memory.importance.value
        })
        
        # Sort timeline by session and timestamp
        wiki.timeline.sort(key=lambda x: (x['session'], x['timestamp']))
        
        # Update mysteries if applicable
        if 'mystery' in memory.tags or memory.memory_type == MemoryType.WORLD_REVELATION:
            mystery_key = f"mystery_{len(wiki.mysteries) + 1}"
            wiki.mysteries[mystery_key] = {
                'title': memory.title,
                'discovered_in': memory.memory_id,
                'clues': [memory.description],
                'status': 'active',
                'related_memories': [memory.memory_id]
            }
        
        # Save wiki to database
        await self._save_campaign_wiki(wiki)

    async def _link_related_memories(self, new_memory: StoryMemory):
        """Find and link related memories."""
        campaign_memories = []
        
        # Gather all memories for this campaign
        for session_memories in self.session_memories.values():
            campaign_memories.extend([m for m in session_memories if m.campaign_id == new_memory.campaign_id])
        
        related_memories = []
        
        for memory in campaign_memories:
            if memory.memory_id != new_memory.memory_id:
                similarity_score = await self._calculate_memory_similarity(new_memory, memory)
                
                if similarity_score > 0.3:  # Threshold for relatedness
                    related_memories.append(memory.memory_id)
                    # Also add reverse link
                    if new_memory.memory_id not in memory.related_memories:
                        memory.related_memories.append(new_memory.memory_id)
                        await self._save_memory_to_db(memory)
        
        new_memory.related_memories = related_memories
        await self._save_memory_to_db(new_memory)

    async def _calculate_memory_similarity(self, memory1: StoryMemory, memory2: StoryMemory) -> float:
        """Calculate similarity between two memories."""
        similarity = 0.0
        
        # Participant overlap
        common_participants = set(memory1.participants) & set(memory2.participants)
        if memory1.participants and memory2.participants:
            participant_similarity = len(common_participants) / max(len(memory1.participants), len(memory2.participants))
            similarity += participant_similarity * 0.3
        
        # Location similarity
        if memory1.location == memory2.location and memory1.location:
            similarity += 0.2
        
        # Tag overlap
        common_tags = set(memory1.tags) & set(memory2.tags)
        if memory1.tags and memory2.tags:
            tag_similarity = len(common_tags) / max(len(memory1.tags), len(memory2.tags))
            similarity += tag_similarity * 0.2
        
        # Memory type similarity
        if memory1.memory_type == memory2.memory_type:
            similarity += 0.1
        
        # Time proximity (memories close in time are more likely related)
        time_diff = abs((memory1.timestamp - memory2.timestamp).total_seconds())
        if time_diff < 3600:  # Within 1 hour
            time_similarity = 1.0 - (time_diff / 3600.0)
            similarity += time_similarity * 0.2
        
        return min(1.0, similarity)

    async def generate_session_summary(self, campaign_id: str, session_number: int,
                                     duration_minutes: int, participants: List[str],
                                     dm_notes: str = "", player_feedback: Dict[str, str] = None) -> SessionSummary:
        """Generate a comprehensive session summary."""
        
        session_memories = [m for m in self.session_memories.get(session_number, []) 
                          if m.campaign_id == campaign_id]
        
        # Extract key information
        key_events = [m.title for m in session_memories if m.importance in [MemoryImportance.IMPORTANT, MemoryImportance.MAJOR, MemoryImportance.LEGENDARY]]
        
        character_developments = [m.title for m in session_memories if m.memory_type == MemoryType.CHARACTER_DEVELOPMENT]
        
        plot_progressions = [m.title for m in session_memories if m.memory_type == MemoryType.QUEST_PROGRESSION]
        
        new_relationships = [m.title for m in session_memories if m.memory_type == MemoryType.RELATIONSHIP_CHANGE]
        
        discoveries = [m.title for m in session_memories 
                      if m.memory_type in [MemoryType.LOCATION_DISCOVERY, MemoryType.WORLD_REVELATION]]
        
        challenges_overcome = [m.title for m in session_memories 
                             if m.memory_type in [MemoryType.COMBAT_ENCOUNTER, MemoryType.SOCIAL_ENCOUNTER]
                             and m.importance != MemoryImportance.TRIVIAL]
        
        mysteries_introduced = [m.title for m in session_memories if 'mystery' in m.tags]
        
        emotional_highlights = [m.title for m in session_memories if m.emotional_weight > 0.5]
        
        # Find cliffhangers (important memories at the end of session)
        recent_memories = sorted(session_memories, key=lambda m: m.timestamp)[-3:]
        cliff_hangers = [m.title for m in recent_memories 
                        if m.importance in [MemoryImportance.IMPORTANT, MemoryImportance.MAJOR]]
        
        summary = SessionSummary(
            session_id=f"{campaign_id}_session_{session_number}",
            campaign_id=campaign_id,
            session_number=session_number,
            date=datetime.now(),
            duration_minutes=duration_minutes,
            participants=participants,
            key_events=key_events,
            character_developments=character_developments,
            plot_progressions=plot_progressions,
            new_relationships=new_relationships,
            discoveries=discoveries,
            challenges_overcome=challenges_overcome,
            mysteries_introduced=mysteries_introduced,
            emotional_highlights=emotional_highlights,
            cliff_hangers=cliff_hangers,
            dm_notes=dm_notes,
            player_feedback=player_feedback or {}
        )
        
        # Save to database
        await self._save_session_summary(summary)
        
        return summary

    async def _save_session_summary(self, summary: SessionSummary):
        """Save session summary to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO session_summaries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary.session_id,
                summary.campaign_id,
                summary.session_number,
                summary.date.isoformat(),
                summary.duration_minutes,
                json.dumps(summary.participants),
                json.dumps(summary.key_events),
                json.dumps(summary.character_developments),
                json.dumps(summary.plot_progressions),
                json.dumps(summary.new_relationships),
                json.dumps(summary.discoveries),
                json.dumps(summary.challenges_overcome),
                json.dumps(summary.mysteries_introduced),
                json.dumps(summary.emotional_highlights),
                json.dumps(summary.cliff_hangers),
                summary.dm_notes,
                json.dumps(summary.player_feedback)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving session summary: {e}")

    async def generate_previously_on_recap(self, campaign_id: str, current_session: int,
                                         recap_sessions: int = 3) -> str:
        """Generate 'Previously on...' recap for campaign."""
        
        # Get recent session summaries
        start_session = max(1, current_session - recap_sessions)
        recent_summaries = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM session_summaries 
                WHERE campaign_id = ? AND session_number >= ? AND session_number < ?
                ORDER BY session_number
            ''', (campaign_id, start_session, current_session))
            
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                summary_data = {
                    'session_number': row[2],
                    'key_events': json.loads(row[6]),
                    'character_developments': json.loads(row[7]),
                    'plot_progressions': json.loads(row[8]),
                    'discoveries': json.loads(row[10]),
                    'cliff_hangers': json.loads(row[14])
                }
                recent_summaries.append(summary_data)
            
        except Exception as e:
            logger.error(f"Error retrieving session summaries: {e}")
            return "Previously on this campaign..."
        
        # Generate narrative recap
        recap_parts = ["Previously on this campaign..."]
        
        for summary in recent_summaries:
            session_recap = []
            
            # Key events
            if summary['key_events']:
                session_recap.extend(summary['key_events'][:2])  # Top 2 events
            
            # Character developments
            if summary['character_developments']:
                session_recap.extend(summary['character_developments'][:1])
            
            # Plot progressions
            if summary['plot_progressions']:
                session_recap.extend(summary['plot_progressions'][:1])
            
            # Discoveries
            if summary['discoveries']:
                session_recap.extend(summary['discoveries'][:1])
            
            if session_recap:
                session_text = f"In Session {summary['session_number']}: {'. '.join(session_recap[:3])}"
                recap_parts.append(session_text)
        
        # Add cliff hangers from last session
        if recent_summaries and recent_summaries[-1]['cliff_hangers']:
            cliff_text = f"Last time, we left off with: {'. '.join(recent_summaries[-1]['cliff_hangers'])}"
            recap_parts.append(cliff_text)
        
        return "\n\n".join(recap_parts)

    async def get_forgotten_plot_threads(self, campaign_id: str, sessions_back: int = 5) -> List[Dict[str, Any]]:
        """Identify plot threads that haven't been mentioned recently."""
        
        # Get all memories for the campaign
        all_memories = []
        for session_memories in self.session_memories.values():
            all_memories.extend([m for m in session_memories if m.campaign_id == campaign_id])
        
        # Find current session
        current_session = max([m.session_number for m in all_memories]) if all_memories else 1
        cutoff_session = current_session - sessions_back
        
        # Identify plot threads
        plot_threads = {}
        
        for memory in all_memories:
            if memory.memory_type in [MemoryType.QUEST_PROGRESSION, MemoryType.WORLD_REVELATION]:
                thread_key = self._extract_plot_thread_key(memory)
                
                if thread_key not in plot_threads:
                    plot_threads[thread_key] = {
                        'title': thread_key,
                        'first_mentioned': memory.session_number,
                        'last_mentioned': memory.session_number,
                        'importance': memory.importance.value,
                        'status': 'active',
                        'related_memories': []
                    }
                
                thread_data = plot_threads[thread_key]
                thread_data['last_mentioned'] = max(thread_data['last_mentioned'], memory.session_number)
                thread_data['related_memories'].append(memory.memory_id)
                
                # Update importance if this memory is more important
                importance_order = ['trivial', 'minor', 'moderate', 'important', 'major', 'legendary']
                if importance_order.index(memory.importance.value) > importance_order.index(thread_data['importance']):
                    thread_data['importance'] = memory.importance.value
        
        # Find forgotten threads
        forgotten_threads = []
        for thread_key, thread_data in plot_threads.items():
            if thread_data['last_mentioned'] < cutoff_session:
                if thread_data['importance'] in ['important', 'major', 'legendary']:
                    thread_data['sessions_since_mention'] = current_session - thread_data['last_mentioned']
                    forgotten_threads.append(thread_data)
        
        # Sort by importance and time since mention
        forgotten_threads.sort(key=lambda x: (
            ['legendary', 'major', 'important'].index(x['importance']) if x['importance'] in ['legendary', 'major', 'important'] else 3,
            -x['sessions_since_mention']
        ))
        
        return forgotten_threads

    def _extract_plot_thread_key(self, memory: StoryMemory) -> str:
        """Extract a plot thread key from a memory."""
        # Simple keyword extraction (would use NLP in production)
        title_words = memory.title.lower().split()
        
        # Remove common words
        common_words = ['the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by']
        meaningful_words = [word for word in title_words if word not in common_words]
        
        # Take first 2-3 meaningful words as thread key
        thread_key = ' '.join(meaningful_words[:3])
        return thread_key or memory.title

    async def build_campaign_timeline(self, campaign_id: str) -> CampaignTimeline:
        """Build comprehensive campaign timeline."""
        
        # Get all memories for campaign
        all_memories = []
        for session_memories in self.session_memories.values():
            all_memories.extend([m for m in session_memories if m.campaign_id == campaign_id])
        
        # Sort by session and timestamp
        all_memories.sort(key=lambda m: (m.session_number, m.timestamp))
        
        # Build events timeline
        events = []
        for memory in all_memories:
            event = {
                'memory_id': memory.memory_id,
                'session': memory.session_number,
                'title': memory.title,
                'description': memory.description,
                'type': memory.memory_type.value,
                'importance': memory.importance.value,
                'participants': memory.participants,
                'location': memory.location,
                'timestamp': memory.timestamp.isoformat(),
                'emotional_weight': memory.emotional_weight,
                'tags': memory.tags
            }
            events.append(event)
        
        # Build character arcs timeline
        character_arcs = {}
        if campaign_id in self.character_arcs:
            for char_name, arc in self.character_arcs[campaign_id].items():
                character_arcs[char_name] = []
                
                for moment_id in arc.key_moments:
                    memory = next((m for m in all_memories if m.memory_id == moment_id), None)
                    if memory:
                        character_arcs[char_name].append({
                            'memory_id': moment_id,
                            'session': memory.session_number,
                            'title': memory.title,
                            'development_type': memory.memory_type.value,
                            'timestamp': memory.timestamp.isoformat()
                        })
        
        # Build plot threads timeline
        plot_threads = {}
        quest_memories = [m for m in all_memories if m.memory_type == MemoryType.QUEST_PROGRESSION]
        
        current_threads = {}
        for memory in quest_memories:
            thread_key = self._extract_plot_thread_key(memory)
            
            if thread_key not in current_threads:
                current_threads[thread_key] = {
                    'title': thread_key,
                    'status': 'active',
                    'events': [],
                    'importance': memory.importance.value
                }
            
            current_threads[thread_key]['events'].append({
                'memory_id': memory.memory_id,
                'session': memory.session_number,
                'title': memory.title,
                'timestamp': memory.timestamp.isoformat()
            })
        
        plot_threads = current_threads
        
        # Build world changes timeline
        world_changes = []
        world_memories = [m for m in all_memories 
                         if m.memory_type in [MemoryType.WORLD_REVELATION, MemoryType.LOCATION_DISCOVERY]]
        
        for memory in world_memories:
            world_changes.append({
                'memory_id': memory.memory_id,
                'session': memory.session_number,
                'title': memory.title,
                'type': memory.memory_type.value,
                'location': memory.location,
                'timestamp': memory.timestamp.isoformat()
            })
        
        # Build relationship evolution
        relationship_evolution = {}
        if campaign_id in self.relationship_webs:
            web = self.relationship_webs[campaign_id]
            for pair_key, history in web.relationship_history.items():
                relationship_evolution[pair_key] = history
        
        timeline = CampaignTimeline(
            campaign_id=campaign_id,
            events=events,
            character_arcs=character_arcs,
            plot_threads=plot_threads,
            world_changes=world_changes,
            relationship_evolution=relationship_evolution
        )
        
        # Save to database
        await self._save_campaign_timeline(timeline)
        
        return timeline

    async def _save_character_arc(self, arc: CharacterArc):
        """Save character arc to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            arc_id = f"{arc.campaign_id}_{arc.character_name}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO character_arcs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                arc_id,
                arc.character_name,
                arc.player_name,
                arc.campaign_id,
                arc.arc_type,
                arc.current_stage,
                json.dumps(arc.key_moments),
                json.dumps(arc.relationships),
                json.dumps(arc.goals),
                json.dumps(arc.internal_conflicts),
                json.dumps(arc.growth_areas),
                json.dumps(arc.future_hooks),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving character arc: {e}")

    async def _save_campaign_wiki(self, wiki: CampaignWiki):
        """Save campaign wiki to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO campaign_wikis VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                wiki.campaign_id,
                json.dumps(wiki.characters),
                json.dumps(wiki.locations),
                json.dumps(wiki.organizations),
                json.dumps(wiki.items),
                json.dumps(wiki.lore),
                json.dumps(wiki.timeline),
                json.dumps(wiki.mysteries),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving campaign wiki: {e}")

    async def _save_campaign_timeline(self, timeline: CampaignTimeline):
        """Save campaign timeline to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO campaign_timelines VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timeline.campaign_id,
                json.dumps(timeline.events, default=str),
                json.dumps(timeline.character_arcs, default=str),
                json.dumps(timeline.plot_threads, default=str),
                json.dumps(timeline.world_changes, default=str),
                json.dumps(timeline.relationship_evolution, default=str),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving campaign timeline: {e}")

    def get_campaign_wiki(self, campaign_id: str) -> Optional[CampaignWiki]:
        """Get campaign wiki."""
        return self.campaign_wikis.get(campaign_id)

    def get_character_arc(self, campaign_id: str, character_name: str) -> Optional[CharacterArc]:
        """Get character arc."""
        if campaign_id in self.character_arcs:
            return self.character_arcs[campaign_id].get(character_name)
        return None

    async def load_campaign_data(self, campaign_id: str):
        """Load all campaign data from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load memories
            cursor.execute('SELECT * FROM story_memories WHERE campaign_id = ?', (campaign_id,))
            memory_rows = cursor.fetchall()
            
            for row in memory_rows:
                memory = StoryMemory(
                    memory_id=row[0],
                    campaign_id=row[1],
                    session_number=row[2],
                    memory_type=MemoryType(row[3]),
                    importance=MemoryImportance(row[4]),
                    title=row[5],
                    description=row[6],
                    participants=json.loads(row[7]),
                    location=row[8],
                    timestamp=datetime.fromisoformat(row[9]),
                    session_timestamp=datetime.fromisoformat(row[10]),
                    tags=json.loads(row[11]),
                    emotional_weight=row[12],
                    consequences=json.loads(row[13]),
                    related_memories=json.loads(row[14]),
                    player_reactions=json.loads(row[15]),
                    dm_notes=row[16],
                    audio_reference=row[17]
                )
                
                session_num = memory.session_number
                if session_num not in self.session_memories:
                    self.session_memories[session_num] = []
                self.session_memories[session_num].append(memory)
            
            # Load character arcs
            cursor.execute('SELECT * FROM character_arcs WHERE campaign_id = ?', (campaign_id,))
            arc_rows = cursor.fetchall()
            
            if campaign_id not in self.character_arcs:
                self.character_arcs[campaign_id] = {}
            
            for row in arc_rows:
                arc = CharacterArc(
                    character_name=row[1],
                    player_name=row[2],
                    campaign_id=row[3],
                    arc_type=row[4],
                    current_stage=row[5],
                    key_moments=json.loads(row[6]),
                    relationships=json.loads(row[7]),
                    goals=json.loads(row[8]),
                    internal_conflicts=json.loads(row[9]),
                    growth_areas=json.loads(row[10]),
                    future_hooks=json.loads(row[11])
                )
                
                self.character_arcs[campaign_id][arc.character_name] = arc
            
            # Load campaign wiki
            cursor.execute('SELECT * FROM campaign_wikis WHERE campaign_id = ?', (campaign_id,))
            wiki_row = cursor.fetchone()
            
            if wiki_row:
                wiki = CampaignWiki(
                    campaign_id=wiki_row[0],
                    characters=json.loads(wiki_row[1]),
                    locations=json.loads(wiki_row[2]),
                    organizations=json.loads(wiki_row[3]),
                    items=json.loads(wiki_row[4]),
                    lore=json.loads(wiki_row[5]),
                    timeline=json.loads(wiki_row[6]),
                    mysteries=json.loads(wiki_row[7])
                )
                
                self.campaign_wikis[campaign_id] = wiki
            
            conn.close()
            logger.info(f"Loaded campaign data for {campaign_id}")
            
        except Exception as e:
            logger.error(f"Error loading campaign data: {e}")

    def get_memory_statistics(self, campaign_id: str) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        campaign_memories = []
        for session_memories in self.session_memories.values():
            campaign_memories.extend([m for m in session_memories if m.campaign_id == campaign_id])
        
        if not campaign_memories:
            return {}
        
        # Count by type
        type_counts = {}
        for memory_type in MemoryType:
            type_counts[memory_type.value] = len([m for m in campaign_memories if m.memory_type == memory_type])
        
        # Count by importance
        importance_counts = {}
        for importance in MemoryImportance:
            importance_counts[importance.value] = len([m for m in campaign_memories if m.importance == importance])
        
        # Session distribution
        session_counts = {}
        for memory in campaign_memories:
            session = memory.session_number
            session_counts[session] = session_counts.get(session, 0) + 1
        
        return {
            'total_memories': len(campaign_memories),
            'memory_types': type_counts,
            'importance_levels': importance_counts,
            'sessions_recorded': len(session_counts),
            'session_distribution': session_counts,
            'average_memories_per_session': len(campaign_memories) / max(len(session_counts), 1),
            'most_active_session': max(session_counts.items(), key=lambda x: x[1])[0] if session_counts else None
        }