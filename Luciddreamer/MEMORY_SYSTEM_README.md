# Luciddreamer Hierarchical Memory System

A sophisticated memory architecture for AI agents that enables persistent knowledge, learning from experience, and memory sharing within agent packs. Inspired by human cognitive systems with four-tier memory architecture.

## Overview

The memory system provides agents with human-like memory capabilities:

- **Working Memory**: Short-term buffer with 20-item capacity and 30-minute decay
- **Episodic Memory**: Time-stamped experiences with importance scoring and emotional tagging
- **Semantic Memory**: Abstract knowledge using vector embeddings and concept hierarchies
- **Procedural Memory**: Skills and abilities with mastery tracking and practice effects

## Features

### Core Memory Systems

- **Working Memory**: Real-time buffer with automatic decay and priority-based eviction
- **Episodic Memory**: Autobiographical experiences with spatial and social context
- **Semantic Memory**: Facts and concepts with vector similarity search
- **Procedural Memory**: Skills with mastery levels and practice-based improvement

### Advanced Capabilities

- **Memory Consolidation**: KL divergence surprise detection and automatic knowledge extraction
- **Memory Retrieval**: Multi-modal search (semantic, temporal, spatial, contextual)
- **Forgetting Mechanisms**: Biologically-inspired forgetting curves and memory pruning
- **Memory Sharing**: Pack-based memory sharing with conflict resolution
- **Skill Trees**: Interconnected skill dependencies and transfer effects

## Installation

```bash
# Install core requirements
pip install -r requirements_memory.txt

# For full functionality with embeddings
pip install sentence-transformers transformers torch

# For GPU acceleration (optional)
pip install faiss-gpu
```

## Quick Start

```python
from memory.hierarchical_memory import HierarchicalMemorySystem

# Initialize memory system
memory_system = HierarchicalMemorySystem(
    agent_id="agent_001",
    storage_path="./memory_data",
    working_memory_capacity=20,
    working_memory_decay=1800.0  # 30 minutes
)

# Start background processes
memory_system.start()

# Add working memory items
memory_system.add_working_memory(
    content="Saw a mysterious artifact in the forest",
    item_type="observation",
    importance=0.8,
    context_tags={"exploration", "mystery"}
)

# Add episodic memories
memory_id = memory_system.add_episodic_memory(
    content="While exploring the ancient forest, I discovered a crystal artifact...",
    emotional_valence=EmotionalValence.POSITIVE,
    importance=0.9,
    tags={"discovery", "artifact"}
)

# Add semantic concepts
concept_id = memory_system.add_semantic_concept(
    name="Crystal Artifact",
    definition="A supernatural object with magical properties",
    embedding=embedding_vector  # Optional
)

# Add and practice skills
skill_id = memory_system.add_skill(
    name="Artifact Investigation",
    skill_type=SkillType.TECHNICAL,
    difficulty=0.8
)

improvement = memory_system.practice_skill(
    skill_id=skill_id,
    result=PracticeResult.SUCCESS,
    performance_rating=0.8
)

# Search memories
results = memory_system.search_memories(
    query="artifact",
    search_mode=SearchMode.HYBRID,
    max_results=10
)

# Share memories with pack
memory_system.share_memory(
    memory_id=memory_id,
    share_type=ShareType.EXPERIENCE,
    permission=SharePermission.PACK_ONLY
)

# Get statistics
stats = memory_system.get_memory_statistics()

# Cleanup
memory_system.stop()
```

## Architecture

### Memory Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                  Working Memory                         │
│  • 20-item capacity                                   │
│  • 30-minute decay                                    │
│  • Priority-based eviction                             │
└─────────────────────────────────────────────────────────┘
                           │ (consolidation)
