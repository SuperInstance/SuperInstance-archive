#!/usr/bin/env python3
"""
SuperInstance.AI Code Analyzer Bot
Advanced AST-based code analysis for Claude bot productivity enhancement
"""

import ast
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import argparse
from dataclasses import dataclass, asdict
import radon.complexity as complexity
import radon.metrics as metrics

@dataclass
class ServiceAnalysis:
    """Structured analysis results for a service"""
    service_name: str
    file_count: int
    line_count: int
    complexity_score: float
    dependencies: List[str]
    endpoints: List[str]
    architecture_patterns: List[str]
    optimization_suggestions: List[str]
    health_score: float
    
class CodeAnalyzerBot:
    """AI-powered code analysis specialized for SuperInstance services"""
    
    def __init__(self, service_path: str):
        self.service_path = Path(service_path)
        self.service_name = self.service_path.name
        
    def analyze_service(self) -> ServiceAnalysis:
        """Comprehensive service analysis using AST and pattern recognition"""
        print(f"🔍 Analyzing service: {self.service_name}")
        
        # Collect all Python files
        python_files = list(self.service_path.rglob("*.py"))
        
        if not python_files:
            return ServiceAnalysis(
                service_name=self.service_name,
                file_count=0,
                line_count=0,
                complexity_score=0,
                dependencies=[],
                endpoints=[],
                architecture_patterns=[],
                optimization_suggestions=["No Python files found"],
                health_score=0
            )
        
        # Analyze each file
        total_lines = 0
        complexity_scores = []
        dependencies = set()
        endpoints = []
        patterns = set()
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Count lines
                total_lines += len(content.splitlines())
                
                # Parse AST
                tree = ast.parse(content)
                
                # Extract dependencies
                deps = self._extract_dependencies(tree)
                dependencies.update(deps)
                
                # Extract endpoints (FastAPI/Flask patterns)
                eps = self._extract_endpoints(tree)
                endpoints.extend(eps)
                
                # Detect architecture patterns
                pats = self._detect_patterns(tree, content)
                patterns.update(pats)
                
                # Calculate complexity
                try:
                    complexity_data = complexity.cc_visit(content)
                    if complexity_data:
                        avg_complexity = sum(block.complexity for block in complexity_data) / len(complexity_data)
                        complexity_scores.append(avg_complexity)
                except:
                    complexity_scores.append(1.0)  # Default low complexity
                    
            except Exception as e:
                print(f"⚠️ Error analyzing {file_path}: {e}")
                continue
        
        # Calculate overall metrics
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 1.0
        health_score = self._calculate_health_score(total_lines, avg_complexity, len(dependencies))
        optimization_suggestions = self._generate_optimization_suggestions(
            dependencies, endpoints, patterns, avg_complexity
        )
        
        return ServiceAnalysis(
            service_name=self.service_name,
            file_count=len(python_files),
            line_count=total_lines,
            complexity_score=round(avg_complexity, 2),
            dependencies=sorted(list(dependencies)),
            endpoints=endpoints,
            architecture_patterns=sorted(list(patterns)),
            optimization_suggestions=optimization_suggestions,
            health_score=round(health_score, 2)
        )
    
    def _extract_dependencies(self, tree: ast.AST) -> List[str]:
        """Extract import dependencies from AST"""
        dependencies = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    dependencies.append(node.module.split('.')[0])
        
        # Filter out standard library and local imports
        external_deps = []
        stdlib_modules = {'os', 'sys', 'json', 'datetime', 'typing', 'pathlib', 'logging', 'collections'}
        
        for dep in dependencies:
            if dep not in stdlib_modules and not dep.startswith('.'):
                external_deps.append(dep)
        
        return external_deps
    
    def _extract_endpoints(self, tree: ast.AST) -> List[str]:
        """Extract API endpoints from FastAPI/Flask decorators"""
        endpoints = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'attr'):
                        method = decorator.func.attr
                        if method in ['get', 'post', 'put', 'delete', 'patch']:
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                path = decorator.args[0].value
                                endpoints.append(f"{method.upper()} {path}")
        
        return endpoints
    
    def _detect_patterns(self, tree: ast.AST, content: str) -> List[str]:
        """Detect architectural patterns in the code"""
        patterns = []
        
        # Check for common patterns
        if 'class' in content and 'Repository' in content:
            patterns.append('repository_pattern')
        
        if 'fastapi' in content.lower() or 'FastAPI' in content:
            patterns.append('fastapi_framework')
        
        if 'flask' in content.lower() or 'Flask' in content:
            patterns.append('flask_framework')
        
        if 'async def' in content:
            patterns.append('async_programming')
        
        if 'sqlalchemy' in content.lower():
            patterns.append('orm_pattern')
        
        if 'pydantic' in content.lower() or 'BaseModel' in content:
            patterns.append('data_validation')
        
        if 'Depends' in content and 'fastapi' in content.lower():
            patterns.append('dependency_injection')
        
        # Check for error handling
        if 'try:' in content and 'except' in content:
            patterns.append('error_handling')
        
        # Check for logging
        if 'logging' in content or 'logger' in content:
            patterns.append('structured_logging')
        
        return patterns
    
    def _calculate_health_score(self, lines: int, complexity: float, dep_count: int) -> float:
        """Calculate service health score (0-10)"""
        # Base score
        score = 10.0
        
        # Penalize high complexity
        if complexity > 10:
            score -= 2
        elif complexity > 7:
            score -= 1
        
        # Penalize too many dependencies
        if dep_count > 20:
            score -= 2
        elif dep_count > 15:
            score -= 1
        
        # Penalize very large services
        if lines > 5000:
            score -= 2
        elif lines > 2000:
            score -= 1
        
        return max(0, score)
    
    def _generate_optimization_suggestions(self, dependencies: List[str], endpoints: List[str], 
                                         patterns: List[str], complexity: float) -> List[str]:
        """Generate optimization suggestions based on analysis"""
        suggestions = []
        
        if complexity > 10:
            suggestions.append("High complexity detected - consider refactoring into smaller functions")
        
        if len(dependencies) > 20:
            suggestions.append("Many dependencies - review if all are necessary")
        
        if len(endpoints) > 0 and 'error_handling' not in patterns:
            suggestions.append("Add comprehensive error handling to API endpoints")
        
        if 'fastapi_framework' in patterns and 'data_validation' not in patterns:
            suggestions.append("Consider using Pydantic models for request/response validation")
        
        if len(endpoints) > 0 and 'structured_logging' not in patterns:
            suggestions.append("Add structured logging for better observability")
        
        if 'async_programming' in patterns and 'orm_pattern' in patterns:
            suggestions.append("Consider async database operations for better performance")
        
        if not suggestions:
            suggestions.append("Service appears well-structured - consider performance profiling")
        
        return suggestions

