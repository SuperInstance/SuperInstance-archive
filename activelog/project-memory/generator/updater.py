#!/usr/bin/env python3
"""
Documentation Updater

Automatically updates project memory based on code changes.
Generates missing documentation and maintains consistency.
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass

from scanner import CodeScanner, CodeChange

@dataclass
class UpdateTask:
    concept_id: str
    priority: str  # 'high', 'medium', 'low'
    task_type: str  # 'create', 'update', 'verify'
    reason: str
    files_affected: List[str]
    estimated_effort: str  # 'low', 'medium', 'high'

class DocumentationUpdater:
    """Updates project memory documentation automatically."""
    
    def __init__(self, project_path: str, memory_path: str):
        self.project_path = Path(project_path)
        self.memory_path = Path(memory_path)
        self.knowledge_path = self.memory_path / "knowledge"
        
        self.scanner = CodeScanner(project_path, memory_path)
        
        # Load existing concepts
        self.existing_concepts = self._load_existing_concepts()
        
        # Templates for new documentation
        self.doc_templates = self._load_doc_templates()
    
    def _load_existing_concepts(self) -> Set[str]:
        """Load list of existing concept IDs."""
        concepts = set()
        
        # Read from index
        index_file = self.knowledge_path / "index.md"
        if index_file.exists():
            with open(index_file, 'r') as f:
                for line in f:
                    if line.startswith('**') and '**' in line[2:]:
                        concept_id = line[2:].split('**')[0]
                        concepts.add(concept_id)
        
        return concepts
    
    def _load_doc_templates(self) -> Dict[str, str]:
        """Load documentation templates."""
        return {
            "service": """# {concept_id}: {title}

**Type:** Service  
**Complexity:** {complexity}  
**Dependencies:** {dependencies}  
**Last Updated:** {timestamp}  

## Simple View (50 tokens)
{simple_description}

## Advanced View (200 tokens)
{advanced_description}

## Full Documentation

### Purpose
{purpose_description}

### Key Features
{key_features}

### API Endpoints
{api_endpoints}

### Configuration
{configuration}

## Code References
{code_references}

## Related Concepts
{related_concepts}
""",
            
            "component": """# {concept_id}: {title}

**Type:** Component  
**Complexity:** {complexity}  
**Dependencies:** {dependencies}  
**Last Updated:** {timestamp}  

## Simple View (50 tokens)
{simple_description}

## Advanced View (200 tokens)
{advanced_description}

## Full Documentation

### Overview
{overview}

### Implementation
{implementation_details}

### Usage Patterns
{usage_patterns}

## Code References
{code_references}

## Related Concepts
{related_concepts}
""",
            
            "pattern": """# {concept_id}: {title}

**Type:** Pattern  
**Complexity:** {complexity}  
**Dependencies:** {dependencies}  
**Last Updated:** {timestamp}  

## Simple View (50 tokens)
{simple_description}

## Advanced View (200 tokens)
{advanced_description}

## Full Documentation

### Pattern Description
{pattern_description}

### When to Use
{when_to_use}

### Implementation
{implementation_guide}

### Examples
{examples}

