"""
DM screen customization and digital screen store
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import DMScreen, Product, ContentType, ProductStatus

class ScreenType(Enum):
    DIGITAL = "digital"
    PRINTABLE = "printable"
    INTERACTIVE = "interactive"
    HYBRID = "hybrid"

class ScreenLayout(Enum):
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    TRI_FOLD = "tri_fold"
    QUAD_FOLD = "quad_fold"
    CUSTOM = "custom"

class ContentCategory(Enum):
    RULES_REFERENCE = "rules_reference"
    TABLES = "tables"
    QUICK_STATS = "quick_stats"
    CAMPAIGN_INFO = "campaign_info"
    RANDOM_GENERATORS = "random_generators"
    INITIATIVE_TRACKER = "initiative_tracker"
    NOTES_SPACE = "notes_space"
    ARTWORK = "artwork"

class GameSystem(Enum):
    DND_5E = "dnd_5e"
    PATHFINDER_2E = "pathfinder_2e"
    DND_35 = "dnd_35"
    PATHFINDER_1E = "pathfinder_1e"
    OSR = "osr"
    GENERIC = "generic"
    CUSTOM = "custom"

class DMScreenStore:
    """Manages DM screen customization marketplace"""
    
    def __init__(self):
        self.dm_screens: Dict[str, DMScreen] = {}
        self.screen_templates: Dict[str, Dict[str, Any]] = {}
        self.content_modules: Dict[str, Dict[str, Any]] = {}
        self.user_screens: Dict[str, List[str]] = {}  # user_id -> screen_ids
        self.featured_screens: List[str] = []
        
        # Initialize screen components
        self._initialize_screen_components()
    
    def _initialize_screen_components(self):
        """Initialize DM screen components and templates"""
        
        self.standard_panels = {
            "rules_reference": {
                "dnd_5e": {
                    "combat_actions": ["Attack", "Dash", "Dodge", "Help", "Hide", "Ready", "Search"],
                    "conditions": ["Blinded", "Charmed", "Deafened", "Frightened", "Grappled", "Incapacitated"],
                    "cover_rules": ["Half Cover (+2 AC)", "Three-Quarters Cover (+5 AC)", "Full Cover (Can't target)"],
                    "skill_dcs": ["Very Easy (5)", "Easy (10)", "Medium (15)", "Hard (20)", "Very Hard (25)", "Nearly Impossible (30)"]
                }
            },
            "quick_tables": {
                "names": {
                    "human_male": ["Aerdeth", "Aramil", "Arannis", "Berris", "Cithreth"],
                    "human_female": ["Arara", "Aribeth", "Bitha", "Caelynn", "Calysta"],
                    "tavern_names": ["The Prancing Pony", "The Dragon's Flagon", "The Rusty Anchor"]
                },
                "random_encounters": {
                    "forest": ["Bandits", "Wild Animals", "Fairy Ring", "Lost Traveler"],
                    "city": ["Pickpocket", "Street Performer", "Noble's Carriage", "Guard Patrol"]
                }
            },
            "status_trackers": {
                "initiative": "Turn order and HP tracking",
                "spell_slots": "Player spell slot usage",
                "conditions": "Active conditions and durations",
                "resources": "Party resources and abilities"
            }
        }
        
        self.visual_themes = {
            "classic_fantasy": {
                "colors": ["#8B4513", "#DAA520", "#2F4F4F"],
                "style": "Traditional medieval fantasy",
                "artwork": "Dragons, castles, medieval imagery"
            },
            "dark_gothic": {
                "colors": ["#2C2C2C", "#8B0000", "#4B0082"],
                "style": "Gothic horror aesthetic",
                "artwork": "Gothic architecture, ravens, skulls"
            },
            "modern_clean": {
                "colors": ["#F5F5F5", "#4169E1", "#2E8B57"],
                "style": "Clean, minimalist design",
                "artwork": "Geometric patterns, simple icons"
            },
            "steampunk": {
                "colors": ["#CD853F", "#B8860B", "#8B4513"],
                "style": "Victorian industrial aesthetic",
                "artwork": "Gears, brass, Victorian elements"
            },
            "cyberpunk": {
                "colors": ["#000000", "#00FFFF", "#FF1493"],
                "style": "Neon futuristic design",
                "artwork": "Circuit patterns, neon lights"
            }
        }
        
        self.interactive_features = {
            "dice_roller": "Built-in dice rolling functionality",
            "timer": "Session and encounter timers",
            "calculator": "Quick math calculations",
            "notes": "Editable notes and reminders",
            "sound_board": "Quick access to sound effects",
            "weather_generator": "Random weather conditions",
            "name_generator": "Random NPC name generation",
            "loot_generator": "Random treasure generation"
        }
    
    def create_dm_screen(
        self,
        creator_id: str,
        name: str,
        description: str,
        screen_type: ScreenType,
        layout: ScreenLayout,
        game_system: GameSystem,
        content_categories: List[ContentCategory],
        visual_theme: str,
        interactive_features: List[str] = None,
        panel_count: int = 3,
        resolution: tuple = (1920, 1080),
        price: Decimal = Decimal("0.00"),
        is_customizable: bool = True,
        includes_blank_template: bool = False
    ) -> DMScreen:
        """Create new DM screen"""
        
        dm_screen = DMScreen(
            creator_id=creator_id,
            title=name,
            description=description,
            content_type=ContentType.DM_SCREEN,
            price=price,
            screen_type=screen_type.value,
            layout=layout.value,
            game_system=game_system.value,
            content_categories=[cat.value for cat in content_categories],
            visual_theme=visual_theme,
            interactive_features=interactive_features or [],
            panel_count=panel_count,
            resolution=resolution,
            is_customizable=is_customizable,
            includes_blank_template=includes_blank_template,
            file_formats=[],
            preview_images=[]
        )
        
        # Set file formats based on screen type
        if screen_type == ScreenType.DIGITAL:
            dm_screen.file_formats = ["PNG", "JPG", "PDF"]
        elif screen_type == ScreenType.PRINTABLE:
            dm_screen.file_formats = ["PDF", "PNG", "SVG"]
        elif screen_type == ScreenType.INTERACTIVE:
            dm_screen.file_formats = ["HTML", "JS", "CSS"]
        else:  # HYBRID
            dm_screen.file_formats = ["PDF", "PNG", "HTML", "JS"]
        
        self.dm_screens[dm_screen.id] = dm_screen
        return dm_screen
    
    def create_custom_screen(
        self,
        user_id: str,
        base_template_id: Optional[str],
        name: str,
        customizations: Dict[str, Any]
    ) -> str:
        """Create custom DM screen from template"""
        
        # Start with base template if provided
        if base_template_id and base_template_id in self.dm_screens:
            base_screen = self.dm_screens[base_template_id]
            
            # Create custom screen
            custom_screen = DMScreen(
                creator_id=user_id,
                title=name,
                description=f"Custom screen based on {base_screen.title}",
                content_type=ContentType.DM_SCREEN,
                price=Decimal("0.00"),  # Custom screens are free to creator
                screen_type=base_screen.screen_type,
                layout=base_screen.layout,
                game_system=base_screen.game_system,
                content_categories=base_screen.content_categories.copy(),
                visual_theme=customizations.get("visual_theme", base_screen.visual_theme),
                interactive_features=customizations.get("interactive_features", base_screen.interactive_features.copy()),
                panel_count=customizations.get("panel_count", base_screen.panel_count),
                resolution=customizations.get("resolution", base_screen.resolution),
                is_customizable=True,
                includes_blank_template=False,
                file_formats=base_screen.file_formats.copy(),
                base_template_id=base_template_id
            )
        else:
            # Create from scratch
            custom_screen = DMScreen(
                creator_id=user_id,
                title=name,
                description="Custom DM screen",
                content_type=ContentType.DM_SCREEN,
                price=Decimal("0.00"),
                screen_type=customizations.get("screen_type", ScreenType.DIGITAL.value),
                layout=customizations.get("layout", ScreenLayout.LANDSCAPE.value),
                game_system=customizations.get("game_system", GameSystem.DND_5E.value),
                content_categories=customizations.get("content_categories", []),
                visual_theme=customizations.get("visual_theme", "classic_fantasy"),
                interactive_features=customizations.get("interactive_features", []),
                panel_count=customizations.get("panel_count", 3),
                resolution=customizations.get("resolution", (1920, 1080)),
                is_customizable=True,
                includes_blank_template=False,
                file_formats=["PNG", "PDF"]
            )
        
        # Apply specific customizations
        if "panel_content" in customizations:
            custom_screen.panel_content = customizations["panel_content"]
        
        if "color_scheme" in customizations:
            custom_screen.color_scheme = customizations["color_scheme"]
        
        if "font_settings" in customizations:
            custom_screen.font_settings = customizations["font_settings"]
        
        self.dm_screens[custom_screen.id] = custom_screen
        
        # Add to user's screens
        if user_id not in self.user_screens:
            self.user_screens[user_id] = []
        self.user_screens[user_id].append(custom_screen.id)
        
        return custom_screen.id
    
    def search_dm_screens(
        self,
        query: Optional[str] = None,
        screen_type: Optional[ScreenType] = None,
        layout: Optional[ScreenLayout] = None,
        game_system: Optional[GameSystem] = None,
        content_categories: List[ContentCategory] = None,
        visual_theme: Optional[str] = None,
        interactive_features: List[str] = None,
        panel_count: Optional[int] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        is_customizable: Optional[bool] = None,
        includes_blank_template: Optional[bool] = None,
        creator_id: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> List[DMScreen]:
        """Search DM screens with filters"""
        
        results = []
        
        for screen in self.dm_screens.values():
            if screen.status != ProductStatus.ACTIVE:
                continue
            
            # Skip custom screens in public search
            if hasattr(screen, 'base_template_id') and screen.base_template_id:
                continue
            
            # Text search
            if query:
                search_text = f"{screen.title} {screen.description} {screen.visual_theme} {' '.join(screen.content_categories)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Screen type filter
            if screen_type and screen.screen_type != screen_type.value:
                continue
            
            # Layout filter
            if layout and screen.layout != layout.value:
                continue
            
            # Game system filter
            if game_system and screen.game_system != game_system.value:
                continue
            
            # Content categories filter
            if content_categories:
                screen_categories = set(screen.content_categories)
                required_categories = set(cat.value for cat in content_categories)
                if not required_categories.issubset(screen_categories):
                    continue
            
            # Visual theme filter
            if visual_theme and screen.visual_theme != visual_theme:
                continue
            
            # Interactive features filter
            if interactive_features:
                screen_features = set(screen.interactive_features)
                required_features = set(interactive_features)
                if not required_features.issubset(screen_features):
                    continue
            
            # Panel count filter
            if panel_count and screen.panel_count != panel_count:
                continue
            
            # Price filter
            if price_min and screen.price < price_min:
                continue
            if price_max and screen.price > price_max:
                continue
            
            # Customizable filter
            if is_customizable is not None and screen.is_customizable != is_customizable:
                continue
            
            # Blank template filter
            if includes_blank_template is not None and screen.includes_blank_template != includes_blank_template:
                continue
            
            # Creator filter
            if creator_id and screen.creator_id != creator_id:
                continue
            
            results.append(screen)
        
        # Sort results
        if sort_by == "price_low":
            results.sort(key=lambda s: s.price)
        elif sort_by == "price_high":
            results.sort(key=lambda s: s.price, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda s: s.created_at, reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda s: (s.download_count, s.average_rating), reverse=True)
        else:  # relevance
            results.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        
        return results
    
    def get_screen_details(self, screen_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed DM screen information"""
        
        if screen_id not in self.dm_screens:
            return None
        
        screen = self.dm_screens[screen_id]
        
        return {
            "screen": screen.dict(),
            "creator_info": self._get_creator_info(screen.creator_id),
            "content_preview": self._generate_content_preview(screen),
            "technical_specs": self._get_technical_specs(screen),
            "customization_options": self._get_customization_options(screen),
            "similar_screens": self._get_similar_screens(screen),
            "usage_instructions": self._get_usage_instructions(screen)
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get screen creator information"""
        
        creator_screens = [s for s in self.dm_screens.values() if s.creator_id == creator_id]
        active_screens = [s for s in creator_screens if s.status == ProductStatus.ACTIVE]
        
        total_downloads = sum(s.download_count for s in active_screens)
        avg_rating = sum(s.average_rating for s in active_screens) / len(active_screens) if active_screens else 0
        
        return {
            "id": creator_id,
            "name": f"Screen Designer {creator_id[:8]}",
            "total_screens": len(active_screens),
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
            "specialties": self._get_creator_specialties(creator_id),
            "verified": len(active_screens) >= 5
        }
    
    def _get_creator_specialties(self, creator_id: str) -> List[str]:
        """Determine creator's specialties"""
        
        creator_screens = [s for s in self.dm_screens.values() 
                          if s.creator_id == creator_id and s.status == ProductStatus.ACTIVE]
        
        # Count screen types and game systems
        type_counts = {}
        system_counts = {}
        
        for screen in creator_screens:
            type_counts[screen.screen_type] = type_counts.get(screen.screen_type, 0) + 1
            system_counts[screen.game_system] = system_counts.get(screen.game_system, 0) + 1
        
        specialties = []
        
        # Top screen type
        if type_counts:
            top_type = max(type_counts.items(), key=lambda x: x[1])
            specialties.append(f"{top_type[0]} screens")
        
        # Top game system
        if system_counts:
            top_system = max(system_counts.items(), key=lambda x: x[1])
            specialties.append(f"{top_system[0]} specialist")
        
        # Interactive features
        interactive_count = sum(1 for s in creator_screens if s.interactive_features)
        if interactive_count > len(creator_screens) * 0.5:
            specialties.append("interactive features")
        
        return specialties[:3]
    
    def _generate_content_preview(self, screen: DMScreen) -> Dict[str, Any]:
        """Generate content preview for screen"""
        
        preview = {
            "layout_info": {
                "type": screen.layout,
                "panel_count": screen.panel_count,
                "resolution": f"{screen.resolution[0]}x{screen.resolution[1]}"
            },
            "content_areas": [],
            "visual_style": {
                "theme": screen.visual_theme,
                "color_scheme": self.visual_themes.get(screen.visual_theme, {}).get("colors", []),
                "style_description": self.visual_themes.get(screen.visual_theme, {}).get("style", "")
            },
            "interactive_elements": screen.interactive_features
        }
        
        # Generate content area previews based on categories
        for category in screen.content_categories:
            if category == ContentCategory.RULES_REFERENCE.value:
                preview["content_areas"].append({
                    "category": "Rules Reference",
                    "description": "Quick access to common rules and mechanics",
                    "sample_content": ["Combat Actions", "Skill DCs", "Conditions"]
                })
            elif category == ContentCategory.TABLES.value:
                preview["content_areas"].append({
                    "category": "Random Tables",
                    "description": "Quick reference tables for gameplay",
                    "sample_content": ["Name Generators", "Random Encounters", "Weather"]
                })
            elif category == ContentCategory.INITIATIVE_TRACKER.value:
                preview["content_areas"].append({
                    "category": "Initiative Tracker",
                    "description": "Combat order and status tracking",
                    "sample_content": ["Turn Order", "HP Tracking", "Condition Monitoring"]
                })
            elif category == ContentCategory.NOTES_SPACE.value:
                preview["content_areas"].append({
                    "category": "Notes Space",
                    "description": "Editable areas for session notes",
                    "sample_content": ["Important NPCs", "Plot Threads", "Reminders"]
                })
        
        return preview
    
    def _get_technical_specs(self, screen: DMScreen) -> Dict[str, Any]:
        """Get technical specifications"""
        
        specs = {
            "file_formats": screen.file_formats,
            "resolution": f"{screen.resolution[0]}x{screen.resolution[1]}",
            "panel_configuration": f"{screen.panel_count} panels in {screen.layout} layout",
            "screen_type": screen.screen_type,
            "compatibility": self._get_compatibility_info(screen),
            "file_size_estimate": self._estimate_file_size(screen)
        }
        
        if screen.screen_type == ScreenType.INTERACTIVE.value:
            specs.update({
                "browser_requirements": "Modern web browser with JavaScript",
                "mobile_compatible": True,
                "offline_capable": "Partial (core features work offline)"
            })
        
        if screen.screen_type == ScreenType.PRINTABLE.value:
            specs.update({
                "print_size": "Standard 8.5x11\" or A4",
                "print_quality": "300 DPI recommended",
                "paper_requirements": "Standard printer paper or cardstock"
            })
        
        return specs
    
    def _get_compatibility_info(self, screen: DMScreen) -> Dict[str, Any]:
        """Get compatibility information"""
        
        compatibility = {
            "vtt_platforms": {
                "roll20": screen.screen_type in [ScreenType.DIGITAL.value, ScreenType.INTERACTIVE.value],
                "foundry": screen.screen_type in [ScreenType.DIGITAL.value, ScreenType.INTERACTIVE.value],
                "fantasy_grounds": screen.screen_type == ScreenType.DIGITAL.value
            },
            "devices": {
                "desktop": True,
                "tablet": screen.screen_type in [ScreenType.DIGITAL.value, ScreenType.INTERACTIVE.value],
                "mobile": screen.screen_type == ScreenType.INTERACTIVE.value,
                "print": screen.screen_type in [ScreenType.PRINTABLE.value, ScreenType.HYBRID.value]
            },
            "software": {
                "pdf_reader": "PDF" in screen.file_formats,
                "image_viewer": any(fmt in screen.file_formats for fmt in ["PNG", "JPG"]),
                "web_browser": "HTML" in screen.file_formats
            }
        }
        
        return compatibility
    
    def _estimate_file_size(self, screen: DMScreen) -> str:
        """Estimate total file size"""
        
        base_size = 0
        
        # Base size by screen type
        if screen.screen_type == ScreenType.DIGITAL.value:
            base_size = screen.panel_count * 2  # MB per panel
        elif screen.screen_type == ScreenType.PRINTABLE.value:
            base_size = screen.panel_count * 1.5  # MB per panel (PDF)
        elif screen.screen_type == ScreenType.INTERACTIVE.value:
            base_size = 5 + (screen.panel_count * 0.5)  # Base HTML/CSS/JS + content
        else:  # HYBRID
            base_size = screen.panel_count * 3  # Larger due to multiple formats
        
        # Add size for interactive features
        base_size += len(screen.interactive_features) * 0.2
        
        return f"~{base_size:.1f} MB"
    
    def _get_customization_options(self, screen: DMScreen) -> Dict[str, Any]:
        """Get available customization options"""
        
        if not screen.is_customizable:
            return {"customizable": False}
        
        return {
            "customizable": True,
            "visual_customization": {
                "themes": list(self.visual_themes.keys()),
                "colors": "Custom color schemes supported",
                "fonts": ["Standard", "Fantasy", "Modern", "Handwritten"],
                "backgrounds": "Custom background images supported"
            },
            "content_customization": {
                "panel_content": "Add/edit/remove content blocks",
                "rules_sections": "Customize rules references",
                "tables": "Add custom tables and generators",
                "notes_areas": "Configurable note-taking spaces"
            },
            "layout_options": {
                "panel_count": f"1-6 panels (current: {screen.panel_count})",
                "arrangement": "Flexible panel arrangement",
                "sizing": "Adjustable panel sizes",
                "spacing": "Customizable margins and padding"
            },
            "interactive_additions": {
                "available_features": list(self.interactive_features.keys()),
                "current_features": screen.interactive_features,
                "feature_descriptions": self.interactive_features
            }
        }
    
    def _get_similar_screens(self, screen: DMScreen) -> List[DMScreen]:
        """Find similar DM screens"""
        
        similar = []
        
        for other in self.dm_screens.values():
            if (other.id == screen.id or 
                other.status != ProductStatus.ACTIVE or
                (hasattr(other, 'base_template_id') and other.base_template_id)):
                continue
            
            similarity_score = 0
            
            # Same game system
            if other.game_system == screen.game_system:
                similarity_score += 3
            
            # Same screen type
            if other.screen_type == screen.screen_type:
                similarity_score += 2
            
            # Common content categories
            common_categories = set(screen.content_categories) & set(other.content_categories)
            similarity_score += len(common_categories)
            
            # Same layout
            if other.layout == screen.layout:
                similarity_score += 1
            
            # Same theme
            if other.visual_theme == screen.visual_theme:
                similarity_score += 1
            
            # Common interactive features
            common_features = set(screen.interactive_features) & set(other.interactive_features)
            similarity_score += len(common_features) * 0.5
            
            if similarity_score >= 3:
                similar.append(other)
        
        similar.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        return similar[:6]
    
    def _get_usage_instructions(self, screen: DMScreen) -> Dict[str, List[str]]:
        """Generate usage instructions"""
        
        instructions = {
            "general": [
                "Download the DM screen package",
                "Extract files to desired location",
                "Follow setup instructions for your platform"
            ]
        }
        
        if screen.screen_type == ScreenType.DIGITAL.value:
            instructions["digital"] = [
                "Open image files in your preferred viewer",
                "Set as desktop wallpaper or display on second monitor",
                "Use tablet/phone for portable reference"
            ]
        
        if screen.screen_type == ScreenType.PRINTABLE.value:
            instructions["printable"] = [
                "Print PDF file on cardstock for durability",
                "Fold along marked lines if tri/quad-fold",
                "Consider laminating for repeated use",
                "Use standard 8.5x11\" or A4 paper"
            ]
        
        if screen.screen_type == ScreenType.INTERACTIVE.value:
            instructions["interactive"] = [
                "Open HTML file in web browser",
                "Bookmark for easy access during sessions",
                "Works offline once loaded",
                "Use on tablet for touch interaction"
            ]
        
        if screen.is_customizable:
            instructions["customization"] = [
                "Use the customization tool to modify content",
                "Save custom versions for different campaigns",
                "Export personalized screens in preferred format",
                "Share custom configurations with other DMs"
            ]
        
        return instructions
    
    def get_user_custom_screens(self, user_id: str) -> List[DMScreen]:
        """Get user's custom DM screens"""
        
        user_screen_ids = self.user_screens.get(user_id, [])
        custom_screens = []
        
        for screen_id in user_screen_ids:
            if screen_id in self.dm_screens:
                custom_screens.append(self.dm_screens[screen_id])
        
        # Sort by creation date, newest first
        custom_screens.sort(key=lambda s: s.created_at, reverse=True)
        return custom_screens
    
    def get_popular_templates(self, game_system: Optional[GameSystem] = None, count: int = 12) -> List[DMScreen]:
        """Get popular screen templates"""
        
        templates = [
            s for s in self.dm_screens.values()
            if (s.status == ProductStatus.ACTIVE and
                not (hasattr(s, 'base_template_id') and s.base_template_id) and
                (not game_system or s.game_system == game_system.value))
        ]
        
        # Sort by downloads and ratings
        templates.sort(key=lambda s: (s.download_count, s.average_rating), reverse=True)
        return templates[:count]
    
    def get_beginner_friendly_screens(self, game_system: GameSystem = GameSystem.DND_5E, count: int = 8) -> List[DMScreen]:
        """Get beginner-friendly DM screens"""
        
        beginner_screens = [
            s for s in self.dm_screens.values()
            if (s.status == ProductStatus.ACTIVE and
                s.game_system == game_system.value and
                ContentCategory.RULES_REFERENCE.value in s.content_categories and
                not (hasattr(s, 'base_template_id') and s.base_template_id))
        ]
        
        # Prioritize screens with good ratings and comprehensive content
        beginner_screens.sort(key=lambda s: (len(s.content_categories), s.average_rating), reverse=True)
        return beginner_screens[:count]
    
    def get_interactive_screens(self, count: int = 10) -> List[DMScreen]:
        """Get interactive DM screens"""
        
        interactive_screens = [
            s for s in self.dm_screens.values()
            if (s.status == ProductStatus.ACTIVE and
                s.screen_type == ScreenType.INTERACTIVE.value and
                not (hasattr(s, 'base_template_id') and s.base_template_id))
        ]
        
        interactive_screens.sort(key=lambda s: (len(s.interactive_features), s.average_rating), reverse=True)
        return interactive_screens[:count]
    
    def get_trending_screens(self, days: int = 30) -> List[DMScreen]:
        """Get trending DM screens"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending = []
        for screen in self.dm_screens.values():
            if (screen.status != ProductStatus.ACTIVE or
                (hasattr(screen, 'base_template_id') and screen.base_template_id)):
                continue
            
            # Calculate trend score
            trend_score = screen.download_count + (float(screen.average_rating) * 10)
            
            # Bonus for interactive features
            trend_score += len(screen.interactive_features) * 2
            
            # Bonus for customizable screens
            if screen.is_customizable:
                trend_score += 5
            
            trending.append({
                "screen": screen,
                "trend_score": trend_score
            })
        
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        return [item["screen"] for item in trending[:15]]