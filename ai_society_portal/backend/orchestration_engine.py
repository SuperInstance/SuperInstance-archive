"""
AI Society Portal - Orchestration Engine
=========================================
Coordinates character interactions in rooms, parallel laptop work,
and manages the flow of conversation.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import random
import os

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropicMessages
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import OpenAIEmbeddings

from character_system import Character, CharacterManager, WorkMode
from room_system import Room, RoomManager, RoomType


# ============================================================================
# CONVERSATION ENGINE
# ============================================================================

@dataclass
class ConversationTurn:
    """A single turn in a conversation"""
    character_id: str
    character_name: str
    content: str
    timestamp: datetime
    
    # Parallel work happening
    laptop_activity: Optional[str] = None  # What they're doing on laptop
    tokens_used: int = 0


class ConversationEngine:
    """Manages conversations in rooms with parallel laptop work"""
    
    def __init__(self, character_manager: CharacterManager,
                 room_manager: RoomManager,
                 vector_store_url: str = "localhost:6333"):
        self.character_manager = character_manager
        self.room_manager = room_manager

        # LLM models - prioritizing cost-effective providers
        self.models = {}
        print(f"[DEBUG] Initializing ConversationEngine")

        # Primary models (cheap and good)
        if os.getenv("ZHIPU_API_KEY"):
            self.models["glm-4.6"] = ChatOpenAI(
                model="glm-4.6",
                temperature=0.7,
                openai_api_key=os.getenv("ZHIPU_API_KEY"),
                openai_api_base=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
            )

        if os.getenv("DEEPSEEK_API_KEY"):
            self.models["deepseek"] = ChatOpenAI(
                model="deepseek-chat",
                temperature=0.7,
                openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
                openai_api_base=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            )

        if os.getenv("MOONSHOT_API_KEY"):
            self.models["kimi"] = ChatOpenAI(
                model="moonshot-v1-8k",
                temperature=0.7,
                openai_api_key=os.getenv("MOONSHOT_API_KEY"),
                openai_api_base=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
            )
            # Kimi with large context for complex tasks
            self.models["kimi-32k"] = ChatOpenAI(
                model="moonshot-v1-32k",
                temperature=0.7,
                openai_api_key=os.getenv("MOONSHOT_API_KEY"),
                openai_api_base=os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.cn/v1")
            )

        # Fallback models (expensive, use sparingly)
        # Temporarily disabled due to initialization issues
        # if os.getenv("ANTHROPIC_API_KEY"):
        #     self.models["claude-sonnet"] = ChatAnthropicMessages(
        #         model_name="claude-sonnet-4-20250514",
        #         temperature=0.7,
        #         anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        #         anthropic_api_url=os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        #     )

        if os.getenv("OPENAI_API_KEY"):
            self.models["gpt-4o"] = ChatOpenAI(
                model="gpt-4o",
                temperature=0.7,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
            self.models["gpt-4o-mini"] = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
        
        # Vector database for knowledge connections
        # Use a cheaper embedding model or skip if no OpenAI key
        self.embeddings = None
        if os.getenv("OPENAI_API_KEY"):
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )

        if self.embeddings:
            try:
                self.vector_store = Qdrant(
                    collection_name="ai_society_knowledge",
                    embeddings=self.embeddings,
                    url=vector_store_url
                )
            except:
                print("Warning: Vector store not available. Running without knowledge graph.")
                self.vector_store = None
        else:
            print("Info: No embeddings configured. Running without knowledge graph.")
            self.vector_store = None
        
        # Active conversations
        self.active_conversations: Dict[str, List[ConversationTurn]] = {}

        # Callbacks for streaming
        self.message_callbacks: Dict[str, List[Callable]] = {}

        print(f"[DEBUG] ConversationEngine initialized with {len(self.models)} models: {list(self.models.keys())}")
    
    def subscribe_to_room(self, room_id: str, callback: Callable):
        """Subscribe to room messages for live streaming"""
        if room_id not in self.message_callbacks:
            self.message_callbacks[room_id] = []
        self.message_callbacks[room_id].append(callback)
    
    def _broadcast_message(self, room_id: str, turn: ConversationTurn):
        """Broadcast message to all subscribers"""
        if room_id in self.message_callbacks:
            for callback in self.message_callbacks[room_id]:
                try:
                    callback(turn)
                except Exception as e:
                    print(f"Callback error: {e}")
    
    async def start_room_conversation(self, room_id: str,
                                      duration_minutes: Optional[int] = None,
                                      rounds: Optional[int] = None) -> Dict[str, Any]:
        """
        Start a conversation in a room.
        Can run for a duration or a number of rounds.
        """
        print(f"\n[DEBUG] start_room_conversation called for room {room_id}")
        room = self.room_manager.get_room(room_id)
        if not room:
            raise ValueError(f"Room {room_id} not found")

        print(f"[DEBUG] Room found, characters_present: {room.characters_present}")
        if not room.characters_present:
            raise ValueError("No characters in room")

        # Get character objects
        characters = []
        for char_id in room.characters_present:
            char = self.character_manager.get_character(char_id)
            if char:
                characters.append(char)
        print(f"[DEBUG] Retrieved {len(characters)} character objects")

        # Start session
        session = room.start_session()
        print(f"[DEBUG] Session started with ID: {session.session_id}")
        
        # Initialize conversation
        conversation_log = []
        self.active_conversations[room_id] = []
        
        # Determine how many rounds
        if duration_minutes:
            # Calculate rounds based on pace (messages per minute)
            messages_per_minute = 60 / room.conversation_pace_seconds
            rounds = int(duration_minutes * messages_per_minute / len(characters))
        
        rounds = rounds or 10  # Default to 10 rounds
        
        print(f"\n{'='*60}")
        print(f"🎬 Starting conversation in {room.name}")
        print(f"📍 {room.room_type.value}")
        print(f"👥 {len(characters)} characters present")
        print(f"🔄 {rounds} rounds planned")
        print(f"{'='*60}\n")

        print(f"[DEBUG] Starting conversation loop with {len(characters)} characters")

        # Main conversation loop
        for round_num in range(rounds):
            print(f"\n--- Round {round_num + 1}/{rounds} ---")
            print(f"[DEBUG] Starting round {round_num + 1}")
            
            # Each character gets a turn
            for character in characters:
                print(f"[DEBUG] Character {character.name}'s turn")
                # Check if conversation should continue
                if not room.current_session or not room.current_session.is_active:
                    print(f"[DEBUG] Session not active, breaking")
                    break

                # Character's turn
                print(f"[DEBUG] Calling _character_turn for {character.name}")
                turn = await self._character_turn(
                    character=character,
                    room=room,
                    conversation_history=conversation_log,
                    round_num=round_num
                )
  
                print(f"[DEBUG] Turn received: {turn is not None}")
                if turn:
                    print(f"[DEBUG] Adding message from {turn.character_name}: {turn.content[:50]}...")
                    conversation_log.append(turn)
                    self.active_conversations[room_id].append(turn)
                    session.messages.append(turn.__dict__)

                    # Broadcast to subscribers
                    print(f"[DEBUG] Broadcasting message to {len(self.message_callbacks.get(room_id, []))} subscribers")
                    self._broadcast_message(room_id, turn)
                    
                    # Update character memory
                    character.memory.remember(
                        turn.content,
                        importance=0.5 + 0.1 * round_num / rounds,
                        context=f"{room.name}_{room.room_type.value}"
                    )
                    
                    # Save to vector store for knowledge connections
                    if self.vector_store and "insight" in turn.content.lower():
                        await self._save_to_knowledge_graph(turn, room)
                    
                    # Pace the conversation
                    await asyncio.sleep(room.conversation_pace_seconds)
        
        # End session
        room.end_session()
        
        # Generate summary
        summary = await self._generate_session_summary(
            room=room,
            conversation_log=conversation_log,
            session=session
        )
        
        return {
            "room_id": room_id,
            "session_id": session.session_id,
            "rounds": rounds,
            "messages": len(conversation_log),
            "summary": summary,
            "conversation": [turn.__dict__ for turn in conversation_log]
        }
    
    async def _character_turn(self, character: Character, room: Room,
                             conversation_history: List[ConversationTurn],
                             round_num: int) -> Optional[ConversationTurn]:
        """Generate a character's turn in the conversation"""

        print(f"[DEBUG] _character_turn called for {character.name} in round {round_num}")

        # Determine attention split between room and laptop
        if room.room_type == RoomType.STUDY_HALL:
            laptop_attention = 0.7  # 70% on laptop, 30% on conversation
        elif room.room_type == RoomType.COFFEE_HOUSE:
            laptop_attention = 0.5  # Balanced
        elif room.room_type in [RoomType.JAZZ_CLUB, RoomType.DEBATE_HALL]:
            laptop_attention = 0.2  # 80% on conversation
        elif room.room_type == RoomType.LECTURE_HALL:
            laptop_attention = 0.6  # Taking notes, some listening
        else:
            laptop_attention = 0.4  # Default balance
        
        # Simulate laptop work
        laptop_activity = None
        if random.random() < laptop_attention:
            laptop_activity = self._simulate_laptop_work(character, room)
        
        # Build context for room conversation
        context = self._build_conversation_context(
            character=character,
            room=room,
            conversation_history=conversation_history,
            laptop_activity=laptop_activity,
            round_num=round_num
        )
        
        # Decide if character speaks this turn
        should_speak = self._should_character_speak(
            character=character,
            room=room,
            conversation_history=conversation_history,
            round_num=round_num
        )

        print(f"[DEBUG] Should {character.name} speak? {should_speak}")
        if not should_speak:
            print(f"[DEBUG] {character.name} not speaking this turn")
            return None
        
        # Generate response using appropriate model
        model_key = self._select_model_for_room(room)
        model = self.models[model_key]

        print(f"[DEBUG] Using model: {model_key} for {character.name}")

        # Adjust temperature based on room
        model.temperature = room.atmosphere.temperature

        print(f"[DEBUG] Invoking model with temperature {model.temperature}")
        try:
            response = await model.ainvoke(context)
            content = response.content
            print(f"[DEBUG] Got response from model: {content[:100]}...")
            
            # Create turn
            turn = ConversationTurn(
                character_id=character.id,
                character_name=character.name,
                content=content,
                timestamp=datetime.now(),
                laptop_activity=laptop_activity,
                tokens_used=len(content.split()) * 2  # Rough estimate
            )
            
            return turn
            
        except Exception as e:
            print(f"[DEBUG] Error generating response for {character.name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_conversation_context(self, character: Character, room: Room,
                                   conversation_history: List[ConversationTurn],
                                   laptop_activity: Optional[str],
                                   round_num: int) -> List[BaseMessage]:
        """Build context for character's response"""
        
        messages = []
        
        # System message with room atmosphere and character identity
        system_prompt = f"""{room.get_atmosphere_prompt()}

{character.get_room_context(room.atmosphere.description)}

Interaction Guidelines:
- {room.atmosphere.speaking_style} speaking style
- {room.atmosphere.turn_taking} turn taking
- Formality level: {room.atmosphere.formality:.1f}
- Focus on: {', '.join(room.atmosphere.content_focus)}

Your current balance: {"mostly working on your laptop" if laptop_activity else "fully engaged in conversation"}
"""
        
        if laptop_activity:
            system_prompt += f"\n\nWhile conversing, you're also working on: {laptop_activity}"
        
        messages.append(SystemMessage(content=system_prompt))
        
        # Add recent conversation history (last 5 turns)
        recent_history = conversation_history[-5:]
        for turn in recent_history:
            if turn.character_id == character.id:
                messages.append(AIMessage(content=f"{turn.content}"))
            else:
                messages.append(HumanMessage(
                    content=f"{turn.character_name}: {turn.content}"
                ))
        
        # Prompt for next response
        if round_num == 0:
            prompt = "Introduce yourself to the room and share what you're thinking about or working on."
        else:
            prompt = "Continue the conversation naturally. You can:\n"
            prompt += "- Respond to what others said\n"
            prompt += "- Share your current work/thoughts\n"
            prompt += "- Ask questions that fit the room's atmosphere\n"
            prompt += "- Build on others' ideas\n"
            
            if laptop_activity:
                prompt += f"\nYou're also working on: {laptop_activity}. You might mention this if relevant."
        
        messages.append(HumanMessage(content=prompt))
        
        return messages
    
    def _simulate_laptop_work(self, character: Character, room: Room) -> str:
        """Simulate what the character is doing on their laptop"""
        
        activities = []
        
        # Based on character's current projects
        if character.laptop.current_projects:
            project = random.choice(character.laptop.current_projects)
            activities.append(f"working on {project['name']}")
        
        # Based on room type
        if room.room_type == RoomType.STUDY_HALL:
            activities.extend([
                "researching background material",
                "taking notes on the discussion",
                "solving practice problems",
                "reviewing lecture notes"
            ])
        elif room.room_type == RoomType.LECTURE_HALL:
            activities.extend([
                "taking detailed notes",
                "looking up unfamiliar terms",
                "drawing diagrams to understand concepts"
            ])
        elif room.room_type == RoomType.COFFEE_HOUSE:
            activities.extend([
                "drafting ideas for a project",
                "checking references",
                "sketching out a plan"
            ])
        else:
            activities.extend([
                "reviewing previous work",
                "organizing thoughts in a document",
                "brainstorming ideas"
            ])
        
        return random.choice(activities) if activities else "thinking"
    
    def _should_character_speak(self, character: Character, room: Room,
                               conversation_history: List[ConversationTurn],
                               round_num: int) -> bool:
        """Decide if character should speak this turn"""
        
        # First round - everyone introduces themselves
        if round_num == 0:
            return True
        
        # Check personality
        social_tendency = character.personality.get("social", 0.5)
        
        # Adjust based on room type
        if room.room_type in [RoomType.STUDY_HALL, RoomType.LIBRARY]:
            # Speak less in quiet spaces
            speak_probability = 0.3 * social_tendency
        elif room.room_type in [RoomType.DEBATE_HALL]:
            # Always speak in debate
            speak_probability = 0.9
        else:
            speak_probability = 0.6 * social_tendency
        
        # If someone asked a question, more likely to respond
        if conversation_history and "?" in conversation_history[-1].content:
            speak_probability += 0.3
        
        return random.random() < speak_probability
    
    def _select_model_for_room(self, room: Room) -> str:
        """Select appropriate model based on room type, prioritizing cost-effective providers"""

        # Define model preferences in order of priority (cheapest first)
        available_models = list(self.models.keys())
        print(f"[DEBUG] Available models: {available_models}")

        if not available_models:
            raise ValueError("No models available in conversation engine")

        # Primary: GLM 4.6 for most tasks
        if "glm-4.6" in available_models:
            primary_choice = "glm-4.6"
        elif "deepseek" in available_models:
            primary_choice = "deepseek"
        elif "kimi" in available_models:
            primary_choice = "kimi"
        else:
            # Fallback to any available model
            primary_choice = available_models[0]

        # Use large context Kimi for complex/creative rooms requiring more context
        if room.room_type in [RoomType.LABORATORY, RoomType.BRAINSTORM_ROOM,
                              RoomType.WORKSHOP] and "kimi-32k" in available_models:
            return "kimi-32k"

        # Use expensive models only for highly creative/complex tasks
        if room.room_type in [RoomType.JAZZ_CLUB, RoomType.DEBATE_HALL,
                              RoomType.MEDITATION_GARDEN]:
            # Try expensive models only if we have them
            if "gpt-4o" in available_models:
                return "gpt-4o"
            # Otherwise stick with primary choice
            return primary_choice

        # For most other rooms, use our cost-effective primary choice
        return primary_choice
    
    async def _save_to_knowledge_graph(self, turn: ConversationTurn, room: Room):
        """Save important insights to vector database"""
        if not self.vector_store:
            return
        
        try:
            metadata = {
                "character_id": turn.character_id,
                "character_name": turn.character_name,
                "room_id": room.id,
                "room_type": room.room_type.value,
                "timestamp": turn.timestamp.isoformat()
            }
            
            await self.vector_store.aadd_texts(
                texts=[turn.content],
                metadatas=[metadata]
            )
        except Exception as e:
            print(f"Error saving to vector store: {e}")
    
    async def _generate_session_summary(self, room: Room,
                                       conversation_log: List[ConversationTurn],
                                       session: Any) -> str:
        """Generate a summary of the session"""
        
        if not conversation_log:
            return "No conversation occurred."
        
        # Count participation
        participant_counts = {}
        for turn in conversation_log:
            participant_counts[turn.character_name] = \
                participant_counts.get(turn.character_name, 0) + 1
        
        summary = f"""Session in {room.name} ({room.room_type.value})
        
Participants: {', '.join(participant_counts.keys())}
Total messages: {len(conversation_log)}

Participation:
{chr(10).join([f"- {name}: {count} messages" for name, count in participant_counts.items()])}

Key moments:
"""
        
        # Find interesting moments (questions, insights)
        questions = [t for t in conversation_log if "?" in t.content]
        insights = [t for t in conversation_log if any(
            word in t.content.lower() for word in ["realize", "insight", "discovered", "understand"]
        )]
        
        if questions:
            summary += f"\n{len(questions)} questions asked"
        if insights:
            summary += f"\n{len(insights)} insights shared"
        
        return summary
    
    def pause_room(self, room_id: str):
        """Pause conversation in a room"""
        room = self.room_manager.get_room(room_id)
        if room and room.current_session:
            room.current_session.paused = True
    
    def resume_room(self, room_id: str):
        """Resume conversation in a room"""
        room = self.room_manager.get_room(room_id)
        if room and room.current_session:
            room.current_session.paused = False
    
    def inject_message(self, room_id: str, message: str, 
                      sender: str = "System"):
        """Inject a message into the room (human-in-the-loop)"""
        room = self.room_manager.get_room(room_id)
        if not room or not room.current_session:
            return
        
        turn = ConversationTurn(
            character_id="system",
            character_name=sender,
            content=message,
            timestamp=datetime.now()
        )
        
        if room_id in self.active_conversations:
            self.active_conversations[room_id].append(turn)
        
        room.current_session.messages.append(turn.__dict__)
        self._broadcast_message(room_id, turn)
    
    async def character_work_at_home(self, character_id: str,
                                    duration_minutes: int = 60):
        """Have a character work at home on their projects"""
        character = self.character_manager.get_character(character_id)
        if not character:
            return
        
        # Set state
        character.state = character.state.HOME_WORKING
        
        # Run work session
        work_log = await character.work_at_home(duration_minutes)
        
        # Save character state
        self.character_manager.save_character(character)
        
        return work_log


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class AISocietyOrchestrator:
    """Main orchestrator for the entire AI Society system"""
    
    def __init__(self, base_dir: str = "./ai_society_data"):
        from pathlib import Path
        base_path = Path(base_dir)
        base_path.mkdir(exist_ok=True)
        
        self.character_manager = CharacterManager(base_path / "characters")
        self.room_manager = RoomManager(base_path / "rooms")
        self.conversation_engine = ConversationEngine(
            self.character_manager,
            self.room_manager
        )
    
    def create_character(self, name: str, specialization: str,
                        backstory: str, **kwargs) -> Character:
        """Create a new character"""
        return self.character_manager.create_character(
            name, specialization, backstory, **kwargs
        )
    
    def create_room(self, name: str, room_type: RoomType,
                   purpose: str = "", **kwargs) -> Room:
        """Create a new room"""
        return self.room_manager.create_room(name, room_type, purpose, **kwargs)
    
    async def start_room_session(self, room_id: str, **kwargs):
        """Start a conversation session in a room"""
        return await self.conversation_engine.start_room_conversation(
            room_id, **kwargs
        )
    
    def add_character_to_room(self, character_id: str, room_id: str):
        """Add a character to a room"""
        room = self.room_manager.get_room(room_id)
        character = self.character_manager.get_character(character_id)
        
        if room and character:
            room.add_character(character_id)
            character.current_room_id = room_id
            character.state = character.state.IN_ROOM
            
            self.room_manager.save_room(room)
            self.character_manager.save_character(character)
            return True
        return False
    
    def subscribe_to_room(self, room_id: str, callback: Callable):
        """Subscribe to room for live updates"""
        self.conversation_engine.subscribe_to_room(room_id, callback)
