#!/usr/bin/env python3
"""
ActiveLog Plugin Documentation Generator
"""

import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import markdown
from jinja2 import Environment, FileSystemLoader


@dataclass
class PluginDoc:
    name: str
    version: str
    description: str
    author: str
    category: str
    runtime: str
    api_endpoints: List[Dict[str, Any]]
    trigger_handlers: List[Dict[str, Any]]
    configuration: Dict[str, Any]
    permissions: Dict[str, Any]
    dependencies: Dict[str, Any]
    methods: List[Dict[str, Any]]
    properties: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    examples: List[Dict[str, Any]]
    changelog: Optional[str] = None


@dataclass
class APIEndpoint:
    path: str
    method: str
    description: str
    parameters: List[Dict[str, Any]]
    responses: List[Dict[str, Any]]
    examples: List[str]


@dataclass
class Method:
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    returns: Dict[str, Any]
    examples: List[str]
    is_async: bool
    decorators: List[str]


@dataclass
class Property:
    name: str
    type: str
    description: str
    readonly: bool
    default_value: Optional[Any]


@dataclass
class Event:
    name: str
    description: str
    parameters: Dict[str, Any]
    example: str


class DocumentationGenerator:
    """Generate comprehensive documentation for plugins"""
    
    def __init__(self, template_dir: Optional[str] = None):
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).parent / "templates"
        self.template_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
        
        # Create default templates if they don't exist
        self._create_default_templates()
    
    def generate_docs(
        self, 
        plugin_dir: str, 
        output_dir: str, 
        formats: List[str] = ["markdown", "html", "json"]
    ) -> Dict[str, str]:
        """Generate documentation in multiple formats"""
        
        plugin_path = Path(plugin_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Parse plugin
        plugin_doc = self._parse_plugin(plugin_path)
        
        generated_files = {}
        
        # Generate documentation in requested formats
        if "markdown" in formats:
            md_file = output_path / "README.md"
            self._generate_markdown(plugin_doc, md_file)
            generated_files["markdown"] = str(md_file)
        
        if "html" in formats:
            html_file = output_path / "index.html"
            self._generate_html(plugin_doc, html_file)
            generated_files["html"] = str(html_file)
        
        if "json" in formats:
            json_file = output_path / "plugin-docs.json"
            self._generate_json(plugin_doc, json_file)
            generated_files["json"] = str(json_file)
        
        if "api" in formats:
            api_file = output_path / "api.md"
            self._generate_api_docs(plugin_doc, api_file)
            generated_files["api"] = str(api_file)
        
        return generated_files
    
    def _parse_plugin(self, plugin_path: Path) -> PluginDoc:
        """Parse plugin directory and extract documentation"""
        
        # Load manifest
        manifest_path = plugin_path / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path) as f:
                manifest = json.load(f)
        else:
            manifest = {}
        
        # Determine runtime and main file
        runtime = manifest.get("runtime", {}).get("type", "unknown")
        main_file = manifest.get("main", "")
        
        # Parse source files based on runtime
        if runtime == "typescript":
            code_info = self._parse_typescript(plugin_path, main_file)
        elif runtime == "python":
            code_info = self._parse_python(plugin_path, main_file)
        else:
            code_info = self._parse_generic(plugin_path, main_file)
        
        # Load additional documentation files
        readme_content = self._load_readme(plugin_path)
        changelog_content = self._load_changelog(plugin_path)
        examples = self._load_examples(plugin_path)
        
        return PluginDoc(
            name=manifest.get("name", "Unknown Plugin"),
            version=manifest.get("version", "1.0.0"),
            description=manifest.get("description", readme_content.get("description", "")),
            author=self._format_author(manifest.get("author")),
            category=manifest.get("category", "utility"),
            runtime=runtime,
            api_endpoints=code_info.get("api_endpoints", []),
            trigger_handlers=code_info.get("trigger_handlers", []),
            configuration=manifest.get("config", {}),
            permissions=manifest.get("permissions", {}),
            dependencies=manifest.get("dependencies", {}),
            methods=code_info.get("methods", []),
            properties=code_info.get("properties", []),
            events=code_info.get("events", []),
            examples=examples,
            changelog=changelog_content
        )
    
    def _parse_typescript(self, plugin_path: Path, main_file: str) -> Dict[str, Any]:
        """Parse TypeScript plugin files"""
        
        info = {
            "api_endpoints": [],
            "trigger_handlers": [],
            "methods": [],
            "properties": [],
            "events": []
        }
        
        # Find TypeScript files
        ts_files = list(plugin_path.glob("**/*.ts"))
        if main_file and (plugin_path / main_file).exists():
            ts_files.insert(0, plugin_path / main_file)
        
        for ts_file in ts_files:
            try:
                content = ts_file.read_text(encoding='utf-8')
                file_info = self._parse_typescript_content(content)
                
                # Merge information
                for key in info:
                    info[key].extend(file_info.get(key, []))
                    
            except Exception as e:
                print(f"Error parsing {ts_file}: {e}")
        
        return info
    
    def _parse_typescript_content(self, content: str) -> Dict[str, Any]:
        """Parse TypeScript content for documentation info"""
        
        info = {
            "api_endpoints": [],
            "trigger_handlers": [],
            "methods": [],
            "properties": [],
            "events": []
        }
        
        # Simple regex-based parsing (could be improved with actual TS parser)
        
        # Find API endpoints
        api_pattern = r'@api_endpoint\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)\s*(?:.*?\n)?\s*(?:async\s+)?(\w+)\s*\('
        for match in re.finditer(api_pattern, content, re.MULTILINE | re.DOTALL):
            path, method, function_name = match.groups()
            
            # Extract function documentation
            func_doc = self._extract_ts_function_doc(content, function_name)
            
            info["api_endpoints"].append({
                "path": path,
                "method": method,
                "function": function_name,
                "description": func_doc.get("description", ""),
                "parameters": func_doc.get("parameters", []),
                "returns": func_doc.get("returns", {})
            })
        
        # Find trigger handlers
        trigger_pattern = r'@trigger_handler\s*\(\s*["\']([^"\']+)["\']\s*\)\s*(?:.*?\n)?\s*(?:async\s+)?(\w+)\s*\('
        for match in re.finditer(trigger_pattern, content, re.MULTILINE | re.DOTALL):
            trigger_type, function_name = match.groups()
            
            func_doc = self._extract_ts_function_doc(content, function_name)
            
            info["trigger_handlers"].append({
                "type": trigger_type,
                "function": function_name,
                "description": func_doc.get("description", ""),
                "parameters": func_doc.get("parameters", [])
            })
        
        # Find class methods
        method_pattern = r'(?:public|private|protected)?\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*:\s*([^{]+)'
        for match in re.finditer(method_pattern, content):
            method_name, return_type = match.groups()
            
            if method_name not in ['constructor', 'getManifest']:  # Skip common methods
                method_doc = self._extract_ts_function_doc(content, method_name)
                
                info["methods"].append({
                    "name": method_name,
                    "description": method_doc.get("description", ""),
                    "parameters": method_doc.get("parameters", []),
                    "returns": {"type": return_type.strip(), "description": ""},
                    "is_async": "async" in content,
                })
        
        return info
    
    def _parse_python(self, plugin_path: Path, main_file: str) -> Dict[str, Any]:
        """Parse Python plugin files"""
        
        info = {
            "api_endpoints": [],
            "trigger_handlers": [],
            "methods": [],
            "properties": [],
            "events": []
        }
        
        # Find Python files
        py_files = list(plugin_path.glob("**/*.py"))
        if main_file and (plugin_path / main_file).exists():
            py_files.insert(0, plugin_path / main_file)
        
        for py_file in py_files:
            try:
                content = py_file.read_text(encoding='utf-8')
                file_info = self._parse_python_content(content)
                
                # Merge information
                for key in info:
                    info[key].extend(file_info.get(key, []))
                    
            except Exception as e:
                print(f"Error parsing {py_file}: {e}")
        
        return info
    
    def _parse_python_content(self, content: str) -> Dict[str, Any]:
        """Parse Python content using AST"""
        
        info = {
            "api_endpoints": [],
            "trigger_handlers": [],
            "methods": [],
            "properties": [],
            "events": []
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    method_info = self._extract_python_method_info(node, content)
                    
                    # Check for decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'id'):
                            decorator_name = decorator.func.id
                            
                            if decorator_name == 'api_endpoint':
                                # Extract API endpoint info
                                endpoint_info = self._extract_api_endpoint_info(decorator, method_info)
                                info["api_endpoints"].append(endpoint_info)
                            
                            elif decorator_name == 'trigger_handler':
                                # Extract trigger handler info
                                trigger_info = self._extract_trigger_handler_info(decorator, method_info)
                                info["trigger_handlers"].append(trigger_info)
                    
                    # Add as regular method if not special
                    if not any(d.func.id in ['api_endpoint', 'trigger_handler'] 
                             for d in node.decorator_list 
                             if isinstance(d, ast.Call) and hasattr(d.func, 'id')):
                        info["methods"].append(method_info)
                
                elif isinstance(node, ast.ClassDef):
                    # Extract class properties
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name):
                                    prop_info = {
                                        "name": target.id,
                                        "type": "Any",  # Could be improved with type analysis
                                        "description": "",
                                        "readonly": False
                                    }
                                    info["properties"].append(prop_info)
            
        except SyntaxError as e:
            print(f"Syntax error in Python code: {e}")
        
        return info
    
    def _parse_generic(self, plugin_path: Path, main_file: str) -> Dict[str, Any]:
        """Generic parsing for unknown runtimes"""
        
        return {
            "api_endpoints": [],
            "trigger_handlers": [],
            "methods": [],
            "properties": [],
            "events": []
        }
    
    def _extract_ts_function_doc(self, content: str, function_name: str) -> Dict[str, Any]:
        """Extract JSDoc-style documentation for TypeScript function"""
        
        # Find the function
        pattern = rf'(/\*\*.*?\*/)\s*(?:.*?\n)?\s*(?:async\s+)?{function_name}\s*\('
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            return {"description": "", "parameters": [], "returns": {}}
        
        doc_comment = match.group(1)
        
        # Parse JSDoc
        description = ""
        parameters = []
        returns = {}
        
        # Extract description
        desc_match = re.search(r'/\*\*\s*\n\s*\*\s*([^@]*?)\s*(?:\*\s*@|\*/)', doc_comment, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()
            description = re.sub(r'\n\s*\*\s*', ' ', description)
        
        # Extract @param tags
        param_pattern = r'@param\s+\{([^}]+)\}\s+(\w+)\s+(.+)'
        for match in re.finditer(param_pattern, doc_comment):
            param_type, param_name, param_desc = match.groups()
            parameters.append({
                "name": param_name,
                "type": param_type,
                "description": param_desc.strip()
            })
        
        # Extract @returns tag
        return_match = re.search(r'@returns?\s+\{([^}]+)\}\s+(.+)', doc_comment)
        if return_match:
            return_type, return_desc = return_match.groups()
            returns = {
                "type": return_type,
                "description": return_desc.strip()
            }
        
        return {
            "description": description,
            "parameters": parameters,
            "returns": returns
        }
    
    def _extract_python_method_info(self, node: ast.FunctionDef, content: str) -> Dict[str, Any]:
        """Extract method information from Python AST node"""
        
        # Get docstring
        docstring = ast.get_docstring(node) or ""
        
        # Parse parameters
        parameters = []
        for arg in node.args.args:
            if arg.arg != 'self':  # Skip self parameter
                param_info = {
                    "name": arg.arg,
                    "type": "Any",  # Could extract from type annotations
                    "description": ""
                }
                
                # Extract type annotation if present
                if arg.annotation:
                    if isinstance(arg.annotation, ast.Name):
                        param_info["type"] = arg.annotation.id
                    elif isinstance(arg.annotation, ast.Constant):
                        param_info["type"] = str(arg.annotation.value)
                
                parameters.append(param_info)
        
        # Parse docstring for parameter descriptions
        if docstring:
            # Simple parsing - could be improved with proper docstring parser
            for param in parameters:
                pattern = rf'{param["name"]}\s*:\s*(.+)'
                match = re.search(pattern, docstring, re.IGNORECASE)
                if match:
                    param["description"] = match.group(1).strip()
        
        return {
            "name": node.name,
            "description": docstring.split('\n')[0] if docstring else "",
            "parameters": parameters,
            "returns": {"type": "Any", "description": ""},
            "is_async": isinstance(node, ast.AsyncFunctionDef)
        }
    
    def _extract_api_endpoint_info(self, decorator: ast.Call, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract API endpoint information from decorator"""
        
        path = ""
        method = "GET"
        
        if decorator.args:
            if len(decorator.args) > 0 and isinstance(decorator.args[0], ast.Constant):
                path = decorator.args[0].value
            if len(decorator.args) > 1 and isinstance(decorator.args[1], ast.Constant):
                method = decorator.args[1].value
        
        return {
            "path": path,
            "method": method,
            "function": method_info["name"],
            "description": method_info["description"],
            "parameters": method_info["parameters"],
            "returns": method_info["returns"]
        }
    
    def _extract_trigger_handler_info(self, decorator: ast.Call, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract trigger handler information from decorator"""
        
        trigger_type = ""
        
        if decorator.args and isinstance(decorator.args[0], ast.Constant):
            trigger_type = decorator.args[0].value
        
        return {
            "type": trigger_type,
            "function": method_info["name"],
            "description": method_info["description"],
            "parameters": method_info["parameters"]
        }
    
    def _load_readme(self, plugin_path: Path) -> Dict[str, Any]:
        """Load and parse README file"""
        
        readme_files = ["README.md", "README.txt", "README.rst", "readme.md"]
        
        for readme_file in readme_files:
            readme_path = plugin_path / readme_file
            if readme_path.exists():
                content = readme_path.read_text(encoding='utf-8')
                
                # Extract description from first paragraph
                lines = content.split('\n')
                description = ""
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        description = line.strip()
                        break
                
                return {
                    "content": content,
                    "description": description
                }
        
        return {"content": "", "description": ""}
    
    def _load_changelog(self, plugin_path: Path) -> Optional[str]:
        """Load changelog file"""
        
        changelog_files = ["CHANGELOG.md", "CHANGELOG.txt", "HISTORY.md", "changelog.md"]
        
        for changelog_file in changelog_files:
            changelog_path = plugin_path / changelog_file
            if changelog_path.exists():
                return changelog_path.read_text(encoding='utf-8')
        
        return None
    
    def _load_examples(self, plugin_path: Path) -> List[Dict[str, Any]]:
        """Load example files"""
        
        examples = []
        examples_dir = plugin_path / "examples"
        
        if examples_dir.exists():
            for example_file in examples_dir.glob("**/*"):
                if example_file.is_file() and example_file.suffix in ['.js', '.ts', '.py', '.json']:
                    try:
                        content = example_file.read_text(encoding='utf-8')
                        examples.append({
                            "name": example_file.stem,
                            "file": str(example_file.relative_to(plugin_path)),
                            "language": example_file.suffix[1:],  # Remove dot
                            "content": content
                        })
                    except Exception:
                        pass
        
        return examples
    
    def _format_author(self, author_data: Any) -> str:
        """Format author information"""
        
        if isinstance(author_data, str):
            return author_data
        elif isinstance(author_data, dict):
            name = author_data.get("name", "Unknown")
            email = author_data.get("email")
            url = author_data.get("url")
            
            result = name
            if email:
                result += f" <{email}>"
            if url:
                result += f" ({url})"
            
            return result
        
        return "Unknown"
    
    def _generate_markdown(self, plugin_doc: PluginDoc, output_file: Path):
        """Generate Markdown documentation"""
        
        template = self.jinja_env.get_template("plugin_readme.md.j2")
        content = template.render(plugin=plugin_doc)
        
        output_file.write_text(content, encoding='utf-8')
    
    def _generate_html(self, plugin_doc: PluginDoc, output_file: Path):
        """Generate HTML documentation"""
        
        template = self.jinja_env.get_template("plugin_docs.html.j2")
        content = template.render(plugin=plugin_doc)
        
        output_file.write_text(content, encoding='utf-8')
    
    def _generate_json(self, plugin_doc: PluginDoc, output_file: Path):
        """Generate JSON documentation"""
        
        # Convert to serializable dict
        doc_dict = {
            "name": plugin_doc.name,
            "version": plugin_doc.version,
            "description": plugin_doc.description,
            "author": plugin_doc.author,
            "category": plugin_doc.category,
            "runtime": plugin_doc.runtime,
            "api_endpoints": plugin_doc.api_endpoints,
            "trigger_handlers": plugin_doc.trigger_handlers,
            "configuration": plugin_doc.configuration,
            "permissions": plugin_doc.permissions,
            "dependencies": plugin_doc.dependencies,
            "methods": plugin_doc.methods,
            "properties": plugin_doc.properties,
            "events": plugin_doc.events,
            "examples": plugin_doc.examples,
            "changelog": plugin_doc.changelog,
            "generated_at": datetime.utcnow().isoformat()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False)
    
    def _generate_api_docs(self, plugin_doc: PluginDoc, output_file: Path):
        """Generate API reference documentation"""
        
        template = self.jinja_env.get_template("api_reference.md.j2")
        content = template.render(plugin=plugin_doc)
        
        output_file.write_text(content, encoding='utf-8')
    
    def _create_default_templates(self):
        """Create default Jinja2 templates"""
        
        # Plugin README template
        readme_template = '''# {{ plugin.name }}

{{ plugin.description }}

**Version:** {{ plugin.version }}  
**Author:** {{ plugin.author }}  
**Category:** {{ plugin.category }}  
**Runtime:** {{ plugin.runtime }}

## Installation

```bash
activelog plugin install {{ plugin.name }}
```

## Configuration

{% if plugin.configuration.schema -%}
```json
{{ plugin.configuration.defaults | tojson(indent=2) }}
```

### Configuration Options

{% for prop, details in plugin.configuration.schema.properties.items() -%}
- **{{ prop }}** ({{ details.type }}): {{ details.description or "No description" }}
  {% if details.default %}- Default: `{{ details.default }}`{% endif %}
{% endfor %}
{%- endif %}

## API Endpoints

{% for endpoint in plugin.api_endpoints -%}
### {{ endpoint.method }} {{ endpoint.path }}

{{ endpoint.description }}

**Function:** `{{ endpoint.function }}`

{% if endpoint.parameters -%}
**Parameters:**
{% for param in endpoint.parameters -%}
- `{{ param.name }}` ({{ param.type }}): {{ param.description }}
{% endfor %}
{%- endif %}

{% if endpoint.returns -%}
**Returns:** {{ endpoint.returns.type }} - {{ endpoint.returns.description }}
{%- endif %}

---
{% endfor %}

## Trigger Handlers

{% for trigger in plugin.trigger_handlers -%}
### {{ trigger.type }}

{{ trigger.description }}

**Function:** `{{ trigger.function }}`

{% if trigger.parameters -%}
**Parameters:**
{% for param in trigger.parameters -%}
- `{{ param.name }}` ({{ param.type }}): {{ param.description }}
{% endfor %}
{%- endif %}

---
{% endfor %}

## Methods

{% for method in plugin.methods -%}
### {{ method.name }}{% if method.is_async %} (async){% endif %}

{{ method.description }}

{% if method.parameters -%}
**Parameters:**
{% for param in method.parameters -%}
- `{{ param.name }}` ({{ param.type }}): {{ param.description }}
{% endfor %}
{%- endif %}

{% if method.returns -%}
**Returns:** {{ method.returns.type }} - {{ method.returns.description }}
{%- endif %}

---
{% endfor %}

## Examples

{% for example in plugin.examples -%}
### {{ example.name }}

**File:** `{{ example.file }}`

```{{ example.language }}
{{ example.content }}
```

---
{% endfor %}

## Permissions Required

{% for service in plugin.permissions.services -%}
- {{ service }}
{% endfor %}

{% if plugin.permissions.network.enabled -%}
- Network access
{% endif %}

{% if plugin.permissions.database.read or plugin.permissions.database.write -%}
- Database access ({% if plugin.permissions.database.read %}read{% endif %}{% if plugin.permissions.database.read and plugin.permissions.database.write %}, {% endif %}{% if plugin.permissions.database.write %}write{% endif %})
{% endif %}

{% if plugin.changelog -%}
## Changelog

{{ plugin.changelog }}
{% endif %}

## Support

For support and issues, please contact {{ plugin.author }}.
'''
        
        readme_template_path = self.template_dir / "plugin_readme.md.j2"
        if not readme_template_path.exists():
            readme_template_path.write_text(readme_template)
        
        # HTML template
        html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ plugin.name }} - Plugin Documentation</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }
        .section { margin-bottom: 40px; }
        .endpoint, .method { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .meta { color: #666; font-size: 0.9em; }
        h1, h2, h3 { color: #333; }
        .badge { background: #007acc; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ plugin.name }}</h1>
        <p>{{ plugin.description }}</p>
        <div class="meta">
            <strong>Version:</strong> {{ plugin.version }} | 
            <strong>Author:</strong> {{ plugin.author }} | 
            <strong>Category:</strong> {{ plugin.category }} | 
            <strong>Runtime:</strong> {{ plugin.runtime }}
        </div>
    </div>

    {% if plugin.api_endpoints -%}
    <div class="section">
        <h2>API Endpoints</h2>
        {% for endpoint in plugin.api_endpoints -%}
        <div class="endpoint">
            <h3><span class="badge">{{ endpoint.method }}</span> {{ endpoint.path }}</h3>
            <p>{{ endpoint.description }}</p>
            <p><strong>Function:</strong> <code>{{ endpoint.function }}</code></p>
            
            {% if endpoint.parameters -%}
            <h4>Parameters:</h4>
            <ul>
            {% for param in endpoint.parameters -%}
                <li><code>{{ param.name }}</code> ({{ param.type }}): {{ param.description }}</li>
            {% endfor %}
            </ul>
            {%- endif %}
        </div>
        {% endfor %}
    </div>
    {%- endif %}

    {% if plugin.methods -%}
    <div class="section">
        <h2>Methods</h2>
        {% for method in plugin.methods -%}
        <div class="method">
            <h3>{{ method.name }}{% if method.is_async %} <span class="badge">async</span>{% endif %}</h3>
            <p>{{ method.description }}</p>
            
            {% if method.parameters -%}
            <h4>Parameters:</h4>
            <ul>
            {% for param in method.parameters -%}
                <li><code>{{ param.name }}</code> ({{ param.type }}): {{ param.description }}</li>
            {% endfor %}
            </ul>
            {%- endif %}
        </div>
        {% endfor %}
    </div>
    {%- endif %}

    {% if plugin.examples -%}
    <div class="section">
        <h2>Examples</h2>
        {% for example in plugin.examples -%}
        <h3>{{ example.name }}</h3>
        <p><strong>File:</strong> <code>{{ example.file }}</code></p>
        <pre><code>{{ example.content }}</code></pre>
        {% endfor %}
    </div>
    {%- endif %}

    <div class="section">
        <h2>Installation</h2>
        <pre><code>activelog plugin install {{ plugin.name }}</code></pre>
    </div>
</body>
</html>'''
        
        html_template_path = self.template_dir / "plugin_docs.html.j2"
        if not html_template_path.exists():
            html_template_path.write_text(html_template)
        
        # API reference template
        api_template = '''# {{ plugin.name }} API Reference

This document provides detailed API reference for the {{ plugin.name }} plugin.

## Overview

- **Plugin Name:** {{ plugin.name }}
- **Version:** {{ plugin.version }}
- **Runtime:** {{ plugin.runtime }}

## API Endpoints

{% for endpoint in plugin.api_endpoints -%}
## {{ endpoint.method }} {{ endpoint.path }}

{{ endpoint.description }}

### Request

{% if endpoint.parameters -%}
**Parameters:**

| Name | Type | Description |
|------|------|-------------|
{% for param in endpoint.parameters -%}
| `{{ param.name }}` | {{ param.type }} | {{ param.description }} |
{% endfor %}
{%- else %}
No parameters required.
{%- endif %}

### Response

{% if endpoint.returns -%}
**Type:** `{{ endpoint.returns.type }}`

{{ endpoint.returns.description }}
{%- else %}
Response format not documented.
{%- endif %}

### Example

```bash
curl -X {{ endpoint.method }} /api/plugins/{{ plugin.name }}{{ endpoint.path }}
```

---

{% endfor %}

## Trigger Handlers

{% for trigger in plugin.trigger_handlers -%}
## {{ trigger.type }}

{{ trigger.description }}

### Event Data

{% if trigger.parameters -%}
| Field | Type | Description |
|-------|------|-------------|
{% for param in trigger.parameters -%}
| `{{ param.name }}` | {{ param.type }} | {{ param.description }} |
{% endfor %}
{%- else %}
No specific event data structure documented.
{%- endif %}

---

{% endfor %}

## Plugin Methods

{% for method in plugin.methods -%}
### {{ method.name }}(){% if method.is_async %} (async){% endif %}

{{ method.description }}

{% if method.parameters -%}
**Parameters:**

| Name | Type | Description |
|------|------|-------------|
{% for param in method.parameters -%}
| `{{ param.name }}` | {{ param.type }} | {{ param.description }} |
{% endfor %}
{%- endif %}

{% if method.returns -%}
**Returns:** `{{ method.returns.type }}` - {{ method.returns.description }}
{%- endif %}

---

{% endfor %}
'''
        
        api_template_path = self.template_dir / "api_reference.md.j2"
        if not api_template_path.exists():
            api_template_path.write_text(api_template)


def main():
    """Command-line interface for documentation generator"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: generator.py <plugin_directory> <output_directory> [formats...]")
        print("Formats: markdown, html, json, api")
        sys.exit(1)
    
    plugin_dir = sys.argv[1]
    output_dir = sys.argv[2]
    formats = sys.argv[3:] if len(sys.argv) > 3 else ["markdown", "html"]
    
    generator = DocumentationGenerator()
    
    try:
        generated_files = generator.generate_docs(plugin_dir, output_dir, formats)
        
        print("Documentation generated successfully:")
        for format_name, file_path in generated_files.items():
            print(f"  {format_name}: {file_path}")
    
    except Exception as e:
        print(f"Error generating documentation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()