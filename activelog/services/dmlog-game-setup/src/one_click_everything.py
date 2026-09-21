import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import random
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class GenerationType(str, Enum):
    ENCOUNTER = "encounter"
    NPC = "npc"
    LOCATION = "location"
    QUEST = "quest"
    ITEM = "item"
    PLOT_TWIST = "plot_twist"
    CLIFFHANGER = "cliffhanger"
    SCENE_ENHANCEMENT = "scene_enhancement"
    RANDOM_EVENT = "random_event"
    TAVERN_BRAWL = "tavern_brawl"

class DifficultyLevel(str, Enum):
    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    DEADLY = "deadly"

@dataclass
class GenerationRequest:
    request_id: str
    generation_type: GenerationType
    parameters: Dict[str, Any]
    context: Dict[str, Any]
    constraints: Dict[str, Any]
    session_id: str
    timestamp: datetime

@dataclass
class GeneratedContent:
    content_id: str
    generation_type: GenerationType
    title: str
    description: str
    details: Dict[str, Any]
    implementation_notes: str
    voice_notes: Optional[str]
    maps_data: Optional[Dict[str, Any]]
    encounter_stats: Optional[Dict[str, Any]]
    audio_cues: List[str]
    context_integration: Dict[str, Any]
    difficulty_level: Optional[DifficultyLevel]
    estimated_duration: int  # minutes

