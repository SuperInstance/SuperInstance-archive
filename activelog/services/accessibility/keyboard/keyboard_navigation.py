"""
Keyboard-Only Navigation System
Comprehensive keyboard navigation support with focus management
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FocusDirection(Enum):
    FORWARD = "forward"
    BACKWARD = "backward"
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    FIRST = "first"
    LAST = "last"

class KeyboardEventType(Enum):
    KEYDOWN = "keydown"
    KEYUP = "keyup"
    KEYPRESS = "keypress"

class FocusableType(Enum):
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TAB = "tab"
    MENU_ITEM = "menu_item"
    TREE_ITEM = "tree_item"
    GRID_CELL = "grid_cell"
    DIALOG = "dialog"
    CUSTOM = "custom"

@dataclass
class KeyboardShortcut:
    shortcut_id: str
    keys: List[str]  # e.g., ["Ctrl", "S"] or ["Alt", "F", "O"]
    action: str
    description: str
    context: Optional[str] = None  # Global, form, dialog, etc.
    enabled: bool = True
    category: Optional[str] = None
    
    def __post_init__(self):
        if not self.shortcut_id:
            self.shortcut_id = str(uuid.uuid4())
    
    def matches_event(self, event_keys: List[str]) -> bool:
        """Check if keyboard event matches this shortcut"""
        return self.enabled and self.keys == event_keys
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_display_string(self) -> str:
        """Get human-readable shortcut string"""
        key_map = {
            'Control': 'Ctrl',
            'Meta': 'Cmd',
            'Alt': 'Alt',
            'Shift': 'Shift'
        }
        
        mapped_keys = []
        for key in self.keys:
            mapped_keys.append(key_map.get(key, key))
        
        return " + ".join(mapped_keys)

@dataclass
class FocusableElement:
    element_id: str
    element_type: FocusableType
    label: Optional[str] = None
    tab_index: Optional[int] = None
    disabled: bool = False
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None
    group: Optional[str] = None  # For radio buttons, tabs, etc.
    position: Optional[Dict[str, int]] = None  # x, y coordinates
    size: Optional[Dict[str, int]] = None  # width, height
    custom_focus_handler: Optional[str] = None
    skip_in_tab_order: bool = False
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.position is None:
            self.position = {'x': 0, 'y': 0}
        if self.size is None:
            self.size = {'width': 0, 'height': 0}
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['element_type'] = self.element_type.value
        return result
    
    def is_focusable(self) -> bool:
        """Check if element can receive focus"""
        return not self.disabled and not self.skip_in_tab_order

@dataclass
class FocusState:
    current_element_id: Optional[str] = None
    previous_element_id: Optional[str] = None
    focus_history: Optional[List[str]] = None
    trap_focus: bool = False
    trap_container_id: Optional[str] = None
    
    def __post_init__(self):
        if self.focus_history is None:
            self.focus_history = []
    
    def add_to_history(self, element_id: str):
        """Add element to focus history"""
        if element_id not in self.focus_history:
            self.focus_history.append(element_id)
        
        # Keep only last 50 elements
        if len(self.focus_history) > 50:
            self.focus_history = self.focus_history[-25:]

class KeyboardNavigationManager:
    """Manager for keyboard-only navigation"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.elements: Dict[str, FocusableElement] = {}
        self.shortcuts: Dict[str, KeyboardShortcut] = {}
        self.focus_state = FocusState()
        
        # Navigation settings
        self.wrap_around = self.config.get('wrap_around', True)
        self.skip_disabled = self.config.get('skip_disabled', True)
        self.visual_focus_indicators = self.config.get('visual_focus_indicators', True)
        
        # Custom handlers
        self.focus_handlers: Dict[str, Callable] = {}
        self.shortcut_handlers: Dict[str, Callable] = {}
        
        # Initialize default shortcuts
        self._setup_default_shortcuts()
    
    def _setup_default_shortcuts(self):
        """Setup default keyboard shortcuts"""
        default_shortcuts = [
            # Navigation
            KeyboardShortcut("tab-forward", ["Tab"], "focus_next", "Move to next focusable element", "global", True, "navigation"),
            KeyboardShortcut("tab-backward", ["Shift", "Tab"], "focus_previous", "Move to previous focusable element", "global", True, "navigation"),
            KeyboardShortcut("home", ["Home"], "focus_first", "Move to first focusable element", "global", True, "navigation"),
            KeyboardShortcut("end", ["End"], "focus_last", "Move to last focusable element", "global", True, "navigation"),
            
            # Arrow navigation
            KeyboardShortcut("arrow-up", ["ArrowUp"], "focus_up", "Move focus up", "grid", True, "navigation"),
            KeyboardShortcut("arrow-down", ["ArrowDown"], "focus_down", "Move focus down", "grid", True, "navigation"),
            KeyboardShortcut("arrow-left", ["ArrowLeft"], "focus_left", "Move focus left", "grid", True, "navigation"),
            KeyboardShortcut("arrow-right", ["ArrowRight"], "focus_right", "Move focus right", "grid", True, "navigation"),
            
            # Application shortcuts
            KeyboardShortcut("save", ["Ctrl", "s"], "save", "Save current document", "global", True, "application"),
            KeyboardShortcut("copy", ["Ctrl", "c"], "copy", "Copy selection", "global", True, "application"),
            KeyboardShortcut("paste", ["Ctrl", "v"], "paste", "Paste from clipboard", "global", True, "application"),
            KeyboardShortcut("undo", ["Ctrl", "z"], "undo", "Undo last action", "global", True, "application"),
            KeyboardShortcut("redo", ["Ctrl", "y"], "redo", "Redo last action", "global", True, "application"),
            
            # Dialog shortcuts
            KeyboardShortcut("escape", ["Escape"], "cancel", "Cancel or close dialog", "dialog", True, "dialog"),
            KeyboardShortcut("enter", ["Enter"], "confirm", "Confirm action", "dialog", True, "dialog"),
            
            # Menu shortcuts
            KeyboardShortcut("menu-open", ["Alt"], "open_menu", "Open application menu", "global", True, "menu"),
            KeyboardShortcut("context-menu", ["ContextMenu"], "context_menu", "Open context menu", "global", True, "menu"),
            KeyboardShortcut("context-menu-alt", ["Shift", "F10"], "context_menu", "Open context menu (alternative)", "global", True, "menu")
        ]
        
        for shortcut in default_shortcuts:
            self.shortcuts[shortcut.shortcut_id] = shortcut
    
    def register_element(self, element: FocusableElement) -> bool:
        """Register a focusable element"""
        try:
            self.elements[element.element_id] = element
            logger.info(f"Registered focusable element: {element.element_id} ({element.element_type.value})")
            return True
        except Exception as e:
            logger.error(f"Failed to register element {element.element_id}: {e}")
            return False
    
    def unregister_element(self, element_id: str) -> bool:
        """Unregister a focusable element"""
        if element_id in self.elements:
            # If this was the focused element, move focus elsewhere
            if self.focus_state.current_element_id == element_id:
                self.focus_next()
            
            del self.elements[element_id]
            return True
        return False
    
    def register_shortcut(self, shortcut: KeyboardShortcut) -> bool:
        """Register a keyboard shortcut"""
        try:
            self.shortcuts[shortcut.shortcut_id] = shortcut
            logger.info(f"Registered keyboard shortcut: {shortcut.get_display_string()} -> {shortcut.action}")
            return True
        except Exception as e:
            logger.error(f"Failed to register shortcut {shortcut.shortcut_id}: {e}")
            return False
    
    def unregister_shortcut(self, shortcut_id: str) -> bool:
        """Unregister a keyboard shortcut"""
        if shortcut_id in self.shortcuts:
            del self.shortcuts[shortcut_id]
            return True
        return False
    
    def set_focus(self, element_id: str, force: bool = False) -> bool:
        """Set focus to specific element"""
        if element_id not in self.elements:
            logger.warning(f"Element {element_id} not found")
            return False
        
        element = self.elements[element_id]
        
        # Check if element can be focused
        if not force and not element.is_focusable():
            logger.warning(f"Element {element_id} is not focusable")
            return False
        
        # Check focus trap
        if self.focus_state.trap_focus and self.focus_state.trap_container_id:
            if not self._is_element_in_container(element_id, self.focus_state.trap_container_id):
                logger.warning(f"Focus trapped in container {self.focus_state.trap_container_id}")
                return False
        
        # Update focus state
        self.focus_state.previous_element_id = self.focus_state.current_element_id
        self.focus_state.current_element_id = element_id
        self.focus_state.add_to_history(element_id)
        
        # Execute custom focus handler if available
        if element.custom_focus_handler and element.custom_focus_handler in self.focus_handlers:
            self.focus_handlers[element.custom_focus_handler](element_id)
        
        logger.info(f"Focus set to element: {element_id}")
        return True
    
    def focus_next(self, wrap: Optional[bool] = None) -> bool:
        """Move focus to next focusable element"""
        return self._navigate_focus(FocusDirection.FORWARD, wrap)
    
    def focus_previous(self, wrap: Optional[bool] = None) -> bool:
        """Move focus to previous focusable element"""
        return self._navigate_focus(FocusDirection.BACKWARD, wrap)
    
    def focus_first(self) -> bool:
        """Move focus to first focusable element"""
        return self._navigate_focus(FocusDirection.FIRST)
    
    def focus_last(self) -> bool:
        """Move focus to last focusable element"""
        return self._navigate_focus(FocusDirection.LAST)
    
    def focus_up(self) -> bool:
        """Move focus up (spatial navigation)"""
        return self._navigate_focus(FocusDirection.UP)
    
    def focus_down(self) -> bool:
        """Move focus down (spatial navigation)"""
        return self._navigate_focus(FocusDirection.DOWN)
    
    def focus_left(self) -> bool:
        """Move focus left (spatial navigation)"""
        return self._navigate_focus(FocusDirection.LEFT)
    
    def focus_right(self) -> bool:
        """Move focus right (spatial navigation)"""
        return self._navigate_focus(FocusDirection.RIGHT)
    
    def _navigate_focus(self, direction: FocusDirection, wrap: Optional[bool] = None) -> bool:
        """Navigate focus in specified direction"""
        if wrap is None:
            wrap = self.wrap_around
        
        focusable_elements = self._get_focusable_elements()
        
        if not focusable_elements:
            return False
        
        current_index = -1
        if self.focus_state.current_element_id:
            try:
                current_index = focusable_elements.index(self.focus_state.current_element_id)
            except ValueError:
                pass
        
        next_index = self._calculate_next_index(
            current_index, len(focusable_elements), direction, wrap
        )
        
        if next_index is not None:
            return self.set_focus(focusable_elements[next_index])
        
        return False
    
    def _calculate_next_index(self, current_index: int, total_elements: int, 
                            direction: FocusDirection, wrap: bool) -> Optional[int]:
        """Calculate next element index based on direction"""
        if direction == FocusDirection.FORWARD:
            next_index = current_index + 1
            if next_index >= total_elements:
                return 0 if wrap else None
            return next_index
        
        elif direction == FocusDirection.BACKWARD:
            next_index = current_index - 1
            if next_index < 0:
                return total_elements - 1 if wrap else None
            return next_index
        
        elif direction == FocusDirection.FIRST:
            return 0
        
        elif direction == FocusDirection.LAST:
            return total_elements - 1
        
        elif direction in [FocusDirection.UP, FocusDirection.DOWN, FocusDirection.LEFT, FocusDirection.RIGHT]:
            # Spatial navigation based on position
            return self._find_spatial_next_element(direction)
        
        return None
    
    def _find_spatial_next_element(self, direction: FocusDirection) -> Optional[int]:
        """Find next element using spatial navigation"""
        if not self.focus_state.current_element_id:
            return 0
        
        current_element = self.elements.get(self.focus_state.current_element_id)
        if not current_element:
            return None
        
        current_pos = current_element.position
        focusable_elements = self._get_focusable_elements()
        
        best_element = None
        best_distance = float('inf')
        
        for element_id in focusable_elements:
            if element_id == self.focus_state.current_element_id:
                continue
            
            element = self.elements[element_id]
            element_pos = element.position
            
            # Check if element is in the right direction
            if direction == FocusDirection.UP and element_pos['y'] >= current_pos['y']:
                continue
            elif direction == FocusDirection.DOWN and element_pos['y'] <= current_pos['y']:
                continue
            elif direction == FocusDirection.LEFT and element_pos['x'] >= current_pos['x']:
                continue
            elif direction == FocusDirection.RIGHT and element_pos['x'] <= current_pos['x']:
                continue
            
            # Calculate distance
            dx = element_pos['x'] - current_pos['x']
            dy = element_pos['y'] - current_pos['y']
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance < best_distance:
                best_distance = distance
                best_element = element_id
        
        if best_element:
            return focusable_elements.index(best_element)
        
        return None
    
    def _get_focusable_elements(self) -> List[str]:
        """Get list of focusable element IDs in tab order"""
        focusable = []
        
        # Get elements that can be focused
        for element_id, element in self.elements.items():
            if element.is_focusable():
                focusable.append((element_id, element.tab_index or 0))
        
        # Sort by tab index
        focusable.sort(key=lambda x: x[1])
        
        # Return just the IDs
        return [element_id for element_id, _ in focusable]
    
    def trap_focus(self, container_id: str) -> bool:
        """Trap focus within a container (for modals, dialogs)"""
        if container_id not in self.elements:
            return False
        
        self.focus_state.trap_focus = True
        self.focus_state.trap_container_id = container_id
        
        # Move focus to first element in container if not already there
        container_elements = self._get_elements_in_container(container_id)
        if container_elements and self.focus_state.current_element_id not in container_elements:
            self.set_focus(container_elements[0])
        
        logger.info(f"Focus trapped in container: {container_id}")
        return True
    
    def release_focus_trap(self) -> bool:
        """Release focus trap"""
        if not self.focus_state.trap_focus:
            return False
        
        container_id = self.focus_state.trap_container_id
        self.focus_state.trap_focus = False
        self.focus_state.trap_container_id = None
        
        logger.info(f"Focus trap released from container: {container_id}")
        return True
    
    def _is_element_in_container(self, element_id: str, container_id: str) -> bool:
        """Check if element is within container"""
        element = self.elements.get(element_id)
        if not element:
            return False
        
        # Check if element is direct child or descendant
        current = element
        while current:
            if current.element_id == container_id:
                return True
            if not current.parent_id:
                break
            current = self.elements.get(current.parent_id)
        
        return False
    
    def _get_elements_in_container(self, container_id: str) -> List[str]:
        """Get all focusable elements within a container"""
        container_elements = []
        
        for element_id, element in self.elements.items():
            if element.is_focusable() and self._is_element_in_container(element_id, container_id):
                container_elements.append(element_id)
        
        return container_elements
    
    def handle_keyboard_event(self, event_type: KeyboardEventType, 
                            keys: List[str], context: str = "global") -> Optional[str]:
        """Handle keyboard event and return action if shortcut matched"""
        if event_type != KeyboardEventType.KEYDOWN:
            return None
        
        # Find matching shortcut
        for shortcut in self.shortcuts.values():
            if shortcut.matches_event(keys) and (not shortcut.context or shortcut.context == context):
                # Execute shortcut handler if available
                if shortcut.action in self.shortcut_handlers:
                    self.shortcut_handlers[shortcut.action](shortcut)
                
                logger.info(f"Executed keyboard shortcut: {shortcut.get_display_string()} -> {shortcut.action}")
                return shortcut.action
        
        return None
    
    def register_focus_handler(self, handler_name: str, handler: Callable):
        """Register custom focus handler"""
        self.focus_handlers[handler_name] = handler
    
    def register_shortcut_handler(self, action: str, handler: Callable):
        """Register custom shortcut handler"""
        self.shortcut_handlers[action] = handler
    
    def get_keyboard_help(self, context: str = "global") -> List[Dict[str, Any]]:
        """Get list of available keyboard shortcuts for context"""
        help_items = []
        
        for shortcut in self.shortcuts.values():
            if shortcut.enabled and (not shortcut.context or shortcut.context == context):
                help_items.append({
                    'keys': shortcut.get_display_string(),
                    'description': shortcut.description,
                    'category': shortcut.category or 'general'
                })
        
        # Sort by category and then by keys
        help_items.sort(key=lambda x: (x['category'], x['keys']))
        return help_items
    
    def generate_focus_css(self) -> str:
        """Generate CSS for focus indicators"""
        css = """
/* Keyboard Navigation Focus Indicators */
:focus {
    outline: 3px solid #005FCC !important;
    outline-offset: 2px !important;
}

:focus:not(:focus-visible) {
    outline: none !important;
}

:focus-visible {
    outline: 3px solid #005FCC !important;
    outline-offset: 2px !important;
}

/* High contrast focus indicators */
@media (prefers-contrast: high) {
    :focus {
        outline: 3px solid #FFFF00 !important;
        outline-offset: 2px !important;
        background-color: #000080 !important;
        color: #FFFFFF !important;
    }
}

/* Skip links */
.skip-link {
    position: absolute;
    top: -40px;
    left: 6px;
    background: #000000;
    color: #FFFFFF;
    padding: 8px;
    text-decoration: none;
    z-index: 1000;
    border-radius: 4px;
}

.skip-link:focus {
    top: 6px;
}

/* Focus trap indicator */
.focus-trapped {
    position: relative;
}

.focus-trapped::before {
    content: '';
    position: absolute;
    top: -2px;
    left: -2px;
    right: -2px;
    bottom: -2px;
    border: 2px dashed #005FCC;
    pointer-events: none;
}

/* Keyboard navigation hints */
.keyboard-user .keyboard-hint {
    display: inline-block;
    font-size: 0.8em;
    opacity: 0.7;
    margin-left: 0.5em;
}

.keyboard-user .keyboard-hint::before {
    content: '(';
}

.keyboard-user .keyboard-hint::after {
    content: ')';
}
"""
        return css
    
    def get_navigation_state(self) -> Dict[str, Any]:
        """Get current navigation state"""
        return {
            'current_focus': self.focus_state.current_element_id,
            'previous_focus': self.focus_state.previous_element_id,
            'focus_trapped': self.focus_state.trap_focus,
            'trap_container': self.focus_state.trap_container_id,
            'total_focusable': len(self._get_focusable_elements()),
            'focus_history_length': len(self.focus_state.focus_history)
        }

