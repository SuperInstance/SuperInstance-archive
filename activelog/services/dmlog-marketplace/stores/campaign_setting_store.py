"""
Campaign setting marketplace for complete world packages
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import CampaignSetting, Product, ContentType, ProductStatus

class SettingGenre(Enum):
    HIGH_FANTASY = "high_fantasy"
    LOW_FANTASY = "low_fantasy"
    DARK_FANTASY = "dark_fantasy"
    URBAN_FANTASY = "urban_fantasy"
    SCIENCE_FANTASY = "science_fantasy"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    POST_APOCALYPTIC = "post_apocalyptic"
    HISTORICAL = "historical"
    HORROR = "horror"
    MODERN = "modern"
    SPACE_OPERA = "space_opera"
    SUPERHERO = "superhero"
    WEIRD_WEST = "weird_west"
    NOIR = "noir"

class SettingScale(Enum):
    LOCAL = "local"          # City or region
    REGIONAL = "regional"    # Country or continent
    GLOBAL = "global"        # Entire world
    PLANAR = "planar"        # Multiple planes/dimensions
    COSMIC = "cosmic"        # Galaxy or universe

class ToneStyle(Enum):
    HEROIC = "heroic"
    GRITTY = "gritty"
    COMEDIC = "comedic"
    TRAGIC = "tragic"
    MYSTERIOUS = "mysterious"
    ROMANTIC = "romantic"
    POLITICAL = "political"
    SURVIVAL = "survival"

class ComplexityLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class CampaignSettingStore:
    """Manages campaign setting marketplace"""
    
    def __init__(self):
        self.campaign_settings: Dict[str, CampaignSetting] = {}
        self.setting_collections: Dict[str, Dict[str, Any]] = {}
        self.expansion_packs: Dict[str, List[str]] = {}  # setting_id -> expansion_ids
        self.featured_settings: List[str] = []
        
        # Initialize setting components
        self._initialize_setting_components()
    
    def _initialize_setting_components(self):
        """Initialize campaign setting components and themes"""
        
        self.world_elements = {
            "geography": [
                "continents", "oceans", "mountain_ranges", "forests", "deserts",
                "rivers", "lakes", "islands", "valleys", "plains", "swamps"
            ],
            "climate_zones": [
                "tropical", "temperate", "arctic", "desert", "Mediterranean",
                "monsoon", "tundra", "alpine", "coastal", "continental"
            ],
            "civilizations": [
                "kingdoms", "empires", "city_states", "tribal_nations",
                "theocracies", "republics", "federations", "nomadic_groups"
            ],
            "conflicts": [
                "territorial_wars", "religious_conflicts", "resource_disputes",
                "succession_crises", "trade_wars", "ideological_struggles"
            ],
            "mysteries": [
                "ancient_ruins", "lost_civilizations", "magical_anomalies",
                "unexplored_regions", "divine_interventions", "cosmic_events"
            ]
        }
        
        self.cultural_themes = {
            "medieval_european": {
                "inspirations": ["feudalism", "chivalry", "gothic_architecture"],
                "conflicts": ["dynastic_struggles", "crusades", "peasant_revolts"]
            },
            "ancient_civilizations": {
                "inspirations": ["egyptian", "roman", "greek", "mesopotamian"],
                "conflicts": ["empire_expansion", "religious_upheaval", "barbarian_invasions"]
            },
            "eastern_philosophy": {
                "inspirations": ["taoism", "buddhism", "confucianism", "shinto"],
                "conflicts": ["honor_codes", "spiritual_balance", "clan_warfare"]
            },
            "renaissance": {
                "inspirations": ["humanism", "exploration", "artistic_flourishing"],
                "conflicts": ["city_state_rivalries", "scientific_revolution", "religious_reform"]
            }
        }
        
        self.magic_systems = {
            "high_magic": "Magic is commonplace and powerful",
            "low_magic": "Magic is rare and subtle", 
            "no_magic": "Pure mundane setting",
            "dying_magic": "Magic is fading from the world",
            "wild_magic": "Magic is unpredictable and dangerous",
            "divine_only": "Only divine magic exists",
            "arcane_only": "Only arcane magic exists",
            "psionic": "Mental powers instead of magic"
        }
        
        self.technology_levels = {
            "stone_age": "Primitive tools and weapons",
            "bronze_age": "Early metalworking",
            "iron_age": "Advanced metallurgy",
            "medieval": "Classical fantasy technology",
            "renaissance": "Early firearms and printing",
            "industrial": "Steam power and machinery",
            "modern": "Contemporary technology",
            "futuristic": "Advanced or alien technology"
        }
    
    def create_campaign_setting(
        self,
        creator_id: str,
        name: str,
        description: str,
        genre: SettingGenre,
        scale: SettingScale,
        tone_style: ToneStyle,
        complexity_level: ComplexityLevel,
        magic_system: str,
        technology_level: str,
        key_themes: List[str],
        major_conflicts: List[str],
        notable_locations: List[str] = None,
        important_npcs: List[str] = None,
        page_count: int = 50,
        includes_maps: bool = True,
        includes_adventures: bool = False,
        player_options: List[str] = None,
        price: Decimal = Decimal("0.00")
    ) -> CampaignSetting:
        """Create new campaign setting"""
        
        campaign_setting = CampaignSetting(
            creator_id=creator_id,
            title=name,
            description=description,
            content_type=ContentType.CAMPAIGN_SETTING,
            price=price,
            genre=genre.value,
            scale=scale.value,
            tone_style=tone_style.value,
            complexity_level=complexity_level.value,
            magic_system=magic_system,
            technology_level=technology_level,
            key_themes=key_themes,
            major_conflicts=major_conflicts,
            notable_locations=notable_locations or [],
            important_npcs=important_npcs or [],
            page_count=page_count,
            includes_maps=includes_maps,
            includes_adventures=includes_adventures,
            player_options=player_options or [],
            content_warnings=[],
            recommended_level_range=(1, 20)
        )
        
        self.campaign_settings[campaign_setting.id] = campaign_setting
        return campaign_setting
    
    def add_expansion_pack(
        self,
        base_setting_id: str,
        creator_id: str,
        expansion_name: str,
        expansion_description: str,
        expansion_type: str,  # "region", "timeline", "theme", "rules"
        additional_content: Dict[str, Any],
        price: Decimal = Decimal("0.00")
    ) -> Optional[str]:
        """Add expansion pack to existing setting"""
        
        if base_setting_id not in self.campaign_settings:
            return None
        
        base_setting = self.campaign_settings[base_setting_id]
        
        # Verify creator can add expansion
        if base_setting.creator_id != creator_id:
            return None
        
        expansion_id = f"exp_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        expansion = CampaignSetting(
            creator_id=creator_id,
            title=f"{base_setting.title}: {expansion_name}",
            description=expansion_description,
            content_type=ContentType.CAMPAIGN_SETTING,
            price=price,
            genre=base_setting.genre,
            scale=base_setting.scale,
            tone_style=base_setting.tone_style,
            complexity_level=base_setting.complexity_level,
            magic_system=base_setting.magic_system,
            technology_level=base_setting.technology_level,
            key_themes=additional_content.get("themes", []),
            major_conflicts=additional_content.get("conflicts", []),
            notable_locations=additional_content.get("locations", []),
            important_npcs=additional_content.get("npcs", []),
            page_count=additional_content.get("page_count", 20),
            includes_maps=additional_content.get("includes_maps", True),
            includes_adventures=additional_content.get("includes_adventures", False),
            player_options=additional_content.get("player_options", []),
            parent_setting_id=base_setting_id,
            expansion_type=expansion_type
        )
        
        self.campaign_settings[expansion_id] = expansion
        
        # Track expansion relationship
        if base_setting_id not in self.expansion_packs:
            self.expansion_packs[base_setting_id] = []
        self.expansion_packs[base_setting_id].append(expansion_id)
        
        return expansion_id
    
    def search_campaign_settings(
        self,
        query: Optional[str] = None,
        genre: Optional[SettingGenre] = None,
        scale: Optional[SettingScale] = None,
        tone_style: Optional[ToneStyle] = None,
        complexity_level: Optional[ComplexityLevel] = None,
        magic_system: Optional[str] = None,
        technology_level: Optional[str] = None,
        key_themes: List[str] = None,
        includes_maps: Optional[bool] = None,
        includes_adventures: Optional[bool] = None,
        page_count_min: Optional[int] = None,
        page_count_max: Optional[int] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        level_range: Optional[tuple] = None,
        creator_id: Optional[str] = None,
        exclude_expansions: bool = False,
        sort_by: str = "relevance"
    ) -> List[CampaignSetting]:
        """Search campaign settings with filters"""
        
        results = []
        
        for setting in self.campaign_settings.values():
            if setting.status != ProductStatus.ACTIVE:
                continue
            
            # Exclude expansion packs if requested
            if exclude_expansions and hasattr(setting, 'parent_setting_id') and setting.parent_setting_id:
                continue
            
            # Text search
            if query:
                search_text = f"{setting.title} {setting.description} {' '.join(setting.key_themes)} {' '.join(setting.major_conflicts)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Genre filter
            if genre and setting.genre != genre.value:
                continue
            
            # Scale filter
            if scale and setting.scale != scale.value:
                continue
            
            # Tone filter
            if tone_style and setting.tone_style != tone_style.value:
                continue
            
            # Complexity filter
            if complexity_level and setting.complexity_level != complexity_level.value:
                continue
            
            # Magic system filter
            if magic_system and setting.magic_system != magic_system:
                continue
            
            # Technology level filter
            if technology_level and setting.technology_level != technology_level:
                continue
            
            # Theme filter
            if key_themes:
                setting_themes = set(setting.key_themes)
                required_themes = set(key_themes)
                if not required_themes.issubset(setting_themes):
                    continue
            
            # Map inclusion filter
            if includes_maps is not None and setting.includes_maps != includes_maps:
                continue
            
            # Adventure inclusion filter
            if includes_adventures is not None and setting.includes_adventures != includes_adventures:
                continue
            
            # Page count filter
            if page_count_min and setting.page_count < page_count_min:
                continue
            if page_count_max and setting.page_count > page_count_max:
                continue
            
            # Price filter
            if price_min and setting.price < price_min:
                continue
            if price_max and setting.price > price_max:
                continue
            
            # Level range filter
            if level_range:
                min_level, max_level = level_range
                setting_min, setting_max = setting.recommended_level_range
                # Check for overlap
                if setting_max < min_level or setting_min > max_level:
                    continue
            
            # Creator filter
            if creator_id and setting.creator_id != creator_id:
                continue
            
            results.append(setting)
        
        # Sort results
        if sort_by == "price_low":
            results.sort(key=lambda s: s.price)
        elif sort_by == "price_high":
            results.sort(key=lambda s: s.price, reverse=True)
        elif sort_by == "page_count":
            results.sort(key=lambda s: s.page_count, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda s: s.created_at, reverse=True)
        elif sort_by == "popular":
            results.sort(key=lambda s: (s.download_count, s.average_rating), reverse=True)
        else:  # relevance
            results.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        
        return results
    
    def get_setting_details(self, setting_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed campaign setting information"""
        
        if setting_id not in self.campaign_settings:
            return None
        
        setting = self.campaign_settings[setting_id]
        
        return {
            "setting": setting.dict(),
            "creator_info": self._get_creator_info(setting.creator_id),
            "world_overview": self._generate_world_overview(setting),
            "content_breakdown": self._get_content_breakdown(setting),
            "expansion_packs": self._get_expansion_packs(setting_id),
            "similar_settings": self._get_similar_settings(setting),
            "player_resources": self._get_player_resources(setting),
            "dm_resources": self._get_dm_resources(setting),
            "compatibility_info": self._get_compatibility_info(setting)
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get setting creator information"""
        
        creator_settings = [s for s in self.campaign_settings.values() if s.creator_id == creator_id]
        active_settings = [s for s in creator_settings if s.status == ProductStatus.ACTIVE]
        
        total_downloads = sum(s.download_count for s in active_settings)
        avg_rating = sum(s.average_rating for s in active_settings) / len(active_settings) if active_settings else 0
        total_pages = sum(s.page_count for s in active_settings)
        
        return {
            "id": creator_id,
            "name": f"World Builder {creator_id[:8]}",
            "total_settings": len(active_settings),
            "total_pages": total_pages,
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
            "specialties": self._get_creator_specialties(creator_id),
            "verified": len(active_settings) >= 3
        }
    
    def _get_creator_specialties(self, creator_id: str) -> List[str]:
        """Determine creator's specialties"""
        
        creator_settings = [s for s in self.campaign_settings.values() 
                          if s.creator_id == creator_id and s.status == ProductStatus.ACTIVE]
        
        # Count genres and scales
        genre_counts = {}
        scale_counts = {}
        
        for setting in creator_settings:
            genre_counts[setting.genre] = genre_counts.get(setting.genre, 0) + 1
            scale_counts[setting.scale] = scale_counts.get(setting.scale, 0) + 1
        
        specialties = []
        
        # Top genre
        if genre_counts:
            top_genre = max(genre_counts.items(), key=lambda x: x[1])
            specialties.append(f"{top_genre[0].replace('_', ' ')} settings")
        
        # Top scale
        if scale_counts:
            top_scale = max(scale_counts.items(), key=lambda x: x[1])
            specialties.append(f"{top_scale[0]} scope worldbuilding")
        
        # Special features
        map_maker = sum(1 for s in creator_settings if s.includes_maps) > len(creator_settings) * 0.7
        if map_maker:
            specialties.append("detailed cartography")
        
        adventure_writer = sum(1 for s in creator_settings if s.includes_adventures) > len(creator_settings) * 0.5
        if adventure_writer:
            specialties.append("integrated adventures")
        
        return specialties[:3]
    
    def _generate_world_overview(self, setting: CampaignSetting) -> Dict[str, Any]:
        """Generate comprehensive world overview"""
        
        return {
            "world_summary": {
                "genre": setting.genre.replace('_', ' ').title(),
                "scale": setting.scale.replace('_', ' ').title(),
                "tone": setting.tone_style.replace('_', ' ').title(),
                "magic_level": setting.magic_system.replace('_', ' ').title(),
                "technology": setting.technology_level.replace('_', ' ').title()
            },
            "key_features": {
                "themes": setting.key_themes,
                "conflicts": setting.major_conflicts,
                "locations": setting.notable_locations[:5],  # Show top 5
                "important_figures": setting.important_npcs[:5]
            },
            "gameplay_elements": {
                "recommended_levels": f"{setting.recommended_level_range[0]}-{setting.recommended_level_range[1]}",
                "complexity": setting.complexity_level.replace('_', ' ').title(),
                "player_options": setting.player_options,
                "includes_adventures": setting.includes_adventures,
                "includes_maps": setting.includes_maps
            },
            "content_warnings": setting.content_warnings if setting.content_warnings else ["None listed"]
        }
    
    def _get_content_breakdown(self, setting: CampaignSetting) -> Dict[str, Any]:
        """Get detailed content breakdown"""
        
        estimated_breakdown = {
            "total_pages": setting.page_count,
            "sections": {
                "world_overview": int(setting.page_count * 0.15),
                "geography": int(setting.page_count * 0.20),
                "history_timeline": int(setting.page_count * 0.15),
                "cultures_civilizations": int(setting.page_count * 0.20),
                "notable_locations": int(setting.page_count * 0.15),
                "important_npcs": int(setting.page_count * 0.10),
                "appendices": int(setting.page_count * 0.05)
            }
        }
        
        # Adjust based on includes
        if setting.includes_maps:
            estimated_breakdown["sections"]["maps"] = int(setting.page_count * 0.10)
            # Reduce other sections proportionally
            for section in ["geography", "notable_locations"]:
                estimated_breakdown["sections"][section] = int(estimated_breakdown["sections"][section] * 0.9)
        
        if setting.includes_adventures:
            estimated_breakdown["sections"]["adventures"] = int(setting.page_count * 0.25)
            # Reduce other sections proportionally
            for section in estimated_breakdown["sections"]:
                if section not in ["adventures", "maps"]:
                    estimated_breakdown["sections"][section] = int(estimated_breakdown["sections"][section] * 0.8)
        
        return estimated_breakdown
    
    def _get_expansion_packs(self, setting_id: str) -> List[Dict[str, Any]]:
        """Get expansion packs for setting"""
        
        expansions = []
        expansion_ids = self.expansion_packs.get(setting_id, [])
        
        for exp_id in expansion_ids:
            if exp_id in self.campaign_settings:
                expansion = self.campaign_settings[exp_id]
                if expansion.status == ProductStatus.ACTIVE:
                    expansions.append({
                        "expansion": expansion.dict(),
                        "type": getattr(expansion, 'expansion_type', 'unknown'),
                        "preview": self._generate_expansion_preview(expansion)
                    })
        
        return expansions
    
    def _generate_expansion_preview(self, expansion: CampaignSetting) -> Dict[str, Any]:
        """Generate expansion preview"""
        
        return {
            "new_locations": len(expansion.notable_locations),
            "new_npcs": len(expansion.important_npcs),
            "new_conflicts": len(expansion.major_conflicts),
            "additional_pages": expansion.page_count,
            "key_additions": expansion.key_themes[:3]
        }
    
    def _get_similar_settings(self, setting: CampaignSetting) -> List[CampaignSetting]:
        """Find similar campaign settings"""
        
        similar = []
        
        for other in self.campaign_settings.values():
            if (other.id == setting.id or 
                other.status != ProductStatus.ACTIVE or
                (hasattr(other, 'parent_setting_id') and other.parent_setting_id)):
                continue
            
            similarity_score = 0
            
            # Same genre
            if other.genre == setting.genre:
                similarity_score += 3
            
            # Same scale
            if other.scale == setting.scale:
                similarity_score += 2
            
            # Same tone
            if other.tone_style == setting.tone_style:
                similarity_score += 2
            
            # Common themes
            common_themes = set(setting.key_themes) & set(other.key_themes)
            similarity_score += len(common_themes)
            
            # Similar magic/tech level
            if other.magic_system == setting.magic_system:
                similarity_score += 1
            if other.technology_level == setting.technology_level:
                similarity_score += 1
            
            # Similar complexity
            if other.complexity_level == setting.complexity_level:
                similarity_score += 1
            
            if similarity_score >= 4:
                similar.append(other)
        
        similar.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        return similar[:6]
    
    def _get_player_resources(self, setting: CampaignSetting) -> Dict[str, Any]:
        """Get player-facing resources"""
        
        return {
            "character_options": setting.player_options,
            "background_info": {
                "world_primer": f"Essential knowledge about {setting.title}",
                "cultural_notes": "Key cultural information for roleplay",
                "language_guide": "Common languages and phrases" if setting.includes_maps else None
            },
            "reference_materials": {
                "location_gazetteer": "Quick reference for major locations",
                "npc_directory": "Important figures players might encounter",
                "timeline": "Historical events and current year"
            },
            "player_aids": {
                "maps": setting.includes_maps,
                "handouts": True,
                "quick_rules": setting.complexity_level != ComplexityLevel.EXPERT.value
            }
        }
    
    def _get_dm_resources(self, setting: CampaignSetting) -> Dict[str, Any]:
        """Get DM-facing resources"""
        
        return {
            "campaign_tools": {
                "adventure_hooks": len(setting.major_conflicts) * 3,  # Estimate
                "random_encounters": "Themed encounter tables",
                "plot_threads": "Interconnected storylines",
                "npc_relationships": "Social network diagrams"
            },
            "world_details": {
                "detailed_locations": len(setting.notable_locations),
                "npc_stat_blocks": len(setting.important_npcs),
                "organization_details": "Factions and their motivations",
                "economic_systems": "Trade routes and currencies"
            },
            "campaign_support": {
                "session_zero_guide": "Setting introduction materials",
                "player_handouts": "Printable reference materials",
                "scaling_advice": f"Adapting for levels {setting.recommended_level_range[0]}-{setting.recommended_level_range[1]}",
                "variant_rules": setting.complexity_level in [ComplexityLevel.ADVANCED.value, ComplexityLevel.EXPERT.value]
            }
        }
    
    def _get_compatibility_info(self, setting: CampaignSetting) -> Dict[str, Any]:
        """Get compatibility information"""
        
        return {
            "game_systems": {
                "primary": "D&D 5e",  # Default assumption
                "adaptable_to": ["Pathfinder 2e", "OSR games", "Generic systems"],
                "conversion_notes": setting.complexity_level != ComplexityLevel.BEGINNER.value
            },
            "existing_campaigns": {
                "can_integrate": setting.scale in [SettingScale.LOCAL.value, SettingScale.REGIONAL.value],
                "replacement_setting": setting.scale in [SettingScale.GLOBAL.value, SettingScale.PLANAR.value, SettingScale.COSMIC.value],
                "crossover_potential": "high" if setting.genre in [SettingGenre.HIGH_FANTASY.value, SettingGenre.URBAN_FANTASY.value] else "moderate"
            },
            "content_maturity": {
                "age_appropriate": "teen+" if setting.content_warnings else "all_ages",
                "content_warnings": setting.content_warnings,
                "safety_tools": "Recommended" if setting.content_warnings else "Optional"
            }
        }
    
    def create_setting_collection(
        self,
        creator_id: str,
        collection_name: str,
        description: str,
        theme: str,
        setting_ids: List[str],
        bundle_price: Optional[Decimal] = None
    ) -> str:
        """Create campaign setting collection"""
        
        # Validate settings
        valid_settings = []
        total_individual_price = Decimal("0.00")
        total_pages = 0
        
        for setting_id in setting_ids:
            if setting_id in self.campaign_settings:
                setting = self.campaign_settings[setting_id]
                if (setting.creator_id == creator_id and 
                    setting.status == ProductStatus.ACTIVE):
                    valid_settings.append(setting_id)
                    total_individual_price += setting.price
                    total_pages += setting.page_count
        
        if not valid_settings:
            return ""
        
        # Calculate bundle price (20% discount if not specified)
        if bundle_price is None:
            bundle_price = total_individual_price * Decimal("0.8")
        
        collection_id = f"collection_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        collection = {
            "id": collection_id,
            "creator_id": creator_id,
            "name": collection_name,
            "description": description,
            "theme": theme,
            "setting_ids": valid_settings,
            "bundle_price": bundle_price,
            "individual_price": total_individual_price,
            "savings": total_individual_price - bundle_price,
            "total_pages": total_pages,
            "setting_count": len(valid_settings),
            "created_at": datetime.utcnow(),
            "download_count": 0,
            "average_rating": Decimal("0.0")
        }
        
        self.setting_collections[collection_id] = collection
        return collection_id
    
    def get_genre_recommendations(self, genre: SettingGenre, count: int = 8) -> List[CampaignSetting]:
        """Get recommendations for specific genre"""
        
        genre_settings = [
            s for s in self.campaign_settings.values()
            if (s.status == ProductStatus.ACTIVE and 
                s.genre == genre.value and
                not (hasattr(s, 'parent_setting_id') and s.parent_setting_id))
        ]
        
        # Sort by quality and popularity
        genre_settings.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        return genre_settings[:count]
    
    def get_beginner_friendly_settings(self, count: int = 6) -> List[CampaignSetting]:
        """Get beginner-friendly campaign settings"""
        
        beginner_settings = [
            s for s in self.campaign_settings.values()
            if (s.status == ProductStatus.ACTIVE and
                s.complexity_level == ComplexityLevel.BEGINNER.value and
                not (hasattr(s, 'parent_setting_id') and s.parent_setting_id))
        ]
        
        beginner_settings.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        return beginner_settings[:count]
    
    def get_complete_world_packages(self, count: int = 10) -> List[CampaignSetting]:
        """Get comprehensive world packages"""
        
        complete_worlds = [
            s for s in self.campaign_settings.values()
            if (s.status == ProductStatus.ACTIVE and
                s.scale in [SettingScale.GLOBAL.value, SettingScale.PLANAR.value] and
                s.page_count >= 100 and
                s.includes_maps and
                not (hasattr(s, 'parent_setting_id') and s.parent_setting_id))
        ]
        
        complete_worlds.sort(key=lambda s: (s.page_count, s.average_rating), reverse=True)
        return complete_worlds[:count]
    
    def get_trending_settings(self, days: int = 30) -> List[CampaignSetting]:
        """Get trending campaign settings"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending = []
        for setting in self.campaign_settings.values():
            if (setting.status != ProductStatus.ACTIVE or
                (hasattr(setting, 'parent_setting_id') and setting.parent_setting_id)):
                continue
            
            # Calculate trend score
            trend_score = setting.download_count + (float(setting.average_rating) * 20)
            
            # Bonus for recent high-quality releases
            if setting.created_at >= cutoff_date and setting.average_rating >= Decimal("4.0"):
                trend_score += 50
            
            trending.append({
                "setting": setting,
                "trend_score": trend_score
            })
        
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        return [item["setting"] for item in trending[:15]]
    
    def get_setting_by_theme(self, theme: str, count: int = 12) -> List[CampaignSetting]:
        """Get settings by specific theme"""
        
        themed_settings = []
        
        for setting in self.campaign_settings.values():
            if (setting.status == ProductStatus.ACTIVE and
                not (hasattr(setting, 'parent_setting_id') and setting.parent_setting_id)):
                
                # Check if theme appears in key themes or description
                if (theme.lower() in [t.lower() for t in setting.key_themes] or
                    theme.lower() in setting.description.lower() or
                    theme.lower() in setting.title.lower()):
                    themed_settings.append(setting)
        
        themed_settings.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        return themed_settings[:count]