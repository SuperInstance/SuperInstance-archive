#!/usr/bin/env python3
"""
Context Window Optimizer

Minimizes token usage while maximizing understanding through intelligent
concept loading, dependency resolution, and progressive disclosure.
"""

import json
import os
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class BotType(str, Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"
    EXPERT = "expert"

class ViewLevel(str, Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"
    FULL = "full"

@dataclass
class ConceptQuery:
    concept_id: str
    context: Optional[str] = None
    bot_type: BotType = BotType.ADVANCED
    max_tokens: int = 2000
    include_dependencies: bool = True
    expand_level: ViewLevel = ViewLevel.ADVANCED

@dataclass
class ConceptResponse:
    concept_id: str
    content: str
    token_count: int
    dependencies_loaded: List[str]
    related_concepts: List[str]
    compression_ratio: float

class ContextOptimizer:
    """Optimizes context loading for minimal token usage."""
    
    def __init__(self, memory_path: str = "/home/activeloguser/activelog/project-memory"):
        self.memory_path = Path(memory_path)
        self.knowledge_path = self.memory_path / "knowledge"
        self.manifest_path = self.memory_path / "context" / "manifest.json"
        self.cache_path = self.memory_path / "cache"
        
        self.manifest = self._load_manifest()
        self.concept_cache = {}
        
    def _load_manifest(self) -> Dict:
        """Load the context manifest with dependency information."""
        try:
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"concepts": {}, "aliases": {}, "patterns": {}}
    
    def _save_manifest(self):
        """Save updated manifest."""
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def _resolve_alias(self, concept_id: str) -> str:
        """Resolve concept aliases to actual IDs."""
        return self.manifest.get("aliases", {}).get(concept_id, concept_id)
    
    def _get_concept_info(self, concept_id: str) -> Optional[Dict]:
        """Get concept metadata from manifest."""
        resolved_id = self._resolve_alias(concept_id)
        return self.manifest.get("concepts", {}).get(resolved_id)
    
    def _load_concept_file(self, concept_id: str, view_level: ViewLevel) -> str:
        """Load concept content from file based on view level."""
        resolved_id = self._resolve_alias(concept_id)
        
        # Try category-specific file first
        category = resolved_id.split('-')[0].lower()
        concept_file = self.knowledge_path / category / f"{resolved_id}.md"
        
        if not concept_file.exists():
            # Fallback to index.md lookup
            return self._get_from_index(resolved_id)
        
        try:
            with open(concept_file, 'r') as f:
                content = f.read()
            
            # Extract appropriate view level
            return self._extract_view_level(content, view_level)
            
        except FileNotFoundError:
            return f"Concept {resolved_id} not found"
    
    def _extract_view_level(self, content: str, view_level: ViewLevel) -> str:
        """Extract specific view level from markdown content."""
        lines = content.split('\n')
        
        if view_level == ViewLevel.SIMPLE:
            # Find simple view section
            in_simple = False
            simple_content = []
            for line in lines:
                if line.startswith('## Simple View'):
                    in_simple = True
                    continue
                elif line.startswith('## ') and in_simple:
                    break
                elif in_simple:
                    simple_content.append(line)
            
            if simple_content:
                return '\n'.join(simple_content).strip()
        
        elif view_level == ViewLevel.ADVANCED:
            # Find advanced view section
            in_advanced = False
            advanced_content = []
            for line in lines:
                if line.startswith('## Advanced View'):
                    in_advanced = True
                    continue
                elif line.startswith('## ') and in_advanced:
                    break
                elif in_advanced:
                    advanced_content.append(line)
            
            if advanced_content:
                return '\n'.join(advanced_content).strip()
        
        # Return full content for FULL level or if specific view not found
        return content
    
    def _get_from_index(self, concept_id: str) -> str:
        """Get concept summary from main index."""
        index_file = self.knowledge_path / "index.md"
        
        try:
            with open(index_file, 'r') as f:
                for line in f:
                    if line.startswith(f"**{concept_id}**"):
                        # Extract everything after the ID until next line or pipe
                        content = line.split('|', 1)
                        if len(content) > 1:
                            return content[1].strip()
                        else:
                            return line.replace(f"**{concept_id}**", "").strip()
            
            return f"Concept {concept_id} not found in index"
            
        except FileNotFoundError:
            return f"Index file not found"
    
    def _calculate_token_count(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 chars)."""
        return max(1, len(text) // 4)
    
    def _get_dependencies(self, concept_id: str) -> List[str]:
        """Get direct dependencies for a concept."""
        concept_info = self._get_concept_info(concept_id)
        if not concept_info:
            return []
        return concept_info.get("dependencies", [])
    
    def _get_related_concepts(self, concept_id: str) -> List[str]:
        """Get related concepts (dependents + dependencies)."""
        concept_info = self._get_concept_info(concept_id)
        if not concept_info:
            return []
        
        dependencies = concept_info.get("dependencies", [])
        dependents = concept_info.get("dependents", [])
        return list(set(dependencies + dependents))
    
    def _select_optimal_view_level(self, concept_id: str, bot_type: BotType, max_tokens: int) -> ViewLevel:
        """Select optimal view level based on bot type and token budget."""
        concept_info = self._get_concept_info(concept_id)
        if not concept_info:
            return ViewLevel.SIMPLE
        
        views = concept_info.get("views", {})
        
        # Bot type preferences
        if bot_type == BotType.SIMPLE:
            return ViewLevel.SIMPLE
        elif bot_type == BotType.EXPERT:
            if views.get("full", 1000) <= max_tokens:
                return ViewLevel.FULL
            elif views.get("advanced", 500) <= max_tokens:
                return ViewLevel.ADVANCED
            else:
                return ViewLevel.SIMPLE
        else:  # ADVANCED
            if views.get("advanced", 500) <= max_tokens:
                return ViewLevel.ADVANCED
            else:
                return ViewLevel.SIMPLE
    
    def _build_dependency_graph(self, concept_id: str, max_depth: int = 2) -> Set[str]:
        """Build dependency graph with limited depth."""
        visited = set()
        to_visit = [(concept_id, 0)]
        
        while to_visit:
            current_id, depth = to_visit.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
                
            visited.add(current_id)
            
            # Add dependencies
            dependencies = self._get_dependencies(current_id)
            for dep in dependencies:
                if dep not in visited:
                    to_visit.append((dep, depth + 1))
        
        return visited
    
    def query_concept(self, query: ConceptQuery) -> ConceptResponse:
        """Query a concept with optimization."""
        concept_id = self._resolve_alias(query.concept_id)
        
        # Determine optimal view level
        view_level = query.expand_level
        if view_level == ViewLevel.ADVANCED:  # Auto-select based on bot type
            view_level = self._select_optimal_view_level(
                concept_id, query.bot_type, query.max_tokens
            )
        
        # Load main concept
        main_content = self._load_concept_file(concept_id, view_level)
        token_count = self._calculate_token_count(main_content)
        
        dependencies_loaded = []
        remaining_tokens = query.max_tokens - token_count
        
        # Load critical dependencies if requested and budget allows
        if query.include_dependencies and remaining_tokens > 100:
            dependencies = self._get_dependencies(concept_id)
            
            # Prioritize high-priority dependencies
            for dep_id in dependencies:
                if remaining_tokens <= 100:
                    break
                
                dep_info = self._get_concept_info(dep_id)
                if not dep_info:
                    continue
                
                # Only load if high priority and fits in budget
                if dep_info.get("priority") == "high":
                    dep_content = self._load_concept_file(dep_id, ViewLevel.SIMPLE)
                    dep_tokens = self._calculate_token_count(dep_content)
                    
                    if dep_tokens <= remaining_tokens:
                        main_content += f"\n\n### Dependency: {dep_id}\n{dep_content}"
                        token_count += dep_tokens
                        remaining_tokens -= dep_tokens
                        dependencies_loaded.append(dep_id)
        
        # Get related concepts for reference
        related_concepts = self._get_related_concepts(concept_id)
        
        # Calculate compression ratio
        full_content = self._load_concept_file(concept_id, ViewLevel.FULL)
        full_tokens = self._calculate_token_count(full_content)
        compression_ratio = token_count / max(full_tokens, 1)
        
        # Update usage stats
        self._update_usage_stats(concept_id, token_count)
        
        return ConceptResponse(
            concept_id=concept_id,
            content=main_content,
            token_count=token_count,
            dependencies_loaded=dependencies_loaded,
            related_concepts=related_concepts,
            compression_ratio=compression_ratio
        )
    
    def _update_usage_stats(self, concept_id: str, token_count: int):
        """Update usage statistics."""
        stats = self.manifest.get("usage_stats", {})
        stats["queries_today"] = stats.get("queries_today", 0) + 1
        
        # Update average tokens
        current_avg = stats.get("avg_tokens_per_query", 0)
        total_queries = stats["queries_today"]
        new_avg = ((current_avg * (total_queries - 1)) + token_count) / total_queries
        stats["avg_tokens_per_query"] = round(new_avg, 2)
        
        self.manifest["usage_stats"] = stats
    
    def get_context_budget_info(self, max_tokens: int = 8000) -> Dict:
        """Get information about context budget utilization."""
        total_concepts = len(self.manifest.get("concepts", {}))
        
        # Estimate tokens for different loading strategies
        simple_total = sum(
            concept.get("views", {}).get("simple", 50)
            for concept in self.manifest.get("concepts", {}).values()
        )
        
        advanced_total = sum(
            concept.get("views", {}).get("advanced", 200)  
            for concept in self.manifest.get("concepts", {}).values()
        )
        
        return {
            "total_concepts": total_concepts,
            "max_tokens": max_tokens,
            "simple_view_total": simple_total,
            "advanced_view_total": advanced_total,
            "simple_utilization": min(1.0, simple_total / max_tokens),
            "advanced_utilization": min(1.0, advanced_total / max_tokens),
            "recommended_strategy": "simple" if simple_total <= max_tokens * 0.7 else "selective"
        }
    
    def optimize_query_list(self, concept_ids: List[str], max_tokens: int = 2000) -> List[ConceptQuery]:
        """Optimize a list of concept queries to fit within token budget."""
        # Sort by priority and token efficiency
        concept_priorities = []
        
        for concept_id in concept_ids:
            concept_info = self._get_concept_info(concept_id)
            if not concept_info:
                continue
                
            priority = {"high": 3, "medium": 2, "low": 1}.get(
                concept_info.get("priority", "medium"), 2
            )
            
            simple_tokens = concept_info.get("views", {}).get("simple", 50)
            efficiency = priority / max(simple_tokens, 1)  # Priority per token
            
            concept_priorities.append((concept_id, priority, simple_tokens, efficiency))
        
        # Sort by efficiency (descending)
        concept_priorities.sort(key=lambda x: x[3], reverse=True)
        
        # Build optimized query list within token budget
        optimized_queries = []
        used_tokens = 0
        
        for concept_id, priority, tokens, efficiency in concept_priorities:
            if used_tokens + tokens <= max_tokens:
                query = ConceptQuery(
                    concept_id=concept_id,
                    bot_type=BotType.ADVANCED,
                    max_tokens=tokens,
                    expand_level=ViewLevel.SIMPLE
                )
                optimized_queries.append(query)
                used_tokens += tokens
            else:
                break
        
        return optimized_queries


if __name__ == "__main__":
    # Example usage
    optimizer = ContextOptimizer()
    
    # Query a specific concept
    query = ConceptQuery(
        concept_id="CORE-001",
        bot_type=BotType.ADVANCED,
        max_tokens=1000
    )
    
    response = optimizer.query_concept(query)
    print(f"Concept: {response.concept_id}")
    print(f"Tokens: {response.token_count}")
    print(f"Compression: {response.compression_ratio:.2%}")
    print(f"Dependencies loaded: {response.dependencies_loaded}")
    print(f"\nContent:\n{response.content}")