async def main():
    """Example usage of keyboard navigation system"""
    
    # Initialize navigation manager
    nav_manager = KeyboardNavigationManager({
        'wrap_around': True,
        'visual_focus_indicators': True
    })
    
    print("=== Keyboard Navigation Demo ===")
    
    # Register some focusable elements
    elements = [
        FocusableElement("header-logo", FocusableType.LINK, "Company Logo", 1),
        FocusableElement("nav-home", FocusableType.LINK, "Home", 2),
        FocusableElement("nav-about", FocusableType.LINK, "About", 3),
        FocusableElement("search-input", FocusableType.INPUT, "Search", 4),
        FocusableElement("search-btn", FocusableType.BUTTON, "Search Button", 5),
        FocusableElement("main-content", FocusableType.CUSTOM, "Main Content", 6),
        FocusableElement("footer-link", FocusableType.LINK, "Contact", 7)
    ]
    
    for element in elements:
        nav_manager.register_element(element)
    
    print(f"Registered {len(elements)} focusable elements")
    
    # Set initial focus
    nav_manager.set_focus("header-logo")
    print(f"Initial focus: {nav_manager.focus_state.current_element_id}")
    
    # Navigate forward
    nav_manager.focus_next()
    print(f"After Tab: {nav_manager.focus_state.current_element_id}")
    
    nav_manager.focus_next()
    print(f"After Tab: {nav_manager.focus_state.current_element_id}")
    
    # Navigate backward
    nav_manager.focus_previous()
    print(f"After Shift+Tab: {nav_manager.focus_state.current_element_id}")
    
    # Jump to first and last
    nav_manager.focus_last()
    print(f"After End: {nav_manager.focus_state.current_element_id}")
    
    nav_manager.focus_first()
    print(f"After Home: {nav_manager.focus_state.current_element_id}")
    
    # Test keyboard event handling
    action = nav_manager.handle_keyboard_event(
        KeyboardEventType.KEYDOWN,
        ["Tab"],
        "global"
    )
    print(f"Keyboard event result: {action}")
    
    # Register custom shortcut
    custom_shortcut = KeyboardShortcut(
        shortcut_id="help",
        keys=["F1"],
        action="show_help",
        description="Show keyboard help",
        context="global",
        category="help"
    )
    
    nav_manager.register_shortcut(custom_shortcut)
    
    # Get keyboard help
    help_items = nav_manager.get_keyboard_help("global")
    print(f"\nKeyboard shortcuts available:")
    current_category = None
    for item in help_items[:10]:  # Show first 10
        if item['category'] != current_category:
            print(f"\n{item['category'].title()}:")
            current_category = item['category']
        print(f"  {item['keys']}: {item['description']}")
    
    # Test focus trap
    dialog_element = FocusableElement("dialog", FocusableType.DIALOG, "Settings Dialog", 100)
    dialog_button = FocusableElement("dialog-ok", FocusableType.BUTTON, "OK", 101, parent_id="dialog")
    
    nav_manager.register_element(dialog_element)
    nav_manager.register_element(dialog_button)
    
    nav_manager.trap_focus("dialog")
    print(f"\nFocus trapped in dialog, current focus: {nav_manager.focus_state.current_element_id}")
    
    # Try to navigate outside (should stay in dialog)
    nav_manager.focus_next()
    print(f"After trying to leave dialog: {nav_manager.focus_state.current_element_id}")
    
    # Release trap
    nav_manager.release_focus_trap()
    print("Focus trap released")
    
    # Get navigation state
    state = nav_manager.get_navigation_state()
    print(f"\nNavigation state:")
    print(f"- Current focus: {state['current_focus']}")
    print(f"- Total focusable elements: {state['total_focusable']}")
    print(f"- Focus trapped: {state['focus_trapped']}")
    
    # Generate CSS
    css = nav_manager.generate_focus_css()
    print(f"\nGenerated focus CSS length: {len(css)} characters")

if __name__ == "__main__":
    asyncio.run(main())