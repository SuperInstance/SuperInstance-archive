"""
High Contrast Mode System
Comprehensive high contrast themes and visual accessibility options
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import logging
from pathlib import Path
import colorsys

logger = logging.getLogger(__name__)

class ContrastMode(Enum):
    NORMAL = "normal"
    HIGH_CONTRAST_DARK = "high_contrast_dark"
    HIGH_CONTRAST_LIGHT = "high_contrast_light"
    INVERTED = "inverted"
    YELLOW_ON_BLACK = "yellow_on_black"
    WHITE_ON_BLACK = "white_on_black"
    BLACK_ON_WHITE = "black_on_white"
    BLUE_ON_WHITE = "blue_on_white"
    GREEN_ON_BLACK = "green_on_black"

class ContrastLevel(Enum):
    AA = "aa"           # WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text)
    AAA = "aaa"         # WCAG 2.1 AAA (7:1 for normal text, 4.5:1 for large text)
    ENHANCED = "enhanced"  # Beyond AAA requirements

@dataclass
class ColorPair:
    foreground: str  # Hex color
    background: str  # Hex color
    contrast_ratio: Optional[float] = None
    
    def __post_init__(self):
        if self.contrast_ratio is None:
            self.contrast_ratio = self.calculate_contrast_ratio()
    
    def calculate_contrast_ratio(self) -> float:
        """Calculate WCAG contrast ratio between foreground and background"""
        return calculate_contrast_ratio(self.foreground, self.background)
    
    def meets_wcag_aa(self, large_text: bool = False) -> bool:
        """Check if color pair meets WCAG 2.1 AA requirements"""
        threshold = 3.0 if large_text else 4.5
        return self.contrast_ratio >= threshold
    
    def meets_wcag_aaa(self, large_text: bool = False) -> bool:
        """Check if color pair meets WCAG 2.1 AAA requirements"""
        threshold = 4.5 if large_text else 7.0
        return self.contrast_ratio >= threshold
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ContrastTheme:
    theme_id: str
    name: str
    mode: ContrastMode
    colors: Dict[str, ColorPair]
    description: Optional[str] = None
    target_users: Optional[List[str]] = None  # low vision, light sensitivity, etc.
    wcag_compliant: bool = False
    compliance_level: Optional[ContrastLevel] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.theme_id:
            self.theme_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.target_users is None:
            self.target_users = []
        
        # Validate WCAG compliance
        self._validate_compliance()
    
    def _validate_compliance(self):
        """Validate WCAG compliance for all color pairs"""
        aa_compliance = all(pair.meets_wcag_aa() for pair in self.colors.values())
        aaa_compliance = all(pair.meets_wcag_aaa() for pair in self.colors.values())
        
        if aaa_compliance:
            self.wcag_compliant = True
            self.compliance_level = ContrastLevel.AAA
        elif aa_compliance:
            self.wcag_compliant = True
            self.compliance_level = ContrastLevel.AA
        else:
            self.wcag_compliant = False
            self.compliance_level = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['mode'] = self.mode.value
        if result.get('compliance_level'):
            result['compliance_level'] = result['compliance_level'].value
        if result.get('created_at'):
            result['created_at'] = result['created_at'].isoformat()
        
        # Convert color pairs
        result['colors'] = {key: pair.to_dict() for key, pair in self.colors.items()}
        
        return result
    
    def generate_css(self) -> str:
        """Generate CSS for the contrast theme"""
        css_rules = [f"/* {self.name} - {self.mode.value} */"]
        css_rules.append(f".contrast-theme-{self.theme_id} {{")
        
        for element, color_pair in self.colors.items():
            css_rules.append(f"  --{element}-fg: {color_pair.foreground};")
            css_rules.append(f"  --{element}-bg: {color_pair.background};")
        
        css_rules.append("}")
        css_rules.append("")
        
        # Generate specific element rules
        element_mappings = {
            'text': 'body, p, div, span',
            'heading': 'h1, h2, h3, h4, h5, h6',
            'link': 'a',
            'button': 'button, input[type="button"], input[type="submit"]',
            'input': 'input, textarea, select',
            'border': '*',
            'focus': ':focus'
        }
        
        for element, color_pair in self.colors.items():
            if element in element_mappings:
                selectors = element_mappings[element]
                css_rules.append(f".contrast-theme-{self.theme_id} {selectors} {{")
                css_rules.append(f"  color: {color_pair.foreground} !important;")
                css_rules.append(f"  background-color: {color_pair.background} !important;")
                
                if element == 'border':
                    css_rules.append(f"  border-color: {color_pair.foreground} !important;")
                elif element == 'focus':
                    css_rules.append(f"  outline: 3px solid {color_pair.foreground} !important;")
                    css_rules.append(f"  outline-offset: 2px !important;")
                
                css_rules.append("}")
                css_rules.append("")
        
        return "\n".join(css_rules)

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color"""
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

