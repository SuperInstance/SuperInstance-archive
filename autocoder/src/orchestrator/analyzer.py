"""
Task Complexity Analyzer
Determines appropriate model for a given task
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TaskComplexity(Enum):
    """Task complexity levels"""
    TRIVIAL = 1      # Format, comments, docstrings (<500 tokens)
    SIMPLE = 2       # Basic functions, small fixes (<2K tokens)
    MODERATE = 3     # Features, tests, single-file refactor (<10K tokens)
    COMPLEX = 4      # Multi-file, reasoning required (10K+ tokens)
    VERY_COMPLEX = 5 # Architecture, security, multi-file refactor


@dataclass
class TaskAnalysis:
    """Analysis result for a task"""
    complexity: TaskComplexity
    estimated_tokens: int
    requires_reasoning: bool
    needs_tools: bool
    suggested_model: str
    confidence: float  # 0-1


class TaskAnalyzer:
    """Analyzes tasks to determine complexity and routing"""

    # Keywords indicating complexity level
    KEYWORDS_TRIVIAL = [
        "format", "indent", "comment", "docstring", "documentation",
        "add comment", "fix formatting", "clean up whitespace"
    ]

    KEYWORDS_SIMPLE = [
        "simple function", "basic", "hello world", "small fix",
        "quick", "utility", "helper", "getter", "setter"
    ]

    KEYWORDS_MODERATE = [
        "implement", "create feature", "add functionality",
        "bug fix", "refactor", "test", "unit test", "integration",
        "api endpoint", "database query", "validation"
    ]

    KEYWORDS_COMPLEX = [
        "architecture", "design system", "multi-file",
        "race condition", "security", "authentication",
        "authorization", "optimization", "algorithm",
        "performance", "scalability", "distributed"
    ]

    KEYWORDS_VERY_COMPLEX = [
        "migrate", "redesign", "complete overhaul",
        "entire system", "across codebase", "microservices",
        "infrastructure", "deployment", "ci/cd"
    ]

    # Keywords indicating tool needs
    TOOL_KEYWORDS = [
        "read file", "write file", "create file", "delete file",
        "git", "commit", "branch", "run", "execute", "test",
        "compile", "build", "deploy", "install"
    ]

    # Keywords indicating reasoning needs
    REASONING_KEYWORDS = [
        "why", "explain", "analyze", "compare", "evaluate",
        "optimize", "improve", "design", "architect", "choose",
        "decide", "recommend", "suggest", "best practice"
    ]

    def analyze(self, task: str) -> TaskAnalysis:
        """
        Analyze task and return complexity assessment

        Args:
            task: User's task description

        Returns:
            TaskAnalysis with complexity and recommendations
        """
        task_lower = task.lower()

        # Estimate tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(task) // 4

        # Check for tool needs
        needs_tools = any(kw in task_lower for kw in self.TOOL_KEYWORDS)

        # Check for reasoning needs
        requires_reasoning = any(kw in task_lower for kw in self.REASONING_KEYWORDS)

        # Determine complexity
        complexity, confidence = self._determine_complexity(task_lower)

        # Suggest model based on complexity
        suggested_model = self._suggest_model(
            complexity,
            estimated_tokens,
            requires_reasoning,
            needs_tools
        )

        return TaskAnalysis(
            complexity=complexity,
            estimated_tokens=estimated_tokens,
            requires_reasoning=requires_reasoning,
            needs_tools=needs_tools,
            suggested_model=suggested_model,
            confidence=confidence
        )

    def _determine_complexity(self, task_lower: str) -> tuple[TaskComplexity, float]:
        """
        Determine task complexity with confidence score

        Returns:
            (complexity, confidence) tuple
        """
        # Count matches for each complexity level
        trivial_score = sum(1 for kw in self.KEYWORDS_TRIVIAL if kw in task_lower)
        simple_score = sum(1 for kw in self.KEYWORDS_SIMPLE if kw in task_lower)
        moderate_score = sum(1 for kw in self.KEYWORDS_MODERATE if kw in task_lower)
        complex_score = sum(1 for kw in self.KEYWORDS_COMPLEX if kw in task_lower)
        very_complex_score = sum(1 for kw in self.KEYWORDS_VERY_COMPLEX if kw in task_lower)

        # Find highest score
        scores = [
            (trivial_score, TaskComplexity.TRIVIAL),
            (simple_score, TaskComplexity.SIMPLE),
            (moderate_score, TaskComplexity.MODERATE),
            (complex_score, TaskComplexity.COMPLEX),
            (very_complex_score, TaskComplexity.VERY_COMPLEX)
        ]

        max_score, complexity = max(scores, key=lambda x: x[0])

        # If no keywords matched, use heuristics
        if max_score == 0:
            word_count = len(task_lower.split())

            if word_count <= 5:
                complexity = TaskComplexity.SIMPLE
                confidence = 0.5
            elif word_count <= 15:
                complexity = TaskComplexity.MODERATE
                confidence = 0.5
            else:
                complexity = TaskComplexity.COMPLEX
                confidence = 0.4

            # Check for code-specific patterns
            if any(pattern in task_lower for pattern in ["class", "function", "method", "def ", "void "]):
                complexity = TaskComplexity.MODERATE
                confidence = 0.6

        else:
            # Confidence based on number of matches
            confidence = min(0.9, 0.5 + (max_score * 0.2))

        # Override: multi-file indicators always = very complex
        if any(indicator in task_lower for indicator in ["multiple files", "entire codebase", "across files"]):
            complexity = TaskComplexity.VERY_COMPLEX
            confidence = 0.95

        return complexity, confidence

    def _suggest_model(
        self,
        complexity: TaskComplexity,
        tokens: int,
        requires_reasoning: bool,
        needs_tools: bool
    ) -> str:
        """
        Suggest which model to use

        Returns:
            Model identifier ('local', 'haiku', 'sonnet')
        """
        # Very complex or requires reasoning → always use best model
        if complexity == TaskComplexity.VERY_COMPLEX or (complexity == TaskComplexity.COMPLEX and requires_reasoning):
            return "sonnet"  # Claude 4 Sonnet

        # Complex → use good model
        if complexity == TaskComplexity.COMPLEX:
            return "sonnet"

        # Moderate → depends on tokens and tools
        if complexity == TaskComplexity.MODERATE:
            if tokens > 5000 or not needs_tools:
                return "haiku"  # Claude Haiku for speed
            return "local"  # Local can handle moderate with tools

        # Simple or trivial → local is perfect
        return "local"  # Qwen 7B on GPU

    def should_use_local(self, analysis: TaskAnalysis, gpu_available: bool = True) -> bool:
        """
        Determine if local model is appropriate

        Args:
            analysis: Task analysis result
            gpu_available: Whether GPU is available

        Returns:
            True if should use local model
        """
        if not gpu_available:
            return False

        # Use local for simple tasks
        if analysis.complexity.value <= TaskComplexity.SIMPLE.value:
            return True

        # Use local for moderate tasks if not too complex
        if analysis.complexity == TaskComplexity.MODERATE:
            if analysis.estimated_tokens < 3000 and not analysis.requires_reasoning:
                return True

        return False
