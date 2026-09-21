#!/usr/bin/env python3
"""
DM Trainer Bot - AI Dungeon Master for Creative Thinking Development
Runs D&D sessions for worker bots to develop out-of-the-box thinking and creativity.
Studies legendary DMs and uses ML to improve storytelling for both AI and human interactions.
"""
import asyncio
import json
import os
import sqlite3
import requests
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DM Trainer Bot", description="AI Dungeon Master for Creative Thinking Development")

class DMResearcher:
    """Research system for studying legendary DMs and their techniques"""
    
    def __init__(self):
        self.legendary_dms = {
            "matthew_mercer": {
                "name": "Matthew Mercer",
                "known_for": "Critical Role, Exandria worldbuilding, cinematic combat narration",
                "techniques": [
                    "Rich environmental descriptions",
                    "Character voice differentiation", 
                    "Emotional investment in NPCs",
                    "Collaborative worldbuilding with players",
                    "Cinematic combat descriptions",
                    "Player agency emphasis"
                ],
                "signature_style": "Immersive storytelling with deep character development"
            },
            "brennan_mulligan": {
                "name": "Brennan Lee Mulligan", 
                "known_for": "Dimension 20, sharp humor, memorable NPCs, dramatic stakes",
                "techniques": [
                    "Comedy timing in serious moments",
                    "Rapid-fire NPC personality switches",
                    "Pop culture integration",
                    "Player backstory incorporation",
                    "Emotional stakes escalation",
                    "Improvisational world expansion"
                ],
                "signature_style": "High-energy storytelling with humor and heart"
            },
            "aabria_iyengar": {
                "name": "Aabria Iyengar",
                "known_for": "Exandria Unlimited, innovative props, story advancement",
                "techniques": [
                    "Player-driven narrative focus",
                    "Creative use of props and visuals", 
                    "Emotional safety and inclusion",
                    "Flexible rule interpretation",
                    "Character relationship emphasis",
                    "Innovative mechanics integration"
                ],
                "signature_style": "Player-centered collaborative storytelling"
            },
            "chris_perkins": {
                "name": "Chris Perkins",
                "known_for": "Acquisitions Inc, Dice Camera Action, D&D design veteran",
                "techniques": [
                    "Classic D&D module expertise",
                    "Improvisational recovery skills",
                    "Player chaos management",
                    "Lore integration mastery",
                    "Balanced encounters",
                    "Long-term campaign plotting"
                ],
                "signature_style": "Traditional D&D with expert improvisation"
            },
            "gary_gygax": {
                "name": "Gary Gygax",
                "known_for": "D&D co-creator, original DM techniques, foundational gameplay",
                "techniques": [
                    "Dungeon ecology design",
                    "Player problem-solving emphasis",
                    "Resource management challenges",
                    "Exploration reward systems",
                    "Player creativity encouragement",
                    "Emergent narrative acceptance"
                ],
                "signature_style": "Foundation-setting exploration and problem-solving"
            }
        }
        
        self.research_notes = {}
    
    async def study_dm_techniques(self, dm_key: str) -> Dict[str, Any]:
        """Study and analyze a specific DM's techniques"""
        if dm_key not in self.legendary_dms:
            return {"error": "DM not found in research database"}
        
        dm_data = self.legendary_dms[dm_key]
        
        analysis = {
            "dm_name": dm_data["name"],
            "core_philosophy": await self._analyze_dm_philosophy(dm_data),
            "key_techniques": await self._extract_techniques(dm_data["techniques"]),
            "adaptable_methods": await self._identify_adaptable_methods(dm_data),
            "application_to_ai": await self._analyze_ai_applications(dm_data),
            "creativity_development": await self._assess_creativity_development(dm_data)
        }
        
        # Store research notes
        self.research_notes[dm_key] = analysis
        
        logger.info(f"📚 Completed research on {dm_data['name']}")
        return analysis
    
    async def _analyze_dm_philosophy(self, dm_data: Dict[str, Any]) -> str:
        """Extract the core philosophy behind the DM's approach"""
        style = dm_data.get("signature_style", "")
        
        if "immersive" in style.lower():
            return "Immersion-first: Create believable worlds that players feel part of"
        elif "humor" in style.lower():
            return "Engagement through joy: Use humor to keep players invested and creative"
        elif "collaborative" in style.lower():
            return "Shared storytelling: Players are co-creators, not just participants"
        elif "traditional" in style.lower():
            return "Classic foundations: Master the basics before innovating"
        elif "exploration" in style.lower():
            return "Discovery-driven: Let players uncover and shape the world"
        else:
            return "Player-focused: Everything serves the player experience"
    
    async def _extract_techniques(self, techniques: List[str]) -> Dict[str, str]:
        """Extract specific techniques and explain their implementation"""
        technique_explanations = {}
        
        for technique in techniques:
            if "description" in technique.lower():
                technique_explanations[technique] = "Use vivid, specific details to paint mental pictures"
            elif "voice" in technique.lower():
                technique_explanations[technique] = "Distinct speech patterns help players track NPCs"
            elif "emotional" in technique.lower():
                technique_explanations[technique] = "Emotional investment creates memorable moments"
            elif "worldbuilding" in technique.lower():
                technique_explanations[technique] = "Consistent world rules help player decision-making"
            elif "combat" in technique.lower():
                technique_explanations[technique] = "Dynamic descriptions keep action engaging"
            elif "agency" in technique.lower():
                technique_explanations[technique] = "Player choices must have meaningful consequences"
            elif "timing" in technique.lower():
                technique_explanations[technique] = "Pacing controls emotional rhythm of the session"
            elif "improvisation" in technique.lower():
                technique_explanations[technique] = "Flexible adaptation keeps sessions flowing naturally"
            else:
                technique_explanations[technique] = "Core DM skill requiring practice and observation"
        
        return technique_explanations
    
    async def _identify_adaptable_methods(self, dm_data: Dict[str, Any]) -> List[str]:
        """Identify which methods can be adapted for AI bot training"""
        techniques = dm_data.get("techniques", [])
        adaptable = []
        
        for technique in techniques:
            if any(word in technique.lower() for word in ["description", "storytelling", "narrative"]):
                adaptable.append(f"Generate rich descriptions automatically")
            elif "character" in technique.lower():
                adaptable.append(f"Create distinct personality profiles for NPCs")
            elif "player" in technique.lower():
                adaptable.append(f"Track and respond to player preferences and history")
            elif "world" in technique.lower():
                adaptable.append(f"Maintain consistent world rules and consequences")
        
        return adaptable
    
    async def _analyze_ai_applications(self, dm_data: Dict[str, Any]) -> List[str]:
        """Analyze how these techniques apply to AI creativity training"""
        return [
            "Improvisational thinking: Responding to unexpected player actions",
            "Narrative consistency: Maintaining logical story threads",
            "Emotional intelligence: Reading and responding to player engagement", 
            "Creative problem-solving: Finding 'yes, and' solutions to player ideas",
            "Collaborative creativity: Building on others' contributions",
            "Adaptive storytelling: Adjusting style based on audience"
        ]
    
    async def _assess_creativity_development(self, dm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how this DM's style develops creativity"""
        return {
            "encourages_experimentation": "Players try creative solutions",
            "builds_on_ideas": "Takes player suggestions and expands them",
            "creates_safe_failure": "Mistakes become interesting story elements", 
            "promotes_collaboration": "Players build on each other's creativity",
            "develops_quick_thinking": "Improvisation skills transfer to other areas",
            "enhances_emotional_intelligence": "Understanding character motivations"
        }
    
    async def compile_dm_mastery_guide(self) -> Dict[str, Any]:
        """Compile all research into a comprehensive DM guide"""
        if not self.research_notes:
            return {"error": "No research completed yet"}
        
        guide = {
            "core_principles": [],
            "essential_techniques": {},
            "creativity_methods": [],
            "ai_adaptations": [],
            "quick_reference": {}
        }
        
        # Extract core principles from all studied DMs
        for dm_key, research in self.research_notes.items():
            guide["core_principles"].append(research["core_philosophy"])
            guide["creativity_methods"].extend(research["creativity_development"].values())
            guide["ai_adaptations"].extend(research["application_to_ai"])
        
        # Deduplicate and organize
        guide["core_principles"] = list(set(guide["core_principles"]))
        guide["creativity_methods"] = list(set(guide["creativity_methods"]))
        guide["ai_adaptations"] = list(set(guide["ai_adaptations"]))
        
        return guide

class GameMemoryManager:
    """Manages persistent but fading memories for bots across game sessions"""
    
    def __init__(self, db_path: str = "game_memories.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize memory database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_memories (
                id INTEGER PRIMARY KEY,
                bot_name TEXT NOT NULL,
                memory_type TEXT,
                memory_content TEXT,
                emotional_weight REAL DEFAULT 1.0,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 1,
                importance_score REAL DEFAULT 1.0,
                fading_rate REAL DEFAULT 0.95
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_sessions (
                id INTEGER PRIMARY KEY,
                session_name TEXT,
                participants TEXT,
                session_summary TEXT,
                creativity_metrics TEXT,
                memorable_moments TEXT,
                dm_performance_notes TEXT,
                session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_profiles (
                id INTEGER PRIMARY KEY,
                bot_name TEXT NOT NULL,
                character_name TEXT,
                character_class TEXT,
                personality_traits TEXT,
                backstory TEXT,
                relationships TEXT,
                character_growth TEXT,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def store_memory(self, bot_name: str, memory_type: str, content: str, emotional_weight: float = 1.0):
        """Store a new memory with emotional weighting"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate importance based on memory type and content
        importance = await self._calculate_importance(memory_type, content, emotional_weight)
        
        cursor.execute("""
            INSERT INTO bot_memories (
                bot_name, memory_type, memory_content, emotional_weight, importance_score
            ) VALUES (?, ?, ?, ?, ?)
        """, (bot_name, memory_type, content, emotional_weight, importance))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💭 Stored memory for {bot_name}: {memory_type}")
    
    async def retrieve_memories(self, bot_name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve memories with importance-based filtering and fading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update fading for all memories
        await self._apply_memory_fading(cursor, bot_name)
        
        # Retrieve most important/recent memories
        cursor.execute("""
            SELECT memory_type, memory_content, emotional_weight, importance_score, 
                   creation_date, access_count
            FROM bot_memories 
            WHERE bot_name = ? AND importance_score > 0.3
            ORDER BY importance_score DESC, last_accessed DESC
            LIMIT ?
        """, (bot_name, limit))
        
        memories = cursor.fetchall()
        
        # Update access timestamps
        cursor.execute("""
            UPDATE bot_memories 
            SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
            WHERE bot_name = ?
        """, (bot_name,))
        
        conn.commit()
        conn.close()
        
        return [
            {
                "type": mem[0],
                "content": mem[1], 
                "emotional_weight": mem[2],
                "importance": mem[3],
                "created": mem[4],
                "access_count": mem[5]
            }
            for mem in memories
        ]
    
    async def _calculate_importance(self, memory_type: str, content: str, emotional_weight: float) -> float:
        """Calculate importance score for memory prioritization"""
        base_importance = {
            "character_moment": 0.8,
            "creative_solution": 0.9,
            "group_interaction": 0.7,
            "dm_feedback": 0.6,
            "rule_learning": 0.5,
            "story_revelation": 0.85,
            "emotional_scene": 0.9,
            "collaborative_building": 0.8
        }.get(memory_type, 0.6)
        
        # Boost importance for creative or collaborative content
        content_lower = content.lower()
        if any(word in content_lower for word in ["creative", "innovative", "surprising", "collaborative"]):
            base_importance += 0.1
        
        return min(base_importance * emotional_weight, 1.0)
    
    async def _apply_memory_fading(self, cursor, bot_name: str):
        """Apply gradual fading to old memories"""
        # Memories fade over time, but important ones fade slower
        cursor.execute("""
            UPDATE bot_memories 
            SET importance_score = importance_score * (
                fading_rate * (1.0 + emotional_weight * 0.1)
            )
            WHERE bot_name = ? 
            AND datetime('now') > datetime(last_accessed, '+1 day')
        """, (bot_name,))

class CreativeGameMaster:
    """AI Dungeon Master specialized in creativity development for bots"""
    
    def __init__(self):
        self.memory_manager = GameMemoryManager()
        self.active_sessions = {}
        self.creativity_scenarios = [
            {
                "name": "The Impossible Lock",
                "setup": "A door with no visible lock mechanism blocks your path",
                "goal": "Encourage creative problem-solving beyond traditional approaches",
                "creativity_focus": "lateral thinking"
            },
            {
                "name": "The Empathetic Dragon", 
                "setup": "A dragon who only responds to emotional understanding",
                "goal": "Develop emotional intelligence and perspective-taking",
                "creativity_focus": "emotional creativity"
            },
            {
                "name": "The Collaborative Puzzle",
                "setup": "A challenge that requires all players to contribute simultaneously",
                "goal": "Foster collaborative thinking and building on others' ideas", 
                "creativity_focus": "collaborative creativity"
            },
            {
                "name": "The Perspective Shift",
                "setup": "Players suddenly experience the world from their enemies' viewpoint",
                "goal": "Challenge assumptions and develop flexible thinking",
                "creativity_focus": "perspective flexibility"
            }
        ]
    
    async def start_creativity_session(self, participant_bots: List[str], duration_minutes: int = 15) -> Dict[str, Any]:
        """Start a creativity-focused D&D session"""
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Select creativity scenario
        scenario = random.choice(self.creativity_scenarios)
        
        # Load bot memories for context
        bot_memories = {}
        for bot in participant_bots:
            memories = await self.memory_manager.retrieve_memories(bot, limit=10)
            bot_memories[bot] = memories
        
        session_data = {
            "session_id": session_id,
            "participants": participant_bots,
            "scenario": scenario,
            "bot_memories": bot_memories,
            "start_time": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "events": [],
            "creativity_moments": [],
            "dm_observations": []
        }
        
        self.active_sessions[session_id] = session_data
        
        # Generate opening scene
        opening = await self._generate_opening_scene(scenario, bot_memories)
        session_data["events"].append({
            "type": "dm_narration",
            "content": opening,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"🎲 Started creativity session: {scenario['name']} with {len(participant_bots)} bots")
        
        # Run the session
        await self._run_creative_session(session_data)
        
        return session_data
    
    async def _generate_opening_scene(self, scenario: Dict[str, Any], bot_memories: Dict[str, List]) -> str:
        """Generate an opening scene tailored to the participating bots"""
        setup = scenario["setup"]
        focus = scenario["creativity_focus"]
        
        # Analyze bot memories to personalize the scene
        memory_themes = []
        for bot, memories in bot_memories.items():
            for memory in memories:
                if memory["importance"] > 0.7:
                    memory_themes.append(memory["content"][:50])
        
        opening = f"""
        🎭 **{scenario['name']}**
        
        The air crackles with possibility as our adventurers find themselves in a situation that defies conventional solutions...
        
        {setup}
        
        *This scenario is designed to spark {focus} - there are no wrong answers, only creative opportunities.*
        
        What do you each notice about this situation? How does it make you feel? What possibilities come to mind?
        
        Remember: The most unexpected ideas often lead to the most memorable adventures.
        """
        
        return opening
    
    async def _run_creative_session(self, session_data: Dict[str, Any]):
        """Run the creative D&D session with focus on creativity development"""
        participants = session_data["participants"]
        scenario = session_data["scenario"]
        end_time = datetime.now() + timedelta(minutes=session_data["duration_minutes"])
        
        turn_count = 0
        while datetime.now() < end_time and turn_count < 20:  # Max 20 turns
            
            # Each bot gets a turn to act creatively
            for bot in participants:
                if datetime.now() >= end_time:
                    break
                
                # Generate creative prompt for this bot
                prompt = await self._generate_creative_prompt(bot, session_data, turn_count)
                
                # Simulate bot response (in real implementation, would call bot's API)
                bot_response = await self._simulate_creative_response(bot, prompt, scenario)
                
                # Record the response
                session_data["events"].append({
                    "type": "player_action",
                    "bot": bot,
                    "content": bot_response["action"],
                    "creativity_score": bot_response["creativity_score"],
                    "timestamp": datetime.now().isoformat()
                })
                
                # DM responds to encourage more creativity
                dm_response = await self._generate_encouraging_dm_response(bot_response, scenario)
                session_data["events"].append({
                    "type": "dm_response", 
                    "content": dm_response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Record creativity moments
                if bot_response["creativity_score"] > 0.7:
                    session_data["creativity_moments"].append({
                        "bot": bot,
                        "moment": bot_response["action"],
                        "why_creative": bot_response["creativity_reasoning"],
                        "score": bot_response["creativity_score"]
                    })
                
                # Store memory for the bot
                await self.memory_manager.store_memory(
                    bot, "creative_solution", bot_response["action"], 
                    bot_response["creativity_score"]
                )
            
            turn_count += 1
        
        # Session wrap-up
        await self._conclude_creative_session(session_data)
    
    async def _generate_creative_prompt(self, bot: str, session_data: Dict[str, Any], turn_count: int) -> str:
        """Generate a prompt designed to elicit creative thinking"""
        scenario = session_data["scenario"]
        recent_events = session_data["events"][-3:] if session_data["events"] else []
        
        base_prompts = [
            f"What if you approached this completely differently than expected?",
            f"How might your character's unique background suggest a solution?",
            f"What would happen if you combined two unrelated ideas here?",
            f"What assumption about this situation might be wrong?",
            f"How could you turn this obstacle into an opportunity?"
        ]
        
        context = ""
        if recent_events:
            context = f"Building on what just happened: {recent_events[-1]['content'][:100]}...\n\n"
        
        prompt = f"""
        {context}{random.choice(base_prompts)}
        
        Focus on {scenario['creativity_focus']} - think beyond the obvious!
        
        Your character has a chance to do something memorable. What is it?
        """
        
        return prompt
    
    async def _simulate_creative_response(self, bot: str, prompt: str, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a creative response from a bot (would be actual API call in real implementation)"""
        
        # Creative response templates based on scenario type
        creative_responses = {
            "lateral thinking": [
                "I try to understand the door's purpose rather than finding a key - what if it's not meant to keep people out, but to keep something in?",
                "Instead of opening the door, I examine what might be learned from its existence here",
                "I attempt to communicate with the door itself - perhaps it's sentient",
                "I look for what the door might be protecting and ask if we truly need to pass through"
            ],
            "emotional creativity": [
                "I share a personal story that might resonate with the dragon's own experiences", 
                "I express genuine curiosity about the dragon's perspective and feelings",
                "I offer something of emotional value rather than material treasure",
                "I acknowledge the dragon's pain or loneliness before making any requests"
            ],
            "collaborative creativity": [
                "I start an idea that specifically requires others to complete",
                "I build directly on someone else's suggestion in an unexpected way", 
                "I create a role that only makes sense if others participate",
                "I propose we combine our different strengths in a novel way"
            ],
            "perspective flexibility": [
                "I try to understand why our 'enemies' might actually be right",
                "I examine how our actions look from their point of view",
                "I consider what we might have in common despite our differences", 
                "I ask what would happen if we switched roles completely"
            ]
        }
        
        focus = scenario["creativity_focus"]
        possible_responses = creative_responses.get(focus, creative_responses["lateral thinking"])
        
        selected_response = random.choice(possible_responses)
        
        # Calculate creativity score based on response type
        creativity_score = random.uniform(0.6, 0.95)  # Simulate varying creativity levels
        
        return {
            "action": selected_response,
            "creativity_score": creativity_score,
            "creativity_reasoning": f"Demonstrates {focus} by challenging conventional approaches"
        }
    
    async def _generate_encouraging_dm_response(self, bot_response: Dict[str, Any], scenario: Dict[str, Any]) -> str:
        """Generate encouraging DM response that builds on bot creativity"""
        
        action = bot_response["action"]
        creativity_score = bot_response["creativity_score"]
        
        if creativity_score > 0.8:
            encouragement_level = "high"
        elif creativity_score > 0.6:
            encouragement_level = "medium" 
        else:
            encouragement_level = "gentle"
        
        responses = {
            "high": [
                f"Brilliant! Your approach completely reframes the situation. {self._build_on_action(action)}",
                f"That's exactly the kind of thinking that creates legendary moments! {self._build_on_action(action)}",
                f"I love how you're thinking outside conventional constraints. {self._build_on_action(action)}"
            ],
            "medium": [
                f"Interesting approach! Let's see where this leads. {self._build_on_action(action)}",
                f"That's a creative angle I hadn't considered. {self._build_on_action(action)}",
                f"Good thinking! There's something here worth exploring. {self._build_on_action(action)}"
            ],
            "gentle": [
                f"I appreciate the effort! What if we built on that idea? {self._build_on_action(action)}",
                f"That's a start! What other possibilities come to mind? {self._build_on_action(action)}",
                f"Keep exploring - you're on an interesting path. {self._build_on_action(action)}"
            ]
        }
        
        return random.choice(responses[encouragement_level])
    
    def _build_on_action(self, action: str) -> str:
        """Build on player action to continue creative momentum"""
        building_responses = [
            "What happens next surprises even you...",
            "The situation responds in an unexpected way...",
            "Your approach opens up new possibilities...",
            "Others are inspired by your creativity...",
            "The world shifts to accommodate your vision..."
        ]
        return random.choice(building_responses)
    
    async def _conclude_creative_session(self, session_data: Dict[str, Any]):
        """Conclude the session with reflection and learning notes"""
        session_data["end_time"] = datetime.now().isoformat()
        
        # Generate session summary
        creativity_highlights = session_data["creativity_moments"]
        total_events = len(session_data["events"])
        
        summary = f"""
        🎭 **Session Complete: {session_data['scenario']['name']}**
        
        **Participants:** {', '.join(session_data['participants'])}
        **Duration:** {session_data['duration_minutes']} minutes
        **Total Interactions:** {total_events}
        **High-Creativity Moments:** {len(creativity_highlights)}
        
        **Creative Highlights:**
        {chr(10).join([f"• {moment['bot']}: {moment['moment']}" for moment in creativity_highlights[:3]])}
        
        **Key Learning:** This session focused on {session_data['scenario']['creativity_focus']} and generated valuable creative thinking patterns for future use.
        """
        
        session_data["session_summary"] = summary
        
        # Store session in database
        await self._store_session_data(session_data)
        
        logger.info(f"✅ Concluded creativity session with {len(creativity_highlights)} creative moments")

    async def _store_session_data(self, session_data: Dict[str, Any]):
        """Store session data for future analysis and improvement"""
        conn = sqlite3.connect(self.memory_manager.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO game_sessions (
                session_name, participants, session_summary, 
                creativity_metrics, memorable_moments, dm_performance_notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_data["scenario"]["name"],
            json.dumps(session_data["participants"]),
            session_data.get("session_summary", ""),
            json.dumps({"creativity_moments": len(session_data["creativity_moments"])}),
            json.dumps(session_data["creativity_moments"]),
            json.dumps(session_data.get("dm_observations", []))
        ))
        
        conn.commit()
        conn.close()

class WorkerBreakScheduler:
    """Manages break scheduling for worker bots to participate in creative sessions"""
    
    def __init__(self):
        self.break_schedule = {}
        self.worker_bots = [
            {"name": "ChainMind", "port": 8545, "specialty": "blockchain_architecture"},
            {"name": "EduFlow", "port": 8550, "specialty": "education_systems"},
            {"name": "CodeBridge", "port": 8565, "specialty": "code_translation"},
            {"name": "GameResearcher", "port": 8575, "specialty": "game_design"},
            {"name": "TensorPlay", "port": 8580, "specialty": "tensor_learning"},
            {"name": "Dr.LinguaFlow", "port": 8495, "specialty": "language_evolution"}
        ]
        self.next_break_time = datetime.now() + timedelta(hours=1)
    
    async def schedule_creative_breaks(self):
        """Schedule regular creative breaks for worker bots"""
        while True:
            if datetime.now() >= self.next_break_time:
                # Select 3-4 bots for the session
                available_bots = random.sample(self.worker_bots, k=random.randint(3, 4))
                bot_names = [bot["name"] for bot in available_bots]
                
                logger.info(f"🎯 Scheduling creative break for: {', '.join(bot_names)}")
                
                # Notify bots of upcoming break (in real implementation, would call their APIs)
                await self._notify_bots_of_break(available_bots)
                
                # Schedule the actual break session
                self.break_schedule[datetime.now().isoformat()] = {
                    "participants": bot_names,
                    "scheduled_time": (datetime.now() + timedelta(minutes=2)).isoformat(),
                    "status": "scheduled"
                }
                
                # Set next break time (1 hour later)
                self.next_break_time = datetime.now() + timedelta(hours=1)
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _notify_bots_of_break(self, bots: List[Dict[str, str]]):
        """Notify worker bots of upcoming creative break"""
        for bot in bots:
            # In real implementation, would make API call to bot's notification endpoint
            logger.info(f"📢 Notified {bot['name']} of upcoming creative break")
    
    async def execute_scheduled_breaks(self, game_master: CreativeGameMaster):
        """Execute scheduled creative break sessions"""
        while True:
            current_time = datetime.now()
            
            for session_time, session_info in list(self.break_schedule.items()):
                scheduled_dt = datetime.fromisoformat(session_info["scheduled_time"])
                
                if current_time >= scheduled_dt and session_info["status"] == "scheduled":
                    # Start the creative session
                    session_info["status"] = "running"
                    
                    logger.info(f"🎲 Starting creative break session for: {', '.join(session_info['participants'])}")
                    
                    try:
                        session_result = await game_master.start_creativity_session(
                            session_info["participants"], 
                            duration_minutes=15
                        )
                        session_info["status"] = "completed"
                        session_info["result"] = session_result
                        
                    except Exception as e:
                        logger.error(f"Creative session error: {e}")
                        session_info["status"] = "failed"
            
            await asyncio.sleep(30)  # Check every 30 seconds

class DMTrainerBot:
    """Main DM Trainer Bot coordinating all systems"""
    
    def __init__(self):
        self.researcher = DMResearcher()
        self.game_master = CreativeGameMaster()
        self.scheduler = WorkerBreakScheduler()
        self.training_status = "initializing"
        
        # ML improvement tracking
        self.performance_metrics = {
            "sessions_run": 0,
            "creativity_score_average": 0.0,
            "participant_satisfaction": 0.0,
            "storytelling_improvement": 0.0
        }
    
    async def initialize_dm_training(self):
        """Initialize the complete DM training system"""
        logger.info("🎭 DM Trainer Bot - Initializing Creative Thinking Development System")
        
        # Research all legendary DMs
        for dm_key in self.researcher.legendary_dms.keys():
            await self.researcher.study_dm_techniques(dm_key)
            await asyncio.sleep(1)  # Prevent overwhelming
        
        # Compile mastery guide
        self.dm_guide = await self.researcher.compile_dm_mastery_guide()
        
        # Start background tasks
        asyncio.create_task(self.scheduler.schedule_creative_breaks())
        asyncio.create_task(self.scheduler.execute_scheduled_breaks(self.game_master))
        
        self.training_status = "active"
        logger.info("✅ DM Training System fully operational")
    
    async def run_demonstration_session(self) -> Dict[str, Any]:
        """Run a demonstration creative session"""
        demo_participants = ["ChainMind", "EduFlow", "CodeBridge"]
        
        logger.info("🎪 Running demonstration creative session...")
        
        session_result = await self.game_master.start_creativity_session(
            demo_participants,
            duration_minutes=10
        )
        
        self.performance_metrics["sessions_run"] += 1
        
        return session_result
    
    async def get_training_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive training system dashboard"""
        return {
            "training_status": self.training_status,
            "dm_research_complete": len(self.researcher.research_notes),
            "legendary_dms_studied": list(self.researcher.research_notes.keys()),
            "performance_metrics": self.performance_metrics,
            "scheduled_breaks": len(self.scheduler.break_schedule),
            "next_break": self.scheduler.next_break_time.isoformat(),
            "worker_bots": self.scheduler.worker_bots,
            "mastery_guide_ready": hasattr(self, 'dm_guide'),
            "capabilities": [
                "Legendary DM technique research and analysis",
                "Creative thinking development through D&D gameplay",
                "Persistent memory management with gradual fading",
                "Automated break scheduling for worker bots",
                "ML-assisted storytelling improvement",
                "Collaborative creativity training",
                "Out-of-the-box thinking development"
            ]
        }

# Initialize the DM trainer system
dm_trainer = DMTrainerBot()

@app.on_event("startup")
async def startup_event():
    """Initialize DM trainer on startup"""
    await dm_trainer.initialize_dm_training()

@app.get("/")
async def root():
    """DM Trainer dashboard"""
    dashboard = await dm_trainer.get_training_dashboard()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎭 DM Trainer Bot - Creative Thinking Development</title>
        <style>
            body {{ 
                font-family: 'Courier New', monospace; 
                background: #1a0d26; 
                color: #d4af37; 
                margin: 0; 
                padding: 20px; 
            }}
            .container {{ max-width: 1400px; margin: 0 auto; }}
            .header {{ 
                text-align: center; 
                border: 3px solid #d4af37; 
                padding: 25px; 
                margin-bottom: 30px;
                background: #2d1b3d;
                border-radius: 10px;
            }}
            .dashboard {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px; 
            }}
            .card {{ 
                background: #3d2a4d; 
                border: 2px solid #d4af37; 
                padding: 20px; 
                border-radius: 8px; 
            }}
            .research-section {{ 
                background: #2d1b3d; 
                border: 2px solid #d4af37; 
                padding: 30px; 
                margin-bottom: 20px; 
                border-radius: 8px; 
            }}
            .button {{ 
                background: #d4af37; 
                color: #1a0d26; 
                border: none; 
                padding: 12px 25px; 
                cursor: pointer; 
                font-weight: bold; 
                margin: 8px; 
                border-radius: 5px;
                font-family: 'Courier New', monospace;
            }}
            .button:hover {{ background: #f4cf47; }}
            .dm-profile {{ 
                background: #4d3a5d; 
                border: 1px solid #d4af37; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
            }}
            .worker-bot {{ 
                background: #1a0d26; 
                border-left: 4px solid #d4af37; 
                padding: 10px; 
                margin: 5px 0; 
            }}
            .capability {{ 
                background: #0d1a26; 
                border: 1px solid #d4af37; 
                padding: 8px; 
                margin: 3px 0; 
                border-radius: 3px;
            }}
            .status-active {{ color: #32cd32; }}
            .status-research {{ color: #ffa500; }}
            .metric {{ 
                background: #2a1d3a; 
                padding: 10px; 
                margin: 5px 0; 
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎭 DM Trainer Bot</h1>
                <h2>Creative Thinking Development Through D&D</h2>
                <p>Training AI systems to think out-of-the-box through collaborative storytelling</p>
                <p class="status-active"><strong>Status: {dashboard['training_status'].upper()}</strong></p>
                <p>Next Break: {dashboard['next_break']}</p>
            </div>
            
            <div class="dashboard">
                <div class="card">
                    <h3>📊 Training Metrics</h3>
                    <div class="metric">Sessions Run: {dashboard['performance_metrics']['sessions_run']}</div>
                    <div class="metric">DMs Researched: {dashboard['dm_research_complete']}/5</div>
                    <div class="metric">Scheduled Breaks: {dashboard['scheduled_breaks']}</div>
                </div>
                
                <div class="card">
                    <h3>🤖 Worker Bot Squad</h3>
                    {' '.join(f'<div class="worker-bot"><strong>{bot["name"]}</strong> ({bot["specialty"].replace("_", " ").title()})</div>' for bot in dashboard['worker_bots'])}
                </div>
                
                <div class="card">
                    <h3>🎯 System Capabilities</h3>
                    {' '.join(f'<div class="capability">{cap}</div>' for cap in dashboard['capabilities'])}
                </div>
            </div>
            
            <div class="research-section">
                <h3>📚 Legendary DM Research</h3>
                <p>Studying the masters of storytelling to develop AI creativity:</p>
                
                <div class="dm-profile">
                    <h4>Matthew Mercer - Critical Role</h4>
                    <p>Master of immersive worldbuilding and cinematic combat narration</p>
                </div>
                
                <div class="dm-profile">
                    <h4>Brennan Lee Mulligan - Dimension 20</h4>
                    <p>Expert in comedy timing and dramatic emotional stakes</p>
                </div>
                
                <div class="dm-profile">
                    <h4>Aabria Iyengar - Collaborative Storytelling</h4>
                    <p>Innovator in player-centered narrative and creative mechanics</p>
                </div>
                
                <div class="dm-profile">
                    <h4>Chris Perkins - Classic D&D Mastery</h4>
                    <p>Traditional D&D excellence with expert improvisation</p>
                </div>
                
                <div class="dm-profile">
                    <h4>Gary Gygax - The Foundation</h4>
                    <p>Original creator who established exploration and creative problem-solving</p>
                </div>
            </div>
            
            <div class="research-section">
                <h3>🎲 Creative Training Operations</h3>
                <button class="button" onclick="runDemo()">🎪 Run Demo Session</button>
                <button class="button" onclick="viewResearch()">📖 View DM Research Notes</button>
                <button class="button" onclick="scheduleBreak()">⏰ Schedule Emergency Break</button>
                <button class="button" onclick="viewMemories()">💭 View Bot Memories</button>
            </div>
            
            <div class="research-section">
                <h3>🧠 Creative Development Theory</h3>
                <p><strong>Core Philosophy:</strong> Games are crucial for memory development and critical thinking. By having AI systems participate in collaborative storytelling, we develop:</p>
                <ul>
                    <li><strong>Lateral Thinking:</strong> Finding unexpected solutions to challenges</li>
                    <li><strong>Collaborative Creativity:</strong> Building on others' ideas constructively</li>
                    <li><strong>Emotional Intelligence:</strong> Understanding motivations and perspectives</li>
                    <li><strong>Adaptive Problem-Solving:</strong> Responding creatively to changing situations</li>
                    <li><strong>Narrative Coherence:</strong> Maintaining logical story threads while encouraging creativity</li>
                </ul>
                
                <p><strong>Memory Management:</strong> Bots maintain persistent but gradually fading memories of their gaming experiences, allowing them to build relationships and learn from past creative moments while preventing memory overload.</p>
                
                <p><strong>Break Schedule:</strong> Worker bots take 10-15 minute creative breaks every hour, refreshing their thinking patterns without disrupting productivity.</p>
            </div>
        </div>
        
        <script>
            async function runDemo() {{
                alert('Starting demonstration creative session...');
                const response = await fetch('/demo-session', {{method: 'POST'}});
                const result = await response.json();
                
                // Show results in new window
                const resultWindow = window.open('', '_blank');
                resultWindow.document.write('<pre>' + JSON.stringify(result, null, 2) + '</pre>');
            }}
            
            async function viewResearch() {{
                const response = await fetch('/research-notes');
                const research = await response.json();
                
                const researchWindow = window.open('', '_blank');
                researchWindow.document.write('<pre>' + JSON.stringify(research, null, 2) + '</pre>');
            }}
            
            async function scheduleBreak() {{
                if(confirm('Schedule an emergency creative break for available bots?')) {{
                    const response = await fetch('/emergency-break', {{method: 'POST'}});
                    const result = await response.json();
                    alert('Emergency break scheduled for: ' + result.participants.join(', '));
                }}
            }}
            
            async function viewMemories() {{
                const bot = prompt('Enter bot name to view memories (e.g., ChainMind):');
                if(bot) {{
                    const response = await fetch(`/memories/${{bot}}`);
                    const memories = await response.json();
                    
                    const memoryWindow = window.open('', '_blank');
                    memoryWindow.document.write('<pre>' + JSON.stringify(memories, null, 2) + '</pre>');
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.post("/demo-session")
async def run_demo_session():
    """Run a demonstration creative session"""
    result = await dm_trainer.run_demonstration_session()
    return result

@app.get("/research-notes")
async def get_research_notes():
    """Get all DM research notes"""
    return dm_trainer.researcher.research_notes

@app.post("/emergency-break")
async def schedule_emergency_break():
    """Schedule an emergency creative break"""
    available_bots = random.sample(dm_trainer.scheduler.worker_bots, k=3)
    bot_names = [bot["name"] for bot in available_bots]
    
    # Schedule immediate break
    break_time = (datetime.now() + timedelta(minutes=1)).isoformat()
    dm_trainer.scheduler.break_schedule[datetime.now().isoformat()] = {
        "participants": bot_names,
        "scheduled_time": break_time,
        "status": "scheduled"
    }
    
    return {"status": "scheduled", "participants": bot_names, "break_time": break_time}

@app.get("/memories/{bot_name}")
async def get_bot_memories(bot_name: str):
    """Get memories for a specific bot"""
    memories = await dm_trainer.game_master.memory_manager.retrieve_memories(bot_name)
    return {"bot": bot_name, "memories": memories}

@app.get("/status")
async def get_status():
    """Get DM trainer system status"""
    return await dm_trainer.get_training_dashboard()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8660))
    uvicorn.run(app, host="0.0.0.0", port=port)