def calculate_luminance(hex_color: str) -> float:
    """Calculate relative luminance according to WCAG guidelines"""
    r, g, b = hex_to_rgb(hex_color)
    
    # Convert to 0-1 range
    r, g, b = r/255.0, g/255.0, b/255.0
    
    # Apply gamma correction
    def gamma_correct(c):
        return c/12.92 if c <= 0.03928 else ((c + 0.055)/1.055) ** 2.4
    
    r, g, b = gamma_correct(r), gamma_correct(g), gamma_correct(b)
    
    # Calculate luminance
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """Calculate contrast ratio between two colors"""
    lum1 = calculate_luminance(color1)
    lum2 = calculate_luminance(color2)
    
    # Ensure lighter color is numerator
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    return (lighter + 0.05) / (darker + 0.05)

def adjust_color_contrast(foreground: str, background: str, target_ratio: float = 4.5) -> str:
    """Adjust foreground color to meet target contrast ratio"""
    current_ratio = calculate_contrast_ratio(foreground, background)
    
    if current_ratio >= target_ratio:
        return foreground
    
    # Convert to HSL for easier manipulation
    r, g, b = hex_to_rgb(foreground)
    h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
    
    # Adjust lightness
    bg_luminance = calculate_luminance(background)
    
    # If background is light, make foreground darker
    # If background is dark, make foreground lighter
    if bg_luminance > 0.5:
        # Light background - darken foreground
        while l > 0 and current_ratio < target_ratio:
            l -= 0.05
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            new_color = rgb_to_hex((int(r*255), int(g*255), int(b*255)))
            current_ratio = calculate_contrast_ratio(new_color, background)
    else:
        # Dark background - lighten foreground
        while l < 1 and current_ratio < target_ratio:
            l += 0.05
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            new_color = rgb_to_hex((int(r*255), int(g*255), int(b*255)))
            current_ratio = calculate_contrast_ratio(new_color, background)
    
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return rgb_to_hex((int(r*255), int(g*255), int(b*255)))

