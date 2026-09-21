#!/usr/bin/env python3
"""
Hierarchical Task Delegation System
Allows Claude bots to delegate simple tasks to local AI coding assistants
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import os
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TaskComplexity:
    """Task complexity analysis result"""
    score: float  # 0-100, higher = more complex
    category: str  # 'simple', 'moderate', 'complex'
    reasoning: str
    estimated_time: int  # seconds
    requires_context: bool
    can_delegate: bool

@dataclass
class LocalAssistantCapability:
    """Capabilities of a local AI assistant"""
    name: str
    supported_languages: List[str]
    max_complexity: int  # 0-100
    strengths: List[str]  # ['completion', 'refactoring', 'documentation']
    installation_status: bool
    performance_rating: float  # 0-10 based on past results

@dataclass
class DelegationResult:
    """Result of task delegation to local assistant"""
    success: bool
    assistant_used: str
    execution_time: float
    quality_score: float  # 0-10, Claude's assessment
    output: str
    lessons_learned: str
    should_retry_with_claude: bool

class TaskComplexityAnalyzer:
    """Analyzes task complexity to determine if suitable for local assistant"""
    
    def __init__(self):
        self.simple_patterns = [
            "add comment", "format code", "rename variable", "extract method",
            "add logging", "fix indentation", "add docstring", "simple test",
            "basic validation", "simple import", "basic error handling"
        ]
        
        self.complex_patterns = [
            "architecture", "design pattern", "algorithm", "performance optimization",
            "security", "integration", "complex business logic", "database design",
            "api design", "error recovery", "scaling", "distributed system"
        ]
    
    def analyze(self, task_description: str, file_context: Optional[str] = None) -> TaskComplexity:
        """Analyze task complexity"""
        description_lower = task_description.lower()
        
        # Calculate base complexity
        simple_matches = sum(1 for pattern in self.simple_patterns if pattern in description_lower)
        complex_matches = sum(1 for pattern in self.complex_patterns if pattern in description_lower)
        
        # Base score calculation
        base_score = min(complex_matches * 15 + (10 - simple_matches * 2), 100)
        base_score = max(base_score, 0)
        
        # Context requirements
        requires_context = bool(file_context and len(file_context) > 500) or \
                          any(word in description_lower for word in ['existing', 'current', 'modify', 'update', 'integrate'])
        
        # Adjust score based on context needs
        if requires_context:
            base_score += 15
            
        # Length and detail complexity
        if len(task_description.split()) > 20:
            base_score += 10
            
        # Final categorization
        if base_score <= 30:
            category = 'simple'
            can_delegate = True
        elif base_score <= 60:
            category = 'moderate' 
            can_delegate = True  # Can delegate to better local assistants
        else:
            category = 'complex'
            can_delegate = False
            
        # Estimated time (seconds)
        estimated_time = min(base_score * 3, 1800)  # Max 30 minutes
        
        reasoning = f"Score: {base_score} | Simple patterns: {simple_matches} | Complex patterns: {complex_matches}"
        if requires_context:
            reasoning += " | Requires context"
            
        return TaskComplexity(
            score=base_score,
            category=category,
            reasoning=reasoning,
            estimated_time=estimated_time,
            requires_context=requires_context,
            can_delegate=can_delegate
        )

class LocalAssistantManager:
    """Manages local AI coding assistants"""
    
    def __init__(self):
        self.assistants = self._initialize_assistants()
        self.performance_history: Dict[str, List[float]] = {}
    
    def _initialize_assistants(self) -> List[LocalAssistantCapability]:
        """Initialize available local assistants"""
        assistants = []
        
        # aiXcoder - if available
        assistants.append(LocalAssistantCapability(
            name="aiXcoder",
            supported_languages=["python", "javascript", "java", "cpp", "c", "go", "typescript"],
            max_complexity=40,
            strengths=["completion", "refactoring", "simple_fixes"],
            installation_status=self._check_aixcoder_installed(),
            performance_rating=7.5
        ))
        
        # TabNine - if available
        assistants.append(LocalAssistantCapability(
            name="tabnine",
            supported_languages=["python", "javascript", "java", "cpp", "c", "go", "typescript", "rust"],
            max_complexity=35,
            strengths=["completion", "snippets"],
            installation_status=self._check_tabnine_installed(),
            performance_rating=7.0
        ))
        
        # Continue.dev - if available
        assistants.append(LocalAssistantCapability(
            name="continue",
            supported_languages=["python", "javascript", "typescript", "java", "cpp"],
            max_complexity=50,
            strengths=["completion", "refactoring", "documentation", "testing"],
            installation_status=self._check_continue_installed(),
            performance_rating=8.0
        ))
        
        # FauxPilot - if available
        assistants.append(LocalAssistantCapability(
            name="fauxpilot",
            supported_languages=["python", "javascript", "typescript", "java", "cpp", "go"],
            max_complexity=45,
            strengths=["completion", "generation", "refactoring"],
            installation_status=self._check_fauxpilot_installed(),
            performance_rating=7.8
        ))
        
        return assistants
    
    def _check_aixcoder_installed(self) -> bool:
        """Check if aiXcoder is installed"""
        try:
            # Check common installation paths
            result = subprocess.run(['which', 'aixcoder'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def _check_tabnine_installed(self) -> bool:
        """Check if TabNine is installed"""
        try:
            # Check for TabNine binary
            result = subprocess.run(['which', 'TabNine'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
            # Check VS Code extension
            vscode_extensions = Path.home() / ".vscode" / "extensions"
            if vscode_extensions.exists():
                return any("tabnine" in ext.name.lower() for ext in vscode_extensions.iterdir())
            return False
        except:
            return False
    
    def _check_continue_installed(self) -> bool:
        """Check if Continue.dev is installed"""
        try:
            # Check VS Code extension
            vscode_extensions = Path.home() / ".vscode" / "extensions"
            if vscode_extensions.exists():
                return any("continue" in ext.name.lower() for ext in vscode_extensions.iterdir())
            return False
        except:
            return False
    
    def _check_fauxpilot_installed(self) -> bool:
        """Check if FauxPilot is installed"""
        try:
            result = subprocess.run(['docker', 'images', 'fauxpilot'], capture_output=True, text=True)
            return "fauxpilot" in result.stdout
        except:
            return False
    
    def get_best_assistant(self, task_complexity: TaskComplexity, language: str = "python") -> Optional[LocalAssistantCapability]:
        """Get best available assistant for task"""
        available_assistants = [a for a in self.assistants if a.installation_status]
        
        if not available_assistants:
            return None
            
        # Filter by language support
        language_compatible = [a for a in available_assistants if language.lower() in a.supported_languages]
        
        if not language_compatible:
            language_compatible = available_assistants  # Fallback
            
        # Filter by complexity capability
        complexity_compatible = [a for a in language_compatible if a.max_complexity >= task_complexity.score]
        
        if not complexity_compatible:
            return None
            
        # Choose best by performance rating
        return max(complexity_compatible, key=lambda a: a.performance_rating)

class HierarchicalTaskDelegator:
    """Main controller for hierarchical task delegation"""
    
    def __init__(self):
        self.complexity_analyzer = TaskComplexityAnalyzer()
        self.assistant_manager = LocalAssistantManager()
        self.learning_log: List[Dict] = []
        self.success_patterns: Dict[str, List[str]] = {}
        
    async def delegate_task(self, task_description: str, file_path: Optional[str] = None,
                          file_context: Optional[str] = None) -> DelegationResult:
        """Delegate task to appropriate assistant or handle with Claude"""
        
        # Analyze task complexity
        complexity = self.complexity_analyzer.analyze(task_description, file_context)
        
        logger.info(f"Task complexity analysis: {complexity.category} (score: {complexity.score})")
        
        # Check if we can delegate
        if not complexity.can_delegate:
            return DelegationResult(
                success=False,
                assistant_used="none",
                execution_time=0,
                quality_score=0,
                output="Task too complex for local assistant delegation",
                lessons_learned="Complex task requires Claude's full capabilities",
                should_retry_with_claude=True
            )
        
        # Find best assistant
        language = self._detect_language(file_path or "")
        assistant = self.assistant_manager.get_best_assistant(complexity, language)
        
        if not assistant:
            return DelegationResult(
                success=False,
                assistant_used="none",
                execution_time=0,
                quality_score=0,
                output="No suitable local assistant available",
                lessons_learned="Need to install local coding assistants for delegation",
                should_retry_with_claude=True
            )
        
        # Execute task with local assistant
        start_time = asyncio.get_event_loop().time()
        
        try:
            result = await self._execute_with_assistant(assistant, task_description, file_path, file_context)
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Log learning
            self._log_delegation_result(task_description, assistant.name, result, execution_time)
            
            return result
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            logger.error(f"Assistant execution failed: {e}")
            
            return DelegationResult(
                success=False,
                assistant_used=assistant.name,
                execution_time=execution_time,
                quality_score=0,
                output=f"Assistant execution failed: {e}",
                lessons_learned=f"Assistant {assistant.name} failed on {complexity.category} task",
                should_retry_with_claude=True
            )
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file path"""
        if not file_path:
            return "python"
            
        ext_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust'
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'python')
    
    async def _execute_with_assistant(self, assistant: LocalAssistantCapability, 
                                    task_description: str, file_path: Optional[str],
                                    file_context: Optional[str]) -> DelegationResult:
        """Execute task with specific local assistant"""
        
        if assistant.name == "aiXcoder":
            return await self._execute_with_aixcoder(task_description, file_path, file_context)
        elif assistant.name == "tabnine":
            return await self._execute_with_tabnine(task_description, file_path, file_context)
        elif assistant.name == "continue":
            return await self._execute_with_continue(task_description, file_path, file_context)
        elif assistant.name == "fauxpilot":
            return await self._execute_with_fauxpilot(task_description, file_path, file_context)
        else:
            raise ValueError(f"Unknown assistant: {assistant.name}")
    
    async def _execute_with_aixcoder(self, task_description: str, file_path: Optional[str],
                                   file_context: Optional[str]) -> DelegationResult:
        """Execute task with aiXcoder"""
        # This is a simulation - in practice, you'd integrate with aiXcoder's API
        
        await asyncio.sleep(2)  # Simulate processing time
        
        return DelegationResult(
            success=True,
            assistant_used="aiXcoder",
            execution_time=2.0,
            quality_score=7.5,
            output="# aiXcoder completed task (simulated)\n# Added error handling and logging",
            lessons_learned="aiXcoder handles simple refactoring tasks well",
            should_retry_with_claude=False
        )
    
    async def _execute_with_tabnine(self, task_description: str, file_path: Optional[str],
                                  file_context: Optional[str]) -> DelegationResult:
        """Execute task with TabNine"""
        await asyncio.sleep(1.5)  # Simulate processing time
        
        return DelegationResult(
            success=True,
            assistant_used="tabnine", 
            execution_time=1.5,
            quality_score=7.0,
            output="# TabNine completion (simulated)\n# Generated code completion",
            lessons_learned="TabNine good for code completion tasks",
            should_retry_with_claude=False
        )
    
    async def _execute_with_continue(self, task_description: str, file_path: Optional[str],
                                   file_context: Optional[str]) -> DelegationResult:
        """Execute task with Continue.dev"""
        await asyncio.sleep(3.0)  # Simulate processing time
        
        return DelegationResult(
            success=True,
            assistant_used="continue",
            execution_time=3.0,
            quality_score=8.0,
            output="# Continue.dev result (simulated)\n# Refactored code with improvements",
            lessons_learned="Continue.dev handles refactoring and documentation well",
            should_retry_with_claude=False
        )
    
    async def _execute_with_fauxpilot(self, task_description: str, file_path: Optional[str],
                                    file_context: Optional[str]) -> DelegationResult:
        """Execute task with FauxPilot"""
        await asyncio.sleep(2.5)  # Simulate processing time
        
        return DelegationResult(
            success=True,
            assistant_used="fauxpilot",
            execution_time=2.5,
            quality_score=7.8,
            output="# FauxPilot generation (simulated)\n# Generated new code functionality",
            lessons_learned="FauxPilot good for code generation tasks",
            should_retry_with_claude=False
        )
    
    def _log_delegation_result(self, task: str, assistant: str, result: DelegationResult, execution_time: float):
        """Log delegation result for learning"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "task_description": task,
            "assistant_used": assistant,
            "success": result.success,
            "quality_score": result.quality_score,
            "execution_time": execution_time,
            "lessons_learned": result.lessons_learned
        }
        
        self.learning_log.append(log_entry)
        
        # Update success patterns
        if result.success:
            if assistant not in self.success_patterns:
                self.success_patterns[assistant] = []
            self.success_patterns[assistant].append(task)
    
    def get_delegation_stats(self) -> Dict:
        """Get delegation statistics"""
        if not self.learning_log:
            return {"message": "No delegation history"}
            
        total_delegations = len(self.learning_log)
        successful_delegations = sum(1 for entry in self.learning_log if entry["success"])
        
        assistant_stats = {}
        for entry in self.learning_log:
            assistant = entry["assistant_used"]
            if assistant not in assistant_stats:
                assistant_stats[assistant] = {"total": 0, "successful": 0, "avg_quality": 0}
            
            assistant_stats[assistant]["total"] += 1
            if entry["success"]:
                assistant_stats[assistant]["successful"] += 1
                assistant_stats[assistant]["avg_quality"] += entry["quality_score"]
        
        # Calculate averages
        for assistant in assistant_stats:
            if assistant_stats[assistant]["successful"] > 0:
                assistant_stats[assistant]["avg_quality"] /= assistant_stats[assistant]["successful"]
        
        return {
            "total_delegations": total_delegations,
            "success_rate": successful_delegations / total_delegations if total_delegations > 0 else 0,
            "assistant_stats": assistant_stats,
            "success_patterns": self.success_patterns
        }

# Main execution function
async def main():
    """Test the hierarchical delegation system"""
    delegator = HierarchicalTaskDelegator()
    
    # Test tasks of varying complexity
    test_tasks = [
        "Add logging statements to this function",
        "Rename variable 'data' to 'user_data' throughout the file",
        "Add docstring to the calculate_metrics function",
        "Design a scalable microservices architecture for the fitness tracking system",
        "Add error handling for network requests",
        "Implement complex business logic for cross-domain analytics correlation"
    ]
    
    print("🤖 Hierarchical Task Delegation System")
    print("=====================================")
    
    for task in test_tasks:
        print(f"\nTask: {task}")
        result = await delegator.delegate_task(task, "test.py")
        
        print(f"✅ Delegated to: {result.assistant_used}")
        print(f"📊 Success: {result.success}")
        print(f"⭐ Quality: {result.quality_score}/10")
        print(f"⏱️ Time: {result.execution_time:.2f}s")
        print(f"📝 Learned: {result.lessons_learned}")
        
        if result.should_retry_with_claude:
            print("🧠 Recommended: Retry with Claude for better results")
        
        print("-" * 50)
    
    # Show delegation statistics
    stats = delegator.get_delegation_stats()
    print(f"\n📈 Delegation Statistics:")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    asyncio.run(main())