┌─────────────────────────────────────────────────────────┐
│                Long-term Memory                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │ Episodic    │ │ Semantic    │ │ Procedural      │   │
│  │ Memory      │ │ Memory      │ │ Memory          │   │
│  │             │ │             │ │                 │   │
│  │ Experiences │ │ Facts/Know. │ │ Skills          │   │
│  │ Emotions    │ │ Concepts    │ │ Mastery Levels  │   │
│  │ Context     │ │ Relationships│ │ Practice        │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Integration Points

- **Consolidation Pipeline**: Automatic transfer from working to long-term memory
- **Retrieval System**: Unified search across all memory types
- **Sharing Protocol**: Peer-to-peer memory synchronization
- **Forgetting System**: Capacity management through selective pruning

## Memory Types

### Working Memory

- **Purpose**: Real-time processing and current context
- **Capacity**: 20 items (configurable)
- **Decay**: 30 minutes (configurable)
- **Features**: Priority-based eviction, access tracking, context tagging

```python
# Add to working memory
memory_system.add_working_memory(
    content="Need to investigate the strange noise",
    item_type="thought",
    importance=0.7,
    context_tags={"investigation", "mystery"}
)
```

### Episodic Memory

- **Purpose**: Autobiographical experiences and events
- **Features**: Emotional tagging, spatial/social context, importance scoring
- **Consolidation**: Automatic knowledge extraction
- **Retrieval**: Temporal and contextual search

```python
# Add episodic memory
memory_id = memory_system.add_episodic_memory(
    content="The cave entrance was covered in strange symbols...",
    emotional_valence=EmotionalValence.NEGATIVE,
    emotional_arousal=0.8,
    importance=0.9,
    spatial_context=SpatialContext(
        location="mysterious_cave",
        environment="underground"
    ),
    tags={"danger", "symbols", "discovery"}
)
```

### Semantic Memory

- **Purpose**: Facts, concepts, and abstract knowledge
- **Features**: Vector embeddings, concept hierarchies, fact verification
- **Storage**: ChromaDB/FAISS support for scalable vector search
- **Retrieval**: Semantic similarity search

```python
# Add semantic concept
concept_id = memory_system.add_semantic_concept(
    name="Ancient Symbols",
    concept_type=ConceptType.ENTITY,
    definition="Mysterious markings found in ancient structures",
    embedding=embedding_vector,  # From sentence transformer
    attributes={"origin": "unknown", "meaning": "cryptic"}
)
```

### Procedural Memory

- **Purpose**: Skills, abilities, and procedures
- **Features**: Mastery levels, practice effects, skill trees
- **Learning**: Experience-based improvement and forgetting
- **Transfer**: Skill transfer between related abilities

```python
# Add skill
skill_id = memory_system.add_skill(
    name="Symbol Deciphering",
    description="Ability to interpret ancient symbols and codes",
    skill_type=SkillType.COGNITIVE,
    difficulty=0.8,
    prerequisites=[("ancient_languages", 0.6)]
)

# Practice skill
improvement = memory_system.practice_skill(
    skill_id=skill_id,
    result=PracticeResult.IMPROVEMENT,
    time_spent=3600,  # 1 hour
    performance_rating=0.7
)
```

## Advanced Features

### Memory Consolidation

Automatic consolidation with surprise detection using KL divergence:

```python
# Force consolidation
memory_system.force_consolidation()

# Get consolidation statistics
stats = memory_system.get_memory_statistics()
print(f"Consolidations: {stats.consolidation['total_consolidations']}")
```

### Memory Retrieval

Multi-modal search across all memory systems:

```python
# Semantic search
results = memory_system.search_memories(
    query="ancient symbols",
    search_mode=SearchMode.SEMANTIC,
    memory_scope=MemoryScope.ALL
)

# Temporal search
recent = memory_system.search_memories(
    query="",
    search_mode=SearchMode.TEMPORAL,
    time_range=(start_time, end_time)
)
```

### Memory Sharing

Pack-based memory sharing with conflict resolution:

```python
# Share with pack
memory_system.share_memory(
    memory_id=memory_id,
    share_type=ShareType.EXPERIENCE,
    permission=SharePermission.PACK_ONLY
)

# Add pack member
memory_system.sharing.add_pack_member(
    agent_id="agent_002",
    endpoint="ws://agent-002:8080",
    trust_level=0.8
)
```

### Forgetting and Pruning

Biologically-inspired memory management:

```python
# Get forgetting statistics
stats = memory_system.get_memory_statistics()
print(f"Forgetting events: {stats.consolidation['total_forgetting_events']}")

# Pruning is automatic but can be configured
```

## Configuration

### Vector Database Backends

```python
# ChromaDB (recommended for development)
semantic_memory = SemanticMemory(
    backend="chroma",
    persist_directory="./chroma_db"
)

# FAISS (recommended for production)
semantic_memory = SemanticMemory(
    backend="faiss",
    index_type="IVF_Flat"
)

# Fallback (in-memory)
semantic_memory = SemanticMemory(backend="fallback")
```

### Memory System Parameters

```python
memory_system = HierarchicalMemorySystem(
    agent_id="agent_001",
    storage_path="./memory_data",
    working_memory_capacity=20,      # Working memory items
    working_memory_decay=1800.0      # Decay time in seconds
)
```

### Consolidation Settings

```python
memory_system.consolidation = MemoryConsolidation(
    consolidation_interval=300.0,    # 5 minutes
    importance_threshold=0.3,
    surprise_threshold=0.6
)
```

## Performance Considerations

### Memory Usage

- **Working Memory**: ~1MB for full capacity
- **Episodic Memory**: ~100B per memory entry
- **Semantic Memory**: Depends on vector database (1KB + embedding size)
- **Procedural Memory**: ~500B per skill

### Scaling

- **Vector Databases**: Use ChromaDB for development, FAISS for production
- **Memory Limits**: Configure pruning thresholds based on available memory
- **Background Processing**: Consolidation and maintenance run in separate threads

### Optimization

- **Embeddings**: Pre-compute embeddings for better performance
- **Indexing**: Use appropriate vector index types for your data size
- **Batching**: Batch operations for better efficiency

## Example Usage

See `memory_system_example.py` for a comprehensive demonstration of all features:

```bash
python memory_system_example.py
```

This example demonstrates:
- Working memory operations
- Episodic memory creation
- Semantic concept management
- Procedural skill development
- Cross-system search
- Memory consolidation
- Pack-based sharing
- Statistics and monitoring

## Research Inspiration

This memory system is inspired by research in:

- **Cognitive Psychology**: Working memory models (Baddeley & Hitch)
- **Neuroscience**: Hippocampal consolidation systems
- **AI Research**: Stanford's Generative Agents project
- **Memory Studies**: Ebbinghaus forgetting curves
- **Distributed Systems**: Peer-to-peer knowledge sharing

## Limitations

- **Embedding Quality**: Dependent on embedding model quality
- **Storage Requirements**: Vector databases can be memory-intensive
- **Conflict Resolution**: Simplified consensus mechanisms
- **Learning Speed**: Mastery improvement is simulated, not learned

## Future Development

- **Advanced Embeddings**: Integration with larger language models
- **Distributed Storage**: Cloud-based vector databases
- **Neural Networks**: Learned forgetting and consolidation
- **Emotion Modeling**: More sophisticated emotional systems
- **Multi-Agent**: Advanced pack dynamics and coordination

## License

This memory system is part of the Luciddreamer project. See main project license for details.

## Contributing

Contributions are welcome! Please ensure:

1. Code follows project style guidelines
2. Tests are included for new features
3. Documentation is updated
4. Performance impact is considered

## Support

For issues and questions:

1. Check existing documentation and examples
2. Review the example code
3. Test with different configuration options
4. Report issues with reproduction steps

---

**Note**: This memory system is designed for AI agents and may not be suitable for human memory applications or clinical use.