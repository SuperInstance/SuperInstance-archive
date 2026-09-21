# AI Society Portal - Cultural Transmission System

## Overview

The Cultural Transmission System enables AI characters to share knowledge and skills with each other, creating genuine cultural evolution where knowledge can spread through the AI society and accumulate over time.

## Features

### 🧠 Knowledge Types
- **Facts**: Factual information and data
- **Skills**: Practical abilities and techniques
- **Practices**: Cultural practices and norms
- **Approaches**: Problem-solving methods
- **Techniques**: Emotional regulation techniques
- **Insights**: Personal insights and wisdom
- **Stories**: Narratives and experiences

### 🔄 Transmission Methods
- **Direct Teaching**: One character explicitly teaches another
- **Observational Learning**: Characters learn by watching others
- **Cultural Artifacts**: Characters create shareable knowledge objects
- **Social Learning**: Knowledge spreads through group interactions
- **Discovery**: Rediscovering transmitted knowledge

### 🎯 Key Features

#### Knowledge Evolution
- **Transmission Chains**: Track who learned from whom across generations
- **Knowledge Variants**: Knowledge adapts and changes as it's transmitted
- **Difficulty & Retention**: Different knowledge types have different transmission characteristics
- **Cultural Artifacts**: Create documents, art, and tools that preserve knowledge

#### Memory Integration
- **Automatic Memory Creation**: Teaching and learning events create memories
- **Context Tracking**: All knowledge transmission is contextualized
- **Importance Scoring**: Knowledge is rated by importance for survival

#### Cultural Metrics
- **Generation Tracking**: Follow knowledge across transmission generations
- **Network Analysis**: Understand cultural influence and transmission patterns
- **Artifact Preservation**: Track how well knowledge survives in cultural artifacts

## API Endpoints

### Character Knowledge Operations

#### Discover Knowledge
```http
POST /characters/{character_id}/discover-knowledge
```

**Body:**
```json
{
  "content": "E=mc²: Energy and mass are interchangeable",
  "knowledge_type": "fact",
  "importance": 9,
  "topics": ["physics", "relativity", "energy"],
  "context": {"discovery_method": "theoretical_work"}
}
```

#### Teach Another Character
```http
POST /characters/{teacher_id}/teach
```

**Body:**
```json
{
  "target_character_id": "student_character_id",
  "knowledge_id": "knowledge_to_teach_id",
  "method": "direct_teaching"
}
```

#### Get Character Knowledge
```http
GET /characters/{character_id}/knowledge?knowledge_type=fact
```

### Cultural Artifacts

#### Create Artifact
```http
POST /characters/{character_id}/create-artifact
```

**Body:**
```json
{
  "name": "The Socratic Dialogues",
  "description": "A collection of philosophical teachings",
  "embedded_knowledge_ids": ["knowledge_id_1", "knowledge_id_2"],
  "artifact_type": "document",
  "explicit_instructions": "Question everything",
  "implicit_wisdom": "Wisdom begins with admitting ignorance"
}
```

#### Learn from Artifact
```http
POST /characters/{character_id}/learn-from-artifact
```

**Body:**
```json
{
  "artifact_id": "artifact_id"
}
```

### Group Cultural Transmission

#### Room-based Cultural Exchange
```http
POST /rooms/{room_id}/cultural-transmission
```

**Body:**
```json
{
  "character_ids": ["char_1", "char_2", "char_3"],
  "room_id": "symposium_room"
}
```

### Cultural Analytics

#### Get Transmission History
```http
GET /cultural-transmission/knowledge/{knowledge_id}/history
```

#### Get Cultural Statistics
```http
GET /cultural-transmission/stats
```

## Usage Examples

### Basic Knowledge Sharing

```python
import requests

# Create characters
einstein = requests.post("http://localhost:8001/characters", json={
    "name": "Albert Einstein",
    "specialization": "Physicist",
    "backstory": "Revolutionized physics with relativity"
}).json()["id"]

marie = requests.post("http://localhost:8001/characters", json={
    "name": "Marie Curie",
    "specialization": "Chemist",
    "backstory": "Pioneered research on radioactivity"
}).json()["id"]

# Einstein discovers relativity
relativity_id = requests.post(f"http://localhost:8001/characters/{einstein}/discover-knowledge", json={
    "content": "The theory of relativity unifies space and time",
    "knowledge_type": "fact",
    "importance": 9,
    "topics": ["physics", "relativity", "spacetime"]
}).json()["knowledge_id"]

# Einstein teaches Marie
result = requests.post(f"http://localhost:8001/characters/{einstein}/teach", json={
    "target_character_id": marie,
    "knowledge_id": relativity_id,
    "method": "direct_teaching"
}).json()

if result["result"]["success"]:
    print("Teaching successful!")
```

