"""
Virtual dice skin and customization store
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import DiceSkin, Product, ContentType, ProductStatus

class DiceType(Enum):
    D4 = "d4"
    D6 = "d6"
    D8 = "d8"
    D10 = "d10"
    D12 = "d12"
    D20 = "d20"
    D100 = "d100"
    CUSTOM = "custom"

class SkinCategory(Enum):
    FANTASY = "fantasy"
    MODERN = "modern"
    HORROR = "horror"
    STEAMPUNK = "steampunk"
    CYBERPUNK = "cyberpunk"
    MEDIEVAL = "medieval"
    NATURE = "nature"
    ELEMENTAL = "elemental"
    METALLIC = "metallic"
    GEMSTONE = "gemstone"
    WOODEN = "wooden"
    CRYSTAL = "crystal"
    BONE = "bone"
    NEON = "neon"
    HOLOGRAPHIC = "holographic"

class AnimationStyle(Enum):
    NONE = "none"
    SIMPLE = "simple"
    PHYSICS = "physics"
    MAGICAL = "magical"
    PARTICLE_EFFECTS = "particle_effects"
    TRAIL_EFFECTS = "trail_effects"

class SoundCategory(Enum):
    SILENT = "silent"
    CLASSIC = "classic"
    WOODEN = "wooden"
    METALLIC = "metallic"
    MAGICAL = "magical"
    ELECTRONIC = "electronic"
    NATURAL = "natural"

class DiceSkinStore:
    """Manages virtual dice skins and customizations"""
    
    def __init__(self):
        self.dice_skins: Dict[str, DiceSkin] = {}
        self.skin_sets: Dict[str, Dict[str, Any]] = {}
        self.user_collections: Dict[str, List[str]] = {}  # user_id -> skin_ids
        self.featured_skins: List[str] = []
        
        # Initialize skin categories and effects
        self._initialize_skin_categories()
    
    def _initialize_skin_categories(self):
        """Initialize dice skin categories and visual effects"""
        
        self.visual_effects = {
            "materials": {
                "metal": ["gold", "silver", "copper", "bronze", "platinum", "iron"],
                "gemstone": ["ruby", "sapphire", "emerald", "diamond", "amethyst", "obsidian"],
                "wood": ["oak", "mahogany", "ebony", "birch", "walnut", "bamboo"],
                "crystal": ["clear", "frosted", "colored", "iridescent", "prism"],
                "bone": ["aged", "polished", "carved", "rune_inscribed"],
                "stone": ["marble", "granite", "sandstone", "slate", "jade"]
            },
            "surface_effects": {
                "texture": ["smooth", "rough", "carved", "etched", "polished"],
                "pattern": ["solid", "marbled", "speckled", "striped", "geometric"],
                "finish": ["matte", "glossy", "metallic", "pearlescent", "holographic"]
            },
            "special_effects": {
                "glow": ["soft_glow", "bright_glow", "pulsing", "breathing", "flickering"],
                "particles": ["sparkles", "flames", "smoke", "lightning", "frost"],
                "aura": ["energy_field", "magical_circle", "elemental_swirl", "shadow"]
            }
        }
        
        self.theme_collections = {
            "elemental": {
                "fire": {"colors": ["red", "orange", "yellow"], "effects": ["flames", "ember_particles"]},
                "water": {"colors": ["blue", "cyan", "white"], "effects": ["water_droplets", "wave_patterns"]},
                "earth": {"colors": ["brown", "green", "gray"], "effects": ["rock_texture", "plant_growth"]},
                "air": {"colors": ["white", "light_blue", "silver"], "effects": ["wind_swirls", "feather_particles"]}
            },
            "class_themed": {
                "fighter": {"materials": ["metal", "leather"], "colors": ["steel", "brown"]},
                "wizard": {"materials": ["crystal", "glass"], "effects": ["arcane_symbols", "magical_particles"]},
                "rogue": {"materials": ["obsidian", "shadow"], "colors": ["black", "dark_purple"]},
                "cleric": {"materials": ["gold", "silver"], "effects": ["holy_light", "divine_symbols"]}
            }
        }
        
        self.dice_fonts = [
            "classic", "medieval", "runic", "elvish", "dwarven", "modern",
            "script", "bold", "ornate", "minimal", "techno", "organic"
        ]
    
    def create_dice_skin(
        self,
        creator_id: str,
        name: str,
        description: str,
        category: SkinCategory,
        dice_types: List[DiceType],
        base_material: str,
        colors: List[str],
        pattern: Optional[str] = None,
        texture: Optional[str] = None,
        finish: Optional[str] = None,
        animation_style: AnimationStyle = AnimationStyle.NONE,
        sound_category: SoundCategory = SoundCategory.CLASSIC,
        special_effects: List[str] = None,
        font_style: str = "classic",
        price: Decimal = Decimal("0.00"),
        is_animated: bool = False,
        supports_vtt: bool = True
    ) -> DiceSkin:
        """Create new dice skin"""
        
        dice_skin = DiceSkin(
            creator_id=creator_id,
            title=name,
            description=description,
            content_type=ContentType.DICE_SKIN,
            price=price,
            category=category.value,
            dice_types=[dt.value for dt in dice_types],
            base_material=base_material,
            colors=colors,
            pattern=pattern,
            texture=texture,
            finish=finish,
            animation_style=animation_style.value,
            sound_category=sound_category.value,
            special_effects=special_effects or [],
            font_style=font_style,
            is_animated=is_animated,
            supports_vtt=supports_vtt,
            preview_images=[],
            technical_specs={}
        )
        
        # Generate technical specs
        dice_skin.technical_specs = self._generate_technical_specs(dice_skin)
        
        self.dice_skins[dice_skin.id] = dice_skin
        return dice_skin
    
    def _generate_technical_specs(self, dice_skin: DiceSkin) -> Dict[str, Any]:
        """Generate technical specifications for dice skin"""
        
        specs = {
            "supported_dice": dice_skin.dice_types,
            "resolution": "1024x1024" if dice_skin.is_animated else "512x512",
            "file_format": "PNG with alpha channel",
            "animation_format": "GIF/MP4" if dice_skin.is_animated else "Static",
            "file_size_estimate": self._estimate_file_size(dice_skin),
            "vtt_compatibility": dice_skin.supports_vtt,
            "mobile_optimized": True,
            "3d_rendered": True
        }
        
        if dice_skin.sound_category != SoundCategory.SILENT.value:
            specs.update({
                "includes_sound": True,
                "sound_format": "OGG/MP3",
                "sound_count": len(dice_skin.dice_types) * 2  # Roll + land sounds
            })
        
        return specs
    
    def _estimate_file_size(self, dice_skin: DiceSkin) -> str:
        """Estimate total file size for dice skin"""
        
        base_size_per_die = 0.5  # MB for static image
        if dice_skin.is_animated:
            base_size_per_die = 2.0  # MB for animated
        
        total_size = len(dice_skin.dice_types) * base_size_per_die
        
        # Add size for special effects
        if dice_skin.special_effects:
            total_size += len(dice_skin.special_effects) * 0.3
        
        # Add size for sounds
        if dice_skin.sound_category != SoundCategory.SILENT.value:
            total_size += len(dice_skin.dice_types) * 0.1  # Sound files
        
        return f"~{total_size:.1f} MB"
    
    def create_dice_set(
        self,
        creator_id: str,
        set_name: str,
        description: str,
        theme: str,
        skin_ids: List[str],
        set_price: Optional[Decimal] = None
    ) -> str:
        """Create dice skin set/collection"""
        
        # Validate skins exist and belong to creator
        valid_skins = []
        total_individual_price = Decimal("0.00")
        
        for skin_id in skin_ids:
            if skin_id in self.dice_skins:
                skin = self.dice_skins[skin_id]
                if skin.creator_id == creator_id:
                    valid_skins.append(skin_id)
                    total_individual_price += skin.price
        
        if not valid_skins:
            return ""
        
        # Calculate set price (10% discount if not specified)
        if set_price is None:
            set_price = total_individual_price * Decimal("0.9")
        
        set_id = f"set_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{creator_id[:8]}"
        
        dice_set = {
            "id": set_id,
            "creator_id": creator_id,
            "name": set_name,
            "description": description,
            "theme": theme,
            "skin_ids": valid_skins,
            "set_price": set_price,
            "individual_price": total_individual_price,
            "savings": total_individual_price - set_price,
            "created_at": datetime.utcnow(),
            "download_count": 0,
            "average_rating": Decimal("0.0"),
            "preview_image": f"https://dice.marketplace.com/sets/{set_id}/preview.jpg"
        }
        
        self.skin_sets[set_id] = dice_set
        return set_id
    
    def search_dice_skins(
        self,
        query: Optional[str] = None,
        category: Optional[SkinCategory] = None,
        dice_types: List[DiceType] = None,
        base_material: Optional[str] = None,
        colors: List[str] = None,
        animation_style: Optional[AnimationStyle] = None,
        sound_category: Optional[SoundCategory] = None,
        special_effects: List[str] = None,
        is_animated: Optional[bool] = None,
        supports_vtt: Optional[bool] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        creator_id: Optional[str] = None,
        sort_by: str = "relevance"
    ) -> List[DiceSkin]:
        """Search dice skins with filters"""
        
        results = []
        
        for skin in self.dice_skins.values():
            if skin.status != ProductStatus.ACTIVE:
                continue
            
            # Text search
            if query:
                search_text = f"{skin.title} {skin.description} {skin.category} {skin.base_material} {' '.join(skin.colors)}".lower()
                if query.lower() not in search_text:
                    continue
            
            # Category filter
            if category and skin.category != category.value:
                continue
            
            # Dice types filter
            if dice_types:
                required_types = set(dt.value for dt in dice_types)
                skin_types = set(skin.dice_types)
                if not required_types.issubset(skin_types):
                    continue
            
            # Material filter
            if base_material and skin.base_material != base_material:
                continue
            
            # Colors filter
            if colors:
                skin_colors = set(skin.colors)
                required_colors = set(colors)
                if not required_colors.intersection(skin_colors):
                    continue
            
            # Animation filter
            if animation_style and skin.animation_style != animation_style.value:
                continue
            
            # Sound filter
            if sound_category and skin.sound_category != sound_category.value:
                continue
            
            # Special effects filter
            if special_effects:
                skin_effects = set(skin.special_effects)
                required_effects = set(special_effects)
                if not required_effects.issubset(skin_effects):
                    continue
            
            # Animation flag filter
            if is_animated is not None and skin.is_animated != is_animated:
                continue
            
            # VTT support filter
            if supports_vtt is not None and skin.supports_vtt != supports_vtt:
                continue
            
            # Price filter
            if price_min and skin.price < price_min:
                continue
            if price_max and skin.price > price_max:
                continue
            
            # Creator filter
            if creator_id and skin.creator_id != creator_id:
                continue
            
            results.append(skin)
        
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
    
    def get_dice_skin_details(self, skin_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed dice skin information"""
        
        if skin_id not in self.dice_skins:
            return None
        
        skin = self.dice_skins[skin_id]
        
        return {
            "dice_skin": skin.dict(),
            "creator_info": self._get_creator_info(skin.creator_id),
            "preview_gallery": self._generate_preview_gallery(skin),
            "technical_details": skin.technical_specs,
            "compatibility_info": self._get_compatibility_info(skin),
            "similar_skins": self._get_similar_skins(skin),
            "usage_instructions": self._get_usage_instructions(skin)
        }
    
    def _get_creator_info(self, creator_id: str) -> Dict[str, Any]:
        """Get dice skin creator information"""
        
        creator_skins = [s for s in self.dice_skins.values() if s.creator_id == creator_id]
        active_skins = [s for s in creator_skins if s.status == ProductStatus.ACTIVE]
        
        total_downloads = sum(s.download_count for s in active_skins)
        avg_rating = sum(s.average_rating for s in active_skins) / len(active_skins) if active_skins else 0
        
        return {
            "id": creator_id,
            "name": f"Dice Designer {creator_id[:8]}",
            "total_skins": len(active_skins),
            "total_downloads": total_downloads,
            "average_rating": round(avg_rating, 2),
            "specialties": self._get_creator_specialties(creator_id),
            "verified": len(active_skins) >= 10
        }
    
    def _get_creator_specialties(self, creator_id: str) -> List[str]:
        """Determine creator's specialties"""
        
        creator_skins = [s for s in self.dice_skins.values() 
                        if s.creator_id == creator_id and s.status == ProductStatus.ACTIVE]
        
        # Count categories
        category_counts = {}
        material_counts = {}
        
        for skin in creator_skins:
            category_counts[skin.category] = category_counts.get(skin.category, 0) + 1
            material_counts[skin.base_material] = material_counts.get(skin.base_material, 0) + 1
        
        specialties = []
        
        # Top category
        if category_counts:
            top_category = max(category_counts.items(), key=lambda x: x[1])
            specialties.append(f"{top_category[0]} themes")
        
        # Top material
        if material_counts:
            top_material = max(material_counts.items(), key=lambda x: x[1])
            specialties.append(f"{top_material[0]} materials")
        
        # Animation specialty
        animated_count = sum(1 for skin in creator_skins if skin.is_animated)
        if animated_count > len(creator_skins) * 0.5:
            specialties.append("animated effects")
        
        return specialties[:3]
    
    def _generate_preview_gallery(self, skin: DiceSkin) -> List[Dict[str, str]]:
        """Generate preview image gallery"""
        
        gallery = []
        base_url = f"https://dice.marketplace.com/previews/{skin.id}"
        
        # Individual die previews
        for die_type in skin.dice_types:
            gallery.append({
                "type": "individual_die",
                "die_type": die_type,
                "url": f"{base_url}/{die_type}_preview.png",
                "description": f"{die_type.upper()} preview"
            })
        
        # Set preview
        gallery.append({
            "type": "full_set",
            "die_type": "all",
            "url": f"{base_url}/set_preview.png",
            "description": "Complete dice set"
        })
        
        # Animation preview if animated
        if skin.is_animated:
            gallery.append({
                "type": "animation",
                "die_type": "d20",
                "url": f"{base_url}/animation_preview.gif",
                "description": "Rolling animation preview"
            })
        
        # Special effects preview
        if skin.special_effects:
            gallery.append({
                "type": "effects",
                "die_type": "d20",
                "url": f"{base_url}/effects_preview.png",
                "description": "Special effects showcase"
            })
        
        return gallery
    
    def _get_compatibility_info(self, skin: DiceSkin) -> Dict[str, Any]:
        """Get compatibility information"""
        
        return {
            "vtt_platforms": {
                "roll20": skin.supports_vtt,
                "foundry": skin.supports_vtt,
                "fantasy_grounds": skin.supports_vtt,
                "tabletop_simulator": True,
                "astral": skin.supports_vtt
            },
            "mobile_devices": {
                "ios": True,
                "android": True,
                "tablets": True
            },
            "desktop_platforms": {
                "windows": True,
                "mac": True,
                "linux": True
            },
            "file_formats": {
                "images": ["PNG", "JPG"],
                "animations": ["GIF", "MP4"] if skin.is_animated else [],
                "sounds": ["OGG", "MP3"] if skin.sound_category != SoundCategory.SILENT.value else []
            }
        }
    
    def _get_similar_skins(self, skin: DiceSkin) -> List[DiceSkin]:
        """Find similar dice skins"""
        
        similar = []
        
        for other in self.dice_skins.values():
            if other.id == skin.id or other.status != ProductStatus.ACTIVE:
                continue
            
            similarity_score = 0
            
            # Same category
            if other.category == skin.category:
                similarity_score += 3
            
            # Same material
            if other.base_material == skin.base_material:
                similarity_score += 2
            
            # Common colors
            common_colors = set(skin.colors) & set(other.colors)
            similarity_score += len(common_colors)
            
            # Same animation style
            if other.animation_style == skin.animation_style:
                similarity_score += 1
            
            # Common special effects
            common_effects = set(skin.special_effects) & set(other.special_effects)
            similarity_score += len(common_effects)
            
            # Same creator
            if other.creator_id == skin.creator_id:
                similarity_score += 1
            
            if similarity_score >= 3:
                similar.append(other)
        
        similar.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        return similar[:6]
    
    def _get_usage_instructions(self, skin: DiceSkin) -> Dict[str, List[str]]:
        """Generate usage instructions for different platforms"""
        
        return {
            "general": [
                "Download the dice skin package",
                "Extract files to your dice application folder",
                "Select the skin from your dice collection",
                "Enjoy rolling with your custom dice!"
            ],
            "vtt_specific": {
                "roll20": [
                    "Upload dice images to your art library",
                    "Create custom dice macros using the images",
                    "Configure dice sounds in settings"
                ],
                "foundry": [
                    "Install via the dice customization module",
                    "Place files in the dice-skins folder",
                    "Activate in module settings"
                ]
            } if skin.supports_vtt else {},
            "mobile": [
                "Import dice skin through app settings",
                "Apply to your dice collection",
                "Customize individual die types as needed"
            ]
        }
    
    def get_user_dice_collection(self, user_id: str) -> Dict[str, Any]:
        """Get user's dice skin collection"""
        
        user_skins = self.user_collections.get(user_id, [])
        owned_skins = [self.dice_skins[skin_id] for skin_id in user_skins 
                      if skin_id in self.dice_skins]
        
        # Group by category
        skins_by_category = {}
        for skin in owned_skins:
            if skin.category not in skins_by_category:
                skins_by_category[skin.category] = []
            skins_by_category[skin.category].append(skin)
        
        # Group by dice type coverage
        dice_type_coverage = {}
        for die_type in [dt.value for dt in DiceType]:
            dice_type_coverage[die_type] = [
                skin for skin in owned_skins 
                if die_type in skin.dice_types
            ]
        
        return {
            "total_skins": len(owned_skins),
            "skins_by_category": skins_by_category,
            "dice_type_coverage": dice_type_coverage,
            "favorite_skins": owned_skins[:5],  # Assume first 5 are favorites
            "recent_purchases": sorted(owned_skins, key=lambda s: s.created_at, reverse=True)[:3],
            "collection_value": sum(skin.price for skin in owned_skins),
            "completion_stats": self._calculate_collection_completeness(owned_skins)
        }
    
    def _calculate_collection_completeness(self, owned_skins: List[DiceSkin]) -> Dict[str, Any]:
        """Calculate collection completeness statistics"""
        
        # Calculate coverage by category
        all_categories = set(skin.category for skin in self.dice_skins.values())
        owned_categories = set(skin.category for skin in owned_skins)
        
        # Calculate coverage by material
        all_materials = set(skin.base_material for skin in self.dice_skins.values())
        owned_materials = set(skin.base_material for skin in owned_skins)
        
        # Calculate dice type coverage
        all_dice_types = set()
        owned_dice_types = set()
        
        for skin in self.dice_skins.values():
            all_dice_types.update(skin.dice_types)
        
        for skin in owned_skins:
            owned_dice_types.update(skin.dice_types)
        
        return {
            "category_completion": f"{len(owned_categories)}/{len(all_categories)}",
            "category_percentage": int((len(owned_categories) / len(all_categories)) * 100) if all_categories else 0,
            "material_completion": f"{len(owned_materials)}/{len(all_materials)}",
            "material_percentage": int((len(owned_materials) / len(all_materials)) * 100) if all_materials else 0,
            "dice_type_completion": f"{len(owned_dice_types)}/{len(all_dice_types)}",
            "dice_type_percentage": int((len(owned_dice_types) / len(all_dice_types)) * 100) if all_dice_types else 0
        }
    
    def get_recommended_skins(self, user_id: str, count: int = 10) -> List[Dict[str, Any]]:
        """Get personalized dice skin recommendations"""
        
        user_skins = self.user_collections.get(user_id, [])
        owned_skins = [self.dice_skins[skin_id] for skin_id in user_skins 
                      if skin_id in self.dice_skins]
        
        if not owned_skins:
            # New user - recommend popular skins
            return self._get_popular_recommendations(count)
        
        # Analyze user preferences
        user_preferences = self._analyze_user_preferences(owned_skins)
        
        # Find similar skins
        recommendations = []
        
        for skin in self.dice_skins.values():
            if (skin.status == ProductStatus.ACTIVE and 
                skin.id not in user_skins):
                
                score = self._calculate_recommendation_score(skin, user_preferences)
                
                if score > 0:
                    recommendations.append({
                        "skin": skin,
                        "score": score,
                        "reason": self._generate_recommendation_reason(skin, user_preferences)
                    })
        
        # Sort by score and return top recommendations
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations[:count]
    
    def _analyze_user_preferences(self, owned_skins: List[DiceSkin]) -> Dict[str, Any]:
        """Analyze user preferences from owned skins"""
        
        category_counts = {}
        material_counts = {}
        color_counts = {}
        effect_counts = {}
        
        for skin in owned_skins:
            # Categories
            category_counts[skin.category] = category_counts.get(skin.category, 0) + 1
            
            # Materials
            material_counts[skin.base_material] = material_counts.get(skin.base_material, 0) + 1
            
            # Colors
            for color in skin.colors:
                color_counts[color] = color_counts.get(color, 0) + 1
            
            # Effects
            for effect in skin.special_effects:
                effect_counts[effect] = effect_counts.get(effect, 0) + 1
        
        return {
            "favorite_categories": sorted(category_counts.items(), key=lambda x: x[1], reverse=True),
            "favorite_materials": sorted(material_counts.items(), key=lambda x: x[1], reverse=True),
            "favorite_colors": sorted(color_counts.items(), key=lambda x: x[1], reverse=True),
            "favorite_effects": sorted(effect_counts.items(), key=lambda x: x[1], reverse=True),
            "prefers_animated": sum(1 for skin in owned_skins if skin.is_animated) > len(owned_skins) * 0.5,
            "prefers_sound": sum(1 for skin in owned_skins if skin.sound_category != SoundCategory.SILENT.value) > len(owned_skins) * 0.5
        }
    
    def _calculate_recommendation_score(self, skin: DiceSkin, preferences: Dict[str, Any]) -> float:
        """Calculate recommendation score for a skin"""
        
        score = 0.0
        
        # Category preference
        for category, count in preferences["favorite_categories"][:3]:
            if skin.category == category:
                score += count * 2
        
        # Material preference
        for material, count in preferences["favorite_materials"][:3]:
            if skin.base_material == material:
                score += count * 1.5
        
        # Color preference
        for color, count in preferences["favorite_colors"][:5]:
            if color in skin.colors:
                score += count
        
        # Effect preference
        for effect, count in preferences["favorite_effects"][:3]:
            if effect in skin.special_effects:
                score += count * 1.2
        
        # Animation preference
        if preferences["prefers_animated"] and skin.is_animated:
            score += 2
        elif not preferences["prefers_animated"] and not skin.is_animated:
            score += 1
        
        # Sound preference
        if preferences["prefers_sound"] and skin.sound_category != SoundCategory.SILENT.value:
            score += 1.5
        elif not preferences["prefers_sound"] and skin.sound_category == SoundCategory.SILENT.value:
            score += 1
        
        # Quality bonus
        score += float(skin.average_rating)
        
        return score
    
    def _generate_recommendation_reason(self, skin: DiceSkin, preferences: Dict[str, Any]) -> str:
        """Generate reason for recommendation"""
        
        reasons = []
        
        # Check category match
        for category, count in preferences["favorite_categories"][:2]:
            if skin.category == category:
                reasons.append(f"Matches your favorite {category} theme")
                break
        
        # Check material match
        for material, count in preferences["favorite_materials"][:2]:
            if skin.base_material == material:
                reasons.append(f"Features your preferred {material} material")
                break
        
        # Check animation preference
        if preferences["prefers_animated"] and skin.is_animated:
            reasons.append("Includes animations you enjoy")
        
        # Quality mention
        if skin.average_rating >= Decimal("4.5"):
            reasons.append("Highly rated by the community")
        
        return reasons[0] if reasons else "Popular choice among similar users"
    
    def _get_popular_recommendations(self, count: int) -> List[Dict[str, Any]]:
        """Get popular recommendations for new users"""
        
        popular_skins = [
            skin for skin in self.dice_skins.values()
            if skin.status == ProductStatus.ACTIVE
        ]
        
        popular_skins.sort(key=lambda s: (s.average_rating, s.download_count), reverse=True)
        
        return [{
            "skin": skin,
            "score": float(skin.average_rating) + (skin.download_count * 0.001),
            "reason": "Popular community choice"
        } for skin in popular_skins[:count]]
    
    def get_trending_dice_skins(self, days: int = 7) -> List[DiceSkin]:
        """Get trending dice skins"""
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        trending = []
        for skin in self.dice_skins.values():
            if skin.status != ProductStatus.ACTIVE:
                continue
            
            # Calculate trend score
            trend_score = skin.download_count + (float(skin.average_rating) * 10)
            
            trending.append({
                "skin": skin,
                "trend_score": trend_score
            })
        
        trending.sort(key=lambda x: x["trend_score"], reverse=True)
        return [item["skin"] for item in trending[:20]]