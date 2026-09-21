"""
ActiveLog Project Memory - Bot-Specific View Manager
Capability-based formatting with automatic view selection
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import json
import re
from datetime import datetime, timezone

class BotCapabilityLevel(Enum):
    """Bot capability levels for view selection"""
    SIMPLE = "simple"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class ViewConfig:
    """Configuration for bot view formatting"""
    max_complexity: int
    include_examples: bool
    include_references: bool
    include_technical_details: bool
    max_context_items: int
    preferred_explanation_style: str

class BotViewManager:
    """
    Manages bot-specific views with capability-based formatting
    Automatically selects optimal view based on bot capabilities
    """
    
    def __init__(self):
        self.view_configs = self._initialize_view_configs()
        self.capability_patterns = self._initialize_capability_patterns()
        self.explanation_cache = {}
    
    def _initialize_view_configs(self) -> Dict[BotCapabilityLevel, ViewConfig]:
        """Initialize view configurations for each capability level"""
        return {
            BotCapabilityLevel.SIMPLE: ViewConfig(
                max_complexity=3,
                include_examples=True,
                include_references=False,
                include_technical_details=False,
                max_context_items=5,
                preferred_explanation_style="basic"
            ),
            BotCapabilityLevel.INTERMEDIATE: ViewConfig(
                max_complexity=6,
                include_examples=True,
                include_references=True,
                include_technical_details=False,
                max_context_items=10,
                preferred_explanation_style="practical"
            ),
            BotCapabilityLevel.ADVANCED: ViewConfig(
                max_complexity=9,
                include_examples=True,
                include_references=True,
                include_technical_details=True,
                max_context_items=20,
                preferred_explanation_style="detailed"
            ),
            BotCapabilityLevel.EXPERT: ViewConfig(
                max_complexity=15,
                include_examples=False,
                include_references=True,
                include_technical_details=True,
                max_context_items=50,
                preferred_explanation_style="technical"
            )
        }
    
    def _initialize_capability_patterns(self) -> Dict[str, BotCapabilityLevel]:
        """Initialize patterns for automatic capability detection"""
        return {
            r"gpt-4|claude-3|opus": BotCapabilityLevel.EXPERT,
            r"gpt-3.5|claude-2": BotCapabilityLevel.ADVANCED,
            r"mistral|llama": BotCapabilityLevel.INTERMEDIATE,
            r"basic|simple|light": BotCapabilityLevel.SIMPLE
        }
    
    def detect_capability_level(self, bot_description: str) -> BotCapabilityLevel:
        """
        Automatically detect bot capability level from description
        """
        bot_lower = bot_description.lower()
        
        for pattern, level in self.capability_patterns.items():
            if re.search(pattern, bot_lower):
                return level
        
        # Default to intermediate if no pattern matches
        return BotCapabilityLevel.INTERMEDIATE
    
    def format_for_bot(self, content: Dict[str, Any], 
                       bot_capabilities: str = "advanced",
                       explicit_level: Optional[BotCapabilityLevel] = None) -> Dict[str, Any]:
        """
        Format content based on bot capabilities
        Returns optimized view for the specific bot
        """
        
        # Determine capability level
        if explicit_level:
            level = explicit_level
        else:
            level = self.detect_capability_level(bot_capabilities)
        
        config = self.view_configs[level]
        
        # Format based on capability level
        formatted_content = {
            "capability_level": level.value,
            "content": self._apply_view_formatting(content, config),
            "metadata": {
                "formatted_at": datetime.now(timezone.utc).isoformat(),
                "config_used": level.value,
                "optimization_applied": True
            }
        }
        
        return formatted_content
    
    def _apply_view_formatting(self, content: Dict[str, Any], config: ViewConfig) -> Dict[str, Any]:
        """Apply specific formatting based on view configuration"""
        
        formatted = {}
        
        # Handle different content types
        if "concepts" in content:
            formatted["concepts"] = self._format_concepts(content["concepts"], config)
        
        if "explanations" in content:
            formatted["explanations"] = self._format_explanations(content["explanations"], config)
        
        if "references" in content:
            if config.include_references:
                formatted["references"] = self._format_references(content["references"], config)
        
        if "examples" in content:
            if config.include_examples:
                formatted["examples"] = self._format_examples(content["examples"], config)
        
        if "technical_details" in content:
            if config.include_technical_details:
                formatted["technical_details"] = content["technical_details"]
        
        return formatted
    
    def _format_concepts(self, concepts: List[Dict[str, Any]], config: ViewConfig) -> List[Dict[str, Any]]:
        """Format concepts based on complexity limits"""
        
        formatted_concepts = []
        
        for concept in concepts[:config.max_context_items]:
            complexity = self._calculate_complexity(concept.get("description", ""))
            
            if complexity <= config.max_complexity:
                formatted_concept = {
                    "id": concept.get("id"),
                    "name": concept.get("name"),
                    "description": self._simplify_description(
                        concept.get("description", ""), 
                        config.preferred_explanation_style
                    )
                }
                
                if config.include_references and "references" in concept:
                    formatted_concept["references"] = concept["references"][:3]
                
                formatted_concepts.append(formatted_concept)
        
        return formatted_concepts
    
    def _format_explanations(self, explanations: List[Dict[str, Any]], config: ViewConfig) -> List[Dict[str, Any]]:
        """Format explanations based on preferred style"""
        
        formatted_explanations = []
        
        for explanation in explanations[:config.max_context_items]:
            formatted_explanation = {
                "topic": explanation.get("topic"),
                "content": self._adapt_explanation_style(
                    explanation.get("content", ""),
                    config.preferred_explanation_style
                )
            }
            
            if config.include_examples and "examples" in explanation:
                formatted_explanation["examples"] = explanation["examples"][:2]
            
            formatted_explanations.append(formatted_explanation)
        
        return formatted_explanations
    
    def _format_references(self, references: List[str], config: ViewConfig) -> List[str]:
        """Format references based on configuration"""
        return references[:min(5, config.max_context_items // 2)]
    
    def _format_examples(self, examples: List[Dict[str, Any]], config: ViewConfig) -> List[Dict[str, Any]]:
        """Format examples based on configuration"""
        return examples[:min(3, config.max_context_items // 3)]
    
    def _calculate_complexity(self, text: str) -> int:
        """Calculate complexity score for text content"""
        
        complexity_indicators = {
            r'\b(algorithm|optimization|complexity|performance)\b': 3,
            r'\b(implement|configure|integrate|deploy)\b': 2,
            r'\b(function|method|class|variable)\b': 2,
            r'\b(system|architecture|framework|library)\b': 2,
            r'[{}()\[\]]': 1,  # Code-like structures
            r'[A-Z]{2,}': 1,   # Acronyms
        }
        
        total_complexity = 0
        text_lower = text.lower()
        
        for pattern, weight in complexity_indicators.items():
            matches = len(re.findall(pattern, text_lower))
            total_complexity += matches * weight
        
        return min(total_complexity, 20)  # Cap at 20
    
    def _simplify_description(self, description: str, style: str) -> str:
        """Simplify description based on preferred style"""
        
        if style == "basic":
            # Remove technical jargon, simplify language
            simplified = re.sub(r'\b(optimization|algorithm|implementation)\b', 'process', description)
            simplified = re.sub(r'\b(architecture|framework)\b', 'structure', simplified)
            return simplified[:150] + "..." if len(simplified) > 150 else simplified
        
        elif style == "practical":
            # Focus on practical aspects
            return description[:200] + "..." if len(description) > 200 else description
        
        elif style == "detailed":
            # Keep full detail but organized
            return description
        
        elif style == "technical":
            # Keep all technical details
            return description
        
        return description
    
    def _adapt_explanation_style(self, content: str, style: str) -> str:
        """Adapt explanation content to preferred style"""
        
        if style == "basic":
            # Use simple language
            content = re.sub(r'utilizing', 'using', content)
            content = re.sub(r'implement', 'create', content)
            content = re.sub(r'configuration', 'setup', content)
        
        elif style == "practical":
            # Focus on actionable content
            sentences = content.split('.')
            practical_sentences = [s for s in sentences if any(
                word in s.lower() for word in ['create', 'use', 'run', 'setup', 'configure']
            )]
            if practical_sentences:
                content = '. '.join(practical_sentences[:3]) + '.'
        
        return content
    
    def generate_multi_level_content(self, base_content: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Generate content for all capability levels"""
        
        multi_level = {}
        
        for level in BotCapabilityLevel:
            multi_level[level.value] = self.format_for_bot(
                base_content, 
                explicit_level=level
            )
        
        return multi_level
    
    def get_optimal_view(self, request_context: Dict[str, Any], 
                        available_views: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select optimal view based on request context
        """
        
        bot_capabilities = request_context.get("bot_capabilities", "advanced")
        task_complexity = request_context.get("task_complexity", "medium")
        time_constraints = request_context.get("time_constraints", "normal")
        
        # Adjust capability level based on context
        detected_level = self.detect_capability_level(bot_capabilities)
        
        # Downgrade if time constrained
        if time_constraints == "urgent" and detected_level == BotCapabilityLevel.EXPERT:
            detected_level = BotCapabilityLevel.ADVANCED
        
        # Upgrade if task is complex and bot can handle it
        if (task_complexity == "high" and 
            detected_level in [BotCapabilityLevel.INTERMEDIATE, BotCapabilityLevel.ADVANCED]):
            detected_level = BotCapabilityLevel.EXPERT
        
        view_key = detected_level.value
        
        if view_key in available_views:
            return available_views[view_key]
        
        # Fallback to closest available view
        fallback_order = [BotCapabilityLevel.ADVANCED, BotCapabilityLevel.INTERMEDIATE, 
                         BotCapabilityLevel.SIMPLE, BotCapabilityLevel.EXPERT]
        
        for fallback_level in fallback_order:
            if fallback_level.value in available_views:
                return available_views[fallback_level.value]
        
        return available_views.get("advanced", available_views)

    async def optimize_for_context_window(self, content: Dict[str, Any], 
                                         max_tokens: int = 4000,
                                         bot_level: BotCapabilityLevel = BotCapabilityLevel.ADVANCED) -> Dict[str, Any]:
        """
        Optimize content to fit within context window constraints
        """
        
        config = self.view_configs[bot_level]
        token_estimate = len(str(content)) // 4  # Rough token estimation
        
        if token_estimate <= max_tokens:
            return self.format_for_bot(content, explicit_level=bot_level)
        
        # Progressive reduction strategy
        reduction_steps = [
            ("examples", 0.7),
            ("technical_details", 0.5),
            ("references", 0.3),
            ("explanations", 0.8)
        ]
        
        optimized_content = content.copy()
        
        for field, reduction_factor in reduction_steps:
            if field in optimized_content and isinstance(optimized_content[field], list):
                current_length = len(optimized_content[field])
                new_length = int(current_length * reduction_factor)
                optimized_content[field] = optimized_content[field][:new_length]
                
                # Re-estimate tokens
                token_estimate = len(str(optimized_content)) // 4
                if token_estimate <= max_tokens:
                    break
        
        return self.format_for_bot(optimized_content, explicit_level=bot_level)