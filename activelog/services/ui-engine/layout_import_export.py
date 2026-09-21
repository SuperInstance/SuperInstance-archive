"""
Layout Import/Export System
Comprehensive system for importing and exporting UI layouts
"""

from typing import Dict, List, Optional, Any, Union, IO
from pydantic import BaseModel, Field
from datetime import datetime
import json
import uuid
import zipfile
import io
import base64
import tempfile
import os
from pathlib import Path
import yaml
import xml.etree.ElementTree as ET

class ExportFormat(str):
    JSON = "json"
    YAML = "yaml"
    XML = "xml"
    ZIP = "zip"
    FIGMA = "figma"
    SKETCH = "sketch"
    ADOBE_XD = "adobe_xd"

class ImportSource(str):
    FILE = "file"
    URL = "url"
    CLIPBOARD = "clipboard"
    FIGMA_API = "figma_api"
    SKETCH_API = "sketch_api"

class LayoutAsset(BaseModel):
    """Asset referenced in layout"""
    id: str
    type: str  # image, icon, font, etc.
    name: str
    url: Optional[str] = None
    data: Optional[str] = None  # base64 encoded data
    mime_type: str = ""
    size: int = 0

class LayoutExport(BaseModel):
    """Complete layout export package"""
    id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    
    # Layout data
    layout: Dict[str, Any]
    components: List[Dict[str, Any]]
    theme: Optional[Dict[str, Any]] = None
    
    # Assets
    assets: List[LayoutAsset] = []
    
    # Metadata
    created_by: str
    created_at: datetime
    exported_at: datetime
    export_format: str
    
    # Compatibility
    ui_engine_version: str = "1.0.0"
    framework_compatibility: List[str] = []
    
    # Export settings
    include_assets: bool = True
    include_theme: bool = True
    minified: bool = False

class LayoutImport(BaseModel):
    """Layout import record"""
    id: str
    source: ImportSource
    source_data: str  # file path, URL, or data
    
    # Import settings
    merge_strategy: str = "replace"  # replace, merge, skip
    prefix_components: bool = False
    component_prefix: str = "imported_"
    
    # Results
    imported_layouts: List[str] = []
    imported_components: List[str] = []
    imported_assets: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []
    
    imported_by: str
    imported_at: datetime