class ContrastModeManager:
    """Manager for high contrast modes and themes"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.themes: Dict[str, ContrastTheme] = {}
        
        # Initialize built-in themes
        self._create_built_in_themes()
        
        # Current active theme
        self.active_theme: Optional[ContrastTheme] = None
    
    def _create_built_in_themes(self):
        """Create built-in high contrast themes"""
        
        # High Contrast Dark theme
        dark_theme = ContrastTheme(
            theme_id="high-contrast-dark",
            name="High Contrast Dark",
            mode=ContrastMode.HIGH_CONTRAST_DARK,
            colors={
                'text': ColorPair("#FFFFFF", "#000000"),
                'heading': ColorPair("#FFFF00", "#000000"),
                'link': ColorPair("#00FFFF", "#000000"),
                'link_visited': ColorPair("#FF00FF", "#000000"),
                'button': ColorPair("#000000", "#FFFF00"),
                'input': ColorPair("#000000", "#FFFFFF"),
                'border': ColorPair("#FFFFFF", "#000000"),
                'focus': ColorPair("#FFFF00", "#000000"),
                'error': ColorPair("#FF0000", "#000000"),
                'success': ColorPair("#00FF00", "#000000"),
                'warning': ColorPair("#FFAA00", "#000000")
            },
            description="High contrast theme with white text on black background",
            target_users=["low_vision", "cataracts", "light_sensitivity"]
        )
        
        # High Contrast Light theme
        light_theme = ContrastTheme(
            theme_id="high-contrast-light",
            name="High Contrast Light",
            mode=ContrastMode.HIGH_CONTRAST_LIGHT,
            colors={
                'text': ColorPair("#000000", "#FFFFFF"),
                'heading': ColorPair("#0000FF", "#FFFFFF"),
                'link': ColorPair("#0000FF", "#FFFFFF"),
                'link_visited': ColorPair("#800080", "#FFFFFF"),
                'button': ColorPair("#FFFFFF", "#0000FF"),
                'input': ColorPair("#000000", "#FFFFFF"),
                'border': ColorPair("#000000", "#FFFFFF"),
                'focus': ColorPair("#FFFFFF", "#0000FF"),
                'error': ColorPair("#CC0000", "#FFFFFF"),
                'success': ColorPair("#006600", "#FFFFFF"),
                'warning': ColorPair("#CC6600", "#FFFFFF")
            },
            description="High contrast theme with black text on white background",
            target_users=["low_vision", "macular_degeneration"]
        )
        
        # Yellow on Black theme
        yellow_black_theme = ContrastTheme(
            theme_id="yellow-on-black",
            name="Yellow on Black",
            mode=ContrastMode.YELLOW_ON_BLACK,
            colors={
                'text': ColorPair("#FFFF00", "#000000"),
                'heading': ColorPair("#FFFFFF", "#000000"),
                'link': ColorPair("#00FFFF", "#000000"),
                'link_visited': ColorPair("#FFAAFF", "#000000"),
                'button': ColorPair("#000000", "#FFFF00"),
                'input': ColorPair("#000000", "#FFFF00"),
                'border': ColorPair("#FFFF00", "#000000"),
                'focus': ColorPair("#000000", "#FFFFFF"),
                'error': ColorPair("#FF6666", "#000000"),
                'success': ColorPair("#66FF66", "#000000"),
                'warning': ColorPair("#FFAA00", "#000000")
            },
            description="Yellow text on black background for enhanced readability",
            target_users=["dyslexia", "low_vision", "computer_vision_syndrome"]
        )
        
        # Blue on White theme
        blue_white_theme = ContrastTheme(
            theme_id="blue-on-white",
            name="Blue on White",
            mode=ContrastMode.BLUE_ON_WHITE,
            colors={
                'text': ColorPair("#000080", "#FFFFFF"),
                'heading': ColorPair("#000040", "#FFFFFF"),
                'link': ColorPair("#0000FF", "#FFFFFF"),
                'link_visited': ColorPair("#800080", "#FFFFFF"),
                'button': ColorPair("#FFFFFF", "#000080"),
                'input': ColorPair("#000080", "#F8F8FF"),
                'border': ColorPair("#000080", "#FFFFFF"),
                'focus': ColorPair("#FFFFFF", "#000080"),
                'error': ColorPair("#800000", "#FFFFFF"),
                'success': ColorPair("#004000", "#FFFFFF"),
                'warning': ColorPair("#806000", "#FFFFFF")
            },
            description="Blue tones on white background for reduced eye strain",
            target_users=["light_sensitivity", "migraine_sufferers", "autism"]
        )
        
        # Inverted theme
        inverted_theme = ContrastTheme(
            theme_id="inverted",
            name="Inverted Colors",
            mode=ContrastMode.INVERTED,
            colors={
                'text': ColorPair("#00FFFF", "#330033"),
                'heading': ColorPair("#FFFF00", "#330033"),
                'link': ColorPair("#FF6600", "#330033"),
                'link_visited': ColorPair("#CC99FF", "#330033"),
                'button': ColorPair("#330033", "#00FFFF"),
                'input': ColorPair("#330033", "#CCFFCC"),
                'border': ColorPair("#00FFFF", "#330033"),
                'focus': ColorPair("#330033", "#FFFF00"),
                'error': ColorPair("#FF3333", "#330033"),
                'success': ColorPair("#33FF33", "#330033"),
                'warning': ColorPair("#FFAA33", "#330033")
            },
            description="Inverted color scheme for unique visual needs",
            target_users=["photophobia", "specific_color_preferences"]
        )
        
        # Register all themes
        for theme in [dark_theme, light_theme, yellow_black_theme, blue_white_theme, inverted_theme]:
            self.themes[theme.theme_id] = theme
    
    def create_custom_theme(self, name: str, mode: ContrastMode, 
                           base_colors: Dict[str, Tuple[str, str]]) -> ContrastTheme:
        """Create a custom contrast theme"""
        
        # Convert color tuples to ColorPair objects
        color_pairs = {}
        for element, (fg, bg) in base_colors.items():
            color_pairs[element] = ColorPair(fg, bg)
        
        theme = ContrastTheme(
            theme_id=str(uuid.uuid4()),
            name=name,
            mode=mode,
            colors=color_pairs,
            description=f"Custom {name} theme"
        )
        
        self.themes[theme.theme_id] = theme
        return theme
    
    def optimize_theme_for_wcag(self, theme_id: str, target_level: ContrastLevel = ContrastLevel.AA) -> bool:
        """Optimize theme colors to meet WCAG requirements"""
        if theme_id not in self.themes:
            return False
        
        theme = self.themes[theme_id]
        target_ratio = 7.0 if target_level == ContrastLevel.AAA else 4.5
        
        # Adjust each color pair
        for element, color_pair in theme.colors.items():
            if color_pair.contrast_ratio < target_ratio:
                # Adjust foreground color
                new_fg = adjust_color_contrast(
                    color_pair.foreground, 
                    color_pair.background, 
                    target_ratio
                )
                
                # Update color pair
                theme.colors[element] = ColorPair(new_fg, color_pair.background)
        
        # Revalidate compliance
        theme._validate_compliance()
        
        logger.info(f"Optimized theme {theme.name} for {target_level.value} compliance")
        return True
    
    def set_active_theme(self, theme_id: str) -> bool:
        """Set the active contrast theme"""
        if theme_id not in self.themes:
            logger.error(f"Theme {theme_id} not found")
            return False
        
        self.active_theme = self.themes[theme_id]
        logger.info(f"Set active contrast theme: {self.active_theme.name}")
        return True
    
    def get_theme_css(self, theme_id: Optional[str] = None) -> str:
        """Get CSS for specified theme or active theme"""
        theme = None
        
        if theme_id:
            theme = self.themes.get(theme_id)
        elif self.active_theme:
            theme = self.active_theme
        
        if not theme:
            return ""
        
        return theme.generate_css()
    
    def get_available_themes(self) -> List[Dict[str, Any]]:
        """Get list of available contrast themes"""
        return [theme.to_dict() for theme in self.themes.values()]
    
    def validate_color_accessibility(self, foreground: str, background: str) -> Dict[str, Any]:
        """Validate color pair accessibility"""
        color_pair = ColorPair(foreground, background)
        
        return {
            'foreground': foreground,
            'background': background,
            'contrast_ratio': color_pair.contrast_ratio,
            'wcag_aa_normal': color_pair.meets_wcag_aa(large_text=False),
            'wcag_aa_large': color_pair.meets_wcag_aa(large_text=True),
            'wcag_aaa_normal': color_pair.meets_wcag_aaa(large_text=False),
            'wcag_aaa_large': color_pair.meets_wcag_aaa(large_text=True),
            'recommendations': self._get_color_recommendations(color_pair)
        }
    
    def _get_color_recommendations(self, color_pair: ColorPair) -> List[str]:
        """Get recommendations for improving color accessibility"""
        recommendations = []
        
        if not color_pair.meets_wcag_aa(large_text=False):
            recommendations.append("Increase contrast ratio to at least 4.5:1 for normal text")
        
        if not color_pair.meets_wcag_aa(large_text=True):
            recommendations.append("Increase contrast ratio to at least 3:1 for large text")
        
        if color_pair.meets_wcag_aa() but not color_pair.meets_wcag_aaa():
            recommendations.append("Consider increasing contrast to 7:1 for AAA compliance")
        
        if color_pair.contrast_ratio < 2.0:
            recommendations.append("Color combination may be difficult to read for users with low vision")
        
        return recommendations
    
    def generate_system_preferences_css(self) -> str:
        """Generate CSS that respects system accessibility preferences"""
        css = """
