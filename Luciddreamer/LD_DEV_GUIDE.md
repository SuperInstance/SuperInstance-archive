# LucidDreamer.AI: Comprehensive Developer Guide
## Building AI-Powered Interactive Storytelling with Persistent Character Agents

**LangGraph v1.0.1 has emerged as the production standard for multi-agent AI systems**, proven at scale by companies like Uber (21K developer hours saved), Klarna (80% faster resolution), and Replit. This guide provides everything needed to build LucidDreamer.AI from development through production deployment.

## Getting started quickly

The fastest path to a working system combines **Ollama for local LLM serving** (10-minute setup), **LangGraph for agent orchestration** (production-proven framework), and **Qdrant for vector memory** (simplest deployment). Start with a supervisor pattern coordinating 2-3 specialized agents, add hierarchical memory gradually, and scale from there. Docker Compose brings everything together in one command.

---

## Production architecture patterns

### Multi-agent orchestration with LangGraph

**Current version**: LangGraph 1.0.1 (released October 20, 2025)

LangGraph provides four proven architectural patterns for multi-agent systems, each suited to different coordination needs. The **supervisor pattern** works best for storytelling systems with clear task delegation, while the **swarm pattern** enables dynamic peer-to-peer collaboration between character agents.

**Installation and setup**
```bash
pip install langgraph==1.0.1
pip install langchain-anthropic  # or langchain-openai
```

**Supervisor pattern implementation**
```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from typing import Literal

def supervisor_agent(state: MessagesState) -> Command[Literal["storyteller", "character_manager", END]]:
    """Central coordinator decides which agent handles each task"""
    response = model.invoke(state["messages"])

    return Command(
        goto=response["next_agent"],  # storyteller, character_manager, or END
        update={"messages": state["messages"]}
    )

def storyteller_agent(state: MessagesState) -> Command[Literal["supervisor"]]:
    """Generates narrative content based on current story state"""
    response = model.invoke(state["messages"])
    return Command(
        goto="supervisor",
        update={"messages": [response]}
    )

# Build the graph
workflow = StateGraph(MessagesState)
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("storyteller", storyteller_agent)
workflow.add_node("character_manager", character_manager_agent)
workflow.add_edge(START, "supervisor")

graph = workflow.compile()
```

**Swarm pattern for character interactions**

The swarm pattern enables characters to dynamically hand off control based on conversation flow, creating more natural multi-character interactions.

```python
from langgraph_swarm import create_handoff_tool, create_swarm
from langgraph.prebuilt import create_react_agent

# Character-specific agents with handoff capabilities
alice = create_react_agent(
    model,
    [dialogue_tool, create_handoff_tool(agent_name="Bob")],
    prompt="You are Alice, a curious scholar with high Openness (0.9).",
    name="Alice"
)

bob = create_react_agent(
    model,
    [action_tool, create_handoff_tool(agent_name="Alice")],
    prompt="You are Bob, a pragmatic warrior with high Conscientiousness (0.8).",
    name="Bob"
)

# Create swarm with persistent memory
from langgraph.checkpoint.memory import InMemorySaver
checkpointer = InMemorySaver()
workflow = create_swarm([alice, bob], default_active_agent="Alice")
app = workflow.compile(checkpointer=checkpointer)
```

**Hierarchical teams for complex systems**

For large-scale storytelling with multiple concurrent storylines, hierarchical teams organize agents into specialized groups with their own coordinators.

```python
# Team structure: Plot supervisor manages character teams
def plot_supervisor(state) -> Command[Literal["main_cast_team", "npc_team", "world_team", END]]:
    response = model.invoke(state["messages"])
    return Command(goto=response["next_team"])

# Each team has its own supervisor managing specialized agents
main_cast_graph = create_character_team(["protagonist", "deuteragonist", "antagonist"])
npc_graph = create_character_team(["merchant", "guard", "villager"])
world_graph = create_world_team(["environment", "lore", "events"])
```

### State management and persistence

**State schema design**
```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class StoryState(TypedDict):
    messages: Annotated[list, add_messages]  # Conversation history
    story_world: dict  # World state (locations, objects, events)
    active_characters: list  # Currently active character IDs
    narrative_arc: dict  # Plot progression tracking
    player_choices: list  # Decision history
    metadata: dict  # Session info, timestamps
```

**Persistence with checkpointing**
```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import AsyncPostgresSaver

# Development: In-memory checkpointing
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

# Production: PostgreSQL persistence
async with AsyncPostgresSaver.from_conn_string(
    "postgresql://user:pass@localhost/luciddreamer"
) as checkpointer:
    graph = workflow.compile(checkpointer=checkpointer)

    # Resume from specific point
    config = {"configurable": {"thread_id": "user-123"}}
    result = await graph.ainvoke(input, config=config)
```

### Performance characteristics

LangGraph's architecture delivers **O(1) scaling on conversation history** through checkpointing, **O(n) on active nodes** enabling parallel agent execution, and handles **independent threads efficiently**. Production deployments at Klarna process 2.5 million conversations with 80% faster resolution times compared to traditional systems.

---

## Technical implementation

### Local LLM deployment

**Ollama for development** (recommended starting point)

Ollama provides the simplest path to local LLM deployment with 10-minute setup time and broad model support.

```bash
# Installation
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.2  # 7B parameters, 8GB RAM required
ollama pull mistral   # Alternative with strong instruction-following

# Start server (runs on port 11434)
ollama serve
```