class LayoutConverter:
    """Converts between different layout formats"""
    
    @staticmethod
    def to_json(layout_export: LayoutExport, pretty: bool = True) -> str:
        """Convert to JSON format"""
        data = layout_export.dict()
        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, separators=(',', ':'), default=str)
    
    @staticmethod
    def to_yaml(layout_export: LayoutExport) -> str:
        """Convert to YAML format"""
        data = layout_export.dict()
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)
    
    @staticmethod
    def to_xml(layout_export: LayoutExport) -> str:
        """Convert to XML format"""
        root = ET.Element("layout_export")
        
        # Add metadata
        metadata = ET.SubElement(root, "metadata")
        ET.SubElement(metadata, "id").text = layout_export.id
        ET.SubElement(metadata, "name").text = layout_export.name
        ET.SubElement(metadata, "version").text = layout_export.version
        ET.SubElement(metadata, "created_by").text = layout_export.created_by
        ET.SubElement(metadata, "exported_at").text = layout_export.exported_at.isoformat()
        
        # Add layout
        layout_elem = ET.SubElement(root, "layout")
        LayoutConverter._dict_to_xml(layout_export.layout, layout_elem)
        
        # Add components
        components_elem = ET.SubElement(root, "components")
        for component in layout_export.components:
            comp_elem = ET.SubElement(components_elem, "component")
            LayoutConverter._dict_to_xml(component, comp_elem)
        
        # Add theme if present
        if layout_export.theme:
            theme_elem = ET.SubElement(root, "theme")
            LayoutConverter._dict_to_xml(layout_export.theme, theme_elem)
        
        return ET.tostring(root, encoding='unicode', method='xml')
    
    @staticmethod
    def _dict_to_xml(data: Dict[str, Any], parent: ET.Element):
        """Convert dictionary to XML elements"""
        for key, value in data.items():
            if isinstance(value, dict):
                elem = ET.SubElement(parent, key)
                LayoutConverter._dict_to_xml(value, elem)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        elem = ET.SubElement(parent, key)
                        LayoutConverter._dict_to_xml(item, elem)
                    else:
                        elem = ET.SubElement(parent, key)
                        elem.text = str(item)
            else:
                elem = ET.SubElement(parent, key)
                elem.text = str(value)
    
    @staticmethod
    def from_json(json_data: str) -> LayoutExport:
        """Create from JSON data"""
        data = json.loads(json_data)
        return LayoutExport(**data)
    
    @staticmethod
    def from_yaml(yaml_data: str) -> LayoutExport:
        """Create from YAML data"""
        data = yaml.safe_load(yaml_data)
        return LayoutExport(**data)
    
    @staticmethod
    def from_figma(figma_data: Dict[str, Any]) -> LayoutExport:
        """Convert from Figma design data"""
        # Simplified Figma import - would need actual Figma API integration
        layout_id = str(uuid.uuid4())
        
        components = []
        layout = {"type": "container", "children": []}
        
        # Process Figma nodes
        if "document" in figma_data:
            components, layout = LayoutConverter._process_figma_nodes(figma_data["document"])
        
        return LayoutExport(
            id=layout_id,
            name=figma_data.get("name", "Imported from Figma"),
            description="Imported from Figma design",
            layout=layout,
            components=components,
            created_by="figma_import",
            created_at=datetime.now(),
            exported_at=datetime.now(),
            export_format="figma",
            framework_compatibility=["react", "vue", "angular"]
        )
    
    @staticmethod
    def _process_figma_nodes(node: Dict[str, Any], components: List[Dict] = None, 
                           layout: Dict[str, Any] = None) -> tuple:
        """Process Figma nodes recursively"""
        if components is None:
            components = []
        if layout is None:
            layout = {"type": "container", "children": []}
        
        node_type = node.get("type", "")
        
        if node_type == "FRAME" or node_type == "GROUP":
            # Container component
            component = {
                "id": str(uuid.uuid4()),
                "type": "container",
                "name": node.get("name", "Container"),
                "properties": {
                    "width": node.get("absoluteBoundingBox", {}).get("width", 100),
                    "height": node.get("absoluteBoundingBox", {}).get("height", 100),
                    "backgroundColor": LayoutConverter._figma_color_to_hex(
                        node.get("backgroundColor", {})
                    )
                }
            }
            components.append(component)
            layout["children"].append({"component_id": component["id"]})
            
        elif node_type == "TEXT":
            # Text component
            component = {
                "id": str(uuid.uuid4()),
                "type": "text",
                "name": node.get("name", "Text"),
                "properties": {
                    "text": node.get("characters", "Text"),
                    "fontSize": node.get("style", {}).get("fontSize", 16),
                    "fontFamily": node.get("style", {}).get("fontFamily", "sans-serif"),
                    "color": LayoutConverter._figma_color_to_hex(
                        node.get("fills", [{}])[0].get("color", {})
                    )
                }
            }
            components.append(component)
            layout["children"].append({"component_id": component["id"]})
            
        elif node_type == "RECTANGLE" or node_type == "ELLIPSE":
            # Shape component
            component = {
                "id": str(uuid.uuid4()),
                "type": "shape",
                "name": node.get("name", "Shape"),
                "properties": {
                    "shape": node_type.lower(),
                    "width": node.get("absoluteBoundingBox", {}).get("width", 100),
                    "height": node.get("absoluteBoundingBox", {}).get("height", 100),
                    "backgroundColor": LayoutConverter._figma_color_to_hex(
                        node.get("fills", [{}])[0].get("color", {})
                    )
                }
            }
            components.append(component)
            layout["children"].append({"component_id": component["id"]})
        
        # Process children
        if "children" in node:
            for child in node["children"]:
                LayoutConverter._process_figma_nodes(child, components, layout)
        
        return components, layout
    
    @staticmethod
    def _figma_color_to_hex(color: Dict[str, float]) -> str:
        """Convert Figma color to hex"""
        if not color:
            return "#000000"
        
        r = int(color.get("r", 0) * 255)
        g = int(color.get("g", 0) * 255) 
        b = int(color.get("b", 0) * 255)
        
        return f"#{r:02x}{g:02x}{b:02x}"

