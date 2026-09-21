"""
Memory service for tracking character interactions and experiences.
"""

import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.memory import (
    MemoryType, MemoryImportance, MemoryCategory,
    MemorySchema, MemoryCreationRequest, MemoryQueryRequest,
    MemoryRecallResult, MemorySearchResult, MemoryAnalysis,
    MemoryTrigger, PersonalHistory, MemoryInfluenceAssessment,
    Memory, MemoryAssociation, MemoryCluster, ConversationMemory
)
from ..models.base import EmotionType
from ..models.personality import PersonalityProfileSchema
from ..config import Config

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.config = Config()
        self.memory_triggers = self._initialize_memory_triggers()
        self.decay_modifiers = self._initialize_decay_modifiers()
        
    def _initialize_memory_triggers(self) -> List[MemoryTrigger]:
        """Initialize common memory triggers."""
        return [
            MemoryTrigger(
                trigger_type="sensory",
                trigger_value="smell",
                memory_types_triggered=[MemoryType.PERSONAL_REVELATION, MemoryType.LOCATION_VISIT],
                strength_threshold=0.2
            ),
            MemoryTrigger(
                trigger_type="verbal",
                trigger_value="name_mention",
                memory_types_triggered=[MemoryType.CONVERSATION, MemoryType.RELATIONSHIP_CHANGE],
                strength_threshold=0.1
            ),
            MemoryTrigger(
                trigger_type="situational",
                trigger_value="combat",
                memory_types_triggered=[MemoryType.COMBAT_ENCOUNTER],
                strength_threshold=0.3
            ),
            MemoryTrigger(
                trigger_type="emotional",
                trigger_value="fear",
                memory_types_triggered=[MemoryType.COMBAT_ENCOUNTER, MemoryType.PERSONAL_REVELATION],
                strength_threshold=0.4
            )
        ]
        
    def _initialize_decay_modifiers(self) -> Dict[MemoryImportance, float]:
        """Initialize memory decay rates by importance."""
        return {
            MemoryImportance.CRITICAL: 0.001,      # Almost never fade
            MemoryImportance.SIGNIFICANT: 0.005,   # Fade very slowly
            MemoryImportance.MODERATE: 0.01,       # Normal fade rate
            MemoryImportance.MINOR: 0.02,          # Fade faster
            MemoryImportance.TRIVIAL: 0.05         # Fade quickly
        }

    async def create_memory(
        self,
        request: MemoryCreationRequest,
        personality: Optional[PersonalityProfileSchema] = None,
        db_session: Optional[Session] = None
    ) -> MemorySchema:
        """Create a new memory for a character."""
        
        # Generate memory ID
        memory_id = f"mem_{request.character_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Set event timestamp if not provided
        event_timestamp = request.event_timestamp or datetime.utcnow()
        
        # Calculate initial strength based on importance and personality
        initial_strength = await self._calculate_initial_strength(
            request.importance, request.category, personality
        )
        
        # Determine decay rate
        decay_rate = self.decay_modifiers.get(request.importance, 0.01)
        
        # Extract keywords from description
        keywords = await self._extract_keywords(request.description, request.tags)
        
        # Create memory
        memory = MemorySchema(
            id=memory_id,
            character_id=request.character_id,
            memory_type=request.memory_type,
            category=request.category,
            importance=request.importance,
            title=request.title,
            description=request.description,
            participants=request.participants or [],
            location=request.location,
            tags=request.tags or [],
            keywords=keywords,
            associated_emotions=request.associated_emotions or [],
            initial_strength=initial_strength,
            current_strength=initial_strength,
            decay_rate=decay_rate,
            event_timestamp=event_timestamp
        )
        
        # Create associations with existing memories
        await self._create_memory_associations(memory, db_session)
        
        logger.info(f"Created memory {memory_id} for character {request.character_id}")
        return memory

    async def recall_memories(
        self,
        character_id: str,
        trigger: str,
        context: Dict[str, Any],
        personality: Optional[PersonalityProfileSchema] = None,
        limit: int = 5
    ) -> List[MemoryRecallResult]:
        """Recall memories based on a trigger and context."""
        
        # Find relevant memory triggers
        applicable_triggers = [
            t for t in self.memory_triggers 
            if trigger.lower() in t.trigger_value.lower() or t.trigger_type in context
        ]
        
        if not applicable_triggers:
            return []
            
        recalled_memories = []
        
        # Search for memories matching trigger criteria
        for memory_trigger in applicable_triggers:
            query = MemoryQueryRequest(
                character_id=character_id,
                memory_types=memory_trigger.memory_types_triggered,
                minimum_strength=memory_trigger.strength_threshold,
                limit=limit
            )
            
            search_result = await self.search_memories(query)
            
            for memory in search_result.memories:
                # Calculate recall confidence
                recall_confidence = await self._calculate_recall_confidence(
                    memory, trigger, context, personality
                )
                
                if recall_confidence > 0.1:  # Minimum threshold for recall
                    # Calculate recall accuracy
                    recall_accuracy = await self._calculate_recall_accuracy(
                        memory, recall_confidence
                    )
                    
                    # Calculate emotional impact
                    emotional_impact = await self._calculate_emotional_impact(
                        memory, context
                    )
                    
                    # Find associated memories
                    associated_memories = await self._find_associated_memories(
                        memory.id, character_id
                    )
                    
                    recall_result = MemoryRecallResult(
                        memory=memory,
                        recall_confidence=recall_confidence,
                        recall_accuracy=recall_accuracy,
                        emotional_impact=emotional_impact,
                        associated_memories=associated_memories,
                        recall_trigger=trigger
                    )
                    
                    recalled_memories.append(recall_result)
                    
                    # Update memory - reinforce it due to recall
                    await self._reinforce_memory(memory)
                    
        # Sort by confidence and return top results
        recalled_memories.sort(key=lambda x: x.recall_confidence, reverse=True)
        return recalled_memories[:limit]

    async def search_memories(
        self,
        query: MemoryQueryRequest
    ) -> MemorySearchResult:
        """Search for memories based on query parameters."""
        
        # In a real implementation, this would query the database
        # For now, we'll return a mock search result
        
        # Calculate search relevance scores
        search_relevance = {}
        
        # Mock memories for demonstration
        mock_memories = [
            MemorySchema(
                id=f"mem_{query.character_id}_001",
                character_id=query.character_id,
                memory_type=MemoryType.CONVERSATION,
                category=MemoryCategory.SOCIAL,
                importance=MemoryImportance.MODERATE,
                title="First meeting with the merchant",
                description="Met Jorik the merchant in the town square. He seemed trustworthy.",
                participants=["jorik_merchant"],
                location="town_square",
                tags=["merchant", "trade", "first_meeting"],
                keywords=["jorik", "merchant", "trustworthy", "town", "square"],
                associated_emotions=[EmotionType.TRUST],
                current_strength=0.8,
                event_timestamp=datetime.utcnow() - timedelta(days=5)
            )
        ]
        
        # Filter memories based on query criteria
        filtered_memories = []
        for memory in mock_memories:
            relevance_score = 0.0
            
            # Check memory types
            if not query.memory_types or memory.memory_type in query.memory_types:
                relevance_score += 0.2
                
            # Check categories
            if not query.categories or memory.category in query.categories:
                relevance_score += 0.2
                
            # Check importance
            if not query.importance_levels or memory.importance in query.importance_levels:
                relevance_score += 0.1
                
            # Check participants
            if query.participants:
                if memory.participants and any(p in memory.participants for p in query.participants):
                    relevance_score += 0.3
                    
            # Check location
            if query.location:
                if memory.location and query.location.lower() in memory.location.lower():
                    relevance_score += 0.2
                    
            # Check keywords
            if query.keywords:
                if memory.keywords:
                    matching_keywords = set(query.keywords) & set(memory.keywords)
                    relevance_score += (len(matching_keywords) / len(query.keywords)) * 0.3
                    
            # Check query text
            if query.query_text:
                text_match = (
                    query.query_text.lower() in memory.title.lower() or
                    query.query_text.lower() in memory.description.lower()
                )
                if text_match:
                    relevance_score += 0.4
                    
            # Check minimum strength
            if memory.current_strength >= query.minimum_strength:
                relevance_score += 0.1
                
            if relevance_score > 0.3:  # Minimum relevance threshold
                filtered_memories.append(memory)
                search_relevance[memory.id] = relevance_score
                
        # Sort by relevance
        filtered_memories.sort(
            key=lambda m: search_relevance.get(m.id, 0),
            reverse=True
        )
        
        # Apply limit
        result_memories = filtered_memories[:query.limit]
        
        return MemorySearchResult(
            memories=result_memories,
            total_found=len(filtered_memories),
            search_relevance=search_relevance,
            clusters_found=["merchant_interactions", "town_square_events"],
            related_concepts=["trade", "trust", "first_meetings"]
        )

    async def update_memory_strength(
        self,
        character_id: str,
        time_passed: timedelta,
        activity_level: float = 1.0
    ) -> Dict[str, float]:
        """Update memory strengths based on time decay and activity."""
        
        # In a real implementation, this would update all memories for the character
        # For now, we'll return mock strength updates
        
        strength_updates = {}
        
        # Mock memory decay calculation
        mock_memories = ["mem_001", "mem_002", "mem_003"]
        
        for memory_id in mock_memories:
            # Calculate decay based on time passed
            days_passed = time_passed.total_seconds() / (24 * 3600)
            base_decay = 0.01 * days_passed * activity_level
            
            # Random variation for demonstration
            actual_decay = base_decay * random.uniform(0.8, 1.2)
            
            # New strength (can't go below 0)
            current_strength = max(0.0, 0.8 - actual_decay)
            strength_updates[memory_id] = current_strength
            
        logger.info(f"Updated {len(strength_updates)} memory strengths for character {character_id}")
        return strength_updates

    async def analyze_character_memories(
        self,
        character_id: str
    ) -> MemoryAnalysis:
        """Analyze a character's memory patterns and distribution."""
        
        # In a real implementation, this would analyze all memories
        # For now, we'll return a mock analysis
        
        return MemoryAnalysis(
            character_id=character_id,
            total_memories=15,
            memory_distribution={
                MemoryType.CONVERSATION: 5,
                MemoryType.COMBAT_ENCOUNTER: 3,
                MemoryType.QUEST_EVENT: 4,
                MemoryType.RELATIONSHIP_CHANGE: 2,
                MemoryType.LOCATION_VISIT: 1
            },
            importance_breakdown={
                MemoryImportance.CRITICAL: 1,
                MemoryImportance.SIGNIFICANT: 3,
                MemoryImportance.MODERATE: 6,
                MemoryImportance.MINOR: 4,
                MemoryImportance.TRIVIAL: 1
            },
            category_breakdown={
                MemoryCategory.SOCIAL: 7,
                MemoryCategory.TACTICAL: 3,
                MemoryCategory.PERSONAL: 2,
                MemoryCategory.FACTUAL: 2,
                MemoryCategory.EMOTIONAL: 1
            },
            strongest_memories=[],  # Would be populated with actual memories
            weakest_memories=[],    # Would be populated with actual memories
            most_accessed=[],       # Would be populated with actual memories
            memory_connections=23,
            cluster_count=5,
            average_memory_strength=0.65
        )

    async def get_character_history(
        self,
        character_id: str
    ) -> PersonalHistory:
        """Get comprehensive personal history of a character."""
        
        # In a real implementation, this would compile actual memories
        return PersonalHistory(
            character_id=character_id,
            major_life_events=[],
            relationship_history={},
            location_history={},
            skill_development=[],
            personality_forming_events=[],
            secrets_and_mysteries=[],
            timeline_gaps=[]
        )

    async def assess_memory_influence(
        self,
        character_id: str,
        current_situation: Dict[str, Any]
    ) -> MemoryInfluenceAssessment:
        """Assess how memories influence current behavior and decisions."""
        
        # In a real implementation, this would analyze memory influence
        return MemoryInfluenceAssessment(
            character_id=character_id,
            influential_memories=[],
            behavioral_patterns={},
            decision_influences={},
            emotional_influences={},
            relationship_influences={}
        )

    async def _calculate_initial_strength(
        self,
        importance: MemoryImportance,
        category: MemoryCategory,
        personality: Optional[PersonalityProfileSchema]
    ) -> float:
        """Calculate initial memory strength based on various factors."""
        
        # Base strength from importance
        importance_strengths = {
            MemoryImportance.CRITICAL: 1.0,
            MemoryImportance.SIGNIFICANT: 0.9,
            MemoryImportance.MODERATE: 0.7,
            MemoryImportance.MINOR: 0.5,
            MemoryImportance.TRIVIAL: 0.3
        }
        
        base_strength = importance_strengths.get(importance, 0.5)
        
        # Adjust based on category
        category_modifiers = {
            MemoryCategory.EMOTIONAL: 0.1,   # Emotional memories are stronger
            MemoryCategory.PERSONAL: 0.05,   # Personal memories slightly stronger
            MemoryCategory.SECRET: 0.15,     # Secrets are memorable
            MemoryCategory.SOCIAL: 0.0,      # Neutral
            MemoryCategory.FACTUAL: -0.05,   # Facts fade faster
            MemoryCategory.TACTICAL: -0.1    # Tactical info fades faster
        }
        
        strength = base_strength + category_modifiers.get(category, 0.0)
        
        # Personality adjustments
        if personality:
            # High conscientiousness = better memory retention
            if personality.conscientiousness > 0.7:
                strength += 0.1
            elif personality.conscientiousness < 0.3:
                strength -= 0.1
                
            # High neuroticism = stronger emotional memories
            if category == MemoryCategory.EMOTIONAL and personality.neuroticism > 0.7:
                strength += 0.1
                
        return max(0.1, min(1.0, strength))

    async def _calculate_recall_confidence(
        self,
        memory: MemorySchema,
        trigger: str,
        context: Dict[str, Any],
        personality: Optional[PersonalityProfileSchema]
    ) -> float:
        """Calculate confidence level for memory recall."""
        
        base_confidence = memory.current_strength * memory.confidence_level
        
        # Time decay factor
        days_since = (datetime.utcnow() - memory.event_timestamp).days
        time_factor = max(0.1, 1.0 - (days_since * 0.01))
        
        # Context relevance
        context_bonus = 0.0
        if memory.location and context.get("location") == memory.location:
            context_bonus += 0.2
        if memory.participants:
            context_participants = context.get("participants", [])
            if any(p in memory.participants for p in context_participants):
                context_bonus += 0.3
                
        # Trigger strength
        trigger_bonus = 0.0
        if memory.keywords:
            trigger_words = trigger.lower().split()
            matching_keywords = [k for k in memory.keywords if any(tw in k.lower() for tw in trigger_words)]
            trigger_bonus = (len(matching_keywords) / len(memory.keywords)) * 0.2
            
        confidence = base_confidence * time_factor + context_bonus + trigger_bonus
        
        # Personality adjustments
        if personality:
            if personality.conscientiousness > 0.7:
                confidence *= 1.1  # More reliable recall
            if personality.neuroticism > 0.7:
                confidence *= 0.9  # Less confident in recall
                
        return max(0.0, min(1.0, confidence))

    async def _calculate_recall_accuracy(
        self,
        memory: MemorySchema,
        confidence: float
    ) -> float:
        """Calculate accuracy of memory recall."""
        
        # Base accuracy from memory's accuracy score
        base_accuracy = memory.accuracy_score
        
        # Confidence affects accuracy
        confidence_factor = 0.5 + (confidence * 0.5)
        
        # Strength affects accuracy
        strength_factor = 0.3 + (memory.current_strength * 0.7)
        
        # Importance affects accuracy (more important = more accurate)
        importance_factors = {
            MemoryImportance.CRITICAL: 1.0,
            MemoryImportance.SIGNIFICANT: 0.95,
            MemoryImportance.MODERATE: 0.85,
            MemoryImportance.MINOR: 0.7,
            MemoryImportance.TRIVIAL: 0.5
        }
        
        importance_factor = importance_factors.get(memory.importance, 0.8)
        
        accuracy = base_accuracy * confidence_factor * strength_factor * importance_factor
        
        # Add some random variation
        accuracy += random.uniform(-0.1, 0.1)
        
        return max(0.0, min(1.0, accuracy))

    async def _calculate_emotional_impact(
        self,
        memory: MemorySchema,
        context: Dict[str, Any]
    ) -> float:
        """Calculate emotional impact of recalling this memory."""
        
        base_impact = 0.5
        
        # Emotional memories have higher impact
        if memory.category == MemoryCategory.EMOTIONAL:
            base_impact += 0.3
            
        # Important memories have more impact
        importance_impacts = {
            MemoryImportance.CRITICAL: 0.4,
            MemoryImportance.SIGNIFICANT: 0.3,
            MemoryImportance.MODERATE: 0.1,
            MemoryImportance.MINOR: 0.0,
            MemoryImportance.TRIVIAL: -0.1
        }
        
        base_impact += importance_impacts.get(memory.importance, 0.0)
        
        # Context similarity increases impact
        if memory.associated_emotions:
            current_emotion = context.get("emotion")
            if current_emotion in memory.associated_emotions:
                base_impact += 0.2
                
        return max(0.0, min(1.0, base_impact))

    async def _extract_keywords(
        self,
        description: str,
        tags: Optional[List[str]] = None
    ) -> List[str]:
        """Extract keywords from memory description."""
        
        # Simple keyword extraction (in a real implementation, use NLP)
        words = description.lower().split()
        
        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "been", "be", "have", "has", "had"}
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Add tags as keywords
        if tags:
            keywords.extend(tags)
            
        # Remove duplicates and limit
        return list(set(keywords))[:10]

    async def _create_memory_associations(
        self,
        memory: MemorySchema,
        db_session: Optional[Session]
    ) -> None:
        """Create associations between this memory and existing memories."""
        
        # In a real implementation, this would find and create associations
        logger.info(f"Creating associations for memory {memory.id}")

    async def _find_associated_memories(
        self,
        memory_id: str,
        character_id: str
    ) -> List[str]:
        """Find memories associated with the given memory."""
        
        # In a real implementation, this would query associations
        return []

    async def _reinforce_memory(
        self,
        memory: MemorySchema
    ) -> None:
        """Reinforce a memory due to recall, increasing its strength."""
        
        # Increase strength slightly
        reinforcement = 0.05 * (1.0 - memory.current_strength)  # Diminishing returns
        memory.current_strength = min(1.0, memory.current_strength + reinforcement)
        memory.reinforcement_count += 1
        memory.last_recalled = datetime.utcnow()
        
        logger.debug(f"Reinforced memory {memory.id}, new strength: {memory.current_strength}")