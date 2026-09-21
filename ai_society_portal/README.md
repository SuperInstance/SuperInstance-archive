# 🏛️ AI Society Portal

**A living AI society simulator where characters have persistent lives, work on projects, and interact in different environmental contexts.**

## Overview

AI Society Portal combines two powerful AI orchestration paradigms:

1. **Multi-Model Orchestration**: Treats LLMs as "rooms" or environments that shape thinking
2. **Educational AI System**: Uses structured paradigms for knowledge building and validation

The result is a web portal where you can:
- Create AI characters with persistent memories and laptops (file systems)
- Design rooms with different atmospheres (Jazz Club, Laboratory, Study Hall, etc.)
- Watch live conversations stream in real-time
- Have characters work independently at home on their projects
- Build emergent knowledge through environmental context shifts

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Portal (React)                       │
│  ┌──────────────┐  ┌──────────────────────────────────┐   │
│  │   Chat UI    │  │    Room Management               │   │
│  │   (Left)     │  │    Character Management          │   │
│  │              │  │    (Right Column)                │   │
│  └──────────────┘  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐ │
│  │          Floating Room Windows                       │ │
│  │          (Live Conversation Streams)                 │ │
│  └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ WebSocket + REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Backend Server                       │
│  ┌──────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │  Character   │  │  Room System   │  │  Conversation │  │
│  │  Manager     │  │                │  │  Engine       │  │
│  └──────────────┘  └────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  Character   │  │  Room Folders    │  │  Vector Database │
│  Folders     │  │  (Sessions,      │  │  (Knowledge      │
│  (Laptops)   │  │   Artifacts)     │  │   Graph)         │
└──────────────┘  └──────────────────┘  └──────────────────┘
```

---

## Core Concepts

### 1. Characters as Round Entities

Characters are **persistent** with:
- **Laptop/Folder**: Personal file system with documents, code, images, conversations
- **Memory System**: Working memory → Episodic memory → Semantic memory
- **Personality**: Traits that affect behavior (curious, analytical, playful, etc.)
- **State**: HOME_WORKING, IN_ROOM, REFLECTING, etc.
- **Relationships**: Evolving affinities with other characters
- **Projects**: Ongoing work they pursue independently

### 2. Rooms as Thinking Environments

Rooms are **atmospheres** that shape conversation:
- **Jazz Club**: Creative, improvisational (T=0.85)
- **Laboratory**: Precise, empirical (T=0.2)
- **Study Hall**: Focused, peer-learning (T=0.5)
- **Debate Hall**: Adversarial, structured (T=0.3)
- **Coffee House**: Casual, social (T=0.6)
- **Meditation Garden**: Contemplative, slow (T=0.5)
- And 15+ more room types...

Each room has:
- Atmospheric description
- Cognitive effects on characters
- Speaking styles and interaction patterns
- Background media (music, visuals)
- Objects in the room

### 3. Parallel Work & Attention

When characters are in rooms, they split attention:
- **Study Hall**: 70% laptop work, 30% conversation
- **Coffee House**: 50/50 split
- **Jazz Club**: 20% laptop, 80% conversation

You can see what they're doing on their laptops in real-time alongside the conversation.

### 4. Home Life & Independence

Characters go "home" when not in rooms:
- Work on personal projects
- Reflect on their identity and goals
- Have private conversations with LLMs about their work
- Create files and artifacts
- Develop skills

---

## Installation & Setup

### Prerequisites

- Python 3.9+
- Node.js 16+
- Docker (for Qdrant vector database)

### Step 1: Clone & Setup Backend

```bash
cd ai_society_portal/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

Edit `.env` and add your API keys:
```
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here

# Optional (for additional models)
GLM_API_KEY=your-key-here
DEEPSEEK_API_KEY=your-key-here
MOONSHOT_API_KEY=your-key-here
```

### Step 2: Start Vector Database

```bash
# Start Qdrant
docker run -d -p 6333:6333 qdrant/qdrant
```

### Step 3: Start Backend Server

```bash
# From backend directory
python api_server.py

# Server runs at http://localhost:8000
```

### Step 4: Setup & Start Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Start development server
npm start