class LayoutImportExport:
    """Layout import/export management system"""
    
    def __init__(self):
        self.exports: Dict[str, LayoutExport] = {}
        self.imports: Dict[str, LayoutImport] = {}
        self.assets: Dict[str, LayoutAsset] = {}
        self.temp_dir = tempfile.mkdtemp()
        
    def export_layout(self, layout_data: Dict[str, Any], components: List[Dict[str, Any]],
                     name: str, created_by: str, export_format: str = ExportFormat.JSON,
                     include_assets: bool = True, include_theme: bool = True,
                     theme_data: Dict[str, Any] = None) -> str:
        """Export layout to specified format"""
        
        export_id = str(uuid.uuid4())
        
        # Collect assets
        assets = []
        if include_assets:
            assets = self._collect_assets(layout_data, components)
        
        # Create export
        export_obj = LayoutExport(
            id=export_id,
            name=name,
            layout=layout_data,
            components=components,
            theme=theme_data if include_theme else None,
            assets=assets,
            created_by=created_by,
            created_at=datetime.now(),
            exported_at=datetime.now(),
            export_format=export_format,
            include_assets=include_assets,
            include_theme=include_theme
        )
        
        self.exports[export_id] = export_obj
        return export_id
    
    def get_export_data(self, export_id: str, format_type: str = None) -> Union[str, bytes]:
        """Get export data in specified format"""
        export_obj = self.exports.get(export_id)
        if not export_obj:
            raise ValueError("Export not found")
        
        format_type = format_type or export_obj.export_format
        
        if format_type == ExportFormat.JSON:
            return LayoutConverter.to_json(export_obj)
        elif format_type == ExportFormat.YAML:
            return LayoutConverter.to_yaml(export_obj)
        elif format_type == ExportFormat.XML:
            return LayoutConverter.to_xml(export_obj)
        elif format_type == ExportFormat.ZIP:
            return self._create_zip_package(export_obj)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    
    def _create_zip_package(self, export_obj: LayoutExport) -> bytes:
        """Create ZIP package with layout and assets"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add main layout file
            zip_file.writestr("layout.json", LayoutConverter.to_json(export_obj))
            
            # Add metadata
            metadata = {
                "name": export_obj.name,
                "version": export_obj.version,
                "created_by": export_obj.created_by,
                "exported_at": export_obj.exported_at.isoformat(),
                "ui_engine_version": export_obj.ui_engine_version
            }
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
            
            # Add assets
            if export_obj.assets:
                for asset in export_obj.assets:
                    if asset.data:
                        asset_data = base64.b64decode(asset.data)
                        zip_file.writestr(f"assets/{asset.name}", asset_data)
            
            # Add theme if included
            if export_obj.theme:
                zip_file.writestr("theme.json", json.dumps(export_obj.theme, indent=2))
            
            # Add installation guide
            guide = self._generate_installation_guide(export_obj)
            zip_file.writestr("README.md", guide)
        
        zip_buffer.seek(0)
        return zip_buffer.read()
    
    def _generate_installation_guide(self, export_obj: LayoutExport) -> str:
        """Generate installation guide"""
        return f"""# {export_obj.name}

{export_obj.description}

## Installation

1. Import the layout.json file into your UI Engine project
2. Apply the included theme if desired
3. Install any required assets
4. Test the layout in your application

## Contents

- Layout: {len(export_obj.components)} components
- Theme: {'Included' if export_obj.theme else 'Not included'}
- Assets: {len(export_obj.assets)} files

## Compatibility

- UI Engine: {export_obj.ui_engine_version}+
- Frameworks: {', '.join(export_obj.framework_compatibility)}

## Version

