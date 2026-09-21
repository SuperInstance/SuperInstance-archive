"""
ActiveLog Plugin SDK - Utilities for Python
"""

import json
import re
import semver
from typing import Any, Dict, List, Optional, Tuple
from .types import PluginManifest, PluginCategory, ValidationError


def validate_manifest(manifest_data: Dict[str, Any]) -> PluginManifest:
    """Validate plugin manifest against schema"""
    errors = []
    
    # Required fields
    required_fields = ['name', 'version', 'description', 'main', 'runtime', 'permissions']
    for field in required_fields:
        if field not in manifest_data:
            errors.append(f'{field} is required')
    
    # Validate name format
    if 'name' in manifest_data:
        name = manifest_data['name']
        if not isinstance(name, str) or not re.match(r'^[a-z][a-z0-9-]*$', name):
            errors.append('name must be lowercase with hyphens only')
    
    # Validate version format
    if 'version' in manifest_data:
        version = manifest_data['version']
        if not isinstance(version, str) or not is_valid_semver(version):
            errors.append('version must be in semver format (x.y.z)')
    
    # Validate category
    if 'category' in manifest_data:
        category = manifest_data['category']
        valid_categories = [cat.value for cat in PluginCategory]
        if category not in valid_categories:
            errors.append(f'category must be one of: {", ".join(valid_categories)}')
    
    # Validate runtime
    if 'runtime' in manifest_data:
        runtime = manifest_data['runtime']
        if not isinstance(runtime, dict) or 'type' not in runtime:
            errors.append('runtime must have a type field')
    
    # Validate permissions structure
    if 'permissions' in manifest_data:
        permissions = manifest_data['permissions']
        if not isinstance(permissions, dict):
            errors.append('permissions must be an object')
    
    if errors:
        raise ValidationError('manifest', '; '.join(errors))
    
    # Convert to PluginManifest object (simplified - in production use proper serialization)
    return manifest_data


def generate_plugin_template(
    name: str,
    display_name: Optional[str] = None,
    description: str = "",
    author: str = "",
    category: str = "utility",
    runtime: str = "python"
) -> Dict[str, Any]:
    """Generate plugin template with manifest and code"""
    
    # Generate manifest
    manifest = {
        "name": name,
        "version": "1.0.0",
        "display_name": display_name or name,
        "description": description,
        "author": {
            "name": author
        },
        "category": category,
        "main": "main.py",
        "runtime": {
            "type": runtime,
            "environment": "python3"
        },
        "permissions": {
            "network": {"enabled": False},
            "filesystem": {"temp": True},
            "database": {"read": False, "write": False},
            "services": []
        },
        "resources": {
            "cpu": 0.5,
            "memory": "256MB",
            "disk": "100MB",
            "timeout": 60
        }
    }
    
    # Generate Python code
    class_name = to_pascal_case(name)
    code = f"""import asyncio
from typing import Any, Dict
from activelog_plugin_sdk import Plugin, PluginContext, TriggerEvent, TriggerResult


class {class_name}Plugin(Plugin):
    def get_manifest(self) -> Dict[str, Any]:
        return {json.dumps(manifest, indent=4)}

    async def on_load(self, context: PluginContext) -> None:
        await super().on_load(context)
        self.log('info', '{display_name or name} plugin loaded')

    async def on_activate(self, context: PluginContext) -> None:
        await super().on_activate(context)
        self.log('info', '{display_name or name} plugin activated')
        
        # Initialize your plugin here

    async def on_trigger(self, event: TriggerEvent, context: PluginContext) -> TriggerResult:
        self.log('info', f'Trigger received: {{event.type}}')
        
        try:
            # Handle trigger event
            if event.type == 'file-upload':
                return await self.handle_file_upload(event.data)
            elif event.type == 'schedule':
                return await self.handle_scheduled_task(event.data)
            else:
                return TriggerResult(success=False, error='Unsupported trigger type')
        except Exception as error:
            self.log('error', f'Trigger execution failed: {{str(error)}}')
            return TriggerResult(success=False, error=str(error))

    async def handle_file_upload(self, data: Any) -> TriggerResult:
        # Implement file upload handling
        self.log('info', f'Handling file upload: {{data}}')
        return TriggerResult(success=True)

    async def handle_scheduled_task(self, data: Any) -> TriggerResult:
        # Implement scheduled task handling
        self.log('info', f'Handling scheduled task: {{data}}')
        return TriggerResult(success=True)


# Export plugin class
plugin_class = {class_name}Plugin
"""
    
    return {
        'manifest': manifest,
        'code': code
    }


