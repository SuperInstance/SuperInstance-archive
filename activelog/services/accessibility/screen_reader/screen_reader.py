"""
Screen Reader Support System
Comprehensive screen reader integration and ARIA support
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
from pathlib import Path
import re

logger = logging.getLogger(__name__)

class ARIARole(Enum):
    BUTTON = "button"
    LINK = "link"
    HEADING = "heading"
    MAIN = "main"
    NAVIGATION = "navigation"
    BANNER = "banner"
    CONTENTINFO = "contentinfo"
    ARTICLE = "article"
    SECTION = "section"
    ASIDE = "complementary"
    FORM = "form"
    SEARCH = "search"
    LISTBOX = "listbox"
    OPTION = "option"
    MENU = "menu"
    MENUITEM = "menuitem"
    TAB = "tab"
    TABPANEL = "tabpanel"
    DIALOG = "dialog"
    ALERT = "alert"
    STATUS = "status"
    LIVE_REGION = "region"
    TEXTBOX = "textbox"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    SLIDER = "slider"
    PROGRESSBAR = "progressbar"
    TABLE = "table"
    GRID = "grid"
    CELL = "cell"
    ROW = "row"
    COLUMNHEADER = "columnheader"
    ROWHEADER = "rowheader"

class LiveRegionPoliteness(Enum):
    OFF = "off"
    POLITE = "polite"
    ASSERTIVE = "assertive"

class ScreenReaderEngine(Enum):
    JAWS = "jaws"
    NVDA = "nvda"
    VOICEOVER = "voiceover"
    NARRATOR = "narrator"
    ORCA = "orca"
    TALKBACK = "talkback"

@dataclass
class ARIAElement:
    element_id: str
    role: ARIARole
    label: Optional[str] = None
    labelledby: Optional[str] = None
    describedby: Optional[str] = None
    expanded: Optional[bool] = None
    selected: Optional[bool] = None
    checked: Optional[Union[bool, str]] = None  # true, false, or "mixed"
    disabled: Optional[bool] = None
    hidden: Optional[bool] = None
    level: Optional[int] = None  # For headings
    live: Optional[LiveRegionPoliteness] = None
    atomic: Optional[bool] = None
    relevant: Optional[str] = None  # additions, removals, text, all
    busy: Optional[bool] = None
    owns: Optional[List[str]] = None
    controls: Optional[str] = None
    flowto: Optional[str] = None
    
    def __post_init__(self):
        if self.owns is None:
            self.owns = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['role'] = self.role.value
        if result.get('live'):
            result['live'] = result['live'].value
        return result
    
    def to_aria_attributes(self) -> Dict[str, str]:
        """Convert to HTML ARIA attributes"""
        attrs = {"role": self.role.value}
        
        if self.label:
            attrs["aria-label"] = self.label
        if self.labelledby:
            attrs["aria-labelledby"] = self.labelledby
        if self.describedby:
            attrs["aria-describedby"] = self.describedby
        if self.expanded is not None:
            attrs["aria-expanded"] = str(self.expanded).lower()
        if self.selected is not None:
            attrs["aria-selected"] = str(self.selected).lower()
        if self.checked is not None:
            if isinstance(self.checked, bool):
                attrs["aria-checked"] = str(self.checked).lower()
            else:
                attrs["aria-checked"] = self.checked
        if self.disabled is not None:
            attrs["aria-disabled"] = str(self.disabled).lower()
        if self.hidden is not None:
            attrs["aria-hidden"] = str(self.hidden).lower()
        if self.level is not None:
            attrs["aria-level"] = str(self.level)
        if self.live:
            attrs["aria-live"] = self.live.value
        if self.atomic is not None:
            attrs["aria-atomic"] = str(self.atomic).lower()
        if self.relevant:
            attrs["aria-relevant"] = self.relevant
        if self.busy is not None:
            attrs["aria-busy"] = str(self.busy).lower()
        if self.owns:
            attrs["aria-owns"] = " ".join(self.owns)
        if self.controls:
            attrs["aria-controls"] = self.controls
        if self.flowto:
            attrs["aria-flowto"] = self.flowto
        
        return attrs

@dataclass
class ScreenReaderAnnouncement:
    message: str
    priority: LiveRegionPoliteness = LiveRegionPoliteness.POLITE
    timestamp: Optional[datetime] = None
    context: Optional[str] = None
    element_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'message': self.message,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'element_id': self.element_id
        }

@dataclass
class NavigationLandmark:
    landmark_id: str
    role: ARIARole
    label: str
    description: Optional[str] = None
    level: int = 1
    parent_id: Optional[str] = None
    children: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['role'] = self.role.value
        return result

class ScreenReaderSupport:
    """Core screen reader support functionality"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.elements: Dict[str, ARIAElement] = {}
        self.landmarks: Dict[str, NavigationLandmark] = {}
        self.announcements: List[ScreenReaderAnnouncement] = []
        
        # Live region management
        self.live_regions: Dict[str, str] = {}  # element_id -> region_id
        
        # Screen reader detection
        self.detected_engine: Optional[ScreenReaderEngine] = None
        
        # Skip links for keyboard navigation
        self.skip_links: List[Dict[str, str]] = []
        
    def register_element(self, element: ARIAElement) -> bool:
        """Register an element for screen reader support"""
        try:
            self.elements[element.element_id] = element
            logger.info(f"Registered screen reader element: {element.element_id} ({element.role.value})")
            return True
        except Exception as e:
            logger.error(f"Failed to register element {element.element_id}: {e}")
            return False
    
    def update_element(self, element_id: str, **updates) -> bool:
        """Update element ARIA properties"""
        if element_id not in self.elements:
            logger.warning(f"Element {element_id} not found for update")
            return False
        
        element = self.elements[element_id]
        
        # Update properties
        for key, value in updates.items():
            if hasattr(element, key):
                setattr(element, key, value)
        
        # Announce changes if live region
        if element.live and element.live != LiveRegionPoliteness.OFF:
            self._announce_element_change(element_id, updates)
        
        return True
    
    def remove_element(self, element_id: str) -> bool:
        """Remove element from screen reader support"""
        if element_id in self.elements:
            del self.elements[element_id]
            if element_id in self.live_regions:
                del self.live_regions[element_id]
            return True
        return False
    
    def create_live_region(self, region_id: str, politeness: LiveRegionPoliteness = LiveRegionPoliteness.POLITE,
                          atomic: bool = False, relevant: str = "additions text") -> ARIAElement:
        """Create a live region for dynamic content announcements"""
        element = ARIAElement(
            element_id=region_id,
            role=ARIARole.LIVE_REGION,
            live=politeness,
            atomic=atomic,
            relevant=relevant,
            label=f"Live region {region_id}"
        )
        
        self.register_element(element)
        self.live_regions[region_id] = region_id
        
        return element
    
    def announce(self, message: str, priority: LiveRegionPoliteness = LiveRegionPoliteness.POLITE,
                context: Optional[str] = None) -> ScreenReaderAnnouncement:
        """Make an announcement to screen readers"""
        announcement = ScreenReaderAnnouncement(
            message=message,
            priority=priority,
            context=context
        )
        
        self.announcements.append(announcement)
        
        # Keep only recent announcements
        if len(self.announcements) > 100:
            self.announcements = self.announcements[-50:]
        
        logger.info(f"Screen reader announcement ({priority.value}): {message}")
        return announcement
    
    def register_landmark(self, landmark: NavigationLandmark) -> bool:
        """Register a navigation landmark"""
        try:
            self.landmarks[landmark.landmark_id] = landmark
            
            # Create corresponding ARIA element
            element = ARIAElement(
                element_id=landmark.landmark_id,
                role=landmark.role,
                label=landmark.label,
                level=landmark.level
            )
            
            self.register_element(element)
            logger.info(f"Registered navigation landmark: {landmark.label} ({landmark.role.value})")
            return True
        except Exception as e:
            logger.error(f"Failed to register landmark {landmark.landmark_id}: {e}")
            return False
    
    def add_skip_link(self, label: str, target_id: str, href: Optional[str] = None) -> Dict[str, str]:
        """Add a skip link for keyboard navigation"""
        skip_link = {
            'label': label,
            'target_id': target_id,
            'href': href or f"#{target_id}",
            'id': f"skip-{target_id}"
        }
        
        self.skip_links.append(skip_link)
        return skip_link
    
    def get_page_structure(self) -> Dict[str, Any]:
        """Generate page structure for screen reader navigation"""
        headings = []
        landmarks = []
        forms = []
        links = []
        
        for element_id, element in self.elements.items():
            if element.role == ARIARole.HEADING:
                headings.append({
                    'id': element_id,
                    'level': element.level or 1,
                    'text': element.label or '',
                    'aria': element.to_aria_attributes()
                })
            elif element.role in [ARIARole.MAIN, ARIARole.NAVIGATION, ARIARole.BANNER, 
                                ARIARole.CONTENTINFO, ARIARole.ASIDE, ARIARole.SEARCH]:
                landmarks.append({
                    'id': element_id,
                    'role': element.role.value,
                    'label': element.label or '',
                    'aria': element.to_aria_attributes()
                })
            elif element.role == ARIARole.FORM:
                forms.append({
                    'id': element_id,
                    'label': element.label or '',
                    'aria': element.to_aria_attributes()
                })
            elif element.role == ARIARole.LINK:
                links.append({
                    'id': element_id,
                    'text': element.label or '',
                    'aria': element.to_aria_attributes()
                })
        
        return {
            'headings': sorted(headings, key=lambda x: x['level']),
            'landmarks': landmarks,
            'forms': forms,
            'links': links,
            'skip_links': self.skip_links
        }
    
    def generate_aria_markup(self, element_id: str) -> str:
        """Generate HTML markup with ARIA attributes"""
        if element_id not in self.elements:
            return ""
        
        element = self.elements[element_id]
        attrs = element.to_aria_attributes()
        
        # Generate attribute string
        attr_string = " ".join([f'{key}="{value}"' for key, value in attrs.items()])
        
        # Suggest appropriate HTML tag based on role
        tag_suggestions = {
            ARIARole.BUTTON: "button",
            ARIARole.LINK: "a",
            ARIARole.HEADING: f"h{element.level or 1}",
            ARIARole.MAIN: "main",
            ARIARole.NAVIGATION: "nav",
            ARIARole.BANNER: "header",
            ARIARole.CONTENTINFO: "footer",
            ARIARole.ARTICLE: "article",
            ARIARole.SECTION: "section",
            ARIARole.ASIDE: "aside",
            ARIARole.FORM: "form",
            ARIARole.TEXTBOX: "input",
            ARIARole.CHECKBOX: "input",
            ARIARole.RADIO: "input"
        }
        
        tag = tag_suggestions.get(element.role, "div")
        return f"<{tag} id=\"{element_id}\" {attr_string}></{tag}>"
    
    def _announce_element_change(self, element_id: str, changes: Dict[str, Any]):
        """Announce element changes to live regions"""
        element = self.elements.get(element_id)
        if not element or not element.live:
            return
        
        # Generate announcement based on changes
        messages = []
        
        if 'expanded' in changes:
            state = "expanded" if changes['expanded'] else "collapsed"
            messages.append(f"{element.label or 'Element'} {state}")
        
        if 'selected' in changes:
            state = "selected" if changes['selected'] else "unselected"
            messages.append(f"{element.label or 'Element'} {state}")
        
        if 'checked' in changes:
            if changes['checked'] is True:
                messages.append(f"{element.label or 'Checkbox'} checked")
            elif changes['checked'] is False:
                messages.append(f"{element.label or 'Checkbox'} unchecked")
        
        if 'disabled' in changes:
            state = "disabled" if changes['disabled'] else "enabled"
            messages.append(f"{element.label or 'Element'} {state}")
        
        if messages:
            self.announce(" and ".join(messages), element.live, f"element_{element_id}")
    
    def detect_screen_reader(self, user_agent: str = "", features: List[str] = None) -> Optional[ScreenReaderEngine]:
        """Attempt to detect screen reader from browser info"""
        features = features or []
        
        # Check for screen reader indicators
        indicators = {
            ScreenReaderEngine.JAWS: ['jaws', 'freedom scientific'],
            ScreenReaderEngine.NVDA: ['nvda'],
            ScreenReaderEngine.VOICEOVER: ['voiceover', 'safari'],
            ScreenReaderEngine.NARRATOR: ['narrator', 'edge'],
            ScreenReaderEngine.ORCA: ['orca', 'linux'],
            ScreenReaderEngine.TALKBACK: ['talkback', 'android']
        }
        
        user_agent_lower = user_agent.lower()
        
        for engine, keywords in indicators.items():
            if any(keyword in user_agent_lower for keyword in keywords):
                self.detected_engine = engine
                return engine
        
        # Check for accessibility features
        if 'high-contrast' in features or 'screen-reader' in features:
            # Default to most common screen reader
            self.detected_engine = ScreenReaderEngine.NVDA
            return self.detected_engine
        
        return None
    
    def get_screen_reader_config(self) -> Dict[str, Any]:
        """Get configuration optimized for detected screen reader"""
        base_config = {
            'announce_focus_changes': True,
            'announce_page_loads': True,
            'announce_dynamic_changes': True,
            'use_aria_descriptions': True,
            'provide_skip_links': True,
            'use_semantic_markup': True
        }
        
        if self.detected_engine == ScreenReaderEngine.JAWS:
            base_config.update({
                'use_jaws_specific_labels': True,
                'provide_table_summaries': True,
                'use_jaws_shortcuts': True
            })
        elif self.detected_engine == ScreenReaderEngine.NVDA:
            base_config.update({
                'use_nvda_browse_mode': True,
                'provide_nvda_shortcuts': True
            })
        elif self.detected_engine == ScreenReaderEngine.VOICEOVER:
            base_config.update({
                'use_voiceover_rotor': True,
                'optimize_for_safari': True,
                'use_voiceover_gestures': True
            })
        
        return base_config
    
    def validate_accessibility(self, html_content: str) -> List[Dict[str, Any]]:
        """Validate HTML content for accessibility issues"""
        issues = []
        
        # Check for missing alt text on images
        img_pattern = r'<img(?![^>]*alt=)[^>]*>'
        for match in re.finditer(img_pattern, html_content, re.IGNORECASE):
            issues.append({
                'type': 'missing_alt_text',
                'severity': 'high',
                'message': 'Image missing alt text',
                'position': match.start(),
                'element': match.group()
            })
        
        # Check for headings structure
        heading_pattern = r'<h([1-6])[^>]*>'
        headings = []
        for match in re.finditer(heading_pattern, html_content, re.IGNORECASE):
            level = int(match.group(1))
            headings.append(level)
        
        # Check for proper heading hierarchy
        for i, level in enumerate(headings[1:], 1):
            prev_level = headings[i-1]
            if level > prev_level + 1:
                issues.append({
                    'type': 'heading_skip',
                    'severity': 'medium',
                    'message': f'Heading skips from h{prev_level} to h{level}',
                    'position': -1
                })
        
        # Check for form labels
        input_pattern = r'<input(?![^>]*aria-label)(?![^>]*aria-labelledby)[^>]*>'
        for match in re.finditer(input_pattern, html_content, re.IGNORECASE):
            if 'type="hidden"' not in match.group():
                issues.append({
                    'type': 'missing_form_label',
                    'severity': 'high',
                    'message': 'Form input missing label or aria-label',
                    'position': match.start(),
                    'element': match.group()
                })
        
        # Check for color-only information
        color_words = ['red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink']
        for color in color_words:
            if f'color: {color}' in html_content or f'class="text-{color}"' in html_content:
                issues.append({
                    'type': 'color_only_info',
                    'severity': 'medium',
                    'message': f'Information may be conveyed by color only ({color})',
                    'position': -1
                })
        
        return issues

