"""
Hierarchical Knowledge Graph with Semantic Compression
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
import hashlib
import re
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class Concept:
    concept_id: str
    content: str
    category: str
    references: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    compression_level: str = "medium"  # low, medium, high, max
    original_content: Optional[str] = None
    semantic_tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0
    quality_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "content": self.content,
            "category": self.category,
            "references": self.references,
            "aliases": self.aliases,
            "compression_level": self.compression_level,
            "semantic_tags": self.semantic_tags,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "access_count": self.access_count,
            "quality_score": self.quality_score
        }

@dataclass
class ConceptLink:
    from_concept: str
    to_concept: str
    relationship_type: str  # "references", "extends", "implements", "uses", "contains"
    strength: float = 1.0
    context: str = ""

class KnowledgeGraph:
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.links: List[ConceptLink] = []
        self.categories: Set[str] = set()
        self.semantic_index: Dict[str, Set[str]] = {}  # keyword -> concept_ids
        self.compression_patterns: Dict[str, str] = self._load_compression_patterns()
        
    def _load_compression_patterns(self) -> Dict[str, str]:
        """Load common compression patterns for semantic aliases"""
        return {
            # Technical abbreviations
            "authentication": "auth",
            "authorization": "authz", 
            "configuration": "config",
            "database": "db",
            "application": "app",
            "service": "svc",
            "management": "mgmt",
            "administration": "admin",
            "development": "dev",
            "production": "prod",
            "environment": "env",
            "repository": "repo",
            "documentation": "docs",
            "interface": "iface",
            "implementation": "impl",
            "specification": "spec",
            "optimization": "opt",
            "performance": "perf",
            "security": "sec",
            "monitoring": "mon",
            "logging": "log",
            
            # Domain-specific
            "artificial_intelligence": "ai",
            "machine_learning": "ml",
            "natural_language_processing": "nlp",
            "application_programming_interface": "api",
            "representational_state_transfer": "rest",
            "javascript_object_notation": "json",
            "extensible_markup_language": "xml",
            "hypertext_transfer_protocol": "http",
            "secure_sockets_layer": "ssl",
            "transport_layer_security": "tls",
            "structured_query_language": "sql",
            "object_relational_mapping": "orm",
            
            # ActiveLog-specific
            "bot_orchestrator": "bot-orch",
            "luciddreamer": "lucid",
            "dream_simulator": "dream-sim",
            "business_platform": "biz-plat",
            "municipal_platform": "muni-plat",
            "dividend_shares": "div-shares",
            "paper_trading": "paper-trade",
            "code_director": "code-dir",
            "project_memory": "proj-mem"
        }
    
    async def create_concept(
        self, 
        content: str, 
        category: str = "CORE", 
        references: List[str] = None,
        compression_level: str = "medium"
    ) -> Optional[str]:
        """Create new concept with automatic ID generation and compression"""
        try:
            # Generate concept ID
            category_prefix = category.replace(" ", "_").upper()
            existing_count = len([c for c in self.concepts.values() if c.category == category])
            concept_id = f"{category_prefix}-{existing_count + 1:03d}"
            
            # Apply semantic compression based on level
            original_content = content
            compressed_content = await self._compress_content(content, compression_level)
            
            # Extract semantic tags
            semantic_tags = await self._extract_semantic_tags(content)
            
            # Generate aliases
            aliases = await self._generate_aliases(content)
            
            concept = Concept(
                concept_id=concept_id,
                content=compressed_content,
                category=category,
                references=references or [],
                aliases=aliases,
                compression_level=compression_level,
                original_content=original_content,
                semantic_tags=semantic_tags,
                quality_score=await self._calculate_quality_score(content)
            )
            
            self.concepts[concept_id] = concept
            self.categories.add(category)
            
            # Update semantic index
            await self._update_semantic_index(concept_id, semantic_tags + aliases)
            
            # Create reference links
            if references:
                for ref in references:
                    if ref in self.concepts:
                        link = ConceptLink(
                            from_concept=concept_id,
                            to_concept=ref,
                            relationship_type="references"
                        )
                        self.links.append(link)
            
            logger.info(f"Created concept {concept_id} with {len(aliases)} aliases")
            return concept_id
            
        except Exception as e:
            logger.error(f"Failed to create concept: {e}")
            return None
    
    async def get_concept(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve concept with access tracking"""
        if concept_id not in self.concepts:
            return None
        
        concept = self.concepts[concept_id]
        concept.access_count += 1
        concept.last_updated = datetime.now(timezone.utc)
        
        return concept.to_dict()
    
    async def semantic_search(
        self, 
        query: str, 
        category: Optional[str] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Semantic search with relevance scoring"""
        query_terms = set(query.lower().split())
        scored_concepts = []
        
        for concept_id, concept in self.concepts.items():
            if category and concept.category != category:
                continue
            
            # Calculate relevance score
            score = await self._calculate_relevance_score(concept, query_terms)
            
            if score > 0:
                scored_concepts.append((score, concept))
        
        # Sort by relevance score
        scored_concepts.sort(key=lambda x: x[0], reverse=True)
        
        # Return top results
        results = []
        for score, concept in scored_concepts[:max_results]:
            result = concept.to_dict()
            result["relevance_score"] = score
            results.append(result)
        
        return results
    
    async def _compress_content(self, content: str, level: str) -> str:
        """Apply semantic compression based on level"""
        if level == "low":
            return content  # No compression
        
        compressed = content
        
        # Apply compression patterns
        for full_term, abbrev in self.compression_patterns.items():
            if level in ["medium", "high", "max"]:
                # Case-insensitive replacement, preserving original case structure
                pattern = re.compile(re.escape(full_term), re.IGNORECASE)
                compressed = pattern.sub(abbrev, compressed)
        
        if level in ["high", "max"]:
            # Remove redundant words
            redundant_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]
            words = compressed.split()
            compressed_words = [word for word in words if word.lower() not in redundant_words or len(words) <= 3]
            compressed = " ".join(compressed_words)
        
        if level == "max":
            # Ultra compression: use only key terms
            key_terms = await self._extract_key_terms(content)
            if len(key_terms) > 0:
                compressed = " ".join(key_terms[:10])  # Max 10 key terms
        
        return compressed
    
    async def _extract_key_terms(self, content: str) -> List[str]:
        """Extract key terms for maximum compression"""
        # Simple key term extraction (could be enhanced with NLP)
        words = re.findall(r'\b[A-Za-z]+\b', content.lower())
        
        # Filter out common words and keep important terms
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should"}
        
        key_terms = []
        for word in words:
            if len(word) > 3 and word not in stop_words:
                key_terms.append(word)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
    async def _extract_semantic_tags(self, content: str) -> List[str]:
        """Extract semantic tags for indexing"""
        tags = []
        
        # Technology tags
        tech_patterns = {
            "python": ["python", "py", "fastapi", "asyncio", "pytest"],
            "javascript": ["javascript", "js", "node", "react", "npm"],
            "docker": ["docker", "container", "dockerfile", "compose"],
            "database": ["database", "sql", "postgresql", "redis", "mongodb"],
            "api": ["api", "rest", "endpoint", "http", "websocket"],
            "ai": ["ai", "ml", "claude", "llm", "model", "intelligence"],
            "security": ["security", "auth", "jwt", "ssl", "tls", "encryption"],
            "monitoring": ["monitoring", "logging", "metrics", "health", "status"]
        }
        
        content_lower = content.lower()
        for tag, patterns in tech_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                tags.append(tag)
        
        # ActiveLog service tags
        service_patterns = {
            "bot-orchestrator": ["bot", "orchestrator", "claude", "llm"],
            "luciddreamer": ["dream", "quantum", "simulation", "lucid"],
            "business": ["business", "portfolio", "financial", "analytics"],
            "municipal": ["municipal", "government", "citizen", "public"],
            "trading": ["trading", "market", "dividend", "portfolio"],
            "development": ["code", "development", "bug", "analysis"]
        }
        
        for tag, patterns in service_patterns.items():
            if any(pattern in content_lower for pattern in patterns):
                tags.append(tag)
        
        return list(set(tags))  # Remove duplicates
    
    async def _generate_aliases(self, content: str) -> List[str]:
        """Generate semantic aliases for concept"""
        aliases = []
        
        # Apply compression patterns to find aliases
        content_lower = content.lower()
        for full_term, abbrev in self.compression_patterns.items():
            if full_term in content_lower:
                aliases.append(abbrev)
        
        # Extract acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', content)
        aliases.extend(acronyms)
        
        return list(set(aliases))  # Remove duplicates
    
    async def _calculate_quality_score(self, content: str) -> float:
        """Calculate quality score for concept"""
        score = 1.0
        
        # Length factor (moderate length is better)
        length = len(content)
        if 50 <= length <= 200:
            score += 0.2
        elif length < 20 or length > 500:
            score -= 0.2
        
        # Information density
        unique_words = len(set(content.lower().split()))
        total_words = len(content.split())
        if total_words > 0:
            density = unique_words / total_words
            score += density * 0.3
        
        # Technical term presence
        tech_terms = ["api", "service", "system", "database", "authentication", "optimization"]
        tech_count = sum(1 for term in tech_terms if term in content.lower())
        score += min(tech_count * 0.1, 0.3)
        
        return min(score, 2.0)  # Cap at 2.0
    
    async def _calculate_relevance_score(self, concept: Concept, query_terms: Set[str]) -> float:
        """Calculate relevance score for search"""
        score = 0.0
        
        # Content matching
        content_words = set(concept.content.lower().split())
        content_matches = len(query_terms.intersection(content_words))
        score += content_matches * 2.0
        
        # Alias matching
        alias_words = set()
        for alias in concept.aliases:
            alias_words.update(alias.lower().split())
        alias_matches = len(query_terms.intersection(alias_words))
        score += alias_matches * 1.5
        
        # Tag matching
        tag_words = set()
        for tag in concept.semantic_tags:
            tag_words.update(tag.lower().split())
        tag_matches = len(query_terms.intersection(tag_words))
        score += tag_matches * 1.0
        
        # Quality and popularity boost
        score *= concept.quality_score
        score += concept.access_count * 0.01
        
        return score
    
    async def _update_semantic_index(self, concept_id: str, terms: List[str]):
        """Update semantic index for fast searching"""
        for term in terms:
            term_lower = term.lower()
            if term_lower not in self.semantic_index:
                self.semantic_index[term_lower] = set()
            self.semantic_index[term_lower].add(concept_id)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        return {
            "concepts": len(self.concepts),
            "categories": len(self.categories),
            "links": len(self.links),
            "indexed_terms": len(self.semantic_index),
            "compression_patterns": len(self.compression_patterns),
            "avg_quality_score": sum(c.quality_score for c in self.concepts.values()) / len(self.concepts) if self.concepts else 0
        }
    
    async def get_efficiency_metrics(self) -> Dict[str, Any]:
        """Get compression and efficiency metrics"""
        if not self.concepts:
            return {"compression_ratio": 0, "storage_efficiency": 0}
        
        total_original = 0
        total_compressed = 0
        
        for concept in self.concepts.values():
            if concept.original_content:
                total_original += len(concept.original_content)
                total_compressed += len(concept.content)
        
        compression_ratio = 1.0 - (total_compressed / total_original) if total_original > 0 else 0
        
        return {
            "compression_ratio": compression_ratio,
            "average_concept_size": total_compressed / len(self.concepts),
            "storage_efficiency": compression_ratio * 100,
            "memory_usage_mb": len(str(self.concepts)) / (1024 * 1024)
        }
    
    async def find_optimization_candidates(self) -> List[Dict[str, Any]]:
        """Find concepts that could benefit from optimization"""
        candidates = []
        
        for concept_id, concept in self.concepts.items():
            optimization_score = 0
            
            # Large uncompressed content
            if len(concept.content) > 300:
                optimization_score += 2
            
            # Low compression level but high access
            if concept.compression_level in ["low", "medium"] and concept.access_count > 10:
                optimization_score += 3
            
            # No aliases but high access
            if len(concept.aliases) == 0 and concept.access_count > 5:
                optimization_score += 2
            
            # Poor quality score
            if concept.quality_score < 1.0:
                optimization_score += 1
            
            if optimization_score >= 3:
                candidates.append({
                    "concept_id": concept_id,
                    "optimization_score": optimization_score,
                    "current_size": len(concept.content),
                    "access_count": concept.access_count,
                    "compression_level": concept.compression_level
                })
        
        # Sort by optimization score
        candidates.sort(key=lambda x: x["optimization_score"], reverse=True)
        
        return candidates
    
    async def get_health_status(self) -> bool:
        """Get health status of knowledge graph"""
        try:
            # Basic health checks
            if len(self.concepts) == 0:
                return False
            
            # Check for corrupted concepts
            corrupted = 0
            for concept in self.concepts.values():
                if not concept.content or not concept.concept_id:
                    corrupted += 1
            
            corruption_rate = corrupted / len(self.concepts)
            
            # Healthy if corruption rate < 5%
            return corruption_rate < 0.05
            
        except Exception:
            return False
    
    async def update_concept(self, concept_id: str, updates: Dict[str, Any]) -> bool:
        """Update existing concept"""
        if concept_id not in self.concepts:
            return False
        
        try:
            concept = self.concepts[concept_id]
            
            if "content" in updates:
                # Recompress with current level
                concept.original_content = concept.original_content or concept.content
                concept.content = await self._compress_content(updates["content"], concept.compression_level)
                
                # Update semantic tags and aliases
                concept.semantic_tags = await self._extract_semantic_tags(updates["content"])
                concept.aliases = await self._generate_aliases(updates["content"])
                concept.quality_score = await self._calculate_quality_score(updates["content"])
                
                # Update semantic index
                await self._update_semantic_index(concept_id, concept.semantic_tags + concept.aliases)
            
            if "category" in updates:
                # Remove from old category, add to new
                concept.category = updates["category"]
                self.categories.add(concept.category)
            
            if "references" in updates:
                concept.references = updates["references"]
                
                # Update links
                self.links = [link for link in self.links if link.from_concept != concept_id]
                for ref in concept.references:
                    if ref in self.concepts:
                        link = ConceptLink(
                            from_concept=concept_id,
                            to_concept=ref,
                            relationship_type="references"
                        )
                        self.links.append(link)
            
            concept.last_updated = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            logger.error(f"Failed to update concept {concept_id}: {e}")
            return False