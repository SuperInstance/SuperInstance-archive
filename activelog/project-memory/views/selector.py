#!/usr/bin/env python3
"""
Bot-Specific View Selector

Automatically selects appropriate documentation complexity based on bot capabilities,
task context, and available token budget.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path

class BotCapability(str, Enum):
    BASIC = "basic"           # Simple task execution, minimal context
    INTERMEDIATE = "intermediate"  # Code understanding, basic reasoning  
    ADVANCED = "advanced"     # Complex reasoning, architectural understanding
    EXPERT = "expert"        # Deep system knowledge, optimization

class TaskType(str, Enum):
    QUESTION = "question"     # Information lookup
    CODE_READ = "code_read"   # Code comprehension
    CODE_WRITE = "code_write" # Code generation/modification
    DEBUG = "debug"          # Problem solving
    DESIGN = "design"        # Architecture/design decisions
    OPTIMIZE = "optimize"    # Performance improvements

class ViewSelector:
    """Selects optimal documentation views for different bot types."""
    
    def __init__(self, memory_path: str = "/home/activeloguser/activelog/project-memory"):
        self.memory_path = Path(memory_path)
        self.views_path = self.memory_path / "views"
        
        # Load bot capability profiles
        self.bot_profiles = self._load_bot_profiles()
        
        # Task complexity weights
        self.task_complexity = {
            TaskType.QUESTION: 1,
            TaskType.CODE_READ: 2, 
            TaskType.CODE_WRITE: 3,
            TaskType.DEBUG: 4,
            TaskType.DESIGN: 5,
            TaskType.OPTIMIZE: 5
        }
    
    def _load_bot_profiles(self) -> Dict:
        """Load bot capability profiles."""
        return {
            BotCapability.BASIC: {
                "token_budget": 500,
                "max_concepts": 3,
                "detail_level": "simple",
                "dependencies": False,
                "code_examples": False,
                "architectural_context": False
            },
            BotCapability.INTERMEDIATE: {
                "token_budget": 1500,
                "max_concepts": 8,
                "detail_level": "simple",
                "dependencies": True,
                "code_examples": True,
                "architectural_context": False
            },
            BotCapability.ADVANCED: {
                "token_budget": 4000,
                "max_concepts": 15,
                "detail_level": "advanced",
                "dependencies": True,
                "code_examples": True,
                "architectural_context": True
            },
            BotCapability.EXPERT: {
                "token_budget": 8000,
                "max_concepts": 25,
                "detail_level": "full",
                "dependencies": True,
                "code_examples": True,
                "architectural_context": True
            }
        }
    
    def detect_bot_capability(self, bot_description: str, context: str = "") -> BotCapability:
        """Automatically detect bot capability from description/context."""
        text = (bot_description + " " + context).lower()
        
        # Expert indicators
        expert_indicators = [
            "architecture", "system design", "optimization", "performance",
            "scalability", "enterprise", "complex", "advanced", "expert"
        ]
        
        # Advanced indicators
        advanced_indicators = [
            "code generation", "debugging", "refactoring", "patterns",
            "integration", "apis", "databases", "frameworks"
        ]
        
        # Intermediate indicators  
        intermediate_indicators = [
            "code", "programming", "development", "scripts", "functions",
            "classes", "methods", "libraries"
        ]
        
        expert_score = sum(1 for indicator in expert_indicators if indicator in text)
        advanced_score = sum(1 for indicator in advanced_indicators if indicator in text) 
        intermediate_score = sum(1 for indicator in intermediate_indicators if indicator in text)
        
        if expert_score >= 2:
            return BotCapability.EXPERT
        elif advanced_score >= 2:
            return BotCapability.ADVANCED
        elif intermediate_score >= 1:
            return BotCapability.INTERMEDIATE
        else:
            return BotCapability.BASIC
    
    def detect_task_type(self, query: str) -> TaskType:
        """Detect task type from user query."""
        query_lower = query.lower()
        
        # Optimization keywords
        if any(word in query_lower for word in ["optimize", "performance", "improve", "faster", "efficient"]):
            return TaskType.OPTIMIZE
        
        # Design keywords
        if any(word in query_lower for word in ["design", "architecture", "structure", "organize", "plan"]):
            return TaskType.DESIGN
            
        # Debug keywords
        if any(word in query_lower for word in ["debug", "fix", "error", "bug", "problem", "issue"]):
            return TaskType.DEBUG
        
        # Code write keywords
        if any(word in query_lower for word in ["create", "write", "build", "implement", "add", "generate"]):
            return TaskType.CODE_WRITE
            
        # Code read keywords
        if any(word in query_lower for word in ["understand", "explain", "analyze", "review", "examine"]):
            return TaskType.CODE_READ
        
        # Default to question
        return TaskType.QUESTION
    
    def calculate_view_requirements(
        self, 
        capability: BotCapability, 
        task_type: TaskType,
        concept_ids: List[str],
        context_hints: Optional[str] = None
    ) -> Dict:
        """Calculate specific view requirements for a bot/task combination."""
        
        profile = self.bot_profiles[capability]
        task_complexity = self.task_complexity[task_type]
        
        # Adjust based on task complexity
        complexity_multiplier = min(2.0, 1.0 + (task_complexity - 1) * 0.2)
        
        adjusted_budget = int(profile["token_budget"] * complexity_multiplier)
        adjusted_concepts = min(len(concept_ids), int(profile["max_concepts"] * complexity_multiplier))
        
        # Determine detail level based on task
        detail_level = profile["detail_level"]
        if task_type in [TaskType.DESIGN, TaskType.OPTIMIZE] and capability in [BotCapability.BASIC, BotCapability.INTERMEDIATE]:
            detail_level = "advanced"  # Upgrade for complex tasks
        
        return {
            "bot_capability": capability,
            "task_type": task_type,
            "token_budget": adjusted_budget,
            "max_concepts": adjusted_concepts,
            "detail_level": detail_level,
            "include_dependencies": profile["dependencies"],
            "include_code_examples": profile["code_examples"],
            "include_architectural_context": profile["architectural_context"],
            "complexity_multiplier": complexity_multiplier
        }
    
    def generate_simple_view(self, concept_id: str, content: str) -> str:
        """Generate simplified view for basic bots."""
        lines = content.split('\n')
        
        # Extract just the first paragraph or simple view section
        simple_lines = []
        in_header = False
        
        for line in lines:
            if line.startswith('# '):
                continue  # Skip title
            elif line.startswith('## Simple View'):
                in_header = True
                continue
            elif line.startswith('## ') and in_header:
                break
            elif in_header or (not simple_lines and line.strip()):
                simple_lines.append(line)
                if len(' '.join(simple_lines)) > 200:  # Limit length
                    break
        
        return '\n'.join(simple_lines).strip()
    
    def generate_advanced_view(self, concept_id: str, content: str, include_examples: bool = True) -> str:
        """Generate advanced view for intermediate/advanced bots."""
        lines = content.split('\n')
        
        # Extract title, advanced view, and optionally code examples
        result_lines = []
        in_advanced = False
        in_examples = False
        
        for line in lines:
            if line.startswith('# '):
                result_lines.append(line)  # Keep title
            elif line.startswith('## Advanced View'):
                in_advanced = True
                result_lines.append(line)
            elif line.startswith('## ') and in_advanced:
                if include_examples and 'example' in line.lower():
                    in_examples = True
                    result_lines.append(line)
                else:
                    break
            elif in_advanced or in_examples:
                result_lines.append(line)
                if len(' '.join(result_lines)) > 1000:  # Limit length
                    break
        
        return '\n'.join(result_lines).strip()
    
    def select_optimal_concepts(
        self, 
        available_concepts: List[str], 
        requirements: Dict,
        priority_concepts: Optional[List[str]] = None
    ) -> List[str]:
        """Select optimal subset of concepts based on requirements."""
        
        max_concepts = requirements["max_concepts"]
        
        # Prioritize concepts
        prioritized = []
        
        # Add priority concepts first
        if priority_concepts:
            for concept in priority_concepts:
                if concept in available_concepts:
                    prioritized.append(concept)
        
        # Add remaining concepts
        for concept in available_concepts:
            if concept not in prioritized:
                prioritized.append(concept)
        
        # Limit to max concepts
        return prioritized[:max_concepts]
    
    def create_bot_specific_documentation(
        self,
        concept_ids: List[str],
        bot_description: str,
        user_query: str,
        context_hints: Optional[str] = None
    ) -> Dict:
        """Create complete bot-specific documentation package."""
        
        # Detect bot capability and task type
        capability = self.detect_bot_capability(bot_description, context_hints or "")
        task_type = self.detect_task_type(user_query)
        
        # Calculate requirements
        requirements = self.calculate_view_requirements(
            capability, task_type, concept_ids, context_hints
        )
        
        # Select optimal concepts
        selected_concepts = self.select_optimal_concepts(
            concept_ids, requirements
        )
        
        return {
            "bot_capability": capability.value,
            "task_type": task_type.value,
            "requirements": requirements,
            "selected_concepts": selected_concepts,
            "token_budget": requirements["token_budget"],
            "recommended_detail_level": requirements["detail_level"],
            "optimization_applied": requirements["complexity_multiplier"] > 1.0
        }
    
    def create_view_template(self, view_type: str) -> str:
        """Create template for specific view type."""
        
        templates = {
            "simple": """# {concept_id}: {title}

