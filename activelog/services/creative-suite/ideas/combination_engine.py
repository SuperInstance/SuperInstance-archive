"""
ActiveLog Creative Suite - Idea Combination Engine

This module provides intelligent idea combination and generation capabilities including:
- Semantic idea clustering and combination algorithms
- Cross-domain concept bridging and metaphor generation
- Constraint-based creative problem solving
- Idea evolution and mutation systems
- Collaborative idea merging and synthesis
- AI-powered concept expansion and exploration
- Domain-specific idea generators (art, writing, business, tech)
- Idea quality scoring and filtering
"""

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import nltk
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize, sent_tokenize

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IdeaDomain(Enum):
    """Creative domains for idea generation"""
    ART = "art"
    WRITING = "writing"
    MUSIC = "music"
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    DESIGN = "design"
    SCIENCE = "science"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    LIFESTYLE = "lifestyle"
    GENERAL = "general"


class IdeaType(Enum):
    """Types of creative ideas"""
    CONCEPT = "concept"
    SOLUTION = "solution"
    PRODUCT = "product"
    STORY = "story"
    ARTWORK = "artwork"
    COMPOSITION = "composition"
    INNOVATION = "innovation"
    METAPHOR = "metaphor"
    SYNTHESIS = "synthesis"


class CombinationMethod(Enum):
    """Methods for combining ideas"""
    SEMANTIC_MERGE = "semantic_merge"
    CONSTRAINT_BLEND = "constraint_blend"
    METAPHORICAL_BRIDGE = "metaphorical_bridge"
    EVOLUTIONARY_MUTATION = "evolutionary_mutation"
    DOMAIN_TRANSFER = "domain_transfer"
    OPPOSITIONAL_SYNTHESIS = "oppositional_synthesis"
    HIERARCHICAL_COMPOSITION = "hierarchical_composition"
    TEMPORAL_SEQUENCING = "temporal_sequencing"