class OneClickGenerator:
    def __init__(self):
        self.generation_templates = self._initialize_templates()
        self.encounter_builders = self._initialize_encounter_builders()
        self.npc_generators = self._initialize_npc_generators()
        self.plot_generators = self._initialize_plot_generators()
        self.random_tables = self._initialize_random_tables()
        self.context_analyzers = self._initialize_context_analyzers()

    def _initialize_templates(self) -> Dict[str, Dict]:
        """Initialize generation templates for different content types."""
        return {
            'tavern_brawl': {
                'base_setup': {
                    'trigger_events': [
                        "A drunk patron insults another's hometown",
                        "Someone cheats at cards and gets caught",
                        "A mercenary refuses to pay their tab",
                        "Two groups argue over the same table",
                        "A bard's song offends local sensibilities"
                    ],
                    'escalation_stages': [
                        "Heated words and shoving",
                        "Chairs and mugs start flying",
                        "Tables get overturned as cover",
                        "Someone draws a weapon",
                        "Full chaos with multiple brawls"
                    ]
                },
                'npcs': {
                    'instigator': ['Drunk Mercenary', 'Offended Local', 'Cheating Gambler', 'Rowdy Sailor'],
                    'peacemaker': ['Wise Bartender', 'Local Guard', 'Respected Elder', 'Diplomatic Merchant'],
                    'wildcard': ['Mysterious Stranger', 'Bard Looking for Material', 'Pickpocket', 'Undercover Noble']
                },
                'complications': [
                    "City guard arrives just as weapons are drawn",
                    "Someone recognizes one of the PCs as wanted",
                    "The fight reveals a hidden entrance or secret",
                    "An NPC the party needs gets seriously hurt",
                    "The brawl is actually a distraction for a heist"
                ]
            },
            'mysterious_npc': {
                'backgrounds': [
                    "Former adventurer with a dark secret",
                    "Disguised noble fleeing political intrigue",
                    "Amnesiac with mysterious powers",
                    "Time traveler from the future/past",
                    "Angel or demon in mortal form",
                    "Retired assassin seeking redemption",
                    "Scholar cursed with forbidden knowledge",
                    "Shapeshifter studying human behavior"
                ],
                'motivations': [
                    "Seeking redemption for past mistakes",
                    "Protecting someone they love",
                    "Gathering information for a secret purpose",
                    "Testing the party's worthiness",
                    "Fulfilling an ancient prophecy",
                    "Hunting a dangerous enemy",
                    "Trying to break a curse",
                    "Maintaining a crucial balance"
                ],
                'quirks': [
                    "Never removes their gloves",
                    "Speaks in riddles and metaphors",
                    "Always knows more than they should",
                    "Has an unusual pet or companion",
                    "Pays for everything with ancient coins",
                    "Their shadow moves independently",
                    "They cast no reflection",
                    "Animals are either drawn to or flee from them"
                ]
            },
            'side_quest': {
                'types': [
                    "Fetch quest with a twist",
                    "Escort mission gone wrong",
                    "Mystery investigation",
                    "Rescue operation",
                    "Delivery with complications",
                    "Competition or tournament",
                    "Exploration and mapping",
                    "Problem-solving for locals"
                ],
                'complications': [
                    "The item/person isn't what they seem",
                    "Multiple parties want the same thing",
                    "The quest giver lied about something important",
                    "Time pressure from an unexpected source",
                    "Moral dilemma about completing the quest",
                    "The reward is cursed or dangerous",
                    "Old enemies of the party get involved",
                    "The quest ties into the main story"
                ]
            }
        }

    def _initialize_encounter_builders(self) -> Dict[str, Any]:
        """Initialize encounter building systems."""
        return {
            'combat_encounters': {
                'terrain_types': {
                    'forest': {
                        'features': ['tall trees', 'undergrowth', 'stream', 'fallen log'],
                        'tactical_elements': ['cover', 'difficult terrain', 'elevation'],
                        'environmental_hazards': ['pit trap', 'thorny vines', 'unstable tree']
                    },
                    'dungeon': {
                        'features': ['stone walls', 'pillars', 'alcoves', 'stairs'],
                        'tactical_elements': ['choke points', 'flanking routes', 'vertical space'],
                        'environmental_hazards': ['spike trap', 'poison gas', 'collapsing ceiling']
                    },
                    'urban': {
                        'features': ['buildings', 'alleyways', 'market stalls', 'fountain'],
                        'tactical_elements': ['crowd control', 'property damage', 'witness concern'],
                        'environmental_hazards': ['fire spread', 'civilian panic', 'guard response']
                    }
                },
                'enemy_groups': {
                    'bandits': {
                        'composition': ['bandit leader', 'archer', 'thug', 'lookout'],
                        'tactics': ['ambush', 'hit_and_run', 'intimidation'],
                        'motivations': ['money', 'territory', 'revenge']
                    },
                    'monsters': {
                        'composition': ['alpha', 'pack members', 'juveniles'],
                        'tactics': ['pack hunting', 'territorial defense', 'feeding frenzy'],
                        'motivations': ['hunger', 'territory', 'protecting young']
                    },
                    'cultists': {
                        'composition': ['cult leader', 'zealots', 'summoned creature'],
                        'tactics': ['fanatical assault', 'ritual protection', 'summoning'],
                        'motivations': ['religious fervor', 'apocalyptic goals', 'power']
                    }
                }
            },
            'social_encounters': {
                'negotiation': {
                    'stakes': ['resources', 'information', 'alliances', 'safe passage'],
                    'complications': ['time pressure', 'hidden agendas', 'cultural barriers', 'past grievances'],
                    'resolution_types': ['compromise', 'creative solution', 'favor exchange', 'future obligation']
                },
                'court_intrigue': {
                    'players': ['ambitious noble', 'scheming adviser', 'foreign diplomat', 'merchant guild representative'],
                    'goals': ['political power', 'trade advantage', 'military alliance', 'information gathering'],
                    'methods': ['blackmail', 'bribery', 'seduction', 'manipulation']
                }
            }
        }

    def _initialize_npc_generators(self) -> Dict[str, Any]:
        """Initialize NPC generation systems."""
        return {
            'personality_traits': [
                'ambitious', 'cautious', 'cheerful', 'cruel', 'curious', 'determined',
                'dishonest', 'eccentric', 'friendly', 'greedy', 'helpful', 'honest',
                'humble', 'idealistic', 'lazy', 'loyal', 'mysterious', 'patient',
                'proud', 'reckless', 'secretive', 'stubborn', 'suspicious', 'wise'
            ],
            'physical_features': [
                'distinctive scar', 'unusual eye color', 'elaborate tattoo', 'missing limb',
                'ornate jewelry', 'weathered hands', 'perfect posture', 'nervous tic',
                'melodious voice', 'gap-toothed smile', 'imposing height', 'delicate build'
            ],
            'occupations': [
                'blacksmith', 'merchant', 'scholar', 'guard', 'farmer', 'innkeeper',
                'healer', 'artisan', 'performer', 'sailor', 'hunter', 'priest',
                'noble', 'spy', 'criminal', 'hermit', 'inventor', 'explorer'
            ],
            'relationships': [
                'estranged sibling', 'former lover', 'business partner', 'rival',
                'mentor', 'student', 'creditor', 'debtor', 'ally', 'enemy',
                'childhood friend', 'co-conspirator', 'witness to crime', 'saved life'
            ],
            'secrets': [
                'true identity', 'hidden wealth', 'shameful past', 'magical ability',
                'criminal history', 'noble birth', 'cursed item', 'forbidden love',
                'spy mission', 'family secret', 'prophetic vision', 'dark pact'
            ]
        }

    def _initialize_plot_generators(self) -> Dict[str, Any]:
        """Initialize plot generation systems."""
        return {
            'plot_twists': {
                'identity_reveals': [
                    "The helpful NPC is actually the main villain",
                    "A party member is related to the antagonist",
                    "The quest giver has been dead all along",
                    "An enemy is actually trying to help"
                ],
                'hidden_connections': [
                    "The current quest is part of a larger conspiracy",
                    "Two seemingly unrelated NPCs are working together",
                    "The party has been manipulated from the beginning",
                    "The real treasure was the friends made along the way... no, it's cursed"
                ],
                'false_assumptions': [
                    "The 'evil' monsters are actually protecting something important",
                    "The artifact the party seeks will cause more harm than good",
                    "The villain's plan would actually save the world",
                    "The party has been helping the wrong side"
                ]
            },
            'cliffhangers': {
                'immediate_danger': [
                    "The floor gives way, revealing a massive pit",
                    "Arrows start flying from hidden archers",
                    "The door seals shut and water begins pouring in",
                    "A massive creature's eyes open in the darkness"
                ],
                'revelations': [
                    "A character discovers a shocking truth about their past",
                    "An ally removes their mask to reveal an enemy",
                    "A message arrives that changes everything",
                    "The party realizes they've been in a magical illusion"
                ],
                'decisions': [
                    "Save the innocent bystander or pursue the villain",
                    "Choose which of two equally important allies to help",
                    "Decide whether to use a powerful but dangerous artifact",
                    "Pick which of multiple urgent quests to tackle first"
                ]
            }
        }

    def _initialize_random_tables(self) -> Dict[str, List]:
        """Initialize random generation tables."""
        return {
            'weather_events': [
                'sudden thunderstorm', 'magical fog', 'aurora displays', 'meteor shower',
                'unseasonable snow', 'scorching heat wave', 'rainbow after rain', 'dancing lights'
            ],
            'travel_encounters': [
                'merchant caravan', 'lost traveler', 'wild animal', 'bandit ambush',
                'ancient ruins', 'strange shrine', 'natural wonder', 'other adventuring party'
            ],
            'tavern_events': [
                'traveling storyteller', 'gambling tournament', 'recruitment officer',
                'mysterious hooded figure', 'celebration feast', 'bar brawl', 'merchant seeking guards'
            ],
            'urban_encounters': [
                'street festival', 'public execution', 'thieves guild recruitment',
                'noble procession', 'market fire', 'refugee influx', 'political demonstration'
            ]
        }

    def _initialize_context_analyzers(self) -> Dict[str, Any]:
        """Initialize context analysis systems."""
        return {
            'party_composition_effects': {
                'heavy_combat': ['fighters', 'barbarians', 'paladins'],
                'stealth_focused': ['rogues', 'rangers', 'shadow_monks'],
                'magic_heavy': ['wizards', 'sorcerers', 'warlocks', 'clerics'],
                'social_specialists': ['bards', 'paladins', 'some_warlocks']
            },
            'campaign_tone_indicators': {
                'heroic': ['save', 'protect', 'justice', 'noble', 'righteous'],
                'dark': ['curse', 'corruption', 'death', 'horror', 'despair'],
                'comedic': ['funny', 'silly', 'absurd', 'parody', 'humor'],
                'political': ['intrigue', 'conspiracy', 'power', 'alliance', 'betrayal'],
                'exploration': ['discover', 'unknown', 'frontier', 'wilderness', 'ancient']
            }
        }

    async def generate_one_click_content(self, generation_type: GenerationType,
                                       session_context: Dict[str, Any],
                                       specific_params: Dict[str, Any] = None) -> GeneratedContent:
        """Generate complete content with one click."""
        
        request = GenerationRequest(
            request_id=f"{generation_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            generation_type=generation_type,
            parameters=specific_params or {},
            context=session_context,
            constraints={},
            session_id=session_context.get('session_id', 'unknown'),
            timestamp=datetime.now()
        )
        
        if generation_type == GenerationType.TAVERN_BRAWL:
            return await self._generate_tavern_brawl(request)
        elif generation_type == GenerationType.NPC:
            return await self._generate_mysterious_npc(request)
        elif generation_type == GenerationType.QUEST:
            return await self._generate_side_quest(request)
        elif generation_type == GenerationType.ENCOUNTER:
            return await self._generate_balanced_encounter(request)
        elif generation_type == GenerationType.PLOT_TWIST:
            return await self._generate_plot_twist(request)
        elif generation_type == GenerationType.CLIFFHANGER:
            return await self._generate_cliffhanger(request)
        elif generation_type == GenerationType.SCENE_ENHANCEMENT:
            return await self._enhance_current_scene(request)
        else:
            return await self._generate_generic_content(request)

    async def _generate_tavern_brawl(self, request: GenerationRequest) -> GeneratedContent:
        """Generate a complete tavern brawl encounter."""
        template = self.generation_templates['tavern_brawl']
        
        # Select trigger event
        trigger = random.choice(template['base_setup']['trigger_events'])
        
        # Generate key NPCs
        instigator_type = random.choice(template['npcs']['instigator'])
        peacemaker_type = random.choice(template['npcs']['peacemaker'])
        wildcard_type = random.choice(template['npcs']['wildcard'])
        
        # Select complication
        complication = random.choice(template['complications'])
        
        # Generate layout
        tavern_layout = {
            'main_room': {
                'tables': random.randint(6, 12),
                'bar': 'along the north wall',
                'fireplace': 'west wall',
                'stairs_to_rooms': 'east side'
            },
            'tactical_elements': {
                'improvised_weapons': ['chairs', 'mugs', 'bottles', 'fireplace poker'],
                'cover': ['overturned tables', 'bar', 'support pillars'],
                'hazards': ['spilled ale (slippery)', 'broken glass', 'fireplace']
            }
        }
        
        # Generate escalation timeline
        escalation = template['base_setup']['escalation_stages']
        
        # Create encounter stats
        encounter_stats = {
            'difficulty': DifficultyLevel.MEDIUM,
            'participants': {
                'instigator': {
                    'name': f"{instigator_type}",
                    'ac': 12,
                    'hp': 15,
                    'attack_bonus': 3,
                    'damage': '1d4+1 (improvised weapon)'
                },
                'bar_patrons': {
                    'count': random.randint(4, 8),
                    'ac': 10,
                    'hp': 4,
                    'attack_bonus': 1,
                    'damage': '1d4 (unarmed)'
                }
            },
            'victory_conditions': [
                'Subdue the instigator',
                'Restore order through diplomacy',
                'Escape the chaos',
                'Protect innocent bystanders'
            ]
        }
        
        # Voice and roleplay notes
        voice_notes = f"""
        {instigator_type}: Slurred speech, aggressive tone, getting louder
        {peacemaker_type}: Calm, authoritative, trying to de-escalate
        {wildcard_type}: Mysterious, observing, may have hidden agenda
        Crowd: Shouts, cheers, gasps as chaos unfolds
        """
        
        description = f"""
        **TAVERN BRAWL: {trigger}**
        
        **The Setup:**
        The party is enjoying drinks at the local tavern when {trigger}. The situation quickly escalates as a {instigator_type} becomes increasingly belligerent.
        
        **Key NPCs:**
        - **{instigator_type}**: The troublemaker who started it all
        - **{peacemaker_type}**: Trying to restore order
        - **{wildcard_type}**: Present with unknown motives
        
        **Escalation Stages:**
        {chr(10).join(f"{i+1}. {stage}" for i, stage in enumerate(escalation))}
        
        **Complication:**
        {complication}
        
        **Tactical Map:**
        - {tavern_layout['main_room']['tables']} tables scattered around the room
        - Bar along the north wall with stools
        - Fireplace on west wall (potential hazard)
        - Stairs to private rooms on east side
        """
        
        implementation_notes = """
        **DM Notes:**
        - Start with social encounter, let it build naturally
        - Use initiative once physical violence starts  
        - Non-lethal damage unless weapons are drawn
        - Give players multiple solution options
        - The complication should happen at the climax
        - Consider consequences: reputation, legal trouble, information gained
        
        **Player Options:**
        - Try to de-escalate verbally
        - Join the fight on one side
        - Protect innocent bystanders  
        - Use the chaos to their advantage
        - Investigate the wildcard NPC
        """
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.TAVERN_BRAWL,
            title="Tavern Brawl: Chaos at the Local Pub",
            description=description,
            details=tavern_layout,
            implementation_notes=implementation_notes,
            voice_notes=voice_notes,
            maps_data=tavern_layout,
            encounter_stats=encounter_stats,
            audio_cues=[
                "Tavern ambiance with growing tension",
                "Chair scraping and voices rising",
                "Crash of breaking furniture",
                "Crowd shouting and cheering",
                "Restoration of order or continued chaos"
            ],
            context_integration={
                'location': 'tavern',
                'npcs_created': 3,
                'plot_hooks': [complication],
                'reputation_effects': 'depends on party actions'
            },
            difficulty_level=DifficultyLevel.MEDIUM,
            estimated_duration=30
        )

    async def _generate_mysterious_npc(self, request: GenerationRequest) -> GeneratedContent:
        """Generate a mysterious NPC with full background and voice."""
        npc_gen = self.npc_generators
        template = self.generation_templates['mysterious_npc']
        
        # Generate core identity
        background = random.choice(template['backgrounds'])
        motivation = random.choice(template['motivations'])
        quirk = random.choice(template['quirks'])
        
        # Generate appearance and personality
        name = await self._generate_fantasy_name()
        personality_traits = random.sample(npc_gen['personality_traits'], 3)
        physical_feature = random.choice(npc_gen['physical_features'])
        occupation = random.choice(npc_gen['occupations'])
        secret = random.choice(npc_gen['secrets'])
        
        # Generate relationships
        relationship_type = random.choice(npc_gen['relationships'])
        
        # Generate voice characteristics
        voice_profile = await self._generate_voice_profile()
        
        description = f"""
        **{name}** - The Mysterious {occupation.title()}
        
        **Appearance:**
        A {occupation} with {physical_feature}. They carry themselves with an air of mystery and seem to know more than they let on.
        
        **Personality:**
        - Primary traits: {', '.join(personality_traits)}
        - Notable quirk: {quirk}
        - Speaking style: {voice_profile['speaking_style']}
        
        **Background:**
        {background}
        
        **Current Motivation:**
        {motivation}
        
        **Secret:**
        They harbor a secret about their {secret}, which drives many of their actions.
        
        **Potential Relationship to Party:**
        Could become a {relationship_type} depending on how the interaction goes.
        """
        
        # Generate conversation starters and plot hooks
        conversation_hooks = [
            f"Approaches party with knowledge about their current quest",
            f"Offers cryptic warnings about dangers ahead",
            f"Requests help with something seemingly simple but actually complex",
            f"Recognizes one of the party members from their past"
        ]
        
        hook = random.choice(conversation_hooks)
        
        voice_notes = f"""
        **Voice Profile for {name}:**
        - Pitch: {voice_profile['pitch']}
        - Tone: {voice_profile['tone']}
        - Accent: {voice_profile['accent']}
        - Speech pattern: {voice_profile['speech_pattern']}
        - Emotional range: {voice_profile['emotional_range']}
        
        **Sample Dialogue:**
        "Ah, I couldn't help but notice... you have the look of people who've seen things. Interesting things. Perhaps we should talk."
        
        **Conversation Style:**
        - Speaks in implications rather than direct statements
        - Often pauses as if choosing words carefully
        - Knows things they shouldn't logically know
        - Changes subject when pressed for details
        """
        
        implementation_notes = f"""
        **DM Guidelines:**
        - Use {name} to advance plot or introduce complications
        - Their {secret} should be revealed gradually
        - They're motivated by {motivation.lower()}
        - Remember their quirk: {quirk}
        
        **Initial Approach:**
        {hook}
        
        **Long-term Role:**
        This NPC can serve as:
        - Information source (reliable but cryptic)
        - Quest giver with hidden agenda  
        - Recurring character with developing relationship
        - Plot twist reveal later in campaign
        
        **Roleplay Notes:**
        - Never give direct answers to direct questions
        - Show don't tell - let their actions reveal character
        - Use their quirk consistently
        - Build mystery gradually
        """
        
        npc_stats = {
            'name': name,
            'background': background,
            'occupation': occupation,
            'personality_traits': personality_traits,
            'physical_features': [physical_feature],
            'quirks': [quirk],
            'secrets': [secret],
            'motivations': [motivation],
            'voice_profile': voice_profile,
            'potential_relationships': [relationship_type],
            'conversation_hooks': conversation_hooks
        }
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.NPC,
            title=f"{name} - Mysterious {occupation.title()}",
            description=description,
            details=npc_stats,
            implementation_notes=implementation_notes,
            voice_notes=voice_notes,
            maps_data=None,
            encounter_stats=None,
            audio_cues=[
                "Mysterious entrance music",
                "Subtle background ambiance",
                "Dramatic chord for revelations",
                "Thoughtful pause music"
            ],
            context_integration={
                'npc_type': 'mysterious_ally',
                'plot_potential': 'high',
                'recurring_character': True,
                'information_source': True
            },
            difficulty_level=None,
            estimated_duration=20
        )

    async def _generate_side_quest(self, request: GenerationRequest) -> GeneratedContent:
        """Generate a complete side quest with NPCs and encounters."""
        template = self.generation_templates['side_quest']
        
        quest_type = random.choice(template['types'])
        complication = random.choice(template['complications'])
        
        # Generate quest giver
        quest_giver_name = await self._generate_fantasy_name()
        quest_giver_occupation = random.choice(['merchant', 'noble', 'priest', 'scholar', 'farmer'])
        
        # Generate quest details based on type
        quest_details = await self._generate_quest_details(quest_type, complication)
        
        # Generate rewards
        rewards = await self._generate_quest_rewards(request.context)
        
        description = f"""
        **Side Quest: {quest_details['title']}**
        
        **Quest Giver:** {quest_giver_name}, Local {quest_giver_occupation.title()}
        
        **Type:** {quest_type}
        
        **Initial Request:**
        {quest_details['initial_request']}
        
        **The Complication:**
        {complication}
        
        **Actual Situation:**
        {quest_details['actual_situation']}
        
        **Key Locations:**
        {chr(10).join(f"- {loc}" for loc in quest_details['locations'])}
        
        **Important NPCs:**
        {chr(10).join(f"- {npc}" for npc in quest_details['npcs'])}
        
        **Potential Rewards:**
        - Gold: {rewards['gold']}
        - Items: {rewards['items']}
        - Information: {rewards['information']}
        - Connections: {rewards['connections']}
        """
        
        implementation_notes = f"""
        **DM Guidelines:**
        
        **Hook Delivery:**
        {quest_giver_name} approaches the party at {quest_details['hook_location']}, appearing {quest_details['approach_mood']}.
        
        **Quest Stages:**
        1. Initial briefing and acceptance
        2. Investigation/travel phase  
        3. Complication reveal: {complication}
        4. Resolution phase
        5. Reward and consequences
        
        **Moral Dimensions:**
        {quest_details['moral_complexity']}
        
        **Time Pressure:**
        {quest_details['time_pressure']}
        
        **Failure Consequences:**
        {quest_details['failure_consequences']}
        
        **Success Variations:**
        - Complete success: Full rewards + reputation boost
        - Partial success: Reduced rewards but no penalties  
        - Creative solution: Bonus reward or future opportunities
        """
        
        quest_data = {
            'title': quest_details['title'],
            'type': quest_type,
            'quest_giver': {
                'name': quest_giver_name,
                'occupation': quest_giver_occupation,
                'motivation': quest_details['giver_motivation']
            },
            'stages': quest_details['stages'],
            'complications': [complication],
            'rewards': rewards,
            'estimated_sessions': quest_details['estimated_sessions'],
            'difficulty': quest_details['difficulty']
        }
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.QUEST,
            title=quest_details['title'],
            description=description,
            details=quest_data,
            implementation_notes=implementation_notes,
            voice_notes=f"Quest giver voice: {quest_giver_occupation} with {quest_details['giver_personality']} personality",
            maps_data=None,
            encounter_stats=None,
            audio_cues=[
                "Quest briefing music",
                "Travel/investigation theme",
                "Complication reveal sting",
                "Resolution music"
            ],
            context_integration={
                'quest_type': quest_type,
                'estimated_duration': quest_details['estimated_sessions'] * 180,  # minutes
                'npcs_introduced': len(quest_details['npcs']),
                'locations_visited': len(quest_details['locations'])
            },
            difficulty_level=DifficultyLevel(quest_details['difficulty']),
            estimated_duration=quest_details['estimated_sessions'] * 180
        )

    async def _generate_balanced_encounter(self, request: GenerationRequest) -> GeneratedContent:
        """Generate a balanced encounter based on party level and size."""
        party_level = request.context.get('party_level', 3)
        party_size = request.context.get('party_size', 4)
        encounter_type = request.parameters.get('encounter_type', 'combat')
        
        if encounter_type == 'combat':
            return await self._generate_combat_encounter(party_level, party_size, request)
        else:
            return await self._generate_social_encounter(party_level, party_size, request)

    async def _generate_combat_encounter(self, party_level: int, party_size: int, request: GenerationRequest) -> GeneratedContent:
        """Generate a balanced combat encounter."""
        encounter_builders = self.encounter_builders['combat_encounters']
        
        # Select terrain
        terrain_type = request.parameters.get('terrain', random.choice(list(encounter_builders['terrain_types'].keys())))
        terrain_data = encounter_builders['terrain_types'][terrain_type]
        
        # Select enemy group
        enemy_group = random.choice(list(encounter_builders['enemy_groups'].keys()))
        enemy_data = encounter_builders['enemy_groups'][enemy_group]
        
        # Calculate encounter difficulty
        target_cr = await self._calculate_target_cr(party_level, party_size, DifficultyLevel.MEDIUM)
        
        # Generate specific enemies
        enemies = await self._generate_enemy_composition(enemy_group, target_cr)
        
        # Generate tactical map
        tactical_map = await self._generate_tactical_map(terrain_type, terrain_data)
        
        description = f"""
        **Combat Encounter: {enemy_group.title()} in {terrain_type.title()}**
        
        **Setup:**
        The party encounters {enemies['description']} in {terrain_type} terrain.
        
        **Enemies:**
        {chr(10).join(f"- {enemy['name']}: AC {enemy['ac']}, HP {enemy['hp']}, Attack +{enemy['attack']}" for enemy in enemies['enemies'])}
        
        **Terrain Features:**
        {chr(10).join(f"- {feature}" for feature in terrain_data['features'])}
        
        **Tactical Elements:**
        {chr(10).join(f"- {element}" for element in terrain_data['tactical_elements'])}
        
        **Environmental Hazards:**
        {chr(10).join(f"- {hazard}" for hazard in terrain_data['environmental_hazards'])}
        
        **Enemy Tactics:**
        {chr(10).join(f"- {tactic}" for tactic in enemy_data['tactics'])}
        """
        
        encounter_stats = {
            'difficulty': DifficultyLevel.MEDIUM,
            'target_cr': target_cr,
            'enemies': enemies['enemies'],
            'terrain': terrain_type,
            'estimated_rounds': random.randint(4, 8),
            'victory_conditions': ['Defeat all enemies', 'Force retreat', 'Achieve objective'],
            'tactical_considerations': terrain_data['tactical_elements']
        }
        
        implementation_notes = f"""
        **Combat Flow:**
        1. Set the scene with terrain description
        2. Roll initiative when combat starts
        3. Use enemy tactics: {', '.join(enemy_data['tactics'])}
        4. Utilize terrain features for dynamic combat
        5. Consider environmental hazards each round
        
        **Scaling Options:**
        - Too Easy: Add reinforcements or environmental pressure
        - Too Hard: Have enemies retreat or make tactical errors
        
        **Loot Suggestions:**
        - {random.choice(['Weapons', 'Armor', 'Treasure', 'Information'])}
        - {random.choice(['Magical trinket', 'Useful consumables', 'Map or clue'])}
        """
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.ENCOUNTER,
            title=f"{enemy_group.title()} Encounter",
            description=description,
            details={'enemies': enemies, 'terrain': terrain_data, 'tactics': enemy_data},
            implementation_notes=implementation_notes,
            voice_notes=f"Enemy voices: {enemy_group} with {enemy_data['motivations'][0]} motivation",
            maps_data=tactical_map,
            encounter_stats=encounter_stats,
            audio_cues=[
                "Combat initiative music",
                "Tension building themes",
                "Victory/defeat resolution"
            ],
            context_integration={
                'encounter_type': 'combat',
                'difficulty_level': 'medium',
                'terrain_type': terrain_type,
                'enemy_type': enemy_group
            },
            difficulty_level=DifficultyLevel.MEDIUM,
            estimated_duration=45
        )

    async def _generate_plot_twist(self, request: GenerationRequest) -> GeneratedContent:
        """Generate a contextual plot twist."""
        plot_gen = self.plot_generators['plot_twists']
        
        # Select twist category based on current campaign elements
        twist_categories = ['identity_reveals', 'hidden_connections', 'false_assumptions']
        category = random.choice(twist_categories)
        
        base_twist = random.choice(plot_gen[category])
        
        # Customize twist based on campaign context
        customized_twist = await self._customize_plot_twist(base_twist, request.context)
        
        description = f"""
        **Plot Twist: {customized_twist['title']}**
        
        **The Revelation:**
        {customized_twist['revelation']}
        
        **How It's Revealed:**
        {customized_twist['revelation_method']}
        
        **Impact on Current Situation:**
        {customized_twist['immediate_impact']}
        
        **Long-term Consequences:**
        {chr(10).join(f"- {consequence}" for consequence in customized_twist['long_term_consequences'])}
        
        **Player Reactions to Consider:**
        {chr(10).join(f"- {reaction}" for reaction in customized_twist['expected_reactions'])}
        """
        
        implementation_notes = f"""
        **Timing:**
        {customized_twist['ideal_timing']}
        
        **Foreshadowing Elements:**
        Look back and emphasize these previous clues:
        {chr(10).join(f"- {clue}" for clue in customized_twist['foreshadowing'])}
        
        **Delivery Method:**
        {customized_twist['delivery_advice']}
        
        **Follow-up Scenes:**
        1. {customized_twist['immediate_followup']}
        2. {customized_twist['character_reactions']}
        3. {customized_twist['new_direction']}
        
        **Damage Control:**
        If players reject the twist: {customized_twist['backup_plan']}
        """
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.PLOT_TWIST,
            title=customized_twist['title'],
            description=description,
            details=customized_twist,
            implementation_notes=implementation_notes,
            voice_notes="Use dramatic pauses and emotional range for the revelation",
            maps_data=None,
            encounter_stats=None,
            audio_cues=[
                "Building tension music",
                "Revelation dramatic sting",
                "Emotional aftermath theme",
                "New direction music"
            ],
            context_integration={
                'twist_type': category,
                'campaign_impact': 'major',
                'requires_follow_up': True
            },
            difficulty_level=None,
            estimated_duration=15
        )

    async def _generate_cliffhanger(self, request: GenerationRequest) -> GeneratedContent:
        """Generate a dramatic cliffhanger ending."""
        cliffhanger_gen = self.plot_generators['cliffhangers']
        
        # Select type based on current session energy
        session_context = request.context
        energy_level = session_context.get('energy_level', 'medium')
        
        if energy_level == 'high':
            category = 'immediate_danger'
        elif energy_level == 'low':
            category = 'revelations'
        else:
            category = random.choice(['immediate_danger', 'revelations', 'decisions'])
        
        base_cliffhanger = random.choice(cliffhanger_gen[category])
        
        # Customize for current context
        customized = await self._customize_cliffhanger(base_cliffhanger, session_context, category)
        
        description = f"""
        **Session Cliffhanger: {customized['title']}**
        
        **The Setup:**
        {customized['setup']}
        
        **The Cliffhanger Moment:**
        {customized['cliffhanger_text']}
        
        **What Happens Next (DM Notes):**
        {customized['next_session_opening']}
        
        **Player Agency:**
        {customized['player_options']}
        """
        
        implementation_notes = f"""
        **Delivery Timing:**
        {customized['timing_advice']}
        
        **Dramatic Techniques:**
        - {customized['dramatic_technique']}
        - End with: "{customized['final_words']}"
        - Then immediately: "And that's where we'll end tonight's session."
        
        **Next Session Prep:**
        {customized['prep_notes']}
        
        **Player Homework:**
        Ask players to think about: {customized['player_homework']}
        
        **Resolution Options:**
        {chr(10).join(f"- {option}" for option in customized['resolution_paths'])}
        """
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.CLIFFHANGER,
            title=customized['title'],
            description=description,
            details=customized,
            implementation_notes=implementation_notes,
            voice_notes="Build tension gradually, then cut off at peak drama",
            maps_data=None,
            encounter_stats=None,
            audio_cues=[
                "Tension building music",
                "Dramatic crescendo",
                "Sudden stop/silence",
                "End credits music"
            ],
            context_integration={
                'cliffhanger_type': category,
                'session_ender': True,
                'next_session_hook': True
            },
            difficulty_level=None,
            estimated_duration=5
        )

    async def _enhance_current_scene(self, request: GenerationRequest) -> GeneratedContent:
        """Enhance the current scene with more drama."""
        current_scene = request.context.get('current_scene', 'unknown')
        scene_type = request.context.get('scene_type', 'social')
        drama_level = request.context.get('drama_level', 'low')
        
        enhancements = await self._generate_scene_enhancements(scene_type, drama_level, current_scene)
        
        description = f"""
        **Scene Enhancement: Making It More Dramatic**
        
        **Current Scene:** {current_scene}
        
        **Dramatic Elements to Add:**
        {chr(10).join(f"- {element}" for element in enhancements['elements'])}
        
        **Sensory Details:**
        - **Visual:** {enhancements['visual']}
        - **Audio:** {enhancements['audio']} 
        - **Emotional:** {enhancements['emotional']}
        
        **Raised Stakes:**
        {enhancements['stakes_escalation']}
        
        **Immediate Complications:**
        {chr(10).join(f"- {comp}" for comp in enhancements['complications'])}
        """
        
        implementation_notes = f"""
        **How to Implement:**
        
        **Gradual Introduction:**
        {enhancements['implementation_method']}
        
        **Player Reaction Opportunities:**
        {chr(10).join(f"- {opportunity}" for opportunity in enhancements['player_opportunities'])}
        
        **Pacing Notes:**
        {enhancements['pacing_advice']}
        
        **If It Goes Too Far:**
        {enhancements['scaling_back_method']}
        """
        
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=GenerationType.SCENE_ENHANCEMENT,
            title="Scene Dramatic Enhancement",
            description=description,
            details=enhancements,
            implementation_notes=implementation_notes,
            voice_notes="Adjust voice and pacing to match new dramatic level",
            maps_data=None,
            encounter_stats=None,
            audio_cues=enhancements.get('audio_cues', ['Dramatic music increase']),
            context_integration={
                'scene_type': scene_type,
                'enhancement_level': drama_level,
                'immediate_effect': True
            },
            difficulty_level=None,
            estimated_duration=10
        )

    # Helper methods for generation

    async def _generate_fantasy_name(self) -> str:
        """Generate a fantasy name."""
        first_syllables = ['Ael', 'Bel', 'Cal', 'Del', 'Fel', 'Gil', 'Hal', 'Kel', 'Lil', 'Mel', 'Nel', 'Pel', 'Ral', 'Sel', 'Tel', 'Vel', 'Wel', 'Zel']
        second_syllables = ['aran', 'beth', 'dan', 'eth', 'fon', 'geth', 'hen', 'ion', 'jos', 'ken', 'lon', 'mon', 'nen', 'oth', 'pen', 'ron', 'sen', 'ton', 'von', 'wen', 'yon', 'zen']
        
        return random.choice(first_syllables) + random.choice(second_syllables)

    async def _generate_voice_profile(self) -> Dict[str, str]:
        """Generate voice characteristics profile."""
        return {
            'pitch': random.choice(['high', 'medium', 'low']),
            'tone': random.choice(['warm', 'cold', 'neutral', 'gravelly', 'melodious']),
            'accent': random.choice(['local', 'foreign', 'noble', 'common', 'educated']),
            'speech_pattern': random.choice(['quick', 'deliberate', 'halting', 'flowing']),
            'emotional_range': random.choice(['expressive', 'reserved', 'dramatic', 'monotone']),
            'speaking_style': random.choice(['direct', 'cryptic', 'verbose', 'terse'])
        }

    async def _generate_quest_details(self, quest_type: str, complication: str) -> Dict[str, Any]:
        """Generate detailed quest information."""
        # This would be expanded with much more sophisticated quest generation
        quest_templates = {
            'Fetch quest with a twist': {
                'title': 'The Simple Retrieval',
                'initial_request': 'Retrieve a family heirloom from an abandoned house',
                'actual_situation': 'The house isn\'t abandoned and the "heirloom" is actually stolen goods',
                'locations': ['Abandoned Manor', 'Hidden Basement', 'Secret Tunnel'],
                'npcs': ['Nervous Quest Giver', 'Squatters in House', 'Original Owner'],
                'giver_motivation': 'Wants to fence stolen goods without getting caught',
                'giver_personality': 'nervous and shifty',
                'hook_location': 'tavern common room',
                'approach_mood': 'anxious and looking over their shoulder',
                'moral_complexity': 'Party must decide whether to return items to rightful owner or complete contract',
                'time_pressure': 'Original owner returns from travel in 3 days',
                'failure_consequences': 'Quest giver flees town, rightful owner accuses party of theft',
                'stages': ['Accept quest', 'Travel to location', 'Discover truth', 'Make moral choice', 'Deal with consequences'],
                'difficulty': 'easy',
                'estimated_sessions': 1
            }
        }
        
        return quest_templates.get(quest_type, quest_templates['Fetch quest with a twist'])

    async def _generate_quest_rewards(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate appropriate quest rewards."""
        party_level = context.get('party_level', 3)
        
        gold_amounts = {1: '50-100', 2: '100-200', 3: '200-400', 4: '400-800', 5: '800-1500'}
        base_gold = gold_amounts.get(party_level, '200-400')
        
        items = ['Healing potions', 'Masterwork weapon', 'Useful magic item', 'Rare components']
        information = ['Local rumors', 'Map to treasure', 'NPC contact', 'Faction intelligence']
        connections = ['Merchant discount', 'Noble favor', 'Guild membership', 'Safe passage']
        
        return {
            'gold': f"{base_gold} gold pieces",
            'items': random.choice(items),
            'information': random.choice(information),
            'connections': random.choice(connections)
        }

    async def _calculate_target_cr(self, party_level: int, party_size: int, difficulty: DifficultyLevel) -> float:
        """Calculate target CR for encounter."""
        # Simplified CR calculation
        base_cr = party_level * 0.25 * party_size
        
        difficulty_multipliers = {
            DifficultyLevel.EASY: 0.5,
            DifficultyLevel.MEDIUM: 1.0,
            DifficultyLevel.HARD: 1.5,
            DifficultyLevel.DEADLY: 2.0
        }
        
        return base_cr * difficulty_multipliers[difficulty]

    async def _generate_enemy_composition(self, enemy_group: str, target_cr: float) -> Dict[str, Any]:
        """Generate enemy composition for target CR."""
        # Simplified enemy generation
        enemy_templates = {
            'bandits': {
                'leader': {'name': 'Bandit Captain', 'cr': 2.0, 'ac': 15, 'hp': 65, 'attack': 5},
                'minion': {'name': 'Bandit', 'cr': 0.125, 'ac': 12, 'hp': 11, 'attack': 3}
            },
            'monsters': {
                'leader': {'name': 'Alpha Wolf', 'cr': 1.0, 'ac': 13, 'hp': 37, 'attack': 4},
                'minion': {'name': 'Wolf', 'cr': 0.25, 'ac': 13, 'hp': 11, 'attack': 4}
            }
        }
        
        template = enemy_templates.get(enemy_group, enemy_templates['bandits'])
        
        # Simple composition: 1 leader + minions to reach target CR
        leader = template['leader']
        minion = template['minion']
        
        remaining_cr = target_cr - leader['cr']
        minion_count = max(1, int(remaining_cr / minion['cr']))
        
        enemies = [leader]
        enemies.extend([minion] * minion_count)
        
        return {
            'description': f"1 {leader['name']} leading {minion_count} {minion['name']}{'s' if minion_count > 1 else ''}",
            'enemies': enemies,
            'total_cr': leader['cr'] + (minion['cr'] * minion_count)
        }

    async def _generate_tactical_map(self, terrain_type: str, terrain_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate tactical map layout."""
        return {
            'size': '30x30 feet',
            'terrain_type': terrain_type,
            'features': terrain_data['features'],
            'cover_locations': random.sample(terrain_data.get('tactical_elements', []), 2),
            'hazards': random.sample(terrain_data.get('environmental_hazards', []), 1),
            'elevation_changes': random.choice([True, False]),
            'entry_points': ['north', 'south', 'east', 'west'][:random.randint(2, 4)]
        }

    async def _customize_plot_twist(self, base_twist: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Customize plot twist for current campaign."""
        return {
            'title': f"Unexpected Revelation: {base_twist[:30]}...",
            'revelation': base_twist,
            'revelation_method': "Through overheard conversation between NPCs",
            'immediate_impact': "Current quest objectives become questionable",
            'long_term_consequences': [
                "Party must reevaluate their alliances",
                "Previous victories may have unintended consequences",
                "New quest opportunities arise"
            ],
            'expected_reactions': [
                "Shock and disbelief",
                "Anger at being deceived",
                "Excitement at plot development"
            ],
            'ideal_timing': "During a quiet moment when players feel secure",
            'foreshadowing': [
                "That NPC who seemed too helpful",
                "The convenient coincidences",
                "Information that was too easily obtained"
            ],
            'delivery_advice': "Reveal gradually, let players piece it together",
            'immediate_followup': "Allow for player reactions and questions",
            'character_reactions': "Show how NPCs respond to the revelation",
            'new_direction': "Present new quest options based on the twist",
            'backup_plan': "Scale it back to a smaller deception if needed"
        }

    async def _customize_cliffhanger(self, base_cliffhanger: str, context: Dict[str, Any], category: str) -> Dict[str, Any]:
        """Customize cliffhanger for current session."""
        return {
            'title': f"Session Cliffhanger: {base_cliffhanger[:30]}...",
            'setup': "Just as the party thinks they've resolved the situation...",
            'cliffhanger_text': base_cliffhanger,
            'next_session_opening': "Start with immediate action or decision",
            'player_options': "Multiple ways to respond to the situation",
            'timing_advice': "Wait for a moment of triumph or relief, then strike",
            'dramatic_technique': "Lower your voice, then pause dramatically",
            'final_words': base_cliffhanger,
            'prep_notes': "Prepare 3-4 different ways the situation could unfold",
            'player_homework': "How would their character react in this moment?",
            'resolution_paths': [
                "Direct confrontation",
                "Creative problem solving", 
                "Retreat and regroup",
                "Seek help from allies"
            ]
        }

    async def _generate_scene_enhancements(self, scene_type: str, current_drama: str, scene_description: str) -> Dict[str, Any]:
        """Generate enhancements to make scene more dramatic."""
        enhancements = {
            'elements': [],
            'visual': '',
            'audio': '',
            'emotional': '',
            'stakes_escalation': '',
            'complications': [],
            'implementation_method': '',
            'player_opportunities': [],
            'pacing_advice': '',
            'scaling_back_method': '',
            'audio_cues': []
        }
        
        if scene_type == 'social':
            enhancements.update({
                'elements': [
                    'Time pressure from approaching deadline',
                    'Unexpected arrival of important NPC',
                    'Hidden agendas revealed',
                    'Stakes raised with new information'
                ],
                'visual': 'Shadows lengthen, faces become more intense',
                'audio': 'Voices become hushed, urgent whispers',
                'emotional': 'Tension rises, trust becomes questioned',
                'stakes_escalation': 'What seemed like simple negotiation now affects entire communities',
                'complications': [
                    'Someone is lying about their identity',
                    'A third party has been listening',
                    'The real decision maker just arrived'
                ]
            })
        elif scene_type == 'exploration':
            enhancements.update({
                'elements': [
                    'Signs of recent activity',
                    'Environmental hazard activation',
                    'Discovery of something unexpected',
                    'Realization they\'re not alone'
                ],
                'visual': 'Shadows move unexpectedly, details become ominous',
                'audio': 'Strange sounds, echo of footsteps, distant voices',
                'emotional': 'Growing unease, sense of being watched'
            })
        
        # Add implementation advice
        enhancements.update({
            'implementation_method': f'Introduce elements gradually over next 10 minutes',
            'player_opportunities': [
                'Chance to investigate the new elements',
                'Opportunity for character moments',
                'Decisions that affect the outcome'
            ],
            'pacing_advice': 'Build tension slowly, then release with action or revelation',
            'scaling_back_method': 'If too intense, have comic relief or partial resolution',
            'audio_cues': ['Tension building music', 'Dramatic crescendo', 'Resolution theme']
        })
        
        return enhancements

    async def _generate_generic_content(self, request: GenerationRequest) -> GeneratedContent:
        """Generate generic content for unspecified requests."""
        return GeneratedContent(
            content_id=request.request_id,
            generation_type=request.generation_type,
            title=f"Generated {request.generation_type.value.title()}",
            description=f"Auto-generated {request.generation_type.value} content based on current context.",
            details={'type': request.generation_type.value, 'context': request.context},
            implementation_notes="Use this as a starting point and adapt as needed.",
            voice_notes=None,
            maps_data=None,
            encounter_stats=None,
            audio_cues=[],
            context_integration={},
            difficulty_level=None,
            estimated_duration=15
        )