def main():
    parser = argparse.ArgumentParser(description='SuperInstance.AI Code Analyzer Bot')
    parser.add_argument('--service', required=True, help='Service name or path to analyze')
    parser.add_argument('--output-format', choices=['json', 'text'], default='text', help='Output format')
    
    args = parser.parse_args()
    
    # Determine service path
    if '/' in args.service:
        service_path = args.service
    else:
        # Assume it's a service name in the services directory
        base_path = Path(__file__).parent.parent.parent.parent
        service_path = base_path / 'services' / args.service
    
    if not os.path.exists(service_path):
        print(f"❌ Service path not found: {service_path}")
        sys.exit(1)
    
    # Analyze service
    analyzer = CodeAnalyzerBot(service_path)
    analysis = analyzer.analyze_service()
    
    # Output results
    if args.output_format == 'json':
        print(json.dumps(asdict(analysis), indent=2))
    else:
        print(f"\n🔍 Code Analysis Report for {analysis.service_name}")
        print("=" * 50)
        print(f"📁 Files: {analysis.file_count}")
        print(f"📄 Lines: {analysis.line_count}")
        print(f"🧮 Complexity Score: {analysis.complexity_score}")
        print(f"🏥 Health Score: {analysis.health_score}/10")
        print(f"\n📦 Dependencies ({len(analysis.dependencies)}):")
        for dep in analysis.dependencies[:10]:  # Show first 10
            print(f"  - {dep}")
        if len(analysis.dependencies) > 10:
            print(f"  ... and {len(analysis.dependencies) - 10} more")
        
        print(f"\n🛤️  API Endpoints ({len(analysis.endpoints)}):")
        for endpoint in analysis.endpoints[:5]:  # Show first 5
            print(f"  - {endpoint}")
        if len(analysis.endpoints) > 5:
            print(f"  ... and {len(analysis.endpoints) - 5} more")
        
        print(f"\n🏗️  Architecture Patterns:")
        for pattern in analysis.architecture_patterns:
            print(f"  ✅ {pattern.replace('_', ' ').title()}")
        
        print(f"\n⚡ Optimization Suggestions:")
        for suggestion in analysis.optimization_suggestions:
            print(f"  💡 {suggestion}")
        
        print(f"\n✨ Analysis complete! Use insights to optimize service architecture.")

if __name__ == "__main__":
    main()