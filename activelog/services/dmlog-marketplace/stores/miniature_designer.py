"""
Custom miniature designer and ordering system
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from ..models.base import CustomMiniature, Product, ContentType, ProductStatus, Order

class MiniatureScale(Enum):
    SCALE_28MM = "28mm"
    SCALE_32MM = "32mm"
    SCALE_75MM = "75mm"
    SCALE_54MM = "54mm"

class MiniatureMaterial(Enum):
    PLA_PLASTIC = "pla_plastic"
    RESIN = "resin"
    METAL = "metal"
    CERAMIC = "ceramic"

class MiniatureSize(Enum):
    TINY = "tiny"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    HUGE = "huge"
    GARGANTUAN = "gargantuan"

class PrintQuality(Enum):
    STANDARD = "standard"
    HIGH = "high"
    ULTRA = "ultra"

class MiniatureDesigner:
    """Custom miniature design and ordering system"""
    
    def __init__(self):
        self.miniatures: Dict[str, CustomMiniature] = {}
        self.design_templates: Dict[str, Dict[str, Any]] = {}
        self.print_providers: Dict[str, Dict[str, Any]] = {}
        self.saved_designs: Dict[str, List[str]] = {}  # user_id -> design_ids
        
        # Initialize base components and pricing
        self._initialize_components()
        self._initialize_pricing()
        self._initialize_print_providers()
    
    def _initialize_components(self):
        """Initialize available design components"""
        
        self.design_components = {
            "races": {
                "human": {"name": "Human", "variants": ["male", "female", "child"]},
                "elf": {"name": "Elf", "variants": ["high_elf", "wood_elf", "dark_elf"]},
                "dwarf": {"name": "Dwarf", "variants": ["mountain", "hill", "duergar"]},
                "halfling": {"name": "Halfling", "variants": ["lightfoot", "stout"]},
                "dragonborn": {"name": "Dragonborn", "variants": ["chromatic", "metallic"]},
                "tiefling": {"name": "Tiefling", "variants": ["standard", "variant"]},
                "orc": {"name": "Orc", "variants": ["standard", "half_orc"]},
                "goblin": {"name": "Goblin", "variants": ["standard", "hobgoblin", "bugbear"]},
                "monster": {"name": "Monster", "variants": ["beast", "aberration", "undead", "dragon"]}
            },
            "classes": {
                "fighter": {"name": "Fighter", "armor_types": ["light", "medium", "heavy"]},
                "wizard": {"name": "Wizard", "gear": ["staff", "spellbook", "components"]},
                "rogue": {"name": "Rogue", "gear": ["daggers", "lockpicks", "cloak"]},
                "cleric": {"name": "Cleric", "gear": ["holy_symbol", "mace", "shield"]},
                "ranger": {"name": "Ranger", "gear": ["bow", "arrows", "animal_companion"]},
                "barbarian": {"name": "Barbarian", "gear": ["axe", "tribal_gear", "scars"]},
                "bard": {"name": "Bard", "gear": ["instrument", "hat", "fancy_clothes"]},
                "paladin": {"name": "Paladin", "gear": ["sword", "shield", "plate_armor"]},
                "warlock": {"name": "Warlock", "gear": ["patron_symbol", "dark_robes", "talisman"]},
                "sorcerer": {"name": "Sorcerer", "gear": ["crystal", "robes", "arcane_focus"]},
                "monk": {"name": "Monk", "gear": ["staff", "simple_robes", "meditation_beads"]},
                "druid": {"name": "Druid", "gear": ["nature_staff", "animal_pelts", "herbs"]}
            },
            "poses": {
                "combat": ["attacking", "defending", "casting", "charging", "sneaking"],
                "neutral": ["standing", "sitting", "walking", "kneeling", "pointing"],
                "dramatic": ["heroic", "menacing", "magical", "dying", "victorious"]
            },
            "weapons": {
                "melee": ["sword", "axe", "mace", "dagger", "staff", "club", "spear", "hammer"],
                "ranged": ["bow", "crossbow", "javelin", "sling", "throwing_axe"],
                "magical": ["wand", "orb", "staff", "tome", "crystal", "rune_weapon"]
            },
            "accessories": {
                "clothing": ["robes", "armor", "cloak", "hat", "boots", "gloves"],
                "jewelry": ["necklace", "ring", "bracelet", "crown", "amulet"],
                "gear": ["backpack", "pouch", "rope", "torch", "scroll", "potion"]
            },
            "bases": {
                "standard": ["plain_round", "plain_square", "textured_stone", "grass", "cobblestone"],
                "themed": ["dungeon", "forest", "desert", "snow", "lava", "water", "ruins"]
            }
        }
    
    def _initialize_pricing(self):
        """Initialize pricing structure"""
        
        self.pricing = {
            "base_costs": {
                MiniatureSize.TINY: Decimal("8.00"),
                MiniatureSize.SMALL: Decimal("12.00"),
                MiniatureSize.MEDIUM: Decimal("15.00"),
                MiniatureSize.LARGE: Decimal("25.00"),
                MiniatureSize.HUGE: Decimal("40.00"),
                MiniatureSize.GARGANTUAN: Decimal("65.00")
            },
            "material_multipliers": {
                MiniatureMaterial.PLA_PLASTIC: Decimal("1.0"),
                MiniatureMaterial.RESIN: Decimal("1.3"),
                MiniatureMaterial.METAL: Decimal("2.5"),
                MiniatureMaterial.CERAMIC: Decimal("1.8")
            },
            "quality_multipliers": {
                PrintQuality.STANDARD: Decimal("1.0"),
                PrintQuality.HIGH: Decimal("1.4"),
                PrintQuality.ULTRA: Decimal("2.0")
            },
            "scale_multipliers": {
                MiniatureScale.SCALE_28MM: Decimal("1.0"),
                MiniatureScale.SCALE_32MM: Decimal("1.2"),
                MiniatureScale.SCALE_54MM: Decimal("2.0"),
                MiniatureScale.SCALE_75MM: Decimal("3.0")
            },
            "complexity_multipliers": {
                "simple": Decimal("1.0"),
                "moderate": Decimal("1.3"),
                "complex": Decimal("1.6"),
                "highly_complex": Decimal("2.0")
            },
            "customization_fees": {
                "custom_pose": Decimal("5.00"),
                "custom_weapon": Decimal("3.00"),
                "multiple_accessories": Decimal("2.00"),
                "custom_base": Decimal("4.00"),
                "color_specification": Decimal("2.00"),
                "rush_order": Decimal("10.00")
            }
        }
    
    def _initialize_print_providers(self):
        """Initialize 3D print service providers"""
        
        self.print_providers = {
            "premium_prints": {
                "name": "Premium Miniature Prints",
                "rating": Decimal("4.8"),
                "turnaround_days": 7,
                "materials": [MiniatureMaterial.RESIN, MiniatureMaterial.PLA_PLASTIC],
                "max_quality": PrintQuality.ULTRA,
                "shipping_cost": Decimal("8.99"),
                "bulk_discount": True
            },
            "fast_minis": {
                "name": "Fast Mini Factory",
                "rating": Decimal("4.3"),
                "turnaround_days": 3,
                "materials": [MiniatureMaterial.PLA_PLASTIC, MiniatureMaterial.RESIN],
                "max_quality": PrintQuality.HIGH,
                "shipping_cost": Decimal("12.99"),
                "bulk_discount": False
            },
            "artisan_crafters": {
                "name": "Artisan Miniature Crafters",
                "rating": Decimal("4.9"),
                "turnaround_days": 14,
                "materials": [MiniatureMaterial.METAL, MiniatureMaterial.CERAMIC, MiniatureMaterial.RESIN],
                "max_quality": PrintQuality.ULTRA,
                "shipping_cost": Decimal("15.99"),
                "bulk_discount": True
            }
        }
    
    def start_design(self, user_id: str, name: str) -> str:
        """Start new miniature design"""
        
        miniature = CustomMiniature(
            creator_id=user_id,
            title=name,
            description="Custom miniature design in progress",
            content_type=ContentType.CUSTOM_MINIATURE,
            price=Decimal("0.00"),
            design_data={
                "race": "",
                "class": "",
                "pose": "",
                "weapons": [],
                "accessories": [],
                "base": "plain_round",
                "custom_features": [],
                "color_scheme": {},
                "complexity_level": "simple"
            },
            scale=MiniatureScale.SCALE_32MM.value,
            material=MiniatureMaterial.RESIN.value,
            size=MiniatureSize.MEDIUM.value,
            print_quality=PrintQuality.STANDARD.value
        )
        
        self.miniatures[miniature.id] = miniature
        
        # Add to user's saved designs
        if user_id not in self.saved_designs:
            self.saved_designs[user_id] = []
        self.saved_designs[user_id].append(miniature.id)
        
        return miniature.id
    
    def update_design(
        self,
        miniature_id: str,
        user_id: str,
        design_updates: Dict[str, Any]
    ) -> bool:
        """Update miniature design"""
        
        if miniature_id not in self.miniatures:
            return False
        
        miniature = self.miniatures[miniature_id]
        
        # Verify ownership
        if miniature.creator_id != user_id:
            return False
        
        # Update design data
        for key, value in design_updates.items():
            if key in miniature.design_data:
                miniature.design_data[key] = value
            elif key in ["scale", "material", "size", "print_quality"]:
                setattr(miniature, key, value)
        
        # Recalculate complexity and price
        miniature.design_data["complexity_level"] = self._calculate_complexity(miniature)
        miniature.price = self._calculate_price(miniature)
        miniature.last_updated = datetime.utcnow()
        
        return True
    
    def _calculate_complexity(self, miniature: CustomMiniature) -> str:
        """Calculate design complexity"""
        
        complexity_score = 0
        design_data = miniature.design_data
        
        # Base complexity from race/class
        if design_data.get("race") in ["dragonborn", "tiefling", "monster"]:
            complexity_score += 2
        elif design_data.get("race") in ["elf", "dwarf"]:
            complexity_score += 1
        
        # Weapon complexity
        weapons = design_data.get("weapons", [])
        complexity_score += len(weapons)
        
        if "magical" in [w.split("_")[0] for w in weapons]:
            complexity_score += 2
        
        # Accessory complexity
        accessories = design_data.get("accessories", [])
        complexity_score += len(accessories) // 2
        
        # Custom features
        custom_features = design_data.get("custom_features", [])
        complexity_score += len(custom_features) * 2
        
        # Pose complexity
        pose = design_data.get("pose", "")
        if pose in ["casting", "magical", "dramatic"]:
            complexity_score += 2
        elif pose in ["attacking", "sneaking", "heroic"]:
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 5:
            return "moderate"
        elif complexity_score <= 8:
            return "complex"
        else:
            return "highly_complex"
    
    def _calculate_price(self, miniature: CustomMiniature) -> Decimal:
        """Calculate miniature price"""
        
        # Base cost by size
        base_cost = self.pricing["base_costs"][MiniatureSize(miniature.size)]
        
        # Apply multipliers
        material_mult = self.pricing["material_multipliers"][MiniatureMaterial(miniature.material)]
        quality_mult = self.pricing["quality_multipliers"][PrintQuality(miniature.print_quality)]
        scale_mult = self.pricing["scale_multipliers"][MiniatureScale(miniature.scale)]
        complexity_mult = self.pricing["complexity_multipliers"][miniature.design_data["complexity_level"]]
        
        total_cost = base_cost * material_mult * quality_mult * scale_mult * complexity_mult
        
        # Add customization fees
        customization_cost = Decimal("0.00")
        design_data = miniature.design_data
        
        if design_data.get("pose") not in ["standing", "walking"]:
            customization_cost += self.pricing["customization_fees"]["custom_pose"]
        
        if len(design_data.get("weapons", [])) > 1:
            customization_cost += self.pricing["customization_fees"]["custom_weapon"]
        
        if len(design_data.get("accessories", [])) > 3:
            customization_cost += self.pricing["customization_fees"]["multiple_accessories"]
        
        if design_data.get("base") != "plain_round":
            customization_cost += self.pricing["customization_fees"]["custom_base"]
        
        if design_data.get("color_scheme"):
            customization_cost += self.pricing["customization_fees"]["color_specification"]
        
        total_cost += customization_cost
        return total_cost.quantize(Decimal('0.01'))
    
    def generate_preview(self, miniature_id: str) -> Dict[str, Any]:
        """Generate 3D preview of miniature"""
        
        if miniature_id not in self.miniatures:
            return {}
        
        miniature = self.miniatures[miniature_id]
        
        # Generate preview data (would integrate with 3D rendering service)
        preview = {
            "miniature_id": miniature_id,
            "preview_images": [
                f"https://preview.miniatures.com/{miniature_id}/front.jpg",
                f"https://preview.miniatures.com/{miniature_id}/back.jpg",
                f"https://preview.miniatures.com/{miniature_id}/side.jpg",
                f"https://preview.miniatures.com/{miniature_id}/3d_view.jpg"
            ],
            "interactive_3d_url": f"https://3d.miniatures.com/{miniature_id}",
            "specifications": {
                "height": f"{self._get_miniature_height(miniature)}mm",
                "base_diameter": f"{self._get_base_diameter(miniature)}mm",
                "estimated_weight": f"{self._estimate_weight(miniature)}g",
                "print_time": f"{self._estimate_print_time(miniature)} hours"
            },
            "design_summary": self._generate_design_summary(miniature)
        }
        
        return preview
    
    def _get_miniature_height(self, miniature: CustomMiniature) -> int:
        """Get miniature height in mm"""
        
        scale_heights = {
            MiniatureScale.SCALE_28MM: 28,
            MiniatureScale.SCALE_32MM: 32,
            MiniatureScale.SCALE_54MM: 54,
            MiniatureScale.SCALE_75MM: 75
        }
        
        base_height = scale_heights[MiniatureScale(miniature.scale)]
        
        # Adjust for pose
        pose = miniature.design_data.get("pose", "standing")
        if pose in ["heroic", "dramatic"]:
            return int(base_height * 1.1)
        elif pose in ["kneeling", "sitting"]:
            return int(base_height * 0.8)
        
        return base_height
    
    def _get_base_diameter(self, miniature: CustomMiniature) -> int:
        """Get base diameter in mm"""
        
        size_diameters = {
            MiniatureSize.TINY: 20,
            MiniatureSize.SMALL: 25,
            MiniatureSize.MEDIUM: 32,
            MiniatureSize.LARGE: 50,
            MiniatureSize.HUGE: 75,
            MiniatureSize.GARGANTUAN: 100
        }
        
        return size_diameters[MiniatureSize(miniature.size)]
    
    def _estimate_weight(self, miniature: CustomMiniature) -> float:
        """Estimate miniature weight in grams"""
        
        base_weights = {
            MiniatureSize.TINY: 2.0,
            MiniatureSize.SMALL: 5.0,
            MiniatureSize.MEDIUM: 8.0,
            MiniatureSize.LARGE: 20.0,
            MiniatureSize.HUGE: 50.0,
            MiniatureSize.GARGANTUAN: 120.0
        }
        
        material_density = {
            MiniatureMaterial.PLA_PLASTIC: 1.0,
            MiniatureMaterial.RESIN: 1.2,
            MiniatureMaterial.METAL: 3.5,
            MiniatureMaterial.CERAMIC: 2.2
        }
        
        base_weight = base_weights[MiniatureSize(miniature.size)]
        density = material_density[MiniatureMaterial(miniature.material)]
        complexity_mult = {"simple": 1.0, "moderate": 1.2, "complex": 1.4, "highly_complex": 1.6}
        
        weight = base_weight * density * complexity_mult[miniature.design_data["complexity_level"]]
        return round(weight, 1)
    
    def _estimate_print_time(self, miniature: CustomMiniature) -> float:
        """Estimate print time in hours"""
        
        base_times = {
            MiniatureSize.TINY: 1.5,
            MiniatureSize.SMALL: 2.5,
            MiniatureSize.MEDIUM: 4.0,
            MiniatureSize.LARGE: 8.0,
            MiniatureSize.HUGE: 16.0,
            MiniatureSize.GARGANTUAN: 32.0
        }
        
        quality_mult = {
            PrintQuality.STANDARD: 1.0,
            PrintQuality.HIGH: 1.5,
            PrintQuality.ULTRA: 2.2
        }
        
        complexity_mult = {"simple": 1.0, "moderate": 1.3, "complex": 1.6, "highly_complex": 2.0}
        
        base_time = base_times[MiniatureSize(miniature.size)]
        quality_factor = quality_mult[PrintQuality(miniature.print_quality)]
        complexity_factor = complexity_mult[miniature.design_data["complexity_level"]]
        
        total_time = base_time * quality_factor * complexity_factor
        return round(total_time, 1)
    
    def _generate_design_summary(self, miniature: CustomMiniature) -> str:
        """Generate human-readable design summary"""
        
        design_data = miniature.design_data
        
        parts = []
        
        # Race and class
        if design_data.get("race"):
            race_name = self.design_components["races"][design_data["race"]]["name"]
            parts.append(race_name)
        
        if design_data.get("class"):
            class_name = self.design_components["classes"][design_data["class"]]["name"]
            parts.append(class_name)
        
        # Pose
        if design_data.get("pose"):
            parts.append(f"in {design_data['pose']} pose")
        
        # Primary weapon
        weapons = design_data.get("weapons", [])
        if weapons:
            parts.append(f"wielding {weapons[0]}")
        
        # Material and scale
        parts.append(f"in {miniature.material} at {miniature.scale} scale")
        
        return " ".join(parts).capitalize()
    
    def place_order(
        self,
        miniature_id: str,
        user_id: str,
        quantity: int,
        provider_id: str,
        shipping_address: Dict[str, str],
        rush_order: bool = False
    ) -> Optional[str]:
        """Place order for miniature printing"""
        
        if miniature_id not in self.miniatures:
            return None
        
        if provider_id not in self.print_providers:
            return None
        
        miniature = self.miniatures[miniature_id]
        provider = self.print_providers[provider_id]
        
        # Verify ownership
        if miniature.creator_id != user_id:
            return None
        
        # Calculate order total
        unit_price = miniature.price
        if rush_order:
            unit_price += self.pricing["customization_fees"]["rush_order"]
        
        subtotal = unit_price * quantity
        shipping_cost = provider["shipping_cost"]
        
        # Apply bulk discount if available
        if provider["bulk_discount"] and quantity >= 5:
            subtotal *= Decimal("0.9")  # 10% discount
        
        total_cost = subtotal + shipping_cost
        
        # Create order (simplified - would integrate with order system)
        order_id = f"order_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{user_id[:8]}"
        
        order_data = {
            "id": order_id,
            "user_id": user_id,
            "miniature_id": miniature_id,
            "provider_id": provider_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "subtotal": subtotal,
            "shipping_cost": shipping_cost,
            "total_cost": total_cost,
            "rush_order": rush_order,
            "shipping_address": shipping_address,
            "estimated_delivery": datetime.utcnow() + timedelta(days=provider["turnaround_days"]),
            "status": "pending_payment",
            "created_at": datetime.utcnow()
        }
        
        # Store order (would use proper order management system)
        if not hasattr(self, 'orders'):
            self.orders = {}
        self.orders[order_id] = order_data
        
        return order_id
    
    def get_user_designs(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all designs by user"""
        
        user_design_ids = self.saved_designs.get(user_id, [])
        designs = []
        
        for design_id in user_design_ids:
            if design_id in self.miniatures:
                miniature = self.miniatures[design_id]
                designs.append({
                    "miniature": miniature.dict(),
                    "preview_image": f"https://preview.miniatures.com/{design_id}/thumb.jpg",
                    "last_modified": miniature.last_updated,
                    "is_complete": miniature.design_data["complexity_level"] != "simple" or len(miniature.design_data.get("weapons", [])) > 0
                })
        
        # Sort by last modified
        designs.sort(key=lambda d: d["last_modified"], reverse=True)
        return designs
    
    def duplicate_design(self, miniature_id: str, user_id: str, new_name: str) -> Optional[str]:
        """Create duplicate of existing design"""
        
        if miniature_id not in self.miniatures:
            return None
        
        original = self.miniatures[miniature_id]
        
        # Create duplicate
        duplicate = CustomMiniature(
            creator_id=user_id,
            title=new_name,
            description=f"Copy of {original.title}",
            content_type=ContentType.CUSTOM_MINIATURE,
            price=original.price,
            design_data=original.design_data.copy(),
            scale=original.scale,
            material=original.material,
            size=original.size,
            print_quality=original.print_quality
        )
        
        self.miniatures[duplicate.id] = duplicate
        
        # Add to user's saved designs
        if user_id not in self.saved_designs:
            self.saved_designs[user_id] = []
        self.saved_designs[user_id].append(duplicate.id)
        
        return duplicate.id
    
    def get_popular_designs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular miniature designs"""
        
        # Simulate popularity based on creation date and complexity
        popular = []
        
        for miniature in self.miniatures.values():
            if miniature.design_data["complexity_level"] in ["complex", "highly_complex"]:
                popularity_score = len(miniature.design_data.get("weapons", [])) * 2
                popularity_score += len(miniature.design_data.get("accessories", []))
                popularity_score += {"simple": 1, "moderate": 2, "complex": 4, "highly_complex": 6}[miniature.design_data["complexity_level"]]
                
                popular.append({
                    "miniature": miniature.dict(),
                    "popularity_score": popularity_score,
                    "preview_image": f"https://preview.miniatures.com/{miniature.id}/thumb.jpg",
                    "creator_name": f"Creator_{miniature.creator_id[:8]}"
                })
        
        # Sort by popularity
        popular.sort(key=lambda d: d["popularity_score"], reverse=True)
        return popular[:limit]