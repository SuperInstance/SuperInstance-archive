#!/usr/bin/env python3
"""
Project Memory Initializer

Scans an existing codebase and generates initial project memory structure.
Creates comprehensive knowledge graph and concept mappings.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple

from scanner import CodeScanner
from updater import DocumentationUpdater

class ProjectMemoryInitializer:
    """Initializes project memory for an existing codebase."""
    
    def __init__(self, project_path: str, memory_path: str):
        self.project_path = Path(project_path)
        self.memory_path = Path(memory_path)
        
        self.scanner = CodeScanner(str(project_path), str(memory_path))
        self.updater = DocumentationUpdater(str(project_path), str(memory_path))
        
        # Analysis results
        self.discovered_concepts = {}
        self.service_map = {}
        self.frontend_map = {}
        self.pattern_map = {}
    
    def analyze_project_structure(self) -> Dict:
        """Analyze project structure to discover concepts."""
        print("🔍 Analyzing project structure...")
        
        structure_analysis = {
            "services": self._analyze_services(),
            "frontends": self._analyze_frontends(), 
            "core_files": self._analyze_core_files(),
            "patterns": self._analyze_patterns(),
            "dependencies": self._analyze_dependencies()
        }
        
        return structure_analysis
    
    def _analyze_services(self) -> Dict:
        """Analyze services directory."""
        services = {}
        services_path = self.project_path / "services"
        
        if not services_path.exists():
            return services
        
        for service_dir in services_path.iterdir():
            if not service_dir.is_dir() or service_dir.name.startswith('.'):
                continue
            
            service_info = {
                "name": service_dir.name,
                "path": str(service_dir.relative_to(self.project_path)),
                "files": [],
                "endpoints": [],
                "models": [],
                "has_main": False,
                "has_tests": False,
                "concept_id": f"SVC-{len(services) + 10:03d}"
            }
            
            # Analyze service files
            for file_path in service_dir.rglob("*"):
                if file_path.is_file():
                    rel_path = str(file_path.relative_to(self.project_path))
                    service_info["files"].append(rel_path)
                    
                    if file_path.name == "main.py":
                        service_info["has_main"] = True
                        service_info["endpoints"] = self._extract_endpoints(file_path)
                    
                    if "test" in file_path.name.lower():
                        service_info["has_tests"] = True
                    
                    if "model" in file_path.name.lower():
                        service_info["models"].append(file_path.name)
            
            services[service_dir.name] = service_info
        
        return services
    
    def _analyze_frontends(self) -> Dict:
        """Analyze frontend directories."""
        frontends = {}
        
        frontend_patterns = ["frontend", "frontend-*", "ui", "web"]
        
        for pattern in frontend_patterns:
            for frontend_dir in self.project_path.glob(pattern):
                if not frontend_dir.is_dir():
                    continue
                
                frontend_info = {
                    "name": frontend_dir.name,
                    "path": str(frontend_dir.relative_to(self.project_path)),
                    "type": self._detect_frontend_type(frontend_dir),
                    "files": [],
                    "components": [],
                    "has_package_json": False,
                    "concept_id": f"FE-{len(frontends) + 10:03d}"
                }
                
                # Analyze frontend files
                for file_path in frontend_dir.rglob("*"):
                    if file_path.is_file():
                        rel_path = str(file_path.relative_to(self.project_path))
                        frontend_info["files"].append(rel_path)
                        
                        if file_path.name == "package.json":
                            frontend_info["has_package_json"] = True
                        
                        if file_path.suffix in ['.jsx', '.tsx', '.vue']:
                            frontend_info["components"].append(file_path.name)
                
                frontends[frontend_dir.name] = frontend_info
        
        return frontends
    
    def _analyze_core_files(self) -> Dict:
        """Analyze core project files."""
        core_files = {
            "docker_compose": [],
            "config_files": [],
            "scripts": [],
            "documentation": []
        }
        
        # Check for docker-compose files
        for compose_file in self.project_path.glob("docker-compose*.yml"):
            core_files["docker_compose"].append(str(compose_file.relative_to(self.project_path)))
        
        # Check for config files
        config_patterns = ["*.json", "*.yml", "*.yaml", "*.toml", "*.ini", ".env*"]
        for pattern in config_patterns:
            for config_file in self.project_path.glob(pattern):
                if config_file.is_file():
                    core_files["config_files"].append(str(config_file.relative_to(self.project_path)))
        
        # Check for scripts
        scripts_dir = self.project_path / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.rglob("*"):
                if script_file.is_file():
                    core_files["scripts"].append(str(script_file.relative_to(self.project_path)))
        
        # Check for documentation
        doc_patterns = ["*.md", "docs/**/*"]
        for pattern in doc_patterns:
            for doc_file in self.project_path.glob(pattern):
                if doc_file.is_file():
                    core_files["documentation"].append(str(doc_file.relative_to(self.project_path)))
        
        return core_files
    
    def _analyze_patterns(self) -> Dict:
        """Analyze common patterns in the codebase."""
        patterns = {
            "fastapi_services": [],
            "react_frontends": [],
            "database_services": [],
            "auth_implementations": [],
            "api_gateways": []
        }
        
        # Analyze services for patterns
        for service_name, service_info in self.service_map.items():
            if any("main.py" in f for f in service_info["files"]):
                patterns["fastapi_services"].append(service_name)
            
            if any("database" in f.lower() or "db" in f.lower() for f in service_info["files"]):
                patterns["database_services"].append(service_name)
            
            if any("auth" in f.lower() for f in service_info["files"]):
                patterns["auth_implementations"].append(service_name)
            
            if "api-gateway" in service_name or "gateway" in service_name:
                patterns["api_gateways"].append(service_name)
        
        # Analyze frontends for patterns
        for frontend_name, frontend_info in self.frontend_map.items():
            if frontend_info["type"] == "react":
                patterns["react_frontends"].append(frontend_name)
        
        return patterns
    
    def _analyze_dependencies(self) -> Dict:
        """Analyze project dependencies."""
        dependencies = {
            "python_packages": set(),
            "node_packages": set(),
            "system_dependencies": set()
        }
        
        # Python dependencies
        requirements_files = list(self.project_path.rglob("requirements*.txt"))
        for req_file in requirements_files:
            try:
                with open(req_file, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            package = line.strip().split('==')[0].split('>=')[0]
                            dependencies["python_packages"].add(package)
            except Exception:
                pass
        
        # Node dependencies
        package_json_files = list(self.project_path.rglob("package.json"))
        for pkg_file in package_json_files:
            try:
                with open(pkg_file, 'r') as f:
                    package_data = json.load(f)
                    for dep_type in ["dependencies", "devDependencies"]:
                        if dep_type in package_data:
                            dependencies["node_packages"].update(package_data[dep_type].keys())
            except Exception:
                pass
        
        # Convert sets to lists for JSON serialization
        for key in dependencies:
            dependencies[key] = list(dependencies[key])
        
        return dependencies
    
    def _extract_endpoints(self, main_file: Path) -> List[str]:
        """Extract API endpoints from main.py."""
        endpoints = []
        
        try:
            with open(main_file, 'r') as f:
                content = f.read()
            
            import re
            patterns = [
                r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for method, path in matches:
                    endpoints.append(f"{method.upper()} {path}")
        
        except Exception:
            pass
        
        return endpoints
    
    def _detect_frontend_type(self, frontend_dir: Path) -> str:
        """Detect frontend framework type."""
        package_json = frontend_dir / "package.json"
        
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    package_data = json.load(f)
                
                deps = {**package_data.get("dependencies", {}), **package_data.get("devDependencies", {})}
                
                if "react" in deps:
                    return "react"
                elif "vue" in deps:
                    return "vue"
                elif "angular" in deps:
                    return "angular"
                elif "svelte" in deps:
                    return "svelte"
            except Exception:
                pass
        
        # Check for framework-specific files
        if list(frontend_dir.rglob("*.jsx")) or list(frontend_dir.rglob("*.tsx")):
            return "react"
        elif list(frontend_dir.rglob("*.vue")):
            return "vue"
        
        return "unknown"
    
    def generate_concept_hierarchy(self, structure: Dict) -> Dict:
        """Generate concept hierarchy from structure analysis."""
        print("📝 Generating concept hierarchy...")
        
        concepts = {}
        concept_counter = {"CORE": 10, "SVC": 10, "FE": 10, "DB": 10, "AUTH": 10, "API": 10}
        
        # Core system concepts
        concepts["CORE-001"] = {
            "title": f"{self.project_path.name.title()} System",
            "type": "architecture",
            "complexity": "medium",
            "description": f"Multi-service ecosystem with {len(structure['services'])} services and {len(structure['frontends'])} frontends",
            "files": structure["core_files"]["config_files"][:5],
            "dependencies": [],
            "priority": "high"
        }
        
        # Service concepts
        for service_name, service_info in structure["services"].items():
            concept_id = service_info["concept_id"]
            concepts[concept_id] = {
                "title": f"{service_name.replace('-', ' ').title()} Service",
                "type": "service",
                "complexity": "medium" if service_info["has_main"] else "low",
                "description": f"Service with {len(service_info['files'])} files, {len(service_info['endpoints'])} endpoints",
                "files": service_info["files"][:10],
                "dependencies": ["CORE-001"],
                "priority": "medium"
            }
        
        # Frontend concepts
        for frontend_name, frontend_info in structure["frontends"].items():
            concept_id = frontend_info["concept_id"]
            concepts[concept_id] = {
                "title": f"{frontend_name.replace('-', ' ').title()} Frontend",
                "type": "frontend",
                "complexity": "medium",
                "description": f"{frontend_info['type'].title()} frontend with {len(frontend_info['components'])} components",
                "files": frontend_info["files"][:10],
                "dependencies": ["CORE-001", "API-001"],
                "priority": "medium"
            }
        
        # Pattern concepts
        if structure["patterns"]["fastapi_services"]:
            concepts["PATTERN-001"] = {
                "title": "FastAPI Service Pattern",
                "type": "pattern",
                "complexity": "low",
                "description": f"Standard FastAPI service pattern used in {len(structure['patterns']['fastapi_services'])} services",
                "files": [],
                "dependencies": ["CORE-001"],
                "priority": "low"
            }
        
        return concepts
    
    def create_initial_index(self, concepts: Dict) -> str:
        """Create initial knowledge index."""
        print("📚 Creating knowledge index...")
        
        index_content = """# Project Knowledge Index

