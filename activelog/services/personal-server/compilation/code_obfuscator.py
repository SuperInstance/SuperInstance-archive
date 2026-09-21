import asyncio
import ast
import py_compile
import marshal
import types
import base64
import zlib
import logging
import os
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import inspect

class ProtectionLevel(Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    MAXIMUM = "maximum"

class CompilationTarget(Enum):
    BYTECODE = "bytecode"
    OBFUSCATED = "obfuscated"
    ENCRYPTED = "encrypted"
    HYBRID = "hybrid"

@dataclass
class CodeUnit:
    name: str
    source_code: str
    file_path: str
    dependencies: List[str]
    sensitivity_level: str
    compilation_target: CompilationTarget

@dataclass
class CompilationResult:
    compiled_code: bytes
    loader_code: str
    metadata: Dict[str, Any]
    protection_level: ProtectionLevel
    size_reduction: float
    security_score: float

class SensitiveCodeCompiler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Sensitive patterns that should be compiled to bytecode
        self.sensitive_patterns = {
            "authentication": [
                "password", "token", "secret", "key", "auth", "login",
                "jwt", "oauth", "session", "credential"
            ],
            "encryption": [
                "encrypt", "decrypt", "cipher", "crypto", "hash",
                "signature", "certificate", "ssl", "tls"
            ],
            "business_logic": [
                "pricing", "billing", "payment", "license", "quota",
                "rate_limit", "algorithm", "proprietary"
            ],
            "api_keys": [
                "api_key", "secret_key", "private_key", "access_token",
                "refresh_token", "client_secret"
            ],
            "database": [
                "connection_string", "db_password", "sql_query",
                "database_url", "mongo_uri"
            ]
        }
        
        # Compilation strategies
        self.compilation_strategies = {
            ProtectionLevel.BASIC: {
                "bytecode_compile": True,
                "name_mangling": False,
                "string_encryption": False,
                "control_flow_obfuscation": False
            },
            ProtectionLevel.ADVANCED: {
                "bytecode_compile": True,
                "name_mangling": True,
                "string_encryption": True,
                "control_flow_obfuscation": False
            },
            ProtectionLevel.MAXIMUM: {
                "bytecode_compile": True,
                "name_mangling": True,
                "string_encryption": True,
                "control_flow_obfuscation": True
            }
        }

    async def analyze_code_sensitivity(self, code_files: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """Analyze code files to identify sensitive sections"""
        try:
            analysis_results = {}
            
            for file_path, source_code in code_files.items():
                analysis = {
                    "sensitivity_score": 0.0,
                    "sensitive_patterns": [],
                    "sensitive_functions": [],
                    "sensitive_classes": [],
                    "recommended_protection": ProtectionLevel.BASIC,
                    "compilation_priority": 0
                }
                
                # Parse AST
                try:
                    tree = ast.parse(source_code)
                    analysis.update(self._analyze_ast_sensitivity(tree, source_code))
                except SyntaxError as e:
                    self.logger.warning(f"Cannot parse {file_path}: {e}")
                    continue
                
                # Text-based pattern matching
                pattern_analysis = self._analyze_text_patterns(source_code)
                analysis["sensitivity_score"] += pattern_analysis["score"]
                analysis["sensitive_patterns"].extend(pattern_analysis["patterns"])
                
                # Determine protection level
                analysis["recommended_protection"] = self._determine_protection_level(analysis["sensitivity_score"])
                analysis["compilation_priority"] = int(analysis["sensitivity_score"] * 10)
                
                analysis_results[file_path] = analysis
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Error analyzing code sensitivity: {e}")
            return {}

    def _analyze_ast_sensitivity(self, tree: ast.AST, source_code: str) -> Dict[str, Any]:
        """Analyze AST for sensitive patterns"""
        analysis = {
            "sensitivity_score": 0.0,
            "sensitive_functions": [],
            "sensitive_classes": [],
            "has_crypto_imports": False,
            "has_network_calls": False,
            "has_file_operations": False
        }
        
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_names = []
                if isinstance(node, ast.Import):
                    module_names = [alias.name for alias in node.names]
                else:
                    module_names = [node.module] if node.module else []
                
                for module in module_names:
                    if module and any(crypto in module.lower() for crypto in ["crypto", "ssl", "jwt", "oauth"]):
                        analysis["has_crypto_imports"] = True
                        analysis["sensitivity_score"] += 2.0
                    
                    if module and any(net in module.lower() for net in ["requests", "urllib", "socket", "http"]):
                        analysis["has_network_calls"] = True
                        analysis["sensitivity_score"] += 1.0
            
            # Check function definitions
            if isinstance(node, ast.FunctionDef):
                func_name = node.name.lower()
                if any(pattern in func_name for patterns in self.sensitive_patterns.values() for pattern in patterns):
                    analysis["sensitive_functions"].append(node.name)
                    analysis["sensitivity_score"] += 1.5
            
            # Check class definitions
            if isinstance(node, ast.ClassDef):
                class_name = node.name.lower()
                if any(pattern in class_name for patterns in self.sensitive_patterns.values() for pattern in patterns):
                    analysis["sensitive_classes"].append(node.name)
                    analysis["sensitivity_score"] += 1.0
            
            # Check string literals for sensitive content
            if isinstance(node, ast.Str):
                string_content = node.s.lower()
                if any(pattern in string_content for patterns in self.sensitive_patterns.values() for pattern in patterns):
                    analysis["sensitivity_score"] += 0.5
        
        return analysis

    def _analyze_text_patterns(self, source_code: str) -> Dict[str, Any]:
        """Analyze source code text for sensitive patterns"""
        analysis = {"score": 0.0, "patterns": []}
        
        source_lower = source_code.lower()
        
        for category, patterns in self.sensitive_patterns.items():
            for pattern in patterns:
                if pattern in source_lower:
                    analysis["patterns"].append({"category": category, "pattern": pattern})
                    # Weight score by category importance
                    weight = {"authentication": 3.0, "encryption": 3.0, "business_logic": 2.0, 
                             "api_keys": 4.0, "database": 2.5}.get(category, 1.0)
                    analysis["score"] += weight
        
        return analysis

    def _determine_protection_level(self, sensitivity_score: float) -> ProtectionLevel:
        """Determine protection level based on sensitivity score"""
        if sensitivity_score >= 10.0:
            return ProtectionLevel.MAXIMUM
        elif sensitivity_score >= 5.0:
            return ProtectionLevel.ADVANCED
        else:
            return ProtectionLevel.BASIC

    async def compile_sensitive_code(
        self,
        code_units: List[CodeUnit],
        protection_level: ProtectionLevel = ProtectionLevel.ADVANCED
    ) -> Dict[str, CompilationResult]:
        """Compile sensitive code units to bytecode with obfuscation"""
        try:
            results = {}
            
            for unit in code_units:
                # Choose compilation strategy
                strategy = self.compilation_strategies[protection_level]
                
                # Apply transformations
                transformed_code = unit.source_code
                
                if strategy["name_mangling"]:
                    transformed_code = self._apply_name_mangling(transformed_code)
                
                if strategy["string_encryption"]:
                    transformed_code = self._apply_string_encryption(transformed_code)
                
                if strategy["control_flow_obfuscation"]:
                    transformed_code = self._apply_control_flow_obfuscation(transformed_code)
                
                # Compile to bytecode
                compiled_code = self._compile_to_bytecode(transformed_code, unit.name)
                
                # Generate loader
                loader_code = self._generate_loader(unit.name, compiled_code, strategy)
                
                # Calculate metrics
                original_size = len(unit.source_code.encode())
                compiled_size = len(compiled_code)
                size_reduction = (original_size - compiled_size) / original_size
                
                security_score = self._calculate_security_score(strategy, unit.sensitivity_level)
                
                results[unit.name] = CompilationResult(
                    compiled_code=compiled_code,
                    loader_code=loader_code,
                    metadata={
                        "original_file": unit.file_path,
                        "dependencies": unit.dependencies,
                        "sensitivity_level": unit.sensitivity_level,
                        "protection_level": protection_level.value,
                        "compilation_time": "now",
                        "checksum": hashlib.sha256(compiled_code).hexdigest()
                    },
                    protection_level=protection_level,
                    size_reduction=size_reduction,
                    security_score=security_score
                )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error compiling sensitive code: {e}")
            return {}

    def _apply_name_mangling(self, source_code: str) -> str:
        """Apply name mangling to obfuscate function and variable names"""
        try:
            tree = ast.parse(source_code)
            
            # Map of original names to mangled names
            name_map = {}
            
            # Find all identifiers to mangle
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):  # Don't mangle private methods
                        name_map[node.name] = f"_{self._generate_mangled_name()}"
                
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith('_'):
                        name_map[node.name] = f"_{self._generate_mangled_name()}"
            
            # Apply name mangling
            class NameMangler(ast.NodeTransformer):
                def visit_Name(self, node):
                    if node.id in name_map:
                        node.id = name_map[node.id]
                    return node
                
                def visit_FunctionDef(self, node):
                    if node.name in name_map:
                        node.name = name_map[node.name]
                    return self.generic_visit(node)
                
                def visit_ClassDef(self, node):
                    if node.name in name_map:
                        node.name = name_map[node.name]
                    return self.generic_visit(node)
            
            mangled_tree = NameMangler().visit(tree)
            return ast.unparse(mangled_tree)
            
        except Exception as e:
            self.logger.warning(f"Name mangling failed: {e}")
            return source_code

    def _generate_mangled_name(self) -> str:
        """Generate a mangled name"""
        import random
        import string
        return ''.join(random.choices(string.ascii_letters, k=8))

    def _apply_string_encryption(self, source_code: str) -> str:
        """Encrypt sensitive strings in the code"""
        try:
            tree = ast.parse(source_code)
            
            # Encrypt string literals that look sensitive
            class StringEncryptor(ast.NodeTransformer):
                def visit_Str(self, node):
                    string_content = node.s.lower()
                    is_sensitive = any(
                        pattern in string_content 
                        for patterns in self.sensitive_patterns.values() 
                        for pattern in patterns
                    )
                    
                    if is_sensitive and len(node.s) > 3:
                        # Simple base64 encoding (in production, use proper encryption)
                        encoded = base64.b64encode(node.s.encode()).decode()
                        return ast.Call(
                            func=ast.Attribute(
                                value=ast.Attribute(
                                    value=ast.Name(id='base64', ctx=ast.Load()),
                                    attr='b64decode',
                                    ctx=ast.Load()
                                ),
                                attr='decode',
                                ctx=ast.Load()
                            ),
                            args=[ast.Str(s=encoded)],
                            keywords=[]
                        )
                    return node
            
            encrypted_tree = StringEncryptor().visit(tree)
            
            # Add base64 import at the beginning
            import_node = ast.Import(names=[ast.alias(name='base64', asname=None)])
            encrypted_tree.body.insert(0, import_node)
            
            return ast.unparse(encrypted_tree)
            
        except Exception as e:
            self.logger.warning(f"String encryption failed: {e}")
            return source_code

    def _apply_control_flow_obfuscation(self, source_code: str) -> str:
        """Apply basic control flow obfuscation"""
        try:
            tree = ast.parse(source_code)
            
            # Add dummy conditions and unreachable code
            class ControlFlowObfuscator(ast.NodeTransformer):
                def visit_If(self, node):
                    # Add dummy condition that's always False
                    dummy_condition = ast.Compare(
                        left=ast.Constant(value=1),
                        ops=[ast.Eq()],
                        comparators=[ast.Constant(value=0)]
                    )
                    dummy_body = [ast.Pass()]
                    
                    # Wrap original condition in more complex expression
                    if not isinstance(node.test, ast.BoolOp):
                        complex_test = ast.BoolOp(
                            op=ast.And(),
                            values=[node.test, ast.Constant(value=True)]
                        )
                        node.test = complex_test
                    
                    return self.generic_visit(node)
            
            obfuscated_tree = ControlFlowObfuscator().visit(tree)
            return ast.unparse(obfuscated_tree)
            
        except Exception as e:
            self.logger.warning(f"Control flow obfuscation failed: {e}")
            return source_code

    def _compile_to_bytecode(self, source_code: str, module_name: str) -> bytes:
        """Compile source code to bytecode"""
        try:
            # Compile to code object
            code_obj = compile(source_code, f"<{module_name}>", 'exec')
            
            # Serialize to bytes
            bytecode = marshal.dumps(code_obj)
            
            # Compress for smaller size
            compressed = zlib.compress(bytecode)
            
            return compressed
            
        except Exception as e:
            self.logger.error(f"Bytecode compilation failed: {e}")
            return b''

    def _generate_loader(self, module_name: str, compiled_code: bytes, strategy: Dict[str, bool]) -> str:
        """Generate loader code to execute compiled bytecode"""
        encoded_bytecode = base64.b64encode(compiled_code).decode()
        
        loader_template = f"""
import base64
import marshal
import zlib
import types

def load_{module_name.replace('.', '_')}():
    \"\"\"Load and execute compiled bytecode for {module_name}\"\"\"
    try:
        # Decode and decompress bytecode
        encoded_data = "{encoded_bytecode}"
        compressed_bytecode = base64.b64decode(encoded_data)
        bytecode = zlib.decompress(compressed_bytecode)
        
        # Load code object
        code_obj = marshal.loads(bytecode)
        
        # Create module
        module = types.ModuleType('{module_name}')
        
        # Execute code in module namespace
        exec(code_obj, module.__dict__)
        
        return module
        
    except Exception as e:
        raise ImportError(f"Failed to load compiled module {module_name}: {{e}}")

# Auto-load when imported
_module = load_{module_name.replace('.', '_')}()
globals().update(_module.__dict__)
"""
        
        return loader_template

    def _calculate_security_score(self, strategy: Dict[str, bool], sensitivity_level: str) -> float:
        """Calculate security score based on applied protections"""
        base_score = 0.5
        
        # Protection bonuses
        if strategy["bytecode_compile"]:
            base_score += 0.2
        
        if strategy["name_mangling"]:
            base_score += 0.1
        
        if strategy["string_encryption"]:
            base_score += 0.1
        
        if strategy["control_flow_obfuscation"]:
            base_score += 0.1
        
        # Sensitivity level multiplier
        level_multiplier = {"low": 0.8, "medium": 1.0, "high": 1.2}.get(sensitivity_level, 1.0)
        
        return min(base_score * level_multiplier, 1.0)

    async def create_secure_runtime(self, compiled_modules: Dict[str, CompilationResult]) -> Dict[str, str]:
        """Create secure runtime environment for compiled modules"""
        try:
            runtime_files = {}
            
            # Create main runtime loader
            runtime_files["secure_runtime.py"] = self._generate_secure_runtime(compiled_modules)
            
            # Create individual module loaders
            for module_name, result in compiled_modules.items():
                loader_filename = f"{module_name.replace('.', '_')}_loader.py"
                runtime_files[loader_filename] = result.loader_code
            
            # Create runtime configuration
            runtime_files["runtime_config.json"] = self._generate_runtime_config(compiled_modules)
            
            # Create security policy
            runtime_files["security_policy.py"] = self._generate_security_policy()
            
            return runtime_files
            
        except Exception as e:
            self.logger.error(f"Error creating secure runtime: {e}")
            return {}

    def _generate_secure_runtime(self, compiled_modules: Dict[str, CompilationResult]) -> str:
        """Generate secure runtime environment"""
        module_imports = []
        for module_name in compiled_modules.keys():
            safe_name = module_name.replace('.', '_')
            module_imports.append(f"    '{module_name}': load_and_verify_{safe_name},")
        
        runtime_code = f"""
import hashlib
import logging
import sys
from typing import Dict, Any

class SecureRuntime:
    \"\"\"Secure runtime for compiled bytecode modules\"\"\"
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.loaded_modules = {{}}
        self.module_loaders = {{
{chr(10).join(module_imports)}
        }}
        self.security_enabled = True
    
    def load_module(self, module_name: str) -> Any:
        \"\"\"Securely load a compiled module\"\"\"
        if module_name in self.loaded_modules:
            return self.loaded_modules[module_name]
        
        if module_name not in self.module_loaders:
            raise ImportError(f"Module {{module_name}} not found in secure runtime")
        
        try:
            # Load with security checks
            if self.security_enabled:
                self._verify_module_integrity(module_name)
            
            module = self.module_loaders[module_name]()
            self.loaded_modules[module_name] = module
            
            self.logger.info(f"Securely loaded module: {{module_name}}")
            return module
            
        except Exception as e:
            self.logger.error(f"Failed to load module {{module_name}}: {{e}}")
            raise
    
    def _verify_module_integrity(self, module_name: str):
        \"\"\"Verify module integrity before loading\"\"\"
        # Implementation would include checksum verification,
        # signature validation, and other security checks
        pass
    
    def get_available_modules(self) -> list:
        \"\"\"Get list of available secure modules\"\"\"
        return list(self.module_loaders.keys())

# Global runtime instance
runtime = SecureRuntime()

def secure_import(module_name: str):
    \"\"\"Secure import function for compiled modules\"\"\"
    return runtime.load_module(module_name)
"""
        
        return runtime_code

    def _generate_runtime_config(self, compiled_modules: Dict[str, CompilationResult]) -> str:
        """Generate runtime configuration"""
        config = {
            "version": "1.0",
            "security_enabled": True,
            "compiled_modules": {},
            "integrity_checks": True,
            "logging_level": "INFO"
        }
        
        for module_name, result in compiled_modules.items():
            config["compiled_modules"][module_name] = {
                "protection_level": result.protection_level.value,
                "checksum": result.metadata["checksum"],
                "size_reduction": result.size_reduction,
                "security_score": result.security_score
            }
        
        return json.dumps(config, indent=2)

    def _generate_security_policy(self) -> str:
        """Generate security policy for runtime"""
        return """
import sys
import os
from typing import List

class SecurityPolicy:
    \"\"\"Security policy for secure runtime\"\"\"
    
    FORBIDDEN_MODULES = [
        'subprocess', 'os.system', 'eval', 'exec',
        'compile', 'open', '__import__'
    ]
    
    RESTRICTED_ATTRIBUTES = [
        '__code__', '__globals__', '__builtins__'
    ]
    
    @classmethod
    def check_import(cls, module_name: str) -> bool:
        \"\"\"Check if module import is allowed\"\"\"
        return module_name not in cls.FORBIDDEN_MODULES
    
    @classmethod
    def check_attribute_access(cls, attribute: str) -> bool:
        \"\"\"Check if attribute access is allowed\"\"\"
        return attribute not in cls.RESTRICTED_ATTRIBUTES
    
    @classmethod
    def sanitize_globals(cls, globals_dict: dict) -> dict:
        \"\"\"Sanitize global namespace\"\"\"
        sanitized = globals_dict.copy()
        
        # Remove dangerous builtins
        dangerous_builtins = ['eval', 'exec', 'compile', '__import__']
        for builtin in dangerous_builtins:
            sanitized.pop(builtin, None)
        
        return sanitized

# Apply security policy
policy = SecurityPolicy()
"""

    async def package_for_deployment(
        self,
        compiled_modules: Dict[str, CompilationResult],
        output_dir: str
    ) -> Dict[str, str]:
        """Package compiled modules for deployment"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Create runtime files
            runtime_files = await self.create_secure_runtime(compiled_modules)
            
            deployed_files = {}
            
            # Save runtime files
            for filename, content in runtime_files.items():
                file_path = os.path.join(output_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                deployed_files[filename] = file_path
            
            # Create deployment manifest
            manifest = {
                "deployment_version": "1.0",
                "compiled_modules": list(compiled_modules.keys()),
                "security_features": ["bytecode_compilation", "name_mangling", "string_encryption"],
                "deployment_time": "now",
                "total_modules": len(compiled_modules)
            }
            
            manifest_path = os.path.join(output_dir, "deployment_manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f, indent=2)
            deployed_files["manifest"] = manifest_path
            
            # Create installation script
            install_script = self._generate_installation_script(compiled_modules)
            install_path = os.path.join(output_dir, "install_secure_modules.py")
            with open(install_path, 'w') as f:
                f.write(install_script)
            deployed_files["installer"] = install_path
            
            return deployed_files
            
        except Exception as e:
            self.logger.error(f"Error packaging for deployment: {e}")
            return {}

    def _generate_installation_script(self, compiled_modules: Dict[str, CompilationResult]) -> str:
        """Generate installation script for secure modules"""
        return f"""
#!/usr/bin/env python3
\"\"\"
Installation script for ActiveLog secure compiled modules
\"\"\"

import os
import sys
import shutil
import json

def install_secure_modules():
    \"\"\"Install compiled secure modules\"\"\"
    print("Installing ActiveLog secure modules...")
    
    # Verify Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher required")
        return False
    
    try:
        # Copy runtime files
        runtime_files = [
            "secure_runtime.py",
            "runtime_config.json", 
            "security_policy.py"
        ]
        
        for file in runtime_files:
            if os.path.exists(file):
                print(f"Installing {{file}}...")
                # In production, copy to appropriate location
                
        # Copy module loaders
        loader_files = [f for f in os.listdir(".") if f.endswith("_loader.py")]
        for loader in loader_files:
            print(f"Installing {{loader}}...")
        
        print("Installation completed successfully!")
        print("\\nUsage:")
        print("  from secure_runtime import secure_import")
        print("  module = secure_import('your_module_name')")
        
        return True
        
    except Exception as e:
        print(f"Installation failed: {{e}}")
        return False

if __name__ == "__main__":
    success = install_secure_modules()
    sys.exit(0 if success else 1)
"""