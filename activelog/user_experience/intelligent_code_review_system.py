"""
Intelligent Code Review and Suggestion System for SuperInstance
AI-powered real-time code analysis, optimization suggestions, and automated improvements
"""

import ast
import re
import json
import time
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from datetime import datetime
import hashlib

class ReviewSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ReviewCategory(Enum):
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    ARCHITECTURE = "architecture"
    BEST_PRACTICES = "best_practices"
    OPTIMIZATION = "optimization"

@dataclass
class CodeIssue:
    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    title: str
    description: str
    file_path: str
    line_number: int
    column: int
    code_snippet: str
    suggestion: str
    auto_fixable: bool
    confidence: float
    impact_score: float
    
@dataclass
class CodeSuggestion:
    id: str
    title: str
    description: str
    category: str
    original_code: str
    suggested_code: str
    benefits: List[str]
    estimated_improvement: Dict[str, float]
    confidence: float

@dataclass
class ArchitectureRecommendation:
    id: str
    component_type: str
    recommendation: str
    reasoning: str
    implementation_complexity: str
    estimated_benefit: float
    prerequisites: List[str]

class CodeAnalysisEngine:
    """Advanced code analysis engine with pattern recognition"""
    
    def __init__(self):
        self.patterns = self._load_analysis_patterns()
        self.performance_benchmarks = self._load_performance_benchmarks()
        self.security_rules = self._load_security_rules()
        
    def analyze_code(self, code: str, file_path: str, language: str) -> List[CodeIssue]:
        """Comprehensive code analysis returning issues and suggestions"""
        issues = []
        
        # AST-based analysis for Python
        if language.lower() == 'python':
            issues.extend(self._analyze_python_ast(code, file_path))
        
        # Pattern-based analysis for all languages
        issues.extend(self._analyze_patterns(code, file_path, language))
        
        # Performance analysis
        issues.extend(self._analyze_performance(code, file_path, language))
        
        # Security analysis
        issues.extend(self._analyze_security(code, file_path, language))
        
        # Architecture analysis
        issues.extend(self._analyze_architecture(code, file_path, language))
        
        return sorted(issues, key=lambda x: (x.severity.value, x.impact_score), reverse=True)
    
    def _analyze_python_ast(self, code: str, file_path: str) -> List[CodeIssue]:
        """AST-based Python code analysis"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            class CodeAnalyzer(ast.NodeVisitor):
                def __init__(self, code_lines, file_path):
                    self.code_lines = code_lines
                    self.file_path = file_path
                    self.issues = []
                    self.complexity_score = 0
                    self.function_depth = 0
                
                def visit_FunctionDef(self, node):
                    self.function_depth += 1
                    
                    # Check function complexity
                    complexity = self._calculate_complexity(node)
                    if complexity > 10:
                        self.issues.append(CodeIssue(
                            id=f"complexity_{node.lineno}",
                            category=ReviewCategory.MAINTAINABILITY,
                            severity=ReviewSeverity.WARNING,
                            title="High Complexity Function",
                            description=f"Function '{node.name}' has cyclomatic complexity of {complexity}",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            code_snippet=self._get_code_snippet(node.lineno, 5),
                            suggestion="Consider breaking this function into smaller, more focused functions",
                            auto_fixable=False,
                            confidence=0.9,
                            impact_score=complexity / 20.0
                        ))
                    
                    # Check function length
                    func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                    if func_lines > 50:
                        self.issues.append(CodeIssue(
                            id=f"length_{node.lineno}",
                            category=ReviewCategory.MAINTAINABILITY,
                            severity=ReviewSeverity.INFO,
                            title="Long Function",
                            description=f"Function '{node.name}' is {func_lines} lines long",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            code_snippet=self._get_code_snippet(node.lineno, 3),
                            suggestion="Consider breaking long functions into smaller, more focused functions",
                            auto_fixable=False,
                            confidence=0.7,
                            impact_score=func_lines / 100.0
                        ))
                    
                    self.generic_visit(node)
                    self.function_depth -= 1
                
                def visit_For(self, node):
                    # Nested loop detection
                    if self._count_nested_loops(node) > 2:
                        self.issues.append(CodeIssue(
                            id=f"nested_loops_{node.lineno}",
                            category=ReviewCategory.PERFORMANCE,
                            severity=ReviewSeverity.WARNING,
                            title="Deeply Nested Loops",
                            description="Multiple nested loops detected - potential performance issue",
                            file_path=file_path,
                            line_number=node.lineno,
                            column=node.col_offset,
                            code_snippet=self._get_code_snippet(node.lineno, 5),
                            suggestion="Consider optimizing with list comprehensions, vectorized operations, or algorithm improvements",
                            auto_fixable=False,
                            confidence=0.8,
                            impact_score=0.7
                        ))
                    
                    self.generic_visit(node)
                
                def visit_Try(self, node):
                    # Broad exception handling
                    for handler in node.handlers:
                        if handler.type is None or (isinstance(handler.type, ast.Name) and handler.type.id == 'Exception'):
                            self.issues.append(CodeIssue(
                                id=f"broad_except_{handler.lineno}",
                                category=ReviewCategory.BEST_PRACTICES,
                                severity=ReviewSeverity.WARNING,
                                title="Broad Exception Handling",
                                description="Catching broad exceptions can hide bugs",
                                file_path=file_path,
                                line_number=handler.lineno,
                                column=handler.col_offset,
                                code_snippet=self._get_code_snippet(handler.lineno, 3),
                                suggestion="Catch specific exceptions instead of broad Exception types",
                                auto_fixable=False,
                                confidence=0.9,
                                impact_score=0.6
                            ))
                    
                    self.generic_visit(node)
                
                def _calculate_complexity(self, node) -> int:
                    """Calculate cyclomatic complexity"""
                    complexity = 1  # Base complexity
                    
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                            complexity += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1
                    
                    return complexity
                
                def _count_nested_loops(self, node) -> int:
                    """Count nested loop depth"""
                    max_depth = 0
                    current_depth = 0
                    
                    for child in ast.walk(node):
                        if isinstance(child, (ast.For, ast.While)):
                            current_depth += 1
                            max_depth = max(max_depth, current_depth)
                    
                    return max_depth
                
                def _get_code_snippet(self, line_num: int, context_lines: int = 3) -> str:
                    """Get code snippet around line"""
                    start = max(0, line_num - context_lines - 1)
                    end = min(len(self.code_lines), line_num + context_lines)
                    return '\n'.join(self.code_lines[start:end])
            
            code_lines = code.split('\n')
            analyzer = CodeAnalyzer(code_lines, file_path)
            analyzer.visit(tree)
            issues.extend(analyzer.issues)
            
        except SyntaxError as e:
            issues.append(CodeIssue(
                id=f"syntax_error_{e.lineno}",
                category=ReviewCategory.BEST_PRACTICES,
                severity=ReviewSeverity.ERROR,
                title="Syntax Error",
                description=f"Syntax error: {e.msg}",
                file_path=file_path,
                line_number=e.lineno or 1,
                column=e.offset or 0,
                code_snippet="",
                suggestion="Fix syntax error",
                auto_fixable=False,
                confidence=1.0,
                impact_score=1.0
            ))
        
        return issues
    
    def _analyze_patterns(self, code: str, file_path: str, language: str) -> List[CodeIssue]:
        """Pattern-based analysis for common issues"""
        issues = []
        lines = code.split('\n')
        
        # SQL injection patterns
        sql_patterns = [
            (r'execute\s*\(\s*["\'].*%.*["\']', "Potential SQL injection vulnerability"),
            (r'query\s*=.*\+.*', "String concatenation in SQL query - use parameterized queries"),
            (r'cursor\.execute\s*\(\s*f["\']', "f-string in SQL query - use parameterized queries")
        ]
        
        # Performance anti-patterns
        perf_patterns = [
            (r'for.*in.*range\(len\(.*\)\)', "Use enumerate() instead of range(len())"),
            (r'\.append\(.*\)\s*$', "Consider list comprehension for better performance"),
            (r'time\.sleep\(.*\)', "Blocking sleep detected - consider async alternatives")
        ]
        
        # Code smell patterns
        smell_patterns = [
            (r'#\s*TODO.*', "TODO comment found - consider creating a task"),
            (r'#\s*FIXME.*', "FIXME comment found - requires attention"),
            (r'print\s*\(.*\)', "Debug print statement - remove before production")
        ]
        
        all_patterns = [
            (sql_patterns, ReviewCategory.SECURITY, ReviewSeverity.CRITICAL),
            (perf_patterns, ReviewCategory.PERFORMANCE, ReviewSeverity.WARNING),
            (smell_patterns, ReviewCategory.MAINTAINABILITY, ReviewSeverity.INFO)
        ]
        
        for patterns, category, severity in all_patterns:
            for pattern, message in patterns:
                for line_num, line in enumerate(lines, 1):
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(CodeIssue(
                            id=f"pattern_{hashlib.md5(f'{pattern}_{line_num}'.encode()).hexdigest()[:8]}",
                            category=category,
                            severity=severity,
                            title=message,
                            description=f"Pattern detected: {pattern}",
                            file_path=file_path,
                            line_number=line_num,
                            column=0,
                            code_snippet=line.strip(),
                            suggestion=message,
                            auto_fixable=category == ReviewCategory.MAINTAINABILITY,
                            confidence=0.8,
                            impact_score=0.5 if severity == ReviewSeverity.INFO else 0.8
                        ))
        
        return issues
    
    def _analyze_performance(self, code: str, file_path: str, language: str) -> List[CodeIssue]:
        """Performance-focused analysis"""
        issues = []
        
        # Inefficient operations
        inefficient_patterns = {
            r'\.sort\(\).*\.reverse\(\)': "Use sort(reverse=True) instead of sort().reverse()",
            r'len\(.*\)\s*==\s*0': "Use 'not container' instead of 'len(container) == 0'",
            r'list\(.*\.keys\(\)\)': "Dictionary keys() is already iterable, no need for list()",
            r'for.*in.*dict\.keys\(\)': "Iterate directly over dictionary instead of .keys()",
        }
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, suggestion in inefficient_patterns.items():
                if re.search(pattern, line):
                    issues.append(CodeIssue(
                        id=f"perf_{hashlib.md5(f'{pattern}_{line_num}'.encode()).hexdigest()[:8]}",
                        category=ReviewCategory.PERFORMANCE,
                        severity=ReviewSeverity.INFO,
                        title="Performance Optimization Opportunity",
                        description=suggestion,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        code_snippet=line.strip(),
                        suggestion=suggestion,
                        auto_fixable=True,
                        confidence=0.9,
                        impact_score=0.3
                    ))
        
        return issues
    
    def _analyze_security(self, code: str, file_path: str, language: str) -> List[CodeIssue]:
        """Security-focused analysis"""
        issues = []
        
        security_patterns = {
            r'eval\s*\(': "Use of eval() is dangerous - consider alternatives",
            r'exec\s*\(': "Use of exec() is dangerous - consider alternatives",
            r'subprocess.*shell=True': "shell=True in subprocess is dangerous",
            r'password\s*=\s*["\'].*["\']': "Hardcoded password detected",
            r'api_key\s*=\s*["\'].*["\']': "Hardcoded API key detected",
            r'secret\s*=\s*["\'].*["\']': "Hardcoded secret detected"
        }
        
        lines = code.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern, description in security_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    severity = ReviewSeverity.CRITICAL if 'eval' in pattern or 'exec' in pattern else ReviewSeverity.ERROR
                    issues.append(CodeIssue(
                        id=f"sec_{hashlib.md5(f'{pattern}_{line_num}'.encode()).hexdigest()[:8]}",
                        category=ReviewCategory.SECURITY,
                        severity=severity,
                        title="Security Issue",
                        description=description,
                        file_path=file_path,
                        line_number=line_num,
                        column=0,
                        code_snippet=line.strip(),
                        suggestion=description,
                        auto_fixable=False,
                        confidence=0.9,
                        impact_score=1.0
                    ))
        
        return issues
    
    def _analyze_architecture(self, code: str, file_path: str, language: str) -> List[CodeIssue]:
        """Architecture and design analysis"""
        issues = []
        
        # Class design issues
        if language.lower() == 'python':
            try:
                tree = ast.parse(code)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Count methods
                        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                        if len(methods) > 20:
                            issues.append(CodeIssue(
                                id=f"god_class_{node.lineno}",
                                category=ReviewCategory.ARCHITECTURE,
                                severity=ReviewSeverity.WARNING,
                                title="God Class Anti-pattern",
                                description=f"Class '{node.name}' has {len(methods)} methods",
                                file_path=file_path,
                                line_number=node.lineno,
                                column=node.col_offset,
                                code_snippet=f"class {node.name}:",
                                suggestion="Consider breaking large classes into smaller, focused classes",
                                auto_fixable=False,
                                confidence=0.8,
                                impact_score=len(methods) / 30.0
                            ))
                        
                        # Check for inheritance depth
                        if len(node.bases) > 0:
                            # This is a simplified check - in reality, you'd trace inheritance
                            pass
                            
            except SyntaxError:
                pass
        
        return issues
    
    def _load_analysis_patterns(self) -> Dict[str, Any]:
        """Load analysis patterns from configuration"""
        return {
            "python": {
                "imports": ["ast", "re", "json"],
                "patterns": {},
                "rules": {}
            }
        }
    
    def _load_performance_benchmarks(self) -> Dict[str, Any]:
        """Load performance benchmarks"""
        return {
            "python": {
                "loop_complexity": 3,
                "function_length": 50,
                "class_methods": 20
            }
        }
    
    def _load_security_rules(self) -> Dict[str, Any]:
        """Load security rules"""
        return {
            "dangerous_functions": ["eval", "exec"],
            "sensitive_patterns": ["password", "api_key", "secret", "token"]
        }

class SuggestionEngine:
    """AI-powered code suggestion engine"""
    
    def __init__(self):
        self.suggestion_templates = self._load_suggestion_templates()
        self.best_practices = self._load_best_practices()
    
    def generate_suggestions(self, code: str, context: Dict[str, Any]) -> List[CodeSuggestion]:
        """Generate intelligent code suggestions"""
        suggestions = []
        
        # Performance suggestions
        suggestions.extend(self._generate_performance_suggestions(code, context))
        
        # Architecture suggestions
        suggestions.extend(self._generate_architecture_suggestions(code, context))
        
        # Modern Python features
        suggestions.extend(self._generate_modernization_suggestions(code, context))
        
        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)
    
    def _generate_performance_suggestions(self, code: str, context: Dict[str, Any]) -> List[CodeSuggestion]:
        """Generate performance improvement suggestions"""
        suggestions = []
        
        # List comprehension suggestions
        for_loop_pattern = r'(\w+)\s*=\s*\[\]\s*\n\s*for\s+(\w+)\s+in\s+([^:]+):\s*\n\s*\1\.append\(([^)]+)\)'
        matches = re.finditer(for_loop_pattern, code, re.MULTILINE)
        
        for match in matches:
            result_var, loop_var, iterable, expression = match.groups()
            original = match.group(0)
            suggested = f"{result_var} = [{expression} for {loop_var} in {iterable}]"
            
            suggestions.append(CodeSuggestion(
                id=f"listcomp_{hash(original)}",
                title="Use List Comprehension",
                description="Replace loop with more efficient list comprehension",
                category="performance",
                original_code=original,
                suggested_code=suggested,
                benefits=["Better performance", "More Pythonic", "Reduced lines of code"],
                estimated_improvement={"performance": 0.3, "readability": 0.2},
                confidence=0.9
            ))
        
        return suggestions
    
    def _generate_architecture_suggestions(self, code: str, context: Dict[str, Any]) -> List[CodeSuggestion]:
        """Generate architectural improvement suggestions"""
        suggestions = []
        
        # Suggest using context managers
        if 'open(' in code and 'close()' in code:
            suggestions.append(CodeSuggestion(
                id="context_manager",
                title="Use Context Manager",
                description="Replace manual file handling with context manager",
                category="architecture",
                original_code="f = open('file.txt')\n# ... code ...\nf.close()",
                suggested_code="with open('file.txt') as f:\n    # ... code ...",
                benefits=["Automatic resource cleanup", "Exception safety", "Cleaner code"],
                estimated_improvement={"reliability": 0.4, "maintainability": 0.3},
                confidence=0.95
            ))
        
        return suggestions
    
    def _generate_modernization_suggestions(self, code: str, context: Dict[str, Any]) -> List[CodeSuggestion]:
        """Generate suggestions for modern Python features"""
        suggestions = []
        
        # f-string suggestions
        format_pattern = r'["\'].*%.*["\']|.*\.format\('
        if re.search(format_pattern, code):
            suggestions.append(CodeSuggestion(
                id="f_strings",
                title="Use f-strings",
                description="Replace string formatting with f-strings",
                category="modernization",
                original_code='name = "world"\nprint("Hello %s" % name)',
                suggested_code='name = "world"\nprint(f"Hello {name}")',
                benefits=["Better performance", "More readable", "Type safety"],
                estimated_improvement={"performance": 0.1, "readability": 0.3},
                confidence=0.8
            ))
        
        return suggestions
    
    def _load_suggestion_templates(self) -> Dict[str, Any]:
        """Load suggestion templates"""
        return {
            "performance": {},
            "architecture": {},
            "modernization": {}
        }
    
    def _load_best_practices(self) -> Dict[str, Any]:
        """Load best practices database"""
        return {
            "python": {
                "pep8": True,
                "typing": True,
                "docstrings": True
            }
        }

class IntelligentCodeReviewSystem:
    """Main system for intelligent code review and suggestions"""
    
    def __init__(self):
        self.analysis_engine = CodeAnalysisEngine()
        self.suggestion_engine = SuggestionEngine()
        self.review_history: Dict[str, List[Dict[str, Any]]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.auto_fix_enabled = True
        
    def review_code(self, code: str, file_path: str, language: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Complete code review with issues and suggestions"""
        start_time = time.time()
        
        # Analyze code for issues
        issues = self.analysis_engine.analyze_code(code, file_path, language)
        
        # Generate suggestions
        context = {
            "language": language,
            "file_path": file_path,
            "user_id": user_id,
            "issues": issues
        }
        suggestions = self.suggestion_engine.generate_suggestions(code, context)
        
        # Filter based on user preferences
        if user_id and user_id in self.user_preferences:
            issues = self._filter_by_preferences(issues, user_id)
            suggestions = self._filter_suggestions_by_preferences(suggestions, user_id)
        
        # Generate architecture recommendations
        architecture_recs = self._generate_architecture_recommendations(code, issues, language)
        
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(issues, len(code.split('\n')))
        
        review_result = {
            "file_path": file_path,
            "language": language,
            "timestamp": time.time(),
            "analysis_time": time.time() - start_time,
            "quality_score": quality_score,
            "issues": [asdict(issue) for issue in issues],
            "suggestions": [asdict(suggestion) for suggestion in suggestions],
            "architecture_recommendations": [asdict(rec) for rec in architecture_recs],
            "summary": self._generate_review_summary(issues, suggestions),
            "auto_fixes_available": len([i for i in issues if i.auto_fixable])
        }
        
        # Store in history
        if user_id:
            if user_id not in self.review_history:
                self.review_history[user_id] = []
            self.review_history[user_id].append(review_result)
        
        return review_result
    
    def apply_auto_fixes(self, code: str, file_path: str, selected_issues: List[str]) -> Dict[str, Any]:
        """Apply automatic fixes to selected issues"""
        if not self.auto_fix_enabled:
            return {"success": False, "message": "Auto-fix disabled"}
        
        fixed_code = code
        applied_fixes = []
        
        # Get fixable issues
        all_issues = self.analysis_engine.analyze_code(code, file_path, "python")
        fixable_issues = [issue for issue in all_issues if issue.auto_fixable and issue.id in selected_issues]
        
        for issue in fixable_issues:
            try:
                if issue.category == ReviewCategory.PERFORMANCE:
                    fixed_code = self._apply_performance_fix(fixed_code, issue)
                elif issue.category == ReviewCategory.STYLE:
                    fixed_code = self._apply_style_fix(fixed_code, issue)
                
                applied_fixes.append(issue.id)
                
            except Exception as e:
                print(f"Failed to apply fix for {issue.id}: {e}")
        
        return {
            "success": True,
            "fixed_code": fixed_code,
            "applied_fixes": applied_fixes,
            "total_fixes": len(applied_fixes)
        }
    
    def set_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Set user preferences for code review"""
        self.user_preferences[user_id] = preferences
    
    def get_learning_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate learning insights based on review history"""
        if user_id not in self.review_history:
            return {"message": "No review history available"}
        
        history = self.review_history[user_id]
        recent_reviews = history[-10:]  # Last 10 reviews
        
        # Calculate trends
        quality_trend = [review["quality_score"] for review in recent_reviews]
        common_issues = self._analyze_common_issues(recent_reviews)
        improvement_areas = self._identify_improvement_areas(recent_reviews)
        
        return {
            "total_reviews": len(history),
            "quality_trend": quality_trend,
            "average_quality": sum(quality_trend) / len(quality_trend) if quality_trend else 0,
            "common_issues": common_issues,
            "improvement_areas": improvement_areas,
            "progress_summary": self._generate_progress_summary(quality_trend)
        }
    
    def _filter_by_preferences(self, issues: List[CodeIssue], user_id: str) -> List[CodeIssue]:
        """Filter issues based on user preferences"""
        prefs = self.user_preferences.get(user_id, {})
        
        if prefs.get("hide_info_level", False):
            issues = [i for i in issues if i.severity != ReviewSeverity.INFO]
        
        if "ignored_categories" in prefs:
            ignored = set(prefs["ignored_categories"])
            issues = [i for i in issues if i.category.value not in ignored]
        
        return issues
    
    def _filter_suggestions_by_preferences(self, suggestions: List[CodeSuggestion], user_id: str) -> List[CodeSuggestion]:
        """Filter suggestions based on user preferences"""
        prefs = self.user_preferences.get(user_id, {})
        
        if "preferred_suggestion_types" in prefs:
            preferred = set(prefs["preferred_suggestion_types"])
            suggestions = [s for s in suggestions if s.category in preferred]
        
        return suggestions
    
    def _generate_architecture_recommendations(self, code: str, issues: List[CodeIssue], language: str) -> List[ArchitectureRecommendation]:
        """Generate high-level architecture recommendations"""
        recommendations = []
        
        # Check for common architecture patterns
        if len(issues) > 10:
            recommendations.append(ArchitectureRecommendation(
                id="refactor_suggestion",
                component_type="architecture",
                recommendation="Consider refactoring this module",
                reasoning=f"Found {len(issues)} issues indicating potential design problems",
                implementation_complexity="medium",
                estimated_benefit=0.7,
                prerequisites=["Code review", "Testing framework"]
            ))
        
        # Suggest design patterns
        if any(issue.category == ReviewCategory.ARCHITECTURE for issue in issues):
            recommendations.append(ArchitectureRecommendation(
                id="design_pattern",
                component_type="pattern",
                recommendation="Consider applying design patterns",
                reasoning="Architecture issues suggest need for better structure",
                implementation_complexity="high",
                estimated_benefit=0.8,
                prerequisites=["Design pattern knowledge", "Refactoring tools"]
            ))
        
        return recommendations
    
    def _calculate_quality_score(self, issues: List[CodeIssue], code_lines: int) -> float:
        """Calculate overall code quality score"""
        if not issues:
            return 1.0
        
        # Weight by severity
        severity_weights = {
            ReviewSeverity.INFO: 0.1,
            ReviewSeverity.WARNING: 0.3,
            ReviewSeverity.ERROR: 0.7,
            ReviewSeverity.CRITICAL: 1.0
        }
        
        total_impact = sum(severity_weights[issue.severity] * issue.impact_score for issue in issues)
        
        # Normalize by code size
        normalized_impact = total_impact / max(code_lines / 10, 1)
        
        # Quality score (0-1, higher is better)
        quality_score = max(0.0, 1.0 - min(normalized_impact, 1.0))
        
        return round(quality_score, 2)
    
    def _generate_review_summary(self, issues: List[CodeIssue], suggestions: List[CodeSuggestion]) -> Dict[str, Any]:
        """Generate human-readable review summary"""
        severity_counts = {}
        category_counts = {}
        
        for issue in issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
            category_counts[issue.category.value] = category_counts.get(issue.category.value, 0) + 1
        
        return {
            "total_issues": len(issues),
            "total_suggestions": len(suggestions),
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "top_priority": issues[0].title if issues else "No issues found",
            "auto_fixable": len([i for i in issues if i.auto_fixable])
        }
    
    def _apply_performance_fix(self, code: str, issue: CodeIssue) -> str:
        """Apply performance-related fixes"""
        # This is a simplified example - real implementation would be more sophisticated
        if "range(len(" in issue.code_snippet:
            # Fix range(len()) to enumerate
            return code.replace(
                issue.code_snippet,
                issue.code_snippet.replace("range(len(", "enumerate(").replace("))", ")")
            )
        return code
    
    def _apply_style_fix(self, code: str, issue: CodeIssue) -> str:
        """Apply style-related fixes"""
        # Remove debug print statements
        if issue.title == "Debug print statement":
            lines = code.split('\n')
            lines[issue.line_number - 1] = ""  # Remove the line
            return '\n'.join(lines)
        return code
    
    def _analyze_common_issues(self, reviews: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze common issues across reviews"""
        issue_counts = {}
        
        for review in reviews:
            for issue in review["issues"]:
                title = issue["title"]
                issue_counts[title] = issue_counts.get(title, 0) + 1
        
        # Return top 5 most common issues
        return dict(sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5])
    
    def _identify_improvement_areas(self, reviews: List[Dict[str, Any]]) -> List[str]:
        """Identify areas for improvement"""
        category_counts = {}
        
        for review in reviews:
            for issue in review["issues"]:
                category = issue["category"]
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Return categories that need most attention
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, count in sorted_categories[:3]]
    
    def _generate_progress_summary(self, quality_trend: List[float]) -> str:
        """Generate progress summary"""
        if len(quality_trend) < 2:
            return "Insufficient data for trend analysis"
        
        recent_avg = sum(quality_trend[-3:]) / len(quality_trend[-3:])
        earlier_avg = sum(quality_trend[:3]) / len(quality_trend[:3])
        
        if recent_avg > earlier_avg + 0.1:
            return "Quality is improving significantly"
        elif recent_avg > earlier_avg:
            return "Quality is improving"
        elif recent_avg < earlier_avg - 0.1:
            return "Quality needs attention"
        else:
            return "Quality is stable"

if __name__ == "__main__":
    # Example usage
    review_system = IntelligentCodeReviewSystem()
    
    sample_code = '''
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            result.append(data[i] * 2)
    return result

def bad_function():
    password = "hardcoded_password"
    eval("print('hello')")
    return password
'''
    
    review = review_system.review_code(sample_code, "example.py", "python", "user_123")
    print(json.dumps(review, indent=2))