**Quick Summary:** {one_liner}

## Key Points
- {key_point_1}
- {key_point_2} 
- {key_point_3}

## Related
{related_concepts}
""",
            
            "advanced": """# {concept_id}: {title}

**Type:** {concept_type}  
**Complexity:** {complexity}  

## Overview
{overview_paragraph}

## Key Components
{component_list}

## Implementation Details
{implementation_details}

## Related Concepts
{related_concepts}

## Code References
{code_references}
""",
            
            "expert": """# {concept_id}: {title}

**Type:** {concept_type}  
**Complexity:** {complexity}  
**Dependencies:** {dependencies}  

## Architecture Overview
{architecture_overview}

## Implementation Details
{implementation_details}

## Performance Considerations
{performance_notes}

## Integration Patterns
{integration_patterns}

## Code Examples
{code_examples}

## Related Concepts
{related_concepts}

## Recent Changes
{change_history}
"""
        }
        
        return templates.get(view_type, templates["simple"])


if __name__ == "__main__":
    # Example usage
    selector = ViewSelector()
    
    # Test bot capability detection
    bot_desc = "Advanced code assistant capable of complex reasoning and system design"
    capability = selector.detect_bot_capability(bot_desc)
    print(f"Detected capability: {capability}")
    
    # Test task type detection
    query = "Help me optimize the authentication service performance"
    task_type = selector.detect_task_type(query)
    print(f"Detected task type: {task_type}")
    
    # Create documentation package
    concept_ids = ["CORE-001", "AUTH-001", "SVC-001"]
    doc_package = selector.create_bot_specific_documentation(
        concept_ids, bot_desc, query
    )
    
    print(f"\nDocumentation package:")
    print(f"Bot capability: {doc_package['bot_capability']}")
    print(f"Task type: {doc_package['task_type']}")
    print(f"Token budget: {doc_package['token_budget']}")
    print(f"Selected concepts: {doc_package['selected_concepts']}")
    print(f"Detail level: {doc_package['recommended_detail_level']}")