**Format:** Each line = one concept (max 255 chars) with unique ID  
**Generated:** Auto-generated from project analysis  
**Coverage:** Core concepts, services, patterns  

## Core Architecture

"""
        
        # Add core concepts
        for concept_id, concept_info in concepts.items():
            if concept_info["type"] in ["architecture", "core"]:
                line = f"**{concept_id}** | {concept_info['title']}: {concept_info['description']}"
                if len(line) > 255:
                    line = line[:252] + "..."
                index_content += line + "\n"
        
        index_content += "\n## Services\n\n"
        
        # Add service concepts
        for concept_id, concept_info in concepts.items():
            if concept_info["type"] == "service":
                line = f"**{concept_id}** | {concept_info['title']}: {concept_info['description']}"
                if len(line) > 255:
                    line = line[:252] + "..."
                index_content += line + "\n"
        
        index_content += "\n## Frontend Systems\n\n"
        
        # Add frontend concepts
        for concept_id, concept_info in concepts.items():
            if concept_info["type"] == "frontend":
                line = f"**{concept_id}** | {concept_info['title']}: {concept_info['description']}"
                if len(line) > 255:
                    line = line[:252] + "..."
                index_content += line + "\n"
        
        index_content += "\n## Patterns\n\n"
        
        # Add pattern concepts
        for concept_id, concept_info in concepts.items():
            if concept_info["type"] == "pattern":
                line = f"**{concept_id}** | {concept_info['title']}: {concept_info['description']}"
                if len(line) > 255:
                    line = line[:252] + "..."
                index_content += line + "\n"
        
        return index_content
    
    def create_initial_manifest(self, concepts: Dict) -> Dict:
        """Create initial context manifest."""
        print("🗂️  Creating context manifest...")
        
        manifest = {
            "version": "1.0.0",
            "last_updated": "2025-08-26T12:00:00Z",
            "concepts": {},
            "aliases": {},
            "patterns": {
                "fastapi-service": {
                    "template": "PATTERN-001",
                    "examples": list(self.service_map.keys())[:5],
                    "token_cost": 100
                }
            },
            "optimization": {
                "max_context_tokens": 8000,
                "target_utilization": 0.7,
                "compression_ratio": 0.8,
                "cache_hit_rate": 0.85
            },
            "usage_stats": {
                "queries_today": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "avg_tokens_per_query": 0
            }
        }
        
        # Add concept information
        for concept_id, concept_info in concepts.items():
            manifest["concepts"][concept_id] = {
                "type": concept_info["type"],
                "complexity": concept_info["complexity"],
                "token_count": len(concept_info["description"]) * 2,  # Rough estimate
                "dependencies": concept_info["dependencies"],
                "dependents": [],
                "tags": [concept_info["type"], concept_id.split('-')[0].lower()],
                "priority": concept_info["priority"],
                "views": {
                    "simple": 50,
                    "advanced": 200,
                    "full": len(concept_info["description"]) * 2
                }
            }
        
        # Calculate dependents
        for concept_id, concept_info in manifest["concepts"].items():
            for dep_id in concept_info["dependencies"]:
                if dep_id in manifest["concepts"]:
                    manifest["concepts"][dep_id]["dependents"].append(concept_id)
        
        return manifest
    
    def initialize_project_memory(self) -> bool:
        """Initialize complete project memory system."""
        print(f"🚀 Initializing project memory for {self.project_path.name}")
        print(f"📁 Memory location: {self.memory_path}")
        
        try:
            # Ensure memory directory structure exists
            self.memory_path.mkdir(parents=True, exist_ok=True)
            (self.memory_path / "knowledge").mkdir(exist_ok=True)
            (self.memory_path / "context").mkdir(exist_ok=True)
            (self.memory_path / "cache").mkdir(exist_ok=True)
            (self.memory_path / "views").mkdir(exist_ok=True)
            (self.memory_path / "generator").mkdir(exist_ok=True)
            
            # Analyze project structure
            structure = self.analyze_project_structure()
            self.service_map = structure["services"]
            self.frontend_map = structure["frontends"]
            self.pattern_map = structure["patterns"]
            
            # Generate concepts
            concepts = self.generate_concept_hierarchy(structure)
            
            # Create knowledge index
            index_content = self.create_initial_index(concepts)
            with open(self.memory_path / "knowledge" / "index.md", 'w') as f:
                f.write(index_content)
            
            # Create context manifest
            manifest = self.create_initial_manifest(concepts)
            with open(self.memory_path / "context" / "manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Generate detailed documentation for key concepts
            print("📄 Generating detailed documentation...")
            key_concepts = [concept_id for concept_id, info in concepts.items() 
                          if info["priority"] == "high"]
            
            for concept_id in key_concepts[:5]:  # Limit initial generation
                concept_info = concepts[concept_id]
                content = self.updater.generate_concept_content(
                    concept_id, concept_info["files"]
                )
                
                # Save to appropriate directory
                category = concept_id.split('-')[0].lower()
                category_dir = self.memory_path / "knowledge" / category
                category_dir.mkdir(exist_ok=True)
                
                with open(category_dir / f"{concept_id}.md", 'w') as f:
                    f.write(content["full_content"])
            
            # Initial scan for baseline
            print("🔍 Performing initial code scan...")
            self.scanner.scan_for_changes()
            
            print("✅ Project memory initialization complete!")
            print(f"   Generated {len(concepts)} concepts")
            print(f"   Documented {len(key_concepts)} key concepts")
            print(f"   Analyzed {len(self.service_map)} services")
            print(f"   Analyzed {len(self.frontend_map)} frontends")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Initialize project memory system")
    parser.add_argument("project_path", help="Path to project root directory")
    parser.add_argument("--memory-path", help="Path to memory storage", 
                       default=None)
    parser.add_argument("--dry-run", action="store_true", 
                       help="Analyze only, don't create files")
    
    args = parser.parse_args()
    
    project_path = Path(args.project_path).resolve()
    if not project_path.exists():
        print(f"❌ Project path does not exist: {project_path}")
        sys.exit(1)
    
    memory_path = args.memory_path or str(project_path / "project-memory")
    
    print(f"🎯 Target project: {project_path}")
    print(f"🎯 Memory location: {memory_path}")
    
    if args.dry_run:
        print("🔍 Dry run mode - analyzing only...")
    
    initializer = ProjectMemoryInitializer(str(project_path), memory_path)
    
    if args.dry_run:
        structure = initializer.analyze_project_structure()
        concepts = initializer.generate_concept_hierarchy(structure)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Services: {len(structure['services'])}")
        print(f"   Frontends: {len(structure['frontends'])}")  
        print(f"   Concepts: {len(concepts)}")
        print(f"   Config files: {len(structure['core_files']['config_files'])}")
    else:
        success = initializer.initialize_project_memory()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()