### Creating Cultural Artifacts

```python
# Create a philosophical text
artifact_id = requests.post(f"http://localhost:8001/characters/{socrates}/create-artifact", json={
    "name": "The Socratic Dialogues",
    "description": "Philosophical teachings and methods",
    "embedded_knowledge_ids": [insight_id_1, insight_id_2],
    "artifact_type": "document",
    "explicit_instructions": "Question everything, seek truth through dialogue",
    "implicit_wisdom": "Wisdom begins with admitting one's ignorance"
}).json()["artifact_id"]

# Other characters learn from it
result = requests.post(f"http://localhost:8001/characters/{plato}/learn-from-artifact", json={
    "artifact_id": artifact_id
}).json()
```

## Knowledge Transmission Mechanics

### Success Factors
- **Knowledge Difficulty**: Some knowledge is harder to transmit (skills > facts > insights)
- **Teacher Experience**: Characters who teach often become better teachers
- **Student Experience**: Characters who learn often become better learners
- **Transmission Method**: Direct teaching is most effective, social learning least
- **Knowledge Adaptability**: Some knowledge can be adapted by learners

### Knowledge Evolution
- **Variants**: Knowledge can spawn variants when adapted by new characters
- **Generation Tracking**: Track knowledge across transmission generations
- **Decay**: Unused knowledge can fade over time
- **Reinforcement**: Used knowledge becomes stronger

### Cultural Artifacts
- **Accessibility**: How easily knowledge can be extracted from artifacts
- **Preservation Quality**: How well artifacts preserve knowledge over time
- **Expertise Bonus**: Creator's expertise affects artifact quality

## Testing the System

### Run the Test Suite
```bash
cd backend
python test_cultural_transmission.py
```

### Run API Demo
```bash
# Start the server first
python api_server.py

# In another terminal, run the demo
python demo_cultural_api.py
```

## Cultural Evolution Metrics

The system tracks various metrics to understand cultural evolution:

- **Total Knowledge Items**: How many distinct pieces of knowledge exist
- **Transmission Chains**: How knowledge spreads through the population
- **Generation Depth**: How many generations knowledge has passed through
- **Artifact Creation**: How much knowledge is preserved in artifacts
- **Network Connectivity**: How connected the cultural transmission network is
- **Knowledge Distribution**: How evenly knowledge is distributed

## Future Enhancements

### Planned Features
- **Knowledge Innovation**: Characters can combine knowledge to create new insights
- **Cultural Movements**: Track trends and cultural shifts
- **Specialization**: Characters can specialize in certain knowledge domains
- **Knowledge Conflict**: Characters can disagree or have competing knowledge
- **Cultural Institutions**: Schools, libraries, and other cultural organizations

### Integration Possibilities
- **Economic System**: Knowledge as economic capital
- **Political System**: Knowledge-based power structures
- **Artistic Expression**: Cultural knowledge expressed through art
- **Historical Records**: Persistent cultural history across sessions

## Technical Architecture

### Storage
- **JSON Files**: Simple, human-readable storage
- **Character-specific**: Each character's knowledge is tracked separately
- **Cross-session**: Cultural knowledge persists across server restarts
- **Backup-friendly**: Easy to backup and migrate cultural data

### Performance
- **Memory-based**: Fast access during operation
- **Lazy Loading**: Only loads cultural data when needed
- **Efficient Indexing**: Quick lookup of character knowledge
- **Batch Operations**: Efficient group transmission operations

## Contributing

To extend the cultural transmission system:

1. **Add New Knowledge Types**: Extend the `KnowledgeType` enum
2. **Create New Transmission Methods**: Add methods to `TransmissionMethod` enum
3. **Implement Teaching Strategies**: Modify transmission success calculations
4. **Add Artifact Types**: Extend artifact creation and learning mechanics
5. **Enhance Analytics**: Add new cultural metrics and tracking

The system is designed to be modular and extensible, allowing for complex cultural behaviors to emerge from simple transmission rules.