"""
Recipe Evolution Tracking System

This module provides comprehensive recipe evolution and culinary heritage tracking
including ingredient adaptation, cooking technique evolution, cultural fusion analysis,
and multi-generational recipe preservation.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
from datetime import datetime, date
import uuid
import numpy as np
from collections import defaultdict

class RecipeCategory(Enum):
    """Categories of recipes"""
    APPETIZER = "appetizer"
    SOUP = "soup"
    SALAD = "salad"
    MAIN_COURSE = "main_course"
    SIDE_DISH = "side_dish"
    DESSERT = "dessert"
    BEVERAGE = "beverage"
    BREAD = "bread"
    SAUCE = "sauce"
    CONDIMENT = "condiment"
    SNACK = "snack"
    BREAKFAST = "breakfast"
    FESTIVAL_FOOD = "festival_food"
    CEREMONIAL = "ceremonial"
    MEDICINAL = "medicinal"

class CookingMethod(Enum):
    """Cooking methods and techniques"""
    BAKING = "baking"
    BOILING = "boiling"
    FRYING = "frying"
    GRILLING = "grilling"
    ROASTING = "roasting"
    STEAMING = "steaming"
    BRAISING = "braising"
    STEWING = "stewing"
    SMOKING = "smoking"
    FERMENTING = "fermenting"
    PICKLING = "pickling"
    DRYING = "drying"
    MARINATING = "marinating"
    RAW = "raw"
    PRESSURE_COOKING = "pressure_cooking"

class EvolutionType(Enum):
    """Types of recipe evolution"""
    INGREDIENT_SUBSTITUTION = "ingredient_substitution"
    METHOD_ADAPTATION = "method_adaptation"
    PORTION_ADJUSTMENT = "portion_adjustment"
    CULTURAL_FUSION = "cultural_fusion"
    MODERNIZATION = "modernization"
    SIMPLIFICATION = "simplification"
    ELABORATION = "elaboration"
    HEALTH_ADAPTATION = "health_adaptation"
    SEASONAL_VARIATION = "seasonal_variation"
    REGIONAL_ADAPTATION = "regional_adaptation"

class DietaryRestriction(Enum):
    """Dietary restrictions and preferences"""
    NONE = "none"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    GLUTEN_FREE = "gluten_free"
    DAIRY_FREE = "dairy_free"
    LOW_SODIUM = "low_sodium"
    LOW_SUGAR = "low_sugar"
    KETO = "keto"
    PALEO = "paleo"
    KOSHER = "kosher"
    HALAL = "halal"
    RAW = "raw"

@dataclass
class Ingredient:
    """Individual ingredient with properties"""
    ingredient_id: str
    name: str
    quantity: str
    unit: str
    preparation: Optional[str] = None
    substitutions: List[str] = field(default_factory=list)
    cultural_significance: Optional[str] = None
    seasonality: List[str] = field(default_factory=list)  # months available
    cost_level: Optional[str] = None  # cheap, moderate, expensive
    nutritional_properties: Dict[str, Any] = field(default_factory=dict)
    source_region: Optional[str] = None

@dataclass
class CookingStep:
    """Individual cooking step with details"""
    step_id: str
    step_number: int
    description: str
    method: CookingMethod
    duration: Optional[str] = None
    temperature: Optional[str] = None
    equipment: List[str] = field(default_factory=list)
    techniques: List[str] = field(default_factory=list)
    critical_points: List[str] = field(default_factory=list)
    variations: List[str] = field(default_factory=list)

@dataclass
class RecipeVersion:
    """A specific version of a recipe"""
    version_id: str
    recipe_name: str
    version_name: str
    category: RecipeCategory
    cultural_origin: str
    creator_name: str
    creation_date: date
    ingredients: List[Ingredient]
    cooking_steps: List[CookingStep]
    cooking_methods: List[CookingMethod]
    difficulty_level: str  # easy, medium, hard, expert
    cooking_time: str
    serving_size: str
    dietary_restrictions: List[DietaryRestriction]
    flavor_profile: List[str]  # sweet, salty, spicy, umami, etc.
    occasion_context: List[str]  # daily, special, ceremonial
    seasonal_context: List[str]  # spring, summer, fall, winter
    nutritional_info: Dict[str, Any] = field(default_factory=dict)
    cultural_notes: str = ""
    family_stories: List[str] = field(default_factory=list)
    success_tips: List[str] = field(default_factory=list)
    common_mistakes: List[str] = field(default_factory=list)
    variations: List[str] = field(default_factory=list)
    equipment_needed: List[str] = field(default_factory=list)
    source_person: Optional[str] = None
    source_generation: Optional[int] = None
    multimedia_links: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class RecipeEvolution:
    """Tracks evolution between recipe versions"""
    evolution_id: str
    original_version_id: str
    evolved_version_id: str
    evolution_type: EvolutionType
    evolution_date: date
    evolution_reason: str
    change_description: str
    ingredient_changes: List[Dict[str, Any]] = field(default_factory=list)
    method_changes: List[Dict[str, Any]] = field(default_factory=list)
    cultural_influences: List[str] = field(default_factory=list)
    environmental_factors: List[str] = field(default_factory=list)
    person_responsible: Optional[str] = None
    success_rating: float = 0.0  # 0-1 scale
    preservation_notes: str = ""

@dataclass
class RecipeLineage:
    """Tracks recipe lineage across generations"""
    lineage_id: str
    recipe_family_name: str
    origin_version_id: str
    current_generation: int
    version_timeline: List[str]  # version IDs in chronological order
    evolution_chain: List[str]   # evolution IDs connecting versions
    family_branches: Dict[str, List[str]]  # family_branch -> version_ids
    cultural_adaptations: List[Dict[str, Any]]
    geographic_spread: List[str]
    time_span: Tuple[date, date]
    preservation_status: str  # thriving, stable, at_risk, lost
    key_innovations: List[str]
    traditional_elements: List[str]
    modernization_level: float  # 0 (traditional) to 1 (completely modern)

@dataclass
class CulinaryTradition:
    """Represents broader culinary traditions"""
    tradition_id: str
    tradition_name: str
    cultural_group: str
    core_recipes: List[str]  # recipe lineage IDs
    key_ingredients: List[str]
    signature_techniques: List[CookingMethod]
    cultural_significance: str
    historical_context: str
    seasonal_calendar: Dict[str, List[str]]  # season -> traditional recipes
    ceremonial_foods: Dict[str, List[str]]  # occasion -> recipes
    preservation_efforts: List[str]
    modern_adaptations: List[str]
    transmission_methods: List[str]  # how tradition is passed down

class RecipeEvolutionTracker:
    """Main system for tracking recipe evolution and culinary heritage"""
    
    def __init__(self):
        self.recipe_versions: Dict[str, RecipeVersion] = {}
        self.recipe_evolutions: Dict[str, RecipeEvolution] = {}
        self.recipe_lineages: Dict[str, RecipeLineage] = {}
        self.culinary_traditions: Dict[str, CulinaryTradition] = {}
        self.ingredient_database: Dict[str, Dict[str, Any]] = {}
        self.cultural_networks: Dict[str, Set[str]] = defaultdict(set)
        self.seasonal_patterns: Dict[str, List[str]] = defaultdict(list)
    
    async def add_recipe_version(self, recipe: RecipeVersion) -> Dict[str, Any]:
        """Add new recipe version and analyze relationships"""
        self.recipe_versions[recipe.version_id] = recipe
        
        # Update ingredient database
        for ingredient in recipe.ingredients:
            if ingredient.name not in self.ingredient_database:
                self.ingredient_database[ingredient.name] = {
                    'cultures': set(),
                    'seasonality': set(),
                    'substitutions': set(),
                    'uses': []
                }
            
            self.ingredient_database[ingredient.name]['cultures'].add(recipe.cultural_origin)
            if ingredient.seasonality:
                self.ingredient_database[ingredient.name]['seasonality'].update(ingredient.seasonality)
            if ingredient.substitutions:
                self.ingredient_database[ingredient.name]['substitutions'].update(ingredient.substitutions)
            
            self.ingredient_database[ingredient.name]['uses'].append(recipe.recipe_name)
        
        # Update cultural networks
        for ingredient in recipe.ingredients:
            if ingredient.source_region:
                self.cultural_networks[recipe.cultural_origin].add(ingredient.source_region)
        
        # Update seasonal patterns
        if recipe.seasonal_context:
            for season in recipe.seasonal_context:
                self.seasonal_patterns[season].append(recipe.version_id)
        
        # Check for potential lineage connections
        lineage_updates = await self._analyze_lineage_connections(recipe)
        
        return {
            'success': True,
            'version_id': recipe.version_id,
            'lineage_updates': lineage_updates,
            'ingredient_database_entries': len(self.ingredient_database),
            'cultural_connections': len(self.cultural_networks[recipe.cultural_origin])
        }
    
    async def document_recipe_evolution(self, evolution: RecipeEvolution) -> Dict[str, Any]:
        """Document evolution between two recipe versions"""
        self.recipe_evolutions[evolution.evolution_id] = evolution
        
        # Update lineage information
        original_recipe = self.recipe_versions.get(evolution.original_version_id)
        evolved_recipe = self.recipe_versions.get(evolution.evolved_version_id)
        
        if original_recipe and evolved_recipe:
            # Find or create lineage
            lineage = await self._find_or_create_lineage(original_recipe, evolved_recipe, evolution)
            
            # Analyze evolution patterns
            evolution_patterns = await self._analyze_evolution_patterns(evolution)
            
            return {
                'success': True,
                'evolution_id': evolution.evolution_id,
                'lineage_id': lineage.lineage_id if lineage else None,
                'evolution_patterns': evolution_patterns
            }
        
        return {'success': False, 'error': 'Recipe versions not found'}
    
    async def trace_recipe_lineage(self, recipe_name: str) -> List[RecipeLineage]:
        """Trace the complete lineage of a recipe family"""
        matching_lineages = []
        
        for lineage in self.recipe_lineages.values():
            if lineage.recipe_family_name.lower() == recipe_name.lower():
                matching_lineages.append(lineage)
        
        # Sort by time span and cultural diversity
        matching_lineages.sort(
            key=lambda x: (x.time_span[1] - x.time_span[0], len(x.cultural_adaptations)), 
            reverse=True
        )
        
        return matching_lineages
    
    async def analyze_ingredient_evolution(self, ingredient_name: str) -> Dict[str, Any]:
        """Analyze how an ingredient has evolved across recipes"""
        if ingredient_name not in self.ingredient_database:
            return {'error': f'Ingredient {ingredient_name} not found in database'}
        
        ingredient_data = self.ingredient_database[ingredient_name]
        
        # Find all recipes using this ingredient
        recipes_with_ingredient = []
        for recipe in self.recipe_versions.values():
            for recipe_ingredient in recipe.ingredients:
                if recipe_ingredient.name.lower() == ingredient_name.lower():
                    recipes_with_ingredient.append({
                        'recipe': recipe,
                        'ingredient_details': recipe_ingredient,
                        'date': recipe.creation_date
                    })
        
        # Sort by date
        recipes_with_ingredient.sort(key=lambda x: x['date'])
        
        # Analyze patterns
        usage_evolution = []
        preparation_evolution = []
        quantity_trends = []
        substitution_patterns = []
        
        for recipe_data in recipes_with_ingredient:
            recipe = recipe_data['recipe']
            ingredient_details = recipe_data['ingredient_details']
            
            usage_evolution.append({
                'recipe_name': recipe.recipe_name,
                'culture': recipe.cultural_origin,
                'date': recipe.creation_date.isoformat(),
                'usage_context': recipe.category.value,
                'quantity': ingredient_details.quantity,
                'preparation': ingredient_details.preparation
            })
            
            if ingredient_details.preparation:
                preparation_evolution.append({
                    'date': recipe.creation_date.isoformat(),
                    'preparation': ingredient_details.preparation,
                    'culture': recipe.cultural_origin
                })
            
            # Track quantity trends (simplified)
            try:
                quantity_num = float(re.findall(r'\d+\.?\d*', ingredient_details.quantity)[0])
                quantity_trends.append({
                    'date': recipe.creation_date.isoformat(),
                    'quantity': quantity_num,
                    'unit': ingredient_details.unit
                })
            except (IndexError, ValueError):
                pass
            
            if ingredient_details.substitutions:
                substitution_patterns.extend([{
                    'original': ingredient_name,
                    'substitute': sub,
                    'date': recipe.creation_date.isoformat(),
                    'culture': recipe.cultural_origin
                } for sub in ingredient_details.substitutions])
        
        return {
            'ingredient_name': ingredient_name,
            'total_recipes': len(recipes_with_ingredient),
            'cultures_used': list(ingredient_data['cultures']),
            'seasonality': list(ingredient_data['seasonality']),
            'common_substitutions': list(ingredient_data['substitutions']),
            'usage_evolution': usage_evolution,
            'preparation_evolution': preparation_evolution,
            'quantity_trends': quantity_trends,
            'substitution_patterns': substitution_patterns,
            'cultural_significance': await self._analyze_ingredient_cultural_significance(ingredient_name, recipes_with_ingredient)
        }
    
    async def generate_cultural_fusion_report(self) -> Dict[str, Any]:
        """Generate report on cultural fusion in recipes"""
        fusion_patterns = []
        cultural_influence_network = defaultdict(lambda: defaultdict(int))
        
        # Analyze each recipe for fusion elements
        for recipe in self.recipe_versions.values():
            recipe_cultures = {recipe.cultural_origin}
            
            # Add cultures from ingredients
            for ingredient in recipe.ingredients:
                if ingredient.source_region and ingredient.source_region != recipe.cultural_origin:
                    recipe_cultures.add(ingredient.source_region)
            
            # Add cultures from evolution history
            for evolution in self.recipe_evolutions.values():
                if (evolution.evolved_version_id == recipe.version_id and 
                    evolution.cultural_influences):
                    recipe_cultures.update(evolution.cultural_influences)
            
            # If multiple cultures, it's fusion
            if len(recipe_cultures) > 1:
                fusion_patterns.append({
                    'recipe_name': recipe.recipe_name,
                    'primary_culture': recipe.cultural_origin,
                    'fusion_cultures': list(recipe_cultures - {recipe.cultural_origin}),
                    'fusion_level': len(recipe_cultures) - 1,
                    'creation_date': recipe.creation_date.isoformat()
                })
                
                # Update influence network
                for other_culture in recipe_cultures:
                    if other_culture != recipe.cultural_origin:
                        cultural_influence_network[other_culture][recipe.cultural_origin] += 1
        
        # Identify major fusion trends
        fusion_by_culture = defaultdict(list)
        for pattern in fusion_patterns:
            fusion_by_culture[pattern['primary_culture']].append(pattern)
        
        fusion_hotspots = []
        for culture, patterns in fusion_by_culture.items():
            if len(patterns) > 2:  # At least 3 fusion recipes
                fusion_hotspots.append({
                    'culture': culture,
                    'fusion_recipes': len(patterns),
                    'average_fusion_level': np.mean([p['fusion_level'] for p in patterns]),
                    'most_common_influences': self._get_most_common_influences(patterns)
                })
        
        return {
            'total_fusion_recipes': len(fusion_patterns),
            'fusion_patterns': fusion_patterns,
            'fusion_hotspots': fusion_hotspots,
            'cultural_influence_network': dict(cultural_influence_network),
            'temporal_fusion_trends': await self._analyze_temporal_fusion_trends(fusion_patterns),
            'fusion_ingredients': await self._identify_fusion_ingredients()
        }
    
    async def predict_recipe_adaptations(self, version_id: str, target_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Predict potential recipe adaptations for different contexts"""
        recipe = self.recipe_versions.get(version_id)
        if not recipe:
            return []
        
        predictions = []
        
        # Dietary adaptation predictions
        if 'dietary_restrictions' in target_context:
            dietary_predictions = await self._predict_dietary_adaptations(recipe, target_context['dietary_restrictions'])
            predictions.extend(dietary_predictions)
        
        # Cultural adaptation predictions
        if 'target_culture' in target_context:
            cultural_predictions = await self._predict_cultural_adaptations(recipe, target_context['target_culture'])
            predictions.extend(cultural_predictions)
        
        # Seasonal adaptation predictions
        if 'target_season' in target_context:
            seasonal_predictions = await self._predict_seasonal_adaptations(recipe, target_context['target_season'])
            predictions.extend(seasonal_predictions)
        
        # Modern equipment adaptations
        if 'modern_equipment' in target_context:
            equipment_predictions = await self._predict_equipment_adaptations(recipe, target_context['modern_equipment'])
            predictions.extend(equipment_predictions)
        
        # Health-focused adaptations
        if 'health_focus' in target_context:
            health_predictions = await self._predict_health_adaptations(recipe, target_context['health_focus'])
            predictions.extend(health_predictions)
        
        return sorted(predictions, key=lambda x: x['confidence'], reverse=True)
    
    async def generate_tradition_preservation_report(self, tradition_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive tradition preservation report"""
        if tradition_id:
            traditions = [self.culinary_traditions[tradition_id]] if tradition_id in self.culinary_traditions else []
        else:
            traditions = list(self.culinary_traditions.values())
        
        if not traditions:
            return {'error': 'No traditions found'}
        
        preservation_analysis = []
        
        for tradition in traditions:
            # Analyze recipe lineage health
            lineage_health = []
            for recipe_lineage_id in tradition.core_recipes:
                if recipe_lineage_id in self.recipe_lineages:
                    lineage = self.recipe_lineages[recipe_lineage_id]
                    health_score = await self._calculate_lineage_health(lineage)
                    lineage_health.append({
                        'lineage_name': lineage.recipe_family_name,
                        'health_score': health_score,
                        'status': lineage.preservation_status,
                        'generations': lineage.current_generation
                    })
            
            # Calculate overall tradition health
            if lineage_health:
                avg_health = np.mean([lh['health_score'] for lh in lineage_health])
                at_risk_count = len([lh for lh in lineage_health if lh['health_score'] < 0.5])
            else:
                avg_health = 0.0
                at_risk_count = 0
            
            # Identify preservation threats and opportunities
            threats = await self._identify_preservation_threats(tradition)
            opportunities = await self._identify_preservation_opportunities(tradition)
            
            preservation_analysis.append({
                'tradition_name': tradition.tradition_name,
                'cultural_group': tradition.cultural_group,
                'core_recipes': len(tradition.core_recipes),
                'overall_health_score': avg_health,
                'recipes_at_risk': at_risk_count,
                'lineage_health': lineage_health,
                'preservation_threats': threats,
                'preservation_opportunities': opportunities,
                'recommendations': await self._generate_preservation_recommendations(tradition, avg_health, threats)
            })
        
        return {
            'preservation_analysis': preservation_analysis,
            'summary': {
                'traditions_analyzed': len(traditions),
                'average_health': np.mean([pa['overall_health_score'] for pa in preservation_analysis]) if preservation_analysis else 0.0,
                'traditions_at_risk': len([pa for pa in preservation_analysis if pa['overall_health_score'] < 0.5]),
                'total_recipes_at_risk': sum(pa['recipes_at_risk'] for pa in preservation_analysis)
            },
            'report_generated': datetime.now().isoformat()
        }
    
    async def _analyze_lineage_connections(self, recipe: RecipeVersion) -> List[str]:
        """Analyze potential lineage connections for new recipe"""
        connections = []
        
        # Look for similar recipe names
        for existing_recipe in self.recipe_versions.values():
            if (existing_recipe.version_id != recipe.version_id and
                self._calculate_recipe_name_similarity(recipe.recipe_name, existing_recipe.recipe_name) > 0.7):
                
                # Check if lineage exists
                lineage = await self._find_lineage_by_recipe(existing_recipe.version_id)
                if lineage:
                    # Add to existing lineage
                    if recipe.version_id not in lineage.version_timeline:
                        lineage.version_timeline.append(recipe.version_id)
                        lineage.current_generation += 1
                        connections.append(lineage.lineage_id)
                else:
                    # Create new lineage
                    new_lineage = await self._create_new_lineage(existing_recipe, recipe)
                    connections.append(new_lineage.lineage_id)
        
        return connections
    
    async def _find_or_create_lineage(self, original: RecipeVersion, evolved: RecipeVersion, 
                                    evolution: RecipeEvolution) -> Optional[RecipeLineage]:
        """Find existing lineage or create new one"""
        # First try to find existing lineage
        existing_lineage = await self._find_lineage_by_recipe(original.version_id)
        
        if existing_lineage:
            # Add evolved version to existing lineage
            if evolved.version_id not in existing_lineage.version_timeline:
                existing_lineage.version_timeline.append(evolved.version_id)
                existing_lineage.evolution_chain.append(evolution.evolution_id)
                existing_lineage.current_generation += 1
            return existing_lineage
        else:
            # Create new lineage
            return await self._create_new_lineage(original, evolved, evolution)
    
    async def _create_new_lineage(self, original: RecipeVersion, evolved: RecipeVersion, 
                                evolution: Optional[RecipeEvolution] = None) -> RecipeLineage:
        """Create new recipe lineage"""
        lineage_id = f"lineage_{uuid.uuid4().hex}"
        
        lineage = RecipeLineage(
            lineage_id=lineage_id,
            recipe_family_name=original.recipe_name,
            origin_version_id=original.version_id,
            current_generation=2,
            version_timeline=[original.version_id, evolved.version_id],
            evolution_chain=[evolution.evolution_id] if evolution else [],
            family_branches={},
            cultural_adaptations=[],
            geographic_spread=[original.cultural_origin, evolved.cultural_origin],
            time_span=(original.creation_date, evolved.creation_date),
            preservation_status="stable",
            key_innovations=[],
            traditional_elements=[],
            modernization_level=0.3
        )
        
        self.recipe_lineages[lineage_id] = lineage
        return lineage
    
    async def _find_lineage_by_recipe(self, version_id: str) -> Optional[RecipeLineage]:
        """Find lineage containing specific recipe version"""
        for lineage in self.recipe_lineages.values():
            if version_id in lineage.version_timeline:
                return lineage
        return None
    
    def _calculate_recipe_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between recipe names"""
        # Simple word overlap calculation
        words1 = set(name1.lower().split())
        words2 = set(name2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    async def _analyze_evolution_patterns(self, evolution: RecipeEvolution) -> Dict[str, Any]:
        """Analyze patterns in recipe evolution"""
        patterns = {
            'evolution_type': evolution.evolution_type.value,
            'driving_factors': evolution.environmental_factors + evolution.cultural_influences,
            'change_complexity': len(evolution.ingredient_changes) + len(evolution.method_changes),
            'success_rating': evolution.success_rating
        }
        
        # Analyze ingredient changes
        if evolution.ingredient_changes:
            patterns['ingredient_patterns'] = {
                'substitutions': len([c for c in evolution.ingredient_changes if c.get('type') == 'substitution']),
                'additions': len([c for c in evolution.ingredient_changes if c.get('type') == 'addition']),
                'removals': len([c for c in evolution.ingredient_changes if c.get('type') == 'removal'])
            }
        
        return patterns
    
    async def _analyze_ingredient_cultural_significance(self, ingredient_name: str, 
                                                      recipe_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze cultural significance of ingredient across recipes"""
        cultural_uses = defaultdict(list)
        ceremonial_uses = []
        regional_variations = defaultdict(list)
        
        for recipe_info in recipe_data:
            recipe = recipe_info['recipe']
            ingredient_details = recipe_info['ingredient_details']
            
            cultural_uses[recipe.cultural_origin].append({
                'recipe': recipe.recipe_name,
                'usage': recipe.category.value,
                'preparation': ingredient_details.preparation
            })
            
            if 'ceremonial' in recipe.occasion_context:
                ceremonial_uses.append({
                    'culture': recipe.cultural_origin,
                    'ceremony_type': recipe.occasion_context,
                    'recipe': recipe.recipe_name
                })
            
            if ingredient_details.cultural_significance:
                regional_variations[recipe.cultural_origin].append(ingredient_details.cultural_significance)
        
        return {
            'cultural_uses': dict(cultural_uses),
            'ceremonial_importance': ceremonial_uses,
            'regional_variations': dict(regional_variations),
            'cross_cultural_presence': len(cultural_uses),
            'significance_score': len(ceremonial_uses) * 0.3 + len(cultural_uses) * 0.1
        }
    
    def _get_most_common_influences(self, fusion_patterns: List[Dict[str, Any]]) -> List[str]:
        """Get most common cultural influences in fusion patterns"""
        influence_counts = defaultdict(int)
        
        for pattern in fusion_patterns:
            for culture in pattern['fusion_cultures']:
                influence_counts[culture] += 1
        
        return sorted(influence_counts.keys(), key=influence_counts.get, reverse=True)[:5]
    
    async def _analyze_temporal_fusion_trends(self, fusion_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal trends in cultural fusion"""
        # Group by decades
        decade_fusion = defaultdict(list)
        
        for pattern in fusion_patterns:
            try:
                year = datetime.fromisoformat(pattern['creation_date']).year
                decade = (year // 10) * 10
                decade_fusion[decade].append(pattern)
            except (ValueError, KeyError):
                continue
        
        trends = {}
        for decade, patterns in decade_fusion.items():
            trends[f"{decade}s"] = {
                'fusion_count': len(patterns),
                'average_fusion_level': np.mean([p['fusion_level'] for p in patterns]),
                'most_active_cultures': self._get_most_common_influences(patterns)
            }
        
        return trends
    
    async def _identify_fusion_ingredients(self) -> List[Dict[str, Any]]:
        """Identify ingredients commonly used in fusion recipes"""
        fusion_ingredients = defaultdict(lambda: {'count': 0, 'cultures': set(), 'recipes': []})
        
        # Find fusion recipes (recipes with multiple cultural influences)
        for recipe in self.recipe_versions.values():
            recipe_cultures = {recipe.cultural_origin}
            
            for ingredient in recipe.ingredients:
                if ingredient.source_region and ingredient.source_region != recipe.cultural_origin:
                    recipe_cultures.add(ingredient.source_region)
            
            if len(recipe_cultures) > 1:  # This is a fusion recipe
                for ingredient in recipe.ingredients:
                    fusion_ingredients[ingredient.name]['count'] += 1
                    fusion_ingredients[ingredient.name]['cultures'].update(recipe_cultures)
                    fusion_ingredients[ingredient.name]['recipes'].append(recipe.recipe_name)
        
        # Sort by count and return top fusion ingredients
        sorted_ingredients = sorted(
            fusion_ingredients.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        return [{
            'ingredient': name,
            'fusion_usage_count': data['count'],
            'cultures_involved': list(data['cultures']),
            'example_recipes': data['recipes'][:3]
        } for name, data in sorted_ingredients[:10]]
    
    async def _predict_dietary_adaptations(self, recipe: RecipeVersion, 
                                         dietary_restrictions: List[str]) -> List[Dict[str, Any]]:
        """Predict dietary adaptations for recipe"""
        adaptations = []
        
        for restriction in dietary_restrictions:
            if restriction == 'vegan':
                # Find non-vegan ingredients and suggest substitutions
                non_vegan_ingredients = []
                for ingredient in recipe.ingredients:
                    if any(animal_product in ingredient.name.lower() 
                          for animal_product in ['meat', 'chicken', 'beef', 'pork', 'fish', 'egg', 'milk', 'cheese', 'butter']):
                        non_vegan_ingredients.append(ingredient)
                
                if non_vegan_ingredients:
                    adaptations.append({
                        'adaptation_type': 'dietary_restriction',
                        'restriction': 'vegan',
                        'confidence': 0.8,
                        'changes_needed': len(non_vegan_ingredients),
                        'suggested_substitutions': await self._get_vegan_substitutions(non_vegan_ingredients),
                        'difficulty': 'medium' if len(non_vegan_ingredients) > 2 else 'easy'
                    })
            
            elif restriction == 'gluten_free':
                gluten_ingredients = []
                for ingredient in recipe.ingredients:
                    if any(gluten_source in ingredient.name.lower() 
                          for gluten_source in ['wheat', 'flour', 'bread', 'pasta']):
                        gluten_ingredients.append(ingredient)
                
                if gluten_ingredients:
                    adaptations.append({
                        'adaptation_type': 'dietary_restriction',
                        'restriction': 'gluten_free',
                        'confidence': 0.7,
                        'changes_needed': len(gluten_ingredients),
                        'suggested_substitutions': await self._get_gluten_free_substitutions(gluten_ingredients),
                        'difficulty': 'medium'
                    })
        
        return adaptations
    
    async def _predict_cultural_adaptations(self, recipe: RecipeVersion, target_culture: str) -> List[Dict[str, Any]]:
        """Predict cultural adaptations for recipe"""
        adaptations = []
        
        # Find ingredients that might not be available or preferred in target culture
        adaptation_suggestions = []
        
        for ingredient in recipe.ingredients:
            if ingredient.source_region and ingredient.source_region != target_culture:
                # Suggest local alternatives
                adaptation_suggestions.append({
                    'original_ingredient': ingredient.name,
                    'reason': 'regional_availability',
                    'suggested_alternatives': await self._get_cultural_ingredient_alternatives(ingredient.name, target_culture)
                })
        
        if adaptation_suggestions:
            adaptations.append({
                'adaptation_type': 'cultural_localization',
                'target_culture': target_culture,
                'confidence': 0.6,
                'adaptations_suggested': len(adaptation_suggestions),
                'ingredient_adaptations': adaptation_suggestions,
                'cultural_context': f'Adapting {recipe.cultural_origin} recipe for {target_culture} preferences'
            })
        
        return adaptations
    
    async def _predict_seasonal_adaptations(self, recipe: RecipeVersion, target_season: str) -> List[Dict[str, Any]]:
        """Predict seasonal adaptations for recipe"""
        adaptations = []
        
        seasonal_ingredients = []
        for ingredient in recipe.ingredients:
            if (ingredient.seasonality and target_season not in ingredient.seasonality):
                seasonal_ingredients.append(ingredient)
        
        if seasonal_ingredients:
            adaptations.append({
                'adaptation_type': 'seasonal_adjustment',
                'target_season': target_season,
                'confidence': 0.7,
                'seasonal_substitutions': len(seasonal_ingredients),
                'suggested_changes': [
                    {
                        'ingredient': ing.name,
                        'current_season': ing.seasonality,
                        'alternatives': await self._get_seasonal_alternatives(ing.name, target_season)
                    } for ing in seasonal_ingredients
                ]
            })
        
        return adaptations
    
    async def _predict_equipment_adaptations(self, recipe: RecipeVersion, modern_equipment: bool) -> List[Dict[str, Any]]:
        """Predict adaptations for modern equipment"""
        adaptations = []
        
        if modern_equipment:
            equipment_upgrades = []
            time_savings = []
            
            for step in recipe.cooking_steps:
                if step.method == CookingMethod.BOILING and 'pressure cooker' not in step.equipment:
                    equipment_upgrades.append({
                        'step': step.step_number,
                        'upgrade': 'Use pressure cooker',
                        'benefit': 'Reduce cooking time by 60%'
                    })
                
                if step.method == CookingMethod.BAKING and 'convection' not in step.description:
                    equipment_upgrades.append({
                        'step': step.step_number,
                        'upgrade': 'Use convection oven',
                        'benefit': 'Even heating, 25% faster'
                    })
            
            if equipment_upgrades:
                adaptations.append({
                    'adaptation_type': 'equipment_modernization',
                    'confidence': 0.8,
                    'equipment_upgrades': equipment_upgrades,
                    'estimated_time_savings': '20-60%',
                    'difficulty': 'easy'
                })
        
        return adaptations
    
    async def _predict_health_adaptations(self, recipe: RecipeVersion, health_focus: str) -> List[Dict[str, Any]]:
        """Predict health-focused adaptations"""
        adaptations = []
        
        if health_focus == 'low_sodium':
            high_sodium_ingredients = []
            for ingredient in recipe.ingredients:
                if any(sodium_source in ingredient.name.lower() 
                      for sodium_source in ['salt', 'soy sauce', 'broth', 'cheese']):
                    high_sodium_ingredients.append(ingredient)
            
            if high_sodium_ingredients:
                adaptations.append({
                    'adaptation_type': 'health_optimization',
                    'health_focus': 'low_sodium',
                    'confidence': 0.9,
                    'ingredients_to_modify': len(high_sodium_ingredients),
                    'suggested_reductions': await self._get_low_sodium_alternatives(high_sodium_ingredients)
                })
        
        elif health_focus == 'low_sugar':
            high_sugar_ingredients = []
            for ingredient in recipe.ingredients:
                if any(sugar_source in ingredient.name.lower() 
                      for sugar_source in ['sugar', 'honey', 'syrup', 'sweet']):
                    high_sugar_ingredients.append(ingredient)
            
            if high_sugar_ingredients:
                adaptations.append({
                    'adaptation_type': 'health_optimization',
                    'health_focus': 'low_sugar',
                    'confidence': 0.8,
                    'ingredients_to_modify': len(high_sugar_ingredients),
                    'suggested_alternatives': await self._get_low_sugar_alternatives(high_sugar_ingredients)
                })
        
        return adaptations
    
    async def _calculate_lineage_health(self, lineage: RecipeLineage) -> float:
        """Calculate health score for recipe lineage"""
        health_factors = {
            'version_count': min(len(lineage.version_timeline) / 5, 1.0) * 0.3,  # Up to 5 versions
            'time_span_factor': min((lineage.time_span[1] - lineage.time_span[0]).days / 3650, 1.0) * 0.2,  # 10 year span
            'cultural_diversity': min(len(lineage.cultural_adaptations) / 3, 1.0) * 0.2,  # Up to 3 cultures
            'geographic_spread': min(len(lineage.geographic_spread) / 5, 1.0) * 0.1,  # Up to 5 regions
            'preservation_status': {'thriving': 1.0, 'stable': 0.8, 'at_risk': 0.4, 'lost': 0.0}.get(lineage.preservation_status, 0.5) * 0.2
        }
        
        return sum(health_factors.values())
    
    async def _identify_preservation_threats(self, tradition: CulinaryTradition) -> List[str]:
        """Identify threats to culinary tradition preservation"""
        threats = []
        
        # Analyze recipe lineage health
        at_risk_lineages = 0
        for lineage_id in tradition.core_recipes:
            if lineage_id in self.recipe_lineages:
                lineage = self.recipe_lineages[lineage_id]
                if lineage.preservation_status in ['at_risk', 'lost']:
                    at_risk_lineages += 1
        
        if at_risk_lineages > len(tradition.core_recipes) * 0.3:
            threats.append("High percentage of core recipes at risk")
        
        # Check for modernization pressure
        modern_adaptations = len(tradition.modern_adaptations)
        if modern_adaptations > len(tradition.core_recipes):
            threats.append("Excessive modernization diluting traditional elements")
        
        # Check ingredient availability
        key_ingredients_at_risk = []
        for ingredient_name in tradition.key_ingredients:
            if ingredient_name in self.ingredient_database:
                ingredient_data = self.ingredient_database[ingredient_name]
                if len(ingredient_data['cultures']) < 2:  # Limited cultural presence
                    key_ingredients_at_risk.append(ingredient_name)
        
        if key_ingredients_at_risk:
            threats.append(f"Key ingredients becoming rare: {', '.join(key_ingredients_at_risk[:3])}")
        
        return threats
    
    async def _identify_preservation_opportunities(self, tradition: CulinaryTradition) -> List[str]:
        """Identify opportunities for tradition preservation"""
        opportunities = []
        
        if len(tradition.preservation_efforts) > 0:
            opportunities.append("Active preservation efforts already in place")
        
        if len(tradition.modern_adaptations) > 0:
            opportunities.append("Modern adaptations could attract new practitioners")
        
        # Check for cultural fusion potential
        cultural_connections = len(self.cultural_networks.get(tradition.cultural_group, set()))
        if cultural_connections > 3:
            opportunities.append("Strong cultural network for knowledge sharing")
        
        return opportunities
    
    async def _generate_preservation_recommendations(self, tradition: CulinaryTradition, 
                                                   health_score: float, threats: List[str]) -> List[str]:
        """Generate preservation recommendations"""
        recommendations = []
        
        if health_score < 0.5:
            recommendations.append("URGENT: Document all traditional recipes immediately")
            recommendations.append("Identify and interview master practitioners")
            recommendations.append("Create multimedia preservation project")
        
        if "recipes at risk" in str(threats):
            recommendations.append("Focus preservation efforts on most endangered recipes")
            recommendations.append("Establish recipe guardian program")
        
        if "ingredients becoming rare" in str(threats):
            recommendations.append("Develop ingredient cultivation or sourcing programs")
            recommendations.append("Document acceptable ingredient substitutions")
        
        if len(tradition.preservation_efforts) == 0:
            recommendations.append("Establish formal preservation initiative")
            recommendations.append("Partner with cultural organizations")
        
        # Always beneficial
        recommendations.append("Create community cooking workshops")
        recommendations.append("Develop educational materials for younger generations")
        recommendations.append("Document family stories associated with recipes")
        
        return recommendations
    
    # Helper methods for ingredient substitutions
    async def _get_vegan_substitutions(self, ingredients: List[Ingredient]) -> Dict[str, List[str]]:
        """Get vegan substitutions for ingredients"""
        vegan_subs = {}
        for ingredient in ingredients:
            name = ingredient.name.lower()
            if 'egg' in name:
                vegan_subs[ingredient.name] = ['flax egg', 'chia egg', 'applesauce', 'aquafaba']
            elif 'milk' in name:
                vegan_subs[ingredient.name] = ['almond milk', 'oat milk', 'coconut milk', 'soy milk']
            elif 'butter' in name:
                vegan_subs[ingredient.name] = ['vegan butter', 'coconut oil', 'olive oil']
            elif any(meat in name for meat in ['chicken', 'beef', 'pork']):
                vegan_subs[ingredient.name] = ['tofu', 'tempeh', 'seitan', 'mushrooms', 'lentils']
        return vegan_subs
    
    async def _get_gluten_free_substitutions(self, ingredients: List[Ingredient]) -> Dict[str, List[str]]:
        """Get gluten-free substitutions for ingredients"""
        gf_subs = {}
        for ingredient in ingredients:
            name = ingredient.name.lower()
            if 'flour' in name or 'wheat' in name:
                gf_subs[ingredient.name] = ['almond flour', 'rice flour', 'coconut flour', 'gluten-free flour blend']
            elif 'bread' in name:
                gf_subs[ingredient.name] = ['gluten-free bread', 'rice cakes', 'corn tortillas']
        return gf_subs
    
    async def _get_cultural_ingredient_alternatives(self, ingredient_name: str, target_culture: str) -> List[str]:
        """Get culturally appropriate ingredient alternatives"""
        # This would be populated with actual cultural knowledge
        cultural_alternatives = {
            'soy sauce': {'indian': ['tamarind paste', 'coconut aminos'], 'mexican': ['worcestershire sauce', 'lime juice']},
            'rice wine': {'western': ['white wine', 'apple cider vinegar'], 'middle_eastern': ['grape vinegar']},
            'miso paste': {'western': ['anchovy paste', 'umami paste'], 'indian': ['tamarind paste']}
        }
        
        return cultural_alternatives.get(ingredient_name.lower(), {}).get(target_culture.lower(), ['local equivalent'])
    
    async def _get_seasonal_alternatives(self, ingredient_name: str, target_season: str) -> List[str]:
        """Get seasonal alternatives for ingredients"""
        seasonal_alts = {
            'tomatoes': {'winter': ['canned tomatoes', 'sun-dried tomatoes', 'tomato paste']},
            'fresh herbs': {'winter': ['dried herbs', 'frozen herbs', 'herb oils']},
            'berries': {'winter': ['frozen berries', 'dried berries', 'berry preserves']}
        }
        
        return seasonal_alts.get(ingredient_name.lower(), {}).get(target_season, [f'{target_season} equivalent'])
    
    async def _get_low_sodium_alternatives(self, ingredients: List[Ingredient]) -> Dict[str, List[str]]:
        """Get low-sodium alternatives"""
        low_sodium_alts = {}
        for ingredient in ingredients:
            name = ingredient.name.lower()
            if 'salt' in name:
                low_sodium_alts[ingredient.name] = ['herbs', 'spices', 'lemon juice', 'garlic']
            elif 'soy sauce' in name:
                low_sodium_alts[ingredient.name] = ['low-sodium soy sauce', 'coconut aminos', 'balsamic vinegar']
        return low_sodium_alts
    
    async def _get_low_sugar_alternatives(self, ingredients: List[Ingredient]) -> Dict[str, List[str]]:
        """Get low-sugar alternatives"""
        low_sugar_alts = {}
        for ingredient in ingredients:
            name = ingredient.name.lower()
            if 'sugar' in name:
                low_sugar_alts[ingredient.name] = ['stevia', 'monk fruit', 'xylitol', 'fresh fruit']
            elif 'honey' in name:
                low_sugar_alts[ingredient.name] = ['sugar-free honey substitute', 'applesauce', 'mashed banana']
        return low_sugar_alts

# Example usage
async def main():
    """Example usage of recipe evolution tracking system"""
    
    print("Recipe Evolution Tracking System Demo")
    print("=" * 50)
    
    # Initialize tracker
    tracker = RecipeEvolutionTracker()
    
    # Create sample ingredients
    ingredients_v1 = [
        Ingredient(
            ingredient_id="ing_001",
            name="ground beef",
            quantity="1",
            unit="lb",
            preparation="browned",
            substitutions=["ground turkey", "lentils"],
            source_region="American Midwest"
        ),
        Ingredient(
            ingredient_id="ing_002",
            name="tomato sauce",
            quantity="2",
            unit="cups",
            seasonality=["summer", "fall"],
            source_region="Italian"
        ),
        Ingredient(
            ingredient_id="ing_003",
            name="pasta shells",
            quantity="12",
            unit="oz",
            source_region="Italian"
        )
    ]
    
    ingredients_v2 = [
        Ingredient(
            ingredient_id="ing_004",
            name="ground turkey",
            quantity="1",
            unit="lb",
            preparation="browned",
            substitutions=["ground beef", "tofu"],
            source_region="American"
        ),
        Ingredient(
            ingredient_id="ing_005",
            name="marinara sauce",
            quantity="2",
            unit="cups",
            seasonality=["year-round"],
            source_region="Italian-American"
        ),
        Ingredient(
            ingredient_id="ing_006",
            name="whole wheat pasta shells",
            quantity="12",
            unit="oz",
            source_region="Italian"
        )
    ]
    
    # Create cooking steps
    steps_v1 = [
        CookingStep(
            step_id="step_001",
            step_number=1,
            description="Brown ground beef in large skillet",
            method=CookingMethod.FRYING,
            duration="5-7 minutes",
            equipment=["large skillet"]
        ),
        CookingStep(
            step_id="step_002",
            step_number=2,
            description="Add tomato sauce and simmer",
            method=CookingMethod.STEWING,
            duration="20 minutes",
            equipment=["skillet"]
        )
    ]
    
    steps_v2 = [
        CookingStep(
            step_id="step_003",
            step_number=1,
            description="Brown ground turkey in large skillet with cooking spray",
            method=CookingMethod.FRYING,
            duration="5-7 minutes",
            equipment=["large non-stick skillet", "cooking spray"]
        ),
        CookingStep(
            step_id="step_004",
            step_number=2,
            description="Add marinara sauce and simmer",
            method=CookingMethod.STEWING,
            duration="15 minutes",
            equipment=["skillet"]
        )
    ]
    
    # Create recipe versions
    recipe_v1 = RecipeVersion(
        version_id="recipe_v1_001",
        recipe_name="Classic Stuffed Shells",
        version_name="Grandma's Original",
        category=RecipeCategory.MAIN_COURSE,
        cultural_origin="Italian-American",
        creator_name="Maria Rossi",
        creation_date=date(1950, 6, 15),
        ingredients=ingredients_v1,
        cooking_steps=steps_v1,
        cooking_methods=[CookingMethod.FRYING, CookingMethod.BAKING, CookingMethod.STEWING],
        difficulty_level="medium",
        cooking_time="45 minutes",
        serving_size="6-8 servings",
        dietary_restrictions=[DietaryRestriction.NONE],
        flavor_profile=["savory", "rich", "comforting"],
        occasion_context=["family dinner", "sunday meal"],
        cultural_notes="Traditional recipe passed down from Italian grandmother",
        family_stories=["Made every Sunday for family gatherings"],
        source_generation=1
    )
    
    recipe_v2 = RecipeVersion(
        version_id="recipe_v2_001",
        recipe_name="Healthy Stuffed Shells",
        version_name="Modern Health-Conscious",
        category=RecipeCategory.MAIN_COURSE,
        cultural_origin="Italian-American",
        creator_name="Lisa Rossi-Johnson",
        creation_date=date(2010, 3, 20),
        ingredients=ingredients_v2,
        cooking_steps=steps_v2,
        cooking_methods=[CookingMethod.FRYING, CookingMethod.BAKING, CookingMethod.STEWING],
        difficulty_level="medium",
        cooking_time="40 minutes",
        serving_size="6-8 servings",
        dietary_restrictions=[DietaryRestriction.LOW_SODIUM],
        flavor_profile=["savory", "lighter", "healthier"],
        occasion_context=["family dinner", "healthy eating"],
        cultural_notes="Modern adaptation focusing on health while preserving tradition",
        family_stories=["Adapted by granddaughter for her health-conscious family"],
        source_person="Maria Rossi",
        source_generation=3
    )
    
    # Add recipes to tracker
    result1 = await tracker.add_recipe_version(recipe_v1)
    print(f"Added recipe v1: Success: {result1['success']}")
    
    result2 = await tracker.add_recipe_version(recipe_v2)
    print(f"Added recipe v2: Success: {result2['success']}")
    
    # Document evolution
    evolution = RecipeEvolution(
        evolution_id="evolution_001",
        original_version_id="recipe_v1_001",
        evolved_version_id="recipe_v2_001",
        evolution_type=EvolutionType.HEALTH_ADAPTATION,
        evolution_date=date(2010, 3, 20),
        evolution_reason="Health-conscious adaptation for modern family",
        change_description="Replaced ground beef with turkey, added whole wheat pasta, used cooking spray",
        ingredient_changes=[
            {"type": "substitution", "original": "ground beef", "new": "ground turkey", "reason": "lower fat"},
            {"type": "substitution", "original": "regular pasta", "new": "whole wheat pasta", "reason": "more fiber"},
            {"type": "method_change", "change": "added cooking spray", "reason": "reduce oil"}
        ],
        cultural_influences=["American health movement"],
        environmental_factors=["increased health awareness"],
        person_responsible="Lisa Rossi-Johnson",
        success_rating=0.9
    )
    
    evolution_result = await tracker.document_recipe_evolution(evolution)
    print(f"Documented evolution: Success: {evolution_result['success']}")
    
    # Trace recipe lineage
    print("\n" + "=" * 50)
    print("RECIPE LINEAGE ANALYSIS")
    print("=" * 50)
    
    lineages = await tracker.trace_recipe_lineage("Stuffed Shells")
    print(f"Found {len(lineages)} lineages for Stuffed Shells")
    
    for lineage in lineages:
        print(f"\nLineage: {lineage.lineage_id}")
        print(f"Family name: {lineage.recipe_family_name}")
        print(f"Generations: {lineage.current_generation}")
        print(f"Time span: {lineage.time_span[0]} to {lineage.time_span[1]}")
        print(f"Geographic spread: {lineage.geographic_spread}")
        print(f"Modernization level: {lineage.modernization_level:.2f}")
    
    # Analyze ingredient evolution
    print("\n" + "=" * 50)
    print("INGREDIENT EVOLUTION ANALYSIS")
    print("=" * 50)
    
    beef_analysis = await tracker.analyze_ingredient_evolution("ground beef")
    print(f"Ground beef analysis:")
    print(f"Total recipes using: {beef_analysis['total_recipes']}")
    print(f"Cultures using: {beef_analysis['cultures_used']}")
    print(f"Common substitutions: {beef_analysis['common_substitutions']}")
    print(f"Cultural significance score: {beef_analysis['cultural_significance']['significance_score']:.2f}")
    
    # Generate cultural fusion report
    print("\n" + "=" * 50)
    print("CULTURAL FUSION REPORT")
    print("=" * 50)
    
    fusion_report = await tracker.generate_cultural_fusion_report()
    print(f"Total fusion recipes: {fusion_report['total_fusion_recipes']}")
    print(f"Fusion hotspots: {len(fusion_report['fusion_hotspots'])}")
    print(f"Top fusion ingredients: {len(fusion_report['fusion_ingredients'])}")
    
    # Predict recipe adaptations
    print("\n" + "=" * 50)
    print("RECIPE ADAPTATION PREDICTIONS")
    print("=" * 50)
    
    predictions = await tracker.predict_recipe_adaptations(
        "recipe_v1_001",
        {
            'dietary_restrictions': ['vegan', 'gluten_free'],
            'target_culture': 'indian',
            'health_focus': 'low_sodium'
        }
    )
    
    print(f"Adaptation predictions: {len(predictions)}")
    for pred in predictions:
        print(f"\n- Adaptation type: {pred['adaptation_type']}")
        print(f"  Confidence: {pred['confidence']:.1%}")
        print(f"  Changes needed: {pred.get('changes_needed', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(main())