## Related Concepts
{related_concepts}
"""
        }
    
    def analyze_update_needs(self, changes: List[CodeChange]) -> List[UpdateTask]:
        """Analyze code changes and determine documentation update needs."""
        tasks = []
        
        # Get impact report
        impact_report = self.scanner.get_concept_impact_report(changes)
        
        for concept_id, impact in impact_report.items():
            change_types = impact["change_types"]
            files_changed = impact["files_changed"]
            total_changes = impact["total_changes"]
            
            # Determine priority based on change impact
            if "deleted" in change_types:
                priority = "high"
                task_type = "verify"
                reason = f"Files deleted affecting {concept_id}"
                effort = "medium"
            elif concept_id not in self.existing_concepts:
                priority = "medium"
                task_type = "create"
                reason = f"New concept {concept_id} identified from new files"
                effort = "high"
            elif total_changes >= 5:
                priority = "high"
                task_type = "update"
                reason = f"Major changes ({total_changes} files) affecting {concept_id}"
                effort = "medium"
            elif "added" in change_types:
                priority = "medium"
                task_type = "update"
                reason = f"New functionality added to {concept_id}"
                effort = "low"
            else:
                priority = "low"
                task_type = "verify"
                reason = f"Minor changes to {concept_id}"
                effort = "low"
            
            task = UpdateTask(
                concept_id=concept_id,
                priority=priority,
                task_type=task_type,
                reason=reason,
                files_affected=files_changed,
                estimated_effort=effort
            )
            tasks.append(task)
        
        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks.sort(key=lambda t: priority_order[t.priority])
        
        return tasks
    
    def generate_concept_content(self, concept_id: str, files_affected: List[str]) -> Dict[str, str]:
        """Generate documentation content for a concept."""
        
        # Analyze the files to understand the concept
        analysis = self._analyze_concept_files(concept_id, files_affected)
        
        # Determine concept type
        concept_type = self._determine_concept_type(concept_id, files_affected)
        
        # Select appropriate template
        template = self.doc_templates.get(concept_type, self.doc_templates["component"])
        
        # Generate content sections
        content_sections = {
            "concept_id": concept_id,
            "title": analysis["title"],
            "complexity": analysis["complexity"],
            "dependencies": ", ".join(analysis["dependencies"]),
            "timestamp": datetime.now().strftime("%Y-%m-%d"),
            "simple_description": analysis["simple_description"],
            "advanced_description": analysis["advanced_description"],
            "purpose_description": analysis.get("purpose", ""),
            "key_features": analysis.get("key_features", ""),
            "api_endpoints": analysis.get("api_endpoints", ""),
            "configuration": analysis.get("configuration", ""),
            "overview": analysis.get("overview", ""),
            "implementation_details": analysis.get("implementation", ""),
            "usage_patterns": analysis.get("usage_patterns", ""),
            "pattern_description": analysis.get("pattern_description", ""),
            "when_to_use": analysis.get("when_to_use", ""),
            "implementation_guide": analysis.get("implementation_guide", ""),
            "examples": analysis.get("examples", ""),
            "code_references": self._format_code_references(files_affected),
            "related_concepts": ", ".join(analysis["related_concepts"])
        }
        
        # Generate final content
        full_content = template.format(**content_sections)
        
        return {
            "full_content": full_content,
            "simple_view": content_sections["simple_description"],
            "advanced_view": content_sections["advanced_description"]
        }
    
    def _analyze_concept_files(self, concept_id: str, files: List[str]) -> Dict:
        """Analyze files to extract concept information."""
        
        analysis = {
            "title": self._generate_title(concept_id, files),
            "complexity": self._assess_complexity(files),
            "dependencies": self._find_dependencies(concept_id),
            "simple_description": self._generate_simple_description(concept_id, files),
            "advanced_description": self._generate_advanced_description(concept_id, files),
            "related_concepts": self._find_related_concepts(concept_id)
        }
        
        # Add type-specific analysis
        if concept_id.startswith("SVC-") or "/services/" in str(files):
            analysis.update(self._analyze_service_files(files))
        elif concept_id.startswith("FE-") or "frontend" in str(files):
            analysis.update(self._analyze_frontend_files(files))
        elif concept_id.startswith("AUTH-"):
            analysis.update(self._analyze_auth_files(files))
        
        return analysis
    
    def _generate_title(self, concept_id: str, files: List[str]) -> str:
        """Generate human-readable title for concept."""
        # Extract from concept ID
        if concept_id.startswith("CORE-"):
            return "Core System Component"
        elif concept_id.startswith("AUTH-"):
            return "Authentication System"
        elif concept_id.startswith("SVC-"):
            return "Service Component"
        elif concept_id.startswith("FE-"):
            return "Frontend Component"
        elif concept_id.startswith("DB-"):
            return "Database Component"
        elif concept_id.startswith("AI-"):
            return "AI/ML Component"
        
        # Try to extract from file paths
        for file_path in files:
            if "/services/" in file_path:
                service_name = file_path.split("/services/")[1].split("/")[0]
                return f"{service_name.replace('-', ' ').title()} Service"
        
        return f"System Component {concept_id}"
    
    def _assess_complexity(self, files: List[str]) -> str:
        """Assess complexity based on file analysis."""
        total_files = len(files)
        
        # Check for complex patterns
        has_ml = any("ml" in f.lower() or "ai" in f.lower() for f in files)
        has_auth = any("auth" in f.lower() or "jwt" in f.lower() for f in files)
        has_db = any("database" in f.lower() or "db" in f.lower() for f in files)
        
        if has_ml or total_files > 10:
            return "High"
        elif has_auth or has_db or total_files > 5:
            return "Medium"
        else:
            return "Low"
    
    def _find_dependencies(self, concept_id: str) -> List[str]:
        """Find concept dependencies."""
        # Load manifest to get existing dependencies
        manifest_file = self.memory_path / "context" / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
                concept_info = manifest.get("concepts", {}).get(concept_id, {})
                return concept_info.get("dependencies", [])
        
        # Infer common dependencies
        if concept_id.startswith("AUTH-"):
            return ["CORE-001", "SEC-001"]
        elif concept_id.startswith("SVC-"):
            return ["CORE-001"]
        elif concept_id.startswith("FE-"):
            return ["CORE-001", "API-001"]
        
        return []
    
    def _generate_simple_description(self, concept_id: str, files: List[str]) -> str:
        """Generate simple description (50 tokens max)."""
        
        # Service descriptions
        if concept_id.startswith("SVC-"):
            service_name = self._extract_service_name(files)
            return f"{service_name} service providing core functionality via FastAPI endpoints."
        
        # Auth descriptions
        elif concept_id.startswith("AUTH-"):
            return "Authentication and authorization system with JWT tokens and security middleware."
        
        # Frontend descriptions
        elif concept_id.startswith("FE-"):
            return "React-based frontend application with components and state management."
        
        # Default
        return f"System component {concept_id} with associated files and functionality."
    
    def _generate_advanced_description(self, concept_id: str, files: List[str]) -> str:
        """Generate advanced description (200 tokens max)."""
        
        file_count = len(files)
        main_files = [f for f in files if "main.py" in f or "index" in f]
        
        description = f"Component {concept_id} consists of {file_count} files including "
        
        if main_files:
            description += f"main entry point ({main_files[0]}) and supporting modules. "
        
        # Add functionality hints based on file patterns
        patterns = []
        if any("auth" in f.lower() for f in files):
            patterns.append("authentication")
        if any("api" in f.lower() for f in files):
            patterns.append("API endpoints")
        if any("db" in f.lower() or "model" in f.lower() for f in files):
            patterns.append("database models")
        if any("test" in f.lower() for f in files):
            patterns.append("test coverage")
        
        if patterns:
            description += f"Implements {', '.join(patterns)}. "
        
        description += "Integrates with project architecture via standardized patterns."
        
        return description
    
    def _find_related_concepts(self, concept_id: str) -> List[str]:
        """Find related concepts."""
        related = []
        
        # Common relationships
        if concept_id.startswith("AUTH-"):
            related.extend(["CORE-001", "SEC-001", "API-001"])
        elif concept_id.startswith("SVC-"):
            related.extend(["CORE-001", "AUTH-001", "API-001"])
        elif concept_id.startswith("FE-"):
            related.extend(["CORE-001", "API-001", "AUTH-001"])
        
        return related
    
    def _analyze_service_files(self, files: List[str]) -> Dict:
        """Analyze service-specific files."""
        analysis = {}
        
        # Look for main.py to extract endpoints
        main_files = [f for f in files if f.endswith("main.py")]
        if main_files:
            endpoints = self._extract_api_endpoints(main_files[0])
            analysis["api_endpoints"] = "\n".join([f"- {ep}" for ep in endpoints])
        
        # Look for configuration
        config_files = [f for f in files if "config" in f.lower() or "settings" in f.lower()]
        if config_files:
            analysis["configuration"] = f"Configuration managed in: {', '.join(config_files)}"
        
        return analysis
    
    def _extract_api_endpoints(self, main_file: str) -> List[str]:
        """Extract API endpoints from main.py file."""
        endpoints = []
        full_path = self.project_path / main_file
        
        if not full_path.exists():
            return endpoints
        
        try:
            with open(full_path, 'r') as f:
                content = f.read()
            
            # Find FastAPI route decorators
            import re
            patterns = [
                r'@app\.(get|post|put|delete|patch)\(["\'](.*?)["\']',
                r'@router\.(get|post|put|delete|patch)\(["\'](.*?)["\']'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for method, path in matches:
                    endpoints.append(f"{method.upper()} {path}")
        
        except Exception:
            pass
        
        return endpoints
    
    def _analyze_frontend_files(self, files: List[str]) -> Dict:
        """Analyze frontend-specific files."""
        analysis = {}
        
        # Count components
        component_files = [f for f in files if f.endswith(('.jsx', '.tsx')) and 'component' in f.lower()]
        if component_files:
            analysis["key_features"] = f"Contains {len(component_files)} React components"
        
        return analysis
    
    def _analyze_auth_files(self, files: List[str]) -> Dict:
        """Analyze authentication-specific files."""
        analysis = {}
        
        features = []
        for file in files:
            file_lower = file.lower()
            if "jwt" in file_lower:
                features.append("JWT token management")
            if "2fa" in file_lower or "totp" in file_lower:
                features.append("Two-factor authentication")
            if "middleware" in file_lower:
                features.append("Authentication middleware")
        
        if features:
            analysis["key_features"] = "\n".join([f"- {feature}" for feature in features])
        
        return analysis
    
    def _determine_concept_type(self, concept_id: str, files: List[str]) -> str:
        """Determine the type of concept for template selection."""
        if concept_id.startswith("SVC-") or any("/services/" in f for f in files):
            return "service"
        elif concept_id.startswith("PATTERN-") or concept_id.endswith("-PATTERN"):
            return "pattern"
        else:
            return "component"
    
    def _format_code_references(self, files: List[str]) -> str:
        """Format code references section."""
        references = []
        for file in sorted(files):
            references.append(f"- `{file}`")
        return "\n".join(references)
    
    def _extract_service_name(self, files: List[str]) -> str:
        """Extract service name from file paths."""
        for file in files:
            if "/services/" in file:
                parts = file.split("/services/")[1].split("/")
                if parts:
                    return parts[0].replace("-", " ").title()
        return "Unknown"
    
    def execute_update_task(self, task: UpdateTask) -> bool:
        """Execute a documentation update task."""
        try:
            if task.task_type == "create":
                return self._create_new_documentation(task)
            elif task.task_type == "update":
                return self._update_existing_documentation(task)
            elif task.task_type == "verify":
                return self._verify_documentation(task)
            
            return False
            
        except Exception as e:
            print(f"Error executing task for {task.concept_id}: {e}")
            return False
    
    def _create_new_documentation(self, task: UpdateTask) -> bool:
        """Create new documentation for a concept."""
        content = self.generate_concept_content(task.concept_id, task.files_affected)
        
        # Determine file path
        category = task.concept_id.split('-')[0].lower()
        doc_file = self.knowledge_path / category / f"{task.concept_id}.md"
        doc_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write documentation
        with open(doc_file, 'w') as f:
            f.write(content["full_content"])
        
        # Update index
        self._update_index(task.concept_id, content["simple_view"])
        
        print(f"Created documentation for {task.concept_id}")
        return True
    
    def _update_existing_documentation(self, task: UpdateTask) -> bool:
        """Update existing documentation."""
        # For now, regenerate the documentation
        return self._create_new_documentation(task)
    
    def _verify_documentation(self, task: UpdateTask) -> bool:
        """Verify documentation is still accurate."""
        # Check if documentation file exists
        category = task.concept_id.split('-')[0].lower()
        doc_file = self.knowledge_path / category / f"{task.concept_id}.md"
        
        if not doc_file.exists():
            print(f"Documentation missing for {task.concept_id}, creating...")
            return self._create_new_documentation(task)
        
        # Update timestamp
        with open(doc_file, 'r') as f:
            content = f.read()
        
        # Update last updated field
        updated_content = re.sub(
            r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}',
            f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}",
            content
        )
        
        if updated_content != content:
            with open(doc_file, 'w') as f:
                f.write(updated_content)
        
        return True
    
    def _update_index(self, concept_id: str, simple_description: str):
        """Update the main index with new concept."""
        index_file = self.knowledge_path / "index.md"
        
        if not index_file.exists():
            return
        
        # Read current index
        with open(index_file, 'r') as f:
            lines = f.readlines()
        
        # Find insertion point or update existing
        new_line = f"**{concept_id}** | {simple_description}\n"
        
        # Update existing or add new
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"**{concept_id}**"):
                lines[i] = new_line
                updated = True
                break
        
        if not updated:
            # Add to appropriate section
            lines.append(new_line)
        
        # Write back
        with open(index_file, 'w') as f:
            f.writelines(lines)


if __name__ == "__main__":
    # Example usage
    updater = DocumentationUpdater(
        project_path="/home/activeloguser/activelog",
        memory_path="/home/activeloguser/activelog/project-memory"
    )
    
    # Scan for changes
    changes = updater.scanner.scan_for_changes()
    print(f"Found {len(changes)} code changes")
    
    # Analyze update needs
    if changes:
        tasks = updater.analyze_update_needs(changes)
        print(f"\nGenerated {len(tasks)} update tasks:")
        
        for task in tasks[:5]:  # Show first 5
            print(f"  {task.priority}: {task.task_type} {task.concept_id}")
            print(f"    Reason: {task.reason}")
            print(f"    Files: {len(task.files_affected)}")
        
        # Execute high priority tasks
        high_priority = [t for t in tasks if t.priority == "high"]
        print(f"\nExecuting {len(high_priority)} high priority tasks...")
        
        for task in high_priority[:3]:  # Execute first 3
            success = updater.execute_update_task(task)
            print(f"  {task.concept_id}: {'✓' if success else '✗'}")