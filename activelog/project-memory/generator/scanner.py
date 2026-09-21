#!/usr/bin/env python3
"""
Code Change Scanner

Monitors codebase changes and identifies documentation update needs.
Maintains bidirectional links between code and knowledge concepts.
"""

import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import ast
import re

@dataclass
class CodeChange:
    file_path: str
    change_type: str  # 'modified', 'added', 'deleted'
    timestamp: float
    old_hash: Optional[str]
    new_hash: Optional[str]
    affected_concepts: List[str]
    change_summary: str

@dataclass
class ConceptLink:
    concept_id: str
    file_path: str
    line_numbers: List[int]
    code_elements: List[str]  # function names, class names, etc.
    last_verified: float

class CodeScanner:
    """Scans code changes and maps to knowledge concepts."""
    
    def __init__(self, project_path: str, memory_path: str):
        self.project_path = Path(project_path)
        self.memory_path = Path(memory_path)
        self.cache_path = self.memory_path / "cache"
        self.cache_path.mkdir(exist_ok=True)
        
        # Load existing state
        self.file_hashes = self._load_file_hashes()
        self.concept_links = self._load_concept_links()
        
        # Code patterns that map to concepts
        self.concept_patterns = self._load_concept_patterns()
    
    def _load_file_hashes(self) -> Dict[str, str]:
        """Load previous file hash state."""
        hash_file = self.cache_path / "file_hashes.json"
        try:
            with open(hash_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_file_hashes(self):
        """Save current file hash state."""
        hash_file = self.cache_path / "file_hashes.json"
        with open(hash_file, 'w') as f:
            json.dump(self.file_hashes, f, indent=2)
    
    def _load_concept_links(self) -> Dict[str, List[ConceptLink]]:
        """Load concept-to-code mappings."""
        links_file = self.cache_path / "concept_links.json"
        try:
            with open(links_file, 'r') as f:
                data = json.load(f)
                result = {}
                for concept_id, links in data.items():
                    result[concept_id] = [
                        ConceptLink(**link) for link in links
                    ]
                return result
        except FileNotFoundError:
            return {}
    
    def _save_concept_links(self):
        """Save concept-to-code mappings."""
        links_file = self.cache_path / "concept_links.json"
        serializable = {}
        for concept_id, links in self.concept_links.items():
            serializable[concept_id] = [
                {
                    "concept_id": link.concept_id,
                    "file_path": link.file_path,
                    "line_numbers": link.line_numbers,
                    "code_elements": link.code_elements,
                    "last_verified": link.last_verified
                }
                for link in links
            ]
        
        with open(links_file, 'w') as f:
            json.dump(serializable, f, indent=2)
    
    def _load_concept_patterns(self) -> Dict[str, List[str]]:
        """Load patterns that map code to concepts."""
        return {
            "CORE-001": [
                "main.py", "FastAPI", "uvicorn", "__main__"
            ],
            "AUTH-001": [
                "/auth/", "jwt", "JWT", "authentication", "login", "password"
            ],
            "SVC-001": [
                "main.py", "FastAPI", "health", "router", "app = FastAPI"
            ],
            "DB-001": [
                "database", "sqlite", "postgresql", "sqlalchemy", "connection"
            ],
            "API-001": [
                "@app.", "router", "endpoint", "POST", "GET", "PUT", "DELETE"
            ],
            "FE-001": [
                "React", "frontend", "components", "jsx", "tsx"
            ],
            "DOCKER-001": [
                "Dockerfile", "docker-compose", "container", "image"
            ]
        }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file contents."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except (OSError, UnicodeDecodeError):
            return ""
    
    def _should_scan_file(self, file_path: Path) -> bool:
        """Determine if file should be scanned."""
        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        if any(part in skip_dirs for part in file_path.parts):
            return False
        
        # Include certain file extensions
        include_extensions = {'.py', '.js', '.tsx', '.jsx', '.md', '.json', '.yml', '.yaml'}
        return file_path.suffix in include_extensions
    
    def scan_for_changes(self) -> List[CodeChange]:
        """Scan project for code changes."""
        changes = []
        current_time = time.time()
        
        # Scan all relevant files
        for file_path in self.project_path.rglob("*"):
            if not file_path.is_file() or not self._should_scan_file(file_path):
                continue
            
            rel_path = str(file_path.relative_to(self.project_path))
            current_hash = self._calculate_file_hash(file_path)
            
            if not current_hash:  # Skip files that can't be read
                continue
            
            old_hash = self.file_hashes.get(rel_path)
            
            if old_hash is None:
                # New file
                change = CodeChange(
                    file_path=rel_path,
                    change_type="added",
                    timestamp=current_time,
                    old_hash=None,
                    new_hash=current_hash,
                    affected_concepts=self._identify_concepts(file_path),
                    change_summary=f"Added new file: {rel_path}"
                )
                changes.append(change)
                
            elif old_hash != current_hash:
                # Modified file
                change = CodeChange(
                    file_path=rel_path,
                    change_type="modified", 
                    timestamp=current_time,
                    old_hash=old_hash,
                    new_hash=current_hash,
                    affected_concepts=self._identify_concepts(file_path),
                    change_summary=f"Modified file: {rel_path}"
                )
                changes.append(change)
            
            # Update hash
            self.file_hashes[rel_path] = current_hash
        
        # Check for deleted files
        current_files = set(self.file_hashes.keys())
        existing_files = {
            str(f.relative_to(self.project_path))
            for f in self.project_path.rglob("*")
            if f.is_file() and self._should_scan_file(f)
        }
        
        deleted_files = current_files - existing_files
        for deleted_file in deleted_files:
            change = CodeChange(
                file_path=deleted_file,
                change_type="deleted",
                timestamp=current_time,
                old_hash=self.file_hashes[deleted_file],
                new_hash=None,
                affected_concepts=self._identify_concepts_by_path(deleted_file),
                change_summary=f"Deleted file: {deleted_file}"
            )
            changes.append(change)
            del self.file_hashes[deleted_file]
        
        # Save updated hashes
        self._save_file_hashes()
        
        # Update concept links
        self._update_concept_links(changes)
        
        return changes
    
    def _identify_concepts(self, file_path: Path) -> List[str]:
        """Identify which concepts are affected by a file."""
        affected_concepts = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            file_path_str = str(file_path).lower()
            
            # Check patterns
            for concept_id, patterns in self.concept_patterns.items():
                for pattern in patterns:
                    if pattern.lower() in content or pattern.lower() in file_path_str:
                        affected_concepts.append(concept_id)
                        break
            
        except (UnicodeDecodeError, OSError):
            pass
        
        # Add path-based identification
        affected_concepts.extend(self._identify_concepts_by_path(str(file_path)))
        
        return list(set(affected_concepts))
    
    def _identify_concepts_by_path(self, file_path: str) -> List[str]:
        """Identify concepts based on file path patterns."""
        concepts = []
        path_lower = file_path.lower()
        
        # Service-specific mappings
        if "/auth/" in path_lower:
            concepts.append("AUTH-001")
        if "/api-gateway/" in path_lower:
            concepts.append("SVC-002")
        if "/bot-ecosystem/" in path_lower:
            concepts.append("AI-001")
        if "/frontend" in path_lower:
            concepts.append("FE-001")
        if "main.py" in path_lower and "/services/" in path_lower:
            concepts.append("SVC-001")
        if "docker" in path_lower:
            concepts.append("CONTAINER-001")
        
        return concepts
    
    def _update_concept_links(self, changes: List[CodeChange]):
        """Update concept-to-code mappings based on changes."""
        current_time = time.time()
        
        for change in changes:
            for concept_id in change.affected_concepts:
                if concept_id not in self.concept_links:
                    self.concept_links[concept_id] = []
                
                # Remove old links for this file
                self.concept_links[concept_id] = [
                    link for link in self.concept_links[concept_id]
                    if link.file_path != change.file_path
                ]
                
                # Add new link if file wasn't deleted
                if change.change_type != "deleted":
                    code_elements = self._extract_code_elements(change.file_path)
                    line_numbers = self._find_concept_lines(change.file_path, concept_id)
                    
                    link = ConceptLink(
                        concept_id=concept_id,
                        file_path=change.file_path,
                        line_numbers=line_numbers,
                        code_elements=code_elements,
                        last_verified=current_time
                    )
                    self.concept_links[concept_id].append(link)
        
        # Save updated links
        self._save_concept_links()
    
    def _extract_code_elements(self, file_path: str) -> List[str]:
        """Extract important code elements (functions, classes, etc.) from file."""
        elements = []
        full_path = self.project_path / file_path
        
        if not full_path.exists() or full_path.suffix != '.py':
            return elements
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse Python AST
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    elements.append(f"function:{node.name}")
                elif isinstance(node, ast.ClassDef):
                    elements.append(f"class:{node.name}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        elements.append(f"import:{alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        elements.append(f"from:{node.module}")
            
        except (SyntaxError, UnicodeDecodeError):
            # For non-Python files or syntax errors, use regex
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract function definitions
                functions = re.findall(r'def\s+(\w+)', content)
                elements.extend([f"function:{func}" for func in functions])
                
                # Extract class definitions
                classes = re.findall(r'class\s+(\w+)', content)
                elements.extend([f"class:{cls}" for cls in classes])
                
            except UnicodeDecodeError:
                pass
        
        return elements
    
    def _find_concept_lines(self, file_path: str, concept_id: str) -> List[int]:
        """Find line numbers where concept-related code appears."""
        lines = []
        full_path = self.project_path / file_path
        
        if not full_path.exists():
            return lines
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    line_lower = line.lower()
                    patterns = self.concept_patterns.get(concept_id, [])
                    
                    for pattern in patterns:
                        if pattern.lower() in line_lower:
                            lines.append(i)
                            break
        
        except UnicodeDecodeError:
            pass
        
        return lines
    
    def get_outdated_concepts(self, max_age_days: int = 7) -> List[str]:
        """Get concepts that may need documentation updates."""
        cutoff_time = time.time() - (max_age_days * 24 * 3600)
        outdated = []
        
        for concept_id, links in self.concept_links.items():
            if not links:  # No links
                continue
                
            latest_verification = max(link.last_verified for link in links)
            if latest_verification < cutoff_time:
                outdated.append(concept_id)
        
        return outdated
    
    def get_concept_impact_report(self, changes: List[CodeChange]) -> Dict[str, Dict]:
        """Generate impact report showing how changes affect concepts."""
        impact_report = {}
        
        for change in changes:
            for concept_id in change.affected_concepts:
                if concept_id not in impact_report:
                    impact_report[concept_id] = {
                        "files_changed": [],
                        "change_types": set(),
                        "total_changes": 0,
                        "needs_doc_update": True
                    }
                
                impact_report[concept_id]["files_changed"].append(change.file_path)
                impact_report[concept_id]["change_types"].add(change.change_type)
                impact_report[concept_id]["total_changes"] += 1
        
        # Convert sets to lists for JSON serialization
        for concept_id in impact_report:
            impact_report[concept_id]["change_types"] = list(impact_report[concept_id]["change_types"])
        
        return impact_report


if __name__ == "__main__":
    # Example usage
    scanner = CodeScanner(
        project_path="/home/activeloguser/activelog",
        memory_path="/home/activeloguser/activelog/project-memory"
    )
    
    print("Scanning for code changes...")
    changes = scanner.scan_for_changes()
    
    print(f"Found {len(changes)} changes:")
    for change in changes[:10]:  # Show first 10
        print(f"  {change.change_type}: {change.file_path}")
        print(f"    Affects concepts: {change.affected_concepts}")
    
    if changes:
        impact_report = scanner.get_concept_impact_report(changes)
        print(f"\nImpact on {len(impact_report)} concepts:")
        for concept_id, impact in impact_report.items():
            print(f"  {concept_id}: {impact['total_changes']} changes")
    
    outdated = scanner.get_outdated_concepts()
    if outdated:
        print(f"\nOutdated concepts needing review: {outdated}")