def to_pascal_case(kebab_str: str) -> str:
    """Convert kebab-case to PascalCase"""
    return ''.join(word.capitalize() for word in kebab_str.split('-'))


def to_kebab_case(pascal_str: str) -> str:
    """Convert PascalCase to kebab-case"""
    return re.sub('([A-Z])', r'-\1', pascal_str).lower().lstrip('-')


def parse_memory_size(size: str) -> int:
    """Parse memory size string to bytes"""
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([KMGT]?)B?$', size, re.IGNORECASE)
    if not match:
        raise ValidationError('memory', 'Invalid memory size format')
    
    value = float(match.group(1))
    unit = match.group(2).upper()
    
    multipliers = {
        '': 1,
        'K': 1024,
        'M': 1024 * 1024,
        'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024
    }
    
    return int(value * multipliers.get(unit, 1))


def format_bytes(bytes_count: int) -> str:
    """Format bytes to human readable string"""
    if bytes_count == 0:
        return '0 B'
    
    k = 1024
    sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    i = int(len(bin(bytes_count)) - 3) // 10
    i = min(i, len(sizes) - 1)
    
    return f"{bytes_count / (k ** i):.2f} {sizes[i]}"


def is_valid_semver(version: str) -> bool:
    """Validate semantic version format"""
    try:
        semver.VersionInfo.parse(version)
        return True
    except ValueError:
        # Fallback to regex if semver library not available
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
        return bool(re.match(pattern, version))


def compare_semver(version1: str, version2: str) -> int:
    """Compare semantic versions (-1, 0, 1)"""
    try:
        v1 = semver.VersionInfo.parse(version1)
        v2 = semver.VersionInfo.parse(version2)
        return v1.compare(v2)
    except (ValueError, AttributeError):
        # Fallback to simple comparison
        parts1 = [int(x) for x in version1.split('.')]
        parts2 = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(parts1), len(parts2))):
            p1 = parts1[i] if i < len(parts1) else 0
            p2 = parts2[i] if i < len(parts2) else 0
            
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        
        return 0


def satisfies_range(version: str, range_spec: str) -> bool:
    """Check if version satisfies range specification"""
    try:
        return semver.match(version, range_spec)
    except (ValueError, AttributeError):
        # Simple fallback implementation
        if range_spec.startswith('^'):
            base_version = range_spec[1:]
            return compare_semver(version, base_version) >= 0
        elif range_spec.startswith('~'):
            base_version = range_spec[1:]
            return compare_semver(version, base_version) >= 0
        else:
            return version == range_spec


def generate_plugin_id(name: str, version: str) -> str:
    """Generate unique plugin ID"""
    return f"{name}@{version}"


def parse_plugin_id(plugin_id: str) -> Tuple[str, str]:
    """Parse plugin ID into name and version"""
    if '@' not in plugin_id:
        raise ValidationError('pluginId', 'Invalid plugin ID format')
    
    parts = plugin_id.rsplit('@', 1)
    if len(parts) != 2:
        raise ValidationError('pluginId', 'Invalid plugin ID format')
    
    return parts[0], parts[1]


def sanitize_plugin_name(name: str) -> str:
    """Sanitize plugin name for use as identifier"""
    return re.sub(r'[^a-z0-9-]', '-', name.lower()).strip('-')


def has_permission(manifest: Dict[str, Any], permission: str) -> bool:
    """Check if plugin has required permission"""
    permissions = manifest.get('permissions', {})
    
    if permission == 'network':
        return permissions.get('network', {}).get('enabled', False)
    elif permission == 'database:read':
        return permissions.get('database', {}).get('read', False)
    elif permission == 'database:write':
        return permissions.get('database', {}).get('write', False)
    elif permission == 'filesystem:read':
        return bool(permissions.get('filesystem', {}).get('read', []))
    elif permission == 'filesystem:write':
        return bool(permissions.get('filesystem', {}).get('write', []))
    
    return False