class IdeaQuality(Enum):
    """Quality ratings for ideas"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"
    BREAKTHROUGH = "breakthrough"


@dataclass
class CreativeIdea:
    """Represents a creative idea with metadata"""
    idea_id: str
    title: str
    description: str
    domain: IdeaDomain
    idea_type: IdeaType
    keywords: List[str]
    concepts: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    inspirations: List[str] = field(default_factory=list)
    parent_ideas: List[str] = field(default_factory=list)  # IDs of parent ideas
    quality_score: float = 0.0  # 0-100
    novelty_score: float = 0.0  # 0-100
    feasibility_score: float = 0.0  # 0-100
    impact_score: float = 0.0  # 0-100
    user_rating: Optional[int] = None  # 1-5
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IdeaCombination:
    """Result of combining multiple ideas"""
    combination_id: str
    source_ideas: List[str]  # IDs of source ideas
    result_idea: CreativeIdea
    method: CombinationMethod
    confidence: float  # 0-1
    explanation: str
    semantic_similarity: float = 0.0
    novelty_increase: float = 0.0
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class IdeaCluster:
    """Cluster of related ideas"""
    cluster_id: str
    name: str
    ideas: List[str]  # IDs of ideas in cluster
    centroid_concepts: List[str]
    dominant_domain: IdeaDomain
    coherence_score: float
    diversity_score: float
    cluster_keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ConceptBridge:
    """Bridge between different concepts or domains"""
    bridge_id: str
    source_concept: str
    target_concept: str
    bridge_concepts: List[str]
    metaphorical_mapping: Dict[str, str]
    strength: float  # 0-1
    domain_transfer: bool = False
    examples: List[str] = field(default_factory=list)


@dataclass
class CreativeConstraint:
    """Constraint for creative problem solving"""
    constraint_id: str
    type: str  # "resource", "format", "theme", "audience", etc.
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    flexibility: float = 0.5  # How flexible this constraint is (0-1)
    priority: int = 1  # 1-5, where 1 is highest


@dataclass
class IdeaEvolution:
    """Evolution path of an idea through modifications"""
    evolution_id: str
    original_idea: str
    evolution_path: List[Tuple[str, str]]  # (idea_id, modification_type)
    final_idea: str
    improvement_score: float
    evolution_steps: int
    created_at: datetime = field(default_factory=datetime.now)


class IdeaGenerator(ABC):
    """Abstract base class for idea generators"""
    
    @abstractmethod
    async def generate_ideas(self, prompt: str, domain: IdeaDomain, 
                           constraints: List[CreativeConstraint], count: int = 5) -> List[CreativeIdea]:
        """Generate ideas based on prompt and constraints"""
        pass
    
    @abstractmethod
    async def expand_idea(self, idea: CreativeIdea, direction: str) -> List[CreativeIdea]:
        """Expand an idea in a specific direction"""
        pass


class IdeaCombinator(ABC):
    """Abstract base class for idea combination strategies"""
    
    @abstractmethod
    async def combine_ideas(self, ideas: List[CreativeIdea], 
                          method: CombinationMethod) -> IdeaCombination:
        """Combine multiple ideas using specified method"""
        pass
    
    @abstractmethod
    async def suggest_combinations(self, idea_pool: List[CreativeIdea]) -> List[Tuple[List[str], float]]:
        """Suggest promising idea combinations"""
        pass


class IdeaAnalyzer(ABC):
    """Abstract base class for idea analysis"""
    
    @abstractmethod
    async def analyze_idea(self, idea: CreativeIdea) -> Dict[str, float]:
        """Analyze idea quality, novelty, feasibility, etc."""
        pass
    
    @abstractmethod
    async def cluster_ideas(self, ideas: List[CreativeIdea]) -> List[IdeaCluster]:
        """Cluster ideas by similarity"""
        pass


class SemanticIdeaGenerator(IdeaGenerator):
    """Semantic-based idea generator using NLP techniques"""
    
    def __init__(self):
        self.domain_vocabularies = {
            IdeaDomain.ART: ["color", "composition", "texture", "form", "expression", "medium", "style"],
            IdeaDomain.TECHNOLOGY: ["algorithm", "interface", "system", "data", "automation", "innovation"],
            IdeaDomain.BUSINESS: ["market", "customer", "value", "revenue", "strategy", "optimization"],
            IdeaDomain.WRITING: ["character", "plot", "setting", "theme", "narrative", "dialogue"],
            IdeaDomain.MUSIC: ["melody", "rhythm", "harmony", "tempo", "genre", "instrument"]
        }
        
        self.concept_templates = {
            IdeaType.PRODUCT: "A {adjective} {noun} that {verb} {object} for {audience}",
            IdeaType.SOLUTION: "Use {method} to solve {problem} by {action}",
            IdeaType.STORY: "A story about {character} who {conflict} in {setting}",
            IdeaType.ARTWORK: "An artwork that represents {concept} through {medium} using {style}",
            IdeaType.INNOVATION: "Combine {technology1} with {technology2} to create {outcome}"
        }
    
    async def generate_ideas(self, prompt: str, domain: IdeaDomain, 
                           constraints: List[CreativeConstraint], count: int = 5) -> List[CreativeIdea]:
        """Generate ideas using semantic analysis and templates"""
        try:
            ideas = []
            domain_vocab = self.domain_vocabularies.get(domain, [])
            
            # Extract key concepts from prompt
            prompt_concepts = await self._extract_concepts(prompt)
            
            for i in range(count):
                # Generate idea using different approaches
                if i < count // 2:
                    # Template-based generation
                    idea = await self._generate_template_idea(prompt, domain, prompt_concepts, constraints)
                else:
                    # Concept combination generation
                    idea = await self._generate_concept_combination_idea(prompt_concepts, domain_vocab, domain, constraints)
                
                if idea:
                    ideas.append(idea)
            
            return ideas
            
        except Exception as e:
            logger.error(f"Error generating ideas: {e}")
            return []
    
    async def expand_idea(self, idea: CreativeIdea, direction: str) -> List[CreativeIdea]:
        """Expand an idea in specific directions"""
        try:
            expansions = []
            
            if direction == "broader":
                # Generalize the idea
                expanded = await self._generalize_idea(idea)
                expansions.extend(expanded)
            elif direction == "narrower":
                # Specialize the idea
                expanded = await self._specialize_idea(idea)
                expansions.extend(expanded)
            elif direction == "alternative":
                # Generate alternatives
                expanded = await self._generate_alternatives(idea)
                expansions.extend(expanded)
            elif direction == "opposite":
                # Generate opposite concepts
                expanded = await self._generate_opposites(idea)
                expansions.extend(expanded)
            
            return expansions
            
        except Exception as e:
            logger.error(f"Error expanding idea: {e}")
            return []
    
    async def _extract_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        try:
            # Simple keyword extraction (in production, use more sophisticated NLP)
            words = word_tokenize(text.lower())
            # Filter out common words and keep meaningful concepts
            concepts = [word for word in words if len(word) > 3 and word.isalpha()]
            return concepts[:10]  # Return top 10 concepts
        except:
            return []
    
    async def _generate_template_idea(self, prompt: str, domain: IdeaDomain, 
                                    concepts: List[str], constraints: List[CreativeConstraint]) -> Optional[CreativeIdea]:
        """Generate idea using templates"""
        try:
            # Choose random idea type
            idea_types = list(IdeaType)
            idea_type = random.choice(idea_types)
            
            # Get template
            template = self.concept_templates.get(idea_type, "An idea about {concept}")
            
            # Fill template with concepts and random elements
            domain_vocab = self.domain_vocabularies.get(domain, ["element", "component", "aspect"])
            
            placeholders = {
                "adjective": random.choice(["innovative", "elegant", "powerful", "intuitive", "creative"]),
                "noun": random.choice(domain_vocab),
                "verb": random.choice(["enhances", "transforms", "creates", "improves", "connects"]),
                "object": random.choice(concepts) if concepts else "experience",
                "audience": "users",
                "method": random.choice(["technology", "design", "process", "system"]),
                "problem": "challenges",
                "action": "innovation",
                "character": "protagonist",
                "conflict": "faces obstacles",
                "setting": "modern world",
                "concept": random.choice(concepts) if concepts else "creativity",
                "medium": random.choice(["digital", "physical", "interactive"]),
                "style": random.choice(["minimalist", "bold", "organic", "geometric"]),
                "technology1": "AI",
                "technology2": "blockchain",
                "outcome": "breakthrough"
            }
            
            # Fill template
            description = template
            for key, value in placeholders.items():
                description = description.replace(f"{{{key}}}", value)
            
            # Create idea
            idea = CreativeIdea(
                idea_id=str(uuid4()),
                title=f"{domain.value.title()} Idea: {description[:50]}...",
                description=description,
                domain=domain,
                idea_type=idea_type,
                keywords=concepts[:5],
                concepts=concepts,
                constraints=[c.description for c in constraints]
            )
            
            return idea
            
        except Exception as e:
            logger.error(f"Error generating template idea: {e}")
            return None
    
    async def _generate_concept_combination_idea(self, concepts: List[str], domain_vocab: List[str], 
                                               domain: IdeaDomain, constraints: List[CreativeConstraint]) -> Optional[CreativeIdea]:
        """Generate idea by combining concepts"""
        try:
            if len(concepts) < 2:
                concepts.extend(domain_vocab[:2])
            
            # Randomly combine concepts
            concept1 = random.choice(concepts)
            concept2 = random.choice([c for c in concepts if c != concept1])
            
            # Create combination description
            combination_patterns = [
                f"Combine {concept1} with {concept2} to create something new",
                f"Apply principles of {concept1} to {concept2}",
                f"What if {concept1} could be enhanced by {concept2}?",
                f"A {domain.value} project that bridges {concept1} and {concept2}",
                f"Reimagine {concept1} through the lens of {concept2}"
            ]
            
            description = random.choice(combination_patterns)
            
            idea = CreativeIdea(
                idea_id=str(uuid4()),
                title=f"Combination: {concept1.title()} + {concept2.title()}",
                description=description,
                domain=domain,
                idea_type=IdeaType.CONCEPT,
                keywords=[concept1, concept2],
                concepts=concepts,
                constraints=[c.description for c in constraints]
            )
            
            return idea
            
        except Exception as e:
            logger.error(f"Error generating concept combination idea: {e}")
            return None
    
    async def _generalize_idea(self, idea: CreativeIdea) -> List[CreativeIdea]:
        """Generate broader versions of the idea"""
        expansions = []
        
        generalization_prompts = [
            f"What broader category does this idea belong to?",
            f"How could this idea apply to other domains?",
            f"What's the general principle behind this idea?"
        ]
        
        for prompt in generalization_prompts:
            expanded = CreativeIdea(
                idea_id=str(uuid4()),
                title=f"Broader: {idea.title}",
                description=f"{prompt} {idea.description}",
                domain=idea.domain,
                idea_type=idea.idea_type,
                keywords=idea.keywords,
                parent_ideas=[idea.idea_id]
            )
            expansions.append(expanded)
        
        return expansions
    
    async def _specialize_idea(self, idea: CreativeIdea) -> List[CreativeIdea]:
        """Generate more specific versions of the idea"""
        expansions = []
        
        specialization_prompts = [
            f"How could this idea be implemented specifically?",
            f"What would be a concrete example of this idea?",
            f"How could this idea be customized for a specific audience?"
        ]
        
        for prompt in specialization_prompts:
            expanded = CreativeIdea(
                idea_id=str(uuid4()),
                title=f"Specific: {idea.title}",
                description=f"{prompt} {idea.description}",
                domain=idea.domain,
                idea_type=idea.idea_type,
                keywords=idea.keywords,
                parent_ideas=[idea.idea_id]
            )
            expansions.append(expanded)
        
        return expansions
    
    async def _generate_alternatives(self, idea: CreativeIdea) -> List[CreativeIdea]:
        """Generate alternative approaches to the same goal"""
        alternatives = []
        
        alternative_prompts = [
            f"What's another way to achieve the same goal?",
            f"How would someone else approach this differently?",
            f"What if we tried the opposite approach?"
        ]
        
        for prompt in alternative_prompts:
            alternative = CreativeIdea(
                idea_id=str(uuid4()),
                title=f"Alternative: {idea.title}",
                description=f"{prompt} {idea.description}",
                domain=idea.domain,
                idea_type=idea.idea_type,
                keywords=idea.keywords,
                parent_ideas=[idea.idea_id]
            )
            alternatives.append(alternative)
        
        return alternatives
    
    async def _generate_opposites(self, idea: CreativeIdea) -> List[CreativeIdea]:
        """Generate opposite concepts"""
        opposites = []
        
        # Simple opposite generation (in production, use more sophisticated semantic analysis)
        opposite_keywords = []
        for keyword in idea.keywords:
            # Basic opposites mapping
            opposites_map = {
                "big": "small", "fast": "slow", "simple": "complex",
                "digital": "analog", "automatic": "manual", "modern": "traditional"
            }
            opposite = opposites_map.get(keyword, f"non-{keyword}")
            opposite_keywords.append(opposite)
        
        opposite_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Opposite: {idea.title}",
            description=f"The opposite approach: {' '.join(opposite_keywords)}",
            domain=idea.domain,
            idea_type=idea.idea_type,
            keywords=opposite_keywords,
            parent_ideas=[idea.idea_id]
        )
        
        opposites.append(opposite_idea)
        return opposites


class IntelligentIdeaCombinator(IdeaCombinator):
    """Intelligent idea combination using multiple strategies"""
    
    def __init__(self):
        self.combination_strategies = {
            CombinationMethod.SEMANTIC_MERGE: self._semantic_merge,
            CombinationMethod.CONSTRAINT_BLEND: self._constraint_blend,
            CombinationMethod.METAPHORICAL_BRIDGE: self._metaphorical_bridge,
            CombinationMethod.EVOLUTIONARY_MUTATION: self._evolutionary_mutation,
            CombinationMethod.DOMAIN_TRANSFER: self._domain_transfer,
            CombinationMethod.OPPOSITIONAL_SYNTHESIS: self._oppositional_synthesis
        }
    
    async def combine_ideas(self, ideas: List[CreativeIdea], 
                          method: CombinationMethod) -> IdeaCombination:
        """Combine ideas using specified method"""
        try:
            if len(ideas) < 2:
                raise ValueError("Need at least 2 ideas to combine")
            
            strategy = self.combination_strategies.get(method)
            if not strategy:
                raise ValueError(f"Unknown combination method: {method}")
            
            result_idea, confidence, explanation = await strategy(ideas)
            
            # Calculate metrics
            semantic_similarity = await self._calculate_semantic_similarity(ideas)
            novelty_increase = await self._calculate_novelty_increase(ideas, result_idea)
            
            combination = IdeaCombination(
                combination_id=str(uuid4()),
                source_ideas=[idea.idea_id for idea in ideas],
                result_idea=result_idea,
                method=method,
                confidence=confidence,
                explanation=explanation,
                semantic_similarity=semantic_similarity,
                novelty_increase=novelty_increase
            )
            
            return combination
            
        except Exception as e:
            logger.error(f"Error combining ideas: {e}")
            # Return default combination
            return IdeaCombination(
                combination_id=str(uuid4()),
                source_ideas=[idea.idea_id for idea in ideas],
                result_idea=ideas[0],  # Fallback to first idea
                method=method,
                confidence=0.1,
                explanation=f"Combination failed: {str(e)}"
            )
    
    async def suggest_combinations(self, idea_pool: List[CreativeIdea]) -> List[Tuple[List[str], float]]:
        """Suggest promising idea combinations"""
        try:
            suggestions = []
            
            # Find complementary ideas
            for i, idea1 in enumerate(idea_pool):
                for j, idea2 in enumerate(idea_pool[i+1:], i+1):
                    compatibility = await self._calculate_compatibility(idea1, idea2)
                    if compatibility > 0.6:  # High compatibility threshold
                        suggestions.append(([idea1.idea_id, idea2.idea_id], compatibility))
            
            # Sort by compatibility score
            suggestions.sort(key=lambda x: x[1], reverse=True)
            
            return suggestions[:10]  # Return top 10 suggestions
            
        except Exception as e:
            logger.error(f"Error suggesting combinations: {e}")
            return []
    
    async def _semantic_merge(self, ideas: List[CreativeIdea]) -> Tuple[CreativeIdea, float, str]:
        """Merge ideas based on semantic similarity"""
        # Combine keywords and concepts
        all_keywords = []
        all_concepts = []
        
        for idea in ideas:
            all_keywords.extend(idea.keywords)
            all_concepts.extend(idea.concepts)
        
        # Remove duplicates while preserving order
        merged_keywords = list(dict.fromkeys(all_keywords))[:10]
        merged_concepts = list(dict.fromkeys(all_concepts))[:10]
        
        # Create merged description
        descriptions = [idea.description for idea in ideas]
        merged_description = f"A synthesis combining: {' AND '.join(descriptions[:2])}"
        
        # Choose dominant domain
        domains = [idea.domain for idea in ideas]
        dominant_domain = max(set(domains), key=domains.count)
        
        merged_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Semantic Merge: {' + '.join([idea.title[:20] for idea in ideas[:2]])}",
            description=merged_description,
            domain=dominant_domain,
            idea_type=IdeaType.SYNTHESIS,
            keywords=merged_keywords,
            concepts=merged_concepts,
            parent_ideas=[idea.idea_id for idea in ideas]
        )
        
        confidence = 0.8
        explanation = f"Merged {len(ideas)} ideas by combining their semantic elements"
        
        return merged_idea, confidence, explanation
    
    async def _constraint_blend(self, ideas: List[CreativeIdea]) -> Tuple[CreativeIdea, float, str]:
        """Blend ideas based on their constraints"""
        all_constraints = []
        for idea in ideas:
            all_constraints.extend(idea.constraints)
        
        # Remove duplicates
        unique_constraints = list(set(all_constraints))
        
        # Create constraint-based combination
        blended_description = f"An idea that satisfies multiple constraints: {', '.join(unique_constraints[:3])}"
        
        blended_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Constraint Blend: Multi-constraint Solution",
            description=blended_description,
            domain=ideas[0].domain,
            idea_type=IdeaType.SOLUTION,
            keywords=[kw for idea in ideas for kw in idea.keywords][:10],
            constraints=unique_constraints,
            parent_ideas=[idea.idea_id for idea in ideas]
        )
        
        confidence = 0.7
        explanation = f"Blended ideas to satisfy {len(unique_constraints)} different constraints"
        
        return blended_idea, confidence, explanation
    
    async def _metaphorical_bridge(self, ideas: List[CreativeIdea]) -> Tuple[CreativeIdea, float, str]:
        """Create metaphorical bridges between ideas"""
        idea1, idea2 = ideas[0], ideas[1]
        
        # Create metaphorical mapping
        metaphor_patterns = [
            f"If {idea1.title} is like {random.choice(['a river', 'a tree', 'a symphony'])}, then {idea2.title} is like {random.choice(['the ocean', 'a forest', 'an orchestra'])}",
            f"Imagine {idea1.title} as the foundation and {idea2.title} as the catalyst",
            f"Picture {idea1.title} and {idea2.title} as dance partners in creative expression"
        ]
        
        metaphor = random.choice(metaphor_patterns)
        
        bridge_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Metaphorical Bridge: {idea1.title[:20]} <-> {idea2.title[:20]}",
            description=f"A metaphorical connection: {metaphor}",
            domain=idea1.domain,
            idea_type=IdeaType.METAPHOR,
            keywords=idea1.keywords + idea2.keywords,
            parent_ideas=[idea1.idea_id, idea2.idea_id]
        )
        
        confidence = 0.6
        explanation = f"Created metaphorical bridge connecting different conceptual domains"
        
        return bridge_idea, confidence, explanation
    
    async def _evolutionary_mutation(self, ideas: List[CreativeIdea]) -> Tuple[CreativeIdea, float, str]:
        """Apply evolutionary mutations to ideas"""
        base_idea = ideas[0]
        
        # Apply random mutations
        mutation_types = ["amplify", "invert", "substitute", "combine"]
        mutation = random.choice(mutation_types)
        
        mutated_keywords = base_idea.keywords.copy()
        
        if mutation == "amplify":
            # Add intensity modifiers
            intensifiers = ["super", "ultra", "mega", "hyper", "extreme"]
            mutated_keywords = [f"{random.choice(intensifiers)}-{kw}" for kw in mutated_keywords[:3]]
        elif mutation == "invert":
            # Invert some concepts
            mutated_keywords = [f"anti-{kw}" for kw in mutated_keywords[:3]]
        elif mutation == "substitute":
            # Substitute random elements
            new_elements = ["quantum", "bio", "neural", "eco", "digital"]
            mutated_keywords[0] = random.choice(new_elements)
        
        mutated_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Evolved: {base_idea.title} ({mutation})",
            description=f"Evolutionary mutation ({mutation}): {base_idea.description}",
            domain=base_idea.domain,
            idea_type=IdeaType.INNOVATION,
            keywords=mutated_keywords,
            parent_ideas=[base_idea.idea_id]
        )
        
        confidence = 0.7
        explanation = f"Applied {mutation} mutation to evolve the original idea"
        
        return mutated_idea, confidence, explanation
    
    async def _domain_transfer(self, ideas: List[CreativeIdea]) -> Tuple[CreativeIdea, float, str]:
        """Transfer ideas between domains"""
        source_idea = ideas[0]
        target_domains = [d for d in IdeaDomain if d != source_idea.domain]
        target_domain = random.choice(target_domains)
        
        # Create domain transfer mapping
        transfer_description = f"Apply the principles of {source_idea.title} to {target_domain.value}"
        
        transferred_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Domain Transfer: {source_idea.title} -> {target_domain.value}",
            description=transfer_description,
            domain=target_domain,
            idea_type=IdeaType.INNOVATION,
            keywords=source_idea.keywords,
            parent_ideas=[source_idea.idea_id]
        )
        
        confidence = 0.8
        explanation = f"Transferred idea from {source_idea.domain.value} to {target_domain.value}"
        
        return transferred_idea, confidence, explanation
    
    async def _oppositional_synthesis(self, ideas: List[CreativeIdea]) -> Tuple[CreativeIdea, float, str]:
        """Synthesize opposing ideas"""
        if len(ideas) < 2:
            return ideas[0], 0.1, "Need multiple ideas for oppositional synthesis"
        
        idea1, idea2 = ideas[0], ideas[1]
        
        # Create synthesis of opposites
        synthesis_description = f"A creative tension between {idea1.title} and {idea2.title}, finding harmony in contradiction"
        
        synthesis_idea = CreativeIdea(
            idea_id=str(uuid4()),
            title=f"Synthesis: {idea1.title[:15]} ↔ {idea2.title[:15]}",
            description=synthesis_description,
            domain=idea1.domain,
            idea_type=IdeaType.SYNTHESIS,
            keywords=idea1.keywords + idea2.keywords,
            parent_ideas=[idea1.idea_id, idea2.idea_id]
        )
        
        confidence = 0.75
        explanation = "Synthesized opposing concepts to create creative tension"
        
        return synthesis_idea, confidence, explanation
    
    async def _calculate_semantic_similarity(self, ideas: List[CreativeIdea]) -> float:
        """Calculate semantic similarity between ideas"""
        try:
            # Simple similarity based on keyword overlap
            if len(ideas) < 2:
                return 0.0
            
            idea1_keywords = set(ideas[0].keywords)
            idea2_keywords = set(ideas[1].keywords)
            
            if not idea1_keywords and not idea2_keywords:
                return 0.0
            
            intersection = len(idea1_keywords.intersection(idea2_keywords))
            union = len(idea1_keywords.union(idea2_keywords))
            
            return intersection / union if union > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    async def _calculate_novelty_increase(self, source_ideas: List[CreativeIdea], result_idea: CreativeIdea) -> float:
        """Calculate how much novelty was added by combination"""
        try:
            # Simple novelty calculation based on new keywords
            source_keywords = set()
            for idea in source_ideas:
                source_keywords.update(idea.keywords)
            
            result_keywords = set(result_idea.keywords)
            new_keywords = result_keywords - source_keywords
            
            return len(new_keywords) / max(len(result_keywords), 1)
            
        except Exception as e:
            logger.error(f"Error calculating novelty: {e}")
            return 0.0
    
    async def _calculate_compatibility(self, idea1: CreativeIdea, idea2: CreativeIdea) -> float:
        """Calculate compatibility between two ideas"""
        try:
            compatibility_score = 0.0
            
            # Domain compatibility
            if idea1.domain == idea2.domain:
                compatibility_score += 0.3
            
            # Keyword overlap (but not too much)
            keyword_overlap = len(set(idea1.keywords).intersection(set(idea2.keywords)))
            if 1 <= keyword_overlap <= 3:  # Sweet spot for combination
                compatibility_score += 0.4
            
            # Different idea types are more interesting to combine
            if idea1.idea_type != idea2.idea_type:
                compatibility_score += 0.3
            
            return min(compatibility_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating compatibility: {e}")
            return 0.0


class ComprehensiveIdeaAnalyzer(IdeaAnalyzer):
    """Comprehensive idea analysis and clustering"""
    
    def __init__(self):
        self.quality_factors = {
            "keyword_richness": 0.15,
            "concept_depth": 0.20,
            "domain_relevance": 0.15,
            "novelty_indicators": 0.25,
            "feasibility_markers": 0.15,
            "impact_potential": 0.10
        }
    
    async def analyze_idea(self, idea: CreativeIdea) -> Dict[str, float]:
        """Comprehensive idea analysis"""
        try:
            analysis = {}
            
            # Quality analysis
            analysis["quality_score"] = await self._calculate_quality(idea)
            
            # Novelty analysis
            analysis["novelty_score"] = await self._calculate_novelty(idea)
            
            # Feasibility analysis
            analysis["feasibility_score"] = await self._calculate_feasibility(idea)
            
            # Impact analysis
            analysis["impact_score"] = await self._calculate_impact(idea)
            
            # Overall score (weighted combination)
            analysis["overall_score"] = (
                analysis["quality_score"] * 0.3 +
                analysis["novelty_score"] * 0.3 +
                analysis["feasibility_score"] * 0.2 +
                analysis["impact_score"] * 0.2
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing idea: {e}")
            return {"overall_score": 50.0, "quality_score": 50.0, "novelty_score": 50.0, 
                   "feasibility_score": 50.0, "impact_score": 50.0}
    
    async def cluster_ideas(self, ideas: List[CreativeIdea]) -> List[IdeaCluster]:
        """Cluster ideas by semantic similarity"""
        try:
            if len(ideas) < 3:
                # Not enough ideas for meaningful clustering
                cluster = IdeaCluster(
                    cluster_id=str(uuid4()),
                    name="Small Collection",
                    ideas=[idea.idea_id for idea in ideas],
                    centroid_concepts=[kw for idea in ideas for kw in idea.keywords],
                    dominant_domain=ideas[0].domain if ideas else IdeaDomain.GENERAL,
                    coherence_score=1.0,
                    diversity_score=0.5
                )
                return [cluster]
            
            # Extract features for clustering
            features = []
            idea_ids = []
            
            for idea in ideas:
                # Create feature vector from keywords and concepts
                feature_text = " ".join(idea.keywords + idea.concepts + [idea.description])
                features.append(feature_text)
                idea_ids.append(idea.idea_id)
            
            # Use TF-IDF for feature extraction
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            feature_matrix = vectorizer.fit_transform(features)
            
            # Determine optimal number of clusters
            n_clusters = min(5, len(ideas) // 2)
            
            # Perform clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(feature_matrix)
            
            # Create cluster objects
            clusters = []
            for cluster_id in range(n_clusters):
                cluster_ideas = [idea_ids[i] for i, label in enumerate(cluster_labels) if label == cluster_id]
                cluster_idea_objects = [idea for idea in ideas if idea.idea_id in cluster_ideas]
                
                # Calculate cluster properties
                all_keywords = []
                domains = []
                for idea in cluster_idea_objects:
                    all_keywords.extend(idea.keywords)
                    domains.append(idea.domain)
                
                # Find most common keywords and domain
                keyword_counts = {}
                for kw in all_keywords:
                    keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
                
                top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:5]
                centroid_concepts = [kw for kw, count in top_keywords]
                
                dominant_domain = max(set(domains), key=domains.count) if domains else IdeaDomain.GENERAL
                
                # Calculate coherence and diversity
                coherence_score = await self._calculate_cluster_coherence(cluster_idea_objects)
                diversity_score = await self._calculate_cluster_diversity(cluster_idea_objects)
                
                cluster = IdeaCluster(
                    cluster_id=str(uuid4()),
                    name=f"Cluster {cluster_id + 1}: {centroid_concepts[0] if centroid_concepts else 'Mixed'}",
                    ideas=cluster_ideas,
                    centroid_concepts=centroid_concepts,
                    dominant_domain=dominant_domain,
                    coherence_score=coherence_score,
                    diversity_score=diversity_score,
                    cluster_keywords=[kw for kw, count in top_keywords]
                )
                
                clusters.append(cluster)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error clustering ideas: {e}")
            # Return single cluster as fallback
            return [IdeaCluster(
                cluster_id=str(uuid4()),
                name="All Ideas",
                ideas=[idea.idea_id for idea in ideas],
                centroid_concepts=[],
                dominant_domain=IdeaDomain.GENERAL,
                coherence_score=0.5,
                diversity_score=0.5
            )]
    
    async def _calculate_quality(self, idea: CreativeIdea) -> float:
        """Calculate idea quality score"""
        quality_score = 0.0
        
        # Keyword richness
        quality_score += min(len(idea.keywords) * 10, 30)
        
        # Description length (more detailed = higher quality)
        quality_score += min(len(idea.description) / 10, 20)
        
        # Concept depth
        quality_score += min(len(idea.concepts) * 5, 25)
        
        # Has constraints (shows thinking)
        if idea.constraints:
            quality_score += 15
        
        # Has inspiration sources
        if idea.inspirations:
            quality_score += 10
        
        return min(quality_score, 100.0)
    
    async def _calculate_novelty(self, idea: CreativeIdea) -> float:
        """Calculate idea novelty score"""
        novelty_score = 50.0  # Base score
        
        # Uncommon keywords increase novelty
        uncommon_keywords = ["quantum", "neural", "bio", "eco", "meta", "hyper"]
        novelty_score += len([kw for kw in idea.keywords if any(uk in kw for uk in uncommon_keywords)]) * 10
        
        # Cross-domain concepts increase novelty
        if len(set([kw[:3] for kw in idea.keywords])) > 3:  # Diverse prefixes
            novelty_score += 15
        
        # Complex combinations increase novelty
        if "+" in idea.title or "hybrid" in idea.description.lower():
            novelty_score += 20
        
        return min(novelty_score, 100.0)
    
    async def _calculate_feasibility(self, idea: CreativeIdea) -> float:
        """Calculate idea feasibility score"""
        feasibility_score = 70.0  # Start optimistic
        
        # Very abstract concepts are less feasible
        abstract_indicators = ["metaphysical", "transcendent", "infinite", "absolute"]
        feasibility_score -= len([kw for kw in idea.keywords if kw in abstract_indicators]) * 20
        
        # Realistic constraints increase feasibility
        if idea.constraints:
            realistic_constraints = ["budget", "time", "resources", "technology"]
            feasibility_score += len([c for c in idea.constraints if any(rc in c.lower() for rc in realistic_constraints)]) * 10
        
        # Domain-specific feasibility
        if idea.domain in [IdeaDomain.TECHNOLOGY, IdeaDomain.BUSINESS]:
            feasibility_score += 10  # More concrete domains
        elif idea.domain in [IdeaDomain.ART, IdeaDomain.WRITING]:
            feasibility_score += 15  # Very feasible creative domains
        
        return min(max(feasibility_score, 0), 100.0)
    
    async def _calculate_impact(self, idea: CreativeIdea) -> float:
        """Calculate potential impact score"""
        impact_score = 50.0  # Base score
        
        # Impact-related keywords
        impact_keywords = ["revolutionary", "breakthrough", "transform", "disrupt", "innovate"]
        impact_score += len([kw for kw in idea.keywords + [idea.description.lower()] if any(ik in kw for ik in impact_keywords)]) * 15
        
        # Broad application domains have higher impact
        broad_domains = [IdeaDomain.TECHNOLOGY, IdeaDomain.EDUCATION, IdeaDomain.BUSINESS]
        if idea.domain in broad_domains:
            impact_score += 20
        
        # Solutions typically have higher impact than concepts
        if idea.idea_type in [IdeaType.SOLUTION, IdeaType.INNOVATION]:
            impact_score += 15
        
        return min(impact_score, 100.0)
    
    async def _calculate_cluster_coherence(self, ideas: List[CreativeIdea]) -> float:
        """Calculate how coherent a cluster is"""
        if len(ideas) <= 1:
            return 1.0
        
        # Calculate average pairwise similarity
        similarities = []
        for i, idea1 in enumerate(ideas):
            for idea2 in ideas[i+1:]:
                similarity = len(set(idea1.keywords).intersection(set(idea2.keywords))) / max(len(set(idea1.keywords).union(set(idea2.keywords))), 1)
                similarities.append(similarity)
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    async def _calculate_cluster_diversity(self, ideas: List[CreativeIdea]) -> float:
        """Calculate how diverse a cluster is"""
        if len(ideas) <= 1:
            return 0.0
        
        # Count unique domains, types, and keywords
        unique_domains = len(set(idea.domain for idea in ideas))
        unique_types = len(set(idea.idea_type for idea in ideas))
        all_keywords = set()
        for idea in ideas:
            all_keywords.update(idea.keywords)
        
        # Normalize by cluster size
        diversity_score = (unique_domains + unique_types + len(all_keywords)) / (len(ideas) * 3)
        
        return min(diversity_score, 1.0)


class IdeaCombinationEngine:
    """Main idea combination engine service"""
    
    def __init__(self,
                 idea_generator: IdeaGenerator,
                 idea_combinator: IdeaCombinator,
                 idea_analyzer: IdeaAnalyzer):
        self.idea_generator = idea_generator
        self.idea_combinator = idea_combinator
        self.idea_analyzer = idea_analyzer
        
        # In-memory storage (replace with database in production)
        self.ideas: Dict[str, CreativeIdea] = {}
        self.combinations: Dict[str, IdeaCombination] = {}
        self.clusters: List[IdeaCluster] = []
        self.concept_bridges: Dict[str, ConceptBridge] = {}
        self.idea_evolutions: Dict[str, IdeaEvolution] = {}
        
        # User context
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.user_ideas: Dict[str, List[str]] = {}  # user_id -> [idea_ids]
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
    
    async def start(self):
        """Start the idea combination engine service"""
        if self._running:
            return
        
        self._running = True
        logger.info("Starting Idea Combination Engine")
        
        # Start background tasks
        self._background_tasks = [
            asyncio.create_task(self._periodic_clustering()),
            asyncio.create_task(self._generate_suggestion_combinations()),
            asyncio.create_task(self._evolve_ideas())
        ]
    
    async def stop(self):
        """Stop the idea combination engine service"""
        if not self._running:
            return
        
        self._running = False
        logger.info("Stopping Idea Combination Engine")
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()
    
    async def generate_ideas(self, user_id: str, prompt: str, domain: IdeaDomain,
                           constraints: List[CreativeConstraint] = None,
                           count: int = 5) -> List[CreativeIdea]:
        """Generate new ideas based on prompt"""
        try:
            if constraints is None:
                constraints = []
            
            # Generate ideas
            ideas = await self.idea_generator.generate_ideas(prompt, domain, constraints, count)
            
            # Analyze and score ideas
            for idea in ideas:
                idea.created_by = user_id
                analysis = await self.idea_analyzer.analyze_idea(idea)
                idea.quality_score = analysis.get("quality_score", 0)
                idea.novelty_score = analysis.get("novelty_score", 0)
                idea.feasibility_score = analysis.get("feasibility_score", 0)
                idea.impact_score = analysis.get("impact_score", 0)
                
                # Store idea
                self.ideas[idea.idea_id] = idea
                
                # Associate with user
                if user_id not in self.user_ideas:
                    self.user_ideas[user_id] = []
                self.user_ideas[user_id].append(idea.idea_id)
            
            logger.info(f"Generated {len(ideas)} ideas for user {user_id}")
            return ideas
            
        except Exception as e:
            logger.error(f"Error generating ideas: {e}")
            return []
    
    async def combine_ideas(self, user_id: str, idea_ids: List[str], 
                          method: CombinationMethod) -> Optional[IdeaCombination]:
        """Combine multiple ideas"""
        try:
            # Get ideas
            ideas = []
            for idea_id in idea_ids:
                if idea_id in self.ideas:
                    ideas.append(self.ideas[idea_id])
                else:
                    logger.warning(f"Idea {idea_id} not found")
            
            if len(ideas) < 2:
                logger.warning("Need at least 2 ideas to combine")
                return None
            
            # Perform combination
            combination = await self.idea_combinator.combine_ideas(ideas, method)
            
            # Analyze result
            analysis = await self.idea_analyzer.analyze_idea(combination.result_idea)
            combination.result_idea.quality_score = analysis.get("quality_score", 0)
            combination.result_idea.novelty_score = analysis.get("novelty_score", 0)
            combination.result_idea.created_by = user_id
            
            # Store combination and result idea
            self.combinations[combination.combination_id] = combination
            self.ideas[combination.result_idea.idea_id] = combination.result_idea
            
            # Associate result with user
            if user_id not in self.user_ideas:
                self.user_ideas[user_id] = []
            self.user_ideas[user_id].append(combination.result_idea.idea_id)
            
            logger.info(f"Combined {len(ideas)} ideas using {method.value}")
            return combination
            
        except Exception as e:
            logger.error(f"Error combining ideas: {e}")
            return None
    
    async def expand_idea(self, user_id: str, idea_id: str, direction: str) -> List[CreativeIdea]:
        """Expand an idea in specified direction"""
        try:
            if idea_id not in self.ideas:
                logger.warning(f"Idea {idea_id} not found")
                return []
            
            base_idea = self.ideas[idea_id]
            expanded_ideas = await self.idea_generator.expand_idea(base_idea, direction)
            
            # Process expanded ideas
            for idea in expanded_ideas:
                idea.created_by = user_id
                analysis = await self.idea_analyzer.analyze_idea(idea)
                idea.quality_score = analysis.get("quality_score", 0)
                idea.novelty_score = analysis.get("novelty_score", 0)
                
                # Store idea
                self.ideas[idea.idea_id] = idea
                
                # Associate with user
                if user_id not in self.user_ideas:
                    self.user_ideas[user_id] = []
                self.user_ideas[user_id].append(idea.idea_id)
            
            logger.info(f"Expanded idea {idea_id} in direction '{direction}' -> {len(expanded_ideas)} new ideas")
            return expanded_ideas
            
        except Exception as e:
            logger.error(f"Error expanding idea: {e}")
            return []
    
    async def get_combination_suggestions(self, user_id: str) -> List[Tuple[List[str], float]]:
        """Get suggested idea combinations for user"""
        try:
            # Get user's ideas
            user_idea_ids = self.user_ideas.get(user_id, [])
            user_ideas = [self.ideas[idea_id] for idea_id in user_idea_ids if idea_id in self.ideas]
            
            if len(user_ideas) < 2:
                return []
            
            # Get suggestions
            suggestions = await self.idea_combinator.suggest_combinations(user_ideas)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting combination suggestions: {e}")
            return []
    
    async def get_idea_clusters(self, user_id: str) -> List[IdeaCluster]:
        """Get idea clusters for user"""
        try:
            # Get user's ideas
            user_idea_ids = self.user_ideas.get(user_id, [])
            user_ideas = [self.ideas[idea_id] for idea_id in user_idea_ids if idea_id in self.ideas]
            
            if len(user_ideas) < 3:
                return []
            
            # Cluster ideas
            clusters = await self.idea_analyzer.cluster_ideas(user_ideas)
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error getting idea clusters: {e}")
            return []
    
    async def search_ideas(self, query: str, domain: Optional[IdeaDomain] = None,
                         user_id: Optional[str] = None) -> List[CreativeIdea]:
        """Search for ideas matching query"""
        try:
            query_lower = query.lower()
            matching_ideas = []
            
            # Determine search scope
            if user_id and user_id in self.user_ideas:
                search_ideas = [self.ideas[idea_id] for idea_id in self.user_ideas[user_id] if idea_id in self.ideas]
            else:
                search_ideas = list(self.ideas.values())
            
            # Search through ideas
            for idea in search_ideas:
                # Check domain filter
                if domain and idea.domain != domain:
                    continue
                
                # Search in title, description, keywords, and concepts
                searchable_text = " ".join([
                    idea.title.lower(),
                    idea.description.lower(),
                    " ".join(idea.keywords).lower(),
                    " ".join(idea.concepts).lower()
                ])
                
                if query_lower in searchable_text:
                    matching_ideas.append(idea)
            
            # Sort by relevance (simple scoring)
            def relevance_score(idea):
                score = 0
                if query_lower in idea.title.lower():
                    score += 10
                if query_lower in idea.description.lower():
                    score += 5
                score += sum(1 for kw in idea.keywords if query_lower in kw.lower())
                return score
            
            matching_ideas.sort(key=relevance_score, reverse=True)
            
            return matching_ideas[:20]  # Return top 20 matches
            
        except Exception as e:
            logger.error(f"Error searching ideas: {e}")
            return []
    
    async def rate_idea(self, user_id: str, idea_id: str, rating: int) -> bool:
        """Rate an idea (1-5 scale)"""
        try:
            if idea_id not in self.ideas:
                return False
            
            if not 1 <= rating <= 5:
                return False
            
            idea = self.ideas[idea_id]
            idea.user_rating = rating
            idea.updated_at = datetime.now()
            
            logger.info(f"User {user_id} rated idea {idea_id}: {rating}/5")
            return True
            
        except Exception as e:
            logger.error(f"Error rating idea: {e}")
            return False
    
    async def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get user's idea statistics"""
        try:
            user_idea_ids = self.user_ideas.get(user_id, [])
            user_ideas = [self.ideas[idea_id] for idea_id in user_idea_ids if idea_id in self.ideas]
            
            if not user_ideas:
                return {}
            
            # Calculate statistics
            total_ideas = len(user_ideas)
            avg_quality = sum(idea.quality_score for idea in user_ideas) / total_ideas
            avg_novelty = sum(idea.novelty_score for idea in user_ideas) / total_ideas
            
            # Domain distribution
            domain_counts = {}
            for idea in user_ideas:
                domain = idea.domain.value
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            # Type distribution
            type_counts = {}
            for idea in user_ideas:
                idea_type = idea.idea_type.value
                type_counts[idea_type] = type_counts.get(idea_type, 0) + 1
            
            # Recent activity
            recent_ideas = [idea for idea in user_ideas if (datetime.now() - idea.created_at).days <= 7]
            
            # Combination statistics
            user_combinations = [combo for combo in self.combinations.values() 
                               if combo.result_idea.created_by == user_id]
            
            return {
                "total_ideas": total_ideas,
                "average_quality": avg_quality,
                "average_novelty": avg_novelty,
                "domain_distribution": domain_counts,
                "type_distribution": type_counts,
                "recent_ideas_count": len(recent_ideas),
                "total_combinations": len(user_combinations),
                "most_productive_domain": max(domain_counts.items(), key=lambda x: x[1])[0] if domain_counts else None,
                "creativity_streak": len(recent_ideas)  # Simple streak calculation
            }
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
    
    async def _periodic_clustering(self):
        """Background task for periodic idea clustering"""
        while self._running:
            try:
                # Cluster all ideas periodically
                all_ideas = list(self.ideas.values())
                
                if len(all_ideas) >= 10:  # Only cluster if we have enough ideas
                    self.clusters = await self.idea_analyzer.cluster_ideas(all_ideas)
                    logger.info(f"Updated global clusters: {len(self.clusters)} clusters")
                
                # Wait 6 hours before next clustering
                await asyncio.sleep(21600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic clustering: {e}")
                await asyncio.sleep(21600)
    
    async def _generate_suggestion_combinations(self):
        """Background task to generate combination suggestions"""
        while self._running:
            try:
                # Generate suggestions for active users
                for user_id, idea_ids in self.user_ideas.items():
                    if len(idea_ids) >= 2:
                        user_ideas = [self.ideas[idea_id] for idea_id in idea_ids if idea_id in self.ideas]
                        suggestions = await self.idea_combinator.suggest_combinations(user_ideas)
                        
                        if suggestions:
                            logger.info(f"Generated {len(suggestions)} combination suggestions for user {user_id}")
                
                # Wait 12 hours before next suggestion generation
                await asyncio.sleep(43200)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error generating suggestions: {e}")
                await asyncio.sleep(43200)
    
    async def _evolve_ideas(self):
        """Background task to evolve ideas through mutations"""
        while self._running:
            try:
                # Select ideas for evolution (high quality, older ideas)
                evolution_candidates = []
                
                for idea in self.ideas.values():
                    age_days = (datetime.now() - idea.created_at).days
                    if idea.quality_score > 70 and age_days > 1:  # High quality, at least 1 day old
                        evolution_candidates.append(idea)
                
                # Evolve a few ideas
                for idea in evolution_candidates[:5]:  # Limit to 5 evolutions per cycle
                    try:
                        evolved_ideas = await self.idea_generator.expand_idea(idea, "alternative")
                        
                        for evolved_idea in evolved_ideas:
                            evolved_idea.created_by = idea.created_by
                            analysis = await self.idea_analyzer.analyze_idea(evolved_idea)
                            evolved_idea.quality_score = analysis.get("quality_score", 0)
                            
                            # Only keep if it's an improvement
                            if evolved_idea.quality_score > idea.quality_score:
                                self.ideas[evolved_idea.idea_id] = evolved_idea
                                
                                # Add to user's ideas
                                user_id = idea.created_by
                                if user_id in self.user_ideas:
                                    self.user_ideas[user_id].append(evolved_idea.idea_id)
                                
                                logger.info(f"Evolved idea {idea.idea_id} -> {evolved_idea.idea_id}")
                        
                    except Exception as e:
                        logger.error(f"Error evolving idea {idea.idea_id}: {e}")
                
                # Wait 24 hours before next evolution cycle
                await asyncio.sleep(86400)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in idea evolution: {e}")
                await asyncio.sleep(86400)


# Singleton instance
_idea_combination_engine_instance: Optional[IdeaCombinationEngine] = None


def get_idea_combination_engine() -> IdeaCombinationEngine:
    """Get the singleton idea combination engine instance"""
    global _idea_combination_engine_instance
    
    if _idea_combination_engine_instance is None:
        # Initialize with default implementations
        idea_generator = SemanticIdeaGenerator()
        idea_combinator = IntelligentIdeaCombinator()
        idea_analyzer = ComprehensiveIdeaAnalyzer()
        
        _idea_combination_engine_instance = IdeaCombinationEngine(
            idea_generator=idea_generator,
            idea_combinator=idea_combinator,
            idea_analyzer=idea_analyzer
        )
    
    return _idea_combination_engine_instance


async def main():
    """Example usage of the idea combination engine"""
    engine = get_idea_combination_engine()
    
    try:
        await engine.start()
        
        user_id = "creative_user_123"
        
        # Example 1: Generate initial ideas
        print("=== Generating Ideas ===")
        constraints = [
            CreativeConstraint(
                constraint_id=str(uuid4()),
                type="budget",
                description="Low budget solution",
                parameters={"max_cost": 1000}
            )
        ]
        
        ideas = await engine.generate_ideas(
            user_id=user_id,
            prompt="Create an innovative mobile app for artists",
            domain=IdeaDomain.TECHNOLOGY,
            constraints=constraints,
            count=3
        )
        
        for idea in ideas:
            print(f"Idea: {idea.title}")
            print(f"Description: {idea.description}")
            print(f"Quality: {idea.quality_score:.1f}, Novelty: {idea.novelty_score:.1f}")
            print("---")
        
        if len(ideas) >= 2:
            # Example 2: Combine ideas
            print("=== Combining Ideas ===")
            combination = await engine.combine_ideas(
                user_id=user_id,
                idea_ids=[ideas[0].idea_id, ideas[1].idea_id],
                method=CombinationMethod.SEMANTIC_MERGE
            )
            
            if combination:
                print(f"Combined Idea: {combination.result_idea.title}")
                print(f"Description: {combination.result_idea.description}")
                print(f"Confidence: {combination.confidence:.2f}")
                print(f"Explanation: {combination.explanation}")
                print("---")
            
            # Example 3: Expand an idea
            print("=== Expanding Ideas ===")
            expanded = await engine.expand_idea(
                user_id=user_id,
                idea_id=ideas[0].idea_id,
                direction="alternative"
            )
            
            for exp_idea in expanded:
                print(f"Expanded: {exp_idea.title}")
                print(f"Description: {exp_idea.description}")
                print("---")
            
            # Example 4: Get combination suggestions
            print("=== Combination Suggestions ===")
            suggestions = await engine.get_combination_suggestions(user_id)
            
            for suggestion, score in suggestions:
                print(f"Suggested combination: {suggestion} (score: {score:.2f})")
            
            # Example 5: Search ideas
            print("=== Searching Ideas ===")
            search_results = await engine.search_ideas("mobile app", IdeaDomain.TECHNOLOGY, user_id)
            
            for result in search_results[:3]:
                print(f"Found: {result.title}")
                print(f"Description: {result.description[:100]}...")
                print("---")
            
            # Example 6: Rate an idea
            await engine.rate_idea(user_id, ideas[0].idea_id, 4)
            print(f"Rated idea {ideas[0].title}: 4/5")
            
            # Example 7: Get user statistics
            print("=== User Statistics ===")
            stats = await engine.get_user_statistics(user_id)
            
            for key, value in stats.items():
                print(f"{key}: {value}")
        
        # Let background tasks run briefly
        await asyncio.sleep(5)
        
    finally:
        await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())