**OpenAI-compatible API**
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="dummy"  # Ollama doesn't require real keys
)

response = client.chat.completions.create(
    model="llama3.2",
    messages=[{"role": "user", "content": "Generate a fantasy story opening"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='', flush=True)
```

**vLLM for production** (when ready to scale)

vLLM delivers **19.3x higher throughput** and **8.4x lower latency** compared to Ollama, making it the clear choice for production deployments serving 100+ concurrent users.

```bash
# Installation
pip install vllm

# Docker deployment
docker run --runtime nvidia --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --gpu-memory-utilization 0.95
```

**Performance comparison**

| Metric | Ollama | vLLM | Ratio |
|--------|--------|------|-------|
| Peak tokens/sec | 41 | 793 | 19.3x |
| Peak requests/sec | 22 | 100 | 4.5x |
| P99 latency | 673ms | 80ms | 8.4x |
| Concurrent scaling | Plateaus at 32 | Linear to 256+ | - |

### Docker containerization

**Complete development stack**

```yaml
# docker-compose.yml
version: '3.8'

services:
  # LLM Backend
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  # Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage

  # Application
  app:
    build: ./app
    depends_on:
      - ollama
      - qdrant
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_URL=http://ollama:11434
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./app:/app

volumes:
  ollama-data:
  qdrant-data:
```

**Starting the stack**
```bash
docker-compose up -d

# Pull models
docker exec -it $(docker ps -q -f name=ollama) ollama pull llama3.2

# Check status
docker-compose ps
docker-compose logs -f app
```

### Vector databases for character memory

**Qdrant setup** (recommended for simplicity)

Qdrant offers the easiest deployment with excellent Python support and built-in clustering.

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Initialize client
client = QdrantClient(url="http://localhost:6333")

# Create collection for character memories
client.create_collection(
    collection_name="character_memories",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# Store memory
def store_memory(character_id: str, memory_text: str, memory_type: str):
    embedding = get_embedding(memory_text)  # from your embedding model

    client.upsert(
        collection_name="character_memories",
        points=[
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "character_id": character_id,
                    "text": memory_text,
                    "type": memory_type,  # episodic, semantic, procedural
                    "timestamp": time.time(),
                    "importance": calculate_importance(memory_text)
                }
            )
        ]
    )

# Retrieve relevant memories
def recall_memories(character_id: str, query: str, limit: int = 5):
    query_embedding = get_embedding(query)

    results = client.search(
        collection_name="character_memories",
        query_vector=query_embedding,
        query_filter={"must": [{"key": "character_id", "match": {"value": character_id}}]},
        limit=limit
    )

    return [hit.payload for hit in results]
```

**Pinecone for managed cloud**

Pinecone provides fully managed vector search with automatic scaling, ideal for production deployments without infrastructure management.

```python
from pinecone import Pinecone

pc = Pinecone(api_key="your-api-key")

# Create index
pc.create_index(
    name="character-memories",
    dimension=1536,
    metric="cosine",
    spec={"serverless": {"cloud": "aws", "region": "us-west-2"}}
)

index = pc.Index("character-memories")

# Upsert memories
index.upsert(vectors=[
    {
        "id": "mem-1",
        "values": embedding,
        "metadata": {"character_id": "alice", "type": "episodic", "text": memory_text}
    }
])

# Query
results = index.query(
    vector=query_embedding,
    filter={"character_id": {"$eq": "alice"}},
    top_k=5,
    include_metadata=True
)
```

### Real-time communication patterns

**WebSocket implementation for live agent interaction**

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        del self.active_connections[user_id]

    async def send_message(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/story/{user_id}")
async def story_websocket(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)

    try:
        while True:
            # Receive player action
            data = await websocket.receive_json()

            # Stream agent response
            async for chunk in agent_graph.astream(data):
                await websocket.send_json({
                    "type": "narrative_chunk",
                    "content": chunk
                })

            # Signal completion
            await websocket.send_json({"type": "complete"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)
```

**Server-Sent Events for simpler unidirectional streaming**

SSE provides a simpler alternative when bidirectional communication isn't needed, with automatic reconnection and standard HTTP compatibility.

```python
from sse_starlette.sse import EventSourceResponse

@app.post("/api/story/continue")
async def continue_story(request: StoryRequest):
    async def generate_narrative():
        async for chunk in story_generator.astream(request.prompt):
            yield {
                "event": "narrative",
                "data": json.dumps({"chunk": chunk}),
                "retry": 5000
            }
        yield {"event": "complete", "data": "{}"}

    return EventSourceResponse(
        generate_narrative(),
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
```

**Client-side consumption**
```javascript
const eventSource = new EventSource('/api/story/continue');

eventSource.addEventListener('narrative', (e) => {
    const data = JSON.parse(e.data);
    appendToStory(data.chunk);
});

eventSource.addEventListener('complete', () => {
    eventSource.close();
    enablePlayerInput();
});
```

### API design patterns

**Rate limiting with token bucket**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/agent/query")
@limiter.limit("100/minute")
async def query_agent(request: Request, query: QueryRequest):
    response = await agent_graph.ainvoke(query.messages)
    return response
```

**Error handling with retry logic**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception(lambda e: isinstance(e, (TimeoutError, ConnectionError))),
    reraise=True
)
async def call_llm_with_retry(prompt: str):
    response = await llm.generate(prompt)
    return response
```

---

## Character and memory systems

### Hierarchical memory architecture

The human memory system's three-level hierarchy—working, episodic, and semantic memory—provides the blueprint for character agents that remember, learn, and evolve.

**MIRIX-inspired memory implementation**

```python
class CharacterMemorySystem:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.working_memory = []  # Current context, 7±2 items
        self.episodic_memory = EpisodicMemory()  # Time-stamped events
        self.semantic_memory = SemanticMemory()  # Facts and knowledge
        self.procedural_memory = ProceduralMemory()  # Skills and procedures
        self.vector_store = qdrant_client

    async def process_event(self, event: dict):
        """Process new event through memory hierarchy"""
        # Add to working memory
        self.working_memory.append(event)

        # Maintain working memory capacity
        if len(self.working_memory) > 7:
            await self.consolidate_oldest()

        # Extract and store episodic memory
        episodic_entry = {
            "timestamp": time.time(),
            "event_type": event["type"],
            "summary": event["summary"],
            "participants": event["participants"],
            "location": event["location"],
            "emotional_impact": self.assess_emotional_impact(event)
        }

        embedding = await get_embedding(episodic_entry["summary"])
        self.vector_store.upsert(
            collection_name=f"episodic_{self.character_id}",
            points=[{
                "id": str(uuid.uuid4()),
                "vector": embedding,
                "payload": episodic_entry
            }]
        )

    async def consolidate_oldest(self):
        """Move working memory to long-term storage"""
        old_memory = self.working_memory.pop(0)

        # Extract semantic knowledge (facts)
        facts = extract_facts(old_memory)
        for fact in facts:
            self.semantic_memory.add(fact)

        # Extract procedural knowledge (how-to)
        procedures = extract_procedures(old_memory)
        for proc in procedures:
            self.procedural_memory.add(proc)

    async def recall_relevant_memories(self, context: str, limit: int = 5):
        """Retrieve memories relevant to current context"""
        query_embedding = await get_embedding(context)

        # Retrieve episodic memories
        episodic_results = self.vector_store.search(
            collection_name=f"episodic_{self.character_id}",
            query_vector=query_embedding,
            limit=limit
        )

        # Apply importance and recency weighting
        weighted_memories = []
        for hit in episodic_results:
            recency_weight = math.exp(-0.01 * (time.time() - hit.payload["timestamp"]))
            importance_weight = hit.payload["emotional_impact"]
            score = hit.score * recency_weight * importance_weight
            weighted_memories.append((score, hit.payload))

        weighted_memories.sort(reverse=True)
        return [mem for _, mem in weighted_memories[:limit]]
```

### Big Five personality model

The OCEAN personality model (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism) drives character behavior through computational trait influence.

**Personality implementation**
```python
from dataclasses import dataclass

@dataclass
class PersonalityTraits:
    openness: float  # 0-1: curiosity, imagination
    conscientiousness: float  # 0-1: organization, dependability
    extraversion: float  # 0-1: sociability, assertiveness
    agreeableness: float  # 0-1: compassion, cooperation
    neuroticism: float  # 0-1: emotional instability, anxiety

    def to_prompt(self) -> str:
        """Convert traits to natural language for LLM"""
        traits_desc = []

        if self.openness > 0.7:
            traits_desc.append("highly curious and imaginative")
        elif self.openness < 0.3:
            traits_desc.append("practical and conventional")

        if self.conscientiousness > 0.7:
            traits_desc.append("organized and detail-oriented")
        elif self.conscientiousness < 0.3:
            traits_desc.append("spontaneous and flexible")

        if self.extraversion > 0.7:
            traits_desc.append("outgoing and energetic")
        elif self.extraversion < 0.3:
            traits_desc.append("reserved and introspective")

        if self.agreeableness > 0.7:
            traits_desc.append("compassionate and cooperative")
        elif self.agreeableness < 0.3:
            traits_desc.append("competitive and skeptical")

        if self.neuroticism > 0.7:
            traits_desc.append("emotionally sensitive and reactive")
        elif self.neuroticism < 0.3:
            traits_desc.append("calm and emotionally stable")

        return f"Character personality: {', '.join(traits_desc)}"

    def influence_action_probability(self, action_type: str) -> float:
        """Modify action probability based on personality"""
        modifiers = {
            "explore": self.openness,
            "plan": self.conscientiousness,
            "socialize": self.extraversion,
            "cooperate": self.agreeableness,
            "worry": self.neuroticism
        }
        return modifiers.get(action_type, 0.5)

class Character:
    def __init__(self, name: str, personality: PersonalityTraits):
        self.name = name
        self.personality = personality
        self.memory = CharacterMemorySystem(character_id=name)
        self.emotion = EmotionalState()

    async def decide_action(self, context: str, options: list[str]) -> str:
        """Choose action influenced by personality and memory"""
        # Retrieve relevant memories
        memories = await self.memory.recall_relevant_memories(context)

        # Build prompt with personality and memories
        prompt = f"""
        {self.personality.to_prompt()}

        Recent relevant memories:
        {format_memories(memories)}

        Current situation: {context}

        Choose the most appropriate action from: {options}
        """

        # Weight options by personality
        weighted_options = [
            (opt, self.personality.influence_action_probability(opt))
            for opt in options
        ]

        # LLM decides with personality context
        response = await llm.invoke(prompt)
        return response.action
```

### Trait evolution mathematics

Characters evolve through experience using reinforcement-inspired learning rules.

**Experience-based trait modification**
```python
class TraitEvolution:
    def __init__(self, base_personality: PersonalityTraits, plasticity: float = 0.1):
        self.base_personality = base_personality
        self.current_personality = base_personality
        self.plasticity = plasticity  # Learning rate
        self.experience_history = []

    def update_traits(self, experience: dict):
        """Modify traits based on experience outcome"""
        trait_impacts = self.analyze_experience(experience)

        for trait_name, impact in trait_impacts.items():
            current_value = getattr(self.current_personality, trait_name)

            # Δtrait = plasticity × (outcome - expected) × relevance
            delta = self.plasticity * impact["surprise"] * impact["relevance"]

            # Apply update with bounds [0, 1]
            new_value = np.clip(current_value + delta, 0.0, 1.0)
            setattr(self.current_personality, trait_name, new_value)

        self.experience_history.append({
            "experience": experience,
            "trait_changes": trait_impacts,
            "timestamp": time.time()
        })

    def analyze_experience(self, experience: dict) -> dict:
        """Determine which traits are affected by experience"""
        impacts = {}

        if experience["type"] == "exploration_success":
            impacts["openness"] = {
                "surprise": experience["outcome"] - experience["expected"],
                "relevance": 0.8
            }

        if experience["type"] == "social_cooperation":
            impacts["agreeableness"] = {
                "surprise": experience["partner_reciprocation"] - 0.5,
                "relevance": 0.7
            }

        return impacts
```

### Emotional state tracking

The Valence-Arousal-Dominance (VAD) model provides three-dimensional emotional representation that evolves dynamically.

```python
class EmotionalState:
    def __init__(self):
        self.valence = 0.0  # -1 (negative) to +1 (positive)
        self.arousal = 0.3  # 0 (calm) to 1 (excited)
        self.dominance = 0.0  # -1 (submissive) to +1 (dominant)
        self.baseline = {"valence": 0.0, "arousal": 0.3, "dominance": 0.0}

    def process_event(self, event: dict, personality: PersonalityTraits):
        """Update emotional state based on event and personality"""
        # Evaluate event impact
        impact = self.evaluate_event(event)

        # Reactivity influenced by neuroticism
        reactivity = 1.0 + personality.neuroticism

        # Update valence
        self.valence += reactivity * impact["valence"]
        self.valence = np.clip(self.valence, -1.0, 1.0)

        # Update arousal
        self.arousal += reactivity * impact["arousal"]
        self.arousal = np.clip(self.arousal, 0.0, 1.0)

        # Decay toward baseline (emotional stability)
        stability = 1.0 - personality.neuroticism
        decay_rate = 0.1 * stability

        self.valence += decay_rate * (self.baseline["valence"] - self.valence)
        self.arousal += decay_rate * (self.baseline["arousal"] - self.arousal)

    def evaluate_event(self, event: dict) -> dict:
        """Assess emotional impact of event"""
        return {
            "valence": event.get("pleasantness", 0.0),
            "arousal": event.get("intensity", 0.0) * 0.5,
            "dominance": event.get("control", 0.0)
        }

    def to_description(self) -> str:
        """Convert state to natural language"""
        if self.valence > 0.5 and self.arousal > 0.6:
            return "excited and joyful"
        elif self.valence > 0.5 and self.arousal < 0.4:
            return "content and peaceful"
        elif self.valence < -0.5 and self.arousal > 0.6:
            return "angry or anxious"
        elif self.valence < -0.5 and self.arousal < 0.4:
            return "sad or melancholic"
        else:
            return "neutral"
```

### Memory consolidation

Importance scoring determines which memories persist long-term, following Ebbinghaus forgetting curves.

```python
def calculate_importance(memory: dict, personality: PersonalityTraits) -> float:
    """Multi-factor importance scoring"""
    # Recency (exponential decay)
    age_hours = (time.time() - memory["timestamp"]) / 3600
    recency_score = math.exp(-0.01 * age_hours)

    # Frequency (logarithmic)
    access_count = memory.get("access_count", 1)
    frequency_score = math.log(access_count + 1) / math.log(100)

    # Emotional salience
    emotional_score = abs(memory["emotional_valence"]) * memory["emotional_arousal"]

    # Personality-weighted relevance
    relevance_score = memory["relevance_to_goals"] * personality.conscientiousness

    # Weighted combination
    importance = (
        0.3 * recency_score +
        0.2 * frequency_score +
        0.3 * emotional_score +
        0.2 * relevance_score
    )

    return importance

async def consolidate_memories(memory_system: CharacterMemorySystem, threshold: float = 0.7):
    """Prune low-importance memories, strengthen important ones"""
    all_memories = await memory_system.get_all_episodic_memories()

    for memory in all_memories:
        importance = calculate_importance(memory, memory_system.character.personality)

        if importance < threshold:
            # Compress or remove low-importance memories
            await memory_system.compress_memory(memory["id"])
        else:
            # Strengthen important memories through rehearsal
            memory["access_count"] += 1
            await memory_system.update_memory(memory["id"], memory)
```

### Relationship graphs

Social networks between characters track dynamic relationships with trust, affinity, and history.

```python
import networkx as nx

class RelationshipGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_character(self, character_id: str, traits: dict):
        """Add character node"""
        self.graph.add_node(character_id, **traits)

    def update_relationship(self, from_id: str, to_id: str, interaction: dict):
        """Update relationship based on interaction"""
        if not self.graph.has_edge(from_id, to_id):
            self.graph.add_edge(from_id, to_id,
                strength=0.0,  # -1 to +1
                trust=0.5,     # 0 to 1
                familiarity=0.0,  # 0 to 1
                history=[]
            )

        edge_data = self.graph[from_id][to_id]

        # Update strength (affinity)
        outcome = interaction["outcome"]  # -1 to +1
        plasticity = 0.1
        edge_data["strength"] += plasticity * outcome * (1 - abs(edge_data["strength"]))
        edge_data["strength"] = np.clip(edge_data["strength"], -1.0, 1.0)

        # Update trust (consistency)
        expected = edge_data["strength"]
        actual = outcome
        consistency = 1.0 - abs(expected - actual)
        edge_data["trust"] += 0.05 * (consistency - edge_data["trust"])
        edge_data["trust"] = np.clip(edge_data["trust"], 0.0, 1.0)

        # Update familiarity
        edge_data["familiarity"] = min(1.0, edge_data["familiarity"] + 0.05)

        # Record interaction
        edge_data["history"].append({
            "timestamp": time.time(),
            "type": interaction["type"],
            "outcome": outcome
        })

    def get_relationship_summary(self, from_id: str, to_id: str) -> str:
        """Generate natural language relationship description"""
        if not self.graph.has_edge(from_id, to_id):
            return "strangers with no history"

        edge_data = self.graph[from_id][to_id]

        strength_desc = "close allies" if edge_data["strength"] > 0.7 else \
                       "friendly acquaintances" if edge_data["strength"] > 0.3 else \
                       "neutral contacts" if edge_data["strength"] > -0.3 else \
                       "rivals" if edge_data["strength"] > -0.7 else "bitter enemies"

        trust_desc = "with complete trust" if edge_data["trust"] > 0.8 else \
                     "with some trust" if edge_data["trust"] > 0.5 else \
                     "with little trust" if edge_data["trust"] > 0.2 else "with deep suspicion"

        return f"{strength_desc} {trust_desc}"
```

---

## Development workflow

### Git workflow for AI projects

**Branch strategy**
```bash
# Main branches
main              # Production-ready code
development       # Integration and testing

# Feature branches with AI-specific prefixes
data/dataset-v2          # Data processing
model/personality-v3     # Model changes
agent/dialogue-system    # Agent implementations
config/llm-settings      # Configuration
```

**Data version control with DVC**

DVC handles large model files and datasets that don't belong in Git.

```bash
# Initialize DVC
dvc init
git commit -m "Initialize DVC"

# Track large files
dvc add data/character_dataset.json
dvc add models/personality_model.pkl

# Commit .dvc metafiles
git add data/.dvc data/character_dataset.json.dvc
git add models/model.pkl.dvc
git commit -m "Track data and models with DVC"

# Configure remote storage (S3 example)
dvc remote add -d storage s3://luciddreamer-models/dvcstore
dvc push  # Upload to remote

# On other machines
git clone <repo>
dvc pull  # Download actual data
```

### Testing AI systems

**Handling non-determinism with pytest-harvest**

```python
import pytest
from pytest_harvest import results_bag

@pytest.mark.parametrize("scenario", load_test_scenarios("scenarios.json"))
def test_story_generation(scenario, results_bag):
    """Test story generation with multiple quality metrics"""
    result = story_agent.generate(scenario["prompt"])

    # Multiple evaluation metrics (don't fail immediately)
    results_bag.coherence = evaluate_coherence(result.story)
    results_bag.character_consistency = check_character_traits(result.characters)
    results_bag.plot_structure = evaluate_plot_structure(result.story)
    results_bag.length_appropriate = 500 < len(result.story) < 2000
    results_bag.llm_judge_score = llm_evaluate_quality(result.story, scenario["criteria"])

    # Pass if 3/5 metrics meet threshold
    passing_metrics = sum([
        results_bag.coherence > 0.7,
        results_bag.character_consistency > 0.8,
        results_bag.plot_structure > 0.6,
        results_bag.length_appropriate,
        results_bag.llm_judge_score > 0.75
    ])

    assert passing_metrics >= 3, f"Only {passing_metrics}/5 metrics passed"
```

**LLM-as-Judge pattern**
```python
async def llm_evaluate_quality(output: str, criteria: dict) -> float:
    """Use LLM to evaluate output quality"""
    evaluation_prompt = f"""
    Evaluate the following story output on a scale of 0-1 based on these criteria:
    - Narrative coherence: {criteria['coherence_weight']}
    - Character development: {criteria['character_weight']}
    - Engagement: {criteria['engagement_weight']}

    Story output: {output}

    Provide a single numerical score between 0 and 1.
    """

    response = await evaluator_llm.invoke(evaluation_prompt)
    return float(response.score)
```

### Debugging with LangSmith

**Setup and instrumentation**
```bash
# Environment variables
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=ls-...
export LANGSMITH_PROJECT=luciddreamer-dev
```

```python
from langsmith import traceable
from langsmith.wrappers import wrap_openai

# Wrap LLM client for automatic tracing
client = wrap_openai(OpenAI())

# Trace custom functions
@traceable(run_type="retriever", name="character_memory_retrieval")
async def retrieve_character_memories(character_id: str, query: str):
    memories = await memory_system.recall_relevant_memories(query)
    return memories

@traceable(metadata={"version": "v2.1", "agent_type": "storyteller"})
async def generate_story_continuation(state: dict):
    memories = await retrieve_character_memories(state["character_id"], state["context"])
    response = await client.chat.completions.create(...)
    return response
```

**Production monitoring**
```python
from langsmith import Client

ls_client = Client()

# Collect user feedback
def record_feedback(run_id: str, user_rating: float, user_comment: str):
    ls_client.create_feedback(
        run_id,
        key="user-rating",
        score=user_rating,
        comment=user_comment
    )

# A/B testing with metadata
async def generate_with_variant(prompt: str, variant: str):
    response = await traceable_generate(
        prompt,
        langsmith_extra={
            "metadata": {"variant": variant, "model": "gpt-4"}
        }
    )
    return response
```

### CI/CD pipeline

**GitHub Actions workflow**
```yaml
name: Development CI/CD

on:
  pull_request:
    branches: [development]
  push:
    branches: [development]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-harvest

      - name: Run tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
        run: pytest tests/ -v --tb=short

      - name: Build Docker image
        run: docker build -t luciddreamer:test .

      - name: Integration tests
        run: |
          docker-compose -f docker-compose-test.yml up -d
          docker-compose -f docker-compose-test.yml exec app pytest tests/integration/
          docker-compose -f docker-compose-test.yml down

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/development'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: |
          docker build -t luciddreamer:staging .
          docker push luciddreamer:staging
          # Trigger staging deployment
```

---

## Code examples and design patterns

### Complete character agent implementation

```python
class CharacterAgent:
    """Complete character agent with personality, memory, and emotion"""

    def __init__(self, name: str, personality: PersonalityTraits, backstory: str):
        self.name = name
        self.personality = personality
        self.backstory = backstory
        self.memory = CharacterMemorySystem(character_id=name)
        self.emotion = EmotionalState()
        self.relationships = RelationshipGraph()

        # Create LangGraph agent
        self.agent = create_react_agent(
            model=llm,
            tools=[
                self.create_dialogue_tool(),
                self.create_action_tool(),
                self.create_memory_tool()
            ],
            prompt=self.build_system_prompt(),
            name=name
        )

    def build_system_prompt(self) -> str:
        """Dynamic system prompt incorporating personality and state"""
        return f"""
        You are {self.name}.

        Backstory: {self.backstory}

        Personality: {self.personality.to_prompt()}

        Current emotional state: {self.emotion.to_description()}

        Instructions:
        - Stay in character with your personality traits
        - Reference relevant memories when making decisions
        - Your emotional state influences your responses
        - Consider relationships when interacting with others
        """

    def create_dialogue_tool(self):
        """Tool for character dialogue generation"""
        @tool
        async def speak(content: str, target_character: str = None):
            \"\"\"Generate character dialogue considering personality and emotion\"\"\"
            # Retrieve relevant memories
            context = f"speaking to {target_character}" if target_character else "speaking"
            memories = await self.memory.recall_relevant_memories(context)

            # Check relationship
            relationship = ""
            if target_character:
                relationship = self.relationships.get_relationship_summary(
                    self.name, target_character
                )

            # Modify dialogue based on emotion
            tone_modifier = "excited" if self.emotion.arousal > 0.7 else \
                          "calm" if self.emotion.arousal < 0.3 else "normal"

            return {
                "speaker": self.name,
                "content": content,
                "tone": tone_modifier,
                "memories_referenced": len(memories),
                "relationship_context": relationship
            }

        return speak

    async def process_interaction(self, interaction: dict):
        """Update character state based on interaction"""
        # Update emotional state
        self.emotion.process_event(interaction, self.personality)

        # Store in memory
        await self.memory.process_event(interaction)

        # Update relationships
        if "other_character" in interaction:
            self.relationships.update_relationship(
                self.name,
                interaction["other_character"],
                interaction
            )

        # Check for personality evolution
        if interaction.get("significance", 0) > 0.8:
            self.evolve_traits(interaction)

    def evolve_traits(self, experience: dict):
        """Gradually evolve personality based on significant experiences"""
        evolution = TraitEvolution(self.personality)
        evolution.update_traits(experience)
        self.personality = evolution.current_personality

# Usage
alice = CharacterAgent(
    name="Alice",
    personality=PersonalityTraits(
        openness=0.9,
        conscientiousness=0.7,
        extraversion=0.6,
        agreeableness=0.8,
        neuroticism=0.3
    ),
    backstory="A curious scholar seeking ancient knowledge"
)

bob = CharacterAgent(
    name="Bob",
    personality=PersonalityTraits(
        openness=0.4,
        conscientiousness=0.9,
        extraversion=0.5,
        agreeableness=0.6,
        neuroticism=0.2
    ),
    backstory="A disciplined warrior protecting his village"
)
```

### Plugin architecture for game systems

**Extensible action system**
```python
class ActionRegistry:
    """Plugin-based action system for different game mechanics"""

    def __init__(self):
        self._actions = {}
        self._validators = {}

    def register_action(self, action_name: str, handler, validator=None):
        """Register new action type"""
        self._actions[action_name] = handler
        if validator:
            self._validators[action_name] = validator

    async def execute_action(self, action_name: str, context: dict, **kwargs):
        """Execute registered action with validation"""
        if action_name not in self._actions:
            raise ValueError(f"Unknown action: {action_name}")

        # Validate if validator exists
        if action_name in self._validators:
            validation_result = await self._validators[action_name](context, kwargs)
            if not validation_result.valid:
                return {"success": False, "error": validation_result.error}

        # Execute action
        result = await self._actions[action_name](context, **kwargs)
        return result

# Register combat actions
action_registry = ActionRegistry()

async def handle_attack(context: dict, target: str, weapon: str):
    attacker = context["character"]
    # Personality influences combat style
    if attacker.personality.agreeableness < 0.3:
        damage_modifier = 1.2  # More aggressive
    else:
        damage_modifier = 0.9  # Reluctant fighter

    damage = calculate_damage(weapon) * damage_modifier
    return {"success": True, "damage": damage, "target": target}

async def validate_attack(context: dict, kwargs: dict):
    target = kwargs.get("target")
    if target == context["character"].name:
        return ValidationResult(valid=False, error="Cannot attack yourself")
    return ValidationResult(valid=True)

action_registry.register_action("attack", handle_attack, validate_attack)

# Register dialogue actions
async def handle_persuade(context: dict, target: str, argument: str):
    persuader = context["character"]

    # High extraversion and openness improve persuasion
    persuasion_bonus = (
        persuader.personality.extraversion * 0.5 +
        persuader.personality.openness * 0.3
    )

    # LLM evaluates argument quality
    success = await evaluate_persuasion(argument, persuasion_bonus)
    return {"success": success, "target": target}

action_registry.register_action("persuade", handle_persuade)
```

### Error handling patterns

**Circuit breaker for LLM calls**
```python
class LLMCircuitBreaker:
    """Prevent cascading failures from LLM unavailability"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
            else:
                # Return fallback response
                return await self.fallback_response(*args, **kwargs)

        try:
            result = await func(*args, **kwargs)

            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")

            return await self.fallback_response(*args, **kwargs)

    async def fallback_response(self, *args, **kwargs):
        """Template-based fallback when LLM unavailable"""
        return {
            "content": "I'm having trouble thinking right now. Can you rephrase that?",
            "fallback": True
        }

# Usage
circuit_breaker = LLMCircuitBreaker()

async def generate_with_protection(prompt: str):
    return await circuit_breaker.call(llm.generate, prompt)
```

---

## Developer tools and resources

### Recommended IDEs and extensions

**VS Code setup**
- **Extensions**: Python, Pylance, Docker, LangChain snippets
- **Settings**: Enable type checking, format on save with Black
- **Launch config** for debugging agents:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Story Agent",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/src/main.py",
            "console": "integratedTerminal",
            "env": {
                "OPENAI_API_KEY": "${env:OPENAI_API_KEY}",
                "LANGSMITH_TRACING": "true"
            }
        }
    ]
}
```

### Testing frameworks

**pytest configuration**
```ini
# pytest.ini
[pytest]
markers =
    llm: tests that call LLM APIs (slow)
    integration: integration tests
    unit: fast unit tests

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Run with: pytest -m "not llm" for fast tests
```

### Deployment strategies

**Kubernetes deployment** (production-ready)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: luciddreamer-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: luciddreamer-api
  template:
    metadata:
      labels:
        app: luciddreamer-api
    spec:
      containers:
      - name: api
        image: luciddreamer:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: OLLAMA_URL
          value: "http://vllm-service:8000"
        - name: QDRANT_URL
          value: "http://qdrant-service:6333"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: luciddreamer-service
spec:
  selector:
    app: luciddreamer-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Monitoring and observability

**Prometheus metrics**
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
agent_invocations = Counter('agent_invocations_total', 'Total agent invocations', ['agent_name'])
generation_latency = Histogram('story_generation_seconds', 'Story generation latency')
active_characters = Gauge('active_characters', 'Number of active character agents')
token_usage = Counter('llm_tokens_total', 'Total LLM tokens used', ['model', 'type'])

# Instrument code
@generation_latency.time()
async def generate_story(prompt: str):
    agent_invocations.labels(agent_name='storyteller').inc()
    result = await story_agent.generate(prompt)
    token_usage.labels(model='llama3.2', type='input').inc(result.input_tokens)
    token_usage.labels(model='llama3.2', type='output').inc(result.output_tokens)
    return result

# Expose metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Documentation templates

**Character agent specification**
```markdown
# Character Agent: [Name]

## Personality Profile
- **Openness**: [0-1] - [Description]
- **Conscientiousness**: [0-1] - [Description]
- **Extraversion**: [0-1] - [Description]
- **Agreeableness**: [0-1] - [Description]
- **Neuroticism**: [0-1] - [Description]

## Backstory
[Character history and motivations]

## Capabilities
- **Actions**: [List of available actions]
- **Knowledge Domains**: [Areas of expertise]
- **Special Abilities**: [Unique capabilities]

## Behavior Guidelines
- [How personality influences decisions]
- [Relationship dynamics]
- [Growth trajectory]

## Implementation Notes
```python
character = CharacterAgent(
    name="[Name]",
    personality=PersonalityTraits(...),
    backstory="[Backstory]"
)
```

---

## Complete project structure

```
luciddreamer/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── character_agent.py      # Character agent implementation
│   │   ├── storyteller_agent.py    # Narrative generation
│   │   └── coordinator.py          # Multi-agent coordination
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── episodic.py             # Time-stamped events
│   │   ├── semantic.py             # Facts and knowledge
│   │   ├── procedural.py           # Skills and procedures
│   │   └── consolidation.py        # Memory management
│   ├── personality/
│   │   ├── __init__.py
│   │   ├── traits.py               # Big Five implementation
│   │   ├── emotion.py              # VAD emotional model
│   │   └── evolution.py            # Trait evolution
│   ├── relationships/
│   │   ├── __init__.py
│   │   └── graph.py                # Relationship management
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── action_registry.py      # Plugin system
│   │   └── game_tools.py           # Game-specific tools
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py               # FastAPI routes
│   │   └── websocket.py            # Real-time communication
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── embeddings.py           # Text embeddings
│   │   └── error_handling.py       # Circuit breakers, retries
│   └── config.py                   # Configuration
├── tests/
│   ├── test_agents.py
│   ├── test_memory.py
│   ├── test_personality.py
│   └── test_integration.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose-prod.yml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
├── requirements.txt
├── langgraph.json
├── pytest.ini
├── .env.example
└── README.md
```

**requirements.txt**
```
# Core frameworks
langgraph==1.0.1
langchain==0.3.0
langchain-openai==0.2.0
pydantic==2.0.0

# LLM clients
openai==1.50.0

# Vector storage
qdrant-client==1.7.0

# Web framework
fastapi==0.115.0
uvicorn==0.30.0
websockets==13.0

# Utilities
tenacity==8.0.0
networkx==3.2
numpy==1.26.0

# Development
pytest==8.0.0
pytest-harvest==1.10.4
pytest-asyncio==0.23.0
black==24.0.0
flake8==7.0.0

# Monitoring
prometheus-client==0.20.0
langsmith==0.1.0
```

---

## Troubleshooting guide

### Common issues and solutions

**Issue: Out of memory errors with Ollama**
- **Solution**: Reduce model size (use 7B instead of 13B) or increase system RAM
- **Check**: `docker stats` to monitor memory usage
- **Fix**: Set `OLLAMA_MAX_LOADED_MODELS=1` to limit concurrent models

**Issue: Slow agent responses**
- **Solution**: Enable GPU acceleration, upgrade to vLLM for production
- **Check**: `nvidia-smi` to verify GPU utilization
- **Optimize**: Reduce max context length, use smaller models for simple tasks

**Issue: Vector database connection timeouts**
- **Solution**: Increase connection timeout, check network connectivity
- **Check**: `curl http://localhost:6333/health` for Qdrant health
- **Fix**: Add connection retry logic with exponential backoff

**Issue: Character personality inconsistencies**
- **Solution**: Strengthen personality prompts, increase memory retrieval
- **Check**: LangSmith traces to verify personality context is included
- **Fix**: Add personality reinforcement in system prompt every N interactions

**Issue: Memory consolidation causing data loss**
- **Solution**: Lower importance threshold, increase rehearsal frequency
- **Check**: Monitor memory access patterns in logs
- **Fix**: Implement memory persistence checks before deletion

**Issue: WebSocket disconnections**
- **Solution**: Implement heartbeat ping/pong, exponential backoff reconnection
- **Check**: Network stability, proxy timeout settings
- **Fix**: Configure longer timeout values in load balancer/proxy

### Performance optimization checklist

- [ ] GPU acceleration enabled for LLM inference
- [ ] Vector database indexes optimized
- [ ] Memory consolidation running on schedule
- [ ] Connection pooling configured for database
- [ ] Caching enabled for frequent queries
- [ ] Rate limiting implemented to prevent overload
- [ ] Monitoring and alerting configured
- [ ] Load testing completed at expected scale

---

## Key insights and recommendations

**Start with the supervisor pattern** for clearest control flow when building multi-agent storytelling systems. The pattern's explicit task delegation makes debugging straightforward while providing flexibility to add specialized agents incrementally.

**Ollama gets you running in 10 minutes** for development, but plan migration to vLLM when concurrent users exceed 20-30. The 19x throughput improvement justifies the additional setup complexity for production deployments.

**Hierarchical memory with importance scoring** prevents overwhelming agents with irrelevant context. Weight emotional salience heavily (0.3 coefficient) for memorable character experiences that drive personality evolution.

**Docker Compose brings everything together** without Kubernetes complexity until you need multi-region deployment. The complete stack (LLM + vector DB + app) runs on a single machine during development.

**LangSmith tracing from day one** saves countless debugging hours. The ability to inspect agent decision paths and identify where personality context gets lost proves invaluable as complexity grows.

**Personality trait evolution requires 0.1-0.2 plasticity** for noticeable change over 10-20 significant experiences while maintaining character stability. Higher values create erratic characters, lower values prevent meaningful growth.

**Test with 3+ evaluation metrics** using pytest-harvest to handle LLM non-determinism. Requiring 3/5 metrics to pass balances quality standards with inevitable response variation.

The Stanford Generative Agents research achieving 85% accuracy in human behavior replication validates this architectural approach. Companies like Klarna and Uber demonstrating production success with LangGraph confirms the framework's maturity.

**Version numbers used in this guide**:
- LangGraph: 1.0.1
- Ollama: Latest (continuous updates October 2025)
- vLLM: 0.9.2+ with V1 architecture
- Qdrant: 1.7.0+
- Python: 3.10-3.12 (3.12 recommended)
- FastAPI: 0.115.0+
- LangChain: 0.3.0+

Build incrementally—start with a single character agent, add memory systems, then expand to multi-agent coordination. This guide provides production-ready patterns proven at scale by Fortune 500 companies.