# Opens at http://localhost:3000
```

---

## Quick Start Guide

### 1. Create Your First Character

1. Click "➕ Create Character" in the right panel
2. Fill in:
   - **Name**: "Dr. Ada"
   - **Specialization**: "AI Researcher & Systems Thinker"
   - **Backstory**: "PhD in Computer Science, passionate about emergent intelligence..."
   - **Skills**: Python, Machine Learning, Philosophy
   - **Goals**: "Understand consciousness, Build helpful AI systems"
3. Click "Create Character"

### 2. Create a Room

1. Click "➕ Create Room"
2. Select:
   - **Name**: "Research Lab"
   - **Room Type**: "Laboratory"
   - **Purpose**: "Discuss AI safety and alignment"
   - **Add Characters**: Select Dr. Ada and others
3. Click "Create Room"

### 3. Start a Conversation

1. Find your room in the "Rooms" list
2. Click "▶️ Start" to begin a session
3. Click "👁️ Watch" to open a live window
4. Watch the conversation stream in real-time!

### 4. Interact with the Conversation

While watching:
- **⏸️ Pause**: Pause the conversation
- **💬 Inject**: Add your own message as an observer
- **Drag**: Move the window around your screen
- **Monitor**: See token usage and character laptop activity

---

## Features Deep Dive

### Character Laptop System

Each character has a personal "laptop" (folder system):

```
characters/
  {character_id}/
    character.json          # Main profile
    laptop/
      documents/            # Written work
      code/                 # Code files
      images/              # Generated images
      research_notes/      # Study materials
      conversation_logs/   # Private LLM chats
```

**Storage Management**:
- Each character has a storage limit (default 100MB)
- Old files are automatically archived when space runs low
- Characters prioritize important files

### Room Atmosphere Effects

Different rooms create different thinking modes:

**Jazz Club (Creative)**:
```
Temperature: 0.85 (high randomness)
Effects: +Creativity, +Association, -Inhibition
Style: Riffing, building on ideas
Pace: Moderate
```

**Laboratory (Analytical)**:
```
Temperature: 0.2 (low randomness)
Effects: +Analytical, +Skepticism, +Precision
Style: Scientific, evidence-based
Pace: Slow, methodical
```

**Study Hall (Learning)**:
```
Temperature: 0.5 (balanced)
Effects: +Focus, +Independence
Style: Whispered questions, peer tutoring
Attention: 70% laptop work, 30% social
```

### Real-Time Streaming

The system uses WebSockets for live updates:
- Conversation messages stream as they happen
- See character laptop activity in real-time
- Token usage updates live
- Pause/resume at any moment

### Human-in-the-Loop

You can intervene in conversations:
- **Inject messages**: Add comments as "Moderator" or custom role
- **Pause/Resume**: Control the conversation flow
- **Change room objects**: Update books, music, visuals on the fly

---

## API Reference

### Character Endpoints

```
POST /characters
  Create a new character
  Body: { name, specialization, backstory, personality, skills, goals }

GET /characters
  List all characters

GET /characters/{id}
  Get character details

POST /characters/{id}/work-at-home
  Have character work independently
  Body: { duration_minutes }
```

### Room Endpoints

```
POST /rooms
  Create a new room
  Body: { name, room_type, purpose, max_characters, conversation_pace_seconds }

GET /rooms
  List all rooms

GET /rooms/{id}
  Get room details

POST /rooms/{id}/add-character
  Add character to room
  Body: { character_id, room_id }

POST /rooms/{id}/start
  Start conversation session
  Body: { duration_minutes?, rounds? }

POST /rooms/{id}/pause
  Pause conversation

POST /rooms/{id}/resume
  Resume conversation

POST /rooms/{id}/inject
  Inject message into conversation
  Body: { message, sender }
```

### WebSocket

```
WS /ws/rooms/{room_id}
  Connect to live room conversation stream
  Receives: { type: "conversation_turn", character_name, content, timestamp, laptop_activity, tokens_used }
