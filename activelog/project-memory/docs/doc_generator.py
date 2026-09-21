"""
ActiveLog Project Memory - Dynamic Documentation Generator
Automated documentation generation with change tracking and bidirectional links
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import os
import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import ast
import inspect

class DocumentationType(Enum):
    """Types of documentation that can be generated"""
    API_REFERENCE = "api_reference"
    CODE_EXPLANATION = "code_explanation" 
    SYSTEM_OVERVIEW = "system_overview"
    INTEGRATION_GUIDE = "integration_guide"
    ARCHITECTURE_DOC = "architecture_doc"
    TROUBLESHOOTING = "troubleshooting"

@dataclass
class CodeChange:
    """Represents a change in the codebase"""
    file_path: str
    change_type: str  # added, modified, deleted
    timestamp: datetime
    content_hash: str
    affected_functions: List[str] = field(default_factory=list)
    affected_classes: List[str] = field(default_factory=list)

@dataclass
class DocumentationNode:
    """Represents a documentation node with bidirectional links"""
    node_id: str
    title: str
    content: str
    doc_type: DocumentationType
    source_files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_outdated: bool = False
    change_detection_hash: str = ""

class DynamicDocumentationGenerator:
    """
    Generates and maintains dynamic documentation with change tracking
    Creates bidirectional links between code and explanations
    """
    
    def __init__(self, project_root: str = "/home/activeloguser/activelog"):
        self.project_root = Path(project_root)
        self.docs_cache = {}
        self.change_tracker = {}
        self.bidirectional_links = {}
        self.outdated_docs = set()
        
        # Initialize documentation templates
        self.doc_templates = self._initialize_templates()
        
    def _initialize_templates(self) -> Dict[DocumentationType, Dict[str, str]]:
        """Initialize documentation templates for different types"""
        return {
            DocumentationType.API_REFERENCE: {
                "header": "# {service_name} API Reference\n\nGenerated: {timestamp}\n\n",
                "endpoint": "## {method} {path}\n\n{description}\n\n### Parameters\n{parameters}\n\n### Response\n{response}\n\n",
                "footer": "\n---\n*Auto-generated documentation - Last updated: {timestamp}*\n"
            },
            DocumentationType.CODE_EXPLANATION: {
                "header": "# Code Explanation: {module_name}\n\nGenerated: {timestamp}\n\n",
                "class": "## Class: {class_name}\n\n{description}\n\n### Methods\n{methods}\n\n",
                "function": "### {function_name}\n\n{description}\n\n```python\n{signature}\n```\n\n{details}\n\n",
                "footer": "\n---\n*Auto-generated from source code - Last updated: {timestamp}*\n"
            },
            DocumentationType.SYSTEM_OVERVIEW: {
                "header": "# System Overview: {system_name}\n\nGenerated: {timestamp}\n\n",
                "service": "## {service_name}\n\n**Port:** {port}\n**Status:** {status}\n\n{description}\n\n### Key Features\n{features}\n\n",
                "footer": "\n---\n*Auto-generated system overview - Last updated: {timestamp}*\n"
            }
        }
    
    def analyze_code_structure(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze Python file structure for documentation generation
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            structure = {
                "file_path": file_path,
                "classes": [],
                "functions": [],
                "imports": [],
                "docstring": ast.get_docstring(tree),
                "complexity_score": 0
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node),
                        "methods": [],
                        "line_number": node.lineno
                    }
                    
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append({
                                "name": item.name,
                                "docstring": ast.get_docstring(item),
                                "line_number": item.lineno,
                                "args": [arg.arg for arg in item.args.args]
                            })
                    
                    structure["classes"].append(class_info)
                
                elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                    # Only top-level functions
                    if node.col_offset == 0:
                        structure["functions"].append({
                            "name": node.name,
                            "docstring": ast.get_docstring(node),
                            "line_number": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "is_async": False
                        })
                
                elif isinstance(node, ast.AsyncFunctionDef):
                    if node.col_offset == 0:
                        structure["functions"].append({
                            "name": node.name,
                            "docstring": ast.get_docstring(node),
                            "line_number": node.lineno,
                            "args": [arg.arg for arg in node.args.args],
                            "is_async": True
                        })
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            structure["imports"].append({
                                "module": alias.name,
                                "alias": alias.asname,
                                "type": "import"
                            })
                    else:
                        module = node.module or ""
                        for alias in node.names:
                            structure["imports"].append({
                                "module": module,
                                "name": alias.name,
                                "alias": alias.asname,
                                "type": "from"
                            })
            
            # Calculate complexity score
            structure["complexity_score"] = self._calculate_code_complexity(structure)
            
            return structure
            
        except Exception as e:
            return {
                "file_path": file_path,
                "error": str(e),
                "classes": [],
                "functions": [],
                "imports": []
            }
    
    def _calculate_code_complexity(self, structure: Dict[str, Any]) -> int:
        """Calculate complexity score for code structure"""
        complexity = 0
        
        # Base complexity from classes and functions
        complexity += len(structure["classes"]) * 3
        complexity += len(structure["functions"]) * 2
        
        # Add complexity for methods
        for cls in structure["classes"]:
            complexity += len(cls["methods"]) * 1
        
        # Add complexity for imports (external dependencies)
        complexity += len(structure["imports"]) * 1
        
        return complexity
    
    def generate_api_documentation(self, service_path: str) -> DocumentationNode:
        """
        Generate API documentation for a service
        """
        main_py_path = os.path.join(service_path, "main.py")
        
        if not os.path.exists(main_py_path):
            return None
        
        structure = self.analyze_code_structure(main_py_path)
        service_name = os.path.basename(service_path)
        
        # Extract API endpoints from FastAPI routes
        endpoints = self._extract_fastapi_endpoints(main_py_path)
        
        content = self.doc_templates[DocumentationType.API_REFERENCE]["header"].format(
            service_name=service_name,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        for endpoint in endpoints:
            content += self.doc_templates[DocumentationType.API_REFERENCE]["endpoint"].format(
                method=endpoint["method"],
                path=endpoint["path"],
                description=endpoint["description"],
                parameters=endpoint["parameters"],
                response=endpoint["response"]
            )
        
        content += self.doc_templates[DocumentationType.API_REFERENCE]["footer"].format(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        node = DocumentationNode(
            node_id=f"api_{service_name}",
            title=f"{service_name} API Reference",
            content=content,
            doc_type=DocumentationType.API_REFERENCE,
            source_files=[main_py_path],
            change_detection_hash=self._calculate_file_hash(main_py_path)
        )
        
        return node
    
    def generate_code_explanation(self, file_path: str, 
                                 target_complexity: str = "advanced") -> DocumentationNode:
        """
        Generate detailed code explanation documentation
        """
        structure = self.analyze_code_structure(file_path)
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        content = self.doc_templates[DocumentationType.CODE_EXPLANATION]["header"].format(
            module_name=module_name,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        # Add module-level docstring
        if structure.get("docstring"):
            content += f"## Overview\n\n{structure['docstring']}\n\n"
        
        # Document classes
        for cls in structure["classes"]:
            methods_doc = ""
            for method in cls["methods"]:
                method_sig = f"def {method['name']}({', '.join(method['args'])})"
                method_desc = method.get("docstring", "No description available.")
                
                methods_doc += self.doc_templates[DocumentationType.CODE_EXPLANATION]["function"].format(
                    function_name=method["name"],
                    description=method_desc,
                    signature=method_sig,
                    details=f"Line {method['line_number']}"
                )
            
            class_desc = cls.get("docstring", "No description available.")
            content += self.doc_templates[DocumentationType.CODE_EXPLANATION]["class"].format(
                class_name=cls["name"],
                description=class_desc,
                methods=methods_doc
            )
        
        # Document top-level functions
        if structure["functions"]:
            content += "## Functions\n\n"
            for func in structure["functions"]:
                func_sig = f"{'async ' if func['is_async'] else ''}def {func['name']}({', '.join(func['args'])})"
                func_desc = func.get("docstring", "No description available.")
                
                content += self.doc_templates[DocumentationType.CODE_EXPLANATION]["function"].format(
                    function_name=func["name"],
                    description=func_desc,
                    signature=func_sig,
                    details=f"Line {func['line_number']}"
                )
        
        content += self.doc_templates[DocumentationType.CODE_EXPLANATION]["footer"].format(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        node = DocumentationNode(
            node_id=f"code_{module_name}",
            title=f"Code Explanation: {module_name}",
            content=content,
            doc_type=DocumentationType.CODE_EXPLANATION,
            source_files=[file_path],
            change_detection_hash=self._calculate_file_hash(file_path)
        )
        
        return node
    
    def generate_system_overview(self, services_info: Dict[str, Any]) -> DocumentationNode:
        """
        Generate comprehensive system overview documentation
        """
        content = self.doc_templates[DocumentationType.SYSTEM_OVERVIEW]["header"].format(
            system_name="ActiveLog Ecosystem",
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        content += "## Architecture Overview\n\n"
        content += "ActiveLog is a comprehensive AI-powered development ecosystem with 12 services across 5 phases:\n\n"
        
        # Group services by phase
        phases = {
            "Phase 1: Bot Orchestration": [],
            "Phase 2: LucidDreamer System": [],
            "Phase 3: Business Platforms": [],
            "Phase 4: Market Infrastructure": [],
            "Phase 5: Developer Tools": []
        }
        
        for service_name, info in services_info.items():
            phase = info.get("phase", "Unknown")
            service_doc = self.doc_templates[DocumentationType.SYSTEM_OVERVIEW]["service"].format(
                service_name=service_name,
                port=info.get("port", "Unknown"),
                status=info.get("status", "Unknown"),
                description=info.get("description", "No description available"),
                features="\n".join([f"- {feature}" for feature in info.get("features", [])])
            )
            
            if phase in phases:
                phases[phase].append(service_doc)
            else:
                phases["Unknown"] = phases.get("Unknown", [])
                phases["Unknown"].append(service_doc)
        
        # Add phase documentation
        for phase_name, phase_services in phases.items():
            if phase_services:
                content += f"## {phase_name}\n\n"
                content += "\n".join(phase_services)
                content += "\n"
        
        content += self.doc_templates[DocumentationType.SYSTEM_OVERVIEW]["footer"].format(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        
        node = DocumentationNode(
            node_id="system_overview",
            title="ActiveLog System Overview",
            content=content,
            doc_type=DocumentationType.SYSTEM_OVERVIEW,
            source_files=[],  # System-wide documentation
            change_detection_hash=hashlib.md5(str(services_info).encode()).hexdigest()
        )
        
        return node
    
    def _extract_fastapi_endpoints(self, file_path: str) -> List[Dict[str, str]]:
        """Extract FastAPI endpoints from Python file"""
        endpoints = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple regex-based extraction for FastAPI decorators
            patterns = [
                r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)\s*(?:async\s+)?def\s+(\w+)',
                r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\'].*?\)\s*(?:async\s+)?def\s+(\w+)'
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
                for match in matches:
                    method = match.group(1).upper()
                    path = match.group(2)
                    function_name = match.group(3)
                    
                    endpoints.append({
                        "method": method,
                        "path": path,
                        "function": function_name,
                        "description": f"Endpoint handled by {function_name}()",
                        "parameters": "To be documented",
                        "response": "To be documented"
                    })
            
        except Exception as e:
            pass
        
        return endpoints
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash for file content change detection"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except:
            return ""
    
    def track_changes(self, file_path: str) -> Optional[CodeChange]:
        """
        Track changes in a file and return change information
        """
        current_hash = self._calculate_file_hash(file_path)
        
        if file_path in self.change_tracker:
            previous_hash = self.change_tracker[file_path]["hash"]
            if current_hash != previous_hash:
                # File has changed
                change = CodeChange(
                    file_path=file_path,
                    change_type="modified",
                    timestamp=datetime.now(timezone.utc),
                    content_hash=current_hash
                )
                
                # Update tracker
                self.change_tracker[file_path] = {
                    "hash": current_hash,
                    "last_check": datetime.now(timezone.utc)
                }
                
                return change
        else:
            # New file
            self.change_tracker[file_path] = {
                "hash": current_hash,
                "last_check": datetime.now(timezone.utc)
            }
            
            return CodeChange(
                file_path=file_path,
                change_type="added",
                timestamp=datetime.now(timezone.utc),
                content_hash=current_hash
            )
        
        return None
    
    def detect_outdated_documentation(self) -> List[str]:
        """
        Detect documentation that needs updating based on source changes
        """
        outdated = []
        
        for doc_id, node in self.docs_cache.items():
            for source_file in node.source_files:
                if os.path.exists(source_file):
                    current_hash = self._calculate_file_hash(source_file)
                    if current_hash != node.change_detection_hash:
                        outdated.append(doc_id)
                        node.is_outdated = True
                        break
        
        return outdated
    
    def create_bidirectional_links(self, source_file: str, doc_node: DocumentationNode):
        """
        Create bidirectional links between source code and documentation
        """
        if source_file not in self.bidirectional_links:
            self.bidirectional_links[source_file] = []
        
        self.bidirectional_links[source_file].append(doc_node.node_id)
        
        # Add reverse link in documentation
        if doc_node.node_id not in self.bidirectional_links:
            self.bidirectional_links[doc_node.node_id] = []
        
        self.bidirectional_links[doc_node.node_id].append(source_file)
    
    def generate_all_documentation(self, force_regenerate: bool = False) -> Dict[str, DocumentationNode]:
        """
        Generate all documentation for the project
        """
        generated_docs = {}
        
        # Find all services
        services_root = self.project_root / "services"
        if services_root.exists():
            for service_dir in services_root.iterdir():
                if service_dir.is_dir():
                    # Generate API documentation
                    api_doc = self.generate_api_documentation(str(service_dir))
                    if api_doc:
                        generated_docs[api_doc.node_id] = api_doc
                        self.docs_cache[api_doc.node_id] = api_doc
                    
                    # Generate code explanations for main files
                    main_py = service_dir / "main.py"
                    if main_py.exists():
                        code_doc = self.generate_code_explanation(str(main_py))
                        generated_docs[code_doc.node_id] = code_doc
                        self.docs_cache[code_doc.node_id] = code_doc
                        
                        # Create bidirectional links
                        self.create_bidirectional_links(str(main_py), code_doc)
        
        return generated_docs
    
    def update_documentation(self, changed_files: List[str]) -> List[DocumentationNode]:
        """
        Update documentation for changed files
        """
        updated_docs = []
        
        for file_path in changed_files:
            # Find related documentation
            related_docs = self.bidirectional_links.get(file_path, [])
            
            for doc_id in related_docs:
                if doc_id in self.docs_cache:
                    node = self.docs_cache[doc_id]
                    
                    # Regenerate based on type
                    if node.doc_type == DocumentationType.CODE_EXPLANATION:
                        updated_node = self.generate_code_explanation(file_path)
                        self.docs_cache[doc_id] = updated_node
                        updated_docs.append(updated_node)
                    
                    elif node.doc_type == DocumentationType.API_REFERENCE:
                        service_path = os.path.dirname(file_path)
                        updated_node = self.generate_api_documentation(service_path)
                        if updated_node:
                            self.docs_cache[doc_id] = updated_node
                            updated_docs.append(updated_node)
        
        return updated_docs
    
    def export_documentation(self, output_dir: str, format: str = "markdown") -> Dict[str, str]:
        """
        Export generated documentation to files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        for doc_id, node in self.docs_cache.items():
            if format == "markdown":
                filename = f"{doc_id}.md"
                file_path = output_path / filename
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(node.content)
                
                exported_files[doc_id] = str(file_path)
        
        return exported_files