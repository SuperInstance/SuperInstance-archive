"""
Advanced Interface Engine
Adaptive UI components, responsive design, and dynamic layouts
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from enum import Enum
from pathlib import Path
import hashlib
import base64

try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

logger = logging.getLogger(__name__)

class ComponentType(Enum):
    BUTTON = "button"
    INPUT = "input"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SLIDER = "slider"
    PROGRESS = "progress"
    CARD = "card"
    MODAL = "modal"
    TABS = "tabs"
    ACCORDION = "accordion"
    TABLE = "table"
    FORM = "form"
    NAVIGATION = "navigation"
    BREADCRUMB = "breadcrumb"
    TOAST = "toast"
    TOOLTIP = "tooltip"
    CHART = "chart"
    CUSTOM = "custom"

class LayoutType(Enum):
    GRID = "grid"
    FLEXBOX = "flexbox"
    MASONRY = "masonry"
    FLOATING = "floating"
    SIDEBAR = "sidebar"
    HEADER_FOOTER = "header_footer"
    DASHBOARD = "dashboard"
    WIZARD = "wizard"
    MOBILE_FIRST = "mobile_first"
    CUSTOM = "custom"

class ThemeVariant(Enum):
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    SEPIA = "sepia"
    BLUE_LIGHT_FILTER = "blue_light_filter"
    COLORBLIND_FRIENDLY = "colorblind_friendly"
    CUSTOM = "custom"

class DeviceCategory(Enum):
    DESKTOP = "desktop"
    TABLET = "tablet"
    MOBILE = "mobile"
    WATCH = "watch"
    TV = "tv"
    VR_AR = "vr_ar"

class InteractionMode(Enum):
    MOUSE_KEYBOARD = "mouse_keyboard"
    TOUCH = "touch"
    VOICE = "voice"
    GESTURE = "gesture"
    EYE_TRACKING = "eye_tracking"
    KEYBOARD_ONLY = "keyboard_only"
    ASSISTIVE_DEVICE = "assistive_device"

@dataclass
class UIComponent:
    component_id: str
    component_type: ComponentType
    label: str
    properties: Dict[str, Any]
    styling: Dict[str, str]
    event_handlers: Dict[str, str]
    validation_rules: List[Dict[str, Any]]
    accessibility_config: Dict[str, Any]
    responsive_config: Dict[DeviceCategory, Dict[str, Any]]
    animation_config: Optional[Dict[str, Any]] = None
    dependencies: List[str] = field(default_factory=list)
    
@dataclass 
class Layout:
    layout_id: str
    layout_type: LayoutType
    components: List[str]  # Component IDs
    grid_config: Dict[str, Any]
    responsive_breakpoints: Dict[str, int]
    spacing_config: Dict[str, Any]
    alignment_config: Dict[str, str]
    container_config: Dict[str, Any]

@dataclass
class Theme:
    theme_id: str
    name: str
    variant: ThemeVariant
    color_palette: Dict[str, str]
    typography: Dict[str, str]
    spacing: Dict[str, str]
    shadows: Dict[str, str]
    borders: Dict[str, str]
    animations: Dict[str, str]
    custom_css: Optional[str] = None

@dataclass
class UserContext:
    user_id: str
    device_category: DeviceCategory
    screen_size: Tuple[int, int]
    interaction_mode: InteractionMode
    accessibility_needs: List[str]
    preferences: Dict[str, Any]
    session_data: Dict[str, Any]
    location_context: Optional[Dict[str, Any]] = None

class UIComponentManager:
    """Advanced UI component management system"""
    
    def __init__(self):
        self.components: Dict[str, UIComponent] = {}
        self.component_templates: Dict[str, str] = {}
        self.component_library: Dict[ComponentType, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize component library
        self._initialize_component_library()
    
    def _initialize_component_library(self):
        """Initialize standard component library"""
        self.component_library = {
            ComponentType.BUTTON: {
                'template': '''
                <button id="{component_id}" 
                        class="btn btn-{variant} {size}" 
                        {disabled}
                        {accessibility_attrs}>
                    {icon}{label}
                </button>
                ''',
                'default_properties': {
                    'variant': 'primary',
                    'size': 'medium',
                    'disabled': False,
                    'icon': None
                },
                'css_classes': ['btn', 'btn-primary', 'btn-secondary', 'btn-success', 'btn-danger']
            },
            
            ComponentType.INPUT: {
                'template': '''
                <div class="input-group">
                    {label}
                    <input id="{component_id}"
                           type="{input_type}"
                           class="form-control {validation_class}"
                           placeholder="{placeholder}"
                           value="{value}"
                           {required}
                           {accessibility_attrs}>
                    {validation_feedback}
                </div>
                ''',
                'default_properties': {
                    'input_type': 'text',
                    'placeholder': '',
                    'value': '',
                    'required': False
                }
            },
            
            ComponentType.CARD: {
                'template': '''
                <div id="{component_id}" class="card {shadow} {border}">
                    {header}
                    <div class="card-body">
                        {content}
                    </div>
                    {footer}
                </div>
                ''',
                'default_properties': {
                    'shadow': 'shadow-sm',
                    'border': 'border',
                    'header': None,
                    'footer': None
                }
            },
            
            ComponentType.MODAL: {
                'template': '''
                <div id="{component_id}" class="modal fade" tabindex="-1" role="dialog">
                    <div class="modal-dialog {size}" role="document">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">{title}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                {content}
                            </div>
                            <div class="modal-footer">
                                {actions}
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                'default_properties': {
                    'size': 'modal-lg',
                    'title': 'Modal',
                    'actions': '<button type="button" class="btn btn-primary">Close</button>'
                }
            }
        }
    
    async def create_component(self, spec: Dict[str, Any]) -> UIComponent:
        """Create UI component from specification"""
        try:
            component_type = ComponentType(spec.get('type', 'button'))
            
            # Generate unique ID if not provided
            component_id = spec.get('id', f"{component_type.value}_{uuid.uuid4().hex[:8]}")
            
            # Merge with defaults
            library_config = self.component_library.get(component_type, {})
            default_props = library_config.get('default_properties', {})
            
            properties = {**default_props, **spec.get('properties', {})}
            
            component = UIComponent(
                component_id=component_id,
                component_type=component_type,
                label=spec.get('label', ''),
                properties=properties,
                styling=spec.get('styling', {}),
                event_handlers=spec.get('event_handlers', {}),
                validation_rules=spec.get('validation_rules', []),
                accessibility_config=spec.get('accessibility', {}),
                responsive_config=spec.get('responsive', {}),
                animation_config=spec.get('animation'),
                dependencies=spec.get('dependencies', [])
            )
            
            # Store component
            self.components[component_id] = component
            
            self.logger.info(f"Component created: {component_id} ({component_type.value})")
            return component
            
        except Exception as e:
            self.logger.error(f"Component creation failed: {e}")
            raise
    
    async def render_component(self, 
                              component_id: str, 
                              context: Optional[Dict[str, Any]] = None) -> str:
        """Render component to HTML"""
        try:
            if component_id not in self.components:
                return f"<div>Component not found: {component_id}</div>"
            
            component = self.components[component_id]
            library_config = self.component_library.get(component.component_type, {})
            template_str = library_config.get('template', '<div>{label}</div>')
            
            # Prepare template variables
            template_vars = {
                'component_id': component.component_id,
                'label': component.label,
                **component.properties,
                **context or {}
            }
            
            # Add accessibility attributes
            accessibility_attrs = self._generate_accessibility_attrs(component)
            template_vars['accessibility_attrs'] = accessibility_attrs
            
            # Add validation classes and feedback
            validation_class, validation_feedback = await self._generate_validation_elements(component)
            template_vars['validation_class'] = validation_class
            template_vars['validation_feedback'] = validation_feedback
            
            # Render template
            if JINJA2_AVAILABLE:
                template = Template(template_str)
                html_content = template.render(**template_vars)
            else:
                # Simple string formatting fallback
                html_content = template_str.format(**template_vars)
            
            # Apply component styling
            if component.styling:
                style_attr = '; '.join([f"{k}: {v}" for k, v in component.styling.items()])
                html_content = html_content.replace('>', f' style="{style_attr}">', 1)
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Component rendering failed: {e}")
            return f"<div>Error rendering component: {e}</div>"
    
    def _generate_accessibility_attrs(self, component: UIComponent) -> str:
        """Generate accessibility attributes"""
        attrs = []
        
        accessibility = component.accessibility_config
        
        if accessibility.get('aria_label'):
            attrs.append(f'aria-label="{accessibility["aria_label"]}"')
        
        if accessibility.get('aria_describedby'):
            attrs.append(f'aria-describedby="{accessibility["aria_describedby"]}"')
        
        if accessibility.get('role'):
            attrs.append(f'role="{accessibility["role"]}"')
        
        if accessibility.get('tabindex') is not None:
            attrs.append(f'tabindex="{accessibility["tabindex"]}"')
        
        return ' '.join(attrs)
    
    async def _generate_validation_elements(self, component: UIComponent) -> Tuple[str, str]:
        """Generate validation CSS classes and feedback elements"""
        validation_class = ""
        validation_feedback = ""
        
        # This would integrate with actual validation logic
        # For now, return empty
        return validation_class, validation_feedback

class LayoutEngine:
    """Advanced layout management system"""
    
    def __init__(self, component_manager: UIComponentManager):
        self.component_manager = component_manager
        self.layouts: Dict[str, Layout] = {}
        self.layout_templates: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize layout templates
        self._initialize_layout_templates()
    
    def _initialize_layout_templates(self):
        """Initialize standard layout templates"""
        self.layout_templates = {
            'dashboard': {
                'type': LayoutType.DASHBOARD,
                'template': '''
                <div class="dashboard-layout">
                    <header class="dashboard-header">
                        {header_components}
                    </header>
                    <aside class="dashboard-sidebar">
                        {sidebar_components}
                    </aside>
                    <main class="dashboard-main">
                        <div class="dashboard-grid">
                            {main_components}
                        </div>
                    </main>
                </div>
                ''',
                'css': '''
                .dashboard-layout { display: grid; grid-template: "header header" auto "sidebar main" 1fr / 250px 1fr; height: 100vh; }
                .dashboard-header { grid-area: header; background: var(--header-bg); padding: 1rem; }
                .dashboard-sidebar { grid-area: sidebar; background: var(--sidebar-bg); padding: 1rem; }
                .dashboard-main { grid-area: main; padding: 1rem; overflow: auto; }
                .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; }
                '''
            },
            
            'wizard': {
                'type': LayoutType.WIZARD,
                'template': '''
                <div class="wizard-layout">
                    <div class="wizard-progress">
                        {progress_component}
                    </div>
                    <div class="wizard-content">
                        {step_components}
                    </div>
                    <div class="wizard-actions">
                        {action_components}
                    </div>
                </div>
                ''',
                'css': '''
                .wizard-layout { display: flex; flex-direction: column; height: 100%; }
                .wizard-progress { flex: 0 0 auto; padding: 1rem; border-bottom: 1px solid var(--border-color); }
                .wizard-content { flex: 1; padding: 2rem; overflow: auto; }
                .wizard-actions { flex: 0 0 auto; padding: 1rem; border-top: 1px solid var(--border-color); text-align: right; }
                '''
            },
            
            'mobile_first': {
                'type': LayoutType.MOBILE_FIRST,
                'template': '''
                <div class="mobile-layout">
                    <div class="mobile-header">
                        {header_components}
                    </div>
                    <div class="mobile-content">
                        {content_components}
                    </div>
                    <div class="mobile-footer">
                        {footer_components}
                    </div>
                </div>
                ''',
                'css': '''
                .mobile-layout { display: flex; flex-direction: column; height: 100vh; }
                .mobile-header { flex: 0 0 auto; background: var(--primary-color); color: white; padding: 1rem; }
                .mobile-content { flex: 1; padding: 1rem; overflow: auto; }
                .mobile-footer { flex: 0 0 auto; background: var(--secondary-color); padding: 0.5rem; }
                @media (min-width: 768px) { 
                    .mobile-layout { grid-template: "header" auto "content" 1fr "footer" auto / 1fr; }
                    .mobile-content { padding: 2rem; }
                }
                '''
            }
        }
    
    async def create_layout(self, spec: Dict[str, Any]) -> Layout:
        """Create layout from specification"""
        try:
            layout_type = LayoutType(spec.get('type', 'grid'))
            layout_id = spec.get('id', f"layout_{uuid.uuid4().hex[:8]}")
            
            layout = Layout(
                layout_id=layout_id,
                layout_type=layout_type,
                components=spec.get('components', []),
                grid_config=spec.get('grid', {}),
                responsive_breakpoints=spec.get('breakpoints', {
                    'sm': 576,
                    'md': 768,
                    'lg': 992,
                    'xl': 1200
                }),
                spacing_config=spec.get('spacing', {}),
                alignment_config=spec.get('alignment', {}),
                container_config=spec.get('container', {})
            )
            
            self.layouts[layout_id] = layout
            
            self.logger.info(f"Layout created: {layout_id} ({layout_type.value})")
            return layout
            
        except Exception as e:
            self.logger.error(f"Layout creation failed: {e}")
            raise
    
    async def render_layout(self, 
                           layout_id: str, 
                           component_context: Optional[Dict[str, Any]] = None) -> str:
        """Render complete layout with components"""
        try:
            if layout_id not in self.layouts:
                return f"<div>Layout not found: {layout_id}</div>"
            
            layout = self.layouts[layout_id]
            
            # Get layout template
            template_config = None
            for template_name, config in self.layout_templates.items():
                if config['type'] == layout.layout_type:
                    template_config = config
                    break
            
            if not template_config:
                return await self._render_generic_layout(layout, component_context)
            
            # Render components by section
            component_sections = await self._organize_components_by_section(layout, component_context)
            
            # Render layout template
            template_vars = {
                **component_sections,
                'layout_id': layout.layout_id
            }
            
            if JINJA2_AVAILABLE:
                template = Template(template_config['template'])
                html_content = template.render(**template_vars)
            else:
                html_content = template_config['template'].format(**template_vars)
            
            # Add layout CSS
            css_content = template_config.get('css', '')
            if css_content:
                html_content = f"<style>{css_content}</style>\n{html_content}"
            
            return html_content
            
        except Exception as e:
            self.logger.error(f"Layout rendering failed: {e}")
            return f"<div>Error rendering layout: {e}</div>"
    
    async def _organize_components_by_section(self, 
                                            layout: Layout, 
                                            context: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Organize components by layout sections"""
        sections = {
            'header_components': '',
            'sidebar_components': '',
            'main_components': '',
            'content_components': '',
            'footer_components': '',
            'step_components': '',
            'action_components': '',
            'progress_component': ''
        }
        
        try:
            for component_id in layout.components:
                if component_id in self.component_manager.components:
                    component_html = await self.component_manager.render_component(component_id, context)
                    
                    # Simple section assignment based on component type
                    component = self.component_manager.components[component_id]
                    
                    if component.component_type == ComponentType.NAVIGATION:
                        sections['header_components'] += component_html
                    elif component.component_type == ComponentType.PROGRESS:
                        sections['progress_component'] = component_html
                    elif component.component_type == ComponentType.BUTTON and 'action' in component.properties.get('role', ''):
                        sections['action_components'] += component_html
                    else:
                        # Default to main/content
                        sections['main_components'] += component_html
                        sections['content_components'] += component_html
            
        except Exception as e:
            self.logger.error(f"Component organization failed: {e}")
        
        return sections