class AccessibilityDatabase:
    """Database for accessibility preferences and settings"""
    
    def __init__(self, db_path: str = "accessibility.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    screen_reader_enabled BOOLEAN DEFAULT 0,
                    screen_reader_engine TEXT,
                    announcement_verbosity TEXT DEFAULT 'normal',
                    skip_links_enabled BOOLEAN DEFAULT 1,
                    focus_indicators_enhanced BOOLEAN DEFAULT 0,
                    aria_descriptions_enabled BOOLEAN DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accessibility_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    event_type TEXT NOT NULL,
                    element_id TEXT,
                    message TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Save user accessibility preferences"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("""
                    INSERT OR REPLACE INTO user_preferences (
                        user_id, screen_reader_enabled, screen_reader_engine,
                        announcement_verbosity, skip_links_enabled,
                        focus_indicators_enhanced, aria_descriptions_enabled,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    preferences.get('screen_reader_enabled', False),
                    preferences.get('screen_reader_engine'),
                    preferences.get('announcement_verbosity', 'normal'),
                    preferences.get('skip_links_enabled', True),
                    preferences.get('focus_indicators_enhanced', False),
                    preferences.get('aria_descriptions_enabled', True),
                    now, now
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to save user preferences: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user accessibility preferences"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None

async def main():
    """Example usage of screen reader support system"""
    
    # Initialize screen reader support
    sr_support = ScreenReaderSupport()
    
    print("=== Screen Reader Support Demo ===")
    
    # Register page landmarks
    main_landmark = NavigationLandmark(
        landmark_id="main-content",
        role=ARIARole.MAIN,
        label="Main content",
        description="Primary content area"
    )
    
    nav_landmark = NavigationLandmark(
        landmark_id="primary-nav",
        role=ARIARole.NAVIGATION,
        label="Primary navigation",
        description="Main site navigation"
    )
    
    sr_support.register_landmark(main_landmark)
    sr_support.register_landmark(nav_landmark)
    
    # Add skip links
    sr_support.add_skip_link("Skip to main content", "main-content")
    sr_support.add_skip_link("Skip to navigation", "primary-nav")
    
    print("Registered navigation landmarks and skip links")
    
    # Register interactive elements
    button_element = ARIAElement(
        element_id="submit-btn",
        role=ARIARole.BUTTON,
        label="Submit form",
        describedby="submit-help"
    )
    
    sr_support.register_element(button_element)
    
    # Create live region for announcements
    live_region = sr_support.create_live_region(
        "announcements",
        LiveRegionPoliteness.POLITE,
        atomic=True
    )
    
    print(f"Created live region: {live_region.element_id}")
    
    # Make announcements
    sr_support.announce("Welcome to the accessibility demo", LiveRegionPoliteness.POLITE)
    sr_support.announce("Form validation completed", LiveRegionPoliteness.ASSERTIVE)
    
    # Update element state
    sr_support.update_element("submit-btn", disabled=True)
    sr_support.update_element("submit-btn", disabled=False)  # This will trigger announcement
    
    # Get page structure
    structure = sr_support.get_page_structure()
    print(f"\nPage structure:")
    print(f"- Landmarks: {len(structure['landmarks'])}")
    print(f"- Skip links: {len(structure['skip_links'])}")
    print(f"- Headings: {len(structure['headings'])}")
    
    # Generate ARIA markup
    markup = sr_support.generate_aria_markup("submit-btn")
    print(f"\nGenerated markup: {markup}")
    
    # Screen reader detection
    detected = sr_support.detect_screen_reader("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 NVDA/2021.1")
    if detected:
        print(f"Detected screen reader: {detected.value}")
        config = sr_support.get_screen_reader_config()
        print(f"Optimized config: {list(config.keys())}")
    
    # Validate accessibility
    sample_html = '''
    <div>
        <h1>Welcome</h1>
        <h3>Skipped heading level</h3>
        <img src="photo.jpg">
        <input type="text" placeholder="Name">
        <button style="color: red;">Click here</button>
    </div>
    '''
    
    issues = sr_support.validate_accessibility(sample_html)
    print(f"\nAccessibility issues found: {len(issues)}")
    for issue in issues:
        print(f"- {issue['type']}: {issue['message']} (severity: {issue['severity']})")

if __name__ == "__main__":
    asyncio.run(main())