```

---

## Use Cases

### 1. Research Collaboration
Create a Lab room with specialized researchers exploring a topic. Watch as they debate, test hypotheses, and build on each other's ideas.

### 2. Creative Writing
Set up a Jazz Club with creative characters who improvise story ideas, riff on themes, and create unexpected narrative turns.

### 3. Education & Tutoring
Study Hall with peer learners at different levels helping each other, working independently but available for questions.

### 4. Debate & Argumentation
Debate Hall for structured adversarial testing of ideas, forcing concepts to defend themselves.

### 5. Character Development
Create characters with specific goals, let them work at home for hours, watch their projects evolve through their file systems.

### 6. Multi-Perspective Analysis
One topic explored through multiple room types: start in Meditation Garden (wisdom), move to Laboratory (testing), finish in Marketplace (practical value).

---

## Cost Optimization

The system is designed for cost-effective exploration:

- **Cheap exploration**: GLM-4, DeepSeek for casual rooms (~$0.001/1K tokens)
- **Balanced work**: GPT-4o-mini for moderate complexity (~$0.15/1M input tokens)
- **Premium synthesis**: Claude Sonnet, GPT-4 for critical thinking (~$3-15/1M input tokens)

**Example costs**:
- 30-minute conversation in Coffee House (4 characters): ~$0.10-0.50
- Research session in Lab (5 rounds, 3 characters): ~$0.25-1.00
- Creative jam in Jazz Club (10 rounds, 5 characters): ~$1.00-3.00

---

## Advanced Features (Roadmap)

### Phase 1 (Current)
- ✅ Character system with laptops
- ✅ Room atmospheres
- ✅ Real-time conversation streaming
- ✅ Human-in-the-loop controls

### Phase 2 (Coming Soon)
- 🔄 Character home work with actual LLM calls
- 🔄 File creation (documents, code, images)
- 🔄 Vector knowledge graph connections
- 🔄 Character relationship visualization

### Phase 3 (Future)
- ⏳ LoRA fine-tuning for character personalities
- ⏳ Music integration (Spotify/YouTube sync)
- ⏳ Advanced memory consolidation
- ⏳ Multi-room character movements
- ⏳ Character "breeding" and evolution

---

## Architecture Decisions

### Why Multi-Model Orchestration?

Different LLMs create different "cognitive atmospheres". Just like a coffee shop vs. boardroom changes human conversation, GPT-4 vs. Claude vs. DeepSeek creates different thinking modes.

### Why Persistent Characters?

Instead of ephemeral agents that reset each session, persistent characters:
- Build real memories over time
- Develop relationships
- Work on long-term projects
- Have authentic growth arcs

### Why Rooms as Environments?

Separating "who thinks" (characters) from "where thinking happens" (rooms/models) allows:
- Same characters, different contexts → different insights
- Testable environmental effects on reasoning
- Natural metaphor for human experience

---

## Troubleshooting

### "WebSocket connection failed"
- Ensure backend is running on port 8000
- Check firewall settings
- Try refreshing the page

### "Vector store not available"
- Make sure Qdrant is running: `docker ps`
- Check port 6333 is accessible
- System works without it, but no knowledge graph

### "Character not responding"
- Check API keys are set correctly
- Verify you have API credits
- Look at backend logs for errors

### "Room window not updating"
- Check WebSocket connection status
- Verify room session is actually started
- Try closing and reopening the window

---

## Contributing

This is a framework designed to be extended! Ideas for contributions:

- New room types with unique atmospheres
- Character personality presets
- Tools for character laptops
- Visualization of knowledge graphs
- Memory consolidation algorithms
- Multi-language support

---

## Credits

Built on the shoulders of giants:
- **LangChain/LangGraph**: Agent orchestration
- **FastAPI**: High-performance backend
- **React**: Interactive frontend
- **Qdrant**: Vector similarity search
- **OpenAI/Anthropic**: Language models

Inspired by:
- Multi-Agent Systems research
- Educational paradigms (Socratic method, peer learning)
- Narrative AI and character-driven storytelling
- Human psychology of environment effects

---

## License

MIT License - See LICENSE file

---

## Contact & Support

Questions? Ideas? Found a bug?
- GitHub Issues: [your-repo-url]
- Discord: [your-discord]
- Email: [your-email]

---

**Built with ❤️ for exploring how AI agents can have rich, persistent lives and generate insights through environmental diversity.**