class ThemeManager:
    """Advanced theme management system"""
    
    def __init__(self):
        self.themes: Dict[str, Theme] = {}
        self.active_theme: Optional[str] = None
        self.user_themes: Dict[str, Dict[str, Theme]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize default themes
        asyncio.create_task(self._create_default_themes())
    
    async def _create_default_themes(self):
        """Create default theme variants"""
        
        # Light theme
        light_theme = Theme(
            theme_id="light",
            name="Light Theme",
            variant=ThemeVariant.LIGHT,
            color_palette={
                'primary': '#007bff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'warning': '#ffc107',
                'danger': '#dc3545',
                'info': '#17a2b8',
                'light': '#f8f9fa',
                'dark': '#343a40',
                'background': '#ffffff',
                'surface': '#f8f9fa',
                'text': '#212529',
                'text_secondary': '#6c757d'
            },
            typography={
                'font_family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
                'font_size_base': '1rem',
                'line_height_base': '1.5',
                'headings_font_weight': '500'
            },
            spacing={
                'base': '1rem',
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '3rem'
            },
            shadows={
                'sm': '0 0.125rem 0.25rem rgba(0, 0, 0, 0.075)',
                'md': '0 0.5rem 1rem rgba(0, 0, 0, 0.15)',
                'lg': '0 1rem 3rem rgba(0, 0, 0, 0.175)'
            },
            borders={
                'width': '1px',
                'color': '#dee2e6',
                'radius': '0.375rem'
            },
            animations={
                'duration': '0.15s',
                'easing': 'ease-in-out'
            }
        )
        
        # Dark theme
        dark_theme = Theme(
            theme_id="dark",
            name="Dark Theme",
            variant=ThemeVariant.DARK,
            color_palette={
                'primary': '#0d6efd',
                'secondary': '#6c757d',
                'success': '#198754',
                'warning': '#ffc107',
                'danger': '#dc3545',
                'info': '#0dcaf0',
                'light': '#f8f9fa',
                'dark': '#212529',
                'background': '#121212',
                'surface': '#1e1e1e',
                'text': '#ffffff',
                'text_secondary': '#adb5bd'
            },
            typography=light_theme.typography,
            spacing=light_theme.spacing,
            shadows={
                'sm': '0 0.125rem 0.25rem rgba(0, 0, 0, 0.3)',
                'md': '0 0.5rem 1rem rgba(0, 0, 0, 0.4)',
                'lg': '0 1rem 3rem rgba(0, 0, 0, 0.5)'
            },
            borders={
                'width': '1px',
                'color': '#495057',
                'radius': '0.375rem'
            },
            animations=light_theme.animations
        )
        
        # High contrast theme
        high_contrast_theme = Theme(
            theme_id="high_contrast",
            name="High Contrast Theme",
            variant=ThemeVariant.HIGH_CONTRAST,
            color_palette={
                'primary': '#0000ff',
                'secondary': '#808080',
                'success': '#008000',
                'warning': '#ffff00',
                'danger': '#ff0000',
                'info': '#00ffff',
                'light': '#ffffff',
                'dark': '#000000',
                'background': '#ffffff',
                'surface': '#ffffff',
                'text': '#000000',
                'text_secondary': '#000000'
            },
            typography={
                **light_theme.typography,
                'headings_font_weight': '700'
            },
            spacing=light_theme.spacing,
            shadows={
                'sm': '0 0 0 2px #000000',
                'md': '0 0 0 3px #000000',
                'lg': '0 0 0 4px #000000'
            },
            borders={
                'width': '2px',
                'color': '#000000',
                'radius': '0'
            },
            animations={
                'duration': '0s',  # No animations for accessibility
                'easing': 'linear'
            }
        )
        
        # Store themes
        self.themes['light'] = light_theme
        self.themes['dark'] = dark_theme
        self.themes['high_contrast'] = high_contrast_theme
        
        # Set default active theme
        self.active_theme = 'light'
    
    async def create_custom_theme(self, user_id: str, theme_spec: Dict[str, Any]) -> Theme:
        """Create custom theme for user"""
        try:
            theme_id = theme_spec.get('id', f"custom_{uuid.uuid4().hex[:8]}")
            
            theme = Theme(
                theme_id=theme_id,
                name=theme_spec.get('name', 'Custom Theme'),
                variant=ThemeVariant.CUSTOM,
                color_palette=theme_spec.get('colors', {}),
                typography=theme_spec.get('typography', {}),
                spacing=theme_spec.get('spacing', {}),
                shadows=theme_spec.get('shadows', {}),
                borders=theme_spec.get('borders', {}),
                animations=theme_spec.get('animations', {}),
                custom_css=theme_spec.get('custom_css')
            )
            
            # Store user theme
            if user_id not in self.user_themes:
                self.user_themes[user_id] = {}
            
            self.user_themes[user_id][theme_id] = theme
            
            self.logger.info(f"Custom theme created: {theme_id} for user {user_id}")
            return theme
            
        except Exception as e:
            self.logger.error(f"Custom theme creation failed: {e}")
            raise
    
    async def generate_css(self, theme_id: str) -> str:
        """Generate CSS for theme"""
        try:
            theme = self._get_theme(theme_id)
            if not theme:
                return ""
            
            css_parts = []
            
            # CSS Custom Properties (Variables)
            css_parts.append(":root {")
            
            # Colors
            for name, value in theme.color_palette.items():
                css_parts.append(f"  --color-{name.replace('_', '-')}: {value};")
            
            # Typography
            for name, value in theme.typography.items():
                css_parts.append(f"  --{name.replace('_', '-')}: {value};")
            
            # Spacing
            for name, value in theme.spacing.items():
                css_parts.append(f"  --spacing-{name}: {value};")
            
            # Shadows
            for name, value in theme.shadows.items():
                css_parts.append(f"  --shadow-{name}: {value};")
            
            # Borders
            for name, value in theme.borders.items():
                css_parts.append(f"  --border-{name}: {value};")
            
            # Animations
            for name, value in theme.animations.items():
                css_parts.append(f"  --animation-{name}: {value};")
            
            css_parts.append("}")
            
            # Base styles
            css_parts.extend([
                "",
                "body {",
                "  font-family: var(--font-family);",
                "  font-size: var(--font-size-base);",
                "  line-height: var(--line-height-base);",
                "  color: var(--color-text);",
                "  background-color: var(--color-background);",
                "}",
                "",
                ".btn {",
                "  border-radius: var(--border-radius);",
                "  transition: all var(--animation-duration) var(--animation-easing);",
                "}",
                "",
                ".card {",
                "  background-color: var(--color-surface);",
                "  border: var(--border-width) solid var(--border-color);",
                "  border-radius: var(--border-radius);",
                "  box-shadow: var(--shadow-sm);",
                "}"
            ])
            
            # Custom CSS
            if theme.custom_css:
                css_parts.extend(["", theme.custom_css])
            
            return "\n".join(css_parts)
            
        except Exception as e:
            self.logger.error(f"CSS generation failed: {e}")
            return ""
    
    def _get_theme(self, theme_id: str, user_id: Optional[str] = None) -> Optional[Theme]:
        """Get theme by ID, checking user themes first"""
        # Check user themes first
        if user_id and user_id in self.user_themes:
            if theme_id in self.user_themes[user_id]:
                return self.user_themes[user_id][theme_id]
        
        # Check global themes
        return self.themes.get(theme_id)

class AdaptiveInterface:
    """Adaptive interface that adjusts to user context"""
    
    def __init__(self, 
                 component_manager: UIComponentManager,
                 layout_engine: LayoutEngine,
                 theme_manager: ThemeManager):
        self.component_manager = component_manager
        self.layout_engine = layout_engine
        self.theme_manager = theme_manager
        
        self.adaptation_rules: List[Dict[str, Any]] = []
        self.user_contexts: Dict[str, UserContext] = {}
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize adaptation rules
        self._initialize_adaptation_rules()
    
    def _initialize_adaptation_rules(self):
        """Initialize adaptive interface rules"""
        self.adaptation_rules = [
            # Mobile device adaptations
            {
                'condition': lambda ctx: ctx.device_category == DeviceCategory.MOBILE,
                'adaptations': {
                    'layout_type': LayoutType.MOBILE_FIRST,
                    'component_size': 'large',
                    'spacing': 'compact',
                    'navigation': 'bottom_tabs'
                }
            },
            
            # Touch interface adaptations
            {
                'condition': lambda ctx: ctx.interaction_mode == InteractionMode.TOUCH,
                'adaptations': {
                    'button_size': 'large',
                    'touch_targets': 'minimum_44px',
                    'gestures': 'enabled'
                }
            },
            
            # High contrast needs
            {
                'condition': lambda ctx: 'high_contrast' in ctx.accessibility_needs,
                'adaptations': {
                    'theme': 'high_contrast',
                    'focus_indicators': 'enhanced',
                    'text_size': 'large'
                }
            },
            
            # Low vision adaptations
            {
                'condition': lambda ctx: 'low_vision' in ctx.accessibility_needs,
                'adaptations': {
                    'theme': 'high_contrast',
                    'text_size': 'extra_large',
                    'spacing': 'expanded',
                    'animations': 'reduced'
                }
            },
            
            # Motor impairment adaptations
            {
                'condition': lambda ctx: 'motor_impairment' in ctx.accessibility_needs,
                'adaptations': {
                    'click_targets': 'large',
                    'hover_time': 'extended',
                    'double_click': 'disabled',
                    'drag_drop': 'alternative_provided'
                }
            },
            
            # Small screen adaptations
            {
                'condition': lambda ctx: ctx.screen_size[0] < 768,
                'adaptations': {
                    'layout': 'single_column',
                    'navigation': 'collapsible',
                    'content_priority': 'progressive_disclosure'
                }
            }
        ]
    
    async def adapt_interface(self, user_id: str, user_context: UserContext) -> Dict[str, Any]:
        """Adapt interface based on user context"""
        try:
            # Store user context
            self.user_contexts[user_id] = user_context
            
            # Apply adaptation rules
            adaptations = {}
            
            for rule in self.adaptation_rules:
                try:
                    if rule['condition'](user_context):
                        adaptations.update(rule['adaptations'])
                except Exception as e:
                    self.logger.warning(f"Adaptation rule evaluation failed: {e}")
            
            # Apply user preferences
            preferences = user_context.preferences
            if preferences.get('theme'):
                adaptations['theme'] = preferences['theme']
            
            if preferences.get('font_size'):
                adaptations['font_size'] = preferences['font_size']
            
            if preferences.get('reduced_motion'):
                adaptations['animations'] = 'none'
            
            # Generate adapted configuration
            adapted_config = await self._generate_adapted_config(adaptations, user_context)
            
            self.logger.info(f"Interface adapted for user {user_id}: {len(adaptations)} adaptations applied")
            return adapted_config
            
        except Exception as e:
            self.logger.error(f"Interface adaptation failed: {e}")
            return {}
    
    async def _generate_adapted_config(self, 
                                      adaptations: Dict[str, Any],
                                      user_context: UserContext) -> Dict[str, Any]:
        """Generate adapted interface configuration"""
        try:
            config = {
                'user_id': user_context.user_id,
                'adaptations_applied': adaptations,
                'theme_id': adaptations.get('theme', 'light'),
                'layout_config': {},
                'component_overrides': {},
                'css_overrides': []
            }
            
            # Layout adaptations
            if adaptations.get('layout_type'):
                config['layout_config']['type'] = adaptations['layout_type']
            
            if adaptations.get('layout') == 'single_column':
                config['layout_config']['grid'] = {'columns': 1}
            
            # Component adaptations
            if adaptations.get('button_size') == 'large':
                config['component_overrides']['button'] = {'size': 'lg', 'min_height': '48px'}
            
            if adaptations.get('text_size') == 'large':
                config['css_overrides'].append('body { font-size: 1.2rem; }')
            elif adaptations.get('text_size') == 'extra_large':
                config['css_overrides'].append('body { font-size: 1.4rem; }')
            
            # Animation adaptations
            if adaptations.get('animations') in ['none', 'reduced']:
                config['css_overrides'].append('* { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }')
            
            return config
            
        except Exception as e:
            self.logger.error(f"Adapted config generation failed: {e}")
            return {}

class InterfaceEngine:
    """Main interface engine orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        self.component_manager = UIComponentManager()
        self.layout_engine = LayoutEngine(self.component_manager)
        self.theme_manager = ThemeManager()
        self.adaptive_interface = AdaptiveInterface(
            self.component_manager,
            self.layout_engine, 
            self.theme_manager
        )
        
        self.active_interfaces: Dict[str, Dict[str, Any]] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize interface engine"""
        try:
            self.logger.info("Initializing next-generation interface engine...")
            
            # Wait for theme manager initialization
            await asyncio.sleep(0.1)
            
            self.logger.info("Interface engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Interface engine initialization failed: {e}")
            return False
    
    async def create_interface(self, 
                              interface_spec: Dict[str, Any],
                              user_context: UserContext) -> Dict[str, Any]:
        """Create complete adaptive interface"""
        try:
            interface_id = interface_spec.get('id', f"interface_{uuid.uuid4().hex[:8]}")
            
            # Create components
            components = {}
            for comp_spec in interface_spec.get('components', []):
                component = await self.component_manager.create_component(comp_spec)
                components[component.component_id] = component
            
            # Create layout
            layout_spec = interface_spec.get('layout', {})
            layout_spec['components'] = list(components.keys())
            layout = await self.layout_engine.create_layout(layout_spec)
            
            # Apply adaptations
            adaptations = await self.adaptive_interface.adapt_interface(
                user_context.user_id,
                user_context
            )
            
            # Generate complete interface
            interface_html = await self._generate_complete_interface(
                interface_id,
                layout,
                adaptations,
                user_context
            )
            
            # Store interface
            self.active_interfaces[interface_id] = {
                'spec': interface_spec,
                'layout': layout,
                'components': components,
                'adaptations': adaptations,
                'user_context': user_context,
                'created_at': datetime.utcnow()
            }
            
            result = {
                'interface_id': interface_id,
                'html': interface_html,
                'adaptations_applied': len(adaptations.get('adaptations_applied', {})),
                'accessibility_features': self._get_accessibility_features(user_context),
                'responsive_breakpoints': layout.responsive_breakpoints,
                'theme_id': adaptations.get('theme_id', 'light')
            }
            
            self.logger.info(f"Interface created: {interface_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Interface creation failed: {e}")
            return {'error': str(e)}
    
    async def _generate_complete_interface(self,
                                         interface_id: str,
                                         layout: Layout,
                                         adaptations: Dict[str, Any],
                                         user_context: UserContext) -> str:
        """Generate complete HTML interface"""
        try:
            # Generate theme CSS
            theme_id = adaptations.get('theme_id', 'light')
            theme_css = await self.theme_manager.generate_css(theme_id)
            
            # Render layout
            layout_html = await self.layout_engine.render_layout(layout.layout_id)
            
            # Apply CSS overrides
            css_overrides = adaptations.get('css_overrides', [])
            override_css = '\n'.join(css_overrides)
            
            # Generate complete HTML document
            html_document = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Intelligent Installer Interface</title>
                
                <!-- Theme CSS -->
                <style>
                    {theme_css}
                </style>
                
                <!-- Adaptation Overrides -->
                <style>
                    {override_css}
                </style>
                
                <!-- Responsive CSS -->
                <style>
                    {self._generate_responsive_css(layout.responsive_breakpoints)}
                </style>
            </head>
            <body data-theme="{theme_id}" data-device="{user_context.device_category.value}">
                {layout_html}
                
                <!-- Interface JavaScript -->
                <script>
                    {self._generate_interface_js(interface_id, user_context)}
                </script>
            </body>
            </html>
            """
            
            return html_document
            
        except Exception as e:
            self.logger.error(f"Complete interface generation failed: {e}")
            return f"<html><body><h1>Error generating interface: {e}</h1></body></html>"
    
    def _generate_responsive_css(self, breakpoints: Dict[str, int]) -> str:
        """Generate responsive CSS"""
        css_rules = []
        
        for name, size in breakpoints.items():
            css_rules.append(f"""
            @media (min-width: {size}px) {{
                .{name}-show {{ display: block !important; }}
                .{name}-hide {{ display: none !important; }}
                .container {{ max-width: {size - 20}px; }}
            }}
            """)
        
        return '\n'.join(css_rules)
    
    def _generate_interface_js(self, interface_id: str, user_context: UserContext) -> str:
        """Generate interface JavaScript"""
        js_code = f"""
        // Interface Engine Runtime
        window.InterfaceEngine = {{
            interfaceId: '{interface_id}',
            deviceCategory: '{user_context.device_category.value}',
            interactionMode: '{user_context.interaction_mode.value}',
            
            // Accessibility helpers
            announceToScreenReader: function(message) {{
                const announcement = document.createElement('div');
                announcement.setAttribute('aria-live', 'polite');
                announcement.setAttribute('aria-atomic', 'true');
                announcement.className = 'sr-only';
                announcement.textContent = message;
                document.body.appendChild(announcement);
                setTimeout(() => document.body.removeChild(announcement), 1000);
            }},
            
            // Touch interaction helpers
            handleTouchGestures: function() {{
                // Implement touch gesture handling
                if (this.interactionMode === 'touch') {{
                    // Add touch-specific event listeners
                    document.addEventListener('touchstart', this.handleTouchStart, {{passive: true}});
                    document.addEventListener('touchmove', this.handleTouchMove, {{passive: true}});
                    document.addEventListener('touchend', this.handleTouchEnd, {{passive: true}});
                }}
            }},
            
            // Initialize interface
            init: function() {{
                this.handleTouchGestures();
                this.setupAccessibilityFeatures();
                console.log('Interface Engine initialized for:', this.interfaceId);
            }},
            
            setupAccessibilityFeatures: function() {{
                // Skip to main content link
                if (!document.querySelector('.skip-to-main')) {{
                    const skipLink = document.createElement('a');
                    skipLink.href = '#main';
                    skipLink.className = 'skip-to-main sr-only sr-only-focusable';
                    skipLink.textContent = 'Skip to main content';
                    document.body.insertBefore(skipLink, document.body.firstChild);
                }}
            }}
        }};
        
        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', () => {{
            window.InterfaceEngine.init();
        }});
        """
        
        return js_code
    
    def _get_accessibility_features(self, user_context: UserContext) -> List[str]:
        """Get accessibility features for user context"""
        features = []
        
        accessibility_needs = user_context.accessibility_needs
        
        if 'screen_reader' in accessibility_needs:
            features.extend(['aria_labels', 'semantic_markup', 'focus_management'])
        
        if 'keyboard_navigation' in accessibility_needs:
            features.extend(['keyboard_shortcuts', 'focus_indicators', 'tab_order'])
        
        if 'high_contrast' in accessibility_needs:
            features.extend(['high_contrast_theme', 'enhanced_focus'])
        
        if 'motor_impairment' in accessibility_needs:
            features.extend(['large_click_targets', 'extended_hover_time'])
        
        return features