{export_obj.version} - Exported on {export_obj.exported_at.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def _collect_assets(self, layout_data: Dict[str, Any], components: List[Dict[str, Any]]) -> List[LayoutAsset]:
        """Collect all assets referenced in layout"""
        assets = []
        asset_urls = set()
        
        # Collect from components
        for component in components:
            properties = component.get("properties", {})
            
            # Image sources
            if "src" in properties or "image" in properties:
                url = properties.get("src") or properties.get("image")
                if url and url not in asset_urls:
                    asset = LayoutAsset(
                        id=str(uuid.uuid4()),
                        type="image",
                        name=os.path.basename(url),
                        url=url
                    )
                    assets.append(asset)
                    asset_urls.add(url)
            
            # Icon references
            if "icon" in properties:
                icon = properties.get("icon")
                if icon and icon not in asset_urls:
                    asset = LayoutAsset(
                        id=str(uuid.uuid4()),
                        type="icon",
                        name=icon,
                        url=f"/icons/{icon}.svg"
                    )
                    assets.append(asset)
                    asset_urls.add(icon)
        
        return assets
    
    def import_layout(self, source: ImportSource, source_data: Union[str, bytes, IO],
                     imported_by: str, merge_strategy: str = "replace",
                     prefix_components: bool = False) -> str:
        """Import layout from various sources"""
        
        import_id = str(uuid.uuid4())
        
        import_record = LayoutImport(
            id=import_id,
            source=source,
            source_data=str(source_data) if isinstance(source_data, str) else "binary_data",
            merge_strategy=merge_strategy,
            prefix_components=prefix_components,
            imported_by=imported_by,
            imported_at=datetime.now()
        )
        
        try:
            # Process based on source type
            if source == ImportSource.FILE:
                layout_export = self._import_from_file(source_data)
            elif source == ImportSource.URL:
                layout_export = self._import_from_url(source_data)
            elif source == ImportSource.CLIPBOARD:
                layout_export = self._import_from_clipboard(source_data)
            elif source == ImportSource.FIGMA_API:
                layout_export = self._import_from_figma(source_data)
            else:
                raise ValueError(f"Unsupported import source: {source}")
            
            # Apply import settings
            if prefix_components:
                self._prefix_component_ids(layout_export, import_record.component_prefix)
            
            # Store import results
            import_record.imported_layouts = [layout_export.id]
            import_record.imported_components = [c.get("id") for c in layout_export.components]
            import_record.imported_assets = [a.id for a in layout_export.assets]
            
        except Exception as e:
            import_record.errors.append(str(e))
        
        self.imports[import_id] = import_record
        return import_id
    
    def _import_from_file(self, file_data: Union[str, bytes, IO]) -> LayoutExport:
        """Import from file"""
        if isinstance(file_data, str):
            # File path
            with open(file_data, 'r', encoding='utf-8') as f:
                content = f.read()
        elif isinstance(file_data, bytes):
            content = file_data.decode('utf-8')
        else:
            content = file_data.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
        
        # Detect format and parse
        content = content.strip()
        
        if content.startswith('{') or content.startswith('['):
            # JSON format
            return LayoutConverter.from_json(content)
        elif content.startswith('---') or 'layout:' in content:
            # YAML format
            return LayoutConverter.from_yaml(content)
        elif content.startswith('<?xml') or content.startswith('<layout_export'):
            # XML format - would need implementation
            raise NotImplementedError("XML import not yet implemented")
        else:
            raise ValueError("Unknown file format")
    
    def _import_from_url(self, url: str) -> LayoutExport:
        """Import from URL"""
        # This would require HTTP client implementation
        raise NotImplementedError("URL import not yet implemented")
    
    def _import_from_clipboard(self, clipboard_data: str) -> LayoutExport:
        """Import from clipboard data"""
        try:
            data = json.loads(clipboard_data)
            return LayoutExport(**data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in clipboard data")
    
    def _import_from_figma(self, figma_url_or_data: str) -> LayoutExport:
        """Import from Figma"""
        # This would require Figma API integration
        # For now, create a mock import
        mock_figma_data = {
            "name": "Figma Design",
            "document": {
                "type": "DOCUMENT",
                "children": [{
                    "type": "FRAME",
                    "name": "Main Frame",
                    "absoluteBoundingBox": {"width": 400, "height": 300},
                    "backgroundColor": {"r": 1, "g": 1, "b": 1},
                    "children": []
                }]
            }
        }
        
        return LayoutConverter.from_figma(mock_figma_data)
    
    def _prefix_component_ids(self, layout_export: LayoutExport, prefix: str):
        """Add prefix to component IDs"""
        id_mapping = {}
        
        # Update component IDs
        for component in layout_export.components:
            old_id = component["id"]
            new_id = f"{prefix}{old_id}"
            component["id"] = new_id
            id_mapping[old_id] = new_id
        
        # Update references in layout
        self._update_id_references(layout_export.layout, id_mapping)
    
    def _update_id_references(self, data: Any, id_mapping: Dict[str, str]):
        """Update ID references recursively"""
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "component_id" and value in id_mapping:
                    data[key] = id_mapping[value]
                elif isinstance(value, (dict, list)):
                    self._update_id_references(value, id_mapping)
        elif isinstance(data, list):
            for item in data:
                self._update_id_references(item, id_mapping)
    
    def get_import_status(self, import_id: str) -> Optional[LayoutImport]:
        """Get import status"""
        return self.imports.get(import_id)
    
    def list_exports(self, created_by: str = None) -> List[Dict[str, Any]]:
        """List all exports"""
        exports = []
        for export in self.exports.values():
            if created_by is None or export.created_by == created_by:
                exports.append({
                    "id": export.id,
                    "name": export.name,
                    "description": export.description,
                    "version": export.version,
                    "created_by": export.created_by,
                    "exported_at": export.exported_at.isoformat(),
                    "format": export.export_format,
                    "component_count": len(export.components),
                    "asset_count": len(export.assets),
                    "has_theme": export.theme is not None
                })
        
        return sorted(exports, key=lambda e: e["exported_at"], reverse=True)
    
    def list_imports(self, imported_by: str = None) -> List[Dict[str, Any]]:
        """List all imports"""
        imports = []
        for import_record in self.imports.values():
            if imported_by is None or import_record.imported_by == imported_by:
                imports.append({
                    "id": import_record.id,
                    "source": import_record.source,
                    "imported_by": import_record.imported_by,
                    "imported_at": import_record.imported_at.isoformat(),
                    "layout_count": len(import_record.imported_layouts),
                    "component_count": len(import_record.imported_components),
                    "asset_count": len(import_record.imported_assets),
                    "warning_count": len(import_record.warnings),
                    "error_count": len(import_record.errors),
                    "success": len(import_record.errors) == 0
                })
        
        return sorted(imports, key=lambda i: i["imported_at"], reverse=True)
    
    def delete_export(self, export_id: str) -> bool:
        """Delete export"""
        if export_id in self.exports:
            del self.exports[export_id]
            return True
        return False
    
    def delete_import(self, import_id: str) -> bool:
        """Delete import record"""
        if import_id in self.imports:
            del self.imports[import_id]
            return True
        return False
    
    def get_supported_formats(self) -> Dict[str, Dict[str, Any]]:
        """Get supported import/export formats"""
        return {
            "export": {
                ExportFormat.JSON: {
                    "name": "JSON",
                    "description": "JavaScript Object Notation",
                    "extensions": [".json"],
                    "mime_type": "application/json"
                },
                ExportFormat.YAML: {
                    "name": "YAML",
                    "description": "YAML Ain't Markup Language",
                    "extensions": [".yml", ".yaml"],
                    "mime_type": "application/x-yaml"
                },
                ExportFormat.XML: {
                    "name": "XML",
                    "description": "Extensible Markup Language",
                    "extensions": [".xml"],
                    "mime_type": "application/xml"
                },
                ExportFormat.ZIP: {
                    "name": "ZIP Package",
                    "description": "Complete package with assets",
                    "extensions": [".zip"],
                    "mime_type": "application/zip"
                }
            },
            "import": {
                ImportSource.FILE: {
                    "name": "File Upload",
                    "description": "Import from uploaded file",
                    "supported_formats": ["json", "yaml", "xml", "zip"]
                },
                ImportSource.URL: {
                    "name": "URL Import",
                    "description": "Import from web URL",
                    "supported_formats": ["json", "yaml"]
                },
                ImportSource.CLIPBOARD: {
                    "name": "Clipboard",
                    "description": "Import from clipboard data",
                    "supported_formats": ["json"]
                },
                ImportSource.FIGMA_API: {
                    "name": "Figma",
                    "description": "Import from Figma design",
                    "supported_formats": ["figma"]
                }
            }
        }
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except Exception:
            pass  # Ignore cleanup errors