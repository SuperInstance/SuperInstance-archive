#!/usr/bin/env python3
"""
Reverse Engineering Toolkit for SuperInstance
==============================================

Advanced analysis tools inspired by reverse engineering methodologies to deeply
understand and optimize the SuperInstance system. This toolkit provides static
and dynamic analysis capabilities for comprehensive system optimization.

Based on insights from reverse engineering tutorials and deep system analysis
methodologies used in security research and performance optimization.
"""

import ast
import dis
import inspect
import sys
import gc
import psutil
import time
import asyncio
import json
import pickle
import hashlib
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Set, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AnalysisType(Enum):
    """Types of analysis performed"""
    STATIC_CODE = "static_code_analysis"
    DYNAMIC_RUNTIME = "dynamic_runtime_analysis"
    MEMORY_FORENSICS = "memory_forensics"
    PERFORMANCE_PROFILING = "performance_profiling"
    DEPENDENCY_MAPPING = "dependency_mapping"
    VULNERABILITY_SCANNING = "vulnerability_scanning"
    ASSEMBLY_ANALYSIS = "assembly_analysis"

@dataclass
class CodeSignature:
    """Signature of code structure for pattern matching"""
    function_name: str
    argument_count: int
    return_annotation: Optional[str]
    complexity_score: int
    instruction_pattern: List[str]
    call_patterns: List[str]
    memory_access_pattern: List[str]
    computational_signature: str

@dataclass
class PerformanceProfile:
    """Performance profile of code execution"""
    function_name: str
    total_time_ms: float
    call_count: int
    memory_peak_mb: float
    cpu_usage_percent: float
    io_operations: int
    cache_hits: int
    cache_misses: int
    bottleneck_instructions: List[str]

@dataclass
class SecurityVulnerability:
    """Detected security vulnerability"""
    vulnerability_type: str
    severity: str  # "low", "medium", "high", "critical"
    location: str
    description: str
    exploitation_potential: float
    mitigation_suggestions: List[str]