/* Respect system preferences for contrast and colors */
@media (prefers-contrast: high) {
    :root {
        --text-color: #000000;
        --background-color: #FFFFFF;
        --accent-color: #0000FF;
        --border-color: #000000;
    }
    
    [data-theme="dark"] {
        --text-color: #FFFFFF;
        --background-color: #000000;
        --accent-color: #FFFF00;
        --border-color: #FFFFFF;
    }
}

@media (prefers-contrast: more) {
    :root {
        --text-color: #000000;
        --background-color: #FFFFFF;
        filter: contrast(1.2);
    }
}

@media (prefers-color-scheme: dark) and (prefers-contrast: high) {
    :root {
        --text-color: #FFFFFF;
        --background-color: #000000;
        --accent-color: #FFFF00;
        --link-color: #00FFFF;
        --visited-link-color: #FF00FF;
    }
}

/* Forced colors mode support */
@media (forced-colors: active) {
    * {
        color: CanvasText !important;
        background-color: Canvas !important;
        border-color: CanvasText !important;
    }
    
    a {
        color: LinkText !important;
    }
    
    a:visited {
        color: VisitedText !important;
    }
    
    button, input[type="button"], input[type="submit"] {
        color: ButtonText !important;
        background-color: ButtonFace !important;
        border-color: ButtonText !important;
    }
    
    :focus {
        outline: 2px solid Highlight !important;
        outline-offset: 2px !important;
    }
}
"""
        return css

async def main():
    """Example usage of contrast mode system"""
    
    # Initialize contrast manager
    contrast_manager = ContrastModeManager()
    
    print("=== High Contrast Mode Demo ===")
    
    # List available themes
    themes = contrast_manager.get_available_themes()
    print(f"Available themes: {len(themes)}")
    for theme in themes:
        print(f"- {theme['name']} ({theme['mode']}): WCAG {theme['compliance_level'] or 'Non-compliant'}")
    
    # Set active theme
    contrast_manager.set_active_theme("high-contrast-dark")
    
    # Generate CSS
    css = contrast_manager.get_theme_css()
    print(f"\nGenerated CSS length: {len(css)} characters")
    print("CSS preview:")
    print(css[:300] + "..." if len(css) > 300 else css)
    
    # Validate color accessibility
    validation = contrast_manager.validate_color_accessibility("#666666", "#FFFFFF")
    print(f"\nColor validation for #666666 on #FFFFFF:")
    print(f"- Contrast ratio: {validation['contrast_ratio']:.2f}")
    print(f"- WCAG AA normal: {validation['wcag_aa_normal']}")
    print(f"- WCAG AAA normal: {validation['wcag_aaa_normal']}")
    print(f"- Recommendations: {validation['recommendations']}")
    
    # Create custom theme
    custom_theme = contrast_manager.create_custom_theme(
        name="Ocean Theme",
        mode=ContrastMode.NORMAL,
        base_colors={
            'text': ("#003366", "#E6F3FF"),
            'heading': ("#001133", "#E6F3FF"),
            'link': ("#0066CC", "#E6F3FF")
        }
    )
    
    print(f"\nCreated custom theme: {custom_theme.name}")
    print(f"WCAG compliant: {custom_theme.wcag_compliant}")
    
    # Optimize theme for WCAG
    if not custom_theme.wcag_compliant:
        success = contrast_manager.optimize_theme_for_wcag(custom_theme.theme_id, ContrastLevel.AA)
        if success:
            print("Optimized custom theme for WCAG AA compliance")
            print(f"Now WCAG compliant: {custom_theme.wcag_compliant}")
    
    # Generate system preferences CSS
    system_css = contrast_manager.generate_system_preferences_css()
    print(f"\nSystem preferences CSS length: {len(system_css)} characters")

if __name__ == "__main__":
    asyncio.run(main())