"""
Setting adaptation tools for converting campaign settings between game systems
"""

from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from ..models.base import ConversionResult
from ..config.systems import GameSystem


class SettingTheme(Enum):
    FANTASY = "fantasy"
    URBAN_FANTASY = "urban_fantasy"
    SCIENCE_FICTION = "science_fiction"
    HORROR = "horror"
    STEAMPUNK = "steampunk"
    POST_APOCALYPTIC = "post_apocalyptic"
    CYBERPUNK = "cyberpunk"
    HISTORICAL = "historical"
    MYTHOLOGICAL = "mythological"


class TechnologyLevel(Enum):
    STONE_AGE = "stone_age"
    BRONZE_AGE = "bronze_age"
    IRON_AGE = "iron_age"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    FUTURISTIC = "futuristic"


class MagicLevel(Enum):
    NO_MAGIC = "no_magic"
    RARE_MAGIC = "rare_magic"
    LOW_MAGIC = "low_magic"
    STANDARD_MAGIC = "standard_magic"
    HIGH_MAGIC = "high_magic"
    UBIQUITOUS_MAGIC = "ubiquitous_magic"


class SettingAdapter:
    """Adapts campaign settings between different game systems"""
    
    def __init__(self):
        self.system_themes = {
            GameSystem.D_AND_D_5E: [
                SettingTheme.FANTASY, SettingTheme.URBAN_FANTASY, 
                SettingTheme.HORROR, SettingTheme.STEAMPUNK
            ],
            GameSystem.PATHFINDER_2E: [
                SettingTheme.FANTASY, SettingTheme.STEAMPUNK,
                SettingTheme.HORROR, SettingTheme.MYTHOLOGICAL
            ],
            GameSystem.CALL_OF_CTHULHU_7E: [
                SettingTheme.HORROR, SettingTheme.HISTORICAL,
                SettingTheme.MODERN
            ],
            GameSystem.CYBERPUNK_RED: [
                SettingTheme.CYBERPUNK, SettingTheme.SCIENCE_FICTION
            ]
        }
        
        self.system_tech_levels = {
            GameSystem.D_AND_D_5E: [
                TechnologyLevel.MEDIEVAL, TechnologyLevel.RENAISSANCE
            ],
            GameSystem.PATHFINDER_2E: [
                TechnologyLevel.MEDIEVAL, TechnologyLevel.RENAISSANCE,
                TechnologyLevel.INDUSTRIAL
            ],
            GameSystem.CALL_OF_CTHULHU_7E: [
                TechnologyLevel.INDUSTRIAL, TechnologyLevel.MODERN
            ],
            GameSystem.CYBERPUNK_RED: [
                TechnologyLevel.FUTURISTIC
            ]
        }
        
        self.system_magic_levels = {
            GameSystem.D_AND_D_5E: [
                MagicLevel.STANDARD_MAGIC, MagicLevel.HIGH_MAGIC
            ],
            GameSystem.PATHFINDER_2E: [
                MagicLevel.STANDARD_MAGIC, MagicLevel.HIGH_MAGIC,
                MagicLevel.UBIQUITOUS_MAGIC
            ],
            GameSystem.CALL_OF_CTHULHU_7E: [
                MagicLevel.NO_MAGIC, MagicLevel.RARE_MAGIC
            ],
            GameSystem.CYBERPUNK_RED: [
                MagicLevel.NO_MAGIC
            ]
        }
    
    def adapt_setting(
        self, 
        setting_data: Dict[str, Any],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> ConversionResult:
        """Adapt a campaign setting to target system"""
        
        result = ConversionResult(
            success=True,
            source_system=source_system,
            target_system=target_system
        )
        
        try:
            if source_system == target_system:
                result.converted_data = setting_data.copy()
                result.conversion_notes = ["No conversion needed - same system"]
                return result
            
            adapted_setting = setting_data.copy()
            
            # Extract setting characteristics
            theme = self._identify_setting_theme(setting_data)
            tech_level = self._identify_tech_level(setting_data)
            magic_level = self._identify_magic_level(setting_data)
            
            # Check compatibility with target system
            compatibility = self._check_system_compatibility(
                theme, tech_level, magic_level, target_system
            )
            
            if not compatibility["compatible"]:
                result.warnings.extend(compatibility["warnings"])
                result.manual_review_required = True
            
            # Adapt core setting elements
            adapted_setting["locations"] = self._adapt_locations(
                setting_data.get("locations", []), source_system, target_system
            )
            
            adapted_setting["organizations"] = self._adapt_organizations(
                setting_data.get("organizations", []), source_system, target_system
            )
            
            adapted_setting["cultures"] = self._adapt_cultures(
                setting_data.get("cultures", []), source_system, target_system
            )
            
            adapted_setting["religions"] = self._adapt_religions(
                setting_data.get("religions", []), source_system, target_system
            )
            
            adapted_setting["conflicts"] = self._adapt_conflicts(
                setting_data.get("conflicts", []), source_system, target_system
            )
            
            adapted_setting["economy"] = self._adapt_economy(
                setting_data.get("economy", {}), source_system, target_system
            )
            
            adapted_setting["magic_system"] = self._adapt_magic_system(
                setting_data.get("magic_system", {}), source_system, target_system
            )
            
            adapted_setting["technology"] = self._adapt_technology(
                setting_data.get("technology", {}), source_system, target_system
            )
            
            # Add system-specific elements
            adapted_setting["system_integration"] = self._add_system_integration(
                adapted_setting, target_system
            )
            
            result.converted_data = adapted_setting
            result.conversion_confidence = self._calculate_setting_confidence(
                setting_data, adapted_setting, compatibility
            )
            
            result.conversion_notes.extend(compatibility.get("adaptation_notes", []))
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Setting adaptation failed: {str(e)}")
            result.conversion_confidence = 0.0
        
        return result
    
    def _identify_setting_theme(self, setting_data: Dict[str, Any]) -> SettingTheme:
        """Identify the primary theme of a setting"""
        
        # Look for theme indicators in setting data
        description = setting_data.get("description", "").lower()
        tags = [tag.lower() for tag in setting_data.get("tags", [])]
        
        theme_keywords = {
            SettingTheme.FANTASY: ["magic", "dragons", "elves", "dwarves", "fantasy"],
            SettingTheme.URBAN_FANTASY: ["modern", "city", "urban", "contemporary"],
            SettingTheme.HORROR: ["horror", "undead", "gothic", "dark", "supernatural"],
            SettingTheme.SCIENCE_FICTION: ["space", "aliens", "technology", "future", "sci-fi"],
            SettingTheme.STEAMPUNK: ["steam", "clockwork", "victorian", "mechanical"],
            SettingTheme.CYBERPUNK: ["cyber", "hacker", "corporate", "dystopian"],
            SettingTheme.HISTORICAL: ["historical", "period", "ancient", "medieval"],
            SettingTheme.MYTHOLOGICAL: ["myth", "gods", "legend", "divine"]
        }
        
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in description:
                    score += 2
                if keyword in tags:
                    score += 3
            theme_scores[theme] = score
        
        # Return theme with highest score, default to fantasy
        if theme_scores:
            return max(theme_scores, key=theme_scores.get)
        return SettingTheme.FANTASY
    
    def _identify_tech_level(self, setting_data: Dict[str, Any]) -> TechnologyLevel:
        """Identify the technology level of a setting"""
        
        tech_indicators = setting_data.get("technology", {})
        description = setting_data.get("description", "").lower()
        
        tech_keywords = {
            TechnologyLevel.MEDIEVAL: ["sword", "horse", "castle", "medieval"],
            TechnologyLevel.RENAISSANCE: ["gunpowder", "printing", "exploration"],
            TechnologyLevel.INDUSTRIAL: ["steam", "factory", "railroad", "industrial"],
            TechnologyLevel.MODERN: ["car", "phone", "electricity", "modern"],
            TechnologyLevel.FUTURISTIC: ["laser", "robot", "space", "cyber", "future"]
        }
        
        tech_scores = {}
        for level, keywords in tech_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in description:
                    score += 1
            tech_scores[level] = score
        
        if tech_scores:
            return max(tech_scores, key=tech_scores.get)
        return TechnologyLevel.MEDIEVAL
    
    def _identify_magic_level(self, setting_data: Dict[str, Any]) -> MagicLevel:
        """Identify the magic level of a setting"""
        
        magic_data = setting_data.get("magic_system", {})
        description = setting_data.get("description", "").lower()
        
        # Check explicit magic level
        if "level" in magic_data:
            level_str = magic_data["level"].lower()
            for magic_level in MagicLevel:
                if level_str == magic_level.value:
                    return magic_level
        
        # Infer from description
        magic_keywords = {
            MagicLevel.NO_MAGIC: ["no magic", "realistic", "historical"],
            MagicLevel.RARE_MAGIC: ["rare magic", "hidden", "secret"],
            MagicLevel.LOW_MAGIC: ["low magic", "limited", "subtle"],
            MagicLevel.STANDARD_MAGIC: ["magic", "spells", "wizards"],
            MagicLevel.HIGH_MAGIC: ["high magic", "powerful", "common magic"],
            MagicLevel.UBIQUITOUS_MAGIC: ["magic everywhere", "magical", "arcane"]
        }
        
        magic_scores = {}
        for level, keywords in magic_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in description:
                    score += 1
            magic_scores[level] = score
        
        if magic_scores:
            return max(magic_scores, key=magic_scores.get)
        return MagicLevel.STANDARD_MAGIC
    
    def _check_system_compatibility(
        self, 
        theme: SettingTheme,
        tech_level: TechnologyLevel,
        magic_level: MagicLevel,
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Check compatibility between setting and target system"""
        
        compatibility = {
            "compatible": True,
            "warnings": [],
            "adaptation_notes": []
        }
        
        # Check theme compatibility
        if theme not in self.system_themes.get(target_system, []):
            compatibility["compatible"] = False
            compatibility["warnings"].append(
                f"Theme {theme.value} may not be well-supported by {target_system.value}"
            )
            compatibility["adaptation_notes"].append(
                f"Consider adapting {theme.value} elements to fit {target_system.value} conventions"
            )
        
        # Check technology level compatibility
        if tech_level not in self.system_tech_levels.get(target_system, []):
            compatibility["warnings"].append(
                f"Technology level {tech_level.value} may need adaptation for {target_system.value}"
            )
            compatibility["adaptation_notes"].append(
                f"Adjust technology descriptions and mechanics for {target_system.value}"
            )
        
        # Check magic level compatibility
        if magic_level not in self.system_magic_levels.get(target_system, []):
            compatibility["warnings"].append(
                f"Magic level {magic_level.value} may not match {target_system.value} expectations"
            )
            compatibility["adaptation_notes"].append(
                f"Modify magic system to align with {target_system.value} mechanics"
            )
        
        return compatibility
    
    def _adapt_locations(
        self, 
        locations: List[Dict[str, Any]],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Adapt location descriptions for target system"""
        
        adapted_locations = []
        
        for location in locations:
            adapted_location = location.copy()
            
            # Adapt mechanical elements
            if "encounters" in location:
                adapted_location["encounters"] = self._adapt_location_encounters(
                    location["encounters"], source_system, target_system
                )
            
            if "shops" in location:
                adapted_location["shops"] = self._adapt_shops(
                    location["shops"], source_system, target_system
                )
            
            if "services" in location:
                adapted_location["services"] = self._adapt_services(
                    location["services"], source_system, target_system
                )
            
            # Adapt governance and law
            if "governance" in location:
                adapted_location["governance"] = self._adapt_governance(
                    location["governance"], source_system, target_system
                )
            
            adapted_locations.append(adapted_location)
        
        return adapted_locations
    
    def _adapt_organizations(
        self, 
        organizations: List[Dict[str, Any]],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Adapt organizations for target system"""
        
        adapted_orgs = []
        
        for org in organizations:
            adapted_org = org.copy()
            
            # Adapt organization structure to system conventions
            if "hierarchy" in org:
                adapted_org["hierarchy"] = self._adapt_hierarchy(
                    org["hierarchy"], source_system, target_system
                )
            
            # Adapt resources and capabilities
            if "resources" in org:
                adapted_org["resources"] = self._adapt_org_resources(
                    org["resources"], source_system, target_system
                )
            
            # Adapt goals and methods to system themes
            if "goals" in org and "methods" in org:
                adapted_goals, adapted_methods = self._adapt_org_goals_methods(
                    org["goals"], org["methods"], source_system, target_system
                )
                adapted_org["goals"] = adapted_goals
                adapted_org["methods"] = adapted_methods
            
            adapted_orgs.append(adapted_org)
        
        return adapted_orgs
    
    def _adapt_cultures(
        self, 
        cultures: List[Dict[str, Any]],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Adapt cultural descriptions for target system"""
        
        adapted_cultures = []
        
        for culture in cultures:
            adapted_culture = culture.copy()
            
            # Adapt cultural values to system themes
            if "values" in culture:
                adapted_culture["values"] = self._adapt_cultural_values(
                    culture["values"], source_system, target_system
                )
            
            # Adapt traditions and practices
            if "traditions" in culture:
                adapted_culture["traditions"] = self._adapt_traditions(
                    culture["traditions"], source_system, target_system
                )
            
            # Adapt social structure
            if "social_structure" in culture:
                adapted_culture["social_structure"] = self._adapt_social_structure(
                    culture["social_structure"], source_system, target_system
                )
            
            adapted_cultures.append(adapted_culture)
        
        return adapted_cultures
    
    def _adapt_religions(
        self, 
        religions: List[Dict[str, Any]],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Adapt religious systems for target system"""
        
        adapted_religions = []
        
        for religion in religions:
            adapted_religion = religion.copy()
            
            # Adapt divine mechanics
            if "divine_intervention" in religion:
                adapted_religion["divine_intervention"] = self._adapt_divine_mechanics(
                    religion["divine_intervention"], source_system, target_system
                )
            
            # Adapt clergy structure
            if "clergy" in religion:
                adapted_religion["clergy"] = self._adapt_clergy_structure(
                    religion["clergy"], source_system, target_system
                )
            
            # Adapt religious practices
            if "practices" in religion:
                adapted_religion["practices"] = self._adapt_religious_practices(
                    religion["practices"], source_system, target_system
                )
            
            adapted_religions.append(adapted_religion)
        
        return adapted_religions
    
    def _adapt_conflicts(
        self, 
        conflicts: List[Dict[str, Any]],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> List[Dict[str, Any]]:
        """Adapt conflicts and tensions for target system"""
        
        adapted_conflicts = []
        
        for conflict in conflicts:
            adapted_conflict = conflict.copy()
            
            # Adapt conflict resolution mechanics
            if "resolution_mechanics" in conflict:
                adapted_conflict["resolution_mechanics"] = self._adapt_resolution_mechanics(
                    conflict["resolution_mechanics"], source_system, target_system
                )
            
            # Adapt scale and scope to system conventions
            if "scale" in conflict:
                adapted_conflict["scale"] = self._adapt_conflict_scale(
                    conflict["scale"], source_system, target_system
                )
            
            adapted_conflicts.append(adapted_conflict)
        
        return adapted_conflicts
    
    def _adapt_economy(
        self, 
        economy: Dict[str, Any],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Adapt economic systems for target system"""
        
        adapted_economy = economy.copy()
        
        # Adapt currency systems
        if "currency" in economy:
            adapted_economy["currency"] = self._adapt_currency(
                economy["currency"], source_system, target_system
            )
        
        # Adapt trade and commerce
        if "trade" in economy:
            adapted_economy["trade"] = self._adapt_trade_systems(
                economy["trade"], source_system, target_system
            )
        
        # Adapt price levels
        if "price_levels" in economy:
            adapted_economy["price_levels"] = self._adapt_price_levels(
                economy["price_levels"], source_system, target_system
            )
        
        return adapted_economy
    
    def _adapt_magic_system(
        self, 
        magic_system: Dict[str, Any],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Adapt magic system for target system"""
        
        adapted_magic = magic_system.copy()
        
        # Adapt magic availability and restrictions
        if "availability" in magic_system:
            adapted_magic["availability"] = self._adapt_magic_availability(
                magic_system["availability"], source_system, target_system
            )
        
        # Adapt spell schools and types
        if "schools" in magic_system:
            adapted_magic["schools"] = self._adapt_magic_schools(
                magic_system["schools"], source_system, target_system
            )
        
        # Adapt magical organizations
        if "organizations" in magic_system:
            adapted_magic["organizations"] = self._adapt_magic_organizations(
                magic_system["organizations"], source_system, target_system
            )
        
        return adapted_magic
    
    def _adapt_technology(
        self, 
        technology: Dict[str, Any],
        source_system: GameSystem,
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Adapt technology systems for target system"""
        
        adapted_tech = technology.copy()
        
        # Adapt technological level descriptions
        if "level" in technology:
            adapted_tech["level"] = self._adapt_tech_level_description(
                technology["level"], source_system, target_system
            )
        
        # Adapt specific technologies
        if "innovations" in technology:
            adapted_tech["innovations"] = self._adapt_tech_innovations(
                technology["innovations"], source_system, target_system
            )
        
        return adapted_tech
    
    def _add_system_integration(
        self, 
        setting: Dict[str, Any], 
        target_system: GameSystem
    ) -> Dict[str, Any]:
        """Add system-specific integration elements"""
        
        integration = {
            "system": target_system.value,
            "mechanical_elements": [],
            "house_rules": [],
            "adaptation_notes": []
        }
        
        # Add system-specific mechanical elements
        if target_system == GameSystem.D_AND_D_5E:
            integration["mechanical_elements"].extend([
                "Background integration with setting cultures",
                "Faction renown and reputation systems",
                "Environmental hazards using existing mechanics"
            ])
        elif target_system == GameSystem.PATHFINDER_2E:
            integration["mechanical_elements"].extend([
                "Ancestry and heritage options from setting cultures",
                "Organization archetypes and dedications",
                "Environmental rules and subsystems"
            ])
        
        # Add recommended house rules
        integration["house_rules"] = self._generate_house_rules(setting, target_system)
        
        # Add adaptation notes
        integration["adaptation_notes"] = self._generate_adaptation_notes(setting, target_system)
        
        return integration
    
    def _generate_house_rules(
        self, 
        setting: Dict[str, Any], 
        target_system: GameSystem
    ) -> List[Dict[str, str]]:
        """Generate recommended house rules for setting integration"""
        
        house_rules = []
        
        # Technology-based house rules
        tech_level = self._identify_tech_level(setting)
        if tech_level == TechnologyLevel.MODERN and target_system in [GameSystem.D_AND_D_5E, GameSystem.PATHFINDER_2E]:
            house_rules.append({
                "name": "Modern Equipment",
                "description": "Rules for incorporating modern weapons and technology",
                "category": "technology"
            })
        
        # Magic-based house rules
        magic_level = self._identify_magic_level(setting)
        if magic_level == MagicLevel.LOW_MAGIC:
            house_rules.append({
                "name": "Limited Magic",
                "description": "Restrictions on spell availability and magical items",
                "category": "magic"
            })
        
        return house_rules
    
    def _generate_adaptation_notes(
        self, 
        setting: Dict[str, Any], 
        target_system: GameSystem
    ) -> List[str]:
        """Generate adaptation notes for DMs"""
        
        notes = []
        
        # System-specific notes
        if target_system == GameSystem.D_AND_D_5E:
            notes.append("Consider using variant rules from the DMG for environmental effects")
            notes.append("Adapt organization goals to faction mechanics")
        elif target_system == GameSystem.PATHFINDER_2E:
            notes.append("Use subsystem rules for complex setting elements")
            notes.append("Consider ancestry variants for unique setting cultures")
        
        return notes
    
    def _calculate_setting_confidence(
        self, 
        original: Dict[str, Any],
        adapted: Dict[str, Any],
        compatibility: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for setting adaptation"""
        
        confidence_factors = []
        
        # Base compatibility score
        if compatibility["compatible"]:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.5)
        
        # Content preservation
        original_sections = len([k for k in original.keys() if isinstance(original[k], (list, dict))])
        adapted_sections = len([k for k in adapted.keys() if isinstance(adapted[k], (list, dict))])
        
        if adapted_sections >= original_sections * 0.9:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.7)
        
        # Complexity assessment
        total_elements = (
            len(original.get("locations", [])) + len(original.get("organizations", [])) +
            len(original.get("cultures", [])) + len(original.get("religions", []))
        )
        
        if total_elements <= 10:
            confidence_factors.append(0.9)
        elif total_elements <= 25:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.7)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    # Placeholder methods for specific adaptation tasks
    def _adapt_location_encounters(self, encounters, source_system, target_system):
        return encounters
    
    def _adapt_shops(self, shops, source_system, target_system):
        return shops
    
    def _adapt_services(self, services, source_system, target_system):
        return services
    
    def _adapt_governance(self, governance, source_system, target_system):
        return governance
    
    def _adapt_hierarchy(self, hierarchy, source_system, target_system):
        return hierarchy
    
    def _adapt_org_resources(self, resources, source_system, target_system):
        return resources
    
    def _adapt_org_goals_methods(self, goals, methods, source_system, target_system):
        return goals, methods
    
    def _adapt_cultural_values(self, values, source_system, target_system):
        return values
    
    def _adapt_traditions(self, traditions, source_system, target_system):
        return traditions
    
    def _adapt_social_structure(self, structure, source_system, target_system):
        return structure
    
    def _adapt_divine_mechanics(self, mechanics, source_system, target_system):
        return mechanics
    
    def _adapt_clergy_structure(self, clergy, source_system, target_system):
        return clergy
    
    def _adapt_religious_practices(self, practices, source_system, target_system):
        return practices
    
    def _adapt_resolution_mechanics(self, mechanics, source_system, target_system):
        return mechanics
    
    def _adapt_conflict_scale(self, scale, source_system, target_system):
        return scale
    
    def _adapt_currency(self, currency, source_system, target_system):
        return currency
    
    def _adapt_trade_systems(self, trade, source_system, target_system):
        return trade
    
    def _adapt_price_levels(self, prices, source_system, target_system):
        return prices
    
    def _adapt_magic_availability(self, availability, source_system, target_system):
        return availability
    
    def _adapt_magic_schools(self, schools, source_system, target_system):
        return schools
    
    def _adapt_magic_organizations(self, orgs, source_system, target_system):
        return orgs
    
    def _adapt_tech_level_description(self, level, source_system, target_system):
        return level
    
    def _adapt_tech_innovations(self, innovations, source_system, target_system):
        return innovations