def calculate_resource_requirements(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate plugin resource requirements"""
    resources = manifest.get('resources', {})
    
    return {
        'cpu': resources.get('cpu', 0.5),
        'memory_bytes': parse_memory_size(resources.get('memory', '256MB')),
        'disk_bytes': parse_memory_size(resources.get('disk', '100MB')),
        'network_bytes': parse_memory_size(resources.get('network', '10MB')),
        'timeout_ms': (resources.get('timeout', 60)) * 1000
    }


def validate_plugin_config(config: Any, schema: Dict[str, Any]) -> bool:
    """Validate plugin configuration against JSON schema"""
    # Basic validation - in production, use jsonschema library
    try:
        import jsonschema
        jsonschema.validate(config, schema)
        return True
    except ImportError:
        # Fallback to basic validation
        return _basic_config_validation(config, schema)
    except Exception:
        return False


def _basic_config_validation(config: Any, schema: Dict[str, Any]) -> bool:
    """Basic configuration validation"""
    if schema.get('type') == 'object' and not isinstance(config, dict):
        return False
    
    if 'required' in schema:
        for required_field in schema['required']:
            if required_field not in config:
                return False
    
    if 'properties' in schema:
        for prop_name, prop_schema in schema['properties'].items():
            if prop_name in config:
                if not _validate_property(config[prop_name], prop_schema):
                    return False
    
    return True


def _validate_property(value: Any, schema: Dict[str, Any]) -> bool:
    """Validate individual property"""
    prop_type = schema.get('type')
    
    if prop_type == 'string' and not isinstance(value, str):
        return False
    elif prop_type == 'number' and not isinstance(value, (int, float)):
        return False
    elif prop_type == 'boolean' and not isinstance(value, bool):
        return False
    elif prop_type == 'array' and not isinstance(value, list):
        return False
    elif prop_type == 'object' and not isinstance(value, dict):
        return False
    
    # Additional validations
    if 'minLength' in schema and isinstance(value, str) and len(value) < schema['minLength']:
        return False
    if 'maxLength' in schema and isinstance(value, str) and len(value) > schema['maxLength']:
        return False
    if 'minimum' in schema and isinstance(value, (int, float)) and value < schema['minimum']:
        return False
    if 'maximum' in schema and isinstance(value, (int, float)) and value > schema['maximum']:
        return False
    
    return True


def extract_plugin_metadata(code: str) -> Dict[str, Any]:
    """Extract metadata from plugin code (decorators, etc.)"""
    import ast
    
    metadata = {
        'api_endpoints': [],
        'trigger_handlers': [],
        'event_listeners': [],
        'scheduled_tasks': [],
        'webhook_handlers': []
    }
    
    try:
        tree = ast.parse(code)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for decorator metadata
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and hasattr(decorator.func, 'id'):
                        decorator_name = decorator.func.id
                        
                        if decorator_name == 'api_endpoint':
                            metadata['api_endpoints'].append(node.name)
                        elif decorator_name == 'trigger_handler':
                            metadata['trigger_handlers'].append(node.name)
                        elif decorator_name == 'event_listener':
                            metadata['event_listeners'].append(node.name)
                        elif decorator_name == 'scheduled_task':
                            metadata['scheduled_tasks'].append(node.name)
                        elif decorator_name == 'webhook_handler':
                            metadata['webhook_handlers'].append(node.name)
    
    except SyntaxError:
        pass  # Invalid Python code
    
    return metadata


def create_plugin_archive(plugin_dir: str, output_path: str) -> str:
    """Create a plugin archive (.zip) for distribution"""
    import zipfile
    import os
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(plugin_dir):
            # Skip hidden directories and files
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                archive_name = os.path.relpath(file_path, plugin_dir)
                zipf.write(file_path, archive_name)
    
    return output_path