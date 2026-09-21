#!/usr/bin/env python3
"""
SuperInstance Knowledge Discovery API
=====================================

Comprehensive search and discovery system for all SuperInstance components, patterns, and documentation.
Part of the $2/month Lego-like software construction toolkit.

Features:
- Full-text search across all documentation and code
- Component compatibility lookup
- Pattern recognition and matching
- Educational content discovery
- Performance benchmarking data
- Integration guide generation
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import re

@dataclass
class ComponentInfo:
    """Information about a SuperInstance Lego component"""
    name: str
    path: str
    description: str
    technologies: List[str]
    interfaces: List[str]
    dependencies: List[str]
    deployment_targets: List[str]
    performance_metrics: Dict[str, Any]
    compatibility_tags: List[str]
    educational_content: List[str]
    last_updated: str

@dataclass
class SearchResult:
    """Search result with relevance scoring"""
    item_type: str  # 'component', 'pattern', 'documentation', 'tutorial'
    title: str
    description: str
    path: str
    relevance_score: float
    tags: List[str]
    related_items: List[str]

@dataclass
class KnowledgePattern:
    """Documented knowledge pattern from bot learning"""
    pattern_id: str
    name: str
    description: str
    use_cases: List[str]
    implementation_examples: List[str]
    performance_data: Dict[str, Any]
    related_components: List[str]
    difficulty_level: str
    educational_resources: List[str]

class SuperInstanceKnowledgeDiscovery:
    """
    Comprehensive knowledge discovery system for SuperInstance Lego components
    """
    
    def __init__(self, base_path: str = "/home/activeloguser/activelog"):
        self.base_path = Path(base_path)
        self.db_path = self.base_path / "knowledge_discovery.db"
        self.search_index = {}
        self.components = {}
        self.patterns = {}
        
        self._initialize_database()
        self._build_knowledge_index()
    
    def _initialize_database(self):
        """Initialize SQLite database for knowledge storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS components (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    path TEXT,
                    description TEXT,
                    technologies TEXT,
                    interfaces TEXT,
                    dependencies TEXT,
                    deployment_targets TEXT,
                    performance_metrics TEXT,
                    compatibility_tags TEXT,
                    educational_content TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    search_text TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    use_cases TEXT,
                    implementation_examples TEXT,
                    performance_data TEXT,
                    related_components TEXT,
                    difficulty_level TEXT,
                    educational_resources TEXT,
                    search_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documentation (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    path TEXT,
                    content TEXT,
                    doc_type TEXT,
                    tags TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create full-text search indices
            conn.execute('CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(content, type, tags, path)')
    
    def _build_knowledge_index(self):
        """Build comprehensive knowledge index from all available sources"""
        print("🔍 Building comprehensive knowledge discovery index...")
        
        # Index all services as components
        services_path = self.base_path / "services"
        if services_path.exists():
            for service_dir in services_path.iterdir():
                if service_dir.is_dir():
                    self._index_component(service_dir)
        
        # Index generated applications
        gen_apps_path = self.base_path / "generated-applications" 
        if gen_apps_path.exists():
            for app_dir in gen_apps_path.iterdir():
                if app_dir.is_dir():
                    self._index_component(app_dir)
        
        # Index documentation
        docs_path = self.base_path / "docs"
        if docs_path.exists():
            self._index_documentation(docs_path)
        
        # Index development tools
        dev_tools_path = self.base_path / "dev-tools"
        if dev_tools_path.exists():
            self._index_dev_tools(dev_tools_path)
        
        # Index patterns from bot learning
        self._index_bot_patterns()
        
        print(f"✅ Knowledge index built: {len(self.components)} components, {len(self.patterns)} patterns")
    
    def _index_component(self, component_path: Path):
        """Index a component directory for search and discovery"""
        try:
            component_name = component_path.name
            
            # Analyze component structure
            technologies = []
            interfaces = []
            dependencies = []
            
            # Check for common files to determine technologies
            if (component_path / "requirements.txt").exists():
                technologies.append("python")
            if (component_path / "package.json").exists():
                technologies.append("nodejs")
            if (component_path / "main.py").exists():
                technologies.append("fastapi")
            if (component_path / "docker-compose.yml").exists():
                technologies.append("docker")
            
            # Read main description from README or main file
            description = "SuperInstance Lego component"
            readme_path = component_path / "README.md"
            if readme_path.exists():
                with open(readme_path) as f:
                    content = f.read()
                    # Extract first meaningful line as description
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith('#'):
                            description = line.strip()[:200]
                            break
            
            # Determine deployment targets
            deployment_targets = ["cloud", "edge"]
            if any(tech in technologies for tech in ["python", "nodejs"]):
                deployment_targets.append("device")
            
            # Create component info
            component_info = ComponentInfo(
                name=component_name,
                path=str(component_path),
                description=description,
                technologies=technologies,
                interfaces=interfaces,
                dependencies=dependencies,
                deployment_targets=deployment_targets,
                performance_metrics={},
                compatibility_tags=technologies,
                educational_content=[],
                last_updated=datetime.now().isoformat()
            )
            
            self.components[component_name] = component_info
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                search_text = f"{component_name} {description} {' '.join(technologies)}"
                conn.execute('''
                    INSERT OR REPLACE INTO components VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    component_name,
                    component_name,
                    str(component_path),
                    description,
                    json.dumps(technologies),
                    json.dumps(interfaces),
                    json.dumps(dependencies),
                    json.dumps(deployment_targets),
                    json.dumps({}),
                    json.dumps(technologies),
                    json.dumps([]),
                    datetime.now().isoformat(),
                    search_text
                ))
                
                # Add to search index
                conn.execute('''
                    INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)
                ''', (search_text, 'component', ' '.join(technologies), str(component_path)))
                
        except Exception as e:
            print(f"Warning: Could not index component {component_path}: {e}")
    
    def _index_documentation(self, docs_path: Path):
        """Index all documentation files"""
        for doc_file in docs_path.rglob("*.md"):
            try:
                with open(doc_file) as f:
                    content = f.read()
                
                # Extract title from first heading
                title = doc_file.stem
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('#'):
                        title = line.strip('#').strip()
                        break
                
                # Determine document type
                doc_type = "documentation"
                if "tutorial" in doc_file.name.lower():
                    doc_type = "tutorial"
                elif "guide" in doc_file.name.lower():
                    doc_type = "guide"
                elif "api" in doc_file.name.lower():
                    doc_type = "api"
                
                with sqlite3.connect(self.db_path) as conn:
                    doc_id = hashlib.md5(str(doc_file).encode()).hexdigest()
                    conn.execute('''
                        INSERT OR REPLACE INTO documentation VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        doc_id,
                        title,
                        str(doc_file),
                        content[:5000],  # First 5000 chars for search
                        doc_type,
                        json.dumps([doc_type]),
                        datetime.now().isoformat()
                    ))
                    
                    # Add to search index
                    search_content = f"{title} {content[:1000]}"
                    conn.execute('''
                        INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)
                    ''', (search_content, doc_type, doc_type, str(doc_file)))
                    
            except Exception as e:
                print(f"Warning: Could not index documentation {doc_file}: {e}")
    
    def _index_dev_tools(self, dev_tools_path: Path):
        """Index development tools and scripts"""
        for tool_file in dev_tools_path.rglob("*.py"):
            try:
                with open(tool_file) as f:
                    content = f.read()
                
                # Extract docstring as description
                description = "Development tool"
                if content.startswith('"""') or content.startswith("'''"):
                    end_quote = '"""' if content.startswith('"""') else "'''"
                    end_pos = content.find(end_quote, 3)
                    if end_pos > 0:
                        description = content[3:end_pos].strip()
                
                with sqlite3.connect(self.db_path) as conn:
                    search_content = f"{tool_file.name} {description}"
                    conn.execute('''
                        INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)
                    ''', (search_content, 'dev-tool', 'automation', str(tool_file)))
                    
            except Exception as e:
                print(f"Warning: Could not index dev tool {tool_file}: {e}")
    
    def _index_bot_patterns(self):
        """Index patterns from bot learning system"""
        patterns_db = self.base_path / "docs" / "bot-learning" / "bot_learning.db"
        if patterns_db.exists():
            try:
                with sqlite3.connect(patterns_db) as source_conn:
                    cursor = source_conn.execute('SELECT * FROM patterns')
                    patterns = cursor.fetchall()
                    
                    for pattern in patterns:
                        pattern_data = {
                            'id': pattern[0],
                            'name': pattern[1],
                            'description': pattern[2],
                            'examples': pattern[3] if len(pattern) > 3 else '[]'
                        }
                        
                        with sqlite3.connect(self.db_path) as conn:
                            search_content = f"{pattern_data['name']} {pattern_data['description']}"
                            conn.execute('''
                                INSERT OR REPLACE INTO search_index VALUES (?, ?, ?, ?)
                            ''', (search_content, 'pattern', 'learning', 'bot-generated'))
                            
            except Exception as e:
                print(f"Warning: Could not index bot patterns: {e}")
    
    def search(self, query: str, result_limit: int = 20) -> List[SearchResult]:
        """
        Comprehensive search across all indexed knowledge
        """
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Full-text search using SQLite FTS5
            cursor = conn.execute('''
                SELECT content, type, tags, path, rank 
                FROM search_index 
                WHERE search_index MATCH ? 
                ORDER BY rank 
                LIMIT ?
            ''', (query, result_limit))
            
            for row in cursor.fetchall():
                content, item_type, tags, path, rank = row
                
                # Calculate relevance score based on query match
                relevance = self._calculate_relevance(query, content)
                
                result = SearchResult(
                    item_type=item_type,
                    title=self._extract_title(content, path),
                    description=content[:200],
                    path=path,
                    relevance_score=relevance,
                    tags=tags.split() if tags else [],
                    related_items=self._find_related_items(item_type, tags)
                )
                
                results.append(result)
        
        return sorted(results, key=lambda x: x.relevance_score, reverse=True)
    
    def find_compatible_components(self, component_name: str) -> List[ComponentInfo]:
        """Find components that can work together with the specified component"""
        compatible = []
        
        if component_name not in self.components:
            return compatible
        
        source_component = self.components[component_name]
        
        for name, component in self.components.items():
            if name == component_name:
                continue
            
            # Check compatibility based on shared technologies
            shared_tech = set(source_component.technologies) & set(component.technologies)
            if shared_tech:
                compatible.append(component)
        
        return compatible[:10]  # Return top 10 compatible components
    
    def get_component_suggestions(self, requirements: List[str]) -> List[ComponentInfo]:
        """Get component suggestions based on requirements"""
        suggestions = []
        
        for component in self.components.values():
            score = 0
            for req in requirements:
                if any(req.lower() in tech.lower() for tech in component.technologies):
                    score += 2
                if req.lower() in component.description.lower():
                    score += 1
                if any(req.lower() in tag.lower() for tag in component.compatibility_tags):
                    score += 1
            
            if score > 0:
                suggestions.append((score, component))
        
        # Sort by score and return top suggestions
        suggestions.sort(key=lambda x: x[0], reverse=True)
        return [comp for score, comp in suggestions[:15]]
    
    def get_learning_path(self, target_skill: str) -> Dict[str, Any]:
        """Generate a learning path for acquiring a specific skill"""
        path = {
            'skill': target_skill,
            'components_to_study': [],
            'tutorials': [],
            'practice_projects': [],
            'estimated_hours': 0
        }
        
        # Find relevant components
        relevant_components = self.search(target_skill, 5)
        for result in relevant_components:
            if result.item_type == 'component':
                path['components_to_study'].append({
                    'name': result.title,
                    'path': result.path,
                    'difficulty': 'beginner'  # Could be enhanced with actual difficulty assessment
                })
        
        # Find tutorials
        tutorial_results = self.search(f"tutorial {target_skill}", 3)
        for result in tutorial_results:
            if result.item_type in ['tutorial', 'documentation']:
                path['tutorials'].append({
                    'title': result.title,
                    'path': result.path
                })
        
        # Estimate learning time (rough approximation)
        path['estimated_hours'] = len(path['components_to_study']) * 2 + len(path['tutorials']) * 1
        
        return path
    
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calculate relevance score for search results"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Exact match bonus
        if query_lower in content_lower:
            score = 1.0
        else:
            # Partial word matches
            query_words = query_lower.split()
            content_words = content_lower.split()
            matches = sum(1 for word in query_words if word in content_words)
            score = matches / len(query_words) if query_words else 0
        
        return score
    
    def _extract_title(self, content: str, path: str) -> str:
        """Extract meaningful title from content or path"""
        lines = content.split('\n')
        for line in lines:
            if line.strip():
                return line.strip()[:50]
        
        return Path(path).name
    
    def _find_related_items(self, item_type: str, tags: str) -> List[str]:
        """Find related items based on type and tags"""
        related = []
        
        if not tags:
            return related
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT path FROM search_index 
                WHERE tags LIKE ? AND type != ? 
                LIMIT 3
            ''', (f'%{tags}%', item_type))
            
            related = [row[0] for row in cursor.fetchall()]
        
        return related
    
    def generate_api_documentation(self) -> Dict[str, Any]:
        """Generate comprehensive API documentation for the knowledge discovery system"""
        return {
            'version': '1.0.0',
            'description': 'SuperInstance Knowledge Discovery API - Search and discover Lego components',
            'endpoints': {
                'search': {
                    'method': 'GET',
                    'path': '/api/search',
                    'parameters': {
                        'q': 'Search query string',
                        'limit': 'Maximum results (default: 20)',
                        'type': 'Filter by type: component, pattern, documentation, tutorial'
                    },
                    'response': 'List of SearchResult objects'
                },
                'components': {
                    'method': 'GET', 
                    'path': '/api/components',
                    'parameters': {
                        'compatible_with': 'Find components compatible with specified component'
                    },
                    'response': 'List of ComponentInfo objects'
                },
                'suggestions': {
                    'method': 'POST',
                    'path': '/api/suggestions',
                    'body': {
                        'requirements': 'List of technology/feature requirements'
                    },
                    'response': 'List of suggested components'
                },
                'learning_path': {
                    'method': 'GET',
                    'path': '/api/learning-path',
                    'parameters': {
                        'skill': 'Target skill to learn'
                    },
                    'response': 'Structured learning path with components and tutorials'
                }
            },
            'examples': {
                'search_fastapi': '/api/search?q=fastapi&limit=10',
                'find_compatible': '/api/components?compatible_with=auth-service',
                'ai_learning_path': '/api/learning-path?skill=artificial-intelligence'
            }
        }

def main():
    """
    Main function to run knowledge discovery system
    """
    print("🧩 SuperInstance Knowledge Discovery System")
    print("=" * 50)
    
    # Initialize knowledge discovery
    kd = SuperInstanceKnowledgeDiscovery()
    
    # Example searches
    print("\n🔍 Example Searches:")
    print("-" * 30)
    
    # Search for authentication components
    auth_results = kd.search("authentication")
    print(f"\nAuthentication components ({len(auth_results)} found):")
    for result in auth_results[:3]:
        print(f"  • {result.title} ({result.item_type}) - {result.relevance_score:.2f}")
    
    # Search for AI/ML components  
    ai_results = kd.search("artificial intelligence")
    print(f"\nAI/ML components ({len(ai_results)} found):")
    for result in ai_results[:3]:
        print(f"  • {result.title} ({result.item_type}) - {result.relevance_score:.2f}")
    
    # Get component suggestions for a web app
    suggestions = kd.get_component_suggestions(['web', 'api', 'database'])
    print(f"\nWeb app component suggestions ({len(suggestions)} found):")
    for comp in suggestions[:3]:
        print(f"  • {comp.name}: {comp.description[:60]}...")
    
    # Generate learning path
    learning_path = kd.get_learning_path('machine learning')
    print(f"\nMachine Learning learning path:")
    print(f"  • Components to study: {len(learning_path['components_to_study'])}")
    print(f"  • Tutorials available: {len(learning_path['tutorials'])}")
    print(f"  • Estimated time: {learning_path['estimated_hours']} hours")
    
    print("\n✅ Knowledge Discovery System operational!")
    print("🎯 Ready to help developers find the perfect Lego components")
    print("💡 SuperInstance: $2/month access to infinite software possibilities")

if __name__ == "__main__":
    main()