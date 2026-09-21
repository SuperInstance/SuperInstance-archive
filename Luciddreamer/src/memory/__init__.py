"""
Hierarchical Memory System for Luciddreamer Agents

This module provides a sophisticated multi-tier memory architecture inspired by
human cognitive systems, enabling agents to develop persistent knowledge,
learn from experience, and share memories within packs.

Memory Tiers:
- Working Memory: Short-term buffer with 20-item limit and 30-minute decay
- Episodic Memory: Time-stamped experiences with importance scoring
- Semantic Memory: Abstract knowledge using vector embeddings
- Procedural Memory: Skills and abilities with mastery tracking
"""

from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory, EpisodicMemoryEntry
from .semantic_memory import SemanticMemory
from .procedural_memory import ProceduralMemory, Skill, MasteryLevel
from .consolidation import MemoryConsolidation, SurpriseDetector
from .retrieval import MemoryRetrieval, RetrievalQuery
from .hierarchical_memory import HierarchicalMemorySystem

__all__ = [
    "WorkingMemory",
    "EpisodicMemory",
    "EpisodicMemoryEntry",
    "SemanticMemory",
    "ProceduralMemory",
    "Skill",
    "MasteryLevel",
    "MemoryConsolidation",
    "SurpriseDetector",
    "MemoryRetrieval",
    "RetrievalQuery",
    "HierarchicalMemorySystem"
]

__version__ = "1.0.0"