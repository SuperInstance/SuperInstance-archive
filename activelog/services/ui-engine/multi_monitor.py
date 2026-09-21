"""
Multi-Monitor Support System
Handles multiple display configurations and adaptive UI layouts
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime
import json
import uuid
import asyncio

class Display(BaseModel):
    """Represents a physical display"""
    id: str
    name: str
    width: int
    height: int
    dpi: float
    position: Tuple[int, int]  # (x, y) offset from primary
    is_primary: bool = False
    orientation: str = "landscape"  # landscape, portrait
    color_profile: str = "sRGB"
    refresh_rate: int = 60
    
class DisplayConfiguration(BaseModel):
    """Configuration for multiple displays"""
    id: str
    name: str
    displays: List[Display]
    layout_mode: str  # "extended", "mirrored", "single"
    primary_display_id: str
    created_at: datetime
    metadata: Dict[str, Any] = {}

class WindowLayout(BaseModel):
    """Layout definition for a window on specific display"""
    id: str
    display_id: str
    x: int
    y: int
    width: int
    height: int
    z_index: int = 1
    is_maximized: bool = False
    is_minimized: bool = False
    is_fullscreen: bool = False

class UILayout(BaseModel):
    """UI layout across multiple displays"""
    id: str
    name: str
    display_config_id: str
    windows: List[WindowLayout]
    adaptive_rules: List[Dict[str, Any]] = []
    created_at: datetime
    metadata: Dict[str, Any] = {}

class ViewportManager(BaseModel):
    """Manages viewports for different display areas"""
    id: str
    display_id: str
    viewports: List[Dict[str, Any]]  # Viewport definitions
    active_viewport: str
    scaling_factor: float = 1.0

class MultiMonitorManager:
    """Multi-monitor support system"""
    
    def __init__(self):
        self.display_configs: Dict[str, DisplayConfiguration] = {}
        self.ui_layouts: Dict[str, UILayout] = {}
        self.viewport_managers: Dict[str, ViewportManager] = {}
        self.active_config_id: Optional[str] = None
        self.display_detection_enabled = True
        self.adaptive_scaling = True
        
    async def detect_displays(self) -> List[Display]:
        """Detect connected displays (simulated for demo)"""
        # In real implementation, this would use system APIs
        mock_displays = [
            Display(
                id="display_1",
                name="Primary Monitor",
                width=1920,
                height=1080,
                dpi=96.0,
                position=(0, 0),
                is_primary=True,
                refresh_rate=60
            ),
            Display(
                id="display_2", 
                name="Secondary Monitor",
                width=1920,
                height=1080,
                dpi=96.0,
                position=(1920, 0),
                refresh_rate=60
            ),
            Display(
                id="display_3",
                name="Vertical Monitor",
                width=1080,
                height=1920,
                dpi=109.0,
                position=(3840, 0),
                orientation="portrait",
                refresh_rate=75
            )
        ]
        
        return mock_displays
    
    def create_display_configuration(self, name: str, displays: List[Display], 
                                   layout_mode: str = "extended") -> str:
        """Create a new display configuration"""
        config_id = str(uuid.uuid4())
        
        # Find primary display
        primary_display_id = next(
            (d.id for d in displays if d.is_primary),
            displays[0].id if displays else ""
        )
        
        config = DisplayConfiguration(
            id=config_id,
            name=name,
            displays=displays,
            layout_mode=layout_mode,
            primary_display_id=primary_display_id,
            created_at=datetime.now()
        )
        
        self.display_configs[config_id] = config
        return config_id
    
    def update_display_configuration(self, config_id: str, updates: Dict[str, Any]):
        """Update display configuration"""
        if config_id not in self.display_configs:
            raise ValueError(f"Display configuration {config_id} not found")
        
        config = self.display_configs[config_id]
        
        if "name" in updates:
            config.name = updates["name"]
        if "layout_mode" in updates:
            config.layout_mode = updates["layout_mode"]
        if "displays" in updates:
            config.displays = [Display(**d) for d in updates["displays"]]
    
    def get_display_configuration(self, config_id: str) -> Optional[DisplayConfiguration]:
        """Get display configuration by ID"""
        return self.display_configs.get(config_id)
    
    def set_active_configuration(self, config_id: str):
        """Set the active display configuration"""
        if config_id not in self.display_configs:
            raise ValueError(f"Display configuration {config_id} not found")
        
        self.active_config_id = config_id
        
        # Create viewport managers for each display
        config = self.display_configs[config_id]
        for display in config.displays:
            self._create_viewport_manager(display)
    
    def _create_viewport_manager(self, display: Display):
        """Create viewport manager for a display"""
        viewport_id = str(uuid.uuid4())
        
        # Create default viewports based on display properties
        viewports = []
        
        if display.orientation == "landscape":
            # Standard landscape viewports
            viewports = [
                {
                    "id": "main",
                    "name": "Main Area",
                    "x": 0,
                    "y": 0,
                    "width": display.width,
                    "height": display.height,
                    "type": "main"
                },
                {
                    "id": "sidebar",
                    "name": "Sidebar",
                    "x": display.width - 300,
                    "y": 0,
                    "width": 300,
                    "height": display.height,
                    "type": "sidebar"
                },
                {
                    "id": "toolbar",
                    "name": "Toolbar",
                    "x": 0,
                    "y": 0,
                    "width": display.width,
                    "height": 60,
                    "type": "toolbar"
                }
            ]
        else:  # Portrait
            viewports = [
                {
                    "id": "main",
                    "name": "Main Area",
                    "x": 0,
                    "y": 0,
                    "width": display.width,
                    "height": display.height,
                    "type": "main"
                },
                {
                    "id": "top_panel",
                    "name": "Top Panel",
                    "x": 0,
                    "y": 0,
                    "width": display.width,
                    "height": 200,
                    "type": "panel"
                },
                {
                    "id": "bottom_panel",
                    "name": "Bottom Panel",
                    "x": 0,
                    "y": display.height - 200,
                    "width": display.width,
                    "height": 200,
                    "type": "panel"
                }
            ]
        
        # Calculate scaling factor based on DPI
        scaling_factor = display.dpi / 96.0 if self.adaptive_scaling else 1.0
        
        manager = ViewportManager(
            id=viewport_id,
            display_id=display.id,
            viewports=viewports,
            active_viewport="main",
            scaling_factor=scaling_factor
        )
        
        self.viewport_managers[display.id] = manager
    
    def create_ui_layout(self, name: str, display_config_id: str) -> str:
        """Create a new UI layout"""
        if display_config_id not in self.display_configs:
            raise ValueError(f"Display configuration {display_config_id} not found")
        
        layout_id = str(uuid.uuid4())
        layout = UILayout(
            id=layout_id,
            name=name,
            display_config_id=display_config_id,
            windows=[],
            created_at=datetime.now()
        )
        
        self.ui_layouts[layout_id] = layout
        return layout_id
    
    def add_window_to_layout(self, layout_id: str, display_id: str, 
                            x: int, y: int, width: int, height: int, 
                            window_id: str = None) -> str:
        """Add a window to UI layout"""
        if layout_id not in self.ui_layouts:
            raise ValueError(f"UI layout {layout_id} not found")
        
        layout = self.ui_layouts[layout_id]
        
        # Validate display exists in configuration
        config = self.display_configs[layout.display_config_id]
        display = next((d for d in config.displays if d.id == display_id), None)
        if not display:
            raise ValueError(f"Display {display_id} not found in configuration")
        
        window_layout_id = window_id or str(uuid.uuid4())
        window = WindowLayout(
            id=window_layout_id,
            display_id=display_id,
            x=x,
            y=y,
            width=width,
            height=height
        )
        
        layout.windows.append(window)
        return window_layout_id
    
    def move_window(self, layout_id: str, window_id: str, x: int, y: int):
        """Move window within layout"""
        if layout_id not in self.ui_layouts:
            raise ValueError(f"UI layout {layout_id} not found")
        
        layout = self.ui_layouts[layout_id]
        window = next((w for w in layout.windows if w.id == window_id), None)
        if window:
            window.x = x
            window.y = y
    
    def resize_window(self, layout_id: str, window_id: str, width: int, height: int):
        """Resize window in layout"""
        if layout_id not in self.ui_layouts:
            raise ValueError(f"UI layout {layout_id} not found")
        
        layout = self.ui_layouts[layout_id]
        window = next((w for w in layout.windows if w.id == window_id), None)
        if window:
            window.width = width
            window.height = height
    
    def move_window_to_display(self, layout_id: str, window_id: str, target_display_id: str):
        """Move window to different display"""
        if layout_id not in self.ui_layouts:
            raise ValueError(f"UI layout {layout_id} not found")
        
        layout = self.ui_layouts[layout_id]
        window = next((w for w in layout.windows if w.id == window_id), None)
        if not window:
            raise ValueError(f"Window {window_id} not found")
        
        # Validate target display
        config = self.display_configs[layout.display_config_id]
        target_display = next((d for d in config.displays if d.id == target_display_id), None)
        if not target_display:
            raise ValueError(f"Target display {target_display_id} not found")
        
        # Adjust position for new display
        old_display = next((d for d in config.displays if d.id == window.display_id), None)
        if old_display and target_display:
            # Calculate relative position
            rel_x = window.x - old_display.position[0]
            rel_y = window.y - old_display.position[1]
            
            # Set new position on target display
            window.x = target_display.position[0] + rel_x
            window.y = target_display.position[1] + rel_y
            window.display_id = target_display_id
            
            # Ensure window fits in new display
            max_x = target_display.position[0] + target_display.width - window.width
            max_y = target_display.position[1] + target_display.height - window.height
            
            window.x = min(max_x, max(target_display.position[0], window.x))
            window.y = min(max_y, max(target_display.position[1], window.y))
    
    def get_optimal_layout_for_displays(self, display_ids: List[str], 
                                       window_count: int) -> Dict[str, Any]:
        """Get optimal window layout for given displays"""
        if not self.active_config_id:
            return {"error": "No active display configuration"}
        
        config = self.display_configs[self.active_config_id]
        displays = [d for d in config.displays if d.id in display_ids]
        
        if not displays:
            return {"error": "No valid displays found"}
        
        # Calculate total screen real estate
        total_area = sum(d.width * d.height for d in displays)
        area_per_window = total_area // window_count if window_count > 0 else 0
        
        # Simple layout algorithm
        layouts = []
        windows_placed = 0
        
        for display in displays:
            display_area = display.width * display.height
            windows_for_display = max(1, int((display_area / total_area) * window_count))
            
            if display.orientation == "landscape":
                # Tile horizontally
                window_width = display.width // windows_for_display
                window_height = display.height
                
                for i in range(windows_for_display):
                    if windows_placed >= window_count:
                        break
                    
                    layouts.append({
                        "display_id": display.id,
                        "x": display.position[0] + (i * window_width),
                        "y": display.position[1],
                        "width": window_width,
                        "height": window_height
                    })
                    windows_placed += 1
            else:  # Portrait
                # Tile vertically
                window_width = display.width
                window_height = display.height // windows_for_display
                
                for i in range(windows_for_display):
                    if windows_placed >= window_count:
                        break
                    
                    layouts.append({
                        "display_id": display.id,
                        "x": display.position[0],
                        "y": display.position[1] + (i * window_height),
                        "width": window_width,
                        "height": window_height
                    })
                    windows_placed += 1
        
        return {"layouts": layouts}
    
    def get_display_metrics(self, display_id: str) -> Dict[str, Any]:
        """Get metrics for a specific display"""
        if not self.active_config_id:
            return {"error": "No active display configuration"}
        
        config = self.display_configs[self.active_config_id]
        display = next((d for d in config.displays if d.id == display_id), None)
        
        if not display:
            return {"error": "Display not found"}
        
        viewport_manager = self.viewport_managers.get(display_id)
        
        return {
            "display": display.dict(),
            "viewports": viewport_manager.viewports if viewport_manager else [],
            "scaling_factor": viewport_manager.scaling_factor if viewport_manager else 1.0,
            "total_area": display.width * display.height,
            "aspect_ratio": display.width / display.height
        }
    
    def adapt_ui_for_displays(self, ui_config: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt UI configuration for current display setup"""
        if not self.active_config_id:
            return ui_config
        
        config = self.display_configs[self.active_config_id]
        adapted_config = ui_config.copy()
        
        # Apply display-specific adaptations
        for display in config.displays:
            display_key = f"display_{display.id}"
            
            if display_key not in adapted_config:
                adapted_config[display_key] = {}
            
            # Adapt for DPI scaling
            if self.adaptive_scaling and display.dpi != 96.0:
                scale_factor = display.dpi / 96.0
                adapted_config[display_key]["scale_factor"] = scale_factor
            
            # Adapt for orientation
            if display.orientation == "portrait":
                adapted_config[display_key]["orientation_optimized"] = True
                adapted_config[display_key]["recommended_layout"] = "vertical"
            else:
                adapted_config[display_key]["recommended_layout"] = "horizontal"
            
            # Color profile adaptation
            adapted_config[display_key]["color_profile"] = display.color_profile
            
            # Refresh rate optimization
            adapted_config[display_key]["refresh_rate"] = display.refresh_rate
        
        return adapted_config
    
    def create_mirrored_layout(self, source_display_id: str, target_display_ids: List[str]) -> str:
        """Create mirrored layout across displays"""
        layout_id = str(uuid.uuid4())
        
        if not self.active_config_id:
            raise ValueError("No active display configuration")
        
        config = self.display_configs[self.active_config_id]
        source_display = next((d for d in config.displays if d.id == source_display_id), None)
        
        if not source_display:
            raise ValueError(f"Source display {source_display_id} not found")
        
        layout = UILayout(
            id=layout_id,
            name=f"Mirrored Layout from {source_display.name}",
            display_config_id=self.active_config_id,
            windows=[],
            created_at=datetime.now(),
            metadata={"type": "mirrored", "source_display": source_display_id}
        )
        
        # Add windows for each target display
        for target_id in target_display_ids:
            target_display = next((d for d in config.displays if d.id == target_id), None)
            if target_display:
                # Calculate scaling to fit content
                scale_x = target_display.width / source_display.width
                scale_y = target_display.height / source_display.height
                scale = min(scale_x, scale_y)  # Maintain aspect ratio
                
                # Center the mirrored content
                scaled_width = int(source_display.width * scale)
                scaled_height = int(source_display.height * scale)
                offset_x = (target_display.width - scaled_width) // 2
                offset_y = (target_display.height - scaled_height) // 2
                
                window = WindowLayout(
                    id=str(uuid.uuid4()),
                    display_id=target_id,
                    x=target_display.position[0] + offset_x,
                    y=target_display.position[1] + offset_y,
                    width=scaled_width,
                    height=scaled_height
                )
                
                layout.windows.append(window)
        
        self.ui_layouts[layout_id] = layout
        return layout_id
    
    def export_display_configuration(self, config_id: str) -> Dict:
        """Export display configuration"""
        if config_id not in self.display_configs:
            raise ValueError(f"Display configuration {config_id} not found")
        
        config = self.display_configs[config_id]
        return {
            "configuration": config.dict(),
            "layouts": [layout.dict() for layout in self.ui_layouts.values() 
                       if layout.display_config_id == config_id],
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0.0"
            }
        }
    
    def import_display_configuration(self, config_data: Dict) -> str:
        """Import display configuration"""
        config_dict = config_data.get("configuration", {})
        config = DisplayConfiguration(**config_dict)
        config.id = str(uuid.uuid4())  # Generate new ID
        
        self.display_configs[config.id] = config
        
        # Import associated layouts
        layouts_data = config_data.get("layouts", [])
        for layout_data in layouts_data:
            layout = UILayout(**layout_data)
            layout.id = str(uuid.uuid4())
            layout.display_config_id = config.id
            self.ui_layouts[layout.id] = layout
        
        return config.id
    
    def list_display_configurations(self) -> List[Dict]:
        """List all display configurations"""
        return [
            {
                "id": config.id,
                "name": config.name,
                "display_count": len(config.displays),
                "layout_mode": config.layout_mode,
                "is_active": config.id == self.active_config_id
            }
            for config in self.display_configs.values()
        ]
    
    def get_ui_layout(self, layout_id: str) -> Optional[UILayout]:
        """Get UI layout by ID"""
        return self.ui_layouts.get(layout_id)