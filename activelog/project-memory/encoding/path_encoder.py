"""
ActiveLog Project Memory - Smart Path Encoding System
Semantic directory structure with functionality encoding in folder names
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone

class PathType(Enum):
    """Types of paths in the encoding system"""
    SERVICE = "service"
    COMPONENT = "component"
    UTILITY = "utility"
    MODEL = "model"
    CONFIG = "config"
    TEST = "test"
    DOCS = "docs"

class FunctionalityCategory(Enum):
    """Categories of functionality for encoding"""
    API = "api"
    AUTH = "auth"
    DATA = "data"
    UI = "ui"
    LOGIC = "logic"
    INTEGRATION = "integration"
    SECURITY = "security"
    MONITORING = "monitoring"

@dataclass
class EncodedPath:
    """Represents an encoded path with semantic meaning"""
    original_path: str
    encoded_path: str
    path_type: PathType
    functionality: FunctionalityCategory
    complexity_level: int
    metadata: Dict[str, Any]
    encoding_version: str = "1.0"

class SmartPathEncoder:
    """
    Smart path encoding system that embeds functionality into folder names
    Maximizes information density while maintaining readability
    """
    
    def __init__(self, project_root: str = "/home/activeloguser/activelog"):
        self.project_root = Path(project_root)
        self.encoding_rules = self._initialize_encoding_rules()
        self.functionality_patterns = self._initialize_functionality_patterns()
        self.encoded_paths_cache = {}
        
    def _initialize_encoding_rules(self) -> Dict[str, Dict[str, str]]:
        """Initialize encoding rules for different path types"""
        return {
            "service": {
                "prefix": "svc",
                "separator": "-",
                "max_length": 50,
                "include_port": True,
                "include_phase": True
            },
            "component": {
                "prefix": "cmp",
                "separator": "_",
                "max_length": 40,
                "include_type": True,
                "include_dependency": False
            },
            "utility": {
                "prefix": "util",
                "separator": "_",
                "max_length": 35,
                "include_functionality": True
            },
            "model": {
                "prefix": "mdl",
                "separator": "_",
                "max_length": 30,
                "include_entity": True
            },
            "config": {
                "prefix": "cfg",
                "separator": "_",
                "max_length": 25,
                "include_environment": True
            }
        }
    
    def _initialize_functionality_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for functionality detection"""
        return {
            "api": ["router", "endpoint", "controller", "handler", "route"],
            "auth": ["auth", "jwt", "token", "login", "session", "permission"],
            "data": ["model", "schema", "database", "orm", "repository", "dao"],
            "ui": ["component", "page", "view", "template", "frontend"],
            "logic": ["service", "business", "processor", "engine", "algorithm"],
            "integration": ["client", "adapter", "connector", "bridge", "gateway"],
            "security": ["encryption", "security", "hash", "crypto", "validate"],
            "monitoring": ["monitor", "health", "metrics", "logging", "telemetry"]
        }
    
    def detect_functionality(self, path: str, content_analysis: Optional[Dict[str, Any]] = None) -> FunctionalityCategory:
        """
        Detect functionality category based on path and optional content analysis
        """
        path_lower = path.lower()
        
        # Check filename and directory names
        path_parts = path_lower.replace('\\', '/').split('/')
        
        for functionality, patterns in self.functionality_patterns.items():
            for pattern in patterns:
                if any(pattern in part for part in path_parts):
                    return FunctionalityCategory(functionality)
        
        # Content-based detection if available
        if content_analysis:
            imports = content_analysis.get("imports", [])
            classes = content_analysis.get("classes", [])
            functions = content_analysis.get("functions", [])
            
            # Check for API-related imports
            api_imports = ["fastapi", "flask", "django", "starlette", "router"]
            if any(imp.get("module", "").lower() in api_imports for imp in imports):
                return FunctionalityCategory.API
            
            # Check for auth-related patterns
            auth_patterns = ["jwt", "auth", "token", "session"]
            if any(pattern in path_lower for pattern in auth_patterns):
                return FunctionalityCategory.AUTH
            
            # Check for data patterns
            data_patterns = ["model", "schema", "database"]
            if any(pattern in cls.get("name", "").lower() for cls in classes for pattern in data_patterns):
                return FunctionalityCategory.DATA
        
        # Default to logic if no specific pattern detected
        return FunctionalityCategory.LOGIC
    
    def calculate_complexity_level(self, path: str, content_analysis: Optional[Dict[str, Any]] = None) -> int:
        """
        Calculate complexity level (1-10) based on path and content
        """
        complexity = 1
        
        # Path-based complexity
        path_depth = len(Path(path).parts)
        complexity += min(path_depth // 2, 3)
        
        # Content-based complexity
        if content_analysis:
            # Classes and functions add complexity
            complexity += len(content_analysis.get("classes", [])) * 2
            complexity += len(content_analysis.get("functions", []))
            
            # Imports indicate external dependencies
            complexity += min(len(content_analysis.get("imports", [])) // 5, 2)
            
            # Existing complexity score if available
            if "complexity_score" in content_analysis:
                complexity += min(content_analysis["complexity_score"] // 5, 3)
        
        return min(complexity, 10)
    
    def encode_service_path(self, service_name: str, port: int, phase: str, 
                          functionality: FunctionalityCategory) -> str:
        """
        Encode service path with maximum information density
        """
        rules = self.encoding_rules["service"]
        
        # Phase encoding (P1, P2, P3, P4, P5)
        phase_code = f"P{phase.split()[-1]}" if "Phase" in phase else f"P{phase}"
        
        # Port encoding (last 2 digits)
        port_code = str(port)[-2:].zfill(2)
        
        # Functionality encoding (first 3 letters)
        func_code = functionality.value[:3].upper()
        
        # Service name abbreviation (max 8 chars, remove vowels if needed)
        service_abbrev = self._abbreviate_name(service_name, 8)
        
        # Combine: svc-P1-50-API-BotOrch
        encoded = f"{rules['prefix']}{rules['separator']}{phase_code}{rules['separator']}{port_code}{rules['separator']}{func_code}{rules['separator']}{service_abbrev}"
        
        return encoded[:rules["max_length"]]
    
    def encode_component_path(self, component_name: str, component_type: str,
                            functionality: FunctionalityCategory,
                            complexity: int) -> str:
        """
        Encode component path with type and complexity information
        """
        rules = self.encoding_rules["component"]
        
        # Component type encoding
        type_codes = {
            "controller": "CTRL",
            "service": "SVC",
            "model": "MDL",
            "utility": "UTIL",
            "handler": "HNDL",
            "manager": "MGR",
            "processor": "PROC"
        }
        
        type_code = type_codes.get(component_type.lower(), component_type[:4].upper())
        
        # Functionality code
        func_code = functionality.value[:3].upper()
        
        # Complexity level (1-10)
        complex_code = f"C{complexity}"
        
        # Component name abbreviation
        comp_abbrev = self._abbreviate_name(component_name, 10)
        
        # Combine: cmp_CTRL_API_C5_TokenMgr
        encoded = f"{rules['prefix']}{rules['separator']}{type_code}{rules['separator']}{func_code}{rules['separator']}{complex_code}{rules['separator']}{comp_abbrev}"
        
        return encoded[:rules["max_length"]]
    
    def encode_utility_path(self, utility_name: str, 
                          functionality: FunctionalityCategory,
                          dependencies: List[str] = None) -> str:
        """
        Encode utility path with functionality and dependency information
        """
        rules = self.encoding_rules["utility"]
        
        # Functionality code
        func_code = functionality.value[:4].upper()
        
        # Dependency encoding (first letter of each major dependency)
        dep_code = ""
        if dependencies:
            major_deps = ["fastapi", "redis", "postgresql", "jwt", "crypto"]
            dep_letters = []
            for dep in dependencies:
                for major in major_deps:
                    if major in dep.lower():
                        dep_letters.append(major[0].upper())
                        break
            dep_code = "".join(dep_letters[:3])
        
        # Utility name abbreviation
        util_abbrev = self._abbreviate_name(utility_name, 12)
        
        # Combine: util_AUTH_FRP_JwtHelper
        if dep_code:
            encoded = f"{rules['prefix']}{rules['separator']}{func_code}{rules['separator']}{dep_code}{rules['separator']}{util_abbrev}"
        else:
            encoded = f"{rules['prefix']}{rules['separator']}{func_code}{rules['separator']}{util_abbrev}"
        
        return encoded[:rules["max_length"]]
    
    def _abbreviate_name(self, name: str, max_length: int) -> str:
        """
        Intelligently abbreviate names while preserving meaning
        """
        if len(name) <= max_length:
            return name
        
        # Remove common suffixes
        suffixes_to_remove = ["_service", "_controller", "_manager", "_handler", 
                             "_processor", "_utility", "_helper"]
        
        for suffix in suffixes_to_remove:
            if name.lower().endswith(suffix):
                name = name[:-len(suffix)]
                break
        
        if len(name) <= max_length:
            return name
        
        # CamelCase abbreviation - keep first letter + capitals
        if any(c.isupper() for c in name[1:]):
            abbreviated = name[0]
            for i, char in enumerate(name[1:], 1):
                if char.isupper():
                    abbreviated += char
                    if len(abbreviated) >= max_length:
                        break
            if len(abbreviated) >= 3:  # Minimum meaningful abbreviation
                return abbreviated
        
        # Remove vowels from the middle
        if len(name) > max_length:
            consonants = name[0]  # Keep first character
            vowels = set('aeiouAEIOU')
            
            for i, char in enumerate(name[1:], 1):
                if char not in vowels or i == len(name) - 1:  # Keep last character
                    consonants += char
                    if len(consonants) >= max_length:
                        break
            
            return consonants[:max_length]
        
        return name[:max_length]
    
    def encode_path(self, original_path: str, 
                   content_analysis: Optional[Dict[str, Any]] = None,
                   override_type: Optional[PathType] = None) -> EncodedPath:
        """
        Main encoding function that creates semantically rich path encodings
        """
        
        # Detect path type
        path_type = override_type or self._detect_path_type(original_path)
        
        # Detect functionality
        functionality = self.detect_functionality(original_path, content_analysis)
        
        # Calculate complexity
        complexity = self.calculate_complexity_level(original_path, content_analysis)
        
        # Generate encoded path based on type
        if path_type == PathType.SERVICE:
            service_name = Path(original_path).name
            port = self._extract_port_from_path(original_path)
            phase = self._extract_phase_from_path(original_path)
            encoded_path = self.encode_service_path(service_name, port, phase, functionality)
        
        elif path_type == PathType.COMPONENT:
            component_name = Path(original_path).stem
            component_type = self._detect_component_type(original_path, content_analysis)
            encoded_path = self.encode_component_path(component_name, component_type, functionality, complexity)
        
        elif path_type == PathType.UTILITY:
            utility_name = Path(original_path).stem
            dependencies = self._extract_dependencies(content_analysis) if content_analysis else []
            encoded_path = self.encode_utility_path(utility_name, functionality, dependencies)
        
        else:
            # Default encoding for other types
            name = Path(original_path).stem
            encoded_path = f"{path_type.value}_{functionality.value[:3]}_{self._abbreviate_name(name, 15)}"
        
        # Create metadata
        metadata = {
            "original_name": Path(original_path).name,
            "encoding_timestamp": datetime.now(timezone.utc).isoformat(),
            "path_depth": len(Path(original_path).parts),
            "file_extension": Path(original_path).suffix,
            "estimated_size": self._estimate_file_size(original_path)
        }
        
        if content_analysis:
            metadata.update({
                "classes_count": len(content_analysis.get("classes", [])),
                "functions_count": len(content_analysis.get("functions", [])),
                "imports_count": len(content_analysis.get("imports", []))
            })
        
        return EncodedPath(
            original_path=original_path,
            encoded_path=encoded_path,
            path_type=path_type,
            functionality=functionality,
            complexity_level=complexity,
            metadata=metadata
        )
    
    def _detect_path_type(self, path: str) -> PathType:
        """Detect the type of path based on structure and location"""
        path_parts = Path(path).parts
        
        if "services" in path_parts:
            return PathType.SERVICE
        elif "test" in path.lower() or path.endswith("_test.py"):
            return PathType.TEST
        elif "docs" in path_parts or path.endswith(".md"):
            return PathType.DOCS
        elif "config" in path.lower() or "settings" in path.lower():
            return PathType.CONFIG
        elif "models" in path_parts or "schemas" in path_parts:
            return PathType.MODEL
        elif "utils" in path_parts or "utilities" in path_parts:
            return PathType.UTILITY
        else:
            return PathType.COMPONENT
    
    def _detect_component_type(self, path: str, content_analysis: Optional[Dict[str, Any]]) -> str:
        """Detect component type from path and content"""
        filename = Path(path).stem.lower()
        
        type_patterns = {
            "controller": ["controller", "ctrl", "handler"],
            "service": ["service", "svc"],
            "manager": ["manager", "mgr"],
            "processor": ["processor", "proc"],
            "utility": ["utility", "util", "helper"],
            "model": ["model", "schema"],
            "router": ["router", "routes"],
            "middleware": ["middleware", "mw"]
        }
        
        for comp_type, patterns in type_patterns.items():
            if any(pattern in filename for pattern in patterns):
                return comp_type
        
        # Content-based detection
        if content_analysis:
            classes = content_analysis.get("classes", [])
            if classes:
                class_name = classes[0].get("name", "").lower()
                for comp_type, patterns in type_patterns.items():
                    if any(pattern in class_name for pattern in patterns):
                        return comp_type
        
        return "component"
    
    def _extract_port_from_path(self, path: str) -> int:
        """Extract port number from path or return default"""
        # Look for port patterns in path
        port_pattern = r'(\d{4})'
        matches = re.findall(port_pattern, path)
        
        if matches:
            port = int(matches[0])
            if 8000 <= port <= 9999:  # Reasonable service port range
                return port
        
        return 8000  # Default port
    
    def _extract_phase_from_path(self, path: str) -> str:
        """Extract phase information from path"""
        path_lower = path.lower()
        
        phase_mapping = {
            "bot": "1",
            "dream": "2", 
            "lucid": "2",
            "business": "3",
            "compute": "3",
            "hatchery": "3",
            "municipal": "3",
            "dividend": "4",
            "paper": "4",
            "trading": "4",
            "market": "4",
            "code": "5",
            "developer": "5"
        }
        
        for keyword, phase in phase_mapping.items():
            if keyword in path_lower:
                return phase
        
        return "1"  # Default to phase 1
    
    def _extract_dependencies(self, content_analysis: Dict[str, Any]) -> List[str]:
        """Extract major dependencies from content analysis"""
        if not content_analysis:
            return []
        
        imports = content_analysis.get("imports", [])
        dependencies = []
        
        for imp in imports:
            module = imp.get("module", "")
            if module:
                # Extract top-level package name
                package = module.split('.')[0]
                if package not in ["typing", "datetime", "os", "sys", "json"]:  # Skip built-ins
                    dependencies.append(package)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _estimate_file_size(self, path: str) -> str:
        """Estimate file size category"""
        try:
            size = os.path.getsize(path)
            if size < 1024:
                return "XS"  # < 1KB
            elif size < 10240:
                return "S"   # < 10KB
            elif size < 102400:
                return "M"   # < 100KB
            elif size < 1048576:
                return "L"   # < 1MB
            else:
                return "XL"  # >= 1MB
        except:
            return "U"  # Unknown
    
    def decode_path(self, encoded_path: str) -> Dict[str, Any]:
        """
        Decode an encoded path back to its semantic components
        """
        parts = encoded_path.split('-') or encoded_path.split('_')
        
        if not parts:
            return {"error": "Invalid encoded path"}
        
        prefix = parts[0]
        decoded = {"prefix": prefix, "components": parts[1:]}
        
        # Decode based on prefix
        if prefix == "svc" and len(parts) >= 5:
            decoded.update({
                "type": "service",
                "phase": parts[1],
                "port_suffix": parts[2],
                "functionality": parts[3],
                "service_name": parts[4]
            })
        
        elif prefix == "cmp" and len(parts) >= 5:
            decoded.update({
                "type": "component",
                "component_type": parts[1],
                "functionality": parts[2],
                "complexity": parts[3],
                "component_name": parts[4]
            })
        
        elif prefix == "util" and len(parts) >= 3:
            decoded.update({
                "type": "utility",
                "functionality": parts[1],
                "dependencies": parts[2] if len(parts) > 3 else None,
                "utility_name": parts[-1]
            })
        
        return decoded
    
    def generate_directory_structure(self, encoded_paths: List[EncodedPath]) -> Dict[str, Any]:
        """
        Generate optimized directory structure using encoded paths
        """
        structure = {}
        
        # Group by functionality and type
        for encoded_path in encoded_paths:
            functionality = encoded_path.functionality.value
            path_type = encoded_path.path_type.value
            
            if functionality not in structure:
                structure[functionality] = {}
            
            if path_type not in structure[functionality]:
                structure[functionality][path_type] = []
            
            structure[functionality][path_type].append({
                "encoded_name": encoded_path.encoded_path,
                "original_name": Path(encoded_path.original_path).name,
                "complexity": encoded_path.complexity_level,
                "metadata": encoded_path.metadata
            })
        
        return structure
    
    def optimize_paths_for_context(self, paths: List[str], 
                                  max_context_items: int = 20) -> List[EncodedPath]:
        """
        Optimize path list for context window usage
        """
        encoded_paths = []
        
        for path in paths:
            encoded = self.encode_path(path)
            encoded_paths.append(encoded)
        
        # Sort by complexity and functionality for optimal context loading
        encoded_paths.sort(key=lambda x: (x.functionality.value, -x.complexity_level))
        
        return encoded_paths[:max_context_items]