class StaticCodeAnalyzer:
    """
    Static analysis of code without execution
    Like Ghidra's static analysis capabilities
    """
    
    def __init__(self):
        self.ast_analyzer = ASTAnalyzer()
        self.bytecode_analyzer = BytecodeAnalyzer()
        self.pattern_matcher = PatternMatcher()
        self.complexity_calculator = ComplexityCalculator()
    
    def analyze_source_code(self, source_code: str) -> Dict[str, Any]:
        """Comprehensive static analysis of source code"""
        try:
            # Parse AST
            tree = ast.parse(source_code)
            
            # Multiple analysis passes
            analysis_results = {
                'ast_analysis': self.ast_analyzer.analyze_ast(tree),
                'complexity_analysis': self.complexity_calculator.calculate_complexity(tree),
                'pattern_analysis': self.pattern_matcher.find_patterns(tree),
                'security_analysis': self._security_analysis(tree),
                'performance_predictions': self._predict_performance(tree),
                'optimization_opportunities': self._find_optimizations(tree)
            }
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Static analysis failed: {e}")
            return {'error': str(e)}
    
    def analyze_bytecode(self, function: Callable) -> Dict[str, Any]:
        """Analyze Python bytecode like assembly analysis"""
        try:
            bytecode = dis.Bytecode(function)
            instructions = list(bytecode)
            
            analysis = {
                'instruction_count': len(instructions),
                'instruction_types': self._categorize_instructions(instructions),
                'stack_usage': self._analyze_stack_usage(instructions),
                'jump_patterns': self._analyze_jumps(instructions),
                'call_patterns': self._analyze_calls(instructions),
                'memory_patterns': self._analyze_memory_access(instructions),
                'optimization_hints': self._generate_bytecode_optimizations(instructions)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Bytecode analysis failed: {e}")
            return {'error': str(e)}
    
    def _categorize_instructions(self, instructions: List) -> Dict[str, int]:
        """Categorize bytecode instructions"""
        categories = defaultdict(int)
        
        for instr in instructions:
            if 'LOAD' in instr.opname:
                categories['load_operations'] += 1
            elif 'STORE' in instr.opname:
                categories['store_operations'] += 1
            elif 'CALL' in instr.opname:
                categories['call_operations'] += 1
            elif 'JUMP' in instr.opname:
                categories['jump_operations'] += 1
            elif 'BINARY' in instr.opname:
                categories['binary_operations'] += 1
            elif 'UNARY' in instr.opname:
                categories['unary_operations'] += 1
            else:
                categories['other_operations'] += 1
        
        return dict(categories)
    
    def _analyze_stack_usage(self, instructions: List) -> Dict[str, int]:
        """Analyze stack usage patterns"""
        stack_depth = 0
        max_stack_depth = 0
        
        for instr in instructions:
            # Simplified stack effect calculation
            if 'LOAD' in instr.opname:
                stack_depth += 1
            elif 'STORE' in instr.opname:
                stack_depth -= 1
            elif 'BINARY' in instr.opname:
                stack_depth -= 1  # Consumes 2, produces 1
            elif 'CALL' in instr.opname:
                # Simplified - actual depends on argument count
                stack_depth -= 1
            
            max_stack_depth = max(max_stack_depth, stack_depth)
        
        return {
            'max_stack_depth': max_stack_depth,
            'final_stack_depth': stack_depth
        }
    
    def _analyze_jumps(self, instructions: List) -> Dict[str, Any]:
        """Analyze jump patterns for control flow"""
        jumps = []
        labels = set()
        
        for i, instr in enumerate(instructions):
            if 'JUMP' in instr.opname:
                jumps.append({
                    'instruction': instr.opname,
                    'from_offset': instr.offset,
                    'to_offset': instr.arg if instr.arg else None,
                    'is_conditional': 'IF' in instr.opname
                })
            
            if instr.is_jump_target:
                labels.add(instr.offset)
        
        return {
            'total_jumps': len(jumps),
            'conditional_jumps': len([j for j in jumps if j['is_conditional']]),
            'unconditional_jumps': len([j for j in jumps if not j['is_conditional']]),
            'jump_targets': list(labels),
            'control_flow_complexity': len(jumps) + len(labels)
        }
    
    def _analyze_calls(self, instructions: List) -> Dict[str, Any]:
        """Analyze function call patterns"""
        calls = []
        
        for instr in instructions:
            if 'CALL' in instr.opname:
                calls.append({
                    'instruction': instr.opname,
                    'offset': instr.offset,
                    'argument_count': instr.arg if instr.arg else 0
                })
        
        return {
            'total_calls': len(calls),
            'avg_args_per_call': sum(c['argument_count'] for c in calls) / max(len(calls), 1),
            'max_args_in_call': max([c['argument_count'] for c in calls], default=0)
        }
    
    def _analyze_memory_access(self, instructions: List) -> Dict[str, Any]:
        """Analyze memory access patterns"""
        memory_ops = []
        
        for instr in instructions:
            if any(op in instr.opname for op in ['LOAD_GLOBAL', 'STORE_GLOBAL', 
                                               'LOAD_ATTR', 'STORE_ATTR',
                                               'LOAD_FAST', 'STORE_FAST']):
                memory_ops.append({
                    'type': instr.opname,
                    'offset': instr.offset,
                    'name': instr.argval if hasattr(instr, 'argval') else None
                })
        
        return {
            'total_memory_operations': len(memory_ops),
            'global_accesses': len([op for op in memory_ops if 'GLOBAL' in op['type']]),
            'attribute_accesses': len([op for op in memory_ops if 'ATTR' in op['type']]),
            'local_accesses': len([op for op in memory_ops if 'FAST' in op['type']])
        }
    
    def _security_analysis(self, tree: ast.AST) -> List[SecurityVulnerability]:
        """Security vulnerability analysis"""
        vulnerabilities = []
        
        for node in ast.walk(tree):
            # Check for eval() usage
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in ['eval', 'exec']:
                    vulnerabilities.append(SecurityVulnerability(
                        vulnerability_type='code_injection',
                        severity='critical',
                        location=f'line {node.lineno}',
                        description=f'Use of {node.func.id}() enables code injection',
                        exploitation_potential=0.9,
                        mitigation_suggestions=['Use ast.literal_eval() instead', 
                                              'Validate input before evaluation']
                    ))
            
            # Check for pickle usage
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'pickle':
                        vulnerabilities.append(SecurityVulnerability(
                            vulnerability_type='deserialization',
                            severity='high',
                            location=f'line {node.lineno}',
                            description='pickle module can execute arbitrary code during deserialization',
                            exploitation_potential=0.7,
                            mitigation_suggestions=['Use json instead of pickle',
                                                  'Validate pickle data sources']
                        ))
        
        return vulnerabilities
    
    def _predict_performance(self, tree: ast.AST) -> Dict[str, Any]:
        """Predict performance characteristics from static analysis"""
        predictions = {
            'loop_nesting_depth': 0,
            'function_call_density': 0,
            'memory_allocation_points': 0,
            'complexity_score': 0
        }
        
        current_loop_depth = 0
        max_loop_depth = 0
        function_calls = 0
        total_nodes = 0
        
        for node in ast.walk(tree):
            total_nodes += 1
            
            if isinstance(node, (ast.For, ast.While)):
                current_loop_depth += 1
                max_loop_depth = max(max_loop_depth, current_loop_depth)
            elif isinstance(node, ast.Call):
                function_calls += 1
                # Check for memory allocation patterns
                if isinstance(node.func, ast.Name) and node.func.id in ['list', 'dict', 'set', 'tuple']:
                    predictions['memory_allocation_points'] += 1
        
        predictions.update({
            'loop_nesting_depth': max_loop_depth,
            'function_call_density': function_calls / max(total_nodes, 1),
            'complexity_score': max_loop_depth * 2 + function_calls
        })
        
        return predictions
    
    def _find_optimizations(self, tree: ast.AST) -> List[str]:
        """Find optimization opportunities"""
        optimizations = []
        
        for node in ast.walk(tree):
            # Suggest list comprehensions instead of loops
            if isinstance(node, ast.For):
                if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                    if node.iter.func.id == 'range':
                        optimizations.append('Consider using list comprehension instead of for loop')
            
            # Suggest caching for repeated calculations
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    optimizations.append('Consider caching method calls if expensive')
        
        return list(set(optimizations))  # Remove duplicates
    
    def _generate_bytecode_optimizations(self, instructions: List) -> List[str]:
        """Generate optimization suggestions from bytecode analysis"""
        optimizations = []
        
        # Count instruction types
        load_count = sum(1 for instr in instructions if 'LOAD' in instr.opname)
        call_count = sum(1 for instr in instructions if 'CALL' in instr.opname)
        
        if load_count > 20:
            optimizations.append('High number of load operations - consider local variable caching')
        
        if call_count > 10:
            optimizations.append('High number of function calls - consider inlining small functions')
        
        return optimizations

class DynamicRuntimeAnalyzer:
    """
    Dynamic analysis of running code
    Like runtime debugging and profiling tools
    """
    
    def __init__(self):
        self.execution_tracer = ExecutionTracer()
        self.memory_monitor = MemoryMonitor()
        self.performance_profiler = PerformanceProfiler()
    
    async def analyze_function_execution(self, func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """Comprehensive runtime analysis of function execution"""
        analysis_results = {}
        
        # Start monitoring
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        # Execute with tracing
        trace_data = []
        def trace_calls(frame, event, arg):
            if event == 'call':
                trace_data.append({
                    'event': 'call',
                    'function': frame.f_code.co_name,
                    'filename': frame.f_code.co_filename,
                    'lineno': frame.f_lineno,
                    'timestamp': time.time()
                })
            elif event == 'return':
                trace_data.append({
                    'event': 'return',
                    'function': frame.f_code.co_name,
                    'value': str(arg)[:100],  # Truncate for logging
                    'timestamp': time.time()
                })
            return trace_calls
        
        # Execute function with tracing
        sys.settrace(trace_calls)
        try:
            result = func(*args, **kwargs)
        finally:
            sys.settrace(None)
        
        # Calculate metrics
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        analysis_results = {
            'execution_time_ms': (end_time - start_time) * 1000,
            'memory_delta_mb': (end_memory - start_memory) / (1024 * 1024),
            'function_calls': [t for t in trace_data if t['event'] == 'call'],
            'return_values': [t for t in trace_data if t['event'] == 'return'],
            'call_graph': self._build_call_graph(trace_data),
            'performance_hotspots': self._identify_hotspots(trace_data),
            'result': str(result)[:200]  # Truncate for logging
        }
        
        return analysis_results
    
    def _build_call_graph(self, trace_data: List[Dict]) -> Dict[str, List[str]]:
        """Build call graph from trace data"""
        call_graph = defaultdict(list)
        call_stack = []
        
        for trace in trace_data:
            if trace['event'] == 'call':
                if call_stack:
                    caller = call_stack[-1]
                    callee = trace['function']
                    if callee not in call_graph[caller]:
                        call_graph[caller].append(callee)
                call_stack.append(trace['function'])
            elif trace['event'] == 'return' and call_stack:
                call_stack.pop()
        
        return dict(call_graph)
    
    def _identify_hotspots(self, trace_data: List[Dict]) -> List[Dict[str, Any]]:
        """Identify performance hotspots"""
        function_times = defaultdict(list)
        call_stack = []
        
        for trace in trace_data:
            if trace['event'] == 'call':
                call_stack.append({
                    'function': trace['function'],
                    'start_time': trace['timestamp']
                })
            elif trace['event'] == 'return' and call_stack:
                call_info = call_stack.pop()
                duration = trace['timestamp'] - call_info['start_time']
                function_times[call_info['function']].append(duration)
        
        # Calculate hotspots
        hotspots = []
        for func_name, times in function_times.items():
            total_time = sum(times)
            call_count = len(times)
            avg_time = total_time / call_count if call_count > 0 else 0
            
            if total_time > 0.001:  # More than 1ms total
                hotspots.append({
                    'function': func_name,
                    'total_time_ms': total_time * 1000,
                    'call_count': call_count,
                    'avg_time_ms': avg_time * 1000
                })
        
        return sorted(hotspots, key=lambda x: x['total_time_ms'], reverse=True)

class MemoryForensicsAnalyzer:
    """
    Memory forensics and leak detection
    Like memory analysis in reverse engineering
    """
    
    def __init__(self):
        self.object_tracker = ObjectTracker()
        self.reference_tracker = ReferenceTracker()
    
    def analyze_memory_usage(self) -> Dict[str, Any]:
        """Comprehensive memory usage analysis"""
        # Get current memory state
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Analyze object counts
        object_counts = {}
        for obj in gc.get_objects():
            obj_type = type(obj).__name__
            object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
        
        # Find large objects
        large_objects = []
        for obj in gc.get_objects():
            try:
                size = sys.getsizeof(obj)
                if size > 1024 * 1024:  # > 1MB
                    large_objects.append({
                        'type': type(obj).__name__,
                        'size_mb': size / (1024 * 1024),
                        'id': id(obj)
                    })
            except:
                pass  # Some objects can't be sized
        
        # Check for circular references
        circular_refs = []
        for obj in gc.garbage:
            circular_refs.append({
                'type': type(obj).__name__,
                'id': id(obj),
                'referrers_count': len(gc.get_referrers(obj))
            })
        
        return {
            'memory_usage_mb': memory_info.rss / (1024 * 1024),
            'virtual_memory_mb': memory_info.vms / (1024 * 1024),
            'object_counts': object_counts,
            'large_objects': sorted(large_objects, key=lambda x: x['size_mb'], reverse=True)[:10],
            'circular_references': circular_refs,
            'gc_stats': {
                'collections': gc.get_stats(),
                'garbage_count': len(gc.garbage)
            }
        }
    
    def detect_memory_leaks(self, baseline_snapshot: Optional[Dict] = None) -> Dict[str, Any]:
        """Detect memory leaks by comparing snapshots"""
        current_snapshot = self.analyze_memory_usage()
        
        if baseline_snapshot is None:
            return {
                'status': 'baseline_captured',
                'snapshot': current_snapshot
            }
        
        # Compare snapshots
        memory_delta = current_snapshot['memory_usage_mb'] - baseline_snapshot['memory_usage_mb']
        
        # Find objects that increased significantly
        object_deltas = {}
        current_objects = current_snapshot['object_counts']
        baseline_objects = baseline_snapshot['object_counts']
        
        for obj_type, current_count in current_objects.items():
            baseline_count = baseline_objects.get(obj_type, 0)
            delta = current_count - baseline_count
            if delta > 100:  # More than 100 new objects
                object_deltas[obj_type] = {
                    'baseline_count': baseline_count,
                    'current_count': current_count,
                    'delta': delta,
                    'growth_rate': delta / max(baseline_count, 1)
                }
        
        return {
            'status': 'leak_analysis_complete',
            'memory_delta_mb': memory_delta,
            'potential_leaks': object_deltas,
            'leak_detected': memory_delta > 10 or len(object_deltas) > 0,
            'recommendations': self._generate_memory_recommendations(memory_delta, object_deltas)
        }
    
    def _generate_memory_recommendations(self, memory_delta: float, object_deltas: Dict) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        if memory_delta > 50:  # > 50MB growth
            recommendations.append('Significant memory growth detected - investigate large allocations')
        
        for obj_type, delta_info in object_deltas.items():
            if delta_info['growth_rate'] > 10:  # 10x growth
                recommendations.append(f'Investigate {obj_type} object growth - possible leak')
        
        if not recommendations:
            recommendations.append('Memory usage appears stable')
        
        return recommendations

class SystemDependencyMapper:
    """
    System dependency analysis and mapping
    Like dependency analysis in reverse engineering
    """
    
    def __init__(self):
        self.import_analyzer = ImportAnalyzer()
        self.call_analyzer = CallAnalyzer()
        self.data_flow_analyzer = DataFlowAnalyzer()
    
    def map_system_dependencies(self, codebase_path: str) -> Dict[str, Any]:
        """Map all dependencies in the system"""
        import os
        import importlib.util
        
        dependencies = {
            'modules': {},
            'imports': defaultdict(list),
            'call_dependencies': defaultdict(list),
            'data_dependencies': defaultdict(list)
        }
        
        # Walk through all Python files
        for root, dirs, files in os.walk(codebase_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    module_name = file[:-3]  # Remove .py
                    
                    try:
                        # Read and analyze file
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        tree = ast.parse(content)
                        
                        # Analyze imports
                        imports = self._extract_imports(tree)
                        dependencies['imports'][module_name] = imports
                        
                        # Analyze function calls
                        calls = self._extract_function_calls(tree)
                        dependencies['call_dependencies'][module_name] = calls
                        
                        # Store module info
                        dependencies['modules'][module_name] = {
                            'path': file_path,
                            'functions': self._extract_functions(tree),
                            'classes': self._extract_classes(tree),
                            'complexity': self._calculate_module_complexity(tree)
                        }
                        
                    except Exception as e:
                        logger.warning(f"Could not analyze {file_path}: {e}")
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(dependencies)
        
        return {
            'dependencies': dependencies,
            'dependency_graph': dependency_graph,
            'circular_dependencies': self._find_circular_dependencies(dependency_graph),
            'dependency_metrics': self._calculate_dependency_metrics(dependency_graph)
        }
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        
        return imports
    
    def _extract_function_calls(self, tree: ast.AST) -> List[str]:
        """Extract function calls"""
        calls = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.append(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        calls.append(f"{node.func.value.id}.{node.func.attr}")
        
        return list(set(calls))
    
    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """Extract function definitions"""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        
        return functions
    
    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """Extract class definitions"""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        
        return classes
    
    def _calculate_module_complexity(self, tree: ast.AST) -> int:
        """Calculate module complexity score"""
        complexity = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                complexity += 1
            elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                complexity += 2
        
        return complexity
    
    def _build_dependency_graph(self, dependencies: Dict) -> Dict[str, List[str]]:
        """Build dependency graph"""
        graph = defaultdict(list)
        
        for module, imports in dependencies['imports'].items():
            for imported in imports:
                # Simplify module names
                base_import = imported.split('.')[0]
                if base_import in dependencies['modules']:
                    graph[module].append(base_import)
        
        return dict(graph)
    
    def _find_circular_dependencies(self, graph: Dict[str, List[str]]) -> List[List[str]]:
        """Find circular dependencies using DFS"""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path[:])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def _calculate_dependency_metrics(self, graph: Dict[str, List[str]]) -> Dict[str, Any]:
        """Calculate dependency metrics"""
        # Calculate in-degree and out-degree
        in_degree = defaultdict(int)
        out_degree = defaultdict(int)
        
        for node, neighbors in graph.items():
            out_degree[node] = len(neighbors)
            for neighbor in neighbors:
                in_degree[neighbor] += 1
        
        # Find hub nodes
        high_in_degree = [(node, degree) for node, degree in in_degree.items() if degree > 5]
        high_out_degree = [(node, degree) for node, degree in out_degree.items() if degree > 5]
        
        return {
            'total_modules': len(graph),
            'total_dependencies': sum(len(deps) for deps in graph.values()),
            'high_dependency_modules': high_in_degree,
            'high_coupling_modules': high_out_degree,
            'average_dependencies_per_module': sum(len(deps) for deps in graph.values()) / max(len(graph), 1)
        }

# Helper classes for organization
class ASTAnalyzer:
    """AST-based analysis"""
    
    def analyze_ast(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze AST structure"""
        node_counts = defaultdict(int)
        for node in ast.walk(tree):
            node_counts[type(node).__name__] += 1
        
        return {
            'node_counts': dict(node_counts),
            'total_nodes': sum(node_counts.values())
        }

class BytecodeAnalyzer:
    """Bytecode analysis"""
    pass

class PatternMatcher:
    """Pattern matching in code"""
    
    def find_patterns(self, tree: ast.AST) -> List[str]:
        """Find code patterns"""
        patterns = []
        
        # Look for common patterns
        for node in ast.walk(tree):
            if isinstance(node, ast.ListComp):
                patterns.append('list_comprehension')
            elif isinstance(node, ast.DictComp):
                patterns.append('dict_comprehension')
        
        return list(set(patterns))

class ComplexityCalculator:
    """Complexity calculation"""
    
    def calculate_complexity(self, tree: ast.AST) -> Dict[str, int]:
        """Calculate various complexity metrics"""
        cyclomatic = 1  # Base complexity
        cognitive = 0
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For)):
                cyclomatic += 1
                cognitive += 1
            elif isinstance(node, ast.Try):
                cyclomatic += 1
                cognitive += 1
            elif isinstance(node, ast.ExceptHandler):
                cyclomatic += 1
        
        return {
            'cyclomatic_complexity': cyclomatic,
            'cognitive_complexity': cognitive
        }

# Additional helper classes would be implemented similarly...
class ExecutionTracer:
    """Execution tracing"""
    pass

class MemoryMonitor:
    """Memory monitoring"""
    pass

class PerformanceProfiler:
    """Performance profiling"""
    pass

class ObjectTracker:
    """Object tracking"""
    pass

class ReferenceTracker:
    """Reference tracking"""
    pass

class ImportAnalyzer:
    """Import analysis"""
    pass

class CallAnalyzer:
    """Call analysis"""
    pass

class DataFlowAnalyzer:
    """Data flow analysis"""
    pass

# Main analyzer class that orchestrates everything
class ReverseEngineeringAnalyzer:
    """
    Main reverse engineering analyzer that orchestrates all analysis types
    """
    
    def __init__(self):
        self.static_analyzer = StaticCodeAnalyzer()
        self.dynamic_analyzer = DynamicRuntimeAnalyzer()
        self.memory_analyzer = MemoryForensicsAnalyzer()
        self.dependency_mapper = SystemDependencyMapper()
    
    async def analyze_complete_system(self, system_path: str) -> Dict[str, Any]:
        """Comprehensive analysis of the entire system"""
        logger.info("Starting comprehensive reverse engineering analysis...")
        
        analysis_results = {
            'analysis_timestamp': time.time(),
            'system_path': system_path,
            'static_analysis': {},
            'dependency_analysis': {},
            'memory_analysis': {},
            'security_analysis': {},
            'performance_predictions': {},
            'optimization_recommendations': []
        }
        
        try:
            # 1. Static analysis of entire codebase
            logger.info("Performing static analysis...")
            dependency_mapping = self.dependency_mapper.map_system_dependencies(system_path)
            analysis_results['dependency_analysis'] = dependency_mapping
            
            # 2. Memory forensics
            logger.info("Analyzing memory usage...")
            memory_analysis = self.memory_analyzer.analyze_memory_usage()
            analysis_results['memory_analysis'] = memory_analysis
            
            # 3. Security analysis
            logger.info("Performing security analysis...")
            security_issues = []
            
            # Walk through all Python files for security analysis
            import os
            for root, dirs, files in os.walk(system_path):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            tree = ast.parse(content)
                            file_security = self.static_analyzer._security_analysis(tree)
                            security_issues.extend(file_security)
                            
                        except Exception as e:
                            logger.warning(f"Could not analyze security for {file_path}: {e}")
            
            analysis_results['security_analysis'] = security_issues
            
            # 4. Generate optimization recommendations
            logger.info("Generating optimization recommendations...")
            recommendations = self._generate_system_recommendations(analysis_results)
            analysis_results['optimization_recommendations'] = recommendations
            
            logger.info("Reverse engineering analysis complete!")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            analysis_results['error'] = str(e)
            return analysis_results
    
    def _generate_system_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate system-wide optimization recommendations"""
        recommendations = []
        
        # Memory recommendations
        memory_usage = analysis['memory_analysis']['memory_usage_mb']
        if memory_usage > 500:  # > 500MB
            recommendations.append({
                'category': 'memory',
                'priority': 'high',
                'title': 'High Memory Usage Detected',
                'description': f'System using {memory_usage:.1f}MB - investigate large objects',
                'impact': 'performance'
            })
        
        # Dependency recommendations
        circular_deps = analysis['dependency_analysis'].get('circular_dependencies', [])
        if circular_deps:
            recommendations.append({
                'category': 'architecture',
                'priority': 'medium',
                'title': 'Circular Dependencies Detected',
                'description': f'Found {len(circular_deps)} circular dependencies',
                'impact': 'maintainability'
            })
        
        # Security recommendations
        security_issues = analysis['security_analysis']
        critical_issues = [issue for issue in security_issues if issue.severity == 'critical']
        if critical_issues:
            recommendations.append({
                'category': 'security',
                'priority': 'critical',
                'title': 'Critical Security Vulnerabilities',
                'description': f'Found {len(critical_issues)} critical security issues',
                'impact': 'security'
            })
        
        return recommendations

# Convenience function for easy use
async def analyze_superinstance_system(system_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze the entire SuperInstance system
    """
    analyzer = ReverseEngineeringAnalyzer()
    return await analyzer.analyze_complete_system(system_path)

if __name__ == "__main__":
    # Example usage
    import sys
    
    async def main():
        if len(sys.argv) > 1:
            system_path = sys.argv[1]
        else:
            system_path = "/home/activeloguser/activelog/services/dmlog-beta-portal"
        
        print(f"Analyzing SuperInstance system at: {system_path}")
        results = await analyze_superinstance_system(system_path)
        
        print("\n🔍 Analysis Results Summary:")
        print(f"📊 Total modules: {results['dependency_analysis']['dependency_metrics']['total_modules']}")
        print(f"💾 Memory usage: {results['memory_analysis']['memory_usage_mb']:.1f}MB")
        print(f"🛡️ Security issues: {len(results['security_analysis'])}")
        print(f"📈 Optimization recommendations: {len(results['optimization_recommendations'])}")
        
        # Save detailed results
        with open('superinstance_analysis_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print("\n💾 Detailed results saved to: superinstance_analysis_results.json")
    
    asyncio.run(main())